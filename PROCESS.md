# How a map is made

This is the repeatable process, the basis of the phase 6 skill. Each step names its tools. Order
matters: work from the centre outwards and from identity to detail.

## 1. Identity: what the place is

Write a `MapIdentity` (`mapgen/kit/identity.py`) before anything is built:

- **Theme**: one sentence on what this place is and what happens there ("a logging and milling village in a deep forest vale…").
- **Environment type**: town, forest, swamp, cave, dungeon, castle, ice or lava (`rules/environments.py`). Statistics are only ever compared with Westwood's maps of the same type.
- **Areas**: each with its purpose (the village heart, the miller's glade, the woodcutter's clearing…) and landmark.
- **Buildings**: each with a role (inn, store, smithy, home, cottage, mill, woodcutter), a name and an occupant. A role fixes:
  - the room program (an inn is a tavern, a kitchen and the innkeeper's bedroom);
  - the wall style and minimum size;
  - whether it faces the square or the road;
  - the outdoor scenes that show the trade (deliveries at the inn, a woodpile at the woodcutter's).
- **Rooms**: each kind has an identity (`ROOMS`): what it is for, what it must contain, what it may contain, and the allowed object types (a bedroom's storage is a chest, never a barrel). Nothing else goes in.
- **Outdoor scenes** (`SCENES`): every prop group has a reason and a place (beside the door, against a side wall, in front).
- **Sections** (larger maps): give each section its own character, in its walls, trees, undergrowth, flowers and
  ground (`FORESTS` in `kit/vegetation.py`; a `REGIONS` table in the design). For example: an ancient green
  north wood, a golden aspen west wood, a pine south wood. Every area names its section
  (`Land.area(..., region=)`). `Land.assign_regions()` gives each square to a section, with wavering borders, and
  `Land.apply()` takes a function of the section for walls and floors. Pick forest walls that have every shape;
  any missing shape falls back to the material Westwood joins it to (`Spec._wall_material`).

## 2. The centre first

Place the central feature at the heart of the main area. Examples: the village square and its landmark (a
well); the sacred grove's crystal cluster with a ring path round it; a mining camp's work yard. Then lay out the
streets leaving it toward the other areas.

Features that shape the land around a centre are planned with it, before any building. A mine entrance
(`kit/mine.MineEntrance`) is planned together with its yard:
- `plan()` reserves the forecourt and tunnel, and forbids land behind the rock face (`Land.forbidden`), so no
  building goes there and the land never grows into the rock;
- the face must be on the yard's north-west or north-east side, because Nox only shows a wall's face toward the
  bottom of the screen; on the other sides it reads as a drop.

## 3. Buildings, from the centre outwards

1. Public buildings face the square across a clear margin.
2. Homes line the streets, entrances facing them.
3. The outlying areas get their own features: the mill house and pond, the woodcutter's hut and stumps, the standing stone.

Rooms are sized by kind (a tavern takes most of an inn's floor) and furnished only from their identity.

## 4. Plan the water with room for its banks, and its crossings with the roads

Reserve the stream's and pond's bands before anything is built, keeping roads clear of them except
at crossings. Connecting structures are planned in this phase, never fitted afterwards:
- **Bridges and fords:** choose the crossing on the road (`Land.plan_crossing`), straighten the road through it, and lay the stream to cross at a right angle, so the deck lands on the road at both ends.
  - The bridge fits its stream. Westwood's stream bridges are rope-bridge kits (`Waterworks.rope_bridge`, using
    the crossing's `kit`) over a 2-row deck. Plank decks are never more than 2 tiles wide.
  - The stream runs straight and calm through the crossing (`stream(calm=[(crossing, 16)])`), never on a bend.
- **Docks:** start where the road meets a lake's shore. Every transition (road to grass, grass to bank, bank to water) needs room for its own
blend. Westwood's town roads almost never run within two tiles of water.

## 5. The land grows around what was placed

Only now draw the map's shape (`Land.carve`): a margin of open ground with an irregular edge around
the square, buildings, roads, water and features, plus the clearings, ending in the forest wall.
Never start from the borders and fit the village into what's left.

Then, in this order:
1. Cut the planned rock (`MineEntrance.cut()`).
2. Assign the sections.
3. Break up broad glades with thickets: `Land.thickets()`, small islands of forest that keep open ground round
   them. Westwood's forests carry 21 to 52 wall pieces per 100 floor tiles; a single ring of forest round open
   grass carries about 15.
4. Apply the walls and floors, then `MineEntrance.ground()` (rock face and tunnel walls, ore-dust floor, the
   cart track).

## 6. Ground, water, life

1. Dig the water into the land, with a bridge where the road crosses.
2. Route a path from each door. Where Westwood never lets the path's floor touch the room's floor (packed dirt
   against marble), the path uses Westwood's buffer floor (`Land.connect_door`).
3. Grass variety patches, kept clear of roads, banks and buildings.
4. Scenes, gardens, benches, street lights, and the features' dressing. `MineEntrance.dress()` adds the portal
   and a timber set every 3 squares, a cave-in from wall to wall, the creak and glow beyond it, torches flanking
   the mouth, and a loaded cart on the track.
5. Vegetation from the forest edge inward: tree lines, groves outside settled areas, and undergrowth and flowers
   in single-type patches. Landmarks (waystones, standing stones) keep a clear space round them.
6. Props that belong somewhere spread out from there with a falloff and spacing (`vegetation.scatter`): stumps
   round the woodcutter's, logs along wood edges, crystal shards out from the cluster. Never put 4 or more of a
   kind together in one spot when there are none elsewhere.

## Relations: every piece makes sense where it stands

- **Paths lead to doors.** Route each door's path from its doorstep to the streets. Streets keep clear of walls and never run into the side of a building.
- **Buildings open toward what they serve.** Public buildings open onto the square, homes onto their street.
- **Set pieces are composed.** The square is symmetric around its centre feature, with benches facing it and lights in balanced positions. Street lights follow a steady rhythm.
- **Water features fit their water.** A dock starts where the road meets the shore and reaches out into open water on a lake, never across a puddle. Reeds grow in the shallows.
- **Rooms are composed as a whole** (`compose` recipes in `kit/identity.py`):
  - each anchor (bed, chest, hearth, stove, shelves) gets its own wall stretch, back walls first, centred where Westwood centres it;
  - a rug lies before the chest or hearth, or in the middle of the room;
  - the table set takes the open middle;
  - supplies stand in rows from a corner;
  - the space in front of every anchor stays clear;
  - companions come only with their anchor (a chair with its table or desk, bellows beside the forge, the anvil before it).
- **A room's arrangement shows its purpose at a glance** (TreePlace v0.1 playtest). Lay out whole groups, not
  single pieces:
  - **Bunk room:** beds of one kind in a straight row, side by side along a back wall, headboards against it
    (`Furnisher.bed_row`). Put a chest at each bed's foot, a rug along the row, and shelves for gear across the
    room. All of Westwood's rooms with 3 or more beds use one kind, in a row.
  - **Mess hall:** long tables in rows with a bench along each long side (`Furnisher.table_rows`), a hearth, and
    a shelf of crockery. Barrels belong in the kitchen or storeroom.
  - **Storeroom:** supplies stocked along the walls in tidy groups (`Furnisher.stock_walls`): stocked log shelves,
    crates side by side, barrels, sacks. The middle stays clear. No bookcases, and no black-powder barrels in a
    dwelling.
  - **Kitchen:** the hearth and cauldron, a table with stools, and provisions along the other walls, so the whole
    room is used.
  - Seats stand along a table's long sides (Westwood: 75% of the chairs at its long tables). A table in a room for
    sitting and eating always has its seats, or it is left out.
  - Food is never set out as loose items. Nox draws items at floor level, so food reads as dropped on the floor;
    use a table that carries its food (`RoundTableWithFood`).
  - Furniture spreads through the room's whole length, never packed into one end (checker: under 35% of the length).
- **Light houses with candelabras and the hearth.** Never use an open torch indoors: a flame on a stick by a wall
  does not look mounted, and an open flame that size indoors is not believable. Use wood candelabras in log and
  stucco houses, iron ones in stone houses. Torches belong outdoors, in dungeons and in mines.
- **Pieces lie along their wall.**
  - Chests, bookcases, desks and potion shelves lie parallel to their wall with their back against it. Beds stand
    with the headboard against the wall.
  - Westwood numbers these pieces by wall: Chest, Bed and Nightstand 1-4 are the SE, SW, NE and NW walls; Bookcase
    and Desk 1-4 are the NW, NE, SE and SW walls. The furnisher picks the number for the wall
    (`Furnisher.along_variant`), including for a room identity's preferred types.
  - No piece stands in a wall cell.
- **Furniture assemblies are complete.** A bar meets the walls at both ends, its flap sits mid-run, and kegs stand behind it.
- **Balance.** Lights go to the emptiest corners: away from other lights and from the pieces already there. A
  candelabra goes to the free corner, not beside the chest. Centre a piece on its wall, or between another
  piece and a wall.
- **Doors line up.** Both halves of a double door sit exactly on the grid, 46 px apart on each axis. A door type
  hangs as a pair only in a wall direction Westwood pairs it in (`rules/out/doors.json` `by_line`).
- **Symmetry outside too.** Torches flank a door as a pair, on the outside of the wall line (`layout.door_frame`),
  or not at all.

## 7. Check, review, playtest

- `validate/validate.py`: errors must be zero. Warnings compare with Westwood's maps of the same environment, including furniture outside a room's identity.
- `review/review.py`: comparison sheet and design measurements (paths, vegetation structure, roads crowding water…). Apply `review/RUBRIC.md`, including criterion 8 (identity), and record the review in `review/reviews/`.
- `review/rooms.py <map> --each`: one numbered close-up per room (building, kind, purpose). Check every room
  against its purpose, and show the pictures to the playtester for numbered feedback.
- Playtest in the game; log the findings in `ROADMAP.md`.

Builds are reproducible: a design and its seed always give the same map. Never use Python's `hash()` on
strings, because it changes from run to run; use `zlib.crc32`.
