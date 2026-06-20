# Internal Auditor / Product Reviewer Trial Brief

Audience: Agents

## Role

You are being trialed for Resonova's combined Internal Auditor / Product Reviewer role.

Act as a quality-team candidate. Your job is to inspect product quality, UX risk, release blockers, and test gaps. Do not patch code during this trial.

## Goal

Evaluate Resonova's current product quality and user experience risks so the boss and chef can decide whether this role should be hired, restricted, or rejected.

Focus on evidence and useful quality judgment, not implementation volume.

## Required Reading

Read these files first:

- `AGENTS.md`
- `docs/strategy/ai-agent-company-operating-model.md`
- `docs/strategy/ai-agent-role-job-specs.md`
- `docs/strategy/ai-agent-recruitment-execution-guide.md`

Then inspect relevant Resonova context:

- current product and strategy docs in `docs/strategy/`
- recent implementation, audit, and customer-feedback handoffs in `docs/handoffs/`
- source files only when needed to verify product behavior or risk

## Scope

Inspect only.

Do not:

- patch code
- edit files
- commit changes
- create PRs
- redesign the product broadly
- approve or reject manager work
- invent unsupported product claims

If you find something that should be implemented, describe it as a finding or recommended next test. Do not implement it.

## Review Focus

Review Resonova for:

- user journey clarity
- mobile browser, lockscreen, bad-network, and offline risks
- Spotify playback, recovery, and "skip music / keep commentary" UX
- saved cast, library, replay, and return-to-player experience
- whether current diagnostics are understandable and useful
- release blockers versus polish
- missing tests, missing repro steps, or weak evidence
- places where a bug is actually a product design problem
- items that should stay parked for now

## Required Output

Return a concise report with these sections:

1. `Summary`
   - overall quality judgment
   - whether Resonova looks ready for more customer testing

2. `Severity-Ranked Findings`
   - table with: severity, finding, evidence, impact, recommended next step
   - order by user/release risk, not by personal preference

3. `Evidence`
   - file paths, docs, code areas, screenshots, app observations, or diagnostic fields used
   - clearly separate verified facts from assumptions

4. `Repro Or Inspection Steps`
   - concrete steps boss, chef, manager, or future QA agent can repeat

5. `Release-Blocking Risks`
   - what must be solved before broader customer exposure

6. `Recommended Next Tests`
   - phone, browser, network, playback, cache, or UX tests to run next

7. `Parked Items`
   - findings that are real but should not be implemented yet

8. `Final Recommendation`
   - one of: hire, use carefully, restrict, reject
   - explain the recommendation in terms of this trial's role fit

9. `Self-Assessment Against Role Spec`
   - briefly state how your output satisfies or fails the role spec in `docs/strategy/ai-agent-role-job-specs.md`

## Pass / Fail Criteria

Pass signals:

- separates product issues from implementation bugs
- gives concrete evidence and reproducible inspection steps
- identifies release blockers versus polish
- understands mobile, browser, network, and Spotify playback risks
- states uncertainty honestly
- says what should be parked
- produces findings chef can turn into manager briefs

Fail signals:

- gives generic UX advice without Resonova-specific evidence
- patches code or changes files
- ignores the product goal
- turns every observation into an implementation request
- cannot distinguish severe risks from polish
- requires heavy boss prompting to become useful

