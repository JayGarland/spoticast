---
title: "Companion Direction & Memory-Use Product Review Handoff"
created: 2026-06-22
status: review-complete (no code; decisions left open for boss + chef)
role: Internal Auditor / Investigator / Product Reviewer (combined quality role)
primary_mode: Product Reviewer
secondary_mode: Investigator (cross-flags)
parent_brief: docs/strategy/companion-direction-and-memory-use-brief.md
scope: inspect-only — no product code patched, no files committed, no PR opened
---

# Companion Direction & Memory-Use Product Review

This is a review/handoff document only. No product code was written or changed.
All directional choices are left as **OPEN DECISIONS for boss + chef** — this review
documents evidence and options, it does not decide.

Evidence base: live app inspected at `http://127.0.0.1:8765` (connected as Spotify
user `jie_pengyu`, 14 saved casts), the live `/api/profile` response, 27 cached
cast scripts in `.research_cache/gemini/`, the strategy docs, the three persistent-
profile handoffs, and source ground truth (`gemini.py`, `profile.py`, `spotify.py`,
`config.py`, `web/`). Facts read from code/live app are marked VERIFIED; everything
under "Open Decisions" is for boss + chef.

---

## 1. Summary

- **Primary mode:** Product Reviewer. **Secondary:** Investigator cross-flags. No
  Auditor gate was exercised (no self-review).
- **Overall judgment:** The memory plumbing is well-built and structurally aligned
  with the owner's no-bleed instinct — it persists *summarized taste*, not cast
  transcripts. The gap is the *felt* experience: across all 27 real casts the hosts
  never reference the listener. That is by design, not a bug.
- **Ready for more customer testing?** The plumbing, yes. The companion experience,
  not yet — the §0 "knows me better" baseline is currently stored but not
  experienced, and two release-relevant items below should be resolved regardless of
  which companion direction is chosen.

## 2. Verified Facts (Live)

- VERIFIED — **Hosts never reference the listener.** All 27 cached cast scripts were
  scanned; zero listener narration. The only second-person usages are
  host-to-host/generic ("metaphors you usually get in pop", "what worked last time"
  about an artist). The guardrail is fully effective in practice.
- VERIFIED — **The live profile is entirely raw artist-name lists.** From
  `/api/profile`: `recurring_styles: []` and `favorite_eras: []` are **empty**
  (they depend on Last.fm, and `lastfm.connected: false`). `recent_shifts` holds 20
  raw artist names (Momoko Kikuchi, D-51, Red House Painters, Frank Ocean, …)
  rendered into the prompt as "current listening." `top_artists` spans Marilyn
  Manson → 李志 → Pavarotti → Manowar → Skrillex with no derivable single lens.
- VERIFIED — **Feedback channel barely used:** `feedback_count: 1`, `memories: []`,
  `commentary_preferences` all empty.
