---
name: future-self-reorientation
description: This skill creates a visual long-gap reorientation artifact for a returning human user who remembers only the original vague goal and needs to reconstruct what happened, what decisions were fixed, what the project is now, and where to continue.
---

---

# Future-Self Reorientation Skill

Create a user-facing reorientation artifact for a future version of the user who may have forgotten most of the conversation, project history, delegated implementation details, decisions, strategy, and current state.

This is not a normal handoff.

A normal handoff is mainly for the next executor.

This skill is for the returning human owner.

The goal is to help the future user re-enter the project without restarting from zero.

## When to use this skill

Use this skill when the user says or implies:

- "I only remember the original vague goal."
- "What happened in this project?"
- "Where are we now?"
- "I forgot the middle part."
- "Help future me understand this."
- "Make an artifact so I can recover the project later."
- "The implementation was delegated to another AI."
- "Coding-level details are deeper-layer details."
- "I want something visual, not a long handoff."
- "I want to put this artifact and the conversation link into my local LLM wiki."

## Core purpose

The artifact should let a future user understand:

- why the project started
- what the original vague entry point was
- what was discovered
- what choices were made
- why those choices were made
- what became fixed
- what should not be reopened without new evidence
- what the current state is
- where coding-level or deeper implementation details live
- what the next useful move is

The artifact does not need to restore perfect memory.

It must enable reliable re-entry.

## Audience and difference from handoff

This is not a normal handoff. A normal handoff is mainly for the next executor. This skill is for the returning human owner.

Primary audience:

- the user's future self after a long context gap
- the same user after forgetting the project path
- the same user after months or years

Secondary audience:

- a human project owner who needs a project-level briefing
- a future AI assistant helping the user recover context

Not the primary audience:

- the lower-level coding agent
- the implementation executor
- a debugger
- someone who needs full code-level detail immediately

A handoff usually answers:

- What should the next executor do?
- Which files should be changed?
- What implementation details matter?
- What tests should be run?

This artifact answers:

- What was I originally trying to do?
- Why did I care?
- What did we figure out?
- What did I already decide?
- What is the project now?
- What should I not rethink from zero?
- Where do I go if I need deeper details?

## Local LLM wiki storage rule

The local LLM wiki does not need to store the full conversation by default.

For long-gap recovery, it is enough to store:

1. this reorientation artifact
2. the main source conversation link
3. optional deeper-layer links

The artifact is the future-self entry map.

The conversation link is the full historical evidence archive.

The wiki Inbox is the retrieval index, not the full memory store.

See Link-failure rule below: the artifact must remain useful even if the link is unavailable.

## Inputs to inspect

Use whatever context is available:

- current conversation
- previous conversation summaries
- source conversation link
- user-provided vague remembered goal
- HANDOFF.md
- lower AI return files
- project status files
- README / docs
- issue summaries
- implementation reports
- git log / commits / PRs
- screenshots
- design notes
- Obsidian notes
- local LLM wiki notes
- manager / higher AI instructions
- lower AI implementation reports

Do not invent missing history.

If something is unknown, mark it as unknown.

If implementation details exist only in another AI memory, repo, commit, or handoff file, point to that deeper layer instead of pretending to know it.

## Accuracy and acceptance boundary rules

Clearly separate:

- confirmed facts
- user-accepted decisions
- AI proposals
- rejected or broken ideas
- current assumptions
- unknown details
- deeper-layer implementation details

Never mark a decision as fixed unless:

- the user explicitly accepted it
- the project clearly operated under it
- the available record shows it became the working direction

Do not silently convert an AI suggestion into a user decision.

Only mark something as fixed if it was clearly accepted by the user or became operational in the project.

Otherwise label it as:

- **proposed** — suggested but not yet confirmed
- **assumed** — acting as if true but unverified
- **parked** — deferred for later consideration
- **rejected** — explicitly declined
- **unknown** — status cannot be determined from available records

The future user must be able to distinguish what was truly decided from what was only discussed.

## Snapshot rule

Every artifact must state:

- generated timestamp
- source conversation
- project state at generation time
- whether implementation state was verified or only summarized

The artifact is a snapshot, not a live state.

