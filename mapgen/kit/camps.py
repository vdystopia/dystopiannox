"""Outdoor places with a purpose, laid out as one composed scene round a centre (square coordinates), each returning
the spots its people stand on so the design can put them there.

- bandit_camp: a fire ringed by stump seats, bedrolls (cots) beyond, pup tents behind, the stolen goods heaped on one
  side with the wagon they came off, racks of arms by the tents, a chest holding the take (Westwood's bandit camp on
  Con03A: CampFire, Cot2, stumps, a StumpChest and a DunMirChest of gold, rocks round it).
- wagon_wreck: a trader's cart stopped on the road, its load spilled round it, the carter's place beside it.
- wolf_den: a heap of rock with bones strewn before it, where a pack lies up.
- cache: a chest (or a hollow stump) hidden at the forest's edge, marked by a little heap of stones.
- signpost: a plank sign whose text is a key of the map's string table (kit/quests.QuestBook.text).

Every piece goes only on the land, off squares already taken, and marks its square taken.
"""
import math
from kit.layout import square_px

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
        self.placed.append((si, sj))
        self.land.taken.add((int(math.floor(si)), int(math.floor(sj)) + 1))
        return o

    def at(self, r, a):
        return self.ci + r * math.cos(a), self.cj + r * math.sin(a)

    def px(self, r, a):
        return square_px(*self.at(r, a))


def bandit_camp(spec, rng, land, centre, toward, loot, sleepers=4, tents=2):
    """The camp round its fire, open toward `toward` (squares: where the way in comes from). loot: the chest's items
    (nox.Spec.obj_px items). Returns dict(fire, seats, lookout, chest, goods) in world px; seats are where the bandits
    sit round the fire, lookout where one keeps watch toward the way in."""
    sc = Scene(spec, rng, land, centre)
    a_in = math.atan2(toward[1] - sc.cj, toward[0] - sc.ci)       # the way in
    sc.put("CampFire", sc.ci, sc.cj)
    seats = []
    for k in range(5):                                             # stump seats round the fire, the way in left open
        a = a_in + math.pi / 3 + k * (4 * math.pi / 3) / 4
        si, sj = sc.at(1.6, a)
        if sc.put(rng.choice(("Stump3", "Stump4", "Stump5", "Stump6")), si, sj): seats.append(sc.px(1.05, a))
    for k in range(sleepers):                                      # bedrolls beyond, on the far side
        a = a_in + math.pi + (k - (sleepers - 1) / 2) * 0.62
        si, sj = sc.at(3.3, a)
        quarter = int(((math.degrees(a) + 45) % 360) // 90)
        sc.put(COT_BY_ANGLE[quarter], si, sj)
    for k in range(tents):                                         # pup tents behind the bedrolls
        a = a_in + math.pi + (k - (tents - 1) / 2) * 0.95
        sc.put("OutdoorTraderPupTent", *sc.at(5.0, a))
    # the stolen goods heaped to one side with the wagon they came off
    side = a_in + math.pi / 2 * (1 if rng.random() < 0.5 else -1)
    gx, gy = sc.at(4.2, side)
    sc.put("OutdoorTraderCart", *sc.at(6.0, side))
    goods = []
    for k in range(rng.randint(7, 10)):
        t = rng.choice(CRATES + CRATES + BARRELS + SACKS)
        r, a = rng.uniform(0, 1.5), rng.uniform(0, 2 * math.pi)
        if sc.put(t, gx + r * math.cos(a), gy + r * math.sin(a)): goods.append(t)
    # racks of arms by the tents, the chest of the take between them
    for k in (-1, 1):
        sc.put(rng.choice(("OutdoorTraderArmorRack1", "OutdoorTraderArmorRack3", "OutdoorTraderArmorRack5")),
               *sc.at(4.6, a_in + math.pi + k * 1.35))
    chest = None
    for r in (4.2, 3.8, 5.0):
        chest = sc.put("Chest3", *sc.at(r, a_in + math.pi), items=loot)
        if chest: break
    # a lookout stands at the camp's edge watching the way in
    lookout = sc.px(3.8, a_in)
    return dict(fire=square_px(sc.ci, sc.cj), seats=seats, lookout=lookout, chest=chest, goods=goods)


def wagon_wreck(spec, rng, land, centre, road_dir):
    """A trader's cart stopped by the road, its load spilled: crates, barrels and sacks thrown about on the side away
    from the road. road_dir: angle (radians, squares) along the road. Returns dict(cart, carter) in world px."""
    sc = Scene(spec, rng, land, centre)
    sc.put("OutdoorTraderCart", sc.ci, sc.cj)
    # the load spills on the side with open ground (thrown against the forest wall, nothing would land)
    free = lambda o: sum(sc.ok(*sc.at(r, o + d)) for r in (1.0, 1.8, 2.4) for d in (-0.6, 0.0, 0.6))
    off = max((road_dir + math.pi / 2, road_dir - math.pi / 2), key=free)
    for k in range(rng.randint(5, 8)):
        r, a = rng.uniform(0.8, 2.4), off + rng.uniform(-1.0, 1.0)
        sc.put(rng.choice(CRATES + BARRELS + SACKS), *sc.at(r, a))
    for k in range(3):
        sc.put(rng.choice(("ArmBone", "LegBone")), *sc.at(rng.uniform(1.5, 2.5), off + math.pi + rng.uniform(-0.6, 0.6)))
    # the carter stands by his cart on open ground: behind it toward the road first, then round it
    for r, da in ((1.3, math.pi), (1.3, math.pi - 0.8), (1.3, math.pi + 0.8), (1.6, math.pi / 2), (1.6, -math.pi / 2),
                  (1.8, 0.0), (2.2, math.pi)):
        if sc.ok(*sc.at(r, road_dir + da)): return dict(cart=square_px(sc.ci, sc.cj), carter=sc.px(r, road_dir + da))
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
