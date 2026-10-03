"""Mines water and crossing rules from the reference corpus:

1. Water materials and where they are used (deep / shallow / plain / swamp, NoTeleport variants).
2. Water bodies: sizes, shore structure (distance of each water material from land), stream widths.
3. Walls on water: where invisible and visible walls sit relative to the shore.
4. Crossings: floor bridges and natural fords (non-water strips with water on both sides) and the
   object kits Dock*, RopeBridge*, StoneBridge*, LavaBridge* (piece order, spacing, orientation).

Writes rules/out/water.json and rules/sections/water.md. Run: py rules/water.py
"""
import math, re, statistics
from collections import Counter, defaultdict, deque
import common as C
from floors import family

SIDE = C.EDGE_SIDES
TILE_STEP_CELLS = math.sqrt(2)      # distance between side-neighbour tile centres, in grid cells
KIT_RX = re.compile(r"^(Dock(?:Up|Down)|RopeBridge(?:Broken)?\d|StoneBridge\d|LavaBridge\d)(.*)$")
CONSTRUCTED = {"interior_wood", "brick", "cobble", "dungeon_stone", "tile", "interior_rug"}


def is_water(mat):
    return mat.startswith("Water")


def water_kind(mat):
    if "Swamp" in mat: return "swamp_deep" if "Deep" in mat else "swamp_shallow"
    if "Deep" in mat: return "deep"
    if "Shallow" in mat: return "shallow"
    return "plain"


def pct(xs, ps=(10, 25, 50, 75, 90)):
    if not xs: return {}
    xs = sorted(xs)
    return {f"p{p}": xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))] for p in ps}


def wpct(pairs, ps=(10, 25, 50, 75, 90)):
    """Weighted percentiles of (value, weight)."""
    pairs = sorted(p for p in pairs if p[1] > 0)
    if not pairs: return {}
    tot = sum(w for _, w in pairs); out = {}
    for p in ps:
        acc = 0
        for v, w in pairs:
            acc += w
            if acc >= p / 100 * tot: out[f"p{p}"] = v; break
    return out


def mine_bodies():
    W = C.sp_weights(); cats = C.map_categories()
    mat_use = defaultdict(lambda: dict(all=0, sp_w=0.0, maps=set(), cats=Counter()))
    dist_by_kind = defaultdict(list)          # kind -> [(distance, weight)]
    bodies = []                                # dicts
    wall_on_water = Counter(); wall_on_water_sp = Counter(); wall_dist = defaultdict(list)
    shore_fence = Counter()                    # shore tiles fenced by wall vs not (sp weighted)
    for m in C.all_maps():
        t = C.tiles(m); w = W.get(m, 0.0)
        water = {p for p, v in t.items() if is_water(v["material"])}
        if not water: continue
        for p in water:
            mat = t[p]["material"]; u = mat_use[mat]
            u["all"] += 1; u["sp_w"] += w; u["maps"].add(m); u["cats"][cats[m]] += 1
        # distance from land (BFS from water tiles touching non-water or void)
        dist = {}; dq = deque()
        for (x, y) in water:
            if any((x + dx, y + dy) not in water for dx, dy in SIDE.values()):
                dist[(x, y)] = 1; dq.append((x, y))
        while dq:
            x, y = dq.popleft()
            for dx, dy in SIDE.values():
                q = (x + dx, y + dy)
                if q in water and q not in dist:
                    dist[q] = dist[(x, y)] + 1; dq.append(q)
        if w:
            for p in water: dist_by_kind[water_kind(t[p]["material"])].append((dist.get(p, 0), w))
        # bodies
        seen = set()
        for p in water:
            if p in seen: continue
            comp = []; dq = deque([p]); seen.add(p)
            while dq:
                x, y = dq.popleft(); comp.append((x, y))
                for dx, dy in SIDE.values():
                    q = (x + dx, y + dy)
                    if q in water and q not in seen: seen.add(q); dq.append(q)
            ds = [dist[c] for c in comp]
            maxd = max(ds)
            ridge = [dist[c] for c in comp if all(dist.get((c[0] + dx, c[1] + dy), 0) <= dist[c] for dx, dy in SIDE.values())]
            kinds = Counter(water_kind(t[c]["material"]) for c in comp)
            elong = len(comp) / max(1, (2 * maxd - 1) ** 2)
            bodies.append(dict(map=m, sp_weight=w, tiles=len(comp), max_dist=maxd,
                               width_tiles=2 * statistics.median(ridge) - 1 if ridge else 1,
                               kinds=dict(kinds), elongation=round(elong, 2), stream=elong > 6 and len(comp) >= 40))
        # walls over water: wall cell (x, y) is covered by tiles (x, y) and (x-1, y-1)
        walls = C.walls(m)
        for (x, y), wl in walls.items():
            a = t.get((x, y)); b = t.get((x - 1, y - 1))
            wa = a and is_water(a["material"]); wb = b and is_water(b["material"])
            if not (wa or wb): continue
            kind = "invisible" if "Invisible" in wl["material"] else "visible"
            where = "on_water" if wa and wb else ("shore_edge" if (a and b) else "water_by_void")
            wall_on_water[(kind, where)] += 1; wall_on_water_sp[(kind, where)] += w
            d = min(dist.get((x, y), 99), dist.get((x - 1, y - 1), 99))
            if w and d < 99: wall_dist[kind].append((d, w))
            if w: wall_dist[kind + ":" + wl["material"]].append((d, w))
        if w:
            wall_cells = set(walls)
            for p in water:
                if dist.get(p) != 1: continue
                fenced = any(c in wall_cells for c in ((p[0], p[1]), (p[0] + 1, p[1] + 1), (p[0] + 1, p[1] - 1), (p[0] - 1, p[1] + 1), (p[0] - 1, p[1] - 1)))
                shore_fence[fenced] += w
    return dict(mat_use=mat_use, dist_by_kind=dist_by_kind, bodies=bodies, wall_on_water=wall_on_water,
                wall_on_water_sp=wall_on_water_sp, wall_dist=wall_dist, shore_fence=shore_fence)


