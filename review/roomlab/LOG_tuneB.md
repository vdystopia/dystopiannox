# Room lab log: tuning track B (tavern, throne room, great hall, chapel, dining hall, hall, shrine, gallery, conservatory)

Branch `night-tuneB`. Seed 1, 10 variants a round. Blind numbers marked **self** were judged by the tuner, who had seen
the Westwood rooms while fixing the index (so its Westwood guesses are recognitions, not judgements); independent
judging is queued in `review/roomlab/TO_JUDGE.md`.

## The Westwood index (rules/rooms/westwood.py)

- `classify`: a "shop" with 3+ bar pieces, no trader's desk, under 2 racks, no lab and 4+ seats is a **tavern** (the barman
  is a Shopkeeper object: Con02a's tavern, shared by Con08a/War03b/War08a/Wiz08a).
- `classify`: a "hall" whose plants (3+) outnumber its statues and columns is a **conservatory** (Galava's walled garden
  and rock garden, Con07B/War07A: they had stood as halls).
- `HAND`: Con07B (112,240) **tavern** (Galava's lower tavern: the bar in the W corner, long tables and tables of food
  round a woven carpet; void-bounded, the finder missed it); Con03B (200,80) **dining hall** (the miners' mess: hearth
  with its pot, three long tables with benches on a carpet, casks; the stove made it a kitchen).
- `RETYPE` (new: rooms the finder closes but the classifier misreads): Wiz05A (48,24) **tavern** (the Conjurers' tap
  room: round tables, stools and fallen chairs on a carpet before the bar, whose nook the finder splits off).
