"""Where Westwood puts each biome's signature objects: on the liquid (lava, water), against a wall (within 1.5 cells
of a wall cell), or in the open; and how many per 100 tiles of that context. Feeds kit/biome.py.

    py rules/biome_places.py
"""
import collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, "validate"))
import mapdata as md
from biomes import layout_key

LIQUID = re.compile(r"^(Lava|Water|WaterDeep|WaterShallow|IceFloorDeepBlue)$")
WATCH = re.compile(r"Flame|LavaBubble|LavaHardened|LavaFountain|FireGrate|Rock\d|TreeSnowCovered|IceCrack|CaveRock|Stalagmite|"
                   r"Mushroom|CaveBoulders|SpiderWeb|Bone|Skull|Straw|MineCrystal|Torch|FlameBasin|ColorLight|Obelisk|"
                   r"Brick$|PitCrumbling|Spike|BlackPowder|GrassTuft")


def one(name):
    m = md.load(md.corpus_json(name))
    near_wall = set()
    for (x, y) in m.walls:
        for a in (-1, 0, 1):
            for b in (-1, 0, 1): near_wall.add((x + a, y + b))
    ctx_tiles = collections.Counter()
    floor_of = {}
    for (x, y), t in m.tiles.items():
        mat = t["material"]
        for c in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)): floor_of[c] = mat
    for c, mat in floor_of.items():
        ctx_tiles["liquid" if LIQUID.match(mat) else "wall" if c in near_wall else "open"] += 1
    counts = collections.Counter()
    for o in m.objects:
        if not WATCH.search(o["type"]): continue
        c = m.cell_of(o["x"], o["y"])
        mat = floor_of.get(c)
        if mat is None: ctx = "void"
        elif LIQUID.match(mat): ctx = "liquid"
        elif c in near_wall: ctx = "wall"
        else: ctx = "open"
        counts[(o["type"], ctx)] += 1
    return name, ctx_tiles, counts


def main():
    env = json.load(open(os.path.join(HERE, "out", "environments.json")))["maps"]
    names = [n for n, _ in md.campaign_corpus_maps()]
    seen, chosen = set(), []
    for n in sorted(names):
        k = layout_key(n)
        if k in seen: continue
        seen.add(k); chosen.append(n)
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(6) as pool:
        res = list(pool.map(one, [n for n in chosen if env.get(n, {}).get("type") in ("ice", "lava", "cave")]))
    out = {}
    for biome in ("ice", "lava", "cave"):
        tiles, counts = collections.Counter(), collections.Counter()
        for name, ct, cn in res:
            if env[name]["type"] != biome: continue
            tiles.update(ct); counts.update(cn)
        types = collections.defaultdict(dict)
        for (t, ctx), n in counts.items():
            types[t][ctx] = dict(n=n, per100=round(100 * n / max(1, tiles[ctx]) * 4, 3))   # per 100 floor tiles (4 cells)
        out[biome] = dict(context_cells=dict(tiles), types=dict(types))
        print(f"\n=== {biome}: cells {dict(tiles)}")
        for t, d in sorted(types.items(), key=lambda kv: -sum(v['n'] for v in kv[1].values()))[:40]:
            print(f"  {t:24s} " + "  ".join(f"{ctx}:{v['n']}({v['per100']})" for ctx, v in sorted(d.items())))
    with open(os.path.join(HERE, "out", "biome_places.json"), "w") as f: json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
