"""How each scene type is laid in the lab: the kit's own code, called as a map's design calls it.

A recipe is dict(plan=f(ctx) before the land is carved, build=f(ctx) after its walls, after_plant=f(ctx) last (the
catalogue's scenes, which the dressing lays after the planting), pond=True when the scene is a pond). ctx: m (the
Spec), rng, land, plots (labgen.Plot), scene, seed, log; a recipe adds pop (kit/npcs.Population), ww (the
Waterworks), keep (squares the planter keeps clear), and per plot p.notes["anchor"] (px): where the scene was laid.
"""
import math, random
import labenv as E
from kit import camps, yards as Y
from kit.layout import square_px, px_square, tile_square, square_tile, cell_square

LOOT = [("Gold", {"Amount": 40}), "RedPotion"]


def _pop(ctx):
    if "pop" not in ctx:
        from kit.npcs import Population
        ctx["pop"] = Population(ctx["m"], random.Random(E.seed_of("pop", ctx["scene"], ctx["seed"])))
    return ctx["pop"]


def _person(ctx, donor, x, y, face, name):
    """A townsperson cloned in their clothes from a stock map (kit/story.Story.person: donor = (map, script name)),
    standing at work (action 4), facing `face`."""
    import os
    from kit.story import STOCK
    from kit.npcs import facing
    xf = dict(DefaultAction=4, Aggressiveness=0.0, Immortal=True)
    if face: xf["DirectionId"] = facing(face[0] - x, face[1] - y)
    mp, scr = donor
    return ctx["m"].clone(os.path.join(STOCK, mp, mp + ".map"), f"{mp}:{scr}", x, y, name=name, xfer=xf)


def _keep(ctx, centre, r):
    ctx.setdefault("keep", set()).update({(int(centre[0]) + a, int(centre[1]) + 1 + b) for a in range(-r, r + 1)
                                          for b in range(-r, r + 1) if a * a + b * b <= r * r})


def _new_objects(m, n0, rx=None):
    import re
    return [o for o in m.d["objects"][n0:] if "type" in o and (rx is None or re.match(rx, o["type"]))]


def _mean(objs):
    return [round(sum(o["x"] for o in objs) / len(objs), 1), round(sum(o["y"] for o in objs) / len(objs), 1)]


# ---------------------------------------------------------------------------------------------------- camps
def _camp_build(kind):
    def build(ctx):
        from kit.posts import camp_posts
        m, land = ctx["m"], ctx["land"]
        pop = _pop(ctx)
        for p in ctx["plots"]:
            rng = p.rng
            site = camps.camp_site(m, land, p.scene_c, reach=p.r - 3, road_clear=3.0, room=7)     # as the designs let it
            toward = p.toward
            sleepers = {"small": 3, "typical": 4, "large": 6}[p.size]
            tents = {"small": 1, "typical": 2, "large": 3}[p.size]
            if kind == "bandit_camp":
                trade = "dig" if p.k % 4 == 3 else "bandit"
                camp = camps.bandit_camp(m, rng, land, site, toward, loot=LOOT, sleepers=sleepers, tents=tents,
                                         trade=trade, finds=("MineCrystal01", "MineCrystal03", "CaveRocksSmall"))
                # the designs' bands: 4-7 people, median 5 (Thornwick, Greywatch, Harrowby, Ambermere, Starwell)
                hide = camp.get("hideout")                  # a hideout's band is smaller (Westwood's: two or three)
                posts = camp_posts(m, camp, square_px(*toward), sit=0 if hide else 1 + (p.size != "small"), tents=1,
                                   watch=1, work=2 if trade == "dig" and not hide else 0)
                kinds = dict(leader="Swordsman", sit="Swordsman", tent="Swordsman", watch="Archer", work="Swordsman")
                p.notes.update(trade=trade, sleepers=sleepers, tents=tents)
            elif kind == "ogre_camp":
                camp = camps.ogre_camp(m, rng, land, site, toward, loot=LOOT, sleepers=sleepers)
                posts = camp_posts(m, camp, square_px(*toward), sit=2, tents=1, watch=2, work=0)
                kinds = dict(leader="OgreWarlord", sit="GruntAxe", tent="GruntAxe", watch="OgreBrute", work="GruntAxe")
            else:
                camp = camps.urchin_camp(m, rng, land, site, toward, loot=LOOT, sleepers=sleepers + 1)
                posts = camp_posts(m, camp, square_px(*toward), sit=2, tents=2, watch=1, work=0)
                kinds = dict(leader="UrchinShaman", sit="Urchin", tent="Urchin", watch="Urchin", work="Urchin")
            fx, fy = camp["fire"]
            pop.creature(kinds["leader"], *posts["leader"], action="guard", face=square_px(*toward), aggr=0.5)
            for role in ("sit", "tent", "work", "watch"):
                for x, y in posts[role]:
                    pop.creature(kinds[role], x, y, action="guard" if role == "watch" else "idle",
                                 face=square_px(*toward) if role == "watch" else (fx, fy), aggr=0.5)
            p.notes["anchor"] = [round(fx, 1), round(fy, 1)]
            p.notes["site_sq"] = [round(site[0], 1), round(site[1], 1)]
    return build


