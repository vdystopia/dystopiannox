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

# the chapel's altar end: one of these by the deficit over a map's chapels (the user: "all rooms use the same altar - try
# different objects"): Dun Mir's altar alone between fire basins, the holy font (the orb pool) or a fountain before it, a
# saint's great statue behind it. Every one keeps a Dun Mir altar (the type's must: kit/roomtypes.py), the eye meets
# the piece before or behind it
CHAPEL_ALTARS = (("altar", 3.0), ("font", 2.0), ("saint", 2.5), ("fountain", 1.5))
# the coven's: the lich god's statue over a sarcophagus, a bier between flaming skulls, a burning pyre of skulls
COVEN_ALTARS = (("lich", 3.0), ("bier", 2.5), ("pyre", 2.0))
# a mana ring's centrepiece (the user: "Try some other centerpiece objects")
MANA_CENTRES = (("DunMirAltar1", 1.0), ("CrystalColumn", 2.0), ("MineManaCrystal9", 2.0), ("MineManaCrystal11", 1.5),
                ("CrystalBlueLargeStalagmite", 1.5), ("OrbPoolWithOrb", 1.5), ("Orrery1", 1.0), ("VandegrafLarge", 1.0))
# the saint's statue faces out from the back wall it stands on (Horrendous, the warrior saint of the Kingdoms)
SAINT = {"/|BR": "HorrendousStatue2", "\\|BL": "HorrendousStatue1"}


def _spread(f, key, options, ok=lambda n: True):
    """One of `options` [(name, weight)] for this room, by the deficit of each over the map's rooms drawn so far (as
    kit/archetypes.py draws archetypes), reproducible from the map's name and the room; a room furnished again (the
    originality check's retries) keeps its draw."""
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
    tot_w = sum(w for _, w in opts)
    n_used = sum(used[n] for n, _ in opts)
    ws = [max(0.05, (n_used + 1) * w / tot_w - used[n]) for n, w in opts]
    rng = random.Random(zlib.crc32(f"sacred:{key}:{f.spec.d.get('name')}:{k[1]}:{n_used}".encode()))
    pick = rng.choices([n for n, _ in opts], ws)[0]
    used[pick] += 1
    memo["rooms"][k] = pick
    return pick


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


def door_axis(f):
    """The axis from the room's main door (Furnisher.main_door) to the far wall across from it, or None."""
    op = f.main_door()
    if not op: return None
    ax = Axis(f, op["line"], op["coord"], op["sign"], op["along"])
    return ax if ax.far and ax.D >= 8 else None


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
    wide either side of the axis (squares are 2 uv units; their seams lie at odd coordinates): a runner of even squares
    when the axis lies on a seam, odd when it runs through the squares' middles. Returns its half width or 0."""
    from kit.furnish import CARPET_FLOORS
    if not CARPET_FLOORS.search(f.room.floor or ""): return 0.0
    m = ax.mid
    odd = abs(m - round(m)) < 0.01 and round(m) % 2 == 1
    even = abs(m - round(m)) < 0.01 and round(m) % 2 == 0
    if not (odd or even): return 0.0
    for squares in want:
        if (squares % 2 == 0) != odd: continue
        half = float(squares)                     # squares of 2 units: half width = squares
        for a, b in ((d0, d1), (d0 + 1.0, d1), (d0 + 2.0, d1), (d0 + 2.0, d1 - 1.0), (d0 + 3.0, d1 - 1.0)):
            if b - a < 4.0: continue
            (u0, v0), (u1, v1) = ax.uv(a, -half + 0.5), ax.uv(b, half - 0.5)
            mat = f.rng.choice(("RugRed", "RugRed", "RugBlueNorm"))
            if f.lay_carpet((min(u0, u1), max(u0, u1), min(v0, v1), max(v0, v1)), margin=0.0, material=mat):
                f.runner_boxes.append(f.carpet_boxes[-1])
                return half
    return 0.0


