# Builds a Nox map from a JSON spec using the editor's own library (NoxShared.dll), so the
# result is written exactly the way the editor writes maps and opens cleanly in it.
# Must run in 32-bit PowerShell (NoxShared targets x86); mapgen\nox.py handles that.
#
# Spec (grid cells for walls/tiles; world pixels, 23 px per cell, for objects/waypoints/polygons):
#   name, nxz (default true), info{summary, description, author, version, date, type, minPlayers, maxPlayers},
#   ambient[r,g,b],
#   walls[{x,y,facing,material[,variation][,window]}],
#   tiles[{x,y,material[,edges[[overlayMaterial, edgeType, direction]]]}],
#   objects[{type,x,y[,team][,durability][,door][,clone{map,scr}]}],
#   waypoints[{id,x,y[,name][,links[id...]]}],
#   polygons[{name,ambient[r,g,b],minimap,points[[x,y]...]}]
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

function Read-Map($path) {
    $fs = [IO.File]::OpenRead($path)
    try { New-Object NoxShared.Map((New-Object NoxShared.NoxBinaryReader($fs, [NoxShared.CryptApi+NoxCryptFormat]::MAP))) }
    finally { $fs.Close() }
}
function AutoVariation($mat, $x, $y) {
    # Same automatic variation pattern as the editor's tile brush (MapHelper.PlaceTile/AddEdge).
    $cols = [int][NoxShared.ThingDb]::FloorTiles[$mat].numCols
    $rows = [int][NoxShared.ThingDb]::FloorTiles[$mat].numRows
    $h = [math]::Floor(($x + $y) / 2)
    ($h % $cols) + ((($y % $rows) + 1 + $cols - ($h % $cols)) % $rows) * $cols
}
$xferField = [NoxShared.Map+Object].GetField('ExtraData', [Reflection.BindingFlags]'NonPublic,Instance')

# Start from the editor's own "new map" template.
$map = Read-Map (Join-Path $repo 'MapEditor\bundled\BlankMap.map')

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
    if ($var -ge $nvar) { $var = $var % $nvar }
    $pt = New-Object Drawing.Point($w.x, $w.y)
    $wall = New-Object NoxShared.Map+Wall($pt, [NoxShared.Map+Wall+WallFacing]$w.facing, [byte]$mat, [byte]100, [byte]$var)
    if ($w.window) { $wall.Window = $true }
    $map.Walls[$pt] = $wall
}

$tileNames = [NoxShared.ThingDb]::FloorTileNames
$edgeNames = [NoxShared.ThingDb]::EdgeTileNames
foreach ($t in $s.tiles) {
    $mat = $tileNames.IndexOf($t.material)
    if ($mat -lt 0) { $errors.Add("unknown floor material '$($t.material)'"); continue }
    $x = [int]$t.x; $y = [int]$t.y
    if (($x + $y) % 2 -ne 0) { $errors.Add("tile at $x,$y is off the tile grid (x+y must be even)"); continue }
    $pt = New-Object Drawing.Point($x, $y)
    $tile = New-Object NoxShared.Map+Tile($pt, [byte]$mat, [uint16](AutoVariation $mat $x $y))
    foreach ($e in $t.edges) {
        $omat = $tileNames.IndexOf($e[0]); $etype = $edgeNames.IndexOf($e[1])
        if ($omat -lt 0 -or $etype -lt 0) { $errors.Add("unknown edge '$($e[0])'/'$($e[1])'"); continue }
        [void]$tile.EdgeTiles.Add((New-Object NoxShared.Map+Tile+EdgeTile([byte]$omat, [uint16](AutoVariation $omat $x $y),
            [NoxShared.Map+Tile+EdgeTile+Direction][byte]$e[2], [byte]$etype)))
    }
    $map.Tiles[$pt] = $tile
}

