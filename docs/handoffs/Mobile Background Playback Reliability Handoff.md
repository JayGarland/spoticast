# Mobile Background Playback Reliability Handoff

**Date:** 2026-06-19
**Status:** Plan ready — awaiting approval before implementation
**Replaces:** Previous failed implementation (2026-06-19)

## Strategy-Layer Gate Review

This handoff is **not accepted as an implementation plan yet**.

Accepted facts from owner validation:

- The previous playback reliability implementation failed.
- Mobile active-page playback does not reliably transition from AI commentary to Spotify music.
- Mobile locked/background playback does not reliably continue through segment transitions.
- The "Tap to Resume" overlay created a bad loop and should not be considered a successful product behavior.
- Desktop playback is materially better than mobile playback.

Repository action taken by strategy layer:

- Restore `resonova/web/player.js`, `resonova/web/index.html`, and `resonova/web/styles.css` to the `5a533c952fbb189c3e371c6f4fe3fe6923238695` playback baseline.
- Preserve later strategy docs, handoffs, and private phone access configuration.

Unaccepted / needs verification:

- The claim that Spotify Web Playback SDK is categorically not viable on mobile browsers is stronger than the current official Spotify docs, which state SDK support for most major mobile and desktop browsers.
- The observed Resonova failure may still be caused by a combination of mobile browser behavior, Spotify account/device requirements, Tailscale/local-host context, SDK activation requirements, or our queue architecture.
- The proposed "mobile commentary-only" fallback may be useful, but it changes the product experience and requires owner approval before implementation.

Process issue:

- The manager transcript shows a command deleting a Copilot memory path outside the repository. That is outside the delegated Resonova repo scope and should be treated as a manager/process failure unless separately authorized.

Gate decision:

```text
Rollback frontend playback to stable baseline first.
Then run a clean mobile Spotify SDK feasibility investigation before implementing a fallback.
Do not apply this handoff's Phase A fallback until approved by the owner.
```

---

## Root Cause Diagnosis

### Finding 1: Spotify Web Playback SDK is NOT viable on mobile browsers

The Spotify Web Playback SDK (`https://sdk.scdn.co/spotify-player.js`) was archived in June 2020 and has not received any updates since. It depends on Encrypted Media Extensions (EME) / Widevine DRM to decrypt audio streams, which fails to initialize on the vast majority of mobile browsers:

- **iOS Safari:** No Widevine CDM available. The SDK will never fire the `ready` event.
- **Android Chrome:** Widevine is present but EME initialization is unreliable when the page is backgrounded or the screen is locked. The `ready` event may never fire, or the `player_state_changed` WebSocket may be throttled/disconnected.
- **All mobile:** The SDK requires `activateElement()` (a method on `Spotify.Player`) to be called before playback can begin on browsers with autoplay restrictions. Resonova never calls this method (no call to `activateElement()` exists anywhere in `player.js`).
- **All mobile:** The SDK fires an `autoplay_failed` event when the browser blocks automatic playback. Resonova does not listen for this event (no `addListener('autoplay_failed', ...)` exists in `player.js`, lines 153–179 where all listeners are registered).

**Conclusion:** No amount of JavaScript fallback, retry logic, or health monitoring can fix a DRM initialization failure. The SDK simply cannot work on mobile. All mobile Spotify integration (lines 466–582 in `_playSpotifyTrack`, lines 595–649 in `_handleSpotifyStateChange`) is dead code on mobile.

### Finding 2: "Tap to Resume" infinite loop — `_clearStallFlag` race condition

**Location:** `_tryRecoverPlayback()`, lines 1009–1054

The race works as follows:

1. Health monitor detects stall and sets `this._playbackStalled = true` (line 963).
2. User returns to tab → `_tryRecoverPlayback()` runs.
3. At line 1037, the Spotify recovery path calls `this.spotifyPlayer.resume()`.
4. That `.resume()` fails → catch at line 1039 calls `this._markSpotifyStalled(...)`.
5. `_markSpotifyStalled()` (line 1069) sets `this._playbackStalled = true` again.
6. **But then execution falls through to line 1051:** `this._clearStallFlag()` unconditionally clears `_playbackStalled` back to `false`.
7. Next health monitor tick sees `_playbackStalled = false`, no progress, so sets it to `true` again → cycle repeats.
8. The resume overlay appears, user taps → `resume-requested` → `_tryRecoverPlayback()` → same race → overlay reappears.

**Root cause:** `_clearStallFlag()` at line 1051 runs unconditionally after the `if/else if` block, undoing whatever `_markSpotifyStalled()` just did on the Spotify failure path. The two functions race inside the same synchronous execution.

