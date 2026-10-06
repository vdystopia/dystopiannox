# Room lab tuning log: agent C (stores, work rooms, martial, the dead)

Types, in priority order: storeroom, laboratory, shop, library, smithy, armoury, barracks, crypt, herbalist, cellar,
treasury, workshop, torture chamber, mausoleum, ossuary, observatory, winch room, powder store. Each round:
`py tests/roomlab.py <type> --iter <name>` (10 variants, seed 1 unless named `s2`). AUC: Westwood against generated,
cross-validated (stop at 0.60); blind: my accuracy telling them apart by eye (stop at 60%) and the mean scores,
generated / Westwood (stop at Westwood's minus 0.5).

## Shared changes (kit/furnish.py), all gated to the recipes that ask for them

- `Furnisher.store_heaps` / `_store_group` / `_store_fill` / `_heap` / `_heap_row` / `_store_palette` /
  `_store_corners`: a new composition slot `"heaps"` (compose and fill). Only recipes naming it use it: storeroom,
  granary, ore_store, ogre_hoard.
- `ROOMS[kind]["lights_per100"]`: a recipe may light its room more dimly than the house default (add_lights caps
  the count at tiles x rate / 100, at least one). Only the store kinds set it.
- `Furnisher.belongs`: a piece with no furniture family (a mine cart) belongs when the recipe's `prefer` names it.
  Before, the ore store's `carts` group could never place its anchor. Affects only recipes that prefer such pieces.

## Storeroom (Westwood: 22 rooms)

What Westwood's look like: 1-5 types (median 3), barrels the commonest kind (17 of 22 rooms), against two walls (p90
three), coverage 0.02-0.07-0.19, no shelves or racks in any. Barrels stand against the back walls (77% of them on NW/NE:
`type_wall_sides`), crates side by side or stacked in the middle, a knot of barrels standing free.

