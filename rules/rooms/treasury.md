# Treasury

Family: stores. Feel: **balanced, guarded**. Kit kind: `treasury` (a keep's strongroom, a town hall's treasury, a
guild's counting room). Profile: `kit/roomtypes.py TYPES["treasury"]`.

## Purpose and feel

Where the wealth is kept and counted: strongboxes in a row along the back walls, each with room before it to open, the
treasurer's counting table in the middle, tally shelves, shields and crossed arms on the walls. Few pieces, all of value;
open floor round the table so the boxes can be reached.

## Focal point

The row of strongboxes on a back wall.

## Pieces

- Must: chests (3+), the counting table with a chair.
- May: tally shelves (TraderShelves), shields and crossed arms hung on the walls, a second row of chests.
- Never: beds, hearths, stoves, plants, barrels, crates, sacks, bookcases, bars, counters, an altar, a throne.

## Composition

- **A back wall:** the strongboxes in a row, the floor before them clear.
- **The other back wall:** hanging shields and crossed arms; the tally shelves.
- **Front walls:** bare, or a second row of chests in a big strongroom.
- **The middle:** the counting table and the treasurer's chair, open floor round it.

## Density and openness

| | Westwood's campaign (3 rooms, 3 maps) | Profile |
|---|---|---|
| coverage | 0.00-0.02-0.03 | 0.03-0.24 (target 0.12) |
| open floor | 0.81-0.89-0.97 | 0.45-0.90 |
| pieces per tile | 0.07-0.08-0.11 | 0.08-0.50 |
| distinct types | 5-6 | 5+ |
| caps | | chests 1 per 10 tiles, at most 6; one table |

## Size

20-120 tiles (Westwood's: 54-117).

## Culture variants

Dun Mir's (Wiz06c): Dun Mir chests under hanging shields. The ogres' (Con05B): their chests and sacks with gold.

## Where people stand

The treasurer behind his counting table (the far side from the door), else beside the strongboxes. Never between the
chests and the floor before them. (`STANDS["treasury"]`: behind the table, beside a chest, a back wall.)

## Common mistakes

- Nine chests down one wall (the first lab version, Dun Mir chests the checker reads as stand-alone pieces): a row of
  three, a second in a big room.
- Barrels and sacks: that is a storeroom.

## Examples

- Westwood: Con05B, cell 192,58 (54 tiles: the ogres' chests, gold, sacks, a great cask); Wiz06c, cell 163,93 (117
  tiles: Dun Mir chests, six shield hangings); Con06b, cell 163,93 (116 tiles: three Dun Mir chests, a table of food
  and four chairs).
- Ours: the room lab's treasuries.

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Westwood's one curated strongroom (Con05B, the ogres', 54 tiles): two chests, sacks of two sizes and a great cask
  over a bare floor. The object knowledge agent found ours read as armouries (trader's shelves and hung shields
  dominating): the recipe now holds three strongboxes (the knowledge base's cap) on the back walls, sacks of coin and a
  cask in heaps, the counting table and chair; no shelves of wares, no hung arms. The cap on stores rose to one per 6
  tiles (Con05B: five on 54 tiles). The brief's Con06b and Wiz06c examples were corridors (curated out).
