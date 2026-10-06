# The room lab

The loop that makes generated rooms indistinguishable from Westwood's, one room type at a time. No whole maps: one
type's rooms, built by the kit's real building and furnishing path, judged against Westwood's campaign rooms of the
type by numbers and by eye.

> "1. You create 10 different variants of a given room type on a blank / template map 2. Each variant is scored and
> given feedback and compared to westwood maps 3. You fine-tune the process and algorithm based on what is good.
> 4. repeat until the generated rooms can be compared side-by-side with westwood rooms and be indistinguishable."
> (the user)

Needs numpy and scikit-learn: `py -m pip install --user numpy scikit-learn`. Never installs a map, never launches the
game or the server; the only program it starts is the map editor's headless renderer.

## One iteration

1. **Generate, render, measure, judge by numbers** (about 30-60 s a type once Westwood's gallery is cached):

       py tests/roomlab.py <type> --iter <name> [--n 10] [--seed 1]

   Types: `py tests/roomlab.py list` (kit/roomtypes.py TYPES, with Westwood's evidence for each). Name iterations in
   order (`baseline`, `it01-snug-chests`, `it02-...`); the same type, n and seed always give the same rooms, so a change
   in the numbers is your change. Keep the seed while tuning; try another seed (`--seed 2`) before calling a type done.
   Writes `review/out/roomlab/<type>/<iter>/`:
   - `index.html`: **the scorecard**: stop criteria, the comparison with the previous iteration, what gives the batch
     away, the worst findings with where to change them, every room's render with its findings, Westwood's rooms of the
     type at the same scale. `scorecard.json`: the same as data;
   - `renders/NN.png` (variant NN), `map/` (the lab map; open it in the editor to inspect), `variants.json` (each
     variant's kind, host role, building style, culture, size and shape class, seed), `metrics.json` (every feature,
     percentile, finding and hard rule);
   - `blind/`: the blind sheet (A-J.png, sheet.png, judge_template.json); `blind_key.json`: its key, kept apart.
2. **Judge by eye**: follow `review/roomlab/JUDGE.md` (look at A-J, guess, score, critique; write `blind/judge.json`),
   then `py review/roomlab/blind.py score <type> <iter>`, which reveals the key and updates the scorecard. Do this at
   least every few iterations, and always before calling a type done. A judge who built the change should still judge
   blind (do not look at the renders/ folder first).
3. **Tune** (below), then go to 1 with a new iteration name.

Everything: `py tests/roomlab.py all --iter <name>` runs every type and writes `review/out/roomlab/summary_<name>.md`.

## Stop criteria (per type)

A type is done when, on two seeds:
- the classifier's AUC (Westwood against generated, cross-validated) is **at most 0.60**;
- the blind judge's accuracy is **at most 60%**;
- the generated rooms' mean blind score is **at least Westwood's mean minus 0.5**;
- **no hard-rule findings** (the user's rules: the type's must/never/focal/caps/reads-as, statues facing walls, a
  blocked way in, overlapping pieces).

The scorecard's first table shows each against its target.

## Reading the judges

- **Findings** are worded critiques: each feature of a room outside Westwood's p10-p90 for the type (its range when
  Westwood has under 10 rooms), worst first, each with where to change it. The batch's worst findings are those most
  rooms share. "Westwood's 24 bedroom rooms of the town culture: 0-0.07" tells you what was compared.
- **What gives the batch away**: each feature's own AUC. Fix the top ones first: they are what the classifier (and
  usually the eye) uses.
