# Replay Count Taste Signal Handoff

Audience: Agents

## Summary

Implemented durable saved-cast replay counting and memory-on-only replay affinity for future cast generation.

The RUG manager was invoked first, but the CLI run hung for several minutes and produced only partial edits. Chef stopped the orphaned process, salvaged the useful backend shape, completed the implementation, and gated the result.

## Changed Files

- `resonova/episodes.py`
- `resonova/server.py`
- `resonova/profile.py`
- `resonova/api/gemini.py`
- `resonova/web/player.js`
- `tests/test_variety_episodes.py`
- `tests/test_profile.py`
- `docs/handoffs/Replay Count Taste Signal Implementation Brief.md`

## Behavior Implemented

- Added `POST /api/episodes/{episode_id}/replay`.
- Added saved episode replay metadata with safe defaults for old episodes:
  - `replay_started_count`
  - `replay_count`
  - `last_started_at`
  - `last_replayed_at`
  - private `_replay_sessions` dedupe map in `episode.json`
- `start` events count once per session.
- `meaningful` events count once per session only when `completed_segments / total_segments >= 0.5`.
- Public episode/list/rename payloads include replay summary fields but do not expose private session ids.
- Saved-cast cards show `Replayed Nx` when `replay_count > 0`.
- Saved-cast replay playback reports start/meaningful events non-blockingly; live generated casts clear replay tracking and do not report replay events.
- `profile.summarize_saved_casts()` derives memory-on-only `taste_profile.replay_affinity` from meaningful replay counts.
- `build_prompt()` includes replay affinity only inside the memory-on trail portion and extends the Stance B guardrail to forbid explicit replay/past-cast callbacks.
- Memory reset still clears profile only; saved cast replay counts persist.
- Memory off keeps replay count display but does not write/use replay-derived profile trail.

## Validation

Passed:

```powershell
uv run python tests/test_variety_episodes.py
uv run python tests/test_profile.py
node --check resonova/web/player.js
git diff --check
```

Browser gate:

- Started local app on `http://127.0.0.1:8766` with `.venv\Scripts\python.exe -m uvicorn resonova.server:app --host 127.0.0.1 --port 8766`.
- Loaded the page in Chrome.
- Current page load had no console warnings/errors.
- Temporary server and tab were closed afterward.

## Notes For Chef Gate

- `git diff --check` exits clean but Windows still prints existing line-ending warnings (`LF will be replaced by CRLF`) for touched files.
- No live saved-cast playback was performed, because that would mutate the boss's real `generated/episodes` replay counts. The replay-count behavior is covered by isolated temp-dir tests.
- The replay affinity prompt signal contains playlist names as private steering text. The guardrail explicitly forbids hosts from mentioning replays, prior casts, or past-session history.

## Remaining Risks

- `_replay_sessions` can grow over time in each episode JSON. This is fine for personal/local scale, but later multi-user/cloud storage should compact or cap session dedupe data.
- Replay affinity currently uses playlist-name affinity, not artist/track-level extraction. This matches the approved plan and keeps the signal lighter.

