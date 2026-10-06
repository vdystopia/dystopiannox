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

## The town setting (night-scenes3, 2026-10-06)

The independent judge on the round-2 sheets (scored against the keys): graveyard r5-trees 8/10, 5.6 / 7.0; garden
r5-household 10/10, 4.8 / 7.4; pond_dock r2-down 9/9, 4.6 / 7.8; bandit_camp r5-edge 10/10, 4.6 / 6.2. "The biggest tell
is the lab's setting: ours stand alone in an empty forest glade, Westwood's sit in towns, among other yards, walls,
paved walks, houses and crypt complexes."

The lab (labgen.py): every scene not of the wild (`WILD`: bandit, ogre and urchin camps, wolf den, quarry, shrine) is
now laid in a hamlet's ground: a larger clearing (12-15 squares), a road through it (the glade site becomes the road
site), two or three houses of the kit's own generator (home, cottage, store, fisher, inn) round it away from the scene,
furnished, each joined to the road by its walk (`plan_context`, `build_context`); a pond scene's water is a lake on one
side of it (10-12 tiles), the hamlet on the other, the dock's landing kept clear of the planting. The scores before and
after are not comparable (the setting changed), so each scene ran again in it.

| Scene | Round | What changed in the kit | AUC | Hard |
|---|---|---|---|---|
| graveyard | t1-town | the town setting, the kit as r5 | 0.625 | 0 |
| graveyard | r6-town | no tree in the yard (the judge: a green tree by the gate, a dead one among the graves); the crypt a square in from the back fence, about the back side's middle, never in a corner; the walk two tiles wide in every yard; the digger at work in 85% of yards; rows staggered | 0.81 | 0 |
| graveyard | r7-town | rows back on the grid's lines (the stagger broke the screen-diagonal steps Westwood keeps: 0.58 against 0.96), the gaps along a row uneven instead (2.7-3.9 squares) | 0.635 | 1 (graves) |
| graveyard | r8-own | the graveyard's own generator (a changed yard had shifted Harrowby's planting until a bush stood in a ruin's doorway, doorways.blocked); unused plots 14% | 0.644 | 0 |
| garden | r6-town | two sizes up first (w + 2, h + 1: "token plots"); the barrel and spade set down off the beds' exact ends | 0.79 | 0 |
| pond_dock | r3-lake | no reed within three tiles of a dock's lane ("reeds against the dock's sides"); the gear only on firm ground (a barrel had stood half in the water) | 0.48 | 0 |
| pond_dock | r4-shore | the bank fuller: 2-4 barrels, the rock 75%, bones 40% | 0.64 | 0 |

Thornwick, Greywatch, Ambermere, Starwell, Harrowby: 0 errors, warnings as at the start of the night; DysVale 0
errors. The tuning agent looked at the renders: graveyard r8-own, garden r6-town and pond_dock r4-shore are queued in
TO_JUDGE.md. The market stall still lays in none of ten clearings (the awning's poles and cloths find no free ground
by the store even with a kept square, r1-square): left for the next round.

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

## Round 4 (night-scenes4, 2026-10-06)

The independent judge on round 3's last sheets: graveyard r8-own 10/10 (5.6 / 7.4), garden r6-town 10/10 (5.4 / 7.8),
pond_dock r4-shore 9/9 (5.6 / 7.8): "each scene is generated as an isolated stamp; Westwood's are built into their
surroundings (walls, roads, houses, other scenes) and vary".

### bandit_camp: the hideout (mapgen/kit/camps.py `hideout_camp`, `rock_pocket`)

Westwood's camp evidence re-read: 10 of its 20 camps are pockets of CaveWall2 on DirtDark2 (Wiz03a, Wiz03b, Wiz03c,
War03a), every piece against the rock (wall torches 1-16 px from the wall's line, rocks 5-25, barrels 13-46, cots
20-48, the fire 50-146).

