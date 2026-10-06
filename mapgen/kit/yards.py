"""Yards (generator v3): gated outdoor plots with a purpose, as Westwood fences them in its towns
(rules/town_walls.py; measured on Con02a, Con08a, War03b, War03c, War03d, War04a and Wiz08a):

- graveyard: an iron fence and its gate (IronFence, Gate) round 63-110 floor tiles of sparse grass; graves in loose
  staggered rows three squares apart, each a headstone (mixed types, Tombstone1 the most), a third on dug earth; a
  gravedigger's corner (an open grave, the coffin, spade, pick, tool barrel and a torch pole), stone pillars by the
  gate, a dead tree or two (`_graveyard`);
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
- jail: two cells of 6 tiles side by side behind cobblestone walls, each with its own jail door (JailDoor), a cot and
  straw in each (Con02a, Con08a, War03b, War08a, Wiz08a).

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
    "field": dict(fence="Log", gate="Gate", floor="DirtDark2", size=[(8, 6), (9, 6), (7, 7)], purpose="the town's crops"),
    "monument": dict(fence="Cobblestone", gate="WoodAndSteelHalfDoor", floor="RoughCobble", size=[(8, 8), (9, 8)],
                     purpose="a memorial to the town's founders"),
    "jail": dict(fence="Cobblestone", gate="JailDoor", floor="RoughCobble", size=[(6, 3)], cells=2,
                 purpose="the town's cells"),
}
CROPS = ("GardenCorn", "GardenTomatos", "GardenCabbage")
TOMBSTONES = {"Tombstone1": 8, "Tombstone11": 4, "Tombstone17": 4, "Tombstone5": 3, "Tombstone14": 3,
              "Tombstone8": 3, "Tombstone12": 3, "Tombstone18": 2}
BONES = ("LegBone", "ArmBone", "Skull")
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


def plan(land, rng, kind, centre, toward=None, margin=2):
    """Reserve a yard of `kind` near `centre` (square coordinates) before the land is carved. Its plot and a margin
    round it must be clear of roads, the square, water and everything already taken. The gate faces `toward`
    (default: the map's middle). Returns the Yard, or None if nothing fits within a few squares of `centre`."""
    rec = YARDS[kind]
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
    land.taken |= {(gi + a, gj + b) for a in range(-2, w + 2) for b in range(-2, h + 2)}      # trees stay off the fence
    return y


def plan_any(land, rng, kind, centres, toward=None):
    """plan() at the first of `centres` (square coordinates) where the yard fits."""
    for c in centres:
        y = plan(land, rng, kind, c, toward)
        if y: return y
    return None


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
    for pts in sides.values():
        for p in pts:
            spec.wall(*point_cell(*p), rec["fence"])
    pts = sides[y.side]
    n_cells = rec.get("cells", 1)
    if n_cells > 1:
        # cells: dividing walls across the long side, a door into each cell from the gate side
        along_i = y.side in ("j0", "j1")
        L = y.w if along_i else y.h
        for c in range(1, n_cells):
            cut = (y.gi + c * L // n_cells) if along_i else (y.gj - 1 + c * L // n_cells)
            for q in (range(y.gj - 1, y.gj + y.h) if along_i else range(y.gi, y.gi + y.w + 1)):
                spec.wall(*point_cell(*((cut, q) if along_i else (q, cut))), rec["fence"])
        doors = []
        for c in range(n_cells):
            mid = (c * L // n_cells + (c + 1) * L // n_cells) // 2
            a = point_cell(*pts[mid])
            b = point_cell(*pts[mid + 1])
            line = "\\" if (b[0] - a[0], b[1] - a[1]) == (1, 1) else "/"
            doors.append(spec.door(rec["gate"], a, line))
        y.gate = doors[0]
        y.cells = doors                 # every cell's door (a gauntlet opens them one at a time)
        placed = []
        for c in range(n_cells):
            lo, hi = c * L // n_cells, (c + 1) * L // n_cells
            back = {"i0": "i1", "i1": "i0", "j0": "j1", "j1": "j0"}[y.side]
            # the cot against the back wall, straw on the floor
            if along_i:
                bj = y.gj + y.h - 2.3 if back == "j1" else y.gj - 0.7
                spec.obj_px("Cot2", *square_px(y.gi + lo + (hi - lo) / 2, bj))
                for _ in range(rng.randint(1, 2)):
                    spec.obj_px("Straw2", *square_px(y.gi + lo + rng.uniform(0.6, hi - lo - 0.6), y.gj - 1.5 + rng.uniform(1.0, y.h - 1.0)))
            else:
                bi = y.gi + y.w - 0.75 if back == "i1" else y.gi + 0.75
                spec.obj_px("Cot2", *square_px(bi, y.gj - 1.5 + lo + (hi - lo) / 2))
                for _ in range(rng.randint(1, 2)):
                    spec.obj_px("Straw2", *square_px(y.gi + rng.uniform(1.0, y.w - 1.0), y.gj - 1.5 + lo + rng.uniform(0.6, hi - lo - 0.6)))
        return placed
    # the gate: a two-cell opening in the middle of its side (a double gate hangs a half at each end)
    k = len(pts) // 2
    a, b = point_cell(*pts[k - 1]), point_cell(*pts[k])
    line = "\\" if (b[0] - a[0], b[1] - a[1]) == (1, 1) else "/"
    y.gate = spec.door(rec["gate"], a, line)
    gm = ((pts[k - 1][0] + pts[k][0]) / 2, (pts[k - 1][1] + pts[k][1]) / 2 - 0.5)  # the gate's middle, as drawn
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
        rows_i = y.side in ("j0", "j1")
        I0, I1, J0, J1 = y.gi, y.gi + y.w, yj - 1, yj - 1 + y.h
        across = (I0, I1) if not rows_i else (J0, J1)
        along = (J0, J1) if not rows_i else (I0, I1)
        for r in _spread(across[0] + 0.85, across[1] - 0.85, 1.25):
            for a in _spread(along[0] + 0.75, along[1] - 0.75, 0.42):
                si, sj = (r, a) if not rows_i else (a, r)
                if free_spot(si, sj, pad=0.6, lane_w=0.7, t=crop): put(crop, si, sj, room=0.3)
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


def _crypts(spec, rng, y, reserve, cells=1, depth=3, span=3):
    """Crypt cells along the yard's back side, as Westwood sets its graveyards against their crypts (War03b, War03c,
    War03d: a row of cobblestone cells, green brick inside, a sarcophagus (Crypt1/Crypt3) in each, a wooden door into
    the yard; Con07B, Con09b: one stone crypt in the yard). The cells stand at one end of the back side, their back and
    end walls the fence's own line. Returns the squares of the door's step in the yard (continuous), one per cell."""
    back = {"i0": "i1", "i1": "i0", "j0": "j1", "j1": "j0"}[y.side]
    gi, gj, w, h = y.gi, y.gj, y.w, y.h
    U = h if back in ("i0", "i1") else w
    if U < cells * span + 3 or (w if back in ("i0", "i1") else h) < depth + 5: return []
    def pt(u, v):                       # a wall point: u along the back side, v in from it
        if back == "i1": return (gi + w - v, gj - 1 + u)
        if back == "i0": return (gi + v, gj - 1 + u)
        if back == "j1": return (gi + u, gj + h - 1 - v)
        return (gi + u, gj - 1 + v)
    def sq(u, v):                       # the square whose corner nearest the back's low end is (u, v)
        p, q = pt(u + 0.5, v + 0.5)
        return int(math.floor(p)), int(math.floor(q)) + 1
    end = rng.random() < 0.5
    u0s = [0 + k * span for k in range(cells)] if not end else [U - (k + 1) * span for k in range(cells)]
    steps = []
    for u0 in u0s:
        for u in range(u0, u0 + span + 1):
            for v in (0, depth):
                spec.wall(*point_cell(*pt(u, v)), "Cobblestone")
        for v in range(0, depth + 1):
            for u in (u0, u0 + span):
                spec.wall(*point_cell(*pt(u, v)), "Cobblestone")
        for u in range(u0, u0 + span):
            for v in range(depth):
                s_ = sq(u, v)
                spec.floor[square_tile(*s_)] = "GreenBrick"
        # the door in the front wall's middle, into the yard
        um = u0 + span // 2
        a, b = point_cell(*pt(um, depth)), point_cell(*pt(um + 1, depth))
        line = "\\" if (b[0] - a[0], b[1] - a[1]) == (1, 1) else "/"
        spec.door("WoodAndSteelDoor", a, line)
        # the sarcophagus in the middle of the cell, long across the door's line
        cu, cv = u0 + span / 2, depth * 0.45
        ci_, cj_ = pt(cu, cv)
        spec.obj_px(rng.choice(("Crypt1", "Crypt3")), *square_px(ci_, cj_ - 0.5))
        for u in range(u0 - 1, u0 + span + 1):
            for v in range(0, depth + 1):
                p_, q_ = pt(u + 0.5, v + 0.5)
                reserve(p_, q_ - 0.5, 0.75)
        p_, q_ = pt(um + 0.5, depth + 0.7)
        steps.append((p_, q_ - 0.5))
    return steps


def _graveyard(spec, rng, y, yj, free_spot, put, gm, reserve):
    """A graveyard as Westwood lays one, and as a place that is used (Starwell playtest, 2026-10-05: "Graveyards mostly
    look good, but it would look better if there were actually some graves. Maybe a bucket of tools. More diversity of
    objects"). The scene lab (review/scenelab, Westwood's campaign graveyards: War03b, War03c, War03d, Con07B, Con09b)
    measured them: headstones of mixed kinds on sparse grass (GrassSparse2), 80-100 px apart in rows on the grid's
    lines, nine in ten of the pieces headstones, a stone pillar each side of the gate (Monument1), a dead
    tree or two among the graves; never a bench.
    - the ground sparse grass, the graves in loose staggered rows across the plot, each a headstone at the head of its
      plot; the newer graves (a third) on dug earth (DirtDark2), a few with flowers laid on them;
    - the gravedigger's corner, away from the gate: a fresh open grave (dark earth) with the coffin waiting beside it,
      the spade stuck in the earth by it, the bucket of tools, a torch pole to work by;
    - a stone pillar either side of the gate; a dead tree or two."""
    I0, I1, J0, J1 = y.gi, y.gi + y.w, yj - 1, yj - 1 + y.h
    ci, cj = y.centre
    for s in y.plot:                                            # the yard's sparse grass (Westwood: GrassSparse2)
        spec.floor[square_tile(*s)] = "GrassSparse2"
    # the crypts along the back (most yards big enough: Westwood's War03 yards are set against their crypt rows), the
    # walk from the gate to the crypt door beaten bare
    steps = []
    if rng.random() < 0.75:
        steps = _crypts(spec, rng, y, reserve, cells=2 if max(y.w, y.h) >= 13 and rng.random() < 0.6 else 1)
    # the walk: from the gate straight in to the crypt's door, or across the yard to its back (War03b, War03c, War03d:
    # a paved walk through the graves), beaten bare, the graves either side of it
    if steps: end_ = steps[0]
    else: end_ = (2 * ci - gm[0], 2 * cj - gm[1])
    ex_, ey_ = end_[0] - gm[0], end_[1] - gm[1]
    if abs(ex_) > abs(ey_): end_ = (end_[0], gm[1])             # along the grid: the walk runs square to the gate
    else: end_ = (gm[0], end_[1])
    tx_, ty_ = end_
    n_ = int(math.hypot(tx_ - gm[0], ty_ - gm[1]) / 0.4) + 1
    for k_ in range(n_ + 1):
        si_, sj_ = gm[0] + (tx_ - gm[0]) * k_ / n_, gm[1] + (ty_ - gm[1]) * k_ / n_
        for o_ in (-0.5, 0.5):
            sqr = (int(math.floor(si_ + (o_ if abs(ey_) >= abs(ex_) else 0))),
                   int(math.floor(sj_ + 0.5 + (o_ if abs(ex_) > abs(ey_) else 0))) + 1)
            if sqr in y.plot: spec.floor[square_tile(*sqr)] = "DirtLight2"
        reserve(si_, sj_, 1.2 if min(y.w, y.h) >= 12 else 0.75)     # a small yard's walk one tile wide
    # the gravedigger's corner: the back corner on the side away from the gate's lane
    corners = [(I0 + 1.4, J0 + 1.4), (I1 - 1.4, J0 + 1.4), (I0 + 1.4, J1 - 1.4), (I1 - 1.4, J1 - 1.4)]
    far = max(corners, key=lambda c: math.hypot(c[0] - gm[0], c[1] - gm[1]))
    dug = None
    gi_, gj_ = int(math.floor(far[0])), int(math.floor(far[1])) + 1             # its square
    oi, oj = gi_ + 0.5, gj_ - 0.5                                               # the open grave's middle
    if rng.random() < 0.65 and free_spot(oi, oj, pad=0.8, lane_w=1.2):         # most are digging a grave
        spec.floor[square_tile(gi_, gj_)] = "DirtDark2"
        dug = (oi, oj)
        dx = 1 if oi < ci else -1
        dy = 1 if oj < cj else -1
        # the spade and the bucket of tools (SW-9); the coffin waiting and a torch pole to work by now and then (no
        # Westwood graveyard has either: the blind judge read a lone coffin on the fence corner as a stray prop)
        for t, (a, b), room, p_ in (("MiningShovelInGround", (0.7 * dx, -0.2 * dy), 0.4, 1.0),
                                    ("BarrelWithTools1", (1.25 * dx, -0.45 * dy), 0.7, 1.0),
                                    ("Coffin1", (0.0, 1.05 * dy), 0.9, 0.25), ("TorchPole", (-0.9 * dx, -0.9 * dy), 0.7, 0.3)):
            if rng.random() >= p_: continue
            si, sj = oi + a, oj + b
            if free_spot(si, sj, pad=0.6, lane_w=1.1, t=t):
                put(t, si, sj, room=room)
        reserve(oi, oj, 1.3)                                              # the open grave keeps its square
    # a stone pillar either side of the gate, just inside it
    side = (-(cj - gm[1]), ci - gm[0])
    L = math.hypot(*side) or 1
    inw = ((ci - gm[0]) / (math.hypot(ci - gm[0], cj - gm[1]) or 1), (cj - gm[1]) / (math.hypot(ci - gm[0], cj - gm[1]) or 1))
    for d in ((1.5, -1.5) if rng.random() < 0.2 else (rng.choice((1.5, -1.5)),) if rng.random() < 0.3 else ()):
        si, sj = gm[0] + side[0] / L * d + inw[0] * 0.7, gm[1] + side[1] / L * d + inw[1] * 0.7
        if free_spot(si, sj, pad=0.5, lane_w=0.9, t="Monument1"): put("Monument1", si, sj, room=0.8)
    # the graves: rows across the plot on the grid's lines, 2.7-2.8 squares (90 px) apart (Westwood: nearest 88-97 px,
    # the steps along the screen's diagonals), a little out of true; a headstone at the head of each plot (a tile (a, b)
    # is drawn over squares a..a+1 across i, its stone at its upper-left edge, (a + 0.1, b - 0.5))
    rows_i = (J1 - J0) >= (I1 - I0)                     # the rows run along the plot's longer side
    big = min(y.w, y.h) >= 12                            # a small yard packs its rows closer (still ~85 px)
    A0, A1, B0, B1 = (I0, I1, J0, J1) if rows_i else (J0, J1, I0, I1)
    k = 0
    r_ = A0 + 1.1
    while r_ <= A1 - 1.1:
        c_ = B0 + 1.2
        while c_ <= B1 - 0.9:
            hi, hj = (r_, c_) if rows_i else (c_, r_)
            hi += rng.uniform(-0.1, 0.1); hj += rng.uniform(-0.15, 0.15)     # a little out of true, as dug by hand
            c_ += rng.uniform(2.9, 3.4) if big else rng.uniform(2.6, 2.9)    # Westwood: nearest 100-130 px
            if rng.random() < 0.12: continue                                 # a plot not yet used
            lw = 0.5                                                         # (the walk is the way through)
            if not (free_spot(hi, hj, pad=1.1 if big else 0.85, lane_w=lw, t="Tombstone1") and
                    free_spot(hi + 0.45, hj, pad=0.9 if big else 0.7, lane_w=lw)):
                continue
            put(_pick(rng, TOMBSTONES), hi, hj, room=1.2)
            if rng.random() < 0.35:                                   # a newer grave: its plot dug earth
                spec.floor[square_tile(int(math.floor(hi - 0.1)), int(math.floor(hj + 0.5)))] = "DirtDark2"
                if rng.random() < 0.5:
                    put(rng.choice(("FlowersWhiteSparse", "FlowersYellowSparse", "FlowersPurpleSparse")), hi + 0.65, hj,
                        room=0.6)
            reserve(hi + 0.45, hj, 0.8)                               # the plot stays clear
        r_ += rng.uniform(2.7, 3.1) if big else rng.uniform(2.4, 2.7)
        k += 1
    # a tree or two by the fence, inside it: a dead one, or one grown old there (Westwood: TreeOgre08-10 and trunks in
    # War03b-d, Galava's trees along its yard's fence), never in the middle among the graves
    for _ in range(rng.randint(1, 2)):
        for _try in range(30):
            s_ = (rng.uniform(I0 + 0.9, I1 - 0.9), rng.uniform(J0 + 0.9, J1 - 0.9))
            if min(s_[0] - I0, I1 - s_[0], s_[1] - J0, J1 - s_[1]) > 1.6: continue
            # a trunk's spread is wide: 1.2 squares off the fence's line, never on it (the blind judge, 2026-10-05)
            if free_spot(*s_, pad=1.2, lane_w=1.3, t="TreeOgre08"):
                put(rng.choice(("TreeOgre08", "TreeOgre09", "TreeOgre10", "TreeTrunk6", "TreeForest01", "TreeForest03")),
                    *s_, room=1.0); break
