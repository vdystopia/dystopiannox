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
- **Docks** [DV4-1, AM-2] (`rules/scenes/pond_dock.md`): a dock stands on a lake, on the shore nearest the road, and
  runs out square to the shore (within 20 degrees of the shore's normal read over ten cells, the checker's ring) into
  open water: water two tiles to either side all along it and three tiles round its tip (`Waterworks._shore_start`;
  `dock(body, "best")` prefers the long DockDown run, DockUp only where it lands much nearer the road). The fishers'
  gear on the bank by its root (`_dock_gear`: barrels touching, a crate or a rock). Reeds grow only in the shallows.
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

### Transporters: lifts, stairs, portals, passages [TR-1]
Every transporter moves the player from a spot A to a spot B, and B is most often a place that cannot be walked to: a
Nox map has one floor, so a cellar, a mine level, an island or a tower floor is a walled-off area drawn in an empty part
of the grid (Westwood: 98% of its lifts, 86% of its pads; `rules/TRANSPORTERS.md`). The process is
`skills/nox-transporters/SKILL.md`; one call lays any kind (`kit/transport.Transporters.add(kind, a, b, name)`):
- **The kind by the setting**: a lift in mines, caves, sewers and pits (CaveElevator with its base, Elevator in the
  mines, GreenElevator in Ix and swamps, WhiteElevator in a castle, LOTDElevator, RedElevator at the volcano); stairs
  between a castle's, Dun Mir's or a crypt's floors; a pentagram for magic places and islands; a passage (the screen
  fades out and in) for a door or tunnel mouth into an inside drawn elsewhere.
- **The far place first**: its own walls, floor, light and purpose (`serves=`: the chest, the boss), then both ends on
  open floor, 23 px or more from a wall; stairs down in a room's west corner, stairs up against its NE wall, as
  Westwood's.
- **Never land the player on a pad that leads on**: a lift is two-way by itself; a two-way portal or stairs is two
  one-way pads, each landing 59 px (Westwood's median) beside the other's pad (Westwood links no two pads both ways).
- **A way back or the map's exit** from every landing, unless the story leads on from there; a transporter that opens
  with the quest is laid `enabled=False` and turned on by `A.enable` (Westwood's exit lifts, Con01A).
  The checker's `transport.*` rules catch the rest (section 9).

### Yards [AM-1, SW-9]
Yards with a purpose (`kit/yards.py`: graveyard, quarry, orchard, park, field, monument, jail) are planned before the
land is carved (`yards.plan`, `yards.plan_any`) and built after its walls (`yards.build`), each fenced in Westwood's
material for it with a gate facing the town.
- A fence point (p, q) is drawn at square (p, q - 0.5): a plot's fence runs gi..gi + w across i and
  gj - 1.5..gj + h - 1.5 across j (`Yard.centre` is its middle). Everything in a yard or garden stands inside that,
  its drawn half-width plus a margin off the line (`spacing.off_walls`); crop rows are centred with a walkable strip
  to the fence all round. Nothing stands on a fence or wall line, ground bits included.
- A household's garden (`Village.garden`, `rules/scenes/garden.md`) is two or three beds side by side, a different crop
  in each, two rows to a bed ~20 px apart, a grass strip between, on grass or dug earth; the water barrel and a spade
  at the path's ends; mostly unfenced, a few behind Westwood's low wooden fence (Dilapidated), never Log (a cabin wall).
- A graveyard has graves (`yards._graveyard`, `rules/scenes/graveyard.md`): its ground sparse grass (GrassSparse2);
  headstones in rows on the grid's lines ~90 px apart (Westwood's nearest), a third of the plots dug earth, flowers on
  some; the gravedigger's corner away from the gate in most yards (an open grave, the coffin, the spade, a bucket of
  tools, a torch pole); a stone pillar either side of the gate; a tree or two by the fence, never among the graves; no
  bench. Westwood has no grave-mound object: its headstones stand on grass and bare earth (War03b-d).

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