| Round | What changed | AUC | Hard |
|---|---|---|---|
| ref4 | the kit as merged (all ten in forest glades) | 0.959 | 0 |
| r1-hideout | the lab: five of ten camps in a rock pocket (CaveWall2 on DirtDark2, one mouth on a spur off a passage between the rows); the kit: `bandit_camp` becomes `hideout_camp` where its ground is a pocket of the rock or a ruin's walls: cots against the back rock with a wall torch, barrels and crates against a flank, big rocks and pillars where the rock juts, a fire in 70%, a table now and then, the chest by the beds | 0.973 | 2 (lone cots) |
| r2-pairs | cots two together along the rock (never alone: the checker's bedroll rule), the groups apart | 0.879 | 1 |
| r3-knots | two to four cots; barrels two against the rock and the rest before them; two or three rock places; the hideout's band smaller (no one at the fire) | 0.938 | 2 |
| r4-groups | a cot group laid whole or not at all, 58-66 px apart and never past 74; a table 20% | 0.944 | 0 |
| r5-small | smaller pockets (4-5.5 squares: Westwood's), the store's fallback flank | 0.967 | 0 |

The hideouts' wall share 0.5-1.0 (Westwood's 0.50; the open-air camps 0.03-0.16). The AUC stays ~0.93-0.97 on the
open-air half (a fire in every one, 11-14 kinds against 9). Queued: r5-small.

### graveyard: on its street (mapgen/kit/yards.py `_graveyard`, `gate_outside`; the lab `by_road`)

| Round | What changed | AUC | Hard |
|---|---|---|---|
| ref4 | the kit as merged | 0.678 | 0 |
| r1-woven | the yard by the hamlet's road (8.5 squares in, the gate toward it), a cobbled road in a third of the hamlets, the gate's walk to the road; graves in families of one to three, gaps between families; weeds by a quarter of the stones; a newer grave's dug earth two squares long; the digger at work: the open grave two squares, its heap, spade, bucket, coffin 60%, pick, torch, and the gravedigger standing there; crypts one to three cells of 2-4 squares | 0.792 | 0 |
| r2-walks | the gate's square fixed (the walk had started inside the fence) | 0.873 | 0 |
| r3-paved | the walk through the yard paved (RoughCobble, War03c): bare earth never showed in the pictures; big yards' graves closer | 0.789 | 0 |
| r4-clear | the graves 1.5 squares off the walk (a stone had stood on it) | 0.849 | 0 |
| r5-small | a small yard (under 12-13 squares) keeps one 3 x 3 crypt, its walk 1.1 squares clear, no heap and the coffin 25% (Harrowby's small yard had held two graves, exterior.graveyard; Starwell's 2 x 2 crypt cell had its sarcophagus in the doorway, doorways.blocked) | 0.782 | 0 |

The AUC rose from the ref's 0.68: the digger's corner (tool share 0.08 against Westwood's 0: the user asked for it,
SW-9), its pieces close together (closest gaps 52 px against 89). By eye the yards now stand on their streets with a
paved walk, crypts of several builds and a man at work. Queued: r5-small. Thornwick, Greywatch, Ambermere,
Starwell, Harrowby: 0 errors; Harrowby's and Starwell's warnings back to the night's start once the small yard was
lightened.

### pond_dock: a lived-in shore (mapgen/kit/water.py `_dock_gear`, `_shore_start`; the lab's lake)

| Round | What changed | AUC | Hard |
|---|---|---|---|
| (r4-shore) | the kit as merged, last round | 0.64 | 0 |
| r1-lakeside | the bank's composition one of four (store, the fishers' fire, a rock with ferns, almost bare); the lab: a bigger town lake (11-14 tiles), two or three docks on it (Con05A), a fisher at the first landing | 0.615 | 0 |
| r2-hut | the fisher's hut on the bank beside the first landing (Con03A); ferns along the bank | 0.44 | 0 |
| r3-bank | `_shore_start` prefers a landing with land five tiles behind it; no fern on a piece | 0.515 | 0 |
| r4-fisher | the fisher stands clear of the gear (he had stood on a fern) | 0.56 | 0 |

AUC at or under 0.6 from r2 (4 Westwood docks: noise). By eye: docks in twos and threes along a lake, ferns and a
rock on the bank, a fire or a barrel knot, the fisher at his landing. Ambermere and DysVale: 0 errors, no dock or
exterior warning. Queued: r4-fisher.

### garden: the household round it (mapgen/kit/village.py `_garden_at`, `_household`)

