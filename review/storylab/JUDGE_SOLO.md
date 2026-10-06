# The story lab's solo judge

A protocol for an agent that has not written the texts. Each file you are given holds **one** text: the lines of one
quest or one place in a Nox single-player map. Each is either from Westwood's Nox campaign (1999) or was written for
a new map. **The files are independent**: any number of them, all or none, may be from either source; do not balance
your answers. Proper nouns are masked: `[Person]`, `[Place]`, `[Thing]`, `[Group]`. The player is never addressed by
class. Page breaks inside a long speech show as ` / `.

## Rules

- Read only this file and the text files you are given. Do not open any other file of the repository, do not list
  folders, do not use the web. Use what you know of Nox and of game writing of its time.
- Judge each text on its own: voice and register, plainness, sentence length and rhythm, punctuation, what it tells
  the player, humour, the journal's phrasing, the shape of the quest.

## The answer

One JSON file per text, `review/storylab/judgements/<iter>/solo/<id>.json` (the text's id), written with the Write
tool:

```json
{"text": "<id>", "judge": "<agent and model>", "verdict": "westwood", "confidence": 3, "score": 7,
 "critique": "One or two sentences: what reads true to Nox, what gives it away."}
```

`verdict`: `"westwood"` or `"generated"`; `confidence` 1 (a guess) to 5 (certain); `score` 1-10, "reads like Nox's
campaign" (9-10 could ship unnoticed; 7-8 Nox-like with a slip; 5-6 competent but not Nox's voice; 3-4 clearly
another writer; 1-2 broken).
