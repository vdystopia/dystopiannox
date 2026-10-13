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

## Pieces

- Must: straw (2+), the stocks or the obelisk.
- May: a stool, a barrel, sacks, bones and a skull.
- Never: tables, desks, shelves, chests, rugs, plants, hangings, hearths.

## Checks

`rooms.qa1_south_corner` does not apply (a pen is open by nature); the kit lays it (`kit/finish.py _ogre_pen`).

## Examples

- Ours: QA round 1 RM-CELL-04, -06, -08, -10 (kept); RM-CELL-02 (the note above).
- Westwood: Con11a, cells 174,44, 166,52, 194,80 and 182,36 (30-35 tiles).
