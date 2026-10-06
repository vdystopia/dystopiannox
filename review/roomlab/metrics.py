"""The room lab's metric judge: what a room is made of and how it is laid out, compared with Westwood's campaign rooms
of the same type, and whether a classifier can tell our rooms from Westwood's.

    py review/roomlab/metrics.py <type> <iter>      re-judge an iteration already generated (tests/roomlab.py does this)
    py review/roomlab/metrics.py --westwood          re-measure every Westwood campaign room (review/roomlab/
                                                     westwood_features.json, from rules/rooms/westwood.json's index)

Needs numpy and scikit-learn (py -m pip install --user numpy scikit-learn).

## Features per room (features(); the same code measures Westwood's rooms and ours)

- cover, open, middle, per_tile, types, most_share, free_most, walls, lined: review/roommeasure.py's measures (the
  share of the floor covered, open floor, pieces standing free in the middle, pieces per tile, distinct types, the
  share of the most common kind, the most of one stand-alone kind, walls with a purpose, back walls lined);
- fam_<family>: pieces of each family (rules/room_types.py) per 10 floor tiles;
- wall_share, mid_share, wall_gap: the share of blocking pieces against a wall, the share more than 2.5 units from
  every wall, and the median gap from a wall piece's back to its wall (snugness);
- max_run, runs3: the longest run of one kind along a wall, and how many runs of 3+ of one kind there are;
- showpiece_rep: showpieces (kit/furnish.py SHOWPIECES: an alchemist's desk, a telescope, a desk...) repeated;
- nn_p10, nn_med: the gap from each blocking piece to its nearest neighbour (10th percentile and median, uv units);
  details["pairs"] holds the median gap per family pair;
- overlaps: pairs of blocking pieces overlapping by more than 0.3 units, per 10 blocking pieces;
- focal_n, focal_back, focal_door: the type's focal piece (kit/roomtypes.py focal): how many, whether it stands on a
  back wall (NE or NW), and its distance from the farthest door over the room's diagonal (1 = across the room);
- way_in, way_in_frac: the clear way in from the doors: the depth straight in before the first blocking piece (units,
  the worst door) and that depth over the room's depth;
- sym, align: mirror symmetry (the share of pieces with a piece of the same family at their mirror image across the
  room's middle, the better axis) and alignment (the share sharing a row or column with a piece of the same kind);
- statues_to_wall, front_faced, odd_facing: statues facing a wall; the share of faced pieces (shelves, hearths,
  stoves, desks, lab benches, chests, hangings) on the front walls (SE, SW) the camera sees only the backs of; pieces
  against a wall in a variant Westwood seldom uses on that wall (under 10% of that kind there);
- lights_per_tile, doors.

## Comparison (compare())

Each feature is placed in Westwood's distribution for the type (its campaign rooms of the same culture when there are
6 or more, else every culture): a percentile, and a finding when it falls outside p10-p90 (outside the range when
Westwood has under 10 rooms), worded as a plain-English critique with where to change it. A type with under 6
Westwood rooms (tavern, study, chapel, great hall, smithy, herbalist, dining hall, throne room) is compared with its
pool instead: the Westwood types the profile names (kit/roomtypes.py westwood) and the rest of its family, and said so.
Every room is also compared on the cross-type features (CROSS: spacing, overlaps, snugness, rows, symmetry, facing,
the way in) with every curated Westwood room, and judged against the user's rules in the type's brief (review/roomscore.py
judge: must, never, focal, caps, repeat, reads as; plus overlaps, statues facing walls, a blocked way in): these are
the hard-rule findings.

## Distinguishability (classify())

A logistic regression (standardised features, L2) learns Westwood against generated over the type's features (not
the size, nor the door count the harness sets), cross-validated (stratified k-fold, k up to 5, repeated 10 times with
fixed seeds): the AUC is how well it tells them apart, 0.5 meaning it cannot. Each feature's own AUC shows which
features give the batch away. With under 6 Westwood rooms the type's pool is used and the result marked as a fallback.
"""
import collections, json, math, os, random, re, statistics, sys
import labenv as E
C = E.C
import roommeasure as RM
from kit.roomtypes import TYPES, profile, KIND_TYPE
from kit.furnish import SHOWPIECES, TALL_PIECES

RT = C.RT
MIN_WW = 6                  # Westwood rooms a type needs to be judged on its own
FACED = re.compile(r"Bookcase|Shelves|Fireplace|Stove|Cauldron|Desk|AlchemistDesk|WizardWorkstation|^Chest|DunMirChest|"
                   r"Tapestry|Painting|Trophy|HangingShield|Banner|ClothSign|WallHanging|CrossedWeapons|HangingSwords")
LETTER = {"a": (1, 0), "b": (1, 1), "c": (0, 1), "d": (-1, 1), "e": (-1, 0), "f": (-1, -1), "g": (0, -1), "h": (1, -1)}
FAMS = ["bed", "nightstand", "storage", "table", "chair", "bench", "desk", "shelves", "fireplace", "stove", "lab",
        "smithy", "counter_bar", "counter_shop", "shop_rack", "altar", "throne", "tomb", "statue", "column", "straw",
        "plant", "wall_decor", "rug", "clutter"]
# features compared with Westwood, in report order; CROSS: those that mean the same in every type
CORE = ["cover", "open", "middle", "per_tile", "types", "most_share", "free_most", "walls", "lined", "wall_share",
        "mid_share", "wall_gap", "max_run", "runs3", "showpiece_rep", "nn_p10", "nn_med", "overlaps", "focal_n",
        "focal_back", "focal_door", "way_in", "way_in_frac", "sym", "align", "statues_to_wall", "front_faced",
        "odd_facing", "lights_per_tile"]
