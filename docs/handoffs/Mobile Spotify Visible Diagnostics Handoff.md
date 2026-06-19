# Mobile Spotify Visible Diagnostics Handoff

## Purpose
A live diagnostic overlay was added to the Resonova player UI to help diagnose why mobile devices reach Spotify segments but produce no audible music. The diagnostic renders Spotify SDK state fields in real time as a fixed bottom overlay on the playing screen, giving the owner an immediate view of what the SDK believes is happening without needing remote debugging tools.

## Strategy-Layer Gate Review

Manager agent used:

```text
RUG
```

Gate review checked:

- Manager response.
- This handoff file.
- `git status`.
- `git diff`.
- Owner mobile validation result.

Owner validation result:

```text
On mobile, there was no apparent visible change.
```

Gate finding:

- The manager implementation created the diagnostic panel lazily only when `player_state_changed` fired.
- If mobile has no Spotify state event, the diagnostic panel never appears.
- The panel was appended at the bottom of the playing layout with very small text, so it could also be easy to miss on mobile.

Strategy-layer correction:

- The diagnostic panel is now rendered immediately when playback starts, before any Spotify event exists.
- It shows `waiting for Spotify state` while no SDK state has been received.
- The panel is now fixed at the bottom of the viewport with larger text and high z-index, so the owner can clearly see it on mobile.
- Follow-up correction: the panel was raised above the playback controls after owner testing showed it blocked the Skip button.

## Files Changed

| File | Change Type | Lines | Summary |
|---|---|---|---|
| `resonova/web/player.js` | Modified (5 changes) | ~30, 259, 388, 411-459, 461-468 | Added `_diagEl` constructor field, immediate `_renderDiagnostics(null)` call at playback start, `_renderDiagnostics` call in `_handleSpotifyStateChange`, `_renderDiagnostics` method, and `_refreshDiagnostics` method |
| `resonova/web/styles.css` | Modified (1 change) | 1050-1118 | Appended `.spotify-diag` and related CSS rules at end of file |
| `resonova/web/index.html` | Not modified | - | Diagnostic element is created lazily in JavaScript; no HTML changes needed |

## Exact Visible Fields Added

| Field | Source | Format |
|---|---|---|
| Paused | `state.paused` | `"yes"` / `"no"` / `"waiting"` |
| Position | `state.position` | `M:SS` |
| Duration | `state.duration` | `M:SS` |
| Track | `state.track_window.current_track.name` | truncated to 32 chars; `"waiting for Spotify state"` before first SDK event |
| Device ID | `this.deviceId` | `"yes"` / `"NO"` (red when `NO`) |
| Prev | `state.track_window.previous_tracks.length` | number |
| Seg type | `this.currentItem.type` | `"audio"` / `"spotify"` / `"-"` |
| Queue | `this.queue.length` | number |

A **"Refresh State"** button is rendered below the rows. Tapping it calls `spotifyPlayer.getCurrentState()` and re-renders the diagnostic panel with the latest SDK state.

## Validation Commands

```bash
# JavaScript syntax check
node --check resonova/web/player.js

# Start the server
python -m uvicorn resonova.server:app --host 127.0.0.1 --port 8765
```

**Note:** The Python import check (`python -c "from resonova.server import app"`) fails due to a pre-existing missing `uuid_extensions` dependency. This is unrelated to the diagnostic changes and does not affect the server when run via `uvicorn`.

## Owner Mobile Test Steps

1. Start the server on the machine with:
   ```
   python -m uvicorn resonova.server:app --host 0.0.0.0 --port 8765
   ```
2. On the mobile phone, navigate to `http://<server-ip>:8765` (use Tailscale IP if needed)
3. Authenticate with Spotify
4. Generate or play an episode that includes Spotify segments
5. When the playing screen appears, the diagnostic panel should be visible at the bottom of the viewport immediately
6. Observe the live-updating fields as the Spotify segment plays
7. Tap **"Refresh State"** to manually poll current Spotify state
8. Pay special attention to the **"Device ID"** row. If it shows `"NO"` in red, the SDK lost device registration.

## How to Interpret the Diagnostic Output

### Device ID (most important)
- `"yes"` = SDK has a registered device, so playback should work
- `"NO"` (red) = SDK lost device registration. **This is the prime suspect**. The `PUT /v1/me/player/play` call will fail silently because `deviceId` is `null`
- This can happen when the mobile browser backgrounds the page and the Spotify SDK disconnects

### Paused
- `"yes"` during a Spotify segment = track is paused, should be playing
- Combined with `Position:0` and `Prev>0` = track-end detection fired, expected behavior

### Position / Duration
- Position should increase over time during playback
- If Position stays at `0:00` and Paused is `"no"`, the SDK thinks it is playing but no audio is produced. This is likely a device output issue.

### Track
- Should show the expected track name
- If `"-"` appears, the Spotify API may not have returned track metadata

### Seg type
- Should show `"spotify"` during Spotify segments
- Shows what the player thinks is currently playing

### Queue
- Shows remaining items to play after the current one finishes

## Design Decisions

- Diagnostic is a fixed bottom overlay with high z-index, offset above the playback controls so the Skip button remains usable
- Diagnostic is a child of `#state-playing`, so it auto-hides when state changes away from playing
- Rendered immediately when playback starts, so it is visible even if the Spotify SDK never emits `player_state_changed`
- Called **before** the `currentItem.type` guard, so it shows last-known Spotify state even during commentary segments
- Opacity `1` for legibility on mobile during owner testing
- `deviceId: null` highlighted in red (`--on-air` color) to draw immediate attention to the prime suspect
- Element created lazily in JavaScript, so no `index.html` changes are needed

## Known Limitations

- The diagnostic is visible on desktop too (not mobile-exclusive)
- `innerHTML` replacement on every state change can cause minor flicker on very slow devices
- During audio/commentary segments, the displayed Spotify fields reflect the last Spotify state event (may be stale)
