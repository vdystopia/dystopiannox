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
WORK_ROOMS = {"storeroom", "smithy", "ore_store", "gear_store", "barracks", "kitchen", "ogre_den", "ogre_hall", "ogre_hoard"}
NOT_ROOM_FLOOR = ("Water", "Grass", "Lava", "Swamp", "Mine", "Black", "Weeds", "Ice",
                  "Rug")   # rugs: Westwood lays them as patches inside rooms (a furnisher's job)
# door objects that are fence gates or cage doors rather than house doors
NOT_HOUSE_DOOR = ("Gate", "Barred", "Cage", "Jail", "Spiked", "Dilapidated")
# One door family per building: Westwood's buildings use one door kind throughout (539 of 630; 11 use three).
# The main entrance takes the family's door, the doorways between rooms its single door: a double door into
# a bedroom is not believable (TreePlace v0.2 playtest).
SINGLE_OF = {"ArchedHalfDoor": "ArchedDoor", "DunMirHalfDoor": "DunMirDoor", "GalavaHalfDoor": "GalavaDoor",
             "LOTDHalfDoor": "LOTDSingleDoor", "WoodAndSteelHalfDoor": "WoodAndSteelDoor", "ThinWoodenDoor": "WoodenDoor",
             "BandedPlankDoor": "BandedWoodenDoor"}

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
        k_left = 1                                        # the largest room alone on one side (an inn's tavern)
        if target >= 5:                                   # many rooms: two groups of about equal floor, so the rooms
            half = sum(weights) / 2                       # stay near square (a manor's hall is not a strip across it)
            k_left = min(range(1, target), key=lambda k: abs(sum(weights[:k]) - half))
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


def _connected(units):
    """True when the units form one piece (edge neighbours)."""
    if not units: return True
    start = next(iter(units))
    seen, q = {start}, deque([start])
    while q:
        i, j = q.popleft()
        for n in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if n in units and n not in seen:
                seen.add(n); q.append(n)
    return len(seen) == len(units)


def _units_for(tiles):
    """Footprint units a room needs for `tiles` of the checker's floor tiles (Westwood's room sizes are in those): its
    walls take a strip around the edge, so a room of n units has about n - 2 sqrt(n) tiles (measured on the building
    lab and TreePlace: 12 units hold 6 tiles, 63 hold 48, 204 hold 176)."""
    return (1 + math.sqrt(1 + tiles)) ** 2


def _wing_labels(rng, parts, target, weights, base_labels):
    """Labels giving the largest wing to the main room and the other wings to the other rooms, or None when the other
    wings are too small for them: each room's floor at least 0.45 of its kind's typical size."""
    labels = dict(base_labels)
    keys = sorted(parts, key=lambda k: -len(parts[k]))
    big, rest = keys[0], keys[1:]
    ws = sorted(weights, reverse=True)[1:]
    if sum(len(parts[k]) for k in rest) < sum(_units_for(0.45 * w) for w in ws): return None
    for p in parts[big]: labels[p] = 0
    if target - 1 == 1 or target - 1 < len(rest):
        # one room for the other wings together (an L or T room), or as many as there are wings to share
        groups = [rest] if target - 1 == 1 else [[k] for k in rest[:target - 2]] + [rest[target - 2:]]
        if any(sum(len(parts[k]) for k in g) < _units_for(0.45 * w) for g, w in zip(groups, ws)): return None
        # a room of several wings must hang together: a U's two arms meet only through its base, so they are not
        # one room (TownLab: a home's living room in two closed-off halves either side of the bedroom)
        if any(not _connected(set().union(*(parts[k] for k in g))) for g in groups): return None
        for g, k_ in enumerate(groups):
            for kk in k_:
                for p in parts[kk]: labels[p] = 1 + g
        return labels
    area = {k: len(parts[k]) for k in rest}
    tot = sum(area.values())
    alloc = {k: max(1, round((target - 1) * area[k] / tot)) for k in rest}
    while sum(alloc.values()) > target - 1:
        k = max(rest, key=lambda k: alloc[k]); alloc[k] -= 1
    while sum(alloc.values()) < target - 1:
        k = max(rest, key=lambda k: area[k] / alloc[k]); alloc[k] += 1
    rid, wi = 1, 0
    for k in rest:
        if area[k] < sum(_units_for(0.45 * w) for w in ws[wi:wi + alloc[k]]): return None
        r = _rects_of_part(parts[k])
        min_side = 4 if min(r[1] - r[0], r[3] - r[2]) >= 8 else 3
        rects = []
        _split(rng, r, alloc[k], min_side, rects, ws[wi:wi + alloc[k]] if alloc[k] > 1 else None)
        wi += alloc[k]
        for (i0, i1, j0, j1) in rects:
            for i in range(i0, i1):
                for j in range(j0, j1):
                    if (i, j) in parts[k]: labels[(i, j)] = rid
            rid += 1
    return labels


