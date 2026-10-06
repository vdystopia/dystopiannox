"""The object knowledge base, as the furnisher and the checker read it (rules/objects.py measures it on Westwood's
campaign rooms and writes rules/out/objects.json).

Harrowby playtest, 2026-10-05 (review/FEEDBACK.md HB-1..HB-5): "Why are there two cauldrons? There should only be a
maximum of one cauldron per room. bed is way too close to one of the cauldrons. The bench is too close to the bed. Chest
is way too close to the other cauldron. Do a pass over all objects and try to understand better how they fit in the
world ... some objects are suitable for lining an entire wall, and some are not." Earlier rounds patched one case at a
time; this answers them all from one table:

- kind(t), category(t): what a piece is (Chest of Chest1-4; chest, supply, shelf, hearth, cauldron, bed, statue ...);
- role(t): "showpiece" (stands once in a room), "fabric" (may line a wall end to end), else a piece that stands alone,
  in a pair or in a short run; max_run(t): the most of one kind side by side along a wall (Westwood: log shelves 2,
  barrels 3, statues and chests 1; bookcases unlimited);
- room_cap(t, type, tiles): the most of a kind one room holds (a cauldron 1, chests by the room type's p90: a bedroom
  1, a lord's chamber 2; a showpiece 1, a hearth 2 in a hall of 240 tiles);
- clearance(a, b): the least gap (uv units, edge to edge) between two categories: Westwood's p5 of the nearest pair
  (a little under it), never under the playtest's floors (a bed or a chest 2 units from any fire, a chest 3 from a
  hearth, a bench 1.2 from a bed, two statues 2 apart unless a deliberate pair);
- hangs_over(cat): False for every floor piece: Westwood hangs nothing above a piece standing against the wall (0-3%
  of them: beds 1.7%, chests 0.4%, statues 0.4%, shelves 0.1%), so a hanging takes a bare stretch of wall;
- light_cap(tiles): candelabras by room size (Westwood's p90 per room: 2 under 40 tiles, 3 under 100, 5 above);
- bedroom_sets: a bedroom holds one table-and-chair set at most (a table or a desk), the playtest's hard rule;
- supply_clusters: how Westwood heaps its supplies (cluster sizes, the mix, the gaps between clusters).
"""
import json, math, os, re
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(os.path.dirname(os.path.dirname(HERE)), "rules", "out", "objects.json")

# ---- what a piece is ------------------------------------------------------------------------------------------------
CATEGORIES = [
    ("light", r"Candleabra|Candelabra|Brazier|^Lantern|Sconce|Sconse|^Torch|Chandelier|FlameBasin|IncenseBasin"),
    ("chest", r"^Chest\d|^Chest[NS][EW]$|^DunMirChest|^LOTDChest|^CryptChest"),
    ("supply", r"Barrel|Crate|^SackChest|OgreSack|^Basket|TraderAppleCrate|^Keg"),
    ("cauldron", r"^Cauldron"),
    ("hearth", r"Fireplace|FirePit"),
    ("stove", r"^Stove|Oven"),
    # the confinement and work rooms' pieces, which have no furniture family (kit/roomtypes.py: torture chambers, cells,
    # winch rooms, workshops, ossuaries, conservatories): their counts per room come from Westwood's evidence rooms
    ("torture", r"^TortureRack"),
    ("restraint", r"^IronMaiden|^Stocks\d"),
    ("gearwork", r"^Gear\d|^PulleyGear|^MechGear|^MineOreCartWheel"),
    ("bones", r"^(Skull|ArmBone|LegBone|RibCage|Bones?\d*)$"),
    ("monument", r"^Monument\d"),
    ("feature", r"^Fountain$|^WishingWell$"),
    ("hanging", r"^StarChart|^Zodiac"),
]
FAMILY_CAT = {"wall_decor": "hanging", "shelves": "shelf", "shop_rack": "rack", "storage": "supply", "stove": "stove",
              "fireplace": "hearth"}
_CAT_RX = [(c, re.compile(p)) for c, p in CATEGORIES]
FIRES = {"hearth", "cauldron", "stove"}


