# Next Up and Episode Library Regression Handoff

Date: 2026-06-21

## Assignment

Boss reported two regressions:

1. `Up next: <song>` still did not display in advance during AI commentary.
2. A newly generated cast still did not reliably appear in Past Episodes, making the user think the cast was lost unless the resume prompt appeared.

Chef delegated to RUG through Copilot CLI as `rug-agentic-workflow:rug-orchestrator`. The manager run exceeded a 10-minute timeout and did not create the required handoff. Chef stopped the lingering `copilot` process, inspected the partial diff, and made one narrow gate correction before validation.

## Root Cause

- `Up next` still depended on the next Spotify queue item already having `name`. New server-generated casts now have metadata, but old/saved casts or URI-only queue items still lacked an async prefetch before the Spotify segment started.
- Past Episodes refresh still depended mostly on the SSE `done` event. If that event was missed, delayed, or the user returned to Library through a later path, the library could skip a fresh load and lose the visible trace of the generated cast.

## Files Changed

- `resonova/web/player.js`
  - Adds `_metaPrefetch` in-flight guard.
  - Adds `_prefetchNextTrackMeta()` to fetch Spotify metadata during commentary without blocking playback.
  - Updates `#next-up` when metadata arrives and the user is still in a commentary segment.
  - Adds a bounded connected-state episode refresh.
  - Uses `_pendingEpisodeFocusId` or the active generated `_episodeId` as the focus id when returning to Library.
- `resonova/web/index.html`
  - Bumps the `player.js` cache-bust version.

## Expected Behavior

- During AI commentary, `Up next` appears immediately when metadata is already on the queued Spotify item.
- If only a Spotify URI is available, the player fetches track metadata in the background and updates `Up next` during the same commentary segment when possible.
- Returning to Library refreshes Past Episodes and focuses the current generated episode id when known, even if the SSE `done` path did not set a pending focus id.

## Validation

- `node --check resonova/web/player.js` passed.
- `uv run python -m py_compile resonova/server.py` passed.
- `uv run python -c "from resonova import server; print('server ok')"` passed.
- `uv run python tests/test_variety_episodes.py` passed.
- `git diff --check -- resonova/web/player.js resonova/web/index.html "docs/handoffs/Next Up and Episode Library Regression Handoff.md"` reported only the existing Git CRLF warning.

## Boss Phone Test

- Generate a new cast and wait for the first track commentary to start. Confirm `Up next` appears before entering the Spotify music segment.
- Return to Library after generation completes. Confirm the new cast appears in Past Episodes under the correct playlist group.
- Repeat once with the phone briefly backgrounded during generation or playback, then return to Library and confirm the cast is not visually lost.

## Remaining Risk

This improves the frontend behavior but does not prove full real-phone behavior. If the server has not finished saving the episode yet, `/api/episodes` cannot show it until save completes. A future product improvement could add an explicit "generation in progress" library row, but this fix stays scoped to the reported regression.
