---
name: handoff
description: Write or update a HANDOFF.md file so the next GitHub Copilot / VS Code agent or fresh chat can continue the work.
---

Write or update a project handoff document so the next agent with fresh context can continue this work.

Steps:

1. Check if HANDOFF.md already exists in the project root.
2. If it exists, read it first to understand prior context before updating.
3. Start the document with an Obsidian-style YAML frontmatter block:
   ```yaml
   ---
   title: "<descriptive title for this handoff>"
   source: "<local path, conversation link, or other origin reference — omit if unknown>"
   author: ""
   published: false
   created: <current date in YYYY-MM-DD format>
   description: "<one-sentence summary of what this handoff covers>"
   tags:
     - handoff
   ---
   ```
   - `created` must always be the current date.
   - `source` is required when a source path or conversation link is available; leave it as `""` placeholder if unknown.
   - `title` and `description` should be concise and informative.
4. Below the frontmatter, include the following sections:
   - **Goal**: What we are trying to accomplish.
   - **Current Progress**: What has been done so far.
   - **What Worked**: Approaches that succeeded.
   - **What Didn't Work**: Approaches that failed, so they are not repeated.
   - **Next Steps**: Clear action items for continuing.
   - **Relevant Files**: Files or directories the next agent should inspect.
   - **Constraints**: Things the next agent must not change or must preserve.
   - **Validation Needed**: Tests, checks, or manual verification still needed.

Save as HANDOFF.md in the project root and tell the user the file path so they can start a fresh conversation or switch agent with just that path.
