"""Yards (generator v3): gated outdoor plots with a purpose, as Westwood fences them in its towns
(rules/town_walls.py; measured on Con02a, Con08a, War03b, War03c, War03d, War04a and Wiz08a):

- graveyard: an iron fence and its gate (IronFence, Gate) round 63-110 floor tiles; graves in rows, each a headstone
  (mixed types, Tombstone1 the most) at the head of its tile of dug earth; a gravedigger's corner (an open grave, the
  coffin, spade, pick and tool barrel), a cross between urns, a mourners' bench, torch poles (`_graveyard`);
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
    "graveyard": dict(fence="IronFence", gate="Gate", floor=None, size=[(8, 7), (9, 8), (9, 7)],
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


def _graveyard(spec, rng, y, yj, free_spot, put, gm, reserve):
    """A graveyard as Westwood lays one, and as a place that is used (Starwell playtest, 2026-10-05: "Graveyards mostly
    look good, but it would look better if there were actually some graves. Maybe a bucket of tools. More diversity of
    objects"). Westwood has no grave-mound object: its graves are headstones on patches of bare earth among the grass
    (War03d: 19 of its 100 headstones on GrassSparse2, 9 on DirtLight2, the earth round them dirt), torch poles at the
    ends of the rows (21 within 70 px of a headstone), flowers, bones, a spade left in the ground (War03d), statues.
    - graves in rows, each a headstone at the head of its plot of earth (a floor tile: old graves DirtLight2, newer
      DirtDark2), flowers laid on some, headstones about 2.2 squares apart (Westwood p25 83 px), a path between rows;
    - the gravedigger's corner, away from the gate: a fresh open grave (dark earth) with the coffin waiting beside it,
      the spade stuck in the spoil heaped by it, the pick, the bucket of tools;
    - a little shrine at the back: a cross between two urns on pedestals;
    - a bench by the gate for mourners, torch poles at two corners for light, a bone or two."""
    I0, I1, J0, J1 = y.gi, y.gi + y.w, yj - 1, yj - 1 + y.h
    ci, cj = y.centre
    back = {"i0": "i1", "i1": "i0", "j0": "j1", "j1": "j0"}[y.side]
    # the gravedigger's corner: the back corner on the side away from the gate's lane
    corners = [(I0 + 1.4, J0 + 1.4), (I1 - 1.4, J0 + 1.4), (I0 + 1.4, J1 - 1.4), (I1 - 1.4, J1 - 1.4)]
    far = max(corners, key=lambda c: math.hypot(c[0] - gm[0], c[1] - gm[1]))
    dug = None
    gi_, gj_ = int(math.floor(far[0])), int(math.floor(far[1])) + 1             # its square
    oi, oj = gi_ + 0.5, gj_ - 0.5                                               # the open grave's middle
    if free_spot(oi, oj, pad=0.8, lane_w=1.2):
        spec.floor[square_tile(gi_, gj_)] = "DirtDark2"
        dug = (oi, oj)
        dx = 1 if oi < ci else -1
        dy = 1 if oj < cj else -1
        for t, (a, b), room in (("Coffin1", (0.0, 1.05 * dy), 0.9), ("MiningShovelInGround", (0.7 * dx, -0.2 * dy), 0.4),
                                ("CaveRocksMedium", (0.75 * dx, 0.3 * dy), 0.4), ("CaveRocksSmall", (0.55 * dx, 0.6 * dy), 0.3),
                                ("MiningPickAxeOnGround2", (1.3 * dx, 0.6 * dy), 0.5),
                                ("BarrelWithTools1", (1.25 * dx, -0.45 * dy), 0.7)):
            si, sj = oi + a, oj + b
            if free_spot(si, sj, pad=0.6, lane_w=1.1, t=t):
                put(t, si, sj, room=room)
        reserve(oi, oj, 1.3)                                              # the open grave keeps its square
    # torch poles in the corners for light (not the gravedigger's), first, so the graves keep off them
    lit = 0
    for c in ((I0 + 0.8, J0 + 0.8), (I1 - 0.8, J1 - 0.8), (I1 - 0.8, J0 + 0.8), (I0 + 0.8, J1 - 0.8)):
        if lit >= 2 or (dug and math.hypot(c[0] - dug[0], c[1] - dug[1]) < 2.0): continue
        if free_spot(*c, pad=0.7, lane_w=1.2, t="TorchPole"): put("TorchPole", *c, room=0.9); lit += 1
    # the shrine by the back fence: a cross between two urns, slid along the fence clear of the gravedigger
    ui, uj = (0.0, 1.0) if back in ("i0", "i1") else (1.0, 0.0)
    bi0 = {"i0": I0 + 1.1, "i1": I1 - 1.1}.get(back, ci)
    bj0 = {"j0": J0 + 1.1, "j1": J1 - 1.1}.get(back, cj)
    for d0 in (0.0, 1.2, -1.2, 2.2, -2.2):
        bi, bj = bi0 + ui * d0, bj0 + uj * d0
        if dug and math.hypot(bi - dug[0], bj - dug[1]) < 2.2: continue
        if not all(free_spot(bi + ui * d, bj + uj * d, pad=0.75, lane_w=1.0, t="StatueVase1S") for d in (-0.9, 0, 0.9)):
            continue
        put(rng.choice(("Cross1", "Cross2", "Statue2a")), bi, bj, room=1.0)
        for d in (-0.9, 0.9):
            put(rng.choice(("StatueVase1S", "StatueVase2S")), bi + ui * d, bj + uj * d, room=0.7)
        break
    # a bench by the gate for mourners, facing in
    gi2, gj2 = gm[0] + (ci - gm[0]) * 0.35, gm[1] + (cj - gm[1]) * 0.35
    side = (-(cj - gm[1]), ci - gm[0])
    L = math.hypot(*side) or 1
    for d in (1.4, -1.4, 2.0, -2.0):
        si, sj = gi2 + side[0] / L * d, gj2 + side[1] / L * d
        if free_spot(si, sj, pad=0.8, lane_w=1.0, t="Bench1"):
            put(BENCH_ON[y.side], si, sj, room=1.0); break
    # the graves: rows across the plot, 2 squares (65 px) apart each way (Westwood: p10 63, p25 83 px between headstones);
    # each grave is a floor tile of earth, its headstone at the tile's head (its upper left edge): a tile (a, b) is
    # drawn over squares a..a+1 across i, its stone at (a + 0.1, b - 0.5)
    for a in range(int(math.ceil(I0 + 1.0)), int(math.floor(I1 - 1.6)) + 1, 2):
        for b in range(int(math.ceil(J0 + 1.5)), int(math.floor(J1 - 0.5)) + 1, 2):
            hi, hj = a + 0.1, b - 0.5 + rng.uniform(-0.08, 0.08)
            pi_, pj_ = a + 0.55, b - 0.5                                # the plot's middle
            if not (free_spot(hi, hj, pad=0.8, lane_w=1.1, t="Tombstone1") and free_spot(pi_, pj_, pad=0.7, lane_w=1.1)
                    and free_spot(a + 0.9, pj_, pad=0.6, lane_w=1.0)):
                continue
            put(_pick(rng, TOMBSTONES), hi, hj, room=1.2)
            spec.floor[square_tile(a, b)] = rng.choice(("DirtDark2", "DirtDark2", "DirtLight2"))
            if rng.random() < 0.4:
                put(rng.choice(("FlowersWhiteSparse", "FlowersYellowSparse", "FlowersPurpleSparse")), a + 0.75, pj_, room=0.8)
            reserve(pi_, pj_, 0.8)                                     # the plot stays clear
    # a bone or two
    for _ in range(rng.randint(1, 2)):
        s_ = (rng.uniform(I0 + 1, I1 - 1), rng.uniform(J0 + 1, J1 - 1))
        if free_spot(*s_, pad=0.8, lane_w=1.2): put(rng.choice(BONES), *s_, room=0.5)
