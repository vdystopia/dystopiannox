# The blind visual judge

A protocol for a vision-capable agent: tell Westwood's rooms from ours by eye, score them, and say what is wrong.
`review/roomlab/blind.py make <type> <iter>` (run by `tests/roomlab.py`) has built the sheet; this file says how to
judge it. Judge honestly: the loop only improves if the judge catches what gives our rooms away.

## Before you look

1. Read what every real room is like, `review/roomlab/judging/README.md`, and what a real room of the type is like,
   `review/roomlab/judging/<type>.md`. Both describe Westwood's own campaign rooms. Read nothing else about the type
   or the lab: not the design briefs (`rules/rooms/`), not `review/FEEDBACK.md`, not the lab's code, logs or notes
   (they describe how the generated rooms are made, which is not what you are judging).
2. Do **not** open `review/out/roomlab/<type>/<iter>/blind_key.json`, `variants.json`, `metrics.json`, `renders/`, the
   scorecard, `review/out/roomlab/<type>/westwood_shown.json` or other iterations' sheets until you have written your
   answers.

## Looking

Open each picture `review/out/roomlab/<type>/<iter>/blind/A.png` ... `J.png` with the Read tool, one at a time (the
`sheet.png` overview is too small to judge by). The pictures are drawn alike on purpose (review/roomlab/FAIRNESS.md):
the same render, one scale for every picture of the sheet, the room cropped with its walls, the walls in front of the
room half see-through as the game draws them, everything outside the room blacked out, no creatures or people in any
room, and Westwood's rooms chosen to be about the size of the generated ones. So do not judge by:

- framing, the black round the room, the scale, or the room's size;
- wall or floor material alone (both come from Westwood's building styles);
- the number of doors alone;
- a room you think you have seen before (the sheets rotate through Westwood's rooms).

Judge the room as a designed room: what is in it, where it stands, how it is spaced, whether it reads as its type.

About half the pictures are Westwood's and about half generated, but the split is not promised. A sheet usually holds
ten; when Westwood has only two to four rooms of the type, it holds that many of each (four, six or eight pictures).
Only when Westwood has a single room of the type does the key fill the Westwood side from the type's pool (kin types: a
hall beside a throne room); judge those for "made by Westwood's designers" all the same.

## What to look for (the rubric)

For each picture, ask:

1. **Purpose and identity.** Does it read at once as this type and no other? Is the focal piece there, and where a real
   room of the type has it (the judging description says where)? Does a group show the use, or is it a scatter?
2. **Walls.** Does each wall have a purpose? Are faced pieces (shelves, hearths, chests, desks, hangings) on the back
   walls (NE top right, NW top left) where the camera sees their fronts, not on the front walls (SE, SW) showing their
   backs? Are lined walls lined end to end, and only with pieces that repeat (bookcases, log shelves, workstations)?
   Do pieces sit snug and square against their walls, the right way round?
3. **Spacing.** Pieces too close (touching, overlapping, chairs jammed), or each standing alone at equal distances (the
   "evenly spaced" look)? Groups with open floor between them? A clear way in from each door?
   Nothing in front of a chest, hearth or stove?
4. **Repetition and variety.** A showpiece repeated, one kind filling the room, the same table set stamped again and
   again? Or a believable mix, as a designer would choose?
5. **Density for the type.** As the judging description says real rooms of the type are: cosy and full, open and
   processional, stocked, bare.
6. **The hand of a designer.** Westwood's rooms have small irregularities with intent (a chair pulled out, a rug a little
   off, one odd object that tells a story) and symmetry where it matters. Generated rooms tend to give themselves away
   by mechanical regularity (everything in rows, perfect spacing) or by randomness without intent (pieces scattered,
   facing oddly, a candelabra in the wrong corner).

## Answers

For each picture write:

- `guess`: "westwood" or "generated";
- `confidence`: 0.5 (a coin toss) to 1.0 (certain);
- `score`: 1-10 for "looks like a real room of this type, made by Westwood's designers" (10: could ship in the
  campaign; 7: good, a fault or two; 5: passable, reads as the type but clearly off; 3: wrong in ways a player notices;
  1: not a room of this type). Score the Westwood pictures by the same standard: their mean is the bar ours must reach;
- `critique`: 1-4 concrete findings, each naming the piece, the wall or the spacing and why (e.g. "two chests side by
  side on the SE wall show their backs", "the bed stands free in the middle, not headboard to a wall", "six identical
  round tables in a grid, no other seating"). Strengths count too when they decided your guess.

And `overall`: in one or two sentences, what gives the generated rooms away.

Write it as JSON to `review/out/roomlab/<type>/<iter>/blind/judge.json`, starting from `blind/judge_template.json`:

```json
{
  "type": "bedroom", "iter": "baseline", "judge": "claude-opus (vision)",
  "pictures": {
    "A": {"guess": "generated", "confidence": 0.8, "score": 4,
          "critique": ["two rugs and a table crowd the middle", "the bookcase run stops short of the corner"]},
    "B": {"guess": "westwood", "confidence": 0.6, "score": 7, "critique": ["bed headboard to the NE wall, chest at its foot"]}
  },
  "overall": "the generated rooms carry more kinds of object and a table set in the middle of every bedroom"
}
```

## Reveal

    py review/roomlab/blind.py score <type> <iter>

It reads `blind/judge.json`, reveals the key, writes `blind/result.json` (accuracy, the mean score of each source, every
picture's guess against the truth) and rewrites the scorecard (`index.html`, `scorecard.json`), which compares the blind
results with the stop criteria: accuracy at most 60%, the generated rooms' mean score at least Westwood's minus 0.5.

Then read the critiques of the pictures you got right with confidence: those are the faults to fix first (README.md,
"Tuning").
