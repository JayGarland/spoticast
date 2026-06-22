<#
  Run the RUG manager through DeepSeek via the Copilot CLI's BYOK (Bring Your Own Key) mode.

  DeepSeek is NOT in the Copilot CLI's built-in model routing, so we activate a custom
  OpenAI-compatible provider via environment variables, scoped to THIS process only — it does
  not change your normal Copilot / VS Code usage.

  SETUP (once): put your DeepSeek API key in the placeholder below (or set $env:DEEPSEEK_API_KEY
  in your shell and leave the placeholder as-is — the script prefers the env var if present).

  USAGE:
    .\scripts\run-rug-deepseek.ps1 -Prompt "your manager brief here"
    .\scripts\run-rug-deepseek.ps1 -PromptFile "C:\path\to\brief.txt"
    .\scripts\run-rug-deepseek.ps1            # interactive session

  Confirm the exact DeepSeek model name your account exposes (e.g. deepseek-chat,
  deepseek-reasoner, or deepseek-v4-pro) and pass it with -Model if it isn't the default.
#>
param(
  [string]$Prompt = "",
  [string]$PromptFile = "",
  [string]$Repo = "F:\GitHub\resonova",
  [string]$Model = "deepseek-chat",          # <-- set to "deepseek-v4-pro" if that is your DeepSeek model
  [string]$Agent = "rug-agentic-workflow:rug-orchestrator"
)

# --- BYOK provider config (DeepSeek is OpenAI-compatible) ---
$env:COPILOT_PROVIDER_BASE_URL = "https://api.deepseek.com"
$env:COPILOT_PROVIDER_TYPE     = "openai"
# Prefer an existing DEEPSEEK_API_KEY env var; otherwise use the placeholder you fill in here:
if ($env:DEEPSEEK_API_KEY) {
  $env:COPILOT_PROVIDER_API_KEY = $env:DEEPSEEK_API_KEY
} else {
  $env:COPILOT_PROVIDER_API_KEY = "<YOUR_DEEPSEEK_API_KEY>"   # <-- FILL THIS IN (or set $env:DEEPSEEK_API_KEY)
}
$env:COPILOT_MODEL = $Model
# Optional: map to a well-known base id so the agent applies tool-support/token-limit config.
# $env:COPILOT_PROVIDER_MODEL_ID = "gpt-5.2"

if ($env:COPILOT_PROVIDER_API_KEY -eq "<YOUR_DEEPSEEK_API_KEY>") {
  Write-Warning "DeepSeek API key not set. Edit this script's placeholder or set `$env:DEEPSEEK_API_KEY before running."
}

$common = @("--agent", $Agent, "--allow-all", "-C", $Repo)

if ($PromptFile -ne "") {
  $text = Get-Content -Raw -Path $PromptFile
  copilot -p $text @common
} elseif ($Prompt -ne "") {
  copilot -p $Prompt @common
} else {
  copilot @common
}