CROSS = ["wall_gap", "nn_p10", "nn_med", "overlaps", "wall_share", "mid_share", "align", "sym", "way_in_frac",
         "front_faced", "statues_to_wall", "odd_facing", "lights_per_tile", "most_share"]
NOT_CLASSIFIED = {"doors"}
# feature: (what it is, critique when low, critique when high, where to change it)
TEXT = {
    "cover": ("floor covered", "too sparse: furniture covers {v} of the floor", "too full: furniture covers {v} of the floor",
              "kit/roomtypes.py cover (the furnisher's target); the type's recipe in kit/identity.py ROOMS"),
    "open": ("open floor", "too little open floor ({v}): the room is cramped", "too much open floor ({v}): the room reads empty",
             "kit/roomtypes.py cover and open; the recipe's fill"),
    "middle": ("floor covered in the middle", "nothing stands free in the middle ({v}): every piece hugs a wall",
               "too much in the middle ({v}): the middle is crowded", "the recipe's middle group (kit/identity.py ROOMS compose)"),
    "per_tile": ("pieces per tile", "too few pieces ({v} per tile)", "too many pieces ({v} per tile): cluttered",
                 "kit/roomtypes.py per_tile; the recipe's fill and top-up"),
    "types": ("distinct object types", "too little variety ({v} kinds of object)", "more kinds of object than Westwood ({v})",
              "the recipe's may-have pieces (kit/identity.py ROOMS)"),
    "most_share": ("share of the most common kind", "no kind dominates ({v})",
                   "one kind dominates ({v} of the pieces): monotonous", "kit/roomtypes.py caps and free_most"),
    "free_most": ("most of one stand-alone piece", "", "a stand-alone piece repeated {v} times",
                  "kit/roomtypes.py free_most; kit/identity.py ROOMS repeat"),
    "walls": ("walls with a purpose", "only {v} walls used: bare walls", "", "the recipe's wall groups"),
    "lined": ("back walls lined", "back walls (NE, NW) bare: {v} lined", "back walls lined more than Westwood's ({v})",
              "kit/roomtypes.py lined; kit/furnish.py line_wall"),
    "wall_share": ("pieces against a wall", "too few pieces against the walls ({v}): furniture floats",
                   "everything against the walls ({v}): nothing in the middle", "the recipe's middle group; FRONT_WEIGHT"),
    "mid_share": ("pieces standing free in the middle", "nothing stands in the middle ({v})",
                  "too many pieces in the middle ({v})", "the recipe's middle group"),
    "wall_gap": ("gap from a wall piece's back to its wall", "wall pieces tighter to the wall than Westwood's ({v} units)",
                 "wall pieces stand off their walls ({v} units): they float", "kit/furnish.py SNUG_GAP"),
    "max_run": ("longest run of one kind along a wall", "no runs of one kind along the walls ({v})",
                "a run of {v} of one kind along one wall", "kit/furnish.py line_wall; complete_bookcase_walls"),
    "runs3": ("runs of 3+ of one kind along walls", "no lined runs ({v})", "{v} runs of 3+ of one kind along the walls",
              "kit/furnish.py line_wall"),
    "showpiece_rep": ("showpieces repeated", "", "a showpiece repeated ({v} extra): it should stand once",
                      "kit/furnish.py SHOWPIECES; kit/identity.py ROOMS repeat"),
    "nn_p10": ("closest gaps between pieces (p10)", "pieces jammed together (p10 gap {v} units)",
               "even the closest pieces stand far apart ({v} units)", "kit/furnish.py spacing (SPACING, the recipe's gaps)"),
    "nn_med": ("typical gap to the nearest piece", "pieces crowd each other (median gap {v} units)",
               "pieces stand apart, each alone (median gap {v} units): no groups", "the recipe's groups (sets, pairs)"),
    "overlaps": ("overlapping pieces per 10", "", "pieces overlap ({v} per 10 pieces)", "kit/furnish.py placement (fits)"),
    "focal_n": ("focal pieces", "no focal piece", "{v} focal pieces (the type's focal kind)", "kit/roomtypes.py focal; the recipe's anchor"),
    "focal_back": ("focal piece on a back wall", "the focal piece is not on a back wall (NE or NW)", "",
                   "kit/roomtypes.py focal where"),
    "focal_door": ("focal piece's distance from the door", "the focal piece sits near the door ({v} of the diagonal)",
                   "the focal piece is far across the room from its door ({v})", "the recipe's anchor placement"),
    "way_in": ("clear way in from the doors (units)", "the way in is blocked {v} units inside a door",
               "", "kit/furnish.py DOOR_WAY_*"),
    "way_in_frac": ("clear way in over the room's depth", "the way in is blocked early ({v} of the depth)",
                    "the way in is clear further than Westwood's ({v})", "kit/furnish.py DOOR_WAY_*"),
    "sym": ("mirror symmetry", "less symmetric than Westwood's ({v})", "more symmetric than Westwood's ({v}): too regular",
            "the recipe's pairs (kit/identity.py ROOMS)"),
    "align": ("pieces in rows", "pieces out of line ({v} share a row): scattered", "everything in rows ({v}): grid-like",
              "kit/furnish.py placement on rows"),
    "statues_to_wall": ("statues facing a wall", "", "{v} statue(s) face a wall", "kit/furnish.py face_statues"),
    "front_faced": ("faced pieces on the front walls", "", "{v} of the faced pieces (shelves, hearths, chests, "
                    "hangings) stand on the front walls (SE, SW), showing their backs", "kit/furnish.py FRONT_WEIGHT; walls"),
    "odd_facing": ("pieces in a variant Westwood seldom uses on that wall", "",
                   "{v} pieces face the wrong way for their wall", "kit/furnish.py WALL_SIDE_TYPE, along_variant"),
    "lights_per_tile": ("lights per tile", "too dark: {v} lights per tile", "too many lights ({v} per tile)",
                        "kit/furnish.py lights"),
}
for _f in FAMS:
    TEXT[f"fam_{_f}"] = (f"{_f.replace('_', ' ')} pieces per 10 tiles", f"fewer {_f.replace('_', ' ')} pieces than "
                         f"Westwood's ({{v}} per 10 tiles)", f"more {_f.replace('_', ' ')} pieces than Westwood's ({{v}} "
                         f"per 10 tiles)", "the recipe (kit/identity.py ROOMS) and caps (kit/roomtypes.py)")


