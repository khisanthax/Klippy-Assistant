param(
    [switch]$Stable,
    [switch]$ValidatedSource,
    [string]$ModelPack = 'local\bundle-models-voice',
    [string]$Iscc = '',
    [string]$Python = '.venv\Scripts\python.exe'
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Invoke-Checked {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Build step failed: $Exe" }
}
if ($Stable) {
    throw 'Stable publication remains disabled until RELEASE_CHECKLIST.md has reviewed hardware/installer evidence.'
}
$taskModelPack = (Resolve-Path -LiteralPath $ModelPack).Path
Invoke-Checked $Python @('scripts/verify_models.py', $taskModelPack, '--qualified')
if ($ValidatedSource) {
    if ($env:GITHUB_ACTIONS -ne 'true' -or $env:GITHUB_SHA -ne (git rev-parse HEAD)) {
        throw 'Reusing source validation requires the same GitHub Actions checkout.'
    }
} else {
    Invoke-Checked $Python @('-m', 'pytest', '-q')
    Invoke-Checked $Python @('-m', 'ruff', 'check', 'src', 'tests', 'scripts')
}
Invoke-Checked $Python @('scripts/collect_licenses.py', 'build/licenses')
$taskPythonExe = (Get-Command $Python).Source
$taskPythonBase = & $taskPythonExe -c 'import sys; print(sys.base_prefix)'
$taskPreviousPath = $env:PATH
try {
    # Ambient tools can contain incompatible DLLs (e.g. Poppler ICU). Never freeze them.
    $env:PATH = @((Split-Path $taskPythonExe), $taskPythonBase, (Join-Path $taskPythonBase 'DLLs'),
        (Join-Path $env:SystemRoot 'System32'), $env:SystemRoot) -join ';'
    Invoke-Checked $taskPythonExe @('-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed', '--onedir',
        '--name', 'Klippy', '--paths', 'src', '--collect-all', 'sherpa_onnx', '--collect-all', 'sounddevice',
        '--collect-all', 'pywebrtc_audio', '--additional-hooks-dir', 'packaging/hooks',
        '--exclude-module', 'cmudict', '--exclude-module', 'sentencepiece',
        '--hidden-import', 'keyring.backends.Windows', '--add-data', 'build/licenses;licenses',
        '--add-data', ($taskModelPack + ';models'), 'scripts/launcher.py')
} finally {
    $env:PATH = $taskPreviousPath
}
$smokeReport = Join-Path $PWD 'build\frozen-smoke.txt'
$process = Start-Process -FilePath (Join-Path $PWD 'dist\Klippy\Klippy.exe') -ArgumentList @('--smoke-test', '--smoke-report', ('"' + $smokeReport + '"')) -WindowStyle Hidden -PassThru
if (-not $process.WaitForExit(30000)) { $process.Kill(); throw 'Frozen application smoke test timed out' }
if ($process.ExitCode -ne 0) { throw 'Frozen application smoke test failed' }
$orbReport = Join-Path $PWD 'build\frozen-orb.json'
$orbProcess = Start-Process -FilePath (Join-Path $PWD 'dist\Klippy\Klippy.exe') -ArgumentList @('--orb-self-test', '--smoke-report', ('"' + $orbReport + '"')) -WindowStyle Hidden -PassThru
if (-not $orbProcess.WaitForExit(30000)) { $orbProcess.Kill(); throw 'Frozen orb self-test timed out' }
if ($orbProcess.ExitCode -ne 0) {
    if (Test-Path -LiteralPath $orbReport) { Get-Content -LiteralPath $orbReport -Raw | Write-Output }
    throw 'Frozen orb self-test failed'
}
$voiceReport = Join-Path $PWD 'build\frozen-voice.json'
$voiceProcess = Start-Process -FilePath (Join-Path $PWD 'dist\Klippy\Klippy.exe') -ArgumentList @('--preview-self-test', '--smoke-report', ('"' + $voiceReport + '"')) -WindowStyle Hidden -PassThru
if (-not $voiceProcess.WaitForExit(300000)) { $voiceProcess.Kill(); throw 'Frozen engineering preview self-test timed out' }
if ($voiceProcess.ExitCode -ne 0) {
    if (Test-Path -LiteralPath $voiceReport) { Get-Content -LiteralPath $voiceReport -Raw | Write-Output }
    throw "Frozen engineering preview self-test failed; see $voiceReport"
}
$wakeReport = Join-Path $PWD 'build\frozen-wake.json'
$wakeProcess = Start-Process -FilePath (Join-Path $PWD 'dist\Klippy\Klippy.exe') -ArgumentList @('--wake-self-test', '--smoke-report', ('"' + $wakeReport + '"')) -WindowStyle Hidden -PassThru
if (-not $wakeProcess.WaitForExit(180000)) { $wakeProcess.Kill(); throw 'Frozen wake recheck qualification timed out' }
if ($wakeProcess.ExitCode -ne 0) { Get-Content -LiteralPath $wakeReport -Raw; throw 'Frozen wake recheck qualification failed' }
if (-not $Iscc) {
    $candidates = @(
        (Join-Path $PWD 'local\inno\ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 7\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 7\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe')
    )
    $Iscc = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $Iscc) { throw 'Install Inno Setup or supply -Iscc path; frozen application is in dist\Klippy.' }
Invoke-Checked $Iscc @('packaging/klippy.iss')
$taskVersion = (Select-String -Path 'packaging/klippy.iss' -Pattern '^#define AppVersion "([^"]+)"').Matches[0].Groups[1].Value
$taskSetup = Get-Item -LiteralPath ("dist/Klippy-Setup-" + $taskVersion + ".exe")
$hash = (Get-FileHash -LiteralPath $taskSetup.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $($taskSetup.Name)" | Set-Content -Encoding ascii -LiteralPath ($taskSetup.FullName + '.sha256')
@{
    source_sha=(git rev-parse HEAD); run_id=$env:GITHUB_RUN_ID; run_attempt=$env:GITHUB_RUN_ATTEMPT
    installer_sha256=$hash; executable_sha256=(Get-FileHash dist/Klippy/Klippy.exe).Hash.ToLowerInvariant()
} | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath 'build/frozen-build.json'
