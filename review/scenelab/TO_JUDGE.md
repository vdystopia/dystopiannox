# Sheets waiting for an independent blind judge

The tuning agent looked at these iterations' renders while tuning, so it did not judge them. A fresh judge follows
`JUDGE.md` on each sheet (only `blind/A.png ...`, never the key, renders or scorecard) and writes `blind/judge.json`,
then `py review/scenelab/blind.py score <scene> <iter>`. Paths are under this worktree's `review/out/scenelab/`
(night-scenes4, round 4: `C:\GOG Games\Nox\dystopiannox-wt\scenes4\review\out\scenelab\`).

| Scene | Iteration | Sheet | Previous independent verdict |
|---|---|---|---|
| bandit_camp | r5-small | `bandit_camp/r5-small/blind/` | r5-edge: 10/10, 4.6 / 6.2 |
| graveyard | r5-small | `graveyard/r5-small/blind/` | r8-own: 10/10, 5.6 / 7.4 |
| garden | r3-far | `garden/r3-far/blind/` | r6-town: 10/10, 5.4 / 7.8 |
| pond_dock | r4-fisher | `pond_dock/r4-fisher/blind/` | r4-shore: 9/9, 5.6 / 7.8 |
| market_stall | r5-under | `market_stall/r5-under/blind/` | (first sheet; Westwood has 3 stalls) |
| urchin_camp | r3-close | `urchin_camp/r3-close/blind/` | (first sheet) |
| shrine | r3-lights | `shrine/r3-lights/blind/` | (first sheet) |
| ogre_camp | r2-hut | `ogre_camp/r2-hut/blind/` | (first sheet; Westwood has 5 ogre fires) |
| well | r1-alone | `well/r1-alone/blind/` | (first sheet; Westwood has 4 wells) |

Every sheet was rendered after the fairness merge (no creatures, the ground outside the scene black); judges read
`review/scenelab/judging/`, not the briefs. Half the bandit camps are hideouts in a rock pocket, eight of ten urchin
camps are dens in the earth, every ogre camp stands in a swamp pocket; the town scenes stand in the hamlet (README
"The setting").
