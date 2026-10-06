# The motif engine (experimental)

A second furnishing engine beside the recipe engine (`mapgen/kit/furnish.py` with `kit/identity.py ROOMS`): rooms
composed from **arrangements mined from Westwood's own campaign rooms**, not from hand-written recipes. The recipe
engine stays the default everywhere.

Why: the room lab's independent blind judges tell every type apart (9-10 of 10), and their reasons repeat across types:
single pieces evenly spaced along walls; one stamped layout per type; a lone table dead centre on a bare floor; barrels
in stepped lines instead of heaps; candelabras where Westwood has torches; recipes making formulas ("the
bookcase-desk-bookcase study end"). Westwood's rooms read as heaped, irregular and lived in. Tuning the recipes improves
the numbers but often makes a new stamp. The hypothesis: arrangements taken from Westwood's rooms carry its irregularity
and composition with them.

    py rules/motifs.py                                          mine the motifs -> rules/out/motifs.json
    py tests/roomlab.py <type> --iter <name> --engine motifs    a room lab iteration furnished by the motif engine
    py review/roomlab/headtohead.py <iterA> <iterB> [type ...]  two iterations side by side (AUC, room score, stamps)

| File | What |
|---|---|
| `rules/motifs.py` | the miner |
| `rules/out/motifs.json` | the motifs, the rooms they come from, the statistics per type |
| `mapgen/kit/motifs.py` | the engine (`MotifFurnisher`, a subclass of the recipe engine's `Furnisher` for its geometry and gate) |
| `mapgen/kit/originality.py` | `furnish_original(..., engine=)`: the switch (`kit/motifs.py engine_for`, `ENGINE_TYPES`, empty) |
| `review/roomlab/labgen.py`, `tests/roomlab.py` | `--engine motifs` for the variant's main room (neighbours keep the recipes); each variant records its motif log and originality check in `variants.json` |
| `review/roomlab/headtohead.py` | the head-to-head table |

## What is mined

From the curated index (`rules/rooms/westwood.json` with `rules/rooms/curated.json`: kept and retyped rooms only, never
the excluded ones; campaign maps Con/War/Wiz only), each room found again with the checker's room finder, wall runs and
doors (as the room lab measures it), in its uv frame:

- **Wall motifs**: each wall run split at its doors is a *stretch*; its pieces from end to end: type, category
  (`kit/objects.py`), family, centre along the stretch measured from a canonical end (the N corner's end on the back
  walls NE and NW, the S corner's end on the front walls SE and SW, so a motif carries to the mirror wall), half length
  along the wall and depth into it, gap from the wall line (snugness), hung or standing, and **heaps** (pieces within
  0.4 units of each other along the wall). The stretch's length, what bounds each end (corner or door), and its share
  in use. Bare stretches are kept: they carry how often a wall stays bare.
- **Corner motifs**: the small pieces (supplies, plants, statues, clutter, lights; never a bed, table or shelf) within
  3.2 units of both walls of a corner, each with its distance from the two walls.
- **Centre motifs**: free-standing groups (pieces within 1.0 unit edge to edge; rugs with what stands on them), each
  piece's offset from the group's centre, the group's place in the room (0-1 over u and v), its distance from a wall.
- **Rooms**: per room, its motifs on each wall, its focal piece's wall (`kit/roomtypes.py focal`) and where that wall
  lies from the main door (opposite, beside, the door's wall), the middle empty or not, lights, and the share of its
  floor carpeted in floor tiles.
- **Statistics per type**: back and front walls bare / half / full, corners and groups per room, the middle empty,
  lights per room, the share of rooms carpeted, the focal's wall, and which motif contents occur together.

174 rooms: 1279 wall stretches (455 furnished, 127 heaps among them), 239 corner motifs, 457 centre groups. For the six
types measured here:

| Type | Westwood rooms | Wall stretches (furnished) | Corner | Centre | Back walls bare/half/full | Front walls bare/half/full | Middle empty | Carpeted | Lights/room | Focal wall from the door |
|---|---|---|---|---|---|---|---|---|---|---|
| bedroom | 28 | 164 (73) | 31 | 32 | .30/.48/.21 | .83/.14/.02 | .57 | .75 | 0.9 | NE opposite 9, NE beside 6, free 6 |
| storeroom | 7 | 37 (17) | 12 | 19 | .20/.60/.20 | .77/.18/.05 | .29 | 0 | 0.1 | - |
| kitchen | 3 | 21 (12) | 3 | 5 | .40/.60/0 | .55/.45/0 | .33 | .33 | 0.7 | NE beside 1, free 1 |
| living room | 14 | 114 (53) | 20 | 22 | .48/.48/.05 | .67/.27/.06 | .36 | .79 | 1.2 | NE beside 4, NW beside 3, NE door 2 |
| tavern | 5 | 59 (27) | 18 | 36 | .60/.40/0 | .59/.28/.14 | .20 | .60 | 2.4 | NE opposite 2 |
| laboratory | 6 | 49 (20) | 12 | 19 | .58/.42/0 | .65/.30/.04 | .67 | .50 | 2.8 | free 3 |

Thin types borrow the motifs of kin types at a third of the weight (`KIN`: a kitchen from living rooms, storerooms,
dining halls and taverns; a tavern from dining halls, living rooms, kitchens and guard rooms; a laboratory from
studies, libraries and herbalists), filtered by the type's never pieces.

## How a room is composed

`MotifFurnisher` (in `kit/motifs.py`) keeps the recipe engine's room geometry and its gate (`Furnisher.try_put`), and
replaces its `furnish()`:

1. **Skeleton.** One Westwood room of the type, of about our room's floor, its culture first. It says which walls are
   used and how fully, which corners hold a heap, where its free groups stood, where the focal stands from its door.
   Only its plan is used: its own motifs at a sixth of the weight, one at most. A carpet is laid in floor tiles in the
   share of Westwood's rooms of the type that have one (the recipe engine's `lay_carpet`).
2. **Focal.** The type's focal piece in a wall motif from another room, on our wall that stands from our main door as
   the skeleton's does, a back wall where the type wants it; a tavern's bar may come as a free group. A bedroom's bed, a
   living room's hearth, a tavern's bar stand once: later motifs holding one are not drawn.
3. **Walls.** Each of our stretches the skeleton uses takes wall motifs end to end (a long wall of ours is two of
   Westwood's), from the same class of wall and a similar share in use. A motif is scaled to its part: the pieces near
   either end keep their distance from the corner, the middle ones scale, a heap moves as one and jitters a little; it
   may run either way; each piece takes the variant for our wall (`side_variant`); one motif in three swaps one kind for
   another of its category that Westwood stands in rooms of the type (keeping its number, its facing).
4. **Corners and groups.** The skeleton's corners get corner motifs (same corner or its mirror); its free groups get
   centre motifs placed where the skeleton's stood, kept inside the room, or at the nearest spot where the group fits
   (the biggest piece must; at least half the blocking pieces).
5. **Density.** While the floor is covered less than the room's draw from Westwood's p25-p75 cover for the type, more
   motifs on the free parts of walls, in corners, and free groups where Westwood's stood.
6. **Rules.** Every piece passes `try_put` (the object knowledge base's caps, clearances, runs, hangings on bare wall;
   the doors' ways in; walkability; the coverage limit) and the kind's profile: never families and never types left
   out, caps and free_most held, the identity's own types (`belongs`), a piece the culture or the identity excludes
   swapped within its category, faced pieces only on back walls, a seat at a table, desk or hearth (or loose in a room
   with a table, in the types where Westwood has loose chairs), a nightstand by the bed, no lone rug or candelabra as a
   group, lights no more than Westwood's rooms of the type hold (and no open torch in a house), a cauldron off the
   hearth. Must pieces still missing come from more motifs that hold them, the recipe's placement as a last resort.
7. **Originality.** A motif once per room, at most two motifs from one Westwood room, and `kit/originality.check` on the
   result: a near copy (0.8 similarity or more to any stock room, mirrors included) is composed again.

Every choice comes from the caller's rng (crc32 seeds), so a type, n and seed always give the same rooms.

## Head to head

Seed 1, ten variants per type, the same shells for both engines (the lab's schedule): the recipe engine as it stood
on this branch (iteration `recipe`, run fresh in this worktree) against the motif engine (iteration `motifs`), from
`py review/roomlab/headtohead.py recipe motifs`. AUC: Westwood against generated (lower is better; 0.5 means it can't
tell them apart). Cross: the same on the cross-type features against all Westwood rooms. Room score: the share of the
type's checks passed in review/roomscore.py (the mean, and how many rooms pass every check). Pieces per tile and cover:
medians, with Westwood's alongside.

| Type | Westwood rooms | AUC recipe | AUC motifs | cross recipe | cross motifs | hard-rule rooms recipe / motifs | room score recipe | room score motifs | pieces/tile recipe / motifs / Westwood | cover recipe / motifs / Westwood |
|---|---|---|---|---|---|---|---|---|---|---|
| bedroom | 28 | 0.98 | **0.838** | 0.906 | **0.745** | 8 / 8 | **0.93** (3 pass) | 0.86 (2 pass) | 0.38 / 0.33 / 0.43 | 0.112 / 0.111 / 0.146 |
| storeroom | 7 | **0.741** | 0.844 | 0.948 | **0.864** | **5** / 7 | 0.87 (2 pass) | **0.88** (3 pass) | 0.40 / 0.34 / 0.38 | 0.186 / 0.173 / 0.157 |
| kitchen | 3 (pool) | 0.999 | **0.966** | 0.965 | **0.859** | **4** / 5 | **0.95** (6 pass) | 0.78 (2 pass) | 0.46 / 0.29 / 0.20 | 0.160 / 0.138 / 0.082 |
| living room | 14 | 0.998 | **0.951** | 0.936 | **0.927** | **5** / 6 | **0.92** (5 pass) | 0.84 (0 pass) | 0.37 / 0.33 / 0.38 | 0.134 / 0.123 / 0.140 |
| tavern | 5 (pool) | **0.927** | 0.971 | 0.988 | **0.982** | 10 / 10 | **0.82** (0 pass) | 0.75 (0 pass) | 0.36 / 0.30 / 0.27 | 0.151 / 0.119 / 0.133 |
| laboratory | 6 | 1.0 | **0.907** | 0.967 | **0.845** | **8** / 10 | **0.92** (3 pass) | 0.82 (0 pass) | 0.38 / 0.27 / 0.25 | 0.119 / 0.090 / 0.089 |

With only ten rooms the AUC is noisy: it moves by about ±0.05 to 0.1 from one change in composition to the next (the
bedroom ranged 0.76-0.85 over the last five iterations). So only the bedroom's and the laboratory's gains are clearly
more than noise. The cross-type AUC measures how pieces relate to each other (spacing, snugness, rows, symmetry,
facing, the way in). It is lower for the motif engine in every type, so the piece-to-piece arrangement is closer to
Westwood's.

What still gives the motif rooms away (the classifier's top features and the findings most rooms share):

- **bedroom:** fewer chairs and chests per tile than in Westwood's small rooms; a free piece in the middle (a chair
  pulled away from the desk, a rug); no nightstand in 7 of 10 rooms (a nightstand is kept only beside a bed).
- **storeroom:** heaps of crates and barrels standing in the middle of the floor (Westwood's centre heaps come from
  rooms whose middle is their aisle); the way in blocked early.
- **kitchen:** a crowded middle, and benches that Westwood's kitchens don't have (borrowed from kin rooms).
- **living room:** pieces stand apart and out of line (nothing forms a row), and the hearth is far across the room
  from the door.
- **tavern:** no clear bar in most rooms, chairs scattered loose, too many kinds of piece (38), table caps exceeded.
- **laboratory:** back walls lined more than Westwood's, more chairs, a crowded middle; the must pieces (3 benches,
  2 shelves, a desk) are not always all there.

**Hard rules.** The motif engine meets fewer of the room score's checks (cover, pieces per tile, walls used, types,
must) in every type except the storeroom. Those ranges were written for the recipe engine, and the motif rooms are
sparser along the walls: Westwood's own back walls are bare 30-58% of the time, its front walls 55-83%. Some of the
findings are real faults:

- must pieces missing, such as a bedroom's chest or a laboratory's second shelf;
- the tavern's table caps exceeded and its missing bar;
- ways in blocked 3-4 units inside a door in the storerooms.

No layout is a copy. The originality check's highest similarity to any stock room is 0.48-0.77 (0.8 counts as a copy;
the recipe engine is checked the same way).

**Variety.** There is no stamp. On average two variants share 6-17% of their motifs (Jaccard of the motif ids). The
most any two share is 26-42%, because a thin type has few motifs to draw from. Ten rooms use 3-7 different skeletons,
and a motif stands only once in a room.

**By eye.** I compared Westwood's gallery, the recipe renders and the motif renders side by side. This is my own look,
not a blind judgement; the blind sheets are queued in `TO_JUDGE.md`.

- **bedroom: motifs closer.** The bed, desk, shelves and chest gather on the back walls round the N corner, as in
  Westwood's rooms, and carpets appear at Westwood's rate. There is no table set dead centre. But the floor in front
  is emptier than in Westwood's small rooms, and candelabras sometimes still cluster by the door.
- **storeroom: recipe closer.** The motif rooms heap crates and barrels well (real heaps, not stepped lines), but too
  many heaps stand out in the middle of the floor. The recipe puts the stock along the walls with an aisle, which
  reads more like Westwood's.
- **kitchen: about even.** The motif kitchens look more lived in (stores heaped round the hearth) but are crowded in
  the middle and have benches. The recipe's kitchens are tidier and emptier. Westwood has only three kitchens, so both
  are judged against a pool.
- **living room: about even, slightly motifs.** The hearth stands on a back wall with shelves either side, and the
  tables are off centre, with no rug-and-table stamp in the middle. But the pieces stand apart and scattered, and no
  group reads as the household's table.
- **tavern: recipe closer.** The motif taverns lose the bar as a clear focus and scatter chairs and stools. The
  recipe's room of bar and tables reads more like a tavern.
- **laboratory: motifs closer.** Workstations, bookcases and potion shelves stand along the back walls in short,
  irregular runs, with the alchemist's desk on its own and carpets. The recipe's lab is one stamped arrangement round
  a central table.

## Round 2: clusters, zones, a centrepiece (night-motifs2)

The independent judges' faults with round 1 (bedroom 6/10, storeroom 7/10): pieces floating free (a lone chair, a chair
facing nothing), chairs not drawn up to tables, heaps mid-floor in the way in, everything on one back wall round a big
empty carpet, too many kinds, large bare floors. Round 2 composes rooms from **clusters** instead of motifs
(`COMPOSE = "clusters"` in `kit/motifs.py`; round 1's `compose_room` stays behind `COMPOSE = "motifs"`). Log of every
round: `LOG_motifs.md`.

- **What is mined.** `rules/motifs.py` now keeps each curated room's raw plan (`rooms[].pieces`: every piece in the room's
  frame with the wall it stands against, and the room's walls, doors and floor cells). `kit/motifs.py room_clusters`
  cuts it into Westwood's groups: pieces within 0.9 units of each other, edge to edge, kept together. A group against one
  wall is a **wall cluster** (its free pieces, a desk's chair or a bed's chest, kept relative to the wall piece they
  stand by); a heap of small pieces against both walls of a corner a **corner cluster**; a group off the walls a **free
  cluster**; a hanging its own. A group running round a corner with a big piece in it splits by wall.
- **Groups, not pieces.** A cluster is placed as one (`_realise`): its lead piece and most of the rest stand, or
  nothing does. Its seats face its table, desk or hearth whichever way it was turned (`_face_seats`, the kit's
  chair_facing). No cluster of seats alone (`_cw`). Clusters that can't stand on a wall (a faced piece on a front wall, a
  kind the room's identity doesn't hold, a capped chest) are filtered before they are tried (`_kinds_ok`).
- **Scale: zones.** A room is split into as many zones as Westwood's median room of the type fits by floor cells
  (`_zones`: strips across the long axis, quarters for a big square room, 1.6 units of floor between them; our typical
  bedroom is one zone, the large ones two or three). Each zone takes the plan of a Westwood room of its own size (its
  clusters' walls, corners and places), each slot filled with a cluster of the same lead and size from another room.
- **One centrepiece.** The type's focal cluster first, the richest groups preferred (a bed with its nightstands and
  chest), on the longest stretch of the back wall across from the main door, at its own place along the wall
  (`_place_focal`). A kind whose focal no cluster holds (an ore store's cart) gets it alone against a wall.
- **Density and details.** Top-up on the free parts of the walls, back walls first, a step of floor between groups,
  leads and kinds already in the room penalised; in rooms well over Westwood's size, a free group; then the gaps
  dressed with Westwood's one-piece clusters (a chest, a nightstand, a plant; stock in a store packed against the
  stock), hangings on bare back wall at Westwood's rate per floor, carpets as Westwood's larger rooms lay them.
- **Stores.** Stock on the back walls while they have room (Westwood's stores use two walls), kinds mixed (no kind of
  store past 40% of the stock), free heaps only in stores of 60 tiles or more, the way in from every door kept clear
  4.4 units deep for every engine piece.
- **Variety.** One kind per category per room (`UNIFY`: one chair, chest, nightstand, candelabra kind), no motif swaps.
  Floors and walls come from the shells; carpets vary in size and place.

- **The focal's place.** The focal's wall is drawn from where Westwood's rooms of the type stand it from their door
  (`_focal_wall`, stats focal: a bed across from the door or beside it, a hearth beside it), on the longest stretch of
  that wall, along it nearest 0.72 of the room's diagonal from the door (Westwood's median).

Results (seed 1; the blind sheets are queued in `TO_JUDGE.md`): bedroom c13 AUC 0.71 (round 1: 0.838-0.88), cross 0.709
(round 1: 0.745), 7 hard-rule rooms (all the checker's "sparse" warning: the bedroom identity allows one chest and no
barrels or crates, so Westwood's density can't be reached with its own pieces); storeroom s6 AUC 0.639 (round 1:
0.844), cross 0.894, 0 hard-rule rooms (round 1: 7). The living room is not ready (best l1 0.804, but loose chairs and
too few tables; see `LOG_motifs.md`).

## Verdict (round 1)

The hypothesis holds in part. Learned arrangements carry Westwood's heaps, its clusters on the back walls and its bare
walls, and no two composed rooms share a stamp. The classifier separates them from Westwood less well in four of six
types, and the cross-type arrangement features improve in all six. But the engine can't replace the recipes yet:

- It misses more of the user's hard rules than the recipes do (must pieces too thin, the tavern's bar, crowded
  middles).
