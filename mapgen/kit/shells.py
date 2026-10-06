"""Room shells as Westwood builds them: the shape of each room, partial partitions and the floor's pattern, drawn in
proportion to Westwood's campaign rooms of the room's type (rules/rooms/shells.json, measured by
`py rules/rooms/shells.py`; a type with under 8 rooms takes its size band's numbers).

Westwood (2026-10-05, 308 built rooms of the campaign maps, each layout once): two rooms in three are rectangles; the
rest a rectangle with a bay or alcove (15%), an L or T (8%) or more broken (10%), more so the larger the room (under 30
tiles 82% rectangles, 80-200 tiles 41%). A partial partition (a wall spur 1-3 points long) stands in 5% of rooms, 15-33%
of those over 80 tiles; free-standing wall pillars almost never (1%). A third of the floors mix two materials: a region
of the room in another (often a wing or one end), a border round it, worn patches of dirt, or inlaid panels.

Used by kit/building.py _build on the unit labels of a building (unit (i, j) -> room label), before its walls:

    labels = shape_rooms(rng, labels, kinds, keep=...)          # bays, alcoves, L notches
    spurs = spur_points(rng, labels, kinds, edges)             # partial partitions: {lattice point}
    tiles = floor_pattern(rng, units, main, kind, floors, work)  # {unit: material} for the units not on `main`
"""
import json, math, os
from collections import Counter, deque

SHELLS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "rules", "rooms",
                      "shells.json")
COURT = "court"
# NOX_SHELLS=0 builds the plain shells of before (rectangles, one floor, carpets less a ring), to compare a design's
# rooms before and after
ENABLED = os.environ.get("NOX_SHELLS", "1") != "0"
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIRTY = ("Dirt", "Cave", "Mud")
# the grounds a building stands on (the town's grass and paths): a floor that never touches them is no floor for a room
TOWN_GROUNDS = {"GrassNorm", "GrassSparse2"}
NOT_SECOND = ("Rug", "Grass", "Weeds", "Swamp", "Water", "Lava", "Ice", "Black", "Mine", "Rock")
_S = None


def stats():
    global _S
    if _S is None:
        try:
            with open(SHELLS, encoding="utf-8") as f: _S = json.load(f)["summary"]
        except OSError: _S = {}
    return _S


def tiles_of(n):
    """Floor tiles of a room of n units (kit/building._units_for the other way round)."""
    return max(1.0, n - 2 * math.sqrt(n))


def group(kind, n_units):
    """Westwood's shell numbers for a room of `kind` and n units: its type's when 8 or more rooms of the type, else its
    size band's."""
    s = stats()
    if not s: return None
    try:
        from kit.roomtypes import KIND_TYPE
        t = KIND_TYPE.get(kind) or kind
    except Exception:
        t = kind
    if t in s and s[t]["n"] >= 8: return s[t]
    tl = tiles_of(n_units)
    band = "tiles:0-30" if tl < 30 else "tiles:30-80" if tl < 80 else "tiles:80-200" if tl < 200 else "tiles:200-5000"
    return s.get(band)


# ------------------------------------------------------------------------------------------------ shapes
def _box(units):
    return (min(i for i, _ in units), max(i for i, _ in units), min(j for _, j in units), max(j for _, j in units))


def is_rect(units):
    i0, i1, j0, j1 = _box(units)
    return len(units) == (i1 - i0 + 1) * (j1 - j0 + 1)


def connected(units):
    if not units: return False
    start = next(iter(units))
    seen, q = {start}, deque([start])
    while q:
        i, j = q.popleft()
        for a, b in N4:
            n = (i + a, j + b)
            if n in units and n not in seen: seen.add(n); q.append(n)
    return len(seen) == len(units)


def _proportioned(units, most=3.2):
    i0, i1, j0, j1 = _box(units)
    a, c = i1 - i0 + 1, j1 - j0 + 1
    return max(a, c) <= most * min(a, c)


def _thin(units):
    """True when some unit of the room has room on neither side across one axis (a corridor one unit wide), which
    leaves no floor for furniture and no straight wall for a door."""
    s = set(units)
    return any(((i - 1, j) not in s and (i + 1, j) not in s) or ((i, j - 1) not in s and (i, j + 1) not in s) for i, j in s)


def _draw(rng, dist):
    keys = sorted(dist)
    tot = sum(dist[k] for k in keys)
    if tot <= 0: return None
    x = rng.random() * tot
    for k in keys:
        x -= dist[k]
        if x <= 0: return k
    return keys[-1]


