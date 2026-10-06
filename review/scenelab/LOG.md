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

Westwood's evidence was deduplicated after graveyard r3 (the same place in two layout groups, Galava's yard in Con07B
and War07A, counted once): bandit camps 20, graveyards 16 -> 13. Numbers after that are on the deduplicated set.

## graveyard (mapgen/kit/yards.py `_graveyard`, YARDS, `plan`)

| Round | What changed | AUC | Blind acc. | Blind gen / WW | Hard |
|---|---|---|---|---|---|
| baseline | | 1.00 | (not judged) | | 1 missing |
| r1-sparse | the yard's ground sparse grass (Westwood's GrassSparse2); graves in rows 2.4 squares apart, a third on dug earth; stone pillars by the gate (Monument1); a dead tree or two; no bench, no cross between urns, no corner torches; the gravedigger's corner kept (the user: "a bucket of tools") in 65% of yards, with a torch pole to work by; `plan` falls back to a smaller plot rather than dropping the yard; the lab plans with `plan_any` as the designs do | 0.96 | 100% | 6.0 / 7.2 | 0 |
| r2-loose | graves a little out of true, an unused plot now and then; trees only by the fence, inside it (dead or leafy), never among the graves | 0.93 | | | 0 |
| r3-spaced | graves 2.7-2.8 squares apart (Westwood's nearest 88-97 px); the digger's corner lighter (no spoil, no pick) | 0.94 | 100% | 6.0 / 7.6 | 0 |
| r4-larger | yard sizes up to 14 x 11 (Westwood's big yards are 16 x 16): AUC 0.80 on the deduplicated evidence, but Harrowby's bigger yard cut off a corner of the map (2 unreachable creatures), so reverted | 0.80 | 100% | 6.0 / 6.8 | 0 |
| r5-kept | the kit as kept (r3 with the sizes 10 x 9 to 11 x 10) | 0.87 | | | 0 |

r4 judge: "Inside the fence the generated yards hold Westwood's headstones, spacing and ground; they still read as one
shape (a small square box in a glade) where Westwood's are long or large and set against buildings and crypts."
Ambermere, Starwell and Harrowby build with 0 errors.

## garden (mapgen/kit/village.py `Village.garden`)

Westwood's gardens (Con05A, Con07B, Con09a, Wiz01A, Wiz03b): beds of two or three crops (the kit's note "one crop
each" was wrong), rows ~22 px apart, mostly unfenced (a built wall within two cells of 9% of their pieces), on grass
more often than dug earth, a water barrel, flowers, a well or a tree about them.

| Round | What changed | AUC | Blind acc. | Blind gen / WW | Hard |
|---|---|---|---|---|---|
| baseline | | 0.89 | (not judged) | | 3 missing |
| r1-beds | beds side by side, a different crop in each, two rows to a bed (one when the plot is narrow), a grass strip between; the rows laid in the fence's frame (the half-square offset of AM-1: a first try put a row on the fence line); dug earth in 40%; a water barrel and a spade at the path's ends; most unfenced; a smaller garden when no room (down to 3 x 2); the lab furnishes its houses and counts a clearing without room as "missing", not a broken rule | 0.42 | 100% | | 0 |
| r2-fence | the garden fence is Westwood's low wooden one (Dilapidated, Wiz01A), not Log (drawn as a cabin wall) | 0.16 | 90% | 6.0 / 7.4 | 0 |
| r3-larger | a size up first where it fits; flowers at a bed's end now and then | 0.30 | 100% | 5.8 / 7.4 | 0 |

AUC sits under 0.6 from r1 (Westwood has only 5 gardens: read it loosely). The judge in r2 opened the key after fixing
its guesses (recorded unchanged). r3 judge: "Kitchen gardens beside houses now read right; the field yard's log-wall
fence is the clearest giveaway, and the gardens are still smaller and barer round the edges than Westwood's." The
town field (`yards` "field", Log fence) is outside this round. Ambermere, Starwell, Harrowby, Greywatch, Thornwick: 0
errors.

## pond_dock (mapgen/kit/water.py `Waterworks.dock`, `_shore_start`, `_dock_gear`)

Westwood's docks (Con05A's three DockDown runs, Con03A's DockUp; War03a's DockUp is three pieces too): out into a big
lake, barrels, a crate, rocks on the bank by the root (store 0.22, rock 0.14 of the pieces).

| Round | What changed | AUC | Blind acc. | Blind gen / WW | Hard |
|---|---|---|---|---|---|
| baseline | | 0.68 | (not judged) | | 0 |
| r1-gear | the fishers' gear on the bank by the root (`_dock_gear`, its own generator): barrels touching on one side, a crate or a rock on the other; the lab's ponds at a lake's scale (6-8 tiles) | 0.80 | | | 2 (AM-2: DockUp 35-40 degrees off square) |
| r2-square | the shore's normal read over the checker's ring (ten cells) and held within 20 degrees; `dock("best")` prefers the long DockDown run (Westwood's usual dock) unless DockUp lands much nearer the road | 0.76 | 100% | 6.0 / 6.75 | 0 |
| r3-bank | the gear tries the other bank when one side has no room; water bubbles count as nature in the lab (both sides) | 0.77 | 100% | 6.6 / 6.75 | 0 |

r3: generated mean within 0.5 of Westwood's. The judge knows Westwood's four dock scenes by heart, so blind accuracy is
not meaningful for this type. Ambermere (dock yes) and DysVale build with 0 errors, warnings unchanged.
