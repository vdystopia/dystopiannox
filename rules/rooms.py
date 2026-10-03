"""Rooms and buildings in Westwood's single-player maps (phase 2 rule mining).

Rooms are found by flood-filling every non-wall cell of the 256x256 grid (4-connected; diagonal wall
chains block 4-connectivity); door gaps are closed with a virtual wall so each room is its own
component. A component is a room when it does not touch the grid border and has 2..MAX_ROOM_TILES
floor tiles. A room is a "building" room when at least 60% of its solid (non-invisible) wall cells
are built materials, otherwise "natural" (cave pockets, tree-ringed clearings). Rooms that share a
wall cell or a door form a building.

Writes rules/out/rooms.json (summary statistics + a room index for phase 3) and
rules/sections/rooms.md. Run: py rules/rooms.py
"""
import collections, re, statistics as st
import common as c

MAX_ROOM_TILES = 400
DOOR_GAP = {"South": (-1, -1), "North": (0, 0), "East": (-1, 0), "West": (0, -1)}
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
NATURAL_WALL = re.compile(r"Cave|Rock|Dirt|Root|Tree|Decidious|Coni-|Aspen|Hedge|Shrub|Thorn|Volcano|IceWall|Shard|Invisible|Mine", re.I)
LIGHT_NAME = re.compile(r"ColorLight|Torch|Candle|Lantern|Lamp|Sconse|Sconce|Flame|Fireplace|Brazier|Basin.*Lit|Chandelier|Lights?$", re.I)


def obj_kind(o):
    """furniture / light / door / item / creature / other, from the object's name and class."""
    cls = o.get("class") or ""
    t = o["type"]
    if "DOOR" in cls: return "door"
    if "MONSTER" in cls or o.get("xtype") == "NPCXfer": return "creature"
    if LIGHT_NAME.search(t) or "FIRE" in cls: return "light"
    if any(k in cls for k in ("TRIGGER", "TRANSPORTER", "HOLE", "MONSTERGENERATOR")) or t == "PlayerStart": return "other"
    if "OBSTACLE" in cls or "IMMOBILE" in cls: return "furniture"
    if "SIMPLE" in cls: return "item"
    return "other"


def door_gaps(map_name, walls):
    """[(door object, gap cell)] using the placement rule verified on Westwood's doors."""
    out = []
    for o in c.objects(map_name):
        if o.get("xtype") != "DoorXfer": continue
        cx, cy = round(o["x"] / c.CELL), round(o["y"] / c.CELL)
        d = DOOR_GAP.get(o["xfer"].get("Direction"), (0, 0))
        g = (cx + d[0], cy + d[1])
        if g in walls:  # rule mismatch: take any open cell around the door corner
            g = next(((cx + a, cy + b) for a, b in ((-1, -1), (0, 0), (-1, 0), (0, -1)) if (cx + a, cy + b) not in walls), g)
        out.append((o, g))
    return out


def components(map_name):
    """Flood fill: returns (comp: cell -> id, comps: [dict(cells, enclosed)], walls, tiles, cell_tile, doors)."""
    walls = c.walls(map_name)
    tiles = c.tiles(map_name)
    cell_tile = {}
    for (x, y) in tiles:
        for cell in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
            cell_tile.setdefault(cell, (x, y))
    doors = door_gaps(map_name, walls)
    blocked = set(walls) | {g for _, g in doors}
    comp, comps = {}, []
    for start in cell_tile:
        if start in comp or start in blocked: continue
        cid = len(comps); comp[start] = cid; q = [start]; cells = []
        enclosed = True
        while q:
            p = q.pop(); cells.append(p)
            for dx, dy in N4:
                n = (p[0] + dx, p[1] + dy)
                if not (0 <= n[0] < 256 and 0 <= n[1] < 256):
                    enclosed = False; continue
                if n in blocked or n in comp: continue
                comp[n] = cid; q.append(n)
        comps.append(dict(cells=cells, enclosed=enclosed))
    return comp, comps, walls, tiles, cell_tile, doors


