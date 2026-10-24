"""TrapDemo dressing: the expedition's camp at a mission's way in, lived in; the passages' mouths kept clear of the
dressing; free spots for quest items and a sparse room's extra pieces.

A camp is lived in (the checker's exterior.camp_bare, kit/camps.py Q1K-3: 16 pieces of 8 kinds at the least: beds,
barrels, crates of apples, sacks, seats at the fire, arms). Mission.dress lays the hearth, a tent, two stools, three
stores and a chest; camp() adds the rest in zones round the fire, by the camera bias (rules: beds and racks on the
NE and NW walls the camera sees, loose stores toward the S and W corners), never in a passage's mouth:

- the sleeping row: bedrolls in pairs along the NE wall, foot to the fire, and a pair on the NW wall;
- the hearth: a third seat;
- the store: a tidy group up the SE wall and along the SW wall from the S corner (barrels, sacks, a crate
  of apples, a water barrel);
- the arms: a pole-arm rack and an armour rack on the NW wall by the W corner;
- a table with two stools on the floor toward the S corner.

    from kit.trapdemo_dress import camp, clear_mouths, start_spot
    M.layout(); n0 = len(M.m.d["objects"]); M.dress()
    clear_mouths(M, M.m.d["objects"][n0:])       # nothing of the dressing in a passage's mouth
    camp(M, "camp")
    M.start_at("camp", *start_spot(M, "camp"))
    M.item("vault", "BlueOrb", *free_spot(M, "vault", 6, 5))   # a quest item off the furniture
    extra(M, "ossuary", [("LOTDTombstoneSkulls1", 3, 10.5), ...])   # more for a sparse room

Room coordinates as Mission.at: a along i from the NW wall (a = w the SE wall), b along j from the SW wall (b = h
the NE wall).
"""
import math
import re

KEEP = re.compile(r"^(ColorLight|Amb|PlayerStart)")      # never removed from a mouth (no body to block a way)


def mouths(M, rid, depth=2.6, margin=0.6):
    """[(a0, a1, b0, b1)] boxes in room `rid`'s coordinates before each passage mouth: the opening's width with
    `margin` either side, `depth` squares into the room."""
    w, h = M.rooms[rid]["size"]
    out = []
    for L in M.links:
        p = L.get("part")
        if p is None: continue
        if rid == L["a"]: s = 0.0
        elif rid == L["b"]: s = p.length
        else: continue
        (a0, b0), (a1, b1) = (M.room_ab(rid, *p.at(s, t)) for t in (0.0, p.width))
        if abs(a0 - a1) < 0.5:                       # on the NW (a = 0) or SE (a = w) wall
            lo, hi = sorted((b0, b1))
            aa = (-1.0, depth) if (a0 + a1) / 2 < w / 2 else (w - depth, w + 1.0)
            out.append((aa[0], aa[1], lo - margin, hi + margin))
        else:                                        # on the SW (b = 0) or NE (b = h) wall
            lo, hi = sorted((a0, a1))
            bb = (-1.0, depth) if (b0 + b1) / 2 < h / 2 else (h - depth, h + 1.0)
            out.append((lo - margin, hi + margin, bb[0], bb[1]))
    return out


def in_mouth(M, rid, a, b, pad=0.0, **kw):
    return any(a0 - pad <= a <= a1 + pad and b0 - pad <= b <= b1 + pad for a0, a1, b0, b1 in mouths(M, rid, **kw))


def room_of(M, x, y, slack=0.3):
    """(rid, a, b) of the room a world point stands in, or None."""
    for rid, R in M.rooms.items():
        w, h = R["size"]
        a, b = M.room_ab(rid, x, y)
        if -slack <= a <= w + slack and -slack <= b <= h + slack:
            return rid, a, b
    return None


