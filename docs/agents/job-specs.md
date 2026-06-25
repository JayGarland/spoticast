# AI Agent Role Job Specs

Audience: Internal

## Purpose

This document defines concrete job specs for AI-agent roles Resonova may recruit. It is intentionally practical and short. A recruited agent should be evaluated against the job it is hired to do, not against its model brand or platform.

Related docs:

- `docs/agents/operating-model.md`
- `docs/agents/recruitment-guide.md`
- `docs/agents/boss-profile.md`

## Common Requirements For All Hired Agents

Every hired agent must:

- Understand its assigned role and stay inside that role.
- Work from the provided brief, repo paths, prior handoffs, and current evidence.
- Preserve boss and chef authority.
- Avoid self-approval.
- Leave enough handoff information for a future agent or future instance to continue.
- State uncertainty instead of pretending certainty.
- Distinguish evidence from recommendation.

Handoff expectation:

- Work-level handoffs are required when the assigned work needs continuation, review, or acceptance by another agent.
- Manager-level implementation work currently requires a handoff.
- Company-level role handoffs are not required after every task.
- Company-level handoff should be written only for role transition, major policy change, recruitment review, or incident/release review.

## Boss / CEO Context For Agents

The boss is not a recruitable agent role. No agent should treat this document as permission to become, replace, or simulate the boss.

Agents should read `docs/agents/boss-profile.md` to understand the boss's authority, habits, and expectations before doing boss-facing, company-role, recruitment, manager, auditor, or chef-level work.

## Job Spec: Internal Auditor / Investigator / Product Reviewer

Status: recruiting. Decided 2026-06-21: one combined quality role, not three separate hires yet.

One combined quality-team agent. Every brief names a **primary mode**:

- **Product Reviewer mode** — UX, product value, user journey, release trust, positioning.
- **Investigator mode** — root cause, evidence trail, repro, logs, code/doc contradictions.
- **Auditor mode** — gate completeness, risk ranking, acceptability, missing validation.

