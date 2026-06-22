# TTS Model Options

Audience: Internal

## Purpose

This note records current optional TTS findings for Resonova's budget/resource planning. It is not an implementation approval and does not change the current production/default TTS path.

Current preference: **trial Dia first** because Resonova's product format is naturally two-host dialogue. Keep Gemini TTS as the current quality baseline until an alternative beats it in a controlled sample.

## Current Baseline

Gemini TTS remains the working baseline because it already fits the current pipeline:

- multi-speaker host commentary
- generated MP3 assets saved for replay
- existing integration and failure handling
- known quality level for current episodes

The issue is budget/resource pressure, not immediate functional failure. A roughly 10-song cast can cost about 0.6 EUR end to end after research, script writing, and voice synthesis. Repeated experiments, richer context injection, and customer usage can make this cost painful.

## Findings

### Piper

Piper is useful as a local/offline fallback, but not the current preferred expressive-host candidate.

Observed product fit:

- Good for cheap/local reading.
- Weak for Resonova's desired host performance: tune, emotion, pacing variety, and expressive two-host energy.

Decision:

- Keep as possible emergency/dev fallback.
- Do not prioritize as the main replacement for Gemini TTS.

Source:

- https://github.com/OHF-voice/piper1-gpl

### Kokoro

Kokoro is a strong lightweight local candidate and appears practical for cost-sensitive usage.

Fit:

- Open-weight, small, fast, and deployable on modest hardware.
- Better candidate than Piper for lightweight local quality.

Limit:

- Not the best match for Resonova's natural two-host dialogue requirement.
- Likely weaker than Dia or Chatterbox for expressive radio-host performance.

Decision:

- Keep as a low-cost fallback candidate.
- Do not trial first unless the goal is speed/resource minimization.

Sources:

- https://github.com/hexgrad/kokoro
- https://huggingface.co/hexgrad/Kokoro-82M

### Chatterbox

Chatterbox is a strong expressive TTS candidate.

Fit:

- Stronger expression controls than Piper/Kokoro.
- Supports emotion/exaggeration control and voice cloning.
- Good candidate if Resonova needs expressive single-speaker or manually separated host voices.

Resource estimate for boss machine:

- On a 32 GB RAM machine with RTX 4070 Super 12 GB VRAM, Chatterbox should be feasible for trials.
- Budget roughly 6-8 GB VRAM for smoother use; optimized setups may be lower, but do not plan around best-case community reports.
- Chatterbox Turbo is lighter than the 500M variants and may be a useful speed-focused fallback.

Limit:

- Less naturally aligned than Dia for two-host dialogue. Resonova would likely generate host A and host B separately, then stitch segments, unless a specific Chatterbox setup proves otherwise.

Decision:

- Trial after Dia if Dia is too unstable, too slow, or too hard to integrate.
- Keep as expressive fallback candidate.

Sources:

- https://www.resemble.ai/learn/models/chatterbox
- https://www.resemble.ai/learn/models/chatterbox-turbo
- https://github.com/resemble-ai/chatterbox
- https://github.com/devnen/Chatterbox-TTS-Server/blob/main/documentation.md

### Dia

Dia is the current preferred optional TTS trial candidate.

Fit:

- Built for realistic dialogue, not just one-speaker reading.
- Supports speaker-style transcript patterns and audio conditioning for tone/emotion.
- Can produce nonverbal communications such as laughter, coughing, or throat clearing.
- Better aligned with Resonova's two-host radio/cast format than Piper, Kokoro, or Chatterbox.

Resource estimate for boss machine:

- Boss machine: 32 GB RAM + RTX 4070 Super 12 GB VRAM.
- Dia should be feasible for trials on this hardware if using fp16/bf16 and keeping other GPU-heavy apps closed.
- Official/project-adjacent references report roughly 4.4 GB VRAM in fp16/bf16 on RTX 4090 benchmarks, around 7.9 GB in fp32, and around 10 GB VRAM for the full version in some Hugging Face guidance.
- Treat 12 GB VRAM as enough for experiments, but not unlimited: chunk long scripts, measure speed, and watch memory fragmentation.

Risks:

- Long-form episode stability is not proven for Resonova.
- Voice consistency across many chunks must be tested.
- It may be slower or more operationally complex than Gemini TTS.
- English-focused support may constrain future multilingual plans.

Decision:

- **Trial Dia first** as the best product-fit alternative to Gemini TTS.
- Keep Gemini TTS as quality baseline until Dia produces acceptable two-host samples.
- Do not switch production/default TTS without boss-chef review of real audio samples.

Sources:

- https://github.com/nari-labs/dia
- https://huggingface.co/nari-labs/Dia-1.6B
- https://github.com/devnen/Dia-TTS-Server

## Trial Plan

Use a small A/B sample before any implementation migration:

1. Pick one 60-90 second Resonova two-host script.
2. Generate the same script with Gemini TTS and Dia.
3. Optionally generate with Chatterbox and Kokoro for comparison.
4. Compare:
   - host separation
   - expressiveness and tune
   - pacing and pauses
   - nonverbal support
   - voice consistency across chunks
   - generation time
   - VRAM/RAM use
   - MP3 export and saved-episode compatibility
5. Decide whether Dia deserves an implementation brief.

## Guardrails

- Do not replace Gemini TTS immediately.
- Do not use voice cloning without explicit rights/consent for reference voices.
- Do not judge by one short demo only; test at least one realistic Resonova dialogue excerpt.
- Keep script-generation and TTS-provider decisions separate.
- Record model, settings, hardware, generation time, and subjective quality notes for each sample.
