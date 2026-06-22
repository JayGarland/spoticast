---
title: "Companion / Memory-Use Privacy & Risk Audit Handoff"
created: 2026-06-22
status: audit-complete (no code; independent challenge)
role: Internal Auditor / Investigator / Product Reviewer (combined quality role)
primary_mode: Auditor / Investigator
parent_brief: docs/strategy/companion-direction-and-memory-use-brief.md
companion_review: docs/handoffs/Companion Direction Memory Use Product Review Handoff.md
scope: inspect-only — no product code patched, no files committed, no PR opened
---

# Companion / Memory-Use Privacy & Risk Audit

Independent audit of the memory layer's privacy, creepiness, and no-bleed risk.
Evidence over opinion: every finding cites a file:line or a live observation.

**No-self-review declaration.** The same reviewer produced the companion Product
Review (linked above). Per the role's no-self-review rule, this audit challenges the
**product and codebase and owner direction independently** — it is NOT an Auditor
gate approving that prior review. Where this audit revises the earlier framing, it
says so. If a formal Auditor gate on the Product Review findings is required, route it
to a different agent.

Evidence base (read this pass): `server.py` (full), `spotify.py` (full),
`profile.py`, `gemini.py`, `config.py`, `web/index.html`, live `/api/profile` at
`http://127.0.0.1:8765`, and the structure of `F:\wiki-system\subwikis\base-llm-wiki`
(structure only — personal notes deliberately not opened).

---

## Summary judgment

The architecture's *content* model is sound for no-bleed: it persists summarized
taste, not cast transcripts (`profile.py` stores artist names / tags / feedback tags
only; no raw cast text). The real risks are at the **identity and control layer**,
not the content layer:

- There is **no per-user isolation** — one global profile, auto-populated on connect.
  In the accepted v0.1 "private hosted owner/beta with testers" shape, this is a
  literal cross-user memory bleed waiting to happen.
- The **disable control does not fully disable**, and **reset does not fully reset**.
- **Mode-awareness does not exist**, so a broadcast cast would leak the private
  profile by construction.

These should be resolved before any second person connects or any broadcast mode is
built — independent of the §3 stance decision.

## Severity-Ranked Findings

