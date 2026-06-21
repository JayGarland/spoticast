# Resonova Agent Orientation

Audience: Agents

## Read First

Before doing company-role, recruitment, manager, auditor, or chef-level work, read:

- `docs/strategy/ai-agent-company-operating-model.md`
- `docs/strategy/ai-agent-role-job-specs.md`
- `docs/strategy/ai-agent-recruitment-execution-guide.md`
- `docs/strategy/boss-profile.md`

Study the boss profile before planning. Agents should understand the boss's authority, habits, preferences, and tolerance for documentation before deciding how to respond.

When reviewing agent performance, also read:

- `docs/strategy/agent-performance-weights-2026-06-19.md`

## Operating Rules

- Boss/CEO and chef hold approval authority for commits, PRs, pipelines, and accepted agent work.
- Manager, worker, auditor, reviewer, and recruiter agents must not approve their own work.
- Non-trivial product, architecture, budget, release, PR, or pipeline decisions require chef-boss discussion.
- Manager-level work currently requires a work handoff.
- Handoffs should explain what changed, what was validated, remaining risks, and what the next agent needs to know.
- Avoid over-documenting. Prefer short decision records, job specs, briefs, and handoffs over large process manuals.
- Chef has standing authorization to commit validated scoped work inside an approved task; non-trivial product, architecture, budget, release, PR, or pipeline changes require chef-boss discussion first.
- When multiple agents or workstreams run at the same time, use separate branches or isolated worktrees where possible, and route parallel implementation work through PR or PR-like review before merge.
- Agents may use available MCP/server tools, including Chrome MCP or browser tools, when useful for inspection, validation, web-UI coordination, or evidence gathering. Tool use must stay inside role authority and task scope.

## Default Behavior

If the requested work is unclear, read the relevant strategy docs before asking questions. If the work changes authority, company roles, recruitment, quality process, or delivery risk, treat it as non-trivial and escalate to boss/chef discussion.