### Room shells: shapes, partitions, floors and carpets (2026-10-05, the shells night)
The room lab's judges and every room-tuning track found the shell the biggest giveaway once the furniture improved:
our rooms were rectangles on one floor, carpeted wall to wall. `py rules/rooms/shells.py` measures every built room of
the campaign maps (308, each layout once; 231 typed by `rules/rooms/westwood.json`) into `rules/rooms/shells.json`, and
`kit/shells.py` draws each room's shell from its type's numbers (its size band's when the type has under 8 rooms),
from its own generator, so the rest of a building draws as before (`NOX_SHELLS=0` builds the old shells, to compare):
- **Shape** (`shape_rooms`, run by `building._build`): two rooms in three are rectangles; 15% have a bay or alcove,
  8% are L or T, 10% more broken; larger rooms less often rectangles (under 30 tiles 82%, 80-200 tiles 41%). By type:
  bedrooms 80% rectangles (12% L, 7% bays), storerooms 73% (27% bays), living rooms 73% (20% bays), halls 41%,
  crypts 67%. A room drawn otherwise gives a corner to the room beside it (an L) or takes an alcove
  from the room beside it; every room keeps one piece, its least size, its proportions and its place in the size
  order; the entrance's facade, throne rooms and chapels stay as they are, and the outline is the footprint's (a notch
  to the outside had opened a way round Thornwick's locked gate). Rooms are shaped against a budget per building
  (an alcove bends the room it is taken from too).
- **Partial partitions** (`spur_points`): a wall spur 1-3 points long from the middle of a wall, two units of floor
  beyond its tip: 5% of rooms, 15% of those of 80-200 tiles, a third over 200. Free-standing wall pillars: 1% (none
  generated; pillars are furniture).
- **Floors with a purpose** (2026-10-06, after independent judges read our second floors as "brick squares scattered
  with no relation to the tombs", "corner patches that serve no purpose", "a brick band along one wall" and our throne
  rooms' planks as "a town hall"). `py rules/rooms/shells.py` now measures only the curated rooms
  (`rules/rooms/curated.json`: 179, the void-bounded throne halls included) and, for every second-floor piece and
  carpet, what stands on it and beside it, how far it lies from a door, its share on the edge ring and in a wing
  (`zone_measure`, `zone_of`; `second_purpose`, `carpet_purpose`, `focal_rate`, `focal_pairs`, `main_family` in
  shells.json). What Westwood's are for:
  - **a hearthstone** under the fireplace or stove: 27 of the 33 rooms with one (living rooms 12 of 14, studies,
    kitchens, dining and great halls), 1-3 squares along the wall, RedBrick on planks, Redbrick3 on GalavaBrick;
  - **a plinth under each tomb**: 25 of 29 rooms with tombs (crypts 23 of 25): 1 by 2 squares of GalavaBrownMarble or
    BlueBrick3 under each sarcophagus on GreenBrick, a band under a row of them, or dirt worn round them;
  - **the throne's dais and the aisle to it** (throne rooms: the runner from the door, 93% of their carpet; the Lich's
    dais); **the floor under the bar** (2 of 5 taverns);
  - **carpets under the seating and the tables** (great halls 88%, taverns 90%, living rooms 56%) and **at the bed**
    (bedroom carpets 81% at the bed: 23 of 46 rooms with a bed); a chapel's under its pews;
  - a wing or alcove on its own floor (living rooms 15%), a border round the room (crypts 15%, cellars); worn floor by
    the doors of cells and guardrooms (not laid yet).
  - **Main floors by type**: crypts stone (GreenBrick 23 of 25), cells stone, chapels and throne rooms stone or
    marble, bedrooms half stone half wood, living rooms two thirds wood. Never planks in a throne room, a crypt or a
    chapel.
  The kit now: `building._build` gives each room, once its type is settled, a floor of a family Westwood lays in that
  type (`shells.fit_floor`: the style's fitting floors, else Westwood's own; the type's floor where Westwood lays one
  in 60% of its rooms, GreenBrick in crypts, unless the style's floor is a culture's own, LOTD or Dun Mir), its second
  floor redrawn for the new floor; `floor_pattern` lays before furnishing only the zones that follow the shape (a wing
  two units deep or more, a border; `zone_odds`: the type's floor_touched times the share of its second floors that
  are those); after furnishing `originality.furnish_original` calls `shells.lay_zones`, which lays the hearthstones (the square under the fireplace and the one before it, where Westwood's lies: ours stand on
  the ring, Westwood's in the wall line; one along the wall more often than not),
  tomb plinths, the throne's dais and the bar's floor at Westwood's rates, in what Westwood lays there
  (`zone_material`), on the main floor only, three cells off every door, never on a carpet or its trim; and
  `furnish.lay_carpet`'s middle carpet goes where `shells.carpet_offset` puts it (at the bed's foot in a bedroom, under
  the seating and tables elsewhere). The strips along one wall, the scattered patches and the inlaid squares are laid
  nowhere. The partner is never one Westwood keeps apart from the main floor or from the town's grass (`ground_shy`);
  two tiles clear of every door; blended where Westwood blends the pair (`blend_pattern`, `nox.Spec.pattern_tiles`).
  The shapes and partitions still draw from the numbers of 2026-10-05 (`rules/rooms/shells_shape.json`): measured on
  the curated rooms they reshape every map's rooms, and Thornwick's north gate could then be walked round (the forest
  beside it moved); re-measuring them is left to the shells owner. A floor refitted to GreenBrick leaves two hard
  GrassNorm/GreenBrick seams (warnings) at Thornwick's chapel crypt.
  The shell AUC (`--lab`) reads three more features: the share of the floor in purposeless zones, a zone at a focal
  piece, a plank main floor.
- **Carpets** (`furnish.lay_carpet`, `CARPET_FULL`): never on the room's outer ring; a small room's carpet is its floor
  less that ring (4 squares across: 3 in 4), a larger room's 2-5 by 3-8 squares placed by `shells.carpet_offset` (8 or
  more across: 1 in 10 wall to wall); a quarter to a third of the floor.
- Doors: Westwood's rooms have one door in two (bedrooms 70%, storerooms 77%), placed 0.3-0.45 of the way along their
  wall, one in seven a unit from a corner.
Measure a lab iteration's shells against Westwood's: `py rules/rooms/shells.py --lab <type> <iter>` (side by side and
a shell AUC); a built map's: `--maps <map> ...`. Tonight's lab (seed 1, iterations `shells0` and `shells`): the shell
AUC went bedroom 0.85 to 0.75, storeroom 0.89 to 0.82, living room 0.88 to 0.80, hall 0.99 to 0.94, crypt 0.99 to
0.78; the furniture AUC barely moved (it reads no shell feature). What still gives the shells away: the lab's own
doors (its schedule gives 1-3, Westwood's rooms mostly one), halls' floors (Westwood's halls mix floors patchily) and
Westwood's irregular halls (rooms run together through openings). The five designs' rooms went from 93-97% rectangles
to 41-83% (Westwood 67%), a quarter to two fifths with a second floor. The checker's threshold rule now looks only
within 4 cells of a door (a room's own second floor further in may share a material with the ground).

### Thresholds [SW-4]
A room's floor runs under its walls (to the wall line on a SW wall: TW-12 below) and out onto the doorstep; the ground
blends onto the doorstep, never onto a tile that reaches into the room (`Spec._wall_line_floors`,
`Spec._door_thresholds`, `Spec._edges`; the rooms' tiles are `Spec.indoor`). The room's own floor, never a carpet laid on it, and never next to a floor Westwood keeps from it
(`Spec._may_take`). Door paths use Westwood's buffer floor where a path may not touch the room's floor
(`Land.connect_door`).

### No blending at a wall [TW-12]
A wall is a hard cut between floors: no edge piece is drawn across it, on either side, whatever the wall (a house, a
yard's fence, a town wall, the forest wall). The user (Thornwick, 2026-10-08, of a soft grass edge along the outside of
a house's wall): "There does not need to be blending on a wall. The wall cuts off vision from the inside out and from
the outside in. It's also a natural transition point in itself. Therefore, this kind of transition must never be used."
- A / wall lies on the seam between two tiles: the cut is at the wall. A \ wall runs through the middle of the tiles
  on its line: the cut falls half a tile from it, between the line tile and the tile beside it, and stays hard.
- `nox.wall_seams` finds every pair of tiles (side or tip neighbours) whose centres' line a visible wall piece touches
  (not merely runs along); `Spec._edges` draws no edge across them. Invisible walls (the water's shoreline) are not
  walls here, and a doorway is an opening: the ground still blends onto the doorstep [SW-4].
- Westwood agrees for solid walls: across a Cobblestone, Log, StuccoLightWood, StoneGray, Dilapidated or GalavaTownWall
  wall it blends 1-9% of the seams on a / line and 7-10% on a \ line; across natural walls (forest, cave) and iron
  fences it blends about half, which this house rule overrides (the check fires on every one of Westwood's campaign
  maps: a stated house rule, the user's word over Westwood's habit).
- A \ wall's line tile takes the floor in front of the wall (below it on screen), as Westwood's do: the ground on a
  room's SW wall, the room's floor on its NE wall (`Spec._wall_line_floors`). Each side's floor then runs up to the wall
  as seen, and the wall's picture covers the half tile behind it; giving the line tile the room's floor on both walls
  had laid a strip of boards half a tile wide along the outside of every SW wall (Thornwick's inn).
- Checked by `floors.wall_blend` (an error; planted case STwallb): a map with an edge piece across a wall fails the gate.

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
- **Lights** [TP1-5, DV4-5, DV6-2]: houses are lit with candelabras and the hearth, never an open torch; lights stand
  where Westwood's do (the placement grammar below), at least 3 units apart, never before a chest, hearth or stove
  however it was placed (`Furnisher._before_anchor`, measured as `composition.anchor_blocked` measures it) [DV5-4].
- **The placement grammar** (2026-10-06; the fair blind judges' faults across ~40 sheets, every type, both engines:
  `review/NIGHTLOG.md`). `py rules/grammar.py` measures Westwood's curated campaign rooms (176 rooms, seen as the checker
  sees ours) into `rules/out/grammar.json`; `mapgen/kit/grammar.py` holds the rules, and both furnishing engines run its
  `audit` as their last pass (each fault moved into place, else dropped; must pieces never dropped). Westwood's numbers
  (house rooms):
  - *lights*: 86% within a unit of a wall; 43% beside a piece they light (shelves 27, supplies 9, chairs 8, benches,
    tables, desks), 39% in a room corner, 7% beside a free piece, 6% alone along a wall, 4% free; none at a bed's foot,
    4 of 140 on a carpet; nearest pair p10 6 units; 37% of house rooms have a floor light at all (bedrooms p50 0, p90 3).
    Rule: a floor light stands by a wall, in a corner or beside what it lights (or flanking a door); never free, on or at
    the edge of a carpet, at a bed's foot, within 3 units of another, or third along one wall; at most the type's p90.
  - *table sets*: 59% within 2 units of a wall, 23% on a carpet, 2% by the hearth, 17% free (mostly great halls,
    barracks, libraries in rows). Rule: a table more than 2 units from every wall stands on a carpet or rug, within 3 of
    the hearth or bar, or in a hall's row; never at a bed's foot or square before the hearth (in the way to the fire).
    A floating set moves whole to a back wall, else a carpet is laid to it, else it goes. Chairs: 9% of Westwood's stand
    away from a table, desk or hearth (bedrooms 0 of 23): a chair is drawn up to something.
  - *lone pieces* (no piece within 0.9 units): exposed (in the open or on a front wall) supplies 15%, chests 2%. Past
    that share a barrel, crate, chest or clutter piece joins a group of its kind by a back wall, or goes.
    Benches: 22% of Westwood's stand alone in the open; past that a bench goes back to a back wall. A column alone
    (no other within 6 units) goes. Stock heaped wholly off the walls only in stores of 60 tiles or more.
  - *gaps along walls*: walls of 3+ pieces with real gaps have a CV of the gaps p50 0.66 (22% under 0.2). Rule: no wall
    of standing pieces or of hangings at even gaps (CV under 0.2), no three of a kind in an evenly stepped diagonal, no
    kind alone one to a corner, no pieces ringing a centre at one radius and even angles (four chairs at a table's
    quarter points, straw round a fire); a stock piece slides against its neighbour (a heap).
  - *wrong pieces*: plants only in types whose Westwood rooms hold them (a gallery; none in 175 other rooms). A face
    (hearth, stove, shelf, desk, chest, workbench) on a front wall moves to a back wall.
  - *stamps*: no two knots (small pieces, or a table with its seats) of the same kinds in the same shape in one room
    (a twin loses a seat or a piece); beds and tombs of one kind to a room.
  - *the way to the fire*: no table or bench square before a hearth within 3.4 units (a bench is drawn up beside it).
  **Round two** (2026-10-06, night-grammar2: what the judges still named on the g3 sheets; `rules/out/grammar.json`
  `round2`, measured on the 116 curated house rooms the same way as ours; `py rules/grammar.py labstats <types> <iter>`
  prints the same numbers for a lab batch, `py rules/grammar.py lab <type> <iter> [-v]` its faults):
  - *strings of singles*: three or more lone pieces in a row along one wall, each 0.5 units or more from the next
    (bookcase, chest, bookcase; three crates none touching; workstations between candelabras; a unit is a run of
    pieces under 0.35 apart, a piece with its candelabra, never a desk with its chair). Westwood: 7 of 116 rooms (none
    longer than 4); ours 20% (q0). Repair: a unit slides along the wall against its neighbour, its own kind first (a
    run of shelves, a heap of stock), until no three stand apart; else a stock piece of the string goes. Seats, tables,
    desks, beds, the bar and fires never slide, nor does anything slide against a fire (the checker's hearth room and
    seated tables keep). Kin standing
    apart on a wall was measured too and is not a rule: Westwood stands 21 of its 73 kin pairs apart, ours 13 of 48.
  - *front walls by category*: the share of each category's wall pieces on a front wall only (SE, SW): supplies 27%,
    workstations 29%, smiths' pieces 25%, statues 18%, beds and cots 15%, clutter 14%, racks 11% (tables, chairs and
    benches 49-62%, the bar 50%, shelves 43%: not judged). Past floor(share x n) a piece goes to a back wall (stock into
    a heap there, a cot or rack turned to its new wall); stock that fits nowhere stays.
  - *front lights*: 29% of Westwood's floor lights stand by a front wall or in the front corner; past that share
    (rounded to the nearest light: none of one, one of two to five) a light moves to a back-wall spot, else goes.
  - *loose pieces with a face*: desks (Westwood: 1 of 33 alone in the open or on a front wall), racks (20%),
    workstations and fairy jars (21%; jars 2 of 11 in the open) join the lone-piece rule: past the share each goes to a
    back wall beside its own kind, else goes (the "lamp post mid-shop" was a FairyJar). Never the shop counter (its
    keeper stands behind it: `identity.keeper`). Stock that joins no group goes to a back wall before it goes.
  - *broken groups*: tables with no seat drawn up, past the type's Westwood share (guardroom 15%, tavern 5%, barracks 11%,
    living room 32%, bedroom 50%; only the types with 5+ Westwood rooms; rounded to the nearest table, so a bedroom's
    one table may stand bare), get one or two seats (`Furnisher.seats_around`; never at a bed's foot; a last seat pass
    after every other move);
    sets of three or more matching chairs all one distance off the table (Westwood: 11 of 54 sets; ours 20 of 30) have
    one or two chairs pulled out 0.25-0.6 units, never past 1.0 from the table (Westwood keeps one kind of chair at 76%
    of its sets, ours 83%: not changed). A twin set's seat goes round to another side before any seat is dropped.
  - *every move* keeps a stove or cauldron 0.87 units from the hearth (validate/checks.py hearth_crowded), and stock
    rehomed never lands where its nearest wall is a front wall.
  - *carpets*: a carpet a square or more from every wall with nothing standing on it and no bed's foot at it (Westwood: 6
    of 61 carpets; 52 of 61 touch a wall, laid to the room's shape) is lifted (`Furnisher.carpet_undo`, `lift_carpet`)
    and laid again at the bed's foot or under the seating (`kit/shells.py carpet_target`), else taken up. Westwood's
    carpets are not smaller than ours (p50 45% of the floor), so size is not a rule.
  - *one trade to a shop*: potion (potion shelves, bookcases, fairy jars, star charts, cauldrons), steel (steel crates
    and barrels, tool barrels, crates, sacks), arms (the trader's racks and hung arms). Westwood's 8 curated shops: 7
    sell one trade, Con07B keeps one potion shelf among its arms; ours 1-9 odd pieces a shop (q0). Past one odd piece a
    piece becomes one of the main trade's (Westwood's pieces of the trade, nearest its size, turned to its wall) where
    it stands, else goes.
  - *the halls' table sets* (taverns, dining halls, great halls of 100+ tiles): the widest stretch of floor with no
    piece on it at most Westwood's widest (8 halls of 104-216 tiles: 3.4-5.7 units; ours 4.0-8.0, q0): a set from the
    crowded part moves whole with every seat onto a carpet laid in the bare stretch (Westwood's free hall tables stand on
    carpets; a room with a carpet keeps it), else it goes back; no three sets in a straight or diagonal row in a tavern or dining hall (Westwood: 1 in 9 rooms).
  `NOX_GRAMMAR2=0` runs the first round alone (the before of every comparison). The lab's numbers (merged master,
  seed 1, 10 rooms a type, faults as rule x room with every rule above) are in the commit that brought round two.
  What the audit drops is made up against the walls by the recipe's top-up, then audited again. `NOX_GRAMMAR=0` turns
  the audit off (for comparisons). The checker warns (`composition.grammar_*`) only where Westwood's own curated rooms
  almost never reach (`checks.GRAMMAR_MIN`; each rule fires on 0.6-6.8% of Westwood's 176 rooms, any of them on 22%);
  planted cases `STg*` in `validate/selftest.py`. Not covered here: one template repeated across variants of a type
  (a recipe's or the motif library's matter), and the shells' floor patches.
- **No loose food** [TP1-1]: Nox draws items at floor level; a table that carries its food (`RoundTableWithFood`).
- **Every piece by what Westwood does with it** [HB-1..HB-5] (2026-10-05, the Harrowby playtest: "Do a pass over all
  objects and try to understand better how they fit in the world"). `py rules/objects.py` measures every kind of piece on
  the campaign maps' rooms and walls (each layout once) into `rules/out/objects.json`: category, footprint, where it stands,
  runs of one kind along a wall, counts per room by type, the nearest piece of every category, what never stands next to
  it, what hangs above it. `kit/objects.py` turns it into rules and `Furnisher._kb_ok` holds every placement to them
  (recipes, fill, top-up, groups, set pieces alike):
  - *showpieces* stand once (a desk, an alchemist's desk, bellows, a telescope; a hearth twice only in a hall of 240
    tiles, or as many as the type's Westwood rooms hold: an observatory's three telescopes); one cauldron a room; chests by
    the type's p90 (a bedroom 1, a chamber of 100 tiles 2, a treasury 3); a bedroom one table or desk with its chairs;
    tables in private and work rooms by the type's p90; statues by the type's p90, a pair at least; torture racks,
    stocks, iron maidens, gears and winches, monuments and fountains by the most the type's evidence rooms hold
    (`kit/roomtypes.py` evidence: the miner names those rooms by their type);
  - *fabric* lines walls (bookcases, a bench of workstations, trader's shelves, straw); everything else stands alone or
    in runs no longer than Westwood's (log shelves 2, barrels 3, chests and statues 1) and never down a whole wall
    (shelves and racks 2 to a wall, supplies 3, statues 2);
  - *clearances* by category pair: 0.8 of Westwood's p5 where it keeps a pair 0.9 units apart or more, and the
    playtest's floors: a bed or a chest 2 units from any fire, a chest 3 from a hearth, a bench 1.2 from a bed, statues
    2 apart unless a deliberate pair flanking something; and Westwood's "never next to" (a bed never beside supplies,
    a table never beside a hearth);
  - *hangings* take bare wall, never above a piece standing against it (Westwood: 0-3%), two of one trophy or painting
    to a wall at most; *candelabras* by the room's size (2 under 40 tiles, 3 under 100, 4 under 200, then 5);
  - *supplies in clusters*, not lines: 1-5 pieces of mixed kinds (sacks of three sizes, then a barrel, then a crate)
    0.2-0.4 apart, 1-4 units of bare wall between clusters (the groups had been laid 0.12 apart, under the 0.15 a fit
    keeps, so every second piece failed and walls took single sacks spread evenly);
  - a chest on a wall between a door and the end of a row of shelves stands centred between them
    (`Furnisher.centre_by_doors`).
  The recipe's hangings go up right after its composition, before the fill lines the walls, so they keep their bare
  stretch. Before and after on the playtest's own rooms: `py mapgen/designs/hbreplay.py` rebuilds them wall for wall from the
  played map and furnishes them again.
- **A room reads as what it is** [SW-6, SWR-1, TW-8, AMR-4] whatever its type: the checker's room-identity warnings
  (`check_identity`) catch a showpiece repeated, a stand-alone piece four or more times along one wall, supplies lining
  a wall outside a store, one kind filling a big room, more free tables than the type sets, a shopkeeper not behind his
  counter and a throne that does not face its door.
  **Recurring:** repeated pieces lining walls came back after a fix; these warnings now fail the QA gate unless the
  design accepts them with a reason.

## 4. Outdoors and scenes

**Per-scene briefs** (purpose, anchor, zones, must/may/never, spacing against Westwood, mistakes): `rules/scenes/`
(bandit camp, graveyard, garden, pond and dock; `rules/scenes/README.md` ranks every scene type with Westwood's
evidence). They are measured and tuned in the scene lab: `py tests/scenelab.py <scene>` lays ten variants with the
kit's real code and judges them against Westwood's campaign scenes by numbers and by eye (`review/scenelab/README.md`,
the iteration log `review/scenelab/LOG.md`). Change a scene's code with the lab open, and run the maps that lay it.

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

- **Zones** (`camps.bandit_camp(spec, rng, land, centre, toward, loot, sleepers=, tents=, trade=, finds=)`;
  `rules/scenes/bandit_camp.md`), as Westwood lays its camps (the scene lab's 20 campaign camps: Wiz03a, Wiz03b,
  Con03A, Con04a, War05A...): the camp backs onto a wall (the wood's edge, the cliff); the hearth (fire, stones ringed
  17-30 px round it, one log bench `OgreBench` behind it, a stool sometimes, a pot rarely); the sleeping row along the
  back wall (each pup tent with its bedrolls beside it, sleepers in pairs 44 px apart, never one alone, an uneven
  rhythm, a torch pole at its end, the leader's awning in the middle with three or more tents); the store on one flank
  against the wall (barrels touching, crates in a pair, one kind of each, a cart sometimes); the arms on the other (a
  rack or two and a polearm rack) or the dig (`trade="dig"`); the lookout at the way in (a torch pole); a rock outcrop
  at the row's end. Typed pieces may stand snug to a wall (`spacing.off_walls`). The layout scales with the clearing
  (0.75-1.25).
- **Seats round a fire** are benches, stools and logs, never stumps [SW-3].
- **The site** [AMR-1]: `camps.camp_site(spec, land, near, ...)` takes a square with open ground clear all round for
  `room - 1` squares and, among those, the one whose nearest wall is nearest (a camp backs onto the wood or the cliff,
  never floats in a wide glade), near the place, off its road; lay the camp open toward the road beside it (`StoryMap.road_near(site)`). A camp
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
   line once the main quest is done, with a Westwood portrait (`q.portrait`), in a voice of their own (below).

The tools: `kit/quests.py` (`QuestBook`, actions `A`) declares it all and `kit/behaviours/quests.go` runs it. Lines are
tried in order, later stages first. Conditions read the world where they can (`q.dead(names)`, `has=`), since a saved
game loaded with fresh scripts loses the script's own flags. Text goes in the map's string table
(`<Map>.strings.json`, written by `q.write_strings`), merged by `mapgen/strings.py` into `nox.csf.json`, which OpenNox
reads in place of nox.csf; keys are at most 31 characters; every line said in a dialogue window is voiced (below).
Objects a script names must be ones the game
registers by name (creatures, doors, exits, `ColorLight`, crystals, chests, signs; a `FireGrate` did not). Keep the
story's places open before the forest is placed (`StoryMap.keep_open`); after planting, `StoryMap.open_ways` takes out
the fewest trees or rocks that wall a target off.

### Voices [VO-1]
Every line said in a dialogue window is voiced, as Westwood's are (965 of its 1391 campaign strings: the talk lines,
shop greetings and refusals; never signs, journal entries, hints, dialogue titles or mission banners). `mapgen/voice.py`
does it, run by `Spec.build` after the scripts (`NOX_NOVOICE=1` skips it while trying seeds; a `VOICE` line reports it):
- **What is spoken**: each talker's lines, each shopkeeper's greeting, and what `q.tell(giver, text)` has a giver say
  when a talk ends. A refusal is `q.tell` (Westwood's "Fine then, don't return my magical staff!" is a second TellStory
  in a window of its own; `q.errand` tells its refusal), never `A.chat`: text over a head or on screen (`A.chat`,
  `A.print`) has no string key and stays silent, and the QA gate lists a refusal said over a head as a LOOK.
- **Who speaks with which voice** (`voice.cast`, the same cast every build): a part from the body, the portrait and
  what the title and the map's text call the speaker (a Maiden clone or a woman donor a woman; "Father Odo" or
  GalavaPriestPic a priest; "Old Brannoc", "Reeve Aldric" or TheogrinPic an elder; Warrior and IxGuard portraits and the
  watch guards; MorganPic a rogue; shopkeepers merchants; ogres brutes); then Kokoro's best voice for the part that the
  map has used least, the speakers with most lines choosing first, blended 3:1 with a partner, at a pace of its own
  (elders and priests 0.86-0.93, rogues to 1.1). A character on two maps keeps one voice when the designs pin it:
  `q.talker(name, lines, voice="bm_george")` (a part, a Kokoro voice, or `{"mix": [[voice, weight], ...], "speed": s}`).
- **The sound**: Kokoro v1.0 (82M parameters, Apache-2.0) through kokoro-onnx on the CPU: local, no paid API, no key.
  It lives in its own venv, installed once per PC by `py mapgen/voice.py fetch`; `mapgen/voice.lock.json` pins the
  packages pip resolved and the model files' SHA-256 (the first fetch writes it: commit it); the model, venv and
  cache are build tools in `.tools/voice/` (`NOX_VOICE_HOME`), never committed, and so are the waves (`mapgen/out/`).
  The text as spoken: line breaks run on, Westwood's " -- " is a pause, shouted words are not spelled out. Mastered as
  Westwood's PCM dialogue measures: about -16 dBFS while speaking, peaks bent under -1 dBFS, a 30 ms lead and a 150 ms
  tail; written PCM 16-bit mono at 22050 Hz. A cache keyed by text, voice, model and mastering makes a rebuild instant.
- **Where it goes**: `<out>/<Name>_dialog/<wave>.wav` and `<Name>.voice.json` (key, wave, speaker, voice, the text as
  spoken and its hash). Wave names are 8 characters as Westwood's 8.3 ones: two letters of the map, two of its crc32 in
  base 36, the line's number and "e" (Thornwick's `th9a001e`). `mapgen/install.py` copies the waves into the game's one
  `Dialog\` folder, takes out the map's old ones and refuses a name of Westwood's or another map's; `mapgen/strings.py`
  gives a line its wave (`str2`) only while the installed wave was made from the line's present text. The scripts do
  not change: TellStory passes no sound, the voice is the string's.
- Try a voice: `py mapgen/voice.py say "Well met, stranger." --voice elder`; a built map's cast: `py mapgen/voice.py
  cast mapgen/out/<map> <Name>`; voice a built map again without rebuilding it: `py mapgen/voice.py voice
  mapgen/out/<map> <Name>`; the offline tests: `py tests/voice_test.py`.

## 8. What the engine needs

The kit does all of this; know why before changing it.
- **Gifts** [TW-11, TW-2, TW-3, TW-4]: `A.give` makes the item at the player's feet and picks it up three frames later.
  An object waits on the server's pending list until the frame ends; picking it up at once left it in the world and the
  pack together, and the next walk through either list looped forever (the freezes on a gift, on death and in fights).
- **Dialogue titles** [TW-6]: the dialogue window titles a creature with the string `NPC:<script name>`; every talker
  gets one (townsfolk get given names; `q.talker(..., title=)` overrides). The string table is shared by all maps, so a
  script name used in two maps carries one title (`mapgen/strings.py` refuses a clash).
- **Dialogue voices** [VO-1] (verified 2026-10-08 on the GOG install and opennox.exe): a string of the table carries a
  wave name beside its text (nox.csf's STRW entries, 1415 of Westwood's; `str2` in OpenNox's nox.csf.json), and when a
  dialogue window shows the string the client streams `Dialog\<wave>.wav` (`"dialog\" + name + ".wav"`, AudDiag.c).
  Westwood's scripts pass no sound to TellStory (the decompiler's "SwordsmanHurt" is sound 0). OpenNox replaces Miles
  with its own stream reader, which decodes PCM, IMA ADPCM and MP3 in a WAV; Westwood's 1254 waves are 1246 MP3 at
  22050 Hz mono and 8 PCM 16-bit mono at 44100 Hz (W1CAP12E, the wizards' airship captain), all 8.3 names of 7-8
  characters (keep ours there). The Dialog folder is the game's, shared by every map: a map's voice cannot travel in
  its own folder or its .map (a multiplayer client downloading a map would get no voice; our maps are solo). The
  dedicated server plays no sound, so its smoke test proves the strings and scripts, not the voices: only a playtest
  hears them.
- **The minimap** [TW-5, GW-3]: the game draws only the walls of the group of the polygon the player stands in, found
  by counting edges crossed on a line to the map's corner (0, 0) or (5888, 5888); it keeps the player in the polygon he
  stands in while it still holds him, else takes the first that does. `Spec.build` gives each map one polygon over the
  whole map, group 100, inset from the edges with its corners off that diagonal, bitten round any polygon the design
  lays itself (Rimehold's ice cave), so no spot lies in two (`nox._world_polygon`). **Recurring** (Greywatch had none;
  Rimehold's cave polygon had left it a minimap only inside the cave): `check_minimap` errs when the start lies in no
  minimap polygon.
- **A long level forest edge crashes the client** [CL-1] (2026-10-08: the voiced Thornwick crashed OpenNox as it
  loaded; the voices were not the cause). OpenNox v1.9.0-alpha13 blacks out what the player cannot see one screen row
  at a time; a row that crosses the edge of his sight 31 times or more panics the client on the spot (client_draw.go
  sub_4C5500, "index out of range [1] with length 1", on stderr only: the log just stops). A forest edge running straight
  across the screen is a saw of wall pieces whose valleys all sit on one row; seen from a few hundred pixels above or
  below, a long one gives 40-48. Thornwick's roads east had them (the 10-05 build too, out of the start's sight); 4 of 5
  such points crashed the client, none after the fix. `Land.apply(..., unlevel=True)` (`Land.unlevel_edges`) breaks
  every level run of the edge longer than 2 squares into V bays with 45-degree sides, into the forest, or into open
  ground along a narrow band of forest; Thornwick uses it. The gate's sight step (`tests/sightrows.py`) estimates the
  worst row from every point of the floor and fails a map at 33 (the estimate over-counts; it is calibrated on the game).
  To try a point in the client: `py tests/sightrows.py <map> --at X,Y --png out.png`.
- **Transporters** [TR-1] (`rules/TRANSPORTERS.md`, read from OpenNox's source and proved in the client): a lift's
  platform and pit name each other by extent (xfer ExtentLink, joined at load); an enabled platform cycles by itself
  (a second's wait at each end), carrying whoever stands on it to the pit and back; a teleport pad sends whoever
  stands on it to the TRANSPORTER it names (a pentagram after its glow, an invisible one at once) and does nothing
  when it names none (an arrival marker). The create flags (ENABLED) are stored only with an object's extended fields:
  `build_map.ps1` writes `enabled: false` that way, and `key` / `link` resolve one object's extent into another's
  ExtentLink. Stairs are pictures with an invisible pad on them. An `-autosrv` host starts NO_COLLIDE and triggers
  no pad: a client test clears that flag first.
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
   and the voices [VO-1]: every spoken line has its wave, made from its present text, PCM 16-bit mono, neither silent
   nor clipped, at a speaking pace, under an 8-character name (`voice.check`; it fails until the TTS is fetched);
5. the room score (`review/roomscore.py`, by room type): rooms that miss it are listed to look at;
6. the exterior's empty ground (`review/exteriors.py`): over Westwood's 90th percentile for the map's environment fails
   (`review/exteriors_baseline.json`, from `py review/exteriors.py --westwood --save`), over the 75th is a look;
   the sight [CL-1] (`tests/sightrows.py`): no point of the floor from which a screen row crosses the edge of the
   player's sight often enough to crash the client (33 fails, 31-32 is a look);
7. the pictures, in `review/out/<Name>/qa/` with `index.html`: the story map, the routes with each stop's facing,
   close-ups of every named story place, every room, the empty ground. Each comes with what to look for (the
   "review only" items of `review/FEEDBACK.md`); look at every one.

It never installs the map nor starts the game or the server. After it passes, the main session installs the map
(`mapgen/install.py`: the map, scripts, text and waves) and runs the server smoke test (`tests/server_smoke.py`),
then the user playtests, and hears the voices.

**The checker's rules.** Every finding names its rule (`checks.RULES`: `exterior.camp_seat`, `routes.facing`,
`identity.showpiece`, ...) and the feedback it answers. Errors are defects a player will see or hit; warnings are
departures from Westwood's range or from a house rule the playtests set. The rules by topic:
- walls, doors, kits, floors, the boundary, reachability and the story's gates (the engine and Westwood's construction);
- `minimap.*` [TW-5, GW-3]; `floors.threshold` [SW-4]; `floors.wall_blend` [TW-12] (no edge piece across a wall);
- `rooms.*` (size, cover, identity strays), `composition.*` (the cross-type room rules, bridges, docks across puddles)
  and `identity.*` (a room reads as what it is) [section 3];
- `routes.*` [TW-1, TW-9, GW-1, GW-6, SW-2, AMR-7]: waypoints and legs clear, doorways square-on, no shared stops, every
  stop facing open ground, tours of 4+ stops of 15+ s, nobody's route through a person standing still;
- `pieces.*` [HB-1..HB-5]: the object knowledge base (cauldrons, chests, showpieces, a bedroom's table sets, the
  clearances the playtest set, runs of pieces that do not line walls, hangings above pieces, candelabras by size),
  calibrated on one map of each campaign layout (6-15% of maps trip a rule; `sets` and `hung` are house rules over
  Westwood's habit);
- `exterior.*` [section 4-5]: overlapping pieces, pieces on a fence line, pickable lights, crowds and swarms, docks,
  stumps as seats, strewn bedrolls, purposeless heaps, graveyards without graves.
- `transport.*` [TR-1] (`check_transport`): every lift and pad linked, every landing on open floor (not void, wall
  or a blocking object; 23 px from a wall) with room to move or a way on, and, from the design's
  `<map>.transport.json`, every end on the map, nobody landing on a pad that leads on, the places a transporter
  serves reachable from its landing, a way back or the exit from every landing, every start reachable. Reachability
  follows transporters (a lift both ways, a pad one way, a passage from the sidecar).

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
