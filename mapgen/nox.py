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
PS32 = os.path.join(os.environ["WINDIR"], "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
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
                               # (a doorway: the path outside spills onto the threshold tile)
        self.door_gaps = set()  # wall cells opened for doors (count as wall when shaping neighbours)
        self.scripts = {}       # filename -> Go source: the map's script (OpenNox runs the .go files in maps/<Name>/)
        self.routes = []        # routes the scripts walk (kit/npcs.Behaviours): <map>.routes.json for the checker
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
            if base in self.blend: bp = self.blend[base][0]
            elif (x, y) in self.local_blend: bp = self.local_blend[(x, y)]
            else: continue
            near = {}
            only = self.local_from.get((x, y))
            for name, (dx, dy) in {**EDGE_SIDES, **EDGE_TIPS}.items():
                m = self.floor.get((x + dx, y + dy))
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
        for _ in range(3): self._buffer_never_touch()      # a buffer tile can meet a new pair (weeds by the water)
        self._blend_thresholds()
        edges = self._edges()
        tiles = [dict(x=x, y=y, material=m, **({"edges": edges[(x, y)]} if (x, y) in edges else {}))
                 for (x, y), m in sorted(self.floor.items())]
        polygons = list(self.d["polygons"])
        if not any(p["minimap"] == 100 for p in polygons):
            # The minimap draws only the walls of the group of the polygon the player stands in (Westwood's
            # Con02a:Town is group 100, like every wall we write); with no polygon it shows nothing but doors. One
            # polygon over the whole map, lit as the map is lit, so the light does not change.
            edge = 256 * CELL
            polygons.append(dict(name=f"{self.d['name']}:World", ambient=list(self.d["ambient"]), minimap=100,
                                 points=[[0, 0], [edge, 0], [edge, edge], [0, edge]]))
        return dict(self.d, walls=walls, tiles=tiles, polygons=polygons)

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
                    if g in self.blend and ground.search(g) and f not in self.blend and not ground.search(f)                             and ft not in self.local_blend:
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
        the full report is in validate/out/<name>/report.md."""
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
        if self.scripts:                        # beside the map: install copies them into maps/<Name>/ with it
            sd = os.path.join(out_dir, self.d["name"] + "_scripts")
            os.makedirs(sd, exist_ok=True)
            for fn, src in self.scripts.items():
                with open(os.path.join(sd, fn), "w", encoding="utf-8", newline="\n") as f: f.write(src)
            lines.append(f"SCRIPTS\t{sd}\t{len(self.scripts)} file(s)")
        # the routes the scripts walk, waypoint by waypoint, for the checker's leg check (validate check_routes)
        rp = os.path.join(out_dir, self.d["name"] + ".routes.json")
        if self.routes:
            with open(rp, "w", encoding="utf-8") as f: json.dump(self.routes, f)
        elif os.path.exists(rp):
            os.remove(rp)
        if check and not os.environ.get("NOX_NOCHECK"):      # NOX_NOCHECK=1: skip the checker (trying seeds)
            chk = subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), "validate", "validate.py"),
                                  os.path.join(out_dir, self.d["name"] + ".map"), "--quiet"], capture_output=True, text=True)
            lines.append("CHECK " + (chk.stdout.strip().splitlines() or ["(checker produced no output)"])[-1])
        return lines
