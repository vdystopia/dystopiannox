# Throne room

Family: ceremonial. Feel: **open and processional**, with character. Kit kind: `throne_room` (the keep's, the college's
Hall of the Star). Profile: `kit/roomtypes.py TYPES["throne_room"]`.

## Purpose and feel

Where a lord sits in state and is approached. The visitor enters at one end and walks the length of the room toward the
seat: the room is built for that walk. It is the opposite of a study: few pieces, much open floor, every piece placed for
effect and most of them in pairs. Its character comes from variety (statues, braziers, columns, tapestries of one colour,
a carpet) and from symmetry, never from more of one piece.

## Focal point

The throne (Dun Mir's four-piece throne, or the lich's in the Land of the Dead), centred on the NW wall, facing SE down
the room to the door in the SE wall, in line with it. Westwood's Dun Mir throne faces SE only, so it stands on the NW
wall; the building gives the room its door on the SE wall (`building._seat_throne`).

## Pieces

- Must: the throne; statues (4+), two flanking the throne against its wall; hangings (2+); columns (2+, in pairs).
- May: braziers or floor candelabras before the dais, a carpet runner, a bench or two by the walls for those who wait,
  plants in the corners, a chest.
- Never: tables, beds, desks, stoves, shelves of any kind, racks, stores (barrels, crates, sacks), hunting trophies,
  straw. Nothing in the aisle.

## Composition

- **NW wall (the back):** the throne centred, statues flanking it, braziers before the dais; tapestries of one colour
  either side.
- **NE wall:** tapestries of the same colour.
- **SE wall:** the door, in line with the throne.
- **SW wall and front corners:** a bench or two; plants.
- **The middle:** a carpet runner and a clear aisle from the door to the throne; a few pairs of columns spread down the
  whole length, set back from the walls (never a row down the middle); pairs of statues between the columns, facing each
  other across the aisle.
- **Movement:** straight in through the door and up the runner to the throne; nothing within 12 units of the door's
  line but the runner.


## Archetypes

Westwood's 4 curated campaign throne room rooms differ in structure, not just in details (clustered by where the focal stands, how the room is zoned, which walls are used, what the middle holds, density: `mapgen/kit/archetypes.py`). Few rooms: the archetypes also draw on kin types' rooms (each counted half a room), as named. Each room draws one by these frequencies, spread over a map's rooms of the type; both engines compose from it (the recipe engine: `kit/identity.py ARCHETYPE_RECIPES`; the motif engine: its zone plans from the archetype's rooms).

| Archetype | Share | Westwood rooms | What it is |
|---|---|---|---|
| processional | 30% | Con06b@58,151; kin: Con04c@75,78 | the throne across from the door at the head of a long walk, fire basins in pairs down it, a pair of columns, victory statues; the walls bare |
| dressed walls | 30% | Con10d@96,150; kin: Con06b@98,180 | the throne on the back wall across from the door, the walls dressed end to end (tapestries, columns against the side walls, balances or obelisks in pairs), the floor bare |
| ringed seat | 20% | Con11a@166,141 | the throne standing out from the back wall ringed by four lights, a square of obelisks or statues before it, chests and tapestries on the walls |
| audience chamber | 20% | Wiz11A@203,72 | a small chamber: the throne on a back wall beside the door, flanked by a pair of obelisks or statues, a lone basin; nothing else |

## Density and openness

| | Westwood's campaign (4 rooms, Con06b, Con10d, Con11a, Wiz11A) | Profile |
|---|---|---|
| coverage | 0.01-0.03-0.05 | 0.03-0.12 (target 0.06) |
| open floor | 0.81-0.93-0.94 | 0.65-0.92 |
| pieces per tile | 0.02-0.10-0.11 | 0.10-0.35 |
| distinct types | 5-8-11 | 9+ (the user asked for character) |
| caps | halls: 6 columns at the median | columns a pair per 26 tiles, at most 8; statues 1 per 14 tiles, at most 10; benches 2 |

## Size

60-260 tiles; long rather than square, the throne at the far end of the long axis.

## Culture variants

