#Requires -Version 5.1
<#
.SYNOPSIS
  Odporny start Shopify theme dev (retry na ETIMEDOUT / zajęty port 9292).

.DESCRIPTION
  Skrót pulpitu „Shopify Dev” powinien wskazywać ten skrypt.
  Przed startem: probe HTTPS do sklepu, flush DNS przy problemach, zwolnienie :9292.
  Przy ETIMEDOUT podczas startu: automatyczne ponowienie (domyślnie 5×).
#>

[CmdletBinding()]
param(
  [string]$ThemeRoot = 'C:\Projekty\GicleeArt',
  [string]$Environment = 'development',
  [string]$HostName = '127.0.0.1',
  [int]$Port = 9292,
  [int]$NetworkRetries = 5,
  [int]$LaunchRetries = 5,
  [int]$ProbeTimeoutSec = 25,
  [int]$StartupWaitSec = 120,
  [switch]$SkipNetworkProbe,
  [switch]$NoOpen
)

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

function Write-Step {
  param([string]$Message, [ConsoleColor]$Color = 'Cyan')
  Write-Host ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $Message) -ForegroundColor $Color
}

function Write-WarnStep {
  param([string]$Message)
  Write-Step -Message $Message -Color Yellow
}

function Write-Ok {
  param([string]$Message)
  Write-Step -Message $Message -Color Green
}

function Write-Fail {
  param([string]$Message)
  Write-Step -Message $Message -Color Red
}

function Get-ThemeStore {
  param([string]$Root)
  $toml = Join-Path $Root 'shopify.theme.toml'
  if (-not (Test-Path -LiteralPath $toml)) {
    return 'giclee-art-3.myshopify.com'
  }
  $text = Get-Content -LiteralPath $toml -Raw -ErrorAction SilentlyContinue
  if ($text -match '(?s)\[environments\.development\].*?store\s*=\s*"([^"]+)"') {
    return $Matches[1].Trim()
  }
  return 'giclee-art-3.myshopify.com'
}

function Get-StorefrontPassword {
  param([string]$Root)
  if ($env:SHOPIFY_FLAG_STORE_PASSWORD) {
    return $env:SHOPIFY_FLAG_STORE_PASSWORD.Trim()
  }
  $path = Join-Path $Root '.shopify-store-password.local'
  if (Test-Path -LiteralPath $path) {
    $line = (Get-Content -LiteralPath $path -TotalCount 1 -ErrorAction SilentlyContinue)
    if ($line) { return $line.Trim() }
  }
  return ''
}

function Resolve-ShopifyCli {
  foreach ($name in @('shopify.cmd', 'shopify')) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { return $cmd.Source }
  }
  $candidates = @(
    (Join-Path $env:APPDATA 'npm\shopify.cmd'),
    (Join-Path $env:LOCALAPPDATA 'Programs\npm\shopify.cmd'),
    (Join-Path ${env:ProgramFiles} 'nodejs\shopify.cmd')
  )
  foreach ($c in $candidates) {
    if ($c -and (Test-Path -LiteralPath $c)) { return $c }
  }
  return $null
}

function Test-PortOpen {
  param([string]$HostName, [int]$Port, [int]$TimeoutMs = 400)
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect($HostName, $Port, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
    if (-not $ok) {
      try { $client.Close() } catch {}
      return $false
    }
    $client.EndConnect($iar)
    $client.Close()
    return $true
  } catch {
    return $false
  }
}

function Test-HttpReady {
  param([string]$Url, [int]$TimeoutSec = 8)
  try {
    $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
    if ($resp.StatusCode -ne 200) { return $false }
    $content = [string]$resp.Content
    if ($content.Length -lt 200) { return $false }
    if ($content -match '(?i)enter_password|storefront-password|password-page|name=["'']password["'']') {
      return $false
    }
    return $true
  } catch {
    return $false
  }
}

function Get-ListeningPids {
  param([string]$HostName, [int]$Port)
  $needle = "${HostName}:${Port}"
  $pids = New-Object System.Collections.Generic.List[int]
  $lines = & netstat -ano 2>$null
  foreach ($line in $lines) {
    if ($line -notmatch [regex]::Escape($needle)) { continue }
    if ($line -notmatch 'LISTENING') { continue }
    $parts = @($line -split '\s+' | Where-Object { $_ })
    $pidText = $parts[-1]
    if ($pidText -match '^\d+$') {
      $id = [int]$pidText
      if (-not $pids.Contains($id)) { [void]$pids.Add($id) }
    }
  }
  return @($pids)
}

