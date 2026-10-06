"""Westwood's campaign scenes for the scene lab: found on the campaign maps (Con/War/Wiz only, never the quest or
multiplayer maps; common.campaign_maps) by each type's signature (scenecat.py), measured by the same code that measures
ours (metrics.features), and rendered as the lab renders ours (labrender.py).

    py review/scenelab/labref.py index               find and measure every scene (writes westwood_scenes.json)
    py review/scenelab/labref.py list                each type's scenes: map, place, pieces
    py review/scenelab/labref.py gallery [type ...]  render each type's scenes (cached in review/out/scenelab/_westwood)

A layout the three class campaigns share (Con05A, War05A...) is one place: its scenes are kept once (the first map's),
with the other maps listed, and weigh as one.
"""
import collections, json, math, os, re, sys
import labenv as E
import scenecat as K
import pieces as P

ENVS = ("town", "forest", "swamp", "ice", "castle")
WATERISH = re.compile(r"Water|WoodGray|WoodSlat|Wood")


def campaign_maps():
    import common
    env = json.load(open(os.path.join(E.REPO, "rules", "out", "environments.json"), encoding="utf-8"))["maps"]
    return [(m, env.get(m, {}).get("type")) for m in common.campaign_maps() if env.get(m, {}).get("type") in ENVS]


def layout_rep():
    import sqlite3
    with sqlite3.connect(os.path.join(E.REPO, "corpus", "out", "nox_corpus.db")) as c:
        return {m: r for m, r in c.execute("SELECT map, rep FROM layout_group")}


def outdoor_floor(m, x, y, water=False, ground=None):
    """Whether the ground under a point is outdoor ground (grass, dirt, swamp, snow, paving), or water and planks for a
    scene on the water (a dock)."""
    import decoration as D
    f = m.floor_at(x, y)
    if not f: return False
    if water and WATERISH.search(f): return True
    fam = D.family(f)
    if fam in ("interior", "dungeon", "cave", "lava", "water"): return False
    if ground and fam not in ground and not (fam == "other" and "ice" in ground and "Ice" in f): return False
    return not re.search(r"Wood|Rug|Tile|Checker|Carpet|Marble", f)


def find_scenes(m, env):
    """[scene record] of one Westwood map: each type's scenes, claimed in catalog.ORDER."""
    objs = m.objects
    claimed = set()
    out = []
    for typ in K.ORDER:
        spec = K.SCENES[typ]
        rx = re.compile(spec["sig"])
        sig = []
        for o in objs:
            if o["id"] in claimed or not rx.match(o["type"]): continue
            if spec.get("creatures"):
                if not P.creature(o): continue
            elif spec.get("doors"):
                if "DOOR" not in o["cls"] and o["xtype"] != "DoorXfer": continue
            if not outdoor_floor(m, o["x"], o["y"], spec.get("water"), spec.get("ground")): continue
            sig.append(o)
        # signature objects within `link` of each other are one scene's seeds
        groups, left = [], list(sig)
        while left:
            g = [left.pop()]
            grew = True
            while grew:
                grew = False
                for o in list(left):
                    if any(math.hypot(o["x"] - q["x"], o["y"] - q["y"]) <= spec["link"] for q in g):
                        g.append(o); left.remove(o); grew = True
            groups.append(g)
        for g in groups:
            if len(g) < spec.get("min_seeds", 1): continue
            cand = [o for o in objs if o["id"] not in claimed and P.piece(o) and
                    outdoor_floor(m, o["x"], o["y"], spec.get("water"))]
            pcs = [(o["type"], o["x"], o["y"]) for o in cand]
            idx = P.grow(pcs, [(o["x"], o["y"]) for o in g], spec["link"], spec["radius"])
            mem = [cand[i] for i in idx]
            if not spec.get("creatures") and not spec.get("doors"):     # the signature itself is a piece (a well)
                mem += [o for o in g if o["id"] not in {q["id"] for q in mem}]
            ids = {o["id"] for o in mem} | {o["id"] for o in g}
            types = [o["type"] for o in mem]
            if spec.get("co") and not any(re.search(spec["co"], t) for t in types): continue
            if spec.get("not_with") and any(re.search(spec["not_with"], t) for t in types): continue
            if len(mem) < spec["min_pieces"]: continue
            claimed |= ids
            seeds = [(round(o["x"], 1), round(o["y"], 1)) for o in g]
            out.append(dict(type=typ, map=m.name, env=env, seeds=seeds,
                            anchor=[round(sum(x for x, _ in seeds) / len(seeds), 1),
                                    round(sum(y for _, y in seeds) / len(seeds), 1)],
                            pieces=[[o["type"], round(o["x"], 1), round(o["y"], 1)] for o in mem]))
    return out


def _index_map(args):
    name, env = args
    import metrics
    m = E.MD.load(E.MD.corpus_json(name))
    res = []
    for s in find_scenes(m, env):
        s["features"], s["details"] = metrics.features(m, s)
        res.append(s)
    return name, res


