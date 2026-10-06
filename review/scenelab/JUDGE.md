# The blind visual judge (scenes)

A protocol for a vision-capable agent: tell Westwood's exterior scenes from ours by eye, score them, and say what is
wrong. `review/scenelab/blind.py make <scene> <iter>` (run by `tests/scenelab.py`) has built the sheet; this file says
how to judge it. Judge honestly: the loop only improves if the judge catches what gives our scenes away.

## Before you look

1. Read what every real exterior scene is like, `review/scenelab/judging/README.md`, and what a real scene of the type
   is like, `review/scenelab/judging/<scene>.md`. Both describe Westwood's own campaign scenes. Read nothing else
   about the scene or the lab: not the design briefs (`rules/scenes/`), not PROCESS.md, not `review/FEEDBACK.md`, not
   the lab's code, logs or notes (they describe how the generated scenes are made, which is not what you are judging).
2. Do **not** open `review/out/scenelab/<scene>/<iter>/blind_key.json`, `variants.json`, `metrics.json`, `renders/`,
   the scorecard, `review/out/scenelab/<scene>/westwood_shown.json` or other iterations' sheets until you have written
   your answers.

## Looking

Open each picture `review/out/scenelab/<scene>/<iter>/blind/A.png` ... with the Read tool, one at a time (the
`sheet.png` overview is too small to judge by). The pictures are drawn alike on purpose (review/roomlab/FAIRNESS.md):
the editor's render without lighting, one window and scale per scene type, only the scene's own footprint shown (its
pieces, a small margin round them and the walls it leans on; everything further out is the canvas colour), no
creatures or people in any picture. So do not judge by:

- framing, the dimming, the scale;
- the setting round the scene, which the pictures cut away on purpose (Westwood's scenes stand in its towns, castles
  and woods; the lab's in a hamlet's ground or a forest glade): do not mark a scene down for what is not in the picture
  (no square round a well, no castle round a jail). Whether a scene sits well in its town is judged on whole maps, not
  here. Judge the setting only where the scene meets it, inside the picture: a camp against a cliff, a dock and its shore, a
  garden and its house and fence, a graveyard and its fence;
- the forest's art or the ground's material alone;
- a scene you think you have seen before (the sheets rotate through Westwood's scenes).

Judge the scene as a designed place: what is in it, where each piece stands, how it is spaced, whether it reads as its
type and as a place people use.

About half the pictures are Westwood's and half generated, but the split is not promised (a type with few Westwood
scenes shows all of them).

## What to look for (the rubric)

1. **Purpose and identity.** Does it read at once as this scene (a camp, a graveyard, a garden, a dock) and as a place
   with a use? Is its anchor (the fire, the headstones, the crop beds, the dock) where it belongs?
2. **Structure.** Are there zones with a reason (the hearth, the beds, the stores), or a scatter? Or the opposite: a
   stamped template, every piece at a fixed offset, the same arrangement every time?
3. **Spacing.** Pieces touching or overlapping? Pieces on a fence line? Everything evenly spread with no stacks or
   clusters?
4. **Relation to the site.** As the judging description says real scenes of the type sit: against a cliff, wall or
   fence, by the road, out into the water, beside a house.
5. **Variety and density.** The objects real scenes of the type hold, at their density (the judging description);
   repetition of one piece.
6. **The hand of a designer.** Westwood's scenes have small irregularities with intent and use the terrain; generated
   ones give themselves away by mechanical regularity or by randomness without intent.

## Answers

For each picture write:

- `guess`: "westwood" or "generated";
- `confidence`: 0.5 (a coin toss) to 1.0 (certain);
- `score`: 1-10 for "looks like a real place made by Westwood's designers" (10: could ship in the campaign; 7: good, a
  fault or two; 5: passable, reads as the scene but clearly off; 3: wrong in ways a player notices; 1: not this scene).
  Score the Westwood pictures by the same standard: their mean is the bar ours must reach;
- `critique`: 1-4 concrete findings, each naming the piece and why ("six bedrolls in a ruler-straight row", "the dock
  runs along the bank", "crops under the fence"). Strengths count too when they decided your guess.

And `overall`: in one or two sentences, what gives the generated scenes away.

Write it as JSON to `review/out/scenelab/<scene>/<iter>/blind/judge.json`, starting from `blind/judge_template.json`:

```json
{
  "scene": "bandit_camp", "iter": "baseline", "judge": "claude-opus (vision)",
  "pictures": {
    "A": {"guess": "generated", "confidence": 0.8, "score": 4,
          "critique": ["tents and bedrolls in a ruler row behind the fire", "the same benches as every other camp"]},
    "B": {"guess": "westwood", "confidence": 0.6, "score": 7, "critique": ["cots against the cliff, a table between"]}
  },
  "overall": "the generated camps all stamp the same layout in the middle of an open glade"
}
```

## Reveal

    py review/scenelab/blind.py score <scene> <iter>

It reads `blind/judge.json`, reveals the key, writes `blind/result.json` (accuracy, the mean score of each source,
every picture's guess against the truth) and rewrites the scorecard, which compares the blind results with the stop
criteria: accuracy at most 60%, the generated scenes' mean score at least Westwood's minus 0.5.

A judge who built the change should still judge before looking at the renders. When the judge is the agent tuning the
kit (the overnight loop), say so in `judge`: its guesses are not truly blind, so weigh its scores and critiques more
than its accuracy.
