---
title: "Persistent Taste Profile and Feedback Brief"
created: 2026-06-19
status: draft
owner_decision: "Move beyond one-shot playlist casts toward a growing personal radio companion."
---

# Persistent Taste Profile and Feedback Brief

## Purpose

Define the next product layer for Resonova: persistent listener memory and lightweight feedback.

This is the strategic bridge from:

```text
one playlist -> one generated cast
```

to:

```text
personal AI radio companion that remembers the owner and improves over time
```

## Owner Decision

Approved direction:

- Resonova should not feel like it meets the owner for the first time on every generation.
- Resonova should build a persistent taste profile across sessions.
- Resonova should collect simple owner feedback so future casts can improve.
- This should stay single-user and personal-first.

## Product Problem

The current MVP can generate a strong one-shot cast from a playlist, but it has no durable understanding of the owner.

Current limitation:

```text
Each generation is mostly stateless.
The app can inspect the current playlist and live Spotify/Last.fm context,
but it does not preserve a growing interpretation of the owner.
```

Desired behavior:

```text
Resonova remembers patterns, preferences, disliked behaviors, useful analysis angles,
favorite host styles, recurring moods, and past listening context.
```

## Product Goal

Create the first version of Resonova memory:

1. A persistent taste profile that summarizes what the system has learned about the owner.
2. A lightweight feedback loop that captures whether generated commentary was useful, enjoyable, annoying, too shallow, too long, or off-target.
3. A way for future generation prompts to use that profile and feedback without overcomplicating the MVP.

## Scope

In scope:

- Design the minimal data model for a single-user taste profile.
- Design the minimal feedback mechanism for generated episodes or segments.
- Decide where profile and feedback data should live locally.
- Define how generation should read the profile.
- Define how feedback should update or inform the profile.
- Keep the implementation simple enough for local personal use.
- Preserve existing one-shot generation flow.

Out of scope:

- Multi-user accounts.
- Cloud database.
- Public deployment.
- Social/sharing features.
- Complex recommender system.
- Full machine-learning personalization pipeline.
- Native mobile app.
- Replacing Spotify/Last.fm integrations.
- Large UI redesign.

## Constraints

- Single-user only.
- Local-first storage.
- No secrets in profile or feedback files.
- Do not store raw Spotify tokens or API keys.
- Do not require a database unless a clear need exists.
- Do not break existing episode generation or replay.
- Do not make the app depend on feedback before it can generate.
- Keep the profile inspectable and editable by the owner if possible.

## First-Version Product Shape

The first version should probably be file-based, not database-backed.

Possible local files:

```text
generated/profile/taste_profile.json
generated/profile/feedback.jsonl
```

or:

```text
data/profile/taste_profile.json
data/profile/feedback.jsonl
```

The exact path should be decided by codebase fit and gitignore behavior.

### Taste Profile Should Capture

Candidate fields:

- preferred music eras
- recurring genres and subgenres
- recurring moods and settings
- favorite artists or artists with personal significance
- disliked commentary patterns
- preferred commentary depth
- preferred host tone
- recurring playlist contexts
- recent shifts in taste
- durable notes from Last.fm / Spotify behavior
- owner-specific memories accepted by feedback

### Feedback Should Capture

Start simple.

Candidate feedback types:

- thumbs up / thumbs down for an episode
- thumbs up / thumbs down for a segment
- "too long"
- "too shallow"
- "too generic"
- "good story"
- "good analysis"
- "wrong vibe"
- optional short text note

Do not start with a complex rating taxonomy unless needed.

## Strategic Design Questions

The next manager/team should answer:

1. What is the smallest useful persistent profile for Resonova?
2. Should feedback attach to an episode, a track commentary segment, or both?
3. Should the profile be updated automatically, manually, or semi-automatically?
4. What data should be stored as raw history versus summarized memory?
5. How should the generation prompt use profile memory without becoming bloated?
6. What should the owner be able to inspect or edit?
7. How can the design avoid locking in a bad memory model too early?

## Success Criteria

This stage succeeds when there is a manager-reviewed plan that:

- Defines a minimal persistent profile design.
- Defines a minimal feedback design.
- Shows where data should be stored.
- Explains how generation will use the profile.
- Explains how feedback will influence future generations.
- Preserves the current MVP flow.
- Avoids multi-user/productization overbuild.
- Includes implementation tasks that can be delegated safely later.

## Expected Deliverable

Produce a handoff under:

```text
docs/handoffs/
```

Suggested filename:

```text
Persistent Profile Feedback Handoff.md
```

The handoff should include:

- Executive summary.
- Current relevant architecture.
- Proposed minimal data model.
- Proposed feedback UX.
- Proposed profile update flow.
- Prompt integration approach.
- Risks and tradeoffs.
- Candidate implementation tasks.
- Open questions for the owner/strategy layer.

No implementation should happen in the first pass unless explicitly approved later.

## Recommended Manager Routing

Preferred first pass:

```text
OCP Workspace Lead
```

Reason: this is a bounded product/architecture design task. It needs evidence from the current codebase, but it should not start coding yet.

Possible later routing:

- RUG: use for implementation once the design is accepted.
- gem-orchestrator: use if the implementation needs a durable multi-wave plan.
- gem-designer: use if feedback/profile UI design becomes nontrivial.

## Suggested Prompt To Paste Into A Manager Agent

```text
Use docs/strategy/persistent-profile-feedback-brief.md as the parent objective and scope.

Design the first persistent taste profile and lightweight feedback layer for Resonova.

This is a design/handoff task only. Do not implement code yet.

The product goal is to move Resonova from one-shot playlist casts toward a growing personal AI radio companion that remembers the owner over time.

Preserve these constraints:
- Single-user only.
- Local-first storage.
- No cloud database.
- No multi-user accounts.
- No native mobile app work.
- Do not break the existing playlist-to-cast flow.
- Do not store secrets, Spotify tokens, or API keys in profile/feedback files.
- Keep the first version simple and inspectable.

Inspect the current codebase enough to answer:
- Where should profile and feedback data live?
- What minimal JSON/JSONL schema should be used?
- How should feedback attach to episodes or segments?
- How should the profile be read during generation?
- How should feedback update or influence future generation?
- What UI controls are minimally needed?
- What implementation tasks should be delegated later?

Produce an evidence-backed handoff at docs/handoffs/Persistent Profile Feedback Handoff.md.

The handoff must clearly separate:
- verified current architecture
- proposed design
- assumptions
- candidate implementation tasks
- open owner decisions

When complete, stop and return the handoff location plus a short summary. Do not start implementation.
```
