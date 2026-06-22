# Mobile Playback Continuity Slice — Handoff

**Status:** Implemented, uncommitted — awaiting chef review  
**Date:** 2026-06-22  
**Scope:** Frontend only — `resonova/web/player.js`

---

## Changed Files

| File | What changed |
|------|-------------|
| `resonova/web/player.js` | 4 surgical edits — see line refs below |

No backend, index.html, styles.css, or other files touched.

---

## How Each Requirement Is Met

### Req 1 — Do NOT start Spotify while page hidden (~line 1672–1685)

Added an early guard at the top of `_playSpotifyTrack`, before any health check or API call:

```javascript
if (document.hidden) {
  this._obsRecord('play:spotify:pending-unlock', item.uri.slice(-24));
  this._pendingUnlockItem = item;
  this._setNowPlaying('Spotify waiting for phone unlock', 'Unlock your phone to resume');
  // ... waveform DOM setup ...
  this._updateSkipMusicButton();
  return;
}
```

`/me/player/devices` and `/me/player/play` are never called. Spotify stays healthy (no `_spotifyUnhealthy` flag set). The item reference is stored as `this._pendingUnlockItem`.

### Req 2 — Auto-resume on visibilitychange (~line 108–131)

The `visibilitychange` handler now checks `_pendingUnlockItem` before falling through to `_reconcileAfterBackground`:

```javascript
const pending = this._pendingUnlockItem;
if (pending) {
  this._pendingUnlockItem = null;
  this._obsRecord('play:spotify:unlock-resume', pending.uri.slice(-24));
  this._setNowPlaying('Spotify waiting for phone unlock', 'Reconnecting…');
  this._recoverSpotifySession().then(success => {
    if (success) {
      this._playSpotifyTrack(pending);   // exact pending URI
    } else {
      this._spotifyRecoveryFailed = true;
      this._updateSkipMusicButton();     // Skip Music stays visible
    }
  });
  return;
}
```

`_recoverSpotifySession` reconnects the SDK player, waits for the device, and verifies Connect visibility via `/me/player/devices` (12 s window). If the device is visible, `_playSpotifyTrack(pending)` fires — `document.hidden` is now `false`, so the early guard does not block it.

### Req 3 — Skip Music fallback intact (~line 2858–2862)

`_updateSkipMusicButton` now includes `|| !!this._pendingUnlockItem` in its `shouldShow` condition. Skip Music is visible the entire time a segment is pending-unlock, and remains visible if recovery fails (`_spotifyRecoveryFailed = true`).

### Req 4 — Non-fatal copy

All user-facing strings in this path:
- `'Spotify waiting for phone unlock'` / `'Unlock your phone to resume'` (pending state)
- `'Spotify waiting for phone unlock'` / `'Reconnecting…'` (unlock, recovery in progress)
- `'Spotify waiting for phone unlock'` / `'Unlock your phone to resume or use Skip Music'` (recovery failed)

Never "Spotify playback failed." The recovery button does not appear during pending-unlock state (only appears if recovery subsequently fails, which is an honest signal).

---

## The Hidden → Pending → Visible → Resume Flow

```
1. Cast is playing. A Spotify segment is next.
2. User locks phone → visibilitychange:hidden fires, obs recorded.
3. Commentary segment ends → _playNext() → _playSpotifyTrack(item) called.
4. document.hidden === true → early guard fires:
     - obs: play:spotify:pending-unlock
     - this._pendingUnlockItem = item
     - now-playing: "Spotify waiting for phone unlock"
     - Skip Music button becomes visible
     - function returns — NO API calls made
5. User unlocks phone → visibilitychange:visible fires:
     - obs: visibilitychange:visible
     - pending = this._pendingUnlockItem (truthy) → handled first
     - this._pendingUnlockItem = null
     - obs: play:spotify:unlock-resume
     - now-playing: "Spotify waiting for phone unlock / Reconnecting…"
     - _recoverSpotifySession() starts (reconnects SDK, polls /me/player/devices)
       • On success:
           - obs: recovery:success
           - _playSpotifyTrack(pending) called (document.hidden=false, plays normally)
       • On failure:
           - obs: play:spotify:unlock-recovery-fail
           - now-playing: "… use Skip Music"
           - _spotifyRecoveryFailed=true → Skip Music stays visible
           - user taps Skip Music → skip() → advances to next commentary segment
```

---

## Desktop Behavior Unchanged

`document.hidden` is `false` on desktop in normal use (active tab). The early guard never fires. The `visibilitychange` handler falls through to the existing `_reconcileAfterBackground()` path. No change in behaviour.

The existing late-404 path (lines ~1762–1773 in the updated file) remains intact as a second layer for edge cases where a play attempt starts just as the page is hidden.

---

## Remaining Risks

1. **Race condition on fast lock/unlock**: If the user locks and immediately unlocks before `_playSpotifyTrack` runs, `document.hidden` may already be `false` by the time the call executes. The segment would play normally — no issue.

2. **Recovery still requires Spotify Premium + SDK overhead**: If the background period is very long (>30 min) the token may have expired. `_recoverSpotifySession` fetches a fresh token first so this should be handled. If it isn't, the existing reload-recommended path triggers.

3. **Only one pending item**: `_pendingUnlockItem` stores one item. If the queue advances multiple segments while hidden (e.g., blind-deadline fires for a prior segment), the last-called `_playSpotifyTrack` wins. Commentary segments are unaffected (they don't use this path). This is acceptable; the cast re-syncs at the pending track.

4. **Real-device verification required**: Only the boss can verify on a real phone. Emulator/desktop testing cannot simulate the browser background throttling that causes the original 404.

---

## Manual Phone Test Steps

1. Open Resonova on mobile Chrome. Sign in. Confirm a cast is generating or is saved.
2. Start playing a cast that has Spotify music segments.
3. Wait for a commentary segment to finish and a Spotify segment to be about to start.
4. **Lock the phone** just as the Spotify segment begins (within 2–3 s of commentary ending).
5. **Expected (unlocked state):**
   - The obs timeline (Diag panel) should show `play:spotify:pending-unlock` and then `visibilitychange:hidden`.
   - No `/me/player/play` or `/me/player/devices` calls were made while locked.
6. **Unlock the phone** (return to Resonova tab).
7. **Expected (after unlock):**
   - Obs shows: `visibilitychange:visible`, `play:spotify:unlock-resume`, `recovery:start`, `recovery:success`, `play:cmd:start`, `play:cmd:ok`.
   - The Spotify track starts playing.
   - Now-playing shows the track name/artist (not "failed").
8. **Test recovery failure path:**
   - Disable network on the phone before unlocking.
   - Unlock → obs shows `recovery:fail`, `play:spotify:unlock-recovery-fail`.
   - "Skip Music" button is visible.
   - Tap "Skip Music" → cast advances to the next commentary segment.
   - Re-enable network, cast continues.

---

## node --check Result

```
node --check resonova/web/player.js  →  (no output) exit code 0 — SYNTAX OK
```

---

## Confirmations

- ✅ No commit, no push, no PR — changes in working tree only
- ✅ Frontend only — `resonova/web/player.js` is the only changed file
- ✅ Desktop behavior unchanged — early guard only fires when `document.hidden === true`
- ✅ Skip Music fallback intact — shown in pending-unlock state and after recovery failure
- ✅ No unrelated refactor or formatting churn
- ✅ All existing `_obsRecord` calls preserved; new obs events added for the new paths
- ✅ No backend, scopes, or memory layer touched
