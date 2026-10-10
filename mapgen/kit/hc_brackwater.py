"""The Hollow Choir: Brackwater's town plan, shared by act 1 (mapgen/designs/hc01_brackwater.py, Brackwatr) and act 10
(mapgen/designs/hc10_lastbell.py, LastBell: the same town, burning). Both acts call plan() with the same seed, so the
land, the river and its pool, the two bridges, the docks, the roads, the square and every building stand in the same
place: the player who comes back in act 10 knows the streets. What differs comes after: the ground's palette, the
town's life, the story's places, the people and the fights.

The plan (screen squares X right, Y down; the river runs from the north-west wood to the south-east along the grid's
i axis, the town on its north-east bank):
- the square and its streets on the north-east bank: the Bell Shrine, the watch house, the inn, Doran's smithy, Wenna's
  herb shop, the river store, houses;
- the Brack, a slow river, widening into the Brack Pool south-east of the square, where the barges tie up at the quay
  (a dock on the pool, the bargemen's houses on the docks road);
- the town bridge (a rope bridge) on the road south-west from the square to the south landing, a crossroads on the far
  bank: the camp road east along the river, the river road south-west to the River Gate and on toward the Mirewood;
- the old bridge upriver, from the ferry lane at the town's north-west end to the old mill on the far bank;
- downstream, past the pool: the reed bank on the near side, a clearing in the old wood on the far side;
- a glade in the wood north-east of the square, joined to the town and the docks by forest paths.

    from kit.hc_brackwater import plan, uv
    P = plan(m, identity, regions, section_of, seed=SEED)      # P.land, P.sm, P.placed, P.ww, P.lake, P.docks, ...
"""
import math, random

from nox import CELL
from kit.identity import BuildingIdentity
from kit.layout import Land, square_px, px_square, cell_square
from kit.water import Waterworks
from kit import yards as Y
from kit.story import StoryMap

SEED = 11


def uv(X, Y):
    """uv of a point given in map squares as seen on screen (X right, Y down, 0..255)."""
    return (X + Y, X - Y)


# areas: (screen X, Y), radius in uv units. i = (X + Y) / 2 runs down the river, j = (X - Y) / 2 across it (the town
# on the j > 0 side).
AREAS = {"town": ((150, 96), 80), "lane": ((88, 52), 16), "mill": ((52, 88), 24), "south": ((96, 150), 16),
         "gate": ((66, 182), 12), "mire": ((40, 208), 12), "docks": ((196, 156), 26), "pool": ((178, 178), 40),
         "reeds": ((222, 186), 18), "camp": ((184, 220), 28), "glade": ((196, 70), 22)}
# the sections: the oak wood round the town and the roads, the red wood of the old mill upriver, the old brown wood
# downstream (the reed bank and the far clearing)
SECTION = {"town": "oak", "lane": "oak", "south": "oak", "gate": "oak", "mire": "oak", "docks": "oak", "pool": "oak",
           "glade": "oak", "mill": "dusk", "reeds": "old", "camp": "old"}
# (a, b, width uv, road, bend)
LINKS = (("town", "docks", 13, True, 0.12), ("town", "south", 14, True, 0.04), ("town", "lane", 12, True, 0.12),
         ("lane", "mill", 12, True, 0.04), ("south", "gate", 13, True, 0.10), ("gate", "mire", 12, True, 0.10),
         ("south", "camp", 12, True, 0.12), ("docks", "reeds", 11, False, 0.18), ("south", "mill", 11, False, 0.22),
         ("town", "glade", 11, False, 0.2), ("glade", "docks", 11, False, 0.2), ("pool", "camp", 13, False, 0.12))
CARVE = (3.5, 0.45)            # the land's margin round what is placed, and its edge's roughness (Land.carve)
THICKETS = (120, (0.9, 1.8))    # islands of forest in the open (Land.thickets: count, radius)
LAKE_R = 10                    # the Brack Pool, tiles
RIVER_W = 3.0                  # the Brack, tiles
POOL = uv(178, 178)            # the pool's middle (uv), on the river
RIVER_W_END, RIVER_E_END = uv(44, 44), uv(214, 214)      # the river comes out of the wood and goes back into it

