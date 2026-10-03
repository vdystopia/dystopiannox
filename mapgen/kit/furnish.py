"""Original room furnishing, generated from rules learned from Westwood's rooms.

    furnish_room(spec, room, kind=None, rng=None, style="town") -> list of placed object dicts

Nothing is copied from a stock room. For the room's type the furnisher samples which furniture
families appear and how many (rules/out/room_types.json), places each piece in a role learned for
that type (against a wall at the learned offset, in a corner, or free-standing), picks the object
variant that matches the wall it stands against (rules/out/decoration.json), composes sets (chairs
facing their table, a nightstand beside the bed, a chair at the desk, storage in small groups),
adds lighting (visible sources plus a ColorLight preset from rules/out/lighting.json), keeps door
areas clear and every part of the room reachable, and returns spots where townsfolk could stand.

Geometry: grid cells for walls, world pixels for objects, rotated coordinates u = x + y, v = x - y
for wall-relative placement (one uv unit = 16.26 px). A '/' wall cell (x, y) lies on the line
u = x + y + 1 and runs along v; a '\\' wall cell lies on v = x - y and runs along u. A room's usable
area is the set of grid cells reached by flood fill from its floor tiles without crossing walls.
"""
import collections, math, random, re
from collections import Counter, deque

from nox import load_rules, CELL
from kit.model import Room
from kit.identity import ROOMS as ROOM_IDENTITY

K = CELL / math.sqrt(2)            # px per uv unit
AGENT = 0.75                       # uv radius kept free for walking (~12 px)
DOOR_CLEAR = 2.4                   # uv radius kept free around each door gap

_RT = _DEC = _LIGHT = _THINGS = None


def _rules():
    global _RT, _DEC, _LIGHT, _THINGS
    if _RT is None:
        _RT = load_rules("room_types")
        _DEC = load_rules("decoration")
        _LIGHT = load_rules("lighting")
        import sqlite3, os
        db = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "corpus", "out", "nox_corpus.db")
        with sqlite3.connect(db) as con:
            _THINGS = {n: (e, ex or 0, ey or 0, cls or "") for n, e, ex, ey, cls in
                       con.execute("SELECT name, ext, ex, ey, class FROM things")}
    return _RT, _DEC, _LIGHT, _THINGS


# Object-name prefixes that belong to other cultures/areas; excluded per style so a town house
# does not get Land-of-the-Dead sconces or ogre stools.
STYLE_EXCLUDE = {
    "town": r"^(LOTD|Ogre|Urchin|DunMir|Crypt|Lich|Horrendous|Mine|Galava|Teepee|Sewer|Pulley|Torture|Coffin|Tomb)|Immobile$|Fallen|Broken|Movable|Shadow$|Empty|HalfFull",
    "dunmir": r"^(LOTD|Ogre|Urchin|Crypt|Lich|Horrendous|Mine|Teepee|Sewer|Pulley|Torture)|Immobile$|Fallen|Broken|Movable|Shadow$",
    "lotd": r"^(Ogre|Urchin|DunMir|Mine|Teepee|Galava)|Immobile$|Fallen|Movable|Shadow$",
    "ogre": r"^(LOTD|Urchin|DunMir|Crypt|Lich|Galava|Teepee)|Immobile$|Movable|Shadow$",
}
# Damaging flame objects (they hurt players; rules: lighting.visible_sources) are never used indoors.
DANGEROUS = re.compile(r"Flame(?!Basin)")
# Street lights stay outdoors.
OUTDOOR_LIGHT = re.compile(r"^TorchPole|^Obelisk|StreetLamp")
# At most this many of a family per room (one-off focal pieces; decorative families that look
# odd when repeated in a small generated room).
CAPS = {"fireplace": 1, "stove": 1, "altar": 1, "throne": 1, "counter_shop": 1, "statue": 2, "column": 4, "smithy": 3,
        "lab": 5, "desk": 2, "shop_rack": 6, "plant": 3, "clutter": 4, "wall_decor": 4, "rug": 2}
# Town-style rooms keep statues and columns for grand rooms only.
GRAND_ROOMS = {"hall", "library", "chapel", "throne_room", "dining_hall"}
# Families placed in each pass; anchors first, sets next, filler last.
ORDER = ["rug", "counter_shop", "counter_bar", "bed", "fireplace", "stove", "smithy", "altar", "throne", "desk",
         "shelves", "shop_rack", "lab", "table", "bench", "chair", "nightstand", "storage", "straw", "statue",
         "column", "plant", "wall_decor", "clutter"]
