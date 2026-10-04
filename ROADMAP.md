# Map-making skill roadmap

Goal: a repeatable process that produces professional-quality Nox maps in one shot, learned from
Westwood's maps. Generated structures must be original (never copy-pasted stock layouts).

| Phase | Status | Where |
|---|---|---|
| 1. Reference corpus (all 157 stock maps, database, renders) | done | `corpus/` |
| 2. Rulebook mined from the corpus | done | `rules/RULEBOOK.md`, `rules/out/*.json` |
| 3. Kit: original buildings, furnished rooms, water features | done | `mapgen/kit/` |
| 4. Automatic checks (validator), calibrated on Westwood's maps | done | `validate/` |
| 5. Visual review against Westwood references (sheets, design measurements, rubric) | done | `review/` |
| Generator v2: layout, vegetation, village and water planners (fixes review criteria 1–5) | done | `mapgen/kit/layout.py`, `vegetation.py`, `village.py` |
| Generator v3: identity first, centre outwards (PROCESS.md) | done | `mapgen/kit/identity.py`, `PROCESS.md` |
| TreePlace: a new map from scratch with the refined process (sections, a mine entrance, thickets) | v0.2 (interiors), awaiting playtest | `mapgen/designs/treeplace.py`, `mapgen/kit/mine.py` |
| 6. Package as a skill | next | |
| 7. Benchmark briefs and refinement loop | | |

## Playtest feedback log

### TreePlace v0.1 (2026-10-03)

"Mostly very good." The outdoors stood; four camp rooms and the indoor lights did not. Fixed in v0.2, and
written into the furnisher, the checker and PROCESS.md:

| Finding | Fix |
|---|---|
| Kitchen: open space everywhere, everything clustered around the chimney, meat on the floor, no clear purpose | Loose food is gone: Nox draws items at floor level, so food on a table reads as dropped, and only 2 of Westwood's 520 food items lie at a table. Kitchens set a table that carries its food (`RoundTableWithFood`) or a work table with stools, and stock provisions along the other walls (`stock_walls`). The checker flags food lying by a table, and furniture that spans under 35% of a room's length (the v0.1 kitchen: 29%) |
| Mess hall: chairs pulled up to the ends of the tables; two water barrels and a stack of barrels just sitting there | Seats go along a table's long sides (Westwood: 75%; never only at the ends). Mess halls lay long tables in rows with a matching bench along each side (`table_rows`), with a hearth and a crockery shelf, and no barrels. The checker flags long tables seated only at their ends, and barrels in a dining hall |
| Bunkhouse: two cots and two beds in random places, a table with no chairs | Bunk rooms lay one bed kind in a straight row along a back wall (`bed_row`), as all of Westwood's rooms with 3+ beds do. Each bed gets a chest at its foot, a rug lies along the row, and gear shelves stand across the room. A table always gets its seats, or it is left out. The checker flags mixed bed kinds, scattered beds, and tables without seats where people sit to eat |
| Storeroom: almost empty; a bookshelf, a crate, an explosive barrel and a barrel scattered at random | Storerooms stock their walls in tidy groups (stocked log shelves, crates, barrels, sacks), with the middle clear. No room recipe allows black-powder barrels, and storerooms take no bookcases. The checker flags both as outside the room's identity |
| Torches indoors do not look attached to the wall, and an open flame that size indoors is unrealistic | Houses (log, stucco and stone walls) are lit with candelabras and the hearth; torches stay outdoors, in dungeons and in mines. Westwood's log cabins mostly use candelabras too (15 of 30 lights). The checker flags open torches inside a house |

Also: log shelves are numbered by wall in a third way, measured on Westwood's maps (3 NW, 4 NE, 2 SE, 1 SW).
The checker counts stocked shelves and apple crates as supplies, so a stocked storeroom no longer reads as a
library and a kitchen no longer reads as a shop.

### DysVale v0.6 (2026-10-03)

Folded into the process. As asked, no DysVale v0.7: the fixes were proven on a new map, TreePlace v0.1
(`review/reviews/TreePlace-v0.1-2026-10-03.md`).

