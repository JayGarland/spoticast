# Small Correctness Honesty Bundle Handoff

Date: 2026-06-21
Owner: Chef
Status: Implemented, not committed

## Scope Completed

- Fixed the shared outro audio path in `resonova/server.py`.
  - Outro files now save under the current episode directory as `episodes/{episode_id}/outro.mp3`.
  - The saved queue and `outro_ready` event now point at the episode-local URL.
- Updated visible app copy in `resonova/web/index.html`.
  - Removed the current-state claim that Resonova has listening memory.
  - Removed the landing-page `brew install ffmpeg` developer requirement from the normal user surface.
  - Added Windows-aware paste shortcuts beside the Mac shortcuts.
- Updated `README.md` to separate current developer setup from v0.1 direction.
  - Current product is described as in development, not already memory-backed.
  - Long-term memory/profile language is framed as planned direction.
  - Prerequisite hints now include Windows-oriented ffmpeg and uv guidance.
- Added a minimal `prefers-reduced-motion` override in `resonova/web/styles.css`.

## Validation

- `uv run python -c "from resonova import server; print('server ok')"` passed.
- `uv run python tests/test_variety_episodes.py` passed.
- `git diff --check -- resonova/server.py resonova/web/index.html resonova/web/styles.css README.md` reported no whitespace errors.
  - Git did report line-ending warnings: these files will be converted from LF to CRLF the next time Git touches them.

## Files Changed

- `resonova/server.py`
- `resonova/web/index.html`
- `resonova/web/styles.css`
- `README.md`
- `docs/handoffs/Small Correctness Honesty Bundle Handoff.md`

## Remaining Risks

- No live browser or real Spotify phone playback test was run in this bundle.
- The blind playback verification task remains separate and should still happen before adding more recovery logic.
- The README still documents developer setup because the repo is currently developer-facing; this does not approve hosted v0.1 architecture.
- No profile, feedback, billing, cloud account, subscription, multi-source, PWA, or native-app work was implemented.

## Recommended Next Gate

Chef/boss should review the diff, then decide whether to route the playback observability + stall verification task to a technical QA auditor before any further reliability code.
