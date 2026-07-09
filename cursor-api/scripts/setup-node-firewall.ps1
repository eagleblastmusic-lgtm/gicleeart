#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Allow Node.js in Windows Firewall (Shopify theme dev + GicleeApp).

.DESCRIPTION
  Adds rules for node.exe:
  - Outbound (HTTPS to Shopify)
  - Inbound (local theme dev preview on port 9292)

  Run as administrator:
    cd C:\Strona\pusty\cursor-api\scripts
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
    .\setup-node-firewall.ps1
#>

$ErrorActionPreference = "Stop"

$nodeCandidates = @(
    "C:\Program Files\nodejs\node.exe",
    "$env:LOCALAPPDATA\Programs\nodejs\node.exe"
)

$node = $nodeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $node) {
  $node = (Get-Command node -ErrorAction SilentlyContinue).Source
}
if (-not $node -or -not (Test-Path $node)) {
  Write-Error "node.exe not found. Install Node.js from https://nodejs.org/"
}

Write-Host "Node.js: $node" -ForegroundColor Cyan

$rules = @(
  @{
    DisplayName = "GicleeArt Node.js Outbound (Shopify CLI)"
    Direction   = "Outbound"
    Program     = $node
    Action      = "Allow"
    Description = "Shopify theme dev outbound HTTPS to Shopify"
  },
  @{
    DisplayName = "GicleeArt Node.js Inbound (theme dev 9292)"
    Direction   = "Inbound"
    Program     = $node
    Action      = "Allow"
    Description = "Shopify theme dev local preview http://127.0.0.1:9292"
  }
)

foreach ($rule in $rules) {
  $existing = Get-NetFirewallRule -DisplayName $rule.DisplayName -ErrorAction SilentlyContinue
  if ($existing) {
    Enable-NetFirewallRule -DisplayName $rule.DisplayName | Out-Null
    Write-Host "[OK] Already exists (enabled): $($rule.DisplayName)" -ForegroundColor Yellow
    continue
  }

  New-NetFirewallRule @rule -Profile Domain, Private, Public -Enabled True | Out-Null
  Write-Host "[OK] Added: $($rule.DisplayName)" -ForegroundColor Green
}

Write-Host ""
Write-Host "GicleeArt Node.js firewall rules:" -ForegroundColor Cyan
Get-NetFirewallRule -DisplayName "GicleeArt Node.js*" |
  Select-Object DisplayName, Direction, Action, Enabled, Profile |
  Format-Table -AutoSize

Write-Host "Done. Run Theme dev in GicleeApp again." -ForegroundColor Green
