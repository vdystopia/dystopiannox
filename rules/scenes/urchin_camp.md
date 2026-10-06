# Urchin camp (the den)

Kit: `kit/camps.py urchin_camp`, which becomes `urchin_den` where its ground is a pocket of the earth or the rock
(`rock_pocket`; `hideout=True/False` forces it). Lab: `py tests/scenelab.py urchin_camp`. Westwood's evidence: 42
campaign scenes, every one a den (Con02a 14, War03c 17, War03d 6, Wiz01A 5).

## What Westwood's are

Pockets dug in the earth: Dirt walls on DirtDark2, joined by passages, a den to a pocket. Every bed and shelf stands
against the earth. Measured from the wall's line (px): paintings and hanging scrolls 2-4, wall torches 6-11, shelves
13-23, beds and hammocks 22-32, chests 21-46, barrels 21-32; the table and its stools in the open (45-120). Pieces in
42 scenes: stools 132, shelves (UrchinShelves, LogShelves, TeepeeShelves) ~190, wall torches 47, beds 134 and hammocks
40, paintings 56, barrels 49, tables 29, hanging scrolls 26, chests 22, torch poles 20, straw 15.

A piece's variant is chosen by where its wall stands from it: a bed with the wall up-left UrchinBed1, up-right 2,
down-right 3, down-left 4; a shelf, hammock or painting by its wall's line (up-left and down-right: UrchinShelvesFull2,
UrchinHammock2, UrchinPainting2; up-right and down-left: the 1s); LogShelvesFull3 on an up-left wall, 4 on an up-right;
ChestUrchin4 up-left, ChestUrchin3 up-right.

## The kit (round 4, 2026-10-06)

- **Beds** of one kind (hammocks 30%), sleepers to sleepers + 2, in twos and threes side by side along the back rock,
  42-48 px apart (never past 64), a group whole or not at all, the next group four to six rays round.
- **Shelves** two or three side by side (26 px) along the upper walls, one or two runs; log shelves in 40% of dens; an
  empty one now and then. Two to four paintings or hanging scrolls on the upper walls. Two or three wall torches.
- **The hoard**: the chest against the upper rock; barrels in a knot of two or three (50%).
- **The table** (65%; large 75%) in the open with two to four stools round it; straw now and then.
- **People**: the shaman by the chest, the others by their beds and the table, the watch inside the mouth.
- **The lab**: eight of ten urchin camps in a pocket of Dirt on DirtDark2 (1.3 times the bandit hideout's size).

## What still gives it away

Westwood's dens are fuller on their walls (wall share 0.88 against ours 0.63) and their pieces closer (closest gaps 22
px against 32); two open-air camps of the ten (the kit's old camp) still stand in glades.
