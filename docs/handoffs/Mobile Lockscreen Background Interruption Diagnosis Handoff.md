# Mobile Lockscreen Background Interruption Diagnosis Handoff

## Purpose
After HTTPS fixed the Spotify SDK registration on mobile (SecureCtx=true, ready=yes, device_id present), two new symptoms appeared: (A) auth can show failed when returning to page after phone locks, and (B) segment transitions interrupt while phone is locked. This handoff diagnoses the root causes and recommends the smallest safe fix path.

## Root Cause Summary

Resonova has zero awareness of mobile page lifecycle. There is no `visibilitychange`, `pagehide`, Media Session API, Wake Lock API, or AudioContext usage. All playback timing relies on `setTimeout`/`setInterval` (throttled to ≥1000ms in background) and the Spotify SDK's `player_state_changed` event (not delivered when the page is frozen).

The two symptoms arise from 5 distinct failure modes:

| # | Failure Mode | Symptom | Severity |
|---|---|---|---|
| 1 | Token refresh fetch fails during page freeze | Auth shows failed on return | Critical |
| 2 | `player_state_changed` event silently dropped | Segment transition stalls | Critical |
| 3 | Track-end detection condition too brittle | Segment transition stalls | High |
| 4 | Crossfade timeout ballooning (1.8s → 20+s) | Long silence between segments | High |
| 5 | SSE connection orphaned during generation | Queue incomplete (edge case) | Medium |

## Failure Mode 1: Token Refresh Fetch Fails During Page Freeze

**Symptom**: Auth shows failed when user unlocks phone and returns to page.

**Root cause**: `getOAuthToken` callback (player.js line 120-123) calls `_apiFetch('/auth/token')` to get a fresh token. When the phone is locked, iOS Safari suspends JS execution and network requests. The `fetch()` throws or never resolves, so `cb(token)` is never called. The SDK receives no token and fires `authentication_error`.

**Platform**: Primarily iOS Safari. Android Chrome throttles but typically doesn't fully suspend fetch.

**Evidence path**: `player.js:120-123` → `_apiFetch('/auth/token')` fails → `cb()` never called → `player.js:153-156` `authentication_error` fires → `_lifecycle.authError` set.

**Fix (~8 lines)**: In `getOAuthToken`, cache the last known token from initial fetch. On fetch failure, call `cb()` with the cached token (even if potentially stale) so the SDK always receives a token. The SDK will retry `getOAuthToken` if the token is actually rejected.

## Failure Mode 2: player_state_changed Event Silently Dropped

**Symptom**: Music stops, queue stalls, no forward progress after phone lock.

**Root cause**: The Spotify Web Playback SDK runs in a cross-origin iframe. When the parent page is frozen (iOS) or severely throttled (Android), the SDK's `postMessage`-based event delivery to `player_state_changed` (player.js line 170-172) is never dispatched. The track-end detection in `_handleSpotifyStateChange` (line 460) has no fallback — if the event never fires, `_playNext()` is never called.

**Platform**: iOS: severe (events dropped entirely). Android: moderate (throttled but eventually delivered).

**Evidence path**: `player.js:170-172` listener registered → SDK fires event internally → parent event loop frozen → event lost → `player.js:460` condition never evaluated → queue stalls.

**Fix (~5 lines, shared with FM3)**: Add a single `setTimeout` watchdog in `_playSpotifyTrack()`: `duration - 2000ms`. When it fires, if the same Spotify item is still current and `_trackEndFired` is false, call `_playNext()` directly. This is a deadline, not a retry loop.

## Failure Mode 3: Track-End Detection Condition Too Brittle

**Symptom**: Track finishes but queue doesn't advance — condition silently fails.

**Root cause**: The three-part condition at `player.js:460` — `paused && position === 0 && track_window.previous_tracks.length > 0` — requires exact concurrence of state values. In background/throttled conditions, the SDK may report `position` as a small non-zero value (e.g., 53ms due to timing granularity) or `paused` may transiently be false. A single deviation causes silent failure. No secondary timer-based dead-man's-switch exists.

**Platform**: Both iOS and Android.

**Evidence path**: `player.js:460` single gate → any deviant value → condition fails → `_trackEndFired` stays false → queue stalls permanently.

**Fix**: Same as Failure Mode 2 — the duration-based deadline watchdog covers both the "event never arrives" case and the "event arrives but condition fails" case.

## Failure Mode 4: Crossfade Timeout Ballooning

**Symptom**: 20+ seconds of silence between segments when phone is locked.

**Root cause**: `_fadeSpotifyVolume` (player.js lines 824-832) performs an async volume ramp in 20 discrete steps using `setTimeout`-based promises. With `_CROSSFADE_MS = 1800`, each step is 90ms. In background, `setTimeout` is clamped to ≥1000ms by both iOS Safari and Android Chrome. The 20-step fade balloons from 1.8s to 20+ seconds. During this entire window, `_playNext()` has not yet been called.

**Platform**: Both iOS and Android, equally severe.

**Evidence path**: `player.js:824-832` 20 steps × 90ms → in background, each step ≥1000ms → 20+ seconds → `player.js:396` `_playNext()` delayed by 20+ seconds.

**Fix (~3 lines)**: Compute step count dynamically: `Math.min(20, Math.ceil(durationMs / 1000))`. In background (each step ≥1000ms), the fade completes in at most `durationMs` wall-clock time. Or set a maximum wall-clock deadline: if the fade hasn't completed within `_CROSSFADE_MS * 1.5`, force-complete it.

## Failure Mode 5: SSE Connection Orphaned During Generation (Edge Case)

**Symptom**: Episode generation was in progress when phone locked — queue ends up incomplete.

