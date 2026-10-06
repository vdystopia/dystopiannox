# Motif engine, round 2: log (night-motifs2)

Every round: `py tests/roomlab.py <type> --iter <iter> --engine motifs`, seed 1, n 10. AUC: Westwood against
generated (0.5 = can't tell); cross: the cross-type arrangement features. Hard: rooms with hard-rule findings
(review/roomscore.py, the user's rules). Medians of our rooms; Westwood's bedroom medians: cover 0.146, pieces per tile
0.43, open floor 0.55; storeroom: cover 0.157, pieces per tile 0.38, open 0.46. With ten rooms the AUC moves by about
0.05-0.1 from noise alone. The look is mine against Westwood's gallery, never a blind judgement (those are queued in
`TO_JUDGE.md`).

Starting point (iteration `m0`, round 1 re-run here): bedroom AUC 0.881, cross 0.823, 8 hard. The independent judges
had given round 1 bedroom 6/10 (4.8 / 6.8) and storeroom 7/10 (5.2 / 5.6).

## Bedroom

| Round | What changed | AUC | Cross | Hard | Cover | Per tile | Open | Look |
|---|---|---|---|---|---|---|---|---|
| c1 | Clusters: Westwood's groups mined whole and placed as one (`rules/motifs.py` keeps each room's raw plan; `kit/motifs.py room_clusters`, `compose_clusters`); zones; the focal group first | 0.905 | 0.863 | 10 | 0.071 | 0.20 | 0.75 | Groups intact but the rooms near empty: most groups failed the gate (the whole group or nothing) |
| c2 | Zones measured by floor cells against Westwood's (our typical room is 1.5 Westwood medians, not 2); the richest bed groups first; a group may lose a minor piece (60% of it stands, its lead always) | 0.800 | 0.829 | 9 | 0.084 | 0.24 | 0.69 | Bed with nightstands and chest, desk with its chair; still bare floors |
| c3 | Clusters that can't stand on a wall filtered before they're tried (faced pieces on front walls, kinds the bedroom doesn't hold, capped chests); a slot falls back to the mirror wall; failed wall parts remembered | 0.868 | 0.845 | 7 | 0.092 | 0.29 | 0.66 | Fuller back walls; candelabras on front walls as Westwood's |
| c4 | Zones as many as Westwood median rooms fit (quarters for big square rooms); the kind check per wall side | 0.876 | 0.819 | 7 | 0.091 | 0.29 | 0.66 | No change in the typical rooms (too small to split) |
| c5 | Carpets as Westwood's larger bedrooms lay them (half to two thirds of each side, 0.9 of big rooms) | 0.905 | 0.832 | 7 | 0.097 | 0.31 | 0.66 | The big rooms now read as Westwood's big bedrooms (War07A, Con02a): groups on the back walls round a carpet |
| c6 | No lone chair anywhere (a seat comes with its table or desk); the bed on the longest stretch of the far back wall, not the farthest point; top-up penalises a lead already in the room | 0.916 | 0.839 | 7 | 0.095 | 0.30 | 0.67 | No floating chairs |
| c7 | (lab fairness merged: creature-free renders, Westwood's door counts) Gap dressing: Westwood's one-piece clusters in the gaps between groups | 0.869 | 0.796 | 7 | 0.105 | 0.33 | 0.63 | Fuller; bookcases too common |
| c8 | Dressing without shelves, stores favoured; shelf groups halved in the top-up | 0.853 | 0.792 | 7 | 0.102 | 0.31 | 0.63 | |
| c9 | Hangings on bare back wall at Westwood's rate per floor (trophies, tapestries, paintings) | 0.825 | 0.796 | 7 | 0.102 | 0.31 | 0.63 | Queued first, then replaced by c13 |
| c10 | The focal's wall drawn from where Westwood's rooms of the type stand it from their door (stats focal: a bed across from the door 12 times, beside it 7); a seat only in a cluster with its table, desk or hearth | 0.661 | 0.776 | 7 | 0.103 | 0.33 | 0.63 | No loose chairs at all |
| c11 | Never on the door's own wall (our door cuts leave no room beside the door) | 0.661 | 0.776 | 7 | 0.103 | 0.33 | 0.63 | Same rooms (seed 1 drew no "door") |
| c12 | The focal group placed along its wall nearest 0.72 of the room's diagonal from the door (Westwood's median) | 0.710 | 0.709 | 7 | 0.103 | 0.33 | 0.64 | Cross AUC best of the night |
| **c13** | A group's piece within reach of the wall takes the wall's variant too | **0.710** | **0.709** | 7 | 0.103 | 0.33 | 0.64 | **Queued.** Same rooms as c12 (no such piece on seed 1). Still 7 pieces in a variant Westwood seldom uses on that wall (Desk1 and Bookcase1 on NE), not yet traced |

Hard-rule rooms in c9: all seven are the checker's "sparse" warning (cover under 11-12%). The bedroom identity
(`kit/identity.py ROOMS["bedroom"]`) holds only chests as storage, one chest per room (`kit/objects.py room_cap`) and one
table-or-desk set (HB-3), so Westwood's barrels, crates and spittoons in bedrooms (11 of 28 rooms) can't be added: they
are strays to the checker (DV3-4, TP1-4). The bedroom's story details are therefore the pelt, the hangings and the
second nightstand. The classifier's top give-aways in c9 are density (open floor, pieces per tile, cover), then the
share of the most common kind.

## Storeroom

| Round | What changed | AUC | Cross | Hard | Cover | Per tile | Open | Look |
|---|---|---|---|---|---|---|---|---|
| s1 | The bedroom's engine as it stood (c9) | 0.777 | 0.944 | 3 | 0.147 | 0.34 | 0.52 | Single big crates spaced along all four walls; 16 of 25 pieces Barrel in two big rooms; no ore cart |
| s2 | Top-up penalises a kind already in the room; free heaps allowed in stores of 60+ tiles (Westwood's big Con07B store has them), never in the way in; the kind's focal placed alone when no cluster holds it (the ore store's cart) | 0.657 | 0.952 | 2 | 0.146 | 0.32 | 0.53 | |
| s3 | Stores mixed: a kind past 40% of the room's stock gives way to the type's least used kind | 0.674 | 0.922 | 0 | 0.151 | 0.32 | 0.51 | No monotony warning |
| s4 | Dressing packs small stock against the stock already on a wall (heaps grow) | 0.647 | 0.921 | 0 | 0.151 | 0.32 | 0.51 | Little change: the cover is reached before the dressing |
| s5 | Stock on the back walls only when they have room (Westwood's stores use 2 walls, ours used 4) | 0.686 | 0.894 | 0 | 0.151 | 0.31 | 0.51 | Within Westwood's own range: its stores are sparse too (a few big crates, a barrel heap) |
| **s6** | The engine as it ends the night (bedroom c13's changes; none is specific to stores) | **0.639** | 0.894 | **0** | 0.151 | 0.34 | 0.51 | **Queued** |

Originality: no room is a copy. Bedroom c9's highest similarity to any stock room is 0.44-0.67; the storerooms are all
one family (storage), which the checker counts as unrecognisable.

## Living room (not queued)

| Round | What changed | AUC | Cross | Hard | Cover | Per tile | Open | Look |
|---|---|---|---|---|---|---|---|---|
| l1 | The engine as at bedroom c9 | 0.804 | 0.714 | 7 | 0.118 | 0.30 | 0.54 | The hearth group whole (fireplace and bellows), tables with their chairs; but loose chairs and a barrel-and-chair against walls, three stoves in four rooms, the hearth far across from the door (0.96 of the diagonal; Westwood 0.57) |
| l2 | One stove; the hearth beside the door as Westwood's (stats focal: beside 7 of 10); a seat only with its table | 0.909 | 0.803 | 7 | 0.094 | 0.22 | 0.66 | Hearth placed right, but no loose chairs left: Westwood's living rooms hold 1.3 chairs per 10 tiles, many pulled out by a wall |
| l3 | (bedroom c11) | 0.945 | 0.871 | 7 | 0.095 | 0.21 | 0.67 | |
| l4 | (bedroom c12) | 0.973 | 0.911 | 9 | 0.098 | 0.24 | 0.67 | |
| l5 | Loose seats again in the types Westwood has them, but only within 3 units of a table or the hearth | 0.974 | 0.904 | 7 | 0.111 | 0.26 | 0.60 | Still sparse and unsymmetric; the table groups fail the gate's clearances against the hearth group (kb refusals), so the table count is half Westwood's |

The living room needs its table groups to stand (the gate refuses most of them next to the hearth group) and its
symmetry (Westwood's hearths stand with something either side). It stays on the recipe engine. Laboratory, kitchen,
crypt, barracks and armoury were not reached tonight.

# Round 3 (night-motifs3): every type, set pieces, the first defaults

Seed 1, n 10 each; `m0` the engine as merged, `r0` the recipe engine on the same code, `m10`/`m11` the round's last
iterations before merging master, `m12` and `r1` after it (placement grammar round two, the thin types' fair sheets).
Full tables in MOTIFS.md round 3.

| Round | What changed | Types run | Notes |
|---|---|---|---|
| m0 | The engine as merged (archetype zone plans) | all 15 + bedroom | throne room without a throne; chapel pews singly on walls; halls' tables singly; tavern without a bar |
| m1 | Kin pools for the thin types; a culture's own kind from any curated room when the type's rooms have none; floor lights against a wall; seats within 1.4 of their table; focal groups by novelty (the bed set); rows and bars mined whole | throne, chapel, tavern, crypt | throne still missing (Dun Mir excluded in town: the recipe's own exception now used) |
| m2-m4 | Axis set pieces (`axis_plan`, `compose_axis`): throne on the NW wall's middle, pairs down the walk; walls kept to hangings after a set piece; Westwood's frame (wall lines one unit outside its floor) | throne, chapel | throne rooms read as Westwood's processional; the chapel's pews met the user's cap of 8 |
| m5 | Free groups over the floor where Westwood's middles are used | six types | tavern and barracks worse: kept for the halls only (m8) |
| m6 | Long boards (`board_units`, `compose_boards`) | great hall, dining hall | great hall long boards read as Con06b's; the dining hall's never stood |
| m7-m9 | Pews borrowed by colonnade and sanctum chapels; altar across from the door; a swapped torch in a house becomes a candelabra | all | throne hard-rule rooms 10 -> 5 |
| (fix) | The lab's export race: a map list per process (validate/mapdata.py) | - | every earlier parallel number re-judged; m0/r0 confirmed |
| m10/m11 | Final code; shelves never left apart with bare wall between (`_shelf_gaps`) | all | defaults chosen: bedroom, throne room, crypt, storeroom |
| m12/r1 | After merging master | all | defaults hold; the queued sheets |

QA after merging master (`py tests/qa.py <design> --no-render`; base: `NOX_MOTIF_TYPES=""`, the recipe for every type):

| Map | Errors base / new | Warnings base -> new | Classes that grew or appeared |
|---|---|---|---|
| Thornwick | 0 / 0 | 21 -> 26 | composition.sparse 11 -> 15, composition.bunched 0 -> 1, composition.short_span 0 -> 1 |
| Greywatch | 0 / 0 | 11 -> 17 | composition.sparse 8 -> 10, composition.bunched 0 -> 2, rooms.stray 1 -> 2, floors.hard_seam 0 -> 1 (GrassNorm against a crypt's GreenBrick) |
| Ambermere | 0 / 0 | 17 -> 21 | composition.sparse 12 -> 16, rooms.stray 1 -> 2 (grammar_corners 1 -> 0) |
| Starwell | 0 / 0 | 19 -> 31 | composition.sparse 16 -> 20, composition.bunched 1 -> 5 (five bedrooms), rooms.stray 2 -> 3, composition.anchor_blocked 0 -> 1 (a bed before a chest), composition.shelves_gap 0 -> 1, composition.short_span 0 -> 1 |
| Harrowby | 0 / 0 | 18 -> 22 | composition.sparse 13 -> 16, composition.bunched 2 -> 3 |

Every map builds with 0 errors. The warnings that grow come mostly from the motif bedrooms: sparser than the checker's
range (the bedroom identity holds one chest and no stores, round 2's finding) and their groups gathered round the N
corner on the back walls, as Westwood's bedrooms gather them, which the checker's bunching rule (offset over 0.76)
counts against. Next: spread a bedroom's second group to the far half of the room when the first stands in a corner.
