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
        self._corners = {}
        self._wall_of = {}
        self.hang_pat = None            # the room's hangings (finish hangs its bare walls with them)
        self.wall_pat = None            # a floor piece for a back wall the hangings could not dress
        self.s_makers = None            # what the S corner takes when the composition left it bare
        self.log = []

    # ---- geometry ------------------------------------------------------------------------------------------------
    def wall(self, name):
        return self.runs[name][0] if self.runs.get(name) else None

    def name_of(self, r):
        return NAME[r["side"]]

    CORNER_DIR = {"N": (-1, 1), "E": (1, 1), "S": (1, -1), "W": (-1, -1)}     # the corner's direction in (u, v)

    def corner_uv(self, corner, d_u, d_v=None):
        """A point `d_u`, `d_v` units in from both walls of a room corner (N, E, S, W): the corner of the room's own
        floor (an L-shaped room's notch is no corner), its walls' lines half a unit past its extreme cell."""
        d_v = d_u if d_v is None else d_v
        su, sv = self.CORNER_DIR[corner]
        if corner not in self._corners:
            x, y = max(self.f.g.cells, key=lambda c: su * (c[0] + c[1] + 1) + sv * (c[0] - c[1]))
            self._corners[corner] = (x + y + 1 + su * 1.0, x - y + sv * 1.0)
        cu, cv = self._corners[corner]
        return cu - su * d_u, cv - sv * d_v

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

    def pick_once(self, pat, fam=None):
        """The room's one type for a pattern (one kind of column, of statue, of bench to a room)."""
        if pat not in self.set_type: self.set_type[pat] = self.pick(pat, fam)
        return self.set_type[pat]

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

    def on_wall(self, t0, r, a, fam=None, extra=0.0, blocking=True, pairing=False, touch=False):
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
            o = f.try_put(t, u, v, blocking=blocking and fam not in F.NON_BLOCKING, snug=True, touch=touch)
        finally:
            f._pairing = saved
        if not o: return None
        key = (r["line"], r["coord"])
        e = (key, a - ha, a + ha)
        f.wall_used.append(e)
        if fam in F.TALL_FAMS: f.wall_tall.append(e)
        f.anchors.append((u, v))
        self._wall_of[id(o)] = (e, (u, v))
        return o, (u, v), ha, hp

    def drop(self, o):
        """Takes a piece out again, with the wall stretch it claimed (a pair that could not be completed)."""
        f = self.f
        e = self._wall_of.pop(id(o), None)
        if e:
            for seq in (f.wall_used, f.wall_tall):
                if e[0] in seq: seq.remove(e[0])
            if e[1] in f.anchors: f.anchors.remove(e[1])
        f._remove(o)

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
                a1 = self.on_wall(t0, r, p["along"] - off, fam, pairing=pairing, blocking=blocking, touch=k > 0)
                a2 = a1 and self.on_wall(t0, r, p["along"] + off, fam, pairing=pairing, blocking=blocking, touch=k > 0)
                if a1 and a2:
                    got += 2; done = True; break
                if a1: self.drop(a1[0])
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
                    if self.on_wall(t0, r, a, fam, pairing=True, touch=True): got += 1
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
                for o in got: self.drop(o)
        return 0

    def hangings(self, pat=None, walls=BACK, step=3.6, most=6, first=None):
        """The back walls hung: each bare stretch of the NE and NW walls takes hangings at even steps, mirrored about
        its middle, two kinds alternating (A B A, A B C B A: two of one kind to a wall at most, kit/objects.py)."""
        f = self.f
        if pat and not self.hang_pat: self.hang_pat = pat
        if pat: types = self.types(pat)
        else: types = sorted(f.decor_theme() or {})
        if not types: return 0
        # tapestries of one colour to a room (a wall of mixed colours reads as random)
        cols = sorted({m.group(1) for t in types for m in [re.match(r"^(Blue|Red|Green|White)Tapestry", t)] if m})
        if len(cols) > 1:
            col = self.set_type.setdefault("tapestry colour", self.rng.choice(cols))
            types = [t for t in types if not re.match(r"^(Blue|Red|Green|White)Tapestry", t) or t.startswith(col)]
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
        segs = [(r["lo"] + 0.6, r["hi"] - 0.6)]
        cuts = []
        for du, dv in f.g.doors:
            perp, along = (du, dv) if r["line"] == "/" else (dv, du)
            if abs(perp - r["coord"]) < 1.6: cuts.append((along - F.DOOR_CLEAR - 0.6, along + F.DOOR_CLEAR + 0.6))
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
            if x: self.drop(x[0])
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
    def bare_spot(self, margin=1.2, skip=()):
        """The point of the floor farthest from every piece and wall (none within 2.5 units of a point in `skip`):
        (u, v, distance), or None."""
        f = self.f
        pieces = [(p[0], p[1], p[2], p[3]) for p in f.g.placed if p[4] and p[5] != "wall"]
        best = None
        for (x, y) in list(f.g.cells)[::2]:
            u, v = x + y + 1.0, float(x - y)
            if not f.g.inside(u, v): continue
            dw = f.g.wall_dist(u, v)
            if dw < margin + 0.8: continue
            if any(abs(u - du) < 2.6 and abs(v - dv) < 2.6 for du, dv in f.g.doors): continue
            if any(math.hypot(u - a, v - b) < 2.5 for a, b in skip): continue
            dp = min([max(abs(u - a) - hu, abs(v - b) - hv, 0.0) for a, b, hu, hv in pieces] or [99.0])
            d = min(dp, dw - 0.6)
            if best is None or d > best[2]: best = (u, v, d)
        return best

    def mirror_pt(self, uv):
        """The point mirrored across the room's long middle line (its axis of symmetry along its length)."""
        cu, cv = self.centre()
        if (self.uS - self.uN) >= (self.vE - self.vW): return uv[0], 2 * cv - uv[1]
        return 2 * cu - uv[0], uv[1]

    def heap_ok(self, uv):
        """Stock may heap here: not before a chest, hearth or stove, not on a carpet."""
        f = self.f
        if f._before_anchor(*uv): return False
        return not any(b[0] <= uv[0] <= b[1] and b[2] <= uv[1] <= b[3] for b in f.carpet_boxes)

    def fill_bare(self, makers, most=3, over=3.2, mirror=False):
        """Groups where the floor is still bare: while some point lies `over` units from everything, the first maker that
        fits there (each a function (ctx, (u, v)) -> pieces) puts its group there; mirror: its twin across the room's
        long middle line too, both or neither (a point on that line stands alone)."""
        f = self.f
        got, tried = 0, []
        for _ in range(most + 6):
            if got >= most: break
            b = self.bare_spot(skip=tried)
            if not b or b[2] < over: break
            u, v, d = b
            tried.append((u, v))
            for mk in makers:
                n0 = len(f.objects)
                n = mk(self, (u, v))
                if n and mirror:
                    mu, mv = self.mirror_pt((u, v))
                    if math.hypot(mu - u, mv - v) > 3.0:
                        if not mk(self, (mu, mv)):
                            for x in f.objects[n0:]: f._remove(x)
                            n = 0
                        else:
                            tried.append((mu, mv))
                if n:
                    got += 1
                    if DEBUG: self.log.append(f"   fill_bare at {u:.1f},{v:.1f} (bare {d:.1f}): {getattr(mk, '__name__', mk)} {n}")
                    break
        return got

    def lights_balanced(self, want):
        """Floor lights in matching pairs: the side corners, then the front and back corners. Returns the lights."""
        for pair in (("W", "E"), ("N", "S")):
            if len(self.lights) >= want: break
            for d in (0.9, 1.5, 2.2):
                if self.corner_lights(pair, d): break
        return len(self.lights)