### Finding 3: `_markSpotifyStalled` dead-ends the queue

**Location:** `_markSpotifyStalled()`, lines 1069–1078

```js
_markSpotifyStalled(message) {
    this._playbackStalled = true;
    this._lastProgressTime = Date.now();
    this._setMediaSessionState('paused');
    document.getElementById('next-up').textContent =
      `${message} Use the system play control, return to Spotify, or press Skip to continue.`;
    if (typeof window.__resonovaShowResume === 'function') {
      window.__resonovaShowResume(true);
    }
  }
```

This method **never calls `_playNext()`**. When any Spotify item fails (no player, no device, play API fails, start timeout, resume fails), the queue is permanently blocked at that Spotify item. The only way forward is manual user skip. On mobile — where the SDK never works — every Spotify item becomes a permanent roadblock, and since commentary → Spotify → commentary alternates, playback stops at the first Spotify item forever.

### Finding 4: Health monitor double-fire risk — bypasses `_audioCleanup`

**Location:** `_startHealthMonitor()`, lines 940–949

```js
if (this._isAudioAtEnd()) {
    this._logPlaybackEvent('audio-ended-healthcheck');
    if (this._audioCleanup) {
        this._audioCleanup();
        this._audioCleanup = null;
    }
    this._lastProgressTime = Date.now();
    this._playNext();  // <-- directly calls _playNext()
    return;
}
```

And the same pattern at lines 1022–1027 in `_tryRecoverPlayback()`:

```js
if (this._isAudioAtEnd()) {
    this._logPlaybackEvent('audio-ended-recovery');
    if (this._audioCleanup) {
        this._audioCleanup();
        this._audioCleanup = null;
    }
    this._clearStallFlag();
    this._playNext();  // <-- directly calls _playNext()
    return;
}
```

Both paths call `_audioCleanup()` (which removes `timeupdate` listeners and nulls `onended`), but they call `_playNext()` inline. If `_playNext()` calls `_playAudio()` which sets up new listeners, and the old `timeupdate` callback closure fires one last time (possible due to event queue timing), the old closure can call `_playNext()` a second time — advancing the queue by two items instead of one.

The correct path is the one taken by the `timeupdate` fallback at lines 409–414:

```js
audioCleanup();
this._audioEndedCleanly = false;
this._logPlaybackEvent('audio-ended-fallback');
this._playNext();
```

This works because `audioCleanup()` is the same closure that removes the listeners, and by the time `_playNext()` runs, the listeners are already detached. But the health monitor and recovery paths call `this._audioCleanup()` (which sets `this._audioCleanup = null`), then immediately call `_playNext()`. If the `timeupdate` closure has a pending call in the microtask queue, it can still fire.

### Finding 5: Missing SDK signals — `activateElement()` and `autoplay_failed`

- **`activateElement()`:** Never called anywhere in `player.js`. The Spotify Web Playback SDK documentation states this must be called before playback on browsers with autoplay restrictions. Without it, `player.resume()` and `player.setVolume()` are no-ops on mobile Safari and some Android Chrome configurations.
- **`autoplay_failed`:** Never registered as a listener (lines 153–179 show all registered listeners: `ready`, `not_ready`, `initialization_error`, `authentication_error`, `account_error`, `player_state_changed` — no `autoplay_failed`). When the SDK cannot start playback due to browser autoplay policy, it silently fails with no diagnostic logged.

---

## Recommended Rollback Plan

### Items to REMOVE (actively harmful)

| # | Item | Lines | Rationale |
|---|------|-------|-----------|
| 1 | `_clearStallFlag()` at end of `_tryRecoverPlayback` | 1051 | Races with `_markSpotifyStalled()` in the Spotify recovery catch (line 1039), creating the "Tap to Resume" endless loop. Remove this unconditional clear — let each recovery path clear its own stall state on success only. |
| 2 | `_isAudioAtEnd()` check in `_startHealthMonitor` that calls `_playNext()` directly | 936–950 | Bypasses the normal transition flow. The `timeupdate` fallback already handles audio-end detection. This duplicate path risks double-fire. Replace with: only detect and log, but do NOT call `_playNext()`. Let the existing `timeupdateFallback` handler do the transition. |
| 3 | `_isAudioAtEnd()` check in `_tryRecoverPlayback` that calls `_playNext()` directly | 1015–1028 | Same double-fire risk as #2. Replace with: if audio is at end, call `audioEl.play()` to trigger the natural `onended` event, or if that's blocked, mark as stalled and show resume overlay. Do NOT call `_playNext()` directly. |
| 4 | `_spotifyStartedForCurrentItem` guard that requires position > 0 | 607–613 (the `hasRealProgress` + `_spotifyStartedForCurrentItem = true` logic) | While intended to prevent false end-detection, on mobile this means the SDK never confirms "started" because it never fires `player_state_changed` with positive position. Combined with Finding 3, this creates a deadlock: the end detector never fires, the start detector never confirms, and the item sits forever. This guard is moot after Phase 1 item 6 (disabling Spotify on mobile). Keep on desktop. |
| 5 | AudioContext unlock (`_unlockAudioOnGesture`) | 1082–1114 | This unlocks the Web Audio API's `AudioContext`, which is separate from `HTMLAudioElement`. It has no effect on `HTMLAudioElement.play()` behavior. It's harmless but misleading — remove to reduce code surface. |
| 6 | Mobile-specific health monitor intervals | 934–935 | The `this._isMobile ? 3000 : 5000` and `this._isMobile ? 10000 : 15000` logic adds complexity without solving the core issue. After Phase 2, mobile has fewer failure modes (Spotify is skipped), so a single interval works for both. Simplify to one interval (4000ms) and one threshold (12000ms). |

