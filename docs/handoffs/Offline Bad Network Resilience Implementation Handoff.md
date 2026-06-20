# Offline / Bad-Network Resilience — Implementation Handoff

Created: 2026-06-20
Status: Implemented and chef-reviewed

---

## Files Changed

| File | Change summary |
|------|----------------|
| `resonova/web/player.js` | Safer `_apiFetch`, network status methods, episodes cache, episode detail cache, Spotify offline guardrail, Skip Music button, auth error annotation |
| `resonova/web/index.html` | Added `#network-status` banner element; added `#skip-music-btn` in playback controls |
| `resonova/web/styles.css` | Added `.network-status`, `#skip-music-btn`, and `.cache-notice` styles |
| `docs/handoffs/Offline Bad Network Resilience Implementation Handoff.md` | This file |

Chef review adjustments after manager implementation:

- Prevented double-wiring of the `Skip Music` click handler.
- Changed offline/network failure during initial auth check to show the connected/library view and load cached saved casts instead of dropping to the landing page.
- Removed duplicate cache notices before rendering a new cached-library notice.
- Reset new CSS letter spacing to `0`.
- Updated the frontend cache-bust query string for `player.js`.

---

## Exact Behavior Added

### 1. Network Status UX (`#network-status` banner)
- Fixed banner below the header, visible to all users (not Diag-gated).
- Text: `"Offline — saved casts only"` (kind=`offline`) or `"Connection unstable"` (kind=`network`).
- Hidden by default (`display:none`); shown on `window.offline` event or when a local `/api/*` fetch throws a network/offline error.
- Auto-clears on `window.online` event or when any local API request succeeds.
- All show/hide transitions are recorded in the observability timeline via `_obsRecord('network:status', kind)` and `_obsRecord('network:clear', '')`.

### 2. Safer `_apiFetch()`
- Wraps `fetch()` in try/catch to distinguish:
  - `err.kind = 'offline'` — `navigator.onLine === false` at throw time
  - `err.kind = 'network'` — online but connection failed (backend unreachable)
  - `err.kind = 'http'` — server responded with an error status; `err.status` is set
- All existing callers preserve their ability to catch and handle errors.
- No tokens or secrets are logged.
- When a local API request (`url.startsWith('/')`) fails with offline/network, calls `_updateNetworkStatus()`.
- When a local API request succeeds, calls `_clearNetworkStatus()`.

### 3. Saved Cast Library Browser Cache
- **Key:** `resonova:episodes-cache`
- **Stored value:** `{ ts: <timestamp ms>, episodes: [...] }`
- On every successful `/api/episodes` response, the episodes array is written to `localStorage`.
- If `/api/episodes` fails (offline/network/http), the catch block reads `resonova:episodes-cache` and renders the cached episodes in the DOM.
- Cached rendering adds a `.cache-notice` banner above the episode list: `"Offline — showing saved casts from cache"`.
- Failed responses are never cached.
- `localStorage` write failures (quota) are silently ignored.
- **Optional episode detail cache:**
  - **Key:** `resonova:episode:${episodeId}`
  - **Stored value:** `{ ts: <timestamp ms>, ep: {...} }`
  - Written after every successful `/api/episodes/${episodeId}` fetch.
  - `_playEpisode()` falls back to the cached detail if the backend request fails.

### 4. Spotify Offline Guardrail
- `recoverSpotify()` checks `navigator.onLine` first.
  - If offline: records `recovery:blocked offline` in the obs timeline, calls `_setNowPlaying('Spotify unavailable offline', 'Use Next to continue commentary')`, shows the Skip Music button, and **returns without attempting recovery**. The existing recovery algorithm for online cases is unchanged.
- `_playSpotifyTrack()` checks offline before attempting auto-recovery of an unhealthy Spotify state.
  - If offline and unhealthy: records `play:spotify:offline`, shows `"Spotify unavailable offline"` + `"Use Next to continue commentary"`, removes waveform spotify-mode, shows Skip Music button.
  - Online unhealthy path is unchanged.
