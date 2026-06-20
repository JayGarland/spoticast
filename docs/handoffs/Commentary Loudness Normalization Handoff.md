# Commentary Loudness Normalization Handoff

## Summary

Implemented server-side commentary loudness normalization for newly generated TTS commentary MP3 files.

## Files Changed

- `resonova/api/audio.py`

## Implementation

`assemble_commentary()` still accepts Gemini raw PCM and appends `TRAIL_SILENCE_MS`, but now exports the commentary through ffmpeg `loudnorm` before writing the final MP3.

Target settings:

- Integrated loudness: `-14 LUFS`
- True peak: `-1 dBTP`
- Loudness range: `11`

The implementation writes a temporary WAV, runs ffmpeg with:

```bash
loudnorm=I=-14:TP=-1:LRA=11
```

and exports MP3 with `libmp3lame`.

If ffmpeg normalization fails, the code logs a warning and exports the MP3 without normalization rather than producing a corrupt file.

## Validation

Passed:

```bash
uv run python -c "from resonova.api.audio import assemble_commentary; print('audio import ok')"
uv run python -c "from resonova import server; print('server ok')"
```

Functional smoke:

- Generated a 2-second synthetic PCM tone through `assemble_commentary()`.
- Output file was created successfully.
- ffmpeg loudnorm measurement reported `input_i: -13.99`, matching the `-14 LUFS` target.

## Notes

- This affects future generated commentary only.
- Existing saved episode commentary files remain unchanged.
- Spotify SDK volume trim is unchanged.
- No player, server route, playlist ordering, profile, or feedback behavior was changed.

## Recommended Owner Test

Generate a fresh episode on phone and compare:

1. Commentary -> Spotify music transition.
2. Spotify music -> next commentary transition.

Expected result: less need to adjust phone system volume between speech and music.
