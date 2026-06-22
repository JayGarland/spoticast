# Style Derivation Handoff — Spotify Genres → recurring_styles

**Date**: 2026-06-22
**Task**: Derive `taste_profile.recurring_styles` from Spotify artist genres (in addition to existing Last.fm tag derivation).

## Changed Files

| File | What changed |
|------|-------------|
| `resonova/api/spotify.py` | Added `top_genres: list[str]` to `UserContext` dataclass; `_top_artists` now returns `(names, genres)` tuple; `fetch_user_context` aggregates genres across short/medium/long term via `Counter.most_common()`; `build_playlist_context` plumbs `spotify_genres` into `context["listener_profile"]`. |
| `resonova/profile.py` | `summarize_context` reads `context["listener_profile"]["spotify_genres"]`, merges with Last.fm tag styles (Last.fm first, then Spotify, deduped, capped at `_MAX_LIST_ITEMS`). |
| `tests/test_profile.py` | Added 3 new test functions (5 assertions). |

## How Each Requirement Is Met

### 1. Capture genres in spotify.py
- **`_top_artists`** (line 252): Returns `tuple[list[str], list[str]]` — artist names and flattened genres from each artist object's `genres` field.
- **`fetch_user_context`** (line 271-280): Aggregates genres from all three time ranges using `collections.Counter.most_common()` → frequency-ranked, de-duplicated list.
- **`UserContext.top_genres`** (line 123): New dataclass field `list[str]`.

### 2. Plumb genres into context
- **`build_playlist_context`** (line 540): Adds `"spotify_genres": user_ctx.top_genres` to `context["listener_profile"]`. Existing keys (`top_artists_all_time`, `recently_played_count`) are untouched.

### 3. Derive recurring_styles in profile.py
- **`summarize_context`** (lines 228-236): Reads `listener.get("spotify_genres") or []`. Merges with Last.fm tag styles: `list(dict.fromkeys(lastfm_styles + spotify_genres))` preserves frequency order, deduplicates, then merges with existing profile styles. Capped at `_MAX_LIST_ITEMS` (20). Not gated by `memory_enabled` (durable field).

## Validation Results

```
uv run python -c "from resonova import server; print('server ok')"
→ server ok

uv run python tests/test_profile.py
→ All profile tests passed ✓ (35 tests, including 3 new)

uv run python tests/test_variety_episodes.py
→ All tests passed ✓
```

## Acceptance Criteria Confirmation

- [x] **Spotify genres only, no Last.fm** → `recurring_styles` populated from Spotify genres in frequency order, capped (`_test_summarize_context_with_spotify_genres_only`).
- [x] **Both sources** → `recurring_styles` contains both, deduped, Last.fm tags first (`_test_summarize_context_with_both_sources`).
- [x] **Empty/missing genres** → No crash, `recurring_styles` unchanged (`_test_summarize_context_empty_genres` — tests missing key, empty list, and None).
- [x] **No Spotify call in tests** — all new tests are pure unit tests with synthetic context dicts.
- [x] **No commit, no push, no PR** — changes left in working tree for chef review.
- [x] **No scope change** — `spotify_scopes` in config.py untouched.
- [x] **Last.fm path preserved** — when Last.fm is present, its tags appear first in `recurring_styles`, then Spotify genres deduped.
- [x] **Graceful on empty genres** — `.get("spotify_genres") or []` handles missing key, None, and empty list identically.
- [x] **No formatting churn** — only semantic changes applied.

## How recurring_styles Is Now Sourced

```
recurring_styles = f(Last.fm tags) + f(Spotify genres) + existing profile styles
                    │                     │
              frequency-ordered     frequency-ordered
              (tag_counts sorted     (from Counter.most_common()
               by descending         in fetch_user_context)
               count)
                    
Order: Last.fm tags FIRST, then Spotify genres, then existing profile entries not already in the new set.
Dedup: dict.fromkeys() preserves first occurrence.
Cap:   [:_MAX_LIST_ITEMS] = 20
```

## Risks

- **Spotify API `genres` field**: Some artists have empty `genres` lists. This is handled — genres that are present across any time range contribute to the counter; empty artists contribute nothing. No crash.
- **Genres across time ranges**: The same genre may appear for the same artist in multiple time ranges. Counter aggregation handles this correctly (counts occurrences across all ranges, not just unique artist-genre pairs). This is fine — a genre appearing many times across short/medium/long should rank higher.
- **`from collections import Counter`**: Added to module-level imports. Also was duplicated inside `fetch_user_context` — removed the duplicate in final edit.

## Next Steps for Chef

1. Review the changes (no commit yet — working tree is dirty with intended changes only).
2. If satisfied, commit and push. If not, provide feedback for iteration.
