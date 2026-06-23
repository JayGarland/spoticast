# Blind Playback Fix — Implementation Brief

Audience: Agents

## Context

Audit finding: Blocker — "Blind Spotify playback still open."
Verified in: Full Product Re-Audit Chef Gate 2026-06-23 (F1)
Also confirmed in: Internal Auditor Product Reviewer Trial Chef Gate (2026-06-21)

`_waitForSpotifyPlaybackStart` in `player.js` returns success when
`currentUri === uri && !state.paused` — but does NOT verify that the playback position
actually advances. The Spotify SDK can report "playing" with a non-paused state while
producing silence. On a miss, `_playSpotifyTrack` arms a full `duration_ms + 3000`
blind deadline and the user hears nothing for a whole track.

## Files

Allowed:
- `resonova/web/player.js` — `_waitForSpotifyPlaybackStart` and its call site in `_playSpotifyTrack`

No-go:
- Do not touch the SSE / generation flow or `_streamProgress`
- Do not touch the mobile recover button, `_markSpotifyUnhealthy`, or device-not-visible handling
- Do not touch `resonova/server.py`, `resonova/config.py`, or any Python files
- Do not rewrite other player methods not directly involved in playback start verification

## Task

Modify `_waitForSpotifyPlaybackStart` (around `player.js:1325`) so that:

1. **Two-sample position verification** — take at least two `getState()` readings separated
   by ~750 ms; confirm that `state.position` has advanced between the two readings.
   Declare playback "started" only once position advance is confirmed.

2. **Shorten the stuck-playback deadline** — if the two-sample check completes without
   confirmed advance (SDK reports playing but position is frozen), surface the
   recover/fallback path within ≤5 seconds instead of waiting the full `duration_ms + 3000`.

3. **Preserve existing instrumentation and fallbacks**:
   - Observability timeline labels (`play:start:blind`, `play:start:confirmed`, etc.)
     must still fire with accurate labels reflecting actual state.
   - Skip Music fallback must remain intact.
   - `_recommendSpotifyReload` and recover-button paths must remain intact.
   - `_setBlindSpotifyDeadline` may be adjusted but must not be removed if still reachable.

## Acceptance Criteria

- [ ] `_waitForSpotifyPlaybackStart` verifies position advance across ≥2 samples (~750ms apart)
- [ ] On position-stuck: recovery is surfaced within ≤5 s, not after full `duration_ms`
- [ ] `node --check resonova/web/player.js` exits 0
- [ ] No other files modified
- [ ] Observability logging labels reflect actual detection outcome

## Output

Produce a handoff at: `docs/handoffs/Blind Playback Fix Handoff.md`

Include: changed functions with before/after logic, verification performed, risks and
caveats noted (especially any timing assumptions).

Do not commit.
