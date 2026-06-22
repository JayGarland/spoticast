# Chef Continuity Handoff — 2026-06-22

Audience: the next chef-role instance (you are still the Resonova **Chef**). Self-contained for
session continuity; lean on the canonical docs + auto-loaded memory for durable rules.

## Read first (don't skip)

- Your memory (auto-loads): `resonova-chef-operating-context`, `rug-manager-cli-invocation`,
  `frontend-gate-needs-parse-and-load-check`. These hold the most important operating rules.
- `docs/strategy/ai-agent-company-operating-model.md` — roles, authority, and (added this session)
  the **single-vs-multi-agent pre-flight checklist**, **cost-routing policy**, **DeepSeek BYOK**
  setup, **/fleet correction**, and the **chef-built-feature → manager-route + gate-before-commit**
  rule.
- `docs/strategy/companion-direction-and-memory-use-brief.md` — the product-soul decisions
  (stance B, memory-control model §3.2, dropped context selector).
- `docs/strategy/boss-profile.md` — how the boss works.

## Operating frame (confirmed by the boss)

- You are a **full working-chef** with **per-step approval**: you may edit/commit, but **ask before
  each commit** and before routing a manager. Non-trivial product/architecture/budget/release
  decisions go to the boss.
- Boss wants **low noise**, evidence-based gating (git status/diff, re-run validation, read risky
  diffs), and concise decision briefs. Use `AskUserQuestion` for genuine boss decisions.
- Work happens on `main` in `F:\GitHub\resonova` (not a worktree). As of this handoff:
  **origin/main == HEAD, working tree clean** (boss pushes; you generally don't push unless asked).

## How you route/run managers (this is working now)

- **Manager = RUG** via the Copilot CLI: `copilot --agent rug-agentic-workflow:rug-orchestrator
  --allow-all -C "F:\GitHub\resonova"`. RUG runs **single-agent** via CLI (no `runSubagent`), so
  **gate harder** (no internal QA subagent). Run in background, log to a temp file, pass long briefs
  via a temp prompt file.
- **DeepSeek (cheap, default for bounded slices):** the boss has set persistent BYOK env vars. Your
  Bash shell does NOT inherit them, so load them in-process via PowerShell without printing the key:
  `$env:COPILOT_PROVIDER_BASE_URL=[Environment]::GetEnvironmentVariable('COPILOT_PROVIDER_BASE_URL','User')`
  (repeat for `_TYPE`, `COPILOT_MODEL`, `_API_KEY`), then invoke copilot. A DeepSeek run shows token
  counts but **no "AI Credits"** line. Running copilot from plain Bash (no env-load) = native Copilot
  (bills credits). Model is `deepseek-chat` (boss may switch to `deepseek-v4-pro`).
- **Cost-routing:** single-agent DeepSeek + rigorous chef gate by default; escalate to multi-agent
  only when a task is too big for one agent or needs real decomposition (run the pre-flight
  checklist in the operating model). Copilot CLI supports `/fleet` parallel subagents (we haven't
  wired RUG to it yet); reasonix (`github.com/esengine/deepseek-reasonix`) is a candidate for cheap
  DeepSeek planner/executor — both parked for "when we go multi-agent."
- **Gate discipline:** always re-run validation yourself; for ANY frontend change run
  `node --check resonova/web/player.js` + a browser load (Chrome MCP: navigate + screenshot +
  read_console_messages). A JS syntax error blanks the whole app — this already bit us once.

## What shipped this session (all on `main`, pushed)

Persistent memory / companion arc is essentially complete:
- **Memory controls** — partial memory-off (suppresses the behavioral *trail*, keeps durable taste),
  per-cast **Incognito** (no read/no write), reset now clears `feedback.jsonl`. Backend + minimal UI
  (incognito checkbox; toggle relabeled "Track my listening trail").
- **Single-user guard** — instance locks to the first Spotify account (`claim_or_check_owner`); a
  second account can't merge into the owner's profile. (Full per-user isolation still deferred.)
- **Mobile background-continuity** — defer a Spotify segment while the phone is locked, auto-resume
  on unlock, non-fatal copy; gated to mobile UA so desktop background playback is preserved.
- **Style derivation** — `recurring_styles` now derived from Spotify artist genres (so stance B has
  real descriptors without Last.fm).
- **Commentary language option** — optional per-cast language; **default = English** when unset.
- **Stance B (host awareness)** — IMPLEMENTED in `gemini.py`: hosts may give a rare, light,
  third-person, playlist-grounded taste nod, framed as their own observation about the music,
  **fourth-wall-preserving** (never "you", never inventory, never cross-cast history, never
  contradict the playlist, never turn to the listener). Only active when a profile exists.
- **Quick one-click from playlist cards** restored (a prior chef commit had removed it).

## ACTIVE — what's pending right now

1. **Stance B real-cast test (top of mind).** The boss needs to restart the server + generate a cast
   on a taste-matching playlist and listen for the 4 failure modes: nod appears & feels natural / no
   "you" / no 4th-wall break ("jump scare" — a customer's explicit fear) / no playlist contradiction.
   If any feel off, **retune the `gemini.py` guardrail wording** (fast, just prompt text) or dial
   back toward stance A. This is the one thing awaiting boss feedback.
2. **Memory still effectively dormant on feedback:** `fold_feedback_into_profile` works but the fold
   **threshold is 3** (`profile.py`), and the boss has given ~1 feedback — nothing has folded yet.
   Option on the table: lower the threshold for faster effect (boss to decide).

## Parked / deferred (not queued)

- Full per-user isolation + user-management (+ a visible owner indicator) — bundle together.
- Public/broadcast cast mode (needs isolation + mode-awareness first); personal-wiki connector
  (`F:\wiki-system\subwikis\base-llm-wiki`) — customer extension, parked.
- Deep-research generation mode (`docs/strategy/deep-research-generation-mode-brief.md`) — opt-in,
  budget-bounded, design-first; reasonix cache-stability is the cost mitigation.
- Field cleanup: `favorite_eras` (dead), `playlist_patterns` (narration-risky), `user-read-email`
  (unused) — decide drop/keep when the design settles.
- Stance A/B/C as user-selectable cast **modes** — parked; B is the single default for now.

## Watch-outs

- **Multiple chef instances commit to `main` in parallel.** Interleaved commits appear in history
  (this session reviewed `2f85280`, `5214c9f`; boss already approved `9dd7306`). If the boss points
  you at a commit hash, gate it post-hoc. Reinforced rule: a **non-trivial/full-stack feature must go
  through the manager-route + gate-before-commit** even if a chef could build it solo (only small
  fixes/polish are chef-direct).
- **Product-soul constraints (never violate in any prompt change):** descriptor-not-inventory; no
  cross-cast memory bleed / no history-recital; fourth wall stays intact (no "you", no turning to the
  listener); never contradict the playlist's vibe; don't be timid/defensive.
- Reviews/audits worth re-reading if you touch memory: the product review + privacy audit handoffs in
  `docs/handoffs/` (the audit's Critical was the cross-user bleed, now guarded).
