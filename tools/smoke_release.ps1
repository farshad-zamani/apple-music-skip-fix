# Synthetic-only package QA. Never opens or repairs the live Apple Music app.
param([string]$ArtifactsRoot = '')
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
if (-not $ArtifactsRoot) { $ArtifactsRoot = Join-Path $root 'dist' }
$ArtifactsRoot = [IO.Path]::GetFullPath($ArtifactsRoot)
$qaRoot = [IO.Path]::GetFullPath((Join-Path $root ('build\package-qa-' + [guid]::NewGuid().ToString('N'))))
if (-not $qaRoot.StartsWith($root + '\build\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Package QA target is outside the workspace build directory.'
}
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{47D86B4E-9178-42E5-8939-88CDEB43B4CB}_is1'
if (Test-Path -LiteralPath $uninstallKey) { throw 'Uninstall an existing assistant before running installer QA.' }
New-Item -ItemType Directory -Path $qaRoot -Force | Out-Null
$results = [ordered]@{ portable_without_python_path = $false; installed_without_python_path = $false; recovery_retained = $false; signatures = @{} }

function Test-DemoExecutable([string]$Path) {
    $info = New-Object Diagnostics.ProcessStartInfo
    $info.FileName = $Path
    $info.Arguments = '--demo --smoke-test'
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.EnvironmentVariables['PATH'] = "$env:SystemRoot\System32;$env:SystemRoot"
    $info.EnvironmentVariables.Remove('PYTHONHOME')
    $info.EnvironmentVariables.Remove('PYTHONPATH')
    $process = [Diagnostics.Process]::Start($info)
    if (-not $process.WaitForExit(30000)) { throw 'Synthetic packaged demo did not exit in 30 seconds.' }
    if ($process.ExitCode -ne 0) { throw "Synthetic packaged demo failed: $($process.ExitCode)" }
}

$version = [regex]::Match((Get-Content -LiteralPath (Join-Path $root 'src\amsf\__init__.py') -Raw), '__version__ = "(\d+\.\d+\.\d+)"').Groups[1].Value
if (-not $version) { throw 'Application version is unavailable.' }
$portable = Join-Path $ArtifactsRoot "AppleMusicSkipFix-$version-Portable.zip"
$setup = Join-Path $ArtifactsRoot "AppleMusicSkipFix-$version-Setup.exe"
$checksumPattern = '^([a-f0-9]{64})  (AppleMusicSkipFix-' + [regex]::Escape($version) + '-(Portable\.zip|Setup\.exe))$'
foreach ($line in Get-Content -LiteralPath (Join-Path $ArtifactsRoot 'SHA256SUMS.txt')) {
    if ($line -notmatch $checksumPattern) { throw 'Unexpected checksum entry.' }
    if ((Get-FileHash -LiteralPath (Join-Path $ArtifactsRoot $Matches[2]) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Matches[1]) { throw 'Artifact hash mismatch.' }
}
Expand-Archive -LiteralPath $portable -DestinationPath (Join-Path $qaRoot 'portable')
$portableExe = Join-Path $qaRoot 'portable\AppleMusicSkipFix\AppleMusicSkipFix.exe'
if (-not (Test-Path -LiteralPath (Join-Path $qaRoot 'portable\AppleMusicSkipFix\_internal\licenses\Qt-upstream\qtbase\LGPL-3.0-only.txt'))) { throw 'LGPL notice missing from distribution.' }
Test-DemoExecutable $portableExe
$results.portable_without_python_path = $true
$destination = Join-Path $qaRoot 'installed'
$arguments = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="' + $destination + '" /LOG="' + (Join-Path $qaRoot 'install.log') + '"'
$install = Start-Process -FilePath $setup -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
if ($install.ExitCode -ne 0) { throw "Installer failed: $($install.ExitCode)" }
Test-DemoExecutable (Join-Path $destination 'AppleMusicSkipFix.exe')
$results.installed_without_python_path = $true
$recoveryRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'AppleMusicSkipFix'
New-Item -ItemType Directory -Path $recoveryRoot -Force | Out-Null
$marker = Join-Path $recoveryRoot ('package-qa-' + [guid]::NewGuid().ToString('N') + '.txt')
[IO.File]::WriteAllText($marker, 'Synthetic package QA retention marker.')
$uninstall = Start-Process -FilePath (Join-Path $destination 'unins000.exe') -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -WindowStyle Hidden -Wait -PassThru
if ($uninstall.ExitCode -ne 0) { throw "Uninstaller failed: $($uninstall.ExitCode)" }
$deadline = [DateTime]::UtcNow.AddSeconds(20)
while ((Test-Path -LiteralPath (Join-Path $destination 'AppleMusicSkipFix.exe')) -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 250 }
if (Test-Path -LiteralPath (Join-Path $destination 'AppleMusicSkipFix.exe')) { throw 'Uninstaller did not remove the installed executable.' }
if (-not (Test-Path -LiteralPath $marker)) { throw 'Uninstaller removed recovery data.' }
$results.recovery_retained = $true
# Delete only our uniquely named synthetic marker, never the containing folder.
Remove-Item -LiteralPath $marker
$results.signatures.portable = [string](Get-AuthenticodeSignature -LiteralPath $portableExe).Status
$results.signatures.setup = [string](Get-AuthenticodeSignature -LiteralPath $setup).Status
$results | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $root 'build\package-qa.json') -Encoding UTF8
$results | ConvertTo-Json -Depth 3
