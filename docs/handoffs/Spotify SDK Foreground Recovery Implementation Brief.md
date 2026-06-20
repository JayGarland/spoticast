# Spotify SDK Foreground Recovery Implementation Brief

## Intended Manager

Use **RUG manager** for implementation.

This is a bounded repair task. Do not redesign the player, do not add polling loops, and do not attempt to make locked-screen transitions automatic. The goal is foreground recovery after the user returns from lockscreen/idle and the Spotify SDK is in `auth_error`, `playback_error`, or `not_ready`.

## Background

Owner-validated failure after commit `98ae62d`:

- Previous works while the phone screen/page is active.
- After lockscreen/idle, playback interrupts.
- Returning to the page and pressing Previous can show `playback_error` and `auth failed`.
- After that, Spotify music segments remain unavailable until full page reload.

External audit report:

- `docs/handoffs/External Mobile Playback Implementation Audit Report.md`

Audit verdict:

- Do **not** roll back.
- Current resume/timeline/previous scaffolding is useful.
- Root cause is missing client-side SDK recovery.
- Server-side token refresh already exists through `/auth/token`.

Chef verification:

- `SPOTIFY_CLIENT_SECRET` is present in `.env` without printing its value.
- `resonova/api/spotify.py:get_current_token()` refreshes expired token server-side.

## Current Root Cause

In `resonova/web/player.js`:

- `not_ready` only nulls `deviceId` and records diagnostics.
- `authentication_error` only records diagnostics.
- `playback_error` only records diagnostics.
- `_reconcileAfterBackground()` logs/saves state but does not reconnect/rebuild Spotify SDK.
- `_playSpotifyTrack()` attempts playback even when `deviceId` is null or SDK is unhealthy.
- `previous()` can route back into a Spotify item while SDK is unhealthy, causing another error.

Reload works because reload reconstructs the Spotify SDK/player/device. We need a bounded in-page version of that reconstruction.

## Implementation Goal

Add one bounded foreground recovery path:

```text
fresh token from /auth/token
→ reconnect or rebuild Spotify.Player
→ wait once for ready/device_id
→ transfer playback to device_id
→ clear health flags
→ retry the current Spotify item once
```

Also add health gating:

- Spotify segments must not call `/me/player/play` until SDK is healthy.
- Previous to a Spotify segment must recover first or show manual recovery state.
- Returning from lockscreen (`visibilitychange -> visible`) must run one recovery attempt if Spotify is unhealthy.

## Required Code Changes

All code changes should be in:

- `resonova/web/player.js`
- `resonova/web/index.html` only if needed for a visible manual control
- `resonova/web/styles.css` only if needed for that control

Do not change backend unless a true blocker is found.

### 1. Add Health State

Add small fields in `constructor()`:

```js
this._spotifyUnhealthy = false;
this._spotifyRecovering = false;
this._spotifyRecoveryPromise = null;
this._spotifyRecoveryFailed = false;
```

Use existing `_lifecycle.authError`, `_lifecycle.playbackError`, `_lifecycle.notReady`, and `this.deviceId`.

Add helper:

```js
_isSpotifyHealthy() {
  return !!this.spotifyPlayer &&
    !!this.deviceId &&
    !this._lifecycle.authError &&
    !this._lifecycle.playbackError &&
    !this._lifecycle.notReady &&
    !this._spotifyUnhealthy;
}
```

### 2. Centralize Error Marking

Add:

```js
_markSpotifyUnhealthy(reason, message) {
  this._spotifyUnhealthy = true;
  this._spotifyRecoveryFailed = false;
  if (reason === 'auth') this._lifecycle.authError = message || 'authentication_error';
  if (reason === 'playback') this._lifecycle.playbackError = message || 'playback_error';
  if (reason === 'not_ready') this._lifecycle.notReady = message || true;
  this._renderDiagnostics(null);
  this._updateRecoveryControl();
}
```

Wire existing listeners to call this helper:

- `not_ready`
- `authentication_error`
- `playback_error`

Do not trigger automatic repeated recovery from the listeners themselves. Recovery should happen on foreground return, Spotify play attempt, or manual button.

### 3. Add `_recoverSpotifySession()`

Add one bounded recovery routine:

```js
async _recoverSpotifySession() {
  if (this._spotifyRecovering) return this._spotifyRecoveryPromise;

  this._spotifyRecovering = true;
  this._spotifyRecoveryFailed = false;
  this._updateRecoveryControl();

  this._spotifyRecoveryPromise = (async () => {
    try {
      const { token } = await this._apiFetch('/auth/token');
      if (!token) throw new Error('No Spotify token');
      this._cachedToken = token;

      // First try to reconnect existing player.
      if (this.spotifyPlayer) {
        try { await this.spotifyPlayer.connect(); } catch (_) {}
      }

      let deviceId = await this._waitForSpotifyDevice(3000);

      // If reconnect did not produce a device, rebuild once.
      if (!deviceId) {
        try { this.spotifyPlayer?.disconnect(); } catch (_) {}
        this.spotifyPlayer = null;
        this.deviceId = null;
        this._lifecycle.ready = false;
        this._lifecycle.deviceId = null;
        await this._initSpotifyPlayer();
        deviceId = await this._waitForSpotifyDevice(5000);
      }

      if (!deviceId) throw new Error('Spotify device did not become ready');

      await this._transferPlayback(deviceId, token);

      this._spotifyUnhealthy = false;
      this._spotifyRecoveryFailed = false;
      this._lifecycle.authError = null;
      this._lifecycle.playbackError = null;
      this._lifecycle.notReady = false;
      this._lifecycle.ready = true;
      this._lifecycle.deviceId = deviceId;
      this._renderDiagnostics(null);
      return true;
    } catch (err) {
      console.warn('[Resonova] Spotify recovery failed:', err);
      this._spotifyRecoveryFailed = true;
      this._renderDiagnostics(null);
      return false;
    } finally {
      this._spotifyRecovering = false;
      this._spotifyRecoveryPromise = null;
      this._updateRecoveryControl();
    }
  })();

  return this._spotifyRecoveryPromise;
}
```