# The buildings: roles and areas fixed (they decide where everything stands); act 10 keeps them and may rename them.
BUILDINGS = [
    BuildingIdentity("village_chapel", "town", "the Bell Shrine", "Brother Edric, keeper of the bell"),
    BuildingIdentity("barracks", "town", "the watch house", "Captain Ilsa Rook and the watch", extra=("cell",)),
    BuildingIdentity("inn", "town", "the Bargeman's Rest", "Hanne the innkeeper"),
    BuildingIdentity("smithy", "town", "Ashforge's smithy", "Doran Ashforge, the old smith"),
    BuildingIdentity("apothecary", "town", "Fell's herb shop", "Wenna Fell, the herbalist", style="cobble_house"),
    BuildingIdentity("store", "town", "the river store", "Bram the chandler"),
    BuildingIdentity("fisher", "docks", "Nell's house", "Nell the eel-wife"),
    BuildingIdentity("fisher", "docks", "", "a bargeman's family"),
    BuildingIdentity("home", "town", "", "a ferryman's family"),
    BuildingIdentity("home", "town", "", "a cooper's family"),
    BuildingIdentity("home", "town", "", "a rope-maker's family"),
    BuildingIdentity("cottage", "town", "", "an old net-maker"),
    BuildingIdentity("cottage", "town", "", "a bell-ringer's widow"),
    BuildingIdentity("mill", "mill", "the old mill", "Abel the miller"),
]


class Plan:
    """What plan() built: land, sm (StoryMap), placed, yards, built (yard kinds), ww, lake, river, crossings,
    bridges, docks, gate (halves, points, square), C (area centres in squares)."""