# ---------------------------------------------------------------------------------------------------- yards
def _yard_plan(kind):
    def plan(ctx):
        land = ctx["land"]
        ctx["yards"] = {}
        for p in ctx["plots"]:
            ring = [(p.c[0] + r * math.cos(k * math.pi / 4), p.c[1] + r * math.sin(k * math.pi / 4))
                    for r in (3, 5) for k in range(8)]
            y = Y.plan_any(land, p.rng, kind, [p.scene_c, p.c] + ring, toward=p.toward)      # as the designs plan
            if y: ctx["yards"][p.k] = y; p.notes["scene_sq"] = list(y.centre)
            else: ctx["log"](f"  plot {p.k + 1}: no room for the {kind}")
    return plan


def _yard_build(ctx):
    m, land = ctx["m"], ctx["land"]
    for p in ctx["plots"]:
        y = ctx["yards"].get(p.k)
        if not y or not y.plot <= land.squares: continue
        Y.build(m, p.rng, land, y)
        p.notes["anchor"] = list(square_px(*y.centre))
        p.notes["yard"] = dict(w=y.w, h=y.h, side=y.side)
        out = Y.gate_outside(y)                       # the walk from the gate to the road, as a map's yards have
        if out and out in land.squares:
            got = land.connect(m, out, footprint=frozenset(y.plot), material="DirtDark2")
            p.notes["walk"] = len(got) if got else 0
        for k_, (donor, (x, yy), face) in enumerate(getattr(y, "people", ())):   # the yard's people at work (the digger)
            _person(ctx, donor, x, yy, face, f"Yard{p.k}_{k_}")


def _jail_court(ctx):
    """Westwood's jails stand in paved town courts (Con07B's castle, Con02a's and War03b's guardhouse yards, all on
    RoughCobble): the lab paves a court round the jail in two clearings of three, so the jail's floor is not read as a
    path laid through the grass."""
    m, land = ctx["m"], ctx["land"]
    for p in ctx["plots"]:
        y = ctx["yards"].get(p.k)
        if not y or p.k % 3 == 2: continue
        for a in range(-3, y.w + 3):
            for b in range(-3, y.h + 3):
                sq = (y.gi + a, y.gj + b)
                if sq in land.squares and sq not in land.water and sq not in land.taken_strict:
                    m.floor[square_tile(*sq)] = "RoughCobble"


# ---------------------------------------------------------------------------------------------------- gardens
HOME_ROLES = ("home", "cottage", "home", "fisher", "herbwife")
GARDENERS = (("Con02a", "Gretchen"), ("Con03A", "Kenneth"), ("Con02a", "Julie"))


