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

    def ok(self, si, sj, pad=0.0, walls=True):
        s = (int(math.floor(si)), int(math.floor(sj)) + 1)
        L = self.land
        if s not in L.squares or s in L.roads or s in L.water or s in L.taken_strict: return False
        if not walls: return True
        x, y = square_px(si, sj)                    # never in or against a wall (the forest's or a fence's)
        cx, cy = int(x // 23), int(y // 23)
        return not any((cx + a, cy + b) in self.spec.wallmap for a in (-1, 0, 1) for b in (-1, 0, 1))

    def put(self, t, si, sj, walls=True, **extra):
        if not self.ok(si, sj, walls=walls): return None
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
        # a piece of a known type may stand snug to a wall, its drawn half-width and a margin off the wall's line
        # (kit/spacing.off_walls; Westwood's hideouts stack their barrels and lay their cots against the rock); a bare
        # point keeps a cell clear of every wall
        if t is not None:
            if not self.ok(*_sq(x, y), walls=False) or not SP.off_walls(self.spec.wallmap, t, x, y, margin=12):
                return False
        elif not self.ok(*_sq(x, y)): return False
        if t is not None and not SP.spaced(t, x, y, self.typed): return False
        return all(math.hypot(x - a, y - b) >= gap for a, b in self.mine)

    def put_px(self, t, x, y, gap=0.0, **extra):
        if not self.free(x, y, gap, t): return None
        o = self.put(t, *_sq(x, y), walls=False, **extra)              # free() held it to its walls
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


# Westwood's camps, measured by the scene lab (review/scenelab: 20 campaign camp scenes on Con03A, Con04a, Con05A,
# War03a, War05A, Wiz02C, Wiz03a, Wiz03b, Wiz03c; 2026-10-05): stones ringed 17-30 px round the fire (five to nine,
# a bigger one or two); a seat or two by a fire at most (a stool 59 px out, the ogres' benches); pup tents single,
# standing apart; the cots lie one or two together against the hideout's walls, a torch by them (Wiz03a, Wiz03b), never
# in a block; barrels in twos and threes touching (25-30 px), crates in pairs, against a wall; half a camp's pieces
# within two cells of a wall (the forest's, the cliff's); nearest-piece gap 33 px (tight little clusters, open ground
# between them); a cauldron in one camp, no straw dummies; the men 47-56 px from the fire at most two (War05A's
# grunts), the rest 120-270 px out (Con03A's swordsmen 194-273, its archer 226).
CAMP_R = dict(seat=62, sit=40, cook=54, cot=120, tent=165, store=170, arms=165, lookout=170)
PAIR_GAP = 44          # px between the two bedrolls of a pair: side by side with a gap, not a block (SP.gap's 35)
SLOT = 80              # px between the sleeping row's slots along the back wall (a tent, a pair of bedrolls)


def _snug(sc, x, y, ux, uy, want=44.0, reach=120):
    """Slide a zone's point (x, y) out along (ux, uy) toward the wall behind it, to `want` px from the wall's line, over
    free ground; where no wall lies within `reach` the point stays (Westwood's camps back their beds and stores onto
    their hideout's walls: half their pieces stand within two cells of one). Returns ((x, y), whether a wall was met)."""
    from kit.spacing import wall_clearance
    for d in range(0, int(reach) + 1, 8):
        px_, py_ = x + ux * d, y + uy * d
        if not sc.ok(*_sq(px_, py_), walls=False) or wall_clearance(sc.spec.wallmap, px_, py_, reach=4) < 26: break
        if wall_clearance(sc.spec.wallmap, px_, py_, reach=4) <= want:
            return (px_, py_), True
    return (x, y), False


def bandit_camp(spec, rng, land, centre, toward, loot, sleepers=4, tents=2, trade="bandit", finds=(), hideout=None):
    """A camp in zones with clear ground between them, as Westwood lays its camps (Con03A, Con04a, War05A, Wiz03a,
    Wiz03b), open toward `toward` (squares: where the way in comes from). Greywatch and Starwell playtests, 2026-10-05:
    "a scattered mess. Beds randomly strewn across an open clearing a few random crates placed haphazardly. Give it more
    structure"; "It needs a lot of refinement and a lot more purpose and organization"; "the stumps around the fires in
    bandit camps arent the right object for that use case". The scene lab (review/scenelab) measured Westwood's camps:
    sparse, backed onto their walls, tight little clusters with open ground between (rules/scenes/bandit_camp.md).

    - the hearth: the fire ringed by stones, a crude log bench behind it and a stool to one side (never stumps), the way
      in to it open; a cook pot now and then, off on the store's side;
    - the sleeping row behind the fire, on the side away from the way in and toward the top of the screen, backed onto
      the wall where there is one: the pup tents standing apart, each with its bedrolls before it (head to the tent,
      foot to the fire, two side by side with a gap between); the leader's awning in the middle with three or more;
      the sleepers without a tent in pairs along the back, each pair apart, a torch pole by them;
    - the store on one flank, against the wall: barrels in a little cluster, the crates in a pair beside them, a sack;
      the cart behind now and then;
    - the arms on the other flank (trade "bandit", most camps): a rack or two and a polearm rack side by side against
      the wall; or the dig (trade "dig"): spades and picks left in the ground, the tool barrel, the spoil heaped,
      `finds` set out;
    - the lookout at the way in: a torch pole (the camp's light at its edge), the watchman's stool and his quivers.
    The whole camp scales with its clearing (0.75-1.25 of Westwood's).
    Returns dict(fire, seats (spots for one or two by the fire), lookout, chest, goods, leader, posts (by the store,
    the arms or the dig, and the pot), tents (a spot by each tent or pair of bedrolls), work (at the dig), zones,
    scale): world px."""
    _replay(rng, "bandit_camp")
    # a camp in a pocket of the rock or a ruin's walls is a hideout, laid as Westwood's are (hideout_camp)
    if hideout or (hideout is None and rock_pocket(spec, centre)):
        return hideout_camp(spec, rng, land, centre, toward, loot, sleepers=sleepers)
    rng = own_rng(spec, "bandit_camp", centre)
    fx, fy = square_px(*centre)
    tx, ty = square_px(*toward)
    a_in = math.atan2(ty - fy, tx - fx)
    probe = Camp(spec, rng, land, centre)
    s_ground = max(0.75, min(1.25, _clearing(probe) / 250.0))       # the open ground it holds (as before)
    s = max(0.8, min(1.0, _clearing(probe) / 250.0))        # a big glade does not make a big camp (Westwood's reach
    # p90 162 px, 93-224, whatever the ground round it)
    R = {k: v * (s if k not in ("seat", "sit", "cook") else 1.0) for k, v in CAMP_R.items()}
    R["cot"] = max(R["cot"], 122)
    R["tent"] = max(R["tent"], R["cot"] + 50)
    # the back of the camp: away from the way in, toward the top of the screen where it can, backed onto the wall (the
    # wood's edge, the cliff) 150-300 px behind the fire with room for the beds before it (Westwood's hideouts)
    def dwall(a):
        for r in range(60, 430, 10):
            if not probe.free(*probe.p(r, a)): return r
        return 430
    best = None
    for q in range(24):
        b = -math.pi + q * math.pi / 12
        off_in = abs(_ang(b - a_in))
        if off_in < math.pi * 0.6: continue
        dw = min(dwall(b + d) for d in (-0.25, 0, 0.25))
        if dw < 130: continue
        side = sum(probe.free(*probe.p(r * s, b + d)) for r in (180, 230) for d in (1.75, -1.75))
        score = (6 if dw <= 260 else 0) - 0.02 * abs(dw - 190) + side + 3 * math.cos(b + math.pi / 2) + 2 * off_in / math.pi
        if best is None or score > best[0]: best = (score, b, dw)
    b = best[1] if best else a_in + math.pi
    if best:                                                        # the sleeping row fits before the wall
        R["tent"] = max(125.0, min(R["tent"], best[2] - 40))
        R["cot"] = R["tent"] - 50
    left = 1 if rng.random() < 0.5 else -1                          # the side the store takes
    if abs(_ang(b + left * 1.75 - a_in)) < abs(_ang(b - left * 1.75 - a_in)): left = -left
    sc = Camp(spec, rng, land, centre)
    sc.put_px("CampFire", fx, fy)
    ph = rng.uniform(0, 1)
    n_st = rng.randint(6, 8)
    for q in range(n_st):                                           # stones ringed round the fire
        sc.put_px("CaveRocksSmall", *sc.p(rng.uniform(20, 25), ph + q * 2 * math.pi / n_st))
    for q in range(rng.randint(0, 2)):                              # a bigger stone or two at its back
        sc.put_px("CaveRocksMedium", *sc.p(34, b + (q - 0.5) * 0.9 + rng.uniform(-0.2, 0.2)))
    zones = {"hearth": ((fx, fy), 90.0)}

    def pair(x, y, a, n):
        """n (1-3) bedrolls side by side across the line to the fire at (x, y), PAIR_GAP apart, head away from it: all
        of them or none (a bedroll never lies alone in the open, GW-4)."""
        ux, uy = -math.sin(a), math.cos(a)
        pts = []
        for j in range(n):
            o = (j - (n - 1) / 2) * PAIR_GAP
            px_, py_ = x + ux * o, y + uy * o
            pts.append((S.COT_FOOT[S.axis_of(fx - px_, fy - py_)], px_, py_))
        typed = list(sc.typed)
        for t, px_, py_ in pts:
            if not sc.free(px_, py_, 0, t): sc.typed = typed; return 0
            sc.typed.append((t, px_, py_))
        sc.typed = typed
        return sum(1 for t, px_, py_ in pts if sc.put_px(t, px_, py_))

    # ---- the sleeping row: along the back wall, behind the fire: each tent with its pair of bedrolls beside it, the
    # leader's awning in the middle with three tents or more, the sleepers without a tent in pairs at the row's ends;
    # every bed's head to the wall, its foot to the fire; a torch pole at the row's end; the rocks the camp shelters by
    # at its ends (Westwood's hideouts: cots one or two together against the rock, a torch by them, Wiz03a, Wiz03b)
    # one pup tent to a camp (no Westwood camp pitches two: Con03A, Con04a, Con05A, Con09d, Wiz03b), the leader's
    # awning beside it when the band is big; the other tents' sleepers lie in pairs
    n_t = min(2, max(0, tents)) if tents >= 3 else min(1, max(0, tents))
    lead = 0 if tents >= 3 else None
    per = [sleepers // max(1, n_t) + (1 if q < sleepers % max(1, n_t) else 0) for q in range(n_t)]
    units, spare = [], 0
    # two sleep in the tent and two under the awning (Westwood's war camps lay no bedrolls by their tent: Con03A,
    # Con04a, Con05A); the rest on bedrolls in pairs, a lone one's beside the tent (never alone in the open, GW-4)
    for q in range(n_t):
        units.append(("awning" if q == lead else "tent", 0)); spare += max(0, per[q] - 2)
    spare += max(0, sleepers - sum(per))
    while spare > 1:
        units.append(("pair", 2)); spare -= 2
    if spare:
        units.insert(1 if units and units[0][0] == "tent" else 0, ("pair", 1))
    # the row's slots, left to right along the back: an awning takes two, a tent one and its pair one, a pair one
    slots = []
    for kind, n in units:
        if kind == "awning": slots.append(("awning", 0, 2))
        elif kind == "tent":
            slots.append(("tent", 0, 1))
            if n: slots.append(("pair", n, 1))
        else: slots.append(("pair", n, 1))
    aw = [q for q in slots if q[0] == "awning"]          # the leader's awning in the row's middle, never at its end
    if aw:
        slots.remove(aw[0]); slots.insert(len(slots) // 2, aw[0])
    width = sum(w for _, _, w in slots)
    R_back = R["tent"]
    step = 2 * math.asin(min(1.0, SLOT / (2 * R_back)))
    leader, tent_spots, spare, torch_by = None, [], 0, None
    pos = -(width - 1) / 2
    ends = []
    gaps_ = [rng.uniform(0.85, 1.3) for _ in slots]                # never an even rhythm: each gap its own
    scale_ = width / (sum(g * w for g, (_, _, w) in zip(gaps_, slots)) or 1)      # (no sleepers: no row)
    for (kind, n, w), g in zip(slots, gaps_):
        a = b + (pos + (w * g * scale_ - 1) / 2) * step
        pos += w * g * scale_
        (x, y), _ = _snug(sc, *sc.p(R_back + rng.uniform(-14, 10), a), math.cos(a), math.sin(a), want=44, reach=56)
        ca = math.atan2(y - fy, x - fx)
        if kind == "awning":
            way = "DN" if math.cos(a) < 0 else "UP"
            parts = S.tent_pieces(way, rng.choice(S.TENT_COLOURS[way]), x, y)
            if all(sc.free(px_, py_, 30) for t_, px_, py_ in parts if "Shadow" not in t_):
                for t_, px_, py_ in parts: sc.put(t_, *_sq(px_, py_), walls=False)
                sc.mine += [(px_, py_) for t_, px_, py_ in parts if "Shadow" not in t_]
                leader = (x - math.cos(ca) * 80, y - math.sin(ca) * 80)
                continue
            kind, n = "pair", 2                      # no room for the awning: its two lie on bedrolls
        if kind == "tent":
            for dr in (0, -16, -32, 12):
                tx_, ty_ = x + math.cos(ca) * dr, y + math.sin(ca) * dr
                if sc.put_px("OutdoorTraderPupTent", tx_, ty_, gap=40):
                    tent_spots.append((tx_ - math.cos(ca) * 60, ty_ - math.sin(ca) * 60)); break
            continue
        got = 0
        for dr, da in ((0, 0), (-16, 0), (-32, 0), (0, 0.08), (0, -0.08), (-24, 0.1), (-24, -0.1), (-48, 0)):
            got = pair(x + math.cos(ca) * dr - math.sin(ca) * da * R_back, y + math.sin(ca) * dr + math.cos(ca) * da * R_back,
                       ca, min(3, n))
            if got: break
        spare += n - got
        if got:
            ends.append(a)
            tent_spots.append((x - math.cos(ca) * 52, y - math.sin(ca) * 52))
    a_end = b + (width / 2 + 0.6) * step * (1 if rng.random() < 0.5 else -1)
    torch_by = sc.p(R_back - 20, a_end)
    sc.put_px("TorchPole", *torch_by)
    zones["sleep"] = (sc.p(R_back, b), max(80.0, R_back * step * width / 2 + 40))
    # the rocks it shelters by, at the row's ends, against the wall where there is one (Westwood's camps stand among
    # rocks: 0.40 of their pieces, Wiz03a, Wiz03c, War03a), big stones with smaller ones fallen round them
    big = rng.choice(("CaveRocksHuge", "CaveBoulders"))           # one kind of boulder to a camp
    # (half the camps, at one end only: three stones, not a quarry: the judge, 2026-10-05, "stray props")
    for k, sgn in enumerate(((-1,) if rng.random() < 0.5 else (1,)) if rng.random() < 0.35 else ()):
        a = b + sgn * (width / 2 + 1.2) * step
        (ox, oy), _ = _snug(sc, *sc.p(R_back + 10, a), math.cos(a), math.sin(a), want=40, reach=60)
        ux, uy = -math.sin(a), math.cos(a)
        for t, du, dw in ((big, 0, 0), ("CaveRocksMedium", sgn * 32, -8), ("CaveRocksSmall", rng.uniform(-36, 36), -22)):
            sc.put_px(t, ox + ux * du + math.cos(a) * dw, oy + uy * du + math.sin(a) * dw)
    t_angles = [b]

    # ---- the hearth: a log bench behind the fire, a stool to one side; a cook pot now and then ----------------------
    seats = []
    # (Westwood's camp fires mostly have no seat at all: a stool at Con03A's, benches at Wiz02C's)
    bench = rng.random() < 0.3
    for a, kind, p in ((b, "bench", 1.0 if bench else 0.0), (b + left * 1.35, "stool", 0.0 if bench else 0.4)):
        if rng.random() >= p or abs(_ang(a - a_in)) < 0.5: continue
        x, y = sc.p(R["seat"], a)
        t = _seat(-math.sin(a), math.cos(a)) if kind == "bench" else rng.choice(("Stool1", "Stool2", "Stool3"))
        if sc.put_px(t, x, y):
            seats.append(sc.p(R["sit"], a + (0.35 if kind == "bench" else 0.0)))
    cook = b + left * 2.35
    pot = sc.put_px("Cauldron", *sc.p(R["cook"], cook)) if rng.random() < 0.08 else None
    cook_spot = sc.p(R["cook"] + 34, cook + 0.3 * left) if pot else None

    # ---- the store on one flank, against the wall: barrels clustered, crates in a pair, a sack -------------------------
    st = b + left * 1.75
    (sx, sy), _ = _snug(sc, *sc.p(R["store"] * 0.8, st), math.cos(st), math.sin(st), want=40, reach=80)
    ux, uy = -math.sin(st), math.cos(st)                            # along the wall (tangent to the camp)
    wx, wy = math.cos(st), math.sin(st)                             # out, toward the wall
    line = S.line_of(ux, uy)
    goods = []
    nb = rng.randint(2, 3)
    kinds = [rng.choice(("Barrel", "Barrel2"))] * (nb - 1) + ["WaterBarrel" if rng.random() < 0.2 else "Barrel"]
    kinds[-1] = kinds[0] if kinds[-1] != "WaterBarrel" else kinds[-1]      # one kind of barrel to a camp
    for t, (du, dw) in zip(kinds, ((0, 0), (27, 2), (13, 24))):     # two or three barrels touching, as Westwood stacks
        if sc.put_px(t, sx + ux * du + wx * dw, sy + uy * du + wy * dw): goods.append(t)
    side = 1 if rng.random() < 0.5 else -1
    crate = S.ALONG[line][rng.choice(("Crate1", "DarkCrate1"))]     # one kind of crate
    cr = [(sx + ux * side * (76 + 32 * j) + wx * 4, sy + uy * side * (76 + 32 * j) + wy * 4) for j in range(2)]
    if rng.random() < 0.75 and sc.free(*cr[0], 0, crate) and sc.free(*cr[1], 0, crate) and             math.hypot(cr[0][0] - cr[1][0], cr[0][1] - cr[1][1]) >= SP.gap(crate, crate):
        for x_, y_ in cr:                                           # the crates in a pair beside them, both or none
            if sc.put_px(crate, x_, y_): goods.append(crate)
    if rng.random() < 0.1:
        t = rng.choice(SACKS)
        if sc.put_px(t, sx - ux * side * 40 - wx * 14, sy - uy * side * 40 - wy * 14): goods.append(t)
    if rng.random() < 0.2:
        sc.put_px("OutdoorTraderCart", sx - ux * side * 70 + wx * 30, sy - uy * side * 70 + wy * 30)
    store_spot = (sx - wx * 50, sy - wy * 50)
    zones["store"] = ((sx, sy), 110.0)

    # ---- the arms corner, or the dig, on the other flank ---------------------------------------------------------------
    ar = b - left * 1.75
    (ax, ay), _ = _snug(sc, *sc.p(R["arms"] * 0.8, ar), math.cos(ar), math.sin(ar), want=40, reach=80)
    ux, uy = -math.sin(ar), math.cos(ar)
    wx, wy = math.cos(ar), math.sin(ar)
    work = []
    arms_spot = None
    if trade == "dig":
        tools = [("BarrelWithTools1", {}), ("MiningShovelInGround", {}), ("MiningPickAxeInGround1", {}),
                 ("MiningShovelInGround", {})]
        sc.row(tools, ax, ay, ux, uy)
        for k in range(3):                                           # the spoil, heaped behind the tools
            sc.put_px(("CaveRocksLarge", "CaveRocksMedium", "CaveRocksMedium")[k],
                      ax + wx * 40 + ux * (k - 1) * 28, ay + wy * 40 + uy * (k - 1) * 28)
        for t, (du, dw) in zip(finds[:2], ((-13, 4), (13, 4))):    # what they dig for, by the spoil (never mid-glade)
            sc.put_px(t, ax + wx * (40 + dw) + ux * (du + 70), ay + wy * (40 + dw) + uy * (du + 70))
        work = [(ax - wx * 30 - ux * 70, ay - wy * 30 - uy * 70), (ax - wx * 30 + ux * 70, ay - wy * 30 + uy * 70)]
    elif rng.random() < 0.6:
        # the arms as Westwood's war camps stand them (Con03A, Con04a, Con05A, Con09d): three or four armour racks of
        # different builds in a row, the helmet poles at its end now and then, or a polearm rack
        builds = rng.sample(("OutdoorTraderArmorRack1", "OutdoorTraderArmorRack2", "OutdoorTraderArmorRack3",
                             "OutdoorTraderArmorRack4"), rng.randint(2, 4))
        racks = [(t, {}) for t in builds]
        q = rng.random()
        if q < 0.3: racks.append(("OutdoorTraderHelmPoles", {}))
        elif q < 0.42: racks.append((S.ALONG[S.line_of(ux, uy)][rng.choice(("TraderPoleArm1", "TraderPoleArm2"))], {}))
        sc.row(racks, ax, ay, ux, uy)
        arms_spot = (ax - wx * 44 + ux * 40, ay - wy * 44 + uy * 40)
    zones["arms"] = ((ax, ay), 100.0)

    # ---- the lookout at the way in: the torch pole, the watchman's stool, his quivers ---------------------------------
    lookout = None
    for r, d in [(r, d) for r in (R["lookout"], R["lookout"] - 30, R["lookout"] - 60, 210, 180) for d in (0, 0.25, -0.25)]:
        a = a_in + d
        x, y = sc.p(r, a)
        ux, uy = -math.sin(a), math.cos(a)
        set_ = [("TorchPole", x + ux * 16 + math.cos(a) * 34, y + uy * 16 + math.sin(a) * 34),
                (rng.choice(("Stool1", "Stool2")), x - math.cos(a) * 30, y - math.sin(a) * 30),       # (rarely)
                ("TraderQuiverRack", x - ux * 22 + math.cos(a) * 34, y - uy * 22 + math.sin(a) * 34)]
        if sc.free(x, y, 40) and all(sc.free(px_, py_, 0, t_) for t_, px_, py_ in set_[:2]):
            lookout = (x, y)
            sit, quiver = rng.random() < 0.1, rng.random() < 0.15      # mostly the watch stands, his bow in hand
            for t_, px_, py_ in set_:
                if (sit or not t_.startswith("Stool")) and (quiver or "Quiver" not in t_): sc.put_px(t_, px_, py_)
            break
    if lookout is None: lookout = sc.p(R["lookout"] * 0.8, a_in)
    zones["lookout"] = (lookout, 60.0)

    # ---- the take: the chest before the leader's tent, the stolen goods beside it --------------------------------------
    chest = None
    # (the take keeps off the fire's bench: at the sleeping row's end, by the leader's bed)
    ca = b
    e_ = (width / 2 + 0.4) * step
    for r, d in ((R["tent"] - 46, e_), (R["tent"] - 46, -e_), (R["tent"] - 60, e_ + 0.15), (R["tent"] - 60, -e_ - 0.15),
                 (R["tent"] - 70, 0.4), (R["tent"] - 70, -0.4), (R["cot"] - 30, 0.6), (R["cot"] - 30, -0.6)):
        chest = sc.put_px("Chest3", *sc.p(r, ca + d), items=loot)
        if chest:
            if n_t >= 3 and sc.put_px("TraderAppleCrate", *sc.p(r + 4, ca + d + math.copysign(0.2, d or 1))):
                goods.append("TraderAppleCrate")
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
    _hold_ground(land, centre, int(round(6 * s_ground)))      # the hearth's ground; the wood may come up to the beds
    return dict(fire=(fx, fy), seats=seats, lookout=lookout, chest=chest, goods=goods, leader=leader, posts=posts,
                tents=tent_spots, work=work, zones=zones, scale=s)


# ---------------------------------------------------------------------------------------------------- the hideout
# Westwood's hideouts (the scene lab, 2026-10-06: Wiz03a x3, Wiz03b x4, Wiz03c, War03a x2: half its camp evidence):
# a pocket of CaveWall2 on DirtDark2 off a cave's passage, nothing in its middle; every piece against the rock (px from
# the wall's line: the wall torches 1-16, rocks and pillars 5-25, barrels 13-46, crates 15-44, cots 20-48); one or two
# cots together (heads to the rock), a torch on the wall by them; barrels in a knot of two to four, a crate or two by
# them; big rocks and a pillar where the rock juts; a fire in half of them (CampFire ringed by stones, or a cold one),
# well off the walls (50-146 px); a table and chairs now and then (Wiz03a, Wiz03b); a few loose stones on the floor.
ROCK_WALL = ("CaveWall", "ManaMineWall", "Volcano", "IceWall", "Dirt", "RockWall")
RUIN_WALL = ("Cobblestone", "DungeonStone", "StoneWall", "GalavaTownWall", "BrickPlain", "Brick")
HIDE_OFF = dict(Torch=9, rock=14, pillar=12, barrel=22, crate=24, cot=31, chest=26, stone=40)


def rock_pocket(spec, centre, reach=330, rays=16, need=11):
    """Whether the ground round `centre` (squares) is a pocket in the rock (or a ruin's walls): `need` of `rays` rays
    from it meet a cave's or a ruin's wall within `reach` px. A forest's edge, a fence or a house is not one."""
    fx, fy = square_px(*centre)
    hit = 0
    for k in range(rays):
        a = k * 2 * math.pi / rays
        for r in range(20, reach, 12):
            c = (int((fx + r * math.cos(a)) // 23), int((fy + r * math.sin(a)) // 23))
            w = spec.wallmap.get(c)
            if w:
                if w["material"].startswith(ROCK_WALL + RUIN_WALL): hit += 1
                break
    return hit >= need


def _hide_fam(t):
    """A hideout piece's family, for its clearance from the rock (HIDE_OFF)."""
    if t == "Torch": return "Torch"
    if t.startswith("Cot"): return "cot"
    if "Barrel" in t: return "barrel"
    if "Crate" in t: return "crate"
    if "Pillar" in t: return "pillar"
    if t.startswith("Chest"): return "chest"
    if t.startswith(("Rock", "CaveRocksSmall")): return "stone"
    return "rock"


class Pocket:
    """A pocket in the rock (a hideout, a den) read by rays from its middle: where the rock is in each of N directions,
    the mouth (toward `toward`, or where no rock closes it), points a given clearance off the rock, rows along it.
    `off(t)`: the clearance (px from the wall's line) a piece of type t keeps. Directions are claimed as zones take
    them, so two zones never share a stretch of rock."""
    N = 48

    def __init__(self, spec, rng, land, centre, toward, off):
        from kit.spacing import wall_clearance
        self.spec, self.rng, self.off, self.clear = spec, rng, off, wall_clearance
        self.sc = Camp(spec, rng, land, centre)
        self.cx, self.cy = square_px(*centre)
        tx, ty = square_px(*toward)
        ends = [self.ray_end(self.A(k)) for k in range(self.N)]
        # the pocket's middle: halfway to the mean of the rays' ends (a camp_site square may sit off it)
        mx = sum(self.cx + min(e, 300) * math.cos(self.A(k)) for k, e in enumerate(ends)) / self.N
        my = sum(self.cy + min(e, 300) * math.sin(self.A(k)) for k, e in enumerate(ends)) / self.N
        if self.sc.ok(*_sq((self.cx + mx) / 2, (self.cy + my) / 2)):
            self.cx, self.cy = (self.cx + mx) / 2, (self.cy + my) / 2
        self.sc.fx, self.sc.fy = self.cx, self.cy
        self.a_in = math.atan2(ty - self.cy, tx - self.cx)
        self.ends = [self.ray_end(self.A(k)) for k in range(self.N)]
        self.mouth = {k for k in range(self.N) if abs(_ang(self.A(k) - self.a_in)) < 0.55 or self.ends[k] >= 400}
        self.used = set(self.mouth)

    def A(self, k):
        return k * 2 * math.pi / self.N

    def ray_end(self, a, cap=420):
        for r in range(12, cap, 6):
            x, y = self.cx + r * math.cos(a), self.cy + r * math.sin(a)
            if not self.sc.ok(*_sq(x, y), walls=False) or self.clear(self.spec.wallmap, x, y, reach=3) < 8: return r
        return cap

    def wall_pt(self, a, off):
        """The point on ray a whose clearance from the rock is about `off` px (None: no rock that way)."""
        e = self.ray_end(a)
        if e >= 400: return None
        for r in range(e, 10, -3):
            x, y = self.cx + r * math.cos(a), self.cy + r * math.sin(a)
            if self.clear(self.spec.wallmap, x, y, reach=4) >= off and self.sc.ok(*_sq(x, y), walls=False): return (x, y)
        return None

    def can(self, t, x, y, gap=0.0, also=()):
        sc = self.sc
        return (sc.ok(*_sq(x, y), walls=False) and self.clear(self.spec.wallmap, x, y, reach=4) >= self.off(t) - 6
                and SP.spaced(t, x, y, list(sc.typed) + list(also))
                and not any(math.hypot(x - a, y - b) < gap for a, b in sc.mine))

    def put(self, t, x, y, gap=0.0, **extra):
        if not self.can(t, x, y, gap): return None
        o = self.sc.put(t, *_sq(x, y), walls=False, **extra)
        if o is not None:
            self.sc.mine.append((x, y)); self.sc.typed.append((t, x, y))
        return o

    def claim(self, k0, w):
        for d in range(-w, w + 1): self.used.add((k0 + d) % self.N)

    def free_k(self, k0, w):
        return all((k0 + d) % self.N not in self.used and self.ends[(k0 + d) % self.N] < 400 for d in range(-w, w + 1))

    def along(self, k0, step, off, n, sgn=1, jitter=4.0, most=999.0):
        """n points along the rock from ray k0 in direction sgn, each about `step` px from the one before (never more
        than `most`), `off` px off the rock: [(k, (x, y))]; fewer where the rock turns away (the mouth) or a ray is
        taken."""
        out, k, near = [], k0, None
        for _ in range(self.N):
            if len(out) >= n or k % self.N in self.used: break
            q = self.wall_pt(self.A(k), off + self.rng.uniform(-jitter, jitter))
            if q and not out: out.append((k % self.N, q))
            elif q:
                d = math.hypot(q[0] - out[-1][1][0], q[1] - out[-1][1][1])
                if d > most:                                         # past the step: the nearest that fell short
                    if near is None: break
                    out.append(near); near = None
                    if len(out) >= n: break
                    d = math.hypot(q[0] - out[-1][1][0], q[1] - out[-1][1][1])
                if d >= step: out.append((k % self.N, q)); near = None
                elif d >= 0.8 * step: near = (k % self.N, q)
            k += sgn
        return out


def hideout_camp(spec, rng, land, centre, toward, loot, sleepers=4):
    """A band's hideout in a pocket of the rock (or a ruined room), laid as Westwood lays its own (the notes above),
    open toward `toward` (squares: the mouth). Its own generator. Returns the record bandit_camp returns (fire, seats,
    lookout, chest, goods, leader, posts, tents, work, zones, scale), for kit/posts.camp_posts."""
    from kit.spacing import wall_clearance
    rng = own_rng(spec, "hideout", centre)
    P = Pocket(spec, rng, land, centre, toward, lambda t: HIDE_OFF.get(_hide_fam(t), 20))
    sc, cx, cy, a_in, N, A, ends, mouth, used = P.sc, P.cx, P.cy, P.a_in, P.N, P.A, P.ends, P.mouth, P.used
    ray_end, wall_pt, can, put, claim, free_k, along = P.ray_end, P.wall_pt, P.can, P.put, P.claim, P.free_k, P.along
    b = a_in + math.pi
    order = sorted(range(N), key=lambda k: abs(_ang(A(k) - b)))
    zones, goods, posts = {}, [], []

    # ---- the beds: cots two (or three) together against the back rock, heads to it, a wall torch by each group
    n_cots = max(2, min(4, sleepers - rng.choice((1, 1, 2))))     # (Westwood's hideouts: two to five cots)
    groups = [2] * (n_cots // 2)
    if n_cots % 2: groups[-1] += 1
    cot_spots = []
    k_start = min(order[:6], key=lambda k: ends[k])                 # the back, where the rock is nearest
    sgn = rng.choice((1, -1))
    for gi, g in enumerate(groups):
        if gi == 1: sgn = -sgn                                      # the second group the other way from the first
        k0 = next((k for k in ([k_start] + [(k_start + sgn * d) % N for d in range(1, N // 3)]) if free_k(k, 1)), None)
        if k0 is None: break
        pts = along(k0, 58 + rng.uniform(0, 8), HIDE_OFF["cot"] + rng.uniform(-2, 6), g, sgn, most=74)
        if len(pts) < 2: continue
        laid, plan = [], []
        for k, p in pts:
            t = S.COT_FOOT[S.axis_of(cx - p[0], cy - p[1])]
            if can(t, *p, also=plan): plan.append((t, p[0], p[1]))
            else: break
        if len(plan) < 2: continue                                   # all of a group or none
        for (k, p), (t, _, _) in zip(pts, plan):
            if put(t, *p): laid.append((k, p))
        if len(laid) < 2:                                           # never a cot alone (GW-4)
            continue
        for k, p in laid:
            L = math.hypot(cx - p[0], cy - p[1]) or 1
            cot_spots.append((p[0] + (cx - p[0]) / L * 58, p[1] + (cy - p[1]) / L * 58))
        ks = [k for k, _ in laid]
        for k in ks: claim(k, 1)
        k_end = ks[-1] + sgn * 3                                    # the torch on the rock beyond them
        q = wall_pt(A(k_end), HIDE_OFF["Torch"] + rng.uniform(-2, 3))
        if q and put("Torch", *q): claim(k_end, 1)
        if gi == 0: k_start = (ks[0] - sgn * rng.randint(4, 7)) % N      # the next group apart, rock between
    zones["sleep"] = ((cx + math.cos(b) * 120, cy + math.sin(b) * 120), 120.0)

    # ---- the store: barrels in a knot against the rock on a flank, a crate or two by them
    side = 1 if rng.random() < 0.5 else -1
    flank = sorted(range(N), key=lambda k: abs(_ang(A(k) - (b + side * 1.6))))
    k0 = next((k for k in flank if free_k(k, 3)), None)
    if k0 is None: k0 = next((k for k in flank if free_k(k, 1)), None)
    store_spot = None
    if k0 is not None:
        bk = rng.choice(("Barrel", "Barrel", "Barrel2"))
        kinds = [bk] * rng.randint(2, 4)
        if rng.random() < 0.25: kinds[-1] = "WaterBarrel"
        if rng.random() < 0.2: kinds[0] = "BarrelSteel1"
        row = along(k0, 26, HIDE_OFF["barrel"], 2, side, jitter=3)    # two against the rock, the rest before them
        laid = []
        for (k, q), t in zip(row, kinds):
            if put(t, *q): laid.append((k, q)); goods.append(t)
        if len(laid) >= 2:                                          # the third (and fourth) before them, a knot
            (_, q1), (_, q2) = laid[0], laid[1]
            ux_, uy_ = (q2[0] - q1[0]) / 26.0, (q2[1] - q1[1]) / 26.0
            mx_, my_ = (q1[0] + q2[0]) / 2, (q1[1] + q2[1]) / 2
            L = math.hypot(cx - mx_, cy - my_) or 1
            for t, du in zip(kinds[2:], (rng.choice((-1, 1)) * 13 * rng.uniform(0.6, 1.0), 26)):
                if put(t, mx_ + (cx - mx_) / L * 22 + ux_ * du, my_ + (cy - my_) / L * 22 + uy_ * du): goods.append(t)
        if laid:
            crate = rng.choice(("Crate2", "DarkCrate2", "CrateSteel2", "Crate1", "DarkCrate1"))
            a = A(laid[-1][0])
            crate = S.ALONG[S.line_of(-math.sin(a), math.cos(a))].get(crate, crate)
            for k in range(laid[0][0] - side, laid[-1][0] + side, side): used.add(k % N)
            got = along((laid[-1][0] + side * 2) % N, 34, HIDE_OFF["crate"] + 4, rng.choice((1, 1, 2)), side, jitter=4)
            for k, q in got:
                if put(crate, *q): goods.append(crate); claim(k, 1)
            p = laid[0][1]
            claim(laid[0][0], 2)
            L = math.hypot(cx - p[0], cy - p[1]) or 1
            store_spot = (p[0] + (cx - p[0]) / L * 52, p[1] + (cy - p[1]) / L * 52)
            zones["store"] = (p, 90.0)

    # ---- the rock: a big rock or a pillar where the rock juts, a smaller stone fallen by it (one to three places)
    big = rng.choice(("CaveRocksHuge", "CaveRocksHuge", "CaveBoulders"))
    for _ in range(rng.choice((2, 2, 3, 3))):      # (Westwood's hideouts: rock 0.40 of their pieces)
        ks = [k for k in range(N) if free_k(k, 1)]
        if not ks: break
        k0 = min(ks, key=lambda k: ends[k] + rng.uniform(0, 60))        # where the rock comes in nearest
        t = big if rng.random() < 0.6 else rng.choice(("CaveRockPillarTall1", "CaveRockPillarShort1", "CaveRockPillarTall2"))
        p = wall_pt(A(k0), HIDE_OFF["pillar" if "Pillar" in t else "rock"])
        if p and put(t, *p):
            for j in range(rng.choice((1, 2, 2))):                     # smaller stones fallen by it
                q = wall_pt(A(k0) + rng.choice((1, -1)) * (30 + 18 * j) / max(80, ends[k0]), 18 + 14 * j)
                if q: put(rng.choice(("CaveRocksMedium", "CaveRocksSmall", "CaveRocksLarge")), *q)
        claim(k0, 2)

    # ---- the hearth (half the hideouts): the fire well off the rock, stones round it; or a cold one
    fire, seats = None, []
    q = rng.random()
    if q < 0.7:
        cold = q >= 0.55
        for r, d in ((0, 0), (30, 0), (30, 1.6), (30, -1.6), (50, 3.1), (50, 0.8), (50, -0.8)):
            x, y = cx + r * math.cos(b + d), cy + r * math.sin(b + d)
            if wall_clearance(spec.wallmap, x, y, reach=5) >= 70 and \
                    put("CampFireUnused" if cold else "CampFire", x, y, gap=56):
                fire = (x, y)
                break
        if fire and not cold:
            ph, n = rng.uniform(0, 6.3), rng.randint(5, 8)
            for j in range(n):
                put("CaveRocksSmall", fire[0] + 22 * math.cos(ph + j * 2 * math.pi / n),
                    fire[1] + 22 * math.sin(ph + j * 2 * math.pi / n))
            if rng.random() < 0.3:
                for j in range(rng.randint(2, 4)):
                    a = rng.uniform(0, 6.3)
                    put(rng.choice(BONES), fire[0] + 40 * math.cos(a), fire[1] + 40 * math.sin(a))
    # ---- a table and chairs on the other flank now and then (Wiz03a, Wiz03b: the hideout's own furniture)
    if rng.random() < 0.2:
        fl = sorted(range(N), key=lambda k: abs(_ang(A(k) - (b - side * 1.5))))
        k0 = next((k for k in fl if free_k(k, 3)), None)
        if k0 is not None:
            p = wall_pt(A(k0), 52)
            if p and put(rng.choice(("RoundTable3", "OvalTable2", "RoundTable1")), *p):
                ux, uy = -math.sin(A(k0)), math.cos(A(k0))
                for s_ in (1, -1):
                    put(rng.choice(("WoodenChair1", "WoodenChair2", "WoodenChair3", "WoodenChair4")),
                        p[0] + ux * s_ * 34, p[1] + uy * s_ * 34)
                seats.append((p[0] - math.cos(A(k0)) * 40, p[1] - math.sin(A(k0)) * 40))
                claim(k0, 3)
    # ---- the take: the chest against the rock by the beds
    chest = None
    for k in order:
        if k in used or abs(_ang(A(k) - b)) > 2.2: continue
        p = wall_pt(A(k), HIDE_OFF["chest"])
        if p:
            chest = put("Chest3", *p, items=loot)
            if chest: claim(k, 2); break
    # ---- a third torch on the rock now and then, loose stones on the floor
    if rng.random() < 0.5:
        ks = [k for k in range(N) if free_k(k, 1)]
        if ks:
            p = wall_pt(A(rng.choice(ks)), HIDE_OFF["Torch"])
            if p: put("Torch", *p)
    for _ in range(rng.choice((0, 0, 2, 3, 4))):
        a, r = rng.uniform(0, 6.3), rng.uniform(40, 150)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        if wall_clearance(spec.wallmap, x, y, reach=4) >= 30: put(rng.choice(("Rock5", "Rock6", "Rock7")), x, y, gap=30)

    def spot(p):
        ring = [(p[0] + r * math.cos(k * math.pi / 4), p[1] + r * math.sin(k * math.pi / 4)) for r in (20, 36) for k in range(8)]
        return sc.stand([p] + ring, clear=32) or p
    if fire:
        seats += [(fire[0] + 50 * math.cos(b + d), fire[1] + 50 * math.sin(b + d)) for d in (1.2, -1.2)]
    # the watch inside the mouth, the leader by the take
    e_in = ray_end(a_in, 300)
    lookout = spot((cx + math.cos(a_in) * max(60, min(160, e_in - 40)), cy + math.sin(a_in) * max(60, min(160, e_in - 40))))
    if chest:
        L = math.hypot(cx - chest["x"], cy - chest["y"]) or 1
        leader = spot((chest["x"] + (cx - chest["x"]) / L * 50, chest["y"] + (cy - chest["y"]) / L * 50))
    else:
        leader = spot((cx + math.cos(b) * 70, cy + math.sin(b) * 70))
    if store_spot: posts.append(spot(store_spot))
    zones["hearth"] = (fire or (cx, cy), 80.0)
    zones["lookout"] = (lookout, 60.0)
    _hold_ground(land, centre, 5)
    return dict(fire=fire or (cx, cy), seats=seats, lookout=lookout, chest=chest, goods=goods, leader=leader,
                posts=posts, tents=[spot(p) for p in cot_spots], work=[], zones=zones, scale=1.0, hideout=True)


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
    # bones dropped round the pit, close (Con05B: 40-75 px out)
    for k in range(rng.randint(4, 7)):
        a = rng.uniform(-math.pi, math.pi)
        if abs(_ang(a - a_in)) < 0.4: continue
        sc.put_px(rng.choice(BONES), *sc.p(rng.uniform(40, 75), a), gap=14)
    # ---- the sleeping row: straw bedding side by side in an arc behind the fire --------------------------------------
    # (Westwood's ogres sleep in their huts: an open camp's bedding is a heap or two of straw, not a row: the lab's
    # Westwood ogre camps hold no straw by the fire)
    n = rng.choice((0, 1, 2)) if rng.random() < 0.5 else 0
    step = 46.0 / R["straw"]
    beds_at = []
    for q in range(n):
        a = b + (q - (n - 1) / 2) * step * (1 if q % 2 == 0 else 1)
        if sc.put_px(rng.choice(("OgreStraw1", "OgreStraw1", "OgreStraw2", "OgreStraw3")), *sc.p(R["straw"], a), gap=34):
            beds_at.append(sc.p(R["straw"] - 42, a + 0.18))
    zones["sleep"] = (sc.p(R["straw"], b), 40.0 + n * 23)
    # the take: the warlord's bearskin and his chest behind the bedding's middle
    chest = None
    rug = sc.put_px(rng.choice(("OgreBearskin1", "OgreBearskin3")), *sc.p(R["back"] + 18, b), gap=40) \
        if rng.random() < 0.3 else None                # (Westwood's bearskins lie in the huts)
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
    stock = [("Barrel", {}), ("OgreSack1", {}), ("Barrel2", {}), ("OgreSack2", {}), ("Barrel", {})][:rng.randint(2, 4)]
    goods += [t for t, _, _ in sc.row(stock, sx, sy, ux, uy)]
    if rng.random() < 0.5 and sc.put_px("OgreHutCarcassBig", sx + wx * 46 + ux * 40, sy + wy * 46 + uy * 40, gap=30):
        goods.append("OgreHutCarcassBig")
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
    gate = rng.random() < 0.4                     # (none of the lab's five Westwood ogre fires has a tusk gate by it)
    for side in ((1, -1) if gate else ()):
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
        # clear all round first: the nearest ground that is not open (a camp's tents stand ~4 squares out); then the
        # site whose nearest wall is no further than that: a camp backs onto the wood's edge or the cliff, as
        # Westwood's hideouts do (the scene lab: half their pieces within two cells of a wall), never in the middle
        # of a wide glade with open ground all round
        clear = min([math.hypot(a, b) for a, b in disc if (s[0] + a, s[1] + b) not in free] or [room + 1.0])
        # (5 squares: the camp's back row ~165 px out, kit/camps CAMP_R; a bigger clearing leaves the camp in a
        # half-empty glade, the blind judge 2026-10-05)
        key = (min(clear, room - 1.0, 5.0), -round(clear), n - 1.5 * d, -s[0], -s[1])
        if best is None or key > best[0]: best = (key, s)
    s = best[1] if best else (int(near[0]), int(near[1]))
    return (s[0] + 0.5, s[1] - 0.5)


# Westwood's urchin dens (the scene lab, 2026-10-06: 42 campaign scenes on Con02a, War03c, War03d, Wiz01A): pockets of
# Dirt walls on DirtDark2, every bed and shelf against the earth (px from the wall's line: paintings and scrolls 2-4,
# wall torches 6-11, shelves 13-23, beds and hammocks 22-32, chests 21-46, barrels 21-32), a round table ringed by
# stools in the open (45-120); the variant of a bed, shelf, painting or chest by where the wall stands from it (a bed:
# wall up-left UrchinBed1, up-right 2, down-right 3, down-left 4; a shelf, painting or hammock by its wall's line).
DEN_OFF = dict(bed=27, hammock=27, shelf=17, painting=3, scroll=3, Torch=9, chest=26, barrel=24, table=60, stool=40,
               straw=30)


def _den_fam(t):
    for k, f in (("UrchinBed", "bed"), ("UrchinHammock", "hammock"), ("Shelves", "shelf"), ("Painting", "painting"),
                 ("Scroll", "scroll"), ("Torch", "Torch"), ("Chest", "chest"), ("Barrel", "barrel"),
                 ("Table", "table"), ("Stool", "stool"), ("Straw", "straw")):
        if k in t: return f
    return "barrel"


def _wall_side(a):
    """Where the wall stands from a piece laid on ray a against the rock: (up, left) as booleans."""
    return math.sin(a) < 0, math.cos(a) < 0


def urchin_den(spec, rng, land, centre, toward, loot, sleepers=5):
    """Urchins' den in a pocket of the earth, laid as Westwood lays its own (the notes above), open toward `toward`
    (squares: the mouth). Its own generator. Returns the record urchin_camp returns, for kit/posts.camp_posts."""
    rng = own_rng(spec, "urchin_den", centre)
    P = Pocket(spec, rng, land, centre, toward, lambda t: DEN_OFF.get(_den_fam(t), 24))
    cx, cy, N, A = P.cx, P.cy, P.N, P.A
    b = P.a_in + math.pi
    order = sorted(range(N), key=lambda k: abs(_ang(A(k) - b)))
    upper = [k for k in order if math.sin(A(k)) < -0.2]          # the walls the camera sees: shelves, pictures

    def bed_of(a, hammock):
        up, left = _wall_side(a)
        if hammock: return "UrchinHammock2" if up == left else "UrchinHammock1"      # "/" walls (up-left, down-right)
        return {(True, True): "UrchinBed1", (True, False): "UrchinBed2", (False, False): "UrchinBed3",
                (False, True): "UrchinBed4"}[(up, left)]

    # ---- the beds: of one kind, side by side along the rock in twos and threes
    hammocks = rng.random() < 0.3
    n_beds = max(2, min(7, sleepers + rng.choice((0, 1, 1, 2))))
    groups, left_ = [], n_beds
    while left_ > 0:
        g = min(left_, rng.choice((2, 2, 3)))
        if left_ - g == 1: g += 1
        groups.append(g); left_ -= g
    beds = []
    k_start, sgn = order[0], rng.choice((1, -1))
    for gi, g in enumerate(groups):
        if gi % 2 == 1: sgn = -sgn
        k0 = next((k for k in [k_start] + [(k_start + sgn * d) % N for d in range(1, N // 3)] if P.free_k(k, 1)), None)
        if k0 is None: break
        pts = P.along(k0, 42 + rng.uniform(0, 6), DEN_OFF["bed"] + rng.uniform(-3, 4), g, sgn, most=64)
        plan = []
        for k, p in pts:
            t = bed_of(A(k), hammocks)
            if P.can(t, *p, also=plan): plan.append((t, p[0], p[1]))
            else: break
        if len(plan) < 2: continue
        for (k, p), (t, _, _) in zip(pts, plan):
            if P.put(t, *p): beds.append((k, p)); P.claim(k, 1)
        k_start = (pts[0][0] - sgn * rng.randint(4, 6)) % N
    # ---- the shelves of the den's stores on the upper walls, a picture or a hanging between them
    log = rng.random() < 0.4

    def shelf_of(a):
        up, left = _wall_side(a)
        t = (("LogShelvesFull3" if left else "LogShelvesFull4") if log else
             ("UrchinShelvesFull2" if up == left else "UrchinShelvesFull1"))
        return t.replace("Full", "Empty") if rng.random() < 0.15 else t
    for _ in range(rng.choice((1, 2, 2))):        # shelves two or three side by side along the upper rock
        k = next((k for k in upper if P.free_k(k, 1)), None)
        if k is None: break
        got = 0
        for kk, p in P.along(k, 26, DEN_OFF["shelf"], rng.choice((2, 2, 3)), rng.choice((1, -1)), jitter=3, most=40):
            if P.put(shelf_of(A(kk)), *p): got += 1; P.claim(kk, 1)
        P.claim(k, 1 if got else 0)
    for _ in range(rng.choice((2, 3, 3, 4))):
        k = next((k for k in upper[rng.randint(0, 3):] if P.free_k(k, 0)), None)
        if k is None: break
        up, left = _wall_side(A(k))
        t = (("UrchinPainting2" if left else "UrchinPainting1") if rng.random() < 0.7 else
             ("UrchinHangingScroll1" if rng.random() < 0.5 else "UrchinHangingScroll2"))
        p = P.wall_pt(A(k), DEN_OFF["painting"])
        if p and P.put(t, *p): P.claim(k, 1)
        else: P.claim(k, 0)
    # ---- the wall torches
    for _ in range(rng.choice((2, 2, 3))):
        ks = [k for k in range(N) if P.free_k(k, 1)]
        if not ks: break
        k = rng.choice(ks)
        p = P.wall_pt(A(k), DEN_OFF["Torch"])
        if p and P.put("Torch", *p): P.claim(k, 2)
        else: P.claim(k, 0)
    # ---- the hoard: the chest against the upper rock, barrels in a knot now and then
    chest = None
    for k in upper:
        if not P.free_k(k, 1): continue
        up, left = _wall_side(A(k))
        p = P.wall_pt(A(k), DEN_OFF["chest"])
        if p:
            chest = P.put("ChestUrchin4" if left else "ChestUrchin3", *p, items=loot)
            if chest: P.claim(k, 2); break
    goods = []
    if rng.random() < 0.5:
        k0 = next((k for k in reversed(order) if P.free_k(k, 2) and k not in P.mouth), None)
        if k0 is not None:
            bk = rng.choice(("Barrel", "Barrel2"))
            for k, q in P.along(k0, 26, DEN_OFF["barrel"], rng.randint(2, 3), rng.choice((1, -1)), jitter=3):
                if P.put(bk, *q): goods.append(bk); P.claim(k, 1)
    # ---- the table in the open, stools round it
    table, seats = None, []
    for r, d in ((0, 0), (40, 1.0), (40, -1.0), (60, 2.4), (60, -2.4), (30, 3.1)) if rng.random() < 0.65 else ():
        x, y = cx + r * math.cos(b + d), cy + r * math.sin(b + d)
        t = "UrchinTableLarge" if rng.random() < 0.75 else "UrchinTableSmall"
        if P.can(t, x, y, gap=50) and P.put(t, x, y):
            table = (x, y)
            ph, n = rng.uniform(0, 6.3), rng.randint(2, 4)
            for j in range(n):
                a = ph + j * 2 * math.pi / n + rng.uniform(-0.2, 0.2)
                P.put(rng.choice(("UrchinStool1", "UrchinStool2")), x + 36 * math.cos(a), y + 36 * math.sin(a))
            seats = [(x + 60 * math.cos(ph + 0.5), y + 60 * math.sin(ph + 0.5))]
            break
    if rng.random() < 0.3:
        for _ in range(rng.randint(1, 2)):
            a, r = rng.uniform(0, 6.3), rng.uniform(60, 140)
            P.put(rng.choice(("Straw1", "Straw2")), cx + r * math.cos(a), cy + r * math.sin(a), gap=30)
    sc = P.sc

    def spot(p):
        ring = [(p[0] + r * math.cos(k * math.pi / 4), p[1] + r * math.sin(k * math.pi / 4)) for r in (20, 36) for k in range(8)]
        return sc.stand([p] + ring, clear=32) or p
    e_in = P.ray_end(P.a_in, 300)
    lookout = spot((cx + math.cos(P.a_in) * max(60, min(150, e_in - 40)), cy + math.sin(P.a_in) * max(60, min(150, e_in - 40))))
    if chest:
        L = math.hypot(cx - chest["x"], cy - chest["y"]) or 1
        leader = spot((chest["x"] + (cx - chest["x"]) / L * 50, chest["y"] + (cy - chest["y"]) / L * 50))
    else:
        leader = spot((cx + math.cos(b) * 70, cy + math.sin(b) * 70))
    tents = []
    for k, p in beds:
        L = math.hypot(cx - p[0], cy - p[1]) or 1
        tents.append(spot((p[0] + (cx - p[0]) / L * 50, p[1] + (cy - p[1]) / L * 50)))
    _hold_ground(land, centre, 4)
    centre_px = table or (cx, cy)
    return dict(fire=centre_px, seats=seats, lookout=lookout, chest=chest, goods=goods, leader=leader, posts=[],
                tents=tents, work=[], zones={"hearth": (centre_px, 80.0)}, scale=1.0, hideout=True)


def urchin_camp(spec, rng, land, centre, toward, loot, sleepers=5, hideout=None):
    """Urchins squatting in the open, composed as Westwood furnishes their dens (Con02a, War03c: beds and hammocks of
    one kind side by side, a table ringed by stools, their pickings heaped together) round a fire, open toward
    `toward` (squares: the way in). The beds in a row behind the fire, their feet to it; the table and stools on one
    flank; the pickings on the other: crates side by side, sacks, the hoard's chest (loot), the shaman's place before
    it; stools round the fire; a lookout's stool toward the way in. Returns dict(fire, seats, lookout, chest, goods,
    leader, posts) in world px, as bandit_camp, for kit/posts.camp_posts. In a pocket of the earth or the rock (rock_pocket)
    it is a den, as Westwood's urchins live (urchin_den)."""
    if hideout or (hideout is None and rock_pocket(spec, centre)):
        return urchin_den(spec, rng, land, centre, toward, loot, sleepers=sleepers)
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