def analyse_map(map_name):
    comp, comps, walls, tiles, cell_tile, doors = components(map_name)
    in_comp = collections.defaultdict(list)
    for o in c.objects(map_name):
        cid = comp.get(c.obj_cell(o))
        if cid is not None: in_comp[cid].append(o)
    rooms = []
    for cid, cp in enumerate(comps):
        cells = cp["cells"]
        tset = [p for p in cells if p in tiles]
        if not cp["enclosed"] or not (2 <= len(tset) <= MAX_ROOM_TILES): continue
        cellset = set(cells)
        us = [x + y for x, y in cells]; vs = [x - y for x, y in cells]
        rdoors = []
        for o, g in doors:
            nb = [(g[0] + dx, g[1] + dy) for dx, dy in N4]
            if not any(n in cellset for n in nb): continue
            beyond = [n for n in nb if n not in cellset and n in comp]
            outside_mat = next((tiles[cell_tile[n]]["material"] for n in beyond if n in cell_tile), None)
            rdoors.append(dict(id=o["id"], type=o["type"], dir=o["xfer"].get("Direction"), gap=list(g),
                               to=comp[beyond[0]] if beyond else None, outside=outside_mat))
        wall_cells = {(p[0] + dx, p[1] + dy) for p in cells for dx, dy in N4 if (p[0] + dx, p[1] + dy) in walls}
        floors = collections.Counter(tiles[t]["material"] for t in tset)
        wmat = collections.Counter(walls[w]["material"] for w in wall_cells)
        solid = sum(n for m, n in wmat.items() if "Invisible" not in m) or 1
        built = sum(n for m, n in wmat.items() if not NATURAL_WALL.search(m) and "Invisible" not in m) / solid
        objs = in_comp[cid]
        rooms.append(dict(id=f"{map_name}:{cid}", map=map_name, comp=cid, tiles=len(tset),
                          kind="building" if built >= 0.6 else "natural",
                          bbox=[min(x for x, _ in cells), min(y for _, y in cells), max(x for x, _ in cells), max(y for _, y in cells)],
                          u_extent=(max(us) - min(us)) / 2 + 1, v_extent=(max(vs) - min(vs)) / 2 + 1,
                          floor=floors.most_common(1)[0][0], floors=dict(floors.most_common(4)),
                          walls=dict(wmat.most_common(4)), wall_cells=wall_cells, doors=rdoors,
                          counts=dict(collections.Counter(obj_kind(o) for o in objs)),
                          objects=[o["id"] for o in objs],
                          object_types=collections.Counter(o["type"] for o in objs if obj_kind(o) in ("furniture", "light"))))
    # buildings: rooms sharing a wall cell or connected by a door
    parent = list(range(len(rooms)))

    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    by_wall = collections.defaultdict(list)
    for i, r in enumerate(rooms):
        for w in r["wall_cells"]: by_wall[w].append(i)
    comp_room = {r["comp"]: i for i, r in enumerate(rooms)}
    for ids in by_wall.values():
        for j in ids[1:]: parent[find(j)] = find(ids[0])
    for i, r in enumerate(rooms):
        for d in r["doors"]:
            if d["to"] in comp_room:
                parent[find(comp_room[d["to"]])] = find(i)
                d["to"] = rooms[comp_room[d["to"]]]["id"]
            else:
                d["to"] = None                # leads outside
    for i, r in enumerate(rooms):
        r["building"] = f"{map_name}:b{find(i)}"
        del r["wall_cells"]
    return rooms


