"""The civic rooms' composer (QA round 1, 2026-10-13): the room types the user did not rate in round 1 inherit the round's
verdict. The user, closing the round: "Much of the feedback boiled down to" two themes:
1. the rooms are too empty, with too little diversity of objects;
2. there is no balance or symmetry: things are placed randomly, not lined up with each other.

The rated rooms taught what the unrated ones must do (review/qa1/civic.md, rules/rooms/<type>.md):
- fill the dead space: the S corner and the SE and SW walls get a group of their own (a small table with two chairs, a
  heap of mixed stock, a bench); bigger rooms more, never a large bare middle;
- several kinds of piece, never one family alone, never the same piece side by side;
- the NE and NW walls hung (banners, trophies, tapestries, paintings) or lined end to end where the type calls for it;
- balance: a piece centred on its wall or between another piece and a wall; mirrored pairs either side of a focal piece
  or in matching corners; a table set centred on its carpet; rows evenly spaced; ceremonial rooms composed on the axis
  from the door;
- a keeper's counter facing the way in with the keeper behind it; clearance round the big pieces and the fires.

A recipe in kit/identity.py ROOMS with `civic` set is composed here (Furnisher.compose's "civic" slot runs `compose`) and
finished here (`finish`) instead of the generic fill, density, wall-lining, lighting and grammar passes, whose random
top-ups and Westwood-statistics moves had undone exactly the balance the user asked for. Everything still goes through
Furnisher.try_put, so the room geometry, the doors' ways in, the object knowledge base and the room's cover limit hold.

Directions are the user's (screen): NE wall top right, NW top left, SE bottom right, SW bottom left; the N corner is the
top one, the S corner the bottom one, nearest the camera. In the kit's uv: the NW wall is the room's least u, the SE its
greatest; the SW wall its least v, the NE its greatest; so the S corner is (max u, min v).
"""
import math
import random
import re
import zlib
from collections import Counter

from kit import furnish as F
from kit import objects as OBJ

NAME = F.WALL_NAME                     # run side -> NE/NW/SE/SW
BACK = ("NE", "NW")
FRONT = ("SE", "SW")
import os as _os
DEBUG = _os.environ.get("NOX_CIVIC_DEBUG") == "1"
CORNERS = {"N": ("NW", "NE"), "E": ("NE", "SE"), "S": ("SE", "SW"), "W": ("SW", "NW")}


