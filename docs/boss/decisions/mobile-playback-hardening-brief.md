# Mobile Playback Hardening Brief

## Current Decision

Do not rush another large playback patch. HTTPS fixed the main mobile Spotify SDK blocker, and owner testing later showed lockscreen playback can work. Treat the remaining problem as intermittent reliability hardening, not an emergency rollback or architecture failure.

Update, 2026-06-19: the owner reproduced a production issue where phone idle/lockscreen playback stops after a while and does not continue. This moves mobile playback hardening from "parked unless reproduced" to "active next implementation candidate."

Update, 2026-06-20: owner retested after the bounded hardening patch and the lockscreen transition problem still persists. The owner also observed that `auth_error` is a separate problem from transition: auth can fail after idle, but active-screen segment transition can still work. This changes the conclusion:

- Token/auth failure should be handled as a user-recoverability issue.
- Lockscreen segment transition is constrained by mobile browser page suspension. If JavaScript timers and Spotify SDK events are frozen while the screen is locked, `setTimeout` and `player_state_changed` cannot reliably advance the queue until the page resumes.
- Do not keep adding background timer patches expecting true locked-screen continuity in the browser architecture.

Next implementation should be small, reversible, and assigned to RUG with strict file limits.

## Immediate Improvement

Add an owner/developer toggle for the Spotify diagnostic panel.

Reason:

- The diagnostic overlay is useful, but it should not always be visible during normal listening.
- The owner needs a fast way to inspect SDK state when testing mobile without changing code.
- This is low-risk UI plumbing and should happen before more playback changes.

Acceptance:

- Diagnostic is hidden by default.
- A visible but unobtrusive control toggles it on/off.
- The setting persists in `localStorage`.
- Existing diagnostic fields and refresh behavior remain unchanged.
- Touch only `resonova/web/player.js` and `resonova/web/styles.css` unless a tiny HTML hook is clearly cleaner.

## Playback Hardening Candidates

Implement now that the owner reproduced lockscreen/idle stopping. Keep the patch small and reversible.

### Phase 1: Token callback fallback

Cache the latest known Spotify token in `player.js`. If `getOAuthToken` cannot fetch while the page is backgrounded, still call Spotify's callback with the cached token.

Why:

- Prevents `cb()` from never being called during page suspension.
- Low risk because the SDK can request a fresh token again if cached token is rejected.

### Phase 2: Fade cap

Reduce background timer damage in `_fadeSpotifyVolume()` by lowering step count when duration is short.

Why:

- A 20-step fade can stretch badly when mobile browsers throttle timers.
- This improves worst-case silence without changing queue structure.

### Phase 3: Spotify segment deadline

Only if stalls are reproduced: add one deadline per Spotify item based on expected duration. This should be a single watchdog, not polling or retry spaghetti.

Why:

- Covers missing `player_state_changed` events during lockscreen/background.
- Higher risk than Phases 1-2 because it can skip music if duration data is wrong, so it needs careful tests.

## Current Active Issue

Boss report:

```text
When the phone is idle or lockscreen a while, playback stops and does not continue.
```

Retest result after `7ab5614 Harden mobile lockscreen playback`:

```text
Lockscreen transition still persists.
auth_error appears to be a separate idle/resume problem.
Active-screen transition is not blocked by the auth_error symptom.
```

Likely target set:

1. Resume-state persistence so an auth failure or reload does not force starting from the beginning.
2. Foreground resume reconciliation on `visibilitychange` / `pageshow`: when the page returns, inspect current state and advance or prompt the owner.
3. Media Session and in-app transport controls for user-driven next/previous/play/pause.
4. Architecture decision for true locked-screen continuity, because browser JS may not run while locked.

Do not implement a general retry loop, polling monitor, or broad lifecycle state machine.

## External Audit Inputs

The external product auditor also found:

- No Media Session API, so lockscreen controls cannot expose next/previous segment.
- Current app UI only has Skip; no in-app play/pause/previous.
- Current queue uses `Array.shift()`, making previous/resume harder.
- Separate data bug: outro writes to shared `generated/outro.mp3`.

Reference: `docs/handoffs/External Product UX Design Audit Handoff.md`

## Parked Work

- Persistent taste/profile memory.
- Thumbs up/down feedback.
- Comparable app research.
- Product vision/roadmap expansion.
- PWA/native app decision.
- Spotify preview URL fallback.
- Full Media Session controls.

## Manager Routing

- Use RUG for the diagnostic toggle.
- Use RUG for small bounded playback hardening phases if owner approves.
- Use gem-orchestrator only for fresh diagnosis when symptoms become contradictory or reproducibility disappears.
- Chef layer must inspect manager response, handoff, `git status`, and `git diff` before accepting.
