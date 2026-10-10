"""Gauntlets: small combat maps to test the mods (mods/MODLAB.md) in a fight. Twenty of them, GT-01 to GT-20, each
built from one entry of THEMES (setting, layout, the monster it features, the boss).

Every gauntlet:
- starts in an armoury: the six power weapons (W1-W6) laid in a row with a sign by each, the featured weapons again
  forged a tier or two up, weapon and armour racks, and three chests: a warrior's kit (plate, shield, axe, sword), a
  caster's kit (robes, helms, staffs and wands) and supplies (potions, a bow and quivers);
- then three to five arenas joined by passages, each with a sign naming it (GT-07-A2 ...), its creatures waiting
  until you come near (the new monsters M1-M5 among the setting's own creatures, harder arena by arena), a few red
  potions at its far side;
- and a boss arena at the end, with the gauntlet's boss, a sign and a reward chest.

    py mapgen/designs/gauntlet.py <1-20> [out_dir|-]      (or GAUNTLET=<k> in the environment: tests/server_smoke.py)
    py mapgen/designs/gauntlet.py all [out_dir]           every gauntlet, each into out_dir/GauntNN/

Maps are named Gaunt01..Gaunt20 (OpenNox loads names up to 9 characters).
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO
from kit.layout import Land, square_px, square_tile
from kit.npcs import Population
from kit.mods import Mods, WEAPONS, MONSTERS
from kit.vegetation import Planter, FORESTS, TOWN_PLANTING
from kit.biome import Dresser

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- the twenty gauntlets -----------------------------------------------------------------------------------------
# setting: cave, ice, swamp, lava (kit/biome.py) or a forest (kit/vegetation FORESTS); layout: line, zigzag, hub, fork,
# ring; feature: the new monster met most; boss: the last arena's monsters; arms: the weapons laid forged a tier up.
THEMES = [
    dict(title="The Ogre Road", setting="forest", forest="pine", layout="line", arenas=3, feature="M5", boss=["M1"], arms=["W1", "W3"]),
    dict(title="Crab Grotto", setting="cave", layout="zigzag", arenas=3, feature="M2", boss=["M2", "M2"], arms=["W3", "W6"]),
    dict(title="The Bone Fen", setting="swamp", layout="hub", arenas=3, feature="M3", boss=["M3", "M5"], arms=["W1", "W5"]),
    dict(title="Ember Pit", setting="lava", layout="line", arenas=4, feature="M4", boss=["M4", "M4"], arms=["W6", "W1"]),
    dict(title="Frost Duel", setting="ice", layout="fork", arenas=4, feature="M5", boss=["M5", "M5", "M5"], arms=["W5", "W6"]),
    dict(title="Warlord's Hollow", setting="cave", layout="ring", arenas=4, feature="M1", boss=["M1", "M1"], arms=["W3", "W1"]),
    dict(title="The Rotting Mire", setting="swamp", layout="zigzag", arenas=4, feature="M2", boss=["M2", "M3"], arms=["W2", "W5"]),
    dict(title="Ashen Halls", setting="lava", layout="hub", arenas=3, feature="M3", boss=["M3", "M4"], arms=["W5", "W3"]),
    dict(title="Oak Trial", setting="forest", forest="oak", layout="fork", arenas=4, feature="M4", boss=["M1", "M5"], arms=["W2", "W1"]),
    dict(title="Glacier Run", setting="ice", layout="line", arenas=5, feature="M2", boss=["M2", "M1"], arms=["W1", "W6"]),
    dict(title="Spider Deep", setting="cave", layout="hub", arenas=4, feature="M3", boss=["M3", "M3"], arms=["W2", "W3"]),
    dict(title="Dusk Wood", setting="forest", forest="dusk", layout="ring", arenas=4, feature="M3", boss=["M3", "M5"], arms=["W5", "W6"]),
    dict(title="Cinder Fork", setting="lava", layout="fork", arenas=4, feature="M5", boss=["M1", "M4"], arms=["W3", "W5"]),
    dict(title="Leech Water", setting="swamp", layout="line", arenas=3, feature="M4", boss=["M4", "M2"], arms=["W6", "W2"]),
    dict(title="Whiteout", setting="ice", layout="zigzag", arenas=4, feature="M1", boss=["M1", "M3"], arms=["W1", "W2"]),
    dict(title="The Gauntlet of Five", setting="cave", layout="line", arenas=5, feature="M5", boss=["M1", "M2", "M3", "M4", "M5"], arms=["W1", "W3", "W5"]),
    dict(title="Ancient Grove", setting="forest", forest="ancient", layout="hub", arenas=4, feature="M2", boss=["M2", "M2", "M5"], arms=["W3", "W2"]),
    dict(title="Brimstone Ring", setting="lava", layout="ring", arenas=5, feature="M1", boss=["M1", "M4"], arms=["W6", "W5"]),
    dict(title="Frozen Crypts", setting="ice", layout="hub", arenas=3, feature="M3", boss=["M3", "M3", "M1"], arms=["W5", "W1"]),
    dict(title="Witchwater", setting="swamp", layout="ring", arenas=5, feature="M5", boss=["M5", "M4", "M3"], arms=["W2", "W6"]),
]

# The settings' own creatures, by rough cost (a warrior of the early chapters: a bat 1, a troll 4, a golem 8). Placed
# unnamed and on guard: a named Skeleton on idle stops the server reading the map (2026-10-09, tests/server_smoke.py).
ROSTERS = {
    "cave": {"Bat": 1, "SmallSpider": 1, "Urchin": 1, "Spider": 2, "SpittingSpider": 2, "GiantLeech": 2,
             "UrchinShaman": 2, "Scorpion": 3, "BlackWidow": 4, "Troll": 4, "StoneGolem": 8},
    "ice": {"WhiteWolf": 2, "BlackWolf": 2, "Ghost": 2, "Skeleton": 2, "Bear": 3, "SkeletonLord": 4, "Troll": 4},
    "swamp": {"Bat": 1, "Wasp": 1, "GiantLeech": 2, "CarnivorousPlant": 2, "Ghost": 2, "WillOWisp": 3, "Shade": 3,
              "OgreBrute": 4},
    "lava": {"Imp": 1, "FireSprite": 2, "Skeleton": 2, "EmberDemon": 4, "MeleeDemon": 4, "SkeletonLord": 4,
             "Horrendous": 8},
    "forest": {"Wasp": 1, "Urchin": 1, "GruntAxe": 2, "Archer": 2, "Swordsman": 3, "Bear": 3, "BlackBear": 4,
               "OgreBrute": 4, "Troll": 4},
}
COST = {"easy": 3, "medium": 5, "hard": 7, "boss": 10}
FLOOR_OF_FOREST = "GrassNorm"

# Layouts: node positions as fractions of the play box (0..1 across, 0..1 down the screen) and the passages between
# them. "S" is the start, "B" the boss, A1.. the arenas in order.
def layout(kind, n, rng):
    j = lambda: rng.uniform(-0.06, 0.06)
    if kind == "line":
        # a long line packs its arenas into each other: four or more snake gently up and down
        xs = [0.06 + 0.88 * i / (n + 1) for i in range(n + 2)]
        amp = 0.0 if n < 4 else 0.24
        pts = [(x + j() * 0.3, 0.5 + (amp if i % 2 else -amp) * (0 < i < n + 1) + j()) for i, x in enumerate(xs)]
        nodes = ["S"] + [f"A{i + 1}" for i in range(n)] + ["B"]
        return dict(zip(nodes, pts)), list(zip(nodes, nodes[1:]))
    if kind == "zigzag":
        xs = [0.1 + 0.8 * i / (n + 1) for i in range(n + 2)]
        pts = [(x + j() * 0.3, (0.25 if i % 2 else 0.75) + j()) for i, x in enumerate(xs)]
        nodes = ["S"] + [f"A{i + 1}" for i in range(n)] + ["B"]
        return dict(zip(nodes, pts)), list(zip(nodes, nodes[1:]))
    if kind == "hub":
        # the start at the west, A1 the hub in the middle, the other arenas round it, the boss beyond the last
        P = {"S": (0.1, 0.5 + j()), "A1": (0.45 + j(), 0.5 + j())}
        ring = [(0.45, 0.1), (0.74, 0.14), (0.74, 0.86), (0.45, 0.9)]
        for i in range(2, n + 1):
            P[f"A{i}"] = (ring[i - 2][0] + j(), ring[i - 2][1] + j())
        P["B"] = (0.96, 0.5 + j())
        E = [("S", "A1")] + [("A1", f"A{i}") for i in range(2, n + 1)] + [(f"A{n}", "B")]
        return P, E
    if kind == "fork":
        # two ways round from A1 that meet before the boss
        half = (n - 2) // 2 + 1
        P = {"S": (0.08, 0.5 + j()), "A1": (0.3 + j(), 0.5 + j())}
        E = [("S", "A1")]
        names = [f"A{i}" for i in range(2, n)]
        top, bot = names[:half], names[half:]
        for row, y in ((top, 0.2), (bot, 0.8)):
            prev = "A1"
            for k_, nm in enumerate(row):
                P[nm] = (0.45 + 0.25 * k_ / max(1, len(row)) + j(), y + j())
                E.append((prev, nm)); prev = nm
            E.append((prev, f"A{n}"))
        P[f"A{n}"] = (0.72 + j(), 0.5 + j())
        P["B"] = (0.92, 0.5 + j())
        E.append((f"A{n}", "B"))
        return P, E
    # ring: the arenas round a loop back to A1, the boss off the far side
    P = {"S": (0.08, 0.5 + j())}
    for i in range(n):
        a = math.pi + 2 * math.pi * i / n
        P[f"A{i + 1}"] = (0.47 + 0.27 * math.cos(a) + j(), 0.5 + 0.36 * math.sin(a) + j())
    E = [("S", "A1")] + [(f"A{i + 1}", f"A{(i + 1) % n + 1}") for i in range(n)]
    far = max(range(1, n + 1), key=lambda i: P[f"A{i}"][0])
    P["B"] = (0.97, P[f"A{far}"][1])
    E.append((f"A{far}", "B"))
    return P, E


def uv(X, Y):
    return (X + Y, X - Y)


def build(k, out_dir=None):
    T = THEMES[k - 1]
    gid, name = f"GT-{k:02d}", f"Gaunt{k:02d}"
    rng = random.Random(9000 + k)
    setting = T["setting"]
    m = Spec(name, summary=f"{gid} {T['title']}", description=f"[env:{'forest' if setting == 'forest' else setting}] "
             f"Gauntlet {gid}, {T['title']}: an armoury, {T['arenas']} arenas and a boss, to test the new weapons and "
             f"monsters. Generated by Claude.", author="vdystopia (generated by Claude)", version="0.1", date="2026",
             type=SOLO, minPlayers=1, maxPlayers=1)
    m.d["nxz"] = False
    m.loot = False
    TEXT = {}

    def text(key, s):
        kk = f"{name}:{key}"
        assert len(kk) <= 31, kk
        TEXT[kk] = s
        return kk

    # ---- the land: the start, the arenas and the boss's, joined by passages -----------------------------------
    n = T["arenas"]
    P, E = layout(T["layout"], n, rng)
    X0, X1, Y0, Y1 = 36, 220, 46, 210                     # the play box, map squares on screen: a small map
    land = Land(rng, u_range=(60, 452), v_range=(-200, 200))
    R = {}
    for nm, (fx, fy) in P.items():
        X, Y = X0 + fx * (X1 - X0), Y0 + fy * (Y1 - Y0)
        r = 18 if nm == "S" else 26 if nm == "B" else rng.uniform(19, 23)
        R[nm] = r
        land.area(nm, uv(X, Y), r, stretch=rng.uniform(1.0, 1.3), angle=rng.uniform(0, 3.1), roughness=0.2)
    for a, b in E:
        land.link(a, b, rng.choice((7, 8, 9)), bend=0.3, road=False, pockets=(0, 0))
    land.carve(margin=2.5)
    land.assign_regions()
    if setting == "forest":
        fw = FORESTS[T["forest"]]["wall"]
        land.apply(m, wall=fw, floor=FLOOR_OF_FOREST)
        m.d["ambient"] = [150, 146, 120]
        d = None
    else:
        d = Dresser(m, rng, land, setting)
        land.apply(m, wall=d.wall, floor=d.base)

    centre = {nm: land.areas[nm]["c"] for nm in P}                # squares
    inside = lambda nm, s, f=1.0: land._in_area((s[0] + 0.5, s[1] - 0.5), dict(land.areas[nm], r=land.areas[nm]["r"] * f))
    edge = land.edge_distance()
    keep = set()                                                  # open floor: the armoury and the arenas' middles
    for nm in P:
        keep |= {s for s in land.squares if inside(nm, s, 0.75 if nm != "S" else 0.95)}
    land.taken |= keep

    # ---- the setting: ground, plants, rocks, lights ---------------------------------------------------------------
    if d:
        d.ground()
        d.vegetate(keep_clear=keep, groves=1)
        d.scatter_open(0.6)
        d.rim()
        d.lights()
    else:
        land.ground_variety(m, clear=2)
        Planter(m, rng, land, T["forest"], keep_clear=keep).plant_all(groves=1, profile=TOWN_PLANTING)

    pop = Population(m, rng)
    mods = Mods(m, pop)

    def spot(nm, f=0.7, gap=1.6, used=None, wall=2):
        """A square in area nm's inner part, at least `wall` from the edge, `gap` from the others used."""
        used = used if used is not None else []
        cand = [s for s in land.squares if inside(nm, s, f) and edge.get(s, 0) >= wall
                and all(math.hypot(s[0] - a, s[1] - b) >= gap for a, b in used)]
        if not cand: cand = [s for s in land.squares if inside(nm, s, 1.0)]
        s = rng.choice(cand)
        used.append(s)
        return s

    sx, sy = centre["S"]
    first = min((b for a, b in E if a == "S"), key=lambda b: 0)
    fx_, fy_ = centre[first]
    L_ = math.hypot(fx_ - sx, fy_ - sy) or 1
    ux, uy = (fx_ - sx) / L_, (fy_ - sy) / L_                     # toward the first arena
    tx, ty = -uy, ux
    at = lambda a, b: square_px(sx + ux * a + tx * b, sy + uy * a + ty * b)

    # ---- the armoury ------------------------------------------------------------------------------------------
    m.obj_px("PlayerStart", *at(-4.5, 0))
    arms = T["arms"]
    intro = (f"{gid} {T['title'].upper()}\nGear up here. On the floor: the six power weapons (W1-W6), a sign by each; "
             f"{' and '.join(WEAPONS[w]['name'] for w in arms)} lie forged a tier up beside them. Chests: warrior's kit, "
             f"caster's kit, supplies. Then fight through {n} arenas ({gid}-A1 to A{n}) to the boss ({gid}-B: "
             f"{', '.join(MONSTERS[b]['name'][4:] for b in T['boss'])}).")
    m.obj_px("Sign1", *at(-3.0, 2.2), xfer={"Text": text("Intro", intro)})
    for i, wid in enumerate(WEAPONS):                              # the row of power weapons, a sign by each
        b = -6.25 + 2.5 * i
        mods.weapon(wid, *at(-1.0, b))
        m.obj_px("Sign2" if i % 2 else "Sign1", *at(-2.0, b), xfer={"Text": text(wid, WEAPONS[wid]["text"])})
    for i, wid in enumerate(arms):                                # the featured weapons, forged a tier or two up
        tier = 2 if i == 0 else 1
        if len(WEAPONS[wid]["tiers"]) > 1:
            mods.weapon(wid, *at(0.6, -2.0 + 2.5 * i), tier=tier)
        else:
            mods.weapon(wid, *at(0.6, -2.0 + 2.5 * i))
    racks = ["TraderArmorRack1", "TraderArmorRack2", "TraderBowRack1", "TraderQuiverRack"]
    for i, rk in enumerate(racks):                                # racks along the armoury's back
        m.obj_px(rk, *at(-6.5, -4.5 + 3.0 * i))
    warrior = ["OrnateHelm", "Breastplate", "PlateLeggings", "PlateArms", "PlateBoots", "SteelShield", "BattleAxe",
               "Longsword"]
    caster = ["WizardRobe", "WizardHelm", "ConjurerHelm", "LeatherBoots", "ForceWand", "LesserFireballWand",
              "MedievalCloak"]
    supplies = [("RedPotion", None, 6), ("BluePotion", None, 4), "CurePoisonPotion", "Bow", ("Quiver", None, 2)]
    for i, (kind, items) in enumerate((("Warrior", warrior), ("Caster", caster), ("Supplies", supplies))):
        m.obj_px("Chest4" if i != 1 else "Chest3", *at(-5.0, -5.0 + 5.0 * i), items=items)

    # ---- the arenas ---------------------------------------------------------------------------------------------
    order = [f"A{i + 1}" for i in range(n)]
    budget = lambda i: 5 + 3 * i                                   # the setting's creatures, by cost, arena by arena
    roster = ROSTERS[setting]
    names = list(roster)
    plan = {}
    feat, others = T["feature"], [mm for mm in MONSTERS if mm != T["feature"]]
    rng.shuffle(others)
    for i, nm in enumerate(order):
        ms = []
        if i % 2 == 1 or i == n - 1: ms.append(feat)              # the featured monster in every other arena
        if i == n // 2: ms.append(others[0])                      # and one other new monster mid-way
        if i >= 3 and rng.random() < 0.5: ms.append(others[1])
        plan[nm] = ms
    plan["B"] = list(T["boss"])
    met = []
    for i, nm in enumerate(order + ["B"]):
        used = []
        mons = plan[nm]
        for mid in mons:
            s = spot(nm, 0.55, 3.0, used)
            mods.monster(mid, *square_px(s[0] + 0.5, s[1] - 0.5), wait=260.0, respawn=0.0,
                         face=square_px(*centre["S"]))
            met.append(mid)
        stock, cost = [], 0
        b = budget(i) if nm != "B" else 6
        cheap = [t for t in names if roster[t] <= max(2, 2 + i)]
        while cost < b:
            t = rng.choice(cheap if rng.random() < 0.6 else names)
            if roster[t] > b - cost + 1: t = min(names, key=lambda q: roster[q])
            c = roster[t]
            # a few together: the cheap ones in twos and threes
            g = rng.choice((1, 2, 3)) if c <= 1 else rng.choice((1, 1, 2)) if c <= 2 else 1
            s0 = spot(nm, 0.75, 2.2, used)
            for q in range(g):
                x, y = square_px(s0[0] + 0.5 + rng.uniform(-0.9, 0.9) * (q > 0), s0[1] - 0.5 + rng.uniform(-0.9, 0.9) * (q > 0))
                pop.creature(t, x, y, action="guard", aggr=0.83)
                stock.append(t)
                cost += c
        label = f"{gid}-{nm}" if nm != "B" else f"{gid}-B"
        new = ", ".join(MONSTERS[mm]["name"][4:] for mm in mons) or "none"
        seen = sorted(set(stock), key=stock.index)
        msg = (f"{label} {'BOSS ARENA' if nm == 'B' else 'ARENA ' + nm[1:]}\nNew monsters: {new}. Also: "
               f"{', '.join(seen) if seen else 'nothing else'}.")
        # the sign where the passage from the way you came enters the arena
        prev = next((a for a, b2 in E if b2 == nm), "S")
        px_, py_ = centre[prev]
        cx, cy = centre[nm]
        Lp = math.hypot(cx - px_, cy - py_) or 1
        rr = land.areas[nm]["r"]
        sgn = (cx - (cx - px_) / Lp * (rr * 0.8), cy - (cy - py_) / Lp * (rr * 0.8))
        m.obj_px("Sign1", *square_px(*sgn), xfer={"Text": text(nm, msg)})
        if nm != "B":                                              # red potions at the far side
            fx2, fy2 = cx + (cx - px_) / Lp * rr * 0.6, cy + (cy - py_) / Lp * rr * 0.6
            for q in range(2):
                m.obj_px("RedPotion", *square_px(fx2 + 0.8 * q, fy2 - 0.4 * q))
        plan[nm] = (mons, seen)
    bx, by = centre["B"]
    m.obj_px("Chest4", *square_px(bx + 3, by - 3), items=[("Gold", {"Amount": 500}), "RedPotion", "BluePotion"])
    m.obj_px("Sign2", *square_px(bx + 2, by - 4.5),
             xfer={"Text": text("End", f"{gid} {T['title'].upper()} - THE END\nIf the boss is down, the gauntlet is "
                                       f"won. Rate it as {gid}; each arena by its sign ({gid}-A1 ... {gid}-B).")})
    mods.attach(pop.behaviours)
    m.scripts.update(pop.behaviours.files(name))

    info = dict(id=gid, name=name, title=T["title"], setting=setting + (f" ({T['forest']})" if setting == "forest" else ""),
                layout=T["layout"], arenas=n, featured_monster=T["feature"], boss=T["boss"], forged_weapons=arms,
                new_monsters_met=sorted(set(met)), plan={k_: dict(new=v[0], stock=v[1]) for k_, v in plan.items()},
                centres={k_: list(square_px(*v)) for k_, v in centre.items()})
    if out_dir and out_dir != "-":
        lines = m.build(out_dir)
        with open(os.path.join(out_dir, f"{name}.strings.json"), "w", encoding="utf-8") as f:
            json.dump(TEXT, f, ensure_ascii=False, indent=1)
        with open(os.path.join(out_dir, f"{name}.gauntlet.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, indent=1)
        print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS"))))
    print(f"{gid} {name} {T['title']}: {setting} {T['layout']} {n} arenas | creatures {len(pop.placed)} | "
          f"new monsters {', '.join(sorted(set(met)))} | signs {len(TEXT)}")
    return m, info


if __name__ != "smoke" or os.environ.get("GAUNTLET"):
    arg = sys.argv[1] if len(sys.argv) > 1 and __name__ == "__main__" else os.environ.get("GAUNTLET", "1")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "out", "gauntlets")
    if arg == "all":
        for k_ in range(1, len(THEMES) + 1):
            build(k_, os.path.join(out, f"Gaunt{k_:02d}"))
    else:
        m, info = build(int(arg), None if __name__ == "smoke" else os.path.join(out, f"Gaunt{int(arg):02d}"))
