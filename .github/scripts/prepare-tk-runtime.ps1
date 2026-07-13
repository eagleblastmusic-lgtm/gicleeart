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
$requiredFiles = @(
    (Join-Path $sourceTcl.FullName "init.tcl"),
    (Join-Path $sourceTk.FullName "tk.tcl"),
    (Join-Path $sourceTk.FullName "spinbox.tcl"),
    (Join-Path $sourceTk.FullName "ttk\defaults.tcl"),
    (Join-Path $sourceTk.FullName "ttk\winTheme.tcl")
)

foreach ($requiredFile in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Runtime setup-python nie zawiera wymaganego pliku: $requiredFile"
    }
    Get-Content -LiteralPath $requiredFile -TotalCount 1 -ErrorAction Stop | Out-Null
}

$env:TCL_LIBRARY = $sourceTcl.FullName
$env:TK_LIBRARY = $sourceTk.FullName
Add-Content -LiteralPath $env:GITHUB_ENV -Value "TCL_LIBRARY=$($sourceTcl.FullName)"
Add-Content -LiteralPath $env:GITHUB_ENV -Value "TK_LIBRARY=$($sourceTk.FullName)"

@'
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk


def normalized(value: str) -> str:
    return os.path.normcase(os.path.normpath(str(Path(value).resolve())))


expected_tcl = normalized(os.environ["TCL_LIBRARY"])
expected_tk = normalized(os.environ["TK_LIBRARY"])
for required in (
    Path(expected_tcl) / "init.tcl",
    Path(expected_tk) / "tk.tcl",
    Path(expected_tk) / "spinbox.tcl",
    Path(expected_tk) / "ttk" / "defaults.tcl",
    Path(expected_tk) / "ttk" / "winTheme.tcl",
):
    required.read_bytes()

root = None
try:
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
finally:
    if root is not None:
        root.destroy()
'@ | python -

if ($LASTEXITCODE -ne 0) {
    throw "Preflight Tcl/Tk nie powiodl sie dla runtime actions/setup-python."
}

if ($env:GITHUB_STEP_SUMMARY) {
    @"
## Setup-python Tcl/Tk runtime

- Python: `$pythonExe`
- job label: `$RuntimeName`
- runtime root: `$sourceRoot`
- mode: direct setup-python runtime; no copied interpreter tree
- TCL_LIBRARY: `$($sourceTcl.FullName)`
- TK_LIBRARY: `$($sourceTk.FullName)`
- required Tk scripts: verified
- Tk/ttk widget preflight: passed
- Tk initialization retry: disabled
"@ | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
}
