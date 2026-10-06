# Story lab results (2026-10-05)

Eight scenarios, 10 variants each, written by agents (one per two to four scenarios, fresh each iteration) and judged
two ways: the metric judge (`metrics.py`, 0-10, Westwood's own units score 9.4-9.8) and a blind judge (a fresh agent
per four packets, `JUDGE.md`: 5 of ours and 5 of Westwood's, masked and shuffled, exactly five to be called ours).
`py tests/storylab.py summary` regenerates the table.

| iter | what the writers followed | metric ours | blind accuracy | blind ours | blind Westwood |
|---|---|---|---|---|---|
| i0 | the skill and Starwell's story (the map agents' practice before the lab) | 7.59 | 100% | 4.7 | 8.1 |
| i1 | `rules/DIALOGUE.md` v1 (the measured voice: lengths, "!", no semicolons, journal as orders, the five beats) | 9.06 | 100% | 6.1 | 8.2 |
| i2 | v2 (the i0-i1 tells: one template, too much said, even register, reminders as mood, rumours mostly colour) and variants spread over nine kinds of map | 9.05 | 100% | 5.9 | 7.8 |
| i3 (3 weakest) | v3 (shapes to draw from per situation, fewer particulars, no closing quips, `--` sparingly) | 9.11 | 100% | 6.1 | 8.1 |

