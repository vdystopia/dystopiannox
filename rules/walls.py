"""Phase 2 rule mining: WALLS, DOORS and BOUNDARIES.

Writes rules/out/walls.json (machine-readable rules) and rules/sections/walls.md (summary).
Engine-validity tables use all 157 stock maps with plain counts; style rules use the campaign
maps weighted by common.campaign_weights() (shared class-campaign maps count once).

    py rules\\walls.py
"""
import math, os, sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c

INVISIBLE = {"InvisibleWallSet", "InvisibleBlockingWallSet", "InvisibleStoneWallSet"}
DIAG = {"TL": (-1, -1), "TR": (1, -1), "BL": (-1, 1), "BR": (1, 1)}
NORMALS = {0: ("TL", "BR"), 1: ("TR", "BL")}           # sides of straight runs
LINE = {"\\": ((1, 1), (-1, -1)), "/": ((1, -1), (-1, 1))}
# door direction -> (gap cell offset from the door corner, wall line it sits in)
DOOR_RULE = {"South": ((-1, -1), "\\"), "North": ((0, 0), "\\"), "East": ((-1, 0), "/"), "West": ((0, -1), "/")}
CAT_RANK = {"interior": 5, "masonry": 4, "cave": 3, "lava": 2, "natural": 1, "water": 0, "void": -1}


def fcat(m):
    """Coarse floor category of a floor material name."""
    if m is None: return "void"
    if "Water" in m: return "water"
    if "Lava" in m: return "lava"
    if any(k in m for k in ("Cave", "Rock", "Volcanic", "ManaMine", "Crystal")): return "cave"
    if "Cobble" not in m and any(k in m for k in ("Grass", "Weeds", "Dirt", "Mud", "Sand", "Swamp", "Ice", "Bones")):
        return "natural"
    if any(k in m for k in ("Wood", "Oak", "Redwood", "Rug", "Tile", "Checker", "Busy", "Marble", "Transparent", "Black")):
        return "interior"
    return "masonry"


class TileIndex:
    """Floor tiles of one map, looked up by visual centre (tile (x,y) is centred on corner (x+1,y+1))."""
    def __init__(self, tiles):
        self.t = tiles

    def at(self, px, py, radius=0.85):
        """Material of the tile whose visual centre is nearest to cell point (px, py), within radius."""
        best, bd = None, radius * radius
        for x in range(int(math.floor(px)) - 2, int(math.floor(px)) + 1):
            for y in range(int(math.floor(py)) - 2, int(math.floor(py)) + 1):
                t = self.t.get((x, y))
                if t is not None:
                    d = (x + 1 - px) ** 2 + (y + 1 - py) ** 2
                    if d <= bd: best, bd = t["material"], d
        return best


def side_materials(ti, x, y, facing, k=0.8):
    """Floor material on each side of wall (x, y). Straight runs: 2 sides; other shapes: 4 diagonals."""
    names = NORMALS.get(facing, tuple(DIAG))
    cx, cy = x + 0.5, y + 0.5
    return {n: ti.at(cx + DIAG[n][0] * k, cy + DIAG[n][1] * k) for n in names}


