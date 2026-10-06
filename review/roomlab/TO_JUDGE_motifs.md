# Sheets to judge (motif engine, night-motifs)

Blind sheets of the motif engine's iteration `motifs` (`py tests/roomlab.py <type> --iter motifs --engine motifs`,
seed 1, n 10), one per type, for an independent judge following `review/roomlab/JUDGE.md`. The judge who built the
engine has not judged them. Each folder holds A.png-J.png, sheet.png and judge_template.json; the key is in
`blind_key.json` one level up (do not open it before judging). After judging, write `blind/judge.json` and run
`py review/roomlab/blind.py score <type> motifs` from this worktree.

| Type | Blind sheet (motif engine) | For comparison: the recipe engine, same seed (iteration `recipe`) |
|---|---|---|
| bedroom | `C:\GOG Games\Nox\dystopiannox-wt\motifs\review\out\roomlab\bedroom\motifs\blind` | `C:\GOG Games\Nox\dystopiannox-wt\motifs\review\out\roomlab\bedroom\recipe\blind` |
| storeroom | `C:\GOG Games\Nox\dystopiannox-wt\motifs\review\out\roomlab\storeroom\motifs\blind` | `C:\GOG Games\Nox\dystopiannox-wt\motifs\review\out\roomlab\storeroom\recipe\blind` |
| kitchen | `C:\GOG Games\Nox\dystopiannox-wt\motifs\review\out\roomlab\kitchen\motifs\blind` | `C:\GOG Games\Nox\dystopiannox-wt\motifs\review\out\roomlab\kitchen\recipe\blind` |
| living_room | `C:\GOG Games\Nox\dystopiannox-wt\motifs\review\out\roomlab\living_room\motifs\blind` | `C:\GOG Games\Nox\dystopiannox-wt\motifs\review\out\roomlab\living_room\recipe\blind` |
| tavern | `C:\GOG Games\Nox\dystopiannox-wt\motifs\review\out\roomlab\tavern\motifs\blind` | `C:\GOG Games\Nox\dystopiannox-wt\motifs\review\out\roomlab\tavern\recipe\blind` |
| laboratory | `C:\GOG Games\Nox\dystopiannox-wt\motifs\review\out\roomlab\laboratory\motifs\blind` | `C:\GOG Games\Nox\dystopiannox-wt\motifs\review\out\roomlab\laboratory\recipe\blind` |