class Ctx:
    """One room's frame and the composer's helpers over a Furnisher."""

    def __init__(self, f):
        self.f = f
        self.rng = random.Random(zlib.crc32(f"civic:{f.spec.d.get('name')}:{f.room.id}".encode()) ^ int(f.rng.random() * 1e9))
        self.runs = {n: [] for n in ("NE", "NW", "SE", "SW")}
        for r in f.g.runs:
            self.runs[NAME[r["side"]]].append(r)
        for n in self.runs: self.runs[n].sort(key=lambda r: r["lo"] - r["hi"])
        us = [x + y + 1 for x, y in f.g.cells]; vs = [x - y for x, y in f.g.cells]
        self.box = (min(us), max(us), min(vs), max(vs))
        # the wall lines (the main run of each wall; a room of another shape keeps its outer box)
        self.uN = self.runs["NW"][0]["coord"] if self.runs["NW"] else self.box[0] - 1
        self.uS = self.runs["SE"][0]["coord"] if self.runs["SE"] else self.box[1] + 1
        self.vW = self.runs["SW"][0]["coord"] if self.runs["SW"] else self.box[2] - 1
        self.vE = self.runs["NE"][0]["coord"] if self.runs["NE"] else self.box[3] + 1
        self.tiles = len(f.room.tiles)
        self.door = f.main_door()
        self.lights = []                # (u, v) of the floor lights composed
        self.set_type = {}              # a grid's one kind of table
        self.log = []

    # ---- geometry ------------------------------------------------------------------------------------------------
    def wall(self, name):
        return self.runs[name][0] if self.runs.get(name) else None

    def name_of(self, r):
        return NAME[r["side"]]

    def corner_uv(self, corner, d_u, d_v=None):
        """A point `d_u`, `d_v` units in from both walls of a room corner (N, E, S, W)."""
        d_v = d_u if d_v is None else d_v
        u = self.uN + d_u if corner in ("N", "W") else self.uS - d_u
        v = self.vE - d_v if corner in ("N", "E") else self.vW + d_v
        return u, v

    def centre(self):
        return (self.uN + self.uS) / 2, (self.vW + self.vE) / 2

    def far_wall(self):
        """The wall straight across the room from the main door (its run), or None."""
        op = self.door
        if not op: return None
        cands = [r for r in self.f.g.runs if r["line"] == op["line"] and r["sign"] == -op["sign"]
                 and r["lo"] + 1 <= op["along"] <= r["hi"] - 1]
        return max(cands, key=lambda r: abs(r["coord"] - op["coord"]), default=None)

    def free(self, r, pad=0.0, tall_only=False):
        """Free stretches (lo, hi) of wall run r."""
        return [(lo, hi) for rr, lo, hi in self.f.segments(pad=pad, tall_only=tall_only) if rr is r]

    def occupied_depth(self, r, reach=4.0):
        """How far into the room the pieces standing against wall run r reach (0 for a bare wall)."""
        best = 0.0
        for t, (u, v, hu, hv, b, layer) in self.f._typed:
            if not b or layer == "wall": continue
            if r["line"] == "/":
                d = (u - r["coord"]) * r["sign"]; along, hp, ha = v, hu, hv
            else:
                d = (v - r["coord"]) * r["sign"]; along, hp, ha = u, hv, hu
            if 0 < d - hp < reach and r["lo"] - 0.5 <= along <= r["hi"] + 0.5:
                best = max(best, d + hp)
        return best

    def middle_box(self, walk=1.3):
        """The open middle: the box inside the pieces standing along the four walls, a walkway clear of them."""
        dn = self.occupied_depth(self.wall("NW")) if self.wall("NW") else 0.0
        ds = self.occupied_depth(self.wall("SE")) if self.wall("SE") else 0.0
        dw = self.occupied_depth(self.wall("SW")) if self.wall("SW") else 0.0
        de = self.occupied_depth(self.wall("NE")) if self.wall("NE") else 0.0
        return (self.uN + max(dn, 0.6) + walk, self.uS - max(ds, 0.6) - walk,
                self.vW + max(dw, 0.6) + walk, self.vE - max(de, 0.6) - walk)

    # ---- types ----------------------------------------------------------------------------------------------------
    def types(self, pat, fam=None):
        f = self.f
        return sorted(t for t in f.things if re.search(pat, t) and f.ok_type(t) and (fam is None or F._family_of(t) == fam))

    def pick(self, pat, fam=None):
        ts = self.types(pat, fam)
        return self.rng.choice(ts) if ts else None

    # ---- placing --------------------------------------------------------------------------------------------------
    def put(self, t, u, v, blocking=True, light=False, **kw):
        f = self.f
        if light: f.placing_light = True
        try:
            return f.try_put(t, u, v, blocking=blocking, **kw)
        finally:
            if light: f.placing_light = False

    def put_all(self, items, pairing=False, group=False):
        """Places every (type, u, v[, kw]) or none of them. Returns the objects or None."""
        f = self.f
        got = []
        saved = (f._pairing, f._group)
        if pairing: f._pairing = True
        if group and f._group is None: f._group = []
        try:
            for it in items:
                t, u, v = it[:3]
                kw = it[3] if len(it) > 3 else {}
                o = self.put(t, u, v, **kw)
                if not o:
                    for x in got: f._remove(x)
                    return None
                got.append(o)
        finally:
            f._pairing, f._group = saved
        return got

    def on_wall(self, t0, r, a, fam=None, extra=0.0, blocking=True, pairing=False):
        """Piece t0 snug against wall run r at `a` along it (its variant for that wall). Returns (obj, (u, v), ha, hp)."""
        f = self.f
        fam = fam or F._family_of(t0)
        t = f.side_variant(t0, r, fam) or (f.along_variant(t0, r["side"]) if fam else None) or t0
        hu, hv = f.half(t)
        ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
        if not (r["lo"] + 1.05 + ha <= a <= r["hi"] - 1.05 - ha): return None
        d = hp + F.SNUG_GAP.get(fam, 0.25) + extra
        u, v = f._uv_on(r, d, a)
        saved = f._pairing
        f._pairing = pairing or saved
        try:
            o = f.try_put(t, u, v, blocking=blocking and fam not in F.NON_BLOCKING, snug=True)
        finally:
            f._pairing = saved
        if not o: return None
        key = (r["line"], r["coord"])
        f.wall_used.append((key, a - ha, a + ha))
        if fam in F.TALL_FAMS: f.wall_tall.append((key, a - ha, a + ha))
        f.anchors.append((u, v))
        return o, (u, v), ha, hp

    def hang(self, t, r, a):
        """A hanging on wall run r at `a` along it."""
        f = self.f
        inv = f.T["inventory"].get("wall_decor", {})
        t = f.side_variant(t, r, "wall_decor")
        if not t: return None
        hu, hv = f.half(t)
        d = max(f.perp_for(t, inv.get("perp_px")), (hu if r["line"] == "/" else hv) + 0.05)   # its box inside the room
        u, v = f._uv_on(r, d, a)
        o = f.try_put(t, u, v, blocking=False, wall_ok=True, layer="wall")
        if DEBUG and not o:
            hu, hv = f.half(t)
            self.log.append(f"   hang {t} at {a:.1f} d={d:.2f}: fits={f.g.fits(u, v, hu, hv, False, True)} "
                            f"kb={f._kb_ok(t, u, v, hu, hv, False, 'wall')} one={f._one_of_a_kind_ok(t, u, v)} {dict(f.kb_refused)}")
        if o:
            f.wall_used.append(((r["line"], r["coord"]), a - F.HANG_HALF, a + F.HANG_HALF))
        return o

    def light_at(self, u, v, t=None):
        f = self.f
        t = t or f.light_type()
        if any(math.hypot(u - a, v - b) < 2.2 for a, b in self.lights): return None
        if any(u + 0.5 > z[0] and u - 0.5 < z[1] and v + 0.5 > z[2] and v - 0.5 < z[3] for z in f.light_zones): return None
        if f._before_anchor(u, v): return None
        o = self.put(t, u, v, light=True)
        if o:
            self.lights.append((u, v))
            self.f.ring_lights.append((u, v))     # add_lights counts them
        return o

    # ---- arrangements ---------------------------------------------------------------------------------------------
    def focal(self, fam, at="center", clear=2.4, door=False, only=None, wall=None, rug=False):
        """The room's focal piece centred on a wall: the wall across from the door (door=True) or a back wall."""
        f = self.f
        if wall:                                   # a named wall, centred on its longest free stretch
            r = self.wall(wall)
            if r:
                for lo, hi in sorted(self.free(r), key=lambda s: s[0] - s[1]):
                    t0 = F._pick(f.rng, {t: w for t, w in f.types_of(fam).items() if not only or re.search(only, t)})
                    if not t0: break
                    res = self.on_wall(t0, r, (lo + hi) / 2, fam)
                    if res:
                        o, uv, ha, hp = res
                        p = dict(obj=o, run=r, uv=uv, along=(lo + hi) / 2, ha=ha, hp=hp)
                        if F.NEEDS_FRONT.search(o["type"]):
                            f.g.zones.append(f.front_zone(r, *uv, max(0.8, ha) + 0.3, hp, max(2.3, clear)))
                            f.light_zones.append(f.front_zone(r, *uv, ha + 0.3, hp, 2.6))
                        if rug: f.rug_before(p)
                        return p
        p = f.place_on_wall(fam, at, clear, door=door, only=only)
        if p and rug: f.rug_before(p)
        return p

    def flank(self, p, pat, gap=0.3, fam=None, n_each=1, pairing=True, blocking=True):
        """Mirrored pieces either side of placed anchor p on its wall: n_each a side, end to end, `gap` from it. Both
        sides or neither, as many as both sides take. Returns the pieces placed."""
        if not p: return 0
        r = p["run"]
        types = self.types(pat, fam)
        if not types: return 0
        t0 = self.rng.choice(types)
        got = 0
        for k in range(n_each):
            done = False
            for extra in (0.0, 0.5, 1.0):
                t = self.f.side_variant(t0, r, fam or F._family_of(t0)) or t0
                hu, hv = self.f.half(t)
                ha = hv if r["line"] == "/" else hu
                off = p["ha"] + gap + extra + ha + k * (2 * ha + 0.05)
                a1 = self.on_wall(t0, r, p["along"] - off, fam, pairing=pairing, blocking=blocking)
                a2 = a1 and self.on_wall(t0, r, p["along"] + off, fam, pairing=pairing, blocking=blocking)
                if a1 and a2:
                    got += 2; done = True; break
                if a1: self.f._remove(a1[0])
            if not done: break
        return got

    def flank_lights(self, p, gap=0.6, before=0.5):
        """A matching pair of floor lights at the anchor's two front corners."""
        if not p: return 0
        r = p["run"]
        d = abs((p["uv"][0] if r["line"] == "/" else p["uv"][1]) - r["coord"]) + p["hp"] * 0.2 + before
        f = self.f
        t = f.light_type()
        for off in (p["ha"] + gap, p["ha"] + gap + 0.6, p["ha"] + gap + 1.2):
            a1, a2 = f._uv_on(r, d, p["along"] - off), f._uv_on(r, d, p["along"] + off)
            o1 = self.light_at(*a1, t=t)
            o2 = o1 and self.light_at(*a2, t=t)
            if o1 and o2: return 2
            if o1: f._remove(o1); self.lights.pop(); f.ring_lights.pop()
        return 0

    def run_pair_from(self, p, pat, fam=None, most=4):
        """Shelves end to end either side of anchor p, mirrored, as far as both sides allow (a hearth or a desk between
        bookcases to the corners)."""
        return self.flank(p, pat, gap=0.15, fam=fam, n_each=most)

    def line(self, r, pat, fam=None, most=20, gap=0.05, centre=True, kinds=1):
        """A wall run lined end to end with pieces of `pat` across its longest free stretch, centred (the room's other
        back wall of bookcases, a herbalist's potion shelves). Returns the pieces placed."""
        if not r: return 0
        f = self.f
        types = self.types(pat, fam)
        if not types: return 0
        chosen = self.rng.sample(types, min(kinds, len(types)))
        got = 0
        for lo, hi in sorted(self.free(r), key=lambda s: s[0] - s[1])[:2]:
            t = f.side_variant(chosen[0], r, fam or F._family_of(chosen[0])) or chosen[0]
            hu, hv = f.half(t)
            w = 2 * (hv if r["line"] == "/" else hu) + gap
            lo2, hi2 = max(lo, r["lo"] + F.CORNER_CLEAR), min(hi, r["hi"] - F.CORNER_CLEAR)
            n = min(most - got, int((hi2 - lo2 + gap) / w))
            if n <= 0: continue
            mid = (lo2 + hi2) / 2 if centre else lo2 + n * w / 2
            for k in range(n):
                a = mid + (k - (n - 1) / 2) * w
                t0 = chosen[k % len(chosen)] if kinds > 1 else chosen[0]
                saved = f._pairing
                f._pairing = True
                try:
                    if self.on_wall(t0, r, a, fam, pairing=True): got += 1
                finally:
                    f._pairing = saved
        return got

    def row(self, r, pat, n, fam=None, extra=0.0, lo=None, hi=None, pairing=True):
        """n pieces evenly spaced along wall run r's longest free stretch (or lo..hi), symmetric about its middle."""
        if not r or n <= 0: return 0
        f = self.f
        t0 = self.pick(pat, fam)
        if not t0: return 0
        segs = [(lo, hi)] if lo is not None else sorted(self.free(r), key=lambda s: s[0] - s[1])[:1]
        for lo_, hi_ in segs:
            for m in range(n, 0, -1):
                step = (hi_ - lo_) / m
                items = []
                for k in range(m):
                    items.append(lo_ + step * (k + 0.5))
                got = []
                for a in items:
                    res = self.on_wall(t0, r, a, fam, extra=extra, pairing=pairing)
                    if not res: break
                    got.append(res[0])
                if len(got) == m: return m
                for o in got: f._remove(o)
        return 0

    def hangings(self, pat=None, walls=BACK, step=3.6, most=6, first=None):
        """The back walls hung: each bare stretch of the NE and NW walls takes hangings at even steps, mirrored about
        its middle, two kinds alternating (A B A, A B C B A: two of one kind to a wall at most, kit/objects.py)."""
        f = self.f
        if pat: types = self.types(pat)
        else: types = sorted(f.decor_theme() or {})
        if not types: return 0
        got = 0
        order = list(types); self.rng.shuffle(order)
        if first: order.sort(key=lambda t: not re.match(first, t))
        for name in walls:
            for r in self.runs.get(name, [])[:2]:
                kinds = []                                 # the kinds this wall has a picture for, one per piece
                for t in order:
                    tv = f.side_variant(t, r, "wall_decor")
                    if tv and OBJ.kind(tv) not in [OBJ.kind(k) for k in kinds]: kinds.append(tv)
                if not kinds: continue
                kinds = kinds[:3]
                for lo, hi in sorted(self.bare(r), key=lambda s: s[0] - s[1]):
                    ha = max(self.f.half(k)[1 if r["line"] == "/" else 0] for k in kinds)
                    lo2, hi2 = max(lo + max(1.0, ha), r["lo"] + 1.9 + ha), min(hi - max(1.0, ha), r["hi"] - 1.9 - ha)
                    if hi2 - lo2 < 0: continue
                    n = min(most, 1 + int((hi2 - lo2) / step))
                    mid = (lo2 + hi2) / 2
                    sp = 0 if n == 1 else (hi2 - lo2) / (n - 1)
                    if n > 1 and sp > step * 1.6:
                        sp = step * 1.6
                    if DEBUG: self.log.append(f"   hang row {name} {lo2:.1f}..{hi2:.1f} n={n} kinds={kinds}")
                    for k in range(n):
                        i = min(k, n - 1 - k)                      # mirrored: the ends alike, the middle its own
                        t = kinds[i % len(kinds)]
                        a = mid + (k - (n - 1) / 2) * sp
                        if self.hang(t, r, a): got += 1
        return got

    def carpet_rect(self, cu, cv, nu, nv):
        """A carpet of nu x nv squares centred as near (cu, cv) as the squares' grid allows, all of it on the room's
        own floor with its trim ring too, clear of the doors. Returns its exact centre (u, v) or None. Nothing is laid
        (lay_carpet lays it)."""
        f = self.f
        if f.carpet_plan is False or not F.CARPET_FLOORS.search(f.room.floor or ""): return None
        sq = {((x + y) // 2, (x - y) // 2) for (x, y) in f.room.tiles}
        nb8 = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]
        inner = {s for s in sq if all((s[0] + a, s[1] + b) in sq for a, b in nb8)}
        tile = lambda s: (s[0] + s[1], s[0] - s[1])
        best = None
        i_c = (cu - nu - 1) / 2; j_c = (cv - nv + 1) / 2
        for di in (0, -1, 1):
            for dj in (0, -1, 1):
                i0 = int(math.floor(i_c)) + di if i_c != int(i_c) else int(i_c) + di
                j0 = int(math.floor(j_c)) + dj if j_c != int(j_c) else int(j_c) + dj
                rect = {(i, j) for i in range(i0, i0 + nu) for j in range(j0, j0 + nv)}
                if not rect <= inner: continue
                ring = {(s[0] + a, s[1] + b) for s in rect for a, b in nb8} - rect
                if any(tile(s) in f.spec.local_blend for s in rect | ring): continue
                c = (2 * i0 + nu + 1, 2 * j0 + nv - 1)
                dd = math.hypot(c[0] - cu, c[1] - cv)
                if best is None or dd < best[0]: best = (dd, c, (i0, j0))
        return None if best is None else (best[1], best[2])

    def lay(self, origin, nu, nv):
        """Lays the carpet carpet_rect found (origin squares i0, j0; nu x nv)."""
        i0, j0 = origin
        box = (2 * i0 + 1.5, 2 * (i0 + nu - 1) + 2.5, 2 * j0 - 0.5, 2 * (j0 + nv - 1) + 0.5)
        return self.f.lay_carpet(box, margin=0.0)

    def table_set(self, uv, table_pat, n_seats, seat="chair", seat_pat=None, carpet=None, rug=False, gap=0.3,
                  reach=3.0):
        """A table with its seats at uv, else as near it as it fits (within `reach`), centred on a carpet of
        carpet=(nu, nv) squares laid under it (the table at the carpet's exact middle). Returns the pieces placed, or 0
        (nothing left behind)."""
        f = self.f
        t = self.pick(table_pat, "table") or self.pick(table_pat)
        if not t: return 0
        u0, v0 = uv
        cands = sorted({(u0 + 0.5 * i, v0 + 0.5 * j) for i in range(-int(2 * reach), int(2 * reach) + 1)
                        for j in range(-int(2 * reach), int(2 * reach) + 1) if 0.25 * (i * i + j * j) <= reach * reach},
                       key=lambda p: math.hypot(p[0] - u0, p[1] - v0))
        tried = set()
        for (u, v) in cands:
            rect = None
            if carpet:
                cr = self.carpet_rect(u, v, *carpet)
                if cr:
                    (u, v), rect = cr
                    if (u, v) in tried: continue
                    tried.add((u, v))
            o = self.put(t, u, v)
            if not o:
                if DEBUG and (u, v) == cands[0]: self.log.append(f"   table {t} at {u:.1f},{v:.1f}: {why(f, t, u, v)}")
                continue
            n0 = len(f.objects)
            n = f.seats_around((u, v), t, n_seats, seat, gap=gap, pat=seat_pat)
            if n < min(2, n_seats) or (n_seats >= 4 and n < 3):
                for x in f.objects[n0:]: f._remove(x)
                f._remove(o)
                continue
            f._seated.add(((u, v), t))
            if rect: self.lay(rect, *carpet)
            elif rug: f.rug_under(o, (u, v))
            self.anchors_add((u, v))
            return 1 + n
        return 0

    def anchors_add(self, uv):
        self.f.anchors.append(uv)

    def bare(self, r, reach=1.8):
        """Stretches of wall run r with nothing standing before it (no piece within `reach` of the wall line) and
        nothing hung on it: where a hanging may go (kit/objects.py: never above a piece)."""
        f = self.f
        segs = self.free(r)
        cuts = []
        for t, (u, v, hu, hv, b, layer) in f._typed:
            if r["line"] == "/": d = (u - r["coord"]) * r["sign"]; along, hp, ha = v, hu, hv
            else: d = (v - r["coord"]) * r["sign"]; along, hp, ha = u, hv, hu
            if layer == "wall" or (0 <= d - hp <= reach):
                cuts.append((along - ha - 0.35, along + ha + 0.35))
        out = []
        for lo, hi in segs:
            free = [(lo, hi)]
            for c0, c1 in cuts:
                nxt = []
                for f0, f1 in free:
                    if c1 <= f0 or c0 >= f1: nxt.append((f0, f1)); continue
                    if c0 > f0: nxt.append((f0, c0))
                    if c1 < f1: nxt.append((c1, f1))
                free = nxt
            out += [(a, b) for a, b in free if b - a >= 1.0]
        return out

    def heap(self, uv, pats, n=4, toward=None):
        """A tight heap of mixed stock at uv: one piece of each pattern in turn (a barrel, a crate, sacks of two sizes),
        each set against the last, toward the corner `toward` (u, v) when given."""
        f = self.f
        pieces = []
        for p in pats:
            t = self.pick(p)
            if t: pieces.append(t)
        if not pieces: return 0
        u0, v0 = uv
        got, saved = [], f._group
        f._group = []
        try:
            for k in range(n):
                t = pieces[k % len(pieces)]
                hu, hv = f.half(t)
                cands = []
                if not got:                        # the first piece: at uv, else slid along either wall
                    su = 1 if toward and toward[0] > u0 else -1
                    sv = 1 if toward and toward[1] > v0 else -1
                    if toward:                     # snug in the corner by its own size
                        u0 = toward[0] - su * (hu + 0.3); v0 = toward[1] - sv * (hv + 0.3)
                    cands = [(u0, v0)] + [(u0 - su * k * 0.5, v0) for k in range(1, 7)] +                             [(u0, v0 - sv * k * 0.5) for k in range(1, 7)] +                             [(u0 - su * k * 0.5, v0 - sv * k * 0.5) for k in range(1, 5)]
                    cands.sort(key=lambda c: math.hypot(c[0] - u0, c[1] - v0))
                for o in got:
                    rec = f._placed_of.get(id(o))
                    if not rec: continue
                    for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1), (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)):
                        cands.append((rec[0] + du * (rec[2] + hu + 0.2), rec[1] + dv * (rec[3] + hv + 0.2)))
                if toward and got:
                    cands.sort(key=lambda c: math.hypot(c[0] - toward[0], c[1] - toward[1]))
                for c in cands[:20]:
                    o = f.try_put(t, *c)
                    if o: got.append(o); break
                    if DEBUG: self.log.append(f"   heap {t} at {c[0]:.1f},{c[1]:.1f}: {why(f, t, *c)}")
        finally:
            f._group = saved
        return len(got)

    def corner_heap(self, corner, pats, n=4, d=1.0):
        cu, cv = self.corner_uv(corner, d)
        far = self.corner_uv(corner, 0.0)
        return self.heap((cu, cv), pats, n, toward=far)

    def corner_set(self, corner, table_pat, seats=2, seat="chair", d=2.0, carpet=False):
        """A small table with its seats standing in a room corner (the S corner's dead space)."""
        for dd in (d, d + 0.5, d + 1.0, d + 1.6):
            uv = self.corner_uv(corner, dd)
            got = self.table_set(uv, table_pat, seats, seat, carpet=(2, 2) if carpet else None, rug=not carpet)
            if got: return got
        return 0

    def corner_lights(self, corners=("W", "E"), d=0.9):
        """A matching pair of floor lights in two corners."""
        f = self.f
        t = f.light_type()
        for dd in (d, d + 0.5, d + 1.0, d + 1.6):
            a = self.corner_uv(corners[0], dd); b = self.corner_uv(corners[1], dd)
            o1 = self.light_at(*a, t=t)
            o2 = o1 and self.light_at(*b, t=t)
            if o1 and o2: return 2
            if o1: f._remove(o1); self.lights.pop(); f.ring_lights.pop()
        return 0

    def front_pair(self, pat, fam=None, wall="SE", off_frac=0.25):
        """A mirrored pair on a front wall, a quarter of the way in from each end (benches, barrels)."""
        r = self.wall(wall)
        if not r: return 0
        lo, hi = r["lo"] + 1, r["hi"] - 1
        t0 = self.pick(pat, fam)
        if not t0: return 0
        for frac in (off_frac, off_frac + 0.08, off_frac - 0.08, off_frac + 0.16):
            a1, a2 = lo + (hi - lo) * frac, hi - (hi - lo) * frac
            x = self.on_wall(t0, r, a1, fam, pairing=True)
            y = x and self.on_wall(t0, r, a2, fam, pairing=True)
            if x and y: return 2
            if x: self.f._remove(x[0])
        return 0

    def centred_on(self, wall, pat, fam=None, extra=0.0):
        """One piece centred on a wall's longest free stretch (a chest)."""
        r = self.wall(wall)
        if not r: return None
        t0 = self.pick(pat, fam)
        if not t0: return None
        for lo, hi in sorted(self.free(r), key=lambda s: s[0] - s[1]):
            res = self.on_wall(t0, r, (lo + hi) / 2, fam, extra=extra)
            if res: return res
        return None

    def wall_set(self, wall, table_pat, seats=2, seat="chair", at=0.5):
        """A table against a wall with its seats, at a share `at` of its free stretch (a front wall's sitting set)."""
        r = self.wall(wall)
        if not r: return 0
        f = self.f
        t = self.pick(table_pat, "table")
        if not t: return 0
        for lo, hi in sorted(self.free(r, pad=0.3), key=lambda s: s[0] - s[1])[:2]:
            for a in (lo + (hi - lo) * at, (lo + hi) / 2):
                hu, hv = f.half(t)
                hp = hu if r["line"] == "/" else hv
                uv = f._uv_on(r, hp + 0.9, a)
                o = self.put(t, *uv)
                if not o: continue
                n = f.seats_around(uv, t, seats, seat, gap=0.3)
                if n >= min(2, seats): return 1 + n
                for x in f.objects[-n:] if n else []: f._remove(x)
                f._remove(o)
        return 0


    # ---- the open floor ---------------------------------------------------------------------------------------------
    def bare_spot(self, margin=1.2):
        """The point of the floor farthest from every piece and wall: (u, v, distance), or None."""
        f = self.f
        pieces = [(p[0], p[1], p[2], p[3]) for p in f.g.placed if p[4] and p[5] != "wall"]
        best = None
        for (x, y) in list(f.g.cells)[::2]:
            u, v = x + y + 1.0, float(x - y)
            if not f.g.inside(u, v): continue
            dw = f.g.wall_dist(u, v)
            if dw < margin + 0.8: continue
            if any(abs(u - du) < 2.6 and abs(v - dv) < 2.6 for du, dv in f.g.doors): continue
            dp = min([max(abs(u - a) - hu, abs(v - b) - hv, 0.0) for a, b, hu, hv in pieces] or [99.0])
            d = min(dp, dw - 0.6)
            if best is None or d > best[2]: best = (u, v, d)
        return best

    def fill_bare(self, makers, most=3, over=3.2):
        """Groups where the floor is still bare: while some point lies `over` units from everything, the first maker that
        fits there (each a function (ctx, (u, v)) -> pieces) puts its group there, mirrored by the makers that do so."""
        got, tried = 0, []
        for _ in range(most + 4):
            if got >= most: break
            b = self.bare_spot()
            if not b or b[2] < over: break
            u, v, d = b
            if any(math.hypot(u - a, v - c) < 1.5 for a, c in tried): break
            tried.append((u, v))
            for mk in makers:
                n = mk(self, (u, v))
                if n:
                    got += 1
                    if DEBUG: self.log.append(f"   fill_bare at {u:.1f},{v:.1f} (bare {d:.1f}): {mk.__name__} {n}")
                    break
            else:
                # nothing fitted there: a rug keeps the spot from being tried again
                t = self.pick(r"^RedRug\d$")
                if not (t and self.put(t, u, v, blocking=False)): break
        return got

    def lights_balanced(self, want):
        """Floor lights in matching pairs: the side corners, then the front and back corners."""
        for pair in (("W", "E"), ("N", "S")):
            if len(self.lights) >= want: break
            for d in (0.9, 1.5, 2.2):
                if self.corner_lights(pair, d): break


