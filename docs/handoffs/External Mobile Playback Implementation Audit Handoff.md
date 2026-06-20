# External Mobile Playback Implementation Audit Handoff

## Purpose

Commission an external auditor/inspector to audit the recent mobile playback implementations, especially the chef-level fixes around lockscreen interruption, resume state, and Previous segment fallback. The owner has validated that the latest implementation still fails after phone lockscreen/idle.

This is an audit request, not an implementation request. Do not patch first. Produce findings with evidence, reproduction notes, and a recommendation on whether to rollback, redesign, or proceed with a bounded fix.

## Product Goal Context

Resonova is a private single-user AI radio/cast MVP:

- User chooses a Spotify playlist or track list.
- Server generates AI commentary and TTS audio.
- Browser player interleaves generated commentary audio with Spotify Web Playback SDK music segments.
- Current target environment is phone browser over Tailscale HTTPS, not a native app.

The intended user experience: a continuous personal radio episode that can survive realistic mobile use, including idle/lockscreen periods, without forcing the user to restart from the beginning.

## Current Owner-Reported Failure

Latest owner test after commit `98ae62d`:

1. Previous button now works while the screen/page is active.
2. After the phone is locked and the cast plays for a while, interruption still happens.
3. On returning to the page, pressing Previous shows `playback_error` and `auth failed`.
4. After this state, Spotify music segments are unavailable until the user reloads the page.
5. User must reload and restart, making the situation worse than before the Previous button fallback.

Interpretation to verify: the Previous button did not solve the lockscreen lifecycle problem. It may now route the user into a poisoned Spotify SDK state where previous/current Spotify segments cannot play after an auth/playback failure.

## Audit Scope

Audit these areas:

- Mobile lockscreen/background lifecycle handling in `resonova/web/player.js`.
- Spotify SDK initialization, token callback, auth error, playback error, and recovery behavior.
- Previous segment implementation and whether it is safe after SDK auth/playback failure.
- Resume state persistence and whether it genuinely restores usable playback or only restores local queue state.
- Served asset/cache-busting and whether the phone is actually running current code.
- Whether browser + Spotify Web Playback SDK is still a viable path for the product goal, or whether the product needs a different playback architecture.

## Files To Inspect

- `resonova/web/player.js`
- `resonova/web/index.html`
- `resonova/server.py`
- `resonova/config.py`
- `docs/strategy/lockscreen-transition-decision-brief.md`
- `docs/strategy/mobile-playback-hardening-brief.md`
- `docs/handoffs/Mobile Lockscreen Playback Hardening Handoff.md`
- `docs/handoffs/Mobile Resume State Recovery Handoff.md`
- `docs/handoffs/Tailscale HTTPS for Mobile Spotify SDK Handoff.md`
- `docs/handoffs/External Product UX Design Audit Handoff.md`

## Commits To Inspect

Use `git show` and `git diff` directly. Do not rely only on handoffs.

- `7ab5614` — Harden mobile lockscreen playback
- `708da74` — Document lockscreen transition limitation
- `e636f29` — Add previous segment playback control
- `0c3e731` — Add mobile resume state recovery
- `fdfb05b` — Fix previous segment control state
- `98ae62d` — Harden previous segment control

Useful command:

```bash
git log --oneline -12
git show --stat --oneline 7ab5614 708da74 e636f29 0c3e731 fdfb05b 98ae62d
git diff 708da74..HEAD -- resonova/web/player.js resonova/web/index.html
```

## Known Implementation Facts

Current relevant client code features:

- `getOAuthToken` fetches `/auth/token`, caches token in `_cachedToken`, and falls back to cached token if fetch fails.
- `authentication_error`, `playback_error`, and `autoplay_failed` only update diagnostic state; they do not reinitialize or reconnect the Spotify player.
- `_reconcileAfterBackground()` runs on `visibilitychange` and calls `spotifyPlayer.getCurrentState()` only when current item is Spotify.
- Resume state is localStorage-only and persists queue/timeline/current item, not Spotify SDK device/session health.
- Previous button is now always clickable at the DOM level and uses `aria-disabled`; JS no-ops if there is no previous segment.
- Previous uses `playbackTimeline/currentIndex` plus `playedItems` fallback to rebuild the queue and replay the previous item.
- If the previous item is Spotify and SDK is in `auth_error` or `playback_error`, `_playSpotifyTrack()` likely fails again because no recovery path resets SDK/device/token state.
- `index.html` now cache-busts `player.js` with `/web/player.js?v=20260620-previous-control`.

## Evidence Already Collected

Local runtime harness against real `player.js` showed active-screen logic works:

