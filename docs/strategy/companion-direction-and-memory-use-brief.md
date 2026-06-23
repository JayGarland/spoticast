# Companion Direction & Memory-Use Discussion Brief

Audience: Boss + Agents (product reviewer, auditor, chef, managers)
Status: Superseded in part by the 2026-06-23 bounded personal music narrator pivot.
Records the boss's words on 2026-06-21 and the shipped Stance-B baseline.

## 0. Baseline (do not forget)

Resonova is a **personal AI radio companion that should understand the listener better the
more they use it.** Every decision below must be checked against this baseline. The point of
the memory layer is not data collection — it is a companion that grows with the user.

## 0.1 Pivot Update (2026-06-23)

Decision record: `docs/strategy/bounded-personal-music-narrator-pivot.md`.

Boss and Chef aligned on a product-direction pivot after reading the boss-curated
research in `docs/research/`: **Strict Stance B is the shipped safety baseline,
not the final product soul.** The target direction is **bounded Stance C: a
private music-memory narrator**.

The updated distinction:

- **Strict B = current safety baseline.** Third-person, descriptor-only taste
  acknowledgment remains the shipped behavior.
- **Bounded C = product direction.** Direct "you" and bounded music-domain
  episodic callbacks may be used when grounded in the current playlist and
  inspectable/resettable memory.
- **Unbounded C = banned.** No cross-domain ChatGPT-style bleed, no unrelated
  personal callbacks, no raw inventory recital, and no private memory in shared
  or public casts.

## Locked Decisions (2026-06-22)

