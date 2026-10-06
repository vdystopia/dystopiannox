# Infirmary

Family: work. Feel: **full, orderly**. Kit kind: `infirmary` (a healer's sick room, a chapel's or a keep's infirmary).
Profile: `kit/roomtypes.py TYPES["infirmary"]`.

## Purpose and feel

Where the sick and the wounded are nursed: a row of cots with a nightstand between neighbours, the healer's remedies on a
back wall, the cauldron toward a corner, the healer's table in the middle. A barracks' order with a herbalist's tools.

No campaign room nurses the sick: this type stands on design judgement, composed from the barracks (the row of cots) and
the herbalist (the potion shelves and the cauldron), which Westwood does build.

## Focal point

The row of cots.

## Pieces

- Must: cots (2+, of one kind, in a row), the cauldron, potion shelves and books of remedies (2+), the healer's table.
- May: nightstands between the cots, a stool at the table, a chest of linen, sacks of herbs, hangings of one colour
  (white, blue, green), plants.
- Never: bars, counters, racks, forges, lab pieces, an altar, a throne, tombs, straw, crates, black powder.

## Composition

- **A front wall:** the cots in a row side by side, headboards to the wall, a nightstand between neighbours.
- **A back wall:** a pair of potion shelves, books of remedies; the cauldron toward a corner.
- **The other back wall:** hangings; a chest.
- **The middle:** the healer's table with its stool, kept clear round it; a way down the row of cots.

## Density and openness

| | Westwood's campaign (none) | Profile |
|---|---|---|
| coverage | (the barracks': 0.03-0.06-0.25) | 0.10-0.32 (target 0.20) |
| open floor | (the barracks': 0.36-0.65-0.78) | 0.30-0.80 |
| pieces per tile | | 0.20-0.90 |
| distinct types | | 8+ |
| caps | | cots 1 per 12 tiles, at most 10 |

## Size

40-200 tiles.

## Culture variants

None yet.

## Where people stand

The healer beside the cauldron or by the potion shelves; never between the cots. (`STANDS["infirmary"]`: beside the
cauldron, beside the potion shelves, a back wall.)

## Common mistakes

- Cots of mixed kinds or scattered (the barracks' rule holds).
- A wall of potion shelves: they stand once, as a pair (kit/furnish.py PAIRED_PIECES).

## Examples

- Westwood: none.
- Ours: the room lab's infirmaries.

## Learned in the room lab (tuneA, 2026-10-05)

No Westwood rooms: judged by eye. The ref read as a bunk room (cots in a row and a tiny table alone in a bare middle).
Now the healer's work table with its stools and sacks of herbs by it (the `worktable` group), drawn off the centre, a
chest of linen. Fill groups grow with the room (a step's `max` times the room's size): a table group in the fill
became three tables and a mess hall; keep the work table in the composition, once.
