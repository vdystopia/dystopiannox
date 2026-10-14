"""Sacred and dark rooms as symmetric set pieces: the chapel, the coven, the mana room and the crypt.

QA round 1 (2026-10-13, the user's notes on the chapel and crypt sets: review/reviews/QA-round1.md, the ledger
review/qa1/sacred.md, Q1C-n):
- "Generally, chapels should have a much more symmetric layout. The carpet that runs down the middle with benches and /
  or pillars and pews evenly and symmetrically placed on either side and an altar at the end, centered." "Chapels should
  always be aligned with the main door. The character should walk in and be on the main path facing the altar."
- "all rooms use the same altar - try different objects"; nox14: "needs more pillars, benches, and statues ... Have the
  priest stand closer to the altar."
- the square mana obelisk arrangements "are excellent, but they do not fit in with the identity of a chapel ... separate
  these rooms into their own category - mana rooms. define them by 1-4 arrangements of mana crystals evenly and
  symmetrically placed and a wide selection of other arcane objects"; "the carpet underneath them made even and
  symmetrical".
- "Create an additional separate chapel category for necromancy. call them Covens. Use coffins and sarcophagi and bones,
  as well as altars, pews, monuments, statues, cauldrons, etc. ... many Mana obelisks lining the walls. All of the rules
  regarding balance and centering of normal chapels should apply to covens as well."
- crypts: "The objects in these rooms need better organization, arrangement, and balance. Add more object diversity,
  like bones. Use the breakable coffin objects sometimes. Add a high chance for these rooms to contain mana obelisks."

So these rooms are not furnished piece by piece and audited for Westwood's irregularity (kit/grammar.py: even gaps,
rings and stepped rows are faults in a house room); each is laid out as one set piece about an axis:
- the chapel, the coven and the crypt about the line from the main door to the far wall (Axis): the altar (or the crypt's
  centrepiece) centred on the far wall in line with the door, a carpet runner centred on that line, and every other floor
  piece in a mirrored pair across it (pews in rows, columns lined up with the rows, statues, coffins, obelisks, lights);
- the mana room about its own centre: one to four rings of four mana obelisks, each round a centrepiece on its own carpet
  centred under it, the rings placed symmetrically, the walls dressed with arcane pieces in mirrored pairs.
Hangings and faced pieces (shelves, workstations) keep to the back walls the camera sees (TP3-a), mirrored about the
wall's own middle. The priest's spot is beside the altar (Furnisher.spots role "priest", kit/roomtypes.py STANDS).

The recipe sets `composer` (kit/identity.py ROOMS[kind]["composer"]: "nave", "coven", "mana", "crypt"); the furnisher
(kit/furnish.py Furnisher.furnish) hands the room over here first and keeps its own path when compose() returns False
(a room too small or too broken for the set piece). The checker holds the result (validate/checks.py check_sacred:
sacred.axis, sacred.symmetry, sacred.carpet, sacred.altar_kind, sacred.dead).
"""
import math, os, random, re, zlib
from collections import Counter

PAIR_TOL = 0.05            # a mirrored pair lands within this of exact (uv units)
BACK_SIDES = ("/|BR", "\\|BL")   # the NW and NE walls (kit/furnish.py BACK_SIDES)

# the chapel's altar: one of these, a map's chapels taking each in turn before any twice (QA round 1, Q1C-4: "all rooms
# use the same altar - try different objects"; round 2, Q2S-1, recurring: "Every single one of these chapels has the
# same square stone altar ... There are a few examples where there are statues in or a well in addition to the altar,
# but they still use the same altar"): the altar itself varies, not what stands beside it. Dun Mir's square stone altar
# between fire basins; a saint's tomb (a sarcophagus lying across the axis); a saint's great statue facing the door; the
# holy font (the orb pool); a fountain. Each stands against the far wall on the axis, alone.
CHAPEL_ALTARS = (("altar", 1.0), ("tomb", 1.0), ("saint", 1.0), ("font", 1.0), ("fountain", 1.0))
# the coven's: the lich god's statue over a sarcophagus, a bier between flaming skulls, a burning pyre of skulls
COVEN_ALTARS = (("lich", 3.0), ("bier", 2.5), ("pyre", 2.0))
# the share of a coven's side walls its mana obelisks line, from the altar's end (QA round 2, Q2S-4, RM-COVEN-03: "there
# are simply too many mana obelisks. It's okay to line most of the wall, but don't line the entire wall"; RM-COVEN-04:
# "There are also too many mana obelisks"): the door's end of the walls is left to the dead and the dressing
COVEN_OBELISK_RUN = 0.6
# a mana ring's centrepiece (the user: "Try some other centerpiece objects")
# QA round 2 (Q2S-3, the mana room set): "Way too many mana pillars, obelisks, crystals. Cut them in half. The mana carts
# look good, but the mana crystals look out of place in the middle of an interior floor. only use a few of them per room
# and concentrate them in corners"; RM-MANAROOM-01..05: "If this room just had the square mana obelisk arrangements with
# no free standing mana crystals, it would be good." So no crystal or crystal pillar stands as a ring's centrepiece or
# on the open floor: the holy font, an altar, an orrery, a generator, a fire basin; the crystals are the corners' clusters
MANA_CENTRES = (("OrbPoolWithOrb", 1.0), ("DunMirAltar1", 1.0), ("Orrery1", 1.0), ("VandegrafLarge", 1.0),
                ("DunMirFlameBasinLit", 1.0))
MANA_SECOND = ("OrbPoolWithOrb", "DunMirFlameBasinLit", "DunMirAltar1")   # the other rings' centre beside a showpiece
# the rings by the room's size (round 1: 1 under 100 tiles, 2 under 170, 3 under 230, else 4; round 2 halved them with
# the obelisks: Q2S-3): one ring under MANA_TWO_RINGS tiles, else two
MANA_TWO_RINGS = 230
# the saint's statue faces out from the back wall it stands on, toward the door (Horrendous, the warrior saint of the
# Kingdoms): HorrendousStatue1 faces SE, 2 faces SW (a probe map's render, QA round 2; RM-CHAPEL-04/05: "The statue
# behind the altar is facing the wrong way": the two had been swapped, each looking along its wall)
SAINT = {"/|BR": "HorrendousStatue1", "\\|BL": "HorrendousStatue2"}


def _spread(f, key, options, ok=lambda n: True, strict=False):
    """One of `options` [(name, weight)] for this room, by the deficit of each over the map's rooms drawn so far (as
    kit/archetypes.py draws archetypes), reproducible from the map's name and the room; a room furnished again (the
    originality check's retries) keeps its draw. strict: only the options used least so far (QA round 2, Q2S-1: "Every
    single one of these chapels has the same square stone altar": no option twice while another that fits is unused)."""
    memo = getattr(f.spec, "_sacred_spread", None)
    if memo is None:
        memo = dict(rooms={}, used={})
        try: setattr(f.spec, "_sacred_spread", memo)
        except AttributeError: pass
    k = (key, getattr(f.room, "id", None))
    opts = [(n, w) for n, w in options if ok(n)]
    if not opts: return None
    if k in memo["rooms"] and any(n == memo["rooms"][k] for n, _ in opts): return memo["rooms"][k]
    used = memo["used"].setdefault(key, Counter())
    if strict:
        least = min(used[n] for n, _ in opts)
        opts = [(n, w) for n, w in opts if used[n] == least]
    tot_w = sum(w for _, w in opts)
    n_used = sum(used[n] for n, _ in opts)
    ws = [max(0.05, (n_used + 1) * w / tot_w - used[n]) for n, w in opts]
    rng = random.Random(zlib.crc32(f"sacred:{key}:{f.spec.d.get('name')}:{k[1]}:{n_used}".encode()))
    pick = rng.choices([n for n, _ in opts], ws)[0]
    used[pick] += 1
    memo["rooms"][k] = pick
    return pick


def _respread(f, key, old, new):
    """The room's draw for `key` taken as `new` after `old` would not fit (the spread's counts kept true)."""
    memo = getattr(f.spec, "_sacred_spread", None)
    if not memo or old == new: return
    used = memo["used"].setdefault(key, Counter())
    if used[old] > 0: used[old] -= 1
    used[new] += 1
    memo["rooms"][(key, getattr(f.room, "id", None))] = new


# ---- the frame ------------------------------------------------------------------------------------------------------
class Axis:
    """A room's axis: depth d from the near wall (the main door's, or the room's near edge) toward the far wall, lateral
    s across it (s = 0 on the axis). line: the near wall's line ('/' walls run along v, so depth runs along u)."""

    def __init__(self, f, line, coord, sign, mid):
        self.f, self.g = f, f.g
        self.line, self.coord, self.sign, self.mid = line, coord, sign, mid
        same = [r for r in self.g.runs if r["line"] == line and (r["coord"] - coord) * sign > 2.0
                and r["lo"] - 0.5 <= mid <= r["hi"] + 0.5]
        self.far = min(same, key=lambda r: abs(r["coord"] - coord), default=None)
        self.near = next((r for r in self.g.runs if r["line"] == line and abs(r["coord"] - coord) < 0.6
                          and r["lo"] - 0.5 <= mid <= r["hi"] + 0.5), None)
        if self.near is None:
            # the axis runs through the doorway itself (the main door centred on it since QA round 2): the door's wall
            # is the run of that line either side of the gap. Without it the pews took the far (altar) wall's variant
            # and faced the door (checks qa2.facing, Westwood's Bench1/2/4/5 per wall side)
            self.near = min((r for r in self.g.runs if r["line"] == line and abs(r["coord"] - coord) < 0.6),
                            key=lambda r: min(abs(r["lo"] - mid), abs(r["hi"] - mid)), default=None)
        self.D = abs(self.far["coord"] - coord) if self.far else 0.0
        # the back side across the axis: a / axis looks along u, its +v side is the NE wall (a back wall); a \ axis
        # looks along v, its -u side is the NW wall
        self.back_s = 1 if line == "/" else -1
        self.far_back = bool(self.far) and self.far["side"] in BACK_SIDES

    def uv(self, d, s):
        c = self.coord + self.sign * d
        a = self.mid + s
        return (c, a) if self.line == "/" else (a, c)

    def ds(self, u, v):
        c, a = (u, v) if self.line == "/" else (v, u)
        return (c - self.coord) * self.sign, a - self.mid

    def halves(self, t):
        """(half along the depth, half across) of piece t."""
        hu, hv = self.f.half(t)
        return (hu, hv) if self.line == "/" else (hv, hu)

    def sides_at(self, d):
        """(room to the wall on the -s side, on the +s side) at depth d, uv units from the axis to the wall line."""
        c = self.coord + self.sign * d
        lo, hi = 99.0, 99.0
        for r in self.g.runs:
            if r["line"] == self.line or not (r["lo"] - 0.5 <= c <= r["hi"] + 0.5): continue
            off = r["coord"] - self.mid
            if off > 0.3: hi = min(hi, off)
            elif off < -0.3: lo = min(lo, -off)
        return lo, hi

    def half_width(self, d0=None, d1=None):
        """The narrower side's room from the axis to its wall over depths d0..d1 (the whole nave by default)."""
        d0 = 1.0 if d0 is None else d0
        d1 = self.D - 1.0 if d1 is None else d1
        best = 99.0
        d = d0
        while d <= d1 + 1e-6:
            best = min(best, *self.sides_at(d))
            d += 0.5
        return best

    def side_run(self, s_sign, d):
        """The wall run on the s_sign side at depth d."""
        c = self.coord + self.sign * d
        cands = [r for r in self.g.runs if r["line"] != self.line and r["lo"] - 0.5 <= c <= r["hi"] + 0.5
                 and (r["coord"] - self.mid) * s_sign > 0.3]
        return min(cands, key=lambda r: abs(r["coord"] - self.mid), default=None)