function Stop-PortListeners {
  param([string]$HostName, [int]$Port)
  $pids = Get-ListeningPids -HostName $HostName -Port $Port
  foreach ($procId in $pids) {
    Write-WarnStep "Zwalniam port ${Port} (PID $procId)…"
    & taskkill /PID $procId /F /T 2>$null | Out-Null
  }
  Start-Sleep -Milliseconds 700
  return $pids
}

function Test-ShopifyReachable {
  param([string]$Store, [int]$TimeoutSec)
  $probes = @(
    @{ Method = 'Post'; Uri = "https://$Store/admin/api/2026-07/graphql.json"; Body = '{}'; ContentType = 'application/json' },
    @{ Method = 'Head'; Uri = "https://$Store/"; Body = $null; ContentType = $null }
  )
  $errors = New-Object System.Collections.Generic.List[string]
  foreach ($p in $probes) {
    try {
      $params = @{
        Uri             = $p.Uri
        Method          = $p.Method
        UseBasicParsing = $true
        TimeoutSec      = $TimeoutSec
      }
      if ($p.Body) {
        $params.Body = $p.Body
        $params.ContentType = $p.ContentType
      }
      $null = Invoke-WebRequest @params
      return @{ Ok = $true; Error = '' }
    } catch {
      $resp = $_.Exception.Response
      if ($resp) {
        try {
          $code = [int]$resp.StatusCode
          if ($code -gt 0 -and $code -lt 500) {
            return @{ Ok = $true; Error = '' }
          }
        } catch {}
      }
      $msg = [string]$_.Exception.Message
      if ($msg -match '(?i)timed out|timeout|ETIMEDOUT|Unable to connect|Nie można nawiązać') {
        [void]$errors.Add('timeout')
      } elseif ($msg) {
        [void]$errors.Add($msg)
      }
    }
  }
  $uniq = $errors | Select-Object -Unique
  return @{ Ok = $false; Error = ($uniq -join '; ') }
}

function Invoke-DnsFlush {
  Write-WarnStep 'ipconfig /flushdns…'
  & ipconfig /flushdns | Out-Null
}

function Ensure-NetworkReady {
  param([string]$Store, [int]$Retries, [int]$TimeoutSec)
  for ($i = 1; $i -le $Retries; $i++) {
    $probe = Test-ShopifyReachable -Store $Store -TimeoutSec $TimeoutSec
    if ($probe.Ok) {
      Write-Ok "Połączenie z $Store OK"
      return $true
    }
    $detail = if ($probe.Error) { $probe.Error } else { 'timeout' }
    Write-WarnStep "Brak połączenia z $Store ($detail) — próba $i/$Retries…"
    if ($i -eq 2 -or $i -eq $Retries) {
      Invoke-DnsFlush
    }
    if ($i -lt $Retries) {
      Start-Sleep -Seconds (3 * $i)
    }
  }
  return $false
}

function Test-LogHasTimeout {
  param([string]$LogFile)
  if (-not (Test-Path -LiteralPath $LogFile)) { return $false }
  $blob = Get-Content -LiteralPath $LogFile -Raw -ErrorAction SilentlyContinue
  if (-not $blob) { return $false }
  return [bool]($blob -match '(?i)etimedout|timed?\s*out|ENETUNREACH|ECONNRESET|fetch failed|socket hang up')
}

function Stop-ProcessTree {
  param([System.Diagnostics.Process]$Process)
  if (-not $Process) { return }
  try {
    if (-not $Process.HasExited) {
      & taskkill /PID $Process.Id /F /T 2>$null | Out-Null
      Start-Sleep -Milliseconds 400
    }
  } catch {}
  try {
    if (-not $Process.HasExited) { $Process.Kill() }
  } catch {}
}

# --- main ---

try {
  $Host.UI.RawUI.WindowTitle = 'Shopify Theme Dev — GicleeArt'
} catch {}

if (-not (Test-Path -LiteralPath $ThemeRoot)) {
  Write-Fail "Brak katalogu motywu: $ThemeRoot"
  exit 1
}
Set-Location -LiteralPath $ThemeRoot

$ipv4 = '--dns-result-order=ipv4first'
if (-not $env:NODE_OPTIONS) {
  $env:NODE_OPTIONS = $ipv4
} elseif ($env:NODE_OPTIONS -notlike "*$ipv4*") {
  $env:NODE_OPTIONS = "$($env:NODE_OPTIONS) $ipv4".Trim()
}

