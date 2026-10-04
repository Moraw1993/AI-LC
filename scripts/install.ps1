param(
    [string]$Version = 'latest',
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'AI-LC'),
    [string]$ReleaseDirectory,
    [switch]$NoModifyPath
)
$ErrorActionPreference = 'Stop'
if ($env:PROCESSOR_ARCHITECTURE -notin @('AMD64', 'x86')) { throw 'This installer supports Windows x64 only.' }
if ($Version -eq 'latest') {
    if ($ReleaseDirectory) { throw 'Offline installation requires -Version vX.Y.Z.' }
    $Version = (Invoke-RestMethod 'https://api.github.com/repos/Moraw1993/AI-LC/releases/latest').tag_name
}
if ($Version -notmatch '^v\d+\.\d+\.\d+$') { throw 'Version must be vX.Y.Z.' }
$InstallRoot = [IO.Path]::GetFullPath($InstallRoot)
$asset = 'ailearn-windows-x64.exe'
$bin = Join-Path $InstallRoot 'bin'
$versionDir = Join-Path $InstallRoot "versions/$Version"
$shim = Join-Path $bin 'ailearn.cmd'
$target = Join-Path $versionDir 'ailearn.exe'
foreach ($path in @($InstallRoot, $bin, (Join-Path $InstallRoot 'versions'), $versionDir, $shim)) {
    if ((Test-Path -LiteralPath $path) -and ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Redirected install path: $path"
    }
}
$shimText = "@echo off`r`n`"%~dp0..\versions\$Version\ailearn.exe`" %*`r`nexit /b %ERRORLEVEL%`r`n"
if (Test-Path -LiteralPath $shim) {
    $old = [IO.File]::ReadAllText($shim)
    if ($old -notmatch '^@echo off\r\n"%~dp0\.\.\\versions\\v\d+\.\d+\.\d+\\ailearn\.exe" %\*\r\nexit /b %ERRORLEVEL%\r\n$') {
        throw 'Existing ailearn.cmd is not owned by this installer; preserved.'
    }
}
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
$stage = Join-Path $InstallRoot ('.install-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    foreach ($name in @($asset, "$asset.sha256")) {
        $out = Join-Path $stage $name
        if ($ReleaseDirectory) { Copy-Item -LiteralPath (Join-Path $ReleaseDirectory $name) -Destination $out }
        else { Invoke-WebRequest "https://github.com/Moraw1993/AI-LC/releases/download/$Version/$name" -OutFile $out }
    }
    $hashLine = [IO.File]::ReadAllText((Join-Path $stage "$asset.sha256")).Trim()
    if ($hashLine -notmatch ('^([a-f0-9]{64})  ' + [regex]::Escape($asset) + '$')) { throw 'Invalid checksum manifest.' }
    $expected = $Matches[1]
    $download = Join-Path $stage $asset
    if ((Get-FileHash -LiteralPath $download -Algorithm SHA256).Hash.ToLower() -ne $expected) { throw 'Checksum mismatch.' }
    Unblock-File -LiteralPath $download
    $actualVersion = & $download --version
    if ($LASTEXITCODE -ne 0 -or $actualVersion -ne $Version.Substring(1)) { throw 'Executable version mismatch.' }
    New-Item -ItemType Directory -Force -Path (Split-Path $versionDir) | Out-Null
    if (Test-Path -LiteralPath $versionDir) {
        if (-not (Test-Path -LiteralPath $target) -or (Get-FileHash -LiteralPath $target).Hash.ToLower() -ne $expected) { throw 'Existing version differs; preserved.' }
    } else {
        $payload = Join-Path $stage 'payload'
        New-Item -ItemType Directory -Path $payload | Out-Null
        Move-Item -LiteralPath $download -Destination (Join-Path $payload 'ailearn.exe')
        Move-Item -LiteralPath $payload -Destination $versionDir
    }
    New-Item -ItemType Directory -Force -Path $bin | Out-Null
    $pending = Join-Path $stage 'ailearn.cmd'
    [IO.File]::WriteAllText($pending, $shimText, [Text.Encoding]::ASCII)
    Move-Item -LiteralPath $pending -Destination $shim -Force
    if (-not $NoModifyPath) {
        $userPath = [string][Environment]::GetEnvironmentVariable('Path', 'User')
        $pathEntries = @($userPath -split ';' | Where-Object { $_ -and $_ -ne $bin })
        $updatedPath = (@($bin) + $pathEntries) -join ';'
        if ($updatedPath -ne $userPath) {
            [Environment]::SetEnvironmentVariable('Path', $updatedPath, 'User')
        }
        $env:Path = "$bin;$env:Path"
    }
    Write-Host "Installed $Version. Open a new terminal, then run: ailearn config --harness codex"
} finally {
    # stage is an exact GUID directory created here under the resolved install root.
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
}
