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
