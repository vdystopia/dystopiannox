# Builds the map editor without Visual Studio or the Windows SDK.
#
# Uses the .NET Framework 4 MSBuild that ships with Windows, plus a pinned copy of
# Microsoft's Roslyn C# compiler from nuget.org (the in-box compiler is C# 5 only).
# Localized resources are skipped because satellite assemblies need al.exe from the SDK.
#
#   powershell -ExecutionPolicy Bypass -File build.ps1 [-Configuration Debug|Release]

param([string]$Configuration = 'Release')
$ErrorActionPreference = 'Stop'

$RoslynVersion = '5.9.0'
$RoslynSha256  = 'b0227910320c5af14d80ec32b5e1a759c1e3cc2ec12e7d9cc8862cf826bd9551'

$root   = $PSScriptRoot
$tools  = Join-Path $root '.tools'
$csc    = Join-Path $tools "roslyn-$RoslynVersion\tasks\net472"
$msbuild = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\MSBuild.exe'

if (-not (Test-Path (Join-Path $csc 'csc.exe'))) {
    New-Item -ItemType Directory -Force $tools | Out-Null
    $pkg = Join-Path $tools "roslyn-$RoslynVersion.nupkg"
    $url = "https://api.nuget.org/v3-flatcontainer/microsoft.net.compilers.toolset/$RoslynVersion/microsoft.net.compilers.toolset.$RoslynVersion.nupkg"
    Write-Host "Downloading Roslyn $RoslynVersion..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    (New-Object Net.WebClient).DownloadFile($url, $pkg)
    $hash = (Get-FileHash $pkg -Algorithm SHA256).Hash.ToLower()
    if ($hash -ne $RoslynSha256) { Remove-Item $pkg; throw "Roslyn package hash mismatch: $hash" }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::ExtractToDirectory($pkg, (Join-Path $tools "roslyn-$RoslynVersion"))
    Remove-Item $pkg
}

& $msbuild (Join-Path $root 'Nox Map Editor.sln') /t:Rebuild /nologo /v:minimal `
    "/p:Configuration=$Configuration" '/p:Platform=Any CPU' `
    "/p:CscToolPath=$csc" /p:CscToolExe=csc.exe /p:SkipSatelliteResources=true
if ($LASTEXITCODE -ne 0) { throw "Build failed ($LASTEXITCODE)" }

Write-Host "Built: $(Join-Path $root "MapEditor\bin\$Configuration\MapEditor.exe")"
