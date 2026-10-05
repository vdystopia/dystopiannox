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
import collections, math, random, re, zlib
from collections import Counter, deque

from nox import load_rules, CELL
from kit.model import Room
from kit.identity import ROOMS as ROOM_IDENTITY, ROOM_COVER, ROOM_COVER_DEFAULT

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


_SOLID = None


def _solid_types():
    """The object types that stop a walking player, as the checker counts them (validate/mapdata.py blocking): an
    obstacle or immobile thing with a footprint that collides. Stools are SIMPLE things a player pushes aside, so
    they cover no floor (a dining hall seated on stools read 17.7% full to the furnisher and 15% to the checker)."""
    global _SOLID
    if _SOLID is None:
        import sqlite3, os
        db = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "corpus", "out", "nox_corpus.db")
        with sqlite3.connect(db) as con:
            _SOLID = {n for n, e, ex, ey, cls, fl in con.execute("SELECT name, ext, ex, ey, class, flags FROM things")
                      if e and e != "NULL" and max(ex or 0, ey or 0) > 0 and ("OBSTACLE" in (cls or "") or
                      "IMMOBILE" in (cls or "")) and "NO_COLLIDE" not in (fl or "")}
    return _SOLID


# Object-name prefixes that belong to other cultures/areas; excluded per style so a town house
# does not get Land-of-the-Dead sconces or ogre stools.
STYLE_EXCLUDE = {
    "town": r"^(LOTD|Ogre|Urchin|DunMir|Crypt|Lich|Horrendous|Mine|Galava|Teepee|Sewer|Pulley|Torture|Coffin|Tomb)|(?<!Bone)(?<!Skull)Immobile$|Fallen|Broken|Movable|Shadow$|Empty",
    "dunmir": r"^(LOTD|Ogre|Urchin|Crypt|Lich|Horrendous|Mine|Teepee|Sewer|Pulley|Torture)|(?<!Bone)(?<!Skull)Immobile$|Fallen|Broken|Movable|Shadow$",
    "mine": r"^(LOTD|Ogre|Urchin|DunMir|Crypt|Lich|Horrendous|Galava|Teepee|Sewer|Torture|Coffin|Tomb)|(?<!Bone)(?<!Skull)Immobile$|Fallen|Broken|Movable|Shadow$|Empty",
    "lotd": r"^(Ogre|Urchin|DunMir|Mine|Teepee|Galava)|(?<!Bone)(?<!Skull)Immobile$|Fallen|Movable|Shadow$",
    "ogre": r"^(LOTD|Urchin|DunMir|Crypt|Lich|Galava|Teepee)|(?<!Bone)(?<!Skull)Immobile$|Movable|Shadow$",
}
# Damaging flame objects (they hurt players; rules: lighting.visible_sources) are never used indoors.
DANGEROUS = re.compile(r"Flame(?!Basin)")
# The walls the camera looks at across a room (NW and NE): Westwood stands most wall pieces there
# (fireplaces 87%, beds 79%, chests 74%, stoves 77%).
BACK_SIDES = ("/|BR", "\\|BL")
# pieces that line a wall, as the room score counts them (review/roomscore.py imports this list): shelves, desks, hearths,
# stoves, chests, beds, benches, racks
TALL_PIECES = re.compile(r"^(Bookcase|PotionShelves|LogShelves|TraderShelves|TraderHelmShelf|Desk\d|Fireplace|WallFireplace|"
                  r"Stove0|Cauldron|CinderBin|Bellows|AlchemistDesk|WizardWorkstation|Chest\d|DunMirChest|Bed\d|WoodBed|Cot\d|Bench|"
                  r"LightBench|CushionedBench|TraderPoleArm|TraderArmorRack|TraderBowRack|TraderClothesRack|TraderQuiverRack)")
LINED_GOAL = 0.38            # share of the NE and NW walls to line (the room score asks 35%)
# what may top a room up to its coverage target, one piece at a time against a wall: never shelves (a lone shelf breaks
# a lined wall) or tables (a table stands with its seats)
TOP_UP_FAMS = ("storage", "bench", "plant", "lab", "statue")      # not stoves: a hearth or stove is an anchor with room round it
# The user's frame of reference (TreePlace v0.3 room review): the NE wall is the top right of a room on screen, the
# NW wall the top left, the SE wall the bottom right and the SW wall the bottom left. In the code's terms
# NW = '/|BR', NE = '\\|BL', SE = '/|TL', SW = '\\|TR'.
WALL_NAME = {"/|BR": "NW", "\\|BL": "NE", "/|TL": "SE", "\\|TR": "SW"}
# The camera looks at a room from the south: it sees the front of what stands against the NE and NW walls, and only
# the back of what stands against the SE and SW walls, or nothing where the wall hides it. House rule of very high
# priority (TreePlace v0.3 room review): pieces with a face (shelves, hangings, hearths, stoves, desks, chests) go on
# the NE and NW walls only; pieces without one (barrels, crates, sacks, benches, carts, racks) take the SE and SW
# walls first; free-standing furniture leans toward the SE and SW walls, leaving the back walls to what faces the room.
FACING_FAMS = {"shelves", "wall_decor", "fireplace", "stove", "desk", "counter_shop", "forge", "bellows", "lab"}
FACING_TYPES = re.compile(r"^(Chest\d|Chest[NS][EW]|DunMirChest\d|TraderShelves\d|TraderHelmShelf\d|TraderHanging|"
                          r"TraderShieldWallHanging|TraderCrossedWeapons|ClothSign)")
FRONT_FAMS = {"bench", "storage", "shop_rack", "cart"}
FRONT_WEIGHT = 1.8                # how strongly free-standing furniture leans toward the SE and SW walls
# Pieces that stand tall against their wall: hangings never go above them (above a chest, a bed or a bench they may).
TALL_FAMS = {"shelves", "fireplace", "stove", "desk", "shop_rack", "counter_shop", "lab", "forge"}
# How far a wall piece's back stands from its wall's line (uv units): Westwood's snug p25-p50 (bookcases 0.15-0.33,
# chests 0.21-0.34, desks 0.25-0.42, fireplaces 0.13-0.22, beds 0.18-0.40). TreePlace v0.3 room review: a chest
# 1.1 units off the NW wall seemed to sit in the middle of the room.
SNUG_GAP = {"shelves": 0.18, "storage": 0.22, "desk": 0.25, "fireplace": 0.15, "stove": 0.2, "bed": 0.28,
            "nightstand": 0.22, "bench": 0.28, "counter_shop": 0.25, "shop_rack": 0.22, "lab": 0.25}
# Carpets of floor tiles (Con07B lays them in 13 of its 28 rooms: RugRed, RugGreen, RugBlueNorm, RugBrown and tan
# tiles), with the gold trim Westwood draws round them (RugTanLightEdge: 100% of RugRed onto GalavaBrick). Built
# floors only: Westwood never lets carpet touch dirt, grass or cobbles (floors.json never_touch).
CARPET_EDGE = "RugTanLightEdge"
CARPET_FLOORS = re.compile(r"Wood|Oak|Redwood|Slat|Plank|Marble|Brick|Tile|Stone")
# Gear racks that stand in rows down the middle of a storeroom, one kind to a row (TreePlace v0.3 room review).
RACKS_PER_ROW = 5
RACK_KINDS = {"gear": (r"^TraderArmorRack[12]$", r"^TraderPoleArm[1-4]$", r"^TraderClothesRack[12]$", r"^TraderBowRack[12]$"),
              "hunt": (r"^TraderBowRack[12]$", r"^TraderQuiverRack$", r"^TraderClothesRack[12]$"),
              "mine": (r"^TraderPoleArm[1-4]$", r"^TraderArmorRack[12]$"),
              "books": (r"^Bookcase[12]$", r"^Bookcase[12]HalfFull$"),   # library stacks: the variants whose front shows
              "columns": (r"^Column[5-8]$",), "cathedral": (r"^CathedralColumn[123]$",),
              "tombs": (r"^Crypt(1|3|5|6|7|8|9|10|11|12)$", r"^Coffin[1-4]$"),
              "lotd_tombs": (r"^LOTDTombstone[1-4]$",), "obelisks": (r"^LOTDManaObelisk$",)}
# Each building keeps one furnishing palette (its chairs, stools, benches, tables, carpets, hangings and plants), so
# its rooms belong together while the buildings of a map differ (TreePlace v0.3 used too few of the game's types).
PALETTES = dict(chair=("WoodenChair", "DarkWoodenChair", "OldDarkWoodenChair"), stool=("Stool", "CushionedStool"),
                bench=("Bench", "LightBench", "CushionedBench"),
                table=(r"^Table[1-4]$", r"^RoundTable[1-3]$", r"^SquareTable[1-3]$", r"^OvalTable[12]$"),
                carpet=(("RugRed", "RugGreen"), ("RugBlueNorm", "RugRed"), ("RugBrown", "RugTanLightNorm"), ("RugGreen", "RugBrown")),
                decor=(("trophies", "green"), ("trophies", "red"), ("blue", "paintings"), ("white", "trophies"), ("arms", "trophies")),
                plant=(r"^(Plant4|Plant5)$", r"^(Plant1|Plant3|Plant5)$", r"^(Plant3|Plant4)$"))
# Houses are lit with candelabras and hearths, never open torches. Westwood's log cabins: 15 of 30 lights are
# candelabras and 5 are fireplaces; stucco houses: 28 of 46 candelabras. Torches belong to dungeons and mines
# (DungeonStone rooms hold 140 of their 199 lights). The TreePlace playtest found torch flames indoors
# unrealistic, and standing torches by a wall do not look mounted on it.
HOUSE_WALLS = re.compile(r"^(Log|Stucco|Brick|StoneGray|StoneBlue|Galava|Cobblestone|FieldStone|Dilapidated)")
STONE_WALLS = re.compile(r"^(Brick|StoneGray|StoneBlue|Galava|Cobblestone|FieldStone)")
HOUSE_LIGHTS = {"wood": {"Candleabra1": 3, "Candleabra2": 1}, "stone": {"Candleabra3": 3, "Candleabra5": 2, "Candleabra1": 1}}
# Families numbered by wall in a third way, measured on Westwood's maps: log shelves 3 stand on the NW wall
# (36 of 47 uses), 4 on the NE wall (44 of 54), 2 on the SE wall (11 of 16) and 1 on the SW wall (3 of 4).
# Cots are numbered by where the pillow is (read off the sprites): Cot1 head NW, Cot2 NE, Cot3 SE, Cot4 SW, the
# same as WoodBed. Westwood often stands cots sideways along a wall, so its wall sides would number them
# the other way and put the headboard away from the wall (TreePlace v0.2 room review).
NUMBERING_OVERRIDES = {"LogShelvesFull": {"1": "\\|TR", "2": "/|TL", "3": "/|BR", "4": "\\|BL"},
                       "LogShelvesEmpty": {"1": "\\|TR", "2": "/|TL", "3": "/|BR", "4": "\\|BL"},
                       "Cot": {"1": "/|BR", "2": "\\|BL", "3": "/|TL", "4": "\\|TR"}}
# Pieces the generator keeps off rugs altogether (TreePlace v0.2 room review: a table half on a rug; a bearskin's
# ragged outline reaches under a table even when the table's box lies within the rug's). Chairs may stand partly
# on a rug, as Westwood's often do.
RUG_WHOLE = {"table", "desk", "bed"}
# Fires draw far wider than their footprint: supplies keep this many units from a hearth or a cauldron.
FIRE_PAD = 2.4
# Rugs draw wider than their footprint too: tables keep this far off them. A bearskin's head and legs reach about
# 1.2 units past its box (measured on the TreePlace v0.3 bedroom), a woven rug's edge less.
def _rug_margin(t):
    return 2.0 if t.startswith("BearskinRug") else 0.8
# Supplies stocked along the walls; everything else blocking is an anchor they keep clear of on every side
# (TreePlace v0.2 room review: the apple crate crowding the cauldron from the next wall).
SUPPLY_FAMS = {"storage", "shelves", "shop_rack"}
# Rooms that get hangings on their back walls (trophies, tapestries, paintings).
DECORATED = {"living_room", "bedroom", "study", "herbalist", "mess_hall", "dining_hall", "tavern", "barracks", "dwelling",
             "library", "shop"}
# One theme of hangings per room (a room of mixed trophies, tapestries and paintings reads as random): hunting
# trophies, tapestries of one colour, or paintings. Stone houses lean to tapestries and paintings, wooden ones to
# trophies. Hangings keep DECOR_GAP units apart along a wall.
DECOR_THEMES = {"trophies": r"^WallTrophy(Bear|Moose|MountainLion|Bull)[12]$", "blue": r"^BlueTapestry\d$",
                "green": r"^GreenTapestry\d$", "red": r"^RedTapestry\d$", "white": r"^WhiteTapestry\d$",
                "paintings": r"^Painting[12]$", "arms": r"^(TraderShieldWallHanging[1-6]|TraderCrossedWeapons[1-6])$"}
