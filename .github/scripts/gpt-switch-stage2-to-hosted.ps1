$ErrorActionPreference = "Stop"

$workflowPath = Join-Path $PSScriptRoot "..\workflows\stage2-ci-baseline.yml"
$workflowPath = [System.IO.Path]::GetFullPath($workflowPath)

$content = Get-Content -LiteralPath $workflowPath -Raw -Encoding UTF8
$needle = "    runs-on: [self-hosted, Windows, X64, giclee-ci]"
$replacement = "    runs-on: windows-latest"

$count = ([regex]::Matches($content, [regex]::Escape($needle))).Count
if ($count -ne 3) {
    throw "Expected exactly 3 self-hosted runs-on entries, found $count."
}

$updated = $content.Replace($needle, $replacement)
if ($updated -eq $content) {
    throw "Workflow content did not change."
}

$remaining = ([regex]::Matches($updated, [regex]::Escape($needle))).Count
$hostedCount = ([regex]::Matches($updated, [regex]::Escape($replacement))).Count
if ($remaining -ne 0 -or $hostedCount -ne 3) {
    throw "Hosted runner replacement validation failed. remaining=$remaining hosted=$hostedCount"
}

[System.IO.File]::WriteAllText(
    $workflowPath,
    $updated,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "Updated exactly 3 Stage 2 jobs to windows-latest."
