"""Outdoor places with a purpose, laid out as one composed scene round a centre (square coordinates), each returning
the spots its people stand on so the design can put them there.

- bandit_camp: a camp in zones with clear ground between them (Westwood's camps on Con03A, Con04a, War05A): the
  hearth (fire, log benches, the pot), the sleeping row (tents with their bedrolls), the store (one tidy row, the cart
  behind), the arms corner or the dig, the lookout at the way in; scaled to its clearing.
- camp_site: where a camp has room, near a place and off its road.
- urchin_camp: urchins squatting round a fire: their beds in a row, a table ringed by stools, their pickings heaped.
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
from kit import spacing as SP

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
    """A scene laid in world px round a centre: polar placement in screen angles (0 = right, -pi/2 = up). Every piece
    keeps Westwood's spacing from the camp's other pieces (kit/spacing: barrels 25 px apart, crates 31, a cart 48 from
    anything...), so a stack touches only where Westwood's stacks touch."""
    def __init__(self, spec, rng, land, centre):
        super().__init__(spec, rng, land, centre)
        self.fx, self.fy = square_px(*centre)
        self.mine = []                                  # px of the pieces laid, for spacing
        self.typed = []                                 # (type, x, y) of the pieces laid

    def p(self, r, a):
        return self.fx + r * math.cos(a), self.fy + r * math.sin(a)

    def free(self, x, y, gap=0.0, t=None):
        if not self.ok(*_sq(x, y)): return False
        if t is not None and not SP.spaced(t, x, y, self.typed): return False
        return all(math.hypot(x - a, y - b) >= gap for a, b in self.mine)

    def put_px(self, t, x, y, gap=0.0, **extra):
        if not self.free(x, y, gap, t): return None
        o = self.put(t, *_sq(x, y), **extra)
        if o is not None:
            self.mine.append((x, y)); self.typed.append((t, x, y))
        return o

    def stand(self, cands, clear=36.0):
        """The first of `cands` (px) where a person can stand: on the camp's open ground, `clear` px from every piece
        laid (a person had stood on a bedroll, 11 px from its middle). None if none is."""
        for x, y in cands:
            if self.ok(*_sq(x, y)) and all(math.hypot(x - a, y - b) >= clear for a, b in self.mine):
                return (x, y)
        return None

    def row(self, pieces, x0, y0, ux, uy, centred=True):
        """Pieces [(type, extra)] in a row along (ux, uy) from (x0, y0), each its Westwood gap after the one before
        (kit/spacing.gap): a tidy stack, never overlapping. Returns [(type, x, y)] of those laid."""
        offs, o = [], 0.0
        for k, (t, _) in enumerate(pieces):
            if k: o += max(SP.gap(pieces[k - 1][0], t), 20.0) + 2
            offs.append(o)
        mid = offs[-1] / 2 if (centred and offs) else 0.0
        out = []
        for (t, extra), o in zip(pieces, offs):
            x, y = x0 + ux * (o - mid), y0 + uy * (o - mid)
            if self.put_px(t, x, y, **extra): out.append((t, x, y))
        return out


def _seat(ux, uy):
    """A crude log bench (OgreBench, Westwood's ogre camps' seat round their fires) lying along a screen direction."""
    a = math.degrees(math.atan2(uy, ux)) % 180
    if a < 22.5 or a >= 157.5: return "OgreBench3"           # across the screen
    if a < 67.5: return "OgreBench1"                         # along "\\"
    if a < 112.5: return "OgreBench4"                        # up and down
    return "OgreBench2"                                      # along "/"


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


def _hold_ground(land, centre, r):
    """The camp's ground stays open: squares within r of its centre are taken, so the planting keeps its trees off and
    the dressing its scenes (Ambermere, 2026-10-05: the trees grew up to the diggers' tents, the camp read as a heap at
    the forest's edge). Scene.ok tests only taken_strict, so the camp's own pieces are not stopped by it."""
    ci, cj = centre
    land.taken |= {(int(ci) + a, int(cj) + 1 + b) for a in range(-r, r + 1) for b in range(-r, r + 1)
                   if a * a + b * b <= r * r and (int(ci) + a, int(cj) + 1 + b) in land.squares}


def _clearing(probe, n=24):
    """How far the camp's open ground reaches (px): the largest radius at which 70% of the ring round the centre, and
    of every ring inside it, is free land."""
    best = 100
    for r in range(120, 341, 20):
        frac = sum(probe.free(*probe.p(r, k * 2 * math.pi / n)) for k in range(n)) / n
        if frac < 0.7: break
        best = r
    return best


# Westwood's camps, measured (Con03A, Con04a, War05A, Wiz02C, Wiz03b, Wiz03c; py corpus, 2026-10-05): stones ringed
# 17-30 px round the fire; one or two seats 52-64 px out (Stool1 59, a stump 64; the ogres' benches and stools); pup
# tents 112-120 px out; the store (barrels in threes, steel crates, the cart) 75-140 px out on one side; racks in a row
# 26-30 px apart 200-225 px out (Con04a); the men 47-56 px from the fire at most two (War05A's grunts), the rest
# 120-270 px out (Con03A's swordsmen 194-273, its archer 226).
CAMP_R = dict(seat=64, sit=42, cook=70, cot=132, tent=196, store=212, arms=212, lookout=262)


