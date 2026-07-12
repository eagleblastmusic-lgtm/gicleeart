param(
    [string]$ToolRoot = "",
    [string]$ScanRoot = "C:\Strona\pusty\cursor-api",
    [string]$ExpectedHead = "",
    [string]$ReportsRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

if ([string]::IsNullOrWhiteSpace($ToolRoot)) {
    $ToolRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    $ToolRoot = (Resolve-Path $ToolRoot).Path
}
$ScanRoot = (Resolve-Path $ScanRoot).Path

if ([string]::IsNullOrWhiteSpace($ReportsRoot)) {
    $ReportsRoot = Join-Path $env:TEMP ("gicleeapp-stage1f-cleanup-validation-" + [guid]::NewGuid().ToString("N"))
}
New-Item -ItemType Directory -Path $ReportsRoot -Force | Out-Null
$ReportsRoot = (Resolve-Path $ReportsRoot).Path

function Invoke-Checked {
    param([string]$Label, [scriptblock]$Command)
    & $Command | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

function Get-GitStatus {
    param([string]$Root)
    $lines = @(& git -C $Root status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read Git status for: $Root"
    }
    return @($lines)
}

function Get-NormalizedIdList {
    param([object]$Value)
    if ($null -eq $Value) {
        return @()
    }
    return @($Value | ForEach-Object { [int64]$_ } | Sort-Object -Unique)
}

$manifestPath = Join-Path $ToolRoot "docs\repository_safety\STAGE_1F_TRACKED_CLEANUP_ALLOWLIST.json"
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$items = @($manifest.paths)
$migratable = @($items | Where-Object { [bool]$_.copy_required })
$generated = @($items | Where-Object { -not [bool]$_.copy_required })

if ($items.Count -ne 111 -or $migratable.Count -ne 109 -or $generated.Count -ne 2) {
    throw "Unexpected cleanup manifest counts."
}

$actualHead = (& git -C $ToolRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Could not resolve validation worktree HEAD."
}
if (-not [string]::IsNullOrWhiteSpace($ExpectedHead) -and $actualHead -ne $ExpectedHead) {
    throw "Unexpected HEAD: $actualHead"
}

$toolStatusBefore = @(Get-GitStatus -Root $ToolRoot)
if ($toolStatusBefore.Count -gt 0) {
    $toolStatusBefore | ForEach-Object { Write-Host $_ }
    throw "Validation worktree is not clean."
}
$sourceStatusBefore = @(Get-GitStatus -Root $ScanRoot)

Write-Host "=== Verify tracked cleanup allowlist ==="
$tracked = @(& git -C $ToolRoot ls-files)
if ($LASTEXITCODE -ne 0) {
    throw "Could not enumerate tracked files."
}
$trackedSet = @{}
foreach ($path in $tracked) { $trackedSet[[string]$path] = $true }
foreach ($item in $items) {
    $path = [string]$item.path
    if ($trackedSet.ContainsKey($path)) {
        throw "Cleanup path is still tracked: $path"
    }
    & git -C $ToolRoot check-ignore --no-index --quiet -- $path
    if ($LASTEXITCODE -ne 0) {
        throw "Cleanup path is not ignored: $path"
    }
}

Write-Host "=== Verify zero tracked-tree blockers ==="
$auditJson = Join-Path $ReportsRoot "cleanup-branch-audit.json"
Push-Location $ToolRoot
try {
    Invoke-Checked -Label "Repository safety audit" -Command {
        & python -m tools.repository_safety audit --repo $ToolRoot --json-out $auditJson
    }
} finally {
    Pop-Location
}
$audit = Get-Content -LiteralPath $auditJson -Raw -Encoding UTF8 | ConvertFrom-Json
if ([int]$audit.blocker_count -ne 0 -or -not [bool]$audit.ok) {
    throw "Cleanup branch still contains tracked-tree blockers."
}

Write-Host "=== Verify AppData copies against canonical sources ==="
$migrationJson = Join-Path $ReportsRoot "canonical-post-cleanup-copy-verification.json"
$migrationExitCode = $null
Push-Location $ToolRoot
try {
    & python -m tools.repository_safety migrate --repo $ScanRoot --profile all --include-untracked --json-out $migrationJson | Out-Host
    $migrationExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
if ($migrationExitCode -notin @(0, 1)) {
    throw "Canonical AppData verification failed with unexpected exit code $migrationExitCode."
}
if (-not (Test-Path -LiteralPath $migrationJson -PathType Leaf)) {
    throw "Canonical AppData verification did not create its JSON report."
}

$migration = Get-Content -LiteralPath $migrationJson -Raw -Encoding UTF8 | ConvertFrom-Json
if (@($migration.errors).Count -gt 0) {
    throw "Canonical AppData verification contains migration errors."
}

$bySource = @{}
foreach ($entry in @($migration.items)) {
    $bySource[[string]$entry.source] = $entry
}

# The canonical checkout can still run pre-import code that updates only the
# legacy last_sync_iso field. This narrow exception is accepted only when Git
# proves that exactly that one JSON line changed and the business-state arrays
# are identical to the AppData state. No file is copied or overwritten here.
$timestampOnlyLegacyDriftPaths = @{
    "Komponenty/dokumentysprzedazy/dane/orders_sync_state.json" = $true
}
$verifiedExactCount = 0
$verifiedTimestampOnlyDriftCount = 0

foreach ($item in $migratable) {
    $path = [string]$item.path
    $sourcePath = Join-Path $ScanRoot $path
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Canonical source is missing before cleanup import: $sourcePath"
    }
    if (-not $bySource.ContainsKey($path)) {
        throw "Migration report is missing cleanup source: $path"
    }

    $entry = $bySource[$path]
    if ([string]$entry.classification -ne [string]$item.classification) {
        throw "Migration classification mismatch for: $path"
    }

    $status = [string]$entry.status
    $sourceHash = [string]$entry.source_sha256
    $destinationHash = [string]$entry.destination_sha256

    if ($status -eq "verified_existing") {
        if ([string]::IsNullOrWhiteSpace($sourceHash) -or $sourceHash -ne $destinationHash) {
            throw "AppData SHA-256 mismatch for: $path"
        }
        $verifiedExactCount += 1
        continue
    }

    if ($status -eq "conflict" -and $timestampOnlyLegacyDriftPaths.ContainsKey($path)) {
        & git -C $ScanRoot ls-files --error-unmatch -- $path | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Timestamp-only legacy fallback is not tracked in the canonical checkout: $path"
        }

        & git -C $ScanRoot diff --cached --quiet -- $path
        $stagedExitCode = $LASTEXITCODE
        if ($stagedExitCode -eq 1) {
            throw "Timestamp-only legacy fallback has staged changes: $path"
        }
        if ($stagedExitCode -ne 0) {
            throw "Could not verify staged state for timestamp-only legacy fallback: $path"
        }

        & git -C $ScanRoot diff --quiet -- $path
        $workingDiffExitCode = $LASTEXITCODE
        if ($workingDiffExitCode -eq 0) {
            throw "Timestamp-only legacy fallback is not locally modified: $path"
        }
        if ($workingDiffExitCode -ne 1) {
            throw "Could not verify working-tree state for timestamp-only legacy fallback: $path"
        }

        $diffLines = @(& git -C $ScanRoot diff --unified=0 -- $path)
        if ($LASTEXITCODE -ne 0) {
            throw "Could not inspect timestamp-only legacy diff: $path"
        }
        $changedLines = @(
            $diffLines | Where-Object {
                ($_ -match "^[+-]") -and ($_ -notmatch "^(---|\+\+\+)")
            }
        )
        if ($changedLines.Count -ne 2) {
            throw "Legacy fallback diff contains more than one replaced line: $path"
        }
        foreach ($line in $changedLines) {
            if ($line -notmatch '"last_sync_iso"\s*:') {
                throw "Legacy fallback diff changes data other than last_sync_iso: $path"
            }
        }

        if ([string]::IsNullOrWhiteSpace($sourceHash) -or [string]::IsNullOrWhiteSpace($destinationHash)) {
            throw "Timestamp-only legacy conflict is missing SHA-256 evidence: $path"
        }
        if ($sourceHash -eq $destinationHash) {
            throw "Timestamp-only legacy conflict unexpectedly has identical hashes: $path"
        }

        $destinationPath = [string]$entry.destination
        if (-not (Test-Path -LiteralPath $destinationPath -PathType Leaf)) {
            throw "Timestamp-only legacy AppData file is missing: $path"
        }

        $sourceState = Get-Content -LiteralPath $sourcePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $destinationState = Get-Content -LiteralPath $destinationPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $expectedStateKeys = @("last_sync_iso", "notified_order_ids", "pending_order_ids") | Sort-Object
        $sourceStateKeys = @($sourceState.PSObject.Properties.Name | Sort-Object)
        $destinationStateKeys = @($destinationState.PSObject.Properties.Name | Sort-Object)
        if (($sourceStateKeys -join "`n") -ne ($expectedStateKeys -join "`n")) {
            throw "Timestamp-only legacy source contains unexpected JSON keys: $path"
        }
        if (($destinationStateKeys -join "`n") -ne ($expectedStateKeys -join "`n")) {
            throw "Timestamp-only AppData destination contains unexpected JSON keys: $path"
        }

        $sourcePending = @(Get-NormalizedIdList -Value $sourceState.pending_order_ids)
        $destinationPending = @(Get-NormalizedIdList -Value $destinationState.pending_order_ids)
        $sourceNotified = @(Get-NormalizedIdList -Value $sourceState.notified_order_ids)
        $destinationNotified = @(Get-NormalizedIdList -Value $destinationState.notified_order_ids)
        if (($sourcePending -join ",") -ne ($destinationPending -join ",")) {
            throw "Timestamp-only legacy pending-order state differs from AppData: $path"
        }
        if (($sourceNotified -join ",") -ne ($destinationNotified -join ",")) {
            throw "Timestamp-only legacy notified-order state differs from AppData: $path"
        }

        $sourceTimestamp = [DateTimeOffset]::Parse(
            [string]$sourceState.last_sync_iso,
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::RoundtripKind
        )
        $destinationTimestamp = [DateTimeOffset]::Parse(
            [string]$destinationState.last_sync_iso,
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::RoundtripKind
        )
        if ($sourceTimestamp -le $destinationTimestamp) {
            throw "Timestamp-only legacy timestamp is not newer than AppData: $path"
        }

        Write-Host "Accepted timestamp-only legacy drift: $path"
        $verifiedTimestampOnlyDriftCount += 1
        continue
    }

    throw "AppData cleanup prerequisite is not verified for: $path (status: $status)"
}

if (($verifiedExactCount + $verifiedTimestampOnlyDriftCount) -ne $migratable.Count) {
    throw "Not all cleanup migration prerequisites were verified."
}

Write-Host "=== Run cleanup contract tests ==="
Push-Location $ToolRoot
try {
    Invoke-Checked -Label "Cleanup contract tests" -Command {
        & python -m pytest tests/test_repository_safety_tracked_cleanup.py tests/test_repository_safety.py tests/test_repository_policy_inventory.py tests/test_stage1e_external_stores_8_sales_sync_artifacts.py -q
    }
} finally {
    Pop-Location
}

$toolStatusAfter = @(Get-GitStatus -Root $ToolRoot)
$sourceStatusAfter = @(Get-GitStatus -Root $ScanRoot)
if (($toolStatusBefore -join "`n") -ne ($toolStatusAfter -join "`n")) {
    throw "Validation worktree Git status changed during validation."
}
if (($sourceStatusBefore -join "`n") -ne ($sourceStatusAfter -join "`n")) {
    throw "Canonical source Git status changed during validation."
}

Write-Host ""
Write-Host "============================================================"
Write-Host "STAGE 1F.1 TRACKED DATA CLEANUP LOCAL VALIDATION COMPLETE"
Write-Host ("Tracked cleanup paths removed from branch: {0}" -f $items.Count)
Write-Host ("Migratable paths verified in AppData: {0}" -f $migratable.Count)
Write-Host ("Exact SHA-256 matches: {0}" -f $verifiedExactCount)
Write-Host ("Timestamp-only legacy drift: {0}" -f $verifiedTimestampOnlyDriftCount)
Write-Host ("Generated artifacts removed from branch: {0}" -f $generated.Count)
Write-Host "Canonical source files modified: NO"
Write-Host "Canonical source files removed: 0"
Write-Host "Git changes created: 0"
Write-Host "Cleanup applied to canonical checkout: NO"
Write-Host ("Reports: {0}" -f $ReportsRoot)
Write-Host "============================================================"
