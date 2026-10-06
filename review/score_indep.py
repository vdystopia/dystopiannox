"""Scores independent blind judgements (judge_indep.json) against their keys (blind_key.json).

    py review/score_indep.py <iteration folder> [...]      e.g. ...\\roomlab\\bedroom\\r7

Each iteration folder holds blind_key.json and blind\\judge_indep.json (written by a fresh judge agent that saw only the
pictures). Prints per sheet: the judge's accuracy, the mean score it gave the generated and the Westwood pictures, and
its mean confidence. The main session runs the judges and this script; tuning agents never see a key before judging.
"""
import json, os, sys


def truth(entry):
    t = entry if isinstance(entry, str) else (entry.get("source") or entry.get("kind") or "")
    return "westwood" if "west" in str(t).lower() else "generated"


def score(folder):
    key = json.load(open(os.path.join(folder, "blind_key.json"), encoding="utf-8"))
    key = key.get("key", key) if isinstance(key, dict) else key
    j = json.load(open(os.path.join(folder, "blind", "judge_indep.json"), encoding="utf-8"))
    ans = j.get("answers", j.get("pictures", j)) if isinstance(j, dict) else j
    if isinstance(ans, dict):
        ans = [dict(label=k, **v) for k, v in ans.items()]
    right, gen, ww, conf = 0, [], [], []
    for a in ans:
        lab = a.get("label") or a.get("id") or a.get("picture")
        t = truth(key[lab])
        right += a["guess"] == t
        (gen if t == "generated" else ww).append(a["score"])
        conf.append(a.get("confidence", 0))
    mean = lambda v: sum(v) / len(v) if v else float("nan")
    return dict(sheet=folder, accuracy=f"{right}/{len(ans)}", generated=round(mean(gen), 1), westwood=round(mean(ww), 1),
                confidence=round(mean(conf), 2))


if __name__ == "__main__":
    for f in sys.argv[1:]:
        r = score(f)
        print(f"{r['sheet']}: accuracy {r['accuracy']}, generated {r['generated']} vs Westwood {r['westwood']}, "
              f"confidence {r['confidence']}")
