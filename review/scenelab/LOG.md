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

## bandit_camp

| Round | What changed (mapgen/kit/camps.py unless said) | AUC | Blind acc. | Blind gen / WW | Hard |
|---|---|---|---|---|---|
| baseline | | 1.00 | 100% | 3.6 / 7.2 | 0 |
| r1-hideout | Westwood's camp evidence widened (outdoor cots and pup tents are camps too: Wiz03a, Wiz03b); bedrolls in pairs with a gap (58 px), not blocks; one bench, an occasional stool, no cauldron at the fire's front (25%), no straw dummy; barrels clustered and crates paired against the wall (`_snug`); fewer racks | 0.996 | | | 0 |
| r2-backed | `camp_site` prefers a site whose nearest wall is just beyond the camp (a camp backs onto the wood's edge or cliff); the back faces a wall 150-300 px off; typed pieces may stand snug to a wall by `spacing.off_walls` (they had kept a whole cell off); a rock outcrop it shelters by; the wood may come up to the beds (`_hold_ground` 8.5 -> 6 squares) | 0.98 | | | 0 |
| r3-wallrow | the sleeping row runs along the back wall: tent, its bedrolls beside it, tent...; a lone sleeper's bedroll joins a pair (never alone, GW-4), pairs laid whole or not at all; one kind of barrel, crate, rack and boulder to a camp; the lookout nearer, mostly without stool and quiver; awning parts count as one kind in the lab (both sides) | 0.97-1.00 | 100% | 5.4 / 6.6 | 0 |

r3 judge: "Much better: clear zones and the user's structure. Still given away by the sleeping row laid tent-pair-tent-pair
in a perfectly even line, the bench and chest crowding the fire's back, and a lookout set far off across empty grass."
The classifier's own floor (Westwood against Westwood, random halves) is 0.56 +/- 0.2 for camps.
