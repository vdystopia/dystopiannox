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