# ---- per type --------------------------------------------------------------------------------------------------------
TABLE_ROUND = r"^RoundTable[12]$"
TABLE_SMALL = r"^SquareTable[12]$|^RoundTable[12]$"
STOCK = dict(barrel=r"^Barrel2?$", water=r"^WaterBarrel$", crate=r"^Crate[12]$", dcrate=r"^DarkCrate[12]$",
             sack_l=r"^SackChestLarge[12]$", sack_m=r"^SackChestMedium[12]$", sack_s=r"^SackChestSmall[12]$",
             apples=r"^TraderAppleCrate$", tools=r"^BarrelWithTools[12]$", steel=r"^CrateSteel[1-4]$",
             steelb=r"^BarrelSteel[12]$", piled=r"^PiledBarrels[1-4]$", cask=r"^LargeBarrel[12]$")
VASE = r"^StatueVase[1-5](N|S|E|W|NE|NW|SE|SW)$"


def S(*keys):
    return [STOCK[k] for k in keys]


# ---- makers: one group at a point of the open floor (Ctx.fill_bare) --------------------------------------------------
def mk_sitting(c, uv):
    """A small table with two chairs on a rug."""
    return c.table_set(uv, TABLE_SMALL, 2, rug=True, reach=1.2)


def mk_round4(c, uv):
    """A round table ringed by four chairs on a rug."""
    return c.table_set(uv, r"^RoundTable[12]$", 4, rug=True, reach=1.2)


def mk_dining(c, uv):
    """A table of food with four chairs, on a carpet."""
    return c.table_set(uv, r"^RoundTableWithFood$|^RoundTable[12]$", 4, carpet=(3, 3), reach=1.2)


def mk_heap(*keys, n=4):
    def mk(c, uv):
        return c.heap(uv, S(*keys), n=n) if c.heap_ok(uv) else 0
    mk.__name__ = "heap:" + "+".join(keys)
    return mk


def mk_one(pat, name=None):
    def mk(c, uv):
        t = c.pick(pat)
        return 1 if t and c.put(t, *uv) else 0
    mk.__name__ = name or f"one:{pat}"
    return mk


def mk_worktable(c, uv):
    """A work table with two stools and a crate of apples or a sack by it."""
    n = c.table_set(uv, r"^Table4$|^RoundTableWithFood$", 2, seat_pat=r"Stool", reach=1.2)
    if n:
        c.heap((uv[0] + 2.2, uv[1] + 0.0), S("apples", "sack_m"), n=1)
    return n