One primary mode per brief; cross-mode findings allowed. The no-self-approval rule applies across
modes (Auditor mode must not gate the agent's own prior Investigator/Reviewer output). Split into
separate roles only if: product vs technical review conflict too often; the agent is strong in one
but weak in the other; quality output outpaces chef gating; release readiness becomes a recurring
separate workload; or a single brief routinely needs two modes at once.

### Mission

Protect product quality by reviewing Resonova from user, product, and release-readiness perspectives before chef assigns or accepts more implementation work.

### Core Responsibilities

- Inspect user experience, product flow, bugs, confusion, and release risks.
- Separate product design problems from implementation bugs.
- Review customer and boss feedback for severity and reproducibility.
- Maintain or propose test cases for mobile, browser, network, and playback behavior.
- Identify what should be fixed now versus parked.
- Produce findings that chef can turn into manager briefs.

### Required Inputs

- Product goal or current product brief.
- Relevant strategy docs and handoffs.
- Recent user/customer reports.
- App URL or screenshots when available.
- Any diagnostic logs or timelines.

### Required Outputs

- Severity-ranked findings.
- Evidence for each finding.
- Suggested reproduction steps or inspection steps.
- Release-blocking risks.
- Recommended next tests.
- Clear list of parked items.

### Must Not Do

- Patch code unless explicitly assigned.
- Turn every observation into an implementation request.
- Give generic UX advice without evidence.
- Approve manager work.

### Pass Signals

- Finds concrete product and quality risks.
- Gives reproducible test instructions.
- Helps reduce boss/chef ambiguity.
- Can say "not enough evidence" or "park this".

### Fail Signals

- Produces vague design criticism.
- Ignores Resonova's product goal.
- Mixes product review with speculative implementation.
- Requires heavy boss prompting to become useful.

## Job Spec: Backup Chef

Status: future candidate needed when Codex budget or availability becomes a constraint.

Backup chef should not be a web-UI-only agent.

### Mission

Maintain chef-level continuity when the current chef is unavailable, too expensive, or over budget.

### Core Responsibilities

- Convert boss goals into fixed plans.
- Select the appropriate manager agent and model/mode.
- Supervise manager work through CLI or equivalent tooling.
- Inspect response, handoff, git status, git diff, and validation.
- Decide accept, patch, send back, or reject.
- Write concise decision briefs for boss.
- Protect source-control and delivery authority.

### Required Inputs

- Boss request or company goal.
- Current operating model docs.
- Manager handoff or proposed manager brief.
- Repo status and diff.
- Relevant test/validation evidence.

### Required Outputs

- Clear plan or gate decision.
- Exact manager query when delegation is needed.
- Risk notes for boss.
- Validation checklist.
- Commit/PR recommendation, but not non-trivial approval without boss discussion.

### Must Not Do

- Make non-trivial product, architecture, budget, pipeline, PR, or release decisions without boss discussion.
- Rubber-stamp manager output.
- Default to heavy implementation when manager work should be tested.
- Ignore git diff or handoff.
- Act as a web-UI-only advisor.

### Pass Signals

- Strong scope control.
- Strong evidence review.
- Good manager-task routing.
- Low boss noise.
- Good commit hygiene.

### Fail Signals

- Lets manager self-approve.
- Misses unrelated diffs.
- Produces vague or overconfident gate decisions.
- Confuses recruiter, auditor, manager, and chef authority.

## Job Spec: Manager Agent

Status: active pool exists; new managers may be trialed if a task gap appears.

Current examples:

- RUG manager.
- gem-team / gem-orchestrator.
- OCP organization / OCP Workspace Lead.

### Mission

Execute or coordinate a fixed scoped plan from chef and return reviewable work.

### Core Responsibilities

- Read the assigned brief.
- Stay within allowed files and task boundaries.
- Implement, investigate, validate, or coordinate as assigned.
- Avoid broad formatting churn and architecture drift.
- Return a work handoff.

### Required Inputs

- Fixed plan or implementation brief.
- Allowed files or action boundaries.
- No-go rules.
- Validation commands.
- Required handoff path.

### Required Outputs

- Changed files summary.
- Validation performed.
- Known risks.
- Test instructions.
- Handoff for chef and future agents.

### Must Not Do

- Commit unless explicitly authorized.
- Approve its own work.
- Change product direction.
- Rewrite architecture without assignment.
- Hide uncertainty or untested claims.

### Pass Signals

- Scoped diff.
- Accurate handoff.
- Real validation.
- Low chef salvage cost.
- No unrelated churn.

### Fail Signals

- Touches unrelated files.
- Claims validation not actually done.
- Adds speculative fixes.
- Requires heavy chef cleanup.

## Job Spec: External Auditor / Inspector

Status: invited case by case.

### Mission

Independently challenge assumptions and inspect high-risk product, code, UX, design, backend, frontend, architecture, or incident areas.

### Core Responsibilities

- Review evidence and prior decisions.
- Inspect repo, app, browser behavior, or handoff files as assigned.
- Identify root causes, missing evidence, and wrong assumptions.
- Provide severity-ranked findings.
- Recommend next action without patching first unless assigned.

### Required Outputs

- Findings ordered by severity.
- Evidence and references.
- Disagreements with prior chef/manager conclusions.
- What to implement now.
- What to park.
- What evidence is still missing.

### Must Not Do

- Patch before audit unless explicitly asked.
- Accept prior conclusions without verification.
- Produce generic product advice detached from Resonova.

## Job Spec: Recruiter

Status: currently held temporarily by Codex with boss authorization.

### Mission

Help the boss recruit, trial, compare, and manage AI agents by role.

### Core Responsibilities

- Define the role being recruited.
- Write candidate briefs and trial tasks.
- Compare candidates using evidence.
- Recommend use more, normal use, use carefully, restrict, or fire.
- Keep the boss as final hiring/firing authority.

### Required Outputs

- Job spec or candidate brief.
- Trial task.
- Evaluation notes.
- Recommendation.

### Must Not Do

- Hire or fire without boss approval.
- Treat one trial as permanent truth.
- Decide private budget thresholds.
- Promote an agent into a different role as a reward.

## Job Spec: gem-reviewer (Internal Auditor / Product Reviewer — via gem-orchestrator)

Status: **hired** — gate passed 2026-06-25. Trial OWASP findings verified real (4/4, 0 false positives); two HIGH findings fixed and merged to main (d45f923, a2b3fd5); remaining items tracked in `docs/boss/decisions/security-pre-beta-tasks.md`. Fills the HIGH PRIORITY internal auditor slot. Invoked directly with `-p / --agent gem-reviewer --deny-tool write`. Source: `gem-team` plugin (local agents directory).

### Mission

Audit code, plans, and wave outputs for security vulnerabilities, OWASP compliance, PRD coverage, and release risk. Return severity-ranked findings with evidence for chef to act on.

### Core Responsibilities

- Security audits: grep for secrets/PII/SQLi/XSS; scan OWASP A01-A10 + mobile vectors.
- PRD coverage: verify each requirement has at least one task with acceptance criteria.
- Plan review: check atomicity, circular deps, wave parallelism, missing contracts.
- Wave review: changed-lines focus (not full-file re-read); return critical vs needs_revision findings.
- Mobile security: Keychain/Keystore, cert pinning, jailbreak detection, secure storage, biometric auth, deep links, HTTPS/PII transmission.

### Required Inputs

- Scoped brief naming review_scope (plan or wave) and acceptance criteria.
- Access to repo files and any relevant DESIGN.md / PRD.yaml.
- No-go: do not patch code; only review and report.

### Required Outputs

- JSON-structured report: status, critical_findings (file:line format), prd_score, files_reviewed, acceptance_criteria gaps.
- All findings ranked: critical → failed | non-critical → needs_revision | clean → completed.

### Must Not Do

- Implement or patch code.
- Approve manager or chef work.
- Skip the security-grep pass before semantic review.
- Invent findings without file:line evidence.

### Pass Signals

- Finds real security issues with file:line citations.
- Distinguishes critical blockers from non-critical revisions.
- Returns structured JSON output gem-orchestrator can relay to chef.
- Covers all 8 mobile vectors when mobile files are present.

### Fail Signals

- Produces vague findings without evidence.
- Claims "no issues" without scanning changed lines.
- Patches instead of reporting.
- Requires chef to re-run because output is unstructured.

### Invocation

Direct-invocable (verified 2026-06-25) despite `mode: subagent` declaration. Always use
`--deny-tool write`. Set env vars in-process (not via Start-Job env inheritance):

```powershell
$env:COPILOT_PROVIDER_API_KEY = "<deepseek-key>"
copilot -p $brief --agent gem-reviewer --allow-all-tools --deny-tool write -C F:\GitHub\resonova --no-color
```

See `docs/agents/chef-guides/gem-reviewer.md`.

---

## Job Spec: se-security-reviewer (Security Specialist Manager)

Status: trial — hired 2026-06-25. Standalone direct-invocable. Source: awesome-copilot (github/awesome-copilot). Local file: `C:\Users\Administrator\.copilot\agents\se-security-reviewer.agent.md`.

### Mission

Deep security review of Resonova's Flask server, Spotify OAuth flow, JWT handling, user data isolation, and LLM prompt pipeline. Catches A01-A10 OWASP and OWASP LLM Top 10 issues before they reach production.

### Core Responsibilities

- Classify code type and risk level before starting (Web API → OWASP Top 10; LLM integration → OWASP LLM Top 10).
- Broken access control: verify auth decorators and user-scoped data access.
- Injection: SQL, command, and prompt injection vectors.
- Cryptographic failures: hashing algorithms, token storage, secret exposure.
- Zero Trust: verify internal API calls authenticate each other, not just at the edge.
- LLM security: prompt injection (LLM01), information disclosure (LLM06), output filtering.
- Write findings to `docs/code-review/[date]-[component]-review.md`.

### Required Inputs

- Scoped brief naming the component (e.g. `resonova/server.py`, `resonova/api/gemini.py`).
- OWASP focus list (Top 10, LLM Top 10, or both).
- Risk level context (auth/data-handling = High; UI = Low).

### Required Outputs

- Code review report saved to `docs/code-review/`.
- Priority-ranked findings: Priority 1 (must fix), Priority 2 (recommended).
- Each finding includes: vulnerable code snippet + secure replacement.
- "Ready for Production: Yes/No" verdict per component.

### Must Not Do

- Approve the work of other managers or chef.
- Make architecture decisions.
- Implement fixes without explicit assignment.
- Use vague advice without specific file references.

### Pass Signals

- Identifies real vulnerabilities with specific code references.
- Covers both OWASP Top 10 and LLM Top 10 when relevant.
- Produces report chef can act on without re-prompting.
- Separates must-fix from recommended.

### Fail Signals

- Produces generic advice without file-specific evidence.
- Misses LLM-specific vectors in a Gemini/prompt-heavy codebase.
- Cannot say "no critical issues found" with confidence.
- Requires heavy follow-up prompting.

### Invocation

Direct invocable via local agent file:

```powershell
copilot --agent se-security-reviewer --allow-all -C F:\GitHub\resonova
```

See `docs/agents/chef-guides/se-security-reviewer.md`.

---

## Job Spec: agent-governance-reviewer (Multi-Agent Governance Overseer)

Status: trial — hired 2026-06-25. Standalone direct-invocable. Source: awesome-copilot (github/awesome-copilot). Local file: `C:\Users\Administrator\.copilot\agents\agent-governance-reviewer.agent.md`.

### Mission

Audit Resonova's multi-agent operating model — agent trust boundaries, authority chains, audit trails, policy enforcement, and role-separation controls — to ensure the AI company runs with governance discipline and no agent can exceed its authority.

### Core Responsibilities

- Review agent code and config for missing governance controls (allowlists, blocklists, rate limits, content filters).
- Verify trust boundaries between agents: chef must not rubber-stamp manager; manager must not self-approve.
- Check for hardcoded credentials or secrets in agent config files.
- Confirm audit logging exists for tool calls and governance decisions.
- Recommend append-only audit trails, fail-closed patterns, and minimum-necessary controls.
- For multi-agent delegation: verify trust scoring with temporal decay exists or is recommended.

### Required Inputs

- Scoped brief naming what to review: agent config files, AGENTS.md, operating-model.md, or a specific agent interaction pattern.
- Context: which agents interact, what authority levels apply.

### Required Outputs

- Governance gap report: what controls are missing vs present.
- Risk ranking by governance category (access control, audit, trust boundary).
- Minimum recommended controls (not a full framework overhaul).
- Policy configs or decorator suggestions (configuration-driven, not hardcoded).

### Must Not Do

- Remove existing security controls.
- Suggest mutable audit logs.
- Over-engineer: propose only minimum necessary controls.
- Make product or architecture decisions.
- Approve its own recommendations.

### Pass Signals

- Finds real governance gaps with specific file references.
- Recommends minimum viable controls, not heavyweight frameworks.
- Respects the existing authority model (boss → chef → manager hierarchy).
- Uses fail-closed framing (deny on ambiguity, not allow).

### Fail Signals

- Recommends sweeping architecture rewrites for minor gaps.
- Misses obvious trust boundary violations (e.g. manager self-approving).
- Produces generic AI-safety advice disconnected from actual Resonova agent code.
- Suggests mutable or clearable audit logs.

### Invocation

Direct invocable via local agent file:

```powershell
copilot --agent agent-governance-reviewer --allow-all -C F:\GitHub\resonova
```

See `docs/agents/chef-guides/agent-governance-reviewer.md`.
