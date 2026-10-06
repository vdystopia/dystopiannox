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