def _assign_rooms(rng, U, target, weights=None, side=None):
    """Label units with room ids: each footprint part gets rooms in proportion to its area."""
    parts = defaultdict(set)
    for p, v in U.items():
        if v != COURT: parts[v].add(p)
    labels = dict((p, COURT) for p, v in U.items() if v == COURT)
    # a building with a room program on a multi-part footprint (T, L, U, Z): its main room (the largest weight) takes
    # the largest wing whole and the other rooms share the other wings, so an inn's tavern is not left the size of its
    # kitchen; only when the other wings hold the other rooms at a fair size (else the floor is shared as below)
    wings = _wing_labels(rng, parts, target, weights, labels) if weights and len(parts) > 1 and 2 <= target <= 4 and \
        max(weights) >= 1.5 * sorted(weights)[-2] else None          # a house's main room; a manor shares its wings
    if wings is not None: return wings
    # a part too small to be a room of its own (a T's short stem, an L's stub) joins the room beside it, so that room is
    # L or T shaped as Westwood's are, instead of a closet the checker calls small for its kind
    least = _units_for(0.45 * min(weights)) if weights else 16
    stubs = {k for k in parts if len(parts[k]) < least} if len(parts) > 1 else set()
    if len(stubs) == len(parts): stubs = set()
    main = {k: s for k, s in parts.items() if k not in stubs}
    hub = _hub_labels(rng, next(iter(main.values())), target, weights, side) if len(main) == 1 and target >= 5 and \
        weights else None
    if hub: labels.update(hub)
    else: _share_parts(rng, main, target, weights, labels, side)
    for k in sorted(stubs, key=str):
        near = Counter(labels[n] for (i, j) in parts[k] for n in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1))
                       if n not in parts[k] and labels.get(n, COURT) != COURT)
        lab = near.most_common(1)[0][0] if near else 0
        for p in parts[k]: labels[p] = lab
    return labels


