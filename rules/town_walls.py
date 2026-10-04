"""Where a town's walls stand: Westwood's town maps carry 26-49 wall pieces per 100 floor tiles (typical 37), and only
a few of them are the houses'. This sorts every wall piece of a map by what it bounds:

- edge: the map's outer boundary (the void beyond it reaches the grid's edge): the forest wall, the cliffs;
- island: the rim of a hole in the land, a block of forest or rock standing in the open (a void with no way out);
- building: a wall of an enclosed room with an indoor floor;
- yard: a wall of an enclosed outdoor plot, closed by a gate (a garden, a pen, a graveyard);
- partition: free-standing in the open with land on both sides (a fence or a hedge row that closes nothing).

and measures the islands, yards and partitions (size, material, what a yard holds).

    py rules/town_walls.py                       # Westwood's town maps -> rules/out/town_walls.json
    py rules/town_walls.py path\\to\\Map.map ...   # the same figures for our maps, beside Westwood's
"""
import collections, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "validate"))
import mapdata as md                                  # noqa: E402
from floors import family                             # noqa: E402
import common as C                                    # noqa: E402

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))
INDOOR = {"interior_wood", "interior_rug", "tile", "brick", "dungeon_stone", "facade"}
FENCES = ("Log", "IronFence", "IronFenceDamaged", "Dilapidated", "DilapidatedShort", "FieldStoneShort", "Cobblestone",
          "AncientRuinShort", "RootLight")


def kind_of(mat):
    if mat.startswith("Invisible"): return "invisible"
    if mat in FENCES: return "fence"
    if mat.startswith(("Decidious", "Coni-", "Aspen", "Shrub", "Root")): return "forest"
    if mat in ("Dirt", "Rock", "CaveWall", "CaveWall2", "ManaMineWall", "IceWall", "Volcano"): return "cliff"
    return "masonry"


def analyse(m):
    """Figures for one MapData."""
    walls = m.walls
    gaps = {d["gap"] for d in m.doors}
    blocked = set(walls) | gaps
    cover = m.cover
    comp, comps = {}, []
    for start in [(x, y) for x in range(256) for y in range(256)]:
        if start in comp or start in blocked: continue
        cid = len(comps); comp[start] = cid; q = [start]; cells = []; edge = False; gate = False
        while q:
            p = q.pop(); cells.append(p)
            if p[0] in (0, 255) or p[1] in (0, 255): edge = True
            for dx, dy in N4:
                n = (p[0] + dx, p[1] + dy)
                if n in gaps: gate = True
                if not (0 <= n[0] < 256 and 0 <= n[1] < 256) or n in blocked or n in comp: continue
                comp[n] = cid; q.append(n)
        covered = [p for p in cells if p in cover]
        fams = collections.Counter(family(m.tiles[t]["material"]) for t in {m.tile_at_cell(p) for p in covered} if t)
        indoor = sum(v for f, v in fams.items() if f in INDOOR)
        n_t = sum(fams.values())
        # a hole is closed off with no door or gate into it: a block of forest or rock standing in the land, however
        # its floor is painted (the tiles under a rim reach inside it); a yard is an outdoor plot behind a gate
        if len(cells) < 4 and not gate: kind = "pocket"
        elif edge: kind = "void_edge" if len(covered) < 0.25 * len(cells) else "land"
        elif not gate: kind = "hole"
        elif n_t and indoor >= 0.5 * n_t: kind = "room"
        elif n_t <= 400: kind = "yard"
        else: kind = "land"
        comps.append(dict(kind=kind, cells=len(cells), tiles=n_t, floors=fams.most_common(3)))
    # the biggest outdoor component is the land, however it was classed
    land = max(range(len(comps)), key=lambda k: comps[k]["tiles"] if comps[k]["kind"] != "void_edge" else -1)
    if comps[land]["kind"] != "room": comps[land]["kind"] = "land"
    cls = {}
    for w in walls:
        ks = {comps[comp[n]]["kind"] for n in ((w[0] + dx, w[1] + dy) for dx, dy in N8) if n in comp}
        if "room" in ks: c = "building"
        elif "yard" in ks: c = "yard"
        elif "hole" in ks: c = "island"
        elif "void_edge" in ks: c = "edge"
        else: c = "partition"
        cls[w] = c
    n_tiles = len(m.tiles)
    per = collections.Counter(cls.values())
    out = dict(tiles=n_tiles, walls=len(walls), per100={k: round(100 * per[k] / n_tiles, 2) for k in
                                                         ("edge", "island", "building", "yard", "partition")})
    # islands: holes and their rims
    holes = [k for k, cp in enumerate(comps) if cp["kind"] == "hole"]
    rim = collections.defaultdict(set)
    for w, c in cls.items():
        if c != "island": continue
        for dx, dy in N8:
            n = (w[0] + dx, w[1] + dy)
            if n in comp and comps[comp[n]]["kind"] == "hole": rim[comp[n]].add(w)
    out["islands"] = dict(n=len(holes), per1000=round(1000 * len(holes) / n_tiles, 2),
                          rim=sorted(len(v) for v in rim.values()),
                          materials=collections.Counter(walls[w].material for v in rim.values() for w in v).most_common(5))
    # partitions and yard walls: runs (8-connected) by material kind
    runs = []
    seen = set()
    for w, c in cls.items():
        if c not in ("partition", "yard") or w in seen: continue
        q, run = [w], []
        seen.add(w)
        while q:
            p = q.pop(); run.append(p)
            for dx, dy in N8:
                n = (p[0] + dx, p[1] + dy)
                if n in cls and cls[n] in ("partition", "yard") and n not in seen: seen.add(n); q.append(n)
        mats = collections.Counter(walls[p].material for p in run)
        runs.append(dict(n=len(run), yard=any(cls[p] == "yard" for p in run), mat=mats.most_common(1)[0][0],
                         kind=kind_of(mats.most_common(1)[0][0])))
    out["runs"] = runs
    # yards: size, floors, what stands in them
    by_comp = collections.defaultdict(list)
    for o in m.objects:
        k = comp.get(md.MapData.cell_of(o["x"], o["y"]))
        if k is not None and comps[k]["kind"] == "yard": by_comp[k].append(o["type"])
    yards = []
    for k, cp in enumerate(comps):
        if cp["kind"] != "yard": continue
        yards.append(dict(tiles=cp["tiles"], floors=cp["floors"],
                          things=collections.Counter(by_comp[k]).most_common(6)))
    out["yards"] = yards
    return out