### Items to FEATURE-FLAG (disable on mobile, keep on desktop)

| # | Item | Lines | Implementation |
|---|------|-------|----------------|
| 7 | All Spotify SDK integration on mobile | Multiple | **In `_playNext()` (line ~340):** Before the `if (item.type === 'audio')` branch, add: `if (this._isMobile && item.type === 'spotify') { this._logPlaybackEvent('spotify-skipped-mobile', { uri: item.uri }); this._playNext(); return; }` |
| 8 | `_playSpotifyTrack()` entry guard | 466 (top of method) | **At line 466:** Add as first line: `if (this._isMobile) { this._logPlaybackEvent('spotify-skipped-mobile', { uri: item.uri }); this._playNext(); return; }` |

### Items to KEEP (genuinely useful on desktop and harmless on mobile)

| # | Item | Lines | Rationale |
|---|------|-------|-----------|
| 9 | `timeupdateFallback` for audio segments | 398–414 | Protects against `onended` not firing — this affects both desktop and mobile. Genuinely useful. |
| 10 | Media Session API | 1227–1272 | Owner confirmed lock screen controls work. Signals to OS that Resonova is a media app. Keep. |
| 11 | Diagnostics panel + `window.__resonovaEventLog` | 33–35, 916–929 | Owner-facing debug surface. Essential for validation. Keep. |
| 12 | "Tap to Resume" overlay (`#resume-overlay`) | In `index.html` and `styles.css` | Useful UX when `NotAllowedError` blocks playback. Keep but fix the loop (via removal #1). |
| 13 | `_audioCleanup` shared function | 416–421 | Correct pattern for preventing double-fires. Keep. |
| 14 | Crossfade handler | 388–396 | Smooth transitions. Keep. |
| 15 | `_fetchWithRetry` for API calls | 1285–1316 | Useful on desktop for transient Spotify API failures. Keep. |
| 16 | Spotify track-end fallback timer | 556–567 | Useful on desktop when `player_state_changed` is delayed. Keep. |
| 17 | `_retryPlay` for AbortError | 1119–1141 | Useful recovery for transient play() failures. Keep. |
| 18 | `_registerRecoveryListeners` + `_tryRecoverPlayback` | 996–1054 | Useful for desktop tab-switch recovery. Keep but fix #1 and #3. |
| 19 | `_startHealthMonitor` | 927–966 | Keep the stall detection concept but fix #2. |
| 20 | Spotify near-end detection in health monitor | 952–965 | Useful on desktop. Keep. |

---

## Recommended Product Fallback

### Phase A (Immediate): Skip Spotify on mobile, play commentary-only

**How it works:**

1. Mobile detection (`this._isMobile`) is already computed at line 51:
   ```js
   this._isMobile = navigator.maxTouchPoints > 0 && /Mobi|Android/i.test(navigator.userAgent);
   ```

2. When `_playNext()` encounters a Spotify item on mobile (added guard at ~line 340):
   ```js
   if (this._isMobile && item.type === 'spotify') {
     this._logPlaybackEvent('spotify-skipped-mobile', { uri: item.uri, name: item.name });
     this._playNext();
     return;
   }
   ```

3. The queue advances immediately past the Spotify item to the next commentary segment. The episode structure becomes: Commentary 1 → Commentary 2 → Commentary 3 → ... (all Spotify tracks transparently skipped).

**What the user experiences:**

- Commentary segments play back-to-back with no music interleaving.
- No stalls, no "Tap to Resume" loops, no silent gaps.
- The diagnostics panel (🔍) shows `spotify-skipped-mobile` events so the owner can see exactly which tracks were skipped.
- Progress bar still advances (completedItems increments for skipped items too).

**Desktop behavior:** Completely unchanged. `_isMobile` is `false` on desktop, so the guard is a no-op. All existing Spotify interleaving works as before.

**Code change size:** ~8 lines added, ~30 lines removed. Net reduction.

### Phase B (Future): 30-second preview clips

Once Phase A is validated and stable, this enhancement can be considered:

- Spotify's `/v1/tracks/{id}` endpoint returns a `preview_url` field — a 30-second MP3 clip (already fetched in `_playSpotifyTrack` at line 504).
- Store `preview_url` in the item during track info fetch.
- On mobile, instead of skipping the Spotify item entirely, play the 30-second preview via `HTMLAudioElement` (same as commentary).
- This gives a richer mobile experience: short music clips between commentary segments.
- Risk: `preview_url` is `null` for many tracks (especially non-US catalog). Fall back to skip behavior when `preview_url` is null.

### Phase C (Not Recommended): Spotify app deep-linking

- Instead of in-browser playback, offer a "Listen on Spotify" button that opens `spotify://track/{id}`.
- This breaks the seamless radio experience and requires the Spotify app installed.
- Not recommended unless Phase A and B both prove insufficient.

---

## Implementation Steps (if approved)

### Step 1: Read current player.js
Confirm the current state matches what this handoff references. If the user has made edits since this handoff was written, re-check line numbers.

### Step 2: Remove harmful items (exact targets)

**Removal 1 — `_clearStallFlag` at end of `_tryRecoverPlayback`:**

Remove line 1051 (`this._clearStallFlag();`) and instead add `this._clearStallFlag();` inside the success path of the audio recovery block (after line 1032, inside `.then()`), and remove it from the Spotify recovery path (which already calls `_markSpotifyStalled` on failure — no stall clear on the Spotify failure path).

**Removal 2 — `_isAudioAtEnd` in health monitor:**

Replace lines 936–950 (the `if (this.currentItem?.type === 'audio' ...)` block that calls `_playNext()`) with a log-only version:
```js
if (this.currentItem?.type === 'audio' && this.audioEl && this._isAudioAtEnd()) {
  this._logPlaybackEvent('audio-ended-healthcheck', { note: 'detected but deferring to timeupdate fallback' });
  // Do NOT call _playNext() — let timeupdateFallback handle it
}
```

**Removal 3 — `_isAudioAtEnd` in `_tryRecoverPlayback`:**

Replace lines 1015–1028 (the `if (this._isAudioAtEnd())` block) with: if audio is at end, attempt `audioEl.play()` to trigger natural `onended`, and if that fails with `NotAllowedError`, show resume overlay. Do NOT call `_playNext()`.

**Removal 4 — `_spotifyStartedForCurrentItem` guard:**

Keep on desktop (it prevents false end-detection there). On mobile, it's moot because Spotify items are skipped. No code change needed beyond the feature-flag — the guard simply never runs on mobile.

**Removal 5 — AudioContext unlock:**

Remove lines 1082–1114 (`_unlockAudioOnGesture` method) and its call at line 90 (`this._unlockAudioOnGesture();`).

**Removal 6 — Mobile-specific intervals:**

Change lines 934–935 from:
```js
const interval = this._isMobile ? 3000 : 5000;
const threshold = this._isMobile ? 10000 : 15000;
```
to:
```js
const interval = 4000;
const threshold = 12000;
```

### Step 3: Add mobile Spotify skip guards

**Guard 1 — In `_playNext()`:**

After line 340 (`this._clearStallFlag();`), before `if (item.type === 'audio')`, add:
```js
if (this._isMobile && item.type === 'spotify') {
  this._logPlaybackEvent('spotify-skipped-mobile', { uri: item.uri, name: item.name || '(unknown)' });
  this._playNext();
  return;
}
```

**Guard 2 — In `_playSpotifyTrack()`:**

At line 466 (first line of method body, after the comment), add:
```js
if (this._isMobile) {
  this._logPlaybackEvent('spotify-skipped-mobile', { uri: item.uri, note: 'reached _playSpotifyTrack on mobile' });
  this._playNext();
  return;
}
```

### Step 4: Keep useful items intact

Do NOT modify: `timeupdateFallback`, `_audioCleanup`, crossfade, `_fetchWithRetry`, Media Session API, diagnostics panel, resume overlay, Spotify fallback timer, `_retryPlay`, `_registerRecoveryListeners`.

### Step 5: Test on desktop

1. Generate a new episode or replay a saved one.
2. Verify Spotify tracks play normally between commentary segments.
3. Verify skip, progress bar, and diagnostics panel work.
4. Verify no regressions — desktop behavior should be identical.

### Step 6: Test on mobile

1. Access Resonova via Tailscale on mobile.
2. Start playback.
3. Verify commentary segments play continuously (no music interleaving).
4. Lock screen during playback — verify commentary continues or resumes after unlock without "Tap to Resume" loop.
5. Open diagnostics panel (🔍) — verify `spotify-skipped-mobile` events appear for every skipped track.
6. Verify progress bar advances through all segments.

### Step 7: Verify diagnostics

Open diagnostics panel on mobile and confirm:
- `spotify-skipped-mobile` events logged for each Spotify item
- No `stall-detected` events (commentary should flow smoothly)
- No repeated `not-allowed` / `visibility-recovery` loops

---

## Constraints Preserved

- [x] Single-user and private — no auth or multi-user changes
- [x] No secrets or tokens exposed — all changes are client-side only
- [x] Desktop playback not broken — `_isMobile` is `false` on desktop, all Spotify code paths run unchanged
- [x] Saved episode replay not broken — same `_startPlayback()` entry point
- [x] Spotify Web Playback SDK retained on desktop — mobile skip is additive, not a removal
- [x] Fix is minimal — net code reduction (~30 lines removed, ~10 added)
- [x] No persistent profile, feedback, native app, or public deployment work

---

## Owner Mobile Testing Steps (After Phase A)

### Test 1: Commentary plays continuously

1. Start playback on mobile.
2. Let multiple segments play without touching the phone.
3. **Expected:** Each commentary segment transitions smoothly to the next. No silent gaps. No "Tap to Resume" overlay appearing unexpectedly.

### Test 2: Lock screen behavior

1. Start playback, wait for a commentary segment to be mid-playback.
2. Lock the phone screen.
3. Wait 30–60 seconds.
4. Unlock and return to Resonova.
5. **Expected:** Playback has advanced to a later commentary segment (or is mid-playback on one). Not stuck at the same position.

### Test 3: No "Tap to Resume" infinite loop

1. Use the phone normally — lock, unlock, switch apps, return.
2. **Expected:** The "Tap to Resume" overlay may appear briefly if the browser blocks autoplay, but tapping it ONCE dismisses it and playback continues. It does not reappear immediately after dismissal.

### Test 4: Diagnostics show Spotify skips

1. Open the diagnostics panel (🔍 button).
2. **Expected:** Each skipped Spotify track appears as `spotify-skipped-mobile` with the track URI. No `stall-detected` events. Commentary transitions show `audio-ended` or `audio-ended-fallback`.

### Test 5: Skip button works

1. Press Skip during a commentary segment.
2. **Expected:** Advances to the next commentary segment (Spotify items are transparently skipped). Progress bar updates. No errors in diagnostics.

---

## Remaining Limitations

After Phase A:

1. **No Spotify music on mobile.** Mobile users hear commentary-only episodes. This is a known, documented limitation. The Spotify Web Playback SDK is architecturally incompatible with mobile browsers due to EME/Widevine DRM requirements.

2. **30-second preview clips not yet implemented.** Phase B (future enhancement) would use `preview_url` from the Spotify API to play short music clips via `HTMLAudioElement` between commentary segments. This gives a richer mobile experience but requires additional implementation and testing.

3. **iOS background suspension.** If iOS suspends the entire page (not just throttling), no JavaScript runs. The Media Session API helps reduce this risk but cannot eliminate it. Commentary-only playback is simpler and less likely to trigger suspension than interleaved playback.

4. **No native app.** Full mobile reliability (background audio with screen locked, seamless music+commentary interleaving) ultimately requires a native app with proper audio session management. This is out of scope.

---

## Candidate Follow-ups

1. **Phase B: 30-second preview clips.** Implement `preview_url` playback for mobile Spotify items. Estimate: ~40 lines of code.

2. **Pre-assembled continuous stream for mobile.** Instead of skipping Spotify items, generate a single continuous audio file server-side that includes both commentary and 30-second preview clips. The mobile client plays one file with no transitions. Estimate: server-side work, ~100 lines.

3. **PWA with audio focus.** Add a web manifest and service worker to make Resonova a Progressive Web App, which may improve background audio behavior on Android. Estimate: ~50 lines of config + service worker.

4. **Remove Spotify SDK entirely (long-term).** If the SDK is archived and unsupported, consider migrating desktop to Spotify Web API-based playback (30-second previews via HTMLAudioElement) for consistency. This would eliminate all SDK-specific code and simplify the player architecture by ~200 lines.
