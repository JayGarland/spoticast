# Replay Count Taste Signal Implementation Brief

Audience: Agents

## Role

You are the RUG manager implementing a bounded Resonova feature under chef gate.

Do not commit. Stay inside this brief. Produce the required handoff when done.

## Goal

Add durable replay counting for saved cast runs and use meaningful replays as a private, memory-on-only playlist-affinity signal for future generations.

A saved-cast replay becomes meaningful after at least 50% of its segments complete. Replay counts remain visible in the library even when memory is off, but memory-off must prevent replay-derived taste signals from reaching profile/prompt personalization.

## Required Behavior

### Backend episode replay events

Add `POST /api/episodes/{episode_id}/replay`.

Payload:

```json
{
  "event": "start",
  "session_id": "uuid-or-client-token",
  "completed_segments": 0,
  "total_segments": 31
}
```

Rules:

- `event` allowed values: `start`, `meaningful`.
- `start` increments `replay_started_count` and updates `last_started_at`.
- `meaningful` increments `replay_count` and updates `last_replayed_at` only when `completed_segments / total_segments >= 0.5`.
- `meaningful` must not increment more than once for the same `session_id` on the same episode.
- `start` should also dedupe per session so retries do not inflate starts.
- Invalid episode id returns 404; invalid payload returns 400.
- Use UTC ISO timestamps, matching existing episode metadata style.

Extend episode metadata backward-compatibly:

- `replay_started_count`
- `replay_count`
- `last_started_at`
- `last_replayed_at`
- private last-session dedupe fields are acceptable in `episode.json`, but do not expose raw session ids in the UI.

Update `list_episodes()`, `get_episode()`, and rename summary output so replay count fields are returned with safe defaults for old episodes.

### Frontend replay reporting

Only saved episode replays should report replay events. A newly streaming generation must not report replay counts before it is saved.

When `_playEpisode(episodeId)` starts a saved cast:

- create a unique replay session id in the browser;
- POST `event=start`;
- start playback normally even if replay reporting fails.

During playback:

- when `completedItems / totalItems >= 0.5`, POST `event=meaningful` exactly once for that replay session;
- also post meaningful on completion if it was not already posted and threshold is met;
- do not block playback on event-report errors.

Update the saved-cast card metadata to show replay counts per run, for example `Replayed 3x`, beside existing run/order/status metadata.

### Profile and prompt

Update `profile.summarize_saved_casts()` so replayed playlists produce a memory-on-only playlist affinity trail signal.

Rules:

- Count meaningful replays (`replay_count`), not `replay_started_count`.
- Weight replayed playlist affinity higher than merely generated casts.
- Store this as trail data, not durable identity.
- When `memory_enabled=False`, do not write replay-derived trail signals.
- Existing saved-cast count should still update even when memory is off.

Update prompt construction so replay-derived playlist affinity can influence generation only when:

- not incognito;
- persistent profile exists and has content;
- `memory_enabled=True`.

Guardrail:

- The prompt may use replay-derived affinity only as private steering.
- Hosts must not mention replays, past casts, "last time", "you replayed", or prior-session history directly.
- Keep current Stance B fourth-wall behavior intact.

## Allowed Files

Expected files:

- `resonova/episodes.py`
- `resonova/server.py`
- `resonova/profile.py`
- `resonova/api/gemini.py`
- `resonova/web/player.js`
- `tests/test_variety_episodes.py`
- `tests/test_profile.py`
- `docs/handoffs/Replay Count Taste Signal Handoff.md`

Avoid unrelated UI/CSS changes unless strictly necessary for the replay-count label.

## No-Go Rules

- Do not commit.
- Do not add new Spotify scopes.
- Do not change saved episode queue playback semantics.
- Do not make hosts explicitly refer to replay history.
- Do not clear replay counts on memory reset.
- Do not make replay reporting required for playback to continue.
- Do not introduce broad formatting churn.

## Validation Required

Run:

```powershell
uv run python tests/test_variety_episodes.py
uv run python tests/test_profile.py
node --check resonova/web/player.js
```

If one cannot be run, state why in the handoff.

## Required Handoff

Write `docs/handoffs/Replay Count Taste Signal Handoff.md` with:

- changed files;
- behavior implemented;
- validation run and exact results;
- remaining risks;
- notes for chef gate;
- any assumptions or deviations from this brief.

