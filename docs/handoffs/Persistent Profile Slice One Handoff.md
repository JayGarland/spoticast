---
title: "Persistent Profile Slice One Handoff"
created: 2026-06-21
status: ready-for-chef-review
author: RUG orchestrator
parent_design: docs/handoffs/Persistent Profile Spotify Trails Design Handoff.md
---

# Persistent Profile — Slice One Handoff

All changes are in the **working tree only**. Nothing was committed, staged, pushed,
or opened as a PR. Chef reviews and approves before any commit.

---

## 1. Files Created / Modified

### New files

| File | Purpose |
|------|---------|
| `resonova/profile.py` | Profile store: load / save / reset / `_enforce_caps` / `summarize_context` / `select_memories_for_prompt` / `profile_has_content` |
| `tests/test_profile.py` | 15 tests: store round-trip, cap eviction, eviction ordering, prompt impact (empty → unchanged, disabled → unchanged, populated → block injected) |

### Modified files

| File | Change |
|------|--------|
| `resonova/server.py` | Added `from resonova import profile as profile_store`; attached profile to context before `generate_script`; non-blocking profile write after `save_episode`; `GET /api/profile` and `DELETE /api/profile` routes |
| `resonova/api/gemini.py` | Added `from resonova import profile as profile_store`; `persistent_profile` read from context; `═══ PERSISTENT MEMORY ═══` block injected into `build_prompt` (gated: non-empty **and** enabled) |
| `resonova/web/index.html` | Added `#memory-widget` service-row pill + `#memory-panel` inspect panel (after the Last.fm widget, inside `state-connected`) |
| `resonova/web/player.js` | Added `_initMemory()`, `_updateMemoryPillLabel()`, `_renderMemoryPanel()` methods; `this._initMemory()` called from `init()` alongside `_initLastFM()` |
| `resonova/web/styles.css` | Added `#memory-pill`, `.memory-panel*`, `.memory-row*`, `.memory-memory-item*`, `.memory-badge*`, `.memory-actions` CSS (all new; nothing removed) |

### Not modified (confirmed)

- `resonova/config.py` — Spotify scopes **unchanged**.
- `resonova/api/spotify.py` — No new fetchers or scopes added.
- `.gitignore` — `generated/` was already ignored on line 2; `generated/profile/` is covered.
- No feedback channel (`feedback.jsonl`, `POST /api/feedback`, thumbs/tags) was built.
- No `PATCH /api/profile` endpoint was added.
- No tokens, email, secrets persisted anywhere.

---

## 2. Validation — Command Output

### `uv run python -c "from resonova import server; print('server ok')"`

```
server ok
```

### `uv run python tests/test_variety_episodes.py`

```
  fingerprint_stable ✓
  select_produces_variety ✓
  select_short_playlist ✓
  pasted_track_order_not_affected ✓
  save_variety_memory ✓
  episodes_lifecycle ✓
  episodes_backward_compat ✓
  run_number ✓
  episode_path_traversal_rejected ✓
  server_track_ready_metadata_shape ✓
  quota_error_classification ✓
  retry_after_formatting ✓
  failed_episode_save ✓
  cooldown_guard_in_server ✓
All tests passed ✓
```

### `uv run python tests/test_profile.py`

```
  empty_profile ✓
  round_trip ✓
  reset ✓
  missing_file_returns_empty ✓
  corrupted_file_returns_empty ✓
  cap_list_fields ✓
  cap_memories_eviction ✓
  memory_eviction_order ✓
  profile_has_content ✓
  select_memories_for_prompt ✓
  summarize_context_minimal ✓
  summarize_context_with_lastfm ✓
  empty_profile_prompt_unchanged ✓
  disabled_profile_prompt_unchanged ✓
  populated_profile_prompt_has_block ✓
All profile tests passed ✓
```

---

## 3. Acceptance Criteria Check

