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
| r6 | lights 3 per 100 tiles; more jitter (rows less ruled); a third wall only to balance | 0.714 | 0.849 | 2 | 100% | 4.8 / 5.6 |
| r7 | a knot is 2+ barrels or none; heaps 1.6 apart (no line of sacks down a wall); 2 carts at most | 0.723 | 0.900 | 2 | - | - |
| r7s2 | (seed 2) | 0.683 | 0.774 | 1 | - | - |
| r8 | ogre hoard: its sacks as the odd piece (7 had stood in a room); `cellar` kin of the storeroom | 0.723 | 0.900 | 1 | - | - |

Blind r6: I told all ten apart, but mostly by what the furnisher does not make: Westwood's stores sit in shaped
rooms (an alcove off a corridor, a fenced cell block, a cave with rock pillars) with ogres and skeletons in them. Of
what the furnisher does make, the giveaways were a line of sacks down a granary wall, one sack alone mid-floor and
four mine carts strewn about (all fixed in r7). The generated mean (4.8) is within 0.8 of Westwood's (5.6).

Left: rows along a wall still align more than Westwood's (align 0.71 against 0.45); 3 walls used against 2; a store
heaped in one corner of a two-door room can still read as bunched (offset 0.78, one room in ten). The shell (plain
rectangles) is the larger giveaway.
