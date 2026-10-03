"""Original building generator: new footprints, room division, doors and materials every time,
sampled from what Westwood's buildings look like (rules/out/buildings.json), never copied.

Geometry: a building is a grid of lattice *units* on the u/v wall lattice (one unit = 2 in u and v,
one wall segment). Unit (i, j) spans u in [U0+2i, U0+2i+2], v in [V0+2j, V0+2j+2] and owns exactly one
floor tile, at (u, v) = (U0+2i, V0+2j+2) (the stock room rule: tiles u0..u1-2, v0+2..v1). Each unit is
labelled with a room id, COURT (open courtyard) or nothing; walls stand on every lattice point that
lies on an edge between differently labelled units. Doors are one-point gaps in the middle of a
straight wall run, placed with spec.door (Westwood's verified placement rule).

    from kit.building import math, generate_building
    b = generate_building(spec, rng, (u0, v0), (max_u_span, max_v_span), "log_cabin",
                          program=["main", "bedroom"], occupied=used_cells, entrance_side="v_min")
    used_cells |= b.cells        # every cell the building covers, plus a 1-cell margin

Sides (screen view): u_min = upper-left, u_max = lower-right, v_min = lower-left, v_max = upper-right.
"""
import json, math, os
from collections import Counter, defaultdict, deque

from .model import Building, Door, Room

RULES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "rules", "out")
COURT = "court"
SIDES = ("u_min", "u_max", "v_min", "v_max")
SUPPORTED_SHAPES = ("rect", "L", "T", "U", "Z", "courtyard")
# floors that make no sense as a building's own room floor (stock rooms near water, mines, swamps)
NOT_ROOM_FLOOR = ("Water", "Grass", "Lava", "Swamp", "Mine", "Black", "Weeds", "Ice",
                  "Rug")   # rugs: Westwood lays them as patches inside rooms (a furnisher's job)
# door objects that are fence gates or cage doors rather than house doors
NOT_HOUSE_DOOR = ("Gate", "Barred", "Cage", "Jail", "Spiked", "Dilapidated")

_STYLES = None
_THINGS = None


def styles():
    global _STYLES
    if _STYLES is None:
        with open(os.path.join(RULES, "buildings.json"), encoding="utf-8") as f:
            _STYLES = json.load(f)["styles"]
    return _STYLES


def _pick(rng, dist, exclude=(), default=None):
    items = [(k, v) for k, v in (dist or {}).items() if v > 0 and not any(e in k for e in exclude)]
    if not items: return default
    keys, w = zip(*items)
    return rng.choices(keys, w)[0]


def _sample_quartiles(rng, qs, lo=None, hi=None):
    """Sample around a [q25, median, q75] triple (triangular between the outer quartiles, with tails)."""
    a, m, b = qs
    span = max(b - a, 1)
    v = rng.triangular(a - 0.25 * span, b + 0.25 * span, m)
    if lo is not None: v = max(lo, v)
    if hi is not None: v = min(hi, v)
    return int(round(v))


