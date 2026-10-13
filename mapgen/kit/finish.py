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
        before = dict(f.kb_refused)
        o = put(f, t, u, v)
        if not o:
            if os.environ.get("NOX_FINISH_DEBUG"):
                hu, hv = f.half(t)
                print("table_set fail", f.room.id, t, round(u, 1), round(v, 1), "fits", f.g.fits(u, v, hu, hv, True, False, 0.1),
                      "reach", f.g.reachable_ok((u, v, hu, hv, True, "floor")),
                      {k: n - before.get(k, 0) for k, n in f.kb_refused.items() if n != before.get(k, 0)},
                      [(tt, round(rr[0], 1), round(rr[1], 1)) for tt, rr in f._typed if abs(rr[0] - u) < 2.5 and abs(rr[1] - v) < 2.5])
            continue
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
    chests0 = [(t, rec[0], rec[1]) for _, t, rec in items(f, CHEST)]
    bed = max(beds, key=lambda b: b[2][2] * b[2][3])
    before = [(t, rec[0], rec[1]) for _, t, rec in items(f, r"^Nightstand\d")]
    head = head_wall(f, bed)
    f._fin_bed = None
    got = _nightstands(f, bed, head, rng, pair_only=True) if head else None
    if not got and f._fin_bed: bed = f._fin_bed
    # (round 2: a bed pushed toward the end of its wall, its nightstands squeezed in, is set again centred: RM-BEDROOM-08,
    # whose bed stood 1.5 units from the E corner, still read "away" from its wall's middle)
    hw = head_wall(f, got) if got else None
    if os.environ.get("NOX_FINISH_DEBUG"):
        print("bedcheck", f.room.id, bool(got), hw and (WALL_NAME[hw[0]["side"]], hw[0]["lo"], hw[0]["hi"], round(hw[1], 1)),
              hw and _centred_on_stretch(f, got[2], hw), head and WALL_NAME[head[0]["side"]])
    if not got or _in_corner(f, got[2], hw or head, margin=2.6 if hw and not _centred_on_stretch(f, got[2], hw) else 1.6):
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
    _seat_bare_tables(f)
    if len(f.room.tiles) >= BEDROOM_ZONE2: _second_zone(f, rng, bed)
    _south_corner(f, rng, sitting=True)
    _centre_rugs(f, bed)
    # round 3 (the coordinator's zones by size): the seating group in every bedroom, the work and storage zones from 50
    # room tiles (40 as the checker counts), a hearth zone from 100 (80)
    _seating(f, rng, bed)
    tiles = len(f.room.tiles)
    if tiles >= BEDROOM_WORK: _work_zone(f, rng, bed); _storage_zone(f, rng, bed)
    if tiles >= BEDROOM_HEARTH: _hearth_zone(f, rng, bed)
    _dress_backs(f, rng, shelves=True, most=5 if tiles >= 40 else 3)
    _dress_each_back(f, rng)
    if tiles >= 20: _second_rug(f, rng, bed)
    _front_wall_piece(f, rng)
    _no_twin_rugs(f, rng)
    _kinds_goal(f, rng, BEDROOM_KINDS[2] if tiles >= BEDROOM_HEARTH else BEDROOM_KINDS[1] if tiles >= BEDROOM_WORK
                else BEDROOM_KINDS[0])
    if not items(f, CHEST) and head_wall(f, bed):  # the chest at the bed's foot, a little further out if need be
        r, a, _ = head_wall(f, bed)
        t = variant(f, "Chest", r["side"])
        if t and f.ok_type(t):
            _, bhp = halves_on(r, bed[2]); chp = halves_on(r, (0, 0) + f.half(t))[1]
            foot = perp_of(r, bed[2][0], bed[2][1]) + bhp
            for gap in (0.8, 1.0, 1.3, 1.6):
                if force_put(f, t, *uv_on(r, foot + gap + chp, along_of(r, bed[2][0], bed[2][1]))): break
    if not items(f, CHEST):                       # never a bedroom without its chest (round 2: one lost in a bed's move)
        if not centre_on_back(f, rng, "Chest", min_len=2.0) and not centre_on_back(f, rng, "Chest", min_len=1.6,
                                                                                    sides=tuple(WALL_NAME)):
            f.place_on_wall("storage", at="any", clear=0.6, only=r"^Chest|^DunMirChest")
    if not items(f, CHEST):
        for t, u, v in chests0:                   # nowhere new: where it stood, if that is still free
            hu, hv = f.half(t)
            if f.g.fits(u, v, hu, hv, True, False, 0.1) and restore(f, t, u, v): break


BEDROOM_ZONE2 = 40         # room tiles (wall lines included; about 30 as the checker counts): a second zone from here
BEDROOM_WORK = 50          # room tiles (40 as the checker counts): a work zone and a storage zone (round 3)
BEDROOM_HEARTH = 100       # room tiles (80 as the checker counts): a third zone, the hearth (round 3)
BEDROOM_KINDS = (6, 8, 11)  # visible kinds a bedroom holds: under 40 tiles, 40+, 80+ as the checker counts (round 3)
RUG_KINDS = ("RedRug1", "RedRug2", "RedRug3", "RedRug4", "BearskinRug1", "BearskinRug2")


def visible_kinds(f):
    """The room's visible kinds of thing, as checks.qa1_fullness counts them (type stems; tiny pieces one kind)."""
    tiny = re.compile(r"Skull|Bone|Cobweb|Candle|RedApple|Meat|Bread|Cheese|Mushroom|Potion$|Cider")
    out = set()
    for o in f.objects:
        t = o["type"]
        if re.search(r"ColorLight|Candleabra|Candelabra|TorchPole|Lantern|Door", t): continue
        out.add("tiny" if tiny.search(t) else re.sub(r"(\d+[a-h]?|NE|NW|SE|SW)$", "", t))
    return out


def _seating(f, rng, bed):
    """Every bedroom's seating group: a table with two chairs drawn up, else (a small room whose one set is its desk)
    two benches facing each other across a rug, in the half of the room without the bed."""
    for o, t, rec in items(f, TABLE):
        k = len([x for x in items(f, SEAT) if max(abs(x[2][0] - rec[0]) - x[2][2] - rec[2],
                                                   abs(x[2][1] - rec[1]) - x[2][3] - rec[3]) < 0.8])
        if k < 2: k += f.seats_around((rec[0], rec[1]), t, 2 - k, "chair")    # a second chair drawn up
        if k >= 2: return
    _, other = _halves(f, bed)
    cu, cv = (other[0] + other[1]) / 2, (other[2] + other[3]) / 2
    spot = _near_spot(f, cu, cv, rad=1.8)
    if spot and table_set(f, *spot): return
    # the bench pair across a rug: the first spot of the bed-less half (nearest its middle) where both benches stand,
    # either way round
    U0, U1, V0, V1 = box(f)
    cands = sorted(((U0 + 1.5 + 0.5 * i, V0 + 1.5 + 0.5 * j)
                    for i in range(int((U1 - U0 - 3) / 0.5) + 1)
                    for j in range(int((V1 - V0 - 3) / 0.5) + 1)),
                   key=lambda p_: (p_[0] - cu) ** 2 + (p_[1] - cv) ** 2)
    if not cands: cands = [(cu, cv)]
    for su, sv in cands[:80]:
        if not f.g.inside(su, sv) or not clear_at(f, su, sv, 0.6): continue
        for long_u in (True, False):
            b = next((x for x in (("Bench2", "Bench3") if long_u else ("Bench1", "Bench4")) if f.ok_type(x)), None)
            if not b: continue
            hb = f.half(b)
            d = (hb[1] if long_u else hb[0]) + 0.9
            pts = [(su, sv - d), (su, sv + d)] if long_u else [(su - d, sv), (su + d, sv)]
            got = [force_put(f, b, u, v) for u, v in pts]
            if all(got):
                rug = _rug_type(f, rng, avoid=[t for _, t, _ in items(f, RUG)])
                ok = False
                if rug and not on_carpet(f, su, sv, pad=1.0):
                    rh = f.half(rug)                 # the rug under the pair: inside the room, on no other rug
                    if all(f.g.inside(su + a * rh[0], sv + b * rh[1]) for a in (-1, 1) for b in (-1, 1)) and                             not any(F.Furnisher._overlap(su, sv, rh[0], rh[1], rr) for _, _, rr in items(f, RUG)):
                        ok = f.put(rug, su, sv, False)
                if os.environ.get("NOX_FINISH_DEBUG"): print("benchrug", f.room.id, rug, bool(ok), [t for _, t, _ in items(f, RUG)])
                return
            remove(f, [g for g in got if g])
    # a small room: two chairs facing each other across a small rug, drawn up to each other (a sitting pair)
    seats = f.types_of("chair") or {"WoodenChair1": 1}
    base = f.palette_seat("chair", seats) or "WoodenChair"
    for su, sv in cands[:120]:
        if not f.g.inside(su, sv) or not clear_at(f, su, sv, 0.4): continue
        # (clear of the bed, the chest and the door: the pair had crowded a bed's foot)
        if any(max(abs(su - rr[0]) - rr[2], abs(sv - rr[1]) - rr[3]) < 2.0 for _, _, rr in items(f, BED + "|" + CHEST)):
            continue
        if not _no_door(f, su, sv, 3.0): continue
        for ax in ("u", "v"):
            pts = [(su - 0.9, sv), (su + 0.9, sv)] if ax == "u" else [(su, sv - 0.9), (su, sv + 0.9)]
            dirs = ["+u", "-u"] if ax == "u" else ["+v", "-v"]
            got = []
            for (u, v), d in zip(pts, dirs):
                ct = ((f.chair_facing.get(base, {}) or {}).get(d) or {}).get("variant")
                ct = ct if ct and f.ok_type(ct) else next((c for c in sorted(seats) if c.startswith(base)), "WoodenChair1")
                got.append(force_put(f, ct, u, v))
            if all(got):
                rug = _rug_type(f, rng, avoid=[t for _, t, _ in items(f, RUG)])
                if rug and not on_carpet(f, su, sv, pad=0.8):
                    rh = f.half(rug)
                    if all(f.g.inside(su + a * rh[0], sv + b * rh[1]) for a in (-1, 1) for b in (-1, 1)) and                             not any(F.Furnisher._overlap(su, sv, rh[0], rh[1], rr) for _, _, rr in items(f, RUG)):
                        f.put(rug, su, sv, False)
                return
            remove(f, [g for g in got if g])
    if os.environ.get("NOX_FINISH_DEBUG"): print("seating none", f.room.id, len(cands), [round(x, 1) for x in other])


