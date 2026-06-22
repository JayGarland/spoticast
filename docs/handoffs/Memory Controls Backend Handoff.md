# Memory Controls Backend Handoff

## Summary
Implemented the boss-settled memory-control model (companion-direction brief §3.2) and fixed two audited honesty bugs. Backend only — no frontend changes.

## Files Changed

| File | Change |
|------|--------|
| `resonova/profile.py` | `reset_profile()` now deletes `_FEEDBACK_PATH`. `summarize_context()`, `summarize_library()`, `summarize_saved_casts()` accept `memory_enabled` flag; when False, TRAIL fields (recent_shifts, playlist_patterns) are not written. |
| `resonova/api/gemini.py` | `build_prompt()`: incognito mode omits both LISTENER PROFILE and PERSISTENT MEMORY blocks entirely. Memory-off (memory_enabled=False) omits TRAIL fields from PERSISTENT MEMORY block; DURABLE fields remain. |
| `resonova/server.py` | `GenerateRequest` gains `incognito: bool = False`. `Job` gains `incognito`. Profile-update block: gated on `not job.incognito`; summarizers called with `memory_enabled` flag instead of full gate. The `persistent_profile` is not attached for incognito jobs. |
| `tests/test_profile.py` | 5 new tests added (see below). Existing `_test_disabled_profile_prompt_unchanged` updated for new partial-memory-off behavior. |

## Acceptance Criteria Verification

- [x] **reset_profile deletes feedback.jsonl**: `_test_reset_deletes_feedback` — writes a feedback event, resets, asserts the file is gone.
- [x] **memory-off prompt contains DURABLE marker but not TRAIL marker**: `_test_memory_off_prompt_omits_trail` — `top_artists` ("DurableArtist") present; `recent_shifts` ("TrailArtist") and `playlist_patterns` absent.
- [x] **memory-on prompt contains both DURABLE and TRAIL**: `_test_memory_on_prompt_contains_both` — both present. All existing prompt tests also pass.
- [x] **incognito prompt contains neither LISTENER PROFILE nor PERSISTENT MEMORY**: `_test_incognito_prompt_omits_all` — both blocks absent.
- [x] **summarizers skip TRAIL when memory_enabled=False but update DURABLE**: `_test_summarizers_skip_trail_when_memory_disabled` — `recent_shifts` empty, `saved_library_artists` + `followed_artists` populated.

## Validation Output

```
uv run python -c "from resonova import server; print('server ok')"
→ server ok

uv run python tests/test_profile.py
→ All 30 tests passed ✓ (25 original + 5 new)

uv run python tests/test_variety_episodes.py
→ All 15 tests passed ✓
```

## Design Details

### Memory-off (partial)
- **Prompt**: PERSISTENT MEMORY block is emitted but skips `recent_shifts` and `playlist_patterns` lines. LISTENER PROFILE section unchanged (its content is already DURABLE — top_artists_all_time). DURABLE fields (top_artists, recurring_styles, favorite_eras, saved_library_artists, followed_artists, commentary_preferences, memories) all appear.
- **Writes**: `summarize_library` skips writing `recent_shifts`. `summarize_saved_casts` skips writing `playlist_patterns`. `summarize_context` only writes DURABLE fields anyway. DURABLE writes (top_artists, saved_library_artists, followed_artists, etc.) continue.

### Incognito (per cast)
- **Prompt**: Both LISTENER PROFILE and PERSISTENT MEMORY blocks are omitted entirely. The listener_lines section shows "(Incognito mode — no listener profile data)".
- **Writes**: The entire profile-update block is skipped (`if not job.incognito`). No feedback written during generation.
- **Owner guard**: Still enforced. Incognito doesn't bypass ownership.

### Reset clears feedback
- `reset_profile()` now calls `_FEEDBACK_PATH.unlink()` if the file exists.

## Remaining Risks

1. **Frontend**: No UI toggle for incognito yet. The backend `incognito` field is accepted but the web UI doesn't expose it. Frontend work required to add an incognito checkbox/button.
2. **Frontend**: Memory-off toggle exists in the API (PATCH /api/profile with memory_enabled) and the UI should reflect correct partial behavior. No UI changes in this slice.
3. **Feedback survives per-cast incognito**: The feedback endpoint (`POST /api/feedback`) is a separate user action. An incognito cast does not write feedback during generation, but a user could still manually submit feedback about an incognito cast afterward. This is intentional — feedback is about the cast quality, not the memory.

## Manual Test Steps

1. Start server: `uv run python -m resonova.server`
2. GET `/api/profile` → confirm `memory_enabled: true`
3. PATCH `/api/profile` with `{"memory_enabled": false}` → confirm memory_enabled false
4. Generate a cast (POST `/generate` with a playlist_uri) → cast should still personalize on durable taste but not on recent/behavioral trail
5. PATCH `/api/profile` with `{"memory_enabled": true}` → restore full memory
6. Generate an incognito cast (POST `/generate` with `{"playlist_uri": "...", "incognito": true}`) → cast should have zero personalization, no profile/feedback writes
7. DELETE `/api/profile` → confirm feedback.jsonl is deleted along with profile.json
8. Verify profile owner guard still works: reset doesn't unlock the instance.

## Non-Regression Confirmation

- **No commit/push/PR made** — all changes in working tree for chef review.
- **No Spotify scopes or config.py changed.**
- **Single-user owner guard not weakened or removed** — `claim_or_check_owner` calls intact.
- **Normal (memory-on, non-incognito) generation unchanged** — existing tests all pass byte-for-byte equivalent output structure. The PERSISTENT MEMORY block content is identical for memory_enabled=True profiles.
- **No unrelated refactoring or formatting churn.**
- **No secrets persisted.**
