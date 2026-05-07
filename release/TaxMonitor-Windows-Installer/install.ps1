$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$source = Join-Path $PSScriptRoot 'TaxMonitor'
if (-not (Test-Path -LiteralPath $source)) { throw "TaxMonitor folder not found: $source" }
$target = Join-Path $env:LOCALAPPDATA 'Programs\TaxMonitor'
$targetParent = Split-Path -Parent $target
New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
$exe = Join-Path $target 'TaxMonitor.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Installed executable not found: $exe" }
$desktop = [Environment]::GetFolderPath('Desktop')
$programs = [Environment]::GetFolderPath('Programs')
$startMenuDir = Join-Path $programs 'Tax Monitor'
New-Item -ItemType Directory -Force -Path $startMenuDir | Out-Null
function New-TaxMonitorShortcut {
    param([string]$ShortcutPath)
    $parent = Split-Path -Parent $ShortcutPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $tempShortcut = Join-Path $env:TEMP ('TaxMonitorShortcut_' + [guid]::NewGuid().ToString('N') + '.lnk')
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($tempShortcut)
    $shortcut.TargetPath = $exe
    $shortcut.WorkingDirectory = $target
    $shortcut.Description = 'Tax Monitor AI Research Workbench'
    $shortcut.IconLocation = "${exe},0"
    $shortcut.Save()
    Move-Item -LiteralPath $tempShortcut -Destination $ShortcutPath -Force
}
foreach ($shortcutPath in @((Join-Path $desktop 'Tax Monitor.lnk'), (Join-Path $startMenuDir 'Tax Monitor.lnk'))) { New-TaxMonitorShortcut -ShortcutPath $shortcutPath }
Write-Host ''
Write-Host 'Tax Monitor installed successfully.' -ForegroundColor Green
Write-Host "Installed to: $target"
Write-Host 'For local LLM analysis, install Ollama and run: ollama pull qwen3:8b'