- `_markSpotifyUnhealthy()` annotates `authError` with `" (offline)"` suffix when `!navigator.onLine`, so the Diag panel shows context instead of only `Authentication failed`.

### 5. "Skip Music" Fallback Button
- `<button id="skip-music-btn">` added to playback controls in `index.html`, hidden by default.
- `_updateSkipMusicButton()` shows the button when:
  `currentItem.type === 'spotify' && (spotifyUnhealthy || spotifyRecoveryFailed || !navigator.onLine)`
- Action: calls `skip()` which uses the existing skip path, advancing to the next queued segment.
- Button is wired eagerly in DOMContentLoaded and guarded by `_wired` so lazy wiring cannot attach a duplicate handler.
- Button auto-hides when the segment advances to audio commentary (`_playAudio` calls `_updateSkipMusicButton`), when playback completes (`_onPlaybackComplete`), and whenever `_updateRecoveryControl` re-runs (covers health state changes).

### 6. Messaging Rules
- Auth errors while offline are annotated with `" (offline)"` in the Diag panel.
- Spotify segment failure while offline shows `"Spotify unavailable offline"` / `"Use Next to continue commentary"` rather than generic auth failure text.
- Real Spotify auth errors when online are unchanged.

---

## Cache Keys Added

| Key | Contents | Notes |
|-----|----------|-------|
| `resonova:episodes-cache` | `{ ts: number, episodes: EpisodeSummary[] }` | Written on every successful `/api/episodes` |
| `resonova:episode:${episodeId}` | `{ ts: number, ep: EpisodeDetail }` | Written on every successful `/api/episodes/${episodeId}` |

Pre-existing keys not changed: `sc:${uri}`, `resonova:resume`, `resonova:diag`.

---

## Validation Commands and Results

```powershell
node --check resonova/web/player.js
# → exit 0 (no syntax errors)

uv run python -c "from resonova import server; print('server ok')"
# → server ok, exit 0

uv run python tests/test_variety_episodes.py
# → All tests passed ✓, exit 0

git diff --check
# → LF/CRLF warnings only (expected on Windows), exit 0
```

---

## Mobile Test Checklist

- [ ] Enable Diag toggle (press **Diag** button while in playing state)
- [ ] Load library at least once online — confirm `localStorage.getItem('resonova:episodes-cache')` is non-null
- [ ] Simulate offline (airplane mode or DevTools throttling → Offline)
- [ ] Reload / navigate; confirm the `#network-status` amber banner appears
- [ ] Confirm saved casts render from cache with `"Offline — showing saved casts from cache"` notice
- [ ] Click **Recover Spotify** while offline; confirm it shows `"Spotify unavailable offline"` / `"Use Next to continue commentary"` and does **not** enter `Recovering…` loop
- [ ] Advance to a Spotify segment while offline; confirm `"Skip Music"` button appears
- [ ] Tap **Skip Music**; confirm playback advances to next commentary segment
- [ ] Return online; confirm `#network-status` banner disappears after next successful API fetch
- [ ] Copy timeline from Diag; confirm it includes `network:status`, `recovery:blocked`, `play:spotify:offline`, `network:clear` events

---

## Known Limits

- Spotify music **cannot play offline** — this is intentional. Spotify Web Playback SDK requires an active network connection. This task only adds graceful degradation messaging and the ability to skip past stuck music segments.
- No PWA / service worker — page reload while fully offline will lose the app shell.
- No true offline auth — if the user has never loaded saved casts into browser cache, the cached library cannot appear. If cached saved casts exist, initial `/auth/token` network failure now opens the connected/library view and renders those cached casts.
- Episode detail cache is never explicitly expired; it accumulates. A future task could add TTL pruning.
- The `resonova:episodes-cache` key stores the full episodes array; it is replaced on every successful load, not merged.
