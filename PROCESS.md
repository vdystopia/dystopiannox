# How a map is made

**How to use this document.** Read it top to bottom once before starting a map: it is the process, organised by
topic, each rule stated once as it stands today, with the kit function that carries it out. `skills/nox-story-map/SKILL.md`
is the recipe (what to call, in which order); this is the rulebook (what a good result is). Section 9 is the gate a map
passes before the user sees it.

Each rule is tagged with the feedback that set it, e.g. **[SW-3]**; the IDs, the user's words and how each is
enforced are in `review/FEEDBACK.md`. **Recurring:** marks a fault that came back after a fix, with the check that now
catches it. The dated history of how each rule came about is kept verbatim in `review/history/PROCESS-2026-10-05.md`
and in the ROADMAP's playtest log.

Work from identity to detail and from the centre outwards. Builds are reproducible: a design and its seed always give
the same map. Never use Python's `hash()` on strings (it changes from run to run); use `zlib.crc32`.

## 1. Identity: what the place is

Write a `MapIdentity` (`kit/identity.py`) before anything is built [DV3-6]:

- **Theme**: one sentence on what the place is and what happens there.
- **Environment**: town, forest, swamp, cave, dungeon, castle, ice or lava (`rules/environments.py`). Statistics are
  only ever compared with Westwood's maps of the same environment [DV3-5]. A town in snow is a town with the ice
  palette.
- **Areas** (`AreaIdentity`): each with its purpose and landmark; on larger maps each names its section
  (`Land.area(..., region=)`).
- **Buildings** (`BuildingIdentity`): a role (`BUILDINGS`: inn, store, smithy, home, mill, keep, barracks, college,
  apothecary, observatory, townhall, fisher, herbwife, barrow...), a name and an occupant. The role fixes the room
  program, wall style and size, whether it faces the square or the road, and the scenes that show its trade outside.
  `style=` gives a house another culture's walls (Ix's `stucco_dark_house` for a wizards' town).
- **Rooms** (`ROOMS`): each kind lists what it is for, what it must and may contain, the allowed types (a bedroom's
  storage is a chest, never a barrel), and its composition recipe. Nothing else goes in [DV3-4].
- **Sections** (larger maps): each its own walls, trees, undergrowth, flowers and ground (`FORESTS` in
  `kit/vegetation.py`, a `REGIONS` table in the design). Pick forest walls that have every shape; a missing shape falls
  back to the material Westwood joins it to (`Spec._wall_material`).
- **Culture**: a map with a culture of its own (Starwell's wizards) names it once, for its outdoor scenes
  (`Exterior(..., culture=)`) and its roles; buildings in a culture's style are furnished in it (`rules/CULTURES.md`).

## 2. Layout

### The centre first [DV1-5, DV3-1]
Place the central feature at the heart of the main area (the square and its well or fountain, a grove's crystal, a
work yard), then the streets leaving it toward the other areas. A town square is a set piece
(`Village.fountain_square` or `Village.square_piece`): symmetric round its feature, benches facing in, lights in
balanced positions [DV4-3]. Street lights keep a steady rhythm along each street, on one side. Public buildings face it across a clear margin; roads stop at its edge.

Features that shape the land round a centre are planned with it, before any building: a mine entrance
(`kit/mine.MineEntrance.plan()`) reserves its forecourt and tunnel and forbids the land behind its rock face
(`Land.forbidden`); the face is on the yard's north-west or north-east side, since Nox shows a wall's face only toward
the bottom of the screen. After the walls, `MineEntrance.ground()` lays the face, tunnel and cart track and
`MineEntrance.dress()` the portal, timbers every 3 squares, the cave-in, torches flanking the mouth and a loaded cart.

### Water and its crossings [DV3-2, DV5-3, DV6-5, MF-3]
- Reserve each stream's and pond's band before anything is built (`Land.reserve_band`); roads stay clear of water
  except at crossings. Westwood's town roads almost never run within two tiles of water.
- A crossing is chosen on the road (`Land.plan_crossing`), the road straightened through it, and the stream laid to
  cross it at a right angle, straight and calm (`Waterworks.stream(calm=[(crossing, 16)])`), never on a bend, so the
  deck lands on the road at both ends.
- Stream bridges are Westwood's rope-bridge kits (`Waterworks.rope_bridge`, the crossing's `kit`) over a 2-row deck.
  A plank deck is never more than 2 tiles wide. Kit pieces stand at Westwood's exact step offsets (`KIT_STEPS`) [DV1-1].
