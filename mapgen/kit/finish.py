"""Room finishing passes from the user's QA round 1 (2026-10-13, review/reviews/QA-round1.md; ledger review/qa1/rooms.md).

The user's two themes over every room type: "the spaces are too empty and lack object diversity", and "a lack of balance
and symmetry: things are placed randomly and not lined up with each other". Both engines (kit/furnish.py recipes,
kit/motifs.py) compose a room from Westwood's measures; the pass here runs last in both (after the grammar audit), per
room kind, and puts right what the user named, in the room as composed:

- bedroom (Q1R-3..7): a nightstand either side of the bed's head at RM-BEDROOM-10's spacing (0.45 units off the bed,
  snug to the wall), the chest centred at the bed's foot or centred on a wall, never in a corner; the S corner filled
  (a small table with two chairs, else a rug); a table floating mid-floor moved there; rugs centred in their half of
  the room; the bare stretches of the NE and NW walls dressed (bookcases, banners, trophies);
- barracks (Q1R-8, Q1R-9): one wall of beds, one wall of racks of arms and armour, gear hung on the back walls;
- ogre den (Q1R-10): mana obelisks in pairs, symmetric (the two corners of one wall, or across the room); no bare
  front corner;
- cell and ogre pen (Q1R-11, Q1R-12): a human cell's stocks and its bench or stool, two cots in a cell of 40 tiles or
  more; an ogre pen's straw heaped in a corner or at one end, no bare corner;
- cellar (Q1R-13): kegs of three kinds, metal barrels, barrels of tools and crates in tidy groups, the great casks
  with room round them;
- armoury / gear store (Q1R-1, Q1R-2): the quartermaster's counter facing the door, racks along the walls of a larger
  room, arms hung;
- great hall (Q1R-15..18): the table groups centred on their carpet, a stray table or bench taken up, an unbroken brick
  band round the room, pieces of more kinds along the walls;
- conservatory (Q1R-14): composed here whole (compose()): a garden indoors on grass and dirt.

Each pass works through the furnisher's own placement (Furnisher.try_put: footprints, door ways, the clearances of the
object knowledge base), so nothing it adds stands in a doorway or on another piece. Its own generator (crc32 of the map
and room), so the composition before it draws as it did. NOX_FINISH=0 turns it off (the before of a comparison).
"""
import math, os, random, re, zlib

ENABLED = os.environ.get("NOX_FINISH", "1") == "1"

BACK = ("/|BR", "\\|BL")                    # the NW and NE walls (the camera sees their fronts)
WALL_NAME = {"/|BR": "NW", "\\|BL": "NE", "/|TL": "SE", "\\|TR": "SW"}
BED = r"^(Bed\d|WoodBed\d|Cot\d|OgreBed\d)$"
CHEST = r"^(Chest\d|Chest[NS][EW]|DunMirChest\d)$"
TABLE = r"^(Table\d|RoundTable\d|SquareTable\d|OvalTable\d|SmallTable\d|RoundTableWithFood)$"
SEAT = r"Chair|Stool|Bench"
RUG = r"^(RedRug\d|BearskinRug\d|OgreBearskin\d)$"
NIGHTSTAND_GAP = 0.45      # units between the bed's side and its nightstand (RM-BEDROOM-10, the gold standard: 0.28-0.40;
                           # RM-BEDROOM-02's 0.22 was "too close to the bed")
NIGHTSTAND_PERP = 0.76     # its centre's distance from the wall line (RM-BEDROOM-10: 0.74-0.78; RM-BEDROOM-01's 0.96
                           # was "too far from the wall")
CHEST_FOOT_GAP = 0.8       # units between the bed's foot and the chest centred there (RM-BEDROOM-10: 0.87)


# ---- geometry ------------------------------------------------------------------------------------------------------
def _rng(f, what):
    return random.Random(zlib.crc32(f"finish:{what}:{f.spec.d.get('name')}:{f.room.id}".encode()))


def items(f, rx):
    """[(object, type, footprint record)] of the pieces placed in the room whose type matches rx."""
    out = []
    for o in list(f.objects):
        rec = f._placed_of.get(id(o))
        if rec is not None and re.search(rx, o["type"]): out.append((o, o["type"], rec))
    return out


def uv_on(r, d, a):
    """The point `d` units into the room from wall run r, at `a` along it."""
    c = r["coord"] + r["sign"] * d
    return (c, a) if r["line"] == "/" else (a, c)


def along_of(r, u, v):
    return v if r["line"] == "/" else u


def perp_of(r, u, v):
    return ((u if r["line"] == "/" else v) - r["coord"]) * r["sign"]


def halves_on(r, rec):
    """(half-length along wall run r, half-depth into the room) of a footprint record."""
    return (rec[3], rec[2]) if r["line"] == "/" else (rec[2], rec[3])


def run_of(f, rec, reach=1.2):
    """(run, along, distance of the piece's back from the wall line) of the wall a piece stands against, or None."""
    u, v, hu, hv = rec[:4]
    best = None
    for r in f.g.runs:
        a = along_of(r, u, v)
        if not r["lo"] - 0.5 <= a <= r["hi"] + 0.5: continue
        ha, hp = halves_on(r, rec)
        off = perp_of(r, u, v) - hp
        if -0.3 < off <= reach and (best is None or off < best[2]): best = (r, a, off)
    return best


def box(f):
    """(u0, u1, v0, v1): the wall lines round the room's cells (NW, SE, SW, NE)."""
    us = [x + y + 1 for x, y in f.g.cells]; vs = [x - y for x, y in f.g.cells]
    return min(us) - 1, max(us) + 1, min(vs) - 1, max(vs) + 1


def blockers(f, skip=()):
    skip = {id(s) for s in skip}
    return [p for p in f.g.placed if p[4] and p[5] != "wall" and id(p) not in skip]


def clear_at(f, u, v, rad, skip=()):
    """True when no blocking floor piece stands within `rad` units (box distance) of (u, v)."""
    for p in blockers(f, skip):
        if max(abs(u - p[0]) - p[2], abs(v - p[1]) - p[3]) < rad: return False
    return True


def put(f, t, u, v, **kw):
    if not t or not f.ok_type(t): return None
    blocking = kw.pop("blocking", F._family_of(t) not in F.NON_BLOCKING)
    return f.try_put(t, u, v, blocking=blocking, snug=True, **kw)


def restore(f, t, u, v):
    """A piece put back where it stood (no rule asked again: it stood there already)."""
    return f.put(t, u, v, F._family_of(t) not in F.NON_BLOCKING)