def _work_zone(f, rng, bed):
    """The work zone (40+ tiles as the checker counts): the desk with its chair centred on a back wall of the half
    without the bed, a bookcase beside it (one stands in the room already: one beside the desk all the same)."""
    desks = items(f, r"^Desk\d$")
    if desks:
        o, t, rec = desks[0]
        w = run_of(f, rec)
        if w and not items(f, r"^Bookcase") or w:
            r, a, _ = w
            ha, _ = halves_on(r, rec)
            bt = f.along_variant("Bookcase1", r["side"])
            if bt and f.ok_type(bt) and not any(math.hypot(x[2][0] - rec[0], x[2][1] - rec[1]) < 2.4
                                                for x in items(f, r"^Bookcase")):
                bha, bhp = halves_on(r, (0, 0) + f.half(bt))
                for s in rng.sample((-1, 1), 2):
                    if f.try_put(bt, *uv_on(r, bhp + 0.18, a + s * (ha + bha + 0.3)), snug=True): break
        return
    _, other = _halves(f, bed)
    u0, u1, v0, v1 = box(f)
    for area in (other, (u0, u1, v0, v1)):            # the bed-less half first, else any back-wall stretch
        for r in sorted((r for r in f.g.runs if r["side"] in BACK), key=lambda r: -(r["hi"] - r["lo"])):
            lo, hi = (area[2], area[3]) if r["line"] == "/" else (area[0], area[1])
            t = f.along_variant("Desk1", r["side"])
            if not t or not f.ok_type(t): continue
            ha, hp = halves_on(r, (0, 0) + f.half(t))
            for a0, a1 in free_stretches(f, r):
                a0, a1 = max(a0, lo, r["lo"] + 1.4), min(a1, hi, r["hi"] - 1.4)
                if a1 - a0 < 2 * ha + 0.2: continue
                o = scan_put(f, t, r, a0, a1, hp + 0.25)
                if not o: continue
                rec = f._placed_of[id(o)]
                mid = along_of(r, rec[0], rec[1])
                f.seats_around((rec[0], rec[1]), t, 1)
                bt = f.along_variant("Bookcase1", r["side"])
                if bt and f.ok_type(bt):
                    bha, bhp = halves_on(r, (0, 0) + f.half(bt))
                    for s_ in rng.sample((-1, 1), 2):
                        if f.try_put(bt, *uv_on(r, bhp + 0.18, mid + s_ * (ha + bha + 0.3)), snug=True): break
                return