# QA round 2 (Q2T-1, review/qa2/ledger.md): "The room is not properly centered. The row of mana obelisks on the
# southeast wall is quite far from the wall, while the row on the northwest wall is close to it" (RM-COVEN-04); "The two
# rows of coffins are not equally spaced in the room" (RM-CRYPT-02); "Centering issues" (RM-CRYPT-04). The axis had been
# the main door's line, a unit off the room's middle in most of the round's rooms (a door's opening is one wall cell wide
# or two, and the building hung it at the wall point nearest the middle: building.py now picks the opening that
# centres). A composition is centred on the room's own middle; a door within ROOM_MID_REACH of it keeps its way in.
ROOM_MID_REACH = 2.0


def room_middle(ax):
    """The room's own middle across the axis (uv): the middle between its side walls most common down the nave, when it
    holds over 40% of the nave, else None."""
    mids = Counter()
    d = 1.5
    while d <= ax.D - 1.5 + 1e-6:
        lo, hi = ax.sides_at(d)
        if lo < 90 and hi < 90: mids[round(ax.mid + (hi - lo) / 2.0, 1)] += 1
        d += 0.5
    if not mids: return None
    m, n = mids.most_common(1)[0]
    return m if n >= 0.4 * sum(mids.values()) else None


def door_axis(f):
    """The axis from the room's main door (Furnisher.main_door) to the far wall across from it, on the room's own middle
    when the door opens within ROOM_MID_REACH of it (Q2T-1), or None."""
    op = f.main_door()
    if not op: return None
    ax = Axis(f, op["line"], op["coord"], op["sign"], op["along"])
    if not (ax.far and ax.D >= 8): return None
    m = room_middle(ax)
    if m is not None and 0.05 < abs(m - ax.mid) <= ROOM_MID_REACH:
        ax2 = Axis(f, op["line"], op["coord"], op["sign"], m)
        if ax2.far and ax2.D >= 8: return ax2
    return ax


def centre_axis(f):
    """The axis down the room's long dimension through its middle (the mana room's): from its near wall to its far."""
    runs = f.g.runs
    us = [r["coord"] for r in runs if r["line"] == "/"]; vs = [r["coord"] for r in runs if r["line"] == "\\"]
    if not us or not vs: return None
    cells = f.g.cells
    cu = [x + y + 1 for x, y in cells]; cv = [x - y for x, y in cells]
    u0, u1 = max(c for c in us if c <= min(cu)), min(c for c in us if c >= max(cu))
    v0, v1 = max(c for c in vs if c <= min(cv)), min(c for c in vs if c >= max(cv))
    if u1 - u0 >= v1 - v0: ax = Axis(f, "/", u0, 1, round((v0 + v1) / 2.0 * 2) / 2.0)
    else: ax = Axis(f, "\\", v0, 1, round((u0 + u1) / 2.0 * 2) / 2.0)
    return ax if ax.far else None


# ---- the composer ---------------------------------------------------------------------------------------------------
class SetPiece:
    """Places mirrored pairs about an Axis through the furnisher's own checks (fits, doors, reachability), as one set
    piece: the object knowledge base's caps and clearances, meant for pieces placed one by one, do not apply
    (Furnisher.set_piece)."""

    def __init__(self, f, ax):
        self.f, self.ax = f, ax
        self.log = Counter()

    def ok(self, t):
        return bool(t) and self.f.ok_type(t)

    def cover_ok(self, t):
        f = self.f
        return f.coverage(f.footprint(t)) <= f.cover_max

    def put(self, t, d, s, blocking=True, layer="floor", wall_ok=False, snug=False):
        if not self.ok(t): return None
        if blocking and layer == "floor" and not self.cover_ok(t): return None
        u, v = self.ax.uv(d, s)
        return self.f.try_put(t, u, v, blocking=blocking, wall_ok=wall_ok, layer=layer, snug=snug)

    def pair(self, t, d, s, t2=None, **kw):
        """t at (d, -s) and t2 (else t) at (d, +s): both or neither. Returns 2 or 0."""
        if abs(s) < 0.3: return 1 if self.put(t, d, 0.0, **kw) else 0
        o1 = self.put(t, d, -abs(s), **kw)
        if not o1: return 0
        o2 = self.put(t2 or t, d, abs(s), **kw)
        if not o2:
            self.f._remove(o1); return 0
        self.log[t] += 2
        return 2

    def light_pair(self, d, s, t=None):
        f = self.f
        t = t or f.light_type()
        f.placing_light = True
        try:
            got = self.pair(t, d, s)
        finally:
            f.placing_light = False
        if got:
            for sg in (-1, 1): f.ring_lights.append(self.ax.uv(d, sg * abs(s)))
        return got

    def bones(self, d, s, n=2, types=("Skull", "ArmBone", "LegBone")):
        """A little heap of bones at (d, +-s), the same heap mirrored on both sides."""
        rng = self.f.rng
        got = 0
        for _ in range(n):
            t = rng.choice(types)
            dd, ss = rng.uniform(-0.7, 0.7), rng.uniform(-0.6, 0.6)
            got += self.pair(t, d + dd, abs(s) + ss, blocking=False)
        return got


def _types(f, fam, pat=None):
    ts = {t: w for t, w in f.types_of(fam).items() if not pat or re.search(pat, t)}
    return ts


def _pick(f, d):
    from kit.furnish import _pick as P
    return P(f.rng, d)


def _across(ax, t):
    """True when piece t lies long across the axis."""
    hd, hs = ax.halves(t)
    return hs > hd + 0.3


def _along(ax, t):
    hd, hs = ax.halves(t)
    return hd > hs + 0.3


def _oriented(f, ax, pat, across=True):
    """The types matching pat that lie across (or along) the axis."""
    out = [t for t in sorted(f.things) if re.search(pat, t) and f.ok_type(t)]
    return [t for t in out if (_across(ax, t) if across else _along(ax, t))]


def _colour_light(f, u, v):
    """One steady warm colour light (as Furnisher.add_lights sets one) at (u, v)."""
    presets = [p for p in f.lighting["colorlight"]["presets"]
               if p["animation"] == "steady" and p["family"] in ("orange", "yellow", "white") and p["intensity_class"] == "full"]
    if not presets: return
    p = f.rng.choices(presets, [x["weighted_share"] for x in presets])[0]
    from kit.furnish import _px
    x, y = _px(u, v)
    f.objects.append(f.spec.obj_px("ColorLight", x, y, xfer=dict(p["xfer"])))


def _runner(f, ax, d0, d1, want=(3, 2)):
    """A carpet runner centred on the axis from depth d0 to d1, its edges on the squares' seams so it lies exactly as
    wide either side of the axis (squares are 2 uv units; as drawn their seams lie at odd u and even v: kit/furnish.py
    square_centre, QA round 2, Q2T-2): a runner of even squares when the axis lies on a seam, odd when it runs through
    their middles. Returns its half width or 0."""
    from kit.furnish import CARPET_FLOORS, seam_parity
    if not CARPET_FLOORS.search(f.room.floor or ""): return 0.0
    m = ax.mid
    if abs(m - round(m)) > 0.01: return 0.0
    on_seam = round(m) % 2 == seam_parity("v" if ax.line == "/" else "u")    # (a / axis runs across v)
    for squares in want:
        if (squares % 2 == 0) != on_seam: continue
        half = float(squares)                     # squares of 2 units: half width = squares
        for a, b in ((d0, d1), (d0 + 1.0, d1), (d0 + 2.0, d1), (d0 + 2.0, d1 - 1.0), (d0 + 3.0, d1 - 1.0)):
            if b - a < 4.0: continue
            (u0, v0), (u1, v1) = ax.uv(a, -half + 0.5), ax.uv(b, half - 0.5)
            mat = f.rng.choice(("RugRed", "RugRed", "RugBlueNorm"))
            if f.lay_carpet((min(u0, u1), max(u0, u1), min(v0, v1), max(v0, v1)), margin=0.0, material=mat,
                            true_uv=True, narrow=squares == 1):
                f.runner_boxes.append(f.carpet_boxes[-1])
                return half
    return 0.0


