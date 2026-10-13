# Herbalist

Family: work. Feel: **full, homely**. Kit kind: `herbalist` (a herbwife's hut, a grovelord's herb room, an apothecary's
brewing room). Profile: `kit/roomtypes.py TYPES["herbalist"]`.

## Purpose and feel

An herb-lore room: brewing, drying, remedies. Earthier than a laboratory: books of remedies, herbs growing and drying,
the cauldron always on.

## Focal point

The bubbling cauldron toward a corner, and the one pair of potion shelves.

## Pieces

- Must: the cauldron; shelves (3+: a pair of potion shelves, the rest books of remedies); a work table.
- May: an alchemist's desk or a workstation (once), sacks of herbs, a chest, plants in pots, hangings, a carpet.
- Never: beds, bars, counters, forges, an altar, a throne, tombs, straw, columns, crates, black-powder barrels.

## Composition

- **A back wall:** the pair of potion shelves; books of remedies end to end.
- **The other back wall:** the cauldron toward a corner.
- **Front walls:** sacks of herbs; pots of herbs in the corners.
- **The middle:** the work table with its stool.

## Density and openness

| | Westwood's campaign (2 rooms, Con07D, Con09a) | Profile |
|---|---|---|
| coverage | 0.07-0.12-0.12 | 0.12-0.30 (target 0.17) |
| open floor | 0.59-0.71-0.71 | 0.30-0.80 |
| distinct types | 10-12-12 | 10+ |

## Size

25-90 tiles.

## Where people stand

The herbwife beside her cauldron, else by the potion shelves; never between the work table and its stool. (`STANDS["herbalist"]`: beside the cauldron, beside the potion shelves, a back wall.)

## Common mistakes

- "The shelves on the NE wall in this room are more of a single instance object. These are not repeatable shelves that
  should line a whole wall ... The shelving on the northwest wall, by contrast, is the kind that can be repeated"
  (Starwell, 2026-10-05): potion shelves stand once, as a pair; bookcases line the wall.

## Examples

- Westwood: Con09a, cell 136,49 (66 tiles, 12 types); Con07D, cell 111,85 (49 tiles).
- Ours: Starwell seed 4, room 1 (the herbwife's, 54 tiles, 13 types) and room 18 (the brewing room, 63 tiles).

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Westwood's two herbalists (Con07D, Con09a): a desk with its chair, a pair of potion shelves, a few bookcases, glowing
  jars, a square table with chairs, a crate; no plants, hangings or sacks down the walls. The recipe follows them and
  keeps the cauldron (the brief's focal piece); pieces a step off the walls (`wall_gap`).

## QA round 1 (2026-10-13): the round's lessons as rules

The user rated other types in round 1 and asked that the round's themes apply to this one too: "Much of the feedback
boiled down to" rooms too empty with too little diversity, and no balance or symmetry ("things placed randomly, not
lined up with each other"). Composed by `kit/civic.py` (`civic.herbalist`); ledger `review/qa1/civic.md` (Q1A-n).
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
- The herbalist's counter out from a back wall facing the way in, her spot behind it (Q1A-6), potion shelves end
  to end either side of her (a herbalist is the exception that lines a wall with them), lights flanking the counter.
- The cauldron centred on the other back wall between books of remedies.
- Glowing jars mirrored on a front wall; the work table with stools on a rug; sacks of herbs, crates and apples heaped
  in the S, W and E corners and on the SE wall.