# ---- per type --------------------------------------------------------------------------------------------------------
TABLE_ROUND = r"^RoundTable[12]$"
TABLE_SMALL = r"^SquareTable[12]$|^RoundTable[12]$"
STOCK = dict(barrel=r"^Barrel2?$", water=r"^WaterBarrel$", crate=r"^Crate[12]$", dcrate=r"^DarkCrate[12]$",
             sack_l=r"^SackChestLarge[12]$", sack_m=r"^SackChestMedium[12]$", sack_s=r"^SackChestSmall[12]$",
             apples=r"^TraderAppleCrate$", tools=r"^BarrelWithTools[12]$", steel=r"^CrateSteel[1-4]$",
             steelb=r"^BarrelSteel[12]$", piled=r"^PiledBarrels[1-4]$", cask=r"^LargeBarrel[12]$")


def S(*keys):
    return [STOCK[k] for k in keys]


def mk_sitting(c, uv):
    """A small table with two chairs on a rug."""
    return c.table_set(uv, TABLE_SMALL, 2, rug=True, reach=1.5)


def mk_round4(c, uv):
    return c.table_set(uv, r"^RoundTable[12]$", 4, rug=True, reach=1.5)


def mk_rug(c, uv):
    t = c.pick(r"^BearskinRug\d$|^RedRug\d$")
    return 1 if t and c.put(t, *uv, blocking=False) else 0


