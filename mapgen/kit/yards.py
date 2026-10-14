"""Yards (generator v3): gated outdoor plots with a purpose, as Westwood fences them in its towns
(rules/town_walls.py; measured on Con02a, Con08a, War03b, War03c, War03d, War04a and Wiz08a):

- graveyard: one of Westwood's three kinds (`GRAVE_ARCH`): a field (stone back wall with its crypt cells, iron fence,
  wide rough rows of headstones, dead trees by the walls), a crypt yard (a fenced lawn, a crypt in a corner, a knot of
  stones by it) or a pen (a small stone-walled court, four to six stones); sparse grass; the gravedigger's corner (a
  fresh grave and the bucket of tools: the user's ask, SW-9) in most fields (`_graveyard`);
- orchard: a low wooden fence (DilapidatedShort, Gate) round 22-28 tiles of grass: fruit bushes (Plant5, Plant4), one tree,
  flowers, an apple on the ground;
- park: low ruined walls (DilapidatedShort, Gate) round 92-112 tiles: eight benches facing in, bushes and flowers,
  a tree;
- quarry: a ring of cliff (CaveWall2, IronFenceGate) round 88-110 tiles of dirt: rocks of every size and short rock
  pillars toward the back, barren plants, a pick and a shovel left in the ground;
- field: a log fence and gate round a plot of dug earth, a crop in rows (Westwood's gardens grow one crop each:
  GardenCorn, GardenTomatos, GardenCabbage);
- monument: a low cobblestone wall (Cobblestone, WoodAndSteelHalfDoor) round 76 tiles of paving: the monument in the
  middle, statues at the corners, torch poles;
- jail: one of Westwood's two kinds (`JAIL_ARCH`): a row of two or three cells behind cobblestone walls, a JailDoor
  into each with a torch beside it outside, the cells bare, with a cot or deep in straw; or a guardhouse, two cells
  behind the guardroom with its racks, table and water barrel (Con02a, Con07B, War03b, War07A; `_jail`).

A yard is planned before the land is carved (`plan`: its squares are content the land grows round) and built after
the land's walls are laid (`build`): the fence on the wall points round the plot, the gate in the side facing
`toward`, a lane from the gate kept clear.
"""
import math
from kit.layout import square_tile, square_px, point_cell
from kit import spacing as SP

YARDS = {
    "graveyard": dict(fence="IronFence", gate="Gate", floor=None, size=[(10, 9), (11, 9), (11, 10)],
                      grow=[(16, 12), (15, 11), (14, 10), (13, 10), (12, 10)], grow_margin=3,
                      purpose="where the town buries its dead"),
    # (QA round 1, nox6: "Good structure for an orchard, but too empty": rows of apple trees, crates of apples, apples
    # on the ground to pick up; larger, so the rows read as an orchard)
    # a low wooden fence, never Log (a cabin's wall): the tall log fence hid the apples, and the larger QA round 1
    # orchard's log walls blocked the client's sight enough to crash it (Brackwater, 34 crossings on a screen row)
    "orchard": dict(fence="DilapidatedShort", gate="Gate", floor=None, size=[(7, 7), (9, 7), (9, 8)],
                    purpose="the town's fruit trees"),
    "park": dict(fence="DilapidatedShort", gate="Gate", floor=None, size=[(9, 9), (10, 9)],
                 purpose="benches round a shade tree"),
    "quarry": dict(fence="CaveWall2", gate="IronFenceGate", floor="DirtLight2", size=[(9, 8), (10, 9)],
                   purpose="where the town cuts its stone"),
    "field": dict(fence="DilapidatedShort", gate=None, floor="DirtDark2", size=[(8, 6), (9, 6), (7, 7)],
                  purpose="the town's crops"),       # Wiz03b's low wooden fence (a Log fence draws as a cabin's wall)
    "monument": dict(fence="Cobblestone", gate="WoodAndSteelHalfDoor", floor="RoughCobble", size=[(8, 8), (9, 8)],
                     purpose="a memorial to the town's founders"),
    "jail": dict(fence="Cobblestone", gate="JailDoor", floor="RoughCobble", size=[(6, 3)], cells=2,
                 purpose="the town's cells"),
    # the set pieces of QA round 1 (kit/setpieces.py lays what stands in them): a well as a feature on its own paving,
    # now and then behind a low fence and gate; a shrine as a paved court of obelisks, pillars or statues in parallel
    # rows leading to a grand centrepiece. Open (no fence) unless an archetype fences it.
    "well": dict(fence="DilapidatedShort", gate=None, floor=None, size=[(5, 5), (7, 7), (7, 5)], open=True,
                 purpose="the town's well, where water is fetched and the weary are healed"),
    "shrine": dict(fence=None, gate=None, floor=None, size=[(9, 13), (11, 15), (9, 11), (11, 13)], open=True,
                   purpose="a shrine: a paved court of standing stones leading to its centrepiece"),
}
# yards whose gate (or way in) is centred on its side: that side an odd number of squares long
ODD_GATE = {"graveyard", "orchard", "field", "monument", "park", "well", "shrine"}
# courts entered from the screen's bottom (their south-east or south-west side), the centrepiece at the back, seen over
# the court and never hidden behind a front piece
FRONT_ENTRY = {"shrine": ("i1", "j0")}
SET_ARCHS = {"well": (("plain", 4), ("fenced", 3), ("market", 3)),
             "shrine": (("obelisk_court", 3), ("statue_avenue", 3), ("mana_court", 2), ("open_chapel", 2))}


def set_arch(kind, at):
    """A set piece's archetype, from its own generator (its place)."""
    import random as _random, zlib
    w = SET_ARCHS[kind]
    r = _random.Random(zlib.crc32(f"{kind}:arch:{at[0]},{at[1]}".encode()))
    return r.choices([a for a, _ in w], [x for _, x in w])[0]
CROPS = ("GardenCorn", "GardenTomatos", "GardenCabbage")
TOMBSTONES = {"Tombstone1": 8, "Tombstone11": 4, "Tombstone17": 4, "Tombstone5": 3, "Tombstone14": 3,
              "Tombstone8": 3, "Tombstone12": 3, "Tombstone18": 2}
BONES = ("LegBone", "ArmBone", "Skull")
# Westwood's thirteen campaign graveyards are of three kinds (review/scenelab, rules/scenes/graveyard.md "Archetypes"):
# - field (6 of 13: War03b x2, War03c x2, War03d x2): a big yard, stone wall (Cobblestone) on its back and often a flank,
#   iron fence on the rest, crypt cells built into the back wall, headstones in wide rough rows, a dead tree or two by
#   the walls, barren weeds;
# - crypt_yard (4 of 13: Con07B x3, Con09b): a smaller fenced lawn with a stone crypt in a back corner, a knot of four
#   to eight headstones near it, the rest of the lawn open;
# - pen (3 of 13: Con04b, War03d x2): a small court walled in stone all round, four to six stones of one kind.
GRAVE_ARCH = (("field", 6), ("crypt_yard", 4), ("pen", 3))
# a design's graveyard drawn unasked is a field or a crypt yard: a pen is a court inside masonry (Westwood's are in its
# castles and walled towns), laid only where a design (or the scene lab) asks for one with arch="pen" (three of four
# story maps had drawn a pen alone in open ground)
GRAVE_ARCH_OPEN = (("field", 6), ("crypt_yard", 4))
# (a pen fenced now, not walled in stone, and big enough for two rows of graves either side of its path: QA round 1)
GRAVE_SIZE = {"crypt_yard": [(11, 11), (12, 11), (11, 12)], "pen": [(9, 8), (9, 9), (8, 9)]}
DEAD_TREES = ("TreeOgre08", "TreeOgre10", "TreeTrunk6")          # War03b-d's dead trees by the yard's walls
# a statue's letter by the square axis it faces (Statue1x and Statue2x alike: a faces SE (+i), c NE (+j), e NW (-i), g
# SW (-j); kit/furnish.STATUE_FACING), and the great seated statue's facing (HorrendousStatue1 faces SE, 2 SW: the
# scene lab's renders, 2026-10-14; the gold wolf faces SE only)
STATUE_LETTER = {"+i": "a", "+j": "c", "-i": "e", "-j": "g"}
GREAT_STATUE = {"+i": "HorrendousStatue1", "-j": "HorrendousStatue2"}


def grave_arch(centre, weights=GRAVE_ARCH_OPEN):
    """A graveyard's archetype by Westwood's frequencies, from the yard's own generator (its place: the design's
    generator draws nothing)."""
    import random as _random, zlib
    r = _random.Random(zlib.crc32(f"graveyard:arch:{centre[0]:.1f},{centre[1]:.1f}".encode()))
    return r.choices([a for a, _ in weights], [w for _, w in weights])[0]