def wall_at(f, r, a, half=1.0):
    """True when wall run r has wall pieces at `a` and `half` units either side along it (a hanging needs a wall behind
    it, not an opening into the next room)."""
    for da in (-half, 0.0, half):
        u, v = uv_on(r, 0.0, a + da)
        x, y = (u + v) / 2, (u - v) / 2
        if not any((int(math.floor(x)) + i, int(math.floor(y)) + j) in f.g.wall_cells
                   for i in (-1, 0, 1) for j in (-1, 0, 1)):
            return False
    return True


def put_corner(f, t, u, v, **kw):
    """put() in a room corner: only the doors' ways in are kept clear there (the space other pieces keep before them
    runs along their wall and may reach a corner, where nothing stands before them)."""
    saved = f.g.zones
    f.g.zones = saved[:len(f.openings)]
    try:
        return put(f, t, u, v, **kw)
    finally:
        f.g.zones = saved


def remove(f, objs):
    for o in objs: f._remove(o)


def variant(f, base, side):
    """The piece of `base` (Chest, Nightstand, Bookcase...) for a wall side, as the furnisher numbers it."""
    t = f.variant_for_side(base, side) if base in f.dirvar else None
    return t or f.along_variant(base + "1", side)


def corner_points(f, inset):
    """{corner name: (u, v)} `inset` units in from each corner of the room's box (N, E, S, W)."""
    u0, u1, v0, v1 = box(f)
    return {"N": (u0 + inset, v1 - inset), "E": (u1 - inset, v1 - inset), "S": (u1 - inset, v0 + inset),
            "W": (u0 + inset, v0 + inset)}


def free_corners(f, inset=1.4, rad=1.6):
    """The corners of the room with no piece within `rad` of the point `inset` in from them (and inside the room)."""
    out = []
    for k, (u, v) in corner_points(f, inset).items():
        if f.g.inside(u, v) and clear_at(f, u, v, rad) and _no_door(f, u, v, 2.6): out.append((k, u, v))
    return out


def _no_door(f, u, v, d):
    return all(math.hypot(u - du, v - dv) >= d for du, dv in f.g.doors)


def wall_pieces(f, r, reach=1.0, layer=None):
    """[(along, half-length, record)] of the pieces standing against wall run r (floor pieces, or with layer="wall"
    the hangings on it)."""
    out = []
    for p in f.g.placed:
        if layer == "wall":
            if p[5] != "wall": continue
        elif not p[4] or p[5] == "wall":
            continue
        w = run_of(f, p, reach=reach if layer != "wall" else 1.6)
        if not w or w[0] is not r: continue
        out.append((w[1], halves_on(r, p)[0], p))
    return out


def hang_backs(f, rng, most=4, types=None, gap=3.2, edge=1.3):
    """Hangings on the bare stretches of the NE and NW walls (the room's theme, else `types`): on each stretch of 2.6
    units or more with nothing against the wall and no hanging, one centred, or two placed symmetrically about the
    stretch's middle on a long one (QA round 1: "more wall objects (banners, trophies...)", "things are placed
    randomly and not lined up"). Returns the hangings placed."""
    if types is None:
        if not hasattr(f, "_decor_types"): f.decor_theme()
        types = dict(f._decor_types)
    if not types: return 0
    order = sorted(types); rng.shuffle(order)
    n = 0
    inv = f.T["inventory"].get("wall_decor", {})
    runs = sorted((r for r in f.g.runs if r["side"] in BACK), key=lambda r: -(r["hi"] - r["lo"]))
    k = 0
    for r in runs:
        if n >= most: break
        hung = [(a, max(ha, F.HANG_HALF)) for a, ha, _ in wall_pieces(f, r, layer="wall")]
        stretches = []
        for a0, a1 in free_stretches(f, r):
            a0, a1 = max(a0, r["lo"] + 1 + edge), min(a1, r["hi"] - 1 - edge)
            for ha_, hh in hung:                 # minus the hangings already there
                if ha_ + hh + 0.6 <= a0 or ha_ - hh - 0.6 >= a1: continue
                if ha_ - a0 > a1 - ha_: a1 = min(a1, ha_ - hh - 0.6)
                else: a0 = max(a0, ha_ + hh + 0.6)
            if a1 - a0 >= 2.0: stretches.append((a0, a1))
        for a0, a1 in stretches:
            if n >= most: break
            L, mid = a1 - a0, (a0 + a1) / 2
            spots = [mid] if L < 2 * gap + 0.4 else [mid - L / 4, mid + L / 4]
            t0 = order[k % len(order)]; k += 1
            t = f.side_variant(t0, r, "wall_decor") or t0
            if not f.ok_type(t): continue
            d = f.perp_for(t, inv.get("perp_px"))
            for a in spots:
                if n >= most: break
                if not wall_at(f, r, a): continue
                u, v = uv_on(r, d, a)
                if f.try_put(t, u, v, blocking=False, wall_ok=True, layer="wall"):
                    n += 1
                    if hasattr(f, "_decor_at"): f._decor_at.append(((r["line"], r["coord"]), a))
    return n


def line_pair(f, rng, base="Bookcase", n=2, min_len=None, sides=BACK):
    """A run of `n` pieces end to end (bookcases) centred on the longest bare stretch of a back wall. Returns the pieces."""
    best = None
    for r in f.g.runs:
        if r["side"] not in sides: continue
        t = f.along_variant(base + "1", r["side"]) or variant(f, base, r["side"])
        if not t or not f.ok_type(t): continue
        hu, hv = f.half(t)
        ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
        need = 2 * ha * n + 0.4
        for a0, a1 in free_stretches(f, r):
            a0, a1 = max(a0, r["lo"] + 1.3), min(a1, r["hi"] - 1.3)
            if a1 - a0 >= max(need, min_len or 0) and (best is None or a1 - a0 > best[0]):
                best = (a1 - a0, r, t, (a0 + a1) / 2, ha, hp)
    if not best: return []
    _, r, t, mid, ha, hp = best
    got = []
    for k in range(n):
        a = mid + (k - (n - 1) / 2) * 2 * ha
        u, v = uv_on(r, hp + F.SNUG_GAP.get("shelves", 0.18), a)
        o = f.try_put(t, u, v, snug=True, touch=True)
        if o: got.append(o)
    if len(got) < min(2, n): remove(f, got); return []
    return got


