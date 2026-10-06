# Mausoleum

Family: the dead. Feel: **open, solemn, round one tomb**. Kit kind: `mausoleum` (a noble family's tomb house in a
graveyard, a great tomb under a keep). Profile: `kit/roomtypes.py TYPES["mausoleum"]`.

## Purpose and feel

One great tomb and the statues of the dead about it. Not a crypt (rows of the many dead with aisles): a mausoleum keeps
one, or a pair, and honours them. Westwood's statue tombs (Con04a, Con04c) hold monuments, a dozen statues, columns, a
crypt chest of grave goods.

## Focal point

The great tomb (a sarcophagus) in the middle.

## Pieces

- Must: the tomb (one; three at most), statues (2+, in pairs facing it), monuments (Monument1, 2+).
- May: a pair of columns, more statues toward the far corners, a tapestry, barren plants.
- Never: beds, desks, tables, chairs, benches, hearths, stoves, forges, lab pieces, bars, counters, racks, straw,
  barrels, sacks, bookcases; rows of tombs (that is a crypt).

## Composition

- **Back walls:** monuments at the corners; a tapestry.
- **Front walls:** bare.
- **The middle:** the great tomb, statues of the dead in pairs facing it, a pair of columns in a big one.

## Density and openness

| | Westwood's campaign (4 rooms, 2 maps) | Profile |
|---|---|---|
| coverage | 0.00-0.06-0.09 | 0.02-0.20 (target 0.10) |
| open floor | 0.51-0.74-1.00 | 0.50-0.92 |
| pieces per tile | 0.01-0.33-0.36 | 0.04-0.40 |
| distinct types | 1-5-6 | 4+ |
| caps | 4 monuments, 12 statues (Con04a) | tombs 1 per 40 tiles, at most 3; statues 1 per 14, at most 8 |

Monuments have no furniture family (rules/room_types.py): the room score counts the tomb, the statues and the columns.

## Size

30-160 tiles (Westwood's: 40-128).

## Culture variants

None yet; a Land of the Dead mausoleum would take an LOTD tombstone and obelisks.

## Where people stand

The mourner, or the keeper of the tomb, beside the tomb at its side, else by a monument; never between the statues and
the tomb they face. (`STANDS["mausoleum"]`: beside the tomb, beside a monument, a back wall.)

## Common mistakes

- Crypt chests across a front wall (the first lab version: the chest's wall variants are mixed in Westwood's maps); the
  mausoleum leaves the chests to the crypt and the ossuary.

## Examples

- Westwood: Con04a / Con05A, cell 148,55 (58 tiles: four monuments, twelve statues, crypt chests, a tombstone); Con04a,
  cell 230,88 (40 tiles); Con04c, cell 220,108 (40 tiles: seven columns, monuments, statues, chests); Con04c, cell 75,78
  (128 tiles: 22 columns, 24 statues, fire grates).
- Ours: the room lab's mausoleums.

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Westwood's 6 curated mausoleums (Con04a's three, Con04c, Con09b, Con10c) hold no great tomb: statues of the dead
  (2-12) in mirrored pairs, a crypt chest, columns in Con04c, obelisks in Con09b and Con10c; mirror symmetry 0.85-1;
  0.06 lights a tile. The recipe: statues in mirrored pairs (GROUPS statues), the crypt chest centred on a back wall, a
  colonnade in a big one; the statue cap rose to one per 5 tiles (Con04a: 12 on 58 tiles).
