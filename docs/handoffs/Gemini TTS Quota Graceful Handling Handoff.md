# Gemini TTS Quota Graceful Handling — Handoff

**Date:** 2026-06-21
**Task:** Implement graceful Gemini TTS quota exhaustion handling
**Brief:** `docs/handoffs/Gemini TTS Quota Graceful Handling Implementation Brief.md`
**Status:** ✅ Implemented and validated

---

## Changed Files

| File | Change |
|------|--------|
| `resonova/api/tts.py` | Added `GeminiTTSQuotaError`, `_parse_quota_error`, `format_duration`; wrapped `synthesize_dialogue` |
| `resonova/episodes.py` | Added `status` field to `save_episode`, `list_episodes`, `rename_episode` |
| `resonova/server.py` | Added `import time`, `GeminiTTSQuotaError` import, cooldown state/functions, `/api/tts-cooldown` endpoint, cooldown check in `/generate`, dedicated `GeminiTTSQuotaError` catch in `_run_generation` |
| `resonova/web/styles.css` | Added `.quota-error-banner`, `.quota-error-*`, `.ep-quota-badge` CSS |
| `resonova/web/player.js` | Updated SSE error handler, added `_showQuotaError`, `_formatDuration`, cooldown guard in `generate()`, `ep-quota-badge` in `_episodeCardHTML`, body parsing in `_apiFetch` |
| `tests/test_variety_episodes.py` | Added 4 new tests: `_test_quota_error_classification`, `_test_retry_after_formatting`, `_test_failed_episode_save`, `_test_cooldown_guard_in_server` |

---

## Behaviour Before / After

### Before

- Gemini TTS 429 raised a bare exception, caught by generic `except Exception`
- User saw a generic "Generation failed" toast for 6 seconds
- No partial audio was saved — the cast disappeared from the library entirely
- `job.status = "error"` but no retry guard; user could immediately retry, burning more quota
- No user-visible retry-after information

### After

**On Gemini TTS 429 / RESOURCE_EXHAUSTED:**

1. `_parse_quota_error` classifies the error and extracts:
   - `code: "tts_quota_exhausted"`
   - `model: <API-reported or configured model name>`
   - `retry_after_seconds: <parsed from "retryDelay": "31678s" or "8h47m" text>`
   - Human-readable `message` including retry wait time

2. `GeminiTTSQuotaError` is raised from `synthesize_dialogue`.

3. `_run_generation` catches it before the generic `except Exception`:
   - Sets `job.status = "error"`
   - Calls `_set_tts_cooldown(exc.retry_after_seconds)` — stores expiry timestamp in-process
   - If `saved_queue` is non-empty (intro or tracks were already synthesised), saves the partial episode with `status="quota_failed"` via `save_episode(..., status="quota_failed")`
   - Pushes structured SSE error event: `{code, model, retry_after_seconds, message}`
   - Logs at ERROR level with model and retry delay

4. `/generate` POST checks `_get_tts_cooldown()` before spawning a job. While cooldown is active it returns HTTP 429 with the structured detail dict — no TTS calls are made.

5. `/api/tts-cooldown` GET returns `{active, code, retry_after_seconds, message}`.

**UI changes:**

- SSE `error` handler in `player.js` detects `code === "tts_quota_exhausted"` and calls `_showQuotaError(errData)` instead of `_showError`.
- `_showQuotaError` renders a **persistent** amber banner inside state-connected (not a 6-second toast):
  ```
  ⏸  Generation paused — Gemini TTS quota exhausted
     Model: gemini-3.1-flash-tts-preview
     Retry after about 8h 47m
     Generated segments so far are saved.              [✕]
  ```
- Cooldown info is written to `localStorage["resonova:tts-cooldown"]` with `{until, model, message}`.
- `generate()` checks localStorage on every submit attempt. If cooldown is still active it shows the quota banner immediately without a server round-trip.
- Server 429 from `/generate` (e.g. after page reload) is detected via `err.status === 429 && err.body.detail.code === "tts_quota_exhausted"` and also shows the quota banner.
- Failed episodes appear in the library with an **⚠ Incomplete** amber badge (`.ep-quota-badge`).
- `_clearGenerationSaveCheck()` is called in the error handler to stop the save-check interval.

---

## Validation Commands and Output

### Chef gate correction

During chef review, two small corrections were applied after the manager implementation:

- `_parse_quota_error()` now handles Python dict-style Gemini errors with single-quoted `'retryDelay': '31678s'`, matching the boss/customer report.
- Server cooldown state now preserves the exhausted TTS model name so later `/generate` 429 responses can still report the affected model.

### Python tests

```
uv run python tests/test_variety_episodes.py
```

Output:
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

All 14 tests pass (10 existing + 4 new).

### JS syntax check

