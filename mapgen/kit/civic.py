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
# A floor square (i, j) is the tile (i + j, i - j), centred at uv (2i + 2, 2j) as the kit counts (Furnisher.lay_carpet),
# but the editor draws it a unit further toward the SW: its middle shows at uv (2i + 2, 2j - SQUARE_V) (the works
# helper's measure on a lone RugGreen tile, QA round 2: 11 px left and 10 px below the tile's point; Westwood's own
# tables on their rugs sit the same way). A carpet, a runner, a hearth's bricks are centred on what stands on them as the
# user sees them (Q2T-2: RM-SOLAR-03/04/05 "Center the tables and chairs on the carpet"; RM-GALLERY-03 "The statues and
# torches are not centered with the carpet"): the squares are chosen about (u, v + SQUARE_V).
SQUARE_V = 1.0


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
        self.carpet_inset = False       # carpets keep their trim off the room's outer ring (a band goes there)
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
        fire = fam == "fireplace"
        if wall:                                   # a named wall, centred on its longest free stretch
            r = self.wall(wall)
            if r:
                stretches = sorted(self.free(r), key=lambda s: s[0] - s[1])
                # a hearth on a square's middle (snap_hearth): each stretch's own middle first, a square aside last
                tries = [((lo, hi), k) for k in ((0, -2, 2) if fire else (0,)) for lo, hi in stretches]
                t0s = {}
                for (lo, hi), k in tries:
                    if (lo, hi) not in t0s:
                        t0s[(lo, hi)] = F._pick(f.rng, {t: w for t, w in f.types_of(fam).items() if not only or re.search(only, t)})
                    t0 = t0s[(lo, hi)]
                    if not t0: break
                    m_ = (lo + hi) / 2
                    a = sq_mid(m_, r["line"] == "/") + k if fire else m_
                    res = self.on_wall(t0, r, a, fam)
                    if DEBUG and not res:
                        tt = f.side_variant(t0, r, fam) or t0
                        hu_, hv_ = f.half(tt)
                        d_ = (hu_ if r["line"] == "/" else hv_) + F.SNUG_GAP.get(fam, 0.25)
                        self.log.append(f"   focal {tt} at {a:.1f} on {wall} ({lo:.1f}..{hi:.1f}): {why(f, tt, *f._uv_on(r, d_, a))}")
                    if res:
                        o, uv, ha, hp = res
                        p = dict(obj=o, run=r, uv=uv, along=a, ha=ha, hp=hp)
                        if F.NEEDS_FRONT.search(o["type"]):
                            f.g.zones.append(f.front_zone(r, *uv, max(0.8, ha) + 0.3, hp, max(2.3, clear)))
                            f.light_zones.append(f.front_zone(r, *uv, ha + 0.3, hp, 2.6))
                        if rug: f.rug_before(p)
                        return p
        p = f.place_on_wall(fam, at, clear, door=door, only=only)
        if p and fire: p = self.snap_hearth(p)
        if p and rug: f.rug_before(p)
        return p

    def snap_hearth(self, p):
        """A wall hearth moved along its wall onto a floor square's middle (as drawn: sq_mid), so
        the patch of brick laid under it, three squares along the wall (kit/shells.py hearth_squares), is centred on it
        (QA round 2, RM-TAVERN-01: "The brick hearth is not centered on the fireplace"). Kept where it was if it will
        not stand there."""
        f = self.f
        a0 = p["along"]
        r, o = p["run"], p["obj"]
        along_v = r["line"] == "/"
        if abs(a0 - sq_mid(a0, along_v)) < 0.05: return p
        t = o["type"]
        rec = f._placed_of.get(id(o))
        if not rec: return p
        depth = abs((rec[0] if r["line"] == "/" else rec[1]) - r["coord"])
        f._remove(o)
        for a in sorted((sq_mid(a0 - 1.0, along_v), sq_mid(a0 + 1.0, along_v)), key=lambda x: abs(x - a0)):
            uv = f._uv_on(r, depth, a)
            o2 = f.try_put(t, *uv, snug=True)
            if o2:
                f.anchors.append(uv)
                return dict(p, obj=o2, uv=uv, along=a)
        o2 = f.try_put(t, *p["uv"], snug=True) or f.put(t, *p["uv"])
        return dict(p, obj=o2)

    def flank(self, p, pat, gap=0.3, fam=None, n_each=1, pairing=True, blocking=True):
        """Mirrored pieces either side of placed anchor p on its wall: n_each a side, end to end, `gap` from it. Both
        sides or neither, as many as both sides take. Returns the pieces placed."""
        if not p: return 0
        r = p["run"]
        types = self.types(pat, fam)
        if not types: return 0
        t0 = self.rng.choice(types)
        half_full = t0 + "HalfFull" if re.match(r"^Bookcase\d$", t0) and self.f.ok_type(t0 + "HalfFull") else None
        got = 0
        for k in range(n_each):
            done = False
            tk = half_full if half_full and k % 2 == 1 else t0     # full and half-full books in turn, mirrored
            for extra in (0.0, 0.5, 1.0):
                t = self.f.side_variant(tk, r, fam or F._family_of(tk)) or tk
                hu, hv = self.f.half(t)
                ha = hv if r["line"] == "/" else hu
                off = p["ha"] + gap + extra + ha + k * (2 * ha + 0.05)
                a1 = self.on_wall(tk, r, p["along"] - off, fam, pairing=pairing, blocking=blocking, touch=k > 0)
                a2 = a1 and self.on_wall(tk, r, p["along"] + off, fam, pairing=pairing, blocking=blocking, touch=k > 0)
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
        if len(cols) == 1: self.set_type.setdefault("tapestry colour", cols[0])
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
        """A carpet of nu x nv squares centred as near (cu, cv) as the squares' grid allows, as drawn (SQUARE_V), all of
        it on the room's own floor with its trim ring too, the ring clear of the walls (a trim square half under a wall
        loses its edge), clear of the doors. Returns its exact centre as drawn (u, v) and its first square, or None.
        Nothing is laid (lay_carpet lays it)."""
        cv = cv + SQUARE_V
        f = self.f
        if f.carpet_plan is False or not F.CARPET_FLOORS.search(f.room.floor or ""): return None
        sq = {((x + y) // 2, (x - y) // 2) for (x, y) in f.room.tiles}
        nb8 = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]
        inner = {s for s in sq if all((s[0] + a, s[1] + b) in sq for a, b in nb8)}
        if self.carpet_inset:
            # a room bordered by a band (great_hall): the carpet's trim stays inside the band's ring, so the band runs
            # unbroken past it (QA round 3, RM-GREATHALL-01: the band along the NE wall had stopped where the carpet's
            # trim lay on its squares)
            inner = {s for s in inner if all((s[0] + a, s[1] + b) in inner for a, b in nb8)}
        tile = lambda s: (s[0] + s[1], s[0] - s[1])
        best = None
        i_c = (cu - nu - 1) / 2; j_c = (cv - nv + 1) / 2
        for di in (0, -1, 1):
            for dj in (0, -1, 1):
                i0 = int(math.floor(i_c)) + di if i_c != int(i_c) else int(i_c) + di
                j0 = int(math.floor(j_c)) + dj if j_c != int(j_c) else int(j_c) + dj
                rect = {(i, j) for i in range(i0, i0 + nu) for j in range(j0, j0 + nv)}
                if not rect <= inner: continue
                if any((f.spec.floor.get(tile(s)) or f.room.floor) != f.room.floor for s in rect): continue
                ring = {(s[0] + a, s[1] + b) for s in rect for a, b in nb8} - rect
                if any(tile(s) in f.spec.local_blend for s in rect | ring): continue
                if any(f.g.wall_dist(2 * s[0] + 2, 2 * s[1] - SQUARE_V) < 0.9 for s in ring): continue
                c = (2 * i0 + nu + 1, 2 * j0 + nv - 1)
                dd = math.hypot(c[0] - cu, c[1] - cv)
                if best is None or dd < best[0]: best = (dd, c, (i0, j0))
        return None if best is None else ((best[1][0], best[1][1] - SQUARE_V), best[2])

    def lay(self, origin, nu, nv):
        """Lays the carpet carpet_rect found (origin squares i0, j0; nu x nv)."""
        i0, j0 = origin
        box = (2 * i0 + 1.5, 2 * (i0 + nu - 1) + 2.5, 2 * j0 - 0.5, 2 * (j0 + nv - 1) + 0.5)
        return self.f.lay_carpet(box, margin=0.0)

    def table_set(self, uv, table_pat, n_seats, seat="chair", seat_pat=None, carpet=None, rug=False, gap=0.3,
                  reach=3.0, need_carpet=False):
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
                elif need_carpet: continue
            o = self.put(t, u, v)
            if not o:
                if DEBUG and (u, v) == cands[0]: self.log.append(f"   table {t} at {u:.1f},{v:.1f}: {why(f, t, u, v)}")
                continue
            n0 = len(f.objects)
            n = f.seats_around((u, v), t, n_seats, seat, gap=gap, pat=seat_pat)
            if rect and n % 2 == 1:
                # on a carpet the set is centred on it: its seats in opposite pairs, an odd one taken out (QA round 2,
                # RM-SOLAR-03/04/05 "Center the tables and chairs on the carpet")
                seats = [(x, f._placed_of.get(id(x))) for x in f.objects[n0:]]
                for x, rec in seats:
                    if rec and not any(y is not x and r2 and abs(rec[0] + r2[0] - 2 * u) < 0.3 and abs(rec[1] + r2[1] - 2 * v) < 0.3
                                       for y, r2 in seats):
                        f._remove(x); n -= 1; break
            if n < min(2, n_seats) or (n_seats >= 4 and n < 3 and not rect) or (rect and n < 2):
                for x in f.objects[n0:]: f._remove(x)
                f._remove(o)
                continue
            f._seated.add(((u, v), t))
            if rect: self.lay(rect, *carpet)
            elif rug and not any(u + 2.2 > bx[0] and u - 2.2 < bx[1] and v + 2.2 > bx[2] and v - 2.2 < bx[3]
                                 for bx in f.carpet_boxes):
                f.rug_under(o, (u, v))
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

    def heap(self, uv, pats, n=4, toward=None, flush=False, gap=0.2):
        """A tight heap of mixed stock at uv: one piece of each pattern in turn (a barrel, a crate, sacks of two sizes),
        each set against the last, toward the corner `toward` (u, v) when given. flush: every piece stands against a
        wall (QA round 2, Q2T-5; RM-KITCHEN-02: "The crate and sack are awkwardly in the middle of the room. Move them
        against the wall"), never slid out into the floor. gap: between the heap's pieces (RM-KITCHEN-04/05: "The apple
        crate is too close to the rectangular crate")."""
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
                        cands.append((rec[0] + du * (rec[2] + hu + gap), rec[1] + dv * (rec[3] + hv + gap)))
                if toward and got:
                    cands.sort(key=lambda c: math.hypot(c[0] - toward[0], c[1] - toward[1]))
                if flush:                          # against a wall, or one piece out from one in a heap two deep
                    cands = [c for c in cands if f.g.wall_dist(*c) - min(hu, hv) <= 1.7 and f.g.inside(*c)]
                for c in cands[:40 if flush else 20]:
                    o = f.try_put(t, *c)
                    if o: got.append(o); break
                    if DEBUG: self.log.append(f"   heap {t} at {c[0]:.1f},{c[1]:.1f}: {why(f, t, *c)}")
        finally:
            f._group = saved
        return len(got)

    def corner_heap(self, corner, pats, n=4, d=1.0, gap=0.2, flush=False):
        cu, cv = self.corner_uv(corner, d)
        far = self.corner_uv(corner, 0.0)
        return self.heap((cu, cv), pats, n, toward=far, flush=flush, gap=gap)

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
    def bare_spot(self, margin=1.2, skip=(), carpet_pad=3.2):
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
            if any(b_[0] - carpet_pad <= u <= b_[1] + carpet_pad and b_[2] - carpet_pad <= v <= b_[3] + carpet_pad
                   for b_ in f.carpet_boxes): continue
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

    def fill_bare(self, makers, most=3, over=3.2, mirror=False, carpet_pad=3.2):
        """Groups where the floor is still bare: while some point lies `over` units from everything, the first maker that
        fits there (each a function (ctx, (u, v)) -> pieces) puts its group there; mirror: its twin across the room's
        long middle line too, both or neither (a point on that line stands alone)."""
        f = self.f
        got, tried = 0, []
        for _ in range(most + 6):
            if got >= most: break
            b = self.bare_spot(skip=tried, carpet_pad=carpet_pad)
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


def mk_rug(c, uv):
    """A rug on its own where the floor is bare (a bearskin or a woven rug)."""
    t = c.pick(r"^BearskinRug\d$|^RedRug\d$")
    return 1 if t and c.put(t, *uv, blocking=False) else 0


def mk_worktable(c, uv):
    """A work table with two stools (its stores stand against the walls, never loose beside it: QA round 2,
    RM-KITCHEN-02 "The crate and sack are awkwardly in the middle of the room")."""
    return c.table_set(uv, r"^Table4$|^RoundTableWithFood$", 2, seat_pat=r"Stool", reach=1.2)


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
    c.s_makers = [lambda c_, uv: c_.corner_set("S", TABLE_SMALL, 2), lambda c_, uv: c_.corner_heap("S", [VASE], n=1, d=1.2)]
    walls = list(BACK); c.rng.shuffle(walls)
    hearth = c.focal("fireplace", clear=2.8, wall=walls[0])
    if hearth:
        c.run_pair_from(hearth, r"^Bookcase\d$", fam="shelves", most=3 if c.tiles < 180 else 4)   # (to the corners)
        r = hearth["run"]
        uv = f._uv_on(r, 8.0, hearth["along"])     # (its carpet two squares clear of the hearth's bricks)
        c.table_set(uv, TABLE_SMALL, 2, carpet=(3, 3), reach=1.5) or c.table_set(uv, TABLE_SMALL, 2, rug=True)
    if bed_set(c, walls[1]):                         # a bearskin or a woven rug before the bed's foot
        r_ = c.wall(walls[1])
        if r_:
            bed = f.beds[-1]
            ba = bed[2][1] if r_["line"] == "/" else bed[2][0]
            for dd in (5.2, 5.8, 6.4):
                if mk_rug(c, f._uv_on(r_, dd, ba)): break
    for w in walls:                                  # a desk faces the camera: back walls only
        if not c.wall(w): continue
        d = c.centred_on(w, r"^Desk[12]$", "desk")
        if d:
            f.seats_around(d[1], d[0]["type"], 1)
            break
    c.lights_balanced(4)
    if c.tiles >= 120:
        # the open middle (QA round 1: no large empty middle; the coordinator, 2026-10-13: large solars "keep a big bare
        # middle"): a table of four centred on its own carpet, clear of the hearth's carpet, with sitting sets mirrored
        # either side of it along the room's long line
        mb = c.middle_box(walk=1.2)
        cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
        long_u = (mb[1] - mb[0]) >= (mb[3] - mb[2])
        def off_carpets(p, pad=3.4):
            return not any(b_[0] - pad <= p[0] <= b_[1] + pad and b_[2] - pad <= p[1] <= b_[3] + pad for b_ in f.carpet_boxes)
        cands = sorted({(cu + (0.5 * k if long_u else 0), cv + (0 if long_u else 0.5 * k)) for k in range(-16, 17)},
                       key=lambda p: math.hypot(p[0] - cu, p[1] - cv))
        placed_mid = None
        # (a carpet of its own two squares clear of the hearth's: QA round 2, RM-SOLAR-03/04/05 "Center the tables and
        # chairs on the carpet": the carpets had run together into one blend, each set off the middle of it)
        # (three squares apart, so the two carpets' trims never meet; else the set stands on a rug of its own)
        far_ = [q for q in cands if off_carpets(q, 9.0)]
        for p_ in far_[:14]:
            for cs in ((3, 3), (4, 4)):
                if c.table_set(p_, r"^RoundTable[12]$|^SquareTable[12]$", 4, carpet=cs, reach=1.5, need_carpet=True):
                    placed_mid = p_; break
            if placed_mid: break
        if not placed_mid:                         # no carpet fits: the set on a rug in the middle all the same
            for p_ in [q for q in cands if off_carpets(q, 5.0)][:6]:
                if c.table_set(p_, r"^RoundTable[12]$|^SquareTable[12]$", 4, rug=True, reach=0.6):
                    placed_mid = p_; break
        if placed_mid:
            mu, mv = placed_mid
            for off in (6.0, 5.2, 6.8, 4.6, 7.6):
                pts = [(mu - off, mv), (mu + off, mv)] if long_u else [(mu, mv - off), (mu, mv + off)]
                if not all(off_carpets(q, 4.2) for q in pts): continue      # (clear of every carpet and its trim)
                n0 = len(f.objects)
                if mk_sitting(c, pts[0]) and mk_sitting(c, pts[1]): break
                for x in f.objects[n0:]: f._remove(x)
        # a statue pair mirrored across the long line, facing in (never a lone statue in the open)
        t = c.pick_once(r"^Statue2[aceg]$")
        if t and placed_mid:
            mu, mv = placed_mid
            done_ = False
            for across in (True, False):               # across the long line, else along it
                for off in (4.6, 5.4, 6.2, 7.0, 7.8, 8.6, 9.4):
                    pts = [(mu, mv - off), (mu, mv + off)] if long_u == across else [(mu - off, mv), (mu + off, mv)]
                    if not all(off_carpets(q, 2.0) for q in pts): continue
                    if c.put_all([(t, *q) for q in pts], pairing=True): done_ = True; break
                if done_: break
    c.corner_set("S", TABLE_SMALL, 2)
    t = c.pick(VASE)
    if t:
        for d_ in (1.3, 1.9, 2.6):                     # urns in the side corners, a step further in where a piece stands
            if c.put_all([(t, *c.corner_uv("W", d_)), (t, *c.corner_uv("E", d_))], pairing=True): break
    wall_pair(c, "SE", r"^Bench\d$|^CushionedBench\d$", 0.25, "bench") or         wall_pair(c, "SW", r"^Bench\d$|^CushionedBench\d$", 0.3, "bench")
    wall_pair(c, "SW", VASE, 0.2) or wall_pair(c, "SE", VASE, 0.12)
    c.fill_bare([mk_sitting, mk_round4], most=max(3, c.tiles // 35), over=2.8, mirror=True, carpet_pad=3.8)
    c.hangings(r"^(Blue|Red|White|Green)Tapestry\d$|^Painting[12]$", most=5)


def study(c, plan):
    """The desk centred on a back wall with its chair, bookcases end to end either side of it; the other back wall
    lined with bookcases round a centred chest; the meeting table centred on its carpet; urns in matching corners; the
    S corner's reading set; lights flanking the desk; groups where the floor is still bare."""
    f = c.f
    c.wall_pat = r"^Bookcase\d$"
    c.s_makers = [lambda c_, uv: c_.corner_set("S", TABLE_SMALL, 2), lambda c_, uv: c_.corner_heap("S", [VASE], n=1, d=1.2)]
    walls = list(BACK); c.rng.shuffle(walls)
    desk = c.focal("desk", clear=1.6, wall=walls[0])
    if desk:
        f.seats_around(desk["uv"], desk["obj"]["type"], 1)
        n = c.run_pair_from(desk, r"^Bookcase\d$", fam="shelves", most=2) // 2
        if n:                     # a scholar's workstations mirrored beyond the books
            bt = f.side_variant(c.pick(r"^Bookcase\d$") or "Bookcase1", desk["run"], "shelves") or "Bookcase1"
            bw = 2 * (f.half(bt)[1] if desk["run"]["line"] == "/" else f.half(bt)[0]) + 0.05
            c.flank(dict(desk, ha=desk["ha"] + 0.15 + n * bw), r"^WizardWorkstation\d[a-d]?$", gap=1.1, fam="lab")
        if not c.run_pair_from(desk, r"^Bookcase\d$", fam="shelves", most=6) and not n:
            c.line(desk["run"], r"^Bookcase\d$", "shelves", most=4)       # no room both sides: the longer stretch
        c.flank_lights(desk, gap=0.4, before=0.8)
    ch = c.centred_on(walls[1], r"^Chest\d$", "storage")
    if ch:
        f.rug_before(anchor_of(c, ch, c.wall(walls[1])))
        c.flank(anchor_of(c, ch, c.wall(walls[1])), r"^Bookcase\d$", gap=1.2, fam="shelves", n_each=5)
    else:
        c.line(c.wall(walls[1]), r"^Bookcase\d$", "shelves", most=8)
    if c.tiles >= 110: stacks(c)                     # a big study keeps stacks of its books, as a library does
    mb = c.middle_box()
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    c.table_set((cu, cv), r"^RoundTable[12]$|^OvalTable[12]$", 4, carpet=(3, 3) if c.tiles >= 60 else (2, 2)) or \
        c.table_set((cu, cv), TABLE_SMALL, 2, rug=True, reach=4.0)
    c.lights_balanced(2)
    c.corner_set("S", TABLE_SMALL, 2)
    t = c.pick(r"^Plant[1345]$")
    if t and not c.put_all([(t, *c.corner_uv("W", 1.2)), (t, *c.corner_uv("E", 1.2))], pairing=True):
        for d_ in (1.1, 1.6):
            if c.put_all([(t, *c.corner_uv("N", d_))]): break
    if c.tiles >= 60: wall_pair(c, "SW", VASE, 0.3)
    if c.tiles >= 90: wall_pair(c, "SE", r"^Statue2[aceg]$", 0.3, "statue")
    if c.tiles >= 70 and not wall_pair(c, "SE", r"^CushionedBench\d$|^Bench\d$", 0.12, "bench"):
        wall_pair(c, "SW", r"^CushionedBench\d$|^Bench\d$", 0.12, "bench")
    c.fill_bare([mk_one(r"^Orrery2$|^Telescope2[a-g]$", "curio")], most=1, over=1.8)
    c.fill_bare([mk_sitting, mk_round4], most=max(2, c.tiles // 45), over=2.8, mirror=True)
    c.hangings(r"^Painting[12]$|^(Blue|Red|Green)Tapestry\d$|^WallTrophy(Bear|Moose|MountainLion)[12]$", most=3)


def library(c, plan):
    """Bookcases end to end along both back walls (and the front walls in a big library); stacks of bookcases in
    mirrored rows either side of an aisle down the middle of a big one; the reading table centred on its carpet; the
    desk centred with its chair; lights in matching corners; reading sets where the floor is still bare."""
    f = c.f
    c.wall_pat = r"^Bookcase\d$"
    c.s_makers = [lambda c_, uv: c_.corner_set("S", TABLE_SMALL, 2), lambda c_, uv: c_.corner_heap("S", [VASE], n=1, d=1.2)]
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
    ch = c.centred_on(walls[1], r"^Chest\d$", "storage") if c.tiles >= 100 else None
    if ch: c.flank(anchor_of(c, ch, c.wall(walls[1])), r"^Bookcase\d$", gap=1.2, fam="shelves", n_each=7)
    else: c.line(c.wall(walls[1]), r"^Bookcase\d$", "shelves", most=14)
    if f._fam_n["shelves"] < 8:                     # books on every wall that has room (a library's exception)
        for w in list(BACK) + list(FRONT): c.line(c.wall(w), r"^Bookcase\d$", "shelves", most=6)
    if c.tiles >= 90: wall_pair(c, "SE", r"^Statue2[aceg]$", 0.3, "statue")
    c.lights_balanced(4 if c.tiles >= 120 else 2)
    if c.tiles >= 140:
        for w in FRONT: c.line(c.wall(w), r"^Bookcase\d$", "shelves", most=8)
    if c.tiles >= 100: stacks(c)
    mb = c.middle_box(walk=1.2)
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    c.table_set((cu, cv), r"^OvalTable[12]$|^RoundTable[12]$", 4, carpet=(3, 3)) or \
        c.table_set((cu, cv), TABLE_SMALL, 2, rug=True, reach=4.0)
    c.corner_set("S", TABLE_SMALL, 2)
    if c.tiles >= 150: c.fill_bare([mk_sitting], most=c.tiles // 90, over=3.4, mirror=True)
    if c.tiles >= 100:                               # urns mirrored in the side corners
        t = c.pick(VASE)
        if t and not c.put_all([(t, *c.corner_uv("W", 1.3)), (t, *c.corner_uv("E", 1.3))], pairing=True):
            wall_pair(c, "SW", VASE, 0.2) or wall_pair(c, "SE", VASE, 0.2)
        c.fill_bare([mk_one(r"^Orrery2$|^Telescope2[a-g]$", "curio")], most=1, over=1.8)   # a scholar's curio
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
    # QA round 2 (Q2C-8): the stores stand against the walls (RM-KITCHEN-02: "The crate and sack are awkwardly in the
    # middle of the room. Move them against the wall"), a hand's width apart, never a crate of apples against a crate
    # (RM-KITCHEN-04/05: "The apple crate is too close to the rectangular crate in the northeast")
    # (the corner heaps a piece bigger than before: the stores the floor's loose heaps held now stand in the corners)
    c.corner_heap("S", S("sack_l", "sack_m", "apples", "sack_s", "barrel"), n=5, flush=True, gap=0.3)
    c.corner_heap("W", S("barrel", "water", "crate", "sack_m"), n=4 if c.tiles < 60 else 5, flush=True, gap=0.3)
    c.corner_heap("E", S("crate", "barrel", "sack_m", "water"), n=4, flush=True, gap=0.3)
    # the front walls lined with stores in a row, flush, a hand's width apart (no heap slid out into the floor)
    for w, mixes in (("SW", (S("barrel", "sack_l", "water", "sack_m"), S("sack_s", "dcrate", "sack_m"))),
                     ("SE", (S("dcrate", "sack_m", "barrel", "sack_s"), S("water", "sack_l", "barrel")))):
        for mix in mixes:                              # a second row on another bare stretch of a long wall
            wall_stock(c, w, mix, n=4 if c.tiles >= 45 else 3, most_share=0.45)
    # the work tables where the floor is still bare (no loose heaps there: a kitchen is used end to end)
    c.fill_bare([mk_worktable], most=max(1, c.tiles // 25), over=2.6)
    # a kind of store the room does not hold yet goes against any wall stretch still bare (a small kitchen whose
    # corners are doors: its stores in a row, of several kinds)
    for key in ("dcrate", "sack_m", "water", "barrel", "apples", "sack_s"):
        if any(re.search(STOCK[key], t) for t, _ in f._typed): continue
        for w in FRONT + BACK:
            if wall_stock(c, w, S(key), n=1, most_share=0.3): break
    if len(c.lights) < 2 and hearth: c.flank_lights(hearth, gap=0.5, before=0.6)
    c.hangings(r"^WallTrophy(Bear|Moose|MountainLion)[12]$|^Painting1$", walls=BACK, most=3)


def wall_stock(c, wall, pats, n=4, gap=0.5, at=None, most_share=0.6):
    """A row of stock flush against a wall, its kinds in turn (A B C A ...), `gap` apart, centred on the wall's longest
    free stretch (or at a share `at` along it), never more than `most_share` of the wall (kit/identity.py: kegs on 40%
    of a wall, stock on half): storage that belongs to a wall stands against it, lined up, never alone mid-floor (QA
    round 2, Q2T-5; RM-KITCHEN-02 "Move them against the wall"; RM-SHOP-01/03 "the random barrels, crates, and sacks
    need to be changed"). Returns the pieces placed."""
    r = c.wall(wall)
    if not r: return 0
    f = c.f
    types = [t for t in (c.pick(p) for p in pats) if t]
    if not types: return 0
    # a crate keeps GAP_CRATE from anything (kit/gaps.py, QA round 2 Q2T-4): a row with a crate in it is spaced to clear
    # it, else the furnisher refuses every crate and the wall stays bare (round 3's shops and kitchens: front walls
    # left empty after the gap rule merged)
    from kit import gaps as GP
    if any(GP.CRATE.match(GP.base(t)) for t in types):
        gap = max(gap, GP.GAP_CRATE + 0.05)
        if sum(1 for t in types if GP.CRATE.match(GP.base(t))) > 1 and len(types) <= 2:
            gap = max(gap, GP.GAP_CRATES + 0.05)
    # (the wall's stretches with nothing standing before them: free() knows only what is set against the wall)
    if DEBUG: c.log.append(f"   wall_stock {wall} bare {[(round(a_, 1), round(b_, 1)) for a_, b_ in c.bare(r, reach=1.6)]} types {types}")
    for lo, hi in sorted(c.bare(r, reach=1.6), key=lambda s_: s_[0] - s_[1])[:2]:
        ws = []
        for k in range(n):
            t = types[k % len(types)]
            tv = f.side_variant(t, r, F._family_of(t)) or t
            hu, hv = f.half(tv)
            ws.append((t, hv if r["line"] == "/" else hu))
        for m in range(n, 0, -1):
            total = sum(2 * ha for _, ha in ws[:m]) + gap * (m - 1)
            if total > min(hi - lo - 0.4, most_share * (r["hi"] - r["lo"])): continue
            mid = (lo + hi) / 2 if at is None else lo + (hi - lo) * at
            lo_m, hi_m = lo + total / 2 + 0.2, hi - total / 2 - 0.2
            mid = min(max(mid, lo_m), hi_m)
            # the row centred on its stretch, else slid along it past a doorway's way or a hearth's front
            for mid_ in [mid] + [x for k in range(1, 12) for x in (mid - 0.6 * k, mid + 0.6 * k) if lo_m <= x <= hi_m]:
                got = _stock_row(c, r, wall, ws[:m], mid_ - total / 2, gap, f, lo, hi)
                if got: return m
    return 0


def _stock_row(c, r, wall, ws, a, gap, f, lo, hi):
    """wall_stock's row from `a` along wall run r: all of it or nothing. Returns the pieces or None."""
    got = []
    for t, ha in ws:
        # (before a front wall a piece stands a little out: the SE and SW walls are drawn over a piece whose middle
        # lies in a wall cell, kit/furnish.py before_back_wall)
        res = None
        for ex in ((0.0,) if wall in BACK else (0.4, 0.8)):
            res = c.on_wall(t, r, a + ha, None, pairing=True, extra=ex)
            if res: break
        if not res:
            if DEBUG:
                tv = f.side_variant(t, r, F._family_of(t)) or t
                hu_, hv_ = f.half(tv)
                d_ = (hu_ if r["line"] == "/" else hv_) + F.SNUG_GAP.get(F._family_of(t), 0.25)
                c.log.append(f"   wall_stock {wall} {tv} at {a + ha:.1f} ({lo:.1f}..{hi:.1f}) m={len(ws)}: "
                             f"{why(f, tv, *f._uv_on(r, d_ + (0.8 if wall in FRONT else 0), a + ha), snug=True)}")
            break
        got.append(res[0]); a += 2 * ha + gap
    if len(got) == len(ws): return got
    for o in got: c.drop(o)
    return None


def front_heaps(c, walls, mixes, n=3, at=(0.35, 0.65), flush=False):
    """Heaps of mixed stock on the front walls, a mirrored pair on each (at the shares `at` of its main run); flush:
    every piece against the wall (Ctx.heap)."""
    got = 0
    for w in walls:
        r = c.wall(w)
        if not r or r["hi"] - r["lo"] < 9: continue
        mix = mixes[got % len(mixes)]
        for frac in at:
            a = r["lo"] + (r["hi"] - r["lo"]) * frac
            uv = c.f._uv_on(r, 1.0, a)
            if c.heap_ok(uv): got += c.heap(uv, mix, n=n, toward=c.f._uv_on(r, 0.0, a), flush=flush) > 0
    return got


SHOP_WAY_HALF = 1.0          # half the width of the walk kept clear from the shop's door to its counter


def shop_walk(c, counter, half=SHOP_WAY_HALF):
    """The walk from the main door to the customer's side of the counter kept clear (QA round 2, Q2C-7, the shop set:
    "Consider the path from the door to the shopkeeper's desk. Don't block it with objects"): straight in from the
    doorway to the counter's line, then along to it (an L, or a straight line when the counter stands across from the
    door), as zones nothing stands in. Returns the zones."""
    f = c.f
    op = c.door
    if not op or not counter: return []
    r = counter["run"]
    cu, cv = counter["uv"]
    # the customer's place: before the counter, away from its wall
    P = f._uv_on(r, abs((cu if r["line"] == "/" else cv) - r["coord"]) + counter["hp"] + 1.4, counter["along"])
    D = (op["coord"] + op["sign"] * 0.6, op["along"]) if op["line"] == "/" else (op["along"], op["coord"] + op["sign"] * 0.6)
    corner = (P[0], D[1]) if op["line"] == "/" else (D[0], P[1])     # in along the door's way first, then across
    zones = []
    for a, b in ((D, corner), (corner, P)):
        z = (min(a[0], b[0]) - half, max(a[0], b[0]) + half, min(a[1], b[1]) - half, max(a[1], b[1]) + half)
        if z[1] - z[0] > 2 * half + 0.1 or z[3] - z[2] > 2 * half + 0.1:
            f.g.zones.append(z); zones.append(z)
    return zones


def shop_counter(c, depth=2.2, clear=1.8):
    """The trader's counter out from a back wall, on a stretch long enough for his goods either side of him (a counter
    stranded in a corner between a doorway and a wall had left the keeper no wares, RM-SHOP-05), across from the main
    door and in line with it where the stretch allows, else in its middle: the keeper's space behind it kept clear and
    his spot recorded (as Furnisher.place_counter, which it falls back to). Returns the placement dict or None."""
    f = c.f
    t0 = F._pick(f.rng, f.types_of("counter_shop"))
    if not t0: return f.place_counter("counter_shop", depth, clear, door=True)
    op = c.door
    cands = []
    for r, lo, hi in f.segments():
        if NAME[r["side"]] not in BACK: continue
        t = f.side_variant(t0, r, "counter_shop") or t0
        hu, hv = f.half(t)
        ha, hp = (hv, hu) if r["line"] == "/" else (hu, hv)
        need = 2 * ha + 7.2                        # the counter and a piece of the keeper's goods either side
        if ha < hp or hi - lo < 2 * ha + 4.4: continue
        if hi - lo < need: need = hi - lo
        across = bool(op) and r["line"] == op["line"] and r["sign"] == -op["sign"]
        mid = (lo + hi) / 2
        spots = [mid + k for k in (0, -1, 1, -2, 2, -3, 3) if lo + need / 2 <= mid + k <= hi - need / 2]
        if across and lo + need / 2 <= op["along"] <= hi - need / 2: spots.insert(0, op["along"])
        cands.append(((hi - lo) + (30.0 if across else 0.0), t, r, ha, hp, spots))

    def goods_room(r, a, ha):                   # both of the keeper's goods clear of every doorway's swing
        pts = [f._uv_on(r, 1.0, a + s_ * (ha + 2.0)) for s_ in (-1, 1)]
        return all(math.hypot(pu - du, pv - dv) > F.DOOR_CLEAR + 1.6 for pu, pv in pts for du, dv in f.g.doors)
    for _, t, r, ha, hp, spots in sorted(cands, key=lambda x: -x[0]):
        for a in sorted(spots, key=lambda a_: not goods_room(r, a_, ha)):
            u, v = f._uv_on(r, depth + hp, a)
            zone = f.front_zone(r, u, v, ha, hp, clear)
            if f.g.zone_blocked(zone): continue
            wu, wv = f._uv_on(r, 0.0, a)
            keeper = f.front_zone(r, wu, wv, ha, 0.0, depth - 0.1)
            if f.g.zone_blocked(keeper): continue
            o = f.try_put(t, u, v)
            if not o: continue
            f.g.zones.append(zone)
            f.g.zones.append(keeper)
            f.spots.append(dict(role="shopkeeper", px=F._px(*f._uv_on(r, max(depth / 2 + 0.2, depth - 0.55), a))))
            f.anchors.append((u, v))
            f.wall_used.append(((r["line"], r["coord"]), a - ha - 0.6, a + ha + 0.6))
            return dict(obj=o, run=r, uv=(u, v), along=a, ha=ha, hp=hp)
    return f.place_counter("counter_shop", depth, clear, door=True)


def flank_goods(c, counter, pat, fam, pairs=2):
    """The keeper's goods mirrored either side of his counter against its wall, each pair both or neither, slid out
    along the wall until it stands clear of his space (Ctx.flank's fixed steps had found no room beside the keeper's
    space in a small shop). Returns the pieces placed."""
    f = c.f
    r, wa = counter["run"], counter["along"]
    t0 = c.pick(pat, fam)
    if not t0: return 0
    t = f.side_variant(t0, r, fam) or t0
    hu, hv = f.half(t)
    ha = hv if r["line"] == "/" else hu
    got, off = 0, counter["ha"] + 0.7 + ha
    for _ in range(pairs):
        done = False
        while off <= counter["ha"] + 6.0 + ha:
            x = c.on_wall(t0, r, wa - off, fam, pairing=True)
            y = x and c.on_wall(t0, r, wa + off, fam, pairing=True)
            if x and y:
                got += 2; done = True; off += 2 * ha + 0.1; break
            if x: c.drop(x[0])
            if DEBUG:
                d_ = (hu if r["line"] == "/" else hv) + F.SNUG_GAP.get(fam, 0.25)
                c.log.append(f"   flank_goods {t} at {wa - off:.1f}/{wa + off:.1f}: {why(f, t, *f._uv_on(r, d_, wa - off), snug=True)} / "
                             f"{why(f, t, *f._uv_on(r, d_, wa + off), snug=True)}")
            off += 0.4
        if not done: break
    return got


# a shop's wares by its trade: (the counter's flanking goods, the other back wall's goods, the front walls' rows, the
# corners' stock, the display rows standing free in a big shop, the walls' hangings)
SHOP_TRADES = {
    "armourer": dict(flank=(r"^TraderShelves\d$|^TraderHelmShelf\d$", "shop_rack"),
                     back=("row", r"^Trader(ArmorRack|PoleArm|BowRack)\d$"),
                     front=[r"^TraderArmorRack[12]$", r"^TraderPoleArm[1-4]$", r"^TraderBowRack[12]$"],
                     corners=[S("steel", "steelb", "crate"), S("crate", "barrel", "steel"), S("tools", "steelb")],
                     display=[r"^TraderArmorRack[12]$", r"^TraderPoleArm[1-4]$", r"^TraderBowRack[12]$"],
                     hang=r"^TraderShieldWallHanging\d$|^TraderCrossedWeapons\d$|^TraderHangingSwords\d$"),
    "apothecary": dict(flank=(r"^PotionShelves\d$", "shelves"),
                       back=("line", r"^PotionShelves\d$|^Bookcase\d$"),
                       front=[STOCK["apples"], STOCK["sack_m"], STOCK["crate"], STOCK["sack_l"]],
                       corners=[S("crate", "sack_m", "barrel"), S("apples", "sack_s", "crate"), S("dcrate", "sack_l")],
                       display=[STOCK["apples"], r"^FairyJar$"],
                       hang=r"^Painting[12]$|^GreenTapestry\d$"),
    "general": dict(flank=(r"^TraderShelves\d$", "shop_rack"),
                    back=("line", r"^TraderShelves\d$"),
                    front=[STOCK["steel"], STOCK["barrel"], STOCK["apples"], STOCK["steelb"], STOCK["tools"]],
                    corners=[S("steel", "barrel", "sack_l"), S("apples", "crate", "steelb"), S("sack_m", "tools", "dcrate")],
                    display=[STOCK["apples"], STOCK["steel"], STOCK["steelb"]],
                    hang=r"^WallTrophy(Bear|Moose|MountainLion)[12]$|^TraderShieldWallHanging\d$"),
}


def display_rows(c, pats, most_rows=2, per=3, gap=1.0, start=0):
    """A big shop's wares on show standing free, as an armoury's racks (QA round 2, Q2C-7: "Treat the shop less like a
    chapel and more like an armory"; rules/rooms/shop.md "racks for show, three to a row, each row its own kind"): rows
    of `per` pieces of one kind along the room's length, mirrored about its middle line across it, clear of the walk to
    the counter (its zones). Returns the pieces placed."""
    f = c.f
    # the floor inside a band of 3.4 units along the walls (what stands against them), the room's own middle
    mb = (c.uN + 3.4, c.uS - 3.4, c.vW + 3.4, c.vE - 3.4)
    du, dv = mb[1] - mb[0], mb[3] - mb[2]
    if DEBUG: c.log.append(f"   display box {[round(x, 1) for x in mb]}")
    if min(du, dv) < 4.0: return 0
    along_u = du >= dv
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    got, k = 0, 0
    w2 = (dv if along_u else du) / 2
    # mirrored pairs of rows, from the sides in; then, where none fits, one row down the middle line
    for off in [w2 - 0.8 - 2.2 * i for i in range(6)] + [0.0]:
        if (off < 2.0 and off != 0.0) or k >= most_rows or (off == 0.0 and k): continue
        placed = False
        for j in range(len(pats)):
            t = c.pick_once(pats[(start + k + j) % len(pats)])
            if not t: continue
            hu, hv = f.half(t)
            ha = hu if along_u else hv
            for n in range(per, 1, -1):
                span = n * 2 * ha + (n - 1) * gap
                if span > (du if along_u else dv): continue
                for slide in [0.0] + [x for i in range(1, 9) for x in (0.5 * i, -0.5 * i)]:
                    items = []
                    for side in ((-1, 1) if off else (0,)):
                        for i in range(n):
                            a = (cu if along_u else cv) + slide - span / 2 + ha + i * (2 * ha + gap)
                            items.append((t, a, cv + side * off) if along_u else (t, cu + side * off, a))
                    res = c.put_all(items, pairing=True)
                    if res:
                        got += len(res); placed = True; break
                    if DEBUG and slide == 0.0:
                        c.log.append(f"   display {t} x{n} off {off:.1f} mb {[round(x, 1) for x in mb]}: "
                                     f"{[why(f, tt, u_, v_) for tt, u_, v_ in items]}")
                if placed: break
            if placed: break
        if placed: k += 1
    return got


def shop(c, plan):
    """Composed as the armoury the user rated 4.8 (QA round 2, Q2C-7, the shop set: "These are very poor and need a lot
    of improvement. Consider the path from the door to the shopkeeper's desk. Don't block it with objects. Treat the
    shop less like a chapel and more like an armory"; RM-SHOP-01/03: "Cluttered mess ... the random barrels, crates, and
    sacks need to be changed"; -02 "too heavily concentrated in the south ... the north is very empty"; -05 "No path
    from the door to the shopkeeper's desk"): the trader's counter out from the back wall across from the door, facing
    it, the keeper behind it with his goods mirrored either side of him and lights flanking it; the walk from the door
    to the counter kept clear; the trade's goods lining the other back wall; the front walls lined with the trade's
    wares in rows against them; stock heaped against the walls in the corners; in a big shop, rows of wares on show
    standing free either side of the room's middle line, clear of the walk; the back walls hung with the trade. Nothing
    loose in the middle of the floor."""
    f = c.f
    c.s_makers = [lambda c_, uv: c_.corner_heap("S", S("crate", "barrel", "sack_m"), n=3, flush=True)]
    trade = c.rng.choice(("armourer", "apothecary", "general"))
    T = SHOP_TRADES[trade]
    counter = shop_counter(c)
    if counter:
        r = counter["run"]
        wa = counter["along"]
        pat, fam = T["flank"]
        flank_goods(c, counter, pat, fam, pairs=3 if c.tiles >= 90 else 2)
        c.flank_lights(dict(counter, hp=counter["hp"]), gap=0.5, before=0.3)
        shop_walk(c, counter)
        other = [w for w in BACK if w != c.name_of(r)]
    else:
        other = list(BACK)
    ow = c.wall(other[0]) if other else None
    kind, pat = T["back"]
    # (the other back wall lined end to end, as the armoury's)
    if kind == "row": c.row(ow, pat, max(2, min(6, c.tiles // 20)), "shop_rack")
    elif trade == "apothecary": c.line(ow, pat, "shelves", most=10, kinds=2)
    else: c.line(ow, pat, "shop_rack", most=8)
    c.lights_balanced(2 if c.tiles < 60 else 4)
    # stock heaped against the walls in the corners (never slid out into the floor)
    c.corner_heap("S", T["corners"][0], n=4, flush=True, gap=0.3)
    c.corner_heap("W", T["corners"][1], n=4, flush=True, gap=0.3)
    c.corner_heap("E", T["corners"][2], n=4, flush=True, gap=0.3)
    # the front walls lined with the trade's wares, in rows against them (the armoury's racks along its walls)
    for w in FRONT:
        for k in range(2):
            front = T["front"][k:] + T["front"][:k]
            wall_stock(c, w, front, n=4 if c.tiles >= 60 else 3, gap=0.4, most_share=0.45)
    # the wares on show in rows standing free, clear of the walk (a pair of short rows in a small shop)
    # wares on show standing free as the armoury's racks (rated 4.8): one mirrored pair of short rows of mixed goods,
    # clear of the walk, in a shop of 80 tiles or more. Three blocks of up to four rows had filled big shops' floors with
    # rows of apple crates (RM-SHOP-03 round 3: one kind repeated, Q2T-8; "Way too many objects in the middle of the
    # floor", Q2C-7); none at all left a big shop's floor bare (Q1T-1), its walls lined only with small crates and sacks
    if c.tiles >= 80:
        display_rows(c, T["display"], most_rows=2, per=3 if c.tiles >= 110 else 2)
    # a ware of the trade on any back-wall stretch still bare; a kind of the trade's stock the shop lacks yet against any
    # wall stretch still bare (several kinds, never one family alone: Q1A-2); then the walls hung
    for w in BACK:
        wall_stock(c, w, T["front"][:2], n=2, gap=0.4, most_share=0.3)
    for key in {"armourer": ("tools", "steelb", "dcrate", "steel"), "apothecary": ("sack_s", "dcrate", "sack_m", "barrel"),
                "general": ("tools", "dcrate", "sack_m", "steel", "barrel")}[trade]:
        if any(re.search(STOCK[key], t) for t, _ in f._typed): continue
        for w in FRONT + BACK:
            if wall_stock(c, w, S(key), n=1, most_share=0.3): break
    c.hangings(T["hang"], walls=tuple(BACK), most=6)
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
    c.s_makers = [lambda c_, uv: c_.corner_heap("S", S("sack_m", "dcrate"), n=2)]
    fronts = sorted((w for w in FRONT if c.wall(w)), key=lambda w: c.wall(w)["lo"] - c.wall(w)["hi"])
    for w in fronts[:2 if c.tiles >= 120 else 1]:
        r = c.wall(w)
        for lo, hi in sorted(c.free(r, pad=0.4), key=lambda s: s[0] - s[1])[:1]:
            # keep the S corner for the other row: the stretch starts two units off it
            cot_row(c, r, lo + 0.6, hi - 0.6)
    desk = counter_for(c, r"^Table[14]$|^SquareTable[12]$")
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
    for w in list(BACK) + list(FRONT):              # the linen chest centred on a stretch of its own
        if c.centred_on(w, r"^Chest\d$", "storage"): break
    mb = c.middle_box()
    c.table_set(((mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2), r"^Table[14]$|^SquareTable[12]$", 2,
                seat_pat=r"Stool", rug=True, reach=3.0)
    t = c.pick(r"^Plant[1345]$")
    if t: c.put_all([(t, *c.corner_uv("N", 1.1))])
    c.corner_heap("W", S("sack_m", "dcrate", "sack_s"), n=3)
    c.corner_heap("E", S("dcrate", "water", "sack_m"), n=3)
    c.corner_heap("N", S("dcrate", "sack_s"), n=2)
    c.fill_bare([mk_sitting], most=c.tiles // 60, over=3.2, mirror=True)
    c.hangings(r"^(White|Blue|Green)Tapestry\d$", most=3)


def herbalist(c, plan):
    """The herbalist's counter facing the way in with her behind it; potion shelves end to end either side of her
    along the back wall; the cauldron centred on the other back wall between books of remedies; glowing jars mirrored
    on a front wall; the work table with stools; sacks of herbs, crates and apples heaped in the corners and mirrored
    on the front walls."""
    f = c.f
    c.wall_pat = r"^Bookcase\d$"
    desk = counter_for(c, r"^Table[14]$|^SquareTable[12]$")
    if desk:
        r = desk["run"]
        back = dict(obj=None, run=r, uv=f._uv_on(r, 0.5, desk["along"]), along=desk["along"], ha=desk["ha"] * 0.5, hp=0.5)
        n = c.flank(back, r"^PotionShelves\d$", gap=0.1, fam="shelves", n_each=4) // 2
        # the potions in their pair or two (kit/objects.py: never a wall of them), then books of remedies on to the
        # corners, mirrored: the whole wall behind her lined
        pt = f.side_variant(c.pick(r"^PotionShelves\d$") or "PotionShelves1", r, "shelves") or "PotionShelves1"
        pw = 2 * (f.half(pt)[1] if r["line"] == "/" else f.half(pt)[0]) + 0.05
        c.flank(dict(back, ha=back["ha"] + 0.1 + n * pw), r"^Bookcase\d$", gap=0.1, fam="shelves", n_each=4)
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
            c.flank(anchor_of(c, res, r), r"^Bookcase\d$", gap=2.0, fam="shelves", n_each=3)
        elif r:
            c.line(r, r"^Bookcase\d$", "shelves", most=6)
    if not desk:                                       # no counter fitted: her potions line a back wall all the same
        c.line(c.wall(BACK[0]), r"^PotionShelves\d$", "shelves", most=4)
    if f._fam_n["stove"] < 1:                          # the cauldron is the room: any free stretch, else the floor
        caul = c.pick(r"^CauldronAnimated$")
        done = False
        for w in list(BACK) + list(FRONT):
            r = c.wall(w)
            if done or not r or not caul: continue
            for lo, hi in sorted(c.free(r, pad=0.6), key=lambda s_: s_[0] - s_[1])[:2]:
                if hi - lo >= 3.0 and c.on_wall(caul, r, (lo + hi) / 2, "stove", extra=0.5): done = True; break
        if not done and caul:
            mb = c.middle_box(walk=1.6)
            c.fill_bare([mk_one(r"^CauldronAnimated$", "cauldron")], most=1, over=1.6)
    if f._fam_n["shelves"] < 4:                        # her books of remedies along what back wall is left
        for w in BACK: c.line(c.wall(w), r"^Bookcase\d$", "shelves", most=4)
    c.lights_balanced(2)
    c.front_pair(r"^FairyJar$", None, wall="SW")
    mb = c.middle_box()
    c.table_set(((mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2), r"^Table4$|^SquareTable[12]$", 2, seat_pat=r"Stool",
                rug=True, reach=3.0)
    c.corner_heap("S", S("sack_l", "sack_m", "sack_s", "apples"), n=4)
    c.corner_heap("W", S("dcrate", "barrel", "sack_m"), n=3)
    c.corner_heap("E", S("apples", "sack_m", "dcrate"), n=3)
    c.fill_bare([mk_sitting, mk_heap("sack_l", "sack_m", "apples", n=3)], most=c.tiles // 50, over=3.0, mirror=True)
    c.hangings(r"^Painting[12]$|^GreenTapestry\d$", most=2)


# ---- shared arrangements ---------------------------------------------------------------------------------------------
def sq_mid(a, along_v):
    """The floor square's middle as drawn nearest `a` along a wall: squares' middles show on even u and on odd v
    (SQUARE_V)."""
    sh = SQUARE_V if along_v else 0.0
    return 2 * round((a + sh) / 2) - sh


def room_mid(c, r):
    """The room's own middle along wall run r: half way between the two walls either side of an axis run out from r
    (QA round 2, Q2T-1: "Center the hall in the room. There's a large gap on the northeast side"), a whole unit (the
    walls' lines are: a '/' wall on an odd u, a '\\' wall on an even v)."""
    a, b = (c.vW, c.vE) if r["line"] == "/" else (c.uN, c.uS)
    return int(round((a + b) / 2))


def axis(c, back_first=False, long_axis=False):
    """The room's main axis: the wall run across from the main door, the room's own middle along it, the room's depth
    from that wall. dict(run, mid, depth) or None. back_first: the far wall must be a back wall (a hearth, a desk, a
    throne), else the longest back wall's. long_axis: a long room (a gallery, a hall) runs its axis down its length
    from a back end wall whatever wall its door is in.

    QA round 2 (Q2T-1; RM-GALLERY-01/02 "The gallery is not centered in the room", RM-THRONEROOM-02/05 "The room is not
    centered"): the composition takes the room's middle, never the door's line (the axis had followed a door within a
    fifth of the wall's middle, shifting everything sideways by up to two units); the shell stands the door in its
    wall's middle (kit/building.py CENTRE_DOOR_ROOMS) and the way in bends to the axis where it does not (door_walk)."""
    f = c.f
    r = c.far_wall()
    if long_axis:
        du, dv = c.uS - c.uN, c.vE - c.vW
        if max(du, dv) >= 1.25 * min(du, dv):
            want = "/" if du > dv else "\\"           # the end walls lie across the length: NW (a '/' run) or NE
            if not r or r["line"] != want:
                end = c.wall("NW" if want == "/" else "NE")
                if end: r = end
    if r and (not back_first or c.name_of(r) in BACK):
        return dict(run=r, mid=room_mid(c, r), depth=f._depth_of(r))
    cands = [rr for n in (BACK if back_first else BACK + FRONT) for rr in c.runs.get(n, [])[:1]]
    if not cands: return None
    r = max(cands, key=lambda rr: rr["hi"] - rr["lo"])
    return dict(run=r, mid=room_mid(c, r), depth=f._depth_of(r))


def _undo_carpet(f):
    """Takes up the carpet laid last, floor and trim as they were (kit/grammar.py lift_carpet)."""
    from kit.grammar import lift_carpet
    if f.carpet_undo: lift_carpet(f, f.carpet_undo[-1])


def runner(c, ax, near, far):
    """A carpet runner down the axis from `near` to `far` units off the axis wall, centred on the axis exactly: two
    squares wide on a seam between squares (an odd axis), three on a square's middle (an even one); a runner the room
    would trim off its middle is taken up again (RM-GALLERY-03: "The statues and torches are not centered with the
    carpet"). Nothing stands on it. Returns True when laid."""
    f = c.f
    if not F.CARPET_FLOORS.search(f.room.floor or ""): return False
    r, mid = ax["run"], ax["mid"]
    across_v = r["line"] == "/"                    # the runner's width runs along v: its squares as drawn (SQUARE_V)
    m_k = mid + (SQUARE_V if across_v else 0.0)    # the axis in the kit's count of squares
    half = 1.5 if runner_squares(ax) == 2 else 2.5
    for n0, f0 in ((near, far), (near, far - 2.0), (near + 2.0, far), (near + 2.0, far - 2.0), (near + 2.0, far - 4.0)):
        if f0 - n0 < 6: continue
        (u0, v0), (u1, v1) = f._uv_on(r, n0, m_k - half), f._uv_on(r, f0, m_k + half)
        if not f.lay_carpet((min(u0, u1), max(u0, u1), min(v0, v1), max(v0, v1)), margin=0.0): continue
        b = f.carpet_boxes[-1]
        cen = (b[2] + b[3]) / 2 if across_v else (b[0] + b[1]) / 2
        # its trim whole: no square of the ring half under a wall (QA round 2, Q2T-6)
        i0, i1, j0, j1 = int((b[0] - 1) // 2), int((b[1] - 3) // 2), int((b[2] + 1) // 2), int((b[3] - 1) // 2)
        ring = [(i, j) for i in range(i0 - 1, i1 + 2) for j in range(j0 - 1, j1 + 2) if not (i0 <= i <= i1 and j0 <= j <= j1)]
        if abs(cen - m_k) > 0.26 or any(f.g.wall_dist(2 * i + 2, 2 * j - SQUARE_V) < 0.9 for i, j in ring):
            _undo_carpet(f); continue
        f.runner_boxes.append((b[0], b[1], b[2] - SQUARE_V, b[3] - SQUARE_V))     # where it shows: nothing stands on it
        return True
    return False


def runner_squares(ax):
    """How many squares wide the runner down the axis is: two on a seam between squares as drawn, three on a square's
    middle."""
    m_k = ax["mid"] + (SQUARE_V if ax["run"]["line"] == "/" else 0.0)
    return 2 if m_k % 2 else 3


def door_walk(c, ax, half=1.3):
    """The main door's way to the axis kept clear when the door is not on it (a long gallery entered from its side, a
    door the shell could not centre): a strip from the doorway straight in to the axis line."""
    f = c.f
    op = c.door
    if not op or not ax: return None
    r, mid = ax["run"], ax["mid"]
    if op["line"] == r["line"]:                       # in an end wall: in line with the axis, or a step to it
        if abs(op["along"] - mid) <= 1.0: return None
        p0, p1 = op["coord"], op["coord"] + op["sign"] * 3.0
        a0, a1 = min(op["along"], mid) - half, max(op["along"], mid) + half
    else:                                            # in a side wall: across to the axis
        p0, p1 = op["coord"], mid
        a0, a1 = op["along"] - half, op["along"] + half
    z = (min(p0, p1), max(p0, p1), a0, a1) if op["line"] == "/" else (a0, a1, min(p0, p1), max(p0, p1))
    f.g.zones.append(z)
    return z


def on_axis(c, ax, depth, off=0.0):
    """uv of a point `depth` units out from the axis wall, `off` along it from the axis."""
    return c.f._uv_on(ax["run"], depth, ax["mid"] + off)


def side_walls(c, ax):
    """The walls either side of the axis: (the one toward lesser along, the one toward greater), runs or None."""
    return (c.wall("SW"), c.wall("NE")) if ax["run"]["line"] == "/" else (c.wall("NW"), c.wall("SE"))


def facing_pair(c, ax, t):
    """The two variants of a seat for a mirrored pair about the axis, each with its back to its own side wall, so both
    face the aisle (QA round 2, Q2T-3; RM-HALL-01: "The benches are facing the wrong way ... they should face
    southwest"; RM-GALLERY-01: "The benches are facing the wrong orientation")."""
    lo_w, hi_w = side_walls(c, ax)
    fam = F._family_of(t)
    t1 = (c.f.side_variant(t, lo_w, fam) if lo_w else None) or t
    t2 = (c.f.side_variant(t, hi_w, fam) if hi_w else None) or t
    return t1, t2


def mirrored(c, ax, t, depth, off, pairing=True, light=False, face=False):
    """A pair of t mirrored about the axis, `off` either side, `depth` out from the axis wall. Both or neither. face: each
    a seat's variant facing the aisle (facing_pair)."""
    a = on_axis(c, ax, depth, -off); b = on_axis(c, ax, depth, off)
    kw = dict(light=True) if light else {}
    t1, t2 = facing_pair(c, ax, t) if face else (t, t)
    got = c.put_all([(t1, *a, kw), (t2, *b, kw)], pairing=pairing)
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
    """A carpet laid under a box of pieces (u0, u1, v0, v1), centred on it as drawn: of the sizes about the box's, the one
    whose middle falls nearest the pieces' (an odd count of squares on a square's middle, an even one on a seam), within
    a unit."""
    nu = max(2, int(math.ceil((box[1] - box[0] + 2 * pad) / 2)))
    nv = max(2, int(math.ceil((box[3] - box[2] + 2 * pad) / 2)))
    cu, cv = (box[0] + box[1]) / 2, (box[2] + box[3]) / 2
    best = None
    for k, (a, b) in enumerate((nu - d1, nv - d2) for d1 in (0, -1, 1, 2) for d2 in (0, -1, 1, 2)):
        if a < 2 or b < 2: continue
        cr = c.carpet_rect(cu, cv, a, b)
        if DEBUG: c.log.append(f"   carpet {a}x{b} at {cu:.1f},{cv:.1f}: {cr}")
        if not cr: continue
        d = math.hypot(cr[0][0] - cu, cr[0][1] - cv)
        if d <= 1.01 and (best is None or d < best[0] - 0.05): best = (d, cr, a, b)
    return c.lay(best[1][1], best[2], best[3]) if best else None


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
BAR_BRICK = ("RedBrick", "Redbrick3", "GreenBrick", "BlueBrick3")


def bar_floor(c):
    """The floor behind the bar laid in solid brick, from the walls to the bar's line, the bar covering its edge: no
    blend past it, as a room's floor ends at its walls (QA round 2, Q2C-6, the tavern set: "Make the floor behind the
    bars solid brick consistent with no blending. The whole area behind the bar should be bricks, and the border
    should be the bar ... Terminate the bricks at the bar"). kit/shells.py lay_zones leaves it alone (room.bar_floor).
    Returns the tiles laid.

    QA round 3 (Q3C-2, the tavern set): "All taverns need to have the floor properly transitioned between the bar floor
    and the main tavern floor where the bar entrance / gap is. This is because the transition there is visible.
    Meanwhile, the transition on the rest of it is obscured by the bar." Where no counter stands over the seam (the
    flap the barkeep walks through, an arm stopping short), the brick is bordered as a hearth's patch is (bar_gap_border).
    """
    from kit import shells as SH
    f = c.f
    room, spec = f.room, f.spec
    for t in getattr(room, "bar_floor", None) or ():      # a furnishing tried before this one (originality re-roll)
        spec.tile(*t, room.floor)
    for n, pair in getattr(room, "bar_edges", None) or ():
        spec.pattern_tiles.get(n, set()).discard(pair)
    room.bar_floor, room.bar_edges = set(), []
    fr = getattr(f, "bar_frame", None)
    if not fr: return set()
    ru, rv, U, V, su, sv = fr["ru"], fr["rv"], fr["U"], fr["V"], fr["su"], fr["sv"]
    main = room.floor
    mat = next((m for m in BAR_BRICK if m != main and frozenset((m, main)) not in SH._never()), None)
    if not mat: return set()
    tiles = set()
    for (x, y) in room.tiles:
        u, v = x + y + 2, x - y - SQUARE_V              # the tile's middle as drawn (SQUARE_V)
        if (u - U) * su <= 0.01 and (v - V) * sv <= 0.01 and (u - ru["coord"]) * su > -1.5 and (v - rv["coord"]) * sv > -1.5:
            tiles.add((x, y))
    if any((spec.floor.get(t) or main) != main for t in tiles): return set()     # (a carpet or a patch already there)
    for t in tiles: spec.tile(*t, mat)
    room.bar_floor = tiles
    bar_gap_border(c, tiles, mat)
    return tiles


BAR_COUNTER = re.compile(r"^Bar(Piece|Corner)")      # the counter's solid pieces (the flap, BarHingedTop, is the gap)
BAR_COVER = 0.35                                     # a seam this near a counter piece's footprint lies under it


def bar_open_seams(tiles, room_tiles, floor, counters, main):
    """The seams between the brick behind a bar and the room's floor that no counter piece stands over: [(brick tile,
    floor tile)]. tiles: the brick's; counters: [(u, v, hu, hv)] of the solid pieces; a seam's middle as drawn (tile
    (x, y) at uv (x + y + 2, x - y - 1)). Shared with validate/checks.py (qa3.bar_gap)."""
    out = []
    for t in sorted(tiles):
        for dx, dy in ((1, -1), (-1, -1), (1, 1), (-1, 1)):
            n = (t[0] + dx, t[1] + dy)
            if n in tiles or n not in room_tiles or (floor.get(n) or main) != main: continue
            mu = (t[0] + t[1] + n[0] + n[1]) / 2 + 2
            mv = (t[0] - t[1] + n[0] - n[1]) / 2 - 1
            if any(abs(mu - u) <= hu + BAR_COVER and abs(mv - v) <= hv + BAR_COVER for u, v, hu, hv in counters):
                continue
            out.append((t, n))
    return out


def bar_gap_border(c, tiles, mat):
    """The brick behind the bar bordered where its seam with the room's floor shows, at the flap the barkeep walks
    through and wherever no counter stands over it (Q3C-2): its edge drawn onto the room's floor there, as a hearth's
    patch is bordered (kit/shells.py lay_patch, PATCH_EDGE); under the counter it ends at the bar's line unbordered
    (Q2C-6: "Terminate the bricks at the bar")."""
    from kit import shells as SH
    f = c.f
    room, spec = f.room, f.spec
    main = room.floor
    counters = [(rec[0], rec[1], rec[2], rec[3]) for t, rec in f._typed if BAR_COUNTER.match(t) and rec[4]]
    if mat not in spec.blend: spec.blending(mat, -50, edge=SH.PATCH_EDGE)
    open_ = bar_open_seams(tiles, set(room.tiles), spec.floor, counters, main)
    # and the seam either side of each, under the counter's ends, so the border runs across the whole gap and on under
    # the counter rather than stopping where the gap's first tile does
    mid = lambda t, n: ((t[0] + t[1] + n[0] + n[1]) / 2, (t[0] - t[1] + n[0] - n[1]) / 2)
    gaps = [mid(t, n) for t, n in open_]
    near = [(t, n) for t, n in bar_open_seams(tiles, set(room.tiles), spec.floor, [], main)
            if (t, n) not in open_ and any(math.hypot(mid(t, n)[0] - a, mid(t, n)[1] - b) <= 2.1 for a, b in gaps)]
    for t, n in open_ + near:
        spec.edge_over[(mat, main)] = SH.PATCH_EDGE
        spec.pattern_tiles.setdefault(n, set()).add((mat, main))
        room.bar_edges.append((n, (mat, main)))
    if DEBUG: c.log.append(f"   bar floor {len(tiles)} tiles, {len(room.bar_edges)} open seams bordered")


def bar_front(c, depth=3.4):
    """The floor before the bar kept for its patrons: a strip `depth` units out from the counter's line along both its
    arms, where no table stands (QA round 2, RM-TAVERN-03: "The table that is touching the east corner of the bar is
    way too close to the bar")."""
    f = c.f
    fr = getattr(f, "bar_frame", None)
    if not fr: return
    ru, rv, U, V, su, sv = fr["ru"], fr["rv"], fr["U"], fr["V"], fr["su"], fr["sv"]
    u_lo, u_hi = sorted((ru["coord"], U + su * depth))
    v_lo, v_hi = sorted((V, V + sv * depth))
    f.g.zones.append((u_lo, u_hi, v_lo, v_hi))            # before the u-run (the arm along u at v = V)
    u_lo, u_hi = sorted((U, U + su * depth))
    v_lo, v_hi = sorted((rv["coord"], V + sv * depth))
    f.g.zones.append((u_lo, u_hi, v_lo, v_hi))            # before the v-run and round the corner
    u_lo, u_hi = sorted((ru["coord"], U)); v_lo, v_hi = sorted((rv["coord"], V))
    f.g.zones.append((u_lo, u_hi, v_lo, v_hi))            # and the barkeep's floor inside it: no table set behind the bar


TAVERN_LAYOUTS = ("grid", "rows", "clusters", "mixed")


def tavern_grid(c, mb):
    """Round tables in an even grid centred on one carpet, stools round each (QA round 1's layout)."""
    f = c.f
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
    return got


def long_table_type(c, along_u):
    """The room's long table turned to lie along u (along_u) or along v, else None."""
    f = c.f
    tt = c.pick_once(r"^Table[1-4]$")
    if not tt: return None
    stem = re.sub(r"\d+$", "", tt)
    sibs = [s_ for s_ in (f"{stem}{d}" for d in "1234") if f.ok_type(s_)]
    return next((s_ for s_ in sibs if (f.half(s_)[0] > f.half(s_)[1]) == along_u), None)


def tavern_rows(c, mb):
    """Long tables with benches in two rows mirrored about the room's middle line, along its length, on one carpet."""
    f = c.f
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    along_u = (mb[1] - mb[0]) >= (mb[3] - mb[2])
    t = long_table_type(c, along_u)
    if not t: return 0
    hu, hv = f.half(t)
    hl = hu if along_u else hv
    span = (mb[1] - mb[0]) if along_u else (mb[3] - mb[2])
    per = max(1, min(3, int((span + 2.0) / (2 * hl + 3.4))))
    n0 = len(f.objects)
    for k in (per, per - 1, 1):
        if k < 1: continue
        for off in (3.4, 3.0, 3.8, 2.6):
            pts = []
            for i in range(k):
                al = (i - (k - 1) / 2) * (2 * hl + 3.4)
                for sgn in (-1, 1):
                    pts.append((cu + al, cv + sgn * off) if along_u else (cu + sgn * off, cv + al))
            ok = True
            for (u, v) in pts:
                o = c.put(t, u, v)
                if not o or f.seats_around((u, v), t, 2, "bench", gap=0.3) < 2:
                    ok = False; break
                f._seated.add(((u, v), t))
            if ok:
                # a stool at each end of every table, mirrored (the head seats: a long table seated round, never only
                # at its ends)
                st = c.pick_once(r"^Stool\d$|^CushionedStool\d$")
                if st:
                    sh = max(f.half(st))
                    for (u, v) in pts:
                        e = hl + sh + 0.35
                        ends = [(u - e, v), (u + e, v)] if along_u else [(u, v - e), (u, v + e)]
                        c.put_all([(st, *q) for q in ends], pairing=True)
                bx = pieces_box(c, n0)
                if bx: carpet_box(c, bx, pad=0.6)
                return len(pts)
            for x in f.objects[n0:]: f._remove(x)
    return 0


def tavern_clusters(c, mb):
    """Two clusters mirrored about the room's middle line: in each a round table ringed by stools and a square table
    with chairs, each set on its own rug."""
    f = c.f
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    along_u = (mb[1] - mb[0]) >= (mb[3] - mb[2])
    rnd = exact_set(r"^RoundTable[12]$", 4, seat_pat=r"Stool", gap=0.45)
    sq = exact_set(r"^SquareTable[12]$", 4, seat="chair", gap=0.35)
    span = ((mb[1] - mb[0]) if along_u else (mb[3] - mb[2])) / 2
    got, off = 0, None
    for off_ in (min(span - 2.4, 6.0), 5.0, 4.4, 7.0):
        if off_ < 3.6: continue
        n0 = len(f.objects)
        pts = [(cu - off_, cv), (cu + off_, cv)] if along_u else [(cu, cv - off_), (cu, cv + off_)]
        if rnd(c, pts[0]) and rnd(c, pts[1]):
            got, off = 2, off_; break
        for x in f.objects[n0:]: f._remove(x)
    if not got: return 0
    for off2 in (4.8, 4.2, 5.4):                      # the square tables across from them, mirrored
        n0 = len(f.objects)
        pts = [(cu - off, cv + off2), (cu + off, cv - off2)] if along_u else [(cu + off2, cv - off), (cu - off2, cv + off)]
        if sq(c, pts[0]) and sq(c, pts[1]):
            got += 2; break
        for x in f.objects[n0:]: f._remove(x)
    for o in [x for x in f.objects if re.match(r"^(RoundTable[12]|SquareTable[12])$", x["type"])]:
        rec = f._placed_of.get(id(o))
        if rec and not any(rec[0] + 2.2 > bx[0] and rec[0] - 2.2 < bx[1] and rec[1] + 2.2 > bx[2] and rec[1] - 2.2 < bx[3]
                           for bx in f.carpet_boxes):
            f.rug_under(o, (rec[0], rec[1]))
    return got


def tavern_mixed(c, mb):
    """A table of food with chairs centred on a carpet in the middle, round tables with stools mirrored either side of
    it along the room's length (and across it where the room is wide)."""
    f = c.f
    cu, cv = (mb[0] + mb[1]) / 2, (mb[2] + mb[3]) / 2
    along_u = (mb[1] - mb[0]) >= (mb[3] - mb[2])
    got = c.table_set((cu, cv), r"^RoundTableWithFood$", 4, carpet=(3, 3), reach=1.5, need_carpet=True) or \
        c.table_set((cu, cv), r"^RoundTableWithFood$", 4, rug=True, reach=1.5)
    if not got: return 0
    rnd = exact_set(r"^RoundTable[12]$", 3, seat_pat=r"Stool", gap=0.45)
    span = ((mb[1] - mb[0]) if along_u else (mb[3] - mb[2])) / 2
    for off in (6.4, 7.0, 5.8, 7.6):
        if off > span: continue
        n0 = len(f.objects)
        pts = [(cu - off, cv), (cu + off, cv)] if along_u else [(cu, cv - off), (cu, cv + off)]
        if rnd(c, pts[0]) and rnd(c, pts[1]):
            got += 2; break
        for x in f.objects[n0:]: f._remove(x)
    for off in (5.0, 4.4, 5.6):
        n0 = len(f.objects)
        pts = [(cu, cv - off), (cu, cv + off)] if along_u else [(cu - off, cv), (cu + off, cv)]
        if rnd(c, pts[0]) and rnd(c, pts[1]):
            got += 2; break
        for x in f.objects[n0:]: f._remove(x)
    return got


def tavern(c, plan):
    """The bar in a back corner meeting both walls, solid brick behind it to its line, kegs behind it, patrons' floor
    kept before it; the hearth centred on the other back wall on its stones, a rug before it clear of the fire, shelves
    of crockery mirrored either side; lights in matching corners; the tables in one of several layouts (a grid of round
    tables on a carpet, rows of long tables with benches, mirrored clusters of round and square tables, a table of food
    flanked by round tables); long tables mirrored by a front wall; kegs heaped in the corners and lined on the front
    walls; round sets where the floor is still bare; trophies at even steps along the back walls.

    QA round 2 (Q2C-6), the tavern set: "Four out of five of these taverns have the exact same table and stool
    configuration, add a little variance ... Overall, they feel just a little bit too empty"."""
    f = c.f
    c.wall_pat = r"^LogShelvesFull\d$"
    c.s_makers = [lambda c_, uv: c_.corner_heap("S", S("barrel", "piled"), n=3)]
    f.bar_frame = None
    f.build_bar()
    bar_floor(c)
    bar_front(c)
    hearth = c.focal("fireplace", clear=2.8)
    if hearth:
        hearth_rug(c, hearth)
        c.flank(hearth, r"^LogShelvesFull\d$", gap=1.4, fam="shelves", n_each=2)
    c.lights_balanced(4)
    mb = c.middle_box(walk=1.4)
    layout = random.Random(zlib.crc32(f"tav:{f.spec.d.get('name')}:{f.room.id}".encode())).choice(TAVERN_LAYOUTS)
    makers = {"grid": tavern_grid, "rows": tavern_rows, "clusters": tavern_clusters, "mixed": tavern_mixed}
    for name in [layout] + [x for x in TAVERN_LAYOUTS if x != layout]:
        if makers[name](c, mb):
            c.log.append(f"tavern layout {name}")
            break
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
    # kegs in the corners and in rows on the front walls, against them (QA round 2, Q2T-5)
    c.corner_heap("S", S("barrel", "piled", "barrel"), n=3, flush=True)
    c.corner_heap("E", S("piled", "barrel", "water"), n=3, flush=True)     # (RM-TAVERN-05: "especially the east side")
    c.corner_heap("W", S("barrel", "water", "piled"), n=3, flush=True)
    for w in FRONT:
        wall_stock(c, w, S("barrel", "piled", "water"), n=3, most_share=0.35)
    # the great casks (by the bar where it has room: furnish.bar_casks), else a pair on a front wall
    if not any(re.search(STOCK["cask"], t) for t, _ in f._typed):
        for w in FRONT:
            if wall_pair(c, w, STOCK["cask"], 0.15): break
    # benches along a front wall for those who drink standing; more light in a big common room (QA round 2: "Overall,
    # they feel just a little bit too empty")
    for w in FRONT:
        if wall_pair(c, w, r"^Bench\d$|^LightBench\d$|^CushionedBench\d$", 0.2, "bench"): break
    c.fill_bare([mk_round4, mk_sitting], most=4, over=3.0, mirror=True, carpet_pad=3.6)
    if c.tiles >= 170: c.lights_balanced(6)
    c.hangings(r"^WallTrophy(Bear|Moose|MountainLion)[12]$", most=5)
    col = c.set_type.setdefault("tapestry colour", c.rng.choice(("Blue", "Red", "Green", "White")))
    c.hangings(rf"^{col}Tapestry\d$", most=4)


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
               r"^WallTrophy(Bear|Moose|MountainLion)[12]$", most=5)


def great_hall(c, plan):
    """A lord's great hall composed on the axis from the door, like a dining hall but grander (QA round 1, the great
    hall set: "The layouts, tables, and chairs are generally pretty good, but the spaces are universally too empty";
    RM-GREATHALL-01: "The six tables on the carpet look good. They just need to be centered more"; -07: the perimeter
    band, "more objects, especially along the northeast wall"; -04: "the table next to the hearth is too close to it"):
    - the far end: the high table across the axis, the lord's chair at its middle facing down the hall with a chair
      either side, on its own carpet, a statue pair flanking it on the far wall (or the hearth behind it);
    - the hearth centred on the other back wall on its brick patch (kit/shells.py), a statue pair flanking it, no table
      within 2.2 units of it;
    - the floor: long boards of tables in mirrored rows either side of the walk, benches down both sides, all on one
      carpet centred under them;
    - mirrored stations by the side walls (statues, braziers, urns), casks and side tables in matching corners, banners
      and trophies at even steps, a band of brick or cobble round the room in three halls of four."""
    f = c.f
    c.wall_pat = VASE
    c.s_makers = [lambda c_, uv: c_.corner_heap("S", S("cask", "barrel"), n=2),
                  lambda c_, uv: c_.corner_lights(("S", "N"), 1.2)]
    ax = axis(c)
    if not ax: return dining_hall(c, plan)
    r = ax["run"]
    # the perimeter band drawn first, so the carpets keep their trim inside it (laid last: band_with_hearth)
    from kit import finish as FIN
    brng = random.Random(zlib.crc32(f"band:{f.spec.d.get('name')}:{f.room.id}".encode()))
    band = brng.random() < FIN.BAND_RATE
    c.carpet_inset = band
    # the hearth: on a back wall other than the far wall, else on the far wall behind the high table
    hearth = None
    for w in BACK:
        rr = c.wall(w)
        if rr and rr is not r:
            hearth = c.focal("fireplace", clear=3.0, wall=w)
            if hearth: break
    behind = False
    if not hearth and c.name_of(r) in BACK:
        hearth = c.focal("fireplace", clear=3.0, wall=c.name_of(r))
        behind = bool(hearth)
    fires = []
    if hearth:
        hr = f._placed_of.get(id(hearth["obj"]))
        if hr: fires.append(hr)
        c.flank(hearth, r"^Statue2[a-h]$", gap=1.2, fam="statue")         # the pair flanking the hearth (round 1)
    def clear_of_fire(u, v, hu, hv, gap=2.2):
        return all(max(abs(u - fr[0]) - hu - fr[2], abs(v - fr[1]) - hv - fr[3]) >= gap for fr in fires)
    # the high table across the far end, on the axis
    depth_far = ax["depth"]
    tt = c.pick_once(r"^Table[1-4]$")
    high = None
    if tt:
        t = f.along_variant(tt, r["side"]) or tt
        hu, hv = f.half(t)
        hp, ha = (hu, hv) if r["line"] == "/" else (hv, hu)
        start = hp + (5.2 if behind else 2.6)
        for d in (start, start + 0.6, start + 1.2, start + 2.0):
            uv = on_axis(c, ax, d)
            if not clear_of_fire(*uv, hu, hv): continue
            n0 = len(f.objects)
            o = c.put(t, *uv)
            if not o: continue
            # the lord's chair at the middle of the far side, facing down the hall, a chair either side of it
            base = f.palette_seat("chair", f.types_of("chair")) or "WoodenChair"
            to_table = ("+" if r["sign"] > 0 else "-") + ("u" if r["line"] == "/" else "v")
            ct = (f.chair_facing.get(base, {}).get(to_table) or {}).get("variant")
            if DEBUG: c.log.append(f"   high table {t} d={d:.1f}: chair base {base} to_table {to_table} -> {ct}; facing keys {list(f.chair_facing.get(base, {}))}")
            if ct and f.ok_type(ct):
                chu, chv = f.half(ct)
                cp = chu if r["line"] == "/" else chv
                seats = [ct for _ in range(3)]
                ca = chv if r["line"] == "/" else chu       # the chair's half width along the wall
                step_ = max(2 * ca + 0.35, ha * 0.62)
                offs = (0.0, -step_, step_)
                got = [c.put(ct, *on_axis(c, ax, d - hp - cp - 0.25, a_)) for a_ in offs]
                if DEBUG: c.log.append(f"   lord's chairs {[bool(g) for g in got]}: {why(f, ct, *on_axis(c, ax, d - hp - cp - 0.25, 0.0))}")
                if not got[0]:
                    for x in f.objects[n0:]: f._remove(x)
                    continue
                if not (got[1] and got[2]):
                    for x in got[1:]:
                        if x: f._remove(x)
            high = dict(obj=o, uv=uv, d=d, hp=hp, ha=ha)
            f._seated.add((uv, t))
            break
    if high:
        far = dict(obj=None, run=r, uv=f._uv_on(r, 0.5, ax["mid"]), along=ax["mid"], ha=max(2.0, high["ha"]), hp=0.4)
        if not behind:
            c.flank(far, r"^Statue2[a-h]$", gap=0.8, fam="statue")
        c.flank_lights(dict(run=r, uv=high["uv"], along=ax["mid"], ha=high["ha"] + 0.8, hp=high["hp"]), gap=0.4,
                       before=-0.4)
    # the boards: long tables end to end in mirrored rows either side of the walk, benches down both sides
    n0 = len(f.objects)
    boards = hall_boards(c, ax, start=(high["d"] + high["hp"] + 2.6) if high else 4.0, clear_of_fire=clear_of_fire)
    if boards:
        # one great carpet under the boards and the high table, centred on them
        recs = [f._placed_of.get(id(o)) for o in f.objects[n0:]] + ([f._placed_of.get(id(high["obj"]))] if high else [])
        recs = [r_ for r_ in recs if r_ and r_[4]]
        if recs:
            bx = (min(r_[0] - r_[2] for r_ in recs), max(r_[0] + r_[2] for r_ in recs),
                  min(r_[1] - r_[3] for r_ in recs), max(r_[1] + r_[3] for r_ in recs))
            if not carpet_box(c, bx, pad=0.8) and c.carpet_inset:
                # too big to keep inside the band: the carpet as before, its trim then laid on the band's brick
                # (band_with_hearth), never no carpet under the boards
                c.carpet_inset = False
                carpet_box(c, bx, pad=0.8)
                c.carpet_inset = True
    c.corner_set("S", r"^SquareTable[12]$|^RoundTable[12]$", 2)
    hearth_rug(c, hearth, gap=1.6)                     # a rug before the hearth, clear of the fire (Q2T-4)
    # the side walls' stations: statues, braziers and urns mirrored down the hall
    f.aisle = dict(run=r, mid=ax["mid"], half=1.6, first=2.0, far=depth_far, door=c.door)
    # (2 units off the side walls: a back wall among them keeps its hangings, kit/objects.py hangs nothing above a piece)
    stations(c, ax, [], [r"^Statue2[a-h]$", r"^Brazier$", VASE], first=(high["d"] + 1.0) if high else 3.0, step=4.4,
             wall_gap=2.0, middle=[VASE, r"^Statue2[a-h]$"] if c.tiles >= 300 else ())
    # (the aisle kept: finish turns the side statues toward it, QA round 2 Q2T-3)
    way_in_urns(c, ax)
    want_l = 4 if c.tiles < 300 else 6
    c.lights_balanced(want_l)
    if len(c.lights) < want_l and hearth: c.flank_lights(hearth, gap=2.8, before=0.9)   # lights before the hearth's statues
    # casks and side tables in matching corners by the door end; the S corner
    c.corner_heap("W", S("cask", "barrel"), n=2)
    c.corner_heap("E", S("cask", "barrel"), n=2)
    # the house's chest centred on a back wall's free stretch; plants in the side corners; side sets mirrored where the
    # floor is still bare (the hall holds as much as before, placed in order: QA round 1, "much more diversity")
    for w in BACK:
        if c.centred_on(w, r"^Chest\d$", "storage"): break
    # a pair of suits of armour on a back wall (rules/rooms/great_hall.md, QA round 1: "suits of armour")
    for w in BACK:
        if c.wall(w) and wall_pair(c, w, r"^TraderArmorRack[12]$", 0.18, "shop_rack"): break
    pl = c.pick_once(r"^(Plant1|Plant3|Plant4|Plant5)$")
    if pl:
        c.put_all([(pl, *c.corner_uv("N", 1.2))])
        for d_ in (1.2, 1.7, 2.3):                     # and a pair in the side corners (rules/rooms/great_hall.md)
            if c.put_all([(pl, *c.corner_uv("W", d_)), (pl, *c.corner_uv("E", d_))], pairing=True): break
    # side sets mirrored about the axis between the boards and the side walls, at even depths down the hall, between
    # the boards and the stations
    mk = exact_set(r"^RoundTable[12]$", 4, gap=0.35)
    reach = min(ax["mid"] - (r["lo"] + 1), (r["hi"] - 1) - ax["mid"])
    first = (high["d"] + high["hp"] + 3.0) if high else 4.0
    depths = [first + (ax["depth"] - 3.0 - first) * fr_ for fr_ in (0.55, 0.8, 0.3)]
    pairs = 0
    for dd in (depths if c.tiles >= 240 else []):
        if pairs >= max(1, c.tiles // 120): break
        for off in (reach - 3.4, reach - 4.0, reach - 4.6, reach - 2.8, reach - 5.4, reach - 6.2, reach - 7.0):
            if off < 5.0: continue
            if not all(clear_of_fire(*on_axis(c, ax, dd, s_ * off), 2.5, 2.5, gap=3.4) for s_ in (-1, 1)): continue
            n0 = len(f.objects)
            if mk(c, on_axis(c, ax, dd, -off)) and mk(c, on_axis(c, ax, dd, off)):
                pairs += 1; break
            for x in f.objects[n0:]: f._remove(x)
    col = c.set_type.setdefault("tapestry colour", c.rng.choice(("Blue", "Red", "Green", "White")))
    c.hangings(rf"^{col}Tapestry\d$|^WallTrophy(Bear|Moose|MountainLion)[12]$", step=3.4, most=7)
    # the perimeter band of brick or cobble (RM-GREATHALL-07), from the rated-rooms pass (kit/finish.py lay_band)
    if band: band_with_hearth(f, brng, hearth)


def band_with_hearth(f, rng, hearth=None):
    """The great hall's band of brick or cobble one square wide round the whole room (kit/finish.py lay_band, the user's
    RM-GREATHALL-07), with the hearth's patch made one with it: the hearth's three squares along its wall by two deep
    laid in the band's own brick, so the patch runs to the wall and never meets a second patch (QA round 2, Q2C-5:
    RM-GREATHALL-02 "The brick hearth around the oven must connect to the wall on both sides"; -03 "The brick hearth
    around the oven conflicts with the brick cobblestone around the border of the room"). A hall with a hearth takes a
    band of brick (a hearth on grey cobbles reads as outdoor paving: kit/shells.py lay_zones). Returns the tiles laid."""
    from kit import finish as FIN
    from kit import shells as SH
    room, spec = f.room, f.spec
    main = room.floor
    sq = {((x + y) // 2, (x - y) // 2) for (x, y) in room.tiles}
    ring = {s for s in sq if any((s[0] + a, s[1] + b) not in sq for a in (-1, 0, 1) for b in (-1, 0, 1))}
    gaps = [d.gap for d in room.doors]
    tile = lambda s: (s[0] + s[1], s[0] - s[1])
    # a carpet's trim square on the ring takes the band's brick under the trim (QA round 3, RM-GREATHALL-01: the band had
    # stopped wherever a carpet's trim lay on its squares): the band runs unbroken, the carpet's trim drawn on its brick
    trim = lambda t: any(m_.startswith("Rug") for m_ in spec.local_from.get(t, ()))
    tiles, trims = set(), {}
    for s in ring:
        t = tile(s)
        if any(max(abs(t[0] - g[0]), abs(t[1] - g[1])) <= 1 for g in gaps): continue
        if (spec.floor.get(t) or main).startswith("Rug"): continue
        if t in spec.local_blend:
            if not trim(t): continue
            trims[t] = [m_ for m_ in spec.local_from[t] if m_.startswith("Rug")]
        tiles.add(t)
    if len(tiles) < 0.6 * len(ring): return set()
    mats = [m for m in FIN.BAND if m != main and frozenset((m, main)) not in SH._never()]
    if not mats: return set()
    mat = rng.choice(mats)
    if hearth and hearth.get("obj"):
        brick = [m for m in mats if re.search(r"[Bb]rick", m)]
        if brick: mat = brick[0]
        hs = SH.hearth_squares(hearth["obj"], sq, ring, SH._things())
        for s in hs:
            t = tile(s)
            if any(max(abs(t[0] - g[0]), abs(t[1] - g[1])) <= 3 for g in gaps): continue
            if (spec.floor.get(t) or main).startswith("Rug") or t in spec.local_blend: continue
            tiles.add(t)
    for t in tiles: spec.tile(*t, main)                 # (a band laid before furnishing goes under this one)
    out = SH.lay_patch(spec, room, tiles, mat)
    for t, rugs in trims.items():
        for rg in rugs: spec.edge_over[(rg, mat)] = F.carpet_trim(rg, mat)
    return out


def hall_boards(c, ax, start, clear_of_fire, gap_rows=None):
    """Long boards (tables end to end, along the axis) in mirrored rows either side of the walk, a bench each side of
    every piece. Rows in pairs, the outer pair only where the hall is wide; boards along the depth of the hall in
    lengths of up to three pieces with an aisle between. Every pair placed both or neither. Returns the tables."""
    f = c.f
    r = ax["run"]
    tt = c.pick_once(r"^Table[1-4]$")
    if not tt: return 0
    depth_dir_u = r["line"] == "/"                    # the depth runs along u for a NW/SE wall
    stem = re.sub(r"\d+$", "", tt)
    sibs = [s_ for s_ in (f"{stem}{d}" for d in "1234") if f.ok_type(s_)]
    t = next((s_ for s_ in sibs if (f.half(s_)[0] > f.half(s_)[1]) == depth_dir_u), None)
    if not t: return 0
    hu, hv = f.half(t)
    hl, hs = (hu, hv) if depth_dir_u else (hv, hu)
    bench = c.pick_once(r"^Bench\d$|^CushionedBench\d$")
    cell_w = 2 * hs + 2 * 1.2 + 1.6                     # a board, a bench each side, the way between rows
    reach = min(ax["mid"] - (r["lo"] + 1), (r["hi"] - 1) - ax["mid"]) - 2.4
    offs = []
    o1 = 1.6 + 1.2 + hs                                 # the walk 3.2 wide, a bench, half a board
    while o1 + hs + 1.2 <= reach and len(offs) < 2:
        offs.append(o1); o1 += cell_w
    if not offs: return 0
    end = ax["depth"] - 3.0                             # clear of the door end
    piece = 2 * hl + 0.04
    # the boards share the room's table cap (kit/roomtypes.py great_hall: the user, 2026-10-04, "4-6 sets fewer"), one
    # kept back for the S corner's side table: rows x sides x blocks x pieces within it, the blocks spread evenly down
    # the hall (no bare far end, no bare door end)
    cap = f.repeat_cap("table") or 12
    # (the S corner's table besides, and in a hall of 240 tiles or more a mirrored pair of side sets)
    budget = cap - f._fam_n["table"] - (3 if c.tiles >= 240 else 1)
    L = end - start
    best = None
    for nr in range(len(offs), 0, -1):                 # rows of boards either side of the walk
        per_row = budget // (2 * nr)
        for nb in (3, 2, 1):                           # boards down the hall
            k = min(3, per_row // nb)                  # pieces end to end in a board
            if k < 1: continue
            gap = (L - nb * k * piece) / (nb + 1)
            if gap < 1.6: continue
            # the most tables, in long boards (two pieces or more), spread so no stretch of the hall is bare
            score = 2 * nr * nb * k * 10 + (25 if k >= 2 else 0) - 3 * max(0.0, gap - 5.0)
            if best is None or score > best[0]: best = (score, nr, nb, k, gap)
    if not best: return 0
    _, nr, nb, k, gap = best
    offs = offs[:nr]
    if DEBUG: c.log.append(f"   boards: wall {c.name_of(r)} mid {ax['mid']:.1f} depth {ax['depth']:.1f} start {start:.1f} "
                           f"offs {[round(o, 1) for o in offs]} blocks {nb}x{k} gap {gap:.1f} cap {cap} budget {budget}")
    got = 0
    for b_ in range(nb):
        d0 = start + gap * (b_ + 1) + b_ * k * piece + hl
        for off in offs:
            pts = []
            for j_ in range(k):
                dd = d0 + j_ * piece
                pts += [on_axis(c, ax, dd, -off), on_axis(c, ax, dd, off)]
            if not all(clear_of_fire(u, v, hu, hv) for u, v in pts): continue
            placed = c.put_all([(t, u, v, dict(touch=True)) for u, v in pts], pairing=True)
            if DEBUG and not placed: c.log.append(f"   board {b_} off {off:.1f}: {[why(f, t, u, v, touch=True) for u, v in pts][:6]}")
            if not placed: continue
            n_before = len(f.objects)
            ok = True
            bpat = re.escape(re.sub(r"\d+$", "", bench)) + r"\d" if bench else None
            for u, v in pts:
                if f.seats_around((u, v), t, 2, "bench", gap=0.25, pat=bpat) < 1: ok = False
            if not ok:
                for x in f.objects[n_before:] + placed: f._remove(x)
                continue
            for u, v in pts: f._seated.add(((u, v), t))
            got += len(pts)
    return got


def ogre_hall(c, plan):
    """The ogres' feast, minimal but balanced: the fire pit in the middle, crude tables mirrored either side of it
    with their stools, meat between them, sacks and barrels heaped in matching corners, a carcass hung in the N
    corner, skulls on the back walls."""
    f = c.f
    c.wall_pat = r"^Barrel2?$"
    c.s_makers = [lambda c_, uv: c_.corner_heap("S", [r"^Barrel2?$", r"^OgreSack\d$"], n=3)]
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
        c.corner_heap(corner, [r"^Barrel2?$", r"^OgreSack\d$", r"^PiledBarrels\d$", r"^OgreSack\d$"], n=4)
    c.corner_heap("S", [r"^Barrel2?$", r"^OgreSack\d$"], n=2)
    c.corner_heap("N", [r"^OgreHutCarcassBig$|^OgreHutCarcass$"], n=1, d=1.4)
    front_heaps(c, ("SE", "SW"), [[r"^Barrel2?$", r"^OgreSack\d$"]], n=2)
    for off in (3.4, 3.0, 3.8):
        pts = [(cu, cv - off), (cu, cv + off)] if long_u else [(cu - off, cv), (cu + off, cv)]
        if c.put_all([("OgreHutMeat", *p) for p in pts]): break
    c.hangings(r"^OgreHutWallSkull[1-4]$", most=4, step=3.6)


# ---- the ceremonial rooms --------------------------------------------------------------------------------------------
def stations(c, ax, inner, outer, first=4.0, step=4.2, inner_off=None, light_inner=False, end=2.4, middle=(),
             wall_gap=0.4, exact=False):
    """The ceremonial rooms' rhythm down the axis: at even steps from the far wall toward the door, a mirrored pair
    beside the aisle (inner: columns, statues, braziers in turn) and a mirrored pair by the side walls (outer: benches,
    urns, statues in turn; a bench facing the aisle), each pair both or neither; in a wide room a third pair half way
    between them (middle: QA round 2, RM-THRONEROOM-03 "Fill the southwestern side of the room. It's too empty").
    Returns the pieces placed."""
    f = c.f
    r, mid = ax["run"], ax["mid"]
    half = (f.aisle or {}).get("half", 1.5)
    a_, b_ = (c.vW, c.vE) if r["line"] == "/" else (c.uN, c.uS)     # the side walls' lines (the room's own width)
    reach = min(mid - a_, b_ - mid) - 1
    depth_max = ax["depth"] - end
    got, d, k = 0, first, 0
    step = max(step, (depth_max - first) / 6.0)          # six stations at most: a rhythm, not a forest of columns
    if DEBUG: c.log.append(f"   stations: run {c.name_of(r)} mid {mid:.1f} reach {reach:.1f} depth {ax['depth']:.1f}")
    while d <= depth_max:
        if inner:
            done = False
            for j in range(1 if exact else len(inner)):   # the station's own kind first, else the next that fits there
                pat = inner[(k + j) % len(inner)]
                t = c.pick_once(pat)
                if not t: continue
                io = inner_off or (half + 0.9 + max(f.half(t)))
                for o in ((io,) if exact else (io, io + 0.5, io + 1.0, io + 1.6)):   # (exact: one straight line)
                    n = mirrored(c, ax, t, d, o, light=light_inner and pat == inner[-1])
                    if n: got += n; done = True; break
                if done: break
        if outer and reach >= 6.0:
            pat = outer[k % len(outer)]
            t = c.pick_once(pat)
            if t:
                hh = max(f.half(t))
                seat = F._family_of(t) == "bench"
                for o in (reach - hh - wall_gap, reach - hh - wall_gap - 0.5, reach - hh - wall_gap - 1.1):
                    if o < (inner_off or half + 2.0) + 2.0: break
                    n = mirrored(c, ax, t, d, o, face=seat)
                    if n: got += n; break
        if middle and reach >= 9.5:
            pat = middle[k % len(middle)]
            t = c.pick_once(pat)
            if t:
                io = inner_off or (half + 2.0)
                mo = (io + reach - 1.0) / 2
                for o in (mo, mo + 0.6, mo - 0.6):
                    n = mirrored(c, ax, t, d, o, face=F._family_of(t) == "bench")
                    if n: got += n; break
        d += step; k += 1
    return got


def hearth_rug(c, p, gap=1.3):
    """A rug before a hearth, a step clear of the fire (QA round 2, Q2T-4; RM-TAVERN-01/03/04/05: "The bearskin rug is
    just slightly too close to the fireplace"): its near edge `gap` units past the hearth's front (furnish.rug_before
    laid it 0.2 off)."""
    if not p: return False
    f = c.f
    r = p["run"]
    front = abs((p["uv"][0] if r["line"] == "/" else p["uv"][1]) - r["coord"]) + p["hp"]
    for g in (gap, gap + 0.5, gap + 1.0):
        o = f.place_rug(r, front + g, p["along"])
        if not o: continue
        rec = f._placed_of.get(id(o))
        if rec and any(rec[0] + rec[2] > b[0] and rec[0] - rec[2] < b[1] and rec[1] + rec[3] > b[2] and rec[1] - rec[3] < b[3]
                       for b in f.carpet_boxes):
            f._remove(o); continue                      # never on a carpet
        return True
    return False


def way_in_urns(c, ax):
    """Urns flanking the way in at the near end of the axis, of another kind than the stations' urns (a pair is one
    kind; the room holds several: QA round 1, Q1A-2)."""
    own = re.sub(r"(N|S|E|W|NE|NW|SE|SW)$", "", c.pick_once(VASE) or "")
    others = [x for x in c.types(VASE) if not x.startswith(own or "~")]
    t = c.rng.choice(others) if others else c.pick_once(VASE)
    if not t: return 0
    half = (c.f.aisle or {}).get("half", 1.6)
    for d_ in (ax["depth"] - 1.4, ax["depth"] - 2.0, ax["depth"] - 2.8):
        for o_ in (half + 2.2, half + 3.0):
            if mirrored(c, ax, t, d_, o_): return 2
    return 0


def gallery(c, plan):
    """Paintings at even steps along both back walls, mirrored; a runner down the axis from the door; statues and a
    pair of flame basins or orreries mirrored down it; benches and urns mirrored by the side walls; plants in the four
    corners; lights in matching corners."""
    f = c.f
    c.wall_pat = VASE
    c.s_makers = [lambda c_, uv: c_.put_all([(c_.pick_once(VASE), *c_.corner_uv("S", 1.2)), (c_.pick_once(VASE), *c_.corner_uv("E", 1.2))]) and 2,
                  lambda c_, uv: c_.corner_heap("S", [VASE], n=1, d=1.2),
                  lambda c_, uv: c_.corner_lights(("S", "E"), 1.2)]
    # QA round 2 (Q2C-1): down the room's length on its own middle (RM-GALLERY-01/02 "not centered in the room"; -04
    # "Awkward shape for a gallery with a lot of open room and dead space on the north, west, and southeast sides": the
    # walk had crossed a long gallery from a door in its long wall), the runner centred on the axis (-03), the benches
    # facing the aisle (-01)
    ax = axis(c, long_axis=True)
    if ax:
        door_walk(c, ax)
        # the centrepiece at the far end of the walk, facing the way in: an orrery between a pair of flame basins
        r = ax["run"]
        cp = c.pick(r"^Orrery2$")
        for d_ in (2.4, 3.0, 3.6, 4.2, 4.8, 5.4, 6.0):
            if cp and c.put(cp, *on_axis(c, ax, d_)):
                mirrored(c, ax, c.pick_once(r"^DunMirFlameBasinLit$") or "Brazier", d_ - 0.2, 2.6)
                break
        runner(c, ax, 4.4, ax["depth"] - 1.0)
        f.aisle = dict(run=r, mid=ax["mid"], half=1.4 if runner_squares(ax) == 2 else 2.4, first=2.0, far=ax["depth"],
                       door=c.door)
        stations(c, ax, [r"^Statue2[aceg]$", r"^DunMirFlameBasinLit$"],
                 [r"^Bench[1-4]$|^CushionedBench\d$", VASE], first=5.6, step=4.4)
    c.lights_balanced(4 if c.tiles >= 150 else 2)
    t = c.pick(r"^Plant[1345]$")
    if t:
        for pair in (("W", "E"), ("N", "S")):
            c.put_all([(t, *c.corner_uv(pair[0], 1.1)), (t, *c.corner_uv(pair[1], 1.1))])
    c.hangings(r"^Painting[12]$|^BlueTapestry[24]$", step=3.2, most=7, first=r"^Painting")


HALL_WIDE = 9.5       # a hall this many units or more from its axis to a side wall (inside the pieces' reach) is wide
HALL_NAVE = 0.45      # a wide hall's colonnade stands this share of the way out to its side walls (Q3C-7)


def hall_nave(c, ax, side, first=5.4, step=4.0, end=2.4):
    """A wide hall's colonnade offset from its axis: HALL_NAVE of the way out to the side walls, moved in or out a step
    at a time to the line the doors' ways in (Furnisher.far_ways) cross at the fewest stations, so the colonnade runs
    straight from end to end, a station left empty where a side door's way crosses it (QA round 3: RM-HALL-01's second
    door had pushed its first pairs out, kinking the line; RM-HALL-03's side doors had put braziers in the columns'
    places)."""
    f = c.f
    half = (f.aisle or {}).get("half", 1.6)
    io0 = round(HALL_NAVE * (side - 1), 1)
    step = max(step, (ax["depth"] - end - first) / 6.0)
    def blocked(o):
        n, d = 0, first
        while d <= ax["depth"] - end:
            for sg in (-1, 1):
                u, v = on_axis(c, ax, d, sg * o)
                if any(u + 1.0 > b[0] and u - 1.0 < b[1] and v + 1.0 > b[2] and v - 1.0 < b[3] for b in f.far_ways):
                    n += 1; break
            d += step
        return n
    cands = [round(io0 + 0.6 * k, 1) for k in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5)]
    cands = [o for o in cands if half + 2.0 <= o <= side - 4.5] or [io0]
    best = min(cands, key=lambda o: (blocked(o), abs(o - io0)))
    if DEBUG: c.log.append(f"   hall nave {best:.1f} (first try {io0:.1f}, {blocked(best)} stations crossed by a door's way)")
    return best


def hall(c, plan):
    """A colonnade in mirrored pairs either side of the aisle from the door, statues and braziers between the columns,
    benches and urns mirrored by the side walls, a statue pair flanking the middle of the far wall, lights in matching
    corners, banners of one colour at even steps on the back walls."""
    f = c.f
    c.wall_pat = VASE
    c.s_makers = [lambda c_, uv: c_.put_all([(c_.pick_once(VASE), *c_.corner_uv("S", 1.2)), (c_.pick_once(VASE), *c_.corner_uv("E", 1.2))]) and 2,
                  lambda c_, uv: c_.corner_heap("S", [VASE], n=1, d=1.2),
                  lambda c_, uv: c_.corner_lights(("S", "E"), 1.2)]
    # QA round 2 (Q2C-2): down the room's length on its own middle (RM-HALL-02: "Center the hall in the room"), the
    # benches facing the aisle (RM-HALL-01: "they should face southwest")
    ax = axis(c, long_axis=True)
    if ax:
        door_walk(c, ax)
        f.aisle = dict(run=ax["run"], mid=ax["mid"], half=1.6, first=2.4, far=ax["depth"], door=c.door)
        r = ax["run"]
        # the far end first, so the colonnade keeps clear of it: a statue pair flanking the middle of the far wall, the
        # house's chest between them with lights flanking it, flame basins before them
        far = dict(obj=None, run=r, uv=f._uv_on(r, 0.5, ax["mid"]), along=ax["mid"], ha=1.2, hp=0.4)
        c.flank(far, r"^Statue2[a-h]$", gap=1.2, fam="statue")
        for a_ in (ax["mid"], ax["mid"] - 1.0, ax["mid"] + 1.0):
            res = c.on_wall(c.pick(r"^DunMirChest\d$|^Chest\d$", "storage") or "Chest1", r, a_, "storage")
            if res:
                c.flank_lights(anchor_of(c, res, r), gap=0.4, before=0.4)
                break
        # a colonnade down the aisle, statues and braziers between its columns (RM-HALL-05, a small square hall: "This
        # does not look like a hall at all": a column at every other station, at every size)
        # QA round 3 (Q3C-7): RM-HALL-01/03, square halls 24 and 34 units across: "Incoherent, random, cluttered with
        # too many pillars and statues", where the long halls 02 and 04 (5 of 5) have one colonnade a side and benches
        # by the walls. The square halls had filled their width with a third rank of urns and statues between the
        # colonnade and the benches, and urns among the benches: three ranks of statue-like pieces a side. Every hall
        # now has the long halls' plan: one colonnade a side, set out to a wide hall's width (the nave as wide as the
        # hall is), benches alone by the side walls, urns flanking the way in only in a narrow hall.
        side = min(ax["mid"] - (c.vW if r["line"] == "/" else c.uN), (c.vE if r["line"] == "/" else c.uS) - ax["mid"])
        wide = side - 1 >= HALL_WIDE
        io = hall_nave(c, ax, side, step=4.0 if c.tiles >= 130 else 3.4) if wide else None
        mirrored(c, ax, c.pick_once(r"^DunMirFlameBasinLit$") or "Brazier", 2.6, (io - 0.4) if wide else 3.2)
        stations(c, ax, [r"^Column[5-8]$", r"^Statue2[a-h]$", r"^Column[5-8]$", r"^Brazier$"],
                 [r"^Bench[1-4]$|^LightBench\d$|^CushionedBench\d$"] + ([] if wide else [VASE]),
                 first=5.4, step=4.0 if c.tiles >= 130 else 3.4, light_inner=True, inner_off=io, exact=wide)
        if not wide: way_in_urns(c, ax)
        # plants in the far corners (rules/rooms/hall.md: "plants in the corners")
        pl = c.pick_once(r"^(Plant1|Plant3|Plant4|Plant5)$")
        reach = min(ax["mid"] - (c.vW if r["line"] == "/" else c.uN), (c.vE if r["line"] == "/" else c.uS) - ax["mid"])
        if pl:
            for d_, o_ in ((1.3, reach - 1.3), (1.8, reach - 1.8), (2.4, reach - 2.4)):
                if mirrored(c, ax, pl, d_, o_): break
    else:
        f.colonnade(gap=4.2, aisle=3.2)
    c.corner_lights(("W", "E"), 1.0)
    c.lights_balanced(4 if c.tiles >= 150 else 2)
    col = c.rng.choice(("Blue", "Red", "Green", "White"))
    c.hangings(rf"^{col}Tapestry\d$" if c.f.style != "dunmir" else r"^DunMirHangingShield\d+$",
               step=3.6, most=6)


# QA round 3 (Q3C-6), the throne room set: "Individually, they are all very good. But as a whole, they are very
# repetitive and all too similar. Add some variance and more object diversity." All five had been one plan (a runner
# lined with braziers and columns, statues and benches by the walls, the same throne setting). A batch now draws its
# layouts in strict rotation (as the chapels' altars, Q2S-1: no layout twice while another that fits is unused), each
# a different treatment of the throne, the floor, the side walls and the pieces, after Westwood's four throne rooms
# (rules/rooms/throne_room.md archetypes) and a court of the kit's own:
# - processional: round 3's room, kept as it was rated (5 of 5): the runner lined with braziers between pairs of
#   columns, statues flanking the throne, chests, benches, statues and urns by the side walls;
# - colonnade (Westwood's dressed walls): a broad carpet down the middle of a bare floor, cathedral or marble columns
#   standing against the side walls with statues of another kind between them, flame basins flanking the throne;
# - ringed seat: the throne a step out from its wall ringed by four candelabras and framed by a pair of columns, a
#   square of obelisks before it, statues by the side walls, braziers flanking the way in, plants in the front corners;
# - audience hall: rows of benches facing the throne either side of the runner, flame basins before the dais, a
#   statue pair flanking the throne, candelabras at the ends of the front rows;
# - garden court: the runner between a pair of orb pools, plants and ferns in pairs down the side walls, statues
#   between them, benches by the pools, plants flanking the throne.
THRONE_LAYOUTS = (("processional", 1.0), ("colonnade", 1.0), ("ringed", 1.0), ("audience", 1.0), ("garden", 1.0))
STATUE1 = r"^Statue1[a-h]$"
STATUE2 = r"^Statue2[a-h]$"
BENCH = r"^Bench[1-4]$|^CushionedBench\d$"
CHESTS = r"^DunMirChest\d$|^Chest\d$"
PLANTS = r"^(Plant1|Plant3|Plant4|Plant5|PlantFern[1-4])$"


def throne_layout(c):
    """This room's layout from THRONE_LAYOUTS, in strict rotation over the map's throne rooms (Q3C-6), among those its
    floor fits."""
    from kit.sacred import _spread
    f = c.f
    nw = c.wall("NW")
    depth = f._depth_of(nw) if nw else 0
    width = c.vE - c.vW
    fits = dict(processional=True, colonnade=width >= 14, ringed=depth >= 16, audience=depth >= 16 and width >= 13,
                garden=width >= 15 and depth >= 14)
    if DEBUG: c.log.append(f"   throne room {depth:.0f} deep, {width:.0f} wide: fits {[k for k, v in fits.items() if v]}")
    return _spread(f, "throne_layout", THRONE_LAYOUTS, ok=lambda n: fits[n], strict=True) or "processional"


def throne_reach(c, ax):
    """How far the floor runs from the axis to the nearer side wall (the stations' reach)."""
    r = ax["run"]
    a_, b_ = (c.vW, c.vE) if r["line"] == "/" else (c.uN, c.uS)
    return min(ax["mid"] - a_, b_ - ax["mid"]) - 1


def broad_carpet(c, ax, near, far, half):
    """A carpet down the middle of the room, `half` units either side of the axis from `near` to `far` units off the axis
    wall, centred on the axis as drawn (carpet_rect). Nothing stands on it. Returns True when laid."""
    f = c.f
    r = ax["run"]
    for h_, n_, f_ in ((half, near, far), (half - 1, near, far), (half, near + 2, far - 2), (half - 2, near, far)):
        if h_ < 2.5 or f_ - n_ < 6: continue
        (u0, v0), (u1, v1) = on_axis(c, ax, n_, -h_), on_axis(c, ax, f_, h_)
        cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
        nu, nv = max(2, int(abs(u1 - u0) / 2)), max(2, int(abs(v1 - v0) / 2))
        cr = c.carpet_rect(cu, cv, nu, nv)
        if not cr: continue
        cen = cr[0][1] if r["line"] == "/" else cr[0][0]
        if abs(cen - ax["mid"]) > 0.26: continue
        if c.lay(cr[1], nu, nv):
            b = f.carpet_boxes[-1]
            f.runner_boxes.append((b[0], b[1], b[2] - SQUARE_V, b[3] - SQUARE_V))
            return True
    return False


def way_in_columns(c, ax, half):
    """A pair of the room's columns framing the way in, near the door end of the axis (the type's two columns placed
    with a purpose, not left to the finishing pass to stand alone by a wall). Returns the pieces placed."""
    t = c.pick_once(r"^Column[5-8]$") or "Column5"
    for d_ in (ax["depth"] - 2.6, ax["depth"] - 3.4, ax["depth"] - 4.4, ax["depth"] - 5.4):
        for o_ in (half + 1.6, half + 2.4, half + 3.2, half + 4.0):
            if mirrored(c, ax, t, d_, o_): return 2
    return 0


def facing_throne(c, ax, t):
    """The variant of a seat with its back to the wall across from the throne (it faces the throne), else t."""
    f = c.f
    r = ax["run"]
    op = next((rr for rr in f.g.runs if rr["line"] == r["line"] and rr["sign"] == -r["sign"]), None)
    return (f.side_variant(t, op, F._family_of(t)) if op else None) or t


def throne_room(c, plan):
    """The throne across from the door on the NW wall facing it, the room composed in one of THRONE_LAYOUTS (Q3C-6):
    each its own treatment of the throne, the floor and the side walls; lights in matching corners; hangings of one
    colour at even steps on the back walls."""
    f = c.f
    c.wall_pat = VASE
    c.s_makers = [lambda c_, uv: c_.put_all([(c_.pick_once(VASE), *c_.corner_uv("S", 1.2)), (c_.pick_once(VASE), *c_.corner_uv("E", 1.2))]) and 2,
                  lambda c_, uv: c_.corner_heap("S", [VASE], n=1, d=1.2),
                  lambda c_, uv: c_.corner_lights(("S", "E"), 1.2)]
    # QA round 2 (Q2C-3): the throne on the room's own middle (RM-THRONEROOM-02/05: "The room is not centered"), the
    # runner centred under its aisle, the benches facing the aisle, and a third pair of statues and urns between the
    # aisle and the side walls in a wide room (-03: "Fill the southwestern side of the room. It's too empty")
    layout = throne_layout(c)
    c.log.append(f"throne room layout {layout}")
    nw = c.wall("NW")
    th = f.place_throne(depth=4.6 if layout == "ringed" else 2.9, runner=False, at=room_mid(c, nw) if nw else None)
    if not th and layout == "ringed":
        layout = "processional"
        th = f.place_throne(depth=2.9, runner=False, at=room_mid(c, nw) if nw else None)
    if not th:
        f.colonnade(gap=5.0, aisle=3.0)
        c.lights_balanced(4)
        return
    ax = dict(run=th["run"], mid=th["along"], depth=f._depth_of(th["run"]))
    reach = throne_reach(c, ax)
    first = th["hp"] + 5.0
    hang = None
    if layout == "processional":
        c.flank(th, STATUE2, gap=0.8, fam="statue")
        c.flank(th, CHESTS, gap=3.4, fam="storage")
        f.flank_lights(th, 0.9)
        runner(c, ax, 2.9 + 1.0, ax["depth"])
        door_walk(c, ax)
        stations(c, ax, [r"^Column[5-8]$", r"^Brazier$"], [BENCH, STATUE2, VASE],
                 first=first, step=4.2, light_inner=True, middle=[STATUE2, VASE])
        way_in_urns(c, ax)
    elif layout == "colonnade":
        # flame basins either side of the throne, then a pair of statues; a broad carpet the width of the nave; the
        # columns standing against the side walls at even steps with statues between them; the floor bare; candelabras
        # flanking the way in; paintings on the back walls
        r = th["run"]
        dt = abs((th["uv"][0] if r["line"] == "/" else th["uv"][1]) - r["coord"])
        basin = c.pick_once(r"^DunMirFlameBasinLit$") or "Brazier"
        for o_ in (th["ha"] + 1.2, th["ha"] + 1.8, th["ha"] + 2.4):
            if mirrored(c, ax, basin, dt + 0.6, o_, light=True): break
        c.flank(th, STATUE1, gap=2.8, fam="statue") or c.flank(th, STATUE2, gap=2.8, fam="statue")
        half = min(reach - 3.6, 5.0)
        broad_carpet(c, ax, 2.9 + 1.0, ax["depth"] - 1.0, half)
        door_walk(c, ax)
        col = r"^CathedralColumn[1-3]$" if c.types(r"^CathedralColumn[1-3]$") else r"^MarbleColumn$|^Column[5-8]$"
        st = max(3.6, (ax["depth"] - 2.4 - (first - 0.6)) / 6.0)
        stations(c, ax, [], [col, STATUE1 if c.types(STATUE1) else STATUE2], first=first - 0.6, step=3.6,
                 wall_gap=0.5)
        # candelabras in pairs along the carpet's edges, before every other station (the colonnade lit, not lined)
        lt = f.light_type()
        d_ = first - 0.6
        while d_ <= ax["depth"] - 3.0:
            for o_ in (half + 1.0, half + 1.5):
                if mirrored(c, ax, lt, d_, o_, light=True): break
            d_ += 2 * st
        for d_ in (ax["depth"] - 2.0, ax["depth"] - 2.8):          # candelabras flanking the way in
            if mirrored(c, ax, lt, d_, half + 1.2, light=True): break
        hang = r"^Painting[12]$"
    elif layout == "ringed":
        # the throne out from its wall, a candelabra at each corner of it and a pair of columns framing it; a square of
        # obelisks before it; statues by the side walls; braziers by the way in; plants in the front corners (a throne
        # room takes no chest: the object knowledge base's cap for the type)
        r = th["run"]
        dt = abs((th["uv"][0] if r["line"] == "/" else th["uv"][1]) - r["coord"])
        lt = f.light_type()
        ring = None
        for o_ in (th["ha"] + 1.0, th["ha"] + 1.6, th["ha"] + 2.2, th["ha"] + 2.8):
            n_ = len(f.objects)
            if mirrored(c, ax, lt, dt - th["hp"] - 0.4, o_, light=True) and                     mirrored(c, ax, lt, dt + th["hp"] + 0.9, o_, light=True):
                ring = o_; break
            for x in f.objects[n_:]:                       # the four lights or none
                f._remove(x)
                if c.lights: c.lights.pop()
                if f.ring_lights: f.ring_lights.pop()
        for o_ in ((ring or th["ha"]) + 2.4, (ring or th["ha"]) + 3.2, (ring or th["ha"]) + 4.0):
            if mirrored(c, ax, c.pick_once(r"^Column[5-8]$") or "Column5", dt, o_): break
        runner(c, ax, dt + th["hp"] + 2.6, ax["depth"])
        door_walk(c, ax)
        ob = c.pick(r"^Obelisk$") or c.pick_once(STATUE2)
        half = (f.aisle or {}).get("half", 1.5)
        for d0 in (dt + th["hp"] + 3.2, dt + th["hp"] + 4.0, dt + th["hp"] + 4.8):
            n_ = len(f.objects)
            if mirrored(c, ax, ob, d0, half + 1.8) and mirrored(c, ax, ob, d0 + 4.2, half + 1.8): break
            for x in f.objects[n_:]: f._remove(x)
        stations(c, ax, [], [STATUE2], first=first + 6.0, step=5.0, wall_gap=0.5)
        for d_ in (ax["depth"] - 1.6, ax["depth"] - 2.4):
            if mirrored(c, ax, "Brazier", d_, half + 2.0, light=True): break
        pl = c.pick_once(PLANTS)
        if pl: c.put_all([(pl, *c.corner_uv("S", 1.2)), (pl, *c.corner_uv("E", 1.2))], pairing=True)
    elif layout == "audience":
        # benches in rows facing the throne either side of the runner, the dais between flame basins and statues; a
        # pair of columns at the way in
        c.flank(th, STATUE2, gap=0.8, fam="statue")
        mirrored(c, ax, c.pick_once(r"^DunMirFlameBasinLit$") or "Brazier", th["hp"] + 3.4, 2.8)
        runner(c, ax, 2.9 + 1.0, ax["depth"])
        door_walk(c, ax)
        half = (f.aisle or {}).get("half", 1.5)
        way_in_columns(c, ax, half)
        b0 = c.pick_once(BENCH)
        rows = 0
        if b0:
            # an audience hall's pews: rows of two a side, as many rows as its floor takes (the type's two benches a
            # side wall do not apply: these are its seats, as a chapel's pews)
            rp = dict(f.ident.get("repeat", {}))
            rp["bench"] = (10, 16)
            f.ident = dict(f.ident, repeat=rp)
            bt = facing_throne(c, ax, b0)
            hu, hv = f.half(bt)
            ha = hv if ax["run"]["line"] == "/" else hu           # its half length across the room
            d, last = first + 3.0, None
            while d <= ax["depth"] - 6.0 and rows < 5:
                n_side = 0
                for k in range(2):
                    o_ = half + 1.0 + ha + k * (2 * ha + 0.3)
                    if o_ + ha > reach - 1.5: break
                    if not mirrored(c, ax, bt, d, o_): break
                    n_side += 1
                if n_side:
                    rows += 1
                    if last is None: last = (d, n_side)
                d += 3.2
            if last:
                o_ = half + 1.0 + (2 * ha + 0.3) * last[1] + 0.6
                mirrored(c, ax, f.light_type(), last[0], o_, light=True)
        stations(c, ax, [], [STATUE1 if c.types(STATUE1) else VASE], first=first, step=6.4, wall_gap=0.5)
    else:   # garden
        # plants flanking the throne, then statues; a pair of orb pools either side of the runner with benches by
        # them; plants in pairs lining the runner; statues of another kind and ferns by the side walls; a pair of
        # columns at the way in
        pl = c.pick_once(PLANTS)
        if pl: c.flank(th, "^" + re.escape(pl) + "$", gap=0.8)
        c.flank(th, STATUE1 if c.types(STATUE1) else STATUE2, gap=2.4, fam="statue")
        runner(c, ax, 2.9 + 1.0, ax["depth"])
        door_walk(c, ax)
        half = (f.aisle or {}).get("half", 1.5)
        way_in_columns(c, ax, half)
        pool = "OrbPoolWithOrb" if f.ok_type("OrbPoolWithOrb") else None
        if pool:
            mid_d = (first + ax["depth"] - 2.0) / 2
            depths = sorted((first + 1.0 + 0.5 * k for k in range(int(2 * (ax["depth"] - first - 8.0)))),
                            key=lambda x: abs(x - mid_d))
            done = False
            for dd in depths:
                for o_ in (half + 4.0, half + 4.8, half + 3.4, half + 5.6):
                    if o_ > reach - 2.0: continue
                    if mirrored(c, ax, pool, dd, o_):
                        done = True
                        b = c.pick_once(BENCH)
                        if b:
                            for dd2 in (dd + 3.4, dd - 3.4, dd + 4.2, dd - 4.2):
                                if mirrored(c, ax, b, dd2, o_, face=True): break
                        break
                if done: break
        fern = c.pick(r"^PlantFern[1-4]$") or pl
        stations(c, ax, [r"^(Plant1|Plant3|Plant4|Plant5)$"], [STATUE1 if c.types(STATUE1) else STATUE2,
                                                             "^" + re.escape(fern) + "$" if fern else PLANTS],
                 first=first, step=4.6)
        hang = r"^GreenTapestry\d$"
    c.lights_balanced(4)
    if hang and c.types(hang):
        c.hangings(hang, step=3.4, most=6)
    else:
        col = c.rng.choice(("Blue", "Red", "White", "Green"))
        c.hangings(rf"^{col}Tapestry\d$", step=3.4, most=6)


COMPOSERS = {"living_room": living_room, "dwelling": living_room, "kitchen": kitchen, "shop": shop, "tavern": tavern,
             "dining_hall": dining_hall, "mess_hall": dining_hall, "ogre_hall": ogre_hall, "gallery": gallery,
             "hall": hall, "throne_room": throne_room, "solar": solar, "study": study, "library": library,
             "infirmary": infirmary, "herbalist": herbalist, "great_hall": great_hall}


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
                if DEBUG: c.log.append(f"   dress {name} bare {lo:.1f}..{hi:.1f} run {r['lo']}..{r['hi']}")
                if hi - lo >= 6.0: c.row(r, c.wall_pat, 2 if hi - lo >= 9 else 1, lo=lo + 0.6, hi=hi - 0.6)


FRONT_PIECES = {"living_room": r"^Bench\d$|^CushionedBench\d$", "dwelling": r"^Bench\d$",
                "solar": r"^CushionedBench\d$|^Bench\d$", "study": r"^Bench\d$|^CushionedBench\d$", "library": r"^Bench\d$|^CushionedBench\d$",
                "infirmary": r"^Bench\d$", "herbalist": r"^TraderAppleCrate$", "kitchen": r"^WaterBarrel$|^Barrel2?$",
                "shop": r"^Barrel2?$|^Crate[12]$", "tavern": r"^Bench\d$|^LightBench\d$",
                "dining_hall": r"^Bench\d$|^LightBench\d$", "mess_hall": r"^Bench\d$", "ogre_hall": r"^Barrel2?$",
                "gallery": r"^Bench[1-4]$", "hall": VASE, "throne_room": VASE, "great_hall": VASE}


def front_dress(c):
    """A front wall left bare along most of its length takes a mirrored pair of the type's front piece (benches, urns,
    barrels), a quarter of the way in from each end (the SE and SW walls were chronically bare: Q1A-1)."""
    pat = FRONT_PIECES.get(c.f.kind)
    if not pat: return 0
    got = 0
    for name in FRONT:
        r = c.wall(name)
        if not r or r["hi"] - r["lo"] < 10: continue
        bare = sum(hi - lo for lo, hi in c.bare(r, reach=2.0))
        if bare >= 0.6 * (r["hi"] - r["lo"] - 1.2): got += wall_pair(c, name, pat, 0.25)
    return got


def finish(f, need):
    """The last pass of a civic room: the back walls dressed where still bare, the S corner given a group where still
    bare, statues face into the room, rugs audited, lights in matching corners up to the room's due (a light per 40
    tiles, at least two, never past kit/objects.py light_cap)."""
    c = getattr(f, "_civic", None) or Ctx(f)
    dress_walls(c)
    front_dress(c)
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


def why(f, t, u, v, blocking=True, touch=False, snug=False):
    """Debug: why try_put would refuse t at (u, v)."""
    hu, hv = f.half(t)
    if touch and f.g.fits(u, v, hu, hv, blocking, False, touch=True):
        if not f._kb_ok(t, u, v, hu, hv, blocking, "floor"): return "kb " + str(dict(f.kb_refused))
        if blocking and not f.g.reachable_ok((u, v, hu, hv, True, "floor")): return "reach"
        if f.coverage(f.footprint(t)) > f.cover_max: return "cover"
        return "touch-ok?"
    if not f.g.fits(u, v, hu, hv, blocking, False, wall_min=0.1 if snug else 0.25):
        pts = [(u + a * hu, v + b * hv) for a in (-1, 0, 1) for b in (-1, 0, 1)]
        if not all(f.g.inside(*p) for p in pts): return "outside"
        if min(f.g.wall_dist(*p) for p in pts) < (0.1 if snug else 0.25): return "wall"
        if not f.g.before_back_wall(u, v): return "wallcell"
        for du, dv in f.g.doors:
            if math.hypot(u - du, v - dv) < F.DOOR_CLEAR + max(hu, hv): return "door"
        for z in f.g.zones:
            if u + hu > z[0] and u - hu < z[1] and v + hv > z[2] and v - hv < z[3]: return f"zone{tuple(round(x,1) for x in z)}"
        for tt, rec in f._typed:
            if bool(rec[4]) == bool(blocking) and rec[5] != "wall" and abs(u - rec[0]) < hu + rec[2] + 0.15 and                     abs(v - rec[1]) < hv + rec[3] + 0.15:
                return f"overlap {tt}"
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
