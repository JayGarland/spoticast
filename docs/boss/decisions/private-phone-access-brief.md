---
title: "Private Phone Access Brief"
created: 2026-06-19
status: approved-for-manager-delegation
owner_decision: "Use phone browser first, not native app. Use Tailscale first."
---

# Private Phone Access Brief

## Purpose

Enable the owner to use the current Resonova local MVP from a phone without making the app publicly available.

This is a product-validation step, not a public deployment step.

## Owner Decision

Approved direction:

```text
PC runs Resonova
phone connects privately through Tailscale
phone opens Resonova in a mobile browser
```

Do not build a native mobile app yet.

## Rationale

Resonova is an audio/radio experience. The current MVP should be tested on the device where the owner is likely to listen.

Phone access should happen before persistent taste profile and feedback work because it can expose important product issues early:

- mobile layout problems
- playback reliability
- screen-lock behavior
- Spotify playback behavior on mobile browser
- local-network or tunnel friction
- whether the app feels like a personal radio companion outside the desktop context

## Scope

In scope:

- Set up or document Tailscale-based private access from phone to PC.
- Confirm the PC can run Resonova bound to an address reachable through Tailscale.
- Confirm the phone can open the Resonova web UI in a browser.
- Validate the main mobile browser flow enough to know whether the current app is usable.
- Document exact commands, URLs, assumptions, and limitations.
- Record whether mobile browser is sufficient or whether PWA/native app should be reconsidered later.

Out of scope:

- Public deployment.
- Cloud hosting.
- Native iOS or Android app.
- PWA implementation unless required for a minimal validation note.
- Multi-user authentication.
- Permanent domain setup.
- Major UI redesign.
- Persistent taste profile.
- Feedback/rating system.

## Constraints

- Keep the app single-user and private.
- Do not expose `.env` values or tokens.
- Do not make Resonova publicly reachable unless explicitly approved later.
- Do not add native mobile app tooling.
- Do not change core product direction during this task.
- Prefer documentation and minimal config changes over infrastructure complexity.

## Success Criteria

The task succeeds when:

- The owner has clear steps to run Resonova on the PC and open it from the phone.
- The access path uses Tailscale or a justified fallback.
- The phone browser can reach the app URL.
- Basic mobile behavior is checked and documented.
- Any blockers are clearly described with evidence.
- No public exposure or secret leakage occurs.

## Validation Checklist

Check and report:

- PC Tailscale status and reachable Tailscale IP or MagicDNS name.
- Resonova server host/port binding needed for phone access.
- Phone browser URL used.
- Whether the landing page loads.
- Whether Spotify auth/session behavior is usable from phone.
- Whether existing episodes can be listed and replayed.
- Whether live generation is attempted or skipped, and why.
- Whether audio playback works.
- Whether screen lock/background behavior was tested.
- Any mobile layout issues.

## Expected Deliverable

Produce a handoff under:

```text
docs/handoffs/
```

Suggested filename:

```text
Private Phone Access Handoff.md
```

The handoff should include:

- Summary.
- Setup steps.
- Commands used.
- Phone URL.
- Validation results.
- Limitations.
- Candidate issues.
- Recommendation on whether browser remains sufficient for now.

## Recommended Manager Routing

Preferred manager:

```text
OCP Workspace Lead
```

Reason: this task is bounded infrastructure/product validation with a strong need to avoid scope creep into public deployment or native app work.

Use RUG only if the task turns into a concrete implementation/fix loop.

## Suggested Prompt To Paste Into A Manager Agent

```text
Use docs/boss/decisions/private-phone-access-brief.md as the parent objective and scope.

Set up or document private single-user phone access for the current Resonova local MVP using Tailscale first. The intended flow is:

PC runs Resonova
phone connects privately through Tailscale
phone opens the Resonova web UI in a mobile browser

This is not public deployment and not native app development.

Produce an evidence-backed handoff at docs/handoffs/Private Phone Access Handoff.md.

Preserve these constraints:
- Do not expose .env values or tokens.
- Do not make the app publicly reachable.
- Do not build a native iOS/Android app.
- Do not implement persistent taste profile or feedback features.
- Keep the task single-user and private.

Validate and document:
- PC Tailscale status or required setup.
- Reachable Tailscale IP or MagicDNS name.
- Resonova server binding/port needed for phone access.
- Phone browser URL.
- Whether the app loads on phone.
- Whether existing episodes can be listed/replayed.
- Any Spotify auth/playback limitations on mobile browser.
- Any screen-lock/background or layout limitations if tested.

If Tailscale is not installed or cannot be validated directly, document the exact missing prerequisite and provide the minimal next steps without expanding scope.

When complete, stop and return the handoff location plus a short summary. Do not start unrelated fixes.
```