def shape_rooms(rng, labels, kinds, least, keep=(), fixed_side=None, hall=None):
    """Bays, alcoves and L notches in proportion to Westwood's rooms of each room's type. labels: {unit: label}
    (COURT for a courtyard, missing outside); kinds: {label: kind or None}; least: {label: fewest units the room may
    keep}; keep: labels left as they are (a throne room, a chapel: their axis); fixed_side: units that must stay (the
    entrance side's row of the main room). Each room drawn to be a rectangle stays as it is; one drawn otherwise gives
    a corner to the room beside it (never to the outside: the outline stays) or takes a bay from it, checked so
    every room keeps one piece, its least size, its proportions and its place in the size order. Returns new labels."""
    lab = dict(labels)
    rooms = sorted({v for v in lab.values() if v != COURT}, key=str)

    def units(r): return {p for p, v in lab.items() if v == r}
    order0 = sorted(rooms, key=lambda r: (-len(units(r)), str(r)))
    size0 = {r: len(units(r)) for r in rooms}

    def ok(new):
        us = {r: {p for p, v in new.items() if v == r} for r in rooms}
        for r in rooms:
            u = us[r]
            if not u or not connected(u) or _thin(u): return False
            # a room may lose floor only down to its least size (one already under it may not lose any)
            if len(u) < least.get(r, 4) and len(u) < size0[r]: return False
            if r != hall and not _proportioned(u): return False
        # the program's kinds go to the rooms by size: keep the order
        if sorted(rooms, key=lambda r: (-len(us[r]), str(r))) != order0: return False
        return True

    # a notch or an alcove shapes the room beside it too, so the building's rooms are shaped against a budget: the
    # number of them Westwood's rooms of their types would leave other than rectangles (stochastic rounding), counting
    # those its footprint already shaped (an L building's L room); rooms are picked for it weighted by their odds
    odds = {}
    for r in order0:
        g = group(kinds.get(r), len(units(r)))
        odds[r] = 0.0 if (r in keep or not g) else 1.0 - g["shape"].get("rect", 1.0)
    budget = int(sum(odds.values()) + rng.random())
    over = rng.random() < 0.5
    tried = set()
    while True:
        bent = sum(1 for r in rooms if not is_rect(units(r)))
        if bent >= budget: break
        pool = {r: w for r, w in odds.items() if w > 0 and r not in tried and len(units(r)) >= 9 and is_rect(units(r))}
        if not pool: break
        r = _draw(rng, pool)
        tried.add(r)
        sh = group(kinds.get(r), len(units(r)))["shape"]
        cls = _draw(rng, {"L": sh.get("L", 0) + sh.get("T", 0), "bay": sh.get("bay", 0),
                          "two": sh.get("TUZ", 0) + sh.get("irregular", 0)}) or "bay"
        for step in range(2 if cls == "two" else 1):
            kind = "L" if cls == "L" or (cls == "two" and step == 0) else "bay"
            for cand in _candidates(rng, lab, r, kind, fixed_side or ()):
                # within the budget: an alcove taken from a rectangle beside it bends that room too
                # (one over it half the time: else a budget of one could never be spent, every notch and alcove
                # bending two rooms now that the outline stays)
                nb = _bent(cand, rooms)
                if ok(cand) and (nb <= max(budget, bent + (1 if step else 0)) or (nb == budget + 1 and over)):
                    lab = cand
                    break
    return lab


def _bent(lab, rooms):
    by = {}
    for p, v in lab.items(): by.setdefault(v, set()).add(p)
    return sum(1 for r in rooms if r in by and not is_rect(by[r]))


