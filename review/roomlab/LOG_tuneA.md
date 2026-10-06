# Room lab log: tuneA (bedroom, living room, kitchen, study, solar, guardroom, cell, infirmary)

Branch `night-tuneA`, 2026-10-05. Seed 1, 10 variants a round (`py tests/roomlab.py <type> --iter <name>`). AUC: the
classifier's (Westwood against ours; stop at 0.60). Blind: the judge's accuracy and mean scores (generated / Westwood),
judged by the tuner itself (Claude, vision), so not a naive judge: it has seen the renders it built and the Westwood
pictures from earlier sheets. Every blind number marked "(self)" is that self-judgement, too generous by the
coordinator's lesson from the scene lab; the rounds worth an independent judge are listed in
`review/roomlab/TO_JUDGE.md` for the main session. Hard: rooms with hard-rule findings. Roomscore: the mean share of review/roomscore.py's
checks a room passes.

## Shared changes (kit/furnish.py; each inert for a kind that does not ask for it)

- `wall_candidates` / `place_on_wall` / compose steps: `far=True` ranks wall spots by their distance from the doors
  (toward 0.7 of the room's diagonal) and keeps the piece on a back wall (a bedroom's bed).
- `furnish`: a recipe may set `decorate` (hang the walls or not; default: the kind in DECORATED) and `lined_goal`
  (how much of the back walls `line_backs` and the hangings line; default LINED_GOAL 0.38).
- `fill_room`: a fill step `slot="beside_bed"` (a second nightstand).
- `GROUPS["side_table"]`: a small table with one or two chairs and no rug under it.
- `GROUPS["family_table"]`: a round table (its food on it most often) with three or four chairs, no rug.
- `compose`: a step may carry `chance` (taken only sometimes; a carpet's chance stays its own).
- `place_center`: a recipe may set `table_palette=False` to take its own tables whatever the building's palette (the
  palette had kept the table of food out of every living room).