**Root cause**: The `EventSource` for `/jobs/{job_id}/stream` auto-reconnects on connection loss, but only when the page event loop is running. On iOS Safari, when the page is frozen, the EventSource connection is terminated at TCP level and no reconnection is attempted until foreground. If the server process restarts during the freeze, all in-memory job state is lost permanently.

**Platform**: iOS: moderate risk (server restart makes it permanent). Android: low risk.

**Evidence path**: `player.js:246` EventSource → page frozen → TCP connection lost → no reconnection → server may restart → `server.py:39-69` in-memory job state lost → `done` event never received.

**Fix (~4 lines)**: Add a `_generationComplete` timeout: if `_generationComplete` is still false 60 seconds after the last SSE event, force it to true and log a warning. This prevents the 300ms polling loop in `_playNext` from running forever.

## Symptom → Failure Mode Mapping

```
Symptom A (auth shows failed):
  └── Failure Mode 1 (PRIMARY)

Symptom B (segment transition interrupts):
  ├── Failure Mode 2 (PRIMARY — event dropped)
  ├── Failure Mode 3 (CONTRIBUTING — condition brittle)
  ├── Failure Mode 4 (CONTRIBUTING — fade ballooning)
  └── Failure Mode 5 (EDGE CASE — SSE orphan)
```

## Diagnostic Test Cases

### Test A-1: Confirm Token Refresh Failure
- Start an episode. Observe diagnostics overlay.
- Lock phone. Wait 2 minutes. Unlock and return to page.
- Check: `auth_error` field in diagnostics. If non-empty, FM1 confirmed.
- Also: Is the landing page showing? If so, `/auth/token` returned unauthenticated.

### Test A-2: Server-Side Token Health
- While playing on mobile, run: `curl -s https://<host>/auth/token`
- Verify `authenticated: true`
- Lock phone 5 minutes, run same curl.
- If now unauthenticated, server-side refresh is failing.

### Test B-1: Confirm Event Drop During Lock
- Temporary: add `console.log('[DIAG] state_change', Date.now(), state)` at top of `_handleSpotifyStateChange`.
- Note timestamp when Spotify track starts. Lock phone. Wait past track duration. Unlock.
- Check: was `player_state_changed` fired for track-end while locked? If NOT, FM2 confirmed.

### Test B-2: Measure Crossfade Duration in Background
- Temporary: add timing around `_fadeSpotifyVolume`: `const start = Date.now(); ... console.log('fade took', Date.now() - start)`.
- Start episode. Immediately lock phone. Wait 30 seconds. Unlock.
- If fade took >> 1800ms (e.g., 20000+), FM4 confirmed.

### Test B-3: Track-End Condition Fragility
- Temporary: add `console.log('end-check:', {paused, position, prevCount})` before the condition in `_handleSpotifyStateChange`.
- Play through several Spotify segments normally (foreground).
- Does `position` ever report non-zero on the event that should trigger transition? If yes, FM3 is live.

## Recommended Implementation Path

**Principle**: Prevention and graceful handling. No retry loops, no recovery spaghetti. All fixes are single-file changes to `player.js` only.

### Phase 1: Prevent Auth Failure (~8 lines, player.js)
Cache last-known token from initial fetch. On `getOAuthToken` fetch failure, call `cb()` with cached token.

### Phase 2: Duration-Based Dead-Man's-Switch (~5 lines, player.js)
Single `setTimeout` watchdog in `_playSpotifyTrack()`: `duration - 2000ms`. Fires `_playNext()` if track should have ended. Covers FM2 + FM3.

### Phase 3: Cap Fade Steps (~3 lines, player.js)
Dynamic step count in `_fadeSpotifyVolume`: `Math.min(20, Math.ceil(durationMs / 1000))`. Covers FM4.

### Phase 4 (Optional): SSE Resilience (~4 lines, player.js)
Timeout: if `_generationComplete` false 60s after last SSE event, force true. Covers FM5.

**Total: ~20 lines across 1 file. No new dependencies. No behavior changes to foreground playback.**

## What NOT to Do
- Do NOT add `visibilitychange`/`pagehide` listeners — this is the retry/recovery anti-pattern
- Do NOT add `navigator.wakeLock` — Android-only, requires user gesture, drains battery
- Do NOT add exponential-backoff retry loops
- Do NOT refactor track-end detection into timer-based polling
- Do NOT add complex state machines for background/foreground transitions

## Research Findings (Reference)

Complete code trace of relevant paths:

### Auth/Token Flow
- Auth: `GET /auth/spotify` → Spotify OAuth → `GET /auth/callback` → token cached to `.research_cache/.spotify_oauth`
- Token refresh: `GET /auth/token` → `spotify.py:get_current_token()` → spotipy auto-refresh via `refresh_access_token()`
- Client token: `player.js:120-123` `getOAuthToken` callback fetches `/auth/token` every time SDK needs a token
- No session timeout, no idle detection, no token revocation logic

### Playback Transition Flow
- `_playNext()` (line 318-336): shifts queue, dispatches to `_playAudio()` or `_playSpotifyTrack()`
- `_handleSpotifyStateChange` (line 460): 3-part condition for track-end: `paused && position===0 && prevCount>0`
- `_fadeSpotifyVolume` (line 824-832): 20-step async fade using `setTimeout` promises
- `_fadeAudioVolume` (line 809-815): `setInterval` at 50ms for audio crossfade
- Queue-empty polling: `setTimeout(() => this._playNext(), 300)` at line 324

### Missing Browser APIs
- No `visibilitychange` event listener — page has no idea it's backgrounded
- No `pagehide`/`freeze` event — no graceful shutdown
- No Media Session API — no lock screen media controls
- No Wake Lock API — CPU can be suspended
- No AudioContext — uses `<audio>` element which has its own background policies