# a culture's own hangings, before any of the themes above (rules/out/cultures.json: the Land of the Dead's tapestries on
# the back walls, Dun Mir's shields, the skulls an ogre nails up)
CULTURE_DECOR = {"lotd": r"^LOTDTapestry[12]$", "dunmir": r"^DunMirHangingShield\d+$", "ogre": r"^OgreHutWallSkull[1-4]$"}
DECOR_GAP = 3.0
# Free-standing groups for the open floor of bigger rooms (TreePlace v0.3/v0.4 room reviews: the middle of a room read
# as empty; tables, chairs and other free pieces lean toward the room's front, its S and W corners). anchor: the
# piece's types; seats (min, max) of `seat` round it (fewer than min and the group goes); rug: chance of a rug under
# it; beside (pattern, n): pieces set close by; pair: a twin mirrored along the room's long axis; clear: room kept
# round it.
GROUPS = {
    "dining": dict(anchor=r"^RoundTableWithFood$|^RoundTable[123]$|^OvalTable[12]$", seats=(2, 4), seat="chair", rug=0.35),
    "feast": dict(anchor=r"^RoundTableWithFood$", seats=(2, 4), seat="chair"),
    "worktable": dict(anchor=r"^Table[1-4]$", seats=(1, 2), seat="chair",
                      beside=(r"^TraderAppleCrate$|^Barrel2?$|^SackChestMedium[12]$|^Crate[12]$", 2)),
    "sitting": dict(anchor=r"^SmallTable2$|^SquareTable[12]$|^RoundTable[12]$", seats=(2, 3), seat="chair", rug=0.8),
    "curio": dict(anchor=r"^Telescope2[a-g]$|^Orrery2$|^SentryGlobeMovable$", clear=1.0),
    "statues": dict(anchor=r"^Statue2[aceg]$", pair=True, clear=1.0),
    "hearth": dict(anchor=r"^FreestandingFireplace$", seats=(2, 4), seat="bench", clear=1.0),
    "carts": dict(anchor=r"^MineManaCart[12]$|^MineOreCart[12]$", clear=0.9, beside=(r"^BarrelWithTools[12]$|^DarkCrate[12]$", 1)),
    # the cultures' rooms (rules/out/cultures.json): an ogre den's fire pit ringed by stools, an ogre feast's crude
    # tables, the Land of the Dead's judgement balances standing in pairs
    "firepit": dict(anchor=r"^OgreFirePit$", seats=(2, 4), seat="chair", clear=1.2),
    "ogre_table": dict(anchor=r"^OgreTable[123]$", seats=(2, 3), seat="chair"),
    "balances": dict(anchor=r"^LOTDJudgementBalance[12]$", pair=True, clear=1.0),
}
# Pieces that need the space before them (the checker's NEEDS_FRONT): chests to open, hearths, stoves, cauldrons.
NEEDS_FRONT = re.compile(r"^Chest\d|^Chest[NS][EW]$|^DunMirChest|Fireplace|^Stove|^Cauldron|^CinderBin")
FRONT_BLOCKERS = {"table", "desk", "bed", "counter_bar", "counter_shop", "stove", "shelves", "chair", "bench"}
FRONT_CLEAR = {"stove": 1.4, "fireplace": 2.0}   # the space a core piece keeps clear before it when it is placed late
# Supplies stocked along a storeroom's or kitchen's walls, in tidy groups: (types, fewest, most pieces in a group).
SUPPLIES = {"shelves": (r"^LogShelvesFull[1-4]$", 1, 2),
            "crates": (r"^(DarkCrate|Crate)[12]$", 1, 2),
            "barrels": (r"^(Barrel|Barrel2|WaterBarrel|PiledBarrels[1-4]|LargeBarrel[12])$", 2, 3),
            "sacks": (r"^SackChest(Large|Medium|Small)[12]$", 2, 3),
            "apples": (r"^TraderAppleCrate$", 1, 2),
            "tools": (r"^BarrelWithTools[12]$", 1, 2)}
PILE = r"^(Barrel|Barrel2|WaterBarrel|SackChest(Large|Medium)[12])$"     # round pieces that heap in a corner
# Shelves and desks face one way and have no corner pieces: they stop at the corner, tight against the wall across
# its end, whose line is 1 unit past the run's end (2026-10-04 review: "make sure bookcases and shelves fit tight
# against corners"; TreePlace v0.2 had kept them 2.2 units out, which left a gap in every corner).
CORNER_CLEAR = 1.05
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


_BLOCKING = None


