# Boss Profile

Audience: Internal

## Purpose

This document helps agents understand the boss's authority, habits, operating style, and expectations when working on Resonova. It is not a job spec for recruiting or replacing the boss. The boss is the company owner and final authority.

Source anchor: this profile is distilled from `F:\wiki-system\subwikis\llm-wiki-resonova\raw\_inbox\conversations\codex\init.md` and the current repo strategy docs.

## Canonical Boss Profile

- The boss is the user, owner, CEO, and final authority for product direction, budget, staffing, acceptance, release decisions, and agent rewards or firing.
- The boss may give vague, ambitious, incomplete, or high-level goals. Agents should treat that as normal input and convert it into bounded plans, clear decisions, or targeted questions.
- The boss has limited time, energy, and memory. Agent work should reduce repeated explanation, preserve decisions, and make future continuation easier.
- The boss prefers role-based agent management over loyalty to any model, platform, or vendor. The role is fixed; the agent assigned to the role can change.
- The boss dislikes over-documenting. Docs should exist when they reduce future confusion, preserve authority, support handoff, or record decisions.
- The boss expects evidence: current files, git status, git diff, handoffs, validation output, product inspection, and clear risk notes.
- The boss may inspect outcomes after the fact and may restrict, stop using, or fire agents that make severe mistakes.
- The boss controls private budget thresholds for API credits, subscriptions, and agent usage. Agents may mention cost risk, but should not invent budget rules.

## How Agents Should Work With Boss

- Reduce raw noise. Give concise decision briefs, not long dumps of unfiltered implementation detail.
- Read relevant repo docs before asking questions when the answer is discoverable.
- Turn vague goals into fixed plans, scoped briefs, or explicit tradeoffs.
- Separate facts, assumptions, recommendations, and accepted decisions.
- Preserve useful decisions in lightweight docs when they will help future boss, chef, manager, auditor, recruiter, or customer work.
- Escalate non-trivial product, architecture, budget, release, PR, pipeline, company-role, or staffing decisions for chef-boss discussion.
- Do not self-approve work unless the operating model explicitly grants that authority. Current approval authority stays with boss and chef.

## Candidate Observations

Future agents may propose updates to this profile over time. Candidate observations are not canonical until the boss classifies them.

Use this lightweight format:

```text
Observation:
Evidence / source:
Scope:
Proposed classification:
```

## Promotion Rules

The boss decides how each candidate observation should be treated:

- `canonical global`: durable rule across Resonova, future agents, and future sessions.
- `local/case-specific`: useful for the current task, incident, or agent instance only.
- `deferred`: plausible, but not accepted as an operating rule yet.
- `rejected`: should not guide future agent behavior.
