# AI Agent Company Operating Model

Audience: Internal

## Purpose

This document records the current company-level operating model for Resonova's AI-agent workforce. It is a descriptive report for boss review, not a final policy.

The company does not treat a specific platform or model as the permanent holder of a role. A role is fixed by job responsibility; the AI agent assigned to that role can change over time.

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

### Chef

Current holder: Codex in this session. This is not a permanent binding.

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

### Internal Auditor / Quality Team

Status: needed, not fully staffed.

Current staffing:

- The company is still recruiting for this role.
- No specific internal auditor agent has been hired yet.

Potential responsibilities:

- Maintain internal quality review separate from external auditors.
- Review whether fixes are actually complete.
- Build repeatable repro protocols.
- Maintain mobile/browser/network test matrix.
- Interpret diagnostic timelines and customer reports.
- Check release readiness.
- Record regression risks.

### Product Reviewer / Quality Team

Status: needed, not fully staffed.

Current staffing:

- The company is still recruiting for this role.
- No specific product-review agent has been hired yet.
- One quality-team agent may temporarily hold both internal-auditor and product-review responsibilities.

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
- Non-trivial commits, PRs, pipeline changes, release decisions, or other decisional actions require chef-boss discussion first.
- Chef can perform routine commits for validated, scoped work, but should escalate when the work changes product direction, architecture, budget, deployment, or release risk.

This is intentionally similar to an Azure DevOps-style authority model: implementation agents can contribute work, but approval power stays with boss and chef.

## Manager Selection Principle

Chef chooses who handles the work, not based on platform loyalty, but based on role fit and recent performance.

Manager selection is not fixed. It depends on the task, chef's judgment, the manager type, and the current operating context.

Selection factors:

- Task type: implementation, diagnosis, planning, validation, design, product review, documentation.
- Risk: production risk, user-facing risk, architecture risk, budget risk.
- Recent performance: scope control, diff quality, truthfulness, validation quality, usefulness.
- Tool fit: CLI availability, file access, browser access, model capability.
- Cost: API credits, subscription limits, time, manual coordination burden.

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
- Whether Codex remains the active chef for the current period.
- Whether a backup chef should be used when Codex budget is exceeded.

Current chef staffing note:

- Codex is the current chef-role holder.
- The boss wants to consider a backup chef for periods when Codex budget is exceeded.
- Backup chef candidates are not finalized in this document.
- Backup chef candidates should not be web-UI agents.

## Open Questions For Boss Review

- What conditions should trigger an agent review besides incidents and releases?
- Should performance weights be numeric, tier-based, or both?
- Should the chef maintain a running ledger after every manager task, and what exact record format should be used?
- Should internal auditor and product reviewer remain one combined quality-team agent initially, or split later after the quality team is hired?
- Which CLI managers are currently easiest for chef to invoke directly without boss copy-paste?
- Which backup chef candidates should be evaluated first when Codex budget is exceeded?

## Explicit Non-Questions

These are clarified and should not be treated as open blockers:

- Budget thresholds are handled by the boss in a personal panel.
- Chrome MCP workflow is defined outside this document.
- Manager selection weights are not fixed; chef chooses by task, manager type, and context.
