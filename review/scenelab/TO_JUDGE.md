# Sheets waiting for an independent blind judge

The tuning agent looked at these iterations' renders while tuning, so it did not judge them. A fresh judge follows
`JUDGE.md` on each sheet and writes `judge.json`; the main session then copies it to the iteration's `blind/` and runs
`py review/scenelab/blind.py score <scene> <iter>`.

**Round 7 (night-scenes7, 2026-10-06).** Two sheets per scene, each in a neutral folder (no iteration name in the path):
`C:\GOG Games\Nox\dystopiannox-wt\scenes7\review\out\scenelab\_judge\round7\<K or Q>\<scene>\` (A.png ... J.png,
sheet.png, judge_template.json). Judge only those pictures; write `judge.json` beside them. Both sets are drawn with the
round-7 framing (only the scene's own footprint and the walls it leans on, the rest the canvas colour:
review/roomlab/FAIRNESS.md 6), so a judge sees no town round either kind of scene; JUDGE.md now says not to mark a
scene down for what the picture cuts away.

Key for the main session (do not give it to the judges): **K = `base7`**, round 6's kit under the new framing (the
"before", which separates the framing change from the kit change); **Q = `round7`**, round 7's kit. The bandit camp's
kit did not change: its K and Q sheets are two samples of the same code. Then, for each scene:

    copy review\out\scenelab\_judge\round7\K\<scene>\judge.json review\out\scenelab\<scene>\base7\blind\judge.json
    py review/scenelab/blind.py score <scene> base7
    copy review\out\scenelab\_judge\round7\Q\<scene>\judge.json review\out\scenelab\<scene>\round7\blind\judge.json
    py review/scenelab/blind.py score <scene> round7

| Scene | Before (K: base7) | After (Q: round7) | Round 6 independent verdict |
|---|---|---|---|
| graveyard | `_judge/round7/K/graveyard/` | `_judge/round7/Q/graveyard/` | 10/10, 4.4 / 7.6 |
| jail | `_judge/round7/K/jail/` | `_judge/round7/Q/jail/` | 10/10, 4.4 / 8.0 |
| pond_dock | `_judge/round7/K/pond_dock/` | `_judge/round7/Q/pond_dock/` | 9/9, 3.8 / 7.2 |
| garden | `_judge/round7/K/garden/` | `_judge/round7/Q/garden/` | 9/10, 4.0 / 7.0 |
| well | `_judge/round7/K/well/` | `_judge/round7/Q/well/` | 9/9, 5.4 / 7.8 |
| ogre_camp | `_judge/round7/K/ogre_camp/` | `_judge/round7/Q/ogre_camp/` | 8/10, 4.8 / 6.4 |
| shrine | `_judge/round7/K/shrine/` | `_judge/round7/Q/shrine/` | 10/10, 4.6 / 7.6 |
| market_stall | `_judge/round7/K/market_stall/` | `_judge/round7/Q/market_stall/` | 7/8, 3.4 / 6.3 |
| urchin_camp | `_judge/round7/K/urchin_camp/` | `_judge/round7/Q/urchin_camp/` | 10/10, 3.6 / 8.4 |
| bandit_camp | `_judge/round7/K/bandit_camp/` | `_judge/round7/Q/bandit_camp/` | 6/10, 5.6 / 6.4 |

What changed is in LOG.md "Round 7". The round-6 sheets (scenes6 worktree) are superseded.
