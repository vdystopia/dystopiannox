# Jail yard

Kit: `kit/yards.py` "jail" (two cells of 6 tiles behind Cobblestone, a JailDoor each). Lab: `py tests/scenelab.py
jail`. Westwood's evidence: eleven campaign scenes found by their JailDoors (Con02a, Con07B, War03b, War03c, War07A).

## What Westwood's are

Cells on RoughCobble behind Cobblestone walls, in paved town or castle courts: a cot in one cell, straw strewn thick
(Straw2, seven to twelve tufts to a jail), a wall torch to a cell; Con02a's and War03b's guardroom before the cells
holds the guards' racks (polearms, hanging swords and crossbow, a bow rack, a quiver rack) and a table.

## The kit (round 4, 2026-10-06)

- The cells' bedding from the jail's own generator (the design's draws replayed, so a map round it is laid as before):
  a cot against the back wall of one cell (80%; Cot2 or Cot1), three to six tufts of straw a cell (Straw2, Straw1
  15%), 0.6 squares apart and off the cot; a wall torch on a cell's back wall (60%).
- Not yet: the guardroom with its racks and table (Greywatch places its prisoners by the cells' geometry).

## Archetypes (round 6, 2026-10-06)

Westwood's eleven campaign jails (`kit/yards.py` `JAIL_ARCH`, `jail_arch`, `_jail`):

| Archetype | Westwood | What it is | The kit |
|---|---|---|---|
| cell row | 9 of 11 (Con07B x7, War07A, War03c's pit) | two to four cells side by side along a wall, a barred door into each with a wall torch beside it outside, alike down the row; inside, variety: one cell bare, one with a cot, one deep in straw | `cell_row` (6 x 3 or 9 x 3: two or three cells): a torch beside every JailDoor on the same side, outside; the cells' kinds bare / cot (with a tuft or three) / straw (six to ten tufts in a drift round one point), shuffled |
| guardhouse | 2 of 11 (Con02a, War03b) | two cells at the back of a stone house, a cot in each and straw in one, the guardroom before them with racks along its walls, a table and a water barrel, its own wooden door | `guardhouse` (6 x 6): the cells' wall three squares in with their JailDoors and torches, the guardroom's racks (bow rack, quiver rack, pole arms) along its side walls, Table1, a WaterBarrel in a corner, a WoodenDoor off the front's middle |

The torches no longer sit inside the cells (the judge: "torches missing or inside cells"). `y.cell_mids` gives each cell's
middle (Greywatch stands its prisoners by it).

**Sites.** Westwood's are built into castle masonry or a guardhouse. The lab: seven of ten against a town wall (the back
side the wall, running on past the corners), the court paved in two of three.

AUC: 0.939 -> 0.889 (round6).
