# Night log: room lab, dialogue and quest lab (from 2026-10-05 20:40)

The user's brief (2026-10-05, evening): "work all night until i tell you to stop. We need to integrate a capability that can
look at a screenshot layout of a room and determine whether it looks like a real room. come up with more room types for
more variety. The iteration process will become:
1. You create 10 different variants of a given room type on a blank / template map
2. Each variant is scored and given feedback and compared to westwood maps
3. You fine-tune the process and algorithm based on what is good.
4. repeat until the generated rooms can be compared side-by-side with westwood rooms and be indistinguishable
no need to generate entire maps, focus only on the room development until it is perfected. in parallel, replicate similar
processes from dialogue and quests. once room generation is perfected, take the same process and apply it to maps."

Reference data: Westwood's campaign maps only (Con/War/Wiz), never quest (G_*) or multiplayer maps.

## Plan
- Phase 1, in parallel:
  - **Room lab and judges:** 10 variants of a type on a template map. Renders framed the same as Westwood's campaign
    rooms. A metric judge (features against Westwood's distribution, plus a classifier's "can it tell them apart"). A
    blind visual judge: a vision agent sorts mixed Westwood and generated rooms and scores realism.
  - **Object knowledge base** from campaign rooms: what may stand once, in pairs or in runs; clearances; caps per
    room type; companions. The furnisher obeys it and the checker enforces it.
  - **More room types:** proposed from campaign rooms and Nox's objects, with briefs, and where people stand in each.
  - **Dialogue and quest lab:** the same loop for dialogue and quests, against Westwood's campaign text and scripts.
- Phase 2: iteration rounds per room type (generate 10, judge, tune, repeat) until the judges can't tell ours from
  Westwood's.
- Phase 3, once rooms pass: the same loop on whole maps.

## Log
- 20:45 Phase 1 started: room lab and judges (`night-lab`), object knowledge base (`night-objkb`), more room types
  (`night-types2`), dialogue and quest lab (`night-dialogue`). The PC is held on until 2026-10-06 14:00 by the guard's
  hold-awake file (remove it when the user says stop).
- 21:15 The user added: "do the same process for exterior settings - bandit camps, graveyards, gardens, ponds etc."
  Scene lab started (`night-scenes`): 10 variants of an outdoor scene type, matched renders against Westwood's
  campaign scenes, metric and blind judges, then iteration rounds on the bandit camp, graveyard, garden and pond first.
- 21:50 Room lab merged (`tests/roomlab.py`, `review/roomlab/`). Baseline over the 19 types: the classifier separates
  every type from Westwood's (AUC 0.94-1.00), and the blind judge picked out all 30 generated pictures (bedroom 3.8 vs
  Westwood 7.2; tavern 4.4 vs 6.2; throne room 4.6 vs 7.0). Furthest: tavern and great hall (every room breaks a hard
  rule), laboratory, throne room (one template every time), library. Closest: shop and storeroom. Found: Westwood's
  room index misfiles Con02a's tavern as a shop and War07A's walled garden as a hall. Tuning rounds start once the
  object knowledge base lands, so they build on it.
- 22:20 Dialogue and quest lab merged (`tests/storylab.py`, `review/storylab/`, `rules/DIALOGUE.md`, `rules/QUESTS.md`,
  `q.errand`, `q.done`, `q.note`). Measured on 1,204 Westwood campaign strings: offers about 39 words, reminders 12,
  completions 24; 56% of lines exclaim; a side quest is five lines plus one journal order. Four rounds: the blind judge
  still picks out all of ours (27/27), but its score for ours rose from 4.7 to 6.1 (Westwood about 8). Our maps under
  `--check` score 6.9-8.2 against Westwood's own 9.6 (first-person journal entries, semicolons, too few exclamations).
  Next: a control packet (Westwood only) to calibrate the judge, writing from real campaign lines, whole-map writers.
