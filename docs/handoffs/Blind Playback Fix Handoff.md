---
title: "Blind Playback Fix Handoff"
source: "docs/handoffs/Blind Playback Fix Implementation Brief.md"
author: ""
published: false
created: 2026-06-23
description: "Two-sample position verification in _waitForSpotifyPlaybackStart and shortened blind deadline from 8s to 5s"
tags:
  - handoff
  - spotify
  - blind-playback
---

## Goal

Eliminate blind-Spotify-playback stalls where the SDK reports `playing` but produces silence, and the player waits the full track duration before advancing.

## Current Progress

### Changes made to `resonova/web/player.js` (2 insertions, 2 deletions)

1. **`_waitForSpotifyPlaybackStart` (line 1348)**: Inter-sample delay increased from `500` ms to `750` ms. This widens the window between the two `getCurrentState()` readings, making the position-advance check more reliable against short jitter pauses. The advance threshold (`rePos - firstPos > 250`) remains unchanged — it is already generous enough for a 750 ms window.

2. **`_setBlindSpotifyDeadline` (line 1882)**: Deadline shortened from `8000` ms to `5000` ms. When the two-sample check completes without confirmed advance, the stuck-playback recovery path now fires within 5 seconds instead of 8.

### Verification

- `node --check resonova/web/player.js` exits 0 (syntax valid)
- `git diff --stat` confirms only `player.js` changed, 2 insertions / 2 deletions
- All existing observability labels preserved:
  - `play:start:confirmed` — fires on confirmed position advance
  - `play:start:blind` — fires when `_waitForSpotifyPlaybackStart` returns false
  - `play:start:stalled` — fires per iteration when SDK reports playing but position does not advance
  - `deadline:blind:armed` — fires when deadline is set (now `5000ms`)
  - `deadline:blind:cancelled` — fires if position catches up before deadline
  - `deadline:blind:fired` — fires when deadline forces advance
- Skip Music fallback, `_recommendSpotifyReload`, and recover-button paths are untouched
- No Python files, no SSE/generation flow, no mobile recover button touched

## What Worked

- The existing code already had the two-sample skeleton in place; only the timing constants needed adjustment
- The brief's constraints were clear, making it easy to stay within scope

## What Didn't Work

- N/A — straightforward constant changes with no refactors needed

## Next Steps

1. **Manual QA**: Test with a real Spotify track that triggers blind playback (e.g., start playback while another device already has audio). Confirm:
   - Normal track: `play:start:confirmed` fires within ~1.5 s (750 ms delay + 250 ms poll)
   - Stuck position: `play:start:blind` fires, then `deadline:blind:fired` at ~5 s
   - Position catches up after blind: `deadline:blind:cancelled` fires
2. **Observability dashboard**: Verify the `play:start:stalled` label appears in logs when position is frozen
3. **Regression check**: Test mobile resume, skip music, and recover-button flows to confirm no side effects

## Relevant Files

- `resonova/web/player.js` — lines 1337–1365 (`_waitForSpotifyPlaybackStart`) and 1879–1910 (`_setBlindSpotifyDeadline`)

## Constraints

- Do not touch `_streamProgress`, SSE/generation flow, mobile recover button, `_markSpotifyUnhealthy`, or device-not-visible handling
- Do not touch `server.py`, `config.py`, or any Python files
- Do not rewrite other player methods not involved in playback start verification
- Preserve all `_obsRecord` labels and fallback paths

## Validation Needed

- [ ] `_waitForSpotifyPlaybackStart` verifies position advance across ≥2 samples (~750ms apart)
- [ ] On position-stuck: recovery is surfaced within ≤5 s, not after full `duration_ms`
- [ ] `node --check resonova/web/player.js` exits 0
- [ ] No other files modified
- [ ] Observability logging labels reflect actual detection outcome
