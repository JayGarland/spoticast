---
title: "Release Access and Memory Positioning Brief"
created: 2026-06-21
status: draft
owner_decision: "Current developer setup is a pre-release constraint, not the intended v0.1 user experience."
---

# Release Access and Memory Positioning Brief

Audience: Internal

## Purpose

Clarify how Resonova should position "owner-inspectable memory plus hosted music commentary" across product stages.

The current local setup is useful for a GitHub developer, but it is not the intended normal-user release shape.

## Owner Decision

Resonova should not be positioned long-term as a tool that normal users must self-host, configure with API keys, and run from a local development server.

Owner clarification, 2026-06-21:

Direct browser access for v0.1 does not reduce the original Resonova goal. The product baseline remains:

```text
the more a person uses Resonova, the better Resonova understands their taste, trails, context, and preferred commentary
```

Persistent memory, user profile, feedback, and Spotify-derived listening trails are not merely "future excitement." They are core to the Resonova direction. They may be sequenced after the v0.1 access path, but agents should keep them visible when planning.

Current setup is acceptable because the product has not truly released yet. At this stage, the expected user is a real human GitHub developer who can:

- clone the repo
- create `.env`
- run the server
- configure Spotify, Gemini, and optional Last.fm credentials
- understand local development constraints

For v0.1, the expected normal user should only need:

- a Spotify Premium account
- a way to connect Spotify
- a direct Resonova experience that works after connection

The user should not need to configure Gemini API keys, run a server, or understand local environment setup.

## Positioning Clarification

The durable product wedge is:

```text
personal, inspectable music memory + hosted AI commentary
```

Do not reduce this to:

```text
local developer app with local files
```

Local-first storage and owner-editable files are current implementation constraints and useful trust principles. They are not a permanent requirement that every released version must be self-hosted.

The v0.1 direction should preserve the spirit of inspectability:

- the user can understand what Resonova remembers
- the user can correct or clear memory
- the user can give feedback that changes future hosted commentary
- the user can authorize Spotify and let Resonova use permitted Spotify signals, such as recent plays, top tracks/artists, playlists, and playback context, to make commentary more personal
- the system does not hide all taste assumptions inside an opaque recommender

The exact storage model for released users is still open and should be decided later.

## Release Stages

### Current Pre-Release / Developer Stage

Audience:

- boss
- chef
- manager agents
- real human GitHub developers

Expected access:

- local repo
- local server
- `.env`
- developer-managed API keys

This stage is allowed to be inconvenient because the goal is product discovery, validation, and implementation.

### v0.1 Release Target

Audience:

- normal Spotify Premium users

Expected access:

- connect Spotify
- generate and listen directly
- no local server setup
- no user-managed Gemini API key
- no manual development configuration

The minimum released value should be hosted music commentary that feels personal and gets more useful from memory or feedback.

The preferred baseline for a new v0.1 test user is:

```text
open the browser site -> connect Spotify Premium -> authorize Resonova -> start listening
```

If a small persistent-memory/profile feature can be designed and implemented without delaying the access baseline or weakening reliability, it is aligned with the origin goal.

### Future Release Options

Future releases may add:

- subscription or paid access, because generation and TTS APIs are not free
- additional music or listening sources beyond Spotify
- user-controlled source connections
- memory export, reset, or edit controls
- more advanced profile and feedback features

These are future product decisions, not current implementation approvals.

## Guardrails

- Do not let current developer setup define the public user experience.
- Do not promise self-hosting as the main differentiator unless the boss explicitly chooses that market.
- Do not build cloud accounts, billing, or multi-source architecture before the boss approves that stage.
- Do not remove inspectability from the memory concept just because v0.1 should be easier to access.
- Do not require normal users to bring AI API keys for v0.1 unless the boss changes the release policy.
- Do not treat "memory not fully implemented yet" as permission to downscope the product into a stateless Spotify playlist tool.
- Do not silently collect or infer user trails without visible authorization, memory controls, and clear product purpose.

## Impact On Existing Strategy Docs

When older docs say `local-first`, read that as the current MVP constraint unless the doc explicitly discusses a released user experience.

When market positioning talks about "local, owner-inspectable memory," prefer this wording:

```text
inspectable personal music memory that can steer hosted AI commentary
```

This keeps the important differentiator without locking v0.1 into a developer-only deployment model.
