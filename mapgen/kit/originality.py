"""Originality check: how closely a generated room's furniture layout resembles any Westwood room.

A layout is the room's furniture (families from rules/room_types.py, lights and NPCs left out) with
positions normalised to the room's uv bounding box, so the same arrangement in a room of another size
still matches. Two layouts are compared by greedy same-family matching: pieces match when they are of
the same family and within MATCH_DIST (normalised units) of each other;
similarity = 2 * matches / (pieces in A + pieces in B). Mirror images count as copies, so each stock
room is also tried flipped along u, v and both.

    check(spec, room, objects) -> dict(max_sim, nearest, ok)
    py mapgen/kit/originality.py [rooms_per_kind]      # calibrate on stock rooms and test the furnisher

The stock index is built once from the corpus and cached in corpus/out/scratch/stock_room_layouts.json.
"""
import collections, json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
CACHE = os.path.join(REPO, "corpus", "out", "scratch", "stock_room_layouts.json")
MATCH_DIST = 0.15
THRESHOLD = 0.8          # max_sim at or above this = a recognisable copy. Westwood's own distinct rooms score a
                         # median 0.71 against their nearest stock neighbour (see calibrate()).
MIN_PIECES = 4           # layouts with fewer pieces, or a single family (a row of crates), cannot be recognised
SKIP = {None, "light", "colorlight", "npc", "shopkeeper", "dungeon"}

_STOCK = None


def _family(t):
    from kit.furnish import _family_of
    return _family_of(t)


def normalise(items, cells):
    """items: [(family, u, v)], cells: room grid cells -> [(family, nu, nv)] in [0, 1]."""
    us = [x + y for x, y in cells]; vs = [x - y for x, y in cells]
    u0, u1, v0, v1 = min(us), max(us) + 2, min(vs) - 1, max(vs) + 1
    return [(f, (u - u0) / max(1, u1 - u0), (v - v0) / max(1, v1 - v0)) for f, u, v in items]


def similarity(a, b):
    """Greedy same-family matching; returns 2 * matches / (len(a) + len(b))."""
    if not a or not b: return 0.0
    pairs = sorted((math.hypot(p[1] - q[1], p[2] - q[2]), i, j)
                   for i, p in enumerate(a) for j, q in enumerate(b) if p[0] == q[0])
    used_a, used_b, m = set(), set(), 0
    for d, i, j in pairs:
        if d > MATCH_DIST: break
        if i in used_a or j in used_b: continue
        used_a.add(i); used_b.add(j); m += 1
    return 2 * m / (len(a) + len(b))


def _flips(lay):
    yield lay
    yield [(f, 1 - u, v) for f, u, v in lay]
    yield [(f, u, 1 - v) for f, u, v in lay]
    yield [(f, 1 - u, 1 - v) for f, u, v in lay]


def build_stock():
    """Index every building room in the corpus (all categories) as a normalised layout."""
    sys.path.insert(0, os.path.join(REPO, "rules"))
    import common as c
    import rooms as R
    rooms = [r for r in json.load(open(os.path.join(c.OUT, "rooms.json"), encoding="utf-8"))["rooms"] if r["kind"] == "building"]
    by_map = collections.defaultdict(list)
    for r in rooms: by_map[r["map"]].append(r)
    groups = {}
    with c.db() as con:
        for row in con.execute("SELECT map, rep FROM layout_group"): groups[row["map"]] = row["rep"]
    out = []
    for m, rs in sorted(by_map.items()):
        _, comps, *_ = R.components(m)
        objs = {o["id"]: o for o in c.objects(m)}
        for r in rs:
            cells = comps[int(r["id"].split(":")[1])]["cells"]
            items = []
            for i in r.get("objects", []):
                o = objs.get(i)
                if not o: continue
                f = _family(o["type"])
                if f in SKIP: continue
                items.append((f, (o["x"] + o["y"]) / 23, (o["x"] - o["y"]) / 23))
            if len(items) >= 2:
                out.append(dict(id=r["id"], map=m, group=groups.get(m, m), tiles=r["tiles"],
                                layout=[[f, round(u, 3), round(v, 3)] for f, u, v in normalise(items, cells)]))
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(out, open(CACHE, "w", encoding="utf-8"))
    return out


def stock():
    global _STOCK
    if _STOCK is None:
        _STOCK = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else build_stock()
        for s in _STOCK: s["layout"] = [tuple(x) for x in s["layout"]]
    return _STOCK


def max_similarity(layout, exclude_group=None):
    best, nearest = 0.0, None
    fams = collections.Counter(f for f, _, _ in layout)
    for s in stock():
        if exclude_group and s["group"] == exclude_group: continue
        # cheap upper bound from family counts before the full match
        sf = collections.Counter(f for f, _, _ in s["layout"])
        bound = 2 * sum((fams & sf).values()) / (len(layout) + len(s["layout"]))
        if bound <= best: continue
        for fl in _flips(s["layout"]):
            sim = similarity(layout, fl)
            if sim > best: best, nearest = sim, s["id"]
    return best, nearest


def layout_of(spec, room, objects):
    """Normalised layout of a generated room from the object dicts the furnisher returned."""
    from kit.furnish import _Room
    g = _Room(spec, room)
    items = [(f, (o["x"] + o["y"]) / 23, (o["x"] - o["y"]) / 23) for o in objects
             for f in [_family(o["type"])] if f not in SKIP]
    return normalise(items, g.cells)


