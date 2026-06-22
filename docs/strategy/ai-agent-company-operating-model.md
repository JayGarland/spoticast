# AI Agent Company Operating Model

Audience: Internal

## Purpose

This document records the current company-level operating model for Resonova's AI-agent workforce. It is the current living operating policy for agent work, and it should be updated as the boss changes staffing, authority, or workflow decisions.

The company does not treat a specific platform or model as the permanent holder of a role. A role is fixed by job responsibility; the AI agent assigned to that role can change over time.

Agents do not need to care whether a role holder comes from Codex, Claude, Gemini, another CLI, or another model/vendor. Agents should care about the role, authority, tool access, evidence quality, and current assignment.

Tool form still matters:

- Workspace/CLI-capable agents can inspect the local repo, git state, diffs, handoffs, tests, and local files directly.
- Web-UI agents may be useful for higher-level discussion, product thinking, review, or specialist critique, but they normally need supplied context or Chrome/MCP-style coordination because they do not automatically have local repo access.
- Agents may use available MCP/server tools, including Chrome MCP or browser tools, when they support inspection, validation, web-UI coordination, or evidence gathering. Tool access does not change role authority: managers, auditors, reviewers, recruiters, and specialists still do not self-approve work.

## Current Company Roles

### Boss / CEO

Current holder: the user.

Responsibilities:

- Own product direction, final priority, budget, and final approval.
- Provide vague or high-level goals when appropriate.
- Inspect outcomes and decide whether work is acceptable.
- Run periodic agent performance review meetings.
- Decide which agents are used more, used carefully, or fired.
- Provide or collect real customer and boss testing feedback.

Notes:

- The boss has limited time, energy, and memory, so agent work should reduce cognitive load.
- The boss should receive concise decision briefs, not raw implementation noise.
- The boss controls budget for API credits, subscriptions, and agent usage. No agent is free.
- Agents should read `docs/strategy/boss-profile.md` when doing boss-facing, company-role, recruitment, manager, auditor, or chef-level work.

### Chef

Current holder: the active chef-role agent chosen by the boss. This is a role assignment, not a platform or model identity.

Responsibilities:

- Discuss goals with the boss and turn vague goals into fixed, executable plans.
- Decide which manager agent should receive a task.
- Select the manager agent and, when applicable, the model or mode to use.
- Demand manager implementation through CLI where possible, so the boss does not depend only on manual copy-paste into VS Code.
- Supervise manager work through CLI output, handoff files, git diff, and validation evidence.
- Review manager performance and report evidence to the boss for review meetings.
- Perform small polishing, correction, finalization, cleanup, and commit-boundary work after manager returns.
- Maintain git hygiene, handoff records, and release checkpoints.

Boundary:

- Chef should not normally perform deep or heavy implementation when a manager can be tested for that work.
- Chef may do scout/discovery, codebase reading, diagnosis, small fixes, gate corrections, and final polish.
- Chef does not need to care how many subagents a manager has or how the manager internally delegates work.
- Chef evaluates the manager result, not the manager's internal org chart.

Required gate behavior:

- Inspect manager response.
- Inspect manager handoff.
- Inspect `git status`.
- Inspect `git diff`.
- Run relevant validation.
- Decide accept, patch, send back, or reject.
- Commit accepted validated updates when appropriate.

Authority:

- Chef may create commits when work has been validated and is inside the agreed scope.
- Chef may prepare or create PRs and pipeline changes only under the company's authority model.
- Chef must discuss non-trivial or decisional actions with the boss before acting.
- Chef must not let manager agents approve their own work.

## Specialized Chef Policy

Current default: one active chef plus specialist agents is sufficient for now. Specialized chefs should be added only when the company has evidence that one general chef is becoming a real bottleneck or risk.

Add a specialized chef only if one of these becomes true:

