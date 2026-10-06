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


def group(kind, n_units, shape=False):
    """Westwood's shell numbers for a room of `kind` and n units: its type's when 8 or more rooms of the type, else its
    size band's. shape: the room-shape numbers (rules/rooms/shells_shape.json, kept as measured on 2026-10-05), else the
    floors' (rules/rooms/shells.json, the curated rooms)."""
    s = shape_stats() if shape else stats()
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


_SHAPE = None


def shape_stats():
    global _SHAPE
    if _SHAPE is None:
        try:
            with open(os.path.join(os.path.dirname(SHELLS), "shells_shape.json"), encoding="utf-8") as f:
                _SHAPE = json.load(f)["groups"]
        except OSError: _SHAPE = {}
    return _SHAPE


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
        g = group(kinds.get(r), len(units(r)), shape=True)
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
        sh = group(kinds.get(r), len(units(r)), shape=True)["shape"]
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
        g = group(kinds.get(r), len(u), shape=True)
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
    """{unit: material} for the units of a room that are not on its main floor, laid before it is furnished where
    Westwood's second floors follow the room's shape (zone_odds): a wing or an alcove on its own floor, a border
    round the room. The second floors under its pieces (a tomb's plinth, a hearthstone, a dais) are laid after
    furnishing (lay_zones). Westwood's other second floors (a strip along one wall, patches, inlaid squares) are laid
    nowhere: with no relation to the room they read as mistakes (independent judges, 2026-10-06)."""
    units = list(units)
    if len(units) < 9: return {}
    odds = zone_odds(kind, len(units))
    s = set(units)
    rest = s - _max_rect(s)
    inner = s - _ring(s)
    # a wing or an alcove: each piece two units deep or more both ways (a strip one unit wide along a wall is no wing:
    # the judges' "brick band along one wall")
    if not rest or len(rest) > 0.45 * len(s) or _thin(rest): odds.pop("wing", None)
    if len(inner) < 4: odds.pop("border", None)
    x = rng.random()
    pattern = None
    for k in sorted(odds):
        x -= odds[k]
        if x < 0: pattern = k; break
    if not pattern: return {}
    second = second_floor(rng, main, "region", floors, work)
    if not second or second == main: return {}
    if pattern == "wing": return {k: second for k in rest}
    return {k: second for k in _ring(s)}


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


# ------------------------------------------------------------------------------------------------ purposeful floors
# What Westwood's second floors and carpets are for (rules/rooms/shells.json `second_purpose`, `carpet_purpose`,
# `focal_rate`, `focal_pairs`; measured by rules/rooms/shells.py on the curated campaign rooms, 2026-10-06):
# - a hearthstone of brick under the fireplace or stove (27 of Westwood's 33 rooms with one: 1-3 squares along the
#   wall, RedBrick on planks, Redbrick3 on GalavaBrick);
# - a plinth under each tomb (23 of 25 crypts: 1 by 2 squares of GalavaBrownMarble or BlueBrick3 under a sarcophagus
#   on GreenBrick; a band under a row of them; else dirt worn round the tombs);
# - the throne's dais and the runner from the door to it (3 of 4 throne rooms); the floor under the bar (2 of 5 taverns);
# - a wing or an alcove on its own floor, a border round the room;
# - carpets under the seating and the tables, before and beside the bed, down the aisle (bedrooms: 23 of 46 rooms with
#   a bed have the carpet at it).
# A second floor with no relation to the room's pieces, doors or shape (the scattered squares, a band along one wall,
# patches in the corners) is not laid: independent judges read them as purposeless (2026-10-06).
FOCAL_TYPES = (("tomb", r"^Crypt\d|Coffin|Sarcophag|Tombstone|LOTDTomb"), ("hearth", r"Fireplace|FirePit|^Stove"),
               ("throne", r"Throne"), ("bar", r"^Bar(Piece|Corner|Hinged)"))
CULTURE_FLOORS = ("LOTD", "DunMir")       # a culture's own floors, kept (the Land of the Dead's, Dun Mir's)
FOCAL_RATE = {"tomb": 0.86, "hearth": 0.82, "throne": 0.75, "bar": 0.4}     # fallbacks of shells.json focal_rate
_FOCAL_RE = None


