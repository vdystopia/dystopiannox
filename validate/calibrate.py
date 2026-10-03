"""Calibrates the checks on Westwood's single-player maps and writes validate/baseline.json.

The baseline holds the ranges warnings compare against (5th..95th percentile over Westwood's
layouts, each layout counted once), Westwood's exact kit step offsets, and per-room-kind size and
furniture ranges. It also prints how often each check fires on Westwood's own maps: errors should be
(close to) zero there, otherwise the check is miscalibrated.

Run: py validate/calibrate.py            (needs corpus/out/json from corpus/build_corpus.py)
"""
import collections, json, os, sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mapdata as md
import checks as C

BASELINE = os.path.join(HERE, "baseline.json")


def wq(pairs, ps=(5, 10, 25, 50, 75, 90, 95)):
    """Weighted percentiles of (value, weight) pairs."""
    pairs = sorted(p for p in pairs if p[0] is not None)
    if not pairs: return None
    tot = sum(w for _, w in pairs); out = {}
    for p in ps:
        acc, target = 0, tot * p / 100
        for v, w in pairs:
            acc += w
            if acc >= target: out[f"p{p}"] = round(v, 3); break
        else:
            out[f"p{p}"] = round(pairs[-1][0], 3)
    return out


def kit_observations(name):
    """Offsets Westwood uses between neighbouring kit pieces, and from front to back pieces."""
    m = md.load(md.corpus_json(name))
    steps, backs = collections.defaultdict(set), collections.defaultdict(set)
    for kit, fronts, bks in C.kit_pieces(m):
        for o in fronts:
            p = C.nearest_piece(o, fronts)
            if p: steps[kit].add((round(p["x"] - o["x"]), round(p["y"] - o["y"])))
        for b in bks:
            f = C.nearest_piece(b, fronts, 100)
            if f: backs[kit].add((round(b["x"] - f["x"]), round(b["y"] - f["y"])))
    return steps, backs


def kit_steps(pool, maps):
    """Allowed offsets per kit: every offset seen in Westwood's maps, plus the generator's own table."""
    sys.path.insert(0, os.path.join(md.REPO, "mapgen"))
    from kit.water import KIT_STEPS
    steps, back = collections.defaultdict(set), collections.defaultdict(set)
    for s, b in pool.map(kit_observations, maps):
        for k, v in s.items(): steps[k] |= v
        for k, v in b.items(): back[k] |= v
    for kit, st in KIT_STEPS.items():
        for key in ("first", "mid", "last"):
            if st.get(key):
                steps[kit].add(tuple(st[key])); steps[kit].add((-st[key][0], -st[key][1]))
        if st.get("back"): back[kit].add(tuple(st["back"]))
    return {k: sorted(v) for k, v in steps.items()}, {k: sorted(v) for k, v in back.items()}


def one(args):
    name, base = args
    m = md.load(md.corpus_json(name))
    findings, ctx = C.run_all(m, base)
    mt = next(f["metrics"] for f in findings if f.get("metrics"))
    rooms = [(C.room_profile(r), r["tiles"]) for r in C.find_rooms(m)]
    sight_sizes = [len(g) for g in C.clusters(ctx.sight_leaks - ctx.walk_leaks, 3)]
    return name, [(f["check"], f["severity"], f["msg"][:90], f["x"], f["y"]) for f in findings if f["severity"] != "info"], \
        mt, rooms, sight_sizes


def main():
    maps = md.sp_corpus_maps()
    weight = dict(maps)
    with ProcessPoolExecutor(6) as pool:
        steps, back = kit_steps(pool, [n for n, _ in maps])
        base = dict(kit_steps=steps, kit_back=back)
        if os.path.exists(BASELINE) and "--fresh" not in sys.argv:
            with open(BASELINE) as f: base.update({k: v for k, v in json.load(f).items() if k not in base})
        results = list(pool.map(one, [(n, base) for n, _ in maps]))
    fired = collections.defaultdict(lambda: collections.Counter())
    examples = collections.defaultdict(list)
    met = collections.defaultdict(list)
    met_env = collections.defaultdict(list)
    ENV = {n: r["type"] for n, r in md.rules("environments")["maps"].items()}
    kinds = collections.defaultdict(lambda: dict(f=[], t=[]))
    sight = []
    for name, finds, mt, rooms, sight_sizes in results:
        w = weight[name]
        for chk, sev, msg, x, y in finds:
            fired[(chk, sev)][name] += 1
            if len(examples[(chk, sev)]) < 6: examples[(chk, sev)].append((name, msg, x, y))
        for k, v in mt.items():
            met[k].append((v, w)); met_env[(ENV.get(name), k)].append((v, w))
        for (kind, furniture), tiles in rooms:
            kinds[kind]["f"].append((100 * furniture / max(1, tiles), w)); kinds[kind]["t"].append((tiles, w))
            kinds[kind].setdefault("s", set()).add((tiles, furniture))
        sight += [(s, w) for s in sight_sizes]
    out = dict(base)
    out["metrics"] = {k: wq(v) for k, v in met.items()}
    out["metrics_by_env"] = collections.defaultdict(dict)
    for (env, k), v in met_env.items():
        if env and len(v) >= 4: out["metrics_by_env"][env][k] = wq(v)
    out["room_kinds"] = {}
    for kind, d in kinds.items():
        fq, tq = wq(d["f"]), wq(d["t"])
        out["room_kinds"][kind] = dict(n=len(d["t"]), furniture_per100=[fq["p5"], fq["p95"]], tiles=[tq["p5"], tq["p95"]],
                                       samples=sorted(d.get("s", ())))   # (tiles, furniture) per distinct room
    out["sight_leak_cell_sizes"] = wq(sight) if sight else None
    out.setdefault("sight_leak_cells", 0)
    with open(BASELINE, "w") as f: json.dump(out, f, indent=1, sort_keys=True)
    print(f"Westwood single-player maps checked: {len(results)}  (baseline written to {BASELINE})\n")
    print("Findings on Westwood's own maps (check / severity: maps affected, total findings):")
    for (chk, sev), per_map in sorted(fired.items()):
        print(f"  {chk:13s} {sev:8s} {len(per_map):3d} maps, {sum(per_map.values()):5d} findings   "
              f"worst: {', '.join(f'{n} {c}' for n, c in per_map.most_common(4))}")
        for ex in examples[(chk, sev)][:3]: print(f"        e.g. {ex[0]} @ {ex[2]},{ex[3]}: {ex[1]}")
    if "--json" in sys.argv:
        json.dump({f"{k[0]}|{k[1]}": dict(v) for k, v in fired.items()}, open(os.path.join(md.OUT, "calibration.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
