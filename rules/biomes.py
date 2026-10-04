"""What sets Westwood's biomes apart: the floors, walls, objects, lights and creatures of its ice, lava and cave
maps against all its other single-player maps (rules/out/environments.json types every map).

For each biome:
- floors and walls by share;
- the signature objects: those far denser in the biome than elsewhere (lift = density in the biome / density in the
  other maps), with the maps that use them;
- lights per 100 floor tiles, the ambient colour and the coloured lights' colours;
- creatures by kind and density.
Writes rules/out/biomes.json; prints a summary. Distinct layouts only (a layout shipped for the three classes counts
once).

    py rules/biomes.py
"""
import collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, "validate"))
import mapdata as md

BIOMES = ("ice", "lava", "cave")
SKIP = re.compile(r"Door|Waypoint|PlayerStart|^Amb|Trigger|Sound|ExtentBox|RewardMarker|Mover$|Glyph|Spell|Teleport|"
                  r"Start$|Invisible|Pressure|Switch|Lever|Button|Elevator")


_GROUPS = None


def layout_key(name):
    """Westwood ships some layouts for the three classes (Con09d, War09d, Wiz09d): count each layout once, by the
    corpus's layout groups (corpus/out/nox_corpus.db layout_group)."""
    global _GROUPS
    if _GROUPS is None:
        import sqlite3
        db = sqlite3.connect(os.path.join(REPO, "corpus", "out", "nox_corpus.db"))
        _GROUPS = dict(db.execute("SELECT map, rep FROM layout_group"))
    return _GROUPS.get(name, name)


