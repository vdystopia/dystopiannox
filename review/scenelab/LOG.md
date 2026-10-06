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

| r4-irregular | the sleeping row's gaps uneven (0.85-1.3 of a slot, a little in and out from the wall); the take (chest) at the row's end by the leader's bed, off the fire's bench; the lookout nearer (190 px); a camp with no sleepers lays no row (Greywatch's gully camp) | 0.98 | 100% | 6.0 / 6.8 | 0 |

r3 judge: "Much better: clear zones and the user's structure. Still given away by the sleeping row laid tent-pair-tent-pair
in a perfectly even line, the bench and chest crowding the fire's back, and a lookout set far off across empty grass."
The classifier's own floor (Westwood against Westwood, random halves) is 0.56 +/- 0.2 for camps.
r4 judge: "The generated camps now have Westwood's bones (things against the edge, beds in ones and twos, a sparse
hearth); still given away by an open forest glade with empty grass in the middle, more people and more kinds of thing
than Westwood's sparse hideouts." Westwood's camp evidence mixes cave hideouts without fires (Wiz03a, Wiz03b) and town
fire rings: an AUC under 0.6 would need the camp to be one of those, not the camp the user asked for.

### bandit_camp, round 2 (night-scenes3, 2026-10-05)

Starting point: the independent blind judge on r4-irregular: 10/10 told apart, generated 5.2 against Westwood's 6.8
("a stamped sleeping row, tent, two cots, tent, two cots; a crowded hearth, the bench tangent to the fire, four people
within 60 px; stray props in open grass, a crystal mid-glade, a lone cauldron, a single crate by the trees, the awning
stranded at the edge; the glade too big, half of it empty"). Westwood's 20 camps re-read: two families, the war camps
(Con03A, Con04a, Con05A, Con09d: one pup tent, a row of three or four armour racks of different builds, helmet poles,
barrels, a cart, the fire ring, no bedrolls) and the cave hideouts (Wiz03a, Wiz03b, Wiz03c, War03a, War05A: cots against
the rock, barrels, rocks, wall torches, often no fire).

| Round | What changed | AUC | Blind | Hard |
|---|---|---|---|---|
| ref | the kit as merged (r4-irregular) | 0.98 | (independent) 10/10, 5.2 / 6.8 | 0 |
| r1-warband | radii ~0.8 (row 165, store 170, lookout 170); scale capped at 1.0 (a big glade does not make a big camp); the arms a row of two to four armour racks of different builds with the helmet poles or a polearm (Westwood's war camps); the bench 40%, else a stool; pot 10%; sack 15%; quiver 20%; one kind of barrel | 0.99 | | 0 |
| r2-onetent | one pup tent to a camp, the awning beside it with a big band, in the row's middle; the outcrop at one end, half the camps, three stones; crates both or none; the dig's finds by the spoil; `camp_site` prefers 5 squares of open ground (backs onto the wood) | 0.985 | | 1 (pile: crates 39 px from the barrels) |
| r3-tentbeds | two sleep in the tent and two under the awning (Westwood lays no bedrolls by its tents); the rest on bedrolls in pairs, a lone one beside the tent; an awning with no room becomes a pair (it had become a second tent); crates 76 px along | 0.947 | | 0 |
| r4-fewer | fewer extras: outcrop 35%, bench 30% (or a stool 40%), pot 8%, water barrel 20%, sack 10%, cart 20%, helmet poles 30% / polearm 12%, the watch's stool 10%, quiver 15% | 0.945 | | 0 |
| r5-edge | the lab as the designs call it: `camp_site` reach to the clearing's edge (the designs give 12-16 squares, the lab gave 5), the band 4-6 people (the designs' median 5; the lab had stood 8-9) | 0.985 | queued for the independent judge | 0 |

Kinds fell from 13-16 to 8-13, pieces from 25-34 to 19-29, beds from 0.15 of the pieces to ~0.07, no second tent. The
classifier still separates them mostly on "against walls" (ours 0.05, Westwood's 0.50: its hideouts are caves) and the
family mix: an AUC near 0.6 needs a cave hideout variant, which the kit has no site for in the woods. The tuning agent
looked at every render, so r5-edge is queued in TO_JUDGE.md for an independent judge.
Greywatch: the changed camp shifted the planting, and a wild spider was shut in by pines, a log and a stump (the
checker blocks logs and stumps; `Story.wild`'s walk test did not): `Story.reachable_cells` now floods as the checker does
and `wild` turns away a shut-in spot (it changes nothing where no spot is shut in). Thornwick, Greywatch, Ambermere,
Starwell, Harrowby: 0 errors, warnings unchanged.

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

### graveyard, round 2 (night-scenes3, 2026-10-05)

Starting point: the independent judge on r3-spaced: 10/10, generated 4.2 against Westwood's 7.4 ("the same small box
every time, a square iron-fenced yard about 6 x 6 squares in a glade, 6-8 headstones on an even grid about 90 px apart;
Westwood's are large or long, joined to roads and crypts, with paved walks; tree trunks on the fence; a coffin on the
front fence corner with no dug grave; headstones strung along one fence, the middle empty"). Westwood re-read (corpus
War03b-d, Con07B, Con09b): crypt rows of Cobblestone cells with GreenBrick floors, a sarcophagus (Crypt1/Crypt3) and a
WoodAndSteelDoor each; GrassSparse2; dead trees and trunks; headstones 100-130 px apart.

| Round | What changed (mapgen/kit/yards.py) | AUC | Blind | Hard / missing |
|---|---|---|---|---|
| ref | the kit as merged | 0.865 | (independent, r3-spaced) 10/10, 4.2 / 7.4 | 0 / 0 |
| r1-crypts | crypt cells along the back (`_crypts`: one, or two in a long yard, 75% of yards; their back and end walls the fence's line); a walk beaten bare from the gate to the crypt door; graves 3.0-3.6 squares along, 2.9-3.3 between rows; the gate pillar one, 30% (both 20%: statue share 0.17 against Westwood's 0); the digger's corner the spade and bucket, the coffin 25%, the torch pole 30%; larger sizes first where they fit with 3 squares free round them (`grow`, 14 x 10 to 12 x 10) | 0.816 | | 1 / 2 |
| r2-larger | `grow` from 16 x 12 | 0.659 | | 0 / 1 |
| r3-walk | the walk always (to the crypt, or across to the back), square to the gate, two tiles wide; graves 1.1 squares off the fence (built_near 0.36 against 0.17) and 0.5 off the walk | 0.578 | | 1 / 2 |
| r4-small | a yard under 12 squares packs its graves closer (2.6-2.9 along, 2.4-2.7 between) and its walk one tile wide | 0.565 | | 0 / 0 |
| r5-trees | the yard's trees 1.2 squares off the fence (the judge: trunks on the fence line) | 0.565 | queued for the independent judge | 0 / 0 |

AUC under 0.6 from r3 (13 Westwood scenes: read it loosely). Thornwick, Greywatch, Ambermere, Starwell, Harrowby: 0
errors, warnings unchanged (the larger yards keep 3 squares free round them, so no corner is shut off). The tuning agent
looked at the renders: r5-trees is queued for an independent judge.

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

### garden, round 2 (night-scenes3, 2026-10-05)

Starting point: the independent judge on r3-larger: 10/10, generated 4.8 against Westwood's 7.8 ("crops under fences or
edges, a tomato row along the front plank fence, rows into the pine edge, corn touching the tree line; too small and
bare, one tomato and one cabbage row 150 px from the cabin, no barrel, spade or path; a bed squeezed between the cabin
corner and the forest, flowers on the crops; the field one crop in a Log-walled pen with an iron gate"). Westwood's
garden fences (corpus): Wiz03b DilapidatedShort (the low lattice), Wiz01A Dilapidated; Con05A's town garden three crops
side by side with apple crates and barrels.

| Round | What changed (mapgen/kit/village.py `garden`, kit/yards.py "field") | AUC | Blind | Hard / missing |
|---|---|---|---|---|
| ref | the kit as merged | 0.54 | (independent, r3-larger) 10/10, 4.8 / 7.8 | 0 / 1 |
| r1-near | two squares of open land round the beds required; the fence DilapidatedShort (Wiz03b's low one); the barrel 85% (beside a narrow bed too), the spade 50%; flowers beyond a bed's end, never on the rows; a crate, barrel or sack on the side 35%; the field's fence DilapidatedShort with a door that suits it (no Log, no iron gate) | 0.07 | | 0 / 2 |
| r2-wide | a second pass without the wide ring where none fits; the field two or three crops in bands of rows, its barrel and spade | 0.24 | | 0 / 0 |
| r3-open | `garden` tries each size wide then narrow, the two largest first (`_garden_at`); a narrow one keeps the planting two squares off | 0.10 | | 0 / 0 |
| r4-unpenned | no fence under 5 x 4 (a little bed's rows were lost to the fence: 8 crops in a pen) | 0.42 | | 0 / 0 |
| r5-household | the garden's own generator (map, house, size: tuning it never shifts the rest of a map); no flowers past the beds' ends (Ambermere: a townsman's walk stop faced them, routes.facing); the crate mid-way along a long side | 0.25 | queued for the independent judge | 0 / 0 |

AUC with 5 Westwood gardens is noise (0.07-0.54): judge by eye. Thornwick, Greywatch, Ambermere, Starwell, Harrowby: 0
errors, warnings as before (an interim build showed the shifted design generator dropping an ogre camp's straw into
Ambermere's chapel crypt, a warning: gone with the garden's own generator). The tuning agent looked at the renders: r5
is queued in TO_JUDGE.md.

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

### pond_dock, round 2 (night-scenes3, 2026-10-05)

Starting point: the independent judge on r3-bank: 9/9, generated 5.2 against Westwood's 7.8 ("the same gear stamp, 2-3
barrels touching at the root, a crate or rock opposite, 1-2 barrels at the tip, a crate in the dock's lane; short DockUp
docks in small round ponds, tips 1.5 tiles out; a lone pond, a dozen reed clumps spread evenly"). Westwood (Con05A):
DockDown runs into the lake, barrels in a loose knot on the bank, a rock with ferns, a crate on a dock's tip, bones.

| Round | What changed (mapgen/kit/water.py `dock`, `_dock_gear`) | AUC | Blind | Hard |
|---|---|---|---|---|
| ref | the kit as merged | 0.75 | (independent, r3-bank) 9/9, 5.2 / 7.8 | 0 |
| r1-loose | the bank laid loosely, never one stamp: 1-4 barrels in a knot with uneven steps (26-44 px), a rock with its stones 60%, a crate a little way off 40%, bones 30%, nothing on the dock's line carried back onto the bank; the dock's load from its own generator (none, a crate, one or two barrels); DockUp only 60 uv nearer the road (was 24) | 0.70 | | 0 |
| r2-down | a one-centre DockDown before any DockUp (a small pond's dock is still the DockDown run) | 0.32 | queued for the independent judge | 0 |

AUC with 4 Westwood docks is noise. Ten of ten docks are DockDown now (three were DockUp). Ambermere and DysVale: 0
errors, no dock warnings. Still: one dock to a pond (Westwood's lake has three), the reeds' even spread (the water
dressing, `_dress`, shared by every map: left alone), and no path or people in the lab's pond clearing.

## Final summary (every type, the kit as committed)

| Scene | Westwood scenes | AUC | Blind acc. | Blind gen/WW | Hard-rule scenes | Missing | Worst findings |
|---|---|---|---|---|---|---|---|
| bandit_camp | 20 | 0.98 | - | - | 0/10  | 0 | 7 creatures; 15 kinds of thing: more variety than Westwood shows |
| graveyard | 13 | 0.86 | - | - | 0/10  | 0 | only 0.55 of the steps along the screen diagonals: off Nox's grid; 0.25 of the pieces are statue (more than Westwood's) |
| garden | 5 | 0.24 | - | - | 0/10  | 0 | round, no main line (0.96); water 138 px from its middle |
| pond_dock | 4 | 0.75 | - | - | 0/10  | 0 | round, no main line (0.77); packed into 86 px |
| ogre_camp | 5 | 0.91 | - | - | 0/10  | 0 | 0.32 of the pieces are hay (more than Westwood's); only 0 of its ground open: crammed |
| well | 4 | 0.75 | - | - | 0/10  | 4 | 0.50 of the pieces are store (more than Westwood's); 0.25 of the pieces are seat (more than Westwood's) |
| market_stall | 3 | - | - | - | 0/10  | 10 |  |
| wagon | 7 | 1.00 | - | - | 0/10  | 1 | 0.40 of the pieces are hay (more than Westwood's); 11 kinds of thing: more variety than Westwood shows |
| urchin_camp | 42 | 1.00 | - | - | 0/10  | 0 | 0.30 of the pieces are rock (more than Westwood's); only 0 of the pieces near a wall |
| smithy_yard | 1 | - | - | - | 0/10  | 2 | 0.50 of the pieces are rock (more than Westwood's); 0 creatures |
| training_ground | 0 | - | - | - | 0/10  | 4 |  |
| woodpile | 3 | 0.99 | - | - | 0/10  | 1 | 0.60 of the pieces are log (more than Westwood's); 0 of the pieces are rock (fewer than Westwood's) |
| shrine | 28 | 1.00 | - | - | 0/10  | 0 | only 0 near a built wall or fence; only 0 of the pieces near a wall |
| farmyard | 6 | 1.00 | - | - | 0/10  | 2 | packed into 41 px; only 0 of the pieces near a wall |
| wolf_den | 4 | 0.97 | - | - | 0/10  | 0 | zones of 7 pieces: big heaps; zones only 0 px apart: they run together |
| quarry | 2 | 0.96 | - | - | 0/10  | 4 | pieces 44 px from their nearest: scattered; 1 of its pieces on a path or road |
| jail | 11 | 0.98 | - | - | 0/10  | 0 | 0.50 of the pieces are bed (more than Westwood's); 1 of its pieces on a path or road |

Types below the sore points have their baseline and this run only (no tuning rounds yet). "Missing": clearings where the recipe could not lay the scene: the market stall's store and inn are too big for the lab's clearings (0 of 10 laid); wells and catalogue themes need a town's context the lab gives only partly.
