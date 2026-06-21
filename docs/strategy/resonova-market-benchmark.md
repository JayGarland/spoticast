---
title: "Resonova Market Benchmark — Comparable Apps Specialist (Trial)"
created: 2026-06-21
status: draft
scope: "External comparable-app research. No code. No implementation tasks. Roadmap input only, routed back to recruiter/chef for gating."
role_boundary: "Comparable-app research, positioning, differentiation, memory/profile/feedback references. NOT implementation, release approval, architecture decisions, or auditor replacement."
---

# Resonova Market Benchmark — Comparable Apps Specialist (Trial)

## Executive Summary

Resonova is not a Spotify DJ clone, and the market makes that clearer, not less clear. Resonova's documented identity — "a personal AI radio companion that grows with your listening history" (`README.md`), with a parked-but-designed persistent taste profile and feedback layer (`docs/strategy/persistent-profile-feedback-brief.md`) — sits in a gap that none of the five benchmarked products fully occupy. The closest direct competitor, Spotify DJ, owns the "AI hosts + your music + commentary" space at massive scale but is cloud, account-based, single-voice, and gives the listener almost no durable control. The closest *format* analogy, NotebookLM Audio Overviews, owns the "two AI hosts discuss your material" space and has shipped exactly the two things Resonova currently only promises: real per-output customization and an interactive mode you can talk to.

The strategic read is that Resonova's defensible wedge is **depth of per-owner memory and editable taste that steers hosted music commentary** — the one thing platform incumbents structurally do not expose (they personalize from opaque models the user cannot inspect or edit). Current local-first storage is a pre-release/developer constraint, not the intended v0.1 normal-user setup; see `docs/strategy/release-access-and-memory-positioning-brief.md`. The market lessons reinforce the existing UX audit: the highest-fit next moves are the already-designed persistent profile + feedback layer and explicit "lenses" (mood/era/host style), because every successful comparable has converged on either *steerability* (Spotify Prompted Playlists, DJ voice requests, NotebookLM custom instructions) or *context-adaptation* (daylist, Endel) — and Resonova currently has neither beyond playlist shuffle.

What the market warns against is equally clear: do **not** chase Spotify DJ's single-celebrity-voice scale play, Endel's biometric/wearable real-time generation, or NotebookLM's general-source ingestion. Those are out of scope per the existing briefs and would dilute the personal-radio-for-music identity. This report ranks feature ideas strictly by fit with the documented direction and keeps Resonova's personal-first MVP constraints intact. No code changes are recommended; all items route back through recruiter/chef gating before they touch the roadmap.

---

## Method & Repo Anchors

This benchmark treats the existing repo strategy as the fixed product baseline, not an open question. The product goal, constraints, and parked items are taken from:

- `README.md` — "personal AI radio companion that grows with your listening history"; documented direction includes long-term taste profile, refreshable sessions, feedback loops, customizable lenses, future source expansion.
- `docs/strategy/resonova-mvp-audit-brief.md` — MVP = playlist → AI cast script → Gemini TTS → browser playback; product identity is broader than the MVP; Spoticast is the upstream base identity.
- `docs/strategy/persistent-profile-feedback-brief.md` — owner-approved move beyond one-shot casts toward persistent memory + lightweight feedback; current MVP constraints include **single-user, local-first, no cloud DB, no multi-user, no native mobile, inspectable/editable by owner.**
- `docs/strategy/release-access-and-memory-positioning-brief.md` — owner clarification that local developer setup is a pre-release constraint; v0.1 should let a normal Spotify Premium user connect and use Resonova directly without managing API keys or a local server.
- `docs/handoffs/External Product UX Design Audit Handoff.md` — confirms the app is still effectively stateless; landing copy over-promises "Listening memory"; investment ranking already puts Media Session/transport first, then profile+feedback, with comparable-app research explicitly *following* (not gating) the profile decision.