def _pews(sp, d_hi, d_lo, s0, rows_max, k_max, s_wall, types, most=None):
    """Rows of pews either side of the aisle: each half-row k pews from s0 outward, the rows from depth d_hi back toward
    d_lo every 2.4 units. Returns (rows laid, k, outer lateral edge of the pews)."""
    f, ax = sp.f, sp.ax
    if not types: return 0, 0, s0, None
    t0 = _pick(f, types)
    door_run = ax.near or ax.far
    t = f.side_variant(t0, door_run, "bench") if door_run else t0          # facing the altar (away from the door wall)
    if not t or not _across(ax, t): t = t0
    if not _across(ax, t):
        t = next((x for x in sorted(types) if _across(ax, x)), None)
        if not t: return 0, 0, s0, None
    hd, hs = ax.halves(t)
    pitch = 2 * hs + 0.2
    k = 0
    for kk in range(k_max, 0, -1):
        if s0 + kk * pitch - 0.2 <= s_wall: k = kk; break
    if not k: return 0, 0, s0, t
    if most:                                     # the room's most pews (TW-8: 46 pews wall to wall), in more rows of
        while k > 1 and most // (2 * k) < 4: k -= 1                   # fewer pews rather than two rows of many
        rows_max = min(rows_max, max(1, most // (2 * k)))
    rows = 0
    d = d_hi - hd
    sp.pew_rows = []
    # the rows spread down the nave when the room's pews run out before it does (at most 3.6 apart: still one congregation)
    step = 2.5 if rows_max < 2 else max(2.5, min(3.6, (d_hi - d_lo - 2 * hd) / (rows_max - 1)))
    while rows < rows_max and d - hd >= d_lo:
        placed = 0
        for i in range(k):                       # a row whose half-rows do not fit (a side door's way in) is left out
            if not sp.pair(t, d, s0 + hs + i * pitch): break
            placed += 1
        if placed:
            rows += 1
            sp.pew_rows.append(d)
        d -= step if placed else 1.0
    return rows, k, s0 + k * pitch - 0.2, t


# ---- the chapel -----------------------------------------------------------------------------------------------------
def chapel(f):
    """The nave: the altar centred on the far wall in line with the main door, a runner up the middle, pews in rows
    either side, columns lined up with the rows, statues and lights in pairs, tapestries on the back walls."""
    ax = door_axis(f)
    if not ax: return False
    sp = SetPiece(f, ax)
    D = ax.D
    W = ax.half_width(2.0, D - 2.0)
    if W < 4.0: return False
    saint = SAINT.get(ax.far["side"]) if ax.far_back else None          # (it faces out of a back wall only)
    tombs = _oriented(f, ax, r"^Crypt(1|3)$", across=True)
    fits = dict(altar=True, tomb=bool(tombs), saint=bool(saint and f.ok_type(saint)),
                font=W >= 7.0 and D >= 14.0 and f.ok_type("OrbPoolWithOrb"),
                fountain=W >= 7.0 and D >= 14.0 and f.ok_type("Fountain"))
    style = _spread(f, "chapel_altar", CHAPEL_ALTARS, ok=lambda n: fits[n], strict=True)
    statue_types = _types(f, "statue", r"^Statue2[a-h]$") or {"Statue2a": 1}
    st = _pick(f, statue_types)
    sr = max(f.half(st))
    stone = "DunMirAltar2" if f.rng.random() < 0.35 else "DunMirAltar1"
    tomb_alt = f.rng.choice(tombs) if tombs else None

    def altar_of(sty):
        """(the altar piece, its gap from the far wall) for an altar style."""
        return {"saint": (saint, 0.3), "tomb": (tomb_alt, 0.45), "font": ("OrbPoolWithOrb", 0.6),
                "fountain": ("Fountain", 0.6)}.get(sty, (stone, 0.45))
    # the altar itself against the far wall on the axis; the stone altar where the drawn one will not fit
    for sty in [style] + [x for x in ("tomb", "altar") if x != style and fits[x]]:
        alt, gap = altar_of(sty)
        ahd, ahs = ax.halves(alt)
        d_alt = D - ahd - gap
        if sp.put(alt, d_alt, 0.0, snug=sty in ("altar", "tomb")):
            _respread(f, "chapel_altar", style, sty)
            style = sty
            break
    else:
        return False
    f.altar_style = style
    wide = ahs
    front = d_alt - ahd
    # the priest beside the altar (nox14: "Have the priest stand closer to the altar"), statues flanking past him
    from kit.furnish import _px
    pu, pv = ax.uv(d_alt - 0.2, ax.back_s * (ahs + 0.95))
    f.spots.append(dict(role="priest", px=_px(pu, pv)))
    s_stat = wide + 2.0 + sr
    sp.pair(st, D - sr - 0.45, s_stat)
    # braziers before the statues, framing the sanctuary (the stone altar had stood beside the font, the fountain and the
    # saint as a second piece: the altar alone now, so the sanctuary keeps a kind more; QA round 2, Q2S-1)
    if style != "altar" and f.ok_type("HandBrazier"):
        f.placing_light = True
        try: sp.pair("HandBrazier", D - 2 * sr - 1.5, s_stat)
        finally: f.placing_light = False
    # fire basins framing the approach before the altar
    s_run = 2.0
    basin = "DunMirFlameBasinLit"
    # the runner from the door to the altar, centred on the axis
    rh = _runner(f, ax, 1.5, front - 0.8, want=(3, 2) if W >= 12 else (2, 3))
    s_run = rh if rh else 1.2
    f.aisle = dict(run=ax.far, mid=ax.mid, half=s_run, first=2.0, far=D, door=None)
    if front - 3.0 > 6.0 and sp.ok(basin):
        sp.pair(basin, front - 1.4, s_run + 1.1)
    # the pews either side of the runner, columns lined up at their outer ends
    cols = _types(f, "column") or {}
    ct = _pick(f, cols) if cols else None
    ch = max(f.half(ct)) if ct else 0.0
    tiles = len(f.room.tiles)
    cap = max(4, min(20, int(tiles / 10)))
    bench = _types(f, "bench")
    s0 = s_run + 0.6
    s_wall = W - 1.7 - (2 * ch + 0.7 if ct else 0.0)
    k_max = 3 if W >= 11 else 2
    colonnade = (f.archetype or {}).get("name") == "colonnade_chapel"    # (kit/archetypes.py: fewer pews, more columns)
    if colonnade: k_max = max(1, k_max - 1)
    rows_max = max(1, cap // 2)                  # (and at most `cap` pews: _pews)
    d_hi = front - 3.0
    d_lo = max(4.5, 0.28 * D)
    rows, k, s_out, pt = _pews(sp, d_hi, d_lo, s0, rows_max, k_max, s_wall, bench, most=cap)
    if not rows and ct:                      # a narrow nave: its pews before its columns, the columns against the walls
        rows, k, s_out, pt = _pews(sp, d_hi, d_lo, s0, rows_max, k_max, W - 1.5, bench, most=cap)
        if not rows:                         # the runner is the aisle: the pews may meet the side walls
            rows, k, s_out, pt = _pews(sp, d_hi, d_lo, s0, rows_max, 1, W - 0.45, bench, most=cap)
        if W - 0.35 - ch < s_out + 0.4 + ch: ct = None
        else: s_out = W - 0.35 - 2 * ch - 0.7
    # columns: a pair at the outer end of each row (every other row in a long nave), and a pair before the sanctuary
    col_s = s_out + 0.7 + ch
    if ct and rows:
        pd = ax.halves(pt)[0]
        step = 1 if rows <= 2 else 2
        # one even pitch down the whole nave, lined up with the rows and on past them to the door (RM-CHAPEL-08:
        # "Balance and line up the pillars and benches better")
        col_d = list(sp.pew_rows[::step])
        pitch_r = (sp.pew_rows[0] - sp.pew_rows[1]) if len(sp.pew_rows) > 1 else 2.5
        d = col_d[-1] - step * pitch_r
        while d >= 2.4:
            col_d.append(d); d -= step * pitch_r
        # a few pairs, never a wall of columns (SW-6 "tons of the same exact pillars"): the type's cap, a column per 16 tiles
        for d_c in col_d[:max(2, min(12, tiles // 16) // 2)]:
            sp.pair(ct, d_c, col_s)
    # the side aisles: statues against the side walls between the column pairs, tapestries on the back side wall
    pew_rows_d = list(getattr(sp, "pew_rows", []))
    if rows >= 2 and W - col_s - ch >= 2.4:
        for i in range(1, rows, 2):
            dm = (pew_rows_d[i - 1] + pew_rows_d[i]) / 2.0
            sp.pair(st, dm, ax.half_width(dm - 1, dm + 1) - sr - 0.5)
            # (four at most: the statue cap left to urns, victors and gargoyles, kinds more; QA round 2)
            if sum(1 for o in f.objects if o["type"].startswith("Statue2")) >= 4: break
    # the narthex by the door: founders' tombs in a big nave, else a pair of statues flanking the runner's foot
    d_n = (d_lo - 0.8 + 2.4) / 2.0
    tomb = None
    if tiles >= 110:                         # (never the saint's tomb an altar may be, Crypt1/3: Q2S-1)
        tombs = [t for t in _oriented(f, ax, r"^Crypt(5|6|7|8|9|10|11|12)$", across=False)]
        tomb = f.rng.choice(tombs) if tombs else None
        # (the drawn one first, then the others, the narrowest first, so the narthex keeps its founders where one fits)
        tombs = [tomb] + sorted((t for t in tombs if t != tomb), key=lambda t: (ax.halves(t)[1], t)) if tomb else []
        tomb = None
        for t in tombs:
            thd, ths = ax.halves(t)
            if d_lo - 2.4 >= 2 * thd + 1.0 and sp.pair(t, (2.6 + d_lo - 0.6) / 2.0, s_run + 1.2 + ths):
                tomb = t
                break
    if not tomb and d_lo >= 4.5:
        sp.pair(st, 3.2, s_run + 1.3 + sr)
    # lights in pairs: beside the altar's statues, by the door, mid-nave in a long one
    from kit import objects as OBJ
    lcap = OBJ.light_cap(tiles)
    n_l = 0
    if sp.light_pair(D - 0.9, s_stat + sr + 1.2): n_l += 2
    if n_l + 2 <= lcap and sp.light_pair(1.6, min(W - 1.2, s_run + 3.2)): n_l += 2
    if n_l + 2 <= lcap and rows >= 3:
        if sp.light_pair(pew_rows_d[rows // 2] - 1.25, W - 0.9): n_l += 2
    cu, cv = ax.uv(D / 2.0, 0.0)
    _colour_light(f, cu, cv)
    _hangings(f, ax, sp, s_stat)
    vase = f.rng.choice(("StatueVase1", "StatueVase2"))
    victory = f.rng.choice(("StatueVictory1", "StatueVictory3", "StatueVictory4"))
    # benches along the side walls, of another kind than the pews (a kind more: QA round 2, the altar's second piece gone)
    pew_stem = re.sub(r"\d+$", "", pt or "")
    wallbench = next((t for t in _oriented(f, ax, r"^(LightBench|CushionedBench)\d$", across=False)
                      if re.sub(r"\d+$", "", t) != pew_stem), None)
    # (the chapel dresses two kinds past its goal: the round 2 chapels' second altar-end piece is gone, Q2S-1, and a
    # room is never left emptier than the round before)
    dress(f, ax, sp, "chapel", [("basins", lambda sg: "DunMirFlameBasinLit", False), ("statues", lambda sg: st, True),
                                ("urns", lambda sg: vase + _facing(ax, sg), False), ("monuments", lambda sg: "Monument1", False),
                                ("gargoyles", lambda sg: "Gargoyle2", True),
                                ("victors", lambda sg: victory + _facing(ax, sg), True),
                                ("pedestals", lambda sg: "OrbPoolEnd1", False),
                                ("braziers", lambda sg: "Brazier", True),
                                ("wallbench", lambda sg: wallbench, False)], extra=2, front_along=True)
    return True


def _hangings(f, ax, sp, s_stat, max_n=6):
    """Tapestries of one colour (the recipe's theme) on the back walls: a pair either side of the altar on the far wall
    when it is a back wall, mirrored about the axis; on the back side wall at the column bays, evenly."""
    f.decor_theme()
    got = 0
    if ax.far_back:
        for s in (s_stat + 2.6, s_stat + 5.6):
            if s > ax.half_width(ax.D - 2, ax.D - 0.5) - 1.2: break
            ok = [f._hang(ax.far, ax.mid - s), f._hang(ax.far, ax.mid + s)]
            got += sum(ok)
            if got >= max_n - 2: break
    side = ax.side_run(ax.back_s, ax.D / 2.0)
    if side:
        n = 0
        d = ax.D - 4.0
        while d > 3.0 and got < max_n:
            c = ax.coord + ax.sign * d
            if side["lo"] + 1.2 <= c <= side["hi"] - 1.2 and f._hang(side, c):
                got += 1; n += 1
            d -= 5.0
    return got


# ---- the coven ------------------------------------------------------------------------------------------------------
def coven(f):
    """The dead worshipped and necromancy practised: the dark altar centred on the far wall in line with the door, a
    cauldron before it, pews either side of the runner, coffins and sarcophagi in mirrored pairs, bones heaped by them,
    monuments by the door, mana obelisks lining both side walls (RM-CHAPEL-10, its basis)."""
    ax = door_axis(f)
    if not ax: return False
    sp = SetPiece(f, ax)
    D = ax.D
    W = ax.half_width(2.0, D - 2.0)
    if W < 4.0: return False
    lich = {"/|BR": "LOTDLichGodStatue1", "\\|BL": "LOTDLichGodStatue2"}.get(ax.far["side"])
    style = _spread(f, "coven_altar", COVEN_ALTARS, ok=lambda n: n != "lich" or bool(lich and f.ok_type(lich)))
    obel = "LOTDManaObelisk" if f.ok_type("LOTDManaObelisk") else "Obelisk"
    oh = max(f.half(obel))
    sarc = _oriented(f, ax, r"^Crypt(1|3)$", across=True) or _oriented(f, ax, r"^Crypt(5|6|7|8|9|10|11|12)$", across=True)
    if style == "lich":
        lhd, lhs = ax.halves(lich)
        if not sp.put(lich, D - lhd - 0.3, 0.0, snug=True): style = "bier"
        else:
            back = D - 2 * lhd - 0.3
            alt = sarc[0] if sarc else None
            if alt:
                ahd, ahs = ax.halves(alt)
                d_alt = back - 0.7 - ahd
                if not sp.put(alt, d_alt, 0.0): alt = None
            if not alt:
                d_alt, ahd, ahs = back - 0.1, 0.0, lhs
            front, wide = d_alt - ahd, max(ahs, lhs)
    if style == "bier":
        alt = sarc[0] if sarc else None
        if not alt: return False
        ahd, ahs = ax.halves(alt)
        d_alt = D - ahd - 1.2
        if not sp.put(alt, d_alt, 0.0):
            return False
        front, wide = d_alt - ahd, ahs
        sp.pair("LOTDFlamingSkullsStatic", d_alt, ahs + 1.0 + 0.77)
    if style == "pyre":
        alt = "LOTDFlamingSkullsAnimated"
        ahd, ahs = ax.halves(alt)
        d_alt = D - ahd - 1.0
        if not sp.put(alt, d_alt, 0.0): return False
        front, wide = d_alt - ahd, ahs
        bal = _oriented(f, ax, r"^LOTDJudgementBalance[12]$", across=False)
        if bal: sp.pair(bal[0], d_alt, ahs + 1.2 + ax.halves(bal[0])[1])
    from kit.furnish import _px
    pu, pv = ax.uv(front - 0.6, ax.back_s * (wide + 0.9))
    f.spots.append(dict(role="priest", px=_px(pu, pv)))
    # obelisks in the far corners and lining both side walls, in pairs at even steps
    s_wall = lambda d: min(ax.sides_at(d)) - oh - 0.35
    sp.pair(obel, D - oh - 0.5, s_wall(D - oh - 0.5))
    # the cauldron on the axis before the altar (one cauldron to a room: HB-1)
    caul = "CauldronAnimated" if f.ok_type("CauldronAnimated") else "Cauldron"
    d_c = front - 2.2 - max(f.half(caul))
    has_c = d_c > 8 and sp.put(caul, d_c, 0.0)
    rh = _runner(f, ax, 1.5, (d_c - max(f.half(caul)) - 0.8) if has_c else front - 0.8, want=(2, 1, 3))
    s_run = rh if rh else 1.2
    f.aisle = dict(run=ax.far, mid=ax.mid, half=s_run, first=2.0, far=D, door=None)
    d = D - 3.4
    n_ob = 0
    while d > max(2.6, (1.0 - COVEN_OBELISK_RUN) * D):
        if sp.pair(obel, d, s_wall(d)): n_ob += 2
        d -= 3.3
    # pews in a few rows, LOTD columns at their ends
    bench = _types(f, "bench")
    d_hi = (d_c - 1.6) if has_c else front - 2.6
    d_lo = max(5.0, 0.42 * D)
    s0 = s_run + 0.6
    col = "LOTDColumn1" if f.ok_type("LOTDColumn1") else None
    ch = max(f.half(col)) if col else 0.0
    s_lim = W - oh * 2 - 0.9 - (2 * ch + 0.6 if col else 0.0)
    rows, k, s_out, _pt = _pews(sp, d_hi, d_lo, s0, 3, 2, s_lim, bench)
    if not rows and col:                     # a narrow coven: its pews before its columns
        col = None
        rows, k, s_out, _pt = _pews(sp, d_hi, d_lo, s0, 3, 2, W - oh * 2 - 0.9, bench)
    if col and rows:                         # the first and last rows' ends, a pair at each
        for d_r in sorted({sp.pew_rows[0], sp.pew_rows[-1]}):
            sp.pair(col, d_r, s_out + 0.6 + ch)
    # the dead: coffins lying along the aisle in pairs, bones heaped by them; sarcophagi by the door in a big coven
    coffins = _oriented(f, ax, r"^Coffin[1-4]$", across=False)
    d_dead = d_lo - 1.4
    placed_c = 0
    if coffins:
        cf = f.rng.choice(coffins)
        chd, chs = ax.halves(cf)
        dd = d_dead - chd
        while dd - chd >= 3.0 and placed_c < 4:
            if sp.pair(cf, dd, s_run + 0.9 + chs):
                placed_c += 2
                sp.bones(dd, s_run + 0.9 + 2 * chs + 0.8, n=1)
            dd -= 2 * chd + 1.4
    if sarc and len(f.room.tiles) >= 150 and placed_c < 4:
        st_ = _oriented(f, ax, r"^Crypt(1|3|5|6|7|8|9|10|11|12)$", across=False)
        if st_:
            t = st_[0]
            thd, ths = ax.halves(t)
            sp.pair(t, max(thd + 2.6, d_dead - thd), s_run + 1.0 + ths)
    # monuments flanking the runner's foot, balances or arks by the altar
    mon = "Monument1"
    for s_m in (s_run + 1.2, 3.2, 4.2):          # (clear of a centred double door's way in: QA round 2)
        if s_m >= s_run + 1.2 and sp.pair(mon, 2.8, s_m): break
    arks = _oriented(f, ax, r"^LOTDArk[12]$", across=False) or _oriented(f, ax, r"^LOTDJudgementBalance[12]$", across=False)
    if arks and style != "pyre":
        a = arks[0]
        sp.pair(a, front - 0.4 - ax.halves(a)[0], wide + 1.6 + ax.halves(a)[1])
    # bones before the altar and by the obelisks
    sp.bones(front - 1.4, s_run + 0.6, n=2)
    sp.bones(D / 2.0, W - 2.6, n=2)
    # lights: candle groups by the altar, candelabras in pairs
    from kit import objects as OBJ
    lcap = OBJ.light_cap(len(f.room.tiles))
    lt = "LOTDCandleabra1" if f.ok_type("LOTDCandleabra1") else f.light_type()
    n_l = 0
    if sp.light_pair(front - 0.6, wide + 2.6, t=lt): n_l += 2
    if n_l + 2 <= lcap and sp.light_pair(1.6, min(W - 1.2, s_run + 3.0), t=lt): n_l += 2
    if f.ok_type("LOTDCandleGroupSmall1"):
        f.placing_light = True
        try: sp.pair("LOTDCandleGroupSmall1", D - 0.9, wide + 1.0)
        finally: f.placing_light = False
    cu, cv = ax.uv(D / 2.0, 0.0)
    _colour_light(f, cu, cv)
    _hangings(f, ax, sp, wide + 1.6, max_n=6)
    # (no stores in a coven; no more obelisks than its walls' run: Q2S-4)
    # (two kinds past the goal: the obelisks' freed stretch of the walls filled with other funerary kinds, Q2S-4)
    dress(f, ax, sp, "coven", [p for p in crypt_pieces(f, ax, True, obelisks=False) if p[0] != "crates"], extra=2)
    return True


# ---- the mana room --------------------------------------------------------------------------------------------------
def _ring_layouts(L, S, foot):
    """[(n, [(d, s)...])] ring centres (depth from the near wall, lateral from the axis) that fit a room L long and S
    wide (uv, wall to wall), most rings first."""
    out = []
    m = foot / 2.0 + 2.6                 # a ring's half footprint and a walk between it and the walls' pieces
    if L >= 2 * m and S >= 2 * m: out.append((1, [(L / 2.0, 0.0)]))
    q = L / 4.0
    if L / 2.0 >= foot + 1.6 and q >= m and S >= 2 * m: out.append((2, [(L / 2.0 - q, 0.0), (L / 2.0 + q, 0.0)]))
    t = L / 3.0
    if t >= foot + 1.6 and L / 2.0 - t >= m and S >= 2 * m:
        out.append((3, [(L / 2.0 - t, 0.0), (L / 2.0, 0.0), (L / 2.0 + t, 0.0)]))
    if L / 2.0 >= foot + 1.6 and S / 2.0 >= foot + 1.6 and q >= m and S / 4.0 >= m - 1.0:
        w = S / 4.0
        out.append((4, [(L / 2.0 - q, -w), (L / 2.0 - q, w), (L / 2.0 + q, -w), (L / 2.0 + q, w)]))
    return sorted(out, key=lambda x: -x[0])


def _ring(f, ax, sp, d, s, centre, ob, carpet_mat):
    """A centrepiece at (d, s) ringed by four obelisks at the room's screen axes (the shrine's ring, the user's "square
    mana obelisk arrangements"), on a carpet centred under it: its edges on the squares' seams, as wide on every side.
    All or nothing. Returns True when laid."""
    u, v = ax.uv(d, s)
    u, v = round(u), round(v)                          # the ring's middle on whole units, so a carpet centres under it
    ch = max(f.half(centre)) if centre else 0.0
    oh = max(f.half(ob))
    r = max(2.0, ch + oh + 1.0)
    r = float(math.ceil(r))                            # obelisks on whole units, mirrored exactly
    o = f.try_put(centre, u, v) if centre else {"type": None}
    if not o: return False
    got = []
    f._pairing = True
    try:
        for du, dv in ((r, r), (-r, -r), (r, -r), (-r, r)):
            x = f.try_put(ob, u + du, v + dv)
            if not x: break
            got.append(x)
    finally:
        f._pairing = False
    if len(got) < 4:
        for x in got + ([o] if centre else []): f._remove(x)
        return False
    # the carpet: squares are 2 units, their seams (as drawn) at odd u and even v (kit/furnish.py square_centre; QA round
    # 2, Q2T-2); centred under the ring when its edges lie as far either side of the middle, on seams
    from kit.furnish import seam_parity
    m = r + oh + 0.3                                   # (the obelisks' outer edges and a step: QA round 2, the dressing
    #                                                    keeps off the carpet, so it is no wider than the ring needs)
    box = []
    for c, axis in ((u, "u"), (v, "v")):
        n = int(math.ceil(m))                          # half width in units, whole
        if (c + n) % 2 != seam_parity(axis): n += 1    # its edges c +- n on seams
        box.append((c - n + 0.5, c + n - 0.5))
    laid = f.lay_carpet((box[0][0], box[0][1], box[1][0], box[1][1]), margin=0.0, material=carpet_mat, true_uv=True)
    from kit.furnish import CARPET_FLOORS
    if not laid and CARPET_FLOORS.search(f.room.floor or ""):
        # every ring on its carpet or none (a ring without one beside a ring with one is lopsided: RM-CHAPEL-02)
        for x in got + ([o] if centre else []): f._remove(x)
        return False
    f.anchors.append((u, v))
    f.g.zones.append((u - r - oh - 0.2, u + r + oh + 0.2, v - r - oh - 0.2, v + r + oh + 0.2))
    return True


def mana_room(f):
    """One to four rings of mana obelisks round centrepieces, evenly and symmetrically placed, each on its own carpet
    centred under it; arcane pieces in mirrored pairs round the walls: bookcases and workstations on the back walls,
    crystal clusters in the corners, generators and glowing jars on the front, candelabras, star charts."""
    ax = centre_axis(f)
    if not ax: return False
    sp = SetPiece(f, ax)
    L = ax.D
    S = 2 * ax.half_width(1.0, L - 1.0)
    if L < 9 or S < 9: return False
    ob = "LOTDManaObelisk" if f.style == "lotd" and f.ok_type("LOTDManaObelisk") else \
        ("ObeliskPrimitive" if f.rng.random() < 0.2 and f.ok_type("ObeliskPrimitive") else "Obelisk")
    from kit.furnish import SHOWPIECES
    tiles = len(f.room.tiles)
    most = 1 if tiles < MANA_TWO_RINGS else 2
    cen = _spread(f, "mana_centre", MANA_CENTRES, ok=lambda n: f.ok_type(n), strict=True)
    if not cen: cen = "DunMirAltar1"
    from kit.furnish import PALETTES
    mats = f.rng.choice(PALETTES["carpet"])
    mat = mats[0]
    rings = 0
    snap = _snapshot(f)
    show = bool(SHOWPIECES.match(cen)) or cen.startswith("DunMirAltar")     # (an altar stands once too: pieces.showpiece)
    alt = next((c for c in MANA_SECOND if c != cen and f.ok_type(c)), "DunMirFlameBasinLit")

    def foot(c):
        return 2 * (max(2.0, math.ceil(max(f.half(c)) + max(f.half(ob)) + 1.0)) + max(f.half(ob)) + 0.5)
    # the most rings the room holds (its size: MANA_TWO_RINGS), each round the room's centrepiece; a showpiece (an orrery,
    # a generator: kit/furnish.py SHOWPIECES) stands once, in the only ring, the other round the second centrepiece
    plans = []
    for n, pos in _ring_layouts(L, S, max(foot(cen), foot(alt))):
        if n > most: continue
        cs = [cen if (not show or n == 1 or (n == 3 and k == 1)) else alt for k in range(n)]
        plans.append((n, pos, cs))
    for n, pos in _ring_layouts(L, S, foot(alt)):
        if n <= most: plans.append((n, pos, [alt] * n))
    for n, pos in _ring_layouts(L, S, foot("DunMirFlameBasinLit")):
        if n <= most: plans.append((n, pos, ["DunMirFlameBasinLit"] * n))
    plans.sort(key=lambda p: -p[0])              # the most rings the room holds first (06: "way too big and empty")
    for n, pos, cs in plans:
        laid = 0
        for (d, s), c in zip(pos, cs):
            if not _ring(f, ax, sp, d, s, c, ob, mat): break
            laid += 1
        if laid == n:
            rings = n
            f.ring_pos = list(pos)
            break
        _reset(f, snap)                              # a partial layout is taken up whole
    if not rings: return False
    f.ring_centres = rings
    # the walls: arcane pieces mirrored about the axis
    _mana_walls(f, ax, sp, rings)
    return True


def _mana_walls(f, ax, sp, rings):
    from kit import objects as OBJ
    from kit.furnish import _px
    L = ax.D
    W = ax.half_width(1.0, L - 1.0)
    # the corners: crystal clusters, four of a kind
    # (each placement takes its own kind of crystal, so no one kind repeats past the room score's most: the corners mana
    # crystal clusters, the rings' flanks blue stalagmites, the dressing mine crystals and crystal pillars)
    cl = f.rng.choice([t for t in ("MineManaCrystal1", "MineManaCrystal2", "MineManaCrystal5", "MineManaCrystal6",
                                   "MineManaCrystal9") if f.ok_type(t)] or ["CrystalColumn"])
    ch = max(f.half(cl))
    # (mana crystals already round the rings, as their centrepieces or the second centrepieces, leave the corners by the
    # door bare of them: the room score counts every MineManaCrystal as one kind, at most 4, or a piece per 30 of its
    # floor tiles, fewer than the kit's; the qa1d mana rooms 08, 17, 19 and 22 held 5-6)
    # (QA round 2, Q2S-3: "only use a few of them per room and concentrate them in corners": the far corners' pair, the
    # near corners' too in a room of 200 tiles or more; no other crystal stands in a mana room)
    ends = (L - ch - 1.0,) if len(f.room.tiles) < 200 else (ch + 1.0, L - ch - 1.0)
    for d in ends:
        sp.pair(cl, d, min(ax.sides_at(d)) - ch - 1.0)
    # the back walls: a centrepiece (workstation, potion shelves, a chest) mirrored about its wall's middle, bookcases
    # either side of it
    backs = [r for r in f.g.runs if r["side"] in BACK_SIDES and r["hi"] - r["lo"] >= 6]
    for r in backs:
        # a wall along the axis is mirrored about the room's middle across it, an end wall about the axis
        mid = ax.coord + ax.sign * L / 2.0 if r["line"] != ax.line else ax.mid
        choice = f.rng.choice(("workstation", "potions", "chest"))
        if choice == "workstation":
            ws = [t for t in sorted(f.things) if re.match(r"^WizardWorkstation[123][a-d]?$", t) and f.ok_type(t)]
            t = f.side_variant(f.rng.choice(ws), r, "lab") if ws else None
        elif choice == "potions":
            t = f.side_variant("PotionShelves1", r, "shelves")
        else:
            t = f.side_variant("DunMirChest1" if f.ok_type("DunMirChest1") else "Chest1", r, "storage")
        a0 = 2.6                                 # where the bookcases start either side of the wall's middle
        if t:
            hu, hv = f.half(t)
            hp, hl = (hu, hv) if r["line"] == "/" else (hv, hu)
            if f.try_put(t, *f._uv_on(r, hp + 0.22, mid), snug=True) and choice != "chest":
                a0 = hl + 0.05                   # end to end with the shelves or the workstation (no bare gap: TP3-b)
        # bookcases end to end either side, mirrored about the wall's middle
        bc = f.side_variant("Bookcase1", r, "shelves")
        if bc:
            hu, hv = f.half(bc)
            hp, ha = (hu, hv) if r["line"] == "/" else (hv, hu)
            n_bc = max(2, min(4, int((r["hi"] - r["lo"]) * 0.18 / (2 * ha))))
            for k in range(n_bc):
                a = a0 + ha + k * (2 * ha + 0.05)
                o1 = f.try_put(bc, *f._uv_on(r, hp + 0.18, mid - a), snug=True, touch=True)
                o2 = o1 and f.try_put(bc, *f._uv_on(r, hp + 0.18, mid + a), snug=True, touch=True)
                if o1 and not o2: f._remove(o1)
                if not (o1 and o2): break
        # past the bookcases, a workstation or a pair of potion shelves at each quarter of a long wall, mirrored
        if r["hi"] - r["lo"] >= 20:
            a = (r["hi"] - r["lo"]) / 4.0 + 1.0
            ws = [t for t in sorted(f.things) if re.match(r"^WizardWorkstation[12][a-d]?$", t) and f.ok_type(t)]
            t2 = f.side_variant(f.rng.choice(ws), r, "lab") if ws and f.rng.random() < 0.6 else                 f.side_variant("PotionShelves1", r, "shelves")
            if t2:
                hu, hv = f.half(t2)
                hp = hu if r["line"] == "/" else hv
                o1 = f.try_put(t2, *f._uv_on(r, hp + 0.22, mid - a), snug=True)
                o2 = o1 and f.try_put(t2, *f._uv_on(r, hp + 0.22, mid + a), snug=True)
                if o1 and not o2: f._remove(o1)
        # star charts above the bare stretches, mirrored
        f.decor_theme()
        charts = [t for t in sorted(f.things) if re.match(r"^(StarChart\d|Zodiac\d)[a-d]$", t)]
        if charts:
            stem = f.rng.choice(sorted({re.sub(r"[a-d]$", "", t) for t in charts}))
            hc = f.side_variant(stem + "a", r, "wall_decor")
            if hc:
                for a in (7.4, 10.4):
                    if mid + a > r["hi"] - 1.5: break
                    d0 = f.perp_for(hc, None)
                    o1 = f.try_put(hc, *f._uv_on(r, d0, mid - a), blocking=False, wall_ok=True, layer="wall")
                    o2 = o1 and f.try_put(hc, *f._uv_on(r, d0, mid + a), blocking=False, wall_ok=True, layer="wall")
                    if o1 and not o2: f._remove(o1)
    # the front walls and the open floor: generators flanking the middle, glowing jars, an orrery between two rings
    gen = "VandegrafSmall" if f.ok_type("VandegrafSmall") else None
    if gen:
        sp.pair(gen, L / 2.0, W - 1.6)
    if rings == 2:                               # the open floor between two rings: an orrery (never a crystal: Q2S-3)
        if f.ok_type("Orrery2"): f.try_put("Orrery2", *ax.uv(L / 2.0, 0.0))
    # each ring flanked across the room by a pair of mana carts, its carpet's width out (round 2: "The mana carts look
    # good"; the blue stalagmites that stood there were the "free standing mana crystals" of Q2S-3)
    cart = "MineManaCart1" if ax.line == "/" else "MineManaCart2"
    for d, s in getattr(f, "ring_pos", []):
        if s < -0.1 or not f.ok_type(cart): continue
        ch_ = ax.halves(cart)[1]
        edge = max([0.0] + [(b[3] - b[2]) / 2.0 if ax.line == "/" else (b[1] - b[0]) / 2.0 for b in f.carpet_boxes])
        for gap in (edge + ch_ + 1.0, edge + ch_ + 1.6, 5.4):       # (off the ring's carpet: Q2T-2)
            if s + gap > W - 1.2: continue
            if sp.pair(cart, d, s + gap): break
    jar = "FairyJar" if f.ok_type("FairyJar") else None
    if jar:
        for d in (L / 4.0, 3 * L / 4.0):
            sp.pair(jar, d, W - 1.1)
    # lights in pairs: by the near and far walls
    lcap = OBJ.light_cap(len(f.room.tiles))
    n_l = 0
    for d in (1.2, L - 1.2):
        if n_l + 2 > lcap: break
        if sp.light_pair(d, W / 2.0): n_l += 2
    cu, cv = ax.uv(L / 2.0, 0.0)
    _colour_light(f, cu, cv)
    # the wall stretches between the doors dressed in pairs, mirrored across the axis or else along it
    # (two kinds past the goal: the floor the halved obelisks and crystals left filled with other arcane kinds, Q2S-3)
    dress(f, ax, sp, "mana_room", mana_pieces(f, ax), both_ways=True, extra=2)


# ---- the crypt ------------------------------------------------------------------------------------------------------
def crypt(f):
    """Where the dead lie, in order: a centrepiece on the far wall in line with the door (a crypt chest, a great tomb or
    a monument between mana obelisks), rows of sarcophagi or breakable coffins either side of a middle aisle, mirrored;
    statues of the dead and tombstones in pairs along the walls, bones heaped by the tombs, candelabras in pairs."""
    ax = door_axis(f)
    if not ax: return False
    sp = SetPiece(f, ax)
    D = ax.D
    W = ax.half_width(1.5, D - 1.5)
    if W < 3.0 or D < 7: return False
    lotd = f.style == "lotd"
    rng = f.rng
    obel = "LOTDManaObelisk" if lotd and f.ok_type("LOTDManaObelisk") else "Obelisk"
    has_ob = rng.random() < 0.8 and f.ok_type(obel)
    oh = max(f.half(obel))
    # the centrepiece on a back wall the camera sees (QA round 1, third pass: crypt 05's stood against its front walls):
    # the far wall in line with the door when it is a back wall, else the middle of the back side wall
    from kit.furnish import WALL_SIDE_TYPE
    centre = _spread(f, "crypt_centre", (("chest", 2.0), ("tomb", 2.0), ("monument", 1.5)))
    wide = 0.0
    on_far = ax.far_back
    side_run = None if on_far else ax.side_run(ax.back_s, D / 2.0)
    if not on_far and side_run is None: on_far = True
    run = ax.far if on_far else side_run
    dc = D / 2.0

    def put_centre(t, out):
        """t against the centrepiece's wall `out` units off it (from its back), on the axis or at the side wall's middle."""
        hd, hs = ax.halves(t)
        if on_far:
            return hs if sp.put(t, D - hd - out, 0.0, snug=out < 0.4) else 0.0
        w_ = ax.sides_at(dc)[0 if ax.back_s < 0 else 1]
        return hd if sp.put(t, dc, ax.back_s * (w_ - hs - out), snug=out < 0.4) else 0.0
    if centre == "chest":
        t = WALL_SIDE_TYPE["CryptChest"].get(run["side"])
        if t and f.ok_type(t): wide = put_centre(t, 0.25)
    if centre == "tomb" or (centre == "chest" and not wide):
        # a great sarcophagus lying on the axis, its head to the wall and its foot toward the door (QA round 2, Q2S-5:
        # "The coffin in between the mana obelisks is facing the wrong way" (RM-CRYPT-02); "The steel coffin is not in
        # the right orientation" (RM-CRYPT-05)): Crypt2 and Crypt4 are drawn square to the screen, at 45 degrees to
        # every wall, so never; Crypt1 lies along v, Crypt3 along u
        al = _oriented(f, ax, r"^Crypt(1|3)$", across=not on_far)
        t = al[0] if al else None
        if t: wide = put_centre(t, 0.6)
    if not wide: wide = 0.5 if put_centre("Monument1", 0.6) else 0.0
    s_flank = wide + 1.2 + oh
    flank = obel if (has_ob or lotd) else _pick(f, _types(f, "statue", r"^Statue2[a-h]$") or {"Statue2a": 1})
    if f.ok_type(flank):
        if on_far: sp.pair(flank, D - oh - 0.5, s_flank)
        else:                                    # either side of it along the back side wall
            w_ = ax.sides_at(dc)[0 if ax.back_s < 0 else 1]
            o1 = sp.put(flank, dc - s_flank, ax.back_s * (w_ - oh - 0.45))
            o2 = o1 and sp.put(flank, dc + s_flank, ax.back_s * (w_ - oh - 0.45))
            if o1 and not o2: f._remove(o1)
    # the rows of the dead either side of the aisle
    kind = rng.random()
    sarcs = _oriented(f, ax, r"^Crypt(1|3)$", across=True) + _oriented(f, ax, r"^Crypt(5|6|7|8|9|10|11|12)$", across=True)
    coffins = _oriented(f, ax, r"^Coffin[1-4]$", across=True)
    lotd_stones = [t for t in ("LOTDTombstone2", "LOTDTombstone3", "LOTDTombstone4", "LOTDTombstoneSkulls1",
                               "LOTDTombstoneScroll1") if f.ok_type(t)]
    if False: rows_of = ["stones"]           # (RM-CRYPT-10 read its LOTD stones as no graves: coffins or sarcophagi)
    # a long narrow crypt lays two long lines of coffins, three or more to a line (QA round 1, third pass: crypt 02's four
    # sarcophagi took its cover to the type's most, 0.25, with the floor still bare)
    elif coffins and D >= 3.5 * W: rows_of = ["coffins"]
    elif kind < 0.4 and coffins: rows_of = ["coffins"]
    elif kind < 0.65 and coffins and sarcs: rows_of = ["sarcs", "coffins"]       # the old dead nearest the far wall
    else: rows_of = ["sarcs"] if sarcs else (["coffins"] if coffins else [])
    aisle = 1.5 if W < 6 else 1.8
    d = (D - 3.4 - (1.0 if has_ob else 0.4)) if on_far else D - 1.6   # a walk round the far end before its centrepiece
    rows = 0
    t_sarc = rng.choice(sarcs) if sarcs else None
    t_coff = rng.choice(coffins) if coffins else None
    t_stone = rng.choice(lotd_stones) if lotd_stones else None
    heads = []
    if os.environ.get("NOX_SACRED_DEBUG"): print("  crypt rows", f.room.id, rows_of, t_sarc, t_coff, round(W, 1), round(D, 1), round(d, 1))
    heads = []

    def along_of(t):
        """t's sibling lying along the aisle (the narrowest), or None."""
        stem = re.sub(r"\d+$", "", t)
        al = [x for x in _oriented(f, ax, "^" + stem + r"\d+$", across=False)
              if not stem.startswith("Crypt") or x in ("Crypt1", "Crypt3") or t not in ("Crypt1", "Crypt3")]
        return min(al, key=lambda x: ax.halves(x)[1]) if al else None

    def row(t, d, a_row, k_most=4, edge=0.75):
        """A mirrored row of t at depth d (its far edge there), from a_row out: (pieces, depth, half depth, outer s)."""
        hd, hs = ax.halves(t)
        dd = d - hd
        if dd - hd < 1.6: return 0, dd, hd, 0.0          # (the near door's own clearance keeps its way in)
        pitch = 2 * hs + 0.5
        k = max(1, min(k_most, int((W - 0.9 - a_row + 0.5) / pitch)))
        if k >= 3: pitch += 0.4                  # (a walk between the tombs of a long row)
        ok, s_out = 0, a_row
        for i in range(k):
            s_ = a_row + hs + i * pitch
            if s_ + hs > W - edge or f._fam_n["tomb"] + 2 > tomb_cap: break
            got = sp.pair(t, dd, s_)
            if not got: break
            ok += got; s_out = s_ + hs
        return ok, dd, hd, s_out

    # the rows down the whole floor, from the far end to the door: across the aisle where they fit, else along it a pace
    # out, else against the side walls; a depth where none fits (a side door's way) is stepped over, not the end of the
    # rows (RM-CRYPT-10: its two rows lay at one end of the floor)
    tomb_all = f.repeat_cap("tomb") or 99         # (the type's most tombs: a tomb per 6 tiles, 16 at most; gravestones
    tomb_cap = tomb_all - 4 if tomb_all >= 10 else tomb_all     # count with them, four kept for the graves)
    row_mode = None                              # (a long crypt's lines along the aisle: one placement for all)
    while d > 1.8 and rows < 14 and f._fam_n["tomb"] + 2 <= tomb_cap:
        what = rows_of[min(len(rows_of) - 1, rows // 2)] if rows_of else None
        t = {"sarcs": t_sarc, "coffins": t_coff, "stones": t_stone}.get(what)
        if not t: break
        hd0, hs0 = ax.halves(t)
        tal = along_of(t) if hs0 > hd0 else None
        tries = []
        if aisle + 2 * hs0 <= W - 0.9: tries.append((t, max(0.9, min(aisle, W - 0.8 - 2 * hs0)), 4, 0.75))
        if tal: tries.append((tal, max(0.9, min(aisle, W - 0.8 - 2 * ax.halves(tal)[1])), 2, 0.75))
        if tal: tries.append((tal, W - 2 * ax.halves(tal)[1] - 0.35, 1, 0.3))
        done = False
        # (the rows stay one line each side: a row laid along the aisle is never followed by one against the walls,
        # which had set crypt 02's door-end pair a pace further out; QA round 2, Q2S-5: "The two rows of coffins are not
        # equally spaced in the room")
        if row_mode is not None: tries = [x for x in tries if (x[0], round(x[1], 2)) == row_mode] or tries[:0]
        for tt, a_row, km, edge in tries:
            if a_row is None:
                hd = ax.halves(tt)[0]
                dd = d - hd
                ok = 1 if dd - hd >= 2.6 and sp.put(tt, dd, 0.0) else 0
                s_out = ax.halves(tt)[1]
            else:
                ok, dd, hd, s_out = row(tt, d, a_row, km, edge)
            if os.environ.get("NOX_SACRED_DEBUG"): print("   row try", tt, round(d, 2), round(a_row or 0, 2), ok)
            if ok:
                heads.append((dd, min(W - 0.9, s_out + 0.8)))
                if what == (rows_of[-1] if rows_of else None) and row_mode is None and tt != t:
                    row_mode = (tt, round(a_row, 2))
                rows += 1
                d = dd - hd - (2.4 if a_row is None else (0.8 if hd > ax.halves(tt)[1] else 1.1))   # (tombs along the
                # aisle lie end to end in two lines down a long crypt, a pace between; single tombs on the line apart)
                done = True
                break
        if not done: d -= 1.0
    # where the side doors' ways left a stretch of the floor without a row, single tombs on the middle line fill it
    t_mid = (lambda t0: along_of(t0) or t0)(t_coff or t_sarc) if (t_coff or t_sarc) else None
    if t_mid and heads:
        hd_m = ax.halves(t_mid)[0]
        d = D - 3.4 - hd_m
        while d - hd_m > 2.6:
            if f._fam_n["tomb"] < tomb_cap and all(abs(d - dd) > hd_m + 2.6 for dd, _ in heads) and sp.put(t_mid, d, 0.0):
                heads.append((d, ax.halves(t_mid)[1] + 0.9)); rows += 1
                d -= 2 * hd_m + 2.4
            else: d -= 0.8
    if not rows and (t_sarc or t_coff):          # else the dead laid in the middle, on the line from the door
        t = along_of(t_coff or t_sarc) or (t_coff or t_sarc)
        hd, hs = ax.halves(t)
        d = D - 3.4 - hd
        while not rows and d - hd > 2.6:
            if sp.put(t, d, 0.0):
                heads.append((d, hs + 0.9)); rows += 1
            else: d -= 0.8
    # bones heaped at the rows' heads, mirrored
    for i, (dd, s) in enumerate(heads):
        if s < W - 0.8: sp.bones(dd, s, n=2 if (lotd or i % 2 == 0) else 1)
    # graves at the rows' heads against the side walls where the walls are free (a crypt's identity: RM-CRYPT-10)
    gst = [t for t in ("Tombstone2", "Tombstone4", "Tombstone7", "DunMirTombstone1") if f.ok_type(t)] if not lotd         else [t for t in ("LOTDTombstone1", "LOTDTombstoneHorns3", "LOTDTombstoneScroll3") if f.ok_type(t)]
    if gst:
        g_t = rng.choice(gst)
        gh = max(ax.halves(g_t))
        for dd, s in heads[::2]:
            if f._fam_n["tomb"] + 2 > tomb_all: break
            if W - gh - 0.4 > s + gh + 0.3: sp.pair(g_t, dd, W - gh - 0.4)
    sp.bones(D / 2.0, 0.6, n=1)
    # (statues, obelisks and lights go to the dressing below, which stands what is tall on the back walls only: the
    # front walls, SE and SW, hold low pieces, TP3-a; QA round 1, third pass)
    stones = [t for t in ("Tombstone2", "Tombstone4", "Tombstone7", "DunMirTombstone1") if f.ok_type(t)] if not lotd \
        else lotd_stones
    if stones and d > 3.2 and f._fam_n["tomb"] + 2 <= tomb_all:
        # (beside the main door's way in, a centred double door's wider than a single's: QA round 2)
        g_s = rng.choice(stones)
        op = f.main_door()
        s_g = max(aisle + 0.9, (op["half"] + max(ax.halves(g_s)) + 0.2) if op else 0.0)
        if s_g + max(ax.halves(g_s)) <= W - 0.2: sp.pair(g_s, min(d, 3.4), s_g)
    lt = "LOTDCandleabra1" if lotd and f.ok_type("LOTDCandleabra1") else f.light_type()
    if on_far: sp.light_pair(D - 0.9, s_flank + oh + 1.2, t=lt)
    f.aisle = dict(run=ax.far, mid=ax.mid, half=aisle, first=2.0, far=D, door=None)
    # a tapestry pair on the far wall when it is a back wall
    if ax.far_back:
        f.decor_theme()
        s = s_flank + 2.4
        if s < W - 1.2:
            f._hang(ax.far, ax.mid - s); f._hang(ax.far, ax.mid + s)
    # the walls and corners dressed until the crypt is full enough in visible pieces, the back walls first
    dress(f, ax, sp, "crypt", crypt_pieces(f, ax, lotd), extra=2)     # (kinds past the goal: QA round 2, never emptier)
    return bool(rows) or bool(wide)


# ---- fullness: the walls and corners dressed until the room is full enough (QA round 1, second and third passes) -----
# The coordinator's reads of the first passes (2026-10-13): small and two-door crypts and mana rooms with doors on several
# walls came out nearly bare (RM-CRYPT-09's fault again: "Worst one in the set, very empty"), against the user's first
# theme of the round, "spaces are too empty and lack object diversity" (Q1T); then, of the second pass, that crypts 02 and
# 05 still read as empty at full size: the count had taken skulls, cobwebs and candles a few pixels wide as kinds, and
# crypt 05's pieces stood against its front walls. So:
# - only pieces a person sees count: a piece at least an urn's size on screen (a circle of 7 px, a box of 11), with a
#   furniture family or a standing light (candelabra, brazier, basin); bones, skulls, cobwebs, candles and the like count
#   together as one kind at most, and never toward the covered floor;
# - each type holds a least number of those kinds by its floor tiles and covers a least share of its floor;
# - the dressing fills the back walls (NE, NW) first; a front wall (SE, SW) takes only low pieces (validate/checks.py
#   sacred.fullness holds the same numbers).
FULL_COVER = {"chapel": 0.07, "coven": 0.10, "mana_room": 0.07, "crypt": 0.10}
FULL_KINDS = {"chapel": (8, 12), "coven": (8, 12), "mana_room": (8, 12), "crypt": (7, 11)}     # (least, most)
TINY_RX = re.compile(r"^(Skull|ArmBone|LegBone)$|^Skull\d$|^Corpse|^SpiderWeb|^Candle\d|CandleGroup|^LOTDCandle(Large|Small)$|"
                     r"Bottle|Potion|^Book|Book\d$")
STANDING_LIGHT_RX = re.compile(r"^(Candleabra\d|LOTDCandleabra\d|Brazier|SpikeBrazier|HandBrazier|DunMirFlameBasin|"
                               r"LOTDIncenseBasin)")


def visible_size(ext, ex, ey):
    """True when a piece's footprint is at least an urn's on screen (StatueVase: a circle of 7 px, a box of 11)."""
    if ext == "CIRCLE": return (ex or 0) >= 7
    if ext == "BOX": return max(ex or 0, ey or 0) >= 11
    return False


def fullness_goal(rtype, tiles):
    """(distinct visible kinds of piece, covered share of the floor) a sacred room of the type and size holds at least: a
    kind more for every 45 tiles past 30, within the type's (least, most)."""
    lo, hi = FULL_KINDS.get(rtype, (5, 9))
    return max(lo, min(hi, lo + int(max(0, tiles - 30) // 45))), FULL_COVER.get(rtype, 0.06)


def counted_kind(t, family, ext=None, ex=0, ey=0):
    """The kind a piece counts as in the room's diversity, or None: "small" for every tiny piece together (bones, skulls,
    cobwebs, candles, anything under an urn's size); a visible piece with a furniture family (rules/room_types.py, the
    relics included) or a standing light by its stem; nothing else (doors, colour lights)."""
    if TINY_RX.search(t) or (ext is not None and not visible_size(ext, ex, ey)):
        return "small" if (family or TINY_RX.search(t) or STANDING_LIGHT_RX.match(t)) else None
    if family or STANDING_LIGHT_RX.match(t): return re.sub(r"(\d+[a-z]?|NE|NW|SE|SW|N|S|E|W)$", "", t)
    return None


def kinds_of(f):
    from kit.furnish import _family_of
    out = set()
    for o in f.objects:
        t = o["type"]
        ext, ex, ey, _ = f.things.get(t, ("NULL", 0, 0, ""))
        k = counted_kind(t, _family_of(t), ext, ex, ey)
        if k: out.add(k)
    return out


def _facing(ax, sign):
    """The compass name a piece on the sign side of the axis looks toward the axis by (StatueVase's variants)."""
    if ax.line == "/": return "SW" if sign > 0 else "NE"      # lateral is v: +v is NE
    return "NW" if sign > 0 else "SE"                           # lateral is u: +u is SE


def _end_back(ax):
    """Which end wall is a back wall: "far", "near" or None."""
    if ax.far_back: return "far"
    if ax.near and ax.near["side"] in BACK_SIDES: return "near"
    return None


def _spots(ax, r_, tall, inner=False, front_along=False):
    """Wall and corner spots for a pair of pieces of radius r_, the back walls first: [(mode, depth, lateral)]. mode "x":
    the pair mirrored across the axis at (d, -s) and (d, +s); "a": the pair on the back side wall mirrored about the
    room's middle along the axis, at (d, b*s) and (D - d, b*s); "f": the same on the front side wall. A tall piece takes
    the back walls only (the end wall the camera sees, both of a pair on it, and the back side wall); a low one the side
    and front walls too."""
    D = ax.D
    out = []
    w_end = ax.half_width(max(1.0, D - 2.0), D - 0.6)
    eb = _end_back(ax)
    if eb:                                       # the back end wall, either side of the axis (the corners last)
        d = D - r_ - 0.45 if eb == "far" else r_ + 0.7
        a = 2.4 + r_
        while a < w_end - r_ - 0.35:
            out.append(("x", d, a)); a += 2.3
        out.append(("x", d, w_end - r_ - 0.45))
    d = D - r_ - 0.6                             # the back side wall, mirrored about the middle along the axis
    while d > D / 2.0 + r_ + 0.4:
        out.append(("a", d, min(ax.sides_at(d)) - r_ - 0.35)); d -= 2.3
    if not tall:
        d = D - r_ - 2.6                         # both side walls, mirrored across the axis
        while d > r_ + 1.6:
            out.append(("x", d, min(ax.sides_at(d)) - r_ - 0.35)); d -= 2.3
        fronts = ([D - r_ - 0.45] if eb != "far" else []) + ([r_ + 0.7] if eb != "near" else [])
        for dd in fronts:                        # the front end wall(s)
            a = 2.4 + r_
            while a < w_end - r_ - 0.35:
                out.append(("x", dd, a)); a += 2.3
    if front_along and not tall:
        # the front side wall, mirrored about the room's middle along the axis (mode "f"), where its twin across the axis
        # would stand under the back side wall's hangings (QA round 2: chapel 04's SE aisle left bare, a kind short)
        d = D - r_ - 2.6
        while d > D / 2.0 + r_ + 0.4:
            out.append(("f", d, min(ax.sides_at(d)) - r_ - 0.35)); d -= 2.3
    if inner:                                    # (a mana room: the open floor between its rings and its walls too)
        # from both ends toward the middle in turn, so the floor fills evenly at both ends (QA round 2: mana room 01's
        # dressing had all stood by its near wall, the far half of the floor bare)
        ds, d = [], 2.6
        while d < D - 2.6:
            ds.append(d); d += 2.8
        for d in sorted(ds, key=lambda x: (min(x, D - x), x)):
            w_ = min(ax.sides_at(d))
            out += [("i", d, w_ * 0.55), ("i", d, w_ * 0.75)]      # (mirrored across the axis only: QA round 2)
    return out


def dress(f, ax, sp, rtype, pieces, both_ways=False, max_pairs=26, extra=0, front_along=False):
    """Pairs of `pieces` [(name, chooser(sign) -> type, tall)] against the walls and in the corners, the back walls first
    (_spots), a kind the room lacks before another of one it has, until the room reaches its fullness_goal in visible
    kinds and covered floor. Each kind two pairs at most (one when the set piece placed it already, a showpiece once), the
    type's caps held, 0.7 units clear of every piece, never under a hanging. extra: kinds past the goal (and 1% more
    cover each). Returns the pairs placed."""
    from kit.furnish import _family_of as _fo, SHOWPIECES
    goal_k, goal_c = fullness_goal(rtype, len(f.room.tiles))
    goal_k, goal_c = goal_k + extra, goal_c + 0.01 * extra
    placed, tried, per_kind = 0, set(), Counter()
    present0 = kinds_of(f)
    b = ax.back_s
    first = True                                 # every kind once (the walls filled), then more until full enough
    while placed < max_pairs:
        have = kinds_of(f)
        if not first and len(have) >= goal_k and f.coverage() >= goal_c: break
        order = sorted(pieces, key=lambda p: (counted_kind(p[1](1) or "", _fo(p[1](1) or "")) in have, not p[2], p[0]))
        progress = False
        for name, choose, tall in order:
            t1, t2 = choose(-1), choose(1)
            if not (t1 and t2 and f.ok_type(t1) and f.ok_type(t2)): continue
            if per_kind[name] >= (1 if SHOWPIECES.match(t1) or counted_kind(t1, _fo(t1)) in present0 else 2): continue
            cap = f.repeat_cap(_fo(t1))
            if cap is not None and f._fam_n[_fo(t1)] + 2 > cap: continue
            r_ = max(f.half(t1))
            light = STANDING_LIGHT_RX.match(t1) is not None
            for mode, d, s in _spots(ax, r_, tall, inner=both_ways, front_along=front_along):
                key = (name, mode, round(d, 1), round(s, 1))
                if key in tried or s < 1.0: continue
                tried.add(key)
                if mode in ("x", "i"): at = [(t1, d, -s), (t2, d, s)]
                elif mode == "a": at = [(t2, d, b * s), (t2, ax.D - d, b * s)]
                else: at = [(t1, d, -b * s), (t1, ax.D - d, -b * s)]
                if not all(_clear_spot(f, t_, *ax.uv(d_, s_)) for t_, d_, s_ in at): continue
                if light: f.placing_light = True
                try:
                    o1 = sp.put(at[0][0], at[0][1], at[0][2])
                    o2 = o1 and sp.put(at[1][0], at[1][1], at[1][2])
                    if o1 and not o2: f._remove(o1)
                    got = bool(o1 and o2)
                    if not got and both_ways and mode == "x" and abs(ax.D - 2 * d) > 2.0:
                        o1 = sp.put(t2, d, s); o2 = o1 and sp.put(t2, ax.D - d, s)
                        if o1 and not o2: f._remove(o1)
                        got = bool(o1 and o2)
                finally:
                    f.placing_light = False
                if got:
                    placed += 1; progress = True; per_kind[name] += 1
                    break
            if placed >= max_pairs: break
            have = kinds_of(f)
            if not first and len(have) >= goal_k and f.coverage() >= goal_c: break
        if not progress and not first: break
        first = False
    if os.environ.get("NOX_SACRED_DEBUG"):
        print("  dress", rtype, f.room.id, len(f.room.tiles), "goal", goal_k, round(goal_c, 2), "kinds", len(kinds_of(f)),
              "cover", round(f.coverage(), 3), dict(per_kind))
    return placed


def _clear_spot(f, t, u, v):
    """A dressing piece at (u, v) keeps 0.7 units from every standing piece (statues apart: pieces.clearance) and never
    stands under a hanging (pieces.hung), as the knowledge base holds single pieces (the set piece's pairs skip it); nor
    on a carpet, whose pieces are the set piece's, centred on it (QA round 2, Q2T-2: mana room 02's ring carpet took
    pedestals at one end and statues at the other)."""
    hu, hv = f.half(t)
    if any(b[0] - hu < u < b[1] + hu and b[2] - hv < v < b[3] + hv for b in f.carpet_boxes): return False
    for tt, rec in f._typed:
        if not rec[4] or rec[5] == "wall": continue
        if max(abs(u - rec[0]) - hu - rec[2], abs(v - rec[1]) - hv - rec[3]) < 0.7: return False
    return not f._under(u, v, hu, hv, hanging=False)


def crypt_pieces(f, ax, lotd, obelisks=True):
    """The crypt's dressing, visible pieces (QA round 1, third pass): statue pairs, urns, candelabras, monuments,
    gravestones, coffins stacked against the walls, crates of burial goods, a bone heap, braziers, rubble; (name,
    chooser, tall). obelisks=False: the statue pairs are statues or gargoyles, never more mana obelisks (a coven's: Q2S-4)."""
    rng = f.rng
    vase = rng.choice(("StatueVase1", "StatueVase2"))
    rub = rng.choice(["RuinsColumnIndoorRubble%02d" % k for k in (1, 3, 5, 7, 9, 11)])
    stone = rng.choice(("LOTDTombstone2", "LOTDTombstone3", "LOTDTombstone4") if lotd else
                       ("Tombstone2", "Tombstone4", "Tombstone7"))
    statue = rng.choice(("Statue2a", "Statue2c")) if not lotd or not obelisks else "LOTDManaObelisk"
    gar = rng.choice(("Gargoyle2", "Gargoyle4", "Gargoyle5"))
    crate = rng.choice(("DarkCrate1", "DarkCrate2", "Crate1", "Crate2"))
    coffin_along = (_oriented(f, ax, r"^Coffin[1-4]$", across=False) or [None])[0]
    broken = rng.choice(("CoffinBreaking1", "CoffinBreaking2", "CoffinBreaking3", "CoffinBreaking4"))
    lt = "LOTDCandleabra1" if lotd and f.ok_type("LOTDCandleabra1") else f.light_type()
    return [("statues", lambda sg: statue, True),
            ("gargoyles", lambda sg: gar, True),
            ("monuments", lambda sg: "Monument1", True),
            ("candelabra", lambda sg: lt, True),
            ("boneheap", lambda sg: "LOTDFlamingSkullsStatic", True),
            ("braziers", lambda sg: "Brazier", True),
            ("urns", lambda sg: vase + _facing(ax, sg), False),
            ("urns2", lambda sg: ("StatueVase2" if vase == "StatueVase1" else "StatueVase1") + _facing(ax, sg), False),
            ("graves", lambda sg: stone, False),
            ("coffins", lambda sg: coffin_along, False),
            ("crates", lambda sg: crate, False),
            ("rubble", lambda sg: rub, False),
            # (low funerary kinds for the walls a full crypt's rows leave only low room by: QA round 2, never emptier)
            ("broken", lambda sg: broken, False), ("skullstones", lambda sg: "LOTDTombstoneSkulls1", False)]


def mana_pieces(f, ax):
    """The mana room's dressing: mana carts, glowing jars, generators, candelabras, braziers, urns, orb pedestals,
    statues, monuments, fire basins; (name, chooser, tall). Never crystals, crystal pillars, stalagmites or obelisks past the rings
    (QA round 2, Q2S-3: "Way too many mana pillars, obelisks, crystals. Cut them in half ... the mana crystals look out of
    place in the middle of an interior floor"): the freed floor takes other arcane kinds."""
    lt = f.light_type()
    statue = f.rng.choice(("Statue2a", "Statue2c"))
    return [("carts", lambda sg: "MineManaCart1" if ax.line == "/" else "MineManaCart2", False),
            ("generators", lambda sg: "VandegrafSmall", True), ("candelabra", lambda sg: lt, True),
            ("braziers", lambda sg: "HandBrazier", True),
            ("jars", lambda sg: "FairyJar", False), ("urns", lambda sg: "StatueVase2" + _facing(ax, sg), False),
            ("pedestals", lambda sg: "OrbPoolEnd1", False), ("statues", lambda sg: statue, True),
            ("monuments", lambda sg: "Monument1", True), ("basins", lambda sg: "DunMirFlameBasinLit", False),
            ("incense", lambda sg: "LOTDIncenseBasinLit", False)]


COMPOSERS = {"nave": chapel, "coven": coven, "mana": mana_room, "crypt": crypt}


def _snapshot(f):
    return dict(objects=len(f.objects), carpets=len(f.carpet_undo), zones=len(f.g.zones), spots=len(f.spots),
                runners=len(f.runner_boxes), anchors=len(f.anchors), lights=len(f.ring_lights))


def _reset(f, snap):
    """Takes back everything laid since the snapshot: pieces, carpets (their floor and trim as they were), zones."""
    from kit.grammar import lift_carpet
    for o in list(f.objects[snap["objects"]:])[::-1]: f._remove(o)
    for rec in list(f.carpet_undo[snap["carpets"]:])[::-1]: lift_carpet(f, rec)
    del f.g.zones[snap["zones"]:]; del f.spots[snap["spots"]:]; del f.runner_boxes[snap["runners"]:]
    del f.anchors[snap["anchors"]:]; del f.ring_lights[snap["lights"]:]


def compose(f):
    """Furnishes the room as its recipe's set piece (ROOMS[kind]["composer"]); False leaves the room bare for the
    furnisher's own path."""
    fn = COMPOSERS.get(f.ident.get("composer"))
    if not fn: return False
    saved = (f.in_required, f.composing)
    snap = _snapshot(f)
    f.in_required, f.composing, f.set_piece = True, False, True
    try:
        ok = fn(f)
    finally:
        f.in_required, f.composing = saved
        f.set_piece = False
    if not ok:
        _reset(f, snap)
        f.aisle = None
        return False
    f.face_statues()
    f.grammar_log = {"set_piece": 1}
    # the Land of the Dead's floors take no second floor under the tombs (QA round 2, Q2S-5, RM-CRYPT-05: "The tile
    # blending and the floor are wrong": a plinth of LOTDDark blended into the LOTDPitted floor; Westwood lays its LOTD
    # halls in one floor): kit/shells.py lay_zones leaves the room as laid
    if f.style == "lotd":
        try: f.room.no_zones = True
        except AttributeError: pass
    return True
