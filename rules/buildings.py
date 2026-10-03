"""Buildings in Westwood's single-player maps: footprint shapes, sizes, how they are divided into
rooms, doors, material styles and town spacing (phase 3 rule mining, feeds mapgen/kit/building.py).

Buildings come from rules/out/rooms.json (rooms sharing a wall or a door). Room cells are rebuilt
with rooms.components() so each building's footprint can be measured on the u/v wall lattice:
a cell (x, y) maps to lattice point (floor(u/2), floor(v/2)) with u = x + y, v = x - y, so a room
bounded by walls u0..u1, v0..v1 covers lattice columns u0/2 .. u1/2-1 and rows v0/2 .. v1/2-1
("units" = wall segments, the same scale as rooms.json u_extent/v_extent).

Shape classes (from the bounding box minus the footprint; small notches ignored):
rect, L (one corner cut), T (two corners cut on one side), U (one notch in a side), cross (four
corners cut), Z (two opposite corners cut), courtyard (hole inside), irregular (anything else).

Statistics weight single-player maps by 1 / layout group size. Writes rules/out/buildings.json and
rules/sections/buildings.md.  Run: py rules/buildings.py
"""
import collections, json, math, os, statistics as st
import common as c
import rooms as R

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
MAX_BUILDING_TILES = 900
MAX_ROOMS = 14
NOT_BUILDINGS = {"IronFence", "IronFenceDamaged", "OgreCage", "InvisibleBlockingWallSet", "InvisibleWallSet",
                 "InvisibleStoneWallSet"}
STYLE_NAMES = {
    "Log": "log_cabin", "StuccoLightWood": "stucco_house", "StuccoDarkWood": "stucco_dark_house",
    "GalavaTownWall": "galava_townhouse", "GalavaTowerWall": "galava_tower", "DunMirCathedral": "dunmir_hall",
    "Dilapidated": "ruined_shack", "OgreWall": "ogre_hut", "Cobblestone": "cobble_house", "StoneGray": "stone_house",
    "StoneBlue": "blue_stone_house", "IxTempleWall": "ix_temple", "DungeonStone": "dungeon_block",
    "LOTDBrick": "lotd_crypt", "LOTDOrnate": "lotd_ornate", "AncientRuin": "ancient_ruin", "BrickBlue": "blue_brick_house",
    "BrickRed": "red_brick_house", "SewerWall": "sewer", "BrickPlain": "brick_house", "BrickFancyBright": "fancy_brick_house",
}
NEEDED_FACINGS = {"0", "1", "3", "4", "5", "6", "7", "8", "9", "10"}   # runs, T-junctions, corners


def q(vals, w=None):
    """Weighted quartiles [25%, 50%, 75%]."""
    if not vals: return None
    if w is None: w = [1.0] * len(vals)
    pairs = sorted(zip(vals, w)); tot = sum(w); out = []
    for p in (0.25, 0.5, 0.75):
        acc = 0
        for v, wt in pairs:
            acc += wt
            if acc >= p * tot: out.append(round(v, 2)); break
    return out


def shares(counter, top=None, nd=3):
    tot = sum(counter.values()) or 1
    items = sorted(counter.items(), key=lambda kv: -kv[1])
    if top: items = items[:top]
    return {str(k): round(v / tot, nd) for k, v in items}


