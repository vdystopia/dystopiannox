# QA round 1: camps and yards (Q1K)

The user's round 1 feedback (2026-10-13, `review/reviews/QA-round1.md`, Exteriors) on the bandit camp, ogre camp, urchin
camp, wolf den, quarry, jail, training ground, smithy yard, market stall, wagon and woodpile, and the in-game screenshot
nox9. Columns as `review/FEEDBACK.md`: the rule that answers each piece of feedback (`P§n` is PROCESS.md section n),
how it is enforced (a checker rule with its planted case in `validate/selftest.py`, or the picture to look at), and its
status before and after this pass. The two overarching themes of the round run through every row: spaces too empty
with too few kinds of object, and things placed at random instead of lined up and balanced.

Before and after pictures: round 1's are `review/out/qa/round1/exteriors/<type>/EX-<TYPE>-NN.png` (sheets in
`review/out/qa/round1/sheets/`); this pass's are the scene lab's iteration `qa1k`
(`py tests/scenelab.py <scene> --n 10 --seed 11 --iter qa1k`), cropped as round 1's were, in
`review/out/scenelab/<scene>/qa1k/qa/` with a contact sheet `SHEET-EX-<TYPE>-qa1k.jpg` beside them.

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| Q1K-1 | wagon set: "Large crates overall are too close to other objects. This seems consistent across every feature"; EX-WAGON-01 "Wagon is too close to the crate", 03 "Move the sacks just a little bit further away from the crate", 06 "large Crate too close to apple crate", 07/09 "Crate too close to cart"; EX-BANDITCAMP-03 "The crates are on top of each other" | P§4 Spacing outdoors: a large crate keeps 48 px from any piece, 72 from a cart (`kit/spacing.py` LARGE_CRATE_GAP, used by every scene, camp, yard and door scene) | `exterior.crate_clear` (STcrate) | none | check |
| Q1K-2 | bandit camp: "Chests and the stool are too close to each other. Barrel and rock are too close to each other. Both beds are too close to each other. Overall layout isn't great" (01); "The crates and barrels are both too close to each other. The armor racks are too close to each other" (10); round theme: things placed randomly, not lined up | P§5 Camps: a camp's pieces keep 1.15 of Westwood's pairs and 26 px between any two solid pieces (`Camp.SPACE`, `SOLID_CLEAR`); bedrolls in pairs 62 px apart; rows against the wall (`camps._wall_row`), the sleeping row even and centred, seats balanced round the fire | `exterior.overlap`, `exterior.crate_clear`; balance: look at the qa1k sheets | review | check |
| Q1K-3 | bandit camp set: "Not enough objects and not enough diversity. Imagine a bandit camp is where multiple humans are hiding out and living for at least a short time. Cots, barrels, crates of apples, a fire with a bench or a couple seats, supplies, armor, weapons, structures like EX-BANDITCAMP-03. When a bandit camp exists in a grassy area, use dirt (similar to paths) for the camp area"; 02, 05, 06, 07, 08, 09 "Needs drastically more objects" | P§5 Camps, the bandit camp: arms row, two-row store, bedrolls with bundles, the awning, a board, a woodpile, the cook's corner; hideouts laid in the same zones; the dirt ground (`camps.camp_ground`) | `exterior.camp_bare` (STcampb: under 16 pieces of 8 kinds) | none | check |
| Q1K-4 | urchin camp: "Needs vastly more objects. More and more and more and more objects"; 02 "Way too many beds"; 03, 06 "Way too many beds. And they're all clustered right next to each other" | P§5 Camps, urchins: one bed to two urchins, BEDS_APART 90 px, each with its own things; the den filled round its rock (`Pocket.row_along`) and more knots in a big one | `exterior.beds_block` (STbedsb), `exterior.camp_bare` | none | check |
| Q1K-5 | ogre camp: "Ogre encampment should be very heavy on barrels (including explosives) and sacks. Add significantly more to all of them. Add more objects overall. use more of the tusk pillars, and pair them on either side of a path so they face each other and form a tunnel" | P§5 Camps, ogres: `camps.ogre_stores` (barrel yards with powder kegs, sacks, straw bedding, a pelt, a carcass, bones), `camps.ogre_tunnel` (facing tusk pairs down the way in, skull posts) | `exterior.camp_bare` (an ogre fire pit is always a camp); the tunnel: look at the qa1k sheet | none | check |
| Q1K-6 | EX-OGRECAMP-03, 04 "Unblended ground northeast of the fire"; 08, 09 "Unblended ground southwest of the fire" | P§5 Camps, ogres: `camps.ogre_ground` lays the trodden path and registers the ground under it for blending (the cave's DirtHard had taken no edges from the path's DirtLight2) | look: the qa1k sheet (the path's edges soft); `floors.unblended` covers seams Westwood blends | review | review |
| Q1K-7 | wolf den: "Add more objects and diversity. TREES, Bones, skulls, meat, corpses, rocks, boulders ... a small pond without a dock goes well in a wolf den and they should usually have lots of trees. Don't use too many of the same objects. Many of these instances have several of the exact same rocks sitting next to each other"; 05 "Just rocks are not enough" | P§5 Camps, wolf dens: `camps.wolf_den` (rock heap with no two neighbours alike, kills picked clean, bones, skulls, meat, a pelt, the forest's trees round it, a pond without a dock) | look: the qa1k sheet | none | review |
| Q1K-8 | quarry: "Add more object diversity. Mining carts, pickaxes, bones, mana crystals. Explosives, crates, barrels. They all look good in terms of layout and there isn't much differentiation or variety" | P§2 Yards, the quarry (`yards._quarry`: the works row, crystals and bones by the back corner) | look: the qa1k sheet | none | review |
| Q1K-9 | EX-QUARRY-03: "The southeast wall of the quarry runs clear across the path" | P§2 Yards: the gate's walk goes round the yard, never along or under its fence (`yards.connect_gate`) | look: the qa1k sheet (EX-QUARRY-03) | none | review |
| Q1K-10 | jail set: "At least 80% of cells should have either a cot, a bench. Needs many more objects and much more object diversity. Almost no cell should have 0 objects in it. Bones, barrels of tools, a piece of meat, a cot, etc Jails in towns should always have a large entry /guard room with a desk and some decor Entry/guard rooms need to be significantly bigger so they don't feel too crowded. Cells are a great location for holes that the player can fall through. (secret escape through a tunnel)"; 03, 08 "Guard room way too concentrated and cluttered" | P§2 Yards, the jail: a town's jail is a guardhouse, its guard room four squares deep across the whole front, furnished as a room with the warden's desk; every cell furnished, a cot or bench in four of five, a prisoner's leavings; the escape hole is a design's lift (no falling hole in the kit) | `exterior.jail_cells` (STjailc); the guard room: look at the qa1k sheet; the hole: not built (see below) | none | check |
| Q1K-11 | market stall: EX-MARKETSTALL-02, 09, 10 "I don't see any market stall in this screenshot"; 01, 03, 04, 05, 08 "more objects"; 06 "I'm not sure where the shopkeeper would stand"; 07 "Very good. Excellent object diversity and just the right number of objects. (a few more objects would still be ok, but no less than this)" | P§4 scenes: the trader's stool under the awning behind a counter of wares; optional wares more often; `market_stall_wall` backs the awning onto the shop's wall where the street is too tight | look: the qa1k sheet (9 of 10 stalls stand; the lab's plot 9 still has none: a small shore plot) | none | review |
| Q1K-12 | wagon: EX-WAGON-02 "The placement of the hay right next to the open side of the wagon is perfect. It really looks like it belongs together. Great job." | P§4 scenes: cart scenes in the screen's frame, the hay 50 px left of the cart, at its open side | look: the qa1k sheet | none | review |
| Q1K-13 | training ground: "These are all pretty poor. They need much improved balance and layout. when using rows (i.e. rows of barrels of weapon / armor racks), place them against a wall so they dont look so random. racks can also be in a row perpendicular to a wall"; EX-TRAININGGROUND-07 "much better if the objects were simply lined up closer to the exterior wall to the northeast of them" | P§4 scenes: `sparring_ring` and `archers_mark` are wall scenes against the barracks, racks along the wall, targets square to it; P§5 camp rows snug to the wall | `exterior.row_float` (STrowf) | none | check |
| Q1K-14 | smithy yard: "These are all pretty good. More object diversity and layout balance would improve them." | P§4 scenes: the smithy yard's layouts balanced on the anvil, more kinds (steel crates and barrels, racks of finished work, ore cart) | look: the qa1k sheet | none | review |
| Q1K-15 | woodpile: "These are all pretty good. They are small and subtle. They don't draw a lot of attention. They can be placed in areas that need to have their space filled." | P§4 scenes: the woodpile scales with the open ground as the fill pass's filler (cap 4 scaled, family cap 6, weight 3) | look:empty (the QA gate's empty-ground picture) | none | review |
| Q1K-16 | nox9.png: "The crates of apples and the larger crate look out of place here. Move them up against the wall so they're out of the street." | P§4 scenes: a door scene's props slid against the house's wall (`Village.scene`) | look: a town map's spots pictures | none | review |

Objects and kinds before and after (the scene lab's ten variants of each type, seed 11: round 1's iteration `qa1`
against `qa1k`; the scene's own pieces round its anchor, no trees, plants, creatures, shadows or lights; a town scene's
outdoor pieces only). Mean objects and mean distinct kinds per scene; in brackets the fewest objects / kinds in one
variant. No type lost objects or kinds (the woodpile was kept as it was: "all good"):

| Type | Objects before | after | Kinds before | after | Fewest (before -> after) |
|---|---|---|---|---|---|
| bandit camp | 20.9 | 31.4 | 10.1 | 15.9 | 9/7 -> 19/10 |
| ogre camp | 10.7 | 37.3 | 7.3 | 16.7 | 5/4 -> 27/14 |
| urchin camp | 15.4 | 41.6 | 6.9 | 19.4 | 10/4 -> 27/15 |
| wolf den | 18.9 | 36.3 | 7.2 | 16.8 | 18/6 -> 32/16 |
| quarry | 31.8 | 33.9 | 6.7 | 13.5 | 27/5 -> 29/11 |
| jail | 14.1 | 28.9 | 3.7 | 13.4 | 5/2 -> 5/2 (the cave cell) |
| training ground | 5.5 | 7.6 | 4.3 | 4.7 | 4/3 -> 5/3 |
| smithy yard | 7.3 | 10.1 | 6.1 | 7.8 | 3/3 -> 7/4 |
| market stall | 9.4 | 12.8 | 6.2 | 8.7 | 0/0 -> 2/2 (the lab's plot 9) |
| wagon | 6.7 | 7.5 | 5.6 | 6.7 | 3/3 -> 3/3 |
| woodpile | 7.5 | 7.5 | 5.4 | 5.4 | 4/3 -> 4/3 |

Designs rebuilt against this branch's base (b005f84), voices off (NOX_NOVOICE=1): TownLab 36 errors (base 41, all
`routes.leg`, none new) and 38 warnings (base 38); Greywatch 0 errors, 15 warnings (base 15; its castle jail now asks
for the cell row, `arch="cell_row"`, the guardhouse having taken its training ground's room); Harrowby 0 errors, 21
warnings (base 21: one `exterior.row_float` is new, its bandit camp's arms row in a glade with no wall within reach,
and one `rooms.stray` fewer).

Not done, and why:
- Harrowby's bandit camp stands in a wide glade with no wall within 210 px of its arms: the row still stands in the open
  and `exterior.row_float` says so; `camps.camp_site` could weigh a wall nearer the flanks.
- The secret escape hole in a cell (Q1K-10): Nox's `Pit` and `ForestPit` objects are DANGEROUS holes a player falls into
  (the engine, not a map, decides what a fall does), so the kit lays none in a cell. A design can make the escape with
  kit/transport.py: a lift whose pit stands in a cell and whose platform waits in a tunnel the design lays elsewhere
  (`Transporters.add("lift", tunnel_px, cell_px, ...)`); the scene lab's jails have no tunnel to lead to.
- One market (the lab's plot 9, a small plot on a shore) still finds no ground for either stall.
- The camps now go far past Westwood's measures (the scene lab's AUC is near 1 for the bandit camp: it tells them apart
  from Westwood's sparse camps at once); that is the user's word over Westwood's habit, stated as a house rule.
