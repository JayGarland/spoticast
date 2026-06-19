# Mobile Spotify SDK Lifecycle Diagnosis Handoff

## Purpose

This handoff adds visible SDK lifecycle diagnostics to the mobile playing screen so the owner can see exactly which SDK lifecycle event fails on mobile. The previous diagnostic only showed Spotify playback state (which never arrives on mobile). Now every SDK event — from script load through connect(), ready, errors — is captured and displayed. Also fixes a bug where the diagnostic panel froze on segment transitions.

## Files Changed

| File | Change | Lines | Summary |
|---|---|---|---|
| `resonova/web/player.js` | 4 changes | — | Added `_lifecycle` object, rewrote `_initSpotifyPlayer()` listeners, extended `_renderDiagnostics()` with lifecycle section, added `_playNext()` re-render |
| `resonova/web/styles.css` | 1 change | — | Added `.spotify-diag-sep` divider rule |
| `resonova/web/index.html` | NOT modified | — | — |

`resonova/web/player.js` — 4 changes:
1. Constructor: added `this._lifecycle` object (15 fields tracking all SDK events + context)
2. `_initSpotifyPlayer()`: rewritten to capture lifecycle state in every listener; added missing `playback_error` and `autoplay_failed` listeners; captured `connect()` result (was discarded)
3. `_renderDiagnostics()`: extended with `const lc = this._lifecycle`, added divider + 14 lifecycle rows between Spotify state and Refresh button
4. `_playNext()`: added `this._renderDiagnostics(null)` after `_updateSkipButton()` to refresh panel on every segment transition

`resonova/web/styles.css` — 1 change:
- Added `.spotify-diag-sep` divider rule (1px line between state and lifecycle sections)

`resonova/web/index.html` — NOT modified

## New Diagnostic Fields (Lifecycle Section)

Below the existing Spotify state rows, after a thin divider, these 14 lifecycle rows now appear:

| Field | Source | Values | Warn When |
|---|---|---|---|
| SDK loaded | `lc.sdkLoaded` | yes / no | — |
| Player built | `lc.playerConstructed` | yes / no | — |
| connect() | `lc.connectResult` | success / … / not called / error: … | connectCalled but no result yet |
| ready | `lc.ready` | yes / no | no (red) |
| device_id | `lc.deviceId` | actual ID or - | null / - (red) |
| not_ready | `lc.notReady` | yes / no | — |
| init_error | `lc.initError` | message or - | non-null (red) |
| auth_error | `lc.authError` | message or - | non-null (red) |
| acct_error | `lc.accountError` | yes / no | — |
| playback_err | `lc.playbackError` | message or - | non-null (red) |
| autoplay_fail | `lc.autoplayFailed` | yes / no | — |
| SecureCtx | `lc.isSecureContext` | true / false | false (red) |
| Protocol | `lc.protocol` | http: / https: | — |
| UA | `lc.userAgent` | truncated to 48 chars | — |

## Bug Fix: Segment Transition Re-render

**Problem:** The diagnostic panel was only updated from `_handleSpotifyStateChange`, which never fires on mobile. The panel froze after `_startPlayback`, showing stale values (Seg type="-", Queue frozen).

**Fix:** Added `this._renderDiagnostics(null)` in `_playNext()` after `_updateSkipButton()` and before the type branch. Now the panel refreshes on every segment transition — Seg type, Queue count, and all lifecycle fields update immediately.

## Validation Results

All checks passed:
- `node --check resonova/web/player.js` — no syntax errors
- `git diff` confirms only diagnostic additions, no playback changes
- `index.html` untouched
- All 13 acceptance criteria PASS
- All 6 hard constraints PASS

## Owner Mobile Result

The owner tested this diagnostic on mobile during a Spotify music segment and observed:

```text
Now Playing: Reason Why / Tram
Seg type: spotify
Queue: 11
SDK loaded: yes
Player built: yes
connect(): success
ready: no
device_id: -
init_error: Failed to initialize player
SecureCtx: false
Protocol: http:
UA: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/5...
```

