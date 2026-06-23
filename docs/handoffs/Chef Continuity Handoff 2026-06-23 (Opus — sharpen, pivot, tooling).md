# Chef Continuity Handoff — 2026-06-23 (Opus session: sharpen + pivot + manager tooling)

Audience: the next chef-role instance (you are still the Resonova **Chef**). Self-contained for
session continuity; lean on the canonical docs + auto-loaded memory for durable rules.

## Read first (don't skip)
- Your auto-memory: `resonova-chef-operating-context`, `rug-manager-cli-invocation`,
  `frontend-gate-needs-parse-and-load-check`, `inspect-only-audit-via-gem-reviewer`,
  **`cursor-agent-manager-interface`**, **`antigravity-cli-headless-recipe`** (the last two are new this session).
- `docs/strategy/ai-agent-company-operating-model.md` — roles, authority, cost-routing, pre-flight.
- `docs/strategy/bounded-personal-music-narrator-pivot.md` + `docs/strategy/memory-gated-stance-note.md` — the product direction (see ACTIVE #1).
- `docs/strategy/sharpen-the-experience-direction.md` — the shipped feature thrust.
- `docs/strategy/boss-profile.md`.

## Operating frame (confirmed)
- Full **working-chef**, **per-step approval**: may edit/commit, but **ask before each commit/manager-route**
  that's non-trivial; route non-trivial multi-file FEATURES to a manager + gate-before-commit. Low noise,
  evidence-based gating, concise decision briefs, `AskUserQuestion` for real boss decisions.
- **You run in a git worktree** (`F:\GitHub\resonova\.claude\worktrees\vigorous-hawking-abb4a9`, branch
  `claude/vigorous-hawking-abb4a9`). The boss runs the app and OTHER chefs work in **main**
  (`F:\GitHub\resonova`). Land changes: commit in worktree → `git rebase main` → `git -C <main> merge --ff-only <branch>`.
  Docs are often edited directly in main. **Sync the worktree to main before each task** (`git merge --ff-only main`).
- **`reload=False`** — the boss must **restart the server** for any code change to go live.

## How you route managers (THREE working interfaces now)
1. **Copilot + RUG on DeepSeek (BYOK)** — default, cheapest, proven. `copilot --agent
   rug-agentic-workflow:rug-orchestrator --allow-all-tools --deny-tool='shell(git commit)' -C <repo> -p "<brief>"`
   with DeepSeek env loaded in-process (see `rug-manager-cli-invocation`). Single-agent → gate harder.
2. **cursor-agent (Cursor CLI)** — clean, reliable, 50+ models; my pick of the alternatives. Wrapper regex
   bug was fixed this session. See `cursor-agent-manager-interface`. `-f`/`--yolo` needs boss authorization.
3. **agy (Antigravity CLI)** — works but finicky; needs the 6-fix recipe (`antigravity-cli-headless-recipe`).
   `--dangerously-skip-permissions` needs boss authorization.
- Auto-approve flags (`--dangerously-skip-permissions`, cursor `-f`) are blocked by the harness classifier
  until the boss explicitly authorizes; the boss cannot be self-granted a *permanent* rule by you.
- **Run any CLI manager via PowerShell `Start-Job` + `Wait-Job -Timeout` synchronously in ONE tool call** —
  `Start-Job` dies across tool calls, and `run_in_background` wrappers don't preserve needed cwd. Gate every
  run (read diff, re-run tests, `node --check` + browser load for web/*.js).

## What shipped this session (all on `main`)
- **Audit + correctness:** full product re-audit chef gate (`8cf3d5f`); memory-off honesty fix (`81fa9ad`);
  blind-playback verify + stale-SSE guard (`66b3005`); **generation resilient to optional-enrichment
  failures** (`a827c90` — a Spotify top-tracks ReadTimeout was aborting whole casts; now best-effort +
  graceful partial-save + dropped the deprecated `audio-features` call + 5s→15s timeout); dropped dead
  `Avg energy: None` from the prompt (`7a877be`); fold threshold 3→2 (`42b02ae`).
- **"Sharpen the experience" thrust:** lenses Depth+Vibe (`0210340`); personalized flow-aware ordering —
  soft taste bias, **never locked** (`9da5282`); shareable episode identity tagline+cover+share (`1e33437`);
  card-polish (`01faf28`, the first change implemented via **agy**).
- **THE PIVOT — bounded Stance C, memory-gated (`25b6477`, just landed, chef-audited):** stance follows the
  memory toggle. memory OFF/incognito → **strict Stance B** (fourth wall); memory ON → **bounded Stance C**
  (may say "you", bounded music-domain playlist-grounded callbacks; thin memory → light, never invent).
  `_persistent_memory_guardrail()` in `gemini.py`; script cache keyed on stance; toggle relabeled
  "Personal music narration". 46 profile tests green incl. 5 new stance tests.
- **Tooling/docs:** cursor + agy chef guides updated with verified recipes; sharpen-direction + memory-gated
  decision notes.

## ACTIVE — pending right now
1. **Bounded-C listening test (TOP OF MIND, the one open gate).** Code passed audit, but C's *feel* needs a
   real-device test. Boss must: restart server → generate a **memory-ON** cast → listen for the 4 failure
   modes (natural "you" / no creepy jump-scare / no invented history / music stays subject). If off → retune
   the C guardrail wording in `_persistent_memory_guardrail` (`gemini.py`, fast prompt-only) or dial back.
   The boss controls stance live via the "Personal music narration" toggle (off = strict B).
2. **Boss to eyeball the new card visuals** (`01faf28`) on a real cast (initial cover, gradient, Copy).

## Parked / deferred
- **Shared/public cast mode + per-user isolation** — HARD dependency for bounded-C beyond single-user:
  personal callbacks must NEVER leak into a shared/public cast. Currently the C guardrail only *instructs*
  this; when shared mode ships it must **structurally force B** (a cast-mode flag), not rely on the prompt.
- Stance-C "degrees" UI (today it's binary via the toggle; the thin-memory ramp is instruction-level).
- Mood/era lenses; flow-aware "energy arc" (NOT feasible — audio-features deprecated/403, don't restore;
  a replacement provider is a separate scoped decision); saved lens presets; deep-research generation mode.
- The cursor share affordance is local clipboard-copy only (no public URL until hosting).

## Watch-outs
- **Multiple chefs commit to `main` in parallel** (all show as author "Jie"). ALWAYS `git log/status` first,
  rebase before landing, and **don't touch another chef's uncommitted WIP unless the boss assigns it**
  (this session the boss had me audit + commit another chef's bounded-C WIP — that was explicit).
- `reload=False` → restart needed for anything to go live.
- **Product-soul constraints are now stance-aware:** memory-OFF/B = strict fourth wall; memory-ON/C = bounded
  callbacks only (no cross-domain bleed, no replay-count/session-history recital, no inventory-as-proof, no
  leak to shared casts, music stays subject). `cast_depth` semantics unchanged by the pivot.
- Frontend gate: `node --check resonova/web/player.js` + browser load (Claude Preview, `.claude/launch.json`
  → `uv run python -m resonova`, `autoPort`) for any web JS change. Tests: `uv run python tests/test_*.py`
  (the bare `python` lacks `google.genai`; `uv run` has it). `uv run` swallows stdout sometimes — capture to a
  file + check exit code + grep.

Good place to hand off. The big open item is the **bounded-C listening test** — start there with the boss.