| Round | What changed | AUC | Hard |
|---|---|---|---|
| ref4 | the kit as merged | 0.76 | 0 |
| r1-household | centred on a side of the house first; the planting's density varies (0.52-0.62); the household: apple trees with a crate of apples (50%), a hedge of bushes (40%), a second water barrel (40%); the lab's gardener | 0.37 (0.236 re-rendered after the fairness merge) | 0 |
| r2-larger | the lab asks a size larger (4 x 3 to 6 x 5) | 0.13 | 0 |
| r3-far | the side goods on the long side away from the house (a sack had leant on the cabin's corner) | 0.062 | 0 |

AUC with 5 Westwood gardens is noise. Still: in a narrow clearing the garden is squeezed between the cabin and the
wood (the wide pass fails, the narrow one lays it). Thornwick, Greywatch, Ambermere, Starwell, Harrowby: 0
errors, no exterior warning (their room warnings come from master's room merges). Queued: r3-far.

### market_stall: it lays (mapgen/kit/scenes.py `market_stall`, kit/dressing.py `_lay`; the lab's market square)

| Round | What changed | AUC | Laid | Hard |
|---|---|---|---|---|
| (summary) | the kit as merged | - | 0 / 10 | 0 |
| r1-square | the wares no longer all musts (the apple crates must, the rest where they fit); the dressing's cut test counts the ground under an awning as blocked (it had read the open square between the awning's sides as a pocket the stall cut off); the hamlet's forest paths join it at its edges, never through its middle (a path's lane is kept clear: no room for an awning) | 0.925 | 4 / 10 | 0 |
| r2-wares | Westwood's wares (barrels in a row, a water barrel, an iron crate, a torch pole, a sack); the lab's store at the clearing's side, the market square 6.5 squares before its door | 0.875 | 4 / 10 | 0 |
| r3-door | the store's door toward the clearing (the building's u runs along the squares' i) | 0.992 | 8 / 10 | 0 |
| r4-fuller | two to four barrels, the cart at the side (35%), an armour rack (15%) | 0.983 | 8 / 10 | 0 |
| r5-under | the stock as Con09d's: the apple crates under the awning's front (the dressing kept every piece 60 px off the cloths: now 30 off a side, 10 off a top), the barrels in a row behind under the back cloth, torch poles at the ends | 0.692 | 8 / 10 | 0 |

3 Westwood stalls: read the AUC loosely. Queued: r5-under.

### well: Westwood's lone well (kit/scenes.py `well_side`)

Westwood's four campaign wells (Con02a, Con07B, Con09a, War07A) are the WishingWell alone, at most a sign a little
apart; none has barrels, a bench or sacks. The kit's well_side had laid a water barrel, barrels, a bench and sacks round
its Well. The landmark stays `Well` (the user has not chosen; rules/scenes/well.md says what Westwood uses).

| Round | What changed | AUC | Hard / missing |
|---|---|---|---|
| (summary) | the kit as merged | 0.75 | 0 / 4 |
| r1-alone | the well alone, 60 px kept clear round it | 0.761 | 0 / 1 |

The classifier separates on zones (ours one piece: Westwood's four have their sign or a trader's pitch beside). By eye
a lone well is Westwood's. No further round (4 Westwood wells).

### urchin_camp: the den (mapgen/kit/camps.py `urchin_den`, the shared `Pocket`)

Westwood's 42 urchin scenes are all dens in the earth (Dirt walls on DirtDark2: Con02a, War03c, War03d, Wiz01A). The
hideout's rock-pocket reading became a class (`Pocket`: rays, the mouth, points off the rock, rows along it), used by
`hideout_camp` and `urchin_den`; `urchin_camp` turns into a den in a pocket (`rock_pocket`, which knows Dirt walls).

| Round | What changed | AUC | Hard / missing |
|---|---|---|---|
| (summary) | the kit as merged (open-air camps round a fire) | 1.00 | 0 / 0 |
| r1-den | the den: beds of one kind in twos and threes against the back rock, their variant by the wall's side; shelves, paintings and scrolls on the upper walls; wall torches; the chest; barrels; a table ringed by stools; the lab: eight of ten in a Dirt pocket | 0.955 | 0 / 0 |
| r2-walls | shelves in runs of two or three, more paintings, more beds, fewer stools, a table in 65%; the lab's dens 1.3 times larger | 0.914 | 0 / 1 |
| r3-close | shelves 26 px apart, beds 42-48 | 0.75 | 0 / 0 |
| r4-wide | dens 1.5 times larger, barrels 70%: worse (0.845), reverted to r3 | 0.845 | 0 / 0 |

Queued: r3-close. Note: the lab is not reproducible run to run (the same code and seed gave bandit camps of 24 and
19 pieces in two runs; graveyard r2 and r3 0 and 1 missing): read single-round AUC moves of under ~0.1 as noise.
Thornwick, Greywatch, Ambermere, Starwell, Harrowby: 0 errors, warnings unchanged.

### shrine: statues in rows against a wall (kit/scenes.py `shrine`, `waystone`)