def _hub_labels(rng, units, target, weights, side=None):
    """A great hall down the middle of a large building with the other rooms in a row along each side, each reaching
    from the outer wall to the hall and opening onto it (the doors' spanning tree runs breadth first from the hall).
    Westwood's multi-room buildings give their largest room half or more of the floor (rules/out/buildings.json
    hall_share, medians 0.5-0.8) and reach the other rooms through it; few have corridors (0-22% by style). The hall
    is about a third of the building's width; the side rooms take the program's other weights, the larger ones
    alternating between the sides. The hall runs toward the entrance `side` (u_min ... v_max) so the door opens
    into it, else along the longer side. Returns {unit: label} (the hall 0) or None when the part is too small."""
    i0, i1, j0, j1 = _rects_of_part(units)
    W, H = i1 - i0, j1 - j0
    along_i = side in ("u_min", "u_max") if side else W >= H
    L, S = (W, H) if along_i else (H, W)
    hb = max(3, round(S * 0.34))
    side = S - hb
    n = target - 1
    nA, nB = (n + 1) // 2, n // 2
    if side < 6 or L < 3 * nA: return None
    dA = side // 2
    ws = sorted(weights[1:], reverse=True)[:n] if len(weights) > 1 else [1.0] * n
    ws += [min(ws or [1.0])] * (n - len(ws))
    wA, wB = ws[0::2], ws[1::2]
    if rng.random() < 0.5: wA.reverse()               # the larger rooms not always at the same end
    if rng.random() < 0.5: wB.reverse()

    def cuts(ws_):
        tot, acc, pos = sum(ws_), 0.0, [0]
        for w in ws_[:-1]:
            acc += w
            pos.append(round(L * acc / tot))
        pos.append(L)
        for k in range(1, len(pos) - 1): pos[k] = max(pos[k], pos[k - 1] + 3)
        for k in range(len(pos) - 2, 0, -1): pos[k] = min(pos[k], pos[k + 1] - 3)
        return pos

    pA, pB = cuts(wA), cuts(wB)
    out = {}
    for (i, j) in units:
        a, c = (i - i0, j - j0) if along_i else (j - j0, i - i0)
        if dA <= c < dA + hb: out[(i, j)] = 0
        elif c < dA: out[(i, j)] = 1 + next(k for k in range(nA) if a < pA[k + 1])
        else: out[(i, j)] = 1 + nA + next(k for k in range(nB) if a < pB[k + 1])
    return out


def _share_parts(rng, parts, target, weights, labels, side=None):
    """Label the parts' units with rooms 0..target-1: each part gets rooms in proportion to its area."""
    total = sum(len(s) for s in parts.values())
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
        hub = _hub_labels(rng, s, alloc[k], [1.0] * alloc[k], side) if alloc[k] >= 5 and weights else None
        if hub:                                   # a wing holding many rooms: its own hall with rooms along it
            for p, lab in hub.items(): labels[p] = rid + lab
            rid += alloc[k]
            continue
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


def _door_points(run, deg):
    """[(distance from the run's middle, lattice point)] of the points inside a straight run (not an end, not a
    junction), nearest the middle first."""
    kind, line, ps, _ = run
    cands = []
    for k in range(1, len(ps)):              # interior points between edge k-1 and edge k
        pos = ps[k]
        pt = (2 * line, 2 * pos) if kind == "u" else (2 * pos, 2 * line)
        if deg[pt] == 2: cands.append((abs(k - len(ps) / 2), pt))
    return sorted(cands)


def _door_point(rng, run, deg):
    """A lattice point inside a straight run (not an end, not a junction), preferring the middle."""
    if len(run[2]) < 2: return None
    cands = _door_points(run, deg)
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


def _kind_tiles(kind, q="p25", default=30):
    """Typical floor area (tiles ~ footprint units) of a room kind in Westwood's maps."""
    global _ROOM_TYPES
    if _ROOM_TYPES is None:
        import json, os
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                               "rules", "out", "room_types.json"), encoding="utf-8") as f:
            _ROOM_TYPES = json.load(f)["types"]
    if kind not in _ROOM_TYPES:                 # the kit's own kinds take their Westwood kind's sizes (a herbalist's
        from kit.identity import WESTWOOD_KIND, ROOMS   # room is a laboratory, a mess hall a dining hall)
        kind = WESTWOOD_KIND.get(kind) or (ROOMS.get(kind) or {}).get("base") or kind
    return ((_ROOM_TYPES.get(kind) or {}).get("tiles") or {}).get(q) or default


_BASE_KINDS = None


