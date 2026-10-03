"""Phase 2 rule mining: DECORATION and FURNITURE placement.

Reads corpus/out/nox_corpus.db (via common.py) and writes:
  rules/out/decoration.json      machine-readable rules (schema in rules/sections/decoration.md)
  rules/sections/decoration.md   human-readable summary with evidence

Style statistics use single-player maps weighted by common.sp_weights() (a layout shared by the
three class campaigns counts once). The list of valid decoration types uses all 157 maps, plain counts.

Run:  py rules\\decoration.py
"""
import math, re, sys
from collections import Counter, defaultdict, deque
import common as C

# ----------------------------------------------------------------------------- classification
EXCLUDE_CLASS = {"MONSTER", "DOOR", "TRIGGER", "EXIT", "TRANSPORTER", "ELEVATOR", "ELEVATOR_SHAFT", "HOLE",
                 "FOOD", "ARMOR", "WEAPON", "KEY", "WAND", "MONSTERGENERATOR", "READABLE", "FIRE", "NULL",
                 "DANGEROUS", "PICKUP"}
EXCLUDE_NAME = re.compile(r"Trap|Marker|BlackPowder|Potion|Gold|Book|Scroll|Spell|Ability|Glyph|Rune|Key|"
                          r"Reward|Generator|Mover|Spike|Pentagram|Teleport|Elevator|Exit|Lever|Switch|Button|"
                          r"PlayerStart|^Crown$|^Flag|Ball|Invisible(?!.*Block)", re.I)
LIGHT_NAME = re.compile(r"Torch|Flame|Candle|Lantern|Lamp|Sconse|Sconce|Brazier|Basin.*Lit|Vandegraf|Orb|"
                        r"FairyJar|Glow|ColorLight", re.I)
CATEGORIES = [  # (category, regex on type name) - first match wins
    ("blocker", r"^Extent"),
    ("ambient_sound", r"^Amb"),
    ("web", r"Web"),
    ("bones", r"Bone|Skull|Corpse|Skeleton|Rib[Cc]age"),
    ("tree", r"^Tree|Pine|Palm|Willow|^Aspen|^Conifer|^Decidious|^Birch"),
    ("flower_tuft", r"Flower|GrassTuft|Mushroom|Lill?y|Toadstool"),
    ("plant", r"Plant|Bush|Fern|Foliage|Weed|Reed|Cattail|Shrub|Vine|Ivy|Hedge|Cactus|Grass|Moss|Garden"),
    ("log", r"ForestLog|Log\d|Stump|Branch"),
    ("rock", r"Rock|Boulder|Pebble|Stalag|Crystal|StoneBlock|IronBlock|Rubble|LavaHardened"),
    ("furniture", r"Chair|Table|Bed\d|^Bed|Cot\d|Bench|Desk|Bookcase|Shel|Nightstand|Chest|Stool|Throne|Rug|"
                  r"Fireplace|Stove|Wardrobe|Dresser|Cabinet|Workstation|Coffin|Pew|Altar|Couch|Counter|Trader|"
                  r"Loom|Cupboard|Podium|Lectern|Cauldron|Tub|Mirror|Wardrobe|Cushion"),
    ("clutter", r"Barrel|Crate|Pot\d|Pot$|Sack|Box|Straw|Hay|Basket|Bottle|Bucket|Cart|Anvil|Bellows|Spitoon|"
                r"Brick|Tool|Jar|Vase|Bag|Cabbage|Pumpkin|Shovel|Pick|Wheel|Debris|Plate|Mug|Bowl|Pile"),
    ("wall_decor", r"Tapestry|Shield|Banner|Painting|Plaque|Hanging|Trophy|Mask|Clock|Sign|Weapons?Rack|Rack"),
    ("structure", r"Column|Statue|Monument|Fountain|Well|Gargoyle|Pillar|Arch|Beam|Gear|Fence|Grate|Pipe|Tomb|"
                  r"Grave|Crypt|Pedestal|Urn|Idol|Post\d|Pole|Stairs|Ramp|Bridge|Dock|Obelisk|Sarcophag|Lever"),
    ("water_decor", r"Ripple|Bubble|Splash|Drip"),
]
CATEGORIES = [(c, re.compile(r)) for c, r in CATEGORIES]
STYLE_CATS = ["tree", "plant", "flower_tuft", "rock", "log", "bones", "web", "furniture", "clutter",
              "wall_decor", "structure", "water_decor", "other"]


