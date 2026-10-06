# Kitchen

Family: work. Feel: **full and busy**. Kit kind: `kitchen` (an inn's, a manor's, a camp's). Profile:
`kit/roomtypes.py TYPES["kitchen"]`.

## Purpose and feel

Where food is cooked and kept. The fire and the pot, a table to work at with its food, and stores everywhere else.

## Focal point

The hearth (a wall fireplace) centred on a back wall, the cooking cauldron two units off it toward a corner.

## Pieces

- Must: the cauldron or stove; stores (4+: barrels, sacks, crates, apple crates); a work table (a table of food, or a
  table with stools).
- May: log shelves of provisions end to end, a second work table in a big kitchen, stools.
- Never: beds, desks, bookcases, an altar, a throne, tombs, lab pieces, bars, counters, forges, statues, columns,
  black-powder barrels; loose food on the floor (Nox draws items at floor level).

## Composition

- **A back wall:** the hearth centred, the cauldron two units from it toward a corner.
- **The other back wall:** log shelves of provisions end to end.
- **Front walls:** sacks, barrels, crates and apples in heaps toward the corners and rows along the walls.
- **The middle:** the work table with its food and stools.
- **Movement:** a clear way from the door to the hearth; supplies a unit from anything else and 2.4 from the fire.

## Density and openness

| | Westwood's campaign (10 rooms, 6 maps) | Profile |
|---|---|---|
| coverage | 0.05-0.15-0.20 | 0.15-0.32 (target 0.21) |
| open floor | 0.43-0.51-0.82 | 0.22-0.65 |
| pieces per tile | 0.17-0.39-0.50 | 0.30-1.0 |
| distinct types | 4-9-13 | 8+ |
| walls with a purpose | 3-4-4 | 3+; back walls 30%+ lined |

## Size

20-80 tiles.

## Culture variants

A camp kitchen (a mess) keeps more barrels; a Dun Mir kitchen (8 of Westwood's 18) its stone oven.

## Where people stand

The cook beside the cauldron (on the side away from the hearth), else by the hearth; never between the work table and the fire. (`STANDS["kitchen"]`: beside the cauldron or stove, beside the hearth, a back wall.)

## Common mistakes

- "Kitchen: open space everywhere, everything clustered around the chimney, meat on the floor, no clear purpose"
  (TreePlace review log).
- "Kitchen: cauldron too close to the hearth; apples crowding the cauldron" (TreePlace review log): Westwood never sets
  them under 0.87 apart.
- "The kitchen lacked any purpose" (DysVale review).

## Examples

- Westwood: War03b / Con02a, cell 100,118 (30 tiles, 13-14 types, coverage 0.20); Con07B, cell 167,214 (40 tiles).
- Ours: Starwell seed 4, room 12, the inn's kitchen (40 tiles, 13 types, coverage 0.20).

## Learned in the room lab (tuneA, 2026-10-05)

Westwood's 10 campaign kitchens (20-80 tiles, median 30) are **the iron stove and a table**, not a store:

- **What they hold**: the iron stove in all ten (`Stove01-05`: Stove05 on the NW wall, Stove03/04 on the NE; three or
  four side by side in the big ones), never the animated cauldron (two shops hold it); table sets with dark wooden
  chairs (6 square tables, 4 round, 3 long, 2 with food); chests (plain or Dun Mir) in five; barrels in three, on the
  back walls; bookcases in four; a bed in three (the cook sleeps there: the brief's never-list keeps beds out); a hearth
  in three. No sacks, apple crates, log shelves or great casks.
- **What gave ours away** (AUC 1.00): the cauldron and the wall hearth in every room, sacks and casks heaped along the
  walls (storage 2.1 pieces per 10 tiles against 0.67), log shelves.
- **Profile** (`kit/roomtypes.py`): focal the stove (was the hearth); must storage 2 (was 4); bookcases allowed (were
  never); cover 0.12-0.17-0.30, types 6, lined 0.10.
- **The recipe now**: the stove toward a back corner (more in a big kitchen), a hearth in 0.4, the round table of food
  with three or four chairs and a second table, two chests on the back walls, barrels on the back walls, bookcases in
  most, a spittoon now and then; wall pieces stand 0.2 units off the wall (Westwood's 0.49 gap against our 0.24).
- **Still giving it away**: big kitchens with bare floor; stoves dotted round the walls rather than in a line.
