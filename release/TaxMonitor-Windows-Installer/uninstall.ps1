$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$target = Join-Path $env:LOCALAPPDATA 'Programs\TaxMonitor'
$desktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Tax Monitor.lnk'
$startMenuDir = Join-Path ([Environment]::GetFolderPath('Programs')) 'Tax Monitor'
Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $desktopShortcut -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $startMenuDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host 'Tax Monitor removed.' -ForegroundColor Green
