# Chef Continuity Handoff - 2026-06-23

Audience: Agents

## Purpose

This handoff is for the next Codex/Chef instance. The boss wants the next instance to keep the same company role: chef above manager level, not a raw coding worker.

Read first:

- `docs/strategy/ai-agent-company-operating-model.md`
- `docs/strategy/ai-agent-role-job-specs.md`
- `docs/strategy/ai-agent-recruitment-execution-guide.md`
- `docs/strategy/boss-profile.md`
- For performance review: `docs/strategy/agent-performance-weights-2026-06-19.md`

## Current Role

You are chef.

Primary responsibilities:

- Turn boss goals into bounded plans or manager briefs.
- Choose the manager: usually RUG for bounded implementation, gem/gem-orchestrator for diagnosis, OCP for strategy/docs/org.
- Prefer direct CLI manager control when possible:
  `copilot -C "F:\GitHub\resonova" --agent "rug-agentic-workflow:rug-orchestrator" --allow-all --no-ask-user -p "<brief>"`
- Gate every manager output: response, handoff, `git status`, `git diff`, validation, scope.
- Patch small gate issues yourself when cheaper than sending back.
- Commit accepted validated scoped work.
- Do not let managers, auditors, reviewers, or workers approve themselves.

Important boundary:

- Do not solo-build non-trivial multi-file/full-stack features if a manager should be tested. Route to manager first.
- Chef may do scout/discovery, diagnosis, small fixes, gate corrections, final polish, and commit-boundary work.
- Non-trivial product, architecture, budget, release, PR, or pipeline decisions require boss-chef discussion.

## Boss Context

The boss is the CEO/final authority. He may give vague, ambitious, or memory-fragmented goals. Reduce his cognitive load: give concise decisions, exact next action, and preserve important context in lightweight docs.

Boss preferences observed:

- Boss prefers RUG for implementation when the task is bounded.
- Boss expects chef to directly conduct managers through CLI when possible, not only give paste prompts.
- Boss values evidence: handoff, diff, tests, git state, product/customer reports.
- Boss wants commits after validated updates.
- Boss dislikes over-documenting; write docs only when they preserve useful decisions or support continuation.

## Current Git State

At handoff creation:

- Worktree: clean.
- Current recent commits:
  - `81fa9ad` Fix memory-off dropping all personalization, not just the trail
  - `8cf3d5f` Add full product re-audit chef gate (2026-06-23)
  - `dd5c9b1` Relax hidden-page Spotify transition gate
  - `42b02ae` Lower feedback fold threshold to 2 for faster memory effect
  - `643f8ad` Add chef continuity handoff for the next instance
  - `919254e` Restore quick one-click generation from playlist cards
  - `9dd7306` Polish commentary language selector
  - `4de16ff` Implement stance B: tasteful, fourth-wall-preserving taste acknowledgment
  - `5214c9f` Let playlist cards respect generation options
  - `e7dc2e9` Polish language option (default=English) + document it + reinforce chef gate rule
  - `2f85280` Add commentary language option
  - `89ae251` Host-awareness decision: self-contained discussion handoff + mark as checkpoint

Earlier important quota commits:

- `36a4e3d` Add Gemini TTS backup resource failover
- `6d77f29` Handle Gemini TTS quota failures gracefully

## Product State

Resonova MVP is a local/private web app that generates AI commentary around Spotify playlists/tracks.

Core product direction:

- Make a personal AI cast around the user's music.
- Preserve taste-aware commentary without breaking the fourth wall.
- Mobile private use is important; Tailscale/HTTPS was used for phone testing.
- Spotify music playback on mobile browser remains constrained by Web Playback SDK/device visibility.

Recent major areas handled:

