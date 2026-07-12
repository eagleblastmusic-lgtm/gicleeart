param(
    [string]$ToolRoot = "",
    [string]$ScanRoot = "C:\Strona\pusty\cursor-api",
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
    $ReportsRoot = Join-Path $env:TEMP ("gicleeapp-repository-safety-archive-cache-" + [guid]::NewGuid().ToString("N"))
}
New-Item -ItemType Directory -Path $ReportsRoot -Force | Out-Null
$ReportsRoot = (Resolve-Path $ReportsRoot).Path

function Invoke-CheckedPython {
    param([string[]]$Arguments)

    & python @Arguments | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: python $($Arguments -join ' ')"
    }
}

function Get-RepositoryStatus {
    $lines = @(& git -C $ScanRoot status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read Git status for: $ScanRoot"
    }
    return @($lines)
}

function Assert-ReportsEquivalentSources {
    param(
        [object]$Before,
        [object]$After,
        [string]$Profile
    )

    $beforeBySource = @{}
    foreach ($item in @($Before.items)) {
        $beforeBySource[[string]$item.source] = $item
    }

    foreach ($item in @($After.items)) {
        $source = [string]$item.source
        if (-not $beforeBySource.ContainsKey($source)) {
            throw "[$Profile] Post-copy report contains an unexpected source: $source"
        }
        $beforeItem = $beforeBySource[$source]
        if ([string]$beforeItem.source_sha256 -ne [string]$item.source_sha256) {
            throw "[$Profile] Source hash changed during the operation: $source"
        }
    }

    if (@($Before.items).Count -ne @($After.items).Count) {
        throw "[$Profile] Item count changed between preflight and post-copy reports."
    }
}

function Invoke-ProfileCopyGate {
    param([ValidateSet("archive", "cache")][string]$Profile)

    $preflightJson = Join-Path $ReportsRoot ("{0}-preflight.json" -f $Profile)
    $copyJson = Join-Path $ReportsRoot ("{0}-copy.json" -f $Profile)
    $postJson = Join-Path $ReportsRoot ("{0}-post-copy.json" -f $Profile)

    Write-Host ""
    Write-Host ("=== {0} profile preflight ===" -f $Profile.ToUpperInvariant())
    Invoke-CheckedPython @(
        "-m", "tools.repository_safety", "migrate",
        "--repo", $ScanRoot,
        "--profile", $Profile,
        "--include-untracked",
        "--json-out", $preflightJson
    )

    $preflight = Get-Content -LiteralPath $preflightJson -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([bool]$preflight.blocked) {
        throw "[$Profile] Preflight is blocked. Review: $preflightJson"
    }
    if ([int]$preflight.item_count -le 0) {
        throw "[$Profile] No items were found. Verify ScanRoot and classification policy."
    }

    Write-Host ("=== {0} profile copy-only ===" -f $Profile.ToUpperInvariant())
    Invoke-CheckedPython @(
        "-m", "tools.repository_safety", "migrate",
        "--repo", $ScanRoot,
        "--profile", $Profile,
        "--include-untracked",
        "--copy",
        "--json-out", $copyJson
    )

    $copy = Get-Content -LiteralPath $copyJson -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([bool]$copy.blocked) {
        throw "[$Profile] Copy-only operation is blocked. Review: $copyJson"
    }

    foreach ($item in @($copy.items)) {
        $status = [string]$item.status
        if ($status -notin @("copied", "verified_existing")) {
            throw "[$Profile] Invalid status '$status' for: $($item.source)"
        }
        if ([string]::IsNullOrWhiteSpace([string]$item.destination_sha256)) {
            throw "[$Profile] Destination hash is missing for: $($item.source)"
        }
        if ([string]$item.source_sha256 -ne [string]$item.destination_sha256) {
            throw "[$Profile] Source and destination SHA-256 values differ: $($item.source)"
        }

        $sourcePath = Join-Path $ScanRoot ([string]$item.source)
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
            throw "[$Profile] Source disappeared after copy-only: $sourcePath"
        }
        $sourceHashNow = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($sourceHashNow -ne ([string]$item.source_sha256).ToLowerInvariant()) {
            throw "[$Profile] Source changed after copy-only: $sourcePath"
        }
    }

    Write-Host ("=== {0} profile post-copy verification ===" -f $Profile.ToUpperInvariant())
    Invoke-CheckedPython @(
        "-m", "tools.repository_safety", "migrate",
        "--repo", $ScanRoot,
        "--profile", $Profile,
        "--include-untracked",
        "--json-out", $postJson
    )

    $post = Get-Content -LiteralPath $postJson -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([bool]$post.blocked) {
        throw "[$Profile] Post-copy verification is blocked. Review: $postJson"
    }
    Assert-ReportsEquivalentSources -Before $preflight -After $post -Profile $Profile

    foreach ($item in @($post.items)) {
        if ([string]$item.status -ne "verified_existing") {
            throw "[$Profile] Post-copy did not confirm an identical copy for: $($item.source)"
        }
        if ([string]$item.source_sha256 -ne [string]$item.destination_sha256) {
            throw "[$Profile] Post-copy SHA-256 mismatch for: $($item.source)"
        }
    }

    return [pscustomobject]@{
        Profile = $Profile
        Items = [int]$copy.item_count
        Copied = [int]$copy.copied_count
        VerifiedExisting = [int]$copy.verified_existing_count
        PreflightReport = $preflightJson
        CopyReport = $copyJson
        PostCopyReport = $postJson
    }
}

Push-Location $ToolRoot
try {
    $statusBefore = @(Get-RepositoryStatus)

    $archive = Invoke-ProfileCopyGate -Profile "archive"
    $cache = Invoke-ProfileCopyGate -Profile "cache"

    $statusAfter = @(Get-RepositoryStatus)
    if (($statusBefore -join "`n") -ne ($statusAfter -join "`n")) {
        Write-Host "Git status before the operation:"
        $statusBefore | ForEach-Object { Write-Host $_ }
        Write-Host "Git status after the operation:"
        $statusAfter | ForEach-Object { Write-Host $_ }
        throw "Canonical repository Git status changed during copy-only."
    }

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "STAGE 1E.10 ARCHIVE/CACHE COPY GATE COMPLETE"
    Write-Host ("Archive items: {0}" -f $archive.Items)
    Write-Host ("Archive copied: {0}" -f $archive.Copied)
    Write-Host ("Archive verified existing: {0}" -f $archive.VerifiedExisting)
    Write-Host ("Cache items: {0}" -f $cache.Items)
    Write-Host ("Cache copied: {0}" -f $cache.Copied)
    Write-Host ("Cache verified existing: {0}" -f $cache.VerifiedExisting)
    Write-Host "Real AppData modified: YES (copy-only, SHA-256 verified)"
    Write-Host "Canonical source files modified: NO"
    Write-Host "Source files removed: 0"
    Write-Host "Git changes created: 0"
    Write-Host "Cleanup/untracking performed: NO"
    Write-Host ("Reports: {0}" -f $ReportsRoot)
    Write-Host "============================================================"
}
finally {
    Pop-Location
}