def _candidates(rng, lab, r, kind, fixed):
    """New label maps with room r given a notch (to a neighbour) or a bay (from a neighbour); the outline stays."""
    u = {p for p, v in lab.items() if v == r}
    i0, i1, j0, j1 = _box(u)
    w, h = i1 - i0 + 1, j1 - j0 + 1
    out = []
    corners = [(i0, j0, 1, 1), (i1, j0, -1, 1), (i0, j1, 1, -1), (i1, j1, -1, -1)]
    rng.shuffle(corners)
    if kind == "L":
        sizes = [(a, b) for a in range(max(2, round(w * 0.3)), max(2, round(w * 0.55)) + 1)
                 for b in range(max(2, round(h * 0.3)), max(2, round(h * 0.55)) + 1)]
    else:
        sizes = [(a, b) for a in (1, 2) for b in (2, 3)] + [(a, b) for a in (2, 3) for b in (1, 2)]
    rng.shuffle(sizes)
    for (ci, cj, di, dj) in corners:
        for (a, b) in sizes[:4]:
            if a >= w - 1 or b >= h - 1: continue
            block = {(ci + di * x, cj + dj * y) for x in range(a) for y in range(b)}
            if not block <= u or block & set(fixed): continue
            # who takes it: the outside when the corner lies on the building's edge both ways, else a room beside it
            outward = [(ci - di, cj + dj * y) for y in range(b)] + [(ci + di * x, cj - dj) for x in range(a)]
            takers = Counter(lab.get(p) for p in outward)
            if all(lab.get(p) is None for p in outward):
                # never to the outside: the building's outline stays as its footprint drew it (a notch out of a corner
                # had opened a way round Thornwick's locked gate, which closes on the houses)
                continue
            else:
                for t, _ in takers.most_common():
                    if t in (None, COURT, r): continue
                    new = dict(lab)
                    for p in block: new[p] = t
                    out.append(new)
                    break
    if kind == "bay":
        # an alcove: r takes a small block out of the room beside one of its sides, off its corners
        sides = []
        for j in range(j0, j1 + 1):
            sides.append(((i0 - 1, j), (-1, 0))); sides.append(((i1 + 1, j), (1, 0)))
        for i in range(i0, i1 + 1):
            sides.append(((i, j0 - 1), (0, -1))); sides.append(((i, j1 + 1), (0, 1)))
        rng.shuffle(sides)
        for (p, (di, dj)) in sides[:12]:
            n = lab.get(p)
            if n in (None, COURT, r): continue
            wd = rng.choice((2, 3, 3, 4)); dp = rng.choice((1, 2, 2))
            if di:                                # the block runs along j, reaching dp units into the neighbour
                block = {(p[0] + di * x, p[1] + y) for x in range(dp) for y in range(wd)}
                if not all((p[0] - di, q[1]) in u for q in block): continue
            else:
                block = {(p[0] + x, p[1] + dj * y) for x in range(wd) for y in range(dp)}
                if not all((q[0], p[1] - dj) in u for q in block): continue
            if not all(lab.get(q) == n for q in block) or block & set(fixed): continue
            new = dict(lab)
            for q in block: new[q] = r
            out.append(new)
    return out


# ------------------------------------------------------------------------------------------------ partitions
def spur_points(rng, labels, kinds, edges, hall=None, keep=()):
    """Partial partitions: for each room drawn to have one (Westwood's share of its type's rooms), a wall spur 1-3
    lattice points long standing out square from the middle stretch of one of its walls, with two units of floor or
    more beyond its tip. Returns {lattice point (doubled, as kit/building.py's wall points): (room label, on the wall)}:
    the spur's points, and its foot on the wall (True)."""
    out = {}
    rooms = sorted({v for v in labels.values() if v != COURT}, key=str)
    for r in rooms:
        if r in keep: continue
        u = {p for p, v in labels.items() if v == r}
        if len(u) < 30: continue
        g = group(kinds.get(r), len(u))
        if not g or rng.random() >= g.get("with_spur", 0): continue
        n = rng.choice((1, 2, 2, 2, 3))
        cands = []
        for (i, j) in sorted(u):
            for (di, dj) in N4:
                if (i - di, j - dj) in u: continue       # (i, j) lies along a wall on the side (-di, -dj)
                # the wall point at the corner shared by (i, j) and its neighbour along the wall, and the spur from it
                if di:
                    q = (i, j + 1)                         # neighbour along the wall (j direction)
                    if q not in u or (q[0] - di, q[1]) in u: continue
                    base = (i + (0 if di > 0 else 1), j + 1)       # lattice point between the two units on the wall line
                    step = (di, 0)
                else:
                    q = (i + 1, j)
                    if q not in u or (q[0], q[1] - dj) in u: continue
                    base = (i + 1, j + (0 if dj > 0 else 1))
                    step = (0, dj)
                pts = [(base[0] + step[0] * k, base[1] + step[1] * k) for k in range(1, n + 1)]
                # every spur point with the room's units on all four sides, and floor beyond the tip (2 units)
                def inner(p): return all((p[0] + a, p[1] + b) in u for a in (-1, 0) for b in (-1, 0))
                if not all(inner(p) for p in pts): continue
                tip = pts[-1]
                beyond = [(tip[0] + step[0] * k, tip[1] + step[1] * k) for k in (1, 2)]
                if not all(inner(p) for p in beyond): continue
                # off the room's corners: two units of straight wall either side of the base
                along = (0, 1) if di else (1, 0)
                if not all(inner((base[0] + along[0] * s + step[0], base[1] + along[1] * s + step[1])) for s in (-2, -1, 1, 2)):
                    continue
                cands.append((base, pts))
        if not cands: continue
        base, pts = rng.choice(cands)
        out[(2 * base[0], 2 * base[1])] = (r, True)
        for p in pts: out[(2 * p[0], 2 * p[1])] = (r, False)
    return out