def table_set(f, u, v, types=None, chairs=2, axis=None):
    """A small table at (u, v) with `chairs` chairs drawn up on opposite sides (along `axis`, "u" or "v", else the one
    that fits). Returns the pieces, or [] (nothing left) when it does not fit."""
    types = types or [t for t in ("SquareTable1", "RoundTable1", "SquareTable2", "RoundTable2") if f.ok_type(t)]
    seats = f.types_of("chair") or {"WoodenChair1": 1}
    base = f.palette_seat("chair", seats) if hasattr(f, "palette_seat") else None
    for t in types:
        o = put(f, t, u, v)
        if not o: continue
        th = f.half(t)
        for ax in ([axis] if axis else ["u", "v"]):
            got = []
            for sgn in (-1, 1)[:chairs]:
                to_table = ("+" if sgn < 0 else "-") + ax
                ct = ((f.chair_facing.get(base or "", {}) or {}).get(to_table) or {}).get("variant")
                if not ct or not f.ok_type(ct):
                    ct = next((c for c in sorted(seats) if not base or c.startswith(base)), "WoodenChair1")
                ch = f.half(ct)
                cu, cv = (u + sgn * (th[0] + ch[0] + 0.2), v) if ax == "u" else (u, v + sgn * (th[1] + ch[1] + 0.2))
                c = put(f, ct, cu, cv)
                if c: got.append(c)
            if len(got) == chairs: return [o] + got
            remove(f, got)
        f._remove(o)
    return []


class _State:
    """The furnisher's limits for a finishing pass: the composition's caps are its own, a finishing piece is placed
    where it fits (its footprint, the door ways, the object knowledge base's clearances and caps still hold)."""

    def __init__(self, f):
        self.f = f

    def __enter__(self):
        f = self.f
        self.saved = (f.composing, f.in_required, f.ceiling, f.placing_light, f.rng)
        f.composing, f.in_required, f.ceiling, f.placing_light = False, True, None, False
        return self

    def __exit__(self, *a):
        f = self.f
        f.composing, f.in_required, f.ceiling, f.placing_light, f.rng = self.saved
        return False


from kit import furnish as F  # noqa: E402  (after the helpers: furnish imports this module lazily)


# ---- bedroom (Q1R-3..7) ------------------------------------------------------------------------------------------
def _bedroom(f, rng):
    beds = items(f, BED)
    if not beds: return
    bed = max(beds, key=lambda b: b[2][2] * b[2][3])
    before = [(t, rec[0], rec[1]) for _, t, rec in items(f, r"^Nightstand\d")]
    head = head_wall(f, bed)
    got = _nightstands(f, bed, head, rng, pair_only=True) if head else None
    if not got or _in_corner(f, got[2], head_wall(f, got) or head):
        moved = _replace_bed(f, got or bed, rng)
        if moved: got = moved
    if not got:                                   # as it was: its own nightstands back
        for t, u, v in before: restore(f, t, u, v)
        got = bed if id(bed[0]) in f._placed_of else None
    if got:
        bed = got
        head = head_wall(f, bed)
        if head: _chest(f, bed, head, rng)
    _floating_tables(f, carpets_too=True)
    _south_corner(f, rng, sitting=True)
    _centre_rugs(f, bed)
    _dress_backs(f, rng, shelves=True, most=5 if len(f.room.tiles) >= 40 else 3)
    if len(f.room.tiles) >= 45: _second_rug(f, rng, bed)


def head_wall(f, bed):
    """(run, along, off) of the wall a bed's headboard is against (the wall side its variant is drawn for), when it
    stands snug there (within 0.6 units), else None."""
    o, t, rec = bed
    for r in f.g.runs:
        if f.along_variant(t, r["side"]) != t: continue
        a = along_of(r, rec[0], rec[1])
        if not r["lo"] - 0.5 <= a <= r["hi"] + 0.5: continue
        ha, hp = halves_on(r, rec)
        off = perp_of(r, rec[0], rec[1]) - hp
        if -0.3 < off <= 0.6: return (r, a, off)
    return None


def free_stretches(f, r, skip=()):
    """[(a0, a1)] of wall run r with no piece standing against it and no doorway (DOOR_CLEAR units each side)."""
    lo, hi = r["lo"] + 1.0, r["hi"] - 1.0
    cuts = []
    for du, dv in f.g.doors:
        if abs(perp_of(r, du, dv)) < 1.6:
            da = along_of(r, du, dv); cuts.append((da - F.DOOR_CLEAR, da + F.DOOR_CLEAR))
    skip = {id(s) for s in skip}
    for p in blockers(f):
        if id(p) in skip: continue
        ha, hp = halves_on(r, p)
        if perp_of(r, p[0], p[1]) - hp > 1.2: continue          # (any piece by this wall, a corner's piece too)
        pa = along_of(r, p[0], p[1])
        cuts.append((pa - ha - 0.15, pa + ha + 0.15))
    free = [(lo, hi)]
    for c0, c1 in cuts:
        nxt = []
        for f0, f1 in free:
            if c1 <= f0 or c0 >= f1: nxt.append((f0, f1)); continue
            if c0 > f0: nxt.append((f0, c0))
            if c1 < f1: nxt.append((c1, f1))
        free = nxt
    return [(a0, a1) for a0, a1 in free if a1 - a0 > 0.5]


def _replace_bed(f, bed, rng):
    """The bed taken up and set again headboard to a back wall, centred on that wall's widest free stretch with room
    for a nightstand either side (QA round 1, RM-BEDROOM-06: "the bed looks like it's attached to the northwest wall");
    its nightstands and the chest beside it go with it. Returns the bed, or None when no back wall has room (the bed
    then stands where it stood)."""
    o, t, rec = bed
    near = [x for x in items(f, r"^Nightstand\d") + items(f, CHEST)
            if max(abs(x[2][0] - rec[0]) - x[2][2] - rec[2], abs(x[2][1] - rec[1]) - x[2][3] - rec[3]) < 1.2]
    stem = re.match(r"^(\D+)", t).group(1)
    ns = f.half(variant(f, "Nightstand", "/|BR") or "Nightstand1")[0]
    cands = []
    for r in f.g.runs:
        if r["side"] not in BACK: continue
        tt = f.along_variant(t, r["side"]) or f.along_variant(stem + "1", r["side"])
        if not tt: continue
        hu, hv = f.half(tt)
        ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
        need = 2 * (ha + NIGHTSTAND_GAP + 2 * ns) + 0.3
        for a0, a1 in free_stretches(f, r, skip=[rec] + [x[2] for x in near]):
            if a1 - a0 < need: continue
            cands.append((a1 - a0 + rng.uniform(0, 0.5), r, tt, (a0 + a1) / 2, hp))
    for _, r, tt, a, hp in sorted(cands, key=lambda c: -c[0]):
        remove(f, [o] + [x[0] for x in near])
        u, v = uv_on(r, hp + F.SNUG_GAP.get("bed", 0.28), a)
        o2 = put(f, tt, u, v)
        if o2:
            nb = (o2, tt, f._placed_of[id(o2)])
            got = _nightstands(f, nb, (r, a, 0.28), rng, pair_only=True)
            if got: return got
            f._remove(o2)
        if id(o) not in f._placed_of: o = restore(f, t, rec[0], rec[1])        # back as it was
        near = [(x[0] if id(x[0]) in f._placed_of else restore(f, x[1], x[2][0], x[2][1]), x[1], x[2]) for x in near]
        near = [(x[0], x[1], f._placed_of[id(x[0])]) for x in near]
    return None


