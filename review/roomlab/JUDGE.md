# The blind visual judge

A protocol for a vision-capable agent: tell Westwood's rooms from ours by eye, score them, and say what is wrong.
`review/roomlab/blind.py make <type> <iter>` (run by `tests/roomlab.py`) has built the sheet; this file says how to
judge it. Judge honestly: the loop only improves if the judge catches what gives our rooms away.

## Before you look

1. Read the type's brief, `rules/rooms/<type>.md` (purpose, focal point, pieces, composition, mistakes), and the rules for
   every room in `rules/rooms/README.md` ("Rules for every room").
2. Read the user's past verdicts on rooms in `review/FEEDBACK.md` (DV5, TP1-TP3, TL, TW-8, GW-7, SW-6, SW-7, SWR): they
   are the faults the user notices.
3. Do **not** open `review/out/roomlab/<type>/<iter>/blind_key.json`, `variants.json`, `metrics.json` or the scorecard
   until you have written your answers.

## Looking

Open each picture `review/out/roomlab/<type>/<iter>/blind/A.png` ... `J.png` with the Read tool, one at a time (the
`sheet.png` overview is too small to judge by). The pictures are drawn alike on purpose: the same render, the same scale
for the type, the room cropped with its walls, the walls in front of the room half see-through as the game draws them,
everything outside the room darkened. So do not judge by:

- framing, darkness outside the room, the scale, or the room's size (ours are built 1.25 times Westwood's by the user's
  choice);
- wall or floor material alone (both come from Westwood's building styles);
- creatures or people standing in a room (Westwood's maps have monsters and NPCs in them; the lab's rooms have none);
- what lies outside the room (neighbouring rooms are dimmed in both).

Judge the room as a designed room: what is in it, where it stands, how it is spaced, whether it reads as its type.

About five of the ten are Westwood's and about five generated, but the split is not promised. When Westwood has fewer
than five rooms of the type, the key fills the Westwood side from the type's pool (kin types: a hall beside a throne
room); judge those for "made by Westwood's designers" all the same.

## What to look for (the rubric)

For each picture, ask:

1. **Purpose and identity.** Does it read at once as this type and no other? Is the focal piece there, and where the brief
   puts it (a bed headboard to a back wall; a throne facing the door down the room; the bar with its kegs; the hearth
   centred on a back wall)? Is there one group in the middle that shows the use, or is it a scatter?
2. **Walls.** Does each wall have a purpose? Are faced pieces (shelves, hearths, chests, desks, hangings) on the back
   walls (NE top right, NW top left) where the camera sees their fronts, not on the front walls (SE, SW) showing their
   backs? Are lined walls lined end to end, and only with pieces that repeat (bookcases, log shelves, workstations)?
   Do pieces sit snug and square against their walls, the right way round?
3. **Spacing.** Pieces too close (touching, overlapping, chairs jammed), or each standing alone at equal distances (the
   "evenly spaced" look the user dislikes, TP2-7)? Groups with open floor between them? A clear way in from each door?
   Nothing in front of a chest, hearth or stove?
4. **Repetition and variety.** A showpiece repeated, one kind filling the room, the same table set stamped again and
   again (TW-8: "too many of the same object")? Or a believable mix, as a designer would choose?
5. **Density for the type.** Cosy and full for private rooms, open and processional for ceremonial ones, stocked for
   stores (rules/rooms/README.md "The families").
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
