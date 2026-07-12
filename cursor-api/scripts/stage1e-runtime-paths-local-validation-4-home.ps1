param([string]$ToolRoot = "")
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($ToolRoot)) {
    if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) { throw "Nie można ustalić katalogu skryptu. Podaj -ToolRoot." }
    $ToolRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else { $ToolRoot = (Resolve-Path $ToolRoot).Path }

$validationRoot = Join-Path $env:TEMP ("gicleeapp-stage1e-4-home-validation-" + [Guid]::NewGuid().ToString("N"))
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
        Write-Host "=== Stage 1E.1-1E.4 Home runtime path tests ==="
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
            tests/test_bazapromptow.py `
            tests/test_integracjagpt.py::test_gpt_config_roundtrip `
            tests/test_launcher_shortcuts.py `
            tests/test_launcher_shortcuts_config.py `
            tests/test_stronyzobrazami.py `
            tests/test_stronaglowna_final_difference.py `
            tests/test_stronaglowna_scroll.py `
            tests/test_stronaglowna_section_bg_effects.py `
            tests/test_stronaglowna_studio_reveal.py `
            Komponenty/stronaglowna/test_home_flow.py `
            Komponenty/stronaglowna/test_home_flow_phase_settings.py `
            Komponenty/stronaglowna/test_home_flow_structure_writer.py `
            --deselect tests/test_stronaglowna_scroll.py::test_write_home_assets_embeds_motion_dynamics `
            --deselect tests/test_stronaglowna_scroll.py::test_write_home_assets_embeds_scroll_config `
            -q
        if ($LASTEXITCODE -ne 0) { throw "Stage 1E.4 Home tests failed with exit code $LASTEXITCODE." }
        Write-Host ""
        Write-Host "=== Compile Stage 1E.4 Home modules ==="
        python -m compileall -q `
            Komponenty/stronaglowna/homepage_variants.py `
            Komponenty/stronaglowna/home_flow.py `
            Komponenty/stronaglowna/home_flow_phase_settings.py `
            Komponenty/stronaglowna/home_flow_structure_writer.py `
            Komponenty/stronaglowna/home_features.py `
            Komponenty/stronaglowna/final_difference_settings.py `
            Komponenty/stronaglowna/scroll_settings.py `
            Komponenty/stronaglowna/section_bg_effects_settings.py `
            Komponenty/stronaglowna/section_effects_storage.py `
            Komponenty/stronaglowna/studio_reveal_settings.py
        if ($LASTEXITCODE -ne 0) { throw "Compile validation failed with exit code $LASTEXITCODE." }
        Write-Host ""
        Write-Host "=== Worktree cleanliness ==="
        $changes = @(git status --porcelain)
        if ($LASTEXITCODE -ne 0) { throw "git status failed." }
        if ($changes.Count -gt 0) { $changes | ForEach-Object { Write-Host $_ }; throw "Validation modified the tool checkout." }
    } finally { Pop-Location }
    Write-Host ""
    Write-Host "============================================================"
    Write-Host "STAGE 1E.4 HOME LOCAL VALIDATION COMPLETE"
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
