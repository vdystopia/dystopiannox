"""Environment types of Westwood's campaign maps (town, forest, swamp, cave, dungeon, castle,
ice, lava). Each map is classified from its floors, buildings and outdoor ground, so that statistics
are compared like with like: a town is measured against Westwood's towns, never against the Dismal
Swamp. Writes rules/out/environments.json: map -> type plus the measurements behind it.

    py rules/environments.py          (prints the classification for review)
"""
import collections, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "validate"))
sys.path.insert(0, os.path.join(REPO, "review"))

TYPES = ["town", "forest", "swamp", "cave", "dungeon", "castle", "ice", "lava"]
DESCRIPTIONS = dict(
    town="villages and towns: several buildings on outdoor ground (grass, dirt, cobble)",
    forest="wilderness: outdoor ground with trees and few buildings",
    swamp="swamps and marshes: swamp grass and swamp water",
    cave="caves and mines: cave floors and rock walls",
    dungeon="dungeons, crypts and sewers: stone and brick floors, little or no outdoor ground",
    castle="castles, manors and temples: interior floors (wood, rug, tile, marble) and halls",
    ice="snow and ice", lava="volcanic: lava and craggy rock")


def features(m):
    """Floor make-up, buildings and outdoor share of a MapData."""
    import design as DS
    od = DS.Outdoor(m)
    c = collections.Counter(DS.family(t["material"]) for t in m.tiles.values())
    tot = sum(c.values()) or 1
    share = {k: v / tot for k, v in c.items()}
    swamp = sum(1 for t in m.tiles.values() if "Swamp" in t["material"]) / tot
    return dict(share={k: round(v, 3) for k, v in sorted(share.items(), key=lambda kv: -kv[1])[:6]},
                swamp=round(swamp, 3), buildings=len(od.buildings()), outdoor=round(len(od.ground) / tot, 3),
                trees=len(od.deco["tree"]), tiles=tot)


def classify(f):
    """First match wins; thresholds chosen by reading every map's floors and summary (py rules/environments.py -v)."""
    s = lambda k: f["share"].get(k, 0)
    green = s("grass") + s("swamp") + 0.5 * s("water")
    masonry = s("brick") + s("dungeon_stone") + s("facade")
    indoor = s("interior_wood") + s("interior_rug") + s("tile")
    if s("lava") >= 0.08: return "lava"
    if s("ice") >= 0.2: return "ice"
    if f["swamp"] >= 0.12: return "swamp"
    if f["buildings"] >= 10 and green + s("dirt") + s("cobble") >= 0.3: return "town"     # paved towns (Ix)
    if green >= 0.25: return "town" if f["buildings"] >= 5 else "forest"
    if s("cave") >= 0.2: return "cave"
    if s("dirt") >= 0.4: return "town" if f["buildings"] >= 5 else ("cave" if s("cave") >= 0.1 else "forest")
    if indoor >= 0.15 or s("facade") >= 0.3: return "castle"
    if masonry >= 0.4: return "dungeon"
    return "forest" if green + s("dirt") >= 0.3 else "dungeon"


def _one(name):
    import mapdata as md
    m = md.load(md.corpus_json(name))
    f = features(m)
    return name, m.info.get("summary") or "", f


def main():
    import mapdata as md
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(6) as pool:
        res = list(pool.map(_one, [n for n, _ in md.campaign_corpus_maps()]))
    out = {}
    for name, summary, f in res:
        out[name] = dict(type=classify(f), summary=summary, **f)
    with open(os.path.join(HERE, "out", "environments.json"), "w") as fh:
        json.dump(dict(descriptions=DESCRIPTIONS, maps=out), fh, indent=1, sort_keys=True)
    by = collections.defaultdict(list)
    for n, r in out.items(): by[r["type"]].append(n)
    for t in TYPES:
        print(f"{t:8s} {len(by[t]):3d}  {' '.join(sorted(by[t]))}")
    if "-v" in sys.argv:
        for n, r in sorted(out.items()):
            print(f"  {n:9s} {r['type']:8s} out={r['outdoor']:.2f} bld={r['buildings']:2d} swamp={r['swamp']:.2f} {r['share']}  {r['summary'][:40]}")


if __name__ == "__main__":
    main()