By scenario (blind score ours / Westwood's):

| scenario | i0 | i1 | i2 | i3 |
|---|---|---|---|---|
| guard_bark | 4.6 / 8.2 | 6.2 / 8.0 | 5.6 / 8.0 | 6.2 / 7.8 |
| bounty_offer | 5.0 / 8.0 | 6.0 / 8.0 | 6.2 / 7.8 | |
| heirloom_fetch | 5.0 / 8.2 | 6.2 / 8.0 | 6.0 / 8.0 | 5.8 / 8.2 |
| rumour | 5.0 / 7.8 | 6.2 / 8.2 | 6.0 / 7.6 | 6.4 / 8.2 |
| shop_greeting | 4.0 / 8.2 | 6.0 / 8.2 | 5.6 / 8.2 | |
| two_givers | 5.0 / 8.4 | 6.0 / 8.6 | 5.8 / 7.8 | |
| rescue | 4.0 / 8.0 | 6.2 / 8.2 | 6.0 / 7.6 | |
| main_opening | 5.2 / 8.2 | 6.0 / 8.4 | 6.0 / 7.6 | |

## What it shows

- **The guide works on the surface and the surface is not enough.** v1 moved every measurable thing to Westwood's
  range (the metric judge from 7.6 to 9.1, Westwood's own 9.6) and the blind judge's score of our text from 4.7 to
  6.1. The blind judge still told every one of ours apart (27 packets, 100%), with confidence 4-5 except two calls at 3
  in i3's rumours.
- **What still gives us away** (the judges' tells, folded into `rules/DIALOGUE.md`): one template across a scenario's
  variants; too much information and too precise (counts, spots, sums repeated); every line polished and even, with a
  crafted quip at the end; dry wit where Westwood is broad, corny and melodramatic; every minor person given a comic
  line; titles where Westwood names people; standalone errands where Westwood's people talk about the chapter's story.
  Westwood's own roughness (slips, run-ons, stock civic phrases) is part of its fingerprint.
- **Part of the gap is the protocol, not the writing:** our five texts answer one scenario on one template map while
  Westwood's five come from different chapters and carry its main plot (the Captain, Hecubah, the next chapter); the
  judge knows five are ours. A control packet (ten of Westwood's, five falsely keyed) would show how far a judge that
  must pick five goes on chance; and scenarios drawn from Westwood-like chapter contexts would remove the topical tell.

## Next

- Give the writers more of the campaign to imitate per situation (20-30 lines each, by shape) rather than rules about
  it; let one writer write a whole map's lines so its sets are uneven the way a map's are.
- Run the control packet; then i4 on all scenarios with guide v3 plus the i3 tells.
- Map agents: `py tests/storylab.py --check` on the existing designs scores 6.9-8.2 (Westwood's own units 9.6): first-
  person narrative journals (11-14 a map), semicolons (15-16 a map), a third of the lines exclaiming or asking against
  Westwood's two thirds, and three times Westwood's share of rare words.

## The second protocol (i4 on)

From i4 the test was rebuilt to be fair (README "Making the test fair"): ten writers a round, one town each, so a
packet's five texts of ours come from five writers; Westwood's five matched to them in length from pools of 10-13
units per scenario; class words in Westwood's lines made class-free (no [Class] tell); opaque packet names; the
writers' exemplars disjoint from the pools; a new scenario, `town`, a cross-section of one town.

**How independent the judgements are.** Every packet from i4 on was judged by a fresh Claude Opus 5.5 subagent that
was given only `JUDGE.md` and two or three packet paths, told to read nothing else (no keys, variants, exemplars,
briefs, rules) and not to use the web. The agent that runs the lab (writes the briefs, builds packets, reads the
results) wrote no variant and judged no packet. Writers were separate fresh agents that never saw a packet or a
judgement. Judges share the writers' model, so a model-level habit can be invisible to both (or obvious to both).

### The control (i4): what a judge does when nothing is ours

Eight packets of ten Westwood units, five falsely keyed as ours, judged by four fresh judges who did not know:

| packets | accuracy | confidence (1-5) | score of texts called generated | called Westwood | all |
|---|---|---|---|---|---|
| 8 | 55% (chance by construction: 50% +- 6 for 8 packets) | 3.3 | 6.3 | 8.4 | 7.4 |

- A forced choice costs a text two points: Westwood's own lines score 6.3 when a judge has called them generated.
  "Ours within a point of Westwood's" is out of reach while the judge can tell; when it cannot, both halves average
  7.4.
- The judges invent tells on pure Westwood text, in the same words they use on ours: "too clean", "smoother, stock
  phrases", "the humour is set up", "repeat a direction across slots". Such tells are noise unless the accuracy says
  otherwise; the confidence is the better sign (3.3 here against 4-5 on ours).

### i4: writers imitate Westwood's lines (WRITER.md v4, exemplars), one writer a town

| scenario | metric ours / WW | blind acc | blind ours / WW |
|---|---|---|---|
| guard_bark | 9.21 / 9.69 | 100% | 6.4 / 9.0 |
| bounty_offer | 9.11 / 9.62 | 100% | 6.0 / 8.4 |
| heirloom_fetch | 8.20 / 9.62 | 100% | 6.2 / 8.8 |
| rumour | 9.06 / 9.71 | 100% | 6.0 / 8.4 |
| shop_greeting | 8.35 / 9.79 | 100% | 6.4 / 8.4 |
| two_givers | 8.76 / 9.47 | 100% | 6.0 / 8.6 |
| rescue | 7.86 / 9.46 | 100% | 6.0 / 8.0 |
| main_opening | 9.12 / 9.59 | 100% | 6.0 / 8.8 |
| town | 8.43 / 9.59 | 100% | 6.0 / 8.6 |
| **all** | **8.68** | **100%** | **6.1 / 8.6** |

The lines read closer to Westwood (writer 1's Brackenford: "Halt! The north gate stays shut till Halvard says
otherwise.", "Can't stop, dear, the bread's in the oven!") but every packet was still told apart at confidence 4-5,
and the reason is new: **ten writers given one brief wrote one template.** "Bah! Scorpions!" / "Dead? All of 'em? Ha!"
/ "You earned every piece"; "Psst! ... Heh, heh, heh... a deal's a deal"; "Did X send you?" / "I think they're coming
back!"; "Halt! ... [Person]'s orders"; "Pull up a stool"; "hasn't slept a wink"; four rescues of a parent's lost boy
(three named Wim). The metric judge's sameness measure saw it too (heirloom 13% of 3-grams in four or more variants).
Imitation fixed the single line; the mode of the model across writers is now the tell. The other tells: exact gold
sums where Westwood hands over items, spells, keys and passes; a joke in every line; one menace threaded through every
voice of a town; clean punctuation (Westwood: "?!", "Oh....", run-ons, missing stops); wares listed in threes;
decorative dialect spelling.

Metric judge changes (all iterations rescored): a `COMPLETED:` journal entry is judged by its objective; a six-word
phrase Westwood itself uses in two lines or more ("as a token of my appreciation") is house style, not a copy.

### i5: a card a map (WRITER.md v5, `cards.py`), the model's mode phrases measured (`modes.json`)

Each writer got a card: its map's own draw of Westwood's shapes (how each giver opens, asks and pays; what the guard,
townsfolk and keepers say; the captive; the one comic person; one rough patch) and two or three model lines a part.

| scenario | metric ours / WW | blind acc | blind ours / WW |
|---|---|---|---|
| guard_bark | 9.02 / 9.69 | 100% | 5.6 / 8.6 |
| bounty_offer | 8.90 / 9.62 | 100% | 6.2 / 8.2 |
| heirloom_fetch | 9.15 / 9.62 | 100% | 6.4 / 8.4 |
| rumour | 9.39 / 9.71 | 100% | 6.4 / 8.2 |
| shop_greeting | 8.37 / 9.79 | 100% | 5.8 / 8.0 |
| two_givers | 8.82 / 9.47 | 100% | 5.2 / 8.8 |
| rescue | 9.49 / 9.46 | 100% | 5.4 / 8.4 |
| main_opening | 9.12 / 9.59 | 100% | 6.0 / 8.0 |
| town | 8.13 / 9.59 | 100% | 6.0 / 8.4 |
| **all** | **8.93** | **100%** | **5.9 / 8.4** |

Control i5 (seven packets, mixed unannounced among the real ones): accuracy 49%, confidence 3.2, called generated
6.7 / called Westwood 8.5. With i4: 15 control packets, 52%, confidence 3.25, 6.5 / 8.45.

The one-template tell went down (the judges name fewer shared lines) but the accuracy did not move, and a new one
appeared: the card's quoted Westwood instances became the shared template ("Oh, I forgot to mention...", "The gate is
open! Hurry!"). The judges' tells now describe a *writerly* voice rather than a template: rewards with a backstory ("A
deserter left this bow behind"); directions as chains of landmarks ("south of the castle by the old mill"); tidy
cause and effect; a constructed joke a line (a "Magic and Goat Rental" shop, the keeper's unrelated sideline);
British and archaic flavour words (reeve, victualler, pilfered, splendid); every person purposeful and on-point where
Westwood's are flat, functional, redundant, unhelpful, American-cartoonish, wired to the plot's mechanics (the Captain
waits at the gate, take this key), with one speech too long and melodramatic. One judge noticed Westwood lines
repeated between a control and a real packet (pools overlap): from i6 no judge gets two packets of one round.

### i6: the plain pass (WRITER.md v6), card shapes without quoted instances; one packet a judge

| scenario | metric ours / WW | blind acc | blind ours / WW |
|---|---|---|---|
| guard_bark | 9.63 / 9.69 | 100% | 6.2 / 8.2 |
| bounty_offer | 9.21 / 9.62 | 100% | 5.6 / 8.2 |
| heirloom_fetch | 9.26 / 9.62 | 100% | 5.4 / 8.2 |
| rumour | 9.42 / 9.71 | 100% | 5.8 / 8.0 |
| shop_greeting | 8.71 / 9.79 | 80% | 6.0 / 8.0 |
| two_givers | 9.04 / 9.47 | 100% | 4.4 / 8.0 |
| rescue | 9.12 / 9.46 | 100% | 6.4 / 8.2 |
| main_opening | 9.36 / 9.59 | 100% | 5.6 / 8.4 |
| town | 8.47 / 9.59 | 100% | 6.0 / 8.6 |
| **all** | **9.14** | **98%** | **5.7 / 8.2** |

The metric judge's best round (9.14; guard 9.63 against Westwood's 9.69) and no better for the blind judge: the
first miss (one shop text, confidence 2) and lower scores. Every item of the plain pass was carried out by all ten
writers and became the new template: an "Oh, one more thing" afterthought in every guard, a one-sentence run-on
monologue as a set piece, "?!" and "Oh...." placed once each, "Deal?" / "What do you say?" endings, the same reward
(100 gold, boots) in several towns. **An instruction to add a feature is followed uniformly, and uniformity is the
tell**: Westwood's quirks fall unevenly, one chapter here, one line there. The tells otherwise repeat i5's: a persona
and a joke for everyone, the town's gimmick in every mouth, sensory scene-setting, consequences over-explained,
reminders restating atmosphere.

### i7: a Westwood frame for every line (WRITER.md v7)

Every part of every town was dealt one of Westwood's own lines (not in any pool), to be rewritten line for line.
Blind: 99% (guard 90%), ours 5.6 / Westwood 8.2. The short lines now read like Westwood's ("Truly stubborn! Off the
planks, bog rat!"), but long offers built on a frame of another situation came out with logic gaps (an offer that
starts mid-thought, thanks about things never said), and the premises behind them were mundane (wolves eat the sheep,
a bounty on bears). Westwood's tics ("heh, heh, heh", "lad") packed densely were a new tell.

### i8: frames for the short lines, exemplars and a dealt premise for the long; the solo protocol

| scenario | metric ours / WW | blind acc (side by side) | blind ours / WW | solo: ours caught | solo: WW called ours |
|---|---|---|---|---|---|
| guard_bark | 9.61 / 9.69 | **80%** | 6.4 / 7.2 | 4/5 | 0/5 |
| bounty_offer | 8.70 / 9.62 | 100% | 6.0 / 7.8 | 4/5 | 0/5 |
| heirloom_fetch | 9.11 / 9.62 | 100% | 6.0 / 8.2 | 5/5 | 1/5 |
| rumour | 9.10 / 9.71 | **80%** | 6.4 / 8.2 | **0/5** (8.2 / 8.4) | 0/5 |
| shop_greeting | 9.46 / 9.79 | **80%** | 6.2 / 7.6 | **3/5** | 0/5 |
| two_givers | 8.76 / 9.47 | 100% | 6.0 / 8.0 | 5/5 | 0/5 |
| rescue | 8.80 / 9.46 | 100% | 6.6 / 8.0 | 5/5 | 0/5 |
| main_opening | 9.08 / 9.59 | 100% | 5.8 / 7.8 | 5/5 | 0/5 |
| town | 7.98 / 9.59 | 100% | 6.0 / 8.0 | 5/5 | 0/5 |
| **all** | **8.96** | **93%** | **6.2 / 7.9** | **36/45 (80%)** | **1/45** |

**The solo protocol** (`JUDGE_SOLO.md`, `py tests/storylab.py solo`): every text of the round alone in its own file,
no quota, no side-by-side, three texts of different kinds a fresh judge. Accuracy 89%; the judges almost never take
Westwood for ours (1 of 45) and catch 80% of ours, at confidence 2.9 (side by side: 4). **Where frames wrote the
lines, ours pass**: townsfolk 0 of 5 caught alone and scored like Westwood's (8.2 / 8.4); shops 3 of 5; guards,
rumours and shops 80% side by side, the first packets below 90%. Every scenario with a long offer or thanks is still
caught, and its tells are the dealt premise turned template: every quest a comic setup with a callback in the thanks,
"X is worse than a plague!", "My X! My poor X!", "I'll make it worth your while".

### i9: sentence frames for the long lines (WRITER.md v9)

Each offer, thanks and opening got the page-and-sentence plan of a Westwood line of its kind and a Westwood sentence
frame for every sentence. Side by side 98% (rumour 80%), ours 5.5 / Westwood 8.4; solo 86% (ours caught 78%,
Westwood's taken for ours 7%). The short lines held (solo: shops 1 of 5 caught, rumours 2 of 5, guards 3 of 5) and
the long ones got worse (two givers 4.4, bounty 5.0): sentences from different speeches read as assembled, with stock
beats that do not follow, objects never introduced and a speaker who changes mid-speech.

### i10: a whole Westwood quest dealt to each quest, line frames for the short lines (WRITER.md v10)

Each quest of each town was dealt one of Westwood's own quests (from the scenario pools; a packet leaves out every
Westwood unit dealt to the writers whose texts it holds, so no text stands beside its own source; where too few were
left, the packet holds 8 texts, four and four, and says so).

| scenario | metric ours / WW | side by side: acc | ours / WW | solo: ours caught | solo: WW taken for ours |
|---|---|---|---|---|---|
| guard_bark | 9.17 / 9.69 | 100% | 5.8 / 8.0 | 2/5 | 0/5 |
| bounty_offer | 9.06 / 9.62 | 100% (8 texts) | 5.5 / 7.5 | 4/4 | 1/4 |
| heirloom_fetch | 9.44 / 9.62 | 100% (8) | 5.5 / 7.8 | 2/3 | 1/4 |
| rumour | 9.49 / 9.71 | 100% | 5.4 / 8.4 | 2/5 | 0/4 |
| shop_greeting | 9.28 / 9.79 | **60%** | 6.8 / 7.4 | 3/5 | 1/4 |
| two_givers | 8.75 / 9.47 | **90%** | 6.4 / 8.4 | **2/4** | 0/5 |
| rescue | 9.12 / 9.46 | **75%** (8) | 6.5 / 7.2 | 3/4 | 0/3 |
| main_opening | 9.19 / 9.59 | 100% | 5.8 / 7.8 | 4/4 | 0/5 |
| town | 8.08 / 9.59 | **75%** (8) | 6.5 / 8.2 | 3/4 | 0/4 |
| **all** | **9.06** | **89%** | **6.0 / 7.9** | **25/38 (66%)** | **3/38 (8%)** |

Solo: 76 texts, accuracy 79%, confidence on ours 2.7, scores ours 6.6 / Westwood 8.1. **The best round on every
blind measure**: two givers, rescues and towns (the long quests) below 100% side by side for the first time, a third
of ours passing alone. The tells left are what writers added to the frames (logistics, cause and consequence, warm
closing sentiments, comic self-introductions, pseudo-archaic ornament, an address word three times, several errands
in one briefing) and, a new one, **recognition**: judges who know Nox saw a famous quest's skeleton under new nouns
("Paraphrase of a known quest skeleton... with the nouns swapped... is a strong tell"), and two of ours written from
near-copies of one Westwood speech (Con and War versions of a line under different keys) stood side by side; from i11
a packet also leaves out near-copies by text.

### i11: quest frames, nothing added (WRITER.md v11)

The i10 method with the tells of i10 written into the brief: rewrite each frame part for part and add nothing (no
logistics, no cause and consequence, no closing sentiment, no persona, no address word the frame lacks), transpose the
trouble as well as the nouns. Packets now also leave out any Westwood unit within 0.6 (difflib) of a line dealt to
their writers. The metric judge also flags more address words than 2.5 times Westwood's rate.

| scenario | metric ours / WW | side by side: acc | ours / WW |
|---|---|---|---|
| guard_bark | 9.35 / 9.69 | 100% | 6.0 / 8.0 |
| bounty_offer | 8.99 / 9.62 | 100% | 6.4 / 8.6 |
| heirloom_fetch | 9.47 / 9.62 | 100% | 6.2 / 8.0 |
| rumour | 8.98 / 9.71 | 80% | 6.2 / 8.0 |
| shop_greeting | 9.40 / 9.79 | 80% | 6.0 / 7.6 |
| two_givers | 8.59 / 9.47 | 80% | 5.8 / 8.2 |
| rescue | 9.06 / 9.46 | 75% (8) | 6.5 / 7.5 |
| main_opening | 9.36 / 9.59 | 100% | 5.8 / 8.6 |
| town | 8.14 / 9.59 | 100% | 6.4 / 8.6 |
| **all** | **9.04** | **91%** | **6.1 / 8.1** |

Solo (39 texts, half the round): accuracy 82%, ours caught 70%, Westwood taken for ours 0%, scores 6.6 / 8.4. No
better than i10 within the noise (a round of nine packets has sd about 6 points on accuracy): saying "add nothing"
removed the logistics and sentiments, and the judges found the next thing (a tidier sentence than Westwood's, a stock
fantasy phrase, a joke that lands too neatly).

### i12: the same brief, sonnet writers

To test whether the tells belong to the writer model, i12 ran the v11 brief with Claude Sonnet writers (fresh Opus
judges as always). Side by side 90% (bounty, rumour, shops and the town 75-80%, the rest 100%), ours 6.1 / Westwood
8.1, metric 8.96: the same as Opus writers. The judges' reasons are the same kind ("built-up stakes Westwood's
briefings rarely spell out", "a forced punchline", "morale-poster lines", "same skeleton as C, swapped piece by
piece"). The tell is the rewriting, not the model.

## Where the lab stands (i0-i12)

| round | method | side by side | solo | ours / WW (blind) |
|---|---|---|---|---|
| control | ten Westwood texts, five keyed as ours | 49-55% (chance) | | called "generated" costs ~2 points |
| i0-i3 | rules (DIALOGUE.md), metric tuning | 100% | | 4.7-6.1 / 8.1 |
| i4 | exemplar imitation | 100% | | 6.1 / 8.6 |
| i5-i6 | story cards, the plain pass | 98-100% | | 5.7-5.9 / 8.2 |
| i7 | line frames for every line | 99% | | 5.6 / 8.2 |
| i8 | line frames short, premises long | 93% | 89% (townsfolk 0/5 caught) | 6.2 / 7.9 |
| i9 | sentence frames | 98% | 86% | 5.5 / 8.4 |
| **i10** | **a whole Westwood quest per quest, line frames for the rest** | **89%** | **79%** | 6.0 / 7.9 |
| i11 | i10 plus "add nothing" | 91% | 82% (half) | 6.1 / 8.1 |
| i12 | i11 with sonnet writers | 90% | | 6.1 / 8.1 |

The stop criteria (accuracy near the control's 50%, blind scores within 0.5 of Westwood's) were not met. What moved the
judges was only frames: Westwood's own lines, one dealt to each line of a map, rewritten line for line. Short lines
written that way (townsfolk, shops, guards, rumours) pass alone or nearly; long quests rewritten from a whole
Westwood quest are caught about four times in five side by side and two times in three alone. Every instruction that
asks writers to add a feature, and every list of tells, moved the judges by no more than the noise. What is left is
the gap between a rewrite and an original: a skeleton a Nox-aware judge recognises, and a sentence a little tidier
or a stake a little more spelled out than Westwood's. The default for map agents (rules/DIALOGUE.md, the skill's step 6) is
the i10/i11 method: `py tests/storylab.py frames --seed <MapName>`, rewrite, add nothing, then `--check`.

## Originality (i13 on): are our lines our own?

Frames make our text derivative by design, and a map's lines must be our own writing. `review/storylab/originality.py`
measures every line and quest against Westwood's whole campaign, with thresholds taken from Westwood against itself:
each of its 936 distinct spoken lines and journal entries against every *other* line (a reused copy, matching at 0.8
or more with class words masked, does not count), and each of its 69 quests (one speaker's offer, reminder, thanks,
afterwards, refusal) against its nearest other quest (`originality.json`). `py tests/storylab.py originality --iter
NAME` checks a round, `--file` one writer's town, and `--check <design>` now has an Originality section.

| measure | what it is | Westwood to itself (p50 / p95, by line length 1-5, 6-12, 13-25, 26+ words) | rule |
|---|---|---|---|
| 3-gram share | the share of a line's word 3-grams found in its closest Westwood line | 0 / 1.0, 0.13 / 0.50, 0.08 / 0.36, 0.05 / 0.21 | median, relative to Westwood's for the length, at most 1.0; at most 10% of lines above p95 |
| edit similarity | word-level normalised edit similarity (2M/T) to the closest Westwood line | 0.44 / 0.67, 0.36 / 0.64, 0.31 / 0.58, 0.23 / 0.46 | the same |
| copied phrase | a run of 5+ words from one Westwood line with 2+ content words, not a stock phrase Westwood uses in two lines or the genre's stock phrases (rules/DIALOGUE.md rule 7) | 210 of 936 lines share a run with another line: all stock by definition | none |
| quest skeleton | each part reduced to function words, punctuation and a slot X for every content word, compared part for part with every Westwood quest (length-weighted) | 0.36 / 0.43 (p99 0.55, max 0.59) | none above p99 (one to one); at most 10% above p95 |

The earlier rounds measured after the fact (all ten towns, every scenario, 360 lines and 60 quests a round):

| round | method | lines above p95 | relative median (3-gram / edit) | copied runs | quest skeleton median | quests above p95 / p99 |
|---|---|---|---|---|---|---|
| i4 | exemplars | 2% | 0.31 / 0.90 | 3 | 0.39 | 10 / 0 |
| i5 | cards | 1% | 0.43 / 0.89 | 7 | 0.37 | 5 / 0 |
| i7 | a line frame a line | 6% | 0.66 / 1.12 | 10 | 0.38 | 9 / 2 |
| i8 | premises | 2% | 0.46 / 0.96 | 2 | 0.37 | 2 / 0 |
| i9 | sentence frames | 3% | 0.49 / 0.96 | 4 | 0.37 | 4 / 0 |
| i10 | a Westwood quest a quest | 14% | 0.85 / 1.19 | 46 | **0.68** | 54 / 50 |
| i11 | i10, add nothing | 8% | 0.74 / 1.16 | 16 | **0.67** | 56 / 50 |
| i12 | i11, sonnet writers | 31% | 1.57 / 1.49 | 89 | **0.76** | 56 / 56 |

The check finds what the judges found: in i10-i12 the nearest Westwood quest of almost every quest is the one it was
dealt (the skeleton 0.6-0.8 to it, where no two of Westwood's quests come closer than 0.59), and the lines sit closer
to Westwood's than Westwood's sit to each other. The lab's best blind rounds were its least original. Every round
before quest frames passes on skeletons and is within Westwood's own spread on lines (a few copied runs aside).

## The third protocol (i13 on): long quests only, two packets a scenario

From i13 the rounds test the long quests alone (bounty, heirloom, two givers, rescue, main opening): ten writers, one
town each, the five quest scenarios; the writers split in two halves (the same split for every scenario), so each
scenario has **two packets**, each five writers' texts beside five Westwood units (disjoint from the other packet's
where the pool allows), each judged by a fresh judge that sees no other packet. Controls for the long scenarios
(rescue's pool is too small for one), mixed in. Solo: every text of both packets alone, three a judge. Writers check
their own town with `py tests/storylab.py originality --file` and revise what it flags.

### i13: blended quests (WRITER.md v13, `cards.blend_card`)

Each quest was dealt a **shape** (A: a Westwood quest of another kind, for the size and rhythm of each part), a
**trouble** (B: another kind and chapter, for the kind of trouble and its turn), for two in three a **payoff or
complication** (C: a third chapter), and for half a **loose spot** (one of 28 Westwood lines that are loose in one
named way: a stake half said, an aside, a slip, a line that runs on), every quest a different one. None from the
scenario's own packet pool, so packets leave nothing out.

| scenario | metric ours / WW | side by side (2 packets) | blind ours / WW |
|---|---|---|---|
| bounty_offer | 9.05 / 9.62 | 100% | 5.9 / 8.0 |
| heirloom_fetch | 9.09 / 9.62 | 100% | 5.6 / 7.9 |
| two_givers | 8.90 / 9.47 | 100% (one of 8) | 5.8 / 8.2 |
| rescue | 9.13 / 9.46 | 100% | 6.1 / 8.3 |
| main_opening | 9.00 / 9.59 | 100% | 5.8 / 8.6 |
| **all** | **9.03** | **100%** (98 texts) | **5.8 / 8.2** |

Controls (3 packets): 60%, confidence 3.1, called generated 6.3 / called Westwood 8.1. Solo (stopped after 36 texts):
100%, every one of ours caught, ours 5.9 / Westwood 8.3. Originality: **passes** (270 lines, none above Westwood's
p95, relative medians 0.30 / 0.90, no copied run; quest skeletons median 0.37 to the nearest Westwood quest, as
Westwood's own 0.36, 10 of 60 above p95, none above p99). By arm, ours scored 5.7 with two sources and 5.9 with three,
5.8 without a loose spot and 5.9 with one: no difference.

**Original, and worse.** The blends were new quests and every source added matter: the judges' tells are offers
packed with backstory, a named helper, logistics, a gift at the ask, a hand-off and local trade colour ("eel boats",
"sluice gate"), three to five pages where Westwood states the trouble, the place and the ask; thanks that set up the
next leg; a sustained crafted persona and wry or understated humour; captives given character beats; journals with
hints. The loose spots came out as performed mannerisms ("Could you... would you", "Um...", stammering ellipses,
agreement slips that "look like editing seams"). What i10's whole-quest frames gave, and the blends lost, was
Westwood's *amount*: a frame of one quest carries just as much matter as a Westwood quest does.

### i14: part frames (WRITER.md v14, `cards.part_frames_card`)

Each part of each quest (offer, refusal, reminder, thanks, afterwards) was dealt one Westwood line of its kind, each
from a different Westwood speaker and none from or near the scenario's packet pool; the brief asked for the line's
size (never more than a tenth over) and rhythm, the scenario's matter only, one trouble said once, nothing else (no
backstory, logistics, scenery, persona, aside). The loose spots were dropped.

| scenario | metric ours / WW | side by side (2 packets) | blind ours / WW |
|---|---|---|---|
| bounty_offer | 9.08 / 9.62 | 100% | 5.8 / 8.0 |
| heirloom_fetch | 9.31 / 9.62 | 100% | 5.9 / 8.3 |
| two_givers | 8.70 / 9.47 | 100% | 5.3 / 8.1 |
| rescue | 9.12 / 9.46 | 95% | 5.7 / 8.5 |
| main_opening | 9.31 / 9.59 | 100% | 5.8 / 8.6 |
| **all** | **9.10** | **99%** | **5.7 / 8.3** |

Controls (3): 53%, confidence 3.1. Solo (51 of 100 texts): 90%, ours caught 84%, Westwood taken for ours 0%, ours
5.9 / Westwood 8.3, confidence on ours 2.8. Originality: lines pass (0% above p95, relative medians 0.09 / 0.95, no
copied run), quests median 0.42 to the nearest Westwood quest (24 of 60 above Westwood's p95, none above p99): a part
frame's template carries into its part, and four writers had to rework a quest the check flagged.

The judges found the same things as in i13, less of them: crafted turns ("beat him or eat him", "my courage holds"),
folksy self-introductions ("[Person]'s the name!", "Folks call me"), invented geography for directions, outcomes that
do not follow their asks (parts from different speakers that do not join up), a reminder that "doesn't follow from
the opening, as if two speakers had been stitched", captives with character beats, journals with flourishes. A few of
ours now score 7-8 at confidence 2. The brief's "nothing more" lists cut the padding of i13 and did not reach the
voice.

### i15: whole-quest frames, then made our own (WRITER.md v15)

The i10/i11 method (a whole Westwood quest per quest, rewritten part for part, add nothing) with one step added: run
the originality check and rework what it flags (the frame's facts in another order, sentences joined or split, the ask
said another way, nothing added) until no quest follows its frame closer than Westwood's p99.

| scenario | metric ours / WW | side by side (2 packets) | blind ours / WW |
|---|---|---|---|
| bounty_offer | 9.07 / 9.62 | 100% | 5.9 / 8.1 |
| heirloom_fetch | 9.24 / 9.62 | 90% | 6.0 / 8.0 |
| two_givers | 8.76 / 9.47 | 100% (8 + 4 texts) | 5.7 / 8.4 |
| rescue | 9.07 / 9.46 | 100% | 6.2 / 8.2 |
| main_opening | 8.90 / 9.59 | 100% | 5.7 / 7.9 |
| **all** | **9.01** | **98%** (88 texts) | **5.9 / 8.1** |

Controls (3): 47%, confidence 3.1. Solo (45 texts): 98%, ours caught 96%, Westwood taken for ours 0%, ours 6.0 /
Westwood 8.3. Originality: lines pass (0% above p95, relative medians 0.34 / 0.92, no copied run), quest skeletons
median 0.42 to the nearest Westwood quest (i11: 0.67), 29 of 60 above Westwood's p95, none above p99. Tells: offers
spread over several pages with designed set-up, thanks that set up the next lead or narrate, tidy cause and effect,
captives with exposition, a shared kit of stock elements across writers ("north road", "old watchtower" from the
Brackenford template), clean restating reminders, crafted cinematic beats. With the skeleton pushed off its frame, the
whole-quest frame does no better than the blends.

## Where the lab stands (i13-i15)

| round | method | originality (lines / quests) | side by side | alone | ours / WW (side by side) |
|---|---|---|---|---|---|
| i10 | a Westwood quest per quest | fails (46 copied runs; skeletons 0.68, 54 of 60 above p95) | 89% | 79% | 6.0 / 7.9 |
| i11 | i10, add nothing | fails (16 copied runs; 0.67) | 91% | 82% | 6.1 / 8.1 |
| i13 | blends of 2-3 Westwood quests, loose spots | **passes** (0 copied; 0.37, 10 of 60 above p95) | 100% | 100% (36) | 5.8 / 8.2 |
| i14 | part frames (each part from another quest) | lines pass; quests 0.42, 24 above p95 | 99% | 90% (51) | 5.7 / 8.3 |
| i15 | whole-quest frames, reworked until the check passes | lines pass; quests 0.42, 29 above p95 | 98% | 98% (45) | 5.9 / 8.1 |
| controls i13-i15 | ten Westwood texts, five keyed as ours | | 53% (90 texts) | | |

i10-i12 numbers are the scenarios they ran (all nine, long and short); from i13 the long quests only, two packets
each. The stop criteria (side by side 65% or less, alone 60% or less, within 0.5 of Westwood) were not met.

**What the three rounds show.**

1. **The originality check measures what the judges recognised.** The best blind rounds (i10-i12) were the least
   original: their quests follow the Westwood quest they were dealt at 0.6-0.8, closer than any two of Westwood's 69
   quests come to each other (max 0.59), and they copy 16-89 five-word runs a round. Every round before quest frames,
   and every round since, sits at Westwood's own self-similarity.
2. **Within originality, nothing tried reaches the long quests.** Blends, part frames and reworked whole frames all
   land at 98-100% side by side and 90-100% alone, scored 5.7-5.9 against Westwood's 8.1-8.3. The judges' tells under
   all three are one family: more designed matter than Westwood puts in a quest (set-up over pages, logistics,
   cause and effect, next-step hooks, crafted turns, characterised captives), and less of Westwood's naive roughness.
   Whole-quest frames got below 90% only by carrying Westwood's own matter and sentence skeletons, which is the
   derivation the user's maps must not have.
3. **Untidiness cannot be dealt.** Loose spots taken from real Westwood lines, one different one per quest, came back
   as performed mannerisms ("Could you... would you", "Um...", agreement slips that "look like editing seams"): the
   same failure as i6's "add a run-on", one level down. A writer who knows a flaw is wanted writes it on purpose.
4. Short lines (townsfolk, shops, guards, rumours) were not retested; i8-i11 had them near chance, and their line
   frames pass the line-level originality check (i10: 14% of lines above Westwood's p95, i11 8%, almost all in the
   long parts).

**For map agents** (rules/DIALOGUE.md, the skill's step 6): frames as before (`frames --seed`, whole quests by
default; `blend=True` deals i13's blends), and the story must pass `--check`'s Originality section; rework what it
flags without adding. Long quests written this way will read as competent pastiche, not as Westwood's; the lab has no
method yet that does both.
