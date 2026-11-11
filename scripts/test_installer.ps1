param([string]$Installer = 'dist\Klippy-Setup-0.2.0-preview.1.exe')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$taskRoot = (Resolve-Path -LiteralPath '.').Path
$taskQaRoot = Join-Path $taskRoot 'local\installer-qa'
$taskInstallDir = Join-Path $taskQaRoot 'application'
$taskDataDir = Join-Path $taskQaRoot 'data'
if (Test-Path -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{D51FBA83-D0C3-4CA5-BA79-EE038805EC21}_is1') {
    throw 'A Klippy installation is already registered. Use a clean Windows VM to avoid altering it.'
}
New-Item -ItemType Directory -Force -Path $taskQaRoot,$taskDataDir | Out-Null
$taskSentinel = Join-Path $taskDataDir 'settings-preservation.txt'
Set-Content -LiteralPath $taskSentinel -Value 'Klippy installer QA sentinel' -Encoding ascii
$taskOriginalLocalAppData = $env:LOCALAPPDATA
$env:LOCALAPPDATA = $taskDataDir
try {
    & .\.venv\Scripts\python scripts/installer_settings.py prepare
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare isolated settings' }
    foreach ($taskIteration in 1,2) {
        $taskInstallerProcess = Start-Process -FilePath (Join-Path $taskRoot $Installer) -WindowStyle Hidden -PassThru -ArgumentList @(
            '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/NOICONS','/TASKS=""',
            ('/DIR="' + $taskInstallDir + '"'),('/LOG="' + (Join-Path $taskQaRoot "install-$taskIteration.log") + '"'))
        if (-not $taskInstallerProcess.WaitForExit(60000)) { throw 'Installer timed out' }
        if ($taskInstallerProcess.ExitCode -ne 0) { throw 'Installer failed' }
        if (-not (Test-Path -LiteralPath (Join-Path $taskInstallDir 'Klippy.exe'))) { throw 'Application missing after install' }
        if ((Get-Content -LiteralPath $taskSentinel) -ne 'Klippy installer QA sentinel') { throw 'Settings sentinel changed' }
        & .\.venv\Scripts\python scripts/installer_settings.py verify
        if ($LASTEXITCODE -ne 0) { throw 'SQLite settings were not preserved' }
    }
    $taskSmokeReport = Join-Path $taskQaRoot 'installed-smoke.txt'
    $taskApp = Start-Process -FilePath (Join-Path $taskInstallDir 'Klippy.exe') -WindowStyle Hidden -PassThru -ArgumentList @(
        '--smoke-test','--smoke-report',('"' + $taskSmokeReport + '"'))
    if (-not $taskApp.WaitForExit(30000) -or $taskApp.ExitCode -ne 0) { throw 'Installed startup failed' }
    $taskUninstaller = Start-Process -FilePath (Join-Path $taskInstallDir 'unins000.exe') -WindowStyle Hidden -PassThru -ArgumentList @(
        '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="' + (Join-Path $taskQaRoot 'uninstall.log') + '"'))
    if (-not $taskUninstaller.WaitForExit(60000) -or $taskUninstaller.ExitCode -ne 0) { throw 'Uninstaller failed' }
    if (Test-Path -LiteralPath (Join-Path $taskInstallDir 'Klippy.exe')) { throw 'Application executable remains after uninstall' }
    if (-not (Test-Path -LiteralPath $taskSentinel)) { throw 'Uninstall removed preserved user data' }
    @{
        status='passed'; environment='Development host, not a clean VM';
        tests=@('per-user install','same-version reinstall preserving isolated data','installed application smoke test',
                'uninstall removes executable','uninstall preserves isolated user data');
        limitations=@('not a cross-version upgrade','not clean-machine qualification','no speech model payload')
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskQaRoot 'results.json') -Encoding utf8
    Write-Output 'Installer QA passed on development host. Clean VM and cross-version upgrade remain untested.'
} finally {
    $env:LOCALAPPDATA = $taskOriginalLocalAppData
}