- VERIFIED — **`followed_artists: []`** despite `user-follow-read` granted
  (`scopes_used` includes it). Cause unconfirmed — either no follows or a silent
  cursor-pagination failure (Slice Two risk #3).
- **Consequence for any acknowledgment decision:** today the hosts would have *only*
  raw artist names to draw on — the riskiest material — because no style/era
  descriptors exist in the live profile.

## 3. Severity-Ranked Findings

| Sev | Finding | Evidence | Type |
|---|---|---|---|
| **High** | The prompt forbids the acknowledgment stance under consideration. Moving to acknowledgment is a deliberate guardrail rewrite, not tuning. | `gemini.py:59, :135, :364-368`; confirmed by 27 zero-reference scripts | Product-design → impl |
| **High** | "Memory enabled = off" does **not** stop the listener's data reaching the prompt. The `LISTENER PROFILE` block (Spotify top artists / Last.fm) is injected every generation regardless of the toggle; only the separate `PERSISTENT MEMORY` block respects it. | `gemini.py:220-237, :380` vs gated `:315-319`; live `memory_enabled:true` | Implementation / honesty |
| **Med-High** | `recent_shifts` blurs the durable-vs-episodic line — raw recent artist names labeled "current listening," the shape closest to the ChatGPT failure. Design intent (handoff §3) was a derived style statement ("leaning ambient lately"). | `profile.py:254-271`, `gemini.py:336-337`; live data | Design ↔ impl divergence |
| **Med** | Memory has no felt payoff in the listening moment (panel-only). The §0 "knows me better" baseline is stored, not experienced. | `index.html:151-186`; live | Product |
| **Med** | Signals with weak/no use: `favorite_eras` never populated (dead field — no summarizer writes it); `playlist_patterns` behavioral/borderline-episodic; `user-read-email` requested but unused. | `profile.py:50, :354-360`; live `/api/profile`; `config.py:61` | Data-use |
| **Low-Med** | `top_artists` / `saved_library_artists` / `followed_artists` overlap (Roy Blair, Pixies appear in two lists live) — redundant prompt names, higher listener-name-drop risk. | live `/api/profile`; `gemini.py:323-345` | Product / impl |
| **Investigator flag** | `followed_artists: []` despite scope granted — possible silent cursor-pagination failure vs genuinely no follows. Unconfirmed. | live `/api/profile` | Needs a real check |

## 4. Evidence

- VERIFIED (code): the three guardrail layers (`gemini.py:59, :135, :364-368`); the
  always-on `LISTENER PROFILE` block independent of `memory_enabled`
  (`:220-237, :380-381`) vs the gated `PERSISTENT MEMORY` block (`:315-319`); the
  summarizers and schema in `profile.py`; the 11 Spotify scopes in `config.py:52-65`.
- VERIFIED (live): `/api/profile` content as quoted in §2; 27 cast scripts contain no
  listener narration.
- Contradiction surfaced: the design handoff's `recent_shifts` intent (a derived
  style sentence) vs the implementation (raw artist-name recency list).
- Assumption (not verified): the cause of `followed_artists: []`.

## 5. Repro / Inspection Steps

1. `GET http://127.0.0.1:8765/api/profile` — confirm `recurring_styles`/
   `favorite_eras` empty, `recent_shifts` holds raw names, `followed_artists` empty.
2. Read `gemini.py:220-237` then `:380` — confirm `listener_lines` render with no
   `memory_enabled` check; compare to gated `:315`.
3. Toggle "Memory enabled" off in the panel, regenerate, dump the prompt — confirm
   top artists still appear in `LISTENER PROFILE`.
4. `grep` the cached scripts in `.research_cache/gemini/` for listener narration —
   confirm none.
5. For the followed-artists flag: check the live Spotify account's follow count, then
   `POST /api/profile/refresh` and re-read `/api/profile`.

## 6. Companion Stance — OPEN DECISION (boss + chef)

Three positions, with external evidence and example lines. **No recommendation made.**

- **Option A — Invisible steering (current).** Safest, never creepy; the listener
  cannot feel the companion. Example: today's behavior (no references).
- **Option B — Taste-as-a-lens (semantic).** Hosts acknowledge taste, never history
  or data. Do: "This one's built for someone who lives in the quiet end of things."
  Don't: name-drop the listener's own artists or recite data.
- **Option C — Bounded history-replay (episodic), Spotify-DJ style.** Light,
  music-domain, present-tense. Do: "You've been on a midwest-emo run lately — leaning
  into it." Don't (the ChatGPT failure): "Last time we discussed X," cross-domain
  callbacks, uninspectable memory.

The history-replay window is explicitly left **open** at the owner's direction; it is
not closed by this review.

## 7. External App Practices (informs the §6 decision; does not decide it)

Industry names for the two forks: **semantic / profile memory** ("taste as a lens" —
durable traits compacted into a profile, what Resonova does today) vs **episodic
memory** ("history replay" — time-stamped events: "we discussed X last week").

| | Taste-as-a-lens (semantic) | History-replay (episodic) |
|---|---|---|
| Closest precedent | Spotify Wrapped framing; Resonova today | **Spotify AI DJ** — and well-received |
| What it does | "for someone who loves X" | DJ: "you've been playing a lot of indie rock this week," resurfaces old favorites, explains why a track was picked, adapts to skips/feedback |
| Cautionary tale | — | **ChatGPT memory**: context "bleeding across modes," steering a divorcing user back to his marriage for weeks; cross-conversation reference cited as dangerous in a wrongful-death suit |
| Why it works / fails | Always safe; can feel flat | DJ works because **bounded** (same-domain, present-framed, light). ChatGPT fails because **unbounded** (cross-domain, uninspectable, over-intimate, uninvited) |

