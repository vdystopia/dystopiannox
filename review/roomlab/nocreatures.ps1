# The room and scene labs' creature-free map copies: loads each map with the built NoxShared.dll (as the editor does),
# removes every creature (thing class MONSTER: monsters and NPCs; PLAYER), and writes the copy for the editor's render.
# Westwood's maps have monsters and NPCs standing in their rooms and the lab's have none (or the kit's posts), which an
# independent blind judge used to tell them apart (2026-10-06): the pictures of both are drawn without any.
# Must run in 32-bit PowerShell: NoxShared targets x86. Used by review/roomlab/labrender.py strip().
param(
    [Parameter(Mandatory)] [string]$Dll,
    [Parameter(Mandatory)] [string]$JobList   # text file, one "<source .map>`t<destination .map>" per line
)
$ErrorActionPreference = 'Stop'
Add-Type -Path $Dll
$creature = [uint64]([NoxShared.ThingDb+Thing+ClassFlags]::MONSTER -bor [NoxShared.ThingDb+Thing+ClassFlags]::PLAYER)
foreach ($line in Get-Content -Encoding UTF8 $JobList) {
    if (-not $line.Trim()) { continue }
    $src, $dst = $line.Split("`t")
    try {
        $fs = [IO.File]::OpenRead($src)
        try {
            $rdr = New-Object NoxShared.NoxBinaryReader($fs, [NoxShared.CryptApi+NoxCryptFormat]::MAP)
            $map = New-Object NoxShared.Map($rdr)
        } finally { $fs.Close() }
        $gone = @()
        foreach ($o in $map.Objects) {
            $t = $null
            if ([NoxShared.ThingDb]::Things.TryGetValue($o.Name, [ref]$t) -and (([uint64]$t.Class) -band $creature)) { $gone += $o }
        }
        foreach ($o in $gone) { $map.Objects.Remove($o) }
        New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
        $map.FileName = $dst
        $map.WriteMap()
        "OK`t$src`t$($gone.Count)"
    } catch {
        "FAIL`t$src`t$($_.Exception.GetBaseException().Message)"
    }
}
