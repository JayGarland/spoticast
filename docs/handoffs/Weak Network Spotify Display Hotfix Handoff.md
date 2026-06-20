# Weak Network Spotify Display Hotfix Handoff

Created: 2026-06-20
Status: chef hotfix implemented

## Trigger

Desktop test showed the app had advanced to a Spotify segment (`Seg type: spotify`), but the visible now-playing text still showed the previous commentary:

- title: `AI Commentary`
- subtitle: `Podcast Intro`
- next-up: previous track context
- diagnostic segment type: `spotify`

The owner also asked whether weak network such as H+ can still halt playback.

## Changes

Files changed:

- `resonova/web/player.js`
- `resonova/web/index.html`

Behavior:

- Spotify segments now set a neutral now-playing state immediately:
  - title: `Spotify music` unless cached metadata is already available
  - subtitle: `Connecting to Spotify...`
- stale `Up next` text is cleared as soon as a Spotify segment begins.
- Spotify metadata fetch failure is recorded as `track:metadata:fail` instead of leaving stale commentary UI.
- local API fetches and Spotify Web API fetches now use bounded `AbortController` timeouts:
  - local API: 12s
  - transfer/play/track metadata: 8s
  - Connect device polling request: 1.5s per attempt
- frontend cache-bust changed to `20260620-weak-network-fix`.

## Validation

Passed:

```powershell
node --check resonova/web/player.js
uv run python -c "from resonova import server; print('server ok')"
uv run python tests/test_variety_episodes.py
git diff --check
curl smoke checks against running server
```

## Product Limit

This does not guarantee Spotify music will play smoothly on H+ or weak mobile data. It prevents indefinite waiting and stale UI. If Spotify cannot confirm playback quickly enough, the app should now move into the existing recovery/fallback path instead of looking like it is playing the wrong segment.
