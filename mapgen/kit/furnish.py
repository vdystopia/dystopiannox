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
    "mine": r"^(LOTD|Ogre|Urchin|DunMir|Crypt|Lich|Horrendous|Galava|Teepee|Sewer|Torture|Coffin|Tomb)|Immobile$|Fallen|Broken|Movable|Shadow$|Empty|HalfFull",
    "lotd": r"^(Ogre|Urchin|DunMir|Mine|Teepee|Galava)|Immobile$|Fallen|Movable|Shadow$",
    "ogre": r"^(LOTD|Urchin|DunMir|Crypt|Lich|Galava|Teepee)|Immobile$|Movable|Shadow$",
}
# Damaging flame objects (they hurt players; rules: lighting.visible_sources) are never used indoors.
DANGEROUS = re.compile(r"Flame(?!Basin)")
# The walls the camera looks at across a room (NW and NE): Westwood stands most wall pieces there
# (fireplaces 87%, beds 79%, chests 74%, stoves 77%).
BACK_SIDES = ("/|BR", "\\|BL")
# Houses are lit with candelabras and hearths, never open torches. Westwood's log cabins: 15 of 30 lights are
# candelabras and 5 are fireplaces; stucco houses: 28 of 46 candelabras. Torches belong to dungeons and mines
# (DungeonStone rooms hold 140 of their 199 lights). The TreePlace playtest found torch flames indoors
# unrealistic, and standing torches by a wall do not look mounted on it.
HOUSE_WALLS = re.compile(r"^(Log|Stucco|Brick|StoneGray|StoneBlue|Galava|Cobblestone|FieldStone|Dilapidated)")
STONE_WALLS = re.compile(r"^(Brick|StoneGray|StoneBlue|Galava|Cobblestone|FieldStone)")
HOUSE_LIGHTS = {"wood": {"Candleabra1": 3, "Candleabra2": 1}, "stone": {"Candleabra3": 3, "Candleabra5": 2, "Candleabra1": 1}}
# Families numbered by wall in a third way, measured on Westwood's maps: log shelves 3 stand on the NW wall
# (36 of 47 uses), 4 on the NE wall (44 of 54), 2 on the SE wall (11 of 16) and 1 on the SW wall (3 of 4).
NUMBERING_OVERRIDES = {"LogShelvesFull": {"1": "\\|TR", "2": "/|TL", "3": "/|BR", "4": "\\|BL"},
                       "LogShelvesEmpty": {"1": "\\|TR", "2": "/|TL", "3": "/|BR", "4": "\\|BL"}}
# Supplies stocked along a storeroom's or kitchen's walls, in tidy groups: (types, fewest, most pieces in a group).
SUPPLIES = {"shelves": (r"^LogShelvesFull[1-4]$", 1, 2),
            "crates": (r"^(DarkCrate|Crate)[12]$", 1, 2),
            "barrels": (r"^(Barrel|Barrel2|WaterBarrel|PiledBarrels[1-4]|LargeBarrel[12])$", 2, 3),
            "sacks": (r"^SackChest(Large|Medium|Small)[12]$", 2, 3),
            "apples": (r"^TraderAppleCrate$", 1, 2)}
# Pieces that only ever stand against a wall (never free in the room).
WALL_PIECES = {"bed", "storage", "shelves", "fireplace", "stove", "desk", "nightstand", "shop_rack", "counter_shop",
               "forge", "bellows", "wall_decor"}
