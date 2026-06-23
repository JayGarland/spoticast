# Internal Quality Audit Report — 2026-06-23

Audience: Boss + Chef
Created: 2026-06-23
Status: Internal Quality Audit (audited by Chef; no product code changed, docs-only updates)
Primary Mode: Auditor / Quality Reviewer mode

---

## 1. Summary

This internal audit evaluates the current state of Resonova's product quality, visual layout, and core playback stability following the implementation of the three visual fixes and the resolution of the prior release blockers (blind playback, stale EventSource connections, and memory-off honesty).

**Overall Quality Judgment**:
The overall product stability has improved significantly. The core playback engine is no longer "blind" (it actively samples audio position to confirm active progress), EventSource connections do not leak or hijack the UI, and the memory toggle is functionally honest. The three player card styling bugs (tagline font fallback, toast transparency, and hover color clashes) have been successfully resolved and verified.

**Customer Testing Readiness**:
Resonova is now **ready for broader, owner-driven mobile trials**. There are no longer any critical user-facing blockers (such as playing silence or leaking old states). However, it is **not yet ready for public or multi-user releases** until per-user profile isolation is structurally enforced and the subjective feel of Bounded Stance C is validated via live listening.

---

## 2. Severity-Ranked Findings

Ordered by user/release risk.

| # | Sev | Finding | Evidence | Impact | Recommended next step |
|---|-----|---------|----------|--------|----------------------|
| F1 | **Medium** | **Stance C listening feel is unvalidated on real devices.** Bounded Stance C prompt logic and cache separation are functional, but the actual subjective "feel" of host callbacks is unverified on physical devices with thin vs. rich memory profiles. | `resonova/api/gemini.py:382-411` (`_persistent_memory_guardrail`). | Host narration could feel "creepy" or overly repetitive/dry if the prompt boundary is too narrow or too loose. | **Open Gate.** The boss must perform a live listening test on a real phone with "Personal music narration" toggled ON and verify the 4 safety boundaries. |
| F2 | **Medium** | **Hidden-page Spotify Connect behavior is untested after relaxation.** Commit `dd5c9b1` relaxed the mobile-only hidden-page deferral block in `player.js`. Real-device handoffs on background/lockscreen states need new validation. | `resonova/web/player.js` (omission of mobile Connect deferral logic). | Potential for playback resume failures or SDK disconnects when transitioning segments in background states. | **Verification required.** Execute lockscreen and background tab transition tests on a mobile device. |
| F3 | **Low** | **No automated test coverage for player.js and endpoints.** Verification of the main player loop and server API routes relies entirely on manual phone/browser smoke tests. | `tests/` directory (only `test_profile.py`, `test_tts_failover.py`, and `test_variety_episodes.py` exist). | Minor frontend refactors or JS changes can introduce regressions that slip past manual inspection. | Add a basic endpoint suite (`fastapi.testclient`) and a JS unit harness for player state transition verification. |
| F4 | **Low** | **Windows setup instructions missing in README.** The installation setup instructions for ffmpeg and uv target macOS/homebrew exclusively. | [README.md:38-42](file:///F:/GitHub/resonova/README.md#L38-L42). | New developers or contributors setting up on Windows will hit a missing-ffmpeg error during pydub execution. | Document Windows-specific setup commands (`scoop` or manual environment variable paths). |

---

## 3. Evidence

**Verified Facts (read from source/git/browser):**
* **Blind Playback Fix**: [player.js](file:///F:/GitHub/resonova/resonova/web/player.js#L1325-L1353) now implements a double-sample position check (`rePos - firstPos > 250` over 500ms) inside `_waitForSpotifyPlaybackStart` to ensure music is actually playing before advancing the queue.
* **Stale-SSE Fix**: EventSource connections are closed before opening new ones (`_streamProgress` at line 1460), and `intro_ready` ignores stale messages using a `jobId !== this._activeGenerationId` guard (line 1477).
* **Memory-Off Honesty**: [server.py](file:///F:/GitHub/resonova/resonova/server.py#L661-L666) loads `persistent_profile` for all non-incognito generation requests, enabling the durable-taste vs trail-exclusion logic to run.
* **Card UI Fixes**: Verified that `styles.css` defines `--font-sans`, renders opaque toast backgrounds (`rgba(10, 10, 15, 0.95)`), and uses accent-purple hover borders (`rgba(108, 99, 255, 0.08)`) on `.ep-btn-share:hover`.

**Assumptions / Honest Gaps:**
* Visual and audio transitions under lockscreen/background states are unverified under weak network signals.
* No live multi-user environment exists to test the profile-leak guardrail.

---

## 4. Repro / Inspection Steps

1. **Verify F1 (Stance C toggle)**:
   * Navigate to the app. Toggle **"Personal music narration" OFF** (incognito or memory disabled). Generate a cast and verify that hosts use strict Stance B (fourth-wall intact, no "you").
   * Toggle it **ON**. Generate a cast with a populated history profile. Confirm the host addresses the listener directly ("you") but restricts references strictly to the music domain.
2. **Verify Playback Observability**:
   * Open the browser console. Open diagnostics panel. Click play and verify that the timeline records `play:cmd:ok` followed by active position updates (no `play:start:blind` or silent progression).

---

## 5. Release-Blocking Risks

* **None for owner-driven mobile testing**. The blocker-level playback bugs have been successfully resolved.
* **Critical for public/customer release**:
  * **Per-user Profile Isolation**: Profile storage must be structurally isolated per-user before non-owner customers can connect, preventing personal memory leaks.

---

## 6. Recommended Next Tests

1. **Stance C Listening Test**: Generate a memory-ON cast. Listen to verify that the host narrative tone is natural, avoids creepy jumps, and remains domain-restricted.
2. **Lockscreen Transitions**: Lock the device during a commentary-to-music transition. Verify that playback starts without stalling on resume.

---

## 7. Parked Items
* Consolidating Spotify health booleans into a single state machine (F3 from prior re-audit).
* Adaptive recovery timeouts for low-connectivity networks (F5 from prior re-audit).

---

## 8. Mode Boundary Notes
* This audit was conducted in Auditor mode. No self-review conflict exists as the audited visual fixes were implemented by a RUG manager run and verified independently.
* Detailed browser-level automation was delegated to the `browser` subagent, keeping the Chef focused on scope analysis.

---

## 9. Self-Assessment Against Role Spec
This report satisfies the combined quality role specification:
* Highlights specific code paths and facts rather than making vague claims.
* Order findings strictly by release impact (focusing on unvalidated Stance C and mobile background transitions).
* Respects the code-freeze/freeze-commit boundary during inspection.
