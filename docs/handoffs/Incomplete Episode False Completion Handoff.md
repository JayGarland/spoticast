# Incomplete Episode False Completion Handoff

Date: 2026-06-21

## Problem

Boss reported the player showing `Episode Complete` and `Thanks for listening` while progress still showed `33 / 41 segments`. The unfinished resume card also appeared outside the intended episode/library section, making the saved/resumable cast feel disconnected from Past Episodes.

## Root Cause

`_playNext()` treated `queue.length === 0 && _generationComplete === true` as a real terminal state. That is false when the live SSE stream or backgrounded browser misses queued tail items while `totalItems` still says more segments should exist.

When this false terminal path ran, `_onPlaybackComplete()` cleared resume state and displayed completion even though `completedItems < totalItems`.

## Change

- `resonova/web/player.js`
  - Allows resume state to persist when progress is incomplete, even if the live queue is temporarily empty.
  - Adds `_loadSavedEpisode()` to fetch the saved episode queue or fall back to local episode cache.
  - Adds `_recoverMissingEpisodeTail()` to rebuild the remaining queue from the saved episode before declaring completion.
  - Adds `_parkIncompleteEpisode()` to show an interrupted/resumable state instead of clearing resume if recovery cannot rebuild the tail.
  - Adds a guard inside `_onPlaybackComplete()` so incomplete progress can never be marked complete.
  - Moves the unfinished resume card into `section-episodes`, before the Past Episodes list.
- `resonova/web/index.html`
  - Bumps the player cache-bust version.

## Expected Behavior

- If the live queue becomes empty at `33 / 41`, the player tries to load `/api/episodes/{episodeId}` and resume at segment 34 instead of showing Episode Complete.
- If the saved episode is not available yet, the UI shows an interrupted/resumable state and keeps the resume data.
- The unfinished episode card appears in the episode/library section, not as a disconnected page-level alert.

## Validation

- `node --check resonova/web/player.js` passed.
- `uv run python -m py_compile resonova/server.py` passed.
- `uv run python -c "from resonova import server; print('server ok')"` passed.
- `uv run python tests/test_variety_episodes.py` passed.

## Boss Phone Test

- Reproduce a case where playback previously showed `Episode Complete` before reaching the final segment. It should now either continue with recovered saved segments or show an interrupted/resumable state.
- Return to Library and confirm the unfinished card appears inside the Past Episodes / episode section.
- Resume from the card and confirm it does not restart from the beginning.

## Remaining Risk

This depends on the server having saved the full episode before recovery. If the browser loses queue events before the server save finishes, the player will park the episode as resumable and the user may need to try Resume again after the save completes.
