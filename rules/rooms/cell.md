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


## Archetypes

Westwood's 10 curated campaign cell rooms differ in structure, not just in details (clustered by where the focal stands, how the room is zoned, which walls are used, what the middle holds, density: `mapgen/kit/archetypes.py`). Each room draws one by these frequencies, spread over a map's rooms of the type; both engines compose from it (the recipe engine: `kit/identity.py ARCHETYPE_RECIPES`; the motif engine: its zone plans from the archetype's rooms).

| Archetype | Share | Westwood rooms | What it is |
|---|---|---|---|
| straw pen | 60% | Con11a@166,52, Con11a@174,44, Con11a@182,36, Con11a@194,80, Con11a@202,72, Con11a@210,64 | an ogre pen: straw heaped over the floor, a primitive obelisk in a corner, a stool or a bench (recipe engine: the kind's own recipe) |
| gaol cell | 30% | War07A@160,230, War07A@164,226, War07A@174,236 | a gaol cell: one cot on a back wall, straw lining the walls and strewn, nothing else (recipe engine: the kind's own recipe) |
| cell block | 10% | War03c@104,88 | a long barred block: bare, barrels in a corner, torches (recipe engine: the kind's own recipe) |

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

## Learned in the room lab (tuneA, 2026-10-05)

Westwood's 10 curated cells: War07A's 13-tile cells hold a cot and **9-12 bundles of straw heaped beside it**; Con11a's
ogre pens hold 4-7 heaps of ogre straw and a crude obelisk (`ObeliskPrimitive`) in four of six, a stool or a bench in
two, a barrel; **never the stocks**, and no light of their own. The recipe now: cells `dark`, the cot far from the
door, straw heaped by it (`scatter by_bed`); pens lift the Ogre pieces whatever the building's style (`lift`; the lab
had built them empty), the obelisk always (the pen's focal now), stocks rare. AUC 0.98 -> 0.83, hard rooms 6 -> 2.
Shell: our cells are 16-36 tiles with up to three doors; Westwood's are 13 tiles behind one barred door.