| Finding | Fix |
|---|---|
| A chest stood perpendicular to its wall | Westwood numbers chests, beds and nightstands 1-4 by wall (SE, SW, NE, NW), and bookcases and desks the other way round (NW, NE, SE, SW). The scheme is learned from Westwood's placements, and the furnisher picks the number for the wall (`Furnisher.along_variant`), now also for a room's preferred types. Chests, bookcases, desks and shelves lie along their wall; beds stand perpendicular. The checker flags pieces lying across their wall (allowing for corners) |
| The candelabra beside the chest belonged in the other corner | Lights score spots by distance from other lights (weighted most) and from pieces, preferring free corners, at least 3 units apart. Pieces centre on a wall or between another piece and a wall |
| Stumps clustered in one spot, with none elsewhere | Props spread out from where they belong with a falloff and spacing (`vegetation.scatter`). The checker flags 4 or more of a kind within 330 px when that is 85% or more of all of them |
| Door halves slightly out of line | Both halves sit at exact multiples of 23 px, 46 px apart on each axis, as in Westwood. Door kinds are chosen per wall direction (`doors.json` `by_line`): BandedPlankDoor hangs as a pair only in '/' walls. The checker flags pairs whose halves do not line up, and pairs in a wall direction Westwood never uses |
| The bridge was too wide for the stream and sat on a bend | Westwood's stream bridges are narrow rope-bridge kits. Crossings are planned with the road and get the kit for their axis. The stream is held straight and calm through the crossing (`stream(calm=)`). The checker flags bridges that cross at a slant, sit on a bend, or have decks wider than 2 tiles |

Also found while building TreePlace, and fixed:
- forest walls missing shapes (DecidiousWall has no corner 8; DecidiousWallRed and AspenSparse have no
  T-junctions) now fall back to the material Westwood joins them to;
