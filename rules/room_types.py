"""Room types learned from Westwood's building rooms (phase 3 rule mining).

Classifies every single-player building room (rules/out/rooms.json) by its contents into a room
type, and learns, per type, everything the furnisher needs to create *new* rooms of that type:
size, floors, which furniture families appear and how many, where each family goes (against a wall
and at what offset, in a corner, free-standing), furniture sets (chairs around tables, a nightstand
beside a bed, a chair at a desk) with their geometry, which object types represent each family,
clutter group sizes, lights and townsfolk. Nothing here stores a stock room's layout: only
distributions.

Geometry is measured in rotated coordinates u = x + y, v = x - y (grid cells). One uv unit is
K = 23/sqrt(2) = 16.26 px, and uv distance is proportional to pixel distance. A wall cell (x, y)
sits on the line u = x + y + 1 ('/' walls, running along v) or v = x - y ('\\' walls, running along
u). Object (px, py) is at u = (px + py) / 23, v = (px - py) / 23. Wall sides follow decoration.json:
'/|BR' = the object is on the +u side of a '/' wall, '/|TL' on the -u side, '\\|TR' on the +v side
of a '\\' wall, '\\|BL' on the -v side.

Writes rules/out/room_types.json and rules/sections/room_types.md. Run: py rules/room_types.py
"""
import collections, json, math, re, statistics as st
import common as c
import rooms as R

K = 23 / math.sqrt(2)
WALL_NEAR = 2.6            # uv units (~42 px): within this of a wall line = against the wall
SET_RADIUS = 60 / K        # companions within 60 px

FAMILIES = [  # (family, regex on object type); first match wins
    ("rug", r"Rug\d?$|Rug\d"),
    ("bed", r"^(Bed\d|WoodBed\d|Cot\d|OgreBed\d|UrchinBed\d)$"),
    ("straw", r"^(OgreStraw\d|Straw\d)$"),
    ("nightstand", r"^Nightstand"),
    ("counter_bar", r"^(BarPiece|BarCorner|BarHingedTop)"),
    ("counter_shop", r"^TraderDesk"),
    ("shop_rack", r"^Trader"),
    ("table", r"Table"),
    ("chair", r"Chair|Stool"),
    ("bench", r"Bench"),
    ("desk", r"^Desk\d"),
    ("shelves", r"Bookcase|Shelves"),
    ("fireplace", r"Fireplace"),
    ("stove", r"^Stove|Cauldron|Oven"),
    ("smithy", r"^(Anvil|Bellows|Forge|Grindstone)"),
    ("lab", r"Vandegraf|Orrery|FairyJar|SentryGlobe|Telescope|WizardWorkstation|AlchemistDesk"),
    ("altar", r"Altar|LichGodStatue|Shrine"),
    ("throne", r"Throne"),
    ("tomb", r"Coffin|^Crypt\d|Tombstone|Sarcophag"),
    ("statue", r"Statue|Gargoyle"),
    ("column", r"Column|Pillar"),
    ("wall_decor", r"Tapestry|Painting|Trophy|HangingShield|Banner|Mirror|ClothSign|WallHanging|CrossedWeapons|HangingSwords|HangingCrossbow"),
    ("storage", r"Chest|Crate|Barrel|^Sack|PiledBarrels"),
    ("plant", r"^Plant|^Bush|^Flowers|Fern"),
    ("clutter", r"Spitoon|Meat|Bottle|Mug|Food|Bucket|Broom|Tools|Apple|Bread|Cheese|Cider"),
]
FAMILY_RE = [(f, re.compile(p)) for f, p in FAMILIES]
DUNGEON = re.compile(r"Spike|Bone|Skull|MonsterGenerator|Pit|Trap|Corpse|SpiderWeb|Rubble|Glyph|PressurePlate", re.I)
BLOCKING_FAMILIES = {"bed", "nightstand", "counter_bar", "counter_shop", "shop_rack", "table", "chair", "bench", "desk",
                     "shelves", "fireplace", "stove", "smithy", "lab", "altar", "throne", "tomb", "statue", "column",
                     "storage", "straw", "plant"}
SHOPKEEPER = re.compile(r"^Shopkeeper")


def family(t):
    for f, rx in FAMILY_RE:
        if rx.search(t): return f
    return None


