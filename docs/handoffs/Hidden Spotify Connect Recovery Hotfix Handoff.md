# Hidden Spotify Connect Recovery Hotfix Handoff

Created: 2026-06-21
Status: chef hotfix implemented

## Trigger

Customer timeline:

```text
06:49:34 visibilitychange hidden
06:50:48 play:cmd:start ...
06:50:53 play:cmd:fail 404:device-not-visible
06:50:53 device:discard Spotify device is not visible in Connect devices
06:50:53 recovery:start
06:50:57 visibilitychange visible
06:50:57 device:ready gen=2 ...
06:51:02 recovery:fail Spotify device is ready in SDK but not visible to Spotify Connect
06:51:02 play:start:failed Spotify device could not be registered with Spotify Connect after recovery
```

## Diagnosis

This was not an offline failure and not the blind-playback branch.

The app attempted to start a new Spotify segment while the page was hidden/backgrounded. The SDK device then became stale or invisible to Spotify Connect. Recovery rebuilt a device after the page became visible, but the current 5s Connect-visibility wait expired before Spotify listed the new device.

## Changes

Files changed:

- `resonova/web/player.js`
- `resonova/web/index.html`

Behavior:

- `_playSpotifyTrack()` now defers a fresh Spotify segment if `document.visibilityState !== 'visible'`.
- Deferred hidden playback records `play:spotify:deferred-hidden`.
- The UI shows:
  - `Spotify waiting for phone unlock`
  - `Return to resume or use Skip Music`
- The item is marked recoverable/unhealthy so `visibilitychange visible` triggers the existing foreground recovery path.
- Recovery Connect-visibility wait increased from 5s to 12s.
- Frontend cache-bust changed to `20260621-hidden-spotify-defer`.

## Product Tradeoff

This does not guarantee seamless locked-screen transition into a brand-new Spotify segment. The customer log shows that attempting that in the hidden page state can poison the Spotify Connect device.

The chosen behavior is controlled degradation:

- do not start a new Spotify segment while hidden
- resume/recover when the page becomes visible
- keep `Skip Music` available as fallback

## Validation

Run:

```powershell
node --check resonova/web/player.js
uv run python -c "from resonova import server; print('server ok')"
uv run python tests/test_variety_episodes.py
git diff --check
```

Expected next phone timeline:

```text
visibilitychange hidden
play:spotify:deferred-hidden ...
visibilitychange visible
recovery:start
device:ready ...
recovery:success
play:cmd:start ...
play:cmd:ok ...
```

If recovery still fails, the next useful field is whether device visibility becomes true after 12s or remains absent from Spotify Connect.
