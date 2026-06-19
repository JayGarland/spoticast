# Mobile Playback Baseline Validation Handoff

**Date:** 2026-06-19
**Status:** Validation baseline established — awaiting owner mobile testing
**Commit:** b0347e0 "Rollback failed mobile playback recovery"

---

## Strategy-Layer Gate Review

Manager agent used:

```text
gem-orchestrator / gem-team
```

Gate review checked:

- Manager response.
- This handoff file.
- `git status`.
- `git diff`.

Git result at review:

```text
Working tree has one new untracked handoff file:
docs/handoffs/Mobile Playback Baseline Validation Handoff.md
No code changes were made by this manager task.
```

Owner live test after this handoff:

```text
Mobile active-page transition now reaches the Spotify segment,
but Spotify music is silent / does not audibly play.
```

Updated interpretation:

- The current rollback baseline no longer shows the failed "Tap to resume" overlay loop.
- The mobile queue can enter the Spotify segment.
- The current failure is narrower: Spotify Web Playback SDK device/playback activation on mobile is not producing audible music.
- This supports the manager's recommended next path: minimal SDK activation and instrumentation before any fallback/product downgrade.

Gate decision:

```text
Accept this handoff as a diagnostic baseline.
Do not accept commentary-only fallback yet.
Next implementation should be minimal SDK activation + autoplay/playback instrumentation.
```

---

## 1. Git State

- **HEAD:** b0347e0 "Rollback failed mobile playback recovery"
- **Branch:** main (ahead of origin/main by 10 commits)
- **Working tree:** clean (nothing to commit)
- **Rollback commits in reverse order:**
  - b0347e0 — Rollback failed mobile playback recovery
  - 19a15fa — Require Spotify progress before end detection (rolled back)
  - f2bd5bf — Guard mobile Spotify false end detection (rolled back)
  - 9d723a6 — Advance ended commentary after background wake (rolled back)
  - b0f1a75 — Prevent Spotify segment skip on mobile recovery (rolled back)
  - b3bffcd — Record mobile playback validation failure (rolled back)
  - d4296a3 — Improve private mobile playback reliability (rolled back)

---

## 2. Frontend Baseline Confirmed

All three frontend files confirmed back to pre-recovery baseline:

| File | Lines | Previous impl | Rollback status |
| ------ | ------ | -------------- | ----------------- |
| `resonova/web/player.js` | 666 | Was ~1,290 | Clean — no health monitor, Media Session, overlay, mobile detection, audio cleanup, retry logic, or resume integration |
| `resonova/web/index.html` | ~337 | Was ~415 | Clean — no resume-overlay, diagnostics-panel, or __resonova globals |
| `resonova/web/styles.css` | ~1,049 | Was ~1,186 | Clean — no resume-overlay or diagnostics-panel styles |

Verification: Grep confirmed zero matches for these patterns from the failed implementation:
`_healthCheck`, `_logPlaybackEvent`, `_tryRecoverPlayback`, `_startHealthMonitor`, `MediaSession`,
`activateElement`, `autoplay_failed`, `_audioCleanup`, `_markSpotifyStalled`, `_needsUserGesture`,
`_isMobile`, `_unlockAudioOnGesture`, `__resonovaShowResume`, `__resonovaEventLog`

---

## 3. Spotify Web Playback SDK — Official Mobile Support

### 3.1 Official Stance

**Source:** <https://developer.spotify.com/documentation/web-playback-sdk/>

> "The Web Playback SDK is supported by most web browsers (Chrome, Firefox, Safari and Microsoft Edge) in both mobile (Android and iOS) and Desktop (macOS, Windows and Linux)."

**Verdict:** Mobile is OFFICIALLY supported. The SDK is not archived or deprecated for mobile.

### 3.2 Documented iOS Limitations

**Source:** SDK Troubleshooting page

> "iOS support has some limitations: The playback does not start automatically after transfering playback. The user must interact with the SDK events to play audio."