def role_of(o):
    """furniture family, 'light', 'colorlight', 'npc', 'shopkeeper', 'dungeon' or None (ignored)."""
    t, cls = o["type"], o.get("class") or ""
    if t in ("ColorLight", "ColorLightMovable"): return "colorlight"
    if SHOPKEEPER.match(t): return "shopkeeper"
    if o.get("xtype") == "NPCXfer" or t in ("NPC", "Maiden"): return "npc"
    if "MONSTER" in cls: return None
    if R.LIGHT_NAME.search(t): return "light"
    if DUNGEON.search(t): return "dungeon"
    return family(t)


def base_name(t):
    """Directional family key as in decoration.json (strip trailing digits / compass suffix)."""
    return re.sub(r"(\d+[a-z]?|NE|NW|SE|SW|North|South|East|West|N|S|E|W)$", "", t)


def classify(fam, npcs):
    f = fam
    n = lambda k: f.get(k, 0)
    if n("counter_shop") or n("shop_rack") >= 2 or npcs.get("shopkeeper"): return "shop"
    if n("counter_bar"): return "tavern"
    if n("smithy"): return "smithy"
    if n("lab"): return "laboratory"
    if n("throne"): return "throne_room"
    if n("altar"): return "chapel"
    if n("tomb") >= 2: return "crypt"
    if n("stove"): return "kitchen"
    if n("bed") + n("straw") >= 3: return "barracks"
    if n("bed"): return "bedroom"
    if n("shelves") >= 2 and not n("bed"): return "library"
    if n("table") >= 2 and n("chair") + n("bench") >= 4: return "dining_hall"
    if n("desk") and n("shelves"): return "study"
    if n("table") or n("desk"): return "living_room"
    if n("storage") >= 3: return "storeroom"
    if n("statue") + n("column") >= 2: return "hall"
    furnished = sum(v for k, v in f.items() if k in BLOCKING_FAMILIES)
    return "other" if furnished else "empty"


def q(vals, ps=(10, 25, 50, 75, 90)):
    if not vals: return None
    s = sorted(vals)
    return {f"p{p}": round(s[min(len(s) - 1, int(p / 100 * len(s)))], 2) for p in ps}


def room_geometry(cells, walls):
    """Wall cells around the room with orientation ('/', '\\', 'corner') and line coordinate."""
    cellset = set(cells)
    wall_cells = {(p[0] + dx, p[1] + dy) for p in cells for dx, dy in R.N4 if (p[0] + dx, p[1] + dy) in walls}
    out = []
    for (x, y) in wall_cells:
        f = walls[(x, y)]["facing"]
        kind = "/" if f in (0,) else "\\" if f in (1,) else "corner"
        out.append((x, y, kind))
    return out


def measure(o, wl, room_u, room_v):
    """Position of object o relative to the room's walls: role, side, perpendicular distance."""
    u, v = (o["x"] + o["y"]) / 23, (o["x"] - o["y"]) / 23
    best = []
    for (x, y, kind) in wl:
        wu, wv = x + y + 1, x - y
        if kind == "/": d, along = abs(u - wu), abs(v - wv)
        elif kind == "\\": d, along = abs(v - wv), abs(u - wu)
        else: d, along = math.hypot(u - wu, v - wv), 0
        if along <= 1.5: best.append((d, kind, wu, wv))
    best.sort()
    straight = [b for b in best if b[1] != "corner" and b[0] <= WALL_NEAR]
    lines = {(b[1], round(b[2] if b[1] == "/" else b[3])) for b in straight}
    if not straight:
        return dict(role="center", u=u, v=v)
    d, kind, wu, wv = straight[0]
    side = ("BR" if u > wu else "TL") if kind == "/" else ("TR" if v > wv else "BL")
    role = "corner" if len({l[0] for l in lines}) >= 2 else "wall"
    return dict(role=role, side=f"{kind}|{side}", perp_px=round(d * K, 1), u=u, v=v)


