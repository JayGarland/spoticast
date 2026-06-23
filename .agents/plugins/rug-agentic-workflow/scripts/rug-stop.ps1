$stdin = [Console]::In.ReadToEnd()
$data = $stdin | ConvertFrom-Json
$reason = $data.terminationReason

# RUG orchestrator should not stop while there's work remaining
# If the model stops on its own (model_stop), force continue
# This matches RUG's "Repeat Until Good" philosophy
if ($reason -eq 'model_stop' -and $data.fullyIdle -eq $true) {
    $result = @{
        decision = 'continue'
        reason = 'RUG protocol: verify all tasks complete. Produce handoff before stopping.'
    }
} else {
    $result = @{ decision = 'allow' }
}
[Console]::Out.WriteLine(($result | ConvertTo-Json -Compress))