def floor_family(mat):
    """wood (planks), stone (brick, cobble, tile, flagstones), marble, earth (dirt, cave), rug or other: as
    rules/rooms/shells.py floor_family."""
    import re
    if not mat: return None
    if mat.startswith("Rug"): return "rug"
    if "Marble" in mat: return "marble"
    if re.search(r"Wood|Oak|Redwood|Slat|Plank", mat): return "wood"
    if re.search(r"Dirt|Cave|Mud|Grass|Weeds|Sand|Swamp", mat): return "earth"
    if re.search(r"Brick|Cobble|Tile|Stone|Rough|LOTD|DunMir|Galava|Pitted|Mine", mat): return "stone"
    return "other"


def _type_of(kind):
    try:
        from kit.roomtypes import KIND_TYPE
        return KIND_TYPE.get(kind) or kind
    except Exception:
        return kind


def fit_families(kind):
    """The floor families Westwood lays in rooms of `kind`'s type (a tenth of its rooms or more), None when it has
    none of the type: throne rooms stone or marble, crypts, chapels and cells stone, bedrooms wood or stone."""
    g = stats().get(_type_of(kind))
    if not g or not g.get("main_family"): return None
    fams = {f for f, s in g["main_family"].items() if s >= 0.1 and f}
    if "stone" in fams: fams.add("marble")                 # a polished stone where a stone floor goes
    return fams


def fit_floor(rng, kind, floor, floors):
    """`floor` when Westwood lays its family in rooms of `kind`'s type, else one of the style's `floors` that is (by
    their weights), else Westwood's own main floor for the type (its commonest). rng: the shell's own generator."""
    fams = fit_families(kind)
    g = stats().get(_type_of(kind)) or {}
    mf = g.get("main_floor") or {}
    if g.get("n", 0) >= 8 and mf and not floor.startswith(CULTURE_FLOORS):
        # a floor Westwood lays in most rooms of the type (crypts: GreenBrick in 23 of 25), as often as it does
        top, k = max(mf.items(), key=lambda kv: (kv[1], kv[0]))
        if k >= 0.6 * g["n"] and not ground_shy(top) and rng.random() < k / g["n"]: return top
    if not fams or floor_family(floor) in fams: return floor
    ok = {k: v for k, v in (floors or {}).items() if floor_family(k) in fams and not ground_shy(k)}
    if ok: return _draw(rng, ok)
    ww = {k: v for k, v in (stats().get(_type_of(kind)) or {}).get("main_floor", {}).items()
          if floor_family(k) in fams and not ground_shy(k)}
    return _draw(rng, ww) if ww else floor


def zone_odds(kind, n_units):
    """{purpose: chance} of the room laying a second floor for that purpose before it is furnished: the type's
    floor_touched times the share of its second floors that fill a wing or run round the room as a border (the rest
    lie under its pieces: lay_zones, after furnishing)."""
    g = group(kind, n_units)
    if not g or "floor_touched" not in g: return {}
    pur = g.get("second_purpose") or {}
    return {k: g["floor_touched"] * pur.get(k, 0) for k in ("wing", "border")}


def _focal_re():
    global _FOCAL_RE
    if _FOCAL_RE is None:
        import re
        _FOCAL_RE = [(f, re.compile(p)) for f, p in FOCAL_TYPES]
    return _FOCAL_RE


def focal_family(t):
    return next((f for f, rx in _focal_re() if rx.search(t or "")), None)


def _things():
    from kit import furnish as F
    return F._rules()[3]


def _squares_under(o, sq, things, least=0.5):
    """The room's squares (i, j) an object covers (each overlapped by `least` uv units both ways), and the object's uv;
    a square's centre is uv (2i + 2, 2j), it spans 2 uv units."""
    from nox import CELL
    K = CELL / math.sqrt(2)
    u, v = (o["x"] + o["y"]) / CELL, (o["x"] - o["y"]) / CELL
    ext, ex, ey, _ = things.get(o["type"], ("CIRCLE", 10, 0, ""))
    hu, hv = (ex / 2 / K, ey / 2 / K) if ext == "BOX" else (ex / K, ex / K)
    out = set()
    for (i, j) in sq:
        ou = min(u + hu, 2 * i + 3) - max(u - hu, 2 * i + 1)
        ov = min(v + hv, 2 * j + 1) - max(v - hv, 2 * j - 1)
        if ou >= least and ov >= least: out.add((i, j))
    return out, (u, v)


def _nearest_square(sq, u, v):
    return min(sq, key=lambda s: ((2 * s[0] + 2 - u) ** 2 + (2 * s[1] - v) ** 2, s)) if sq else None