# ---------------------------------------------------------------------------------------------------- geometry
def half(o):
    return C._half_uv(o)


def gap(a, b):
    """Signed gap between two pieces' footprints (uv units; negative: they overlap by that much)."""
    (ua, va), (ub, vb) = C.uv_of(a), C.uv_of(b)
    (hua, hva), (hub, hvb) = half(a), half(b)
    du, dv = abs(ua - ub) - (hua + hub), abs(va - vb) - (hva + hvb)
    if du > 0 or dv > 0: return math.hypot(max(0.0, du), max(0.0, dv))
    return max(du, dv)


def room_doors(m, r, cu, cv):
    """[(u, v, inward (du, dv), wall name)] of the doorways into the room."""
    cells = set(r["cells"])
    out = []
    for d in m.doors:
        gx, gy = d["gap"]
        if not any((gx + a, gy + b) in cells for a in (-1, 0, 1) for b in (-1, 0, 1)): continue
        u, v = gx + gy + 1, gx - gy
        if d["line"] == "/":
            n = (1.0 if cu > u else -1.0, 0.0)
            name = C._wall_name("/", u, cu, cv)
        else:
            n = (0.0, 1.0 if cv > v else -1.0)
            name = C._wall_name("\\", v, cu, cv)
        out.append((u, v, n, name))
    return out


