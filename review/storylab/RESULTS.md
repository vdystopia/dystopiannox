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