### 3.3 Critical API: `activateElement()`

**Source:** SDK Reference — Spotify.Player#activateElement

> "Some browsers prevent autoplay of media by ensuring that all playback is triggered by synchronous event-paths originating from user interaction such as a click. In the autoplay disabled browser, to be able to keep the playing state during transfer from other applications to yours, this function needs to be called in advance. Otherwise it will be in pause state once it's transferred."

**Resonova baseline status:** `activateElement()` is NEVER called. This is a critical gap.

### 3.4 Critical Event: `autoplay_failed`

**Source:** SDK Reference — Events

> "Emitted when playback is prohibited by the browser's autoplay rules. Check Spotify.Player#activateElement for more information."

**Resonova baseline status:** `autoplay_failed` is NEVER listened for. This is a critical gap.

### 3.5 Critical Error: `initialization_error`

**Source:** SDK Reference — Errors

> "Emitted when the Spotify.Player fails to instantiate a player capable of playing content in the current environment. Most likely due to the browser not supporting EME protection."

**Resonova baseline status:** Listeners exist for `initialization_error`, `authentication_error`, and `account_error`, but NOT for `playback_error`.

### 3.6 iOS `setVolume` No-Op

**Source:** SDK Reference — Spotify.Player#setVolume

> "On iOS devices, the audio level is always under the user's physical control. The volume property is not settable in JavaScript."

**Resonova baseline status:** `setVolume(0.85)` is called in both `_initSpotifyPlayer` (constructor option) and `_playSpotifyTrack` (line ~372). On iOS this is a no-op — harmless but irrelevant.

### 3.7 SDK Built-in Media Session

**Source:** SDK Reference — Spotify.Player constructor

> `enableMediaSession` (Boolean): "If set to true, the Media Session API will be set with metadata and action handlers. Default value is false."

**Resonova baseline status:** `enableMediaSession` is not set — not passed in the Player constructor options. The SDK has built-in Media Session support but Resonova doesn't use it.

### 3.8 Assessment

| Claim | Evidence | Verdict |
| ------ | ------ | ------ |
| "SDK is impossible on mobile" | Official docs say supported on mobile Chrome, Firefox, Safari, Edge | **FALSE** — needs correct usage |
| "SDK was archived in 2020" | Docs are live, SDK script loads from sdk.scdn.co, no archive notice | **FALSE** — still maintained |
| "activateElement must be called from user gesture" | Official SDK reference explicitly requires this | **TRUE** — Resonova doesn't do it |
| "autoplay_failed is the diagnostic signal" | Official SDK events reference documents this | **TRUE** — Resonova doesn't listen |
| "setVolume is no-op on iOS" | Official SDK reference explicitly states this | **TRUE** — known limitation |

---

## 4. Current Baseline Assessment

### 4.1 What Works (Desktop)

- Audio commentary segments play and transition via `audio.onended`
- Spotify tracks play via the SDK and transition via `player_state_changed`
- Crossfade between commentary and Spotify works
- Saved episode replay works
- Library browsing and generation work

### 4.2 Known Gaps in Baseline (Desktop + Mobile)

| Gap | Location | Impact |
| ------ | ------ | ------ |
| No `activateElement()` call | `_initSpotifyPlayer()` ~line 107 | On mobile, playback transfer may be blocked |
| No `autoplay_failed` listener | `_initSpotifyPlayer()` ~line 107 | Mobile autoplay blocks are invisible |
| No `playback_error` listener | `_initSpotifyPlayer()` ~line 107 | Track load/play failures are invisible |
| `onended` only trigger for audio→next | `_playAudio()` ~line 322 | If `onended` doesn't fire (background), queue stalls |
| `player_state_changed` only trigger for Spotify→next | `_handleSpotifyStateChange()` ~line 382 | If event doesn't fire (background), queue stalls |
| No `enableMediaSession` in SDK constructor | `_initSpotifyPlayer()` ~line 112 | No lock-screen controls on mobile |
| `play().catch()` silently skips | `_playAudio()` ~line 327 | Segment lost on any play failure |
| No visibility/focus recovery | player.js | Backgrounded tab stays stalled |

