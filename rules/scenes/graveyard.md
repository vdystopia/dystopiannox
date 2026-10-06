# Graveyard

Kit: `kit/yards.py` (`YARDS["graveyard"]`, `plan`, `build`, `_graveyard`). Lab: `py tests/scenelab.py graveyard`.
Westwood's evidence: 13 campaign scenes (War03b, War03c, War03d, Con04b, Con07B/War07A, Con09b).

## Purpose

Where the town buries its dead, and a place that is used: graves, and someone digging the next one (SW-9).

## Anchor

The headstones themselves, in rows; the yard's iron fence (IronFence) and its gate facing the town.

## Zones

- **The graves**: rows on the grid's lines, 2.7-2.8 squares (~90 px) apart, a little out of true, an unused plot now
  and then; mixed headstones (Tombstone1 the most); a third of the plots dug earth (DirtDark2) for newer graves, a few
  with flowers.
- **The gravedigger's corner** (most yards), the back corner away from the gate: the open grave (dark earth), the coffin
  beside it, the spade in the ground, the bucket of tools (BarrelWithTools), a torch pole to work by.
- **The gate**: a stone pillar either side, just inside (Monument1, as War03b's).
- **The ground**: sparse grass (GrassSparse2, Westwood's), a tree or two by the fence inside it (dead or old), never
  among the graves; the walk from the gate kept clear.

## Must, may, never

- Must: headstones (graves, SW-9), the fence and gate.
- May: the gravedigger's corner, dug plots, flowers, pillars, trees by the fence.
- Never: a bench (no Westwood graveyard has one), a cross between urns as a set piece, torches in every corner, bones
  strewn, anything on the fence line (AM-1), a tree among the graves.

## Spacing (Westwood against the kit, r5)

| | Westwood (median, p10-p90) | Kit now |
|---|---|---|
| headstones' share of the pieces | 0.89 (0.56-1.0) | ~0.7 (the digger's corner is the user's ask) |
| kinds | 2 (1-6) | 4-7 |
| nearest-piece gap | 97 px (16-127) | ~70-90 |
| steps along the screen diagonals | 0.96 | ~0.75 |
| open ground | 0.55 | ~0.3 |

## Variance

Yard size (10 x 9 to 11 x 10, smaller where there is no room), the rows' axis (the plot's long side), which plots are
dug or empty, the digger's corner (65%), the trees' kind and place, the headstones' kinds.

## Mistakes (the user's words)

- "Graveyards mostly look good, but it would look better if there were actually some graves. Maybe a bucket of tools.
  More diversity of objects." (SW-9)
- The lab's own: graves 65 px apart on dirt tiles read as a grid of plots; a bench and urns that Westwood never lays;
  dead trees planted in the yard's middle.

## What still gives it away

Size and shape: every kit graveyard is a small square box in a glade; Westwood's run large (up to 16 x 16 squares) or
long, against buildings and crypts, often with a paved walk. Larger yards (14 x 11) took the AUC from 0.87 to 0.80 but
cut a corner of Harrowby off, so they wait for a design that plans the room for them.
