# Sheets waiting for an independent blind judge

The tuning agent looked at these iterations' renders while tuning, so it did not judge them. A fresh judge follows
`JUDGE.md` on each sheet (only `blind/A.png ...`, never the key, renders or scorecard) and writes `blind/judge.json`,
then `py review/scenelab/blind.py score <scene> <iter>`. Paths are under this worktree's `review/out/scenelab/`
(night-scenes3: `C:\GOG Games\Nox\dystopiannox-wt\scenes3\review\out\scenelab\`).

| Scene | Iteration | Sheet | Previous independent verdict |
|---|---|---|---|
| bandit_camp | r5-edge | `bandit_camp/r5-edge/blind/` | r4-irregular: 10/10, 5.2 / 6.8 |
| graveyard | r5-trees | `graveyard/r5-trees/blind/` | r3-spaced: 10/10, 4.2 / 7.4 |
