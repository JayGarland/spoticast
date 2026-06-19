# Mobile Playback Hardening Brief

## Current Decision

Do not rush another large playback patch. HTTPS fixed the main mobile Spotify SDK blocker, and owner testing later showed lockscreen playback can work. Treat the remaining problem as intermittent reliability hardening, not an emergency rollback or architecture failure.

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

Implement only after the diagnostic toggle, and only if the owner can reproduce interruption again.

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

