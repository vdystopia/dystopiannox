"""The object knowledge base: how every kind of indoor piece stands in Westwood's campaign rooms.

The Harrowby playtest (2026-10-05) found the same faults in room after room that earlier rounds had patched one case
at a time: two cauldrons in one cottage, a bed and a chest against the fires, four chests in a bedroom, statues side by
side, trophies hung behind statues, a candelabra every few steps, a whole wall of sacks evenly spaced, a storeroom wall
of fifteen identical shelves. "Do a pass over all objects and try to understand better how they fit in the world"
(review/FEEDBACK.md HB-1..HB-5). So this measures every kind of piece, once, on Westwood's campaign rooms (Con/War/Wiz
only, rules/common.py; a room the three campaigns share counted once, as rules/rooms/westwood.py counts them), and the
furnisher (mapgen/kit/furnish.py, through mapgen/kit/objects.py) and the checker (validate/checks.py pieces.*) both
obey it.

For every kind of piece (the type without its number, letter or direction: Chest of Chest1-4, Statue of Statue2a-h):
- cat: its category (chest, supply, shelf, hearth, cauldron, bed, table, statue, light, hanging, ...);
- foot: its footprint (half extents, uv units) and drawn extent (rules/out/decoration.json where known);
- where: the share standing against a wall, in a corner, free; walls: the share on each wall (NW, NE, SE, SW);
- runs: for the pieces against a wall, the lengths of runs of the same kind side by side (edge gap under RUN_GAP),
  as shares of the pieces (a piece in a run of 3 counts in "3"); alone: the share standing alone; groups: the same for
  free pieces;
- count: per room it stands in, by room type and over all: p50, p90, max, and in how many rooms;
- near: its nearest piece of each other category (edge gap, uv units): p5, p25, n;
- companions: the categories standing next to it (within NEXT_GAP) more often than chance, and those that share its
  rooms but never stand next to it;
- under: for a hanging, what stands under it on its wall; for a floor piece against a wall, how often a hanging hangs
  above it ("over");
- role: "showpiece" (once a room), "pair", "group", "fabric" (lines a wall: runs of 3 or more are common) or "piece".
And for the room as a whole: supply clusters (sizes, kinds per cluster, the gaps between clusters), candelabras per
100 tiles by room size, tables per room by type.

Writes rules/out/objects.json and prints a summary. Run: py rules/objects.py
"""
import collections, importlib.util, json, math, os, re, sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for p in ("validate", "review", "rules", "mapgen"):
    if os.path.join(REPO, p) not in sys.path: sys.path.insert(0, os.path.join(REPO, p))
import mapdata as md
import checks as C
import roommeasure as RM

_spec = importlib.util.spec_from_file_location("ww_rooms", os.path.join(HERE, "rooms", "westwood.py"))
WW = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(WW)

OUT = os.path.join(HERE, "out", "objects.json")
WALL_REACH = 1.0     # uv units from a wall line to a piece's back: it stands against the wall
RUN_GAP = 1.2        # uv units between two pieces' edges: they stand side by side (kit/objects.py RUN_GAP)
NEXT_GAP = 1.0       # uv units: standing next to each other
CLUSTER_GAP = 0.8    # supplies this near each other heap together

# Categories, finer than rules/room_types.py's families (a chest is not a sack, a cauldron is not a stove): one
# definition, the kit's (mapgen/kit/objects.py category, kind), so the furnisher reads the table by the same names.
from kit.objects import category, kind as kind_of
SUPPLY_SUB = [("sack", r"Sack"), ("crate", r"Crate"), ("keg", r"LargeBarrel|PiledBarrels"), ("barrel", r"Barrel"),
              ("basket", r"Basket")]


def supply_sub(t):
    for s, p in SUPPLY_SUB:
        if re.search(p, t): return s
    return "other"


def pct(vals, ps=(5, 25, 50, 75, 90)):
    s = sorted(vals)
    if not s: return None
    return {f"p{p}": round(s[min(len(s) - 1, int(p / 100 * len(s)))], 2) for p in ps}


