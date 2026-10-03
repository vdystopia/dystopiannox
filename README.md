# MapEditor

## Building and testing (dystopiannox fork)

No Visual Studio or Windows SDK needed; Windows 10/11 has everything except the C# compiler,
which `build.ps1` downloads (Roslyn from nuget.org, pinned version and SHA-256).

```
powershell -ExecutionPolicy Bypass -File build.ps1
```

Output: `MapEditor\bin\Release\` (`MapEditor.exe`, `NoxShared.dll`). Targets .NET Framework 4.x.
Korean/Dutch/en-GB dialog translations are skipped (`/p:SkipSatelliteResources=true`) because
they need `al.exe` from the Windows SDK.

Round-trip test: loads stock Nox maps with the built library, saves them, and checks with an
independent parser that no walls, floor tiles, objects or waypoints were lost or changed.
Needs Python 3 and `pip install pycryptodome`; finds Nox via the registry.

```
py tests\roundtrip.py          # 8 representative maps
py tests\roundtrip.py --all    # every map in Nox\maps
```

Run it after every change to map reading or writing code.

## Nox Map Editor 1.2 by KITTY

Improved map compression, nearly identical to original sizes!
 - (many thanks to panic and AngryKiRC for their help)

Added Buff Editor Window:
 - New GUI for adding Enchants to any entity
 - Change Spell Level, Duration, and Shield HP
 - CAUTION: Old map editors will fail to read map

Object List Window:
 - Added search filter (Enter to search, Ctrl+Enter to clear)
 - Added object count
 - Added Delete Object
 - Fixed Apply Changes not correctly updating when sorting
 - Fixed Scripts/Enchants getting wiped after Editing Object

Scripting Window:
 - Added more details in the Wrong Syntax error messages
 - Functions treenode now defaults to expanded
 - Window can now remain open while map editing
 - Fixed parser not reading Gvars and vars above a single digit
 - Fixed parser incorrectly parsing brackets
 - Fixed parser not reading every jump label
 - Fixed Groups not being recognized by their index

Revised Voice set on NPC/Maiden Edit:
 - Added "_Guard1", "_Guard2", and an empty option
 - Got rid of broken ones
 - Fixed unrecognized Voice error

Trigger Edit:
 - Added MonsterGenerator flag (Quest)
 - Updated GUI

Sentry Edit:
 - Added preview for angle and speed
 - Fixed SentryGlobe direction not applying to map
 - Updated GUI

Polygon Edit:
 - Added Minimap Group to Polygon label
 - Added all used Polygon colors to Custom Colors
 - Fixed Polygons not accepting decimals
 - Fixed Polygons Minimap Group range

Added Wall Property Picker

Added Clone to Inventory Edit

Added Waypoints to Statusbar on hover

Other:
 - Added option for Save NXZ Only
 - Added icons for Grid Snap
 - Added icon for Randomize
 - Added Waypoint total to List
 - Added Script Wiki link

More Bug Fixes:
 - Fixed Bomber Spells
 - Fixed ColorLight Editor not expanding
 - Fixed Object box switching tabs when numbers 1-4 pressed
 - Fixed Recent Items removing from top instead of bottom
 - Fixed Undo not reversing Oriented Rectangle
 - Fixed Undo wiping NPC properties
 - Fixed Existing Team setting not functioning
 - Fixed Weapons not accepting 0 charges
 - Fixed Tile Picker not selecting variation
 - Fixed Tile Brush not applying Manual Variation
 - Fixed tabs not scaling properly on non-English Windows
 - Fixed Groups occasionally saving incorrect index
 - Fixed Grid Snap settings not saving/loading
 - Fixed "Buffer cannot be null" error when saving
 - Many other small bug fixes and code cleanup


## Nox Map Editor X by Protokol

Waypoints:
 - Added Connection Flag
 - Select/Enable/Delete multiple Waypoints
 - Added Copy Waypoints Right-click menu
 - Fixed editor not drawing all Connections

Added Waypoint List to Map menu
 - Can search/sort by any column

Added Waypoint Properties dialog
 - Can view/delete all Connections
 - Can edit Coordinates

Added Object search filter
 - Type in Object box, then hit Space bar

Added Randomize button based on Category
 - Right click to reshuffle

Other:
 - Disabled Objects are shaded gray
 - Inventory list shows count of items
 - Added graphic to About