NON_BLOCKING = {"rug", "wall_decor"}
WALL_ONLY = {"wall_decor", "shelves", "shop_rack", "fireplace"}
SEAT_FAMILIES = {"chair", "bench"}
# Anchors a room of each kind must contain (minimum counts); Westwood's rooms of the kind always have them.
REQUIRED = {"bedroom": {"bed": 1}, "barracks": {"bed": 2}, "kitchen": {"stove": 1}, "tavern": {"counter_bar": 1, "table": 2},
            "shop": {"counter_shop": 1, "shop_rack": 3}, "library": {"shelves": 3}, "study": {"desk": 1, "shelves": 1},
            "smithy": {"smithy": 1}, "laboratory": {"lab": 2}, "dining_hall": {"table": 2}, "living_room": {"table": 1},
            "storeroom": {"storage": 2}, "chapel": {"altar": 1}, "throne_room": {"throne": 1}}
# Families that only appear in a kind's sample because a few Westwood rooms were mixed-use (a tavern with a
# wizard's workbench); generated rooms of that kind leave them out.
VETO = {"tavern": {"lab", "bed"}, "shop": {"bed", "counter_bar"}, "library": {"bed", "stove"},
        "dining_hall": {"bed"}, "study": {"bed"}}
DEFAULT_KIND_BY_SIZE = [(18, "storeroom"), (30, "bedroom"), (55, "living_room"), (90, "dining_hall"), (10 ** 6, "hall")]
_FAMILY = None


def _family_of(t):
    """Furniture family of an object type (same definition as rules/room_types.py)."""
    global _FAMILY
    if _FAMILY is None:
        import importlib.util, os
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "rules", "room_types.py")
        src = open(p, encoding="utf-8").read()
        start = src.index("FAMILIES = [")
        fams = eval(src[start + len("FAMILIES = "):src.index("\n]\n", start) + 2])
        _FAMILY = [(f, re.compile(rx)) for f, rx in fams]
    for f, rx in _FAMILY:
        if rx.search(t): return f
    return None


def _base(t):
    return re.sub(r"(\d+[a-z]?|NE|NW|SE|SW|North|South|East|West|N|S|E|W)$", "", t)


def _uv(px, py):
    return (px + py) / CELL, (px - py) / CELL


def _px(u, v):
    return (u + v) / 2 * CELL, (u - v) / 2 * CELL


def _q(rng, qd, scale=1.0):
    """Sample a value from learned quantiles {p10..p90} by interpolation."""
    if not qd: return None
    pts = sorted((int(k[1:]), v) for k, v in qd.items())
    r = rng.uniform(pts[0][0], pts[-1][0])
    for (p0, v0), (p1, v1) in zip(pts, pts[1:]):
        if p0 <= r <= p1:
            return (v0 + (v1 - v0) * (r - p0) / max(1e-9, p1 - p0)) * scale
    return pts[-1][1] * scale


def _pick(rng, shares, allowed=None):
    items = [(k, v) for k, v in shares.items() if v > 0 and (allowed is None or allowed(k))]
    if not items: return None
    ks, ws = zip(*items)
    return rng.choices(ks, ws)[0]