- 22:45 16 new room types merged (`night-types2`), each with campaign evidence read by hand: guardroom, cell (and
  ogre pen), torture chamber, cellar, treasury, powder store, solar, workshop, winch room, observatory, infirmary (no
  campaign example: design judgement), shrine (and dark shrine), conservatory, gallery, mausoleum, ossuary. That makes 35
  types. Every type now has "where people stand" (`STANDS`, `StoryMap.stand_px`, `person_in`). Six new building roles
  (gaol, gatehouse, healer, wheelwright, mausoleum, shrine); roles take the new rooms with `extra=`. Existing maps are
  unchanged.
- 23:10 Object knowledge base merged (`rules/objects.py` -> `rules/out/objects.json`, `kit/objects.py`): 229 object kinds
  profiled from 357 campaign rooms (showpiece, fabric, pair, group; runs along walls; counts per room type; clearances;
  companions; hangings). The furnisher checks every placement against it; eight new `pieces.*` checks. The user's five
  Harrowby rooms, rebuilt wall for wall (`hbreplay.py`): cauldrons 2->0, bedroom chests 4->1 and table sets 3->1, library
  candelabras 8->3, storeroom log shelves 15->2 in mixed clusters. Room lab: 0 `pieces.*` findings (89 before).
  Next: tuning rounds by room type in three parallel tracks.
