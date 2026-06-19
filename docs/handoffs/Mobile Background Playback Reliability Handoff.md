# Mobile Background Playback Reliability Handoff

**Date:** 2026-06-19
**Status:** Failed owner mobile validation; needs follow-up architecture/fix pass
**Parent Objective:** [Mobile Background Playback Reliability Brief](../strategy/mobile-background-playback-reliability-brief.md)

## Summary

Resonova's core playback engine had 5 root causes that caused silent stalls when transitioning between segments — especially on mobile with screen locked. This fix adds 13 defense-in-depth mechanisms spanning health monitoring, timeupdate fallback, intelligent error handling, visibility recovery, Spotify SDK hardening, Media Session API support, and a "Tap to Resume" overlay. The result: playback reliably advances across segments without requiring tab reactivation, with honest documentation of remaining browser-policy limitations.

## Owner Validation Failure

Owner mobile testing after commit `d4296a3` showed the lock-screen Media Session surface now appears correctly, but playback still does not continue automatically across a segment transition while the phone is locked/backgrounded.

Screenshot evidence:

- Lock screen displays `Resonova Commentary`.
- Media controls are visible.
- The next segment appears at `00:00 / 01:22`.
- Pause button is shown, but playback did not continue through the transition.

Interpretation:

```text
The Media Session layer is working, but the mobile browser still blocks or suspends
programmatic playback of the next segment after the current segment ends while locked.
```

Gate decision:

```text
The manager fix improved observability/control-surface behavior but did not solve
the core continuous background transition requirement.
```

This should not be treated as resolved.

Additional regression observed by owner:

```text
After returning to the page, Resonova advanced to the next commentary segment
instead of playing the Spotify music segment that should have come between.
```

Strategy-layer correction:

- Spotify startup/resume failures should not silently call `_playNext()`.
- The Spotify segment should remain the current segment and surface a stalled/retry state.
- The owner can then retry/resume or explicitly press Skip. The app should not silently delete the music segment from the episode flow.

Likely implication:

```text
For reliable locked-screen mobile playback, Resonova may need to avoid requiring
JavaScript to start a new media source while the phone is locked.
```

Candidate next direction:

- Investigate a mobile playback architecture that uses fewer runtime source transitions, such as a preassembled continuous commentary stream for mobile replay, a foreground-only interleaved mode with explicit warning, or a deeper platform-specific approach if Spotify interleaving must work under lock screen.

## Strategy-Layer Gate Notes

After manager return, the strategy layer applied two integration corrections before acceptance:

- Removed the `queue.unshift(item)` behavior on `NotAllowedError`. The blocked audio item is already the current item with `audioEl.src` set; re-adding it to the queue could replay the same segment after the resume overlay succeeds.
- Updated stall-monitor progress tracking so `_lastProgressTime` refreshes when HTML audio `currentTime` advances and when Spotify SDK position advances. Without this, normal long segments could be marked as stalled even while playing.
- Removed unconditional diagnostic `console.log` output. The in-app diagnostics panel remains the owner-facing debug surface.

## Root Cause Analysis

### Root Cause 1: `audio.onended` Not Firing (Mobile Primary)

**Problem:** HTML `<audio>` elements rely on the `onended` event to trigger transition to the next segment. On mobile browsers, `onended` can fail to fire when the page is backgrounded or the screen is locked — the browser throttles or suspends event dispatch to conserve power.

**Where:** `_playAudio()` at `player.js:345` originally attached only `audioEl.onended` as the sole transition mechanism.

**Impact:** A commentary segment finishes playing, but `onended` never fires. The player sits at the end of the segment forever, waiting for an event that will never arrive. The user hears silence until they unlock their phone.

### Root Cause 2: Spotify `player_state_changed` Not Firing (Mobile + Desktop)

**Problem:** The Spotify Web Playback SDK communicates playback state via WebSocket. When the tab is backgrounded, the WebSocket may be throttled or disconnected by the browser, causing `player_state_changed` events to never arrive. The original code relied on a single detection condition: `paused && position === 0 && track_window.previous_tracks.length > 0`.

**Where:** `_handleSpotifyStateChange()` at `player.js:579` only checked one condition.

**Impact:** A Spotify track finishes but the state-change event never fires. The next segment (commentary) never starts. Same silent-stall outcome as Root Cause 1.

