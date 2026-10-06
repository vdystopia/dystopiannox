"""Yards (generator v3): gated outdoor plots with a purpose, as Westwood fences them in its towns
(rules/town_walls.py; measured on Con02a, Con08a, War03b, War03c, War03d, War04a and Wiz08a):

- graveyard: one of Westwood's three kinds (`GRAVE_ARCH`): a field (stone back wall with its crypt cells, iron fence,
  wide rough rows of headstones, dead trees by the walls), a crypt yard (a fenced lawn, a crypt in a corner, a knot of
  stones by it) or a pen (a small stone-walled court, four to six stones); sparse grass; the gravedigger's corner (a
  fresh grave and the bucket of tools: the user's ask, SW-9) in most fields (`_graveyard`);
- orchard: a log fence (Log, BarredGate) round 22-28 tiles of grass: fruit bushes (Plant5, Plant4), one tree,
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
    "orchard": dict(fence="Log", gate="BarredGate", floor=None, size=[(5, 5), (6, 5)], purpose="the town's fruit trees"),
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
}
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
GRAVE_SIZE = {"crypt_yard": [(10, 9), (10, 10), (11, 9)], "pen": [(6, 6), (7, 6), (7, 7)]}
DEAD_TREES = ("TreeOgre08", "TreeOgre10", "TreeTrunk6")          # War03b-d's dead trees by the yard's walls


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
    side = min(mids, key=lambda s: math.hypot(mids[s][0] - tx, mids[s][1] - ty))
    y = Yard(kind, gi, gj, w, h, side)
    if kind == "jail": y.arch = arch
    if kind == "graveyard":
        import random as _random, zlib
        y.arch = arch
        ar = _random.Random(zlib.crc32(f"graveyard:walls:{gi},{gj}:{arch}".encode()))
        back = {"i0": "i1", "i1": "i0", "j0": "j1", "j1": "j0"}[side]
        flanks = [f for f in ("i0", "i1", "j0", "j1") if f not in (side, back)]
        if arch == "field":                   # the stone wall behind (its crypt row), often down a flank too
            y.walls = {back: "Cobblestone"}
            if ar.random() < 0.5: y.walls[ar.choice(flanks)] = "Cobblestone"
        elif arch == "pen":                   # walled in stone all round
            y.walls = {f: "Cobblestone" for f in ("i0", "i1", "j0", "j1")}
        elif ar.random() < 0.3:               # a crypt yard against a stone wall now and then (Con07B's by the street)
            y.walls = {back: "Cobblestone"}
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


def build(spec, rng, land, y):
    """Lay the yard planned by `plan`: its floor, its fence and gate, what it holds. Returns the objects placed."""
    rec = YARDS[y.kind]
    if rec["floor"]:
        for s in y.plot: spec.floor[square_tile(*s)] = rec["floor"]
    sides = _fence_points(y)
    walls = getattr(y, "walls", {})
    for side_ in sorted(sides, key=lambda f: f in walls):     # (a stone side's corners stone)
        for p in sides[side_]:
            spec.wall(*point_cell(*p), walls.get(side_, rec["fence"]))
    pts = sides[y.side]
    n_cells = rec.get("cells", 1)
    if n_cells > 1:
        return _jail(spec, rng, y, rec, pts)
    # the gate: a two-cell opening in the middle of its side (a double gate hangs a half at each end)
    k = len(pts) // 2
    a, b = point_cell(*pts[k - 1]), point_cell(*pts[k])
    line = "\\" if (b[0] - a[0], b[1] - a[1]) == (1, 1) else "/"
    y.gate = spec.door(rec["gate"], a, line)
    gm = ((pts[k - 1][0] + pts[k][0]) / 2, (pts[k - 1][1] + pts[k][1]) / 2 - 0.5)  # the gate's middle, as drawn
    y.gate_mid = gm
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
        _graveyard(spec, rng, y, yj, free_spot, put, gm, lambda si, sj, room: placed.append((si, sj, room)))
    elif y.kind == "orchard":
        tree = (y.gi + y.w - 1.4, yj + y.h - 2.4) if y.side in ("i0", "j0") else (y.gi + 1.4, yj + 0.4)
        put("TreeForest11", *tree, room=1.6)
        for si in [y.gi + 1.0 + 1.4 * k for k in range(int((y.w - 1.6) / 1.4) + 1)]:
            for sj in [yj - 1 + 1.0 + 1.4 * k for k in range(int((y.h - 1.6) / 1.4) + 1)]:
                s = (si + jit() * 0.5, sj + jit() * 0.5)
                if free_spot(*s, pad=0.8, lane_w=0.9): put(rng.choice(("Plant5", "Plant5", "Plant4")), *s, room=1.1)
        for t in ("FlowersYellowSparse", "FlowersYellowSparse", "FlowersWhiteSparse"):     # no apples: food on the
                                                                                     # ground can be picked up
            for _ in range(20):
                s = (rng.uniform(y.gi + 0.7, y.gi + y.w - 0.7), rng.uniform(yj - 0.3, yj + y.h - 1.7))
                if free_spot(*s, pad=0.6, lane_w=0.8): put(t, *s, room=0.5); break
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
        # one crop in rows, the rows centred in the fence with a walkable strip all round (Ambermere playtest,
        # 2026-10-05: "the northeast stretch of fence overlaps with the row of crops"), bare earth between the rows; the
        # rows run away from the gate, so the lane from it runs between them
        crop = rng.choice(CROPS)
        # two or three crops, each its own band of rows (Con05A's town garden: corn, tomatoes and cabbage side by side)
        bands = [crop] + [c for c in CROPS if c != crop][:1 + (rng.random() < 0.5)]
        rows_i = y.side in ("j0", "j1")
        I0, I1, J0, J1 = y.gi, y.gi + y.w, yj - 1, yj - 1 + y.h
        across = (I0, I1) if not rows_i else (J0, J1)
        along = (J0, J1) if not rows_i else (I0, I1)
        rws = _spread(across[0] + 0.85, across[1] - 0.85, 1.25)
        for k_, r in enumerate(rws):
            crop_ = bands[min(len(bands) - 1, k_ * len(bands) // len(rws))]
            for a in _spread(along[0] + 0.75, along[1] - 0.75, 0.42):
                si, sj = (r, a) if not rows_i else (a, r)
                if free_spot(si, sj, pad=0.6, lane_w=0.7, t=crop_): put(crop_, si, sj, room=0.3)
        for t_ in ("WaterBarrel", "MiningShovelInGround"):           # the barrel and the spade by the gate, inside
            for f_ in (0.3, 0.7):
                s_ = (gm[0] + (ci - gm[0]) * 0.25 + (cj - gm[1]) * (f_ - 0.5) * 0.6, gm[1] + (cj - gm[1]) * 0.25 - (ci - gm[0]) * (f_ - 0.5) * 0.6)
                if free_spot(*s_, pad=0.6, lane_w=0.6, t=t_): put(t_, *s_, room=0.5); break
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
        # the rock face at the back: big rocks and pillars along the walls away from the gate, rubble in the open
        back = {"i0": "i1", "i1": "i0", "j0": "j1", "j1": "j0"}[y.side]
        bx = {"i0": y.gi + 1.2, "i1": y.gi + y.w - 1.2}.get(back)
        by_ = {"j0": yj - 1 + 1.2, "j1": yj + y.h - 2.2}.get(back)
        along = [yj - 1 + 1.3 + 1.6 * k for k in range(int((y.h - 2) / 1.6) + 1)] if bx is not None else \
                [y.gi + 1.3 + 1.6 * k for k in range(int((y.w - 2) / 1.6) + 1)]
        for t in along:
            s = (bx + jit(), t + jit()) if bx is not None else (t + jit(), by_ + jit())
            big = rng.choices(("CaveRocksHuge", "CaveRockPillarShort2", "CaveRocksLarge", "CaveRocksMedium"), (3, 2, 2, 2))[0]
            if free_spot(*s, pad=0.9, lane_w=1.3): put(big, *s, room=1.3)
        # in the open, as many as Westwood's quarry yards hold (Con02a, War03b, War08a: 17-24 pebbles, 6-9 medium
        # rocks, 4-6 huge ones, 3-4 short pillars, 2-4 barren plants)
        for t, n in (("CaveRocksHuge", 2), ("CaveRockPillarShort1", 1), ("CaveRocksMedium", 7), ("CaveRocksSmall", 4),
                     ("CaveRocksPebbles", 18), ("PlantBarren1", 3), ("MiningPickAxeInGround1", 1),
                     ("MiningShovelInGround", 1)):
            for _ in range(n):
                for _try in range(15):
                    s = (rng.uniform(y.gi + 0.8, y.gi + y.w - 0.8), rng.uniform(yj - 0.2, yj + y.h - 1.8))
                    if free_spot(*s, pad=0.7, lane_w=1.2): put(t, *s, room=0.6 if "Pebbles" in t else 0.9); break
    return placed



# Westwood's eleven campaign jails are of two kinds (rules/scenes/jail.md "Archetypes"):
# - cell_row (9 of 11: Con07B x7, War07A, War03c's pit): a row of two to four cells side by side along a wall, a barred
#   door into each with a wall torch beside it outside; inside, variety: one cell bare, one with a cot, one deep in straw;
# - guardhouse (2 of 11: Con02a, War03b): two cells at the back of a stone house, the guardroom before them with the
#   guards' racks along its walls, a table and a water barrel, its own door.
JAIL_ARCH = (("cell_row", 9), ("guardhouse", 2))
JAIL_SIZE = {"cell_row": [(6, 3), (9, 3), (9, 3)], "guardhouse": [(6, 6)]}
GUARD_RACKS = ("TraderBowRack2", "TraderQuiverRack", "TraderPoleArm1", "TraderPoleArm2")


def jail_arch(centre, weights=JAIL_ARCH):
    """A jail's archetype by Westwood's frequencies, from its own generator (its place)."""
    import random as _random, zlib
    r = _random.Random(zlib.crc32(f"jail:arch:{centre[0]:.1f},{centre[1]:.1f}".encode()))
    return r.choices([a for a, _ in weights], [w for _, w in weights])[0]


def _jail(spec, rng, y, rec, pts):
    """The jail's cells (and a guardhouse's guardroom) inside the stone walls `build` laid: the dividing walls, a
    JailDoor into each cell, a torch beside each door outside it (Westwood's: one to every barred door), the cells
    furnished each its own way (bare, a cot, deep straw). Sets y.gate, y.cells (the doors) and y.cell_mids (each cell's
    middle, px). The design's generator draws what the first jails drew, so a map round it is laid as before."""
    import random as _random, zlib
    from kit import scenes as S
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

    def door(u, v, kind):
        a, b = point_cell(*pt(u, v)), point_cell(*pt(u + 1, v))
        return spec.door(kind, a, "\\" if (b[0] - a[0], b[1] - a[1]) == (1, 1) else "/")

    for c in range(rec.get("cells", 2)):           # (the draws the first jails made)
        for _ in range(rng.randint(1, 2)): rng.uniform(0, 1); rng.uniform(0, 1)
    own = _random.Random(zlib.crc32(f"{spec.d['name']}:jail:{y.gi},{y.gj}".encode()))
    n = 2 if arch == "guardhouse" else max(2, L // 3)
    v_cells = 3 if arch == "guardhouse" else 0     # where the cells' front wall stands
    if v_cells:
        for u in range(0, L + 1): spec.wall(*point_cell(*pt(u, v_cells)), rec["fence"])
    # (round 7, the judges: "doors and torches at exact even spacing; the cells bare, straw, cot in strict order"):
    # the cells of uneven widths, each door where it falls in its cell, the torch on either side of it a step or so off
    # (one door in six without), the cells furnished each by its own draw (two alike now and then), from the jail's
    # own hand-generator so its other draws are as before
    hand = _random.Random(zlib.crc32(f"{spec.d['name']}:jail-hand:{y.gi},{y.gj}".encode()))
    widths = [2] * n
    for _ in range(L - 2 * n): widths[hand.randrange(n)] += 1
    if arch == "guardhouse": widths = [L // 2, L - L // 2]
    bounds = [sum(widths[:k]) for k in range(n + 1)]
    for u_k in bounds[1:-1]:                       # the walls between the cells
        for v in range(v_cells, D + 1): spec.wall(*point_cell(*pt(u_k, v)), rec["fence"])
    doors, mids = [], []
    side_t = 1 if own.random() < 0.5 else -1       # (the draw the first jails made)
    for c in range(n):
        lo, hi = bounds[c], bounds[c + 1]
        du_ = hand.randint(lo + 1, max(lo + 1, hi - 2))
        doors.append(door(du_, v_cells, rec["gate"]))
        mids.append(square_px(*at((lo + hi) / 2, (v_cells + D) / 2)))
        sd_ = hand.choice((1, -1))
        tu = du_ + 0.5 + sd_ * hand.uniform(0.85, 1.35)
        if not (lo + 0.3 < tu < hi - 0.3) and arch != "cell_row":
            tu = du_ + 0.5 - sd_ * hand.uniform(0.85, 1.1)
        if (lo + 0.3 < tu < hi - 0.3 or arch == "cell_row") and (c == 0 or hand.random() >= 1 / 6):
            spec.obj_px("Torch", *square_px(*at(tu, v_cells - 0.3 - hand.uniform(0, 0.12))))
    y.gate, y.cells, y.cell_mids = doors[0], doors, mids
    # the cells' furnishing: bare, a cot or deep in straw, each cell its own draw, never all alike
    kinds = ["bare", "cot", "straw"]
    own.shuffle(kinds)
    kinds = [hand.choices(("straw", "cot", "bare"), (0.45, 0.3, 0.25))[0] for _ in range(n)]
    if len(set(kinds)) == 1 and n > 1: kinds[hand.randrange(n)] = hand.choice([k for k in ("straw", "cot", "bare")
                                                                              if k != kinds[0]])
    if arch == "guardhouse": kinds = ["cot", own.choice(("straw", "cot"))]       # (Con02a, War03b: a cot in each)
    else: own.choice(("bare", "straw"))
    for c, kind in enumerate(kinds):
        lo, hi = bounds[c], bounds[c + 1]
        laid = []
        if kind == "cot":
            cu = (lo + hi) / 2 + own.uniform(-0.4, 0.4)
            spec.obj_px(own.choice(("Cot2", "Cot2", "Cot1")), *square_px(*at(cu, D - 0.8)))
            laid.append((cu, D - 0.8))
        n_s = {"cot": own.choice((0, 1, 2, 3)), "straw": own.randint(6, 10)}.get(kind, 0)
        fu, fv = own.uniform(lo + 0.9, hi - 0.9), own.uniform(v_cells + 1.0, D - 0.9)     # a drift, not a carpet
        for _ in range(n_s):
            for _try in range(12):
                su = min(hi - 0.5, max(lo + 0.5, own.gauss(fu, 0.6)))
                sv = min(D - 0.45, max(v_cells + 0.6, own.gauss(fv, 0.5)))
                if all(math.hypot(su - a, sv - b) >= (0.9 if (a, b) == laid[0] and kind == "cot" else 0.45)
                       for a, b in laid):
                    spec.obj_px("Straw2" if own.random() < 0.85 else "Straw1", *square_px(*at(su, sv)))
                    laid.append((su, sv))
                    break
    if arch == "guardhouse":
        # the guardroom: its door in the front wall off the middle, the racks along its side walls, the table, the
        # water barrel in a corner (Con02a, War03b)
        du = own.choice((1, L - 2))
        door(du, 0, "WoodenDoor")
        y.gate = doors[0]
        ex, ey = square_px(*at(1, 0)); fx, fy = square_px(*at(0, 0))
        line_u = S.line_of(ex - fx, ey - fy)                      # the screen line the front wall runs along
        line_v = "/" if line_u == "\\" else "\\"
        racks = list(GUARD_RACKS)
        own.shuffle(racks)
        spots = [(0.6, 1.0, line_v), (0.6, 2.2, line_v), (L - 0.6, 1.0, line_v), (L - 0.6, 2.2, line_v)]
        for (u, v, ln), t in zip(spots[:own.randint(3, 4)], racks):
            t = S.ALONG[ln].get(t, t)
            spec.obj_px(t, *square_px(*at(u, v)))
        spec.obj_px("Table1", *square_px(*at(L / 2 + own.uniform(-0.4, 0.4), 1.6)))
        wu = L - 0.7 if du == 1 else 0.7
        spec.obj_px("WaterBarrel", *square_px(*at(wu, 0.6)))
    return []

def _crypts(spec, rng, y, reserve, cells=1, depth=3, span=3, v0=1, corner=False):
    """Crypt cells along the yard's back side, as Westwood sets its graveyards against their crypts (War03b, War03c,
    War03d: a row of cobblestone cells, green brick inside, a sarcophagus (Crypt1/Crypt3) in each, a wooden door into
    the yard; Con07B, Con09b: one stone crypt in the yard). The cells stand at one end of the back side, their back and
    end walls the fence's own line. Returns the squares of the door's step in the yard (continuous), one per cell."""
    back = {"i0": "i1", "i1": "i0", "j0": "j1", "j1": "j0"}[y.side]
    gi, gj, w, h = y.gi, y.gj, y.w, y.h
    U = h if back in ("i0", "i1") else w
    # v0 = 1: a square in from the back fence, standing free (the blind judge, 2026-10-05: "the crypt jammed into the
    # fence line or a fence corner"; Con07B's crypt stands in its yard); v0 = 0: built into a stone back wall, as
    # War03b-d's crypt rows are
    if U < cells * span + 4 or (w if back in ("i0", "i1") else h) < depth + v0 + 5: return []
    def pt(u, v):                       # a wall point: u along the back side, v in from it
        if back == "i1": return (gi + w - v, gj - 1 + u)
        if back == "i0": return (gi + v, gj - 1 + u)
        if back == "j1": return (gi + u, gj + h - 1 - v)
        return (gi + u, gj - 1 + v)
    def sq(u, v):                       # the square whose corner nearest the back's low end is (u, v)
        p, q = pt(u + 0.5, v + 0.5)
        return int(math.floor(p)), int(math.floor(q)) + 1
    start = (U - cells * span) // 2 + rng.choice((-1, 0, 0, 1))     # about the back side's middle, off its corners
    start = max(2, min(U - cells * span - 2, start))
    if corner: start = rng.choice((1 + v0, U - cells * span - 1 - v0))      # a crypt yard's crypt in a back corner
    u0s = [start + k * span for k in range(cells)]
    steps = []
    for u0 in u0s:
        for u in range(u0, u0 + span + 1):
            for v in (v0, v0 + depth):
                spec.wall(*point_cell(*pt(u, v)), "Cobblestone")
        for v in range(v0, v0 + depth + 1):
            for u in (u0, u0 + span):
                spec.wall(*point_cell(*pt(u, v)), "Cobblestone")
        for u in range(u0, u0 + span):
            for v in range(v0, v0 + depth):
                s_ = sq(u, v)
                spec.floor[square_tile(*s_)] = "GreenBrick"
        # the door in the front wall's middle, into the yard
        um = u0 + span // 2
        a, b = point_cell(*pt(um, v0 + depth)), point_cell(*pt(um + 1, v0 + depth))
        line = "\\" if (b[0] - a[0], b[1] - a[1]) == (1, 1) else "/"
        spec.door("WoodAndSteelDoor", a, line)
        # the sarcophagus in the middle of the cell, long across the door's line
        cu, cv = u0 + span / 2, v0 + depth * 0.45
        ci_, cj_ = pt(cu, cv)
        spec.obj_px(rng.choice(("Crypt1", "Crypt3")), *square_px(ci_, cj_ - 0.5))
        for u in range(u0 - 1, u0 + span + 1):
            for v in range(0, v0 + depth + 1):
                p_, q_ = pt(u + 0.5, v + 0.5)
                reserve(p_, q_ - 0.5, 0.75)
        p_, q_ = pt(um + 0.5, v0 + depth + 0.7)
        steps.append((p_, q_ - 0.5))
    return steps


def _graveyard(spec, rng, y, yj, free_spot, put, gm, reserve):
    """A graveyard as Westwood lays one, and as a place that is used (Starwell playtest, 2026-10-05: "Graveyards mostly
    look good, but it would look better if there were actually some graves. Maybe a bucket of tools. More diversity of
    objects"). One of Westwood's three kinds (`y.arch`, set by `plan`; rules/scenes/graveyard.md "Archetypes"):
    - field: the stone back wall with its crypt cells built into it (70%), headstones in wide rough rows over the whole
      yard (Westwood's 100-130 px apart), a dead tree or two by the walls (60%), barren weeds by a few stones;
    - crypt_yard: a stone crypt in a back corner, a knot of four to eight headstones near it, the lawn open;
    - pen: a small stone-walled court, four to six stones of one kind, a wall torch now and then.
    The ground sparse grass (GrassSparse2). The gravedigger's corner (the user's ask, SW-9) in most fields and some crypt
    yards: a fresh grave of dark earth with its heap, the bucket of tools (BarrelWithTools1), a torch pole now and then;
    never a coffin, a spade or a pick (Westwood's graveyards have none: the judge, 2026-10-06). Stone pillars as gateposts
    now and then; never a bench or flowers."""
    import random as _random, zlib
    # the yard's own generator (the map and the plot): tuning a graveyard never shifts the rest of the map (a changed
    # yard had moved Harrowby's planting until a bush stood in a ruin's doorway)
    rng = _random.Random(zlib.crc32(f"{spec.d['name']}:graveyard:{y.gi},{y.gj}".encode()))
    arch = getattr(y, "arch", "field")
    walls = getattr(y, "walls", {})
    I0, I1, J0, J1 = y.gi, y.gi + y.w, yj - 1, yj - 1 + y.h
    ci, cj = y.centre
    back = {"i0": "i1", "i1": "i0", "j0": "j1", "j1": "j0"}[y.side]
    for s in y.plot:                                            # the yard's sparse grass (Westwood: GrassSparse2)
        spec.floor[square_tile(*s)] = "GrassSparse2"
    # the headstones' kinds: one in a pen, a main kind and two or three others in a field (War03b-d: Tombstone1 the most)
    main = _pick(rng, TOMBSTONES)
    others = sorted(k for k in TOMBSTONES if k != main)
    rng.shuffle(others)
    palette = {main: 1.0} if arch == "pen" else \
        dict([(main, 3.0)] + [(k, 1.0) for k in others[:rng.choice((1, 2, 3) if arch == "field" else (1, 2))]])
    # ---- the crypts -------------------------------------------------------------------------------------------------
    steps = []
    if arch == "field" and rng.random() < 0.7:
        # (a cell under 3 x 3 squares put its sarcophagus in its doorway: Starwell, doorways.blocked; a small yard
        # keeps to one cell, or its graves had no room: Harrowby, two graves)
        big_ = max(y.w, y.h) >= 13
        n_c = rng.choice((1, 2, 2, 3)) if big_ else 1
        v0 = 0 if walls.get(back) == "Cobblestone" else 1     # built into the stone wall, as War03b-d's rows
        steps = _crypts(spec, rng, y, reserve, cells=n_c, depth=3, span=rng.choice((3, 3, 4)) if big_ else 3, v0=v0)
        if not steps and n_c > 1: steps = _crypts(spec, rng, y, reserve, cells=1, depth=3, span=3, v0=v0)
    elif arch == "crypt_yard":
        v0 = 0 if walls.get(back) == "Cobblestone" else 1
        steps = _crypts(spec, rng, y, reserve, cells=1, depth=3, span=3, v0=v0, corner=True)
    # ---- the walk: paving from the gate in, now and then (War03c paves one; most have none) ---------------------------
    if steps: end_ = steps[0]
    else: end_ = (2 * ci - gm[0], 2 * cj - gm[1])
    ex_, ey_ = end_[0] - gm[0], end_[1] - gm[1]
    if abs(ex_) > abs(ey_): end_ = (end_[0], gm[1])             # along the grid: the walk runs square to the gate
    else: end_ = (gm[0], end_[1])
    tx_, ty_ = end_
    walk_on = arch != "pen" and rng.random() < (0.4 if steps else 0.2)
    n_ = int(math.hypot(tx_ - gm[0], ty_ - gm[1]) / 0.4) + 1
    for k_ in range(n_ + 1 if walk_on else 0):
        si_, sj_ = gm[0] + (tx_ - gm[0]) * k_ / n_, gm[1] + (ty_ - gm[1]) * k_ / n_
        for o_ in (-0.5, 0.5):
            sqr = (int(math.floor(si_ + (o_ if abs(ey_) >= abs(ex_) else 0))),
                   int(math.floor(sj_ + 0.5 + (o_ if abs(ex_) > abs(ey_) else 0))) + 1)
            if sqr in y.plot: spec.floor[square_tile(*sqr)] = "RoughCobble"
        reserve(si_, sj_, 1.5 if max(y.w, y.h) >= 12 else 1.2)       # (a headstone had stood on the paved walk;
        #                                                       round 7, the judges: "several on the paving itself")
    if not walk_on:
        reserve(gm[0] + (ci - gm[0]) * 0.25, gm[1] + (cj - gm[1]) * 0.25, 1.2)    # the way in from the gate kept clear
    # ---- the dead trees by the walls (a field's: War03b-d) ------------------------------------------------------------
    if arch == "field" and rng.random() < 0.6:
        for _ in range(rng.choice((1, 1, 2))):
            for _try in range(20):
                f_ = rng.choice([f for f in ("i0", "i1", "j0", "j1") if f != y.side])
                u_ = rng.uniform(0.2, 0.8)
                s_ = {"i0": (I0 + 1.1, J0 + (J1 - J0) * u_), "i1": (I1 - 1.1, J0 + (J1 - J0) * u_),
                      "j0": (I0 + (I1 - I0) * u_, J0 + 1.1), "j1": (I0 + (I1 - I0) * u_, J1 - 1.1)}[f_]
                if free_spot(*s_, pad=0.9, lane_w=1.3):
                    put(rng.choice(DEAD_TREES), *s_, room=1.7)
                    break
    # ---- the gravedigger's corner (SW-9): a back corner away from the gate's lane and the crypt ------------------------
    corners = [(I0 + 1.4, J0 + 1.4), (I1 - 1.4, J0 + 1.4), (I0 + 1.4, J1 - 1.4), (I1 - 1.4, J1 - 1.4)]
    far = max(corners, key=lambda c: math.hypot(c[0] - gm[0], c[1] - gm[1]) +
              (2 * min(math.hypot(c[0] - a, c[1] - b) for a, b in steps) if steps else 0))
    gi_, gj_ = int(math.floor(far[0])), int(math.floor(far[1])) + 1             # its square
    oi, oj = gi_ + 0.5, gj_ - 0.5                                               # the open grave's middle
    y.people = []
    dig_p = {"field": 0.6, "crypt_yard": 0.4}.get(arch, 0.0)
    if rng.random() < dig_p and free_spot(oi, oj, pad=0.8, lane_w=1.2):
        dx = 1 if oi < ci else -1
        dy = 1 if oj < cj else -1
        # the fresh grave: two squares of dark earth, the heap thrown up beside it
        for sq_ in ((gi_, gj_), (gi_ + dx, gj_)):
            if sq_ in y.plot: spec.floor[square_tile(*sq_)] = "DirtDark2"
        hx, hy = oi + 0.5 * dx, oj - 0.75 * dy
        for k_, t in enumerate(("CaveRocksPebbles", "CaveRocksPebbles", "CaveRocksSmall")[:rng.randint(2, 3)]):
            if free_spot(hx + 0.25 * k_ * dx, hy, pad=0.5, lane_w=1.0):
                put(t, hx + 0.25 * k_ * dx, hy, room=0.3)
        # the bucket of tools by the grave (the user's ask, SW-9), a torch pole to work by now and then
        for t, (a, b), room, p_ in (("BarrelWithTools1", (1.3 * dx, -0.6 * dy), 0.7, 1.0),
                                    ("TorchPole", (-0.9 * dx, -0.9 * dy), 0.7, 0.25)):
            if rng.random() >= p_: continue
            for da, db in ((0, 0), (0.3 * dx, 0.3 * dy), (-0.3 * dx, 0.4 * dy)):
                if free_spot(oi + a + da, oj + b + db, pad=0.55, lane_w=1.1, t=t):
                    put(t, oi + a + da, oj + b + db, room=room)
                    break
        reserve(oi, oj, 1.3)                                              # the open grave keeps its square
        mx_, my_ = square_px(oi - 0.9 * dx, oj + 0.2 * dy)
        y.people.append((("Con03A", "Kenneth"), (mx_, my_), square_px(oi, oj)))      # (donor map, script name)
    # ---- the gateposts: a stone pillar either side of the gate, outside it (War03b, War03c, Con09b: Monument1 pairs) --
    side = (-(cj - gm[1]), ci - gm[0])
    L = math.hypot(*side) or 1
    inw = ((ci - gm[0]) / (math.hypot(ci - gm[0], cj - gm[1]) or 1), (cj - gm[1]) / (math.hypot(ci - gm[0], cj - gm[1]) or 1))
    for d in ((1.5, -1.5) if rng.random() < {"field": 0.35, "crypt_yard": 0.25}.get(arch, 0.0) else ()):
        si, sj = gm[0] + side[0] / L * d - inw[0] * 0.8, gm[1] + side[1] / L * d - inw[1] * 0.8
        spec.obj_px("Monument1", *square_px(si, sj))
    # ---- a pen's wall torch (War03d: a Torch on the court's wall) ------------------------------------------------------
    if arch == "pen" and rng.random() < 0.4:
        u_ = rng.uniform(-0.6, 0.6)
        bi, bj = {"i0": (I0 + 0.25, (J0 + J1) / 2 + u_), "i1": (I1 - 0.25, (J0 + J1) / 2 + u_),
                  "j0": ((I0 + I1) / 2 + u_, J0 + 0.25), "j1": ((I0 + I1) / 2 + u_, J1 - 0.25)}[back]
        spec.obj_px("Torch", *square_px(bi, bj))
        reserve(bi, bj, 0.8)
    # ---- the graves ----------------------------------------------------------------------------------------------------
    # rows across the plot on the grid's lines (Westwood: the steps along the screen's diagonals), wide apart (a field's
    # 100-130 px), a family's graves closer, a little out of true; a headstone at the head of each plot
    rows_i = (J1 - J0) >= (I1 - I0)                     # the rows run along the plot's longer side
    big = min(y.w, y.h) >= 12
    small = arch == "pen"
    A0, A1, B0, B1 = (I0, I1, J0, J1) if rows_i else (J0, J1, I0, I1)
    pad_ = 1.4 if big else (0.8 if small else 1.1)
    # (round 7, the judges: "headstones in a near-perfect lattice, four rows of three, filling the yard"; the lab's
    # measures: Westwood's own fields ARE laid on a lattice, snapped to the screen's diagonals, rows 0.83 of their stones,
    # ~98 px apart; what differs is that its rows are of different lengths, start at different plots and leave plots
    # empty, the stones wider apart). One pitch along the rows and one between them for the yard (Westwood's wider),
    # each row starting at the first or second plot and stopping short by up to two, a stone barely out of true
    cands = []
    pitch = rng.uniform(1.9, 2.4) if small else rng.uniform(2.9, 3.3)
    r_ = A0 + pad_ + 0.2 + rng.uniform(0, 0.4)
    c_first = B0 + pad_ + 0.3 + rng.uniform(0, 0.4)
    while r_ <= A1 - pad_ - 0.2:
        n_plots = int((B1 - pad_ - 0.3 - c_first) / pitch) + 1
        k0 = 0 if small else rng.choice((0, 0, 1))
        k1 = n_plots - (0 if small else rng.choice((0, 0, 1, 2)))
        for k_ in range(k0, max(k0, k1)):
            c_ = c_first + k_ * pitch
            hi, hj = (r_, c_) if rows_i else (c_, r_)
            hi += rng.uniform(-0.1, 0.1); hj += rng.uniform(-0.12, 0.12)     # barely out of true
            cands.append((hi, hj))
        r_ += rng.uniform(2.7, 3.4) if big else (rng.uniform(1.9, 2.4) if small else rng.uniform(2.6, 3.2))
    lw = 0.5                                                             # (the walk is the way through)
    cands = [(hi, hj) for hi, hj in cands if free_spot(hi, hj, pad=pad_, lane_w=lw, t="Tombstone1") and
             free_spot(hi + 0.45, hj, pad=pad_ - 0.4, lane_w=lw)]
    if arch == "field":
        cands = [c for c in cands if rng.random() >= 0.15]                 # a plot not yet used
    elif arch == "crypt_yard":
        # a knot of graves near the crypt (or the yard's back), the lawn by the gate left open
        focus = steps[0] if steps else (2 * ci - gm[0], 2 * cj - gm[1])
        cands.sort(key=lambda c: math.hypot(c[0] - focus[0], c[1] - focus[1]) + rng.uniform(0, 1.2))
        cands = cands[:rng.randint(5, 8)]
    else:
        rng.shuffle(cands)
        cands = cands[:rng.randint(4, 6)]
    n_graves = 0
    for hi, hj in cands:
        if not free_spot(hi, hj, pad=pad_, lane_w=lw): continue
        put(_pick(rng, palette), hi, hj, room=1.2)
        n_graves += 1
        if arch == "field" and rng.random() < 0.2:                       # weeds by the stone (War03c: PlantBarren)
            wi, wj = hi + rng.uniform(0.3, 0.8), hj + rng.uniform(-0.5, 0.5)
            if free_spot(wi, wj, pad=0.6, lane_w=0.5): put(rng.choice(("PlantBarren1", "PlantBarren2")), wi, wj, room=0.4)
        if arch != "pen" and rng.random() < 0.12:                        # a newer grave: its plot dug earth
            a_ = int(math.floor(hi - 0.1)), int(math.floor(hj + 0.5))     # (one square: two in a line had read as a
            for sq_ in (a_,):                                             # path under the stones, round 7)
                if sq_ in y.plot: spec.floor[square_tile(*sq_)] = "DirtDark2"
        reserve(hi + 0.45, hj, 0.8)                               # the plot stays clear
    # a yard keeps four graves at the least (a graveyard has graves, SW-9): a small yard's rows had left room for three,
    # so the rest go where they fit, loose, at a pen's spacing
    want = 4 if arch == "pen" else 5
    got = n_graves
    for _try in range(200 if got < want else 0):
        if got >= want: break
        hi, hj = rng.uniform(I0 + pad_, I1 - pad_), rng.uniform(J0 + pad_, J1 - pad_)
        if free_spot(hi, hj, pad=pad_, lane_w=0.5, t="Tombstone1") and free_spot(hi + 0.45, hj, pad=pad_ - 0.4, lane_w=0.5):
            put(_pick(rng, palette), hi, hj, room=1.7)
            reserve(hi + 0.45, hj, 0.8)
            got += 1