- Active chef becomes the bottleneck for multiple parallel workstreams.
- Product strategy and technical delivery conflict too often.
- Boss receives too much raw noise again.
- Chef repeatedly misses product or UX risks.
- Codex budget or availability becomes painful.
- Manager or auditor outputs pile up ungated.

Possible future specialized chefs:

- Technical Chef / CTO Chef: codebase, architecture, commits, PRs, and managers.
- Product Chef / CPO Chef: roadmap, UX, positioning, market benchmark, and product reviews.
- Quality / Release Chef: release gates, QA matrix, regression risk, and customer readiness.
- Recruiter / People Ops Chef: agent hiring, firing, restrictions, and performance review.

### Manager

Current manager pool:

- RUG manager: `C:\Users\Administrator\.copilot\installed-plugins\awesome-copilot\rug-agentic-workflow\agents\rug-orchestrator.md`
- gem-team leader: `C:\Users\Administrator\.copilot\agents\gem-orchestrator.agent.md`
- OCP organization leader: `C:\Users\Administrator\AppData\Roaming\Code\User\prompts\OCP Workspace Lead.agent.md`

Responsibilities:

- Receive a fixed plan or scoped brief from chef.
- Implement or coordinate implementation.
- Return a handoff file with changed files, validation, risks, and test instructions.
- Stay inside scope.
- Avoid broad formatting churn, speculative rewrites, and unapproved architecture changes.

Boundary:

- The manager role is fixed, but the agent occupying the role is replaceable.
- The company does not need to inspect manager subagents as part of normal chef workflow.
- The manager is not promoted to another role as a reward.
- Reward means the company uses that manager more often or gives it better-matched tasks.
- Punishment means the company uses that manager less, restricts it to safer tasks, or fires/replaces it.
- Managers do not have approval authority over commits, PRs, or pipelines.
- Managers may propose changes and produce handoffs, but chef or boss must approve accepted work.

### External Auditor / Inspector

Current holder: invited case by case through handoff files and/or web UI.

Responsibilities:

- Independently inspect product, codebase, UX, design, backend, frontend, architecture, or incident history.
- Challenge chef and manager conclusions.
- Provide findings before implementation when the failure class is unclear.
- Use workspace paths, git history, app URLs, Chrome MCP/browser inspection, and handoff docs where available.

Boundary:

- External auditor should not patch first unless explicitly assigned.
- External auditor is especially useful for high-risk areas: mobile playback, Spotify SDK lifecycle, UX/design, architecture, product roadmap, and company process.

### Quality Team — Combined Role (decided 2026-06-21)

The internal auditor, investigator, and product reviewer are **one combined quality role** for
now: `Internal Auditor / Investigator / Product Reviewer`. Do not split into separate hires yet —
that adds staffing and coordination cost before we have the volume.

Every quality brief must name a **primary mode**:

- **Product Reviewer mode** — UX, product value, user journey, release trust, positioning mismatch.
- **Investigator mode** — root cause, evidence trail, repro, logs, code/doc contradictions (within
  quality review; does not replace `gem-orchestrator` diagnostic implementation-prep).
- **Auditor mode** — gate completeness, risk ranking, whether work is acceptable, missing validation.

Rules:

- One primary mode per brief; the agent may still flag cross-mode findings.
- The no-self-approval rule applies **across modes**: in Auditor mode the agent must not gate work
  it itself produced or strongly recommended in a prior Investigator/Reviewer brief.

Split into separate roles only if: product UX review and technical investigation conflict too
often; one agent is strong at product judgment but weak at evidence/root cause (or vice versa);
quality outputs pile up faster than chef can gate; release readiness becomes a recurring separate
workload; or a single brief routinely needs two modes at once.

The two sections below describe the responsibilities that map onto these modes.

### Internal Auditor / Quality Team

Status: trialed; use carefully as inspect-only quality reviewer.

Current staffing:

- One internal auditor / product reviewer has completed a trial and is approved for inspect-only use under chef gate.
- The role is not yet fully staffed or autonomous.
- Reference: `docs/handoffs/Internal Auditor Product Reviewer Trial Chef Gate.md`.

