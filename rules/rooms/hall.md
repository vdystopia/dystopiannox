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
