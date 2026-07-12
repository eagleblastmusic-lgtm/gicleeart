[CmdletBinding()]
param(
    [string]$ToolRoot = "",
    [string]$ScanRoot = "C:\Strona\pusty\cursor-api",
    [string]$StagingRoot = "C:\Strona\_gicleeapp_staging",
    [string]$OutputRoot = (Join-Path $env:TEMP "gicleeapp-repository-safety")
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-CheckedPython {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    Write-Host ""
    Write-Host "=== $Label ===" -ForegroundColor Cyan
    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

if ([string]::IsNullOrWhiteSpace($ToolRoot)) {
    $ToolRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
else {
    $ToolRoot = (Resolve-Path $ToolRoot).Path
}
$ScanRoot = (Resolve-Path $ScanRoot).Path
$StagingRoot = (Resolve-Path $StagingRoot).Path
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$AuditJson = Join-Path $OutputRoot "gicleeapp-tracked-tree.json"
$AuditText = Join-Path $OutputRoot "gicleeapp-tracked-tree.txt"
$MigrationJson = Join-Path $OutputRoot "gicleeapp-migration-dry-run.json"
$MigrationText = Join-Path $OutputRoot "gicleeapp-migration-dry-run.txt"
$SnapshotJson = Join-Path $OutputRoot "gicleeapp-snapshot-dry-run.json"
$SnapshotText = Join-Path $OutputRoot "gicleeapp-snapshot-dry-run.txt"

Write-Host "Tool checkout: $ToolRoot"
Write-Host "Scanned cursor-api: $ScanRoot"
Write-Host "Read-only staging target: $StagingRoot"

Push-Location $ToolRoot
try {
    Invoke-CheckedPython -Label "Focused repository-safety tests" -Arguments @(
        "-m", "pytest",
        "tests/test_gicleeapp_push.py",
        "tests/test_gicleeapp_push_allowlist.py",
        "tests/test_repository_safety.py",
        "tests/test_repository_migration_profiles.py",
        "tests/test_repository_snapshot.py",
        "tests/test_repository_policy_inventory.py",
        "tests/test_repository_safety_runbook.py",
        "-q"
    )

    Invoke-CheckedPython -Label "Compile repository-safety package" -Arguments @(
        "-m", "compileall", "-q",
        "Komponenty/integracjagpt/gicleeapp_push.py",
        "tools/repository_safety"
    )

    Write-Host ""
    Write-Host "=== Full tracked-tree audit of canonical cursor-api ===" -ForegroundColor Cyan
    & python -m tools.repository_safety audit --repo $ScanRoot --json-out $AuditJson 2>&1 |
        Tee-Object -FilePath $AuditText
    $AuditExitCode = $LASTEXITCODE
    Write-Host "Tracked-tree audit exit code: $AuditExitCode"
    Write-Host "A non-zero audit code is expected while tracked runtime/private files still exist."

    Write-Host ""
    Write-Host "=== Canonical migration discovery including untracked files (DRY-RUN ONLY) ===" -ForegroundColor Cyan
    & python -m tools.repository_safety migrate --repo $ScanRoot --profile all --include-untracked --json-out $MigrationJson 2>&1 |
        Tee-Object -FilePath $MigrationText
    if ($LASTEXITCODE -ne 0) {
        throw "Migration dry-run failed with exit code $LASTEXITCODE."
    }

    Write-Host ""
    Write-Host "=== Canonical allowlist snapshot plan (DRY-RUN ONLY) ===" -ForegroundColor Cyan
    & python -m tools.repository_safety snapshot --source $ScanRoot --staging $StagingRoot --json-out $SnapshotJson 2>&1 |
        Tee-Object -FilePath $SnapshotText
    if ($LASTEXITCODE -ne 0) {
        throw "Snapshot dry-run failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "=== LOCAL VALIDATION COMPLETE ===" -ForegroundColor Green
Write-Host "The canonical cursor-api and staging repositories were read only."
Write-Host "No data was copied, moved, overwritten or deleted."
Write-Host "No repository mutation or Shopify deployment was executed."
Write-Host "Reports:" -ForegroundColor Yellow
Write-Host "  Audit JSON:      $AuditJson"
Write-Host "  Audit text:      $AuditText"
Write-Host "  Migration JSON:  $MigrationJson"
Write-Host "  Migration text:  $MigrationText"
Write-Host "  Snapshot JSON:   $SnapshotJson"
Write-Host "  Snapshot text:   $SnapshotText"
Write-Host ""
Write-Host "Review the reports before any separate migration copy operation."
