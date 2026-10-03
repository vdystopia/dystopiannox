# Loads each map with the built NoxShared.dll and saves it again, exactly as the editor does.
# Must run in 32-bit PowerShell: NoxShared targets x86.
param(
    [Parameter(Mandatory)] [string]$Dll,
    [Parameter(Mandatory)] [string]$OutDir,
    [Parameter(Mandatory)] [string]$MapList   # text file, one .map path per line
)
$ErrorActionPreference = 'Stop'
Add-Type -Path $Dll
New-Item -ItemType Directory -Force $OutDir | Out-Null
foreach ($src in Get-Content -Encoding UTF8 $MapList) {
    try {
        $fs = [IO.File]::OpenRead($src)
        try {
            $rdr = New-Object NoxShared.NoxBinaryReader($fs, [NoxShared.CryptApi+NoxCryptFormat]::MAP)
            $map = New-Object NoxShared.Map($rdr)
        } finally { $fs.Close() }
        $map.FileName = Join-Path $OutDir (Split-Path $src -Leaf)
        $map.WriteMap()
        "OK`t$src"
    } catch {
        "FAIL`t$src`t$($_.Exception.GetBaseException().Message)"
    }
}