# a bench facing each way, by the side of the centre it stands on (Village.BENCH_FACING, in squares)
BENCH_ON = {"i0": "Bench1", "i1": "Bench5", "j0": "Bench4", "j1": "Bench2"}


class Yard:
    def __init__(self, kind, gi, gj, w, h, side):
        self.kind, self.gi, self.gj, self.w, self.h, self.side = kind, gi, gj, w, h, side
        self.plot = {(gi + a, gj + b) for a in range(w) for b in range(h)}
        self.gate = None

    @property
    def centre(self):
        """The middle of the plot as drawn, in continuous square coordinates. The fence's wall points (p, q) are drawn
        at square coordinates (p, q - 0.5), half a square toward -j of the squares' own numbering (a tile is drawn at
        its grid corner (x + 1, y + 1), a wall at its cell's middle): so the drawn plot runs gi..gi + w across i and
        gj - 1.5..gj + h - 1.5 across j (Ambermere playtest, 2026-10-05: a garden's last row of crops stood right
        under its NE fence)."""
        return self.gi + self.w / 2, self.gj - 1.5 + self.h / 2


def _pick(rng, w):
    k = list(w); return rng.choices(k, [w[x] for x in k])[0]


def _spread(lo, hi, step):
    """Evenly spaced positions from lo to hi, about `step` apart (rows that fit the plot, ends included)."""
    n = max(1, int((hi - lo) / step) + 1)
    if n == 1: return [(lo + hi) / 2]
    return [lo + (hi - lo) * k / (n - 1) for k in range(n)]


def plan(land, rng, kind, centre, toward=None, margin=2, arch=None):
    """Reserve a yard of `kind` near `centre` (square coordinates) before the land is carved. Its plot and a margin
    round it must be clear of roads, the square, water and everything already taken. The gate faces `toward`
    (default: the map's middle). A graveyard is one of Westwood's archetypes (`arch`, else drawn by `grave_arch`),
    which sets its size and its walls. Returns the Yard, or None if nothing fits within a few squares of `centre`."""
    rec = dict(YARDS[kind])
    if kind == "graveyard":
        arch = arch or grave_arch(centre)
        if arch in GRAVE_SIZE: rec.update(size=GRAVE_SIZE[arch], grow=())
    elif kind == "jail":
        arch = arch or jail_arch(centre)
        rec.update(size=JAIL_SIZE[arch])
    busy = set(land.roads) | land.plaza | land.water | land.taken | land.reserved
    w, h = rng.choice(rec["size"])
    if rng.random() < 0.5: w, h = h, w
    ci, cj = centre
    best = None
    # the size drawn, else the kind's smaller sizes (a yard that has no room at its size is laid smaller, not dropped)
    sizes = [(w, h)] + sorted({(a, b) if (w >= h) == (a >= b) else (b, a) for a, b in rec["size"] if a * b < w * h},
                              key=lambda t: -t[0] * t[1])
    # a kind that runs larger where the ground allows (Westwood's graveyards: up to 16 x 16 squares, long, against
    # crypts) tries its larger sizes first, with a wider margin kept free round them (a larger yard had shut a corner
    # of Harrowby off from the rest)
    grow = [((a, b) if (w >= h) == (a >= b) else (b, a), rec.get("grow_margin", margin)) for a, b in rec.get("grow", ())]
    sizes = grow + [(t, margin) for t in sizes]
    for (w, h), margin_ in sizes:
        for di in range(-4, 5):
            for dj in range(-4, 5):
                gi, gj = int(round(ci - w / 2)) + di, int(round(cj - h / 2 + 1)) + dj
                ring = {(gi + a, gj + b) for a in range(-margin_, w + margin_) for b in range(-margin_, h + margin_)}
                if ring & busy: continue                  # (the margin also keeps 2 squares free beyond the fence)
                # on the grid with room for the forest round it (Land.carve keeps squares within 3..250)
                if not all(8 <= i + j <= 245 and 8 <= i - j <= 245 for i, j in ring): continue
                d = abs(di) + abs(dj)
                if best is None or d < best[0]: best = (d, gi, gj)
        if best: break
    if best is None: return None
    _, gi, gj = best
    tx, ty = toward if toward else (125.0, 0.0)
    mids = {"i0": (gi, gj - 1 + h / 2), "i1": (gi + w, gj - 1 + h / 2),
            "j0": (gi + w / 2, gj - 1), "j1": (gi + w / 2, gj + h - 1)}
    if rec.get("cells", 1) > 1:                  # cells side by side: their doors are on a long side
        mids = {s: p for s, p in mids.items() if (s in ("j0", "j1")) == (w >= h)}
    if kind in FRONT_ENTRY:                      # a court entered from the screen's bottom, its centrepiece at the back
        mids = {s: p for s, p in mids.items() if s in FRONT_ENTRY[kind]}
    side = min(mids, key=lambda s: math.hypot(mids[s][0] - tx, mids[s][1] - ty))
    if kind == "jail" and arch in ("guardhouse", "cell_row"):
        # the jail's front on the side toward the camera (SE or SW), its cells behind on the far side: a cell's cot
        # against a wall the camera looks over had been hidden behind it (QA round 1, Q1K-10)
        side = next(s_ for s_ in ("i1", "j0") if s_ in mids)
    if kind in ODD_GATE:
        # the gate centred on its side, so a path, a mausoleum and the rows centre on it (QA round 1, EX-GRAVEYARD-10:
        # "the gate is slightly off-centre with the cobblestone path"): its side an odd number of squares long
        if side in ("j0", "j1") and w % 2 == 0: w -= 1
        if side in ("i0", "i1") and h % 2 == 0: h -= 1
    y = Yard(kind, gi, gj, w, h, side)
    if YARDS[kind].get("open"): y.open = True
    if kind == "jail":
        y.arch = arch
        if arch == "cave_cell": y.walls = {f: "Dirt" for f in ("i0", "i1", "j0", "j1")}
    if kind == "graveyard":
        y.arch = arch
        back = {"i0": "i1", "i1": "i0", "j0": "j1", "j1": "j0"}[side]
        # the perimeter a fence, stone only for the back wall opposite the gate and the mausoleums (QA round 1: "Stone
        # walls don't make sense for the graveyard perimeter itself ... EX-GRAVEYARD-05 does this PERFECTLY"); a pen is
        # no longer walled in stone all round
        y.walls = {back: "Cobblestone"}
    if kind in SET_ARCHS:
        y.arch = arch or set_arch(kind, (gi, gj))
        if kind == "well" and y.arch == "fenced":
            y.open = False                    # (a well behind its own low fence and gate)
    land.taken |= {(gi + a, gj + b) for a in range(-2, w + 2) for b in range(-2, h + 2)}      # trees stay off the fence
    return y


def plan_any(land, rng, kind, centres, toward=None, arch=None):
    """plan() at the first of `centres` (square coordinates) where the yard fits."""
    for c in centres:
        y = plan(land, rng, kind, c, toward, arch=arch or {"graveyard": grave_arch, "jail": jail_arch}.get(kind, lambda _: None)(centres[0]))
        if y: return y
    return None


def gate_outside(y, out=1.6):
    """The square just outside the yard's gate (its walk to the road starts there), or None before build()."""
    gm = getattr(y, "gate_mid", None)
    if gm is None: return None
    ci, cj = y.centre
    dx, dy = gm[0] - ci, gm[1] - cj
    if abs(dx) >= abs(dy): dx, dy = math.copysign(1.0, dx), 0.0      # straight out of its side
    else: dx, dy = 0.0, math.copysign(1.0, dy)
    si, sj = gm[0] + dx * out, gm[1] + dy * out
    return int(math.floor(si)), int(math.floor(sj)) + 1


def _fence_points(y):
    """Wall points round the plot, by side, each side's points in order along it."""
    gi, gj, w, h = y.gi, y.gj, y.w, y.h
    return {"i0": [(gi, q) for q in range(gj - 1, gj + h)], "i1": [(gi + w, q) for q in range(gj - 1, gj + h)],
            "j0": [(p, gj - 1) for p in range(gi, gi + w + 1)], "j1": [(p, gj + h - 1) for p in range(gi, gi + w + 1)]}


def yard_ground(y, land=None):
    """The squares under a yard's fenced ground: i across gi..gi + w - 1, j across gj..gj + h - 1, the plot's own
    squares, every one of them inside the fence and the fence's line their outer edge on every side (QA round 2,
    2026-10-14 [Q2T-6, Q2X-1]: "The brick extends outside of the enclosure to the southwest"). A square's tile is drawn
    half a square toward -j of where kit/layout.square_px puts the square's middle (TILE_DJ: the scene lab's renders,
    a fence of points round paved squares, 2026-10-14), while walls and objects agree with square_px: so a tile row
    meets a fence's j line at its edge, as it does an i line. QA round 1's ground (gj - 1..gj + h - 1, read as half a
    square past the fence on both j sides) had in truth laid a whole row outside the fence on its j0 (south-west) side
    and none on its j1 side."""
    out = set(y.plot)
    return {s for s in out if land is None or (s in land.squares and s not in land.water)}


