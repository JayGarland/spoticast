# reasonixcli Guide

Audience: Agents

## Purpose

Use `reasonixcli` as a Resonova manager interface when its native strengths fit the
task: long-running DeepSeek sessions, cheap broad-context exploration,
resumable project state, and native `explore` / `task` / `review` / `wait`
coordination.

Do not treat reasonixcli as a GitHub Copilot RUG clone. RUG remains the known
bounded implementation path. reasonixcli is a separate manager option.

Related decision: `docs/agents/manager-interface-decision-reasonix.md`.

## Current Local State

Verified 2026-06-25:

- Installed version: `reasonix v1.8.0`.
- Global config: `%AppData%\reasonix\config.toml`.
- DeepSeek key source: `%AppData%\reasonix\.env`, not Resonova `.env`.
- Active Resonova command:
  `%AppData%\reasonix\commands\reasonixcli.md`.
- Archived misleading command:
  `%AppData%\reasonix\archive\commands\rug-*.md`.
- No project `reasonix.toml` or `.reasonix/` folder is currently required in
  the Resonova repo.
- No MCP servers are currently configured.
- Windows bash sandbox reports unavailable; use isolated worktrees for writes.

## Best-Fit Work

Use reasonixcli for:

- long-running manager investigations,
- broad docs/repo exploration,
- budget-sensitive DeepSeek runs,
- large context reading before Chef writes a precise brief,
- docs or strategy changes in isolated worktrees,
- parallel read-only research slices,
- review/handoff generation.

Use carefully for:

- backend/frontend implementation,
- prompt and memory behavior,
- Spotify SDK and mobile playback work.

Approved status:

- Hired restricted manager interface as of 2026-06-25.
- Product-code work is allowed only in isolated worktrees with explicit file
  scope, validation commands, and Chef gate.
- Evidence: one docs trial, one small frontend navigation trial, and one
  memory/prompt safety trial. The memory/prompt trial found the right issue but
  Chef strengthened the tests before acceptance.

Do not use reasonixcli for:

- direct approval,
- release gates,
- direct main-worktree changes,
- secrets edits,
- product-direction decisions without boss/Chef discussion.

## Standard Invocation

For interactive long-running manager work:

```powershell
cd F:\GitHub\resonova-reasonix-trial
reasonix chat
```

Interactive chat expects a real terminal/TTY. A 2026-06-25 scripted stdin test
using `@('/help','/exit') | reasonix chat -max-steps 2` timed out and had to be
terminated. Do not use shell-wrapper piping to drive `reasonix chat`; use
`reasonix run` for noninteractive tasks, `reasonix serve` for a browser session,
or open `reasonix chat` in a real terminal window for human-supervised manager
work.

Inside Reasonix:

```text
/reasonixcli <bounded manager brief>
```

For one-shot work:

```powershell
cd F:\GitHub\resonova-reasonix-trial
reasonix run "/reasonixcli <bounded manager brief>"
```

Continue the latest session:

```powershell
reasonix chat --continue
reasonix run --continue "<follow-up>"
```

For reasonixcli manager follow-ups, prefer:

```powershell
reasonix run --continue "<follow-up brief>"
```

This keeps the manager run inside the existing Reasonix session and makes
better use of prompt caching. Start a fresh `reasonix run` only when the task
should not inherit the previous manager context.

Choose a specific saved session:

```powershell
reasonix chat --resume
reasonix run --resume <session-path> "<follow-up>"
```

## Browser UI

Reasonix can expose a local browser interface:

```powershell
cd F:\GitHub\resonova-reasonix-trial
reasonix serve
```

Use the default local-only address for local inspection. If binding outside
loopback, enable authentication first. Do not expose a manager session publicly.

## Feature Map For Resonova

`explore`:

- Use for read-only orientation, large docs scans, and "what files matter?"
  questions.
- Good first step before assigning implementation.

`task`:

- Use for bounded implementation or independent research slices.
- Give explicit scope, files allowed, files forbidden, validation, and handoff
  requirements.

`review`:

- Use after a diff or evidence packet exists.
- Ask for bugs, scope drift, missing tests, and spec mismatch before summary.

`wait`:

- Use when Reasonix starts parallel background tasks.
- Chef should require the handoff to state whether `wait` was used and what it
  joined.

Slash commands:

- User commands live under `%AppData%\reasonix\commands\`.
- Project commands can live under `.reasonix/commands/` if we later want
  repo-owned commands.
- Current policy: keep the Resonova manager command global; do not add repo-owned
  Reasonix commands until there is a stronger need.

MCP:

- Reasonix can use MCP servers from config or a project `.mcp.json`.
- No Resonova MCP servers are configured yet.
- Add MCP only when a specific task needs it; avoid broad tool surface by
  default.

Plan / Goal / Rewind:

- Plan mode is useful for non-trivial work that should stay read-only until
  Chef approves execution.
- Goal/AutoResearch is a candidate for long-horizon research, but should be
  trialed separately before relying on it for product work.
- Rewind/checkpoints can help recover from bad turns, but Chef should still
  rely on git worktrees and diffs as the source-control boundary.

Memory:

- Upstream docs describe memory retrieval and Memory v5 behavior.
- The installed `reasonix v1.8.0` help does not expose
  `reasonix config memory-v5`; do not assume that shell command exists locally.
- Treat Reasonix memory as manager-session aid, not product truth.

## Chef Gate Checklist

Before accepting Reasonix output:

1. Inspect Reasonix response and handoff.
2. Inspect `git status --short --branch`.
3. Inspect `git diff`.
4. Run relevant validation independently.
5. For frontend JS, run `node --check resonova/web/player.js` and browser-load
   the app.
6. Confirm no unrelated dirty work was touched.
7. Commit only from Chef/Boss authority after validation.

## Product-Code Trial Rule

For product-code work:

- Require `/reasonixcli`.
- Require `explore` before writing.
- Require `review` after writing.
- Require `git diff --check`.
- Require the relevant tests or static checks named in the brief.
- Require a concise handoff with changed files, validation, review result, risks,
  and primitives used.
- Chef audits the diff and reruns validation before accepting or merging.