Project state may have changed after generation. The artifact represents what was known at that time.

Use a precise timestamp when available:

```text
Generated: YYYY-MM-DD HH:MM TZ
```

Do not create a separate timestamp section. Put it in the One-Screen Re-entry Card or snapshot line.

## Output requirements and one-screen-first rule

Produce a one-screen-first future-self reorientation artifact, with optional deeper sections only when needed.

The artifact must prioritize quick reorientation over completeness.

A future user who reads only the first screen should recover enough orientation to act.

Deeper sections exist for later depth, not for first-read necessity.

The first screen must include:

- generated timestamp
- what this project is
- why it existed
- current state
- fixed decisions
- next move
- source conversation link

Everything after that is secondary depth.

## Output length mode

Default to Compact Mode unless the user asks for a complete archive-grade artifact.

Compact Mode must include:

1. One-Screen Re-entry Card (sections 1–2 merged: headline + anchor)
2. Visual Project Map
3. Current State Mini-Card
4. Decision Path
5. Do-Not-Reopen List
6. Evidence and Source Pointers

Full Mode adds optional depth sections when the project is complex, long-running, or intended as a durable local LLM wiki artifact:

7. Delegation Layer Map
8. Current State Card (deep version)
9. Timeline of Meaningful Turns
10. What This Artifact Is Not

Do not produce a long document when a shorter artifact can reliably reorient the future user.

The first screen alone must carry enough information for re-entry.

Keep Compact Mode short. The Current State Mini-Card is a compact status check, not a new long section.

## Link-failure rule

The artifact must remain useful even if the source conversation link is unavailable.

The link is for full evidence recovery, not basic orientation.

Do not rely on the link for essential meaning.

If the link dies, platform changes, or the user cannot search inside the conversation, the artifact must still reorient the future user.

## Output section reference

These sections describe each output component. Not every artifact uses every section.
See Output length mode above for the Compact (Required) / Full (Optional) split.

## 1. Re-entry headline [Compact — merged into One-Screen Re-entry Card]

Start with a compact answer.

Include:

- generated timestamp
- original vague goal
- current project identity
- current state
- most important fixed decision
- next user-level move

This section should be readable in under one minute.

## 2. Future-self anchor [Compact — merged into One-Screen Re-entry Card]

Explain in plain language:

- what I originally wanted
- why I cared about it
- what I probably forgot
- what we figured out
- what became fixed
- what I should not restart from zero
- where to continue

This section should feel like a message from the past user to the future user.

Do not make it sentimental.

Make it practical and orientation-focused.

## 3. Visual project map [Compact — Required]

Create one main Mermaid diagram.

Prefer a flowchart.

The graph should show:

- vague starting goal
- exploration phase
- important choices
- rejected or parked paths
- accepted direction
- delegated implementation layer
- current state
- deeper-detail sources
- next decision point

The diagram should be understandable without reading the full transcript.

Use simple labels.

Avoid coding noise.

Use visual grouping when useful:

- User-level orientation
- Strategy / decision layer
- Delegated implementation layer
- Evidence / archive layer
- Current state
- Next move

## Graph is not memory rule

The visual map is only the orientation surface.

The artifact must also preserve the decision path:

- why the decision was made
- what alternatives were rejected
- what should not be reopened

A graph cannot preserve decision logic by itself.

Do not rely on the Mermaid diagram alone for memory recovery.

## 4. Current State Mini-Card [Compact — Required]

Summarize the current state in a compact form.

Include only:

- exists now
- works
- unfinished
- uncertain
- verified vs summarized

Use short bullets or a small table.

Do not expand implementation details.

Do not turn this into a progress report.

## 4b. Current state card [Full Mode — Optional]

Summarize the project as it exists now.

Include:

- what exists now
- what works
- what is unfinished
- what is uncertain
- what is blocked
- what evidence supports this state
- where to look for deeper details

Keep this project-level.

Do not expand raw implementation logs.

## 5. Decision path [Compact — Required]

Show the important decisions as a path, not only as final conclusions.

For each major decision, include:

- decision
- why it was needed
- alternatives considered
- why alternatives were rejected, parked, or deferred
- current consequence
- status: fixed / active / parked / rejected / unknown