# Dłuższy budżet na wolniejsze połączenia CLI ↔ Shopify
if (-not $env:SHOPIFY_CLI_MAX_REQUEST_TIME_FOR_NETWORK_CALLS) {
  $env:SHOPIFY_CLI_MAX_REQUEST_TIME_FOR_NETWORK_CALLS = '120000'
}

$store = Get-ThemeStore -Root $ThemeRoot
$password = Get-StorefrontPassword -Root $ThemeRoot
$cli = Resolve-ShopifyCli
$previewUrl = "http://${HostName}:${Port}/?giclee_skip_splash=1&giclee_skip_notice=1"

Write-Host ''
Write-Host '══════════════════════════════════════════════════' -ForegroundColor DarkCyan
Write-Host '  Shopify theme dev — start odporny na timeouty' -ForegroundColor Cyan
Write-Host '══════════════════════════════════════════════════' -ForegroundColor DarkCyan
Write-Step "Motyw:  $ThemeRoot"
Write-Step "Sklep:  $store"
Write-Step "Env:    $Environment"
Write-Step "Port:   ${HostName}:${Port}"
if ($cli) {
  Write-Step "CLI:    $cli"
} else {
  Write-Fail 'Nie znaleziono Shopify CLI (shopify.cmd).'
  Write-Host 'Zainstaluj: npm install -g @shopify/cli @shopify/theme' -ForegroundColor Yellow
  exit 1
}
if ($password) {
  $env:SHOPIFY_FLAG_STORE_PASSWORD = $password
  Write-Step 'Hasło sklepu: załadowane'
} else {
  Write-WarnStep 'Brak hasła sklepu (.shopify-store-password.local) — OK, jeśli sklep nie ma password page.'
}
Write-Host ''

if ((Test-PortOpen -HostName $HostName -Port $Port) -and (Test-HttpReady -Url $previewUrl -TimeoutSec 6)) {
  Write-Ok "Theme dev już działa: $previewUrl"
  if (-not $NoOpen) { Start-Process $previewUrl }
  Write-Host 'Zostaw działający proces albo zamknij port przez GicleeApp → Zamknij porty.' -ForegroundColor DarkGray
  exit 0
}

if (Test-PortOpen -HostName $HostName -Port $Port) {
  Write-WarnStep "Port $Port zajęty, ale HTTP nie odpowiada — zabijam zombie…"
  [void](Stop-PortListeners -HostName $HostName -Port $Port)
}

if (-not $SkipNetworkProbe) {
  Write-Step "Sprawdzam łączność z Shopify (timeout ${ProbeTimeoutSec}s)…"
  $netOk = Ensure-NetworkReady -Store $store -Retries $NetworkRetries -TimeoutSec $ProbeTimeoutSec
  if (-not $netOk) {
    Write-Fail "Nie udało się połączyć z $store po $NetworkRetries próbach."
    Write-Host ''
    Write-Host 'ETIMEDOUT = problem sieci (nie auth / theme ID).' -ForegroundColor Yellow
    Write-Host 'Spróbuj: wyłącz VPN, hotspot, firewall dla node.exe' -ForegroundColor Yellow
    Write-Host '  .\cursor-api\scripts\setup-node-firewall.ps1   (jako administrator)' -ForegroundColor Yellow
    Write-Host ''
    Write-Host 'Enter = spróbuj mimo to uruchomić theme dev  |  Ctrl+C = wyjdź' -ForegroundColor DarkGray
    [void][Console]::ReadLine()
  }
}

$cliArgs = [System.Collections.Generic.List[string]]@('theme', 'dev', '--environment', $Environment, '--host', $HostName, '--port', "$Port")
if ($password) {
  [void]$cliArgs.Add('--store-password')
  [void]$cliArgs.Add($password)
}
if (-not $NoOpen) {
  [void]$cliArgs.Add('--open')
}