def _house(ctx, p, role, at, side=None, quiet=False):
    """A small house of `role` with its footprint's corner near `at` (squares), by the kit's building generator."""
    from kit.building import generate_building
    from kit.identity import BUILDINGS, BuildingIdentity, role_size
    from kit.village import _squares_of
    m, land = ctx["m"], ctx["land"]
    r = BUILDINGS[role]
    size0, min_units = role_size(r)
    program = [k for k, _ in r["rooms"]]
    for shrink in (0.85, 0.75, 0.65):
        size = (2 * round(size0[0] * shrink / 2), 2 * round(size0[1] * shrink / 2))
        for di in (0, -2, 2, -4, 4):
            for dj in (0, -2, 2, -4, 4):
                o = (2 * int(at[0] + di - size[0] / 4), 2 * int(at[1] + dj - size[1] / 4))
                if not land.lot_free(o, size, margin=1): continue
                b = generate_building(m, p.rng, o, size, r["style"], program=program, entrance_side=side,
                                      building_id=f"H{p.k}", occupied={square_tile(*s) for s in land.taken}, tries=10,
                                      shape="rect", min_units=int(min_units * shrink * shrink))
                if b:
                    land.take_cells(b.cells, margin=1)
                    land.wall_cells |= set(m.wallmap)
                    land.taken_strict |= _squares_of(b.footprint)
                    bid = BuildingIdentity(role, p.name, "", "")
                    ctx.setdefault("placed", []).append((bid, b))
                    from kit.originality import furnish_original
                    for room in b.rooms:                 # furnished as a map's are: their rooms show in the picture
                        furnish_original(m, room, kind=room.kind, rng=random.Random(E.seed_of("furnish", p.k, room.id)),
                                         style="town")
                    return bid, b
    if not quiet: ctx["log"](f"  plot {p.k + 1}: no room for the {role}")
    return None


def _garden_plan(ctx):
    land = ctx["land"]
    ctx["yards"], ctx["houses"] = {}, {}
    for p in ctx["plots"]:
        if p.size == "large" and p.site == "glade":
            y = Y.plan(land, p.rng, "field", p.scene_c, toward=p.toward)
            if y: ctx["yards"][p.k] = y
            continue
        ux, uy = p.dir
        role = HOME_ROLES[p.k % len(HOME_ROLES)] if p.size != "small" else "cottage"     # a small clearing: a cottage
        at = (p.c[0] - ux * 3.5, p.c[1] - uy * 3.5)
        h = _house(ctx, p, role, at, quiet=True) or _house(ctx, p, role, p.c)
        if h: ctx["houses"][p.k] = h; p.notes["scene_sq"] = [at[0], at[1]]


def _garden_build(ctx):
    from kit.village import Village
    m, land = ctx["m"], ctx["land"]
    land.clear_walls(m)
    for p in ctx["plots"]:
        y = ctx["yards"].get(p.k)
        if y:
            if y.plot <= land.squares:
                Y.build(m, p.rng, land, y)
                p.notes.update(anchor=list(square_px(*y.centre)), kind="field")
            continue
        h = ctx["houses"].get(p.k)
        if not h: continue
        bid, b = h
        from kit.village import _squares_of
        for d in b.entrances: land.connect_door(m, d, _squares_of(b.footprint))
        vil = Village(m, p.rng, land)
        n0 = len(m.d["objects"])
        size = {"small": (4, 3), "typical": (5, 4), "large": (6, 5)}[p.size]     # (Westwood's run 6-9 squares)
        if vil.garden(b, size=size):
            crops = _new_objects(m, n0, r"^Garden")
            if crops:
                p.notes.update(anchor=_mean(crops), kind="garden", role=bid.role)
                if p.rng.random() < 0.6:                 # the gardener at work at the beds' end
                    xs = sorted(crops, key=lambda o: o["x"] + o["y"])
                    a, z = xs[0], xs[-1]
                    q = a if p.rng.random() < 0.5 else z
                    mx, my = _mean(crops)
                    L_ = math.hypot(q["x"] - mx, q["y"] - my) or 1
                    _person(ctx, GARDENERS[p.k % len(GARDENERS)], q["x"] + (q["x"] - mx) / L_ * 34,
                            q["y"] + (q["y"] - my) / L_ * 34, (mx, my), f"Gardener{p.k}")


# ---------------------------------------------------------------------------------------------------- ponds and docks
POND_R = {"small": 6.0, "typical": 7.0, "large": 8.0}       # tiles: a lake a dock reaches out into (Con05A)
LAKE_R = {"small": 13.0, "typical": 15.0, "large": 16.0}    # a town's lakeshore: the lake on one side, the hamlet on the other (bigger: "every pier into a small closed pond")
DOCKS = {"small": 1, "typical": 2, "large": 3}              # docks to a lake (Con05A: three along its town's shore)
FISHERS = (("Con03A", "Kenneth"), ("Con07B", "Dorian"))


