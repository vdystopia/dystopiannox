"""Westwood's placement grammar: where a piece may stand relative to the walls, the doors and the other pieces, as
measured on the curated campaign rooms (rules/grammar.py -> rules/out/grammar.json). One module for the two furnishing
engines (the recipe engine, kit/furnish.py, and the motif engine, kit/motifs.py: both call `audit` as their last pass)
and for the checker (validate/checks.py composition.grammar_*: `faults` on a finished map's room).

The independent blind judges' faults, the same whatever the type or engine (review/NIGHTLOG.md, 2026-10-06), and the
rule that answers each:

1. **Lights.** A floor light stands against a wall (Westwood: 86% within 1 unit) and either in a room corner (41% in
   house rooms) or beside the piece it lights (41%: a shelf, a desk, a table, a statue) or flanking a doorway; never
   free in a walkway, on a carpet, at a bed's foot, or in a row along a wall; at most the type's Westwood count.
2. **Floating groups.** A table more than FLOAT units from every wall stands on a carpet or rug, by the hearth or bar,
   or in a row of tables (Westwood's free tables: 90% so anchored); never crowding a bed. A chair is drawn up to a table,
   desk, hearth, counter or workbench (Westwood: 0 of 23 bedroom chairs alone).
3. **Lone pieces.** A barrel, crate, chest or clutter piece with no other piece within LINK stands in the open or on a
   front wall no more often than Westwood's (chests never; supplies 17%): the rest are moved into a group or dropped.
4. **Even spacing.** Three or more pieces along a wall at equal gaps (the coefficient of variation of the gaps under
   EVEN_CV), or three of a kind in an evenly stepped row: Westwood's walls are irregular (median CV 0.78).
5. **Wrong pieces.** Plants only in the types whose Westwood rooms hold them (a gallery: none in 28 bedrooms).
6. **Mirrored stamps.** Two knots of small pieces (or two table sets) of the same kinds in the same shape in one room;
   beds or tombs of mixed kinds.

And from the judges' later sheets (2026-10-06): a table or bench square before the hearth (in the way to the fire); a
bench or column alone in the open; stock heaped in the open floor of a small room; one lone piece of a kind to each
corner; pieces ringing a centre at even distance and angles (four chairs at a table's quarter points); hangings at
even gaps; a face (hearth, stove, shelf, desk, chest) on a front wall, seen from behind.

Round two (night-grammar2, 2026-10-06: what the judges still named on the g3 sheets; rules/out/grammar.json round2):
strings of three single pieces at gaps along a wall (rule "string"); stock, cots, racks and workstations on the front
walls past Westwood's share for the category, and front lights ("front", "light"); desks, racks, fairy jars and shop
counters alone in the open ("lone"); tables with no seats and sets of matching chairs at one distance ("seats"); a
carpet floating in the middle with nothing on it ("carpet"); shops mixing trades ("trade"); a hall's table sets leaving
a stretch of bare floor wider than Westwood's or stamped in a row ("hall"). PROCESS.md has each with its figures.

    faults(view) -> [dict(rule, i, msg)]          # i: the piece's index in view.pieces
    audit(furnisher) -> Counter of fixes          # the engines' last pass (moves, drops)
    view_from_furnisher(f), view_from_map(m, r, C, rtype)
"""
import collections, json, math, os, re
from functools import lru_cache

from kit import objects as OBJ

HERE = os.path.dirname(os.path.abspath(__file__))
GRAMMAR_PATH = os.path.join(os.path.dirname(os.path.dirname(HERE)), "rules", "out", "grammar.json")

WALL_REACH = 1.0       # a piece whose back is within this of a wall line stands against it (as rules/motifs.py)
CORNER_REACH = 1.8     # a light within this of two walls that meet stands in the corner
SERVE = 1.0            # a light within this of a piece (edge to edge) stands beside it (rules/objects.py NEXT_GAP)
DOOR_FLANK = 3.0       # a light against a door's wall within this of the doorway's centre flanks it
LINK = 0.9             # pieces within this (edge to edge) are one group (kit/motifs.py LINK)
FLOAT = 2.0            # a table further than this from every wall stands free (Westwood's house tables: p50 1.6)
ANCHOR_REACH = 3.0     # a free table within this of a hearth, bar or stove is anchored by it
ROW_REACH = 1.6        # tables within this of one another stand in a row (a hall's, a barracks')
SEAT_REACH = 1.5       # a chair within this of what it serves is drawn up to it
BED_FOOT = 1.0         # nothing but a chest or nightstand stands within this of a bed's foot
EVEN_CV = 0.2          # gaps along a wall more regular than this are evenly spaced (Westwood's walls: median 0.78)
EVEN_MIN_GAP = 0.4     # ... when they are real gaps (shelves end to end are a lined wall, not a spaced row)
STEP_TOL = 0.3         # three of a kind whose two steps differ by less than this stand in a stepped row
TWIN_TOL = 0.35        # two knots whose pairwise distances differ by less than this have one shape
MIN_EVIDENCE = 5       # a type needs this many Westwood rooms for its own numbers; else the house numbers
LIGHT_GAP = 3.0        # two floor lights closer than this stand side by side (Westwood's nearest pairs: p10 6 units)
LIGHTS_PER_WALL = 2    # floor lights along one wall (a third makes a row)
CARPET_PAD = 0.9       # a light whose footprint comes within this of a carpet stands on its edge or corner (the
                       # carpet's gold trim is drawn on the ring of squares round it)
RING_TOL = 0.3         # pieces round a centre at radii within this, at even angles, stand in a ring
RING_CV = 0.2
HEARTH_DEPTH = 3.4     # a table or bench square before a hearth within this blocks the way to the fire

NOT_SERVED = {"light", "rug", "hanging"}
SEAT_TARGET = {"table", "desk", "hearth", "counter_bar", "counter_shop", "lab", "throne", "stove", "smithy"}
TABLE_ANCHOR = {"hearth", "counter_bar", "stove", "counter_shop"}
ROUND2 = os.environ.get("NOX_GRAMMAR2", "1") == "1"   # NOX_GRAMMAR2=0: the first round's audit alone (comparisons)
# round two adds desks, racks and workstations (fairy jars); never the shop counter, whose keeper stands behind it
LONE_CATS = ("supply", "chest", "clutter", "column", "bench") + (("desk", "rack", "lab") if ROUND2 else ())   # a column alone in open floor: Westwood never (0 of its columns)
SMALL = {"supply", "chest", "light", "plant", "clutter", "statue", "nightstand", "bones"}
SETS = {"table", "chair", "bench"}                         # a table set: a twin of it is a stamp too
STEPPED = {"supply", "chest", "light", "statue", "clutter", "plant", "table", "bench", "straw", "tomb", "bed"}
CORNER_CATS = {"supply", "chest", "clutter", "rack", "statue", "plant"}     # lights: their own rules (39% in corners)
UNIFY = ("bed", "tomb")
FACED = {"hearth", "stove", "shelf", "desk", "chest", "lab", "counter_shop", "nightstand"}   # drawn facing the camera                                    # one kind of each to a room (Westwood's vaults, dormitories)
BED_OK = {"chest", "nightstand", "rug", "hanging", "bed"}     # what may stand at a bed's foot
# rooms whose lights flank an aisle, a throne, an altar or the dead (Westwood's free-standing lights are theirs)
CEREMONIAL = {"throne_room", "chapel", "hall", "great_hall", "shrine", "mausoleum", "crypt", "ossuary", "gallery"}
# rooms whose tables stand in rows by design
TABLE_ROWS = {"great_hall", "dining_hall", "barracks", "tavern", "library"}
FRONT = {"SE", "SW"}


# ---- the measured numbers -------------------------------------------------------------------------------------------
@lru_cache(None)
def stats():
    try:
        with open(GRAMMAR_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"types": {}, "house": {}}


def _tstat(rtype, key, default=None):
    """A measured number for the type, or the house rooms' when the type has under MIN_EVIDENCE Westwood rooms."""
    s = stats()
    t = s.get("types", {}).get(rtype)
    if t and t.get("rooms", 0) >= MIN_EVIDENCE and key in t: return t[key]
    return s.get("house", {}).get(key, default)


def light_cap(rtype, tiles):
    """The most floor lights a room of the type and size takes: Westwood's p90 lights per 100 tiles for the type (its
    rooms with lights), never under one, never over the knowledge base's cap by size (kit/objects.py light_cap)."""
    rate = _tstat(rtype, "lights_per100_p90", 4.0) or 0.0
    cap_n = _tstat(rtype, "lights_p90", 3)
    n = max(1, int(math.ceil(rate * tiles / 100.0 - 0.25)))
    if cap_n is not None: n = min(n, max(1, int(cap_n) + (1 if tiles >= 100 else 0)))
    return min(n, OBJ.light_cap(tiles))


CARPET_ROOMS = 0.5     # a carpet is laid to anchor a table only in the types Westwood carpets this often


@lru_cache(None)
def carpeted(rtype):
    """The share of Westwood's rooms of the type with a carpet laid in the floor (rules/out/motifs.json stats)."""
    try:
        with open(os.path.join(os.path.dirname(GRAMMAR_PATH), "motifs.json"), encoding="utf-8") as f:
            st = json.load(f).get("stats", {})
    except (OSError, ValueError):
        return 0.0
    return (st.get(rtype) or {}).get("carpeted", 0.0) or 0.0


def lone_budget(cat, rtype, n):
    """How many pieces of a category of n in a room may stand alone in the open or on a front wall: Westwood's share for
    the category (house rooms), rounded down."""
    share = (stats().get("house", {}).get("lone_exposed", {}) or {}).get(cat)
    if share is None: share = {"supply": 0.15, "chest": 0.02, "clutter": 0.15, "column": 0.0, "bench": 0.22, "desk": 0.03,
                               "rack": 0.2, "lab": 0.21, "counter_shop": 0.22}.get(cat, 0.0)
    return int(math.floor(share * n + 1e-9))


def chair_budget(rtype, n):
    share = _tstat(rtype, "lone_chair_share", 0.0) or 0.0
    return int(math.floor(share * n + 1e-9))


def plants_ok(rtype):
    """Whether the type's Westwood rooms hold plants (a type with too few Westwood rooms to say: yes)."""
    t = stats().get("types", {}).get(rtype)
    if not t or t.get("rooms", 0) < MIN_EVIDENCE: return True
    return t.get("plants", 0) > 0


# ---- a room as the rules see it ------------------------------------------------------------------------------------
class View:
    """A furnished room: pieces (dict t, cat, u, v, hu, hv, blocking, hang, and the engine's or map's object as `o`),
    walls (dict name NE/NW/SE/SW, line, coord, lo, hi), doors [(u, v, line)], carpet test, the type and floor tiles."""

    def __init__(self, rtype, tiles, pieces, walls, doors, on_carpet=None):
        self.rtype, self.tiles = rtype, tiles
        self.pieces, self.walls, self.doors = pieces, walls, doors
        self._carpet = on_carpet or (lambda u, v: False)

    def walls_of(self, p, reach=WALL_REACH):
        """[(wall, gap)] of the walls a piece stands against (its edge within reach of the line)."""
        out = []
        for w in self.walls:
            if w["line"] == "/":
                if not (w["lo"] - 0.5 <= p["v"] <= w["hi"] + 0.5): continue
                d = abs(p["u"] - w["coord"]) - p["hu"]
            else:
                if not (w["lo"] - 0.5 <= p["u"] <= w["hi"] + 0.5): continue
                d = abs(p["v"] - w["coord"]) - p["hv"]
            if d <= reach: out.append((w, d))
        return sorted(out, key=lambda x: x[1])

    def wall_dist(self, p):
        best = 99.0
        for w in self.walls:
            a = p["v"] if w["line"] == "/" else p["u"]
            if not (w["lo"] - 0.5 <= a <= w["hi"] + 0.5): continue
            d = abs((p["u"] if w["line"] == "/" else p["v"]) - w["coord"]) - (p["hu"] if w["line"] == "/" else p["hv"])
            best = min(best, d)
        return best

    def on_carpet(self, p):
        if self._carpet(p["u"], p["v"]): return True
        return any(q["cat"] == "rug" and abs(p["u"] - q["u"]) <= q["hu"] and abs(p["v"] - q["v"]) <= q["hv"]
                   for q in self.pieces)

    def near_carpet(self, p, pad=0.6):
        """On a carpet or rug, or its edge within pad of one (a table set beside the carpet it is laid to)."""
        for du in (-pad, 0, pad):
            for dv in (-pad, 0, pad):
                for a in (-1, 0, 1):
                    for b in (-1, 0, 1):
                        if self._carpet(p["u"] + a * p["hu"] + du, p["v"] + b * p["hv"] + dv): return True
        return any(q["cat"] == "rug" and edge(p, q) <= pad for q in self.pieces)

    def floor(self, p):
        return not p.get("hang") and p["cat"] not in ("rug", "hanging")