class _Room:
    """Geometry of one room: usable cells, wall runs, doors, placed footprints."""

    def __init__(self, spec, room):
        self.spec = spec
        walls = spec.wallmap
        # usable cells: flood fill from the floor tiles' visual centres, never crossing wall cells
        seeds = {(x + 1, y + 1) for (x, y) in room.tiles} | {(x, y) for (x, y) in room.tiles}
        xs = [x for x, _ in room.tiles]; ys = [y for _, y in room.tiles]
        lo, hi = (min(xs) - 3, min(ys) - 3), (max(xs) + 4, max(ys) + 4)
        # door openings close the room; double doors open two cells (spec.door_gaps has all of them)
        blocked = set(walls) | {d.gap for d in room.doors} | set(getattr(spec, "door_gaps", ()))
        cells, q = set(), deque(s for s in seeds if s not in blocked)
        while q:
            p = q.popleft()
            if p in cells or p in blocked or not (lo[0] <= p[0] <= hi[0] and lo[1] <= p[1] <= hi[1]): continue
            cells.add(p)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)): q.append((p[0] + d[0], p[1] + d[1]))
        self.cells = cells
        cu = sum(x + y + 1 for x, y in cells) / len(cells); cv = sum(x - y for x, y in cells) / len(cells)
        self.centroid = (cu, cv)
        # wall runs adjacent to the room
        near = {(x + dx, y + dy) for (x, y) in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)} & set(walls)
        runs = {}
        for (x, y) in near:
            for line, nbs in (("/", ((1, -1), (-1, 1))), ("\\", ((1, 1), (-1, -1)))):
                if any((x + a, y + b) in walls for a, b in nbs) or walls[(x, y)].get("facing") in ((0,) if line == "/" else (1,)):
                    coord = x + y + 1 if line == "/" else x - y
                    along = x - y if line == "/" else x + y + 1
                    runs.setdefault((line, coord), []).append(along)
        self.runs = []
        for (line, coord), alongs in runs.items():
            if line == "/": side = "BR" if cu > coord else "TL"
            else: side = "TR" if cv > coord else "BL"
            self.runs.append(dict(line=line, coord=coord, lo=min(alongs) - 1, hi=max(alongs) + 1, side=f"{line}|{side}",
                                  sign=1 if side in ("BR", "TR") else -1))
        self.doors = [(g[0] + g[1] + 1, g[0] - g[1]) for g in (d.gap for d in room.doors)]
        self.placed = []          # (u, v, hu, hv, blocking, layer)
        self.area = len(cells)

    # ---- geometry tests ----------------------------------------------------------------
    def inside(self, u, v):
        """Inside the room: the point's grid cell (or a neighbour, since cells are diamonds in uv and
        leave a saw-tooth strip along straight walls) belongs to the room, and the point is on the
        room's side of every wall line it is close to."""
        x, y = (u + v) / 2, (u - v) / 2
        c = (math.floor(x), math.floor(y))
        if c not in self.cells and not any((c[0] + a, c[1] + b) in self.cells for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            return False
        for r in self.runs:
            a = v if r["line"] == "/" else u
            if r["lo"] - 0.5 <= a <= r["hi"] + 0.5:
                off = (u if r["line"] == "/" else v) - r["coord"]
                if abs(off) < 1.5 and off * r["sign"] < 0: return False
        return True

    def wall_dist(self, u, v):
        best = 99.0
        for r in self.runs:
            a = v if r["line"] == "/" else u
            if r["lo"] - 0.5 <= a <= r["hi"] + 0.5:
                best = min(best, abs((u if r["line"] == "/" else v) - r["coord"]))
        return best

    def fits(self, u, v, hu, hv, blocking=True, wall_ok=False):
        pts = [(u + a * hu, v + b * hv) for a in (-1, 0, 1) for b in (-1, 0, 1)]
        if not all(self.inside(*p) for p in pts): return False
        if not wall_ok and min(self.wall_dist(*p) for p in pts) < 0.25: return False
        if blocking:
            for du, dv in self.doors:
                if math.hypot(u - du, v - dv) < DOOR_CLEAR + max(hu, hv): return False
        for (pu, pv, phu, phv, pb, player) in self.placed:
            if pb != blocking or (player == "wall") != wall_ok:
                continue                 # rugs under furniture and wall hangings above it may overlap
            gap = 0.15
            if abs(u - pu) < hu + phu + gap and abs(v - pv) < hv + phv + gap: return False
        return True

    def reachable_ok(self, extra):
        """True if the room stays walkable: door areas connected and no sizeable area cut off."""
        step = 0.5
        us = [x + y for x, y in self.cells]; vs = [x - y for x, y in self.cells]
        blocks = [p for p in self.placed if p[4]] + [extra]
        grid = {}
        for i in range(int(min(us) / step) - 1, int((max(us) + 2) / step) + 1):
            for j in range(int((min(vs) - 1) / step) - 1, int((max(vs) + 1) / step) + 1):
                u, v = i * step, j * step
                if not self.inside(u, v) or self.wall_dist(u, v) < AGENT * 0.9: continue
                if any(abs(u - b[0]) < b[2] + AGENT and abs(v - b[1]) < b[3] + AGENT for b in blocks): continue
                grid[(i, j)] = True
        if not grid: return False
        starts = [min(grid, key=lambda k: (k[0] * step - du) ** 2 + (k[1] * step - dv) ** 2) for du, dv in self.doors] or [next(iter(grid))]
        seen, q = set(), deque([starts[0]])
        while q:
            k = q.popleft()
            if k in seen or k not in grid: continue
            seen.add(k)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)): q.append((k[0] + d[0], k[1] + d[1]))
        if any(s not in seen for s in starts): return False
        return len(seen) >= 0.9 * len(grid)


