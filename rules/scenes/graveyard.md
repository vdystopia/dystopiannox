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

## Round 2 (2026-10-05): crypts, the walk, larger yards

- **The crypts** (75% of yards, `yards._crypts`): one cobblestone cell (two in a long yard) at one end of the back
  side, 3 x 3 squares, green brick inside, a sarcophagus (Crypt1/Crypt3), a WoodAndSteelDoor into the yard; its back
  and end walls stand on the fence's line (War03b-d's crypt rows, Con07B's and Con09b's single crypts).
- **The walk**: beaten bare (DirtLight2) from the gate square in to the crypt's door, or across to the back; two tiles
  wide in a big yard, one in a small; graves either side of it, 0.5 squares off.
- **Size**: `plan` tries 16 x 12 down to 12 x 10 first where they fit with 3 squares free round them, else the old
  10 x 9 to 11 x 10 (a larger yard once shut a corner of Harrowby off).
- **Graves**: 2.9-3.4 squares along a row, 2.7-3.1 between rows (2.6-2.9 / 2.4-2.7 in a small yard), 1.1 squares off
  the fence; the gate pillar rare; the digger's corner the spade and bucket, the coffin and torch now and then.

## What still gives it away

Round 1: every kit graveyard was a small square box in a glade. Round 2 (AUC 0.565): crypts, a walk and larger yards;
still a yard alone in a glade (Westwood's stand against town walls and buildings), and the walk's bare earth reads
faintly on sparse grass.