```
node --check resonova/web/player.js
```

Exit code: 0 (no syntax errors).

### Python import check

```python
from resonova.api.tts import GeminiTTSQuotaError, format_duration, _parse_quota_error
from resonova.server import _get_tts_cooldown, _set_tts_cooldown, GeminiTTSQuotaError
from resonova.episodes import save_episode, list_episodes
```

All import without error.

---

## Acceptance Test Evidence (Simulated)

### 1. Normal path (no quota error)

- `_parse_quota_error` returns `None` for all non-quota exceptions → `synthesize_dialogue` propagates normally → generation completes → `save_episode(..., status="complete")` → episode appears in library without quota badge.
- Validated by `_test_quota_error_classification` (non-quota path).

### 2. Simulated 429 during intro

```python
exc = Exception('429 RESOURCE_EXHAUSTED "retryDelay": "31678s"')
result = _parse_quota_error(exc)
# result["code"] == "tts_quota_exhausted"
# result["retry_after_seconds"] == 31678
```

- `saved_queue = []` (no audio yet) → no episode saved → quota banner shown → no fake episode created.
- Validated by `_test_quota_error_classification`.

### 3. Simulated 429 after one track ready

- `saved_queue` contains intro + commentary → `save_episode(..., status="quota_failed")` called
- Episode appears in library with `status="quota_failed"` and `ep-quota-badge`
- `list_episodes()` returns `status: "quota_failed"` in summary
- Validated by `_test_failed_episode_save`.

### 4. Retry-after parsing

```python
format_duration(31678) == "8h 47m"   # ✓
format_duration(3600) == "1h"         # ✓
format_duration(45) == "45s"          # ✓
```

Validated by `_test_retry_after_formatting`.

### 5. Immediate retry blocked

- `_set_tts_cooldown(31678)` sets `_tts_cooldown_until = time.time() + 31678`
- `_get_tts_cooldown()` returns cooldown info while `time.time() < _tts_cooldown_until`
- `/generate` raises HTTP 429 → client shows quota banner, no TTS call
- `localStorage["resonova:tts-cooldown"]` persists across page reloads
- Validated by `_test_cooldown_guard_in_server`.

### 6. Existing saved episodes still load

- `list_episodes()` uses `meta.get("status", "complete")` — old episodes without `status` field default to `"complete"` and are unaffected.
- Validated by `_test_episodes_backward_compat` (pre-existing test, still passes).

---

## Remaining Risks

| Risk | Severity | Notes |
|------|----------|-------|
| Cooldown is in-process only | Low | Restarting the server clears `_tts_cooldown_until`. Client localStorage remains, providing a secondary guard across restarts. |
| Regex-based retry-after parsing | Low | If Google changes the error format, parsing may return `None`. Fallback: 1h cooldown is applied; message says "try again later". |
| `GeminiTTSQuotaError` not raised for Vertex AI path | Medium | Vertex AI uses `google.api_core.exceptions.ResourceExhausted` which has `"ResourceExhausted"` in its class name — caught by the `exc_type` check. Needs live verification once Vertex AI quota hits. |
| Partial episode playable but incomplete | Low/design | Quota-failed episodes with partial queues are playable. The ⚠ Incomplete badge makes this clear. The outro is missing if quota fires during outro synthesis. |

---

## Fallback Provider / Model Routing

**Parked.** Not implemented. The brief explicitly prohibits adding a new TTS provider or changing billing tier without boss approval. If free quota is consistently exhausted, the next step is a boss decision: upgrade to paid tier, or add a fallback provider through a separate brief.

---

## Manual Test Steps for Boss

1. Start the server: `uv run resonova`
2. Connect Spotify, paste a playlist, click Generate Cast.
3. **Normal path:** generation completes; episode appears in library without any quota badge. ✓
4. **Simulate quota failure:** in `resonova/api/tts.py`, temporarily add `raise GeminiTTSQuotaError("tts_quota_exhausted", "gemini-3.1-flash-tts-preview", 31678, "test")` at the top of `synthesize_dialogue`. Restart the server and generate:
   - Generating state appears → amber "Generation paused" banner appears
   - If intro was skipped (raised before PCM assembly), no incomplete episode in library
   - If raised after at least one track, an episode with ⚠ Incomplete badge appears
   - App shows connected state, not stuck on generating
   - "On Air" badge clears
5. **Retry during cooldown:** with the fake error still in place, click Generate Cast again:
   - Client-side: quota banner shown immediately (no network call if localStorage has cooldown)
   - Server-side: `/generate` returns 429 if localStorage was cleared
6. **After cooldown expires:** remove the fake raise, wait for `_tts_cooldown_until` to pass (or restart server), generate again — normal path resumes.
7. **Existing episodes:** click ▶ Play on any saved episode — plays correctly, no regression.
