# Ossuary

Family: the dead. Feel: **bare but for the bones**. Kit kind: `ossuary` (a chapel's bone room, a catacomb's charnel, a
dungeon's bone pit). Profile: `kit/roomtypes.py TYPES["ossuary"]`.

## Purpose and feel

Where the bones are kept once the graves are full: skulls and long bones in heaps, crypt chests in the corners, a
monument or two, a coffin. No rows of sarcophagi (a crypt's), no statues: the bones are the room.

## Focal point

None: the heaps of bones.

## Pieces

- Must: a crypt chest; bones and skulls (8+ to read as an ossuary).
- May: a second crypt chest, monuments, a coffin.
- Never: beds, desks, tables, chairs, benches, hearths, stoves, forges, lab pieces, bars, counters, racks, straw, rugs,
  plants, barrels, sacks, bookcases; rows of tombs.

## Composition

- **Back walls:** crypt chests in the corners; a monument.
- **Front walls:** bones.
- **The middle:** bones in heaps, a way kept through them to the chests.

## Density and openness

| | Westwood's campaign (4 rooms, 2 maps) | Profile |
|---|---|---|
| coverage | 0.00-0.04-0.16 | 0.01-0.18 (target 0.06) |
| open floor | 0.52-0.92-1.00 | 0.55-0.99 |
| pieces per tile | 0.00-0.03-0.11 | 0.00-0.40 |
| distinct types | 0-1-1 | 1+ |

Bones have no furniture family: they are the room, but the room score does not count them.

## Size

9-120 tiles (Westwood's: 9-81).

## Culture variants

The Land of the Dead's bones lie in every room of theirs (`dark_crypt`, `dark_chapel`); an ossuary of theirs would take
LOTD tombstones.

## Where people stand

The sexton beside a crypt chest, else at a back wall; never on the bones. (`STANDS["ossuary"]`: beside a crypt chest, a
back wall.) The restless dead stand about it (StoryMap.keepers).

## Common mistakes

- Bones strewn evenly over the floor like a scatter (the first lab version): heaps of four to seven.

## Examples

- Westwood: Con04a, cell 123,107 (81 tiles: two crypt chests, two monuments, bones); Con04a, cell 125,160 (64 tiles: a
  crypt chest, eleven bones); War04b, cell 239,65 (9 tiles: a crypt chest and 21 bones); Con04a, cell 114,122 (24
  tiles). (Wiz07B's bone pocket, cell 238,110, has cave walls: not counted.)
- Ours: the room lab's ossuaries.