def scan_put(f, t, r, a0, a1, depth, force=False):
    """`t` against wall run r at `depth` from its line, at the first spot from the middle of [a0, a1] outward that takes
    it. Returns the piece or None."""
    ha = halves_on(r, (0, 0) + f.half(t))[0]
    mid = (a0 + a1) / 2
    for k in range(0, 24):
        a = mid + (k // 2) * 0.35 * (1 if k % 2 else -1)
        if a - ha < a0 or a + ha > a1: continue
        u, v = uv_on(r, depth, a)
        hu, hv = f.half(t)
        if any(F.Furnisher._overlap(u, v, hu, hv, rr) for _, _, rr in items(f, RUG)): continue   # never on a rug
        if on_carpet(f, u, v, pad=max(hu, hv) + 0.3): continue                                  # nor on the carpet
        o = force_put(f, t, u, v) if force else put(f, t, u, v)
        if o: return o
    return None


def _storage_zone(f, rng, bed):
    """The storage zone (40+ tiles as the checker counts): a clothes rack and a second chest, each on the longest free
    stretch of a wall that takes it (the back walls first)."""
    want = []
    if not items(f, r"^TraderClothesRack"):
        want.append(("rack", [t for t in ("TraderClothesRack1", "TraderClothesRack2") if f.ok_type(t)]))
    if len(items(f, CHEST)) < 2: want.append(("chest", ["Chest"]))
    _, other = _halves(f, bed)
    oc = ((other[0] + other[1]) / 2, (other[2] + other[3]) / 2)
    def near_other(r, a0, a1):                       # stretches in the bed-less half first
        u, v = uv_on(r, 1.0, (a0 + a1) / 2)
        return math.hypot(u - oc[0], v - oc[1]) - 0.3 * (a1 - a0)
    for what, types in want:
        done = False
        # (a rack stands on a front wall first: the SE and SW walls of a big bedroom stood bare, its back walls dressed)
        order = (BACK,) if what == "chest" else (tuple(x for x in WALL_NAME if x not in BACK), tuple(WALL_NAME))
        for sides in order:
            if done: break
            for r in sorted((r for r in f.g.runs if r["side"] in sides), key=lambda r: -(r["hi"] - r["lo"])):
                if done: break
                t = (variant(f, "Chest", r["side"]) if what == "chest" else
                     next((f.side_variant(x, r, "shop_rack") or x for x in types), None))
                if not t or not f.ok_type(t): continue
                hp = halves_on(r, (0, 0) + f.half(t))[1]
                for a0, a1 in sorted(free_stretches(f, r), key=lambda s_: near_other(r, *s_)):
                    a0, a1 = max(a0, r["lo"] + 1.2), min(a1, r["hi"] - 1.2)
                    if a1 - a0 < 1.4: continue
                    if scan_put(f, t, r, a0, a1, hp + 0.3, force=(what == "chest")):
                        done = True; break


def _hearth_zone(f, rng, bed):
    """The third zone (80+ tiles as the checker counts): a hearth centred on a free back-wall stretch, a pair of chairs
    drawn up before it on a rug, mirrored."""
    if items(f, r"Fireplace"): return
    for r in sorted((r for r in f.g.runs if r["side"] in BACK), key=lambda r: -(r["hi"] - r["lo"])):
        t = f.side_variant("Fireplace1", r, "fireplace") or f.along_variant("Fireplace1", r["side"])
        if not t or not f.ok_type(t): continue
        ha, hp = halves_on(r, (0, 0) + f.half(t))
        for a0, a1 in free_stretches(f, r):
            a0, a1 = max(a0, r["lo"] + 2.0), min(a1, r["hi"] - 2.0)
            if a1 - a0 < 4.0: continue
            mid = (a0 + a1) / 2
            o = put(f, t, *uv_on(r, hp + 0.15, mid))
            if not o: continue
            ru, rv = uv_on(r, hp + 2.6, mid)
            rug = _rug_type(f, rng, avoid=[x for _, x, _ in items(f, RUG)])
            if rug and not on_carpet(f, ru, rv, pad=1.0): put(f, rug, ru, rv, blocking=False)
            ch = f.types_of("chair") or {"WoodenChair1": 1}
            c = sorted(ch)[0]
            for s in (-1, 1):
                force_put(f, c, *uv_on(r, hp + 2.6, mid + s * 1.4))
            return


def _dress_each_back(f, rng):
    """Both back walls dressed: a back wall with no shelf and no hanging takes a hanging centred on its longest bare
    stretch (a painting or a trophy when the room's theme cannot)."""
    for r in f.g.runs:
        if r["side"] not in BACK or r["hi"] - r["lo"] < 4: continue
        has = any(True for _ in wall_pieces(f, r, layer="wall")) or any(
            re.match(r"^(Bookcase|PotionShelves)", t) and (w := run_of(f, rec)) and w[0] is r for _, t, rec in items(f, r"^(Bookcase|PotionShelves)"))
        if has: continue
        types = dict(getattr(f, "_decor_types", None) or {})
        for t in sorted(f.things):
            if re.match(r"^(Painting[12]|WallTrophy(Bear|Moose)[12])$", t) and f.ok_type(t): types.setdefault(t, 1)
        inv = f.T["inventory"].get("wall_decor", {})
        best = None
        for a0, a1 in free_stretches(f, r):
            a0, a1 = max(a0, r["lo"] + 2.1), min(a1, r["hi"] - 2.1)
            if a1 - a0 > 0 and (best is None or a1 - a0 > best[1] - best[0]): best = (a0, a1)
        if not best: continue
        mid = (best[0] + best[1]) / 2
        for t0 in sorted(types, key=lambda x: rng.random()):
            t = f.side_variant(t0, r, "wall_decor") or t0
            if f.ok_type(t) and wall_at(f, r, mid) and \
                    f.try_put(t, *uv_on(r, f.perp_for(t, inv.get("perp_px")), mid), blocking=False, wall_ok=True, layer="wall"):
                break


RUG_DESIGN = {"RedRug1": "a", "RedRug2": "a", "RedRug3": "b", "RedRug4": "b"}   # one design, two turns (round 3)


def rug_design(t):
    return RUG_DESIGN.get(t, re.sub(r"\d$", "", t))


def _no_twin_rugs(f, rng):
    """No rug design repeated in one room (round 3: "the two rugs are the same piece repeated"): a second rug of one
    design becomes another design, else goes."""
    seen = set()
    for o, t, rec in items(f, RUG):
        d = rug_design(t)
        if d not in seen:
            seen.add(d); continue
        f._remove(o)
        alt = next((x for x in sorted(RUG_KINDS, key=lambda _: rng.random()) if f.ok_type(x) and rug_design(x) not in seen
                    and abs(f.half(x)[0] - rec[2]) + abs(f.half(x)[1] - rec[3]) < 1.0), None)
        if alt and put(f, alt, rec[0], rec[1], blocking=False): seen.add(rug_design(alt))


def _kinds_goal(f, rng, goal):
    """Pieces of further kinds until the room holds `goal` visible kinds: a bench on a bare front wall, potion shelves
    on a back wall, a painting, a trophy, a stool by the desk."""
    adds = [lambda: _front_wall_piece(f, rng, force=True),
            lambda: centre_on_back(f, rng, "PotionShelves", min_len=2.0),
            lambda: _hang_kind(f, rng, r"^Painting[12]$"),
            lambda: _hang_kind(f, rng, r"^WallTrophy(Bear|Moose|MountainLion)[12]$"),
            lambda: _hang_kind(f, rng, r"^(Red|Blue|Green)Tapestry\d$")]
    for add in adds:
        if len(visible_kinds(f)) >= goal: return
        try: add()
        except Exception: pass


def _hang_kind(f, rng, rx):
    types = {t: 1 for t in f.things if re.match(rx, t) and f.ok_type(t)}
    if types and not any(re.match(rx, o["type"]) for o in f.objects): hang_backs(f, rng, most=1, types=types)


def _halves(f, bed):
    """((u0, u1, v0, v1) of the room's half with the bed, the other half's), split across the room's long axis."""
    u0, u1, v0, v1 = box(f)
    rec = bed[2]
    if (u1 - u0) >= (v1 - v0):
        mid = (u0 + u1) / 2
        a, b = (u0, mid, v0, v1), (mid, u1, v0, v1)
        return (a, b) if rec[0] < mid else (b, a)
    mid = (v0 + v1) / 2
    a, b = (u0, u1, v0, mid), (u0, u1, mid, v1)
    return (a, b) if rec[1] < mid else (b, a)


def _second_zone(f, rng, bed):
    """The half of a bigger bedroom without the bed made a second zone (the coordinator, round 2: "for bedrooms over
    about 60 tiles add a second zone: desk or writing table with chair, wardrobe or dresser, a chest, a rug with a pair of
    chairs ... mirrored or centred on its wall"; RM-BEDROOM-06 "very empty and tons of dead space"): a sitting group (a
    small table with a chair either side) centred in that half, on a rug when it stands on the bare floor; the desk
    with its chair centred on that half's back wall, else a pair of bookcases there. No wardrobe or dresser exists among
    the game's objects."""
    # a rug object on the carpet is taken up first (never a rug on a carpet; it kept the set off the carpet's middle)
    for o, t, rec in items(f, RUG):
        if on_carpet(f, rec[0], rec[1], pad=0.6): f._remove(o)
    _, other = _halves(f, bed)
    hu0, hu1, hv0, hv1 = other
    cu, cv = (hu0 + hu1) / 2, (hv0 + hv1) / 2
    cb = carpet_box(f)                                # a carpet there: the group centred on it
    if os.environ.get("NOX_FINISH_DEBUG"):
        print("zone2", f.room.id, [round(x, 1) for x in other], cb, [(t, round(r_[0], 1), round(r_[1], 1)) for _, t, r_ in items(f, TABLE)])
    if cb:
        bu, bv = (cb[0] + cb[1]) / 2, (cb[2] + cb[3]) / 2
        if hu0 - 1 <= bu <= hu1 + 1 and hv0 - 1 <= bv <= hv1 + 1: cu, cv = bu, bv
    # a table set standing off to one side (a corner, a carpet's edge) moves whole to the zone's centre
    for o, t, rec in items(f, TABLE):
        if math.hypot(rec[0] - cu, rec[1] - cv) < 1.5: break
        seats = [x for x in items(f, SEAT) if max(abs(x[2][0] - rec[0]) - x[2][2] - rec[2],
                                                  abs(x[2][1] - rec[1]) - x[2][3] - rec[3]) < 0.8]
        keep = [(t, rec[0], rec[1])] + [(x[1], x[2][0], x[2][1]) for x in seats]
        if os.environ.get("NOX_FINISH_DEBUG"):
            print("zone2 move", f.room.id, t, round(rec[0], 1), round(rec[1], 1), "->", round(cu, 1), round(cv, 1),
                  clear_at(f, cu, cv, 2.2), [(tt, round(rr[0], 1), round(rr[1], 1)) for tt, rr in f._typed
                                             if rr[4] and abs(rr[0] - cu) < 3 and abs(rr[1] - cv) < 3])
        remove(f, [o] + [x[0] for x in seats])
        spot = _near_spot(f, cu, cv)
        if not spot or not table_set(f, *spot, types=[t] + [x for x in ("SquareTable1", "RoundTable1") if x != t]):
            for tt, u, v in keep: restore(f, tt, u, v)
        break
    spot = _near_spot(f, cu, cv)
    if spot: cu, cv = spot
    if not items(f, TABLE) and spot:
        long_u = (hu1 - hu0) >= (hv1 - hv0)
        got = table_set(f, cu, cv, axis="v" if long_u else "u")
        if got and not on_carpet(f, cu, cv, pad=1.2):
            rt = [t for t in ("RedRug1", "RedRug2", "RedRug3", "RedRug4") if f.ok_type(t)]
            if rt:
                for o in got: f._remove(o)                     # the rug first, the set on it
                rug = put(f, rng.choice(rt), cu, cv, blocking=False)
                got = table_set(f, cu, cv, axis="v" if long_u else "u")
                if not got and rug: f._remove(rug); table_set(f, cu, cv, axis="v" if long_u else "u")
    # the back wall of that half: the desk and its chair centred, else a pair of bookcases
    desk_done = bool(items(f, r"^Desk\d$"))
    for r in f.g.runs:
        if r["side"] not in BACK: continue
        lo, hi = (hv0, hv1) if r["line"] == "/" else (hu0, hu1)
        best = None
        for a0, a1 in free_stretches(f, r):
            a0, a1 = max(a0, lo + 0.5, r["lo"] + 1.4), min(a1, hi - 0.5, r["hi"] - 1.4)
            if a1 - a0 > 2.4 and (best is None or a1 - a0 > best[1] - best[0]): best = (a0, a1)
        if not best: continue
        mid = (best[0] + best[1]) / 2
        if not desk_done:
            t = f.along_variant("Desk1", r["side"])
            if t and f.ok_type(t):
                ha, hp = halves_on(r, (0, 0) + f.half(t))
                if best[1] - best[0] >= 2 * ha + 0.4:
                    u, v = uv_on(r, hp + 0.25, mid)
                    o = put(f, t, u, v)
                    if o:
                        f.seats_around((u, v), t, 1)
                        desk_done = True
                        continue
        t = f.along_variant("Bookcase1", r["side"])
        if t and f.ok_type(t):
            ha, hp = halves_on(r, (0, 0) + f.half(t))
            if best[1] - best[0] >= 4 * ha + 0.2:
                got = [f.try_put(t, *uv_on(r, hp + 0.18, mid + s * (ha + 0.01)), snug=True, touch=True) for s in (-1, 1)]
                if not all(got): remove(f, [g for g in got if g])


def _near_spot(f, cu, cv, rad=2.2):
    """The spot nearest (cu, cv), within 1.5 units of it, with nothing within `rad`, inside the room; or None."""
    for du, dv in sorted([(a * 0.5, b * 0.5) for a in range(-5, 6) for b in range(-5, 6)], key=lambda d: d[0] ** 2 + d[1] ** 2):
        u, v = cu + du, cv + dv
        if f.g.inside(u, v) and f.g.wall_dist(u, v) > 2.4 and clear_at(f, u, v, rad) and \
                f.g.fits(u, v, 1.0, 1.0, True, False, 0.1): return (u, v)
    return None


def _seat_bare_tables(f):
    """A bedroom table standing with no chair gets two drawn up, else goes (a table in the N corner on its own: round 2)."""
    for o, t, rec in items(f, TABLE):
        if any(max(abs(sr[0] - rec[0]) - sr[2] - rec[2], abs(sr[1] - rec[1]) - sr[3] - rec[3]) < 0.8
               for _, _, sr in items(f, SEAT)): continue
        f.seats_around((rec[0], rec[1]), t, 2, "chair")   # (round 3: the table stays even with no chair: it is a set)


def _front_wall_piece(f, rng, force=False):
    """A bench centred on the longest bare front wall (SE or SW) of a bedroom of 30 tiles or more: those walls stood bare
    (round 2: "the SE/SW walls bare"; the brief: "Front walls: a desk or a small table with its chair; a bench")."""
    if not force and (len(f.room.tiles) < 30 or items(f, r"^(Bench\d|LightBench\d|CushionedBench\d)$")): return
    best = None
    for r in f.g.runs:
        if r["side"] in BACK: continue
        for a0, a1 in free_stretches(f, r):
            a0, a1 = max(a0, r["lo"] + 1.6), min(a1, r["hi"] - 1.6)
            if a1 - a0 > 3.0 and (best is None or a1 - a0 > best[0]): best = (a1 - a0, r, (a0 + a1) / 2)
    if not best: return
    _, r, a = best
    for b in ("Bench1", "Bench2", "LightBench1", "LightBench2"):
        t = f.along_variant(b, r["side"])
        if t and f.ok_type(t):
            hp = halves_on(r, (0, 0) + f.half(t))[1]
            if put(f, t, *uv_on(r, hp + 0.3, a)): return


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
    if os.environ.get("NOX_FINISH_DEBUG"):
        print("replace_bed", f.room.id, t, [(WALL_NAME[r["side"]], round(sum(b - a for a, b in free_stretches(f, r, skip=[rec] + [x[2] for x in near])), 1))
                                           for r in f.g.runs if r["side"] in BACK], len(cands))
    for _, r, tt, a, hp in sorted(cands, key=lambda c: -c[0]):
        remove(f, [o] + [x[0] for x in near])
        u, v = uv_on(r, hp + F.SNUG_GAP.get("bed", 0.28), a)
        o2 = put(f, tt, u, v)
        if o2:
            nb = (o2, tt, f._placed_of[id(o2)])
            f._fin_bed = None
            got = _nightstands(f, nb, (r, a, 0.28), rng, pair_only=True)
            if got: return got
            f._remove(f._fin_bed[0] if f._fin_bed else o2)
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
        # (the bed may stand again as a new piece where it stood: the caller's record of it is stale, so the current one
        # is kept here; round 3 found a bed laid twice over itself when the old record was "removed" again)
        f._fin_bed = (o_bed, tb, f._placed_of[id(o_bed)]) if id(o_bed) in f._placed_of else None
        return None
    # no room for the pair anywhere along the wall: one nightstand, on the side with room
    for s in rng.sample((-1, 1), 2):
        u, v = uv_on(r, NIGHTSTAND_PERP, a + s * (bha + NIGHTSTAND_GAP + nh))
        if put(f, t, u, v): break
    return (o_bed, tb, f._placed_of[id(o_bed)])


def _second_rug(f, rng, bed):
    """A big bedroom's other half takes a rug of its own, centred there (RM-BEDROOM-07: "perhaps another small rug
    added to the northwest volume of the room"), when it is bare."""
    if len(items(f, RUG)) >= 2 or (len(f.room.tiles) < 45 and items(f, RUG) and f.carpet_boxes): return
    u0, u1, v0, v1 = box(f)
    long_u = (u1 - u0) >= (v1 - v0)
    for half in ((0, 0.5), (0.5, 1)):
        if long_u:
            cu, cv = u0 + (u1 - u0) * (half[0] + half[1]) / 2, (v0 + v1) / 2
        else:
            cu, cv = (u0 + u1) / 2, v0 + (v1 - v0) * (half[0] + half[1]) / 2
        if any(math.hypot(rr[0] - cu, rr[1] - cv) < 4 for _, _, rr in items(f, RUG)): continue
        if on_carpet(f, cu, cv, pad=1.8) or not clear_at(f, cu, cv, 1.4): continue
        t = _rug_type(f, rng, avoid=[x for _, x, _ in items(f, RUG)])
        if t and put(f, t, cu, cv, blocking=False): return


def carpet_box(f):
    """(u0, u1, v0, v1) of the room's carpet as laid now (its Rug floor tiles; the furnisher's own boxes go stale when
    the grammar audit lifts a carpet and lays it again), or None."""
    sq = [((x + y) // 2, (x - y) // 2) for (x, y) in f.room.tiles if (f.spec.floor.get((x, y)) or "").startswith("Rug")]
    if len(sq) < 4: return None
    return (min(2 * i + 1 for i, _ in sq), max(2 * i + 3 for i, _ in sq), min(2 * j - 1 for _, j in sq),
            max(2 * j + 1 for _, j in sq))


def on_carpet(f, u, v, pad=0.0):
    """True when the floor at (u, v) (or within `pad` units of it) is a carpet (Rug floor tiles). A room's square
    (i, j) is the tile (i + j, i - j), its centre at uv (2i + 2, 2j)."""
    for du in ((0.0,) if not pad else (-pad, 0.0, pad)):
        for dv in ((0.0,) if not pad else (-pad, 0.0, pad)):
            i, j = round((u + du - 2) / 2), round((v + dv) / 2)
            m = f.spec.floor.get((i + j, i - j)) or ""
            if m.startswith("Rug"): return True
    return False


def _in_corner(f, rec, w, margin=1.6):
    r, a, _ = w
    ha, _ = halves_on(r, rec)
    return min(a - ha - (r["lo"] + 1), (r["hi"] - 1) - (a + ha)) < margin


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
    if not items(f, CHEST):                                  # (the bed's move took it: never a bedroom without its chest)
        f.place_on_wall("storage", at="center", clear=1.0, only=r"^Chest|^DunMirChest") or \
            f.place_on_wall("storage", at="any", clear=0.6, only=r"^Chest|^DunMirChest")


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
    # (lights, and a bed's own nightstands, do not bound the stretch it is centred on)
    lights = {id(rr) for tt, rr in f._typed if re.search(r"Candleabra|Candelabra|^TorchPole|Lantern|^Nightstand", tt)}
    for p in blockers(f, (rec,)):
        if p is rec or id(p) in lights: continue
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


def _rug_type(f, rng, avoid=()):
    types = [t for t in (f.types_of("rug") or {}) if re.match(RUG, t)] or \
        [t for t in ("RedRug1", "RedRug2", "BearskinRug1") if f.ok_type(t)]
    # never the rug the room already has (round 3: "the two rugs are the same piece repeated")
    bad = {rug_design(t) for t in avoid}
    fresh = [t for t in sorted(set(types) | {t for t in RUG_KINDS if f.ok_type(t)}) if rug_design(t) not in bad]
    pool = [t for t in sorted(types) if rug_design(t) not in bad] or fresh
    return rng.choice(pool) if pool else None


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
    if len(row) < 2:                            # no wall holds a row: as it was (the racks and the rest still go up)
        remove(f, row)
        for t, u, v in keep: restore(f, t, u, v)
        row = [o for o, _, _ in items(f, BED)]
    bed_run = run_of(f, f._placed_of[id(row[0])], reach=1.6) if row else None
    skip = [bed_run[0]] if bed_run else []
    n = max(3, min(7, len(f.room.tiles) // 20))
    if not wall_row(f, rng, RACK_KINDS[:3], n, sides=BACK, skip_runs=skip):
        # a small room whose back walls are taken: the racks on any wall with room, two or even one
        wall_row(f, rng, RACK_KINDS[:3], n, sides=tuple(WALL_NAME), skip_runs=skip, min_n=1)
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
    if len(f.room.tiles) >= 110: _barracks_middle(f, rng)
    barrels = _types(f, r"^(Barrel|Barrel2|BarrelWithTools[12])$")
    fill_corners(f, rng, [lambda u, v: knot(f, rng, u, v, barrels, 3),
                          lambda u, v: knot(f, rng, u, v, _types(f, r"^(Crate[12]|Barrel)$"), 2)])
    hang_backs(f, rng, most=2)


def _barracks_middle(f, rng):
    """A big barracks' open middle (round 2: "look again at big barracks, which read open in the middle"): the crew's
    boards in a row through the room's middle along its length, two long tables end on with benches down both sides, and
    a pair of armour stands at the row's ends, mirrored; whatever table stood alone in the middle joins the row."""
    u0, u1, v0, v1 = box(f)
    long_u = (u1 - u0) >= (v1 - v0)
    cu, cv = f.g.centroid
    for o, t, rec in items(f, TABLE):                 # the lone table in the middle goes (the row takes its place)
        if math.hypot(rec[0] - cu, rec[1] - cv) < 3.0:
            remove(f, [x[0] for x in _with_seats(f, rec)] + [o])
    t = next((x for x in (("Table2", "Table4") if long_u else ("Table1", "Table3")) if f.ok_type(x)), None)
    if not t: return
    hu, hv = f.half(t)
    step = 2 * (hu if long_u else hv) + 1.6
    spots = [(cu - step / 2, cv), (cu + step / 2, cv)] if long_u else [(cu, cv - step / 2), (cu, cv + step / 2)]
    got = []
    for u, v in spots:
        if not clear_at(f, u, v, 2.0): continue
        o = force_put(f, t, u, v)
        if not o: continue
        got.append(o)
        if f.seats_around((u, v), t, 2, "bench") < 2:
            f.seats_around((u, v), t, 2, "chair")
    if not got: return
    racks = _types(f, r"^TraderArmorRack[12]$")
    if racks:
        end = step + (hu if long_u else hv) + 1.4
        ends = [(cu - end, cv), (cu + end, cv)] if long_u else [(cu, cv - end), (cu, cv + end)]
        pair = [force_put(f, racks[0], u, v) for u, v in ends]
        if not all(pair): remove(f, [p_ for p_ in pair if p_])


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
    n = max(9, min(16, len(f.room.tiles) // 3))      # (round 2: a full heap, not a handful)
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
    # (round 2, the fullness floor: a bigger pen holds a second heap at its other end, a crude bench on a wall, bones)
    if len(f.room.tiles) >= 36:
        other = next((k for k in order[1:] if (pts[k][0] - hu) ** 2 + (pts[k][1] - hv) ** 2 > 36 and
                      not any(math.hypot(pts[k][0] - r_[0], pts[k][1] - r_[1]) < 2.0 for _, _, r_ in items(f, r"^ObeliskPrimitive$"))), None)
        if other:
            ou, ov = pts[other]
            got = 0
            for k in range(30):
                if got >= n // 2: break
                ang = k * 2.4; rad = 0.25 + 0.3 * math.sqrt(k)
                if put(f, rng.choice(kinds), ou + rad * math.cos(ang), ov + rad * math.sin(ang), blocking=False): got += 1
        centre_on_back(f, rng, "OgreBench", min_len=3.0, sides=tuple(WALL_NAME))
    bones = _types(f, r"^(Skull[1-4]?|ArmBone|LegBone|OgreHutMeat)$")
    for o_, t_, r_ in items(f, r"^Stocks\d$")[:1]:       # bones and a skull before the stocks
        for k in range(3):
            ang = rng.uniform(0, 2 * math.pi)
            if bones: put(f, rng.choice(bones), r_[0] + 1.3 * math.cos(ang), r_[1] + 1.3 * math.sin(ang), blocking=False)
    stores = _types(f, r"^(Barrel|OgreSack[12]|OgreStool[12])$")
    fill_corners(f, rng, [lambda u, v: knot(f, rng, u, v, stores, 2),
                          lambda u, v: knot(f, rng, u, v, bones or stores, 2),
                          lambda u, v: knot(f, rng, u, v, stores, 1)], inset=1.4, rad=1.3)


# ---- cellar (Q1R-13) -----------------------------------------------------------------------------------------------
CASK_CLEAR = 0.8           # units a great cask keeps from every other piece (RM-CELLAR-01: "the gigantic wine barrels are
                           # way too close to each other and to the other barrels"; -08, -09 "need more space")
CASK_DRAWN = (1.8, 1.1)    # half-length and half-depth of a great cask as the game draws it (its footprint is half that)
# each group a row along a wall: the kinds of its pieces in order (one kind never more than three side by side: HB-5)
CELLAR_GROUPS = (("kegs", (r"^Barrel$", r"^Barrel$", r"^Barrel2$", r"^PiledBarrels[1-4]$"), 4),
                 ("steel", (r"^BarrelSteel[12]$", r"^BarrelSteel[12]$", r"^BarrelWithTools[12]$"), 3),
                 ("crates", (r"^(Crate[12]|DarkCrate[12])$", r"^Barrel2?$", r"^Barrel2?$"), 3),
                 ("tools", (r"^BarrelWithTools[12]$", r"^Barrel$", r"^BarrelSteel[12]$"), 3),
                 ("steelcrates", (r"^CrateSteel[1-4]$", r"^BarrelSteel[12]$"), 2))


def _cellar(f, rng):
    """The cellar stocked again in organised groups of several kinds (QA round 1: "Many of these include only barrels.
    Improve the diversity. Add metal barrels and tools. Use crates more often alongside the barrels"; RM-CELLAR-08 "the
    diversity of objects is better ... It just needs to be organized a little bit better. The giant wine barrel needs
    more space"): the great casks centred on a back wall with CASK_CLEAR round them (two, symmetric, in a cellar of 45
    tiles or more), then a row of each kind from a corner along the walls (wooden kegs, metal barrels, crates, barrels of
    tools), each group of one kind, the middle an aisle; what the old heaps held beyond that goes."""
    old = items(f, r"^(Barrel|Barrel2|LargeBarrel[12]|PiledBarrels[1-4]|DarkCrate[12]|Crate[12]|BarrelSteel[12]|"
                   r"BarrelWithTools[12]|CrateSteel[1-4]|WaterBarrel)$")
    keep = [(t, rec[0], rec[1]) for _, t, rec in old]
    remove(f, [o for o, _, _ in old])
    tiles = len(f.room.tiles)
    casks = []
    n_casks = 0 if tiles < 20 else 1 if tiles < 45 else 2
    for _ in range(1):
        if not n_casks: break
        best = None
        for r in f.g.runs:
            if r["side"] not in BACK: continue
            t = "LargeBarrel2" if r["line"] == "/" else "LargeBarrel1"
            if not f.ok_type(t): continue
            for a0, a1 in free_stretches(f, r):
                a0, a1 = max(a0, r["lo"] + 1.5), min(a1, r["hi"] - 1.5)
                if best is None or a1 - a0 > best[0]: best = (a1 - a0, r, t, a0, a1)
        if not best: break
        L, r, t, a0, a1 = best
        ha, hp = halves_on(r, (0, 0) + f.half(t))
        va = CASK_DRAWN[0]                          # its picture is twice its footprint
        spots = [(a0 + a1) / 2] if n_casks == 1 or L < 4 * va + CASK_CLEAR + 1.0 else \
            [(a0 + a1) / 2 - va - CASK_CLEAR / 2, (a0 + a1) / 2 + va + CASK_CLEAR / 2]
        for a in spots:
            o = put(f, t, *uv_on(r, hp + 0.35, a))
            if o: casks.append(f._placed_of[id(o)])
    def cask_ok(t, u, v):
        hu, hv = f.half(t)
        for c in casks:                              # the cask as drawn, its long side along its wall
            cu_, cv_ = (CASK_DRAWN[0], CASK_DRAWN[1]) if c[2] >= c[3] else (CASK_DRAWN[1], CASK_DRAWN[0])
            if max(abs(u - c[0]) - hu - cu_, abs(v - c[1]) - hv - cv_) < CASK_CLEAR: return False
        return True
    # (round 2 of the QA, the coordinator's reading of the pictures: the first pass left cellars emptier than before;
    # "the user didn't want fewer things, they wanted more kinds of thing, laid out in order": Westwood's run caps lifted
    # here as a house rule, every wall stocked about half its length in groups of one kind each, the kinds cycling)
    f.lift_runs = True
    placed = 0
    try:
        placed += cellar_corners(f, rng, cask_ok)
        placed += cellar_walls(f, rng, cask_ok, share=CELLAR_WALL_SHARE)
        if tiles >= 32: placed += cellar_stack(f, rng, cask_ok)
    finally:
        f.lift_runs = False
    if placed + len(casks) < 3:                    # nothing fitted: as it was
        remove(f, [o for o, _, _ in items(f, r"^(LargeBarrel|Barrel|Crate|PiledBarrels|BarrelSteel|BarrelWithTools)")])
        for t, u, v in keep: restore(f, t, u, v)


CELLAR_WALL_SHARE = 0.55   # of each wall's free length stocked (the coordinator: "roughly half the wall length is used")
CELLAR_KINDS = (r"^(Barrel|Barrel2)$", r"^BarrelSteel[12]$", r"^(Crate[12]|DarkCrate[12])$", r"^BarrelWithTools[12]$",
                r"^SackChest(Large|Medium)[12]$", r"^CrateSteel[1-4]$", r"^WaterBarrel$")


def cellar_corners(f, rng, ok):
    """A piled barrel (a stack of kegs) in each bare corner. Returns the pieces."""
    piled = _types(f, r"^PiledBarrels[1-4]$")
    if not piled: return 0
    n = 0
    for name, u, v in free_corners(f, 1.3, 1.2):
        t = rng.choice(piled)
        if ok(t, u, v) and put_corner(f, t, u, v): n += 1
    return n


def cellar_walls(f, rng, ok, share=0.55):
    """Every wall's free stretches stocked from their ends toward the middle, `share` of each, in groups of one kind (two
    or three pieces touching, 0.35 units between groups), the kinds cycling so no two groups beside each other are of
    one kind (a long piece only where it lies along its wall); a spot that takes nothing is stepped over. The back walls
    take a pair of shelves of jars and food in a big cellar. Returns the pieces."""
    kinds = [k for k in (_types(f, rx) for rx in CELLAR_KINDS) if k]
    if not kinds: return 0
    order = list(range(len(kinds))); rng.shuffle(order)
    n, ki = 0, 0
    runs = sorted(f.g.runs, key=lambda r: (r["side"] not in BACK, -(r["hi"] - r["lo"])))
    shelves = _types(f, r"^LogShelvesFull[1-4]$")
    if shelves and len(f.room.tiles) >= 40:      # shelves of jars and food first, on the longest bare back wall
        n += len(line_pair(f, rng, "LogShelvesFull", 2, min_len=3.0))

    def along(t, r):
        h = f.half(t)
        return abs(h[0] - h[1]) < 0.05 or (h[1] >= h[0]) == (r["line"] == "/")
    for r in runs:
        for a0, a1 in free_stretches(f, r):
            a0, a1 = max(a0, r["lo"] + 1.1), min(a1, r["hi"] - 1.1)
            L = a1 - a0
            if L < 1.6: continue
            # (the length stocked is counted, not the distance walked: a stretch's end by a cask or a door is stepped over)
            ends = [(a0, 1, a1, share * L)] if L < 6.0 else [(a0, 1, (a0 + a1) / 2, share * L / 2), (a1, -1, (a0 + a1) / 2, share * L / 2)]
            for start, step, stop, want in ends:
                a, misses, done = start, 0, 0.0
                while (stop - a) * step > 0.5 and done < want - 0.4:
                    kind = [t for t in kinds[order[ki % len(order)]] if along(t, r)]; ki += 1
                    if not kind: misses += 1; continue
                    got = 0
                    for _ in range(rng.choice((2, 3, 3))):
                        t = rng.choice(kind)
                        ha, hp = halves_on(r, (0, 0) + f.half(t))
                        c = a + step * ha
                        if (c + step * ha - stop) * step > 0.1 or not (a0 - 0.05 <= c - ha and c + ha <= a1 + 0.05): break
                        u, v = uv_on(r, hp + 0.25, c)
                        o = f.try_put(t, u, v, snug=True, touch=True) if ok(t, u, v) else None
                        if not o: break
                        n += 1; got += 1; done += 2 * ha
                        a = c + step * (ha + 0.04)
                    if got: misses = 0; a += step * 0.35
                    else:
                        misses += 1; a += step * 0.25
                        if os.environ.get("NOX_FINISH_DEBUG") and kind:
                            t = kind[0]; ha, hp = halves_on(r, (0, 0) + f.half(t)); u, v = uv_on(r, hp + 0.25, a)
                            hu, hv = f.half(t)
                            print("miss", f.room.id, WALL_NAME[r["side"]], round(L, 1), t, round(a, 1), "ok", ok(t, u, v),
                                  "fits", f.g.fits(u, v, hu, hv, True, False, 0.1, True), "in", f.g.inside(u, v),
                                  "wd", round(f.g.wall_dist(u, v), 2), "bbw", f.g.before_back_wall(u, v),
                                  "zone", any(u + hu > z[0] and u - hu < z[1] and v + hv > z[2] and v - hv < z[3] for z in f.g.zones),
                                  "door", round(min([math.hypot(u - du, v - dv) for du, dv in f.g.doors] or [99]), 1),
                                  "near", [(tt, round(rr[0], 1), round(rr[1], 1)) for tt, rr in f._typed
                                           if abs(rr[0] - u) < 1.6 and abs(rr[1] - v) < 1.6 and rr[4]][:3])
    return n


def cellar_stack(f, rng, ok):
    """A stack in a big cellar's middle: four kegs or crates, two by two, touching. Returns the pieces."""
    cu, cv = f.g.centroid
    if os.environ.get("NOX_FINISH_DEBUG"):
        print("stack", f.room.id, round(cu, 1), round(cv, 1), clear_at(f, cu, cv, 2.6),
              [z for z in f.g.zones if z[0] - 1 < cu < z[1] + 1 and z[2] - 1 < cv < z[3] + 1])
    if not clear_at(f, cu, cv, 2.6): return 0
    types = _types(f, r"^(Barrel|Barrel2|BarrelSteel[12])$")
    if not types: return 0
    t = rng.choice(types)
    h = f.half(t)[0] + 0.09                     # (0.18 apart: the fit keeps 0.15 between pieces)
    got = [force_put(f, t, cu + a * h, cv + b * h) for a in (-1, 1) for b in (-1, 1)]
    if sum(1 for g in got if g) < 4:
        remove(f, [g for g in got if g]); return 0
    return 4


def row_from_corner(f, rng, types, n, ok=None, avoid=(), sides=None):
    """A row of up to `n` pieces of `types` side by side against a wall, from the end of a free stretch at a room corner
    (the corner farthest from the doors first), touching, mixed within the kind. Returns the pieces."""
    cands = []
    doors = f.g.doors or [f.g.centroid]
    for r in f.g.runs:
        if sides and r["side"] not in sides: continue
        for a0, a1 in free_stretches(f, r):
            for end, a in ((0, a0), (1, a1)):
                at_corner = (a - (r["lo"] + 1.0)) < 0.6 if end == 0 else ((r["hi"] - 1.0) - a) < 0.6
                if a1 - a0 < 2.0: continue
                u, v = uv_on(r, 1.0, a)
                if any(math.hypot(u - x[0], v - x[1]) < 2.2 for x in avoid): continue
                far = min(math.hypot(u - du, v - dv) for du, dv in doors)
                cands.append((min(far, 8) + (4 if at_corner else 0) + (2.5 if r["side"] in BACK else 0) +
                              rng.uniform(0, 1), r, end, a0, a1))
    for _, r, end, a0, a1 in sorted(cands, key=lambda c: -c[0]):
        got = []
        a = a0 + 0.15 if end == 0 else a1 - 0.15
        step = 1 if end == 0 else -1
        for k in range(n):
            pool = types[k % len(types)] if types and isinstance(types[0], (list, tuple)) else types
            t0 = rng.choice(pool)
            t = t0
            h = f.half(t0)
            if abs(h[0] - h[1]) > 0.05:                 # a long piece lies along its wall
                t = next((x for x in pool if (f.half(x)[1] >= f.half(x)[0]) == (r["line"] == "/")), t0)
            ha, hp = halves_on(r, (0, 0) + f.half(t))
            c = a + step * ha
            if not (a0 - 0.05 <= c - ha and c + ha <= a1 + 0.05): break
            u, v = uv_on(r, hp + 0.25, c)
            if ok and not ok(t, u, v): break
            o = f.try_put(t, u, v, snug=True, touch=True)
            if not o:
                if os.environ.get("NOX_FINISH_DEBUG"):
                    hu, hv = f.half(t)
                    print("row stop", t, len(got), f.g.fits(u, v, hu, hv, True, False, 0.1, True), dict(f.kb_refused))
                break
            got.append(o)
            a = c + step * (ha + 0.05)
        if len(got) >= min(2, n): return got
        remove(f, got)
    return []


# ---- armoury / gear store (Q1R-1, Q1R-2) ----------------------------------------------------------------------------
def _gear_store(f, rng):
    """The quartermaster's counter is the recipe's; here the walls: a row of racks of arms and armour along each back
    wall with room for it, a second along a front wall in a larger room, arms hung on the bare back wall, stock in the
    bare corners, a bench by the counter's wall (QA round 1: "Larger rooms need to have things like weapon racks along
    their walls"; RM-ARMOURY-03, -07, -08 "too empty", -06 "more decorations on the walls")."""
    tiles = len(f.room.tiles)
    n = max(2, min(6, tiles // 18))
    wall_row(f, rng, RACK_KINDS, n, sides=BACK)
    if tiles >= 60: wall_row(f, rng, RACK_KINDS, n, sides=BACK)
    if tiles >= 90: wall_row(f, rng, RACK_KINDS, n, sides=tuple(WALL_NAME))
    hang_backs(f, rng, most=2 + tiles // 40, types={t: 1 for t in _types(f, ARMS_HUNG)})
    barrels = _types(f, r"^(Barrel|BarrelSteel[12]|BarrelWithTools[12])$")
    crates = _types(f, r"^(Crate[12]|CrateSteel[1-4])$")
    fill_corners(f, rng, [lambda u, v: knot(f, rng, u, v, barrels, 3),
                          lambda u, v: knot(f, rng, u, v, crates + barrels, 2)])
    # (round 2: kinds kept: a chest of arms centred on a back wall, a crate and a barrel by the counter's front wall)
    if not items(f, CHEST): centre_on_back(f, rng, "Chest", min_len=2.4)
    if crates:
        row_from_corner(f, rng, [crates, barrels or crates], 2, sides=tuple(s_ for s_ in WALL_NAME if s_ not in BACK))


# ---- great hall (Q1R-15..18) ---------------------------------------------------------------------------------------
BAND = ("RoughCobble", "RedBrick", "CobbleStone")     # the band round a great hall (RM-GREATHALL-07's brick and cobble)
BAND_RATE = 0.75


def _with_seats(f, rec, reach=0.9):
    return [x for x in items(f, SEAT) if max(abs(x[2][0] - rec[0]) - x[2][2] - rec[2],
                                             abs(x[2][1] - rec[1]) - x[2][3] - rec[3]) < reach]


def _great_hall(f, rng):
    """The tables kept to their carpet and centred on it, a stray table or bench taken up, the tables clear of the
    hearth; then pieces of more kinds, placed in pairs and centred (statues flanking the hearth, suits of armour on the
    other back wall, plants in the side corners, a chest), the back walls hung, and a band of brick or cobble round the
    whole room (QA round 1: "The layouts, tables, and chairs are generally pretty good, but the spaces are universally too
    empty. We need much more diversity of objects"; RM-GREATHALL-01 "the six tables on the carpet ... need to be centered
    more. The seventh table should be removed"; -02 "fix the table randomly placed in the south corner"; -04 "the table
    next to the hearth is too close to it"; -07 "build this perimeter around the entire room ... more objects, especially
    along the northeast wall")."""
    fires = items(f, r"Fireplace")
    tables = items(f, TABLE)
    boxes = list(f.carpet_boxes)
    def on_carpet_box(rec):
        return any(b[0] <= rec[0] <= b[1] and b[2] <= rec[1] <= b[3] for b in boxes)
    # strays: a table off the carpet when the others are on it, a table crowding the hearth
    on = [x for x in tables if on_carpet_box(x[2])]
    moved = []
    for o, t, rec in tables:
        # (a wall hearth's front: RM-GREATHALL-04; a free hearth in the middle keeps its own ring of tables)
        near_fire = any(max(abs(rec[0] - fr[0]) - rec[2] - fr[2], abs(rec[1] - fr[1]) - rec[3] - fr[3]) <
                        (2.2 if run_of(f, fr, reach=1.0) else 0.9) for _, _, fr in fires)
        if near_fire or (boxes and len(on) >= 2 and not on_carpet_box(rec)):
            remove(f, [x[0] for x in _with_seats(f, rec)] + [o])
            moved.append(t)
    # each table taken up is set again with two seats in the open floor nearest the room's middle (round 2: the hall
    # holds as much as it did, only placed better)
    cu0, cv0 = f.g.centroid
    for t in moved:
        for rad in (4.0, 5.5, 7.0, 2.5):
            done = False
            for k in range(12):
                ang = k * math.pi / 6
                spot = _near_spot(f, cu0 + rad * math.cos(ang), cv0 + rad * math.sin(ang), rad=2.0)
                if spot and not any(max(abs(spot[0] - fr[0]) - fr[2], abs(spot[1] - fr[1]) - fr[3]) < 3.4 for _, _, fr in fires)                         and table_set(f, *spot, types=[t, "RoundTable1", "SquareTable1"]):
                    done = True; break
            if done: break
    # a big hall's open middle (round 2, the fullness floor: the 380-400 tile halls read empty in the middle): four
    # table sets mirrored about the room's centre, each on the open floor, seated two to four
    u0, u1, v0, v1 = box(f)
    if len(f.room.tiles) >= 220:
        cu0, cv0 = f.g.centroid
        su, sv = max(4.0, (u1 - u0) / 4.5), max(4.0, (v1 - v0) / 4.5)
        ts = [t for t in ("RoundTable1", "SquareTable1", "RoundTable2") if f.ok_type(t)]
        for du, dv in ((su, sv), (-su, -sv), (su, -sv), (-su, sv)):
            if not clear_at(f, cu0 + du, cv0 + dv, 2.2) or not f.g.inside(cu0 + du, cv0 + dv): continue
            if any(max(abs(cu0 + du - fr[0]) - fr[2], abs(cv0 + dv - fr[1]) - fr[3]) < 3.4 for _, _, fr in fires): continue
            got = table_set(f, cu0 + du, cv0 + dv, types=ts[:1])
            if got: f.seats_around((cu0 + du, cv0 + dv), got[0]["type"], 2, "chair")
    # a bench standing alone: no table at it, not against a wall
    for o, t, rec in items(f, r"^(Bench\d|CushionedBench\d)$"):
        if any(max(abs(rec[0] - tr[0]) - rec[2] - tr[2], abs(rec[1] - tr[1]) - rec[3] - tr[3]) < 0.9
               for _, _, tr in items(f, TABLE)): continue
        if f.g.wall_dist(rec[0], rec[1]) - max(rec[2], rec[3]) < 0.8: continue
        f._remove(o)
    # the boards centred on their carpet
    if boxes:
        b = max(boxes, key=lambda b: (b[1] - b[0]) * (b[3] - b[2]))
        grp = [x for x in items(f, TABLE) if b[0] <= x[2][0] <= b[1] and b[2] <= x[2][1] <= b[3]]
        allp = {id(x[0]): x for g in grp for x in [g] + _with_seats(f, g[2])}
        if allp:
            recs = [x[2] for x in allp.values()]
            gu = (min(r_[0] - r_[2] for r_ in recs) + max(r_[0] + r_[2] for r_ in recs)) / 2
            gv = (min(r_[1] - r_[3] for r_ in recs) + max(r_[1] + r_[3] for r_ in recs)) / 2
            du, dv = (b[0] + b[1]) / 2 - gu, (b[2] + b[3]) / 2 - gv
            if math.hypot(du, dv) > 0.3:
                was = [(x[1], x[2][0], x[2][1]) for x in allp.values()]
                remove(f, [x[0] for x in allp.values()])
                order = sorted(was, key=lambda w: F._family_of(w[0]) != "table")
                got = [put(f, t, u + du, v + dv) for t, u, v in order]
                if not all(got):
                    remove(f, [g for g in got if g])
                    for t, u, v in order: restore(f, t, u, v)
    # pieces of more kinds, in pairs
    for o, t, fr in fires[:1]:
        w = run_of(f, fr, reach=1.0)
        if not w: continue
        r, a, _ = w
        ha, _ = halves_on(r, fr)
        sts = _types(f, r"^Statue[12][a-h]$") or _types(f, r"^Statue")
        if sts:
            st = rng.choice(sorted({re.sub(r"[a-h]$", "", x) for x in sts}))
            pair = []
            for s in (-1, 1):
                tt = next((x for x in sts if x.startswith(st)), sts[0])
                o2 = put(f, tt, *uv_on(r, 0.9, a + s * (ha + 1.9)))
                if o2: pair.append(o2)
            if len(pair) < 2: remove(f, pair)
    # a second pair of statues on the other back wall of a big hall (suits of armour and hung arms read as an
    # armoury: the room score's reads-as)
    sts = _types(f, r"^Statue[12][a-h]$")
    if sts and len(f.room.tiles) >= 120:
        fire_runs = [run_of(f, fr, reach=1.0) for _, _, fr in fires]
        skip = [w[0] for w in fire_runs if w]
        pair_on_wall(f, rng, sts[0], sides=BACK, skip_runs=skip)
    plants = _types(f, r"^(Plant1|Plant3|Plant4|Plant5)$")
    if plants:
        p = rng.choice(plants)
        pts = corner_points(f, 1.2)
        got = [put_corner(f, p, *pts[k]) for k in ("W", "E") if f.g.inside(*pts[k])]
        if len([g for g in got if g]) < 2: remove(f, [g for g in got if g])
    if not items(f, CHEST): centre_on_back(f, rng, "Chest", min_len=3.0)
    banners = {t: 1 for t in f.things if re.match(r"^(Red|Blue|Green|White)Tapestry\d$|^WallTrophy", t) and f.ok_type(t)}
    theme = {t: w for t, w in (getattr(f, "_decor_types", None) or {}).items() if not re.match(ARMS_HUNG, t)}
    hang_backs(f, rng, most=6, types=theme or banners)
    hang_backs(f, rng, most=3, types=banners)
    f.face_statues()
    _south_corner_bench(f, rng)
    if rng.random() < BAND_RATE: lay_band(f, rng)


def pair_on_wall(f, rng, t, sides=BACK, skip_runs=()):
    """Two of `t` against the longest free stretch of a wall, symmetric about its middle. Returns them."""
    best = None
    for r in f.g.runs:
        if r["side"] not in sides or any(r is s for s in skip_runs): continue
        for a0, a1 in free_stretches(f, r):
            a0, a1 = max(a0, r["lo"] + 1.5), min(a1, r["hi"] - 1.5)
            if a1 - a0 > 4.0 and (best is None or a1 - a0 > best[0]): best = (a1 - a0, r, a0, a1)
    if not best: return []
    L, r, a0, a1 = best
    tt = f.side_variant(t, r, F._family_of(t)) or t
    hp = halves_on(r, (0, 0) + f.half(tt))[1]
    mid, off = (a0 + a1) / 2, min(L / 4, 3.0)
    got = [put(f, tt, *uv_on(r, hp + 0.3, mid + s * off)) for s in (-1, 1)]
    if not all(got): remove(f, [g for g in got if g]); return []
    return got


def _south_corner_bench(f, rng):
    """A bench along each front wall at the S corner, where those who wait sit (HB-2), when the corner is bare."""
    u0, u1, v0, v1 = box(f)
    if not clear_at(f, u1 - 2.4, v0 + 2.4, 2.0): return
    for r in f.g.runs:
        if r["side"] in BACK: continue
        bt = f.along_variant("Bench1", r["side"]) or f.along_variant("Bench2", r["side"])
        if not bt or not f.ok_type(bt): continue
        ha, hp = halves_on(r, (0, 0) + f.half(bt))
        end = r["hi"] - 1.0 - 1.4 - ha if r["line"] == "/" else r["lo"] + 1.0 + 1.4 + ha
        # (the S corner is the high-u end of a SW wall run and the low-v end of a SE wall run)
        end = (r["lo"] + 1.0 + 1.4 + ha) if r["line"] == "/" else (r["hi"] - 1.0 - 1.4 - ha)
        put(f, bt, *uv_on(r, hp + 0.3, end))


def lay_band(f, rng):
    """A band of brick or cobble one square wide round the whole room, unbroken but for the doorways' own squares
    (RM-GREATHALL-07: "I really like the brick cobblestone tiling around the outside of this room. It is interrupted on
    the northeast wall ... build this perimeter around the entire room"), bordered where it meets the floor."""
    from kit import shells as SH
    room, spec = f.room, f.spec
    main = room.floor
    sq = {((x + y) // 2, (x - y) // 2) for (x, y) in room.tiles}
    ring = {s for s in sq if any((s[0] + a, s[1] + b) not in sq for a in (-1, 0, 1) for b in (-1, 0, 1))}
    gaps = [d.gap for d in room.doors]
    tile = lambda s: (s[0] + s[1], s[0] - s[1])
    tiles = set()
    for s in ring:
        t = tile(s)
        if any(max(abs(t[0] - g[0]), abs(t[1] - g[1])) <= 1 for g in gaps): continue
        if (spec.floor.get(t) or main).startswith("Rug") or t in spec.local_blend: continue
        tiles.add(t)
    if len(tiles) < 0.6 * len(ring): return set()
    mats = [m for m in BAND if m != main and frozenset((m, main)) not in SH._never()]
    if not mats: return set()
    for t in tiles: spec.tile(*t, main)                 # (a band laid before furnishing goes under this one)
    return SH.lay_patch(spec, room, tiles, rng.choice(mats))


# ---- conservatory (Q1R-14), composed whole --------------------------------------------------------------------------
GARDEN_GROUND = "GrassNorm"
GARDEN_BED = "DirtDark2"
GARDEN_PAVING = ("CobbleStone", "RoughCobble")
CROPS = ("GardenCorn", "GardenTomatos", "GardenCabbage")
CONS_PLANTS = r"^(Plant[1-5]|Plant2Flowered|PlantFern[1-4])$"
APPLE_TREES = ("TreeApple",)


def force_put(f, t, u, v, blocking=True):
    """A piece placed where its footprint fits (the doors' ways, the room's walls and the pieces already there), the
    object knowledge base's caps aside (a second fountain set as a symmetric pair)."""
    if not f.ok_type(t): return None
    hu, hv = f.half(t)
    if not f.g.fits(u, v, hu, hv, blocking, False, 0.1): return None
    return f.put(t, u, v, blocking)


def _conservatory(f, rng):
    """A garden indoors (QA round 1: "Make the floors grass/dirt/outdoor. Occasionally include small patches of
    cobblestone or tile floor in sections with proper borders. Make sure plants are situated on dirt or grass ...
    Limit these rooms to a maximum of one well. When there are multiple fountains, organize them so that they have a
    balanced, symmetrical layout ... Add some different trees, especially apple trees with apples on the ground ...
    occasional rows of crops ... barrels of tools ... a few crates and barrels rarely. Make sure benches are against the
    walls"). The floor grass; beds of dirt along the NE and NW walls planted in clumps; the fountain in the middle (two,
    mirrored along the room's length, in a big one; or the one well), now and then on a bordered square of paving;
    benches against the long walls facing each fountain; apple trees in the side corners on their own dirt, apples
    fallen round them; in a larger room two beds of crops mirrored at its ends; a barrel of tools by the beds."""
    from kit import shells as SH
    spec, room = f.spec, f.room
    tiles_all = sorted(room.tiles)
    sq = {((x + y) // 2, (x - y) // 2) for (x, y) in tiles_all}
    tile = lambda s: (s[0] + s[1], s[0] - s[1])
    gaps = [d.gap for d in room.doors]
    near_door = lambda t, k=3: any(max(abs(t[0] - g[0]), abs(t[1] - g[1])) <= k for g in gaps)
    # the ground
    for t in tiles_all:
        spec.tile(*t, GARDEN_GROUND)
        if hasattr(spec, "indoor"): spec.indoor[t] = GARDEN_GROUND
    room.floor = GARDEN_GROUND
    u0, u1, v0, v1 = box(f)
    long_u = (u1 - u0) >= (v1 - v0)
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    L = (u1 - u0) if long_u else (v1 - v0)
    n_tiles = len(tiles_all)
    # the fountains (or the one well), symmetric
    two = n_tiles >= 140 and rng.random() < 0.6
    spots = [(cu - L / 4, cv), (cu + L / 4, cv)] if two and long_u else \
        [(cu, cv - L / 4), (cu, cv + L / 4)] if two else [(cu, cv)]
    feat = "WishingWell" if (not two and rng.random() < 0.25 and f.ok_type("WishingWell")) else "Fountain"
    placed_f = [force_put(f, feat, u, v) for u, v in spots]
    if not all(placed_f):
        remove(f, [o for o in placed_f if o])
        spots = [(cu, cv)]
        placed_f = [force_put(f, feat, cu, cv)]
        for alt in ("WishingWell", "Well"):              # a narrow room: the well, which takes less floor
            if placed_f[0]: break
            placed_f = [force_put(f, alt, cu, cv)]
    feats = [f._placed_of[id(o)] for o in placed_f if o]
    pave = rng.random() < 0.4
    for rec in feats if pave else ():                  # a square of paving under it, bordered
        i, j = round((rec[0] - 2) / 2), round(rec[1] / 2)
        ps = {(i + a, j + b) for a in (-1, 0, 1) for b in (-1, 0, 1)} & sq
        ts = {tile(s) for s in ps if not near_door(tile(s))}
        SH.lay_patch(spec, room, ts, rng.choice(GARDEN_PAVING), edge="BlendEdge")
    if not items(f, r"^(Bench\d|LightBench\d)$"):           # a bench centred on whatever wall has room
        centre_on_back(f, rng, "Bench", min_len=3.0, sides=tuple(WALL_NAME))
    # apple trees in the side corners, on their own dirt, apples fallen round them
    trees = [t for t in APPLE_TREES if f.ok_type(t)]
    if trees and n_tiles >= 60:
        pts = corner_points(f, 2.6)
        side = ("W", "E")
        got = []
        for k in side:
            tu, tv = pts[k]
            if not f.g.inside(tu, tv) or not _no_door(f, tu, tv, 3.5): continue
            o = force_put(f, trees[0], tu, tv)
            if not o: continue
            got.append((tu, tv))
            i, j = round((tu - 2) / 2), round(tv / 2)
            ts = {tile((i + a, j + b)) for a in (0, -1, 1) for b in (0, -1, 1) if (i + a, j + b) in sq and abs(a) + abs(b) <= 1}
            SH.lay_patch(spec, room, {t for t in ts if not near_door(t)}, GARDEN_BED, edge="BlendEdge")
            for n in range(rng.choice((2, 3))):
                ang = rng.uniform(0, 2 * math.pi); rad = rng.uniform(1.3, 1.8)
                put(f, "RedApple", tu + rad * math.cos(ang), tv + rad * math.sin(ang), blocking=False)
    # beds of dirt along the back walls, planted in clumps
    beds = set()
    for s in sq:
        ne = (s[0], s[1] + 1) not in sq
        nw = (s[0] - 1, s[1]) not in sq
        front = (s[0], s[1] - 1) not in sq or (s[0] + 1, s[1]) not in sq
        if (ne or nw or (front and len(tiles_all) < 80)) and not near_door(tile(s)): beds.add(s)
    plants = _types(f, CONS_PLANTS) or ["Plant1"]
    for s in sorted(beds):
        spec.tile(*tile(s), GARDEN_BED)
    SH.lay_patch(spec, room, {tile(s) for s in beds}, GARDEN_BED, edge="BlendEdge")
    # the plants in clumps along the beds, a step off the wall, gaps between the clumps
    pblock = F._family_of(plants[0]) in F._blocking()
    for r in f.g.runs:
        # (a small conservatory plants its front walls' ends as well: round 2's fullness floor)
        if r["side"] not in BACK and n_tiles >= 80: continue
        a = r["lo"] + 1.0 + 1.2
        while a < r["hi"] - 1.0 - 1.0:
            uu, vv = uv_on(r, 1.0, a)
            if _no_door(f, uu, vv, 3.2):
                for _ in range(rng.choice((2, 3, 3))):
                    force_put(f, rng.choice(plants), *uv_on(r, rng.uniform(0.7, 1.4), a + rng.uniform(-0.5, 0.5)),
                              blocking=pblock)
            a += rng.uniform(2.0, 2.6) if n_tiles >= 80 else rng.uniform(1.5, 1.9)
    # benches against the long walls, facing each fountain
    for (fu, fv) in spots:
        for r in f.g.runs:
            if r["line"] != ("\\" if long_u else "/"): continue
            a = fu if long_u else fv
            if not r["lo"] + 1.5 <= a <= r["hi"] - 1.5: continue
            bt = f.along_variant("Bench1", r["side"]) or f.along_variant("Bench2", r["side"])
            if not bt: continue
            hp = halves_on(r, (0, 0) + f.half(bt))[1]
            d = hp + 0.3 + (1.9 if r["side"] in BACK else 0.0)      # (before the bed of dirt on a back wall)
            put(f, bt, *uv_on(r, d, a))
    # two beds of crops mirrored at the room's ends (a larger room with one fountain)
    if not two and n_tiles >= 90:
        for sgn in (-1, 1):
            if long_u:
                ci = round(((cu + sgn * L * 0.32) - 2) / 2)
                js = sorted(j for (i, j) in sq if i == ci)
                if not js: continue
                rows = [(ci + d, js[0] + 2, js[-1] - 2) for d in (-1, 1)]
            else:
                cj = round((cv + sgn * L * 0.32) / 2)
                is_ = sorted(i for (i, j) in sq if j == cj)
                if not is_: continue
                rows = [(cj + d, is_[0] + 2, is_[-1] - 2) for d in (-1, 1)]
            crop = rng.choice(CROPS)
            for c, lo, hi in rows:
                if hi - lo < 2: continue
                row_sq = [(c, x) if long_u else (x, c) for x in range(lo, hi + 1)]
                row_sq = [s for s in row_sq if s in sq and not near_door(tile(s)) and
                          clear_at(f, 2 * s[0] + 2, 2 * s[1], 0.6)]
                if len(row_sq) < 3: continue
                SH.lay_patch(spec, room, {tile(s) for s in row_sq}, GARDEN_BED, edge="BlendEdge")
                for s in row_sq:
                    bu, bv = 2 * s[0] + 2, 2 * s[1]
                    for off in (-0.5, 0.5):
                        pu, pv = (bu, bv + off) if long_u else (bu + off, bv)
                        put(f, crop, pu, pv, blocking=False)
    # four clumps of plants on dirt at each fountain's diagonals, mirrored (round 2: the fullness floor, in order)
    if n_tiles >= 90 or len(spots) > 1:
        for (fu, fv) in spots:
            for du, dv in ((3.6, 3.6), (3.6, -3.6), (-3.6, 3.6), (-3.6, -3.6)):
                pu, pv = fu + du, fv + dv
                if not f.g.inside(pu, pv) or not clear_at(f, pu, pv, 0.9) or not _no_door(f, pu, pv, 3.0): continue
                i, j = round((pu - 2) / 2), round(pv / 2)
                if (i, j) in sq and not near_door(tile((i, j))):
                    SH.lay_patch(spec, room, {tile((i, j))}, GARDEN_BED, edge="BlendEdge")
                for _ in range(3):
                    force_put(f, rng.choice(plants), pu + rng.uniform(-0.5, 0.5), pv + rng.uniform(-0.5, 0.5),
                              blocking=pblock)
    # a pair of statues flanking the (first) fountain along the room's length, facing it (round 2: kinds kept)
    sts = _types(f, r"^Statue2[aceg]$")
    if sts and spots:
        fu, fv = spots[0]
        off = 3.4
        pair = [force_put(f, sts[0], fu + off, fv) if not long_u else force_put(f, sts[0], fu, fv + off),
                force_put(f, sts[0], fu - off, fv) if not long_u else force_put(f, sts[0], fu, fv - off)]
        if not all(pair): remove(f, [p_ for p_ in pair if p_])
        else: f.face_statues()
    # a barrel of tools by the beds, now and then a crate or a barrel
    tools = _types(f, r"^BarrelWithTools[12]$")
    extra = _types(f, r"^(Barrel|Crate1|Crate2|WaterBarrel)$")
    fill_corners(f, rng, [lambda u, v: knot(f, rng, u, v, tools, 1)] +
                 ([lambda u, v: knot(f, rng, u, v, extra, 1)] if rng.random() < 0.35 else []), inset=1.3, rad=1.2)


# ---- dispatch ------------------------------------------------------------------------------------------------------
PASSES = {"bedroom": _bedroom, "barracks": _barracks, "ogre_den": _ogre_den, "cell": _cell, "ogre_pen": _ogre_pen,
          "cellar": _cellar, "gear_store": _gear_store, "great_hall": _great_hall}
COMPOSERS = {"conservatory": _conservatory}


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
