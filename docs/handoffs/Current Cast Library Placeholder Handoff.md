# Current Cast Library Placeholder Handoff

Date: 2026-06-21

## Problem

Boss reported that a cast generated from a new playlist still did not appear in `section-episodes` / Past Episodes. The user could see only the unfinished/resume trail, which makes the cast feel lost.

## Root Cause

Past Episodes only represented saved episodes returned by `/api/episodes`. A brand-new playlist has no existing group, and the server only saves the episode after the full generation pipeline finishes. While the cast is actively generating or saving, there was no visible cast instance inside the episode section.

## Change

- `resonova/web/player.js`
  - Tracks the active generation id/name/source after `/generate`.
  - Renders a `Current Cast` accordion group inside `section-episodes` when the active cast has not appeared in `/api/episodes` yet.
  - Updates the current-cast row while track/outro segments stream in if the user is in Library.
  - Removes the placeholder automatically once the saved episode appears in the API response.
  - Prevents clicks on the placeholder from trying to play an undefined episode id.
- `resonova/web/index.html`
  - Bumps the `player.js` cache-bust version.

## Expected Behavior

- A new playlist cast appears in Past Episodes immediately as `Current Cast` while generating.
- Once the full episode is saved, the real saved episode group/card replaces the placeholder.
- The user no longer has to rely only on the unfinished/resume card to know the cast exists.

## Validation

- `node --check resonova/web/player.js` passed.
- `uv run python -m py_compile resonova/server.py` passed.
- `uv run python -c "from resonova import server; print('server ok')"` passed.
- `uv run python tests/test_variety_episodes.py` passed.

## Boss Test

- Generate from a playlist that has never appeared in Past Episodes.
- Click Back/Library while it is still generating.
- Confirm `section-episodes` shows a `Current Cast` group.
- Wait until generation completes and confirm the saved episode replaces the placeholder.

## Remaining Risk

If the server generation fails, the placeholder will remain tied to the active client session until error handling returns the user to Library. A future polish pass can add an explicit failed-current-cast state if needed.