def main():
    rooms = [r for r in json.load(open(c.os.path.join(c.OUT, "rooms.json"), encoding="utf-8"))["rooms"]
             if r["kind"] == "building" and r["map"] in c.sp_weights()]
    W = c.sp_weights()
    by_map = collections.defaultdict(list)
    for r in rooms: by_map[r["map"]].append(r)

    records = []                       # one per room
    placements = collections.defaultdict(list)    # (type, family) -> [placement dicts]
    sets = collections.defaultdict(list)          # (anchor family, companion family) -> offsets
    facing = collections.defaultdict(collections.Counter)   # chair family base -> (direction to anchor, variant)
    for m, rs in sorted(by_map.items()):
        comp, comps, walls, tiles, cell_tile, doors = R.components(m)
        objs = {o["id"]: o for o in c.objects(m)}
        for r in rs:
            cid = int(r["id"].split(":")[1])
            cells = comps[cid]["cells"]
            wl = room_geometry(cells, walls)
            us = [x + y for x, y in cells]; vs = [x - y for x, y in cells]
            items = [objs[i] for i in r["objects"] if i in objs]
            fam_count = collections.Counter(); npcs = collections.Counter(); dungeon = 0
            placed = []
            for o in items:
                ro = role_of(o)
                if ro is None: continue
                if ro == "dungeon": dungeon += 1; continue
                if ro in ("npc", "shopkeeper"): npcs[ro] += 1
                meas = measure(o, wl, (min(us), max(us)), (min(vs), max(vs)))
                placed.append(dict(o=o, fam=ro, **meas))
                if ro not in ("npc", "shopkeeper", "light", "colorlight"): fam_count[ro] += 1
            domestic = sum(v for k, v in fam_count.items() if k in BLOCKING_FAMILIES)
            rtype = "dungeon" if dungeon > max(3, domestic) else classify(fam_count, npcs)
            rec = dict(id=r["id"], map=m, w=W[m], type=rtype, tiles=r["tiles"], u_ext=r["u_extent"], v_ext=r["v_extent"],
                       floor=r["floor"], walls=r["walls"], fam=dict(fam_count),
                       lights=collections.Counter(p["o"]["type"] for p in placed if p["fam"] == "light"),
                       colorlights=sum(1 for p in placed if p["fam"] == "colorlight"), npcs=dict(npcs),
                       doors=len(r["doors"]))
            records.append(rec)
            for p in placed:
                placements[(rtype, p["fam"])].append(dict(type=p["o"]["type"], role=p["role"], side=p.get("side"),
                                                          perp=p.get("perp_px"), w=W[m]))
            # sets: companions near anchors
            for a in placed:
                if a["fam"] not in ("table", "desk", "bed", "counter_bar", "counter_shop", "fireplace", "stove", "smithy", "altar"): continue
                for b in placed:
                    if b is a: continue
                    du, dv = b["u"] - a["u"], b["v"] - a["v"]
                    if math.hypot(du, dv) > SET_RADIUS: continue
                    sets[(a["fam"], b["fam"])].append(dict(du=du, dv=dv, w=W[m], anchor=a["o"]["id"], rtype=rtype,
                                                           atype=a["o"]["type"], btype=b["o"]["type"]))
                    if b["fam"] in ("chair", "bench"):
                        # which variant faces the anchor: direction from chair to anchor in uv quadrants
                        ang = math.degrees(math.atan2(-dv, -du)) % 360
                        quad = ["+u", "+v", "-u", "-v"][int(((ang + 45) % 360) // 90)]
                        facing[base_name(b["o"]["type"])][(quad, b["o"]["type"])] += W[m]

    out = dict(schema_version=1, k_px_per_uv=round(K, 3), types={}, sets={}, chair_facing={})
    # ---- per type
    for rtype in sorted({r["type"] for r in records}):
        rs = [r for r in records if r["type"] == rtype]
        wsum = sum(r["w"] for r in rs)
        fams = sorted({f for r in rs for f in r["fam"]})
        inventory = {}
        for f in fams:
            present = [r for r in rs if r["fam"].get(f)]
            pw = sum(r["w"] for r in present)
            counts = [r["fam"][f] for r in present]
            per100 = [100 * r["fam"][f] / max(1, r["tiles"]) for r in present]
            pl = placements[(rtype, f)]
            plw = sum(p["w"] for p in pl) or 1
            roles = collections.Counter(); sides = collections.Counter(); types = collections.Counter(); perp = []
            for p in pl:
                roles[p["role"]] += p["w"]; types[p["type"]] += p["w"]
                if p["side"]: sides[p["side"]] += p["w"]
                if p["perp"] is not None: perp.append(p["perp"])
            inventory[f] = dict(p_present=round(pw / wsum, 3), count=q(counts), per100_tiles=q(per100),
                                roles={k: round(v / plw, 3) for k, v in roles.most_common()},
                                wall_sides={k: round(v / max(1, sum(sides.values())), 3) for k, v in sides.most_common()},
                                perp_px=q(perp), object_types={k: round(v / plw, 3) for k, v in types.most_common(12)},
                                evidence=dict(rooms=len(present), weighted=round(pw, 1)))
        lights = collections.Counter(); light_rooms = 0
        for r in rs:
            for k, v in r["lights"].items(): lights[k] += v * r["w"]
        out["types"][rtype] = dict(
            rooms=len(rs), weighted=round(wsum, 1), maps=len({r["map"] for r in rs}),
            tiles=q([r["tiles"] for r in rs]), u_extent=q([r["u_ext"] for r in rs]), v_extent=q([r["v_ext"] for r in rs]),
            floors=dict(collections.Counter({k: round(sum(r["w"] for r in rs if r["floor"] == k) / wsum, 3) for k in {r["floor"] for r in rs}}).most_common(8)),
            wall_materials=dict(collections.Counter({k: round(sum(r["w"] for r in rs if k in r["walls"]) / wsum, 3) for k in {m for r in rs for m in r["walls"]}}).most_common(8)),
            doors=q([r["doors"] for r in rs]),
            inventory=inventory,
            visible_lights=dict(count=q([sum(r["lights"].values()) for r in rs]),
                                per100_tiles=q([100 * sum(r["lights"].values()) / max(1, r["tiles"]) for r in rs]),
                                types={k: round(v / max(1, sum(lights.values())), 3) for k, v in lights.most_common(12)},
                                roles={k: round(v / max(1, sum(p["w"] for p in placements[(rtype, 'light')])), 3)
                                       for k, v in collections.Counter({rl: sum(p["w"] for p in placements[(rtype, 'light')] if p["role"] == rl) for rl in ("wall", "corner", "center")}).items()}),
            colorlights=dict(count=q([r["colorlights"] for r in rs]), p_any=round(sum(r["w"] for r in rs if r["colorlights"]) / wsum, 3)),
            npcs=dict(p_npc=round(sum(r["w"] for r in rs if r["npcs"].get("npc")) / wsum, 3),
                      p_shopkeeper=round(sum(r["w"] for r in rs if r["npcs"].get("shopkeeper")) / wsum, 3)))
    # ---- sets
    for (a, b), offs in sorted(sets.items()):
        if sum(o["w"] for o in offs) < 3: continue
        anchors = collections.defaultdict(float); per_anchor = collections.Counter()
        for o in offs: per_anchor[o["anchor"]] += 1; anchors[o["anchor"]] = o["w"]
        dist = [math.hypot(o["du"], o["dv"]) * K for o in offs]
        out["sets"][f"{a}+{b}"] = dict(pairs=len(offs), weighted=round(sum(o["w"] for o in offs), 1),
                                       per_anchor=q(list(per_anchor.values())), distance_px=q(dist),
                                       axis_share=round(sum(1 for o in offs if min(abs(o["du"]), abs(o["dv"])) < 0.6) / len(offs), 3))
    # ---- chair facing: which variant to use given the direction towards the table/desk
    for base, cnt in facing.items():
        by_dir = collections.defaultdict(collections.Counter)
        for (quad, t), w in cnt.items(): by_dir[quad][t] += w
        out["chair_facing"][base] = {qd: dict(variant=ct.most_common(1)[0][0], share=round(ct.most_common(1)[0][1] / sum(ct.values()), 2),
                                              weighted=round(sum(ct.values()), 1)) for qd, ct in by_dir.items()}
    # ---- per object type: which wall sides it stands against (orientation of non-paired variants)
    tsides = collections.defaultdict(collections.Counter)
    for pl in placements.values():
        for p in pl:
            if p["side"] and p["role"] in ("wall", "corner"): tsides[p["type"]][p["side"]] += p["w"]
    out["type_wall_sides"] = {t: dict(n=round(sum(c_.values()), 1), **{k: round(v / sum(c_.values()), 3) for k, v in c_.most_common()})
                              for t, c_ in sorted(tsides.items()) if sum(c_.values()) >= 2}
    out["assemblies"] = dict(bar_counter=bar_assembly())
    c.save_json("room_types.json", out)
    write_md(out)
    print("room types:", {k: v["rooms"] for k, v in out["types"].items()})


def bar_assembly():
    """How Westwood builds bar counters from BarPiece/BarCorner objects: pieces on a 2-unit uv grid
    (~33 px), each piece series runs along one axis on one side of the enclosed bar, and each corner
    piece joins two specific arms. Measured from every bar piece in the single-player maps."""
    pieces = collections.defaultdict(list)
    for m in c.sp_maps():
        for o in c.objects(m):
            if re.match(r"^(BarPiece|BarCorner|BarHingedTop)", o["type"]):
                pieces[m].append((o["type"], (o["x"] + o["y"]) / 23, (o["x"] - o["y"]) / 23))
    series_axis = collections.defaultdict(collections.Counter)
    corner_arms = collections.defaultdict(collections.Counter)
    spacing, letters = [], collections.defaultdict(collections.Counter)
    for m, ps in pieces.items():
        for t, u, v in ps:
            mm = re.match(r"^(BarPiece|BarCorner)(\d)([A-E])$", t)
            if mm: letters[mm[1] + mm[2]][mm[3]] += 1
            nbs = [(t2, u2 - u, v2 - v) for t2, u2, v2 in ps if (t2, u2, v2) != (t, u, v) and math.hypot(u2 - u, v2 - v) < 2.6]
            for t2, du, dv in nbs:
                spacing.append(math.hypot(du, dv) * K)
                d = ("+u" if du > 0 else "-u") if abs(du) > abs(dv) else ("+v" if dv > 0 else "-v")
                if t.startswith("BarCorner"): corner_arms[t[:10]][d] += 1
                elif t.startswith("BarPiece"): series_axis[t[:9]]["u" if d in ("+u", "-u") else "v"] += 1
                elif t == "BarHingedTop": series_axis["BarHingedTop"]["u" if d in ("+u", "-u") else "v"] += 1
    return dict(
        grid_uv=2, spacing_px=q(spacing),
        series_axis={k: dict(axis=v.most_common(1)[0][0], share=round(v.most_common(1)[0][1] / sum(v.values()), 2), n=sum(v.values()))
                     for k, v in sorted(series_axis.items())},
        corner_arms={k: dict(arms=[a for a, _ in v.most_common(2)], n=sum(v.values())) for k, v in sorted(corner_arms.items())},
        letters={k: dict(v.most_common()) for k, v in sorted(letters.items())},
        side_series={"low_u": "BarPiece1", "high_u": "BarPiece3", "low_v": "BarPiece2", "high_v": "BarPiece4"},
        note="An L or U outline on the grid: v-runs use BarPiece1 (low-u side) / BarPiece3 (high-u side), u-runs use "
             "BarPiece2 (low-v side) / BarPiece4 (high-v side); corners join the arms listed in corner_arms.")


def write_md(out):
    L = ["# Room types\n",
         "Westwood's single-player building rooms classified by contents, with everything the furnisher "
         "needs to generate new rooms of each type. Distributions only: no stock layout is stored. "
         "Generated by `rules/room_types.py`.\n",
         "## JSON schema (`rules/out/room_types.json`)\n",
         "- `k_px_per_uv`: pixels per unit of the rotated coordinates u = x + y, v = x - y.",
         "- `types.<type>`: `rooms`, `weighted`, `maps`; `tiles`, `u_extent`, `v_extent` (quantiles); `floors`, "
         "`wall_materials` (shares); `doors`; `inventory.<family>`: `p_present` (share of rooms with it), `count`, "
         "`per100_tiles` (quantiles where present), `roles` (wall / corner / center), `wall_sides` (decoration.json side "
         "keys), `perp_px` (distance from the wall line when against a wall), `object_types` (which objects represent "
         "the family), `evidence`; `visible_lights`; `colorlights`; `npcs` (`p_npc`, `p_shopkeeper`).",
         "- `sets.<anchor>+<companion>`: companions within 60 px of anchors: `per_anchor` count quantiles, `distance_px`, "
         "`axis_share` (share placed along a u or v axis from the anchor).",
         "- `chair_facing.<chair family>.<direction>`: the variant used when the anchor (table/desk) lies in that uv "
         "direction from the chair (`+u` = down-right on screen, `-u` = up-left, `+v` = up-right, `-v` = down-left).\n",
         "Classification (first match): shop (trader desk, 2+ shop racks or a shopkeeper), tavern (bar counter), "
         "smithy, laboratory, throne room, chapel (altar), crypt (2+ tombs), kitchen (stove), barracks (3+ beds), "
         "bedroom, library (2+ shelves), dining hall (2+ tables, 4+ seats), study (desk + shelves), living room "
         "(table or desk), storeroom (3+ storage), hall (statues/columns), other, empty; rooms dominated by dungeon "
         "objects (spikes, bones, generators) are `dungeon`.\n",
         "## Types\n",
         "| type | rooms (weighted) | maps | tiles p25/p50/p75 | main floors | top furniture families (share of rooms) |",
         "|---|---|---|---|---|---|"]
    for t, d in sorted(out["types"].items(), key=lambda kv: -kv[1]["weighted"]):
        inv = sorted(d["inventory"].items(), key=lambda kv: -kv[1]["p_present"])[:6]
        tl = d["tiles"] or {}
        L.append(f"| {t} | {d['rooms']} ({d['weighted']}) | {d['maps']} | {tl.get('p25')}/{tl.get('p50')}/{tl.get('p75')} | "
                 f"{', '.join(list(d['floors'])[:3])} | {', '.join(f'{k} {v['p_present']:.0%}' for k, v in inv)} |")
    L += ["", "## Placement roles of key families (all types)\n", "| type | family | roles | wall sides | perp px p50 |", "|---|---|---|---|---|"]
    for t, d in sorted(out["types"].items()):
        if t in ("dungeon", "empty", "other"): continue
        for f, inv in d["inventory"].items():
            if inv["evidence"]["weighted"] < 3: continue
            L.append(f"| {t} | {f} | {', '.join(f'{k} {v:.0%}' for k, v in inv['roles'].items())} | "
                     f"{', '.join(f'{k} {v:.0%}' for k, v in list(inv['wall_sides'].items())[:4])} | {(inv['perp_px'] or {}).get('p50')} |")
    L += ["", "## Furniture sets\n", "| anchor + companion | pairs | per anchor p50 | distance px p50 | along an axis |", "|---|---|---|---|---|"]
    for k, s in sorted(out["sets"].items(), key=lambda kv: -kv[1]["weighted"])[:30]:
        L.append(f"| {k} | {s['pairs']} | {s['per_anchor']['p50']} | {s['distance_px']['p50']} | {s['axis_share']:.0%} |")
    L += ["", "## Chair variant by direction to the table/desk\n", "| family | +u | -u | +v | -v |", "|---|---|---|---|---|"]
    for b, dd in sorted(out["chair_facing"].items()):
        if sum(x["weighted"] for x in dd.values()) < 5: continue
        L.append(f"| {b} | " + " | ".join(f"{dd[q]['variant']} ({dd[q]['share']:.0%})" if q in dd else "" for q in ("+u", "-u", "+v", "-v")) + " |")
    a = out["assemblies"]["bar_counter"]
    L += ["", "## Bar counter assembly\n", a["note"], "",
          f"Spacing between neighbouring pieces: {a['spacing_px']} px.", "",
          "| piece series | runs along | share | pieces |", "|---|---|---|---|"]
    L += [f"| {k} | {v['axis']} | {v['share']:.0%} | {v['n']} |" for k, v in a["series_axis"].items()]
    L += ["", "| corner | arms | evidence |", "|---|---|---|"]
    L += [f"| {k} | {', '.join(v['arms'])} | {v['n']} |" for k, v in a["corner_arms"].items()]
    L += ["", "## Wall side by object type (`type_wall_sides`)\n",
          "Which wall side each object type stood against, for orienting variant sets without paired rules "
          "(e.g. Bookcase1-4). Types with a clear (>= 90%) preference and at least 10 weighted placements:", "",
          "| type | side | share | weighted |", "|---|---|---|---|"]
    for t, d in out["type_wall_sides"].items():
        side, share = max(((k, v) for k, v in d.items() if k != "n"), key=lambda kv: kv[1])
        if share >= 0.9 and d["n"] >= 10: L.append(f"| {t} | `{side.replace('|', chr(92) + '|')}` | {share:.0%} | {d['n']} |")
    c.save_section("room_types.md", "\n".join(L) + "\n")


if __name__ == "__main__":
    main()
