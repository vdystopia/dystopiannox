"""Shared helpers for mining map-making rules from the reference corpus (corpus/out/nox_corpus.db).

Verified facts encoded here (see mapgen/README.md and corpus/FINDINGS.md):
- Walls and floor tiles sit on cells where x + y is even. A floor tile at (x, y) is drawn centred
  on grid corner (x+1, y+1). Objects use world pixels (23 per cell).
- Rotated coordinates u = x + y, v = x - y: walls run along constant u ('/' runs, facing 0) or
  constant v ('\\' runs, facing 1).
- Wall neighbours are the 4 diagonal cells; floor edge neighbours are the 4 diagonal cells
  ("sides") plus 4 cells two steps away along an axis ("tips").
- Style statistics come from the campaign maps only (Con/War/Wiz: campaign_weights()). Class campaigns share maps: weight them by 1 / layout group size so a
  layout used by 3 classes counts once.
"""
import json, os, re, sqlite3
from collections import defaultdict
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DB_PATH = os.path.join(REPO, "corpus", "out", "nox_corpus.db")
OUT = os.path.join(HERE, "out")
SECTIONS = os.path.join(HERE, "sections")
CELL = 23

WALL_NEIGHBOURS = {"TL": (-1, -1), "TR": (1, -1), "BL": (-1, 1), "BR": (1, 1)}
EDGE_SIDES = {"E": (1, -1), "N": (-1, -1), "S": (1, 1), "W": (-1, 1)}
EDGE_TIPS = {"NE": (0, -2), "NW": (-2, 0), "SE": (2, 0), "SW": (0, 2)}
FACING_NAMES = {0: "/ run", 1: "\\ run", 2: "cross", 3: "T (south)", 4: "T (east)", 5: "T (north)",
                6: "T (west)", 7: "corner SW", 8: "corner NW", 9: "corner NE", 10: "corner SE"}


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


@lru_cache(None)
def map_categories():
    with db() as c:
        return {r["name"]: r["category"] for r in c.execute("SELECT name, category FROM maps")}


CAMPAIGN_RX = re.compile(r"^(con|war|wiz)\d\d[a-z]$", re.I)


def is_campaign(name):
    """Westwood's campaign maps are exactly Con/War/Wiz + chapter + part (Con01A, War03b, Wiz11A). Not the quest maps
    (G_*), the social maps (So_*) nor the other multiplayer maps: they are other games' maps and are noise for the
    campaign maps we make."""
    return bool(CAMPAIGN_RX.match(name or ""))


@lru_cache(None)
def campaign_weights():
    """THE source of style knowledge: Westwood's campaign maps -> weight 1/layout group size (the three class campaigns
    share most layouts; a layout used by 3 classes counts once). Every rule, baseline and calibration that says what
    Westwood does is measured on these maps only (107 maps, 54.0 layouts). Validity tables (what exists at all: object,
    wall and floor types, pieces that join) may use all_maps()."""
    with db() as c:
        cats = {r["name"]: r["category"] for r in c.execute("SELECT name, category FROM maps")}
        return {r["map"]: 1.0 / r["size"] for r in c.execute("SELECT map, size FROM layout_group")
                if is_campaign(r["map"]) and cats.get(r["map"]) == "campaign"}


def campaign_maps():
    return sorted(campaign_weights())


@lru_cache(None)
def campaign_types():
    """Object types placed in at least one campaign map (anything else is seen only in quest or multiplayer maps)."""
    names = campaign_maps()
    with db() as c:
        return frozenset(r[0] for r in c.execute(
            f"SELECT DISTINCT type FROM objects WHERE map IN ({','.join('?' * len(names))})", names))


def all_maps():
    return sorted(map_categories())


@lru_cache(None)
def things():
    with db() as c:
        return {r["name"]: dict(r) for r in c.execute("SELECT * FROM things")}


@lru_cache(64)
def walls(map_name):
    """(x, y) -> dict(facing, material, variation, minimap, props)."""
    with db() as c:
        return {(r["x"], r["y"]): dict(facing=r["facing"], material=r["material"], variation=r["variation"],
                                       minimap=r["minimap"], props=json.loads(r["props"]) if r["props"] else {})
                for r in c.execute("SELECT * FROM walls WHERE map=?", (map_name,))}


@lru_cache(64)
def tiles(map_name):
    """(x, y) -> dict(material, variation, edges[list of (overlay, variation, dir, edge_type)])."""
    out = {}
    with db() as c:
        for r in c.execute("SELECT * FROM tiles WHERE map=?", (map_name,)):
            out[(r["x"], r["y"])] = dict(material=r["material"], variation=r["variation"], edges=[])
        for r in c.execute("SELECT * FROM edges WHERE map=?", (map_name,)):
            out[(r["x"], r["y"])]["edges"].append((r["overlay"], r["variation"], r["dir"], r["edge_type"]))
    return out


@lru_cache(64)
def objects(map_name, top_level_only=True):
    """List of dicts: type, x, y (world px), extent, team, scr, xtype, class, xfer (dict), id, parent."""
    sql = "SELECT * FROM objects WHERE map=?" + (" AND parent IS NULL" if top_level_only else "")
    with db() as c:
        return [dict(r, xfer=json.loads(r["xfer"]) if r["xfer"] else {}) for r in c.execute(sql, (map_name,))]


def tile_center_cell(x, y):
    """Visual centre of floor tile (x, y), in grid cells."""
    return x + 1, y + 1


def obj_cell(o):
    """Grid cell containing an object."""
    return int(o["x"] // CELL), int(o["y"] // CELL)


def tile_under(map_name, px, py):
    """Floor tile whose visual centre is nearest to a world-pixel point (None if no tile nearby)."""
    t = tiles(map_name)
    cx, cy = px / CELL, py / CELL
    best, bd = None, 9.0
    for x in range(int(cx) - 3, int(cx) + 2):
        for y in range(int(cy) - 3, int(cy) + 2):
            if (x, y) in t:
                d = (x + 1 - cx) ** 2 + (y + 1 - cy) ** 2
                if d < bd: best, bd = (x, y), d
    return best


def wcount():
    return defaultdict(float)


def save_json(name, data):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)


def save_section(name, text):
    os.makedirs(SECTIONS, exist_ok=True)
    with open(os.path.join(SECTIONS, name), "w", encoding="utf-8") as f:
        f.write(text)
