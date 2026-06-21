# Generation Complete State Race Handoff

Date: 2026-06-21

## Problem

Boss reported the player still showed `Episode Progress ... · generating…` even though generation had actually finished.

## Root Cause

The server set `job.status = "done"` before pushing the `done` SSE event. The stream loop can wake during that window, see `job.status in ("done", "error")`, and close before the `done` event is drained to the browser. When the browser misses `done`, `_generationComplete` stays `false`, so `_updateProgress()` keeps rendering the `· generating…` suffix.

## Change

- `resonova/server.py`
  - Pushes the `done` SSE event before setting `job.status = "done"`.
- `resonova/web/player.js`
  - Starts a bounded saved-episode confirmation check after `outro_ready`.
  - If `/api/episodes/{episodeId}` exists, marks generation complete, updates progress/buttons, and refreshes Past Episodes.
  - Clears the confirmation check when the normal `done` event arrives.
- `resonova/web/index.html`
  - Bumps the `player.js` cache-bust version.

## Validation

- `node --check resonova/web/player.js` passed.
- `uv run python -m py_compile resonova/server.py` passed.
- `uv run python -c "from resonova import server; print('server ok')"` passed.
- `uv run python tests/test_variety_episodes.py` passed.

## Boss Test

Generate a cast and let it finish. Once the saved episode exists, the player should stop showing `· generating…` even if the browser misses the final SSE `done` event.

## Remaining Risk

If saving the episode fails, the suffix should remain until the error path runs. This fix is for the missed-`done` completion race, not generation failure handling.