def _nightstands(f, bed, w, rng, pair_only=False):
    """A nightstand either side of the bed's head, NIGHTSTAND_GAP off it, NIGHTSTAND_PERP from the wall line, one kind
    (RM-BEDROOM-10); the bed slides along its wall when one side has no room. Returns the bed (moved or not), or None
    with pair_only when no pair fits (the bed is then where it was, its nightstands taken up)."""
    r, a, _ = w
    old = items(f, r"^Nightstand\d")
    t = variant(f, "Nightstand", r["side"]) or (old[0][1] if old else None)
    if not t: return bed
    nh = f.half(t)[0]
    remove(f, [o for o, _, _ in old])
    o_bed, tb, rec = bed
    bha, bhp = halves_on(r, rec)
    bperp = perp_of(r, rec[0], rec[1])
    for shift in (0.0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5, 2.0, -2.0):
        if shift:
            f._remove(o_bed)
            u, v = uv_on(r, bperp, a + shift)
            o2 = put(f, tb, u, v)
            if not o2:
                u, v = uv_on(r, bperp, a)
                o_bed = put(f, tb, u, v) or o_bed
                continue
            o_bed = o2
        aa = a + shift
        got = []
        for s in (-1, 1):
            u, v = uv_on(r, NIGHTSTAND_PERP, aa + s * (bha + NIGHTSTAND_GAP + nh))
            o = put(f, t, u, v)
            if not o: break
            got.append(o)
        if len(got) == 2:
            return (o_bed, tb, f._placed_of[id(o_bed)])
        remove(f, got)
        if shift:                                   # back where it stood
            f._remove(o_bed)
            u, v = uv_on(r, bperp, a)
            o_bed = put(f, tb, u, v) or o_bed
    if pair_only:
        return None
    # no room for the pair anywhere along the wall: one nightstand, on the side with room
    for s in rng.sample((-1, 1), 2):
        u, v = uv_on(r, NIGHTSTAND_PERP, a + s * (bha + NIGHTSTAND_GAP + nh))
        if put(f, t, u, v): break
    return (o_bed, tb, f._placed_of[id(o_bed)])


def _second_rug(f, rng, bed):
    """A big bedroom's other half takes a rug of its own, centred there (RM-BEDROOM-07: "perhaps another small rug
    added to the northwest volume of the room"), when it is bare."""
    if len(items(f, RUG)) >= 2: return
    u0, u1, v0, v1 = box(f)
    long_u = (u1 - u0) >= (v1 - v0)
    for half in ((0, 0.5), (0.5, 1)):
        if long_u:
            cu, cv = u0 + (u1 - u0) * (half[0] + half[1]) / 2, (v0 + v1) / 2
        else:
            cu, cv = (u0 + u1) / 2, v0 + (v1 - v0) * (half[0] + half[1]) / 2
        if any(math.hypot(rr[0] - cu, rr[1] - cv) < 4 for _, _, rr in items(f, RUG)): continue
        if on_carpet(f, cu, cv, pad=1.8) or not clear_at(f, cu, cv, 1.4): continue
        t = _rug_type(f, rng)
        if t and put(f, t, cu, cv, blocking=False): return


def on_carpet(f, u, v, pad=0.0):
    """True when the floor at (u, v) (or within `pad` units of it) is a carpet (Rug floor tiles). A room's square
    (i, j) is the tile (i + j, i - j), its centre at uv (2i + 2, 2j)."""
    for du in ((0.0,) if not pad else (-pad, 0.0, pad)):
        for dv in ((0.0,) if not pad else (-pad, 0.0, pad)):
            i, j = round((u + du - 2) / 2), round((v + dv) / 2)
            m = f.spec.floor.get((i + j, i - j)) or ""
            if m.startswith("Rug"): return True
    return False


def _in_corner(f, rec, w):
    r, a, _ = w
    ha, _ = halves_on(r, rec)
    return min(a - ha - (r["lo"] + 1), (r["hi"] - 1) - (a + ha)) < 1.6


def _at_foot(f, chest_rec, bed_rec, r):
    a_b = along_of(r, bed_rec[0], bed_rec[1]); a_c = along_of(r, chest_rec[0], chest_rec[1])
    _, bhp = halves_on(r, bed_rec)
    foot = perp_of(r, bed_rec[0], bed_rec[1]) + bhp
    return abs(a_b - a_c) < 0.5 and 0 < perp_of(r, chest_rec[0], chest_rec[1]) - foot < 2.0


def _chest(f, bed, w, rng):
    """The chest centred at the bed's foot (RM-BEDROOM-10), else centred on a bare stretch of a back wall; never in a
    corner (RM-BEDROOM-03: "the chest in the north corner looks out of place. Center the chest on the northwest wall")."""
    chests = items(f, CHEST)
    r, a, _ = w
    bed_rec = bed[2]
    def good(c):
        if _at_foot(f, c[2], bed_rec, r): return True
        cw = run_of(f, c[2])
        return bool(cw) and not _in_corner(f, c[2], cw) and _centred_on_stretch(f, c[2], cw)
    if chests and all(good(c) for c in chests): return
    t0 = chests[0][1] if chests else "Chest1"
    remove(f, [c[0] for c in chests])
    base = re.sub(r"\d$", "", t0) if re.search(r"\d$", t0) else "Chest"
    t = variant(f, base, r["side"]) or t0
    hu, hv = f.half(t)
    ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
    _, bhp = halves_on(r, bed_rec)
    foot = perp_of(r, bed_rec[0], bed_rec[1]) + bhp
    for gap in (CHEST_FOOT_GAP, 1.0, 1.25):
        u, v = uv_on(r, foot + gap + hp, along_of(r, bed_rec[0], bed_rec[1]))
        if not f._front_crowded(r, u, v, ha, hp) and put(f, t, u, v): return
    if centre_on_back(f, rng, base, min_len=2.4): return
    if centre_on_back(f, rng, base, min_len=2.4, sides=tuple(WALL_NAME)): return
    for c in chests: restore(f, c[1], c[2][0], c[2][1])      # nowhere better: as it was


