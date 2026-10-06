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
