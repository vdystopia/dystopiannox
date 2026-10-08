"""Westwood's iron fences against the floor grid [FN-1]: where the floor changes under a fence and whether it blends.

    py rules/fences.py          # the campaign maps (one map per layout) -> rules/out/fences.json and a summary

Geometry (mapgen/nox.py FENCE_POLICY): walls and tiles both sit on the even lattice (x + y even); a tile (x, y) is a
diamond centred on grid corner (x+1, y+1), its sides on the lines x + y odd and x - y odd.
- A / piece (facing 0) runs from its cell's corner (x, y+1) to (x+1, y): exactly on the seam between the tile behind
  it, (x-1, y-1), and the tile in front, (x, y).
- A \\ piece (facing 1) runs from (x, y) to (x+1, y+1), through the centres of the tiles on its line, (x-1, y-1) and
  (x, y). Each such line tile has a tile behind it (E, (1, -1)) and in front (W, (-1, 1)); a floor change across the
  piece lies on one of those two seams, half a tile from the fence.
For each straight piece this counts the floor changes across it, which seam they lie on, and how many carry an edge
piece (blend), all and for the outdoor ground pairs alone (grass, dirt, cobble, stone), and how many pieces over
outdoor ground have one floor under them (the line tile and both tiles across it).

Result (2026-10-08): across all iron fences (many in dungeons, over lava and tiles) about two thirds of the floor changes
blend; but over outdoor ground Westwood keeps one floor under the fence: 93% of / pieces and 78% of \\ pieces, and the
few \\ pieces it lays across two grounds are cut hard (71% of their seams behind the line tile).
"""
import collections, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C                                    # noqa: E402

FENCES = ("IronFence", "IronFenceDamaged")
SIDE = {"E": (1, -1), "N": (-1, -1), "S": (1, 1), "W": (-1, 1)}
PIECES = {"E": (12, 13, 14, 18, 19), "N": (6, 8, 10, 18, 17), "S": (5, 7, 9, 19, 16), "W": (1, 2, 3, 17, 16)}
OPP = {"E": "W", "W": "E", "N": "S", "S": "N"}
GROUND = re.compile(r"Grass|Dirt|Cobble|Stone")


def layouts():
    """One campaign map per layout (the class campaigns share most of them)."""
    with C.db() as c:
        reps = {r["map"]: r["rep"] for r in c.execute("SELECT map, rep FROM layout_group")}
        maps = {r["map"] for r in c.execute("SELECT DISTINCT map FROM walls WHERE material IN (?, ?)", FENCES)}
    return sorted({reps.get(m, m) for m in maps if C.is_campaign(m)})


def measure():
    tot = collections.Counter()
    with C.db() as c:
        for mp in layouts():
            tiles = {(r["x"], r["y"]): r["material"] for r in c.execute("SELECT x, y, material FROM tiles WHERE map=?", (mp,))}
            edges = collections.defaultdict(set)
            for r in c.execute("SELECT x, y, overlay, dir FROM edges WHERE map=?", (mp,)):
                edges[(r["x"], r["y"])].add((r["overlay"], r["dir"]))
            walls = [(r["x"], r["y"], r["facing"]) for r in
                     c.execute("SELECT x, y, facing FROM walls WHERE map=? AND material IN (?, ?)", (mp,) + FENCES)]

            def seam(a, d, key):
                b = (a[0] + SIDE[d][0], a[1] + SIDE[d][1])
                ma, mb = tiles.get(a), tiles.get(b)
                if ma is None or mb is None or ma == mb: return
                blended = any(ov == mb and p in PIECES[d] for ov, p in edges[a]) or \
                    any(ov == ma and p in PIECES[OPP[d]] for ov, p in edges[b])
                for k in (key, key + " ground") if GROUND.search(ma) and GROUND.search(mb) else (key,):
                    tot[k + " seams"] += 1; tot[k + " blended"] += blended

            for x, y, f in walls:
                trio = [(x - 1, y - 1), (x, y)] if f == 0 else [(x, y), (x + 1, y - 1), (x - 1, y + 1)] if f == 1 else []
                ms = [tiles.get(t) for t in trio]
                if trio and None not in ms and all(GROUND.search(m_) for m_ in ms):
                    k = "/" if f == 0 else "\\"
                    tot[f"{k} pieces over outdoor ground"] += 1
                    tot[f"{k} pieces over outdoor ground, one floor under them"] += len(set(ms)) == 1
                if f == 0:
                    tot["/ pieces"] += 1
                    seam((x - 1, y - 1), "S", "/ on the line")
                elif f == 1:
                    t, e, w = (x, y), (x + 1, y - 1), (x - 1, y + 1)
                    if None in (tiles.get(t), tiles.get(e), tiles.get(w)): continue
                    tot["\\ pieces"] += 1
                    if tiles[e] != tiles[w]:
                        tot["\\ floor changes across"] += 1
                        tot["\\ line tile takes the floor in front" if tiles[t] == tiles[w] else
                            "\\ line tile takes the floor behind" if tiles[t] == tiles[e] else "\\ line tile a third floor"] += 1
                    seam(t, "E", "\\ half a tile behind")
                    seam(t, "W", "\\ half a tile in front")
    return dict(layouts=len(layouts()), counts=dict(sorted(tot.items())))


if __name__ == "__main__":
    res = measure()
    os.makedirs(C.OUT, exist_ok=True)
    with open(os.path.join(C.OUT, "fences.json"), "w", encoding="utf-8") as f: json.dump(res, f, indent=1)
    print(f"{res['layouts']} campaign layouts with iron fences")
    for k, v in res["counts"].items():
        if k.endswith(" blended"):
            n = res["counts"][k[:-8] + " seams"]
            print(f"  {k[:-8]:40s} {v:5d} of {n:5d} seams blended ({v / n:.0%})")
        elif not k.endswith(" seams"):
            print(f"  {k:40s} {v:5d}")