- A lake belongs in its own dead-end area, its radius well under the area's.
- **Docks** [DV4-1, AM-2]: a dock stands on a lake, on the shore nearest the road, and runs out square to the shore
  (within 30 degrees of straight out from the bank) into open water: water two tiles to either side all along it and
  three tiles round its tip (`Waterworks._shore_start`; `dock(body, "best")` takes whichever kit fits nearest the
  road). Reeds grow only in the shallows.
  **Recurring:** caught by `checks.dock_reach` (run by `check_exterior`).

### The land grows round what was placed [DV1-5, DV1-6]
Only now draw the map's shape (`Land.carve`): open ground with an irregular edge round the square, buildings, roads,
water, yards and features, ending in the forest wall. Never start from the borders and fit the village into what is
left. Then, in order:
1. Cut planned rock (`MineEntrance.cut()`); keep the story's places open (`StoryMap.keep_open`).
2. Assign the sections (`Land.assign_regions()`; wavering borders).
3. Break up broad glades with thickets (`Land.thickets`), small islands of forest with open ground round them, kept off
   the story's lanes. Westwood's forests carry 21-52 wall pieces per 100 floor tiles; a single ring of forest carries
   about 15.
4. Keep every passage open (`Land.open_links()`), then lay walls and floors (`Land.apply`, a function of the section),
   then `MineEntrance.ground()`.

A town is a web of forest corridors, not a clearing (`rules/TOWNS.md`): give it outskirts, a glade between each pair of
roads joined to both by forest paths 11 uv wide or more (`Land.link(..., road=False)`), so paths loop round blocks of
forest; put clumps of forest in the open meadows.

### Yards [AM-1, SW-9]
Yards with a purpose (`kit/yards.py`: graveyard, quarry, orchard, park, field, monument, jail) are planned before the
land is carved (`yards.plan`, `yards.plan_any`) and built after its walls (`yards.build`), each fenced in Westwood's
material for it with a gate facing the town.
- A fence point (p, q) is drawn at square (p, q - 0.5): a plot's fence runs gi..gi + w across i and
  gj - 1.5..gj + h - 1.5 across j (`Yard.centre` is its middle). Everything in a yard or garden stands inside that,
  its drawn half-width plus a margin off the line (`spacing.off_walls`); crop rows are centred with a walkable strip
  to the fence all round. Nothing stands on a fence or wall line, ground bits included.
- A graveyard has graves (`yards._graveyard`): rows 2 squares apart, each a tile of dug earth with its headstone at the
  head, flowers on some; the gravedigger's corner away from the gate (an open grave, the coffin, the spade, the pick,
  a bucket of tools); a cross between two urns by the back fence; a mourners' bench by the gate; torch poles in two
  corners. Westwood has no grave-mound object: its headstones stand on bare earth (War03d).

## 3. Buildings and rooms

### Buildings [DV4-4, DV1-4, TP3-e]
1. Public buildings face the square (`StoryMap.place_buildings(square_area=)`), homes their street, entrances toward
   what they serve; a building that faces the square has its door on that side (the footprint mirrors to put it there).