| Criterion | Status | Evidence |
|-----------|--------|---------|
| `resonova/profile.py` exists with load/save/reset + caps + eviction; round-trips correctly | ✅ PASS | `tests/test_profile.py` round_trip, cap, eviction tests all pass |
| Summariser builds `taste_profile` from existing context with zero new scopes/fetchers | ✅ PASS | `summarize_context` uses only `context["listener_profile"]` and `context["artist_profiles"]`; no new Spotify API calls |
| Generation updates `profile.json` after successful save, non-blocking on error | ✅ PASS | `server.py` wraps `summarize_context` + `save_profile` in `try/except`; logs warning, never raises |
| Prompt adds capped memory block only when non-empty AND enabled; empty/disabled leaves prompt unchanged | ✅ PASS | `_test_empty_profile_prompt_unchanged`, `_test_disabled_profile_prompt_unchanged`, `_test_populated_profile_prompt_has_block` all pass |
| `GET /api/profile` returns the profile | ✅ PASS | Route added to `server.py`; `server ok` import validates |
| `DELETE /api/profile` resets it | ✅ PASS | Route added; calls `profile_store.reset_profile()` |
| Memory panel renders profile (source + confidence) and offers Clear-memory with confirm | ✅ PASS | `_renderMemoryPanel` in `player.js` renders badges; Clear uses `confirm()` dialog |
| `generated/profile/` is git-ignored | ✅ PASS | `.gitignore` line 2 ignores all of `generated/`; confirmed with `Select-String` |

---

## 4. Hard No-Go Checks

- **No Spotify OAuth scopes added or changed** — `resonova/config.py` not touched.
- **No feedback channel built** — No `feedback.jsonl`, no `POST /api/feedback`, no thumbs/tags.
- **No edit/pin/disable-toggle UI** — Only inspect + reset (no `PATCH /api/profile`).
- **No commit, push, stage, or PR** — Working tree only.
- **No tokens, secrets, or email persisted** — `profile.json` contains only summarised strings.
- **No regression for users without a profile** — `_test_empty_profile_prompt_unchanged` verifies byte-identical prompt when no profile is present.

---

## 5. Remaining Risks

1. **Prompt block is new to Gemini.** The `═══ PERSISTENT MEMORY ═══` block has not been tested
   against a live Gemini call. It could shift the model's output in unexpected ways for edge
   cases (very sparse profile, very long taste list). Chef should do a live cast smoke-test.

2. **Guardrail is instructional, not enforced.** The GUARDRAIL line in the memory block instructs
   the hosts not to narrate the listener, but the model could still slip. This mirrors the same
   risk that exists for the existing LISTENER PROFILE block. No new risk beyond current behaviour.

3. **Cap on `top_artists` merging.** `summarize_context` merges new artists with existing, deduped.
   If the user changes Spotify accounts or clears top-artists, stale artists from prior runs
   persist until a manual reset. A future slice can add per-field provenance timestamps to
   enable staleness eviction.

4. **`generated/profile/` gitignore.** `generated/` is already ignored at the directory level.
   If the repo structure ever moves `generated/` inside a tracked subtree, profile files would
   need their own explicit ignore rule.

5. **Memory panel always visible once /api/profile returns.** Even if the profile is empty, the
   widget shows "Memory — empty". Some may prefer to hide it until memory actually exists.
   Low risk; easy to adjust in a future CSS/JS tweak.

6. **No browser tests for the frontend JS.** The memory panel JS was written to match the
   Last.fm widget pattern and has been code-reviewed, but there are no automated browser tests.
   Chef should manually verify the panel opens/closes and Clear memory resets correctly.

---

## 6. Test Instructions for Chef

```bash
# In the repo root:

# 1. Validate existing tests still pass
uv run python tests/test_variety_episodes.py

# 2. Validate new profile tests
uv run python tests/test_profile.py

# 3. Validate server imports cleanly
uv run python -c "from resonova import server; print('server ok')"

# 4. Smoke-test the profile store manually
uv run python -c "
from resonova import profile as p
import json, tempfile, pathlib, os

# Point at a temp dir so we don't pollute the real profile
p._PROFILE_DIR = pathlib.Path(tempfile.mkdtemp()) / 'profile'
p._PROFILE_PATH = p._PROFILE_DIR / 'profile.json'

# Test round-trip
prof = p._empty_profile()
prof['taste_profile']['top_artists'] = ['Radiohead']
p.save_profile(prof)
loaded = p.load_profile()
print('Artists:', loaded['taste_profile']['top_artists'])
print('Reset:', p.reset_profile()['taste_profile']['top_artists'])
print('All OK')
"

# 5. Live server test (needs Spotify env configured):
# uv run python -m resonova
# Then in another terminal:
# curl http://localhost:8000/api/profile
# curl -X DELETE http://localhost:8000/api/profile
```

To verify the frontend memory panel:
1. Start the server and authenticate with Spotify.
2. In `state-connected`, a "Memory — empty" pill should appear.
3. Click **inspect** — the panel should expand showing "No memory yet…".
4. Run a generation to completion. The profile should auto-populate.
5. Refresh (or click inspect again) — top artists and recurring styles should appear.
6. Click **Clear memory** and confirm — panel should show empty state again.
