[CmdletBinding(SupportsShouldProcess)]
param([switch]$RemoveGenerated)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
# Literal allowlist. Installers, reports, model sources, profiles and Git data are outside it.
foreach ($relative in @('.pytest_cache', '.ruff_cache', 'dist\Klippy')) {
    $candidate = Join-Path $root $relative
    if (-not (Test-Path -LiteralPath $candidate -PathType Container)) { continue }
    $path = (Resolve-Path -LiteralPath $candidate).Path
    if ($path -ne [IO.Path]::GetFullPath($candidate) -or
        -not $path.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unexpected generated path $relative"
    }
    $ancestor = Get-Item -Force -LiteralPath $path
    while ($ancestor.FullName -ne $root) {
        if ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Linked path in $relative" }
        $ancestor = $ancestor.Parent
    }
    $entries = @(Get-ChildItem -Force -Recurse -LiteralPath $path)
    if ($entries | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) {
        throw "Linked contents in $relative"
    }
    $bytes = ($entries | Where-Object { -not $_.PSIsContainer } | Measure-Object Length -Sum).Sum
    [PSCustomObject]@{GeneratedPath=$relative; Bytes=[long]$bytes}
    if ($RemoveGenerated -and $PSCmdlet.ShouldProcess($path, 'Remove generated output')) {
        Remove-Item -Force -Recurse -LiteralPath $path
    }
}
