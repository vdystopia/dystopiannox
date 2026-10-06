"""Room archetypes: the several genuinely different layouts Westwood gives one room type.

Independent blind judges (review/NIGHTLOG.md, 2026-10-06) named "one template per type repeated across variants" the top
remaining giveaway of generated rooms: the same throne room four times, the same shop three times, the same NW wall
(bookcase, desk with chair, bookcase) in every study end, every laboratory's workbenches as one block in the middle.
Westwood's rooms of one type differ in structure, not just in details: one bedroom is a chamber with a bed end and a
sitting end, another a small cot room, another a lord's room with an oval table standing free on a rug.

So each type's curated Westwood campaign rooms (rules/out/motifs.json, Con/War/Wiz only, curated.json applied) are
clustered here by structure, by eye from their measured plans: where the focal stands from the door, how the room is
zoned, which walls are used, what the middle holds, how dense it is. Each archetype names its Westwood rooms (`rooms`);
its frequency is their share of the type's rooms. A thin type (throne room, great hall, kitchen, tavern...) takes
archetypes from its own few rooms plus kin types' rooms (`kin`, counted at KIN_SHARE each), and says so.

Both engines draw one archetype per room (draw()):
- by Westwood's frequencies among the archetypes whose rooms are of about the room's size (FIT: a room of ours is
  1.25 times Westwood's in length, about 1.56 in tiles);
- spread over the map: a map's rooms of one type draw by the deficit of each archetype against its frequency (the
  first room of a type draws by frequency alone; one already used is drawn again only once its share is due), so a
  town's five bedrooms or the room lab's ten variants are not one archetype five times by chance;
- reproducible: its own generator seeded from the map's name, the room and the type (crc32), and a room re-composed by
  the originality check keeps its archetype.

The recipe engine (kit/furnish.py) lays the archetype's own composition over the kind's recipe
(kit/identity.py ROOMS[kind]["archetypes"][name]: its compose, fill and whatever else it sets, a cover factor); the
motif engine (kit/motifs.py) takes its zone skeletons only from the archetype's Westwood rooms, stands the focal piece
where they stand it from the door, and scales its density by the archetype's cover factor. Within an archetype the
pieces still vary (the recipes' own draws, the motifs drawn from every room of the type).

    py mapgen/kit/archetypes.py [type ...]      the archetypes, their frequencies and Westwood examples
"""
import collections, json, math, os, random, zlib
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
MOTIFS_PATH = os.path.join(REPO, "rules", "out", "motifs.json")
KIN_SHARE = 0.5          # a kin type's room counts half a room of the type in a thin type's frequencies
SCALE_TILES = 1.56       # our rooms' tiles over Westwood's (kit/identity.py BUILDING_SCALE 1.25, squared)
FIT = (0.55, 1.8)        # an archetype fits a room within this factor of its Westwood rooms' tile range