def classify(o):
    """Category of an object, 'light' for visible light sources, or None if it is not decoration."""
    t = o["type"]; cls = set((o["class"] or "").replace(" ", "").split(","))
    if o["xtype"] == "InvisibleLightXfer" or (LIGHT_NAME.search(t) and not re.search(r"Unlit", t)):
        if cls & {"MONSTER", "WEAPON", "ARMOR", "FOOD", "KEY"}: return None
        return "light"
    if o["xtype"] not in (None, "DefaultXfer"): return None
    if cls & EXCLUDE_CLASS: return None
    if EXCLUDE_NAME.search(t): return None
    for c, rx in CATEGORIES:
        if rx.search(t): return c
    return "other"


FAMILIES = [
    ("water", r"^Water(?!Swamp)"), ("swamp", r"Swamp|^Mud"), ("lava", r"Lava|Volcanic"), ("ice", r"Ice"),
    ("interior", r"Wood|Rug|Oak|Redwood|Tile|Checker|Busy"), ("grass", r"Grass|Weeds"),
    ("cave", r"Cave|^Rock|Crystal|ManaMine"), ("dirt", r"Dirt|Sand"),
    ("dungeon", r"Dungeon|LOTD|Crypt|^Black|Bones|GreenBrick|BlueBrick|Bluebrick|WornBlue|StoneLight|AncientRuin"),
    ("town_paving", r"Cobble|Brick|Galava|DunMir|Ix|Facade|Marble|Stone"),
]
FAMILIES = [(f, re.compile(r)) for f, r in FAMILIES]


def family(material):
    for f, rx in FAMILIES:
        if rx.search(material or ""): return f
    return "other"


VARIANT_RX = re.compile(r"^(.*?)(\d+[a-dA-D]?|NE|NW|SE|SW|North|South|East|West)$")


def base_name(t):
    m = VARIANT_RX.match(t)
    return m.group(1) if m and m.group(1) else t


# ----------------------------------------------------------------------------- helpers
def wq(values, qs=(0.1, 0.25, 0.5, 0.75, 0.9)):
    """Weighted quantiles of [(value, weight)]."""
    if not values: return None
    values = sorted(values)
    tot = sum(w for _, w in values); out = []
    for q in qs:
        acc, target = 0.0, q * tot
        for v, w in values:
            acc += w
            if acc >= target: out.append(round(v, 1)); break
        else: out.append(round(values[-1][0], 1))
    return dict(zip(("p10", "p25", "p50", "p75", "p90"), out))


def distance_field(sources, max_d=20):
    """8-connected BFS distance (in cells) from a set of cells, capped at max_d."""
    dist = {s: 0 for s in sources}
    dq = deque(sources)
    while dq:
        x, y = dq.popleft(); d = dist[(x, y)]
        if d >= max_d: continue
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if n not in dist and 0 <= n[0] < 256 and 0 <= n[1] < 256:
                    dist[n] = d + 1; dq.append(n)
    return dist


