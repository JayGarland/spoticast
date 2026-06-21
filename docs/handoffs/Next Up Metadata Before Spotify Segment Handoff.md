# Next Up Metadata Before Spotify Segment Handoff

Date: 2026-06-21

## Problem

During newly generated casts, `Up next: <song>` could appear late. The frontend looked ahead for the next Spotify queue item, but live `track_ready` events only provided `track_uri`. The song title was usually learned later, when the Spotify segment itself started and the client fetched Spotify metadata.

## Change

- `resonova/server.py`
  - Builds a `tracks_by_uri` lookup from the selected Spotify tracks.
  - Persists Spotify queue items with `name`, `artist`, and `duration_ms`.
  - Sends `track_name`, `artist`, and `duration_ms` in each `track_ready` SSE payload.
- `resonova/web/player.js`
  - Copies streamed track metadata onto live Spotify queue items.
  - Falls back to local track metadata cache when rendering `Up next`.
  - Escapes the title before rendering it into the `next-up` element.
- `resonova/web/index.html`
  - Bumps the `player.js` cache-bust version.
- `tests/test_variety_episodes.py`
  - Adds a smoke guard that confirms generation includes Spotify display metadata in saved queue items and `track_ready` payloads.

## Validation

- `node --check resonova/web/player.js` passed.
- `uv run python -m py_compile resonova/server.py` passed.
- `uv run python -c "from resonova import server; print('server ok')"` passed.
- `uv run python tests/test_variety_episodes.py` passed.
- `git diff --check -- resonova/server.py resonova/web/player.js resonova/web/index.html tests/test_variety_episodes.py` reported only the existing Git CRLF warning.

## Remaining Risk

Existing saved casts generated before this change may still lack persisted Spotify metadata. The frontend cache fallback helps after a track has been fetched once, but full advance display for old casts would require a one-time metadata backfill.