# ---- the private rooms -----------------------------------------------------------------------------------------------
def living_room(c, plan):
    """The hearth centred on a back wall between mirrored shelves, a rug and a bench before it; the household's table
    centred on its carpet in the middle; the chest centred on the other back wall between a pair of shelves (or the
    bed with a nightstand each side in a dwelling); lights in matching corners; a sitting set in the S corner, mixed
    stock in the front corners, benches mirrored on a front wall; groups where the floor is still bare; the back
    walls hung."""
    f = c.f
    c.wall_pat = r"^LogShelvesFull\d$" if f.kind == "dwelling" else r"^Bookcase\d$|^LogShelvesFull\d$"
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
            c.flank(anchor_of(c, ch, c.wall(ow)), r"^Bookcase\d$|^LogShelvesFull\d$", gap=1.0, fam="shelves")
    mb = c.middle_box()
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    if not c.table_set((cu, cv), r"^RoundTableWithFood$|^RoundTable[12]$", 4,
                       carpet=(4, 4) if c.tiles >= 100 else (3, 3) if c.tiles >= 45 else (2, 2)):
        c.table_set((cu, cv), r"^RoundTableWithFood$|^RoundTable[12]$", 3, rug=True, reach=4.0) or \
            c.table_set((cu, cv), r"^RoundTableWithFood$|^RoundTable[12]$", 2, reach=4.0)
    c.lights_balanced(2 if c.tiles < 70 else 4) or c.flank_lights(hearth)
    if c.tiles >= 36: c.corner_set("S", TABLE_SMALL, 2)
    else: c.corner_heap("S", S("barrel", "water"), n=2)
    c.corner_heap("W", S("barrel", "sack_m", "crate"), n=3)
    c.corner_heap("E", S("water", "crate", "sack_s"), n=2 if c.tiles < 70 else 3)
    if c.tiles >= 60: c.front_pair(r"^Bench\d$|^CushionedBench\d$", "bench", wall="SW" if c.rng.random() < 0.5 else "SE")
    c.fill_bare([mk_sitting, mk_round4], most=c.tiles // 45, over=3.0)
    c.hangings(walls=BACK, most=3)


def bed_set(c, wall):
    """The bed centred on a wall, headboard to it, a nightstand each side at the RM-BEDROOM-10 standard (a hand's width
    off the bed), the chest at its foot."""
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
        f.wall_used.append(((r["line"], r["coord"]), a - ha - 1.4, a + ha + 1.4))
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
            opp = {"/|BR": "/|TL", "/|TL": "/|BR", "\\|BL": "\\|TR", "\\|TR": "\\|BL"}[r["side"]]
            for t2 in [f.along_variant(ct, opp) or ct, ct]:
                h2 = f.half(t2)
                hp2 = h2[0] if r["line"] == "/" else h2[1]
                if c.put(t2, *f._uv_on(r, foot + hp2 + 0.35, a)): break
        return 1
    return 0


def solar(c, plan):
    """The lord's chamber in two ends: the bed centred on one back wall with a nightstand each side and the chest at
    its foot; the hearth centred on the other back wall between bookcases, a sitting set on a carpet before it; the
    desk centred with its chair; a dining set centred on its carpet; lights in matching corners; benches and urns
    mirrored on the front walls; the S corner's set; groups where the floor is still bare; tapestries."""
    f = c.f
    c.wall_pat = r"^Bookcase\d$"
    walls = list(BACK); c.rng.shuffle(walls)
    hearth = c.focal("fireplace", clear=2.8, wall=walls[0])
    if hearth:
        c.run_pair_from(hearth, r"^Bookcase\d$", fam="shelves", most=2 if c.tiles < 180 else 3)
        r = hearth["run"]
        uv = f._uv_on(r, 6.0, hearth["along"])
        c.table_set(uv, TABLE_SMALL, 2, carpet=(3, 3), reach=1.5) or c.table_set(uv, TABLE_SMALL, 2, rug=True)
    bed_set(c, walls[1])
    for w in list(FRONT) + walls:
        if not c.wall(w): continue
        d = c.centred_on(w, r"^Desk[12]$", "desk")
        if d:
            f.seats_around(d[1], d[0]["type"], 1)
            break
    c.lights_balanced(4)
    c.corner_set("S", TABLE_SMALL, 2)
    c.corner_heap("W", S("sack_m", "crate"), n=2)
    c.corner_heap("E", S("crate", "sack_s"), n=2)
    wall_pair(c, "SE", r"^Bench\d$|^CushionedBench\d$", 0.25, "bench")
    wall_pair(c, "SW", VASE, 0.2)
    c.fill_bare([mk_dining, mk_sitting, mk_round4], most=max(2, c.tiles // 50), over=3.0, mirror=True)
    c.hangings(r"^(Blue|Red|White|Green)Tapestry\d$|^Painting[12]$", most=4)


def study(c, plan):
    """The desk centred on a back wall with its chair, bookcases end to end either side of it; the other back wall
    lined with bookcases round a centred chest; the meeting table centred on its carpet; urns in matching corners; the
    S corner's reading set; lights flanking the desk; groups where the floor is still bare."""
    f = c.f
    c.wall_pat = r"^Bookcase\d$"
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
    c.lights_balanced(2)
    c.corner_set("S", TABLE_SMALL, 2)
    if c.tiles >= 60:
        t = c.pick(VASE)
        if t: c.put_all([(t, *c.corner_uv("W", 1.3)), (t, *c.corner_uv("E", 1.3))], pairing=True)
    if c.tiles >= 90: wall_pair(c, "SE", r"^Statue2[aceg]$", 0.3, "statue")
    c.fill_bare([mk_sitting], most=c.tiles // 50, over=3.0, mirror=True)
    c.hangings(r"^Painting[12]$|^(Blue|Red|Green)Tapestry\d$", most=3)


def library(c, plan):
    """Bookcases end to end along both back walls (and the front walls in a big library); stacks of bookcases in
    mirrored rows either side of an aisle down the middle of a big one; the reading table centred on its carpet; the
    desk centred with its chair; lights in matching corners; reading sets where the floor is still bare."""
    f = c.f
    c.wall_pat = r"^Bookcase\d$"
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
    c.lights_balanced(4 if c.tiles >= 120 else 2)
    if c.tiles >= 140:
        for w in FRONT: c.line(c.wall(w), r"^Bookcase\d$", "shelves", most=8)
    if c.tiles >= 100: stacks(c)
    mb = c.middle_box(walk=1.2)
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    c.table_set((cu, cv), r"^OvalTable[12]$|^RoundTable[12]$", 4, carpet=(3, 3)) or \
        c.table_set((cu, cv), TABLE_SMALL, 2, rug=True, reach=4.0)
    c.corner_set("S", TABLE_SMALL, 2)
    c.fill_bare([mk_sitting, mk_round4], most=c.tiles // 50, over=3.0, mirror=True)
    c.hangings(r"^Painting[12]$|^(Blue|Red|Green)Tapestry\d$", most=2)


def stacks(c):
    """A big library's stacks: rows of bookcases end to end standing free, facing the camera (the NE or NW wall's
    variant), in mirrored blocks either side of an aisle across the middle, rows evenly spaced. Returns the pieces."""
    f = c.f
    mb = c.middle_box(walk=1.4)
    du, dv = mb[1] - mb[0], mb[3] - mb[2]
    # the rows run along the longer side's wall: rows of constant u (a NW-wall bookcase) or of constant v (NE)
    rows_along_v = dv >= du
    wall = c.wall("NW" if rows_along_v else "NE")
    if not wall: return 0
    t0 = c.pick(r"^Bookcase\d$")
    if not t0: return 0
    t = f.side_variant(t0, wall, "shelves") or t0
    hu, hv = f.half(t)
    ha = hv if rows_along_v else hu                    # half its length along the row
    hp = hu if rows_along_v else hv
    span_a = (mb[2], mb[3]) if rows_along_v else (mb[0], mb[1])
    span_p = (mb[0], mb[1]) if rows_along_v else (mb[2], mb[3])
    aisle = 3.0
    half_len = (span_a[1] - span_a[0] - aisle) / 2
    per = int((half_len + 0.05) / (2 * ha + 0.05))
    if per < 2: return 0
    per = min(per, 4)
    step = 3.6
    n_rows = max(1, min(4, int((span_p[1] - span_p[0]) / step)))
    pc = (span_p[0] + span_p[1]) / 2
    ac = (span_a[0] + span_a[1]) / 2
    got = 0
    for i in range(n_rows):
        p = pc + (i - (n_rows - 1) / 2) * step
        items = []
        for side in (-1, 1):
            for k in range(per):
                a = ac + side * (aisle / 2 + ha + k * (2 * ha + 0.05))
                items.append((t, p, a) if rows_along_v else (t, a, p))
        res = c.put_all([(tt, u, v, dict(touch=True)) for tt, u, v in items], pairing=True)
        if res: got += len(res)
    return got


# ---- the work rooms --------------------------------------------------------------------------------------------------
def kitchen(c, plan):
    """The hearth centred on a back wall on its stones, the cooking pot or the stove a step off it; provisions lining
    the other back wall end to end; the work table with its food and stools centred in the middle; lights in matching
    corners; stores heaped in the front corners, each a mix; water barrels mirrored on a front wall; more work tables
    and heaps where the floor is still bare; a trophy or two."""
    f = c.f
    c.wall_pat = r"^LogShelvesFull\d$"
    c.s_makers = [lambda c_, uv: c_.corner_heap("S", S("sack_l", "barrel", "crate"), n=3)]
    hearth = c.focal("fireplace", clear=2.6)
    other = [w for w in BACK if not hearth or c.name_of(hearth["run"]) != w]
    if hearth:
        stove = c.pick(r"^CauldronAnimated$|^Stove0[1-5]$", "stove")
        if stove:
            r = hearth["run"]
            hs = max(f.half(stove))
            for side in (1, -1):
                res = c.on_wall(stove, r, hearth["along"] + side * (hearth["ha"] + 1.9 + hs), "stove", extra=0.35)
                if res:
                    f.g.zones.append(f.front_zone(r, *res[1], res[2], res[3], 1.4))
                    break
        c.flank(hearth, r"^LogShelvesFull\d$", gap=2.0 + 2 * 0.9, fam="shelves")
    if other:
        c.line(c.wall(other[0]), r"^LogShelvesFull\d$", "shelves", most=6 if c.tiles >= 60 else 4)
    mb = c.middle_box()
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    c.table_set((cu, cv), r"^RoundTableWithFood$|^Table4$", 3, seat_pat=r"Stool", reach=3.0) or \
        c.table_set((cu, cv), r"^RoundTableWithFood$", 2, seat_pat=r"Stool", reach=3.5)
    c.lights_balanced(2)
    c.corner_heap("S", S("sack_l", "sack_m", "apples", "sack_s"), n=4)
    c.corner_heap("W", S("barrel", "water", "crate"), n=3 if c.tiles < 60 else 4)
    c.corner_heap("E", S("crate", "apples", "barrel"), n=3)
    front_heaps(c, ("SE", "SW"), [S("tools", "dcrate", "sack_m"), S("water", "barrel", "sack_s")], n=3)
    c.fill_bare([mk_worktable, mk_heap("barrel", "sack_l", "crate", "sack_s")], most=c.tiles // 35, over=2.8)
    c.hangings(r"^WallTrophy(Bear|Moose|MountainLion)[12]$|^Painting1$", walls=tuple(other) or BACK, most=2)


def front_heaps(c, walls, mixes, n=3, at=(0.35, 0.65)):
    """Heaps of mixed stock on the front walls, a mirrored pair on each (at the shares `at` of its main run)."""
    got = 0
    for w in walls:
        r = c.wall(w)
        if not r or r["hi"] - r["lo"] < 9: continue
        mix = mixes[got % len(mixes)]
        for frac in at:
            a = r["lo"] + (r["hi"] - r["lo"]) * frac
            uv = c.f._uv_on(r, 1.0, a)
            if c.heap_ok(uv): got += c.heap(uv, mix, n=n, toward=c.f._uv_on(r, 0.0, a)) > 0
    return got


def shop(c, plan):
    """The trader's counter out from a back wall facing the way in, the keeper behind it with his goods mirrored either
    side of him; the trade's own goods lining the other back wall; lights flanking the counter; stock heaped in the S
    corner and the front corners and mirrored on the front walls; a mirrored display before the counter in a big
    shop; the walls hung with the trade."""
    f = c.f
    c.s_makers = [lambda c_, uv: c_.corner_heap("S", S("crate", "barrel", "sack_m"), n=3)]
    trade = c.rng.choice(("armourer", "apothecary", "general"))
    counter = f.place_counter("counter_shop", 2.2, 1.8)
    if counter:
        r = counter["run"]
        wa = counter["along"]
        if trade == "apothecary": pat, fam = r"^PotionShelves\d$", "shelves"
        elif trade == "armourer": pat, fam = r"^TraderShelves\d$|^TraderHelmShelf\d$", "shop_rack"
        else: pat, fam = r"^TraderShelves\d$", "shop_rack"
        back = dict(obj=None, run=r, uv=f._uv_on(r, 0.5, wa), along=wa, ha=counter["ha"] * 0.6, hp=0.5)
        c.flank(back, pat, gap=0.4, fam=fam, n_each=2)
        c.flank_lights(dict(counter, hp=counter["hp"]), gap=0.5, before=0.3)
        other = [w for w in BACK if w != c.name_of(r)]
    else:
        other = list(BACK)
    ow = c.wall(other[0]) if other else None
    if trade == "apothecary":
        c.line(ow, r"^PotionShelves\d$|^Bookcase\d$", "shelves", most=8, kinds=2)
        hang = r"^Painting[12]$|^GreenTapestry\d$"
        heaps = [S("crate", "sack_m", "barrel"), S("apples", "sack_s", "crate"), S("dcrate", "sack_l")]
    elif trade == "armourer":
        c.row(ow, r"^Trader(ArmorRack|PoleArm|BowRack)\d$", 3 if c.tiles >= 70 else 2, "shop_rack")
        hang = r"^TraderShieldWallHanging\d$|^TraderCrossedWeapons\d$|^TraderHangingSwords\d$"
        heaps = [S("steel", "steelb", "crate"), S("crate", "barrel", "steel"), S("tools", "dcrate")]
    else:
        c.line(ow, r"^TraderShelves\d$", "shop_rack", most=4)
        hang = r"^WallTrophy(Bear|Moose|MountainLion)[12]$|^TraderShieldWallHanging\d$"
        heaps = [S("steel", "barrel", "sack_l"), S("apples", "crate", "steelb"), S("sack_m", "tools", "dcrate")]
    c.lights_balanced(2 if c.tiles < 100 else 4)
    c.corner_heap("S", heaps[0], n=4)
    c.corner_heap("W", heaps[1], n=3)
    c.corner_heap("E", heaps[2], n=3)
    front_heaps(c, ("SE", "SW"), heaps, n=3)
    # the walk from the door to the counter lined with a mirrored display of the trade (racks, jars, stock)
    if counter and c.tiles >= 60:
        ax = dict(run=counter["run"], mid=counter["along"], depth=f._depth_of(counter["run"]))
        f.aisle = dict(run=counter["run"], mid=counter["along"], half=1.4, first=2.0, far=ax["depth"], door=c.door)
        if trade == "armourer":
            inner, outer = [r"^TraderArmorRack[12]$", r"^TraderPoleArm[1-4]$"], [r"^TraderBowRack[12]$"]
        elif trade == "apothecary":
            inner, outer = [r"^FairyJar$", r"^TraderAppleCrate$"], [r"^SackChestLarge[12]$"]
        else:
            inner, outer = [r"^CrateSteel[1-4]$", r"^TraderAppleCrate$", r"^BarrelSteel[12]$"], [r"^Barrel2?$"]
        stations(c, ax, inner, outer, first=counter["hp"] + 2.2 + 3.4, step=3.4, inner_off=2.2, end=3.0)
        f.aisle = None
    makers = [mk_heap("crate", "barrel", "sack_m", n=3)] if trade != "armourer" else [mk_one(r"^TraderArmorRack[12]$", "rack")]
    c.fill_bare(makers, most=max(1, c.tiles // 60), over=3.4, mirror=True)
    c.hangings(hang, walls=tuple(BACK), most=3)
    f._trade = {}
    c.log.append(f"trade {trade}")


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


def cot_row(c, r, lo, hi, gap=2.2, most=8):
    """Cots evenly spaced along wall run r's stretch lo..hi, heads to the wall, a nightstand between neighbours."""
    f = c.f
    t = f._variant_for_wall("Cot", r, across=True) or "Cot1"
    hu, hv = f.half(t)
    ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
    n = max(2, min(most, int((hi - lo) / (2 * ha + gap))))
    step = (hi - lo) / n
    got = 0
    for k in range(n):
        a = lo + step * (k + 0.5)
        uv = f._uv_on(r, hp + 0.3, a)
        o = c.put_all([(t, *uv)], pairing=True)
        if o:
            f.beds.append((o[0], r, uv)); got += 1
    ns = f.variant_for_side("Nightstand", r["side"])
    if ns:
        nh = f.half(ns)
        for k in range(n - 1):
            a = lo + step * (k + 1)
            c.put_all([(ns, *f._uv_on(r, (nh[0] if r["line"] == "/" else nh[1]) + 0.3, a))], pairing=True)
    if got: f.wall_used.append(((r["line"], r["coord"]), lo, hi))
    return got


def infirmary(c, plan):
    """A row of cots evenly spaced along the longest front wall with a nightstand between neighbours (a second row on
    the other front wall in a big infirmary); the healer's table facing the way in with the healer behind it; a pair
    of potion shelves centred on a back wall with bookcases end to end either side; the cauldron on its own stretch,
    clear of the beds; supplies heaped in the corners; hangings of one colour."""
    f = c.f
    c.wall_pat = r"^Bookcase\d$"
    c.s_makers = [lambda c_, uv: c_.corner_heap("S", S("sack_m", "crate"), n=2)]
    fronts = sorted((w for w in FRONT if c.wall(w)), key=lambda w: c.wall(w)["lo"] - c.wall(w)["hi"])
    for w in fronts[:2 if c.tiles >= 120 else 1]:
        r = c.wall(w)
        for lo, hi in sorted(c.free(r, pad=0.4), key=lambda s: s[0] - s[1])[:1]:
            # keep the S corner for the other row: the stretch starts two units off it
            cot_row(c, r, lo + 0.6, hi - 0.6)
    desk = counter_for(c, r"^Table[14]$|^SquareTable[12]$|^TraderDesk[1-6]$")
    if desk:
        c.flank_lights(desk, gap=0.4, before=0.2)
    ow = [w for w in BACK if not desk or c.wall(w) is not desk["run"]]
    pot = c.centred_on(ow[0], r"^PotionShelves\d$", "shelves") if ow else None
    if pot:
        p = anchor_of(c, pot, c.wall(ow[0]))
        c.flank(p, r"^PotionShelves\d$", gap=0.1, fam="shelves")
        c.flank(dict(p, ha=p["ha"] + 2 * pot[2] + 0.2), r"^Bookcase\d$", gap=0.1, fam="shelves", n_each=3)
    if desk:
        r = desk["run"]
        back = dict(obj=None, run=r, uv=f._uv_on(r, 0.5, desk["along"]), along=desk["along"], ha=desk["ha"] * 0.6, hp=0.5)
        c.flank(back, r"^Bookcase\d$", gap=0.4, fam="shelves", n_each=2)
    if c.tiles >= 100:
        across = {"SE": "NW", "SW": "NE"}.get(fronts[0]) if fronts else None
        r = c.wall(across) if across else None
        if r:
            for lo, hi in sorted(c.free(r, pad=0.6), key=lambda s_: s_[0] - s_[1])[:1]:
                if hi - lo >= 9: cot_row(c, r, lo + 0.4, hi - 0.4, most=5)
    caul = c.pick(r"^CauldronAnimated$")
    if caul:
        done = False
        for w in list(BACK) + list(FRONT):
            r = c.wall(w)
            if not r or done: continue
            for lo, hi in sorted(c.free(r, pad=1.0), key=lambda s: s[0] - s[1])[:1]:
                if c.on_wall(caul, r, (lo + hi) / 2, "stove", extra=0.5): done = True
    c.lights_balanced(2 if c.tiles < 120 else 4)
    c.corner_heap("W", S("sack_m", "crate", "sack_s"), n=3)
    c.corner_heap("E", S("crate", "water", "sack_m"), n=3)
    c.corner_heap("N", S("crate", "sack_s"), n=2)
    c.fill_bare([mk_heap("crate", "sack_m", "sack_s", n=3), mk_sitting], most=c.tiles // 60, over=3.2, mirror=True)
    c.hangings(r"^(White|Blue|Green)Tapestry\d$", most=3)


def herbalist(c, plan):
    """The herbalist's counter facing the way in with her behind it; potion shelves end to end either side of her
    along the back wall; the cauldron centred on the other back wall between books of remedies; glowing jars mirrored
    on a front wall; the work table with stools; sacks of herbs, crates and apples heaped in the corners and mirrored
    on the front walls."""
    f = c.f
    c.wall_pat = r"^Bookcase\d$"
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
    c.lights_balanced(2)
    c.front_pair(r"^FairyJar$", None, wall="SW")
    mb = c.middle_box()
    c.table_set(((mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2), r"^Table4$|^SquareTable[12]$", 2, seat_pat=r"Stool",
                rug=True, reach=3.0)
    c.corner_heap("S", S("sack_l", "sack_m", "sack_s", "apples"), n=4)
    c.corner_heap("W", S("crate", "dcrate", "barrel"), n=3)
    c.corner_heap("E", S("apples", "sack_m", "crate"), n=3)
    front_heaps(c, ("SE",), [S("sack_m", "sack_s", "apples")], n=3)
    c.fill_bare([mk_heap("sack_l", "sack_m", "apples", n=3), mk_sitting], most=c.tiles // 45, over=2.8)
    c.hangings(r"^Painting[12]$|^GreenTapestry\d$", most=2)


# ---- shared arrangements ---------------------------------------------------------------------------------------------
def axis(c, back_first=False):
    """The room's main axis: the wall run across from the main door and the point along it in line with the door, the
    room's depth from that wall. dict(run, mid, depth) or None. back_first: the far wall must be a back wall (a hearth,
    a desk, a throne), else the longest back wall's middle."""
    f = c.f
    r = c.far_wall()
    if r and (not back_first or c.name_of(r) in BACK):
        # in line with the door when it opens near the middle of its wall, else the far wall's middle (a door by a
        # corner would put the whole composition against one side wall)
        centre = (r["lo"] + r["hi"]) / 2
        mid = c.door["along"] if abs(c.door["along"] - centre) <= 0.2 * (r["hi"] - r["lo"]) else centre
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
    if DEBUG and not got:
        x = c.put(t, *a, **kw)
        c.log.append(f"   mirrored {t}: first {'ok' if x else why(c.f, t, *a)}, second {why(c.f, t, *b)}")
        if x: c.f._remove(x)
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
        if x: c.drop(x[0])
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
    before it and shelves of crockery mirrored either side; lights in matching corners; the round tables in an even
    grid centred on one carpet; long tables mirrored by a front wall; kegs heaped in the S corner and mirrored on the
    front walls; round sets where the floor is still bare; trophies at even steps along the back walls."""
    f = c.f
    c.wall_pat = r"^LogShelvesFull\d$"
    c.s_makers = [lambda c_, uv: c_.corner_heap("S", S("barrel", "piled"), n=3)]
    f.build_bar()
    hearth = c.focal("fireplace", clear=2.8)
    if hearth:
        f.rug_before(hearth)
        c.flank(hearth, r"^LogShelvesFull\d$", gap=1.4, fam="shelves")
    c.lights_balanced(4)
    mb = c.middle_box(walk=1.4)
    mk = exact_set(r"^RoundTable[12]$", 4, seat_pat=r"Stool", gap=0.45)
    step = 5.0
    nx, ny = max(1, min(3, int((mb[1] - mb[0]) / step) + 1)), max(1, min(3, int((mb[3] - mb[2]) / step) + 1))
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
        got = grid_sets(c, (cu, cu, cv, cv), mk, gx, gy, step, step)
        if got: break
    if got:
        bx = pieces_box(c, n0)
        if bx: carpet_box(c, bx, pad=0.8)
    lt = exact_set(r"^Table[1-4]$", 2, seat="bench")
    for w in (("SE", "SW") if c.rng.random() < 0.5 else ("SW", "SE")):
        r = c.wall(w)
        if not r: continue
        placed = False
        for lo, hi in sorted(c.free(r, pad=0.5), key=lambda s: s[0] - s[1])[:1]:
            for frac in (0.3, 0.25, 0.35, 0.2):
                a1, a2 = lo + (hi - lo) * frac, hi - (hi - lo) * frac
                n1 = len(f.objects)
                if lt(c, f._uv_on(r, 2.6, a1)) and lt(c, f._uv_on(r, 2.6, a2)):
                    placed = True; break
                for x in f.objects[n1:]: f._remove(x)
        if placed: break
    c.corner_heap("S", S("barrel", "piled", "barrel"), n=3)
    front_heaps(c, ("SE", "SW"), [S("barrel", "piled"), S("barrel", "water")], n=2)
    c.fill_bare([mk_round4, mk_sitting], most=3, over=3.2, mirror=True)
    c.hangings(r"^WallTrophy(Bear|Moose|MountainLion)[12]$|^TraderShieldWallHanging\d$", most=5)


def dining_hall(c, plan):
    """Composed on the axis from the door: the high table across the far end, seated, a pair of lights flanking it;
    long tables in rows down the axis on one carpet; the hearth centred on a side back wall between crockery shelves;
    casks in the front corners; benches mirrored on a front wall; banners at even steps on the back walls."""
    f = c.f
    c.wall_pat = r"^LogShelvesFull\d$"
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
        # sideboards of crockery mirrored on the axis wall either side of the high table
        c.flank(dict(obj=None, run=r, uv=f._uv_on(r, 0.5, ax["mid"]), along=ax["mid"], ha=3.0, hp=0.5),
                r"^LogShelvesFull\d$", gap=0.5, fam="shelves")
    rows = f.table_rows(max(2, min(6, c.tiles // 30)),
                        seat="bench" if f.kind == "mess_hall" or c.rng.random() < 0.5 else "chair")
    if rows and f.kind != "mess_hall":
        recs = [f._placed_of.get(id(o)) for o, _ in rows]
        recs = [r_ for r_ in recs if r_]
        if recs:
            carpet_box(c, (min(r_[0] - r_[2] for r_ in recs), max(r_[0] + r_[2] for r_ in recs),
                           min(r_[1] - r_[3] for r_ in recs), max(r_[1] + r_[3] for r_ in recs)), pad=1.6)
    c.lights_balanced(4 if c.tiles >= 120 else 2)
    c.corner_heap("W", S("cask", "barrel"), n=2)
    c.corner_heap("E", S("cask", "barrel"), n=2)
    c.corner_heap("S", S("barrel", "piled", "water"), n=3)
    wall_pair(c, "SW" if c.rng.random() < 0.5 else "SE", r"^Bench\d$|^LightBench\d$", 0.2, "bench")
    t = c.pick(VASE)
    if t: c.put_all([(t, *c.corner_uv("N", 1.3))])
    c.fill_bare([mk_sitting, mk_heap("barrel", "water", n=2)], most=c.tiles // 60, over=3.2)
    c.hangings(r"^(Red|Blue|Green|White)Tapestry\d$" if f.kind != "mess_hall" else
               r"^WallTrophy(Bear|Moose|MountainLion)[12]$|^TraderShieldWallHanging\d$", most=5)


def ogre_hall(c, plan):
    """The ogres' feast, minimal but balanced: the fire pit in the middle, crude tables mirrored either side of it
    with their stools, meat between them, sacks and barrels heaped in matching corners, a carcass hung in the N
    corner, skulls on the back walls."""
    f = c.f
    c.wall_pat = r"^Barrel2?$"
    c.s_makers = [lambda c_, uv: c_.corner_heap("S", S("barrel", "sack_l"), n=3)]
    mb = c.middle_box(walk=1.0)
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    for du in (0, 0.5, -0.5, 1.0, -1.0, 1.5):
        pit = c.put("OgreFirePit", cu + du, cv - du) if f.ok_type("OgreFirePit") else None
        if pit:
            cu, cv = cu + du, cv - du
            break
    long_u = (mb[1] - mb[0]) >= (mb[3] - mb[2])
    mk = exact_set(r"^OgreTable[123]$", 3, seat_pat=r"^OgreStool\d$|^OgreBench[34]$", gap=0.35)
    for off in (6.4, 5.8, 7.0, 5.2):
        pts = [(cu - off, cv), (cu + off, cv)] if long_u else [(cu, cv - off), (cu, cv + off)]
        n0 = len(f.objects)
        if mk(c, pts[0]) and mk(c, pts[1]): break
        for x in f.objects[n0:]: f._remove(x)
    if c.tiles >= 150:                    # a second pair across the other axis
        for off in (6.0, 5.4, 6.6):
            pts = [(cu, cv - off), (cu, cv + off)] if long_u else [(cu - off, cv), (cu + off, cv)]
            n0 = len(f.objects)
            if mk(c, pts[0]) and mk(c, pts[1]): break
            for x in f.objects[n0:]: f._remove(x)
    c.lights_balanced(4 if c.tiles >= 150 else 2)
    for corner in ("W", "E"):
        c.corner_heap(corner, S("barrel", "sack_l", "piled", "sack_m"), n=4)
    c.corner_heap("S", S("barrel", "sack_m"), n=2)
    c.corner_heap("N", [r"^OgreHutCarcassBig$|^OgreHutCarcass$"], n=1, d=1.4)
    front_heaps(c, ("SE", "SW"), [S("barrel", "sack_s")], n=2)
    for off in (3.4, 3.0, 3.8):
        pts = [(cu, cv - off), (cu, cv + off)] if long_u else [(cu - off, cv), (cu + off, cv)]
        if c.put_all([("OgreHutMeat", *p) for p in pts]): break
    c.hangings(r"^OgreHutWallSkull[1-4]$", most=4, step=3.6)


# ---- the ceremonial rooms --------------------------------------------------------------------------------------------
def stations(c, ax, inner, outer, first=4.0, step=4.2, inner_off=None, light_inner=False, end=2.4):
    """The ceremonial rooms' rhythm down the axis: at even steps from the far wall toward the door, a mirrored pair
    beside the aisle (inner: columns, statues, braziers in turn) and a mirrored pair by the side walls (outer: benches,
    urns, statues in turn), each pair both or neither. Returns the pieces placed."""
    f = c.f
    r, mid = ax["run"], ax["mid"]
    half = (f.aisle or {}).get("half", 1.5)
    reach = min(mid - (r["lo"] + 1), (r["hi"] - 1) - mid)
    depth_max = ax["depth"] - end
    got, d, k = 0, first, 0
    step = max(step, (depth_max - first) / 6.0)          # six stations at most: a rhythm, not a forest of columns
    if DEBUG: c.log.append(f"   stations: run {c.name_of(r)} mid {mid:.1f} reach {reach:.1f} depth {ax['depth']:.1f}")
    while d <= depth_max:
        if inner:
            pat = inner[k % len(inner)]
            t = c.pick_once(pat)
            if t:
                io = inner_off or (half + 0.9 + max(f.half(t)))
                for o in (io, io + 0.5, io + 1.0):
                    n = mirrored(c, ax, t, d, o, light=light_inner and pat == inner[-1])
                    if n: got += n; break
                    if DEBUG:
                        pa, pb = on_axis(c, ax, d, -o), on_axis(c, ax, d, o)
                        c.log.append(f"   station {t} d={d:.1f} o={o:.1f}: {why(f, t, *pa)} / {why(f, t, *pb)}")
        if outer and reach >= 6.0:
            pat = outer[k % len(outer)]
            t = c.pick_once(pat)
            if t:
                hh = max(f.half(t))
                for o in (reach - hh - 0.4, reach - hh - 0.9, reach - hh - 1.5):
                    if o < (inner_off or half + 2.0) + 2.0: break
                    n = mirrored(c, ax, t, d, o)
                    if n: got += n; break
        d += step; k += 1
    return got


def gallery(c, plan):
    """Paintings at even steps along both back walls, mirrored; a runner down the axis from the door; statues and a
    pair of flame basins or orreries mirrored down it; benches and urns mirrored by the side walls; plants in the four
    corners; lights in matching corners."""
    f = c.f
    c.wall_pat = VASE
    c.s_makers = [lambda c_, uv: c_.put_all([(c_.pick_once(VASE), *c_.corner_uv("S", 1.2)), (c_.pick_once(VASE), *c_.corner_uv("E", 1.2))]) and 2,
                  lambda c_, uv: c_.corner_heap("S", [VASE], n=1, d=1.2),
                  lambda c_, uv: c_.corner_lights(("S", "E"), 1.2)]
    ax = axis(c)
    if ax:
        # the centrepiece at the far end of the walk, facing the way in: an orrery between a pair of flame basins
        r = ax["run"]
        cp = c.pick(r"^Orrery2$")
        if cp and c.put(cp, *on_axis(c, ax, 2.4)):
            mirrored(c, ax, c.pick_once(r"^DunMirFlameBasinLit$") or "Brazier", 2.2, 2.6)
        f.lay_runner(r, ax["mid"], 4.4, ax["depth"] - 1.0)
        f.aisle = dict(run=r, mid=ax["mid"], half=1.4, first=2.0, far=ax["depth"], door=c.door)
        stations(c, ax, [r"^Statue2[aceg]$", r"^DunMirFlameBasinLit$"],
                 [r"^Bench[1-4]$|^CushionedBench\d$", VASE], first=5.6, step=4.4)
    c.lights_balanced(4 if c.tiles >= 150 else 2)
    t = c.pick(r"^Plant[1345]$")
    if t:
        for pair in (("W", "E"), ("N", "S")):
            c.put_all([(t, *c.corner_uv(pair[0], 1.1)), (t, *c.corner_uv(pair[1], 1.1))])
    c.hangings(r"^Painting[12]$|^BlueTapestry[24]$", step=3.2, most=7, first=r"^Painting")


def hall(c, plan):
    """A colonnade in mirrored pairs either side of the aisle from the door, statues and braziers between the columns,
    benches and urns mirrored by the side walls, a statue pair flanking the middle of the far wall, lights in matching
    corners, banners of one colour at even steps on the back walls."""
    f = c.f
    c.wall_pat = VASE
    c.s_makers = [lambda c_, uv: c_.put_all([(c_.pick_once(VASE), *c_.corner_uv("S", 1.2)), (c_.pick_once(VASE), *c_.corner_uv("E", 1.2))]) and 2,
                  lambda c_, uv: c_.corner_heap("S", [VASE], n=1, d=1.2),
                  lambda c_, uv: c_.corner_lights(("S", "E"), 1.2)]
    ax = axis(c)
    if ax:
        f.aisle = dict(run=ax["run"], mid=ax["mid"], half=1.6, first=2.4, far=ax["depth"], door=c.door)
        stations(c, ax, [r"^Column[5-8]$", r"^Statue2[a-h]$", r"^Brazier$"], [r"^Bench[1-4]$|^CushionedBench\d$", VASE],
                 first=3.4, step=4.0, light_inner=True)
        r = ax["run"]
        far = dict(obj=None, run=r, uv=f._uv_on(r, 0.5, ax["mid"]), along=ax["mid"], ha=1.2, hp=0.4)
        if c.flank(far, r"^Statue2[a-h]$", gap=1.2, fam="statue"):
            # the house's chest centred between them, flame basins before them
            res = c.on_wall(c.pick(r"^DunMirChest\d$|^Chest\d$", "storage") or "Chest1", r, ax["mid"], "storage")
            mirrored(c, ax, c.pick_once(r"^DunMirFlameBasinLit$") or "Brazier", 2.6, 3.2)
    else:
        f.colonnade(gap=4.2, aisle=3.2)
    c.lights_balanced(4 if c.tiles >= 150 else 2)
    col = c.rng.choice(("Blue", "Red", "Green", "White"))
    c.hangings(rf"^{col}Tapestry\d$|^TraderShieldWallHanging\d$" if c.f.style != "dunmir" else r"^DunMirHangingShield\d+$",
               step=3.6, most=6)


def throne_room(c, plan):
    """The throne across from the door on the NW wall facing it down a runner; statues and braziers flanking it;
    columns and braziers in mirrored pairs down the aisle; benches and statues mirrored by the side walls; lights in
    matching corners; urns flanking the way in; tapestries of one colour at even steps."""
    f = c.f
    c.wall_pat = VASE
    c.s_makers = [lambda c_, uv: c_.put_all([(c_.pick_once(VASE), *c_.corner_uv("S", 1.2)), (c_.pick_once(VASE), *c_.corner_uv("E", 1.2))]) and 2,
                  lambda c_, uv: c_.corner_heap("S", [VASE], n=1, d=1.2),
                  lambda c_, uv: c_.corner_lights(("S", "E"), 1.2)]
    th = f.place_throne(depth=2.9, runner=True)
    if th:
        c.flank(th, r"^Statue2[a-h]$", gap=0.8, fam="statue")
        c.flank(th, r"^DunMirChest\d$|^Chest\d$", gap=3.4, fam="storage")
        f.flank_lights(th, 0.9)
        ax = dict(run=th["run"], mid=th["along"], depth=f._depth_of(th["run"]))
        stations(c, ax, [r"^Column[5-8]$", r"^Brazier$"], [r"^Bench[1-4]$|^CushionedBench\d$", r"^Statue2[a-h]$", VASE],
                 first=th["hp"] + 5.0, step=4.2, light_inner=True)
    else:
        f.colonnade(gap=5.0, aisle=3.0)
    c.lights_balanced(4)
    col = c.rng.choice(("Blue", "Red", "White", "Green"))
    c.hangings(rf"^{col}Tapestry\d$", step=3.4, most=6)


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


def s_corner_bare(c, reach=3.4):
    """True when nothing stands, lies or hangs within `reach` units of the room's S corner (validate/checks.py civic)."""
    f = c.f
    su, sv = c.corner_uv("S", 0.5)
    for t, (u, v, hu, hv, b, layer) in f._typed:
        if max(abs(u - su) - hu, 0) ** 2 + max(abs(v - sv) - hv, 0) ** 2 <= reach ** 2: return False
    return True


def dress_walls(c):
    """The back walls' bare stretches hung (the room's own hangings, then tapestries of one colour), then any stretch
    still bare given a mirrored pair of the room's wall piece (validate/checks.py civic.bare_wall)."""
    col = c.set_type.setdefault("tapestry colour", c.rng.choice(("Blue", "Red", "Green", "White")))
    for pat in (c.hang_pat, rf"^{col}Tapestry\d$"):
        if pat: c.hangings(pat, step=3.4, most=8)
    if not c.wall_pat: return
    for name in BACK:
        for r in c.runs.get(name, [])[:2]:
            for lo, hi in sorted(c.bare(r, reach=2.0), key=lambda s: s[0] - s[1]):
                if hi - lo >= 6.0: c.row(r, c.wall_pat, 2 if hi - lo >= 9 else 1, lo=lo + 0.6, hi=hi - 0.6)


def finish(f, need):
    """The last pass of a civic room: the back walls dressed where still bare, the S corner given a group where still
    bare, statues face into the room, rugs audited, lights in matching corners up to the room's due (a light per 40
    tiles, at least two, never past kit/objects.py light_cap)."""
    c = getattr(f, "_civic", None) or Ctx(f)
    dress_walls(c)
    if c.tiles >= 36 and s_corner_bare(c):
        for mk in (c.s_makers or [lambda c_, uv: c_.corner_set("S", TABLE_SMALL, 2),
                                  lambda c_, uv: c_.corner_heap("S", S("barrel", "crate", "sack_m"), n=3)]):
            if mk(c, c.corner_uv("S", 1.6)): break
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
    if any(u + hu > b[0] and u - hu < b[1] and v + hv > b[2] and v - hv < b[3] for b in f.runner_boxes): return "runner"
    if F._family_of(t) in F.WAY_TALL and any(u + hu > b[0] and u - hu < b[1] and v + hv > b[2] and v - hv < b[3]
                                             for b in f.far_ways): return "far_way"
    cap = f.repeat_cap(F._family_of(t))
    if cap is not None and f._fam_n[F._family_of(t)] >= cap: return f"repeat cap {cap}"
    k0 = Counter(f.kb_refused)
    if not f._kb_ok(t, u, v, hu, hv, blocking, "floor"):
        return "kb " + str(Counter(f.kb_refused) - k0)
    if not f._one_of_a_kind_ok(t, u, v): return "one_of_a_kind"
    if blocking and not f.g.reachable_ok((u, v, hu, hv, True, "floor")): return "reach"
    if f.coverage(f.footprint(t)) > f.cover_max: return "cover"
    return "ok?"
