"""TrapGaunt: ten trap gauntlets, TG-01 to TG-10, each a chain of trap stations the player crosses one after another
(kit/trapkit patterns of every kind, rules/TRAPS.md), from a short run of five to a long descent of fourteen.

Every gauntlet:
- starts in a hall with its sign (the gauntlet's name, how many stages, whether monsters wait), potions and a chest
  of gear for any class;
- then its stages, each a walled run of one trap pattern (signed TG-NN-Sk at its mouth: the trap's name and tier),
  joined by small rooms where the route turns; every second room is a rest (potions; every fourth a healing well);
- teaches before it tests: the first third of a gauntlet draws standard patterns, the last third hard ones, and a
  kind appears plain before it appears hard;
- seven of the ten have monsters (the user: about 70% with rising monsters, 30% pure traps): none in the first
  stages, then creatures in the turning rooms (a fight between traps) and waiting at the far ends of stations (a
  fight on a trap's edge), more stage by stage; the last room holds the strongest;
- a fall into a pit drops the player back into the room before the stage (rules/TRAPS.md T5);
- ends in a room with a reward chest and the closing sign.

    py mapgen/designs/trapgaunt.py <1-10> [out_dir|-]
    py mapgen/designs/trapgaunt.py all [out_dir]

Maps are named TrapGnt01..TrapGnt10 (9 characters).
"""
import json, math, os, random, sys, zlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO
from kit.dungeon import Dungeon, LIGHTS, glow
from kit.traps import Traps
from kit.trapkit import Station, PATTERNS, TITLES, tier_of
from kit.signs import wrap

HERE = os.path.dirname(os.path.abspath(__file__))
# setting: walls, floor, room floor; the kinds a setting favours (drawn first when the gauntlet has room for them)
SETTINGS = {
    "crypt": ("DungeonStone", "GreenBrick", "CryptFloor", ["spike", "blade", "pit", "spell", "block"]),
    "forge": ("GalavaTownWall", "LOTDPitted", "GalavaBrick2", ["flame", "block", "push", "spell", "spike"]),
    "temple": ("IxTempleWall", "IxBrickFancy", "AncientRuin", ["arrow", "spike", "pit", "trigger", "sentry"]),
    "lotd": ("LOTDBrick", "LOTDPitted", "LOTDBlackMarble", ["sentry", "spell", "blade", "arrow", "trigger"]),
    "mine": ("CaveWall", "CaveHardBrown", "CaveHardTan", ["pit", "push", "block", "blade", "flame"]),
    "castle": ("BrickBlue", "TileDark", "DungeonStoneDark", ["arrow", "trigger", "block", "sentry", "spell"]),
}
# creatures by setting, with a rough cost (an early-chapter warrior: a bat 1, a troll 4, a golem 8)
ROSTERS = {
    "crypt": {"Bat": 1, "Zombie": 2, "Skeleton": 2, "Ghost": 2, "SkeletonLord": 4, "VileZombie": 4},
    "forge": {"Imp": 1, "FireSprite": 2, "Skeleton": 2, "EmberDemon": 4, "MeleeDemon": 4},
    "temple": {"Urchin": 1, "Spider": 2, "SpittingSpider": 2, "Scorpion": 3, "BlackWidow": 4},
    "lotd": {"Bat": 1, "Skeleton": 2, "Ghost": 2, "SkeletonLord": 4, "Shade": 3},
    "mine": {"Bat": 1, "SmallSpider": 1, "Spider": 2, "GiantLeech": 2, "Troll": 4, "StoneGolem": 8},
    "castle": {"GruntAxe": 2, "Archer": 2, "Swordsman": 3, "OgreBrute": 4, "Troll": 4},
}
THEMES = [
    dict(title="The Drowned Stair", setting="crypt", stages=5, monsters=False, hard=0.2),
    dict(title="Ember Run", setting="forge", stages=7, monsters=True, hard=0.35),
    dict(title="The Hall of Lanes", setting="temple", stages=8, monsters=True, hard=0.35),
    dict(title="Bone Mill", setting="crypt", stages=6, monsters=False, hard=0.6),
    dict(title="Sentinel's Way", setting="lotd", stages=9, monsters=True, hard=0.45),
    dict(title="The Grinding Deep", setting="mine", stages=8, monsters=True, hard=0.45),
    dict(title="Gallery of Snares", setting="castle", stages=7, monsters=True, hard=0.4),
    dict(title="The Long Descent", setting="mine", stages=14, monsters=True, hard=0.5),
    dict(title="Clockwork Gate", setting="castle", stages=10, monsters=False, hard=0.6),
    dict(title="The Gauntlet of All", setting="lotd", stages=12, monsters=True, hard=0.55),
]
ROOM = 10                                # squares a side of a turning room
DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]


