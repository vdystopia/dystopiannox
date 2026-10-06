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
