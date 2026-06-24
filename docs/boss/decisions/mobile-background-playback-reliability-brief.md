---
title: "Mobile Background Playback Reliability Brief"
created: 2026-06-19
status: draft
priority: P0
owner_report: "On mobile/background playback, Resonova stops when moving to the next segment; on PC it sometimes needs the tab to be clicked/reactivated."
---

# Mobile Background Playback Reliability Brief

## Purpose

Fix Resonova's core playback reliability before moving to persistent taste profile or feedback features.

The owner validated private phone access through Tailscale, but found a core playback bug:

```text
When Resonova plays in the background on mobile and transitions to the next segment,
the next segment may not start.

On PC, playback sometimes also needs the browser tab to be clicked/reactivated.
```

This affects the main product promise: a hands-free personal radio/cast listening experience.

## Owner Observation

Confirmed user report:

- Mobile phone can access Resonova through Tailscale.
- Phone system media panel appears and controls active Resonova audio.
- During background playback, segment transition can stall.
- On desktop, tab reactivation sometimes nudges playback forward.

This should be treated as a product-blocking playback reliability bug.

## Current Suspected Areas

Initial code inspection points to these risk areas:

- `resonova/web/player.js` depends on `audio.onended` for HTML audio commentary transitions.
- `player.js` depends on Spotify Web Playback SDK `player_state_changed` for Spotify track-end detection.
- `_playNext()` starts the next segment programmatically, which may be blocked or throttled when the page is backgrounded or mobile screen is locked.
- `_playAudio()` catches `audioEl.play()` failure and immediately skips to the next segment, which may hide the real failure mode.
- No Media Session API handlers are currently registered.
- No robust resume/retry path exists for failed programmatic playback.
- No visibility/focus recovery handler exists for stalled playback.

These are hypotheses, not confirmed root causes.

## Scope

In scope:

- Diagnose why next segment playback stalls on mobile/background and sometimes desktop tab inactivity.
- Improve playback transition reliability across:
  - commentary audio -> Spotify track
  - Spotify track -> commentary audio
  - commentary audio -> commentary audio
  - generated live queue transitions
  - replayed saved episode queue transitions
- Add practical recovery behavior when autoplay/programmatic playback is blocked.
- Improve Media Session API support if it helps mobile lock-screen/control-panel behavior.
- Preserve existing queue model and generated episode format unless a minimal compatible extension is clearly needed.
- Add logging or visible diagnostics if useful for owner validation.

Out of scope:

- Persistent taste profile.
- Feedback/rating feature.
- Native mobile app.
- Public deployment.
- Major playback architecture rewrite unless the current architecture is proven unfixable.
- Server-side Spotify audio streaming.
- Full PWA implementation unless a tiny manifest/media-session change is needed for this bug.

## Constraints

- Keep the app single-user and local/private.
- Do not expose secrets or tokens.
- Do not break existing desktop playback.
- Do not break saved episode replay.
- Do not remove Spotify Web Playback SDK support without explicit approval.
- Keep fixes minimal and evidence-backed.
- If browser/mobile autoplay policy prevents a perfect fix, provide the best fallback UX and document the limitation clearly.

## Required Investigation Questions

The manager/team should answer:

1. Which transition stalls: AI commentary -> Spotify, Spotify -> AI commentary, or both?
2. Does the failure happen only when the page is backgrounded/screen locked, or also when visible?
3. Is `audio.onended` firing on mobile background?
4. Is `audioEl.play()` rejecting with `NotAllowedError`, `AbortError`, or another error?
5. Is the Spotify SDK available/reliable in the tested mobile browser?
6. Does Media Session API state/action handling improve system control behavior?
7. Does a user-gesture "unlock audio session" need to be added before playback starts?
8. Can stalled playback recover on `visibilitychange`, `focus`, `pageshow`, or a retry button?

## Acceptance Criteria

The fix is acceptable when:

- Existing episode replay can progress across multiple segments without needing tab reactivation while the page is visible.
- Mobile/background behavior is improved and tested by the owner.
- If lock-screen autoplay cannot be fully guaranteed, the app surfaces a clear resume/retry state instead of silently stalling.
- `audioEl.play()` failures are not silently skipped without recording useful diagnostics.
- Media Session metadata/control behavior is improved or explicitly documented as unsupported.
- The handoff clearly states what was fixed, what remains browser-policy-limited, and how the owner should test.

## Expected Deliverable

Produce a handoff under:

```text
docs/handoffs/
```

Suggested filename:

```text
Mobile Background Playback Reliability Handoff.md
```

The handoff should include:

- Root-cause findings.
- Files changed.
- Playback transitions tested.
- Commands/run steps.
- Owner mobile validation steps.
- Remaining limitations.
- Candidate follow-ups.

## Recommended Manager Routing

Preferred manager:

```text
RUG
```

Reason: this is now a concrete bug/fix loop. It needs implementation plus independent validation, and may require repeat-until-good behavior.

Alternative:

```text
gem-orchestrator
```

Use gem-team if a durable plan and browser-tester/reviewer wave is preferred.

Avoid OCP for the first fix attempt unless the task is reframed as diagnosis-only. OCP was useful for bounded audits, but this bug needs active debugging and correction.

## Suggested Prompt To Paste Into RUG

```text
Use docs/boss/decisions/mobile-background-playback-reliability-brief.md as the parent objective and scope.

Fix Resonova's playback reliability bug:
- On mobile/background playback, Resonova can stop when transitioning to the next segment.
- On desktop, playback sometimes needs the tab to be clicked/reactivated before continuing.

This is a P0 product bug. Resolve it before persistent profile or feedback work.

Preserve these constraints:
- Keep the app single-user and private.
- Do not expose secrets or tokens.
- Do not break existing desktop playback.
- Do not break saved episode replay.
- Do not remove Spotify Web Playback SDK support without explicit approval.
- Keep the fix minimal and evidence-backed.

Investigate and fix:
- HTML audio commentary segment transitions.
- Spotify Web Playback SDK track transitions.
- programmatic play failures when backgrounded or inactive.
- missing retry/resume behavior.
- Media Session API support for mobile system controls if useful.

Expected deliverable:
- Implement the minimal reliable fix.
- Produce docs/handoffs/Mobile Background Playback Reliability Handoff.md.
- Include root cause, files changed, validation steps, remaining browser-policy limitations, and exact owner mobile test steps.

Do not start persistent profile, feedback, native app, or public deployment work.
```