Gate conclusion:

- The queue transition is working. The UI reaches the Spotify segment.
- The SDK script loads, the player is constructed, and `connect()` resolves.
- The SDK never registers a playable Spotify Connect device on mobile.
- The strongest blocker is `SecureCtx=false` on `http:`. The Spotify player depends on browser media/DRM APIs that require a secure context on mobile browsers.
- The next implementation should focus on serving the private phone URL over HTTPS, not on playback retry loops.

## Owner Mobile Test Steps

1. Start server: `python -m uvicorn resonova.server:app --host 0.0.0.0 --port 8765`
2. On mobile phone, navigate to `http://<server-ip>:8765`
3. Authenticate with Spotify
4. Generate/play an episode with Spotify segments
5. When the playing screen appears, scroll to the diagnostic panel at the bottom
6. Observe the lifecycle section BELOW the thin divider line

**What to watch for:**
- Focus on rows 4-6: **ready**, **device_id**, **not_ready**
- If `ready = no` and `device_id = -` and no error appears → the SDK simply never fires the ready event on mobile
- If `init_error` or `auth_error` has a message → read the error text
- If `connect() = not called` → SDK script may not have loaded
- Compare `SecureCtx`, `Protocol`, and `UA` between desktop (working) and mobile (failing)

## How to Interpret the Lifecycle Output

### The Key Question: Which event fails?

The lifecycle rows show a complete timeline of SDK initialization. On desktop, the expected sequence is:

```
SDK loaded → yes
Player built → yes
connect() → success
ready → yes
device_id → (some hex ID)
```

On mobile, one of these steps fails. The diagnostic will show exactly which one:

- **connect() = "not called"**: The Spotify SDK script never loaded. Check `SDK loaded = no`. Possible causes: script blocked by mobile browser, network issue.
- **connect() = "success" but ready = "no"**: The SDK connected but the ready callback never fired. This is the most likely mobile failure mode — the browser may be preventing the SDK from acquiring an audio context or registering a device.
- **init_error / auth_error has a message**: Read the error. Auth errors mean the token flow failed. Init errors may indicate the SDK couldn't initialize on this browser.
- **SecureCtx = "false"**: The Spotify Web Playback SDK requires a secure context (HTTPS or localhost). If the mobile browser shows `http:` with `SecureCtx = false`, the SDK will not work.

### Next Recommended Fix

Based on which lifecycle event fails:
- If `ready` never fires: investigate mobile browser audio context policies, consider a user-gesture-initiated `player.resume()` or `player.activateElement()`
- If `connect()` fails: investigate network, CORS, or browser blocking of third-party scripts
- If `SecureCtx = false`: ensure HTTPS or use localhost tunneling
- If `init_error`: read the message — may indicate browser incompatibility

## Design Decisions

- Lifecycle state is stored in `this._lifecycle` (not scattered across instance properties) — one object to inspect in console if needed
- `connect()` result captured via `.then()` / `.catch()` on the returned Promise — was previously discarded
- Every lifecycle listener calls `_renderDiagnostics(null)` — panel updates immediately when any event fires, no polling needed
- `_playNext()` re-render uses `null` state — existing Spotify state fields show their "waiting" fallback values, lifecycle fields show current actual state
- Divider separates Spotify playback state (dynamic, per-track) from lifecycle state (one-time, per-session) — makes it easy to focus on the right section

## Known Limitations

- connect() result appears asynchronously — may show "…" briefly before resolving to "success" or "error: …"
- The `playback_error` and `autoplay_failed` events are newly registered but were never tested (they never fired before on any platform)
- The diagnostic panel is visible on desktop too, not mobile-exclusive
- If the SDK script never loads at all (network blocks `sdk.scdn.co`), `_initSpotifyPlayer` is never called and `_lifecycle.sdkLoaded` stays `false` — but `window.onSpotifyWebPlaybackSDKReady` may also never fire, so there's no callback to update the diagnostic. The SDK loaded field will correctly show "no" from the initial state.