def plan(m, identity, wall_of, floor_of, seed=SEED, regions=None, furnish_seed=None):
    """Lays Brackwater's land, water, roads, square, buildings and yards into spec `m` (identity: the act's
    MapIdentity, whose buildings are BUILDINGS in this order). wall_of / floor_of: section -> forest wall / ground
    material (each act its own palette). regions: {section: ...} for the caller's ground_variety. Every step draws from
    its own generator, so what an act does after (or a furnishing that differs with the map's name) never moves the
    plan: both acts get the same town."""
    assert [(b.role, b.area, b.style, b.extra) for b in identity.buildings] == \
           [(b.role, b.area, b.style, b.extra) for b in BUILDINGS], "the act's buildings must be Brackwater's"
    P = Plan()
    rng = random.Random(seed)
    land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
    for k_, ((X_, Y_), r_) in AREAS.items():
        land.area(k_, uv(X_, Y_), r_, clearing=k_ != "town", region=SECTION[k_])
        ar = land.areas[k_]
        x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
        assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
    for a_, b_, w_, road_, bend_ in LINKS:
        land.link(a_, b_, w_, bend=bend_, road=road_, pockets=(1, 2) if road_ else (0, 1))
    land.blends(m)

    # the river and its two crossings, planned with the roads before anything is built: the town bridge on the road
    # from the square to the south landing, the old bridge on the lane to the mill; the river is laid through both,
    # square to each road, and on through the pool
    cross_town = land.plan_crossing("town", "south", t=0.5, approach=8)
    cross_mill = land.plan_crossing("lane", "mill", t=0.5, approach=7)
    pts = [RIVER_W_END]
    for cr in (cross_mill, cross_town):
        C_ = cr["uv"]
        fu, fv = cr["flow"]
        if (RIVER_E_END[0] - C_[0]) * fu + (RIVER_E_END[1] - C_[1]) * fv < 0: fu, fv = -fu, -fv   # toward the east end
        pts += [(C_[0] - 16 * fu, C_[1] - 16 * fv), C_, (C_[0] + 16 * fu, C_[1] + 16 * fv)]
    pts += [(POOL[0] - 30, POOL[1]), POOL, (POOL[0] + 30, POOL[1]), RIVER_E_END]
    land.reserve_band(pts, 3.6)
    land.reserve_band([POOL], LAKE_R * 1.35 + 1.5)
    P.river, P.crossings = pts, (cross_town, cross_mill)

    # the centre: the square, the roads leaving it
    land.paint_square(m, "town", 12, "RoughCobble")
    vc = land.areas["town"]["c"]
    land.taken |= {(int(vc[0]) + a, int(vc[1]) + 1 + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}
    mill_c0 = land.areas["mill"]["c"]                     # the lane stops short of the old mill's door
    land.paint_roads(m, "DirtDark2", width_squares=2.8,
                     skip=land.reserved | {(i, j) for i in range(int(mill_c0[0]) - 12, int(mill_c0[0]) + 13)
                                           for j in range(int(mill_c0[1]) - 12, int(mill_c0[1]) + 13)
                                           if math.hypot(i - mill_c0[0], j - mill_c0[1]) < 9})

    # the buildings, from the square outwards; the bargemen's houses on the docks road first
    sm = StoryMap(m, rng, land, identity)
    placed = sm.place_buildings(no_build={"south": 9, "camp": 16, "reeds": 9, "gate": 6, "mire": 7, "glade": 8,
                                          "lane": 4},
                                first=("docks",), centred={"mill": "lane"})
    sm.rng = random.Random(seed * 7 + 1 if furnish_seed is None else furnish_seed)   # the furnishing's own draws
    sm.connect_and_furnish()
    after = random.Random(seed * 7 + 2)                  # everything after the buildings
    land.rng, sm.rng, m.rng = after, after, random.Random(seed * 7 + 3)

    # the yards: the shrine's graveyard, an orchard behind the houses, the miller's field
    yards = []

    def ring_of(c, radii):
        return [(c[0] + r * math.cos(a * math.pi / 6), c[1] + r * math.sin(a * math.pi / 6)) for r in radii for a in range(12)]

    for kind_, area_, rs_, toward_ in (("graveyard", "town", (22, 26, 30, 34, 38, 42), "town"),
                                       ("orchard", "town", (18, 22, 26, 30, 34), "town"),
                                       ("field", "mill", (8, 11, 14), "mill")):
        y_ = Y.plan_any(land, after, kind_, ring_of(land.areas[area_]["c"], rs_), toward=land.areas[toward_]["c"])
        if y_: yards.append(y_)
        else: print(f"no room for the {kind_}")

    # the land grows round everything, ending in the forest wall
    land.carve(margin=CARVE[0], roughness=CARVE[1])
    lane_ = sm.keep_open({"south": 5, "camp": 10, "reeds": 7, "mill": 5, "lane": 3, "docks": 3, "gate": 3, "mire": 3,
                          "glade": 6})
    land.assign_regions()
    P.thickets = land.thickets(THICKETS[0], size=THICKETS[1], clear=1, avoid=frozenset(lane_ & land.squares))
    land.open_links()

    def section(r):
        if r in SECTION.values(): return r
        for part in (r or "").split("_")[1:]:
            if part in SECTION: return SECTION[part]
        return SECTION.get(r, "oak")

    land.region_map = {s_: section(r_) for s_, r_ in land.region_map.items()}
    land.apply(m, wall=wall_of, floor=floor_of, unlevel=True)
    built = []
    for y_ in yards:
        if not y_.plot <= land.squares:
            print(f"the {y_.kind} lies off the land"); continue
        Y.build(m, after, land, y_)
        built.append(y_)

    # the water: the river dug through its band and the pool, a rope bridge on each planned crossing
    ww = Waterworks(m, after, inside=lambda x, y: m.floor.get((x, y), "").startswith(("Grass", "Dirt")))
    lake = ww.pond(POOL, radius=LAKE_R, roughness=0.28)
    river = ww.stream(pts, width=RIVER_W, wiggle=1.6, calm=[(cr["uv"], 16) for cr in (cross_town, cross_mill)])
    bridges = []
    for cr in (cross_town, cross_mill):
        C_, span = cr["uv"], 10
        a_uv, b_uv = ((C_[0] - span, C_[1]), (C_[0] + span, C_[1])) if cr["axis"] == "u" else \
            ((C_[0], C_[1] + span), (C_[0], C_[1] - span))
        bridges.append(ww.rope_bridge(a_uv, b_uv, kit=cr["kit"]))
    for b_ in ww.bodies:
        for t in b_.tiles:
            if "Water" in m.floor.get(t, ""): land.water.add(cell_square(*t))
    # the quay: a dock out into the pool where the docks road comes down to it, a path from its foot to the road
    docks_c = land.areas["docks"]["c"]
    docks = []
    for length_, beyond_ in ((2, 3), (1, 2)):
        d_ = ww.dock(lake, "best", length=length_, beyond=beyond_, near=(2 * docks_c[0], 2 * docks_c[1]))
        if d_:
            du_, dv_ = d_["start"]
            land.connect(m, px_square((du_ + dv_) / 2 * CELL, (du_ - dv_) / 2 * CELL))
            docks.append(d_)
    for c in list(ww.no_walls): land.taken.add(cell_square(*c))

    # the River Gate: a wall of grey stone across the river road from forest to forest, a double gate in it
    gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "mire"), prefix="RiverGate")

    P.land, P.sm, P.placed, P.yards, P.built = land, sm, placed, yards, built
    P.ww, P.lake, P.stream, P.bridges, P.docks = ww, lake, river, bridges, docks
    P.gate = (gate_halves, gate_pts, gate_sq)
    P.C = {k: land.areas[k]["c"] for k in AREAS}
    P.lane = lane_
    P.section = section
    P.rng = after
    return P