- Dun Mir (the kit's): DunMirThrone, Statue2 statues, Column5-8 or cathedral columns, tapestries.
- Land of the Dead: the lich's throne with its base and shadow, mana obelisks, LOTD tapestries and columns, candelabras:
  the Lich Lord's room in Con10d (356 tiles, coverage 0.03, open 0.85, with the judgement balances and arks), the
  finale's in Con11a (296 tiles, 0.01, 0.93) and Wiz11A's niche (84 tiles, 0.05, 0.81). (The 50-tile G_LOTD room this
  brief once stood on is a quest map's.)

## Where people stand

The lord beside his throne (on the dais, at its side), never on the runner or in the aisle between the door and the throne; courtiers by the statues. (`STANDS["throne_room"]`: beside the throne, a back wall.)

## Common mistakes

- "The throne at the end of the room is facing sideways towards the store room. The pillars are in the dead center of
  the room, making walking straight in through the door impossible. There are also two statues that mysteriously face
  directly against the wall." (Greywatch's keep, 2026-10-05)
- "The throne room is also kind of empty and barren. It's just a long room with tons of the same exact pillars. It
  doesn't have any character." (Starwell's Hall of the Star, 2026-10-05: 22 columns 3.4 units apart down both sides,
  hunting trophies on the walls)
- Filling the floor to a house room's coverage: a throne room is open by nature (the user: "should, by its nature, be
  more open with less object density").
- An orrery or any curio in the aisle: it stands in the way of the throne's view of its door.

## Examples

- Westwood: Hecubah's throne room in Con06b, cell 55,144 (492 tiles; it ends in the void and its walls are half crystal,
  so `rules/rooms/westwood.py` reads it by hand: `HAND`): the three-piece Dun Mir throne looks down a runner to its
  doors, wolf statues flanking it, flame basins in pairs along the runner: coverage 0.01, open 0.94.
- Westwood: the Lich Lord's throne room in Con10d (War10d, Wiz10d), cell 89,143: 356 tiles, the lich's throne on its
  base, six LOTD columns, fourteen tapestries, obelisks, the judgement balances: coverage 0.03, open 0.85.