def edge(a, b):
    """Edge-to-edge gap of two footprints (negative: they overlap)."""
    return max(abs(a["u"] - b["u"]) - a["hu"] - b["hu"], abs(a["v"] - b["v"]) - a["hv"] - b["hv"])


def _others(view, p, skip=NOT_SERVED):
    return [q for q in view.pieces if q is not p and view.floor(q) and q["cat"] not in skip]


# ---- 1. lights -----------------------------------------------------------------------------------------------------
def bed_ends(view, bed):
    """((head u, v), (foot u, v)) of a bed: its long axis, the head the end nearer a wall."""
    if bed["hu"] >= bed["hv"]:
        ends = [(bed["u"] - bed["hu"], bed["v"]), (bed["u"] + bed["hu"], bed["v"])]
    else:
        ends = [(bed["u"], bed["v"] - bed["hv"]), (bed["u"], bed["v"] + bed["hv"])]
    def wd(pt):
        return view.wall_dist(dict(u=pt[0], v=pt[1], hu=0.0, hv=0.0))
    ends.sort(key=wd)
    return ends[0], ends[1]


def at_bed_foot(view, p):
    """Whether p stands within BED_FOOT of a bed and nearer its foot than its head."""
    for b in view.pieces:
        if b["cat"] != "bed" or b is p: continue
        if edge(p, b) > BED_FOOT: continue
        head, foot = bed_ends(view, b)
        if math.hypot(p["u"] - foot[0], p["v"] - foot[1]) < math.hypot(p["u"] - head[0], p["v"] - head[1]) - 0.3:
            return True
    return False


def light_class(view, p):
    """Where a floor light stands: corner, served (by a wall, beside a piece), door (flanking a doorway), served-free,
    wall-alone or free."""
    walls = view.walls_of(p, WALL_REACH)
    near = [q for q in _others(view, p) if edge(p, q) <= SERVE]
    if near: return "served" if walls else "served-free"
    if not walls: return "free"
    lines = {w["line"] for w, _ in view.walls_of(p, CORNER_REACH)}
    if len(lines) == 2: return "corner"
    for du, dv, line in view.doors:
        if math.hypot(p["u"] - du, p["v"] - dv) <= DOOR_FLANK and any(w["line"] == line for w, _ in walls):
            return "door"
    return "wall-alone"


def floor_lights(view):
    return [p for p in view.pieces if p["cat"] == "light" and p.get("blocking") and not p.get("hang")]


def light_faults(view):
    out = []
    lights = floor_lights(view)
    if view.rtype in CEREMONIAL: return out
    for p in lights:
        c = light_class(view, p)
        why = None
        if c in ("free", "served-free"): why = "stands free on the floor, away from every wall"
        elif c == "wall-alone": why = "stands alone along a wall, beside nothing it lights and in no corner"
        elif at_bed_foot(view, p): why = "stands at a bed's foot"
        elif view.on_carpet(p) or view.near_carpet(p, CARPET_PAD): why = "stands on the carpet or at its edge"
        if why: out.append(dict(rule="light", p=p, msg=why))
    flagged = {id(f["p"]) for f in out}
    for i, p in enumerate(lights):
        if id(p) in flagged: continue
        if any(math.hypot(p["u"] - q["u"], p["v"] - q["v"]) < LIGHT_GAP for q in lights[:i] if id(q) not in flagged):
            out.append(dict(rule="light", p=p, msg="stands side by side with another light")); flagged.add(id(p))
    per_wall = collections.defaultdict(list)
    for p in lights:
        if id(p) in flagged: continue
        ws = view.walls_of(p, WALL_REACH)
        if ws: per_wall[(ws[0][0]["line"], ws[0][0]["coord"])].append(p)
    for k, ps in per_wall.items():
        for p in ps[LIGHTS_PER_WALL:]:
            out.append(dict(rule="light", p=p, msg=f"is light number {len(ps)} along one wall: a row"))
            flagged.add(id(p))
    cap = light_cap(view.rtype, view.tiles)
    if len(lights) > cap:
        for p in lights[cap:]:
            if not any(f["p"] is p for f in out):
                out.append(dict(rule="lights", p=p, msg=f"one of {len(lights)} floor lights where Westwood's rooms of the "
                                f"type and size hold {cap}"))
    return out


# ---- 2. groups -----------------------------------------------------------------------------------------------------
def table_state(view, p):
    """wall, carpet, hearth, row or floating."""
    if view.wall_dist(p) <= FLOAT: return "wall"
    if view.near_carpet(p): return "carpet"
    if any(q["cat"] in TABLE_ANCHOR and edge(p, q) <= ANCHOR_REACH for q in view.pieces): return "hearth"
    if view.rtype in TABLE_ROWS and any(q is not p and q["cat"] == "table" and edge(p, q) <= ROW_REACH for q in view.pieces):
        return "row"
    return "floating"


def before_hearth(view, p):
    """Whether p stands square in front of a hearth against a wall, within HEARTH_DEPTH of it."""
    for h in view.pieces:
        if h["cat"] != "hearth" or h is p: continue
        ws = view.walls_of(h, WALL_REACH)
        if not ws: continue
        w = ws[0][0]
        if w["line"] == "/":
            along, ha = abs(p["v"] - h["v"]), h["hv"]
            depth = abs(p["u"] - w["coord"]) - abs(h["u"] - w["coord"]) - h["hu"] - p["hu"]
        else:
            along, ha = abs(p["u"] - h["u"]), h["hu"]
            depth = abs(p["v"] - w["coord"]) - abs(h["v"] - w["coord"]) - h["hv"] - p["hv"]
        if along <= ha * 0.6 and 0 <= depth <= HEARTH_DEPTH: return True
    return False


def seat_target(view, p):
    return min([edge(p, q) for q in view.pieces if q["cat"] in SEAT_TARGET] or [99.0])


def group_faults(view):
    out = []
    for p in view.pieces:
        if p["cat"] == "table":
            st = table_state(view, p)
            if st == "floating":
                out.append(dict(rule="table", p=p, msg=f"stands {view.wall_dist(p):.1f} units out on the open floor, by no "
                                f"wall, carpet or hearth"))
            elif at_bed_foot(view, p):
                out.append(dict(rule="table", p=p, msg="crowds a bed's foot"))
            elif before_hearth(view, p):
                out.append(dict(rule="table", p=p, msg="stands square before the hearth, in the way to the fire"))
    for p in view.pieces:
        if p["cat"] == "bench" and before_hearth(view, p) and not view.walls_of(p, WALL_REACH):
            out.append(dict(rule="table", p=p, msg="stands square before the hearth, in the way to the fire"))
    chairs = [p for p in view.pieces if p["cat"] == "chair"]
    lone = [p for p in chairs if seat_target(view, p) > SEAT_REACH]
    allow = chair_budget(view.rtype, len(chairs))
    for p in lone[allow:]:
        out.append(dict(rule="chair", p=p, msg="is drawn up to nothing (no table, desk or hearth beside it)"))
    for p in chairs:
        if p not in lone and at_bed_foot(view, p):
            out.append(dict(rule="chair", p=p, msg="crowds a bed's foot"))
    return out


# ---- 3. lone pieces ------------------------------------------------------------------------------------------------
def lone_where(view, p):
    """None if p has a neighbour within LINK; else 'open', 'front' or 'back' (where it stands alone)."""
    if any(edge(p, q) <= LINK for q in _others(view, p, skip={"rug", "hanging"})): return None
    if p["cat"] == "column" and any(q is not p and q["cat"] == "column" and edge(p, q) <= 6.0 for q in view.pieces):
        return None                               # columns in a row (a nave's, a throne room's) are not alone
    walls = view.walls_of(p, WALL_REACH)
    if not walls: return "open"
    return "front" if all(w["name"] in FRONT for w, _ in walls) else "back"


OPEN_HEAP_TILES = 60    # stock heaped in the open floor only in stores this big (Westwood's Con07B store)


def open_heaps(view):
    """Knots of stock (barrels, crates, sacks) standing wholly off the walls in a room under OPEN_HEAP_TILES."""
    if view.tiles >= OPEN_HEAP_TILES: return []
    out = []
    for k in knots(view):
        st = [p for p in k if p["cat"] == "supply"]
        if len(st) < 2 or len(st) < len(k) - 1: continue
        if any(view.walls_of(p, WALL_REACH) for p in k): continue
        out.append(st)
    return out


def lone_faults(view):
    out = []
    for k in open_heaps(view):
        for p in k:
            out.append(dict(rule="lone", p=p, msg="stands in a heap of stock out in the open floor"))
    for cat in LONE_CATS:
        ps = [p for p in view.pieces if p["cat"] == cat and view.floor(p)]
        exposed = [p for p in ps if lone_where(view, p) in ("open", "front")]
        allow = lone_budget(cat, view.rtype, len(ps))
        for p in exposed[allow:]:
            where = lone_where(view, p)
            out.append(dict(rule="lone", p=p, msg="stands alone " + ("in the open" if where == "open" else
                                                                      "on a front wall")))
    return out


# ---- 4. even spacing -----------------------------------------------------------------------------------------------
def wall_rows(view):
    """{wall name: [pieces against it, in order along it]} of the standing pieces (lights apart)."""
    by = collections.defaultdict(list)
    for p in view.pieces:
        if not view.floor(p) or not p.get("blocking") or p["cat"] == "light": continue
        ws = view.walls_of(p, WALL_REACH)
        if not ws: continue
        w = ws[0][0]
        by[(w["name"], w["line"], w["coord"])].append(p)
    out = {}
    for (name, line, coord), ps in by.items():
        key = (lambda q: q["v"]) if line == "/" else (lambda q: q["u"])
        out[(name, line, coord)] = sorted(ps, key=key)
    return out


def gaps_along(line, ps):
    a = (lambda q: (q["v"], q["hv"])) if line == "/" else (lambda q: (q["u"], q["hu"]))
    return [a(y)[0] - a(y)[1] - (a(x)[0] + a(x)[1]) for x, y in zip(ps, ps[1:])]


def cv(xs):
    m = sum(xs) / len(xs)
    if m <= 0: return 99.0
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs)) / m


def even_runs(view):
    """[(wall key, pieces, gaps)] of the walls whose pieces stand at even gaps (3+ pieces)."""
    out = []
    for key, ps in wall_rows(view).items():
        if len(ps) < 3: continue
        if len(ps) == 3 and ps[1]["cat"] in ("bed", "desk") and ps[0]["cat"] == ps[2]["cat"]: continue   # a bed's set
        g = gaps_along(key[1], ps)
        # only the stretches of real gaps: a lined run of shelves end to end is one piece of wall
        if min(g) < 0.1 and max(g) < EVEN_MIN_GAP: continue
        if sum(g) / len(g) >= EVEN_MIN_GAP and cv([max(0.0, x) for x in g]) < EVEN_CV:
            out.append((key, ps, g))
    return out


def p_cat(p):
    return p["cat"]