- **Companion stance: Option B (taste-as-a-lens / semantic) now; Option C (bounded episodic) later
  as an explicit experiment.** Hosts may acknowledge taste via *derived descriptors* ("leans to the
  quiet end"), never the user's own artist-name *inventory* (descriptor-not-inventory, per the
  privacy audit) and never cross-cast history. Requires a style-derivation source first (see §4 and
  the style-source note). Locked after both quality passes (product review + privacy audit).
  **SUPERSEDED IN PART (2026-06-23):** this remains the shipped Stance-B baseline, but bounded
  music-domain episodic narration is now accepted as the product direction rather than merely a
  later optional experiment.
  **CHECKPOINT RESOLVED (2026-06-22):** Option B confirmed from four angles — the boss's lean, both
  quality passes, the boss-curated research export
  (`docs/research/AI Companion Personalization and Trust.md`), and a customer's
  jump-scare concern (hosts "turning to" the listener feels scary — that's stance C, which B avoids).
  Implemented in `gemini.py` with a **fourth-wall-preserving** guardrail: a rare, light, third-person,
  playlist-grounded taste nod framed as the hosts' own observation about the music — NEVER "you",
  inventory, history, playlist-contradiction, or turning to the listener. The old "C is rejected"
  wording is superseded: **unbounded C is rejected; bounded C is the target direction.** A/B/C as
  user-selectable modes remain not built. Pending: boss listens to real casts to calibrate how much
  personal narration feels right.
- **Per-user isolation: enforce single-user now.** Lock the instance to the owner's Spotify
  identity — do not auto-populate/merge a second connecting account. This addresses the audit's
  Critical cross-user bleed before any second tester connects. Full per-user isolation (profile/
  token keyed per Spotify id) is deferred as a manager task. **A visible owner indicator in the UI
  is bundled with that user-management/isolation work (boss decision 2026-06-22), not added
  standalone now** — the silent guard already protects.
- **Still open:** the memory-control model (§3.2); the disable/reset fixes (depend on §3.2); the
  style-derivation implementation; field cleanup (deferred until the above settle).

## 1. Boss observation (2026-06-21): the cast doesn't reference the user

The boss generated a new cast. The hosts did **not** mention anything about the user and did
**not** break the fourth wall. This is currently **by design**: the prompt guardrail
(`resonova/api/gemini.py`, "music knowledge show, not a listener profile show" / "never
narrate the listener's habits aloud") makes the hosts perform to a generic radio audience.

Consequence to discuss: the memory we now collect only **steers commentary invisibly**
(angle, tone, what's interesting) — it never **surfaces** to the user. So the companion can be
informed by the profile yet still not *feel* like it knows the listener. The boss's
"knows-me-better" intention and the current invisible-steering stance need to be reconciled.

## 2. The two memory layers (already in repo, restated for the discussion)

Memory has two sources feeding one profile (see the persistent-profile design handoff):

- **Layer A — Resonova-owned activity:** the user's behaviour *inside* Resonova — saved casts,
  replays, repeated playlists, and (built) explicit feedback. No extra permission; grows with use.
- **Layer B — Spotify activity:** the user's behaviour *on Spotify* — top/recent, saved library
  (recency-weighted), followed artists. Rich from a single authorization.

Both are real and partly built. The open question is not *what* we collect but *how the
companion uses it in the listener's actual experience*.

## 3. CENTRAL OPEN DECISION — host awareness / the fourth wall

The companion's fixed position is **personal**: the hosts exist *for the user*. The undecided
question (boss-posed): **should the hosts be aware of the user?** Do they know there is an
audience — and that it is a single audience, the listener — or do they perform to no one in
particular? Spectrum to choose from:

1. **Invisible steering only (current).** Memory shapes content; hosts never reference the
   listener. Safest, never creepy — but the user cannot feel the companion knowing them.
2. **Tasteful acknowledgment.** Hosts occasionally, lightly acknowledge the single listener and
   their history ("you've been leaning ambient lately") without reciting data. Companion warmth;
   risk of feeling invasive if overdone.
3. **Direct companion.** Hosts clearly address the user as a known individual, with callbacks to
   past casts and taste. Strongest "knows me" feel; highest creepiness/privacy risk.

This decision drives prompt design, the value of the memory layer, and the product's soul. It
must be resolved with the product team before more memory features are built, and re-checked
against the baseline and against "not creepy."

### Boss lean (2026-06-21): tasteful, but no cross-cast memory bleed

The boss leans toward **(2) tasteful acknowledgment — "a bit"**, with a hard constraint from a
bad ChatGPT experience: **do not let memory bleed across casts.** ChatGPT-style memory drags
context from previous chats into new reasoning, which felt intrusive and wrong. Resonova must be
**cautious about memory injection** — but must **NOT become defensive/conservative** like
ChatGPT. The boss explicitly dislikes that timid style.

Design implication at the time: inject a **durable taste/preference profile** (e.g. "leans
ambient lately"), NOT an **unbounded episodic replay** of prior casts ("last time we discussed X"
without a clear music-domain reason). Warm, taste-aware framing — never creepy session callbacks
or stale context carried in uninvited. Updated 2026-06-23: bounded music-domain callbacks are
allowed when they are playlist-grounded, inspectable/resettable, and valuable to the current cast.
Memory may narrate the listener's relationship to the music; it must not haunt unrelated sessions.

### Chef assessment

I agree with the boss's lean and reasoning, with one structural addition:
- **Agree:** tasteful acknowledgment fits the baseline better than invisible-only, and the
  no-bleed constraint is correct — it is the line between "knows my taste" (good) and "won't let
  go of last conversation" (the ChatGPT failure). Our design already favors a *summarized taste
  profile* over raw logs, so we are positioned for this; we just must keep episodic per-cast
  content out of the persistent profile.
- **Add:** make memory injection **mode-aware** (see §3.1). Host awareness should be "aware of the
  listener's taste," not "aware of the listener's history" — the former is warm, the latter is
  what felt invasive.

## 3.1 Personal by default, optional public/broadcast mode (boss-raised 2026-06-21)

The source is the user's **personal, often private** playlist and listening. So Resonova is
**personal by default** — a private companion. The boss raises an **optional** future mode:
customers may want to **share a playlist with friends, or use it to make friends**, so Resonova
could optionally support a **public / broadcast / social mode**, staying **compatible with
Spotify** (Spotify's own social sharing). This stays optional; Resonova originally aims at
personal use.

Chef assessment: I agree directionally, with caveats.
- **Agree:** personal-first respects that listening data is private; "compatible with Spotify" is
  the right substrate alignment and low-friction; an optional social mode is a credible growth path.
- **Caveats:** public/broadcast mode is a real scope jump (multi-user, sharing, the privacy of a
  *shared* cast) and is **post-v0.1, clearly optional.** It also **interacts with §3**: in a
  shared cast the audience is not a single private listener, so the host's awareness and any
  memory injection must be **mode-aware** — a private taste profile must not leak into a cast the
  user broadcasts to friends. Decide §3 for personal mode first; design public mode separately.

## 3.2 Memory control model — what does "memory off" mean? (boss-raised 2026-06-22)

Today there is one boolean `memory_enabled`, and the privacy audit
(`docs/handoffs/Companion Memory Use Privacy Audit Handoff.md`) shows it is both incomplete and
ambiguous: "off" still injects the listener's Spotify top artists into the prompt, and "Clear
memory" never deletes `feedback.jsonl` (cleared prefs resurrect on the next cast). Before fixing
those, decide *what the control should mean.* The boss wants a consolidated model — degrees of
memory-off, an Incognito mode, and the line between clearing *preferences* vs clearing *data trails.*

Control surface to decide (not yet built):

- **Personalize on/off** — should generation use the persistent profile AND the live
  listener-profile (top artists etc.), or neither? Today's toggle covers only the former. Decide
  whether "off" means *no personal data in the prompt at all.*
- **Incognito (this cast only)** — generate one cast with no profile read AND no profile/feedback
  write, leaving stored memory untouched. A session-level, non-destructive "don't remember this one."
- **Clear preferences vs clear trails** — two different deletes: (a) reset learned
  preferences/feedback (must also delete `feedback.jsonl`); (b) clear the taste profile/trails.
  Decide whether "Clear memory" is one button or two — and that whatever ships actually clears
  everything it claims.

This model defines what the audit's disable/reset fixes (High + Med-High) must implement, so settle
it before patching. Ties to §3.1 (a shared/public cast is effectively forced-Incognito for the
private profile).

### Decision (2026-06-22, boss + chef): memory-off is partial; Incognito is the clean one

Boss decision: **"memory off" is a *partial* toggle** — it turns off the *data trace / user trail*
(the accumulating behavioral trail), NOT a full wipe. Making it "all clean" would collide with
**Incognito**, which is the full no-trace mode. **Chef: accepted** — this separates the two
controls cleanly. Resulting model:

- **Normal** — full personalization; trail accumulates.
- **Memory off (partial)** — suppress and stop accumulating the *trail/trace* layer; the durable
  *taste-as-a-lens* (top artists / derived styles) may still apply. A soft "don't track my trail,"
  not a wipe.
- **Incognito (per cast)** — this cast uses no personal data and writes nothing; stored memory is
  left untouched.

To pin down before implementing: the exact field set that counts as "trail" (suppressed by
memory-off) vs "durable taste" (kept). Proposed trail set: `recent_shifts`, recently-played
context, `playlist_patterns`. This refines what the audit's disable fix (High) must do — and note
the separate honesty bug stands regardless: today's toggle doesn't even gate the always-on
`LISTENER PROFILE` block.

## 4. PRINCIPLE — collect data only with a plan to use it

Boss direction: do **not** keep collecting all available personal data without a roadmap for
using it. Every signal in the profile should have a concrete, stated answer to: *how does this
change the listener's experience?* If a signal has no use, do not collect or persist it. The
next design pass should produce a **per-signal data-use roadmap** (signal → how it changes the
cast / the companion's behaviour), not more raw collection.

## 4.1 Context / scenario-aware personalization (boss-raised 2026-06-22)

Listening happens in real scenarios — the boss opens a playlist/cast **while riding/commuting,
when alone, when at work.** A cast could adapt to the *situation*, not just taste: a focus-at-work
cast is framed differently from an alone-in-the-evening one. This is a personalization axis
**orthogonal to taste**, and an intuitive fit for the companion baseline.

How to get the signal:

- **Explicit (recommended start):** the user picks a context at generation — e.g. *commute /
  focus·work / alone·evening / workout*. Simple, consent-clear, no inference creepiness, and it
  sidesteps the surveillance line the audit drew (the user *tells* us the scenario).
- **Inferred (later, optional):** time of day, weekday/weekend, Spotify device type
  (phone / computer / car-Connect), playback context. Less reliable and creepier — defer.

Chef note: a strong, low-risk axis to start with an **explicit context selector**, and it composes
cleanly with stance B — the hosts frame the cast *for the scenario* without narrating the listener.
Feeds the per-signal data-use roadmap (§4). Open: which contexts to offer; explicit-only vs add
light inference later; whether the chosen context is per-cast or remembered as a preference (and if
remembered, it is "trail"-class memory under §3.2).

### Reconsidered (2026-06-22): DROP the explicit scenario selector — redundant + awkward

Boss reconsidered: a scenario selector is **redundant and awkward**. The **playlist already conveys
the vibe** — you can't make a techno playlist feel "quiet" via commentary, so a separately-declared
scenario would conflict with the music rather than help. And the UX should not ask the user to pick a
scenario before/alongside the playlist. The scenario idea came from reasoning *in reverse* ("when you
open a playlist you're probably alone or driving"), but normally the flow is just: **put in a
playlist → generate.** That baseline stays simple.

**Chef: agree.** The playlist is the primary vibe signal; commentary should match the music, not a
declared scenario that may contradict it; a mandatory scenario pick adds friction and breaks the
baseline. **Decision: do NOT build the explicit context/scenario selector.** Removed from the build
queue.

Still open (needs consolidation, not queued): optional, lightweight customization is acceptable (the
boss agrees) — but it must be optional, must not contradict the playlist's vibe, and must not become
a "pick a scenario first" gate. Park until a concrete, non-awkward form is consolidated.

## 5. CANDIDATE EXTENSION (experimental) — personal-wiki connector

Boss's experimental idea: enrich the user profile by connecting the user's **personal wiki
system** (reference: `F:\wiki-system\subwikis\base-llm-wiki` — a structured Obsidian/LLM
knowledge base; cf. `me-llm-wiki`, `llm-wiki-resonova`). This is a much richer, user-authored
source of personal context than Spotify behaviour alone.

Status (boss 2026-06-21): treat as an **optional customer extension** — not owner-only, but not
core v0.1 either. The product team should evaluate it as a real extension candidate. Open
questions: what subset of a personal wiki is safe/useful to ingest; how to keep it consent-gated,
inspectable, and resettable like the rest of memory; how it interacts with the no-bleed rule
(§3); and where it sits on the roadmap. Optional and consent-first, like all memory.

## 6. What needs to happen next

- Multi-staff discussion (product reviewer, product investigator, auditor, chef) on §3, §3.1, §4.
  Use the two tailored prompts in Appendix A (product reviewer) and Appendix B (auditor).
- Anchor every option to the baseline (§0) and to "not creepy."
- Resolve §3 for **personal mode** first (boss leans tasteful, no cross-cast bleed); design the
  optional public/broadcast mode (§3.1) separately and later.
- Output a per-signal data-use roadmap (§4) before building more memory.
- Have the product team evaluate the personal-wiki connector (§5) as a customer extension.

---

## How to send these (combined quality role)

These map to the combined `Internal Auditor / Investigator / Product Reviewer` role (one agent,
mode-per-brief). Either run them as **two focused passes** (Appendix A, then Appendix B), or send
**one brief with a primary mode named** — primary: Product Reviewer (A), secondary:
Auditor/Investigator (B). Prefer two passes when you want each lens sharp; the one merged send
(Appendix C) when you want a single round-trip.

## Appendix A — Prompt to paste to the PRODUCT REVIEWER

Focus: companion experience, UX, the listener's felt experience.

> Resonova is a **personal AI radio companion**. Baseline (do not lose it): it should understand
> the listener better the more they use it — **without feeling invasive.** It already collects two
> memory layers (the user's activity inside Resonova: saved casts, replays, feedback; and the
> user's Spotify activity: top/recent, recency-weighted saved library, followed artists) into one
> inspectable profile. Today the hosts **never reference the listener** — memory only steers
> commentary invisibly, and a test cast did not mention the user at all.
>
> Hard constraint from the owner: **no cross-cast memory bleed.** A bad ChatGPT experience —
> where memory dragged previous-chat context into new reasoning — must not be repeated. We want a
> durable *taste* profile ("leans ambient lately"), not episodic replay ("last time we discussed
> X"). But do **not** over-correct into a timid, defensive, conservative style — the owner
> dislikes that. Owner leans toward *tasteful* acknowledgment of the single listener.
>
> Read these files first (repo root `F:\GitHub\resonova`; you have full workspace access — read
> the real files, don't rely on this summary):
> - `docs/strategy/companion-direction-and-memory-use-brief.md` — this brief: baseline (§0) and the
>   open decisions (§3 host awareness, §3.1 personal/public mode, §4 data-use, §5 wiki extension).
> - `README.md` and `docs/strategy/v0.1-roadmap.md` — product baseline and roadmap.
> - `docs/strategy/boss-profile.md` — owner preferences and working style.
> - `docs/handoffs/Persistent Profile Spotify Trails Design Handoff.md` — memory architecture and
>   the full list of signals; `docs/handoffs/Persistent Profile Slice One Handoff.md` and
>   `docs/handoffs/Persistent Profile Slice Two Handoff.md` — what is actually built.
> - `resonova/api/gemini.py` — `build_prompt`: the `LISTENER PROFILE` / `PERSISTENT MEMORY` blocks
>   and the "never narrate the listener" guardrails (ground truth on how memory reaches the cast).
> - `resonova/profile.py` — what is summarized/persisted into the profile (taste, prefs, feedback).
> - `resonova/api/spotify.py` and `resonova/config.py` — the Spotify signals and OAuth scopes used.
> - `resonova/web/index.html` and `resonova/web/player.js` — the Memory panel UI and connect-time
>   consent copy.
> - Live app, if running: `http://127.0.0.1:8765` — connect Spotify to see the real flow.
>
> Review and advise (do not implement; do not patch code):
> 1. Where should the companion sit — (a) invisible steering only, (b) tasteful acknowledgment of
>    the single listener, (c) direct companion — to feel warm and personal without creepiness?
>    Recommend a concrete stance and example host lines.
> 2. How do hosts acknowledge *taste* without replaying *history* or breaking the experience? Give
>    do/don't examples that avoid the ChatGPT-style bleed yet aren't timid.
> 3. For each memory signal, give a concrete, valuable way it should change the listener's
>    experience. Flag any signal with no good use — we want a data-use roadmap, not hoarding.
> 4. Personal-by-default vs an optional public/broadcast/social mode (sharing a cast with friends,
>    Spotify-compatible): is this a credible companion experience, and how should host framing and
>    memory differ when a cast is shared vs private?
> 5. Is a personal-wiki connector a worthwhile customer extension for profile enrichment? What
>    would make it feel valuable and safe?
>
> Return severity-ranked findings, a recommended companion stance with examples, a per-signal use
> roadmap, and what to park. Separate product-design issues from implementation.

## Appendix B — Prompt to paste to the AUDITOR / INVESTIGATOR

Focus: independent challenge, privacy/creepiness risk, assumptions.

> Resonova is a personal AI radio companion that collects two memory layers (in-app activity;
> Spotify top/recent, saved library, followed artists) into an inspectable, resettable profile,
> injected into the cast-generation prompt. Currently hosts never reference the listener (memory
> only steers invisibly). The owner wants *tasteful* acknowledgment but with a hard rule: **no
> cross-cast memory bleed** (the ChatGPT failure mode), and **no timid/defensive over-correction.**
> The owner also floats an optional public/broadcast mode for sharing casts.
>
> Read these files first (repo root `F:\GitHub\resonova`; you have full workspace access — verify
> against the real files, don't trust this summary):
> - `docs/strategy/companion-direction-and-memory-use-brief.md` — baseline (§0) and open decisions.
> - `resonova/profile.py` — exactly what is summarized/persisted (taste, prefs, feedback fold);
>   confirm whether any raw/episodic or private data is retained.
> - `resonova/api/gemini.py` — `build_prompt`: how the profile is injected into the cast, the
>   capping/gating, and the "never narrate the listener" guardrails.
> - `resonova/server.py` — generation pipeline, the profile read/write hooks, and the
>   `/api/profile`, `/api/profile/refresh`, `/api/feedback` routes (where data flows).
> - `resonova/api/spotify.py` and `resonova/config.py` — the Spotify signals and OAuth scopes;
>   confirm scopes are read-only and justified.
> - `resonova/web/index.html` and `resonova/web/player.js` — the consent copy and Memory panel
>   (inspect/edit/reset/disable controls).
> - `docs/handoffs/Persistent Profile Slice Two Handoff.md` — the latest build's stated risks.
> - For the wiki-connector question: `F:\wiki-system\subwikis\base-llm-wiki` — the owner's personal
>   wiki structure (and siblings `me-llm-wiki`, `llm-wiki-resonova`).
> - Live app, if running: `http://127.0.0.1:8765`.
>
> Audit independently (do not patch code; challenge our assumptions):
> 1. Where is the real creepiness / privacy risk if hosts start acknowledging the listener? What
>    crosses the line from "knows my taste" into "surveillance"?
> 2. Stress-test the no-bleed rule: how could episodic/private context leak across casts or into a
>    shared/public cast? What guards are needed, especially mode-awareness (private profile must
>    not surface in a broadcast cast)?
> 3. Are we collecting any personal signal we cannot justify by a concrete listener benefit?
>    Identify data we should stop collecting or persisting.
> 4. What are the privacy/consent risks of a personal-wiki connector, and what would have to be
>    true to make it safe for customers (not just the owner)?
> 5. What must be tested on a real account/device before building more memory features?
>
> Return severity-ranked findings, disagreements with our current direction, the highest-risk
> items to resolve first, and what to park. Evidence over opinion.

## Appendix C — Combined single-send brief (one role, primary mode named)

Use this when you want one round-trip to the combined quality agent instead of two passes.
Primary mode: Product Reviewer. Secondary mode: Auditor / Investigator.

> Resonova is a personal AI radio companion. Baseline (do not lose it): it should understand the
> listener better the more they use it — without feeling invasive. It collects two memory layers
> (the user's activity inside Resonova: saved casts, replays, feedback; and the user's Spotify
> activity: top/recent, recency-weighted saved library, followed artists) into one inspectable,
> resettable profile, injected into the cast-generation prompt. Today the hosts never reference the
> listener — memory only steers invisibly, and a test cast did not mention the user at all.
>
> Owner constraints: lean toward *tasteful* acknowledgment of the single listener; **no cross-cast
> memory bleed** (the ChatGPT failure mode — durable taste profile, not episodic replay); and **no
> timid/defensive over-correction.** Personal by default, with an optional public/broadcast mode
> later. You are the combined Internal Auditor / Investigator / Product Reviewer.
> **Primary mode: Product Reviewer. Secondary: Auditor/Investigator.** Lead with product judgment;
> add risk/evidence findings where they matter.
>
> Read these files first (repo root `F:\GitHub\resonova`; full workspace access — read the real
> files, don't rely on this summary):
> - `docs/strategy/companion-direction-and-memory-use-brief.md` — baseline (§0) and open decisions.
> - `README.md`, `docs/strategy/v0.1-roadmap.md`, `docs/strategy/boss-profile.md` — baseline,
>   roadmap, owner preferences.
> - `resonova/api/gemini.py` — `build_prompt`: profile injection, capping/gating, the "never
>   narrate the listener" guardrails.
> - `resonova/profile.py` — what is summarized/persisted (taste, prefs, feedback); confirm no
>   raw/episodic/private data is retained.
> - `resonova/server.py` — generation pipeline, profile hooks, `/api/profile`,
>   `/api/profile/refresh`, `/api/feedback` routes.
> - `resonova/api/spotify.py`, `resonova/config.py` — Spotify signals and OAuth scopes (read-only?).
> - `resonova/web/index.html`, `resonova/web/player.js` — Memory panel and consent copy.
> - `docs/handoffs/Persistent Profile Spotify Trails Design Handoff.md`,
>   `docs/handoffs/Persistent Profile Slice One Handoff.md`,
>   `docs/handoffs/Persistent Profile Slice Two Handoff.md` — architecture, signals, built state, risks.
> - Wiki-connector question: `F:\wiki-system\subwikis\base-llm-wiki` (siblings `me-llm-wiki`,
>   `llm-wiki-resonova`).
> - Live app, if running: `http://127.0.0.1:8765`.
>
> Advise (do not implement; do not patch code):
> Product Reviewer (primary):
> 1. Where should the companion sit — (a) invisible steering, (b) tasteful acknowledgment of the
>    single listener, (c) direct companion — to feel warm without creepiness? Recommend a stance
>    with example host lines.
> 2. How do hosts acknowledge *taste* without replaying *history*? Give do/don't examples that
>    avoid the ChatGPT bleed yet aren't timid.
> 3. For each memory signal, give a concrete way it should change the listener's experience; flag
>    any signal with no good use (data-use roadmap, not hoarding).
> 4. Personal-by-default vs an optional public/broadcast mode: credible? How should host framing
>    and memory differ when a cast is shared vs private?
> 5. Is a personal-wiki connector a worthwhile, safe customer extension?
> Auditor / Investigator (secondary):
> 6. Where is the real creepiness/privacy line, and how could private/episodic context leak across
>    casts or into a shared cast? What guards (esp. mode-awareness) are needed?
> 7. Are we collecting any signal we cannot justify, or retaining raw/private data we shouldn't?
> 8. What must be tested on a real account/device before building more?
>
> Return: a recommended companion stance with examples (primary), a per-signal use roadmap,
> severity-ranked risk findings (secondary), and what to park. Separate product-design from
> implementation. State which mode each finding comes from.
