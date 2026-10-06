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