def _pct(vals, p):
    s = sorted(vals)
    if not s: return None
    k = (len(s) - 1) * p / 100
    f = math.floor(k); c = min(len(s) - 1, f + 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def features(m, r, typ, kind=None):
    """(features, details) of room r (a validate/checks.py find_rooms room) judged as room type `typ`."""
    me = RM.measure(m, r)
    cells = r["cells"]
    cu, cv = me["centre"]
    runs = me["runs"]
    tiles = max(1, me["tiles"])
    objs = r["objects"]
    pieces = [o for o in objs if RT.family(o["type"])]
    block = [o for o in pieces if m.blocking(o) and RT.family(o["type"]) in RT.BLOCKING_FAMILIES]
    fam = collections.Counter(RT.family(o["type"]) for o in pieces)
    kinds = collections.Counter(RM.kind_of(o["type"]) for o in pieces)
    us = [x + y + 1 for x, y in cells]; vs = [x - y for x, y in cells]
    du_ext, dv_ext = max(us) - min(us) + 1, max(vs) - min(vs) + 1
    diag = math.hypot(du_ext, dv_ext)
    f = dict(tiles=me["tiles"], cover=me["cover"], open=me["open"], middle=me["middle"], per_tile=me["per_tile"],
             types=me["types"], most_share=(me["most"][1] / max(1, me["pieces"])), free_most=me["free_most"][1],
             walls=me["walls"], lined=me["lined"])
    for fm in FAMS:
        f[f"fam_{fm}"] = 10.0 * fam.get(fm, 0) / tiles
    # walls: who stands against which wall, how snug
    against = {}
    for o in pieces:
        a = C._against(o, runs, cu, cv, m, reach=1.0, across=True)
        if a: against[o["id"]] = a
    bl_ag = [o for o in block if o["id"] in against]
    f["wall_share"] = len(bl_ag) / len(block) if block else 0.0
    gaps = [against[o["id"]][1] for o in bl_ag]
    f["wall_gap"] = statistics.median(gaps) if gaps else 0.25
    mid = 0
    for o in block:
        a = C._against(o, runs, cu, cv, m, reach=2.5, across=True)
        if not a: mid += 1
    f["mid_share"] = mid / len(block) if block else 0.0
    # runs of one kind along a wall
    by_wall = collections.defaultdict(list)
    for o in pieces:
        if o["id"] in against and RT.family(o["type"]) not in ("rug",):
            name, g, along, line, coord = against[o["id"]]
            hl = half(o)[1] if line == "/" else half(o)[0]
            by_wall[(line, coord, name)].append((along, hl, RM.kind_of(o["type"])))
    run_list = []
    for (line, coord, name), ps in by_wall.items():
        ps.sort()
        cur = [ps[0]]
        for p in ps[1:]:
            q = cur[-1]
            if p[2] == q[2] and p[0] - q[0] - p[1] - q[1] <= 0.8: cur.append(p)
            else:
                run_list.append((len(cur), cur[0][2], name)); cur = [p]
        run_list.append((len(cur), cur[0][2], name))
    f["max_run"] = max((n for n, _, _ in run_list), default=0)
    f["runs3"] = sum(1 for n, _, _ in run_list if n >= 3)
    f["showpiece_rep"] = sum(max(0, n - 1) for k, n in kinds.items() if SHOWPIECES.match(k))
    # nearest neighbours and overlaps
    nn, pairs, overl = [], collections.defaultdict(list), 0
    for i, a in enumerate(block):
        best = None
        for j, b in enumerate(block):
            if i == j: continue
            g = gap(a, b)
            if best is None or g < best[0]: best = (g, b)
            if j > i and g < -0.3: overl += 1
        if best:
            nn.append(best[0])
            fa, fb = sorted((RT.family(a["type"]), RT.family(best[1]["type"])))
            pairs[f"{fa}|{fb}"].append(best[0])
    f["nn_p10"] = _pct(nn, 10) if nn else 0.0
    f["nn_med"] = statistics.median(nn) if nn else 0.0
    f["overlaps"] = 10.0 * overl / max(1, len(block))
    # the focal piece and the doors
    doors = room_doors(m, r, cu, cv)
    f["doors"] = len(doors)
    p = profile(kind) if kind and KIND_TYPE.get(kind) else dict(TYPES.get(typ, {}), type=typ)   # a passage has none
    fo = p.get("focal")
    foc = [o for o in objs if fo and re.search(fo["types"], o["type"])]
    if fo and fo.get("fam") == "throne": foc = foc[:1]
    f["focal_n"] = len(foc)
    if foc:
        o = foc[0]
        a = C._against(o, runs, cu, cv, m, reach=fo.get("reach", 1.8), across=True)
        f["focal_back"] = 1.0 if a and a[0] in ("NE", "NW") else 0.0
        ou, ov = C.uv_of(o)
        f["focal_door"] = max((math.hypot(ou - du, ov - dv) for du, dv, _, _ in doors), default=0.0) / diag
    else:
        f["focal_back"], f["focal_door"] = None, None
    # the clear way in: straight in from each door, a corridor 1.15 units either side of the door's line
    ways = []
    for du, dv, (nu, nv), _ in doors:
        depth = du_ext if nu else dv_ext
        first = depth
        for o in block:
            ou, ov = C.uv_of(o)
            t = (ou - du) * nu + (ov - dv) * nv
            side = abs((ou - du) * nv - (ov - dv) * nu)
            hu, hv = half(o)
            h_along, h_side = (hu, hv) if nu else (hv, hu)
            if t + h_along <= 0.3: continue
            if side - h_side < 1.15:
                first = min(first, max(0.0, t - h_along))
        ways.append((first, first / max(1.0, depth)))
    f["way_in"] = min((w for w, _ in ways), default=0.0)
    f["way_in_frac"] = min((w for _, w in ways), default=0.0)
    # symmetry and rows
    sym_set = [o for o in pieces if RT.family(o["type"]) in RT.BLOCKING_FAMILIES | {"wall_decor"}]
    pos = [(C.uv_of(o), RT.family(o["type"])) for o in sym_set]
    best_sym = 0.0
    for axis in (0, 1):
        hit = 0
        for (u, v), fm in pos:
            mu, mv = (2 * cu - u, v) if axis == 0 else (u, 2 * cv - v)
            if any(fm2 == fm and math.hypot(u2 - mu, v2 - mv) <= 1.5 for (u2, v2), fm2 in pos): hit += 1
        best_sym = max(best_sym, hit / len(pos) if pos else 0.0)
    f["sym"] = best_sym
    kpos = [(C.uv_of(o), RM.kind_of(o["type"])) for o in block]
    al = 0
    for i, ((u, v), k) in enumerate(kpos):
        if any(j != i and k2 == k and (abs(u - u2) < 0.35 or abs(v - v2) < 0.35) for j, ((u2, v2), k2) in enumerate(kpos)):
            al += 1
    f["align"] = al / len(kpos) if kpos else 0.0
    # facing
    st_wall = 0
    wall_pieces = []
    faced_n = faced_front = 0
    for o in pieces:
        a = against.get(o["id"])
        if not a: continue
        name, g, along, line, coord = a
        wall_pieces.append([o["type"], RM.kind_of(o["type"]), name])
        mt = re.match(r"^Statue\d([a-h])$", o["type"])
        if mt:
            fu, fv = LETTER[mt.group(1)]
            nu, nv = ((1.0 if cu > coord else -1.0), 0.0) if line == "/" else (0.0, (1.0 if cv > coord else -1.0))
            if fu * nu + fv * nv < 0: st_wall += 1
        if FACED.search(o["type"]):
            faced_n += 1
            if name in ("SE", "SW"): faced_front += 1
    f["statues_to_wall"] = st_wall
    f["front_faced"] = faced_front / faced_n if faced_n else 0.0
    f["odd_facing"] = 0.0           # filled in by compare() from Westwood's variants by wall (details["wall_pieces"])
    lights = [o for o in objs if C.LIGHT_NAME.search(o["type"]) and RT.family(o["type"]) != "fireplace"]
    f["lights_per_tile"] = len(lights) / tiles
    # the layout, for the batch's template similarity (template()): each piece's family, where it stands (the wall it
    # is against, "mid" more than 2.5 units from every wall, else "free") and its place over the room's uv box (0-1)
    u0_, u1_, v0_, v1_ = min(us), max(us) + 1, min(vs), max(vs) + 1
    layout = []
    for o in pieces:
        fm = RT.family(o["type"])
        if fm in (None, "light", "rug"): continue
        a = against.get(o["id"])
        place = a[0] if a else ("mid" if not C._against(o, runs, cu, cv, m, reach=2.5, across=True) else "free")
        ou, ov = C.uv_of(o)
        layout.append([fm, place, round((ou - u0_) / max(1, u1_ - u0_), 3), round((ov - v0_) / max(1, v1_ - v0_), 3)])
    details = dict(kinds=dict(kinds), fam=dict(fam), wall_pieces=wall_pieces, layout=layout,
                   pairs={k: round(statistics.median(v), 3) for k, v in pairs.items()},
                   runs=[[n, k, w] for n, k, w in sorted(run_list, reverse=True) if n >= 3][:6],
                   focal=foc[0]["type"] if foc else None, doors=[w for _, _, _, w in doors],
                   overlap_pairs=[[a["type"], b["type"], round(gap(a, b), 2)] for i, a in enumerate(block)
                                  for b in block[i + 1:] if gap(a, b) < -0.3][:8])
    for k, v in f.items():
        if isinstance(v, float): f[k] = round(v, 4)
    return f, details


# ---------------------------------------------------------------------------------------------------- Westwood
_WW = None


def westwood():
    """Every Westwood campaign room's features (review/roomlab/westwood_features.json; labref.py builds it)."""
    global _WW
    if _WW is None:
        if not os.path.exists(E.WW_FEATURES):
            import labref
            labref.build_features()
        with open(E.WW_FEATURES, encoding="utf-8") as f:
            _WW = E.curate(json.load(f)["rooms"])      # the verdicts by eye (rules/rooms/curated.json)
        facing_table(_WW)
        for r in _WW: r["features"]["odd_facing"] = odd_facing(r["details"]["wall_pieces"])
    return _WW


_FACING = None


def facing_table(rooms):
    """(kind, wall) -> Counter of the exact types Westwood stands there, over every campaign room."""
    global _FACING
    t = collections.defaultdict(collections.Counter)
    for r in rooms:
        for typ, kind, wall in r["details"]["wall_pieces"]:
            t[(kind, wall)][typ] += 1
    _FACING = t
    return t


def odd_facing(wall_pieces):
    """How many pieces against a wall stand in a variant Westwood uses for under 10% of that kind on that wall (with 8
    or more of the kind there to go by), or never on that wall while it uses the kind elsewhere."""
    n = 0
    for typ, kind, wall in wall_pieces:
        c = _FACING.get((kind, wall)) if _FACING else None
        tot = sum(c.values()) if c else 0
        if tot >= 8 and c[typ] / tot < 0.10 and typ != kind: n += 1
    return float(n)


def pool(typ, culture=None):
    """(Westwood rooms to compare a room of the type with, a note on what they are). The type's own rooms of the same
    culture when there are MIN_WW, else of every culture; a type with fewer takes its pool: the Westwood types its
    profile names, then its family's other types."""
    ww = westwood()
    own = [r for r in ww if r["type"] == typ]
    if culture:
        same = [r for r in own if r["culture"] == culture]
        if len(same) >= MIN_WW: return same, f"Westwood's {len(same)} {typ.replace('_', ' ')} rooms of the {culture} culture"
    if len(own) >= MIN_WW: return own, f"Westwood's {len(own)} {typ.replace('_', ' ')} rooms"
    p = TYPES[typ]
    names = list(dict.fromkeys(p.get("westwood", (typ,))))
    rooms = [r for r in ww if r["type"] in names]
    if len(rooms) < MIN_WW:              # still thin: the rest of its family too
        names = list(dict.fromkeys(names + [t for t, q in TYPES.items() if q["family"] == p["family"]]))
        rooms = [r for r in ww if r["type"] in names]
    used = sorted({r["type"] for r in rooms})
    return rooms, (f"FALLBACK: Westwood has only {len(own)} {typ.replace('_', ' ')} room(s) (under {MIN_WW}); compared "
                   f"with the {len(rooms)} rooms of its pool ({', '.join(used)}), so read these numbers loosely and lean "
                   f"on the brief's rules (rules/rooms/{typ}.md) and the cross-type features")


def _percentile(vals, v):
    if not vals: return None
    lo = sum(1 for x in vals if x < v); eq = sum(1 for x in vals if x == v)
    return round(100.0 * (lo + 0.5 * eq) / len(vals), 1)


def _fmt(v):
    if v is None: return "-"
    if isinstance(v, float) and abs(v - round(v)) > 1e-9: return f"{v:.2f}"
    return str(int(round(v)))


def judge_feature(name, v, vals, typ_label):
    """(percentile, finding or None) of value v against Westwood's values for the feature."""
    vals = [x for x in vals if x is not None]
    if v is None or not vals: return None, None
    pc = _percentile(vals, v)
    if len(vals) >= 10: lo, hi = _pct(vals, 10), _pct(vals, 90)
    else: lo, hi = min(vals), max(vals)
    spread = (_pct(vals, 75) - _pct(vals, 25)) or (statistics.pstdev(vals) if len(vals) > 1 else 0) or max(0.05, abs(lo) * 0.2)
    if v < lo - 1e-9: side, dist = "low", (lo - v) / spread
    elif v > hi + 1e-9: side, dist = "high", (v - hi) / spread
    else: return pc, None
    label, low, high, where = TEXT.get(name, (name, "{v} is low", "{v} is high", ""))
    text = (low if side == "low" else high)
    if not text: return pc, None                  # a direction that is no fault (fewer overlaps than Westwood)
    text = text.format(v=_fmt(v)) + f" (Westwood's {typ_label}: {_fmt(lo)}-{_fmt(hi)}, median {_fmt(_pct(vals, 50))})"
    return pc, dict(feature=name, value=v, side=side, severity=round(min(dist, 10.0), 2), percentile=pc, range=[lo, hi],
                    text=text, where=where)


def hard_rules(m, r, kind, f, d, warns=()):
    """The user's rules for every room and for the type (review/roomscore.py judge, and this module's own): a list of
    plain-English findings, each a hard-rule failure."""
    import roomscore
    out = []
    checks, _, _ = roomscore.judge(m, r, kind, r.get("tiles"), list(warns))
    for name, ok, detail in checks:
        if ok or name in ("cover", "open", "per tile", "types", "walls", "lined"): continue    # measured, not rules
        out.append(dict(rule=name, text=f"{name}: {detail}", source="review/roomscore.py (the type's profile)"))
    if f["statues_to_wall"]:
        out.append(dict(rule="statue facing", text=f"{int(f['statues_to_wall'])} statue(s) face a wall [GW-7]",
                        source="rules/rooms/README.md"))
    if f["way_in"] < 4.0:
        out.append(dict(rule="way in", text=f"the straight way in from a door is blocked {f['way_in']:.1f} units inside "
                        f"(the rule: nothing within 4 units) [GW-7]", source="rules/rooms/README.md"))
    deep = [p for p in d["overlap_pairs"] if p[2] < -0.6 and not (re.search(r"Chair|Stool|Bench", p[0] + p[1])
                                                                      and re.search(r"Table", p[0] + p[1]))]
    if deep:
        out.append(dict(rule="overlap", text=f"pieces overlap: " + "; ".join(f"{a} and {b} by {-g:.1f}" for a, b, g in deep[:3]),
                        source="metrics overlaps"))
    return out


def compare(f, d, typ, culture=None):
    """Findings for one room's features against Westwood: dict(note, cross_note, pct={feature: percentile},
    findings=[...] (worst first), cross=[...])."""
    f = dict(f)
    westwood()
    f["odd_facing"] = odd_facing(d["wall_pieces"])
    rooms, note = pool(typ, culture)
    label = note.split(":")[0] if note.startswith("FALLBACK") else note.replace("Westwood's ", "")
    label = "pool" if note.startswith("FALLBACK") else label
    pct, finds = {}, []
    names = CORE + [k for k in f if k.startswith("fam_")]
    # a thin type's pool holds kin types without its defining pieces (halls have no throne): its own families are
    # judged by the brief's rules (must, caps) instead
    own_fams = set()
    if note.startswith("FALLBACK"):
        p = TYPES[typ]
        own_fams = set(p.get("must", {})) | set(p.get("needs", ())) | {(p.get("focal") or {}).get("fam")}
    for k in names:
        vals = [r["features"].get(k) for r in rooms]
        if k.startswith("fam_") and not any(vals) and not f.get(k): continue
        if k.startswith("fam_") and k[4:] in own_fams: continue
        pc, fd = judge_feature(k, f.get(k), vals, label)
        pct[k] = pc
        if fd: finds.append(fd)
    # kinds Westwood never repeats in a room of the type, repeated here
    own = [r for r in rooms if r["type"] == typ] or rooms
    seen = collections.Counter(); rep = collections.Counter()
    for r in own:
        for k, n in r["details"]["kinds"].items():
            seen[k] += 1
            if n > 1: rep[k] += 1
    for k, n in d["kinds"].items():
        if n > 1 and seen[k] >= 3 and rep[k] == 0 and not RM.LINED.match(k):
            finds.append(dict(feature="singleton", value=n, side="high", severity=1.0 + 0.3 * n, percentile=None,
                              range=[1, 1], text=f"{k} stands {n} times; Westwood's rooms of the type hold it once "
                              f"({seen[k]} rooms)", where="kit/identity.py ROOMS repeat; kit/furnish.py SHOWPIECES"))
    finds.sort(key=lambda x: -x["severity"])
    allr = westwood()
    cross = []
    for k in CROSS:
        pc, fd = judge_feature(k, f.get(k), [r["features"].get(k) for r in allr], "rooms of every type")
        if fd: cross.append(fd)
    cross.sort(key=lambda x: -x["severity"])
    return dict(note=note, pct=pct, findings=finds, cross=cross, odd_facing=f["odd_facing"])


# ---------------------------------------------------------------------------------------------------- classifier
def classify(gen_feats, typ, culture=None, seed=0):
    """Cross-validated AUC of Westwood against generated over the type's features. gen_feats: [features dict].
    Returns dict(auc, auc_sd, n_westwood, n_generated, note, fallback, top=[(feature, own AUC, direction)])."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    rooms, note = pool(typ, culture)
    fallback = note.startswith("FALLBACK")
    names = [k for k in CORE if k not in NOT_CLASSIFIED] + [f"fam_{x}" for x in FAMS]
    wwf = [r["features"] for r in rooms]
    gen = []
    for g in gen_feats:
        g = dict(g)
        gen.append(g)
    allf = wwf + gen
    names = [k for k in names if len({round(float(x.get(k) or 0), 4) for x in allf}) > 1]
    med = {k: statistics.median([float(x[k]) for x in allf if x.get(k) is not None] or [0.0]) for k in names}
    X = np.array([[float(x[k]) if x.get(k) is not None else med[k] for k in names] for x in allf])
    y = np.array([0] * len(wwf) + [1] * len(gen))
    out = dict(n_westwood=len(wwf), n_generated=len(gen), note=note, fallback=fallback, features=len(names))
    k = min(5, len(wwf), len(gen))
    if k < 2 or not names:
        out.update(auc=None, auc_sd=None, top=[]); return out
    aucs = []
    for rep in range(10):
        skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed + rep)
        p = np.zeros(len(y))
        for tr, te in skf.split(X, y):
            clf = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000, class_weight="balanced"))
            clf.fit(X[tr], y[tr])
            p[te] = clf.predict_proba(X[te])[:, 1]
        aucs.append(roc_auc_score(y, p))
    out["auc"] = round(float(np.mean(aucs)), 3)
    out["auc_sd"] = round(float(np.std(aucs)), 3)
    top = []
    for j, kname in enumerate(names):
        a = roc_auc_score(y, X[:, j])
        top.append((kname, round(float(max(a, 1 - a)), 3), "higher" if a >= 0.5 else "lower",
                    round(float(np.median(X[y == 1, j])), 3), round(float(np.median(X[y == 0, j])), 3)))
    top.sort(key=lambda t: -t[1])
    out["top"] = top[:8]
    return out


def cross_classify(gen_feats, seed=0):
    """The same on the cross-type features against every Westwood room (all types): the fallback for thin types."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    westwood()
    wwf = [r["features"] for r in _WW]
    X = np.array([[float(x.get(k) or 0) for k in CROSS] for x in wwf + list(gen_feats)])
    y = np.array([0] * len(wwf) + [1] * len(gen_feats))
    k = min(5, len(gen_feats))
    if k < 2: return dict(auc=None)
    aucs = []
    for rep in range(10):
        p = np.zeros(len(y))
        for tr, te in StratifiedKFold(n_splits=k, shuffle=True, random_state=seed + rep).split(X, y):
            clf = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000, class_weight="balanced"))
            clf.fit(X[tr], y[tr]); p[te] = clf.predict_proba(X[te])[:, 1]
        aucs.append(roc_auc_score(y, p))
    return dict(auc=round(float(np.mean(aucs)), 3), n_westwood=len(wwf))