# Lights in one room stand at least this far apart (uv units, ~50 px).
MIN_LIGHT_GAP = 3.0
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
        self.wall_cells = set(walls)
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
        mats = Counter(walls[c].get("material") for c in near)
        self.wall_material = mats.most_common(1)[0][0] if mats else ""
        self.placed = []          # (u, v, hu, hv, blocking, layer)
        self.zones = []           # (u0, u1, v0, v1): space kept clear in front of a piece (rugs may lie there)
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
        # the piece's own grid cell is never a wall cell (cells are diamonds in uv: a piece close to a wall
        # can stand in the wall's cell between its neighbours, and the game then draws it in the wall)
        if not wall_ok and (math.floor((u + v) / 2), math.floor((u - v) / 2)) in self.wall_cells: return False
        if blocking:
            for du, dv in self.doors:
                if math.hypot(u - du, v - dv) < DOOR_CLEAR + max(hu, hv): return False
            for (u0, u1, v0, v1) in self.zones:          # never in front of another piece
                if u + hu > u0 and u - hu < u1 and v + hv > v0 and v - hv < v1: return False
        for (pu, pv, phu, phv, pb, player) in self.placed:
            if pb != blocking or (player == "wall") != wall_ok:
                continue                 # rugs under furniture and wall hangings above it may overlap
            gap = 0.15
            if abs(u - pu) < hu + phu + gap and abs(v - pv) < hv + phv + gap: return False
        return True

    def zone_blocked(self, z):
        """True if a blocking floor piece already stands in zone z."""
        u0, u1, v0, v1 = z
        return any(p[4] and p[5] != "wall" and p[0] + p[2] > u0 and p[0] - p[2] < u1 and p[1] + p[3] > v0 and p[1] - p[3] < v1
                   for p in self.placed)

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
        self.anchors = []         # (u, v) of the pieces composed so far (to spread the next ones)
        self._placed_of = {}      # id(object) -> its footprint record in g.placed
        self.wall_used = []       # ((line, coord), a0, a1): wall stretches pieces already stand against

    # ---- helpers -----------------------------------------------------------------------
    def half(self, t):
        ext, ex, ey, _ = self.things.get(t, ("CIRCLE", 10, 0, ""))
        if ext == "BOX": return ex / 2 / K, ey / 2 / K
        return ex / K, ex / K

    def ok_type(self, t):
        return t in self.things and not self.exclude.search(t) and not DANGEROUS.search(t)

    def put(self, t, u, v, blocking=True, layer="floor", **extra):
        hu, hv = self.half(t)
        rec = (u, v, hu, hv, blocking, layer)
        self.g.placed.append(rec)
        if blocking and not self.placing_light: self.n_blocking += 1
        x, y = _px(u, v)
        o = self.spec.obj_px(t, x, y, **extra)
        self.objects.append(o)
        self._placed_of[id(o)] = rec
        return o

    def _remove(self, o):
        """Takes a placed piece out again (part of a group that could not be completed)."""
        rec = self._placed_of.pop(id(o), None)
        if rec is not None:
            for k in range(len(self.g.placed) - 1, -1, -1):
                if self.g.placed[k] is rec: del self.g.placed[k]; break
            if rec[4] and not self.placing_light: self.n_blocking -= 1
        for seq in (self.objects, self.spec.d["objects"]):
            for k in range(len(seq) - 1, -1, -1):
                if seq[k] is o: del seq[k]; break

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
        prefer = ROOM_IDENTITY.get(self.kind, {}).get("prefer", {}).get(fam)
        if prefer:                                       # the identity's own choice (a kitchen table with food)
            chosen = {t: w for t, w in prefer.items() if ok(t)}
            if chosen: return chosen
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
                t = self.along_variant(t, r["side"])
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

    def seats_around(self, anchor_uv, anchor_t, n, seat_fam="chair", base=None):
        """Seats facing a table or desk. A long table is seated along its two long sides, spread evenly;
        Westwood seats 75% of the chairs at its rectangular tables there (TreePlace playtest: chairs only at
        the ends looked wrong). A bench takes a whole side. A round or square table is seated all round,
        opposite pairs first. A single seat (a desk's) goes on whichever long side has room. Returns the
        seats placed."""
        types = self.types_of(seat_fam)
        if not types or n <= 0: return 0
        base = base or _base(_pick(self.rng, types))
        facing = self.chair_facing.get(base, {})
        ahu, ahv = self.half(anchor_t)
        au, av = anchor_uv
        sides = []                                  # (direction from the table to its seats, offsets along it)
        if abs(ahu - ahv) >= 0.3:                   # a long table: its two long sides
            across = "v" if ahu > ahv else "u"
            hl = max(ahu, ahv)
            first, second = self.rng.sample(["+" + across, "-" + across], 2)
            if n == 1:
                sides = [(first, [0.0]), (second, [0.0])]
            else:
                m1 = 1 if seat_fam == "bench" and hl < 2.4 else (n + 1) // 2
                m2 = 1 if seat_fam == "bench" and hl < 2.4 else n // 2
                spread = lambda m: [0.0] if m == 1 else [-hl * 0.55 + 1.1 * hl * k / (m - 1) for k in range(m)]
                sides = [(first, spread(m1)), (second, spread(m2))]
        else:
            ax = self.rng.sample(["u", "v"], 2)
            sides = [(d, [0.0]) for d in ("+" + ax[0], "-" + ax[0], "+" + ax[1], "-" + ax[1])]
        placed = 0
        for d, offs in sides:
            for off in offs:
                if placed >= n: break
                to_table = ("-" if d[0] == "+" else "+") + d[1]
                t = (facing.get(to_table) or {}).get("variant")
                if not t or not self.ok_type(t):
                    t = _pick(self.rng, {k: w for k, w in types.items() if _base(k) == base} or types)
                hu, hv = self.half(t)
                sgn = 1 if d[0] == "+" else -1
                if d[1] == "u":
                    u, v = au + sgn * (ahu + hu + 0.2), av + off
                else:
                    u, v = au + off, av + sgn * (ahv + hv + 0.2)
                if self.try_put(t, u, v): placed += 1
            if n == 1 and placed: break
        return placed

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
        if ROOM_IDENTITY.get(self.kind, {}).get("compose"):
            self.in_required = True                      # the plan is already within the room's density
            self.compose(plan, need)
            self.in_required = False
            self.placing_light = True
            self.add_lights()
            self.placing_light = False
            return self.objects
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

    # ---- composition: one plan for the whole room (kit/identity.py ROOMS[kind]["compose"]) ----------
    def segments(self):
        """Free stretches of every wall: the run minus door openings (with room to pass) and the
        stretches pieces already stand against. [(run, lo, hi)] in the run's along coordinate."""
        out = []
        for r in self.g.runs:
            key = (r["line"], r["coord"])
            free = [(r["lo"] + 0.6, r["hi"] - 0.6)]
            cuts = [(a0 - 0.25, a1 + 0.25) for k, a0, a1 in self.wall_used if k == key]
            for du, dv in self.g.doors:
                perp, along = (du, dv) if r["line"] == "/" else (dv, du)
                if abs(perp - r["coord"]) < 1.6:
                    cuts.append((along - DOOR_CLEAR - 0.6, along + DOOR_CLEAR + 0.6))
            for c0, c1 in cuts:
                nxt = []
                for f0, f1 in free:
                    if c1 <= f0 or c0 >= f1: nxt.append((f0, f1)); continue
                    if c0 > f0: nxt.append((f0, c0))
                    if c1 < f1: nxt.append((c1, f1))
                free = nxt
            out += [(r, f0, f1) for f0, f1 in free if f1 - f0 >= 1.2]
        return out

    # Westwood numbers the wall variants of many pieces by the wall they stand against: Bed, Chest and
    # Nightstand 1-4 = SE, SW, NE, NW wall; Bookcase and Desk 1-4 = NW, NE, SE, SW wall (90-100% of their
    # uses). Chests, bookcases and desks lie along the wall; beds stand with the headboard against it.
    SCHEMES = ({"1": "/|TL", "2": "\\|TR", "3": "\\|BL", "4": "/|BR"},
               {"1": "/|BR", "2": "\\|BL", "3": "/|TL", "4": "\\|TR"})
    _scheme_cache = {}

    def numbering(self, stem):
        """{side: digit} for a numbered family, from Westwood's placements (room_types.type_wall_sides);
        None when the family is not numbered by wall side."""
        if stem in self._scheme_cache: return self._scheme_cache[stem]
        if stem in NUMBERING_OVERRIDES:
            self._scheme_cache[stem] = {side: d for d, side in NUMBERING_OVERRIDES[stem].items()}
            return self._scheme_cache[stem]
        tws = _RT.get("type_wall_sides", {})
        votes = [0, 0]
        for d in "1234":
            rec = tws.get(f"{stem}{d}")
            if not rec or rec.get("n", 0) < 2: continue
            side = max((k for k in rec if k != "n"), key=lambda k: rec[k])
            if rec[side] < 0.6: continue
            for k, sch in enumerate(self.SCHEMES):
                votes[k] += sch[d] == side
        best = None
        if max(votes) >= 2 and min(votes) == 0:
            sch = self.SCHEMES[votes.index(max(votes))]
            best = {side: d for d, side in sch.items()}
        self._scheme_cache[stem] = best
        return best

    def along_variant(self, t, side):
        """The variant of t for a wall on `side`: the numbered sibling for that wall when the family is
        numbered by wall side; else t when it lies the right way (long side along the wall; a bed's
        across it), else a sibling that does. None when no variant fits."""
        if not t: return t
        m = re.fullmatch(r"(.*?)(\d)([A-Za-z]*)", t)
        if m:
            stem, d, tail = m.groups()
            num = self.numbering(stem)
            if num:
                want = num[side]
                for cand in (f"{stem}{want}{tail}", f"{stem}{want}"):
                    if self.ok_type(cand): return cand
                return None
        line = side.split("|")[0]
        hu, hv = self.half(t)
        if abs(hu - hv) < 0.05: return t
        along = _family_of(t) != "bed"
        fits = lambda x: self._along_wall(x, line) == along
        if fits(t): return t
        if not m: return None
        stem, _, tail = m.groups()
        sibs = [f"{stem}{d}{tail}" for d in "123456" if self.ok_type(f"{stem}{d}{tail}") and fits(f"{stem}{d}{tail}")]
        return sibs[0] if sibs else None

    def side_variant(self, t0, r, fam=None):
        """The variant of t0 for wall run r: Westwood's own variant for that wall side when there is a
        rule; else, among the room identity's preferred types (a lit hearth, never an unlit sibling),
        one whose long side runs along the wall; else orient()."""
        base = _base(t0)
        if base in self.dirvar and self.dirvar[base].get("use_variant_for_wall_side"):
            return self.along_variant(self.variant_for_side(base, r["side"]), r["side"])
        pref = ROOM_IDENTITY.get(self.kind, {}).get("prefer", {}).get(fam) if fam else None
        if pref:
            along = [t for t in pref if self.ok_type(t) and self._along_wall(t, r["line"])]
            if along:                     # and the numbered sibling for this wall (Desk4 is the NE wall's desk)
                return self.along_variant(t0 if t0 in along else self.rng.choice(along), r["side"])
        return self.along_variant(self.orient(t0, r["side"]), r["side"])

    def _along_wall(self, t, line):
        hu, hv = self.half(t)
        return abs(hu - hv) < 0.05 or (hv >= hu) == (line == "/")

    def wall_candidates(self, fam, t0, at):
        """Positions for a piece against a wall, best first: a back wall, away from the pieces already
        composed (one anchor per wall where the room allows), centred on its free stretch (at="center")
        or toward an end of it (at="corner")."""
        inv = self.T["inventory"].get(fam, {})
        out = []
        for r, lo, hi in self.segments():
            t = self.side_variant(t0, r, fam)
            if not t: continue
            hu, hv = self.half(t)
            ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)      # half-length along the wall / into the room
            if hi - lo < 2 * ha + 0.1: continue
            d = self.perp_for(t, inv.get("perp_px"))
            if fam != "wall_decor": d = max(d, hp + 0.3)
            coord = r["coord"] + r["sign"] * d
            mid = (lo + hi) / 2
            ends = [lo + ha + 0.1, hi - ha - 0.1]
            spots = [mid] if at == "center" else ends if at == "corner" else [mid] + ends
            for a in spots:
                u, v = (coord, a) if r["line"] == "/" else (a, coord)
                spacing = min([math.hypot(u - au, v - av) for au, av in self.anchors] or [8.0])
                score = (3.0 if r["side"] in BACK_SIDES else 0.0) + 2.0 * min(spacing, 8.0) / 8.0 \
                    + 0.05 * (hi - lo) + self.rng.uniform(0, 0.4)
                if at != "corner": score += 1.0 - abs(a - mid) / max(1.0, (hi - lo) / 2)
                out.append((score, t, r, u, v, a, ha, hp))
        out.sort(key=lambda c: -c[0])
        return out

    @staticmethod
    def front_zone(r, u, v, ha, hp, clear):
        s = r["sign"]
        if r["line"] == "/":
            f0, f1 = u + s * hp, u + s * (hp + clear)
            return (min(f0, f1), max(f0, f1), v - ha, v + ha)
        f0, f1 = v + s * hp, v + s * (hp + clear)
        return (u - ha, u + ha, min(f0, f1), max(f0, f1))

    def place_on_wall(self, fam, at="center", clear=1.6, t0=None):
        """One piece against a wall at the best composed position, with `clear` uv units kept free in
        front of it (nothing blocking may stand there later; it must be free now)."""
        t0 = t0 or _pick(self.rng, self.types_of(fam))
        if not t0: return None
        for score, t, r, u, v, a, ha, hp in self.wall_candidates(fam, t0, at):
            zone = self.front_zone(r, u, v, ha, hp, clear) if clear else None
            if zone and self.g.zone_blocked(zone): continue
            o = self.try_put(t, u, v, blocking=fam not in NON_BLOCKING)
            if not o: continue
            if zone: self.g.zones.append(zone)
            self.anchors.append((u, v))
            self.wall_used.append(((r["line"], r["coord"]), a - ha, a + ha))
            return dict(obj=o, run=r, uv=(u, v), along=a, ha=ha, hp=hp)
        return None

    def rug_before(self, p):
        """A rug laid out before a piece (a chest, a hearth), its long side along the wall."""
        t0 = _pick(self.rng, self.types_of("rug"))
        if not t0: return False
        r = p["run"]
        t = self.orient(t0, r["side"]) or t0
        rhu, rhv = self.half(t)
        rp = rhu if r["line"] == "/" else rhv
        u, v = p["uv"]
        off = p["hp"] + rp + 0.2
        uu, vv = (u + r["sign"] * off, v) if r["line"] == "/" else (u, v + r["sign"] * off)
        return bool(self.try_put(t, uu, vv, blocking=False))

    def free_middle(self, hu, hv):
        """The open spot of the room farthest from walls and from what already stands there."""
        cu, cv = self.g.centroid
        blocks = [p for p in self.g.placed if p[4] and p[5] != "wall"]
        best = None
        for (x, y) in self.g.cells:
            u, v = x + y + 1.0, x - y
            if not self.g.fits(u, v, hu, hv): continue
            room = min([self.g.wall_dist(u, v) - max(hu, hv)] +
                       [max(abs(u - b[0]) - b[2] - hu, abs(v - b[1]) - b[3] - hv) for b in blocks])
            score = min(room, 3.0) - 0.25 * math.hypot(u - cu, v - cv)
            if best is None or score > best[0]: best = (score, u, v)
        return best and best[1:]

    def place_center(self, fam):
        t = _pick(self.rng, self.types_of(fam))
        if not t: return None
        hu, hv = self.half(t)
        pad = 1.4 if fam in ("table", "desk") else 0.0   # room around a table for its seats
        spot = self.free_middle(hu + pad, hv + pad) or self.free_middle(hu, hv)
        if not spot: return None
        o = self.try_put(t, *spot, blocking=fam not in NON_BLOCKING)
        if not o: return None
        self.anchors.append(spot)
        return o, spot

    def storage_row(self, fam, at, n):
        """A tight row of supplies (barrels, crates, sacks) along a wall from its corner."""
        p = self.place_on_wall(fam, at, clear=0)
        if not p: return 0
        r, (u, v), a, ha = p["run"], p["uv"], p["along"], p["ha"]
        direction = 1 if a < (r["lo"] + r["hi"]) / 2 else -1
        types = self.types_of(fam)
        placed = 1
        edge = a + direction * ha                      # the row grows from the first piece's far side
        for k in range(1, n):
            t = _pick(self.rng, types) if self.rng.random() < 0.4 else p["obj"]["type"]
            hu, hv = self.half(t)
            ta, tp = (hv, hu) if r["line"] == "/" else (hu, hv)
            aa = edge + direction * (ta + 0.12)
            d = max(self.perp_for(t, self.T["inventory"].get(fam, {}).get("perp_px")), tp + 0.3)
            coord = r["coord"] + r["sign"] * d
            uu, vv = (coord, aa) if r["line"] == "/" else (aa, coord)
            if not self.try_put(t, uu, vv): break
            placed += 1
            edge = aa + direction * ta
            self.wall_used.append(((r["line"], r["coord"]), aa - ta, aa + ta))
        return placed

    def place_beside(self, fam, p, gap=0.25, clear=0.0):
        """One piece of `fam` against the same wall as placed piece p, right beside it, with `clear` uv
        units kept free in front of it."""
        t0 = _pick(self.rng, self.types_of(fam))
        if not t0: return None
        r = p["run"]
        t = self.side_variant(t0, r, fam) or t0
        hu, hv = self.half(t)
        ta, tp = (hv, hu) if r["line"] == "/" else (hu, hv)
        d = max(self.perp_for(t, self.T["inventory"].get(fam, {}).get("perp_px")), tp + 0.3)
        coord = r["coord"] + r["sign"] * d
        for sgn in self.rng.sample([-1, 1], 2):
            a = p["along"] + sgn * (p["ha"] + ta + gap)
            u, v = (coord, a) if r["line"] == "/" else (a, coord)
            zone = self.front_zone(r, u, v, ta, tp, clear) if clear else None
            if zone and self.g.zone_blocked(zone): continue
            o = self.try_put(t, u, v, blocking=fam not in NON_BLOCKING)
            if o:
                if zone: self.g.zones.append(zone)
                self.wall_used.append(((r["line"], r["coord"]), a - ta, a + ta))
                return dict(obj=o, run=r, uv=(u, v), along=a, ha=ta, hp=tp)
        return None

    def place_before(self, fam, p, gap=2.4):
        """One piece of `fam` standing in front of placed piece p, just past the space kept clear before
        it (the anvil before the forge)."""
        t0 = _pick(self.rng, self.types_of(fam))
        if not t0: return None
        r = p["run"]
        t = self.side_variant(t0, r, fam) or t0
        hu, hv = self.half(t)
        tp = hu if r["line"] == "/" else hv
        off = p["hp"] + gap + tp
        u, v = p["uv"]
        for slide in (0.0, 0.8, -0.8):
            uu, vv = (u + r["sign"] * off, v + slide) if r["line"] == "/" else (u + slide, v + r["sign"] * off)
            o = self.try_put(t, uu, vv, blocking=fam not in NON_BLOCKING)
            if o:
                self.anchors.append((uu, vv))
                return dict(obj=o, run=r, uv=(uu, vv), along=vv if r["line"] == "/" else uu, ha=hv if r["line"] == "/" else hu, hp=tp)
        return None

    def place_decor(self):
        """A hanging (tapestry, trophy) centred on a free stretch of a back wall, where it is seen."""
        t0 = _pick(self.rng, self.types_of("wall_decor"))
        if not t0: return False
        for score, t, r, u, v, a, ha, hp in self.wall_candidates("wall_decor", t0, "center"):
            if r["side"] not in BACK_SIDES: continue
            if self.try_put(t, u, v, blocking=False, wall_ok=True, layer="wall"):
                self.wall_used.append(((r["line"], r["coord"]), a - ha, a + ha))
                return True
        return False

    # Nox draws items at floor level, so food set on a table reads as food dropped on the floor (TreePlace
    # playtest; only 2 of Westwood's 520 food items lie at a table). A meal is shown with a table that
    # carries the food in its own picture (RoundTableWithFood).

    # ---- arrangements: groups laid out as a whole (TreePlace playtest) ---------------------------------------
    @staticmethod
    def _uv_on(r, depth, a):
        """uv of the point `depth` units into the room from wall run r, at `a` along it."""
        c = r["coord"] + r["sign"] * depth
        return (c, a) if r["line"] == "/" else (a, c)

    def _variant_for_wall(self, stem, r, across=False):
        """The variant of a numbered family (Cot, Chest, LogShelvesFull...) for wall run r, lying along the
        wall, or across it with one end against it (a bed's headboard): Westwood's numbered variant for
        that wall when it lies the right way, else the variant Westwood used most on that side."""
        sibs = [s for s in (f"{stem}{d}" for d in "123456") if self.ok_type(s)]
        if not sibs: return None

        def fits(s):
            hu, hv = self.half(s)
            if abs(hu - hv) < 0.05: return True
            return self._along_wall(s, r["line"]) != across
        num = self.numbering(stem)
        if num and f"{stem}{num.get(r['side'])}" in sibs and fits(f"{stem}{num.get(r['side'])}"):
            return f"{stem}{num.get(r['side'])}"
        ok = [s for s in sibs if fits(s)]
        if not ok: return None
        tws = _RT.get("type_wall_sides", {})
        return max(ok, key=lambda s: (tws.get(s) or {}).get(r["side"], 0))

    def bed_row(self, n):
        """Bunks for a crew: up to n beds of one kind side by side along one wall, headboards against it,
        evenly spaced and centred on its free stretch; a chest at each bed's foot and a rug along the row.
        Westwood's rooms with 3 or more beds all use one bed kind, in a straight row 2-4.5 units apart.
        Returns the beds placed."""
        stems = Counter()
        for t, w in self.types_of("bed").items(): stems[re.sub(r"\d+$", "", t)] += w
        if not stems: return []
        stem = _pick(self.rng, dict(stems))
        # the wall that holds the most beds, a back wall first: the walls nearest the camera hide what stands
        # against them (Westwood stands 79% of its beds on the back walls)
        cands = []
        for r, lo, hi in self.segments():
            t = self._variant_for_wall(stem, r, across=True)
            if not t: continue
            ha = self.half(t)[1] if r["line"] == "/" else self.half(t)[0]
            k = min(n, int((hi - lo + 0.6) / (2 * ha + 0.6)))
            if k >= 2: cands.append(((k + 0.01 * (hi - lo)) * (1.6 if r["side"] in BACK_SIDES else 1.0), r, lo, hi, t))
        for _, r, lo, hi, t in sorted(cands, key=lambda c: -c[0]):
            hu, hv = self.half(t)
            ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
            k = min(n, int((hi - lo + 0.6) / (2 * ha + 0.6)))
            pitch = min(4.5, (hi - lo) / k)
            start = (lo + hi) / 2 - pitch * (k - 1) / 2
            beds = []
            for i in range(k):
                a = start + i * pitch
                o = self.try_put(t, *self._uv_on(r, hp + 0.3, a))
                if o: beds.append((o, a))
            if len(beds) < 2:
                for o, _ in beds: self._remove(o)
                continue
            for o, a in beds:
                self.wall_used.append(((r["line"], r["coord"]), a - ha, a + ha))
                self.beds.append((o, r, self._uv_on(r, hp + 0.3, a)))
                self.anchors.append(self._uv_on(r, hp + 0.3, a))
            foot = 2 * hp + 0.3                         # the beds' feet, measured from the wall line
            chests = {t: w for t, w in self.types_of("storage").items() if re.match(r"^Chest\d$", t)}
            ct = self._variant_for_wall("Chest", r) if chests else None
            if ct:
                chu, chv = self.half(ct)
                cp = chu if r["line"] == "/" else chv
                got = [o for o in (self.try_put(ct, *self._uv_on(r, foot + 0.2 + cp, a)) for _, a in beds) if o]
                if len(got) * 2 < len(beds):            # an odd chest here and there reads as clutter
                    for o in got: self._remove(o)
                else:
                    foot += 0.2 + 2 * cp
            rug = _pick(self.rng, {t: w for t, w in self.types_of("rug").items() if t.startswith("RedRug")} or self.types_of("rug"))
            rug = rug and self.orient(rug, r["side"])
            if rug:
                rhu, rhv = self.half(rug)
                rp = rhu if r["line"] == "/" else rhv
                mid = sum(a for _, a in beds) / len(beds)
                self.try_put(rug, *self._uv_on(r, foot + 0.3 + rp, mid), blocking=False)
            return [o for o, _ in beds]
        return []

    def table_rows(self, n, seat="bench"):
        """Dining tables in rows through the open middle of the room, their long sides along the room's
        length, evenly spaced and centred, seated along both long sides: a mess hall (Westwood's dining
        halls set long tables with benches). A table that gets fewer than 2 seats is taken out again.
        Returns the tables placed."""
        us = [x + y + 1 for x, y in self.g.cells]; vs = [x - y for x, y in self.g.cells]
        long_u = (max(us) - min(us)) >= (max(vs) - min(vs))
        rect = {t: w for t, w in self.types_of("table").items() if abs(self.half(t)[0] - self.half(t)[1]) >= 0.3}
        if not rect: return []
        t0 = _pick(self.rng, rect)
        stem = re.sub(r"\d+$", "", t0)
        sibs = [t0] + [s for s in (f"{stem}{d}" for d in "123456") if self.ok_type(s) and s != t0]
        t = next((s for s in sibs if (self.half(s)[0] > self.half(s)[1]) == long_u), None)
        if not t: return []
        hu, hv = self.half(t)
        hl, hs = (hu, hv) if long_u else (hv, hu)
        cell_l = 2 * hl + 1.6                           # a table and the aisle past its end
        cell_w = 2 * hs + 2 * 1.3 + 1.4                 # a table, a seat on each side, an aisle
        inset = 1.3                                     # wall pieces and a walkway along the walls
        span_l = (max(us) - min(us) if long_u else max(vs) - min(vs)) - 2 * inset
        span_w = (max(vs) - min(vs) if long_u else max(us) - min(us)) - 2 * inset
        per_row = max(1, int((span_l + 1.6) / cell_l))
        rows = max(1, int((span_w + 1.4) / cell_w))
        while per_row * rows > n and rows > 1 and per_row * (rows - 1) >= n: rows -= 1
        while per_row * rows > n and per_row > 1: per_row -= 1
        cu, cv = self.g.centroid
        mid_l, mid_w = (cu, cv) if long_u else (cv, cu)
        seat_types = self.types_of(seat)
        seat_base = _base(_pick(self.rng, seat_types)) if seat_types else None   # one seat style for the room
        tables = []
        for i in range(rows):
            w = mid_w + (i - (rows - 1) / 2) * cell_w
            for k in range(per_row):
                ell = mid_l + (k - (per_row - 1) / 2) * cell_l
                uv = (ell, w) if long_u else (w, ell)
                o = self.try_put(t, *uv)
                if not o: continue
                got = self.seats_around(uv, t, 2 if seat == "bench" else 4, seat, base=seat_base)
                if got < 2 and seat == "bench": got += self.seats_around(uv, t, 4 - got, "chair")
                if got < 2:
                    self._remove(o); continue
                self._seated.add((uv, t))
                self.anchors.append(uv)
                tables.append((o, uv))
        return tables

    def stock_walls(self, coverage=0.65, kinds=("shelves", "crates", "barrels", "sacks")):
        """Supplies along the free wall stretches in tidy groups (a shelf of goods, crates side by side,
        barrels, a heap of sacks) with walking room between groups, back walls first, until `coverage` of
        the free wall length holds something. Doors keep their clearance and the middle stays open.
        Returns the pieces placed."""
        segs = sorted(self.segments(), key=lambda s: (s[0]["side"] not in BACK_SIDES, -(s[2] - s[1])))
        total = sum(hi - lo for _, lo, hi in segs) or 1.0
        used, placed, k = 0.0, 0, self.rng.randrange(len(kinds))
        for r, lo, hi in segs:
            a = lo + 0.15
            misses = 0
            while used < coverage * total and a < hi - 0.8 and misses < len(kinds):
                kind = kinds[k % len(kinds)]; k += 1
                pat, n0, n1 = SUPPLIES[kind]
                types = [t for t in self.things if re.match(pat, t) and self.ok_type(t)]
                if not types: misses += 1; continue
                if kind == "shelves":
                    t1 = self._variant_for_wall("LogShelvesFull", r)
                    group = [t1] * self.rng.randint(n0, n1) if t1 else []
                else:
                    group = [self.orient(self.rng.choice(types), r["side"]) for _ in range(self.rng.randint(n0, n1))]
                group = [t for t in group if t]
                got, edge = 0, a
                for t in group:
                    thu, thv = self.half(t)
                    ta, tp = (thv, thu) if r["line"] == "/" else (thu, thv)
                    if edge + 2 * ta > hi: break
                    if self.try_put(t, *self._uv_on(r, tp + 0.3, edge + ta)):
                        self.wall_used.append(((r["line"], r["coord"]), edge, edge + 2 * ta))
                        edge += 2 * ta + 0.12; got += 1
                    else:
                        break
                if got:
                    placed += got; used += edge - a; misses = 0
                    a = edge + self.rng.uniform(0.7, 1.3)
                else:
                    misses += 1; a += 0.5
        return placed

    def compose(self, plan, need):
        """Furnish from the room's composition (kit/identity.py ROOMS[kind]["compose"]): anchors on
        their own wall stretches, a rug before the anchor that calls for it, the table set in the open
        middle, supplies in rows from a corner, hangings on the back walls; then any core piece the
        composition could not fit is placed the old way so the room keeps its identity."""
        done = collections.Counter()
        tables, placed = [], {}
        for st in ROOM_IDENTITY[self.kind]["compose"]:
            fam = st["fam"]
            n = plan.get(fam, 0) - done[fam]
            if n <= 0: continue
            if fam == "rug":                          # a rug no anchor called for: the middle of the room
                t = _pick(self.rng, self.types_of("rug"))
                if t:
                    cu, cv = self.g.centroid
                    spot = (cu, cv) if self.g.fits(cu, cv, *self.half(t), blocking=False) else self.free_middle(*self.half(t))
                    if spot and self.try_put(t, *spot, blocking=False): done["rug"] += 1
                continue
            if st["slot"] == "decor":
                for _ in range(n):
                    if self.place_decor(): done[fam] += 1
                continue
            if st["slot"] == "bed_row":
                beds = self.bed_row(n)
                done[fam] += len(beds)
                if beds: placed[fam] = True
                continue
            if st["slot"] == "table_rows":
                rows = self.table_rows(n, st.get("seat", "bench"))
                done[fam] += len(rows)
                done[st.get("seat", "bench")] += 2 * len(rows)
                continue
            if st["slot"] == "stock":
                done[fam] += self.stock_walls(st.get("coverage", 0.65), st.get("kinds", ("shelves", "crates", "barrels", "sacks")))
                continue
            if st["slot"] == "center":
                for _ in range(n):
                    res = self.place_center(fam)
                    if not res: break
                    o, uv = res
                    if st.get("seats"):                   # a table always has its seats, or it goes
                        want = max(2, plan.get("chair", 0) // max(1, n))
                        if self.seats_around(uv, o["type"], min(4, want), "chair") < 2 and \
                                self.seats_around(uv, o["type"], 2, "chair") < 2:
                            self._remove(o); break
                        self._seated.add((uv, o["type"]))
                    done[fam] += 1
                    tables.append((uv, o["type"]))
                continue
            if st["slot"] == "before":
                if placed.get(st["of"]):
                    q = self.place_before(fam, placed[st["of"]], st.get("gap", 2.4))
                    if q: done[fam] += 1; placed[fam] = q
                continue
            if st.get("beside") and placed.get(st["beside"]):
                q = self.place_beside(fam, placed[st["beside"]], clear=st.get("clear", 0.0))
                if q:
                    done[fam] += 1; placed[fam] = q
                    continue                          # otherwise: a wall spot of its own (below)
            n = min(n, st.get("n", n))
            k = 0
            while k < n:                              # wall pieces
                if st.get("group"):
                    got = self.storage_row(fam, st.get("at", "corner"), min(n - k, self.rng.choice((2, 3))))
                    if not got: break
                    k += got
                    continue
                p = self.place_on_wall(fam, st.get("at", "center"), st.get("clear", 1.6))
                if not p: break
                k += 1
                placed.setdefault(fam, p)
                if fam == "bed": self.beds.append((p["obj"], p["run"], p["uv"]))
                if st.get("rug") and plan.get("rug", 0) > done["rug"] and self.rug_before(p):
                    done["rug"] += 1
                if st.get("seats"): self.seats_around(p["uv"], p["obj"]["type"], 1)   # a desk and its chair
            done[fam] += k
        if plan.get("nightstand") and self.beds:
            self.beside_bed(); done["nightstand"] += 1
        for f, n in need.items():                     # core pieces the composition could not fit
            for _ in range(max(0, n - done[f])):
                if f in SEAT_FAMILIES: break
                roles = ("wall", "corner") if f in WALL_PIECES else ("wall", "corner", "center")
                res = next((x for r_ in roles for x in [self.place_one(f, r_, tries=120)] if x), None)
                if res: done[f] += 1
        return done

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
            # odd offsets from the wall line put the last piece of each run 1 unit from the wall, so the
            # counter meets the wall flush (Westwood's run ends: 1.0-1.3 units from the wall line)
            long_bar = len(self.room.tiles) >= 100
            du = self.rng.choice([7, 9] if long_bar else [5, 7]); dv = self.rng.choice([7, 9] if long_bar else [5, 7])
            # each run is anchored on its own wall line ('/' walls lie on odd u, '' walls on even v), so
            # with odd offsets the last piece always sits 1 unit from the wall
            U = ru["coord"] + su * du; V = rv["coord"] + sv * dv
            pieces = [(corner, U, V)]
            u = U - su * 2                       # u-run back towards the '/' wall
            while (u - ru["coord"]) * su >= 0.9:
                pieces.append((series[urun_side], u, V)); u -= su * 2
            v = V - sv * 2                       # v-run back towards the '\' wall
            while (v - rv["coord"]) * sv >= 0.9:
                pieces.append((series[vrun_side], U, v)); v -= sv * 2
            if len(pieces) < 4: continue
            # the pass-through flap sits mid-run with counter on both sides (Westwood: 2-6 units from
            # the corner, never at an end), on the v-run, the only axis Westwood uses for it
            vrun = [i for i, p in enumerate(pieces) if p[0] == series[vrun_side]]
            if len(vrun) >= 3:
                k = vrun[1]
                pieces[k] = ("BarHingedTop", pieces[k][1], pieces[k][2])
            # the piece that meets a wall is a plain counter (A/B); panel-like variants read as a window
            ends = {max((i for i, p in enumerate(pieces) if p[0] == series[urun_side]), default=-1),
                    max((i for i, p in enumerate(pieces) if p[0] == series[vrun_side]), default=-1)}

            def plain(prefix):
                opts = {f"{prefix}{k}": n for k, n in letters.get(prefix, {"A": 1}).items()
                        if k in "AB" and f"{prefix}{k}" in self.things}
                return _pick(self.rng, opts) or f"{prefix}A"
            typed = [(t if t == "BarHingedTop" else plain(t) if i in ends else pick(t), u, v) for i, (t, u, v) in enumerate(pieces)]
            # pieces meet the walls: test a slightly reduced outline so touching a wall is allowed, but keep
            # every doorway fully clear
            if not all(self.g.fits(u, v, *(max(0.2, h - 0.35) for h in self.half(t))) for t, u, v in typed): continue
            if any(math.hypot(u - du, v - dv) < DOOR_CLEAR + max(self.half(t)) for t, u, v in typed for du, dv in self.g.doors):
                continue
            before = len(self.g.placed)
            # the flap lets the barkeep through: it does not block the way behind the bar
            for t, u, v in typed: self.g.placed.append((u, v, *self.half(t), t != "BarHingedTop", "floor"))
            if not self.g.reachable_ok((U, V, 0.01, 0.01, True, "floor")):
                del self.g.placed[before:]
                continue
            del self.g.placed[before:]
            for t, u, v in typed: self.put(t, u, v, blocking=t != "BarHingedTop")
            inside = (U - su * du / 2, V - sv * dv / 2)
            self.spots.append(dict(role="barkeep", px=_px(*inside)))
            # kegs behind the bar, against the back walls
            kegs = [t for t in ("Barrel", "Barrel2", "LargeBarrel2", "PiledBarrels1") if self.ok_type(t)] or ["Barrel"]
            n_kegs = self.rng.randint(2, 4)
            for k in range(1, 6):
                for (uu, vv) in ((ru["coord"] + su * 1.2, rv["coord"] + sv * (1.4 + 1.5 * k)),
                                 (ru["coord"] + su * (1.4 + 1.5 * k), rv["coord"] + sv * 1.2)):
                    if n_kegs > 0 and abs(uu - ru["coord"]) < du - 1.2 and abs(vv - rv["coord"]) < dv - 1.2:
                        if self.try_put(self.rng.choice(kegs), uu, vv): n_kegs -= 1
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
        n = max(1 if tiles >= 12 else 0, tiles // 40, min(n, max(1, tiles // 12)))
        types = {t: s for t, s in vl.get("types", {}).items()
                 if self.ok_type(t) and _family_of(t) not in ("fireplace", "stove") and not OUTDOOR_LIGHT.search(t)} or {"Candleabra1": 1}
        if HOUSE_WALLS.search(self.g.wall_material or ""):       # a house: candelabras, never torches
            types = {t: s for t, s in HOUSE_LIGHTS["stone" if STONE_WALLS.search(self.g.wall_material) else "wood"].items()
                     if self.ok_type(t)} or types
        # lights balance the room: each goes to the wall spot that is farthest from the lights already
        # placed and from the furniture, preferring corners (with a chest centred on one wall and shelves
        # on the next, the candelabra goes to the empty far corner, not between them)
        lights = []
        t_room = _pick(self.rng, types)                # one style of light per room
        for _ in range(n):
            t = t_room if self.rng.random() < 0.8 else _pick(self.rng, types)
            base = _base(t)
            mounted = bool(base in self.dirvar and self.dirvar[base].get("use_variant_for_wall_side")
                           and not t.startswith("Candleabra"))
            pieces = [(p[0], p[1]) for p in self.g.placed if p[4] and p[5] != "wall"]

            def score(c):
                _, u, v, corner = c
                dl = min([math.hypot(u - a, v - b) for a, b in lights] or [10.0])
                dp = min([math.hypot(u - a, v - b) for a, b in pieces] or [6.0])
                return 2.0 * min(dl, 10.0) / 10.0 + 1.6 * min(dp, 6.0) / 6.0 + (0.5 if corner else 0.0)
            spots = sorted(self._light_spots(t, base, mounted), key=lambda c: -score(c))
            for tv, u, v, _ in spots:
                if lights and min(math.hypot(u - a, v - b) for a, b in lights) < MIN_LIGHT_GAP: continue
                if self.try_put(tv, u, v, blocking=not mounted, wall_ok=mounted, layer="wall" if mounted else "floor"):
                    lights.append((u, v)); break
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

    def _light_spots(self, t, base, mounted):
        """Candidate light positions along the walls: both ends of every wall run (the corners) and
        its middle. Wall-mounted lights use the variant for that wall side."""
        out = []
        for r in self.g.runs:
            if r["hi"] - r["lo"] < 2: continue
            tv = self.variant_for_side(base, r["side"]) if mounted else t
            if not tv: continue
            hu, hv = self.half(tv)
            perp = (hu if r["line"] == "/" else hv) + (0.05 if mounted else 0.45)
            coord = r["coord"] + r["sign"] * perp
            n = max(2, int((r["hi"] - r["lo"] - 2.4) / 2.5) + 1)
            for k in range(n):                          # both ends (the corners) and evenly between
                a = r["lo"] + 1.2 + (r["hi"] - r["lo"] - 2.4) * k / max(1, n - 1)
                out.append((tv,) + ((coord, a) if r["line"] == "/" else (a, coord)) + (k in (0, n - 1),))
        self.rng.shuffle(out)
        return out

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
