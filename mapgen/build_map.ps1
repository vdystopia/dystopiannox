# Builds a Nox map from a JSON spec using the editor's own library (NoxShared.dll), so the
# result is written exactly the way the editor writes maps and opens cleanly in it.
# Must run in 32-bit PowerShell (NoxShared targets x86); mapgen\build.py handles that.
#
# Spec (all coordinates in grid cells; objects in world pixels, 23 px per cell):
#   name, info{summary, description, author, version, date, type, minPlayers, maxPlayers},
#   ambient[r,g,b], walls[{x,y,facing,material[,variation]}], tiles[{x,y,material}],
#   objects[{type,x,y[,team]}]
param(
    [Parameter(Mandatory)] [string]$Spec,
    [Parameter(Mandatory)] [string]$OutDir
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Add-Type -AssemblyName System.Drawing
Add-Type -Path (Join-Path $repo 'Shared\bin\Release\NoxShared.dll')

$s = Get-Content -Raw -Encoding UTF8 $Spec | ConvertFrom-Json
$errors = New-Object System.Collections.Generic.List[string]

# Start from the editor's own "new map" template.
$template = Join-Path $repo 'MapEditor\bundled\BlankMap.map'
$fs = [IO.File]::OpenRead($template)
try { $map = New-Object NoxShared.Map((New-Object NoxShared.NoxBinaryReader($fs, [NoxShared.CryptApi+NoxCryptFormat]::MAP))) }
finally { $fs.Close() }

$i = $s.info
$map.Info.Summary = $i.summary
$map.Info.Description = $i.description
$map.Info.Author = $i.author
$map.Info.Version = $i.version
$map.Info.Date = $i.date
$map.Info.Type = [NoxShared.Map+MapInfo+MapType][uint32]$i.type
$map.Info.RecommendedMin = [byte]$i.minPlayers
$map.Info.RecommendedMax = [byte]$i.maxPlayers
$map.Ambient.AmbientColor = [Drawing.Color]::FromArgb($s.ambient[0], $s.ambient[1], $s.ambient[2])

$wallNames = [NoxShared.ThingDb]::WallNames
foreach ($w in $s.walls) {
    $mat = $wallNames.IndexOf($w.material)
    if ($mat -lt 0) { $errors.Add("unknown wall material '$($w.material)'"); continue }
    if (($w.x + $w.y) % 2 -ne 0) { $errors.Add("wall at $($w.x),$($w.y) is off the wall grid (x+y must be even)"); continue }
    $nvar = [NoxShared.ThingDb]::Walls[$mat].Variations
    $var = if ($null -ne $w.variation) { [int]$w.variation } else { 0 }
    if ($var -ge $nvar) { $errors.Add("wall at $($w.x),$($w.y): variation $var >= $nvar available"); continue }
    $pt = New-Object Drawing.Point($w.x, $w.y)
    $map.Walls[$pt] = New-Object NoxShared.Map+Wall($pt, [NoxShared.Map+Wall+WallFacing]$w.facing, [byte]$mat, [byte]100, [byte]$var)
}

$tileNames = [NoxShared.ThingDb]::FloorTileNames
foreach ($t in $s.tiles) {
    $mat = $tileNames.IndexOf($t.material)
    if ($mat -lt 0) { $errors.Add("unknown floor material '$($t.material)'"); continue }
    $x = [int]$t.x; $y = [int]$t.y
    if (($x + $y) % 2 -ne 0) { $errors.Add("tile at $x,$y is off the tile grid (x+y must be even)"); continue }
    # Same automatic variation pattern as the editor's tile brush (MapHelper.PlaceTile).
    $cols = [int][NoxShared.ThingDb]::FloorTiles[$mat].numCols
    $rows = [int][NoxShared.ThingDb]::FloorTiles[$mat].numRows
    $h = [math]::Floor(($x + $y) / 2)
    $vari = ($h % $cols) + ((($y % $rows) + 1 + $cols - ($h % $cols)) % $rows) * $cols
    $pt = New-Object Drawing.Point($x, $y)
    $map.Tiles[$pt] = New-Object NoxShared.Map+Tile($pt, [byte]$mat, [uint16]$vari)
}

$extent = 3   # 2 is reserved for the host player (see MapInterface.GetNextObjectExtent)
$things = [NoxShared.ThingDb]::Things
foreach ($o in $s.objects) {
    if (-not $things.ContainsKey($o.type)) { $errors.Add("unknown object type '$($o.type)'"); continue }
    $obj = New-Object NoxShared.Map+Object($o.type, (New-Object Drawing.PointF([float]$o.x, [float]$o.y)))
    $obj.Extent = $extent++
    if ($null -ne $o.team) {
        # Team is only written when the extended-fields flag is set (editor: "extra" checkbox).
        $obj.Team = [byte]$o.team
        $obj.Terminator = 0xFF
    }
    # Same defaults the editor applies when placing equipment (XferGui\EquipmentEdit.SetDefaultData);
    # weapons with zero durability can crash the game.
    $thing = $things[$o.type]
    if ($thing.Xfer -eq 'WeaponXfer') {
        $wx = $obj.GetType().GetMethod('GetExtraData').MakeGenericMethod([NoxShared.ObjDataXfer.WeaponXfer]).Invoke($obj, $null)
        $wx.Durability = if ($null -ne $o.durability) { [int16]$o.durability } else { [int16]$thing.Health }
        $wx.DefaultsFor($thing)
    } elseif ($thing.Xfer -eq 'ArmorXfer') {
        $errors.Add("armor '$($o.type)' needs the editor's per-item durability table; not supported yet")
    }
    [void]$map.Objects.Add($obj)
}

if ($errors.Count) { $errors | ForEach-Object { "ERROR`t$_" }; exit 1 }

# Header wall offset: stock maps store the minimum wall x/y here; the editor never updates it.
if ($map.Walls.Count) {
    $hdrField = [NoxShared.Map].GetField('Header', [Reflection.BindingFlags]'NonPublic,Instance')
    $hdr = $hdrField.GetValue($map)
    $hdr.wallOffsetX = ($map.Walls.Keys | ForEach-Object { $_.X } | Measure-Object -Minimum).Minimum
    $hdr.wallOffsetY = ($map.Walls.Keys | ForEach-Object { $_.Y } | Measure-Object -Minimum).Minimum
}

New-Item -ItemType Directory -Force $OutDir | Out-Null
$map.FileName = Join-Path $OutDir ($s.name + '.map')
$map.WriteMap()
$map.WriteNxz()
"OK`t$($map.FileName)`twalls=$($map.Walls.Count) tiles=$($map.Tiles.Count) objects=$($map.Objects.Count)"
foreach ($t in ($s.objects | ForEach-Object { $_.type } | Sort-Object -Unique)) { "XFER`t$t`t$($things[$t].Xfer)" }
