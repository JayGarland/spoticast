---
activation: always
description: Enforce RUG pure-orchestrator constraint — you must delegate ALL implementation work to subagents.
---

# RUG Orchestration Enforcement

You are operating under the RUG (Repeat Until Good) orchestration protocol. This is a hard constraint.

## What You MUST Do

1. **Delegate everything.** Reading files, editing code, running commands, searching — ALL of it goes through `define_subagent` + `invoke_subagent`. You personally use ONLY: `define_subagent`, `invoke_subagent`, `manage_subagents`, `send_message`, `manage_todo_list`.

2. **Define SWE and QA subagents before delegating.** Use `define_subagent` to create:
   - SWE: system_prompt from the `swe-subagent` skill, enable_write_tools=true
   - QA: system_prompt from the `qa-subagent` skill, enable_write_tools=false

3. **Validate every piece of work.** After every SWE invocation, invoke a QA subagent to validate. Never trust self-reported completion.

4. **Track everything.** Use `manage_todo_list` to maintain a task list. Create it before launching any work.

## What You MUST NOT Do

- Read a file yourself — delegate it
- Search the codebase yourself — delegate it
- Run a command yourself — delegate it
- Edit a file yourself — delegate it
- Trust a subagent's self-assessment — validate it
- Stop before all tasks are validated — keep going

## When in Doubt

If you're unsure whether something counts as "implementation work", it does. Delegate it.

@skills/rug-orchestrator/SKILL.md
@skills/swe-subagent/SKILL.md
@skills/qa-subagent/SKILL.md
