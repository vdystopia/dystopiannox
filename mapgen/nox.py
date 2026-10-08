"""Helpers for writing Nox maps from Python. A design script builds a Spec with these helpers
and calls build(); build_map.ps1 then writes the map with the editor's own library.

Grid facts (verified against stock maps, the editor, and the engine):
- Walls and floor tiles sit on cells where x + y is even.
- Rooms are rectangles in rotated coordinates u = x + y, v = x - y; on screen they look like
  diamonds. room() takes u/v bounds.
- Wall facing is derived from which diagonal neighbours are walls (see FACING_BY_ARMS).
- Objects, waypoints and polygons use world pixels: 23 px per grid cell.
"""
import json, os, random, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(os.path.dirname(HERE), "rules", "out")


_CAMPAIGN_TYPES = None


def campaign_types():
    """The object types Westwood places in its campaign maps (Con/War/Wiz: rules/common.py is_campaign). Types seen
    only in the quest (G_*) and multiplayer maps are other games' furniture: the kit picks decoration from statistics
    only among these; a type outside them is placed only where a rule names it on purpose."""
    global _CAMPAIGN_TYPES
    if _CAMPAIGN_TYPES is None:
        import sqlite3
        db = os.path.join(os.path.dirname(HERE), "corpus", "out", "nox_corpus.db")
        rx = re.compile(r"^(con|war|wiz)\d\d[a-z]$", re.I)
        with sqlite3.connect(db) as con:
            _CAMPAIGN_TYPES = frozenset(t for t, m in con.execute("SELECT DISTINCT type, map FROM objects") if rx.match(m))
    return _CAMPAIGN_TYPES