def town_maps():
    e = json.load(open(os.path.join(C.OUT, "environments.json"), encoding="utf-8"))["maps"]
    sp = C.sp_weights()
    return [k for k, v in e.items() if v.get("type") == "town" and k in sp]


def summary(results, weights):
    tot = sum(weights.values())
    def wavg(f): return round(sum(f(r) * weights[k] for k, r in results.items()) / tot, 2)
    s = dict(maps=sorted(results), per100={k: wavg(lambda r: r["per100"][k]) for k in
                                           ("edge", "island", "building", "yard", "partition")})
    s["islands_per1000"] = wavg(lambda r: r["islands"]["per1000"])
    rims = sorted(x for r in results.values() for x in r["islands"]["rim"])
    s["island_rim"] = dict(p25=rims[len(rims) // 4], p50=rims[len(rims) // 2], p75=rims[3 * len(rims) // 4]) if rims else {}
    runs = [x for r in results.values() for x in r["runs"]]
    by_kind = collections.Counter()
    for x in runs: by_kind[(x["kind"], x["yard"])] += x["n"]
    s["partition_pieces_by_kind"] = {f"{k}{' (yard)' if y else ''}": v for (k, y), v in by_kind.most_common()}
    fence_runs = sorted(x["n"] for x in runs if x["kind"] == "fence" and not x["yard"])
    s["fence_run"] = dict(n=len(fence_runs), p50=fence_runs[len(fence_runs) // 2] if fence_runs else 0,
                          p75=fence_runs[3 * len(fence_runs) // 4] if fence_runs else 0)
    mats = collections.Counter()
    for x in runs: mats[x["mat"]] += x["n"]
    s["partition_materials"] = mats.most_common(10)
    things = collections.Counter()
    for r in results.values():
        for y in r["yards"]:
            for t, n in y["things"]: things[t] += n
    s["yards"] = dict(n=sum(len(r["yards"]) for r in results.values()),
                      tiles=sorted(y["tiles"] for r in results.values() for y in r["yards"]),
                      things=things.most_common(15))
    return s


def show(name, r):
    p = r["per100"]
    print(f"{name:12s} tiles {r['tiles']:5d} walls/100 {100 * r['walls'] / r['tiles']:5.1f} | edge {p['edge']:5.1f} "
          f"island {p['island']:5.1f} building {p['building']:5.1f} yard {p['yard']:4.1f} partition {p['partition']:5.1f}"
          f" | islands {r['islands']['n']:3d} ({r['islands']['per1000']}/1000 tiles)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for path in sys.argv[1:]:
            r = analyse(md.load(path))
            show(os.path.splitext(os.path.basename(path))[0], r)
            print("   partition runs:", sorted(((x["n"], x["mat"], x["yard"]) for x in r["runs"]), reverse=True)[:12])
            print("   yards:", [(y["tiles"], y["things"][:3]) for y in r["yards"]][:10])
        sys.exit()
    res, w = {}, {}
    sp = C.sp_weights()
    for k in town_maps():
        res[k] = analyse(md.load(md.corpus_json(k)))
        w[k] = sp[k]
        show(k, res[k])
    s = summary(res, w)
    print(json.dumps(s, indent=1)[:3000])
    C.save_json("town_walls.json", dict(summary=s, maps={k: {a: b for a, b in v.items() if a != "runs"} for k, v in res.items()}))
