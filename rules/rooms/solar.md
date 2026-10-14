# Solar

Family: private. Feel: **full, in two ends**. Kit kind: `solar` (a lord's or a lady's private chamber in a keep or a
manor). Profile: `kit/roomtypes.py TYPES["solar"]`.

## Purpose and feel

The lord's own room, bigger than a bedroom and used in two ends: the bed end, where he sleeps, and the sitting end, where
he reads, writes and receives a guest by his own fire. A bedroom with a hearth and a desk is not enough: the two ends each
have their own wall and their own group, with open floor between.

## Focal point

The hearth centred on a back wall with bookcases either side of it (the sitting end); the bed is the other end's.

## Pieces

- Must: a bed (one), the hearth, the desk, bookcases (2+), a chest, a small table with two or three chairs.
- May: the nightstand, a rug before the chest, a carpet under the table, tapestries of one colour or trophies, a bench,
  plants.
- Never: a second bed, stoves, bars, counters, racks, forges, an altar, a throne, tombs, straw, barrels, crates, sacks.

## Composition

- **A back wall (the bed end):** the bed, headboard to the wall, toward a corner; the nightstand at its head; the chest
  snug with a rug before it.
- **The other back wall (the sitting end):** the hearth centred with a rug before it, bookcases either side end to end;
  the desk with its chair on a stretch of its own.
- **Front walls:** a bench; plants in the corners.
- **The middle:** the small table and chairs on a carpet before the sitting end; open between the two ends.

## Density and openness

| | Westwood's campaign (4 rooms, 3 maps) | Profile |
|---|---|---|
| coverage | 0.05-0.09-0.09 | 0.05-0.28 (target 0.15) |
| open floor | 0.64-0.69-0.79 | 0.35-0.85 |
| pieces per tile | 0.11-0.29-0.31 | 0.15-0.80 |
| distinct types | 12-18-20 | 12+ |
| caps | one bed | one bed; tables 1 per 40 tiles, at most 2 |

## Size

60-220 tiles (Westwood's: 98-196).

## Culture variants

Dun Mir's (Con06b's chambers, 96-196 tiles): Dun Mir chests, benches and columns, a bearskin before the bed.

## Where people stand

The lord by his hearth (at its side, never before it), else by his desk; never between the table and its chairs, never
in the way from the door to the bed. (`STANDS["solar"]`: beside the hearth, beside the desk, a back wall.)

## Common mistakes

- A bedroom blown up: one bed and a scatter of chests and benches down the walls (Thornwick's 105-tile lord's chamber,
  `rules/rooms/bedroom.md`). A chamber that size is a solar: give it the sitting end.
- Two beds: a guest chamber is a bedroom; a solar is one person's.

## Examples

- Westwood: Con07D, cell 134,63 (102 tiles: the bed, the hearth, twelve bookcases, two small tables, white and blue
  tapestries, eleven candelabras); Con06b, cells 116,182 and 91,158 (132 and 196 tiles: Dun Mir chambers); Wiz03b, cell
  78,85 (98 tiles: a cot, the hearth, bookcases, ten green tapestries, obelisks).
- Ours: the room lab's solars.

## Learned in the room lab (tuneA, 2026-10-05)

Westwood's four lords' chambers (98-196 tiles) hold 12-20 kinds, no plants, a bearskin or a red rug, tapestries of one
colour, and are carpeted wall to wall and zoned by the shell (Con07D's hearth on a partition across the middle, the bed
in its own end). The recipe now: no plants, a bench drawn up before the hearth, a second sitting group, rugs, carpet in
0.8. The furniture cannot fill an open 200-tile square at Westwood's 0.05-0.09 cover without reading as empty: the
zoning is the shell's.

## QA round 1 (2026-10-13): the round's lessons as rules

The user rated other types in round 1 and asked that the round's themes apply to this one too: "Much of the feedback
boiled down to" rooms too empty with too little diversity, and no balance or symmetry ("things placed randomly, not
lined up with each other"). Composed by `kit/civic.py` (`civic.solar`); ledger `review/qa1/civic.md` (Q1A-n).
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
- The hearth centred on one back wall between bookcases, a small table with two chairs on a carpet before it.
- The bed centred on the other back wall, a nightstand each side, the chest at its foot (Q1A-9).
- The desk centred on a free stretch with its chair; a dining set and sitting sets mirrored where the floor is still
  bare; benches and urns mirrored on the front walls; the S corner's sitting set; sacks and crates in the W and E
  corners; tapestries of one colour.
- (2026-10-13) A solar of 120+ tiles keeps no bare middle: a table of four centred on its own carpet, never touching
  the hearth's carpet, sitting sets mirrored either side of it along the room's long line, a statue pair mirrored
  across it; a rug before the bed's foot. A rug never overlaps a carpet (`civic.table_set`), and the groups filling
  bare floor keep 3 units off every carpet.
