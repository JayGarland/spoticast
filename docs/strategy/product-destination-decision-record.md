---
title: "Decision Record — Product Destination"
created: 2026-06-23
status: accepted
audience: Boss / Chef / Internal
decision_owner: Boss
relates_to:
  - docs/strategy/v0.1-access-shape-decision-record.md
  - docs/strategy/v0.1-access-shape-decision-brief.md
  - docs/strategy/release-access-and-memory-positioning-brief.md
  - docs/strategy/v0.1-roadmap.md
---

# Decision Record — Product Destination

## Boss Decision (2026-06-23)

The ultimate product destination for Resonova is **Option C: a public hosted app with
user accounts, access controls, and cost recovery.**

The three access options from `v0.1-access-shape-decision-brief.md` are now clarified
as a sequenced roadmap, not competing alternatives:

| Step | Access Shape | Purpose |
|------|-------------|---------|
| **Option A (done)** | Developer local self-hosted alpha | Internal checkpoint, code validation, developer audience. Bring your own keys. |
| **Option B (next)** | Private hosted owner/beta instance | Owner + small trusted testers. Platform-managed API keys. Direct browser access. |
| **Option C (ultimate)** | Public hosted app with accounts and billing | Normal Spotify Premium users. Subscription or quota-based cost recovery. Full hosted memory and profile per user. |

## What This Means

- Option A is complete. The developer alpha checkpoint is tagged at `v0.1-alpha-developer`.
- Option B is the current engineering target. It is not yet started. It is the bridge between
  the local MVP and a normal-user hosted experience.
- Option C is the destination. All product, memory, feedback, and identity work should be
  designed with Option C in mind — even when the current build is Option A or B.

## Implications for Design and Architecture

Agents, managers, and chefs should read this decision when:

- Designing the persistent profile or memory storage model. Storage must eventually
  support per-user hosted data, not only local files.
- Designing the Spotify OAuth flow. The redirect URI and token handling must eventually
  support a multi-user hosted environment.
- Designing feedback and profile update flows. These should be scoped to work
  single-user locally now, but designed to migrate to a hosted per-user model later.
- Writing copy, README text, or product positioning. The product destination is a public
  personal AI radio companion — not a developer tool or a self-hosted app.

## What Is Still Parked

This decision does not approve implementation of Option C components today. The
following remain parked until explicitly reopened by boss/chef:

- Public account system (registration, login, identity management).
- Billing, subscription, quota, payment integration.
- Hosted multi-user memory storage architecture.
- Full cloud database for per-user profiles and feedback.
- Public launch or marketing.

## Relationship to Existing Guardrails

The existing parked list in `v0.1-roadmap.md` and `persistent-profile-feedback-brief.md`
remains valid for current implementation work. This record adds forward context only:
those guardrails exist to avoid building Option C prematurely, not to prohibit it
permanently.

The product direction from `release-access-and-memory-positioning-brief.md` is unchanged:
the durable wedge is inspectable personal music memory that steers hosted AI commentary.
Option C is the release shape that makes that wedge available to normal users at scale.

## Option B Completion Gate

Option B must be designed and implemented before Option C work begins. At minimum,
Option B requires:

- A hosted server environment running the Resonova backend.
- Platform-managed Gemini/TTS API key handling (users do not bring their own keys).
- Spotify OAuth configured for a stable production domain (not localhost).
- A cost guard or per-session quota to protect API spend during validation.
- Single-user or invite-only access control during beta.

No Option C design or implementation should begin before Option B is validated with
at least one real non-developer user session.