def stepped_rows(view):
    """[pieces] of three of a kind standing in an evenly stepped row off the walls (a diagonal of barrels)."""
    out = []
    kinds = collections.defaultdict(list)
    for p in view.pieces:
        if view.floor(p) and p.get("blocking") and p["cat"] in STEPPED:
            kinds[OBJ.kind(p["t"])].append(p)
    for k, ps in kinds.items():
        if len(ps) < 3: continue
        for a in ps:
            for b in ps:
                if b is a: continue
                du, dv = b["u"] - a["u"], b["v"] - a["v"]
                if math.hypot(du, dv) > 4.0 or math.hypot(du, dv) < 0.5: continue
                if abs(du) < 0.5 or abs(dv) < 0.5:
                    # a straight row in the room's frame reads as a diagonal on screen: one of loose pieces off the
                    # walls (tables in a grid, barrels in a line), never pews, beds, tombs or straw laid in rows
                    if p_cat(a) in ("bench", "bed", "tomb", "straw") or any(view.walls_of(x, WALL_REACH) for x in (a, b)):
                        continue
                for c in ps:
                    if c is a or c is b: continue
                    if abs(c["u"] - b["u"] - du) < STEP_TOL and abs(c["v"] - b["v"] - dv) < STEP_TOL:
                        out.append([a, b, c])
    seen, uniq = set(), []
    for row in out:
        key = frozenset(id(x) for x in row)
        if key not in seen: seen.add(key); uniq.append(row)
    return uniq


def hung_even(view):
    """[(wall key, hangings, gaps)] of 3+ hangings (or mounted lights) along one wall at even gaps."""
    by = collections.defaultdict(list)
    for p in view.pieces:
        if not (p.get("hang") or p["cat"] == "hanging"): continue
        ws = view.walls_of(p, 2.6)
        if ws: by[(ws[0][0]["name"], ws[0][0]["line"], ws[0][0]["coord"])].append(p)
    out = []
    for key, ps in by.items():
        if len(ps) < 3: continue
        ps = sorted(ps, key=(lambda q: q["v"]) if key[1] == "/" else (lambda q: q["u"]))
        g = gaps_along(key[1], ps)
        if sum(g) / len(g) >= EVEN_MIN_GAP and cv([max(0.0, x) for x in g]) < EVEN_CV: out.append((key, ps, g))
    return out


def corner_singles(view):
    """{kind: [pieces]} of one kind standing alone in two or more of the room's corners (one barrel per corner)."""
    by = collections.defaultdict(list)
    for p in view.pieces:
        if not view.floor(p) or p["cat"] not in CORNER_CATS: continue
        if len({w["line"] for w, _ in view.walls_of(p, CORNER_REACH)}) < 2: continue
        if any(edge(p, q) <= LINK for q in _others(view, p, skip={"rug", "hanging", "light"})): continue
        by[OBJ.kind(p["t"])].append(p)
    return {k: ps for k, ps in by.items() if len(ps) >= 2}


RING_CATS = ("chair", "bench", "table", "straw", "supply", "bed", "statue", "light", "tomb")


def rings(view):
    """[(centre, pieces)] of three or more pieces of one kind round a centre piece at one radius and even angles (four
    chairs at a table's quarter points, straw heaps round a fire, tables ringing a fire pit)."""
    out = []
    for c in view.pieces:
        if not view.floor(c) or c["cat"] == "light": continue
        by = collections.defaultdict(list)
        for q in view.pieces:
            if q is c or not view.floor(q) or q["cat"] not in RING_CATS: continue
            d = math.hypot(q["u"] - c["u"], q["v"] - c["v"])
            if d <= max(c["hu"], c["hv"]) + 6.0: by[OBJ.kind(q["t"])].append((d, q))
        for k, dq in by.items():
            if len(dq) < 3: continue
            dq.sort(key=lambda x: x[0])
            for i in range(len(dq) - 2):
                grp = [x for x in dq if abs(x[0] - dq[i][0]) <= RING_TOL]
                if len(grp) < 3: continue
                ang = sorted(math.atan2(q["v"] - c["v"], q["u"] - c["u"]) for _, q in grp)
                gaps = [b - a for a, b in zip(ang, ang[1:])] + [2 * math.pi - (ang[-1] - ang[0])]
                if len(grp) == 3 and max(gaps) > math.pi * 1.05: continue    # three to one side: not a ring
                if cv(gaps) >= RING_CV: continue
                out.append((c, [q for _, q in grp])); break
    return out


