# Background Spotify Transition Regression Handoff

Created: 2026-06-21
Status: chef hotfix implemented

## Trigger

Owner reported a regression:

- when Chrome is backgrounded, commentary reaches a music transition
- music does not play until the user reopens the page
- after reopening, recovery/reload can make music work

## Cause

The prior hidden-page hotfix was too conservative. It deferred every fresh Spotify segment while `document.visibilityState !== 'visible'`. That prevented the stale-device recovery loop, but it also blocked the desired background transition path entirely.

## Fix

Behavior is now:

1. Allow Spotify music start attempts while the page is hidden/backgrounded.
2. If Spotify Connect says the device is missing (`404` / device not visible) while hidden:
   - record `play:spotify:connect-missing-hidden`
   - mark Spotify unhealthy/recoverable
   - show `Spotify waiting for phone unlock`
   - do not start recovery while hidden
   - foreground recovery handles it when the user returns
3. If Spotify starts successfully in the background, no deferral happens.

## Files Changed

- `resonova/web/player.js`
- `resonova/web/index.html`

Frontend cache-bust updated to `20260621-background-attempt`.

## Expected Next Timeline

Successful background transition:

```text
visibilitychange hidden
play:cmd:start ...
play:cmd:ok 204
play:start:confirmed
```

Connect device missing while hidden:

```text
visibilitychange hidden
play:cmd:start ...
play:cmd:fail 404:device-not-visible
play:spotify:connect-missing-hidden ...
visibilitychange visible
recovery:start
...
```

## Validation

Run:

```powershell
node --check resonova/web/player.js
uv run python -c "from resonova import server; print('server ok')"
uv run python tests/test_variety_episodes.py
git diff --check
```
