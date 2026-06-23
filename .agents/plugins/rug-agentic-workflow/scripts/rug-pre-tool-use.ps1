$stdin = [Console]::In.ReadToEnd()
$data = $stdin | ConvertFrom-Json
$toolName = $data.toolCall.name

# RUG orchestrator whitelist — ONLY these tools are allowed directly
$allowed = @(
    'define_subagent',
    'invoke_subagent', 
    'manage_subagents',
    'send_message',
    'manage_todo_list'  # Antigravity equivalent of todo tracking
)

if ($allowed -contains $toolName) {
    $result = @{ decision = 'allow' }
} else {
    $result = @{ 
        decision = 'deny'
        reason = "RUG protocol violation: orchestrator must delegate. Tool '$toolName' is not in the whitelist. Use define_subagent + invoke_subagent instead."
    }
}
[Console]::Out.WriteLine(($result | ConvertTo-Json -Compress))