def centre_on_back(f, rng, base, min_len=2.0, sides=BACK):
    """One piece of `base` (Chest, Desk...) centred on the longest bare stretch of a back wall, its front kept clear."""
    best = []
    for r in f.g.runs:
        if r["side"] not in sides: continue
        t = variant(f, base, r["side"])
        if not t or not f.ok_type(t): continue
        hu, hv = f.half(t)
        ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
        for a0, a1 in free_stretches(f, r):
            a0, a1 = max(a0, r["lo"] + 1.6), min(a1, r["hi"] - 1.6)
            if a1 - a0 >= max(min_len, 2 * ha + 0.6): best.append((a1 - a0, r, t, (a0 + a1) / 2, ha, hp))
    for _, r, t, a, ha, hp in sorted(best, key=lambda b: -b[0]):
        u, v = uv_on(r, hp + F.SNUG_GAP.get("storage", 0.22), a)
        if F.NEEDS_FRONT.search(t) and f._front_crowded(r, u, v, ha, hp): continue
        o = put(f, t, u, v)
        if o: return o
    return None


def _centred_on_stretch(f, rec, w):
    """True when a piece stands near the middle of the free stretch of its wall (between the corners, doors and the
    pieces beside it)."""
    r, a, _ = w
    ha, _ = halves_on(r, rec)
    lo, hi = r["lo"] + 1, r["hi"] - 1
    for du, dv in f.g.doors:
        if abs(perp_of(r, du, dv)) < 1.6:
            da = along_of(r, du, dv)
            if da < a: lo = max(lo, da + 1.2)
            else: hi = min(hi, da - 1.2)
    for p in blockers(f, (rec,)):
        if p is rec: continue
        pw = run_of(f, p)
        if not pw or pw[0] is not r: continue
        pa = pw[1]; pha, _ = halves_on(r, p)
        if pa < a: lo = max(lo, pa + pha)
        else: hi = min(hi, pa - pha)
    return abs(a - (lo + hi) / 2) < max(0.6, 0.15 * (hi - lo))


def _floating_tables(f, carpets_too=False):
    """A table more than 2.2 units from every wall and not on a rug or carpet goes, with its seats (the S corner's
    sitting group takes its place: RM-BEDROOM-08 "the table in the middle of the room looks out of place")."""
    for o, t, rec in items(f, TABLE):
        if f.g.wall_dist(rec[0], rec[1]) - max(rec[2], rec[3]) <= 2.2: continue
        if not carpets_too:
            if any(F.Furnisher._overlap(rec[0], rec[1], rec[2], rec[3], rr) for tt, rr in f._typed if re.search(RUG, tt)): continue
            if on_carpet(f, rec[0], rec[1]): continue
        seats = [so for so, st, sr in items(f, SEAT) if max(abs(sr[0] - rec[0]) - sr[2] - rec[2],
                                                            abs(sr[1] - rec[1]) - sr[3] - rec[3]) < 0.8]
        remove(f, seats + [o])


def _south_corner(f, rng, sitting=True):
    """The S corner, where a room most often stood bare (QA round 1, bedrooms: "dead spaces in the south corner are too
    common"; nox5, nox21): a small table with two chairs when the room has no table or desk yet (RM-BEDROOM-08: "a
    small table with two chairs would be perfect here"), else a rug centred in the corner's part of the room, far
    enough from the front walls to be seen. Returns what it placed."""
    u0, u1, v0, v1 = box(f)
    has_set = bool(items(f, TABLE) or items(f, r"^Desk\d"))
    for inset in (3.2, 2.9, 3.6):
        u, v = u1 - inset, v0 + inset
        if not f.g.inside(u, v) or not _no_door(f, u, v, 3.0): continue
        if not clear_at(f, u, v, 1.9): return None
        big = len(f.room.tiles) >= F.BEDROOM_DESK_AND_TABLE
        if sitting and (not has_set or (big and not items(f, TABLE))) and len(f.room.tiles) >= 20:
            got = table_set(f, u, v, axis="u" if (u1 - u0) < (v1 - v0) else "v")
            if got: return got
        rug = _rug_type(f, rng)
        if rug:
            k = max(inset, max(f.half(rug)) + 1.7)          # its edge clear of the front walls, which hide what is by them
            u, v = u1 - k, v0 + k
            if len(items(f, RUG)) < 2 and not on_carpet(f, u, v, pad=1.6) and clear_at(f, u, v, 1.2) and \
                    put(f, rug, u, v, blocking=False): return ["rug"]
        return None
    return None


def _rug_type(f, rng):
    types = [t for t in (f.types_of("rug") or {}) if re.match(RUG, t)] or \
        [t for t in ("RedRug1", "RedRug2", "BearskinRug1") if f.ok_type(t)]
    return rng.choice(sorted(types)) if types else None


def _centre_rugs(f, bed):
    """Each rug object centred in its part of the room (RM-BEDROOM-07: "the bear skin rug needs to be more centred in
    the south-eastern volume of the room"): the room split across its long axis, a rug in the half without the bed
    centred in it when it fits there."""
    u0, u1, v0, v1 = box(f)
    long_u = (u1 - u0) >= (v1 - v0)
    bed_rec = bed[2]
    for o, t, rec in items(f, RUG):
        if long_u:
            mid = (u0 + u1) / 2
            half = (u0, mid) if rec[0] < mid else (mid, u1)
            if half[0] <= bed_rec[0] <= half[1]: continue
            cu, cv = (half[0] + half[1]) / 2, (v0 + v1) / 2
        else:
            mid = (v0 + v1) / 2
            half = (v0, mid) if rec[1] < mid else (mid, v1)
            if half[0] <= bed_rec[1] <= half[1]: continue
            cu, cv = (u0 + u1) / 2, (half[0] + half[1]) / 2
        if math.hypot(rec[0] - cu, rec[1] - cv) < 0.6 or on_carpet(f, cu, cv, pad=1.8): continue
        f._remove(o)
        if not put(f, t, cu, cv, blocking=False):
            put(f, t, rec[0], rec[1], blocking=False)


def _dress_backs(f, rng, shelves=False, most=4):
    """The bare stretches of the NE and NW walls (QA round 1: "more wall objects (banners, trophies, bookshelves,
    etc)"): a pair of bookcases end to end on a long bare stretch, then hangings."""
    if shelves and not items(f, r"^Bookcase") or shelves and len(f.room.tiles) >= 50:
        line_pair(f, rng, "Bookcase", 2, min_len=4.0)
    hang_backs(f, rng, most)