def bridge_ends(P, which=0):
    """The two ends of a bridge (world px): its landing on the near bank (j > 0, the town's side) first."""
    cr = P.crossings[which]
    C_ = cr["uv"]
    span = 12
    a_uv, b_uv = ((C_[0] - span, C_[1]), (C_[0] + span, C_[1])) if cr["axis"] == "u" else \
        ((C_[0], C_[1] + span), (C_[0], C_[1] - span))
    to_px = lambda p: ((p[0] + p[1]) / 2 * CELL, (p[0] - p[1]) / 2 * CELL)
    a, b = to_px(a_uv), to_px(b_uv)
    # the near bank has the larger v (j > 0)
    return (a, b) if a_uv[1] >= b_uv[1] else (b, a)


JOURNEYMAN = ("War01A", "Tyler")        # Doran's journeyman works the anvil (Doran himself is CAST's Con02a:Bryan)


def place_forge(m, mods, sm, room, store, lines=("longsword", "battleaxe"), copies=2):
    """The smithing forge (kit/mods.py S1, as Mods.forge lays it) in a smithy: the anvil where the forge room's own anvil
    stood, the journeyman beside it (cloned as Doran's journeyman: Doran is the stock smith's body, CAST), the forge
    plate of black stone about 130 px off on clear floor, and the forged copies the anvil hands out (Mods.forge keeps
    them in a vault sealed off the land, which the checker counts as weapons no one can reach) kept instead in the
    smithy's own stock room `store`, its door locked to a mechanism no script turns: Doran's strongroom. Returns
    dict(anvil, smith, plate) in world px."""
    import os
    from kit.mods import FORGE_LINES, WEAPONS, _ench
    from kit.story import STOCK
    from kit.npcs import facing
    cells = set(room.tiles)
    on_room = lambda x, y, cs=cells: any((int(x // CELL) + a, int(y // CELL) + b) in cs
                                         for a, b in ((0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)))
    anvils = [o for o in m.d["objects"] if o.get("type", "").startswith("Anvil") and on_room(o["x"], o["y"])]
    if anvils:
        anvil = (anvils[0]["x"], anvils[0]["y"])
        for o in anvils: m.d["objects"].remove(o)
    else:
        anvil = sm.stand_px(room)
    objs = [(o["x"], o["y"]) for o in m.d["objects"] if "x" in o]
    near_wall = lambda x, y, r=1: any((int(x // CELL) + i, int(y // CELL) + j) in m.wallmap for i in range(-r, r + 1)
                                      for j in range(-r, r + 1))
    clear = lambda x, y, r: all(math.hypot(x - p, y - q) >= r for p, q in objs)
    smith = None
    for d in (36, 42, 30, 48):
        for k in range(16):
            x, y = anvil[0] + d * math.cos(k * math.pi / 8), anvil[1] + d * math.sin(k * math.pi / 8)
            if on_room(x, y) and not near_wall(x, y) and clear(x, y, 22):
                smith = (x, y); break
        if smith: break
    smith = smith or (anvil[0] + 30, anvil[1])

    def plate_ok(x, y, wall_r, clr):
        cx, cy = int(x // CELL), int(y // CELL)
        for dx in range(-1, 3):
            for dy in range(-1, 3):
                c = (cx + dx, cy + dy)
                if (c[0] + c[1]) % 2 == 0 and c not in cells: return False
                if c in m.wallmap: return False
        return not near_wall(x, y, wall_r) and clear(x, y, clr) and math.hypot(x - smith[0], y - smith[1]) > 50
    plate = None
    for wall_r, clr in ((2, 34), (1, 30), (1, 24)):     # the plate's own clear floor first, then a little tighter
        for d in (130, 120, 140, 110, 150, 100, 160, 90):
            for k in range(24):
                x, y = anvil[0] + d * math.cos(k * math.pi / 12), anvil[1] + d * math.sin(k * math.pi / 12)
                if plate_ok(x, y, wall_r, clr): plate = (x, y); break
            if plate: break
        if plate: break
    assert plate, "no clear floor for the forge plate in the smithy"
    # (kit/mods.py Mods.forge, the anvil, plate and smith as it lays them)
    m.obj_px("Anvil2", *anvil, scr="S1_Anvil")
    pcx, pcy = int(plate[0] // CELL), int(plate[1] // CELL)
    for dx in range(-1, 3):
        for dy in range(-1, 3):
            m.tile(pcx + dx, pcy + dy, "LOTDBlackMarble")
    m.clone(os.path.join(STOCK, JOURNEYMAN[0], JOURNEYMAN[0] + ".map"), f"{JOURNEYMAN[0]}:{JOURNEYMAN[1]}", *smith,
            name="S1_Smith", xfer={"DirectionId": facing(anvil[0] - smith[0], anvil[1] - smith[1])})
    mods.calls.append(f'ModForge("S1_Anvil", {plate[0]:.1f}, {plate[1]:.1f}, "S1_Smith")')
    # the forged copies in the stock room, on its open floor, off its walls
    scells = set(store.tiles)
    spots = sorted({((x + 1) * CELL, (y + 1) * CELL) for x, y in scells if not near_wall((x + 1) * CELL, (y + 1) * CELL)},
                   key=lambda p: (p[1], p[0]))
    taken = []
    for key in lines:
        L = FORGE_LINES[key]
        if "weapon" in L:
            w = WEAPONS[L["weapon"]]
            base, kind, tiers, n = w["base"], w["kind"], w["tiers"], 1
        else:
            base, kind, tiers, n = L["base"], "", L["tiers"], copies
        names = []
        for t in (1, 2, 3):
            tn = []
            for c in range(n):
                nm = f"Forge_{key}_{t}_{c + 1}"
                at = next((p for p in spots if all(math.hypot(p[0] - a, p[1] - b) >= 20 for a, b in taken)), spots[0])
                taken.append(at)
                x_ = {"Enchantments": _ench(tiers[t])} if tiers[t] else {}
                m.obj_px(base, *at, scr=nm, **({"xfer": x_} if x_ else {}))
                tn.append(nm)
            names.append(tn)
        mods.forge_line(key, L["label"], base, kind, [], *names)
    sm.lock_room(store, lock="Mechanism")
    return dict(anvil=anvil, smith=smith, plate=plate)