### 4.3 Mobile-Specific Risks (Baseline)

The baseline was never tested on mobile. The following are HYPOTHESES (not confirmed):

1. **H1:** `audio.onended` may not fire when page is backgrounded or screen locked
2. **H2:** `player_state_changed` may not fire when page is backgrounded or screen locked
3. **H3:** Spotify SDK `ready` event may not fire on mobile without proper gesture context
4. **H4:** `audioEl.play()` may reject with NotAllowedError on mobile without prior user gesture
5. **H5:** The "Connect Spotify" landing page click may or may not count as the required user gesture for SDK activation

### 4.4 What the Failed Implementation Got Wrong

1. Added ~624 lines of JavaScript fallback logic instead of using the SDK's built-in `activateElement()` and `autoplay_failed`
2. Created a race condition between `_clearStallFlag()` and `_markSpotifyStalled()`
3. Made `_markSpotifyStalled()` a dead-end that never advanced the queue
4. Added AudioContext unlock that doesn't help HTMLAudioElement
5. The fundamental mistake: treating the SDK as broken rather than incorrectly configured

---

## 5. Owner Mobile Test Checklist

Run these tests on the current baseline (commit b0347e0). All tests use the phone browser over Tailscale.

### Test 1: Desktop Replay (Baseline Integrity)

**Prerequisite:** Desktop browser, any saved episode

1. Open Resonova on desktop
2. Play a saved episode
3. Let it run through 3+ segments (commentary → Spotify → commentary → ...)
4. **Pass criteria:** Playback proceeds through all segments without stalling
5. **If fail:** DO NOT continue mobile tests — fix desktop first

### Test 2: Mobile Active-Page Commentary → Spotify Transition

**Prerequisite:** Mobile browser (iOS Safari or Android Chrome), page visible & active

1. Open Resonova on mobile over Tailscale
2. Generate a new episode or play a saved one
3. Keep the page visible and active
4. Watch the first commentary segment play through
5. **Pass criteria:** Commentary ends and Spotify music begins playing automatically
6. **If fail, collect:**
   - Does the Spotify SDK `ready` event fire? (check browser console for "Connected with Device ID" or any Spotify errors)
   - Does `audio.onended` fire? (add a console.log in the onended handler to check)
   - Does `audioEl.play()` reject? (check for "Audio play failed" in console)
   - What does the UI show? (segment type indicator, now-playing text)
   - Take a screenshot of any console errors

### Test 3: Mobile In-Page Skip from Commentary

**Prerequisite:** Mobile browser, page visible & active, episode playing commentary

1. During an AI commentary segment (not during Spotify music)
2. Press the Skip button
3. **Pass criteria:** Playback advances to the next item. If next is Spotify, Spotify plays.
4. **If fail, collect:**
   - Same diagnostics as Test 2
   - Does Skip advance to next commentary (skipping Spotify) or stall entirely?

### Test 4: Mobile Locked-Screen Transition

**Prerequisite:** Mobile browser, episode playing

1. Start an episode playing
2. During a commentary segment, lock the phone screen (or switch to another app)
3. Wait 60+ seconds (long enough for the segment to finish)
4. Unlock and return to Resonova in the browser
5. **Pass criteria:** Playback has advanced to the next segment (or at least is not stuck on the same segment)
6. **If fail, collect:**
   - Is it still on the same segment? (commentary text same)
   - Is it silent? (no audio playing)
   - Does interacting with the page (tap) resume anything?
   - Check console for any errors

### Test 5: "Tap to Resume" Behavior (Regression Check)

1. Verify the "Tap to resume" overlay does NOT appear (it was removed in rollback)
2. If audio stops, does the page respond to a tap by resuming playback?