| Sev | Finding | Evidence | Audit type |
|---|---|---|---|
| **Critical** | **No per-user isolation + auto-populate on connect = cross-user bleed.** One global `generated/profile/profile.json` (no identity keying) and one `.research_cache/.spotify_oauth` token. On every OAuth callback the profile is auto-refreshed from whoever just connected. If a second tester connects (v0.1 allows ≤25 Spotify dev users), their library/follows **merge into the same profile** and steer the owner's casts, and vice versa. | `profile.py:19-20`; `spotify.py:15`; `server.py:147-164, :202` | Privacy / no-bleed |
| **High** | **"Disable memory" does not stop personal data reaching the prompt.** The `LISTENER PROFILE` block (Spotify top artists + Last.fm) is built and injected every generation regardless of `memory_enabled`; only the separate `PERSISTENT MEMORY` block respects the toggle. | `server.py:515-522, :552-554`; `gemini.py:220-237, :315-319, :380-381` | Honesty / consent |
| **High** | **No mode-awareness; broadcast mode leaks the private profile by construction.** No `shared`/`private` flag anywhere in the pipeline or `build_prompt`. A naive broadcast/social cast would inject the private taste profile into a cast shared with friends. | `gemini.py:build_prompt` (no mode branch); `server.py:_run_generation` (no mode) | Privacy / no-bleed |
| **Med-High** | **Reset is incomplete — deleted memory resurrects.** `reset_profile()` rewrites an empty `profile.json` but never deletes `feedback.jsonl`. `DELETE /api/profile` calls only `reset_profile()`. The next generation runs `fold_feedback_into_profile`, re-deriving `avoid`/`loved` prefs and feedback memories from the retained feedback log. "Clear memory" is partially false. | `profile.py:101-106` vs `_FEEDBACK_PATH:376`; `server.py:319-323`; fold at `server.py:655` | Honesty / data-retention |
| **Med** | **Memory is opt-out, not opt-in, and consent copy is incomplete.** `memory_enabled` defaults `true`; profile auto-populates on connect. Landing consent names only saved music + followed artists — omits that top artists / recently-played / playlists are also read, that top artists are persisted, and that memory is on by default and feeds the prompt. | `profile.py:38`; `server.py:202`; `index.html:98-101` | Consent |
| **Med** | **`recent_shifts` and `playlist_patterns` are the episodic gray-zone signals.** `recent_shifts` = raw recent saved-track artist names rendered as "current listening"; `playlist_patterns` = "frequently casts from 'X'" — behavioral history about the user's own past casting, injected into the prompt. Not transcripts, but the closest thing to "what you've been doing lately." | `profile.py:254-271, :354-360`; `gemini.py:336-337` | No-bleed / creepiness |
| **Med** | **`user-read-email` requested but never used.** `current_user()` is read only for `me["id"]` (playlist-ownership filter); email is never accessed or persisted. Unjustified consent line (Spotify shows "email address"). | `spotify.py:414-415`; `config.py:61` | Data minimization |
| **Low-Med** | **"Read-only scopes" framing is inaccurate.** `streaming` and `user-modify-playback-state` are playback-*control* scopes (start/pause/skip/transfer the user's active Spotify). Justified by the in-browser player, but they are not read-only — relevant to any consent/policy statement that claims read-only. | `config.py:57-59`; Slice Two handoff "READ ONLY" claim | Accuracy / consent |
| **Low** | **Free-text feedback `note` persisted raw.** Arbitrary `note` string written verbatim to `feedback.jsonl`. Not folded into the profile (tags only), but it is the one raw free-text retention path on disk. | `server.py:371-395`; `profile.py:386-390` | Data-retention |
| **Low** | **Spotify token exposed to the browser** via `/auth/token` (by design for the Web Playback SDK); not persisted to the profile. Acceptable, noted for completeness. | `server.py:206-211` | Noted, accepted |

## Answers to the Audit Questions

**1. Where is the real creepiness / privacy line?** Two lines, not one. (a) *Inventory
vs descriptor*: injecting the user's actual artist names (top/followed/library lists,
`gemini.py:323-345`) and then acknowledging them risks reading the listener's own
private library back at them — that can feel like surveillance even with zero history
replay. Safe acknowledgment needs *descriptors* ("leans ambient"), not the user's
*inventory*. (b) *Taste vs behavior*: `recent_shifts`/`playlist_patterns` cross from
"knows my taste" into "watched what I did lately." This revises the Product Review's
framing slightly: the danger is not only episodic replay; it is also descriptor-vs-
inventory.

**2. No-bleed stress test.** Content-level bleed is well-contained: no cast transcripts
are persisted; `memories` come only from feedback-tag folding. The leaks are
elsewhere: (i) **identity-level bleed** (Finding Critical) — the global profile merges
multiple users; (ii) **mode-level bleed** (Finding High) — no private/shared flag, so a
broadcast cast injects the private profile; (iii) **resurrection bleed** (Finding
Med-High) — reset leaves `feedback.jsonl`, so cleared preferences come back. Guards
needed: per-identity profile keying (or hard single-user enforcement); a `cast_mode`
flag that gates BOTH the `LISTENER PROFILE` and `PERSISTENT MEMORY` blocks off for
shared casts; and a reset that also clears `feedback.jsonl`.

**3. Unjustifiable signals.** `user-read-email` (never read) — drop. Free-text `note`
(persisted raw, only tags used) — drop or scrub. `playlist_patterns` (behavioral,
narration-risky, thin benefit) — reconsider. `favorite_eras` (declared, never
populated — confirmed empty live) — drop or populate. Everything else maps to a stated
benefit.

