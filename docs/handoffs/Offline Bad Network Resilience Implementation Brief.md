# Offline Bad Network Resilience Implementation Brief

Created: 2026-06-20
Owner: Chef/Codex gate
Target manager: RUG orchestrator
Status: approved for implementation

## Goal

Make Resonova degrade gracefully under bad network or offline conditions.

Do not try to make Spotify music playable offline. Spotify music segments depend on Spotify Web Playback SDK / Spotify Connect and require network. The product goal for this task is:

- no crash-like dead end
- no endless Recover Spotify trap
- no vague auth failure when the browser is offline
- saved cast library remains visible from browser cache when the backend/network request fails
- user can continue commentary when Spotify music is unavailable

## Customer Reports

Current / recent real-phone reports:

1. With bad network or offline conditions, the app becomes unusable or appears to crash.
2. A previous captured failure showed:
   - `Seg type: spotify`
   - `Device ID: yes`
   - `ready: yes`
   - `auth_error: Authentication failed`
   - Recover button stuck at `Recovering...`
3. Another severe report: Spotify cannot recover after a recovery retry, forcing the user to reload and restart.
4. User also asks about cache: when network is bad/offline, the app seems to reload all data and lose useful loaded-cast state.

## Current Relevant State

Files to inspect:

- `resonova/web/player.js`
- `resonova/web/index.html`
- `resonova/web/styles.css`
- `resonova/episodes.py`
- `resonova/server.py`

Existing cache / persistence:

- Saved casts are persisted on disk under `generated/episodes`.
- Saved cast summaries and queue are exposed via `/api/episodes` and `/api/episodes/{episode_id}`.
- Browser currently caches Spotify track metadata in `localStorage` keys `sc:${uri}`.
- Resume state exists in `localStorage` key `resonova:resume`.
- Diag visibility persists in `localStorage` key `resonova:diag`.
- There is no browser cache for saved-cast library or episode detail.
- There is no user-facing offline status.
- `_apiFetch()` currently throws raw network errors.

## Strict Scope

Allowed files:

- `resonova/web/player.js`
- `resonova/web/index.html`
- `resonova/web/styles.css`
- `docs/handoffs/Offline Bad Network Resilience Implementation Handoff.md`

Do not modify:

- server auth/token behavior
- Spotify recovery algorithm beyond offline guardrails
- episode generation backend
- `.env`
- model config

## Required Behavior

### 1. Network Status UX

Add a small user-facing network status indicator that appears when the browser is offline or a local API fetch fails due to network.

Requirements:

- show online/offline state outside the owner-only Diag panel
- text should be concise, e.g. `Offline - saved casts only` or `Connection unstable`
- hide automatically after network returns and the app has a successful local API fetch
- record events into existing observability timeline via `_obsRecord`

### 2. Safer `_apiFetch()`

Wrap fetch failures so the UI can distinguish:

- HTTP error from local server
- browser offline
- network request failed / backend unreachable

Requirements:

- preserve existing callers' ability to catch errors
- attach useful fields such as `err.kind = 'offline' | 'network' | 'http'`
- do not log tokens or secrets
- when a local API request fails from network/offline, update the network status indicator

### 3. Saved Cast Library Browser Cache

Cache successful `/api/episodes` response in `localStorage`.

Requirements:

- key: `resonova:episodes-cache`
- store timestamp and episodes array
- if `/api/episodes` fails because offline/network/backend unreachable, render cached saved casts if available
- show a subtle label/message that cached saved casts are being shown
- do not cache failed responses
- do not block the app if localStorage quota fails

Optional but preferred:

- cache `/api/episodes/{episode_id}` responses with key `resonova:episode:${episodeId}`
- `_playEpisode()` should fall back to cached episode detail if the backend request fails

### 4. Spotify Offline Guardrail

When the browser is offline or local network is unstable:

- do not let Recover Spotify loop forever
- if user clicks Recover while offline, show a clear message instead of attempting Spotify recovery
- if current segment is Spotify and network is offline/unavailable, show clear now-playing text:
  - `Spotify unavailable offline`
  - secondary: `Use Next to continue commentary`

Do not alter the existing recovery algorithm for online cases.

### 5. "Skip Music, Keep Commentary" Fallback

Add a visible fallback action when Spotify is unhealthy/offline during a music segment.

Behavior:

- button appears only when current segment is Spotify and Spotify is unhealthy, recovery failed, or offline
- label: `Skip Music`
- action: skip the current Spotify segment and advance to the next queued segment
- should use existing `skip()` path where safe
- must not appear during normal healthy playback

This is the offline/bad-network version of the parked fallback. It is now approved because the user explicitly prioritized bad-network usability.

### 6. Messaging Rules

Replace vague offline/bad-network messages where possible:

- if offline: do not show only `Authentication failed`
- if recovery fails while offline: explain offline/network
- if API fetch fails for library: show cached library if possible

Do not hide real Spotify auth errors when online.

## Non-goals

- no PWA/service worker
- no true offline reload support
- no Spotify music offline playback
- no backend caching rewrite
- no new dependencies
- no autoplay policy rewrite
- no stall-aware playback verification in this task

## Acceptance Tests

Static:

```powershell
node --check resonova/web/player.js
uv run python -c "from resonova import server; print('server ok')"
uv run python tests/test_variety_episodes.py
git diff --check
```

Manual desktop:

1. Start app.
2. Load library successfully once.
3. Confirm `localStorage.getItem('resonova:episodes-cache')` exists.
4. Simulate failed `/api/episodes` fetch or browser offline.
5. Reload connected view if possible.
6. Saved casts render from cached data with clear cached/offline message.
7. With `navigator.onLine === false`, clicking Recover Spotify does not enter endless `Recovering...`.
8. During a Spotify failure/unhealthy state, `Skip Music` appears and advances to the next segment.
9. Return online; successful API fetch hides network warning.

Real-phone:

1. Enable Diag.
2. Load saved casts once.
3. Trigger bad network / idle / offline condition.
4. Verify the app shows network/offline state instead of only generic auth failure.
5. If Spotify fails, tap `Skip Music`; commentary should continue.
6. Copy timeline; it should include offline/network/fallback events.

## Handoff Output

Create:

`docs/handoffs/Offline Bad Network Resilience Implementation Handoff.md`

Include:

- files changed
- exact behavior added
- cache keys added
- validation commands and results
- mobile test checklist
- known limits, especially that Spotify music cannot play offline
