param(
    [switch]$CleanRuntimeData
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

function Resolve-InProject {
    param([string]$Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $fullPath.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to touch path outside project: $fullPath"
    }
    return $fullPath
}

function Remove-ProjectItem {
    param([string]$RelativePath)

    $target = Resolve-InProject (Join-Path $ProjectRoot $RelativePath)
    if (Test-Path -LiteralPath $target) {
        Write-Host "Removing $RelativePath"
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}

Write-Host "Cleaning Tax Monitor project at: $ProjectRoot"

foreach ($target in @("build", "dist", "TaxMonitor.spec")) {
    Remove-ProjectItem $target
}

Get-ChildItem -LiteralPath $ProjectRoot -Recurse -Force -Directory |
    Where-Object { $_.Name -eq "__pycache__" } |
    ForEach-Object {
        $path = Resolve-InProject $_.FullName
        Write-Host "Removing $($_.FullName.Substring($ProjectRoot.Length + 1))"
        Remove-Item -LiteralPath $path -Recurse -Force
    }

Get-ChildItem -LiteralPath $ProjectRoot -Recurse -Force -File |
    Where-Object { $_.Extension -in @(".pyc", ".tmp", ".log") } |
    ForEach-Object {
        $path = Resolve-InProject $_.FullName
        Write-Host "Removing $($_.FullName.Substring($ProjectRoot.Length + 1))"
        Remove-Item -LiteralPath $path -Force
    }

$releaseDir = Resolve-InProject (Join-Path $ProjectRoot "release")
if (Test-Path -LiteralPath $releaseDir) {
    $keepRelease = @(
        "TaxMonitor-Setup.exe",
        "TaxMonitor-Windows-Installer.zip",
        "SHA256SUMS.txt"
    )
    Get-ChildItem -LiteralPath $releaseDir -Force |
        Where-Object { $keepRelease -notcontains $_.Name } |
        ForEach-Object {
            $path = Resolve-InProject $_.FullName
            Write-Host "Removing release\$($_.Name)"
            Remove-Item -LiteralPath $path -Recurse -Force
        }
}

if ($CleanRuntimeData) {
    foreach ($target in @(
        "tax_monitor_runtime.db",
        "tax_monitor_runtime.db-journal",
        "data\tax_monitor.db-journal",
        "data\reports",
        "data\upload_files",
        "data\uploads",
        "upload_files"
    )) {
        Remove-ProjectItem $target
    }
    foreach ($dir in @("data\reports", "data\upload_files", "data\uploads")) {
        $fullDir = Resolve-InProject (Join-Path $ProjectRoot $dir)
        New-Item -ItemType Directory -Force -Path $fullDir | Out-Null
    }
}

Write-Host ""
Write-Host "Clean complete." -ForegroundColor Green
Write-Host "Release files:"
Get-ChildItem -LiteralPath (Join-Path $ProjectRoot "release") -Force -ErrorAction SilentlyContinue |
    Select-Object Name, Length, LastWriteTime |
    Format-Table -AutoSize
