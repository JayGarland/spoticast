# Gemini TTS Model Cost Research — Verification Handoff

Date: 2026-06-24
Task: Research-only — verify which Gemini TTS model is cheapest without quality regression
Status: Pending
Chef will gate the return before any config change is made.

---

## Background

Resonova uses Gemini TTS to synthesize two-speaker (Sam + Alex) English dialogue.
Current model: `gemini-3.1-flash-tts-preview` at **$20/1M output audio tokens**.

Two cheaper Gemini TTS models came up in research but neither is confirmed:

| Claim | Source | Status |
|---|---|---|
| `gemini-2.5-flash-tts` exists at **$10/1M** output | Multiple pricing aggregators | Unverified — may be deprecated |
| `gemini-3.5-flash-tts` exists at **$6/1M** output | One pricing aggregator | Contradicted by official docs search — possibly wrong |

A config-only change (`resonova/config.py` line 41) is all that's needed to switch models — no
code changes required. But we must not switch to a deprecated or non-existent model.

---

## Task: Web Research Only

**Do not edit any files.** Return findings as a structured report.

### Q1 — Is `gemini-2.5-flash-tts` still available?

Check the official Google Gemini API models list and pricing page:
- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/pricing

Look for `gemini-2.5-flash-tts` or `gemini-2.5-flash` with TTS capability under
`response_modalities=["AUDIO"]`. Confirm:
- Is the model listed as active (not deprecated or removed)?
- What is the official price per 1M output audio tokens?
- Is multi-speaker dialogue supported?

### Q2 — Does `gemini-3.5-flash-tts` exist?

One aggregator (rogue-marketing pricing page) listed it at $6/1M output. Official docs
search returned no result for this model. Verify:
- Is `gemini-3.5-flash-tts` a real, available TTS model on the Gemini API?
- If yes: what is the official model ID and price?
- If no: mark the $6/1M claim as false.

### Q3 — Are there any other Gemini TTS models cheaper than `gemini-3.1-flash-tts-preview`?

Check the current models list for any TTS-capable model with lower audio output pricing.
Include the `gemini-3.1-flash-tts` non-preview variant if it exists at a different price.

### Q4 — Quality notes

If any benchmark, blog post, or official release note compares audio quality between
`gemini-2.5-flash-tts` and `gemini-3.1-flash-tts-preview`, include a brief summary.
The product requirement is expressive English radio-host dialogue — accent-free, natural
pacing, emotionally varied. A quality downgrade is not acceptable.

---

## What to Return

A structured report with:

```
## Q1: gemini-2.5-flash-tts availability
Status: [ACTIVE / DEPRECATED / NOT FOUND]
Official price: [$/1M output tokens or N/A]
Multi-speaker: [YES / NO / UNCONFIRMED]
Source URL:

## Q2: gemini-3.5-flash-tts existence
Status: [EXISTS / DOES NOT EXIST]
If exists — official model ID:
If exists — official price:
Source URL:

## Q3: Other cheaper Gemini TTS models
[List any found, with model ID + price + source, or "None found"]

## Q4: Quality comparison notes
[Brief summary or "No benchmark data found"]

## Recommendation
[Which model to switch to, or "Stay on gemini-3.1-flash-tts-preview"]
```

---

## Context for the Agent

- Resonova is an English-language app; Chinese or multilingual quality is not relevant here.
- The TTS pipeline uses `google-genai` SDK with `response_modalities=["AUDIO"]` and
  `speech_config` for multi-speaker voice assignment.
- Model is read from `settings.gemini_tts_model`; a single string change in `config.py`
  is the entire implementation if a switch is warranted.
- Do not recommend switching to a non-Gemini provider — that is a separate decision already
  parked (Dia local trial).
- Chef gates this return before any action is taken.