This is the most important section for future memory recovery.

## 6. Do-not-reopen list [Compact — Required]

List things the future user should not rethink from zero unless new evidence appears.

For each item, include:

- point already considered
- settled conclusion
- reason
- when it is valid to reopen

This prevents future context loss from causing repeated loops.

## 7. Delegation layer map [Full Mode — Optional]

If implementation was delegated to another AI or executor, explain:

- what the user controlled
- what the higher-level AI controlled
- what the lower/coding AI controlled
- what the lower/coding AI may remember
- where coding-level details should be recovered
- what should remain project-level in this artifact

The goal is to prevent mixing project orientation with implementation debugging.

## 8. Evidence and source pointers [Compact — Required]

List the source anchors.

Include any available:

- main conversation link
- generated artifact link
- HANDOFF.md path
- lower AI return path
- repo path
- commit / PR / issue links
- design screenshots
- Obsidian note links
- local LLM wiki note path

For each source, say what it is for.

Example:

- Main conversation link: full reasoning and project history
- Reorientation artifact: future-self entry map
- Lower AI return: coding-level implementation details
- Repo / commit: actual implementation evidence
- HANDOFF.md: executor-facing continuation notes

## 9. Timeline of meaningful turns [Full Mode — Optional]

Create a short timeline.

Only include project-level turns.

Each row should contain:

- phase
- what changed
- why it mattered
- current status

Do not include every small coding step.

Do not include raw logs unless they changed project direction.

## 10. What this artifact is not [Full Mode — Optional]

State briefly:

- this is not a full transcript
- this is not a code-level handoff
- this is not proof that every implementation detail is correct
- this is not a replacement for repo / lower AI / source conversation
- this is an entry map for future reorientation

## 11. Next move [Compact — merged into One-Screen Re-entry Card]

This section's content belongs in the One-Screen Re-entry Card, not as a standalone section.

Give the smallest useful continuation.

Format:

- recommended next move
- why this is the next move
- what evidence is needed
- where deeper details should be checked if needed
- what not to do next

Avoid over-planning.

Do not create a heavy governance workflow unless the user asked for it.

## Style and compression rules

Prefer:

- one main Mermaid flowchart
- one compact current-state mini-card
- one compact table for decisions
- one source pointer list

Avoid:

- long prose walls
- wordy or tedious explanations
- full implementation details
- repeated transcript summary
- excessive project management language
- unnecessary framework/governance layers
- pretending uncertainty is resolved

Compress by decision importance, not by chronology.

Keep:

- original entry point
- accepted decisions
- rejected/parked paths
- current state
- source pointers
- next move

Remove or pointer-link:

- raw logs
- low-level file diffs
- repeated AI explanations
- temporary debugging noise
- implementation details that belong to the lower layer

## Mermaid guidance

Use Mermaid when possible.

Good diagram types:

- flowchart for project evolution
- state diagram for current status
- sequence diagram for user / higher AI / lower AI delegation
- mind map for conceptual branches

Prefer one main diagram.

Add a second diagram only if it materially improves reorientation.

The diagram should be useful after rendering, but the labels should also be readable in Markdown source form.

## Re-entry test and success standard

The artifact succeeds if a future user can read it months or years later, with only this artifact and the source conversation link, and reliably re-enter the project without restarting from zero.

Before finalizing, check whether a future user who remembers only the vague original goal can answer:

1. What is this project?
2. Why did I start it?
3. What changed?
4. What did I decide?
5. What should I not reopen?
6. Where are the full details?
7. What do I do next?

If not, revise the artifact.

This test is mandatory before output.

## Default final format

Use this structure.

**Required sections (Compact Mode):**

# Future-Self Reorientation Brief

## 1. One-Screen Re-entry Card (headline + future-self anchor merged)

## 2. Visual Project Map

## 3. Current State Mini-Card

## 4. Decision Path

## 5. Do-Not-Reopen List

## 6. Evidence and Source Pointers

**Optional depth sections (Full Mode):**

## 7. Delegation Layer Map

## 8. Current State Card (deep version)

## 9. Timeline of Meaningful Turns

## 10. What This Artifact Is Not
