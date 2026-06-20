---
title: "External Intermittent Mobile Spotify Playback Audit — Report"
source: "External auditor — against docs/handoffs/External Intermittent Mobile Spotify Playback Audit Handoff.md"
created: 2026-06-20
status: draft
verdict: "PARTIAL — recovery architecture is now coherent and much improved; remaining failures are explained by trust-without-verify playback + zero network/lifecycle instrumentation, not by incoherent retry patches. Do NOT rewrite. Add observability + stall detection + state separation before any more recovery logic."
constraints_met: "No code changed. No commits. No .env/token values read or printed."
---

# External Intermittent Mobile Spotify Playback Audit — Report

## Verdict: PARTIAL

The recovery work has materially improved since the previous mobile-playback audit. The app now has a **single, concurrency-guarded recovery routine** (`_recoverSpotifySession`), it **invalidates the stale device on 404** before retrying, it **rebuilds the SDK, waits for a new device, verifies Spotify Connect visibility, transfers playback, then retries once**, and it has added **Media Session handlers, play/pause, a guarded Previous, and a user-facing Recover button**. This is not a pile of incoherent timer patches — the core recovery sequence is sound and matches what the prior audit recommended.

The remaining intermittent failures are explained by a single underlying weakness, not by the recovery code being wrong: **the player drives Spotify playback from device registration + HTTP acceptance rather than from confirmed audible state, and it has essentially no network/lifecycle instrumentation to tell the failure modes apart.** When `/me/player/play` returns 200 but no audio actually starts, the code enters a "blind playback" mode that masks the stall and silently advances at the track's nominal end — which is exactly the "music begins, then halts near the start" symptom. And because there is no `navigator.onLine`, no `pageshow/pagehide`, and no device-age/rebuild instrumentation, neither the owner nor a future fix can tell whether a given failure was a transient offline blip, a bfcache restore, or a genuinely stale Connect device.

So: keep the architecture, stop adding recovery branches, and add **observability + stall-aware verification + UI state separation** next. The hypothesis in the brief (stale Connect device lifecycle + insufficient state separation) is **largely confirmed**, with one important update: device-staleness is now *handled*; the unresolved half is **trust-without-verify playback** plus **missing instrumentation**.

---

## Method & Limitations

**Inspected (current code):** `resonova/web/player.js` (1,903 lines — full read), `resonova/web/index.html` (playback controls, mini-panel, cache-bust), `resonova/api/spotify.py` (token/refresh). Prior reports and lifecycle handoffs reviewed for continuity.

**Live corroboration (Claude-in-Chrome MCP, against the running `http://127.0.0.1:8765`):** served build is `player.js?v=20260620-now-playing-trail`; the new grouped cast-management UI renders (playlists grouped, "Run #1" badge, order fingerprint, track preview, Play/Rename/Delete). Entering a saved episode, the live playing-state DOM exposes **Previous, Pause, Next, Diag**, with **Recover Spotify present but hidden** until unhealthy — matching the source.

**Limitations (honest):**
- **The intermittent failure was not reproduced.** It only occurs on a real mobile device under background/network conditions a desktop Chrome session can't reproduce. The root-cause tree is established by code analysis + the owner's diagnostic reports, not a fresh capture. Required on-device evidence is listed below.
- **Commit-level `git diff` could not be run** (the sandbox VM that runs git was unavailable this pass). Findings rest on the current code state, which is decisive; commit messages are taken from the brief.

---

## Single Root-Cause Tree