# type -> [dict(name, desc, rooms, kin=(), focal=None|"opposite"|"beside"|"free", cover=1.0)]
# focal: where the focal piece stands from the main door (motif engine); cover: a factor on the room's cover goal.
ARCHETYPES = {
    "bedroom": [
        dict(name="cot_room", cover=0.75, focal="opposite",
             desc="a small sleeping room: the bed with its nightstand on the back wall across from the door, a chest "
                  "by it or on the other back wall, a bookcase at most; nothing in the middle, no desk or table",
             rooms=("Con03B@132,98", "Con07B@97,219", "Con09b@188,86", "Con09a@135,41")),
        dict(name="bed_and_desk", cover=1.0, focal="opposite",
             desc="a snug chamber in two walls: the bed and nightstand on one back wall, the desk with its chair on the "
                  "other, a bookcase or two beside one of them, the chest snug at the bed or free before it; the middle "
                  "bare. In three the door is in a back wall and the bed stands across from it on a front wall",
             rooms=("Con02a@68,156", "Con02a@74,98", "Con05A@83,51", "Con07B@173,213", "Con07B@36,34",
                    "Con07B@40,38", "Con07B@92,224", "Con07B@38,28", "Con07B@42,32", "Con07B@46,36")),
        dict(name="sitting_end", cover=1.15, focal="beside",
             desc="a chamber of two ends: the bed end (the bed with nightstands, often in a corner of a back wall) and a "
                  "sitting or working end (a table with chairs, or a desk among bookcases, candles), a carpet under much "
                  "of it",
             rooms=("Con02a@214,42", "Con02a@78,126", "Con02a@80,94", "Con02a@76,174", "Con03B@210,71",
                    "Con07B@113,203", "Con07D@125,86", "Con07D@137,75", "War07A@122,199")),
        dict(name="lords_room", cover=0.7, focal="opposite",
             desc="a big, sparse chamber: the bed on a back wall, a rug and an oval table standing free on the open "
                  "floor, a chest, trophies or tapestries on the walls; most of the floor bare",
             rooms=("Con06b@85,218", "Con06b@92,211", "Con06b@149,60", "Con07E@183,119", "Con06b@97,200")),
    ],
    "living_room": [
        dict(name="hearth_nook", cover=0.9, focal="beside",
             desc="a small hearth room: the hearth on a back wall, the round table ringed by chairs before it or off "
                  "to a side, a bench, a barrel or a water barrel; little else",
             rooms=("Con06a@130,174", "Con06a@137,166", "Con07B@105,197", "Con07B@74,178", "Con07B@80,184")),
        dict(name="parlour", cover=1.1, focal="beside",
             desc="the hearth between bookcases (or bookcases on the wall across), tables with chairs on a carpet, "
                  "candles: a household's best room",
             rooms=("Con02a@211,51", "Con02a@80,168", "Con07B@167,214")),
        dict(name="common_room", cover=1.0, focal="beside",
             desc="a great house's common room: the hearth with chairs on a rug before it, two or more tables apart, "
                  "bookcases along a wall, statues and tapestries, barrels by the hearth; open floor between the sets",
             rooms=("War07A@119,187", "Wiz01A@108,137")),
        dict(name="cottage", cover=1.1, focal="free",
             desc="a one-room cottage: no hearth but an iron stove in a corner, a bed or a cot on a wall, chests on "
                  "another, a round table with chairs on a rug",
             rooms=("Con02a@100,118", "Con02a@57,149", "Con07B@64,194", "Wiz06a@79,60")),
    ],
    "guardroom": [
        dict(name="watch_table", cover=0.9, focal="free",
             desc="a guard post: a round table with three or four chairs (one fallen) off the middle, barrels or a chest "
                  "by the walls; no beds",
             rooms=("Con06b@104,79", "Wiz06a@210,180", "Wiz06a@84,151", "Wiz06b@46,38", "Con06b@179,71")),
        dict(name="cot_post", cover=1.0, focal="free",
             desc="a watch hut: two cots against the walls with chests, a table with food and chairs, barrels",
             rooms=("Con03A@110,112", "Con03A@164,60", "Con03A@81,83", "Wiz06a@136,196")),
        dict(name="armed_hall", cover=0.9, focal="opposite",
             desc="the keep's guard room: arms on the walls (swords, shields, racks), a long table with benches and a "
                  "round table, barrels and a chest",
             rooms=("Con02a@93,175", "Con06a@69,199")),
    ],
    "cell": [
        dict(name="straw_pen", cover=1.0,
             desc="an ogre pen: straw heaped over the floor, a primitive obelisk in a corner, a stool or a bench",
             rooms=("Con11a@166,52", "Con11a@174,44", "Con11a@182,36", "Con11a@194,80", "Con11a@202,72",
                    "Con11a@210,64")),
        dict(name="gaol_cell", cover=1.0, focal="opposite",
             desc="a gaol cell: one cot on a back wall, straw lining the walls and strewn, nothing else",
             rooms=("War07A@160,230", "War07A@164,226", "War07A@174,236")),
        dict(name="cell_block", cover=0.6,
             desc="a long barred block: bare, barrels in a corner, torches", rooms=("War03c@104,88",)),
    ],
    "storeroom": [
        dict(name="corner_heaps", cover=0.9,
             desc="a small store: a heap of barrels in one corner, a crate or an apple crate by another wall, the middle "
                  "an aisle", rooms=("Con01A@95,121", "Con02a@58,154", "Con06a@12,149", "War03d@88,216")),
        dict(name="shelved_store", cover=1.2,
             desc="shelves of stores on both back walls, water barrels free before them",
             rooms=("Con05A@52,18",)),
        dict(name="hall_of_stock", cover=1.0,
             desc="a big store: crates and casks heaped free over the floor in knots, a desk, odd things put away "
                  "(statues, telescopes, bookcases)", rooms=("Con03B@203,115", "Con07B@121,219")),
    ],
    "barracks": [
        dict(name="bunk_row", cover=1.0, focal="opposite",
             desc="bunks of one kind in a row on one wall with chests, the crew's tables and chairs free before them, "
                  "arms hung", rooms=("Con06b@160,48", "Con06b@106,192", "Con05A@48,66")),
        dict(name="ogre_den", cover=1.0,
             desc="the ogres' den: straw heaped over the floor, crude beds on the back walls, a table with stools, "
                  "barrels in a knot, meat", rooms=("Con05C@122,91", "Con05C@140,109", "Con09c@50,210", "Con09c@62,206")),
    ],
    "crypt": [
        dict(name="tomb_niche", cover=1.0,
             desc="a small side chamber: one or two sarcophagi off the middle, a tombstone at the wall",
             rooms=("War03c@74,214", "War03c@83,223", "War03c@85,203", "War03c@94,212", "War03d@52,214",
                    "War03d@62,222", "War03d@64,202", "War03d@74,210")),
        dict(name="tomb_row", cover=1.0,
             desc="a big vault with a row of three or four sarcophagi along one side and tombstones behind them, the "
                  "rest of the floor open", rooms=("War03c@73,224", "War03c@95,202", "War03d@52,223", "War03d@74,201")),
        dict(name="wall_tombs", cover=1.0,
             desc="sarcophagi against the walls, torches, a crypt chest or obelisks in the middle",
             rooms=("Con04a@100,130", "Con04a@128,136", "Con04a@136,150", "Con04a@138,118", "Con04a@138,97",
                    "War03c@100,229")),
        dict(name="tombstone_yard", cover=1.0,
             desc="no sarcophagi: tombstones in a loose grid over the floor, a crypt chest",
             rooms=("Con04a@148,127", "Con04a@150,108", "Con04b@142,44", "Con04c@194,152", "War03c@80,98",
                    "War03c@94,112")),
        dict(name="statue_vault", cover=1.0, desc="statues in pairs on every wall, tombstones in rows between",
             rooms=("Con04a@112,146",)),
    ],
    "shop": [
        dict(name="lined_walls", cover=1.0, focal="opposite",
             desc="goods lining the back walls (potion shelves, bookcases, trader's shelves), the keeper's desk on a "
                  "wall or a little out from it, a cauldron or a stove in a corner, the floor open",
             rooms=("Con02a@113,142", "Con09b@184,92", "War07A@109,167", "Con07B@106,208")),
        dict(name="stock_heaps", cover=1.1, focal="opposite",
             desc="a general store: steel crates and barrels heaped along both long walls, the keeper's desk with its "
                  "chair at the far end; the middle an aisle", rooms=("Con03A@14,198", "Con03B@238,74")),
        dict(name="showroom", cover=1.0, focal="free",
             desc="an armourer's showroom: racks hung along the walls and standing free over the floor in loose rows, "
                  "the keeper's desk standing free among them", rooms=("Con06a@142,205", "War07A@132,174")),
    ],
    "tavern": [
        dict(name="common_room", cover=1.0, focal="beside",
             desc="the bar in a back corner with kegs behind it, the hearth on another wall, tables of two kinds over "
                  "the floor with open floor between", rooms=("Con02a@86,105", "Con07B@91,177")),
        dict(name="hearth_hall", cover=0.9, focal="opposite",
             desc="free-standing hearths down the middle, round tables with cushioned stools clustered in one half, a "
                  "short bar on a back wall with barrels", rooms=("Con06a@143,178",)),
        dict(name="barroom", cover=1.0, focal="opposite",
             desc="the bar across the room with great casks behind it and piled barrels, little seating",
             rooms=("Wiz05A@43,19",)),
        dict(name="drinking_room", cover=0.9, focal="free",
             desc="the seating room: round tables with stools against the walls, no bar or hearth of its own",
             rooms=("Wiz05A@48,24",), kin=("Con06b@104,79", "Wiz06a@210,180")),
    ],
    "laboratory": [
        dict(name="study_lab", cover=0.8, focal="opposite",
             desc="a scholar's lab: the desk with its chair on a back wall, one workstation or shelf apart, candles; the "
                  "floor mostly bare", rooms=("Con07E@190,124", "Con07D@118,93")),
        dict(name="work_wall", cover=1.0, focal="beside",
             desc="workstations side by side along one wall, the desk and a shelf on the other",
             rooms=("Con09b@192,94", "Con05A@55,41")),
        dict(name="zoned_lab", cover=1.1, focal="beside",
             desc="a big lab in zones: bookcases lining the walls, workstations as a bench (along a front wall or as an "
                  "island), a table set in a corner, generators along a wall, many candles",
             rooms=("Con07C@71,136", "Con07C@82,193")),
    ],
    "kitchen": [
        dict(name="cookhouse", cover=1.1, focal="beside",
             desc="the wall hearth with iron stoves beside it, barrels heaped in the corners, work tables",
             rooms=("Con06b@202,53",), kin=("Con02a@100,118", "Con07B@64,194")),
        dict(name="stove_kitchen", cover=0.8, focal="free",
             desc="an iron stove in a corner and a table with a chair or two; a hanging; nothing else",
             rooms=("Con05A@25,21",), kin=("Wiz06a@79,60",)),
        dict(name="open_hearth", cover=1.0, focal="free",
             desc="a free-standing hearth in the middle, the stove and tables round the walls",
             rooms=("Con07B@128,189",)),
        dict(name="pantry_kitchen", cover=1.1, focal="beside",
             desc="the hearth with its pot, provisions on shelves along a back wall, stores heaped by the walls (kin: "
                  "the storerooms' heaps and the living rooms' hearths)", rooms=(),
             kin=("Con06a@12,149", "Con07B@167,214", "Con05A@52,18")),
    ],
    "throne_room": [
        dict(name="processional", cover=1.0, focal="opposite",
             desc="the throne across from the door at the head of a long walk, fire basins in pairs down it, a pair of "
                  "columns, victory statues; the walls bare", rooms=("Con06b@58,151",), kin=("Con04c@75,78",)),
        dict(name="dressed_walls", cover=1.0, focal="opposite",
             desc="the throne on the back wall across from the door, the walls dressed end to end (tapestries, columns "
                  "against the side walls, balances or obelisks in pairs), the floor bare",
             rooms=("Con10d@96,150",), kin=("Con06b@98,180",)),
        dict(name="ringed_seat", cover=1.0, focal="opposite",
             desc="the throne standing out from the back wall ringed by four lights, a square of obelisks or statues "
                  "before it, chests and tapestries on the walls", rooms=("Con11a@166,141",)),
        dict(name="audience_chamber", cover=0.8, focal="beside",
             desc="a small chamber: the throne on a back wall beside the door, flanked by a pair of obelisks or statues, "
                  "a lone basin; nothing else", rooms=("Wiz11A@203,72",)),
    ],
    "chapel": [
        dict(name="pewed_nave", cover=1.0, focal="opposite",
             desc="pews in short rows either side of a carpeted aisle, columns ringing the nave among them, tapestries "
                  "of one colour, candelabras in pairs, a statue by the altar", rooms=("Con07B@143,201",)),
        dict(name="sanctum", cover=0.8, focal="free", weight=0.75,      # three shrines, not three chapels
             desc="the holy thing in the middle ringed by four obelisks on a carpet, candelabras along the walls, a "
                  "few pews facing it (kin: the shrines)", rooms=(), kin=("Con07D@118,78", "Wiz02B@120,120",
                                                                       "Wiz11A@50,215")),
        dict(name="colonnade_chapel", cover=1.0, focal="opposite",
             desc="the altar at the end of a colonnade, statues in pairs facing across the aisle, a few pews near the "
                  "altar (kin: Con04c's colonnade hall)", rooms=(), kin=("Con04c@75,78",)),
    ],
    "great_hall": [
        dict(name="hearth_in_the_round", cover=1.0, focal="free",
             desc="a free-standing hearth in the middle, benches in rows round it, shields and banners on the back "
                  "walls", rooms=("Con06b@186,38",)),
        dict(name="feast_hall", cover=1.0, focal="beside",
             desc="the hearth on a back wall, many small tables of mixed kinds with chairs along the walls and over the "
                  "floor, torch poles, trophies", rooms=("Con07E@173,104",)),
        dict(name="long_boards", cover=1.0, focal="opposite",
             desc="the hearth on a back wall, long boards in parallel on a great carpet with benches down both sides",
             rooms=(), kin=("Con06a@81,211", "Con05C@139,92")),
    ],
}
# the kit's kinds map to these through kit/roomtypes.py KIND_TYPE; a culture variant of a type (an ogre den, a dark
# crypt) keeps its own recipe: its archetypes are those whose rooms are of its culture (see draw: culture)