# ---------------------------------------------------------------------------------------------------- an iteration
# ---------------------------------------------------------------------------------------------------- templates
# "One template per type repeated across variants" (the independent blind judges, review/NIGHTLOG.md 2026-10-06): a
# batch whose ten rooms are more alike than Westwood's rooms of the type are. Two rooms' layout similarity (0-1) is the
# mean of a structural one (the same families on the same walls: weighted Jaccard of (family, wall) counts, each count
# held to 3, the mirror image counted) and a positional one (pieces of one family within MATCH of each other over the
# rooms' boxes, greedy, kit/originality.py's measure with a looser match, the four flips counted). A batch's template
# similarity is the mean over its pairs; Westwood's spread for the type is the same mean over random draws of as many of
# its rooms (its own when it has 3 or more, with the kin rooms its archetypes name when it has fewer than MIN_WW; else
# the pool's). The lab flags a batch above Westwood's p90.
T_MATCH = 0.2
MIRROR_WALL = {"NE": "NW", "NW": "NE", "SE": "SW", "SW": "SE"}


def _tokens(lay, mirror=False):
    c = collections.Counter((f, MIRROR_WALL.get(p, p) if mirror else p) for f, p, _, _ in lay)
    return {k: min(3, n) for k, n in c.items()}


def _struct(a, b):
    ta = _tokens(a)
    best = 0.0
    for mir in (False, True):
        tb = _tokens(b, mir)
        keys = set(ta) | set(tb)
        den = sum(max(ta.get(k, 0), tb.get(k, 0)) for k in keys)
        if den: best = max(best, sum(min(ta.get(k, 0), tb.get(k, 0)) for k in keys) / den)
    return best


