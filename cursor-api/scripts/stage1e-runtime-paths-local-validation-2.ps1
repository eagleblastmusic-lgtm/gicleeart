param(
    [string]$ToolRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($ToolRoot)) {
    if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        throw "Nie można ustalić katalogu skryptu. Podaj -ToolRoot."
    }
    $ToolRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    $ToolRoot = (Resolve-Path $ToolRoot).Path
}

$validationRoot = Join-Path $env:TEMP (
    "gicleeapp-stage1e-2-validation-" + [Guid]::NewGuid().ToString("N")
)
$localRoot = Join-Path $validationRoot "local"
$roamingRoot = Join-Path $validationRoot "roaming"

New-Item -ItemType Directory -Force -Path $localRoot | Out-Null
New-Item -ItemType Directory -Force -Path $roamingRoot | Out-Null

$originalLocalRoot = $env:GICLEEAPP_LOCAL_ROOT
$originalRoamingRoot = $env:GICLEEAPP_ROAMING_ROOT

try {
    $env:GICLEEAPP_LOCAL_ROOT = $localRoot
    $env:GICLEEAPP_ROAMING_ROOT = $roamingRoot

    Write-Host "Tool checkout: $ToolRoot"
    Write-Host "Isolated Local root: $localRoot"
    Write-Host "Isolated Roaming root: $roamingRoot"
    Write-Host "No real AppData or canonical source data will be modified."

    Push-Location $ToolRoot
    try {
        Write-Host ""
        Write-Host "=== Stage 1E.1 and 1E.2 external runtime path tests ==="
        python -m pytest `
            tests/test_app_paths.py `
            tests/test_stage1e_external_stores.py `
            tests/test_stage1e_runtime_runbook.py `
            tests/test_stage1e_external_stores_2.py `
            tests/test_stage1e_runtime_runbook_2.py `
            tests/test_bazapromptow.py `
            tests/test_integracjagpt.py::test_gpt_config_roundtrip `
            -q
        if ($LASTEXITCODE -ne 0) {
            throw "Stage 1E.2 runtime path tests failed with exit code $LASTEXITCODE."
        }

        Write-Host ""
        Write-Host "=== Compile Stage 1E runtime modules ==="
        python -m compileall -q `
            giclee_app/app_paths.py `
            Komponenty/_shared/recent_images.py `
            Komponenty/blog/storage.py `
            Komponenty/dnr/storage.py `
            Komponenty/dokumentysprzedazy/storage.py `
            Komponenty/kpir/storage.py `
            Komponenty/kalkulacja/store.py `
            Komponenty/kalkulacja/import_excel.py `
            Komponenty/bazapromptow/storage.py `
            Komponenty/integracjagpt/config.py
        if ($LASTEXITCODE -ne 0) {
            throw "Compile validation failed with exit code $LASTEXITCODE."
        }

        Write-Host ""
        Write-Host "=== Worktree cleanliness ==="
        $changes = @(git status --porcelain)
        if ($LASTEXITCODE -ne 0) {
            throw "git status failed."
        }
        if ($changes.Count -gt 0) {
            $changes | ForEach-Object { Write-Host $_ }
            throw "Validation modified the tool checkout."
        }
    }
    finally {
        Pop-Location
    }

    Write-Host ""
    Write-Host "============================================================"
    Write-Host "STAGE 1E.2 LOCAL VALIDATION COMPLETE"
    Write-Host "Real AppData modified: NO"
    Write-Host "Canonical source files modified: NO"
    Write-Host "Source files removed: 0"
    Write-Host "Git changes created: 0"
    Write-Host "Isolated test output: $validationRoot"
    Write-Host "============================================================"
}
finally {
    $env:GICLEEAPP_LOCAL_ROOT = $originalLocalRoot
    $env:GICLEEAPP_ROAMING_ROOT = $originalRoamingRoot
}