Potential responsibilities:

- Maintain internal quality review separate from external auditors.
- Review whether fixes are actually complete.
- Build repeatable repro protocols.
- Maintain mobile/browser/network test matrix.
- Interpret diagnostic timelines and customer reports.
- Check release readiness.
- Record regression risks.

### Product Reviewer / Quality Team

Status: trialed; use carefully as inspect-only product reviewer.

Current staffing:

- The current trialed quality-team agent may temporarily hold both internal-auditor and product-review responsibilities.
- The role is not yet fully staffed or autonomous.
- Reference: `docs/handoffs/Internal Auditor Product Reviewer Trial Chef Gate.md`.

Potential responsibilities:

- Review product experience, user flows, visual clarity, and feature value.
- Translate customer discomfort into product-quality findings.
- Inspect whether UI behavior matches Resonova's product goal.
- Review frontend experience separately from implementation correctness.
- Help identify when a bug is actually a product design issue.

## Current Workflow

1. Boss raises a goal, concern, customer report, or company-level question.
2. Chef discusses with boss if needed and forms a fixed plan or brief.
3. Chef selects the manager agent and model/mode for the work.
4. Chef invokes or instructs the manager through CLI when possible.
5. Manager implements or investigates and returns a handoff.
6. Chef gates the result by reading response, handoff, git status, git diff, and validation.
7. Chef may polish, correct, or finalize small issues.
8. Boss tests or reviews when real product judgment is required.
9. Accepted updates are committed.
10. Agent performance evidence is recorded for later review meetings.

## Handoff Policy

All agents should leave enough context for a future agent or future instance to continue the work. The future agent may be the same agent in a new session, another instance, or a different AI agent entirely.

This does not mean every role writes a company-level handoff after every task.

Current rules:

- Manager-level work currently requires a work handoff.
- The handoff should explain what changed, what was validated, what risks remain, and what the next agent needs to know.
- Chef reviews manager handoff before accepting the work.
- Company-level role handoffs should be rare and lightweight.
- Company-level handoffs are appropriate for role transition, major policy change, recruitment decision, incident review, or release review.
- Routine tasks should not create over-engineered company-role handoffs.

The default handoff is a work handoff, not a company bureaucracy artifact.

## Documentation Principle

Resonova should borrow GitLab-style handbook principles, not GitLab-scale documentation.

Current rules:

- Avoid over-documenting.
- Write docs when they reduce future confusion, support handoff, record authority, or preserve decisions.
- Prefer short decision records, job specs, briefs, and handoffs over large process manuals.
- Keep documentation useful for the next boss, chef, agent, auditor, or customer who needs it.

Audience labels:

- `Audience: Agents` for manager briefs, handoffs, role specs, and implementation guides.
- `Audience: Boss` for decision briefs, review summaries, and recruitment recommendations.
- `Audience: Customer` for user-facing guides, onboarding, support, and release notes.
- `Audience: Internal` for docs shared by boss, chef, agents, and auditors.

Historical docs do not need a bulk audience-label update. Existing handoffs remain implicitly agent-facing unless revisited. Future docs should include an audience line when it helps avoid confusion.

## Source Control And Delivery Authority

Current authority holders:

- Boss / CEO.
- Chef.

Allowed authority:

- Create commits.
- Approve or reject agent work.
- Create PRs.
- Approve PRs from agents.
- Create or change pipelines.
- Decide whether manager output enters the product.

Restrictions:

- Manager agents, worker agents, auditors, and reviewers do not self-approve product changes.
- Chef has standing authorization to create routine commits for validated, scoped work inside an approved task.
- Non-trivial commits, PRs, pipeline changes, release decisions, or other decisional actions require chef-boss discussion first.
- Chef should escalate when the work changes product direction, architecture, budget, deployment, or release risk.