def crossing_tiles(t, water, p, axis):
    """Width of a land strip through p across water along `axis` ('EW' or 'NS'), else None."""
    d1, d2 = (SIDE["E"], SIDE["W"]) if axis == "EW" else (SIDE["N"], SIDE["S"])
    out = []
    for dx, dy in (d1, d2):
        x, y = p
        for k in range(1, 6):
            x += dx; y += dy
            q = (x, y)
            if q in water: out.append(k); break
            if q not in t: return None
        else:
            return None
    width = out[0] + out[1] - 1
    return width if width <= 6 else None


def mine_crossings():
    W = C.sp_weights()
    found = []
    for m in C.all_maps():
        t = C.tiles(m); w = W.get(m, 0.0)
        water = {p for p, v in t.items() if is_water(v["material"])}
        if not water: continue
        cand = {}
        for p, v in t.items():
            if p in water: continue
            near = any((p[0] + dx, p[1] + dy) in water for dx, dy in SIDE.values())
            for axis in ("EW", "NS"):
                wd = crossing_tiles(t, water, p, axis)
                if wd:
                    cand[p] = (axis, wd); break
        seen = set()
        run_dir = {"EW": (SIDE["N"], SIDE["S"]), "NS": (SIDE["E"], SIDE["W"])}
        for p, (axis, wd) in cand.items():
            if p in seen: continue
            comp = []; dq = deque([p]); seen.add(p)
            while dq:
                c = dq.popleft(); comp.append(c)
                for dx, dy in SIDE.values():
                    q = (c[0] + dx, c[1] + dy)
                    if q in cand and q not in seen and cand[q][0] == axis: seen.add(q); dq.append(q)
            if len(comp) < 2: continue
            mats = Counter(t[c]["material"] for c in comp)
            fams = Counter(family(t[c]["material"]) for c in comp)
            main_fam = fams.most_common(1)[0][0]
            # length along the running direction: projection onto run direction vector
            rdx, rdy = run_dir[axis][0]
            proj = [c[0] * rdx + c[1] * rdy for c in comp]
            length = (max(proj) - min(proj)) // 2 + 1
            widths = Counter(cand[c][1] for c in comp)
            edges = Counter((e[0], e[3]) for c in comp for e in t[c]["edges"])
            # land beyond each end
            ends = Counter()
            for c in comp:
                for dx, dy in run_dir[axis]:
                    q = (c[0] + dx, c[1] + dy)
                    if q in t and q not in cand and q not in water: ends[t[q]["material"]] += 1
            found.append(dict(map=m, sp_weight=w, tiles=len(comp), length_tiles=length,
                              width_tiles=widths.most_common(1)[0][0],
                              kind="bridge" if main_fam in CONSTRUCTED else "ford",
                              materials=dict(mats.most_common(4)), edges=dict(Counter({f"{a}|{b}": n for (a, b), n in edges.items()}).most_common(4)),
                              end_materials=dict(ends.most_common(3)),
                              water=dict(Counter(t[q]["material"] for c in comp for dx, dy in SIDE.values()
                                                 for q in [(c[0] + dx, c[1] + dy)] if q in water).most_common(2))))
    return found


