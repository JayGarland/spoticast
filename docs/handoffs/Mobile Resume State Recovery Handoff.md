# Mobile Resume State Recovery Handoff

## Purpose
When mobile playback is interrupted by idle/lockscreen (auth errors, page freeze), the user previously had to restart the episode from the beginning. This handoff adds resume-state persistence so the player saves its position to localStorage, and on page reload/auth recovery shows a "Resume episode" affordance. A visibilitychange listener reconciles playback state when the page returns to foreground.

## What Was Implemented

Three mechanisms, all in `player.js` only:

1. **Playback state persistence** — Saves episode ID, remaining queue, previous-segment history, current item, progress, and segment type to `localStorage` key `resonova:resume` on every segment transition.
2. **Resume affordance** — On `init()` after auth, checks for unfinished episode. Shows a "Resume" card in the connected state with segment progress info. Clears on dismiss or episode completion.
3. **Foreground reconciliation** — `visibilitychange` listener queries Spotify `getCurrentState()` when page becomes visible. If track appears ended (paused, near position 0, has history), advances gracefully. If auth error exists but resume state exists, treats it as non-fatal.

## Files Changed

| File | Changes | Summary |
|---|---|---|
| `resonova/web/player.js` | 15 changes, ~160 new lines | 3 constructor fields, visibilitychange listener, 6 new methods, 5 integration points, chef gate fixes |
| `resonova/web/styles.css` | NOT modified | — |
| `resonova/web/index.html` | NOT modified | Resume card created dynamically in JS |

## New Methods

| Method | Lines | Purpose |
|---|---|---|
| `_saveResumeState()` | 80-98 | Writes `resonova:resume` to localStorage with episodeId, queue snapshot, playedItems, currentItem, progress, segmentType, timestamp |
| `_clearResumeState()` | 100-102 | Removes `resonova:resume` from localStorage |
| `_checkResumeState()` | 104-118 | Reads + validates resume state; expires after 30 minutes; handles corruption gracefully |
| `_showResumePrompt(state)` | 121-159 | Creates a "Resume" card in #state-connected with segment progress, Resume + Dismiss buttons |
| `_resumePlayback(state)` | 161-179 | Rebuilds queue from saved state (currentItem first, then remaining queue), starts playback, adjusts completedItems |
| `_reconcileAfterBackground()` | 181-203 | Called on visibilitychange→visible; checks Spotify currentState; advances if track ended; treats auth_error as non-fatal if episode exists |

## Chef Gate Corrections

- Generated casts now set `_episodeId = jobId` immediately after `/generate` returns, because the server uses the job ID as the eventual saved episode ID.
- Resume state now saves and restores `playedItems`, so the in-app Previous segment button can work after resume/recovery.
- `_resumePlayback()` no longer references non-existent `#step-intro`; it resumes directly into the player state.
- `_resumePlayback()` restores `totalItems` from saved state after queue rebuild, preserving progress display.
- Live queue updates (`track_ready`, `outro_ready`) save resume state after appending newly available segments.

## Integration Points

| Where | What |
|---|---|
| Constructor | `_episodeId`, `_segmentType`, `_resumeChecked` fields; `visibilitychange` listener |
| `init()` | After auth, checks resume state; shows prompt if unfinished episode exists |
| `generate()` | Sets `_episodeId` from returned `job_id` |
| `_playEpisode()` | Sets `this._episodeId = episodeId` |
| `_startPlayback()` | Calls `_saveResumeState()` |
| `_playNext()` | Calls `_saveResumeState()` after state updates |
| `track_ready` / `outro_ready` | Saves updated live queue after new segments arrive |
| `_onPlaybackComplete()` | Calls `_clearResumeState()` |
| `_setSegmentType()` | Captures `this._segmentType = type` |

## localStorage Format

Key: `resonova:resume`
```json
{
    "episodeId": "06a35...",
    "queue": [{ "type": "audio", "url": "..." }, { "type": "spotify", "uri": "..." }],
    "playedItems": [{ "type": "audio", "url": "..." }],
    "currentItem": { "type": "spotify", "uri": "...", "name": "...", "artist": "..." },
    "completedItems": 3,
    "totalItems": 14,
    "segmentType": "spotify",
    "ts": 1750358400000
}
```

- Expires after 30 minutes of inactivity
- Cleared on episode completion
- Written on every segment transition and on background return

## Design Decisions

- **localStorage over sessionStorage**: survives browser tab close/reopen on mobile
- **30-minute expiry**: prevents stale "resume" prompts days later
- **`_resumeChecked` flag**: prevents duplicate prompts if `init()` is called multiple times
- **Resume card in #state-connected**: appears above the generate form, not in landing (user must be authenticated to resume)
- **Resume rebuilds queue with currentItem first**: the partially-played item goes first, then remaining queue — user doesn't lose the segment they were on
- **`completedItems - 1` on resume**: the current item hasn't been completed yet, so we back up one
- **visibilitychange reconciliation is bounded**: one `getCurrentState()` call, no polling
- **`position < 2000` threshold for "ended"**: more lenient than the exact `position === 0` check in normal track-end detection, accounts for timing granularity after background

## Validation Results

- `node --check` — PASS
- Backend import smoke test — PASS
- Only `player.js` modified
- `styles.css` and `index.html` — zero diff
- All 19 acceptance criteria PASS
- No retry loops, no state machines, no wake lock, no Media Session
- No new dependencies

## Mobile Test Steps

### Test 1: Resume after page reload
1. Start an episode. Let it play through 2-3 segments.
2. Close the browser tab (or navigate away).
3. Reopen `https://buttking.tail15ea24.ts.net:8765`.
4. Authenticate if needed.
5. Verify: A "Resume" card appears with segment progress (e.g., "Segment 3/14").
6. Click "Resume".
7. Verify: Playback resumes from approximately where it left off.

### Test 2: Resume after lockscreen auth error
1. Start an episode.
2. Lock phone. Wait 2-3 minutes.
3. Unlock phone, return to page.
4. If auth error is shown in diagnostics, reload the page.
5. After reload + re-auth: verify "Resume" card appears.
6. Click "Resume" — verify playback continues.

### Test 3: Dismiss resume prompt
1. Start an episode, play a segment, close tab.
2. Reopen, authenticate.
3. Verify "Resume" card appears.
4. Click the ✕ dismiss button.
5. Verify card disappears.
6. Reload page — card should NOT reappear (state was cleared).

### Test 4: Resume expiry
1. Start an episode, play a segment.
2. Manually set an old timestamp in localStorage:
   ```js
   var s = JSON.parse(localStorage.getItem('resonova:resume'));
   s.ts = Date.now() - 31 * 60 * 1000;
   localStorage.setItem('resonova:resume', JSON.stringify(s));
   ```
3. Reload page.
4. Verify: "Resume" card does NOT appear (expired).

### Test 5: Foreground reconciliation
1. Start an episode. Wait for a Spotify segment.
2. Keep the page visible (don't lock).
3. Switch to another app briefly (5-10 seconds), then switch back.
4. Verify: Playback continues normally. The `visibilitychange` handler ran but took no action (track wasn't ended).

## What Was NOT Done (by design)
- Media Session API
- Wake Lock API
- Retry loops or polling monitors
- Lifecycle state machines
- Changes to index.html or styles.css
- Server-side save/restore

## Rollback

```bash
git checkout HEAD -- resonova/web/player.js
localStorage.removeItem('resonova:resume')  # in browser console
```