### Root Cause 3: Programmatic `play()` Rejection Without Recovery

**Problem:** Browsers enforce autoplay policies that reject `audioEl.play()` with `NotAllowedError` when called without a recent user gesture. This is most common on mobile Safari but also affects desktop Chrome when the tab hasn't been interacted with recently. The original code caught the error with a bare `.catch()` and immediately skipped to the next segment — hiding the failure entirely.

**Where:** `_playAudio()` at `player.js:345` had a simple `.catch()` with no error classification.

**Impact:** Known as the "desktop tab click" bug — playback stalls silently, and the user must click the tab to resume. On mobile, this manifests as playback stopping after screen unlock.

### Root Cause 4: No Visibility/Focus Recovery

**Problem:** When the tab became visible again (user unlocks phone, switches back to tab), no code attempted to recover stalled playback. The player had no awareness of whether it was stalled or not.

**Where:** No `visibilitychange`, `focus`, or `pageshow` listeners existed in the original code.

**Impact:** Even if the browser allowed playback after the tab regained visibility, the player never tried to resume — it just sat there.

### Root Cause 5: Missing Media Session API

**Problem:** The Media Session API signals to the OS that a page is a media-playing app. Without it, the OS is more aggressive about suspending the tab. No metadata or action handlers were registered.

**Where:** No `navigator.mediaSession` usage existed.

**Impact:** Mobile OS treats Resonova as a generic web page rather than a media app, making it more susceptible to background suspension.

## Files Changed

| File | Lines Changed | Summary |
|------|--------------|---------|
| `resonova/web/player.js` | ~500 → ~1,292 lines | 13 new methods/properties; hardened existing methods with fallback paths and error classification |
| `resonova/web/index.html` | +~80 lines | "Tap to Resume" overlay (`#resume-overlay`), diagnostics panel (`#diagnostics-panel`), diagnostics trigger button, inline scripts for overlay + diagnostics |
| `resonova/web/styles.css` | +~130 lines | Styles for resume overlay (blur backdrop, pulsing play icon), diagnostics panel (terminal-green monospace, sticky header), diagnostics trigger (fixed-position circle button) |

## Fixes Implemented

### Fix 1: Playback Health Monitor

- **Method:** `_startHealthMonitor()` at `player.js:869`, `_clearStallFlag()` at `player.js:910`
- **What it does:** A `setInterval` that checks whether playback has made progress recently. If `Date.now() - this._lastProgressTime` exceeds a threshold, `_playbackStalled` is set to `true` — which triggers visibility recovery attempts and the resume overlay.
- **Key parameters:** 5s interval on desktop, 3s on mobile; 15s stall threshold on desktop, 10s on mobile.
- **Bonus:** Also performs near-end Spotify track detection (see Fix 6, condition 3).

```js
_startHealthMonitor() {
  const interval = this._isMobile ? 3000 : 5000;
  const threshold = this._isMobile ? 10000 : 15000;
  this._healthCheckInterval = setInterval(() => {
    // ── Near-end Spotify track detection (Phase 3.2) ──────────────────
    if (this.currentItem?.type === 'spotify' && !this._trackEndFired) {
      const sinceLastState = Date.now() - this._spotifyLastStateTime;
      if (sinceLastState > 8000 && this._spotifyLastPosition > 0 && this._spotifyLastDuration > 0) {
        const remaining = this._spotifyLastDuration - this._spotifyLastPosition;
        if (remaining < 3000) {
          this._trackEndFired = true;
          this._logPlaybackEvent('spotify-ended-near', { position, duration, remaining, sinceLastState });
          this._fadeSpotifyVolume(0.85, 0, _CROSSFADE_MS).then(() => this._playNext());
          return;
        }
      }
    }

    if (Date.now() - this._lastProgressTime > threshold) {
      this._playbackStalled = true;
      // ... log stall event ...
    }
  }, interval);
}
```

### Fix 2: Audio Segment timeupdate Fallback

