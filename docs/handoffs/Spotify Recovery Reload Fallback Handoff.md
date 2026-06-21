# Spotify Recovery Reload Fallback Handoff

Created: 2026-06-21
Status: chef hotfix implemented

## Trigger

Customer pressed Recover repeatedly without reloading the page. The timeline showed repeated failures:

```text
recovery:start
recovery:fail Spotify device is ready in SDK but not visible to Spotify Connect
...
recovery:start
recovery:fail Spotify device is ready in SDK but not visible to Spotify Connect
```

After a full page refresh, playback worked.

## Diagnosis

The old in-memory JavaScript session could not repair the Spotify Connect device. A full reload rebuilt the page, SDK instance, auth callback path, and Spotify device registration from a clean browser state.

The previous hidden-page hotfix still requires a reload to be loaded into the running page. This handoff adds a future-facing fallback so users are not trapped pressing Recover forever.

## Changes

Files changed:

- `resonova/web/player.js`
- `resonova/web/index.html`

Behavior:

- Track consecutive Spotify recovery failures.
- Reset the failure count after recovery success.
- After 2 recovery failures, recommend reload:
  - now-playing title: `Spotify session stale`
  - subtitle: `Reload player to reconnect Spotify`
  - event: `recovery:reload-recommended`
- The Recover button changes to `Reload Player`.
- Clicking `Reload Player` records `recovery:reload-click` and calls `location.reload()`.
- Frontend cache-bust changed to `20260621-reload-fallback`.

## Product Rationale

Manual reload is already proven to resolve this failure class. This change turns that hidden workaround into an explicit recovery path after bounded retry failure.

## Validation

Run:

```powershell
node --check resonova/web/player.js
uv run python -c "from resonova import server; print('server ok')"
uv run python tests/test_variety_episodes.py
git diff --check
```
