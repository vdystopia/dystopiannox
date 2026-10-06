"""Two iterations of the room lab side by side, type by type: the recipe engine against the motif engine
(kit/motifs.py), or any two iterations.

    py review/roomlab/headtohead.py <iterA> <iterB> [type ...] [--md out.md]

For each type: the classifier's AUC (Westwood against generated; lower is better, 0.5 cannot tell them apart), the
cross-type AUC, the rooms with hard-rule findings, the room score (review/roomscore.py: the share of the type's checks
a room passes, its mean over the variants and how many pass every check), the pieces per tile and the floor covered
(against Westwood's median), and the findings most rooms share. Reads each iteration's metrics.json and scores its map
again (review/roomscore.py score).
"""
import json, os, statistics, sys
import labenv as E

TYPES = ["bedroom", "storeroom", "kitchen", "living_room", "tavern", "laboratory"]


def roomscores(typ, it):
    import roomscore
    d = E.iter_dir(typ, it)
    with open(os.path.join(d, "variants.json"), encoding="utf-8") as f:
        vs = json.load(f)["variants"]
    out = []
    for mname in sorted({v["map"] for v in vs}):
        rows = {r["number"]: r for r in roomscore.score(os.path.join(d, "map", mname + ".map"))}
        for v in vs:
            if v["map"] == mname and v["number"] in rows: out.append(rows[v["number"]])
    return out


def stamps(typ, it):
    """For a motif-engine iteration: the most motifs two variants share (Jaccard of their motif ids, 0 none in common),
    the skeletons used, and the originality check's highest similarity to a stock room (kit/originality.py; 0.8 is a
    copy)."""
    import re
    d = E.iter_dir(typ, it)
    with open(os.path.join(d, "variants.json"), encoding="utf-8") as f:
        vs = json.load(f)["variants"]
    ids = [set(re.findall(r"<- ([wcg]\d+)", " ".join(v.get("motif_log") or []))) for v in vs]
    jac = [len(a & b) / max(1, len(a | b)) for i, a in enumerate(ids) for b in ids[i + 1:]]
    sk = [re.findall(r"skeleton (\S+)", " ".join(v.get("motif_log") or [])) for v in vs]
    sims = [v["originality"]["max_sim"] for v in vs if v.get("originality")]
    return dict(max_shared=round(max(jac or [0]), 2), mean_shared=round(statistics.mean(jac or [0]), 3),
                skeletons=len({s[0] for s in sk if s}), motifs=sum(len(x) for x in ids),
                max_sim=max(sims or [0]), copies=sum(1 for v in vs if v.get("originality") and not v["originality"]["ok"]))


def one(typ, it):
    d = E.iter_dir(typ, it)
    with open(os.path.join(d, "metrics.json"), encoding="utf-8") as f:
        m = json.load(f)
    rs = roomscores(typ, it)
    feats = [r["features"] for r in m["rooms"]]
    return dict(auc=m["classifier"]["auc"], fallback=m["classifier"].get("fallback"),
                cross=m["cross_classifier"].get("auc"), hard=m["rooms_with_hard"], n=len(m["rooms"]),
                hard_rules=m["hard_rules"],
                score=statistics.mean(r["score"] for r in rs) if rs else None, passed=sum(r["ok"] for r in rs),
                per_tile=statistics.median(f["per_tile"] for f in feats), cover=statistics.median(f["cover"] for f in feats),
                top=[t[0] for t in m["classifier"]["top"][:3]],
                worst=[w["example"].split(" (Westwood")[0] for w in m["worst"][:2]])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    md = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else None
    if md in args: args.remove(md)
    a, b = args[:2]
    types = args[2:] or TYPES
    import metrics
    lines = [f"| Type | Westwood rooms | AUC {a} | AUC {b} | cross {a} | cross {b} | hard-rule rooms {a} | {b} | "
             f"room score {a} | {b} | pieces/tile {a} / {b} / Westwood | cover {a} / {b} / Westwood | "
             f"gives {b} away |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for t in types:
        x, y = one(t, a), one(t, b)
        own = [r for r in metrics.westwood() if r["type"] == t]
        pool = own if len(own) >= metrics.MIN_WW else metrics.pool(t)[0]
        wpt = statistics.median(r["features"]["per_tile"] for r in pool)
        wcv = statistics.median(r["features"]["cover"] for r in pool)
        fb = " (pool)" if x["fallback"] else ""
        lines.append(f"| {t} | {len(own)} | {x['auc']}{fb} | {y['auc']}{fb} | {x['cross']} | {y['cross']} | "
                     f"{x['hard']}/{x['n']} | {y['hard']}/{y['n']} | {x['score']:.2f} ({x['passed']} pass) | "
                     f"{y['score']:.2f} ({y['passed']} pass) | {x['per_tile']:.2f} / {y['per_tile']:.2f} / {wpt:.2f} | "
                     f"{x['cover']:.3f} / {y['cover']:.3f} / {wcv:.3f} | {', '.join(y['top'])}; {'; '.join(y['worst'])} |")
        print(t, "A", json.dumps(x["hard_rules"]), "B", json.dumps(y["hard_rules"]))
        for it in (a, b):
            try: print("   ", it, "stamps:", json.dumps(stamps(t, it)))
            except (KeyError, OSError): pass
    text = "\n".join(lines) + "\n"
    print(text)
    if md:
        with open(md, "w", encoding="utf-8") as f: f.write(text)


if __name__ == "__main__":
    main()
