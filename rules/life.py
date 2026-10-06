"""Townsfolk, shops, waypoints and roaming in Westwood's campaign maps (phase 2 rule mining).

Townsfolk: shopkeepers (Shopkeeper*), maidens (Maiden), civilian NPCs (NPC objects that are immortal or
carry no weapon) and special friendlies (AirshipCaptain, Wounded*). Armed, mortal NPCs are reported
separately as "armed NPCs" (guards, soldiers, enemy humans).

Waypoint contexts are judged from the surroundings of each point: walls within 5 cells (built vs
natural materials), the floor, whether the point is inside a building room (rules/rooms.py), and
whether townsfolk are within 30 cells (town vs dungeon).

Writes rules/out/life.json and rules/sections/life.md. Run: py rules/life.py
"""
import collections, json, math, re, statistics as st
import common as c
import rooms as R

ACTIONS = ["IDLE", "WAIT", "WAIT_RELATIVE", "ESCORT", "GUARD", "HUNT", "RETREAT", "MOVE_TO", "FAR_MOVE_TO", "DODGE",
           "ROAM", "PICKUP_OBJECT", "DROP_OBJECT", "FIND_OBJECT", "RETREAT_TO_MASTER", "FIGHT", "MELEE_ATTACK",
           "MISSILE_ATTACK", "CAST_SPELL_ON_OBJECT", "CAST_SPELL_ON_LOCATION", "CAST_DURATION_SPELL", "BLOCK_ATTACK",
           "BLOCK_FINISH", "WEAPON_BLOCK", "FLEE", "FACE_LOCATION", "FACE_OBJECT", "FACE_ANGLE", "SET_ANGLE",
           "RANDOM_WALK", "DYING", "DEAD", "REPORT", "MORPH_INTO_CHEST", "MORPH_BACK_TO_SELF", "GET_UP", "CONFUSED",
           "MOVE_TO_HOME", "INVALID"]   # NoxShared NoxEnums.AIActionStrings
TREE_WALL = re.compile(r"Tree|Decidious|Coni-|Aspen|Hedge|Shrub|Root|Thorn", re.I)
OUTDOOR_FLOOR = re.compile(r"Grass|Weeds|Swamp|Water|Mud|Sand|Snow", re.I)
ROAD_FLOOR = re.compile(r"Cobble|Brick|Dirt|Road|Path|Tile|Stone", re.I)
TOWN_RADIUS, POP_RADIUS = 30, 12