def load_rules(name):
    """Machine-readable rules mined from Westwood's maps (rules/out/<name>.json)."""
    with open(os.path.join(RULES, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


_WALL_RULES = None
_DOOR_RULES = None
# Single door to use when a double door does not fit (same look family).
SINGLE_DOOR_FOR = {"Arched": "ArchedDoor", "DunMir": "DunMirDoor", "LOTD": "LOTDSingleDoor", "Galava": "ArchedDoor"}


def door_rules():
    global _DOOR_RULES
    if _DOOR_RULES is None: _DOOR_RULES = load_rules("doors")
    return _DOOR_RULES


def wall_rules():
    global _WALL_RULES
    if _WALL_RULES is None: _WALL_RULES = load_rules("walls")
    return _WALL_RULES
PS32 = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
CELL = 23
SOLO, ARENA = 0x1, 0x34

# Weapon durability Westwood used in its multiplayer maps (most common value per weapon,
# surveyed from the stock maps). Higher than thing.bin's base health, which the editor uses.
STOCK_DURABILITY = {
    "BattleAxe": 300, "Bow": 1000, "CrossBow": 500, "ForceWand": 500, "GreatSword": 400,
    "LesserFireballWand": 100, "Longsword": 180, "MorningStar": 200, "RoundChakram": 300,
    "Sword": 200, "WarHammer": 350,
    # armour, from the editor's table of Westwood's values (MapEditor/XferGui/EquipmentEdit.GetDurability)
    "OrnateHelm": 850, "SteelHelm": 675, "Breastplate": 800, "PlateLeggings": 700, "PlateArms": 600,
    "PlateBoots": 700, "MedievalCloak": 200, "ChainCoif": 325, "ChainLeggings": 325, "ChainTunic": 400,
    "ConjurerHelm": 500, "LeatherHelm": 200, "LeatherArmbands": 200, "LeatherArmoredBoots": 300,
    "LeatherLeggings": 200, "LeatherArmor": 300, "LeatherBoots": 200, "WizardRobe": 325, "WizardHelm": 350,
    "SteelShield": 300, "WoodenShield": 200, "OgreAxe": 50,
}

# Diagonal neighbours of a wall cell, named by screen direction.
TL, TR, BL, BR = (-1, -1), (1, -1), (-1, 1), (1, 1)
# Wall facing for each set of connected neighbours (from the editor's wall renderer).
FACING_BY_ARMS = {
    frozenset([TR, BL]): 0, frozenset([TL, BR]): 1, frozenset([TL, TR, BL, BR]): 2,
    frozenset([TR, BL, TL]): 3, frozenset([TL, BR, TR]): 4, frozenset([TR, BL, BR]): 5,
    frozenset([TL, BR, BL]): 6, frozenset([TL, TR]): 7, frozenset([TR, BR]): 8,
    frozenset([BL, BR]): 9, frozenset([TL, BL]): 10,
    frozenset([TR]): 0, frozenset([BL]): 0, frozenset([TL]): 1, frozenset([BR]): 1, frozenset(): 0,
}

# Stand-ins for wall shapes a material lacks, when Westwood never joined it to anything (rules: walls.joins).
WALL_FALLBACK = {"AspenSparse": ("DecidiousWallBrown",), "Hedge1": ("Shrub", "DecidiousWallGreen"),
                 "CrystalCyan": ("CaveWall2",)}

# Floor edge blending, learned from all stock maps (see mapgen/README.md):
# side neighbours and "tip" neighbours two cells away, and the edge piece Westwood used.
EDGE_SIDES = {"E": (1, -1), "N": (-1, -1), "S": (1, 1), "W": (-1, 1)}
EDGE_TIPS = {"NE": (0, -2), "NW": (-2, 0), "SE": (2, 0), "SW": (0, 2)}
SIDE_PIECES = {"E": (12, 13, 14), "N": (6, 8, 10), "S": (5, 7, 9), "W": (1, 2, 3)}
CORNER_PIECES = {("E", "N"): 18, ("E", "S"): 19, ("N", "W"): 17, ("S", "W"): 16}
TIP_PIECES = {"NE": 15, "NW": 4, "SE": 11, "SW": 0}
TIP_BLOCKERS = {"NE": ("E", "N"), "NW": ("N", "W"), "SE": ("E", "S"), "SW": ("S", "W")}

# No floor blending at a wall [TW-12] (user, 2026-10-08, of Thornwick: "There does not need to be blending on a wall.
# The wall cuts off vision from the inside out and from the outside in. It's also a natural transition point in itself.
# Therefore, this kind of transition must never be used."). A wall piece is drawn from its cell's centre toward each
# wall it joins (its arms; a straight piece across the whole cell). A floor tile (x, y) is centred on grid corner
# (x+1, y+1); a tile and its neighbour (side or tip) meet *at a wall* when a visible wall piece touches the line between
# their centres anywhere (not merely running along it): a / wall lies on the seam between two tiles, a \ wall runs
# through the middle of the tiles on its line, half a tile from their seams with the tiles either side. No edge piece
# is drawn across such a seam (Spec._edges); validate/checks.py check_wall_blends fails a map that has one.
WALL_ARMS = {f: arms for arms, f in FACING_BY_ARMS.items() if len(arms) >= 2}   # the arms each facing draws
_NEIGHBOURS = list(EDGE_SIDES.values()) + list(EDGE_TIPS.values())

# Iron fences: blend or cut [FN-1] (user, 2026-10-08: "Try iron fences with and without blending. If no blending is
# used, then must be put precisely on the line between two tiles."). Westwood blends about two thirds of the floor
# seams along its iron fences (42 campaign layouts: 69% of the 393 differing seams across a / piece; across a \ piece
# 66% of the 463 behind its line tile and 81% of the 233 in front), against 1-10% across its solid walls. Its \ line
# tile takes the floor in front 72% of the time (377 of 524). The two policies (Spec.fence_policy, default FENCE_POLICY):
# - "cut": a fence is a hard cut like any wall (TW-12), and the cut lies exactly on the fence line. Walls and tiles
#   both sit on the even lattice (x + y even; the client's sight pass, client/sight.go, visits only those cells, so a
#   wall cannot be moved off it), and a tile's sides run along the lines x + y odd and x - y odd. A / piece (facing 0,
#   from its cell's corner (x, y+1) to (x+1, y), on x + y = odd) therefore lies exactly on the seam between tiles
#   (x-1, y-1) and (x, y): a floor change there is on the line. A \ piece (facing 1, from (x, y) to (x+1, y+1), on
#   x - y = even) runs through the centres of the tiles on its line: the nearest seams lie half a tile behind and
#   in front of it, and a floor changed there shows a strip of the wrong floor through the bars. So under a \ piece
#   (and the \ arm of a corner, and a gate's \ opening) the floor is one floor on the line tile and on both tiles
#   across it (Spec._fence_line_floors gives them the ground, the floor of lowest blend priority); the change moves
#   one tile off the fence, where it is ordinary ground and blends as ground does.
# - "blend": floors blend across iron fences (Westwood's way); every other wall stays a hard cut (TW-12).
# validate/checks.py: floors.fence_line (cut: a floor change under a \ fence is an error) and floors.wall_blend (an
# edge across any wall, or across a fence under the cut policy, is an error). The policy goes to <name>.fences.json
# beside the map for the checker.
FENCE_POLICY = "cut"
FENCE_POLICIES = ("cut", "blend")
FENCES = ("IronFence", "IronFenceDamaged")
BACKSLASH_ARMS = {TL: (-1, -1), BR: (0, 0)}         # a \ arm -> the tile it runs through, relative to its cell


def is_fence(material):
    return material in FENCES


def fence_line_tiles(facings):
    """For {fence cell: facing}: each \\ arm's line tile -> (the tile behind it (E, up the screen), the tile in front of
    it (W)) [FN-1]. Under the cut policy those three are one floor."""
    out = {}
    for (x, y), f in facings.items():
        for arm in WALL_ARMS.get(f, ()):
            if arm in BACKSLASH_ARMS:
                t = (x + BACKSLASH_ARMS[arm][0], y + BACKSLASH_ARMS[arm][1])
                out[t] = ((t[0] + 1, t[1] - 1), (t[0] - 1, t[1] + 1))
    return out


def fence_facings(walls, gaps=()):
    """{cell: facing} of the iron fence pieces among `walls` ({cell: (facing, material)}), with each door opening
    (`gaps`) in a fence line (a gate) as a straight piece of that line."""
    out = {c: f for c, (f, mat) in walls.items() if is_fence(mat)}
    gaps = set(gaps)
    for g in sorted(gaps):
        for facing, d in ((1, (1, 1)), (0, (1, -1))):
            run = [(g[0] + s * k * d[0], g[1] + s * k * d[1]) for s in (1, -1) for k in (1, 2)]
            if any(c in walls and is_fence(walls[c][1]) for c in run) and \
                    any(c in walls or c in gaps for c in run[:1] + run[2:3]):
                out[g] = facing
                break
    return out


def _orient(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def _touches(p, q, a, b):
    """Segment a-b (a wall arm) touches segment p-q (between two tile centres) other than by running along it. The
    points lie on a half-cell grid, so the arithmetic is exact."""
    d1, d2 = _orient(a, b, p), _orient(a, b, q)
    if d1 == 0 and d2 == 0: return False
    return d1 * d2 <= 0 and _orient(p, q, a) * _orient(p, q, b) <= 0


def _seam_template():
    """For a wall cell at (0, 0) (walls and tiles both sit where x + y is even, so one template serves every wall):
    arm -> the ordered tile pairs (t, n), relative to the cell, whose centres' line that arm touches."""
    out = {}
    for arm in (TL, TR, BL, BR):
        a, b = (0.5, 0.5), (0.5 + arm[0] / 2, 0.5 + arm[1] / 2)
        out[arm] = [((tx, ty), (tx + dx, ty + dy)) for tx in range(-4, 4) for ty in range(-4, 4) if (tx + ty) % 2 == 0
                    for dx, dy in _NEIGHBOURS if _touches((tx + 1, ty + 1), (tx + dx + 1, ty + dy + 1), a, b)]
    return out


_SEAMS = _seam_template()


def wall_seams(facings):
    """The ordered tile pairs (t, n) that meet at a wall [TW-12], given {wall cell: facing} of the visible walls."""
    out = set()
    for (x, y), f in facings.items():
        for arm in WALL_ARMS.get(f, ()):
            for (tx, ty), (nx, ny) in _SEAMS[arm]:
                out.add(((x + tx, y + ty), (x + nx, y + ny)))
    return out


def uv_to_xy(u, v):
    return (u + v) / 2, (u - v) / 2


def xy_to_uv(x, y):
    return x + y, x - y


def px(u, v):
    """World pixel position of a point given in u/v coordinates (may be fractional)."""
    x, y = uv_to_xy(u, v)
    return round(x * CELL, 1), round(y * CELL, 1)


def rect_tiles(u0, u1, v0, v1):
    """Floor cells of a u/v room, offset by one tile like stock rooms."""
    for u in range(u0, u1 - 1, 2):
        for v in range(v0 + 2, v1 + 1, 2):
            x, y = uv_to_xy(u, v)
            yield int(x), int(y)


def rect_wall_cells(u0, u1, v0, v1):
    cells = set()
    for v in range(v0, v1 + 2, 2):
        for u in (u0, u1): cells.add((u, v))
    for u in range(u0, u1 + 2, 2):
        for v in (v0, v1): cells.add((u, v))
    return {tuple(int(c) for c in uv_to_xy(u, v)) for u, v in cells}


def _poly_area(pts):
    return abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                   for i in range(len(pts)))) / 2


def _covers_map(pts, share=0.25):
    """A polygon big enough to be a map's minimap polygon (a quarter of the map or more), not one room's light."""
    return _poly_area(pts) >= share * (256 * CELL) ** 2


def _world_polygon(others, edge=256 * CELL, pad=23):
    """The map-wide minimap polygon: inset from the map's edges, its corners off the (0,0)-(5888,5888) diagonal
    (validate check_minimap), with a rectangular bite from the nearest edge round the bounding box of each other polygon
    so no spot lies in two. With no others it is the four corners it has always been."""
    A, B, Cc, D = (46, 23), (edge - 23, 69), (edge - 46, edge - 23), (23, edge - 69)
    sides = {"top": (A, B), "right": (B, Cc), "bottom": (Cc, D), "left": (D, A)}
    bites = {k: [] for k in sides}
    for pts in others:
        if not pts or _covers_map(pts): continue
        x0, x1 = min(p[0] for p in pts) - pad, max(p[0] for p in pts) + pad
        y0, y1 = min(p[1] for p in pts) - pad, max(p[1] for p in pts) + pad
        side = min((("top", y0), ("right", edge - x1), ("bottom", edge - y1), ("left", x0)), key=lambda s: s[1])[0]
        bites[side].append((x0, x1, y0, y1))

    def on_side(side, t):                       # the point of a side at parameter t (x for top/bottom, y for left/right)
        (ax, ay), (bx, by) = sides[side]
        if side in ("top", "bottom"): return (t, ay + (by - ay) * (t - ax) / (bx - ax))
        return (ax + (bx - ax) * (t - ay) / (by - ay), t)

    out = []
    for side in ("top", "right", "bottom", "left"):
        a, b = sides[side]
        out.append(list(a))
        horiz = side in ("top", "bottom")
        forward = (b[0] > a[0]) if horiz else (b[1] > a[1])
        lo_t, hi_t = sorted((a[0], b[0]) if horiz else (a[1], b[1]))
        used = []
        for x0, x1, y0, y1 in sorted(bites[side], key=lambda r: (r[0] if horiz else r[2]), reverse=not forward):
            t0, t1 = (x0, x1) if horiz else (y0, y1)
            if t0 <= lo_t + pad or t1 >= hi_t - pad or any(t0 < u1 and u0 < t1 for u0, u1 in used): continue
            used.append((t0, t1))
            first, last = (t0, t1) if forward else (t1, t0)
            depth = {"top": y1, "bottom": y0, "left": x1, "right": x0}[side]
            p1, p4 = on_side(side, first), on_side(side, last)
            p2 = (first, depth) if horiz else (depth, first)
            p3 = (last, depth) if horiz else (depth, last)
            out += [list(p1), list(p2), list(p3), list(p4)]
    for p in out:                                # off the diagonal the game's lines follow
        if abs(p[0] - p[1]) < 1: p[0] += 2
    return [[round(x, 1), round(y, 1)] for x, y in out]


class Spec:
    def __init__(self, name, **info):
        # Westwood kept map names to 8 characters. OpenNox loads 9 (TreePlace), but its map list cuts a 10-character
        # name to 8 and then cannot find the map (Gloomdelve, 2026-10-03): 9 at most
        assert len(name) <= 9, "map names are limited to 9 characters (OpenNox's map list cuts longer ones)"
        self.d = dict(name=name, info=info, ambient=[150, 150, 150], walls=[], tiles=[], objects=[],
                      waypoints=[], polygons=[])
        self.wallmap = {}     # (x, y) -> dict(material, variation, window, facing or None)
        self.floor = {}       # (x, y) -> material
        self.blend = {}       # material -> (priority, edge type used when it spills onto others)
        self.edge_over = {}   # (overlay, base) -> edge type override
        self.local_blend = {}  # (x, y) -> priority for one tile whose material does not blend elsewhere
        self.local_from = {}   # (x, y) -> the only materials whose edge may spill onto that tile (a carpet's trim)
        self.pattern_tiles = {}  # (x, y) -> {(overlay, base)}: a room's second floor spills onto that tile of its first
                               # (a doorway: the path outside spills onto the threshold tile)
        self.door_gaps = set()  # wall cells opened for doors (count as wall when shaping neighbours)
        self.indoor = {}        # floor tile of a building's room -> the room's floor (kit/building.py), for its thresholds
        self.sheltered = set()  # tiles inside a doorway: no outdoor ground spills onto them (_door_thresholds)
        self.scripts = {}       # filename -> Go source: the map's script (OpenNox runs the .go files in maps/<Name>/)
        self.routes = []        # routes the scripts walk (kit/npcs.Behaviours): <map>.routes.json for the checker
        self.rng = random.Random(1)
        self.fence_policy = FENCE_POLICY  # iron fences: "cut" (a hard cut on the fence line) or "blend" [FN-1]

    # ---- walls -------------------------------------------------------------------------
    def wall(self, x, y, material, variation=None, window=False, facing=None):
        """Wall cell. variation=None (recommended) picks a valid style for the final wall shape in
        Westwood's proportions; an explicit variation that is invalid for the shape is replaced."""
        assert (x + y) % 2 == 0, (x, y)
        self.wallmap[(x, y)] = dict(material=material, variation=variation, window=window, facing=facing)

    def remove_wall(self, x, y):
        self.wallmap.pop((x, y), None)

    def room(self, u0, u1, v0, v1, wall, floor):
        """Walled rectangular room in u/v coordinates (all bounds even)."""
        assert all(n % 2 == 0 for n in (u0, u1, v0, v1))
        for x, y in sorted(rect_wall_cells(u0, u1, v0, v1)):
            self.wall(x, y, wall)
        for x, y in rect_tiles(u0, u1, v0, v1):
            self.floor[(x, y)] = floor

    # ---- floor -------------------------------------------------------------------------
    def tile(self, x, y, material):
        if (x + y) % 2 == 0: self.floor[(x, y)] = material

    def blending(self, material, priority, edge="BlendEdge"):
        """Let `material` spill soft edges onto neighbouring materials of lower priority."""
        self.blend[material] = (priority, edge)

    def _edges(self, seams=frozenset()):
        """The edge pieces of every tile. `seams`: the tile pairs that meet at a wall (wall_seams), where no edge is drawn
        [TW-12]."""
        out = {}
        for (x, y), base in self.floor.items():
            # beside a room's second floor, which blends onto it (kit/shells.py), while the tile is that room's floor
            pat = {o for o, b in self.pattern_tiles.get((x, y), ()) if b == base}
            if pat: bp = -60
            elif base in self.blend: bp = self.blend[base][0]
            elif (x, y) in self.local_blend: bp = self.local_blend[(x, y)]
            else: continue
            near = {}
            only = self.local_from.get((x, y))
            if pat: only = (only or set()) | pat
            sheltered, indoor = (x, y) in self.sheltered, (x, y) in self.indoor
            for name, (dx, dy) in {**EDGE_SIDES, **EDGE_TIPS}.items():
                m = self.floor.get((x + dx, y + dy))
                if (x + dx, y + dy) not in self.indoor:
                    # the outdoor ground stops at the wall line (Starwell playtest, 2026-10-05): a room's tile takes no
                    # edge from outside across its wall (the wall hides that seam; a tip always lies across it), nor in
                    # a doorway (_door_thresholds)
                    if sheltered: continue
                    if indoor and (name in EDGE_TIPS or (x + max(dx, 0), y + max(dy, 0)) in self.wallmap): continue
                if ((x, y), (x + dx, y + dy)) in seams: continue          # never across a wall [TW-12]
                if m in self.blend and self.blend[m][0] > bp and (only is None or m in only):
                    near.setdefault(m, set()).add(name)
            edges = []
            for m, dirs in sorted(near.items(), key=lambda kv: self.blend[kv[0]][0]):
                etype = self.edge_over.get((m, base), self.blend[m][1])
                sides = {d for d in dirs if d in EDGE_SIDES}
                for (a, b), piece in CORNER_PIECES.items():
                    if a in sides and b in sides:
                        edges.append([m, etype, piece]); sides -= {a, b}
                for d in sorted(sides):
                    edges.append([m, etype, self.rng.choice(SIDE_PIECES[d])])
                for t in sorted(d for d in dirs if d in EDGE_TIPS):
                    if not any(b in dirs for b in TIP_BLOCKERS[t]):
                        edges.append([m, etype, TIP_PIECES[t]])
            if edges: out[(x, y)] = edges
        return out

    # ---- objects, waypoints, polygons -----------------------------------------------------
    def obj(self, type_, u, v, team=None):
        x, y = px(u, v)
        return self.obj_px(type_, x, y, team)

    def obj_px(self, type_, x, y, team=None, items=None, **extra):
        """An object at world pixel (x, y). items: what it holds (a chest's loot), each a type name, (type, xfer)
        or (type, xfer, count); Gold takes its amount as xfer {"Amount": n}."""
        o = self.item(type_, x, y, **extra)
        if team is not None: o["team"] = team
        if items: o["items"] = self.items_at(items, x, y)
        self.d["objects"].append(o)
        return o

    @staticmethod
    def item(type_, x, y, **extra):
        o = dict(type=type_, x=round(x, 1), y=round(y, 1), **extra)
        if type_ in STOCK_DURABILITY and "durability" not in o: o["durability"] = STOCK_DURABILITY[type_]
        return o

    def items_at(self, items, x, y):
        """Inventory objects for a holder at (x, y), set a little off it as Westwood's are (about 25 px)."""
        out = []
        for k, it in enumerate(items):
            t, xfer, n = (it, None, 1) if isinstance(it, str) else (tuple(it) + (None, 1))[:3]
            for _ in range(n or 1):
                o = self.item(t, x + 18 + 3 * (k % 4), y + 20 + 2 * (k // 4))
                if xfer: o["xfer"] = dict(xfer)
                out.append(o)
        return out

    def clone(self, donor_map, scr, x, y, name=None, xfer=None):
        """Copy a configured object (e.g. a townsperson in its clothes) from a stock map by its script name; `name`
        gives it a script name in this map, `xfer` overrides its settings (facing, default action)."""
        o = dict(clone=dict(map=donor_map, scr=scr), x=round(x, 1), y=round(y, 1))
        if name: o["scr"] = name
        if xfer: o["xfer"] = dict(xfer)
        self.d["objects"].append(o)
        return o

    def door_type_for(self, wall_material):
        """Door type Westwood uses in walls of this material, sampled by frequency (rules: walls.doors)."""
        options = wall_rules()["doors"]["types_by_wall_material"].get(wall_material) or {"WoodenDoor": 1}
        types, weights = zip(*sorted(options.items()))
        return self.rng.choices(types, weights)[0]

    def _plain_run(self, cell, line):
        """True if `cell` is a wall whose only connections run along `line` (no junction or corner)."""
        if cell not in self.wallmap: return False
        along = {TL, BR} if line == "\\" else {TR, BL}
        arms = {a for a in (TL, TR, BL, BR) if (cell[0] + a[0], cell[1] + a[1]) in self.wallmap
                or (cell[0] + a[0], cell[1] + a[1]) in self.door_gaps}
        return arms <= along

    def door(self, type_, gap, line):
        """Door at wall cell `gap`; line '\\' or '/' is the direction of the wall it sits in.
        type_=None picks a type that suits the wall material. Follows Westwood's construction
        (rules/out/doors.json): single doors fill a 1-cell opening; double doors (*HalfDoor, Gate,
        CryptDoor, ...) are two halves hinged at the ends of a 2-cell opening, and fall back to the
        matching single door where the wall has no room for two cells. Returns the (first) door object."""
        if type_ is None:
            type_ = self.door_type_for(self.wallmap.get(gap, {}).get("material", ""))
        step = (1, 1) if line == "\\" else (1, -1)
        rule = door_rules()["types"].get(type_, {})
        by_line = rule.get("by_line", {}).get(line)
        kind = by_line["kind"] if by_line and by_line.get("weighted_count", 0) >= 5 else rule.get("kind")
        if kind == "double":
            for a in (gap, (gap[0] - step[0], gap[1] - step[1])):
                b = (a[0] + step[0], a[1] + step[1])
                if self._plain_run(a, line) and self._plain_run(b, line):
                    for cell in (a, b):
                        self.remove_wall(*cell); self.door_gaps.add(cell)
                    if line == "\\":
                        first = self.obj_px(type_, a[0] * CELL, a[1] * CELL, door=16)                 # North
                        self.obj_px(type_, (b[0] + 1) * CELL, (b[1] + 1) * CELL, door=0)              # South
                    else:
                        first = self.obj_px(type_, a[0] * CELL, (a[1] + 1) * CELL, door=8)            # West
                        self.obj_px(type_, (b[0] + 1) * CELL, b[1] * CELL, door=24)                   # East
                    return first
            # no room for two halves: Westwood hangs the type alone in this wall direction often enough,
            # or uses the matching single door
            if not (by_line and by_line.get("share_one_cell", 0) >= 0.25):
                type_ = next((single for key, single in SINGLE_DOOR_FOR.items() if key in type_), "WoodenDoor")
        gx, gy = gap
        self.remove_wall(gx, gy); self.door_gaps.add(gap)
        if line == "\\":
            return self.obj_px(type_, (gx + 1) * CELL, (gy + 1) * CELL, door=0)    # South
        return self.obj_px(type_, gx * CELL, (gy + 1) * CELL, door=8)              # West

    def waypoint(self, x, y, name=""):
        w = dict(id=len(self.d["waypoints"]) + 1, x=round(x, 1), y=round(y, 1), name=name, links=[])
        self.d["waypoints"].append(w)
        return w

    def link(self, a, b):
        if b["id"] not in a["links"]: a["links"].append(b["id"])
        if a["id"] not in b["links"]: b["links"].append(a["id"])

    def polygon(self, name, ambient, points_px, minimap=100):
        self.d["polygons"].append(dict(name=name, ambient=list(ambient), minimap=minimap,
                                       points=[[round(x, 1), round(y, 1)] for x, y in points_px]))

    # ---- output ------------------------------------------------------------------------
    def _finalize(self):
        walls = []
        for (x, y), w in sorted(self.wallmap.items()):
            facing = w["facing"]
            if facing is None:
                # door openings count as wall: Westwood shapes jamb pieces that way (rules/out/doors.json)
                arms = frozenset(a for a in (TL, TR, BL, BR) if (x + a[0], y + a[1]) in self.wallmap
                                 or (x + a[0], y + a[1]) in self.door_gaps)
                facing = FACING_BY_ARMS[arms]
            mat = self._wall_material(w["material"], facing)
            walls.append(dict(x=x, y=y, facing=facing, material=mat,
                              variation=self._wall_variation(mat, facing, w["variation"]), window=w["window"]))
        assert self.fence_policy in FENCE_POLICIES, self.fence_policy
        fences = fence_facings({(w["x"], w["y"]): (w["facing"], w["material"]) for w in walls}, self.door_gaps)
        self._wall_line_floors()
        self._door_thresholds()
        if self.fence_policy == "cut": self._fence_line_floors(fences)
        for _ in range(3): self._buffer_never_touch()      # a buffer tile can meet a new pair (weeds by the water)
        self._blend_thresholds()
        # the walls no edge is drawn across [TW-12]; iron fences too under the cut policy, their gates with them, and
        # under the blend policy not iron fences [FN-1]
        hard = {(w["x"], w["y"]): w["facing"] for w in walls if not w["material"].startswith("Invisible")}
        if self.fence_policy == "cut": hard.update(fences)
        else: hard = {c: f for c, f in hard.items() if c not in fences}
        edges = self._edges(wall_seams(hard))
        tiles = [dict(x=x, y=y, material=m, **({"edges": edges[(x, y)]} if (x, y) in edges else {}))
                 for (x, y), m in sorted(self.floor.items())]
        polygons = list(self.d["polygons"])
        if not any(p["minimap"] == 100 and _covers_map(p["points"]) for p in polygons):
            # The minimap draws only the walls of the group of the polygon the player stands in (Westwood's
            # Con02a:Town is group 100, like every wall we write); with no polygon it shows nothing but doors. One
            # polygon over the whole map, lit as the map is lit, so the light does not change.
            # The game tests "inside" by counting the edges crossed by a line from the player to the map's corner
            # (0, 0) or (5888, 5888), alternately (nox_xxx_polygon_421660). A polygon with a corner on either point
            # (or on the diagonal those lines follow) makes the line end on a vertex, counts two crossings and calls
            # the player outside, and the minimap stays empty: so the polygon stands inside the map, its corners off
            # the diagonal.
            # The design's own polygons (Rimehold's ice cave, with its own light) keep their ground: the game keeps a
            # player in the polygon he stands in while it still holds him, and otherwise takes the first that does, so
            # two polygons over one spot would leave the cave lit as the world. The world polygon is bitten round each
            # of them from the nearest edge of the map (_world_polygon). A design polygon alone had left Rimehold
            # without a minimap outside the cave (validate check_minimap).
            polygons.append(dict(name=f"{self.d['name']}:World", ambient=list(self.d["ambient"]), minimap=100,
                                 points=_world_polygon([p["points"] for p in polygons])))
        return dict(self.d, walls=walls, tiles=tiles, polygons=polygons)

    def _fence_line_floors(self, fences):
        """Under the cut policy a floor change under an iron fence lies exactly on the fence line [FN-1]: a / piece is
        on a seam between tiles and may stand between two floors; a \\ piece runs through the middle of the tiles on its
        line, so the line tile and the tiles behind and in front of it take one floor, the ground (the floor of lowest
        blend priority among them: grass under a fence between grass and cobble, dirt between dirt and stone; else the
        floor in front, as Westwood lays a \\ line tile). A yard's own floor then stops one tile inside its \\ sides,
        where it meets the ground as ground meets ground, away from the fence."""
        if getattr(self, "raw_floors", False): return
        lines = fence_line_tiles(fences)
        for _ in range(4):                               # a corner's tiles serve two arms: settle until nothing moves
            moved = False
            for t, (e, w) in sorted(lines.items()):
                trio = [c for c in (t, e, w) if c in self.floor and c not in self.indoor]
                mats = {self.floor[c] for c in trio}
                if len(mats) < 2: continue
                prio = lambda m_: self.blend[m_][0] if m_ in self.blend else 99
                front = self.floor.get(w) or self.floor.get(t)
                ground = min(sorted(mats), key=lambda m_: (prio(m_), m_ != front))
                for c in trio:
                    if self.floor[c] != ground: self.floor[c] = ground; moved = True
            if not moved: break

    def _wall_line_floors(self):
        """The room's floor runs under its walls, out to the wall line on the side in front of the wall (Starwell
        playtest, 2026-10-05: the grass and the path's dirt showed on the boards inside; TW-12, Thornwick 2026-10-08:
        no blending at a wall). Each tile that meets a room's tile through an open cell by a wall takes that room's
        floor, except a tile on a NW-SE (\\) wall line with the room behind it, up the screen (a room's SW wall). A \\
        wall runs through the middle of the tiles on its line, and Westwood gives such a tile the floor in front of the
        wall, below it on screen (StuccoLightWood, Log, Cobblestone, StoneGray, Dilapidated walls: the front floor or a
        third floor, the floor behind 0-4%), so each side's floor runs up to the wall as seen and the wall's own
        picture covers the half tile behind it. Giving it the room's floor had laid a strip of boards half a tile wide
        along the outside of every such wall (Thornwick's inn, TW-12). No edge is drawn across the wall either way
        (_edges)."""
        if getattr(self, "raw_floors", False) or not self.indoor: return
        for (x, y) in sorted(self.indoor):
            f = self.indoor[(x, y)]                      # the room's own floor, never a carpet laid on it
            if (x, y) not in self.floor: continue
            for (dx, dy) in EDGE_SIDES.values():
                n = (x + dx, y + dy)
                if n in self.indoor or n not in self.floor: continue
                if (dx, dy) == EDGE_SIDES["W"] and self._on_backslash_line(n): continue    # the ground in front [TW-12]
                shared = (x + max(dx, 0), y + max(dy, 0))
                if shared in self.wallmap or shared in self.door_gaps: continue
                if any((shared[0] + a, shared[1] + b) in self.wallmap for a in (-1, 0, 1) for b in (-1, 0, 1)) and \
                        self._may_take(n, f):
                    self.floor[n] = f

    def _on_backslash_line(self, t):
        """Tile t lies on a visible NW-SE (\\) wall's line: the wall piece of one of its two cells on that line reaches
        through its centre (toward the other, a wall or a door opening)."""
        a, b = (t[0], t[1]), (t[0] + 1, t[1] + 1)
        wall = lambda c: c in self.wallmap and not self.wallmap[c]["material"].startswith("Invisible")
        return (wall(a) and (b in self.wallmap or b in self.door_gaps)) or (wall(b) and (a in self.wallmap or a in self.door_gaps))

    def _may_take(self, t, floor):
        """Whether tile t may take a room's floor: no neighbour of a floor Westwood never lets touch it that the buffer
        pass (_buffer_never_touch) could not settle, its buffer meeting water or another floor it never touches (a stone
        floor against swamp grass by the water: Mirefen's stilt houses)."""
        if not hasattr(self, "_never_touch"):
            self._never_touch = {}
            for r in load_rules("floors")["never_touch"]:
                bm = r.get("buffer_materials")
                self._never_touch[frozenset((r["a"], r["b"]))] = max(bm.items(), key=lambda kv: kv[1])[0] if bm else None
        near = list(EDGE_SIDES.values()) + list(EDGE_TIPS.values())
        for dx, dy in near:
            n = (t[0] + dx, t[1] + dy)
            m = self.floor.get(n)
            if not m or m == floor or frozenset((m, floor)) not in self._never_touch: continue
            buf = self._never_touch[frozenset((m, floor))]      # the buffer pass turns that neighbour to buf: unless
            if not buf: return False                            # buf itself would meet a floor it never touches
            if any(frozenset((k, buf)) in self._never_touch for k in
                   (self.floor.get((n[0] + a, n[1] + b)) for a, b in near) if k and k not in (buf, floor)):
                return False
        return True

    def _door_thresholds(self):
        """A building's doorway as Westwood draws it (Starwell playtest, 2026-10-05: "Tile blending on the inside of doors
        seems consistently off", the path's dirt and the grass spilt onto the boards just inside the door). In
        Westwood's town doorways the inside floor runs right up to the door, under it, and out onto the doorstep; the
        ground outside blends onto that doorstep tile, never onto a tile that reaches into the room (corpus, exterior
        doors of the single-player maps: the tiles inside the wall line carry the ground's edge at about 1 door in 10).
        So for each door between a room's floor (`indoor`) and the ground: the tiles covering the opening or the cell
        straight out from it that lie wholly outside the wall line take the room's floor (the doorstep: two tiles in a
        NW-SE (backslash) wall, where the floor tiles sit on the wall line; one in a NE-SW (/) wall, where they straddle it) and
        let the ground spill onto them; the tiles that reach inside take no outdoor edge at all (`sheltered`)."""
        if getattr(self, "raw_floors", False) or not self.indoor: return
        def covering(c):
            return [t for t in ((c[0], c[1]), (c[0] - 1, c[1] - 1), (c[0] - 1, c[1]), (c[0], c[1] - 1)) if t in self.floor]
        def cells(t):
            return ((t[0], t[1]), (t[0] + 1, t[1]), (t[0], t[1] + 1), (t[0] + 1, t[1] + 1))
        for g in sorted(self.door_gaps):
            along = {(1, 1), (-1, -1)}
            ln = "\\" if any((g[0] + a, g[1] + b) in self.wallmap or (g[0] + a, g[1] + b) in self.door_gaps
                              for a, b in along) else "/"
            p = (1, -1) if ln == "\\" else (1, 1)
            sides = []
            for sgn in (1, -1):
                c = (g[0] + 3 * sgn * p[0], g[1] + 3 * sgn * p[1])
                ts = covering(c)
                sides.append((any(t in self.indoor for t in ts), ts))
            if sides[0][0] == sides[1][0]: continue                         # between two rooms, or two yards (a gate)
            o = p if sides[1][0] else (-p[0], -p[1])                       # toward the outside
            inside = next(t for t in sides[0 if sides[0][0] else 1][1] if t in self.indoor)
            floor = self.indoor[inside]                  # the room's own floor (a carpet stops inside the door)
            for c in (g, (g[0] + o[0], g[1] + o[1])):
                for t in covering(c):
                    side = [(cx - g[0]) * o[0] + (cy - g[1]) * o[1] for cx, cy in cells(t)]
                    if min(side) < 0:                                      # reaches into the room: the room's floor
                        self.sheltered.add(t)
                        self.local_blend.pop(t, None)
                        if t not in self.indoor and self._may_take(t, floor): self.floor[t] = floor
                    elif t not in self.indoor and self._may_take(t, floor):
                        self.floor[t] = floor
                        if floor not in self.blend: self.local_blend[t] = -50

    def _blend_thresholds(self):
        """Where an outdoor ground that blends (a dirt path, grass) meets a building's floor that blends with nothing
        (boards, flagstones) with no wall between them, in a doorway, the ground spills onto the floor with edge
        pieces, as Westwood draws a threshold (the checker counts a pair Westwood blends left unblended as a hard
        seam). Same sides as _buffer_never_touch."""
        if getattr(self, "raw_floors", False): return
        # the land's own floors, the biomes' too (Emberhollow: marble paving against VolcanicCraggy, an error)
        ground = re.compile(r"Grass|Dirt|Sand|Weeds|Volcanic|IceFloor")       # SwampGrass matches "Grass"
        for (x, y), a in list(self.floor.items()):
            for d, shared in (((1, -1), (x + 1, y)), ((1, 1), (x + 1, y + 1))):
                n = (x + d[0], y + d[1])
                b = self.floor.get(n)
                if b is None or a == b or shared in self.wallmap: continue
                for g, f, ft in ((a, b, n), (b, a, (x, y))):
                    if g in self.blend and ground.search(g) and f not in self.blend and not ground.search(f) \
                            and ft not in self.local_blend and ft not in self.sheltered:
                        self.local_blend[ft] = -50

    def _buffer_never_touch(self):
        """Floors Westwood never lets touch (rules/out/floors.json never_touch: a stone floor against a sparse grass):
        the ground tile of such a pair takes the floor Westwood puts between them (its buffer material), as at the inner
        corner of an L or T building, where the house's floor meets the grass outside. Same sides as the checker
        (validate/checks.py check_floors). A test map of the checker sets `raw_floors` to keep its bad floors."""
        if getattr(self, "raw_floors", False): return
        nt = {}
        for r in load_rules("floors")["never_touch"]:
            buf = max(r["buffer_materials"].items(), key=lambda kv: kv[1])[0] if r.get("buffer_materials") else None
            if buf: nt[frozenset((r["a"], r["b"]))] = buf
        # the land's own floors, the biomes' too (Emberhollow: marble paving against VolcanicCraggy, an error)
        ground = re.compile(r"Grass|Dirt|Sand|Weeds|Volcanic|IceFloor")       # SwampGrass matches "Grass"
        for (x, y), a in list(self.floor.items()):
            for d, shared in (((1, -1), (x + 1, y)), ((1, 1), (x + 1, y + 1))):
                n = (x + d[0], y + d[1])
                b = self.floor.get(n)
                if b is None or a == b or shared in self.wallmap: continue
                buf = nt.get(frozenset((a, b)))
                if not buf: continue
                if ground.search(b) and not ground.search(a): self.floor[n] = buf
                elif ground.search(a) and not ground.search(b): self.floor[(x, y)] = buf; a = buf

    def _wall_material(self, material, facing):
        """The material itself, or, when Westwood never drew it in this shape (DecidiousWallRed has no
        crossing piece, AspenSparse no T-junctions), the visible material Westwood joins it to most often
        that has the shape (rules: walls.materials.joins), else WALL_FALLBACK."""
        rules = wall_rules()
        valid = rules["valid_variations"]
        if valid.get(material, {}).get(str(facing)): return material
        mats = rules["materials"]
        joins = mats.get(material, {}).get("joins", {})
        for other in sorted(joins, key=joins.get, reverse=True) + list(WALL_FALLBACK.get(material, ())):
            if not mats.get(other, {}).get("invisible") and valid.get(other, {}).get(str(facing)): return other
        return material

    def _wall_variation(self, material, facing, wanted):
        """A wall style that exists for this material and shape (rules: walls.valid_variations)."""
        rules = wall_rules()
        valid = rules["valid_variations"].get(material, {}).get(str(facing), {})
        if wanted is not None and str(wanted) in valid: return wanted
        weights = rules["variation_weights"].get(material, {}).get(str(facing)) or {"0": 1.0}
        options, w = zip(*sorted(weights.items()))
        return int(self.rng.choices(options, w)[0])

    def build(self, out_dir, check=True):
        """Write the map (and .nxz unless d['nxz'] is False) into out_dir. Returns the report lines.
        check=True then runs the automatic checks (validate/validate.py) and adds their summary line;
        the full report is in validate/out/<name>/report.md.
        Containers left empty get Westwood's loot first (kit/loot.py; a test map sets `loot = False` to keep them
        empty); the tally goes to <name>.loot.json beside the map. A map with a story then has its spoken lines voiced
        (mapgen/voice.py; a "VOICE" line reports it)."""
        loot_lines = []
        if getattr(self, "loot", True):
            from kit import loot
            rep = loot.fill(self)
            loot_lines.append(loot.summary(rep))
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, self.d["name"] + ".loot.json"), "w", encoding="utf-8") as f:
                json.dump(rep, f, indent=1)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(self._finalize(), f)
        try:
            res = subprocess.run([PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                  os.path.join(HERE, "build_map.ps1"), "-Spec", f.name, "-OutDir", out_dir],
                                 capture_output=True, text=True)
        finally:
            os.unlink(f.name)
        lines = (res.stdout + res.stderr).strip().splitlines()
        if res.returncode or not any(l.startswith("OK") for l in lines):
            sys.exit("map build failed:\n" + "\n".join(lines))
        lines += loot_lines
        # the transporters (kit/transport.py): <name>.transport.json for the checker, transport.go for the scripts
        if getattr(self, "transporters", None) is not None:
            self.transporters.finish(self, out_dir)
        elif os.path.exists(os.path.join(out_dir, self.d["name"] + ".transport.json")):
            os.remove(os.path.join(out_dir, self.d["name"] + ".transport.json"))
        if self.scripts:                        # beside the map: install copies them into maps/<Name>/ with it
            sd = os.path.join(out_dir, self.d["name"] + "_scripts")
            os.makedirs(sd, exist_ok=True)
            for fn, src in self.scripts.items():
                with open(os.path.join(sd, fn), "w", encoding="utf-8", newline="\n") as f: f.write(src)
            lines.append(f"SCRIPTS\t{sd}\t{len(self.scripts)} file(s)")
        # the fence policy the floors were laid by, for the checker (validate check_wall_blends, check_fence_lines) [FN-1]
        with open(os.path.join(out_dir, self.d["name"] + ".fences.json"), "w", encoding="utf-8") as f:
            json.dump({"policy": self.fence_policy}, f)
        # the routes the scripts walk, waypoint by waypoint, for the checker's leg check (validate check_routes)
        rp = os.path.join(out_dir, self.d["name"] + ".routes.json")
        if self.routes:
            with open(rp, "w", encoding="utf-8") as f: json.dump(self.routes, f)
        elif os.path.exists(rp):
            os.remove(rp)
        # every line said in a dialogue window voiced (mapgen/voice.py: <name>_dialog/ and <name>.voice.json beside the
        # map, from the design's <name>.strings.json and .speech.json); NOX_NOVOICE=1 skips it (trying seeds)
        if not os.environ.get("NOX_NOVOICE"):
            if HERE not in sys.path: sys.path.insert(0, HERE)
            import voice
            lines += voice.build_step(self.d["objects"], out_dir, self.d["name"])
        if check and not os.environ.get("NOX_NOCHECK"):      # NOX_NOCHECK=1: skip the checker (trying seeds)
            chk = subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), "validate", "validate.py"),
                                  os.path.join(out_dir, self.d["name"] + ".map"), "--quiet"], capture_output=True, text=True)
            lines.append("CHECK " + (chk.stdout.strip().splitlines() or ["(checker produced no output)"])[-1])
        return lines
