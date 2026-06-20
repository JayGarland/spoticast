# Commentary Loudness Normalization Implementation Brief

## Intended Manager

Use **RUG manager** for implementation.

This is a bounded audio-quality fix. Do not touch Spotify SDK recovery, playback controls, playlist ordering, or persistent profile/feedback.

## Parent Audit

- `docs/handoffs/External Audio Balance and Replay Variety Audit Report.md`
- `docs/handoffs/External Audio Balance and Replay Variety Audit Handoff.md`

## Problem

Owner reports commentary is quieter/smaller than Spotify music.

Current code:

- `resonova/api/audio.py`
  - `assemble_commentary()` converts Gemini raw PCM to MP3.
  - It appends 800 ms trailing silence.
  - It does **no** loudness normalization, compression, or gain staging.
- `resonova/web/player.js`
  - Commentary plays at `audioEl.volume = 1`.
  - Spotify volume is reduced by `_SPOTIFY_VOLUME = 0.62`, but SDK volume control can be unreliable/no-op on mobile.

Conclusion: frontend Spotify trim is not enough. We need to normalize commentary audio at generation time.

## Goal

Normalize generated commentary MP3s server-side so new episodes have consistent perceived loudness across phone and desktop.

Preferred target:

- Integrated loudness: about `-14 LUFS`
- True peak: about `-1 dBTP`
- Loudness range: about `11`

Use ffmpeg `loudnorm` if practical through pydub/ffmpeg tooling already present. If exact two-pass loudnorm is too heavy, implement a simple, bounded one-pass loudnorm and document the tradeoff.

## Files In Scope

- `resonova/api/audio.py`
- Optional: tests if the repo has a suitable test location
- Optional: `docs/handoffs/Commentary Loudness Normalization Handoff.md`

Avoid changing:

- `resonova/web/player.js` unless a tiny `_SPOTIFY_VOLUME` note is necessary
- saved episode metadata
- Spotify SDK recovery code

## Required Behavior

1. `assemble_commentary(pcm_bytes, filename)` still returns the output `Path`.
2. It still accepts Gemini raw PCM: 16-bit signed, 24 kHz, mono.
3. It still appends `TRAIL_SILENCE_MS`.
4. The exported MP3 should be loudness-normalized.
5. If ffmpeg normalization fails, generation should fail clearly or fall back safely with a warning. Do not silently produce corrupted audio.

## Suggested Implementation

Option A, preferred:

- Build `AudioSegment` as today.
- Export a temporary wav or mp3.
- Run ffmpeg with:

```bash
ffmpeg -y -i input.wav -af loudnorm=I=-14:TP=-1:LRA=11 output.mp3
```

- Replace temp handling with safe temporary files under a temp directory.
- Clean up temp files.

Option B, acceptable fallback:

- Use pydub normalization/target dBFS if ffmpeg filter integration becomes too large.
- Document that this is less perceptual than LUFS.

## Acceptance Tests

Static:

```bash
uv run python -c "from resonova.api.audio import assemble_commentary; print('audio import ok')"
uv run python -c "from resonova import server; print('server ok')"
```

Functional smoke:

```bash
uv run python - <<'PY'
from pathlib import Path
from resonova.api.audio import assemble_commentary
pcm = (b'\x00\x00' * 24000)  # 1 second silence PCM
p = assemble_commentary(pcm, 'test-normalized.mp3')
print(p, Path(p).exists(), Path(p).stat().st_size)
PY
```

If ffmpeg is available, measure:

```bash
ffmpeg -i generated/test-normalized.mp3 -af loudnorm=print_format=json -f null -
```

Phone/owner acceptance:

- Generate a fresh episode.
- Play commentary -> Spotify -> commentary at fixed phone system volume.
- Owner should not need to adjust volume between commentary and music.

## Old Episodes

This fix affects future generated commentary only.

Do not batch-normalize old episodes in this task. If needed, propose a separate one-time migration.

## Do Not Do

- Do not add a user-facing balance slider.
- Do not rely on Spotify SDK `setVolume()` as the primary mobile fix.
- Do not modify Spotify SDK recovery.
- Do not normalize Spotify music.
- Do not alter playlist ordering.
- Do not expose `.env` or secrets.

## Expected Handoff

Return:

- Changed files.
- Exact normalization approach used.
- Validation commands and outputs.
- Whether ffmpeg/loudnorm was available.
- Any tradeoff if fallback normalization was used.
