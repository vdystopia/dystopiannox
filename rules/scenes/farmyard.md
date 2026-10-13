# Farmyard

Kit: the catalogue's `hay_store` (a wall scene by a mill, home, cottage, grove lord's or barracks), `threshing_floor`
and `windmill` (the "farm" culture's). Lab: `py tests/scenelab.py farmyard`. Westwood's evidence: six campaign scenes
(Con08d, War03c, Wiz03a, Wiz03b): heaps of straw (OgreStraw1 most) spread along a wall over ~90 px, a barrel or two, a
wall torch, a rock or a pillar; no sacks, no tools.

## QA round 1 (2026-10-13): a farmstead, not a heap [Q1X-17 .. Q1X-19]

The user: "Overall, the exteriors are too empty on all of them. Add some more variety. An apple tree with apples on the
ground (the item that players can pick up), a well, multiple gardens, etc."; nox6 (Brackwater's orchard): "Good
structure for an orchard, but too empty. Add a few crates of apples and some apples on the ground that the player can
pick up". EX-FARMYARD-04's hearth floor tiles off the fireplace are the rooms' (kit/shells.py hearthstone), not this
scene's.

- The lab's farmyard is a farmstead (`review/scenelab/recipes._farm_plan`, `_farm_build`): the farmhouse; a well yard
  across the yard from it (kit/yards "well", plain); two gardens by the house (`Village.garden`); in the larger
  clearings an orchard; the harvest scenes (hay, threshing floor, wind-mill) laid last. A design's farm lays the same
  pieces: `yards.plan(..., "well")`, `yards.plan(..., "orchard")`, `Village.garden` twice.
- The orchard (`kit/yards._orchard`): 7 x 7 to 9 x 8 squares in its log fence, apple trees (TreeApple) in even rows
  mirrored about the gate's axis, a walk up the middle, windfalls (RedApple) below each crown, a crate of apples either
  side of the gate outside, the bucket of tools and a barrel in the back corners, flowers along the fence.
- Apple trees (`kit/setpieces.apple_tree`) by every household garden in seven of ten, apples under them.

## The kit (round 4, 2026-10-06)

- `hay_store`: two to four heaps 48 px apart along the wall (OgreStraw1 twice as often as 2 or 3), a fifth before them
  50%, a barrel or two at the run's end, sacks 35%, a torch pole 35%, a rock 25%. (A run of five 54 px apart reached
  round a house's corner into Harrowby's storeroom.)
- The threshing floor and the windmill are the kit's own (Westwood has no counterpart): judge them by eye.