```
ROOT: Playback is driven by device-registration + HTTP acceptance, not by
      confirmed audible SDK state — and there is no network/lifecycle
      instrumentation to distinguish failure modes.
│
├─ Branch A — Device deregistration (suspend / bfcache / idle)
│    SDK device drops out of Spotify Connect → /me/player/play → 404 "Device not found".
│    STATUS: now HANDLED — _discardSpotifyDevice() + rebuild + Connect-visibility recheck + retry once.
│    Residual: fixed 3–5s timeouts can lose the race on slow mobile networks → recoveryFailed.
│
├─ Branch B — Play accepted (200) but no audio  ← the main unresolved symptom
│    _sendSpotifyPlayCommand succeeds; _waitForSpotifyPlaybackStart times out (3–5s);
│    code enters BLIND playback mode and sets a duration-based deadline.
│    RESULT: user hears silence "halting near the start"; queue still advances at nominal end.
│    There is no stall detection (position-not-advancing) — only an end-of-track deadline.
│
└─ Branch C — Transient offline / page lifecycle
     A brief offline blip or bfcache page restore produces the same generic failure,
     because nothing observes navigator.onLine, online/offline, or pageshow/pagehide.
     RESULT: misattributed/over-generic failure; no targeted recovery or message.
```

All three branches are the same defect viewed three ways: **trust without verify, plus no observability.** Fixing those two things addresses all three; adding more recovery entry points does not.

---

## Findings (ranked by severity)

### F1 · High · "Blind playback" trusts HTTP 200 and masks real stalls
When the play command returns OK but `_waitForSpotifyPlaybackStart()` (only **3s**, 5s on retry) doesn't see playback, the code logs "continuing in blind playback mode" and arms `_setBlindSpotifyDeadline()` — a `duration_ms + 3000` timer that force-advances at the track's nominal end (`player.js:1070-1088`, `1102-1114`, `778-792`). Consequences: (a) a genuinely silent/stalled segment is presented as playing and the user hears **nothing for the whole track** before the queue advances; (b) a track that simply started slowly is falsely treated as blind. There is **no stall detection** (position not advancing) anywhere — only end-time deadlines (`_handleSpotifyStateChange`, `:1132-1144`). This is the most direct explanation of "music begins, then halts near the start."

### F2 · High · No network or page-lifecycle instrumentation
Grep confirms **no** `navigator.onLine`, `online`/`offline` listeners, `pageshow`/`pagehide`, device-acquisition timestamp, or rebuild/generation counter anywhere in `player.js`. The diagnostic panel (`:1158-1227`) shows only current booleans, with no event history. There is therefore no way to attribute an intermittent failure to an offline blip vs. a bfcache restore vs. a stale device, and no way to know how old the device is or how many times it has been rebuilt. **This is the single highest-leverage gap** — it should be closed before any further recovery logic.

### F3 · Medium · Health is scattered booleans, not one explicit state machine
"Spotify health" is derived ad hoc from `_spotifyUnhealthy`, `_spotifyRecovering`, `_spotifyRecoveryFailed`, and `_lifecycle.authError/playbackError/notReady/ready` via `_isSpotifyHealthy()` (`:75-82`), checked at ~7 entry points (`_playSpotifyTrack` pre-check `:1020`, 404 path `:1075`, outer catch `:1091`; `resume` `:273`; `previous` `:1700`; `_reconcileAfterBackground` `:488`; `recoverSpotify` `:228`). The single recovery routine is concurrency-guarded (`:132`) and coherent, but there is **no single source of truth** for "what state are we in," so flags can drift (e.g., `_clearSpotifyUnhealthy` only runs on `ready`/recovery success; a stale `playbackError` cleared in one path but set in another). Coherent *enough* today, but the implicit-state design is the maintenance risk that produces "fixed one case, broke another."

### F4 · Medium · Fixed timeouts race against mobile network latency
Recovery uses hard timeouts: device-ready 3s then 5s (`:149,159`), Connect-visibility 5s polling every 350ms (`:734-750`), playback-start 3s/5s (`:778`). On a slow/variable mobile connection these can expire even when the operation would have succeeded a moment later, surfacing as intermittent `recoveryFailed`. There is no adaptive wait or one-shot delayed re-check.