def check(spec, room, objects, threshold=THRESHOLD):
    """Compare a furnished room against every stock room. ok is False when it is a near copy."""
    lay = layout_of(spec, room, objects)
    sim, nearest = max_similarity(lay)
    trivial = len(lay) < MIN_PIECES or len({f for f, _, _ in lay}) < 2
    return dict(max_sim=round(sim, 3), nearest=nearest, pieces=len(lay), ok=sim < threshold or trivial)


def furnish_original(spec, room, kind=None, rng=None, style="town", tries=6, threshold=THRESHOLD):
    """furnish_room, re-rolled (removing the previous attempt's objects) until the layout is not a near copy
    of a stock room. Returns (objects, check result)."""
    from kit.furnish import furnish_room
    rng = rng or random.Random(0)
    best = None
    for _ in range(tries):
        objs = furnish_room(spec, room, kind, random.Random(rng.random()), style)
        res = check(spec, room, objs, threshold)
        if res["ok"]: return objs, res
        if best is None or res["max_sim"] < best[1]["max_sim"]: best = (objs, res)
        ids = {id(o) for o in objs}
        spec.d["objects"][:] = [o for o in spec.d["objects"] if id(o) not in ids]
    objs = furnish_room(spec, room, kind, random.Random(rng.random()), style)   # keep the last, flagged
    return objs, check(spec, room, objs, threshold)


# ---- calibration / report ------------------------------------------------------------------
def _q(vals):
    s = sorted(vals)
    return {f"p{p}": round(s[min(len(s) - 1, int(p / 100 * len(s)))], 3) for p in (10, 50, 90)} | {"max": round(s[-1], 3)}


def calibrate(per_kind=20, seed=7):
    st = stock()
    rng = random.Random(seed)
    report = {}
    # 1. Westwood re-used layouts (same layout group = the same map shipped for several classes): must score ~1
    by_group = collections.defaultdict(list)
    for s in st: by_group[s["group"]].append(s)
    dup = []
    for g, ss in by_group.items():
        maps = sorted({s["map"] for s in ss})
        if len(maps) < 2: continue
        a = [s for s in ss if s["map"] == maps[0] and len(s["layout"]) >= MIN_PIECES]
        for s in a[:6]:
            twin = next((t for t in ss if t["map"] == maps[1] and t["id"].split(":")[1] == s["id"].split(":")[1]), None)
            if twin: dup.append(similarity(s["layout"], twin["layout"]))
    report["stock_duplicates_same_layout_group"] = _q(dup) if dup else None
    # 2. distinct Westwood rooms: each stock room's best match among rooms of OTHER layout groups
    sample = rng.sample([s for s in st if len(s["layout"]) >= MIN_PIECES], 300)
    report["stock_vs_other_stock"] = _q([max_similarity(s["layout"], exclude_group=s["group"])[0] for s in sample])
    # 3. generated rooms
    report["generated"] = gen_report(per_kind, seed)
    return report


def gen_report(per_kind, seed):
    from nox import Spec, SOLO, uv_to_xy, rect_tiles, rect_wall_cells
    from kit.model import Room, Door
    from kit.furnish import furnish_room
    kinds = ["bedroom", "living_room", "kitchen", "dining_hall", "tavern", "shop", "library", "study", "smithy",
             "storeroom", "barracks", "laboratory"]
    rng = random.Random(seed)
    out, worst = {}, []
    for kind in kinds:
        sims = []
        for i in range(per_kind):
            m = Spec("Orig", summary="", description="", author="", version="", date="", type=SOLO, minPlayers=1, maxPlayers=1)
            us, vs = rng.choice(range(10, 25, 2)), rng.choice(range(10, 21, 2))
            u0, v0 = 160, -60
            m.room(u0, u0 + us, v0, v0 + vs, wall="StuccoLightWood", floor="OakWoodFloor")
            gap = tuple(int(c) for c in uv_to_xy((u0 + us // 2) // 2 * 2, v0))
            d = m.door(None, gap, "\\")
            r = Room(id="r", tiles=set(rect_tiles(u0, u0 + us, v0, v0 + vs)), floor="OakWoodFloor",
                     walls=rect_wall_cells(u0, u0 + us, v0, v0 + vs),
                     doors=[Door(gap=gap, line="\\", type=d["type"], connects=("r", "out"), px=(d["x"], d["y"]))])
            objs = furnish_room(m, r, kind, random.Random(rng.random()))
            res = check(m, r, objs)
            sims.append(res["max_sim"])
            worst.append((res["max_sim"], kind, us, vs, res["nearest"], res["pieces"], res["ok"]))
        out[kind] = _q(sims)
    allv = [w[0] for w in worst]
    out["all"] = _q(allv)
    out["share_at_or_above_threshold"] = round(sum(v >= THRESHOLD for v in allv) / len(allv), 3)
    out["share_flagged_not_ok"] = round(sum(not w[6] for w in worst) / len(worst), 3)
    out["worst"] = [dict(sim=w[0], kind=w[1], size=f"{w[2]}x{w[3]}", nearest=w[4], pieces=w[5]) for w in sorted(worst, reverse=True)[:5]]
    return out


if __name__ == "__main__":
    if "--rebuild" in sys.argv: build_stock(); sys.argv.remove("--rebuild")
    rep = calibrate(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
    path = os.path.join(REPO, "mapgen", "out", "test_rooms", "originality.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(rep, open(path, "w"), indent=1)
    print(json.dumps(rep, indent=1))