def _pond_plan(ctx):
    land = ctx["land"]
    for p in ctx["plots"]:
        pr = (LAKE_R if p.town else POND_R)[p.size]
        ux, uy = p.dir
        pc = p.c if p.site != "wall" else (p.c[0] + ux * 2.5, p.c[1] + uy * 2.5)
        if p.town: pc = (p.c[0] - ux * p.r * 0.3, p.c[1] - uy * p.r * 0.3)
        p.pond = (pc, pr)
        p.notes["scene_sq"] = [pc[0], pc[1]]
        land.reserve_band([(2 * pc[0], 2 * pc[1]), (2 * pc[0] + 0.1, 2 * pc[1])], pr + 1.0)
        if p.site == "road":
            p.toward = ((p.road[0][0] + p.road[1][0]) / 2, (p.road[0][1] + p.road[1][1]) / 2)
        else:
            p.toward = (p.c[0] - ux * p.r, p.c[1] - uy * p.r)


def _pond_build(ctx):
    from kit.water import Waterworks
    m, land = ctx["m"], ctx["land"]
    ww = ctx.setdefault("ww", Waterworks(m, ctx["rng"], inside=lambda x, y: tile_square(x, y) in land.squares))
    for p in ctx["plots"]:
        body = p.notes.pop("body", None)
        if body is None: continue
        n0 = len(m.d["objects"])
        t = p.toward
        dock = ww.dock(body, "best", length=2, beyond=4, near=(2 * t[0] + 2, 2 * t[1]))
        pcs = _new_objects(m, n0, r"^Dock")
        if dock and pcs:
            p.notes.update(anchor=_mean(pcs), kit=dock["kind"])
            du, dv = dock["start"]
            land.connect(m, px_square((du + dv) / 2 * 23, (du - dv) / 2 * 23))
            # a bank to reach it with no tree on it (the blind judge, 2026-10-06: "the root jammed against the tree line")
            _keep(ctx, px_square((du + dv) / 2 * 23, (du - dv) / 2 * 23), 5)
            # more docks along the town's shore (Con05A: three), each its own landing and walk
            (pci, pcj), _ = p.pond
            n_more = DOCKS[p.size] - 1 if p.town else 0
            for q in range(n_more):
                d2 = ww.dock(body, "best", length=2 if p.rng.random() < 0.6 else 1, beyond=3,
                             near=(du + (14 + 6 * q) * (1 if q % 2 == 0 else -1), dv + (10 + 4 * q) * (1 if q % 2 else -1)))
                if not d2: continue
                eu, ev = d2["start"]
                land.connect(m, px_square((eu + ev) / 2 * 23, (eu - ev) / 2 * 23))
                _keep(ctx, px_square((eu + ev) / 2 * 23, (eu - ev) / 2 * 23), 5)
            # a fisher at work on the first dock's landing, looking out over the water
            x_, y_ = (du + dv) / 2 * 23, (du - dv) / 2 * 23
            tip = (pcs[0]["x"], pcs[0]["y"])
            L_ = math.hypot(tip[0] - x_, tip[1] - y_) or 1
            if p.town and p.rng.random() < 0.8:
                near_ = [(o["x"], o["y"]) for o in m.d["objects"] if "type" in o and abs(o["x"] - x_) < 200 and
                         abs(o["y"] - y_) < 200 and not o["type"].startswith("Dock")]
                ex_, ey_ = (tip[0] - x_) / L_, (tip[1] - y_) / L_
                for f_, g_ in ((30, 26), (30, -26), (10, 40), (10, -40), (50, 0), (-20, 40), (-20, -40)):
                    fx_, fy_ = x_ + ex_ * f_ + ey_ * g_, y_ + ey_ * f_ - ex_ * g_
                    if all(math.hypot(fx_ - a, fy_ - b) >= 30 for a, b in near_):   # never on a fern or a barrel
                        _person(ctx, FISHERS[p.k % len(FISHERS)], fx_, fy_, tip, f"Fisher{p.k}")
                        break
        else:
            ctx["log"](f"  plot {p.k + 1}: no room for the dock")
            (ci, cj), _ = p.pond
            p.notes["anchor"] = list(square_px(ci, cj))
    for c in list(ww.no_walls): land.taken.add(cell_square(*c))


