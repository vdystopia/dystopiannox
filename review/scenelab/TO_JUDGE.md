# Sheets waiting for an independent blind judge

The tuning agent looked at these iterations' renders while tuning, so it did not judge them. A fresh judge follows
`JUDGE.md` on each sheet (only `blind/A.png ...`, never the key, renders or scorecard) and writes `blind/judge.json`,
then `py review/scenelab/blind.py score <scene> <iter>`. Paths are under this worktree's `review/out/scenelab/`
(night-scenes4, round 4: `C:\GOG Games\Nox\dystopiannox-wt\scenes4\review\out\scenelab\`).

| Scene | Iteration | Sheet | Previous independent verdict |
|---|---|---|---|
| bandit_camp | r9-warcamp | `bandit_camp/r9-warcamp/blind/` | r5-small (round 4, critiques in LOG round 5) |
| graveyard | r6-loose | `graveyard/r6-loose/blind/` | r5-small (round 4) |
| garden | r5-against | `garden/r5-against/blind/` | r3-far (round 4) |
| pond_dock | r6-lake | `pond_dock/r6-lake/blind/` | r4-fisher (round 4) |
| market_stall | r6-trades | `market_stall/r6-trades/blind/` | r5-under: 3.6 / 8.0 |
| urchin_camp | r5-knots | `urchin_camp/r5-knots/blind/` | r3-close (round 4) |
| shrine | r5-masonry | `shrine/r5-masonry/blind/` | r3-lights (round 4) |
| ogre_camp | r4-fewbones | `ogre_camp/r4-fewbones/blind/` | r2-hut (round 4) |
| jail | r3-torch | `jail/r3-torch/blind/` | (first sheet) |
| well | r2-road | `well/r2-road/blind/` | r1-alone (round 4: "the restraint is right") |

Every sheet was rendered after the fairness merge (no creatures, the ground outside the scene black); judges read
`review/scenelab/judging/`, not the briefs. Half the bandit camps are hideouts in a rock pocket, eight of ten urchin
camps are dens in the earth, every ogre camp stands in a swamp pocket; the town scenes stand in the hamlet (README
"The setting").

Round 5 (after the judge's round-4 critiques): the sheets above replace round 4's; what changed is in LOG.md "Round 5".
