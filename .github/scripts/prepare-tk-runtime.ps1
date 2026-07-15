param(
    [Parameter(Mandatory = $false)]
    [string]$RuntimeName = $env:GITHUB_JOB,
    [Parameter(Mandatory = $false)]
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

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

function ConvertTo-SafeRuntimePart {
    param(
        [Parameter(Mandatory = $false)]
        [AllowEmptyString()]
        [string]$Value,
        [Parameter(Mandatory = $true)]
        [string]$Fallback
    )

    $clean = (($Value | Out-String).Trim() -replace '[^A-Za-z0-9_.-]', '-')
    if (-not $clean) {
        return $Fallback
    }
    return $clean
}

function Get-RuntimeManifest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $resolvedRoot = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\', '/')
    $entries = Get-ChildItem -LiteralPath $resolvedRoot -Recurse -File |
        Sort-Object FullName |
        ForEach-Object {
            $relative = [System.IO.Path]::GetRelativePath($resolvedRoot, $_.FullName)
            $relative = $relative.Replace('\', '/')
            [pscustomobject]@{
                path = $relative
                length = [int64]$_.Length
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }
    return @($entries)
}

function Assert-RuntimeManifestsEqual {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Expected,
        [Parameter(Mandatory = $true)]
        [object[]]$Actual,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    if ($Expected.Count -ne $Actual.Count) {
        throw "$Label manifest count mismatch: expected $($Expected.Count), actual $($Actual.Count)."
    }

    $actualByPath = @{}
    foreach ($entry in $Actual) {
        $actualByPath[[string]$entry.path] = $entry
    }

    foreach ($expectedEntry in $Expected) {
        $path = [string]$expectedEntry.path
        if (-not $actualByPath.ContainsKey($path)) {
            throw "$Label manifest is missing: $path"
        }
        $actualEntry = $actualByPath[$path]
        if ([int64]$expectedEntry.length -ne [int64]$actualEntry.length) {
            throw "$Label length mismatch for $path."
        }
        if ([string]$expectedEntry.sha256 -ne [string]$actualEntry.sha256) {
            throw "$Label SHA-256 mismatch for $path."
        }
    }
}

function Assert-RequiredRuntimeFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [Parameter(Mandatory = $true)]
        [string]$TclDirectoryName,
        [Parameter(Mandatory = $true)]
        [string]$TkDirectoryName
    )

    $requiredRelativePaths = @(
        (Join-Path $TclDirectoryName "init.tcl"),
        (Join-Path $TkDirectoryName "tk.tcl"),
        (Join-Path $TkDirectoryName "icons.tcl"),
        (Join-Path $TkDirectoryName "spinbox.tcl"),
        (Join-Path $TkDirectoryName "ttk\ttk.tcl"),
        (Join-Path $TkDirectoryName "ttk\defaults.tcl"),
        (Join-Path $TkDirectoryName "ttk\classicTheme.tcl"),
        (Join-Path $TkDirectoryName "ttk\winTheme.tcl")
    )

    foreach ($relativePath in $requiredRelativePaths) {
        $path = Join-Path $Root $relativePath
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Runtime Tcl/Tk nie zawiera wymaganego pliku: $path"
        }
        [System.IO.File]::OpenRead($path).Dispose()
    }
}

function Publish-RuntimeEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RuntimeRoot,
        [Parameter(Mandatory = $true)]
        [string]$TclLibrary,
        [Parameter(Mandatory = $true)]
        [string]$TkLibrary,
        [Parameter(Mandatory = $true)]
        [string]$ManifestPath
    )

    $values = [ordered]@{
        GICLEEAPP_TK_RUNTIME_ROOT = $RuntimeRoot
        GICLEEAPP_TK_RUNTIME_MANIFEST = $ManifestPath
        TCL_LIBRARY = $TclLibrary
        TK_LIBRARY = $TkLibrary
    }

    foreach ($entry in $values.GetEnumerator()) {
        Set-Item -Path "Env:$($entry.Key)" -Value $entry.Value
        if ($env:GITHUB_ENV) {
            Add-Content -LiteralPath $env:GITHUB_ENV -Value "$($entry.Key)=$($entry.Value)"
        }
    }
}

