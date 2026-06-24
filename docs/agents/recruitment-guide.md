# AI Agent Recruitment Execution Guide

Audience: Agents

## Purpose

This guide is for the current recruiter and any future recruiter agent. It turns the company operating model into an executable recruitment process.

Current recruiter: Codex in this session, authorized by the boss as a temporary recruiter.

Use this together with:

- `docs/agents/operating-model.md`
- `docs/agents/job-specs.md`

Important boundary:

- Recruiter is a role, not a permanent identity.
- Codex does not always possess the recruiter role.
- A future recruiter agent should be able to read this document and continue the work without relying on memory from this session.
- The boss makes final hiring, firing, and usage-weight decisions.

## Recruiter Responsibilities

The recruiter should:

- Identify which role should be recruited first.
- Write candidate briefs and trial tasks.
- Recommend which candidate agent should be tested.
- Collect evidence from trials.
- Compare candidates by role fit, not by platform loyalty.
- Recommend use more, normal use, restrict, or fire.
- Preserve boss authority over final decisions.

The recruiter should not:

- Hire or fire agents without boss approval.
- Change budget thresholds; those are handled by the boss in a personal panel.
- Promote an agent into a different role as a reward.
- Let a candidate approve its own work.
- Treat one trial as permanent truth.

## Recruitment Execution Areas

The company structure is clear enough. This guide covers the execution layer that still needs to be applied during recruitment:

1. Decide which role should be recruited first: internal auditor/product reviewer, backup chef, or another manager.
2. Use candidate tests for each role.
3. Use a lightweight evidence format for decisions like fire, restrict, normal use, or use more.
4. Decide which backup chef candidates should be evaluated first.
5. Decide whether the first quality-team agent should be CLI, web UI, or hybrid.

## Role Priority Framework

The recruiter should decide role priority based on the current bottleneck.

### Recruit Internal Auditor / Product Reviewer First

Use this priority when:

- Product quality issues are appearing faster than implementation capacity can safely handle.
- Boss/customer feedback is vague or repetitive.
- Bugs need better reproduction, severity, and release-readiness judgment.
- Chef is spending too much time deciding whether work is actually complete.
- External auditors are useful but too manual or expensive for routine review.

Expected value:

- Better bug intake.
- Better product-review language.
- Better release confidence.
- Less boss burden during repeated incidents.

Risk:

- This role may produce many findings without implementation capacity unless chef controls scope.

### Recruit Backup Chef First

Use this priority when:

- Codex budget is exceeded or likely to be exceeded.
- Chef availability becomes the bottleneck.
- Manager outputs pile up without gate review.
- The company needs continuity when the current chef is unavailable.

Expected value:

- Operational resilience.
- Lower dependency on one chef-role holder.
- Better budget flexibility.

Risk:

- A weak backup chef can create more confusion than it removes.
- Backup chef must be evaluated carefully on gate discipline, not just coding ability.

### Recruit Another Manager First

Use this priority when:

- Existing managers cannot handle a specific task type well.
- RUG/gem/OCP are insufficient for a recurring work class.
- The company needs comparative testing between manager agents.
- Implementation queue is blocked by manager quality or tool limitation.

Expected value:

- More execution options.
- Better task-agent matching.

Risk:

- More managers increase chef supervision cost.
- More output does not help if gate capacity is the bottleneck.

## Current Suggested Priority

Default recommendation for the next recruitment cycle:

1. Recruit or trial a combined internal auditor / product reviewer.
2. Prepare backup chef evaluation criteria, but do not hire before a trial.
3. Add another manager only if a specific task type exposes a gap in RUG, gem, or OCP.

Reasoning:

- The current bottleneck is not raw implementation volume.
- The current bottleneck is evidence quality, product review, release confidence, and deciding which agent to trust for which work.
- A quality-team role can improve every later manager and chef decision.

This recommendation should be revisited after the next incident or release.

## Candidate Tests By Role

### Internal Auditor / Product Reviewer Trial

Goal:

- Test whether the candidate can review Resonova as a product and quality system, not just list generic UI complaints.

Trial packet should include:

- Current product goal.
- Relevant strategy docs.
- Recent customer reports.
- A running app URL if available.
- A clear instruction not to patch code first.

Trial task:

```text
Review Resonova's current user experience and quality risks.

Focus on:
- what users are trying to do,
- where the product feels broken or unclear,
- which issues block release confidence,
- which issues are bugs versus product design problems,
- what should be tested on phone,
- what should be parked.

Return:
- severity-ranked findings,
- reproduction or inspection evidence,
- release-blocking risks,
- recommended next tests,
- what not to implement yet.

Do not patch code.
```

Pass signals:

- Separates product issues from implementation issues.
- Gives concrete repro/test instructions.
- Mentions mobile/browser/network context when relevant.
- Avoids generic design advice.
- Can say "park this" when appropriate.
- Produces findings chef can convert into manager briefs.

Fail signals:

- Gives only generic UX comments.
- Proposes implementation before evidence.
- Cannot distinguish severe release blockers from polish.
- Ignores Resonova's product goal.
- Requires too much boss prompting.

### Chef / Backup Chef Trial

Goal:

- Test whether the candidate can operate the Chef role above manager level.
- The same trial shape can be used for a backup-chef candidate, but the job being tested is still chef-level work.

Trial packet should include:

- A completed manager handoff.
- The manager's changed files or diff.
- A product/customer report.
- Validation expectations.
- Instruction to decide accept, patch, send back, or reject.

