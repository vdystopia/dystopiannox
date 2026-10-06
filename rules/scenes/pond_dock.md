# Pond with a dock

Kit: `kit/water.py Waterworks.pond`, `dock` (`_shore_start`, `_dock_gear`). Lab: `py tests/scenelab.py pond_dock`.
Westwood's evidence: 4 campaign docks (Con05A's three DockDown runs into the lake, Con03A's DockUp; War03a's DockUp).

## Purpose

Where boats tie up and the fishers work: a dock run out from the bank into open water, their gear on the bank.

## Anchor

The dock: a kit chain at Westwood's exact steps (`KIT_STEPS`, DV1-1), its root on the bank, square to the shore, its
tip in open water.

## Zones

- **The dock**: DockDown preferred (FarRamp, two centres, NearEnd: Westwood's usual dock), DockUp (three pieces) only
  where it lands much nearer the road; a barrel or two near the tip.
- **The bank**: two or three barrels touching on one side of the root (the water barrel among them), a crate or a rock
  on the other, a small stone; on land, off the dock's lane, clear of the shore walls.

## Must, may, never

- Must: the dock runs out square to its shore (within 20 degrees over the checker's ring of ten cells) with water two
  tiles to either side and three round its tip (AM-2, DV4-1).
- May: barrels on the dock, the gear on the bank, reeds in the shallows only.
- Never: a dock along the bank, across a puddle, or ending near the far shore; gear on the dock's lane.

## Spacing (Westwood against the kit, r3)

| | Westwood (median) | Kit now |
|---|---|---|
| pieces | 6.5 | 5-9 |
| reach from the middle | 158 px | ~100-150 |
| stores' share | 0.22 | ~0.3 |
| rocks' share | 0.14 | ~0.1 |

## Variance

Kit (DockDown or DockUp by the shore), the bank side of the gear, two or three barrels, a crate or a rock.

## Mistakes (the user's words)

- "Another example of a doc problem that I thought we fixed ... the dock is way too close to the shore and does not
  extend out into the middle of the pond." (AM-2, recurring DV4-1)
- The lab's own: the kit's 30-degree test over six tiles let two DockUp docks run 35-40 degrees off square as the
  checker reads them.

## Round 2 (2026-10-05)

- `dock("best")`: the DockDown run at the asked length, else a one-centre DockDown, and a DockUp only where it lands
  60 uv nearer the road: Westwood's dock is the DockDown run.
- The bank never one stamp (`_dock_gear`, its own generator): 1-4 barrels in a loose knot (26-44 px steps, some
  touching), a rock with its stones (60%), a crate set down a little way off (40%), bones (30%); nothing on the dock's
  line carried back onto the bank. The dock's own load: nothing, a crate, or one or two barrels near the tip.

## What still gives it away

The short DockUp in a small forest pond; Westwood's docks are long runs into a big lake.

## Round 3 (2026-10-06, the town setting)

- No reed within three tiles of a dock's lane; the bank's gear only where the ground a step round it is land too; 2-4
  barrels, the rock 75%, bones 40%.