This is intentionally similar to an Azure DevOps-style authority model: implementation agents can contribute work, but approval power stays with boss and chef.

## Parallel Agent Branch And PR Policy

Single scoped work can be committed directly by chef after validation when it stays inside an approved task.

When multiple agents or workstreams operate at the same time:

- Use a separate branch or isolated worktree for each agent/workstream where possible.
- Prefer PR or PR-like review packets for parallel implementation work before merge.
- Managers, workers, auditors, reviewers, recruiters, and specialists must not approve or merge their own work.
- Chef gates each branch or PR by inspecting the agent response, handoff, git status, git diff, and validation evidence.
- Boss review is required before merging non-trivial product, architecture, budget, release, PR, or pipeline changes.
- If two agents touch overlapping files or behavior, chef should sequence the work and resolve the conflict before merge.
- If a branch/worktree is not practical, the agent brief must state why and define stricter file boundaries and handoff requirements.

## Manager Selection Principle

Chef chooses who handles the work, not based on platform loyalty, but based on role fit and recent performance.

Manager selection is not fixed. It depends on the task, chef's judgment, the manager type, and the current operating context.

Selection factors:

- Task type: implementation, diagnosis, planning, validation, design, product review, documentation.
- Risk: production risk, user-facing risk, architecture risk, budget risk.
- Recent performance: scope control, diff quality, truthfulness, validation quality, usefulness.
- Tool fit: CLI availability, file access, browser access, model capability.
- Cost: API credits, subscription limits, time, manual coordination burden.

Current boss preference, 2026-06-22:

- For severe implementation regressions delegated to an external manager, use `deepseek-v4-pro` when that manager runtime supports explicit model selection.
- If the active runtime does not expose `deepseek-v4-pro`, chef should say so clearly and proceed with the best available manager path rather than blocking an urgent fix.

## Performance Review Meeting

The company should periodically review agents, but not too often. The purpose is to update usage weights and management rules.

Current trigger:

- Boss triggers and organizes the review meeting manually.
- For now, reviews happen after an incident, release, or other meaningful checkpoint.
- Later, this review process may be handed to an auditor or quality-team role and run on a schedule.

Review subjects:

- Chef role holder.
- Each manager agent.
- External auditors used during the period.
- Internal quality/product reviewers when hired.
- Specialist agents when used.

Review evidence:

- Completed tasks.
- Failed tasks.
- Handoff quality.
- Diff quality.
- Validation quality.
- Scope discipline.
- Whether boss had to intervene.
- Whether chef had to salvage output.
- Whether customer/boss testing confirmed the result.
- Budget/cost consumed.

Possible decisions:

- Increase usage frequency.
- Keep normal usage.
- Use only under strict scope.
- Use only for certain task types.
- Require external audit before accepting.
- Stop assigning critical work.
- Fire or replace the agent/agent configuration.

Current scoring position:

- The company does not yet have a formal scoring standard, rating system, or database.
- Numeric scores can be useful as rough heuristics, but should not pretend to be objective precision.
- Until a scoring system exists, review output should focus on practical routing decisions: use more, use normally, use carefully, restrict, or fire.

## Current Known Manager Notes

### Manager Model Selection (budget, 2026-06-22)

Boss direction: prefer a cheaper model for manager runs to control budget — target DeepSeek
(`deepseek-v4-pro`).

Finding (verified): DeepSeek is **not** in the Copilot CLI's built-in model routing —
`--model deepseek-v4-pro` and all `deepseek*` variants return "not available." The only path is
**BYOK (Bring Your Own Key)** via environment variables:

- `COPILOT_PROVIDER_BASE_URL` = DeepSeek's OpenAI-compatible endpoint (e.g. `https://api.deepseek.com`)
- `COPILOT_PROVIDER_TYPE` = `openai`
- `COPILOT_PROVIDER_API_KEY` = the boss's DeepSeek API key
- `COPILOT_MODEL` = the model name DeepSeek's API expects (confirm whether `deepseek-v4-pro` is a
  valid API model; otherwise `deepseek-chat` / `deepseek-reasoner`)