- Segment 1: Previous unavailable (`aria-disabled=true`).
- Segment 2: Previous available (`aria-disabled=false`).
- Calling `previous()` rewinds to segment 1 in-process.

Served asset verification after starting the server:

- `http://127.0.0.1:8765/` returned 200.
- `https://buttking.tail15ea24.ts.net:8765/` returned 200.
- Both served `/web/player.js?v=20260620-previous-control` containing `_hasPreviousSegment`, `aria-disabled`, and `fallbackItem`.

Before starting the local server, Tailscale HTTPS returned 502 because nothing was listening on the configured local backend. This is a separate environment risk: external audit should verify the backend is running before mobile tests.

## Key Hypotheses To Attack

### H1: SDK Poisoned State After Lockscreen

After lockscreen/idle, Spotify SDK enters `authentication_error` or `playback_error`. The app records this in diagnostics but does not recover by refreshing token, reconnecting, rebuilding the player, transferring playback, or falling back.

Expected evidence:

- Diagnostics show `auth_error` and/or `playback_err`.
- `_playSpotifyTrack()` continues to call `spotifyPlayer.setVolume()` and Web API `/me/player/play` on a broken device/session.
- Reload works because it reconstructs SDK/player/device state.

### H2: Resume/Previous Only Restore Queue State, Not Playback Capability

Resume and Previous rebuild local queue state but do not restore the Spotify device/session. This can make UI state look recoverable while music remains broken.

Expected evidence:

- Commentary segments may play.
- Spotify segments fail until reload.
- Previous to a Spotify segment after auth failure triggers `playback_error` again.

### H3: Browser SDK Is Not Sufficient For Lockscreen Product Goal

Even if foreground playback works, lockscreen/background page lifecycle may freeze timers, token fetches, and SDK iframe events enough that a reliable continuous radio product cannot be achieved in this architecture.

Expected evidence:

- Failures occur only after lockscreen/idle, not active foreground.
- Reload fixes because it reconstructs browser/SDK state.
- Prior bounded timer/token fixes reduce symptoms but do not eliminate lockscreen breakage.

### H4: Control Fallback Is Mispositioned

Previous is useful only while the SDK is healthy. Once SDK auth/playback is broken, Previous cannot be the main recovery affordance. The product may need a "Recover Spotify session" action, auto SDK rebuild, or a non-SDK music fallback.

## Auditor Tasks

1. Reproduce the owner scenario on mobile:
   - Start server.
   - Open `https://buttking.tail15ea24.ts.net:8765`.
   - Start a generated or saved episode.
   - Confirm active-screen Previous works.
   - Lock phone and let it play long enough to interrupt.
   - Return to page and press Previous.
   - Record diagnostic fields: `auth_error`, `playback_err`, `ready`, `device_id`, `not_ready`, `autoplay_fail`, current segment type, queue count.

2. Inspect code paths:
   - `_initSpotifyPlayer()`
   - `getOAuthToken`
   - `authentication_error` listener
   - `playback_error` listener
   - `_playSpotifyTrack()`
   - `_reconcileAfterBackground()`
   - `previous()`
   - `_resumePlayback()`

3. Decide whether the current implementation should be:
   - accepted with a bounded recovery fix,
   - rolled back to `708da74` plus a different recovery design,
   - or redesigned around a different playback architecture.

4. Produce a concise audit report with:
   - findings ranked by severity,
   - file/line references,
   - reproduction evidence,
   - recommended next action,
   - specific "do not do" list to avoid another timer/retry patch spiral.

## Questions The Auditor Must Answer

1. When SDK has `auth_error` or `playback_error`, what exact recovery action is required before attempting any Spotify segment again?
2. Should `previous()` avoid replaying Spotify segments while SDK is unhealthy and instead show a recover/reload action?
3. Is it viable to rebuild Spotify Player in-page after auth/playback failure without a full reload?
4. Should Resonova add a visible "Recover Spotify" control or automatic SDK reset on `visibilitychange`?
5. Should the product stop relying on Spotify Web Playback SDK for mobile lockscreen continuity and move to a different fallback for music segments?

## Non-Goals

- Do not implement native app/PWA during the audit.
- Do not add broad polling loops, retry storms, or hidden timers.
- Do not add unrelated UI redesign.
- Do not expose `.env` secrets or Spotify tokens.
- Do not trust previous manager or chef handoffs without checking code and runtime behavior.

## Current Working State

As of this handoff:

- Branch: `main`
- Latest relevant commit: `98ae62d Harden previous segment control`
- Repo was clean before this audit handoff file was created.
- Server may need to be started manually before mobile test:

```bash
uv run resonova
```

Then verify:

```bash
curl http://127.0.0.1:8765/
curl -k https://buttking.tail15ea24.ts.net:8765/
```