class Grid:
    """Bucketed point index for nearest-neighbour queries (world px)."""
    def __init__(self, pts, size=46):
        self.size = size; self.b = defaultdict(list)
        for i, (x, y) in enumerate(pts): self.b[(int(x // size), int(y // size))].append(i)
        self.pts = pts

    def nearest(self, i, max_r=230):
        x, y = self.pts[i]; bx, by = int(x // self.size), int(y // self.size)
        best = None
        for r in range(0, max_r // self.size + 2):
            for gx in range(bx - r, bx + r + 1):
                for gy in range(by - r, by + r + 1):
                    if max(abs(gx - bx), abs(gy - by)) != r: continue
                    for j in self.b.get((gx, gy), ()):
                        if j == i: continue
                        d = math.hypot(self.pts[j][0] - x, self.pts[j][1] - y)
                        if best is None or d < best: best = d
            if best is not None and best <= r * self.size: break
        return best if best is not None and best <= max_r else None

    def within(self, i, r):
        x, y = self.pts[i]; bx, by = int(x // self.size), int(y // self.size); k = r // self.size + 1
        for gx in range(bx - k, bx + k + 1):
            for gy in range(by - k, by + k + 1):
                for j in self.b.get((gx, gy), ()):
                    if j != i and math.hypot(self.pts[j][0] - x, self.pts[j][1] - y) <= r: yield j


LINE_OF = {0: "/", 3: "/", 5: "/", 1: "\\", 4: "\\", 6: "\\"}


def nearest_straight_wall(walls, px, py, max_cells=3):
    """Nearest wall cell with a straight or T facing; returns (line, side, perpendicular px, facing) or None.
    '/' walls run along constant u; side 'BR' = towards +u (down-right on screen), 'TL' the other side.
    '\\' walls run along constant v; side 'TR' = towards +v (up-right on screen), 'BL' the other side."""
    cx, cy = px / C.CELL, py / C.CELL
    best = None
    for x in range(int(cx) - max_cells, int(cx) + max_cells + 1):
        for y in range(int(cy) - max_cells, int(cy) + max_cells + 1):
            w = walls.get((x, y))
            if not w or w["facing"] not in LINE_OF: continue
            dx, dy = px - (x + 0.5) * C.CELL, py - (y + 0.5) * C.CELL
            d = math.hypot(dx, dy)
            if best is None or d < best[0]: best = (d, w["facing"], dx, dy)
    if not best or best[0] > max_cells * C.CELL: return None
    d, f, dx, dy = best
    if LINE_OF[f] == "/":
        s = (dx + dy) / math.sqrt(2); side = "BR" if s > 0 else "TL"
    else:
        s = (dx - dy) / math.sqrt(2); side = "TR" if s > 0 else "BL"
    return LINE_OF[f], side, abs(s), f


def top(counter, n, total=None):
    total = total or sum(counter.values()) or 1
    return [[k, round(v / total, 3)] for k, v in counter.most_common(n)]


# ----------------------------------------------------------------------------- mining
def mine():
    W = C.sp_weights()
    res = {}

    # Valid decoration types (engine-level evidence): all 157 maps, plain counts
    valid = defaultdict(lambda: [0, set(), None])
    for m in C.all_maps():
        for o in C.objects(m):
            cat = classify(o)
            if cat is None: continue
            v = valid[o["type"]]; v[0] += 1; v[1].add(m); v[2] = cat
    res["observed_types"] = {t: {"category": v[2], "count": v[0], "maps": len(v[1])} for t, v in sorted(valid.items())}

    mat_tiles = Counter(); fam_tiles = Counter()
    mat_obj = defaultdict(Counter); fam_obj = defaultdict(Counter); fam_cat = defaultdict(Counter)
    mat_maps = defaultdict(set); fam_maps = defaultdict(set)
    nn = defaultdict(list); wall_d = defaultdict(list); nn_maps = defaultdict(set)
    tree_path_d = []; tree_on = Counter(); tree_wall_band = Counter(); grass_wall_band = Counter()
    clusters = defaultdict(list)
    pair_cnt = Counter(); pair_maps = defaultdict(set); pair_d = defaultdict(list); pair_off = defaultdict(list)
    base_cnt = Counter()
    dir_stats = defaultdict(lambda: defaultdict(float)); dir_perp = defaultdict(list); dir_maps = defaultdict(set)
    dir_free = defaultdict(float)
    block_types = Counter(); block_near = defaultdict(Counter); block_fam = defaultdict(Counter); block_maps = defaultdict(set)
    block_on_wall = defaultdict(float)
    amb_fam = defaultdict(Counter)

    BANDS = [(0, 2), (2, 4), (4, 8), (8, 16), (16, 999)]
    band = lambda d: next(f"{a}-{b}" if b < 999 else f"{a}+" for a, b in BANDS if a <= d < b)

    for mi, m in enumerate(C.sp_maps()):
        w = W[m]
        T = C.tiles(m); WL = C.walls(m); objs = C.objects(m)
        for (x, y), t in T.items():
            mat_tiles[t["material"]] += w; fam_tiles[family(t["material"])] += w
        wall_dist = distance_field(list(WL.keys()), 20)
        path_cells = [k for k, t in T.items() if family(t["material"]) in ("dirt", "town_paving")]
        path_dist = distance_field(path_cells, 12) if path_cells else {}
        for (x, y), t in T.items():
            if family(t["material"]) == "grass":
                grass_wall_band[band(wall_dist.get((x + 1, y + 1), 99))] += w

        deco = []
        for o in objs:
            cat = classify(o)
            if cat is None: continue
            tu = C.tile_under(m, o["x"], o["y"])
            mat = T[tu]["material"] if tu else None
            deco.append((o, cat, mat))
            if cat in ("light",): continue
            if cat == "ambient_sound":
                amb_fam[family(mat) if mat else "no_floor"][o["type"]] += w; continue
            if cat == "blocker":
                block_types[o["type"]] += w; block_maps[o["type"]].add(m); block_fam[o["type"]][family(mat)] += w
                if C.obj_cell(o) in WL: block_on_wall[o["type"]] += w
                continue
            if mat:
                mat_obj[mat][o["type"]] += w; mat_maps[mat].add(m)
                fam_obj[family(mat)][o["type"]] += w; fam_cat[family(mat)][cat] += w; fam_maps[family(mat)].add(m)

        # spacing and wall distance per category
        bycat = defaultdict(list)
        for o, cat, mat in deco:
            if cat in STYLE_CATS: bycat[cat].append(o)
        for cat, lst in bycat.items():
            g = Grid([(o["x"], o["y"]) for o in lst])
            for i, o in enumerate(lst):
                d = g.nearest(i)
                nn[cat].append((d if d is not None else 999.0, w))
                wd = wall_dist.get(C.obj_cell(o), 21)
                wall_d[cat].append((wd, w))
            nn_maps[cat].add(m)

        # trees relative to paths and walls
        for o in bycat.get("tree", []):
            tu = C.tile_under(m, o["x"], o["y"])
            fam = family(T[tu]["material"]) if tu else "none"
            tree_on[fam] += w
            if fam == "grass":
                cx, cy = C.obj_cell(o)
                tree_path_d.append((path_dist.get((cx - 1, cy - 1), 13), w))
                tree_wall_band[band(wall_dist.get((cx, cy), 99))] += w

        # clustering of flowers / mushrooms / small plants (single linkage, 35 px)
        for key, rx in (("flowers", r"Flower"), ("mushrooms", r"Mushroom"), ("grass_tufts", r"GrassTuft"),
                        ("plants", r"Plant|Bush|Fern|Foliage"), ("rocks", r"Rock|Pebble|Boulder"),
                        ("barrels_crates", r"Barrel|Crate")):
            pts = [(o["x"], o["y"], o["type"]) for o, cat, mat in deco if re.search(rx, o["type"])]
            if not pts: continue
            g = Grid([(x, y) for x, y, _ in pts]); seen = set()
            for i in range(len(pts)):
                if i in seen: continue
                comp, dq = [i], deque([i]); seen.add(i)
                while dq:
                    j = dq.popleft()
                    for k in g.within(j, 35):
                        if k not in seen: seen.add(k); comp.append(k); dq.append(k)
                same = Counter(pts[k][2] for k in comp).most_common(1)[0][1] / len(comp)
                clusters[key].append((len(comp), same, w))

        # co-occurrence among furniture / clutter / lights / structures
        anchor = [(o, cat) for o, cat, mat in deco if cat in ("furniture", "clutter", "light", "structure", "wall_decor")]
        if anchor:
            g = Grid([(o["x"], o["y"]) for o, _ in anchor])
            for i, (o, cat) in enumerate(anchor):
                a = base_name(o["type"]); base_cnt[a] += w
                seen_b = set()
                for j in g.within(i, 60):
                    ob = anchor[j][0]; b = base_name(ob["type"])
                    if b == a or b in seen_b: continue
                    seen_b.add(b)
                    pair_cnt[(a, b)] += w; pair_maps[(a, b)].add(m)
                    pair_d[(a, b)].append((math.hypot(ob["x"] - o["x"], ob["y"] - o["y"]), w))
                    pair_off[(a, b)].append((ob["x"] - o["x"], ob["y"] - o["y"]))

        # directional variants vs the nearest straight wall
        for o, cat, mat in deco:
            if cat not in ("furniture", "wall_decor", "light", "structure", "clutter"): continue
            if not VARIANT_RX.match(o["type"]): continue
            r = nearest_straight_wall(WL, o["x"], o["y"])
            if r is None:
                dir_free[o["type"]] += w; continue
            line, side, perp, f = r
            dir_stats[o["type"]][f"{line}|{side}"] += w
            dir_perp[o["type"]].append((perp, w)); dir_maps[o["type"]].add(m)
        if mi % 20 == 0: print(f"  mined {mi + 1}/{len(C.sp_maps())} maps", flush=True)

    # ---------------------------------------------------------------- assemble
    def palette(tile_c, obj_c, maps_c, min_tiles=150):
        out = {}
        for k, objs in obj_c.items():
            tw = tile_c.get(k, 0)
            if tw < min_tiles: continue
            tot = sum(objs.values())
            out[k] = {"tiles_weighted": round(tw), "maps": len(maps_c[k]),
                      "objects_per_100_tiles": round(100 * tot / tw, 2), "top_types": top(objs, 25, tot)}
        return out

    res["palettes_by_material"] = palette(mat_tiles, mat_obj, mat_maps)
    res["palettes_by_family"] = palette(fam_tiles, fam_obj, fam_maps, 0)
    for f, d in res["palettes_by_family"].items():
        d["category_density_per_100_tiles"] = {c: round(100 * v / fam_tiles[f], 2) for c, v in fam_cat[f].most_common()}
    res["family_of_material"] = {m: family(m) for m in sorted(mat_tiles)}

    res["spacing_px"] = {c: {"nearest_same_category": wq(nn[c]), "n_weighted": round(sum(w for _, w in nn[c]), 1),
                             "maps": len(nn_maps[c]),
                             "share_isolated_over_230px": round(sum(w for d, w in nn[c] if d >= 999) / max(1e-9, sum(w for _, w in nn[c])), 3)}
                         for c in STYLE_CATS if nn[c]}
    res["wall_distance_cells"] = {}
    for c in STYLE_CATS:
        if not wall_d[c]: continue
        tot = sum(w for _, w in wall_d[c])
        res["wall_distance_cells"][c] = {"quantiles": wq(wall_d[c]),
                                         "share_within_1_cell": round(sum(w for d, w in wall_d[c] if d <= 1) / tot, 3),
                                         "share_within_2_cells": round(sum(w for d, w in wall_d[c] if d <= 2) / tot, 3)}

    tt = sum(tree_on.values())
    res["trees"] = {
        "floor_family_share": top(tree_on, 12, tt),
        "on_grass_distance_to_path_tile_cells": wq(tree_path_d),
        "on_grass_share_within_1_cell_of_path": round(sum(w for d, w in tree_path_d if d <= 1) / max(1e-9, sum(w for _, w in tree_path_d)), 3),
        "density_per_100_grass_tiles_by_wall_distance": {b: round(100 * tree_wall_band[b] / grass_wall_band[b], 2)
                                                          for b in grass_wall_band if grass_wall_band[b] > 20},
        "note": "Trees concentrate near the walls that bound outdoor areas (tree lines / forest edges); "
                "path tiles are dirt or paving families; distance capped at 13 cells."}

    res["clusters_35px"] = {}
    for k, lst in clusters.items():
        tot = sum(w for _, _, w in lst)
        sizes = [(s, w) for s, _, w in lst]
        res["clusters_35px"][k] = {"cluster_size": wq(sizes), "share_singletons": round(sum(w for s, _, w in lst if s == 1) / tot, 3),
                                   "mean_same_type_share": round(sum(sh * w for s, sh, w in lst if s > 1) / max(1e-9, sum(w for s, _, w in lst if s > 1)), 3)}

    pairs = []
    for (a, b), cnt in pair_cnt.items():
        if len(pair_maps[(a, b)]) < 3 or cnt < 4: continue
        lift = cnt / max(1e-9, base_cnt[a])
        offs = pair_off[(a, b)]
        mdx = sorted(x for x, _ in offs)[len(offs) // 2]; mdy = sorted(y for _, y in offs)[len(offs) // 2]
        pairs.append({"a": a, "b": b, "weighted": round(cnt, 1), "maps": len(pair_maps[(a, b)]),
                      "share_of_a_with_b_within_60px": round(lift, 3), "distance_px": wq(pair_d[(a, b)]),
                      "median_offset_px": [round(mdx), round(mdy)]})
    pairs.sort(key=lambda p: (-p["share_of_a_with_b_within_60px"] * min(1, p["weighted"] / 20), -p["weighted"]))
    res["co_occurrence"] = pairs[:150]

    groups = defaultdict(list)
    for t in set(dir_stats) | set(dir_free):
        groups[base_name(t)].append(t)
    dirrules = {}
    for g, types in sorted(groups.items()):
        if len(types) < 2: continue
        tot_g = sum(sum(dir_stats[t].values()) + dir_free[t] for t in types)
        if tot_g < 4: continue
        variants = {}
        for t in sorted(types):
            s = dir_stats[t]; tot = sum(s.values()) + dir_free[t]
            if tot <= 0: continue
            best = max(s.items(), key=lambda kv: kv[1]) if s else (None, 0)
            variants[t] = {"weighted": round(tot, 1), "maps": len(dir_maps[t]),
                           "share_free_standing": round(dir_free[t] / tot, 3),
                           "wall_side_shares": {k: round(v / tot, 3) for k, v in sorted(s.items(), key=lambda kv: -kv[1])},
                           "dominant": best[0], "dominant_share": round(best[1] / tot, 3) if best[0] else 0,
                           "perpendicular_distance_px": wq(dir_perp[t])}
        by_side = defaultdict(Counter)
        for t in types:
            for k, v in dir_stats[t].items(): by_side[k][t] += v
        choose = {}
        for k, c in by_side.items():
            tot = sum(c.values()); t, v = c.most_common(1)[0]
            if tot >= 2: choose[k] = {"variant": t, "share": round(v / tot, 3), "weighted": round(tot, 1)}
        dirrules[g] = {"variants": variants, "use_variant_for_wall_side": choose}
    res["directional_variants"] = dirrules
    res["directional_convention"] = ("line '/' = wall run along constant u (facing 0, T 3/5); side BR = towards +u "
                                     "(down-right on screen), TL = other side. line '\\' = run along constant v "
                                     "(facing 1, T 4/6); side TR = towards +v (up-right), BL = other side. "
                                     "Nearest straight wall within 3 cells; otherwise counted free-standing.")

    res["blockers"] = {t: {"weighted": round(v, 1), "maps": len(block_maps[t]),
                           "floor_family_share": top(block_fam[t], 5),
                           "share_on_wall_cell": round(block_on_wall[t] / v, 3)}
                       for t, v in block_types.most_common()}
    # what sits on top of blockers: re-scan (cheap) for nearby scenery
    near = defaultdict(Counter)
    for m in C.sp_maps():
        objs = C.objects(m); w = W[m]
        blk = [o for o in objs if o["type"].startswith("Extent")]
        if not blk: continue
        rest = [o for o in objs if not o["type"].startswith("Extent") and classify(o) not in (None, "ambient_sound")]
        g = Grid([(o["x"], o["y"]) for o in rest])
        g.pts = [(o["x"], o["y"]) for o in rest]
        for b in blk:
            bx, by = int(b["x"] // g.size), int(b["y"] // g.size)
            cand = [j for gx in (bx - 1, bx, bx + 1) for gy in (by - 1, by, by + 1) for j in g.b.get((gx, gy), ())]
            cand = [j for j in cand if math.hypot(rest[j]["x"] - b["x"], rest[j]["y"] - b["y"]) <= 40]
            if cand:
                j = min(cand, key=lambda j: math.hypot(rest[j]["x"] - b["x"], rest[j]["y"] - b["y"]))
                near[b["type"]][rest[j]["type"]] += w
            else:
                near[b["type"]]["(nothing within 40px)"] += w
    for t in res["blockers"]:
        res["blockers"][t]["nearest_object_within_40px"] = top(near[t], 8)

    res["ambient_sounds_by_family"] = {f: {"per_100_tiles": round(100 * sum(c.values()) / fam_tiles[f], 3) if fam_tiles[f] else None,
                                           "weighted": round(sum(c.values()), 1), "top_types": top(c, 8)}
                                       for f, c in amb_fam.items() if fam_tiles[f] > 500 or f == "no_floor"}
    res["meta"] = {"single_player_maps": len(C.sp_maps()), "layouts_weighted": round(sum(W.values()), 1),
                   "excluded": "monsters/NPCs, items, doors, triggers, exits, transporters, elevators, generators, "
                               "holes, traps/spikes, markers, PlayerStart; lights only used in co-occurrence/directional"}
    return res


# ----------------------------------------------------------------------------- report
def report(r):
    L = []
    a = L.append
    a("# Decoration and furniture placement rules\n")
    a("Mined by `rules/decoration.py` from the reference corpus. Style figures use the 120 single-player maps "
      "weighted so each distinct layout counts once (62 layouts); `observed_types` uses all 157 maps.\n")
    a("## JSON schema (`rules/out/decoration.json`)\n")
    a("""```
observed_types[type] = {category, count, maps}            # every decoration type seen (all maps)
family_of_material[material] = family                     # grass/dirt/cave/dungeon/town_paving/interior/swamp/ice/lava/water/other
palettes_by_material[material] / palettes_by_family[family] = {
    tiles_weighted, maps, objects_per_100_tiles, top_types[[type, share]...],
    category_density_per_100_tiles{category: value}       # family palettes only
}
spacing_px[category] = {nearest_same_category{p10..p90}, share_isolated_over_230px, n_weighted, maps}
wall_distance_cells[category] = {quantiles{p10..p90}, share_within_1_cell, share_within_2_cells}
trees = {floor_family_share, on_grass_distance_to_path_tile_cells{..}, on_grass_share_within_1_cell_of_path,
         density_per_100_grass_tiles_by_wall_distance{band: value}}
clusters_35px[kind] = {cluster_size{p10..p90}, share_singletons, mean_same_type_share}
co_occurrence[] = {a, b, weighted, maps, share_of_a_with_b_within_60px, distance_px{..}, median_offset_px[dx,dy]}
directional_variants[base] = {variants[type] = {weighted, maps, share_free_standing, wall_side_shares{"line|side": share},
                              dominant, dominant_share, perpendicular_distance_px{..}},
                              use_variant_for_wall_side{"line|side": {variant, share, weighted}}}
directional_convention = text  (line '/' sides BR/TL, line '\\' sides TR/BL)
blockers[type] = {weighted, maps, floor_family_share, share_on_wall_cell, nearest_object_within_40px}
ambient_sounds_by_family[family] = {per_100_tiles, top_types}
```
Quantiles are weighted p10/p25/p50/p75/p90. Distances: px = world pixels (23 per cell).\n""")

    a("## Key rules\n")
    fam = r["palettes_by_family"]; sp = r["spacing_px"]; wd = r["wall_distance_cells"]; tr = r["trees"]
    dens = lambda f: fam.get(f, {}).get("objects_per_100_tiles")
    share1 = lambda c: round(100 * wd[c]["share_within_1_cell"])
    p50 = lambda c: sp[c]["nearest_same_category"]["p50"]
    bands = tr["density_per_100_grass_tiles_by_wall_distance"]
    a(f"- **Density by terrain** (decoration objects per 100 floor tiles): grass {dens('grass')}, dirt {dens('dirt')}, "
      f"cave {dens('cave')}, swamp {dens('swamp')}, interior {dens('interior')}, town paving {dens('town_paving')}, "
      f"dungeon {dens('dungeon')}, lava {dens('lava')}, ice {dens('ice')}. Grass = small plants (Plant4/Plant5/PlantForest1), "
      "flowers, mushrooms and trees; dirt and cave = rocks, pebbles, rock pillars and mushrooms; dungeon = bones, webs, columns.")
    a(f"- **Scenery hugs walls**: within 1 cell of a wall - plants {share1('plant')}%, rocks {share1('rock')}%, "
      f"trees {share1('tree')}%, furniture {share1('furniture')}%, clutter {share1('clutter')}%, webs {share1('web')}%; "
      f"wall decorations sit on the wall cell ({share1('wall_decor')}% within 1 cell).")
    a("- **Trees line the edges of outdoor areas**: trees per 100 grass tiles by distance from the bounding wall: "
      + ", ".join(f"{b} cells: {v}" for b, v in sorted(bands.items(), key=lambda kv: int(kv[0].split('-')[0].rstrip('+'))))
      + f". Only {round(100 * tr['on_grass_share_within_1_cell_of_path'])}% of trees stand within 1 cell of a path tile "
      f"(median {tr['on_grass_distance_to_path_tile_cells']['p50']} cells away). Median tree spacing {p50('tree')} px "
      f"(~{round(p50('tree') / 23, 1)} cells).")
    cl = r["clusters_35px"]
    a(f"- **Small scenery is close-packed**: median nearest neighbour - plants {p50('plant')} px, flowers/tufts/mushrooms "
      f"{p50('flower_tuft')} px, rocks {p50('rock')} px. Mushrooms clump (p75 cluster {cl['mushrooms']['cluster_size']['p75']}, "
      f"p90 {cl['mushrooms']['cluster_size']['p90']}, mostly one type); flowers are almost always single "
      f"({round(100 * cl['flowers']['share_singletons'])}% singletons).")
    a("- **Furniture sets**: chairs with tables and desks (about half of tables/desks have a chair within 60 px), "
      "nightstands with beds (68% of nightstands beside a bed, median 35 px), bellows with fireplaces, stools with "
      "Urchin/Ogre tables, straw with ogre beds; barrels and crates in small groups (p75 2, p90 3).")
    a("- **Directional variants follow the wall they back onto** (table below): one variant per wall side with 80-100% "
      "consistency for beds, nightstands, desks, benches, chests, sconces, lanterns and DunMir torches. Furniture is "
      "placed mostly against the walls on the BR side of '/' walls and the BL side of '\\' walls.")
    a("- **Extent\\* blockers** are invisible collision shapes: on town paving/dungeon floors, often on wall cells or "
      "alone (stairs, ledges, fountains, tower bases), and under scenery such as swamp Plant3 and Galava trees.")
    a("")
    a("## Palettes by floor family (decoration objects per 100 tiles)\n")
    a("| family | tiles (weighted) | maps | per 100 tiles | category densities | top types |\n|---|---|---|---|---|---|")
    for f, d in sorted(r["palettes_by_family"].items(), key=lambda kv: -kv[1]["tiles_weighted"]):
        cats = ", ".join(f"{c} {v}" for c, v in list(d["category_density_per_100_tiles"].items())[:5])
        tops = ", ".join(f"{t} {round(100 * s)}%" for t, s in d["top_types"][:8])
        a(f"| {f} | {d['tiles_weighted']} | {d['maps']} | {d['objects_per_100_tiles']} | {cats} | {tops} |")
    a("\n## Palettes by floor material (largest 25)\n")
    a("| material | family | tiles | per 100 tiles | top types |\n|---|---|---|---|---|")
    for mat, d in sorted(r["palettes_by_material"].items(), key=lambda kv: -kv[1]["tiles_weighted"])[:25]:
        tops = ", ".join(f"{t} {round(100 * s)}%" for t, s in d["top_types"][:7])
        a(f"| {mat} | {r['family_of_material'].get(mat)} | {d['tiles_weighted']} | {d['objects_per_100_tiles']} | {tops} |")

    a("\n## Spacing and distance from walls\n")
    a("| category | nearest same-category object px (p25 / p50 / p75) | isolated (>230 px) | wall distance cells (p25/p50/p75) | within 1 cell of wall |\n|---|---|---|---|---|")
    for c, d in r["spacing_px"].items():
        q = d["nearest_same_category"]; wd = r["wall_distance_cells"].get(c, {})
        wq_ = wd.get("quantiles") or {}
        a(f"| {c} | {q['p25']} / {q['p50']} / {q['p75']} | {round(100 * d['share_isolated_over_230px'])}% | "
          f"{wq_.get('p25')} / {wq_.get('p50')} / {wq_.get('p75')} | {round(100 * wd.get('share_within_1_cell', 0))}% |")

    t = r["trees"]
    a("\n## Trees outdoors\n")
    a(f"- Floor under trees: " + ", ".join(f"{k} {round(100 * v)}%" for k, v in t["floor_family_share"][:6]))
    q = t["on_grass_distance_to_path_tile_cells"] or {}
    a(f"- Trees on grass: distance to nearest path tile (dirt/paving) p25 {q.get('p25')} / median {q.get('p50')} / p75 {q.get('p75')} cells; "
      f"{round(100 * t['on_grass_share_within_1_cell_of_path'])}% stand within 1 cell of a path.")
    a("- Tree density per 100 grass tiles by distance from the nearest wall (cells): " +
      ", ".join(f"{b}: {v}" for b, v in sorted(t["density_per_100_grass_tiles_by_wall_distance"].items(), key=lambda kv: int(kv[0].split('-')[0].rstrip('+')))))

    a("\n## Clumping (single-linkage clusters, 35 px)\n")
    a("| kind | cluster size p50 / p75 / p90 | singletons | same type within a clump |\n|---|---|---|---|")
    for k, d in r["clusters_35px"].items():
        q = d["cluster_size"]
        a(f"| {k} | {q['p50']} / {q['p75']} / {q['p90']} | {round(100 * d['share_singletons'])}% | {round(100 * d['mean_same_type_share'])}% |")

    a("\n## Co-occurrence (furniture, clutter, lights, structures within 60 px; top 40)\n")
    a("| a | b | share of a with b nearby | weighted | maps | median distance px | median offset b-a (dx,dy) |\n|---|---|---|---|---|---|---|")
    for p in r["co_occurrence"][:40]:
        a(f"| {p['a']} | {p['b']} | {round(100 * p['share_of_a_with_b_within_60px'])}% | {p['weighted']} | {p['maps']} | {p['distance_px']['p50']} | {p['median_offset_px']} |")

    a("\n## Directional variants against walls\n")
    a(r["directional_convention"] + "\n")
    a("| group | wall side -> variant (share, weighted) |\n|---|---|")
    for g, d in sorted(r["directional_variants"].items(), key=lambda kv: -sum(v["weighted"] for v in kv[1]["variants"].values())):
        ch = d["use_variant_for_wall_side"]
        if not ch: continue
        cells = "; ".join(f"{k}: {v['variant']} ({round(100 * v['share'])}%, {v['weighted']})" for k, v in sorted(ch.items()))
        a(f"| {g} | {cells} |")
    a("\nPer-variant detail (dominant side, share free-standing, perpendicular distance from the wall centre line) is in the JSON.\n")

    a("## Invisible blockers (Extent*)\n")
    a("| type | weighted | maps | on a wall cell | floor | nearest object within 40 px |\n|---|---|---|---|---|---|")
    for tname, d in r["blockers"].items():
        a(f"| {tname} | {d['weighted']} | {d['maps']} | {round(100 * d['share_on_wall_cell'])}% | "
          + ", ".join(f"{k} {round(100 * v)}%" for k, v in d["floor_family_share"][:3]) + " | "
          + ", ".join(f"{k} {round(100 * v)}%" for k, v in d["nearest_object_within_40px"][:4]) + " |")

    a("\n## Ambient sound emitters by floor family\n")
    a("Ambient sound emitters (Amb*) per 100 tiles of the floor they sit on; `no_floor` = placed over void "
      "(off the walkable area, common for area-wide sounds).\n")
    for f, d in sorted(r["ambient_sounds_by_family"].items(), key=lambda kv: -(kv[1]["per_100_tiles"] or 0)):
        dens = f"{d['per_100_tiles']} per 100 tiles" if d["per_100_tiles"] is not None else f"{d['weighted']} emitters (weighted)"
        a(f"- {f}: {dens} - " + ", ".join(f"{t} {round(100 * s)}%" for t, s in d["top_types"][:5]))
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    r = mine()
    C.save_json("decoration.json", r)
    C.save_section("decoration.md", report(r))
    print("wrote rules/out/decoration.json and rules/sections/decoration.md")