# ---- shared: rows along a wall, knots, corners ---------------------------------------------------------------------
ARMS_HUNG = r"^(TraderHangingSwords\d|TraderShieldWallHanging\d|TraderCrossedWeapons\d|TraderHangingCrossbow\d)$"
RACK_KINDS = (r"^TraderArmorRack[12]$", r"^TraderPoleArm[1-4]$", r"^TraderBowRack[12]$", r"^TraderQuiverRack$")


def _types(f, rx):
    return sorted(t for t in f.things if re.match(rx, t) and f.ok_type(t))


def wall_row(f, rng, kinds, n, sides=BACK, skip_runs=(), gap=0.5, min_n=2, near_end=False):
    """A row of up to `n` pieces against one wall, centred on its longest free stretch, the kinds alternating (one kind
    never side by side: kit/objects.py runs, HB-5), even gaps: a row reads as one deliberate group (QA round 1, barracks:
    "one wall of beds and one wall of weapon and armor racks"). kinds: [regex] cycled. Returns the pieces."""
    pools = [_types(f, k) for k in kinds]
    pools = [p for p in pools if p]
    if not pools: return []
    best = None
    for r in f.g.runs:
        if r["side"] not in sides or any(r is s for s in skip_runs): continue
        for a0, a1 in free_stretches(f, r):
            a0, a1 = max(a0, r["lo"] + 1.4), min(a1, r["hi"] - 1.4)
            if a1 - a0 > 2.0 and (best is None or a1 - a0 > best[0]): best = (a1 - a0, r, a0, a1)
    if not best: return []
    _, r, a0, a1 = best
    seq = []
    for k in range(n):
        t0 = rng.choice(pools[k % len(pools)])
        t = f.side_variant(t0, r, F._family_of(t0)) or t0
        if not f.ok_type(t): t = t0
        seq.append(t)
    while seq:
        widths = [2 * halves_on(r, (0, 0) + f.half(t))[0] for t in seq]
        total = sum(widths) + gap * (len(seq) - 1)
        if total <= a1 - a0: break
        seq.pop()
    if len(seq) < min_n: return []
    widths = [2 * halves_on(r, (0, 0) + f.half(t))[0] for t in seq]
    total = sum(widths) + gap * (len(seq) - 1)
    a = (a0 + a1) / 2 - total / 2
    got = []
    for t, w in zip(seq, widths):
        hp = halves_on(r, (0, 0) + f.half(t))[1]
        u, v = uv_on(r, hp + 0.3, a + w / 2)
        o = put(f, t, u, v)
        if o: got.append(o)
        elif os.environ.get("NOX_FINISH_DEBUG"):
            hu, hv = f.half(t)
            print("  fail", t, round(u, 2), round(v, 2), "fits", f.g.fits(u, v, hu, hv, True, False, 0.1),
                  "inside", f.g.inside(u, v), "wd", round(f.g.wall_dist(u, v), 2), "bbw", f.g.before_back_wall(u, v),
                  "zones", [z for z in f.g.zones if u + hu > z[0] and u - hu < z[1] and v + hv > z[2] and v - hv < z[3]][:2],
                  "reach", f.g.reachable_ok((u, v, hu, hv, True, "floor")),
                  "doors", [(round(du, 1), round(dv, 1)) for du, dv in f.g.doors if math.hypot(u - du, v - dv) < 4],
                  "near", [(tt, round(rr[0], 1), round(rr[1], 1), rr[4], rr[5]) for tt, rr in f._typed
                           if abs(rr[0] - u) < 2.5 and abs(rr[1] - v) < 2.5])
        a += w + gap
    if os.environ.get("NOX_FINISH_DEBUG"):
        print("wall_row", f.kind, f.room.id, WALL_NAME.get(r["side"]), round(a1 - a0, 1), seq, len(got), dict(f.kb_refused))
    if len(got) < min_n:
        remove(f, got); return []
    return got


def knot(f, rng, u, v, types, n=3, spread=0.75):
    """A tight knot of `n` pieces (barrels and sacks) round (u, v), touching. Returns the pieces."""
    got = []
    tries = [(0.0, 0.0)] + [(spread * math.cos(k * 2.1 + 0.3), spread * math.sin(k * 2.1 + 0.3)) for k in range(6)]
    for du, dv in tries:
        if len(got) >= n: break
        t = rng.choice(types)
        saved = f.g.zones
        f.g.zones = saved[:len(f.openings)]
        try:
            o = f.try_put(t, u + du, v + dv, snug=True, touch=True)
        finally:
            f.g.zones = saved
        if o: got.append(o)
    return got


def fill_corners(f, rng, plan, inset=1.5, rad=1.5):
    """Each bare corner of the room takes the next group of `plan` ([callable(u, v) -> pieces])."""
    k = 0
    for name, u, v in sorted(free_corners(f, inset, rad), key=lambda c: "SEWN".index(c[0])):
        if k >= len(plan): break
        if plan[k](u, v): k += 1