2. Outlying areas get their own features (the mill and pond, the woodcutter's hut and stumps).
3. Buildings are 1.25 times Westwood's size (`BUILDING_SCALE`, `role_size`), tried again at 0.92 and 0.84 of that if
   they do not fit; buildings grow to fit their room program. A Nox map is 256 x 256 cells, so "larger" means bigger
   structures and rooms within that grid.
4. A room of n footprint units holds about n - 2 sqrt(n) floor tiles (`building._units_for`). No room comes out below
   Westwood's 10th percentile for its kind times the kit's scale, never below Westwood's own.
5. A building of five or more rooms is a hub, as Westwood's large buildings are: a great hall down the middle toward
   the entrance, every other room opening onto it.
6. One kind of door per building [TP2-10]: the entrance takes the family's door, the doorways between rooms its single
   door. Never a double door into a bedroom. A door type hangs as a pair only in a wall direction Westwood pairs it in
   (`rules/out/doors.json` `by_line`); both halves sit exactly on the grid, 46 px apart on each axis [DV6-4]. Half-door
   types are always pairs in a 2-cell opening [DV1-3]; wall pieces beside an opening are shaped as if it were wall
   [DV1-2].
7. Signs by the doors read what the building is (`Village.SIGN_TEXT`, by role); torches flank a door as a pair outside
   the wall line (`layout.door_frame`) or not at all; a torch pole never stands in or against a wall, and a yard's
   corner torch moves into the yard when a building reaches that corner.

### Thresholds [SW-4]
A room's floor runs under its walls and out onto the doorstep; the ground blends onto the doorstep, never onto a tile
that reaches into the room (`Spec._wall_line_floors`, `Spec._door_thresholds`, `Spec._edges`; the rooms' tiles are
`Spec.indoor`). The room's own floor, never a carpet laid on it, and never next to a floor Westwood keeps from it
(`Spec._may_take`). Door paths use Westwood's buffer floor where a path may not touch the room's floor
(`Land.connect_door`).

### Rooms: per type in `rules/rooms/`
There is no one-size-fits-all room: each room type has its own rules, Westwood's measures and good examples in
`rules/rooms/<type>.md`, indexed by `rules/rooms/README.md` (the room recipes are `ROOMS` in `kit/identity.py`, the
furnishing `kit/furnish.py`). Starwell's archmagister's study [SW-7] is the good example of a study
(`rules/rooms/study.md`), not the yardstick for every room. Read the type's file before composing or changing a room.

Rules that hold for every type:
- **Directions** [TP3-a]: the user's frame: the NE wall is a room's top right on screen, NW top left, SE bottom right,
  SW bottom left.
- **What the camera sees** [TP3-a]: shelves, hangings, hearths, stoves, desks, chests and lab benches go on the NE and
  NW walls, whose fronts face the camera (Con07B: shelves NW 10, NE 2, SE 3, SW 0; hangings only NE and NW).
  Free-standing pieces lean toward the S and W corners (`FRONT_WEIGHT`). Benches, supplies and carts may stand against
  the front walls.
- **Pieces along their wall** [DV6-1, TP3-3]: chests, bookcases, desks and shelves lie along their wall, back against it,
  snug (`SNUG_GAP`); beds stand headboard to the wall. Westwood numbers these by wall and the furnisher picks the number
  (`Furnisher.along_variant`). A piece drawn facing one way takes its wall's variant (`WALL_SIDE_TYPE`); statues face
  into the room (`face_statues`) [GW-7].
- **The clear way in** [GW-7]: the straight way in from every door stays clear (`DOOR_WAY_*`): nothing within 4 units
  (0.4 of the depth), no column or statue within 12 (3/4 of the depth). The space before every anchor (chest, hearth,
  stove, shelf) stays clear (`FRONT_CLEAR`) [DV5-4].
- **Spacing** [TP2-*, DV6-*]: supplies keep a unit from anything that is not a supply and 2.4 units from a fire; beds
  never closer than 0.9 units; a cauldron or stove at least 0.87 from a hearth; tables, desks and beds stay off rugs
  (except a woven rug centred under a table); potted plants only in real corners; furniture spreads through the room's
  length (under 35% is bunched) [TP1-1].
- **Lights** [TP1-5, DV4-5, DV6-2]: houses are lit with candelabras and the hearth, never an open torch; lights go to the
  emptiest corners, at least 3 units apart, never before a chest, hearth or stove however it was placed
  (`Furnisher._before_anchor`, measured as `composition.anchor_blocked` measures it) [DV5-4].
- **No loose food** [TP1-1]: Nox draws items at floor level; a table that carries its food (`RoundTableWithFood`).
- **A room reads as what it is** [SW-6, SWR-1, TW-8, AMR-4] whatever its type: the checker's room-identity warnings
  (`check_identity`) catch a showpiece repeated, a stand-alone piece four or more times along one wall, supplies lining
  a wall outside a store, one kind filling a big room, more free tables than the type sets, a shopkeeper not behind his
  counter and a throne that does not face its door.
  **Recurring:** repeated pieces lining walls came back after a fix; these warnings now fail the QA gate unless the
  design accepts them with a reason.

## 4. Outdoors and scenes

### Ground, paths and planting [DV1-6, DV4-2, TL-4]
- Route a path from each door's doorstep to the streets (`Land.connect_door`); streets keep clear of walls and never
  run into the side of a building.
- Grass variety patches (`Land.ground_variety`) kept clear of roads, banks and buildings.
- Vegetation from the forest edge inward (`Planter.plant_all`): tree lines, groves outside settled areas, undergrowth
  and flowers in single-type patches; landmarks keep a clear space. A town is planted as Westwood plants one
  (`TOWN_PLANTING`: about 2 trees per 100 floor tiles by the forest wall, plants at the wall's foot and in the open,
  flowers a little way out). Few aspens right against the boundary; rock piles in Westwood's manner
  (`Planter.rock_piles`), small scenes in the woods (`Planter.forest_floor`).
- Gardens and flowers keep two squares off every door and gate (`Planter`) [AMR-6].
- Props that belong somewhere spread out from it with a falloff (`vegetation.scatter`): never 4 or more of a kind in
  one spot when there are none elsewhere [DV6-3].

### Scenes with a purpose, not piles [DV3-3, GW-2, TW-10]
The outdoor ground is dressed last, after the people and their routes: `kit/dressing.Exterior(m, land, biome,
placed=placed, culture=, martial=).dress()`.
- Every outdoor group is a theme from the catalogue (`kit/scenes.py CATALOGUE`): a purpose, where it belongs (against a
  house, fence, masonry, curtain or the wild wall; in the open by a road, the square, a gate, water, the garrison's
  ground; beside which buildings and on which side; the biomes), its anchor, must-have and may-have pieces at set
  offsets, and its variance (layouts, count ranges, swapped types, chance pieces, mirroring, facing its road). Add a
  theme there when a map needs one; never lay loose piles in a design.
- The buildings call for their scenes first (`ROLE_SCENES`; every role must call for some [AMR-5]; a guard post by each
  gate), then the emptiest ground takes a scene that belongs there until none lies over 4.5 cells from a prop or nothing
  fits. Westwood's campaign towns carry about 25 props per 100 open tiles and leave 17% of open ground over 4 cells from a prop
  (`py review/exteriors.py <map> --holes`).
- A scene is laid whole or not at all (its must-haves, 70% of it, 3 kinds and 4 pieces at least), within its cap, its
  family's spacing and cap (3 carts to a map), 6 squares from other scenes. Groups keep off roads, lanes, water, yards,
  story places, doors (3 squares), gates, exits, creatures and route legs (`spec.routes`), and never cut the walkable
  ground. Tall scenes keep off front walls. The dressing and the camps draw from their own generators
  (`camps.own_rng`), so nothing after them shifts.
- A culture's scenes (`culture=` themes) are laid only on a map that names that culture. A map may name several
  (`Exterior(..., culture=("farm", "ogre"))`: Harrowby's farmers' threshing floors, harvest wains and wind-mills in
  town, the ogres' middens and cooking pits only within 24 squares of their keep, `ROLE_SCENES["ogre_keep"]`);
  each theme still keeps to its own places and buildings.

### Spacing outdoors [SW-5]
Outdoor pieces keep Westwood's closest gaps (`kit/spacing.py`, p05 of each family's nearest; `py rules/spacing.py` re-measures
them on the campaign maps alone: every pair the kit names is at or under the campaign's p05 but sacks, 20 against 17): barrels 25 px, big
barrels 31, barrel and big barrel 33, crates 31, barrel and crate 38, sacks 20, sack and crate 33, sack and barrel 30,
racks 27, bedrolls 35, benches 45, headstones 39, a cart 48 from anything, a fire 50; other pairs 0.8 of both
footprints. The dressing, camps, wreck, door scenes and yards all place by it.

### Outdoor lights [SW-8]
Outdoors a light is a torch pole, a brazier, a street lamp or a fire (Westwood: TorchPole 497, wall Torch 974; no
candles). Nothing the player can pick up lies outdoors as decor (candles, lanterns, loose food without a script name).

## 5. Camps

**Recurring:** "a scattered mess" three rounds running [GW-4, SW-1, SW-3, AMR-1, AMR-2]. Never strew a camp's pieces by
hand in a design: use `kit/camps.py`. The checker's camp warnings (`check_exterior`: `exterior.camp_seat`, a stump by
a fire; `exterior.bedroll`, a bedroll away from any tent or row; `exterior.pile`, a heap of crates and barrels with no
purpose) and the crowd rules (`exterior.swarm`, `exterior.two_bodies`) catch what can be measured; the QA gate's spots
pictures show every camp for the rest.

- **Zones** (`camps.bandit_camp(spec, rng, land, centre, toward, loot, sleepers=, tents=, trade=, finds=)`), as
  Westwood lays its camps (Con03A, Con04a, War05A, Wiz02C, Wiz03b, Wiz03c): the hearth (fire, stones ringed 17-30 px
  round it, two log benches `OgreBench` and a stool 52-64 px out, the pot); the sleeping row behind it toward the top of
  the screen (tents in an arc 112-120 px out, two bedrolls before each, head to the tent); the store on one flank (one
  tidy row of sacks, crates, barrels and the water barrel at Westwood's gaps, the cart behind); the arms corner on the
  other (racks in a row 26-30 px apart, a straw dummy) or the dig (`trade="dig"`: tools in the ground, the tool barrel,
  spoil, `finds`); the lookout at the way in (a torch pole, a stool, quivers). Zones keep clear ground between them;
  the layout scales with the clearing (0.75-1.25).
- **Seats round a fire** are benches, stools and logs, never stumps [SW-3].
- **The site** [AMR-1]: `camps.camp_site(spec, land, near, ...)` takes the square with the most open ground clear all
  round, near the place, off its road; lay the camp open toward the road beside it (`StoryMap.road_near(site)`). A camp
  holds its ground: planting and dressing keep off it.
- **Urchins** squat as Westwood furnishes their dens (Con02a, War03c): `camps.urchin_camp` (beds of one kind side by
  side, a table ringed by stools, the pickings heaped) [AMR-2].
- **Ogres** lay their village as Westwood's Con05B: `camps.ogre_camp` (the fire pit with meat and a carcass, log
  benches and stools, straw bedding in an arc behind with the warlord's bearskin and chest, barrels and ogre sacks in
  a row with a big carcass, and the gate: two wings of tusk palisade along a screen diagonal, 33 px apart, every tusk
  and skull post with its shadow at Westwood's offset, the gate set where both wings stand whole off the road). It
  returns the bandit camp's record, so `posts.camp_posts` stands the ogres at their posts.
- Yards planned round the town keep off the foes' ground (a town field had hemmed Harrowby's ogre camp against the
  forest, AMR-1): filter their candidate centres away from the camps' areas.
- **The wagon wreck** (`camps.wagon_wreck`): a wheel off, the load thrown out in a fan, heavy things near.
- **Posts** [GW-5, SW-1]: `posts.camp_posts(spec, camp, toward, sit=, tents=, watch=, work=)` returns spots for the
  leader (by his tent and the take), at most two at the fire (Westwood: War05A's grunts 47 and 56 px out), the others by
  their tents, the store, the racks, the pot or the dig, the watch at the way in; 64 px apart, 28 px clear of every
  piece. A digger camp's workers work.

## 6. People and movement

- **Townsfolk never wander** [TW-9]: each walks a tour of the town's real places (`StoryMap.townsfolk`): home door,
  the square, a shop, the well, statues, benches, gardens, yard gates, neighbours' doors, 5-7 stops in a loop, different
  for each person, 16-24 s at each (plus up to 4 s). Tours stay outdoors and near the square and are laid when the
  scripts are written (`Behaviours.later`), once everything stands.
- **Legs follow the roads** [TW-9, GW-1]: `kit/walkways.Router` routes over cells a body stands clear on, road cheaper
  than grass, pulled straight into legs within 16 px of it (a waypoint at each bend, legs under 230 px). Waypoints on a
  tour are never linked (a linked waypoint makes Move roam).
- **Doorways square-on** [TW-1]: a point straight out, the opening's centre, a point straight in (`Ground.passage`);
  the router never routes through a door cell. Townsfolk step inside only unlocked shops, inns, chapels and smithies;
  elsewhere they stop beside the doorstep, 34-64 px out, never against the jamb. Garrison patrols go room to room the
  same way (`Dresser._route`).
- **The watch walks a beat** (`StoryMap.beat`): 6-7 stops across the town, 8-12 s at each.
- **Long walks are journeys** [GW-1]: the game's own path search gives up on a far goal and walks straight at it, so a
  story never sends anyone far with one Move. `StoryMap.journey(name, key, to, look=)` lays the walk along roads and
  paths and through unlocked doorways and gates square-on (`Router.route_far`); `A.walk(name, key)` starts it.
- **Nobody shares a spot** [GW-6]: every stop of every tour, beat and journey gets its own standing spot
  (`StoryMap._spots`), 40 px from every other spot and from every creature, 26 px clear of every doorway's passage
  points; beats prefer places no other beat takes; garrison patrollers get their own stops (`Dresser._own_rounds`).
- **A person waiting at a door** stands beside the doorstep, off the door's way: `StoryMap.doorside(role or building,
  toward=)`, never `outside_door` plus an offset [AMR-7]. Keep townsfolk's stops off a foe's ground with
  `StoryMap.keep_folk_away(centre, r)`.
- **Routes keep clear of people standing still, by construction** [AMR-7]: every tour, beat and journey is laid on a
  ground where each person who stands where they were placed (a giver, the gate's guard, a man on the road; not a
  shopkeeper, not a walker) is an obstacle (`StoryMap.standing`, `Ground.add_people`: legs pass 22 px off, over the
  checker's 18), so a route goes round them, and a journey ends at the first free spot it reaches round them. Only a
  walk with no way round at all falls back to the plain ground (and `routes.through_person` says so).
- **Facing** [SW-2]: every stop faces somewhere that makes sense (`kit/walkways.stop_facing`, applied by
  `Behaviours._facings`): a feature (well, statue, bench, stall, the gate a watchman keeps) is faced; a doorstep faces
  straight out, away from its building; a place on the square faces its middle; a step inside a shop faces into the
  room; otherwise the most open way. Then it is turned the least so nothing stands within 40 px straight ahead (22
  degrees either side), and within 34 px of a wall or building to within 80 degrees of straight away from it. In the
  game (`walker.face`) the walker turns on arrival and twice a second while it stands: toward the player within 110 px,
  back to the stop's way when they leave (townsfolk set Idle first, so the game's turn toward a bump is dropped).
- **In the game a walker never pushes**: the ticker (twice a second) judges progress toward the waypoint. Not nearer for
  1.5 s: at a stop it stands aside and takes its pause; at a bend or doorway point it goes on; elsewhere it gives way 1-3
  s and retries, twice. Townsfolk set out a few frames apart and run home along their own route.
- **Hostile groups stand apart** [GW-5, SW-1]: Westwood's grouped creatures stand 46 px from their nearest at p25, 71 at
  the median: `Population.creature` keeps every hostile creature 48 px from the others (`spread=False` for two
  prisoners in a cell, or a person's disabled twin, which stands exactly on his spot). Roused groups come at the player
  from their own sides, fanned 50 degrees apart, archers holding their ground (`spreadOn`); a pack lies up spread about
  its den.
- Townsfolk names follow the donor's body: Maiden clones are women (`story.is_woman`).

## 7. Story and scripts

A finished map is a story the player walks through; every creature is placed for a reason. Write the story in the
design's docstring before building, then plan the areas from it: each quest needs its places.

1. **The start and the hook**: the player arrives somewhere that shows what is wrong, and someone says where to go.
2. **The main quest locks the exit**: a wall across the road with a double gate (`StoryMap.gate_across`, LockType
   Mechanism), opened by the quest's end (`A.unlock`); the exit area beyond (`StoryMap.exit_to`) leads to the next map,
   which must exist (the exit reads its PlayerStart; build the chain from its end).
3. **Side quests**, each with its own place, giver and reward, sending the player across the whole map; one may offer a
   choice.
4. **Fights with a reason**: an ambush off a road (`q.near` + `A.hunt`), a camp with a sentry (`B.sentry`), a pack at its
   den, a room's keepers (`StoryMap.keepers`), a boss guarding a chest or dropping the quest item.
5. **Rewards** [TW-7]: items first, some gold (`A.give`, `A.gold`); story chests hold their loot (`items=`); 2-3 caches
   (`StoryMap.hidden_spot` + `camps.cache`); shops that buy and sell (`StoryMap.shops`). Every other container is filled
   at build time in Westwood's manner (`kit/loot.py`: every chest, about 40% of barrels, half the crates, coffins in
   crypts), within the map's gold budget of about 500-1500 (`rules/QUESTS.md`); the tally is `<map>.loot.json`.
6. **Everyone talks**: givers, guards, the watch and every townsperson, each with a line pointing at a quest and a new
   line once the main quest is done, with a Westwood portrait (`q.portrait`).

The tools: `kit/quests.py` (`QuestBook`, actions `A`) declares it all and `kit/behaviours/quests.go` runs it. Lines are
tried in order, later stages first. Conditions read the world where they can (`q.dead(names)`, `has=`), since a saved
game loaded with fresh scripts loses the script's own flags. Text goes in the map's string table
(`<Map>.strings.json`, written by `q.write_strings`), merged by `mapgen/strings.py` into `nox.csf.json`, which OpenNox
reads in place of nox.csf; keys are at most 31 characters; no audio. Objects a script names must be ones the game
registers by name (creatures, doors, exits, `ColorLight`, crystals, chests, signs; a `FireGrate` did not). Keep the
story's places open before the forest is placed (`StoryMap.keep_open`); after planting, `StoryMap.open_ways` takes out
the fewest trees or rocks that wall a target off.

## 8. What the engine needs

The kit does all of this; know why before changing it.
- **Gifts** [TW-11, TW-2, TW-3, TW-4]: `A.give` makes the item at the player's feet and picks it up three frames later.
  An object waits on the server's pending list until the frame ends; picking it up at once left it in the world and the
  pack together, and the next walk through either list looped forever (the freezes on a gift, on death and in fights).
- **Dialogue titles** [TW-6]: the dialogue window titles a creature with the string `NPC:<script name>`; every talker
  gets one (townsfolk get given names; `q.talker(..., title=)` overrides). The string table is shared by all maps, so a
  script name used in two maps carries one title (`mapgen/strings.py` refuses a clash).
- **The minimap** [TW-5, GW-3]: the game draws only the walls of the group of the polygon the player stands in, found
  by counting edges crossed on a line to the map's corner (0, 0) or (5888, 5888); it keeps the player in the polygon he
  stands in while it still holds him, else takes the first that does. `Spec.build` gives each map one polygon over the
  whole map, group 100, inset from the edges with its corners off that diagonal, bitten round any polygon the design
  lays itself (Rimehold's ice cave), so no spot lies in two (`nox._world_polygon`). **Recurring** (Greywatch had none;
  Rimehold's cave polygon had left it a minimap only inside the cave): `check_minimap` errs when the start lies in no
  minimap polygon.
- **Clones** lose their donor map's script hooks (ScriptEvents naming its functions).
- **Never place a `Zombie`**: OpenNox cannot read the map back. Map names are at most 9 characters.
- OpenNox alpha13 leaves TellStoryStr, quest status, JournalEntryStr/Edit, MakeFriendly and GiveXp unimplemented; the
  kit uses TellStory and JournalEntry by key with the map's own string table.
- The dedicated server never fires MapInitialize without a player, so a map's setup runs once, from MapInitialize or
  the 30th frame.
- When the game stops responding in a playtest build it saves a dump to `logs\freezes\<time>\` in the Nox folder.

## 9. Checks and review

**The gate.** A map goes to the user only after `py tests/qa.py <design> [seed]` passes. It runs, in order:
1. the build (builds run one at a time);
2. the checker (`validate/checks.py`, also run by every build): 0 errors, and every warning either fixed or accepted by
   the design with a reason in `QA_ACCEPT = [("<rule or check>", "<regex on the message>", "<why>")]`;
3. the scripts' compile against the game's NoxScript (`tests/check_scripts.py`);
4. the story: every talker's dialogue title, string keys of 31 characters or less, gifts picked up on a timer, the exit
   leading to a built map, every chest holding loot, the gold in budget, no Zombie, a name of 9 characters or less;
5. the room score (`review/roomscore.py`, by room type): rooms that miss it are listed to look at;
6. the exterior's empty ground (`review/exteriors.py`): over Westwood's 90th percentile for the map's environment fails
   (`review/exteriors_baseline.json`, from `py review/exteriors.py --westwood --save`), over the 75th is a look;
7. the pictures, in `review/out/<Name>/qa/` with `index.html`: the story map, the routes with each stop's facing,
   close-ups of every named story place, every room, the empty ground. Each comes with what to look for (the
   "review only" items of `review/FEEDBACK.md`); look at every one.

It never installs the map nor starts the game or the server. After it passes, the main session installs the map
(`mapgen/install.py`) and runs the server smoke test (`tests/server_smoke.py`), then the user playtests.

**The checker's rules.** Every finding names its rule (`checks.RULES`: `exterior.camp_seat`, `routes.facing`,
`identity.showpiece`, ...) and the feedback it answers. Errors are defects a player will see or hit; warnings are
departures from Westwood's range or from a house rule the playtests set. The rules by topic:
- walls, doors, kits, floors, the boundary, reachability and the story's gates (the engine and Westwood's construction);
- `minimap.*` [TW-5, GW-3]; `floors.threshold` [SW-4];
- `rooms.*` (size, cover, identity strays), `composition.*` (the cross-type room rules, bridges, docks across puddles)
  and `identity.*` (a room reads as what it is) [section 3];
- `routes.*` [TW-1, TW-9, GW-1, GW-6, SW-2, AMR-7]: waypoints and legs clear, doorways square-on, no shared stops, every
  stop facing open ground, tours of 4+ stops of 15+ s, nobody's route through a person standing still;
- `exterior.*` [section 4-5]: overlapping pieces, pieces on a fence line, pickable lights, crowds and swarms, docks,
  stumps as seats, strewn bedrolls, purposeless heaps, graveyards without graves.

**Keeping the checks honest.**
- A new rule gets a planted defect in `validate/selftest.py` (`py validate/selftest.py [case ...]`); a finding no rule
  names fails the self-test.
- A new rule is calibrated on Westwood's maps: `py validate/calibrate.py --dry` (how often each check fires there) and
  `py validate/checkcheck.py` (per rule: our 11 maps, Westwood's 107 campaign maps, the planted case; flags dead rules, rules firing
  on more than a quarter of Westwood's maps, unnamed findings). A rule that fires a lot on Westwood is either narrowed
  or kept as a stated house rule (the playtest's word over Westwood's habit, as with torches indoors).
- A new piece of feedback gets a line in `review/FEEDBACK.md`: the rule here that answers it, and the check, or the
  picture and what to look for when it can only be judged by eye.

**Review and playtest.** `review/review.py` (the sheet beside the 3 most similar Westwood maps, scored with
`review/RUBRIC.md`, recorded in `review/reviews/`), the room lab (`mapgen/designs/roomlab.py`) and building lab
(`mapgen/designs/buildinglab.py`) between playtests; then the user's playtest, whose numbered feedback goes into
`review/FEEDBACK.md` with its date and map.
