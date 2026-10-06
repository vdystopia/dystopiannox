# Room lab baseline (2026-10-05)

`py tests/roomlab.py all --iter baseline` (10 variants a type, seed 1), the kit as of commit 29c63e5. Scorecards:
`review/out/roomlab/<type>/baseline/index.html` (not committed; re-run to rebuild). Blind judge: the lab's builder
(Claude, vision) by `JUDGE.md` on bedroom, throne room and tavern.

**Nothing is indistinguishable yet.** The classifier separates every type's batch from Westwood's campaign rooms
(AUC 0.94-1.00; stop at 0.60) and the blind judge picked all 30 pictures right (stop at 60%). Generated blind scores:
bedroom 3.8 against Westwood's 7.2, throne room 4.6 against 7.0, tavern 4.4 against 6.2 (stop at Westwood's minus 0.5).

| Type | Westwood rooms | AUC | Cross AUC | Blind acc. | Hard-rule rooms | Worst findings |
|---|---|---|---|---|---|---|
| bedroom | 40 | 1.00 | 0.922 | 100% | 2/10 {"warnings": 2, "way in": 2} | more kinds of object than Westwood (17); too much in the middle (0.05): the middle is crowded |
| study | 2 | 1.00 (pool) | 0.983 | - | 4/10 {"warnings": 3, "way in": 3, "must": 1} | more lab pieces than Westwood's (0.45 per 10 tiles); too much in the middle (0.09): the middle is crowded |
| living_room | 15 | 1.00 | 0.901 | - | 2/10 {"way in": 1, "warnings": 1} | more shelves pieces than Westwood's (1.63 per 10 tiles); back walls lined more than Westwood's (0.55) |
| kitchen | 10 | 1.00 | 0.946 | - | 5/10 {"reads as": 2, "way in": 5} | more storage pieces than Westwood's (2.33 per 10 tiles); too full: furniture covers 0.23 of the floor |
| laboratory | 19 | 1.00 | 0.96 | - | 9/10 {"caps": 4, "warnings": 4, "must": 5, "way in": 2, "repeat": 1} | more plant pieces than Westwood's (0.62 per 10 tiles); too much in the middle (0.07): the middle is crowded |
| herbalist | 2 | 1.00 (pool) | 0.984 | - | 5/10 {"way in": 2, "must": 1, "focal": 1, "reads as": 3} | too much in the middle (0.08): the middle is crowded; more plant pieces than Westwood's (0.36 per 10 tiles) |
| library | 7 | 0.99 | 0.996 | - | 1/10 {"warnings": 1, "way in": 1} | too much in the middle (0.14): the middle is crowded; more plant pieces than Westwood's (0.39 per 10 tiles) |
| smithy | 2 | 1.00 (pool) | 0.928 | - | 2/10 {"way in": 2} | too much in the middle (0.13): the middle is crowded; too many pieces in the middle (0.46) |
| storeroom | 22 | 0.95 | 0.975 | - | 5/10 {"focal": 3, "way in": 4, "caps": 1, "warnings": 1} | back walls lined more than Westwood's (0.44); more kinds of object than Westwood (13) |
| barracks | 16 | 1.00 | 0.952 | - | 2/10 {"caps": 1, "warnings": 2} | 1 focal pieces (the type's focal kind); more chair pieces than Westwood's (1 per 10 tiles) |
| armoury | 16 | 1.00 | 0.98 | - | 1/10 {"must": 1} | a run of 14 of one kind along one wall; 1 runs of 3+ of one kind along the walls |
| shop | 16 | 0.94 | 0.966 | - | 3/10 {"way in": 3, "focal": 1} | back walls lined more than Westwood's (0.66); more shop rack pieces than Westwood's (3.06 per 10 tiles) |
| tavern | 2 | 0.97 (pool) | 0.992 | 100% | 10/10 {"caps": 10, "reads as": 7, "warnings": 3, "way in": 1} | more rug pieces than Westwood's (0.22 per 10 tiles); more kinds of object than Westwood (44) |
| dining_hall | 3 | 1.00 (pool) | 0.986 | - | 3/10 {"reads as": 2, "caps": 1} | too much in the middle (0.16): the middle is crowded; everything in rows (0.97): grid-like |
| great_hall | 2 | 0.94 (pool) | 0.993 | - | 10/10 {"caps": 10, "warnings": 1, "way in": 1, "must": 2} | back walls lined more than Westwood's (0.34); 5 pieces face the wrong way for their wall |
| hall | 17 | 0.99 | 0.979 | - | 3/10 {"caps": 1, "warnings": 1, "repeat": 1} | more bench pieces than Westwood's (0.59 per 10 tiles); back walls lined more than Westwood's (0.29) |
| throne_room | 4 | 1.00 (pool) | 0.994 | 100% | 3/10 {"caps": 2, "warnings": 1} | 3 pieces face the wrong way for their wall; back walls lined more than Westwood's (0.16) |
| chapel | 1 | 0.98 (pool) | 0.965 | - | 6/10 {"caps": 6} | too much in the middle (0.08): the middle is crowded; more kinds of object than Westwood (14) |
| crypt | 30 | 0.98 | 0.962 | - | 2/10 {"warnings": 1, "caps": 1} | 18 focal pieces (the type's focal kind); too full: furniture covers 0.20 of the floor |

"(pool)": Westwood has under 6 rooms of the type; compared with its pool (rules/rooms/westwood.json types named by the
profile, then its family). Cross AUC: type-free features (spacing, overlaps, snugness, rows, symmetry, facing, the way
in) against all 235 Westwood rooms. Hard-rule rooms: the brief's rules (review/roomscore.py judge), statues facing a
wall, a blocked way in, overlaps; "warnings" are the checker's findings in the room.

## What gives them away (the classifier's best single features, and the blind judge)

- **bedroom**: hangings and trophies (Westwood's bedrooms have almost none), too many kinds of object (12 against 6),
  a table set with chairs, often two, on rugs in the middle; candelabras spaced evenly round the walls. Westwood's
  bedrooms: one carpet, the bed with its nightstands and chest, a dresser; shaped rooms (L-rooms, niches, a dais).
- **throne room**: one template every time (a plain rectangle, the four-piece Dun Mir throne on its dais in the NW
  corner, a runner to an SE door, pillars and statues dotted singly); pieces against walls in variants Westwood does
  not use there; too many kinds of object. Westwood's four are shaped halls built round a set piece (Hecubah's, the
  Lich Lord's) with paired columns, braziers and inlaid floors.
- **tavern**: back walls lined, everything in rows, rugs under tables, 40+ kinds of object; a short bar in the north
  corner with no stools, kegs end to end along the SW wall, single table sets dotted at even gaps. Westwood's taverns
  are built round a big bar ringed with stools, the seating grouped (on a carpet, in the corners).
- **great hall**: two hearths, lined back walls, odd facing, a crowded middle; **crypt**: twice Westwood's tombs and
  cover, the way in blocked by the rows; **armoury**: every wall used and lined end to end (runs of 14 racks or
  shelves) where Westwood leaves walls bare.

Furthest from Westwood (every type's AUC is near 1, so by the hard rules, findings and cross AUC): tavern and great
hall (all 10 rooms break a hard rule: caps; the tavern reads as a dining hall in 7), laboratory (9 of 10: must, caps,
checker warnings), throne room and library (cross AUC 0.99+), study and herbalist (pool AUC 1.0, cross 0.98).
Closest: shop and storeroom (AUC 0.94-0.95), living room and bedroom (cross AUC 0.90-0.92).

## Notes on the evidence

- Thin types (Westwood campaign rooms): chapel 1, study 2, tavern 2, smithy 2, herbalist 2, great hall 2, dining hall 3,
  throne room 4. Their numbers come from the pool and are flagged FALLBACK in every finding.
- The index has misfiled rooms that weaken the pools: Con02a's tavern (bar, barman, stools) is filed as a shop
  (its barman is a Shopkeeper object), and War07A's walled garden as a hall. Two of the tavern sheet's Westwood
  pictures were shops. Worth a fix in rules/rooms/westwood.py `classify` (owner: the rules, not the lab).
- Some lab shells come out with the checker's door warnings ("ArchedHalfDoor stands on a wall piece"), in the
  galava styles with neighbouring rooms: real kit output, reported as hard-rule warnings.
- Westwood's pictures can show monsters and NPCs; the lab's rooms have none (JUDGE.md tells the judge to ignore them).
- Reproducibility: these baseline maps were built before the harness named each map by (type, seed) alone; the
  furnisher seeds its palette from the map's name, so a fresh run of seed 1 now gives the same rooms on every run but
  not exactly these. Start a type's tuning with a fresh reference run (`py tests/roomlab.py <type> --iter ref`) and
  compare iterations with it; the baseline's numbers stand as the picture of where every type starts.
