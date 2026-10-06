# The story lab

The dialogue and quest counterpart of the room lab: write 10 variants of a story situation, score them against
Westwood's campaign and compare them blind, fix the guide and the kit by what the judges say, and repeat until ours
cannot be told from Westwood's.

| file | what it is |
|---|---|
| `scenarios.json` | the situations, on one template map (Brackenford): a guard's barks, a bounty on beasts, an heirloom fetched start to end, rumours pointing at quests, shopkeepers' greetings, a choice between two givers, a rescue, the main quest's opening. Each has its map context (names, reward items, a gold budget), the parts a variant writes, and 5-7 Westwood units (string-table keys) to set beside ours |
| `westwood.py` | the campaign's text from `nox.csf` (read only), each line sorted by situation from its key |
| `originality.py`, `originality.json` | (i13 on) every line and quest against Westwood's whole campaign: closest line by word 3-grams and edit similarity, copied 5-word runs, quest skeletons; thresholds from Westwood against itself (`py tests/storylab.py originality --iter NAME` or `--file`, and in `--check`) |
| `metrics.py` | the metric judge: each line against Westwood's measured lines of its situation (length, sentence length, paging, punctuation, rare words, what it must carry), a set of lines for its voice (exclaiming, addressing the player, semicolons), and consistency (names not on the map, reward over budget, journal entries that are not orders, lines copied from the campaign) |
| `JUDGE.md` | the blind judge's protocol and its fixed JSON |
| `WRITER.md` | the writers' brief (v4 on; v11: a Westwood quest frame for each quest, a line frame for each short line, nothing added) |
| `cards.py` | what each writer is dealt: v5-v6 a card of shapes; v7-v9 line and sentence frames; v10 on quest frames (`quest_frames_card`) and line frames (`frames_card`); `map_frames` for a map agent (`py tests/storylab.py frames --seed <Map>`) |
| `JUDGE_SOLO.md` | the solo protocol: each text judged alone, no quota (`py tests/storylab.py solo --iter NAME`) |
| `modes.json` | the phrases every writer reaches for (`py tests/storylab.py modes`), flagged by the metric judge |
| `exemplars.py`, `exemplars/<situation>.md` | 20-30 of Westwood's own lines per situation for the writers to imitate (offer, opening, reminder, completion, after, townsfolk, guard, shop, captive, journal); none of them is in a packet pool |
| `variants/<iter>/maps/<n>.json` | (i4 on) writer n's whole town: every scenario's lines, one voice |
| `variants/<iter>/<scenario>.json` | the variants of a scenario (from i4 merged from the towns: variant n is town n) |
| `judgements/<iter>/<id>.json` | the blind judge's answers, by the packet's opaque id (i0-i3: by scenario) |
| `RESULTS.md` | the iterations run and how the scores moved |

## Who writes the variants

The variants are written by LLM agents and stored as data: a map's story is written by the agent that builds the map,
so the lab tests the instructions such an agent follows (`WRITER.md` and the exemplars, `rules/DIALOGUE.md`,
`rules/QUESTS.md`, the `QuestBook` helpers in `mapgen/kit/quests.py`, `skills/nox-story-map/SKILL.md`), not a text
generator. From i4 there are **ten writers a round, one town each**: writer n writes every scenario for town n
(Brackenford, then nine kinds of map), so a scenario's ten variants come from ten writers as ten maps' stories would,
and a whole town comes from one voice. The `town` scenario is a cross-section of each town (a quest's offer, thanks
and journal, a guard, a shopkeeper, two townsfolk), set beside a cross-section of a Westwood town.

## Making the test fair (i4 on)

- **Ours five come from five writers' towns; Westwood's five are matched to them in length** (the unit nearest in
  words to each of ours, from a pool of 10-13 units of the same situation per scenario).
- **No [Class] mask:** our maps never name the player's class, so Westwood's lines that do are made class-free the
  way Westwood's own class-free chapter speaks ("young Mage" -> "young sir", "Thank you, Warrior!" -> "Thank you,
  Adventurer!"); other class words show as [Group].
- **Opaque packets:** `review/out/storylab/_blind/<iter>/<id>.md`; the judge sees neither the scenario's id nor
  whether the packet is a control.
- **The control:** `py tests/storylab.py control --iter NAME` writes, per scenario, a packet of ten of Westwood's own
  units with five falsely keyed as ours. Its accuracy is chance by construction (50%, sd 17 points a packet); it shows
  how sure a judge is when nothing is to be found and how far calling a text "generated" pulls its score down (the
  floor for "ours within a point of Westwood's").
- **Independent judges:** every packet is judged by a fresh agent that reads only `JUDGE.md` and its packets (two or
  three a judge, controls mixed in unannounced). The agent that runs the lab writes no variants and judges nothing.
- The writers never see the lines they are judged beside: the exemplars leave out every pool key.

## One iteration (i4 on)

```
py tests/storylab.py brief --iter i4                  # one brief a writer -> review/out/storylab/brief_i4_w<n>.md
(ten fresh agents, one town each -> review/storylab/variants/i4/maps/<n>.json)
py tests/storylab.py merge --iter i4                  # -> variants/i4/<scenario>.json (and the town cross-sections)
py tests/storylab.py all --iter i4                    # metric judge; blind packets -> review/out/storylab/_blind/i4/<id>.md
py tests/storylab.py control --iter i4                # the control packets, same folder
(fresh agents judge the packets by JUDGE.md -> review/storylab/judgements/i4/<id>.json, one packet a judge)
py tests/storylab.py solo --iter i4                   # (i8 on) every text alone -> review/out/storylab/_solo/i4/, judges.json
(fresh agents judge three texts each by JUDGE_SOLO.md -> review/storylab/judgements/i4/solo/<id>.json)
py tests/storylab.py all --iter i4; py tests/storylab.py summary
```

From i13 a round is the long quests only, two packets a scenario (`py tests/storylab.py originality --iter NAME` with it; RESULTS.md "The third protocol").

Then read the judges' critiques and tells and fix what they point at: `WRITER.md` and the exemplars first (what the
writers imitate), the guide when a rule is wrong, the quest patterns when the shape is, `kit/quests.py` when the kit
makes the wrong thing easy. Stop when the blind accuracy is near the control's chance level and our scores are within
half a point of Westwood's.

## A map's existing story

`py tests/storylab.py --check mapgen/designs/<map>.py` reads the design's story (q.say, q.errand, q.journal, q.text,
RUMOURS) without building it and scores every line by the metric judge, with the whole story's voice; it writes
`review/out/storylab/check/<map>.md`.
