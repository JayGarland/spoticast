---
title: "External Mobile Playback Implementation Audit — Report"
source: "External auditor — against docs/handoffs/External Mobile Playback Implementation Audit Handoff.md"
created: 2026-06-20
status: draft
verdict: "Do not roll back. Keep current code; add one bounded SDK-recovery routine + health gating + a manual Recover affordance. Treat automatic-transition-while-locked as parked."
constraints_met: "No code changed. No commits. No .env/token values read or printed."
---

# External Mobile Playback Implementation Audit — Report

## Executive Summary

The owner's report is accurate and the root cause is verifiable in the current code: **the Spotify Web Playback SDK has no recovery path.** Every recovery-relevant listener (`authentication_error`, `playback_error`, `not_ready`) only writes a diagnostic field — none of them refreshes the token, reconnects the SDK, rebuilds the player, or re-transfers the device. Once the SDK is poisoned after lockscreen/idle, the only thing that reconstructs a working session is a full page reload. The recently added **Previous** button routes straight back into the same unguarded Spotify play path, so pressing Previous after a failure re-triggers `playback_error`/`auth failed` and makes the situation worse — exactly as reported.

Importantly, the building block for a clean fix already exists: the server **does** mint a fresh token on every `/auth/token` call (`spotify.py:81-86` refreshes if expired). The page can always obtain a valid token while it is in the foreground. What is missing is the client-side step that *uses* that token to repair the SDK (reconnect → re-acquire `device_id` → re-transfer → retry) before attempting any further Spotify segment.

A second, structural finding: **the implementation drifted from the agreed decision.** `docs/strategy/lockscreen-transition-decision-brief.md` explicitly split the problem into (A) recoverability and (B) locked-screen transition, and prescribed *foreground reconciliation + Media Session controls*, with a clear instruction not to ship another timer-based "make transitions automatic while locked" patch. What actually shipped afterward was an **in-page Previous button** plus a **`setTimeout` segment-deadline watchdog** — no Media Session, no real recovery — i.e. partly the thing the decision brief warned against, and missing the thing it asked for.

**Verdict: do not roll back to `708da74`.** The resume-state, timeline/history, and previous-segment scaffolding are genuinely useful and are prerequisites for both real recovery and a future Media Session layer. The correct next step is a single **bounded recovery routine** (token refresh → reconnect/re-transfer → one retry), **health-gating** of Spotify playback and Previous, and a visible **"Recover Spotify"** affordance as the fallback. Separately, schedule Media Session as the real lockscreen-control milestone, and explicitly park "automatic transition while the screen stays locked" as not achievable in this architecture.

---

## What Was Inspected & Method

**Code (read in full / targeted):** `resonova/web/player.js` (1,219 lines, current), `resonova/web/index.html` (playback controls + cache-bust), `resonova/api/spotify.py` (token/refresh path), prior frontend.

**Docs:** `lockscreen-transition-decision-brief.md`, `mobile-playback-hardening-brief.md`, `Mobile Resume State Recovery Handoff.md`, `External Product UX Design Audit Handoff.md`, and the audit brief itself.

**Live corroboration (Claude-in-Chrome MCP, against the running `http://127.0.0.1:8765`):** loaded a saved episode; the playing state's live DOM exposes exactly three controls — *"Toggle Spotify diagnostic panel"*, *"No previous segment yet"* (Previous, `aria-disabled` on segment 1), *"Skip to next segment"*. This confirms the served asset is the current `previous-control` build and that active-screen Previous gating works as designed.

**Method limitations (honest):**
- **The lockscreen/idle failure was not reproduced by the auditor.** It only manifests on a real backgrounded mobile browser; it cannot be reproduced from a desktop Chrome session. The failure mechanism below is established by **code analysis**, corroborated by the owner's report and the prior decision brief — not by a fresh on-device capture.
- **Commit-level `git diff` inspection could not be completed** this pass (the sandbox VM that runs git was unavailable). Findings are based on the **current code state**, which is decisive for the recovery gap, plus the commit *messages* and the resume handoff for narrative. A diff pass would add history detail but would not change the conclusions.

---