# where a square's tile is drawn, in kit/layout.square_px's square coordinates (which walls and objects follow): its
# middle at (i + 0.5, j + TILE_DJ), half a square toward -j of square_px's (i + 0.5, j - 0.5) (yard_ground)
TILE_DJ = -1.0


def tile_centre(s):
    """The drawn middle of square s's tile, in square_px's coordinates (TILE_DJ)."""
    return s[0] + 0.5, s[1] + TILE_DJ


def tile_at(si, sj):
    """The square whose drawn tile holds the point (si, sj) of square_px's coordinates (TILE_DJ)."""
    return int(math.floor(si + 1e-6)), int(math.floor(sj - TILE_DJ + 0.5 + 1e-6))


def door_between(spec, kind, pa, pb):
    """A door (a double door's two halves) in the two wall cells of points pa, pb, exactly there: Spec.door hangs a
    double door from its gap cell along its line's step and falls back to the cell before, which had set a gate a cell
    off its side's middle when the points ran against the step (QA round 1, EX-GRAVEYARD-10)."""
    a, b = point_cell(*pa), point_cell(*pb)
    d = (b[0] - a[0], b[1] - a[1])
    line = "\\" if d in ((1, 1), (-1, -1)) else "/"
    step = (1, 1) if line == "\\" else (1, -1)
    first = a if d == step else b
    return spec.door(kind, first, line)


class Frame:
    """A yard's own frame, for laying it symmetric about its gate (QA round 1: "lack of balance and symmetry"): u runs
    across the yard along the gate's side, 0 on the gate's middle (u > 0 and u < 0 mirror each other); v runs inward
    from the gate's side (0 on its line) to the back (D). `sq(u, v)` gives continuous square coordinates (as drawn),
    `px` world px, `square` the square there, `point` the wall point there. The squares' centres lie on a lattice
    symmetric about u = 0 (on it for a gate in a j side, half a square off it for one in an i side)."""
    FWD = {"j0": ((0, 1), (1, 0)), "j1": ((0, -1), (-1, 0)), "i0": ((1, 0), (0, 1)), "i1": ((-1, 0), (0, -1))}
    AXIS = {(1, 0): "+i", (-1, 0): "-i", (0, 1): "+j", (0, -1): "-j"}

    def __init__(self, y):
        self.y = y
        self.f, self.r = self.FWD[y.side]
        self.gm = y.gate_mid
        self.L, self.D = (y.w, y.h) if y.side in ("j0", "j1") else (y.h, y.w)
        self.half = self.L / 2
        self.back = {"i0": "i1", "i1": "i0", "j0": "j1", "j1": "j0"}[y.side]
        self.lat = 0.0 if y.side in ("j0", "j1") else 0.5          # u of the squares' centres, mod 1
        self.path_half = 1.5 if self.lat == 0.0 else 1.0           # a path 3 (2) squares wide, centred on the gate

    def sq(self, u, v):
        return (self.gm[0] + u * self.r[0] + v * self.f[0], self.gm[1] + u * self.r[1] + v * self.f[1])

    def px(self, u, v):
        return square_px(*self.sq(u, v))

    def square(self, u, v):
        """The square whose drawn tile holds the frame point (u, v) (tile_at: a tile is drawn half a square toward -j
        of square_px's middle)."""
        return tile_at(*self.sq(u, v))

    def point(self, u, v):
        si, sj = self.sq(u, v)
        return int(round(si)), int(round(sj + 0.5))

    def axis(self, du, dv):
        """The square axis ("+i", ...) of a frame direction (du, dv): one of the four, du or dv zero."""
        d = (int(du * self.r[0] + dv * self.f[0]), int(du * self.r[1] + dv * self.f[1]))
        return self.AXIS[d]

    def uv_of_square(self, s):
        """(u, v) of a square's drawn tile middle (tile_centre)."""
        ci, cj = tile_centre(s)
        si, sj = ci - self.gm[0], cj - self.gm[1]
        return si * self.r[0] + sj * self.r[1], si * self.f[0] + sj * self.f[1]

    def squares(self, u0, u1, v0, v1):
        """The squares whose drawn tiles' middles lie in u0..u1, v0..v1 (symmetric when u0 = -u1). The tiles' middles
        lie on whole u either side of the gate's middle, on a gate in any side, and half a square into the yard along v
        (QA round 2 [Q2X-2, Q2X-3]: on a gate in an i side the path and the aisle had been laid half a square off the
        gate, the mausoleum and the statue: "The cobblestone path is not aligned correctly with the gate and
        mausoleum")."""
        out = set()
        ci, cj = self.sq(0, (v0 + v1) / 2)
        R = int(max(abs(u0), abs(u1)) + abs(v1 - v0) / 2) + 3
        for i in range(int(ci) - R, int(ci) + R + 2):
            for j in range(int(cj) - R, int(cj) + R + 3):
                u, v = self.uv_of_square((i, j))
                if u0 - 1e-6 <= u <= u1 + 1e-6 and v0 - 1e-6 <= v <= v1 + 1e-6: out.add((i, j))
        return out


def build(spec, rng, land, y):
    """Lay the yard planned by `plan`: its floor, its fence and gate, what it holds. Returns the objects placed."""
    rec = YARDS[y.kind]
    if rec["floor"]:
        for s in (yard_ground(y, land) if y.kind in ODD_GATE else y.plot): spec.floor[square_tile(*s)] = rec["floor"]
    sides = _fence_points(y)
    walls = getattr(y, "walls", {})
    fenced = not getattr(y, "open", False)
    for side_ in sorted(sides, key=lambda f: f in walls) if fenced else ():     # (a stone side's corners stone)
        for p in sides[side_]:
            spec.wall(*point_cell(*p), walls.get(side_, rec["fence"]))
    pts = sides[y.side]
    n_cells = rec.get("cells", 1)
    if n_cells > 1:
        return _jail(spec, rng, y, rec, pts)
    # the gate: a two-cell opening in the middle of its side (a double gate hangs a half at each end); an open yard has
    # its way in there, unwalled
    k = len(pts) // 2
    if fenced: y.gate = door_between(spec, rec["gate"], pts[k - 1], pts[k])
    gm = ((pts[k - 1][0] + pts[k][0]) / 2, (pts[k - 1][1] + pts[k][1]) / 2 - 0.5)  # the gate's middle, as drawn
    y.gate_mid = gm
    if land is not None and y.kind in ODD_GATE:
        # no walk crosses the yard's ground (a house's walk had laid its dirt over a well's paving)
        land.reserved |= yard_ground(y, land)
    if y.kind in ("well", "shrine"):
        from kit import setpieces
        return setpieces.build_set(spec, land, y, Frame(y))
    ci, cj = y.centre
    lane = (gm, (ci, cj))
    placed = []

    yj = y.gj - 0.5                     # the drawn plot's j, half a square below the squares' (Yard.centre)

    def free_spot(si, sj, pad=0.9, lane_w=1.3, t=None):
        if not (y.gi + pad <= si <= y.gi + y.w - pad and yj - 1 + pad <= sj <= yj + y.h - 1 - pad): return False
        if t is not None and not SP.off_walls(spec.wallmap, t, *square_px(si, sj), margin=6): return False
        (ax, ay), (bx, by) = lane
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((si - ax) * dx + (sj - ay) * dy) / (dx * dx + dy * dy or 1)))
        if math.hypot(si - ax - t * dx, sj - ay - t * dy) < lane_w: return False
        return all(math.hypot(si - p, sj - q) >= r for p, q, r in placed)

    def put(t, si, sj, room=0.8, **extra):
        spec.obj_px(t, *square_px(si, sj), **extra)
        placed.append((si, sj, room))

    jit = lambda: rng.uniform(-0.25, 0.25)
    if y.kind == "graveyard":
        _graveyard(spec, land, y, Frame(y))
    elif y.kind == "orchard":
        _orchard(spec, land, y, Frame(y))
    elif y.kind == "park":
        # eight benches facing a tree in the middle, two to a side; bushes in the corners, flowers along the walls
        put("TreeForest15", ci, cj, room=1.8)
        for side, (di, dj) in (("i0", (-1, 0)), ("i1", (1, 0)), ("j0", (0, -1)), ("j1", (0, 1))):
            for off in (-1.0, 1.0):
                s = (ci + 2.6 * di + off * abs(dj), cj + 2.6 * dj + off * abs(di))
                if free_spot(*s, pad=0.8, lane_w=0.9): put(BENCH_ON[side], *s, room=0.9)
        for c in ((y.gi + 1.0, yj), (y.gi + y.w - 1.0, yj), (y.gi + 1.0, yj + y.h - 2), (y.gi + y.w - 1.0, yj + y.h - 2)):
            if free_spot(*c, pad=0.7, lane_w=1.1): put(rng.choice(("Bush6", "Plant5", "Plant4")), *c, room=1.0)
        for _ in range(10):
            s = (rng.uniform(y.gi + 0.8, y.gi + y.w - 0.8), rng.choice((yj - 0.2, yj + y.h - 1.8)))
            if free_spot(*s, pad=0.6, lane_w=1.1): put(rng.choice(("FlowersBlueSparse", "FlowersPurpleSparse", "FlowersWhiteSparse")), *s, room=0.7)
    elif y.kind == "field":
        _field(spec, land, y, Frame(y))
    elif y.kind == "monument":
        put("Monument1", ci, cj, room=2.2)
        for c in ((y.gi + 1.3, yj + 0.3), (y.gi + y.w - 1.3, yj + 0.3), (y.gi + 1.3, yj + y.h - 2.3),
                  (y.gi + y.w - 1.3, yj + y.h - 2.3)):
            if free_spot(*c, pad=1.0, lane_w=1.3): put("Statue2a", *c, room=1.4)
        for d in (-1.6, 1.6):                       # torch poles flanking the way in, and the monument
            dx, dy = cj - gm[1], -(ci - gm[0])
            n = math.hypot(dx, dy) or 1
            for f in (0.35, 0.8):
                s = (gm[0] + (ci - gm[0]) * f + d * dx / n, gm[1] + (cj - gm[1]) * f + d * dy / n)
                if free_spot(*s, pad=0.8, lane_w=1.1): put("TorchPole", *s, room=0.8)
    elif y.kind == "quarry":
        _quarry(spec, rng, y, yj, free_spot, put, jit)
    return placed



