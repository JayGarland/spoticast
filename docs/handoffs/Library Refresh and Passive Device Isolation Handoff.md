# Library Refresh and Passive Device Isolation Handoff

Date: 2026-06-21

## Problem

Boss reported two bugs:

1. A cast generated from a new playlist still did not reliably appear in `section-episodes` / Past Episodes.
2. Refreshing Resonova on the phone interrupted the active local PC playback session at `127.0.0.1`, which is unacceptable.

## Root Cause

- Episode list refresh still allowed browser/API cache reuse and only refreshed on a throttled connected-state path unless specific flags were set.
- Every authenticated page load initialized the Spotify Web Playback SDK. When the SDK reported `ready`, Resonova immediately called `_transferPlayback(device_id, token)`, which could transfer the Spotify account's active playback target to the refreshed phone tab even though the user did not start playback there.

## Change

- `resonova/web/player.js`
  - Stops transferring Spotify playback in the SDK `ready` event. A passive phone tab may prepare a device, but it no longer steals active playback from PC.
  - Keeps playback transfer/recovery for explicit active playback paths.
  - Loads `/api/episodes` with a timestamp query and `cache: "no-store"` so Past Episodes is fetched fresh.
  - Allows `_showState("connected", { forceRefreshEpisodes: true })`.
  - Back-to-Library buttons now force a Past Episodes refresh.
  - Connected-state focus uses the known generated/current episode id when available.
- `resonova/web/index.html`
  - Bumps the player cache-bust version.

## Validation

- `node --check resonova/web/player.js` passed.
- `uv run python -m py_compile resonova/server.py` passed.
- `uv run python -c "from resonova import server; print('server ok')"` passed.
- `uv run python tests/test_variety_episodes.py` passed.

## Boss Test

- Generate from a brand-new playlist. Return to Library. The new playlist group/cast should appear under Past Episodes without relying on the resume prompt.
- Start playback on PC at `127.0.0.1`, then refresh/open Resonova on phone without pressing play/recover there. PC playback should not be interrupted.

## Remaining Risk

The phone can still take over playback if the user explicitly starts playback, presses Recover, or resumes a cast on the phone. That is expected. The fixed issue is passive refresh stealing PC playback.
