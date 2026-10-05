"""Yards (generator v3): gated outdoor plots with a purpose, as Westwood fences them in its towns
(rules/town_walls.py; measured on Con02a, Con08a, War03b, War03c, War03d, War04a and Wiz08a):

- graveyard: an iron fence and its gate (IronFence, Gate) round 63-110 floor tiles of dirt; tombstones about three
  squares apart in loose rows, of mixed types (Tombstone1 the most), torch poles, a few bones;
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

YARDS = {
    "graveyard": dict(fence="IronFence", gate="Gate", floor="DirtDark2", size=[(8, 7), (9, 8), (9, 7)],
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
        return self.gi + self.w / 2, self.gj - 1 + self.h / 2          # continuous square coordinates


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
    for di in range(-4, 5):
        for dj in range(-4, 5):
            gi, gj = int(round(ci - w / 2)) + di, int(round(cj - h / 2 + 1)) + dj
            ring = {(gi + a, gj + b) for a in range(-margin, w + margin) for b in range(-margin, h + margin)}
            if ring & busy: continue                  # (the margin also keeps 2 squares free beyond the fence)
            # on the grid with room for the forest round it (Land.carve keeps squares within 3..250)
            if not all(8 <= i + j <= 245 and 8 <= i - j <= 245 for i, j in ring): continue
            d = abs(di) + abs(dj)
            if best is None or d < best[0]: best = (d, gi, gj)
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
                bj = y.gj + y.h - 1.75 if back == "j1" else y.gj - 0.25
                spec.obj_px("Cot2", *square_px(y.gi + lo + (hi - lo) / 2, bj))
                for _ in range(rng.randint(1, 2)):
                    spec.obj_px("Straw2", *square_px(y.gi + lo + rng.uniform(0.6, hi - lo - 0.6), y.gj - 1 + rng.uniform(1.0, y.h - 1.0)))
            else:
                bi = y.gi + y.w - 0.75 if back == "i1" else y.gi + 0.75
                spec.obj_px("Cot2", *square_px(bi, y.gj - 1 + lo + (hi - lo) / 2))
                for _ in range(rng.randint(1, 2)):
                    spec.obj_px("Straw2", *square_px(y.gi + rng.uniform(1.0, y.w - 1.0), y.gj - 1 + lo + rng.uniform(0.6, hi - lo - 0.6)))
        return placed
    # the gate: a two-cell opening in the middle of its side (a double gate hangs a half at each end)
    k = len(pts) // 2
    a, b = point_cell(*pts[k - 1]), point_cell(*pts[k])
    line = "\\" if (b[0] - a[0], b[1] - a[1]) == (1, 1) else "/"
    y.gate = spec.door(rec["gate"], a, line)
    gm = ((pts[k - 1][0] + pts[k][0]) / 2, (pts[k - 1][1] + pts[k][1]) / 2)     # the gate's middle, in squares
    ci, cj = y.centre
    lane = (gm, (ci, cj))
    placed = []

    def free_spot(si, sj, pad=0.9, lane_w=1.3):
        if not (y.gi + pad <= si <= y.gi + y.w - pad and y.gj - 1 + pad <= sj <= y.gj + y.h - 1 - pad): return False
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
        # loose rows of tombstones about three squares apart (Westwood's spacing: 4.2 cells)
        for si in _spread(y.gi + 1.3, y.gi + y.w - 1.3, 2.3):
            for sj in _spread(y.gj - 1 + 1.3, y.gj + y.h - 2.3, 2.2):
                s = (si + jit() * 0.8, sj + jit() * 0.8)
                if free_spot(*s, pad=1.0, lane_w=1.4): put(_pick(rng, TOMBSTONES), *s, room=1.6)
        for c in ((y.gi + 0.9, y.gj - 0.1), (y.gi + y.w - 0.9, y.gj + y.h - 1.9)):      # torch poles in two corners
            if free_spot(*c, pad=0.8, lane_w=1.2): put("TorchPole", *c, room=1.0)
        for _ in range(rng.randint(1, 3)):
            s = (rng.uniform(y.gi + 1, y.gi + y.w - 1), rng.uniform(y.gj, y.gj + y.h - 2))
            if free_spot(*s, pad=0.8, lane_w=1.2): put(rng.choice(BONES), *s, room=0.5)
    elif y.kind == "orchard":
        tree = (y.gi + y.w - 1.4, y.gj + y.h - 2.4) if y.side in ("i0", "j0") else (y.gi + 1.4, y.gj + 0.4)
        put("TreeForest11", *tree, room=1.6)
        for si in [y.gi + 1.0 + 1.4 * k for k in range(int((y.w - 1.6) / 1.4) + 1)]:
            for sj in [y.gj - 1 + 1.0 + 1.4 * k for k in range(int((y.h - 1.6) / 1.4) + 1)]:
                s = (si + jit() * 0.5, sj + jit() * 0.5)
                if free_spot(*s, pad=0.8, lane_w=0.9): put(rng.choice(("Plant5", "Plant5", "Plant4")), *s, room=1.1)
        for t in ("FlowersYellowSparse", "FlowersYellowSparse", "RedApple"):
            for _ in range(20):
                s = (rng.uniform(y.gi + 0.7, y.gi + y.w - 0.7), rng.uniform(y.gj - 0.3, y.gj + y.h - 1.7))
                if free_spot(*s, pad=0.6, lane_w=0.8): put(t, *s, room=0.5); break
    elif y.kind == "park":
        # eight benches facing a tree in the middle, two to a side; bushes in the corners, flowers along the walls
        put("TreeForest15", ci, cj, room=1.8)
        for side, (di, dj) in (("i0", (-1, 0)), ("i1", (1, 0)), ("j0", (0, -1)), ("j1", (0, 1))):
            for off in (-1.0, 1.0):
                s = (ci + 2.6 * di + off * abs(dj), cj + 2.6 * dj + off * abs(di))
                if free_spot(*s, pad=0.8, lane_w=0.9): put(BENCH_ON[side], *s, room=0.9)
        for c in ((y.gi + 1.0, y.gj), (y.gi + y.w - 1.0, y.gj), (y.gi + 1.0, y.gj + y.h - 2), (y.gi + y.w - 1.0, y.gj + y.h - 2)):
            if free_spot(*c, pad=0.7, lane_w=1.1): put(rng.choice(("Bush6", "Plant5", "Plant4")), *c, room=1.0)
        for _ in range(10):
            s = (rng.uniform(y.gi + 0.8, y.gi + y.w - 0.8), rng.choice((y.gj - 0.2, y.gj + y.h - 1.8)))
            if free_spot(*s, pad=0.6, lane_w=1.1): put(rng.choice(("FlowersBlueSparse", "FlowersPurpleSparse", "FlowersWhiteSparse")), *s, room=0.7)
    elif y.kind == "field":
        # one crop in rows across the plot, a row of bare earth between rows (the lane from the gate stays open)
        crop = rng.choice(CROPS)
        rows_i = y.side in ("j0", "j1")             # rows run away from the gate, so the lane runs between them
        for a in range(y.w):
            for b in range(y.h):
                if (a if rows_i else b) % 2: continue
                for t in (0.3, 0.7):
                    s = (y.gi + a + (t if not rows_i else 0.5), y.gj - 1 + b + (0.5 if not rows_i else t))
                    if free_spot(*s, pad=0.5, lane_w=0.8): put(crop, *s, room=0.3)
    elif y.kind == "monument":
        put("Monument1", ci, cj, room=2.2)
        for c in ((y.gi + 1.3, y.gj + 0.3), (y.gi + y.w - 1.3, y.gj + 0.3), (y.gi + 1.3, y.gj + y.h - 2.3),
                  (y.gi + y.w - 1.3, y.gj + y.h - 2.3)):
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
        by_ = {"j0": y.gj - 1 + 1.2, "j1": y.gj + y.h - 2.2}.get(back)
        along = [y.gj - 1 + 1.3 + 1.6 * k for k in range(int((y.h - 2) / 1.6) + 1)] if bx is not None else \
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
                    s = (rng.uniform(y.gi + 0.8, y.gi + y.w - 0.8), rng.uniform(y.gj - 0.2, y.gj + y.h - 1.8))
                    if free_spot(*s, pad=0.7, lane_w=1.2): put(t, *s, room=0.6 if "Pebbles" in t else 0.9); break
    return placed