def zone_material(rng, fam, main, have=None):
    """The second floor Westwood lays for a purpose on `main`: the room's own second floor when it has one, else
    what Westwood lays under that family on that main floor (shells.json focal_pairs), else under the family on any
    floor, else what it lays with `main`; never one it keeps apart from `main` or from the town's grass."""
    def fine(m):
        return bool(m) and m != main and frozenset((m, main)) not in _never() and not ground_shy(m) \
            and not any(x in m for x in NOT_SECOND)
    if have and fine(have): return have
    fp = (stats().get("focal_pairs") or {}).get(fam) or {}
    anywhere = {}
    for d in fp.values():
        for k, v in d.items(): anywhere[k] = anywhere.get(k, 0) + v
    pools = [fp.get(main) or {}, anywhere, stats().get("floor_pairs", {}).get(main) or {}]
    if fam == "throne" and not main.startswith(CULTURE_FLOORS):
        # Westwood's one dais floor is the Land of the Dead's: elsewhere a marble Westwood lays beside the floor
        # (GalavaBrownMarble beside the Galava bricks)
        pools.insert(1, {k: 1 for pr, r in _blend_rules().items() if main in pr and r.get("edge_share_sp") is not None
                         for k in pr if k != main and floor_family(k) == "marble"})
    for pool in pools:
        pool = {k: v for k, v in pool.items() if fine(k) and (fam == "tomb" or not any(d in k for d in DIRTY))}
        if pool: return _draw(rng, pool)
    return None


