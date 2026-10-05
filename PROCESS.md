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

- Westwood's room sizes are in floor tiles inside the walls: a room of n footprint units holds about n - 2 sqrt(n)
  of them. No room comes out below Westwood's smallest for its kind.
- A building of five or more rooms is a hub, as Westwood's large buildings are (their largest room holds half or
  more of the floor; few have corridors): a great hall down the middle, running toward the entrance, with the
  other rooms along both sides and every door opening onto it.
- A building in a culture's style is furnished in that culture (`rules/CULTURES.md`): an ogre keep with straw,
  fire pits and crude tables; a Land of the Dead temple with sconces, obelisks and tombstones.

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

A town is a web of forest corridors, not a clearing (`rules/TOWNS.md`). Most of a Westwood town's walls ring blocks
of forest and fenced plots, not houses:
- Give it outskirts: a glade between each pair of roads, joined to both by forest paths 11 uv wide or more, so the
  paths loop round blocks of forest. Plan them after the buildings, so they do not change them.
- Give the glades and the town yards with a purpose (`kit/yards.py`): a graveyard, a quarry, an orchard, a monument
  plot, a park of benches, jail cells by the gate, fields by the mill. Each is fenced in Westwood's material for it,
  with a gate facing the town.
- Put clumps of forest in the open meadows (`Land.thickets`).

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
4. Scenes, gardens, benches, street lights, and the features' dressing. A town square in Westwood's manner
   (`Village.fountain_square`): a fountain ringed by potted plants and flowers, benches facing in, ornate street
   lamps at the edge. Signs by the doors read what the building is. `MineEntrance.dress()` adds the portal
   and a timber set every 3 squares, a cave-in from wall to wall, the creak and glow beyond it, torches flanking
   the mouth, and a loaded cart on the track.
5. Vegetation from the forest edge inward: tree lines, groves outside settled areas, and undergrowth and flowers
   in single-type patches. Landmarks (waystones, standing stones) keep a clear space round them. A town is planted
   as Westwood plants one (`vegetation.TOWN_PLANTING`): about 2 trees per 100 floor tiles, by the forest wall,
   because the wall is itself drawn as trees; plants at the wall's foot and in the open; flowers and mushrooms a
   little way out from the wall.
6. Props that belong somewhere spread out from there with a falloff and spacing (`vegetation.scatter`): stumps
   round the woodcutter's, logs along wood edges, crystal shards out from the cluster. Never put 4 or more of a
   kind together in one spot when there are none elsewhere.
