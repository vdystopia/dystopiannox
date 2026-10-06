# The story lab

The dialogue and quest counterpart of the room lab: write 10 variants of a story situation, score them against
Westwood's campaign and compare them blind, fix the guide and the kit by what the judges say, and repeat until ours
cannot be told from Westwood's.

| file | what it is |
|---|---|
| `scenarios.json` | the situations, on one template map (Brackenford): a guard's barks, a bounty on beasts, an heirloom fetched start to end, rumours pointing at quests, shopkeepers' greetings, a choice between two givers, a rescue, the main quest's opening. Each has its map context (names, reward items, a gold budget), the parts a variant writes, and 5-7 Westwood units (string-table keys) to set beside ours |
| `westwood.py` | the campaign's text from `nox.csf` (read only), each line sorted by situation from its key |
| `metrics.py` | the metric judge: each line against Westwood's measured lines of its situation (length, sentence length, paging, punctuation, rare words, what it must carry), a set of lines for its voice (exclaiming, addressing the player, semicolons), and consistency (names not on the map, reward over budget, journal entries that are not orders, lines copied from the campaign) |
| `JUDGE.md` | the blind judge's protocol and its fixed JSON |
| `variants/<iter>/<scenario>.json` | the variants an agent wrote for an iteration |
| `judgements/<iter>/<scenario>.json` | the blind judge's answers |
| `RESULTS.md` | the iterations run and how the scores moved |

## Who writes the variants

The variants are written by an LLM agent and stored as data: a map's story is written by the agent that builds the
map, so the lab tests the instructions such an agent follows (`rules/DIALOGUE.md`, `rules/QUESTS.md`, the
`QuestBook` helpers in `mapgen/kit/quests.py`, `skills/nox-story-map/SKILL.md`), not a text generator. Each
iteration's writer gets only the brief (`py tests/storylab.py brief --iter NAME`), which points it at the guide; the
baseline's brief (`--baseline`) points it at what map agents read before the lab (the skill and Starwell's story).

## One iteration

```
py tests/storylab.py brief --iter i1                  # the writer's brief -> review/out/storylab/brief_i1.md
(an agent writes review/storylab/variants/i1/<scenario>.json, 10 variants each)
py tests/storylab.py all --iter i1                    # metric judge; blind packets -> review/out/storylab/<scenario>/i1/packet.md
(a fresh agent judges each packet by JUDGE.md -> review/storylab/judgements/i1/<scenario>.json)
py tests/storylab.py all --iter i1                    # the scorecards, now with the blind results
py tests/storylab.py summary                          # every scenario and iteration -> review/out/storylab/SUMMARY.md
```

Then read the judges' critiques and tells, and fix what they point at: the guide when the voice is off, the quest
patterns when the shape is, `kit/quests.py` when the kit makes the wrong thing easy. Stop when the blind accuracy is
near chance (50%) and our scores are within a point of Westwood's.

## A map's existing story

`py tests/storylab.py --check mapgen/designs/<map>.py` reads the design's story (q.say, q.errand, q.journal, q.text,
RUMOURS) without building it and scores every line by the metric judge, with the whole story's voice; it writes
`review/out/storylab/check/<map>.md`.