def spacing_faults(view):
    out = []
    for key, ps, g in hung_even(view):
        out.append(dict(rule="even", p=ps[len(ps) // 2], msg=f"is one of {len(ps)} hangings along the {key[0]} wall at "
                        f"even gaps"))
    for k, ps in corner_singles(view).items():
        out.append(dict(rule="corners", p=ps[-1], msg=f"is one of {len(ps)} lone {k} standing one to a corner"))
    for c, ps in rings(view):
        out.append(dict(rule="ring", p=ps[-1], msg=f"is one of {len(ps)} {OBJ.kind(ps[0]['t'])} ringing {c['t']} at even "
                        f"distance and angles"))
    for key, ps, g in even_runs(view):
        out.append(dict(rule="even", p=ps[len(ps) // 2], msg=f"is one of {len(ps)} pieces along the {key[0]} wall at even "
                        f"gaps ({', '.join(f'{x:.1f}' for x in g)})"))
    for row in stepped_rows(view):
        out.append(dict(rule="stepped", p=row[1], msg=f"is one of three {OBJ.kind(row[0]['t'])} in an evenly stepped row"))
    return out


# ---- 5. wrong pieces -----------------------------------------------------------------------------------------------
def front_faced(view):
    """Pieces with a face (hearths, stoves, shelves, desks, chests, workbenches) against a front wall only: the camera
    sees their backs (Westwood: stoves 1 in 15, shelves 1 in 100)."""
    out = []
    for p in view.pieces:
        if p["cat"] not in FACED or not view.floor(p): continue
        ws = view.walls_of(p, WALL_REACH)
        if ws and all(w["name"] in FRONT for w, _ in ws): out.append(p)
    return out


def plant_faults(view):
    if plants_ok(view.rtype): return []
    return [dict(rule="plant", p=p, msg=f"Westwood's {view.rtype.replace('_', ' ')} rooms hold no plants")
            for p in view.pieces if p["cat"] == "plant"]


def facing_faults(view):
    return [dict(rule="front", p=p, msg="shows its back from a front wall") for p in front_faced(view)]


def mixed_kinds(view):
    """{category: [pieces not of the room's main kind]} for the categories a room keeps to one kind of (beds, tombs)."""
    out = {}
    for cat in UNIFY:
        ps = [p for p in view.pieces if p["cat"] == cat]
        kinds = collections.Counter(OBJ.kind(p["t"]) for p in ps)
        if len(kinds) < 2: continue
        main = kinds.most_common(1)[0][0]
        out[cat] = [p for p in ps if OBJ.kind(p["t"]) != main]
    return out


def mixed_faults(view):
    return [dict(rule="mixed", p=p, msg=f"is a {OBJ.kind(p['t'])} among the room's {cat}s of another kind")
            for cat, ps in mixed_kinds(view).items() for p in ps]


# ---- 6. mirrored stamps --------------------------------------------------------------------------------------------
def knots(view):
    """Groups (pieces within LINK of each other) of two or more small pieces."""
    ps = [p for p in view.pieces if view.floor(p) and p["cat"] != "rug"]
    parent = list(range(len(ps)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i in range(len(ps)):
        for j in range(i + 1, len(ps)):
            if edge(ps[i], ps[j]) <= LINK: parent[find(i)] = find(j)
    comps = collections.defaultdict(list)
    for i, p in enumerate(ps): comps[find(i)].append(p)
    return [c for c in comps.values() if len(c) >= 2 and (all(p["cat"] in SMALL for p in c) or
            (all(p["cat"] in SETS for p in c) and any(p["cat"] == "table" for p in c)))]


def _shape(c):
    return sorted(round(math.hypot(a["u"] - b["u"], a["v"] - b["v"]), 2) for i, a in enumerate(c) for b in c[i + 1:])


def twins(view):
    """[(knot, its twin)] of knots of the same kinds in the same shape (a mirrored stamp)."""
    ks = knots(view)
    out = []
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            if len(a) != len(b): continue
            if sorted(OBJ.kind(p["t"]) for p in a) != sorted(OBJ.kind(p["t"]) for p in b): continue
            sa, sb = _shape(a), _shape(b)
            if all(abs(x - y) <= TWIN_TOL for x, y in zip(sa, sb)): out.append((a, b))
    return out


def twin_faults(view):
    return [dict(rule="twin", p=b[0], msg=f"heads a knot ({', '.join(sorted(OBJ.kind(p['t']) for p in b))}) that repeats "
                 f"another in the room in the same shape") for a, b in twins(view)]


# ---- round two (2026-10-06, the g3 sheets' judges): strings of singles, front walls, broken groups, carpets, trades ----
SPACED = 0.5           # pieces along a wall further apart than this (edge to edge) stand apart: a gap, not a run
UNIT_GAP = 0.35        # ... nearer than this they are one unit (a run of shelves, a heap, a desk with its candelabra)
STRING_LEN = 3         # three or more lone units in a row along one wall at gaps: a string of singles
REPEAT = {"supply", "shelf", "lab", "rack", "bed", "chest", "statue", "straw", "nightstand", "counter_shop", "stove",
          "smithy", "desk"}  # the pieces Westwood runs end to end or heaps when it has two
SEATS = ("chair", "bench")
SEAT_SET_MIN = 3       # a table with this many seats is a set whose seats Westwood mixes and pulls about
TRADES = (            # what a shop sells, by its pieces (Westwood's eight curated shops: rules/grammar.py `trades`)
    ("potion", r"^PotionShelves|^FairyJar|^StarChart|^Cauldron|^Bookcase|^TeepeeShelves|^Obelisk|^Zodiac"),
    ("steel", r"^CrateSteel|^BarrelSteel|^BarrelWithTools|^Crate(?!Steel)|^DarkCrate|^Sack"),
    ("arms", r"^Trader(PoleArm|ArmorRack|BowRack|QuiverRack|HangingSwords|HangingCrossbow|CrossedWeapons|"
             r"ShieldWallHanging|HelmShelf|Shelves|ClothesRack|WeaponRack)|^WeaponRack|^ArmorStand|^Armor"),
)
_TRADE_RX = [(n, re.compile(p)) for n, p in TRADES]


def trade_of(t):
    for n, rx in _TRADE_RX:
        if rx.search(t or ""): return n
    return None


def front_only(view, p, reach=WALL_REACH):
    """Whether p stands against the front walls only (seen from behind), not a back wall too."""
    ws = view.walls_of(p, reach)
    return bool(ws) and all(w["name"] in FRONT for w, _ in ws)


def wall_units(view):
    """{wall key: [units]} of the floor pieces (floor lights too) against each wall, in order along it; a unit is a run
    of pieces nearer than UNIT_GAP along the wall: dict(ps, lo, hi, solo) where solo is one piece (and the lights
    beside it) with nothing else within LINK (a desk's chair, a table's seats make a group)."""
    by = collections.defaultdict(list)
    for p in view.pieces:
        if not view.floor(p) or not (p.get("blocking") or p["cat"] == "light"): continue
        ws = view.walls_of(p, WALL_REACH)
        if not ws: continue
        w = ws[0][0]
        by[(w["name"], w["line"], w["coord"])].append(p)
    out = {}
    for key, ps in by.items():
        line = key[1]
        a = (lambda q: (q["v"] - q["hv"], q["v"] + q["hv"])) if line == "/" else (lambda q: (q["u"] - q["hu"], q["u"] + q["hu"]))
        ps = sorted(ps, key=lambda q: a(q)[0])
        units = []
        for p in ps:
            lo, hi = a(p)
            if units and lo - units[-1]["hi"] < UNIT_GAP:
                units[-1]["ps"].append(p); units[-1]["hi"] = max(units[-1]["hi"], hi)
            else:
                units.append(dict(ps=[p], lo=lo, hi=hi))
        for u in units:
            main = [p for p in u["ps"] if p["cat"] != "light"]
            mine = {id(p) for p in u["ps"]}
            off = [q for q in _others(view, u["ps"][0], skip={"rug", "hanging", "light"})
                   if id(q) not in mine and any(edge(p, q) <= LINK for p in u["ps"])]
            u["solo"] = len(main) == 1 and not off
            u["main"] = main[0] if len(main) == 1 else None
        out[key] = units
    return out


def strings(view):
    """[(wall key, units)] of STRING_LEN or more solo units in a row along one wall, each SPACED or more from the next:
    singles at gaps (bookcase, chest, bookcase; three crates none touching; workstations between candelabras)."""
    out = []
    for key, units in wall_units(view).items():
        run = []
        for u in units + [None]:
            if u is not None and u["solo"] and (not run or u["lo"] - run[-1]["hi"] >= SPACED):
                run.append(u); continue
            if len(run) >= STRING_LEN: out.append((key, run))
            run = [u] if (u is not None and u["solo"]) else []
    return out


def kin_gaps(view):
    """[(wall key, a, b)] of two solo pieces of one repeatable kind on one wall with at most one solo unit between
    them, standing apart (Westwood runs its shelves end to end and heaps its stock)."""
    out = []
    for key, units in wall_units(view).items():
        for i, u in enumerate(units):
            if not u["solo"] or u["main"] is None or u["main"]["cat"] not in REPEAT: continue
            for j in (i + 1, i + 2):
                if j >= len(units): break
                w = units[j]
                if j == i + 2 and not units[i + 1]["solo"]: break
                if not w["solo"] or w["main"] is None: continue
                if OBJ.kind(w["main"]["t"]) == OBJ.kind(u["main"]["t"]) and w["lo"] - u["hi"] >= SPACED:
                    out.append((key, u["main"], w["main"])); break
    return out


def seats_of(view, table):
    """The chairs and benches drawn up to a table (within SEAT_REACH, and no nearer any other seat target)."""
    return [q for q in _group_of(view, table) if q is not table]


def seat_sets(view):
    """[(table, seats)] of the tables with SEAT_SET_MIN or more seats."""
    return [(p, s) for p in view.pieces if p["cat"] == "table" for s in [seats_of(view, p)] if len(s) >= SEAT_SET_MIN]


def stamped_set(view, table, seats):
    """Whether a table's seats are one kind, each the same distance off the table (a perfect cross or pair of rows):
    Westwood mixes its chairs and pulls one out."""
    chairs = [q for q in seats if q["cat"] == "chair"]
    if len(chairs) < SEAT_SET_MIN: return False
    if len({OBJ.kind(q["t"]) for q in chairs}) > 1: return False
    gaps = [edge(q, table) for q in chairs]
    return max(gaps) - min(gaps) < 0.3


def carpet_cells_of(view):
    return getattr(view, "carpet_cells", None) or set()


def carpet_relation(view):
    """(carpet share of the floor, pieces standing on it off the walls, pieces at its rim against the walls) or None
    when the room has no carpet laid in its floor."""
    cells = carpet_cells_of(view)
    if not cells: return None
    share = len(cells) / max(1, view.tiles)
    on = [p for p in view.pieces if view.floor(p) and p["cat"] != "light" and view.on_carpet(p) and
          not view.walls_of(p, WALL_REACH)]
    rim = [p for p in view.pieces if view.floor(p) and p["cat"] != "light" and view.walls_of(p, WALL_REACH) and
           not view.on_carpet(p)]
    return share, on, rim


def carpet_offset(view):
    """How far the carpet's middle lies from the room's middle, as a share of the room's half extent (0: centred,
    1: against a wall), the larger of the two axes; and the carpet's margin to the room's edge in tiles (its least)."""
    cells = carpet_cells_of(view)
    room = getattr(view, "cells", None)
    if not cells or not room: return None, None
    def uv(c): return c[0] + c[1] + 1, c[0] - c[1]
    ru = [uv(c) for c in room]; cu = [uv(c) for c in cells]
    mu, mv = sum(a for a, _ in ru) / len(ru), sum(b for _, b in ru) / len(ru)
    hu = (max(a for a, _ in ru) - min(a for a, _ in ru)) / 2 or 1; hv = (max(b for _, b in ru) - min(b for _, b in ru)) / 2 or 1
    ku, kv = sum(a for a, _ in cu) / len(cu), sum(b for _, b in cu) / len(cu)
    off = max(abs(ku - mu) / hu, abs(kv - mv) / hv)
    margin = min(min(a for a, _ in cu) - min(a for a, _ in ru), max(a for a, _ in ru) - max(a for a, _ in cu),
                 min(b for _, b in cu) - min(b for _, b in ru), max(b for _, b in ru) - max(b for _, b in cu)) / 2
    return round(off, 3), round(margin, 2)


def trades_in(view):
    """Counter of trades of a shop's pieces (stock, shelves, racks, hung arms)."""
    return collections.Counter(tr for p in view.pieces for tr in [trade_of(p["t"])] if tr)


# the faults (each against Westwood's measured rate; rules/out/grammar.json `round2`)
def _r2(key, default=None):
    return (stats().get("round2") or {}).get(key, default)


def string_faults(view):
    out = []
    for key, run in strings(view):
        out.append(dict(rule="string", p=run[len(run) // 2]["ps"][0], msg=f"is one of {len(run)} single pieces at gaps "
                        f"along the {key[0]} wall ({', '.join(OBJ.kind(u['ps'][0]['t']) for u in run)})"))
    # kin standing apart (kin_gaps) is measured but not a fault: Westwood stands 21 of its 73 kin pairs apart, the
    # engines 13 of 48 (q0), the same share
    return out


def front_budget(cat, n):
    share = (_r2("front_share", {}) or {}).get(cat)
    if share is None: return n
    return int(math.floor(share * n + 1e-9))


# the categories Westwood seldom stands on a front wall (under a third of those on walls: supplies 27%, workstations 29%,
# smiths' pieces 25%, statues 18%, beds 15%, clutter 14%, racks 11%); tables, chairs, benches and the bar stand there
# about half the time (49-62%) and shelves 43%, so they are not judged here (the faced pieces keep facing_faults)
FRONT_CATS = ("supply", "bed", "rack", "lab", "statue", "smithy", "clutter")


def front_faults(view):
    """Pieces on the front walls past Westwood's share for their category (stock, cots, racks, workstations, the bar);
    the faced pieces (hearths, shelves, desks, chests) keep their own rule (facing_faults)."""
    out = []
    for cat in FRONT_CATS:
        ps = [p for p in view.pieces if p["cat"] == cat and view.floor(p) and view.walls_of(p, WALL_REACH)]
        fr = [p for p in ps if front_only(view, p)]
        allow = front_budget(cat, len(ps))
        for p in fr[allow:]:
            out.append(dict(rule="front", p=p, msg=f"stands on a front wall, seen from behind ({len(fr)} of {len(ps)} "
                            f"{cat} pieces on walls)"))
    return out


def light_front_faults(view):
    """Floor lights on a front wall or in the front corner, past Westwood's share (most of its stand on back walls)."""
    if view.rtype in CEREMONIAL: return []
    L = floor_lights(view)
    fr = [p for p in L if front_only(view, p, CORNER_REACH)]
    allow = int(math.floor((_r2("light_front", 0.0) or 0.0) * len(L) + 1e-9))
    return [dict(rule="light", p=p, msg="stands by a front wall, lighting nothing the eye sees") for p in fr[allow:]]


def seat_faults(view):
    out = []
    tables = [p for p in view.pieces if p["cat"] == "table" and view.floor(p)]
    bare = [p for p in tables if not seats_of(view, p)]
    share = (_r2("table_bare", {}) or {}).get(view.rtype)      # only the types with their own Westwood evidence
    allow = len(tables) if share is None else int(math.floor(share * len(tables) + 1e-9))
    for p in bare[allow:]:
        out.append(dict(rule="seats", p=p, msg="is a table with no chair, stool or bench drawn up to it"))
    stamped = [(t, s) for t, s in seat_sets(view) if stamped_set(view, t, s)]
    allow = int(math.floor((_r2("set_stamped", 0.0) or 0.0) * len(seat_sets(view)) + 1e-9))
    for t, s in stamped[allow:]:
        out.append(dict(rule="seats", p=s[0], msg=f"is one of {len(s)} matching chairs set the same distance round a "
                        f"table (Westwood mixes them and pulls one out)"))
    return out


def floating_carpet(view):
    """Whether the room's carpet lies off every wall (a square or more from each) with nothing standing on it and no
    bed's foot at it: a mat in the middle the furniture rims (Westwood: 7 of its 61 carpets; rules/out/grammar.json
    round2 carpet_floating)."""
    rel = carpet_relation(view)
    if rel is None: return False
    share, on, rim = rel
    off, margin = carpet_offset(view)
    if margin is None or margin < 1 or on: return False
    return not any(at_bed_foot(view, dict(u=u, v=v, hu=0.5, hv=0.5)) for u, v in _carpet_centres(view))


def carpet_faults(view):
    if not floating_carpet(view): return []
    rel = carpet_relation(view)
    p = (rel[2] or [None])[0]
    if p is None: return []
    return [dict(rule="carpet", p=p, msg="the carpet lies in the middle with nothing on it, the furniture rimming it")]


def _carpet_centres(view):
    cells = carpet_cells_of(view)
    return [(x + y + 1, x - y) for (x, y) in cells]


def trade_faults(view):
    if view.rtype != "shop": return []
    tr = trades_in(view)
    if len(tr) < 2: return []
    main = tr.most_common(1)[0][0]
    odd = [p for p in view.pieces if trade_of(p["t"]) not in (None, main)]
    allow = int(_r2("shop_odd_max", 1) or 0)
    return [dict(rule="trade", p=p, msg=f"is a {trade_of(p['t'])} piece in a {main} shop") for p in odd[allow:]]


# ---- round two: the table sets of a hall (taverns, dining halls, great halls) --------------------------------------
SET_HALLS = {"tavern", "dining_hall", "great_hall"}
SET_HALL_TILES = 100     # the halls of this many floor tiles or more (Westwood's: 9 rooms of 104-216 tiles)
SET_ROW_TYPES = {"tavern", "dining_hall"}   # Westwood: 1 row of three sets in its 9 taverns and dining halls (great
                                           # halls set theirs in rows by design: Con06b, Con07E)
ROW_TOL = 0.7            # three table centres within this of one line, at steps within ROW_STEP of each other: a row
ROW_STEP = 0.3


def bare_spot(view):
    """(radius, u, v) of the widest stretch of floor with no piece on it (a light apart): the floor point furthest from
    every piece and wall."""
    ps = [p for p in view.pieces if view.floor(p) and p["cat"] != "light"]
    best = (0.0, None, None)
    for c in getattr(view, "cells", None) or ():
        u, v = c[0] + c[1] + 1, c[0] - c[1]
        d = min([max(0.0, abs(u - p["u"]) - p["hu"], abs(v - p["v"]) - p["hv"]) for p in ps] or [99.0])
        d = min(d, view.wall_dist(dict(u=u, v=v, hu=0.0, hv=0.0)))
        if d > best[0]: best = (d, u, v)
    return best


def bare_limit(view):
    """The widest bare floor Westwood leaves in a hall of the type (rules/out/grammar.json round2 hall_bare_max), or
    None for the rooms it does not judge."""
    if view.rtype not in SET_HALLS or view.tiles < SET_HALL_TILES: return None
    return _r2("hall_bare_max", 5.0)


def set_rows(view):
    """[(a, b, c)] of three tables (any kind) standing in a straight or diagonal line at even steps, off the walls."""
    ts = [p for p in view.pieces if p["cat"] == "table" and view.floor(p) and view.wall_dist(p) > WALL_REACH]
    out = []
    for i, a in enumerate(ts):
        for c in ts[i + 1:]:
            L = math.hypot(c["u"] - a["u"], c["v"] - a["v"])
            if L < 2.0 or L > 16.0: continue
            for b in ts:
                if b is a or b is c: continue
                # b between a and c, near the line, at about the middle
                t = ((b["u"] - a["u"]) * (c["u"] - a["u"]) + (b["v"] - a["v"]) * (c["v"] - a["v"])) / (L * L)
                if not 0.2 < t < 0.8: continue
                px, py = a["u"] + t * (c["u"] - a["u"]), a["v"] + t * (c["v"] - a["v"])
                if math.hypot(b["u"] - px, b["v"] - py) > ROW_TOL: continue
                if abs(t - 0.5) * 2 > ROW_STEP: continue
                out.append((a, b, c))
    seen, uniq = set(), []
    for r in out:
        k = frozenset(id(x) for x in r)
        if k not in seen: seen.add(k); uniq.append(r)
    return uniq


def hall_faults(view):
    out = []
    lim = bare_limit(view)
    if lim is not None:
        r, u, v = bare_spot(view)
        if r > lim:
            near = min((p for p in view.pieces if p["cat"] == "table"), key=lambda p: math.hypot(p["u"] - u, p["v"] - v),
                       default=None)
            if near is not None:
                out.append(dict(rule="hall", p=near, msg=f"leaves {r:.1f} units of bare floor beside it (Westwood's halls: "
                                f"at most {lim:.1f})"))
    if view.rtype in SET_ROW_TYPES:
        for a, b, c in set_rows(view)[:3]:
            out.append(dict(rule="hall", p=b, msg="is one of three table sets stamped in a straight or diagonal row"))
    return out


def _move_group(f, view, grp, spots, log, why):
    """Moves a table and its seats whole to the first of spots (u, v of the table) where all of it fits (a seat that
    would not fit is left out, never the table). True if moved."""
    table = grp[0]
    offs = [(q, q["u"] - table["u"], q["v"] - table["v"]) for q in grp]
    recs = [(q, q["t"], _extra(q["o"]), f._placed_of.get(id(q["o"]))) for q in grp]
    for q in grp:
        if q["o"] in f.objects: f._remove(q["o"])
    saved = (f.in_required, f.composing, f._group)
    f.in_required, f.composing = True, False
    try:
        for (u, v) in spots:
            f._group = []
            n = f.try_put(table["t"], u, v, blocking=True, **recs[0][2])
            if n is None: continue
            placed = [(table, n, u, v)]
            for (q, du, dv), (_, t, ex, rec) in zip(offs[1:], recs[1:]):
                m_ = f.try_put(t, u + du, v + dv, blocking=rec[4] if rec else True, **ex)
                if m_ is not None: placed.append((q, m_, u + du, v + dv))
            if len(grp) > 1 and len(placed) == 1:
                f._remove(n); continue
            for q, o2, uu, vv in placed: q["o"], q["u"], q["v"] = o2, uu, vv
            for q, *_ in recs:
                if all(q is not x[0] for x in placed): q["gone"] = True
            log[why] += 1
            return True
        for q, t, ex, rec in recs:                       # back as it stood
            if rec is not None: q["o"] = f.put(t, rec[0], rec[1], rec[4], rec[5], **ex)
        return False
    finally:
        f.in_required, f.composing, f._group = saved


def fix_halls(f, view, log, rng):
    """A hall's table sets spread over its floor as Westwood's (no stretch of bare floor wider than its halls leave, no
    three sets stamped in a row): where the room has no carpet one is laid in the bare stretch (Westwood's free hall
    tables stand on carpets: its taverns' tables 68% by a wall, 18% on a carpet, 9% free), and a set from the most
    crowded part (a row's first, then the free ones, then those by a wall) moves whole onto it; a set left floating goes
    back. The middle set of a row steps off its line."""
    if view.rtype not in SET_HALLS: return
    for _ in range(4):
        view = view_from_furnisher(f)
        rows = set_rows(view) if view.rtype in SET_ROW_TYPES else []
        lim = bare_limit(view)
        r, u, v = bare_spot(view) if lim is not None else (0.0, None, None)
        tables = [p for p in view.pieces if p["cat"] == "table" and p["o"] in f.objects]
        if not tables: return
        if lim is not None and r > lim:
            if not f.carpet_boxes:
                h = max(1.6, min(3.5, r - 1.2))
                try:
                    if f.lay_carpet(box=(u - h, u + h, v - h, v + h), margin=0.0):
                        log["carpet laid in the hall's bare floor"] += 1
                except Exception:
                    pass

            def crowd(p):
                return min([math.hypot(p["u"] - q["u"], p["v"] - q["v"]) for q in tables if q is not p] or [99])
            cands = sorted(tables, key=lambda p: (not any(p in row for row in rows), view.wall_dist(p) <= WALL_REACH,
                                                  crowd(p)))
            moved = False
            for t in cands[:4]:
                grp = _group_of(view, t)
                if len(grp) < 2: continue                 # a set with its seats, never a lone side table
                home = (t["u"], t["v"])
                spots = [(u + du, v + dv) for k in (0.0, 0.8, 1.6) for du, dv in
                         ((k, 0), (-k, 0), (0, k), (0, -k), (k * 0.7, k * 0.7), (-k * 0.7, k * 0.7))]
                spots = list(dict.fromkeys(spots))
                if not _move_group(f, view, grp, spots, log, "table set moved into the bare floor"): continue
                v2 = view_from_furnisher(f)
                t2 = next((p for p in v2.pieces if p["o"] is t["o"]), None)
                if t2 is not None and table_state(v2, t2) == "floating":
                    back = [(home[0] + k, home[1]) for k in (0.0, 0.4, -0.4)]
                    _move_group(f, v2, [x for x in _group_of(v2, t2)], back, log, "table set put back")
                    continue
                moved = True; break
            if moved: continue
        if rows:
            a, b, c = rows[0]
            du, dv = c["u"] - a["u"], c["v"] - a["v"]
            d = math.hypot(du, dv) or 1.0
            grp = _group_of(view, b)
            spots = [(b["u"] - dv / d * k, b["v"] + du / d * k) for k in (1.6, -1.6, 2.2, -2.2, 1.1, -1.1)]
            spots += [(b["u"] + du / d * k, b["v"] + dv / d * k) for k in (0.9, -0.9)]
            if _move_group(f, view, grp, spots, log, "table set stepped off a row"): continue
        return


def faults(view):
    """Every grammar fault of a furnished room, worst first: dict(rule, p (the piece), msg)."""
    if not ROUND2:
        return (light_faults(view) + group_faults(view) + lone_faults(view) + spacing_faults(view) + plant_faults(view)
                + twin_faults(view) + mixed_faults(view) + facing_faults(view))
    return (light_faults(view) + light_front_faults(view) + group_faults(view) + seat_faults(view) + lone_faults(view)
            + spacing_faults(view) + string_faults(view) + plant_faults(view) + twin_faults(view) + mixed_faults(view)
            + facing_faults(view) + front_faults(view) + carpet_faults(view) + trade_faults(view) + hall_faults(view))


# ---- views -----------------------------------------------------------------------------------------------------------
SIDE_NAME = {"/|BR": "NW", "/|TL": "SE", "\\|TR": "SW", "\\|BL": "NE"}


def view_from_furnisher(f):
    from kit import furnish as F
    by_rec = {id(rec): o for o in f.objects for rec in [f._placed_of.get(id(o))] if rec is not None}
    pieces = []
    for t, rec in f._typed:
        o = by_rec.get(id(rec))
        if o is None: continue
        cat = OBJ.category(t) or F._family_of(t)
        if cat is None: continue
        u, v, hu, hv, blocking, layer = rec
        pieces.append(dict(t=t, cat=cat, u=u, v=v, hu=hu, hv=hv, blocking=bool(blocking), hang=layer == "wall", o=o))
    walls = [dict(name=SIDE_NAME.get(r["side"], "NE"), line=r["line"], coord=r["coord"], lo=r["lo"], hi=r["hi"])
             for r in f.g.runs]
    doors = [((op["coord"], op["along"]) if op["line"] == "/" else (op["along"], op["coord"])) + (op["line"],)
             for op in f.openings]
    boxes = list(f.carpet_boxes)
    def on_carpet(u, v):
        return any(b[0] <= u <= b[1] and b[2] <= v <= b[3] for b in boxes)
    # floor tiles as the checker counts them (its room's cells that are tiles), so both see the same caps
    tiles = len(set(map(tuple, f.g.cells)) & set(map(tuple, f.room.tiles))) or len(f.room.tiles)
    view = View(f.rtype, tiles, pieces, walls, doors, on_carpet)
    fl = getattr(f.spec, "floor", {}) or {}
    view.carpet_cells = {tuple(t) for t in f.room.tiles if CARPET.search(fl.get(tuple(t)) or "")} if boxes else set()
    view.cells = [tuple(t) for t in f.room.tiles]
    return view


CARPET = re.compile(r"Carpet|Rug")


def view_from_map(m, r, C, rtype):
    """The view of a room the checker found (validate/checks.py find_rooms), its pieces from the map."""
    cells = r["cells"]
    cu = sum(x + y + 1 for x, y in cells) / len(cells); cv_ = sum(x - y for x, y in cells) / len(cells)
    walls = [dict(name=C._wall_name(line, coord, cu, cv_), line=line, coord=coord, lo=lo, hi=hi)
             for (line, coord), (lo, hi) in C.room_runs(m, cells).items()]
    cs = set(cells)
    doors = []
    for d in m.doors:
        gx, gy = d["gap"]
        if any((gx + a, gy + b) in cs for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            doors.append((gx + gy + 1, gx - gy, d["line"]))
    pieces = []
    for o in r["objects"]:
        t = o["type"]
        fam = C.RT.family(t)
        cat = OBJ.category(t)
        if (fam is None and cat != "light") or t == "ColorLight" or m.is_door(o): continue
        if re.search(r"Door|Trigger|NPC|PlayerStart", t): continue
        cat = cat or OBJ.FAMILY_CAT.get(fam, fam)
        hu, hv = C._half_uv(o)
        u, v = C.uv_of(o)
        blocking = bool(m.blocking(o))
        hang = fam == "wall_decor" or (cat == "light" and not blocking)
        pieces.append(dict(t=t, cat=cat, u=u, v=v, hu=hu, hv=hv, blocking=blocking, hang=hang, o=o))
    carpet = {c for c in cells if c in m.tiles and CARPET.search(m.tiles[c].get("material") or "")}
    def on_carpet(u, v):
        return (math.floor((u + v) / 2), math.floor((u - v) / 2)) in carpet
    view = View(rtype, r.get("tiles") or len(cells), pieces, walls, doors, on_carpet)
    view.carpet_cells = carpet
    view.cells = [c for c in cells if c in m.tiles]
    return view


# ---- the engines' last pass ------------------------------------------------------------------------------------------
def _must(f):
    """{family: least count} the room's kind must keep (kit/roomtypes.py must, the recipe's need)."""
    from kit.roomtypes import profile
    p = profile(f.kind) or {}
    out = dict(p.get("must") or {})
    for k, n in (getattr(f, "_need", None) or {}).items(): out[k] = max(out.get(k, 0), n)
    return out


def _can_drop(f, t):
    from kit import furnish as F
    fam = F._family_of(t)
    need = _must(f).get(fam)
    return need is None or f._fam_n[fam] > need


def _extra(o):
    return {k: v for k, v in o.items() if k not in ("type", "x", "y")}


def _drop(f, p, log, why):
    if not _can_drop(f, p["t"]): return False
    f._remove(p["o"])
    log[why] += 1
    return True


def _try_at(f, p, spots, light=False, newt=None):
    """Moves piece p to the first of spots (u, v) the furnisher's gate takes (as type newt when given); True if moved.
    On failure it stays as it was."""
    o, t0 = p["o"], p["t"]
    t = newt or t0
    rec = f._placed_of.get(id(o))
    if rec is None: return False
    u0, v0, hu, hv, blocking, layer = rec
    extra = _extra(o)
    f._remove(o)
    saved = (f.in_required, f.placing_light, f.composing)
    f.in_required = True
    f.placing_light = light
    f.composing = False
    try:
        for (u, v) in spots:
            n = f.try_put(t, u, v, blocking=blocking, layer=layer, **extra)
            if n is not None:
                p["o"], p["u"], p["v"], p["t"] = n, u, v, t
                return True
        n = f.put(t0, u0, v0, blocking, layer, **extra)          # back where it stood
        p["o"] = n
        return False
    finally:
        f.in_required, f.placing_light, f.composing = saved


def _sign(f, w):
    for r in f.g.runs:
        if r["line"] == w["line"] and r["coord"] == w["coord"] and r["lo"] == w["lo"]: return r["sign"]
    return None


def _wall_spots(f, view, hu, hv, step=0.5, back_first=True, gaps=(0.3,)):
    """(u, v, wall) of the spots along every wall where a piece of half size (hu, hv) stands with its back `gap` from
    it (the furnisher's gate keeps 0.25 between a piece and a wall)."""
    out = []
    for w in view.walls:
        sign = _sign(f, w)
        if sign is None: continue
        depth = hu if w["line"] == "/" else hv
        for gap in gaps:
            perp = w["coord"] + sign * (depth + gap)
            a = w["lo"] + 0.6
            while a <= w["hi"] - 0.6:
                out.append(((perp, a) if w["line"] == "/" else (a, perp)) + (w,))
                a += step
    if back_first: out.sort(key=lambda s: s[2]["name"] in FRONT)
    return out


def _beside_on_wall(f, view, p, q, gap=0.1, wgaps=(0.3, 0.45)):
    """Spots for p beside q along the wall q stands against, p's back to that wall."""
    ws = view.walls_of(q, WALL_REACH)
    if not ws: return []
    w = ws[0][0]
    sign = _sign(f, w)
    if sign is None: return []
    out = []
    if w["line"] == "/":
        for s_ in (-1, 1):
            a = q["v"] + s_ * (q["hv"] + p["hv"] + gap)
            for wg in wgaps: out.append((w["coord"] + sign * (p["hu"] + wg), a))
    else:
        for s_ in (-1, 1):
            a = q["u"] + s_ * (q["hu"] + p["hu"] + gap)
            for wg in wgaps: out.append((a, w["coord"] + sign * (p["hv"] + wg)))
    return out


def _beside(p, q, gap=0.08):
    """Spots for p touching q on each of its four sides (edge gap `gap`)."""
    du = p["hu"] + q["hu"] + gap; dv = p["hv"] + q["hv"] + gap
    return [(q["u"] + du, q["v"]), (q["u"] - du, q["v"]), (q["u"], q["v"] + dv), (q["u"], q["v"] - dv)]


def fix_plants(f, view, log):
    for fl in plant_faults(view): _drop(f, fl["p"], log, "plant dropped")


def fix_chairs(f, view, log):
    for fl in group_faults(view):
        if fl["rule"] == "chair": _drop(f, fl["p"], log, "chair dropped")


def _group_of(view, table):
    """The table and the chairs, benches and stools drawn up to it (and no nearer anything else)."""
    out = [table]
    for q in view.pieces:
        if q["cat"] in ("chair", "bench") and edge(q, table) <= SEAT_REACH:
            other = min([edge(q, x) for x in view.pieces if x is not table and x["cat"] in SEAT_TARGET] or [99.0])
            if other >= edge(q, table): out.append(q)
    return out


def fix_tables(f, view, log, rng):
    """A floating table set moves whole to a back wall (its seats keep their places round it; a seat that would stand
    in the wall is left out), else to a front wall, else it is dropped (a must table stays)."""
    for fl in [x for x in group_faults(view) if x["rule"] == "table"]:
        table = fl["p"]
        if table["o"] not in f.objects: continue
        if table["cat"] == "bench":            # a bench before the fire: drawn up beside it, the way to the fire open
            h = min((q for q in view.pieces if q["cat"] == "hearth"), key=lambda q: edge(q, table), default=None)
            if h is not None:
                ws = view.walls_of(h, WALL_REACH)
                along_v = bool(ws) and ws[0][0]["line"] == "/"
                ha = (h["hv"] + table["hv"]) if along_v else (h["hu"] + table["hu"])
                spots = []
                for k in (0.3, 0.6, 1.0):
                    for sg in (-1, 1):
                        x = sg * (ha + k)
                        spots.append((table["u"], h["v"] + x) if along_v else (h["u"] + x, table["v"]))
                rng.shuffle(spots)
                if _try_at(f, table, spots):
                    log["bench drawn up beside the hearth"] += 1; continue
        grp = _group_of(view, table)
        offs = [(q, q["u"] - table["u"], q["v"] - table["v"]) for q in grp]
        spots = _wall_spots(f, view, table["hu"], table["hv"], step=0.7, gaps=(0.4, 0.9, 1.5, 1.9))
        rng.shuffle(spots)
        spots.sort(key=lambda s: (s[2]["name"] in FRONT, math.hypot(s[0] - table["u"], s[1] - table["v"]) // 3))
        if _can_drop(f, table["t"]):           # a table that may go never moves to a front wall, seen from behind
            spots = [x for x in spots if x[2]["name"] not in FRONT]
        olds = [(q, q["o"], f._placed_of.get(id(q["o"]))) for q in grp]
        extras = [(q, q["t"], _extra(q["o"]), f._placed_of.get(id(q["o"]))) for q in grp]
        for q in grp:
            if q["o"] in f.objects: f._remove(q["o"])
        moved = False
        saved = (f.in_required, f.composing, f._group)
        f.in_required, f.composing = True, False
        try:
            must = not _can_drop(f, table["t"])
            tries = [(u, v, w, True) for (u, v, w) in spots[:120]]
            if must: tries += [(u, v, w, False) for (u, v, w) in spots[:120]]   # a must table may stand by its wall alone
            for (u, v, w, seated) in tries:
                f._group = []
                n = f.try_put(table["t"], u, v, blocking=True, **extras[0][2])
                if n is None: continue
                placed = [(table, n, u, v)]
                for (q, du, dv), (_, t, ex, rec) in zip(offs[1:], extras[1:]):
                    m_ = f.try_put(t, u + du, v + dv, blocking=rec[4] if rec else True, **ex)
                    if m_ is not None: placed.append((q, m_, u + du, v + dv))
                if seated and len(grp) > 1 and len(placed) == 1:   # a set without one seat left: try the next spot
                    f._remove(n); continue
                for q, o2, uu, vv in placed: q["o"], q["u"], q["v"] = o2, uu, vv
                for q, *_ in extras:
                    if all(q is not x[0] for x in placed): q["gone"] = True
                moved = True
                log["table set moved to a wall"] += 1
                break
        finally:
            f.in_required, f.composing, f._group = saved
        if not moved:
            # put it back, then drop what may be dropped (a must table stays where it stood)
            for q, t, ex, rec in extras:
                if rec is None: continue
                q["o"] = f.put(t, rec[0], rec[1], rec[4], rec[5], **ex)
            # or a carpet laid to it, as Westwood anchors its free tables (23% of its house tables stand on one)
            if fl["msg"].startswith("stands") and not f.carpet_boxes and not before_hearth(view, table) and                     carpeted(view.rtype) >= CARPET_ROOMS:
                us = [q["u"] for q in grp]; vs = [q["v"] for q in grp]
                box = (min(us) - 0.6, max(us) + 0.6, min(vs) - 0.6, max(vs) + 0.6)
                try:
                    laid = f.lay_carpet(box=box, margin=0.8)
                except Exception:
                    laid = []
                if laid:
                    log["carpet laid under the table set"] += 1
                    continue
            if _can_drop(f, table["t"]):
                for q in grp: f._remove(q["o"]); q["gone"] = True
                log["table set dropped"] += 1


def fix_lone(f, view, log, rng):
    """A lone barrel, crate, chest or clutter piece beyond Westwood's share joins a group of its own kind (a heap of
    stock, a chest by the bed or a shelf) on a back wall, else any group against a back wall, else it is dropped."""
    for fl in lone_faults(view):
        p = fl["p"]
        if p.get("gone") or p["o"] not in f.objects: continue
        _rehome(f, view, p, log, rng)
        if not p.get("gone") and fl["msg"].startswith("stands in a heap"):
            # still in the open: a wall heap of its kind cannot take it; it stays only if the room needs it
            if not view.walls_of(p, WALL_REACH) and _drop(f, p, log, "open heap thinned"): p["gone"] = True


def fix_spacing(f, view, log, rng):
    """Breaks even gaps: one inner piece of an evenly spaced wall moves against a neighbour (a heap, for stock) or by
    a part of its gap; a stepped row loses its middle step."""
    for key, ps, g in even_runs(view):
        line = key[1]
        k = rng.randrange(1, len(ps) - 1) if len(ps) > 2 else 1
        p = ps[k]
        if p.get("gone"): continue
        left, right = ps[k - 1], ps[k + 1]
        towards = left if rng.random() < 0.5 else right
        gap = g[k - 1] if towards is left else g[k]
        shift = gap - 0.06 if p["cat"] == "supply" or towards["cat"] == p["cat"] else gap * rng.uniform(0.45, 0.8)
        sgn = -1 if towards is left else 1
        cand = [((p["u"], p["v"] + sgn * shift) if line == "/" else (p["u"] + sgn * shift, p["v"]))]
        cand.append((p["u"], p["v"] - sgn * shift * 0.6) if line == "/" else (p["u"] - sgn * shift * 0.6, p["v"]))
        for k in (0.35, -0.35, 0.5, -0.5, 0.25, -0.25):          # any shift that breaks the rhythm
            x = k * (sum(g) / len(g) + 0.3)
            cand.append((p["u"], p["v"] + x) if line == "/" else (p["u"] + x, p["v"]))
        ends = [ps[0], ps[-1]]                                   # or an end piece moves instead
        if _try_at(f, p, cand): log["even gaps broken"] += 1
        elif any(_try_at(f, e, [((e["u"], e["v"] + x) if line == "/" else (e["u"] + x, e["v"]))
                                for x in (0.4, -0.4, 0.6, -0.6, 0.8, -0.8)]) for e in ends if not e.get("gone")):
            log["even gaps broken"] += 1
        elif p["cat"] in LONE_CATS and _drop(f, p, log, "even row thinned"): p["gone"] = True
    for row in stepped_rows(view):
        a, b, c = row
        if b.get("gone") or b["o"] not in f.objects: continue
        if b["cat"] in ("supply", "chest", "clutter", "light", "plant"):
            spots = _beside(b, a, gap=0.06) + _beside(b, c, gap=0.06)
            rng.shuffle(spots)
        else:                                             # a table, bench, bed or tomb steps out of the line
            du, dv = c["u"] - a["u"], c["v"] - a["v"]
            d = math.hypot(du, dv) or 1.0
            spots = [(b["u"] - dv / d * k, b["v"] + du / d * k) for k in (0.8, -0.8, 1.2, -1.2)]
            spots += [(b["u"] + du / d * k, b["v"] + dv / d * k) for k in (0.6, -0.6)]
        du, dv = c["u"] - a["u"], c["v"] - a["v"]
        d = math.hypot(du, dv) or 1.0
        spots += [(b["u"] - dv / d * k, b["v"] + du / d * k) for k in (0.7, -0.7, 1.1, -1.1)]
        if _try_at(f, b, spots): log["stepped row broken"] += 1
        elif _drop(f, b, log, "stepped row thinned"): b["gone"] = True


def fix_twins(f, view, log, rng):
    for a, b in twins(view):
        seats = [p for p in b if p["cat"] in ("chair", "bench")]
        small = seats[:1] if len(seats) >= 2 else sorted(b, key=lambda p: p["hu"] * p["hv"])
        for p in small:
            if p.get("gone") or p["o"] not in f.objects: continue
            if _drop(f, p, log, "twin knot broken"):
                p["gone"] = True; break


def _light_spots(f, view, t, rng):
    """(u, v, rank) of the spots Westwood stands a floor light: by a wall beside a piece it lights (a desk, a bed's
    head, a shelf, a table, a hearth's side, a statue), in a room corner, flanking a doorway. Lower rank first."""
    hu, hv = f.half(t)
    probe = dict(t=t, cat="light", hu=hu, hv=hv, blocking=True, hang=False)
    out = []
    serve_rank = {"desk": 0, "bed": 0, "shelf": 1, "table": 1, "lab": 1, "counter_shop": 1, "statue": 1, "chest": 2,
                  "hearth": 2, "rack": 2, "bench": 2, "chair": 3, "supply": 3, "nightstand": 0}
    for q in view.pieces:
        if q.get("gone") or q["cat"] not in serve_rank or not view.floor(q) or q["o"] not in f.objects: continue
        if not view.walls_of(q, WALL_REACH): continue
        for (u, v) in _beside_on_wall(f, view, probe, q, gap=0.12):
            out.append((u, v, serve_rank[q["cat"]]))
    for (u, v, w) in _wall_spots(f, view, hu, hv, step=0.5, gaps=(0.3, 0.45)):
        p = dict(probe, u=u, v=v)
        if len({x["line"] for x, _ in view.walls_of(p, CORNER_REACH)}) == 2: out.append((u, v, 1.5))
    for du, dv, line in view.doors:
        for (u, v, w) in _wall_spots(f, view, hu, hv, step=0.5):
            if w["line"] == line and 2.4 <= math.hypot(u - du, v - dv) <= DOOR_FLANK: out.append((u, v, 2.5))
    good = []
    for (u, v, rank) in out:
        p = dict(probe, u=u, v=v)
        if not view.walls_of(p, WALL_REACH) or at_bed_foot(view, p) or view.on_carpet(p): continue
        if light_class(view, p) not in ("served", "corner", "door"): continue
        front = all(w["name"] in FRONT for w, _ in view.walls_of(p, WALL_REACH))
        good.append((rank + (1.5 if front else 0.0) + rng.random() * 1.2, u, v))   # back walls first: in front of a
                                                                                     # front wall it reads as loose
    good.sort()
    return [(u, v) for _, u, v in good]


def fix_lights(f, view, log, rng):
    """Every floor light where Westwood stands one; past the type's count, or with no such spot left, dropped."""
    if view.rtype in CEREMONIAL: return
    lights = [p for p in floor_lights(view) if p["o"] in f.objects]
    cap = light_cap(view.rtype, view.tiles)
    bad = {id(fl["p"]) for fl in light_faults(view) + (light_front_faults(view) if ROUND2 else []) if fl["rule"] == "light"}
    lights.sort(key=lambda p: id(p) in bad)
    keep = [p for p in lights if id(p) not in bad][:cap]
    for p in lights:
        if p in keep: continue
        if len(keep) >= cap or id(p) not in bad:
            f._remove(p["o"]); p["gone"] = True; log["light past the count dropped"] += 1; continue
        def ok(u, v):
            if any(math.hypot(u - k["u"], v - k["v"]) < LIGHT_GAP + 1.0 for k in keep): return False
            q = dict(p, u=u, v=v)
            if view.near_carpet(q, CARPET_PAD): return False
            if ROUND2 and front_only(view, q, CORNER_REACH): return False   # by a front wall: round two (light_front)
            ws = view.walls_of(q, WALL_REACH)
            if ws:
                key = (ws[0][0]["line"], ws[0][0]["coord"])
                on = sum(1 for k in keep if any((w["line"], w["coord"]) == key for w, _ in view.walls_of(k, WALL_REACH)))
                if on >= LIGHTS_PER_WALL: return False
            return True
        spots = [(u, v) for (u, v) in _light_spots(f, view, p["t"], rng) if ok(u, v)]
        if spots and _try_at(f, p, spots[:40], light=True):
            keep.append(p); log["light moved beside what it lights"] += 1
        else:
            f._remove(p["o"]); p["gone"] = True; log["light dropped"] += 1


def fix_front(f, view, log, rng):
    """A faced piece on a front wall moves to a back wall (its wall's variant), else a supply or chest goes."""
    for p in front_faced(view):
        if p.get("gone") or p["o"] not in f.objects: continue
        spots = []
        for (u, v, w) in _wall_spots(f, view, p["hu"], p["hv"], step=0.6):
            if w["name"] in FRONT: continue
            spots.append((math.hypot(u - p["u"], v - p["v"]) + rng.random() * 3, u, v, w))
        spots.sort(key=lambda x: x[0])
        moved = False
        for _, u, v, w in spots[:30]:
            side = next((r["side"] for r in f.g.runs if r["line"] == w["line"] and r["coord"] == w["coord"]), None)
            t = p["t"]
            try:
                t = f.side_variant(p["t"], dict(side=side, line=w["line"])) or p["t"]
            except Exception:
                t = p["t"]
            hu, hv = f.half(t)
            uu, vv = u, v
            if (hu, hv) != (p["hu"], p["hv"]):          # the wall's variant lies the other way: its back to the wall
                sign = _sign(f, w)
                if w["line"] == "/": uu = w["coord"] + sign * (hu + 0.3)
                else: vv = w["coord"] + sign * (hv + 0.3)
            if _try_at(f, p, [(uu, vv)], newt=t if t != p["t"] else None):
                moved = True; break
        if moved: log["faced piece to a back wall"] += 1
        elif p["cat"] in ("chest", "nightstand") and _drop(f, p, log, "faced piece dropped"): p["gone"] = True


def fix_hung(f, view, log, rng):
    """A row of hangings at even gaps loses one (not an end one)."""
    for key, ps, g in hung_even(view):
        p = ps[rng.randrange(1, len(ps) - 1)]
        if p["o"] in f.objects and _drop(f, p, log, "even hanging dropped"): p["gone"] = True


def fix_corners(f, view, log, rng):
    """One lone piece of a kind per corner: all but one join a group by a back wall, else go."""
    for k, ps in corner_singles(view).items():
        rng.shuffle(ps)
        for p in ps[1:]:
            if p.get("gone") or p["o"] not in f.objects: continue
            _rehome(f, view, p, log, rng)


def fix_rings(f, view, log, rng):
    """Pieces ringing a centre at one radius and even angles: one moves in or out (a chair pushed back), or goes."""
    for c, ps in rings(view):
        p = rng.choice(ps)
        if p.get("gone") or p["o"] not in f.objects: continue
        du, dv = p["u"] - c["u"], p["v"] - c["v"]
        d = math.hypot(du, dv) or 1.0
        spots = []
        for k in (0.5, 0.8, -0.4, 1.1):
            spots.append((p["u"] + du / d * k, p["v"] + dv / d * k))
        for k in (0.6, -0.6):                                 # or slides round
            spots.append((p["u"] - dv / d * k, p["v"] + du / d * k))
        if _try_at(f, p, spots): log["ring broken"] += 1
        elif (p["cat"] not in ("chair", "bench") or len(ps) > 3) and _drop(f, p, log, "ring thinned"): p["gone"] = True


def fix_mixed(f, view, log, rng):
    """Beds (tombs) of another kind than the room's main one take the main one's type where it fits."""
    for cat, ps in mixed_kinds(view).items():
        all_ = [q for q in view.pieces if q["cat"] == cat]
        main = collections.Counter(OBJ.kind(q["t"]) for q in all_).most_common(1)[0][0]
        types = collections.Counter(q["t"] for q in all_ if OBJ.kind(q["t"]) == main)
        for p in ps:
            if p["o"] not in f.objects: continue
            for t, _ in types.most_common():
                hu, hv = f.half(t)
                if _try_at(f, p, [(p["u"], p["v"])], newt=t):
                    log[f"{cat} made one kind"] += 1; break
            else:
                # a type of the main kind in this piece's orientation (a bed lying the other way)
                stems = [t for t in f.things if OBJ.kind(t) == main and f.ok_type(t)]
                rng.shuffle(stems)
                for t in stems[:12]:
                    if _try_at(f, p, [(p["u"], p["v"])], newt=t):
                        log[f"{cat} made one kind"] += 1; break


def _rehome(f, view, p, log, rng, drop=True):
    if p["cat"] == "column":                  # a column belongs to a row or a wall, never beside a heap: it goes
        if _drop(f, p, log, "lone column dropped"): p["gone"] = True
        return
    if p["cat"] in WALL_HOMED:                # a desk, rack, workstation or counter: to a back wall, beside its kind
        if _to_back_wall(f, view, p, rng): log[f"lone {p['cat']} to a back wall"] += 1
        elif _drop(f, p, log, f"lone {p['cat']} dropped"): p["gone"] = True
        return
    if p["cat"] == "bench":                   # a bench goes back against a back wall, near where it stood
        spots = [(u, v) for (u, v, w) in _wall_spots(f, view, p["hu"], p["hv"], step=0.6) if w["name"] not in FRONT]
        spots.sort(key=lambda s_: math.hypot(s_[0] - p["u"], s_[1] - p["v"]) + rng.random() * 2)
        if spots and _try_at(f, p, spots[:40]): log["lone bench to a wall"] += 1
        elif _drop(f, p, log, "lone bench dropped"): p["gone"] = True
        return
    same = [q for q in view.pieces if q is not p and not q.get("gone") and q["o"] in f.objects and view.floor(q)
            and q["cat"] in ((p["cat"],) if p["cat"] != "chest" else ("bed", "shelf", "desk", "nightstand", "chest"))]
    anyg = [q for q in view.pieces if q is not p and not q.get("gone") and q["o"] in f.objects and view.floor(q)
            and q["cat"] not in ("light", "rug", "hanging", "chair") and view.walls_of(q)]
    spots = []
    for pool in (same, anyg):
        pool = sorted(pool, key=lambda q: (all(w["name"] in FRONT for w, _ in view.walls_of(q)) if view.walls_of(q) else True,
                                           rng.random()))
        for q in pool:
            spots += _beside(p, q, gap=rng.choice((0.05, 0.1, 0.2)))
    good = []
    for (u, v) in spots:
        ws = view.walls_of(dict(p, u=u, v=v), WALL_REACH)
        if not ws or all(w["name"] in FRONT for w, _ in ws): continue     # by a back wall, in a group
        good.append((u, v))
    if DEBUG: print(f"    rehome {p['t']} at {p['u']:.1f},{p['v']:.1f}: {len(spots)} spots, {len(good)} by a back wall; "
                    f"same {[(q['t'], round(q['u'], 1), round(q['v'], 1)) for q in same]}")
    if good and _try_at(f, p, good):
        log[f"lone {p['cat']} joined a group"] += 1
    elif ROUND2 and p["cat"] in ("supply", "chest", "clutter") and _to_back_wall(f, view, p, rng):
        log[f"lone {p['cat']} to a back wall"] += 1      # the first of a heap there (round two: stock off the front)
    elif drop and _drop(f, p, log, f"lone {p['cat']} dropped"):
        p["gone"] = True


# ---- round two's repairs -----------------------------------------------------------------------------------------
WALL_HOMED = {"desk", "rack", "lab", "counter_shop", "bed", "straw", "statue", "smithy", "table"}


def _to_back_wall(f, view, p, rng, near_kind=True, tries=40):
    """Moves p against a back wall (its wall's variant where the type has one), beside a piece of its own kind there
    first (a run of racks, a workstation by the others), else nearest where it stood. True if moved."""
    kin = [q for q in view.pieces if q is not p and not q.get("gone") and q["o"] in f.objects and view.floor(q)
           and OBJ.kind(q["t"]) == OBJ.kind(p["t"]) and view.walls_of(q, WALL_REACH) and not front_only(view, q)]
    spots = []
    for (u, v, w) in _wall_spots(f, view, p["hu"], p["hv"], step=0.5):
        if w["name"] in FRONT: continue
        d = math.hypot(u - p["u"], v - p["v"])
        if near_kind and kin:
            dk = min(edge(dict(p, u=u, v=v), q) for q in kin)
            d = (0.0 if 0.0 <= dk <= 0.3 else 20.0) + d * 0.2
        spots.append((d + rng.random() * 1.5, u, v, w))
    spots.sort(key=lambda x: x[0])
    for _, u, v, w in spots[:tries]:
        side = next((r["side"] for r in f.g.runs if r["line"] == w["line"] and r["coord"] == w["coord"]), None)
        try:
            t = f.side_variant(p["t"], dict(side=side, line=w["line"])) or p["t"]
        except Exception:
            t = p["t"]
        hu, hv = f.half(t)
        uu, vv = u, v
        if (hu, hv) != (p["hu"], p["hv"]):          # the wall's variant lies the other way: its back to the wall
            sign = _sign(f, w)
            if w["line"] == "/": uu = w["coord"] + sign * (hu + 0.3)
            else: vv = w["coord"] + sign * (hv + 0.3)
        if _try_at(f, p, [(uu, vv)], newt=t if t != p["t"] else None):
            p["hu"], p["hv"] = hu, hv
            return True
    return False


def fix_strings(f, view, log, rng):
    """Singles at gaps along a wall (Westwood: 7 of 116 house rooms hold a string of three or more; rules/out/grammar.json
    round2 strings_rooms): one unit of the string slides along the wall against its neighbour (its own kind first: a
    run of shelves, a heap of stock), as often as it takes to leave no three apart in a row."""
    tried = set()
    for _ in range(8):
        view = view_from_furnisher(f)
        st = [(k, r) for k, r in strings(view) if id(r[0]["ps"][0]["o"]) not in tried]
        if not st: return
        key, run = st[0]
        tried.add(id(run[0]["ps"][0]["o"]))
        line = key[1]
        done = False

        def kin(i, j):
            return 0 <= j < len(run) and run[i]["main"] is not None and run[j]["main"] is not None and \
                OBJ.kind(run[i]["main"]["t"]) == OBJ.kind(run[j]["main"]["t"])
        # a unit beside one of its own kind first, then the inner ones, then the ends
        order = list(range(len(run)))
        rng.shuffle(order)
        order.sort(key=lambda i: (not (kin(i, i - 1) or kin(i, i + 1)), i in (0, len(run) - 1)))
        for i in order:
            p = run[i]["main"]
            if p is None or p.get("gone") or p["o"] not in f.objects: continue
            nbs = [j for j in (i - 1, i + 1) if 0 <= j < len(run)]
            nbs.sort(key=lambda j: (not kin(i, j), rng.random()))
            for j in nbs:
                nb = run[j]
                half = p["hv"] if line == "/" else p["hu"]
                at = p["v"] if line == "/" else p["u"]
                gap = rng.uniform(0.04, 0.14)
                tgt = nb["hi"] + half + gap if j < i else nb["lo"] - half - gap
                shift = tgt - at
                spots = [((p["u"], p["v"] + shift) if line == "/" else (p["u"] + shift, p["v"]))]
                if _try_at(f, p, spots):
                    log["string of singles closed up"] += 1; done = True; break
            if done: break
        if not done:
            # nothing slides: a stock, clutter or statue piece of the string goes
            for u_ in run[1:-1] + run[:1] + run[-1:]:
                p = u_["main"]
                if p is not None and p["cat"] in ("supply", "clutter", "statue") and p["o"] in f.objects and \
                        _drop(f, p, log, "string of singles thinned"):
                    p["gone"] = True; done = True; break


def fix_front2(f, view, log, rng):
    """Stock, cots, racks, workstations, benches and tables on the front walls past Westwood's share for their
    category (rules/out/grammar.json round2 front_share) go to a back wall (stock into a heap there), else go."""
    for fl in front_faults(view):
        p = fl["p"]
        if p.get("gone") or p["o"] not in f.objects: continue
        if p["cat"] == "counter_bar": continue          # the bar is built whole (kit/furnish.py build_bar)
        if p["cat"] in ("supply", "clutter"):
            _rehome(f, view, p, log, rng, drop=False); continue     # where nothing takes it, it stays
        if p["cat"] in ("table", "bench") and any(q["cat"] in SEATS for q in view.pieces
                                                  if q is not p and edge(p, q) <= SEAT_REACH):
            continue                                     # a seated set by the front wall: its seats face the room
        if _to_back_wall(f, view, p, rng): log[f"{p['cat']} from a front wall to a back wall"] += 1
        elif p["cat"] in ("statue", "straw") and _drop(f, p, log, f"{p['cat']} on a front wall dropped"): p["gone"] = True


def fix_seats(f, view, log, rng):
    """A table with no seat (past Westwood's share for the type) gets one or two drawn up (the room's own seat kind);
    a set of matching chairs at one distance has one pulled out (Westwood: 11 of 54 sets so stamped)."""
    for fl in seat_faults(view):
        p = fl["p"]
        if p["cat"] != "table" or p.get("gone") or p["o"] not in f.objects: continue
        n = (1 if max(p["hu"], p["hv"]) < 1.0 else 2) + rng.choice((0, 1))
        saved = (f.in_required, f.composing)
        f.in_required, f.composing = True, False
        before = set(map(id, f.objects))
        try:
            got = f.seats_around((p["u"], p["v"]), p["t"], n)
        except Exception:
            got = 0
        finally:
            f.in_required, f.composing = saved
        v2 = view_from_furnisher(f)
        for q in v2.pieces:                       # a seat never crowds a bed's foot
            if id(q["o"]) not in before and q["cat"] in SEATS and at_bed_foot(v2, q):
                f._remove(q["o"]); got -= 1
        if got > 0: log["seats drawn up to a bare table"] += 1
    view = view_from_furnisher(f)
    for table, seats in seat_sets(view):
        if not stamped_set(view, table, seats): continue
        chairs = [q for q in seats if q["cat"] == "chair" and q["o"] in f.objects]
        rng.shuffle(chairs)
        moved = 0
        for q in chairs[:2 if len(chairs) >= 4 else 1]:
            du, dv = q["u"] - table["u"], q["v"] - table["v"]
            d = math.hypot(du, dv) or 1.0
            spots = []
            for k in (0.45, 0.6, 0.35, 0.75):
                for s_ in (0.0, 0.25, -0.25):
                    spots.append((q["u"] + du / d * k - dv / d * s_, q["v"] + dv / d * k + du / d * s_))
            if _try_at(f, q, spots): moved += 1
        if moved: log["chair pulled out of a stamped set"] += 1


def lift_carpet(f, rec):
    """Takes a carpet up again (kit/furnish.py lay_carpet's record): its floor, trim and box as they were."""
    for t, old in rec["floor"].items():
        if old is None: f.spec.floor.pop(t, None)
        else: f.spec.floor[t] = old
    for t, old in rec["blend"].items():
        if old is None: f.spec.local_blend.pop(t, None)
        else: f.spec.local_blend[t] = old
    for t, old in rec["frm"].items():
        if old: f.spec.local_from[t] = set(old)
        else: f.spec.local_from.pop(t, None)
    if rec["box"] in f.carpet_boxes: f.carpet_boxes.remove(rec["box"])
    if rec in f.carpet_undo: f.carpet_undo.remove(rec)


def fix_carpet(f, view, log, rng):
    """A carpet floating in the middle with nothing on it is laid again where the room's pieces give it a purpose
    (kit/shells.py carpet_target: at the bed's foot, under the seating, before the hearth); with no such place it is
    taken up."""
    if not floating_carpet(view) or not getattr(f, "carpet_undo", None): return
    from kit import shells as SH
    rec = f.carpet_undo[-1]
    u0, u1, v0, v1 = rec["box"]
    lift_carpet(f, rec)
    tgt = SH.carpet_target(f.kind, f._typed)
    laid = []
    if tgt is not None:
        hu, hv = min(3.0, (u1 - u0) / 2), min(3.0, (v1 - v0) / 2)
        for k in (1.0, 0.8, 0.6):
            laid = f.lay_carpet(box=(tgt[0] - hu * k, tgt[0] + hu * k, tgt[1] - hv * k, tgt[1] + hv * k), margin=0.0,
                                material=rec["mat"])
            if laid and not floating_carpet(view_from_furnisher(f)): break
            if laid: lift_carpet(f, f.carpet_undo[-1]); laid = []
    log["carpet laid again to a group" if laid else "floating carpet taken up"] += 1


def _cat_of(t):
    from kit import furnish as F
    fam = F._family_of(t)
    return OBJ.category(t) or OBJ.FAMILY_CAT.get(fam, fam)


# each trade's pieces in Westwood's curated shops (Con02a, Con03A, Con03B, Con06a, Con07B, Con09b, War07A x2)
TRADE_VOCAB = {
    "arms": ("TraderShelves1", "TraderShelves2", "TraderPoleArm1", "TraderPoleArm2", "TraderPoleArm3", "TraderPoleArm4",
             "TraderArmorRack1", "TraderArmorRack2", "TraderClothesRack1", "TraderClothesRack2", "TraderBowRack1",
             "TraderBowRack2", "TraderQuiverRack", "TraderHelmShelf2", "Barrel2", "PiledBarrels1"),
    "potion": ("PotionShelves1", "PotionShelves2", "PotionShelves3", "PotionShelves4", "PotionShelves6", "Bookcase2",
               "Bookcase4", "TeepeeShelvesFull2", "FairyJar"),
    "steel": ("CrateSteel1", "CrateSteel3", "CrateSteel4", "BarrelSteel1", "BarrelSteel2", "BarrelWithTools1"),
}


def _trade_swap(f, view, p, main, rng):
    """Puts a piece of the shop's main trade where p stands (the trade's pieces already in the room first, then
    Westwood's for the trade, nearest p's size; turned to p's wall). True if one fits."""
    have = [t for t, _ in collections.Counter(q["t"] for q in view.pieces if trade_of(q["t"]) == main
                                              and not q.get("hang")).most_common()]
    cands = [t for t in dict.fromkeys(have + list(TRADE_VOCAB.get(main, ()))) if t in f.things and f.ok_type(t)]
    if front_only(view, p):                       # on a front wall: stock only, never a face seen from behind
        cands = [t for t in cands if _cat_of(t) == "supply"]
    if not cands: return False
    ws = view.walls_of(p, WALL_REACH)
    w = ws[0][0] if ws else None
    side = w and next((r["side"] for r in f.g.runs if r["line"] == w["line"] and r["coord"] == w["coord"]), None)
    opts = []
    for t in cands:
        if w is not None:
            try:
                t = f.side_variant(t, dict(side=side, line=w["line"])) or t
            except Exception:
                pass
        hu, hv = f.half(t)
        opts.append((abs(hu - p["hu"]) + abs(hv - p["hv"]) + (0.3 if t in have else 0) + rng.random() * 0.4, t, hu, hv))
    opts.sort()
    sign = _sign(f, w) if w is not None else None
    for _, t, hu, hv in opts[:8]:
        spots = []
        for k in (0.0, 0.3, -0.3, 0.6, -0.6):
            u, v = p["u"], p["v"]
            if w is not None and sign is not None:
                if w["line"] == "/": u, v = w["coord"] + sign * (hu + 0.3), v + k
                else: u, v = u + k, w["coord"] + sign * (hv + 0.3)
            elif k: break
            spots.append((u, v))
        if _try_at(f, p, spots, newt=t if t != p["t"] else None):
            p["hu"], p["hv"] = hu, hv
            return True
    return False


def fix_trades(f, view, log, rng):
    """One trade to a shop (Westwood's 8 shops: 7 sell one trade; Con07B's keeps one potion shelf among its arms): a
    piece of another trade past that one becomes a piece of the main trade where it stands, else goes."""
    for fl in trade_faults(view):
        p = fl["p"]
        if p.get("gone") or p["o"] not in f.objects: continue
        main = trades_in(view).most_common(1)[0][0]
        if not p.get("hang") and _trade_swap(f, view, p, main, rng): log["odd trade piece made the shop's own"] += 1
        elif p.get("hang") or p["cat"] == "hanging":
            f._remove(p["o"]); p["gone"] = True; log["odd trade hanging dropped"] += 1
        elif _drop(f, p, log, "odd trade piece dropped"): p["gone"] = True


def audit(f, rng=None):
    """The engines' last pass: each grammar fault fixed in place (a piece moved into a group or to a wall, else
    dropped; must pieces are never dropped). Returns a Counter of what it did (the engines log it)."""
    import random as _r
    rng = rng or _r.Random(0)
    log = collections.Counter()
    steps = (fix_plants, fix_trades, fix_mixed, fix_chairs, fix_tables, fix_halls, fix_seats, fix_twins, fix_rings,
             fix_corners, fix_lone, fix_front, fix_front2, fix_spacing, fix_strings, fix_hung, fix_lone, fix_carpet,
             fix_lights)
    if not ROUND2:
        steps = (fix_plants, fix_mixed, fix_twins, fix_chairs, fix_tables, fix_rings, fix_corners, fix_lone, fix_front,
                 fix_spacing, fix_hung, fix_lone, fix_lights)
    for step in steps:
        view = view_from_furnisher(f)
        if DEBUG:
            print(f"  [grammar {f.room.id} {step.__name__}] {len(view.pieces)} pieces; " +
                  "; ".join(f"{x['rule']}: {x['p']['t']} {x['msg']}" for x in faults(view)))
        if step in (fix_plants, fix_chairs): step(f, view, log)
        else: step(f, view, log, rng)
    return log


DEBUG = os.environ.get("NOX_GRAMMAR_DEBUG") == "1"
