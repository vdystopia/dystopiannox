# The story lab's blind judge

A protocol for an agent that has not written the texts. It tells whether our dialogue and quest text can stand beside
Westwood's Nox campaign (1999) and not be told apart.

## What the judge gets

One packet at a time: `review/out/storylab/_blind/<iter>/<id>.md` (the id is opaque), written by
`py tests/storylab.py all --iter <iter>`. It holds ten texts labelled A to J, each the lines of one quest or one place
(an offer, a reminder, the thanks when it is done, the journal entry; or three townsfolk; or three shopkeepers; or a
cross-section of one town). **Exactly five** are from Westwood's campaign and five were written for new maps. The order
is shuffled by a seed. Proper nouns are masked on both sides: `[Person]`, `[Place]`, `[Thing]`, `[Group]`. The player
is never addressed by class on either side: where Westwood's line named the class, it reads as Westwood's class-free
chapter does ("brave Adventurer", "young sir"). Page breaks inside a long speech show as ` / `.

The key (which text is which) is written apart, where the judge does not look.

## Rules for the judge

- Read only this file and the packet(s) you are given. Do not open the keys (`review/out/storylab/_keys/`), anything
  else under `review/` (variants, judgements, exemplars, briefs, scorecards), `rules/`, `skills/`, the game's string
  table, or any other file of the repository, and do not search the web. Use what you know of Nox and of game writing
  of its time.
- Judge each text on its own and then against the others: voice and register, how plainly people speak, sentence
  length and rhythm, punctuation, what a line tells the player (who, what, where, what to do, the reward), humour,
  how the journal is phrased, and the shape of the quest.
- Topic is no evidence: each new text was written for another invented town, and Westwood's come from different
  chapters. Judge the writing.
- Guess exactly five as generated.

## The score (1-10): "reads like Nox's campaign"

| score | meaning |
|---|---|
| 9-10 | could ship in Westwood's campaign unnoticed: its voice, length, punctuation, plainness and humour |
| 7-8 | Nox-like, with a slip or two (a word, a sentence too long, one turn of phrase) |
| 5-6 | competent fantasy game writing, but not Nox's voice |
| 3-4 | clearly another writer: register, length or structure is off |
| 1-2 | the wrong world, broken, or unreadable |

Score Westwood's texts by the same scale: some of Westwood's lines are weak too.

## The answer (fixed JSON)

Write one file per packet to `review/storylab/judgements/<iter>/<id>.json` (the packet's id):

```json
{
  "packet": "<id>",
  "judge": "<who judged: agent and model>",
  "items": [
    {"label": "A", "verdict": "westwood", "confidence": 4, "score": 8,
     "critique": "One or two sentences: what reads true to Nox, what gives it away."}
  ],
  "tells": ["What, across the packet, separated the new texts from Westwood's."]
}
```

- `items`: all ten, A to J. `verdict`: `"westwood"` or `"generated"`, five of each. `confidence`: 1 (a guess) to 5
  (certain). `score`: 1-10 by the table above.
- `tells`: the cues you used, general enough to fix a style guide by (not "Text C mentions a mill").

## What the lab computes

`py tests/storylab.py all --iter <iter>` reads the judgements and the keys and writes the scorecards
(`review/out/storylab/<scenario>/<iter>/scorecard.md`):

- **accuracy**: the share of the ten the judge placed right. 50% is chance; the target is near 50%.
- **ours caught**: the share of our five the judge called generated.
- **scores**: the mean 1-10 for ours and for Westwood's; the target is ours within a point of Westwood's.

`py tests/storylab.py summary` puts every scenario and iteration in one table (`review/out/storylab/SUMMARY.md`).
