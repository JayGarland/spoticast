# Product Baseline / Release-Readiness Review

Audience: Boss + Chef
Created: 2026-06-21
Author role: Internal Auditor / Product Reviewer (inspect-only)
Status: inspect-only deliverable — no code changed, no commits, no implementation approved, no release decision made
Scope source: boss/chef review request "Review Resonova's current product baseline and release readiness"

---

## Executive Summary

Resonova's engineering baseline is **stronger than the older audits suggest**, and several stale findings are now false in current source. Media Session, in-app Previous/Pause/Next transport controls, a now-playing mini-trail with return-to-player, unfinished-episode resume, offline/bad-network resilience, an observability ring buffer with a Diag panel and Copy-Timeline, and a saved-cast library with run numbers, order fingerprints, and rename/delete are all present and wired in current code. As a **developer-stage** product the core loop (connect → generate → listen → replay) works and feels coherent.

The top blocker has **shifted**. It is no longer "playback has no controls." The two dominant gaps now are (1) the **access/onboarding model does not match the stated v0.1 direction** — current reality is clone + `.env` + local server + Gemini key + ffmpeg, while v0.1 is supposed to be "connect Spotify and use directly," and (2) a **memory/learning promise the product does not yet deliver** (landing and README claim listening memory and hosts that "learn your taste," but generation is effectively stateless). Behind those sit one real user-facing playback defect (blind playback) and one data-integrity bug (shared outro path on replay).

My judgment: **good developer-stage baseline; not yet ready for a normal (non-owner) v0.1 user.** The gap between "now" and "v0.1" is mostly a *product/access decision plus an honesty fix*, not a reliability collapse. The single most useful next step is a boss-chef decision on v0.1 access shape, run in parallel with a small, cheap correctness/honesty bundle — not another speculative mobile-recovery cycle.

This review is inspect-only. Everything below is a finding or recommended next step, not an implementation or a release decision.

---

## Current Product Journey (verified in source)

**Connect.** Unauthenticated users see the landing state (`index.html` `#state-landing`) with a "Connect Spotify" link to `/auth/spotify`. OAuth runs through `server.py` (`/auth/spotify`, `/auth/callback`, PKCE; Tailscale `.ts.net` hosts get an HTTPS redirect for mobile). On success the user lands in the connected state.

**Generate.** The connected state (`#state-connected`) offers a playlist/URI/track-paste textarea, an optional Last.fm widget (only shown if server reports keys present), and library shelves (Past Episodes, Recently Played, Your Playlists). Submitting calls `POST /generate`, which starts a background job (`_run_generation`) and streams SSE progress. The UI shows a four-step generating state (fetch → research → script → tts) and lets the user background it ("← Back · generating in background").

**Listen.** Generation streams the intro as soon as it is synthesized (`intro_ready`), then each track's commentary + Spotify segment (`track_ready`), then the outro. The player (`player.js`) interleaves HTML `<audio>` commentary with Spotify Web Playback SDK music, crossfading at boundaries. The playing state has segment-type indicator, now-playing text, waveform, Previous/Pause/Next, contextual Skip-Music and Recover-Spotify buttons, and an episode progress bar.

**Replay.** Episodes persist (`episodes_store.save_episode`) and render in Past Episodes grouped by playlist, with Run #, an 8-char order fingerprint, track preview, and Play/Rename/Delete. Replay (`_playEpisode`) loads the saved queue (`GET /api/episodes/{id}`) with a localStorage fallback for offline. A memory-aware variety layer (`variety_store`) varies track order across re-generations of the same playlist.

---

## Release-Readiness Findings (severity-ranked)

Ordered by risk to a **v0.1 normal user**, per the stated product direction.