def clear_mouths(M, objs, **kw):
    """Take out of the map every piece of `objs` (the dressing) that stands in a passage's mouth. Returns the types
    taken out."""
    drop, gone = set(), []
    for o in objs:
        if KEEP.match(o.get("type", "")): continue
        r = room_of(M, o["x"], o["y"])
        if r and in_mouth(M, r[0], r[1], r[2], **kw):
            drop.add(id(o)); gone.append(o["type"])
    if drop:
        M.m.d["objects"] = [o for o in M.m.d["objects"] if id(o) not in drop]
    return gone


def put(M, rid, t, a, b, gap=1.0, placed=None, **kw):
    """A piece at room point (a, b) unless it is in a mouth, too near a doorway's middle or within `gap` squares of
    a piece already placed in the room (`placed`: [(a, b)])."""
    if in_mouth(M, rid, a, b, pad=0.3): return None
    if placed is not None and any(math.hypot(a - pa, b - pb) < gap for pa, pb in placed): return None
    o = M.put(rid, t, a, b, clear=2.4, **kw)
    if o is not None and placed is not None: placed.append((a, b))
    return o


def _taken(M, rid):
    """Room points of the pieces already in room `rid` (the dressing Mission.dress laid)."""
    out = []
    for o in M.m.d["objects"]:
        if KEEP.match(o.get("type", "")): continue
        r = room_of(M, o["x"], o["y"], slack=0.0)
        if r and r[0] == rid: out.append((r[1], r[2]))
    return out


def camp(M, rid, arms=True):
    """The camp's lived-in pieces round the hearth Mission.dress laid at the middle of room `rid`."""
    w, h = M.rooms[rid]["size"]
    placed = _taken(M, rid)
    n = 0

    def P(t, a, b, gap=1.0, **kw):
        nonlocal n
        if put(M, rid, t, a, b, gap=gap, placed=placed, **kw) is not None: n += 1

    cx, cy = w / 2, h / 2

    def fits(spots, gap):
        return all(not in_mouth(M, rid, a, b, pad=0.3) and M.free(rid, a, b, 2.4) and 0.7 <= a <= w - 0.7 and
                   0.7 <= b <= h - 0.7 and not any(math.hypot(a - pa, b - pb) < gap for pa, pb in placed)
                   for a, b in spots)

    def pairs(t, spot, lo, hi, most=2, gap=1.3):
        """Up to `most` pairs of bedrolls side by side along a wall, `spot(s)` the room point s along it, searched
        from lo to hi (a lone bedroll reads as strewn: the checker's exterior.bedroll)."""
        nonlocal n
        s_, k = lo, 0
        while s_ <= hi and k < most:
            spots = [spot(s_), spot(s_ + 1.9)]
            if fits(spots, gap):
                for a, b in spots: P(t, a, b, gap=0.5)
                k += 1
                s_ += 4.2
            else:
                s_ += 0.2
    def along(t, spot, lo, hi, gap=1.2):
        """One piece at the first room point spot(s), s from lo to hi, that fits."""
        nonlocal n
        s_ = lo
        while s_ <= hi:
            if fits([spot(s_)], gap):
                P(t, *spot(s_), gap=0.1)
                return s_
            s_ += 0.2
        return None
    # the arms: racks on the NW wall (a = 0) by the W corner
    if arms:
        s1 = along("TraderPoleArm1", lambda s_: (0.9, s_), 2.4, 4.5)
        if s1 is not None: along("OutdoorTraderArmorRack1", lambda s_: (0.9, s_), s1 + 1.4, s1 + 3.2)
    # the sleeping row: bedrolls in pairs along the NE wall (b = h), foot to the fire (-j: Cot2), then the NW wall
    # (+i: Cot1)
    pairs("Cot2", lambda s_: (s_, h - 1.25), 3.4, w - 4.0)
    pairs("Cot1", lambda s_: (1.25, h - s_), 3.6, h - 3.0, most=1)
    # the hearth: a third seat
    P("UrchinStool1", cx + 0.2, cy + 1.7, gap=0.9)
    # the store: Mission.dress's three stores at the S corner laid again apart (a large crate keeps 48 px clear: the
    # checker's exterior.crate_clear), then a tidy group up the SE wall (a = w) and along the SW wall (b = 0)
    stores = set(M.decor["store"][:3])
    old = [o for o in M.m.d["objects"] if o.get("type") in stores and (room_of(M, o["x"], o["y"], 0.0) or ("",))[0] == rid
           and M.room_ab(rid, o["x"], o["y"])[0] > w - 2.0]
    if old:
        M.m.d["objects"] = [o for o in M.m.d["objects"] if all(o is not p_ for p_ in old)]
        placed[:] = _taken(M, rid)
        for k, o in enumerate(old):
            P(o["type"], w - 1.35, 1.4 + 1.65 * k, gap=1.55)
    for k, t in enumerate(("SackChestLarge1", "TraderAppleCrate", "SackChestMedium1", "WaterBarrel")):
        P(t, w - 1.1, 1.4 + 1.65 * len(old) + 0.2 + 1.05 * k, gap=0.9)
    for k, t in enumerate(("Barrel2", "SackChestLarge2", "Barrel")):
        P(t, w - 2.9 - 1.05 * k, 1.0, gap=0.9)
    # a table with two stools on the floor toward the S corner
    ta, tb = w - 4.2, 4.4
    if put(M, rid, "RoundTable1", ta, tb, gap=1.6, placed=placed) is not None:
        n += 1
        P("Stool1", ta - 1.05, tb + 0.2, gap=0.6)
        P("Stool2", ta + 0.2, tb + 1.05, gap=0.6)
    return n