def living_room(c, plan):
    """The hearth centred on a back wall between mirrored shelves, a rug and a bench before it; the household's table
    centred on its carpet in the middle; the chest centred on the other back wall between a pair of shelves (or the
    bed with a nightstand each side in a dwelling); a sitting set in the S corner, mixed stock in the front corners,
    benches mirrored on a front wall, the back walls hung, lights in matching corners."""
    f = c.f
    dwelling = f.kind == "dwelling"
    big = c.tiles >= 80
    hearth = c.focal("fireplace", clear=2.6)
    if hearth:
        c.run_pair_from(hearth, r"^Bookcase\d$|^LogShelvesFull\d$" if not dwelling else r"^LogShelvesFull\d$",
                        fam="shelves", most=1 if c.tiles < 55 else 2 if c.tiles < 90 else 3)
        f.rug_before(hearth)
        if c.tiles >= 60: f.place_before("bench", hearth, gap=2.8)
    other = [w for w in BACK if not hearth or c.name_of(hearth["run"]) != w]
    ow = other[0] if other else "NE"
    if dwelling:
        bed_set(c, ow)
    else:
        ch = c.centred_on(ow, r"^Chest\d$", "storage")
        if ch and big:
            p = dict(obj=ch[0], run=c.wall(ow), uv=ch[1], along=(ch[1][1] if c.wall(ow)["line"] == "/" else ch[1][0]),
                     ha=ch[2], hp=ch[3])
            c.flank(p, r"^Bookcase\d$|^LogShelvesFull\d$", gap=1.0, fam="shelves")
    # the household's table, centred on its carpet in the open middle
    mb = c.middle_box()
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    if not c.table_set((cu, cv), r"^RoundTableWithFood$|^RoundTable[12]$", 4,
                       carpet=(4, 4) if c.tiles >= 100 else (3, 3) if c.tiles >= 45 else (2, 2)):
        c.table_set((cu, cv), r"^RoundTableWithFood$|^RoundTable[12]$", 3, rug=True, reach=4.0) or             c.table_set((cu, cv), r"^RoundTableWithFood$|^RoundTable[12]$", 2, reach=4.0)
    if not c.corner_lights(("W", "E"), 0.9): c.flank_lights(hearth)
    # the dead space: the S corner's own group, the front corners' stock
    if c.tiles >= 36: c.corner_set("S", TABLE_SMALL, 2)
    else: c.corner_heap("S", S("barrel", "water"), n=2)
    c.corner_heap("W", S("barrel", "sack_m", "crate"), n=3)
    c.corner_heap("E", S("water", "crate", "sack_s"), n=2 if c.tiles < 70 else 3)
    if c.tiles >= 60: c.front_pair(r"^Bench\d$|^CushionedBench\d$", "bench", wall="SW" if c.rng.random() < 0.5 else "SE")
    c.fill_bare([mk_sitting, mk_rug], most=1 + c.tiles // 60)
    c.hangings(walls=BACK, most=3)


def bed_set(c, wall):
    """The bed centred on a wall, headboard to it, a nightstand each side at the RM-BEDROOM-10 standard (a hand's width
    off the bed), the chest at its foot, a rug beside it."""
    f = c.f
    r = c.wall(wall)
    if not r: return 0
    bt = c.pick(r"^Bed[2-4]$|^WoodBed[1-3]$", "bed") or c.pick(r"^Cot\d$", "bed")
    if not bt: return 0
    for lo, hi in sorted(c.free(r, pad=1.2), key=lambda s: s[0] - s[1]):
        a = (lo + hi) / 2
        t = f._variant_for_wall(re.sub(r"\d+$", "", bt), r, across=True) or bt
        hu, hv = f.half(t)
        ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
        uv = f._uv_on(r, hp + F.SNUG_GAP.get("bed", 0.28), a)
        o = c.put(t, *uv)
        if not o: continue
        f.beds.append((o, r, uv))
        f.wall_used.append(((r["line"], r["coord"]), a - ha, a + ha))
        ns = f.variant_for_side("Nightstand", r["side"])
        if ns:
            nhu, nhv = f.half(ns)
            nha = nhv if r["line"] == "/" else nhu
            nhp = nhu if r["line"] == "/" else nhv
            for gap in (0.45, 0.6, 0.8):
                off = ha + nha + gap
                d = max(f.perp_for(ns, None), nhp + 0.3)
                got = c.put_all([(ns, *f._uv_on(r, d, a - off)), (ns, *f._uv_on(r, d, a + off))], pairing=True)
                if got: break
        ct = c.pick(r"^Chest\d$", "storage")
        if ct:
            foot = 2 * hp + F.SNUG_GAP.get("bed", 0.28)
            for t2 in [f.along_variant(ct, ("/|TL" if r["side"] == "/|BR" else "/|BR" if r["side"] == "/|TL" else
                                             "\\|TR" if r["side"] == "\\|BL" else "\\|BL")) or ct, ct]:
                h2 = f.half(t2)
                hp2 = h2[0] if r["line"] == "/" else h2[1]
                if c.put(t2, *f._uv_on(r, foot + hp2 + 0.35, a)): break
        return 1
    return 0


def kitchen(c, plan):
    f = c.f
    hearth = c.focal("fireplace", clear=2.6)
    other = [w for w in BACK if not hearth or c.name_of(hearth["run"]) != w]
    # the cooking pot or the iron stove a step off the hearth, never in the corner
    if hearth:
        stove = c.pick(r"^CauldronAnimated$|^Stove0[1-5]$", "stove")
        if stove:
            r = hearth["run"]
            hu, hv = f.half(stove)
            hs = max(hu, hv)
            for side in (1, -1):
                off = hearth["ha"] + 1.9 + hs
                res = c.on_wall(stove, r, hearth["along"] + side * off, "stove", extra=0.35)
                if res:
                    f.g.zones.append(f.front_zone(r, *res[1], res[2], res[3], 1.4))
                    break
    # provisions lining the other back wall end to end
    if other:
        c.line(c.wall(other[0]), r"^LogShelvesFull\d$", "shelves", most=6 if c.tiles >= 60 else 4)
    # the work table with its food in the middle, stools round it
    mb = c.middle_box()
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    if not c.table_set((cu, cv), r"^RoundTableWithFood$|^Table4$", 3, seat_pat=r"Stool"):
        c.table_set((cu, cv), r"^RoundTableWithFood$", 2, seat_pat=r"Stool")
    # stores heaped in the front corners, each a mix (sacks of three sizes, a barrel, a crate of apples)
    c.corner_heap("S", S("sack_l", "sack_m", "apples", "sack_s"), n=4)
    c.corner_heap("W", S("barrel", "water", "crate"), n=3 if c.tiles < 60 else 4)
    c.corner_heap("E", S("crate", "apples", "barrel"), n=3)
    if c.tiles >= 70:
        r = c.wall("SE")
        if r: c.heap(f._uv_on(r, 1.0, (r["lo"] + r["hi"]) / 2), S("tools", "dcrate", "sack_m"), n=3)
    c.hangings(r"^WallTrophy(Bear|Moose|MountainLion)[12]$|^Painting1$", walls=tuple(other) or BACK, most=2)
    c.corner_lights(("W", "E"), 1.8) or c.flank_lights(hearth)


def shop(c, plan):
    """The trader's counter out from the wall across from the way in (a back wall), the keeper behind it, his goods on
    the wall behind him mirrored either side, the trade's stock heaped by the front walls, the walls hung with it."""
    f = c.f
    trade = c.rng.choice(("armourer", "apothecary", "general"))
    counter = f.place_counter("counter_shop", 2.2, 1.8)
    if counter:
        r = counter["run"]
        wa = counter["along"]
        if trade == "apothecary": pat, fam = r"^PotionShelves\d$", "shelves"
        elif trade == "armourer": pat, fam = r"^TraderShelves\d$|^TraderHelmShelf\d$", "shop_rack"
        else: pat, fam = r"^TraderShelves\d$", "shop_rack"
        back = dict(obj=None, run=r, uv=f._uv_on(r, 0.5, wa), along=wa, ha=counter["ha"] * 0.6, hp=0.5)
        c.flank(back, pat, gap=0.4, fam=fam, n_each=1)
        c.flank_lights(dict(counter, hp=counter["hp"]), gap=0.5, before=0.3)
        other = [w for w in BACK if w != c.name_of(r)]
    else:
        other = list(BACK)
    ow = c.wall(other[0]) if other else None
    if trade == "apothecary":
        c.line(ow, r"^PotionShelves\d$|^Bookcase\d$", "shelves", most=6, kinds=2)
        c.hangings(r"^Painting[12]$|^GreenTapestry\d$", walls=other, most=2)
        mid = r"^FairyJar$"
        c.front_pair(mid, None, wall="SW")
        heaps = [S("crate", "sack_m", "barrel"), S("apples", "sack_s", "crate"), S("dcrate", "sack_l")]
    elif trade == "armourer":
        c.row(ow, r"^Trader(ArmorRack|PoleArm|BowRack)\d$", 3 if c.tiles >= 70 else 2, "shop_rack")
        c.hangings(r"^TraderShieldWallHanging\d$|^TraderCrossedWeapons\d$|^TraderHangingSwords\d$",
                   walls=tuple(BACK), most=3)
        heaps = [S("steel", "steelb", "crate"), S("crate", "barrel", "steel"), S("tools", "dcrate")]
    else:
        c.row(ow, r"^TraderShelves\d$", 2, "shop_rack")
        c.hangings(r"^WallTrophy(Bear|Moose|MountainLion)[12]$|^TraderShieldWallHanging\d$", walls=tuple(BACK), most=2)
        heaps = [S("steel", "barrel", "sack_l"), S("apples", "crate", "steelb"), S("sack_m", "tools", "dcrate")]
    # the stock by the front walls: the S corner and both front corners, each heap its own mix
    c.corner_heap("S", heaps[0], n=4)
    c.corner_heap("W", heaps[1], n=3)
    c.corner_heap("E", heaps[2], n=3)
    if c.tiles >= 90 and trade == "armourer":
        # racks for show in a mirrored pair in the open floor before the counter
        mb = c.middle_box(walk=1.6)
        cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
        t = c.pick(r"^TraderArmorRack[12]$")
        if t:
            long_u = (mb[1] - mb[0]) >= (mb[3] - mb[2])
            for off in (2.2, 3.0, 1.6):
                pts = [(cu, cv - off), (cu, cv + off)] if not long_u else [(cu - off, cv), (cu + off, cv)]
                if c.put_all([(t, *p) for p in pts], pairing=True): break
    if c.tiles >= 100:
        r = c.wall("SE")
        if r: c.heap(f._uv_on(r, 1.0, (r["lo"] + r["hi"]) / 2), heaps[1], n=3)
    f._trade = {}
    c.log.append(f"trade {trade}")


# ---- shared arrangements ---------------------------------------------------------------------------------------------
def axis(c, back_first=False):
    """The room's main axis: the wall run across from the main door and the point along it in line with the door, the
    room's depth from that wall. dict(run, mid, depth) or None. back_first: the far wall must be a back wall (a hearth,
    a desk, a throne), else the longest back wall's middle."""
    f = c.f
    r = c.far_wall()
    if r and (not back_first or c.name_of(r) in BACK):
        mid = min(max(c.door["along"], r["lo"] + 3.0), r["hi"] - 3.0)
        return dict(run=r, mid=mid, depth=f._depth_of(r))
    cands = [rr for n in (BACK if back_first else BACK + FRONT) for rr in c.runs.get(n, [])[:1]]
    if not cands: return None
    r = max(cands, key=lambda rr: rr["hi"] - rr["lo"])
    return dict(run=r, mid=(r["lo"] + r["hi"]) / 2, depth=f._depth_of(r))


def on_axis(c, ax, depth, off=0.0):
    """uv of a point `depth` units out from the axis wall, `off` along it from the axis."""
    return c.f._uv_on(ax["run"], depth, ax["mid"] + off)


def mirrored(c, ax, t, depth, off, pairing=True, light=False):
    """A pair of t mirrored about the axis, `off` either side, `depth` out from the axis wall. Both or neither."""
    a = on_axis(c, ax, depth, -off); b = on_axis(c, ax, depth, off)
    kw = dict(light=True) if light else {}
    got = c.put_all([(t, *a, kw), (t, *b, kw)], pairing=pairing)
    if got and light:
        c.lights += [a, b]; c.f.ring_lights += [a, b]
    return 2 if got else 0


def axis_pairs(c, ax, pat, depths, off, light=False):
    """Mirrored pairs down the axis at each depth (columns, statues, braziers, benches)."""
    t = c.pick(pat)
    if not t: return 0
    got = 0
    for d in depths:
        for o in (off, off + 0.6, off - 0.6, off + 1.2):
            n = mirrored(c, ax, t, d, o, light=light)
            if n: got += n; break
    return got


def wall_pair(c, wall, pat, frac=0.25, fam=None):
    """A mirrored pair on a wall a share `frac` in from each end of its main run."""
    r = c.wall(wall)
    if not r: return 0
    t0 = c.pick(pat, fam)
    if not t0: return 0
    lo, hi = r["lo"] + 1, r["hi"] - 1
    for fr in (frac, frac + 0.07, frac - 0.07, frac + 0.14):
        x = c.on_wall(t0, r, lo + (hi - lo) * fr, fam, pairing=True)
        y = x and c.on_wall(t0, r, hi - (hi - lo) * fr, fam, pairing=True)
        if x and y: return 2
        if x: c.f._remove(x[0])
    return 0


def grid_sets(c, box, maker, nx, ny, step_u, step_v):
    """Table sets in an even grid centred in `box` (u0, u1, v0, v1): nx by ny, shrunk until every set fits.
    maker(ctx, (u, v)) places one set (returns pieces or 0). Returns the sets placed."""
    f = c.f
    cu, cv = (box[0] + box[1]) / 2, (box[2] + box[3]) / 2
    for gx, gy in ((nx, ny),):
        n0 = len(f.objects)
        ok = 0
        for i in range(gx):
            for j in range(gy):
                uv = (cu + (i - (gx - 1) / 2) * step_u, cv + (j - (gy - 1) / 2) * step_v)
                if maker(c, uv): ok += 1
        if DEBUG: c.log.append(f"   grid {gx}x{gy} at {cu:.1f},{cv:.1f}: {ok}")
        if ok == gx * gy: return ok
        for x in f.objects[n0:]: f._remove(x)
    return 0


def exact_set(table_pat, seats, seat="chair", seat_pat=None, gap=0.3):
    """A maker of one table set placed exactly at the point (a grid's cell), or nothing."""
    def mk(c, uv):
        f = c.f
        t = c.set_type.get(table_pat) or c.pick(table_pat, "table") or c.pick(table_pat)
        if not t: return 0
        c.set_type[table_pat] = t                   # one kind of table to the grid
        o = c.put(t, *uv)
        if not o: return 0
        n0 = len(f.objects)
        n = f.seats_around(uv, t, seats, seat, gap=gap, pat=seat_pat)
        if n < min(2, seats):
            for x in f.objects[n0:]: f._remove(x)
            f._remove(o); return 0
        f._seated.add((uv, t))
        return 1 + n
    mk.__name__ = f"set:{table_pat}"
    return mk


def carpet_box(c, box, pad=1.0):
    """A carpet laid under a box of pieces (u0, u1, v0, v1), centred on it (within a unit)."""
    nu = max(2, int(math.ceil((box[1] - box[0] + 2 * pad) / 2)))
    nv = max(2, int(math.ceil((box[3] - box[2] + 2 * pad) / 2)))
    cu, cv = (box[0] + box[1]) / 2, (box[2] + box[3]) / 2
    for du in range(0, 3):
        a, b = max(2, nu - du), max(2, nv - du)
        cr = c.carpet_rect(cu, cv, a, b)
        if DEBUG: c.log.append(f"   carpet {a}x{b} at {cu:.1f},{cv:.1f}: {cr}")
        if cr and math.hypot(cr[0][0] - cu, cr[0][1] - cv) <= 1.01:
            return c.lay(cr[1], a, b)
    return None


def pieces_box(c, n0):
    """uv box round the pieces placed since object n0."""
    recs = [c.f._placed_of.get(id(o)) for o in c.f.objects[n0:]]
    recs = [r for r in recs if r]
    if not recs: return None
    return (min(r[0] - r[2] for r in recs), max(r[0] + r[2] for r in recs),
            min(r[1] - r[3] for r in recs), max(r[1] + r[3] for r in recs))


def anchor_of(c, res, r):
    """A placement dict (as Furnisher.place_on_wall returns) from an on_wall result on run r."""
    o, uv, ha, hp = res
    return dict(obj=o, run=r, uv=uv, along=(uv[1] if r["line"] == "/" else uv[0]), ha=ha, hp=hp)


# ---- the public rooms ------------------------------------------------------------------------------------------------
def tavern(c, plan):
    """The bar in a back corner with kegs behind it; the hearth centred on the other back wall on its stones, a rug
    before it and shelves of crockery mirrored either side; the round tables in an even grid centred on one carpet;
    long tables by a front wall, mirrored; kegs heaped in the S corner; trophies along the back walls; lights in
    matching corners."""
    f = c.f
    f.build_bar()
    hearth = c.focal("fireplace", clear=2.8)
    if hearth:
        f.rug_before(hearth)
        c.flank(hearth, r"^LogShelvesFull\d$", gap=1.4, fam="shelves")
    c.corner_lights(("W", "E"), 0.9)
    mb = c.middle_box(walk=1.4)
    mk = exact_set(r"^RoundTable[12]$", 4, seat_pat=r"Stool", gap=0.45)
    w, h = mb[1] - mb[0], mb[3] - mb[2]
    step = 4.6
    nx, ny = max(1, min(4, int(w / step) + 1)), max(1, min(4, int(h / step) + 1))
    n0 = len(f.objects)
    got = 0
    cap = (f.repeat_cap("table") or 12) - 2           # two long tables by a front wall besides
    configs = [(gx, gy) for gx, gy in ((nx, ny), (nx, max(1, ny - 1)), (max(1, nx - 1), ny), (max(1, nx - 1), max(1, ny - 1)),
                                       (3, 2), (2, 3), (2, 2), (2, 1), (1, 2)) if 1 < gx * gy <= max(2, cap)]
    for gx, gy in configs:
        # the grid centred on a carpet's squares, so the carpet laid under it is centred too
        cr = c.carpet_rect((mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2, max(2, int(round((gx - 1) * step / 2)) + 3),
                           max(2, int(round((gy - 1) * step / 2)) + 3))
        cu, cv = cr[0] if cr else ((mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2)
        box = (cu - 0.01, cu + 0.01, cv - 0.01, cv + 0.01)
        got = grid_sets(c, box, mk, gx, gy, step, step) if gx * gy > 1 else 0
        if got == gx * gy and got: break
    if got:
        bx = pieces_box(c, n0)
        if bx: carpet_box(c, bx, pad=0.8)
    # long tables with benches by a front wall, mirrored
    lt = exact_set(r"^Table[1-4]$", 2, seat="bench")
    r = c.wall("SE") if c.rng.random() < 0.5 else c.wall("SW")
    if r:
        for lo, hi in sorted(c.free(r, pad=0.5), key=lambda s: s[0] - s[1])[:1]:
            for frac in (0.3, 0.25, 0.35):
                a1, a2 = lo + (hi - lo) * frac, hi - (hi - lo) * frac
                p1, p2 = f._uv_on(r, 2.6, a1), f._uv_on(r, 2.6, a2)
                n1 = len(f.objects)
                if lt(c, p1) and lt(c, p2): break
                for x in f.objects[n1:]: f._remove(x)
    c.corner_heap("S", S("barrel", "piled", "barrel"), n=3)
    c.fill_bare([mk_round4, mk_sitting], most=2)
    c.hangings(r"^WallTrophy(Bear|Moose|MountainLion)[12]$|^TraderShieldWallHanging\d$", most=4)


def dining_hall(c, plan):
    """Composed on the axis from the door: the high table across the far end, seated, a pair of lights flanking it;
    long tables in rows down the axis on one carpet; the hearth centred on a side back wall between crockery shelves;
    casks in the front corners; benches mirrored on a front wall; banners at even steps on the back walls."""
    f = c.f
    if f.kind == "ogre_hall": return ogre_hall(c, plan)
    ax = axis(c)
    hearth = None
    for w in BACK:                      # the hearth on a back wall that is not the axis wall
        r = c.wall(w)
        if r and (not ax or r is not ax["run"]):
            hearth = c.focal("fireplace", clear=2.8, wall=w)
            if hearth: break
    if not hearth: hearth = c.focal("fireplace", clear=2.8)
    if hearth:
        c.flank(hearth, r"^LogShelvesFull\d$", gap=0.6, fam="shelves", n_each=2 if c.tiles >= 150 else 1)
    if ax:
        r = ax["run"]
        tt = c.pick(r"^Table[1-4]$")            # the high table across the far end, its long side along the wall
        if tt:
            t = f.along_variant(tt, r["side"]) or tt
            hu, hv = f.half(t)
            hp, ha = (hu, hv) if r["line"] == "/" else (hv, hu)
            for d in (hp + 2.2, hp + 2.8, hp + 3.4):
                uv = on_axis(c, ax, d)
                o = c.put(t, *uv)
                if o:
                    f.seats_around(uv, t, 4 if c.tiles >= 120 else 2, "chair", gap=0.3)
                    c.flank_lights(dict(run=r, uv=uv, along=ax["mid"], ha=ha + 0.6, hp=hp), gap=0.6, before=-0.2)
                    break
    rows = f.table_rows(max(2, c.tiles // 40), seat="bench" if f.kind == "mess_hall" or c.rng.random() < 0.5 else "chair")
    if rows and f.kind != "mess_hall":
        recs = [f._placed_of.get(id(o)) for o, _ in rows]
        recs = [r_ for r_ in recs if r_]
        if recs:
            carpet_box(c, (min(r_[0] - r_[2] for r_ in recs), max(r_[0] + r_[2] for r_ in recs),
                           min(r_[1] - r_[3] for r_ in recs), max(r_[1] + r_[3] for r_ in recs)), pad=1.6)
    c.corner_heap("W", S("cask", "barrel"), n=2)
    c.corner_heap("E", S("cask", "barrel"), n=2)
    c.corner_heap("S", S("barrel", "piled", "water"), n=3)
    wall_pair(c, "SW" if c.rng.random() < 0.5 else "SE", r"^Bench\d$|^LightBench\d$", 0.2, "bench")
    c.fill_bare([mk_sitting], most=1)
    c.lights_balanced(4 if c.tiles >= 120 else 2)
    c.hangings(r"^(Red|Blue|Green|White)Tapestry\d$" if f.kind != "mess_hall" else
               r"^WallTrophy(Bear|Moose|MountainLion)[12]$|^TraderShieldWallHanging\d$", most=4)


def ogre_hall(c, plan):
    """The ogres' feast, minimal but balanced: the fire pit in the middle, crude tables mirrored either side of it
    with their stools, meat by them, sacks and barrels heaped in matching corners, skulls on the back walls."""
    f = c.f
    mb = c.middle_box(walk=1.0)
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    for du in (0, 0.5, -0.5, 1.0, -1.0, 1.5):
        pit = c.put("OgreFirePit", cu + du, cv - du) if f.ok_type("OgreFirePit") else None
        if pit:
            cu, cv = cu + du, cv - du
            break
    long_u = (mb[1] - mb[0]) >= (mb[3] - mb[2])
    mk = exact_set(r"^OgreTable[123]$", 3, seat_pat=r"^OgreStool\d$|^OgreBench[34]$", gap=0.35)
    for off in (5.0, 4.4, 5.8, 3.8, 6.4):
        pts = [(cu - off, cv), (cu + off, cv)] if long_u else [(cu, cv - off), (cu, cv + off)]
        n0 = len(f.objects)
        if mk(c, pts[0]) and mk(c, pts[1]): break
        for x in f.objects[n0:]: f._remove(x)
    for corner in ("W", "E"):
        c.corner_heap(corner, [r"^OgreSack\d$", r"^Barrel2?$", r"^PiledBarrels\d$"], n=3)
    c.corner_heap("S", [r"^Barrel2?$", r"^OgreSack\d$"], n=2)
    c.corner_heap("N", [r"^OgreHutCarcassBig$|^OgreHutCarcass$"], n=1, d=1.4)
    if c.tiles >= 150:
        for off in (2.6, 3.2):
            pts = [(cu, cv - off), (cu, cv + off)] if long_u else [(cu - off, cv), (cu + off, cv)]
            if c.put_all([("OgreHutMeat", *p) for p in pts]): break
    c.hangings(r"^OgreHutWallSkull[1-4]$", most=3, step=4.0)


# ---- the ceremonial rooms --------------------------------------------------------------------------------------------
def gallery(c, plan):
    """Paintings at even steps along both back walls, mirrored; a runner down the axis from the door; statues in
    mirrored pairs down it and a pair of centrepieces (flame basins or orreries) either side of its middle; benches
    mirrored on the front walls; plants in the four corners."""
    f = c.f
    ax = axis(c)
    if ax:
        r = ax["run"]
        f.lay_runner(r, ax["mid"], 1.0, ax["depth"] - 1.0)
        depth = ax["depth"]
        k = max(1, int((depth - 4) / 5.5))
        axis_pairs(c, ax, r"^Statue2[aceg]$", [2.6 + (depth - 5.2) * (i + 0.5) / k for i in range(k)], 2.6)
        axis_pairs(c, ax, r"^DunMirFlameBasinLit$|^Orrery2$", [depth / 2], 4.4)
    for corner in ("W", "E", "S", "N"):
        cu, cv = c.corner_uv(corner, 1.0)
        t = c.pick(r"^Plant[1345]$")
        if t: c.put(t, cu, cv)
    for w in FRONT:
        wall_pair(c, w, r"^Bench[1-4]$|^CushionedBench\d$", 0.3, "bench")
    c.lights_balanced(4 if c.tiles >= 150 else 2)
    c.hangings(r"^Painting[12]$|^BlueTapestry[24]$", step=3.2, most=7, first=r"^Painting")


def hall(c, plan):
    """A colonnade in mirrored pairs either side of the aisle from the door, statues facing across it between the
    columns, a statue pair flanking the middle of the far wall, benches mirrored on the front walls, lights in matching
    corners, banners and shields at even steps on the back walls."""
    f = c.f
    ax = axis(c)
    if ax:
        f.aisle = dict(run=ax["run"], mid=ax["mid"], half=1.6, first=2.4, far=ax["depth"], door=c.door)
    f.colonnade(gap=4.2, aisle=3.2)
    if f.aisle:
        t = c.pick(r"^Statue2[a-h]$")
        if t: f.aisle_pair(t)
    if ax:
        r = ax["run"]
        far = dict(obj=None, run=r, uv=f._uv_on(r, 0.5, ax["mid"]), along=ax["mid"], ha=1.2, hp=0.4)
        c.flank(far, r"^Statue2[a-h]$", gap=1.2, fam="statue")
    for w in FRONT:
        wall_pair(c, w, r"^Bench[1-4]$|^CushionedBench\d$", 0.28, "bench")
    c.lights_balanced(4 if c.tiles >= 150 else 2)
    c.corner_heap("S", [r"^StatueVase\d"], n=1, d=1.2)
    c.hangings(r"^(Blue|Red|Green|White)Tapestry\d$|^TraderShieldWallHanging\d$|^DunMirHangingShield\d+$",
               step=3.6, most=6)


def throne_room(c, plan):
    """The throne across from the door on the NW wall facing it down a runner; statues and braziers flanking it; pairs
    of columns and braziers down the aisle; benches mirrored on two walls; tapestries of one colour at even steps;
    lights in matching corners."""
    f = c.f
    th = f.place_throne(depth=2.9, runner=True)
    if th:
        c.flank(th, r"^Statue2[a-h]$", gap=0.8, fam="statue")
        f.flank_lights(th, 0.9)
    f.colonnade(gap=5.0, aisle=3.0)
    f.aisle_lights(2)
    if f.aisle:
        t = c.pick(r"^Statue2[a-h]$")
        if t: f.aisle_pair(t)
    for w in ("SW", "NE"):
        wall_pair(c, w, r"^Bench[1-4]$|^CushionedBench\d$", 0.3, "bench")
    c.corner_lights(("W", "E"), 1.0)
    c.corner_heap("S", [r"^StatueVase\d"], n=1, d=1.2)
    col = c.rng.choice(("Blue", "Red", "White", "Green"))
    c.hangings(rf"^{col}Tapestry\d$", step=3.4, most=6)


# ---- the private rooms -----------------------------------------------------------------------------------------------
def solar(c, plan):
    """The lord's chamber in two ends: the bed centred on one back wall with a nightstand each side and the chest at
    its foot; the hearth centred on the other back wall between bookcases, a sitting set on a carpet before it; the
    desk centred with its chair; benches and urns mirrored on the front walls; tapestries; the S corner's set."""
    f = c.f
    walls = list(BACK); c.rng.shuffle(walls)
    hearth = c.focal("fireplace", clear=2.8, wall=walls[0])
    if hearth:
        c.run_pair_from(hearth, r"^Bookcase\d$", fam="shelves", most=2 if c.tiles < 180 else 3)
        r = hearth["run"]
        uv = f._uv_on(r, 6.2, hearth["along"])
        c.table_set(uv, TABLE_SMALL, 2, carpet=(3, 3), reach=1.5) or c.table_set(uv, TABLE_SMALL, 2, rug=True)
    bed_set(c, walls[1])
    for w in walls + list(FRONT):
        if not c.wall(w): continue
        d = c.centred_on(w, r"^Desk[12]$", "desk")
        if d:
            f.seats_around(d[1], d[0]["type"], 1)
            break
    c.lights_balanced(4)
    c.corner_set("S", TABLE_SMALL, 2)
    c.corner_heap("W", S("sack_m", "crate"), n=2)
    wall_pair(c, "SE", r"^Bench\d$|^CushionedBench\d$", 0.25, "bench")
    wall_pair(c, "SW", r"^StatueVase\d", 0.2)
    c.fill_bare([mk_sitting, mk_rug], most=2)
    c.hangings(r"^(Blue|Red|White|Green)Tapestry\d$|^Painting[12]$", most=4)


def study(c, plan):
    """The desk centred on a back wall with its chair, bookcases end to end either side of it; the other back wall
    lined with bookcases round a centred chest; the meeting table centred on its carpet; curios in matching corners;
    the S corner's reading set; lights flanking the desk."""
    f = c.f
    walls = list(BACK); c.rng.shuffle(walls)
    desk = c.focal("desk", clear=1.6, wall=walls[0])
    if desk:
        f.seats_around(desk["uv"], desk["obj"]["type"], 1)
        c.run_pair_from(desk, r"^Bookcase\d$", fam="shelves", most=6)
        c.flank_lights(desk, gap=0.4, before=0.8)
    ch = c.centred_on(walls[1], r"^Chest\d$", "storage")
    if ch:
        c.flank(anchor_of(c, ch, c.wall(walls[1])), r"^Bookcase\d$", gap=1.2, fam="shelves", n_each=5)
    else:
        c.line(c.wall(walls[1]), r"^Bookcase\d$", "shelves", most=8)
    mb = c.middle_box()
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    c.table_set((cu, cv), r"^RoundTable[12]$|^OvalTable[12]$", 4, carpet=(3, 3) if c.tiles >= 60 else (2, 2)) or \
        c.table_set((cu, cv), TABLE_SMALL, 2, rug=True, reach=4.0)
    c.corner_set("S", TABLE_SMALL, 2)
    if c.tiles >= 70:
        t = c.pick(r"^StatueVase\d")
        for corner in ("W", "E"):
            if t: c.put(t, *c.corner_uv(corner, 1.4))
    if c.tiles >= 90: wall_pair(c, "SE", r"^Statue2[aceg]$", 0.3, "statue")
    c.fill_bare([mk_sitting, mk_rug], most=1)
    c.lights_balanced(2)
    c.hangings(r"^Painting[12]$|^(Blue|Red|Green)Tapestry\d$", most=3)


def library(c, plan):
    """Bookcases end to end along both back walls (and the front walls in a big library); stacks of bookcases in rows
    down the middle of a big one; the reading table centred on its carpet; the desk centred with its chair; lights in
    matching corners."""
    f = c.f
    walls = list(BACK); c.rng.shuffle(walls)
    desk = None
    r = c.wall(walls[0])
    t = c.pick(r"^Desk[1-4]$")
    if r and t:
        for lo, hi in sorted(c.free(r), key=lambda s: s[0] - s[1])[:1]:
            res = c.on_wall(t, r, (lo + hi) / 2, "desk")
            if res: desk = anchor_of(c, res, r)
    if desk:
        f.seats_around(desk["uv"], desk["obj"]["type"], 1)
        c.run_pair_from(desk, r"^Bookcase\d$", fam="shelves", most=10)
    else:
        c.line(r, r"^Bookcase\d$", "shelves", most=14)
    c.line(c.wall(walls[1]), r"^Bookcase\d$", "shelves", most=14)
    if c.tiles >= 140:
        for w in FRONT: c.line(c.wall(w), r"^Bookcase\d$|^MovableBookcase\d$", "shelves", most=10)
    if c.tiles >= 110:
        f.rack_rows("books", aisle=2.6, gap=2.4)
    mb = c.middle_box(walk=1.2)
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    c.table_set((cu, cv), r"^OvalTable[12]$|^RoundTable[12]$", 4, carpet=(3, 3)) or \
        c.table_set((cu, cv), TABLE_SMALL, 2, rug=True, reach=4.0)
    c.corner_set("S", TABLE_SMALL, 2)
    c.lights_balanced(4 if c.tiles >= 120 else 2)
    c.fill_bare([mk_sitting], most=2)
    c.hangings(r"^Painting[12]$|^(Blue|Red|Green)Tapestry\d$", most=2)


# ---- the work rooms with a keeper ----------------------------------------------------------------------------------
def counter_for(c, pat, depth=2.2):
    """The keeper's counter (a table or a trader's desk) set out from a back wall, facing the way in, the keeper's
    space behind it kept clear and his spot recorded there (Furnisher.place_counter)."""
    f = c.f
    types = c.types(pat)
    if not types: return None
    saved = f.ident
    f.ident = dict(f.ident, types=dict(f.ident.get("types", {}), counter_shop=pat),
                   prefer=dict(f.ident.get("prefer", {}), counter_shop={t: 1 for t in types}))
    try:
        return f.place_counter("counter_shop", depth, 1.8)
    finally:
        f.ident = saved


def infirmary(c, plan):
    """A row of cots evenly spaced along the longest front wall with a nightstand between neighbours; the healer's
    table facing the way in with the healer behind it; a pair of potion shelves centred on a back wall with bookcases
    end to end either side; the cauldron centred on its own stretch, clear of the beds; supplies heaped in the front
    corners; hangings of one colour."""
    f = c.f
    walls = sorted((w for w in ("SE", "SW", "NE", "NW") if c.wall(w)), key=lambda w: c.wall(w)["lo"] - c.wall(w)["hi"])
    bedwall = next((w for w in walls if w in FRONT), walls[0] if walls else None)
    if bedwall:
        r = c.wall(bedwall)
        for lo, hi in sorted(c.free(r, pad=0.4), key=lambda s: s[0] - s[1])[:1]:
            t = f._variant_for_wall("Cot", r, across=True) or "Cot1"
            hu, hv = f.half(t)
            ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
            n = max(2, min(8, int((hi - lo) / (2 * ha + 2.2))))
            step = (hi - lo) / n
            ns = f.variant_for_side("Nightstand", r["side"])
            for k in range(n):
                a = lo + step * (k + 0.5)
                uv = f._uv_on(r, hp + 0.3, a)
                o = c.put_all([(t, *uv)], pairing=True)
                if o: f.beds.append((o[0], r, uv))
            if ns:
                nh = f.half(ns)
                for k in range(n - 1):
                    a = lo + step * (k + 1)
                    c.put_all([(ns, *f._uv_on(r, (nh[0] if r["line"] == "/" else nh[1]) + 0.3, a))], pairing=True)
    desk = counter_for(c, r"^Table[14]$|^SquareTable[12]$|^TraderDesk[1-6]$")
    if desk:
        c.flank_lights(desk, gap=0.4, before=0.2)
    ow = [w for w in BACK if not desk or c.wall(w) is not desk["run"]]
    pot = c.centred_on(ow[0], r"^PotionShelves\d$", "shelves") if ow else None
    if pot:
        p = anchor_of(c, pot, c.wall(ow[0]))
        c.flank(p, r"^PotionShelves\d$", gap=0.1, fam="shelves")
        c.flank(dict(p, ha=p["ha"] + 2 * pot[2] + 0.2), r"^Bookcase\d$", gap=0.1, fam="shelves", n_each=2)
    caul = c.pick(r"^CauldronAnimated$")
    if caul:
        done = False
        for w in list(BACK) + list(FRONT):
            r = c.wall(w)
            if not r or done: continue
            for lo, hi in sorted(c.free(r, pad=1.0), key=lambda s: s[0] - s[1])[:1]:
                if c.on_wall(caul, r, (lo + hi) / 2, "stove", extra=0.4): done = True
    c.corner_heap("W", S("sack_m", "crate", "sack_s"), n=3)
    c.corner_heap("E", S("crate", "water"), n=2)
    c.lights_balanced(2)
    c.fill_bare([mk_sitting, mk_rug], most=1)
    c.hangings(r"^(White|Blue|Green)Tapestry\d$", most=3)


def herbalist(c, plan):
    """The herbalist's counter facing the way in with her behind it; potion shelves end to end along the back wall
    behind her; the cauldron centred on the other back wall between books of remedies; glowing jars mirrored on a
    front wall; the work table with stools; sacks of herbs, crates and apples heaped in the front corners."""
    f = c.f
    desk = counter_for(c, r"^TraderDesk[1-6]$|^Table[14]$")
    if desk:
        r = desk["run"]
        back = dict(obj=None, run=r, uv=f._uv_on(r, 0.5, desk["along"]), along=desk["along"], ha=desk["ha"] * 0.5, hp=0.5)
        c.flank(back, r"^PotionShelves\d$", gap=0.1, fam="shelves", n_each=4)
        c.flank_lights(desk, gap=0.4, before=0.2)
    ow = [w for w in BACK if not desk or c.wall(w) is not desk["run"]]
    if ow:
        r = c.wall(ow[0])
        caul = c.pick(r"^CauldronAnimated$")
        res = None
        if caul and r:
            for lo, hi in sorted(c.free(r), key=lambda s: s[0] - s[1])[:1]:
                res = c.on_wall(caul, r, (lo + hi) / 2, "stove", extra=0.5)
        if res:
            c.flank(anchor_of(c, res, r), r"^Bookcase\d$", gap=1.4, fam="shelves", n_each=3)
        elif r:
            c.line(r, r"^Bookcase\d$", "shelves", most=6)
    c.front_pair(r"^FairyJar$", None, wall="SW")
    mb = c.middle_box()
    c.table_set(((mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2), r"^Table4$|^SquareTable[12]$", 2, seat_pat=r"Stool",
                rug=True, reach=3.0)
    c.corner_heap("S", S("sack_l", "sack_m", "sack_s", "apples"), n=4)
    c.corner_heap("W", S("crate", "dcrate", "barrel"), n=3)
    c.corner_heap("E", S("apples", "sack_m"), n=2)
    c.lights_balanced(2)
    c.hangings(r"^Painting[12]$|^GreenTapestry\d$", most=2)


COMPOSERS = {"living_room": living_room, "dwelling": living_room, "kitchen": kitchen, "shop": shop, "tavern": tavern,
             "dining_hall": dining_hall, "mess_hall": dining_hall, "ogre_hall": ogre_hall, "gallery": gallery,
             "hall": hall, "throne_room": throne_room, "solar": solar, "study": study, "library": library,
             "infirmary": infirmary, "herbalist": herbalist}


def compose(f, plan, need):
    """The civic slot: the room composed by its type's composer. Returns {family: pieces placed}."""
    fn = COMPOSERS.get(f.kind)
    if not fn: return Counter()
    before = Counter(f._fam_n)
    c = Ctx(f)
    f._civic = c
    fn(c, plan)
    return Counter({k: v - before.get(k, 0) for k, v in f._fam_n.items() if v - before.get(k, 0) > 0})


def finish(f, need):
    """The last pass of a civic room: statues face into the room, rugs and tables audited, lights where the composer set
    none (a light per 40 tiles at least, in the corners first)."""
    c = getattr(f, "_civic", None) or Ctx(f)
    f.audit_rugs()
    f.face_statues()
    want = 0 if f.ident.get("dark") else min(OBJ.light_cap(len(f.room.tiles)), max(2, c.tiles // 40))
    if len(c.lights) < want: c.lights_balanced(want)
    f.civic_log = list(c.log)


def _traced(name, fn):
    def w(self, *a, **k):
        r = fn(self, *a, **k)
        if isinstance(r, tuple) and r and isinstance(r[0], dict): show = r[0].get("type")
        elif isinstance(r, dict): show = (r.get("obj") or {}).get("type")
        elif isinstance(r, list): show = len(r)
        else: show = r
        self.log.append(f"{name}{tuple(x for x in a if isinstance(x, (str, int, float)))} -> {show}")
        return r
    return w


if DEBUG:
    for _n in ("focal", "flank", "flank_lights", "run_pair_from", "line", "row", "hangings", "table_set", "heap",
               "corner_heap", "corner_set", "corner_lights", "front_pair", "centred_on", "wall_set"):
        setattr(Ctx, _n, _traced(_n, getattr(Ctx, _n)))


def why(f, t, u, v, blocking=True):
    """Debug: why try_put would refuse t at (u, v)."""
    hu, hv = f.half(t)
    if not f.g.fits(u, v, hu, hv, blocking, False):
        pts = [(u + a * hu, v + b * hv) for a in (-1, 0, 1) for b in (-1, 0, 1)]
        if not all(f.g.inside(*p) for p in pts): return "outside"
        if min(f.g.wall_dist(*p) for p in pts) < 0.25: return "wall"
        if not f.g.before_back_wall(u, v): return "wallcell"
        for du, dv in f.g.doors:
            if math.hypot(u - du, v - dv) < F.DOOR_CLEAR + max(hu, hv): return "door"
        for z in f.g.zones:
            if u + hu > z[0] and u - hu < z[1] and v + hv > z[2] and v - hv < z[3]: return f"zone{tuple(round(x,1) for x in z)}"
        return "overlap"
    k0 = Counter(f.kb_refused)
    if not f._kb_ok(t, u, v, hu, hv, blocking, "floor"):
        return "kb " + str(Counter(f.kb_refused) - k0)
    if not f._one_of_a_kind_ok(t, u, v): return "one_of_a_kind"
    if blocking and not f.g.reachable_ok((u, v, hu, hv, True, "floor")): return "reach"
    if f.coverage(f.footprint(t)) > f.cover_max: return "cover"
    return "ok?"