def _edge_gap(a, b):
    """Gap between two pieces' footprints (uv units, boxes as the furnisher's; 0 when they touch or overlap)."""
    return max(0.0, abs(a["u"] - b["u"]) - a["hu"] - b["hu"], abs(a["v"] - b["v"]) - a["hv"] - b["hv"])


def _wall_lines(m):
    """Every wall cell's lines: cell -> [(line, coord, along)] (a '/' cell lies on u = x + y + 1 and runs along
    v = x - y; a back-slash cell on v = x - y, along u = x + y + 1), as the furnisher reads its runs."""
    out = {}
    for (x, y), w in m.walls.items():
        ls = []
        if any((x + a, y + b) in m.walls for a, b in ((1, -1), (-1, 1))) or w.facing == 0: ls.append(("/", x + y + 1, x - y))
        if any((x + a, y + b) in m.walls for a, b in ((1, 1), (-1, -1))) or w.facing == 1: ls.append(("\\", x - y, x + y + 1))
        if ls: out[(x, y)] = ls
    return out


def _walls_of(p, lines):
    """[(wall name, line, coord, gap from the line to the piece's back, along)] of the walls a piece stands against:
    the wall lines within three cells of it, on whichever side it stands (NW, NE, SE, SW in the user's frame)."""
    reach = 2.4 if p["cat"] == "hanging" else WALL_REACH
    x0, y0 = math.floor((p["u"] + p["v"]) / 2), math.floor((p["u"] - p["v"]) / 2)
    best = {}
    for a in range(-3, 4):
        for b in range(-3, 4):
            for line, coord, along_c in lines.get((x0 + a, y0 + b), ()):
                along = p["v"] if line == "/" else p["u"]
                if abs(along - along_c) > 1.05: continue
                perp = (p["u"] if line == "/" else p["v"]) - coord
                depth = p["hu"] if line == "/" else p["hv"]
                gap = abs(perp) - depth
                if gap > reach or abs(perp) < 0.05: continue
                key = (line, coord, perp > 0)
                if key not in best or gap < best[key][3]:
                    name = ("NW" if perp > 0 else "SE") if line == "/" else ("SW" if perp > 0 else "NE")
                    best[key] = (name, line, coord, round(gap, 2), along)
    return sorted(best.values(), key=lambda w: w[3])


def _pieces(m, objs, lines):
    ps = []
    for o in objs:
        t = o["type"]
        cat = category(t)
        if not cat or "MONSTER" in o["cls"]: continue
        u, v = C.uv_of(o)
        hu, hv = C._half_uv(o)
        p = dict(t=t, kind=kind_of(t), cat=cat, u=u, v=v, hu=hu, hv=hv, block=m.blocking(o))
        ws = _walls_of(p, lines)
        p["walls"] = ws
        if cat == "hanging": p["where"] = "wall" if ws else "free"
        else:
            p["where"] = "corner" if len({w[1] for w in ws}) >= 2 else "wall" if ws else "free"
        p["wall"] = ws[0][0] if ws else None
        ps.append(p)
    return ps