def kind(t):
    """A type without its number, letter or direction: the piece it is (Chest of Chest3, Statue of Statue2a)."""
    return re.sub(r"(\d+[a-z]?|HalfFull|Empty|Immobile|Shadow|Base|NE|NW|SE|SW|N|S|E|W)+$", "", t or "") or t


@lru_cache(None)
def _families():
    """rules/room_types.py FAMILIES, read from its source (the rules package is not importable from the kit)."""
    p = os.path.join(os.path.dirname(os.path.dirname(HERE)), "rules", "room_types.py")
    src = open(p, encoding="utf-8").read()
    start = src.index("FAMILIES = [")
    fams = eval(src[start + len("FAMILIES = "):src.index("\n]\n", start) + 2])
    return tuple((f, re.compile(rx)) for f, rx in fams)


def category(t):
    """A piece's category: chest, supply, cauldron, hearth, stove, light, else its furniture family (rules/room_types.py),
    hangings as "hanging", shelves as "shelf", racks as "rack"."""
    t = t or ""
    for c, rx in _CAT_RX:
        if rx.search(t): return c
    for f, rx in _families():
        if rx.search(t): return FAMILY_CAT.get(f, f)
    return None


@lru_cache(None)
def kb():
    try:
        with open(KB_PATH, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return dict(kinds={}, cat_pairs={}, hung_over={}, clusters={}, lights={}, types={})


def profile(t):
    """The kind's measured profile (rules/out/objects.json kinds), or None."""
    return kb()["kinds"].get(kind(t))


# ---- multiplicity: showpieces, fabric, runs -------------------------------------------------------------------------
# Westwood's own showpieces (rules/out/objects.json role "showpiece": once in a room, alone, measured on 20+ pieces) and
# the house's (kit/furnish.py SHOWPIECES: a telescope, an orrery, generators as one pair; the cauldron: "There should only
# be a maximum of one cauldron per room", Harrowby). Sets are no showpieces however Westwood counted them (a bunk room's
# beds, a feast's oval tables), so beds, tables, seats, rugs, plants and the bar's pieces are left out.
SET_CATS = {"bed", "table", "chair", "bench", "rug", "plant", "counter_bar", "supply", "shelf", "straw", "tomb", "column",
            "light", "hanging", "clutter"}
HOUSE_SHOWPIECES = re.compile(r"^(AlchemistDesk|Vandegraf|Telescope|Orrery|SentryGlobe|CrystalBall|Desk|Cauldron|Anvil|"
                              r"Bellows|CinderBin|TraderDesk|Fireplace|WallFireplace|DunMirThrone|"
                              r"LOTDLichThrone|DunMirAltar)")
SHOWPIECE_TWICE = {"Vandegraf": 2}           # generators stand as a pair
TWICE_IN_HALL = {"hearth"}                    # a great hall of 240 tiles or more may have a hearth at each end
HALL_TILES, TWICE_GAP = 240, 10.0
# Pieces that may line a wall end to end whatever Westwood's sample says: a bench of wizards' workstations of three kinds
# (Wiz07D), a trader's shelves of goods, a lich's tombstones in rows. Everything else lines a wall only if Westwood's runs
# of it are long (role "fabric": bookcases, straw).
HOUSE_FABRIC = re.compile(r"^(Bookcase|WizardWorkstation|TraderShelves|Straw|OgreStraw|BarPiece|BarCorner)")
# Two pieces stand side by side when their edges are within RUN_GAP units (rules/objects.py measures Westwood's runs so):
# round sacks a step apart read as a row as much as crates that touch
RUN_GAP = 1.2
# the most of one kind side by side along a wall where Westwood's sample is thin (fewer than RUN_MIN wall pieces)
RUN_MIN = 20
RUN_DEFAULT = {"shelf": 2, "supply": 2, "rack": 2, "statue": 1, "chest": 1, "lab": 2, "bed": 1, "nightstand": 1,
               "desk": 1, "hearth": 1, "stove": 1, "cauldron": 1, "table": 1, "plant": 2}


def role(t):
    """"showpiece", "fabric" or "piece" (stands alone, in a pair or in a short run)."""
    k, c = kind(t), category(t)
    if HOUSE_FABRIC.match(t or ""): return "fabric"
    p = profile(t)
    if HOUSE_SHOWPIECES.match(t or "") or c == "cauldron": return "showpiece"
    if p and p["n"] >= 20 and c not in SET_CATS:
        if p["role"] == "showpiece": return "showpiece"
    if p and p["wallpieces"] >= RUN_MIN and p["role"] == "fabric": return "fabric"
    return "piece"


def lineable(t):
    """May line a wall end to end (Harrowby: "The shelves lining the northwest and northeast walls are the kind of objects
    that can be used to span an entire wall, lined up side by side"; "some objects are suitable for lining an entire
    wall, and some are not")."""
    return role(t) == "fabric"


def max_run(t):
    """The most pieces of t's kind that stand side by side along one wall (None: no limit, it lines walls). Westwood's
    longest run that 3% of its wall pieces stand in (and 3 of them at least); where it has fewer than RUN_MIN wall
    pieces of the kind, the category's default."""
    if lineable(t): return None
    p = profile(t)
    if p and p["wallpieces"] >= RUN_MIN:
        runs = {int(k): v for k, v in p["runs"].items()}
        n = sum(runs.values()) or 1
        best = 1
        for L, v in sorted(runs.items()):
            if v >= 3 and v / n >= 0.03: best = L
        return best
    return RUN_DEFAULT.get(category(t), 2)


def wall_cap(t):
    """The most pieces of t's kind along one wall, side by side or spaced out (None: no cap): a piece that does not line
    walls never repeats down a whole wall, however far apart (Harrowby: "a tendency to line walls with things like sacks
    and barrels ... roughly evenly spread out ... Repeating the same item along the entire length of a wall is not
    realistic"). Shelves and racks: their longest run, at least 2; supplies one more than their longest run, at least 3;
    statues 2."""
    mr = max_run(t)
    if mr is None: return None
    c = category(t)
    if c in ("shelf", "rack"): return max(2, mr)
    if c == "supply": return max(3, mr + 1)
    if c == "statue": return 2
    return None


def chest_cap(room_type, tiles):
    """The most chests a room holds: its type's p90 in Westwood's rooms, at least 1; a bedroom 1, a chamber of 100 tiles
    2 ("Too many treasure chests in this room. Let's be real. Why are there four treasure chests?", Harrowby)."""
    if room_type == "bedroom": return 2 if tiles >= 100 else 1
    t = kb()["types"].get(room_type or "", {})
    p90 = (t.get("chests") or {}).get("p90", 1)
    return max(1, min(3, int(p90)))


def room_cap(t, room_type, tiles):
    """The most pieces of t's kind (a chest: of chests) a room of `room_type` and `tiles` floor tiles holds, or None."""
    c = category(t)
    if c == "chest": return chest_cap(room_type, tiles)
    if c == "cauldron": return 1
    if c == "table": return table_cap(room_type, tiles)
    if c == "statue" and kind(t) == "Statue":
        # statues by the type's Westwood p90 per room, a pair at least (a living room 2, a library 4, a hall 12)
        st = (kb().get("types", {}).get(room_type or "", {}).get("statues") or {})
        if st: return max(2, int(st.get("p90", 0)))
    ev = evidence_cap(t, room_type, tiles)
    if ev is not None: return ev
    if role(t) == "showpiece":
        k = kind(t)
        for stem, n in SHOWPIECE_TWICE.items():
            if k.startswith(stem): return n
        if c in TWICE_IN_HALL and tiles >= HALL_TILES: return 2
        # a type whose Westwood rooms hold more than one (an observatory's three telescopes, Con07B)
        own = ((profile(t) or {}).get("count") or {}).get(room_type or "")
        return max(1, int(own["max"])) if own and c != "cauldron" else 1
    return None


# Tables in private and work rooms: Westwood's p90 per room of the type, more in a room bigger than its p90 room (a
# bedroom: 1 whatever its size, the playtest's hard rule: "A bedroom should never have more than one table and chair
# set"); the public and ceremonial rooms seat their tables in sets their types cap (kit/roomtypes.py caps)
TABLE_TYPES = {"bedroom", "living_room", "study", "library", "kitchen", "herbalist", "laboratory", "smithy", "storeroom",
               "armoury", "barracks"}


def table_cap(room_type, tiles):
    if room_type == "bedroom": return 1
    if room_type not in TABLE_TYPES: return None
    t = kb()["types"].get(room_type, {})
    p90 = max(1, int((t.get("tables") or {}).get("p90", 1)))
    big = max(1.0, tiles / max(20, (t.get("tiles") or {}).get("p90", 60)))
    return max(1, int(round(p90 * min(big, 2.5))))


# categories whose per-room count is Westwood's own in the evidence rooms of each type (kit/roomtypes.py evidence):
# rules/out/objects.json kinds[k]["count"][type]["max"]
EVIDENCE_CATS = {"torture", "restraint", "gearwork", "monument", "feature"}


def evidence_cap(t, room_type, tiles):
    """The most of t's kind a room of `room_type` holds where Westwood's evidence rooms of the type hold it (their max,
    twice that in a room twice their median size), else None."""
    if category(t) not in EVIDENCE_CATS: return None
    p = profile(t)
    c = (p or {}).get("count", {}).get(room_type or "")
    if not c: return None
    ty = kb().get("types", {}).get(room_type or "", {})
    p50 = ((ty.get("tiles") or {}).get("p50") or tiles)
    return max(1, int(c["max"])) * (2 if tiles >= 2 * p50 else 1)


def cap_key(t):
    """What room_cap counts: chests together, cauldrons together, else the kind."""
    c = category(t)
    return c if c in ("chest", "cauldron", "table") else kind(t)      # statues: kind Statue (Statue2a-h)


def light_cap(tiles):
    """The most floor lights (candelabras) a room of `tiles` floor tiles takes: Westwood's p90 per room, by size (2 under
    40 tiles, 3 under 100, 5 over 100: rules/out/objects.json lights), one more for every 120 tiles past 200 (our rooms
    run larger). Harrowby's 143-tile study had 8 ("Too many candelabras")."""
    L = kb().get("lights", {})
    small = (L.get("small", {}).get("count") or {}).get("p90", 2) or 2
    medium = (L.get("medium", {}).get("count") or {}).get("p90", 3) or 3
    large = (L.get("large", {}).get("count") or {}).get("p90", 5) or 5
    if tiles < 40: return max(1, small)
    if tiles < 100: return medium
    if tiles < 200: return min(large, medium + 1)
    return large + int((tiles - 200) // 120)


# ---- clearances -----------------------------------------------------------------------------------------------------
# The playtest's floors (uv units, edge to edge), over Westwood's p5: "bed is way too close to one of the cauldrons. The
# bench is too close to the bed. Chest is way too close to the other cauldron" (a cottage); "The two treasure chests are
# both too close to the hearth" (the moot hall); "two statues way too close to each other" (a library).
HOUSE_CLEAR = {("bed", "hearth"): 2.0, ("bed", "cauldron"): 2.0, ("bed", "stove"): 2.0,
               ("chest", "hearth"): 3.0, ("chest", "cauldron"): 2.0, ("chest", "stove"): 2.0,
               ("bed", "bench"): 1.2, ("statue", "statue"): 2.0, ("cauldron", "cauldron"): 4.0,
               ("table", "cauldron"): 1.0, ("bench", "cauldron"): 1.0}
# categories whose spacing is kept by their own rules (seats at their table, lights by the light pass, plants in
# corners, hangings on the wall, rugs under things), or that stand in composed sets
CLEAR_SKIP = {"chair", "light", "plant", "rug", "hanging", "clutter", "column", "counter_bar", "straw", "tomb", "lab",
              "rack", "shelf", "nightstand", "smithy", "throne", "altar", "counter_shop", "desk"}
CLEAR_MIN_N, CLEAR_MIN_P5, CLEAR_SHARE, CLEAR_MAX = 10, 0.9, 0.8, 3.0
ALIAS = {"cauldron": "stove"}          # a cauldron is measured with the stoves (Westwood has few cauldrons indoors)


@lru_cache(None)
def clearances():
    """{(a, b): least edge gap in uv units} for unordered category pairs: CLEAR_SHARE of Westwood's p5 where it keeps the
    pair at least CLEAR_MIN_P5 apart (measured on CLEAR_MIN_N pieces), at most CLEAR_MAX; the house floors over it."""
    out = {}
    cp = kb().get("cat_pairs", {})
    cats = {k.split("|")[0] for k in cp} | {"cauldron"}
    for a in cats:
        for b in cats:
            if a > b or a in CLEAR_SKIP or b in CLEAR_SKIP: continue
            vals = []
            for x, y in ((a, b), (b, a)):
                rec = cp.get(f"{ALIAS.get(x, x)}|{ALIAS.get(y, y)}")
                if rec and rec["n"] >= CLEAR_MIN_N: vals.append(rec["p5"])
            if vals and min(vals) >= CLEAR_MIN_P5:
                out[(a, b)] = round(min(CLEAR_MAX, CLEAR_SHARE * min(vals)), 2)
    for (a, b), g in HOUSE_CLEAR.items():
        key = tuple(sorted((a, b)))
        out[key] = max(out.get(key, 0.0), g)
    return out


def clearance(a, b):
    """The least gap (uv units, edge to edge) between pieces of categories a and b; 0 when Westwood lets them touch."""
    if not a or not b: return 0.0
    return clearances().get(tuple(sorted((a, b))), 0.0)


NEVER_MIN = 20         # pieces of a kind Westwood's "never next to" list stands on
NEXT_GAP = 1.0         # uv units, edge to edge: standing next to each other (rules/objects.py NEXT_GAP)


def never_next(t):
    """The categories a piece of t's kind never stands next to (within NEXT_GAP) in Westwood's rooms although they share
    its rooms (rules/out/objects.json never: a bed never beside a bench, a desk or supplies; a round table never beside
    a bed, a chest or a hearth; a fireplace never beside a bench or a table; a nightstand never beside a table)."""
    p = profile(t)
    if not p or p["n"] < NEVER_MIN: return frozenset()
    return frozenset(p.get("never") or ())


# Hangings Westwood hangs in rows (tapestries, banners, shields: a room of 8-14 of one kind) and those it hangs one at a
# time (trophies, paintings: one or two to a room): the latter stand at most HANG_SAME of a kind on one wall, so a wall
# never reads as a row of one moose head (the rule that keeps a run of one floor piece short, max_run)
HANG_ROWS = re.compile(r"Tapestry|Banner|HangingShield|ShieldWallHanging|CrossedWeapons")
HANG_SAME = 2


def hang_cap(t):
    """The most hangings of t's kind on one wall (None: no cap)."""
    return None if HANG_ROWS.search(t or "") else HANG_SAME


def hangs_over(cat):
    """Whether a hanging may hang above a floor piece of this category standing against the same wall: never (Westwood:
    rules/out/objects.json hung_over, 0-3% of wall pieces of every category; Harrowby: "trophies on the wall with statues
    right on top of them. Double-placed objects")."""
    return cat in (None, "hanging", "rug")


# ---- supplies in clusters -------------------------------------------------------------------------------------------
def supply_clusters():
    """Westwood's supply clusters: dict(size: {n: share}, gap: {p25, p50, p75}, mixed: share of clusters of 2+ with two
    kinds or more)."""
    c = kb().get("clusters") or {}
    size = {int(k): v for k, v in (c.get("size") or {}).items()}
    tot = sum(size.values()) or 1
    return dict(size={k: v / tot for k, v in size.items()}, gap=c.get("gap") or {"p25": 1.1, "p50": 2.6, "p75": 6.4},
                mixed=c.get("mixed", 0.3))