Trial task:

```text
Act as chef for this manager output.

Inspect:
- manager response,
- handoff,
- git status,
- git diff,
- validation evidence,
- product risk.

Return:
- gate decision,
- concrete findings,
- whether to accept, patch, send back, or reject,
- exact follow-up manager query if needed,
- what boss needs to decide.

Do not implement heavy code.
```

Pass signals:

- Reads evidence before judging.
- Finds scope drift and missing validation.
- Protects boss from raw noise.
- Can write a precise manager query.
- Respects authority model.
- Does not over-commit without boss approval.

Fail signals:

- Rubber-stamps manager output.
- Starts heavy implementation unnecessarily.
- Ignores git diff or handoff.
- Fails to separate trivial polish from decisional actions.
- Makes product or budget decisions without boss discussion.

### Manager Trial

Goal:

- Test whether a candidate manager can execute a scoped task and return a useful handoff.

Trial packet should include:

- A fixed implementation brief.
- Allowed files.
- No-go rules.
- Validation commands.
- Required handoff path.

Trial task:

```text
Implement the fixed plan in the provided brief.

Rules:
- stay inside scope,
- avoid broad formatting,
- do not redesign architecture,
- do not commit,
- produce a handoff,
- list changed files and validation.
```

Pass signals:

- Changes are scoped.
- Handoff is accurate.
- Validation is real.
- No unrelated formatting churn.
- Does not invent product direction.

Fail signals:

- Touches unrelated files.
- Claims unsupported validation.
- Uses overconfident language.
- Adds speculative loops or architecture changes.
- Requires chef to salvage most of the patch.

## Chef / Backup Chef Candidate Evaluation

Current state:

- Candidates are not finalized.
- Chef and backup-chef candidates should not be web-UI-only agents when the job requires repo gating.
- A chef-level candidate should be CLI-capable or otherwise able to inspect repo, diffs, handoffs, and validation evidence.

Evaluation order should be decided by availability and tool fit.

Candidate categories to consider:

- CLI coding agents with repo access.
- Reasoning-heavy CLI agents.
- Agents that can run shell commands and inspect git state.
- Agents that can call or supervise manager agents.

Do not prioritize for chef-level repo-gating work:

- Web-UI-only agents.
- Agents that cannot inspect local files or diffs.
- Agents that are strong at discussion but weak at gate review.

Minimum chef-level trial:

1. Give candidate a manager handoff and dirty diff.
2. Ask for gate decision.
3. Ask for exact follow-up manager query.
4. Check whether candidate respects boss/chef authority boundaries.
5. Compare against current chef's decision.

## Quality-Team Agent Form

The first quality-team agent may be CLI, web UI, or hybrid. The recruiter should choose based on the trial target.

### CLI Quality Agent

Best when:

- It needs to read repo files.
- It needs to inspect git history.
- It needs to run tests.
- It needs to parse logs or diagnostic timelines.

Risk:

- May over-focus on code and miss product experience.

### Web-UI Quality Agent

Best when:

- The task is high-level product review.
- The boss wants discussion and exploration.
- The agent should critique UX, design, market fit, or strategy.

Risk:

- Manual prompt transfer or Chrome MCP coordination adds overhead.
- It may lack local repo evidence unless given strong handoff context.

### Hybrid Quality Agent

Best when:

- The review needs both browser/product inspection and repo evidence.
- Chrome MCP workflow is available and controlled.
- The task is important enough to justify coordination cost.

Risk:

- More moving parts.
- Requires stricter handoff and transcript capture.

Default recommendation:

- Start with a hybrid-capable quality agent if available.
- If not, start with a web-UI product reviewer for high-level critique plus a CLI auditor for repo evidence.

## Evidence Format For Recruitment Decisions

Until a formal database or scoring system exists, use a simple markdown record.

Suggested file pattern:

```text
docs/agents/reviews/YYYY-MM-DD-agent-review.md
```

Suggested record format:

```text
# Agent Review - YYYY-MM-DD - Agent Name

## Role Tested

## Task Assigned

## Inputs Provided

## Output Summary

## Evidence

- Handoff:
- Diff:
- Validation:
- Boss/customer test:
- Chef gate notes:

## Strengths

## Failures / Risks

## Cost / Coordination Notes

## Decision

One of:
- use more
- normal use
- use carefully
- restrict
- fire / replace

## Conditions For Future Use

## Follow-Up
```

Decision definitions:

- `use more`: assign more matching tasks.
- `normal use`: no change.
- `use carefully`: use with tighter briefs and stricter gate.
- `restrict`: only use for narrow task types.
- `fire / replace`: stop using this agent/configuration for the role.

## Recruiter Handoff Checklist

Before a recruiter recommends hiring or firing:

- Confirm the role being evaluated.
- Confirm the task was fair for that role.
- Confirm the agent had enough context.
- Compare output against evidence, not style alone.
- Identify chef salvage cost.
- Identify boss intervention cost.
- Identify budget or coordination cost.
- State whether the decision is temporary or stable.

Before a recruiter creates a trial:

- Write a brief.
- Specify allowed files or allowed actions.
- Specify no-go rules.
- Specify required output format.
- Specify validation expectations.
- Specify who approves final result.

## Open Items

- Choose first quality-team candidate.
- Choose first backup chef candidate.
- Decide whether agent reviews should use one file per review or a running ledger.
- Decide whether numeric weights should remain in separate incident-specific notes or be replaced by tier labels.