class Furnisher:
    def __init__(self, spec, room, kind, rng, style):
        RT, DEC, LIGHT, THINGS = _rules()
        self.spec, self.room, self.rng = spec, room, rng
        self.g = _Room(spec, room)
        self.kind = kind or next(k for lim, k in DEFAULT_KIND_BY_SIZE if self.g.area <= lim)
        self.T = RT["types"][ROOM_IDENTITY.get(self.kind, {}).get("base", self.kind)]
        self.chair_facing = RT["chair_facing"]
        self.dirvar = DEC["directional_variants"]
        self.things = THINGS
        self.exclude = re.compile(STYLE_EXCLUDE.get(style, STYLE_EXCLUDE["town"]))
        self.lighting = LIGHT
        self.objects, self.spots, self.beds = [], [], []
        self.n_blocking, self.cap, self.in_required, self.placing_light = 0, 10 ** 6, False, False
        self.style = style
        self._seated = set()

    # ---- helpers -----------------------------------------------------------------------
    def half(self, t):
        ext, ex, ey, _ = self.things.get(t, ("CIRCLE", 10, 0, ""))
        if ext == "BOX": return ex / 2 / K, ey / 2 / K
        return ex / K, ex / K

    def ok_type(self, t):
        return t in self.things and not self.exclude.search(t) and not DANGEROUS.search(t)

    def put(self, t, u, v, blocking=True, layer="floor", **extra):
        hu, hv = self.half(t)
        self.g.placed.append((u, v, hu, hv, blocking, layer))
        if blocking and not self.placing_light: self.n_blocking += 1
        x, y = _px(u, v)
        o = self.spec.obj_px(t, x, y, **extra)
        self.objects.append(o)
        return o

    def try_put(self, t, u, v, blocking=True, wall_ok=False, layer="floor", **extra):
        # hard cap on furniture (Westwood density for the room kind); essentials and lights are exempt
        if blocking and not self.placing_light and not self.in_required and self.n_blocking >= self.cap:
            return None
        hu, hv = self.half(t)
        if not self.g.fits(u, v, hu, hv, blocking, wall_ok): return None
        if blocking and not self.g.reachable_ok((u, v, hu, hv, True, layer)): return None
        return self.put(t, u, v, blocking, layer, **extra)

    def orient(self, t, side):
        """Variant of `t` for a wall side, for objects without paired directional rules (Bookcase1-4,
        WizardWorkstation3a-d, ...): the sibling Westwood used on that side (room_types.type_wall_sides),
        else the sibling whose long side runs along the wall (a / wall runs along v, the other along u)."""
        if not t: return None
        m = re.fullmatch(r"(.*\d)[a-z]", t)
        if m or t + "b" in self.things: pat = re.escape(m.group(1) if m else t) + r"[a-z]?"     # Foo3a..3d
        else: pat = re.escape(re.sub(r"\d+$", "", t)) + r"\d+"                                # Foo1..4
        sibs = sorted(s for s in self.things if re.fullmatch(pat, s) and self.ok_type(s)) or [t]
        tws = _RT.get("type_wall_sides", {})
        learned = [(tws[s].get(side, 0), s) for s in sibs if s in tws and tws[s]["n"] >= 5]
        best = max(learned, default=(0, None))
        if best[0] >= 0.6: return best[1]
        if learned and t in tws and tws[t]["n"] >= 5 and tws[t].get(side, 0) < 0.2:
            return None                      # Westwood never stood this piece against such a wall
        line = side.split("|")[0]
        hu, hv = self.half(t)
        if abs(hu - hv) < 0.05 or (hv >= hu) == (line == "/"): return t
        fit = [s for s in sibs if abs(self.half(s)[0] - hv) < 0.05 and abs(self.half(s)[1] - hu) < 0.05]
        return self.rng.choice(fit) if fit else None

    def variant_for_side(self, base, side):
        rule = self.dirvar.get(base, {}).get("use_variant_for_wall_side", {}).get(side)
        if rule and self.ok_type(rule["variant"]): return rule["variant"]
        return None

    def perp_for(self, t, fam_perp):
        info = self.dirvar.get(_base(t), {}).get("variants", {}).get(t, {}).get("perpendicular_distance_px")
        lo, hi = ((info or {}).get("p25"), (info or {}).get("p75"))
        if lo is None:
            fp = fam_perp or {}
            lo, hi = fp.get("p25", 12), fp.get("p75", 24)
        return self.rng.uniform(lo, hi) / K

    def types_of(self, fam):
        inv = self.T["inventory"].get(fam, {})
        allow = ROOM_IDENTITY.get(self.kind, {}).get("types", {}).get(fam)
        ok = (lambda t: self.ok_type(t) and re.search(allow, t)) if allow else self.ok_type
        shares = {t: s for t, s in inv.get("object_types", {}).items() if ok(t)}
        if not shares:   # fall back to the same family in any room type
            for d in _RT["types"].values():
                for t, s in d["inventory"].get(fam, {}).get("object_types", {}).items():
                    if ok(t): shares[t] = shares.get(t, 0) + s
        return shares

    def against_wall(self, fam, t_choice=None, side_pref=None, role="wall", tries=40):
        """Place one piece of `fam` against a wall, choosing the variant for the wall side."""
        inv = self.T["inventory"].get(fam, {})
        side_shares = dict(inv.get("wall_sides") or {"/|BR": 0.4, "\\|BL": 0.4, "/|TL": 0.1, "\\|TR": 0.1})
        types = self.types_of(fam)
        for _ in range(tries):
            runs = [r for r in self.g.runs if r["hi"] - r["lo"] >= 2 and (side_pref is None or r["side"] == side_pref)]
            if not runs: return None
            weights = [side_shares.get(r["side"], 0.02) * (r["hi"] - r["lo"]) for r in runs]
            r = self.rng.choices(runs, weights)[0]
            t = t_choice
            if t is None:
                base = _base(_pick(self.rng, types) or "")
                t = self.variant_for_side(base, r["side"]) if base in self.dirvar else self.orient(_pick(self.rng, types), r["side"])
                if t is None:   # this family has no variant for that wall side
                    continue
            hu, hv = self.half(t)
            along_half = hv if r["line"] == "/" else hu
            span = (r["lo"] + along_half + 0.3, r["hi"] - along_half - 0.3)
            if span[0] > span[1]: continue
            d = self.perp_for(t, inv.get("perp_px"))
            perp_half = hu if r["line"] == "/" else hv
            d = max(d, perp_half + 0.3)
            coord = r["coord"] + r["sign"] * d
            if role == "corner":     # slide in from one end of the run until it clears the side wall
                end = self.rng.choice([0, 1])
                cands = [span[end] + (1 - 2 * end) * k * 0.25 for k in range(16)]
            else:
                cands = [self.rng.uniform(*span)]
            for a in cands:
                if not span[0] <= a <= span[1]: break
                u, v = (coord, a) if r["line"] == "/" else (a, coord)
                o = self.try_put(t, u, v, blocking=fam not in NON_BLOCKING, wall_ok=fam == "wall_decor",
                                 layer="wall" if fam == "wall_decor" else "floor")
                if o: return o, r, (u, v)
        return None

    def free_spot(self, fam, t, min_wall=2.4, tries=60):
        for _ in range(tries):
            c = self.rng.choice(sorted(self.g.cells))
            u, v = c[0] + c[1] + self.rng.uniform(0.2, 1.8), c[0] - c[1] + self.rng.uniform(-0.8, 0.8)
            if self.g.wall_dist(u, v) < min_wall: continue
            o = self.try_put(t, u, v, blocking=fam not in NON_BLOCKING)
            if o: return o, (u, v)
        return None

    # ---- composition ---------------------------------------------------------------------
    def scale(self):
        """Room size relative to a typical Westwood room of this kind (no floor: small rooms get less).
        g.area counts grid cells; floor tiles cover every other cell, so tiles = area / 2."""
        return max(0.15, min(4.0, self.g.area / 2 / max(8, (self.T["tiles"] or {}).get("p50", 30))))

    def count(self, fam):
        inv = self.T["inventory"].get(fam)
        if not inv or self.rng.random() > inv["p_present"]: return 0
        n = _q(self.rng, inv.get("count"), self.scale()) or 0
        if n < 1:                                   # a fraction of a piece: present with that probability
            return 1 if self.rng.random() < n else 0
        return min(CAPS.get(fam, 99), int(round(n)))

    def furniture_cap(self):
        """Most furniture pieces this room should hold: the kind's typical Westwood density
        (expected pieces per tile) times the room's area, with 25% headroom."""
        inv = self.T["inventory"]
        expected = sum(v.get("p_present", 0) * ((v.get("count") or {}).get("p50") or 1)
                       for f, v in inv.items() if f not in NON_BLOCKING and f not in VETO.get(self.kind, ()))
        per_tile = expected / max(8, (self.T["tiles"] or {}).get("p50", 30))
        return max(2, int(round(1.25 * per_tile * self.g.area / 2)))

    def seats_around(self, anchor_uv, anchor_t, n, seat_fam="chair"):
        types = self.types_of(seat_fam)
        if not types: return
        base = _base(_pick(self.rng, types))
        facing = self.chair_facing.get(base, {})
        ahu, ahv = self.half(anchor_t)
        dirs = [("+u", (1, 0)), ("-u", (-1, 0)), ("+v", (0, 1)), ("-v", (0, -1))]
        self.rng.shuffle(dirs)
        placed = 0
        for name, (du, dv) in dirs:
            if placed >= n: break
            to_anchor = {"+u": "-u", "-u": "+u", "+v": "-v", "-v": "+v"}[name]
            t = (facing.get(to_anchor) or {}).get("variant")
            if not t or not self.ok_type(t):
                t = _pick(self.rng, types)
            hu, hv = self.half(t)
            dist = (ahu if du else ahv) + (hu if du else hv) + self.rng.uniform(0.15, 0.6)
            u, v = anchor_uv[0] + du * dist, anchor_uv[1] + dv * dist
            if self.try_put(t, u, v): placed += 1

    def storage_group(self, fam, left):
        """A short row of matching chests/crates/barrels along a wall. Returns pieces counted (>= 1)."""
        res = self.against_wall(fam, role=self.rng.choice(["corner", "wall"]))
        if not res: return 1
        o, r, (u, v) = res
        placed = 1
        t = o["type"]
        hu, hv = self.half(t)
        step = 2 * (hv if r["line"] == "/" else hu) + 0.2
        for k in range(1, min(left, self.rng.choice([1, 2, 2, 3]))):
            a = self.rng.choice([-1, 1]) * step * ((k + 1) // 2)
            uu, vv = (u, v + a) if r["line"] == "/" else (u + a, v)
            if self.try_put(t, uu, vv): placed += 1
        return placed

    def place_one(self, fam, role, tries=40):
        """Place one piece of `fam` in `role` (wall / corner / center). Returns (object, uv) or None."""
        if role == "center" and fam not in WALL_ONLY:
            t = _pick(self.rng, self.types_of(fam))
            res = t and self.free_spot(fam, t, tries=tries)
            if not res: return None
            o, uv = res
        else:
            res = self.against_wall(fam, role="corner" if role == "corner" else "wall", tries=tries)
            if not res: return None
            o, r, uv = res
            if fam == "counter_shop": self.counter_spot(res)
            if fam == "bed": self.beds.append(res)
        return o, uv

    def identity_plan(self):
        """Families and counts from the room's identity (kit/identity.py ROOMS): every core family at
        its Westwood count clamped to the identity's range, optional families by their probability,
        nothing else. Returns (plan, need) or None for kinds without an identity."""
        ident = ROOM_IDENTITY.get(self.kind)
        if not ident: return None
        plan, need = {}, {}
        for f, (lo, hi) in ident["core"].items():
            n = self.count(f) or lo
            if f in ident.get("per_tiles", {}):            # big rooms get more (a tavern: a table per 35 tiles)
                n = max(n, int(len(self.room.tiles) / ident["per_tiles"][f]))
            plan[f] = max(lo, min(hi, n)); need[f] = lo
        for f, (p, hi) in ident["optional"].items():
            if self.rng.random() < p:
                plan[f] = max(1, min(hi, self.count(f) or 1))
        return plan, {f: n for f, n in need.items() if n > 0 and (self.types_of(f) or f in ("counter_bar", "chair", "bench"))}

    def furnish(self):
        inv_all = self.T["inventory"]
        ip = self.identity_plan()
        if ip:
            plan, need = ip
        else:
            plan = {f: self.count(f) for f in ORDER if f in inv_all and f not in VETO.get(self.kind, ())}
        if self.style == "town" and self.kind not in GRAND_ROOMS:
            plan["statue"] = plan["column"] = 0
        if not ip:
            need = {f: n for f, n in REQUIRED.get(self.kind, {}).items() if self.types_of(f) or f == "counter_bar"}
        for f, n in need.items():
            n = n if self.g.area >= 30 or n <= 1 else 1
            plan[f] = max(n, plan.get(f, 0))
        # keep the total within Westwood's density for this kind of room: trim the most numerous
        # optional families first, never below what the room kind requires
        cap = self.cap = self.furniture_cap()
        while sum(n for f, n in plan.items() if f not in NON_BLOCKING) > cap:
            trimmable = [f for f, n in plan.items() if f not in NON_BLOCKING and n > need.get(f, 0)]
            if not trimmable: break
            plan[max(trimmable, key=lambda f: plan[f])] -= 1
        tables, done = [], collections.Counter()
        # required anchors first (in ORDER), with more tries and role fallbacks; then everything else
        for phase in ("required", "rest"):
            self.in_required = phase == "required"
            for fam in ORDER:
                n = plan.get(fam, 0) - done[fam]
                if phase == "required": n = min(n, need.get(fam, 0) - done[fam])
                if phase == "rest" and fam in SEAT_FAMILIES and not tables:
                    n = min(n, 2)                     # a room without tables gets at most a couple of loose seats
                if n <= 0:
                    if phase == "rest" and fam in ("table", "desk"): self.seat_tables(tables, plan)
                    continue
                roles = inv_all.get(fam, {}).get("roles") or {"wall": 1}
                for _ in range(n):
                    if fam == "rug":
                        t = _pick(self.rng, self.types_of("rug"))
                        if t: self.free_spot("rug", t, min_wall=2.0)
                        done[fam] += 1; continue
                    if fam in SEAT_FAMILIES and tables:
                        done[fam] += 1; continue      # seats are placed with their tables
                    if fam == "nightstand":
                        self.beside_bed(); done[fam] += 1; continue
                    if fam == "storage":
                        goal = need[fam] if phase == "required" else plan[fam]
                        if done[fam] >= goal: break
                        done[fam] += self.storage_group(fam, goal - done[fam])
                        continue
                    if fam == "counter_bar":
                        self.build_bar(); done[fam] = plan[fam]; break    # one assembled counter per room
                    role = "wall" if fam in WALL_ONLY else _pick(self.rng, roles) or "wall"
                    if phase == "required":
                        fallbacks = [role] + [r_ for r_ in ("wall", "corner", "center") if r_ != role]
                        res = next((x for r_ in fallbacks for x in [self.place_one(fam, r_, tries=120)] if x), None)
                    else:
                        res = self.place_one(fam, role)
                    done[fam] += 1
                    if res and fam in ("table", "desk"):
                        tables.append((res[1], res[0]["type"], fam))
                if phase == "rest" and fam in ("table", "desk"): self.seat_tables(tables, plan)
        self.in_required = False
        self.placing_light = True
        self.add_lights()
        self.placing_light = False
        return self.objects

    def seat_tables(self, tables, plan):
        """Chairs or benches around every table (several, per learned table+seat sets) and desk (one)."""
        for (uv, t, f) in tables:
            if (uv, t) in self._seated: continue
            self._seated.add((uv, t))
            if f == "desk":
                self.seats_around(uv, t, 1)
            else:
                seat = "bench" if plan.get("bench") and self.rng.random() < 0.5 else "chair"
                k = max(1, int(round(_q(self.rng, (_RT["sets"].get(f"table+{seat}") or {}).get("per_anchor"), 1.0) or 2)))
                # the room's identity sets a minimum (a living room's table has 2+ chairs)
                lo = ROOM_IDENTITY.get(self.kind, {}).get("core", {}).get("chair", (0, 0))[0]
                k = max(k, -(-lo // max(1, sum(1 for x in tables if x[2] == "table"))))
                self.seats_around(uv, t, min(4, k), seat)

    def beside_bed(self):
        for (o, r, (u, v)) in self.beds:
            t = self.variant_for_side("Nightstand", r["side"])
            if not t: continue
            bhu, bhv = self.half(o["type"]); nhu, nhv = self.half(t)
            along = (bhv + nhv + 0.25) if r["line"] == "/" else (bhu + nhu + 0.25)
            d = self.perp_for(t, None)
            d = max(d, (nhu if r["line"] == "/" else nhv) + 0.3)
            coord = r["coord"] + r["sign"] * d
            for s in self.rng.sample([-1, 1], 2):
                a = (v if r["line"] == "/" else u) + s * along
                uu, vv = (coord, a) if r["line"] == "/" else (a, coord)
                if self.try_put(t, uu, vv): return

    def build_bar(self):
        """Assemble an L-shaped bar counter enclosing a room corner from BarPiece/BarCorner objects,
        following rules room_types.assemblies.bar_counter (2-unit grid, series per side, corner arms)."""
        A = _RT["assemblies"]["bar_counter"]
        series = A["side_series"]
        letters = A["letters"]
        runs = {r["side"]: r for r in self.g.runs if r["hi"] - r["lo"] >= 6}
        # corner of the room -> (wall sides, inner-corner direction signs, corner piece, u-run side, v-run side)
        corners = [("/|BR", "\\|BL", +1, -1, "BarCorner2", "low_v", "high_u"),   # back corner (top of screen)
                   ("/|BR", "\\|TR", +1, +1, "BarCorner3", "high_v", "high_u"),
                   ("/|TL", "\\|BL", -1, -1, "BarCorner1", "low_v", "low_u"),
                   ("/|TL", "\\|TR", -1, +1, "BarCorner4", "high_v", "low_u")]

        def pick(prefix):
            opts = {f"{prefix}{k}": n for k, n in letters.get(prefix, {"A": 1}).items() if f"{prefix}{k}" in self.things}
            return _pick(self.rng, opts) or f"{prefix}A"

        for (us, vs, su, sv, corner, urun_side, vrun_side) in corners:
            if us not in runs or vs not in runs: continue
            ru, rv = runs[us], runs[vs]          # '/' wall (constant u) and '\' wall (constant v)
            du = self.rng.choice([6, 8]); dv = self.rng.choice([6, 8])
            U = 2 * round((ru["coord"] + su * du) / 2); V = 2 * round((rv["coord"] + sv * dv) / 2)
            pieces = [(corner, U, V)]
            u = U - su * 2                       # u-run back towards the '/' wall
            while (u - ru["coord"]) * su >= 1.4:
                pieces.append((series[urun_side], u, V)); u -= su * 2
            v = V - sv * 2                       # v-run back towards the '\' wall
            while (v - rv["coord"]) * sv >= 1.4:
                pieces.append((series[vrun_side], U, v)); v -= sv * 2
            if len(pieces) < 4: continue
            if self.rng.random() < 0.5 and len([p for p in pieces if p[0] == series[vrun_side]]) >= 2:
                k = next(i for i, p in enumerate(pieces) if p[0] == series[vrun_side])
                pieces[k] = ("BarHingedTop", pieces[k][1], pieces[k][2])   # pass-through flap
            typed = [(t if t == "BarHingedTop" else pick(t), u, v) for t, u, v in pieces]
            if not all(self.g.fits(u, v, *self.half(t)) for t, u, v in typed): continue
            before = len(self.g.placed)
            for t, u, v in typed: self.g.placed.append((u, v, *self.half(t), True, "floor"))
            if not self.g.reachable_ok((U, V, 0.01, 0.01, True, "floor")):
                del self.g.placed[before:]
                continue
            del self.g.placed[before:]
            for t, u, v in typed: self.put(t, u, v)
            inside = (U - su * du / 2, V - sv * dv / 2)
            self.spots.append(dict(role="barkeep", px=_px(*inside)))
            return True
        return False

    def counter_spot(self, res):
        o, r, (u, v) = res
        coord = r["coord"] + r["sign"] * 0.9
        self.spots.append(dict(role="shopkeeper", px=_px(*((coord, v) if r["line"] == "/" else (u, coord)))))

    def add_lights(self):
        vl = self.T.get("visible_lights", {})
        tiles = len(self.room.tiles)
        rate = _q(self.rng, vl.get("per100_tiles")) or 3.0          # learned lights per 100 tiles
        n = int(round(min(rate, 9.0) * tiles / 100 + self.rng.random() * 0.6))
        n = max(1 if tiles >= 12 else 0, min(n, max(1, tiles // 12)))
        types = {t: s for t, s in vl.get("types", {}).items()
                 if self.ok_type(t) and _family_of(t) not in ("fireplace", "stove") and not OUTDOOR_LIGHT.search(t)} or {"Candleabra1": 1}
        for _ in range(n):
            t = _pick(self.rng, types)
            base = _base(t)
            if base in self.dirvar and self.dirvar[base].get("use_variant_for_wall_side") and not t.startswith("Candleabra"):
                self._wall_light(base)                 # wall-mounted: variant must match the wall side
            else:
                res = self.against_wall("light", t_choice=t, role=self.rng.choice(["corner", "wall"]))
                if not res: self.free_spot("light", t, min_wall=1.2)
        cl = self.T.get("colorlights", {})
        if self.rng.random() < max(0.35, cl.get("p_any", 0)):
            presets = [p for p in self.lighting["colorlight"]["presets"]
                       if p["animation"] == "steady" and p["family"] in ("orange", "yellow", "white") and p["intensity_class"] == "full"]
            p = self.rng.choices(presets, [x["weighted_share"] for x in presets])[0]
            cu, cv = self.g.centroid
            for _ in range(20):
                u, v = cu + self.rng.uniform(-2, 2), cv + self.rng.uniform(-2, 2)
                if self.g.inside(u, v):
                    x, y = _px(u, v)
                    self.objects.append(self.spec.obj_px("ColorLight", x, y, xfer=dict(p["xfer"])))
                    break

    def _wall_light(self, base):
        for _ in range(20):
            runs = [r for r in self.g.runs if r["hi"] - r["lo"] >= 2]
            if not runs: return
            r = self.rng.choice(runs)
            t = self.variant_for_side(base, r["side"])
            if not t: continue
            if self.against_wall("light", t_choice=t, side_pref=r["side"]): return


def furnish_room(spec, room: Room, kind=None, rng=None, style="town"):
    """Furnish one room in place. Returns the list of object dicts added to the spec."""
    rng = rng or random.Random(0)
    f = Furnisher(spec, room, kind, rng, style)
    objs = f.furnish()
    room.kind = f.kind
    room.spots = f.spots
    return objs
