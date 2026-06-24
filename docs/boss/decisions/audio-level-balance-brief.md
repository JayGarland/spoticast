# Audio Level Balance Brief

## Customer Issue

Commentary sounds quieter than Spotify music. The transition from generated host audio to mastered music feels uneven and can make users adjust volume repeatedly.

## Current Fix

The frontend keeps commentary at full HTML audio volume and lowers Spotify playback volume with a named constant:

```text
_SPOTIFY_VOLUME = 0.62
```

Reason:

- Generated commentary already plays at `audioEl.volume = 1`.
- Spotify tracks are mastered louder than Gemini TTS commentary.
- Lowering Spotify is safer than over-amplifying commentary and risking clipping.

## Follow-Up If Needed

If the balance still feels wrong after listening tests:

- Tune `_SPOTIFY_VOLUME` upward or downward in small increments.
- Consider normalizing newly generated commentary MP3 files in `resonova/api/audio.py`.
- Keep existing saved episodes in mind; frontend Spotify volume affects old and new episodes, while backend normalization only affects future generated commentary.