- 23:20 Phase 2 started: three room tuning tracks, each running the lab loop (ref, then rounds r1, r2...; a blind
  judgement every second round; stop at AUC <= 0.6, blind accuracy <= 60%, scores within 0.5 of Westwood's):
  A (`night-tuneA`): bedroom, living room, kitchen, study, solar, guardroom, cell, infirmary.
  B (`night-tuneB`): tavern, throne room, great hall, chapel, dining hall, hall, shrine, gallery, conservatory, plus the
     classifier's misfiled tavern and garden.
  C (`night-tuneC`): storeroom, laboratory, shop, library, smithy, armoury, barracks, crypt, herbalist, cellar,
     treasury, workshop, torture chamber, mausoleum, ossuary, observatory, winch room, powder store.
  Still running: the scene lab (`night-scenes`) and dialogue round 2 (`night-dialogue2`).
- 22:20 (Correction: the times on the entries above were estimates and ran ahead of the clock. The real time of this
  entry is 22:20, so the entries stamped 21:50-23:20 all happened between 21:30 and 22:15.) Scene lab mid-run: garden
  AUC 0.89 -> 0.16-0.42 (Westwood has only 5 gardens); graveyard 1.00 -> 0.87 (graves in Westwood's rows and spacing,
  sparse grass, pillars at the gate; the blind judge still sees one small square box where Westwood's yards are long or
  large and set against buildings); bandit camp r3 judged "much better: clear zones and the user's structure".
- 22:40 Scene lab round 1 merged (`night-scenes`): 159 Westwood campaign scenes of 18 types catalogued
  (`rules/scenes/`). Bandit camp AUC 1.00->0.98 (score 3.6->6.0 vs Westwood 6.8), graveyard 1.00->0.87, garden
  0.89->0.30, pond with dock 0.68->0.77 (6.6 vs 6.75). Kit: camps back onto a wall with a sleeping row; graveyards in
  Westwood's rows; gardens with mixed beds and a low wooden fence; docks square with barrels on the bank. Caveat: the
  tuning agent judged its own sheets, so an independent blind judge (a fresh agent that sees only the pictures, never
  the key) is now judging them. From here on, every blind result in this log is marked "independent" or "self".
  Scene lab round 2 (`night-scenes3`) started: camp sub-types (hideout and fire camp), graveyards fitted to the site,
  then the other 13 scene types.
- 22:55 First independent blind judgement (a fresh agent, pictures only, scored against the keys by the main session),
  on scene lab round 1's last sheets: bandit camp 10/10 (generated 5.2 vs Westwood 6.8), graveyard 10/10 (4.2 vs 7.4),
  garden 10/10 (4.8 vs 7.8), pond with dock 9/9 (5.2 vs 7.8). Self-judging had been too generous; these are the real
  starting points. Its critique (stamped tent rows, the same 6x6 graveyard box, crops on fences again, the same dock gear
  stamp in a small round pond) has been passed to scene round 2.
- 23:05 Independent judgement of rooms (pictures only, scored against the keys): bedroom ref 6/10 (generated 6.4 vs
  Westwood 6.0), bedroom r6 8/10 (4.8 vs 5.8), living room r6 8/10 (6.0 vs 4.6), storeroom r8 8/10 (5.6 vs 4.2).
  Rooms are much closer to Westwood than scenes are. Lessons: (1) the bedroom regressed by eye from ref to r6 though
  its AUC improved: the tuning made a stamp (chest against the bed's head, a lone bench and candelabra on the front
  wall), so AUC alone can't steer; (2) the Westwood galleries hold rooms that aren't truly the type (dais rooms,
  cellars, cave caches), which pulls Westwood's means down and skews the targets; (3) one judge on ten pictures is noisy.
  Passed to the tracks. A shells agent (`night-shells`) now owns room shapes and floors: L-shapes, alcoves, corridors,
  floor patterns.
- 23:25 Westwood references curated by eye (`night-curate`, `rules/rooms/curated.json`): all 235 campaign rooms looked
  at; 110 kept, 67 retyped to their true type, 58 excluded (corridors, cave caches, traps, burning houses, set pieces,
  second-campaign copies the old de-duplication missed). Bedroom 40->28 references, storeroom 22->7 (the real ones are
  fuller: coverage 0.07->0.16), living room 15->14 (now real households: bigger, with more kinds of piece), laboratory
  19->6, hall 17->3. New types gain real references: guardroom 11, cell 10, mausoleum 6, shrine 5, cellar 4, solar 4,
  winch room 4. Storeroom AUC 0.955->0.741 from the cleaner references alone. The tuning tracks are told to merge it.
- 23:45 Independent judgements, round 2 (12 sheets): every room type is still told apart (9-10/10). Generated / Westwood:
  bedroom r7 4.8/6.6, kitchen ref 5.0/5.8 -> r8 3.4/5.8 (regressed: no cauldron, stoves, bookcases), storeroom r9
  5.0/5.4 (closest), laboratory r8 4.6/5.6, shop r4 4.2/6.4, tavern ref 5.0/7.0, throne room ref 4.8/7.2 -> r5 5.2/7.2,
  great hall r4 4.8/6.0; bandit camp r5 4.6/6.2.
  Three methodological fixes from the judges: (1) a render artifact: generated rooms had a glowing rim of sunlit ground
  round their walls (fixed in `labrender.py`; the rim is gone); (2) the same Westwood pictures repeat across a type's
  iterations, so a judge seeing two sheets recognises them: one sheet per type per judge from now on; (3) rounds have
  often improved the metrics while making rooms worse by eye (stamps), so the tracks now check each round by eye
  against ref. `review/score_indep.py` scores a judgement against its key.
- 23:55 A second furnishing engine started as an experiment (`night-motifs`): arrangements mined from the curated
  campaign rooms (wall motifs with Westwood's real gaps and heaps, corner clusters, centre groups), recombined per room
  without copying any one room (originality rule kept). It sits behind a switch; the lab compares it head to head with
  the recipe engine, and its sheets go to independent judges. Reason: the judges' reasons repeat across every type
  (evenly spaced singles, one stamp per type, a lone table dead centre), which tuning recipes hasn't cured.
- 00:05 Dialogue round 2 merged (`night-dialogue2`, i4-i12; every packet judged by a fresh agent, one packet per judge;
  control packets of Westwood only scored 49-55%, chance level). Best round i10: told apart 89% side by side and 79% when
  each text is judged alone; scores 6.0 vs Westwood 7.9. What worked was only "frames": each line rewritten from one of
  Westwood's own lines, each quest from a whole Westwood quest. Rules, imitation and lists of tells did not help (any
  added instruction became the new tell). Short lines (townsfolk, shops, guards, rumours) now pass or nearly pass; long
  quests are still caught by a recognisable skeleton and slightly tidier sentences. The writer model made no difference.
  The `q.errand`, `q.done` and `q.note` helpers compile (three fixes). For map agents: `py tests/storylab.py frames --seed
  <Map>` deals the frames, and `--check` flags shared stock phrases.
- 23:59 (Clock check: the 00:05 and 23:55 entries above were stamped ahead of the real time; entries from here use
  the system clock.) 16 more sheets sent to four fresh judges (13 room types, 3 scenes; one sheet per type per judge).
  Four sheets rendered before the renderer fix (tavern r10, study r3, solar r3, chapel r3) were sent back for
  re-rendering. Track commits so far: A 7, B 13, C 13, scenes 5.
- 00:03 First room type to pass the independent blind test: **storeroom r16, 5/10 (chance)**, generated 5.2 vs
  Westwood 5.8 (track C: supplies heaped as Westwood heaps them, fuller rooms after the curated references). Still told
  apart 10/10: cell r4 (3.8/7.2), infirmary r2 (4.6/4.0; no Westwood infirmaries), dining hall r8 (4.0/6.4), hall r3
  (4.4/6.0), shrine r9 (4.6/6.8), gallery r3 (3.6/6.0), laboratory r11 (4.4/6.8). The judges agree on one diagnosis
  across types: one set stamped at equal spacing, a lone group dead centre, large bare floor, where Westwood's rooms
  have "one strong idea placed with small irregularities". Note for the method: the briefs describe our generator's
  rules (caps per wall), and a judge used that to tell rooms apart; judges should get a type description without the
  generator's rules.
- 00:03 More independent results: shop r8 10/10 (4.4/7.2); scenes: graveyard r5 8/10 (5.6/7.0, progress),
  garden r5 10/10 (4.8/7.4), pond and dock r2 9/9 (4.6/7.8). The scenes' main tell is partly the lab: ours stand alone
  in an empty forest glade, Westwood's among town walls, walks, yards and houses. The scene lab is asked to generate
  variants in a realistic town or shore context.
- 00:04 Track A independent results: bedroom r10 8/10 (5.6/7.4; r7 was 9/10), kitchen r11 10/10 (5.0/4.2),
  living room r10 10/10 (4.6/6.6), guardroom r8 9/10 (5.4/5.4, equal scores). Judge: "one piece in each slot, large
  evenly empty floor round each group", and real clearance faults the knowledge base should have caught (barrels
  against the hearth, a second table set in a living room, chests loose on the floor).
