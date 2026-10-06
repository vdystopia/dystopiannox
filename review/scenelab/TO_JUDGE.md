# Sheets waiting for an independent blind judge

The tuning agent looked at these iterations' renders while tuning, so it did not judge them. A fresh judge follows
`JUDGE.md` on each sheet and writes `judge.json`; the main session then copies it to the iteration's `blind/` and runs
`py review/scenelab/blind.py score <scene> <iter>`.

**Round 6 (night-scenes6, 2026-10-06).** Each sheet is copied to a neutral folder (no iteration name in the path; the
round-5 judge had seen "r2-road"): `C:\GOG Games\Nox\dystopiannox-wt\scenes6\review\out\scenelab\_judge\round6\<scene>\`
(A.png ... J.png, sheet.png, judge_template.json). Judge only those pictures; write `judge.json` beside them. Then:

    copy review\out\scenelab\_judge\round6\<scene>\judge.json review\out\scenelab\<scene>\round6\blind\judge.json
    py review/scenelab/blind.py score <scene> round6

| Scene | Sheet (neutral folder) | Iteration | Previous independent verdict (round 5) |
|---|---|---|---|
| bandit_camp | `_judge/round6/bandit_camp/` | round6 | r9-warcamp: 8/10, 4.8 / 7.2 |
| graveyard | `_judge/round6/graveyard/` | round6 | r6-loose: 10/10, 4.4 / 7.2 |
| garden | `_judge/round6/garden/` | round6 | r5-against: 8/10, 4.8 / 7.2 |
| pond_dock | `_judge/round6/pond_dock/` | round6 | r6-lake: 9/9, 4.8 / 7.0 |
| market_stall | `_judge/round6/market_stall/` | round6 | r6-trades: 7/8, 4.0 / 6.3 |
| urchin_camp | `_judge/round6/urchin_camp/` | round6 | r5-knots: 10/10, 4.2 / 7.0 |
| shrine | `_judge/round6/shrine/` | round6 | r5-masonry: 10/10, 4.6 / 8.4 |
| ogre_camp | `_judge/round6/ogre_camp/` | round6 | r4-fewbones: 10/10, 5.2 / 7.6 |
| jail | `_judge/round6/jail/` | round6 | r3-torch: 10/10, 3.2 / 8.6 |
| well | `_judge/round6/well/` | round6 | r2-road: 9/9, 4.0 / 7.8 |

Every sheet was rendered after the fairness merge (no creatures, the ground outside the scene dark); judges read
`review/scenelab/judging/`, not the briefs. What changed is in LOG.md "Round 6". The round-5 sheets are superseded.
