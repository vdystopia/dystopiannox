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
   order (`baseline`, `r1-...`); the same type, n and seed always give the same map. Writes
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
| `blind.py`, `JUDGE.md` | the blind visual judge |
| `scorecard.py` | the scorecard and the iteration history (`review/out/scenelab/<scene>/iterations.json`) |
| `LOG.md` | the per-scene iteration log |

**The setting** (since 2026-10-06): a scene of the wild (labgen `WILD`: the camps, the wolf den, the quarry, the
shrine) is laid in a forest glade; every other in a hamlet's ground: a road through it, two or three houses of the kit's
generator round it with their walks to the road, a pond scene's lake on one side and the hamlet on the other.

**Fairness.** A generated scene is found on the lab map by the same signature search that finds Westwood's
(`labref.find_scenes`), its pieces grown the same way, measured by the same `metrics.features`, drawn by the same
`labrender.picture` (one window per type, the ground away from the scene dimmed). What still differs: Westwood's
scenes stand in its towns, castles and caves, ours in forest clearings; Westwood's creatures are its monsters, ours the
kit's posts (creature features are shown, not classified).

**Westwood's evidence** is from the campaign maps only (Con/War/Wiz). Some types are thin or absent there (a brazier
guard post, target barrels, woodpiles, smithy yards: 0-3 scenes); their numbers are read loosely and the brief leans on
the user's rules and the blind judge.