- optional `COPILOT_PROVIDER_MODEL_ID` = a well-known base id so tool-support/token-limit config applies.

Boundaries:

- The **boss must set the API key** — agents do not enter API keys.
- BYOK replaces Copilot routing for that session; RUG's orchestration/tool-calling was tuned for
  Copilot models, so **test DeepSeek on a small task before relying on it** for real implementation.
- Once the env is configured, invoke RUG normally:
  `copilot --agent rug-agentic-workflow:rug-orchestrator --allow-all -C <repo>` (the BYOK env vars
  select the model).

Making it persistent (no per-run wrapper — so future chef instances just inherit it):

The CLI reads BYOK config from environment variables ONLY — there is no config-file or key-file
setting, and it does NOT read a project `.env` (Resonova's `.env` is read by the Python app, not by
`copilot`). To avoid a per-run wrapper, set the vars once as **persistent Windows user environment
variables**:

```
setx COPILOT_PROVIDER_BASE_URL "https://api.deepseek.com"
setx COPILOT_PROVIDER_TYPE "openai"
setx COPILOT_MODEL "deepseek-chat"            # or deepseek-v4-pro if your account exposes it
setx COPILOT_PROVIDER_API_KEY "<your key>"    # boss runs this one
```

After that, any `copilot` run uses DeepSeek with no wrapper. Caveats: this makes DeepSeek the model
for ALL Copilot CLI usage (BYOK disables GitHub routing) — to revert, clear these vars; and do NOT
set `COPILOT_PROVIDER_BASE_URL` persistently before the key is in place, or copilot runs fail auth.

Scoped alternative (DeepSeek for ONE run only, leaves global Copilot routing intact):
`scripts/run-rug-deepseek.ps1` sets the vars in-process and invokes RUG.

Setup status (2026-06-22): the boss has **completed** the persistent BYOK setup — DeepSeek is now
the active model for the Copilot CLI, so manager runs use DeepSeek with no wrapper. Confirm the
exact `COPILOT_MODEL` value works on a small task before a real build.

### Candidate Manager — reasonix (cost-efficient DeepSeek, long-running)

Boss-referenced: `https://github.com/esengine/deepseek-reasonix` — a Go terminal coding agent built
for long-running sessions, kept cheap via **prefix-cache stability** (high DeepSeek cache-hit rate).
Config-driven (`reasonix.toml`), multi-model (planner/executor in isolated cache sessions),
MCP-compatible plugins, any OpenAI-compatible endpoint, `npm i -g reasonix`.

Chef note: a credible **second manager option** for budget-sensitive / long-running implementation
on DeepSeek, and its cache-stability technique is directly relevant to the deep-research generation
mode's cost problem (`deep-research-generation-mode-brief.md`). Evaluate with a small trial before
routing real work — not yet adopted; RUG remains the primary manager.

### RUG Manager

Observed strengths:

- Useful for bounded implementation tasks.
- Can produce working patches and handoff files.
- Good target when chef provides strict file limits and acceptance tests.

Observed risks:

- Needs strict gate.
- Has produced noisy diffs and formatting churn.
- Can be overconfident in handoff language.
- Should not receive vague architecture or product direction without a precise brief.

Current operational rule:

- Use for implementation after chef defines the failing layer and acceptance evidence.
- Require strict gate before commit.
- For the moment, chef mainly uses RUG for manager-level implementation work.

### gem-team / gem-orchestrator

Observed strengths from existing notes:

- Useful for diagnosis, research, baseline validation, and correcting false assumptions.
- Better fit before implementation when the failure class is unclear.

Current operational rule:

- Prefer for diagnostic/research work before assigning implementation.

### OCP Organization / OCP Workspace Lead

Observed strengths from existing notes:

- Fit for strategy, roadmap, audit, organization, and document-first work.