- Each room once, really: a room met again in another campaign whose floor differs by a few tiles (doors open or shut)
  was counted twice (War01A's shop and store, War03a's armoury, War06b's smithy and bedroom, War07A's crypt, shop and
  gardens, War07D's laboratory): same type, centre within 3 cells (7 for rooms of 40+ tiles), tiles within 15%,
  another map. 235 -> 227 rooms. Note for the other tracks: smithy 2 -> 1, bedroom 40 -> 39, laboratory 19 -> 18,
  storeroom 22 -> 21, armoury 16 -> 15, crypt 30 -> 29, shop 16 -> 13, hall 17 -> 13.
- Every campaign tavern and dining hall searched by hand (every room, walled and void-bounded, holding a bar, two tables
  and four seats, a throne or an altar): **taverns 5** (Con02a, Con06a, Con07B, Con07B lower, Wiz05A), **dining halls 3**
  (Con05C ogres, Con06a, Con03B). Rejected: Con05A's bar of potions (a shop), the Wiz02B/Wiz07D library counters,
  Con03B's mine office, Con06b's lord's hall (a solar), Wiz05A's 15-tile bar nook (left a shop).
- Rebuilt `rules/rooms/westwood.json` and `review/roomlab/westwood_features.json`. Not rebuilt: `rules/out/objects.json`
  (its per-type counts still see Con02a as a shop) and `validate/baseline.json` (the checker's tavern sizes 166-216 and
  coverage median 0.124 still stand on its own older classification).

## Shared changes (kit/furnish.py)

- `repeat_cap`: a profile's caps (a piece per so many floor tiles) counted the building's footprint tiles, the tiles
  under the walls with them (168 for a room the score measures at 143): a tavern of 143 tiles took 6 tables against a
  cap of 5 in every room. Now 0.9 x half the usable cells (the half-tile grid), which matches the room score. Affects
  every type with caps (they hold slightly fewer of the capped piece). Checked on bedroom, kitchen, barracks, crypt
  (pre/post, seed 1): AUC 0.988/0.911, 1.0/1.0, 0.999/0.997, 0.981/0.954; hard-rule rooms 6/7, 4/4, 1/0, 1/0 (the
  bedroom's extra one is a way-in at exactly 4.0 in a room the new index sized smaller).
- New opt-in recipe keys (no-ops for every other kind): `one_set` (one table type and one seat kind for each named
  group in a room), `group_rugs` (False: no rugs under the groups' tables), `seat_gaps` and `group_seats` (a recipe's
  own seat spacing and count per group), `by_walls` (those groups take the open spots nearest the walls:
  `Furnisher.wall_spots`); SUPPLIES `kegs` (barrels without the great casks).
- `build_bar` (taverns only): 9-14 pieces in a common room, shorter only where it must; any back corner (N, E, W) at
  random, never the front; the walls inside the bar kept clear (the hearth had gone up behind the counter); stools of
  one kind along its outer face (5 at most); a spittoon at its foot; a pair of great casks against the wall just past
  its end (`bar_casks`); the kegs behind it barrels only. The bar's kegs and stools count toward the plan.

## Tavern

| round | change | AUC (pool) | cross AUC | hard-rule rooms | blind |
|---|---|---|---|---|---|
| ref | (index fixed; pool still shops) | 0.99 | 0.992 | 10 (caps 10, reads as 7) | - |
| r1 | pool tavern+dining hall; recipe: kegs 2-6, no plants, bearskin only, one set kind each, carpet under the tables 45%; bar 9-11, stools | 0.986 | 0.99 | 10 | - |
| r2 | bar stools fixed (series match), repeat_cap on usable cells, round tables 2+1 | 0.986 | 0.994 | 8 | - |
| r3 | bar fallback sizes, walls behind the bar kept, casks by the bar, no kegs group, profile tiles 160+ | 0.969 | 0.993 | 8 | - |
| r4 | seats pulled out (seat_gaps), caps at 0.9 | 0.989 | 0.994 | 6 | - |
| r5 | one stool kind at bar and round tables (Westwood's dominant seat), free_most (12, 14), kin living room (Con02a reads 13.7 tavern / 8.4 living room), no shelves | 0.935 | 0.989 | 9 (checker: size, sparse) | - |
| r6 | long tables and food tables by the walls | 0.90 | 0.983 | 9 (checker) | - |
| r7 | profile tiles 180+ (the checker's 166-216), kegs kind | 0.941 | 0.976 | 9 | - |
| r8 | bar kegs and stools counted; round seats 2-3; bar stools 5 | 0.882 | 0.983 | 7 | - |
| r9 | third round table only past 220 tiles, benches 4 | 0.929 | 0.99 | 2 (sparse 0.12 against the checker's 0.124) | self: 100%, generated 5.2, Westwood 7.6 |
| r10 | bar in any back corner | 0.946 | 0.987 | 4 (sparse) | queued |

Self-judged r9: the generated taverns are big floors with small sets dotted at even gaps; Westwood's bars are longer
(U or L ringed by stools) and its sets cluster on a carpet; the room is denser. What still gives them away (metrics):
lights per tile (0.028 against 0.049: Westwood lights its taverns with torch poles and colour lights, which the user's
rule TP1-5 forbids indoors), the middle a little fuller than Westwood's, pieces nearer each other. Shell: every lab
tavern is a plain rectangle; Westwood's have a dais (Con02a), an L (Con07B), a stair (Con07B).

## Throne room

Westwood: Hecubah's (Con06b, Dun Mir), the Lich Lord's (Con10d), the finale's (Con11a), Wiz11A's niche: three of four
are the Land of the Dead's. The lab builds only the kit's Dun Mir throne in town styles (there is no Land of the Dead
throne-room kind), so its pool is halls and throne rooms. Shell giveaways (not mine to change): every lab throne room
is a plain rectangle on one floor; Westwood's are shaped (a cross, an apse) with a dais and an inlaid runner of another
floor; the lab's door can sit at the end of the SE wall, so the throne in line with it stands off-centre.

| round | change | AUC (pool) | cross AUC | hard-rule rooms | blind |
|---|---|---|---|---|---|
| ref | - | 0.999 | 0.991 | 6 (statues 2/4) | - |
| r1 | recipe: no plants or benches, a chest at most, 4 hangings; braziers in pairs down the aisle (`aisle_lights`); statues in the back corners | 0.983 | 0.986 | 10 (statues) | - |
| r2 | **shared:** the knowledge base's "a showpiece twice only 10 units apart" no longer applies to statues (they keep their 2-unit clearance, pairs closer): no throne could be flanked nor an aisle lined | 0.999 | 0.993 | 0 | - |
| r3 | statues on a back wall turned along it toward the throne (`statues_along`: Westwood stands Statue2c/2g on NW walls, 19 of 20); `decor_max` caps all hangings | 0.965 | 0.996 | 0 | - |
| r4 | columns a pair per 36 tiles, 3 pairs at most | 0.965 | 0.991 | 2 (bunched) | - |
| r5 | a pair per 30 tiles | 0.965 | 0.992 | 1 (bunched, 121 tiles) | queued |

What still gives it away (metrics): the dominant kind's share (Westwood's halls are mostly columns; ours mix columns,
statues, braziers, hangings), a lone throne where Westwood's has its base, back and shadow plus a dais, the plain shell.

## Great hall

Westwood: Con06b's Dun Mir hall (twelve Table1/2 joined into long boards in a U round a free hearth, sixteen benches,
three free hearths, eleven shields and war poles) and Con07E's feast hall (twenty tables of food and square tables with
chairs). Pool: great halls and halls (whose bare middles make every table "too much in the middle": read loosely).

| round | change | AUC (pool) | cross AUC | hard-rule rooms | blind |
|---|---|---|---|---|---|
| ref | - | 0.954 | 0.988 | 2 (a shell door warning) | - |
| r1 | recipe: no plants or statues, one free hearth (alone) besides the wall hearth, benches only in the front corners; boards of 3 joined tables (`table_rows(joined=)`); a table piece per 24 tiles | 0.921 | 0.991 | 4 | - |
| r2 | (no change: the boards were not joining) | 0.921 | 0.991 | 4 | - |
| r3 | base statistics a dining hall's (a hall's density trimmed the boards to four tables); joined pieces 0.04 apart (`fits` keeps 0.02 when touching); a board laid whole before its benches | 0.915 | 0.992 | 10 (benches 60% of pieces) | - |
| r4 | benches at every other piece of a board (Con06b: 16 benches down 12 tables) | 0.886 | 0.991 | 1 (shell door) | queued |

Shared: `table_rows` takes `joined` (0, the default, is the old behaviour); a board's tables are laid before they are
seated. Still giving it away: the boards stand as islands mid-carpet (Westwood's U wraps a free hearth), the plain
shell, few lights.

## Chapel

Westwood: one campaign chapel, Galava's temple (Con07B, 123 tiles: eight pews in the arms of a cross-shaped carpet,
six columns ringing the nave near its walls, white and blue tapestries, candelabras, statues by the altar, a lectern).
Pool: the ceremonial family.

| round | change | AUC (pool) | cross AUC | hard-rule rooms | blind |
|---|---|---|---|---|---|
| ref | - | 0.97 | 0.981 | 1 (pews 3/4 in an 81-tile nave) | - |
| r1 | pews a pair per 15 tiles, 8 at most (Westwood's 8; the user's "way too many benches"); columns ringing the nave near the walls (`columns_by_walls`); statues turned along the altar wall; 6 hangings at most; no plants | 0.956 | 0.974 | 1 | - |
| r2 | sarcophagi only when the plan draws them (25%; they had stood behind the pews in every nave), one wall tomb at most in a big nave | 0.956 | 0.971 | 1 | - |
| r3 | the columns fall back to beside the pews when the walls leave no room | 0.957 | 0.967 | 1 | queued |

Still giving it away: the runner is a plain strip where Westwood's carpet is a cross (the shell's floor); a wide nave
entered from its long side gets a one-sided set of pews (the shell's door); one tapestry colour where Westwood
alternates two.

## Merges from master

- Curated Westwood references (`rules/rooms/curated.json`, applied after my dedup; my classify fixes and hand rooms
  kept): 179 rooms, 48 excluded. Taverns 6 (Wiz05A's bar nook joins), dining halls 3, great halls 2, halls 3, chapel 1,
  shrines 5, gallery 1, conservatory 0 (both gardens excluded: a cave pocket and a garden open to the sky).
- The lab renderer's sunlit rim fixed (the cached Westwood galleries cleared and rebuilt).

Independent judge (main session), first sheets: tavern ref 10/10 right (generated 5.0, Westwood 7.0); throne room ref
10/10 (4.8 / 7.2), r5 10/10 (5.2 / 7.2); great hall r4 10/10 (4.8 / 6.0). Their critiques taken up below: the great
hall's free hearth "dumped at the carpet's S corner before the door" and "twelve identical banners" (now toward a wall,
six hangings at most); every recipe's `decor_max` now also caps the lining loop's hangings (furnish.py: it had hung
banners until the back walls read lined).

## Dining hall (and mess hall, ogre hall)

Westwood: Con06a (55 tiles: two Table1s with benches and chairs before the hearth, a bookcase, a chest), Con03B's
miners' mess (108: three long tables with benches on a carpet, the cooking hearth, casks), the ogres' Con05C (110: two
crude tables ringed by stools, barrels heaped, skull posts, no straw). Pool now dining halls, taverns, great halls.

| round | change | AUC (pool) | cross AUC | hard-rule rooms | blind |
|---|---|---|---|---|---|
| ref | (pool still shops) | 1.0 | 0.983 | 2 | - |
| ref2 | r1's recipe on the curated pool: two or three tables (a piece per 32 tiles, cap a table per 30) with benches, casks, a bookcase at most, no plants or statues; mess halls a table per 22; the ogres' hall without straw, a third of the meat, tables a piece per 45 | 0.905 | 0.981 | 6 | - |
| r2 | no bench top-up down the walls; ogre tables a piece per 50 | 0.925 | 0.986 | 10 (checker: sparse) | - |
| r4 | a feast and dining set may join; shelves and ogre barrels fixed in number | 0.905 | 0.986 | 10 | - |
| r6 | crockery shelves only (bookcases had made it read as a library), two of them | 0.916 | 0.985 | 10 | - |
| r8 | the boards' ends seated; stores two clusters at most; hangings capped in the lining loop | 0.882 | 0.987 | 10 (sparse) | queued |

The checker's "sparse" (coverage under its median 0.15 for dining halls, measured on its own older classification
with Con07E's feast hall among them) now fires on every room at 0.08-0.13; the lab's Westwood dining halls cover
0.06-0.15 (median 0.10). Left as it is: chasing it brought back the grid of eight tables. Still giving it away: seats
0.2 units from their tables (Westwood's median gap to the nearest piece 0.58), rows aligned, few lights.

## Hall

Westwood (curated): Con04c's colonnade (128 tiles: 22 columns, 24 statues, fire grates), Con06b's bare hall (two
statues, shields), Con10c's ring of four columns round its obelisks (209). Pool: the ceremonial family.

| round | change | AUC (pool) | cross AUC | hard-rule rooms | blind |
|---|---|---|---|---|---|
| ref | - | 0.951 | 0.968 | 3 (5 statues against 4) | - |
| r1 | no plants, tables or benches down the walls (a bench at most), a chest at most, four hangings, statues turned along their walls, no top-up | 0.831 | 0.976 | 9 (checker: sparse at 1-2%) | - |
| r2 | statue pairs twice and statues in two corners | 0.851 | 0.974 | 10 (repeat: statues) | - |
| r3 | statues capped by the profile (a piece per 18 tiles, 8) instead of free_most; columns a piece per 14 tiles, 12 at most | 0.784 | 0.976 | 6 (sparse 2-3%, under the checker's 0.027) | queued |

Still giving it away: two statue pairs meet in the middle of the aisle; plain shell (Westwood's halls are rings,
inlaid floors and fire grates).

## Shrine

Westwood (curated, 5): Con07D (42 tiles: four obelisks in a diamond round a key on a ring of carpet, candelabras in
the corners, a chest), Wiz02B (25: four obelisks, a spell book, bones), Wiz11A's three Land of the Dead niches (13-36:
two or four mana obelisks round a spell book). None holds an altar.

| round | change | AUC (pool) | cross AUC | hard-rule rooms | blind |
|---|---|---|---|---|---|
| ref | - | 0.999 | 0.933 | 7 (dark shrines in town houses empty: their LOTD pieces excluded by the style) | - |
| r1 | obelisks for statues, no plants, a chest; the dark shrine lifts LOTD and Lich in any building | 0.997 | 0.956 | 4 | - |
| r2-r6 | `relic_ring`: the holy thing (the altar, else a basin of fire, else bare floor) in the open middle ringed by four obelisks at the screen's axes with a carpet under the ring; failed every time: the profile capped statues at 2 (a piece per 16 tiles), and the way-in rule keeps columns and statues off the doors' lines (the ring tries every open spot) | 0.989-1.0 | 0.92-0.98 | 3 | - |
| r7 | statues a piece per 6 tiles (Westwood: four obelisks in 25-42 tiles): the ring stands | 0.989 | 0.923 | 3 | - |
| r8 | no extra corner obelisks | 0.965 | 0.922 | 4 | - |
| r9 | the dark shrine is a shrine by its obelisks (Wiz11A's niches hold no god's statue): no focal or altar required | 0.967 | 0.922 | 1 (bunched) | queued |

Profile focal "any" (the altar in the ring where the room has the floor, else on the wall across from the door).

## Gallery

Westwood (curated, 1): Con07E's gallery (210 tiles, retyped from laboratory): bays along a blue-carpeted walk, each with
its exhibit (an orrery, a flame basin on a plinth, crystals among plants, a fountain), seven paintings and five blue
tapestries between them, sixteen lanterns. Its bays are the shell's; the furniture can give the exhibits.

| round | change | AUC (pool) | cross AUC | hard-rule rooms | blind |
|---|---|---|---|---|---|
| ref | - | 0.983 | 0.995 | 5 | - |
| r1 | exhibits apart instead of a bench group in the middle: the orrery and a statue pair toward the walls (`by_walls`), flame basins, plants; one bench at most; tapestries with the paintings | 0.934 | 0.99 | 6 (reads as nothing: tapestries took the paintings' places) | - |
| r2 | paintings only, the gallery decorated like the other ceremonial rooms (up to 10 hangings) | 0.923 | 0.989 | 0 | - |
| r3 | the basins and orrery named (their families are none), plants in any corner, statues on the walls' middles | 0.917 | 0.988 | 1 | queued |

Still giving it away: coverage 0.009 against 0.05 (the room is bare; Westwood's bays make it), four paintings at most
(the knowledge base's two of a kind to a wall), small pieces lost on a big floor. The weakest of my types.

## Conservatory

No Westwood reference left: the curated index excludes both of Galava's gardens (a cave pocket; a garden open to the
sky), so the lab compares it with the ceremonial pool (AUC 0.999 by its plants alone; meaningless). ref: the fountain
or well in the middle, benches, a statue pair, plants in the corners and in clumps: 0 hard-rule rooms bar one bunched.
r1 tried beds of 4-6 plants instead of clumps (per 100 tiles 5): the clearances thinned them to a sparser, emptier
garden (AUC 0.995); reverted. Not queued for judging (nothing to tell it from). Still giving it away by eye: clumps
dotted evenly, benches not turned to the fountain.

## Second pass

Independent judge (main session), every sheet 10/10 picked: dining hall r8 (generated 4.0 / Westwood 6.4), hall r3
(4.4 / 6.0), shrine r9 (4.6 / 6.8), gallery r3 (3.6 / 6.0). Their summary: "one set stamped at equal spacing, a lone
group dead centre, and large bare stretches of floor. Westwood's rooms tend to have one strong idea placed with small
irregularities."

### Tavern against its own six rooms (the curated pool)

| round | change | AUC | cross AUC | hard-rule rooms |
|---|---|---|---|---|
| r11 | r10's kit on the curated pool (6 taverns: no fallback) | 0.993 | 0.983 | 4 (sparse) |
| r12 | kegs behind the bar snug to the wall; bars of 11-13 pieces past 220 tiles; two benches along the walls | 0.965 | 0.983 | 3 |
| r13 | the kegs and casks 0.15 off the wall (Westwood's median 0.16; they had stood 0.35-0.66 off) | 0.952 | 0.985 | 3 |
| r14 | spittoons scattered (2): per tile unchanged, the bar came out short; reverted | 0.997 | 0.987 | 5 |
| r15 | r13 re-run (its sheet re-rendered after the renderer fix): queued | 0.952 | 0.985 | 3 |

Chapel r3 re-run as r4 (re-rendered): AUC 0.959, 1 hard-rule room; queued in its place.

### Answers to the independent judge (second pass)

| type | round | change | AUC | cross AUC | hard-rule rooms |
|---|---|---|---|---|---|
| throne room | r6 | (r5's kit, re-rendered with the fixed renderer and the curated pool) | 0.861 | 0.997 | 1 |
| throne room | r7 | a dais of carpet under the throne: too small to read and it kept the runner from laying (the carpets' trims may not touch); reverted | 0.867 | 0.996 | 1 |
| dining hall | r9 | long tables with a bench down each side set as groups where the floor is open, not `table_rows` ("stamped in a perfect diagonal line"); the far bench was there all along, hidden behind its table at 0.2 off | 0.894 | 0.986 | 10 (sparse) |
| dining hall | r10 | the far bench 0.6 off its table, seen past it | 0.884 | 0.985 | 10 |
| dining hall | r11 | a recipe's `cluster` sets stand together: the next table beside the last, a little off the line (Con06a's pair, Con03B's three on a carpet) | 0.908 | 0.971 | 10 |
| hall | r4 | one statue group, not two (two pairs had met in a 2x2 block mid-aisle) | 0.829 | 0.975 | 7 (sparse) |
| shrine | r10 | the ring takes the open spot nearest the room's middle, not the front corner the free pieces lean to ("jammed into the S corner") | 0.971 | 0.919 | 0 |
| gallery | r4-r6 | blue tapestries hung after the paintings (`decor_first`), a gallery reads as one with three paintings (two to a wall by the knowledge base, a wall broken by a door holds one) | 0.938 | 0.989 | 0 |
| gallery | r7-r8 | the centrepiece: the orrery ringed by candelabras mid-walk, a statue pair, basins by the walls; no bench (Westwood's has none; the profile's must dropped it) | 0.941 | 0.996 | 0 |

Shared, opt-in: `cluster`, `decor_first` recipe keys. The gallery still reads as a lone group on a bare floor: its
Westwood example is a set of bays (the shell).