- Westwood's motifs come from rooms smaller than ours. Our rooms come out sparse along the walls, and the top-up then
  fills the gap with groups in the middle.

**Don't make it the default for any type yet** (`ENGINE_TYPES` stays empty). The candidates are **bedroom** and
**laboratory** first, then the living room, once two things are true: their hard-rule findings are down to the recipe
engine's level, and an independent blind judgement agrees. The storeroom and the tavern should stay on the recipes.

Next steps, ordered by what the judges and the numbers point at:

1. **Free groups:** only add them where the skeleton's middle is used, and keep supply heaps in corners and along walls
   (Westwood's storerooms keep their aisle). In the top-up, prefer more wall motifs end to end over more groups.
2. **The tavern's focal:** mine the bar and its kegs as one motif and place it first, as the recipe does.
3. **Must pieces:** draw the motifs that hold them before the skeleton's other walls, not after.
4. **Size:** Westwood's motifs come from rooms of 9-45 tiles, and ours are built 1.25 times larger. Mine pairs of
   neighbouring motifs along a wall as one longer motif, so a long wall of ours is filled from Westwood's own longer
   walls.
5. **Confirm:** run a second seed and the blind judge before calling any of it better.

## Round 3: every type, set pieces, the first defaults (night-motifs3)

Why: the judges named the insides of the recipe rooms (singles at a regular pitch along walls, one table set stamped in a
grid or ring, the focal off its axis, tombs touching, benches never a congregation), and wherever both engines were
judged the motif engine did better (review/NIGHTLOG.md 03:44). Log of the round: `LOG_motifs.md`.

**Where it stood** (iteration `m0`, the engine as merged with archetypes, seed 1, n 10, every type): it composed every
type from its own Westwood rooms, but four types had no plan it could carry out:
- **throne room**: no throne at all (its four Westwood rooms are Land of the Dead and Dun Mir; every piece was excluded
  for a town room and nothing swapped in; a focal "by the door" was never placed): a clump of statues mid-floor;
- **chapel**: the altar off the axis, pews singly along the walls (a cap of 8 and no congregation);
- **great hall, dining hall**: tables singly round the walls (Westwood's long boards have gaps over 0.9, so the miner cut
  them into lone tables);
- **tavern**: the bar cut into three wall clusters by the miner, so no bar stood (a lone counter piece at the end).

**What was added** (`mapgen/kit/motifs.py`):
- **Axis set pieces** (`axis_plan`, `compose_axis`): a Westwood room's pieces in the frame of its axis of symmetry (the
  line through its throne or altar, or through the midpoint of its mirrored pairs, whichever pairs most of its pieces),
  each with its distance from the head wall, its offset from the axis, its mate across it. A throne room or chapel stands
  the throne (Dun Mir's three pieces, as the recipe does; the Lich's in the Land of the Dead) or the altar centred on
  the head wall (the NW wall for a throne, which faces SE only; for an altar the back wall across from the main door),
  then the plan's pairs at their distances scaled to our room's length and their offsets kept (the side walls' pieces at
  their distance from the side wall), both of a pair or neither, the walk kept clear (a runner in the processional);
  rows of pews repeat down the nave at Westwood's pitch (Con07B's congregation, borrowed by the colonnade and sanctum
  plans), within the kind's own cap (the user's 8 pews). Plans: the archetype's own rooms and kin rooms (thin types,
  `KIN`: a throne room from the halls and the gallery, a chapel from the shrines and halls; a great hall from the
  dining halls, halls and taverns; a study from the libraries, solars and laboratories).
