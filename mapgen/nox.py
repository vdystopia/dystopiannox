"""Helpers for writing Nox maps from Python. A design script builds a Spec with these helpers
and calls build(); build_map.ps1 then writes the map with the editor's own library.

Grid facts (verified against stock maps, the editor, and the engine):
- Walls and floor tiles sit on cells where x + y is even.
- Rooms are rectangles in rotated coordinates u = x + y, v = x - y; on screen they look like
  diamonds. room() takes u/v bounds.
- Wall facing is derived from which diagonal neighbours are walls (see FACING_BY_ARMS).
- Objects, waypoints and polygons use world pixels: 23 px per grid cell.
"""
import json, os, random, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(os.path.dirname(HERE), "rules", "out")


def load_rules(name):
    """Machine-readable rules mined from Westwood's maps (rules/out/<name>.json)."""
    with open(os.path.join(RULES, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


_WALL_RULES = None


def wall_rules():
    global _WALL_RULES
    if _WALL_RULES is None: _WALL_RULES = load_rules("walls")
    return _WALL_RULES
PS32 = os.path.join(os.environ["WINDIR"], "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
CELL = 23
SOLO, ARENA = 0x1, 0x34

# Weapon durability Westwood used in its multiplayer maps (most common value per weapon,
# surveyed from the stock maps). Higher than thing.bin's base health, which the editor uses.
STOCK_DURABILITY = {
    "BattleAxe": 300, "Bow": 1000, "CrossBow": 500, "ForceWand": 500, "GreatSword": 400,
    "LesserFireballWand": 100, "Longsword": 180, "MorningStar": 200, "RoundChakram": 300,
    "Sword": 200, "WarHammer": 350,
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

# Floor edge blending, learned from all stock maps (see mapgen/README.md):
# side neighbours and "tip" neighbours two cells away, and the edge piece Westwood used.
EDGE_SIDES = {"E": (1, -1), "N": (-1, -1), "S": (1, 1), "W": (-1, 1)}
EDGE_TIPS = {"NE": (0, -2), "NW": (-2, 0), "SE": (2, 0), "SW": (0, 2)}
SIDE_PIECES = {"E": (12, 13, 14), "N": (6, 8, 10), "S": (5, 7, 9), "W": (1, 2, 3)}
CORNER_PIECES = {("E", "N"): 18, ("E", "S"): 19, ("N", "W"): 17, ("S", "W"): 16}
TIP_PIECES = {"NE": 15, "NW": 4, "SE": 11, "SW": 0}
TIP_BLOCKERS = {"NE": ("E", "N"), "NW": ("N", "W"), "SE": ("E", "S"), "SW": ("S", "W")}


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


class Spec:
    def __init__(self, name, **info):
        assert len(name) <= 8, "map names are limited to 8 characters"
        self.d = dict(name=name, info=info, ambient=[150, 150, 150], walls=[], tiles=[], objects=[],
                      waypoints=[], polygons=[])
        self.wallmap = {}     # (x, y) -> dict(material, variation, window, facing or None)
        self.floor = {}       # (x, y) -> material
        self.blend = {}       # material -> (priority, edge type used when it spills onto others)
        self.edge_over = {}   # (overlay, base) -> edge type override
        self.rng = random.Random(1)

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

    def _edges(self):
        out = {}
        for (x, y), base in self.floor.items():
            if base not in self.blend: continue
            bp = self.blend[base][0]
            near = {}
            for name, (dx, dy) in {**EDGE_SIDES, **EDGE_TIPS}.items():
                m = self.floor.get((x + dx, y + dy))
                if m in self.blend and self.blend[m][0] > bp:
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

    def obj_px(self, type_, x, y, team=None, **extra):
        o = dict(type=type_, x=round(x, 1), y=round(y, 1), **extra)
        if team is not None: o["team"] = team
        if type_ in STOCK_DURABILITY: o["durability"] = STOCK_DURABILITY[type_]
        self.d["objects"].append(o)
        return o

    def clone(self, donor_map, scr, x, y):
        """Copy a configured object (e.g. a townsperson) from a stock map by its script name."""
        o = dict(clone=dict(map=donor_map, scr=scr), x=round(x, 1), y=round(y, 1))
        self.d["objects"].append(o)
        return o

    def door_type_for(self, wall_material):
        """Door type Westwood uses in walls of this material, sampled by frequency (rules: walls.doors)."""
        options = wall_rules()["doors"]["types_by_wall_material"].get(wall_material) or {"WoodenDoor": 1}
        types, weights = zip(*sorted(options.items()))
        return self.rng.choices(types, weights)[0]

    def door(self, type_, gap, line):
        """Door in a one-cell wall gap. line '\\' or '/' is the direction of the wall it sits in.
        Placement follows Westwood's doors (98-100% of single-player doors). type_=None picks a
        type that suits the wall material."""
        gx, gy = gap
        if type_ is None:
            type_ = self.door_type_for(self.wallmap.get(gap, {}).get("material", ""))
        self.remove_wall(gx, gy)
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
                arms = frozenset(a for a in (TL, TR, BL, BR) if (x + a[0], y + a[1]) in self.wallmap)
                facing = FACING_BY_ARMS[arms]
            walls.append(dict(x=x, y=y, facing=facing, material=w["material"],
                              variation=self._wall_variation(w["material"], facing, w["variation"]), window=w["window"]))
        edges = self._edges()
        tiles = [dict(x=x, y=y, material=m, **({"edges": edges[(x, y)]} if (x, y) in edges else {}))
                 for (x, y), m in sorted(self.floor.items())]
        return dict(self.d, walls=walls, tiles=tiles)

    def _wall_variation(self, material, facing, wanted):
        """A wall style that exists for this material and shape (rules: walls.valid_variations)."""
        rules = wall_rules()
        valid = rules["valid_variations"].get(material, {}).get(str(facing), {})
        if wanted is not None and str(wanted) in valid: return wanted
        weights = rules["variation_weights"].get(material, {}).get(str(facing)) or {"0": 1.0}
        options, w = zip(*sorted(weights.items()))
        return int(self.rng.choices(options, w)[0])

    def build(self, out_dir):
        """Write the map (and .nxz unless d['nxz'] is False) into out_dir. Returns the report lines."""
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
        return lines