function Invoke-TkRuntimePreflight {
    @'
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk


def normalized(value: str) -> str:
    return os.path.normcase(os.path.normpath(str(Path(value).resolve())))


runtime_root = normalized(os.environ["GICLEEAPP_TK_RUNTIME_ROOT"])
expected_tcl = normalized(os.environ["TCL_LIBRARY"])
expected_tk = normalized(os.environ["TK_LIBRARY"])
if not expected_tcl.startswith(runtime_root + os.sep):
    raise RuntimeError(f"TCL_LIBRARY is outside runtime mirror: {expected_tcl!r}")
if not expected_tk.startswith(runtime_root + os.sep):
    raise RuntimeError(f"TK_LIBRARY is outside runtime mirror: {expected_tk!r}")

for required in (
    Path(expected_tcl) / "init.tcl",
    Path(expected_tk) / "tk.tcl",
    Path(expected_tk) / "icons.tcl",
    Path(expected_tk) / "spinbox.tcl",
    Path(expected_tk) / "ttk" / "ttk.tcl",
    Path(expected_tk) / "ttk" / "defaults.tcl",
    Path(expected_tk) / "ttk" / "classicTheme.tcl",
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
    themes = tuple(style.theme_names())
    if not themes:
        raise RuntimeError("Tk ttk runtime reported no themes")

    print("tk_patchlevel=" + str(root.tk.call("info", "patchlevel")))
    print("tcl_library=" + actual_tcl)
    print("tk_library=" + actual_tk)
    print("themes=" + ",".join(themes))
finally:
    if root is not None:
        root.destroy()
'@ | python -

    if ($LASTEXITCODE -ne 0) {
        throw "Preflight Tcl/Tk nie powiodl sie dla izolowanego mirroru runtime."
    }
}

function Write-RuntimeSummary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Mode,
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        [Parameter(Mandatory = $true)]
        [string]$RuntimeRoot,
        [Parameter(Mandatory = $true)]
        [string]$ManifestPath,
        [Parameter(Mandatory = $true)]
        [int]$FileCount
    )

    if (-not $env:GITHUB_STEP_SUMMARY) {
        return
    }

    @"
## Mirrored Tcl/Tk runtime

- Python: $PythonExe
- job label: $RuntimeName
- mode: $Mode
- mirror root: $RuntimeRoot
- manifest: $ManifestPath
- mirrored files: $FileCount
- integrity: relative path + length + SHA-256
- Tk/ttk widget preflight: passed
- Tk initialization retry: disabled
"@ | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
}

$pythonExe = (& python -c "import sys; print(sys.executable)").Trim()
if (-not $pythonExe) {
    throw "Nie udalo sie ustalic sciezki interpretera Python."
}