$extent = 3   # 2 is reserved for the host player (see MapInterface.GetNextObjectExtent)
function Set-Extents($obj) {
    $obj.Extent = $script:extent++
    foreach ($inv in $obj.InventoryList) { Set-Extents $inv }
}
$things = [NoxShared.ThingDb]::Things
$donors = @{}
foreach ($o in $s.objects) {
    if ($o.clone) {
        # Copy a fully configured object (e.g. a townsperson with clothes) from a stock map.
        if (-not $donors.ContainsKey($o.clone.map)) { $donors[$o.clone.map] = Read-Map $o.clone.map }
        $src = $donors[$o.clone.map].Objects | Where-Object { $_.Scr_Name -eq $o.clone.scr } | Select-Object -First 1
        if (-not $src) { $errors.Add("clone source '$($o.clone.scr)' not found in $($o.clone.map)"); continue }
        $obj = $src.Clone()
        $obj.Location = New-Object Drawing.PointF([float]$o.x, [float]$o.y)
        $obj.Scr_Name = ''                    # no script in this map references it
        Set-Extents $obj
        [void]$map.Objects.Add($obj)
        continue
    }
    if (-not $things.ContainsKey($o.type)) { $errors.Add("unknown object type '$($o.type)'"); continue }
    $obj = New-Object NoxShared.Map+Object($o.type, (New-Object Drawing.PointF([float]$o.x, [float]$o.y)))
    Set-Extents $obj
    if ($null -ne $o.team) {
        # Team is only written when the extended-fields flag is set (editor: "extra" checkbox).
        $obj.Team = [byte]$o.team
        $obj.Terminator = 0xFF
    }
    # Same defaults the editor applies when placing equipment (XferGui\EquipmentEdit.SetDefaultData);
    # weapons with zero durability can crash the game.
    $thing = $things[$o.type]
    $x = $xferField.GetValue($obj)
    if ($thing.Xfer -eq 'WeaponXfer') {
        $x.Durability = if ($null -ne $o.durability) { [int16]$o.durability } else { [int16]$thing.Health }
        $x.DefaultsFor($thing)
    } elseif ($thing.Xfer -eq 'ArmorXfer') {
        $errors.Add("armor '$($o.type)' needs the editor's per-item durability table; not supported yet")
    } elseif ($thing.Xfer -eq 'DoorXfer') {
        $x.Direction = [NoxShared.ObjDataXfer.DoorXfer+DOORS_DIR][int]$o.door
    }
    [void]$map.Objects.Add($obj)
}

# Waypoints: ids are local to the spec; connections carry flag 128, which roaming NPCs follow.
$wpById = @{}
foreach ($w in $s.waypoints) {
    $wp = New-Object NoxShared.Map+Waypoint(([string]$w.name), (New-Object Drawing.PointF([float]$w.x, [float]$w.y)), [int]$w.id)
    $wp.Flags = 1
    $wpById[[int]$w.id] = $wp
    [void]$map.Waypoints.Add($wp)
}
foreach ($w in $s.waypoints) {
    foreach ($l in $w.links) {
        if (-not $wpById.ContainsKey([int]$l)) { $errors.Add("waypoint $($w.id) links to missing $l"); continue }
        [void]$wpById[[int]$w.id].connections.Add((New-Object NoxShared.Map+Waypoint+WaypointConnection($wpById[[int]$l], [byte]128)))
    }
}

foreach ($p in $s.polygons) {
    $pts = New-Object 'System.Collections.Generic.List[System.Drawing.PointF]'
    foreach ($q in $p.points) { $pts.Add((New-Object Drawing.PointF([float]$q[0], [float]$q[1]))) }
    $col = [Drawing.Color]::FromArgb($p.ambient[0], $p.ambient[1], $p.ambient[2])
    [void]$map.Polygons.Add((New-Object NoxShared.Map+Polygon($p.name, $col, [byte]$p.minimap, $pts, '', '', $false)))
}

if ($errors.Count) { $errors | Select-Object -Unique | ForEach-Object { "ERROR`t$_" }; exit 1 }

# Header wall offset: stock maps store the minimum wall x/y here; the editor never updates it.
if ($map.Walls.Count) {
    $hdr = [NoxShared.Map].GetField('Header', [Reflection.BindingFlags]'NonPublic,Instance').GetValue($map)
    $hdr.wallOffsetX = ($map.Walls.Keys | ForEach-Object { $_.X } | Measure-Object -Minimum).Minimum
    $hdr.wallOffsetY = ($map.Walls.Keys | ForEach-Object { $_.Y } | Measure-Object -Minimum).Minimum
}

New-Item -ItemType Directory -Force $OutDir | Out-Null
$map.FileName = Join-Path $OutDir ($s.name + '.map')
$map.WriteMap()
if ($s.nxz -ne $false) { $map.WriteNxz() }   # .nxz is only used to send maps to multiplayer clients
"OK`t$($map.FileName)`twalls=$($map.Walls.Count) tiles=$($map.Tiles.Count) objects=$($map.Objects.Count) waypoints=$($map.Waypoints.Count) polygons=$($map.Polygons.Count)"
foreach ($t in ($s.objects | Where-Object { $_.type } | ForEach-Object { $_.type } | Sort-Object -Unique)) { "XFER`t$t`t$($things[$t].Xfer)" }