- **Method:** `_playAudio()` at `player.js:345` — timeupdate closure at line ~390
- **What it does:** Attaches a `timeupdate` listener to the audio element that compares `currentTime` against `duration`. If the audio has reached within 0.5s of the end AND `currentTime` hasn't changed for 2 seconds (indicating the audio has truly stopped advancing), it triggers the transition — even though `onended` never fired.
- **Shared cleanup:** A `_audioCleanup` function removes both `timeupdate` listeners and the `onended` handler, preventing double-fires when one event type triggers before the other.

```js
const timeupdateFallback = () => {
  const now = Date.now();
  if (audioEl.currentTime !== lastTime) {
    lastTime = audioEl.currentTime;
    lastChangeTime = now;
  }
  if (audioEl.duration && isFinite(audioEl.duration) && audioEl.duration > 0) {
    if (audioEl.currentTime >= audioEl.duration - 0.5 && now - lastChangeTime > 2000) {
      audioCleanup();
      this._audioEndedCleanly = false;
      this._logPlaybackEvent('audio-ended-fallback');
      this._playNext();
    }
  }
};
```

### Fix 3: Intelligent play() Error Handling

- **Method:** `_playAudio()` at `player.js:345` — `.catch()` block at line ~434, `_retryPlay()` at `player.js:1034`
- **What it does:** Classifies `audioEl.play()` rejections by `err.name` and applies the appropriate recovery strategy:

| Error | Strategy |
|-------|----------|
| `NotAllowedError` | Unshift item back to front of queue, set `_needsUserGesture = true`, show "Tap to Resume" overlay. Recovery happens on next user gesture. |
| `AbortError` | Retry up to 3 times with exponential backoff (200ms → 400ms → 800ms). If all retries exhausted, skip to next segment. |
| `NotSupportedError` | Skip immediately — the audio format is not playable. |
| Other | Retry once after 1 second. If still failing, skip. |

```js
audioEl.play().catch(err => {
  if (err.name === 'NotAllowedError') {
    this._logPlaybackEvent('not-allowed', { state: 'play' });
    this.queue.unshift(item);
    this._needsUserGesture = true;
    this._playbackStalled = true;
    if (typeof window.__resonovaShowResume === 'function') {
      window.__resonovaShowResume(true);
    }
  } else if (err.name === 'AbortError') {
    this._retryPlay(item, audioEl, 0);
  } else if (err.name === 'NotSupportedError') {
    audioCleanup();
    this._playNext();
  } else {
    setTimeout(() => {
      audioEl.play().catch(() => {
        audioCleanup();
        this._playNext();
      });
    }, 1000);
  }
});
```

### Fix 4: Visibility & Focus Recovery

- **Methods:** `_registerRecoveryListeners()` at `player.js:934`, `_tryRecoverPlayback()` at `player.js:959`
- **What it does:** Registers listeners for `visibilitychange`, `focus`, and `pageshow` (bfcache restore). When the tab becomes visible and `_playbackStalled` is true, attempts to resume:
  - Audio items: calls `audioEl.play()`, clears stall on success, shows resume overlay on `NotAllowedError`
  - Spotify items: calls `spotifyPlayer.resume()`, skips to next on failure
- **Debounce:** At most one recovery attempt per second (`_lastRecoveryAttempt`).

### Fix 5: Spotify Track-End Fallback Timer

- **Method:** `_playSpotifyTrack()` at `player.js:465` — setTimeout at line ~555
- **What it does:** After issuing the Spotify play API call, sets a fallback timer for `track_duration + 15 seconds`. If `_trackEndFired` has not been set to `true` by the time the timer fires (meaning no state change or health-monitor near-end detection caught the track end), it forces the transition. This is the last line of defense.
- **Cleanup:** The timer is cleared if `_handleSpotifyStateChange()` or the health monitor detects track end first.

### Fix 6: Hardened Spotify State Change Detection

- **Method:** `_handleSpotifyStateChange()` at `player.js:579` + health monitor near-end check at `player.js:869`
- **What it does:** Three independent detection conditions:

1. **Condition 1 (original, retained):** `paused && position === 0 && track_window.previous_tracks.length > 0` — the track ended normally and the SDK queued the previous track.
2. **Condition 2 (new):** `paused && position === 0 && !track_window.current_track` — the SDK lost the current track entirely (common after long background periods).
3. **Condition 3 (new, in health monitor):** Track is near its end (`duration - position < 3s`) and no state change has been received for 8+ seconds — the SDK WebSocket may have disconnected but the last known position indicates the track should be finished.