This pseudocode may need adjustment if `_initSpotifyPlayer()` should be split into a build/listener method. Keep it small and local.

### 4. Add `_waitForSpotifyDevice(timeoutMs)`

Add helper:

```js
_waitForSpotifyDevice(timeoutMs) {
  if (this.deviceId) return Promise.resolve(this.deviceId);
  return new Promise(resolve => {
    const started = Date.now();
    const id = setInterval(() => {
      if (this.deviceId) {
        clearInterval(id);
        resolve(this.deviceId);
      } else if (Date.now() - started >= timeoutMs) {
        clearInterval(id);
        resolve(null);
      }
    }, 100);
  });
}
```

This is bounded and foreground-only. Do not create a long-running monitor.

### 5. Gate `_playSpotifyTrack(item)`

Before metadata fetch and `/me/player/play`, ensure SDK health:

```js
if (!this._isSpotifyHealthy()) {
  const recovered = await this._recoverSpotifySession();
  if (!recovered) {
    this._showSpotifyRecoveryNeeded();
    return;
  }
}
```

Important:

- Do **not** call `_playNext()` when recovery fails. That silently skips all music and creates commentary-only behavior.
- Do not loop.
- On success, continue with the normal play path.

### 6. Gate `previous()`

When the target previous item is Spotify:

- If SDK is unhealthy, run `_recoverSpotifySession()` before `_playNext()`.
- If recovery fails, keep current queue/timeline state stable and show the manual recovery affordance.
- Previous to commentary remains safe.

Implementation detail:

- Determine `previousItem` first.
- If `previousItem.type === 'spotify' && !this._isSpotifyHealthy()`, recover before mutating `queue/currentItem/currentIndex`.

### 7. Wire Foreground Reconciliation

In `_reconcileAfterBackground()`:

- If `_lifecycle.authError`, `_lifecycle.playbackError`, `_lifecycle.notReady`, `!this.deviceId`, or `_spotifyUnhealthy`, run exactly one `await this._recoverSpotifySession()`.
- If recovery succeeds and current item is Spotify, retry current item once.
- If recovery fails, show manual recovery affordance.

Do not add background polling.

### 8. Add Manual Recovery Affordance

Add a visible control in playing state:

- Label: `Recover Spotify`
- Hidden by default.
- Visible when `_spotifyRecoveryFailed` or `_spotifyUnhealthy` is true.
- Disabled/label changes while `_spotifyRecovering`.
- Click calls `_recoverSpotifySession()` and, if current item is Spotify and recovery succeeds, retries `_playSpotifyTrack(this.currentItem)`.

Prefer a small button near existing playback controls. It must not cover Skip/Previous on mobile.

## Acceptance Tests

### Static/Local

Run:

```bash
node --check resonova/web/player.js
uv run python -c "from resonova import server; print('server ok')"
git diff --check
```

### Desktop Smoke

1. Start server:
   ```bash
   uv run resonova
   ```
2. Verify:
   ```bash
   curl http://127.0.0.1:8765/
   curl http://127.0.0.1:8765/web/player.js?v=20260620-previous-control
   ```
3. Open desktop app.
4. Play saved episode.
5. Active-screen Previous and Skip still work.
6. No recovery button visible while healthy.

### Simulated Unhealthy State In Browser Console

In desktop console:

```js
resonova._markSpotifyUnhealthy('auth', 'test auth failure')
```

Expected:

- Recover Spotify button appears.
- Pressing Recover attempts bounded recovery.
- Button does not cover Previous/Skip.
- No infinite retry loop.

### Mobile Real Test

1. Start server and verify Tailscale HTTPS returns 200.
2. Open phone URL:
   `https://buttking.tail15ea24.ts.net:8765`
3. Start an episode and confirm active-screen playback.
4. Lock phone during a Spotify segment for long enough to trigger interruption.
5. Return to page.
6. Expected:
   - If SDK is unhealthy, app shows `Recover Spotify` or auto-attempts recovery once.
   - Pressing Previous must not immediately cause another `auth failed` / `playback_error`.
   - After successful recovery, Spotify music segments can play without full page reload.
   - If recovery fails, app should ask for manual recovery/reload instead of silently skipping all music.

## Do Not Do

- Do not add indefinite polling.
- Do not add timer-based lockscreen transition patches.
- Do not rely on Previous as recovery.
- Do not silently call `_playNext()` on failed Spotify recovery.
- Do not remove resume/timeline/previous scaffolding.
- Do not add native app/PWA work in this task.
- Do not expose `.env`, tokens, or secrets.

## Expected Handoff From RUG

Return:

- Files changed.
- Exact code paths changed.
- Validation commands and outputs.
- Manual test checklist.
- Any remaining blocker.
- Whether recovery is confirmed only in desktop simulation or also on real phone.

If implementation cannot be kept bounded, stop and return a design note instead of patching broadly.
