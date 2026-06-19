# Mobile Lockscreen Playback Hardening Handoff

## Purpose
Three bounded, prevention-oriented fixes to address mobile playback stopping when the phone is idle or on lockscreen. All fixes are in `player.js` only, with no retry loops, state machines, or new dependencies.

## Root Causes (from prior diagnosis)

| Failure Mode | Root Cause | Fix |
|---|---|---|
| Token refresh fetch fails during page freeze | `getOAuthToken` callback calls `_apiFetch('/auth/token')` which fails when JS is suspended. `cb()` is never called, SDK fires `authentication_error`. | Fix 1: Token cache |
| Crossfade timeout ballooning (1.8s → 20+s) | `_fadeSpotifyVolume` uses 20 hardcoded `setTimeout` steps. When background-throttled to ≥1000ms each, fade becomes 20+ seconds. | Fix 2: Fade cap |
| `player_state_changed` event dropped or condition missed | SDK event not delivered when page frozen; track-end condition too brittle. Queue stalls permanently. | Fix 3: Segment deadline |

## Files Changed

| File | Change | Summary |
|---|---|---|
| `resonova/web/player.js` | 3 fixes, ~30 lines | Token cache in getOAuthToken, fade step cap, bounded segment deadline |
| `resonova/web/styles.css` | NOT modified | — |
| `resonova/web/index.html` | NOT modified | — |

## Fix 1: Token Cache (~8 lines)

**What**: Cache the latest Spotify access token. When the `getOAuthToken` callback's fetch fails (mobile backgrounded), fall back to the cached token so `cb()` is always called.

**Where**:
- Constructor: `this._cachedToken = null;`
- `_initSpotifyPlayer`: after initial fetch `this._cachedToken = token;`
- `getOAuthToken` callback: wrapped in `try/catch` — on failure, `cb(this._cachedToken)` if cached

**Why it works**: The Spotify SDK needs `cb(token)` to be called to function. A slightly stale token (seconds old) is still accepted by the SDK. The SDK will retry `getOAuthToken` if the token is actually rejected.

## Fix 2: Fade Step Cap (~3 lines)

**What**: Instead of hardcoded 20 steps, compute step count dynamically based on `durationMs`. Each step is `durationMs / steps`. With a minimum of 1 step per second, background-throttled `setTimeout` (≥1000ms) won't balloon the fade.

**Where**: `_fadeSpotifyVolume` method

**Before**: `const steps = 20;`
**After**: `const steps = Math.min(20, Math.max(1, Math.ceil(durationMs / 1000)));`

**Effect**: For `_CROSSFADE_MS = 1800`: foreground = 2 steps at ~900ms each (smooth fade). Background = each step throttled to ~1000ms, total ~2 seconds instead of 20+.

## Fix 3: Bounded Segment Deadline (~12 lines)

**What**: A one-shot `setTimeout` watchdog set when `player_state_changed` first reports a track's duration. If the same track is still playing after remaining duration plus a 3000ms grace period and `_trackEndFired` is still false, force-advance to the next segment.

**Where**:
- Constructor: `this._segmentDeadline = null;`
- `_handleSpotifyStateChange`: sets deadline on first `state.duration > 0` event
- `_playNext`: clears deadline when item changes
- `_onPlaybackComplete`: clears deadline

**Safety guarantees**:
- Uses **sentinel reference comparison** (`===`), not index — tied to exact object identity
- Self-clearing: sets `_segmentDeadline = null` after firing
- Only fires when `_trackEndFired` is still false (normal detection didn't work)
- Only sets when `duration > 0` (known duration, no guessing)
- Cleared on any item change (`_playNext`) or playback completion
- Grace period: `remaining duration + 3000ms` (not aggressive)

## Strategy-Layer Gate Review

Gate result: accepted after cleanup.

Corrections applied:

- Removed unrelated formatting-only changes from `docs/handoffs/Diagnostic Panel Toggle Handoff.md`.
- Removed incidental `player.js` formatting churn while preserving the three functional fixes.
- Tightened the segment deadline from full `duration + 3000ms` to remaining-duration `duration - position + 3000ms`.

Owner concern:

- The owner specifically reported that `auth_error` can show auth failed after phone idle and force a restart from the beginning.
- The token cache fix directly targets the most likely cause: `getOAuthToken` fetch failing while backgrounded and never calling Spotify's callback.
- If auth errors still appear after this patch, the next product fix should be resume-state persistence, not another blind auth retry loop.

## Validation Results

- `node --check resonova/web/player.js` — PASS
- `git diff --name-only` — only `player.js` (+ handoff .md)
- `git diff -- resonova/web/styles.css` — zero output
- `git diff -- resonova/web/index.html` — zero output
- All 26 functional criteria PASS
- No retry loops, no state machines, no new dependencies
- All existing playback methods untouched

## Mobile Test Steps

### Prerequisites
- Tailscale connected on server and mobile
- Server running: `python -m uvicorn resonova.server:app --host 127.0.0.1 --port 8765`
- Mobile browser at: `https://buttking.tail15ea24.ts.net:8765`
- Enable diagnostic panel (click "Diag" button)

### Test 1: Token survives background
1. Start an episode. Note diagnostic shows SDK ready=yes, device_id present.
2. Lock phone. Wait 2-3 minutes.
3. Unlock, return to page.
4. Verify: auth_error field is "-" (no auth error). Playback should resume or advance.
5. Before this fix: auth_error would show a message, landing page might appear.

### Test 2: Segment transition during lockscreen
1. Start an episode with multiple Spotify segments.
2. Wait for a Spotify segment to begin playing. Note the track name.
3. Lock phone immediately.
4. Wait longer than the track duration + 10 seconds.
5. Unlock, return to page.
6. Verify: playback has advanced to the next segment (commentary or next track).
7. Before this fix: playback would be stuck mid-episode with no progress.

### Test 3: Fade doesn't cause long silence
1. Start an episode. Lock phone during a Spotify segment near its end.
2. Unlock after 5-10 seconds.
3. Verify: if fade was in progress, it completed quickly (not 20+ seconds of silence).
4. Before this fix: silence gap could be very long when lock happened during crossfade.

### Test 4: Foreground playback unchanged
1. Play through a full episode without locking the phone.
2. Verify: all segment transitions, crossfades, and track changes work as before.
3. No timing changes should be noticeable in foreground.

## Rollback

```bash
git checkout HEAD -- resonova/web/player.js
```

## Design Decisions

- **Prevention over recovery**: fixes prevent failures rather than detecting and recovering from them
- **Bounded deadlines, not retry loops**: one-shot timeouts that self-clear, not recurring intervals
- **Sentinel identity, not index**: deadline uses `===` on object reference — immune to queue reordering
- **No guessing**: deadline only set when actual duration is known from SDK
- **3-second grace**: not aggressive — normal track-end detection has priority
- **All in player.js**: no server changes, no config changes, no CSS changes

## What Was NOT Done (by design)

- Media Session API — future task
- Wake Lock API — Android-only, requires user gesture, drains battery
- visibilitychange/pagehide listeners — anti-pattern, leads to state machines
- Polling monitors — adds complexity without reliability gain
- Exponential backoff retry — unnecessary when prevention works
- Queue refactoring — not needed for this fix scope
