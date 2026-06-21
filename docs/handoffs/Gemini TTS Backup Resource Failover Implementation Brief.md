# Gemini TTS Backup Resource Failover Implementation Brief

Audience: Agents

## Assigned Manager

RUG manager:

`rug-agentic-workflow:rug-orchestrator`

## Chef Decision

Implement backup-resource failover for Gemini TTS.

This is the capacity-continuity phase after graceful quota handling. It lets Resonova use a second Google project/API key as backup TTS capacity when the primary TTS resource hits quota.

## Product Intent

Quota exhaustion should not immediately stop a cast if another approved TTS resource is configured.

Important distinction:

- Another API key in the same Google project does **not** solve per-project quota.
- Another Google project/API key can provide independent capacity.
- This implementation must not create hidden infinite retries or hide that quota pressure exists.

## Allowed Scope

Allowed files:

- `resonova/config.py`
- `.env.example`
- `resonova/api/tts.py`
- `resonova/server.py` only if needed to preserve existing cooldown semantics
- `tests/test_variety_episodes.py` or a new focused test file
- required handoff file

Avoid touching frontend unless strictly necessary. The existing UI already handles final quota failure.

## Required Config

Add explicit TTS backup configuration. Suggested names:

```text
GEMINI_TTS_API_KEY=
GEMINI_TTS_BACKUP_API_KEYS=key_from_backup_project_1,key_from_backup_project_2
```

Semantics:

- `GEMINI_TTS_API_KEY` is optional and overrides `GEMINI_API_KEY` for TTS primary only.
- If `GEMINI_TTS_API_KEY` is unset, primary TTS uses the current auth behavior:
  - `GEMINI_API_KEY`, or
  - Vertex AI / ADC fallback.
- `GEMINI_TTS_BACKUP_API_KEYS` is optional comma-separated backup API keys.
- Do not log API key values.
- `.env.example` must explain that backup keys should be from separate Google projects to provide independent quota.

## Required Runtime Behavior

In `resonova/api/tts.py`:

1. Build an ordered list of TTS resources:
   - primary,
   - backup 1,
   - backup 2,
   - etc.
2. Each resource should have:
   - safe label, e.g. `primary`, `backup_1`,
   - client kwargs,
   - per-resource cooldown timestamp.
3. On TTS synthesis:
   - skip resources whose cooldown is still active,
   - try the first available resource,
   - if it succeeds, return audio,
   - if it quota-fails, mark only that resource cooling down using retry-after if available, then try the next available resource,
   - if all resources are exhausted/cooling down, raise `GeminiTTSQuotaError` so the existing server/UI graceful failure path runs.
4. Do not retry non-quota errors against backups by default. Non-quota errors should still surface normally unless there is a narrow, justified reason.
5. The raised final `GeminiTTSQuotaError` should include:
   - `code="tts_quota_exhausted"`,
   - model,
   - retry-after for the earliest next available resource if known,
   - user-facing message that says all configured TTS resources are exhausted/cooling down.

## No-Go Rules

Do not:

- add a new provider,
- change billing,
- change Gemini script/research models,
- add frontend retry loops,
- log keys or expose key fragments,
- route to backup on arbitrary playback/network bugs,
- silently make unbounded attempts.

## Acceptance Tests

Add focused tests for:

1. Backup key parsing:
   - trims whitespace,
   - ignores empty entries,
   - preserves order.
2. Primary quota failure, backup success:
   - primary is marked cooling down,
   - backup is attempted,
   - no `GeminiTTSQuotaError` is raised.
3. All resources quota-fail:
   - final `GeminiTTSQuotaError` is raised,
   - retry-after is based on an available cooldown value,
   - no key values appear in message/log-facing fields.
4. Non-quota error:
   - does not blindly try all backups unless explicitly justified in code comments/tests.
5. Existing graceful quota tests still pass.

Validation commands:

```text
uv run python tests/test_variety_episodes.py
node --check resonova/web/player.js
uv run python -c "from resonova.api import tts; print('tts import ok')"
```

## Required Handoff

Write:

`docs/handoffs/Gemini TTS Backup Resource Failover Handoff.md`

Handoff must include:

- changed files,
- exact config names,
- failover behavior,
- tests run,
- remaining risks,
- boss setup instructions for adding a second project/API key.

## Chef Gate

Chef will inspect:

- manager response,
- handoff,
- `git status`,
- `git diff`,
- tests,
- key secrecy,
- whether unrelated dirty work was touched.
