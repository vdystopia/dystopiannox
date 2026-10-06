"""Mine lighting rules from the reference corpus.

Writes rules/out/lighting.json (machine-readable, for the generator and validator) and
rules/sections/lighting.md (summary with evidence). Run: py rules/lighting.py

Covers: ColorLight (invisible light, InvisibleLightXfer) settings and presets, light density and
spacing by floor context, pairing of ColorLights with visible light sources, visible light source
types per context and wall-mounted direction variants, map/polygon ambient colour.
Engine-validity facts use all 157 maps (plain counts); style rules use campaign maps weighted
by common.campaign_weights() (1 / layout group size).
"""
import colorsys, json, math, os, re, statistics
from collections import Counter, defaultdict
import common as C

# ---------------------------------------------------------------- floor contexts
CONTEXT_RULES = [  # first match wins
    ("lava", r"Lava|Volcanic"),
    ("water", r"Water"),
    ("ice", r"Ice"),
    ("dungeon", r"LOTD|Dungeon|Crypt|^Black$|AncientRuin"),
    ("interior", r"Wood|Oak|Redwood|Rug|Tile|Busy|Facade|Marble"),
    ("cave", r"Cave|Rock|ManaMine|Crystal|^Mud$"),
    ("masonry", r"Brick|Cobble|Stone"),
    ("swamp", r"Swamp"),
    ("outdoor", r"Grass|Weeds|Dirt|Sand"),
]


def context_of(material):
    if material is None: return "none"
    for name, rx in CONTEXT_RULES:
        if re.search(rx, material): return name
    return "other"


# ---------------------------------------------------------------- light source classification
PICKUP_CLASSES = ("FOOD", "KEY", "WEAPON", "ARMOR", "MONSTER", "PLAYER", "MISSILE")
PICKUP_XFERS = {"GoldXfer", "RewardMarkerXfer", "AmmoXfer", "WeaponXfer", "ArmorXfer", "MonsterXfer", "NPCXfer"}
FIRE_RX = r"Torch|Flame|Fireplace|Brazier|Basin|Stove|Candle|Lantern|Sconse|Fire"
MAGIC_RX = r"Crystal|Obelisk|Orb|Fairy|Vandegraf|Workstation|SoulGate|Globe"


def light_source_kind(t):
    """None if not a scenery light source; else 'fire' | 'magic' | 'other'."""
    th = C.things().get(t)
    if not th or "LIGHT" not in (th["class"] or ""): return None
    if t.startswith("ColorLight"): return None
    if any(k in th["class"] for k in PICKUP_CLASSES) or th["xfer"] in PICKUP_XFERS: return None
    if re.search(FIRE_RX, t): return "fire"
    if re.search(MAGIC_RX, t): return "magic"
    return "other"


def wall_mounted(t):
    th = C.things().get(t) or {}
    f = th.get("flags") or ""
    return "AIRBORNE" in f and "NO_COLLIDE" in f