# ---------------------------------------------------------------------------------------------------- the catalogue
def _theme_after(themes, role=None, culture=None, biome="green"):
    """Scenes of kit/scenes.py's catalogue, laid by the dressing's own code (kit/dressing.Exterior: _try_wall,
    _try_open with only=the theme), one to a clearing, near the clearing's scene point."""
    def after(ctx):
        from kit.dressing import Exterior
        from kit import scenes as S
        m, land = ctx["m"], ctx["land"]
        placed = ctx.get("placed", [])
        for p in ctx["plots"]:
            ex = Exterior(m, land, biome, placed=placed, culture=culture, seed=p.k)
            ex._setup()
            ex.n0 = len(m.d["objects"])
            ex.cgrid = ex._grid(ex.colliders)
            ex._refresh()
            cx, cy = square_px(*p.scene_c)
            R = p.r * 32.5
            ex.signs = {f: [q for q in pts if math.hypot(q[0] - cx, q[1] - cy) < R] for f, pts in ex.signs.items()}
            names = [themes[(p.k + q) % len(themes)] for q in range(len(themes))]
            cands = sorted((s for s in ex.free if math.hypot(s[0] + 0.5 - p.scene_c[0], s[1] - 0.5 - p.scene_c[1]) < p.r - 1),
                           key=lambda s: (math.hypot(s[0] + 0.5 - p.scene_c[0], s[1] - 0.5 - p.scene_c[1]), s))
            done = None
            for name in names:
                th = S.THEMES[name]
                for s in cands[:400]:
                    n0 = len(m.d["objects"])
                    if th.stand == "wall":
                        x, y = square_px(s[0] + 0.5, s[1] - 0.5)
                        w = ex._nearest_wall(x, y, 2)
                        ok = w is not None and ex._try_wall(s, w, only={name})
                    else:
                        ok = ex._try_open(s, only={name})
                    if ok:
                        new = _new_objects(m, n0)
                        done = name
                        p.notes.update(anchor=[round(new[0]["x"], 1), round(new[0]["y"], 1)], theme=name)
                        break
                if done: break
            if not done: ctx["log"](f"  plot {p.k + 1}: none of {names} fitted")
    return after


def _house_plan(roles, square=0):
    """A house of one of `roles` at the clearing's side; `square` > 0: the ground before it kept open as a town's
    square is (a market stall's awning needs a market place; the planting had filled the lab's clearings)."""
    def plan(ctx):
        for p in ctx["plots"]:
            ux, uy = p.dir
            role = roles[p.k % len(roles)]
            # (a market's square before its store: the store at the clearing's side, the square kept open in the
            # middle; the store at 4.5 squares had stood on the square itself, and no awning found room by it)
            back = (p.r - 5.5) if (square and p.town) else 4.5
            side = None
            if square:                                   # its door toward the clearing (the market square before it)
                # (the building's u runs along the squares' i, its v along j)
                side = ("u_max" if ux > 0 else "u_min") if abs(ux) >= abs(uy) else ("v_max" if uy > 0 else "v_min")
            h = _house(ctx, p, role, (p.c[0] - ux * back, p.c[1] - uy * back), side=side)
            if square and h and h[1].entrances:
                # the market's square before the store's door, six and a half squares out
                from kit.village import _squares_of
                foot = _squares_of(h[1].footprint)
                fi, fj = sum(i for i, _ in foot) / len(foot), sum(j for _, j in foot) / len(foot)
                di, dj = px_square(*h[1].entrances[0].px)
                L = math.hypot(di - fi, dj - fj) or 1
                p.scene_c = (di + (di - fi) / L * 6.5, dj + (dj - fj) / L * 6.5)      # (a door keeps 3 squares clear)
                p.notes["scene_sq"] = list(p.scene_c)
            if square: _keep(ctx, p.scene_c, square)
    return plan


def _house_build(ctx):
    from kit.village import _squares_of
    m, land = ctx["m"], ctx["land"]
    land.clear_walls(m)
    done = ctx.setdefault("connected", set())
    for bid, b in ctx.get("placed", []):
        if id(b) in done: continue
        done.add(id(b))
        for d in b.entrances: land.connect_door(m, d, _squares_of(b.footprint))


def _nothing(ctx):
    pass


