"""Outdoor places with a purpose, laid out as one composed scene round a centre (square coordinates), each returning
the spots its people stand on so the design can put them there.

- bandit_camp: tents in an arc behind a stone-ringed fire, each bedroll before its tent, the leader's awning in the
  middle with the take before it, the store (cart, crates, barrels, sacks) on one flank, the racks on the other, a
  lookout post toward the way in (Westwood's camps on Con03A, Con04a, War05A).
- wagon_wreck: a trader's cart stopped on the road and plundered, a wheel off, its load thrown out in a fan, the
  carter's place beside it.
- wolf_den: a heap of rock with bones strewn before it, where a pack lies up.
- cache: a chest (or a hollow stump) hidden at the forest's edge, marked by a little heap of stones.
- signpost: a plank sign whose text is a key of the map's string table (kit/quests.QuestBook.text).

Every piece goes only on the land, off squares already taken, and marks its square taken.
"""
import math, random, zlib
from kit.layout import square_px
from kit import loot
from kit import scenes as S

CRATES = ("Crate1", "Crate2", "DarkCrate1", "DarkCrate2")
BARRELS = ("Barrel", "Barrel2")
SACKS = ("SackChestLarge1", "SackChestLarge2", "SackChestMedium1", "SackChestMedium2")
BONES = ("ArmBone", "LegBone", "Skull", "ArmBone", "LegBone")
# a cot's variant by the screen direction its foot points (toward the fire): Cot1-4 lie along the four wall lines
COT_BY_ANGLE = ("Cot1", "Cot2", "Cot3", "Cot4")