def point_in_poly(px, py, pts):
    inside, j = False, len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]; xj, yj = pts[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def norm(counter, digits=3):
    tot = sum(counter.values()) or 1
    return {str(k): round(v / tot, digits) for k, v in sorted(counter.items(), key=lambda kv: -kv[1])}


def main():
    con = c.db()
    weights = c.campaign_weights()
    maps_all = c.all_maps()

    # ---- 1. valid combinations (engine validity, all maps) --------------------------------
    valid = defaultdict(lambda: defaultdict(Counter))
    combo_maps = defaultdict(set)
    for r in con.execute("SELECT map, material, facing, variation FROM walls"):
        valid[r["material"]][r["facing"]][r["variation"]] += 1
        combo_maps[(r["material"], r["facing"], r["variation"])].add(r["map"])
    mat_count_all = {m: sum(sum(v.values()) for v in fac.values()) for m, fac in valid.items()}
    mat_maps_all = defaultdict(set)
    for (m, f, v), ms in combo_maps.items(): mat_maps_all[m] |= ms

    # ---- per-map passes over campaign maps ------------------------------------------
    var_w = defaultdict(lambda: defaultdict(Counter))
    ctx = defaultdict(Counter); role = defaultdict(Counter); joins = defaultdict(Counter)
    mat_sp_w = Counter(); mat_sp_maps = defaultdict(set)
    special = {k: defaultdict(Counter) for k in ("window", "destructible", "secret")}
    special_ctx = {k: Counter() for k in ("window", "destructible", "secret")}
    secret_scan = Counter(); secret_state = Counter()
    boundary_closed = Counter(); boundary_per_map = {}
    invis_ctx = defaultdict(Counter); invis_role = defaultdict(Counter)
    door_rule = defaultdict(Counter); door_type_by_mat = defaultdict(Counter)
    door_inside = defaultdict(Counter); gap_widths = Counter(); doors_per_gap = Counter()
    door_lock = Counter(); door_type_ctx = defaultdict(Counter)
    mm_values = Counter(); mm_ctx = defaultdict(Counter); mm_poly = Counter()

    for mp in maps_all:
        is_sp = mp in weights
        if not is_sp: continue
        w = weights[mp]
        W = c.walls(mp); T = c.tiles(mp); ti = TileIndex(T)
        polys = [(p["minimap"], __import__("json").loads(p["points"])) for p in
                 con.execute("SELECT minimap, points FROM polygons WHERE map=?", (mp,))]

        for (x, y), wl in W.items():
            m, f = wl["material"], wl["facing"]
            var_w[m][f][wl["variation"]] += w
            mat_sp_w[m] += w; mat_sp_maps[m].add(mp)
            sides = side_materials(ti, x, y, f)
            cats = [fcat(s) for s in sides.values()]
            floor_cats = [k for k in cats if k != "void"]
            for k in floor_cats: ctx[m][k] += w / max(1, len(floor_cats))
            if not floor_cats: rl = "isolated"
            elif "void" in cats: rl = "boundary"
            else: rl = "partition"
            role[m][rl] += w
            for d in DIAG.values():
                o = W.get((x + d[0], y + d[1]))
                if o and o["material"] != m: joins[m][o["material"]] += w
            p = wl["props"]
            flags = {"window": p.get("Window"), "destructible": p.get("Destructable"),
                     "secret": ("Secret_ScanFlags" in p) or ("Secret_WallState" in p)}
            for k, on in flags.items():
                if on:
                    special[k][m][f] += w
                    special_ctx[k][rl] += w
            if "Secret_ScanFlags" in p: secret_scan[p["Secret_ScanFlags"]] += w
            if "Secret_WallState" in p: secret_state[p["Secret_WallState"]] += w
            if m in INVISIBLE:
                near = {fcat(ti.at(x + 0.5 + dx, y + 0.5 + dy, 1.2)) for dx in (-1.5, 0, 1.5) for dy in (-1.5, 0, 1.5)}
                tags = []
                if "water" in near: tags.append("water")
                if "lava" in near: tags.append("lava")
                if rl == "boundary": tags.append("void edge")
                if any(W.get((x + d[0], y + d[1]), {}).get("material") not in (None, *INVISIBLE) for d in DIAG.values()):
                    tags.append("next to visible wall")
                if not tags: tags.append("open ground (blocker)")
                for tg in tags: invis_ctx[m][tg] += w
                invis_role[m][rl] += w
            mm_values[wl["minimap"]] += w
            mm_ctx[rl if rl != "partition" else ("interior" if "interior" in floor_cats else "other partition")][wl["minimap"]] += w
            if polys:
                px, py = (x + 0.5) * c.CELL, (y + 0.5) * c.CELL
                inside = [mm for mm, pts in polys if point_in_poly(px, py, pts)]
                if inside: mm_poly["match" if wl["minimap"] in inside else "differs"] += w
                else: mm_poly["no polygon"] += w

        # ---- 4. outer boundary of the walkable floor ----
        closed = Counter()
        for (x, y), t in T.items():
            for dx, dy in DIAG.values():
                if (x + dx, y + dy) in T: continue
                mx, my = x + 1 + dx / 2, y + 1 + dy / 2       # midpoint of the floor edge, in cells
                found = set()
                for wx in range(int(mx) - 2, int(mx) + 2):
                    for wy in range(int(my) - 2, int(my) + 2):
                        wl = W.get((wx, wy))
                        if wl and (wx + 0.5 - mx) ** 2 + (wy + 0.5 - my) ** 2 <= 1.1 ** 2:
                            found.add("invisible" if wl["material"] in INVISIBLE else "visible")
                kind = "visible wall" if "visible" in found else "invisible wall only" if found else "no wall"
                closed[kind] += 1
        tot = sum(closed.values()) or 1
        boundary_per_map[mp] = {k: round(v / tot, 3) for k, v in closed.items()}
        for k, v in closed.items(): boundary_closed[k] += w * v / tot

        # ---- 5. doors ----
        for o in c.objects(mp):
            if o["xtype"] != "DoorXfer": continue
            d = o["xfer"].get("Direction")
            door_lock[o["xfer"].get("LockType")] += w
            if d not in DOOR_RULE: door_rule["other direction"][d] += w; continue
            cx, cy = round(o["x"] / c.CELL), round(o["y"] / c.CELL)
            (ox, oy), line = DOOR_RULE[d]
            gx, gy = cx + ox, cy + oy
            a, b = LINE[line]
            ends = [W.get((gx + a[0] * k, gy + a[1] * k)) for k in range(1, 6)] + [W.get((gx + b[0] * k, gy + b[1] * k)) for k in range(1, 6)]
            line_wall = next((e for e in ends if e), None)
            ok = (gx, gy) not in W and (W.get((gx + a[0], gy + a[1])) or W.get((gx + b[0], gy + b[1])))
            door_rule[d]["match" if ok else ("gap occupied" if (gx, gy) in W else "no wall beside gap")] += w
            if line_wall: door_type_by_mat[line_wall["material"]][o["type"]] += w
            if ok:
                # gap width along the wall line, and how many doors share it
                run = [(gx, gy)]
                for dirn in (a, b):
                    k = 1
                    while k < 8 and (gx + dirn[0] * k, gy + dirn[1] * k) not in W:
                        run.append((gx + dirn[0] * k, gy + dirn[1] * k)); k += 1
                gap_widths[len(run)] += w
                # which side is "more inside"? sides perpendicular to the wall line
                s1, s2 = (("TR", "BL") if line == "\\" else ("TL", "BR"))
                m1 = fcat(ti.at(gx + 0.5 + DIAG[s1][0] * 1.4, gy + 0.5 + DIAG[s1][1] * 1.4, 1.2))
                m2 = fcat(ti.at(gx + 0.5 + DIAG[s2][0] * 1.4, gy + 0.5 + DIAG[s2][1] * 1.4, 1.2))
                if CAT_RANK[m1] != CAT_RANK[m2]:
                    inside = s1 if CAT_RANK[m1] > CAT_RANK[m2] else s2
                    door_inside[f"{line} wall, inside {inside}"][d] += w
                else:
                    door_inside[f"{line} wall, sides alike"][d] += w
                door_type_ctx[o["type"]][f"{m1}|{m2}" if m1 <= m2 else f"{m2}|{m1}"] += w

    # count doors per gap (doors within 1 cell of each other on the same line counts as double)
    # (derived from gap width histogram: width>=2 indicates a double opening)

    # ---- assemble -------------------------------------------------------------------------
    materials = {}
    for m in sorted(set(mat_count_all) | set(mat_sp_w)):
        materials[m] = dict(
            count_all=mat_count_all.get(m, 0), maps_all=len(mat_maps_all.get(m, ())),
            sp_weight=round(mat_sp_w.get(m, 0), 1), sp_maps=len(mat_sp_maps.get(m, ())),
            invisible=m in INVISIBLE,
            context=norm(ctx[m]), role=norm(role[m]),
            joins={k: round(v, 1) for k, v in joins[m].most_common(8)},
            windows=round(sum(special["window"][m].values()), 1),
            destructible=round(sum(special["destructible"][m].values()), 1),
            secret=round(sum(special["secret"][m].values()), 1))

    data = dict(
        valid_variations={m: {str(f): {str(v): n for v, n in sorted(vs.items())} for f, vs in sorted(fac.items())}
                          for m, fac in sorted(valid.items())},
        variation_weights={m: {str(f): norm(vs) for f, vs in sorted(fac.items())} for m, fac in sorted(var_w.items())},
        materials=materials,
        special_walls={k: dict(by_material={m: {str(f): round(v, 1) for f, v in fs.items()} for m, fs in sorted(d.items())},
                               role=norm(special_ctx[k])) for k, d in special.items()},
        secret_settings=dict(scan_flags=norm(secret_scan), wall_state=norm(secret_state)),
        boundary=dict(closed_by=norm(boundary_closed), per_map=boundary_per_map),
        invisible_walls={m: dict(contexts={k: round(v, 1) for k, v in invis_ctx[m].most_common()}, role=norm(invis_role[m]))
                         for m in sorted(invis_ctx)},
        doors=dict(
            placement_rule={d: norm(v) for d, v in door_rule.items()},
            types_by_wall_material={m: {k: round(v, 1) for k, v in d.most_common(6)} for m, d in sorted(door_type_by_mat.items())},
            direction_by_inside_side={k: norm(v) for k, v in sorted(door_inside.items())},
            gap_width_cells=norm(gap_widths),
            lock_type=norm(door_lock),
            context_by_type={t: norm(v) for t, v in sorted(door_type_ctx.items())}),
        minimap=dict(values=norm(mm_values), by_role={k: dict(list(norm(v).items())[:6]) for k, v in mm_ctx.items()},
                     matches_enclosing_polygon=norm(mm_poly)),
    )
    c.save_json("walls.json", data)
    write_md(data)
    print("walls.json and walls.md written:", len(materials), "materials,",
          sum(len(f) for m in valid.values() for f in m.values()), "valid (material, facing, variation) combos")


def write_md(d):
    L = []
    A = L.append
    A("# Walls, doors and boundaries\n")
    A("Generated by `rules/walls.py` from `corpus/out/nox_corpus.db`. Validity tables use all 157 stock maps "
      "(plain counts); style statistics use the 107 campaign maps weighted so each distinct layout counts once "
      "(shares below are weighted shares).\n")
    A("## JSON schema (`rules/out/walls.json`)\n")
    A("""| Key | Meaning |
|---|---|
| `valid_variations[material][facing][variation]` | Number of stock walls with that exact combination (all maps). **A combination absent here has no graphics: never use it.** |
| `variation_weights[material][facing][variation]` | Share of campaign walls using that variation: sample from this for natural-looking walls. |
| `materials[material]` | `count_all`, `maps_all`, `sp_weight`, `sp_maps`, `invisible`, `context` (share of adjacent floor categories: natural, masonry, interior, cave, water, lava), `role` (boundary = void on one side, partition = floor both sides, isolated), `joins` (other wall materials it touches, weighted), `windows`/`destructible`/`secret` (weighted counts). |
| `special_walls[window/destructible/secret]` | `by_material[material][facing]` weighted counts, `role` shares. |
| `secret_settings` | Distribution of `Secret_ScanFlags` and `Secret_WallState` on real secret walls. |
| `boundary.closed_by` | How the edge of the walkable floor (floor next to void) is closed: `visible wall`, `invisible wall only`, `no wall`. `per_map` gives each map's shares. |
| `invisible_walls[material]` | `contexts` (water, lava, void edge, next to visible wall, open ground blocker; weighted counts, a wall can have several) and `role`. |
| `doors.placement_rule[direction]` | Share of doors matching the gap-corner rule (`match`), or not. |
| `doors.types_by_wall_material` | Door object types used in each wall material (weighted). |
| `doors.direction_by_inside_side` | For doors between two different floor categories: which direction Westwood used given which side is "more inside" (interior > masonry > cave > lava > natural > water). |
| `doors.gap_width_cells` | Width of the wall opening a door sits in, in wall cells. |
| `minimap` | Wall minimap group values, by role, and whether a wall's group equals the group of the room polygon containing it. |

Floor categories: `natural` (grass, dirt, mud, sand, swamp, ice), `masonry` (cobble, brick, stone, facades, dungeon/crypt/temple floors), `interior` (wood, rugs, tiles, marble), `cave` (cave, rock, volcanic, mana mine, crystal), `water`, `lava`.

Wall facings: 0 `/` run, 1 `\\` run, 2 cross, 3-6 T-junctions, 7-10 corners.
""")
    # 1
    A("## 1. Valid wall pieces (the black-wall fix)\n")
    A("A wall's available variations depend on its **facing**, not just its material. Straight runs (facings 0 and 1) "
      "usually have several variations; corners, T-junctions and crosses almost always only variation 0. "
      "`thing.bin`'s per-material variation count is **not** a safe bound (e.g. `Log` reports 7, but only 0-2 exist on runs).\n")
    A("| Material | Walls (all maps) | Variations on `/` runs | on `\\` runs | Corners/T/cross variations used |")
    A("|---|---|---|---|---|")
    for m, fac in sorted(d["valid_variations"].items(), key=lambda kv: -d["materials"][kv[0]]["count_all"]):
        others = sorted({int(v) for f, vs in fac.items() if f not in ("0", "1") for v in vs})
        A(f"| {m} | {d['materials'][m]['count_all']} | {','.join(fac.get('0', {}))} | {','.join(fac.get('1', {}))} | {','.join(map(str, others))} |")
    # 2
    A("\n## 2. Materials: where Westwood uses them\n")
    A("Context = floor categories next to the wall; role = outer boundary (void on one side) vs interior partition. "
      "Campaign maps, weighted.\n")
    A("| Material | Campaign layouts | Main context | Boundary / partition | Joins most with |")
    A("|---|---|---|---|---|")
    for m, info in sorted(d["materials"].items(), key=lambda kv: -kv[1]["sp_weight"]):
        if info["sp_weight"] < 1: continue
        ctx = ", ".join(f"{k} {int(v * 100)}%" for k, v in list(info["context"].items())[:3])
        rl = f"{int(info['role'].get('boundary', 0) * 100)}% / {int(info['role'].get('partition', 0) * 100)}%"
        jn = ", ".join(list(info["joins"])[:3])
        A(f"| {m} | {info['sp_maps']} | {ctx} | {rl} | {jn} |")
    # 3
    A("\n## 3. Windows, breakable and secret walls\n")
    for k, sw in d["special_walls"].items():
        tops = sorted(((m, sum(v.values())) for m, v in sw["by_material"].items()), key=lambda kv: -kv[1])[:8]
        A(f"- **{k}**: " + ", ".join(f"{m} ({v:.0f})" for m, v in tops) + f". Role: " +
          ", ".join(f"{r} {int(s * 100)}%" for r, s in sw["role"].items()))
    A(f"- Secret wall settings: scan flags {d['secret_settings']['scan_flags']}, wall state {d['secret_settings']['wall_state']} "
      "(real secret walls carry `Secret_ScanFlags`/`Secret_WallState`; `Secret_OpenWaitSeconds=3` is a default on every wall).\n")
    # 4
    A("## 4. Boundaries (the see-through-hole fix)\n")
    cb = d["boundary"]["closed_by"]
    A("Every edge where walkable floor meets void, across campaign maps (weighted): " +
      ", ".join(f"{k} {v * 100:.1f}%" for k, v in cb.items()) + ".\n")
    worst = sorted(d["boundary"]["per_map"].items(), key=lambda kv: -kv[1].get("invisible wall only", 0))[:5]
    A("Maps with the most invisible-only boundary edges: " + ", ".join(f"{m} ({v.get('invisible wall only', 0) * 100:.0f}%)" for m, v in worst) + ".\n")
    A("Where invisible walls are used (weighted counts; a wall can have several tags):\n")
    for m, info in d["invisible_walls"].items():
        A(f"- `{m}`: " + ", ".join(f"{k} {v:.0f}" for k, v in info["contexts"].items()) +
          "; role " + ", ".join(f"{r} {int(s * 100)}%" for r, s in info["role"].items()))
    A("")
    # 5
    A("## 5. Doors\n")
    A("Placement rule (door object on the corner of a one-cell gap; `\\` wall: South at gap+(1,1) or North at gap; "
      "`/` wall: East at gap+(1,0) or West at gap+(0,1)):\n")
    for dr, v in d["doors"]["placement_rule"].items():
        A(f"- {dr}: " + ", ".join(f"{k} {s * 100:.0f}%" for k, s in v.items()))
    A("\nWhich direction, given the inside of the building (the higher-ranked floor category):\n")
    for k, v in d["doors"]["direction_by_inside_side"].items():
        A(f"- {k}: " + ", ".join(f"{dr} {s * 100:.0f}%" for dr, s in v.items()))
    A("\nOpening width (wall cells): " + ", ".join(f"{k}: {v * 100:.0f}%" for k, v in d["doors"]["gap_width_cells"].items()) +
      ". Lock types: " + ", ".join(f"{k} {v * 100:.0f}%" for k, v in d["doors"]["lock_type"].items()) + ".\n")
    A("Door types by wall material (weighted counts):\n")
    for m, types in sorted(d["doors"]["types_by_wall_material"].items(), key=lambda kv: -sum(kv[1].values())):
        A(f"- {m}: " + ", ".join(f"{t} {v:.0f}" for t, v in types.items()))
    # 6
    A("\n## 6. Minimap groups\n")
    A("Values used (weighted share): " + ", ".join(f"{k}: {v * 100:.1f}%" for k, v in list(d["minimap"]["values"].items())[:10]) + ".\n")
    for k, v in d["minimap"]["by_role"].items():
        A(f"- {k}: " + ", ".join(f"{g}: {s * 100:.0f}%" for g, s in v.items()))
    A("- Wall group vs enclosing room polygon's group: " + ", ".join(f"{k} {v * 100:.0f}%" for k, v in d["minimap"]["matches_enclosing_polygon"].items()))
    A("\nThe minimap shows the wall groups of the polygon the player stands in; 100 is the default group, other values "
      "(90, 80, 70, 110...) separate areas (e.g. interiors, upper floors, secret areas) so they are hidden until entered.\n")
    c.save_section("walls.md", "\n".join(L))


if __name__ == "__main__":
    main()
