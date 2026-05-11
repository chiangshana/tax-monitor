param(
    [string]$Python = "..\.venv\Scripts\python.exe",
    [string]$AppName = "TaxMonitor"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python executable not found: $Python"
}

$ReleaseRoot = Join-Path $ProjectRoot "release"
$BuildRoot = Join-Path $env:LOCALAPPDATA "TaxMonitorBuildWindowed"
$SetupBuildRoot = Join-Path $env:LOCALAPPDATA "TaxMonitorSetupBuild"
$DistFolder = Join-Path $BuildRoot "dist\$AppName"
$InstallerName = "TaxMonitor-Windows-Installer"
$InstallerDir = Join-Path $ReleaseRoot $InstallerName
$ZipPath = Join-Path $ReleaseRoot "$InstallerName.zip"
$SetupExePath = Join-Path $ReleaseRoot "TaxMonitor-Setup.exe"

New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null

Write-Host "==> Building Tkinter desktop app with PyInstaller..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name $AppName `
    --workpath (Join-Path $BuildRoot "build") `
    --distpath (Join-Path $BuildRoot "dist") `
    --specpath $BuildRoot `
    --collect-submodules sklearn `
    --collect-submodules pandas `
    --collect-submodules pptx `
    --collect-submodules routers `
    --hidden-import pypdf `
    --hidden-import main `
    --hidden-import uvicorn `
    --add-data "$ProjectRoot\ui;ui" `
    --add-data "$ProjectRoot\examples;examples" `
    --add-data "$ProjectRoot\n8n_tax_monitor_workflow.json;." `
    --add-data "$ProjectRoot\n8n_tax_monitor_obsidian_workflow.json;." `
    --add-data "$ProjectRoot\n8n_tax_monitor_alert_workflow.json;." `
    --add-data "$ProjectRoot\n8n_tax_monitor_gmail_alert_workflow.json;." `
    --add-data "$ProjectRoot\demo_tax_update.txt;." `
    --add-data "$ProjectRoot\README.md;." `
    "desktop_app\__main__.py"

if (-not (Test-Path -LiteralPath (Join-Path $DistFolder "$AppName.exe"))) {
    throw "PyInstaller output missing: $DistFolder"
}

Write-Host "==> Creating installer folder..."
foreach ($Target in @($InstallerDir, $ZipPath, $SetupExePath)) {
    if (Test-Path -LiteralPath $Target) {
        Remove-Item -LiteralPath $Target -Recurse -Force
    }
}
New-Item -ItemType Directory -Force -Path $InstallerDir | Out-Null
Copy-Item -LiteralPath $DistFolder -Destination (Join-Path $InstallerDir $AppName) -Recurse -Force

$installBat = @(
    "@echo off",
    "chcp 65001 >nul",
    "powershell -NoProfile -ExecutionPolicy Bypass -File `"%~dp0install.ps1`"",
    "echo.",
    "pause"
)
Set-Content -LiteralPath (Join-Path $InstallerDir "install.bat") -Encoding ASCII -Value $installBat

$installPs1 = @(
    "`$ErrorActionPreference = 'Stop'",
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()",
    "`$source = Join-Path `$PSScriptRoot 'TaxMonitor'",
    "if (-not (Test-Path -LiteralPath `$source)) { throw `"TaxMonitor folder not found: `$source`" }",
    "`$target = Join-Path `$env:LOCALAPPDATA 'Programs\TaxMonitor'",
    "`$targetParent = Split-Path -Parent `$target",
    "New-Item -ItemType Directory -Force -Path `$targetParent | Out-Null",
    "if (Test-Path -LiteralPath `$target) { Remove-Item -LiteralPath `$target -Recurse -Force }",
    "Copy-Item -LiteralPath `$source -Destination `$target -Recurse -Force",
    "`$exe = Join-Path `$target 'TaxMonitor.exe'",
    "if (-not (Test-Path -LiteralPath `$exe)) { throw `"Installed executable not found: `$exe`" }",
    "`$desktop = [Environment]::GetFolderPath('Desktop')",
    "`$programs = [Environment]::GetFolderPath('Programs')",
    "`$startMenuDir = Join-Path `$programs 'Tax Monitor'",
    "New-Item -ItemType Directory -Force -Path `$startMenuDir | Out-Null",
    "function New-TaxMonitorShortcut {",
    "    param([string]`$ShortcutPath)",
    "    `$parent = Split-Path -Parent `$ShortcutPath",
    "    New-Item -ItemType Directory -Force -Path `$parent | Out-Null",
    "    `$tempShortcut = Join-Path `$env:TEMP ('TaxMonitorShortcut_' + [guid]::NewGuid().ToString('N') + '.lnk')",
    "    `$shell = New-Object -ComObject WScript.Shell",
    "    `$shortcut = `$shell.CreateShortcut(`$tempShortcut)",
    "    `$shortcut.TargetPath = `$exe",
    "    `$shortcut.WorkingDirectory = `$target",
    "    `$shortcut.Description = 'Tax Monitor AI Research Workbench'",
    "    `$shortcut.IconLocation = `"`${exe},0`"",
    "    `$shortcut.Save()",
    "    Move-Item -LiteralPath `$tempShortcut -Destination `$ShortcutPath -Force",
    "}",
    "foreach (`$shortcutPath in @((Join-Path `$desktop 'Tax Monitor.lnk'), (Join-Path `$startMenuDir 'Tax Monitor.lnk'))) { New-TaxMonitorShortcut -ShortcutPath `$shortcutPath }",
    "Write-Host ''",
    "Write-Host 'Tax Monitor installed successfully.' -ForegroundColor Green",
    "Write-Host `"Installed to: `$target`"",
    "Write-Host 'Open Tax Monitor from the desktop shortcut, then use LLM Setup > One-click setup selected model.'",
    "Write-Host 'The app can find/install Ollama, start the local service, and pull the selected model.'"
)
Set-Content -LiteralPath (Join-Path $InstallerDir "install.ps1") -Encoding UTF8 -Value $installPs1

