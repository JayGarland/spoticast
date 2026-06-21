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
| Chef - Opus 4.8 (Claude env) | 0.83 | Active chef, favored (boss decision 2026-06-21) | Scope control, evidence-based gating, CLI manager routing, diff review, commit discipline, strategy docs, manager query writing | Normal gate; must parse/load-check frontend before accepting |
| Chef - GPT 5.5 (Codex env) | 0.70 | Backup chef, reduced attention (boss decision 2026-06-21) | Chef continuity when Opus 4.8 is unavailable or over budget | Strict gate; use carefully |
| gem-orchestrator / gem-team | 0.82 | Award for diagnosis | Research, baseline validation, document-first analysis, correcting false assumptions | Normal gate; prefer for diagnosis before implementation |
| OCP workspace lead / OCP organization | 0.76 | Stable planner | Strategy, roadmap, audits, organizational briefs | Normal gate; use when output should become repo docs |
| RUG manager | 0.70 | Preferred implementation manager, strict gate | Bounded patches with explicit file limits and acceptance tests | Strict gate; require no broad formatting, no speculative recovery loops, no coding outside task scope |

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
- Owner clarification: not every style diff is a manager mistake; owner may intentionally tune UI values. Chef layer must identify owner edits before reverting or penalizing.

## Updated Routing Rules

1. For unclear playback/mobile failures, assign diagnosis first to `gem-orchestrator`.
2. Assign implementation to `RUG` after the failing layer is named and acceptance evidence is specified; owner currently prefers RUG for implementation tests.
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
| Chef - Opus 4.8 (Claude) | Award (2026-06-21) | First full chef cycle: packet-grounded gating, CLI manager routing, caught a false scope claim, diagnosed and fixed the blank-page regression. Boss raised chef weight. |
| Chef - GPT 5.5 (Codex) | Reduced attention (2026-06-21) | Boss prefers Opus 4.8 as the active chef; Codex moved to backup, lower weight. |

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

## Update 2026-06-21 - Chef-Role Weights

Boss decision (authorized this date, classified `canonical`): the chef role now has two
documented holders, and the boss favors the Claude holder.

- **Chef - Opus 4.8 (Claude env): 0.78 → 0.83 (active, favored).** Basis: first full chef
  cycle on the persistent-memory work — read the onboarding packet before acting, gated each
  slice on independently re-run validation, routed the RUG manager through the Copilot CLI
  (not chat-only), caught a false "Verified" Spotify-scope claim, and diagnosed + fixed the
  blank-page regression live via Chrome MCP. Caveat: one session; the same chef initially
  missed the slice-two JS syntax error in its gate (boss caught it), so this is a normal-gate
  trust level, not high-autonomy. Revisable after more cycles.
- **Chef - GPT 5.5 (Codex env): 0.78 → 0.70 (backup, reduced attention).** Remains available
  for continuity when Opus 4.8 is unavailable or over budget; use carefully under strict gate.

Scope note: this update changes only chef-role weights, per the boss's explicit authorization.
RUG's weight is unchanged here; see `docs/strategy/agent-reviews/2026-06-21-rug-manager-review.md`
for the RUG evidence and a separate (boss-pending) recommendation to nudge RUG 0.70 → ~0.75 for
backend tasks.