@lru_cache(None)
def _rooms():
    try:
        with open(MOTIFS_PATH, encoding="utf-8") as f:
            return {r["id"]: r for r in json.load(f)["rooms"]}
    except OSError:
        return {}


def table(rtype):
    """[(archetype, frequency)] for the type, frequencies summing to 1 (kin rooms at KIN_SHARE)."""
    arcs = ARCHETYPES.get(rtype) or []
    w = [a.get("weight", len(a["rooms"]) + KIN_SHARE * len(a.get("kin", ()))) for a in arcs]
    tot = sum(w) or 1.0
    return [(a, x / tot) for a, x in zip(arcs, w)]


def tile_range(a):
    """(lo, hi) Westwood tiles of an archetype's rooms (its own, else its kin)."""
    rs = _rooms()
    t = [rs[i]["tiles"] for i in a["rooms"] if i in rs] or [rs[i]["tiles"] for i in a.get("kin", ()) if i in rs]
    return (min(t), max(t)) if t else (1, 10 ** 6)


def cultures(a):
    rs = _rooms()
    return {rs[i]["culture"] for i in tuple(a["rooms"]) + tuple(a.get("kin", ())) if i in rs}


RICH = 10                # a type with this many Westwood rooms holds its archetypes to their rooms' sizes (FIT); a thinner
THIN_FIT = (0.2, 6.0)   # one's few rooms say little about size: only a room far off them is kept from an archetype