def build_index(log=print):
    """Finds and measures every Westwood campaign scene; writes review/scenelab/westwood_scenes.json."""
    from concurrent.futures import ProcessPoolExecutor
    maps = campaign_maps()
    rep = layout_rep()
    with ProcessPoolExecutor(6) as pool:
        found = dict(pool.map(_index_map, maps))
    scenes, seen = [], {}
    for name, env in maps:
        for s in found[name]:
            key = (rep.get(name, name), s["type"], round(s["anchor"][0] / 60), round(s["anchor"][1] / 60))
            # the same place in two layout groups (Galava's yard in Con07B and War07A): its anchor and pieces match
            twin = next((t for t in scenes if t["type"] == s["type"] and abs(len(t["pieces"]) - len(s["pieces"])) <= 4 and
                         math.hypot(t["anchor"][0] - s["anchor"][0], t["anchor"][1] - s["anchor"][1]) < 60), None)
            if key in seen or twin:
                (seen.get(key) or twin)["also"].append(name); continue
            s["also"] = []
            seen[key] = s
            scenes.append(s)
    scenes.sort(key=lambda s: (K.SCENES[s["type"]]["rank"], s["map"], s["anchor"]))
    for k, s in enumerate(scenes): s["id"] = f"{s['type']}_{s['map']}_{int(s['anchor'][0])}_{int(s['anchor'][1])}"
    with open(E.WW_INDEX, "w", encoding="utf-8") as f:
        json.dump(dict(source="Westwood's campaign maps (Con/War/Wiz; rules/common.campaign_maps), outdoor ground, "
                       "found by review/scenelab/scenecat.py signatures", measured_by="review/scenelab/metrics.py features()",
                       scenes=scenes), f, indent=0)
    c = collections.Counter(s["type"] for s in scenes)
    for t in K.ranked(): log(f"  {t:16s} {c.get(t, 0):3d} scenes")
    log(f"{len(scenes)} Westwood scenes -> {E.rel(E.WW_INDEX)}")
    return scenes


_WW = None


def westwood(typ=None):
    global _WW
    if _WW is None:
        with open(E.WW_INDEX, encoding="utf-8") as f: _WW = json.load(f)["scenes"]
    return [s for s in _WW if typ is None or s["type"] == typ]


# ---------------------------------------------------------------------------------------------------- the gallery
def gallery_dir(typ):
    return os.path.join(E.WW_OUT, typ)


def window(typ):
    """The world-px window (w, h) every picture of the type shows: Westwood's scenes of the type fit it (their p80
    reach from the middle plus a margin), 4:3 like the canvas."""
    import labrender as R
    reach = []
    for s in westwood(typ):
        cx, cy = R.centre_of(s)
        reach.append(max([math.hypot(x - cx, y - cy) for _, x, y in s["pieces"]] + [60]))
    reach.sort()
    r = reach[int(0.8 * (len(reach) - 1))] if reach else 220
    half_h = max(230.0, min(560.0, r + 120))
    return (round(half_h * 2 * 4 / 3), round(half_h * 2))


def gallery(typ, log=print):
    """Renders Westwood's scenes of the type into review/out/scenelab/_westwood/<type>/ (cached): one PNG per scene and
    gallery.json. Returns the gallery's record."""
    import labrender as R
    d = gallery_dir(typ)
    meta_path = os.path.join(d, "gallery.json")
    ww = westwood(typ)
    win = window(typ)
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f: meta = json.load(f)
        if meta.get("version") == R.VERSION and meta.get("window") == list(win) and \
                {x["id"] for x in meta["scenes"]} == {s["id"] for s in ww} and \
                all(os.path.exists(os.path.join(d, x["file"])) for x in meta["scenes"]):
            return meta
    os.makedirs(d, exist_ok=True)
    for fn in os.listdir(d): os.remove(os.path.join(d, fn))
    out = []
    for s in ww:
        m = E.MD.load(E.MD.corpus_json(s["map"]))
        full = R.westwood_render(m)
        pic = R.picture(full, s, win)
        fn = s["id"] + ".png"
        pic.save(os.path.join(d, fn))
        out.append(dict(file=fn, id=s["id"], map=s["map"], env=s["env"], anchor=s["anchor"], n=len(s["pieces"])))
        log(f"  {fn}")
    meta = dict(version=R.VERSION, type=typ, window=list(win), scenes=out)
    with open(meta_path, "w", encoding="utf-8") as f: json.dump(meta, f, indent=1)
    return meta


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "index":
        build_index()
    elif a and a[0] == "list":
        for s in westwood():
            if len(a) > 1 and s["type"] not in a[1:]: continue
            c = collections.Counter(P.base(t) for t, _, _ in s["pieces"])
            print(f"{s['type']:14s} {s['map']:7s} ({int(s['anchor'][0])},{int(s['anchor'][1])}) n={len(s['pieces']):3d} "
                  f"{'+' + ','.join(s['also']) if s['also'] else ''}  " + ", ".join(f"{t}x{n}" for t, n in c.most_common(9)))
    elif a and a[0] == "gallery":
        for t in a[1:] or K.ranked():
            g = gallery(t)
            print(f"{t}: {len(g['scenes'])} scenes, window {g['window']}")
    else:
        print(__doc__)
