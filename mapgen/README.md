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

To play or open it, copy both files to `<Nox>\maps\<Name>\`. Story maps (with scripts and text) are installed by
`py mapgen/install.py mapgen/out/<map> <Name>`, which also rebuilds `nox.csf.json`; before that a map passes the QA
gate, `py tests/qa.py <design>` (PROCESS.md section 9).

## Maps

The early test maps are below; the campaign's story maps (Thornwick, TNorth, Rimehold, RimePass, Emberhollow,
AshRoad, Deepvault, Mirefen, Greywatch, Ambermere, Starwell) are listed in `ROADMAP.md` and the overnight reports in
`review/reviews/`.

| Design | Type | What it is |
|---|---|---|
| `designs/dyscrypt.py` | Arena (Deathmatch, Elimination, King of the Realm) | One crypt room, 2-8 players |
| `designs/dysvale.py` | Solo (single player) | Phase 3 showcase village: generated buildings, furnished rooms, stream, bridges, ford, pond and dock |
| `designs/mossford.py` | Solo (single player) | Woodland river village: 8 furnished buildings, 2 bridges, square, gardens, 16 roaming/stationary townsfolk copied from Con07B |
| `designs/treeplace.py` | Solo (single player) | A sacred mana forest (16,168 tiles). A giant crystal cluster sits in a grove of standing stones and silver trees. Three themed woods (the grovelord's shack in the north, a lily pond in the west, a brook with a rope bridge in the south). A long winding path leads to a mining camp below a rock face, whose timbered mine tunnel is blocked by a cave-in |

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
| `kit/identity.py` | Map, area, building and room identities: purposes, room programs (`BUILDINGS`), room recipes (`ROOMS`, `compose`), coverage targets, the rooms sidecar (`rooms_sidecar`) |
| `kit/building.py` | `generate_building(...)`: new footprints split into rooms, interior and exterior doors, walls and floors in a learned style; hub plans, the throne room's seat, the chapel's altar axis |
| `kit/furnish.py` | `Furnisher` / `furnish_room(spec, room, kind)`: rooms composed from their recipe (anchors, lined walls, groups, caps, counters, thrones, showpieces once) |
| `kit/originality.py` | Compares a furnished room against all ~3,100 stock rooms; `furnish_original` re-rolls near copies |
| `kit/water.py` | `Waterworks`: streams, ponds, lava flows, bridges, fords, docks square to the shore, rope and lava bridges, shore walls |
| `kit/layout.py` | `Land`: areas and links, the land grown round what is placed, roads, the square, thickets, sections, door paths |
| `kit/vegetation.py` | `Planter`: tree lines, groves, undergrowth and flowers in single-type patches, a town's planting, rock piles, forest-floor scenes |
| `kit/village.py` | `Village`: door scenes, gardens, the square, signs, ground bits |
| `kit/yards.py` | Gated yards with a purpose: graveyard, quarry, orchard, park, field, monument, jail |
| `kit/mine.py` | `MineEntrance`: a rock face along a yard with a timbered tunnel blocked by a cave-in |
| `kit/biome.py` | Cave, ice, lava and swamp palettes; `Dresser` (biome structures and their garrisons) |
| `kit/story.py` | `StoryMap`: the steps every story map shares (buildings, people, tours, beats, journeys, gates, exits, shops, keepers); `Curtain` (a castle's walls) |
| `kit/quests.py` | `QuestBook` and actions `A`: dialogue, quest stages, events, the map's text (run by `kit/behaviours/quests.go`) |
| `kit/npcs.py` | `Population` (creatures, spaced) and `Behaviours` (tours, patrols, journeys, sentries, packs; `kit/behaviours/behaviours.go`) |
| `kit/walkways.py` | `Ground` and `Router`: where a body can walk, routes along roads, doorways square-on, each stop's facing |
| `kit/camps.py` | Story places: bandit camps in zones, urchin camps, camp sites, wreck, den, cache, ruined tower, stone ring, training ground, signposts |
| `kit/posts.py` | `camp_posts`: where a camp's people stand |
| `kit/scenes.py` | The outdoor scene catalogue (`CATALOGUE`, `ROLE_SCENES`) |
| `kit/dressing.py` | `Exterior`: the outdoor ground dressed with whole scenes from the catalogue |
| `kit/spacing.py` | Westwood's closest gaps between outdoor pieces; wall-line clearance |
| `kit/loot.py` | Container loot in Westwood's shares, filled at build time |

The process (which rule each module carries out) is `PROCESS.md`; the recipe for a story map is
`skills/nox-story-map/SKILL.md`.

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
- Westwood kept map names to 8 characters; OpenNox loads 9 (TreePlace, verified in the game's server) and its map
  list cuts longer ones, so `Spec` allows at most 9.
- A floor tile at (x, y) is drawn centred on grid corner (x+1, y+1); paint terrain by that centre.
- Doors: a one-cell gap in a wall; in a `\` wall the door goes on the gap's bottom-right corner
  facing South, in a `/` wall on its bottom-left corner facing West (64/67 of Con07B's doors).
- Water is fenced by InvisibleWallSet walls on the shoreline cells, as in stock maps.
- Single-player maps: type Solo (0x1), one PlayerStart, no teams/crowns/flags, no .nxz.