7. Last, after the people and their routes: fill the empty ground (`kit/dressing.Exterior(m, land, biome).dress()`;
   2026-10-05 playtest: "exterior areas are way too empty", a castle alley held one bush and two pebbles).
   - Westwood's towns (`py review/exteriors.py --westwood`; per 100 open tiles, roads left out, pebbles not counted)
     carry about 25 props, 6 of them made things, and only 16% of the open ground lies over 4 cells from a prop
     (6% over 6). Our maps had 33-55% (Greywatch, Rimehold); `py review/exteriors.py <map> --holes` draws it.
   - **Scenes with a purpose, not piles** (2026-10-05 Greywatch playtest, scene review: "exterior objects are very
     random and purposeless ... instead of 3 crates and 2 barrels, try a cart, 2 barrels, a crate, a weapon stand,
     and a box"; a lone stone block by a wall's corner). Every outdoor group is a theme from the catalogue
     (`kit/scenes.py CATALOGUE`), each with a purpose, where it belongs (against a house, fence, masonry, curtain or
     the wild wall; in the open by a road, the square, a gate, water, the garrison's ground, town or wild; beside
     which buildings and on which side of them; the biomes), its anchor, its must-have and may-have pieces at set
     offsets, and its variance (one of its layouts, counts in ranges, types swapped, chance pieces, mirrored, turned
     to face its road). Cart loading, a wagon on the verge, a broken wagon, a market awning, a household's stores,
     a woodpile, a chopping yard, a hay store, a midden, a smith's yard, a well, a washing place, a drying line, a
     bench by the wall, an unhitched cart, a timber stack, a sparring ring, archery butts, an archers' mark, a watch
     fire, a guard post, an arms store, masons at work, a waystone, a shrine, a graveside, a hunter's rack, a cold
     fire with logs, a felling; the wood's, the cave's, the lava's and the snow's own heaps.
   - The buildings call for their scenes first (`ROLE_SCENES`: a sparring ring by the barracks, the smith's yard by
     the smithy, a midden behind the inn, a cart loading at the store or mill; a guard post by each gate). Then the
     emptiest ground takes a scene that belongs there, until none lies over 4.5 cells from a prop or nothing fits.
   - A scene is laid whole or not at all: its must-have pieces fit, 70% of what it means to lay, at least 3 kinds of
     thing and 4 pieces. Each theme has a cap to a map (the wood's heaps grow with the ground), a spacing from its
     family (carts, arms, wood...) and from like things already there (a camp's cart, a training ground's
     targets), a family cap (3 carts to a map), and scenes keep 6 squares and their footprints apart, so some open
     ground stays open. Tall scenes keep off front walls; a building's own door scenes are not repeated by it.
   - Groups keep off roads, lanes, water, yards, story places, doors (3 squares), gates, exits, creatures and the
     legs of the routes already laid (`spec.routes`), and a group whose bodies would cut the walkable ground apart
     is taken back. The dressing draws from its own generator; so do the camps (`camps.own_rng`), which replay the
     first camps' draws on the design's generator so nothing after them shifts.
   - **Camps are composed** (same review: "The bandit camp looks terrible ... Beds randomly strewn across an open
     clearing"). `camps.bandit_camp` as Westwood lays its camps: tents in an arc behind a fire ringed with stones,
     on the side away from the way in and toward the top of the screen (a pup tent faces the camera); each bedroll
     before its tent, head to the tent, foot to the fire, two to a tent; with no tents, the bedrolls side by side in
     a row; the leader's awning in the middle with the take before it; the store (cart, crates side by side,
     barrels in a three, sacks) on one flank, the racks in a row on the other, the cooking pot by the fire, a
     lookout post toward the way in. It returns the leader's spot and posts by the store and the racks, so the band
     is not bunched round the fire. The wagon wreck: a wheel off, its load thrown out in a fan, heavy things near.

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
- **Directions.** The user's frame of reference: the NE wall is a room's top right on screen, the NW wall its top
  left, the SE wall its bottom right and the SW wall its bottom left (TreePlace v0.3 room review).
- **What the camera sees** (TreePlace v0.3 room review, very high priority).
  - Shelves, hangings (trophies, tapestries, banners, paintings), hearths, stoves, desks, chests and lab benches go
    on the NE and NW walls, whose fronts face the camera. On the SE and SW walls the camera sees only a piece's
    back, or nothing (Con07B: shelves NW 10, NE 2, SE 3, SW 0; hangings only on the NE and NW walls).
  - Tables, chairs and other free-standing pieces lean toward the room's front, its S and W corners, nearer the SE
    and SW walls (`FRONT_WEIGHT` in `middle_spots`). Benches, supplies and carts may stand against the front walls.
- **2026-10-04 review** (TownLab and the labs):
  - Storerooms: free-standing armour and weapon racks in the middle, crates, barrels and wall shelves round them,
    but at most 5 racks to a row, 1.2 units apart, with 2.2-unit aisles.
  - A wall with one bookcase is filled with bookcases end to end (`complete_bookcase_walls`), and shelves sit tight
    into the corners (`CORNER_CLEAR` 1.05; a whole wall packs into the corner it shares with the other back wall).
  - Great halls: a table per 48 tiles (at most 6) on a large carpet of floor tiles.
  - Outdoors: rock piles in Westwood's manner (`Planter.rock_piles`); few aspens right against the boundary.
- **Large rooms mix their pieces** (2026-10-05 playtest, Greywatch: "way too many benches and not enough object
  diversity ... too many of the same object (chapel benches, tavern tables and chairs)").
  - A big room's repeated set stops at a cap, a piece per so many floor tiles (`repeat` in `ROOMS`, held in
    `try_put`, the plan, the fill steps and the top-up). The space left takes other composed groups of the room's
    identity, or stays open floor: Westwood's big rooms are sparser than its small ones.
  - Westwood: taverns hold a table per 27-42 tiles (Con07B 8 in 216 tiles, Con06a 4 in 166) in mixed kinds; halls
    and temples with benches hold 6-8 (2-6.5 per 100 tiles) among columns, statues, tapestries and plants.
  - Taverns: a table per 28 tiles, at most 12, in three kinds of set (round tables with stools, long tables with a
    bench each side, tables of food), with the wall hearth and a rug before it, open hearths with benches round them
    in a big common room, a cask with barrels by it, kegs along the walls (was 24-28 tables and 76-83 chairs).
  - Chapels: the altar (Dun Mir's; the town style had left it out) on the back wall facing the longest run of the
    nave, between statues; a pew per 10 tiles, at most 16, two to a side in rows nearest the altar; a carpet runner
    up the aisle; a colonnade either side of the pews and on down the nave; a pair of sarcophagi behind the pews
    (was 30-46 pews wall to wall).
  - Great halls: a bench per 11 tiles in all (the tables' and the hearths' included), at most 24; a chest per 80
    tiles; open hearths with benches at the ends of a long hall (Thornwick's had 26 benches and 8 chests).
  - A capped set must not hand its space to one other piece: plants and statues do not multiply with a room's size
    in the fill and top-up (with its benches capped, Thornwick's great hall had been topped up with 15 of each), and
    a top-up plant goes only into a real corner.
- **Throne rooms and halls face their door** (2026-10-05 playtest, Greywatch's keep: "The throne at the end of the
  room is facing sideways towards the store room. The pillars are in the dead center of the room, making walking
  straight in through the door impossible. There are also two statues that mysteriously face directly against the
  wall.").
  - Westwood's Dun Mir throne faces SE only (Hecubah's in Con06b looks down a runner to his doors, wolf statues
    flanking it, flame basins in pairs along the runner). So it stands on the NW wall, in line with the throne room's
    door in the SE wall, facing it down the room (`place_throne`). The building gives the throne room that door
    (`building._seat_throne`): the entrance room keeps the throne when the entrance is in its SE wall; else the throne
    goes to the room on the hall's NW side, entered through its SE wall, its door centred on that wall, and the
    entrance room becomes the great hall. A keep entered from the NW has no such room (none in the campaign).
  - A clear aisle and a carpet runner run from the throne to the door; statues flank the throne against its wall
    (`flank`) and line the aisle in pairs facing across it (`aisle_pair`); columns stand in pairs of rows either side,
    set back from the walls (`colonnade`, halls too), never a row down the middle.
  - The straight way in from every door stays clear (`_openings`, `DOOR_WAY_*`): nothing within 4 units (0.4 of the
    room's depth), no column or statue within 12 (3/4 of the depth).
  - Statues face into the room (`face_statues`): with their back to the wall they stand by, else toward the aisle or
    their twin. Statue2a faces SE, 2c NE, 2e NW, 2g SW (Westwood: 35 of 50 2a at a NW wall, 39 of 55 2c at a SW, 49 of
    73 2e at a SE, 48 of 58 2g at a NE).
  - Floor candelabras go by the back walls or beside the columns; before a SE or SW wall, drawn see-through, they read
    as loose on the floor.
  - The checker warns of a piece in the way in from a door and of a statue facing a wall within 3 units
    (`checks.room_ways`; Westwood: 31 such pieces in 218 rooms, 4 statues).
- **Whole walls, not single pieces** (TreePlace v0.3 room review: "put bookshelves end to end for the entire length
  of the wall").
  - `Furnisher.line_wall` lines a back wall end to end. It tests every spot of the wall first and lays only one
    unbroken stretch: the one at the anchor (hearth or desk, flanked on both sides), or else the longest. There are
    no holes, never a lone shelf against a long wall, and 1.3 units stay clear at the corners.
  - With `decor=k`, a hanging takes a gap after every k shelves. A run never starts or ends with that gap.
  - Studies, living rooms and big bedrooms line their second back wall too (`other=True`). Line it before the
    hangings, or they take the wall.
  - Every room whose identity lines walls is lined to 38% of its NE and NW walls (`Furnisher.line_backs`, measured
    as the room score measures it: `TALL_PIECES` and hangings). It lines the back wall not yet lined, then grows the
    rows already there end to end. It never starts a second row on a wall: a shelf set singly by a hearth counts as
    that wall's row. Hangings close what is left. Big rooms have two long back walls, and their recipes had left
    them about 30% lined.
  - A room still short of its coverage target after its fill steps is topped up (`Furnisher.top_up`). First its
    shelf rows grow, then single pieces its identity allows: chests, benches, plants, lab pieces, statues. Never
    more than the identity's count for the room's size, plus one (7 potted plants in a study is clutter), and never
    stoves, a hearth's anchor.
  - Rows stand unbroken too: gear racks down the middle of a storeroom, and library stacks of bookcases end to end
    in a big study (`rack_rows`, kinds gear, hunt, mine and books). A row slides across the room until it fits
    whole, or it is left out. Rows stay off carpets.
- **Rooms are full, and fuller as they grow** (TreePlace v0.2-v0.4 room reviews).
  - Fullness is the share of the floor that furniture covers (`ROOM_COVER` in `kit/identity.py`), not a piece
    count. A wall of shelves is not clutter. Storerooms 0.30-0.42, kitchens 0.21-0.32, barracks and mess halls
    0.24-0.34, living rooms, studies and herbalists 0.17-0.30, bedrooms 0.14-0.28.
  - Compose the anchors first, then `fill_room` takes the recipe's `fill` steps in turn (each with its own `max`,
    and `min_area` in grid cells, about 2.2 per floor tile) until the target is met.
  - The open floor of a bigger room takes free-standing groups (`GROUPS`, `place_group`):
    - a table and its seats, sometimes on a rug;
    - a table that carries food;
    - a work table with stools and crates beside it;
    - a curio (telescope, orrery, globe);
    - a pair of statues;
    - a freestanding hearth with benches;
    - ore carts.
    A group takes only pieces its room's identity allows (`Furnisher.belongs`).
  - Set pieces for the grander rooms:
    - a tavern's bar, with kegs behind it;
    - a trader's counter set out from the wall, with the keeper's space behind it;
    - a chapel's pews in rows facing the altar, split by an aisle;
    - colonnades in halls and throne rooms;
    - rows of coffins and sarcophagi side by side in crypts;
    - Westwood's four-piece Dun Mir throne on a NE wall.
  - Each building keeps one palette of chairs, stools, benches, tables, carpets, hangings and plants, so its rooms
    belong together while the buildings of a map differ.
  - Some rooms on built floors get a carpet of floor tiles instead of a rug object, with Westwood's gold trim (Con07B
    lays them in 13 of its 28 rooms; `lay_carpet`).
  - Late core pieces keep their front clear too: a hearth or cauldron placed by the fallback still gets its zone
    (`FRONT_CLEAR`), so no candelabra stands before it.
  - The checker calls a generated room sparse below Westwood's median coverage for its kind and size. Westwood's
    rooms of 50 or more tiles are sparser (bedrooms: 0.117 overall, 0.078 large). It calls a room crammed above the
    kind's `ROOM_COVER` maximum.
- **Bigger than Westwood** (instruction during the v0.3 round: "we are going to ultimately produce much larger maps
  and a larger scale than anything in the original game").
  - Buildings are 1.25 times Westwood's size (`BUILDING_SCALE`, `role_size`). A building that does not fit is tried
    again at 0.92 and 0.84 of that.
  - A Nox map is 256 x 256 cells, so "larger" means bigger structures, rooms and groups within that grid.
- **Spacing within the room.**
  - A cauldron stands about 2 units from the hearth (Westwood's typical gap; the closest is 0.87).
  - Supplies keep a unit or more from anything that is not a supply, on every side, not just along their own
    wall. They keep 2.4 units from a fire, because fires are drawn far wider than their footprint.
  - Shelves and desks face one way and have no corner pieces, so they keep 2.2 units out of corners.
  - Bunks stand at least 0.9 units apart (Westwood's closest) with a nightstand between neighbours, spread evenly
    along the wall. Each bed's head goes against the wall (the cot numbering comes from the pillows, not from
    Westwood's sideways cots).
  - Tables, desks and beds stay off rugs. Bearskins are drawn about 1.2 units past their footprint, so the
    margin is 2 units for a bearskin and 0.8 for a woven rug.
  - The exception is a woven rug laid centred under a round or square table (`Furnisher.rug_under`), which makes
    the middle of a bedroom, study or living room one composed piece.
  - Rugs try the other designs and slide a little before giving up.
  - Potted plants go only into real corners of the room.
  - Storerooms mix heaps in the corners with groups and single pieces, so they have both clusters and open
    stretches.
  - A herbalist's or library's shelves line one whole wall, side by side, but not every wall.
- **One kind of door per building.** The main entrance takes the family's door; the doorways between rooms take
  its single door. A double door into a bedroom is not believable.
- **Light houses with candelabras and the hearth.** Never use an open torch indoors: a flame on a stick by a wall
  does not look mounted, and an open flame that size indoors is not believable. Use wood candelabras in log and
  stucco houses, iron ones in stone houses. Torches belong outdoors, in dungeons and in mines.
- **Pieces lie along their wall.**
  - Chests, bookcases, desks and potion shelves lie parallel to their wall with their back against it. Beds stand
    with the headboard against the wall.
  - Westwood numbers these pieces by wall: Chest, Bed and Nightstand 1-4 are the SE, SW, NE and NW walls; Bookcase
    and Desk 1-4 are the NW, NE, SE and SW walls. The furnisher picks the number for the wall
    (`Furnisher.along_variant`), including for a room identity's preferred types.
  - Pieces stand snug against their wall (`SNUG_GAP`: Westwood's p25-p50 gap between a piece's back and the wall
    line: shelves 0.18, chests 0.22, desks 0.25, hearths 0.15). Their centres may fall in the wall's cell in front of
    a NE or NW wall, at least 0.3 units into the room, as Westwood's do (202 pieces). The checker credits such a
    piece to the room on its side of the wall.
- **Furniture assemblies are complete.** A bar meets the walls at both ends, its flap sits mid-run, and kegs stand behind it.
- **Balance.** Lights go to the emptiest corners: away from other lights and from the pieces already there. A
  candelabra goes to the free corner, not beside the chest. Centre a piece on its wall, or between another
  piece and a wall.
- **Doors line up.** Both halves of a double door sit exactly on the grid, 46 px apart on each axis. A door type
  hangs as a pair only in a wall direction Westwood pairs it in (`rules/out/doors.json` `by_line`).
- **Symmetry outside too.** Torches flank a door as a pair, on the outside of the wall line (`layout.door_frame`),
  or not at all. A torch pole never stands in or against a wall. A yard's corner torch moves into the yard when a
  bigger building reaches that corner.

## Story: a map with a start, missions, fights, rewards and an exit (Thornwick, 2026-10-04)

A finished map is a story the player walks through, and every creature in it is placed for a reason. Write the story
in the design's docstring before building anything, then plan the areas from it: each quest needs its places.

1. **The start and the hook.** The player arrives somewhere that shows what is wrong (Thornwick: a plundered wagon
   on the road, the carter beside it) and someone tells them where to go.
2. **The main quest locks the exit.** The way out is barred until the main quest is done: a wall across the road
   with a double gate, LockType Mechanism, unlocked by the quest giver's last line (`A.unlock`). The exit area
   (`InvisibleExitArea`, xfer MapName) lies beyond it and leads to the next map, which must exist (TNorth).
3. **Side quests, each with its own place, giver and reward**, chosen to send the player through the whole map: a
   crypt behind a key-locked door (LockType Silver; the giver hands over the key), a wolf den up a side path, a ruin
   with a boss and an heirloom. One quest may offer a choice (two givers want the same item).
4. **Fights with a reason:** an ambush from a camp off the road (a `near` event sets them hunting), a camp with a
   sentry who rouses the rest, a pack round its den, the restless dead in a crypt, a boss guarding a chest.
5. **Rewards:** gold and items from the givers (`A.gold`, `A.give`), loot in chests (`items=`), caches hidden at the
   forest's edge, a shop for each trade that buys and sells. Every other container is filled at build time in
   Westwood's manner (`kit/loot.py`): every chest, about 40% of barrels, half the crates, coffins in crypts, within
   the map's gold budget after the story's own gold and the quests' payments.
6. **Everyone talks:** quest givers, guards, the watch and every townsperson, each with a line that points at a quest
   (rumours), and a new line once the main quest is done. A portrait for each (`q.portrait`, Westwood's names).

The tools:
- `kit/quests.py` (`QuestBook`) declares it all; `kit/behaviours/quests.go` runs it. Lines are tried in order, the
  later stages first. Conditions read the world where they can: `q.dead(names)` for deaths, `has=` for carried
  items, so a saved game loaded with fresh scripts strands nothing (the script's own flags do not survive it).
- Text goes in the map's string table (`<Map>.strings.json`), merged into the game's by `mapgen/strings.py` as
  `nox.csf.json`, which OpenNox reads in place of nox.csf. Keys are at most 31 characters. No audio yet.
- `kit/camps.py` lays the story's places: bandit camp, wreck, wolf den, cache, ruined tower, signpost; `kit/scenes.py` holds the outdoor scene catalogue.
- Keep the story's places open before the forest is placed (reserve them in `land.taken`); the planter keeps forest
  paths free of trees itself, and `Land.open_links` keeps every passage open.
- Creatures: never place a Zombie (OpenNox cannot read the map back); clone townsfolk from Westwood's maps in their
  clothes (`spec.clone(..., name=)`).
- Check: `tests/check_scripts.py` (compiles against the game's NoxScript), `mapgen/install.py`, then
  `tests/server_smoke.py <design>`: the map loads, and the self-checks find every creature, waypoint and story
  object. `review/spots.py <map> <names>` renders close-ups of the story's places.

**What the engine needs** (Thornwick and Greywatch playtests, 2026-10-05: freezes, "MISSING:NPC:Hedda", no minimap).
The kit does all of it; know why before changing it:
- A gift (`A.give`) is made at the player's feet and picked up three frames later. A new object waits on the server's
  pending list until the frame ends; picking it up at once left it in the world and the pack together, and the next
  walk through either list looped forever: the game froze after a talk gave an item, and later on death or in fights.
- The dialogue window titles a creature with the string `NPC:<script name>` (Westwood's `NPC:Horst`). Every talker
  gets one; townsfolk get given names (Westwood's donors' names stay theirs). The string table is shared by all maps,
  so one script name in two maps carries one title (`mapgen/strings.py` refuses a clash).
- The minimap draws only the walls of the group of the polygon the player stands in, and the game finds that polygon
  by counting edges crossed on a line to the map's corner (0, 0) or (5888, 5888). Each map gets one polygon over the
  whole map, group 100 as every wall, inset from the edges with its corners off that diagonal; corners on the map's
  corners put the player "outside" everywhere.
- Clones lose their donor map's script hooks (ScriptEvents naming its functions, KeeperDie, MonsterGoHome).
- Playtest builds start from `Nox Map Test` (the Nox folder): when the game stops responding it saves a dump of what
  it was doing to `logs\freezes\<time>\`.

**How people move** (playtest 2026-10-05: "npcs wander around too sporadically. they walk into walls ... they look like
ants"; "npc trying to walk through the door but getting stuck on the frame").
- Townsfolk never Wander. Each walks a tour of the town's real places (`StoryMap.townsfolk`): their home door, a spot
  on the square, a shop, then the well, statues, benches, gardens, yard gates and neighbours' doors, 5-7 stops in a
  loop, different for each person (`_pick_tour`, its own generator per name). They stand 16-24 s at each stop (plus up
  to 4 s in the script), facing what is there, or the player when near.
- Legs follow the roads and paths: `kit/walkways.Router` routes over the cells a body stands clear on, road cells
  cheaper than grass, then pulls the path straight into legs within 16 px of it (a waypoint at each bend, legs under
  230 px). Tours stay outdoors and within reach of the square; they are laid when the scripts are written
  (`Behaviours.later`), once every wall, tree and bench stands.
- Doorways are passed square-on, or not at all: a point straight out in front of the opening, its centre, a point
  straight in behind it (`Ground.passage`, single and double doors, both wall lines). The router itself never routes
  through a door cell. Townsfolk step inside only shops, inns, chapels and smithies whose door is not locked; elsewhere
  they stop on the doorstep, 34-64 px out, never against the jamb. Garrison patrols go room to room through shared
  doorways the same way (`Dresser._route`).
- The watch walks a beat (`StoryMap.beat`): 6-7 stops spread across the town, 8-12 s at each.
- In the game, one ticker looks after every walker twice a second: a walker that has not moved for 6 s on a leg is
  sent on again, after 12 s it skips to the next waypoint. Waypoints on a tour are never linked (a linked waypoint
  makes Move roam the links).
- The checker proves it (`check_routes`, on every build): every waypoint on floor, off walls (11 px), out of
  obstacles and water; every link and every leg of `<map>.routes.json` sampled every 4 px, clear of the void, wall
  pieces (as thin lines, 10 px), obstacles, and through doorways within 25 degrees of square-on and near the middle.
  `review/storymap.py <map> --routes` draws them.
- 2026-10-05, long walks (playtest: Greywatch's Wil, sent home by `A.walk` as one `Move` to the barracks, pressed
  into the trees at the end of a forest strip). The game's own path search gives up on a far goal and walks
  straight at it, so a story never sends anyone far with one Move. `StoryMap.journey(name, key, to)` lays the walk
  once the map stands: `Router.route_far`, along roads and paths and through any unlocked doorway or gate square-on
  (each doorway a portal of its three passage points), a waypoint at each bend; `A.walk(name, key)` starts it and
  the walker goes leg by leg (behaviours `Journey`), staying at its end. Journeys are in `routes.json`, so the route
  check walks them too. Wil, Gunnar and Pip, Brin and Tam walk home so.
- 2026-10-05, nobody shares a spot (playtest: a townswoman and a guard pushing each other off one stop by a gate for
  ever; the old builds had 30-45 stops exactly shared on each town). Every stop of every tour, beat and journey gets
  a standing spot of its own (`StoryMap._spots`): another side of the well or statue, beside a doorstep rather than
  in front of the door, its own place on the square, its own spot past a shop's threshold; 40 px from every other
  spot and from every creature standing where it was placed, 26 px clear of every doorway's passage points. Beats
  prefer places no other beat takes; a garrison's patrollers each get their own stops, starting apart round the
  loop (`Dresser._own_rounds`). `check_routes` faults two walkers' stops under 32 px apart.
- In the game a walker never pushes: the ticker watches whether it gets nearer its waypoint, not whether it moves
  (two pushing each other jostle without getting anywhere). Not nearer for 1.5 s: at a stop it stands where it is,
  a little aside, and takes its pause; at a bend or doorway point it goes on to the next; elsewhere (someone in the
  doorway or gate) it gives way 1-3 s and tries again, and after two tries goes on. Townsfolk set out a few frames
  apart, and run home along their own route (the shorter way round), never with one Move.
- 2026-10-05, hostile groups stand apart (playtest: Thornwick's bandits bunched round the fire "like a swarm").
  Westwood's grouped creatures stand 49 px from their nearest at p25, 70 at the median (corpus, 3,091 creatures):
  `Population.creature` keeps every hostile creature 48 px from the others (`spread=False` for two prisoners in a
  cell). A camp's men take posts as a camp is lived in (`kit/posts.camp_posts`, from what `bandit_camp` returns and
  the tents and bedrolls round the fire): the leader by the chest, some on every other seat round the fire, some by
  their tents, the watch well apart at the approach. When roused (sentry, pack, ambush) melee fighters come at the
  player from their own sides, fanned 50 degrees apart, archers keeping their ground (`spreadOn`); a pack lies up
  spread about its den, each on its own spot, rather than trailing its leader.

**A culture's own pieces** (Starwell, 2026-10-05: a wizards' college town, the third map of the one-map loop).
- A map with a culture of its own gets its own outdoor scenes without touching the others: a theme with `culture=`
  (`kit/scenes.py`: the wizards' `alchemists_yard`, `stargazers_post`, `star_shards`, `shard_wall`) is laid only when
  the design names that culture (`Exterior(..., culture="wizard")`); every other map draws exactly as before.
- New building roles for it (`kit/identity.py`): `college` (the archmagister's hall of state, a throne room so the seat
  faces its door down a runner; library, laboratory, study, chamber), `apothecary` (shop and brewing room), `observatory`
  (a hall, workroom and chart library in blue stone). Houses take the culture's style by `BuildingIdentity(style=)`:
  Ix's dark-timbered stucco (`stucco_dark_house`, Wiz01A) for a wizards' town.
- A sealed building the story opens: `StoryMap.seal_entrance(building, prefix)` names its entrance door(s) and locks
  them to a mechanism; `A.unlock` opens them (the observatory, when the three binding-stones' keepers are dead).
- A dark ward or a dead stone the story relights is a ring of standing stones round a crystal with a named
  `ColorLight` disabled in `q.start` and enabled by the story (Starwell's south ward-ring and the Starwell); the
  binding-stones' purple lights go out as their keepers die. Westwood's stones are drawn crystalline either way, so
  the light is what tells lit from dark: confirm it in the game.
- A choice between a bribe and the law: the band are cloned people (they can talk, and one of them offers the purse)
  with a disabled fighter hidden at each one's spot; refusing turns them all (`A.turn`), taking the purse leaves them
  digging and the captain's reward unpaid.
- Townsfolk names follow the donor's body: Westwood's Maiden clones (Wiz02A's Maiden1-9, TowerMaiden, Con06a's
  Townswoman) are women (`story.is_woman`; Con02a's Joyce had been given a man's name).

## 7. Check, review, playtest

- `validate/validate.py`: errors must be zero. Warnings compare with Westwood's maps of the same environment, including furniture outside a room's identity.
- `review/review.py`: comparison sheet and design measurements (paths, vegetation structure, roads crowding water…). Apply `review/RUBRIC.md`, including criterion 8 (identity), and record the review in `review/reviews/`.
- `review/rooms.py <map> --each`: one numbered close-up per room (building, kind, purpose). Check every room
  against its purpose, and show the pictures to the playtester for numbered feedback. Walls in front of each room
  show half see-through, as the game draws them when you are inside, so pieces against them are visible.
- Generated maps write `<map>.rooms.json` beside the map. The checker then judges each room as what it was
  meant to be (a study with two bookcases is not a library).
- Between playtests, improve rooms in the room lab (`mapgen/designs/roomlab.py`, `review/roomscore.py`): every room
  kind at Westwood's typical and large sizes and half as big again, scored on coverage, an open middle, lined back
  walls and the checker's findings. Fix what fails in three seeds before the next playtest.
- Then whole buildings in the building lab (`mapgen/designs/buildinglab.py`, `review/buildingscore.py`): every
  building role at Westwood's size, the kit's 1.25 and the bigger 1.6, scored on room sizes for their kinds,
  reachability, the checker's findings and the rooms' own scores.
- Then a whole town in the town lab (`mapgen/designs/townlab.py`): the village pipeline at the bigger scale, with
  traders behind their counters, villagers on their rounds and creatures in the woods round it, scored by the
  checker, the room score and the design review.
- Load every map with scripts in the OpenNox server before installing it: the behaviours' self-check must find every
  named creature and waypoint.
- Playtest in the game; log the findings in `ROADMAP.md`.

Builds are reproducible: a design and its seed always give the same map. Never use Python's `hash()` on
strings, because it changes from run to run; use `zlib.crc32`.
