# Guardroom

Family: martial. Feel: **balanced, lived in**. Kit kind: `guardroom` (a gatehouse's watch room, a gaol's gaoler's room,
a keep's guard post). Profile: `kit/roomtypes.py TYPES["guardroom"]`.

## Purpose and feel

Where the watch waits between rounds: they eat, dice and sleep in turns by the door they guard. Not a barracks (a crew's
bunks in rows) and not an armoury (arms on show): a few cots, a table with a meal on it, the arms within reach on the
walls. Westwood's guard rooms are by a gate or a cell block, with the archer and the swordsman standing in them.

## Focal point

The watch's table in the middle, chairs round it, a meal on it (RoundTableWithFood).

## Pieces

- Must: a table (with its chairs), a cot or two, arms on the wall (hanging swords, pole arms, a bow rack).
- May: a chest at each cot, barrels of water and ale by the front walls, shields and crossed arms or a hunting trophy
  hung on the back walls, a bench, a spittoon.
- Never: bars, counters, an altar, a throne, tombs, lab pieces, forges, stoves, desks, plants, bookcases, black powder.

## Composition

- **A back wall:** two or three cots for the watch off duty, a chest snug at each.
- **The other back wall:** swords, pole arms and bows on the wall; shields and crossed arms between them.
- **Front walls:** a barrel or two by the door; a bench.
- **The middle:** the table with its chairs, a meal on it; a clear way from the door past it.
- **Movement:** in at the door, past the table, to the cell door or the stair beyond.

## Density and openness

| | Westwood's campaign (5 rooms, 4 maps) | Profile |
|---|---|---|
| coverage | 0.10-0.13-0.24 | 0.10-0.32 (target 0.18) |
| open floor | 0.41-0.57-0.59 | 0.30-0.80 |
| pieces per tile | 0.24-0.29-0.47 | 0.15-0.90 |
| distinct types | 4-8-13 | 8+ |
| caps | 2 cots, 1 table at the median | cots 1 per 12 tiles, at most 4; tables 1 per 30, at most 2 |

## Size

20-90 tiles (Westwood's: 15-63).

## Culture variants

Dun Mir's (Con06b's guard posts): Dun Mir chests and hanging shields in place of chests and trophies.

## Where people stand

The guards by their arms on the wall (beside the racks), the sergeant on the far side of the table from the door; never
in the doorway or the way past the table. (`STANDS["guardroom"]`: beside a weapon rack, behind the table, a back wall.)

## Common mistakes

- Rows of cots: that is a barracks. Two or three, against one wall.
- A rack of armour stands in the middle: a guardroom's arms hang on its walls (an armoury racks them in rows).

## Examples

- Westwood: Con03A / War03a, cell 110,112 (63 tiles: two cots, four chests, a table of food with four chairs, hanging
  swords, a bear's head, a spittoon, the archer and the swordsman); Con06a, cell 69,199 (55 tiles: tables, benches,
  shields, hanging swords); Con06b, cell 179,71 (25 tiles); Con03A, cell 81,83 (15 tiles: a guard post with two cots);
  Con02a / War03b, cell 93,175 (25 tiles: the gaoler's room by the cells, a table, racks of bows and swords).
- Ours: the room lab's guardrooms (`py mapgen/designs/roomlab.py 1 guardroom --stands`).
