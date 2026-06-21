# Gemini TTS Backup Resource Failover Handoff

Date: 2026-06-21
Task: Gemini TTS Backup Resource Failover Implementation
Status: Complete — validated, not committed

---

## Changed Files

| File | Change |
|---|---|
| `resonova/config.py` | Added `gemini_tts_api_key` and `gemini_tts_backup_api_keys` settings |
| `.env.example` | Documented new TTS backup config variables with project-isolation warning |
| `resonova/api/tts.py` | Replaced single-client pattern with resource pool + per-resource cooldown failover |
| `tests/test_tts_failover.py` | New focused test file (5 tests, no real API calls) |

**Not touched:** `resonova/server.py`, all frontend files, `resonova/api/gemini.py`, any other module.

---

## Exact Config Names

```text
GEMINI_TTS_API_KEY=          # Optional. Overrides GEMINI_API_KEY for TTS primary resource only.
GEMINI_TTS_BACKUP_API_KEYS=  # Optional. Comma-separated API keys from SEPARATE Google projects.
```

Both variables are optional and default to `None`. Existing deployments using only `GEMINI_API_KEY` continue to work without any config changes.

---

## Failover Behavior

1. **Resource list is built once lazily** on the first `synthesize_dialogue` call. Order:
   - `primary` — uses `GEMINI_TTS_API_KEY` if set, else `GEMINI_API_KEY`, else Vertex AI / ADC
   - `backup_1`, `backup_2`, … — one entry per non-empty entry in `GEMINI_TTS_BACKUP_API_KEYS`

2. **On each TTS synthesis call:**
   - Resources whose per-resource cooldown is still active are skipped without an API call.
   - The first available resource is tried.
   - **Success** → return audio bytes immediately.
   - **Quota error (429 / RESOURCE_EXHAUSTED)** → mark that resource cooling (uses `retryDelay` from API response if available, otherwise 1 hour default), log a warning with label + model name only (no key values), then continue to the next resource.
   - **Non-quota error** → re-raised immediately; backups are not tried for unrelated failures (network, auth, malformed payload, etc.).

3. **When all resources are exhausted or cooling:**
   - `GeminiTTSQuotaError` is raised with:
     - `code="tts_quota_exhausted"`
     - `model` extracted from the error body (or falls back to config value)
     - `retry_after_seconds` = earliest remaining cooldown across all resources
     - `message` stating that all configured resources are exhausted (no key values included)
   - The existing server-level `except GeminiTTSQuotaError` handler in `_run_generation` catches this, calls `_set_tts_cooldown`, saves any partial episode, and pushes the quota error event to the client UI. **No server changes were required.**

---

## Server-Level vs. Per-Resource Cooldown

| Layer | Where | Purpose |
|---|---|---|
| Per-resource cooldown | `tts.py` `_TtsResource._cooldown_until` | Prevents retrying a specific exhausted project within a running job |
| Process-wide cooldown | `server.py` `_tts_cooldown_until` | Blocks starting new generation jobs while all resources are known-exhausted |

These are complementary, not redundant. The server gate prevents wasted job starts; the per-resource gate enables transparent failover within a running job.

---

## Tests Run

```
uv run python tests/test_tts_failover.py
```

Results:
```
  backup_key_parsing ✓
  primary_quota_backup_success ✓
  all_resources_exhausted ✓
  non_quota_error_no_backup ✓
  cooling_resource_is_skipped ✓
All TTS failover tests passed ✓
```

```
uv run python tests/test_variety_episodes.py
```

Results (all 14 existing tests):
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

```
uv run python -c "from resonova.api import tts; print('tts import ok')"
# → tts import ok

node --check resonova/web/player.js
# → (clean, exit 0)
```

---

## Remaining Risks

- **Vertex AI backup path not implemented.** Backup keys are API-key-only. If the primary uses Vertex AI / ADC, there is no way to specify a backup Vertex AI project via `GEMINI_TTS_BACKUP_API_KEYS` (ADC does not take an API key). This is a deliberate scope boundary — the brief allows comma-separated API keys only.

- **Resource list is process-scoped.** Cooldown state lives in memory. A server restart clears per-resource cooldowns (same as the existing server-level cooldown). This is expected behavior.

- **No cross-process or persistent cooldown.** If the app is deployed with multiple workers, each process maintains its own resource list and cooldown state. This is acceptable for the current single-process deployment but should be noted for future scaling.

- **Same-project backup keys.** The config and `.env.example` document that backup keys from the same Google project share the same per-project quota. Users who misconfigure this will not get quota relief, but the failover path will still work without errors — it just won't help.

---

## Boss Setup Instructions — Adding a Second Google Project/API Key

1. Create a new Google Cloud project (or use an existing one that is **not** the same project as the current API key).
2. Enable the **Generative Language API** (AI Studio API) in that project.
3. Create an API key at [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) for that project.
4. Add to `.env`:
   ```
   GEMINI_TTS_BACKUP_API_KEYS=your_new_project_api_key_here
   ```
   For two backups from two separate projects:
   ```
   GEMINI_TTS_BACKUP_API_KEYS=key_from_project_b,key_from_project_c
   ```
5. Restart Resonova. No other config changes are needed.
6. Optionally set `GEMINI_TTS_API_KEY` if you want TTS to use a specific primary credential instead of the general `GEMINI_API_KEY`. This does not create extra TTS quota when the key belongs to the same Google project; use separate-project backup keys for additional TTS capacity:
   ```
   GEMINI_TTS_API_KEY=key_from_primary_project_dedicated_to_tts
   ```

**Verification:** On next quota exhaustion, the server log will show:
```
WARNING  resonova.api.tts: TTS resource primary quota exhausted (model=...); trying next resource.
```
and generation will continue using the backup resource.
