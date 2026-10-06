# Sheets waiting for an independent blind judge

The tuning agent looked at these iterations' renders while tuning, so it did not judge them. A fresh judge follows
`JUDGE.md` on each sheet (only `blind/A.png ...`, never the key, renders or scorecard) and writes `blind/judge.json`,
then `py review/scenelab/blind.py score <scene> <iter>`. Paths are under this worktree's `review/out/scenelab/`
(night-scenes3: `C:\GOG Games\Nox\dystopiannox-wt\scenes3\review\out\scenelab\`).

| Scene | Iteration | Sheet | Previous independent verdict |
|---|---|---|---|
| graveyard | r8-own | `graveyard/r8-own/blind/` | r5-trees: 8/10, 5.6 / 7.0 |
| garden | r6-town | `garden/r6-town/blind/` | r5-household: 10/10, 4.8 / 7.4 |
| pond_dock | r4-shore | `pond_dock/r4-shore/blind/` | r2-down: 9/9, 4.6 / 7.8 |
| bandit_camp | r5-edge (judged) | | r5-edge: 10/10, 4.6 / 6.2 |

The setting changed between these and the previous sheets (a hamlet round the town scenes: README "The setting").