| Round | What changed | AUC | Hard / missing |
|---|---|---|---|
| (summary) | the kit as merged (a statue with torch poles and flowers in a glade; a milestone with flowers and stones) | 1.00 | 0 / 0 |
| r1-rows | Westwood's compositions: statues of one kind three in a row 49 px apart, a pair flanking, a lone one between pillars; the waystone a row of milestones with its altar; no flowers | 0.991 | 0 / 0 |
| r2-wall | the shrine a wall scene (Westwood's: 0.94 of their pieces within two cells of a built wall); the lab lays shrines in the hamlet's ground among houses | 0.901 | 0 / 1 |
| r3-lights | a second torch pole and the pillars more often (Westwood's median 5.5 pieces, ours 3) | 0.836 | 0 / 0 |

Queued: r3-lights. Thornwick, Greywatch, Ambermere, Starwell, Harrowby: 0 errors. (Thornwick's warnings now and then
include "a study room holds OgreStraw4": a catalogue hay scene in a ruined room; it comes and goes between runs of the
same code, as the lab's maps do, so it is not this change's.)

### ogre_camp: the fire in the swamp (kit/camps.py `ogre_camp`)

| Round | What changed | AUC | Hard / missing |
|---|---|---|---|
| ref4 | the kit as merged (a forest glade) | 1.0 | 0 / 0 |
| r1-swamp | the lab: every ogre camp in a pocket of RootLight on dirt; the kit: bones close round the pit, straw rare, the stock two to four, the big carcass 50%, the tusk gate 40% | 1.0 | 0 / 0 |
| r2-hut | the warlord's bearskin by the fire 30% (Westwood's lie in the huts) | 1.0 | 0 / 0 |

Five Westwood scenes: the AUC cannot move far (its top features: the fire by a path, open ground). Queued: r2-hut.

### jail: straw and torches (kit/yards.py jail cells; the lab's paved court)

Westwood's eleven jail scenes (Con02a, Con07B, War03b, War03c, War07A): cells on RoughCobble behind Cobblestone, a cot in
one cell, straw strewn thick (seven to twelve tufts to a jail), a wall torch to a cell; Con02a's and War03b's guardroom
racks and table before the cells (not attempted: Greywatch places its prisoners by the cells' geometry).

| Round | What changed | AUC | Hard / missing |
|---|---|---|---|
| ref4 | the kit as merged (a cot and one or two straw in every cell) | 0.974 | 0 / 1 |
| r1-straw | the cells' bedding from the jail's own generator (the design's draws replayed): a cot in one cell (80%), three to six tufts of straw a cell, 0.6 squares apart | 0.977 | 0 / 1 |
| r2-court | the lab paves a court round the jail in two clearings of three (Westwood's jails stand in paved courts) | 0.927 | 0 / 0 |
| r3-torch | a wall torch on a cell's back wall (60%) | 0.905 | 0 / 0 |

Thornwick, Greywatch, Ambermere, Starwell, Harrowby: 0 errors.

## Round 5 (night-scenes4, 2026-10-06): the independent judge on the round-4 sheets

The judge's critiques (scores in the main session's log). Common thread: "singles at even spacing, one template per
scene, too sparse; Westwood's scenes are clustered knots of mixed pieces leaning on terrain". What each scene changed:

| Scene | Round | The judge said | What changed | AUC (round 4 -> 5) |
|---|---|---|---|---|
| market_stall | r6-trades | near-empty (4-5 pieces against 11-16); barrels in an even line; nothing says what is sold; red/blue and yellow/green awnings Westwood never uses | three trades (a provisioner: apple crates, a knot of barrels, sacks, the cart; an armourer: three armour racks and helm poles; a potion seller: cauldron, stool, ore cart); the awning always Westwood's UP kind (purple and orange, green and red); 9-13 pieces | 0.692 -> 0.962 (3 stalls; 7 of 10 laid) |
| urchin_camp | r5-knots | far too sparse; the table's stools spread wide; beds at even intervals; no barrel corners, no shelf runs | two or three shelf runs, three to five pictures, barrels in a corner knot (75%), stools packed 29 px round the table (three to five), straw more often | 0.75 -> 0.651 |
| bandit_camp | r6-knots, r7-hollows, r8-upper | the same hollow and straight corridor; cots at even steps; the fire stones a wide even hexagon; stores in one strip; a bench right beside the fire | a tight, uneven fire ring (17-23 px, angles jittered); the hideout's crates set before the barrels' end (a knot); cot steps 54-70 px; the bench 70 px out; the lab's pockets stretched and turned, their passages winding; cots on an upper wall where they can (a cot under the near rock is hidden) | 0.967 -> 0.862 |
| ogre_camp | r3-varied, r4-fewbones | one fire layout stamped every time; a torch pole by the fire or alone; the bearskin behind a bench; a chest Westwood never has | the meat one of four sets, one to three seats from six places, bones (none in two of five camps) mostly to one side; the bearskin gone, the chest 25%; without the gate the torch pole stands by the store at the camp's edge | 1.0 -> 0.992 (5 Westwood fires) |
| garden | r4-knot | equal ruler-straight bands; crops under the fence; barrels, crates, a sack and a spade each alone round the beds | bed lengths uneven (each end 0-0.7 squares in); crops 12 px off a fence; no spade (Westwood's gardens keep no tools); the household's goods in one knot by the water barrel, each at Westwood's gap | 0.062 -> 0.448 (5 gardens) |
| graveyard | r6-loose | a cobbled path down the middle to a crypt every time; stones on the fence line; pillars inside; flower patches | the walk in 60% of yards with a crypt, 30% without; stones 1.4 squares off the fence (1.1 in a small yard); the gate pillars a pair outside the gate (35%); no flowers | 0.811 -> 0.814 |
| pond_dock | r5-knots | the same lone crate squared on the last plank; two piers squeezed together; goods split into singles; a barrel on the cobbled road | no crate on a dock's tip; docks 18 tiles apart (was 12); the bank's gear never on a road | 0.47 -> 0.443 |
| shrine | r4-chapel | set against wooden cabins or floating in a glade; statues cramped or strewn | the lab sets the shrine by the village chapel (its stone_house style) | 0.836 -> 0.788 |
| well | r2-road | no road or square: not a public landmark; placed by geometry | the lab sets the well 3.5 squares in from the hamlet's road | 0.761 -> 0.761 |

Thornwick, Greywatch, Ambermere, Starwell, Harrowby, DysVale: 0 errors after round 5 (warnings: room rules only). The
round-5 sheets are queued in TO_JUDGE.md.

Shrine r5-masonry: the kit's `shrine` now stands only against masonry, a castle's walls or a stone house (`Theme.house_roles`:
chapels, the shrine and mausoleum buildings, keeps, manors, the town hall, barracks, towers, gatehouses, gaols,
observatories), never a cabin; the lab builds a small stone shrine or mausoleum for it (the village chapel did not fit).
AUC 0.91 (2 of 10 missing). Thornwick, Greywatch, Ambermere, Starwell, Harrowby: 0 errors.

Graveyard r7-walls (reverted): the back side a Cobblestone wall in 40% of yards and a broken length of fence
(IronFenceDamaged) in 30%, as Westwood's War03b-d, War03c and Con07B yards have them: two of ten yards came out with
three to five graves and two were not found at all (AUC 0.815, one hard rule), so the change was taken back; the
yards' fences stay plain IronFence. Worth another try with the graves' count checked.

Garden r5-against: the garden centred on a side of its house a square from the wall (it had stood two off: "floating in
open grass between cabins with nothing behind them"; Con07B's beds lie along their house). AUC 0.434. Thornwick,
Greywatch, Ambermere, Starwell, Harrowby: 0 errors.

Bandit camp r9-warcamp: two kinds of open camp, as Westwood's: a war camp (60%: the pup tent and the awning, the armour
racks 90%, no bedrolls: its men sleep in the tent and under the awning; Con03A, Con04a, Con05A, Con09d) or a rough camp
(bedrolls in pairs, racks 20%). AUC 0.873 (1 of 10 not found). Thornwick, Greywatch, Ambermere, Starwell, Harrowby: 0
errors.

Pond and dock r6-lake: the lab's town lake larger (13-16 tiles: "every pier into a small closed pond"). AUC 0.295. The
lab only.

### farmyard: Westwood's straw heaps (kit/scenes.py `hay_store`)

Westwood's six farmyards (Con08d, War03c, Wiz03a, Wiz03b) are heaps of straw (OgreStraw1 most) along a wall, a barrel or
two, a torch, a rock. The kit's hay_store had laid one or two heaps with sacks.

| Round | What changed | AUC | Hard / missing |
|---|---|---|---|
| ref4 | the kit as merged | 1.0 | 0 / 3 |
| r1-heaps | three to five heaps along the wall, a barrel or two, sacks 35%, a torch pole 35%, a rock 25% | 0.92 | 0 / 1 |
| r2-spread | heaps 54 px apart | 0.942 | 0 / 2 |
| r3-shorter | two to four heaps 48 px apart (r2's run reached round a house's corner into Harrowby's storeroom: rooms.stray) | 0.967 | 0 / 3 |

The lab alternates hay_store with the kit's threshing floor and windmill, which Westwood has no counterpart for.
Thornwick, Greywatch, Ambermere, Starwell, Harrowby: 0 errors, warnings as before. Not queued (one round of small moves).