def _kind_min_tiles(kind, scaled=True):
    """The fewest floor tiles a room of `kind` should have: Westwood's 10th percentile (rules/out/room_types.json), or
    the checker's lower bound for the kind when that is higher (validate/baseline.json room_kinds: the 5th percentile
    of the rooms it read, 166 tiles for a tavern), so the checker never calls a generated room small for its kind."""
    global _BASE_KINDS
    if _BASE_KINDS is None:
        p = os.path.join(os.path.dirname(RULES), "..", "validate", "baseline.json")
        _BASE_KINDS = json.load(open(p, encoding="utf-8")).get("room_kinds", {}) if os.path.exists(p) else {}
    from kit.identity import WESTWOOD_KIND, ROOMS
    wk = WESTWOOD_KIND.get(kind) or (ROOMS.get(kind) or {}).get("base") or kind
    # at the kit's scale (identity.BUILDING_SCALE, 1.25 Westwood's) a room's least floor grows with the square of it:
    # Westwood's 10th percentile bedroom is 12 tiles, a cramped closet at our scale (2026-10-05 room audit)
    from kit.identity import BUILDING_SCALE
    # (the scale once, not squared: squared, a mill's two rooms fitted its lot 4 times in 10)
    return max(_kind_tiles(kind, "p10", default=8) * (BUILDING_SCALE if scaled else 1.0),
               ((_BASE_KINDS.get(wk) or {}).get("tiles") or [0])[0])


def _rooms_fit(labels, program, scaled=True):
    """True when the rooms, largest first, hold the program's kinds, largest first, at their least size or more
    (_kind_min_tiles)."""
    sizes = sorted(Counter(v for v in labels.values() if v != COURT).values(), reverse=True)
    need = sorted((_units_for(_kind_min_tiles(k, scaled)) for k in program), reverse=True)
    return all(s >= n for s, n in zip(sizes, need))


ROOM_ASPECT_MAX = 3.2       # Westwood's rooms: long side over short side rarely past 3 (Thornwick v0.2's manor had
                            # its library, study and bedrooms 2-3 tiles wide and five times as long)


