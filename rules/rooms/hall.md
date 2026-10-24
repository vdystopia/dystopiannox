# Hall

Family: ceremonial. Feel: **open and stately**. Kit kind: `hall` (an observatory's star-chamber, a demon forge's hall of
arms). Profile: `kit/roomtypes.py TYPES["hall"]`.

## Purpose and feel

A hall of state or display with no seat to face: a gallery, an antechamber, a temple's outer hall. Among the campaign's
larger rooms (17 halls; crypts and bedrooms are commoner): a colonnade, statues, a few hangings, and nearly all of the floor open.

## Focal point

The colonnade and the statues facing each other across the aisle; in a long hall, a pair of statues at its far end.

## Pieces

- Must: columns (2+, in pairs); statues (2+).
- May: hangings (shields, banners, tapestries), benches by the walls, plants in the corners, a chest, a table with a
  chair or two.
- Never: beds, desks, stoves, shelves, racks, stores, lab pieces, straw.

## Composition

- **Back walls:** hangings of one theme.
- **Front walls:** benches; plants in the corners.
- **The middle:** a colonnade in pairs either side of a clear aisle (never a row down the middle in line with the door),
  statues in pairs facing across it.
- **Movement:** straight through from door to door.

## Density and openness

| | Westwood's campaign (17 rooms, 12 maps) | Profile |
|---|---|---|
| coverage | 0.00-0.03-0.10 | 0.02-0.14 (target 0.04) |
| open floor | 0.61-0.78-0.97 | 0.65-0.97 |
| pieces per tile | 0.04-0.12-0.34 | 0.05-0.30 |
| distinct types | 2-4-9 | 6+ |
| caps | 6 columns at the median | columns 1 per 18 tiles, at most 10 |

## Size

50-260 tiles.

## Culture variants

Land of the Dead halls (3 of the campaign's 17; Con10c's obelisk halls): mana obelisks and LOTD columns instead of statues and columns. Dun Mir: Dun
Mir statues and hanging shields.

## Where people stand

Beside a statue, at its side away from the aisle, else against a back wall; never in the aisle down the colonnade or between two columns in line with a door. (`STANDS["hall"]`: beside a statue, a back wall.)

## Common mistakes

- Columns in a row down the middle, blocking the way in (Greywatch's keep, 2026-10-05: "The pillars are in the dead
  center of the room, making walking straight in through the door impossible").
- A block of columns or obelisks: pairs either side of the aisle.

## Examples

- Westwood: Wiz02A / Con07B, cell 150,198: a 155-tile hall, 15 types (columns, statues, plants, chests): coverage 0.06,
  open 0.76.
- Ours: Starwell's star-chamber (seed 4, room 3, 98 tiles): coverage 0.04, open 0.73.

## Learned in the room lab (2026-10-05, track B; review/roomlab/LOG_tuneB.md)

Westwood's halls (curated: Con04c, Con06b, Con10c) are columns, statues and open floor.
- **No plants, no tables, no benches down the walls** (one at most), a chest at most, four hangings at most.
- **Statues are the hall's repeated piece** (Con04c holds 24): a piece per 18 tiles, 8 at most, in pairs across the
  aisle and in the corners, turned along their walls; columns a piece per 14 tiles, 12 at most, in pairs.

## QA round 1 (2026-10-13): the round's lessons as rules

The user rated other types in round 1 and asked that the round's themes apply to this one too: "Much of the feedback
boiled down to" rooms too empty with too little diversity, and no balance or symmetry ("things placed randomly, not
lined up with each other"). Composed by `kit/civic.py` (`civic.hall`); ledger `review/qa1/civic.md` (Q1A-n).
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
- Composed on the axis from the door: columns, statues and braziers in mirrored pairs at even steps either side of
  the aisle (one kind of column and of statue to the hall), benches and urns mirrored by the side walls; a statue pair
  flanking the middle of the far wall.
- Tapestries of one colour (or Dun Mir's shields) at even steps on the back walls; urns flanking the way in; lights in
  matching corners.

## QA round 2 (2026-10-14; review/qa2/ledger.md Q2C-2)

The user: "The benches are facing the wrong way. They are facing south, but they should face southwest" (RM-HALL-01);
"Center the hall in the room. There's a large gap on the northeast side" (-02); "This does not look like a hall at all"
(-05, a small square Dun Mir hall). Round 2's refinements (PROCESS.md top section) apply too: centred on the room, facing designed, pieces never touching, storage against the wall, floors ending at a hard line, fullness from kinds. Composed by `kit/civic.py`; ledger `review/qa2/ledger.md`.

- **Centred on the room**, down its length in a long hall (`civic.axis(long_axis=True)`, `room_mid`); the door in its
  wall's middle (`CENTRE_DOOR_ROOMS`), else a clear walk from it (`door_walk`).
- **A hall at every size:** the far end first (a statue pair flanking the far wall's middle, the chest between them with
  lights, flame basins before it), then a colonnade down the aisle, a column at every other station with statues and
  braziers between (stations a step closer in a hall under 130 tiles), benches and urns mirrored by the side walls, a
  middle ring of urns and statues in a wide hall, urns of another kind flanking the way in, plants in the far corners.
- **Benches face the aisle** (`facing_pair`). Checked: `qa2.centre`, `qa2.facing`.

## QA round 3 (2026-10-23; review/qa3/ledger-civic.md Q3C-7)

The user: "Incoherent, random , cluttered with too many pillars and statues" (RM-HALL-01, a typical square Dun Mir hall
of 156 tiles; -03, a large square one of 270 tiles: both 2 of 5); -02 and -04, long halls, 5 of 5; -05, a small square
one, 4.

- **Every hall is the long halls' plan** (02 and 04): one colonnade a side of the aisle (a column at every other station,
  statues and braziers between them), benches alone by the side walls facing the aisle, the far end's statues, chest
  and flame basins, plants in the far corners. Cause: a square hall is as wide as it is long, and the stations filled
  the width with three ranks a side (the colonnade, a "middle ring" of urns and statues, then benches with urns between
  them), a grid of statue-like pieces (01: 4 columns, 4 statues, 6 urns; urns read as statues in the picture).
- **A wide hall widens its nave instead of adding ranks:** where the floor runs 9.5 units or more from the axis to a
  side wall, the colonnade stands 0.45 of the way out (`civic.HALL_WIDE`, `HALL_NAVE`), no middle ring, no urns among
  the benches or flanking the way in (`civic.hall`). A narrow hall is laid as before (02, 04, 05 unchanged).