def _blocking():
    """The furniture families that count as blocking pieces (rules/room_types.py BLOCKING_FAMILIES)."""
    global _BLOCKING
    if _BLOCKING is None:
        import os
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "rules", "room_types.py")
        src = open(p, encoding="utf-8").read()
        start = src.index("BLOCKING_FAMILIES = ")
        _BLOCKING = eval(src[start + len("BLOCKING_FAMILIES = "):src.index("}", start) + 1])
    return _BLOCKING


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
        # u - v grows toward the room's S corner (screen y): the front, between the SE and SW walls
        self.front_lo = min(2 * y + 1 for _, y in cells); self.front_hi = max(2 * y + 1 for _, y in cells)
        # wall runs adjacent to the room
        near = {(x + dx, y + dy) for (x, y) in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)} & set(walls)
        runs = {}
        for (x, y) in near:
            for line, nbs in (("/", ((1, -1), (-1, 1))), ("\\", ((1, 1), (-1, -1)))):
                if any((x + a, y + b) in walls for a, b in nbs) or walls[(x, y)].get("facing") in ((0,) if line == "/" else (1,)):
                    coord = x + y + 1 if line == "/" else x - y
                    along = x - y if line == "/" else x + y + 1
                    runs.setdefault((line, coord), []).append(along)
        # a wall line broken by an opening into another part of the same room (an L or T room whose wing joins it) is
        # two runs, not one across the opening; a doorway does not break its wall's run
        door_cells = {d.gap for d in room.doors} | set(getattr(spec, "door_gaps", ()))
        doors_on = collections.defaultdict(set)
        for (x, y) in door_cells:
            doors_on[("/", x + y + 1)].add(x - y)
            doors_on[("\\", x - y)].add(x + y + 1)
        self.runs = []
        for (line, coord), alongs in runs.items():
            if line == "/": side = "BR" if cu > coord else "TL"
            else: side = "TR" if cv > coord else "BL"
            al = sorted(set(alongs))
            segs, cur = [], [al[0]]
            for a in al[1:]:
                if a - cur[-1] <= 2 or all(g in doors_on[(line, coord)] for g in range(cur[-1] + 2, a, 2)): cur.append(a)
                else: segs.append(cur); cur = [a]
            segs.append(cur)
            for seg in segs:
                self.runs.append(dict(line=line, coord=coord, lo=seg[0] - 1, hi=seg[-1] + 1, side=f"{line}|{side}",
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

    def front(self, u, v):
        """How far toward the SE and SW walls a point lies: 0 at the room's N corner, 1 at its S corner."""
        return ((u - v) - self.front_lo) / max(1.0, self.front_hi - self.front_lo)

    def before_back_wall(self, u, v, depth=0.3):
        """False if the point's grid cell is a wall cell, unless it stands in front of a NE or NW wall at least `depth`
        units into the room: the game draws it in front of that wall (Westwood's snug chests and desks often stand
        so); against a SE or SW wall the wall is drawn over it. Both cells count when the point lies on a cell edge
        (the position is rounded when the map is written)."""
        cells = {(math.floor((u + v) / 2 + ex), math.floor((u - v) / 2 + ey)) for ex in (-0.01, 0.01) for ey in (-0.01, 0.01)}
        for (x, y) in cells & self.wall_cells:
            runs = [r for r in self.runs if r["coord"] == (x + y + 1 if r["line"] == "/" else x - y)]
            if not runs: return False
            for r in runs:
                off = ((u if r["line"] == "/" else v) - r["coord"]) * r["sign"]
                if r["side"] not in BACK_SIDES or off < depth: return False
        return True

    def fits(self, u, v, hu, hv, blocking=True, wall_ok=False, wall_min=0.25, touch=False):
        pts = [(u + a * hu, v + b * hv) for a in (-1, 0, 1) for b in (-1, 0, 1)]
        if not all(self.inside(*p) for p in pts): return False
        if not wall_ok and min(self.wall_dist(*p) for p in pts) < wall_min: return False
        if not wall_ok and not self.before_back_wall(u, v): return False
        if blocking:
            for du, dv in self.doors:
                if math.hypot(u - du, v - dv) < DOOR_CLEAR + max(hu, hv): return False
            for (u0, u1, v0, v1) in self.zones:          # never in front of another piece
                if u + hu > u0 and u - hu < u1 and v + hv > v0 and v - hv < v1: return False
        for (pu, pv, phu, phv, pb, player) in self.placed:
            if pb != blocking or (player == "wall") != wall_ok:
                continue                 # rugs under furniture and wall hangings above it may overlap
            gap = 0.02 if touch else 0.15     # shelves lining a wall touch end to end
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
        self.composing = False
        self.ceiling = None       # most furniture for the room: Westwood's p95 of the kind and size (the checker's limit)
        self.style = style
        self._seated = set()
        self.anchors = []         # (u, v) of the pieces composed so far (to spread the next ones)
        self._placed_of = {}      # id(object) -> its footprint record in g.placed
        self._typed = []          # (type, footprint record) of every piece placed
        self._rug_under = {}      # id(rug record) -> the table record it is centred under
        self._lined = set()       # (line, coord) of the wall runs lined with shelves
        self.carpet_boxes = []    # uv boxes of the carpets laid
        self.light_zones = []     # the space before chests, hearths and stoves: no candelabra stands there
        self._deferred_decor = 0  # hangings the composition called for, put up after the walls are lined
        self._line_blocks = {}    # (line, coord) -> [(along0, along1)] of the rows of shelves lining that wall
        self._rack_centres = set()  # the rows of racks standing free: their centre lines across the room
        self.wall_used = []       # ((line, coord), a0, a1): wall stretches pieces already stand against
        self.wall_tall = []       # the same for tall pieces only (shelves, hearths): hangings keep off them
        self.carpet_plan = None   # the room's carpet step when it lays carpet tiles instead of rug objects
        self.cover_target, self.cover_max = ROOM_COVER.get(self.kind, ROOM_COVER_DEFAULT)
        # the building's palette: the same for every room of one building (its id seeds it), differing between buildings
        prng = random.Random(zlib.crc32(f"{spec.d.get('name')}:{getattr(room, 'building', '')}".encode()))
        self.palette = {k: prng.choice(v) for k, v in PALETTES.items()}

    # ---- helpers -----------------------------------------------------------------------
    def half(self, t):
        ext, ex, ey, _ = self.things.get(t, ("CIRCLE", 10, 0, ""))
        if ext == "BOX": return ex / 2 / K, ey / 2 / K
        return ex / K, ex / K

    def ok_type(self, t):
        return t in self.things and not self.exclude.search(t) and not DANGEROUS.search(t)

    def footprint(self, t):
        """Floor area a piece covers, in square uv units."""
        ext, ex, ey, _ = self.things.get(t, ("CIRCLE", 10, 0, ""))
        return (ex * ey if ext == "BOX" else math.pi * ex * ex) / (K * K)

    def coverage(self, extra=0.0):
        """Share of the room's floor its furniture covers (as the checker measures it: blocking furniture families;
        a grid cell is 2 square uv units)."""
        area = sum(self.footprint(t) for t, rec in self._typed if rec[4] and rec[5] != "wall" and _family_of(t) in _blocking()
                   and t in _solid_types())
        return (area + extra) / (2.0 * max(1, len(self.g.cells)))

    def put(self, t, u, v, blocking=True, layer="floor", **extra):
        hu, hv = self.half(t)
        rec = (u, v, hu, hv, blocking, layer)
        self.g.placed.append(rec)
        if blocking and not self.placing_light: self.n_blocking += 1
        x, y = _px(u, v)
        o = self.spec.obj_px(t, x, y, **extra)
        self.objects.append(o)
        self._placed_of[id(o)] = rec
        self._typed.append((t, rec))
        return o

    def _remove(self, o):
        """Takes a placed piece out again (part of a group that could not be completed)."""
        rec = self._placed_of.pop(id(o), None)
        self._typed = [tr for tr in self._typed if tr[1] is not rec]
        if rec is not None:
            for k in range(len(self.g.placed) - 1, -1, -1):
                if self.g.placed[k] is rec: del self.g.placed[k]; break
            if rec[4] and not self.placing_light: self.n_blocking -= 1
        for seq in (self.objects, self.spec.d["objects"]):
            for k in range(len(seq) - 1, -1, -1):
                if seq[k] is o: del seq[k]; break

    def try_put(self, t, u, v, blocking=True, wall_ok=False, layer="floor", snug=False, touch=False, **extra):
        # hard cap on furniture (Westwood density for the room kind); essentials and lights are exempt
        if blocking and not self.placing_light and not self.in_required and self.n_blocking >= self.cap:
            return None
        if blocking and not self.placing_light and self.ceiling and self.n_blocking >= self.ceiling:
            return None
        # composed rooms: never past the share of the floor the room's kind may cover (kit/identity.py ROOM_COVER)
        if blocking and not self.placing_light and self.composing and _family_of(t) in _blocking() and \
                self.coverage(self.footprint(t)) > self.cover_max:
            return None
        hu, hv = self.half(t)
        if not self.g.fits(u, v, hu, hv, blocking, wall_ok, wall_min=0.1 if snug else 0.25, touch=touch): return None
        fam = _family_of(t)
        if fam in RUG_WHOLE or fam == "rug":           # tables, desks and beds stay off rugs
            for tt, rec in self._typed:
                f2 = _family_of(tt)
                if fam in RUG_WHOLE and f2 == "rug": mg = _rug_margin(tt)
                elif fam == "rug" and f2 in RUG_WHOLE: mg = _rug_margin(t)
                else: continue
                if self._overlap(u, v, hu + mg, hv + mg, rec): return None
        if blocking and not self.g.reachable_ok((u, v, hu, hv, True, layer)): return None
        return self.put(t, u, v, blocking, layer, **extra)

    @staticmethod
    def _overlap(u, v, hu, hv, rec):
        pu, pv, phu, phv = rec[:4]
        return min(u + hu, pu + phu) - max(u - hu, pu - phu) > 0.05 and min(v + hv, pv + phv) - max(v - hv, pv - phv) > 0.05

    @staticmethod
    def _half_on(u, v, hu, hv, rug):
        """True if the piece at (u, v) overlaps the rug without lying wholly on it."""
        gu, gv, ghu, ghv = rug[:4]
        if min(u + hu, gu + ghu) - max(u - hu, gu - ghu) <= 0.05 or min(v + hv, gv + ghv) - max(v - hv, gv - ghv) <= 0.05:
            return False
        return not (u - hu >= gu - ghu - 0.05 and u + hu <= gu + ghu + 0.05 and v - hv >= gv - ghv - 0.05 and v + hv <= gv + ghv + 0.05)

    def _clear_of_anchors(self, u, v, hu, hv, pad):
        """True if a supply at (u, v) keeps `pad` units from every placed piece that is not itself a supply (the
        cauldron, the hearth, a table, a bed), on any side."""
        for tt, (pu, pv, phu, phv, pb, layer) in self._typed:
            f = _family_of(tt)
            if not pb or layer == "wall" or f in SUPPLY_FAMS: continue
            need = max(pad, FIRE_PAD) if f in ("stove", "fireplace") else pad
            if max(abs(u - pu) - hu - phu, abs(v - pv) - hv - phv) < need: return False
        return True

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
            runs = [r for r in self.g.runs if r["hi"] - r["lo"] >= 2 and (side_pref is None or r["side"] == side_pref)
                    and (fam not in FACING_FAMS or r["side"] in BACK_SIDES)]
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
            if FACING_TYPES.match(t) and r["side"] not in BACK_SIDES: continue
            hu, hv = self.half(t)
            along_half = hv if r["line"] == "/" else hu
            span = (r["lo"] + along_half + 0.3, r["hi"] - along_half - 0.3)
            if span[0] > span[1]: continue
            perp_half = hu if r["line"] == "/" else hv
            d = perp_half + SNUG_GAP.get(fam, 0.3) if fam != "wall_decor" else self.perp_for(t, inv.get("perp_px"))
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
                                 layer="wall" if fam == "wall_decor" else "floor", snug=fam != "wall_decor")
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
        base = base or self.palette_seat(seat_fam, types) or _base(_pick(self.rng, types))
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

    def palette_seat(self, seat_fam, types):
        """The building's own seat for this room (its chair, stool or bench), where the room's identity allows it."""
        bases = {_base(t) for t in types}
        allow = ROOM_IDENTITY.get(self.kind, {}).get("types", {}).get(seat_fam)
        keys = ("bench",) if seat_fam == "bench" else ("stool", "chair") if bases <= {"Stool", "CushionedStool"} else ("chair",)
        for key in keys:
            b = self.palette[key]
            if b in self.chair_facing and self.ok_type(b + "1") and (not allow or re.search(allow, b + "1")):
                return b
        return None

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
            if f in ident.get("per_tiles", {}):            # big rooms get more (a tavern: a table per 35 tiles), past
                by_size = int(len(self.room.tiles) / ident["per_tiles"][f])   # Westwood's range in rooms bigger
                n, hi = max(n, by_size), max(hi, by_size)                      # than Westwood's
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
            self.composing = True                        # the room's coverage limit holds instead (ROOM_COVER)
            self.compose(plan, need)
            self.fill_room()
            self.line_backs()
            self.complete_bookcase_walls()
            for _ in range(self._deferred_decor): self.place_decor()
            if self.kind in DECORATED: self.decorate_walls()
            while self.line_family() and self.back_lined() < LINED_GOAL and self.place_decor(): pass
            self.audit_rugs()
            self.in_required = self.composing = False
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
    def segments(self, pad=0.0, tall_only=False):
        """Free stretches of every wall: the run minus door openings (with room to pass) and the
        stretches pieces already stand against, `pad` units round them besides; with tall_only, minus the
        stretches of tall pieces only (hangings may go above a chest or a bed). [(run, lo, hi)] in the run's
        along coordinate."""
        out = []
        for r in self.g.runs:
            key = (r["line"], r["coord"])
            free = [(r["lo"] + 0.6, r["hi"] - 0.6)]
            cuts = [(a0 - 0.25 - pad, a1 + 0.25 + pad) for k, a0, a1 in (self.wall_tall if tall_only else self.wall_used) if k == key]
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
        facing = fam in FACING_FAMS or bool(FACING_TYPES.match(t0 or ""))
        out = []
        for r, lo, hi in self.segments(tall_only=fam == "wall_decor"):
            back = r["side"] in BACK_SIDES
            if facing and not back: continue                 # the camera would see only its back
            t = self.side_variant(t0, r, fam)
            if not t: continue
            hu, hv = self.half(t)
            ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)      # half-length along the wall / into the room
            if hi - lo < 2 * ha + 0.1: continue
            if fam == "wall_decor": d = self.perp_for(t, inv.get("perp_px"))
            else: d = hp + SNUG_GAP.get(fam, 0.3) + self.rng.uniform(0.0, 0.08)    # snug against the wall
            side_score = (3.0 if back else 0.0) if facing else (0.0 if back else 3.0) if fam in FRONT_FAMS else (1.5 if back else 0.0)
            coord = r["coord"] + r["sign"] * d
            mid = (lo + hi) / 2
            # a stretch can start past the line of the wall across its end (a run reaches one unit beyond the room's
            # corner): pieces keep 0.3 units clear of that wall
            c0, c1 = r["lo"] + 1 + 0.3 + ha, r["hi"] - 1 - 0.3 - ha
            ends = [max(lo + ha + 0.1, c0), min(hi - ha - 0.1, c1)]
            if fam == "wall_decor":                    # a hanging stays well clear of the corners
                k0, k1 = r["lo"] + 1 + 0.8 + ha, r["hi"] - 1 - 0.8 - ha
                if k0 > k1 or hi - ha < k0 or lo + ha > k1: continue
                mid = min(max(mid, k0, lo + ha), k1, hi - ha)
                ends = [min(max(e, k0), k1) for e in ends]
            if at == "room_corner":                    # only where the stretch meets the next wall
                ends = [e for e, edge in ((ends[0], lo - r["lo"]), (ends[1], r["hi"] - hi)) if edge < 1.6]
                ends = [e for e in ends if lo + ha - 0.05 <= e <= hi - ha + 0.05]
                if not ends: continue
            if fam in ("shelves", "desk", "shop_rack"):        # they face one way and are no corner pieces
                ends = [max(lo, r["lo"] + CORNER_CLEAR) + ha, min(hi, r["hi"] - CORNER_CLEAR) - ha]
                if ends[0] > ends[1]: continue
                mid = min(max(mid, ends[0]), ends[1])
            spots = [mid] if at == "center" else ends if at in ("corner", "room_corner") else [mid] + ends
            for a in spots:
                u, v = (coord, a) if r["line"] == "/" else (a, coord)
                spacing = min([math.hypot(u - au, v - av) for au, av in self.anchors] or [8.0])
                score = side_score + 2.0 * min(spacing, 8.0) / 8.0 + 0.05 * (hi - lo) + self.rng.uniform(0, 0.4)
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

    def _front_crowded(self, r, u, v, ha, hp):
        """True if a table, desk, bed, counter, stove, shelf, seat or floor light already stands in the space before a
        piece at (u, v) that needs it (a chest, hearth, stove or cauldron): 2.6 units deep from its centre, as the
        checker looks (validate/checks.py NEEDS_FRONT)."""
        # in a corner a piece stands against two walls, and the checker may take either as its back (a cauldron is
        # round): the space before it is kept clear from both
        walls = [r] + [rr for rr in self.g.runs if rr is not r and
                       abs((u - rr["coord"]) if rr["line"] == "/" else (v - rr["coord"])) <= hp + 0.6 and
                       rr["lo"] - 0.5 <= (v if rr["line"] == "/" else u) <= rr["hi"] + 0.5]
        for w in walls:
            z = self.front_zone(w, u, v, max(0.8, ha) + 0.3, 0.4, 2.2)
            for tt, (pu, pv, phu, phv, pb, layer) in self._typed:
                if not pb or layer == "wall": continue
                if _family_of(tt) in FRONT_BLOCKERS or re.search(r"Candleabra|Candelabra|^TorchPole|Lantern\d$", tt):
                    if z[0] <= pu <= z[1] and z[2] <= pv <= z[3]: return True
        return False

    def place_on_wall(self, fam, at="center", clear=1.6, t0=None):
        """One piece against a wall at the best composed position, with `clear` uv units kept free in
        front of it (nothing blocking may stand there later; it must be free now)."""
        t0 = t0 or _pick(self.rng, self.types_of(fam))
        if not t0: return None
        for score, t, r, u, v, a, ha, hp in self.wall_candidates(fam, t0, at):
            zone = self.front_zone(r, u, v, ha, hp, clear) if clear else None
            if zone and self.g.zone_blocked(zone): continue
            if NEEDS_FRONT.search(t) and self._front_crowded(r, u, v, ha, hp): continue
            o = self.try_put(t, u, v, blocking=fam not in NON_BLOCKING, snug=True)
            if not o: continue
            if zone: self.g.zones.append(zone)
            if NEEDS_FRONT.search(t): self.light_zones.append(self.front_zone(r, u, v, ha + 0.3, hp, 2.6))
            self.anchors.append((u, v))
            self.wall_used.append(((r["line"], r["coord"]), a - ha, a + ha))
            if fam in TALL_FAMS: self.wall_tall.append(((r["line"], r["coord"]), a - ha, a + ha))
            return dict(obj=o, run=r, uv=(u, v), along=a, ha=ha, hp=hp)
        return None

    def place_rug(self, r, depth_from, along, types=None):
        """A rug laid along wall run r, its near edge `depth_from` units from the wall line, centred at `along`:
        the room's chosen design first, then the others (a woven rug where a bearskin's legs would reach the
        furniture), sliding a little along the wall. Returns the rug or None."""
        types = types or self.types_of("rug")
        if not types or self.carpet_plan: return None
        first = _pick(self.rng, types)
        order = [first] + sorted((t for t in types if t != first), key=lambda t: (_rug_margin(t), self.half(t)[0] * self.half(t)[1]))
        for t0 in order:
            t = self.orient(t0, r["side"]) or t0
            rhu, rhv = self.half(t)
            rp = rhu if r["line"] == "/" else rhv
            for slide in (0.0, 0.6, -0.6, 1.2, -1.2):
                o = self.try_put(t, *self._uv_on(r, depth_from + rp, along + slide), blocking=False)
                if o: return o
        return None

    def rug_under(self, table, uv):
        """A woven rug centred under a round or square table, a margin wider than the table all round: the
        table set reads as one piece in the middle of the room (TreePlace v0.2 room review: a table half on a
        rug looked wrong; centred on it, it is a composition). Returns the rug or None."""
        rec_t = self._placed_of.get(id(table))
        if rec_t is None or self.carpet_plan: return None
        thu, thv = rec_t[2], rec_t[3]
        if abs(thu - thv) > 0.3: return None              # long tables are wider than any rug
        for t in self.rng.sample(["RedRug1", "RedRug2", "RedRug3", "RedRug4"], 4):
            if not self.ok_type(t): continue
            rhu, rhv = self.half(t)
            if rhu < thu + 0.2 or rhv < thv + 0.2: continue
            u, v = uv
            if not self.g.fits(u, v, rhu, rhv, blocking=False): continue
            if any(self._overlap(u, v, rhu + 0.8, rhv + 0.8, p) for tt, p in self._typed
                   if p is not rec_t and _family_of(tt) in RUG_WHOLE):
                continue
            o = self.put(t, u, v, blocking=False)
            self._rug_under[id(self._placed_of[id(o)])] = rec_t
            return o
        return None

    def rug_before(self, p):
        """A rug laid out before a piece (a chest, a hearth), its long side along the wall."""
        r = p["run"]
        depth = abs((p["uv"][0] if r["line"] == "/" else p["uv"][1]) - r["coord"]) + p["hp"] + 0.2
        return bool(self.place_rug(r, depth, p["along"]))

    def middle_spots(self, hu, hv):
        """Open spots of the room, best first: farthest from the walls and from what already stands there,
        nearest the middle."""
        cu, cv = self.g.centroid
        blocks = [p for p in self.g.placed if p[4] and p[5] != "wall"]
        out = []
        for (x, y) in self.g.cells:
            u, v = x + y + 1.0, x - y
            if not self.g.fits(u, v, hu, hv): continue
            room = min([self.g.wall_dist(u, v) - max(hu, hv)] +
                       [max(abs(u - b[0]) - b[2] - hu, abs(v - b[1]) - b[3] - hv) for b in blocks])
            out.append((min(room, 3.0) - 0.25 * math.hypot(u - cu, v - cv) + FRONT_WEIGHT * self.g.front(u, v), u, v))
        out.sort(key=lambda s: -s[0])
        return [(u, v) for _, u, v in out]

    def free_middle(self, hu, hv):
        """The open spot of the room farthest from walls and from what already stands there."""
        spots = self.middle_spots(hu, hv)
        return spots[0] if spots else None

    def place_center(self, fam, small=False):
        """One piece standing free in the room, at the best open spot where it may stand (the next best when
        a rug or the room's density rules out the first). Tables come from the building's palette when the room
        allows them; `small`: the smallest type the room allows (a table its seats fit round in a small room)."""
        types = self.types_of(fam)
        if fam == "table":
            own = {t: w for t, w in types.items() if re.match(self.palette["table"], t)}
            types = own or types
        if small and types:
            t = min(types, key=lambda k: (self.footprint(k), k))
        else:
            t = _pick(self.rng, types)
        if not t: return None
        hu, hv = self.half(t)
        pad = 1.4 if fam in ("table", "desk") else 0.0   # room around a table for its seats
        spots = self.middle_spots(hu + pad, hv + pad)[:40] or self.middle_spots(hu, hv)[:40]
        for spot in spots:
            o = self.try_put(t, *spot, blocking=fam not in NON_BLOCKING)
            if o:
                self.anchors.append(spot)
                return o, spot
        return None

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
                if NEEDS_FRONT.search(t): self.light_zones.append(self.front_zone(r, u, v, ta + 0.3, tp, 2.6))
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

    def decor_theme(self):
        """The room's hangings: the identity's own choice, else one theme picked for the room."""
        if not hasattr(self, "_decor_types"):
            own = ROOM_IDENTITY.get(self.kind, {}).get("prefer", {}).get("wall_decor")
            culture = CULTURE_DECOR.get(self.style)
            if own:
                self._decor_types = {t: w for t, w in own.items() if self.ok_type(t)}
            elif culture and any(re.match(culture, t) and self.ok_type(t) for t in self.things):
                self._decor_types = {t: 1 for t in self.things if re.match(culture, t) and self.ok_type(t)}
            else:                                       # one of the building's two themes, as the room allows it
                themes = list(self.palette["decor"]); self.rng.shuffle(themes)
                for th in themes:
                    self._decor_types = {t: 1 for t in self.things if re.match(DECOR_THEMES[th], t) and self.ok_type(t)
                                         and self.belongs(t)}
                    if self._decor_types: break
            self._decor_at = []
        return self._decor_types

    def place_decor(self):
        """A hanging of the room's theme centred on a free stretch of a back wall, where it is seen, and at
        least DECOR_GAP units from the other hangings on that wall."""
        types = self.decor_theme()
        t0 = _pick(self.rng, types) or _pick(self.rng, self.types_of("wall_decor"))
        if not t0: return False
        for score, t, r, u, v, a, ha, hp in self.wall_candidates("wall_decor", t0, "center"):
            if r["side"] not in BACK_SIDES: continue
            if any(k == (r["line"], r["coord"]) and abs(a - a2) < DECOR_GAP for k, a2 in self._decor_at): continue
            if self.try_put(t, u, v, blocking=False, wall_ok=True, layer="wall"):
                self.wall_used.append(((r["line"], r["coord"]), a - ha, a + ha))
                self._decor_at.append(((r["line"], r["coord"]), a))
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
        """Bunks for a crew: up to n beds of one kind, headboards against the wall, evenly spaced with room
        between them (TreePlace v0.2 playtest: beds too close together). One row on the wall that holds the
        most, a SE or SW wall first (the NE and NW walls are kept for the shelves and hangings that face the
        camera, TreePlace v0.3 room review); when one wall holds too few, two
        rows facing each other across an aisle. A single row gets a chest at each bed's foot and rugs before
        them; nightstands stand between neighbours. Westwood's rooms with 3 or more beds all use one bed
        kind, lined up. Returns the beds placed."""
        stems = Counter()
        for t, w in self.types_of("bed").items(): stems[re.sub(r"\d+$", "", t)] += w
        if not stems: return []
        stem = _pick(self.rng, dict(stems))
        rows = {}
        for r in self.g.runs:                          # the best even row on every wall
            t = self._variant_for_wall(stem, r, across=True)
            if t: rows[id(r)] = (r, t, self._row_plan(t, r, n))
        if not rows: return []
        back = lambda r: r["side"] in BACK_SIDES
        best1 = max(rows.values(), key=lambda x: (len(x[2]), not back(x[0]), x[0]["hi"] - x[0]["lo"]))
        choice = [best1]
        if len(best1[2]) < n:                          # two rows facing each other across an aisle
            hp_of = lambda r, t: self.half(t)[0] if r["line"] == "/" else self.half(t)[1]
            best2 = None
            for r1, t1, p1 in rows.values():
                for r2, t2, p2 in rows.values():
                    if r2["line"] != r1["line"] or r2["sign"] == r1["sign"] or id(r2) == id(r1): continue
                    aisle = abs(r2["coord"] - r1["coord"]) - 2 * hp_of(r1, t1) - 2 * hp_of(r2, t2) - 0.6
                    if aisle < 2.4 or len(p1) < 2 or len(p2) < 2: continue
                    k1 = len(p1); k2 = min(len(p2), n - k1)
                    if k2 < 2: continue
                    score = (k1 + k2, not (back(r1) and back(r2)))
                    if best2 is None or score > best2[0]: best2 = (score, (r1, t1, p1), (r2, t2, self._row_plan(t2, r2, k2)))
            if best2 and best2[0][0] > len(best1[2]) + 1: choice = [best2[1], best2[2]]
        placed_beds = []
        for r, t, plan in choice:
            hu, hv = self.half(t)
            ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
            beds = [(o, a) for o, a in ((self.try_put(t, *self._uv_on(r, hp + 0.3, a)), a) for a in plan) if o]
            if len(beds) < 2:
                for o, _ in beds: self._remove(o)
                continue
            deep = len(choice) == 1                     # one row: chests at the feet and rugs before them
            self._dress_bed_line(r, beds, hp, ha, deep)
            placed_beds += [o for o, _ in beds]
        return placed_beds

    def _row_plan(self, t, r, n, min_gap=1.6, max_gap=3.6):
        """Where up to n beds of type t go along wall run r, headboards against it: evenly spaced with
        min_gap..max_gap units between neighbours (room for a nightstand; spread out, TreePlace v0.2
        playtest), every one where it fits now (doors keep their clearance), centred on the wall. The most
        beds first, then the widest spacing. Returns the positions along the wall."""
        hu, hv = self.half(t)
        ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
        step = 0.25
        lo, hi = r["lo"] + 1.2 + ha, r["hi"] - 1.2 - ha
        if hi < lo: return []
        grid = [lo + k * step for k in range(int((hi - lo) / step) + 1)]
        ok = {round(a / step) for a in grid if self.g.fits(*self._uv_on(r, hp + 0.3, a), hu, hv)}
        mid = (r["lo"] + r["hi"]) / 2
        for k in range(min(n, len(grid)), 0, -1):
            best = None
            pitches = [2 * ha + max_gap - q * step for q in range(int((max_gap - min_gap) / step) + 1)] if k > 1 else [0.0]
            for pitch in pitches:
                for a0 in grid:
                    pos = [a0 + i * pitch for i in range(k)]
                    if pos[-1] > hi + 1e-6: break
                    if all(round(a / step) in ok for a in pos):
                        off = abs((pos[0] + pos[-1]) / 2 - mid)
                        if best is None or (pitch, -off) > (best[0], -best[1]): best = (pitch, off, pos)
                if best: break
            if best: return best[2]
        return []

    def _dress_bed_line(self, r, beds, hp, ha, deep=True):
        """A row of bunks: a nightstand at the head between neighbours, a chest a step beyond each bed's foot
        (TreePlace v0.3 room review: the chests stood too close to the beds), and one rug before each bed, all
        alike and evenly spaced, or none (the rugs had looked weirdly spaced)."""
        # the row holds its whole stretch of wall, the nightstands between the beds included
        self.wall_used.append(((r["line"], r["coord"]), beds[0][1] - ha, beds[-1][1] + ha))
        for o, a in beds:
            self.beds.append((o, r, self._uv_on(r, hp + 0.3, a)))
            self.anchors.append(self._uv_on(r, hp + 0.3, a))
        ns = self.variant_for_side("Nightstand", r["side"])
        if ns:
            nhu, nhv = self.half(ns)
            na, nperp = (nhv, nhu) if r["line"] == "/" else (nhu, nhv)
            for (_, a1), (_, a2) in zip(beds, beds[1:]):
                if a2 - a1 - 2 * ha >= 2 * na + 0.8:
                    self.try_put(ns, *self._uv_on(r, nperp + 0.3, (a1 + a2) / 2))
        foot = 2 * hp + 0.3                             # the beds' feet, measured from the wall line
        chests = {t: w for t, w in self.types_of("storage").items() if re.match(r"^Chest\d$", t)}
        ct = self._variant_for_wall("Chest", r) if chests else None
        if ct and deep:
            chu, chv = self.half(ct)
            cp = chu if r["line"] == "/" else chv
            # not beside another wall: a chest at the foot of the end bed would stand across the side wall
            spots = [self._uv_on(r, foot + 1.2 + cp, a) for _, a in beds]
            got = [o for o in (self.try_put(ct, *uv) for uv in spots if self.g.wall_dist(*uv) - max(chu, chv) >= 1.0)
                   if o]
            if len(got) * 2 < len(beds):                # an odd chest here and there reads as clutter
                for o in got: self._remove(o)
            else:
                foot += 1.2 + 2 * cp
        rugs = {t: w for t, w in self.types_of("rug").items() if not t.startswith("Bearskin")}
        if not rugs or not deep or self.carpet_plan: return
        pitch = min(b - a for (_, a), (_, b) in zip(beds, beds[1:])) if len(beds) > 1 else 9.0
        for t0 in self.rng.sample(sorted(rugs), len(rugs)):
            t = next((s for s in (self.orient(t0, r["side"]), t0) if s and
                      2 * (self.half(s)[1] if r["line"] == "/" else self.half(s)[0]) + 0.2 <= pitch), None)
            if not t: continue
            rp = self.half(t)[0] if r["line"] == "/" else self.half(t)[1]
            got = [self.try_put(t, *self._uv_on(r, foot + 0.3 + rp, a), blocking=False) for _, a in beds]
            if all(got): return
            for o in got:
                if o: self._remove(o)

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

    def stock_walls(self, coverage=0.65, kinds=("shelves", "crates", "barrels", "sacks"), pad=1.0, limit=None):
        """Supplies along the free wall stretches: a heap two deep where a stretch starts in a corner, then
        groups of different sizes and single pieces with varied gaps, so the room has both clusters and
        open stretches (TreePlace v0.2 playtest: evenly spaced supplies looked mechanical, packed ones
        cluttered). The SE and SW walls first (the NE and NW walls are kept for what faces the camera), until
        `coverage` of the free wall length holds something. Pieces
        already standing keep `pad` units round them (the cauldron is not crowded by apple crates); shelves
        keep a unit off the corners (they face one way: no corner pieces); doors keep their clearance; the
        middle stays open. Returns the pieces placed."""
        segs = sorted(self.segments(pad=pad), key=lambda s: (s[0]["side"] in BACK_SIDES, -(s[2] - s[1])))
        total = sum(hi - lo for _, lo, hi in segs) or 1.0
        used, placed, k = 0.0, 0, self.rng.randrange(len(kinds))
        for r, lo, hi in segs:
            a = lo + 0.15
            if a - r["lo"] < 1.6 and used < coverage * total:          # the stretch starts in a corner: a heap
                got, edge = self._pile(r, a, hi, pad)
                if got: placed += got; used += edge - a; a = edge + self.rng.uniform(0.9, 2.0)
            tries = 0                          # a blocked spot (a piece in the corner) moves us along, not off the wall
            while used < coverage * total and a < hi - 0.8 and tries < 120 and \
                    (limit is None or self.n_blocking < limit):
                tries += 1
                kind = kinds[k % len(kinds)]; k += 1
                pat, n0, n1 = SUPPLIES[kind]
                types = self.supply_types(pat)
                if not types: continue
                size = self.rng.choices([1, n0, n1, n1 + 1], [3, 3, 2, 1])[0]
                if kind == "shelves":
                    if r["side"] not in BACK_SIDES: continue
                    t1 = self._variant_for_wall("LogShelvesFull", r)
                    group = [t1] * max(1, min(size, n1)) if t1 and a >= r["lo"] + CORNER_CLEAR else []
                else:
                    group = [self.orient(self.rng.choice(types), r["side"]) for _ in range(size)]
                group = [t for t in group if t]
                got, edge = 0, a
                for t in group:
                    thu, thv = self.half(t)
                    ta, tp = (thv, thu) if r["line"] == "/" else (thu, thv)
                    if edge + 2 * ta > hi or (kind == "shelves" and edge + 2 * ta > r["hi"] - CORNER_CLEAR): break
                    uv_ = self._uv_on(r, tp + 0.3, edge + ta)
                    if self._clear_of_anchors(*uv_, thu, thv, pad) and self.try_put(t, *uv_):
                        self.wall_used.append(((r["line"], r["coord"]), edge, edge + 2 * ta))
                        edge += 2 * ta + 0.12; got += 1
                    else:
                        break
                if got:
                    placed += got; used += edge - a
                    a = edge + (self.rng.uniform(1.3, 2.6) if got >= 3 else self.rng.uniform(0.5, 1.4))
                elif k % len(kinds) == 0:              # no kind fits here: try a little further along
                    a += 0.5
        return placed

    def supply_types(self, pat):
        """Supply types matching pat that the room's identity allows (its storage and shelf patterns)."""
        types = ROOM_IDENTITY.get(self.kind, {}).get("types", {})

        def allowed(t):
            allow = types.get("shelves" if re.match(r"^(LogShelves|PotionShelves|Bookcase)", t) else "storage")
            return not allow or re.search(allow, t)
        return [t for t in self.things if re.match(pat, t) and self.ok_type(t) and allowed(t)]

    def stack_middle(self, n=4):
        """A stack of goods standing free in the middle of a big storeroom, with aisles all round: crates
        side by side and a barrel or sack against them. Returns the pieces placed."""
        crates = self.supply_types(r"^(DarkCrate|Crate)[12]$")
        round_ = self.supply_types(PILE)
        if not crates or self.g.area < 80: return 0
        t = self.rng.choice(crates)
        hu, hv = self.half(t)
        spot = self.free_middle(2 * hu + 2.4, 2 * hv + 2.4)
        if not spot: return 0
        u, v = spot
        long_u = hu > hv
        offs = [(0, -hv - 0.1), (0, hv + 0.1)] if long_u else [(-hu - 0.1, 0), (hu + 0.1, 0)]
        got = sum(1 for du, dv in offs if self.try_put(t, u + du, v + dv))
        if got and round_ and n > got:
            tr = self.rng.choice(round_); th = self.half(tr)[0]
            du, dv = ((hu + th + 0.2) * self.rng.choice((-1, 1)), 0) if long_u else (0, (hv + th + 0.2) * self.rng.choice((-1, 1)))
            got += bool(self.try_put(tr, u + du, v + dv))
        if got: self.anchors.append(spot)
        return got

    def _pile(self, r, a, hi, pad=1.0):
        """A heap in a corner: two or three barrels and sacks along the wall, one or two more in front.
        Returns (pieces placed, where the heap ends along the wall)."""
        types = self.supply_types(PILE)
        if not types: return 0, a
        row, edge = [], a
        for _ in range(self.rng.randint(2, 3)):
            t = self.rng.choice(types); th = self.half(t)[0]
            if edge + 2 * th > hi: break
            uv_ = self._uv_on(r, th + 0.3, edge + th)
            if not (self._clear_of_anchors(*uv_, th, th, pad) and self.try_put(t, *uv_)): break
            row.append((edge + th, th)); edge += 2 * th + 0.08
        got = len(row)
        for ac, th0 in row[:self.rng.randint(1, 2)]:
            t = self.rng.choice(types); th = self.half(t)[0]
            uv_ = self._uv_on(r, 2 * th0 + 0.4 + th, ac + self.rng.uniform(-0.3, 0.3))
            if self._clear_of_anchors(*uv_, th, th, pad) and self.try_put(t, *uv_): got += 1
        if row: self.wall_used.append(((r["line"], r["coord"]), a, edge))
        return got, edge

    def line_wall(self, fam, near=None, max_n=None, decor_every=0, around=0.9, other=False, grow_only=False):
        """Shelves end to end along a NE or NW wall (TreePlace v0.3 room review: fill whole walls with bookshelves and
        similar pieces rather than one here and there; not every wall). The wall is the one holding `near` (a placed
        anchor such as the hearth or the desk: the shelves then flank it on both sides, packed toward it and so
        mirrored, `around` units from it), else the back wall with the most free length. Every free stretch of that
        wall fills from end to end, or takes a centred group of up to max_n. With decor_every > 0 a hanging of the
        room's theme takes a gap after every that many shelves. Half-full bookcases mix in. Returns the shelves
        placed. grow_only: only lengthen the rows already on a wall, end to end (never a second row with bare wall
        between)."""
        types = self.types_of(fam)
        if not types: return 0
        t0 = _pick(self.rng, types)
        if near and near["run"]["side"] in BACK_SIDES:
            runs = [near["run"]]
        else:
            near = None
            free = {id(r): sum(hi - lo for rr, lo, hi in self.segments() if rr is r) for r in self.g.runs}
            runs = sorted((r for r in self.g.runs if r["side"] in BACK_SIDES), key=lambda r: -free[id(r)] - self.rng.uniform(0, 0.5))
        for r in runs:
            if other and (r["line"], r["coord"]) in self._lined: continue    # the back wall not lined yet
            if grow_only and (r["line"], r["coord"]) not in self._line_blocks: continue
            t = self.side_variant(t0, r, fam)
            for alt in sorted(types, key=lambda k: -types[k]):   # t0 has no piece facing out of this wall (a
                if t: break                                      # bookcase drawn for one wall only): another type
                t = alt != t0 and self.side_variant(alt, r, fam)
            if not t: continue
            mix = [t] + ([t + "HalfFull"] if self.ok_type(t + "HalfFull") else [])
            got = self._line_run(r, mix, near, max_n, decor_every, around, fam, grow_only)
            if got:
                self._lined.add((r["line"], r["coord"]))
                return got
        return 0

    def _can_put(self, t, u, v, snug=False, touch=False):
        """Whether try_put would place a blocking piece t at (u, v) now (all but the walkability test)."""
        hu, hv = self.half(t)
        if self.composing and _family_of(t) in _blocking() and self.coverage(self.footprint(t)) > self.cover_max: return False
        return self.g.fits(u, v, hu, hv, True, False, wall_min=0.1 if snug else 0.25, touch=touch)

    def _line_run(self, r, mix, near, max_n, decor_every, around, fam, grow_only=False):
        """Lines the free stretches of wall run r (see line_wall). Every spot of the run is tested first and only an
        unbroken stretch of it is laid (the one at the anchor, else the longest), so a run never has holes."""
        hu, hv = self.half(mix[0])
        ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
        pitch = 2 * ha + 0.04
        dgap = 2.4 if decor_every else 0.0               # room for a hanging between groups of shelves
        d = hp + SNUG_GAP.get(fam, 0.2)
        key = (r["line"], r["coord"])
        got = 0
        for rr, lo, hi in self.segments():
            if rr is not r: continue
            lo, hi = max(lo, r["lo"] + CORNER_CLEAR), min(hi, r["hi"] - CORNER_CLEAR)     # tight into the corners
            toward = 0
            for b0_, b1_ in self._line_blocks.get(key, ()):     # a row already on this wall: grow it end to end
                if abs(lo - b1_) < 0.3: lo, toward = b1_ + 0.04, -1
                elif abs(hi - b0_) < 0.3: hi, toward = b0_ - 0.04, 1
            if near:
                a0, a1 = near["along"] - near["ha"], near["along"] + near["ha"]
                if abs(hi - (a0 - 0.25)) < 0.3: hi, toward = a0 - around, 1          # this stretch ends at the anchor
                elif abs(lo - (a1 + 0.25)) < 0.3: lo, toward = a1 + around, -1      # this one starts at it
            if grow_only and not toward: continue                # a stretch apart from the row: leave it
            length = lambda n: n * pitch - 0.04 + ((n - 1) // decor_every * dgap if decor_every and n > 1 else 0.0)
            n = 0
            while length(n + 1) <= hi - lo and (max_n is None or n < max_n): n += 1
            if n == 0: continue
            span = length(n)
            # a whole wall (no anchor, no row to grow) packs into the corner it shares with the other back wall, so
            # the two rows meet there with no gap; the slack goes to the front corner
            if not toward and not near and max_n is None:
                toward = self._back_corner_end(r, lo, hi)

            def lay_out(a, n):
                out = []                                 # ("shelf" | "decor", where it starts along the wall)
                for i in range(n):
                    if decor_every and i and i % decor_every == 0:
                        out.append(("decor", a)); a += dgap
                    out.append(("shelf", a)); a += pitch
                return out

            def fits_all(sl):
                return [kind == "decor" or self._can_put(mix[0], *self._uv_on(r, d, a0 + ha), snug=True, touch=True)
                        for kind, a0 in sl]
            a = lo if toward == -1 else hi - span if toward == 1 else (lo + hi) / 2 - span / 2
            slots = lay_out(a, n); ok = fits_all(slots)
            # packed into a corner whose first spot is taken (the other wall's row stands in that corner): slide out
            # a tenth of a unit at a time until the row starts tight against it, instead of a whole shelf's gap
            end = 0 if toward == -1 else -1
            if toward and ok and not ok[end]:
                for step in range(1, 30):
                    shift = step * 0.1 * (1 if toward == -1 else -1)
                    if abs(shift) > pitch + 0.05: break
                    n_ = n
                    while n_ > 1 and (a + shift < lo - 0.01 or a + shift + length(n_) > hi + 0.01): n_ -= 1
                    a_ = a + shift if toward == -1 else hi - length(n_) + shift
                    if toward == 1 and n_ < n: a_ = a + shift + (length(n) - length(n_))
                    sl = lay_out(a_, n_)
                    ok_ = fits_all(sl)
                    if ok_ and ok_[end]:
                        slots, ok = sl, ok_; break
            blocks, cur = [], []
            for k, (kind, a0) in enumerate(slots):
                if ok[k]: cur.append(k)
                else:
                    if cur: blocks.append(cur)
                    cur = []
            if cur: blocks.append(cur)
            blocks = [[k for k in b] for b in blocks]
            for b in blocks:                             # a run never starts or ends with a hanging's gap
                while b and slots[b[0]][0] == "decor": b.pop(0)
                while b and slots[b[-1]][0] == "decor": b.pop()
            blocks = [b for b in blocks if b]
            if not blocks: continue
            shelves = lambda b: sum(1 for k in b if slots[k][0] == "shelf")
            if toward == -1 and blocks[0][0] == 0: block = blocks[0]
            elif toward == 1 and blocks[-1][-1] == len(slots) - 1: block = blocks[-1]
            elif grow_only: continue                     # the spot by the row is taken: a stretch apart would leave a gap
            else: block = max(blocks, key=shelves)
            if shelves(block) < (1 if near else 2): continue       # never one shelf alone against a long wall
            laid, placed_seq = [], []                    # placed_seq: (slot index, object or None) in order
            for k in block:
                kind, a0 = slots[k]
                if kind == "decor":
                    if not self._hang(r, a0 + dgap / 2):        # no hanging fits: close the gap with shelves instead
                        k_fit = max(1, int((dgap + 0.04) / pitch))
                        st0 = a0 + (dgap - (k_fit * pitch - 0.04)) / 2
                        filled = 0
                        for q in range(k_fit):
                            if self.try_put(mix[0], *self._uv_on(r, d, st0 + q * pitch + ha), snug=True, touch=True):
                                laid.append(st0 + q * pitch); filled += 1
                        if not filled: placed_seq.append((k, None))     # a hole: the run is cut here (below)
                    continue
                t = mix[0] if len(mix) == 1 or self.rng.random() < 0.65 else mix[1]
                o = self.try_put(t, *self._uv_on(r, d, a0 + ha), snug=True, touch=True)
                placed_seq.append((k, o))
                if o: laid.append(a0)
            # a shelf that failed after all (the walkability test) leaves a hole: keep the longest unbroken part
            runs_, cur = [], []
            for k, o in placed_seq:
                if o: cur.append((k, o))
                else:
                    if cur: runs_.append(cur)
                    cur = []
            if cur: runs_.append(cur)
            if len(runs_) > 1:
                keep = max(runs_, key=len)
                for run_ in runs_:
                    if run_ is keep: continue
                    for k, o in run_:
                        self._remove(o); laid.remove(slots[k][1])
            if not laid: continue
            got += len(laid)
            b0, b1 = min(laid), max(laid) + 2 * ha
            self.wall_used.append((key, b0, b1)); self.wall_tall.append((key, b0, b1))
            self._line_blocks.setdefault(key, []).append((b0, b1))
            u, v = self._uv_on(r, d, (b0 + b1) / 2)
            self.g.zones.append(self.front_zone(r, u, v, (b1 - b0) / 2, hp, 1.2))
            self.anchors.append((u, v))
        return got

    def _back_corner_end(self, r, lo, hi):
        """-1 if wall run r's low end is the corner it shares with the other back wall (the room's top corner on
        screen), 1 if its high end is, else 0."""
        for rr in self.g.runs:
            if rr is r or rr["side"] not in BACK_SIDES or rr["line"] == r["line"]: continue
            if not rr["lo"] - 0.5 <= r["coord"] <= rr["hi"] + 0.5: continue
            if abs(rr["coord"] - (r["lo"] + 1)) < 1.6 and lo - r["lo"] < 2.5: return -1
            if abs(rr["coord"] - (r["hi"] - 1)) < 1.6 and r["hi"] - hi < 2.5: return 1
        return 0

    def complete_bookcase_walls(self):
        """A back wall holding a bookcase is filled with bookcases end to end (2026-10-04 review: "when a wall has
        one bookcase, it should usually be full of bookcases"). The row on the wall grows both ways with its own
        type until no more fit; a wall of shelves is not clutter, so the room's coverage limit is lifted for it."""
        keep_max, self.cover_max = self.cover_max, 9.9
        try:
            for r in self.g.runs:
                if r["side"] not in BACK_SIDES: continue
                key = (r["line"], r["coord"])
                mine = []
                for t, rec in self._typed:
                    if not t.startswith("Bookcase"): continue
                    u, v, hu, hv = rec[:4]
                    perp, along = (u, v) if r["line"] == "/" else (v, u)
                    ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
                    if abs(perp - r["coord"]) - hp > 0.6 or not r["lo"] <= along <= r["hi"]: continue
                    mine.append((t, along, ha))
                if not mine: continue
                blocks = self._line_blocks.setdefault(key, [])
                for t, along, ha in mine:
                    if not any(b0 - 0.05 <= along - ha and along + ha <= b1 + 0.05 for b0, b1 in blocks):
                        blocks.append((along - ha, along + ha))
                base = re.sub(r"HalfFull$", "", mine[0][0])
                mix = [base] + ([base + "HalfFull"] if self.ok_type(base + "HalfFull") else [])
                for _ in range(6):
                    if not self._line_run(r, mix, None, None, 0, 0.9, "shelves", grow_only=True): break
                self._lined.add(key)
        finally:
            self.cover_max = keep_max

    def _hang(self, r, a):
        """One hanging of the room's theme on wall run r, centred at `a` along it: the theme's types in turn until one
        has a variant for that wall and fits."""
        types = sorted(self.decor_theme()); self.rng.shuffle(types)
        for t0 in types[:10]:
            t = self.side_variant(t0, r, "wall_decor")
            if not t: continue
            d = self.perp_for(t, self.T["inventory"].get("wall_decor", {}).get("perp_px"))
            if self.try_put(t, *self._uv_on(r, d, a), blocking=False, wall_ok=True, layer="wall"):
                self._decor_at.append(((r["line"], r["coord"]), a))
                return True
        return False

    def shelf_wall(self, fam, cover=1.0):
        """One back wall lined with shelves end to end (an herbalist's potions, a library's books)."""
        return self.line_wall(fam)

    def lay_carpet(self, box=None, margin=0.8, material=None):
        """Carpet floor tiles instead of a rug object (Con07B lays carpets in 13 of its 28 rooms). box: uv (u0, u1, v0,
        v1) to cover, grown by `margin`; None covers the whole room but its outer ring of tiles. The carpet is a
        rectangle of the room's squares whose ring of neighbouring squares is the room's own floor too (the gold
        trim is drawn on the ring) and clear of the doors' thresholds; built floors only. The material comes from the
        building's palette. Returns the squares laid."""
        if not CARPET_FLOORS.search(self.room.floor or ""): return []
        sq = {((x + y) // 2, (x - y) // 2) for (x, y) in self.room.tiles}
        tile = lambda s: (s[0] + s[1], s[0] - s[1])
        nb8 = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]
        inner = {s for s in sq if all((s[0] + a, s[1] + b) in sq for a, b in nb8)}
        if box:                                        # squares whose centre (2i + 2, 2j) lies in the box
            u0, u1, v0, v1 = box[0] - margin, box[1] + margin, box[2] - margin, box[3] + margin
            inner = {(i, j) for (i, j) in inner if u0 <= 2 * i + 2 <= u1 and v0 <= 2 * j <= v1}
        if not inner: return []
        i0, i1 = min(i for i, _ in inner), max(i for i, _ in inner)
        j0, j1 = min(j for _, j in inner), max(j for _, j in inner)
        rect = {(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)}
        while not rect <= inner:                       # trim the side with the most squares missing
            sides = {"i0": [s for s in rect if s[0] == i0], "i1": [s for s in rect if s[0] == i1],
                     "j0": [s for s in rect if s[1] == j0], "j1": [s for s in rect if s[1] == j1]}
            worst = max(sides, key=lambda k: sum(s not in inner for s in sides[k]))
            if worst == "i0": i0 += 1
            elif worst == "i1": i1 -= 1
            elif worst == "j0": j0 += 1
            else: j1 -= 1
            if i0 > i1 or j0 > j1: return []
            rect = {(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)}
        if i1 - i0 < 1 or j1 - j0 < 1: return []        # at least 2 x 2 squares
        ring = {(s[0] + a, s[1] + b) for s in rect for a, b in nb8} - rect
        if any(tile(s) in self.spec.local_blend for s in rect | ring): return []     # a door's threshold
        mat = material or self.rng.choice(self.palette["carpet"])
        for s in rect: self.spec.floor[tile(s)] = mat
        self.carpet_boxes.append((2 * i0 + 1, 2 * i1 + 3, 2 * j0 - 1, 2 * j1 + 1))    # its uv box (rows stay off it)
        if mat not in self.spec.blend: self.spec.blending(mat, 40, edge=CARPET_EDGE)
        for s in ring:
            self.spec.local_blend[tile(s)] = -60
            self.spec.local_from.setdefault(tile(s), set()).add(mat)
        return sorted(rect)

    def _table_box(self):
        """uv box round the tables composed so far and the seats about them."""
        recs = [rec for t, rec in self._typed if _family_of(t) == "table"]
        if not recs: return None
        return (min(r[0] - r[2] for r in recs) - 1.3, max(r[0] + r[2] for r in recs) + 1.3,
                min(r[1] - r[3] for r in recs) - 1.3, max(r[1] + r[3] for r in recs) + 1.3)

    def rack_rows(self, kind="gear", aisle=None, gap=None, side_by_side=False):
        """Rows of gear racks standing free down the middle of a storeroom (TreePlace v0.3 room review: a store room
        holds more than other rooms, racks of gear in the middle), along the room's long axis, with aisles to the
        stocked walls and between the rows; one kind of rack to a row, its long side along the row. The first call sets
        the middle pair of rows; a room wide enough takes more pairs further out, one pair a call (a study twice
        Westwood's size holds several stacks). Returns the racks placed."""
        # gear racks stand a step apart with wide aisles, at most RACKS_PER_ROW to a row (2026-10-04 review: the
        # storerooms' racks were "a little bit too dense and numerous"); books and tombs keep their own spacing
        gear = kind in ("gear", "hunt", "mine")
        if aisle is None: aisle = 2.2 if gear else 1.6
        us = [x + y + 1 for x, y in self.g.cells]; vs = [x - y for x, y in self.g.cells]
        long_u = (max(us) - min(us)) >= (max(vs) - min(vs))
        lo_a, hi_a = (min(us), max(us)) if long_u else (min(vs), max(vs))
        lo_c, hi_c = (min(vs), max(vs)) if long_u else (min(us), max(us))
        margin = 1.6 + aisle                            # the pieces along the walls, then an aisle
        width = (hi_c - lo_c) - 2 * margin
        pats = list(RACK_KINDS.get(kind, RACK_KINDS["gear"]))
        self.rng.shuffle(pats)
        p = 1.9 + aisle                                 # a row and the aisle beside it
        n_fit = 0 if width < 1.2 else 1 if width < 2 * 1.9 + aisle else 2 + 2 * int((width - (2 * 1.9 + aisle)) / (2 * p))
        mid = (lo_c + hi_c) / 2
        centres = [mid] if n_fit == 1 else [mid + sg * (p / 2 + j * p) for j in range(n_fit // 2) for sg in (-1, 1)]
        centres = [c for c in centres if (long_u, round(c, 2)) not in self._rack_centres][:2]
        got = 0
        for k, c in enumerate(centres):
            types = [t for t in self.things if re.match(pats[k % len(pats)], t) and self.ok_type(t) and self.belongs(t)]
            if not types:
                types = [t for p_ in pats for t in self.things if re.match(p_, t) and self.ok_type(t) and self.belongs(t)]
            if not types: continue
            along = lambda t: self.half(t)[0] if long_u else self.half(t)[1]
            across = lambda t: self.half(t)[1] if long_u else self.half(t)[0]
            if side_by_side:                            # coffins and sarcophagi lie side by side, across the row
                t = max(types, key=lambda t: (along(t) <= across(t) + 0.01, self.rng.random()))
            else:
                t = max(types, key=lambda t: (along(t) >= across(t) - 0.01, self.rng.random()))
            tight = kind == "books"                     # library stacks stand end to end, racks a step apart
            pitch = 2 * along(t) + (gap if gap is not None else 0.04 if tight else 1.2 if gear else 0.5)
            span_lo, span_hi = lo_a + margin, hi_a - margin
            n = int((span_hi - span_lo + pitch - 2 * along(t)) / pitch)
            if gear: n = min(n, RACKS_PER_ROW)
            if n < 2: continue
            start = (span_lo + span_hi) / 2 - (n * pitch - (pitch - 2 * along(t))) / 2 + along(t)
            hu, hv = self.half(t)
            off_carpet = lambda uu, vv: not any(uu + hu > b[0] - 0.3 and uu - hu < b[1] + 0.3 and vv + hv > b[2] - 0.3
                                                and vv - hv < b[3] + 0.3 for b in self.carpet_boxes)
            row = []
            # the row slides across the room (the front holds the table) until it stands unbroken: the longest run of
            # free spots, at least half the row and 2 pieces; never a row with holes, never on a carpet
            out = 1 if c > mid else -1                  # a row further out slides only outward, keeping its aisle
            shifts = (0.0, -1.0, 1.0, -2.0, 2.0, -3.0, 3.0) if abs(c - mid) <= p else (0.0, out * 1.0, out * 2.0)
            for shift in shifts:
                cc = c + shift
                spots = [((a, cc) if long_u else (cc, a)) for a in (start + i * pitch for i in range(n))]
                ok = [off_carpet(*sp) and self._can_put(t, *sp, touch=tight) for sp in spots]
                best, cur = [], []
                for i, f in enumerate(ok):
                    cur = cur + [i] if f else []
                    if len(cur) > len(best): best = cur
                if len(best) < max(2, (n + 1) // 2): continue
                for i in best:
                    o = self.try_put(t, *spots[i], touch=tight)
                    if not o: break
                    row.append(o)
                if len(row) == len(best): break
                for o in row: self._remove(o)
                row = []
            if len(row) < 2:
                for o in row: self._remove(o)
                continue
            got += len(row)
            self._rack_centres.add((long_u, round(c, 2)))
            self.anchors.append((c, (span_lo + span_hi) / 2) if not long_u else ((span_lo + span_hi) / 2, c))
        return got

    # ---- set pieces: a trader's counter, pews, a throne ---------------------------------------------------------
    def place_counter(self, fam="counter_shop", depth=2.2, clear=1.8):
        """A trader's counter set out from a back wall, `depth` units into the room, along the wall and centred on its
        free stretch: the keeper stands in the space behind it (kept clear) and the customer before it."""
        t0 = _pick(self.rng, self.types_of(fam))
        if not t0: return None
        best = None
        for r, lo, hi in self.segments():
            if r["side"] not in BACK_SIDES: continue
            t = self.side_variant(t0, r, fam) or t0
            hu, hv = self.half(t)
            ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
            if ha < hp or hi - lo < 2 * ha + 2.0: continue
            score = (hi - lo) + self.rng.uniform(0, 1)
            if best is None or score > best[0]: best = (score, t, r, lo, hi, ha, hp)
        if not best: return None
        _, t, r, lo, hi, ha, hp = best
        a = (lo + hi) / 2
        u, v = self._uv_on(r, depth + hp, a)
        zone = self.front_zone(r, u, v, ha, hp, clear)
        if self.g.zone_blocked(zone): return None
        o = self.try_put(t, u, v)
        if not o: return None
        self.g.zones.append(zone)
        wu, wv = self._uv_on(r, 0.0, a)
        self.g.zones.append(self.front_zone(r, wu, wv, ha, 0.0, depth - 0.1))     # the keeper's space
        self.spots.append(dict(role="shopkeeper", px=_px(*self._uv_on(r, depth / 2 + 0.2, a))))
        self.anchors.append((u, v))
        self.wall_used.append(((r["line"], r["coord"]), a - ha - 0.6, a + ha + 0.6))
        return dict(obj=o, run=r, uv=(u, v), along=a, ha=ha, hp=hp)

    def pew_rows(self, fam="bench", toward=None, gap=2.6, aisle=2.4, first=3.4):
        """Rows of benches facing the altar wall (a chapel's pews): parallel to it from `first` units off it to 2 units
        short of the far wall, `gap` apart, every row split by a middle aisle. toward: the placed anchor (the altar)
        whose wall they face, else the back wall with the most length. Returns the benches placed."""
        types = self.types_of(fam)
        if not types: return 0
        r = toward["run"] if toward else max((rr for rr in self.g.runs if rr["side"] in BACK_SIDES),
                                            key=lambda rr: rr["hi"] - rr["lo"], default=None)
        if r is None: return 0
        opp = {"/|BR": "/|TL", "\\|BL": "\\|TR", "/|TL": "/|BR", "\\|TR": "\\|BL"}[r["side"]]
        back = next((rr for rr in self.g.runs if rr["side"] == opp), None)
        t0 = _pick(self.rng, types)
        t = (self.side_variant(t0, back, fam) if back else None) or t0     # a bench set against the far wall faces the altar
        hu, hv = self.half(t)
        ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
        depth_max = max(abs((x + y + 1 if r["line"] == "/" else x - y) - r["coord"]) for x, y in self.g.cells) - 2.0
        mid = toward["along"] if toward else (r["lo"] + r["hi"]) / 2
        lo, hi = r["lo"] + 1.6, r["hi"] - 1.6
        pitch = 2 * ha + 0.15
        got, d = 0, first
        while d + hp <= depth_max:
            for side in (-1, 1):                         # each half of the row, from the aisle outward
                a = mid + side * (aisle / 2 + ha)
                while lo + ha <= a <= hi - ha:
                    if self.try_put(t, *self._uv_on(r, d, a)): got += 1
                    a += side * pitch
            d += gap
        return got

    THRONE = (("DunMirThroneShadow", -61, -30), ("DunMirThroneBack", -4, -26), ("DunMirThroneBase", 0, 0),
              ("DunMirThroneFront", -33, 3))            # Westwood's assembly (the Kingdoms map), px from the base

    def place_throne(self, depth=2.6, clear=3.0):
        """The throne of a throne room: Westwood's Dun Mir throne in its four pieces at the Kingdoms map's offsets,
        centred on the NE wall (the one way it faces: into the room, toward the SW corner)."""
        runs = sorted((rr for rr in self.g.runs if rr["side"] == "\\|BL"), key=lambda rr: rr["lo"] - rr["hi"])
        for r in runs:
            a = (r["lo"] + r["hi"]) / 2
            u, v = self._uv_on(r, depth, a)
            if not self.g.fits(u, v, 2.0, 2.0) or not self.g.reachable_ok((u, v, 2.0, 2.0, True, "floor")): continue
            x0, y0 = _px(u, v)
            for typ, dx, dy in self.THRONE:
                if typ in self.things:
                    self.put(typ, *_uv(x0 + dx, y0 + dy), blocking=typ != "DunMirThroneShadow")
            self.g.zones.append(self.front_zone(r, u, v, 1.6, 1.4, clear))
            self.wall_used.append(((r["line"], r["coord"]), a - 2.2, a + 2.2)); self.wall_tall.append(((r["line"], r["coord"]), a - 2.2, a + 2.2))
            self.anchors.append((u, v))
            return dict(run=r, uv=(u, v), along=a, ha=2.0, hp=1.6)
        return None

    def belongs(self, t):
        """True if the room's identity has a place for type t (its family among the core or optional ones, matching the
        identity's pattern for it): what the checker's identity rule accepts (validate/checks.py identity_strays)."""
        ident = ROOM_IDENTITY.get(self.kind)
        if not ident: return True
        fam = _family_of(t)
        if not (fam in ident.get("core", {}) or fam in ident.get("optional", {}) or
                (fam in ("chair", "bench") and "table" in ident.get("core", {}))): return False
        pat = ident.get("types", {}).get(fam)
        return not pat or bool(re.search(pat, t))

    def _clearance(self, u, v, hu, hv):
        """Open floor round a piece at (u, v): the least gap to a wall or a blocking floor piece."""
        blocks = [p for p in self.g.placed if p[4] and p[5] != "wall"]
        return min([self.g.wall_dist(u, v) - max(hu, hv)] +
                   [max(abs(u - b[0]) - b[2] - hu, abs(v - b[1]) - b[3] - hv) for b in blocks])

    def scatter(self, fam, per100=6.0, cluster=(2, 4), wall_gap=0.6, spread=1.3):
        """Pieces of `fam` strewn over the floor in small heaps (straw in an ogre den, bones and skulls in the Land of
        the Dead: rules/out/cultures.json): about `per100` for every 100 floor tiles, `cluster` to a heap, `wall_gap`
        units clear of the walls and clear of the doors and the spaces kept clear. Returns the pieces placed."""
        types = self.types_of(fam)
        if not types: return 0
        n = max(1, int(round(per100 * len(self.room.tiles) / 100)))
        cells = sorted(self.g.cells)
        self.rng.shuffle(cells)
        got = 0
        for (x, y) in cells:
            if got >= n: break
            u0, v0 = x + y + 1.0, float(x - y)
            if self.g.wall_dist(u0, v0) < wall_gap + spread: continue
            for _ in range(self.rng.randint(*cluster)):
                t = _pick(self.rng, types)
                u, v = u0 + self.rng.uniform(-spread, spread), v0 + self.rng.uniform(-spread, spread)
                if self.try_put(t, u, v, blocking=_family_of(t) in _blocking()):
                    got += 1
                    if got >= n: break
        return got

    def place_group(self, name):
        """One free-standing group of GROUPS[name] at the best open spot of the floor (middle_spots: room round it, the
        front of the room first). Returns the pieces placed (0 when it does not fit)."""
        g = GROUPS[name]
        types = sorted(t for t in self.things if re.match(g["anchor"], t) and self.ok_type(t) and self.belongs(t))
        if not types: return 0
        t = self.rng.choice(types)
        hu, hv = self.half(t)
        pad = 1.4 if g.get("seats") else g.get("clear", 0.6)
        cu, cv = self.g.centroid
        us = [x + y + 1 for x, y in self.g.cells]; vs = [x - y for x, y in self.g.cells]
        long_u = (max(us) - min(us)) >= (max(vs) - min(vs))
        spots = self.middle_spots(hu + pad, hv + pad)[:30]
        if not spots and g.get("seats") and g["seats"][0] <= 2:    # a seat or two need not ring it: a narrower margin
            spots = self.middle_spots(hu + 0.9, hv + 0.9)[:30]
        for spot in spots:
            o = self.try_put(t, *spot)
            if not o: continue
            got = [o]
            if g.get("pair"):                           # its twin across the middle of the room's length
                twin = (2 * cu - spot[0], spot[1]) if long_u else (spot[0], 2 * cv - spot[1])
                if math.hypot(twin[0] - spot[0], twin[1] - spot[1]) < 3.0: self._remove(o); continue
                o2 = self.try_put(t, *twin) if self._clearance(*twin, hu, hv) >= g.get("clear", 0.6) else None
                if not o2: self._remove(o); continue
                got.append(o2)
            n_seats = 0
            if g.get("seats"):
                lo, hi = g["seats"]
                n_seats = self.seats_around(spot, t, self.rng.randint(lo, hi), g["seat"])
                if n_seats < lo:
                    for x in got: self._remove(x)
                    continue                            # seats_around removes nothing: the seats it placed stay
                self._seated.add((spot, t))
            if g.get("rug") and self.rng.random() < g["rug"]: self.rug_under(o, spot)
            if g.get("beside"):
                pat, n = g["beside"]
                bt = sorted(x for x in self.things if re.match(pat, x) and self.ok_type(x) and self.belongs(x))
                for _ in range(n if bt else 0):
                    b = self.rng.choice(bt); bhu, bhv = self.half(b)
                    for du, dv in self.rng.sample([(1, 0), (-1, 0), (0, 1), (0, -1)], 4):
                        uu, vv = spot[0] + du * (hu + bhu + 0.35), spot[1] + dv * (hv + bhv + 0.35)
                        x = self.try_put(b, uu, vv)
                        if x: got.append(x); break
            self.anchors.append(spot)
            return len(got) + n_seats
        return 0

    def fill_room(self):
        """Tops the room up toward the share of its floor its kind should cover (kit/identity.py ROOM_COVER) with what
        its identity says belongs there (ROOMS[kind]["fill"]), taking the steps in turn, each up to its own `max`
        pieces: a room holding only its anchors reads as empty, and coverage grows with the room (bigger rooms
        than Westwood's get more)."""
        steps = ROOM_IDENTITY.get(self.kind, {}).get("fill") or []
        if not steps: return
        # the steps' limits suit Westwood's rooms of the kind: a room bigger than its kind's median takes more of each
        # in proportion (a study of 266 tiles, twice Westwood's median, two reading tables and two curios)
        p50 = (self.T.get("tiles") or {}).get("p50") or 30
        grow = max(1.0, self.g.area / (2.4 * p50))
        cap = lambda st: st.get("max", 99) if st.get("max", 99) >= 99 or st.get("fixed") else \
            int(math.ceil(st["max"] * grow - 0.25))           # `fixed`: a set piece (a pair of statues) does not multiply
        k, misses, done_once, added = 0, 0, set(), collections.Counter()
        while self.coverage() < self.cover_target and misses < 2 * len(steps):
            i = k % len(steps); st = steps[i]; k += 1
            if i in done_once or added[i] >= cap(st) or self.g.area < st.get("min_area", 0): misses += 1; continue
            if st.get("once"): done_once.add(i)
            before = self.n_blocking
            fam = st["fam"]
            if st["slot"] == "stock":
                self.stock_walls(st.get("coverage", 0.3), st.get("kinds", ("crates", "barrels", "sacks")), pad=st.get("pad", 1.0))
            elif st["slot"] == "line":
                self.line_wall(fam, max_n=st.get("n"), decor_every=st.get("decor", 0), other=st.get("other", False))
            elif st["slot"] == "racks":
                self.rack_rows(st.get("kind", "gear"), st.get("aisle"), st.get("gap"), st.get("side_by_side", False))
            elif st["slot"] == "stack":
                self.stack_middle(st.get("n", 4))
            elif st["slot"] == "scatter":
                self.scatter(fam, st.get("per100", 6.0), st.get("cluster", (2, 4)), st.get("wall_gap", 0.6))
            elif st["slot"] == "group":                 # its `max` counts groups (a table and its chairs), not pieces
                if self.place_group(st["group"]): added[i] += 1
                misses = 0 if self.n_blocking > before else misses + 1
                continue
            elif st["slot"] == "center":
                res = self.place_center(fam)
                if res and st.get("seats"):
                    o, uv = res
                    if self.seats_around(uv, o["type"], 2, "chair") < 2: self._remove(o)
                    elif st.get("rug"): self.rug_under(o, uv)
            else:
                p = self.place_on_wall(fam, st.get("at", "center"), st.get("clear", 1.2))
                if p and st.get("seats"): self.seats_around(p["uv"], p["obj"]["type"], 1)   # a desk and its chair
            added[i] += self.n_blocking - before
            misses = 0 if self.n_blocking > before else misses + 1
        self.top_up()

    def top_up(self):
        """Pieces the room's identity allows (TOP_UP_FAMS among its core and optional families), one at a time against
        the walls, until the room reaches its coverage target. The fill steps open with the room's size (min_area),
        and a medium room of some kinds ran out of steps below its target (bedrooms of 32-48 tiles at 0.11-0.13
        against 0.14, studies of 60-90 tiles at 0.08-0.10 against 0.11)."""
        ident = ROOM_IDENTITY.get(self.kind, {})
        # first the rows of shelves already lining the walls, grown end to end
        fam = self.line_family()
        while fam and self.coverage() < self.cover_target and self.line_wall(fam, grow_only=True): pass
        # then single pieces, no more of a family than the identity allows a room of this size (7 potted plants in
        # a study is clutter, not furniture)
        p50 = (self.T.get("tiles") or {}).get("p50") or 30
        grow = max(1.0, self.g.area / (2.4 * p50))
        limits = {f: int(math.ceil(rng_[1] * grow)) + 1 for f, rng_ in list(ident.get("optional", {}).items()) +
                  list(ident.get("core", {}).items()) if f in TOP_UP_FAMS and self.types_of(f)}
        have = Counter(_family_of(t) for t, _ in self._typed)
        misses = 0
        while self.coverage() < self.cover_target:
            fams = [f for f, n in limits.items() if have[f] < n]
            if not fams or misses >= 2 * len(fams): break
            f = fams[misses % len(fams)] if misses else self.rng.choice(fams)
            before = self.n_blocking
            self.place_on_wall(f, self.rng.choice(("corner", "center")), 1.0)
            if self.n_blocking > before: have[f] += 1; misses = 0
            else: misses += 1

    def line_family(self):
        """The family this room's identity lines its walls with (shelves, shop racks), or None."""
        ident = ROOM_IDENTITY.get(self.kind, {})
        return next((st["fam"] for st in (ident.get("compose") or []) + (ident.get("fill") or [])
                     if st.get("slot") == "line"), None)

    def back_lined(self):
        """Share of the NE and NW walls lined, measured as the room score measures it: the stretches that tall pieces
        and hangings stand against, over the back walls' length less 3 units for each doorway in them."""
        backs = [r for r in self.g.runs if r["side"] in BACK_SIDES]
        length = 0.0
        for r in backs:
            length += r["hi"] - r["lo"]
            for du, dv in self.g.doors:
                perp, along = (du, dv) if r["line"] == "/" else (dv, du)
                if abs(perp - r["coord"]) < 1.6 and r["lo"] < along < r["hi"]: length -= 3.0
        spans = collections.defaultdict(list)
        for t, rec in self._typed:
            if not (TALL_PIECES.match(t) or _family_of(t) == "wall_decor"): continue
            u, v, hu, hv = rec[:4]
            for r in backs:
                perp, along = (u, v) if r["line"] == "/" else (v, u)
                ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
                if abs(perp - r["coord"]) - hp <= 1.0 and r["lo"] - ha <= along <= r["hi"] + ha:
                    spans[(r["line"], r["coord"])].append((along - ha, along + ha)); break
        used = 0.0
        for sp in spans.values():
            sp.sort(); end = -1e9
            for a, b in sp:
                if b <= end: continue
                used += b - max(a, end); end = b
        return used / length if length > 0 else 1.0

    def line_backs(self, goal=LINED_GOAL):
        """Lines the NE and NW walls until `goal` of their length is lined (TreePlace v0.3 review: shelves and wall
        decoration go on the NE and NW walls, whole walls end to end): the back wall not lined yet first, then the rows
        already there grown on. Hangings close what is left after the walls are decorated (furnish). A big room has
        two long back walls, and its recipe's one or two lining steps had left it about 30% lined."""
        fam = self.line_family()
        if not fam: return
        # shelves already standing against a back wall (one set there singly, beside a hearth or a desk) are that
        # wall's row: the pass grows it end to end rather than starting a second row with bare wall between
        for r in self.g.runs:
            if r["side"] not in BACK_SIDES: continue
            key = (r["line"], r["coord"])
            for t, rec in self._typed:
                if _family_of(t) != fam: continue
                u, v, hu, hv = rec[:4]
                perp, along = (u, v) if r["line"] == "/" else (v, u)
                ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
                if abs(perp - r["coord"]) - hp > 0.6 or not r["lo"] <= along <= r["hi"]: continue
                blocks = self._line_blocks.setdefault(key, [])
                if not any(b0 - 0.05 <= along - ha and along + ha <= b1 + 0.05 for b0, b1 in blocks):
                    blocks.append((along - ha, along + ha))
                self._lined.add(key)
        for _ in range(4):
            if self.back_lined() >= goal: return
            if not (self.line_wall(fam, other=True) or self.line_wall(fam, grow_only=True)): return

    def decorate_walls(self):
        """Hangings on the NE and NW walls the camera sees (trophies, tapestries, paintings, shields), each centred on
        a stretch free of tall pieces (above a chest, a bed or a bench they may hang): about one for every 3.5 units,
        1 to 8 (TreePlace room reviews: a living room needs trophies on the walls; more banners and trophies along the
        NE wall)."""
        self.decor_theme()
        free = sum(hi - lo for r, lo, hi in self.segments(tall_only=True) if r["side"] in BACK_SIDES)
        n = max(1, min(8, int(free / 3.5)))
        for _ in range(n):
            if not self.place_decor(): break

    def _rug_clear(self, rec, t=""):
        """A rug (of type t) lies clear of the tables, desks and beds."""
        mg = _rug_margin(t)
        own = self._rug_under.get(id(rec))
        return not any(self._overlap(p[0], p[1], p[2] + mg, p[3] + mg, rec) for tt, p in self._typed
                       if p is not rec and p is not own and _family_of(tt) in RUG_WHOLE)

    def audit_rugs(self):
        """Takes up any rug that lies half under a piece of furniture (TreePlace v0.2 playtest: a table and
        chairs half on a rug too small for them)."""
        for o in list(self.objects):
            if _family_of(o["type"]) != "rug": continue
            rec = self._placed_of.get(id(o))
            if rec and not self._rug_clear(rec, o["type"]): self._remove(o)


    def compose(self, plan, need):
        """Furnish from the room's composition (kit/identity.py ROOMS[kind]["compose"]): anchors on
        their own wall stretches, a rug before the anchor that calls for it, the table set in the open
        middle, supplies in rows from a corner, hangings on the back walls; then any core piece the
        composition could not fit is placed the old way so the room keeps its identity."""
        done = collections.Counter()
        tables, placed = [], {}
        steps = ROOM_IDENTITY[self.kind]["compose"]
        cp = next((st for st in steps if st["slot"] == "carpet"), None)
        if cp and CARPET_FLOORS.search(self.room.floor or "") and self.rng.random() < cp.get("chance", 0.5):
            self.carpet_plan = cp                       # carpet tiles in this room, no rug objects
        for st in steps:
            fam = st["fam"]
            if st["slot"] == "carpet":
                if self.carpet_plan:
                    box = self._table_box() if st.get("where") == "under" else None
                    if (st.get("where") != "under" or box) and self.lay_carpet(box, margin=st.get("margin", 0.4) if box else 0.8):
                        continue
                    self.carpet_plan = None             # no carpet fitted: a rug in the middle instead
                    t = _pick(self.rng, self.types_of("rug"))
                    spot = t and self.free_middle(*self.half(t))
                    if spot: self.try_put(t, *spot, blocking=False)
                continue
            n = plan.get(fam, 0) - done[fam]
            if n <= 0 and st["slot"] not in ("racks", "line", "pews"): continue      # rows and lined walls are sized by the room
            if st["slot"] == "line":
                done[fam] += self.line_wall(fam, near=placed.get(st.get("near")), max_n=st.get("n"),
                                            decor_every=st.get("decor", 0), other=st.get("other", False))
                continue
            if st["slot"] == "racks":
                done[fam] += self.rack_rows(st.get("kind", "gear"), st.get("aisle"), st.get("gap"), st.get("side_by_side", False))
                continue
            if st["slot"] == "bar":
                if self.build_bar(): done[fam] += 1
                continue
            if st["slot"] == "groups":                  # n free-standing groups (a tavern's tables with their stools)
                for _ in range(min(n, st.get("n", n))):
                    if not self.place_group(st["group"]): break
                    done[fam] += 1
                continue
            if st["slot"] == "counter":
                q = self.place_counter(fam, st.get("depth", 2.2), st.get("clear", 1.8))
                if q: done[fam] += 1; placed[fam] = q
                continue
            if st["slot"] == "throne":
                q = self.place_throne()
                if q: done[fam] += 1; placed[fam] = q
                continue
            if st["slot"] == "pews":
                done[fam] += self.pew_rows(fam, placed.get(st.get("toward")), st.get("gap", 2.6))
                continue
            if fam == "rug":                          # a rug no anchor called for: the middle of the room
                t = None if self.carpet_plan else _pick(self.rng, self.types_of("rug"))
                if t:
                    cu, cv = self.g.centroid
                    spot = (cu, cv) if self.g.fits(cu, cv, *self.half(t), blocking=False) else self.free_middle(*self.half(t))
                    if spot and self.try_put(t, *spot, blocking=False): done["rug"] += 1
                continue
            if st["slot"] == "scatter":               # strewn over the floor in heaps (straw, bones, meat)
                done[fam] += self.scatter(fam, st.get("per100", 6.0), st.get("cluster", (2, 4)), st.get("wall_gap", 0.6))
                continue
            if st["slot"] == "decor":                 # hangings go up last, once every wall is lined (fill_room)
                self._deferred_decor += n
                done[fam] += n
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
                done[fam] += self.stock_walls(st.get("coverage", 0.65), st.get("kinds", ("shelves", "crates", "barrels", "sacks")),
                                              pad=st.get("pad", 1.0))
                continue
            if st["slot"] == "shelf_wall":
                got = self.shelf_wall(fam, st.get("cover", 0.9))
                done[fam] += got
                continue
            if st["slot"] == "center":
                for _ in range(n):
                    res = self.place_center(fam)
                    if not res: break
                    o, uv = res
                    if st.get("seats"):                   # a table always has its seats, or it goes
                        want = max(2, plan.get("chair", 0) // max(1, n))
                        n0 = len(self.objects)
                        seated = self.seats_around(uv, o["type"], min(4, want), "chair") >= 2 or \
                            self.seats_around(uv, o["type"], 2, "chair") >= 2
                        if not seated:                    # no seats round it: the smallest table the room allows
                            for x in self.objects[n0:]: self._remove(x)       # with the odd chair that did fit
                            self._remove(o)
                            res = self.place_center(fam, small=True)
                            if not res: break
                            o, uv = res
                            n0 = len(self.objects)
                            if self.seats_around(uv, o["type"], 2, "chair") < 2:
                                for x in self.objects[n0:]: self._remove(x)
                                self._remove(o); break
                        self._seated.add((uv, o["type"]))
                        if st.get("rug"): self.rug_under(o, uv)
                    done[fam] += 1
                    tables.append((uv, o["type"]))
                continue
            if st["slot"] == "before":
                if placed.get(st["of"]):
                    q = self.place_before(fam, placed[st["of"]], st.get("gap", 2.4))
                    if q: done[fam] += 1; placed[fam] = q
                continue
            if st.get("beside") and placed.get(st["beside"]):
                q = self.place_beside(fam, placed[st["beside"]], gap=st.get("gap", 0.25), clear=st.get("clear", 0.0))
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
            if fam == "bed" and k and plan.get("nightstand") and not done["nightstand"]:
                self.beside_bed(); done["nightstand"] += 1      # at the bed's head before shelves line its wall
        if plan.get("nightstand") and self.beds and not done["nightstand"]:
            self.beside_bed(); done["nightstand"] += 1
        for f, n in need.items():                     # core pieces the composition could not fit
            for _ in range(max(0, n - done[f])):
                if f in SEAT_FAMILIES: break
                if f in FRONT_CLEAR:                      # a piece that is tended keeps the space before it clear
                    p = next((p for c in (FRONT_CLEAR[f], 1.0) for at in ("corner", "center")
                              for p in [self.place_on_wall(f, at, c)] if p), None)
                    if p:
                        done[f] += 1; continue
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
            along = (bhv + nhv + 0.6) if r["line"] == "/" else (bhu + nhu + 0.6)     # not pressed against it
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
        own = ROOM_IDENTITY.get(self.kind, {}).get("lights")
        if own:                                                  # the culture's own lights (rules/out/cultures.json)
            types = {t: s for t, s in own.items() if self.ok_type(t)} or types
        elif HOUSE_WALLS.search(self.g.wall_material or ""):     # a house: candelabras, never torches
            types = {t: s for t, s in HOUSE_LIGHTS["stone" if STONE_WALLS.search(self.g.wall_material) else "wood"].items()
                     if self.ok_type(t)} or types
        # lights balance the room: each goes to the wall spot that is farthest from the lights already
        # placed and from the furniture, preferring corners (with a chest centred on one wall and shelves
        # on the next, the candelabra goes to the empty far corner, not between them)
        # lights cover the room evenly: each goes to the wall spot that leaves the farthest corner of the
        # floor closest to a light (TreePlace v0.2 playtest: lights bunched on one side), never beside another
        lights = []
        t = _pick(self.rng, types)                     # one style of light per room
        base = _base(t)
        mounted = bool(base in self.dirvar and self.dirvar[base].get("use_variant_for_wall_side")
                       and not t.startswith("Candleabra"))
        cells = [(x + y + 1.0, float(x - y)) for (x, y) in self.g.cells]
        cells = cells[::max(1, len(cells) // 150)]
        pieces = [(p[0], p[1]) for p in self.g.placed if p[4] and p[5] != "wall"]
        spots = list(self._light_spots(t, base, mounted))
        for _ in range(n):
            ranked = []
            for c in spots:
                tv, u, v, corner = c
                if lights and min(math.hypot(u - a, v - b) for a, b in lights) < MIN_LIGHT_GAP: continue
                reach = max(min(math.hypot(cu - a, cv - b) for a, b in lights + [(u, v)]) for cu, cv in cells)
                dp = min([math.hypot(u - a, v - b) for a, b in pieces] or [3.0])
                ranked.append((reach - 0.2 * min(dp, 2.0) - (0.15 if corner else 0.0), c))
            for _, (tv, u, v, _c) in sorted(ranked, key=lambda r: r[0]):
                if not mounted and any(u + 0.5 > z[0] and u - 0.5 < z[1] and v + 0.5 > z[2] and v - 0.5 < z[3]
                                       for z in self.light_zones):
                    continue                              # never right before a chest, hearth or stove
                if self.try_put(tv, u, v, blocking=not mounted, wall_ok=mounted, layer="wall" if mounted else "floor"):
                    lights.append((u, v)); break
            else:
                break
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