Each lesson below ties back to one of these anchors. Where a benchmark suggests something the briefs put out of scope, it is sent to "Park," not "Build."

Live products were verified against primary sources (Spotify Newsroom, Spotify Support, Google blog/Help, Endel) plus current (2025–2026) coverage; citations are inline and collected under Sources.

---

## Competitor / Product Map

The five benchmarks are not peers. They split cleanly into **direct competitors** (same job: AI-mediated personal music listening) and **analogy products** (adjacent jobs Resonova can borrow mechanics from without competing head-on).

| Product | Category | Core job | Personal memory model | Hosted voice/commentary | Owner control / steerability | Where it runs |
|---|---|---|---|---|---|---|
| **Spotify DJ** | Direct competitor | AI radio: your music + spoken commentary | Deep, opaque, server-side (Discover/Daily Mix engines); adapts within a session to skips/saves | Yes — single branded voice ("X"), now multi-language | Low → growing: real-time **voice requests** added 2025 | Cloud, account-bound |
| **Spotify AI / Prompted Playlists** | Direct competitor (adjacent surface) | Turn a text prompt into a personalized, self-refreshing playlist | Server-side taste model; "steer the algorithm" framing | No spoken host — text prompt only | **High** — explicit prompt rules, "steer," now spans podcasts | Cloud, account-bound |
| **Spotify daylist** | Direct competitor (adjacent surface) | Context/time-of-day refreshing playlist with evocative names | Server-side; keyed to time + recurring micro-genre habits | No host (hyper-specific titles only) | Low — automatic, not steerable | Cloud, account-bound |
| **NotebookLM Audio Overviews** | Analogy product (format twin) | Two AI hosts discuss *your provided sources* | None of "you" — memory is the uploaded sources, per notebook | Yes — two hosts, multiple formats (Deep Dive/Brief/Critique/Debate) | **High** — custom instructions, tone/length, **Interactive Mode (talk to hosts)** | Cloud |
| **Endel** | Analogy product (adaptation twin) | Functional, real-time-adapting soundscapes for focus/sleep | Builds a listener profile from context + biometrics; adapts on-the-fly | No (generative ambient, not commentary) | Indirect — you pick a mode; engine adapts to context/biometrics | App + cloud, wearable inputs |

**Direct competitors** (Spotify DJ, AI/Prompted Playlists, daylist) compete with Resonova for the same listener moment. **Analogy products** (NotebookLM, Endel) do a different job but have solved mechanics Resonova wants: two-host hosted audio with real customization (NotebookLM) and context-driven adaptation of an audio stream (Endel).

The crucial structural fact: **all three direct competitors are cloud, account-bound, and personalize from models the listener cannot see or edit.** Resonova's owner-inspectable taste profile is therefore not a weaker version of the same thing — it is a different axis the incumbents do not expose. The released product should keep this inspectability while avoiding developer-only setup for normal users.

---

## What Resonova Should Learn

