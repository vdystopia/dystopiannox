# Towns: walls, islands, yards and planting

What Westwood's 16 campaign town maps (rules/environments.py type "town"; the quest maps G_Forest, G_ForesD and G_Mines
no longer count) are made of beyond their
buildings, and how the kit builds the same. Measured by `py rules/town_walls.py` (writes `rules/out/town_walls.json`;
`py rules/town_walls.py <map> ...` gives the same figures for our maps).

## Where a town's walls stand

Westwood's towns carry 26-49 wall pieces per 100 floor tiles (typical 37). Few of them are the houses'. Every wall
piece sorted by what it bounds, per 100 floor tiles (weighted mean):

| Class | Westwood | What it is |
|---|---|---|
| edge | 10.1 | the map's outer boundary: the forest wall, cliffs |
| island | 12.9 | the rim of a block of forest or rock standing in the land, with no way in |
| building | 5.5 | walls of rooms with an indoor floor |
| yard | 6.5 | walls of an outdoor plot behind a gate: a garden, a graveyard, a quarry |
| partition | 1.8 | free-standing walls with land on both sides: a fence or hedge that closes nothing |

A town is not a clearing with houses in it. It is a web of corridors through the forest that loop round blocks of
forest, with bays off them and fenced plots in them.

## Islands

- Westwood's campaign towns hold about 26 islands each (median; 3.67 per 1000 floor tiles, weighted). Their rims
  run 8-36 wall pieces (median 14). (With the three quest maps: 7.4 per 1000 and a rim of 8: the quest
  forests are strewn with small clumps.)
- They stand near the edge (median 5 cells from an edge wall) and about 10 cells apart.
- Their walls are cliff (CaveWall2, Dirt), forest (DecidiousWallGreen, Coni-Wall1), a closed fence (Log,
  Cobblestone, DilapidatedShort) or masonry.
- The large ones are the forest enclosed by corridors that loop. The small ones are clumps standing in a meadow.

The kit (mapgen/designs/townlab.py):
- a glade between each pair of roads, reached from both by forest paths (`Land.link(..., road=False)`), so every
  pair of roads and its glade loop round a block of forest (`Land.carve` keeps holes over 40 squares void);
- clumps of forest in the open (`Land.thickets`, 0.9-1.8 squares across, 2 squares clear round each).

Paths through the forest need 11 uv or more: at 9 uv the wavy edges of a path pinched it shut, and creatures were
left behind the pinch.

## Yards

Westwood fences plots with a purpose and a gate (127 gated outdoor plots in the town maps). The kit's
`kit/yards.py` builds them:

| Yard | Fence and gate | Size (tiles) | What it holds |
|---|---|---|---|
| graveyard | IronFence, Gate (or Rock with a JailDoor) | 63-110 dirt | tombstones about 3 squares apart (Tombstone1 the most), torch poles, coloured lights, bones |
| orchard | Log (and the house wall), BarredGate | 22-28 grass | Plant5, Plant4, flowers, one tree, an apple |
| flower garden | DilapidatedShort and the house wall, Gate, a door from the house | 60 grass | blue, purple and white flowers, Bush6 |
| park | forest wall, DilapidatedShort, IronFence, Gate | 92-112 grass and cobble | eight benches, plants, a tree |
| quarry | CaveWall2 cliff, IronFenceGate | 88-110 dirt | pebbles 17-24, medium rocks 6-9, huge rocks 4-6, short pillars 3-4, barren plants |
| jail | Cobblestone, JailDoor | 6 cobble a cell, two cells | Cot2, Straw2 |
| trader's stall | Cobblestone, JailDoor and ThickWoodenDoor | 36 cobble | weapon racks along the walls, a table, the trader |
| monument | Cobblestone, WoodAndSteelHalfDoor | 76 cobble and tile | monuments, statues (Statue2a), torch poles |
| ogre pen | Dirt cliff, OgreCageDoor | 48-129 dirt | ogre straw, corpses, urchin chests |
| mine compound | Log palisade, WoodenDoor | 20-286 dirt | mining tools, barrels, crates, carts, torch poles |

The kit builds the graveyard (graves on dug earth in rows, a gravedigger's corner: PROCESS.md section 2), orchard,
park, quarry, field (a Log fence round a crop in rows, kept inside the fence as drawn), monument and jail. A
yard is planned before the land is carved (`yards.plan`, `yards.plan_any`: its plot and two squares round it are
taken, so the land grows round it and the forest's trees stay off its fence) and built after the land's walls are
laid (`yards.build`: floor, fence, gate facing the town, a clear lane from the gate, the contents).

Yards are declared in the map's rooms sidecar with `yard: true` (`identity.rooms_sidecar(..., yards=)`). The checker
(`checks.indoor_rooms`) and the room score hold them to no indoor room's rules: a graveyard is not a crypt with stray
tombstones.

## Planting

Westwood's towns per 100 floor tiles: 1.7 trees (p75 2.2), 7.1 plants, 3.2 flowers and mushrooms, 2 rocks.

- Three quarters of the trees stand within 3 cells of the forest wall. The forest wall itself is drawn as trees, so
  tree objects are accents, not the forest.
- Half the plants are at the wall's foot and a quarter out in the open.
- Most flowers and mushrooms are 1.5-3 cells out from the wall. Rocks sit at the wall's foot.

A forest map's planting gave the town lab 11.3 trees per 100 tiles (28 decorations per 100 tiles against Westwood's
7.9-23.7). `vegetation.TOWN_PLANTING` (`Planter.plant_all(profile=...)`) plants a town as Westwood does: the town
lab now carries 20 decorations per 100 tiles.

## The town lab against Westwood

|  | Westwood's towns | Town lab before | Town lab now |
|---|---|---|---|
| walls per 100 tiles | 25.9-49.2 (typical 35) | 20.9 | 26.4 |
| decorations per 100 tiles | 7.9-26.0 (typical 20) | 24.3 | 20.4 |
| islands | about 26 | 0 | 4 forest blocks, 26 clumps |
| yards | about 9 a map | 0 | 9 |
