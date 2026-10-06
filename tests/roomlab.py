"""The room lab's harness: one iteration of the loop for one room type (or every type), steps 1-2 of
review/roomlab/README.md and the metric judge.

    py tests/roomlab.py <type> [--n 10] [--seed S] [--iter NAME]     one type (kit/roomtypes.py TYPES: bedroom, tavern...)
    py tests/roomlab.py all [--n 10] [--seed S] [--iter NAME]        every type, then a summary table
    py tests/roomlab.py list                                         the types and their Westwood evidence

Each run:
1. generates N variants of the type (review/roomlab/labgen.py): each the main room of its own building shell, built
   and furnished by the kit, varying size (Westwood's small, typical and large), shape (square, long), doors (1-3),
   culture and building style, and seed; the map goes to review/out/roomlab/<type>/<iter>/map/;
2. renders each room as Westwood's rooms are rendered (labrender.py), to renders/NN.png, and Westwood's rooms of the
   type into the cached gallery (review/out/roomlab/_westwood/<type>/);
3. measures and judges every room against Westwood's campaign rooms of the type (metrics.py: features, percentiles,
   critiques, hard rules, the batch's classifier AUC) into metrics.json;
4. builds the blind sheet (blind.py: blind/A-J.png, the key apart in blind_key.json);
5. writes the scorecard (scorecard.py: index.html and scorecard.json) and records the iteration in
   review/out/roomlab/<type>/iterations.json, which the next iteration's scorecard compares with.

The same type, N and seed always give the same rooms (crc32 seeds, never hash()). Iteration names: letters, digits,
'-' and '_' (default "scratch"). Needs numpy and scikit-learn (py -m pip install --user numpy scikit-learn).
Never installs, never launches the game or the server: only the map editor's headless renderer.
"""
import argparse, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "review", "roomlab"))
import labenv as E   # noqa: E402  (sets the import paths)


def run(typ, n=10, seed=1, it="scratch", log=print):
    import labgen, labrender, labref, metrics, blind, scorecard
    t0 = time.time()
    d = E.iter_dir(typ, it)
    os.makedirs(d, exist_ok=True)
    name = "R" + format(E.seed_of(typ, it) & 0xFFFFFF, "06x")            # unique per (type, iteration)
    batch = labgen.generate(typ, n, seed, out_dir=os.path.join(d, "map"), name=name, log=log)
    with open(os.path.join(d, "variants.json"), "w", encoding="utf-8") as f:
        json.dump(dict(type=typ, iter=it, n=n, seed=seed, maps=[E.rel(p) for p in batch["maps"]],
                       variants=batch["variants"]), f, indent=1)
    t1 = time.time()
    gal = labref.gallery(typ, log=lambda *_: None)
    scale = gal["scale"]
    rd = os.path.join(d, "renders")
    os.makedirs(rd, exist_ok=True)
    by_map = {}
    for v in batch["variants"]: by_map.setdefault(v["map"], []).append(v)
    for mname, vs in by_map.items():
        path = os.path.join(d, "map", mname + ".map")
        m = E.MD.load(path)
        full, bare = labrender.lab_renders(path)
        rooms = {r["declared"]["number"]: r for r in E.C.find_rooms(m, max_tiles=1500) if r.get("declared")}
        for v in vs:
            r = rooms.get(v["number"])
            if not r: continue
            pic, s = labrender.picture(full, bare, r["cells"], scale)
            pic.save(os.path.join(rd, f"{v['index']:02d}.png"))
            v["render_scale"] = round(s, 3)
    t2 = time.time()
    res = metrics.judge_batch(typ, it, log=log)
    t3 = time.time()
    blind.make(typ, it)
    page = scorecard.write(typ, it)
    s = scorecard.summarise(typ, it)
    log(f"{typ} [{it}]: {len(res['rooms'])} rooms; AUC {s['auc']}{' (fallback pool)' if s['fallback'] else ''}, "
        f"cross-type AUC {s['cross_auc']}; {s['rooms_with_hard']} rooms with hard-rule findings; "
        f"Westwood evidence {s['westwood_rooms']} rooms  (build {t1 - t0:.0f}s, render {t2 - t1:.0f}s, "
        f"judge {t3 - t2:.0f}s)")
    for w in res["worst"][:4]:
        log(f"   {w['rooms']:2d} rooms: {w['example']}")
    log(f"   scorecard: {E.rel(page)}")
    return s


def summary_table(rows, it):
    lines = [f"# Room lab: iteration {it}", "",
             "| Type | Westwood rooms | AUC | Cross AUC | Blind acc. | Hard-rule rooms | Worst findings |",
             "|---|---|---|---|---|---|---|"]
    for s in rows:
        auc = "-" if s["auc"] is None else f"{s['auc']:.2f}" + (" (pool)" if s["fallback"] else "")
        acc = "-" if s.get("blind_accuracy") is None else f"{s['blind_accuracy']:.0%}"
        worst = "; ".join(w.split(" (Westwood")[0] for w in s["worst"][:2])
        lines.append(f"| {s['type']} | {s['westwood_rooms']} | {auc} | {s['cross_auc']} | {acc} | "
                     f"{s['rooms_with_hard']}/{s['rooms']} {json.dumps(s['hard_rules']) if s['hard_rules'] else ''} | {worst} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("type")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--iter", default="scratch")
    a = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", a.iter): sys.exit("--iter: letters, digits, '-' and '_' only")
    types = E.types()
    if a.type == "list":
        import metrics
        for t in types:
            n = sum(1 for r in metrics.westwood() if r["type"] == t)
            print(f"{t:12} Westwood rooms: {n}{'  (thin: compared with its pool)' if n < metrics.MIN_WW else ''}")
        return
    todo = types if a.type == "all" else [a.type]
    for t in todo:
        if t not in types: sys.exit(f"unknown type {t}; one of: {', '.join(types)}")
    rows = []
    for t in todo:
        rows.append(run(t, a.n, a.seed, a.iter))
    if len(todo) > 1:
        import scorecard
        rows = [scorecard.summarise(t, a.iter) for t in todo]
        text = summary_table(rows, a.iter)
        p = os.path.join(E.OUT, f"summary_{a.iter}.md")
        with open(p, "w", encoding="utf-8") as f: f.write(text)
        print(text)
        print(E.rel(p))


if __name__ == "__main__":
    main()
