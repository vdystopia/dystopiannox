# Living room

Family: private. Feel: **cosy and full**. Kit kinds: `living_room` (a home's hearth room), `dwelling` (a one-room
cottage or hut: the living room with the bed in it). Profile: `kit/roomtypes.py TYPES["living_room"]`.

## Purpose and feel

The household's hearth room: where the family eats, sits by the fire and keeps its everyday things. Warm and lived-in.

## Focal point

The hearth, centred on a back wall, shelves end to end either side of it, a rug before it.

## Pieces

- Must: the hearth; a table with its chairs. A dwelling also its bed.
- May: shelves end to end on both back walls, a chest, benches, trophies and hangings on the back walls, a carpet under
  the table, statues (a big house), plants, a cauldron on a dwelling's fire, sacks and a barrel by a dwelling's wall.
- Never: bars, counters, forges, racks, lab pieces, an altar, a throne, tombs, straw, black-powder barrels.

## Composition

- **A back wall:** the hearth centred, shelves either side, a rug before it (nothing ever stands before a hearth).
- **The other back wall:** shelves end to end with trophies between; the chest. In a dwelling, the bed.
- **Front walls:** a bench; plants in the corners.
- **The middle:** the table with its chairs, toward the front, often on a carpet.
- **Movement:** from the door to the table and the hearth.

## Density and openness

| | Westwood's campaign (15 rooms, 9 maps) | Profile |
|---|---|---|
| coverage | 0.07-0.12-0.21 | 0.10-0.30 (target 0.17; dwelling 0.16) |
| open floor | 0.23-0.51-0.80 | 0.30-0.80 (dwelling 0.22-0.80) |
| pieces per tile | 0.08-0.38-0.60 | 0.25-0.90 |
| distinct types | 3-5-10 | 9+ (fewer in a small room) |
| most of one stand-alone piece | 2-3-4 | 4, or 1 per 20 tiles |

## Size

20-90 tiles.

## Culture variants

Log cabins take log shelves and hunting trophies; stone houses bookcases and tapestries. A dwelling in a lake town keeps
its nets and salt in sacks by the wall.

## Where people stand

The householder at the hearth's side, never before it (the rug and the way to the fire stay clear); never between the table and its chairs. (`STANDS["living_room"]`: beside the hearth, a back wall.)

## Common mistakes

- A living room without trophies or hangings on its walls (TreePlace review: "a living room needs trophies on the
  walls").
- Single shelves here and there instead of a wall lined end to end ("put bookshelves end to end for the entire length
  of the wall").
- A back room with four table sets (DysVale v0.3): one table, one sitting group.
- Harrowby playtest (2026-10-05, HB-1, a cottage): "Why are there two cauldrons? There should only be a maximum of one cauldron per room. bed is way too close to one of the cauldrons. The bench is too close to the bed. Chest is way too close to the other cauldron." One cauldron a room; a bed and a chest 2 units from any fire, a chest 3 from the hearth, a bench 1.2 from the bed (kit/objects.py HOUSE_CLEAR; checker `pieces.cauldrons`, `pieces.clearance`). "The table, chairs, fireplace, and bookshelves all look good."

## Examples

- Westwood: Con07B, cell 105,197 (31 tiles, 12 types); War05A / Con05A, cell 80,10 (40 tiles).
- Ours: Starwell seed 4, rooms 25 and 27 (50 and 60 tiles, 17 and 21 types), rooms 29-30 (dwellings).

## Learned in the room lab (tuneA, 2026-10-05)

Westwood's 15 campaign living rooms (8-40 tiles, one of 116) are **sitting rooms round a table**, not lined rooms:

- **What they hold**: a round table (12 of 15; with its food in 7) ringed by three to five chairs, sometimes one fallen
  over; the hearth in only 6 (Fireplace, with bellows beside it in 3); a chest (6); barrels or water barrels (6), heaped
  in a corner or in pairs; a bench or a cushioned bench (6); a spittoon (2); a rug, a tapestry or two, a painting now
  and then. **No bookcases** (one movable bookcase in 15), **no plants**, **no statues** but a vase. 5 kinds of object
  (3-10); the back walls lined 0.05; the commonest piece is the chair (0.44 of the pieces).
- **What gave ours away** (AUC 0.985 at the start): bookcases lining both back walls, plants, statues, sacks, no chairs
  at the table (the building's table palette left out the table of food), hangings by the room's decoration pass.
- **The recipe now** (`kit/identity.py ROOMS["living_room"]`, `["dwelling"]`): the hearth centred on a back wall, shelves
  beside it in a quarter of the rooms only (the TreePlace review's "shelves along the wall with the hearth"), the
  `family_table` group (a round table, its food on it most often, three or four chairs), a chest, one barrel, a bench, a
  spittoon sometimes, at most one hanging; no plants, no decorated walls (`decorate=False`), lined goal 0.05.
- **Profile**: lined 0.08, types_min 6 (were 0.30 and 9, above Westwood's p90).
- **Still giving it away**: the hearth in every room (the brief's must; Westwood's in 6 of 15), the table dead centre and
  single barrels spaced along the walls; Westwood's heap the barrels in one corner and pull chairs round the hearth.

**On the curated set** (14 households, median 30 tiles and 10 kinds; the earlier 15 held guard posts): the hearth with
its bellows beside it in 7, bookcases in 7, an iron stove in 5, two tables, a spittoon in 4. The recipe adds the
bellows (`smithy` is off the profile's never list), an iron stove in a third, up to two tables, bookcases by the hearth
in half, fewer benches, and draws the table off the centre (an independent judge picked out "a round table of food,
chairs evenly round it, dead centre").
