---
name: handoff
description: Write or update a handoff document inside docs/handoffs/ so the next agent or fresh session can continue the work.
---

Write or update a project handoff document inside the `docs/handoffs/` directory so the next agent with fresh context can continue the work.

## Naming Conventions
* **Task / Feature Work Handoffs**: Save as `docs/handoffs/<Feature Name> Handoff.md` (e.g. `docs/handoffs/Persistent Profile Slice One Handoff.md`).
* **Session Continuity / Role Handoffs**: Save as `docs/handoffs/<Role> Continuity Handoff YYYY-MM-DD.md` (e.g. `docs/handoffs/Chef Continuity Handoff 2026-06-23.md`).

## Policies
* **Trivial Tasks**: Small fixes, simple polish, or tiny corrections (e.g. minor CSS tweaks or quick string changes) do **NOT** require creating a new manager handoff to avoid codebase documentation noise.
* **Work Handoffs**: Mandatory for non-trivial implementation milestones.
* **Company Handoffs**: Rare, lightweight, and used only for transitions or policy updates.

## Steps

1. Check the `docs/handoffs/` directory for any relevant prior handoffs.
2. Start the document with an Obsidian-style YAML frontmatter block:
   ```yaml
   ---
   title: "<descriptive title for this handoff>"
   source: "<local path, conversation link, or other origin reference — omit if unknown>"
   author: ""
   published: false
   created: YYYY-MM-DD
   description: "<one-sentence summary of what this handoff covers>"
   tags:
     - handoff
   ---
   ```
   - `created` must always be the current date.
   - `source` is required when a source path or conversation link is available; leave it as `""` placeholder if unknown.
   - `title` and `description` should be concise and informative.
3. Below the frontmatter, include the following sections:
   - **Goal**: What we are trying to accomplish.
   - **Current Progress**: What has been done so far.
   - **What Worked**: Approaches that succeeded.
   - **What Didn't Work**: Approaches that failed.
   - **Next Steps**: Clear action items for continuing.
   - **Relevant Files**: Files or directories the next agent should inspect.
   - **Constraints**: Things the next agent must not change or must preserve.
   - **Validation Needed**: Tests, checks, or manual verification still needed.

Save the file in the `docs/handoffs/` directory. Notify the user of the created/updated file path.