def in_bounds(sq, margin=6):
    return all(margin <= i + j <= 254 - margin and margin <= i - j <= 254 - margin for i, j in sq)


def pick_patterns(T_, rng):
    """The stages' patterns: the setting's kinds first, standard ones early and hard ones late, no pattern twice,
    a kind's hard pattern only after one of its standard ones."""
    fav = SETTINGS[T_["setting"]][3]
    kinds = [k for k in fav if k in PATTERNS] + [k for k in PATTERNS if k not in fav]
    pool = [(k, i, p) for k in kinds for i, p in enumerate(PATTERNS[k])]
    n = T_["stages"]
    n_hard = max(1, int(round(n * T_["hard"])))
    tiers = ["standard"] * (n - n_hard) + ["hard"] * n_hard
    seen_std, used, out = set(), set(), []
    for s, tier in enumerate(tiers):
        def ok(c):
            k, i, p = c
            meta_tier = tier_of(p)
            return (k, i) not in used and meta_tier == tier and (tier == "standard" or k in seen_std) and \
                (s < n - 1 or p.size[0] >= 30 or tier == "standard" or True)
        cand = [c for c in pool if ok(c)]
        if not cand:
            cand = [c for c in pool if (c[0], c[1]) not in used]
        # favour the setting's kinds and not the same kind twice in a row
        weights = []
        for k, i, p in cand:
            w = 3.0 if k in fav else 1.0
            if out and out[-1][0] == k: w *= 0.2
            if p.size[0] > 30 and s < n - 2: w *= 0.3          # the long combined runs near the end
            weights.append(w)
        k, i, p = rng.choices(cand, weights)[0]
        used.add((k, i))
        if tier == "standard": seen_std.add(k)
        out.append((k, i, p))
    return out