- Westwood's campaign has 4 throne rooms (Con06b, Con10d, Con11a, Wiz11A), all read by hand; none is a town's. The
  profile stays fuller than they are (the user's choice: character, a pair of columns and statues), and smaller
  (60-260 tiles against their 84-492).
- Ours: Starwell's Hall of the Star (seed 4, room 6, 170 tiles): the throne on the NW wall down a runner, statues and
  braziers, four pairs of columns, statues across the aisle, tapestries of one colour: coverage 0.04, open 0.81,
  13 types (`review/out/Starwell/rooms/06.png`).

## Learned in the room lab (2026-10-05, track B; review/roomlab/LOG_tuneB.md)

- **Few hangings, placed:** four at most in all (Westwood's: Hecubah's war poles by the door, the Lich Lord's
  tapestries in pairs), never one every few steps down both back walls.
- **The runner lined with fire:** braziers in pairs just off the runner between the pairs of columns (Hecubah's six
  flame basins), besides the pair before the dais.
- **Columns:** a pair per 30 tiles, three pairs at most (the Lich Lord's six in 356 tiles).
- **Statues:** two flanking the throne, a pair across the aisle, two in the back corners; a statue on a back wall turns
  along it toward the throne (Statue2c/2g on the NW wall, as Westwood stands 19 of its 20), never with its back flat
  to the wall facing the camera.
- **Nothing else:** no plants, no benches, a chest at most.
- Still missing: the dais and inlaid runner (a different floor under the throne and down the aisle) and a shaped hall
  (the shell); a Land of the Dead throne room (the lich's throne with its base and shadow, obelisks, LOTD tapestries)
  for Westwood's three of four.

## QA round 1 (2026-10-13): the round's lessons as rules

The user rated other types in round 1 and asked that the round's themes apply to this one too: "Much of the feedback
boiled down to" rooms too empty with too little diversity, and no balance or symmetry ("things placed randomly, not
lined up with each other"). Composed by `kit/civic.py` (`civic.throne_room`); ledger `review/qa1/civic.md` (Q1A-n).
These rules come before Westwood's statistics above wherever they disagree (the user's word over Westwood's habit).

Every room of the type:
- **The dead space is used** (Q1A-1, Q1A-7): the S corner takes a group of its own; the front corners and the SE and
  SW walls take mixed stock, benches or urns, mirrored; where the floor is still bare a group goes there, bigger rooms
  more. Checked: `civic.s_corner`.
- **Diversity** (Q1A-2): several kinds of piece, more in a bigger room; heaps mix their kinds (never one family alone,
  never the same piece side by side). Checked: `civic.kinds`.
- **The back walls dressed** (Q1A-3): the NE and NW walls hung at even steps, mirrored about each stretch, one
  tapestry colour to a room; a bare stretch takes a pair of the type's wall piece. Checked: `civic.bare_wall`.
- **Balance** (Q1A-4, Q1A-13): pieces centred on their wall or between a piece and a wall; mirrored pairs; one kind of
  table, column, statue to a room; lights in matching corners or flanking the focal piece.
- **Carpets** (Q1A-10): a table set at its carpet's exact middle; a carpet only where its whole rectangle and trim
  lie on the room's floor.

For this type:
- The throne on the NW wall across from the door, facing it down a runner (unchanged), statues and braziers flanking
  it.
- Columns and braziers in mirrored pairs at even steps down the aisle (one kind of column to the room); benches,
  statues and urns mirrored by the side walls; urns flanking the way in (the S and E corners).
- Tapestries of one colour at even steps on the back walls; lights in matching corners.
- Composed by the recipe engine now (`kit/motifs.py ENGINE_TYPES` no longer lists it).

## QA round 2 (2026-10-14; review/qa2/ledger.md Q2C-3)

The user: "The room is not centered" (RM-THRONEROOM-02, -05); "Fill the southwestern side of the room. It's too empty"
(-03). Round 2's refinements (PROCESS.md top section) apply too: centred on the room, facing designed, pieces never touching, storage against the wall, floors ending at a hard line, fullness from kinds. Composed by `kit/civic.py`; ledger `review/qa2/ledger.md`.

- **The throne on the room's own middle** of the NW wall (`furnish.place_throne(at=)`, `civic.room_mid`), the door in
  the SE wall's middle (`CENTRE_DOOR_ROOMS`), the runner centred under the aisle as drawn (`civic.runner`).
- **Both sides filled alike:** the stations' outer pairs reach the side walls on the room's middle; a middle ring of
  statues and urns between the colonnade and the side walls in a wide room; urns of another kind flanking the way in.
  The SW wall is a front wall and takes no hangings, so its side is filled on the floor.
- **Benches face the aisle** (`facing_pair`). Checked: `qa2.centre`, `qa2.facing`.

## QA round 3 (2026-10-23; review/qa3/ledger-civic.md Q3C-6)

The user, of the whole set (all five 5 of 5): "Individually, they are all very good. But as a whole, they are very
repetitive and all too similar. Add some variance and more object diversity."

- **A batch's throne rooms differ in plan, not only in size:** each room draws one of five layouts in strict rotation
  over the map's throne rooms (`civic.THRONE_LAYOUTS`, `throne_layout`, as the chapels' altars, Q2S-1: no layout twice
  while another that fits is unused), each its own treatment of the throne, the floor, the side walls and the pieces:
  - **processional** (round 3's room, kept as rated): the runner lined with braziers between pairs of columns, statues
    and candelabras flanking the throne, benches, statues and urns by the side walls, urns at the way in;
  - **colonnade** (Westwood's dressed walls): flame basins and statues of the other series (Statue1) flanking the
    throne, a broad carpet four or five squares wide, cathedral columns standing against the side walls with statues
    between them, candelabras in pairs along the carpet's edges, paintings on the back walls; no braziers, benches or
    urns;
  - **ringed seat** (Westwood's Con11a): the throne a step out from its wall, a candelabra at each corner of it, a pair
    of columns framing it, a square of four obelisks before it, statues by the side walls, braziers at the way in,
    plants in the front corners;
  - **audience hall**: rows of benches, two a side, facing the throne either side of the runner (an audience's seats,
    as a chapel's pews, so the type's cap of two benches a side wall does not apply), flame basins before the dais,
    statues by the side walls, candelabras at the front row, columns framing the way in;
  - **garden court**: plants and statues flanking the throne, a pair of orb pools either side of the runner with a
    bench by each, plants in pairs lining the runner, statues and ferns by the side walls, columns framing the way in,
    green tapestries.
- **The throne's dais bordered** like a hearth's patch (`shells.BORDERED_ZONES`), never blended.
- **Every column in a pair placed with a purpose** (`civic.way_in_columns`), never a lone column left by the finishing
  pass against a wall.
- A throne room takes no chest (the object knowledge base's cap for the type). Checked: `qa3.batch_repeat` (three or
  more throne rooms in a map whose pieces are, past 80% on average, of the kinds all of them have).
