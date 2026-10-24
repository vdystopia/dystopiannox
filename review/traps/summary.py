"""The trap maps' test results in one table per map: for every station what a careful player paid in the game (the
tour along the simulator's plan), what a careless walk and run paid (the tour's straight lines, and the real-input
walk where one was made), and whether it passes our rules (rules/TRAPS.md T2, T3):

    py review/traps/summary.py <built_dir> [<built_dir> ...] > summary.md

A station passes when its careful pass costs at most 25 HP (standard) or 90 HP (hard) in the game, and a careless walk
or run costs at least a third of a 100 HP wizard (33) or drops the player into the pit or kills him. Where the game
gave no careful number, or the simulator cannot see the trap's logic, the verdict says so.
"""
import json, os, sys

CAREFUL = {"standard": 25, "hard": 90}


def load(bdir, ext):
    lab = next((f for f in os.listdir(bdir) if f.endswith(".lab.json")), None)
    if not lab: return None
    name = lab[:-len(".lab.json")]
    p = os.path.join(bdir, name + ext)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def bites(lost, outcome):
    return outcome in ("fell", "died") or (lost is not None and lost >= 33)


def judge(st, tour, rw):
    tier = st.get("tier", "standard")
    g = (tour or {}).get("game", {})
    plan = g.get("plan")
    careless = [v for k, v in g.items() if k in ("walk", "run") and v]
    if rw: careless.append((rw["lost"], "fell" if rw["outcome"] == "fell" else
                            "died" if rw["outcome"] == "died" else "passed"))
    if not plan:
        return "not toured", plan, careless
    careful_ok = plan[1] == "passed" and plan[0] <= CAREFUL.get(tier, 25)
    bite = any(bites(l, o) for l, o in careless)
    if careful_ok and bite: return "pass", plan, careless
    if not careful_ok: return f"careful pass costs {plan[0]} HP ({plan[1]})", plan, careless
    return "careless costs too little", plan, careless


def main(dirs):
    total = {}
    out = []
    for bdir in dirs:
        info = load(bdir, ".lab.json")
        if not info: continue
        tours = {r["label"]: r for r in (load(bdir, ".tour.json") or [])}
        rws = (load(bdir, ".realwalk.json") or {}).get("walk", {})
        rows, n_pass = [], 0
        for st in info["stations"]:
            v, plan, careless = judge(st, tours.get(st["label"]), rws.get(st["label"]))
            n_pass += v == "pass"
            total[v.split(" (")[0] if v.startswith("careful") else v] = total.get(v.split(" (")[0] if v.startswith("careful") else v, 0) + 1
            c = ", ".join(f"{l} {o}" for l, o in careless) or "-"
            rows.append(f"| {st['label']} {st['title']} | {st.get('tier', '')} | "
                        f"{f'{plan[0]} {plan[1]}' if plan else '-'} | {c} | {v} |")
        out += [f"### {info['name']}{': ' + info['title'] if info.get('title') else ''} "
                f"({n_pass} of {len(info['stations'])} pass)", "",
                "| Station | Tier | Careful (game) | Careless (game walk, run; real walk) | Verdict |",
                "|---|---|---|---|---|"] + rows + [""]
    head = ["Totals: " + ", ".join(f"{k}: {v}" for k, v in sorted(total.items(), key=lambda kv: -kv[1])), ""]
    print("\n".join(head + out))


if __name__ == "__main__":
    main(sys.argv[1:])