# ---- barracks (Q1R-8, Q1R-9) ---------------------------------------------------------------------------------------
def _barracks(f, rng):
    """One wall of bunks, a chest at every foot; one back wall of racks of arms and armour; the crew's arms hung on the
    bare back wall; the crew's table; knots of barrels in the bare corners (QA round 1: "instead of having two walls lined
    with beds, try one wall of beds and one wall of weapon and armor racks. Transform the barracks from a giant room
    with beds to a place where warriors sleep and keep their combat gear"; RM-BARRACKS-09 "the best example of a human
    barracks ... needs more decorations on the walls and a few more objects")."""
    beds = items(f, BED)
    if not beds: return
    stem = re.match(r"^(\D+)", beds[0][1]).group(1)
    old = [b[0] for b in beds]
    for b in beds:                              # the bunks are laid again on one wall, with what stood by them
        old += [c[0] for c in items(f, CHEST + r"|^Nightstand\d|" + RUG)
                if max(abs(c[2][0] - b[2][0]) - c[2][2] - b[2][2], abs(c[2][1] - b[2][1]) - c[2][3] - b[2][3]) < 1.6]
    old = list({id(o): o for o in old}.values())
    keep = [(o["type"], f._placed_of[id(o)][0], f._placed_of[id(o)][1]) for o in old if id(o) in f._placed_of]
    remove(f, old)
    row = bunk_wall(f, rng, stem, want=max(3, min(10, len(f.room.tiles) // 13)))
    if len(row) < 2:                            # no wall holds a row: as it was
        remove(f, row)
        for t, u, v in keep: restore(f, t, u, v)
        return
    bed_run = run_of(f, f._placed_of[id(row[0])], reach=1.6)
    skip = [bed_run[0]] if bed_run else []
    n = max(3, min(7, len(f.room.tiles) // 20))
    wall_row(f, rng, RACK_KINDS[:3], n, sides=BACK, skip_runs=skip)
    if len(f.room.tiles) >= 110:               # a big room: a second row of racks on another wall
        wall_row(f, rng, RACK_KINDS[:3], n, sides=tuple(WALL_NAME), skip_runs=skip)
    hang_backs(f, rng, most=4 if len(f.room.tiles) >= 80 else 2, types={t: 1 for t in _types(f, ARMS_HUNG)})
    tables = items(f, TABLE)
    cu, cv = f.g.centroid
    if tables and len(f.room.tiles) >= 90 and clear_at(f, cu, cv, 3.0):
        # a big room's bare middle takes the crew's table, moved there whole with its seats
        o, t, rec = tables[0]
        seats = [(so, st, sr) for so, st, sr in items(f, SEAT) if max(abs(sr[0] - rec[0]) - sr[2] - rec[2],
                                                                     abs(sr[1] - rec[1]) - sr[3] - rec[3]) < 0.8]
        remove(f, [o] + [x[0] for x in seats])
        o2 = put(f, t, cu, cv)
        if o2 and f.seats_around((cu, cv), t, max(2, len(seats)), "chair") >= 2:
            tables = items(f, TABLE)
        else:
            for so, _, sr in items(f, SEAT):
                if max(abs(sr[0] - cu), abs(sr[1] - cv)) < 2.6: f._remove(so)
            if o2: f._remove(o2)
            restore(f, t, rec[0], rec[1])
            for so, st, sr in seats: restore(f, st, sr[0], sr[1])
    if not tables or (len(f.room.tiles) >= 90 and len(tables) < 2):
        # the crew's table in the middle, seated both sides (a big barracks' open floor: RM-BARRACKS-03, -06 rated 2-3)
        cu, cv = f.g.centroid
        for du, dv in ((0, 0), (1.5, 0), (-1.5, 0), (0, 1.5), (0, -1.5)):
            if not clear_at(f, cu + du, cv + dv, 2.4): continue
            t = rng.choice(_types(f, r"^Table[1-4]$") or ["Table1"])
            o = put(f, t, cu + du, cv + dv)
            if not o: continue
            if f.seats_around((cu + du, cv + dv), t, 4, "chair") >= 2: break
            for so, _, sr in items(f, SEAT):
                if max(abs(sr[0] - cu - du), abs(sr[1] - cv - dv)) < 2.6: f._remove(so)
            f._remove(o)
    barrels = _types(f, r"^(Barrel|Barrel2|BarrelWithTools[12])$")
    fill_corners(f, rng, [lambda u, v: knot(f, rng, u, v, barrels, 3),
                          lambda u, v: knot(f, rng, u, v, _types(f, r"^(Crate[12]|Barrel)$"), 2)])
    hang_backs(f, rng, most=2)


def bunk_wall(f, rng, stem, want):
    """Up to `want` beds of `stem` headboard to one wall, evenly spaced 1.0-1.6 units apart, centred on the wall's
    longest free stretch (the wall holding the most; a front wall, SE or SW, before a back wall, which keeps its back
    walls for the racks and hangings the camera sees), a chest at each foot. Returns the beds."""
    best = None
    for r in f.g.runs:
        t = f.along_variant(stem + "1", r["side"])
        if not t or not f.ok_type(t): continue
        hu, hv = f.half(t)
        ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
        for a0, a1 in free_stretches(f, r):
            a0, a1 = max(a0, r["lo"] + 1.2), min(a1, r["hi"] - 1.2)
            k = min(want, int((a1 - a0 + 1.0) / (2 * ha + 1.0)))
            if k < 2: continue
            score = (k + (0.6 if r["side"] not in BACK else 0.0), a1 - a0)
            if best is None or score > best[0]: best = (score, r, t, a0, a1, ha, hp, k)
    if not best: return []
    _, r, t, a0, a1, ha, hp, k = best
    gap = min(1.6, (a1 - a0 - 2 * ha * k) / max(1, k - 1)) if k > 1 else 0
    total = 2 * ha * k + gap * (k - 1)
    a = (a0 + a1) / 2 - total / 2 + ha
    got = []
    for _ in range(k):
        o = put(f, t, *uv_on(r, hp + 0.3, a))
        if o:
            got.append(o)
            c = variant(f, "Chest", r["side"])
            if c and f.ok_type(c):
                chp = halves_on(r, (0, 0) + f.half(c))[1]
                put(f, c, *uv_on(r, 2 * hp + 0.3 + 0.5 + chp, a))
        a += 2 * ha + gap
    return got


# ---- the ogres' den (Q1R-10) ---------------------------------------------------------------------------------------
def _ogre_den(f, rng):
    """The mana obelisks as a symmetric pair, in the two corners of the longest back wall (four in a den of 150 tiles
    or more: every corner but the S, which takes the stores); the front corners never bare (RM-BARRACKS-04 "when
    placing two mana obelisks, place them with symmetry. For example, in the corners"; -05 "the right side is too
    empty"; -08 "needs more objects, especially on the SE"; -10 "add an object or two to the south corner area")."""
    ob = items(f, r"^ObeliskPrimitive$")
    remove(f, [o for o, _, _ in ob])
    obelisk_pair(f, rng, "ObeliskPrimitive", inset=1.3, four=len(f.room.tiles) >= 150)
    stores = _types(f, r"^(Barrel|Barrel2|OgreSack[12])$")
    meat = _types(f, r"^OgreHutMeat$")
    fill_corners(f, rng, [lambda u, v: knot(f, rng, u, v, stores, 3),
                          lambda u, v: knot(f, rng, u, v, stores + meat, 2),
                          lambda u, v: knot(f, rng, u, v, meat or stores, 1)], inset=1.6, rad=1.6)
    hang_backs(f, rng, most=2, types={t: 1 for t in _types(f, r"^OgreHutWallSkull[1-4]$")})


def obelisk_pair(f, rng, t, inset=1.3, four=False):
    """A pair of `t` in the two corners at the ends of the longest back wall (or all four corners). Returns them."""
    if not f.ok_type(t): return []
    u0, u1, v0, v1 = box(f)
    pts = corner_points(f, inset)
    nw_len, ne_len = v1 - v0, u1 - u0                      # the NW wall runs along v, the NE along u
    pairs = [("N", "E") if ne_len >= nw_len else ("W", "N"), ("W", "N") if ne_len >= nw_len else ("N", "E"),
             ("W", "E")]
    if four: pairs = [("N", "E", "W", "S")] + pairs
    movable = r"^(Barrel|Barrel2|OgreSack\d|PiledBarrels\d|TorchPole|OgreHutMeat|OgreStraw\d|Crate\d)$"
    for names in pairs:
        if any(not f.g.inside(*pts[k]) or not _no_door(f, *pts[k], 2.8) for k in names): continue
        # the corners cleared of what was heaped there (it is heaped again in the corners left bare)
        for k in names:
            u, v = pts[k]
            remove(f, [o for o, tt, rr in items(f, movable) if max(abs(rr[0] - u) - rr[2], abs(rr[1] - v) - rr[3]) < 1.3])
        got = []
        for k in names:
            u, v = pts[k]
            o = put_corner(f, t, u, v) if f.g.inside(u, v) else None
            if not o:
                if os.environ.get("NOX_FINISH_DEBUG"):
                    hu, hv = f.half(t)
                    print("obelisk fail", k, round(u, 1), round(v, 1), f.g.inside(u, v), f.ok_type(t),
                          f.g.fits(u, v, hu, hv, True, False, 0.1),
                          "pts", all(f.g.inside(u + a * hu, v + b * hv) for a in (-1, 0, 1) for b in (-1, 0, 1)),
                          "wd", round(min(f.g.wall_dist(u + a * hu, v + b * hv) for a in (-1, 0, 1) for b in (-1, 0, 1)), 2),
                          "bbw", f.g.before_back_wall(u, v),
                          "door", round(min([math.hypot(u - du, v - dv) for du, dv in f.g.doors] or [99]), 1),
                          "zone", any(u + hu > z[0] and u - hu < z[1] and v + hv > z[2] and v - hv < z[3] for z in f.g.zones),
                          [(tt, round(rr[0], 1), round(rr[1], 1)) for tt, rr in f._typed if abs(rr[0] - u) < 2 and abs(rr[1] - v) < 2])
                break
            got.append(o)
        if len(got) == len(names): return got
        remove(f, got)
    return []


# ---- cells (Q1R-11, Q1R-12) ----------------------------------------------------------------------------------------
CELL_DOUBLE = 36           # tiles: a human cell this big holds two cots (RM-CELL-07: 49 tiles "very large for a single
                           # cell with one bed. Adding another bed would make this better")


def _cell(f, rng):
    """A human cell: its cot (two side by side in a cell of CELL_DOUBLE tiles or more), the stocks, a bench or a stool
    (QA round 1: "Cells with stockades look really good because the extra object really helps establish an identity.
    Try some other objects that would make sense in a cell too. a bench or a stool. Make larger cells double
    occupancy")."""
    cots = items(f, r"^Cot\d$")
    if cots and len(f.room.tiles) >= CELL_DOUBLE and len(cots) < 2:
        o, t, rec = cots[0]
        w = run_of(f, rec, reach=1.0)
        if w:
            r, a, _ = w
            ha, hp = halves_on(r, rec)
            for s in rng.sample((-1, 1), 2):
                for gap in (1.4, 1.8, 1.1):
                    u, v = uv_on(r, perp_of(r, rec[0], rec[1]), a + s * (2 * ha + gap))
                    if put(f, t, u, v): break
                else:
                    continue
                break
            else:                                       # no room on its wall: a cot on another back wall
                f.place_on_wall("bed", at="center", clear=0.8, only=r"^Cot", back_only=True)
    if not items(f, r"^Stocks\d$") and len(f.room.tiles) >= 16:
        centre_on_back(f, rng, "Stocks", min_len=1.6, sides=tuple(WALL_NAME))
    if not items(f, r"^(Bench\d|Stool\d|LightBench\d)$"):
        if not centre_on_back(f, rng, "Bench", min_len=2.8) and                 not centre_on_back(f, rng, "Bench", min_len=2.8, sides=tuple(WALL_NAME)):
            for _, u, v in free_corners(f, 1.0, 1.0)[:1]:
                put(f, rng.choice(_types(f, r"^Stool[1-4]?$") or ["Stool"]), u, v)


def _ogre_pen(f, rng):
    """An ogre pen: its straw heaped in one corner (the one farthest from the door), the obelisk in another, the stocks
    against a wall, the other corners never bare (RM-CELL-02: "The ogre straw looks better when it's in a corner or end
    of the room. the E corner being bare here doesn't look good")."""
    straw = items(f, r"^OgreStraw\d$")
    kinds = sorted({t for _, t, _ in straw}) or _types(f, r"^OgreStraw[1-3]$")
    remove(f, [o for o, _, _ in straw])
    ob = items(f, r"^ObeliskPrimitive$")
    pts = corner_points(f, 1.7)
    doors = f.g.doors or [f.g.centroid]
    order = sorted(pts, key=lambda k: -min(math.hypot(pts[k][0] - du, pts[k][1] - dv) for du, dv in doors))
    heap = order[0]
    hu, hv = pts[heap]
    n = max(5, min(9, len(f.room.tiles) // 6))
    got = 0
    for k in range(40):
        if got >= n: break
        ang = k * 2.4; rad = 0.25 + 0.3 * math.sqrt(k)
        if put(f, rng.choice(kinds), hu + rad * math.cos(ang), hv + rad * math.sin(ang), blocking=False): got += 1
    if ob:                                            # the obelisk in the corner across from the heap
        o, t, rec = ob[0]
        far = [k for k in order[1:] if k != heap]
        for k in far:
            u, v = corner_points(f, 1.2)[k]
            f._remove(o)
            if put(f, t, u, v): break
            o = restore(f, t, rec[0], rec[1])
    bones = _types(f, r"^(Skull|ArmBone|LegBone)$")
    stores = _types(f, r"^(Barrel|OgreSack[12]|OgreStool[12])$")
    fill_corners(f, rng, [lambda u, v: knot(f, rng, u, v, stores, 2),
                          lambda u, v: knot(f, rng, u, v, bones or stores, 2),
                          lambda u, v: knot(f, rng, u, v, stores, 1)], inset=1.4, rad=1.3)


# ---- dispatch ------------------------------------------------------------------------------------------------------
PASSES = {"bedroom": _bedroom, "barracks": _barracks, "ogre_den": _ogre_den, "cell": _cell, "ogre_pen": _ogre_pen}
COMPOSERS = {}


def finish(f):
    """The room's finishing pass (both engines' last step)."""
    fn = PASSES.get(f.kind)
    if not ENABLED or not fn: return
    with _State(f):
        f.rng = _rng(f, "rng")
        fn(f, _rng(f, f.kind))


def compose(f):
    """A room kind composed here whole (the conservatory): True when it was."""
    fn = COMPOSERS.get(f.kind)
    if not ENABLED or not fn: return False
    with _State(f):
        f.rng = _rng(f, "rng")
        fn(f, _rng(f, f.kind))
    return True
