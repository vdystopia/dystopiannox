# Cell

Family: confinement. Feel: **bare**. Kit kinds: `cell` (a gaol's or a keep's cell), `ogre_pen` (the ogres' pen for
their captives). Profile: `kit/roomtypes.py TYPES["cell"]`.

## Purpose and feel

A small bare room someone is kept in. Straw on the floor, a cot if the gaoler is kind, the stocks in a bigger cell,
bones where nobody came back. Nothing to use, nothing to hide behind. The emptiness is the identity: never furnish a cell
to a target.

## Focal point

The cot against the back wall (the stocks in an ogre pen).

## Pieces

- Must: straw (2+ heaps); a cot (`cell`); the stocks (`ogre_pen`).
- May: the stocks in a bigger cell, a few bones and a skull.
- Never: tables, desks, chairs, shelves, chests, hangings, rugs, plants, statues, hearths, lights of its own beyond the
  house's candelabras.

## Composition

- **A back wall:** the cot, headboard to the wall.
- **The other back wall:** the stocks, or bare.
- **Front walls:** bare; the door.
- **The middle:** straw strewn in a few heaps, a bone or two; open.

## Density and openness

| | Westwood's campaign (7 rooms, 2 maps) | Profile |
|---|---|---|
| coverage | 0.03-0.07-0.30 | 0.02-0.25 (target 0.10) |
| open floor | 0.47-0.65-0.77 | 0.25-0.98 |
| pieces per tile | 0.08-0.23-1.00 | 0.05-1.00 |
| distinct types | 1-3-5 | 2+ |

## Size

8-40 tiles (Westwood's: 13 for a cell, 30-35 for the ogres' pens).

## Culture variants

`ogre_pen` (Con11a's five pens): ogre straw, the stocks, bones; no cot.

## Where people stand

The prisoner at the back wall by his cot (or by the stocks), facing the door; never in the doorway (the gaoler stands
outside, in the guardroom). (`STANDS["cell"]`: beside the cot, beside the stocks, a back wall.)

## Common mistakes

- A carpet of straw: heaps, not a floor of it (the ogre pen's first version: 22 heaps in 56 tiles).
- Furnished to look lived in: a cell has one cot and nothing else.
- The door: Westwood's cells shut with a jail door (JailDoor: 7 in 6 campaign rooms). The kit gives a building one door
  family, so a cell's door is still the building's; a jail door per cell is for kit/building.py to learn.

## Examples

- Westwood: War07A, cells 174,236, 160,230 and 164,226 (13 tiles each: a cot, straw, a jail door); Con11a, cells 174,44,
  166,52, 194,80 and 182,36 (30-35 tiles: the ogres' pens, straw and the stocks).
- Ours: the room lab's cells and pens.
