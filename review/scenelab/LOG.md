# Scene lab: iteration log

One entry per round: what changed in the kit, and how the scores moved. AUC: the metric judge's classifier (Westwood
against generated, cross-validated; target at most 0.60). Blind: the visual judge's accuracy and the mean scores of the
generated and Westwood pictures (targets: accuracy at most 60%, generated at least Westwood minus 0.5). The visual
judge is the tuning agent itself (not truly blind: read its scores and critiques more than its accuracy).

## Baselines (2026-10-05, seed 1, the kit as on branch night-scenes at edad925)

| Scene | Westwood scenes | AUC | Blind acc. | Blind gen / WW | Hard-rule scenes | Missing |
|---|---|---|---|---|---|---|
| bandit_camp | 20 | 1.00 | 100% | 3.6 / 7.2 | 0 | 0 |
| graveyard | 16 | 1.00 | | | 1 | 1 |
| garden | 6 | 0.88 | | | 3 | 3 |
| pond_dock | 4 | 0.68 | | | 0 | 0 |
| ogre_camp | 5 | 0.98 | | | 0 | 0 |
| well | 5 | 0.80 | | | 8 | 8 |
| market_stall | 4 | - | | | 10 | 10 |
| wagon | 7 | 1.00 | | | 5 | 5 |
| urchin_camp | 49 | 1.00 | | | 0 | 0 |
| smithy_yard | 2 | 1.00 | | | 2 | 2 |
| training_ground | 0 | - | | | 1 | 1 |
| woodpile | 3 | 0.98 | | | 1 | 1 |
| shrine | 32 | 1.00 | | | 0 | 0 |
| farmyard | 6 | 0.99 | | | 1 | 1 |
| wolf_den | 4 | 0.97 | | | 0 | 0 |
| quarry | 2 | 0.96 | | | 4 | 4 |
| jail | 17 | 0.98 | | | 0 | 0 |

"Missing": the recipe could not lay the scene in that clearing (the catalogue's town themes need a town round them:
a well, a market stall, a wagon by a road), a lab gap more than a kit fault; fixed in the lab's recipes as rounds go.

### bandit_camp baseline, the blind judge
"Every generated camp stamps the same template in the middle of its glade (bench T and cauldron at the fire, tents with
bedrolls packed in a block behind, crates in a touching row with a cart); Westwood's camps are sparse, use their walls
and spread their beds one by one." One camp backed its cart into the pond.
