# Agent Performance Weights - 2026-06-19

## Purpose

This note records current trust weights for Resonova manager agents after the mobile playback incident. These weights are operational heuristics, not permanent labels. They should guide which manager receives which kind of task and how strict the gate should be.

## Scoring Model

- `0.90-1.00`: high autonomy, light gate
- `0.75-0.89`: trusted for matching task type, normal gate
- `0.55-0.74`: useful but must be tightly scoped, strict gate
- `<0.55`: do not assign critical work without a narrow checklist and manual review

## Current Weights

| Agent / Role | Weight | Status | Best Use | Gate Requirement |
|---|---:|---|---|---|
| Boss | 1.00 | Owner | Product authority, final approval, real-device testing | Must receive concise decision briefs, not raw noise |
| Codex chef layer | 0.78 | Gatekeeper with probation note | Scope control, diff review, commit discipline, strategy docs, manager query writing | Must inspect manager response, handoff, git status, and git diff before accepting |
| gem-orchestrator / gem-team | 0.82 | Award for diagnosis | Research, baseline validation, document-first analysis, correcting false assumptions | Normal gate; prefer for diagnosis before implementation |
| OCP workspace lead / OCP organization | 0.76 | Stable planner | Strategy, roadmap, audits, organizational briefs | Normal gate; use when output should become repo docs |
| RUG manager | 0.64 | Implementation probation | Bounded patches with explicit file limits and acceptance tests | Strict gate; require no broad formatting, no speculative recovery loops, no coding outside task scope |

## Incident Review

### What Worked

- HTTPS/Tailscale path fixed the real SDK blocker. Mobile now reports `SecureCtx=true`, `Protocol=https:`, `ready=yes`, and a real `device_id`.
- Visible lifecycle diagnostics turned a vague mobile playback complaint into a concrete browser security-context diagnosis.
- Boss real-device testing was decisive. Desktop-only validation would not have found this.
- Git rollback and small commits kept the incident recoverable.

### What Failed

- Early playback-recovery patches attacked symptoms before isolating root cause.
- One manager incorrectly claimed Spotify Web Playback SDK mobile support was impossible.
- RUG produced useful work, but repeatedly introduced excess patch surface such as large CSS formatting churn.
- Chef layer allowed too much implementation momentum before forcing clean diagnosis.

## Updated Routing Rules

1. For unclear playback/mobile failures, assign diagnosis first to `gem-orchestrator`.
2. Assign implementation to `RUG` only after the failing layer is named and acceptance evidence is specified.
3. If RUG touches unrelated files or creates formatting churn, reject the patch and salvage only the minimal logic.
4. Use `OCP` for strategy docs, roadmap, and company operating model work.
5. Chef layer must produce the exact manager query and include file limits, no-go rules, and validation evidence.

## Reward / Penalty Ledger

| Actor | Decision | Reason |
|---|---|---|
| Boss | Award | Persisted through real-device validation and gave precise symptom reports |
| gem-orchestrator / gem-team | Award | Corrected the false mobile-SDK assumption and kept diagnosis focused |
| OCP | Neutral-positive | Good fit for strategy and audit work; not heavily tested in this incident |
| RUG | Penalty with recovery path | Delivered final HTTPS solution, but had prior speculative patches and noisy diffs |
| Codex chef layer | Mild penalty with retained authority | Gatekeeping improved later, but earlier phases should have forced diagnosis sooner |

## Next Technical Gate

Current unresolved issue: mobile lockscreen/background continuity.

Known facts:

- HTTPS and SDK device registration are now fixed.
- Mobile can reach a Spotify segment with a registered device.
- Locking/idling the phone can still interrupt the transition between commentary and music.
- Reopening from idle can show auth failure.

Next manager should not add retries blindly. The next brief must determine whether the failure is:

- browser background suspension,
- token refresh/auth callback state,
- Spotify Connect device handoff after page resume,
- Media Session action handling,
- or an architectural limitation of browser-based interleaving.