# ---------------------------------------------------------------- colour helpers
def colour_family(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    if mx < 40: return "dark"
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if s < 0.18: return "white"
    deg = h * 360
    for lim, name in ((15, "red"), (40, "orange"), (70, "yellow"), (170, "green"), (200, "cyan"),
                      (260, "blue"), (330, "purple"), (361, "red")):
        if deg < lim: return name
    return "red"


def animated(x):
    return x.get("PulseSpeed", 0) > 0 or x.get("type", 0) == 1


def wq(values, weights, q):
    """Weighted quantile."""
    pairs = sorted(zip(values, weights))
    if not pairs: return None
    tot = sum(w for _, w in pairs); acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= q * tot: return v
    return pairs[-1][0]


def quart(values, weights=None):
    if not values: return None
    weights = weights or [1.0] * len(values)
    return [round(wq(values, weights, q), 1) for q in (0.25, 0.5, 0.75)]


def point_in_poly(px, py, pts):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]; xj, yj = pts[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / ((yj - yi) or 1e-9) + xi:
            inside = not inside
        j = i
    return inside


# ================================================================ mining
def main():
    con = C.db()
    W = C.campaign_weights()
    allmaps = C.all_maps()

    # ---------- 1. ColorLight field validity (all maps)
    all_lights = [(r["map"], json.loads(r["xfer"])) for r in
                  con.execute("SELECT map, xfer FROM objects WHERE xtype='InvisibleLightXfer'")]
    fields = defaultdict(Counter)
    for _, x in all_lights:
        for k, v in x.items(): fields[k][json.dumps(v)] += 1
    constant = {k: json.loads(c.most_common(1)[0][0]) for k, c in fields.items() if len(c) == 1}
    varying = {k: len(c) for k, c in fields.items() if len(c) > 1}
    rad_by_int, u7_by_int = defaultdict(Counter), defaultdict(Counter)
    for _, x in all_lights:
        rad_by_int[x["LightIntensity"]][x["LightRadius"]] += 1
        u7_by_int[x["LightIntensity"]][x["Unknown7"]] += 1
    rgb_eq_c1 = sum(1 for _, x in all_lights if [x["R"], x["G"], x["B"]] == x["Color1"]) / len(all_lights)
    cis_eq_int = sum(1 for _, x in all_lights if x["ChangeIntensitySingle"] == x["LightIntensity"]) / len(all_lights)

    # ---------- per campaign map pass
    ctx_tiles = defaultdict(float)            # context -> weighted tile count
    ctx_cl = defaultdict(float)               # context -> weighted ColorLight count
    ctx_src = defaultdict(float)              # context -> weighted scenery light source count
    ctx_maps_cl = defaultdict(set)
    cluster_members = defaultdict(list)       # preset key -> list of (weight, xfer, map, ctx)
    nn_by_ctx = defaultdict(lambda: ([], []))  # ctx -> (dists px, weights)
    nn_all = ([], [])
    pair_dist = ([], [])
    pair_offsets = defaultdict(list)          # visible type -> (dx, dy)
    pair_presets = defaultdict(Counter)       # visible type -> preset key counter (weighted)
    src_with_cl = defaultdict(lambda: [0.0, 0.0])  # visible type -> [weighted with CL within 46px, total]
    src_stats = defaultdict(lambda: dict(w=0.0, maps=set(), ctx=Counter()))
    wallrel = defaultdict(Counter)            # visible wall-mounted type -> (facing class, side) weighted
    wall_dist = defaultdict(list)
    near_flags = Counter()
    map_rows = []
    poly_rows = []

    for m in sorted(W):
        w = W[m]
        T = C.tiles(m); WL = C.walls(m); O = C.objects(m)
        tctx = {p: context_of(t["material"]) for p, t in T.items()}
        cnt = Counter(tctx.values())
        for k, n in cnt.items(): ctx_tiles[k] += w * n
        n_tiles = max(1, len(T))
        cls_set = [o for o in O if o["xtype"] == "InvisibleLightXfer"]
        srcs = [o for o in O if light_source_kind(o["type"])]

        def ctx_at(o):
            tp = C.tile_under(m, o["x"], o["y"])
            return tctx.get(tp, "none") if tp else "none"

        def near(o, kinds, r=3):
            cx, cy = int(o["x"] // C.CELL), int(o["y"] // C.CELL)
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if tctx.get((cx + dx, cy + dy)) in kinds: return True
            return False

        for o in cls_set:
            x = o["xfer"]; ctx = ctx_at(o)
            key = (colour_family(x["R"], x["G"], x["B"]), "animated" if animated(x) else "steady",
                   "full" if x["LightIntensity"] >= 60 else "dim")
            cluster_members[key].append((w, x, m, ctx))
            ctx_cl[ctx] += w; ctx_maps_cl[ctx].add(m)
            if near(o, ("water",)): near_flags["colorlight_near_water"] += w
            if near(o, ("lava",)): near_flags["colorlight_near_lava"] += w
            near_flags["colorlight_total"] += w
        for o in srcs:
            ctx = ctx_at(o); ctx_src[ctx] += w
            s = src_stats[o["type"]]; s["w"] += w; s["maps"].add(m); s["ctx"][ctx] += w

        # spacing between ColorLights
        pts = [(o["x"], o["y"], ctx_at(o)) for o in cls_set]
        for i, (x1, y1, cx) in enumerate(pts):
            best = min((math.hypot(x1 - x2, y1 - y2) for j, (x2, y2, _) in enumerate(pts) if j != i), default=None)
            if best is not None:
                nn_all[0].append(best); nn_all[1].append(w)
                nn_by_ctx[cx][0].append(best); nn_by_ctx[cx][1].append(w)

        # pairing ColorLight <-> visible source
        for o in cls_set:
            if not srcs: break
            s = min(srcs, key=lambda q: (q["x"] - o["x"]) ** 2 + (q["y"] - o["y"]) ** 2)
            d = math.hypot(s["x"] - o["x"], s["y"] - o["y"])
            pair_dist[0].append(d); pair_dist[1].append(w)
            if d <= 46:
                pair_offsets[s["type"]].append((o["x"] - s["x"], o["y"] - s["y"]))
                x = o["xfer"]
                pair_presets[s["type"]][(colour_family(x["R"], x["G"], x["B"]), "animated" if animated(x) else "steady",
                                         "full" if x["LightIntensity"] >= 60 else "dim")] += w
        for s in srcs:
            has = any(math.hypot(o["x"] - s["x"], o["y"] - s["y"]) <= 46 for o in cls_set)
            src_with_cl[s["type"]][0] += w * has; src_with_cl[s["type"]][1] += w

        # wall-mounted sources: relation to nearest wall
        for s in srcs:
            if not wall_mounted(s["type"]): continue
            cx, cy = s["x"] / C.CELL, s["y"] / C.CELL
            best, bd = None, 9.0
            for wx in range(int(cx) - 2, int(cx) + 2):
                for wy in range(int(cy) - 2, int(cy) + 2):
                    if (wx, wy) in WL:
                        d = (wx + 0.5 - cx) ** 2 + (wy + 0.5 - cy) ** 2
                        if d < bd: best, bd = (wx, wy), d
            if not best: continue
            f = WL[best]["facing"]
            du = (cx + cy) - (best[0] + best[1] + 1)
            dv = (cx - cy) - (best[0] - best[1])
            if f == 0: rel = ("'/' wall", "SE side" if du > 0 else "NW side")
            elif f == 1: rel = ("'\\' wall", "NE side" if dv > 0 else "SW side")
            else: rel = ("junction/corner", "")
            wallrel[s["type"]][rel] += w
            wall_dist[s["type"]].append(math.sqrt(bd) * C.CELL)

        # map kind and ambient
        npcs = sum(1 for o in O if o["type"] in ("NPC", "Maiden") or o["xtype"] == "NPCXfer")
        share = {k: cnt[k] / n_tiles for k in cnt}
        if share.get("lava", 0) >= 0.08: kind = "lava"
        elif share.get("ice", 0) >= 0.10: kind = "ice"
        elif npcs >= 8: kind = "town"
        elif share.get("swamp", 0) + share.get("water", 0) >= 0.25: kind = "swamp"
        elif share.get("cave", 0) >= 0.35: kind = "cave"
        elif share.get("dungeon", 0) + share.get("masonry", 0) + share.get("interior", 0) >= 0.5: kind = "dungeon/castle"
        elif share.get("outdoor", 0) + share.get("swamp", 0) >= 0.35: kind = "outdoor"
        else: kind = "mixed"
        amb = json.loads(con.execute("SELECT ambient FROM maps WHERE name=?", (m,)).fetchone()[0])
        polys = [dict(r) for r in con.execute("SELECT * FROM polygons WHERE map=?", (m,))]
        covered = 0
        if polys:
            parsed = []
            for p in polys:
                pp = json.loads(p["points"])
                if len(pp) >= 3:
                    xs = [q[0] for q in pp]; ys = [q[1] for q in pp]
                    parsed.append((min(xs), max(xs), min(ys), max(ys), pp, p))
            pctx = defaultdict(Counter)
            for (tx, ty), c in tctx.items():
                px_, py_ = (tx + 1) * C.CELL, (ty + 1) * C.CELL
                hit = False
                for x0, x1, y0, y1, pp, p in parsed:
                    if x0 <= px_ <= x1 and y0 <= py_ <= y1 and point_in_poly(px_, py_, pp):
                        pctx[p["idx"]][c] += 1; hit = True
                covered += hit
            for x0, x1, y0, y1, pp, p in parsed:
                dom = pctx[p["idx"]].most_common(1)[0][0] if pctx[p["idx"]] else "none"
                poly_rows.append(dict(map=m, w=w, amb=json.loads(p["ambient"]), mm=p["minimap"], ctx=dom,
                                      tiles=sum(pctx[p["idx"]].values()), enter=bool(p["enter_player"])))
        map_rows.append(dict(map=m, w=w, kind=kind, ambient=amb, npcs=npcs, polygons=len(polys),
                             coverage=round(covered / n_tiles, 3), colorlights=len(cls_set), sources=len(srcs),
                             lights_per_100_tiles=round(100 * (len(cls_set) + len(srcs)) / n_tiles, 2), tiles=n_tiles))

    # ---------- presets
    total_cl_w = sum(w for v in cluster_members.values() for w, *_ in v)
    presets, other_w = [], 0.0
    for key, mem in sorted(cluster_members.items(), key=lambda kv: -sum(w for w, *_ in kv[1])):
        ww = sum(w for w, *_ in mem)
        if ww / total_cl_w < 0.005:
            other_w += ww; continue
        full = Counter()
        for w, x, *_ in mem: full[json.dumps(x, sort_keys=True)] += w
        exemplar, ex_w = full.most_common(1)[0]
        rs = [x["R"] for _, x, *_ in mem]; gs = [x["G"] for _, x, *_ in mem]; bs = [x["B"] for _, x, *_ in mem]
        ws = [w for w, *_ in mem]
        ctxc = Counter()
        for w, x, m, c in mem: ctxc[c] += w
        presets.append(dict(
            id="%s_%s_%s" % key, family=key[0], animation=key[1], intensity_class=key[2],
            weighted_share=round(ww / total_cl_w, 4), count=len(mem), maps=len({m for _, _, m, _ in mem}),
            rgb_median=[wq(rs, ws, .5), wq(gs, ws, .5), wq(bs, ws, .5)],
            intensity_median=wq([x["LightIntensity"] for _, x, *_ in mem], ws, .5),
            radius_median=wq([x["LightRadius"] for _, x, *_ in mem], ws, .5),
            contexts={k: round(v / ww, 3) for k, v in ctxc.most_common(5)},
            exemplar_share_in_preset=round(ex_w / ww, 3),
            xfer=json.loads(exemplar)))

    # ---------- density by context
    density = {}
    for ctx in sorted(ctx_tiles, key=lambda k: -ctx_tiles[k]):
        tw = ctx_tiles[ctx]
        if tw < 50: continue
        density[ctx] = dict(tiles_weighted=round(tw), colorlights_per_100_tiles=round(100 * ctx_cl[ctx] / tw, 2),
                            sources_per_100_tiles=round(100 * ctx_src[ctx] / tw, 2),
                            all_lights_per_100_tiles=round(100 * (ctx_cl[ctx] + ctx_src[ctx]) / tw, 2),
                            maps_with_colorlights=len(ctx_maps_cl[ctx]))
    lp100 = [r["lights_per_100_tiles"] for r in map_rows]; lw = [r["w"] for r in map_rows]
    cl100 = [100 * r["colorlights"] / r["tiles"] for r in map_rows]

    spacing = {"all_colorlights_nn_px": quart(*nn_all)}
    for ctx, (d, ws) in nn_by_ctx.items():
        if sum(ws) >= 20: spacing[ctx] = quart(d, ws)

    # ---------- visible sources
    vis = {}
    for t, s in sorted(src_stats.items(), key=lambda kv: -kv[1]["w"]):
        if len(s["maps"]) < 2 and s["w"] < 5: continue
        tot = sum(s["ctx"].values())
        entry = dict(kind=light_source_kind(t), weighted_count=round(s["w"], 1), maps=len(s["maps"]),
                     contexts={k: round(v / tot, 3) for k, v in s["ctx"].most_common(4)},
                     dangerous="DANGEROUS" in (C.things()[t]["class"] or ""),
                     wall_mounted=wall_mounted(t),
                     share_with_colorlight_within_46px=round(src_with_cl[t][0] / src_with_cl[t][1], 3) if src_with_cl[t][1] else None)
        if pair_presets[t]:
            pp = pair_presets[t]; ptot = sum(pp.values())
            entry["paired_colorlight_presets"] = {"%s_%s_%s" % k: round(v / ptot, 3) for k, v in pp.most_common(3)}
            offs = pair_offsets[t]
            entry["paired_offset_px_median"] = [round(statistics.median(o[0] for o in offs), 1),
                                                round(statistics.median(o[1] for o in offs), 1)]
        if wallrel[t]:
            wt = sum(wallrel[t].values())
            entry["wall_relation"] = [dict(wall=k[0], side=k[1], share=round(v / wt, 3)) for k, v in wallrel[t].most_common(4)]
            entry["distance_to_wall_centre_px_median"] = round(statistics.median(wall_dist[t]), 1)
        vis[t] = entry

    # ---------- ambient
    by_kind = defaultdict(list)
    for r in map_rows: by_kind[r["kind"]].append(r)
    amb_kind = {}
    for k, rows in sorted(by_kind.items()):
        ws = [r["w"] for r in rows]
        amb_kind[k] = dict(maps=len(rows), weighted_maps=round(sum(ws), 2),
                           ambient_rgb_median=[wq([r["ambient"][i] for r in rows], ws, .5) for i in range(3)],
                           brightness_quartiles=quart([sum(r["ambient"]) / 3 for r in rows], ws),
                           lights_per_100_tiles=quart([r["lights_per_100_tiles"] for r in rows], ws),
                           polygons_per_map=quart([r["polygons"] for r in rows], ws),
                           polygon_coverage=quart([r["coverage"] for r in rows], ws),
                           examples=[r["map"] for r in sorted(rows, key=lambda r: -r["w"])][:6])
    pctx = defaultdict(list)
    for p in poly_rows: pctx[p["ctx"]].append(p)
    poly_ctx = {}
    for c, rows in sorted(pctx.items(), key=lambda kv: -len(kv[1])):
        ws = [r["w"] for r in rows]
        poly_ctx[c] = dict(polygons=len(rows), ambient_rgb_median=[wq([r["amb"][i] for r in rows], ws, .5) for i in range(3)],
                           brightness_quartiles=quart([sum(r["amb"]) / 3 for r in rows], ws))
    mm = Counter()
    for p in poly_rows: mm[p["mm"]] += p["w"]
    mmt = sum(mm.values())

    out = dict(
        schema_version=1,
        floor_context_rules=[dict(context=n, regex=r) for n, r in CONTEXT_RULES],
        colorlight=dict(
            thing_types={"ColorLight": "static", "ColorLightMovable": "movable (rare, 113 uses)"},
            constant_fields=constant, varying_fields=varying,
            colour_fields="R,G,B are the light colour; Color1 equals R,G,B in %.0f%% of lights (set both)" % (100 * rgb_eq_c1),
            change_intensity_single_equals_intensity_share=round(cis_eq_int, 3),
            radius_by_intensity={str(k): v.most_common(1)[0][0] for k, v in sorted(rad_by_int.items())},
            unknown7_by_intensity={str(k): v.most_common(1)[0][0] for k, v in sorted(u7_by_int.items())},
            presets=presets, other_presets_weighted_share=round(other_w / total_cl_w, 4)),
        density=dict(by_context=density,
                     per_map_lights_per_100_tiles=quart(lp100, lw),
                     per_map_colorlights_per_100_tiles=quart(cl100, lw),
                     colorlight_near_water_share=round(near_flags["colorlight_near_water"] / near_flags["colorlight_total"], 3),
                     colorlight_near_lava_share=round(near_flags["colorlight_near_lava"] / near_flags["colorlight_total"], 3)),
        spacing=spacing,
        pairing=dict(colorlight_to_nearest_source_px=quart(*pair_dist),
                     colorlight_within_46px_of_source_share=round(sum(w for d, w in zip(*pair_dist) if d <= 46) / sum(pair_dist[1]), 3)),
        visible_sources=vis,
        ambient=dict(map_by_kind=amb_kind, polygon_by_context=poly_ctx,
                     polygon_minimap_groups={str(k): round(v / mmt, 3) for k, v in mm.most_common(8)},
                     polygon_enter_function_share=round(sum(p["w"] for p in poly_rows if p["enter"]) / max(1e-9, sum(p["w"] for p in poly_rows)), 3),
                     maps=[dict((k, r[k]) for k in ("map", "kind", "ambient", "polygons", "coverage", "lights_per_100_tiles")) for r in map_rows]),
    )
    C.save_json("lighting.json", out)
    C.save_section("lighting.md", render_md(out))
    print("wrote rules/out/lighting.json and rules/sections/lighting.md;",
          len(presets), "presets,", len(vis), "visible source types,", len(map_rows), "maps")


# ================================================================ markdown
def render_md(o):
    cl, dn, amb = o["colorlight"], o["density"], o["ambient"]
    L = []
    a = L.append
    a("## Lighting\n")
    a("Source: `rules/lighting.py` -> `rules/out/lighting.json`. Style figures are campaign maps weighted by "
      "1/layout-group size; validity facts use all 157 maps. Quartiles are written as [25%, median, 75%].\n")
    a("**JSON schema (`lighting.json`)**: `floor_context_rules` (ordered regex -> context used everywhere below); "
      "`colorlight` {`constant_fields`, `varying_fields` (field -> distinct values), `radius_by_intensity`, "
      "`unknown7_by_intensity`, `presets[]` {id, family, animation, intensity_class, weighted_share, count, maps, "
      "rgb_median, intensity_median, radius_median, contexts, `xfer` = complete field set of the most common real light "
      "in the preset}}; `density` {by_context{ctx: tiles_weighted, colorlights/sources/all_lights_per_100_tiles}, "
      "per_map quartiles}; `spacing` {ctx: nearest-neighbour px quartiles}; `pairing`; `visible_sources` {type: kind, "
      "weighted_count, maps, contexts, dangerous, wall_mounted, share_with_colorlight_within_46px, paired_colorlight_presets, "
      "paired_offset_px_median, wall_relation[], distance_to_wall_centre_px_median}; `ambient` {map_by_kind, "
      "polygon_by_context, polygon_minimap_groups, maps[]}.\n")
    a("### ColorLight (invisible light) settings\n")
    a("- Fields that never vary across 13,145 lights in all maps (copy as-is): " + ", ".join(sorted(cl["constant_fields"])) + ".")
    a("- " + cl["colour_fields"] + ". `ChangeIntensitySingle` equals `LightIntensity` in %.0f%% of lights." % (100 * cl["change_intensity_single_equals_intensity_share"]))
    top = {k: cl["radius_by_intensity"][k] for k in ("63", "50", "49", "45", "40", "25") if k in cl["radius_by_intensity"]}
    a("- `LightRadius` and `Unknown7` are tied to `LightIntensity` (most common radius per intensity: %s). "
      "The standard light is intensity 63 / radius 181-182 (about 90%% of all lights); to make a light, copy a preset's "
      "`xfer` and change only the colour (R,G,B and Color1)." % ", ".join("%s->%s" % kv for kv in top.items()))
    a("\n| preset | share | maps | median RGB | intensity / radius | main contexts |\n|---|---|---|---|---|---|")
    for p in cl["presets"]:
        a("| %s | %.1f%% | %d | %s | %d / %d | %s |" % (p["id"], 100 * p["weighted_share"], p["maps"], p["rgb_median"],
                                                     p["intensity_median"], p["radius_median"],
                                                     ", ".join("%s %.0f%%" % (k, 100 * v) for k, v in list(p["contexts"].items())[:3])))
    a("\n### Density and spacing\n")
    a("- Per map, all light sources per 100 tiles: %s; ColorLights alone: %s." % (dn["per_map_lights_per_100_tiles"], dn["per_map_colorlights_per_100_tiles"]))
    a("\n| floor context | weighted tiles | ColorLights /100 tiles | visible sources /100 tiles | all /100 tiles | ColorLight nearest-neighbour px |\n|---|---|---|---|---|---|")
    for ctx, d in o["density"]["by_context"].items():
        a("| %s | %d | %.2f | %.2f | %.2f | %s |" % (ctx, d["tiles_weighted"], d["colorlights_per_100_tiles"],
                                                  d["sources_per_100_tiles"], d["all_lights_per_100_tiles"], o["spacing"].get(ctx, "")))
    a("\n- ColorLights near water (3 cells): %.0f%%; near lava: %.0f%%." % (100 * dn["colorlight_near_water_share"], 100 * dn["colorlight_near_lava_share"]))
    a("- Distance from a ColorLight to the nearest visible light source: %s px; %.0f%% sit within 46 px (2 cells) of one, i.e. most "
      "ColorLights are free-standing area lights, not just glows on torches." % (o["pairing"]["colorlight_to_nearest_source_px"],
                                                                                100 * o["pairing"]["colorlight_within_46px_of_source_share"]))
    a("\n### Visible light sources\n")
    a("| type | kind | weighted uses | maps | main contexts | wall-mounted | has ColorLight within 46 px | usual placement |\n|---|---|---|---|---|---|---|---|")
    for t, v in list(o["visible_sources"].items())[:28]:
        place = ""
        if v.get("wall_relation"):
            r0 = v["wall_relation"][0]
            place = "%s %s (%.0f%%), %s px from wall centre" % (r0["wall"], r0["side"], 100 * r0["share"], v["distance_to_wall_centre_px_median"])
        a("| %s | %s%s | %.1f | %d | %s | %s | %s | %s |" % (
            t, v["kind"], " (hurts)" if v["dangerous"] else "", v["weighted_count"], v["maps"],
            ", ".join("%s %.0f%%" % (k, 100 * s) for k, s in list(v["contexts"].items())[:2]),
            "yes" if v["wall_mounted"] else "", "" if v["share_with_colorlight_within_46px"] is None else "%.0f%%" % (100 * v["share_with_colorlight_within_46px"]),
            place))
    a("\n### Ambient colour and polygons\n")
    a("| map kind | maps | median ambient RGB | brightness [25/50/75] | lights /100 tiles | polygons per map | polygon coverage | examples |\n|---|---|---|---|---|---|---|---|")
    for k, v in amb["map_by_kind"].items():
        a("| %s | %d | %s | %s | %s | %s | %s | %s |" % (k, v["maps"], v["ambient_rgb_median"], v["brightness_quartiles"],
                                                       v["lights_per_100_tiles"], v["polygons_per_map"], v["polygon_coverage"],
                                                       ", ".join(v["examples"][:4])))
    a("\n| polygon dominant floor context | polygons | median ambient RGB | brightness [25/50/75] |\n|---|---|---|---|")
    for k, v in amb["polygon_by_context"].items():
        a("| %s | %d | %s | %s |" % (k, v["polygons"], v["ambient_rgb_median"], v["brightness_quartiles"]))
    a("\n- Polygon minimap groups (weighted share): " + ", ".join("%s: %.0f%%" % (k, 100 * v) for k, v in amb["polygon_minimap_groups"].items()) + ".")
    a("- Polygons with a player-enter script: %.0f%%." % (100 * amb["polygon_enter_function_share"]))
    covs = [r["coverage"] for r in amb["maps"]]
    a("- Polygons tile essentially the whole floor: %d of %d maps have >= 99%% of floor tiles inside a polygon "
      "(minimum %.2f). Every area needs a polygon carrying its ambient colour and minimap group." %
      (sum(1 for c in covs if c >= 0.99), len(covs), min(covs)))
    a("- Flames of type SmallFlame/MediumFlame/Flame/LargeFlame are DANGEROUS (they burn players); Westwood uses "
      "them mostly in lava areas. Use torches, TorchPole, candelabra, lanterns, basins and fireplaces as safe light.")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
