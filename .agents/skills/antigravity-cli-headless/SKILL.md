---
name: antigravity-cli-headless
description: "Guidelines and recipes for running the Antigravity CLI (agy) in headless mode on Windows."
---

# Headless Antigravity CLI Recipes (Windows)

When executing `agy` jobs programmatically in the background without user interaction, you must follow this 6-step recipe:

1. **Authentication**: Confirm the user is logged in (`agy models` runs without auth error).
2. **Disable Tool Whitelists**: Ensure `.agents/plugins/rug-agentic-workflow/hooks.json` has `rug-tool-whitelist` set to `enabled: false` (to allow write tools without subagent support).
3. **C: Drive Working Directory**: The `agy` transcript pathing resolver defaults to the active drive root. You must set the working directory to `C:\Users\Administrator` inside the task execution block to avoid silent execution aborts.
4. **Absolute File Paths**: Pass absolute file paths for the `--add-dir` workspace and task briefs, since relative paths will resolve against the `C:` drive cwd.
5. **Model Support**: Use `Gemini 3.5 Flash (High)` or `Gemini 3.5 Flash (Medium)`. Do NOT use Claude models in headless mode, as they can hang.
6. **Synchronous Wrapper**: Run the command inside a PowerShell job using `Start-Job` and `Wait-Job -Timeout` in a single tool call to prevent job termination across tool calls.

### Example Invocation
```powershell
$job = Start-Job { Set-Location "C:\Users\Administrator"
  & "C:\Users\Administrator\AppData\Local\agy\bin\agy.exe" --add-dir "F:\GitHub\resonova" `
    --model "Gemini 3.5 Flash (High)" --print "F:\GitHub\resonova\path\to\task_brief.txt" `
    --log-file "F:\GitHub\resonova\log\agy_task.log" --print-timeout 420s --dangerously-skip-permissions }
Wait-Job $job -Timeout 460; Receive-Job $job
```