**4. Personal-wiki connector risk.** Structure confirms the hazard. `base-llm-wiki` is
methodology/templates (non-personal), but the system design includes `raw/_inbox/`
(raw dumps, incl. conversation logs — `boss-profile.md` itself cites a raw codex
conversation), `raw/_rejected/`, and full git history; personal content lives in the
sibling `me-llm-wiki`. Risks: (a) naive ingest pulls uncurated `raw/` personal/
sensitive prose, not just curated pages; (b) git history retains rejected/deleted
content; (c) free-form prose is cross-domain (health, relationships, work) — the exact
cross-domain bleed that made ChatGPT feel invasive; (d) for a *customer*, sensitivity
is far higher than music. To be safe it must ALL hold: opt-in per-subwiki AND
per-folder (curated `wiki/` pages only, never `raw/`, never git history); ingest as
LLM-derived *taste descriptors* with the prose discarded; a hard music/culture domain
filter; same inspect/edit/reset/disable as Spotify memory (and a reset that actually
clears it); explicit consent naming the exact folders; never narrated. Recommendation:
**park for v0.1**; if piloted, owner-only, curated-pages-only, behind the memory
disable toggle.

**5. What to test on a real account/device first.**
- *Two-identity test:* connect a second Spotify account on the same instance; observe
  whether profiles isolate or merge (expected: merge — proves Critical finding).
- *Disable test:* toggle memory off, generate, capture the actual prompt; check whether
  top artists still appear (expected: yes — proves High finding).
- *Reset test:* `DELETE /api/profile`, then generate; check whether feedback-derived
  prefs reappear (expected: yes — proves resurrection finding).
- *Followed-artists:* on an account that follows artists, confirm population (the
  silent-`[]` bug is fixed in code; live empty is likely "no follows").
- *Reconnect/scope-change:* confirm re-auth after scope change doesn't crash and shows
  the expected consent screen.
- *Real-phone playback* (roadmap Phase 3) — still outstanding.

## Disagreements With Current Direction

1. **Sequencing.** The brief says decide the §3 personal stance first and design
   broadcast later. The identity-isolation problem (Critical) is **not** a broadcast
   concern — it already applies to the accepted v0.1 "private hosted owner/beta with
   testers." It must be fixed before any second tester connects, independent of the
   stance decision.
2. **"Read-only scopes."** The Slice Two handoff and the audit prompt frame scopes as
   read-only; two granted scopes are playback-control, not read-only. Accuracy matters
   for a consent/policy statement.
3. **"Tasteful acknowledgment is inherently low-risk."** Mild challenge: with the
   profile injecting the user's own artist-name inventory, even non-episodic
   acknowledgment can feel like surveillance. The safe line is descriptor-not-inventory,
   not merely taste-not-history.

## Highest-Risk Items to Resolve First (order)

1. Per-user profile isolation (or enforced single-user) **before any second tester
   connects** (Critical).
2. Make "disable" actually disable, and "reset" actually clear feedback (High + Med-High)
   — before any "you control your memory" claim ships.
3. Design `cast_mode` mode-awareness **before** broadcast/social mode is built (High).
4. Fix consent copy completeness; drop `user-read-email` (Med).

## Park

- Broadcast / social mode — until isolation (Critical) and mode-awareness (High) exist.
- Personal-wiki connector — until the safe-subset + consent model above exist.
- Segment-level feedback, audio features, staleness eviction — as already parked.

## Verification Status

- VERIFIED (code): all file:line claims above were read this pass.
- VERIFIED (live): `/api/profile` content; profile auto-populated, `memory_enabled:true`,
  `followed_artists:[]`, feedback effectively unused.
- VERIFIED (structure only): the wiki directory layout; personal notes not opened.
- NOT VERIFIED (recommended live tests): the two-identity merge, the disable-still-injects,
  and the reset-resurrection behaviors are predicted from code and should be confirmed on
  a real second account before building more memory.

## Mode Boundary Notes

- Primary mode: Auditor / Investigator. Cross-mode flags into Product Review territory
  (descriptor-vs-inventory) are surfaced, not hidden.
- No-self-review respected: this audit challenges the product/codebase/direction; it does
  not ratify the linked Product Review. A formal gate on that review should go to a
  different agent.
- Deeper diagnosis / fix-planning for the isolation and mode-awareness work should route
  to `gem-orchestrator` or a technical manager — not this quality role.
