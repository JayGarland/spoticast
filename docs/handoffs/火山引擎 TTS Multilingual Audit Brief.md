# 火山引擎 豆包 TTS — Multilingual Performance Audit

Date: 2026-06-24
Task: Research-only — audit multilingual quality of 火山引擎 (Volcengine) Doubao TTS
Audience: Research agent
Chef gates the return.

---

## Background

Resonova is an English-first AI podcast/casting app (two-host dialogue, Sam + Alex).
Current TTS: `gemini-3.1-flash-tts-preview` (API, $20/1M audio output tokens).

**What we already know about 火山引擎 for English:**
- English quality is documented as coming from "data generalization in pretraining, not
  targeted training" — i.e., English is incidental, not designed.
- The podcast/casting model (豆包语音播客大模型) was built for Chinese content.
- English was ruled out as a production path for Resonova's current English casting use case.

**What we don't know:**
- Which other languages (besides Chinese) are first-class in 火山引擎 TTS?
- Is the quality strong enough for expressive two-host podcast dialogue in those languages?
- Could 火山引擎 be the right TTS provider if Resonova expands to French, Spanish,
  Japanese, Korean, or other language markets?
- How does it compare to Gemini TTS across languages?

This audit is forward-looking — for multilingual SaaS planning, not immediate implementation.

---

## Research Questions

### Q1 — Language coverage

Which languages does 火山引擎 豆包 TTS officially support?
- List all supported languages/locales.
- Distinguish between: (a) languages with dedicated voice training, (b) languages supported
  via cross-lingual cloning only, (c) languages listed but with no quality evidence.

Source targets: official Volcengine docs, model release notes, developer community posts.

### Q2 — Quality evidence per language

For each major language (at minimum: Chinese Mandarin, French, Spanish, German, Japanese,
Korean, Portuguese), find any quality evidence:
- Official quality claims or benchmark scores from Volcengine
- Third-party comparisons or developer reviews
- Any mention of accent, naturalness, or expressiveness for that language
- Any known weaknesses (e.g. accent issues, limited voice options, monotone delivery)

The use case for quality assessment is **expressive two-host podcast dialogue** — not just
reading text aloud. Flat/robotic delivery is a disqualifier.

### Q3 — Multi-speaker support per language

The podcast model supports multi-speaker dialogue in Chinese. Does it support multi-speaker
dialogue in other languages?
- Is the `[S1]`/`[S2]` speaker-label transcript format available for non-Chinese languages?
- Or is multi-speaker only available in Chinese?

### Q4 — Pricing by language

Does pricing differ by language or is it flat across all languages?
Official source: https://www.volcengine.com/docs/6561/1359370

### Q5 — Comparison vs Gemini TTS for multilingual

Gemini 3.1 Flash TTS supports 70+ languages with the same expressive multi-speaker model.
Where does 火山引擎 beat Gemini on language quality (if anywhere)?
Particularly interested in: Chinese Mandarin, Japanese, Korean — languages where a Chinese
lab might have an edge over Google.

---

## Output Format

Return a structured report:

```
## Q1: Language coverage
[List of officially supported languages, noting which are first-class vs cross-lingual only]

## Q2: Quality evidence per language
[Per language: quality claim / third-party evidence / known weaknesses / verdict for casting]

## Q3: Multi-speaker support per language
[Supported / Chinese-only / unknown]

## Q4: Pricing by language
[Flat / tiered / unknown — cite source]

## Q5: vs Gemini TTS multilingual
[Where 火山引擎 wins / ties / loses by language]

## Overall verdict
[Which languages, if any, make 火山引擎 worth trialing for Resonova multilingual expansion?
Which languages should stay on Gemini? Anything surprising?]
```

---

## Constraints

- Research only — no account creation, no API calls, no code.
- If a quality claim comes from Volcengine's own marketing, flag it as self-reported.
- If no quality evidence exists for a language, say so — don't invent a verdict.
- Chef gates this return before any decision is made.
