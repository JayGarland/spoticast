---
title: "Spotify SDK Foreground Recovery Implementation"
source: "f:\\GitHub\\resonova\\docs\\handoffs\\Spotify SDK Foreground Recovery Implementation Brief.md"
author: ""
published: false
created: 2026-06-20
description: "Implementation of the bounded Spotify SDK foreground recovery path and health gating."
tags:
  - handoff
---

## Goal

The goal is to implement a robust, bounded Spotify SDK foreground recovery path to prevent silent audio failures and stuck state transitions (especially on the Previous button) when a user returns to the app from a suspended state/background/locked screen on mobile.

## Current Progress

We have fully implemented and statically verified the bounded recovery mechanism:

* **Health State Management**: Added constructor flags to track Spotify SDK health and recovery status. Created centralized helpers to mark or clear unhealthiness, updating the diagnostic panel and UI overlays synchronously.
* **Web Playback SDK listeners**: Integrated the new error-marking and health-restoration helpers directly into the SDK's `ready`, `not_ready`, `authentication_error`, and `playback_error` callbacks.
* **One Bounded Recovery Path**: Implemented `_recoverSpotifySession()` to perform a single closed-loop recovery: fetch a fresh token -> try direct player connect() with 3000ms await -> fallback to full player teardown/rebuild and init with 5000ms await -> transfer playback to active device -> clean health flags.
* **Playback Health Gate**: Integrated check gate at the start of playing a Spotify track. If it fails to play or recover, it gracefully halts playback with visual indications instead of falling back to a silent skip to the next track.
* **Previous Button Guard**: Made `previous()` asynchronous, adding a check to recover Spotify if the target segment is Spotify and the SDK is currently unhealthy. If recovery fails, it preserves index states and aborts, showing manual indicators.
* **Foreground Auto-Recovery**: Wired check inside `_reconcileAfterBackground()` to trigger a single auto-recovery if returning to the foreground (on `visibilitychange`) with an unhealthy Spotify player.
* **Manual Recovery UI**: Integrated a visible "Recover Spotify" button into `.playback-controls` that displays beautifully during failures on mobile (inheriting existing styles with a soft warning color border).

## What Worked

* **Centralized Health State**: Funneling all SDK errors through `_markSpotifyUnhealthy` avoids duplicating diagnostic rendering or button updates.
* **Limited Await Timers**: Using a controlled interval-checking loop with strict 3000ms and 5000ms caps avoids infinite wait blocks or lockups in suspended mobile environments.
* **Non-destructive Failures**: Halting playback and retaining queue position rather than forcefully executing `_playNext()` prevents commentary from playing alone (which ruins the "radio show" illusion).

## What Didn't Work

* **Automatic Silent Transitions in Background**: We avoided trying to patch locked-screen transition errors automatically because mobile OS sleep rules freeze background iFrames/timers, which makes auto-reconciliation impossible. Manual manual recover button and foreground change triggers are the correct compromise.

## Next Steps

To continue verifying and launching this feature:

1. **Manual User Verification**: Open the local web server and verify that the "Recover Spotify" button displays when Simulated/Real errors are thrown, and clicking it correctly triggers `_recoverSpotifySession()`.
2. **Real-device Testing**: Test on a physical mobile device behind Tailscale HTTPS to check if returning from lockscreen triggers auto-recovery correctly.
3. **Refine Timeout Bounds**: If 3000ms or 5000ms is too short/long for slower mobile networks, tune the limit under `_recoverSpotifySession()`.

## Relevant Files

* [resonova/web/player.js](resonova/web/player.js): Contains the state variables, helper methods, bound recovery routine, health gates, and background hook logic.
* [resonova/web/index.html](resonova/web/index.html): Contains the new manual recovery button setup.
* [resonova/web/styles.css](resonova/web/styles.css): Contains the layout wrap updates and specific button design styles.
* [docs/handoffs/Spotify SDK Foreground Recovery Implementation Brief.md](docs/handoffs/Spotify%20SDK%20Foreground%20Recovery%20Implementation%20Brief.md): Requirements and recovery flow specification.
* [docs/handoffs/External Mobile Playback Implementation Audit Report.md](docs/handoffs/External%20Mobile%20Playback%20Implementation%20Audit%20Report.md): Mobile recovery context and guidelines.

## Constraints

* **Do not redesign playback**: Keep the existing player queue, timeline arrays, and history mutations exactly as they are outside of the recovery gates.
* **Do not add polling loops**: No long-running continuous background watchers.
* **Do not touch server tokens**: Do not hardcode or print client secrets or expose credentials anywhere.

## Validation Needed

* Run tests or local server instances to double-check that no console runtime syntax issues exist.
* Manual end-to-end verification of recovery state triggers on the UI.

## Chef Gate Corrections

The initial implementation had three issues found during gate review and corrected before acceptance:

* `_markSpotifyUnhealthy()` now accepts the actual listener reason names (`authentication_error`, `playback_error`) as well as shorthand names, so diagnostics and health gates stay aligned.
* `not_ready` now clears `deviceId`, `lifecycle.ready`, and `lifecycle.deviceId`; recovery should not trust a stale device after the SDK marks it unavailable.
* `index.html` now cache-busts `player.js` with `?v=20260620-spotify-recovery` so mobile browsers fetch the recovery build instead of the previous-control build.

Additional harness validation confirmed:

* `authentication_error` marks auth state unhealthy and shows the recovery button.
* `not_ready` clears the stale device id.
* `_recoverSpotifySession()` can fetch a fresh token, wait for a new device id, transfer playback, clear unhealthy flags, and report healthy state in a simulated foreground recovery.
