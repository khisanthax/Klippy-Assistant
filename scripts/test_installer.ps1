param([string]$Installer = 'dist\Klippy-Setup-0.8.0-preview.3.exe', [string]$PreviousInstaller = '',
      [string]$Python = '.venv\Scripts\python.exe', [switch]$BlockExternalNetwork,
      [switch]$MeasurePerformance, [ValidateSet('on','off')][string]$Consent='on')
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
$taskDataDir = Join-Path $taskQaRoot ("profile-" + $Consent + "-" + [Guid]::NewGuid())
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
    & $Python scripts/installer_settings.py prepare $Consent
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare isolated settings' }
    $taskIteration = 0
    $taskInstallers = @($PreviousInstaller, $Installer, $Installer) | Where-Object { $_ }
    if ($BlockExternalNetwork) {
        if (Get-NetFirewallProfile | Where-Object { -not $_.Enabled }) {
            throw 'Offline qualification requires enabled Windows firewall profiles'
        }
        $taskExternalAddresses = @('0.0.0.0-126.255.255.255','128.0.0.0-255.255.255.255',
                                  '::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')
        $taskBlocked = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        function Block-QaProgram([string]$Program) {
            if ($taskBlocked.Add($Program)) {
                New-NetFirewallRule -DisplayName $taskFirewallGroup -Group $taskFirewallGroup -Direction Outbound -Action Block -Program $Program -RemoteAddress $taskExternalAddresses | Out-Null
            }
        }
        foreach ($taskSetupPath in $taskInstallers) { Block-QaProgram (Resolve-Path -LiteralPath $taskSetupPath).Path }
        Block-QaProgram (Join-Path $taskInstallDir 'Klippy.exe')
        Block-QaProgram (Join-Path $taskInstallDir 'unins000.exe')
    }
    foreach ($taskTargetInstaller in $taskInstallers) {
        $taskIteration++
        if ($taskTargetInstaller -eq $PreviousInstaller -and (Get-FileHash $PreviousInstaller).Hash -ne '0c308b113082c2bca18ba328d005e4d659ace77b909c497012775b79b0095238') {
            throw 'Previous installer differs from the published v0.7.2-preview.1 digest.'
        }
        $taskInstallerProcess = Start-Process -FilePath (Resolve-Path -LiteralPath $taskTargetInstaller).Path -WindowStyle Hidden -PassThru -ArgumentList @(
            '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/NOICONS','/TASKS=""',
            ('/DIR="' + $taskInstallDir + '"'),('/LOG="' + (Join-Path $taskQaRoot "install-$taskIteration.log") + '"'))
        Wait-QaProcess $taskInstallerProcess 240
        if (-not (Test-Path -LiteralPath (Join-Path $taskInstallDir 'Klippy.exe'))) { throw 'Application missing after install' }
        if ((Get-Content -LiteralPath $taskSentinel) -ne 'Klippy installer QA sentinel') { throw 'Settings sentinel changed' }
        & $Python scripts/installer_settings.py verify $Consent
        if ($LASTEXITCODE -ne 0) { throw 'SQLite settings were not preserved' }
        if ($BlockExternalNetwork) {
            $taskRuntimes = @(Get-ChildItem -LiteralPath $taskInstallDir -Recurse -Filter 'llama-server.exe')
            if (-not $taskRuntimes) { throw 'Bundled language runtime missing for firewall qualification' }
            foreach ($taskRuntime in $taskRuntimes) { Block-QaProgram $taskRuntime.FullName }
        }
        if ($taskTargetInstaller -eq $Installer) {
            $env:KLIPPY_SMOKE_QA_PROFILE = $taskDataDir
            $taskBoot = Start-Process -FilePath (Join-Path $taskInstallDir 'Klippy.exe') -WindowStyle Hidden -PassThru -ArgumentList '--smoke-test'
            Wait-QaProcess $taskBoot 30
            Remove-Item Env:KLIPPY_SMOKE_QA_PROFILE
            & $Python scripts/installer_settings.py verify $Consent
            if ($LASTEXITCODE -ne 0) { throw 'Opening the upgraded profile changed protected records' }
        }
    }
    $env:KLIPPY_SMOKE_QA_PROFILE = $taskDataDir
    $taskSmokeReport = Join-Path $taskQaRoot 'installed-smoke.txt'
    $taskApp = Start-Process -FilePath (Join-Path $taskInstallDir 'Klippy.exe') -WindowStyle Hidden -PassThru -ArgumentList @(
        '--smoke-test','--smoke-report',('"' + $taskSmokeReport + '"'))
    if (-not $taskApp.WaitForExit(30000) -or $taskApp.ExitCode -ne 0) { throw 'Installed startup failed' }
    Remove-Item Env:KLIPPY_SMOKE_QA_PROFILE
    $taskOrbReport = Join-Path $taskQaRoot 'installed-orb.json'
    $taskOrb = Start-Process -FilePath (Join-Path $taskInstallDir 'Klippy.exe') -WindowStyle Hidden -PassThru -ArgumentList @(
        '--orb-self-test','--smoke-report',('"' + $taskOrbReport + '"'))
    Wait-QaProcess $taskOrb 30
    if (-not (Get-Content -LiteralPath $taskOrbReport -Raw | ConvertFrom-Json).passed) { throw 'Installed orb gate failed' }
    $taskVoiceReport = Join-Path $taskQaRoot 'installed-voice.json'
    $taskVoice = Start-Process -FilePath (Join-Path $taskInstallDir 'Klippy.exe') -WindowStyle Hidden -PassThru -ArgumentList @(
        '--preview-self-test','--smoke-report',('"' + $taskVoiceReport + '"'))
    Wait-QaProcess $taskVoice 300
    if (-not (Get-Content -LiteralPath $taskVoiceReport -Raw | ConvertFrom-Json).engineering_preview_passed) { throw 'Installed engineering preview gate failed' }
    $taskWakeReport = Join-Path $taskQaRoot 'installed-wake.json'
    $taskWake = Start-Process -FilePath (Join-Path $taskInstallDir 'Klippy.exe') -WindowStyle Hidden -PassThru -ArgumentList @(
        '--wake-self-test','--smoke-report',('"' + $taskWakeReport + '"'))
    Wait-QaProcess $taskWake 180
    if (-not (Get-Content -LiteralPath $taskWakeReport -Raw | ConvertFrom-Json).passed) { throw 'Installed wake recheck gate failed' }
    if ($MeasurePerformance) {
        & (Join-Path $PSScriptRoot 'performance_probe.ps1') -Application 'local\installer-qa\application\Klippy.exe'
    }
    $taskExecutableHash = (Get-FileHash (Join-Path $taskInstallDir 'Klippy.exe')).Hash.ToLowerInvariant()
    $taskUninstaller = Start-Process -FilePath (Join-Path $taskInstallDir 'unins000.exe') -WindowStyle Hidden -PassThru -ArgumentList @(
        '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="' + (Join-Path $taskQaRoot 'uninstall.log') + '"'))
    Wait-QaProcess $taskUninstaller 120
    if (Test-Path -LiteralPath (Join-Path $taskInstallDir 'Klippy.exe')) { throw 'Application executable remains after uninstall' }
    if (-not (Test-Path -LiteralPath $taskSentinel)) { throw 'Uninstall removed preserved user data' }
    & $Python scripts/installer_settings.py verify $Consent
    if ($LASTEXITCODE -ne 0) { throw 'Uninstall or application startup changed protected SQLite records' }
    $taskReportHashes = @{}
    foreach ($taskReport in @($taskSmokeReport,$taskOrbReport,$taskVoiceReport,$taskWakeReport)) {
        $taskReportHashes[[IO.Path]::GetFileName($taskReport)] = (Get-FileHash -LiteralPath $taskReport).Hash.ToLowerInvariant()
    }
    if ($MeasurePerformance) {
        foreach ($taskReport in 'local/performance-voice.json','local/performance-budget.json') {
            $taskReportHashes[[IO.Path]::GetFileName($taskReport)] = (Get-FileHash -LiteralPath $taskReport).Hash.ToLowerInvariant()
        }
    }
    @{
        report_sha256=$taskReportHashes
        executable_sha256=$taskExecutableHash; consent=$Consent; preserved_profile_sha256=(Get-Content -Raw ($taskDataDir + '.sha256')).Trim();
        source_sha=(git rev-parse HEAD); run_id=$env:GITHUB_RUN_ID; run_attempt=$env:GITHUB_RUN_ATTEMPT;
        status='passed'; environment=$(if ($env:GITHUB_ACTIONS -eq 'true') { 'Fresh Windows CI runner; not a clean Windows desktop VM' } else { 'Development host; not a clean VM' });
        host_ram_bytes=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory;
        os=[Environment]::OSVersion.VersionString; build_run=$env:KLIPPY_QUALIFIED_BUILD_RUN;
        installer_sha256=(Get-FileHash -LiteralPath (Resolve-Path -LiteralPath $Installer).Path -Algorithm SHA256).Hash.ToLowerInvariant();
        cross_version_upgrade=[bool]$PreviousInstaller; external_network_blocked=[bool]$BlockExternalNetwork;
        performance_budget_test=[bool]$MeasurePerformance;
        firewall_profiles=$(if ($BlockExternalNetwork) { @(Get-NetFirewallProfile | Select-Object Name,Enabled) } else { @() });
        installers=$taskInstallers; tests=@('per-user install','same-version reinstall preserving isolated data','installed application smoke test',
                'installed synthetic audio orb states/rendering/geometry/cleanup and performance',
                'installed offline engineering query/wake-followup preview; full voice diagnostics retained separately',
                'uninstall removes executable','uninstall preserves isolated user data');
        limitations=@('not clean Windows desktop VM qualification','not physical microphone accuracy')
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskQaRoot 'results.json') -Encoding utf8
    Write-Output 'Installer QA passed; see local/installer-qa/results.json for exact scope.'
} finally {
    if ($BlockExternalNetwork) { Get-NetFirewallRule -Group $taskFirewallGroup -ErrorAction SilentlyContinue | Remove-NetFirewallRule }
    Remove-Item Env:KLIPPY_SMOKE_QA_PROFILE -ErrorAction SilentlyContinue
    $env:LOCALAPPDATA = $taskOriginalLocalAppData
}