def one(name):
    m = md.load(md.corpus_json(name))
    floors = collections.Counter(t["material"] for t in m.tiles.values())
    walls = collections.Counter(w.material for w in m.walls.values())
    objs, mons, lights, colours = collections.Counter(), collections.Counter(), 0, collections.Counter()
    for o in m.objects:
        c = o["cls"]
        if "MONSTER" in c:
            mons[o["type"]] += 1; continue
        if any(k in c for k in ("WEAPON", "ARMOR", "FOOD", "KEY", "READABLE", "MISSILE", "PLAYER", "FLAG", "TREASURE")):
            continue
        if o["xtype"] in ("NPCXfer", "DoorXfer", "MonsterXfer") or SKIP.search(o["type"]): continue
        if "LIGHT" in c or o["type"] == "ColorLight":
            lights += 1
            if o["type"] == "ColorLight":
                x = o["xfer"] or {}
                if "R" in x: colours[(int(x["R"]) // 32 * 32, int(x["G"]) // 32 * 32, int(x["B"]) // 32 * 32)] += 1
        objs[o["type"]] += 1
    # region light: the polygons' ambient colours, weighted by their area
    regions = collections.Counter()
    for p in m.polygons:
        pts = p.get("pts") or []
        area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))) / 2 / (23 * 23)
        amb = p.get("amb")
        if amb and area: regions[tuple(int(v) // 16 * 16 for v in amb)] += area
    return name, dict(tiles=len(m.tiles), floors=floors, walls=walls, objs=objs, mons=mons, lights=lights,
                      colours=colours, ambient=m.ambient, regions=regions)


def main():
    env = json.load(open(os.path.join(HERE, "out", "environments.json")))["maps"]
    from concurrent.futures import ProcessPoolExecutor
    names = [n for n, _ in md.sp_corpus_maps()]
    seen, chosen = set(), []
    for n in sorted(names):                                   # one map per layout
        k = layout_key(n)
        if k in seen: continue
        seen.add(k); chosen.append(n)
    with ProcessPoolExecutor(6) as pool:
        data = dict(pool.map(one, chosen))
    groups = collections.defaultdict(list)
    for n in chosen: groups[env.get(n, {}).get("type", "?")].append(n)
    out = {}
    for b in BIOMES:
        inside = groups[b]; others = [n for n in chosen if n not in inside]
        tiles_in = sum(data[n]["tiles"] for n in inside) or 1
        tiles_out = sum(data[n]["tiles"] for n in others) or 1
        fl, wa, ob, mo, col, reg = (collections.Counter() for _ in range(6))
        ob_out = collections.Counter(); used_in = collections.defaultdict(set)
        for n in inside:
            d = data[n]
            fl.update(d["floors"]); wa.update(d["walls"]); ob.update(d["objs"]); mo.update(d["mons"]); col.update(d["colours"])
            reg.update(d["regions"])
            for t in d["objs"]: used_in[t].add(n)
        for n in others: ob_out.update(data[n]["objs"])
        fsum, wsum = sum(fl.values()) or 1, sum(wa.values()) or 1
        sig = []
        for t, c in ob.items():
            dens_in = 100 * c / tiles_in
            dens_out = 100 * ob_out[t] / tiles_out
            lift = dens_in / dens_out if dens_out else float("inf")
            if c >= 5 and len(used_in[t]) >= 1 and (lift >= 3 or dens_out == 0):
                sig.append(dict(type=t, n=c, per100=round(dens_in, 3), lift=None if lift == float("inf") else round(lift, 1),
                                maps=sorted(used_in[t])))
        sig.sort(key=lambda s: -s["n"])
        out[b] = dict(maps=inside, tiles=tiles_in,
                      floors=[(k, round(v / fsum, 3)) for k, v in fl.most_common(15)],
                      walls=[(k, round(v / wsum, 3)) for k, v in wa.most_common(12)],
                      objects=[(k, v, round(100 * v / tiles_in, 3)) for k, v in ob.most_common(40)],
                      signature=sig[:60],
                      creatures=[(k, v, round(100 * v / tiles_in, 3)) for k, v in mo.most_common(25)],
                      creatures_per100=round(100 * sum(mo.values()) / tiles_in, 2),
                      lights_per100=round(100 * sum(data[n]["lights"] for n in inside) / tiles_in, 2),
                      ambient={n: data[n]["ambient"] for n in inside},
                      light_colours=[(list(k), v) for k, v in col.most_common(8)],
                      region_ambient=[(list(k), round(v)) for k, v in reg.most_common(8)])
    # the other environments, for contrast
    out["_contrast"] = {}
    for e in ("town", "forest", "dungeon", "castle", "swamp"):
        ns = groups[e]; tl = sum(data[n]["tiles"] for n in ns) or 1
        out["_contrast"][e] = dict(maps=len(ns), creatures_per100=round(100 * sum(sum(data[n]["mons"].values()) for n in ns) / tl, 2),
                                   lights_per100=round(100 * sum(data[n]["lights"] for n in ns) / tl, 2),
                                   ambient=collections.Counter(tuple(data[n]["ambient"]) for n in ns).most_common(3))
    with open(os.path.join(HERE, "out", "biomes.json"), "w") as f: json.dump(out, f, indent=1)
    for b in BIOMES:
        r = out[b]
        print(f"\n=== {b}: {len(r['maps'])} layouts {r['maps']} ({r['tiles']} tiles)")
        print("  floors:", ", ".join(f"{k} {v:.2f}" for k, v in r["floors"][:10]))
        print("  walls: ", ", ".join(f"{k} {v:.2f}" for k, v in r["walls"][:8]))
        print("  lights/100:", r["lights_per100"], " creatures/100:", r["creatures_per100"], " ambient:", r["ambient"])
        print("  light colours:", r["light_colours"][:6])
        print("  region ambient (by area):", r["region_ambient"][:6])
        print("  creatures:", ", ".join(f"{k} {v}" for k, v, _ in r["creatures"][:15]))
        print("  signature:", ", ".join(f"{s['type']}({s['n']}, x{s['lift']})" for s in r["signature"][:30]))
        print("  top objects:", ", ".join(f"{k}({v})" for k, v, _ in r["objects"][:25]))
    print("\ncontrast:", json.dumps(out["_contrast"]))


if __name__ == "__main__":
    main()
