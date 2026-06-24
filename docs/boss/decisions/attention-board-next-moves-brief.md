---
title: "Attention Board - Next v0.1 Moves"
created: 2026-06-21
status: draft
audience: Boss
purpose: "Compare plausible next Resonova moves before boss-chef decision."
---

# Attention Board - Next v0.1 Moves

Audience: Boss

## Summary

This brief uses an "attention over moves" view: observe several plausible next moves together before choosing one.

It does not approve implementation. It is a boss-chef decision aid for the next 1-3 moves under the v0.1 roadmap.

Product baseline:

- Resonova is a personal AI radio companion, not a Spotify DJ clone.
- The current working value is hosted music commentary over Spotify playlists or pasted tracks.
- The durable product wedge is inspectable personal music memory that can steer hosted AI commentary.
- v0.1 should feel like direct use after Spotify connection, not self-hosting or user-managed AI API keys.
- Reliability and product-baseline truth should outrank feature excitement.

## Current Baseline

Latest gate:

- `docs/handoffs/Product Baseline Release Readiness Review.md` was accepted by chef as the current product/release-readiness gate.
- That review shifts top attention from playback controls to v0.1 access/onboarding shape plus memory-promise honesty.
- It confirms current source has Media Session, Previous/Pause/Next, observability, offline/bad-network handling, and saved-cast library behavior.

Verified current state:

- Media Session and in-app transport controls now exist in current source: `navigator.mediaSession`, `MediaMetadata`, `setActionHandler`, Previous, Pause/Resume, and Next are present in `resonova/web/player.js` and `resonova/web/index.html`.
- Older audits that say Media Session is absent are stale for current code, though their underlying mobile-reliability concern remains useful historical context.
- Current playback risk has shifted from "no controls" to "trust without verify": Spotify play can be accepted without confirmed audible progress, and mobile/network lifecycle evidence is still thin.
- The app still has no persistent taste profile or feedback loop. The profile/feedback layer is approved directionally, but it needs a design handoff before coding.
- The v0.1 access policy is clarified: current local setup is developer-stage only; normal users should not need local server setup or AI API keys.
- A known correctness bug remains in `resonova/server.py`: outro audio is still written to shared `/audio/outro.mp3`, so older saved episodes can replay the newest outro.

Unvalidated or incomplete:

- Real-phone intermittent Spotify playback still needs better observable evidence.
- The exact v0.1 hosting/account/billing/storage model is not decided.
- Inspectable memory behavior is not designed at implementation detail yet.
- Small UX honesty/polish items remain: landing memory copy, Windows hints, reduced motion/accessibility.

## Attention Matrix

| Candidate move | User value | Strategic fit | Evidence strength | Release risk | Cost | Dependency | Attention |
|---|---|---|---|---|---|---|---|
| v0.1 access/onboarding shape | High | High | High | High | Low as brief, high as build | Before release architecture | **Very high** |
| Small correctness/polish bundle | Medium | Medium | High | Low | Low | Can run in parallel if scoped | **High** |
| Playback observability + stall verification | High | High | High | Medium | Medium | Before more recovery logic | **High** |
| Persistent profile + feedback design | High | Very high | High | Medium | Low-medium | Before profile coding | **Very high** |
| Billing/subscription model | Future high | Medium | Medium | High | High | After v0.1 access decision | Park |
| Cloud accounts / hosted memory storage | Future high | Medium | Low-medium | Very high | High | After release architecture decision | Park |
| Multi-source expansion beyond Spotify | Future medium-high | Medium | Medium | High | High | After Spotify-first v0.1 | Park |
| PWA/native/interactive hosts | Future medium | Medium | Low-medium | High | High | After reliability + core memory | Park |

## Option Notes

### 1. Playback observability + stall verification

Why now:

- This is the strongest reliability move before adding more recovery behavior.
- Current code already has better controls, recovery, and Media Session, so the next risk is not missing controls; it is not knowing whether Spotify audio actually advanced.
- Better diagnostics protect boss testing time and prevent another speculative mobile patch cycle.

Why not now:

- It is still technical and may not visibly improve the product unless a real failure is reproduced.

Missing evidence:

- A real-phone failure timeline showing whether the problem is device loss, accepted-but-silent playback, offline/network, or page lifecycle.