def q(vals):
    vals = sorted(vals)
    if not vals: return None
    if len(vals) < 4: return [round(vals[0], 2), round(vals[len(vals) // 2], 2), round(vals[-1], 2)]
    a, b, d = st.quantiles(vals, n=4)
    return [round(a, 2), round(b, 2), round(d, 2)]


def wq(pairs):
    """Weighted quartiles from (value, weight) pairs; weights are 1, 1/2, 1/3, 1/4 (replicate x12)."""
    vals = []
    for v, w in pairs: vals += [v] * round(12 * w)
    return q(vals)


def share(pairs, top=None):
    tot = collections.defaultdict(float)
    for k, w in pairs: tot[k] += w
    s = sum(tot.values()) or 1
    return {str(k): round(v / s, 4) for k, v in sorted(tot.items(), key=lambda kv: -kv[1])[:top]}


def role(o, inventory):
    t = o["type"]
    if t.startswith("Shopkeeper"): return "shopkeeper"
    if t == "Maiden": return "maiden"
    if t == "AirshipCaptain" or t.startswith("Wounded"): return "special"
    if o.get("xtype") == "NPCXfer":
        armed = any(i.get("xtype") == "WeaponXfer" for i in inventory)
        return "civilian" if (o["xfer"].get("Immortal") or not armed) else "armed_npc"
    return None


def nearest(p, pts):
    return min((math.dist(p, q) for q in pts), default=None)


class MapCtx:
    """Per-map lookups: building-room cells, walls, tiles, doors, waypoints, townsfolk."""

    def __init__(self, m):
        self.m = m
        comp, comps, walls, tiles, cell_tile, doors = R.components(m)
        rooms = R.analyse_map(m)
        building = {r["comp"] for r in rooms if r["kind"] == "building"}
        self.indoor = {cell for cid in building for cell in comps[cid]["cells"]}
        self.walls, self.tiles, self.cell_tile = walls, tiles, cell_tile
        self.door_pts = [(round(o["x"] / c.CELL), round(o["y"] / c.CELL)) for o, _ in doors]
        self.rooms = rooms
        all_objs = c.objects(m, top_level_only=False)
        kids = collections.defaultdict(list)
        for o in all_objs:
            if o["parent"] is not None: kids[o["parent"]].append(o)
        self.top = [o for o in all_objs if o["parent"] is None]
        self.folk = []
        for o in self.top:
            r = role(o, kids[o["id"]])
            if r: self.folk.append(dict(o=o, role=r, inv=[i["type"] for i in kids[o["id"]]], cell=c.obj_cell(o)))
        self.town_pts = [f["cell"] for f in self.folk if f["role"] in ("civilian", "maiden", "shopkeeper")]
        with c.db() as con:
            self.wps = {r["n"]: dict(r) for r in con.execute("SELECT n, name, x, y FROM waypoints WHERE map=?", (m,))}
            self.links = [tuple(r) for r in con.execute("SELECT a, b, flag FROM waypoint_links WHERE map=?", (m,))]

    def floor_at(self, cell):
        t = self.cell_tile.get(cell)
        return self.tiles[t]["material"] if t else None

    def context(self, cell):
        """town / dungeon / cave / wilderness for a grid cell."""
        x, y = cell
        if cell in self.indoor:
            return "town" if self.near_town(cell) else "dungeon"
        near = [self.walls[(x + dx, y + dy)]["material"] for dx in range(-5, 6) for dy in range(-5, 6)
                if (x + dx, y + dy) in self.walls]
        solid = [w for w in near if "Invisible" not in w]
        floor = self.floor_at(cell) or ""
        if not solid:
            return "wilderness" if OUTDOOR_FLOOR.search(floor) or not floor else ("town" if self.near_town(cell) else "dungeon")
        built = sum(1 for w in solid if not R.NATURAL_WALL.search(w)) / len(solid)
        if built >= 0.5:
            return "town" if self.near_town(cell) else "dungeon"
        trees = sum(1 for w in solid if TREE_WALL.search(w)) / len(solid)
        return "wilderness" if trees >= 0.5 or OUTDOOR_FLOOR.search(floor) else "cave"

    def near_town(self, cell):
        return any(abs(cell[0] - p[0]) <= TOWN_RADIUS and abs(cell[1] - p[1]) <= TOWN_RADIUS for p in self.town_pts)

    def wall_distance(self, cell, r=8):
        x, y = cell
        best = None
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if (x + dx, y + dy) in self.walls:
                    d = math.hypot(dx, dy)
                    if best is None or d < best: best = d
        return best if best is not None else r + 1


def townsfolk(ctxs, W):
    folk = [(cx, f) for cx in ctxs for f in cx.folk]
    out = {}
    roles = ("civilian", "maiden", "shopkeeper", "special", "armed_npc")
    out["role_counts"] = {r: dict(objects=sum(1 for _, f in folk if f["role"] == r),
                                  maps=len({cx.m for cx, f in folk if f["role"] == r})) for r in roles}
    # towns: maps with 5+ civilians/maidens/shopkeepers
    towns = []
    for cx in ctxs:
        n = collections.Counter(f["role"] for f in cx.folk)
        friendly = n["civilian"] + n["maiden"] + n["shopkeeper"]
        if friendly < 5: continue
        pop = {t for t in cx.tiles if any(abs(t[0] + 1 - p[0]) <= POP_RADIUS and abs(t[1] + 1 - p[1]) <= POP_RADIUS for p in cx.town_pts)}
        b_rooms = [r for r in cx.rooms if r["kind"] == "building" and
                   any(abs((r["bbox"][0] + r["bbox"][2]) / 2 - p[0]) <= TOWN_RADIUS and abs((r["bbox"][1] + r["bbox"][3]) / 2 - p[1]) <= TOWN_RADIUS for p in cx.town_pts)]
        towns.append(dict(map=cx.m, townsfolk=friendly, civilians=n["civilian"], maidens=n["maiden"], shopkeepers=n["shopkeeper"],
                          armed_npcs=n["armed_npc"], populated_tiles=len(pop), building_rooms_near=len(b_rooms),
                          buildings_near=len({r["building"] for r in b_rooms}),
                          per_100_populated_tiles=round(100 * friendly / max(1, len(pop)), 2),
                          per_building=round(friendly / max(1, len({r["building"] for r in b_rooms})), 2),
                          weight=W[cx.m]))
    out["towns"] = sorted(towns, key=lambda t: -t["townsfolk"])
    tw = [(t, t["weight"]) for t in towns]
    out["town_quartiles"] = dict(
        town_maps=len(towns), townsfolk=wq((t["townsfolk"], w) for t, w in tw),
        shopkeepers=wq((t["shopkeepers"], w) for t, w in tw),
        per_100_populated_tiles=wq((t["per_100_populated_tiles"], w) for t, w in tw),
        per_building=wq((t["per_building"], w) for t, w in tw),
        buildings_near=wq((t["buildings_near"], w) for t, w in tw))
    # behaviour settings per role
    settings = {}
    for r in ("civilian", "maiden", "shopkeeper", "armed_npc"):
        fs = [(cx, f) for cx, f in folk if f["role"] == r]
        if not fs: continue
        x = lambda f, k, d=None: f["o"]["xfer"].get(k, d)
        settings[r] = dict(
            n=len(fs), maps=len({cx.m for cx, _ in fs}),
            default_action=share(((ACTIONS[x(f, "DefaultAction", 0)] if 0 <= x(f, "DefaultAction", 0) < len(ACTIONS) else x(f, "DefaultAction"), W[cx.m]) for cx, f in fs)),
            roam_path_flag=share(((x(f, "ActionRoamPathFlag"), W[cx.m]) for cx, f in fs), 8),
            immortal=share(((bool(x(f, "Immortal")), W[cx.m]) for cx, f in fs)),
            team=share(((f["o"]["team"], W[cx.m]) for cx, f in fs)),
            aggressiveness=share(((round(x(f, "Aggressiveness", 0), 2), W[cx.m]) for cx, f in fs), 6),
            sight_range=share(((round(x(f, "SightRange", 0)), W[cx.m]) for cx, f in fs), 5),
            retreat_ratio=share(((round(x(f, "RetreatRatio", 0), 2), W[cx.m]) for cx, f in fs), 5),
            health=wq(((x(f, "Health", 0) or 0), W[cx.m]) for cx, f in fs),
            npc_speed=share(((round(x(f, "NPCSpeed", 0) or 0, 2), W[cx.m]) for cx, f in fs), 5) if r in ("civilian", "armed_npc") else None,
            has_script_name=round(sum(W[cx.m] for cx, f in fs if f["o"]["scr"]) / sum(W[cx.m] for cx, f in fs), 3),
            has_script_events=round(sum(W[cx.m] for cx, f in fs if any(e for e in (x(f, "ScriptEvents") or []) if e)) / sum(W[cx.m] for cx, f in fs), 3),
            indoors=round(sum(W[cx.m] for cx, f in fs if f["cell"] in cx.indoor) / sum(W[cx.m] for cx, f in fs), 3),
            door_distance_cells=wq(((nearest(f["cell"], cx.door_pts) or 99), W[cx.m]) for cx, f in fs),
        )
    out["settings"] = settings
    # clothing
    civ = [(cx, f) for cx, f in folk if f["role"] == "civilian"]
    out["clothing"] = dict(
        items_per_civilian=wq((len(f["inv"]), W[cx.m]) for cx, f in civ),
        item_types=share(((t, W[cx.m]) for cx, f in civ for t in f["inv"]), 25),
        outfits=share((("+".join(sorted(f["inv"])) or "(none)", W[cx.m]) for cx, f in civ), 15))
    # shopkeepers: shop contents and surroundings
    shops = [(cx, f) for cx, f in folk if f["role"] == "shopkeeper"]
    item_counts, units, kinds, mults, greet, near = [], [], collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    for cx, f in shops:
        info = f["o"]["xfer"].get("ShopkeeperInfo") or {}
        items = info.get("ShopItems") or []
        n_units = 0
        for it in items:
            m = re.match(r"x(\d+)\s+(\S+)", str(it))
            if m:
                n_units += int(m[1]); kinds[m[2]] += W[cx.m]
        item_counts.append((len(items), W[cx.m])); units.append((n_units, W[cx.m]))
        mults[(info.get("BuyValueMultiplier"), info.get("SellValueMultiplier"))] += W[cx.m]
        g = info.get("ShopkeeperGreetingText") or ""
        greet["map:key string id" if ":" in g else ("empty" if not g else "other")] += W[cx.m]
        for o in cx.top:
            if o is f["o"]: continue
            if math.dist((o["x"], o["y"]), (f["o"]["x"], f["o"]["y"])) <= 3 * c.CELL:
                near[o["type"]] += W[cx.m]
    out["shops"] = dict(
        n=len(shops), maps=len({cx.m for cx, _ in shops}),
        shopkeeper_types=share(((f["o"]["type"], W[cx.m]) for cx, f in shops)),
        item_lines_per_shop=wq(item_counts), item_units_per_shop=wq(units),
        top_items=share(kinds.items(), 30),
        buy_sell_multipliers=[dict(buy=b, sell=s, share=round(v / sum(mults.values()), 3)) for (b, s), v in mults.most_common(5)],
        greeting_text=share(greet.items()),
        objects_within_3_cells=share(near.items(), 25),
        note="ShopItems lists are truncated at 64 entries by the corpus export; 'xN Type' means N units of Type.")
    return out


def waypoints(ctxs, W):
    per_ctx_wp, per_ctx_tiles = collections.Counter(), collections.Counter()
    lengths, flags, degrees, bidir, wall_d, road = [], collections.Counter(), collections.Counter(), [], collections.defaultdict(list), collections.defaultdict(list)
    graph_stats, named = [], 0.0
    tile_road = collections.defaultdict(list)
    for cx in ctxs:
        w = W[cx.m]
        # tile contexts on a stride (every 3rd tile) to keep this fast; scaled back up
        for i, t in enumerate(cx.tiles):
            if i % 3: continue
            ctx = cx.context((t[0] + 1, t[1] + 1))
            per_ctx_tiles[ctx] += 3 * w
            tile_road[ctx].append((1 if ROAD_FLOOR.search(cx.tiles[t]["material"]) else 0, w))
        if not cx.wps: continue
        deg = collections.Counter()
        pairs = set()
        for a, b, fl in cx.links:
            if a not in cx.wps or b not in cx.wps: continue
            pa, pb = cx.wps[a], cx.wps[b]
            lengths.append((math.dist((pa["x"], pa["y"]), (pb["x"], pb["y"])) / c.CELL, w))
            flags[fl] += w
            deg[a] += 1
            pairs.add((a, b))
        bidir.append((sum(1 for a, b in pairs if (b, a) in pairs) / max(1, len(pairs)), w))
        for n, p in cx.wps.items():
            cell = (int(p["x"] // c.CELL), int(p["y"] // c.CELL))
            ctx = cx.context(cell)
            per_ctx_wp[ctx] += w
            degrees[min(deg[n], 6)] += w
            wall_d[ctx].append((cx.wall_distance(cell), w))
            fl = cx.floor_at(cell) or ""
            road[ctx].append((1 if ROAD_FLOOR.search(fl) else 0, w))
            if p["name"]: named += w
        # components and cycles (undirected)
        und = collections.defaultdict(set)
        for a, b in pairs: und[a].add(b); und[b].add(a)
        seen, comps = set(), 0
        for n in cx.wps:
            if n in seen: continue
            comps += 1; stack = [n]; seen.add(n)
            while stack:
                for k in und[stack.pop()]:
                    if k not in seen: seen.add(k); stack.append(k)
        edges = len({tuple(sorted(p)) for p in pairs})
        graph_stats.append(dict(map=cx.m, waypoints=len(cx.wps), edges=edges, components=comps,
                                cycles=edges - len(cx.wps) + comps, weight=w))
    density = {k: round(100 * per_ctx_wp[k] / per_ctx_tiles[k], 3) for k in per_ctx_tiles if per_ctx_tiles[k]}
    tot_wp = sum(per_ctx_wp.values()) or 1
    return dict(
        density_per_100_tiles=density,
        waypoint_share_by_context=share(per_ctx_wp.items()),
        link_length_cells=wq(lengths),
        link_flags=share(flags.items()),
        degree=share(degrees.items()),
        bidirectional_link_share=wq(bidir),
        named_waypoint_share=round(named / tot_wp, 3),
        wall_distance_cells_by_context={k: wq(v) for k, v in wall_d.items()},
        on_road_floor_share_by_context={k: round(sum(a * b for a, b in v) / max(1e-9, sum(b for _, b in v)), 3) for k, v in road.items()},
        road_floor_share_of_tiles_by_context={k: round(sum(a * b for a, b in v) / max(1e-9, sum(b for _, b in v)), 3) for k, v in tile_road.items()},
        graphs=dict(maps_with_waypoints=len(graph_stats),
                    waypoints_per_map=wq((g["waypoints"], g["weight"]) for g in graph_stats),
                    components_per_map=wq((g["components"], g["weight"]) for g in graph_stats),
                    cycles_per_map=wq((g["cycles"], g["weight"]) for g in graph_stats),
                    per_map=[{k: g[k] for k in ("map", "waypoints", "edges", "components", "cycles")} for g in graph_stats]),
        context_method="cell context from walls within 5 cells (built vs natural), floor material, building rooms, townsfolk within 30 cells; tiles sampled every 3rd")


def roaming(ctxs, W):
    rows = []
    for cx in ctxs:
        flags_present = collections.Counter(fl for _, _, fl in cx.links)
        for o in cx.top:
            if o.get("xtype") not in ("NPCXfer", "MonsterXfer"): continue
            x = o["xfer"]
            if x.get("DefaultAction") != 10: continue
            rf = x.get("ActionRoamPathFlag") or 0
            pos = (o["x"], o["y"])
            near = [n for n, p in cx.wps.items() if math.dist(pos, (p["x"], p["y"])) <= 6 * c.CELL]
            near_link_flags = {fl for a, b, fl in cx.links if a in near}
            rows.append(dict(map=cx.m, type=o["type"], townsperson=o["type"] in ("NPC", "Maiden"), flag=rf,
                             nearest_wp=(min((math.dist(pos, (p["x"], p["y"])) for p in cx.wps.values()), default=None) or 0) / c.CELL if cx.wps else None,
                             matching_link_in_map=any(fl & rf for fl in flags_present), matching_link_nearby=any(fl & rf for fl in near_link_flags),
                             w=W[cx.m]))
    def summ(rs):
        if not rs: return None
        tw = sum(r["w"] for r in rs)
        return dict(n=len(rs), roam_flag=share(((r["flag"], r["w"]) for r in rs), 8),
                    nearest_waypoint_cells=wq(((r["nearest_wp"] if r["nearest_wp"] is not None else 99), r["w"]) for r in rs),
                    share_flag_matches_some_link=round(sum(r["w"] for r in rs if r["matching_link_in_map"]) / tw, 3),
                    share_matching_link_within_6_cells=round(sum(r["w"] for r in rs if r["matching_link_nearby"]) / tw, 3))
    return dict(townsfolk=summ([r for r in rows if r["townsperson"]]), monsters=summ([r for r in rows if not r["townsperson"]]),
                flag_semantics="ActionRoamPathFlag is a bitmask; a roaming creature follows waypoint links whose flag shares a bit "
                               "with it (255 has every bit, so it uses any link). 128 is the editor's default link flag and carries 87% "
                               "of links (general paths); the single-bit flags 1..64 appear on small separate networks, "
                               "which reads as private patrol/escort routes (inferred, not verified in the engine).")


def main():
    W = c.campaign_weights()
    ctxs = [MapCtx(m) for m in c.campaign_maps()]
    data = dict(schema_version=1, townsfolk=townsfolk(ctxs, W), waypoints=waypoints(ctxs, W), roaming=roaming(ctxs, W))
    data["townsfolk"]["towns"] = [{k: v for k, v in t.items() if k != "weight"} for t in data["townsfolk"]["towns"]]
    c.save_json("life.json", data)
    write_md(data)
    tf = data["townsfolk"]
    print("townsfolk roles:", tf["role_counts"])
    print("town maps:", tf["town_quartiles"]["town_maps"], "| waypoint density:", data["waypoints"]["density_per_100_tiles"])


def fmt(d, n=8):
    return ", ".join(f"{k} {v:.0%}" for k, v in list((d or {}).items())[:n])


def write_md(d):
    tf, wp, ro = d["townsfolk"], d["waypoints"], d["roaming"]
    tq, S = tf["town_quartiles"], tf["settings"]
    rc = tf["role_counts"]
    sh = tf["shops"]
    L = [
        "# Townsfolk, shops, waypoints and roaming",
        "",
        "Source: `rules/life.py` over the 107 campaign maps; shares and quartiles ([25%, median, 75%])",
        "weighted by `1 / layout group size`. Roles: **civilian** = NPC object that is immortal or unarmed;",
        "**armed_npc** = mortal NPC carrying a weapon (guards, soldiers, hostile humans); **maiden**;",
        "**shopkeeper** (Shopkeeper*); **special** (AirshipCaptain, Wounded*). A **town map** has 5+ civilians,",
        f"maidens and shopkeepers. Populated tiles = tiles within {POP_RADIUS} cells of a townsperson.",
        "",
        "## JSON schema (`rules/out/life.json`)",
        "",
        "```",
        "{schema_version: 1,",
        " townsfolk: {role_counts{role: {objects, maps}},",
        "   towns[{map, townsfolk, civilians, maidens, shopkeepers, armed_npcs, populated_tiles,",
        "          building_rooms_near, buildings_near, per_100_populated_tiles, per_building}],",
        "   town_quartiles{town_maps, townsfolk, shopkeepers, per_100_populated_tiles, per_building, buildings_near},",
        "   settings{role: {n, maps, default_action{ACTION: share}, roam_path_flag{flag: share}, immortal{..}, team{..},",
        "            aggressiveness{..}, sight_range{..}, retreat_ratio{..}, health_q, npc_speed{..},",
        "            has_script_name, has_script_events, indoors, door_distance_cells_q}},",
        "   clothing{items_per_civilian_q, item_types{type: share}, outfits{'A+B+C': share}},",
        "   shops{n, maps, shopkeeper_types, item_lines_per_shop_q, item_units_per_shop_q, top_items,",
        "         buy_sell_multipliers[{buy, sell, share}], greeting_text, objects_within_3_cells}},",
        " waypoints: {density_per_100_tiles{context: n}, waypoint_share_by_context, link_length_cells_q,",
        "   link_flags{flag: share}, degree{n: share}, bidirectional_link_share_q, named_waypoint_share,",
        "   wall_distance_cells_by_context{context: q}, on_road_floor_share_by_context, road_floor_share_of_tiles_by_context,",
        "   graphs{maps_with_waypoints, waypoints_per_map_q, components_per_map_q, cycles_per_map_q, per_map[...]}},",
        " roaming: {townsfolk|monsters: {n, roam_flag{..}, nearest_waypoint_cells_q, share_flag_matches_some_link,",
        "           share_matching_link_within_6_cells}, flag_semantics}}",
        "```",
        "",
        "## Townsfolk",
        "",
        "- **Who.** " + ", ".join(f"{r} {v['objects']} in {v['maps']} maps" for r, v in rc.items()) + ".",
        f"- **How many.** {tq['town_maps']} town maps. Townsfolk per town {tq['townsfolk']}, shopkeepers {tq['shopkeepers']},"
        f" buildings near townsfolk {tq['buildings_near']}; {tq['per_100_populated_tiles']} townsfolk per 100 populated"
        f" tiles; {tq['per_building']} per building. Largest towns: "
        + ", ".join(f"{t['map']} ({t['townsfolk']})" for t in tf["towns"][:6]) + ".",
    ]
    for r in ("civilian", "maiden", "shopkeeper", "armed_npc"):
        s = S.get(r)
        if not s: continue
        L.append(f"- **{r} settings** ({s['n']} in {s['maps']} maps). Default action: {fmt(s['default_action'], 4)}; roam flag:"
                 f" {fmt(s['roam_path_flag'], 4)}; immortal: {fmt(s['immortal'])}; team: {fmt(s['team'])}; aggressiveness:"
                 f" {fmt(s['aggressiveness'], 4)}; sight range: {fmt(s['sight_range'], 3)}; health {s['health']}."
                 f" Script name {s['has_script_name']:.0%}, script events {s['has_script_events']:.0%}; indoors {s['indoors']:.0%};"
                 f" distance to nearest door {s['door_distance_cells']} cells.")
    cl = tf["clothing"]
    L += [
        f"- **Clothing (civilians).** Items {cl['items_per_civilian']}; types: {fmt(cl['item_types'], 12)}. Common outfits:"
        f" {fmt(cl['outfits'], 6)}.",
        "",
        "## Shops",
        "",
        f"- {sh['n']} shopkeepers in {sh['maps']} maps: {fmt(sh['shopkeeper_types'], 8)}.",
        f"- Item lines per shop {sh['item_lines_per_shop']}, units {sh['item_units_per_shop']}. Most stocked: {fmt(sh['top_items'], 15)}.",
        "- Buy/sell multipliers: " + "; ".join(f"{m['buy']}/{m['sell']} ({m['share']:.0%})" for m in sh["buy_sell_multipliers"]) + ".",
        f"- Greeting text: {fmt(sh['greeting_text'])} (a string-table id such as `Con02a:Mystic`).",
        f"- Objects within 3 cells of a shopkeeper (counters, racks, shelves): {fmt(sh['objects_within_3_cells'], 15)}.",
        "",
        "## Waypoints",
        "",
        "- **Density per 100 floor tiles:** " + ", ".join(f"{k} {v}" for k, v in wp["density_per_100_tiles"].items())
        + f". Share of all waypoints: {fmt(wp['waypoint_share_by_context'])}.",
        f"- **Spacing.** Linked waypoints are {wp['link_length_cells']} cells apart. Degree: {fmt(wp['degree'])}."
        f" Bidirectional link share per map {wp['bidirectional_link_share']}. Named waypoints {wp['named_waypoint_share']:.1%}.",
        f"- **Flags.** {fmt(wp['link_flags'])}.",
        f"- **Graph shape.** {wp['graphs']['maps_with_waypoints']} maps; waypoints per map {wp['graphs']['waypoints_per_map']};"
        f" separate networks per map {wp['graphs']['components_per_map']}; independent loops per map {wp['graphs']['cycles_per_map']}.",
        "- **Placement.** Distance to the nearest wall (cells): " + ", ".join(f"{k} {v}" for k, v in wp["wall_distance_cells_by_context"].items())
        + ". Waypoints on road-like floors (cobble/brick/dirt/tile/stone) vs all tiles: "
        + ", ".join(f"{k} {wp['on_road_floor_share_by_context'][k]:.0%} vs {wp['road_floor_share_of_tiles_by_context'].get(k, 0):.0%}"
                    for k in wp["on_road_floor_share_by_context"]) + ".",
        "",
        "## Roaming",
        "",
        f"- {ro['flag_semantics']}",
    ]
    for k in ("townsfolk", "monsters"):
        s = ro[k]
        if s:
            L.append(f"- **Roaming {k}** ({s['n']}): roam flags {fmt(s['roam_flag'], 5)}; nearest waypoint {s['nearest_waypoint_cells']} cells;"
                     f" flag matches a link in the map {s['share_flag_matches_some_link']:.0%}, within 6 cells {s['share_matching_link_within_6_cells']:.0%}.")
    L += ["", "## Notes for generation", "",
          "- Give townsfolk scripts only when they have dialogue; plain roamers need DefaultAction ROAM (10) and a roam flag",
          "  that matches the link flags of a nearby waypoint network (128 for general paths).",
          "- Stationary townsfolk (GUARD/IDLE) stand indoors near doors, counters and shop shelves."]
    c.save_section("life.md", "\n".join(L) + "\n")


if __name__ == "__main__":
    main()
