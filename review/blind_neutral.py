"""Hands a judge a blind sheet under a neutral name, so the iteration's name ("r2-road", "g3m") does not hint at what
was changed or which engine made it.

    py review/blind_neutral.py out <iteration folder> [...]    copies each <folder>/blind/ to review/out/judge/<id>/
                                                              and prints the id for each; the judge gets that path
    py review/blind_neutral.py back                            copies every judged sheet's judge_indep.json back to
                                                              <folder>/blind/ (then score with review/score_indep.py)

The map from ids to folders is kept in review/out/judge/map.json, which a judge must not open (JUDGE.md's rule on keys
covers it).
"""
import json, os, secrets, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "out", "judge")
MAP = os.path.join(ROOT, "map.json")


def load():
    return json.load(open(MAP, encoding="utf-8")) if os.path.exists(MAP) else {}


def out(folders):
    m = load()
    for f in folders:
        src = os.path.join(os.path.abspath(f), "blind")
        sid = secrets.token_hex(4)
        dst = os.path.join(ROOT, sid)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("judge*.json", "result.json"))
        shutil.copy(os.path.join(src, "judge_template.json"), dst)
        m[sid] = os.path.abspath(f)
        print(f"{sid}  {dst}  <- {f}")
    os.makedirs(ROOT, exist_ok=True)
    json.dump(m, open(MAP, "w", encoding="utf-8"), indent=1)


def back():
    m = load()
    for sid, f in m.items():
        j = os.path.join(ROOT, sid, "judge_indep.json")
        if os.path.exists(j):
            shutil.copy(j, os.path.join(f, "blind", "judge_indep.json"))
            print(f"{sid} -> {f}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["out"]: out(sys.argv[2:])
    elif sys.argv[1:2] == ["back"]: back()
    else: print(__doc__)
