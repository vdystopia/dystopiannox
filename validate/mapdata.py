"""Loads a Nox map for checking: exports it through the editor's own library (corpus/dump_maps.ps1,
the same exporter as the reference corpus) and decodes walls, floor tiles, objects and doors.

Grid model (verified in phase 2, rules/rooms.py): the map is a 256 x 256 grid of 23 px cells. A wall
occupies its cell; a floor tile at (x, y) covers cells (x, y), (x+1, y), (x, y+1), (x+1, y+1).
Flood-filling cells 4-connected with wall cells blocked separates every enclosed area, because
diagonal wall chains cannot be crossed by 4-connected steps.
"""
import json, os, re, subprocess, sys, tempfile
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RULES = os.path.join(REPO, "rules", "out")
CORPUS_JSON = os.path.join(REPO, "corpus", "out", "json")
OUT = os.path.join(HERE, "out")
PS32 = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
CELL = 23
GRID = 256
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
TL, TR, BL, BR = (-1, -1), (1, -1), (-1, 1), (1, 1)
DIAG = (TL, TR, BL, BR)

sys.path.insert(0, os.path.join(REPO, "mapgen"))
sys.path.insert(0, os.path.join(REPO, "rules"))
sys.path.insert(0, os.path.join(REPO, "review"))
from nox import FACING_BY_ARMS  # noqa: E402

ARMS_OF = {f: arms for arms, f in FACING_BY_ARMS.items() if len(arms) >= 2}   # stubs also map to 0/1; skip them
# door object corner -> wall cell left open for it (verified on Westwood's doors, rules/doors.py)
DOOR_GAP = {"South": (-1, -1), "North": (0, 0), "East": (-1, 0), "West": (0, -1)}
DOOR_LINE = {"South": "\\", "North": "\\", "East": "/", "West": "/"}
LINE_STEP = {"\\": (1, 1), "/": (1, -1)}
VOID_FLOORS = {"Black"}
LINE_ARMS = {"\\": frozenset([TL, BR]), "/": frozenset([TR, BL])}