### F5 · Medium · UI collapses distinct states into one generic failure
Offline, device-lost, SDK-not-ready, and blind-playback all present to the user as either silent continuation or the generic "(Spotify connection lost. Click Recover below.)" / "Recover needed" (`:1025,1096,1507-1519`). There is no offline-specific message and **no "skip music, keep commentary" fallback**, so a single bad music segment can stall the whole episode instead of degrading gracefully. The detailed signals exist internally and in the owner-only diag panel but never reach the user as distinct, actionable states.

### F6 · Low · `_waitForSpotifyConnectDevice` adds latency to every Spotify segment
`_sendSpotifyPlayCommand()` calls `_waitForSpotifyConnectDevice()` (a `/me/player/devices` round-trip, up to 5s) **before every** play command, even on a healthy device (`:752-776`). In the common healthy case this adds a network round-trip of startup latency per music segment. Consider gating it to the post-recovery / first-play case.

### F7 · Low (positive — preserve) · The genuinely-improved parts
404 handling now invalidates the stale device and rebuilds before retry (`:1075-1089`); `previous()` recovers before navigating into a Spotify segment and aborts cleanly if recovery fails (`:1700-1709`); recovery is single-attempt with a shared in-flight promise (no retry storm) (`:131-190`); Media Session metadata + handlers are wired (`:333-360`); play/pause exists. These directly resolve earlier audit findings and should **not** be regressed.

---

## Answers To The 10 Audit Questions

1. **One coherent state machine or overlapping recovery paths?** One coherent *recovery routine* (`_recoverSpotifySession`, concurrency-guarded) reached from ~7 entry points; but overall "health" is represented as **scattered booleans**, not an explicit state machine (F3). Coherent enough today, fragile to extend.
2. **On 404 Device not found, is the stale device invalidated before retry?** **Yes** — `_discardSpotifyDevice()` disconnects, nulls the player and `deviceId`, then recovery rebuilds (`:1077-1080`). This is a real fix vs. the prior audit.
3. **Does recovery rebuild SDK → wait new ready device → transfer → then retry?** **Yes** — token refresh → reconnect → wait device (3s) → if none, disconnect+rebuild → wait (5s) → wait Connect-visible (5s) → transfer → caller retries play (`:131-190`, `:228-233`, `:1080-1088`).
4. **Does the UI distinguish offline / token-failed / SDK-not-ready / device-stale / play-accepted-no-state / playing-but-state-unavailable?** **Internally, mostly yes; in the UI, no.** Device-missing, blind-playback, and auth are distinct in logic, but the user sees generic "Recover needed" / silence. **Offline is not detected at all** (F2, F5).
5. **Instrumentation for `navigator.onLine` / online-offline / failed fetches / device-id age-generation / visibility-pagehide-pageshow timing?** `visibilitychange`: yes (one listener). **Everything else: no** — no `onLine`, no online/offline, no pageshow/pagehide, no device age or rebuild counter, only ad-hoc `console` logs (F2).
6. **Does Recover retry forever, once, or bounded backoff?** **Bounded single attempt per trigger**, guarded by `_spotifyRecovering` (`:132`); repeats are user-driven via the button. No infinite loop, no automatic backoff. Good.
7. **Does the app risk advancing the queue while Spotify hasn't actually started audible playback?** **Yes** — blind-playback mode advances at the nominal track end even when audio never started (F1). It can also sit in silence for a full track first.
8. **Are Previous/Next guarded against re-entering a known-bad Spotify segment?** **Previous: yes** (explicit health check + abort, `:1700-1709`). **Next/Skip:** indirectly — `skip()` itself has no check, but it lands in `_playSpotifyTrack()` which does a health pre-check + single auto-recovery (`:1020-1030`). No repeat-loop, but the guarding is asymmetric.
9. **Minimum instrumentation before another fix?** Online/offline + pageshow/pagehide event logging; device-acquired timestamp + rebuild/generation counter; per-play HTTP status+body, playback-start result, deadline fire, recovery start/result — all into a small ring buffer visible in the diag panel and copyable. Ship this **alone**, capture one real phone failure, then decide the next fix from data.
10. **UX fallback when Spotify is temporarily unavailable?** Add: an offline-specific message (via `navigator.onLine`), distinct device-lost vs. Spotify-error messages, and a **"Skip music, keep commentary"** option so one bad segment degrades gracefully instead of halting the episode.