- **Thin types.** Westwood's campaign has few rooms of some types (tavern 2, study 2, smithy 2, herbalist 2, great hall
  2, dining hall 3, throne room 4, chapel 1). With under 6, the type is compared with its pool (the Westwood types its
  profile names, then its family's) and every number says FALLBACK: read them loosely. For these types lean on the
  hard rules (the brief, rules/rooms/<type>.md, and the user's verdicts in review/FEEDBACK.md), the cross-type features
  (spacing, overlaps, snugness, rows, symmetry, facing, the way in, compared with all 235 Westwood rooms: the cross AUC)
  and the blind judge.
- **Template similarity** (the scorecard's last stop row; `metrics.template`): how alike the batch's ten rooms are
  (mean pairwise layout similarity: the same families on the same walls, and at the same places, mirrors counted)
  against Westwood's rooms of the type (the same mean over draws of as many of them; a thin type's with the kin rooms its
  archetypes name). Above Westwood's p90: "more alike than Westwood", one template repeated; the twins listed are pairs
  more alike than Westwood's p95 pair. The cure is the type's archetypes (`mapgen/kit/archetypes.py`, rules/rooms/README.md).
- **Culture.** A batch mixes the type's kinds in proportion to Westwood's rooms by culture (a chapel and the Land of the
  Dead's dark chapel; a barracks and the ogres' den). A room is compared with Westwood's rooms of its own culture when
  there are 6 or more, else with all of the type.

## Tuning: where to make changes

| What the judges say | Where |
|---|---|
| density: cover, open floor, pieces per tile, too sparse or too full | `mapgen/kit/roomtypes.py` the type's `cover`, `open`, `per_tile` (the furnisher fills toward cover's target) |
| what the room holds: a family too many or too few, variety, a piece that never belongs | the kind's recipe, `mapgen/kit/identity.py ROOMS[kind]` (`compose`, `fill`, may/must pieces); the profile's `must`/`never` |
| one kind repeated, a showpiece twice, a set stamped across a big room | the profile's `caps`, `free_most`; `kit/furnish.py SHOWPIECES` |
| walls: lining, snugness, the wrong wall, facing | `kit/furnish.py` (`line_wall`, `SNUG_GAP`, `FRONT_WEIGHT`, `along_variant`, `WALL_SIDE_TYPE`, `face_statues`) |
| spacing, groups, rows, symmetry, the way in, the middle group | `kit/furnish.py` placement (`DOOR_WAY_*`, `FRONT_CLEAR`, the recipe's groups and pairs) |
| the focal piece and its place | the profile's `focal`; the recipe's anchor |
| lights | `kit/furnish.py` lights |

Other agents work on the object knowledge base (`furnish.py`, `identity.py`, `rules/objects*`) and on new room types
at the same time: keep each change small, say in the commit which iteration it answers, and re-run the types it
touches. A change for one type must not break another: run `py tests/roomlab.py all --iter <name>` before committing a
shared change (`furnish.py`), and compare the summary with the last one.

Record each iteration's verdict in one line in the commit message (type, iteration, AUC, blind accuracy, what changed).

## The tools

| File | What it does |
|---|---|
| `tests/roomlab.py` | the harness: generate, render, measure, blind sheet, scorecard |
| `review/roomlab/labgen.py` | the variants: size, shape, doors (Westwood's counts for the type), culture, building style and seed; each the main room of a building shell built by `kit/building.py _build` and furnished by `kit/originality.furnish_original` |
| `review/roomlab/labrender.py` | the room pictures, drawn alike for Westwood and ours |
| `review/roomlab/labref.py` | Westwood's campaign rooms from `rules/rooms/westwood.json`: measured (`westwood_features.json`, committed) and rendered (`review/out/roomlab/_westwood/<type>/`, cached) |
| `review/roomlab/metrics.py` | the metric judge: features, comparison, critiques, hard rules, classifier |
| `review/roomlab/blind.py`, `JUDGE.md`, `judging/` | the blind visual judge, its protocol and what it reads (a judging description per type) |
| `review/roomlab/FAIRNESS.md`, `fairness.py`, `nocreatures.ps1` | the known tells that are not design and how each is handled; before and after pictures of the fixes; the creature-free map copies |
| `review/roomlab/scorecard.py` | the scorecard and the iteration history (`review/out/roomlab/<type>/iterations.json`) |
| `review/roomlab/BASELINE.md` | the baseline iteration for every type |
| `review/roomlab/MOTIFS.md`, `headtohead.py` | the experimental motif engine (`--engine motifs`: rooms composed from arrangements mined from Westwood's rooms, `kit/motifs.py`) and the head-to-head table of two iterations |

How the renders are matched (review/roomlab/FAIRNESS.md lists every known tell that is not design and how it is
handled): the editor's full render (no lighting) of a creature-free copy of the map (`nocreatures.ps1`: no monsters,
NPCs or players in either) for both; the room cropped by its own cells (the checker's room finder, for both) plus a
margin and the rise of its walls; the front walls half see-through over the floor; everything outside the room and its
own walls blacked out (no grass field, no Westwood town, no furnished neighbours); one scale per type (Westwood's
median room of the type fits the 960 x 720 canvas with room for a room 1.25 times as long), and on a blind sheet one
scale for all ten pictures; the canvas fixed; no labels. Generated variants come in the type's Westwood cultures and
the building styles of the roles that host the kind, whose walls, floors and doors are Westwood's
(rules/out/buildings.json), with Westwood's door counts for the type. The blind sheet pairs each generated room with a
Westwood room of its culture and about its size, rotating through Westwood's rooms from sheet to sheet
(`review/out/roomlab/<type>/westwood_shown.json`). Judges read `review/roomlab/judging/` (what real rooms are like,
from Westwood's evidence), never the design briefs.

Westwood reference data comes only from the campaign maps (Con, War, Wiz; `rules/rooms/westwood.json`, each room once),
with the verdicts by eye of `rules/rooms/curated.json` applied (misfiled rooms retyped, rooms not to learn from left
out; `labenv.curate`, used by `labref.index` and `metrics.westwood`).
Rebuild it after the index changes: `py review/roomlab/labref.py features`; re-render a gallery by deleting
`review/out/roomlab/_westwood/<type>/`.

## Density (2026-10-06)

The independent judges' most common fault on every type and both engines was density ("a lone piece in a huge bare
floor", "everything bunched in one corner"). `metrics.density()` measures, for Westwood's curated rooms and ours alike:
`pieces`; `reach`, the share of the floor within 2 units of a piece (furniture, rugs and clutter; not lights or
hangings); `empty_rect`, the largest bare rectangle over the floor; `zones`, the share of the room's 3 x 3 zones holding
a piece; `groups_100`, groups of pieces 1.5 units apart per 100 tiles; `offset`, the furniture's centre off the floor's
centre (as the checker's bunched rule). What separates ours (d0 batches, both engines) from Westwood's is **not the
piece count** (per-measure AUC 0.54-0.76: our rooms hold Westwood's counts) but the floor they are spread over: our
rooms are about 1.6 times Westwood's floor (the kit's scale) so `reach` falls (AUC 0.76-1.0: bedroom 0.45-0.51 against
Westwood's median 0.68, living room 0.44-0.51 against 0.80, laboratory 0.32-0.35 against 0.59, shop 0.32 against 0.59,
tavern 0.53 against 0.75), and the bare floor gathers at one end (`empty_rect` AUC 0.70-0.89, `offset` 0.69-0.85).
`reach`, `empty_rect`, `offset` and `groups_100` are now classifier features and findings; the scorecard's density
table puts the batch's median of each against Westwood's p10-p90 (`metrics.density_table`) and flags it outside.
Westwood's numbers per type: `rules/out/density.json` (`py review/roomlab/labref.py density`), which the kit's density
pass (`mapgen/kit/density.py`, both engines) fills toward.
