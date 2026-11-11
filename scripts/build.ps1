param(
    [switch]$Stable,
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
    Invoke-Checked $Python @('-c', 'from pathlib import Path; from klippy.models import verify_pack; verify_pack(Path("models"))')
    throw 'Stable publication remains disabled until RELEASE_CHECKLIST.md has reviewed hardware/installer evidence.'
}
Invoke-Checked $Python @('-m', 'pytest', '-q')
Invoke-Checked $Python @('-m', 'ruff', 'check', 'src', 'tests', 'scripts')
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
        '--hidden-import', 'keyring.backends.Windows', '--add-data', 'build/licenses;licenses',
        '--add-data', 'models/manifest.json;models', 'scripts/launcher.py')
} finally {
    $env:PATH = $taskPreviousPath
}
$smokeReport = Join-Path $PWD 'build\frozen-smoke.txt'
$process = Start-Process -FilePath (Join-Path $PWD 'dist\Klippy\Klippy.exe') -ArgumentList @('--smoke-test', '--smoke-report', ('"' + $smokeReport + '"')) -WindowStyle Hidden -PassThru
if (-not $process.WaitForExit(30000)) { $process.Kill(); throw 'Frozen application smoke test timed out' }
if ($process.ExitCode -ne 0) { throw 'Frozen application smoke test failed' }
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
Get-ChildItem -LiteralPath 'dist' -Filter 'Klippy-Setup-*.exe' | ForEach-Object {
    $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $($_.Name)" | Set-Content -Encoding ascii -LiteralPath ($_.FullName + '.sha256')
}
