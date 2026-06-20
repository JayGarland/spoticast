# Memory Aware Replay Variety Implementation Brief

## Intended Manager

Use **RUG manager** for implementation after audio normalization, unless owner explicitly prioritizes replay variety first.

This is a bounded generation-order fix. Do not implement persistent taste profile, feedback UI, explicit replay modes, or energy-arc ordering in this task.

## Parent Audit

- `docs/handoffs/External Audio Balance and Replay Variety Audit Report.md`
- `docs/strategy/playlist-order-variety-brief.md`

## Problem

Owner reports repeated casts from the same playlist still feel rigid.

Current code:

- `resonova/server.py:_select_playlist_tracks_for_episode(tracks)`
  - Uniform random shuffle.
  - Retries only to avoid exactly matching the original playlist order.
  - Has no memory of prior generated orders.
- `resonova/api/gemini.py`
  - Script cache key is `cache_key("script_v4_ordered", username, *track_uris)`.
  - Same order returns identical cached commentary.

Conclusion: current shuffle can repeat recent orders, and repeated order means identical commentary. We need memory-aware ordering.

## Goal

Persist recent generated orders per playlist and choose a novel order for future playlist-generated casts.

The MVP goal is not perfect DJ sequencing. It is simply:

- Avoid repeating recent playlist orders.
- Improve perceived freshness.
- Preserve direct pasted track order.
- Keep script cache useful.

## Files In Scope

- `resonova/server.py`
- Optional new helper module, e.g. `resonova/variety.py`
- Optional handoff doc after implementation

Avoid changing:

- `resonova/api/gemini.py` cache key for the MVP
- direct pasted track-list behavior
- persistent profile/feedback files

## Data Storage

Persist under `generated/variety/`.

Suggested file:

```text
generated/variety/<playlist-id-or-safe-hash>.json
```

Suggested schema:

```json
{
  "playlist_uri": "spotify:playlist:...",
  "recent_orders": [
    {
      "created_at": "2026-06-20T00:00:00Z",
      "track_uris": ["spotify:track:...", "..."]
    }
  ],
  "recent_tracks": {
    "spotify:track:...": "2026-06-20T00:00:00Z"
  }
}
```

Keep only the last 3-5 orders.

## Required Behavior

1. Playlist URL/URI input uses memory-aware ordering.
2. Direct pasted track-list input preserves user order exactly.
3. Same playlist generated three times in a row should produce distinct orders when enough tracks exist.
4. If the playlist is too short to produce a novel order, choose the most different candidate and do not fail generation.
5. Avoid obvious same-artist or same-album adjacency when track metadata makes that easy.
6. Do not depend on Spotify audio features; they are unreliable in Dev Mode.

## Suggested Algorithm

Input:

- `tracks`
- `playlist_uri`
- `max_tracks`

Candidate loop:

1. Generate up to N candidates, e.g. 20.
2. For each candidate:
   - shuffle full track list,
   - choose first `max_tracks`,
   - lightly repair same-artist adjacency by swapping with a later track when possible.
3. Score each candidate:
   - exact recent order match: reject if alternatives exist,
   - overlap with recent first 5 tracks: penalize,
   - same opener as recent order: penalize,
   - same closer as recent order: penalize,
   - adjacent same artist/album: penalize,
   - recently used tracks for large playlists: penalize.
4. Pick lowest penalty.
5. Persist selected order after generation starts or after successful generation. Prefer after successful track selection but before script generation so failures are debuggable.

Keep random behavior, but make it memory-aware.

## Acceptance Tests

Static:

```bash
uv run python -c "from resonova import server; print('server ok')"
```

Unit-style smoke with fake tracks:

- Construct fake tracks with `.uri`, `.artist`, `.album` or matching available fields.
- Call selection repeatedly for the same playlist.
- Verify orders differ when possible.
- Verify pasted track-list branch does not use the variety selector.

Manual:

1. Generate the same playlist three times.
2. Confirm episode orders differ.
3. Confirm generated scripts differ because order differs.
4. Confirm old saved episodes still replay unchanged.

## Cache Implication

Do not nonce the script cache key.

Because the cache key is order-sensitive, novel order naturally creates a cache miss and fresh commentary. This preserves cost control.

If a future feature wants a different script for the exact same order, use a bounded variation token in prompt and cache key. That is out of scope here.

## Do Not Do

- Do not add profile/feedback weighting.
- Do not add explicit modes (`Deep cut`, `Flow`, etc.).
- Do not build energy-arc ordering.
- Do not alter direct pasted order.
- Do not kill the Gemini cache with per-run nonce.
- Do not expose tokens or secrets.

## Expected Handoff

Return:

- Changed files.
- Persistence schema.
- Selection/scoring logic summary.
- Validation commands and outputs.
- Edge cases for short playlists.
