# Episode Library Refresh After Generation Handoff

Date: 2026-06-21

## Problem

After a new cast finished generating, the Past Episodes section could remain visually stale. The client did call `_loadEpisodes()` on the SSE `done` event, but it ignored the completed `episode_id`, did not expand the matching playlist group, did not mark the new cast, and did not refresh again when returning to Library after playback.

## Change

- `resonova/web/player.js`
  - Parses the `done` event payload and captures `episode_id`.
  - Refreshes the episode library with a focused episode id after generation completes.
  - Expands the group that contains the newly generated cast.
  - Marks the newly generated cast with a temporary `New` badge.
  - Caches the completed episode detail in `localStorage` so the newly generated cast is immediately replayable from local cache.
  - Refreshes the library on return to Library if generation completed while the player was active and the earlier refresh did not land fresh data.
- `resonova/web/styles.css`
  - Adds a subtle highlighted card state and `New` badge.
- `resonova/web/index.html`
  - Bumps the `player.js` cache-bust version.

## Validation

- `node --check resonova/web/player.js` passed.
- `uv run python -c "from resonova import server; print('server ok')"` passed.
- `uv run python tests/test_variety_episodes.py` passed.
- `git diff --check -- resonova/web/player.js resonova/web/styles.css resonova/web/index.html` reported only the existing Git CRLF warning.

Note: `uv run pytest tests/test_variety_episodes.py` collected zero tests because that file is a script-style smoke test. The documented script invocation passed.

## Remaining Risk

This was not verified with a full real Spotify/Gemini generation in-browser during this pass. The fix is scoped to the client library refresh path and uses the existing server `done` payload: `{ episode_id, episode_name }`.