# ------------------------------------------------------------------------------------------------ floors
def _ring(units):
    s = set(units)
    return {k for k in s if any((k[0] + a, k[1] + b) not in s for a in (-1, 0, 1) for b in (-1, 0, 1))}


def _never():
    _blend_rules()
    return _NEVER


def second_floor(rng, main, pattern, floors, work):
    """The second material: what Westwood lays with `main` (shells.json floor_pairs), else from the style's floors;
    dirt for worn patches. Never one Westwood keeps apart from `main` (rules/out/floors.json never_touch)."""
    s = _second_floor(rng, main, pattern, floors, work)
    if not s or frozenset((s, main)) in _never(): return None
    # nor one Westwood keeps apart from a ground (grass, dirt, water): it could meet it through a ruin's gap or a window
    return None if ground_shy(s) else s


def ground_shy(mat):
    """True when Westwood never lets `mat` touch a town's grass and keeps a built floor between them (rules/out/floors.json
    never_touch, its buffer no ground): BrokenCobbleDirtWebs, TileStarBlack, StoneLight, the rugs."""
    _blend_rules()
    return any(mat in pr and (pr - {mat}) & TOWN_GROUNDS and not any(g in b for b in buf for g in ("Grass", "Dirt"))
               for pr, buf in _NEVER_BUF.items())


def _second_floor(rng, main, pattern, floors, work):
    pairs = {k: v for k, v in (stats().get("floor_pairs", {}).get(main) or {}).items()
             if not any(x in k for x in NOT_SECOND)}
    if pattern == "patches":
        dirt = {k: v for k, v in pairs.items() if any(d in k for d in DIRTY)}
        if dirt: return _draw(rng, dirt)
        return "DirtDark2" if work or main in ("GreenBrick", "BlueBrick7", "RoughCobble", "CobbleDirt") else None
    pairs = {k: v for k, v in pairs.items() if not any(d in k for d in DIRTY) or work}
    if pairs: return _draw(rng, pairs)
    # the style's other floors, those Westwood blends with this one (a hard seam reads as a mistake)
    other = {k: v for k, v in (floors or {}).items() if k != main and not any(x in k for x in NOT_SECOND)
             and (work or not any(d in k for d in DIRTY))
             and ((_blend_rules().get(frozenset((k, main))) or {}).get("edge_share_sp") or 0) >= 0.5}
    return _draw(rng, other) if other else None


def floor_pattern(rng, units, main, kind, floors=None, work=False):
    """{unit: material} for the units of a room that are not on its main floor, drawn as Westwood lays a second floor in
    its rooms of the room's type (rules/rooms/shells.json: how many of them have one on 3% of their floor or more, how
    much of it, in which pattern): a region (a wing, a bay, a strip along one wall or one end), a border round the room,
    worn patches, inlaid panels."""
    units = list(units)
    if len(units) < 9: return {}
    g = group(kind, len(units))
    if not g or "floor_touched" not in g: return {}
    if rng.random() >= g["floor_touched"]: return {}
    q = g.get("touched_share") or {"p25": 0.09, "p50": 0.16, "p75": 0.31}
    a, m, b = q["p25"], q["p50"], q["p75"]
    target = max(0.04, min(0.5, rng.triangular(a - 0.25 * (b - a), b + 0.25 * (b - a), m)))
    pats = {k: v for k, v in (g.get("touched_pattern") or {}).items() if k not in (None, "null")}
    if sum(pats.values()) < 6:
        pats = {k: v for k, v in stats()["all built rooms"]["touched_pattern"].items() if k not in (None, "null")}
    for _ in range(3):                                 # a pattern the main floor has a partner for
        pattern = _draw(rng, pats)
        second = second_floor(rng, main, pattern, floors, work)
        if second and second != main: break
    else:
        return {}
    s = set(units)
    n = len(s)
    i0, i1, j0, j1 = _box(s)
    out = {}
    if pattern == "border":
        for k in _ring(s): out[k] = second
    elif pattern == "region":
        rest = s - _max_rect(s)
        if rest and 0.5 * target <= len(rest) / n <= 2.0 * target:
            for k in rest: out[k] = second            # the wing or the bay on its own floor
        else:                                          # a strip along one wall, or one end of the room
            sides = [("i", i0, 1), ("i", i1, -1), ("j", j0, 1), ("j", j1, -1)]
            ax, edge, d = rng.choice(sides)
            span = (j1 - j0 + 1) if ax == "i" else (i1 - i0 + 1)
            rows = max(1, round(target * n / max(1, span)))
            for (i, j) in s:
                k = (i - edge) * d if ax == "i" else (j - edge) * d
                if 0 <= k < rows: out[(i, j)] = second
    elif pattern == "patches":
        want = max(2, round(target * n))
        ring = sorted(_ring(s))
        tries = 0
        while len(out) < want and tries < 50:
            tries += 1
            p = rng.choice(ring if rng.random() < 0.7 else sorted(s))
            for _ in range(rng.choice((1, 2, 2, 3, 4))):
                out[p] = second
                nb = [(p[0] + x, p[1] + y) for x, y in N4 if (p[0] + x, p[1] + y) in s]
                if not nb: break
                p = rng.choice(nb)
    else:                                              # inlaid panels in rows, off the walls
        inner = s - _ring(s)
        long_i = (i1 - i0) >= (j1 - j0)
        pa, pb = (2, 1) if rng.random() < 0.6 else (2, 2)
        period = 3 if pa == 2 and pb == 1 else 4
        # rows far enough apart for the panels to cover about the target share of the floor
        yp = max(3, round(pa * pb / (period * target) * len(inner) / n))
        for (i, j) in sorted(inner):
            x, y = (i - i0 - 1, j - j0 - 1) if long_i else (j - j0 - 1, i - i0 - 1)
            if x % period < pa and y % yp < pb: out[(i, j)] = second
    if len(out) >= 0.6 * n: return {}
    return out


