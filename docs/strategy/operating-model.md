---
title: "Resonova Operating Model"
created: 2026-06-19
status: draft
owner: "Project owner"
---

# Resonova Operating Model

## Purpose

Define how the Resonova project should be operated while it is still a small, founder-led startup-style effort using multiple AI manager teams.

This file exists because the project owner may give vague goals, lose context over time, and return later expecting the system to preserve direction, evidence, and continuity.

## Authority Model

```text
Project owner
-> strategy / chief-of-staff layer
-> manager teams
-> specialist agents
-> code, docs, tests, research artifacts
```

### Project Owner

The project owner is the final authority.

The owner's job is to provide goals, taste, dissatisfaction, priorities, and acceptance or rejection. The owner may give vague, wild, incomplete, or unrealistic goals. The system should not require the owner to remember every prior decision or manage every detail.

Owner constraints:

- Time is limited.
- Energy is limited.
- Memory may be unreliable across sessions.
- The owner may inspect work after the fact and reject poor work.
- The owner should not be forced into low-level project management.

### Strategy / Chief-of-Staff Layer

This is the layer currently handled by Codex in this thread.

Responsibilities:

- Convert vague owner goals into bounded strategic briefs.
- Preserve decisions in `docs/strategy/`.
- Choose which manager team is appropriate for a task.
- Prepare manager-ready prompts.
- Read manager handoffs and evaluate whether they answer the owner-level goal.
- Separate verified facts, assumptions, proposals, and accepted decisions.
- Protect the owner from repeated rediscovery and memory loss.
- Escalate only when a decision materially needs owner judgment.

This layer is below the owner and above manager teams.

It should not pretend to be the final authority. It proposes, structures, and reviews.

### Manager Teams

Manager teams execute bounded goals and return evidence.

Current manager options:

- RUG: strict delegation and validation loop.
- gem-orchestrator: phased planning/execution with durable plan artifacts.
- OCP Workspace Lead: bounded evidence-based delegation with archive candidates.

Managers should not redefine the project direction. They receive a goal, scope, constraints, and success checks, then return a handoff or evidence packet.

### Specialist Agents

Specialist agents perform lower-level work such as implementation, QA, research, design, debugging, documentation, or validation.

Their outputs are not automatically accepted as project direction.

## Boss-Style Workflow

The owner may say something like:

```text
Make this more like a growing personal AI radio companion.
```

The strategy layer should translate that into:

1. What problem is being solved.
2. What is in scope now.
3. What is explicitly out of scope.
4. Which manager team should handle it.
5. What evidence must come back.
6. Where the handoff should be written.
7. What decisions remain for the owner.

The owner should be able to inspect later and decide:

- accepted
- rejected
- needs revision
- manager/agent failed
- direction changed

## Gating, Veto, And Redo Rules

Manager team output is not accepted automatically.

For now, every nontrivial manager handoff must return to the strategy / chief-of-staff layer for review before it is treated as usable project state.

Review responsibilities:

- Check whether the handoff answered the original owner-level goal.
- Check whether the manager stayed inside scope.
- Check whether evidence is strong enough.
- Check whether assumptions, candidate issues, and accepted decisions are separated.
- Check whether secrets or sensitive values were exposed.
- Check whether the result is clear enough for the owner to inspect quickly.

If the output is low quality, incomplete, vague, or has drifted from the goal, the strategy layer can veto it without asking the owner to debug the details.

Veto outcomes:

- request revision from the same manager
- redo with a different manager team
- split the task into smaller manager briefs
- escalate to the owner only when the decision changes product direction, risk, cost, or scope

The owner should usually only be called when judgment or authorization is required. If no owner decision is needed, the strategy layer should prepare the result for owner verification and authorization.

Git is the version-control and recovery boundary:

- use git status/diff to inspect changes
- keep unrelated work separate where possible
- do not treat generated handoffs as accepted until reviewed
- after an update is validated and accepted, create a git commit checkpoint
- use commits as explicit checkpoints when the owner authorizes them
- never use destructive git operations unless the owner explicitly asks

## Memory And Continuity Rules

Because the owner may forget context, durable artifacts matter.

Use these surfaces:

- `docs/strategy/`: owner-level strategy, operating model, briefs, roadmap, decisions.
- `docs/handoffs/`: manager or executor handoffs.
- `.github/skills/future-self-reorientation/`: skill for future owner re-entry artifacts.
- `docs/plan/`: manager-generated durable plans when using gem-team.

Important rule:

```text
Do not rely on chat memory alone.
```

For any nontrivial stage, preserve at least one of:

- a strategy brief
- a handoff
- an archive candidate
- a future-self reorientation artifact

## Quality Bar

The owner may be dissatisfied if work is sloppy, vague, or drifts from the goal.

Manager-ready tasks should therefore include:

- objective
- scope
- constraints
- prohibited actions
- success criteria
- evidence required
- handoff location
- open questions

Reports should clearly separate:

- verified facts
- assumptions
- candidate issues
- rejected ideas
- accepted decisions
- unresolved questions

## Current Operating Sequence

The agreed initial sequence is:

1. Audit current Resonova MVP.
2. Define product vision and roadmap.
3. Research comparable apps.

The first created strategy brief is:

```text
docs/strategy/resonova-mvp-audit-brief.md
```

Preferred manager for the first audit:

```text
OCP Workspace Lead
```

Reason: the first task is bounded audit work, not implementation.