## Hypothesis Verdicts

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| **H1** | SDK enters poisoned `auth_error`/`playback_error` state after lockscreen and the app records but never recovers | **Confirmed (code-level)** | `authentication_error` (`player.js:351-355`), `playback_error` (`:363-366`), `not_ready` (`:338-342`) each only set a `_lifecycle.*` field + render diagnostics. No `connect()`, token refresh, rebuild, or transfer anywhere in those paths. Reload works precisely because it reconstructs SDK/player/device. |
| **H2** | Resume/Previous restore queue state but not playback capability | **Confirmed** | Resume (`_resumePlayback`, `:166-189`) and Previous (`previous`, `:1067-1102`) rebuild `queue`/`playbackTimeline`/`currentIndex` only. Neither touches SDK/device/token health. Commentary (HTML `<audio>`) keeps working; Spotify segments fail until reload. |
| **H3** | Browser SDK is not sufficient for the lockscreen product goal | **Confirmed for *automatic transition while locked*; not the cause of the immediate failure** | The decision brief's diagnosis is correct: page JS/timers/SDK iframe messages are frozen while locked, so no `setTimeout`/`player_state_changed` patch can guarantee transitions *while still locked*. **But** the owner's actual blocker (broken music + Previous trap *after unlock/return*) is a recoverability gap that **is** fixable in-foreground. Keep these two separate. |
| **H4** | Previous is mispositioned as the recovery affordance | **Confirmed** | `previous()` (`:1067-1102`) unconditionally calls `_playNext()` → `_playSpotifyTrack()` even when the target is Spotify and the SDK is unhealthy / `deviceId` is null. It cannot recover a broken session and instead re-triggers the error. A dedicated recover/reset action is required. |

---

## Findings (ranked by severity)

### F1 · Critical · No SDK recovery on auth/playback/not_ready
The three listeners that signal a broken session do nothing but record state:
- `authentication_error` → `_lifecycle.authError = message` only (`player.js:351-355`)
- `playback_error` → `_lifecycle.playbackError = message` only (`:363-366`)
- `not_ready` → sets `this.deviceId = null` and a flag only (`:338-342`)

There is no code anywhere that, on these events, refreshes the token, calls `spotifyPlayer.connect()`, rebuilds the player, or re-transfers playback. This is the single root cause of the "poisoned until reload" behavior (H1).

### F2 · High · `deviceId` is nulled and never re-acquired; play then targets a dead/null device
`not_ready` sets `this.deviceId = null` (`:339`). `_playSpotifyTrack()` then issues `PUT /me/player/play?device_id=${this.deviceId}` (`:645`) — with `device_id=null` (or a stale id) after backgrounding. The `catch` (`:653-656`) swallows the error and calls `_playNext()`, **skipping the music** and advancing to the next commentary. Net effect matches the report: music silently unavailable after idle.

### F3 · High · Previous is a trap after failure (directly matches owner report)
`previous()` rebuilds the queue and calls `_playNext()` with no SDK-health check (`:1067-1102`). If the previous item is Spotify and the SDK is in `auth_error`/`playback_error` with `deviceId` null, it re-enters `_playSpotifyTrack()` and re-triggers the failure — producing the owner's observed `playback_error` + `auth failed` and worsening the state. Previous should be *blocked or recovery-gated* for Spotify targets while the SDK is unhealthy.

### F4 · High · Foreground reconciliation does not actually reconcile/repair
`_reconcileAfterBackground()` (`:191-219`), run on `visibilitychange→visible`, explicitly treats an existing `authError` as *"not fatal"*, logs it, and saves resume state — then only advances if the current Spotify track *appears ended*. It never refreshes the token, reconnects, or re-transfers the device. So returning to the foreground — the one moment JS is alive again and a fresh token is obtainable — does **not** heal the session. This is the highest-leverage place to add recovery, and it contradicts the decision brief's "foreground resume reconciliation so returning to the page catches up cleanly."

### F5 · Medium · Implementation drifted from the agreed decision brief
`lockscreen-transition-decision-brief.md` prescribed: (A) resume-state recovery, (B) **foreground reconciliation + Media Session next/play/pause**, and "**do not assign another 'make lockscreen transition automatic' patch without changing architecture.**" What shipped after the resume work: an in-page **Previous** control and a **`setTimeout` segment-deadline watchdog** (`_handleSpotifyStateChange`, `:675-687`). The watchdog is precisely the timer-based transition mechanism the brief warned is futile while locked (the timer is frozen with the page), and **Media Session was never added** (verified: no `mediaSession`/`MediaMetadata`/`setActionHandler` anywhere in `player.js`). The lockscreen still has no real custom controls.