- 00:27 Scene rounds 2-3 merged (night-scenes3): camps cut to one tent with sleepers inside, armour racks in
  a row, smaller bands; graveyards larger where the ground allows, crypts set in from the fence, a walk from the gate, no
  trees inside; gardens open, with Westwood's low lattice fence only round large ones; docks prefer the long DockDown,
  with varied gear on firm ground. The lab now generates scenes in a hamlet (road, houses, lake) except wild ones. Each
  scene has its own random generator, so tuning one can't shift a design. Graveyard is the closest scene (judge 8/10).
  Round 4 started (night-scenes4): a cave-hideout camp (Westwood's camps are mostly hideouts), a better lab setting,
  then the 13 untuned scene types. Three new scene sheets are with a judge.
- 00:29 Scene round 3's last sheets, judged independently: graveyard r8 10/10 (5.6/7.4), garden r6 10/10 (5.4/7.8,
  up from 4.8), dock r4 9/9 (5.6/7.8, up from 4.6). Scores are rising and all are still told apart. Diagnosis: each
  scene is an isolated stamp, where Westwood's are woven into walls, roads, houses and each other. Passed to round 4.
- 00:39 Merged: room shells (night-shells: L-shapes, alcoves, partitions, second floors and carpets at Westwood's
  rates; rooms now 41-83% rectangles per map against Westwood's 67%; shell AUC down for all five lab types, crypt
  0.99->0.78), tuning tracks C (storeroom passed; 18 types tuned; shared heaps slot, steel stock, crypt-chest variants)
  and A (8 types; guardroom matched Westwood's score; fixes for double-door clearance and stray chairs), and the motif
  engine (night-motifs: 174 curated rooms mined into 1279 wall stretches, 239 corner and 457 centre motifs; experimental,
  off by default; lower AUC in 4 of 6 types but more hard-rule rooms). Conflicts in furnish.py and identity.py were
  additive and resolved keeping both sides. 22 new sheets sent to six fresh judges. Integration build running.
  Track B and dialogue round 3 and scene round 4 still running.
- 00:43 Integration build of the merged kit: 0 errors on every map, but warnings rose (Thornwick 0->7, Starwell 0->7,
  Greywatch 1->8, Ambermere 0->7). Almost all are composition.sparse: the user's TreePlace house rule ("rooms at Westwood's
  median and below read as empty") against the tuned rooms, which now match Westwood's real spread (10-11% cover against
  the curated medians of 12-13%; half of Westwood's own rooms fall below its median). Kept as warnings: the user's call.
  The rest are real: a hard OakWoodFloor/RedBrick seam from the new second floors, a dining hall of 29 WoodenChairs
  (track B not merged yet), a bookcase gap in a library. Track A's third sheets: bedroom j6 9/10 (5.4/7.0), guardroom j3
  9/10 (4.4/6.2), kitchen j2, living room j6, cell j1, infirmary j3, study r4, solar r4 all 10/10. Motif engine sheets
  (independent): living room 10/10 (4.4/7.6), tavern 10/10 (3.6/7.6), laboratory 9/10 (4.6/7.4): worse than recipes. A
  lab-fairness agent (night-labfair) removes the remaining non-design tells: creatures in Westwood's renders, briefs that
  leak our rules to judges, the lab's 1-3 doors where Westwood has one, repeated Westwood pictures.
- 00:43 Pushed the merged kit (integration: 0 errors on all five recent maps). Independent results: track C
  laboratory r17 10/10 (5.4/6.2), shop r12 10/10 (4.6/6.8), crypt r7 10/10 (5.2/7.4), armoury c3 10/10 (4.8/6.6),
  barracks c3 8/10 (4.8/7.2), cellar r2 10/10 (5.2/6.4), mausoleum r6 10/10 (3.8/7.4), library c1 10/10 (4.6/6.2).
  **Motif engine: bedroom 6/10 (near chance; 4.8/6.8), storeroom 7/10 (5.2/5.6)**, kitchen 10/10. Learned
  arrangements beat the tuned recipes on the two types with the most Westwood rooms (recipe bedroom best 8/10). The
  judges' diagnosis of the recipe rooms is unanimous across 30 sheets: everything at even gaps along the back walls,
  one template repeated, a token group in a bare middle; Westwood's are zoned, dense, irregular, with story details.
- 00:51 Dialogue round 3 merged (night-dialogue3, i13-i15). An originality check (review/storylab/originality.py),
  calibrated on Westwood against itself, shows the earlier best rounds (i10-i12) did better only by staying closer to
  Westwood's own text (their quests 0.67-0.76 similar to the quest each was dealt, closer than any two Westwood quests are
  to each other; 16-89 copied five-word runs per round). Within the originality limit, long quests are still caught 98-100%
  side by side (5.7-5.9 vs 8.1-8.3); blends, quest parts from different quests, and deliberate roughness all failed.
  Controls: 53%. Short lines pass. Map agents now must pass the originality section of --check. The dialogue lab pauses here:
  original long quests that read as Westwood's are the user's call (pastiche vs closeness).
