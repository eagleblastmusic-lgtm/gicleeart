param([string]$ToolRoot = "")
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ([string]::IsNullOrWhiteSpace($ToolRoot)) { $ToolRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { $ToolRoot = (Resolve-Path $ToolRoot).Path }
$validationRoot = Join-Path $env:TEMP ("gicleeapp-stage1e-3-validation-" + [Guid]::NewGuid().ToString("N"))
$localRoot = Join-Path $validationRoot "local"
$roamingRoot = Join-Path $validationRoot "roaming"
New-Item -ItemType Directory -Force -Path $localRoot, $roamingRoot | Out-Null
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
        Write-Host "=== Stage 1E.1-1E.3 external runtime path tests ==="
        python -m pytest `
            tests/test_app_paths.py `
            tests/test_stage1e_external_stores.py `
            tests/test_stage1e_runtime_runbook.py `
            tests/test_stage1e_external_stores_2.py `
            tests/test_stage1e_runtime_runbook_2.py `
            tests/test_stage1e_external_stores_3.py `
            tests/test_stage1e_runtime_runbook_3.py `
            tests/test_bazapromptow.py `
            tests/test_integracjagpt.py::test_gpt_config_roundtrip `
            tests/test_launcher_shortcuts.py `
            tests/test_launcher_shortcuts_config.py `
            tests/test_stronyzobrazami.py `
            -q
        if ($LASTEXITCODE -ne 0) { throw "Stage 1E.3 tests failed with exit code $LASTEXITCODE." }
        Write-Host ""
        Write-Host "=== Compile Stage 1E.3 modules ==="
        python -m compileall -q `
            Komponenty/planer/view.py `
            Komponenty/zadania/storage.py `
            Komponenty/tytulyai/storage.py `
            Komponenty/poczta/client_order_processor.py `
            Komponenty/karuzela/service.py `
            Komponenty/produkcja/package_templates.py `
            Komponenty/stronydozycia/storage.py `
            Komponenty/stronyzobrazami/storage.py `
            Komponenty/stronyzobrazami/settings.py `
            giclee_app/launcher_layout.py `
            giclee_app/launcher_shortcuts.py `
            giclee_app/studio/categories.py
        if ($LASTEXITCODE -ne 0) { throw "Compile validation failed with exit code $LASTEXITCODE." }
        Write-Host ""
        Write-Host "=== Worktree cleanliness ==="
        $changes = @(git status --porcelain)
        if ($LASTEXITCODE -ne 0) { throw "git status failed." }
        if ($changes.Count -gt 0) { $changes | ForEach-Object { Write-Host $_ }; throw "Validation modified the tool checkout." }
    } finally { Pop-Location }
    Write-Host ""
    Write-Host "============================================================"
    Write-Host "STAGE 1E.3 LOCAL VALIDATION COMPLETE"
    Write-Host "Real AppData modified: NO"
    Write-Host "Canonical source files modified: NO"
    Write-Host "Source files removed: 0"
    Write-Host "Git changes created: 0"
    Write-Host "Isolated test output: $validationRoot"
    Write-Host "============================================================"
} finally {
    $env:GICLEEAPP_LOCAL_ROOT = $originalLocalRoot
    $env:GICLEEAPP_ROAMING_ROOT = $originalRoamingRoot
}
