"""Westwood's building rooms by type: the numbers each type's brief (rules/rooms/<type>.md) and profile
(mapgen/kit/roomtypes.py) stand on.

Every enclosed room of Westwood's single-player maps whose walls are built (not a cave pocket) is classified by its
contents into one of our room types (kit/roomtypes.py TYPES; rules/room_types.py classify, refined: a desk among a few
shelves is a study, racks with no counter or keeper an armoury, a big hall of tables a great hall) and its culture
(Land of the Dead, ogre, Dun Mir, or the towns'), then measured as review/roommeasure.py measures ours. Per type:
how many rooms, their sizes, and the 10th-90th percentiles of coverage, open floor, pieces per tile, distinct types and
the most of one piece; and the best examples (the most varied rooms of a typical size, by map and room centre).

Writes rules/rooms/westwood.json and prints a table. Run: py rules/rooms/westwood.py
"""
import collections, json, os, re, sys
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for p in ("validate", "review", "rules", "mapgen"):
    sys.path.insert(0, os.path.join(REPO, p))
import mapdata as md
import checks as C
import roommeasure as RM

NATURAL = re.compile(r"Cave|Rock|Dirt|Root|Tree|Decidious|Coni-|Aspen|Hedge|Shrub|Thorn|Volcano|IceWall|Shard|Invisible|Mine",
                     re.I)
OUT = os.path.join(HERE, "westwood.json")


def culture(objs):
    n = collections.Counter()
    for o in objs:
        t = o["type"]
        if t.startswith("LOTD") or "LOTD" in t: n["lotd"] += 1
        elif t.startswith("Ogre"): n["ogre"] += 1
        elif t.startswith("DunMir"): n["dunmir"] += 1
    if n["lotd"] >= 2: return "lotd"
    if n["ogre"] >= 2: return "ogre"
    if n["dunmir"] >= 1: return "dunmir"
    return "town"


def classify(r, meas):
    """Our room type for a Westwood room, from its contents."""
    kind, _ = C.room_profile(r)
    f = meas["fam"]
    n = lambda k: f.get(k, 0)
    ts = [o["type"] for o in r["objects"]]
    keeper = any(C.RT.SHOPKEEPER.match(t) for t in ts)
    if kind == "shop" and not n("counter_shop") and not keeper: return "armoury"
    if kind == "laboratory" and not any(re.match(r"WizardWorkstation|Vandegraf|Orrery|Telescope|SentryGlobe", t) for t in ts) \
            and any(re.match(r"PotionShelves|Cauldron", t) for t in ts):
        return "herbalist"
    if kind == "library" and n("desk") and n("shelves") <= 6: return "study"
    if kind in ("dining_hall", "living_room") and meas["tiles"] >= 140 and n("table") >= 2: return "great_hall"
    if kind == "hall" and n("bench") >= 4: return "chapel"            # Westwood's temples: benches facing the far end
    if kind == "hall" and (meas["tiles"] < 40 or meas["pieces"] < 4): return "passage"   # a corridor, a bare vestibule
    return kind


def one(name):
    m = md.load(md.corpus_json(name))
    out = []
    for r in C.find_rooms(m, max_tiles=1500):
        if r["tiles"] < 8 or not r["objects"]: continue
        wall = [m.walls[(x + a, y + b)] for x, y in r["cells"] for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if (x + a, y + b) in m.walls]
        if not wall or sum(1 for w in wall if not NATURAL.search(w.material)) < 0.6 * len(wall): continue
        meas = RM.measure(m, r)
        typ = classify(r, meas)
        if typ in ("empty", "other", "dungeon"): continue
        xs = [c[0] for c in r["cells"]]; ys = [c[1] for c in r["cells"]]
        out.append(dict(map=name, type=typ, culture=culture(r["objects"]), centre=[round(sum(xs) / len(xs)), round(sum(ys) / len(ys))],
                        **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in meas.items()
                           if k in ("tiles", "cover", "middle", "open", "pieces", "per_tile", "types", "most", "free_most",
                                    "walls", "lined", "fam")}))
    return out


def pct(vals, ps=(10, 25, 50, 75, 90)):
    s = sorted(vals)
    if not s: return None
    return {f"p{p}": round(s[min(len(s) - 1, int(p / 100 * len(s)))], 3) for p in ps}


def main():
    maps = [n for n, _ in md.sp_corpus_maps()]
    with ProcessPoolExecutor(6) as pool:
        found = [r for rs in pool.map(one, maps) for r in rs]
    # the three campaigns share most layouts: a room met again (same type, size and contents) counts once
    seen, rooms = set(), []
    for r in found:
        key = (r["type"], r["tiles"], r["pieces"], r["types"], tuple(sorted(r["fam"].items())))
        if key in seen: continue
        seen.add(key); rooms.append(r)
    by = collections.defaultdict(list)
    for r in rooms: by[r["type"]].append(r)
    types = {}
    for t, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        mid = pct([r["tiles"] for r in rs])
        typical = [r for r in rs if mid["p25"] <= r["tiles"] <= mid["p90"]] or rs
        best = sorted(typical, key=lambda r: (-r["types"], -r["walls"], r["most"][1]))[:4]
        fams = collections.Counter()
        for r in rs:
            for f in r["fam"]: fams[f] += 1
        types[t] = dict(n=len(rs), maps=len({r["map"] for r in rs}),
                        cultures=dict(collections.Counter(r["culture"] for r in rs)),
                        tiles=mid, cover=pct([r["cover"] for r in rs]), open=pct([r["open"] for r in rs]),
                        middle=pct([r["middle"] for r in rs]), per_tile=pct([r["per_tile"] for r in rs]),
                        types=pct([r["types"] for r in rs]), most=pct([r["most"][1] for r in rs]),
                        free_most=pct([r["free_most"][1] for r in rs]), walls=pct([r["walls"] for r in rs]),
                        lined=pct([r["lined"] for r in rs]),
                        families={f: round(k / len(rs), 2) for f, k in fams.most_common()},
                        most_kinds=collections.Counter(r["most"][0] for r in rs).most_common(5),
                        best=[dict(map=r["map"], centre=r["centre"], tiles=r["tiles"], types=r["types"], cover=r["cover"],
                                   open=r["open"], culture=r["culture"]) for r in best])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(dict(rooms=len(rooms), types=types), f, indent=1)
    print(f"{len(rooms)} rooms")
    print(f"{'type':14} {'n':>4} {'maps':>4}  tiles p50  cover p10-p50-p90   open p10-p50-p90   per_tile p50  types p50  most p50/p90")
    for t, d in types.items():
        print(f"{t:14} {d['n']:4} {d['maps']:4}  {d['tiles']['p50']:6}   {d['cover']['p10']:.2f}-{d['cover']['p50']:.2f}-{d['cover']['p90']:.2f}"
              f"   {d['open']['p10']:.2f}-{d['open']['p50']:.2f}-{d['open']['p90']:.2f}   {d['per_tile']['p50']:.2f}"
              f"   {d['types']['p50']:5}   {d['most']['p50']}/{d['most']['p90']}  {d['cultures']}")


if __name__ == "__main__":
    main()