### Evidence Collection for ALL Tests

For each test, collect:

- Phone model, OS version, browser name and version
- Exact time of test
- Screenshot of the UI state at the moment of failure
- Screenshot of browser console (how to open on mobile:
  - iOS Safari: connect to desktop Safari's Develop menu → select phone → console
  - Android Chrome: chrome://inspect on desktop → select device → console
  OR: Use a simple on-page console logger)

---

## 6. Recommended Next Implementation Path

**Priority order, based on official SDK documentation:**

### Path A (Recommended): Minimal SDK Activation + Instrumentation

This is the FIRST thing to try. It adds ~30 lines, not ~624.

1. **Call `activateElement()` from the "Connect Spotify" click handler:**
   - After `_initSpotifyPlayer()` succeeds, call `this.spotifyPlayer.activateElement()`
   - This must be called during a user gesture event path
   - The landing page "Connect Spotify" button click is the ideal time

2. **Listen for `autoplay_failed`:**
   - Add listener in `_initSpotifyPlayer()`
   - On `autoplay_failed`: log the event, show a visible UI indicator
   - This tells the owner definitively whether autoplay is the issue

3. **Listen for `playback_error`:**
   - Add listener in `_initSpotifyPlayer()`
   - On `playback_error`: log the error message
   - This catches track load/play failures

4. **Set `enableMediaSession: true` in the Player constructor:**
   - This enables the SDK's built-in Media Session API support
   - Gives lock-screen controls on mobile for free

5. **If the above fails to resolve mobile Spotify:**
   - Then consider the commentary-only fallback (Path B)

### Path B: Mobile Commentary-Only Fallback

Only pursue if Path A fails after collecting owner validation evidence.

1. Detect mobile in constructor
2. In `_playNext()`: if mobile and item type is 'spotify', skip with `_playNext()`
3. Result: mobile plays continuous commentary segments, desktop unchanged

### Path C: 30-Second Preview Fallback

Future enhancement only. Uses Spotify `/v1/tracks/{id}` `preview_url` field.

### What NOT to do

- Do NOT add health monitors or recovery timers — they add complexity without addressing root cause
- Do NOT add "Tap to resume" overlays — if autoplay is the issue, fix `activateElement()` first
- Do NOT add AudioContext unlock — irrelevant for HTMLAudioElement
- Do NOT add retry wrappers around SDK API calls — the SDK handles its own retries

---

## 7. Open Decisions for Strategy Layer

These questions should be answered by the product owner before the next implementation:

1. **Is mobile browser playback a hard requirement?** If yes, Path A (minimal SDK fix) is the next step. If mobile is "nice to have," Path B (commentary-only fallback) may be sufficient.

2. **Is "hands-free" (locked screen) playback required?** Both Path A and Path B will have limitations when the screen is locked. The browser may throttle or suspend the page regardless of SDK configuration.

3. **Should we consider a PWA?** A Progressive Web App with a manifest and service worker may improve background reliability by signaling "this is an app" to the OS.

4. **Is the "Connect Spotify" click sufficient as the user gesture?** The `activateElement()` call must happen during a user gesture event. The current flow has the user click "Connect Spotify" which triggers OAuth redirect and SDK initialization. The timing of `activateElement()` relative to this flow needs validation.

5. **Should we add on-page console logging for mobile testing?** Mobile browser consoles are hard to access. A simple on-page log panel would make owner testing much easier without requiring desktop Safari/Chrome remote debugging.

---

## 8. Constraints Preserved

- [x] Single-user and private — no auth changes
- [x] No secrets or tokens exposed in frontend
- [x] Desktop playback preserved (baseline confirmed)
- [x] Saved episode replay preserved
- [x] Spotify Web Playback SDK support retained (not removed)
- [x] No persistent profile or feedback work
- [x] No native app or public deployment work
- [x] No code implemented — validation/diagnosis only