class Scene:
    def __init__(self, spec, rng, land, centre):
        self.spec, self.rng, self.land = spec, rng, land
        self.ci, self.cj = centre
        self.placed = []

    def ok(self, si, sj, pad=0.0):
        s = (int(math.floor(si)), int(math.floor(sj)) + 1)
        L = self.land
        if s not in L.squares or s in L.roads or s in L.water or s in L.taken_strict: return False
        x, y = square_px(si, sj)                    # never in or against a wall (the forest's or a fence's)
        cx, cy = int(x // 23), int(y // 23)
        return not any((cx + a, cy + b) in self.spec.wallmap for a in (-1, 0, 1) for b in (-1, 0, 1))

    def put(self, t, si, sj, **extra):
        if not self.ok(si, sj): return None
        o = self.spec.obj_px(t, *square_px(si, sj), **extra)
        loot.tag(self.spec, [o], "camp")      # a camp's goods hold a camp's loot (kit/loot.py)
        self.placed.append((si, sj))
        self.land.taken.add((int(math.floor(si)), int(math.floor(sj)) + 1))
        return o

    def at(self, r, a):
        return self.ci + r * math.cos(a), self.cj + r * math.sin(a)

    def px(self, r, a):
        return square_px(*self.at(r, a))


def _sq(x, y):
    """Continuous square coordinates of a world px point (the inverse of square_px)."""
    return ((x + y) / 23.0 - 1) / 2, ((x - y) / 23.0 - 1) / 2


class Camp(Scene):
    """A scene laid in world px round a centre: polar placement in screen angles (0 = right, -pi/2 = up)."""
    def __init__(self, spec, rng, land, centre):
        super().__init__(spec, rng, land, centre)
        self.fx, self.fy = square_px(*centre)
        self.mine = []                                  # px of the pieces laid, for spacing

    def p(self, r, a):
        return self.fx + r * math.cos(a), self.fy + r * math.sin(a)

    def free(self, x, y, gap=0.0):
        return self.ok(*_sq(x, y)) and all(math.hypot(x - a, y - b) >= gap for a, b in self.mine)

    def put_px(self, t, x, y, gap=0.0, **extra):
        if not self.free(x, y, gap): return None
        o = self.put(t, *_sq(x, y), **extra)
        if o is not None: self.mine.append((x, y))
        return o


def own_rng(spec, kind, centre):
    """A scene's own generator (zlib.crc32 of the map's name, the scene and its place): a camp's variance draws
    nothing from the design's generator, so changing a camp never shifts the rest of the map."""
    return random.Random(zlib.crc32(f"{spec.d['name']}:{kind}:{centre[0]:.1f},{centre[1]:.1f}".encode()))


def _replay(rng, kind):
    """Draw from the design's generator what the first camps drew (2026-10-04), so the rest of a map built after a
    camp (its trees, its creatures) is laid as it was before the camps were recomposed."""
    if kind == "bandit_camp":
        for _ in range(5): rng.choice(("Stump3", "Stump4", "Stump5", "Stump6"))
        rng.random()
        for _ in range(rng.randint(7, 10)):
            rng.choice(CRATES + CRATES + BARRELS + SACKS); rng.uniform(0, 1.5); rng.uniform(0, 2 * math.pi)
        for _ in range(2): rng.choice(("OutdoorTraderArmorRack1", "OutdoorTraderArmorRack3", "OutdoorTraderArmorRack5"))
    elif kind == "wagon_wreck":
        for _ in range(rng.randint(5, 8)):
            rng.uniform(0.8, 2.4); rng.uniform(-1.0, 1.0); rng.choice(CRATES + BARRELS + SACKS)
        for _ in range(3):
            rng.choice(("ArmBone", "LegBone")); rng.uniform(1.5, 2.5); rng.uniform(-0.6, 0.6)


def _ang(a):
    return math.atan2(math.sin(a), math.cos(a))


def bandit_camp(spec, rng, land, centre, toward, loot, sleepers=4, tents=2):
    """A bandit camp in Westwood's manner (Con03A, Con04a, War05A: a fire ringed by small stones, seats 55-65 px out,
    pup tents 105-120 px out on the far side, the stores together on one side), composed round its fire and open
    toward `toward` (squares: where the way in comes from). 2026-10-05 playtest: "The bandit camp looks terrible. It's
    a scattered mess. Beds randomly strewn across an open clearing a few random crates placed haphazardly."

    - the tents stand in an arc behind the fire, all facing it, on the side away from the way in and toward the top
      of the screen where it can (a pup tent is drawn one way: it faces the camera); with three or more, the leader's
      awning (a trader's tent, stolen) takes the middle;
    - each bedroll lies in front of its tent, its head to the tent and its foot to the fire (two to a tent when the
      sleepers outnumber the tents); with no tents the bedrolls lie in an arc behind the fire;
    - the fire: stones ringed round it, stumps to sit on either side of it, the cooking pot to one side;
    - the store on one flank: the cart they took, crates side by side, barrels in a three, sacks;
    - the arms on the other flank: racks in a row, a polearm rack, a quiver;
    - a lookout post out toward the way in: a stump seat, a quiver rack, a few stones;
    - the take: the chest before the leader's tent, the stolen goods (sacks, an apple crate) beside it.
    Variance: the arc's width and the side the store takes, racks and seats by type and count, the leader's awning's
    colours. loot: the chest's items. Returns dict(fire, seats (round the fire), lookout, chest, goods, leader (before
    the leader's tent), posts (by the store and the racks)): world px."""
    _replay(rng, "bandit_camp")
    rng = own_rng(spec, "bandit_camp", centre)
    fx, fy = square_px(*centre)
    tx, ty = square_px(*toward)
    a_in = math.atan2(ty - fy, tx - fx)
    probe = Camp(spec, rng, land, centre)
    # the back of the camp: away from the way in, toward the top of the screen where it can, with room for the tents
    best = None
    for q in range(24):
        b = -math.pi + q * math.pi / 12
        off_in = abs(_ang(b - a_in))
        if off_in < math.pi * 0.55: continue
        room = sum(probe.free(*probe.p(r, b + d)) for r in (95, 130, 160, 190) for d in (-0.7, -0.35, 0, 0.35, 0.7))
        side = sum(probe.free(*probe.p(r, b + d)) for r in (120, 160) for d in (1.6, -1.6))
        score = room * 2 + side + 3 * math.cos(b + math.pi / 2) + 2 * off_in / math.pi
        if best is None or score > best[0]: best = (score, b)
    b = best[1] if best else a_in + math.pi
    # the clearing's size: shrink the camp until its core fits
    k = 1.0
    for k in (1.0, 0.9, 0.8, 0.7):
        core = [probe.p(r * k, b + d) for r, d in ((150, -0.6), (150, 0), (150, 0.6), (95, -0.5), (95, 0.5),
                                                    (165, math.pi / 2), (150, -math.pi / 2))]
        if sum(probe.free(x, y) for x, y in core) >= len(core) - 1: break
    sc = Camp(spec, rng, land, centre)
    sc.put_px("CampFire", fx, fy)
    ph = rng.uniform(0, 1)
    for q in range(7):                                             # stones ringed round the fire
        sc.put_px("CaveRocksSmall", *sc.p(22, ph + q * 2 * math.pi / 7))
    left = 1 if rng.random() < 0.5 else -1                          # the side the store takes
    # the arms take the side nearer the way in (they guard it); the store the far one
    if abs(_ang(b + left * math.pi / 2 - a_in)) < abs(_ang(b - left * math.pi / 2 - a_in)): left = -left

    # ---- the tents in an arc behind the fire, the bedrolls before them ------------------------------------------
    R_t = 150 * k
    n_t = max(0, tents)
    step = 2 * math.asin(min(1.0, 118 / (2 * R_t))) if n_t > 1 else 0
    t_angles = [b + (q - (n_t - 1) / 2) * step for q in range(n_t)]
    lead = n_t // 2 if n_t >= 3 else None
    leader = None
    beds = []                                                       # (angle, how many) bedrolls by each tent
    per = [sleepers // max(1, n_t) + (1 if q < sleepers % max(1, n_t) else 0) for q in range(n_t)]
    spare = 0
    for q, a in enumerate(t_angles):
        if q == lead:
            # the leader's awning, a little further back; its open side toward the camera, and so the fire
            x, y = sc.p(R_t + 40 * k, a)
            way = "DN" if math.cos(a) < 0 else "UP"
            parts = S.tent_pieces(way, rng.choice(S.TENT_COLOURS[way]), x, y)
            if all(sc.free(px_, py_, 30) for t_, px_, py_ in parts if "Shadow" not in t_):
                for t_, px_, py_ in parts: sc.put(t_, *_sq(px_, py_))
                sc.mine += [(px_, py_) for t_, px_, py_ in parts if "Shadow" not in t_]
                leader = sc.p(R_t - 34 * k, a)
                spare += per[q]
                continue
            # no room for the awning: a pup tent like the rest
        if sc.put_px("OutdoorTraderPupTent", *sc.p(R_t, a), gap=60):
            beds.append((a, per[q]))
        else:
            spare += per[q]
    for j in range(spare):                                          # the leader's and a lost tent's sleepers
        if beds: beds[j % len(beds)] = (beds[j % len(beds)][0], beds[j % len(beds)][1] + 1)
    R_c = (95 if n_t else 90) * k
    if not beds:
        # no tents: the bedrolls side by side in a row behind the fire, all one way, their feet to it
        x0, y0 = sc.p(R_c, b)
        cot = S.COT_FOOT[S.axis_of(fx - x0, fy - y0)]
        ux, uy = -math.sin(b), math.cos(b)
        for j in range(sleepers):
            o = (j - (sleepers - 1) / 2) * 38
            sc.put_px(cot, x0 + ux * o, y0 + uy * o, gap=28)
    for a, cnt in beds:
        x0, y0 = sc.p(R_c, a)
        cot = S.COT_FOOT[S.axis_of(fx - x0, fy - y0)]               # the head to the tent, the foot to the fire
        ux, uy = -math.sin(a), math.cos(a)                          # side by side across the line to the fire
        for j in range(min(cnt, 2)):
            o = (j - (min(cnt, 2) - 1) / 2) * 36
            sc.put_px(cot, x0 + ux * o, y0 + uy * o, gap=28)
    # ---- seats round the fire, the cooking spot to one side --------------------------------------------------------
    seats = []
    seat_angles = [b + left * 1.25, b - left * 1.25, b + math.pi + left * 0.6, b + math.pi - left * 0.6]
    for a in seat_angles[:3 + (sleepers > 3)]:
        if abs(_ang(a - a_in)) < 0.35: continue                     # the way in to the fire stays open
        if sc.put_px(rng.choice(("Stump3", "Stump4", "Stump5", "Stump6")), *sc.p(62, a), gap=26):
            seats.append(sc.p(38, a))
    cook = b - left * 1.9
    if sc.put_px("Cauldron", *sc.p(58, cook), gap=26):
        sc.put_px(rng.choice(("SackChestMedium1", "SackChestMedium2")), *sc.p(94, cook - 0.25), gap=22)
        sc.put_px("WaterBarrel", *sc.p(96, cook + 0.25), gap=22)
    # ---- the store on one flank: the cart, crates side by side, barrels in a three, sacks --------------------------
    st = b + left * math.pi / 2
    goods = []
    sc.put_px("OutdoorTraderCart", *sc.p(178 * k, st), gap=40)
    ux, uy = math.cos(st + math.pi / 2), math.sin(st + math.pi / 2)        # along the store's line (tangent)
    line = S.line_of(ux, uy)
    gx, gy = sc.p(128 * k, st)
    n_cr = rng.randint(2, 3)
    for j in range(n_cr):                                           # crates side by side along the line
        o = (j - (n_cr - 1) / 2) * 30
        t = S.ALONG[line][rng.choice(("Crate1", "DarkCrate1"))]
        if sc.put_px(t, gx + ux * o, gy + uy * o, gap=24): goods.append(t)
    # the barrels at the crates' front end (away from the tents), the sacks by the cart
    fu = 1 if math.cos(st + math.pi / 2 - (b + math.pi)) > 0 else -1
    bx, by = gx + ux * (n_cr * 15 + 30) * fu, gy + uy * (n_cr * 15 + 30) * fu
    for dx, dy in ((0, 0), (22, 4), (10, -19)):                     # barrels in a three
        t = rng.choice(("Barrel", "Barrel2"))
        if sc.put_px(t, bx + dx, by + dy, gap=18): goods.append(t)
    cx_, cy_ = sc.p(178 * k, st)
    for j in range(rng.randint(1, 2)):
        t = rng.choice(SACKS)
        if sc.put_px(t, cx_ + ux * (46 + 20 * j) * fu, cy_ + uy * (46 + 20 * j) * fu, gap=18): goods.append(t)
    posts = [sc.p(98 * k, st)]
    # ---- the arms on the other flank: racks in a row ------------------------------------------------------------------
    ar = b - left * math.pi / 2
    ax, ay = sc.p(150 * k, ar)
    ux, uy = math.cos(ar + math.pi / 2), math.sin(ar + math.pi / 2)
    racks = [rng.choice(("OutdoorTraderArmorRack1", "OutdoorTraderArmorRack3", "OutdoorTraderArmorRack5"))
             for _ in range(rng.randint(2, 3))]
    racks.append(S.ALONG[S.line_of(ux, uy)][rng.choice(("TraderPoleArm1", "TraderPoleArm2"))])
    for j, t in enumerate(racks):
        o = (j - (len(racks) - 1) / 2) * 36
        sc.put_px(t, ax + ux * o, ay + uy * o, gap=24)
    sc.put_px("TraderQuiverRack", *sc.p(116 * k, ar + 0.32), gap=22)
    posts.append(sc.p(112 * k, ar))
    # ---- the lookout post toward the way in -------------------------------------------------------------------------------
    lookout = None
    for r in (215, 190, 165, 140):
        x, y = sc.p(r * k, a_in)
        if sc.free(x, y, 30):
            lookout = (x, y)
            sc.put_px(rng.choice(("Stump3", "Stump5")), *sc.p(r * k + 22, a_in + 0.28), gap=20)
            sc.put_px("TraderQuiverRack", *sc.p(r * k + 20, a_in - 0.3), gap=20)
            for q in range(3):
                sc.put_px(rng.choice(("CaveRocksMedium", "CaveRocksSmall")), *sc.p(r * k + 46 + q * 6, a_in + (q - 1) * 0.22))
            break
    if lookout is None: lookout = sc.p(120 * k, a_in)
    # ---- the take: the chest before the leader's tent, the stolen goods beside it --------------------------------------
    chest = None
    ca = t_angles[lead] if lead is not None else b
    for r, d in ((R_t - 32 * k, 0.34), (R_t - 32 * k, -0.34), (R_t * 0.72, 0.0), (R_t + 30, 0.6), (R_t + 30, -0.6),
                 (R_t * 0.6, 0.6), (R_t * 0.6, -0.6)):
        chest = sc.put_px("Chest3", *sc.p(r, ca + d), gap=24, items=loot)
        if chest:
            for j, t in enumerate((rng.choice(SACKS), "TraderAppleCrate", rng.choice(SACKS))[:2 + (n_t >= 3)]):
                if sc.put_px(t, *sc.p(r + 6 * j, ca + d + math.copysign(0.2 + 0.16 * j, d or 1)), gap=20):
                    goods.append(t)
            break
    if leader is None: leader = sc.p(R_t * 0.6, ca)
    return dict(fire=(fx, fy), seats=seats, lookout=lookout, chest=chest, goods=goods, leader=leader, posts=posts)


def wagon_wreck(spec, rng, land, centre, road_dir):
    """A trader's cart stopped by the road and plundered: a wheel off and lying behind it, its load thrown out in a fan
    from its side away from the road, the heavy things near (crates), the rolling ones further (barrels), the sacks
    slit and dropped between. road_dir: angle (radians, squares) along the road. Returns dict(cart, carter) in world
    px."""
    _replay(rng, "wagon_wreck")
    rng = own_rng(spec, "wagon_wreck", centre)
    sc = Scene(spec, rng, land, centre)
    sc.put("OutdoorTraderCart", sc.ci, sc.cj)
    # the load spills on the side with open ground (thrown against the forest wall, nothing would land)
    free = lambda o: sum(sc.ok(*sc.at(r, o + d)) for r in (1.0, 1.8, 2.4) for d in (-0.6, 0.0, 0.6))
    off = max((road_dir + math.pi / 2, road_dir - math.pi / 2), key=free)
    j = lambda: rng.uniform(-0.12, 0.12)
    sc.put("MineOreCartWheel", *sc.at(1.15, road_dir + math.pi + j()))          # the wheel that came off
    for r, d, kinds in ((1.05, -0.4, CRATES), (1.25, -0.05, CRATES), (1.9, -0.3, ("TraderAppleCrate",)),
                        (1.45, 0.45, SACKS), (1.85, -0.75, SACKS), (2.1, 0.3, BARRELS), (2.7, 0.55, BARRELS),
                        (1.0, 0.95, ("Straw1", "Straw2"))):
        if rng.random() < 0.85 or kinds is CRATES:
            sc.put(rng.choice(kinds), *sc.at(r + j(), off + d + j()))
    # the carter stands by his cart on open ground: behind it toward the road first, then round it
    for r, da in ((1.3, math.pi), (1.3, math.pi - 0.8), (1.3, math.pi + 0.8), (1.6, math.pi / 2), (1.6, -math.pi / 2),
                  (1.8, 0.0), (2.2, math.pi)):
        if sc.ok(*sc.at(r, off + da)): return dict(cart=square_px(sc.ci, sc.cj), carter=sc.px(r, off + da))
    return dict(cart=square_px(sc.ci, sc.cj), carter=square_px(sc.ci, sc.cj + 1.0))


def wolf_den(spec, rng, land, centre, mouth):
    """A heap of rock with the den's mouth toward `mouth` (squares), bones strewn before it. Returns the spots
    (world px) where the pack lies."""
    sc = Scene(spec, rng, land, centre)
    a_m = math.atan2(mouth[1] - sc.cj, mouth[0] - sc.ci)
    for t, r, n in (("CaveRocksHuge", 0.0, 1), ("CaveRocksLarge", 0.9, 3), ("CaveRocksMedium", 1.4, 3),
                    ("CaveRocksSmall", 1.8, 4)):
        for k in range(n):
            a = a_m + math.pi + (k - (n - 1) / 2) * (2.4 / max(1, n)) + rng.uniform(-0.2, 0.2)
            sc.put(t, *sc.at(r, a))
    for k in range(7):
        sc.put(rng.choice(BONES), *sc.at(rng.uniform(1.6, 3.2), a_m + rng.uniform(-0.9, 0.9)))
    return [sc.px(2.2 + 0.4 * (k % 2), a_m + (k - 1.5) * 0.45) for k in range(4)]


def cache(spec, rng, land, centre, loot, stump=False):
    """A chest (or a hollow stump) hidden off the path, marked by a small heap of stones. Returns the object."""
    sc = Scene(spec, rng, land, centre)
    o = sc.put("StumpChest1" if stump else rng.choice(("Chest1", "Chest2")), sc.ci, sc.cj, items=loot)
    for k in range(3):
        sc.put(rng.choice(("CaveRocksSmall", "CaveRocksPebbles")), *sc.at(0.9, 2 * math.pi * k / 3 + rng.uniform(0, 1)))
    return o


def signpost(spec, land, at_sq, key, kind="PlankSign1"):
    """A plank sign at a square whose text is `key` in the map's string table."""
    sc = Scene(spec, None, land, at_sq)
    return sc.put(kind, sc.ci, sc.cj, xfer={"Text": key})


def ruined_tower(spec, rng, land, centre, toward, loot, size=(7, 7), material="AncientRuin"):
    """The stump of an old tower: a square of ruined wall round a plot (square coordinates), broken through on the
    side facing `toward` (the way in) and breached here and there elsewhere, rubble fallen inside and out, a chest at
    the back. Lay it after the land's walls, before the planting. Returns dict(inside: world px spots for its
    keepers, chest, boss: the spot at the back by the chest)."""
    from kit.layout import point_cell
    w, h = size
    gi, gj = int(round(centre[0] - w / 2)), int(round(centre[1] - h / 2 + 1))
    sides = {"i0": [(gi, q) for q in range(gj - 1, gj + h)], "i1": [(gi + w, q) for q in range(gj - 1, gj + h)],
             "j0": [(p, gj - 1) for p in range(gi, gi + w + 1)], "j1": [(p, gj + h - 1) for p in range(gi, gi + w + 1)]}
    mids = {"i0": (gi, gj - 1 + h / 2), "i1": (gi + w, gj - 1 + h / 2), "j0": (gi + w / 2, gj - 1), "j1": (gi + w / 2, gj + h - 1)}
    front = min(mids, key=lambda s: math.hypot(mids[s][0] - toward[0], mids[s][1] - toward[1]))
    back = {"i0": "i1", "i1": "i0", "j0": "j1", "j1": "j0"}[front]
    for side, pts in sides.items():
        n = len(pts)
        gaps = set()
        if side == front:                                  # the way in: the middle of the wall is down
            gaps |= set(range(n // 2 - 1, n // 2 + 2))
        elif side != back and rng.random() < 0.7:         # a breach in a side wall
            k = rng.randint(2, n - 3)
            gaps |= {k, k + 1}
        for k, p in enumerate(pts):
            if k in gaps: continue
            c = point_cell(*p)
            if c not in spec.wallmap: spec.wall(*c, material)
        for k in gaps:                                     # the fallen stones lie where the wall came down
            si, sj = pts[k][0] + rng.uniform(-0.6, 0.6), pts[k][1] + rng.uniform(-0.6, 0.6)
            sc = Scene(spec, rng, land, (si, sj))
            sc.put(rng.choice(("CaveRocksMedium", "CaveRocksSmall", "CaveRocksPebbles")), si, sj)
    land.taken |= {(gi + a, gj + b) for a in range(-1, w + 1) for b in range(-1, h + 1)}
    ci, cj = gi + w / 2, gj - 1 + h / 2
    sc = Scene(spec, rng, land, (ci, cj))
    for k in range(rng.randint(4, 6)):                     # rubble against the inside of the walls
        a = rng.uniform(0, 2 * math.pi)
        sc.put(rng.choice(("CaveRocksLarge", "CaveRocksMedium", "CaveRocksSmall")), *sc.at(min(w, h) / 2 - 1.2, a))
    bx, by = mids[back]
    bi, bj = ci + (bx - ci) * 0.6, cj + (by - cj) * 0.6
    chest = sc.put("Chest4", bi, bj, items=loot)
    boss = square_px(ci + (bx - ci) * 0.25, cj + (by - cj) * 0.25)
    inside = [sc.px(1.6, a) for a in (0.5, 2.6, 4.4)]
    return dict(inside=inside, chest=chest, boss=boss, front=front)


def training_ground(spec, rng, land, centre, toward, r=4.5, floor="DirtLight2"):
    """A garrison's training ground (Greywatch's courtyard): a square of trodden sand round `centre` (squares), target
    barrels in a row along the far side from `toward` (where the watchers come from), racks of arms at its back
    corners, straw heaped by the targets, benches for the watchers by the way in. The sand goes only on land, off
    roads and buildings; lay it after land.apply. Returns dict(centre, spots: four points on the open sand where
    fighters stand, watch: by the benches, all world px)."""
    ci, cj = centre
    sc = Scene(spec, rng, land, centre)
    from kit.layout import square_tile
    for i in range(int(ci - r) - 1, int(ci + r) + 2):
        for j in range(int(cj - r), int(cj + r) + 3):
            if max(abs(i + 0.5 - ci), abs(j - 0.5 - cj)) > r: continue
            s = (i, j)
            if s in land.squares and s not in land.roads and s not in land.taken_strict and s not in land.water:
                spec.floor[square_tile(*s)] = floor
                land.taken.add(s)
    a_in = math.atan2(toward[1] - cj, toward[0] - ci)
    back = a_in + math.pi
    # the targets: a row across the back, square to the way in
    ux, uy = math.cos(back), math.sin(back)
    px_, py_ = -uy, ux
    for k in (-1.5, -0.5, 0.5, 1.5):
        sc.put(rng.choice(("TargetBarrel1", "TargetBarrel2")), ci + ux * (r - 1.2) + px_ * k * 1.3,
               cj + uy * (r - 1.2) + py_ * k * 1.3)
    for k in (-1, 1):                                          # racks at the back corners, straw beside the targets
        sc.put(rng.choice(("OutdoorTraderArmorRack1", "OutdoorTraderArmorRack3", "OutdoorTraderArmorRack5")),
               ci + ux * (r - 1.0) + px_ * k * (r - 0.8), cj + uy * (r - 1.0) + py_ * k * (r - 0.8))
        sc.put(rng.choice(("Straw1", "Straw2")), ci + ux * (r - 2.4) + px_ * k * 3.4, cj + uy * (r - 2.4) + py_ * k * 3.4)
    # benches for the watchers either side of the way in, facing across the sand
    for k in (-1, 1):
        si, sj = ci + math.cos(a_in) * (r - 0.9) + px_ * k * 2.6, cj + math.sin(a_in) * (r - 0.9) + py_ * k * 2.6
        bench = {"+u": "Bench1", "-u": "Bench5", "+v": "Bench4", "-v": "Bench2"}
        f = (-math.cos(a_in), -math.sin(a_in))                 # facing in
        key = ("+u" if f[0] > 0 else "-u") if abs(f[0]) >= abs(f[1]) else ("+v" if f[1] > 0 else "-v")
        sc.put(bench[key], si, sj)
    spots = [sc.px(1.6, a_in + math.pi / 2 * k + math.pi / 4) for k in range(4)]
    watch = sc.px(r - 1.6, a_in)
    return dict(centre=square_px(ci, cj), spots=spots, watch=watch)


def stone_ring(spec, rng, land, centre, n=7, radius=2.6, stone="ObeliskPrimitive", core=None, core_name=None,
               light=None, light_name=None, clear=4):
    """A ring of standing stones round a centre (squares): a shrine, a vent's ring, a circle in the woods. `core`: an
    object at the middle (a crystal, a fire basin), named `core_name` for the story's scripts; `light`: a ColorLight
    xfer at the middle, named `light_name` (A.enable lights it when the story says). The ring and `clear` squares
    round it are taken, so nothing grows into it. Returns the centre in world px."""
    ci, cj = centre
    for k in range(n):
        a = k * 2 * math.pi / n
        spec.obj_px(stone, *square_px(ci + radius * math.cos(a), cj + radius * math.sin(a)))
    x, y = square_px(ci, cj)
    if core: spec.obj_px(core, x, y, **({"scr": core_name} if core_name else {}))
    if light: spec.obj_px("ColorLight", x, y - 5, xfer=dict(light), **({"scr": light_name} if light_name else {}))
    land.taken |= {(int(ci) + a, int(cj) + 1 + b) for a in range(-clear, clear + 1) for b in range(-clear, clear + 1)}
    return x, y