- door paths no longer put packed dirt against marble (they use Westwood's buffer floor);
- a desk could stand in a wall cell (cells are diamonds in uv). This was the RoomTest finding below;
- gardens were blocked by their own building's clearance margin;
- the torches flanking a door were placed from the square under the door object, which can be outside the
  wall (`layout.door_frame`);
- builds were not reproducible, because region borders used Python's per-run string `hash()`.

### DysVale v0.1 (2026-10-03)

Fixed in phase 3:

- **Mismatched dock planks.** Pieces were spaced on a pure diagonal; Westwood's steps have small sideways offsets. Kits now use the exact measured pixel steps (`kit/water.py` KIT_STEPS).
- **Sight gap at a corner beside a door.** Wall shapes were computed without the door opening, turning the corner into a straight piece. Westwood shapes jamb pieces as if the opening were wall (29.8% of jambs match only that way, 0.7% the other way); `nox.Spec` now does the same.
- **Gap beside a door frame.** Half-door types were placed singly in 1-cell openings. They are double doors: two halves hinged at the ends of a 2-cell opening (`rules/doors.py`). `Spec.door` builds pairs and falls back to the matching single door where the wall has no room.
- **Cluttered tavern.** There were two causes:
  - The building was sized from the style's typical house, so the tavern room was about 16 tiles; Westwood's taverns are 62-266.
  - The furnisher kept at least 60% of a full inventory.

  Buildings now grow to fit their room program. The largest room takes the entrance and the program's first role. Furniture scales with room area, and a hard cap holds each room at its kind's Westwood density (essentials and lights exempt).

Recorded for later phases (design level):

1. **No flow or coherent design.** Buildings sit at random spots with no roads or paths connecting them; Westwood towns are compact, with streets, a square, and buildings facing the streets. This needs a layout planner: a district/road graph first, buildings placed along roads with entrances facing them, then paths to every door, bridges where roads cross water, and organic outer boundaries instead of a geometric diamond. *(Generator v2, before or alongside phase 5.)*
2. **Trees and shrubs look random.** Uniform scatter instead of Westwood's structure: trees line edges and paths, groves and clearings, single-type clumps of flowers and mushrooms, undergrowth hugging walls and trees (`rules/out/decoration.json` has the measurements). This needs a vegetation planner driven by those rules. *(Generator v2.)*

Checks phase 4 must include, from this playtest (all implemented in `validate/`, each proven by a planted defect in `validate/selftest.py`):

- wall pieces beside door openings shaped as if the opening were wall
- double-door types only in 2-cell openings as matched pairs; single doors in 1-cell openings
- kit pieces at Westwood's exact step offsets
- furniture density per room within the kind's Westwood range; rooms within the kind's size range
- line-of-sight closure: no see-through gaps in building and boundary walls

### Mossford v0.1 (2026-10-03)

| Problem | Status |
|---|---|
| Black walls (invalid wall pieces) | Fixed: valid-piece table |
| See-through hole in the boundary | Rule recorded: invisible walls never on the boundary. The water kit follows it; Mossford itself still needs a rebuild |
| Abrupt bridges | Fixed in the water kit (Con05A-style decks, narrow streams). Mossford still needs a rebuild |

### DysVale v0.5 (2026-10-03)

The tavern's main room and bar were a big improvement. Fixed in v0.6:

| Finding | Fix |
|---|---|
| Bedroom behind the bar: chests and rugs not centred | Rooms are composed as a whole (`Furnisher.compose`, recipes in `kit/identity.py`). Each anchor piece gets its own wall stretch, the back walls the camera sees first (Westwood stands 74-87% of wall pieces there), centred where Westwood centres it. A rug is laid before the chest or hearth, or centred in the room |
| The kitchen lacked any purpose | The kitchen identity follows Westwood's kitchens: a lit stone oven centred on a back wall with the cooking cauldron beside it, one work table in the middle with food set out, supplies (barrels, an apple crate, sacks) in a row from a corner. The smithy became a real forge (glowing coals, bellows, the anvil before the fire, water and tool barrels, weapon racks) |
| The bridge ended against the forest wall | Crossings are planned with the roads (`Land.plan_crossing`): the road is straightened through the crossing, the stream is laid to flow across it at a right angle, and the deck runs in the road's direction and lands on the road at both ends. The checker flags bridges whose ends do not open onto ground |
| Fourth room: the chest in the south corner behind a table and a lamp; everything bunched in one corner | Every anchor keeps the space in front of it clear (nothing blocking may stand there), the table set takes the open middle of the room, and pieces spread across the walls. The checker flags pieces standing in front of a chest, hearth or stove, chairs with no table, and furniture bunched into one part of a room. On v0.5 it finds exactly the chair before the chest and the bridge |

Also fixed:
- door paths blend into the doorway;
- floor tiles straddling building walls no longer count as paths;
- buildings facing the square are rejected before they are written if they cannot open onto it.

### DysVale v0.4 (2026-10-03)

The theme of this playtest: every piece must make sense in relation to what is around it. Fixed in v0.5:

| Finding | Fix |
|---|---|
| A dock across a puddle | The mill stands on a lake (radius 11 tiles) at the end of its road. The dock starts where the road meets the shore and needs open water past its tip (`Waterworks.dock(beyond=, near=)`). Reeds grow only in the shallows. The checker flags docks with no open water beyond them |
| A path led to the side of a building with no door; the door had no path | Door paths start from the actual doorstep and are routed around buildings to the streets (`Land.connect_door`). Streets keep clear of walls, and roads that would run into a building are cut back. The checker flags short paths that end at a wall with no door. Root cause: the land-square helpers were half a tile out of register with the real tiles; fixed |
| Random benches and torches around the square | The square is a composed set piece: the well in the centre, 8 benches in 4 pairs facing it, 4 torch poles on the diagonals. Street lights keep a steady rhythm along each street, always on the same side |
| The inn's only door faced away from the square | Buildings that face the square get their door on the square side. The footprint is mirrored when needed so the main room touches that side, and the design checks the door faces the square |
| Two candelabras side by side | Each light goes to the wall spot farthest from the room's other lights, at least 50 px apart. The checker flags lights standing side by side |
| The bar did not meet the walls; the flap read as a window; the tavern felt empty | Bar runs end 1 unit from the wall line (Westwood: 1.0-1.3), with plain pieces at the ends and the flap mid-run with counter on both sides. Kegs stand behind the bar. The tavern identity follows Westwood's proportions: 3-8 tables, 6-24 stools and chairs, 3-6 barrels, a likely hearth, benches and wall decorations. The checker flags bars that stop short of a wall |

### DysVale v0.3 (2026-10-03)

The layout, trees and shrubs improved a lot. Fixed in generator v3:

| Finding | Fix |
|---|---|
| The square was off-centre, and a building stood on one of its tiles | The square is placed first. Public buildings face it across a clear margin, and roads stop at its edge |
| Paths near the river were hard to read because of stacked blends | Spacing comes first: the stream's band is reserved before anything is built, and the road stays 2.5 squares clear except at the bridge. Grass patches keep 3 squares from every transition. New review measure: road tiles crowding water (Westwood towns about 0.4%; v0.3 had 6.9%, v0.4 has 1.4%) |
| Exterior objects felt random | Outdoor props are scenes with a reason, tied to a building's role: deliveries at the inn, a woodpile at the woodcutter's, a water barrel at the smithy, grain sacks at the mill |
| Interiors were incoherent (a back room with four table sets) | Room identities list what each kind must, may and must never contain. The checker flags furniture outside a room's identity; on v0.3 it finds the barrels in bedrooms and the bookcases in the tavern |
| Swamp densities were averaged with towns | Westwood's maps are classified into 8 environment types (`rules/environments.py`); the checker and the review compare only like with like |
| The map needs an identity step | `MapIdentity` comes first (PROCESS.md, step 1). Generation runs from the centre outwards, and the land grows around what was placed (user direction) |

## Found by the checker (to fix in later phases)

- **Mossford v0.1** has 49 errors (black walls, 2 boundary holes, plank floor straight onto dirt at house doorsteps). It still needs a rebuild with the kit.
- **Furnisher:** a desk was placed inside a wall in RoomTest. Fixed: no piece may stand in a wall cell (`Room.fits`).
- **RoomTest** (a sheet of standalone rooms) reports its outer doors as standing in the void, because its rooms
  float in darkness with doors that lead nowhere. This happens on master too (21 errors). The test map should
  give each room a doorstep.
- **TreePlace v0.1:** no creatures; 16.9 wall pieces per 100 floor tiles (Westwood's forests: 21-52).
- **Style warnings on DysVale:** no creatures; few wall pieces per floor tile (an open layout); the tavern is small for its kind (55 tiles against Westwood's 166–269). These are for the layout planner (generator v2).

## Visual review findings

- **DysVale v0.2** (`review/reviews/DysVale-2026-10-03.md`) scores 1 on silhouette, flow and vegetation, and 2 on settlement, water and every-screen variety; interiors score 3. Generator v2 has to deliver:
  - an organic walkable shape cut out of forest
  - a road graph with buildings packed along it around a focal point
  - deep tree lines, groves and single-type plant patches
  - dressed water with bridges where roads cross

  Each is measured in `review/design.py`.

- **DysVale v0.3** (generator v2, `review/reviews/DysVale-v0.3-2026-10-03.md`) scores 4 on silhouette, flow and vegetation and 3 on settlement, water, every-screen variety and interiors. The checker finds no errors and every design measurement is within Westwood's range. Open items:
  - creatures and townsfolk (none yet)
  - denser villages
  - dressed stream banks
  - corridor width variety
  - the furnisher sometimes places furniture on a wall cell (fixed for TreePlace)

- **TreePlace v0.1** (generator v3 with sections and a mine entrance, `review/reviews/TreePlace-v0.1-2026-10-03.md`)
  scores 4 on every criterion and 5 on identity. The checker finds no errors. Design measurements are within
  Westwood's forest range; paths and plant clumps are above it (more structured).