def _pews(sp, d_hi, d_lo, s0, rows_max, k_max, s_wall, types):
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
    rows = 0
    d = d_hi - hd
    sp.pew_rows = []
    while rows < rows_max and d - hd >= d_lo:
        placed = 0
        for i in range(k):                       # a row whose half-rows do not fit (a side door's way in) is left out
            if not sp.pair(t, d, s0 + hs + i * pitch): break
            placed += 1
        if placed:
            rows += 1
            sp.pew_rows.append(d)
        d -= 2.5
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
    style = _spread(f, "chapel_altar", CHAPEL_ALTARS,
                    ok=lambda n: (n not in ("font", "fountain") or (W >= 8.0 and D >= 18.0)) and
                    (n != "saint" or bool(ax.far_back and SAINT.get(ax.far["side"]))))
    statue_types = _types(f, "statue", r"^Statue2[a-h]$") or {"Statue2a": 1}
    st = _pick(f, statue_types)
    sr = max(f.half(st))
    # the altar end: the altar against the far wall; a saint's statue behind it, or the holy font before it
    alt = "DunMirAltar2" if f.rng.random() < 0.35 else "DunMirAltar1"
    ahd, ahs = ax.halves(alt)
    wide = ahs
    d_alt = D - ahd - 0.45
    if style == "saint":
        big = SAINT.get(ax.far["side"])
        bhd, bhs = ax.halves(big)
        if sp.put(big, D - bhd - 0.3, 0.0):
            d_alt = D - 2 * bhd - 0.3 - 0.7 - ahd
            wide = max(ahs, bhs)
        else: style = "altar"
    if not sp.put(alt, d_alt, 0.0, snug=style != "saint"): return False
    front = d_alt - ahd
    if style in ("font", "fountain"):
        basin_t = "OrbPoolWithOrb" if style == "font" else "Fountain"
        bhd, bhs = ax.halves(basin_t)
        if sp.put(basin_t, front - 1.1 - bhd, 0.0): front = front - 1.1 - 2 * bhd
        else: style = "altar"
    # the priest beside the altar (nox14: "Have the priest stand closer to the altar"), statues flanking past him
    from kit.furnish import _px
    pu, pv = ax.uv(d_alt - 0.2, ax.back_s * (ahs + 0.95))
    f.spots.append(dict(role="priest", px=_px(pu, pv)))
    s_stat = wide + 2.0 + sr
    sp.pair(st, D - sr - 0.45, s_stat)
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
    cap = max(4, min(16, int(tiles / 10)))
    bench = _types(f, "bench")
    s0 = s_run + 0.6
    s_wall = W - 1.7 - (2 * ch + 0.7 if ct else 0.0)
    k_max = 3 if W >= 11 else 2
    colonnade = (f.archetype or {}).get("name") == "colonnade_chapel"    # (kit/archetypes.py: fewer pews, more columns)
    if colonnade: k_max = max(1, k_max - 1)
    rows_max = max(1, cap // 2)
    d_hi = front - 3.0
    d_lo = max(4.5, 0.28 * D)
    rows, k, s_out, pt = _pews(sp, d_hi, d_lo, s0, rows_max, k_max, s_wall, bench)
    if not rows and ct:                      # a narrow nave: its pews before its columns, the columns against the walls
        rows, k, s_out, pt = _pews(sp, d_hi, d_lo, s0, rows_max, k_max, W - 1.5, bench)
        if not rows:                         # the runner is the aisle: the pews may meet the side walls
            rows, k, s_out, pt = _pews(sp, d_hi, d_lo, s0, rows_max, 1, W - 0.45, bench)
        if W - 0.35 - ch < s_out + 0.4 + ch: ct = None
        else: s_out = W - 0.35 - 2 * ch - 0.7
    # columns: a pair at the outer end of each row (every other row in a long nave), and a pair before the sanctuary
    col_s = s_out + 0.7 + ch
    if ct and rows:
        pd = ax.halves(pt)[0]
        step = 1 if rows <= 3 or colonnade else 2
        # one even pitch down the whole nave, lined up with the rows and on past them to the door (RM-CHAPEL-08:
        # "Balance and line up the pillars and benches better")
        col_d = list(sp.pew_rows[::step])
        d = col_d[-1] - step * 2.5
        while d >= 2.4:
            col_d.append(d); d -= step * 2.5
        for d_c in col_d:
            sp.pair(ct, d_c, col_s)
    # the side aisles: statues against the side walls between the column pairs, tapestries on the back side wall
    pew_rows_d = list(getattr(sp, "pew_rows", []))
    if rows >= 2 and W - col_s - ch >= 2.4:
        for i in range(1, rows, 2):
            dm = (pew_rows_d[i - 1] + pew_rows_d[i]) / 2.0
            sp.pair(st, dm, ax.half_width(dm - 1, dm + 1) - sr - 0.5)
            if sum(1 for o in f.objects if o["type"].startswith("Statue2")) >= 6: break
    # the narthex by the door: founders' tombs in a big nave, else a pair of statues flanking the runner's foot
    d_n = (d_lo - 0.8 + 2.4) / 2.0
    tomb = None
    if tiles >= 150:
        tombs = [t for t in _oriented(f, ax, r"^Crypt(1|3|5|6|7|8|9|10|11|12)$", across=False)]
        tomb = f.rng.choice(tombs) if tombs else None
    if tomb and d_lo - 2.4 >= 2 * ax.halves(tomb)[0] + 1.0:
        thd, ths = ax.halves(tomb)
        if not sp.pair(tomb, (2.6 + d_lo - 0.6) / 2.0, s_run + 1.2 + ths): tomb = None
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
    while d > 2.6:
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
    sp.pair(mon, 2.8, s_run + 1.2)
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
    # the carpet: squares are 2 units, centred at even coordinates; centred under the ring when its edges lie as far
    # either side of the middle: an odd count of squares round an even middle, an even count round an odd one
    m = r + oh + 0.5
    box = []
    for c in (u, v):
        n = int(math.ceil(m))                          # half width in units, whole
        if c % 2 == 0 and n % 2 == 0: n += 1           # even middle: odd half widths (seams at odd coordinates)
        if c % 2 == 1 and n % 2 == 1: n += 1           # odd middle: even half widths
        box.append((c - n + 0.5, c + n - 0.5))
    laid = f.lay_carpet((box[0][0], box[0][1], box[1][0], box[1][1]), margin=0.0, material=carpet_mat)
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
    most = 1 if tiles < 100 else 2 if tiles < 170 else 3 if tiles < 230 else 4
    cen = _spread(f, "mana_centre", MANA_CENTRES, ok=lambda n: f.ok_type(n))
    if not cen: cen = "CrystalColumn"
    from kit.furnish import PALETTES
    mats = f.rng.choice(PALETTES["carpet"])
    mat = mats[0]
    rings = 0
    snap = _snapshot(f)
    show = bool(SHOWPIECES.match(cen))
    alt = next((c for c in ("MineManaCrystal9", "CrystalColumn", "DunMirAltar1") if c != cen and f.ok_type(c)), "CrystalColumn")

    def foot(c):
        return 2 * (max(2.0, math.ceil(max(f.half(c)) + max(f.half(ob)) + 1.0)) + max(f.half(ob)) + 0.5)
    # the most rings the room holds (its size: 1 under 100 tiles, 2 under 170, 3 under 230, else 4), each round the
    # room's centrepiece; a showpiece (an orrery, a generator: kit/furnish.py SHOWPIECES) stands once, in the only ring or
    # the middle one of three, the others round the second centrepiece
    plans = []
    for n, pos in _ring_layouts(L, S, max(foot(cen), foot(alt))):
        if n > most: continue
        cs = [cen if (not show or n == 1 or (n == 3 and k == 1)) else alt for k in range(n)]
        plans.append((n, pos, cs))
    for n, pos in _ring_layouts(L, S, foot(alt)):
        if n <= most: plans.append((n, pos, [alt] * n))
    for n, pos in _ring_layouts(L, S, foot("CrystalColumn")):
        if n <= most: plans.append((n, pos, ["CrystalColumn"] * n))
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
    cl = f.rng.choice([t for t in ("MineManaCrystal1", "MineManaCrystal2", "MineManaCrystal5", "MineManaCrystal6",
                                   "CrystalBlueSmallStalagmite", "MineManaCrystal9") if f.ok_type(t)] or ["CrystalColumn"])
    ch = max(f.half(cl))
    for d in (ch + 1.0, L - ch - 1.0):
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
        if t:
            hu, hv = f.half(t)
            hp = hu if r["line"] == "/" else hv
            f.try_put(t, *f._uv_on(r, hp + 0.22, mid), snug=True)
        # bookcases end to end either side, mirrored about the wall's middle
        bc = f.side_variant("Bookcase1", r, "shelves")
        if bc:
            hu, hv = f.half(bc)
            hp, ha = (hu, hv) if r["line"] == "/" else (hv, hu)
            n_bc = max(2, min(4, int((r["hi"] - r["lo"]) * 0.18 / (2 * ha))))
            for k in range(n_bc):
                a = 2.6 + ha + k * (2 * ha + 0.05)
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
    if rings == 2:                               # the open floor between two rings: an orrery, else a crystal
        if not (f.ok_type("Orrery2") and f.try_put("Orrery2", *ax.uv(L / 2.0, 0.0))):
            f.try_put("CrystalBlueLargeStalagmite", *ax.uv(L / 2.0, 0.0))
    # each ring flanked across the room by a pair of crystal clusters (or candelabras), its carpet's width out
    small = [t for t in ("MineManaCrystal1", "MineManaCrystal2", "MineManaCrystal5", "MineManaCrystal6",
                         "CrystalBlueSmallStalagmite") if f.ok_type(t) and t != cl]
    for d, s in getattr(f, "ring_pos", []):
        if s < -0.1 or not small: continue
        t = f.rng.choice(small)
        for gap in (5.4, 4.6, 6.2):
            if s + gap > W - 1.2: continue
            if sp.pair(t, d, s + gap): break
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
    if W < 3.6 or D < 9: return False
    lotd = f.style == "lotd"
    rng = f.rng
    obel = "LOTDManaObelisk" if lotd and f.ok_type("LOTDManaObelisk") else "Obelisk"
    has_ob = rng.random() < 0.8 and f.ok_type(obel)
    oh = max(f.half(obel))
    # the centrepiece
    centre = _spread(f, "crypt_centre", (("chest", 2.0), ("tomb", 2.0), ("monument", 1.5)))
    wide = 0.0
    if centre == "chest":
        from kit.furnish import WALL_SIDE_TYPE
        t = WALL_SIDE_TYPE["CryptChest"].get(ax.far["side"])
        if t and f.ok_type(t):
            hd, hs = ax.halves(t)
            if sp.put(t, D - hd - 0.25, 0.0, snug=True): wide = hs
    if centre == "tomb" or (centre == "chest" and not wide):
        t = next((x for x in ("Crypt2", "Crypt4") if f.ok_type(x)), None)
        if t:
            hd, hs = ax.halves(t)
            if sp.put(t, D - hd - 1.0, 0.0): wide = hs
    if not wide:
        if sp.put("Monument1", D - 1.2, 0.0): wide = 0.5
    s_flank = wide + 1.2 + oh
    if has_ob:
        sp.pair(obel, D - oh - 0.5, s_flank)
    else:
        st = _pick(f, _types(f, "statue", r"^Statue2[a-h]$") or {"Statue2a": 1})
        if f.ok_type(st): sp.pair(st, D - 0.95, s_flank)
    # the rows of the dead either side of the aisle
    kind = rng.random()
    sarcs = _oriented(f, ax, r"^Crypt(1|3)$", across=True) + _oriented(f, ax, r"^Crypt(5|6|7|8|9|10|11|12)$", across=True)
    coffins = _oriented(f, ax, r"^Coffin[1-4]$", across=True)
    lotd_stones = [t for t in ("LOTDTombstone2", "LOTDTombstone3", "LOTDTombstone4", "LOTDTombstoneSkulls1",
                               "LOTDTombstoneScroll1") if f.ok_type(t)]
    if False: rows_of = ["stones"]           # (RM-CRYPT-10 read its LOTD stones as no graves: coffins or sarcophagi)
    elif kind < 0.4 and coffins: rows_of = ["coffins"]
    elif kind < 0.65 and coffins and sarcs: rows_of = ["sarcs", "coffins"]       # the old dead nearest the far wall
    else: rows_of = ["sarcs"] if sarcs else (["coffins"] if coffins else [])
    aisle = 1.5 if W < 6 else 1.8
    d = D - 3.4 - (1.0 if has_ob else 0.4)            # a walk round the far end, before its centrepiece
    rows = 0
    t_sarc = rng.choice(sarcs) if sarcs else None
    t_coff = rng.choice(coffins) if coffins else None
    t_stone = rng.choice(lotd_stones) if lotd_stones else None
    heads = []
    if os.environ.get("NOX_SACRED_DEBUG"): print("  crypt rows", f.room.id, rows_of, t_sarc, t_coff, round(W, 1), round(D, 1), round(d, 1))
    d_start = d
    heads = []
    for orient in ("across", "along"):           # tombs across the aisle; where a side door's way keeps them out, along it
        d = d_start
        while True:
            what = rows_of[min(len(rows_of) - 1, rows // 2)] if rows_of else None
            t = {"sarcs": t_sarc, "coffins": t_coff, "stones": t_stone}.get(what)
            if not t: break
            hd, hs = ax.halves(t)
            if (orient == "along" or aisle + 2 * hs > W - 0.9) and hs > hd:   # along the aisle (a narrow crypt)
                stem = re.sub(r"\d+$", "", t)
                along_ = [x for x in _oriented(f, ax, "^" + stem + r"\d+$", across=False)
                          if not stem.startswith("Crypt") or x in ("Crypt1", "Crypt3") or t not in ("Crypt1", "Crypt3")]
                if along_:
                    t = min(along_, key=lambda x: ax.halves(x)[1])
                    hd, hs = ax.halves(t)
            dd = d - hd
            if dd - hd < 3.2: break
            pitch = 2 * hs + 0.5
            k = 2 if W - aisle - 2 * pitch - 1.2 >= 0 and W >= 9 else 1
            a_row = max(0.9, min(aisle, W - 0.8 - 2 * hs))     # a narrow crypt's aisle narrows to a pace
            ok = 0
            for i in range(k):
                s = a_row + hs + i * pitch
                if s + hs > W - 0.75: break
                ok += sp.pair(t, dd, s)
            if ok:                               # (a row a side door's way crosses is left out, the next tried)
                heads.append((dd, a_row + k * pitch - 0.5 + 0.8))
                rows += 1
                d = dd - hd - 1.3
            else:
                d -= 1.0
            if rows >= 6: break
        if rows: break
    if not rows and (t_sarc or t_coff):          # no room for rows (a small crypt's side door): tombs along the side walls
        base = t_coff or t_sarc
        stem = re.sub(r"\d+$", "", base)
        along_ = _oriented(f, ax, "^" + stem + r"\d+$", across=False)
        if along_:
            t = along_[0]
            hd, hs = ax.halves(t)
            d = D - 2.4 - hd
            while d - hd > 2.0 and rows < 2:
                if sp.pair(t, d, W - hs - 0.35):
                    heads.append((d, W - 2 * hs - 1.0)); rows += 1; d -= 2 * hd + 1.4
                else: d -= 0.8
            d = D - 3.4 - hd
            while not rows and d - hd > 4.6:     # else the dead laid in the middle, on the line from the door
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
            if W - gh - 0.4 > s + gh + 0.3: sp.pair(g_t, dd, W - gh - 0.4)
    sp.bones(D / 2.0, 0.6, n=1)
    # statues of the dead (or gargoyles) in pairs along the side walls, tombstones flanking the aisle's foot
    if W >= 6.5 and D >= 14:
        st = _pick(f, _types(f, "statue", r"^Statue2[a-h]$") or {"Statue2a": 1})
        if f.ok_type(st) and not lotd:
            sp.pair(st, D * 0.5, W - 0.95)
    stones = [t for t in ("Tombstone2", "Tombstone4", "Tombstone7", "DunMirTombstone1") if f.ok_type(t)] if not lotd \
        else lotd_stones
    if stones and d > 3.2:
        sp.pair(rng.choice(stones), min(d, 3.4), aisle + 0.9)
    # mana obelisks by the door in a big crypt
    if has_ob and len(f.room.tiles) >= 90:
        sp.pair(obel, 1.6 + oh, W - oh - 0.5)
    # lights in pairs
    from kit import objects as OBJ
    lcap = OBJ.light_cap(len(f.room.tiles))
    lt = "LOTDCandleabra1" if lotd and f.ok_type("LOTDCandleabra1") else f.light_type()
    n_l = 0
    if sp.light_pair(D - 0.9, s_flank + oh + 1.2, t=lt): n_l += 2
    if n_l + 2 <= lcap and sp.light_pair(1.4, min(W - 1.0, aisle + 2.4), t=lt): n_l += 2
    f.aisle = dict(run=ax.far, mid=ax.mid, half=aisle, first=2.0, far=D, door=None)
    # a tapestry pair on the far wall when it is a back wall
    if ax.far_back:
        f.decor_theme()
        s = s_flank + 2.4
        if s < W - 1.2:
            f._hang(ax.far, ax.mid - s); f._hang(ax.far, ax.mid + s)
    return bool(rows) or bool(wide)


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
    return True