@lru_cache(None)
def rules(name):
    with open(os.path.join(RULES, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def export(map_path, out_dir=None):
    """Exports a .map to JSON with the editor's library; returns the JSON path."""
    out_dir = out_dir or os.path.join(OUT, "json")
    os.makedirs(out_dir, exist_ok=True)
    lst = os.path.join(out_dir, "_maplist.txt")
    with open(lst, "w", encoding="utf-8") as f: f.write(os.path.abspath(map_path))
    res = subprocess.run([PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                          os.path.join(REPO, "corpus", "dump_maps.ps1"), "-MapList", lst, "-OutDir", out_dir],
                         capture_output=True, text=True)
    name = os.path.splitext(os.path.basename(map_path))[0]
    js = os.path.join(out_dir, name + ".json")
    if "FAIL" in res.stdout or not os.path.exists(js):
        raise RuntimeError(f"could not read {map_path}:\n{res.stdout}\n{res.stderr}")
    return js


@lru_cache(None)
def thing_db(path):
    with open(path, encoding="utf-8") as f:
        g = json.load(f)
    return ([x["name"] for x in g["floors"]], [x["name"] for x in g["walls"]], [x["name"] for x in g["edges"]],
            {t["name"]: t for t in g["things"]})


class Wall:
    __slots__ = ("x", "y", "facing", "material", "variation", "window", "secret", "destructible", "invisible")

    def __init__(self, x, y, facing, material, variation, props):
        self.x, self.y, self.facing, self.material, self.variation = x, y, facing, material, variation
        props = props or {}
        self.window = bool(props.get("Window"))
        self.secret = bool(props.get("Secret_ScanFlags"))
        self.destructible = bool(props.get("Destructable"))
        self.invisible = material.startswith("Invisible")

    @property
    def opaque(self):
        return not self.invisible and not self.window


class MapData:
    def __init__(self, json_path):
        with open(json_path, encoding="utf-8") as f:
            d = json.load(f)
        things_path = os.path.join(os.path.dirname(json_path), "things.json")
        if not os.path.exists(things_path): things_path = os.path.join(CORPUS_JSON, "things.json")
        F, W, E, self.things = thing_db(things_path)
        self.name, self.info, self.ambient = d["name"], d["info"], d["ambient"]
        self.file = d.get("file")
        self.walls = {(x, y): Wall(x, y, f, W[m], v, p) for x, y, f, m, v, mm, p in d["walls"]}
        self.tiles = {(x, y): dict(material=F[m], variation=v, edges=[(F[eg], ev, ed, E[et]) for eg, ev, ed, et in es])
                      for x, y, m, v, es in d["tiles"]}
        self.objects = []
        for o in d["objects"]:
            t = self.things.get(o["t"], {})
            self.objects.append(dict(type=o["t"], x=o["x"], y=o["y"], xtype=o["xtype"], xfer=o["xfer"] or {},
                                     scr=o["scr"], cls=t.get("class") or "", flags=t.get("flags") or "",
                                     ext=t.get("ext"), ex=t.get("ex") or 0, ey=t.get("ey") or 0, id=len(self.objects)))
        self.waypoints, self.polygons, self.groups = d["waypoints"], d["polygons"], d["groups"]
        self.script_funcs = d["script"]["funcs"]
        self.cover = set()                       # cells covered by a floor tile
        for (x, y), t in self.tiles.items():
            if t["material"] in VOID_FLOORS: continue            # black void paint
            self.cover.update(((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)))
        self.scripted_walls = {tuple(m) for g in self.groups if g["type"] == "walls" for m in g["members"]}
        self.doors = self._doors()
        self.door_gaps = {d["gap"]: d for d in self.doors}

    # ---- geometry -------------------------------------------------------------------------------
    @staticmethod
    def cell_of(x, y):
        return int(x // CELL), int(y // CELL)

    def tile_at_cell(self, cell):
        """A floor tile covering the cell (None in the void)."""
        x, y = cell
        for t in ((x, y), (x - 1, y), (x, y - 1), (x - 1, y - 1)):
            if t in self.tiles: return t
        return None

    def floor_at(self, px, py):
        t = self.tile_at_cell(self.cell_of(px, py))
        return self.tiles[t]["material"] if t else None

    def is_door(self, o):
        return o["xtype"] == "DoorXfer" or "DOOR" in o["cls"]

    def blocking(self, o):
        """Objects that stop a walking player (furniture, rocks, trees, ...)."""
        c, f = o["cls"], o["flags"]
        if self.is_door(o) or "MONSTER" in c or "NO_COLLIDE" in f or not o["ext"] or o["ext"] == "NULL": return False
        if not ("OBSTACLE" in c or "IMMOBILE" in c): return False
        return max(o["ex"], o["ey"]) > 0

    def radius(self, o):
        """Approximate footprint radius in px (CIRCLE: ex is the radius; BOX: ex x ey)."""
        if o["ext"] == "BOX": return max(o["ex"], o["ey"]) / 2
        return o["ex"]

    # ---- doors ------------------------------------------------------------------------------------
    def _doors(self):
        out = []
        for o in self.objects:
            if o["xtype"] != "DoorXfer": continue
            direction = o["xfer"].get("Direction")
            if direction not in DOOR_GAP: continue
            cx, cy = round(o["x"] / CELL), round(o["y"] / CELL)
            dx, dy = DOOR_GAP[direction]
            gap = (cx + dx, cy + dy)
            out.append(dict(obj=o, gap=gap, line=DOOR_LINE[direction], direction=direction, corner=(cx, cy),
                            in_wall_cell=gap in self.walls))
        return out

    # ---- wall shapes --------------------------------------------------------------------------------
    def arms(self, cell):
        """Directions this cell's wall piece reaches toward (door openings count as their line)."""
        if cell in self.walls:
            return ARMS_OF.get(self.walls[cell].facing, frozenset())
        if cell in self.door_gaps:
            return LINE_ARMS[self.door_gaps[cell]["line"]]
        return frozenset()


def load(path):
    """MapData from a .map (exported first) or an already exported .json."""
    if path.lower().endswith(".json"):
        return MapData(path)
    return MapData(export(path))


def corpus_json(name):
    return os.path.join(CORPUS_JSON, name + ".json")


def campaign_corpus_maps():
    """(map name, weight) for Westwood's campaign maps (Con/War/Wiz; common.campaign_weights); weight 1/size of the layout group."""
    import common
    return sorted(common.campaign_weights().items())