def _pos(a, b):
    if not a or not b: return 0.0
    best = 0.0
    for fu, fv in ((0, 0), (1, 0), (0, 1), (1, 1)):
        bb = [(f, 1 - u if fu else u, 1 - v if fv else v) for f, _, u, v in b]
        pairs = sorted((math.hypot(p[2] - q[1], p[3] - q[2]), i, j) for i, p in enumerate(a) for j, q in enumerate(bb)
                       if p[0] == q[0])
        ua, ub, mm = set(), set(), 0
        for dd, i, j in pairs:
            if dd > T_MATCH: break
            if i in ua or j in ub: continue
            ua.add(i); ub.add(j); mm += 1
        best = max(best, 2 * mm / (len(a) + len(b)))
    return best


def layout_similarity(a, b):
    """0-1: how alike two rooms' layouts (details["layout"]) are."""
    if not a or not b: return 0.0
    return 0.5 * (_struct(a, b) + _pos(a, b))


def _mean_pairs(lays):
    sims = [layout_similarity(a, b) for i, a in enumerate(lays) for b in lays[i + 1:]]
    return (sum(sims) / len(sims)) if sims else None, sims


def template_reference(typ):
    """(Westwood layouts the type's template similarity is compared with, a note)."""
    ww = [r for r in westwood() if r["details"].get("layout")]
    own = [r for r in ww if r["type"] == typ]
    if len(own) >= MIN_WW: return own, f"Westwood's {len(own)} {typ.replace('_', ' ')} rooms"
    kin = set()
    try:
        from kit.archetypes import ARCHETYPES
        kin = {i for a in ARCHETYPES.get(typ, []) for i in a.get("kin", ())}
    except Exception:
        pass
    key = lambda r: f"{r['map']}@{r['centre'][0]},{r['centre'][1]}"
    with_kin = own + [r for r in ww if key(r) in kin and r["type"] != typ]
    if len(with_kin) >= 3:
        return with_kin, (f"Westwood's {len(own)} {typ.replace('_', ' ')} rooms" +
                          (f" and {len(with_kin) - len(own)} kin rooms its archetypes name" if len(with_kin) > len(own) else ""))
    rooms, note = pool(typ)
    rooms = [r for r in rooms if r["details"].get("layout")]
    return rooms, f"its pool's {len(rooms)} rooms (thin type)"