def _rooms_proportioned(labels, hall=0):
    """True when no room but the hall (label `hall`, a great hall may run long) is a strip: its box's long side at
    most ROOM_ASPECT_MAX times its short side."""
    boxes = {}
    for (i, j), v in labels.items():
        if v == COURT or v == hall: continue
        b = boxes.setdefault(v, [i, i, j, j])
        b[0], b[1], b[2], b[3] = min(b[0], i), max(b[1], i), min(b[2], j), max(b[3], j)
    for i0, i1, j0, j1 in boxes.values():
        a, c = i1 - i0 + 1, j1 - j0 + 1
        if max(a, c) > ROOM_ASPECT_MAX * min(a, c): return False
    return True


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
        if W > maxW or H > maxH: continue        # the transposition swapped the sides past the lot
        area = sum(1 for v in U.values() if v != COURT)
        if program: n_rooms = len(program)
        elif rooms: n_rooms = rooms
        else:
            n_rooms = int(_pick(rng, st["rooms"], default="1"))
            # small Westwood houses split ~60 units into 2-3 rooms (stucco: 47% two-room at 9x7);
            # the "10" bucket is large complexes, so cap by area
            n_rooms = max(1, min(n_rooms, area // 22))
        labels = _assign_rooms(rng, U, n_rooms, [float(_kind_tiles(k, 'p50')) for k in program] if program else None,
                               entrance_side)
        if program and len({v for v in labels.values() if v != COURT}) != len(program):
            continue                     # footprint too small to hold the requested rooms: try again
        if program and entrance_side:
            labels = _main_room_on_side(labels, entrance_side)
            if labels is None: continue  # the main room cannot reach the entrance side: try again
        # a room below its least size (a closet bedroom): try again; at the kit's scale for most tries, then at
        # Westwood's own least size, never below it (a fallback with no check at all gave 6-tile rooms)
        if program and not _rooms_fit(labels, program, scaled=attempt < tries * 3 // 4):
            continue
        if program and attempt < tries * 3 // 4 and not _rooms_proportioned(labels):
            continue                     # a room drawn out into a corridor: try again
        cells = _cells_of(U0, V0, labels)
        if cells & occupied: continue
        b = _build(spec, rng, st, style, U0, V0, W, H, labels, program, entrance_side,
                   building_id or f"b{len(spec.d['objects'])}_{U0}_{V0}", cells, shp, strict=attempt < tries * 3 // 4)
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


def _build(spec, rng, st, style, U0, V0, W, H, labels, program, entrance_side, bid, cells, shp, strict=True):
    edges = _boundary(labels)
    deg = _point_degree(edges)
    room_ids = sorted({v for v in labels.values() if v != COURT}, key=lambda r: -sum(1 for v in labels.values() if v == r))
    ext_mat = st["exterior_wall"]
    int_mat = _pick(rng, st["interior_wall_materials"], exclude=("Invisible", "IronFence", "Cage", "Damaged"), default=ext_mat)
    if int_mat != ext_mat and rng.random() < 0.7: int_mat = ext_mat
    floors = {k: v for k, v in st["room_floors"].items() if not any(b in k for b in NOT_ROOM_FLOOR)}
    # bare earth floors only a working room (Westwood's stone houses: 2.7% dirt, their barns and stores): a manor's
    # great hall on packed dirt reads as a barn
    clean = {k: v for k, v in floors.items() if not k.startswith("Dirt")} or floors
    main_floor = _pick(rng, clean, default="OakWoodFloor")

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
        work = program and k < len(program) and program[k] in WORK_ROOMS
        floor = main_floor if (k == 0 or rng.random() < 0.65) else _pick(rng, floors if work else clean, default=main_floor)
        tiles = set()
        for (i, j) in units:
            t = _xy(U0, V0, (2 * i, 2 * j + 2))
            spec.tile(*t, floor); tiles.add(t)
            if hasattr(spec, "indoor"): spec.indoor[t] = floor    # its doorways' thresholds (nox.Spec._door_thresholds)
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
    from nox import door_rules
    ext_type = _pick(rng, ext_types)
    int_type = SINGLE_OF.get(ext_type, ext_type)
    if door_rules()["types"].get(int_type, {}).get("kind") == "double":
        int_type = "WoodenDoor"
    used_points = set()

    def along(gap, line):                # a door's place along its wall line, in the furnisher's units
        return gap[0] - gap[1] if line == "/" else gap[0] + gap[1] + 1

    def place_door(run, dtype, connects, centre=None, avoid=()):
        pt = _door_point(rng, run, deg)
        line_ = "/" if run[0] == "u" else "\\"
        bad = lambda p: any(l_ == line_ and abs(along(_xy(U0, V0, p), line_) - a0) < ALTAR_AXIS for l_, a0 in avoid)
        if pt is not None and bad(pt):       # off the altar's axis (the draw is made all the same)
            pt = next((q for _, q in _door_points(run, deg) if not bad(q) and q not in used_points), None)
        if pt is not None and centre:    # the middle of the whole wall instead (the random draw is made all the same,
            c = _wall_middle(centre, deg)                # so the rest of the map comes out as before)
            if c and c not in used_points and not any(abs(c[0] - q[0]) + abs(c[1] - q[1]) <= 4 for q in used_points):
                pt = c
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
        d = place_door(rn, ext_type, (rooms[rid].id, "outside"))
        if d:
            rooms[rid].doors.append(d); b.entrances.append(d)
            if len(b.entrances) == 1: b.entrance_side = _side_of_run(rn, W, H) if _on_outer_side(rn, W, H, _side_of_run(rn, W, H)) else "inner"

    # the room with the main entrance takes the program's first role (a tavern opens onto the street)
    if program and b.entrances:
        entry = next(r for r in room_ids if rooms[r].id == b.entrances[0].connects[0])
        order = [entry] + [r for r in room_ids if r != entry]
        for k, r in enumerate(order):
            rooms[r].kind = program[k] if k < len(program) else None

    # a throne room is entered through its SE wall, so its throne can face the door (_seat_throne)
    throne = None
    if program and "throne_room" in program and b.entrances:
        throne = _seat_throne(rooms, room_ids, program, labels, b)
        if throne is False:
            if strict: return None       # no room can face its throne down to its door: try another layout
            throne = None

    # a chapel's altar stands across the nave from its main door, in line with it: no inner door takes that place
    # (Ambermere, 2026-10-05: the crypt's door sat in the middle of the altar's wall, the altar beside it, the pews'
    # aisle off the door's line and half the nave bare)
    axes = {}
    for d in b.entrances:
        rr = next((r for r in room_ids if rooms[r].id == d.connects[0]), None)
        if rr is not None and rooms[rr].kind in ALTAR_ROOMS and rr not in axes: axes[rr] = (d.line, along(d.gap, d.line))
    # interior doors: spanning tree from the entrance room, plus occasional extra loops
    int_runs = _runs(edges, lambda pr: pr[0] not in (None, COURT) and pr[1] not in (None, COURT))
    throne_wall = throne and [rn for rn in int_runs if rn[0] == "u" and rn[1] == throne[1] and frozenset(rn[3]) == throne[0]]
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
            d = place_door(rn, int_type, (rooms[r].id, rooms[nb].id),
                           centre=throne_wall if throne and frozenset((r, nb)) == throne[0] else None,
                           avoid=[axes[x] for x in (r, nb) if x in axes])
            if d is None:
                # try any other run between the same two rooms
                for nb2, rn2 in adj[r]:
                    if nb2 == nb and rn2 is not rn:
                        d = place_door(rn2, int_type, (rooms[r].id, rooms[nb].id))
                        if d: break
            if d is None: continue
            rooms[r].doors.append(d); rooms[nb].doors.append(d)
            seen.add(nb); queue.append(nb)
    # rooms not reached through interior walls get their own outside door
    for r in room_ids:
        if r in seen: continue
        for rn in ext_runs:
            if run_room(rn) == r:
                d = place_door(rn, ext_type, (rooms[r].id, "outside"))
                if d: rooms[r].doors.append(d); b.entrances.append(d); break

    if program and "throne_room" in program and strict:
        # the throne room's way in came out in its SE wall, and the NW wall across from it is free of doors where the
        # throne goes (in line with that door)
        tr = next(r for r in room_ids if rooms[r].kind == "throne_room")
        ins = [d for d in rooms[tr].doors if d in b.entrances][:1] or rooms[tr].doors[:1]
        if not ins or not _in_se_wall(rooms[tr], ins[0]): return None
        a0 = ins[0].gap[0] - ins[0].gap[1]
        cu = sum(x + y for x, y in rooms[tr].tiles) / len(rooms[tr].tiles)
        if any(d.line == "/" and d.gap[0] + d.gap[1] + 1 < cu and abs((d.gap[0] - d.gap[1]) - a0) < 5.5
               for d in rooms[tr].doors): return None
    b.rooms = [rooms[r] for r in room_ids]
    b.footprint = set().union(*(r.tiles for r in b.rooms))
    b.cells = cells
    b.shape, b.size_units = shp, (W, H)
    b.unreachable = [rooms[r].id for r in room_ids if not rooms[r].doors]
    return b


ALTAR_ROOMS = ("chapel", "dark_chapel")
ALTAR_AXIS = 6.0         # units an inner door keeps from the line of an altar room's main door


def _in_se_wall(room, d):
    """True if door d lies in the room's SE wall (a '/' wall on the room's high-u side)."""
    cu = sum(x + y for x, y in room.tiles) / len(room.tiles)
    return d.line == "/" and d.gap[0] + d.gap[1] + 1 > cu


def _seat_throne(rooms, room_ids, program, labels, b):
    """Puts the throne room where its throne can face its door. Westwood's Dun Mir throne faces SE only (kit/furnish.py
    place_throne), so a throne room needs its way in through its SE wall, across the room from the NW wall the throne
    stands on (2026-10-05 playtest, Greywatch: the keep's throne room was entered from its SW end and its throne faced
    "sideways towards the store room"). The entrance room keeps the throne when the entrance is in its SE wall (a keep
    entered from the SE, its hall running from the door to the throne). Else the throne goes to the largest room on the
    entrance room's NW side (a hall entered from the SW or NE has rooms along its NW side, each reached through its SE
    wall), roomier the deeper it runs from that wall, and the entrance room takes the program's next role (the great
    hall). Returns None when the entrance room keeps it, (rooms, wall line) of the wall between the entrance room and
    the throne room, whose door the caller centres on it (_merge_wall), or False when no room will do."""
    entry = next(r for r in room_ids if rooms[r].id == b.entrances[0].connects[0])
    if rooms[entry].kind == "throne_room" and _in_se_wall(rooms[entry], b.entrances[0]): return None
    shared = defaultdict(list)           # room -> unit lines L where it lies against the entrance room's NW side
    for (i, j), lab in labels.items():
        if lab == entry and labels.get((i - 1, j)) not in (None, COURT, entry):
            shared[labels[(i - 1, j)]].append(i)

    def depth(r):                        # how far it runs from its SE wall to its NW wall, against its width
        us = [x + y for x, y in rooms[r].tiles]; vs = [x - y for x, y in rooms[r].tiles]
        return (max(us) - min(us) + 2) / max(2, max(vs) - min(vs) + 2)

    least = _kind_min_tiles("throne_room", scaled=False)
    cands = [r for r, ls in shared.items() if len(ls) >= 3 and len(rooms[r].tiles) >= least]
    if not cands: return False
    best = max(cands, key=lambda r: (min(depth(r), 1.0) * len(rooms[r].tiles), len(rooms[r].tiles)))
    others = [r for r in dict.fromkeys([entry] + list(room_ids)) if r != best]
    roles = list(program)
    roles.remove("throne_room")
    plan = {best: "throne_room"}
    for r, k in zip(others, roles + [None] * len(others)): plan[r] = k
    if any(k and len(rooms[r].tiles) < _kind_min_tiles(k, scaled=False) for r, k in plan.items()): return False
    for r, k in plan.items(): rooms[r].kind = k
    return frozenset((entry, best)), Counter(shared[best]).most_common(1)[0][0]


def _wall_middle(runs, deg):
    """The lattice point nearest the middle of the wall the runs make together (the wall between a throne room and the
    room it is entered from), where a door may go (not a junction); None when they do not make one unbroken wall.
    _boundary keeps an edge's room pair in the order it met them, and a mirrored footprint meets them both ways, so one
    wall comes out as several runs (the keep's wall between its hall and the throne room as six runs of 1-3 edges, and
    the door near the room's end, 2026-10-05 playtest)."""
    if not runs: return None
    line = runs[0][1]
    ps = sorted(p for rn in runs for p in rn[2])
    if ps != list(range(ps[0], ps[-1] + 1)) or len(ps) < 2: return None
    cands = [(abs(k - len(ps) / 2), k, (2 * line, 2 * ps[k])) for k in range(1, len(ps)) if deg[(2 * line, 2 * ps[k])] == 2]
    return min(cands)[2] if cands else None


def _default_kinds(rooms, room_ids):
    """Room kinds from size when no program is given: largest room is the main/hall room."""
    for k, r in enumerate(room_ids):
        n = len(rooms[r].tiles)
        if k == 0: rooms[r].kind = "hall" if len(room_ids) >= 3 else "main"
        elif n <= 12: rooms[r].kind = "storage"
        else: rooms[r].kind = "bedroom"
