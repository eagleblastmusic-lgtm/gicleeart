param([string]$ToolRoot = "")
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($ToolRoot)) {
    if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) { throw "Nie można ustalić katalogu skryptu. Podaj -ToolRoot." }
    $ToolRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else { $ToolRoot = (Resolve-Path $ToolRoot).Path }

$validationRoot = Join-Path $env:TEMP ("gicleeapp-stage1e-6-socialmedia-validation-" + [Guid]::NewGuid().ToString("N"))
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
        Write-Host "=== Stage 1E.1-1E.6 Social Media runtime path tests ==="
        python -m pytest `
            tests/test_app_paths.py `
            tests/test_stage1e_external_stores.py `
            tests/test_stage1e_runtime_runbook.py `
            tests/test_stage1e_external_stores_2.py `
            tests/test_stage1e_runtime_runbook_2.py `
            tests/test_stage1e_external_stores_3.py `
            tests/test_stage1e_runtime_runbook_3.py `
            tests/test_stage1e_external_stores_4_home.py `
            tests/test_stage1e_runtime_runbook_4_home.py `
            tests/test_stage1e_external_stores_5_dodajobraz.py `
            tests/test_stage1e_runtime_runbook_5_dodajobraz.py `
            tests/test_stage1e_external_stores_6_socialmedia.py `
            tests/test_stage1e_runtime_runbook_6_socialmedia.py `
            tests/test_meta_token_status.py `
            tests/test_description_update_marks.py `
            tests/test_product_template_assignments.py `
            tests/test_variant_templates_default.py `
            tests/test_r2_usage.py `
            tests/test_markets.py `
            -q
        if ($LASTEXITCODE -ne 0) { throw "Stage 1E.6 Social Media tests failed with exit code $LASTEXITCODE." }
        Write-Host ""
        Write-Host "=== Compile Stage 1E.6 Social Media modules ==="
        python -m compileall -q `
            Komponenty/socialmedia/storage.py `
            Komponenty/socialmedia/presets.py `
            Komponenty/socialmedia/cykl/storage.py `
            Komponenty/socialmedia/cykl/images.py `
            Komponenty/socialmedia/cykl/meta_token_status.py
        if ($LASTEXITCODE -ne 0) { throw "Compile validation failed with exit code $LASTEXITCODE." }
        Write-Host ""
        Write-Host "=== Worktree cleanliness ==="
        $changes = @(git status --porcelain)
        if ($LASTEXITCODE -ne 0) { throw "git status failed." }
        if ($changes.Count -gt 0) { $changes | ForEach-Object { Write-Host $_ }; throw "Validation modified the tool checkout." }
    } finally { Pop-Location }
    Write-Host ""
    Write-Host "============================================================"
    Write-Host "STAGE 1E.6 SOCIAL MEDIA LOCAL VALIDATION COMPLETE"
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