$logDir = Join-Path $env:TEMP 'giclee-theme-dev'
if (-not (Test-Path -LiteralPath $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}

for ($launch = 1; $launch -le $LaunchRetries; $launch++) {
  if ($launch -gt 1) {
    Write-WarnStep "Ponawiam start theme dev ($launch/$LaunchRetries)…"
    [void](Stop-PortListeners -HostName $HostName -Port $Port)
    Invoke-DnsFlush
    Start-Sleep -Seconds (2 * $launch)
    if (-not $SkipNetworkProbe) {
      [void](Ensure-NetworkReady -Store $store -Retries 3 -TimeoutSec $ProbeTimeoutSec)
    }
  }

  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  $logFile = Join-Path $logDir "theme-dev-$stamp-try$launch.log"
  Write-Step "Start: shopify $($cliArgs -join ' ')"
  Write-Step "Log:   $logFile" -Color DarkGray
  Write-Host ''

  # Uruchomienie przez cmd: przekierowanie stdout+stderr do pliku (nie blokuje bufferów).
  $argParts = foreach ($a in $cliArgs) {
    if ($a -match '[\s"]') { '"' + ($a -replace '"', '\"') + '"' } else { $a }
  }
  $argLine = $argParts -join ' '
  $cmdLine = "/c `"`"$cli`" $argLine > `"$logFile`" 2>&1`""

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $env:ComSpec
  $psi.Arguments = $cmdLine
  $psi.WorkingDirectory = $ThemeRoot
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  $proc = New-Object System.Diagnostics.Process
  $proc.StartInfo = $psi
  [void]$proc.Start()

  # Tail logu w tle (PowerShell job)
  $tailJob = Start-Job -ScriptBlock {
    param($path)
    $shown = 0
    while ($true) {
      if (Test-Path -LiteralPath $path) {
        $lines = Get-Content -LiteralPath $path -ErrorAction SilentlyContinue
        if ($lines -and $lines.Count -gt $shown) {
          $lines[$shown..($lines.Count - 1)] | ForEach-Object { $_ }
          $shown = $lines.Count
        }
      }
      Start-Sleep -Milliseconds 400
    }
  } -ArgumentList $logFile

  $cleanup = {
    Stop-Job $tailJob -ErrorAction SilentlyContinue
    Remove-Job $tailJob -Force -ErrorAction SilentlyContinue
    Stop-ProcessTree -Process $proc
    [void](Stop-PortListeners -HostName $HostName -Port $Port)
  }

  try {
    $ready = $false
    $deadline = (Get-Date).AddSeconds($StartupWaitSec)
    while ((Get-Date) -lt $deadline) {
      Receive-Job $tailJob | ForEach-Object { Write-Host $_ }

      if (Test-HttpReady -Url $previewUrl -TimeoutSec 5) {
        $ready = $true
        break
      }
      if ($proc.HasExited) {
        Start-Sleep -Milliseconds 500
        Receive-Job $tailJob | ForEach-Object { Write-Host $_ }
        break
      }
      Start-Sleep -Seconds 1
    }

    if ($ready) {
      Write-Host ''
      Write-Ok "Theme dev gotowy: $previewUrl"
      Write-Host 'Proces działa — Ctrl+C zatrzyma theme dev i zwolni port 9292.' -ForegroundColor DarkGray
      Write-Host ''
      while (-not $proc.HasExited) {
        Receive-Job $tailJob | ForEach-Object { Write-Host $_ }
        Start-Sleep -Milliseconds 800
      }
      Receive-Job $tailJob -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_ }
      Write-WarnStep "Theme dev zakończył się (exit $($proc.ExitCode))."
      & $cleanup
      exit $(if ($null -ne $proc.ExitCode) { $proc.ExitCode } else { 0 })
    }
  } catch {
    & $cleanup
    throw
  }

  # Startup nieudany
  Stop-Job $tailJob -ErrorAction SilentlyContinue
  Remove-Job $tailJob -Force -ErrorAction SilentlyContinue
  Receive-Job $tailJob -ErrorAction SilentlyContinue | ForEach-Object { Write-Host $_ }

  $timedOut = Test-LogHasTimeout -LogFile $logFile

  if (-not $proc.HasExited) {
    Write-WarnStep 'Serwer nie wstał w czasie — zabijam i ponawiam…'
    Stop-ProcessTree -Process $proc
  } else {
    Write-WarnStep "Proces padł przy starcie (exit $($proc.ExitCode))."
  }
  [void](Stop-PortListeners -HostName $HostName -Port $Port)

  if ($timedOut -and $launch -lt $LaunchRetries) {
    Write-WarnStep 'Wykryto timeout sieci — kolejna próba…'
    continue
  }

  if ($timedOut) {
    Write-Fail "Theme dev nie połączył się z Shopify ($store) po $LaunchRetries próbach."
    Write-Host 'ETIMEDOUT = timeout sieci. VPN off / hotspot / firewall node.exe / flushdns.' -ForegroundColor Yellow
    Write-Host "Log: $logFile" -ForegroundColor DarkGray
    exit 1
  }

  Write-Fail 'Theme dev nie wystartował. Zobacz log powyżej.'
  Write-Host "Log: $logFile" -ForegroundColor DarkGray
  exit $(if ($null -ne $proc.ExitCode) { $proc.ExitCode } else { 1 })
}

Write-Fail 'Wyczerpano próby startu.'
exit 1
