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
| bedroom | c9 | C:\GOG Games\Nox\dystopiannox-wt\motifs2\review\out\roomlab\bedroom\c9\blind | Westwood's groups placed whole (bed with nightstands and chest, desk with its chair drawn up); the bed group on the back wall across from the door; no lone chairs; zones of Westwood's room size in large rooms; carpets as Westwood's larger bedrooms lay them; hangings at Westwood's rate | |
| storeroom | s5 | C:\GOG Games\Nox\dystopiannox-wt\motifs2\review\out\roomlab\storeroom\s5\blind | stock on the back walls in heaps, front walls mostly bare, the way in kept clear 4 units deep, kinds of store mixed (no kind past 40%), free heaps only in rooms of 60+ tiles, the ore store's cart | |