def bandit_camp(spec, rng, land, centre, toward, loot, sleepers=4, tents=2, trade="bandit", finds=()):
    """A camp in zones with clear ground between them, as Westwood lays its camps (Con03A, Con04a, War05A), open toward
    `toward` (squares: where the way in comes from). Starwell playtest, 2026-10-05: "another absolute mess of randomly
    placed things and overly clustered NPCs ... It needs a lot of refinement and a lot more purpose and organization";
    "the stumps around the fires in bandit camps arent the right object for that use case".

    - the hearth: the fire ringed by stones, two or three crude log benches and a stool round it (never stumps), the
      way in to it left open, the cook pot beside it;
    - the sleeping row behind the fire, on the side away from the way in and toward the top of the screen: the tents
      in an arc facing the fire, each with its bedrolls before it (head to the tent, foot to the fire); the leader's
      awning in the middle with three or more; with no tents, the bedrolls side by side in a row;
    - the store on one flank: one tidy row of sacks, crates and barrels (water barrel last), each its Westwood gap
      from the next, the cart drawn up behind it;
    - the arms corner on the other flank (trade "bandit"): racks in a row, a polearm rack, a straw dummy before them;
      or the dig (trade "dig"): spades and picks left in the ground, the tool barrel, the spoil heaped, what they dig
      for (`finds`) set out in a little heap;
    - the lookout at the way in: a torch pole (the camp's light at its edge), the watchman's stool and his quivers.
    Every zone keeps clear ground round it, and the whole camp scales with its clearing (0.75-1.25 of Westwood's).
    Returns dict(fire, seats (spots for one or two by the fire), lookout, chest, goods, leader, posts (by the store,
    the arms or the dig, and the pot), tents (a spot before each tent), work (at the dig), zones): world px."""
    _replay(rng, "bandit_camp")
    rng = own_rng(spec, "bandit_camp", centre)
    fx, fy = square_px(*centre)
    tx, ty = square_px(*toward)
    a_in = math.atan2(ty - fy, tx - fx)
    probe = Camp(spec, rng, land, centre)
    s = max(0.75, min(1.25, _clearing(probe) / 250.0))
    R = {k: v * (s if k not in ("seat", "sit", "cook") else 1.0) for k, v in CAMP_R.items()}
    R["cot"] = max(R["cot"], 118)
    R["tent"] = max(R["tent"], R["cot"] + 58)
    # the back of the camp: away from the way in, toward the top of the screen where it can, with room for the tents
    best = None
    for q in range(24):
        b = -math.pi + q * math.pi / 12
        off_in = abs(_ang(b - a_in))
        if off_in < math.pi * 0.6: continue
        room = sum(probe.free(*probe.p(r * s, b + d)) for r in (120, 170, 210, 240) for d in (-0.6, -0.3, 0, 0.3, 0.6))
        side = sum(probe.free(*probe.p(r * s, b + d)) for r in (180, 230) for d in (1.75, -1.75))
        score = room * 2 + side + 3 * math.cos(b + math.pi / 2) + 2 * off_in / math.pi
        if best is None or score > best[0]: best = (score, b)
    b = best[1] if best else a_in + math.pi
    left = 1 if rng.random() < 0.5 else -1                          # the side the store takes
    # the arms (or the dig) take the side nearer the way in (they guard it); the store the far one
    if abs(_ang(b + left * 1.75 - a_in)) < abs(_ang(b - left * 1.75 - a_in)): left = -left
    sc = Camp(spec, rng, land, centre)
    sc.put_px("CampFire", fx, fy)
    ph = rng.uniform(0, 1)
    for q in range(7):                                             # stones ringed round the fire
        sc.put_px("CaveRocksSmall", *sc.p(22, ph + q * 2 * math.pi / 7))
    zones = {"hearth": ((fx, fy), 90.0)}

    # ---- the sleeping row: the tents in an arc behind the fire, the bedrolls before them ------------------------
    n_t = max(0, tents)
    step = 2 * math.asin(min(1.0, 124 / (2 * R["tent"]))) if n_t > 1 else 0
    t_angles = [b + (q - (n_t - 1) / 2) * step for q in range(n_t)]
    lead = n_t // 2 if n_t >= 3 else None
    leader, tent_spots, beds = None, [], []
    per = [sleepers // max(1, n_t) + (1 if q < sleepers % max(1, n_t) else 0) for q in range(n_t)]
    spare = 0
    for q, a in enumerate(t_angles):
        if q == lead:
            # the leader's awning, a little further back; its open side toward the camera, and so the fire
            x, y = sc.p(R["tent"] + 40, a)
            way = "DN" if math.cos(a) < 0 else "UP"
            parts = S.tent_pieces(way, rng.choice(S.TENT_COLOURS[way]), x, y)
            if all(sc.free(px_, py_, 30) for t_, px_, py_ in parts if "Shadow" not in t_):
                for t_, px_, py_ in parts: sc.put(t_, *_sq(px_, py_))
                sc.mine += [(px_, py_) for t_, px_, py_ in parts if "Shadow" not in t_]
                leader = sc.p(R["tent"] - 40, a)
                spare += per[q]
                continue
        for dr, da in ((0, 0), (-18, 0), (0, 0.12), (0, -0.12), (-18, 0.12), (-18, -0.12), (22, 0)):
            if sc.free(*sc.p(R["cot"] + dr, a + da)) and \
                    sc.put_px("OutdoorTraderPupTent", *sc.p(R["tent"] + dr, a + da), gap=70):
                beds.append((a + da, per[q], dr))
                break
        else:
            spare += per[q]
    for j in range(spare):                                          # the leader's and a lost tent's sleepers
        if beds: beds[j % len(beds)] = beds[j % len(beds)][:1] + (beds[j % len(beds)][1] + 1,) + beds[j % len(beds)][2:]
    if not beds and sleepers:
        # no tents: the bedrolls side by side in a row behind the fire, all one way, their feet to it
        x0, y0 = sc.p(R["cot"], b)
        cot = S.COT_FOOT[S.axis_of(fx - x0, fy - y0)]
        ux, uy = -math.sin(b), math.cos(b)
        sc.row([(cot, {})] * sleepers, x0, y0, ux, uy)
        tent_spots.append(sc.p(R["cot"] - 44, b + 0.45))
    for a, cnt, dr in beds:
        x0, y0 = sc.p(R["cot"] + dr, a)
        cot = S.COT_FOOT[S.axis_of(fx - x0, fy - y0)]               # the head to the tent, the foot to the fire
        ux, uy = -math.sin(a), math.cos(a)                          # side by side across the line to the fire
        sc.row([(cot, {})] * min(cnt, 2), x0, y0, ux, uy)
        tent_spots.append(sc.p(R["tent"] + dr - 30, a + 0.3))       # beside the bedrolls, by the tent's mouth
    zones["sleep"] = (sc.p((R["cot"] + R["tent"]) / 2, b), max(80.0, R["tent"] * step * max(1, n_t) / 2 + 40))

    # ---- the hearth: log benches and a stool round the fire, the cook pot beside it --------------------------------
    seats = []
    for k, (a, kind) in enumerate(((b, "bench"), (b + left * 1.3, "stool"), (b - left * 1.3, "bench"))):
        if abs(_ang(a - a_in)) < 0.5: continue                       # the way in to the fire stays open
        x, y = sc.p(R["seat"], a)
        t = _seat(-math.sin(a), math.cos(a)) if kind == "bench" else rng.choice(("Stool1", "Stool2", "Stool3"))
        if sc.put_px(t, x, y) and len(seats) < 2:
            seats.append(sc.p(R["sit"], a + (0.3 if kind == "bench" else 0.0)))
    cook = b + left * 2.35               # the pot by the fire's front on the store's side, off the line to the store
    pot = sc.put_px("Cauldron", *sc.p(R["cook"], cook))
    cook_spot = sc.p(R["cook"] + 34, cook + 0.3 * left) if pot else None

    # ---- the store on one flank: one tidy row, the cart drawn up behind it -----------------------------------------
    st = b + left * 1.75
    sx, sy = sc.p(R["store"], st)
    ux, uy = -math.sin(st), math.cos(st)                            # along the row (tangent to the camp)
    wx, wy = math.cos(st), math.sin(st)                             # out, away from the fire
    line = S.line_of(ux, uy)
    goods = []
    stock = [(rng.choice(SACKS), {}) for _ in range(rng.randint(1, 2))]
    stock += [(S.ALONG[line][rng.choice(("Crate1", "DarkCrate1"))], {}) for _ in range(rng.randint(2, 3))]
    stock += [(rng.choice(("Barrel", "Barrel2")), {}) for _ in range(rng.randint(1, 2))] + [("WaterBarrel", {})]
    if rng.random() < 0.5: stock.reverse()
    goods += [t for t, _, _ in sc.row(stock, sx, sy, ux, uy)]
    sc.put_px("OutdoorTraderCart", sx + wx * 58, sy + wy * 58)
    store_spot = (sx - wx * 44, sy - wy * 44)
    zones["store"] = ((sx + wx * 20, sy + wy * 20), 110.0)

    # ---- the arms corner, or the dig, on the other flank --------------------------------------------------------------
    ar = b - left * 1.75
    ax, ay = sc.p(R["arms"], ar)
    ux, uy = -math.sin(ar), math.cos(ar)
    wx, wy = math.cos(ar), math.sin(ar)
    work = []
    if trade == "dig":
        # spades and picks left standing in the ground, the tool barrel, the spoil heaped behind, the finds before it
        tools = [("BarrelWithTools1", {}), ("MiningShovelInGround", {}), ("MiningPickAxeInGround1", {}),
                 ("MiningShovelInGround", {}), ("MiningPickAxeInGround2", {})]
        sc.row(tools, ax, ay, ux, uy)
        for k in range(3):                                           # the spoil, heaped behind the tools
            sc.put_px(("CaveRocksLarge", "CaveRocksMedium", "CaveRocksMedium")[k],
                      ax + wx * 44 + ux * (k - 1) * 30, ay + wy * 44 + uy * (k - 1) * 30)
        for t, (du, dw) in zip(finds[:3], ((-13, 4), (13, 4), (0, -18))):     # what they dig for, heaped before them
            sc.put_px(t, ax - wx * (44 + dw) + ux * du, ay - wy * (44 + dw) + uy * du)
        work = [(ax - wx * 30 - ux * 70, ay - wy * 30 - uy * 70), (ax - wx * 30 + ux * 70, ay - wy * 30 + uy * 70)]
        arms_spot = None
    else:
        racks = [(rng.choice(("OutdoorTraderArmorRack1", "OutdoorTraderArmorRack3", "OutdoorTraderArmorRack5")), {})
                 for _ in range(rng.randint(2, 3))]
        racks.append((S.ALONG[S.line_of(ux, uy)][rng.choice(("TraderPoleArm1", "TraderPoleArm2"))], {}))
        sc.row(racks, ax, ay, ux, uy)
        sc.put_px(rng.choice(("TargetBarrel1", "TargetBarrel2")), ax - wx * 64, ay - wy * 64)      # the dummy
        arms_spot = (ax - wx * 40 + ux * 50, ay - wy * 40 + uy * 50)
    zones["arms"] = ((ax, ay), 100.0)

    # ---- the lookout at the way in: the torch pole, the watchman's stool, his quivers ---------------------------------
    lookout = None
    for r, d in [(r, d) for r in (R["lookout"], R["lookout"] - 30, R["lookout"] - 60, 210, 180) for d in (0, 0.25, -0.25)]:
        a = a_in + d
        x, y = sc.p(r, a)
        ux, uy = -math.sin(a), math.cos(a)
        # the torch pole and the quivers out ahead of the watch, his stool just behind him
        set_ = [("TorchPole", x + ux * 20 + math.cos(a) * 48, y + uy * 20 + math.sin(a) * 48),
                (rng.choice(("Stool1", "Stool2")), x - math.cos(a) * 40, y - math.sin(a) * 40),
                ("TraderQuiverRack", x - ux * 26 + math.cos(a) * 48, y - uy * 26 + math.sin(a) * 48)]
        if sc.free(x, y, 40) and all(sc.free(px_, py_, 0, t_) for t_, px_, py_ in set_[:2]):
            lookout = (x, y)
            for t_, px_, py_ in set_: sc.put_px(t_, px_, py_)
            break
    if lookout is None: lookout = sc.p(R["lookout"] * 0.8, a_in)
    zones["lookout"] = (lookout, 60.0)

    # ---- the take: the chest before the leader's tent, the stolen goods beside it --------------------------------------
    chest = None
    ca = t_angles[lead] if lead is not None else b
    for r, d in ((R["tent"] - 52, 0.0), (R["tent"] - 52, 0.3), (R["tent"] - 52, -0.3), (R["tent"] + 50, 0.5),
                 (R["tent"] + 50, -0.5), (R["cot"] - 20, 0.6), (R["cot"] - 20, -0.6)):
        if n_t == 1 and abs(d) < 0.2: continue           # not in a tent's mouth
        chest = sc.put_px("Chest3", *sc.p(r, ca + d), items=loot)
        if chest:
            for j, t in enumerate((rng.choice(SACKS), "TraderAppleCrate")[:1 + (n_t >= 3)]):
                if sc.put_px(t, *sc.p(r + 4, ca + d + math.copysign(0.2 + 0.18 * j, d or 1))):
                    goods.append(t)
            break
    if leader is None:                              # by the take, on its fire side, clear of the bedrolls
        cx_, cy_ = (chest["x"], chest["y"]) if chest else sc.p(R["tent"] - 52, ca)
        ux_, uy_ = fx - cx_, fy - cy_
        L_ = math.hypot(ux_, uy_) or 1
        cands = [(cx_ + ux_ / L_ * d + -uy_ / L_ * o, cy_ + uy_ / L_ * d + ux_ / L_ * o)
                 for d in (40, 54, 30) for o in (0, 30, -30, 55, -55)]
        leader = (sc.stand(cands) or
                  sc.stand([sc.p(r, ca + d) for r in (R["cot"] - 50, R["cot"] - 40) for d in (0.5, -0.5, 0.9, -0.9)]) or
                  sc.p(R["cot"] - 50, ca + 0.6))
    def spot(p):                                    # a person's spot near p, clear of the camp's pieces
        ring = [(p[0] + r * math.cos(k * math.pi / 4), p[1] + r * math.sin(k * math.pi / 4)) for r in (20, 36) for k in range(8)]
        return sc.stand([p] + ring, clear=32) or p
    posts = [spot(p) for p in (store_spot, arms_spot, cook_spot) if p]
    tent_spots = [spot(p) for p in tent_spots]
    work = [spot(p) for p in work]
    _hold_ground(land, centre, int(round(8.5 * s)))
    return dict(fire=(fx, fy), seats=seats, lookout=lookout, chest=chest, goods=goods, leader=leader, posts=posts,
                tents=tent_spots, work=work, zones=zones, scale=s)


# Westwood's ogre village (Con05B / War05B / Wiz05B, measured 2026-10-05): the fire pit with meat and a carcass 55-80 px
# off it, stools and log benches 73-100 px out, bones strewn round; the tusk palisades are rows of OgreMoundTusk along a
# screen diagonal 33 px apart, each tusk with its shadow at a fixed offset; skull posts (OgrePostSkull, OgrePostHeads)
# with their shadows by the palisades' ends; barrels, sacks and carcasses 120-230 px out on one side; straw bedding.
TUSK_SHADOW = {"OgreMoundTusk1": (-1, 1), "OgreMoundTusk3": (-15, 0), "OgreMoundTusk4": (-21, -5),
               "OgreMoundTusk5": (-14, -13), "OgreMoundTusk6": (-16, -11)}
POST_SHADOW = {"OgrePostSkull1": ("OgrePostShadowSkull1", (-18, 4)), "OgrePostSkull2": ("OgrePostShadowSkull2", (-18, 17)),
               "OgrePostHeads1": ("OgrePostShadowHeads1", (-28, 24))}
OGRE_R = dict(seat=82, sit=50, meat=62, straw=138, store=205, gate=250, back=196)


def ogre_camp(spec, rng, land, centre, toward, loot, sleepers=4, wing=4):
    """The ogres' village before their lair, laid as Westwood lays Con05B's (an ogre culture's camp, the bandit camp's
    zones in the ogres' pieces), open toward `toward` (squares: the way in):
    - the hearth: the fire pit (a real fire), meat and a carcass on the cook's side, crude log benches and stools round
      it with the way in to it open, bones strewn;
    - the sleeping row behind it: heaps of straw bedding side by side in an arc, the warlord's bearskin and the take
      (a chest) at its middle;
    - the store on one flank: barrels and ogre sacks in one row, a big carcass hung beside it;
    - the gate at the way in: two wings of tusk palisade (rows of tusks along a screen diagonal, 33 px apart, each with
      its shadow) either side of the way, skull posts at the gate's ends, a torch pole inside it, the lookout's spot.
    Scales with its clearing as bandit_camp does. Returns the same record as bandit_camp (fire, seats, lookout, chest,
    goods, leader, posts, tents, work, zones), for kit/posts.camp_posts."""
    rng = own_rng(spec, "ogre_camp", centre)
    fx, fy = square_px(*centre)
    tx, ty = square_px(*toward)
    a_in = math.atan2(ty - fy, tx - fx)
    probe = Camp(spec, rng, land, centre)
    s = max(0.8, min(1.2, _clearing(probe) / 260.0))
    R = {k: v * (s if k in ("straw", "store", "gate", "back") else 1.0) for k, v in OGRE_R.items()}
    b = a_in + math.pi                                       # the back, away from the way in
    left = 1 if rng.random() < 0.5 else -1
    sc = Camp(spec, rng, land, centre)
    sc.put_px("OgreFirePit", fx, fy)
    zones = {"hearth": ((fx, fy), 100.0)}
    # ---- the hearth: meat and carcass on the cook's side, benches and stools round, bones about -------------------
    cook = b + left * 2.2
    goods = []
    for k, t in enumerate(("OgreHutMeat", "OgreHutCarcass", "OgreHutMeat")):
        if sc.put_px(t, *sc.p(R["meat"] + 6 * k, cook + (k - 1) * 0.42), gap=26): goods.append(t)
    seats = []
    for a, kind in ((b, "bench"), (b - left * 1.25, "stool"), (b + left * 0.95, "stool"), (a_in + left * 1.35, "bench")):
        if abs(_ang(a - a_in)) < 0.6: continue
        t = _seat(-math.sin(a), math.cos(a)) if kind == "bench" else rng.choice(("OgreStool1", "OgreStool2"))
        if sc.put_px(t, *sc.p(R["seat"], a), gap=30) and len(seats) < 2:
            seats.append(sc.p(R["sit"], a + 0.35))
    for k in range(5):
        a = b + rng.uniform(-2.4, 2.4)
        if abs(_ang(a - a_in)) < 0.5: continue
        sc.put_px(rng.choice(BONES), *sc.p(rng.uniform(100, 130), a), gap=18)
    # ---- the sleeping row: straw bedding side by side in an arc behind the fire --------------------------------------
    n = max(2, sleepers)
    step = 46.0 / R["straw"]
    beds_at = []
    for q in range(n):
        a = b + (q - (n - 1) / 2) * step * (1 if q % 2 == 0 else 1)
        if sc.put_px(rng.choice(("OgreStraw1", "OgreStraw1", "OgreStraw2", "OgreStraw3")), *sc.p(R["straw"], a), gap=34):
            beds_at.append(sc.p(R["straw"] - 42, a + 0.18))
    zones["sleep"] = (sc.p(R["straw"], b), 40.0 + n * 23)
    # the take: the warlord's bearskin and his chest behind the bedding's middle
    chest = None
    rug = sc.put_px(rng.choice(("OgreBearskin1", "OgreBearskin3")), *sc.p(R["back"] + 18, b), gap=40)
    for d in (0.32, -0.32, 0.5, -0.5):
        chest = sc.put_px("Chest3", *sc.p(R["back"] + 12, b + d), gap=30, items=loot)
        if chest: break
    leader = sc.stand([sc.p(R["back"] - 34, b + d) for d in (0.0, 0.15, -0.15, 0.3, -0.3)], clear=30) or \
        sc.p(R["back"] - 34, b)
    # ---- the store on one flank: barrels and sacks in one row, the big carcass beside it -------------------------------
    st = b - left * 1.65
    sx, sy = sc.p(R["store"], st)
    ux, uy = -math.sin(st), math.cos(st)
    wx, wy = math.cos(st), math.sin(st)
    stock = [("Barrel", {}), ("OgreSack1", {}), ("Barrel2", {}), ("OgreSack2", {}), ("Barrel", {})][:rng.randint(4, 5)]
    goods += [t for t, _, _ in sc.row(stock, sx, sy, ux, uy)]
    if sc.put_px("OgreHutCarcassBig", sx + wx * 46 + ux * 40, sy + wy * 46 + uy * 40, gap=30): goods.append("OgreHutCarcassBig")
    store_spot = (sx - wx * 46, sy - wy * 46)
    zones["store"] = ((sx, sy), 100.0)
    # ---- the gate: two wings of tusk palisade either side of the way in, skull posts at its ends -----------------------
    tx_, ty_ = -math.sin(a_in), math.cos(a_in)               # across the way in
    dx_, dy_ = (math.sqrt(0.5), math.sqrt(0.5)) if abs(tx_ + ty_) >= abs(tx_ - ty_) else (math.sqrt(0.5), -math.sqrt(0.5))
    if dx_ * tx_ + dy_ * ty_ < 0: dx_, dy_ = -dx_, -dy_      # the palisade's line: the screen diagonal nearest across
    # the gate where both wings stand whole: off the road the way in comes by, clear of the camp's pieces (the first
    # Harrowby camp's wings were broken off by the hill road, two tusks on one side)
    def wings_at(r):
        cx_, cy_ = sc.p(r, a_in)
        return sum(sc.free(cx_ + dx_ * o, cy_ + dy_ * o, 0, "OgreMoundTusk4")
                   for side in (1, -1) for o in (side * (58 + 33 * k) for k in range(wing)))
    gr = max((R["gate"], R["gate"] - 20, R["gate"] + 20, R["gate"] - 40, R["gate"] + 40, R["gate"] - 60),
             key=lambda r: (wings_at(r), -abs(r - R["gate"])))
    gx, gy = sc.p(gr, a_in)
    for side in (1, -1):
        for k in range(wing):
            o = side * (58 + 33 * k)
            t = rng.choice(tuple(TUSK_SHADOW))
            x, y = gx + dx_ * o, gy + dy_ * o
            if sc.put_px(t, x, y):
                sh = TUSK_SHADOW[t]
                spec.obj_px(t.replace("Tusk", "TuskShadow"), x + sh[0], y + sh[1])
        post = "OgrePostHeads1" if side == left else "OgrePostSkull2"
        x, y = gx + dx_ * side * 30, gy + dy_ * side * 30
        if sc.put_px(post, x, y):
            shn, sh = POST_SHADOW[post]
            spec.obj_px(shn, x + sh[0], y + sh[1])
    ix, iy = math.cos(a_in), math.sin(a_in)
    lookout = sc.stand([(gx - ix * d + dx_ * o, gy - iy * d + dy_ * o) for d in (46, 60, 34) for o in (-40, 40, -60, 60)],
                       clear=30) or (gx - ix * 50, gy - iy * 50)
    sc.put_px("TorchPole", gx - ix * 38 - dx_ * 64 * left, gy - iy * 38 - dy_ * 64 * left, gap=24)
    zones["gate"] = ((gx, gy), 70.0 + 33 * wing)
    posts = [p for p in (store_spot, sc.p(R["meat"] + 40, cook + 0.5 * left)) if p]

    def spot(p):
        ring = [(p[0] + r * math.cos(k * math.pi / 4), p[1] + r * math.sin(k * math.pi / 4)) for r in (20, 36) for k in range(8)]
        return sc.stand([p] + ring, clear=32) or p
    posts = [spot(p) for p in posts]
    tents = [spot(p) for p in beds_at[::2]]
    _hold_ground(land, centre, int(round(9 * s)))
    return dict(fire=(fx, fy), seats=seats, lookout=lookout, chest=chest, goods=goods, leader=leader, posts=posts,
                tents=tents, work=[], zones=zones, scale=s, gate=(gx, gy))


def camp_site(spec, land, near, reach=14, road_clear=4.5, room=7, avoid=()):
    """Where a camp goes near `near` (squares): the square within `reach` with the most open ground round it (land off
    roads, water, buildings, walls and `avoid` within `room` squares), no road within `road_clear`, a little nearer
    `near` on a tie. Ambermere, 2026-10-05: the diggers' camp, laid on the square nearest the barrow-field's middle
    off the road, was squeezed between the graveyard's fence and the forest, its tents, racks and pot in a heap.
    Returns continuous square coordinates (the square's middle), as bandit_camp takes them."""
    from kit.layout import bfs_distance
    avoid = set(avoid)
    near_road = bfs_distance(list(land.roads), land.squares, int(road_clear) + 1)
    probe = Scene(spec, None, land, near)
    free = {s for s in land.squares if s not in avoid and probe.ok(s[0] + 0.5, s[1] - 0.5)
            and math.hypot(s[0] - near[0], s[1] - near[1]) <= reach + room}
    best = None
    for s in free:
        d = math.hypot(s[0] - near[0], s[1] - near[1])
        if d > reach or near_road.get(s, 99) < road_clear: continue
        disc = [(a, b) for a in range(-room, room + 1) for b in range(-room, room + 1) if a * a + b * b <= room * room]
        n = sum((s[0] + a, s[1] + b) in free for a, b in disc)
        # clear all round first: the nearest ground that is not open (a camp's tents stand ~4 squares out)
        clear = min([math.hypot(a, b) for a, b in disc if (s[0] + a, s[1] + b) not in free] or [room + 1.0])
        key = (min(clear, room - 1.0), n - 1.5 * d, -s[0], -s[1])
        if best is None or key > best[0]: best = (key, s)
    s = best[1] if best else (int(near[0]), int(near[1]))
    return (s[0] + 0.5, s[1] - 0.5)


def urchin_camp(spec, rng, land, centre, toward, loot, sleepers=5):
    """Urchins squatting in the open, composed as Westwood furnishes their dens (Con02a, War03c: beds and hammocks of
    one kind side by side, a table ringed by stools, their pickings heaped together) round a fire, open toward
    `toward` (squares: the way in). The beds in a row behind the fire, their feet to it; the table and stools on one
    flank; the pickings on the other: crates side by side, sacks, the hoard's chest (loot), the shaman's place before
    it; stools round the fire; a lookout's stool toward the way in. Returns dict(fire, seats, lookout, chest, goods,
    leader, posts) in world px, as bandit_camp, for kit/posts.camp_posts."""
    rng = own_rng(spec, "urchin_camp", centre)
    fx, fy = square_px(*centre)
    tx, ty = square_px(*toward)
    a_in = math.atan2(ty - fy, tx - fx)
    sc = Camp(spec, rng, land, centre)
    best = None
    for q in range(24):                                   # the back: away from the way in, with room for the beds
        b = -math.pi + q * math.pi / 12
        off_in = abs(_ang(b - a_in))
        if off_in < math.pi * 0.55: continue
        room = sum(sc.free(*sc.p(r, b + d)) for r in (80, 110, 140) for d in (-0.6, -0.3, 0, 0.3, 0.6))
        side = sum(sc.free(*sc.p(r, b + d)) for r in (100, 140) for d in (1.6, -1.6))
        score = room * 2 + side + 2 * math.cos(b + math.pi / 2) + 2 * off_in / math.pi
        if best is None or score > best[0]: best = (score, b)
    b = best[1] if best else a_in + math.pi
    sc.put_px("CampFire", fx, fy)
    ph = rng.uniform(0, 1)
    for q in range(6):
        sc.put_px("CaveRocksSmall", *sc.p(22, ph + q * 2 * math.pi / 6))
    # the beds side by side in a row behind the fire, all one kind, their feet to it; a second row behind if need be
    x0, y0 = sc.p(92, b)
    bed = S.COT_FOOT[S.axis_of(fx - x0, fy - y0)].replace("Cot", "UrchinBed")
    ux, uy = -math.sin(b), math.cos(b)
    per_row = min(sleepers, 4)
    laid = 0
    for row, r in enumerate((92, 128)):
        n = per_row if row == 0 else sleepers - laid
        if n <= 0: break
        x0, y0 = sc.p(r, b)
        for j in range(n):
            o = (j - (n - 1) / 2) * 34
            if sc.put_px(bed, x0 + ux * o, y0 + uy * o, gap=24): laid += 1
    left = 1 if rng.random() < 0.5 else -1
    # the table on one flank, its stools round it
    ta = b + left * 1.45
    tbx, tby = sc.p(100, ta)
    if sc.put_px(rng.choice(("UrchinTableLarge", "UrchinTableSmall")), tbx, tby, gap=30):
        for q in range(rng.randint(3, 4)):
            a = ta + math.pi / 2 + q * 2 * math.pi / 4 + rng.uniform(-0.15, 0.15)
            sc.put_px(rng.choice(("UrchinStool1", "UrchinStool2")), tbx + 26 * math.cos(a), tby + 26 * math.sin(a))
    # the pickings on the other flank: crates side by side, sacks, the hoard's chest before them
    pa = b - left * 1.45
    gx, gy = sc.p(118, pa)
    vx, vy = math.cos(pa + math.pi / 2), math.sin(pa + math.pi / 2)
    line = S.line_of(vx, vy)
    goods = []
    for j in range(rng.randint(2, 3)):
        t = S.ALONG[line][rng.choice(("Crate1", "DarkCrate1"))]
        if sc.put_px(t, gx + vx * (j - 1) * 30, gy + vy * (j - 1) * 30, gap=22): goods.append(t)
    for j in range(2):
        t = rng.choice(SACKS)
        if sc.put_px(t, gx + vx * (60 + 20 * j) - math.cos(pa) * 10, gy + vy * (60 + 20 * j) - math.sin(pa) * 10,
                     gap=18): goods.append(t)
    chest = None
    for r, d in ((80, 0.0), (80, 0.25), (80, -0.25), (70, 0.4), (95, 0.35)):
        chest = sc.put_px("Chest2", *sc.p(r, pa + d), gap=24, items=loot)
        if chest: break
    leader = (sc.stand([sc.p(r, pa + d * left) for r in (62, 74, 86) for d in (0.5, 0.75, 0.3, 1.0)], clear=30) or
              (sc.p(62, pa + 0.5 * left) if chest else sc.p(60, b)))
    # stools round the fire, the way in to it left open
    seats = []
    for a in (b + 0.9, b - 0.9, b + math.pi + 0.7, b + math.pi - 0.7):
        if abs(_ang(a - a_in)) < 0.35: continue
        if sc.put_px(rng.choice(("UrchinStool1", "UrchinStool2")), *sc.p(54, a), gap=22):
            seats.append(sc.p(34, a))
    # the lookout toward the way in
    lookout = None
    for r in (170, 145, 120):
        x, y = sc.p(r, a_in)
        if sc.free(x, y, 30):
            lookout = (x, y)
            sc.put_px(rng.choice(("UrchinStool1", "UrchinStool2")), *sc.p(r + 20, a_in + 0.3), gap=18)
            for q in range(2):
                sc.put_px(rng.choice(("CaveRocksMedium", "CaveRocksSmall")), *sc.p(r + 40, a_in + (q - 0.5) * 0.4))
            break
    if lookout is None: lookout = sc.p(110, a_in)
    posts = [sc.p(100, ta + left * 0.5), sc.p(104, pa - left * 0.6)]
    lx_, ly_ = leader                                               # clear of the stools laid after it
    leader = sc.stand([(lx_ + r * math.cos(k * math.pi / 4), ly_ + r * math.sin(k * math.pi / 4))
                       for r in (0, 18, 32, 46) for k in range(8 if r else 1)], clear=30) or leader
    beds_at = [sc.p(150, b + 0.35), sc.p(150, b - 0.35)]           # behind the bed row, each by his own bed
    _hold_ground(land, centre, 6)
    return dict(fire=(fx, fy), seats=seats[:2], lookout=lookout, chest=chest, goods=goods, leader=leader, posts=posts,
                tents=beds_at, work=[])


def wagon_wreck(spec, rng, land, centre, road_dir):
    """A trader's cart stopped by the road and plundered: a wheel off and lying behind it, its load thrown out in a fan
    from its side away from the road, the heavy things near (crates), the rolling ones further (barrels), the sacks
    slit and dropped between. road_dir: angle (radians, squares) along the road. Returns dict(cart, carter) in world
    px."""
    _replay(rng, "wagon_wreck")
    rng = own_rng(spec, "wagon_wreck", centre)
    sc = Camp(spec, rng, land, centre)            # its pieces keep Westwood's gaps (kit/spacing), thrown or not
    sc.put_px("OutdoorTraderCart", *square_px(sc.ci, sc.cj))
    # the load spills on the side with open ground (thrown against the forest wall, nothing would land)
    free = lambda o: sum(sc.ok(*sc.at(r, o + d)) for r in (1.0, 1.8, 2.4) for d in (-0.6, 0.0, 0.6))
    off = max((road_dir + math.pi / 2, road_dir - math.pi / 2), key=free)
    j = lambda: rng.uniform(-0.12, 0.12)
    sc.put("MineOreCartWheel", *sc.at(1.15, road_dir + math.pi + j()))          # the wheel that came off
    for r, d, kinds in ((1.05, -0.4, CRATES), (1.25, -0.05, CRATES), (1.9, -0.3, ("TraderAppleCrate",)),
                        (1.45, 0.45, SACKS), (1.85, -0.75, SACKS), (2.1, 0.3, BARRELS), (2.7, 0.55, BARRELS),
                        (1.0, 0.95, ("Straw1", "Straw2"))):
        if rng.random() < 0.85 or kinds is CRATES:
            t = rng.choice(kinds)
            p = sc.at(r + j(), off + d + j())
            for dr in (0.0, 0.3, -0.25, 0.55):         # slid a little out or in until it lies clear of the rest
                if sc.put_px(t, *square_px(p[0] + dr * math.cos(off + d), p[1] + dr * math.sin(off + d))): break
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
