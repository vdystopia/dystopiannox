# DysVale v0.3 — visual review (2026-10-03)

The first map built with generator v2 (`kit/layout.py`, `kit/vegetation.py`, `kit/village.py`).
Sheet: `review/out/DysVale/sheet.png`, compared with Con03A, Con08a and Con05A. Checker: 0 errors,
4 warnings (no creatures yet; one road-against-floor seam, which Westwood also leaves in 23 maps;
furniture against a wall; a small tavern).

| # | Criterion | v0.2 | v0.3 | What the sheet shows now |
|---|---|---|---|---|
| 1 | Silhouette | 1 | **4** | Six areas joined by long winding forest corridors in a loop, with side pockets. It reads like Con03A's branching corridors. Corridor widths are a little more even than Westwood's |
| 2 | Flow | 1 | **4** | A dirt road runs down every corridor to a cobbled village square with a well, and doorstep paths join the doors. Path share is 19.5% (Westwood typically 19%). The network is more perfectly joined than Westwood's |
| 3 | Settlement | 2 | **3** | Six buildings sit close around the square, facing the roads, with gardens, barrels and benches. Some bare grass remains between them; Con05A and Con08a are denser and have more buildings |
| 4 | Vegetation | 1 | **4** | Tree lines several deep in front of the forest walls (95% of trees line an edge; Westwood 83–100%), groves in the open, and undergrowth and flowers in single-type patches (47%; Westwood 23–62%) |
| 5 | Water | 2 | **3** | The stream comes out of the forest, passes under the mill road at a plank bridge, then runs beside the woodcutter's road before turning back into the forest. The mill pond has a dock. Its banks are plainer than Westwood's |
| 6 | Every screen | 2 | **3** | Screens now alternate between village, square, forest corridor, waterside and clearings. Some corridor screens are just road and trees |
| 7 | Interiors | 3 | **3** | Rooms read as their purpose. The furnisher still sometimes puts a piece against a wall cell, and the tavern is small for a tavern |

**Verdict:** ready for playtesting (every criterion 3+, no checker errors).

Next improvements:
- creatures and townsfolk (none yet: Westwood has 0.14–2.15 per 100 tiles)
- denser villages with more buildings
- dressed stream banks (rocks, reeds)
- corridor width variety
- the furnisher's wall placement
