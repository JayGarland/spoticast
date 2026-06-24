# TTS Cost Strategy — Decision Record

Date: 2026-06-24
Decision by: Boss + Chef
Status: APPROVED

---

## Decision

Two-step TTS cost reduction before SaaS launch:

1. **P0 — Cut per-track dialogue length** from 5–8 exchanges to 3–4 exchanges.
   Two-line edit in `resonova/api/gemini.py` (lines 135 and 607).
   Implement now.

2. **Dia trial** — Trial the Dia open-source local TTS model as a replacement for
   Gemini TTS. Trial plan in `docs/boss/decisions/tts-model-options.md`.
   Begin immediately after P0 is committed.

---

## Confirmed Provider

**`gemini-3.1-flash-tts-preview` stays as production TTS for all phases until SaaS volume
warrants revisiting.** Confirmed 2026-06-24 after full research cycle.

Cost position: Gemini 3.1 Flash TTS + P0 dialogue cut (`cad313d`). No further TTS
provider changes planned for pre-SaaS beta.

---

## What Was Ruled Out

| Option | Verdict | Reason |
|---|---|---|
| Switch to `gemini-2.5-flash-preview-tts` ($10/1M) | REJECTED | Google confirms 3.1 is a "substantial step up" in expressiveness — quality regression risk for Sam/Alex persona |
| Switch to `gemini-3.5-flash-tts` at $6/1M | REJECTED | Does not exist — false claim from a pricing aggregator |
| Batch API on `gemini-3.1-flash-tts-preview` ($10/1M) | PARKED | Requires async generation, breaks real-time streaming architecture |
| `gpt-4o-mini-tts` ($12/1M) | REJECTED | No native multi-speaker — would require per-speaker stitching + tts.py rewrite |
| 火山引擎 豆包播客TTS | PARKED (future) | English quality secondary to Chinese; consider if Resonova adds Chinese-language content |

---

## Expected Outcome

| Phase | TTS approach | Est. cost per 10-song cast |
|---|---|---|
| Current (pre-P0) | `gemini-3.1-flash-tts-preview` | ~€0.57 |
| After P0 | Same model, shorter dialogues | ~€0.30 |
| After P0 + Dia passes quality bar | Dia local, no API cost | ~€0.03 (script gen only) |
| Public SaaS (Option C) | Re-evaluate — hosted Dia or Gemini at scale | TBD |

---

## Dia Trial Result (2026-06-24)

Tested `Dia-1.6B` via Dia-TTS-Server on RTX 4070 Super against Gemini 3.1 Flash TTS
on the same 4-exchange Fast Car script.

| | Dia 1.6B | Gemini 3.1 Flash TTS |
|---|---|---|
| Generation time | ~308 seconds | ~23 seconds |
| VRAM | 5.6 GB | — (API) |
| Quality verdict | Below casting bar | Production quality |

Boss verdict: Gemini is significantly better for the casting format. Dia is a step up from
basic TTS but lacks the expressive radio-host energy Sam and Alex require. Would need
fine-tuning on casting data to be viable — that is a research project, not a near-term
option.

**Decision: Park Dia. Stay on Gemini + P0 as the cost position.**

**Architectural stance confirmed:** Local/self-hosted TTS (Dia, Chatterbox, Kokoro, Piper)
is ruled out for SaaS production. Generation speed makes it impractical (308s for 4
exchanges on RTX 4070 Super), and hosting a GPU server for TTS at scale adds infrastructure
complexity the boss does not want. API-based TTS is the correct path for all phases.

Next candidate if API cost pressure returns: `gpt-4o-mini-tts` ($12/1M output vs $20/1M)
— but requires per-speaker stitching in tts.py. Only worth revisiting at real SaaS volume.

---

## Guardrails

- Do not switch TTS provider without a controlled sample test (see trial plan in `tts-model-options.md`).
- Do not make the Dia switch in production without boss-chef review of real audio samples.
- For Option C (public SaaS), hosted Dia infrastructure cost must be evaluated separately
  before committing to it over Gemini pay-as-you-go.
- 火山引擎 remains an option only for Chinese-language content; English path stays on Gemini or Dia.

---

## Research Trail

- Handoff: `docs/handoffs/Gemini TTS Model Cost Research Handoff.md` — agent-verified
  model availability and pricing
- Background: `docs/boss/decisions/tts-model-options.md` — Dia, Chatterbox, Kokoro, Piper
  comparison; Dia selected as preferred trial candidate
- Prior mention: `docs/handoffs/Spoticast → Resonova.md` — original 火山引擎 and CosyVoice
  notes