def start_spot(M, rid):
    """A room point for the player's start: by the NW wall near the tent, off every mouth and every piece."""
    w, h = M.rooms[rid]["size"]
    taken = _taken(M, rid)
    for a, b in ((2.4, h / 2), (2.6, h / 2 - 2), (w / 2, 2.2), (w / 2 - 2.5, h / 2 - 1.5), (w - 2.5, h / 2)):
        if not in_mouth(M, rid, a, b, pad=0.5) and M.free(rid, a, b, 2.4) and                 not any(math.hypot(a - qa, b - qb) < 1.1 for qa, qb in taken):
            return a, b
    return free_spot(M, rid, 2.4, h / 2)


def extra(M, rid, pieces, clear=1.3, reach=2.0):
    """More pieces for a sparse room: each (type, a, b, xfer...) at the free spot nearest (a, b) within `reach`
    squares (none if the room is full there). Returns how many went in."""
    n = 0
    for t, a, b, *kw in pieces:
        spot = free_spot(M, rid, a, b, clear=clear, reach=reach, strict=True)
        if spot and M.put(rid, t, *spot, clear=2.4, **(kw[0] if kw else {})) is not None: n += 1
    return n


def free_spot(M, rid, a, b, clear=1.1, step=0.5, reach=6.0, strict=False):
    """The room point nearest (a, b) with no piece within `clear` squares, off the walls (a square) and out of every
    mouth: where a quest item or a person goes so it never lies on a table or in a chair."""
    w, h = M.rooms[rid]["size"]
    taken = _taken(M, rid)
    best = None
    r = 0.0
    while r <= reach and best is None:
        n = max(1, int(2 * math.pi * r / step)) if r else 1
        for k in range(n):
            t = 2 * math.pi * k / n
            pa, pb = a + r * math.cos(t), b + r * math.sin(t)
            if not (1.0 <= pa <= w - 1.0 and 1.0 <= pb <= h - 1.0): continue
            if in_mouth(M, rid, pa, pb, pad=0.3): continue
            if any(math.hypot(pa - qa, pb - qb) < clear for qa, qb in taken): continue
            best = (pa, pb)
            break
        r += step
    return best if strict else (best or (a, b))
