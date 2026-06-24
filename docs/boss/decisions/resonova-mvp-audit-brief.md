---
title: "Resonova MVP Audit Brief"
created: 2026-06-19
status: draft
owner: "Strategy layer"
intended_manager_layer:
  - RUG
  - gem-orchestrator
  - OCP Workspace Lead
---

# Resonova MVP Audit Brief

## Purpose

Audit the current Resonova local MVP before defining the product vision, roadmap, or comparable-app research plan.

This brief is written for the layer above execution managers. Its job is to define what the audit should answer, what is in scope, what is out of scope, and what evidence a manager team must return.

## Strategic Context

Resonova is the user's product direction, forked from the Spoticast MVP.

The current MVP is understood as:

```text
Spotify playlist
-> AI-generated cast/radio script
-> Gemini TTS host audio
-> browser playback with Spotify music
```

The intended product direction is broader:

```text
Resonova = a personal AI radio/cast companion that grows with listening history, taste profile, feedback, and usage over time.
```

Spoticast should be treated as the upstream/base implementation identity. Resonova is the product identity.

## Audit Objective

Produce an evidence-backed understanding of the current local MVP:

1. What the app can currently do.
2. How the current flow works end to end.
3. Which parts are stable enough to build on.
4. Which parts are fragile, renamed incompletely, or blocked by configuration.
5. What gaps exist between the current MVP and the Resonova product direction.
6. What should be preserved as core working assets.
7. What should not be changed yet.

The audit must not implement new features.

## Scope

In scope:

- Repository structure and main entry points.
- Current app name and rename state: Spoticast to Resonova.
- Server startup path and local host/port behavior.
- Spotify integration.
- Gemini script generation integration.
- Gemini TTS integration.
- Playback/frontend flow.
- Generated episode/artifact storage.
- Configuration and environment requirements, without exposing secrets.
- Existing docs and handoffs.
- Obvious tests, scripts, or validation commands.
- Current git branch and working tree state.

Out of scope:

- New product features.
- Major refactors.
- Multi-user architecture.
- Online deployment.
- Authentication design.
- New database or long-term profile implementation.
- Comparable-app research.
- Product roadmap decisions.

## Constraints

- Do not expose or commit `.env` secrets.
- Do not print Spotify client secret, Gemini API key, or other credentials.
- Do not revert the Spotify API compatibility fixes described in the handoff docs.
- Do not hardcode Gemini model names.
- Keep script generation model and TTS model separate.
- Treat the project as personal-use and single-user for now.
- Do not expand scope from audit into implementation.
- If validation requires real API calls, record what was attempted and whether credentials were available, but do not reveal credential values.

## Key Reference Files

Read these first:

- `docs/handoffs/Spoticast -> Resonova.md`
- `docs/handoffs/Spoticast Local MVP Handoff.md`
- `README.md`
- `pyproject.toml`
- `.env.example`

Then inspect the implementation surfaces needed to understand the flow, likely including:

- `resonova/`
- server entry point
- Spotify API module
- Gemini/LLM module
- TTS/audio generation module
- frontend/static playback files
- generated episode output paths

Read `.env` only if required for local validation, and never include secret values in the report.

## Questions The Audit Must Answer

### Product and Flow

- What is the current user journey from opening the app to generating/listening to an episode?
- Is the MVP still one-playlist-to-one-cast, or does it already contain any persistent profile/history behavior?
- What outputs are generated, where are they stored, and can they be replayed?
- What parts already support the future "growing personal cast" direction?

### Technical Architecture

- What are the main modules and their responsibilities?
- What external APIs are used?
- Where are model names configured?
- How does the server communicate with the frontend?
- How does playback alternate between AI commentary and Spotify music?
- What assumptions does the code make about Spotify Premium, browser support, local files, or network access?

### Rename Health

- Are there remaining `spoticast` package names, imports, docs, commands, or UI labels?
- Are any remaining references intentional upstream/base references?
- Does `uv run python -m resonova` work?
- Do README commands match the current package name?

### Configuration and Secrets

- What environment variables are required?
- Are `.env.example` and config code aligned?
- Is `.env` ignored by git?
- Are generated artifacts and local caches ignored where appropriate?

### Validation

- Which commands were run?
- Did the server start?
- Did the web UI load?
- Could a public or user playlist be processed?
- Could TTS audio be generated?
- If any validation was not run, why not?

### Risks and Gaps

- What could break the MVP flow?
- What parts are most fragile or hard to extend?
- What gaps block the next strategy step: product vision and roadmap?
- What gaps are important but can wait?

## Expected Deliverable

The manager team should produce a handoff/report file under:

```text
docs/handoffs/
```

Suggested filename:

```text
Resonova MVP Audit Handoff.md
```

The report should include:

- Executive summary.
- Current MVP capability map.
- End-to-end flow map.
- Architecture map with file references.
- Rename health findings.
- Configuration and secret-handling findings.
- Validation commands and results.
- Risks, gaps, and candidate issues.
- Recommended preservation list: what not to break.
- Open questions for the strategy layer.
- Clear statement of any work not performed.

Do not present implementation recommendations as automatically approved next tasks. Treat them as candidate issues or roadmap inputs.

## Success Criteria

The audit is successful when:

- A future agent can understand the current MVP without rediscovering the whole repo.
- The strategy layer can safely move to product vision and roadmap definition.
- The report clearly separates verified facts from assumptions.
- Validation evidence is included.
- No secrets are exposed.
- No product or architecture direction is accepted without user/strategy-layer review.

## Recommended Manager Routing

Any of the manager systems can run this audit, but their fit differs:

- RUG: best if the goal is strict delegation and independent validation.
- gem-orchestrator: best if a durable `docs/plan/{plan_id}` plan and context envelope are useful.
- OCP Workspace Lead: best if the audit should remain tightly bounded, evidence-based, and end with a self-contained archive candidate.

Preferred first pass:

```text
OCP Workspace Lead
```

Reason: this is an audit, not implementation. OCP's bounded scope, evidence discipline, and archive candidate format match the need well.

## Suggested Prompt To Paste Into A Manager Agent

```text
Audit the current Resonova local MVP using the strategy brief at docs/boss/decisions/resonova-mvp-audit-brief.md as the parent objective and scope.

This is an audit only. Do not implement new features, refactor, or change product direction.

Produce an evidence-backed handoff file at docs/handoffs/Resonova MVP Audit Handoff.md.

Preserve these constraints:
- Do not expose or commit secrets.
- Do not print .env values.
- Do not revert existing Spotify API compatibility fixes.
- Keep script generation and TTS model configuration separate.
- Treat Resonova as a personal-use local MVP for now.

The handoff must answer the audit questions in the brief, include validation commands/results, clearly separate facts from assumptions, and list candidate issues without turning them into approved next tasks.
```