Current operational rule:

- Prefer for company operating model, strategy docs, roadmap, and organizational briefs.

## Budget Note

Agent usage consumes boss-controlled budget through API credits, subscriptions, compute, time, and coordination effort.

Budget should influence:

- How many agents are involved in a task.
- Whether an external auditor is justified.
- Whether to use a web UI discussion or a CLI worker.
- Whether repeated failure should lead to firing/replacement.
- Which model tier is used for a manager task.
- Which provider/model is used for product research, script writing, and TTS.
- Whether a full cast generation is justified for a test, or whether cached/partial/offline validation is enough.
- Whether the active chef-role holder remains the right fit for the current period.
- Whether a backup chef should be used when the active chef is unavailable, over budget, or not the best fit.

## Budget And Model Resource Policy

Resonova should prepare fallback and optional models for budget control. This applies to both product generation and agent labor.

Product generation cost concern:

- A roughly 10-song cast generation currently costs about 0.6 EUR end to end after research, script writing, and voice synthesis.
- This cost is acceptable for owner testing but can become a problem when usage increases, when customer testing begins, or when experimental tests repeatedly trigger full generation.
- Future features that add larger context, richer memory/profile injection, or more prompt material may increase text-generation and TTS cost.
- Tests should avoid full paid generation when a cheaper validation path is enough: cached fixtures, partial generation, offline inspection, one-track smoke tests, or mocked/cached research.

Model fallback domains to maintain:

- Research model: keep a cheaper fallback for grounded/background research where quality loss is acceptable.
- Script-writing model: keep at least one lower-cost text-generation option for drafts, experiments, and non-production tests.
- TTS model: keep fallback or optional TTS providers/models because voice synthesis is a recurring cost driver and can block the whole generation flow.

Current candidate options and preferences:

- `deepseek-v4-pro` is a boss-named candidate for text generation and manager-agent work when the runtime supports explicit model selection.
- For development manager-agent work, prefer DeepSeek or another cheaper capable model as the primary choice or at least an available option when quality is sufficient.
- The current integrated Copilot-manager path may consume the boss's personal Copilot Pro+ subscription/credits, so it should not be treated as free infrastructure.
- Cheaper Chinese models may be acceptable for dev, trials, manager implementation, research drafts, or non-production exploration if they preserve enough evidence quality and scope discipline.

Guardrails:

- Do not change production model/provider defaults solely for cost without boss-chef discussion.
- Do not assume a cheaper model is acceptable for release-facing script quality or TTS quality without A/B evidence.
- Record model/provider used in expensive trials, manager reviews, or generation-cost investigations when practical.
- Budget thresholds remain private to the boss; agents may flag cost pressure but must not invent hard thresholds.

Current chef staffing note:

- The active chef-role holder is chosen by the boss and may change over time.
- The boss wants to consider a backup chef for periods when the active chef is unavailable, over budget, or not the best fit.
- Backup chef candidates are not finalized in this document.
- Backup chef candidates should not be web-UI agents.

## Open Questions For Boss Review

- What conditions should trigger an agent review besides incidents and releases?
- Should performance weights be numeric, tier-based, or both?
- Should the chef maintain a running ledger after every manager task, and what exact record format should be used?
- (Resolved 2026-06-21) Quality team stays one combined role — `Internal Auditor / Investigator / Product Reviewer` — with each brief naming a primary mode (Product Reviewer / Investigator / Auditor); split only on the listed triggers. See the "Quality Team — Combined Role" section.
- Which CLI managers are currently easiest for chef to invoke directly without boss copy-paste?
- Which backup chef candidates should be evaluated first when Codex budget is exceeded?

## Explicit Non-Questions

These are clarified and should not be treated as open blockers:

- Budget thresholds are handled by the boss in a personal panel.
- Chrome MCP workflow is defined outside this document.
- Manager selection weights are not fixed; chef chooses by task, manager type, and context.