### F6 · Medium · Cached-token fallback gives false protection
`getOAuthToken` caches the last token and falls back to it if the fetch fails (`:315-325`). This correctly prevents the `cb()`-never-called deadlock — a real improvement — **but** after a long idle the cached token is itself expired, so the SDK still receives a dead token and emits `auth_error`. The fallback prevents a hang, not an auth failure; it should not be mistaken for a recovery mechanism.

### F7 · Low · Spotify play failure is silent to the user
On play failure the `catch` only `console.error`s and advances (`:653-656`). The user gets no signal that music is broken and no recovery affordance — the episode just turns commentary-only. Once F1 recovery exists, this path should route to it (or to the manual Recover control) rather than silently skipping.

### F8 · Low (positive) · Server-side refresh already works — recovery is feasible without reload
`/auth/token` → `get_current_token()` refreshes an expired token server-side (`spotify.py:81-86`), provided `SPOTIFY_CLIENT_SECRET` is set (README notes it's recommended for exactly this). The client recovery routine therefore has a reliable fresh-token source; it just isn't wired into any recovery path today.

---

## Answers To The Auditor Questions

**1. When the SDK has `auth_error`/`playback_error`, what exact recovery is required before any further Spotify segment?**
A bounded, ordered routine: (a) fetch `/auth/token` to get a server-refreshed token and update `_cachedToken`; (b) ensure the SDK is connected and `ready` — try `spotifyPlayer.connect()`; if no `ready`/`device_id` arrives within a short timeout, `disconnect()` and rebuild a fresh `Spotify.Player` once; (c) on `ready`, re-transfer playback to the new `device_id` (`PUT /me/player` with `play:false`); (d) clear the `authError`/`playbackError` flags; (e) only then retry the current Spotify item. Gate every Spotify play on `deviceId != null` and no unrecovered error. One attempt — no loops.

**2. Should `previous()` avoid replaying Spotify segments while the SDK is unhealthy?**
Yes. If the target is Spotify and the SDK is unhealthy, run the recovery routine first; if it succeeds, play; if it fails, do **not** call play — surface the "Recover Spotify / Reload" affordance. Previous to a *commentary* segment is always safe (HTML `<audio>`), so it can proceed regardless.

**3. Is it viable to rebuild the Spotify Player in-page after failure without a full reload?**
Generally yes — `disconnect()` then a new `Spotify.Player(...).connect()`, await `ready`, re-transfer. Reliability on a mobile browser *that is still suspended* is not guaranteed, but on **return to foreground** it is the standard, reload-free recovery. Make it bounded (single rebuild attempt, then fall back to the manual control). Often a plain `connect()` re-acquires a device without a full rebuild; rebuild is the fallback.

**4. Should Resonova add a visible "Recover Spotify" control and/or auto-reset on `visibilitychange`?**
Yes to both, as one idempotent routine: auto-attempt recovery **once** on `visibilitychange→visible` when an error flag is set (this is where F4 should live), and expose a manual **"Recover Spotify"** button in the playing state that calls the same routine for when the auto attempt fails. Strictly bounded — no background polling, no repeated auto-retries.

**5. Should the product stop relying on the Web Playback SDK for lockscreen continuity?**
Split the answer. For **automatic segment transitions while the screen stays locked**: yes — accept this is not achievable with the Web Playback SDK in a frozen mobile tab (consistent with the decision brief); stop patching timers for it. For **foreground / unlock-and-resume playback**: keep the SDK; it works and is recoverable with F1–F4. True locked-screen continuity would require an architecture change (native app, or a single continuous audio stream — which legally/technically can't carry full Spotify tracks via the Web Playback SDK). That is an owner-level product decision, not an immediate code fix, and should be taken deliberately rather than via another patch.

---

## Recommended Next Action (bounded)

1. **Add one `_recoverSpotifySession()` routine** implementing Q1 (token refresh → connect/re-transfer → single rebuild fallback → retry current item). Idempotent, no loops.
2. **Health-gate Spotify playback**: `_playSpotifyTrack()` and `previous()`/`skip()` check `deviceId` + error flags; if unhealthy, call recovery before play.
3. **Wire F4**: make `_reconcileAfterBackground()` invoke `_recoverSpotifySession()` once when an error flag is set, instead of declaring it "not fatal."
4. **Add a visible "Recover Spotify" affordance** in the playing state as the fallback when auto-recovery fails (replaces silent skip / Previous-trap).
5. **Keep resume-state + timeline/history + the deadline watchdog** — but demote the watchdog to a *foreground catch-up only*, never the primary transition mechanism.
6. **Separately, schedule Media Session** (metadata + play/pause/next/previous handlers) as the real lockscreen-control milestone the decision brief already approved. The existing `playedItems`/`playbackTimeline`/`currentIndex` model makes `previoustrack` feasible.
7. **Explicitly park** "automatic transition while the screen remains locked" as out of scope for this architecture; route any future request for it into the architecture-options decision, not another timer patch.

**On rollback:** not recommended. Rolling back to `708da74` would discard the resume/timeline/previous work that the recovery and Media Session milestones both depend on, without fixing the underlying recovery gap (which `708da74` also lacked).

---

## Do-Not-Do List (avoid another patch spiral)

- **Do not** add polling loops, retry storms, or repeated auto-recovery attempts. Recovery is a single bounded attempt, then a manual affordance.
- **Do not** add more `setTimeout`/`player_state_changed` watchdogs as a *primary* transition mechanism — they are frozen while the screen is locked (per the decision brief).
- **Do not** keep Previous as the recovery path; it must be health-gated.
- **Do not** roll back the resume-state / timeline / previous-segment work.
- **Do not** treat the cached-token fallback as recovery — it prevents a hang, not an auth failure.
- **Do not** ship another "make lockscreen transitions automatic" attempt without an explicit architecture change decision.
- **Do not** add a native app / PWA inside this fix; that is a separate, owner-level decision.
- **Do not** expose `.env`, Spotify tokens, or secrets.

---

## Evidence Index

| Claim | Evidence |
|---|---|
| No recovery on SDK errors | `player.js:338-342` (`not_ready` nulls deviceId), `:351-355` (`auth_error` records only), `:363-366` (`playback_error` records only) |
| Play targets null/stale device, silently skips | `player.js:608-657` (esp. `:645` device_id, `:653-656` catch→`_playNext`) |
| Previous re-enters broken Spotify path | `player.js:1067-1102` |
| Foreground reconcile doesn't repair | `player.js:191-219` (auth_error "not fatal", no token/connect/transfer) |
| Timer watchdog (frozen while locked) | `player.js:675-687` |
| No Media Session anywhere | absence of `mediaSession`/`MediaMetadata`/`setActionHandler` in `player.js` (full read) |
| Cached-token fallback (hang fix, not auth fix) | `player.js:315-325` |
| Server refreshes token (recovery feasible) | `spotify.py:76-86` |
| Previous/Skip + cache-bust in DOM | `index.html:294-310`, `:333` (`?v=20260620-previous-control`) |
| Served code is current build (live) | Chrome-MCP playing-state DOM: Diag + "No previous segment yet" + "Skip to next segment" |
| Prior agreed direction | `lockscreen-transition-decision-brief.md` (Problem A/B split; Media Session + foreground reconciliation; no more auto-transition patches) |

Commits named in the brief (messages, not diff-verified this pass): `7ab5614` harden lockscreen, `708da74` document limitation, `e636f29` add previous control, `0c3e731` add resume recovery, `fdfb05b` fix previous state, `98ae62d` harden previous.

---

## Areas Not Tested

- **On-device lockscreen reproduction** — not performed (requires a real backgrounded phone; not reproducible on desktop). The failure mechanism is established by code analysis + owner report. To capture it directly: on the phone via `https://buttking.tail15ea24.ts.net:8765`, start an episode, enable Diag, lock the phone through a Spotify segment, return, and record `auth_error`/`playback_err`/`ready`/`device_id`/`not_ready` before and after pressing Previous.
- **Commit-level `git diff`** — not completed (git sandbox unavailable this pass); current code state was used instead.
- **Server-start / 502 environment risk** — the brief notes Tailscale returns 502 if the backend isn't listening; confirm `uv run resonova` is running before any mobile test. (Local server was reachable during this audit.)
- **Whether token refresh succeeds without `SPOTIFY_CLIENT_SECRET`** — not verified; if the secret is unset, server-side refresh (F8) may fail and recovery would need re-auth. Worth confirming the secret is present before relying on reload-free recovery.

## Constraint Compliance

No code implemented, no commits, no `.env`/token values read or printed, product identity unchanged, no rewrite recommended, and verified facts (code/line evidence, live DOM) are separated from the one item that depends on on-device behavior (flagged as not reproduced).
