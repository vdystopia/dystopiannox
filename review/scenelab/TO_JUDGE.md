# Sheets waiting for an independent blind judge

The tuning agent looked at these iterations' renders while tuning, so it did not judge them. A fresh judge follows
`JUDGE.md` on each sheet and writes `judge.json`; the main session then copies it to the iteration's `blind/` and runs
`py review/scenelab/blind.py score <scene> <iter>`.

**Round 8 (night-scenes8, 2026-10-06).** One sheet per changed scene, iteration `round8`, drawn with the round-7
footprint framing, at `C:\GOG Games\Nox\dystopiannox-wt\scenes8\review\out\scenelab\<scene>\round8\blind\`
(A.png ... J.png, sheet.png, judge_template.json). The main session copies each to a neutral folder (no iteration name
in the path) before a judge sees it. Then, for each scene:

    copy <neutral folder>\judge.json review\out\scenelab\<scene>\round8\blind\judge.json
    py review/scenelab/blind.py score <scene> round8

| Scene | Sheet | What changed (LOG.md "Round 8") | Round 7 independent verdict |
|---|---|---|---|
| shrine | `shrine/round8/blind/` | seven Westwood structures; Westwood's wall runs and paving instead of the shrine house | 10/10, 4.8 / 7.8 |
| ogre_camp | `ogre_camp/round8/blind/` | five structures, one per Westwood fire; meat knots; things against the wall | 10/10, 4.4 / 6.0 |
| jail | `jail/round8/blind/` | corridor cell rows, straw mats, racks snug to the wall, a cave cell | 8/10, 5.4 / 6.2 |
| well | `well/round8/blind/` | the sign 50-56 px before the well, a bare well, a market well with its lamp | 9/9, 4.8 / 6.8 |
| urchin_camp | `urchin_camp/round8/blind/` | round 6's den again (renders identical to base7: a confirmation only, optional) | base7 3/10, 5.8 / 5.8 |

Pond dock, garden, graveyard: unchanged since round 7 (keep). Bandit camp and market stall: not changed this round.
The round-7 sheets (scenes7 worktree) are superseded.