Discussion candidate:

- Assign an implementation manager only for observability + stall verification, with a strict no-new-recovery-branches rule.

### 2. Persistent profile + lightweight feedback design

Why now:

- This is the strongest product-identity move.
- It makes "grows with your listening history" honest.
- It turns the market wedge into a designed product layer: memory the owner can inspect, correct, clear, and use to steer future commentary.

Why not code now:

- The profile schema, update policy, feedback attachment level, and prompt integration are still design questions.
- A rushed memory model could make the product harder to trust later.

Missing evidence:

- A manager-reviewed design handoff that specifies minimal data shape, feedback UX, prompt usage, and open owner decisions.

Discussion candidate:

- Send OCP a design-only task for persistent profile + feedback. Do not implement code in that task.

### 3. v0.1 access and onboarding shape

Why now:

- It prevents the wrong product positioning from hardening.
- v0.1 should mean connect Spotify and use Resonova directly, not clone repo + run server + bring Gemini keys.
- It clarifies that inspectability is the differentiator, not self-hosting.

Why not build now:

- Hosting, accounts, billing, storage, and cost recovery are non-trivial product and architecture decisions.
- The current product is still developer-stage and reliability/memory are more immediate.

Missing evidence:

- Decision brief for v0.1 release architecture options: hosted app, private beta shape, cost envelope, account model, and memory storage model.

Discussion candidate:

- Keep this as a product/release decision discussion, not an implementation assignment yet.

### 4. Small correctness/polish bundle

Why now:

- These are cheap, concrete improvements with strong evidence.
- They reduce trust leaks while bigger moves are being designed.
- The outro path bug is a real data-integrity issue.

Candidate bundle:

- Save outro audio inside each episode folder instead of shared `/audio/outro.mp3`.
- Reconcile landing copy so it does not promise implemented memory before profile work ships.
- Fix Windows-facing copy hints where needed.
- Add or verify reduced-motion/accessibility polish only where current source still lacks it.

Why not over-expand:

- This should stay a small RUG-style patch. It must not become a broad UI redesign or release-prep sweep.

Missing evidence:

- Fresh diff and validation after patch, because related frontend files have changed since older audits.

Discussion candidate:

- Approve a tightly scoped correctness/polish manager task if boss wants quick cleanup while larger decisions remain open.

## Boss-Chef Discussion Points

Recommended next discussion candidates:

1. Should v0.1 target a private hosted beta shape where users connect Spotify and do not bring AI API keys?
2. Should RUG receive a small correctness/honesty bundle now: outro path, memory-copy honesty, cross-platform setup/copy, and reduced-motion/accessibility verification?
3. Should blind-playback verification wait for one real-phone Diag/Copy-Timeline before any more recovery implementation?
4. Should OCP receive the persistent profile + feedback design-only handoff after access/copy honesty is settled?

Decisions not yet approved:

- No billing or subscription model.
- No cloud accounts or hosted-memory architecture.
- No multi-source implementation.
- No native app or PWA commitment.
- No interactive host conversation.
- No profile/feedback coding before a design handoff is accepted.

## Parked List

Park until boss-chef discussion explicitly reopens them:

- Subscription, billing, usage caps, and free-trial mechanics.
- Public release infrastructure and account system.
- Hosted memory storage model for normal v0.1 users.
- Multi-source support beyond Spotify.
- PWA/native packaging.
- Interactive "talk to your hosts" mode.
- Broad mobile recovery rewrites or retry loops.
- Any implementation that treats self-hosting as the v0.1 user promise.

## Chef Recommendation

Use the attention board this way.

Status update after boss steering and Phase 2 implementation:

1. **v0.1 access shape** is accepted as planning direction: private hosted owner/beta, direct browser use after Spotify connection, no normal-user API keys.
2. **Small correctness/polish bundle** has been implemented and needs boss/chef diff acceptance before commit.
3. Route **persistent profile + Spotify trails + feedback design** next so the origin goal stays central: Resonova should know the user better with continued use.
4. Use the current Diag/Copy-Timeline path to capture one real-phone blind-playback failure before assigning more recovery code.
5. Keep billing, public accounts, full hosted memory architecture, multi-source expansion, PWA/native, and broad recovery rewrites parked until explicitly reopened.
