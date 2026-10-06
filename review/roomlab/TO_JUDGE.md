# Blind sheets for an independent judge (tuneA)

Each line: type, iteration, the blind folder. Judge by review/roomlab/JUDGE.md from the pictures alone (never
blind_key.json). The tuner's own judgements, where there are any, are in each folder's judge.json (self, too generous):
overwrite or set them aside.

## Judged (results from the main session)

| Type | Iteration | Note | Result (accuracy, generated / Westwood) |
|---|---|---|---|
| bedroom | ref | before | 6/10, 6.4 / 6.0 |
| bedroom | r6 | Westwood stamp (dropped) | 8/10, 4.8 / 5.8 |
| living_room | r6 | | 8/10, 6.0 / 4.6 |
| bedroom | r7 | ref's composition, Westwood's proportions (dropped) | 9/10, 4.8 / 6.6 |
| kitchen | ref | before | 10/10, 5.0 / 5.8 |
| kitchen | r8 | Westwood's pieces (dropped) | 10/10, 3.4 / 5.8 |

## Judged, second batch (after the renderer fix)

| Type | Iteration | Result (accuracy, generated / Westwood) |
|---|---|---|
| bedroom | r10 | 8/10, 5.6 / 7.4 |
| kitchen | r11 | 10/10, 5.0 / 4.2 (thin pool) |
| living_room | r10 | 10/10, 4.6 / 6.6 |
| guardroom | r8 | 9/10, 5.4 / 5.4 |
| cell | r4 | 10/10, 3.8 / 7.2 |
| infirmary | r2 | 10/10, 4.6 / 4.0 (kin rooms) |

## Queued (third batch: the judge's faults from the second batch taken out; one sheet per type)