def lay_zones(spec, room, objs, kind=None):
    """After furnishing: the second floor laid where Westwood lays it under a room's pieces (FOCAL_TYPES): a plinth
    under each tomb, a hearthstone under the fireplace, the throne's dais, the floor under the bar. Each at its
    family's rate (shells.json focal_rate), from the room's own generator; on the room's main floor only (never on a
    carpet, a threshold or a carpet's trim), three cells clear of every door, never beside a floor Westwood keeps from
    it. Returns {tile: material} laid."""
    if not ENABLED or not room or not getattr(room, "tiles", None) or not hasattr(spec, "floor"): return {}
    import random, zlib
    main = room.floor
    rng = random.Random(zlib.crc32(f"zones:{room.id}".encode()))
    things = _things()
    sq = {((x + y) // 2, (x - y) // 2) for (x, y) in room.tiles}
    tile = lambda s: (s[0] + s[1], s[0] - s[1])
    ring = {s for s in sq if any((s[0] + a, s[1] + b) not in sq for a in (-1, 0, 1) for b in (-1, 0, 1))}
    gaps = [d.gap for d in (getattr(room, "doors", None) or ())]
    floor = spec.floor
    local = getattr(spec, "local_blend", {}) or {}
    have = next((m for t in sorted(room.tiles) for m in [floor.get(t)] if m and m != main and not m.startswith("Rug")),
                None)
    by_fam = {}
    for o in objs or ():
        f = focal_family(o.get("type"))
        if f and "x" in o: by_fam.setdefault(f, []).append(o)
    rates = stats().get("focal_rate") or {}
    want = {}                                          # square -> family
    for fam in sorted(by_fam):
        if rng.random() >= rates.get(fam, FOCAL_RATE[fam]): continue
        os_ = by_fam[fam]
        if fam == "tomb":                              # a plinth under each tomb (a band under a row of them)
            for o in os_:
                for s in _squares_under(o, sq, things)[0]: want[s] = fam
        elif fam == "hearth":                          # 1-3 squares along the wall at the fireplace
            for o in os_[:2]:
                under, (u, v) = _squares_under(o, sq, things, least=0.3)
                s0 = _nearest_square(under or sq, u, v)
                if s0 is None: continue
                # the fireplace stands on the ring (Westwood's in the wall line): its hearthstone is the square before
                # it, where Westwood's lies, with the square under it, and one along the wall more often than not
                pad = {s0}
                key = lambda s: ((2 * s[0] + 2 - u) ** 2 + (2 * s[1] - v) ** 2, s)
                inward = sorted((s for s in sq - ring if abs(s[0] - s0[0]) + abs(s[1] - s0[1]) == 1), key=key)
                if inward: pad.add(inward[0])
                if rng.random() < 0.6:
                    d = (inward[0][0] - s0[0], inward[0][1] - s0[1]) if inward else (0, 0)
                    side = sorted((s for s in sq if abs(s[0] - s0[0]) + abs(s[1] - s0[1]) == 1 and s not in pad
                                   and (s[0] - s0[0], s[1] - s0[1]) != (-d[0], -d[1])), key=key)[:1]
                    for s in side:
                        pad.add(s)
                        if inward and (s[0] + d[0], s[1] + d[1]) in sq: pad.add((s[0] + d[0], s[1] + d[1]))
                for s in pad: want[s] = fam
        else:                                          # the throne's dais, the floor under the bar: one square round
            under = set()
            for o in os_: under |= _squares_under(o, sq, things, least=0.3)[0]
            if not under:
                o = os_[0]
                s0 = _nearest_square(sq, (o["x"] + o["y"]) / 23.0, (o["x"] - o["y"]) / 23.0)
                under = {s0} if s0 else set()
            for s in {(a + x, b + y) for a, b in under for x in (-1, 0, 1) for y in (-1, 0, 1)} & sq: want[s] = fam
    if not want: return {}
    mats = {fam: zone_material(rng, fam, main, have) for fam in sorted(set(want.values()))}
    out = {}
    for s, fam in sorted(want.items()):
        t, mat = tile(s), mats.get(fam)
        if not mat or floor.get(t, main) != main or t in local: continue
        if any(max(abs(t[0] - g[0]), abs(t[1] - g[1])) <= 3 for g in gaps): continue
        # never beside a floor Westwood keeps from it (a carpet, the next room's floor through a wall)
        if any(frozenset((mat, floor.get((t[0] + a, t[1] + b)))) in _never()
               for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2) if floor.get((t[0] + a, t[1] + b))): continue
        out[t] = mat
    # a zone too broken by the doors and carpets to read as one is left out
    if len(out) < max(1, 0.5 * len(want)): return {}
    for t, mat in out.items(): spec.tile(*t, mat)
    blend_pattern(spec, {t: floor.get(t, main) for t in room.tiles}, gaps)
    return out


def carpet_target(kind, typed):
    """Where a room's carpet goes (Westwood's rooms are shaped round it): before the bed in a bedroom (23 of
    Westwood's 46 rooms with a bed have their carpet at it), else under the seating and the tables, else before the
    hearth. typed: the furnisher's [(type, (u, v, hu, hv, blocking, layer))]. Returns a uv point or None."""
    import re
    seats = [(r[0], r[1]) for t, r in typed if re.search(r"Table|Chair|Bench|Stool", t) and r[5] != "wall"]
    beds = [(r[0], r[1]) for t, r in typed if re.search(r"^(Bed\d|WoodBed|Cot\d)", t)]
    hearth = [(r[0], r[1]) for t, r in typed if re.search(r"Fireplace|^Stove", t)]
    if _type_of(kind) in ("bedroom", "solar") and beds: return beds[0]
    if len(seats) >= 2: return sum(u for u, _ in seats) / len(seats), sum(v for _, v in seats) / len(seats)
    if beds: return beds[0]
    if hearth: return hearth[0]
    return None


def carpet_offset(rng, kind, typed, box, size):
    """Where in a room's inner squares (box: i0, i1, j0, j1) a carpet of size (ci, cj) squares lies, as offsets from
    the box's corner: its centre nearest carpet_target (before the bed, under the seating), a square either way at
    random; else the middle, a square either way (furnish.lay_carpet)."""
    i0, i1, j0, j1 = box
    ci, cj = size
    si, sj = i1 - i0 + 1 - ci, j1 - j0 + 1 - cj
    jit = lambda: rng.choice((-1, 0, 0, 1))
    tgt = carpet_target(kind, typed)
    if tgt is None:
        return max(0, min(si, si // 2 + jit())), max(0, min(sj, sj // 2 + jit()))
    cu, cv = 2 * (i0 + i1) / 2 + 2, 2 * (j0 + j1) / 2           # the box's centre in uv
    tu, tv = tgt
    if _type_of(kind) in ("bedroom", "solar") and any(t.startswith(("Bed", "WoodBed", "Cot")) for t, _ in typed):
        tu, tv = tu + 0.35 * (cu - tu), tv + 0.35 * (cv - tv)    # the bed's foot: toward the room's middle
    # the offsets putting the carpet's centre (uv 2 (i0 + oi) + ci + 1, 2 (j0 + oj) + cj - 1) on the target
    oi = round((tu - ci - 1) / 2 - i0) + (jit() if rng.random() < 0.3 else 0)
    oj = round((tv - cj + 1) / 2 - j0) + (jit() if rng.random() < 0.3 else 0)
    return max(0, min(si, oi)), max(0, min(sj, oj))