# ---------------------------------------------------------------------------------- footprint
def _footprint(rng, shape, W, H):
    """Units of a footprint W x H as {(i, j): part index}; COURT marks an open courtyard."""
    U = {}

    def fill(i0, i1, j0, j1, label):
        for i in range(i0, i1):
            for j in range(j0, j1): U[(i, j)] = label

    r = lambda lo, hi: rng.randint(lo, max(lo, hi))
    if shape == "rect":
        fill(0, W, 0, H, 0)
    elif shape == "L":
        h1 = r(max(3, int(H * 0.4)), H - 3); w2 = r(max(3, int(W * 0.35)), W - 3)
        fill(0, W, 0, h1, 0); fill(0, w2, h1, H, 1)
    elif shape == "T":
        h1 = r(max(3, int(H * 0.4)), H - 3); w2 = r(3, max(3, int(W * 0.5)))
        a = r(1, W - w2 - 1)
        fill(0, W, 0, h1, 0); fill(a, a + w2, h1, H, 1)
    elif shape == "U":
        h1 = r(3, max(3, H - 4)); wa = r(3, max(3, (W - 3) // 2))
        fill(0, W, 0, h1, 0); fill(0, wa, h1, H, 1); fill(W - wa, W, h1, H, 2)
    elif shape == "Z":
        h1 = r(3, H - 3); a = r(max(3, int(W * 0.45)), W - 3); b = r(1, a - 3)
        fill(0, a, 0, h1, 0); fill(b, W, h1, H, 1)
    elif shape == "courtyard":
        t = r(3, max(3, min(W, H) // 3))
        fill(0, W, 0, H, 0)
        fill(t, W - t, t, H - t, COURT)
        # split the ring into wings so each becomes its own room run
        for (i, j), v in list(U.items()):
            if v == COURT: continue
            U[(i, j)] = 0 if j < t else 1 if j >= H - t else 2 if i < t else 3
    return U


def _transform(rng, U, W, H):
    """Random mirror/transposition so shapes face any direction."""
    flip_i, flip_j, swap = rng.random() < 0.5, rng.random() < 0.5, rng.random() < 0.5
    out = {}
    for (i, j), v in U.items():
        if flip_i: i = W - 1 - i
        if flip_j: j = H - 1 - j
        if swap: i, j = j, i
        out[(i, j)] = v
    return out, (H, W) if swap else (W, H)


# ---------------------------------------------------------------------------------- rooms
def _rects_of_part(units):
    """Bounding rectangle (i0, i1, j0, j1) of a set of units (parts are rectangles by construction)."""
    i0 = min(i for i, _ in units); i1 = max(i for i, _ in units) + 1
    j0 = min(j for _, j in units); j1 = max(j for _, j in units) + 1
    return i0, i1, j0, j1


def _split(rng, rect, target, min_side, rooms_out, weights=None):
    """Guillotine-split a rectangle into `target` rooms, each at least min_side units across. With
    `weights` (one per room) the cuts follow them, so a tavern can take most of an inn's floor."""
    i0, i1, j0, j1 = rect
    w, h = i1 - i0, j1 - j0
    weights = weights or [1.0] * target
    if target <= 1 or (w < 2 * min_side and h < 2 * min_side):
        rooms_out.append(rect); return
    along_i = (w >= h) if (w >= 2 * min_side and h >= 2 * min_side) else (w >= 2 * min_side)
    n = w if along_i else h
    if len(set(weights)) > 1:
        weights = sorted(weights, reverse=True)
        k_left = 1                                        # the largest room alone on one side
    else:
        k_left = max(1, round(target * rng.uniform(0.35, 0.65)))
    k_left = min(k_left, target - 1)
    frac = sum(weights[:k_left]) / sum(weights)
    cut = round(n * frac + rng.uniform(-1, 1))
    cut = max(min_side, min(n - min_side, cut))
    wl, wr = weights[:k_left], weights[k_left:]
    if along_i:
        _split(rng, (i0, i0 + cut, j0, j1), k_left, min_side, rooms_out, wl)
        _split(rng, (i0 + cut, i1, j0, j1), target - k_left, min_side, rooms_out, wr)
    else:
        _split(rng, (i0, i1, j0, j0 + cut), k_left, min_side, rooms_out, wl)
        _split(rng, (i0, i1, j0 + cut, j1), target - k_left, min_side, rooms_out, wr)


def _assign_rooms(rng, U, target, weights=None):
    """Label units with room ids: each footprint part gets rooms in proportion to its area."""
    parts = defaultdict(set)
    for p, v in U.items():
        if v != COURT: parts[v].add(p)
    total = sum(len(s) for s in parts.values())
    labels = dict((p, COURT) for p, v in U.items() if v == COURT)
    rid = 0
    # few rooms in a multi-part footprint: merge parts into one L/T-shaped room (as Westwood does)
    if target < len(parts):
        for s in parts.values():
            for p in s: labels[p] = 0
        return labels
    # rooms per part in proportion to area, summing exactly to target (largest remainder), >= 1 each
    keys = sorted(parts, key=str)
    raw = {k: target * len(parts[k]) / total for k in keys}
    alloc = {k: max(1, int(raw[k])) for k in keys}
    for k in sorted(keys, key=lambda k: -(raw[k] - int(raw[k]))):
        if sum(alloc.values()) >= target: break
        alloc[k] += 1
    while sum(alloc.values()) > target:
        k = max(keys, key=lambda k: alloc[k]); alloc[k] -= 1
    for k, s in sorted(parts.items(), key=lambda kv: str(kv[0])):
        rects = []
        r = _rects_of_part(s)
        min_side = 4 if min(r[1] - r[0], r[3] - r[2]) >= 8 else 3
        _split(rng, r, alloc[k], min_side, rects, weights if len(parts) == 1 and weights and len(weights) == alloc[k] else None)
        for (i0, i1, j0, j1) in rects:
            for i in range(i0, i1):
                for j in range(j0, j1):
                    if (i, j) in s: labels[(i, j)] = rid
            rid += 1
    return labels


# ---------------------------------------------------------------------------------- walls/doors
def _boundary(labels):
    """Edges between differently labelled units. Returns {edge: (labelA, labelB)} where an edge is
    ('u', i_line, j) (constant u line at unit column boundary i_line, spanning row j) or
    ('v', i, j_line). Outside is None."""
    edges = {}
    cells = set(labels)
    for (i, j), a in labels.items():
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (i + di, j + dj)
            b = labels.get(n)
            if b == a: continue
            e = ("u", i + max(di, 0), j) if di else ("v", i, j + max(dj, 0))
            edges[e] = (a, b) if e not in edges else edges[e]
    return edges


def _edge_points(e):
    kind, a, b = e
    return [(2 * a, 2 * b), (2 * a, 2 * b + 2)] if kind == "u" else [(2 * a, 2 * b), (2 * a + 2, 2 * b)]


def _runs(edges, pair_filter):
    """Straight runs of consecutive edges whose label pair passes pair_filter.
    Returns [(kind, line, [positions along the line in order], pair)]."""
    by_line = defaultdict(list)
    for e, pair in edges.items():
        if pair_filter(pair):
            kind, a, b = e
            line, pos = (a, b) if kind == "u" else (b, a)
            by_line[(kind, line, frozenset(x for x in pair if x is not None) or None, pair)].append(pos)
    runs = []
    for (kind, line, _, pair), ps in by_line.items():
        ps.sort()
        cur = [ps[0]]
        for p in ps[1:]:
            if p == cur[-1] + 1: cur.append(p)
            else: runs.append((kind, line, cur, pair)); cur = [p]
        runs.append((kind, line, cur, pair))
    return runs


def _point_degree(edges):
    deg = Counter()
    for e in edges:
        for p in _edge_points(e): deg[p] += 1
    return deg


def _door_point(rng, run, deg):
    """A lattice point inside a straight run (not an end, not a junction), preferring the middle."""
    kind, line, ps, _ = run
    if len(ps) < 2: return None
    cands = []
    for k in range(1, len(ps)):              # interior points between edge k-1 and edge k
        pos = ps[k]
        pt = (2 * line, 2 * pos) if kind == "u" else (2 * pos, 2 * line)
        if deg[pt] == 2: cands.append((abs(k - len(ps) / 2), pt))
    if not cands: return None
    cands.sort()
    best = [c for c in cands if c[0] <= cands[0][0] + 1.0]
    return rng.choice(best)[1]


def _on_outer_side(run, W, H, side):
    """True when the run lies on the footprint's outermost edge on that side."""
    kind, line = run[0], run[1]
    return {"u_min": kind == "u" and line == 0, "u_max": kind == "u" and line == W,
            "v_min": kind == "v" and line == 0, "v_max": kind == "v" and line == H}[side]


def _main_room_on_side(labels, side):
    """Mirrors the footprint when needed so the main (largest) room touches `side`; the main room
    takes the entrance, so a building facing the square gets its door on the square side.
    Returns the labels, or None when neither orientation works."""
    sizes = defaultdict(int)
    for v in labels.values():
        if v != COURT: sizes[v] += 1
    main = max(sizes, key=lambda k: sizes[k])
    i0 = min(i for i, _ in labels); i1 = max(i for i, _ in labels)
    j0 = min(j for _, j in labels); j1 = max(j for _, j in labels)
    edge = {"u_min": lambda i, j: i == i0, "u_max": lambda i, j: i == i1,
            "v_min": lambda i, j: j == j0, "v_max": lambda i, j: j == j1}[side]
    touches = lambda lb: any(edge(i, j) for (i, j), v in lb.items() if v == main)
    if touches(labels): return labels
    if side in ("u_min", "u_max"):
        flipped = {(i0 + i1 - i, j): v for (i, j), v in labels.items()}
    else:
        flipped = {(i, j0 + j1 - j): v for (i, j), v in labels.items()}
    return flipped if touches(flipped) else None


def _side_of_run(run, W, H):
    kind, line, ps, pair = run
    if kind == "u": return "u_min" if line <= W / 2 else "u_max"
    return "v_min" if line <= H / 2 else "v_max"


# ---------------------------------------------------------------------------------- main entry
_ROOM_TYPES = None


def _kind_tiles(kind, q="p25"):
    """Typical floor area (tiles ~ footprint units) of a room kind in Westwood's maps."""
    global _ROOM_TYPES
    if _ROOM_TYPES is None:
        import json, os
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                               "rules", "out", "room_types.json"), encoding="utf-8") as f:
            _ROOM_TYPES = json.load(f)["types"]
    return ((_ROOM_TYPES.get(kind) or {}).get("tiles") or {}).get(q) or 30


def generate_building(spec, rng, origin_uv, max_size_uv, style, program=None, occupied=None,
                      entrance_side=None, shape=None, rooms=None, building_id=None, tries=40, min_units=0):
    """Generate an original building into `spec`. Returns a kit.model.Building (with extra attribute
    `cells`: all grid cells it covers plus a 1-cell margin) or None if nothing fits.

    origin_uv: (u0, v0) even ints, the footprint's minimum u and v corner.
    max_size_uv: (max u span, max v span) in u/v units (2 per wall segment).
    style: key of rules/out/buildings.json styles (e.g. log_cabin, stucco_house, galava_townhouse).
    program: room kinds, largest room first (e.g. ["tavern", "kitchen", "bedroom"]); fixes the room count.
    entrance_side: side for the main entrance (u_min, u_max, v_min, v_max) or None (style's habit).
    shape / rooms: force a shape (rect, L, T, U, Z, courtyard) / room count.
    """
    st = styles()[style]
    occupied = occupied or set()
    U0, V0 = origin_uv
    assert U0 % 2 == 0 and V0 % 2 == 0, "origin must be on the wall lattice (even u, v)"
    maxW, maxH = max_size_uv[0] // 2, max_size_uv[1] // 2
    for attempt in range(tries):
        shp = shape or _pick(rng, {k: v for k, v in st["shapes"].items() if k in SUPPORTED_SHAPES}, default="rect")
        long_ = _sample_quartiles(rng, st["size_units"]["W"], lo=4)
        short = _sample_quartiles(rng, st["size_units"]["H"], lo=4, hi=long_)
        if program:                      # big enough for the planned rooms at Westwood sizes
            need = sum(_kind_tiles(k) for k in program)
            if long_ * short < need:
                grow = math.sqrt(need / max(1, long_ * short))
                long_, short = int(math.ceil(long_ * grow)), int(math.ceil(short * grow))
        shrink = 1 - attempt / (tries * 1.5)
        long_, short = max(4, int(long_ * shrink)), max(4, int(short * shrink))
        W, H = (long_, short) if rng.random() < 0.5 else (short, long_)
        W, H = min(W, maxW), min(H, maxH)
        if shp in ("L", "T", "Z") and (W < 7 or H < 7): shp = "rect"
        if shp in ("U",) and (W < 9 or H < 7): shp = "rect"
        if shp == "courtyard" and (W < 10 or H < 10): shp = "rect"
        if W < 4 or H < 4: continue
        if W * H < min_units:                # the role needs this much floor (an inn's common room)
            W, H = min(maxW, max(W, int(math.ceil(min_units / max(1, H))))), H
            if W * H < min_units: H = min(maxH, int(math.ceil(min_units / max(1, W))))
            if W * H < min_units: continue
        U = _footprint(rng, shp, W, H)
        U, (W, H) = _transform(rng, U, W, H)
        area = sum(1 for v in U.values() if v != COURT)
        if program: n_rooms = len(program)
        elif rooms: n_rooms = rooms
        else:
            n_rooms = int(_pick(rng, st["rooms"], default="1"))
            # small Westwood houses split ~60 units into 2-3 rooms (stucco: 47% two-room at 9x7);
            # the "10" bucket is large complexes, so cap by area
            n_rooms = max(1, min(n_rooms, area // 22))
        labels = _assign_rooms(rng, U, n_rooms, [float(_kind_tiles(k, 'p50')) for k in program] if program else None)
        if program and len({v for v in labels.values() if v != COURT}) != len(program):
            continue                     # footprint too small to hold the requested rooms: try again
        if program and entrance_side:
            labels = _main_room_on_side(labels, entrance_side)
            if labels is None: continue  # the main room cannot reach the entrance side: try again
        cells = _cells_of(U0, V0, labels)
        if cells & occupied: continue
        b = _build(spec, rng, st, style, U0, V0, W, H, labels, program, entrance_side,
                   building_id or f"b{len(spec.d['objects'])}_{U0}_{V0}", cells, shp)
        if b is not None: return b
    return None


_VALID = None


def _valid_pieces():
    global _VALID
    if _VALID is None:
        with open(os.path.join(RULES, "walls.json"), encoding="utf-8") as f:
            _VALID = json.load(f)["valid_variations"]
    return _VALID


def _pieces_ok(U0, V0, point_mat):
    """True when every wall point's shape (corner, T-junction, cross...) exists for its material."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from nox import FACING_BY_ARMS
    pts = {_xy(U0, V0, p): m for p, m in point_mat.items()}
    valid = _valid_pieces()
    for (x, y), m in pts.items():
        arms = frozenset(a for a in ((-1, -1), (1, -1), (-1, 1), (1, 1)) if (x + a[0], y + a[1]) in pts)
        if str(FACING_BY_ARMS[arms]) not in valid.get(m, {}): return False
    return True


def _cells_of(U0, V0, labels):
    """All grid cells covered by the units (walls on their edges included) plus a 1-cell margin."""
    cells = set()
    for (i, j) in labels:
        for du in range(-2, 5):
            for dv in range(-2, 5):
                u, v = U0 + 2 * i + du, V0 + 2 * j + dv
                if (u + v) % 2 == 0: cells.add(((u + v) // 2, (u - v) // 2))
    return cells


def _xy(U0, V0, pt):
    u, v = U0 + pt[0], V0 + pt[1]
    return (u + v) // 2, (u - v) // 2


def _build(spec, rng, st, style, U0, V0, W, H, labels, program, entrance_side, bid, cells, shp):
    edges = _boundary(labels)
    deg = _point_degree(edges)
    room_ids = sorted({v for v in labels.values() if v != COURT}, key=lambda r: -sum(1 for v in labels.values() if v == r))
    ext_mat = st["exterior_wall"]
    int_mat = _pick(rng, st["interior_wall_materials"], exclude=("Invisible", "IronFence", "Cage", "Damaged"), default=ext_mat)
    if int_mat != ext_mat and rng.random() < 0.7: int_mat = ext_mat
    floors = {k: v for k, v in st["room_floors"].items() if not any(b in k for b in NOT_ROOM_FLOOR)}
    main_floor = _pick(rng, floors, default="OakWoodFloor")

    # walls: exterior material on points touching the outside or a courtyard, else interior material
    point_mat = {}
    for e, (a, b) in edges.items():
        outer = a in (None, COURT) or b in (None, COURT)
        for p in _edge_points(e):
            if outer or p not in point_mat: point_mat[p] = ext_mat if outer else point_mat.get(p, int_mat)
    if not _pieces_ok(U0, V0, point_mat):
        return None                      # a junction this material has no piece for: try another layout
    if program and entrance_side:
        # the main room must be able to open on the requested side (a building facing the square opens
        # onto it): otherwise try another layout before anything is written
        main = room_ids[0]
        ext = _runs(edges, lambda pr: (pr[0] in (None, COURT)) != (pr[1] in (None, COURT)))
        if not any(main in rn[3] and _on_outer_side(rn, W, H, entrance_side) and _door_point(rng, rn, deg) is not None
                   for rn in ext):
            return None
    for p, mat in point_mat.items():
        spec.wall(*_xy(U0, V0, p), mat)

    # rooms and floors
    b = Building(id=bid, style=style, wall_material=ext_mat)
    rooms = {}
    for k, r in enumerate(room_ids):
        units = [p for p, v in labels.items() if v == r]
        floor = main_floor if (k == 0 or rng.random() < 0.65) else _pick(rng, floors, default=main_floor)
        tiles = set()
        for (i, j) in units:
            t = _xy(U0, V0, (2 * i, 2 * j + 2))
            spec.tile(*t, floor); tiles.add(t)
        walls = set()
        for e, pair in edges.items():
            if r in pair:
                for p in _edge_points(e): walls.add(_xy(U0, V0, p))
        kind = program[k] if program and k < len(program) else None
        rooms[r] = Room(id=f"{bid}:r{k}", tiles=tiles, floor=floor, walls=walls, kind=kind, building=bid)
    court_floor = _pick(rng, st.get("outside_floors") or {}, exclude=("Water", "Lava"), default="GrassNorm")
    for (i, j), v in labels.items():
        if v == COURT: spec.tile(*_xy(U0, V0, (2 * i, 2 * j + 2)), court_floor)
    if not program:
        _default_kinds(rooms, room_ids)

    ext_types = {k: v for k, v in st["exterior_door_types"].items() if not any(x in k for x in NOT_HOUSE_DOOR)} or {"WoodenDoor": 1}
    int_types = {k: v for k, v in (st["interior_door_types"] or ext_types).items() if not any(x in k for x in NOT_HOUSE_DOOR)} or ext_types
    used_points = set()

    def place_door(run, dtype, connects):
        pt = _door_point(rng, run, deg)
        if pt is None or pt in used_points: return None
        # keep doors apart and off points next to another door
        if any(abs(pt[0] - q[0]) + abs(pt[1] - q[1]) <= 4 for q in used_points): return None
        used_points.add(pt)
        gap = _xy(U0, V0, pt)
        line = "/" if run[0] == "u" else "\\"
        o = spec.door(dtype, gap, line)
        d = Door(gap=gap, line=line, type=o["type"], connects=connects, px=(o["x"], o["y"]))
        return d

    # entrance(s): main room to the outside (or courtyard), on the requested / a likely side
    ext_runs = _runs(edges, lambda pr: (pr[0] in (None, COURT)) != (pr[1] in (None, COURT)))
    side = entrance_side or _pick(rng, st.get("entrance_sides") or {}, default="v_min")
    n_entr = 1 + (1 if rng.random() < 0.2 and len(room_ids) > 1 else 0)

    def run_room(run):
        return next(x for x in run[3] if x not in (None, COURT))
    # with a program, the main (largest) room gets the entrance whenever it has an outside wall, so
    # the program's first role (e.g. tavern) lands in the biggest room; otherwise prefer the side
    main_first = (lambda rn: room_ids.index(run_room(rn)) > 0) if program else (lambda rn: False)
    ranked = sorted(ext_runs, key=lambda rn: (not _on_outer_side(rn, W, H, side) if entrance_side else False, main_first(rn),
                                              not _on_outer_side(rn, W, H, side), _side_of_run(rn, W, H) != side,
                                              room_ids.index(run_room(rn)) if run_room(rn) in room_ids else 99,
                                              -len(rn[2]), rng.random()))
    for rn in ranked:
        if len(b.entrances) >= n_entr: break
        if b.entrances and run_room(rn) == b.entrances[0].connects[0].split(":r")[-1]: continue
        rid = run_room(rn)
        d = place_door(rn, _pick(rng, ext_types), (rooms[rid].id, "outside"))
        if d:
            rooms[rid].doors.append(d); b.entrances.append(d)
            if len(b.entrances) == 1: b.entrance_side = _side_of_run(rn, W, H) if _on_outer_side(rn, W, H, _side_of_run(rn, W, H)) else "inner"

    # the room with the main entrance takes the program's first role (a tavern opens onto the street)
    if program and b.entrances:
        entry = next(r for r in room_ids if rooms[r].id == b.entrances[0].connects[0])
        order = [entry] + [r for r in room_ids if r != entry]
        for k, r in enumerate(order):
            rooms[r].kind = program[k] if k < len(program) else None

    # interior doors: spanning tree from the entrance room, plus occasional extra loops
    int_runs = _runs(edges, lambda pr: pr[0] not in (None, COURT) and pr[1] not in (None, COURT))
    adj = defaultdict(list)
    for rn in int_runs:
        a, c = rn[3]
        adj[a].append((c, rn)); adj[c].append((a, rn))
    start = next((r for r in room_ids if any(d in b.entrances for d in rooms[r].doors)), room_ids[0])
    seen, queue = {start}, deque([start])
    while queue:
        r = queue.popleft()
        for nb, rn in sorted(adj[r], key=lambda t: (-len(t[1][2]), rng.random())):
            if nb in seen: continue
            d = place_door(rn, _pick(rng, int_types), (rooms[r].id, rooms[nb].id))
            if d is None:
                # try any other run between the same two rooms
                for nb2, rn2 in adj[r]:
                    if nb2 == nb and rn2 is not rn:
                        d = place_door(rn2, _pick(rng, int_types), (rooms[r].id, rooms[nb].id))
                        if d: break
            if d is None: continue
            rooms[r].doors.append(d); rooms[nb].doors.append(d)
            seen.add(nb); queue.append(nb)
    # rooms not reached through interior walls get their own outside door
    for r in room_ids:
        if r in seen: continue
        for rn in ext_runs:
            if run_room(rn) == r:
                d = place_door(rn, _pick(rng, ext_types), (rooms[r].id, "outside"))
                if d: rooms[r].doors.append(d); b.entrances.append(d); break

    b.rooms = [rooms[r] for r in room_ids]
    b.footprint = set().union(*(r.tiles for r in b.rooms))
    b.cells = cells
    b.shape, b.size_units = shp, (W, H)
    b.unreachable = [rooms[r].id for r in room_ids if not rooms[r].doors]
    return b


def _default_kinds(rooms, room_ids):
    """Room kinds from size when no program is given: largest room is the main/hall room."""
    for k, r in enumerate(room_ids):
        n = len(rooms[r].tiles)
        if k == 0: rooms[r].kind = "hall" if len(room_ids) >= 3 else "main"
        elif n <= 12: rooms[r].kind = "storage"
        else: rooms[r].kind = "bedroom"