def _wreck_build(ctx):
    m, land = ctx["m"], ctx["land"]
    for p in ctx["plots"]:
        if p.site != "road" or p.k % 2: continue
        a, b = p.road
        c = (p.toward[0] - p.dir[0] * 2.0, p.toward[1] - p.dir[1] * 2.0)
        w = camps.wagon_wreck(m, p.rng, land, (int(c[0]) + 0.5, int(c[1]) - 0.5), math.atan2(b[1] - a[1], b[0] - a[0]))
        p.notes.update(anchor=[round(w["cart"][0], 1), round(w["cart"][1], 1)], theme="wagon_wreck")


def _wolf_build(ctx):
    m, land = ctx["m"], ctx["land"]
    pop = _pop(ctx)
    for p in ctx["plots"]:
        c = (int(p.scene_c[0]) + 0.5, int(p.scene_c[1]) - 0.5)
        spots = camps.wolf_den(m, p.rng, land, c, p.toward)
        for x, y in spots[:3 + (p.size == "large")]:
            pop.creature("Wolf", x, y, action="idle", aggr=0.5)
        p.notes["anchor"] = list(square_px(*c))


RECIPES = {
    # half the camps in a pocket of the rock (Westwood's hideouts: 10 of its 20 camps), the kit's own test (rock_pocket)
    # turns them into hideouts
    "bandit_camp": dict(plan=_nothing, build=_camp_build("bandit_camp"), caves=(1, 3, 5, 7, 8)),
    # Westwood's ogre fires burn in pockets of the swamp's root walls (Con05B, Con09b: RootLight)
    "ogre_camp": dict(plan=_nothing, build=_camp_build("ogre_camp"), caves=tuple(range(10)), cave_wall="RootLight",
                      cave_scale=1.7),
    # Westwood's urchins live in dens dug in the earth (42 of 42: Dirt walls on DirtDark2, Con02a, War03c, War03d,
    # Wiz01A): eight of ten in a pocket, the kit's own test (rock_pocket) turns them into dens
    "urchin_camp": dict(plan=_nothing, build=_camp_build("urchin_camp"), caves=(1, 2, 3, 4, 5, 7, 8, 9),
                        cave_wall="Dirt", cave_scale=1.3),
    "graveyard": dict(plan=_yard_plan("graveyard"), build=_yard_build, by_road=8.5),
    "quarry": dict(plan=_yard_plan("quarry"), build=_yard_build),
    "jail": dict(plan=_yard_plan("jail"), build=lambda c: (_jail_court(c), _yard_build(c))),
    "garden": dict(plan=_garden_plan, build=_garden_build),
    "pond_dock": dict(plan=_pond_plan, build=_pond_build, pond=True),
    # the well by the road, a public landmark (the judge, 2026-10-06: "no road ... placed by geometry rather than use")
    "well": dict(plan=_house_plan(["home", "inn", "cottage"]), build=_house_build, after_plant=_theme_after(["well_side"]),
                 by_road=3.5),
    "market_stall": dict(plan=_house_plan(["store", "inn"], square=5), build=_house_build,
                         after_plant=_theme_after(["market_stall"])),
    "wagon": dict(plan=_house_plan(["store", "mill", "home"]), build=lambda c: (_house_build(c), _wreck_build(c)),
                  after_plant=_theme_after(["wagon_verge", "unhitched_cart", "broken_wagon"])),
    "smithy_yard": dict(plan=_house_plan(["smithy"]), build=_house_build, after_plant=_theme_after(["smithy_yard"])),
    "training_ground": dict(plan=_house_plan(["barracks"]), build=_house_build,
                            after_plant=_theme_after(["sparring_ring", "archers_mark"])),
    "woodpile": dict(plan=_house_plan(["home", "cottage", "woodcutter"]), build=_house_build,
                     after_plant=_theme_after(["woodpile", "chopping_yard", "timber_stack"])),
    # the shrine by the village's chapel: masonry to stand against (the judge, 2026-10-06: "shrines set against wooden
    # peasant cabins")
    "shrine": dict(plan=_house_plan(["shrine", "mausoleum"]), build=_house_build,
                   after_plant=_theme_after(["waystone", "shrine"])),
    "farmyard": dict(plan=_house_plan(["mill", "home", "cottage"]), build=_house_build,
                     after_plant=_theme_after(["hay_store", "threshing_floor", "windmill"], culture="farm")),
    "wolf_den": dict(plan=_nothing, build=_wolf_build),
}