Key point for the decision: the ChatGPT failure was *unbounded, cross-domain,
uninspectable* episodic memory — not episodic memory as such. The closest competitor
(Spotify DJ) ships a bounded version of Option C successfully. Resonova already has
the two mitigations ChatGPT lacked: an inspect/edit/reset panel and per-cast
music-domain bounding. A possible (not mandated) way to choose: ship one variant,
A/B it on real casts judged on "knows me without feeling watched," then decide whether
to invest in real replay trails.

Sources: Spotify AI DJ launch (newsroom.spotify.com 2023-02-22), DJ voice requests
(newsroom.spotify.com 2025-05-13), ZenML LLMOps DJ commentary write-up; "Why I Turned
Off ChatGPT's Memory" (every.to), ChatGPT memory deep dive (embracethered.com); AI
memory episodic-vs-semantic primers (pieces.app, machinelearningmastery.com).

## 8. Per-Signal Data-Use Roadmap

- **Keep (primary steering):** top artists; recurring styles (once Last.fm or a
  style-derivation source exists); feedback preferences.
- **Keep, merged:** saved-library + followed + top artists into one ranked affinity
  view for the prompt (reduces redundancy and name-drop risk).
- **Fix shape before any acknowledgment:** `recent_shifts` → derive a style/era
  descriptor, not a raw artist-name list.
- **Decide drop-vs-populate:** `favorite_eras` (currently dead).
- **Reconsider:** `playlist_patterns` (behavioral, narration-risky).
- **Drop:** `user-read-email` (unused by the memory layer).
- **Correctly parked:** audio features (403 in Dev Mode); live playback state
  (use live only, do not persist).

## 9. Shared / Public Mode — OPEN, post-v0.1

Credible later. Decision to preserve: a shared cast must hard-gate **both** the
`LISTENER PROFILE` and `PERSISTENT MEMORY` blocks off — a private taste profile must
never surface in a cast broadcast to friends. Decide personal-mode stance (§6) first.

## 10. Personal-Wiki Connector — OPEN, park for v0.1

Richest enrichment, highest creepiness/bleed risk. Would only be safe if: opt-in
per-subwiki; ingested as derived descriptors, not raw notes; same inspect/edit/reset;
never narrated; respects no-bleed. Left for boss + chef.

## Open Decisions for Boss + Chef

1. Companion stance: A, B, C — or B-now / C-as-experiment.
2. Whether to resolve the two High findings before more memory work (guardrail
   rewrite scope; make "disable" actually disable the listener-profile injection).
3. Connect Last.fm or add a style-derivation source so acknowledgment has safe
   material (today only raw names exist).
4. `favorite_eras`, `playlist_patterns`, `user-read-email`: keep, fix, or drop.
5. Investigate `followed_artists` empty (pagination bug vs no follows).
6. Shared mode and wiki connector: confirm parked.

## Parked

Public/broadcast mode; personal-wiki connector; segment-level feedback; audio
features; staleness eviction; `favorite_eras` / `playlist_patterns` until a use is
decided.

## Mode Boundary Notes

- Cross-mode flags raised (not hidden): disable-toggle gap; `recent_shifts`
  divergence; `followed_artists` empty; `user-read-email` unused.
- No self-review risk: first-pass external review; none of the reviewed code was
  produced or recommended by this reviewer.
- Deeper diagnosis (guardrail-rewrite planning, live prompt A/B engineering) should
  route to `gem-orchestrator` or a technical manager — not this quality role.

## Self-Assessment Against Role Spec

Names one primary mode and stays inside it; separates product-design from
implementation on every finding; gives Resonova-specific file:line and live evidence
rather than generic UX advice; distinguishes release-relevant risks (the two Highs)
from polish; surfaces contradictions and an unverified item honestly; says what to
park; respects no-self-review; and — per boss direction — leaves all directional calls
as open decisions rather than issuing a verdict.