def lattice(cell):
    x, y = cell
    return ((x + y) // 2, (x - y) // 2)


def classify_shape(F):
    """Shape class of a lattice footprint (set of (i, j))."""
    i0, i1 = min(i for i, _ in F), max(i for i, _ in F)
    j0, j1 = min(j for _, j in F), max(j for _, j in F)
    W, H = i1 - i0 + 1, j1 - j0 + 1
    missing = {(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)} - F
    if not missing: return "rect", W, H
    comps, seen = [], set()
    for p in missing:
        if p in seen: continue
        stack, comp = [p], []
        seen.add(p)
        while stack:
            a = stack.pop(); comp.append(a)
            for di, dj in N4:
                n = (a[0] + di, a[1] + dj)
                if n in missing and n not in seen: seen.add(n); stack.append(n)
        comps.append(comp)
    big = [cp for cp in comps if len(cp) >= max(3, 0.04 * W * H)]
    if not big: return "rect", W, H
    corners, notches, holes, other = [], [], 0, 0
    for cp in big:
        sides = set()
        for i, j in cp:
            if i == i0: sides.add("i0")
            if i == i1: sides.add("i1")
            if j == j0: sides.add("j0")
            if j == j1: sides.add("j1")
        if not sides: holes += 1
        elif len(sides) == 1: notches.append(sides)
        elif len(sides) == 2 and not ({"i0", "i1"} <= sides or {"j0", "j1"} <= sides): corners.append(frozenset(sides))
        else: other += 1
    if other: return "irregular", W, H
    if holes and not corners and not notches: return "courtyard", W, H
    if holes: return "irregular", W, H
    if not notches:
        if len(corners) == 1: return "L", W, H
        if len(corners) == 2:
            a, b = corners
            return ("T" if a & b else "Z"), W, H
        if len(corners) == 4: return "cross", W, H
        if len(corners) == 3: return "T", W, H
    if len(notches) == 1 and not corners: return "U", W, H
    if len(notches) == 2 and not corners: return "H", W, H
    return "irregular", W, H


def analyse_map(map_name, rooms_of_map):
    comp, comps, walls, tiles, cell_tile, doors = R.components(map_name)
    by_building = collections.defaultdict(list)
    for r in rooms_of_map:
        if r["kind"] == "building": by_building[r["building"]].append(r)
    out = []
    cell_room = {}
    for r in rooms_of_map:
        cid = int(r["id"].split(":")[1])
        for cell in comps[cid]["cells"]: cell_room[cell] = r["id"]
    room_building = {r["id"]: r["building"] for r in rooms_of_map if r["kind"] == "building"}
    for bid, rs in by_building.items():
        ntiles = sum(r["tiles"] for r in rs)
        if ntiles > MAX_BUILDING_TILES or len(rs) > MAX_ROOMS: continue
        cells = set()
        for r in rs: cells |= set(comps[int(r["id"].split(":")[1])]["cells"])
        F = {lattice(p) for p in cells}
        shape, W, H = classify_shape(F)
        # walls around the building: interior (between two of its rooms) or exterior
        ext_walls, int_walls, outside_floor, outside_kind = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
        perim = 0
        for (x, y), w in walls.items():
            nb_rooms = set()
            nb_out = []
            for dx, dy in N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                n = (x + dx, y + dy)
                rid = cell_room.get(n)
                if rid is not None and room_building.get(rid) == bid: nb_rooms.add(rid)
                elif n not in walls: nb_out.append(n)
            if not nb_rooms: continue
            if len(nb_rooms) >= 2: int_walls[w["material"]] += 1
            else:
                ext_walls[w["material"]] += 1
                perim += 1
                for n in nb_out:
                    rid = cell_room.get(n)
                    if rid is not None and rid in room_building: outside_kind["building"] += 1
                    elif n in cell_tile:
                        outside_kind["open"] += 1
                        outside_floor[tiles[cell_tile[n]]["material"]] += 1
                    else: outside_kind["void"] += 1
        if not ext_walls: continue
        main_mat = ext_walls.most_common(1)[0][0]
        if main_mat in NOT_BUILDINGS: continue
        tot_out = sum(outside_kind.values()) or 1
        freestanding = outside_kind["open"] / tot_out >= 0.5
        room_dims = [(r["u_extent"], r["v_extent"]) for r in rs]
        int_doors = [d for r in rs for d in r["doors"] if d["to"] is not None]
        ext_doors = [d for r in rs for d in r["doors"] if d["to"] is None]
        # which footprint side each entrance is on
        i0, i1 = min(i for i, _ in F), max(i for i, _ in F)
        j0, j1 = min(j for _, j in F), max(j for _, j in F)
        sides = []
        for d in ext_doors:
            gi, gj = lattice(tuple(d["gap"]))
            dist = {"u_min": abs(gi - i0), "u_max": abs(gi - i1 - 1), "v_min": abs(gj - j0), "v_max": abs(gj - j1 - 1)}
            sides.append(min(dist, key=dist.get))
        largest = max(r["tiles"] for r in rs)
        corridors = sum(1 for r in rs if min(r["u_extent"], r["v_extent"]) <= 3 and max(r["u_extent"], r["v_extent"]) >= 6)
        out.append(dict(map=map_name, building=bid, tiles=ntiles, rooms=len(rs), shape=shape, W=W, H=H,
                        area_units=len(F), fill=round(len(F) / (W * H), 2), room_dims=room_dims,
                        room_tiles=[r["tiles"] for r in rs], hall_share=round(largest / ntiles, 2),
                        corridors=corridors, interior_doors=len(int_doors) // 2 if int_doors else 0,
                        interior_door_rooms=len(int_doors), entrances=len(ext_doors), entrance_sides=sides,
                        ext_material=main_mat, ext_materials=dict(ext_walls), int_materials=dict(int_walls),
                        room_floors=[r["floor"] for r in rs], ext_door_types=[d["type"] for d in ext_doors],
                        int_door_types=[d["type"] for d in int_doors], outside_floors=dict(outside_floor.most_common(4)),
                        freestanding=freestanding, cells=cells))
    # spacing between freestanding buildings in the same map (gap in cells between footprints)
    free = [b for b in out if b["freestanding"]]
    for b in free:
        best = None
        bc = [(x + y, x - y) for x, y in b["cells"]]
        for o in free:
            if o is b: continue
            oc = [(x + y, x - y) for x, y in o["cells"]]
            # gap in wall units along u/v (Chebyshev between bounding boxes, cheap and adequate)
            bu0, bu1 = min(u for u, _ in bc), max(u for u, _ in bc)
            bv0, bv1 = min(v for _, v in bc), max(v for _, v in bc)
            ou0, ou1 = min(u for u, _ in oc), max(u for u, _ in oc)
            ov0, ov1 = min(v for _, v in oc), max(v for _, v in oc)
            gu = max(0, max(ou0 - bu1, bu0 - ou1)) / 2
            gv = max(0, max(ov0 - bv1, bv0 - ov1)) / 2
            g = max(gu, gv)
            if best is None or g < best: best = g
        b["nearest_gap_units"] = best
    for b in out: del b["cells"]
    return out


def main():
    data = json.load(open(os.path.join(c.OUT, "rooms.json"), encoding="utf-8"))
    W8 = c.sp_weights()
    by_map = collections.defaultdict(list)
    for r in data["rooms"]: by_map[r["map"]].append(r)
    buildings = []
    for m in sorted(W8):
        for b in analyse_map(m, by_map.get(m, [])):
            b["w"] = W8[m]; buildings.append(b)
    wall_rules = json.load(open(os.path.join(c.OUT, "walls.json"), encoding="utf-8"))["valid_variations"]

    def summarize(bs):
        w = [b["w"] for b in bs]
        shape = collections.Counter()
        rooms_n, floors, ext_dt, int_dt, int_m, out_f, sides, ent = (collections.Counter() for _ in range(8))
        for b in bs:
            shape[b["shape"]] += b["w"]; rooms_n[min(b["rooms"], 10)] += b["w"]; ent[b["entrances"]] += b["w"]
            for f in b["room_floors"]: floors[f] += b["w"] / len(b["room_floors"])
            for t in b["ext_door_types"]: ext_dt[t] += b["w"]
            for t in b["int_door_types"]: int_dt[t] += b["w"]
            for m, n in b["int_materials"].items(): int_m[m] += b["w"] * n
            for m, n in b["outside_floors"].items(): out_f[m] += b["w"] * n
            for s in b["entrance_sides"]: sides[s] += b["w"]
        multi = [b for b in bs if b["rooms"] > 1]
        room_dims = [d for b in bs for d in b["room_dims"]]
        rd_w = [b["w"] for b in bs for _ in b["room_dims"]]
        return dict(
            buildings=len(bs), weighted=round(sum(w), 2), shapes=shares(shape),
            size_units=dict(W=q([max(b["W"], b["H"]) for b in bs], w), H=q([min(b["W"], b["H"]) for b in bs], w)),
            tiles=q([b["tiles"] for b in bs], w), rooms=shares(rooms_n),
            area_units_per_room=q([b["area_units"] / b["rooms"] for b in multi], [b["w"] for b in multi]) if multi else None,
            room_long_short_units=dict(long=q([max(a, bb) for a, bb in room_dims], rd_w), short=q([min(a, bb) for a, bb in room_dims], rd_w)),
            hall_share=q([b["hall_share"] for b in multi], [b["w"] for b in multi]) if multi else None,
            corridor_share=round(sum(b["w"] for b in multi if b["corridors"]) / (sum(b["w"] for b in multi) or 1), 3),
            interior_doors_per_extra_room=q([b["interior_doors"] / (b["rooms"] - 1) for b in multi], [b["w"] for b in multi]) if multi else None,
            entrances=shares(ent), entrance_sides=shares(sides),
            room_floors=shares(floors, 8), exterior_door_types=shares(ext_dt, 6), interior_door_types=shares(int_dt, 6),
            interior_wall_materials=shares(int_m, 5), outside_floors=shares(out_f, 6),
            nearest_gap_units=q([b["nearest_gap_units"] for b in bs if b.get("nearest_gap_units") is not None],
                                [b["w"] for b in bs if b.get("nearest_gap_units") is not None]))

    town = [b for b in buildings if b["freestanding"]]
    by_mat = collections.defaultdict(list)
    for b in buildings: by_mat[b["ext_material"]].append(b)
    styles = {}
    for mat, bs in sorted(by_mat.items(), key=lambda kv: -sum(b["w"] for b in kv[1])):
        if sum(b["w"] for b in bs) < 2 or mat not in STYLE_NAMES: continue
        free_bs = [b for b in bs if b["freestanding"]]
        # house-like styles: describe them from their freestanding examples when there are enough
        source = "freestanding" if sum(b["w"] for b in free_bs) >= 2 else "all"
        s = summarize(free_bs if source == "freestanding" else bs)
        s["source"] = source
        facings = set(wall_rules.get(mat, {}))
        s.update(exterior_wall=mat, freestanding_share=round(sum(b["w"] for b in bs if b["freestanding"]) / sum(b["w"] for b in bs), 2),
                 wall_pieces_complete=NEEDED_FACINGS <= facings, missing_wall_facings=sorted(NEEDED_FACINGS - facings, key=int))
        styles[STYLE_NAMES[mat]] = s
    result = dict(schema_version=1, all=summarize(buildings), freestanding=summarize(town), styles=styles,
                  shape_definitions={"rect": "no part of the bounding box missing", "L": "one corner cut",
                                     "T": "two corners cut on one side", "U": "one notch in a side", "H": "notches in two sides",
                                     "cross": "four corners cut", "Z": "two opposite corners cut", "courtyard": "hole inside",
                                     "irregular": "anything else"},
                  units="lattice units along the wall axes: one wall segment = 2 in u or v")
    c.save_json("buildings.json", result)
    write_md(result)
    print(f"buildings: {len(buildings)} ({len(town)} freestanding), styles: {', '.join(styles)}")


def fmt(d, n=6):
    if not d: return "-"
    return ", ".join(f"{k} {round(v * 100)}%" for k, v in list(d.items())[:n])


def write_md(r):
    a, f = r["all"], r["freestanding"]
    L = ["# Buildings", "",
         "Source: `rules/buildings.py`, buildings from `rules/out/rooms.json` (rooms sharing a wall or door) in the 120 "
         "single-player maps, at most 900 floor tiles and 14 rooms (larger complexes are dungeons). Weighted by 1 / layout "
         "group size. Sizes are in lattice units along the wall axes (one wall segment = 2 in u or v, about one cell "
         "along the wall). Quartiles are [25%, median, 75%]. A building is *freestanding* when at least half of what lies "
         "outside its outer walls is open floor (towns, villages), as opposed to rooms inside larger structures.", "",
         "## JSON schema (`rules/out/buildings.json`)", "",
         "```",
         "{schema_version, units, shape_definitions{shape: text},",
         " all|freestanding|styles{name}: {buildings, weighted, shapes{shape: share}, size_units{W (long side), H (short)}: quartiles,",
         "   tiles, rooms{n: share}, area_units_per_room, room_long_short_units{long, short}, hall_share (largest room / building),",
         "   corridor_share, interior_doors_per_extra_room, entrances{n: share}, entrance_sides{u_min|u_max|v_min|v_max: share},",
         "   room_floors, exterior_door_types, interior_door_types, interior_wall_materials, outside_floors{material: share},",
         "   nearest_gap_units (to the next freestanding building),",
         "   styles only: exterior_wall, freestanding_share, source (freestanding|all: which buildings the style was measured on),",
         "   wall_pieces_complete, missing_wall_facings}}",
         "```", "",
         "## All buildings", "",
         f"- {a['buildings']} buildings ({a['weighted']} weighted). Shapes: {fmt(a['shapes'], 8)}.",
         f"- Long side {a['size_units']['W']} units, short side {a['size_units']['H']}; floor tiles {a['tiles']}.",
         f"- Rooms: {fmt(a['rooms'], 8)}; lattice units per room in multi-room buildings {a['area_units_per_room']}.",
         f"- Rooms measure long {a['room_long_short_units']['long']} x short {a['room_long_short_units']['short']} units; "
         f"the largest room holds {a['hall_share']} of a multi-room building; {round(a['corridor_share'] * 100)}% of multi-room buildings have a corridor.",
         f"- Interior doors per additional room {a['interior_doors_per_extra_room']} (below 1 means some rooms join through archways or each other).",
         f"- Entrances: {fmt(a['entrances'])}; sides: {fmt(a['entrance_sides'])}.",
         "", "## Freestanding buildings (towns and villages)", "",
         f"- {f['buildings']} buildings ({f['weighted']} weighted). Shapes: {fmt(f['shapes'], 8)}.",
         f"- Long side {f['size_units']['W']} units, short side {f['size_units']['H']}; floor tiles {f['tiles']}; rooms {fmt(f['rooms'], 6)}.",
         f"- Entrances {fmt(f['entrances'])}; sides {fmt(f['entrance_sides'])}.",
         f"- Gap to the nearest neighbouring building {f['nearest_gap_units']} units (0 = sharing walls / touching).",
         f"- Outside them: {fmt(f['outside_floors'])}.",
         "", "## Styles (by exterior wall material)", "",
         "| style | wall | buildings (w) | freestanding | shapes | long x short (median) | rooms | room floors | doors (ext) | partition walls | pieces complete |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, s in r["styles"].items():
        L.append(f"| {name} | {s['exterior_wall']} | {s['buildings']} ({s['weighted']}) | {round(s['freestanding_share'] * 100)}% | "
                 f"{fmt(s['shapes'], 3)} | {s['size_units']['W'][1]} x {s['size_units']['H'][1]} | {fmt(s['rooms'], 3)} | "
                 f"{fmt(s['room_floors'], 3)} | {fmt(s['exterior_door_types'], 2)} | {fmt(s['interior_wall_materials'], 2)} | "
                 f"{'yes' if s['wall_pieces_complete'] else 'missing ' + ','.join(s['missing_wall_facings'])} |")
    L += ["", "## Notes for generation", "",
          "- Footprints are unions of rectangles on the u/v wall lattice; rectangles dominate, then L and T/U shapes.",
          "- A style is only safe for multi-room interiors when its wall material has valid pieces for T-junctions and corners "
          "(`wall_pieces_complete`); otherwise use a different partition material (the style's `interior_wall_materials`) "
          "or keep the building single-roomed.",
          "- Freestanding buildings mostly have one entrance; place it on the side facing the street or square.", ""]
    c.save_section("buildings.md", "\n".join(L))


if __name__ == "__main__":
    main()