def _side_line(y, yj, f, inset):
    """A function t (0..1) -> (si, sj) along the inside of side f of the yard's fence, `inset` squares in from it."""
    I0, I1, J0, J1 = y.gi, y.gi + y.w, yj - 1, yj - 1 + y.h
    if f == "i0": return lambda t: (I0 + inset, J0 + 1.2 + (J1 - J0 - 2.4) * t)
    if f == "i1": return lambda t: (I1 - inset, J0 + 1.2 + (J1 - J0 - 2.4) * t)
    if f == "j0": return lambda t: (I0 + 1.2 + (I1 - I0 - 2.4) * t, J0 + inset)
    return lambda t: (I0 + 1.2 + (I1 - I0 - 2.4) * t, J1 - inset)


def _quarry(spec, rng, y, yj, free_spot, put, jit):
    """The quarry: the rock face at the back; the works along one flank's fence (QA round 1, 2026-10-13 [Q1K-8]: "Add
    more object diversity. Mining carts, pickaxes, bones, mana crystals. Explosives, crates, barrels. They all look good
    in terms of layout and there isn't much differentiation"): an ore cart with its spare wheel, the steel crates and
    barrels, the powder kegs set apart at the row's end, the tool barrels, the picks laid down, in a row against the
    fence; on the other flank the crystals the cutting turned up, in the rock by the back corner, with the bones of what
    was buried in it; the rubble and the tools in the open as before, fewer pebbles. Each quarry draws its own share of
    these, so no two read alike."""
    back = {"i0": "i1", "i1": "i0", "j0": "j1", "j1": "j0"}[y.side]
    flanks = [f for f in ("i0", "i1", "j0", "j1") if f not in (y.side, back)]
    rng.shuffle(flanks)
    bx = {"i0": y.gi + 1.2, "i1": y.gi + y.w - 1.2}.get(back)
    by_ = {"j0": yj - 1 + 1.2, "j1": yj + y.h - 2.2}.get(back)
    along = [yj - 1 + 1.3 + 1.6 * k for k in range(int((y.h - 2) / 1.6) + 1)] if bx is not None else \
            [y.gi + 1.3 + 1.6 * k for k in range(int((y.w - 2) / 1.6) + 1)]
    for t in along:                                   # the rock face at the back
        s = (bx + jit(), t + jit()) if bx is not None else (t + jit(), by_ + jit())
        big = rng.choices(("CaveRocksHuge", "CaveRockPillarShort2", "CaveRocksLarge", "CaveRocksMedium"), (3, 2, 2, 2))[0]
        if free_spot(*s, pad=0.9, lane_w=1.3): put(big, *s, room=1.3)
    # ---- the works against the first flank's fence: one row, its pieces drawn from the quarry's own share
    line = _side_line(y, yj, flanks[0], 1.1)
    cart_axis = "\\" if flanks[0] in ("j0", "j1") else "/"
    cart = rng.choice(("MineOreCart1", "MineOreCartBroken1")) if cart_axis == "\\" else \
        rng.choice(("MineOreCart2", "MineOreCartBroken2"))
    works = [cart, rng.choice(("CrateSteel1", "CrateSteel2")), rng.choice(("BarrelSteel1", "BarrelSteel2")),
             rng.choice(("BarrelWithTools1", "BarrelWithTools2")), "BlackPowderBarrel",
             rng.choice(("MiningPickAxeOnGround1", "MiningPickAxeOnGround2", "MineOreCartWheel"))]
    if rng.random() < 0.5: works[1], works[2] = works[2], works[1]
    n = len(works)
    typed = []                                       # (each its kit/spacing gap from the row's others: Q1K-1)
    for k, t in enumerate(works):
        for dt in (0.0, 0.05, -0.05, 0.1, -0.1, 0.15, -0.15):
            si, sj = line(min(1.0, max(0.0, k / max(1, n - 1) + dt)))
            x_, y_ = square_px(si, sj)
            if free_spot(si, sj, pad=0.6, lane_w=1.2, t=t) and SP.spaced(t, x_, y_, typed):
                put(t, si, sj, room=1.0 if "Cart" in t and "Wheel" not in t else (0.9 if "Crate" in t else 0.6))
                typed.append((t, x_, y_))
                break
    # ---- the crystals in the rock by the back corner of the other flank, the bones the cutting turned up
    line2 = _side_line(y, yj, flanks[1], 0.95)
    end = 1.0 if (back in ("i1", "j1")) == (flanks[1] in ("i0", "i1")) else 0.0
    for k, t in enumerate([rng.choice(("MineCrystal01", "MineCrystal02", "MineCrystal03")),
                           rng.choice(("MineCrystal04", "MineCrystal05")), rng.choice(("MineCrystal01", "MineCrystal03")),
                           "CaveRocksLarge", "Skull", "LegBone", "ArmBone"]):
        tt = abs(end - (0.05 + 0.11 * k + rng.uniform(-0.02, 0.02)))
        si, sj = line2(tt)
        if "Bone" in t or t == "Skull": sj += rng.uniform(-0.5, 0.5); si += rng.uniform(-0.5, 0.5)
        if free_spot(si, sj, pad=0.7, lane_w=1.2): put(t, si, sj, room=0.5 if "Bone" in t or t == "Skull" else 0.9)
    # ---- in the open: the rubble and the tools, as many as Westwood's quarry yards hold (Con02a, War03b, War08a: 17-24
    # pebbles, 6-9 medium rocks, 4-6 huge ones, 3-4 short pillars, 2-4 barren plants), never fewer than before
    for t, n in (("CaveRocksHuge", 2), ("CaveRockPillarShort1", 1), ("CaveRocksMedium", 7), ("CaveRocksSmall", 4),
                 ("CaveRocksPebbles", 18), ("PlantBarren1", 3), ("MiningPickAxeInGround1", 1),
                 ("MiningShovelInGround", 1), ("MiningPickAxeInGround2", 1 if rng.random() < 0.5 else 0)):
        for _ in range(n):
            for _try in range(15):
                s = (rng.uniform(y.gi + 0.8, y.gi + y.w - 0.8), rng.uniform(yj - 0.2, yj + y.h - 1.8))
                if free_spot(*s, pad=0.7, lane_w=1.2): put(t, *s, room=0.6 if "Pebbles" in t else 0.9); break


def connect_gate(spec, land, y, material="DirtDark2"):
    """The walk from a yard's gate to the road network, routed round the yard: never along or under its fence (QA round
    1, 2026-10-13 [Q1K-9]: "The southeast wall of the quarry runs clear across the path": the walk had hugged the
    fence's outside, a square off its line, and read as a path the wall stood across). The fence's ring of squares is
    blocked but for the squares before the gate. Returns the walk's squares, or None."""
    out = gate_outside(y)
    if not out or out not in land.squares: return None
    ring = {(y.gi + a, y.gj + b) for a in range(-2, y.w + 2) for b in range(-2, y.h + 2)}
    gm = y.gate_mid
    ci, cj = y.centre
    dx, dy = gm[0] - ci, gm[1] - cj
    d = (int(math.copysign(1, dx)), 0) if abs(dx) >= abs(dy) else (0, int(math.copysign(1, dy)))
    keep = {(out[0] + d[0] * k, out[1] + d[1] * k) for k in range(0, 4)}       # straight out from the gate
    return land.connect(spec, out, footprint=frozenset(ring - keep - {out}), material=material)


