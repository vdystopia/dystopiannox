# Map generator

Builds Nox maps from Python designs. Maps are written by the editor's own library
(`NoxShared.dll`), so they open in the editor exactly like hand-made maps.

## Files

| File | Purpose |
|---|---|
| `nox.py` | Design helpers: `Spec`, `room()` (walled room with floor), `obj()` (place an object), `build()` |
| `build_map.ps1` | Turns a JSON spec into `.map` + `.nxz`; validates every material and object name against the game's `thing.bin` |
| `designs/*.py` | One script per map. Run it to build that map into `mapgen/out/` |
| `screenshot_editor.ps1` | Opens a map in the built editor and saves a screenshot |
| `editor_qa.ps1` | With the editor open: screenshots Map Info, Mini Map, and the Large Map view centred on the map |

## Build a map

```
powershell -ExecutionPolicy Bypass -File build.ps1      # once, builds NoxShared.dll
py mapgen\designs\dyscrypt.py                            # writes mapgen\out\DysCrypt.map/.nxz
```

To play or open it, copy both files to `<Nox>\maps\<Name>\`.

## Rules the generator follows (verified against stock maps and the game engine)

- Walls and floor tiles occupy cells where `x + y` is even. Rooms are rectangles in rotated
  coordinates `u = x + y`, `v = x - y`; on screen they are diamonds.
- Wall facing: 0 = `/`, 1 = `\`, corners 7-10 (see `nox.py`). Floor fills a room offset by one tile.
- Object extents (IDs) start at 3; 2 is reserved for the host player.
- Weapons get Westwood's multiplayer durability values; wands get full charges.
- An object's team is only saved when its extended-fields flag is set; the builder does this.
- Arena maps (`type=0x34`) carry three Crowns (teams 0, 1, 2), like every stock arena map.
- Map names are at most 8 characters.
