# Lists every object that holds others (chests, creatures) in a map, as the editor's library reads it: a check that
# generated loot and carried items were written where the game will find them.
# Must run in 32-bit PowerShell: NoxShared targets x86.
param([Parameter(Mandatory)] [string]$Map)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Add-Type -AssemblyName System.Drawing
Add-Type -Path (Join-Path $repo 'Shared\bin\Release\NoxShared.dll')
$fs = [IO.File]::OpenRead($Map)
try { $m = New-Object NoxShared.Map((New-Object NoxShared.NoxBinaryReader($fs, [NoxShared.CryptApi+NoxCryptFormat]::MAP))) }
finally { $fs.Close() }
$xf = [NoxShared.Map+Object].GetField('ExtraData', [Reflection.BindingFlags]'NonPublic,Instance')
foreach ($o in $m.Objects) {
    if ($o.InventoryList.Count -eq 0) { continue }
    $inv = $o.InventoryList | ForEach-Object {
        $x = $xf.GetValue($_)
        $extra = if ($_.Name -eq 'Gold') { "($($x.Amount))" } elseif ($x.PSObject.Properties['Durability']) { "[$($x.Durability)]" } else { '' }
        "$($_.Name)$extra"
    }
    "$($o.Name)`t$($o.Scr_Name)`t$($o.Location.X),$($o.Location.Y)`t$($inv -join ', ')"
}