# Westwood's eleven campaign jails, by structure (rules/scenes/jail.md "Structures", round 8; the judges on round 7:
# "one free-standing rectangular block every time", "straw as one neat clump mid-cell", "racks standing off the wall"):
# - cell_row (8 of 11: Con07B x7, War07A): cells off a corridor inside the castle's masonry, the corridor walled with
#   its own wooden door (ThickWoodenDoor), a barred door into each cell and a wall torch by it in the corridor; inside,
#   variety: many cells bare, one with a cot in a back corner and a mat of straw (7-10 Straw2 8-16 px apart, a streak
#   or a blob reaching out from the cot), one with a few straws;
# - cave_cell (1 of 11: War03c): one cell dug in the earth (Dirt walls, DirtDark2), four ogre straws in a heap, a torch
#   by its barred door;
# - guardhouse (2 of 11: Con02a, War03b): two cells at the back of a stone house, the guardroom before them with the
#   guards' racks against its walls, a table and a water barrel, its own door.
# (A corridor needs five squares' depth: a jail planned smaller is the open row of rounds 6-7. A cave cell is laid only
# where it is asked for, `arch="cave_cell"`: one cell holds one prisoner, and Westwood's is in a cave.)
# (QA round 1, 2026-10-13 [Q1K-10], every jail rated 2: "At least 80% of cells should have either a cot, a bench. Needs
# many more objects and much more object diversity. Almost no cell should have 0 objects in it. Bones, barrels of
# tools, a piece of meat, a cot, etc. Jails in towns should always have a large entry /guard room with a desk and some
# decor. Entry/guard rooms need to be significantly bigger so they don't feel too crowded"): a town's jail is a
# guardhouse, its guard room across the whole front, four squares deep or more (the round's was two by six, "way too
# concentrated and cluttered"), the cells behind it; the castle's cell row and the cave cell are laid only where a design
# asks for them.
JAIL_ARCH = (("guardhouse", 1),)
JAIL_SIZE = {"cell_row": [(6, 5), (9, 5), (8, 5)], "cave_cell": [(4, 3), (3, 3)],
             "guardhouse": [(11, 8), (12, 8), (10, 8), (9, 8)]}
GUARD_DEPTH = 4                 # squares, the guard room's depth at the least (the cells take the rest, three or four)
CELL_FURNISHED = 0.8            # of a jail's cells, at the least, have a cot or a bench [Q1K-10]
CELL_EXTRAS = (("bones", 3), ("straw", 3), ("meat", 2), ("tools", 2), ("stool", 2), ("bucket", 1))
GUARD_RACKS = ("TraderBowRack2", "TraderQuiverRack", "TraderPoleArm1", "TraderPoleArm2")


def jail_arch(centre, weights=JAIL_ARCH):
    """A jail's archetype (a town's: the guardhouse), from its own generator (its place)."""
    import random as _random, zlib
    r = _random.Random(zlib.crc32(f"jail:arch:{centre[0]:.1f},{centre[1]:.1f}".encode()))
    return r.choices([a for a, _ in weights], [w for _, w in weights])[0]