def template(gen_layouts, typ, n=None, draws=300):
    """The batch's template similarity against Westwood's spread for the type: dict(batch, westwood p10/p50/p90 of the
    same mean over random draws of n of its rooms, flag, twins: the batch's pairs more alike than Westwood's p95 pair)."""
    lays = [l for l in gen_layouts if l]
    bm, bsims = _mean_pairs(lays)
    ref, note = template_reference(typ)
    rl = [r["details"]["layout"] for r in ref]
    k = min(len(rl), n or len(lays))
    if len(rl) <= k: k = max(3, len(rl) - 2)        # a thin type: its spread over leave-two-out draws
    rng = random.Random(E.seed_of("template", typ))
    full = {}
    def sim(i, j):
        if (i, j) not in full: full[(i, j)] = layout_similarity(rl[i], rl[j])
        return full[(i, j)]
    means = []
    if k >= 2:
        for _ in range(draws):
            idx = sorted(rng.sample(range(len(rl)), k))
            ss = [sim(i, j) for a_, i in enumerate(idx) for j in idx[a_ + 1:]]
            means.append(sum(ss) / len(ss))
    means.sort()
    pq = lambda p: round(means[min(len(means) - 1, int(p / 100 * len(means)))], 3) if means else None
    allpairs = sorted(sim(i, j) for i in range(len(rl)) for j in range(i + 1, len(rl)))
    p95 = allpairs[min(len(allpairs) - 1, int(0.95 * len(allpairs)))] if allpairs else 1.0
    twins = []
    idxs = [i for i, l in enumerate(gen_layouts) if l]
    pairs = [(idxs[a], idxs[b]) for a in range(len(idxs)) for b in range(a + 1, len(idxs))]
    for (i, j), s_ in zip(pairs, bsims):
        if s_ > p95: twins.append([i, j, round(s_, 3)])
    out = dict(batch=round(bm, 3) if bm is not None else None, ww_p10=pq(10), ww_p50=pq(50), ww_p90=pq(90),
               ww_pair_p95=round(p95, 3), twins=sorted(twins, key=lambda t: -t[2])[:8], note=note, ww_rooms=len(rl))
    out["flag"] = bool(bm is not None and out["ww_p90"] is not None and bm > out["ww_p90"])
    return out