def layout(stations, rng, start=(60, -40)):
    """Place the stations end to end with a turning room between each pair: a route that winds across the map
    without crossing itself. Returns [(kind, axis, sign, i0, j0)] for each piece or None."""
    taken = set()

    def box_sq(i0, j0, L, W, axis, sign):
        if axis == "i":
            ii = range(i0, i0 + L) if sign > 0 else range(i0 - L, i0)
            return {(i, j) for i in ii for j in range(j0, j0 + W)}
        jj = range(j0, j0 + L) if sign > 0 else range(j0 - L, j0)
        return {(i, j) for i in range(i0, i0 + W) for j in jj}

    def room_sq(ci, cj):
        return {(i, j) for i in range(ci - ROOM // 2, ci + ROOM // 2) for j in range(cj - ROOM // 2, cj + ROOM // 2)}

    def grow(sq, m=2):
        return {(i + a, j + b) for i, j in sq for a in range(-m, m + 1) for b in range(-m, m + 1)}
    pieces = []
    ci, cj = start
    first = room_sq(ci, cj)
    taken |= first
    pieces.append(("room", ci, cj))
    d = (1, 0)
    for k, (L, W) in enumerate(stations):
        opts = [dd for dd in DIRS if dd != (-d[0], -d[1])]
        rng.shuffle(opts)
        opts.sort(key=lambda dd: 0 if dd != d else 1)               # prefer to turn (a winding route)
        placed = False
        for dd in opts:
            ei, ej = ci + dd[0] * ROOM // 2, cj + dd[1] * ROOM // 2  # the room's side the station leaves from
            axis = "i" if dd[0] else "j"
            sign = dd[0] or dd[1]
            if axis == "i":
                i0, j0 = ei, ej - W // 2
            else:
                i0, j0 = ei - W // 2, ej
            sq = box_sq(i0, j0, L, W, axis, sign)
            ni, nj = ci + dd[0] * (ROOM + L), cj + dd[1] * (ROOM + L)   # the next room's centre
            rq = room_sq(ni, nj)
            if not in_bounds(sq | rq): continue
            if (sq | rq) & grow(taken - room_sq(ci, cj), 2): continue
            if rq & grow(taken, 2): continue
            taken |= sq | rq
            pieces.append(("station", axis, sign, i0, j0, L, W))
            pieces.append(("room", ni, nj))
            ci, cj, d = ni, nj, dd
            placed = True
            break
        if not placed:
            return None
    return pieces


def build(k, out_dir=None):
    T_ = THEMES[k - 1]
    gid, name = f"TG-{k:02d}", f"TrapGnt{k:02d}"
    rng = random.Random(zlib.crc32(name.encode()))
    wall, floor, rfloor, _ = SETTINGS[T_["setting"]]
    pats = pick_patterns(T_, rng)
    pieces = None
    for attempt in range(80):
        pieces = layout([p.size for _, _, p in pats], random.Random(attempt * 7919 + k))
        if pieces: break
    assert pieces, f"{name}: no layout fits"
    m = Spec(name, summary=f"{gid} {T_['title']}",
             description=f"[env:castle] Trap gauntlet {gid}, {T_['title']}: {T_['stages']} trap stages one after "
                         f"another{', with monsters' if T_['monsters'] else ', traps alone'}. Generated by Claude.",
             author="vdystopia (generated by Claude)", version="0.1", date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
    m.d["nxz"] = False
    m.d["ambient"] = [120, 115, 110]
    m.loot = False
    TEXT = {}

    def text(key, s):
        kk = f"{name}:{key}"
        assert len(kk) <= 31, kk
        TEXT[kk] = s
        return kk

    def sign(key, s, x, y, step=(14, 14)):
        for q, part in enumerate(wrap(s)):
            m.obj_px("Sign1", x + step[0] * q, y + step[1] * q, xfer={"Text": text(key if not q else f"{key}_{q + 1}", part)})

    d = Dungeon(m, rng, wall=wall, floor=floor)
    rooms, parts = [], []
    for q, pc in enumerate(pieces):
        if pc[0] == "room":
            _, ci, cj = pc
            rooms.append(d.box(f"room{len(rooms)}", ci - ROOM // 2, cj - ROOM // 2, ROOM, ROOM, floor=rfloor))
        else:
            _, axis, sgn, i0, j0, L, W = pc
            parts.append(d.box(f"st{len(parts)}", i0, j0, L, W, axis=axis, sign=sgn))
    d.apply()
    T = Traps(m, prefix="")
    from kit.npcs import Population
    pop = Population(m, rng)
    roster = ROSTERS[T_["setting"]]
    stations, n = [], len(parts)
    for s, ((kind, idx, p), part) in enumerate(zip(pats, parts)):
        label = f"{gid}-S{s + 1}"
        prev_room = rooms[s]
        st = Station(T, part, f"S{s + 1:02d}", rng, fall_to=prev_room.centre, spec=m)
        meta = p(st)
        tier = meta.get("tier", p.tier)
        for o in m.d["objects"]:                         # a fall drops the player back into the room before
            if o["type"] in ("Pit", "PitCrumblingFloor", "ForestPit") and "xfer" in o and o.get("scr", "").startswith(st.label):
                o["xfer"].update(FallX=int(prev_room.centre[0]), FallY=int(prev_room.centre[1]))
        mx, my = part.at(0.4, 0.6)
        sign(f"S{s + 1}", f"{label} {p.title.upper()} ({tier}). {meta.get('tells', '')}", mx, my)
        # an unseen light down the passage every 6 squares (no torches indoors, nothing in a trap's lane)
        for a in range(3, part.length - 2, 6):
            glow(m, *part.at(a, part.width / 2))
        T.label(label, p.title, [*part.at(0, 0), *part.at(part.length, part.width)], kind, tier, notes=json.dumps(meta))
        stations.append(dict(label=label, title=p.title, kind=kind, pattern=idx + 1, tier=tier, meta=meta,
                             L=part.length, W=part.width, start=list(part.at(0.5, part.width / 2)),
                             end=list(part.at(part.length, part.width / 2)), along=list(part.direction()),
                             across=list(part.across()), clocks=st.starts, rest=st.rest))
        # monsters, rising: none in the first third, then in the turning room after the stage and at its far end
        if T_["monsters"] and s >= max(1, n // 3):
            level = (s - n // 3 + 1) / max(1, n - n // 3)
            budget = 3 + int(round(9 * level))
            room = rooms[s + 1]
            names = sorted(roster, key=lambda t: roster[t])
            cost = 0
            while cost < budget:
                t = rng.choice([x for x in names if roster[x] <= max(2, budget - cost)] or names[:1])
                a_, b_ = rng.uniform(2, ROOM - 2), rng.uniform(2, ROOM - 2)
                pop.creature(t, *room.at(a_, b_), action="guard", aggr=0.83)
                cost += roster[t]
            if level > 0.5 and rng.random() < 0.7:          # one waiting at the far end of the stage
                t = max((x for x in names if roster[x] <= 4), key=lambda x: roster[x])
                pop.creature(t, *part.at(part.length - 1.2, part.width / 2), action="guard", aggr=0.83)
    # the rooms: start, rests, end
    start, end = rooms[0], rooms[-1]
    m.obj_px("PlayerStart", *start.at(3, ROOM / 2))
    intro = (f"{gid} {T_['title'].upper()}: {n} trap stages one after another"
             f"{', and monsters from the middle on' if T_['monsters'] else ', traps alone'}. Rest in the rooms "
             f"between. Rate each stage by its sign ({gid}-S1 ...).")
    sign("Intro", intro, *start.at(1.5, 1.5))
    m.obj_px("Chest4", *start.at(2, ROOM - 2), items=["RedPotion"] * 4 + ["BluePotion"] * 2 + ["CurePoisonPotion"])
    m.obj_px("Chest3", *start.at(5, ROOM - 2), items=["Longsword", "SteelShield", "LeatherBoots", "ForceWand",
                                                     "LesserFireballWand", "WizardRobe", "Bow", ("Quiver", None, 2)])
    for q, room in enumerate(rooms[1:-1], 1):
        if q % 2 == 0 or q == len(rooms) - 2:
            for z in range(2):
                m.obj_px("RedPotion", *room.at(1.5 + 0.7 * z, 1.5))
        if q % 4 == 0:
            m.obj_px("WishingWell", *room.at(ROOM / 2, ROOM - 2))
        for c in (0.8, ROOM - 0.8):                    # a light in two opposite corners, clear of the mouths
            m.obj_px(LIGHTS[T_["setting"]], *room.at(c, c))
    m.obj_px("Chest4", *end.at(ROOM / 2, ROOM - 2), items=[("Gold", {"Amount": 300 + 60 * n}), "RedPotion", "BluePotion"])
    sign("End", f"{gid} {T_['title'].upper()} - THE END. The gauntlet is run. Rate it as {gid}, each stage by its sign.",
         *end.at(ROOM / 2 - 1, ROOM / 2))
    T.attach()
    m.scripts.update(pop.behaviours.files(name))
    info = dict(name=name, id=gid, title=T_["title"], setting=T_["setting"], monsters=T_["monsters"],
                stations=stations, hub_start=list(start.at(3, ROOM / 2)), walls=sorted(m.wallmap),
                secret={f"{x},{y}": w["secret"] for (x, y), w in m.wallmap.items() if w.get("secret")},
                creatures=len(pop.placed))
    if out_dir and out_dir != "-":
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"{name}.strings.json"), "w", encoding="utf-8") as f:
            json.dump(TEXT, f, ensure_ascii=False, indent=1)
        lines = m.build(out_dir)
        T.write(out_dir)
        with open(os.path.join(out_dir, f"{name}.lab.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, indent=1)
        print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS"))))
    print(f"{gid} {name} {T_['title']}: {n} stages ({', '.join(f'{k}{i + 1}' for k, i, _ in pats)}), "
          f"creatures {len(pop.placed)}")
    return m, info


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "1"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "out", "trapgaunt")
    ks = range(1, len(THEMES) + 1) if arg == "all" else [int(arg)]
    for k_ in ks:
        build(k_, None if out == "-" else os.path.join(out, f"TrapGnt{k_:02d}"))