def _buckets(ps, size=8.0):
    b = collections.defaultdict(list)
    for i, p in enumerate(ps): b[(int(p["u"] // size), int(p["v"] // size))].append(i)
    return b, size


def _around(p, ps, bk):
    b, size = bk
    i0, j0 = int(p["u"] // size), int(p["v"] // size)
    for a in (-1, 0, 1):
        for c in (-1, 0, 1):
            for k in b.get((i0 + a, j0 + c), ()): yield ps[k]


def _relate(ps):
    """Runs of one kind side by side along a wall, free groups of one kind, each piece's nearest of every category
    (within 8 units), and the hangings with what stands under them."""
    floor = [p for p in ps if p["cat"] not in ("hanging", "rug")]
    bk = _buckets(floor)
    for p in floor: p["run"] = 1
    by_wall = collections.defaultdict(list)
    for p in floor:
        if p["where"] != "free":
            w = p["walls"][0]
            by_wall[(w[1], w[2], w[0], p["kind"])].append((w[4], p))
    for lst in by_wall.values():
        lst.sort(key=lambda x: x[0])
        groups, cur = [], [lst[0][1]]
        for (a0, p0), (a1, p1) in zip(lst, lst[1:]):
            if _edge_gap(p0, p1) <= RUN_GAP: cur.append(p1)
            else: groups.append(cur); cur = [p1]
        groups.append(cur)
        for g in groups:
            for p in g: p["run"] = len(g)
    free = [p for p in floor if p["where"] == "free"]
    for p in free: p["_seen"] = False
    for p in free:
        if p["_seen"]: continue
        comp, q = [], [p]
        while q:
            x = q.pop()
            if x["_seen"]: continue
            x["_seen"] = True; comp.append(x)
            q += [y for y in _around(x, floor, bk) if y["where"] == "free" and y.get("_seen") is False
                  and y["kind"] == x["kind"] and _edge_gap(x, y) <= RUN_GAP]
        for x in comp: x["run"] = len(comp)
    for p in free: p.pop("_seen", None)
    for p in floor:
        near = {}
        for q in _around(p, floor, bk):
            if q is p: continue
            g = _edge_gap(p, q)
            key = q["cat"] if q["kind"] != p["kind"] else "same"
            if g < near.get(key, 1e9): near[key] = g
        p["near"] = {k: round(g, 2) for k, g in near.items()}
    for p in floor: p["hung"] = False
    for h in ps:
        if h["cat"] != "hanging" or not h["walls"]: continue
        name, line, coord, _, along = h["walls"][0]
        ha = h["hv"] if line == "/" else h["hu"]
        h["under"] = []
        for p in _around(h, floor, bk):
            if p["where"] == "free" or not any(w[1] == line and w[2] == coord and w[0] == name for w in p["walls"]): continue
            pa = p["v"] if line == "/" else p["u"]
            pha = p["hv"] if line == "/" else p["hu"]
            if abs(pa - along) < ha + pha - 0.1:
                h["under"].append(p["cat"]); p["hung"] = True
    return floor


KEEP = ("t", "kind", "cat", "hu", "hv", "where", "wall", "run", "near", "hung", "block", "under")


def room_facts(m, r, typ, lines):
    """One room: its pieces (for the counts per room) and its supply clusters."""
    ps = _pieces(m, r["objects"], lines)
    floor = _relate(ps)
    sup = [p for p in floor if p["cat"] == "supply"]
    seen, clusters = set(), []
    for i in range(len(sup)):
        if i in seen: continue
        comp, q = [], [i]
        while q:
            j = q.pop()
            if j in seen: continue
            seen.add(j); comp.append(sup[j])
            q += [k for k in range(len(sup)) if k not in seen and _edge_gap(sup[k], sup[j]) <= CLUSTER_GAP]
        clusters.append(comp)
    cl_out = []
    for k, c in enumerate(clusters):
        others = [x for kk, cc in enumerate(clusters) if kk != k for x in cc]
        gap = min((_edge_gap(a, b) for a in c for b in others), default=None)
        cl_out.append(dict(n=len(c), kinds=len({x["kind"] for x in c}), subs=sorted({supply_sub(x["t"]) for x in c}),
                           wall=any(x["where"] != "free" for x in c), gap=None if gap is None else round(gap, 2),
                           most=collections.Counter(x["kind"] for x in c).most_common(1)[0][1]))
    return dict(type=typ, tiles=r["tiles"], pieces=[{k: p[k] for k in KEEP if k in p} for p in ps], clusters=cl_out)


def one(name, whole=False):
    """The rooms of one campaign map (and, for a layout's representative map, every piece of it: whole)."""
    m = md.load(md.corpus_json(name))
    lines = _wall_lines(m)
    out = []
    found = []
    for r in C.find_rooms(m, max_tiles=1500):
        if r["tiles"] < 8 or not r["objects"]: continue
        wall = [m.walls[(x + a, y + b)] for x, y in r["cells"] for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if (x + a, y + b) in m.walls]
        built = wall and sum(1 for w in wall if not WW.NATURAL.search(w.material)) >= 0.6 * len(wall)
        # a cave pocket or a dungeon hall is no building room (it has no type)
        found.append((r, None if built else "other"))
    for r, typ, _ in WW.hand_rooms(name, m): found.append((r, typ))
    for r, typ0 in found:
        meas = RM.measure(m, r)
        typ = typ0 or WW.classify(r, meas)
        if typ in ("empty", "dungeon"): typ = "other"
        xs = [c[0] for c in r["cells"]]; ys = [c[1] for c in r["cells"]]
        f = room_facts(m, r, typ, lines)
        f.update(map=name, centre=[round(sum(xs) / len(xs)), round(sum(ys) / len(ys))])
        out.append(f)
    pieces = []
    if whole:
        # how every piece stands, wherever it stands (Westwood keeps most of its log shelves and sacks in caves and
        # dens the room finder does not close: War03c, Con02a); a supply or a plant only near a wall, so the open
        # ground's props stay out
        ps = _pieces(m, m.objects, lines)
        _relate(ps)
        pieces = [{k: p[k] for k in KEEP if k in p} for p in ps if p["walls"] or p["cat"] not in ("supply", "plant")]
    return out, pieces


def _one(args):
    return one(*args)


def _share(c):
    n = sum(c.values()) or 1
    return {k: round(v / n, 3) for k, v in sorted(c.items(), key=lambda kv: -kv[1])}


def aggregate(rooms, pieces):
    kinds = collections.defaultdict(lambda: dict(n=0, cat=None, types=collections.Counter(), where=collections.Counter(),
                                                 walls=collections.Counter(), runs=collections.Counter(),
                                                 groups=collections.Counter(), near=collections.defaultdict(list),
                                                 next=collections.Counter(), hung=0, wallpieces=0,
                                                 under=collections.Counter(), hu=[], hv=[]))
    counts = collections.defaultdict(lambda: collections.defaultdict(list))     # kind -> type -> [count per room]
    rooms_of = collections.Counter()                                           # kind -> rooms holding it
    cats_in_room = collections.defaultdict(collections.Counter)                # kind -> cat -> rooms sharing
    type_tiles = collections.defaultdict(list)
    for r in rooms:
        type_tiles[r["type"]].append(r["tiles"])
        n = collections.Counter(p["kind"] for p in r["pieces"])
        cats = {p["cat"] for p in r["pieces"]}
        for k, c in n.items():
            counts[k][r["type"]].append(c); rooms_of[k] += 1
            if r["type"] != "other": counts[k]["*"].append(c)        # "*": building rooms of every type
            cat_k = next(p["cat"] for p in r["pieces"] if p["kind"] == k)
            for c2 in cats:
                if c2 != cat_k: cats_in_room[k][c2] += 1
    for p in pieces:
        if True:
            d = kinds[p["kind"]]
            d["n"] += 1; d["cat"] = p["cat"]; d["types"][p["t"]] += 1
            d["hu"].append(p["hu"]); d["hv"].append(p["hv"])
            d["where"][p["where"]] += 1
            if p.get("wall"): d["walls"][p["wall"]] += 1
            if "run" in p:
                (d["runs"] if p["where"] != "free" else d["groups"])[min(p["run"], 6)] += 1
            for c2, g in (p.get("near") or {}).items(): d["near"][c2].append(g)
            for c2, g in (p.get("near") or {}).items():
                if g <= NEXT_GAP and c2 not in ("same", "samecat"): d["next"][c2] += 1
            if p["cat"] not in ("hanging", "rug") and p["where"] != "free":
                d["wallpieces"] += 1; d["hung"] += bool(p.get("hung"))
            for c2 in p.get("under", ()): d["under"][c2] += 1
    out = {}
    for k, d in kinds.items():
        cnt = {t: dict(p50=pct(v)["p50"], p90=pct(v)["p90"], max=max(v), rooms=len(v)) for t, v in counts[k].items()}
        runs_n = sum(d["runs"].values())
        alone = d["runs"][1] / runs_n if runs_n else None
        long_runs = sum(v for L, v in d["runs"].items() if L >= 3) / runs_n if runs_n else 0.0
        pairs = d["runs"][2] / runs_n if runs_n else 0.0
        run_p90 = None
        if runs_n:
            acc, run_p90 = 0, 1
            for L in sorted(d["runs"]):
                acc += d["runs"][L]
                if acc >= 0.9 * runs_n: run_p90 = L; break
        near = {c2: dict(p5=pct(v)["p5"], p25=pct(v)["p25"], n=len(v)) for c2, v in d["near"].items() if len(v) >= 3}
        comp = {}
        for c2, nn in d["next"].items():
            comp[c2] = round(nn / d["n"], 3)
        never = sorted(c2 for c2, rr in cats_in_room[k].items() if rr >= 5 and d["next"].get(c2, 0) == 0
                       and c2 not in ("hanging", "rug", "light"))
        allc = cnt.get("*") or cnt.get("other", {})
        if allc.get("p90", 1) <= 1 and allc.get("rooms", 0) >= 2 and (alone is None or alone >= 0.8):
            role = "showpiece"
        elif runs_n >= 6 and long_runs >= 0.35:
            role = "fabric"
        elif runs_n >= 4 and pairs >= 0.4 and long_runs < 0.2:
            role = "pair"
        elif runs_n >= 4 and long_runs >= 0.15:
            role = "group"
        else:
            role = "piece"
        out[k] = dict(cat=d["cat"], n=d["n"], rooms=rooms_of[k], types=dict(d["types"].most_common(8)),
                      foot=dict(hu=round(sum(d["hu"]) / len(d["hu"]), 2), hv=round(sum(d["hv"]) / len(d["hv"]), 2)),
                      where=_share(d["where"]), walls=_share(d["walls"]),
                      runs={str(L): v for L, v in sorted(d["runs"].items())}, alone=None if alone is None else round(alone, 3),
                      long_runs=round(long_runs, 3), run_p90=run_p90,
                      groups={str(L): v for L, v in sorted(d["groups"].items())},
                      count=cnt, near=near, companions=dict(sorted(comp.items(), key=lambda kv: -kv[1])[:8]), never=never,
                      over=round(d["hung"] / d["wallpieces"], 3) if d["wallpieces"] else None, wallpieces=d["wallpieces"],
                      under=dict(d["under"]), role=role)
    # category pairs: nearest-neighbour edge gaps (the clearances)
    pairs = collections.defaultdict(list)
    for p in pieces:
        if True:
            for c2, g in (p.get("near") or {}).items():
                if c2 == "same": c2 = p["cat"]
                elif c2 == "samecat": continue
                pairs[f"{p['cat']}|{c2}"].append(g)
    cat_pairs = {k: dict(pct(v, (1, 5, 10, 25, 50)), n=len(v)) for k, v in sorted(pairs.items()) if len(v) >= 5}
    # hangings over floor pieces by category
    over = collections.defaultdict(lambda: [0, 0])
    for p in pieces:
        if True:
            if p["cat"] in ("hanging", "rug", "light") or p["where"] == "free": continue
            over[p["cat"]][0] += 1; over[p["cat"]][1] += bool(p.get("hung"))
    hung_over = {c: dict(wallpieces=a, hung=b, share=round(b / a, 3)) for c, (a, b) in sorted(over.items()) if a >= 5}
    # supply clusters
    cl = [c for r in rooms for c in r["clusters"]]
    clusters = dict(n=len(cl), size={str(k): v for k, v in sorted(collections.Counter(min(c["n"], 8) for c in cl).items())},
                    size_pct=pct([c["n"] for c in cl]),
                    kinds_by_size={str(s): pct([c["kinds"] for c in cl if min(c["n"], 6) == s]) for s in range(2, 7)},
                    mixed=round(sum(1 for c in cl if c["n"] >= 2 and c["kinds"] >= 2) / max(1, sum(1 for c in cl if c["n"] >= 2)), 3),
                    most_of_one=pct([c["most"] for c in cl if c["n"] >= 3]),
                    gap=pct([c["gap"] for c in cl if c["gap"] is not None]),
                    subs=_share(collections.Counter(s for c in cl for s in c["subs"])),
                    on_wall=round(sum(1 for c in cl if c["wall"]) / max(1, len(cl)), 3))
    # candelabras (any floor light) per room and per 100 tiles; tables per room
    lights = collections.defaultdict(list)
    for r in rooms:
        if r["type"] == "other": continue
        n = sum(1 for p in r["pieces"] if p["cat"] == "light" and p["kind"] in ("Candleabra", "Candelabra"))
        band = "small" if r["tiles"] < 40 else "medium" if r["tiles"] < 100 else "large"
        lights[band].append((n, r["tiles"]))
        lights["*"].append((n, r["tiles"]))
    light = {b: dict(count=pct([n for n, _ in v]), per100=pct([100 * n / t for n, t in v if n]),
                     tiles_per=pct([t / n for n, t in v if n]), rooms=len(v), with_any=sum(1 for n, _ in v if n))
             for b, v in lights.items()}
    sets = collections.defaultdict(list)
    for r in rooms:
        if r["type"] == "other": continue
        tables = sum(1 for p in r["pieces"] if p["cat"] == "table")
        desks = sum(1 for p in r["pieces"] if p["cat"] == "desk")
        chests = sum(1 for p in r["pieces"] if p["cat"] == "chest")
        cauld = sum(1 for p in r["pieces"] if p["cat"] == "cauldron")
        statues = sum(1 for p in r["pieces"] if p["cat"] == "statue")
        sets[r["type"]].append((tables, desks, chests, cauld, statues, r["tiles"]))
    per_type = {t: dict(rooms=len(v), tiles=pct([x[5] for x in v]), tables=pct([x[0] for x in v]),
                        tables_desks=pct([x[0] + x[1] for x in v]), chests=pct([x[2] for x in v]),
                        chests_max=max(x[2] for x in v), cauldrons_max=max(x[3] for x in v),
                        statues=pct([x[4] for x in v]))
                for t, v in sorted(sets.items())}
    return dict(kinds=out, cat_pairs=cat_pairs, hung_over=hung_over, clusters=clusters, lights=light, types=per_type)


def main():
    import common
    maps = [n for n, _ in md.campaign_corpus_maps()]
    with common.db() as con:                 # one map of each layout (the three campaigns share most of them)
        rep = {r["map"]: r["rep"] for r in con.execute("SELECT map, rep FROM layout_group")}
    reps = {rep.get(n, n) for n in maps}
    with ProcessPoolExecutor(6) as pool:
        res = list(pool.map(_one, [(n, n in reps) for n in maps]))
    found = [r for rs, _ in res for r in rs]
    pieces = [p for _, ps in res for p in ps]
    seen, rooms = set(), []
    for r in found:                      # a room the campaigns share (same floor, same place) counts once
        key = (r["tiles"], tuple(r["centre"]))
        if key in seen: continue
        seen.add(key); rooms.append(r)
    agg = aggregate(rooms, pieces)
    agg["source"] = dict(rooms=len(rooms), pieces=len(pieces), layouts=len(reps), maps="Westwood's campaign maps (Con/War/Wiz), each room once",
                         run_gap=RUN_GAP, next_gap=NEXT_GAP, wall_reach=WALL_REACH, cluster_gap=CLUSTER_GAP)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(agg, f, indent=1, sort_keys=True)
    ks = agg["kinds"]
    roles = collections.Counter(d["role"] for d in ks.values())
    print(f"{len(rooms)} rooms, {len(ks)} kinds profiled: {dict(roles)}")
    print(f"{'kind':24} {'cat':9} {'n':>4} {'rooms':>5} role       alone long run90 cnt p50/p90/max  where")
    for k, d in sorted(ks.items(), key=lambda kv: -kv[1]["n"])[:70]:
        c = d["count"].get("*", {})
        print(f"{k:24} {str(d['cat']):9} {d['n']:4} {d['rooms']:5} {d['role']:10} {str(d['alone']):5} {d['long_runs']:.2f} "
              f"{str(d['run_p90']):4} {c.get('p50')}/{c.get('p90')}/{c.get('max')}  {d['where']}")
    print("clusters:", agg["clusters"])
    print("lights:", agg["lights"])
    print("hung over:", agg["hung_over"])


if __name__ == "__main__":
    main()