def judge_batch(typ, it, log=print):
    """Measures and judges an iteration's generated rooms (review/out/roomlab/<type>/<iter>/variants.json), writes
    metrics.json there and returns it."""
    d = E.iter_dir(typ, it)
    with open(os.path.join(d, "variants.json"), encoding="utf-8") as fh:
        batch = json.load(fh)
    import validate as V
    rooms_out = []
    by_map = collections.defaultdict(list)
    for v in batch["variants"]: by_map[v["map"]].append(v)
    for mname, vs in by_map.items():
        path = os.path.join(d, "map", mname + ".map")
        m = E.MD.load(path)
        try:
            _, findings, _ = V.validate(path)
        except Exception as ex:                  # the checker is a bonus here, never a blocker
            log(f"  checker failed on {mname}: {ex}"); findings = []
        found = {r["declared"]["number"]: r for r in C.find_rooms(m, max_tiles=1500) if r.get("declared")}
        for v in vs:
            r = found.get(v["number"])
            if r is None:
                log(f"  variant {v['index']}: room not found in {mname}"); continue
            cells = r["cells"]
            near = {(x + a, y + b) for x, y in cells for a in (-1, 0, 1) for b in (-1, 0, 1)}
            warns = [w for w in findings if w["severity"] != "info" and w.get("x") is not None and
                     (int(w["x"] // 23), int(w["y"] // 23)) in near]
            f, det = features(m, r, typ, v["kind"])
            cmp_ = compare(f, det, typ, v["culture"])
            f["odd_facing"] = cmp_["odd_facing"]
            hard = hard_rules(m, r, v["kind"], f, det, warns)
            rooms_out.append(dict(index=v["index"], kind=v["kind"], culture=v["culture"], role=v["role"],
                                  style=v["style"], size=v["size"], shape=v["shape"], tiles=f["tiles"], doors=f["doors"],
                                  features=f, details=det, note=cmp_["note"], pct=cmp_["pct"],
                                  findings=cmp_["findings"], cross=cmp_["cross"], hard=hard,
                                  warnings=[w["msg"][:120] for w in warns[:6]]))
    rooms_out.sort(key=lambda x: x["index"])
    gen = [x["features"] for x in rooms_out]
    cultures = collections.Counter(x["culture"] for x in rooms_out)
    main_culture = cultures.most_common(1)[0][0] if cultures else None
    cls = classify(gen, typ, None, seed=E.seed_of(typ) % 1000)
    cross = cross_classify(gen, seed=E.seed_of(typ) % 1000)
    # the batch's worst findings: those most rooms share, by severity
    tally = collections.defaultdict(list)
    for x in rooms_out:
        for fd in x["findings"]: tally[(fd["feature"], fd["side"])].append(fd)
    worst = sorted(tally.items(), key=lambda kv: (-len(kv[1]), -statistics.mean(f["severity"] for f in kv[1])))
    worst = [dict(feature=k[0], side=k[1], rooms=len(v), example=max(v, key=lambda f: f["severity"])["text"],
                  where=v[0]["where"]) for k, v in worst[:8]]
    hard_tally = collections.Counter(h["rule"] for x in rooms_out for h in x["hard"])
    own = sum(1 for r in westwood() if r["type"] == typ)
    tmpl = template([x["details"].get("layout") for x in rooms_out], typ)
    res = dict(type=typ, iter=it, classifier=cls, cross_classifier=cross, westwood_rooms=own, template=tmpl,
               westwood_cultures=dict(collections.Counter(r["culture"] for r in westwood() if r["type"] == typ)),
               batch_cultures=dict(cultures), worst=worst, hard_rules=dict(hard_tally),
               rooms_with_hard=sum(1 for x in rooms_out if x["hard"]), rooms=rooms_out)
    with open(os.path.join(d, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    return res


if __name__ == "__main__":
    if "--westwood" in sys.argv:
        import labref
        labref.build_features()
    elif len(sys.argv) >= 3:
        r = judge_batch(sys.argv[1], sys.argv[2])
        c = r["classifier"]
        print(f"{r['type']} {r['iter']}: AUC {c['auc']} ({c['note']}); hard-rule rooms {r['rooms_with_hard']}")
        for w in r["worst"]: print(f"  {w['rooms']} rooms: {w['example']}")
    else:
        print(__doc__)
