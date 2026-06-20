# Saved Cast Library and Replay Variety Handoff

**Date:** 2026-06-20  
**Manager:** RUG  
**Status:** Implemented, chef-reviewed, tested, not committed

---

## Summary

Two reinforcing problems were addressed in this implementation:

1. **Past Episodes distinguishability** — multiple casts from the same playlist looked identical in the UI (same name prefix, no run number, no order info).
2. **Replay variety** — repeated playlist generations could reproduce recent track orders, and because the Gemini script cache is order-keyed, identical order → identical commentary.

### What was built

- **`resonova/variety.py`** (new) — memory-aware playlist track selection; persists recent orders under `generated/variety/`
- **`resonova/episodes.py`** — extended metadata (`order_fingerprint`, `track_order_preview`); `rename_episode()` and `delete_episode()`; `list_episodes()` now returns `run_number` per same-playlist discriminator
- **`resonova/server.py`** — new `PATCH /api/episodes/{id}` and `DELETE /api/episodes/{id}` routes; generation pipeline integrated with variety and passes extended metadata to save_episode
- **`resonova/web/player.js`** — improved episode cards (run badge, fingerprint, track preview, Play/Rename/Delete buttons); `_renameEpisode()` and `_deleteEpisode()` methods
- **`resonova/web/styles.css`** — styles for episode card layout, action buttons, run badge, fingerprint, preview line
- **`tests/test_variety_episodes.py`** (new) — 8 focused unit-style smoke tests; no network required

---

## Files Changed

| File | Change |
|---|---|
| `resonova/variety.py` | **New** — memory-aware track selection, fingerprinting, variety persistence |
| `resonova/episodes.py` | Extended `save_episode`, enriched `list_episodes`, added `rename_episode`, `delete_episode` |
| `resonova/server.py` | New PATCH/DELETE routes, variety integration in generation pipeline |
| `resonova/web/player.js` | Improved `_episodeCardHTML`, added `_renameEpisode`, `_deleteEpisode`, fixed click delegation |
| `resonova/web/styles.css` | Episode card layout and action button styles |
| `tests/test_variety_episodes.py` | **New** — 8 smoke tests |

---

## Implementation Details

### Variety module (`resonova/variety.py`)

**Persistence:** `generated/variety/<sha1-of-playlist-uri>.json`

Schema:
```json
{
  "playlist_uri": "spotify:playlist:...",
  "recent_orders": [
    {
      "created_at": "2026-06-20T12:00:00Z",
      "track_uris": ["spotify:track:...", "..."],
      "fingerprint": "a1b2c3d4"
    }
  ]
}
```

Keeps last 5 orders per playlist (`_MAX_RECENT = 5`).

**Selection algorithm:**
1. Generate up to 20 candidate shuffles (`_NUM_CANDIDATES = 20`)
2. Score each candidate (lower = better):
   - +1000 exact fingerprint match with recent order
   - +20 same opener as any recent order
   - +10 same closer as any recent order
   - +1 per recently-used track (only when playlist > max_tracks)
   - +5 per adjacent same-artist pair, +2 per adjacent same-album pair
3. After shuffle, run a light adjacency-repair pass (swap same-artist neighbours within a window of 5)
4. Pick lowest-score candidate; stop early if score < 20
5. Persist via `save_variety_memory()` called **after** `save_episode()` succeeds

**Fingerprint:** SHA1 of `"|".join(track_uris)`, first 8 hex chars.

### Episode metadata extensions

`save_episode()` accepts two new optional keyword args:
- `order_fingerprint: str | None` — 8-char fingerprint of the selected order
- `track_order_preview: list[str] | None` — first 3 "Artist – Track" strings

`list_episodes()` returns (in addition to existing fields):
- `order_fingerprint` — from metadata, `None` for old episodes
- `track_order_preview` — from metadata, `None` for old episodes
- `run_number` — 1-based sequential count among episodes with the same `playlist_uri`, ordered by `created_at`; fully derived at read-time (no stored field)

Old episodes without the new fields continue to load and display normally (backward compatible via `.get()` with `None` defaults).

### Management routes

```
PATCH /api/episodes/{episode_id}
  Body: { "name": "New Name" }
  Returns: updated summary dict (400 on empty name, 404 if not found)

DELETE /api/episodes/{episode_id}
  Returns: { "deleted": true, "id": "..." }
  (404 if not found; path-traversal guard via Path.resolve().relative_to())
```

### Frontend episode card

Each episode card now shows:
- Episode name (large)
- Playlist name · track count · date+time · **Run #N** badge · fingerprint
- First 3 "Artist – Track" as a preview line (playlist episodes only)
- Action row: **▶ Play** | **✏** (rename) | **🗑** (delete)