---

## Evidence To Collect On The Real Phone (next test)

With the Diag panel on, reproduce a failure and record, **at the moment it stalls**:
- Diag fields: `ready`, `device_id`, `not_ready`, `auth_error`, `playback_err`, `Paused`, `Position`, `Duration`, `Track`.
- The exact play response: HTTP **status and body** (the code already includes up to 180 chars — note whether it's `404 Device not found` vs `Spotify SDK did not report playback`).
- Did the track briefly appear then **freeze** (position not advancing) — i.e. true stall — or never appear at all?
- `navigator.onLine` value and whether Wi-Fi/cell was momentarily dropping.
- Did the failure follow a **lock/return** or tab switch (page lifecycle)?
- Press **Recover**: does the new `device_id` **differ** (true rebuild) or stay the same (reconnect only)? Does playback then start?
- Capture the **console log** trail (the player logs play/recovery steps verbosely).

This distinguishes Branch A (404/device) from Branch B (200-but-silent) from Branch C (offline/lifecycle) — which the current code cannot do for you.

---

## Bounded Implementation Brief (RUG-ready, if approved)

**Sequence matters — do Item 1 first, ship it alone, gather one real failure, then proceed.**

**Item 1 — Observability only (no behavior change).** `player.js`.
- Add `online`/`offline` and `pageshow`/`pagehide` listeners that append to a bounded in-memory ring buffer (timestamp + event).
- Record device-acquired timestamp and a `deviceGeneration` counter (increment on every rebuild in `_recoverSpotifySession`/`_initSpotifyPlayer`).
- Log into the same ring buffer: play command (uri, status, body), playback-start confirmed/blind, deadline fired, recovery start/result, device discarded.
- Surface the ring buffer in the diag panel with a copy-to-clipboard button.
- Acceptance: a single phone failure yields a copyable timeline that identifies Branch A/B/C.

**Item 2 — Stall-aware playback verification (replaces blind trust).** `player.js`.
- After a successful play command, verify **audible progress**: poll `getCurrentState()` and require `position` to *advance* across two samples (not just match the URI once) within N seconds.
- If it never starts or stalls: do **not** silently arm a full-duration blind deadline. Mark unhealthy, show a precise message, and offer Recover and/or auto "skip music."
- Keep a short safety deadline only as a last resort, not as the primary signal.
- Acceptance: a 200-but-silent segment surfaces within a few seconds as a recoverable state, never as silent "playing."

**Item 3 — UI state separation + graceful music fallback.** `player.js` + `index.html`/`styles.css`.
- Distinct messages: offline (`navigator.onLine` false), device lost, Spotify error.
- Add a **"Skip music, keep commentary"** action so one bad Spotify segment advances to the next commentary instead of stalling the episode.
- Acceptance: with network toggled off mid-segment, the UI says "offline" (not generic), and the episode can continue commentary-only.

**Optional Item 4 (low priority) —** consolidate the health booleans behind one small status getter/object to reduce desync risk (F3). Only if recovery churn continues.

---

## Do-Not-Do List (avoid hiding the state problem)

- **Do not** keep blind force-advance as the primary mechanism — verify audible progress instead (F1).
- **Do not** trust HTTP 200 from `/me/player/play` as "audio is playing."
- **Do not** add more recovery entry points or any automatic repeating/backoff recovery before Item 1 instrumentation exists.
- **Do not** add infinite or timer-driven retry loops (the current single-attempt model is correct — keep it).
- **Do not** rewrite the player or the recovery routine; the device-invalidation/rebuild/transfer sequence is sound.
- **Do not** fold cast-cache / loaded-cast management into this work — it's a separate RUG task (see below).
- **Do not** expose `.env`, tokens, or secrets; keep the diag panel owner-only.

---

## Separation Of Concerns Note (cast management)

Per the brief, this audit does **not** cover cast-cache / loaded-cast management — but note that a first version **already exists** in the current build: episodes are grouped by playlist with "Run #" badges, an order fingerprint, a track-order preview, and Play/Rename/Delete actions (`player.js:1270-1366`, live-confirmed). The parked RUG product/UX task should **build on this existing UI** (add Resume/Regenerate/Refresh-snapshot and a clearer replay-vs-generate distinction) rather than start fresh, and it should stay independent of the playback-reliability work above.

---

## Evidence Index

| Claim | Evidence |
|---|---|
| Single recovery routine, concurrency-guarded | `player.js:131-190` |
| 404 → discard stale device + rebuild + retry once | `:1075-1089`, `_discardSpotifyDevice` `:794-801` |
| Recovery sequence (token→reconnect→rebuild→Connect-visible→transfer) | `:138-176`, `_waitForSpotifyConnectDevice` `:734-750`, `_transferPlayback` `:718-732` |
| Blind playback masks stalls; trusts 200 | `:1070-1088`, `_waitForSpotifyPlaybackStart` `:778-792`, `_setBlindSpotifyDeadline` `:1102-1114` |
| No stall (position-progress) detection | `_handleSpotifyStateChange` `:1116-1156` (end-deadline only) |
| No network/lifecycle instrumentation | grep: no `navigator.onLine`/`online`/`offline`/`pageshow`/`pagehide`/device-age/generation in `player.js` |
| Health = scattered booleans | `_isSpotifyHealthy` `:75-82`; flags set across `:84-113, 660-715, 1020, 1075-1095, 1700` |
| Fixed timeouts | `:149,159` (3s/5s), `:734` (5s), `:778` (3s/5s) |
| UI collapses states; no offline message; no music-skip fallback | `:1025, 1096, 1507-1519` |
| Connect-visibility round-trip on every play | `_sendSpotifyPlayCommand` `:752-776` |
| Previous guarded; Recover single-attempt; Media Session | `:1700-1709`, `:131-190`, `:333-360` |
| Cast-management UI already present | `:1270-1366`; live DOM (grouped, Run #, fingerprint, Play/Rename/Delete) |
| Served build current | `index.html:369` (`?v=20260620-now-playing-trail`); live controls Previous/Pause/Next/Diag, Recover hidden |

Commits named in the brief (messages, not diff-verified this pass): `916ca16` Gemini 3.5 Flash · `1a9d26f` wait for Connect device · `028facc` blind playback · `a0ceed6` verify playback after recovery · `20db310` retry after stale device · `ccdb343` clarify errors · `a867fec` now-playing trail + media controls · `5bb49fc` library nav + model defaults · `98d6b4c` saved cast management + replay variety · `b92c73f` normalize commentary loudness.

---

## Areas Not Tested

- **On-device intermittent reproduction** — not performed (desktop can't reproduce mobile background/network conditions). Root-cause tree is code- and report-based; the phone-evidence checklist above closes it.
- **Commit-level `git diff`** — not performed (git sandbox unavailable); current code state used instead.
- **Whether `setVolume`/transfer behave on the owner's specific phone** — taken from SDK limitations + owner reports, not re-measured.
- **Real Spotify Connect 404 timing under live mobile suspension** — the handling path is verified in code but its success rate against actual timeouts can only be measured on-device (Item 1 instrumentation will quantify it).

## Constraint Compliance

No code implemented, no commits, no `.env`/token values read or printed, product identity unchanged, no rewrite recommended, and verified facts (code/line evidence, live DOM) are separated from the items dependent on on-device behavior (flagged as not reproduced).
