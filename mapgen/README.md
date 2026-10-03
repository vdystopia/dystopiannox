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

## Maps

| Design | Type | What it is |
|---|---|---|
| `designs/dyscrypt.py` | Arena (Deathmatch, Elimination, King of the Realm) | One crypt room, 2-8 players |
| `designs/dysvale.py` | Solo (single player) | Phase 3 showcase village: generated buildings, furnished rooms, stream, bridges, ford, pond and dock |
| `designs/mossford.py` | Solo (single player) | Woodland river village: 8 furnished buildings, 2 bridges, square, gardens, 16 roaming/stationary townsfolk copied from Con07B |

Single-player maps get no `.nxz` (only used to send maps to multiplayer clients). To test one in
game: start a Solo game, press F1, type `racoiaws` (enables cheats), then `load <mapname>`.

## What the builder supports

Walls of any shape (facing derived from neighbours), windows, floor tiles with soft edge blending
(rules learned from all stock maps), doors placed in wall gaps, objects, objects copied from a stock
map by script name (e.g. configured townsfolk; their script names are cleared), waypoints with
roaming links (flag 128), and room polygons.

## Kit (phase 3): original structures, not copies

Generators in `mapgen/kit/` build new structures from rules learned from Westwood's maps
(`rules/out/*.json`); no stock building or room layout is ever copied.

| Module | What it generates |
|---|---|
| `kit/model.py` | Shared Building / Room / Door records |
| `kit/building.py` | `generate_building(spec, rng, origin_uv, max_size_uv, style, program=...)`: new footprints (rect, L, T, U, Z, courtyard) split into rooms, interior and exterior doors, walls and floors in one of 20 learned styles (log cabin, stucco house, Galava town house, ...) |
| `kit/furnish.py` | `furnish_room(spec, room, kind)`: furniture, sets and lighting for 12 learned room kinds (tavern, bedroom, shop, kitchen, smithy, library, ...), wall pieces turned to face away from their wall, doorways and walkways kept clear |
| `kit/originality.py` | Compares a furnished room against all ~3,100 stock rooms; `furnish_original` re-rolls near copies |
| `kit/water.py` | `Waterworks`: streams, ponds, lava flows, plank bridges, fords, docks, rope and lava bridges, shore walls and water dressing |

Demos: `designs/test_buildings.py`, `designs/test_rooms.py`, `designs/test_water.py`, and
`designs/dysvale.py`, a village combining all of them.

## Rules the generator follows (verified against stock maps and the game engine)

- Walls and floor tiles occupy cells where `x + y` is even. Rooms are rectangles in rotated
  coordinates `u = x + y`, `v = x - y`; on screen they are diamonds.
- Wall facing: 0 = `/`, 1 = `\`, corners 7-10 (see `nox.py`). Floor fills a room offset by one tile.
- Object extents (IDs) start at 3; 2 is reserved for the host player.
- Weapons get Westwood's multiplayer durability values; wands get full charges.
- An object's team is only saved when its extended-fields flag is set; the builder does this.
- Arena maps (`type=0x34`) carry three Crowns (teams 0, 1, 2), like every stock arena map.
- Map names are at most 8 characters.
- A floor tile at (x, y) is drawn centred on grid corner (x+1, y+1); paint terrain by that centre.
- Doors: a one-cell gap in a wall; in a `\` wall the door goes on the gap's bottom-right corner
  facing South, in a `/` wall on its bottom-left corner facing West (64/67 of Con07B's doors).
- Water is fenced by InvisibleWallSet walls on the shoreline cells, as in stock maps.
- Single-player maps: type Solo (0x1), one PlayerStart, no teams/crowns/flags, no .nxz.