if ($VerifyOnly) {
    $runtimeRoot = ($env:GICLEEAPP_TK_RUNTIME_ROOT | Out-String).Trim()
    $manifestPath = ($env:GICLEEAPP_TK_RUNTIME_MANIFEST | Out-String).Trim()
    $targetTcl = ($env:TCL_LIBRARY | Out-String).Trim()
    $targetTk = ($env:TK_LIBRARY | Out-String).Trim()

    foreach ($requiredValue in @($runtimeRoot, $manifestPath, $targetTcl, $targetTk)) {
        if (-not $requiredValue) {
            throw "VerifyOnly wymaga opublikowanego mirroru Tcl/Tk i manifestu."
        }
    }
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Brak manifestu mirroru Tcl/Tk: $manifestPath"
    }

    $document = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $expectedRoot = (Resolve-Path -LiteralPath ([string]$document.runtime_root)).Path
    $actualRoot = (Resolve-Path -LiteralPath $runtimeRoot).Path
    if ($expectedRoot -ne $actualRoot) {
        throw "Manifest wskazuje inny runtime root: $expectedRoot != $actualRoot"
    }

    Assert-RequiredRuntimeFiles `
        -Root $actualRoot `
        -TclDirectoryName ([string]$document.tcl_directory_name) `
        -TkDirectoryName ([string]$document.tk_directory_name)
    $actualManifest = @(Get-RuntimeManifest -Root $actualRoot)
    Assert-RuntimeManifestsEqual `
        -Expected @($document.files) `
        -Actual $actualManifest `
        -Label "VerifyOnly"

    Publish-RuntimeEnvironment `
        -RuntimeRoot $actualRoot `
        -TclLibrary $targetTcl `
        -TkLibrary $targetTk `
        -ManifestPath $manifestPath
    Invoke-TkRuntimePreflight
    Write-RuntimeSummary `
        -Mode "verify-only" `
        -PythonExe $pythonExe `
        -RuntimeRoot $actualRoot `
        -ManifestPath $manifestPath `
        -FileCount $actualManifest.Count
    return
}

$pythonRoot = Split-Path -Parent $pythonExe
$sourceRoot = Join-Path $pythonRoot "tcl"
if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
    throw "Brak katalogu Tcl/Tk przy interpreterze: $sourceRoot"
}

$sourceTcl = Get-RequiredRuntimeDirectory -Root $sourceRoot -RequiredFile "init.tcl"
$sourceTk = Get-RequiredRuntimeDirectory -Root $sourceRoot -RequiredFile "tk.tcl"
Assert-RequiredRuntimeFiles `
    -Root $sourceRoot `
    -TclDirectoryName $sourceTcl.Name `
    -TkDirectoryName $sourceTk.Name

$identityParts = @(
    (ConvertTo-SafeRuntimePart -Value $RuntimeName -Fallback "job"),
    (ConvertTo-SafeRuntimePart -Value $env:GITHUB_RUN_ID -Fallback "local-run"),
    (ConvertTo-SafeRuntimePart -Value $env:GITHUB_RUN_ATTEMPT -Fallback "attempt-1"),
    (ConvertTo-SafeRuntimePart -Value $env:GITHUB_JOB -Fallback "local-job")
)
$safeIdentity = $identityParts -join "-"
$targetRoot = Join-Path $env:RUNNER_TEMP "python-tcl-runtime-$safeIdentity"
$manifestPath = Join-Path $env:RUNNER_TEMP "python-tcl-runtime-$safeIdentity.manifest.json"

Remove-Item -LiteralPath $targetRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $manifestPath -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null

$sourceManifest = @(Get-RuntimeManifest -Root $sourceRoot)
& robocopy $sourceRoot $targetRoot /E /COPY:DAT /DCOPY:DAT /R:3 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
$copyExitCode = $LASTEXITCODE
$global:LASTEXITCODE = 0
if ($copyExitCode -gt 7) {
    throw "Robocopy Tcl/Tk zakonczyl sie kodem $copyExitCode."
}

$targetManifest = @(Get-RuntimeManifest -Root $targetRoot)
Assert-RuntimeManifestsEqual `
    -Expected $sourceManifest `
    -Actual $targetManifest `
    -Label "Mirror copy"
Assert-RequiredRuntimeFiles `
    -Root $targetRoot `
    -TclDirectoryName $sourceTcl.Name `
    -TkDirectoryName $sourceTk.Name

$manifestDocument = [ordered]@{
    version = 1
    runtime_root = (Resolve-Path -LiteralPath $targetRoot).Path
    source_root = (Resolve-Path -LiteralPath $sourceRoot).Path
    tcl_directory_name = $sourceTcl.Name
    tk_directory_name = $sourceTk.Name
    files = $targetManifest
}
$manifestDocument | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding utf8

$targetTcl = Join-Path $targetRoot $sourceTcl.Name
$targetTk = Join-Path $targetRoot $sourceTk.Name
Publish-RuntimeEnvironment `
    -RuntimeRoot $targetRoot `
    -TclLibrary $targetTcl `
    -TkLibrary $targetTk `
    -ManifestPath $manifestPath
Invoke-TkRuntimePreflight
Write-RuntimeSummary `
    -Mode "prepare-mirror" `
    -PythonExe $pythonExe `
    -RuntimeRoot $targetRoot `
    -ManifestPath $manifestPath `
    -FileCount $targetManifest.Count