def mine_kits():
    chains = []
    for m in C.all_maps():
        objs = [o for o in C.objects(m) if KIT_RX.match(o["type"])]
        if not objs: continue
        walls = C.walls(m); t = C.tiles(m)
        # single-linkage clusters within 70 px
        left = list(range(len(objs))); groups = []
        while left:
            g = [left.pop()]; i = 0
            while i < len(g):
                a = objs[g[i]]
                near = [j for j in left if math.hypot(objs[j]["x"] - a["x"], objs[j]["y"] - a["y"]) <= 70]
                for j in near: left.remove(j); g.append(j)
                i += 1
            groups.append([objs[j] for j in g])
        for g in groups:
            base = Counter(KIT_RX.match(o["type"])[1] for o in g).most_common(1)[0][0]
            fronts = [o for o in g if o["type"].endswith("Front")]
            backs = [o for o in g if o["type"].endswith("Back")]
            pair_off = []
            for f in fronts:
                stem = f["type"][:-5]
                bs = [b for b in backs if b["type"][:-4] == stem]
                if bs:
                    b = min(bs, key=lambda b: math.hypot(b["x"] - f["x"], b["y"] - f["y"]))
                    pair_off.append((round(b["x"] - f["x"], 1), round(b["y"] - f["y"], 1)))
            units = fronts if fronts else g   # one unit per Front piece (docks have no Front/Back)
            # principal direction from first to last unit
            xs = [o["x"] for o in units]; ys = [o["y"] for o in units]
            if len(units) > 1:
                # order along the longest spread
                span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
                key = (lambda o: o["x"]) if span_x >= span_y else (lambda o: o["y"])
                units = sorted(units, key=key)
            seq = [KIT_RX.match(o["type"])[2].replace("Front", "") for o in units]
            steps = [(round(b["x"] - a["x"], 1), round(b["y"] - a["y"], 1)) for a, b in zip(units, units[1:])]
            under = Counter()
            for o in g:
                tu = C.tile_under(m, o["x"], o["y"])
                under[t[tu]["material"] if tu else "(void)"] += 1
            wall_near = Counter()
            for o in g:
                cx, cy = int(o["x"] // C.CELL), int(o["y"] // C.CELL)
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        if (cx + dx, cy + dy) in walls: wall_near[walls[(cx + dx, cy + dy)]["material"]] += 1
            near = [o for o in units if "Near" in o["type"]]; far = [o for o in units if "Far" in o["type"]]
            near_far = None
            if near and far:
                dx, dy = far[0]["x"] - near[0]["x"], far[0]["y"] - near[0]["y"]
                n = math.hypot(dx, dy) or 1
                near_far = (round(dx / n, 1), round(dy / n, 1))
            chains.append(dict(map=m, kit=base, pieces=len(g), sequence=seq, steps=steps, front_back_offsets=pair_off,
                               near_to_far_direction=near_far,
                               start=[round(units[0]["x"], 1), round(units[0]["y"], 1)],
                               floor_under=dict(under.most_common(3)), walls_near=dict(wall_near.most_common(3))))
    return chains


def summarize(b, crossings, chains):
    mat_use = {k: dict(tiles_all=v["all"], sp_weighted=round(v["sp_w"], 1), maps=len(v["maps"]), categories=dict(v["cats"]))
               for k, v in sorted(b["mat_use"].items(), key=lambda kv: -kv[1]["all"])}
    shore = {k: dict(distance_from_land_weighted=wpct(v), mean=round(sum(d * w for d, w in v) / sum(w for _, w in v), 2))
             for k, v in b["dist_by_kind"].items()}
    sp_bodies = [x for x in b["bodies"] if x["sp_weight"] > 0 and x["tiles"] >= 4]
    streams = [x for x in sp_bodies if x["stream"]]
    pools = [x for x in sp_bodies if not x["stream"]]
    bodies = dict(
        sp_bodies=len(sp_bodies), streams=len(streams), pools_lakes=len(pools),
        size_tiles=wpct([(x["tiles"], x["sp_weight"]) for x in sp_bodies]),
        stream_width_tiles=wpct([(x["width_tiles"], x["sp_weight"]) for x in streams]),
        stream_width_cells=wpct([(round(x["width_tiles"] * TILE_STEP_CELLS, 1), x["sp_weight"]) for x in streams]),
        stream_max_width_tiles=wpct([(2 * x["max_dist"] - 1, x["sp_weight"]) for x in streams]),
        stream_sizes_tiles=wpct([(x["tiles"], x["sp_weight"]) for x in streams]),
        lake_max_depth_tiles=wpct([(x["max_dist"], x["sp_weight"]) for x in pools]),
        stream_composition=dict(Counter(k for x in streams for k in x["kinds"] for _ in [0])),
        note="width = 2 * median ridge distance - 1, in tiles across (1 tile ~ 1.41 cells); stream = elongation > 6 and >= 40 tiles")
    walls = dict(
        counts_all={f"{k}:{w}": n for (k, w), n in b["wall_on_water"].most_common()},
        counts_sp_weighted={f"{k}:{w}": round(n, 1) for (k, w), n in b["wall_on_water_sp"].most_common()},
        distance_from_land={k: wpct(v) for k, v in b["wall_dist"].items() if ":" not in k},
        materials_on_water={k.split(":", 1)[1]: round(sum(w for _, w in v), 1)
                            for k, v in sorted(b["wall_dist"].items(), key=lambda kv: -sum(w for _, w in kv[1])) if ":" in k},
        shore_tiles_with_wall_share_sp=round(b["shore_fence"][True] / max(1e-9, sum(b["shore_fence"].values())), 3),
        note="a wall cell (x,y) is covered by floor tiles (x,y) and (x-1,y-1); distance 1 = water tile touching land")
    sp_cross = [c for c in crossings if c["sp_weight"] > 0]
    cross = {}
    for kind in ("bridge", "ford"):
        cs = [c for c in sp_cross if c["kind"] == kind]
        mats = Counter(); ends = Counter(); edges = Counter(); wat = Counter()
        for c in cs:
            for k, n in c["materials"].items(): mats[k] += n * c["sp_weight"]
            for k, n in c["end_materials"].items(): ends[k] += n * c["sp_weight"]
            for k, n in c["edges"].items(): edges[k] += n * c["sp_weight"]
            for k, n in c["water"].items(): wat[k] += n * c["sp_weight"]
        tot = lambda c: sum(c.values()) or 1e-9
        cross[kind] = dict(
            count_sp=len(cs), length_tiles=wpct([(c["length_tiles"], c["sp_weight"]) for c in cs]),
            width_tiles=wpct([(c["width_tiles"], c["sp_weight"]) for c in cs]),
            materials={k: round(v / tot(mats), 3) for k, v in mats.most_common(8)},
            end_materials={k: round(v / tot(ends), 3) for k, v in ends.most_common(6)},
            edges_on_crossing={k: round(v / tot(edges), 3) for k, v in edges.most_common(6)},
            water_beside={k: round(v / tot(wat), 3) for k, v in wat.most_common(4)},
            examples=[dict(map=c["map"], tiles=c["tiles"], length=c["length_tiles"], width=c["width_tiles"], materials=c["materials"])
                      for c in sorted(cs, key=lambda c: -c["tiles"])[:6]])
    kits = defaultdict(lambda: dict(chains=0, maps=set(), sequences=Counter(), steps=Counter(), front_back=Counter(),
                                    floor_under=Counter(), walls_near=Counter(), length=Counter(), dirs=Counter()))
    for ch in chains:
        k = kits[ch["kit"]]
        k["chains"] += 1; k["maps"].add(ch["map"]); k["length"][len(ch["sequence"])] += 1
        k["sequences"][" > ".join(ch["sequence"])] += 1
        for s in ch["steps"]: k["steps"][s] += 1
        for s in ch["front_back_offsets"]: k["front_back"][s] += 1
        for f, n in ch["floor_under"].items(): k["floor_under"][f] += n
        for f, n in ch["walls_near"].items(): k["walls_near"][f] += n
        if ch["near_to_far_direction"]: k["dirs"][ch["near_to_far_direction"]] += 1
    kits_out = {name: dict(chains=v["chains"], maps=sorted(v["maps"]), units_per_chain=dict(v["length"].most_common()),
                           sequences=dict(v["sequences"].most_common(6)),
                           step_offsets_px={f"{a},{b}": n for (a, b), n in v["steps"].most_common(6)},
                           front_back_offset_px={f"{a},{b}": n for (a, b), n in v["front_back"].most_common(4)},
                           floor_under=dict(v["floor_under"].most_common(5)), walls_near=dict(v["walls_near"].most_common(4)),
                           near_to_far_direction={f"{a},{b}": n for (a, b), n in v["dirs"].most_common(4)})
                for name, v in sorted(kits.items())}
    return dict(water_materials=mat_use, shore_structure=shore, bodies=bodies, walls_on_water=walls,
                crossings=cross, kits=kits_out,
                kit_examples=[c for c in chains if c["map"] in ("G_Swamp", "Con05A", "Con08e", "G_Lava")][:12])


def md(d):
    L = ["# Water and crossings", "",
         "Schema of `rules/out/water.json`:",
         "- `water_materials{material: tiles_all, sp_weighted, maps, categories}`",
         "- `shore_structure{kind: distance_from_land_weighted percentiles, mean}`: kind = deep / shallow / plain / swamp_*; "
         "distance 1 = water tile touching land, counted in tile steps.",
         "- `bodies{}`: single-player water bodies; size, stream width (tiles and cells), lake depth, composition.",
         "- `walls_on_water{}`: walls whose cell is covered by water tiles; invisible vs visible; distance from land; shore fencing share.",
         "- `crossings{bridge|ford: count_sp, length_tiles, width_tiles, materials, end_materials, edges_on_crossing, water_beside, examples}`",
         "- `kits{kit: chains, maps, units_per_chain, sequences, step_offsets_px, front_back_offset_px, floor_under, walls_near}` and `kit_examples[]`.", ""]
    L += ["## Water materials", ""]
    for k, v in d["water_materials"].items():
        L.append(f"- {k}: {v['tiles_all']} tiles in {v['maps']} maps, categories {v['categories']}")
    L += ["", "## Shore structure (single-player, distance from land in tile steps)", ""]
    for k, v in d["shore_structure"].items():
        L.append(f"- {k}: {v['distance_from_land_weighted']} (mean {v['mean']})")
    b = d["bodies"]
    L += ["", "## Water bodies", "",
          f"- {b['sp_bodies']} single-player bodies: {b['streams']} streams, {b['pools_lakes']} pools/lakes. Size (tiles): {b['size_tiles']}.",
          f"- Stream width: typical {b['stream_width_tiles']} tiles = {b['stream_width_cells']} cells; widest point {b['stream_max_width_tiles']} tiles; size {b['stream_sizes_tiles']} tiles.",
          f"- Lake depth (max distance from shore, tiles): {b['lake_max_depth_tiles']}.", ""]
    w = d["walls_on_water"]
    L += ["## Walls on water", "",
          f"- Counts (all maps): {w['counts_all']}.",
          f"- Distance of wall from land: {w['distance_from_land']}.",
          f"- Wall materials on water (weighted): {dict(list(w['materials_on_water'].items())[:8])}.",
          f"- Share of shore tiles fenced by a wall: {w['shore_tiles_with_wall_share_sp']:.0%}.", ""]
    L += ["## Crossings (floor)", ""]
    for kind, v in d["crossings"].items():
        L += [f"### {kind} ({v['count_sp']} in single-player maps)", "",
              f"- Length {v['length_tiles']} tiles, width {v['width_tiles']} tiles.",
              f"- Materials: {v['materials']}.", f"- Land at the ends: {v['end_materials']}.",
              f"- Edges on the crossing (overlay|type): {v['edges_on_crossing']}.", f"- Water beside: {v['water_beside']}.",
              "- Examples: " + "; ".join(f"{e['map']} {e['length']}x{e['width']} {list(e['materials'])[:2]}" for e in v["examples"]), ""]
    L += ["## Crossing kits (objects)", ""]
    for k, v in d["kits"].items():
        L += [f"### {k}: {v['chains']} chains in {len(v['maps'])} maps", "",
              f"- Units per chain: {v['units_per_chain']}. Sequences: {v['sequences']}.",
              f"- Step between units (px): {v['step_offsets_px']}. Front->Back offset (px): {v['front_back_offset_px']}.",
              f"- Floor under: {v['floor_under']}. Walls near: {v['walls_near']}.",
              f"- Direction NearEnd -> FarEnd (unit vector, screen x/y): {v['near_to_far_direction']}.", ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    data = summarize(mine_bodies(), mine_crossings(), mine_kits())
    C.save_json("water.json", data)
    C.save_section("water.md", md(data))
    print("water: bodies", data["bodies"]["sp_bodies"], "| bridges", data["crossings"]["bridge"]["count_sp"],
          "| fords", data["crossings"]["ford"]["count_sp"], "| kits", {k: v["chains"] for k, v in data["kits"].items()})
