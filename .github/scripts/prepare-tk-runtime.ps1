param(
    [Parameter(Mandatory = $false)]
    [string]$RuntimeName = $env:GITHUB_JOB
)

$ErrorActionPreference = "Stop"

function Get-RequiredRuntimeDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [Parameter(Mandatory = $true)]
        [string]$RequiredFile
    )

    $match = Get-ChildItem -LiteralPath $Root -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName $RequiredFile) } |
        Select-Object -First 1

    if ($null -eq $match) {
        throw "Nie znaleziono katalogu runtime zawierajacego $RequiredFile pod $Root."
    }

    return $match
}

$pythonExe = (& python -c "import sys; print(sys.executable)").Trim()
if (-not $pythonExe) {
    throw "Nie udalo sie ustalic sciezki interpretera Python."
}

$pythonRoot = Split-Path -Parent $pythonExe
$sourceRoot = Join-Path $pythonRoot "tcl"
if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
    throw "Brak katalogu Tcl/Tk przy interpreterze: $sourceRoot"
}

$sourceTcl = Get-RequiredRuntimeDirectory -Root $sourceRoot -RequiredFile "init.tcl"
$sourceTk = Get-RequiredRuntimeDirectory -Root $sourceRoot -RequiredFile "tk.tcl"

$safeRuntimeName = ($RuntimeName -replace '[^A-Za-z0-9_.-]', '-')
if (-not $safeRuntimeName) {
    $safeRuntimeName = "job"
}

$identityParts = @($safeRuntimeName)
foreach ($value in @($env:GITHUB_RUN_ID, $env:GITHUB_RUN_ATTEMPT, $env:GITHUB_JOB)) {
    $clean = (($value | Out-String).Trim() -replace '[^A-Za-z0-9_.-]', '-')
    if ($clean) {
        $identityParts += $clean
    }
}
$safeIdentity = $identityParts -join "-"
$targetRoot = Join-Path $env:RUNNER_TEMP "python-tcl-runtime-$safeIdentity"
$copySucceeded = $false
$lastCopyError = $null

for ($attempt = 1; $attempt -le 3; $attempt++) {
    try {
        Remove-Item -LiteralPath $targetRoot -Recurse -Force -ErrorAction SilentlyContinue
        New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
        Copy-Item -Path (Join-Path $sourceRoot "*") -Destination $targetRoot -Recurse -Force

        $targetTcl = Join-Path $targetRoot $sourceTcl.Name
        $targetTk = Join-Path $targetRoot $sourceTk.Name
        $targetInit = Join-Path $targetTcl "init.tcl"
        $targetTkInit = Join-Path $targetTk "tk.tcl"

        if (-not (Test-Path -LiteralPath $targetInit -PathType Leaf)) {
            throw "Kopia runtime nie zawiera init.tcl: $targetInit"
        }
        if (-not (Test-Path -LiteralPath $targetTkInit -PathType Leaf)) {
            throw "Kopia runtime nie zawiera tk.tcl: $targetTkInit"
        }

        Get-Content -LiteralPath $targetInit -TotalCount 1 -ErrorAction Stop | Out-Null
        Get-Content -LiteralPath $targetTkInit -TotalCount 1 -ErrorAction Stop | Out-Null
        $copySucceeded = $true
        break
    }
    catch {
        $lastCopyError = $_
        if ($attempt -lt 3) {
            Start-Sleep -Seconds $attempt
        }
    }
}

if (-not $copySucceeded) {
    throw "Nie udalo sie przygotowac izolowanej kopii Tcl/Tk po 3 probach: $lastCopyError"
}

$env:TCL_LIBRARY = $targetTcl
$env:TK_LIBRARY = $targetTk
Add-Content -LiteralPath $env:GITHUB_ENV -Value "TCL_LIBRARY=$targetTcl"
Add-Content -LiteralPath $env:GITHUB_ENV -Value "TK_LIBRARY=$targetTk"

@'
import os
import tkinter as tk

root = tk.Tk()
root.withdraw()
print("tk_patchlevel=" + str(root.tk.call("info", "patchlevel")))
print("tcl_library=" + str(root.tk.globalgetvar("tcl_library")))
print("env_TCL_LIBRARY=" + str(os.environ.get("TCL_LIBRARY", "")))
print("env_TK_LIBRARY=" + str(os.environ.get("TK_LIBRARY", "")))
root.destroy()
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Preflight Tcl/Tk nie powiodl sie dla izolowanego runtime."
}

if ($env:GITHUB_STEP_SUMMARY) {
    @"
## Isolated Tcl/Tk runtime

- Python: `$pythonExe`
- source: `$sourceRoot`
- isolated copy: `$targetRoot`
- run identity: `$safeIdentity`
- TCL_LIBRARY: `$targetTcl`
- TK_LIBRARY: `$targetTk`
"@ | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
}
