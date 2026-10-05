"""One measure of a room's density and openness, used both on Westwood's rooms (rules/rooms/westwood.py, which sets each
room type's ranges in mapgen/kit/roomtypes.py) and on ours (review/roomscore.py, which judges a room against its type).

    measure(m, r) -> dict

- tiles, cells: floor tiles (the checker's count) and grid cells;
- cover: the share of the floor that blocking furniture covers (validate/checks.py room_coverage);
- middle: the share covered by blocking pieces standing free, more than 2.5 units from every wall;
- open: the share of the floor more than OPEN_GAP units from every blocking piece: floor a body can stand on and
  walk through (a throne room is mostly open, a storeroom little);
- pieces, per_tile: the room's furnishings (every piece with a furniture family, hangings and rugs included, not lights)
  and how many per floor tile;
- types: distinct object types among them;
- most: (kind, n) the piece repeated most (a kind: the type without its number or direction, Column of Column5-8);
- free_most: (kind, n) the same over pieces that stand alone (not the kinds that line walls or stand in rows);
- walls: how many of its four walls have a purpose (a piece other than a light against it);
- lined: the share of its back walls (NE and NW, the walls the camera sees) taken by tall pieces and hangings, less
  3 units for each doorway in them;
- fam: family -> count (rules/room_types.py families); kinds: piece kind -> count over the furnishings; all_kinds: over
  every object but lights (a forge's coals have no furniture family).
"""
import collections, math, os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ("validate", "mapgen", "rules"):
    if os.path.join(REPO, p) not in sys.path: sys.path.insert(0, os.path.join(REPO, p))
import checks as C

OPEN_GAP = 1.2           # uv units (about 20 px) clear of every blocking piece: room to stand and pass

# kinds that stand in rows or line walls by design: not counted as a piece repeated alone
LINED = re.compile(r"^(Bookcase|MovableBookcase|LogShelves|PotionShelves|WizardWorkstation|Trader|Bed|WoodBed|Cot|Bench|"
                   r"LightBench|CushionedBench|Crypt|Coffin|Column|CathedralColumn|LOTD|Barrel|Crate|DarkCrate|Sack|"
                   r"PiledBarrels|LargeBarrel|WaterBarrel|BarrelWithTools|Candleabra|Nightstand|Chest|OgreStraw|BarPiece|"
                   r"BarCorner|BarHinged)")
from kit.furnish import TALL_PIECES as TALL   # one list: the furnisher lines walls by the same measure


def kind_of(t):
    """An object type without its number, letter or direction: the piece it is (Column of Column5)."""
    return re.sub(r"(\d+[a-z]?|HalfFull|Empty|Immobile|Shadow|Base|NE|NW|SE|SW|N|S|E|W)+$", "", t) or t


def _dist_to_piece(u, v, o):
    ou, ov = C.uv_of(o)
    hu, hv = C._half_uv(o)
    if o["ext"] == "BOX":
        return math.hypot(max(0.0, abs(u - ou) - hu), max(0.0, abs(v - ov) - hv))
    return max(0.0, math.hypot(u - ou, v - ov) - hu)


def measure(m, r):
    cells = r["cells"]
    runs = C.room_runs(m, cells)
    cu = sum(x + y + 1 for x, y in cells) / len(cells); cv = sum(x - y for x, y in cells) / len(cells)
    objs = r["objects"]
    fam = collections.Counter(C.RT.family(o["type"]) for o in objs)
    fam.pop(None, None)
    pieces = [o for o in objs if C.RT.family(o["type"])]
    block = [o for o in pieces if m.blocking(o) and C.RT.family(o["type"]) in C.RT.BLOCKING_FAMILIES]
    # the middle and the open floor
    mid = 0.0
    for o in block:
        u, v = C.uv_of(o)
        dist = min((abs(u - c) if l == "/" else abs(v - c)) for (l, c) in runs) if runs else 0
        if dist > 2.5: mid += C.piece_area(o)
    near = [(C.uv_of(o), o) for o in block]
    open_cells = 0
    for x, y in cells:
        u, v = x + y + 1, x - y
        if all(abs(u - pu) > 4 or abs(v - pv) > 4 or _dist_to_piece(u, v, o) > OPEN_GAP for (pu, pv), o in near):
            open_cells += 1
    # walls used and back walls lined
    back_len, back_used, used = 0.0, collections.defaultdict(list), set()
    doors = [(d["gap"][0] + d["gap"][1] + 1, d["gap"][0] - d["gap"][1]) for d in m.doors]
    for (line, coord), (a0, a1) in runs.items():
        if C._wall_name(line, coord, cu, cv) not in ("NE", "NW"): continue
        back_len += a1 - a0
        for du, dv in doors:
            if abs((du if line == "/" else dv) - coord) < 1.6 and a0 < (dv if line == "/" else du) < a1:
                back_len -= 3.0
    for o in pieces:
        hit = C._against(o, runs, cu, cv, m, reach=1.6, across=True)
        if not hit: continue
        used.add(hit[0])
        if (TALL.match(o["type"]) or C.RT.family(o["type"]) == "wall_decor") and hit[0] in ("NE", "NW"):
            ha = C._half_uv(o)[1] if hit[3] == "/" else C._half_uv(o)[0]
            back_used[(hit[3], hit[4])].append((hit[2] - ha, hit[2] + ha))
    lined_len = 0.0
    for spans in back_used.values():
        spans.sort(); end = -1e9
        for a, b in spans:
            if b <= end: continue
            lined_len += b - max(a, end); end = b
    kinds = collections.Counter(kind_of(o["type"]) for o in pieces)
    free = collections.Counter(kind_of(o["type"]) for o in pieces
                               if not LINED.match(o["type"]) and C.RT.family(o["type"]) not in ("wall_decor", "rug"))
    tiles = r.get("tiles") or sum(1 for p in cells if p in m.tiles)
    return dict(tiles=tiles, cells=len(cells), cover=C.room_coverage(m, r), middle=mid / (2 * len(cells)),
                open=open_cells / len(cells), pieces=len(pieces), per_tile=len(pieces) / max(1, tiles),
                types=len({o["type"] for o in pieces}),
                most=kinds.most_common(1)[0] if kinds else ("", 0),
                free_most=free.most_common(1)[0] if free else ("", 0),
                walls=len(used), lined=min(1.0, lined_len / back_len) if back_len > 0 else 0.0,
                fam=dict(fam), kinds=dict(kinds), runs=runs, centre=(cu, cv),
                all_kinds=dict(collections.Counter(kind_of(o["type"]) for o in objs if not C.LIGHT_NAME.search(o["type"]))))