Clicking the main card body (outside actions) still plays the episode (backward-compatible).  
Rename uses `window.prompt` (lightweight, mobile-friendly).  
Delete uses `window.confirm` before proceeding.  
Both actions call `_loadEpisodes()` to refresh the list inline.

**Pasted track-list episodes** — `order_fingerprint` and `track_order_preview` are `null`, run badge and preview line are omitted.

---

## Validation Commands and Results

### Python import smoke check
```
uv run python -c "from resonova import server; print('server ok')"
→ server ok  ✓
```

### JS syntax check
```
node --check resonova/web/player.js
→ player.js ok  ✓
```

### Unit tests
```
uv run python tests/test_variety_episodes.py

  fingerprint_stable ✓
  select_produces_variety ✓
  select_short_playlist ✓
  pasted_track_order_not_affected ✓
  save_variety_memory ✓
  episodes_lifecycle ✓
  episodes_backward_compat ✓
  run_number ✓
  episode_path_traversal_rejected ✓
All tests passed ✓
```

### Diff hygiene
```
git diff --check
→ no whitespace errors; only CRLF normalization warnings on touched files
```

### git diff --stat
```
 resonova/episodes.py    |  97 ++++++-
 resonova/server.py      |  57 +++-
 resonova/web/player.js  | 192 +++++++++----
 resonova/web/styles.css | 743 +++++++++++++++++++++++++++++++++++++++---------
 4 files changed, 869 insertions(+), 220 deletions(-)
```
(+ 2 new untracked: `resonova/variety.py`, `tests/test_variety_episodes.py`)

---

## Chef Gate Review Notes

Codex reviewed the manager output before handoff acceptance and made two bounded corrections:

1. **Episode path-safety hardening** — `get_episode`, `save_episode`, `rename_episode`, and `delete_episode` now resolve episode paths through a shared `_episode_dir()` guard so new mutation APIs cannot escape `generated/episodes/`.
2. **Custom-track UI distinction** — Past Episode cards only show `Run #N` for true Spotify playlist episodes (`spotify:playlist:*`). Pasted track-list casts do not show playlist run badges.

The regression test suite was extended with `episode_path_traversal_rejected`.

---

## Known Risks / Parked Work

| Risk / Item | Notes |
|---|---|
| styles.css line count looks large | The `--stat` inflated by pre-existing uncommitted formatting changes already in the file before this task. Our episode-card additions are ~80 lines. |
| `window.prompt` / `window.confirm` | Functional on desktop and mobile. Can be replaced with a modal component if a modal system is added later. |
| Variety memory race condition | If two generation jobs run in parallel for the same playlist, both will read the same (empty) memory before either saves. This is a very edge case for a personal app; no lock is needed for MVP. |
| `run_number` is O(n episodes) | Computed from all episodes at list-time. Fine for personal use (tens/hundreds of episodes). |
| Gemini cache implication | As documented in the audit brief: novel order → cache miss → fresh commentary. No cache key changes needed. |
| Old episode batch re-normalization | Out of scope; old episodes keep their original audio. |
| Variety memory not gitignored | `generated/` should already be in `.gitignore`; confirm this is the case if the directory is ever committed. |
| `variety_store.save_variety_memory` is called synchronously in async context | It's a tiny JSON write; using `run_in_executor` is not needed at MVP scale but could be added if I/O latency becomes a concern. |

---

## Manual Boss Test Checklist

- [ ] Start the server (`uv run resonova`) and navigate to the app
- [ ] Generate the same playlist 3 times; confirm episode list shows Run #1, Run #2, Run #3
- [ ] Confirm each episode card shows the track preview (first 3 artist – title)
- [ ] Confirm each episode shows a different order fingerprint (8-char hex)
- [ ] Click the **✏** rename button on an episode; rename it; confirm the list updates inline
- [ ] Click the **🗑** delete button; confirm the confirmation dialog appears; confirm after delete the episode disappears from the list
- [ ] Load a renamed/un-deleted old episode and confirm it plays correctly (backward compat)
- [ ] Paste a track list instead of a playlist URI; generate; confirm the episode card has no run badge / no order preview (custom episode)
- [ ] On mobile (via Tailscale): confirm episode cards render cleanly (action row wraps to a row on small screens per the `@media (max-width: 480px)` rule)
- [ ] Confirm Generate, Skip, Previous, Recover Spotify, and Diag buttons still work normally

---

## Commit Not Made

As instructed, no `git commit` was created. All changes are in the working tree.
