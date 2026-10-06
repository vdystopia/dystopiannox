# The scene lab

The loop that makes generated exterior scenes (camps, graveyards, gardens, ponds and docks...) indistinguishable from
Westwood's, one scene type at a time. The outdoor twin of the room lab (review/roomlab/, whose design and code it
copies). No whole maps: one type's scenes, laid by the kit's real code, judged against Westwood's campaign scenes of the
type by numbers and by eye.

> "do the same process for exterior settings - bandit camps, graveyards, gardens, ponds etc." (the user)

Needs numpy and scikit-learn: `py -m pip install --user numpy scikit-learn`. Never installs a map, never launches the
game or the server; the only program it starts is the map editor's headless renderer.

## One iteration

1. **Generate, render, measure, judge by numbers** (about 15-30 s a type once Westwood's gallery is cached):

       py tests/scenelab.py <scene> --iter <name> [--n 10] [--seed 1]

   Types: `py tests/scenelab.py list` (scenecat.py, ranked, with Westwood's evidence for each). Name iterations in
   order (`baseline`, `r1-...`); the same code, type, n and seed always give the same map, whatever the iteration's
   name (since round 6: the lab map's name, which the kit seeds its scenes' own generators from, had been drawn from the
   iteration's name, so two runs of the same code gave camps of 24 and 19 pieces). Writes
   `review/out/scenelab/<scene>/<iter>/`:
   - `index.html`: **the scorecard**: stop criteria, plain-English findings, the comparison with the previous
     iteration, what gives the batch away (each feature's own AUC), every scene's render with its findings, Westwood's
     scenes of the type drawn the same way; `scorecard.json`: the same as data;
   - `renders/NN.png`, `map/` (the lab map), `variants.json` (each variant's size, site, forest, what the kit laid),
     `metrics.json` (every feature, finding and hard rule);
   - `blind/`: the blind sheet (A-J.png, sheet.png, judge_template.json); `blind_key.json` apart.
2. **Judge by eye**: follow `review/scenelab/JUDGE.md` (look at every picture, guess, score, critique; write
   `blind/judge.json`), then `py review/scenelab/blind.py score <scene> <iter>`.
3. **Tune** the kit's scene code, then go to 1 with a new iteration name; log the round in `LOG.md`.

Everything: `py tests/scenelab.py all --iter <name>` runs every type with a recipe and writes
`review/out/scenelab/summary_<name>.md`.

## Stop criteria (per scene)

- the classifier's AUC (Westwood against generated, cross-validated) **at most 0.60**;
- the blind judge's accuracy **near chance** (at most 60%);
- the generated scenes' mean blind score **at least Westwood's mean minus 0.5**;
- **no hard-rule findings** (the checker's exterior rules round the scene: overlaps, a piece on a fence line, pickable
  lights, swarms, a dock that does not reach out, stumps by a fire, strewn bedrolls, purposeless heaps, graveyards
  without graves; a scene the kit failed to lay).

## How it works

| File | What it does |
|---|---|
| `tests/scenelab.py` | the harness: generate, judge, render, blind sheet, scorecard |
| `scenecat.py` | the scene types: each one's Westwood signature, reach and rank |
| `labref.py` | Westwood's campaign scenes: found by signature (`find_scenes`), measured (`westwood_scenes.json`, committed), rendered (`review/out/scenelab/_westwood/<scene>/`, cached) |
| `pieces.py` | what a scene is made of: pieces (not nature, not trivial ground bits), families, the scene grown from its anchor |
| `labgen.py` | the template map: ten clearings (sizes small/typical/large; sites glade, wall, road, shore; seven forests), the Planter |
| `recipes.py` | each type laid by the kit's own code: `camps.bandit_camp` + `posts.camp_posts`, `yards.plan/build`, `Village.garden`, `Waterworks.pond/dock`, the dressing's `Exterior._try_wall/_try_open` for catalogue themes |
| `metrics.py` | the metric judge: features, findings, hard rules, classifier |
| `labrender.py` | the pictures, drawn alike for Westwood and ours |
| `blind.py`, `JUDGE.md`, `judging/` | the blind visual judge, its protocol and what it reads (a judging description per scene) |
| `scorecard.py` | the scorecard and the iteration history (`review/out/scenelab/<scene>/iterations.json`) |
| `LOG.md` | the per-scene iteration log |

**The setting** (since 2026-10-06): a scene of the wild (labgen `WILD`: the bandit, ogre and urchin camps, the wolf
den, the quarry) is laid in a forest glade, or in a pocket of the rock where its recipe says (`caves`: the plots in a
pocket; `cave_wall`: CaveWall2 for the bandits' hideouts, Dirt for the urchins' dens, RootLight for the ogres' swamp;
`cave_scale`), each pocket on its own spur off a passage between the rows, so it has one mouth. Every other scene is
laid in a hamlet's ground: a road through it (cobbled in a third of the hamlets), two or three houses of the kit's
generator round it with their walks to the road, the forest paths joining the hamlet at its edges (never through its
middle); `by_road` sets the scene that many squares in from the road (the graveyard's gate toward it); a pond scene's
lake (11-14 tiles) lies on one side with the fisher's hut by the first landing; the market's store stands at the
clearing's side, its door toward the market square. Townsfolk at work (the gravedigger, the fisher, the gardener) are
clones of Westwood's townsfolk; the renders leave every creature out.

**Sites by type** (since round 6, a recipe's `site_map` turns the schedule's sites into those Westwood's scenes of the type
stand in): a **town wall** (graveyards in four clearings, jails in seven: the yard's back side Cobblestone, the wall
running on seven squares past its corners, `recipes._town_wall`); a **cliff** (four of the bandits' five open camps: a
glade walled by CaveWall2 instead of the wood, its trees kept off the rock's foot); the ogres' **swamp pocket** floored
with SwampGrass and a trodden DirtLight2 path in from the mouth to the fire (`cave_floor`, `path_in`); every urchin camp
a Dirt den. A recipe can fix a batch's archetypes in Westwood's frequencies (`GRAVE_ORDER`, `JAIL_ORDER`, `OGRE_ORDER`).

**Fairness** (review/roomlab/FAIRNESS.md lists every known tell that is not design and how it is handled). A
generated scene is found on the lab map by the same signature search that finds Westwood's (`labref.find_scenes`), its
pieces grown the same way, measured by the same `metrics.features`, drawn by the same `labrender.picture` (one window
per type; since round 7 only the scene's own footprint, its pieces plus a small margin and the walls it leans on, the
rest the canvas colour) from a creature-free copy of the map (no monsters, NPCs, players or
the kit's posts in either picture; the metrics still count creatures on the real map). The blind sheets rotate through
Westwood's scenes of the type (`review/out/scenelab/<scene>/westwood_shown.json`), and judges read
`review/scenelab/judging/` (what real scenes are like, from Westwood's evidence), never the design briefs. Westwood's
scenes stand in its towns, castles and caves, ours in a hamlet's ground or a forest glade: since round 7 the pictures cut
that setting away for both (FAIRNESS.md 6), so **the lab judges a scene's own arrangement; whether a scene sits well in
its town (a well on its square, a jail in its castle, a stall on a market) is judged on whole maps** (tests/qa.py's
pictures, the playtests), not here.

**Westwood's evidence** is from the campaign maps only (Con/War/Wiz). Some types are thin or absent there (a brazier
guard post, target barrels, woodpiles, smithy yards: 0-3 scenes); their numbers are read loosely and the brief leans on
the user's rules and the blind judge.