- `wall_candidates`: a step may set `back=True` (back walls only: a kitchen's barrels, as Westwood stands them); a recipe
  may set `wall_gap` (its wall pieces that far off the wall, Westwood's kitchens: 0.49 against our 0.24).
- `WALL_SIDE_TYPE["Stove"]`: the iron stove's variant for each wall as Westwood's kitchens use them (NW Stove05, NE
  Stove04, SE Stove01, SW Stove02). **Affects every room with a stove** (a correctness fix; tavern, storeroom and
  barracks checks unchanged).
- Reference data: `rules/rooms/westwood.py RETYPE` (below, "Westwood's reference"), with `rules/rooms/westwood.json`
  and `review/roomlab/westwood_features.json` rebuilt.
- Checks before each commit: tavern, storeroom (and barracks for the reference change) identical AUC and hard-rule
  counts to the kit before tuneA (`--iter base0`, `check1`-`check3`).
- **For the shells agent**: what the shell gives away in my types: plain rectangles with doors cut into the back
  walls (bedrooms of 15-25 tiles with three doors leave no wall for a bed group), sizes 1.25 times Westwood's with
  Westwood's pieces (the checker's sparse line at Westwood's median cover then fails), one shell warning
  (galava_townhouse: an ArchedDoor on a wall piece).

## bedroom

| Round | Change | AUC | Cross | Blind acc. (self) | Blind gen / WW (self) | Hard | Roomscore |
|---|---|---|---|---|---|---|---|
| ref | - | 0.988 | 0.855 | 100% | 4.6 / 7.0 | 6 (sparse 5, door 1) | 0.96 |
| r1 | Westwood's set: bed, nightstand, chest beside the bed, desk among bookcases; no plants, hangings 0.15, rug 0.2, table 0.3; no decorated walls; `far` bed | 0.972 | 0.904 | - | - | 7 (bed off the back walls 6) | - |
| r2 | top-up off (benches); far toward 0.7 on a back wall; second nightstand; table where no desk | 0.904 | 0.895 | - | - | 8 | - |
| r3 | the bed centred on the far back wall | 0.827 | 0.805 | - | - | 8 (sparse) | 0.95 |
| r4 | beds over cots, desk 0.85, bench only in big rooms | 0.878 | 0.863 | - | - | 9 (sparse) | - |
| r5 | single bookcases on short stretches | 0.835 | 0.835 | - | - | 7 (sparse) | - |
| r6 | a bench on a front wall when short of cover | 0.876 | 0.883 | 100% | 5.8 / 6.6 | 5 (sparse 4, door 1) | 0.98 |

**Independent judge (main session, pictures only):** ref 6/10 correct, generated 6.4 / Westwood 6.0; r6 8/10,
generated 4.8 / Westwood 5.8. **r6 regressed by eye** although its AUC improved: it stamped Westwood's commonest
layout (bed with chest and nightstand pressed at its head, a desk or bookcase crowding it, a lone bench on the SE wall
with a candelabra, an empty carpet) on every room. The judge also found Westwood "bedrooms" that were not bedrooms.

| Round | Change | AUC | Cross | Blind | Hard | Roomscore |
|---|---|---|---|---|---|---|
| ref2 | the ref recipe again, against the cleaned Westwood set (31 bedrooms; see "Westwood's reference" below) | 0.917 | 0.815 | - | 7 (sparse 5, door 1, way in 1) | 0.98 |
| r7 | ref's composition (the chest centred on its own back wall with a rug before it, shelves end to end, the desk or a table set) with Westwood's proportions: desk 0.7 (was 0.5), table 0.4, bench 0.3, plants 0.3 x1, hangings 0.6 x2 and no decoration pass | 0.921 | 0.807 | queued | 5 (sparse 3, door 1, way in 1) | 0.96 |

r1-r6's recipe is kept aside (not in the kit); its lessons that held are in rules/rooms/bedroom.md.

Earlier note (r6): what changed the eye's verdict most: the room now reads as Westwood's (bed with nightstand
and chest, desk among bookcases, two walls used); what still gives it away: plain rectangles with large bare floors and
doors in the back walls; Westwood's are shaped and carry odd lived-in pieces. The hard rule left is the checker's sparse
line (Westwood's median cover) in rooms of 15-25 tiles with three doors (10-11% against 11.7%), and one shell warning
(an ArchedDoor on a wall piece in a galava_townhouse: building.py, not the furniture). Blind sheets: before
`review/out/roomlab/bedroom/ref/blind/`, after `review/out/roomlab/bedroom/r6/blind/`.

## living_room

The reference is `base0` (the kit before any tuneA change; tuneA's shared changes are inert for this type). Half of each
batch is the dwelling variant (a one-room home with its bed), which Westwood's 15 living rooms never are.

| Round | Change | AUC | Cross | Blind acc. (self) | Blind gen / WW (self) | Hard | Roomscore |
|---|---|---|---|---|---|---|---|
| base0 | - | 0.985 | 0.925 | - | - | 3 (sparse 2, door 1) | 0.98 |
| r1 | Westwood's set: hearth, round table and 3-5 chairs, chest, barrel, bench, spittoon, a rug; shelves by the hearth in a quarter; no plants or statues; no decorated walls, lined goal 0.05 | 0.903 | 0.883 | - | - | 3 (way in 2) | - |
| r2 | tables outside the building's palette (`table_palette=False`) so the table carries its food; 4-5 chairs; dwellings: chests and barrels, no sacks | 0.833 | 0.824 | - | - | 5 | - |
| r3 | the table of food as a group first | 0.843 | 0.817 | - | - | 3 | - |
| r4 | `family_table` group (3-4 chairs); one barrel, one bench | 0.788 | 0.777 | 100% | 4.6 / 6.4 | 3 | - |
| r5 | dwellings: the family table, top-up of benches only, 2-4 chairs | 0.768 | 0.762 | - | - | 4 | - |
| r6 | dwellings: no cauldron (crowded the hearth); one hanging; a bench and a second sitting table in big rooms | 0.738 | 0.748 | 100% | 4.8 / 6.4 | 4 (sparse 3, door 1) | 0.98 (profile lined 0.08, types 6) |

Profile: `lined` 0.30 -> 0.08 and `types_min` 9 -> 6 (Westwood's 0.05 and 5): the room score had failed every
Westwood-like room on them. Still giving it away: the hearth in every room (the profile's must; Westwood's in 6 of 15),
the dwelling's bed, the table dead centre with single barrels at even gaps along the walls; Westwood's heap barrels in
a corner and pull the chairs round the hearth. Hard rules left: the checker's sparse line in the big (49-56 tile) rooms
and the way in at exactly 4.0 units in one dwelling.

## kitchen

| Round | Change | AUC | Cross | Blind | Hard | Roomscore |
|---|---|---|---|---|---|---|
| ref | - | 1.00 | 0.970 | queued | 4 (sparse 2, way in 2) | 1.00 (new profile) |
| r1 | Westwood's set: the iron stove (never the cauldron), table sets with chairs, chests and barrels; no sacks, apple crates, log shelves or great casks; hearth in 30%; focal = the stove | 1.00 | 0.961 | - | 7 (never: bookcases 5) | - |
| r2 | bookcases allowed (4 of Westwood's 10 kitchens hold them); stoves by size; one chest | 1.00 | 0.971 | - | 9 (sparse) | - |
| r3 | two or three tables, bookcases 0.5 | 0.998 | 0.959 | - | 7 | - |
| r4 | more chests, barrels, bookcases | 0.997 | 0.962 | - | 6 | - |
| r5 | stove variants per wall (`WALL_SIDE_TYPE["Stove"]`); must storage 2; Westwood re-measured with the stove as focal (AUC 0.998 -> 0.970 on the same rooms) | 0.970 | 0.922 | - | 10 (sparse) | - |
| r6 | barrels on the back walls (`back=True`), wall pieces 0.2 off the wall (`wall_gap`) | 0.846 | 0.924 | - | 10 (sparse) | - |
| r7 (extra) | single bookcases on short stretches; barrels in the fill | 0.924 | 0.943 | - | 8 (sparse) | - |
| r8 (extra) | the family table group (a round table of food, 3-4 chairs) first; two chests; bookcases 0.85 | 0.926 | 0.840 | queued | 4 (sparse 3, a neighbour's log shelves 1) | 0.97 |

Two rounds past the limit: r6 had the best AUC but every room broke the checker's sparse line, and r7 looked empty by
eye; r8 is the round to judge. Still giving it away: big kitchens (78-80 tiles) with a lot of bare floor and stoves
dotted along the walls (the "beside" step did not line them up); Westwood's are 20-30 tiles and fuller. Profile
changes (rules/rooms/kitchen.md): focal the stove, must storage 2 (was 4), bookcases allowed, cover 0.12-0.17-0.30,
lined 0.10, types 6.

## Westwood's reference (rules/rooms/westwood.py RETYPE)

An independent blind judge found "Westwood bedrooms" and "living rooms" that were not: a dais hall, guard posts by
barred doors, a cell. Fifteen rooms read by eye from the gallery are retyped wherever their layout recurs (the
campaigns share most maps): to cell 1 (War07A's), guardroom 8 (gaol posts and bunk huts), solar 4 (the lords' chambers
that are the solar's evidence), dropped 2 (Con07F's dais hall, Con09a's ogre shack). Bedroom 40 -> 31 rooms (median 12
tiles), living room 15 -> 9; guardroom now has 8 Westwood rooms of its own, cell 1, solar 4. `rules/rooms/westwood.json`
and `review/roomlab/westwood_features.json` rebuilt (233 rooms; only these rooms and the kitchen's focal features
changed). Galleries of bedroom and living room re-rendered.

## study

Thin: Westwood has two studies (Con02a's); the classifier compares with the pool (the two studies and 7 libraries),
FALLBACK. The user's verdict leads here: Starwell's archmagister's study was "exceptional ... full, balanced, and
themed" (SW-7), and it is this recipe's composition (the desk among bookcases, a meeting table on a carpet, a curio).

| Round | Change | AUC (pool) | Cross | Blind | Hard | Roomscore |
|---|---|---|---|---|---|---|
| ref | - | 1.00 | 0.955 | queued | 4 (must: no chest 2; galava shell 2) | 0.98 |
| r1 | the hearth in 0.6 (Westwood's studies and libraries: 5 of 9), curios, statues and plants occasional, book stacks only over 200 area | 0.990 | 0.985 | - | 7 (sparse 3, way in 3, reads as a living room 1) | - |
| r2 | the fill back to ref's; the chest before the shelves; hearth 0.3 | 0.998 | 0.983 | - | 4 (galava shell 3, reads as a living room 1) | - |
| r3 | no hearth (it made a study read as a living room); plants 0.4 x1 | 0.994 | 0.990 | queued | 4 (galava shell 3: an ArchedDoor on a wall piece and the way in it blocks; sparse 1) | 0.98 |

Stopped at r3: the pool's measures say little (what tells our studies from Westwood's libraries is the meeting table
and curio in the middle, which the user's praised study has), and every change that moved the measures cost a hard
rule. Fixed: the chest every study must have. Left for the shells agent: the galava tower and town-house shells put
an ArchedDoor on a wall piece in 3 of 10 studies; the checker then also finds the way in blocked.

## solar

Thin: Westwood's four lords' chambers (Con07D, Con06b's two, Wiz03b; 98-196 tiles), retyped from the bedroom set
this session; the classifier compares with the pool (bedrooms, living rooms, studies: small rooms), so its AUC stays
1.00 whatever the furniture does. Compared by hand with the four (`cmp.py solar <iter> solar`).

| Round | Change | AUC (pool) | Cross | Blind | Hard | Roomscore |
|---|---|---|---|---|---|---|
| ref | - | 1.00 | 0.982 | queued | 0 | - |
| r1 | no plants; one bench, a bearskin or red rug; whole carpet 0.6; no decoration pass; top-up chests only | 1.00 | 0.971 | - | 0 | - |
| r2 | a second sitting group in the middle; hangings back (decorate) and rugs 1-2; wall pieces 0.2 off the wall | 1.00 | 0.973 | - | 0 | - |
| r3 | a bench drawn up before the hearth; carpet 0.8 | 1.00 | 0.973 | queued | 0 | - |

Against the four by hand, r3 is closer on kinds (no plants, rugs, tapestries) but not on the middle: Westwood's
chambers are zoned by the shell (Con07D's hearth stands in a partition across the middle, the bed in its own end) and
carpeted wall to wall, where ours are open squares of 120-220 tiles with two small table sets in a big bare floor.
That is the shells agent's (a partition or an alcove for the bed end); the furniture cannot fill 200 tiles at
Westwood's 0.05-0.09 cover without reading as empty.
