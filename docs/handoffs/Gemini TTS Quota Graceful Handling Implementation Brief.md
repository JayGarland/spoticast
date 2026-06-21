# Gemini TTS Quota Graceful Handling Implementation Brief

Audience: Agents

## Assigned Manager

RUG manager:

`C:\Users\Administrator\.copilot\installed-plugins\awesome-copilot\rug-agentic-workflow\agents\rug-orchestrator.md`

## Chef Decision

Implement graceful handling for Gemini TTS quota exhaustion.

This task does **not** solve the upstream quota. It guarantees that quota exhaustion does not make Resonova look broken, lose generated progress, or mislead the user.

## Problem

Boss observed frequent Gemini API 429 failures:

```text
429 RESOURCE_EXHAUSTED
Quota exceeded for metric:
generativelanguage.googleapis.com/generate_requests_per_model_per_day
limit: 100
model: gemini-3.1-flash-tts
RetryInfo: retryDelay ~= 8h47m
```

Current behavior is product-hostile:

- generation can fail midway through TTS,
- the generated cast may not appear in the Episodes section,
- the user may assume the cast is lost,
- the UI may keep showing misleading generation state,
- repeated retries can keep burning requests or fail again without explanation.

## Evidence To Inspect First

Read these files before changing code:

- `resonova/config.py`
- `resonova/api/tts.py`
- `resonova/server.py`
- `resonova/storage/episodes.py`
- `resonova/web/player.js`
- `resonova/web/index.html`
- `resonova/web/styles.css`
- `.env.example`

Key current facts:

- Script model is `GEMINI_MODEL=gemini-3.5-flash`.
- TTS model is `GEMINI_TTS_MODEL=gemini-3.1-flash-tts-preview`.
- Each intro, track commentary, and outro uses one TTS request.
- Episodes are currently saved only after all TTS work completes.

## Required Product Guarantees

After this patch:

1. If Gemini TTS quota is exhausted, the user sees a clear message:
   - quota exhausted,
   - which model failed if known,
   - retry-after time if available.
2. A partly generated cast is not invisible:
   - it must remain visible as current/incomplete/failed in the library or current-cast section,
   - it must not look like a successfully completed episode.
3. The app must stop pretending generation is still running after a quota failure.
4. The app must avoid immediate blind retry loops while the quota cooldown is known.
5. Existing completed episodes must still load and play.

## Non-Goals

Do not do these in this task:

- Do not add a new paid TTS provider.
- Do not change billing tier or Google project settings.
- Do not silently downgrade to a lower-quality provider without boss approval.
- Do not create a broad model-router architecture.
- Do not rewrite episode storage.
- Do not add aggressive retry loops.
- Do not change unrelated UI layout.

## Recommended Implementation Shape

### 1. Add Gemini quota error classification

Add a small classifier around TTS/Gemini errors. It should detect:

- `RESOURCE_EXHAUSTED`,
- HTTP/API status `429`,
- `QuotaFailure`,
- `RetryInfo.retryDelay`,
- quota model name when present.

Output should be a structured internal object or fields such as:

```text
code: "tts_quota_exhausted"
model: "gemini-3.1-flash-tts-preview" or API-provided model
retry_after_seconds: number | null
message: user-facing string
```

### 2. Emit structured generation errors

When `_run_generation` catches quota exhaustion:

- set job status to `error`,
- push an SSE `error` event with structured fields,
- include a user-facing message,
- include retry-after if available.

Do not hide the raw status in logs.

### 3. Preserve partial generation visibility

If generation fails after intro or some track commentaries are already generated:

- save enough episode/job state that the UI can show the cast as incomplete or failed,
- do not mark it as complete,
- do not show "Episode Complete",
- do not make it disappear from the library/current-cast area.

Keep this minimal. If the current episode storage format cannot safely support partial episodes, implement a minimal generation-status record rather than a broad schema rewrite.

### 4. UI behavior

The UI should show a clear recoverable state, for example:

```text
Generation paused: Gemini TTS quota exhausted.
Retry after about 8h 48m.
Generated segments so far are saved.
```

Avoid phrasing that tells the user to reconnect Spotify; this is unrelated to Spotify.

### 5. Local cooldown guard

When a retry-after is known, store a lightweight cooldown marker server-side or client-side so immediate retries can be blocked with the same clear message.

This is not a quota accounting system. It is only a safety guard after a known quota failure.

## Acceptance Tests

Manager must provide validation evidence for:

1. Normal generation path still works when no quota error occurs.
2. Simulated Gemini TTS 429 during intro:
   - UI shows quota message,
   - no completed episode is falsely created,
   - generation stops cleanly.
3. Simulated Gemini TTS 429 after at least one `track_ready`:
   - generated progress remains visible,
   - library/current-cast area does not imply the cast is lost,
   - app does not show "Episode Complete".
4. Retry-after parsing:
   - `31678s` or equivalent displays as a human-readable wait.
5. Immediate retry during cooldown:
   - does not call TTS again,
   - shows the cooldown/quota message.
6. Existing saved episodes still load.

Preferred validation:

- add or update focused tests if the repo already has adjacent test patterns,
- run `node --check resonova/web/player.js`,
- run relevant Python import/test commands,
- include exact commands in the handoff.

## Required Handoff

Write the manager handoff to:

`docs/handoffs/Gemini TTS Quota Graceful Handling Handoff.md`

The handoff must include:

- changed files,
- exact behavior before/after,
- validation commands and output summary,
- remaining risks,
- whether fallback provider/model routing is still parked,
- manual test steps for boss.

## Chef Gate Notes

Chef will reject the work if:

- it retries quota failures aggressively,
- it hides partial generation,
- it creates fake successful episodes,
- it changes unrelated strategy docs or formatting,
- it introduces provider/billing decisions without boss approval,
- it does not include a handoff.
