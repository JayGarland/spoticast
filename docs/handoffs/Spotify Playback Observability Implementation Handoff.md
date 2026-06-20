---
title: "Spotify Playback Observability Implementation Handoff"
created: 2026-06-20
status: complete
brief: "docs/handoffs/Spotify Playback Observability Implementation Brief.md"
---

# Spotify Playback Observability Implementation Handoff

## Files Changed

| File | Change |
|---|---|
| `resonova/web/player.js` | Observability ring buffer, event hooks, updated `_renderDiagnostics`, new `_obsRecord` / `_copyObsTimeline` / `_refreshDiagnostics` methods |
| `resonova/web/styles.css` | Added CSS for `.spotify-diag-section-label`, `.spotify-diag-event`, `.spotify-diag-etime`, `.spotify-diag-ename`, `.spotify-diag-edetail` |
| `docs/handoffs/Spotify Playback Observability Implementation Handoff.md` | This file |

No other files were changed. `.env` was not touched.

Chef review adjustments after manager implementation:

- Event timeline detail is HTML-escaped before rendering into the diagnostic panel.
- `_obsRecord()` refreshes the visible diagnostic panel immediately when `Diag` is enabled.
- Diagnostic section label letter spacing was reset to `0` to match UI constraints.

---

## Exact Behavior Added

### 1. Observability Ring Buffer

- `this._obsTimeline` — a bounded array (max 50 entries) stored on `ResonovaPlayer`.
- `this._deviceGeneration` — integer, incremented each time the SDK reports a new `ready` device.
- `this._deviceAcquiredAt` — `Date.now()` timestamp recorded at each new `ready` event.
- `_obsRecord(event, detail)` — appends `{ t: Date.now(), event, detail }` and trims to 50.
- `_obsRecord()` also refreshes the visible diagnostic panel when `Diag` is enabled.

### 2. Event Categories Wired

| Category | Events recorded |
|---|---|
| **Online/offline** | `online:init` at startup (with `online`/`offline` value); `online` / `offline` on browser window events |
| **Page lifecycle** | `pageshow` with `persisted=true/false`; `pagehide` with `persisted=true/false`; `visibilitychange` with `visible`/`hidden` value |
| **Spotify device** | `device:ready gen=N id=...XXXXXX` (last 6 chars of device ID, generation counter); `device:discard` with truncated reason |
| **Recovery lifecycle** | `recovery:start`; `recovery:success`; `recovery:fail` with truncated error message |
| **Play command** | `play:cmd:start` with last 24 chars of URI; `play:cmd:ok` with HTTP status; `play:cmd:fail` with `status:body-prefix` |
| **Playback start** | `play:start:confirmed` / `play:start:blind` / `play:start:failed`; all three have an optional `retry` detail on the retry path |
| **Deadlines** | `deadline:blind:armed` with ms; `deadline:blind:fired`; `deadline:seg:armed` with ms; `deadline:seg:fired` |

### 3. Diagnostic Panel Updates

The existing `Diag` panel (`_renderDiagnostics`) now shows at the top:

- **Online** — `yes` / `NO` (warn if offline), reads `navigator.onLine` live
- **Device gen** — current `_deviceGeneration` count
- **Device age** — seconds/minutes since last `ready` event

Below the existing rows there is a new **Events** section showing the 10 most recent timeline entries (newest first), each showing `HH:MM:SS event detail`.

Event names and detail strings are escaped before insertion into `innerHTML`; token values and full device IDs are not logged.

Two buttons are rendered side-by-side:
- **Refresh State** — existing behavior (queries current Spotify SDK state)
- **Copy Timeline** — calls `_copyObsTimeline()` which writes all 50 buffered events (ISO timestamps) to the clipboard via `navigator.clipboard.writeText`; falls back to `console.log` if clipboard is unavailable.

### 4. No Behavior Changes

The following were **not changed**:
- Recovery logic (`_recoverSpotifySession`, timeouts, retry counts)
- Play/skip/previous/pause/resume behavior
- Blind deadline firing logic (only a record call was added alongside existing behavior)
- Segment deadline firing logic (same — record only)
- Queue advancement
- Episode generation / cache
- `.env` / token / server auth

---

## Verification Commands and Results

```powershell
# 1. Syntax check
node --check resonova/web/player.js
# → (exit 0, no output)

# 2. Server import
uv run python -c "from resonova import server; print('server ok')"
# → server ok

# 3. Whitespace check
git diff --check
# → Only line-ending warnings (CRLF on Windows) — exit 0, no content errors
```

All three passed.

---

## Manual Desktop Smoke Test Checklist

- [ ] Start Resonova (`uv run python -m resonova`)
- [ ] Enable `Diag` panel
- [ ] Confirm `Online`, `Device gen`, `Device age`, `Events` section appear at top
- [ ] Switch browser tab away and back → confirm `visibilitychange hidden` + `visibilitychange visible` in Events
- [ ] Use DevTools Network → Offline → Online → confirm `offline` + `online` in Events
- [ ] Click **Copy Timeline** → paste confirms ISO-timestamp lines
- [ ] Play a Spotify segment → confirm `play:cmd:start`, `play:cmd:ok`, `play:start:confirmed` or `play:start:blind` in Events
- [ ] Confirm `deadline:seg:armed` appears after Spotify state change fires

---

## Real-Phone Acceptance Test Checklist

1. Enable `Diag` on phone browser.
2. Play a cast until a Spotify segment.
3. Lock/idle phone long enough to trigger the intermittent issue.
4. Return to page.
5. Tap **Copy Timeline**.
6. Paste and inspect. The timeline should make one of the following branches clear:
   - `offline` + `online` → network interruption
   - `pagehide persisted=true` + `pageshow persisted=true` → bfcache restore
   - `visibilitychange hidden` → `device:discard` → `recovery:start` → stale device rebuild
   - `play:cmd:ok` + `play:start:blind` → play accepted but audio stalled (blind mode)

---

## Risks / Parked Follow-up Work

| Risk | Notes |
|---|---|
| `navigator.clipboard` unavailable on some mobile browsers | Fallback logs to console; clipboard API requires HTTPS or localhost — Tailscale HTTPS setup already done |
| Ring buffer holds up to 50 entries; busy sessions may overflow older events | Increase cap if needed; 50 is sufficient for a single failure incident |
| `Device age` resets on any rebuild, not wall-clock session age | This is correct — it reflects how long the *current* device has been alive |

Parked (not implemented, per brief):
- Stall-aware playback verification (position-not-advancing detection)
- Replacing blind playback behavior
- Explicit offline UI state
- "Skip music, keep commentary" fallback
- Cast cache / loaded-cast management

All of these require evidence from this observability pass first.