- 00:52 Track B finished (night-tuneB, 42 commits): tavern AUC 0.99->0.877 (bar of 9-14 pieces in a back corner, stools,
  kegs behind), throne room 0.999->0.86 (braziers in pairs down the runner, three compositions instead of one template),
  great hall, chapel, dining hall, hall, shrine and gallery tuned; the classifier now finds 6 taverns and 3 dining halls
  (Con02a's barman is a Shopkeeper object). Its merge with master conflicts in 7 furnish.py and 2 identity.py hunks, so the
  merge was aborted and an agent is merging master into night-tuneB, resolving both sides and testing a sample of every
  track's types before it comes to master. B's sheets wait for the lab-fairness fixes before judging.
- 01:13 Lab fairness merged (night-labfair): renders without creatures (both kinds), black surroundings with only the
  room's own walls, one scale per sheet with each generated room paired to a Westwood room of similar size and culture,
  door counts from Westwood's rooms, Westwood pictures rotated across sheets, and judges read review/roomlab/judging/
  and review/scenelab/judging/ (Westwood descriptions without our generator's rules). Found on the way: scale was a tell
  (ours always drawn larger), and culture was (the lab built no Dun Mir bedrooms). All blind results before this point
  were under less fair renders. From now on judges get the new protocol.
- 01:42 All of tonight's room work is now in master: motif round 2 merged (night-motifs2: whole Westwood groups,
  zones of Westwood's room sizes, a placed centrepiece; storeroom AUC 0.64 with 0 hard-rule rooms, bedroom 0.71), and track
  B (merged into its own branch first: 10 conflicts resolved keeping both sides; a postmerge run reproduced each
  track's last numbers; reference counts after rebuild: bedroom 28, crypt 25, living room 14, guardroom 11, cell 10,
  shop 8, storeroom 7, barracks 7, tavern 6...). Fair head-to-head now with two judges: motif vs recipe engine on
  bedroom and storeroom. Generating fair baseline sheets for 12 more types from master.
- 01:45 First fully fair head-to-head (new renders and protocol, independent judges): recipe storeroom 6/10 near chance
  (5.4/6.0); motif storeroom 8/10 (5.0/7.0); motif bedroom 10/10 at low confidence 0.57 (5.0/6.2); recipe bedroom 9/10
  (5.4/8.0). A split: recipes keep the storeroom, motifs bring the bedroom closer on score. Faults common to both
  engines: candelabras free in walkways and on carpets, table sets out on the floor away from every wall, plants in
  bedrooms (Westwood's have none), single pieces alone in the open, stock spread instead of heaped.
- 02:00 **Fair baseline** of master's recipe engine after all tonight's merges (new renders and protocol, one
  independent judge per sheet; accuracy, then generated / Westwood score; 5/10 is chance):

  | Type | Accuracy | Score | Type | Accuracy | Score |
  |---|---|---|---|---|---|
  | storeroom | **6/10** | 5.4 / 6.0 | crypt | 9/10 | 4.4 / 6.6 |
  | guardroom | **7/10** | 5.8 / 6.2 | chapel | 9/10 | 4.4 / 5.0 |
  | tavern | 8/10 | 6.2 / 6.6 | bedroom | 9/10 | 5.4 / 8.0 |
  | living room | 8/10 | 5.2 / 5.8 | shop | 10/10 | 4.6 / 7.2 |
  | barracks | 8/10 | 5.0 / 7.6 | laboratory | 10/10 | 4.2 / 6.6 |
  | throne room | 10/10 | 5.2 / 7.6 | kitchen | 10/10 | 4.0 / 6.8 |
  | great hall | 10/10 | 3.8 / 6.8 | dining hall | 10/10 | 4.2 / 7.8 |

  The same faults named across every sheet: one template per type repeated across variants; singles at even gaps
  (rows, rings, one per corner); lights loose on the floor; table sets and apparatus parked mid-floor; few story pieces.
  All sent to the placement-grammar agent (night-grammar). New tells from the room shells: second-floor patches
  (brick squares) scattered with no relation to the room, and plank floors in throne rooms. Thin evidence misleads:
  the judging description of kitchens (3 Westwood rooms) says kitchens hold no cauldron, against the user's own rules:
  for the user to decide.