def _max_rect(units):
    """The largest rectangle of units inside a set of units."""
    i0, i1, j0, j1 = _box(units)
    best, bestA = set(), 0
    h = [0] * (j1 - j0 + 1)
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            h[j - j0] = h[j - j0] + 1 if (i, j) in units else 0
        stack = []
        for k in range(len(h) + 1):
            cur = h[k] if k < len(h) else 0
            start = k
            while stack and stack[-1][1] >= cur:
                s0, hh = stack.pop()
                if hh * (k - s0) > bestA:
                    bestA = hh * (k - s0)
                    best = {(x, j0 + y) for x in range(i - hh + 1, i + 1) for y in range(s0, k)}
                start = s0
            stack.append((start, cur))
    return best


_BLEND = None
_NEVER = set()
_NEVER_BUF = {}


def _blend_rules():
    global _BLEND
    if _BLEND is None:
        p = os.path.join(os.path.dirname(SHELLS), "..", "out", "floors.json")
        global _NEVER
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        _BLEND = {frozenset((r["a"], r["b"])): r for r in d["blend"]}
        _NEVER = {frozenset((r["a"], r["b"])) for r in d["never_touch"]}
        _NEVER_BUF.update({frozenset((r["a"], r["b"])): set(r.get("buffer_materials") or ()) for r in d["never_touch"]})
    return _BLEND


SIDES_TIPS = ((1, -1), (-1, -1), (1, 1), (-1, 1), (0, -2), (-2, 0), (2, 0), (0, 2))


def blend_pattern(spec, tiles, doors=()):
    """Edges between a room's two floors where Westwood blends the pair (rules/out/floors.json: dirt worn into
    brick, marble panels in a steel or brick trim): the overlay spills onto the tiles beside it, the room's own and those
    under its walls, and nothing else spills there (nox.Spec.pattern_tiles); never within 3 cells of a door, where the
    doorway's floor is the room's own. tiles: {tile: material} of one room; doors: the door gaps."""
    mats = set(tiles.values())
    if len(mats) < 2 or not hasattr(spec, "pattern_tiles"): return
    for pair in sorted({tuple(sorted((a, b))) for a in mats for b in mats if a != b}):
        rec = _blend_rules().get(frozenset(pair))
        if not rec or (rec.get("edge_share_sp") or 0) < 0.5 or not rec.get("preferred_edge_type"): continue
        over = rec["overlay"]; base = next(m for m in pair if m != over)
        if over not in spec.blend: spec.blending(over, -50, edge=rec["preferred_edge_type"])
        spec.edge_over[(over, base)] = rec["preferred_edge_type"]
        for t, m in tiles.items():
            if m != over: continue
            for a, b in SIDES_TIPS:
                n = (t[0] + a, t[1] + b)
                if tiles.get(n, base) != base: continue
                if any(max(abs(n[0] - g[0]), abs(n[1] - g[1])) <= 3 for g in doors): continue
                spec.pattern_tiles.setdefault(n, set()).add((over, base))
