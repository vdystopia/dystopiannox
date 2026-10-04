"""Scores the buildings of a building lab map (mapgen/designs/buildinglab.py writes <map>.buildings.json beside it):
- each room's floor against Westwood's sizes for its kind (validate/baseline.json room_kinds: below its 5th
  percentile is small; above its 95th is big, which the bigger scale allows);
- rooms that cannot be reached from the entrance;
- the checker's errors and warnings inside the building;
- the share of its rooms that pass review/roomscore.py.

    py review/buildingscore.py mapgen/out/buildinglab/BldLab.map
"""
import json, os, sys
REPO = os.path.dirname(os.path.abspath(__file__)) + "/.."
sys.path.insert(0, os.path.join(REPO, "validate")); sys.path.insert(0, os.path.join(REPO, "mapgen")); sys.path.insert(0, os.path.join(REPO, "review"))
import validate as V
import roomscore as RS
from kit.identity import WESTWOOD_KIND


def score(map_path):
    meta = json.load(open(os.path.splitext(map_path)[0] + ".buildings.json", encoding="utf-8"))
    base = V.baseline().get("room_kinds", {})
    _, findings, _ = V.validate(map_path)
    rooms = RS.score(map_path)
    out = []
    for b in meta:
        x0, y0, x1, y1 = b["box"]
        inside = lambda f: f.get("x") is not None and x0 <= f["x"] / 23 <= x1 and y0 <= f["y"] / 23 <= y1
        errs = [f for f in findings if f["severity"] == "error" and inside(f)]
        warns = [f for f in findings if f["severity"] == "warning" and inside(f)]
        notes = []
        for r in b["rooms"]:
            k = base.get(WESTWOOD_KIND.get(r["kind"], r["kind"])) or {}
            lo, hi = (k.get("tiles") or [0, 10 ** 6])
            if r["tiles"] < lo: notes.append(f"{r['kind']} small ({r['tiles']} < {lo:.0f})")
            elif r["tiles"] > hi: notes.append(f"{r['kind']} big ({r['tiles']} > {hi:.0f})")
        mine = [r for r in rooms if r["purpose"].startswith(b["role"] + " ")]
        passed = sum(r["ok"] for r in mine)
        ok = not errs and not b["unreachable"] and not any("small" in n for n in notes) and passed == len(mine)
        out.append(dict(role=b["role"], style=b["style"], shape=b["shape"], units=b["units"], footprint=b["footprint"],
                        rooms=len(b["rooms"]), entrances=b["entrances"], unreachable=len(b["unreachable"]), errors=len(errs),
                        warnings=len(warns), notes=notes, rooms_pass=f"{passed}/{len(mine)}", ok=ok))
    return out


def report(map_path, rows):
    lines = [f"# Building scores: {os.path.basename(map_path)}", "",
             f"{sum(r['ok'] for r in rows)} of {len(rows)} buildings pass (no errors, every room reachable, no room small "
             f"for its kind, every room passing roomscore).", "",
             "| Role | Style | Shape | Units | Tiles | Rooms | Rooms pass | Entrances | Unreachable | Errors | Warnings | Notes |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['role']}{'' if r['ok'] else ' **x**'} | {r['style']} | {r['shape']} | {r['units'][0]}x{r['units'][1]} | "
                     f"{r['footprint']} | {r['rooms']} | {r['rooms_pass']} | {r['entrances']} | {r['unreachable']} | "
                     f"{r['errors']} | {r['warnings']} | {'; '.join(r['notes'])} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    p = sys.argv[1]
    rows = score(p)
    text = report(p, rows)
    od = os.path.join(REPO, "review", "out", os.path.splitext(os.path.basename(p))[0])
    os.makedirs(od, exist_ok=True)
    open(os.path.join(od, "buildingscore.md"), "w", encoding="utf-8").write(text)
    print(text)
