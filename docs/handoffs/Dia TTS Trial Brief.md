# Dia TTS Trial — Implementation Brief

Date: 2026-06-24
Audience: Manager (RUG)
Chef gates the return before any decision is made.
Status: APPROVED — boss + chef

---

## Goal

Set up the Dia TTS local model in an **independent folder on F: drive** (not inside the
Resonova repo) and generate a two-host audio sample for quality comparison against the
current Gemini TTS baseline. No Resonova code changes in this brief.

---

## Target Directory

Create and work entirely inside:

```
F:\dia-trial\
```

Do NOT touch `F:\GitHub\resonova\` except to read the existing MP3 file listed below.

---

## Phase 1 — Install Dia TTS Server

Clone and set up the Dia TTS Server (HTTP API wrapper around Dia-1.6B):

```
https://github.com/devnen/Dia-TTS-Server
```

Steps:
1. `git clone https://github.com/devnen/Dia-TTS-Server F:\dia-trial\Dia-TTS-Server`
2. `cd F:\dia-trial\Dia-TTS-Server`
3. Read the README for exact install instructions — follow them for Windows + CUDA GPU.
4. Create a venv inside `F:\dia-trial\Dia-TTS-Server\` (do not use the Resonova venv).
5. Install dependencies per the README.
6. Download the `nari-labs/Dia-1.6B` model weights (HuggingFace) — the README will
   specify the download method (usually `huggingface-cli download` or auto on first run).
7. Start the server and confirm it loads on GPU in fp16/bf16.
   Target: ~4.4–8 GB VRAM. The machine has an RTX 4070 Super with 12 GB VRAM.
8. Run a quick sanity test: send a short two-speaker `[S1]/[S2]` transcript via the
   server API and confirm a WAV file is returned.

---

## Phase 2 — Generate the Dia sample

Use the following test script. This is a realistic Resonova-style 3-4 exchange two-host
track commentary (the format used in production after the P0 length cut):

```
[S1] Okay so this one — "Fast Car" by Tracy Chapman, 1988 — it almost didn't exist.
Chapman recorded it in a single afternoon for a demo tape that was only supposed to get
her more gigs in Boston. No label was interested for two years.
[S2] And then Elektra signed her, put it on the debut album, and it became the song of
that summer. What's wild is the production is almost nothing — just her voice, a guitar,
and this incredibly steady bassline that never lets up for four minutes.
[S1] That bassline is doing so much emotional work. It's relentless in the best way —
like the narrator in the song, just keep moving, keep moving. Chapman said she wrote it
thinking about a specific person she grew up with, someone who never got out.
[S2] It hit number six on the Billboard Hot 100 which for a solo acoustic folk track in
1988 was basically unheard of. And it's one of those songs where the story hasn't dated
at all. You hear it now and it still lands exactly the same way.
```

Send this script to the Dia TTS Server API. Save the output as:

```
F:\dia-trial\output\track_fastcar_dia.wav
```

Also convert to MP3 (ffmpeg or equivalent):

```
F:\dia-trial\output\track_fastcar_dia.mp3
```

Record and include in your handoff:
- Generation time (seconds from API call to file saved)
- VRAM peak during generation (if visible from nvidia-smi or server logs)
- Any warnings or errors from the server

---

## Phase 3 — Generate the Gemini baseline

Using the same test script above, generate a Gemini TTS version using the existing
Resonova `tts.py` module. Write a standalone Python script at:

```
F:\dia-trial\gemini_baseline.py
```

The script should:
1. Import `resonova.api.tts` from `F:\GitHub\resonova\` (add to sys.path).
2. Build a dialogue list in the same format `tts.py` expects (list of
   `{"speaker": "Sam"/"Alex", "text": "..."}` dicts).
3. Call `synthesize_dialogue()` and save the output PCM as an MP3 at:
   `F:\dia-trial\output\track_fastcar_gemini.mp3`

Speaker mapping for the script above:
- `[S1]` → Sam
- `[S2]` → Alex

The Resonova venv is at `F:\GitHub\resonova\.venv\` — use it only to run
`gemini_baseline.py`, do not install anything into it.

---

## Output Files Expected

```
F:\dia-trial\output\
    track_fastcar_dia.wav
    track_fastcar_dia.mp3
    track_fastcar_gemini.mp3
```

Both MP3s should be ready for side-by-side listening by the boss.

---

## Handoff Return Format

Return a report with:

```
## Setup
[Did Dia-TTS-Server install and start cleanly? Any blockers?]
[GPU / VRAM confirmed?]

## Dia generation
Generation time: [X seconds]
VRAM peak: [X GB or unknown]
Output file: F:\dia-trial\output\track_fastcar_dia.mp3 [size in MB]
Any issues: [none / describe]

## Gemini baseline generation
Output file: F:\dia-trial\output\track_fastcar_gemini.mp3 [size in MB]
Any issues: [none / describe]

## Notes
[Anything unexpected — model warnings, voice inconsistency noticed during generation,
server errors, etc.]
```

Do not evaluate audio quality — that is for the boss to do by listening.
Chef gates this return before any further action.

---

## Out of Scope

- Do not modify any file inside `F:\GitHub\resonova\`
- Do not integrate Dia into `tts.py` — that is a separate brief pending trial outcome
- Do not trial Chatterbox, Kokoro, or any other model in this brief
- Do not push any commits
