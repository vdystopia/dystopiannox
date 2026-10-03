# Automatic checks (phase 4)

The checker reads a finished `.map` through the editor's own library (the corpus exporter), so it
sees exactly what the game loads. It reports **errors** (defects a player will see or hit) and
**warnings** (departures from the range Westwood's single-player maps stay within), each with its
position. It can also draw them on a picture of the map.

Every map build runs it: `Spec.build()` ends with a `CHECK <map>: N error(s), M warning(s)` line.
The full report goes to `validate/out/<map>/report.md`.

## Commands

| Command | What it does |
|---|---|
| `py validate/validate.py DysVale` | Checks a map: a `.map` path, a game map folder name, or a Westwood map name such as `Con07B` |
| `py validate/validate.py DysVale --image` | Also writes `overview.png` (numbered markers: red = error, orange = warning) and `errors/error_NNN.png` close-ups |
| `py validate/selftest.py` | Builds a clean test map and 21 maps with planted defects, and confirms each defect is caught |
| `py validate/calibrate.py` | Re-measures Westwood's 120 single-player maps, rewrites `baseline.json`, and lists how often each check fires on them |

The exit code of `validate.py` is 0 when there are no errors, 1 when there are errors, and 2 when the map can't be read.

## The checks

| Check | Severity | Catches |
|---|---|---|
| setup | error | No PlayerStart; map type flags 0. Also warns about multiplayer-only objects in a single-player map |
| wall_pieces | error | Wall styles with no artwork for that shape: black walls (Mossford playtest) |
| wall_shapes | error | A built wall piece that doesn't reach back to a neighbour reaching toward it: see-through gaps, including jamb pieces shaped as if the door opening were empty (DysVale playtest). Natural walls are exempt because they draw as overlapping blobs |
| boundary | error | A short gap in an outer wall showing the void, including gaps closed only by invisible walls (Mossford playtest) |
| boundary | warning | A long open edge, which Westwood uses only for cliffs |
| doors | error | A half of a double door alone in a 1-cell opening, or with no matching half (DysVale playtest); a single door in an unpaired 2-cell opening; a door on a wall piece or with no wall beside it; a pair whose halves do not line up, or a type hung as a pair in a wall direction Westwood never pairs it in (DysVale v0.6 playtest) |
| kits | error | Dock and bridge pieces off every step offset Westwood uses (DysVale playtest); railing pieces off their deck piece |
| objects | error | Creatures, items, doors or the start standing in the void (unscripted maps) |
| objects | warning | Furniture inside a wall |
| reachability | error | Creatures and items the player can't reach from the start (unscripted maps; Westwood opens areas with scripts) |
| doorways | error | A blocking object in a door opening |
| floors | error | Floor pairs Westwood never lets touch (e.g. rug on grass) |
| floors | warning | Pairs Westwood blends left mostly as hard seams |
| rooms | warning | Furniture count above Westwood's rooms of the same kind and similar size (DysVale playtest); nearly bare rooms; room size outside the kind's range |
| composition | warning | Pieces that make no sense where they stand (DysVale v0.4 and v0.5 playtests): a piece right in front of a chest, hearth or stove; chairs with no table; furniture bunched into one part of a room (beyond Westwood's 95th percentile); a bridge whose ends do not open onto ground. Also: a dock with no open water past its tip, lights of one room side by side, a short path ending at a building wall with no door, a bar counter stopping short of the wall. From the v0.6 playtest: a chest, bookcase, desk or shelf lying across its wall instead of along it; 4 or more stumps, logs, rocks, boulders, crystals or mushrooms bunched in one spot (330 px) when that is most of them; a bridge crossing at a slant (under 60°), sitting on a bend, or with a plank deck wider than 2 tiles. Furniture outside a room's identity also counts the identity's aliases (an ore store is a storeroom, a mess hall a dining hall) |
| density | warning | Lights, coloured lights, decorations, creatures, edge coverage and walls per 100 floor tiles outside Westwood's 5th–95th percentile |

## How it was calibrated

The grid model comes from phase 2 (`rules/rooms.py`). A wall blocks its own cell, and a floor tile
covers 4 cells. Flood-filling cells from the player start therefore finds what the player can reach,
and what they can see through invisible walls, without pixel geometry. Fixes that came from
Westwood's own maps:

- The game stops players at the edge of the floor, so open floor ends are a look, not a walk-off
  hole. War01A's plateau town ends in cliff art with no walls.
- Secret and script-opened walls are closed for the hole check (the map before anything opens) and
  open for reachability. Elevators and teleports join the areas they stand in.
- Wall-mounted objects (bookcases, buttons, traps) legitimately sit on wall cells.
- Several door types (BandedPlankDoor, IronFenceGate, ...) are used both singly and as pairs. Only
  types Westwood never uses one way are checked for opening width.
- Kit offsets are learned from every bridge and dock in Westwood's maps.
- Room furniture is compared with rooms of a similar size, because tiny bedrooms have very high
  per-tile densities.

### What remains on Westwood's 120 single-player maps (errors)

| Check | Findings | Maps | Notes |
|---|---|---|---|
| wall_shapes | 51 | 22 | Out of about 100,000 built wall pieces. Some are real Westwood gaps (a visible black hole in Con07C's tower wall) |
| doors | 43 | 17 | Gates and crypt doors set at odd angles in natural walls (about 2% of their doors) |
| doorways | 11 | 8 | Deliberate puzzle obstacles: powder barrels, boulders, spike blocks |
| boundary | 5 | 5 | 1–3 cell gaps; three of them are one shared layout |

Composition warnings on Westwood's maps (they are guidance, not errors):

- 10 docks with under 2 tiles of open water (6 maps; some river piers);
- 3 pairs of lights side by side;
- 1 bar gap;
- about 2 short paths per map ending at a wall with no door. Westwood's wide paved streets often run up to building sides.

### Our maps

| Map | Result |
|---|---|
| Mossford v0.1 | 49 errors: all three playtest problems are found independently (39 black-wall pieces, 2 holes closed only by invisible walls, 8 plank-on-dirt seams) |
| DysVale | 0 errors |
| DysCrypt | 0 errors after a rebuild (the original had 2 black corner pieces from before the valid-style table) |
| BldTest (all 20 building styles) | 0 errors |
| TestWatr | 0 errors |
| TreePlace v0.1 | 0 errors; warnings: no creatures, 16.9 wall pieces per 100 floor tiles (Westwood's forests 21-52) |
| RoomTest | 20 doors standing in the void: the test sheet's rooms float in darkness (same on master) |
