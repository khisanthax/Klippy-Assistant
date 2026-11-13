param([string]$Installer = 'dist\Klippy-Setup-0.5.1-preview.1.exe', [string]$PreviousInstaller = '',
      [string]$Python = '.venv\Scripts\python.exe', [switch]$BlockExternalNetwork,
      [switch]$MeasurePerformance)
$ErrorActionPreference = 'Stop'
function Wait-QaProcess {
    param($Process, [int]$Seconds)
    $taskDeadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while (-not $Process.WaitForExit(30000)) {
        if ([DateTime]::UtcNow -ge $taskDeadline) { throw 'Installer QA process timed out' }
    }
    if ($Process.ExitCode -ne 0) { throw "Installer QA process failed: $($Process.ExitCode)" }
}
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
$taskFirewallGroup = "Klippy-QA-" + [Guid]::NewGuid().ToString()
$env:LOCALAPPDATA = $taskDataDir
try {
    & $Python scripts/installer_settings.py prepare
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare isolated settings' }
    $taskIteration = 0
    $taskInstallers = @($PreviousInstaller, $Installer, $Installer) | Where-Object { $_ }
    foreach ($taskTargetInstaller in $taskInstallers) {
        $taskIteration++
        $taskInstallerProcess = Start-Process -FilePath (Resolve-Path -LiteralPath $taskTargetInstaller).Path -WindowStyle Hidden -PassThru -ArgumentList @(
            '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/NOICONS','/TASKS=""',
            ('/DIR="' + $taskInstallDir + '"'),('/LOG="' + (Join-Path $taskQaRoot "install-$taskIteration.log") + '"'))
        Wait-QaProcess $taskInstallerProcess 240
        if (-not (Test-Path -LiteralPath (Join-Path $taskInstallDir 'Klippy.exe'))) { throw 'Application missing after install' }
        if ((Get-Content -LiteralPath $taskSentinel) -ne 'Klippy installer QA sentinel') { throw 'Settings sentinel changed' }
        & $Python scripts/installer_settings.py verify
        if ($LASTEXITCODE -ne 0) { throw 'SQLite settings were not preserved' }
    }
    if ($BlockExternalNetwork) {
        if (Get-NetFirewallProfile | Where-Object { -not $_.Enabled }) {
            throw 'Offline qualification requires enabled Windows firewall profiles'
        }
        $taskExternalAddresses = @('0.0.0.0-126.255.255.255','128.0.0.0-255.255.255.255',
                                  '::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')
        $taskPrograms = @((Join-Path $taskInstallDir 'Klippy.exe')) + @(Get-ChildItem -LiteralPath $taskInstallDir -Recurse -Filter 'llama-server.exe' | ForEach-Object FullName)
        if ($taskPrograms.Count -lt 2) { throw 'Bundled language runtime missing for firewall qualification' }
        foreach ($taskProgram in $taskPrograms) {
            New-NetFirewallRule -DisplayName $taskFirewallGroup -Group $taskFirewallGroup -Direction Outbound -Action Block -Program $taskProgram -RemoteAddress $taskExternalAddresses | Out-Null
        }
    }
    $taskSmokeReport = Join-Path $taskQaRoot 'installed-smoke.txt'
    $taskApp = Start-Process -FilePath (Join-Path $taskInstallDir 'Klippy.exe') -WindowStyle Hidden -PassThru -ArgumentList @(
        '--smoke-test','--smoke-report',('"' + $taskSmokeReport + '"'))
    if (-not $taskApp.WaitForExit(30000) -or $taskApp.ExitCode -ne 0) { throw 'Installed startup failed' }
    $taskVoiceReport = Join-Path $taskQaRoot 'installed-voice.json'
    $taskVoice = Start-Process -FilePath (Join-Path $taskInstallDir 'Klippy.exe') -WindowStyle Hidden -PassThru -ArgumentList @(
        '--preview-self-test','--smoke-report',('"' + $taskVoiceReport + '"'))
    Wait-QaProcess $taskVoice 240
    if (-not (Get-Content -LiteralPath $taskVoiceReport -Raw | ConvertFrom-Json).engineering_preview_passed) { throw 'Installed engineering preview gate failed' }
    if ($MeasurePerformance) {
        & (Join-Path $PSScriptRoot 'performance_probe.ps1') -Application 'local\installer-qa\application\Klippy.exe'
    }
    $taskUninstaller = Start-Process -FilePath (Join-Path $taskInstallDir 'unins000.exe') -WindowStyle Hidden -PassThru -ArgumentList @(
        '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="' + (Join-Path $taskQaRoot 'uninstall.log') + '"'))
    Wait-QaProcess $taskUninstaller 120
    if (Test-Path -LiteralPath (Join-Path $taskInstallDir 'Klippy.exe')) { throw 'Application executable remains after uninstall' }
    if (-not (Test-Path -LiteralPath $taskSentinel)) { throw 'Uninstall removed preserved user data' }
    @{
        status='passed'; environment=$(if ($env:GITHUB_ACTIONS -eq 'true') { 'Fresh Windows CI runner; not a clean Windows desktop VM' } else { 'Development host; not a clean VM' });
        host_ram_bytes=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory;
        os=[Environment]::OSVersion.VersionString; build_run=$env:KLIPPY_QUALIFIED_BUILD_RUN;
        installer_sha256=(Get-FileHash -LiteralPath (Resolve-Path -LiteralPath $Installer).Path -Algorithm SHA256).Hash.ToLowerInvariant();
        cross_version_upgrade=[bool]$PreviousInstaller; external_network_blocked=[bool]$BlockExternalNetwork;
        performance_budget_test=[bool]$MeasurePerformance;
        firewall_profiles=$(if ($BlockExternalNetwork) { @(Get-NetFirewallProfile | Select-Object Name,Enabled) } else { @() });
        installers=$taskInstallers; tests=@('per-user install','same-version reinstall preserving isolated data','installed application smoke test',
                'installed offline engineering query/wake-followup preview; full voice diagnostics retained separately',
                'uninstall removes executable','uninstall preserves isolated user data');
        limitations=@('not clean Windows desktop VM qualification','not physical microphone accuracy')
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskQaRoot 'results.json') -Encoding utf8
    Write-Output 'Installer QA passed; see local/installer-qa/results.json for exact scope.'
} finally {
    if ($BlockExternalNetwork) { Get-NetFirewallRule -Group $taskFirewallGroup -ErrorAction SilentlyContinue | Remove-NetFirewallRule }
    $env:LOCALAPPDATA = $taskOriginalLocalAppData
}