**1. Steerability is now table stakes, and it is Resonova's nearest gap.** (anchor: README "feedback loops," "customizable lenses"; UX audit UX-1/strategy findings)
Every direct competitor has moved toward letting the listener *direct* the output: Prompted Playlists are explicitly pitched as "you're in control / steer the algorithm" ([Spotify Newsroom, Dec 2025](https://newsroom.spotify.com/2025-12-10/spotify-prompted-playlists-algorithm-gustav-soderstrom/)), and DJ now takes spoken requests ([Spotify Newsroom, May 2025](https://newsroom.spotify.com/2025-05-13/dj-voice-requests/)). NotebookLM exposes custom instructions plus tone/length controls ([TechCrunch, Sept 2025](https://techcrunch.com/2025/09/03/googles-notebooklm-now-lets-you-customize-the-tone-of-its-ai-podcasts/)). Resonova today offers only Skip-forward and a single static persona prompt (UX audit). The market lesson: ship **lenses** (mood / era / host tone / analysis depth) — already named in the README — as the cheapest credible step toward steerability. This is product-shaped, not a rebuild.

**2. A persistent, *editable* taste profile is a real differentiator — lean into "inspectable."** (anchor: persistent-profile-feedback-brief constraints "inspectable/editable by owner")
Spotify's personalization is powerful but a black box; users cannot open or correct it. Resonova's brief already mandates an inspectable, owner-editable taste profile for the current MVP. That is not a constraint to apologize for — it is the one thing no incumbent offers and the strongest reason for an owner to prefer Resonova to Spotify DJ. Learn from NotebookLM that *visible, controllable* AI behavior is itself the feature people praise. For v0.1, preserve inspectability without requiring the user to self-host or bring AI API keys.

**3. Lightweight feedback is the mechanism that makes "grows over time" true.** (anchor: persistent-profile-feedback-brief; UX audit UX-1 "promises memory it does not have")
Spotify DJ adapts within a session from skips/saves/duration ([Spotify Debuts AI DJ, 2023](https://newsroom.spotify.com/2023-02-22/spotify-debuts-a-new-ai-dj-right-in-your-pocket/)). Resonova can do the durable, cross-session version that DJ does *not* expose: thumbs up/down per episode or segment written to `feedback.jsonl`, feeding the next generation's prompt. This directly closes the landing-copy honesty gap the UX audit flagged (UX-1). Build the smallest version first, exactly as the brief scopes it.

**4. Two-host hosted audio benefits enormously from format/tone presets and an interactive mode — and Resonova already has the two-voice engine.** (anchor: README two AI hosts; MVP audit)
NotebookLM's most-praised 2025 additions were format presets (Deep Dive/Brief/Critique/Debate) and Interactive Mode where you talk back to the hosts ([NotebookLM Help](https://support.google.com/notebooklm/answer/16212820), [TechCrunch](https://techcrunch.com/2025/09/03/googles-notebooklm-now-lets-you-customize-the-tone-of-its-ai-podcasts/)). Resonova already synthesizes two voices in one pass; a "Brief vs. Deep Dive" commentary-length lens is a near-free borrow that maps onto the README's "analysis depth" feedback dimension. Interactive "talk to your hosts" is a compelling *future* north-star but is heavier (real-time loop) — note it, don't rush it.

**5. Context-as-a-lens is a proven hook — borrow the framing, not the sensors.** (anchor: README "refreshable sessions based on recent listening, playlists, and library context")
daylist's appeal is time/context-sensitive refresh with evocative, identity-flattering titles ([Spotify Newsroom, daylist](https://newsroom.spotify.com/2023-09-12/ever-changing-playlist-daylist-music-for-all-day/)); Endel adapts to time-of-day/weather/activity ([Endel technology](https://endel.io/technology)). Resonova can offer *context lenses the owner chooses* (morning / late-night / road-trip-memory / focus) — using listening context it already fetches — without any biometric or sensor dependency. The lesson is the **framing** (a session that feels tuned to *this moment*), achieved with existing inputs.

**6. Evocative naming and shareable identity are cheap perceived-quality wins.** (anchor: UX audit D-1 "cohesive, on-identity visual system")
daylist's hyper-specific auto-generated titles drove its virality. Resonova already generates episode titles (the UX audit saw *Drifting Through Stardust*, *Slowcore Echoes*). Doubling down on owner-flattering, moment-specific episode naming is on-brand and effectively free.

---

## What Resonova Should Avoid

**1. Don't compete as a "Spotify DJ clone."** (fail condition guard; anchor: MVP audit product identity)
Resonova cannot and should not match DJ's scale, single-celebrity voice, or cloud recommendation engine. Trying to out-Spotify Spotify on its own axis is a losing race. Resonova wins on the orthogonal axis (owner-inspectable memory + multi-voice hosted depth), not on catalog or scale.

**2. Don't adopt Endel's biometric/wearable real-time generation.** (anchor: persistent-profile-feedback-brief out-of-scope: no complex ML pipeline, single-user local)
Endel's heart-rate/motion-driven, neural real-time synthesis ([gobeyond.ai case study](https://www.gobeyond.ai/ai-resources/case-studies/endel-ai-personalized-soundscapes-music)) is a different product class with heavy device, sensor, and infra requirements. It is squarely outside the local-first, simple-MVP constraints. Borrow the *idea of context*, not the sensor stack.

**3. Don't generalize into NotebookLM's "any source" territory.** (anchor: README scope = music; brief "do not replace Spotify/Last.fm integrations")
NotebookLM ingests arbitrary documents. Resonova's identity is *music radio*. Expanding to general source ingestion would blur the personal-music-companion positioning that is the product's biggest asset (UX audit D-1). Future source expansion (README) means *more music sources*, not documents/podcasts-about-anything.

**4. Don't build cloud accounts / multi-user to "match" the incumbents before the release stage requires it.** (anchor: persistent-profile-feedback-brief constraints; UX audit "keep parked: multi-user/cloud"; release-access brief)
The current MVP should stay local and simple while the product is unreleased. For v0.1, the user experience should be direct connection and use, not developer setup. Any future account, subscription, billing, or hosted-memory design needs a separate boss-chef decision.

**5. Don't let comparable-app research gate or trigger a rebuild.** (fail condition guard; anchor: UX audit "comparable-app research as a gating step → keep parked")
The UX audit is explicit: comparable-app research should *follow*, not precede, the profile decision, and broad rebuild/native/cloud is not justified by evidence. This report is roadmap *input*, not a mandate to build.

---

## Product Positioning Implications

Resonova's defensible position, sharpened by the benchmark, is:

> **"Your own AI radio hosts who actually remember you — with a taste profile you can inspect, correct, and use to steer future shows."**

Three positioning pillars fall out of the map:

**Pillar A — Owned & inspectable memory (vs. Spotify's black box).** The incumbents personalize from models you cannot see. Resonova's editable profile is the differentiator. Positioning language should emphasize *ownership and transparency of taste*, not "more accurate recommendations" (a race Spotify wins). Do not position v0.1 around local developer setup.

**Pillar B — Hosted depth, not just curation (vs. Prompted Playlists / daylist).** Spotify's prompt and daylist surfaces produce *playlists*; Resonova produces *a hosted show about your music* with two voices, trivia, production stories, and connections. Position against the playlist tools on *narrative depth and companionship*, not track selection.

**Pillar C — Personal companion, not a general AI tool (vs. NotebookLM).** NotebookLM is a productivity/research tool that happens to make audio. Resonova is a *companion for your music life*. The same two-host mechanic, pointed at a fundamentally warmer, identity-driven job.

The honest near-term caveat (straight from the UX audit): the landing page currently *claims* memory it doesn't have. Positioning and product must converge — either soften copy now or ship the minimal profile so the claim is true. The benchmark strengthens the case for shipping it, because "memory you can edit" is the single line that differentiates Resonova from all five products.

---

## Feature Ideas, Ranked by Fit With Documented Direction

Ranked by fit with the *existing* Resonova briefs (not raw market appeal). "Fit" = directly named in README/briefs and preserves current MVP constraints unless a later release decision changes them. This is prioritization, not a wishlist.

**Tier 1 — Highest fit, build candidates (already in the briefs; market validates urgency):**

1. **Lenses: mood / era / host tone / analysis depth selector.** Directly named in README ("customizable lenses"); the market's clearest convergence point (Prompted Playlists, NotebookLM custom instructions, DJ requests). Highest fit-to-effort. *Borrowed from: Prompted Playlists + NotebookLM formats.*
2. **Persistent editable taste profile (`taste_profile.json`) read into generation.** The core of the persistent-profile brief; makes the tagline honest (UX-1); the unique-vs-incumbents feature. *Borrowed from: the gap Spotify leaves open.*
3. **Lightweight per-episode / per-segment feedback (`feedback.jsonl`) feeding the next prompt.** The mechanism that operationalizes "grows over time"; scoped small in the brief. *Borrowed from: DJ's skip/save adaptation, made durable + cross-session.*

> Note: Tiers 1–3 are *product* candidates. The UX audit independently sequences **Media Session + index-based queue + transport controls** as the immediate engineering milestone *before* profile work, because previous/resume and the queue refactor unblock everything. That ordering is an engineering/auditor call, not this specialist's — flagged here only so the roadmap doesn't read profile work as "first thing to code."

**Tier 2 — Strong fit, build later (named or strongly implied; modest effort):**

4. **Commentary-length presets (Brief vs. Deep Dive).** Maps to README "analysis depth"; near-free given two-voice engine already exists. *Borrowed from: NotebookLM formats.*
5. **Owner-chosen context lenses (morning / late-night / road-trip / focus).** Uses listening context already fetched; no sensors. *Borrowed from: daylist + Endel framing, sensor-free.*
6. **Richer episode naming + lightweight shareable episode identity.** On-brand, cheap perceived quality. *Borrowed from: daylist titles.*

**Tier 3 — Interesting, lower fit / defer (heavier or adjacent to constraints):**

7. **Interactive "talk to your hosts" mode.** Compelling north-star (NotebookLM Interactive Mode), but a real-time conversational loop is heavy and beyond the simple-MVP constraint. Park as a *vision* item, revisit after profile/feedback prove out.
8. **Taste-/flow-aware ordering (energy arc, "open strong") beyond random shuffle.** The UX audit notes current shuffle is uniform-random; a flow-aware pass is a natural later refinement once a profile exists. Defer until profile lands.

---

## What Should Stay Parked

Consistent with the existing briefs and the UX audit's parked list:

- **Biometric / wearable real-time adaptation (Endel-style).** Out of scope; violates local-first/simple-MVP constraints.
- **General non-music source ingestion (NotebookLM-style).** Dilutes the music-companion identity.
- **Cloud accounts / multi-user / public deployment before release approval.** Explicitly out of scope for current MVP work. For v0.1, direct use without user-managed API keys is a product target, but the account/billing/storage design is not yet approved.
- **Native mobile app / broad mobile-playback hardening loops.** Parked in the UX audit (history of reverted recovery loops); Media Session is the sanctioned mobile lever, not native packaging.
- **Single-celebrity-voice scale strategy.** Not a fit for a single-owner local product.
- **Comparable-app research as a *gating* step for the profile decision.** Per UX audit, research informs but must not block or trigger rebuild — this report is input only.
- **Interactive real-time host conversation.** Parked as vision (see Tier 3).

---

## Role-Boundary & Handoff Note

This is a specialist *trial* deliverable, used for comparable-app research, positioning, differentiation, and memory/profile/feedback references only. It does **not** approve any release, decide architecture, choose implementation order, or replace the internal auditor / product reviewer. Engineering sequencing (e.g., Media Session and the queue refactor before profile coding) remains the auditor's/owner's call. All build candidates above are roadmap inputs that should route back to recruiter and chef for gating before they affect the roadmap. No code was written or changed.

---

# Addendum — Release & Access Positioning (v0.1 normal-user direct use)

*Added 2026-06-21. Narrow steering supplement requested by boss/chef. Anchored to `docs/strategy/release-access-and-memory-positioning-brief.md`. This does not redo the benchmark, does not reopen the "Spotify DJ clone" question, does not change implementation order, and approves no cloud accounts, billing, subscriptions, or multi-source architecture. Roadmap/release-positioning input only.*

**Framing correction absorbed.** The body of this report described the wedge as "local, owner-inspectable memory." Per the release brief, *local-first is a current pre-release/developer constraint, not the intended v0.1 user experience.* The durable wedge is restated as **inspectable personal music memory that can steer hosted AI commentary** — inspectability is the principle to preserve; self-hosting is not. Today's expected user is a real GitHub developer (clone, `.env`, keys, local server); v0.1's expected user has only a Spotify Premium account and connects directly.

### 1. What v0.1 user setup should feel like
Like Spotify DJ or daylist: open, connect one account, get value in the first session — zero key management, zero server. The whole category has set the expectation that AI-audio personalization is a *toggle inside an app you already use*, not a thing you configure. The current developer flow (keys + local server) is fine *only* because the product is pre-release; it should not leak into the v0.1 surface. Concretely, v0.1 onboarding should be: connect Spotify → generate → listen, with the Gemini/TTS plumbing invisible to the user.

### 2. Does "connect Spotify only" match category expectations?
Yes, and it is the strongest available default. Spotify DJ and daylist require nothing but the existing Spotify account (DJ requires Premium, which Resonova already requires for the Web Playback SDK — so no *new* gate for the target user) ([Spotify Support — DJ](https://support.spotify.com/us/article/dj/)). NotebookLM requires only a Google sign-in; Endel only an app install. No comparable in this category asks a normal user to bring an AI/API key — that is exclusively a developer-tool pattern. So "connect Spotify only" is not just acceptable, it is the category norm. The honesty caveat from UX-1 still applies: don't promise memory the released build doesn't yet deliver.

### 3. How comparables hide, expose, or recover generation cost
All of them **hide generation cost behind an account the user already pays for or already has**, and none expose per-generation cost to the user:
- **Spotify DJ / Prompted Playlists / daylist** — cost is absorbed into the existing **Premium subscription**; the AI is a Premium perk, not a separately metered product ([Spotify Newsroom — DJ](https://newsroom.spotify.com/2023-02-22/spotify-debuts-a-new-ai-dj-right-in-your-pocket/)).
- **NotebookLM** — generation is **free with a Google account up to daily limits**; paid Google AI/Workspace/Cloud plans raise limits rather than making Audio Overviews a bring-your-own-key feature ([NotebookLM upgrade limits](https://support.google.com/notebooklm/answer/16213268), [NotebookLM Pro plans](https://notebooklm.google/plans)).
- **Endel** — direct **freemium subscription**: short free sessions as a taste, a 7-day free trial for the full version, and Premium for unlimited access ([Endel free trial / free version](https://endel.zendesk.com/hc/en-us/articles/360010523860-You-want-to-enjoy-Endel-for-free), [Endel premium](https://payment.endel.io/)).
The lesson for Resonova: the released user should never see "you used $0.04 of Gemini." Cost recovery, when it comes, should sit behind a subscription or a daily free allowance — not bring-your-own-key for normal users.

### 4. Subscription / free-trial / usage-cap / bring-your-own-key patterns
Three viable patterns appear, ranked by fit with the brief's "normal user, no keys" guardrail:
- **Daily free allowance + paid tier for volume (NotebookLM model).** Highest fit for an expensive-per-generation product: the feature is always free to try, you pay only to generate more. Maps naturally onto Resonova's costly TTS/script step (e.g., N free casts/day, more behind a plan). *Borrow as the default mental model.*
- **Bundled-into-existing-subscription (Spotify model).** Cleanest UX but not available to Resonova — Resonova isn't the subscription the user already holds. *Note as the ideal the user is anchored on; can't be copied directly.*
- **Freemium subscription with trial (Endel model).** Standard, works, but front-loads a paywall. *Acceptable later fallback.*
- **Bring-your-own-key.** This is the *current developer* mechanism and, per the brief's guardrail, must **not** be required of normal users in v0.1. *Park as developer-only.*
The brief explicitly defers the choice; this addendum only maps the options, recommends none for build, and approves no billing.

### 5. How comparables handle sources beyond the first
- **Spotify** stays inside its own walled catalog and expands by *content type, not provider* — Prompted Playlists grew from music to **podcasts** within Spotify, no second account connected ([Spotify Newsroom, Apr 2026](https://newsroom.spotify.com/2026-04-07/prompted-playlist-for-podcasts-launch/)).
- **NotebookLM** is the multi-source model: the user *explicitly adds* each source (Docs, PDFs, links) per notebook — connection is user-driven and visible.
- **Endel** adds *input* sources (Apple Health/Watch context), not content libraries.
Lesson: when Resonova eventually expands beyond Spotify (README "future source expansion"), the credible pattern is **user-initiated, visible, opt-in source connections** (NotebookLM-style), with each source clearly owned by the user — *not* silent backend aggregation. But this is a future stage; the brief forbids building multi-source architecture now, so this is positioning guidance only.

### 6. How memory / privacy / edit / reset controls are positioned
This is where Resonova can lead, and it survives the local→hosted reframing intact. Incumbents personalize from **opaque server-side models the user cannot open, correct, or reset** — Spotify's taste model is a black box; daylist just happens *to* you. NotebookLM is transparent only because its "memory" is the visible sources you uploaded, and it offers no persistent *taste* memory of you at all. So no benchmarked product offers an **inspectable, correctable, resettable model of the user's taste**. The brief preserves exactly this as the wedge: the v0.1 user should be able to see what Resonova remembers, correct it, clear it, and give feedback that changes future commentary — *without* that requiring local files. Position it as "memory you can read and edit," a privacy/trust feature, not as "self-hosting."

### 7. Borrow / Avoid / Park
**Borrow (positioning, not build):**
- One-tap "connect Spotify, then it just works" onboarding as the v0.1 north star (Spotify DJ / daylist norm).
- NotebookLM's **always-free-to-try, pay-for-volume** cost framing as the default when cost recovery is eventually needed.
- NotebookLM's **user-initiated, visible source-add** pattern as the future multi-source shape.
- Transparent, editable, resettable **taste memory** as the lead differentiator — reframed from "local" to "inspectable."

**Avoid:**
- Requiring normal users to bring a Gemini/TTS API key (developer-only; brief guardrail).
- Marketing v0.1 as "self-hosting" or "local app" — the brief says don't position self-hosting as the differentiator unless the boss explicitly chooses that market.
- Exposing raw per-generation cost to users.
- Copying Spotify's "bundled, invisible, free-feeling" model literally — Resonova lacks the host subscription to bundle into.

**Park (future stage, needs boss approval — no build now):**
- Subscriptions, billing, usage caps, free-trial mechanics.
- Cloud accounts / hosted storage model for released-user memory (storage model is explicitly left open in the brief).
- Multi-source / second-provider connections.
- Any decision on which cost-recovery pattern to adopt.

**Net steering line for the boss/chef:** v0.1 = *connect Spotify, listen, and see/edit what it remembers* — developer setup and key management stay strictly pre-release; cost-recovery and multi-source are real but parked future stages; the differentiator is **inspectable taste memory**, reframed away from "local/self-hosted."

---

## Sources

- Spotify DJ — debut & how it works: [Spotify Newsroom, Feb 2023](https://newsroom.spotify.com/2023-02-22/spotify-debuts-a-new-ai-dj-right-in-your-pocket/) · [Spotify Support — DJ](https://support.spotify.com/us/article/dj/)
- Spotify DJ — voice requests (2025): [Spotify Newsroom, May 2025](https://newsroom.spotify.com/2025-05-13/dj-voice-requests/) · [Music Ally, May 2025](https://musically.com/2025/05/14/spotify-listeners-can-now-talk-back-to-its-ai-dj-with-requests/)
- Spotify DJ — language/market expansion (2026): [Spotify Newsroom, May 2026](https://newsroom.spotify.com/2026-05-07/dj-expansion-4-new-languages/)
- Spotify AI Playlist (original beta): [Spotify Newsroom, Apr 2024](https://newsroom.spotify.com/2024-04-07/spotify-premium-users-can-now-turn-any-idea-into-a-personalized-playlist-with-ai-playlist-in-beta/)
- Spotify Prompted Playlists — support & "steer the algorithm": [Spotify Support — Prompted Playlists](https://support.spotify.com/us/article/prompted-playlists/) · [Spotify Newsroom, Dec 2025](https://newsroom.spotify.com/2025-12-10/spotify-prompted-playlists-algorithm-gustav-soderstrom/) · [TechCrunch, Dec 2025](https://techcrunch.com/2025/12/10/spotify-tests-more-personalized-ai-powered-prompted-playlists/)
- Spotify Prompted Playlists — podcasts expansion (2026): [Spotify Newsroom, Apr 2026](https://newsroom.spotify.com/2026-04-07/prompted-playlist-for-podcasts-launch/)
- Spotify daylist: [Spotify Newsroom, Sept 2023](https://newsroom.spotify.com/2023-09-12/ever-changing-playlist-daylist-music-for-all-day/) · [Axios, Sept 2024](https://www.axios.com/2024/09/04/spotify-daylist-feature-globally-viral)
- NotebookLM Audio Overviews — launch & help: [Google Blog](https://blog.google/technology/ai/notebooklm-audio-overviews/) · [NotebookLM Help](https://support.google.com/notebooklm/answer/16212820)
- NotebookLM — customization, formats & Interactive Mode (2025): [TechCrunch, Sept 2025](https://techcrunch.com/2025/09/03/googles-notebooklm-now-lets-you-customize-the-tone-of-its-ai-podcasts/) · [Google Workspace Updates, Apr 2025](https://workspaceupdates.googleblog.com/2025/04/language-expansion-audio-overviews-notebooklm.html)
- Endel: [Endel](https://endel.io/) · [Endel — technology](https://endel.io/technology) · [App Store — Endel](https://apps.apple.com/us/app/endel-focus-sleep-sounds/id1346247457) · [gobeyond.ai case study](https://www.gobeyond.ai/ai-resources/case-studies/endel-ai-personalized-soundscapes-music)

### Addendum sources (release & access positioning)
- NotebookLM free-vs-paid access and limits: [Google NotebookLM Help — upgrade limits](https://support.google.com/notebooklm/answer/16213268) · [NotebookLM Pro plans](https://notebooklm.google/plans)
- Endel freemium, free trial, and premium access: [Endel Help — free trial / free version](https://endel.zendesk.com/hc/en-us/articles/360010523860-You-want-to-enjoy-Endel-for-free) · [Endel — Get Premium](https://payment.endel.io/)
- Spotify Premium-bundled AI: [Spotify Newsroom — DJ debut](https://newsroom.spotify.com/2023-02-22/spotify-debuts-a-new-ai-dj-right-in-your-pocket/) · [Spotify Support — DJ](https://support.spotify.com/us/article/dj/)
- Spotify source expansion (music → podcasts): [Spotify Newsroom, Apr 2026](https://newsroom.spotify.com/2026-04-07/prompted-playlist-for-podcasts-launch/)

### Internal repo anchors (product baseline)
- [README.md](F:/GitHub/resonova/README.md)
- [docs/strategy/resonova-mvp-audit-brief.md](F:/GitHub/resonova/docs/strategy/resonova-mvp-audit-brief.md)
- [docs/strategy/persistent-profile-feedback-brief.md](F:/GitHub/resonova/docs/strategy/persistent-profile-feedback-brief.md)
- [docs/strategy/release-access-and-memory-positioning-brief.md](F:/GitHub/resonova/docs/strategy/release-access-and-memory-positioning-brief.md)
- [docs/handoffs/External Product UX Design Audit Handoff.md](F:/GitHub/resonova/docs/handoffs/External%20Product%20UX%20Design%20Audit%20Handoff.md)