- Mobile Spotify playback reliability has many graceful-recovery layers now: diagnostics, recover button, previous/next, skip music, resume state, device visibility handling.
- Hidden-page Spotify transition was relaxed/gracefully handled; locked/background mobile Chrome can still make Spotify Connect device invisible.
- Gemini TTS quota failures now show graceful quota UI, save partial/incomplete state when possible, and avoid blind retries.
- Gemini TTS can fail over to backup API keys from separate Google projects via `GEMINI_TTS_BACKUP_API_KEYS`.
- Library/current-cast trust improved: new casts appear correctly and current/incomplete state is less misleading.
- Language option and memory/taste acknowledgment have been worked on after this quota sequence.

## Current Playback Reality

Known mobile issue class:

When the phone page is hidden/locked, Spotify SDK can be locally `ready` but not visible to Spotify Connect. Typical log:

```text
play:cmd:fail 404:device-not-visible
Spotify device unavailable while page hidden
recovery:fail Spotify device is ready in SDK but not visible to Spotify Connect
```

Current stance:

- This is not primarily auth or network.
- Browser mobile cannot guarantee native-background Spotify behavior.
- Do not chase timer/retry loops.
- Better product behavior is: defer Spotify start while hidden, auto-resume on visible, keep Skip Music fallback, and avoid calling it fatal.
- Fully automatic locked-screen music transition is parked as not reliably solvable in mobile Chrome without native/external-player architecture.

## API / Resource Notes

Gemini:

- `GEMINI_API_KEY` is the general key.
- `GEMINI_TTS_BACKUP_API_KEYS` is the important backup setting for extra TTS capacity.
- Backup keys should come from separate Google projects; same-project keys share quota.
- `GEMINI_TTS_API_KEY` is optional. It only overrides the primary TTS credential; it does not create extra quota if it points to the same project.

Last.fm:

- Optional enrichment only.
- Spotify already supplies useful behavior through authorized recent/top/playlist data.
- Last.fm can add long-term scrobbles, loved tracks, play counts, tags, and extra personalization.
- Not required for MVP operation; defer unless boss already uses Last.fm or wants deeper music-history personalization.

## Manager Workflow

Preferred direct RUG invocation shape:

```powershell
$prompt = @'
You are acting as the RUG manager for Resonova.

Implement the task in:
F:\GitHub\resonova\docs\handoffs\<Implementation Brief>.md

Rules:
- Stay strictly inside the brief.
- Do not commit.
- Protect existing dirty work.
- Produce the required handoff.
'@

copilot -C "F:\GitHub\resonova" --agent "rug-agentic-workflow:rug-orchestrator" --name "<task name>" --allow-all --no-ask-user --output-format text -p $prompt
```

If Copilot reports unavailable agent path, use logical id:

`rug-agentic-workflow:rug-orchestrator`

RUG risks:

- Can overclaim in handoff.
- May touch adjacent unrelated files if brief is loose.
- May need chef correction for parsing edge cases, key secrecy, or scoped staging.

Gate procedure:

1. Read manager handoff.
2. `git status --short`
3. `git diff --stat`
4. Inspect risky diffs.
5. Run validation independently.
6. Patch small issues if cheaper than send-back.
7. Stage only scoped files/hunks.
8. `git diff --cached --check`
9. Commit accepted work.

## Parked / Next Work

Likely next product work:

- Product UX/readiness review follow-up from `docs/handoffs/Product Baseline Release Readiness Review.md`.
- Better mobile control-panel / lock-screen UX if boss/customer keeps reporting confusion.
- Decide whether to recruit/harden internal quality-team role.
- Evaluate reasonix or Copilot `/fleet` only after current product queue stabilizes; do not migrate manager platform on enthusiasm.
- Last.fm setup is optional, not urgent.
- More robust offline/bad-network behavior remains relevant, but avoid pretending Spotify music is offline-cacheable.

Playback parked:

- Fully automatic Spotify music transition while phone is locked/backgrounded in mobile browser.
- Native app/external Spotify-player architecture if this becomes a release blocker.

Resource parked:

- Additional non-Gemini TTS provider fallback.
- Persistent/cross-process quota cooldown store.

## Final Instruction To Next Chef

Start by checking:

```powershell
git status --short
git log --oneline -12
```

Then read the newest boss message literally. Do not keep working on an older ghost request if the boss has changed direction.