| Type | Iteration | Blind folder | What changed since the judged round | Result |
|---|---|---|---|---|
| bedroom | j6 | C:\GOG Games\Nox\dystopiannox-wt\tuneA\review\out\roomlab\bedroom\j6\blind | the bed centred on a back wall, the desk on a back wall, the table drawn off the centre, a second nightstand and bookcases on the other back wall (fuller: Westwood's 0.147 cover) | |
| kitchen | j2 | C:\GOG Games\Nox\dystopiannox-wt\tuneA\review\out\roomlab\kitchen\j2\blind | the pot always beside the hearth, stores fewer and heaped, provision shelves on the second back wall | |
| living_room | j6 | C:\GOG Games\Nox\dystopiannox-wt\tuneA\review\out\roomlab\living_room\j6\blind | barrels heaped by the stock pass 2.4 off the fire, a bench drawn up before the hearth, no stamped benches, no second set on a rug | |
| guardroom | j3 | C:\GOG Games\Nox\dystopiannox-wt\tuneA\review\out\roomlab\guardroom\j3\blind | two cots side by side on a back wall, no pennants, the table off the corner | |
| cell | j1 | C:\GOG Games\Nox\dystopiannox-wt\tuneA\review\out\roomlab\cell\j1\blind | pens: the stocks with one straw heap before them (Westwood's Con11a), the obelisk; fewer straw mats | |
| infirmary | j3 | C:\GOG Games\Nox\dystopiannox-wt\tuneA\review\out\roomlab\infirmary\j3\blind | 3-9 cots (was up to 10 stamped), one pair of potion shelves and two bookcases, not a lined wall | |
| study | r4 | C:\GOG Games\Nox\dystopiannox-wt\tuneA\review\out\roomlab\study\r4\blind | re-rendered after the renderer fix (queued earlier as r3) | |
| solar | r4 | C:\GOG Games\Nox\dystopiannox-wt\tuneA\review\out\roomlab\solar\r4\blind | re-rendered after the renderer fix (queued earlier as r3) | |

# Motif engine, round 2 (night-motifs2): clusters, zones, a centrepiece

Built with `py tests/roomlab.py <type> --iter <iter> --engine motifs` (seed 1, n 10) after merging the lab-fairness
fixes (master 474c927: creature-free renders, paired sizes, Westwood's door counts). The builder has not judged them.
After judging, write `blind/judge.json` and run `py review/roomlab/blind.py score <type> <iter>` from this worktree.

| Type | Iteration | Blind folder | What changed since the judged motif round (bedroom 6/10, storeroom 7/10) | Result |
|---|---|---|---|---|
| bedroom | c13 | C:\GOG Games\Nox\dystopiannox-wt\motifs2\review\out\roomlab\bedroom\c13\blind | Westwood's groups placed whole (bed with nightstands and chest, desk with its chair drawn up); the bed group on a back wall where Westwood's stand from the door (across from it or beside it), about 0.7 of the room's diagonal from it; no lone chairs; zones of Westwood's room size in large rooms; carpets as Westwood's larger bedrooms lay them; hangings at Westwood's rate | |
| storeroom | s6 | C:\GOG Games\Nox\dystopiannox-wt\motifs2\review\out\roomlab\storeroom\s6\blind | stock on the back walls in heaps, front walls mostly bare, the way in kept clear 4 units deep, kinds of store mixed (no kind past 40%), free heaps only in rooms of 60+ tiles, the ore store's cart | |

# Placement grammar (night-grammar): Westwood's placement rules, both engines' last pass

Built with `py tests/roomlab.py <type> --iter g3 [--engine motifs]` (seed 1, n 10) with `mapgen/kit/grammar.py`'s audit
on (the rules measured on the curated campaign rooms by `rules/grammar.py`). One sheet per type, the better engine of
the final round. The builder has not judged them. After judging, write `blind/judge.json` and run
`py review/roomlab/blind.py score <type> <iter>` from this worktree. Before (same seed, audit off): iterations `ref`
(recipe) and `refm` (motifs) in the same folders.

| Type | Iteration | Engine | Blind folder | What changed (the judges' faults) | Result |
|---|---|---|---|---|---|
| bedroom | g3m | motifs | C:\GOG Games\Nox\dystopiannox-wt\grammar\review\out\roomlab\bedroom\g3m\blind | lights beside the bed head, a desk or shelf, or in a corner, never loose or at the bed's foot; no lone chair; no plants | |
| storeroom | g3 | recipe | C:\GOG Games\Nox\dystopiannox-wt\grammar\review\out\roomlab\storeroom\g3\blind | no stepped rows or even gaps of stock; lone stock joins a heap by a back wall | |
| living_room | g3 | recipe | C:\GOG Games\Nox\dystopiannox-wt\grammar\review\out\roomlab\living_room\g3\blind | the way to the hearth open (a bench drawn up beside it, not square before it); table sets by a wall or on a carpet laid to them; no lone barrels or benches; no chairs at even quarter points; lights by walls | |
| kitchen | g3m | motifs | C:\GOG Games\Nox\dystopiannox-wt\grammar\review\out\roomlab\kitchen\g3m\blind | placement only (contents untouched): no lone barrels in corners or open floor, no stock heaps mid-floor, lights by walls | |
| laboratory | g3m | motifs | C:\GOG Games\Nox\dystopiannox-wt\grammar\review\out\roomlab\laboratory\g3m\blind | candelabras by the shelves and benches or in corners, not out in the room; no floating table | |
| shop | g3m | motifs | C:\GOG Games\Nox\dystopiannox-wt\grammar\review\out\roomlab\shop\g3m\blind | lights by the counter or shelves, none loose; lone barrels and crates heaped | |
| tavern | g3 | recipe | C:\GOG Games\Nox\dystopiannox-wt\grammar\review\out\roomlab\tavern\g3\blind | no plants; lights by walls (two to a wall at most, none side by side); table sets anchored; no twin sets, rings of stools or stepped rows | |
| guardroom | g3 | recipe | C:\GOG Games\Nox\dystopiannox-wt\grammar\review\out\roomlab\guardroom\g3\blind | no barrel to each corner, no lights side by side on the floor, chairs drawn up, tables by a wall or rug | |

## Queued (shells2: purposeful second floors and carpets, one sheet per type)

Before: `fair1` (main) and `sh0` here, the judges' faults: brick squares scattered with no relation to the tombs, corner patches,
a brick band along one wall, plank floors in throne rooms.

| Type | Iteration | Blind folder | What changed | Result |
|---|---|---|---|---|
| crypt | sh3 | C:\GOG Games\Nox\dystopiannox-wt\shells2\review\out\roomlab\crypt\sh3\blind | GreenBrick floors (Westwood's crypt floor); a stone plinth under each tomb (a band under a row); no scattered brick squares | |
| chapel | sh3 | C:\GOG Games\Nox\dystopiannox-wt\shells2\review\out\roomlab\chapel\sh3\blind | stone floors (no planks); no scattered patches; the carpet down the aisle as before | |
| throne_room | sh3 | C:\GOG Games\Nox\dystopiannox-wt\shells2\review\out\roomlab\throne_room\sh3\blind | stone floors, never planks; no strips along the walls | |
| bedroom | sh3 | C:\GOG Games\Nox\dystopiannox-wt\shells2\review\out\roomlab\bedroom\sh3\blind | the carpet at the bed's foot; no stray second floors | |
| living_room | sh3 | C:\GOG Games\Nox\dystopiannox-wt\shells2\review\out\roomlab\living_room\sh3\blind | a brick hearthstone before the fireplace; carpets under the seating; no strips, corner patches or inlaid squares | |
| great_hall | sh3 | C:\GOG Games\Nox\dystopiannox-wt\shells2\review\out\roomlab\great_hall\sh3\blind | a hearthstone before the fireplace; carpets under the tables; second floors only as a border or a wing | |

## Queued (night-variety: archetypes, several Westwood layouts per type; one sheet per type)

The judges' top giveaway: "one template per type repeated across variants". Each type's curated campaign rooms are now
clustered into archetypes (`mapgen/kit/archetypes.py`, each brief's "Archetypes"), each room draws one by Westwood's
frequencies, spread over the batch, and the engines compose from it. Built with `py tests/roomlab.py <type> --iter <it>
[--engine motifs]` (seed 1, n 10) after merging master (shells2, bf457ea). Before: the same seed with
`NOX_ARCHETYPES=0` (iterations `v0` recipe, `m0` motifs, in the same folders). The builder has not judged them. Template:
the batch's mean pairwise layout similarity (`metrics.template`; lower is more varied) against Westwood's spread for the
type (p50, p90 of the same mean over draws of its rooms; a thin type's with the kin rooms its archetypes name). After
judging, write `blind/judge.json` and run `py review/roomlab/blind.py score <type> <iter>` from this worktree.

| Type | Iteration | Engine | Blind folder | What changed | Measured (before -> after) | Result |
|---|---|---|---|---|---|---|
| throne_room | v3 | recipe | C:\GOG Games\Nox\dystopiannox-wt\variety\review\out\roomlab\throne_room\v3\blind | four archetypes: processional (fire basins in pairs down a runner, a pair or two of columns), dressed walls (no runner, hangings end to end, columns by the side walls, statues along the walls), ringed seat (the throne out from the wall between lights and columns, a square of statues before it, chests), audience chamber (the throne between statues, a pair of columns, nothing else) | template 0.717 -> 0.555 (Westwood p50 0.171, p90 0.197); AUC 0.871 -> 0.869 | |
| great_hall | v2 | recipe | C:\GOG Games\Nox\dystopiannox-wt\variety\review\out\roomlab\great_hall\v2\blind | three archetypes: hearth in the round (a free hearth in the middle with boards round it, shields and banners), feast hall (the wall hearth, many small tables of mixed kinds along the walls and over the floor), long boards (boards in parallel on a great carpet); an L room's arm takes a set | template 0.459 -> 0.311 (Westwood p50 0.16, p90 0.23); AUC 0.875 -> 0.876 | |
| crypt | v3 | recipe | C:\GOG Games\Nox\dystopiannox-wt\variety\review\out\roomlab\crypt\v3\blind | four archetypes: tomb niche (one or two sarcophagi off the middle), tomb row (rows of sarcophagi side by side), wall tombs (sarcophagi a pace off the walls, a chest in the middle), tombstone yard (tombstones in a loose grid, no sarcophagi) | template 0.27 -> 0.368 (Westwood p50 0.287, p90 0.372); AUC 0.94 -> 0.882 | |
| chapel | v2 | recipe | C:\GOG Games\Nox\dystopiannox-wt\variety\review\out\roomlab\chapel\v2\blind | three archetypes: pewed nave (pews either side of the aisle, columns among them, no tomb slab), sanctum (the altar in the middle ringed by obelisks on a carpet, a few pews), colonnade chapel (the altar at the end of a colonnade, statues facing across, a few pews) | template 0.37 -> 0.362 (Westwood p50 0.093, p90 0.12); AUC 0.98 -> 0.936 | |
| shop | v2 | recipe | C:\GOG Games\Nox\dystopiannox-wt\variety\review\out\roomlab\shop\v2\blind | three archetypes: lined walls (a pair of potion shelves and bookcases on the back walls, the counter, a cauldron), stock heaps (steel crates and barrels heaped down the walls, the counter at the end), showroom (racks on the walls and standing free, the counter among them) | template 0.288 -> 0.216 (Westwood p50 0.148, p90 0.177); AUC 0.975 -> 0.896 | |
| laboratory | v2 | recipe | C:\GOG Games\Nox\dystopiannox-wt\variety\review\out\roomlab\laboratory\v2\blind | three archetypes: study lab (the desk on a back wall, one workstation apart, the floor bare), work wall (workstations side by side along one wall, the desk on the other), zoned lab (bookcases lining, a workbench at the far end, the table set away from the desk) | template 0.474 -> 0.339 (Westwood p50 0.164, p90 0.181); AUC 0.918 -> 0.742 | |
| tavern | v2 | recipe | C:\GOG Games\Nox\dystopiannox-wt\variety\review\out\roomlab\tavern\v2\blind | four archetypes: common room (the recipe), hearth hall (two free hearths, round tables clustered at one end, a short bar), barroom (the bar and casks, little seating), drinking room (round tables by the walls, no bar or hearth) | template 0.522 -> 0.434 (Westwood p50 0.262, p90 0.292); AUC 0.908 -> 0.907 | |
| bedroom | m2 | motifs (zone plans from the archetype's Westwood rooms) | C:\GOG Games\Nox\dystopiannox-wt\variety\review\out\roomlab\bedroom\m2\blind | four archetypes: cot room (bed, nightstand, chest, a bookcase at most), bed and desk (bed on one back wall, desk on the other, bookcases with either or none), sitting end (the bed in a corner, a table set at the far end), lord's room (the bed, an oval table free on a rug, trophies, a desk) | template 0.225 -> 0.209 (Westwood p50 0.195, p90 0.227); AUC 0.677 -> 0.83 | |
| living_room | v2 | recipe | C:\GOG Games\Nox\dystopiannox-wt\variety\review\out\roomlab\living_room\v2\blind | four archetypes: hearth nook (the hearth and the table by it, a bench, barrels), parlour (the hearth between bookcases, two tables on a carpet), common room (sets apart, bookcases on a wall), cottage (an iron stove and a bed, no hearth, chests, the table on a rug) | template 0.326 -> 0.28 (Westwood p50 0.219, p90 0.236); AUC 0.935 -> 0.864 | |
| kitchen | v2 | recipe | C:\GOG Games\Nox\dystopiannox-wt\variety\review\out\roomlab\kitchen\v2\blind | four archetypes: pantry kitchen (the recipe), cookhouse (the wall hearth with iron stoves, barrels heaped, work tables), stove kitchen (a stove in a corner and a table), open hearth (a free hearth in the middle, the stove and tables by the walls) | template 0.452 -> 0.335 (Westwood p50 0.146, p90 0.194); AUC 0.995 -> 0.97 | |