def _jail(spec, rng, y, rec, pts):
    """The jail's cells (and a guardhouse's guard room) inside the stone walls `build` laid: the dividing walls, a
    JailDoor into each cell, a torch beside each door, the guard room furnished as a room (kit/furnish, kind guardroom)
    with the warden's desk, every cell furnished (kind cell) and given a cot or a bench and a prisoner's leavings.
    Sets y.gate, y.cells (the doors), y.cell_mids (each cell's middle, px), y.rooms (the Rooms laid). The design's
    generator draws what the first jails drew, so a map round it is laid as before."""
    import random as _random, zlib
    from kit.model import Room, Door
    arch = getattr(y, "arch", "cell_row")
    along_i = y.side in ("j0", "j1")
    L = y.w if along_i else y.h                    # along the front
    D = y.h if along_i else y.w                    # front to back

    def pt(u, v):                                  # a wall point: u along the front, v in from it
        if y.side == "j0": return (y.gi + u, y.gj - 1 + v)
        if y.side == "j1": return (y.gi + u, y.gj + y.h - 1 - v)
        if y.side == "i0": return (y.gi + v, y.gj - 1 + u)
        return (y.gi + y.w - v, y.gj - 1 + u)

    def at(u, v):                                  # an object's square coordinates (drawn half a square toward -j)
        p, q = pt(u, v)
        return p, q - 0.5

    def uv_of(s):                                  # a square's (u, v) of its middle
        si, sj = s[0] + 0.5, s[1] - 0.5
        if y.side == "j0": return si - y.gi, sj + 0.5 - (y.gj - 1)
        if y.side == "j1": return si - y.gi, y.gj + y.h - 1.5 - sj
        if y.side == "i0": return sj + 0.5 - (y.gj - 1), si - y.gi
        return sj + 0.5 - (y.gj - 1), y.gi + y.w - si

    doors_made = []

    def door(u, v, kind, connects):
        a, b = point_cell(*pt(u, v)), point_cell(*pt(u + 1, v))
        line = "\\" if (b[0] - a[0], b[1] - a[1]) == (1, 1) else "/"
        o = spec.door(kind, a, line)
        doors_made.append((Door(gap=a, line=line, type=kind, connects=connects, px=(o["x"], o["y"])), connects))
        return o

    for c in range(rec.get("cells", 2)):           # (the draws the first jails made)
        for _ in range(rng.randint(1, 2)): rng.uniform(0, 1); rng.uniform(0, 1)
    own = _random.Random(zlib.crc32(f"{spec.d['name']}:jail:{y.gi},{y.gj}".encode()))
    hand = _random.Random(zlib.crc32(f"{spec.d['name']}:jail-hand:{y.gi},{y.gj}".encode()))
    if arch == "guardhouse":
        v_cells = max(GUARD_DEPTH, D - 4)
        n = max(2, min(4, L // 3))
    elif arch == "cave_cell":
        v_cells, n = 0, 1
    else:
        v_cells = 2 if D >= 5 else 0
        n = max(2, L // 3)
    if v_cells:
        for u in range(0, L + 1): spec.wall(*point_cell(*pt(u, v_cells)), rec["fence"])
    if arch == "cave_cell":                        # (War03c: a cell dug in the earth)
        for s_ in y.plot: spec.floor[square_tile(*s_)] = "DirtDark2"
    # the cells of even widths in a guardhouse (QA round 1: balance), uneven in a castle's row (round 7's judges)
    widths = [L // n] * n
    for k in range(L - sum(widths)):
        widths[(k * 2 + (n % 2)) % n if arch == "guardhouse" else hand.randrange(n)] += 1
    if arch == "cave_cell": widths = [L]
    bounds = [sum(widths[:k]) for k in range(n + 1)]
    for u_k in bounds[1:-1]:                       # the walls between the cells
        for v in range(v_cells, D + 1): spec.wall(*point_cell(*pt(u_k, v)), rec["fence"])
    doors, mids = [], []
    for c in range(n):
        lo, hi = bounds[c], bounds[c + 1]
        # a guardhouse's cell door in its cell's middle (the row reads even from the guard room), a castle's where it falls
        du_ = lo + (hi - lo - 1) // 2 if arch == "guardhouse" else hand.randint(lo + 1, max(lo + 1, hi - 2))
        doors.append(door(du_, v_cells, rec["gate"], ("guard" if arch == "guardhouse" else "outside", f"cell{c}")))
        mids.append(square_px(*at((lo + hi) / 2, (v_cells + D) / 2)))
        # (a guardhouse's torches each on the same side of its door, never two side by side; a castle row's as it falls)
        sd_ = 1 if arch == "guardhouse" else hand.choice((1, -1))
        tu = du_ + 0.5 + sd_ * (1.1 if arch == "guardhouse" else hand.uniform(0.85, 1.35))
        if not (lo + 0.3 < tu < hi - 0.3): tu = du_ + 0.5 - sd_ * 1.0
        if lo + 0.3 < tu < hi - 0.3 or arch == "cell_row":
            spec.obj_px("Torch", *square_px(*at(tu, v_cells - 0.3)))
    y.gate, y.cells, y.cell_mids = doors[0], doors, mids
    if arch == "cell_row" and v_cells:
        # the corridor's own wooden door near one end of its outer wall (Con07B, War07A: ThickWoodenDoor)
        y.gate = door(hand.choice((1, L - 2)), 0, "ThickWoodenDoor", ("outside", "corridor"))
    elif arch == "guardhouse":
        # the guard room's door in the middle of the front, the way in straight on to the cells (QA round 1: balance)
        y.gate = door((L - 1) // 2, 0, "WoodenDoor", ("outside", "guard"))
    y.rooms = []

    def room_of(name, us, vs, floor):
        sqs = {s for s in y.plot if us[0] < uv_of(s)[0] < us[1] and vs[0] < uv_of(s)[1] < vs[1]}
        tiles = {square_tile(*s) for s in sqs}
        walls = {c for c in spec.wallmap if any((c[0] + a, c[1] + b) in tiles for a in (-1, 0, 1) for b in (-1, 0, 1))}
        ds = [d for d, con in doors_made if name in con]
        return Room(id=f"jail{y.gi},{y.gj}:{name}", tiles=tiles, floor=floor, walls=walls, doors=ds,
                    kind="guardroom" if name == "guard" else "cell", building="the jail"), sqs

    floor = rec.get("floor") or "RoughCobble"
    if arch == "guardhouse":
        guard, gsq = room_of("guard", (0, L), (0, v_cells), floor)
        _guard_room(spec, own, guard)
        y.rooms.append(guard)
    if arch != "cave_cell":
        for c in range(n):
            cell, csq = room_of(f"cell{c}", (bounds[c], bounds[c + 1]), (v_cells, D), floor)
            _cell(spec, own, cell, csq, (bounds[c], bounds[c + 1]), v_cells, D, at, k=c)
            y.rooms.append(cell)
    else:
        for k in range(4):                           # War03c's heap of ogre straw
            spec.obj_px("OgreStraw1", *square_px(*at(L / 2 + own.uniform(-0.8, 0.8), D - 1.0 + own.uniform(-0.3, 0.3))))
    return []


def _guard_room(spec, rng, room):
    """The guard room furnished as a room (kit/furnish, kind guardroom: the watch's table, cots for the off watch, the
    racks and hangings), the warden's desk laid first against a back wall with his chair before it (QA round 1
    [Q1K-10]: "a large entry/guard room with a desk and some decor")."""
    from kit.furnish import Furnisher
    from kit import loot
    f = Furnisher(spec, room, "guardroom", rng, "town")
    f.in_required = True
    for t, side in (("Desk2", "\\|TR"), ("Desk1", "/|TL"), ("Desk4", "/|BR"), ("Desk3", "\\|BL")):
        got = f.against_wall("desk", t_choice=t, side_pref=side, role="wall")
        if got:
            o, r_, uv = got
            f.seats_around(uv, t, 1)
            break
    f.in_required = False
    objs = f.furnish()
    # the decor the round asked for: hangings on its back walls (arms, shields), the watch's water and ale in a knot
    for _ in range(3):
        try: f.place_decor()
        except Exception: break
    for t in ("WaterBarrel", "Barrel", "Barrel2"):
        try: f.against_wall("storage", t_choice=t, role="corner", tries=12)
        except Exception: break
    for t in ("TraderQuiverRack", "OutdoorTraderArmorRack1", "TraderArmorRack1"):     # the watch's arms by the walls
        try: f.against_wall("shop_rack", t_choice=t, tries=12)
        except Exception: break
    objs = f.objects
    # (the torches by the cell doors light the room: no candelabra stands by one, composition.lights_pair)
    torches = [o for o in spec.d["objects"] if o.get("type") == "Torch" and
               any(math.hypot(o["x"] - q["x"], o["y"] - q["y"]) < 400 for q in objs)]
    for o in [o for o in objs if o.get("type", "").startswith("Candleabra") and
              any(math.hypot(o["x"] - t_["x"], o["y"] - t_["y"]) < 90 for t_ in torches)]:
        f._remove(o)
    objs = f.objects
    room.kind = f.kind
    loot.tag(spec, objs, f.kind)
    return objs


def _cell(spec, rng, room, sqs, us, v0, D, at, k=0):
    """One cell furnished as a room (kit/furnish, kind cell), then made sure of its cot or bench (CELL_FURNISHED) and
    given a prisoner's leavings: bones, straw, a scrap of meat, a barrel of tools, a stool (QA round 1 [Q1K-10]). Each
    piece keeps 30 px off the rest; the doorway's square stays clear."""
    from kit.furnish import furnish_room
    import re as _re
    n0 = len(spec.d["objects"])
    try:
        furnish_room(spec, room, kind="cell", rng=rng, style="town")
    except Exception:                                # (a cell too small for the room furnisher: laid by hand below)
        del spec.d["objects"][n0:]
    mine = [o for o in spec.d["objects"][n0:] if "type" in o]
    lo, hi = us

    def free(x, y_, clear=30.0):
        return all(math.hypot(x - o["x"], y_ - o["y"]) >= clear for o in mine)

    def put(t, u, v, clear=30.0):
        x, y_ = square_px(*at(u, v))
        if not free(x, y_, clear): return None
        o = spec.obj_px(t, x, y_)
        mine.append(o)
        return o

    # the cot or the bench: in every cell but one in five (whole jails hold to CELL_FURNISHED), along the back wall
    has_bed = any(_re.match(r"^(Cot\d|Bench\d|LightBench\d|WoodBed|Bed\d)", o["type"]) for o in mine)
    if not has_bed and (k % 5 != 4):
        for t, u in (("Cot2", lo + 0.9), ("Cot2", hi - 0.9), ("Cot1", (lo + hi) / 2), ("Bench4", (lo + hi) / 2)):
            x, y_ = square_px(*at(u, D - 0.8))
            # (straw and bones strewn where the cot goes are cleared for it: the cot comes first)
            loose = [o for o in mine if _re.match(r"^(Straw|ArmBone|LegBone|Skull|RottenMeat)", o["type"])
                     and math.hypot(x - o["x"], y_ - o["y"]) < 34]
            if all(math.hypot(x - o["x"], y_ - o["y"]) >= 34 for o in mine if o not in loose):
                for o in loose:
                    mine.remove(o)
                    objs_ = spec.d["objects"]
                    del objs_[next(i for i, q in enumerate(objs_) if q is o)]
                if put(t, u, D - 0.8, 34): break
    # the leavings, two or three of them
    picks = [n for n, w in CELL_EXTRAS for _ in range(w)]
    rng.shuffle(picks)
    got = set()
    for name in picks:
        if len(got) >= rng.randint(2, 3): break
        if name in got: continue
        u, v = rng.uniform(lo + 0.6, hi - 0.6), rng.uniform(v0 + 1.4, D - 0.5)
        if name == "bones":
            ok = put(rng.choice(("LegBone", "ArmBone")), u, v, 14) and put("Skull", u + 0.35, v - 0.2, 12)
        elif name == "straw":
            ok = put("Straw2", u, v, 22) and put("Straw1", u + 0.3, v + 0.25, 10)
        elif name == "meat": ok = put("RottenMeat", u, v, 20)
        elif name == "tools": ok = put("BarrelWithTools1", hi - 0.6 if rng.random() < 0.5 else lo + 0.6, D - 0.6, 30)
        elif name == "stool": ok = put("Stool1", u, v, 28)
        else: ok = put("WaterBarrel", lo + 0.6, D - 0.6, 30)
        if ok: got.add(name)



# ---------------------------------------------------------------------------------------------------- QA round 1
# The user's QA round 1 (review/reviews/QA-round1.md; ledger review/qa1/setpieces.md): yards are composed as a whole,
# symmetric about the way in, in even rows, with more kinds of thing in them. Each lays its pieces in the yard's Frame.
COFFIN_ALONG = {"\\": "Coffin2", "/": "Coffin1"}        # a coffin lying along a screen line (kit/scenes.ALONG's kin)
GRAVE_PITCH = (1.5, 1.7)     # least squares between graves across and along their rows (49, 55 px; Westwood's 39-90)


class _Lay:
    """Pieces laid in a yard's frame, each kept clear of the others."""
    def __init__(self, spec, fr):
        self.spec, self.fr, self.placed = spec, fr, []

    def put(self, t, u, v, room=0.6, **extra):
        o = self.spec.obj_px(t, *self.fr.px(u, v), **extra)
        self.placed.append((u, v, room))
        return o

    def free(self, u, v, room=0.6):
        return all(math.hypot(u - a, v - b) >= max(room, r) for a, b, r in self.placed)


def _line_of_axis(ax):
    """The screen line a square axis runs along: i runs "\\" (north-west to south-east), j runs "/"."""
    return "\\" if ax in ("+i", "-i") else "/"


def _graveyard(spec, land, y, fr):
    """A graveyard composed as a whole and symmetric about its gate (QA round 1, graveyard: "the graves/headstones
    should be in symmetrical, even rows ... organization and balance"; EX-GRAVEYARD-05 "PERFECTLY": an iron fence, stone
    only for the back wall and the mausoleums; EX-GRAVEYARD-02 "center the mausoleum ... the obelisks on either side of
    the entrance look excellent"; EX-GRAVEYARD-06 "better if the mausoleum was not connected to the fence perimeter";
    EX-GRAVEYARD-10 and nox7 "the cobblestone path really adds a lot ... the gate is slightly off-centre with the
    path"; "never exclusively graves": coffins, dead trees, buckets of tools, barrels, torches, bones, skulls; "no big
    empty space with graves all on one side"):
    - the ground sparse grass (Westwood's GrassSparse2), the gate centred on its side (plan: an odd side), stone
      pillars (Monument1) either side of it outside;
    - a cobbled path from the gate straight up the yard's axis to the mausoleum's door, whole squares, centred on the
      gate;
    - the mausoleum centred on the back wall opposite the gate: built into the stone back wall (a field: one, a wide
      one, three side by side, or a pair flanking the path's end with a statue between) or standing free a walkway in
      from it (a crypt yard), never touching the fence; torch poles either side of its door; a pen: no mausoleum, a
      memorial at the path's end between two open-air sarcophagi;
    - the headstones in even rows filling the yard both sides of the path, mirrored, one kind to a row; a pair of fresh
      graves on dug earth now and then;
    - in two corners the gravedigger's work (an open grave of dug earth, the spade, the heap, a coffin, the bucket of
      tools, a skull and a bone) and, mirrored, the keeper's stores (barrels, a tool barrel, a coffin waiting); dead
      trees in the other two corners."""
    import random as _random, zlib
    rng = _random.Random(zlib.crc32(f"{spec.d['name']}:graveyard2:{y.gi},{y.gj}".encode()))
    arch = getattr(y, "arch", "field")
    lay = _Lay(spec, fr)
    half, D = fr.half, fr.D
    for s in yard_ground(y, land): spec.floor[square_tile(*s)] = "GrassSparse2"
    keep = []                                            # (u0, u1, v0, v1) boxes kept from the graves, mirrored

    def keep_box(u0, u1, v0, v1):
        keep.append((u0, u1, v0, v1))
        keep.append((-u1, -u0, v0, v1))

    # ---- the path's width: three squares, its middle one on the gate's axis (the tiles lie on whole u on a gate in any
    # side: Frame.squares); a narrow yard's path one square, so a column of graves fits each side of it (a gate in an i
    # side had a path of two squares, laid half a square off its gate: QA round 2 [Q2X-2])
    ph = 1.5 if half >= (6 if y.side in ("j0", "j1") else 5) else 0.5
    # ---- the mausoleum ------------------------------------------------------------------------------------------
    styles = []
    if arch != "pen" and D >= 9:
        if half >= 6.5: styles += ["row3", "pair", "wide"]
        if half >= 4.5: styles += ["wide", "single"]
        elif half >= 3.5: styles += ["single"]
    style = rng.choice(styles) if styles else None
    cells = {"single": [(-1.5, 1.5)], "wide": [(-2.5, 2.5)], "row3": [(-4.5, -1.5), (-1.5, 1.5), (1.5, 4.5)],
             "pair": [(-4.5, -1.5), (1.5, 4.5)]}.get(style, [])
    v0 = 2 if arch == "crypt_yard" else 0                # free-standing a walkway in from the back wall, or built into it
    depth = 3
    Vb = D - v0
    Vf = Vb - depth
    stone = "Cobblestone"
    crypt = rng.choice(("Crypt1", "Crypt3"))
    for Ua, Ub in cells:
        n_ = int(round(Ub - Ua))
        for k in range(n_ + 1):
            spec.wall(*point_cell(*fr.point(Ua + k, Vf)), stone)
            if v0: spec.wall(*point_cell(*fr.point(Ua + k, Vb)), stone)
        for V in range(int(Vf), int(Vb) + 1):
            spec.wall(*point_cell(*fr.point(Ua, V)), stone)
            spec.wall(*point_cell(*fr.point(Ub, V)), stone)
        for s in fr.squares(Ua + 0.2, Ub - 0.2, Vf + 0.2, Vb - 0.2):
            spec.floor[square_tile(*s)] = "GreenBrick"
        um = (Ua + Ub) / 2
        # a crypt's double door, its two halves either side of the axis (a single door had filled one of the two
        # middle cells, half a cell off the path: QA round 2 [Q2X-2], "one straight line from the gate's middle to the
        # mausoleum's door")
        door_between(spec, "CryptDoor", fr.point(um - 0.5, Vf), fr.point(um + 0.5, Vf))
        if n_ >= 5:                                       # a wide mausoleum: two sarcophagi side by side
            for d_ in (-1.0, 1.0): lay.put(crypt, um + d_, Vf + depth * 0.58, room=1.0)
        else:
            lay.put(crypt, um, Vf + depth * 0.55, room=1.0)
    if cells:
        Umax = max(Ub for _, Ub in cells)
        keep_box(0, Umax + 0.85, Vf - 1.3, D + 1)
        if style != "pair":                               # torch poles either side of the door
            for sd in (1, -1): lay.put("TorchPole", sd * (ph + 0.6), Vf - 0.8, room=0.7)
    crypt_box = list(keep[:2])
    # ---- the path ----------------------------------------------------------------------------------------------
    # (to the mausoleum's door: on a gate in a j side the walls run through the squares' middles, so the path takes the
    # square under the door's wall too, else half a square of grass is left before the door)
    # (from the gate's line, never out past it: a yard's paving stays inside its enclosure, QA round 2 [Q2T-6]; the
    # walk to the road, kit/yards.connect_gate, starts outside the gate)
    v_end = Vf if style in ("single", "wide", "row3") else (D - 0.6) if style == "pair" else (D - 2.4)
    for s in fr.squares(-ph + 0.05, ph - 0.05, 0.0, v_end):
        if land is None or (s in land.squares and s not in land.water): spec.floor[square_tile(*s)] = "RoughCobble"
    keep_box(0, ph + 0.4, -2, D + 1)
    # ---- what stands at the path's end -----------------------------------------------------------------------------
    if style == "pair":                                  # a statue between the two mausoleums
        # (facing the gate down the path: Statue1a faces +i, c +j, e -i, g -j, as Statue2's letters, kit/furnish
        # STATUE_FACING; QA round 2 [Q2T-3])
        lay.put("Statue1" + STATUE_LETTER[fr.axis(0, -1)], 0, D - 1.2, room=0.8)
    elif not cells:                                      # a memorial between two open-air sarcophagi
        lay.put("Monument1", 0, D - 1.5, room=0.9)
        for sd in (1, -1): lay.put(crypt, sd * (ph + 1.3), D - 1.6, room=1.2)
        keep_box(0, ph + 2.6, D - 3.0, D + 1)
    # ---- the gate's stone pillars outside, else torch poles (EX-GRAVEYARD-02) ---------------------------------------
    if rng.random() < 0.85:
        for sd in (1, -1): lay.put("Monument1", sd * 1.9, -0.8, room=0.6)
    else:
        for sd in (1, -1): lay.put("TorchPole", sd * 1.7, -0.7, room=0.6)
    # ---- the corners: the gravedigger's work and the keeper's stores, mirrored; dead trees in the other two ----------
    cu = half - 1.7

    def blocked(uc, vc):
        return any(a - 0.3 < abs(uc) + 1.0 and abs(uc) - 1.0 < b + 0.3 and c - 0.3 < vc + 1.2 and vc - 1.2 < d + 0.3
                   for a, b, c, d in crypt_box if a >= 0)
    back_ok = cu > 1.5 and not blocked(cu, D - 1.6)
    work_v, tree_v = (D - 1.6, 1.5) if back_ok else (1.6, None)
    dv_in = -1 if back_ok else 1                          # toward the yard's middle along v
    y.people = []
    line = _line_of_axis(fr.axis(0, 1))
    # (a small yard keeps to its graves, its path and its memorial: the corners' pieces had crowded a 5-square yard)
    room_ = (back_ok and half >= 4.5 and D >= 9) or (not back_ok and half >= 6 and D >= 11)
    if room_ and rng.random() < {"field": 0.85, "crypt_yard": 0.75}.get(arch, 0.6):
        s_ = rng.choice((1, -1))

        def at(a, b, side=s_):
            return side * cu - side * a, work_v + dv_in * b     # a: in toward the axis, b: along v toward the middle
        for b in (0, 1):                                 # the open grave: two squares of dug earth
            spec.floor[square_tile(*fr.square(*at(0, b)))] = "DirtDark2"
        lay.put("MiningShovelInGround", *at(0.1, -0.75), room=0.4)
        for t, a, b in (("CaveRocksPebbles", -0.75, 0.2), ("CaveRocksPebbles", -0.75, 0.7), ("CaveRocksSmall", -0.7, 1.25)):
            lay.put(t, *at(a, b), room=0.3)
        lay.put(COFFIN_ALONG[line], *at(1.25, 0.5), room=0.8)
        lay.put("BarrelWithTools1", *at(1.0, -0.6), room=0.6)
        lay.put("Skull", *at(0.4, 1.75), room=0.2)
        lay.put("LegBone", *at(0.75, 1.9), room=0.2)
        # the keeper's stores in the mirrored corner: barrels, a tool barrel, a coffin waiting
        o_ = -s_
        lay.put("Barrel", *at(-0.5, -0.55, o_), room=0.5)
        lay.put("Barrel2", *at(-0.5, 0.3, o_), room=0.5)
        lay.put("BarrelWithTools2", *at(0.35, -0.6, o_), room=0.5)
        lay.put(COFFIN_ALONG[line], *at(1.25, 0.5, o_), room=0.8)
        keep_box(cu - 2.1, half, min(work_v, work_v + dv_in * 2.3) - 0.6, max(work_v, work_v + dv_in * 2.3) + 0.8)
        y.people.append((("Con03A", "Kenneth"), fr.px(*at(1.05, 1.45)), fr.px(*at(0, 0.5))))
        trees_v = tree_v
    else:
        trees_v = work_v if tree_v is None else (work_v if rng.random() < 0.5 else tree_v)
    if trees_v is not None and half >= 4.5 and D >= 8 and not blocked(cu, trees_v):
        t = rng.choice(DEAD_TREES)
        for sd in (1, -1): lay.put(t, sd * (half - 1.4), trees_v, room=1.4)
        keep_box(half - 2.6, half, trees_v - 1.5, trees_v + 1.5)
    # ---- the graves: even rows both sides of the path, mirrored, one kind to a row ---------------------------------
    palette = {_pick(rng, TOMBSTONES): 4.0}
    others = sorted(k for k in TOMBSTONES if k not in palette)
    rng.shuffle(others)
    palette.update({k: 1.0 for k in others[:2]})
    # (even spacing across the room each side of the path and along the yard, never under Westwood's closest pair of
    # headstones, 39 px: a lattice of whole squares had left a narrow yard one column a side, s2)
    def spread(lo, hi, pitch):
        if hi < lo - 1e-6: return []
        n = int((hi - lo) / pitch + 1e-6) + 1
        return [(lo + hi) / 2] if n == 1 else [lo + (hi - lo) * k / (n - 1) for k in range(n)]
    cols = spread(ph + 0.85, half - 0.9, GRAVE_PITCH[0])
    rows = spread(2.0, D - 1.0, GRAVE_PITCH[1])

    def inside(u, v):
        return any(a - 1e-6 <= u <= b + 1e-6 and c - 1e-6 <= v <= d + 1e-6 for a, b, c, d in keep)
    graves = []
    for v in rows:
        t = _pick(rng, palette)
        for u in cols:
            if inside(u, v) or inside(-u, v) or inside(u, v - 0.85) or inside(-u, v - 0.85): continue
            for sd in (1, -1):
                lay.put(t, sd * u, v, room=0.9)
            graves.append((u, v))
    # fresh graves: a mirrored pair on dug earth now and then (the square before the headstone)
    if graves and rng.random() < 0.8:
        u, v = rng.choice(graves)
        for sd in (1, -1):
            spec.floor[square_tile(*fr.square(sd * u, v - 0.85))] = "DirtDark2"
    y.n_graves = 2 * len(graves)
    return lay.placed


def _orchard(spec, land, y, fr):
    """An orchard in even rows (QA round 1, nox6: "Good structure for an orchard, but too empty. Add a few crates of
    apples and some apples on the ground that the player can pick up"): apple trees (TreeApple) in rows mirrored about
    the gate's axis, a walk up the middle; apples (RedApple, which the player picks up) on the ground under them; a
    crate of apples either side of the gate outside; the tool barrel and a barrel in the back corners; flowers along
    the fence."""
    import random as _random, zlib
    rng = _random.Random(zlib.crc32(f"{spec.d['name']}:orchard:{y.gi},{y.gj}".encode()))
    lay = _Lay(spec, fr)
    half, D = fr.half, fr.D
    lo, hi = 1.25, half - 1.15
    n = max(1, int((hi - lo) / 1.9) + 1)
    cols = [lo + (hi - lo) * k / (n - 1) for k in range(n)] if n > 1 else [(lo + hi) / 2]
    r0, r1 = 2.3, D - 1.3
    m = max(1, int((r1 - r0) / 2.0) + 1)
    rows = [r0 + (r1 - r0) * k / (m - 1) for k in range(m)] if m > 1 else [(r0 + r1) / 2]
    for v in rows:
        for u in cols:
            for sd in (1, -1):
                lay.put("TreeApple", sd * u, v, room=1.4)
                # windfalls below the tree on screen, where its crown does not hide them (the user: "apples on the
                # ground that the player can pick up")
                x, y_ = fr.px(sd * u, v)
                for _ in range(rng.choice((1, 1, 2))):
                    spec.obj_px("RedApple", x + rng.uniform(-26, 26), y_ + rng.uniform(22, 40))
    # crates of the picked apples outside the gate, either side of it, where they are seen (inside, the tall log fence
    # and the crowns hid them)
    for sd in (1, -1):
        lay.put("TraderAppleCrate", sd * 1.9, -0.8, room=0.6)
    lay.put("BarrelWithTools1", half - 0.8, D - 0.8, room=0.6)
    lay.put("Barrel", -(half - 0.8), D - 0.8, room=0.6)
    for sd in (1, -1):                                    # flowers along the side fences, between the rows
        for v in rows[:-1]:
            u_ = sd * (half - 0.55)
            if lay.free(u_, v + 1.0, 0.5):
                lay.put(rng.choice(("FlowersYellowSparse", "FlowersWhiteSparse")), u_, v + 1.0, room=0.4)
    return lay.placed


def lay_crop_rows(spec, fr, rng, walk=True, start=1.5, step=0.7, end_pad=0.8, objects=True, crops=None):
    """Crops in even rows on dug earth, mirrored about the frame's axis (QA round 1, the garden: "space rows of crops
    out and make them even and balanced ... Use fewer plants per row and space them out a little bit more"; nox2's
    garden, "more or less perfect": straight parallel rows inside the fence on dark earth). The rows run away from the
    way in; a wide plot keeps a walk up the middle. Each row one crop, a row and its mirror alike. With objects: the
    water barrel and the tool barrel either side of the way in. Returns the plants laid."""
    half, D = fr.half, fr.D
    lim = half - 0.75
    if walk and half >= 3.4:
        w0 = 0.5 if fr.lat == 0.0 else 1.0
        offs = []
        u = w0 + 0.6
        while u <= lim + 1e-6:
            offs.append(u)
            u += 1.15
    else:
        n = max(1, int(2 * lim / 1.1) + 1)
        offs = sorted({round(abs(-lim + 2 * lim * k / (n - 1)), 4) for k in range(n)} if n > 1 else {0.0})
    order = list(crops or CROPS)
    rng.shuffle(order)
    # a narrow plot's barrels stand at its far end: by the gate they would stand in its straight way in
    far = objects and half - 0.6 < 1.25
    if far: end_pad = max(end_pad, 1.45)
    v0, v1 = start, D - end_pad
    np_ = max(2, int((v1 - v0) / step) + 1)
    vs = [v0 + (v1 - v0) * k / (np_ - 1) for k in range(np_)]
    laid = 0
    for k, u in enumerate(sorted(offs)):
        crop = order[k % len(order)]
        for sd in ((1, -1) if u > 1e-6 else (1,)):
            for v in vs:
                spec.obj_px(crop, *fr.px(sd * u, v))
                laid += 1
    if objects:
        # in the corners either side of the way in, clear of the gate's straight way in (composition.way_in)
        a, v_ = max(0.6, half - 0.6), (D - 0.7 if far else 0.7)
        spec.obj_px("WaterBarrel", *fr.px(a, v_))
        spec.obj_px("BarrelWithTools1", *fr.px(-a, v_))
    return laid


def _field(spec, land, y, fr):
    """The town's field (nox2's garden, the user's "more or less perfect"): a low wooden fence and its gate round dug
    earth, the crops in even rows mirrored about the gate's axis, the water barrel and the tool barrel inside the gate,
    the harvest (a sack, a crate of apples) outside the far corners."""
    import random as _random, zlib
    rng = _random.Random(zlib.crc32(f"{spec.d['name']}:field:{y.gi},{y.gj}".encode()))
    lay_crop_rows(spec, fr, rng)
    for sd in (1, -1):
        spec.obj_px(rng.choice(("SackChestLarge1", "SackChestLarge2")) if sd > 0 else "TraderAppleCrate",
                    *fr.px(sd * (fr.half - 0.55), fr.D + 0.75))
    return []