$uninstallBat = @(
    "@echo off",
    "chcp 65001 >nul",
    "powershell -NoProfile -ExecutionPolicy Bypass -File `"%~dp0uninstall.ps1`"",
    "echo.",
    "pause"
)
Set-Content -LiteralPath (Join-Path $InstallerDir "uninstall.bat") -Encoding ASCII -Value $uninstallBat

$uninstallPs1 = @(
    "`$ErrorActionPreference = 'Stop'",
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()",
    "`$target = Join-Path `$env:LOCALAPPDATA 'Programs\TaxMonitor'",
    "`$desktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Tax Monitor.lnk'",
    "`$startMenuDir = Join-Path ([Environment]::GetFolderPath('Programs')) 'Tax Monitor'",
    "Remove-Item -LiteralPath `$target -Recurse -Force -ErrorAction SilentlyContinue",
    "Remove-Item -LiteralPath `$desktopShortcut -Force -ErrorAction SilentlyContinue",
    "Remove-Item -LiteralPath `$startMenuDir -Recurse -Force -ErrorAction SilentlyContinue",
    "Write-Host 'Tax Monitor removed.' -ForegroundColor Green"
)
Set-Content -LiteralPath (Join-Path $InstallerDir "uninstall.ps1") -Encoding UTF8 -Value $uninstallPs1