def q(vals):
    vals = sorted(vals)
    if not vals: return None
    if len(vals) < 4: return [vals[0], vals[len(vals) // 2], vals[-1]]
    a, b, d = st.quantiles(vals, n=4)
    return [round(a, 2), round(b, 2), round(d, 2)]


def share(pairs, top=None):
    """pairs of (key, weight) -> {key: share}, largest first."""
    tot = collections.defaultdict(float)
    for k, w in pairs: tot[k] += w
    s = sum(tot.values()) or 1
    items = sorted(tot.items(), key=lambda kv: -kv[1])[:top]
    return {str(k): round(v / s, 4) for k, v in items}


def stats(rooms, W):
    """Weighted statistics for a set of rooms (weights are 1, 1/2, 1/3, 1/4: replicate x12)."""
    if not rooms: return {}
    tw = sum(W(r) for r in rooms)

    def wq(key):
        vals = []
        for r in rooms: vals += [key(r)] * round(12 * W(r))
        return q(vals)
    buildings = collections.defaultdict(list)
    for r in rooms: buildings[r["building"]].append(r)
    io = collections.Counter()
    for r in rooms:
        for d in r["doors"]:
            if d["to"] is None and d["outside"]: io[(r["floor"], d["outside"])] += W(r)
    io_tot = sum(io.values()) or 1
    return dict(
        rooms=len(rooms), rooms_weighted=round(tw, 1), buildings=len(buildings),
        tiles_per_room_q=wq(lambda r: r["tiles"]),
        u_extent_cells_q=wq(lambda r: r["u_extent"]), v_extent_cells_q=wq(lambda r: r["v_extent"]),
        aspect_q=wq(lambda r: round(max(r["u_extent"], r["v_extent"]) / max(1, min(r["u_extent"], r["v_extent"])), 2)),
        size_bands={band: round(sum(W(r) for r in rooms if lo <= r["tiles"] < hi) / tw, 3)
                    for band, lo, hi in (("2-9", 2, 10), ("10-24", 10, 25), ("25-49", 25, 50), ("50-99", 50, 100),
                                         ("100-199", 100, 200), ("200-400", 200, 401))},
        doors_per_room=share(((min(len(r["doors"]), 6), W(r)) for r in rooms)),
        share_with_door_to_outside=round(sum(W(r) for r in rooms if any(d["to"] is None for d in r["doors"])) / tw, 3),
        door_types=share(((d["type"], W(r)) for r in rooms for d in r["doors"]), 20),
        floor_materials=share(((r["floor"], W(r)) for r in rooms), 25),
        wall_materials=share(((m, W(r) * n) for r in rooms for m, n in r["walls"].items()), 20),
        floor_inside_outside=[dict(inside=a, outside=b, share=round(v / io_tot, 4)) for (a, b), v in io.most_common(25)],
        share_floor_changes_at_outside_door=round(sum(v for (a, b), v in io.items() if a != b) / io_tot, 3),
        furniture_per_room_q=wq(lambda r: r["counts"].get("furniture", 0)),
        furniture_per_100_tiles_q=wq(lambda r: round(100 * r["counts"].get("furniture", 0) / r["tiles"], 1)),
        lights_per_room_q=wq(lambda r: r["counts"].get("light", 0)),
        lights_per_100_tiles_q=wq(lambda r: round(100 * r["counts"].get("light", 0) / r["tiles"], 1)),
        share_with_light=round(sum(W(r) for r in rooms if r["counts"].get("light")) / tw, 3),
        items_per_room_q=wq(lambda r: r["counts"].get("item", 0)),
        creatures_per_room_q=wq(lambda r: r["counts"].get("creature", 0)),
        rooms_per_building=share(((min(len(v), 10), W(v[0])) for v in buildings.values())),
        multi_room_building_share=round(sum(W(v[0]) for v in buildings.values() if len(v) > 1)
                                        / (sum(W(v[0]) for v in buildings.values()) or 1), 3),
        top_furniture_and_lights=share(((t, W(r) * n) for r in rooms for t, n in r["object_types"].items()), 40),
    )


def main():
    weights = c.sp_weights()
    W = lambda r: weights[r["map"]]
    rooms = [r for m in c.sp_maps() for r in analyse_map(m)]
    built = [r for r in rooms if r["kind"] == "building"]
    natural = [r for r in rooms if r["kind"] == "natural"]
    summary = dict(definition=f"enclosed 4-connected component, 2..{MAX_ROOM_TILES} floor tiles, door gaps closed; "
                              "building = >=60% of solid wall cells are built materials",
                   maps=len(c.sp_maps()), building_rooms=stats(built, W), natural_rooms=stats(natural, W))
    index = []
    for r in rooms:
        e = {k: r[k] for k in ("id", "map", "building", "kind", "tiles", "bbox", "u_extent", "v_extent", "floor",
                               "floors", "walls", "counts")}
        e["doors"] = [{k: d[k] for k in ("id", "type", "dir", "gap", "to")} for d in r["doors"]]
        if r["kind"] == "building": e["objects"] = r["objects"]   # phase 3 copies these layouts
        index.append(e)
    import json, os
    os.makedirs(c.OUT, exist_ok=True)
    with open(os.path.join(c.OUT, "rooms.json"), "w", encoding="utf-8") as f:   # compact: the index is large
        json.dump(dict(schema_version=1, summary=summary, rooms=index), f, separators=(",", ":"))
    write_md(summary)
    print(f"rooms: {len(rooms)} ({len(built)} building, {len(natural)} natural) across {summary['maps']} maps")


def fmt(d, n=8):
    return ", ".join(f"{k} {v:.0%}" for k, v in list(d.items())[:n])


def write_md(s):
    b, n = s["building_rooms"], s["natural_rooms"]
    lines = [
        "# Rooms and buildings",
        "",
        "Source: `rules/rooms.py` over the 120 single-player maps (campaign + quest); statistics weighted by",
        "`1 / layout group size` so a layout shared by the three class campaigns counts once. Quartiles are",
        "[25%, median, 75%].",
        "",
        "Method: flood-fill every non-wall cell (diagonal wall chains block 4-connectivity); door gaps are",
        f"closed with a virtual wall. A room is an enclosed component with 2-{MAX_ROOM_TILES} floor tiles. It is a",
        "**building** room when at least 60% of its solid walls are built materials, else **natural** (cave",
        "pockets, tree-ringed clearings). Rooms sharing a wall cell or a door form one building. Door gap cells",
        "use the verified rule (South: corner-(1,1); North: corner; East: corner-(1,0); West: corner-(0,1)).",
        "",
        "## JSON schema (`rules/out/rooms.json`)",
        "",
        "```",
        "{schema_version: 1,",
        " summary: {definition, maps,",
        "   building_rooms|natural_rooms: {rooms, rooms_weighted, buildings, tiles_per_room_q, u_extent_cells_q,",
        "     v_extent_cells_q, aspect_q, size_bands{band: share}, doors_per_room{n: share},",
        "     share_with_door_to_outside, door_types{type: share}, floor_materials{..}, wall_materials{..},",
        "     floor_inside_outside[{inside, outside, share}], share_floor_changes_at_outside_door,",
        "     furniture_per_room_q, furniture_per_100_tiles_q, lights_per_room_q, lights_per_100_tiles_q,",
        "     share_with_light, items_per_room_q, creatures_per_room_q, rooms_per_building{n: share},",
        "     multi_room_building_share, top_furniture_and_lights{type: share}}},",
        " rooms: [{id 'map:comp', map, building 'map:bN', kind building|natural, tiles, bbox[x0,y0,x1,y1] cells,",
        "          u_extent, v_extent (cells along the wall axes), floor, floors{top 4}, walls{top 4},",
        "          counts{furniture, light, item, creature, door, other},",
        "          doors[{id, type, dir, gap[x,y], to: room id or null = outside}],",
        "          objects[object ids in corpus objects table] (building rooms only)}]}",
        "```",
        "",
        f"## Building rooms ({b['rooms']} rooms, {b['buildings']} buildings)",
        "",
        f"- **Size.** Floor tiles {b['tiles_per_room_q']}; extent along the wall axes u {b['u_extent_cells_q']},"
        f" v {b['v_extent_cells_q']} cells; aspect {b['aspect_q']}. Bands: {fmt(b['size_bands'])}.",
        f"- **Doors.** Doors per room: {fmt(b['doors_per_room'])}. {b['share_with_door_to_outside']:.0%} have a door"
        f" to the outside; rooms with no door object are entered through open archways, secret walls, other rooms"
        f" or teleports. Door types: {fmt(b['door_types'], 10)}.",
        f"- **Floors.** {fmt(b['floor_materials'], 12)}. At doors to the outside the floor changes"
        f" {b['share_floor_changes_at_outside_door']:.0%} of the time; common inside/outside pairs: "
        + "; ".join(f"{d['inside']}/{d['outside']}" for d in b["floor_inside_outside"][:10]) + ".",
        f"- **Walls.** {fmt(b['wall_materials'], 12)}.",
        f"- **Contents.** Furniture per room {b['furniture_per_room_q']} ({b['furniture_per_100_tiles_q']} per 100"
        f" tiles); lights per room {b['lights_per_room_q']} ({b['lights_per_100_tiles_q']} per 100 tiles),"
        f" {b['share_with_light']:.0%} of rooms lit; items {b['items_per_room_q']}; creatures {b['creatures_per_room_q']}.",
        f"- **Furniture and lights.** {fmt(b['top_furniture_and_lights'], 20)}.",
        f"- **Buildings.** Rooms per building: {fmt(b['rooms_per_building'])}; multi-room buildings"
        f" {b['multi_room_building_share']:.0%}.",
        "",
        f"## Natural enclosures ({n['rooms']} rooms)",
        "",
        f"- Floor tiles {n['tiles_per_room_q']}; floors {fmt(n['floor_materials'], 8)}; walls {fmt(n['wall_materials'], 6)}.",
        f"- Furniture (mostly rocks/plants) per room {n['furniture_per_room_q']}; lights {n['lights_per_room_q']},"
        f" {n['share_with_light']:.0%} lit.",
        "",
        "## Notes for generation",
        "",
        "- Use `rooms[]` (kind building) to choose reference rooms by size, floor and wall material in phase 3;",
        "  object ids join to the corpus `objects` table so a room's furniture layout can be copied relative to",
        "  its bounding box.",
        "- Small rooms (<10 tiles) are mostly closets, corridors, stair landings and are often empty; furniture",
        "  and lights scale with area.",
    ]
    c.save_section("rooms.md", "\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