def _own(a):
    rs = _rooms()
    for i in a["rooms"]:
        if i in rs: return rs[i]["type"]
    return None


def fits(a, tiles, culture=None):
    lo, hi = tile_range(a)
    t = tiles / SCALE_TILES
    typ = _own(a)
    rich = typ and sum(len(b["rooms"]) for b in ARCHETYPES.get(typ, [])) >= RICH
    f0, f1 = FIT if rich else THIN_FIT
    if not (lo * f0 <= t <= hi * f1): return False
    cs = cultures(a)
    # an ogre pen or an ogre den for ogre rooms only; the other cultures share their archetypes
    if culture == "ogre" or cs == {"ogre"}: return culture in cs or not cs
    return True


def _size_miss(a, tiles):
    lo, hi = tile_range(a)
    t = tiles / SCALE_TILES
    return 0.0 if lo <= t <= hi else min(abs(math.log(t / lo)), abs(math.log(t / hi)))


def draw(spec, room, rtype, tiles, culture="town"):
    """The archetype (its record, or None) a room of the type takes: by Westwood's frequencies among those that fit
    its size and culture, by deficit over the map's rooms of the type drawn so far; reproducible (crc32), and a room
    drawn again (the originality check's retries) keeps its archetype."""
    if os.environ.get("NOX_ARCHETYPES") == "0": return None     # the room lab's before: one composition per kind
    tab = table(rtype)
    if not tab: return None
    memo = getattr(spec, "_archetypes", None)
    if memo is None:
        memo = dict(rooms={}, used=collections.defaultdict(collections.Counter))
        try: setattr(spec, "_archetypes", memo)
        except AttributeError: pass
    key = (rtype, getattr(room, "id", None))
    if key in memo["rooms"]: return memo["rooms"][key]
    ok = [(a, f) for a, f in tab if fits(a, tiles, culture)]
    if not ok:                                   # none of Westwood's sizes: the nearest
        best = min(_size_miss(a, tiles) for a, _ in tab)
        ok = [(a, f) for a, f in tab if _size_miss(a, tiles) <= best + 1e-9 and fits(a, tiles * 0 + tiles, culture)] or \
             [(a, f) for a, f in tab if _size_miss(a, tiles) <= best + 1e-9]
    tot = sum(f for _, f in ok)
    used = memo["used"][rtype]
    n = sum(used[a["name"]] for a, _ in ok)
    weights = [max(0.04, (n + 1) * f / tot - used[a["name"]]) for a, f in ok]
    name = getattr(spec, "d", {}).get("name") if hasattr(spec, "d") else None
    rng = random.Random(zlib.crc32(f"archetype:{name}:{key[1]}:{rtype}:{n}".encode()))
    a = rng.choices([a for a, _ in ok], weights)[0]
    used[a["name"]] += 1
    memo["rooms"][key] = a
    return a


def describe(rtype):
    lines = []
    tab = table(rtype)
    n_own = sum(len(a["rooms"]) for a in ARCHETYPES.get(rtype, []))
    for a, f in tab:
        lo, hi = tile_range(a)
        kin = f"; kin {', '.join(a['kin'])}" if a.get("kin") else ""
        lines.append(f"  {a['name']:20} {f:4.0%}  ({len(a['rooms'])} of {n_own}{kin}; Westwood {lo}-{hi} tiles)  "
                     f"{', '.join(a['rooms'])}\n      {a['desc']}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    for t in (sys.argv[1:] or sorted(ARCHETYPES)):
        print(t); print(describe(t))
