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
| TreePlace: a new map from scratch with the refined process (sections, a mine entrance, thickets) | retired 2026-10-04 (with DysVale): new maps with the new process instead | `mapgen/designs/treeplace.py`, `mapgen/kit/mine.py` |
| Room lab: every room kind at three sizes, scored (`roomlab.py`, `review/roomscore.py`) | 21 kinds at Westwood's true sizes (two lab pages): 62 of 63 rooms pass in each of 3 seeds (186 of 189) | `mapgen/designs/roomlab.py` |
| Building lab: every building role at a scale, scored (`buildinglab.py`, `review/buildingscore.py`) | 16 roles (a manor of 8 rooms, 3 culture buildings): 44 of 48 pass over 3 seeds at the kit's scale (1.25); 13 of 14 at 1.6 | `mapgen/designs/buildinglab.py` |
| Biomes: caves, snow and ice, lava, measured on Westwood's maps and built by a palette kit | v0.2 maps installed with a structure each: Darkdelve's ogre keep, Frostfang's dark temple, Emberdeep's demon forge | `rules/BIOMES.md`, `mapgen/kit/biome.py` |
| Town lab: the village pipeline at the bigger scale, a market town of 13 buildings round a square (`townlab.py`) | 13 of 13 buildings; outskirts with forest loops and nine yards; checker 0 errors, 0 warnings; 29 of 30 rooms pass | `mapgen/designs/townlab.py` |
| Cultures: how Westwood furnishes ogre lairs, the Land of the Dead and Dun Mir, room by room | ogre, Land of the Dead and Dun Mir room recipes; 3 culture buildings | `rules/CULTURES.md`, `rules/cultures.py` |
| NPCs: Westwood's placement and movement measured; behaviour sets scripted in Go for OpenNox | NpcLab test map installed; Darkdelve's bats skittish, Frostfang's wolves in packs | `rules/NPCS.md`, `mapgen/kit/npcs.py`, `mapgen/kit/behaviours/` |
| Weapons: how each weapon fires its projectile (thing.bin USE lines, OpenNox's handlers); a fireball staff that throws harpoons | Harpoon test map installed | `rules/WEAPONS.md`, `mapgen/kit/behaviours/weapons.go` |
| Towns: where a town's walls stand (edge, islands, buildings, yards); yards with a purpose; a town's planting | 7 yard kinds built (graveyard, quarry, orchard, park, field, monument, jail) | `rules/TOWNS.md`, `rules/town_walls.py`, `mapgen/kit/yards.py` |
| Story maps: quests, dialogue (the map's own text in `nox.csf.json`), loot, shops, purposeful NPCs, gates and exits | Thornwick (chapter one) and Rimehold (chapter two) with TNorth and RimePass between and after; each 0 errors, 0 warnings, loaded in the server with every story object found | `mapgen/kit/quests.py`, `kit/story.py`, `kit/camps.py`, `mapgen/strings.py`, `PROCESS.md` "Story" |
| Voiced dialogue: every line said in a dialogue window spoken by a local TTS voice cast per NPC, in Westwood's wave format, wired through the string table (2026-10-08, VO-1) | pipeline built into `Spec.build`, install and the QA gate; offline tests pass (`tests/voice_test.py`); the installed Thornwick's 54 spoken lines cast to 22 speakers (58 once rebuilt: its 4 refusals are now told). Waiting on this PC: `py mapgen/voice.py fetch` (Kokoro v1.0, kokoro-onnx 0.4.9), a Thornwick rebuild through the QA gate, install, and a listen in game | `mapgen/voice.py`, PROCESS.md "Voices" |
| Transporters: lifts, stairs, portals and scripted passages, measured on Westwood's maps and laid by one call (2026-10-08, TR-1) | `kit/transport.py` (one API for the four kinds; links by extent, disabled-at-start, arrival beside the return pad), the checker's `transport.*` rules with planted cases, reachability through transporters; TestTrans installed (a lift to a cellar, a portal to an island, castle stairs to an upper floor, a passage to a crypt): QA gate PASS, server self-check 8 of 8, every leg proved in the client | `rules/TRANSPORTERS.md`, `skills/nox-transporters/SKILL.md`, `mapgen/kit/transport.py` |
| 6. Package as a skill | first draft, being tested by a fresh agent building chapter three | `skills/nox-story-map/SKILL.md` |
| 7. Benchmark briefs and refinement loop | | |

## Playtest feedback log

### Room and exterior review (2026-10-04, TownLab and the labs)

TownLab "excellent, way better than treeplace or dysvale". Rooms: small improvements, progress good.
1. Storeroom racks a little too dense and numerous: spread out, fewer. Done (5 a row, 1.2 apart, 2.2 aisles).
2. A wall with one bookcase should usually be full of bookcases; shelves tight into corners. Done.
3. Great hall: 4-6 fewer table sets; a large floor-tile carpet. Done.
4. Exterior: layout and planting excellent; more object variety (rock piles); fewer aspens on the map edge. Done.

### TreePlace v0.3 room review (2026-10-03)

Numbered room pictures again. The user set the frame of reference: NE wall = top right, NW = top left,
SE = bottom right, SW = bottom left. Fixed in v0.4:

| # | Finding | Fix |
|---|---|---|
| all | Very high priority: shelves and hangings on the NE and NW walls (the camera sees their fronts); tables, chairs and free pieces toward the S and W corners | Facing pieces only on back walls (`FACING_FAMS`, `FACING_TYPES`); free pieces lean to the front (`FRONT_WEIGHT`). Checker: a facing piece on the SE or SW wall |
| all | Fill whole walls with bookshelves end to end, not one here and there | `line_wall`: one unbroken run per wall, flanking its anchor; a second back wall in studies, living rooms and big bedrooms. Checker: two shelves on a wall with bare wall between them |
| all | Use more of the game's objects | Building palettes (seats, tables, carpets, hangings, plants), free-standing groups (tables with food, work tables, lab benches, telescopes and orreries, statues, freestanding hearths), library stacks |
| all | Study Con07B; use carpet floor tiles sometimes | Carpets of floor tiles with the gold trim in some rooms on built floors (Con07B: 13 of 28 rooms) |
| all | Bigger rooms and structures than Westwood's | Buildings 1.25 times Westwood's size; fullness by floor coverage (`ROOM_COVER`), which grows with the room |
| 1, 2 | Much better | Kept |
| 3 | The chest should be closer to the NW wall; it sits in the middle | Pieces stand snug against their wall (Westwood's gaps, `SNUG_GAP`). Checker: a chest, shelf or desk 0.9-3 units off its wall |
| 4, 5, 7 | A store room holds more than other rooms: racks of gear in the middle | `rack_rows`: unbroken rows of gear racks down the middle (gear, hunting and mining kinds); the gear store is its own room kind |
| 6 | Carpets weirdly spaced; chests too close to the beds | One rug before each bed or none; the chests stand 1.2 units past each bed's foot |
| 8 | Shelves along the wall with the hearth | Shelves line the hearth's wall on both sides of it |
| 9 | Still too empty | A table with food, work tables with stools and crates |
| 10 | More shelves, banners and trophies along the NE wall | Both back walls lined, hangings between groups of shelves, library stacks in the middle |
| 11 | Best room of the group | Kept |

Also:
- the checker credits a piece whose centre falls in a wall's cell to the room on its side, as Westwood's maps need;
- "sparse" compares a room with Westwood's rooms of its kind and size (rooms of 50+ tiles are sparser).


### TreePlace v0.2 room review (2026-10-03)

The first review from numbered room pictures (`review/rooms.py --each`). The theme: almost every room was too
empty. Fixed in v0.3:

| # | Finding | Fix |
|---|---|---|
| 1 | Living room: very empty, lights uneven, the table half on a rug too small for it | Rooms fill toward Westwood's fuller rooms of the kind (85th percentile, never past the 95th) with what their identity calls for: shelves, a bench, plants, hangings in one theme. Lights go where they leave the darkest corner closest to a light. Tables stay off rugs, or stand centred on a woven rug of their own (checker: tables half on a rug) |
| 2 | Herbalist: table on a rug, unbalanced; line whole walls with potion shelves (but not every wall) | `shelf_wall`: one whole back wall of shelves side by side; sacks of herbs, potted plants |
| 3 | Bedroom: very empty; nightstand too close to the bed | The bedroom gets a desk and chair, shelves, a bench and a plant; the nightstand stands apart from the bed |
| 4 | Storeroom: too empty; a shelf in a corner looked wrong (it faces one way; no corner piece) | Walls are stocked past blocked spots (stocking used to give up after four misses). Heaps go in the corners. Shelves and desks keep 2.2 units out of corners |
| 5 | Ore shed: clusters and open spaces; spread things out | Carts keep room round them; crates and tool barrels stand along the walls with gaps |
| 6 | Bunk room: beds too close; more shelves, objects and bigger rugs | Beds of one kind, evenly spaced at least 1.6 units apart, a nightstand between neighbours, a footlocker at each foot, rugs along the aisle, two shelves for gear, hangings. The cot heads are now at the wall (`NUMBERING_OVERRIDES`). Checker: beds closer than 0.9 units (Westwood never) |
| 7 | Bunkhouse storeroom: too evenly spaced; balance clusters and spaced objects | Corner heaps, groups of 1-4 with varied gaps, single pieces |
| 8 | Mess hall: good layout but needs more | More tables in rows, benches along the walls, crockery shelves, hangings |
| 9 | Kitchen: cauldron too close to the hearth; apples crowding the cauldron | The cauldron stands 2 units from the hearth (Westwood's typical gap). Supplies keep clear of anything that is not a supply on every side, 2.4 units from a fire, since a fire is drawn far wider than its footprint. Checker: a cauldron or stove within 0.6 units of a hearth (Westwood: at least 0.87) |
| 10 | Study: too small and empty; a double door into a bedroom; three kinds of door in one house | The foreman's house is bigger. Each building picks one door family: the entrance gets its door, the rooms its single door. Checker: double doors between house rooms; 3+ door kinds per building |
| 11 | Foreman's bedroom: could use more | As 3 |

Also:
- the room pictures show front walls see-through (an editor `nowalls` render, blended);
- the checker judges each generated room by its declared kind (`<map>.rooms.json`);
- a room never goes past Westwood's 95th percentile for its kind.

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
