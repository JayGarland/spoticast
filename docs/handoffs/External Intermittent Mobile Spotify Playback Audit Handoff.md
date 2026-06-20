# External Intermittent Mobile Spotify Playback Audit Handoff

Created: 2026-06-20
Owner: Chef/Codex gate
Audience: External product/implementation auditor
Repo: `F:\GitHub\resonova`

## Purpose

Audit the remaining intermittent mobile Spotify playback failures before any more implementation patches are assigned to a manager.

Do not implement code in this pass. This is an evidence audit and architecture recommendation pass.

## Current Product Context

Resonova generates a podcast-like listening session from Spotify playlist tracks:

- AI commentary segments are generated as local audio files.
- Music segments are played through Spotify Web Playback SDK / Spotify Connect.
- Mobile access currently runs over HTTPS through Tailscale Serve.
- The product is usable, but Spotify music segments still intermittently halt or require recovery on mobile.

The customer impact is no longer total failure, but it is still serious:

- Sometimes a music segment starts, then stalls at the beginning.
- Sometimes "Recover Spotify" appears and works.
- Sometimes recovery appears again and does not resolve the segment.
- Sometimes Previous/Next can recover.
- Sometimes the user must reload the page, losing flow.
- The UI does not clearly distinguish "network offline", "Spotify device missing", "SDK not ready", "play command accepted but no state", or "auth/session stale".

## Current HEAD And Recent Playback Commits

Current HEAD when this handoff was written:

```text
916ca16 Update Gemini script model to 3.5 Flash
1a9d26f Wait for Spotify Connect device before playback
028facc Treat missing Spotify state as blind playback
a0ceed6 Verify Spotify playback starts after recovery
20db310 Retry Spotify playback after stale device
ccdb343 Clarify Spotify generation errors
a867fec Add now playing trail and media controls
5bb49fc Improve episode library navigation and model defaults
98d6b4c Add saved cast management and replay variety
b92c73f Normalize commentary loudness
```

Important: several recent commits are incremental playback recovery patches. The audit should verify whether they form a coherent state machine, or whether they are masking the same underlying Spotify Connect lifecycle problem.

## Files To Inspect

Core playback:

- `resonova/web/player.js`
- `resonova/web/index.html`
- `resonova/web/styles.css`

Spotify server/client integration:

- `resonova/api/spotify.py`
- `resonova/server.py`
- `resonova/config.py`

Relevant prior reports:

- `docs/handoffs/External Mobile Playback Implementation Audit Report.md`
- `docs/handoffs/Spotify SDK Foreground Recovery Implementation handoff.md`
- `docs/handoffs/Tailscale HTTPS for Mobile Spotify SDK Handoff.md`
- `docs/handoffs/Mobile Lockscreen Playback Hardening Handoff.md`
- `docs/handoffs/Mobile Resume State Recovery Handoff.md`
- `docs/handoffs/Mobile Spotify SDK Lifecycle Diagnosis Handoff.md`

## Latest Customer Reports To Explain

Observed on real mobile device:

1. Music segment begins, then halts near the start.
2. Diagnostic panel can show:
   - `ready: yes`
   - `Device ID: yes`
   - `SecureCtx: true`
   - `playback_err: Device playback endpoint returned 404`
   - sometimes full Spotify error body: `Device not found`
3. Another observed diagnostic:
   - `playback_err: Spotify SDK did not report playback after play command`
4. Recovery button may appear:
   - sometimes resolves
   - sometimes returns to recovery state again
5. Previous/Next can sometimes recover but not reliably.
6. UI does not show loading/offline/network state; it appears to simply stop.

## Audit Questions

Answer these with code evidence and, if possible, live browser inspection.

1. Does the current `player.js` have one coherent Spotify playback state machine, or multiple overlapping recovery paths?
2. When `/v1/me/player/play?device_id=...` returns 404 `Device not found`, does the client invalidate the stale device ID before retrying?
3. Does recovery rebuild the SDK player, wait for a new `ready` device ID, transfer playback, and only then retry play?
4. Does the code distinguish these states in UI:
   - browser offline
   - token fetch failed
   - Spotify SDK not ready
   - Spotify Connect device stale/missing
   - play command accepted but no SDK state reported
   - playback genuinely in progress but SDK state unavailable
5. Is there any explicit instrumentation for:
   - `navigator.onLine`
   - `online` / `offline` events
   - failed `fetch()` calls to Spotify and local `/auth/token`
   - device ID age / generation count
   - visibility/pagehide/pageshow transition timing
6. Does `Recover Spotify` retry forever, retry once, or follow a bounded backoff?
7. Does the app risk advancing the queue while Spotify has not actually started audible playback?
8. Are Previous/Next guarded against entering a known-bad Spotify segment repeatedly?
9. What minimum instrumentation should be added before another real fix?
10. What UX fallback should exist when Spotify is temporarily unavailable?

## Expected Output

Produce an audit report at:

`docs/handoffs/External Intermittent Mobile Spotify Playback Audit Report.md`

The report should include:

- Verdict: pass / partial / fail for current recovery architecture.
- Severity-ranked findings with exact file/line references.
- One likely root-cause tree, not a list of unrelated guesses.
- Evidence required from the real phone for the next test.
- A bounded implementation brief for RUG, if implementation is justified.
- A do-not-do list to avoid another timer/retry patch that hides the state problem.

## Strong Initial Hypothesis

The app is now past the "HTTPS / SDK ready" failure stage. The remaining failures look like stale Spotify Connect device lifecycle plus insufficient state separation:

- the SDK can be ready at one moment,
- the device can become invalid/stale,
- `/me/player/play` can return 404 Device not found,
- recovery may still retry against a stale device or rebuild without strongly invalidating old state,
- the UI then shows generic playback failure instead of a precise recoverable state.

Validate or reject this hypothesis with code evidence.

## Parked Work: Cast Cache / Loaded Cast Management

Do not audit or implement cast cache in this report except to note separation of concerns.

The next manager task after playback audit should define user-facing loaded-cast management:

- cached/saved casts visible by playlist
- multiple runs from the same playlist distinguishable by run number, date/time, track count, and first few tracks
- explicit actions: Play, Resume, Rename, Delete, Regenerate, Refresh playlist snapshot
- clear difference between replaying an existing cast and generating a new one

That should be handled by RUG as a product/UX implementation task after the playback audit.
