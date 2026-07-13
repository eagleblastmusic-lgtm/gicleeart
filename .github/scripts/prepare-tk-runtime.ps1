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

function Get-RuntimeManifest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    return @(
        Get-ChildItem -LiteralPath $Root -Recurse -File |
            ForEach-Object {
                $relative = [System.IO.Path]::GetRelativePath($Root, $_.FullName).Replace("\", "/")
                "$relative|$($_.Length)"
            } |
            Sort-Object
    )
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
$sourceManifest = Get-RuntimeManifest -Root $sourceRoot
if ($sourceManifest.Count -eq 0) {
    throw "Manifest zrodlowego runtime Tcl/Tk jest pusty: $sourceRoot"
}

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

        & robocopy $sourceRoot $targetRoot /E /COPY:DAT /DCOPY:DAT /R:3 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
        $robocopyExit = $LASTEXITCODE
        if ($robocopyExit -ge 8) {
            throw "Robocopy zakonczyl sie kodem $robocopyExit."
        }

        $targetTcl = Join-Path $targetRoot $sourceTcl.Name
        $targetTk = Join-Path $targetRoot $sourceTk.Name
        $requiredFiles = @(
            (Join-Path $targetTcl "init.tcl"),
            (Join-Path $targetTk "tk.tcl"),
            (Join-Path $targetTk "spinbox.tcl"),
            (Join-Path $targetTk "ttk\defaults.tcl")
        )
        foreach ($requiredFile in $requiredFiles) {
            if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
                throw "Kopia runtime nie zawiera wymaganego pliku: $requiredFile"
            }
            Get-Content -LiteralPath $requiredFile -TotalCount 1 -ErrorAction Stop | Out-Null
        }

        $targetManifest = Get-RuntimeManifest -Root $targetRoot
        $manifestDiff = @(Compare-Object -ReferenceObject $sourceManifest -DifferenceObject $targetManifest)
        if ($manifestDiff.Count -ne 0) {
            $preview = ($manifestDiff | Select-Object -First 10 | Out-String).Trim()
            throw "Manifest kopii Tcl/Tk rozni sie od zrodla. Pierwsze roznice: $preview"
        }

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
    throw "Nie udalo sie przygotowac kompletnej kopii Tcl/Tk po 3 probach: $lastCopyError"
}

$env:TCL_LIBRARY = $targetTcl
$env:TK_LIBRARY = $targetTk
$env:GICLEEAPP_TCL_SOURCE_LIBRARY = $sourceTcl.FullName
$env:GICLEEAPP_TK_SOURCE_LIBRARY = $sourceTk.FullName
Add-Content -LiteralPath $env:GITHUB_ENV -Value "TCL_LIBRARY=$targetTcl"
Add-Content -LiteralPath $env:GITHUB_ENV -Value "TK_LIBRARY=$targetTk"
Add-Content -LiteralPath $env:GITHUB_ENV -Value "GICLEEAPP_TCL_SOURCE_LIBRARY=$($sourceTcl.FullName)"
Add-Content -LiteralPath $env:GITHUB_ENV -Value "GICLEEAPP_TK_SOURCE_LIBRARY=$($sourceTk.FullName)"

@'
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk


def normalized(value: str) -> str:
    return os.path.normcase(os.path.normpath(str(Path(value).resolve())))


expected_tcl = normalized(os.environ["TCL_LIBRARY"])
expected_tk = normalized(os.environ["TK_LIBRARY"])
source_tcl = normalized(os.environ["GICLEEAPP_TCL_SOURCE_LIBRARY"])
source_tk = normalized(os.environ["GICLEEAPP_TK_SOURCE_LIBRARY"])
for required in (
    Path(source_tcl) / "init.tcl",
    Path(source_tk) / "tk.tcl",
    Path(source_tk) / "spinbox.tcl",
    Path(source_tk) / "ttk" / "defaults.tcl",
):
    required.read_bytes()
root = tk.Tk()
root.withdraw()
actual_tcl = normalized(str(root.tk.globalgetvar("tcl_library")))
actual_tk = normalized(str(root.tk.globalgetvar("tk_library")))
if actual_tcl != expected_tcl:
    raise RuntimeError(f"Unexpected tcl_library: {actual_tcl!r} != {expected_tcl!r}")
if actual_tk != expected_tk:
    raise RuntimeError(f"Unexpected tk_library: {actual_tk!r} != {expected_tk!r}")
spinbox = tk.Spinbox(root)
spinbox.destroy()
style = ttk.Style(root)
if not style.theme_names():
    raise RuntimeError("Tk ttk runtime reported no themes")
print("tk_patchlevel=" + str(root.tk.call("info", "patchlevel")))
print("tcl_library=" + actual_tcl)
print("tk_library=" + actual_tk)
print("env_TCL_LIBRARY=" + expected_tcl)
print("env_TK_LIBRARY=" + expected_tk)
print("source_TCL_LIBRARY=" + source_tcl)
print("source_TK_LIBRARY=" + source_tk)
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
- manifest entries: $($sourceManifest.Count)
- TCL_LIBRARY: `$targetTcl`
- TK_LIBRARY: `$targetTk`
- fallback TCL_LIBRARY: `$($sourceTcl.FullName)`
- fallback TK_LIBRARY: `$($sourceTk.FullName)`
- required Tk scripts: verified
- Tk/ttk widget preflight: passed
"@ | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
}