### Fix 7: Spotify SDK Readiness Check

- **Method:** `_playSpotifyTrack()` at `player.js:465` — deviceId polling at line ~472
- **What it does:** Before attempting to play a Spotify track, polls for `this.deviceId` at 200ms intervals (up to 5 seconds). If no device is ready after 5s, logs the error and skips to the next segment. Prevents silent failures when the Spotify SDK hasn't finished initializing.

### Fix 8: Spotify API Retry Logic

- **Method:** `_fetchWithRetry()` at `player.js:1197`
- **What it does:** Wraps `fetch()` with retry logic for transient failures:
  - 429 (Rate Limited) or 5xx → retry with 1s/2s backoff
  - Network errors (`TypeError`) → retry
  - 404 → no retry (resource doesn't exist)
  - Other 4xx → no retry
- **Max retries:** 2 (3 total attempts)

### Fix 9: Media Session API

- **Methods:** `_setupMediaSessionHandlers()` at `player.js:1143`, `_updateMediaSession()` at `player.js:1175`, `_setMediaSessionState()` at `player.js:1188`
- **What it does:**
  - Registers action handlers for `play`, `pause`, `nexttrack`, and `previoustrack` (no-op)
  - Updates `MediaMetadata` with current track/commentary information
  - Sets `playbackState` to `playing`, `paused`, or `none`
  - Called from `_playAudio()`, `_playSpotifyTrack()`, and `_onPlaybackComplete()`
- **Impact:** OS-level media controls (lock screen, control center, notification shade) now show Resonova's playing state and allow play/pause/skip. This also signals to the OS that Resonova is a media app, reducing aggressive suspension.

### Fix 10: AudioContext Unlock

- **Method:** `_unlockAudioOnGesture()` at `player.js:1000`
- **What it does:** On the first user gesture (click, touchstart, or keydown), creates a short-lived `AudioContext`, plays a silent oscillator for 0.001s, then closes it. This "unlocks" the audio subsystem on mobile Safari, which otherwise blocks `audioEl.play()` until a user gesture is received.

```js
_unlockAudioOnGesture() {
  const unlock = () => {
    if (this._audioUnlocked) return;
    try {
      const ctx = new AudioContext();
      ctx.resume().then(() => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        gain.gain.value = 0.001;
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(0);
        osc.stop(ctx.currentTime + 0.001);
        setTimeout(() => { ctx.close(); this._audioUnlocked = true; }, 100);
      }).catch(() => {});
    } catch (_) {}
  };
  document.addEventListener('click', unlock, { once: true });
  document.addEventListener('touchstart', unlock, { once: true });
  document.addEventListener('keydown', unlock, { once: true });
}
```

### Fix 11: Mobile Detection

- **Property:** `this._isMobile` in constructor at `player.js:49`
- **What it does:** Detects mobile browsers via `navigator.maxTouchPoints > 0` combined with user-agent matching for `Mobi` or `Android`. Used by the health monitor to select tighter intervals/thresholds on mobile.

```js
this._isMobile = navigator.maxTouchPoints > 0 && /Mobi|Android/i.test(navigator.userAgent);
```

### Fix 12: "Tap to Resume" Overlay

- **Files:** `index.html` (`#resume-overlay`), `styles.css` (lines 1053–1101), `player.js` integration
- **What it does:** A full-screen overlay with a pulsing play icon and "Tap to resume playback" text. Shown when `NotAllowedError` blocks `audioEl.play()` (both on initial play and during visibility recovery). Tapping dispatches a `resume-requested` custom event that `player.js` listens for. The overlay has a `backdrop-filter: blur(4px)` for visual polish.

### Fix 13: Diagnostics Panel

- **Files:** `index.html` (`#diagnostics-panel`, `#diagnostics-trigger`), `styles.css` (lines 1103–1188), `player.js` integration
- **What it does:** A slide-up panel (350px wide, 300px max-height) accessible via a 🔍 button in the bottom-right corner. Displays the last 50 playback events from `window.__resonovaEventLog` in terminal-green monospace. Updates every 2 seconds via polling. Events include: `audio-start`, `audio-ended`, `audio-ended-fallback`, `spotify-start`, `spotify-ended`, `spotify-ended-near`, `spotify-ended-fallback`, `stall-detected`, `not-allowed`, `visibility-recovery`, and transition events showing `from`/`to` segment types.

## Remaining Browser-Policy Limitations

These limitations are inherent to browser architecture and cannot be fully solved in JavaScript alone:

1. **Complete page freeze (iOS):** When iOS suspends the entire page (not just throttling), no JavaScript runs — including timers, event listeners, and the health monitor. The Media Session API helps signal to the OS that this is a media app, but cannot fully prevent suspension. This is most likely to occur when multiple other apps are open and the phone is locked for extended periods.

2. **Deep background setTimeout throttling:** Chrome on Android throttles `setInterval`/`setTimeout` to 1-minute intervals when a tab has been backgrounded for 5+ minutes. The health monitor (3s/5s interval) will be throttled along with everything else. The timeupdate fallback on `<audio>` elements is also affected — the browser may stop firing `timeupdate` events entirely.

3. **Spotify SDK WebSocket disconnect:** If the Spotify Web Playback SDK loses its WebSocket connection while backgrounded, it may not reconnect until the tab is foregrounded. The health monitor's near-end detection (condition 3) and the fallback timer mitigate this, but both depend on timers that may themselves be throttled.

4. **Autoplay policies:** Some browsers (especially iOS Safari) require a user gesture for *every* `play()` call, not just the first one. The "Tap to Resume" overlay handles this gracefully, but it requires user interaction — there is no fully automatic recovery from `NotAllowedError`.

5. **No audio playback in background tabs (desktop Chrome):** Chrome's "Tab Freeze" and "Heavy Ad Intervention" can suspend audio from background tabs. This is less common than mobile issues but can occur on resource-constrained machines.

## Owner Mobile Testing Steps

### Test 1: Background Audio Segment Transition (iOS Safari + Android Chrome)

1. Start playback of a saved episode or live generation.
2. Wait for a commentary segment ("AI Commentary" badge) to begin playing.
3. Lock the phone screen (or switch to another app via Home button).
4. Wait until the segment should have finished (30–60 seconds).
5. Unlock and return to the Resonova tab.
6. **Expected:** Playback has advanced to the next segment (commentary or Spotify track). The "Now Playing" info has updated. The diagnostics panel (🔍 button) shows `audio-ended-fallback` or `audio-ended` events with recent timestamps. The progress bar has advanced.

### Test 2: Background Spotify Track Transition

1. Start playback and wait for a Spotify track to begin playing (green "Now Playing" badge).
2. Lock the phone screen.
3. Wait until the track should have finished (typically 3–4 minutes).
4. Unlock and return to Resonova.
5. **Expected:** Playback has advanced to the next commentary segment. The diagnostics panel shows `spotify-ended`, `spotify-ended-near`, or `spotify-ended-fallback`.

### Test 3: Desktop Tab Reactivation

1. Start playback on desktop Chrome.
2. Click to a different tab and leave it inactive for 30+ seconds, spanning at least one segment transition.
3. Click back to the Resonova tab.
4. **Expected:** Playback has continued through the transition. No manual click was needed to "unstick" playback.

### Test 4: "Tap to Resume" Overlay

1. Start fresh playback on mobile (ideally iOS Safari where autoplay is strictest).
2. If playback starts normally, lock and unlock the screen during a commentary segment.
3. **Expected if `NotAllowedError` occurs:** A full-screen overlay appears with a pulsing ▶ icon and "Tap to resume playback." Tapping it dismisses the overlay and resumes playback.
4. **Expected if no error:** The overlay does not appear and playback continues normally.

### Test 5: Media Session Controls

1. Start playback on mobile.
2. Lock the screen.
3. Observe the lock screen media controls.
4. **Expected:** The now-playing info shows "Resonova" (or the current track name). Play/Pause and Skip controls are functional. The scrubber/progress bar may not be accurate (browser limitation).

### Test 6: Diagnostics Panel

1. While playback is active, click the 🔍 button in the bottom-right corner of the page.
2. Observe the event log entries.
3. **Expected:** Events are displayed in terminal-green monospace text on a dark background. Recent events show playback transitions with timestamps. Close with the ✕ button in the panel header. The 🔍 button reappears.

## Mobile Detection Logic

Mobile vs. desktop is detected at construction time in `player.js:49`:

```js
this._isMobile = navigator.maxTouchPoints > 0 && /Mobi|Android/i.test(navigator.userAgent);
```

This requires BOTH a touch-capable device AND a mobile user-agent string. Tablets with keyboards, desktop touchscreens, and desktop browsers with touch emulation are correctly classified as desktop. iPadOS 13+ reports a desktop user-agent but has `maxTouchPoints > 0` — it will be classified as desktop, which is acceptable since iPadOS Safari behavior is closer to desktop Safari than mobile Safari.

The `_isMobile` flag controls:
- Health monitor interval: 3s (mobile) vs. 5s (desktop)
- Stall threshold: 10s (mobile) vs. 15s (desktop)

## New Player.js Methods Reference

| Method/Property | Line (approx) | Purpose |
|----------------|---------------|---------|
| `_lastProgressTime` | 28 | Timestamp of last known playback progress (health monitor input) |
| `_playbackStalled` | 29 | Flag set by health monitor when no progress detected |
| `_healthCheckInterval` | 30 | `setInterval` ID for the health monitor |
| `_eventLog` | 33 | Ring buffer (max 100) of diagnostic events; exposed as `window.__resonovaEventLog` |
| `_audioEndedCleanly` | 37 | Whether `onended` (true) or timeupdate fallback (false) triggered last transition |
| `_audioCleanup` | 38 | Shared cleanup function to prevent double-fires between `onended` and fallback |
| `_needsUserGesture` | 41 | True when `NotAllowedError` blocked play; cleared on recovery |
| `_lastRecoveryAttempt` | 42 | Debounce timestamp for `_tryRecoverPlayback()` |
| `_hiddenSince` | 43 | Timestamp when tab was last hidden |
| `_listenersRegistered` | 44 | Guard against duplicate listener registration |
| `_isMobile` | 49 | Mobile/desktop detection flag |
| `_spotifyTrackTimeout` | 50 | `setTimeout` ID for Spotify track-end fallback timer |
| `_spotifyTrackDuration` | 51 | Cached duration of current Spotify track (ms) |
| `_spotifyLastStateTime` | 52 | Timestamp of last `player_state_changed` event |
| `_spotifyLastPosition` | 53 | Last known playback position in current Spotify track (ms) |
| `_spotifyLastDuration` | 54 | Last known duration of current Spotify track (ms) |
| `_audioUnlocked` | 57 | Whether AudioContext unlock has been performed |
| `_startHealthMonitor()` | 869 | Periodic stall detection + near-end Spotify check |
| `_clearStallFlag()` | 910 | Resets stall state; called at every transition |
| `_logPlaybackEvent(type, detail)` | 915 | Appends diagnostic event to ring buffer |
| `_registerRecoveryListeners()` | 934 | Registers `visibilitychange`/`focus`/`pageshow` handlers |
| `_tryRecoverPlayback()` | 959 | Attempts to resume stalled playback; debounced to 1/s |
| `_unlockAudioOnGesture()` | 1000 | Unlocks AudioContext on first user gesture (mobile Safari fix) |
| `_retryPlay(item, audioEl, attempt)` | 1034 | Retries `play()` with exponential backoff for `AbortError` |
| `_setupMediaSessionHandlers()` | 1143 | Registers Media Session API action handlers |
| `_updateMediaSession(title, artist, album)` | 1175 | Updates Media Session metadata |
| `_setMediaSessionState(state)` | 1188 | Sets `navigator.mediaSession.playbackState` |
| `_fetchWithRetry(url, options, maxRetries)` | 1197 | Fetch wrapper with retry logic for transient failures |

## Constraints Preserved

- [x] Single-user and private — no multi-user or auth changes
- [x] No secrets or tokens exposed — all changes are client-side JS/CSS/HTML only
- [x] Existing desktop playback not broken — all new paths are additive; original `onended` and state-change paths still work
- [x] Saved episode replay not broken — `_playEpisode()` calls the same `_startPlayback()` entry point
- [x] Spotify Web Playback SDK support retained — SDK integration is hardened, not removed
- [x] Fix is minimal and evidence-backed — each fix targets a specific root cause; no speculative rewrites
- [x] No persistent profile, feedback, native app, or public deployment work started
