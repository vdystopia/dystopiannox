# Barracks

Family: martial. Feel: **full, orderly**. Kit kinds: `barracks` (soldiers' or miners' bunks), `ogre_den` (where the
ogres sleep). Profile: `kit/roomtypes.py TYPES["barracks"]`.

## Purpose and feel

Bunks for a crew: everyone sleeps in one room, in rows. Order is the point: beds of one kind, evenly spaced, each with its
chest.

## Focal point

The row of bunks, headboards against a wall.

## Pieces

- Must: beds (2+, 3+ to read as a barracks), all of one kind.
- May: a nightstand between neighbours, a chest a step beyond each bed's foot, a rug before each bed, shelves for gear end
  to end, shields and trophies, a table with seats, a freestanding hearth, benches.
- Never: bars, counters, an altar, a throne, tombs, lab pieces, forges, stoves, black-powder barrels.

## Composition

- **A wall (a front wall when the back walls are wanted for shelves):** beds in a straight row side by side, headboards to
  the wall, at least 0.9 apart, a nightstand between neighbours.
- **A back wall:** shelves for gear end to end; shields and trophies.
- **The middle:** a table with its seats; a hearth with benches in a big room.

## Density and openness

| | Westwood's campaign (16 rooms, 7 maps) | Profile |
|---|---|---|
| coverage | 0.03-0.06-0.25 | 0.12-0.34 (target 0.24) |
| open floor | 0.36-0.65-0.78 | 0.25-0.75 |
| pieces per tile | 0.11-0.23-0.77 | 0.20-0.80 |
| distinct types | 2-5-14 | 8+ |
| caps | 3+ beds always of one kind, in a row | beds 1 per 12 tiles, at most 12 |

## Size

40-200 tiles.

## Culture variants

- `ogre_den` (17 of Westwood's 26 barracks are ogres'): straw heaped free on the floor (72% of ogre rooms), crude beds
  against the back walls, a fire pit ringed by stools in the middle, meat and carcasses, barrels; torch poles. Its focus
  is the fire pit.

## Where people stand

A soldier beside his bunk (at its side, not at its foot where the chest is), an ogre by the fire pit; never in the row's walkway or between the table and its seats. (`STANDS["barracks"]`: beside a bed, beside the fire pit, a back wall.)

## Common mistakes

- An ogre den of 26 straw heaps in 32 pieces (Harrowby; `identity.monotony`): the straw scatter's per100 counts heaps of
  2-3, so 4 heaps per 100 tiles gives Westwood's 8.6 straw per 100; three crude beds; meat and carcasses 3 per 100.

- Beds of mixed kinds, or scattered: "All of Westwood's rooms with 3 or more beds use one kind, in a row."
- Cots read sideways (the cot numbering comes from the pillows).

## Examples

- Westwood: War09c / Con09c, cell 62,206 (56 tiles, 14-15 types: an ogre den); Con05C, cell 122,91 (136 tiles).
- Ours: Starwell seed 4, room 14, the soldiers' bunks (187 tiles).

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Westwood's ogre barracks (Con05C, Con09c, Con11a, War02A) have no fire pit: straw heaped on the floor is the commonest
  piece, barrels in a knot, a crude bed or three, a crude table with stools in some, meat, a primitive obelisk. The ogre
  den follows them (AUC 1.0 -> 0.86). A den of straw is a pen's kin (`cell`).