- **Rows mined whole** (`ROW_LINK`): a crypt's tombs, a chapel's pews and columns, a hall's boards stay one cluster
  with their real gaps, so a row of sarcophagi moves as one, on its line.
- **Bars whole**: a tavern's bar (a U of counter pieces with the kegs inside) is one rigid cluster on the back wall it
  stands on, never turned, mirrored or re-varianted, placed first as the tavern's focal.
- **Long boards** (`board_units`, `compose_boards`): tables of one kind end to end at their pitch with their benches
  at their offsets (Con06b's great hall), down our room's long axis, one to three side by side.
- **A free pass** for the halls (great hall, dining hall): Westwood's free groups over the floor, as many as its rooms
  hold for their floor, before the walls take the cover.
- **Culture swap** (`all_kinds`): a piece the room's culture excludes swaps for the culture's own kind of the same
  family from any curated room (a town column for a Land of the Dead one), when the type's own rooms have none.
- **Its own faults**: floor lights only within 1.6 of a wall line (Westwood: 90% of its floor lights; the throne
  room's basins down the walk excepted); a pulled-out seat within 1.4 of its table (no lone chair); the focal group
  drawn by novelty over the map's rooms of the type, not the richest first (the stamped bed with two nightstands and a
  chest at its foot); two shelves on one wall with bare wall between them are not left (`_shelf_gaps`); a torch swapped
  in for a basin in a house becomes the house's candelabra.
- **The lab's export race** (`validate/mapdata.py export`): parallel room-lab runs of different types shared one map
  list file and could read each other's maps (a run's metrics silently came from another iteration's export); the
  list file is per process now. Every number below was measured after the fix.

**Results** (seed 1, n 10; AUC Westwood against generated, lower is better; template: the batch's mean pairwise layout
similarity, against Westwood's p50/p90 for the type; r0 the recipe engine as it stands):

| Type | Recipe r0 AUC / template | Motifs m0 AUC / template | Motifs now AUC / template | Westwood p50/p90 | Default now |
|---|---|---|---|---|---|
| bedroom | 0.845 / 0.287 | (m2 on night-variety: 0.83 / 0.209) | 0.868 / 0.263 (m11) | 0.195 / 0.227 | **motifs** |
| throne room | 0.869 / 0.555 | 0.964 / 0.793 (no throne) | **0.843 / 0.533** (m11) | 0.171 / 0.197 | **motifs** |
| crypt | 0.882 / 0.368 | 0.888 / 0.271 | 0.888 / **0.271** (m11) | 0.287 / 0.372 | **motifs** |
| storeroom | 0.809 / 0.572 | 0.781 / 0.471 | 0.796 / **0.471** (m11) | 0.230 / 0.256 | **motifs** |
| kitchen | 0.970 / 0.335 | 0.931 / 0.380 | 0.927 / 0.356 (m10) | 0.146 / 0.194 | recipe (in the QA maps a stove crowded the hearth) |
| laboratory | 0.742 / 0.339 | 0.750 / 0.319 | 0.825 / 0.339 (m10) | 0.164 / 0.181 | recipe |
| shop | 0.896 / 0.216 | 0.779 / 0.271 | 0.903 / 0.296 (m10) | 0.148 / 0.177 | recipe |
| living room | 0.864 / 0.280 | 0.904 / 0.259 | 0.915 / 0.262 (m10) | 0.219 / 0.236 | recipe |
| guardroom | 0.518 / 0.270 | 0.510 / 0.278 | 0.517 / 0.298 (m10) | 0.205 / 0.215 | recipe (more hard-rule rooms: 5 against 1) |
| cell | 0.955 / 0.470 | 0.978 / 0.413 | 0.978 / 0.413 (m10) | 0.282 / 0.339 | recipe |
| barracks | 0.947 / 0.229 | 0.893 / 0.309 | 0.943 / 0.326 (m10) | 0.228 / 0.271 | recipe |
| tavern | 0.907 / 0.434 | 0.910 / 0.460 | 0.925 / 0.493 (m10) | 0.262 / 0.292 | recipe |
| chapel | 0.936 / 0.362 | 1.000 / 0.594 | 0.968 / 0.290 (m10) | 0.093 / 0.120 | recipe |
| great hall | 0.876 / 0.311 | 0.888 / 0.280 | 0.872 / 0.369 (m10) | 0.160 / 0.230 | recipe |
| study | 0.994 / 0.407 | 0.993 / 0.455 | 0.973 / 0.334 (m10) | 0.332 / 0.332 | recipe |
| dining hall | 0.971 / 0.302 | 0.997 / 0.319 | 0.955 / 0.236 (m10) | 0.191 / 0.191 | recipe |

By eye against Westwood's galleries: the motif throne rooms now read as Westwood's (the throne centred at the head of a
walk, basins and statues in pairs down it, the walls bare but for hangings), where the recipe's throne stands at the end
of the NW wall; the motif crypts keep their tombs on lines with gaps and their floors open, where the recipe's tombs
touch in clumps; the motif storerooms are sparse with a heap or two as Westwood's, where the recipe lines barrels along
every wall. The chapel's congregation stands only where the axis plan fits (a door in the head wall's middle sends it
back to the clusters, whose pews line the walls): not yet. The great hall's boards read as Westwood's long boards, but
its feast-hall rooms still scatter single tables round the walls. The tavern has its bar now, but its floor is still a
bare carpet with the tables round the walls. With ten rooms the AUC moves by 0.05-0.1 from noise alone; the sheets are
queued in `TO_JUDGE.md` (one per type) for the independent judges.

**Defaults** (`ENGINE_TYPES`): bedroom, throne room, crypt, storeroom. `NOX_MOTIF_TYPES` (comma-separated, "" for none)
overrides it for a comparison. QA of the five story maps: see `LOG_motifs.md`.

Next, by what the renders show: the chapel's congregation off the axis plan (pews in rows either side of an aisle
wherever the altar stands); the tavern's floor (Westwood's taverns stand tables of two kinds over the floor among the
drinkers; ours keep them to the walls); the great hall's feast crowd; the laboratory's and shop's density in rooms
1.5 times Westwood's floor.
