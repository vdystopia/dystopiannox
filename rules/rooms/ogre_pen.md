# Ogre pen

Family: confinement. Feel: **bare, rough**. Kit kind: `ogre_pen` (the ogres' pen for their captives). Profile:
`kit/roomtypes.py TYPES["ogre_pen"]`.

Split from the cell in QA round 1 (2026-10-13, Q1R-11): "Create a separate category for ogre cells and human cells.
Similar to barracks, the human and ogre variants should be different and have different rules." Westwood's evidence:
Con11a's six pens (`rules/rooms/curated.py` CULTURE_SPLIT; archetype `straw_pen`).

## Purpose and feel

Where the ogres keep a captive: straw, the stocks, a crude obelisk glowing in a corner, bones. The user rated these
4-5 of 5 and kept most as they were.

## Composition

- **The straw:** heaped in one corner, the one farthest from the door, or at one end of the room; never a sheet across
  the middle (RM-CELL-02: "The ogre straw looks better when it's in a corner or end of the room").
- **The obelisk:** in another corner, across from the heap.
- **The stocks:** against a wall.
- **No bare corner** (RM-CELL-02: "the E corner being bare here doesnt look good"): a barrel or a sack, bones, a stool in
  the corners left.

- **Round 2 (fullness):** a full heap (9-16 bundles), a second heap at the other end of a pen of 36+ tiles, a crude
  bench centred on a wall, bones and a skull before the stocks. Checked by `rooms.qa1_fullness`.

## Pieces

- Must: straw (2+), the stocks or the obelisk.
- May: a stool, a barrel, sacks, bones and a skull.
- Never: tables, desks, shelves, chests, rugs, plants, hangings, hearths.

## Checks

`rooms.qa1_south_corner` does not apply (a pen is open by nature); the kit lays it (`kit/finish.py _ogre_pen`).

## Examples

- Ours: QA round 1 RM-CELL-04, -06, -08, -10 (kept); RM-CELL-02 (the note above).
- Westwood: Con11a, cells 174,44, 166,52, 194,80 and 182,36 (30-35 tiles).

## QA round 2 (2026-10-14; review/qa2/ledger.md Q2F-6)

Rated 1, all five Fix (the round's lowest): "The ogre pen should be on an ogre tile set. This is using human buildings
and floors and just putting straw on the floor. In order to make an actual ogre pen, you have to use an
ogre/cave/outdoor/rock-themed base and then layer in ogre features like straw, sacks, and tusks." Now:
- **The ogres' shell:** the room lab builds a pen in the ogres' keep (`ogre_keep`: `dungeon_block` walls of
  DungeonStone, GreenBrick floors, crypt doors; `review/roomlab/labgen.py OPTION_HOSTED`, since the keep lists the pen
  among its options), as Westwood's own pens in Con11a are (DungeonStone, GreenBrick with DirtDark2). A map puts a pen
  in an ogre building, never a town house.
- **Earth under the straw** (`pen_earth`): DirtDark2 within two squares of each heap's middle, blended into the floor,
  none by a door.
- **Ogre features layered in:** a pair of tusks (OgreMoundTusk3/4 with their shadows, kit/camps.py) framing the stocks,
  else the obelisk (`pen_tusks`); a skull post with its shadow in a bare corner off the straw (`_skull_post`); sacks and
  a barrel flush against a back wall (`ogre_stores`); a carcass by the heap; the crude bench lying along its wall
  (`ogre_bench`, never the round stumps that stood out from it) with a stool at its end; bones before the stocks.
- Checked: `rooms.qa2_wall` (sacks flush; round 2's stood 0.78 off their walls).
