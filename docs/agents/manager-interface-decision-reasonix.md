# Manager Interface Decision - reasonixcli

Audience: Internal

## Decision

`reasonixcli` should be evaluated and used as its own manager interface, not as a
clone of GitHub Copilot RUG.

The earlier direction tried to copy the RUG/Copilot workflow onto other CLI
manager surfaces. That was the wrong evaluation frame. Resonova already has a
working RUG path where RUG fits. reasonixcli should instead be selected when its
own features match the work: long-running DeepSeek-native sessions, low-cost
large-context exploration, project state, resumable runs, and native
`explore` / `task` / `review` / `wait` orchestration.

## Accepted Position

- Copilot RUG remains the mature implementation manager for bounded patches
  when Chef wants the known RUG workflow.
- reasonixcli is a hired restricted manager interface for long-running,
  budget-sensitive, research-heavy, high-volume, and bounded product-code work.
- reasonixcli should not be judged by whether it perfectly reproduces RUG.
- Do not name the Reasonix command `/rug`; that creates the wrong expectation.
  The installed command is `/reasonixcli`.
- Chef still gates reasonixcli output before commit, merge, or acceptance.

## Current Audit

Verified on 2026-06-25:

- Reasonix version behind reasonixcli: `v1.8.0`.
- DeepSeek key is configured outside the Resonova repo.
- Project-scoped sessions and subagent session files are persisted under the
  Reasonix user data directory.
- `explore`, `task`, `review`, and `wait` worked in no-write smoke tests.
- `reasonix chat --continue`, `reasonix run --continue`, and `--resume` are
  available for long-running work.
- The Windows bash sandbox reported unavailable; shell commands can run
  unconfined. This requires isolated worktrees and Chef gate discipline.
- Product-code trial evidence: reasonixcli produced a small frontend navigation
  fix and a bounded memory/prompt safety fix. Chef accepted the manager as hired
  restricted after independently strengthening tests and validation.

## Best Use

Use reasonixcli for:

- long-running manager investigations,
- broad repo or docs exploration,
- strategy/doc implementation in isolated worktrees,
- cheap DeepSeek-based research and decomposition,
- parallel read-only or low-risk task slices,
- manager handoff generation for Chef review,
- bounded product-code implementation in isolated worktrees.

Use carefully for:

- backend/frontend implementation, only inside isolated worktrees,
- safety-sensitive prompt or memory changes,
- mobile playback and Spotify SDK work that requires browser or real-device
  validation.

Do not use reasonixcli for:

- self-approval,
- direct commits to main without Chef gate,
- release approval,
- product-direction decisions without boss/Chef discussion,
- editing secrets or credentials.

## Operating Rule

When Chef routes work to reasonixcli:

1. Use an isolated worktree unless the task is read-only.
2. Invoke `/reasonixcli`, not `/rug`.
3. Require a handoff with changed files, validation, review result, risks, and
   whether `explore`, `task`, `review`, and `wait` were used.
4. Independently inspect `git status`, `git diff`, and validation output.
5. Product-code output may be accepted only after Chef independently validates
   the diff, tests, and scope.

## Rationale

Manager interfaces should be chosen by role fit, not platform loyalty or
feature cloning. RUG is valuable because it is a disciplined implementation
manager with known review expectations. reasonixcli is valuable because it can be
a cheaper, persistent, long-running DeepSeek manager. These are different
strengths.

The company should keep both paths available and route by task shape.
