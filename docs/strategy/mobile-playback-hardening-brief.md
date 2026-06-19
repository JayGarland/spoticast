# Mobile Playback Hardening Brief

## Current Decision

Do not rush another large playback patch. HTTPS fixed the main mobile Spotify SDK blocker, and owner testing later showed lockscreen playback can work. Treat the remaining problem as intermittent reliability hardening, not an emergency rollback or architecture failure.

Update, 2026-06-19: the owner reproduced a production issue where phone idle/lockscreen playback stops after a while and does not continue. This moves mobile playback hardening from "parked unless reproduced" to "active next implementation candidate."

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

Likely target set:

1. Token callback fallback.
2. Fade-step cap.
3. Carefully bounded Spotify segment deadline only if the implementation can prove it is tied to the current item.

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