| # | Sev | Finding | Evidence | Impact | Recommended next step (no build approved) |
|---|-----|---------|----------|--------|-------------------------------------------|
| R1 | **High (v0.1 blocker)** | **Access model contradicts the v0.1 direction.** Current product requires clone, `.env`, local server, developer-managed Gemini key, and ffmpeg. v0.1 direction is "connect Spotify → generate → listen, no server/keys." The landing page even instructs end users to `brew install ffmpeg`. | `README.md` setup (steps 1–5, `.env`, `make run`); `index.html:99` landing prereq shows ffmpeg/brew to the user; `release-access-and-memory-positioning-brief.md` (v0.1 = no keys, no server). | This is the structural gap between "developer-stage" and "v0.1 normal user." Cannot put in front of a non-owner user as-is. | **Boss-chef decision, not a build.** v0.1 release/access architecture (hosting, account, key-handling, storage) is explicitly parked pending discussion. Flagging as the dominant blocker; recommending it go on the next boss-chef agenda. |
| R2 | **High (trust)** | **Product promises memory/learning it does not deliver.** Landing tagline "Listening memory," feature "Two AI hosts learn your taste," README "grows with your listening history." Generation is effectively stateless — no persistent taste profile is read or written. | `index.html:79` (tagline "Listening memory"), `:84` ("Two AI hosts learn your taste"); `README.md:1,3`; `persistent-profile-feedback-brief.md` ("each generation is mostly stateless", profile not built); no `taste_profile`/profile read anywhere in `server.py` generation pipeline or `gemini` context build. | First-session users are told the system remembers/learns them; it doesn't yet. Direct honesty/trust risk and the clearest "this is overselling" signal. | **Cheap to resolve two ways:** soften landing/README copy now to match reality, *or* sequence the already-designed persistent profile so the claim becomes true. Either is fine; the mismatch is the problem. Not a build approval — recommendation only. |
| R3 | **High** | **"Blind playback" still trusts the play command without confirming audio advanced.** `_waitForSpotifyPlaybackStart` returns success on a single `currentUri === uri && !state.paused` check (no position-advance verification); on failure the code arms a `duration_ms`-based blind deadline and presents a possibly-silent track as playing. | `player.js:870-884` (`_waitForSpotifyPlaybackStart`), `1180-1216` (blind branch + retry), `1230-1244` (`_setBlindSpotifyDeadline`). Verified present in current source. | A user can hear a full track of silence while the UI says "playing" — the most likely "the app is broken" report. Matches prior trial F1 and the chef gate's validated finding. | Capture a real-phone Diag timeline first (observability now supports it), then require position to advance across ≥2 samples before declaring start. Verification + a bounded brief — not approved here. |
| R4 | **Med** | **Outro audio is written to a shared `/audio/outro.mp3`, so replaying an old episode can play the newest outro.** Per-track/intro audio is saved under the episode dir, but the outro is not. | `server.py:430-433` (`assemble_commentary(..., "outro.mp3")` and `saved_queue.append({"url": "/audio/outro.mp3"})`); intro/track use `ep_dir` (`:393,:409`). Confirms `attention-board-next-moves-brief.md` correctness note. | Data-integrity/replay bug: saved episodes don't replay their own outro after a newer generation overwrites the shared file. Quiet but real. | Small correctness fix: write outro inside the episode folder like intro/tracks. Fits the brief's "small correctness/polish bundle." Not patched here. |
| R5 | **Med** | **Onboarding copy is macOS-centric and exposes dev plumbing.** Paste hint uses ⌘A/⌘C only; landing shows `brew install ffmpeg`. Owner runs Windows. | `index.html:99,162-163`; `README.md:38,40` (brew-only). | Windows owner / future contributor / any non-Mac user hits wrong shortcuts and a mac-only dependency hint. Trust leak and a real setup wall. | Add Windows/cross-platform copy; remove end-user-facing ffmpeg hint from the landing (it's a dev concern). Docs/copy only. |
| R6 | **Med** | **No automated tests on the highest-risk surfaces.** Only `tests/test_variety_episodes.py` exists; nothing covers `player.js`, the Spotify recovery/playback logic, or `server.py` endpoints. | `tests/` contains only `test_variety_episodes.py` (+ `__pycache__`). | The most-edited, most-fragile code (player + endpoints) has no regression net; every playback change is validated by manual phone testing only. | Add a thin server-endpoint smoke test (episodes list/get/rename/delete, auth status) and a small JS harness for queue/health logic. Medium; after R1–R4 direction is set. |
| R7 | **Low** | **Developer jargon surfaces in user-facing UI.** Order-fingerprint badge (8-char hash) and recovery/diagnostic labels ("Recover Spotify", "Reload Player", "Diag") read as developer tooling. | `player.js:1594-1596` (fingerprint badge), `:263-281` (recovery labels), Diag panel `:1351-1385`. | Fine for owner stage; would confuse a normal v0.1 user. Diag is correctly behind a toggle, so low risk. | Park the fingerprint badge / Diag visibility behind a "developer mode" before v0.1 exposure. Polish. |
| R8 | **Low** | **No `prefers-reduced-motion` handling.** The landing (40 bars) and player (36 bars) waveforms animate continuously with no reduced-motion fallback. | `styles.css` has zero `prefers-reduced-motion` rules (grep); animated `.waveform-bar` markup in `index.html`. | Minor accessibility/battery gap; not user-blocking. | Add a reduced-motion media query when doing the copy/polish bundle. Low. |

---

## What Is Already Good Enough (for a developer / owner stage)

Verified present and coherent in current source — these refute the stale audits:

- **Transport controls + Media Session.** `_initMediaSessionHandlers` wires play/pause/next/previous; `_updateMediaSession` sets `MediaMetadata`; in-app Previous/Pause/Next buttons exist and are wired (`player.js:401-428, 307-361, 1970-2033`; `index.html:319-356`). Older "no Media Session / no controls" findings are **stale**.
- **Now-playing trail + return-to-player.** Mini panel shows segment type/title/progress in the library and returns to the player (`index.html:168-181`, `player.js:1762-1808, 2209-2212`).
- **Resume unfinished episode.** localStorage resume state with a 30-minute TTL and a resume card (`player.js:446-553, 633-641`).
- **Offline / bad-network resilience.** Network status banner, online/offline listeners, offline episode-cache rendering, cached Spotify metadata, contextual Skip-Music fallback (`player.js:79-101, 2090-2121, 1469-1539`; `index.html:23-24`).
- **Observability.** Ring buffer of lifecycle/network/playback events, Diag panel, Copy-Timeline export (`player.js:71-107, 1290-1409`).
- **Spotify recovery with escalation.** Single auto-recovery, rebuild-once, Connect-visibility wait, and a reload recommendation after repeated failure (`player.js:167-300`).
- **Saved-cast library.** Grouping by playlist, run numbers, order fingerprints, track preview, rename/delete, focus-after-generation (`player.js:1469-1650`; `server.py:203-242`).
- **Streaming generation.** Intro plays before the full episode is synthesized (`server.py:392-433`).
- **Memory-aware replay variety.** `variety_store` varies order across regenerations and persists after successful save (`server.py:103-105, 447-449`).

This is a real, working MVP for the owner. None of it is "release-ready for a normal v0.1 user" only because of R1/R2 above, not because the feature set is thin.

---

## What Blocks v0.1 Confidence (for a normal, non-owner user)

In priority order:

1. **R1 — access/onboarding model.** A normal user cannot clone a repo, write `.env`, run a server, and supply a Gemini key. Until the v0.1 access shape is decided, there is no path to put this in front of a non-owner. This is a **decision blocker**, not a code blocker, and it is the real top blocker today.
2. **R2 — memory promise vs. delivery.** Shipping copy that claims memory/learning the product doesn't have undermines the product's own differentiator (inspectable memory) on first contact. Solvable cheaply by honesty or by shipping the minimal profile.
3. **R3 — blind playback.** A user-facing "silent track while UI says playing" defect in the core loop. High, but second-tier to R1/R2 for *v0.1 confidence* because it needs real-phone evidence to fix correctly.
4. **R4 — shared outro on replay.** Real data-integrity bug; low blast radius but easy to fix and worth clearing before wider exposure.

Everything else (R5–R8) is polish/quality, not a v0.1 confidence blocker.

---

## Direct Answers To The Review Questions

1. **User journey (connect→generate→listen→replay):** Works end-to-end in current source; see "Current Product Journey." Coherent for the owner.
2. **Release-ready for a developer-stage product:** The whole playback/controls/library/observability/offline/resume stack (see "What Is Already Good Enough"). Genuinely solid.
3. **Blocks v0.1 confidence for a normal user:** R1 access model (top), R2 memory-honesty, R3 blind playback, R4 outro replay bug.
4. **Is playback reliability still the top blocker?** **No — it has shifted.** Controls, Media Session, recovery, and observability landed. The top blocker is now the **access/onboarding mismatch (R1)** plus **memory-promise honesty (R2)**. Playback reliability (R3 blind playback) is a high but no-longer-#1 blocker, and is pending real-phone evidence.
5. **Does the product promise memory/learning it doesn't deliver?** **Yes (R2).** Landing + README promise listening memory and hosts that learn; generation is stateless and no persistent profile exists.
6. **Is the absence of persistent profile/feedback a blocker, a trust risk, or the next feature?** It is a **product-trust risk now and the next feature — but not an inherent release blocker by itself.** The blocker is the *mismatch* between promise and delivery, which can be closed either by softening copy now or by shipping the minimal profile. The profile work itself is design-ready (`persistent-profile-feedback-brief.md`) and should follow the copy/access decision, not precede it.
7. **Does onboarding/copy match reality and the v0.1 direction?** **Partially, no.** Mismatches with reality: ffmpeg/brew shown to users, mac-only ⌘ shortcuts (owner is on Windows), memory claims unfulfilled. Mismatch with v0.1 direction: landing implies direct use while the actual flow is developer-stage.
8. **Are controls / replay-library / diagnostics / mobile understandable to a real user?** Controls and replay/library are clear and well-labeled (minor jargon: fingerprint badge, "Reload Player"). Diagnostics are explicitly developer tooling but correctly gated behind a toggle. Mobile has the right primitives (transport + Media Session) but still carries the blind-playback risk and Spotify-segment lockscreen limitation; **not live-tested in this review** (see Areas Not Tested).
9. **What should be fixed before profile/feedback work?** Decide R1 (access shape, boss-chef), fix R2 (copy honesty — cheap), fix R4 (outro path), verify R3 (blind playback) with a real-phone timeline, and clean R5 (cross-platform copy). These are the attention board's "observability + small correctness/polish" lane; profile/feedback should follow.
10. **What should stay parked?** Billing/subscriptions, cloud accounts / hosted-memory storage, multi-source expansion, PWA/native, interactive hosts (all per briefs); plus health-state-machine consolidation, adaptive timeouts (until phone data), per-play device round-trip optimization, favicon, and flow-aware ordering (until a profile exists).

---

## Recommended Next Move (recommendation only — no decision made here)

1. **Put v0.1 access shape (R1) on the next boss-chef agenda.** It is the true blocker between "now" and "v0.1" and is a product/architecture decision, not an implementation task. No hosting/billing/account build is recommended here.
2. **In parallel, a small low-risk correctness/honesty bundle:** copy honesty (R2), outro path (R4), cross-platform onboarding copy (R5). Cheap, high trust-per-effort, well-evidenced. Scope it tightly so it doesn't become a UI sweep.
3. **Then blind-playback verification (R3):** capture one real-phone Diag/Copy-Timeline of the stall before writing any more recovery code; the observability layer exists precisely for this.
4. **Persistent profile/feedback design is ready to route** (`persistent-profile-feedback-brief.md`) but should follow the copy/access decision so the memory promise and the memory feature land together.

Sequencing and approval are the chef's/boss's call; this is the auditor's recommended ordering by evidence.

---

## Evidence References

**Verified directly from current source this pass (file tools):**

- Journey/states/controls/copy: `resonova/web/index.html` (landing `:31-101`, connected `:107-208`, generating `:213-252`, playing `:257-372`, served build `player.js?v=20260621-library-refresh` `:379`).
- Player behavior: `resonova/web/player.js` — Media Session `:401-428`; transport `:307-361, 1970-2033`; blind playback `:870-884, 1180-1244`; recovery `:167-300`; observability/Diag `:71-107, 1290-1409`; resume `:446-553`; offline/network `:79-101, 2090-2121`; library/replay/rename/delete `:1469-1671`; now-playing trail `:1762-1808`.
- Backend: `resonova/server.py` — generation pipeline `:312-458`; **outro shared-path bug `:430-433`**; episode CRUD `:203-242`; variety `:103-105, 447-449`.
- Tests: only `tests/test_variety_episodes.py`.
- No `.gitattributes`; no `prefers-reduced-motion` rules in `styles.css`.

**Strategy/positioning anchors (read, not re-derived):**

- `docs/strategy/attention-board-next-moves-brief.md`, `release-access-and-memory-positioning-brief.md`, `persistent-profile-feedback-brief.md`, `resonova-market-benchmark.md`, `README.md`.

**Verified facts vs. assumptions:**

- *Verified:* every R1–R8 code/copy claim cites a current file:line read this pass. Stale-audit reversal (Media Session/transport now present) is verified in source.
- *Assumption / not verified:* real-phone intermittent Spotify behavior (R3) — not reproduced; rests on code + prior reports. TTS/Spotify in-browser audio quality not re-measured (no live session). Mobile lockscreen behavior not observed live.
- *Explicitly not re-litigated:* repo-wide line-ending/CRLF state. The bash sandbox mount returned a stale/partial copy (wrong line count, false syntax error, git index-lock errors), so I make **no git/process verdict** here — consistent with the chef gate's instruction that line-ending hygiene is a separate, deliberate chef/boss action.

---

## Areas Not Tested

- **No live app run.** I could not launch or interact with the running app this session; all findings are from source + docs. Dynamic behavior (actual audio, crossfade timing, real OAuth, real Spotify playback) is inferred from code, not observed.
- **No real-phone testing.** Mobile background/lockscreen/bad-network behavior (R3, timeouts) not reproduced — same hardware limitation noted in prior audits.
- **No git/CI/sandbox validation.** The bash mount was unreliable this session; I did not run `node --check`, tests, or git diff as authoritative. Re-run these in a clean environment before any commit.
- **Did not re-read every individual mobile handoff** (≈20 exist). I verified their claims against current source directly rather than trusting the handoffs, and cross-referenced the four required briefs.
- **Market benchmark not redone** (per constraint); used only as positioning context.

---

## Self-Note On Constraints Honored

Inspect-only: no code patched, no files edited except this report, no commit, no PR, no release decision, no manager-work approval. Parked items left parked (no billing/cloud/multi-source/PWA/native/interactive-host recommendations beyond "keep parked"). Self-hosting is treated as the current developer constraint, not the v0.1 promise. Findings separate verified current facts from assumptions, and stale audit claims were checked against current source rather than assumed true.