$runBat = @(
    "@echo off",
    "chcp 65001 >nul",
    "cd /d `"%~dp0TaxMonitor`"",
    "TaxMonitor.exe"
)
Set-Content -LiteralPath (Join-Path $InstallerDir "run_without_install.bat") -Encoding ASCII -Value $runBat

$installReadme = @(
    "Tax Monitor Windows Installer",
    "=============================",
    "",
    "Recommended install:",
    "1. Run TaxMonitor-Setup.exe.",
    "2. Launch Tax Monitor from the desktop shortcut.",
    "",
    "ZIP fallback:",
    "1. Extract TaxMonitor-Windows-Installer.zip.",
    "2. Run install.bat.",
    "",
    "Local LLM setup:",
    "Open Tax Monitor from the desktop shortcut.",
    "Go to LLM Setup.",
    "Choose a model.",
    "Click One-click setup selected model.",
    "",
    "The app can find/install Ollama, start the local service, and pull the selected model.",
    "",
    "This package is unsigned. Windows SmartScreen may show an unknown publisher warning."
)
Set-Content -LiteralPath (Join-Path $InstallerDir "README_INSTALL.txt") -Encoding UTF8 -Value $installReadme

Write-Host "==> Creating ZIP package..."
Compress-Archive -LiteralPath $InstallerDir -DestinationPath $ZipPath -Force

Write-Host "==> Creating single-file setup EXE with IExpress..."
if (Get-Command iexpress.exe -ErrorAction SilentlyContinue) {
    if (Test-Path -LiteralPath $SetupBuildRoot) {
        Remove-Item -LiteralPath $SetupBuildRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $SetupBuildRoot | Out-Null
    Copy-Item -LiteralPath $ZipPath -Destination (Join-Path $SetupBuildRoot "$InstallerName.zip") -Force

    $payloadPs1 = @(
        "`$ErrorActionPreference = 'Stop'",
        "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()",
        "`$payload = Join-Path `$PSScriptRoot 'TaxMonitor-Windows-Installer.zip'",
        "`$workDir = Join-Path `$env:TEMP ('TaxMonitorInstaller_' + [guid]::NewGuid().ToString('N'))",
        "New-Item -ItemType Directory -Force -Path `$workDir | Out-Null",
        "try {",
        "    Expand-Archive -LiteralPath `$payload -DestinationPath `$workDir -Force",
        "    `$installScript = Join-Path `$workDir 'TaxMonitor-Windows-Installer\install.ps1'",
        "    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File `$installScript",
        "} finally {",
        "    Remove-Item -LiteralPath `$workDir -Recurse -Force -ErrorAction SilentlyContinue",
        "}"
    )
    Set-Content -LiteralPath (Join-Path $SetupBuildRoot "install_payload.ps1") -Encoding UTF8 -Value $payloadPs1

    $StageSetupExe = Join-Path $SetupBuildRoot "TaxMonitor-Setup.exe"
    $SedPath = Join-Path $SetupBuildRoot "TaxMonitorSetup.sed"
    $sed = @(
        "[Version]",
        "Class=IEXPRESS",
        "SEDVersion=3",
        "[Options]",
        "PackagePurpose=InstallApp",
        "ShowInstallProgramWindow=1",
        "HideExtractAnimation=0",
        "UseLongFileName=1",
        "InsideCompressed=0",
        "CAB_FixedSize=0",
        "CAB_ResvCodeSigning=0",
        "RebootMode=N",
        "InstallPrompt=%InstallPrompt%",
        "DisplayLicense=%DisplayLicense%",
        "FinishMessage=%FinishMessage%",
        "TargetName=%TargetName%",
        "FriendlyName=%FriendlyName%",
        "AppLaunched=%AppLaunched%",
        "PostInstallCmd=<None>",
        "AdminQuietInstCmd=%AppLaunched%",
        "UserQuietInstCmd=%AppLaunched%",
        "SourceFiles=SourceFiles",
        "[Strings]",
        "InstallPrompt=",
        "DisplayLicense=",
        "FinishMessage=Tax Monitor installation completed.",
        "TargetName=$StageSetupExe",
        "FriendlyName=Tax Monitor Installer",
        "AppLaunched=powershell.exe -NoProfile -ExecutionPolicy Bypass -File install_payload.ps1",
        "FILE0=TaxMonitor-Windows-Installer.zip",
        "FILE1=install_payload.ps1",
        "[SourceFiles]",
        "SourceFiles0=$SetupBuildRoot\",
        "[SourceFiles0]",
        "%FILE0%=",
        "%FILE1%="
    )
    Set-Content -LiteralPath $SedPath -Encoding ASCII -Value $sed

    Start-Process -FilePath "iexpress.exe" -ArgumentList @("/N", "/Q", $SedPath) -Wait -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 2
    if (-not (Test-Path -LiteralPath $StageSetupExe)) {
        Start-Process -FilePath (Join-Path $env:WINDIR "System32\iexpress.exe") -ArgumentList @("/N", "/Q", $SedPath) -Wait -WindowStyle Hidden | Out-Null
        Start-Sleep -Seconds 2
    }
    if (-not (Test-Path -LiteralPath $StageSetupExe)) {
        $DdfPath = Join-Path $SetupBuildRoot "~TaxMonitor-Setup.DDF"
        if (Test-Path -LiteralPath $DdfPath) {
            Write-Host "IExpress left a DDF without a setup exe; running makecab fallback..."
            & makecab.exe /F $DdfPath | Out-Null
            Start-Sleep -Seconds 2
        }
    }
    if (-not (Test-Path -LiteralPath $StageSetupExe)) {
        throw "IExpress did not create $StageSetupExe"
    }
    Copy-Item -LiteralPath $StageSetupExe -Destination $SetupExePath -Force
    $global:LASTEXITCODE = 0
} else {
    Write-Warning "IExpress not found. ZIP package was created, but single EXE setup was skipped."
}

Write-Host "==> Writing SHA256SUMS.txt..."
$HashTargets = @()
if (Test-Path -LiteralPath $SetupExePath) { $HashTargets += $SetupExePath }
$HashTargets += $ZipPath
$HashLines = foreach ($Path in $HashTargets) {
    $Hash = Get-FileHash -LiteralPath $Path -Algorithm SHA256
    "$($Hash.Hash)  $([IO.Path]::GetFileName($Path))"
}
Set-Content -LiteralPath (Join-Path $ReleaseRoot "SHA256SUMS.txt") -Value $HashLines -Encoding ASCII

Write-Host "==> Release files:"
Get-ChildItem -LiteralPath $ReleaseRoot | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
Write-Host "Done." -ForegroundColor Green