| Round | Change | AUC | Cross | Hard rooms | Blind acc. | Blind gen / WW |
|---|---|---|---|---|---|---|
| ref | (the kit as found: log shelves, a row of hunting racks, every wall stocked with clusters of every kind; 8-15 types) | 0.955 | 0.975 | 6 | - | - |
| r1 | new `heaps` slot: a palette of a lead kind, a second kind and one odd piece; heaped in one corner and along its two walls, a stack of crates in the middle; no shelves, no racks; cover target 0.30 -> 0.13 | 0.843 | 0.966 | 4 (bunched) | - | - |
| r2 | the second kind toward the far end of the long wall; fill picks rows along the home walls | 0.745 | 0.879 | 3 | - | - |
| r3 | fill on the free stretch furthest from the stores so far (balances the checker's furniture offset); the ore store gets its carts (`lift` Mine, `belongs` fix) | 0.735 | 0.919 | 1 | - | - |
| r4 | fill goes on to 13 groups; jitter off the wall | 0.717 | 0.892 | 3 | - | - |
| r5 | home corner where the lead kind may stand (barrels: the back walls), a knot of barrels standing free | 0.759 | 0.871 | 1 | - | - |
| r6 | lights 3 per 100 tiles; more jitter (rows less ruled); a third wall only to balance | 0.714 | 0.849 | 2 | 100% (self) | 4.8 / 5.6 (self) |
| r7 | a knot is 2+ barrels or none; heaps 1.6 apart (no line of sacks down a wall); 2 carts at most | 0.723 | 0.900 | 2 | - | - |
| r7s2 | (seed 2) | 0.683 | 0.774 | 1 | - | - |
| r8 | ogre hoard: its sacks as the odd piece (7 had stood in a room); `cellar` kin of the storeroom | 0.723 | 0.900 | 1 | - | - |

Blind r6 (self-judged; an independent judge is queued in TO_JUDGE.md): I told all ten apart, but mostly by what the furnisher does not make: Westwood's stores sit in shaped
rooms (an alcove off a corridor, a fenced cell block, a cave with rock pillars) with ogres and skeletons in them. Of
what the furnisher does make, the giveaways were a line of sacks down a granary wall, one sack alone mid-floor and
four mine carts strewn about (all fixed in r7). The generated mean (4.8) is within 0.8 of Westwood's (5.6).

Left: rows along a wall still align more than Westwood's (align 0.71 against 0.45); 3 walls used against 2; a store
heaped in one corner of a two-door room can still read as bunched (offset 0.78, one room in ten). The shell (plain
rectangles) is the larger giveaway.

Independent blind judge (storeroom r8, run by the main session): accuracy 80%, generated 5.6 against Westwood's 4.2.
Its tells: clusters of sacks strung down a whole wall at regular gaps; single crates dead centre or one per corner;
three barrels in an evenly spaced row; an under-stocked middle lit by candelabras in the open corners. (Westwood lights
its stores with torches; the house rule [TP1-5] keeps candelabras indoors, so the lights stay candelabras.)

| Round | Change | AUC | Cross | Hard rooms | Blind |
|---|---|---|---|---|---|
| r9 | answering the judge: two fills in three grow a heap already standing (the next pieces touch its end) instead of a new cluster down the wall; the odd piece touches the heap; the stack of crates stands free as near the heaps as an aisle allows, never dead centre; lights 2 per 100 tiles | 0.761 | 0.908 | 0 | queued |

## Laboratory (Westwood: 19 rooms)

What Westwood's look like: nothing in the middle (0-0.02 covered more than 2.5 units from a wall); no cauldron, plant
or rug; 4-15 types (median 7); back walls 0.06-0.35 lined (median 0.15), workstations on every wall and the front walls
the most (10 of 16), bookcases often on the SE wall (Con07C, Wiz02B); small ones a desk or an alchemist's desk and a
bookcase; big ones a row of coils, 12 bookcases, a table with chairs.

| Round | Change | AUC | Cross | Hard rooms | Blind |
|---|---|---|---|---|---|
| ref | (as found: alchemy table on a rug with the cauldron in the middle, a conjuring circle of candelabras, plants, statues, a bench of 4 workstations with a hanging) | 0.999 | 0.967 | 8 (caps 4, must desk 4) | - |
| r1 | no middle groups, no cauldron, plants or rug; a desk with 2 bookcases, a bench of 3; coils on a wall; cover 0.17 -> 0.11; desk corner fix (below) | 0.967 | 0.892 | 8 | - |
| r2 | workstations singly in corners on any wall (`front_ok`) | 0.994 | 0.936 | 5 | - |
| r3 | `lined_goal` 0.15 (the decor pass had hung tapestries to the house's 0.38); the desk is the focal piece | 0.953 | 0.936 | 10 | - |
| r4 | the fill's `min_area` in cells (2.4 a tile: gargoyles and coils had stood in 40-tile rooms); desk centred | 0.957 | 0.881 | 10 (sparse) | - |
| r5 | `decor_max` 1 (decorate_walls hung one per 3.5 units of free back wall) | 0.946 | 0.833 | 8 | - |
| r6 | bookcases on the front walls: the checker forbids it (the camera sees their backs); reverted in r7 | 0.945 | 0.841 | 10 | - |
| r7 | fewer workstations in small rooms (the lab cap) | 0.948 | 0.876 | 10 (sparse) | - |
| r8 | the table with chairs and a jar from 38 tiles | 0.947 | 0.855 | 7 (3 door shells, 4 sparse) | queued |

What still gives them away: the back walls (0.47 lined against 0.15). Westwood's small labs hold a desk or an
alchemist's desk and a bookcase on 24-45 tiles, and its big ones stand their bookcases against the SE wall, which the
house rules forbid; meanwhile the checker's house rule wants a generated room at least as covered as Westwood's median
(0.097), so the pieces it needs go on the back walls. The two rules together keep the AUC near 0.95.

Shared changes in this round (kit/furnish.py):
- `wall_candidates`: a desk "toward the corner" keeps 0.1 more off the wall across its end. At CORNER_CLEAR its end
  stood 0.05 from that wall, under the snug fit's 0.1, so `at="corner"` never fitted a desk anywhere (the object
  knowledge agent's "the small laboratory gets no desk"). Turns failures into fits for every type's desk at a corner.
- Recipe keys, each a no-op unless a recipe sets it: `front_ok` (families a kind may stand on the front walls),
  `lined_goal` (instead of LINED_GOAL), `decor_max` (decorate_walls' count); GROUPS `labtable`.

## Shop (Westwood: 16 rooms)

What Westwood's look like: each shop keeps one trade, an apothecary's (potion shelves, a glowing jar, bookcases:
Con02a, War03b, War07A), an armourer's (pole arms, armour stands, trader's shelves, swords and shields hung: Con06a,
War01A, War07A) or a general store's (steel crates and barrels by the counter: Con03A, Con03B); 5-16 types (median 7),
no plants; coverage 0.06-0.13-0.28.

| Round | Change | AUC | Cross | Hard rooms | Blind |
|---|---|---|---|---|---|
| ref | (as found: every shop crates, barrels, sacks, racks, potion shelves and plants) | 0.907 | 0.962 | 2 | - |
| r1 | `trades` (new recipe key, kit/furnish.py `_trade`): each shop draws one of armourer, apothecary, general store, which narrows its types and skips steps; no plants; steel crates and barrels (SUPPLIES "steel"); hung swords and shields; must is the counter only | 0.851 | 0.971 | 3 | - |
| r2 | the top-up keeps to the trade (an apothecary had taken barrels) | 0.885 | 0.930 | 7 (sparse) | - |
| r3 | the apothecary's bookcases and jars (War07A: 3 bookcases, 4 jars; the house rule keeps potion shelves to a pair) | 0.861 | 0.901 | 8 | - |
| r4 | half-full bookcases allowed (the line completes with them) | 0.861 | 0.901 | 5 (2 way in, 1 bunched/sparse) | queued |

Still giving them away: rows (align 0.79 against 0.43: racks three to a row, stock in rows), four walls used against
three, the stock crowding (median gap 0.36 against 1.0).

Shared (kit/furnish.py), a no-op unless a recipe sets `trades`: `Furnisher._trade` filters `types_of`,
`supply_types` and the top-up and skips steps (`_skipped`); SUPPLIES gains "steel" (used only by the shop recipe).

## Library (Westwood: 7 rooms)

What Westwood's look like: the middle bare (0-0.03), no plants or curios, back walls 0.04-0.29 lined, a hearth in 3
of 7, a round or oval table with chairs (0.22 tables per 10 tiles), bookcases 2-17 (160 in Con07D's 494-tile hall).

| Round | Change | AUC | Cross | Hard rooms | Blind |
|---|---|---|---|---|---|
| ref | (as found: stacks of bookcases down the middle from 33 tiles, plants, telescopes and orreries, statues, both back walls lined) | 0.991 | 0.996 | 1 | - |
| r1 | no plants, curios or rugs mostly; a hearth (0.45); one back wall lined by the desk, the other filled; stacks only past 175 tiles; `lined_goal` 0.3; cover target 0.17 -> 0.13 | 0.871 | 0.993 | 8 (sparse) | - |
| r2 | a chest, two reading tables from 62 tiles | 0.884 | 0.986 | 7 (sparse) | - |
| r3 | the second back wall lined end to end (the user's HB-4), stacks from 100 tiles | 0.886 | 0.992 | 4 (3 sparse, 1 door shell) | - |

The tension: Westwood's libraries line their back walls 0.11 and keep the middle bare at 0.12 covered (their
bookcases stand on every wall, the front ones too); the checker forbids bookcases on the front walls and wants the room
as covered as Westwood's median, and the user wants a lined wall lined end to end. What gives ours away: lined back
walls (0.65), the desk on its back wall (Westwood's libraries have no desk), pieces touching end to end (nn 0.04).

## Armoury (Westwood: 16 rooms; kit kind gear_store)

What Westwood's look like: 3-13 types (median 6), supplies 0-0.73 per 10 tiles, no shelves; one or two racks, shown on
a back wall (the focal piece on NE or NW in all 16); swords, crossbows and shields hung on the walls; Dun Mir chests;
in 6 of 16 the guards' table with chairs (Con03A, Con05A, Con06a, Con06b, War03a/b).

| Round | Change | AUC | Cross | Hard rooms | Blind |
|---|---|---|---|---|---|
| ref | (as found: log shelves, rows of racks, every wall stocked with sacks, tool barrels and crates; 11-18 types) | 1.000 | 0.992 | 1 | - |
| r1 | racks against the walls and a row only in a big room, hangings of arms, a chest, one heap of barrels (`store_heaps`); no shelves or sacks; cover 0.24 -> 0.12 | 0.977 | 0.869 | 1 | - |
| r2 | fewer racks: too sparse, racks on the front walls (FRONT_FAMS) | 0.997 | 0.944 | 5 | - |
| r3 | `back_only` (new recipe key): racks shown on the back walls | 0.997 | 0.893 | 3 (bunched) | - |
| r4 | one standing rack (two in all), two chests, the guards' table with chairs (the profile's never-table dropped: Westwood's evidence) | 0.942 | 0.877 | 4 (3 bunched, 1 sparse) | - |

Left: runs of 3 of one kind (the hangings of arms side by side), the pieces bunched toward the home corner in big
rooms, sparse big rooms. Shared: recipe key `back_only` (wall_candidates treats those families as faced), a no-op
elsewhere.

## Barracks (Westwood: 16 rooms, 12 of them the ogres'; kit kinds barracks, ogre_den)

What Westwood's ogre barracks look like (Con05C, Con09c, Con11a, War02A): no fire pit; straw heaped on the floor the
commonest piece (most_share 0.64), barrels in a knot, a crude bed or three, a table with a bench and a stool or two
in some, meat, a primitive obelisk; coverage 0.03-0.06-0.20.

| Round | Change | AUC | Cross | Hard rooms | Blind |
|---|---|---|---|---|---|
| ref | (as found: the ogre den round a fire pit ringed by stools, two to five pits in a big den) | 0.999 | 0.943 | 1 | - |
| r1 | ogre den: no fire pit; straw scattered (9 per 100 tiles), beds, a knot of barrels (`store_heaps`), a crude table with stools, meat, an obelisk in a big one; cover 0.14 -> 0.09; torch poles 2 per 100 tiles | 0.873 | 0.873 | 4 (3 one-kind) | - |
| r2 | the table only past 54 tiles; less straw in the fill | 0.786 | 0.863 | 6 | - |
| r3 | straw 6 per 100 tiles (a big den was 2/3 straw: the checker's monotony); `cell` kin of the barracks (a den of straw reads as a pen) | 0.856 | 0.886 | 1 (a town barracks' bed cap) | - |

Left: walls used 4 against 2, the town barracks (2 of 10 variants) untouched.

## Crypt (Westwood: 25 curated rooms)

What Westwood's look like (Con04a-c, War03b-d): 1-5 types (median 2), two to six sarcophagi in short rows, all aligned
(align 1.0), none against a wall and none far from one, a crypt chest; 0.67 tombs per 10 tiles, coverage 0.08.

| Round | Change | AUC | Cross | Hard rooms | Blind |
|---|---|---|---|---|---|
| ref2 | (after the curated references; as found: long rows of sarcophagi and coffins, columns, statues, tapestries, plants) | 0.999 | 0.965 | 2 | - |
| r1 | sarcophagi and tombstones along the walls, a chest: wrong way (Westwood's stand free of the walls) | 0.982 | 0.859 | 8 | - |
| r2 | rows again, capped at a tomb per 12 tiles (6 at most); no columns, tapestries, plants | 0.950 | 0.938 | 3 | - |
| r3 | `wall_gap` (new recipe key): sarcophagi along the walls a pace out | 0.974 | 0.777 | 1 | - |
| r4 | two rows with a wide aisle (3.6) so each keeps near its wall; the pace-out tombs only in the fill | 0.886 | 0.751 | 5 (2 chests across a wall, 2 sparse, 1 reads as mausoleum) | - |

## Storeroom, after the curated references and the independent judges

The curated references (7 true storerooms) are fuller: coverage median 0.16, 0.38 pieces a tile, 4 types, the
commonest kind 0.40, no lights in the room. Independent judge of r9: 9/10, generated 5.0 against Westwood's 5.4; its
tells: barrels in evenly stepped lines and staircases, sacks sprinkled over the floor, one or two kinds only,
candelabras.

| Round | Change | AUC | Cross | Hard rooms | Blind |
|---|---|---|---|---|---|
| r10 | `_heap` builds a clump: each piece touches one already in the heap at a random bearing, within 3 units of the wall, a piece in four of the room's other kinds; bigger heaps (4-6) | 0.839 | 0.912 | 1 | - |
| r11 | a second kind in 95% of rooms, an odd piece in 80%, two kinds in a heap 40% of the time; no lights in a store (`lights_per100` 0: Westwood's have none inside; the house rule keeps torches out of houses) | 0.777 | 0.931 | 1 | - |
| r12 | cover target 0.13 -> 0.17 (the curated median 0.16) | 0.761 | 0.925 | 1 | - |
| r13 | clumps compact (along the wall penalised over depth): no line of casks down a wall | 0.726 | 0.903 | 1 | - |
| r14 | an odd kind twice a room at most | 0.771 | 0.910 | 1 | - |
| r15 | no stretch left: a clump in another corner | 0.736 | 0.904 | 1 | - |
| r16 | a heap's first piece slides along when its spot is taken | 0.781 | 0.809 | 0 | queued |
| r16s2 | (seed 2) | 0.891 | 0.839 | 3 | - |
