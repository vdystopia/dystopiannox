"""Sentry beams: SentryGlobe (and SentryGlobeMovable, carried by a T.mover) casts a 600-unit beam every frame while it
is enabled; walls stop it (objects do not) and anything with health it touches takes 500 damage: instant death. It
is narrow (a hero one square beside it was untouched), not jumpable, and a disabled globe has no beam, is not drawn,
and starts its sweep again from its base angle when switched on. xfer: BasePosRadian (0 = east, +x; pi/2 = south,
+y), RotateSpeed (radians a frame), CurrentPosRadian.

Rule T6 (rules/TRAPS.md): instant death only where the safe side is plain: a wall corner or stub to stand behind, a
slow sweep (20 s or more a turn), a gap that walks at most one beam a second, a tell before a beam switches on, and
never with forced movement beside it. Here every beam is traced against the map's real walls when the station is
built: none may leave its station (the hall and the end room stay safe), and every rest spot a pattern names must
stay at least CLEAR squares from every beam it can ever cast. The traced beams go into the Meta ("beams", world px)
for the page and the simulator.

Tells: a globe that is off is invisible, so each switched globe has a pair of candelabra at its foot and a strip of
dark floor along its line; SentryCue (behaviours/traps_sentry.go) plays a sound at the globe a moment before its
clock switches it on. Angles come from the station's own vectors (st.along, st.across), never from world directions.

The station frame: a along the run, b across, squares; b = 0 the NW wall. Wall cells are centred (in a lab station)
at half-integer a and whole b: a wall along a lies on the squares' edges, a wall across runs through a row of squares'
middles.
"""
import math
from kit.trapkit import pattern, Meta, frames, SQ

TAU = 2 * math.pi
IN = 0.5                     # squares from its wall to a wall globe (16 px: Westwood sets them 5-16 px from it)
REACH = 600.0                # beam length, px
CLEAR = 0.6                  # squares: a rest spot keeps this far from every beam
STRIP = "LOTDBlackMarble"    # the dark floor along a switched beam's line


# ---- geometry ------------------------------------------------------------------------------------------------------

def _cell(st, a, b):
    """The wall cell whose centre is nearest station point (a, b); a cell (X, Y) (X + Y even) is centred at world
    ((X + .5) * 23, (Y + .5) * 23)."""
    x, y = st.at(a, b)
    fx, fy = x / 23.0 - 0.5, y / 23.0 - 0.5
    X0, Y0 = math.floor(fx), math.floor(fy)
    return min(((X, Y) for X in (X0, X0 + 1) for Y in (Y0, Y0 + 1) if (X + Y) % 2 == 0),
               key=lambda c: (c[0] - fx) ** 2 + (c[1] - fy) ** 2)


def _wall(st, a0, b0, a1, b1, secret=None, facing=None):
    """Wall cells centred on the line from (a0, b0) to (a1, b1), one a square; returns the cells."""
    n = int(round(max(abs(a1 - a0), abs(b1 - b0))))
    cells = []
    for k in range(n + 1):
        c = _cell(st, a0 + (a1 - a0) * k / max(1, n), b0 + (b1 - b0) * k / max(1, n))
        if c not in cells:
            cells.append(c)
    for x, y in cells:
        st.spec.wall(x, y, st.part.wall or "LOTDBrick", secret=secret, facing=facing)
    return cells


def _ang(st, da, db):
    """World angle (Nox: 0 east, pi/2 south) of the station direction (da, db)."""
    ux, uy = st.along()
    vx, vy = st.across()
    return math.atan2(da * uy + db * vy, da * ux + db * vx) % TAU


def _turn(st):
    """+1 if a positive RotateSpeed turns a beam from +a toward +b in this station, else -1."""
    d = (_ang(st, 0, 1) - _ang(st, 1, 0)) % TAU
    return 1 if abs(d - math.pi / 2) < 0.1 else -1


_ARMS = ((-1, -1), (1, -1), (-1, 1), (1, 1))


def _segments(st):
    """World segments of the wall pieces round the station (each cell drawn from its centre toward the walls it joins,
    a straight piece when it joins fewer than two; open secret walls let a beam through)."""
    cx, cy = st.at(st.L / 2, st.W / 2)
    r = (math.hypot(st.L, st.W) / 2 + 3) * SQ       # a beam that gets past these leaves the station: _record says so
    W = st.spec.wallmap
    out = []
    for (X, Y), w in W.items():
        x, y = (X + 0.5) * 23.0, (Y + 0.5) * 23.0
        if abs(x - cx) > r or abs(y - cy) > r or w.get("secret") == "open":
            continue
        arms = [d for d in _ARMS if (X + d[0], Y + d[1]) in W]
        f = w.get("facing")
        if f == 2:
            arms = list(_ARMS)
        elif len(arms) < 2:
            if f is None:
                f = 1 if arms and arms[0] in ((-1, -1), (1, 1)) else 0
            arms = [(1, -1), (-1, 1)] if f == 0 else [(-1, -1), (1, 1)]
        for dx, dy in arms:
            out.append(((x, y), (x + dx * 11.5, y + dy * 11.5)))
    return out


def _ray(x, y, ang, segs):
    """Where a beam from (x, y) at world angle `ang` stops: the first wall piece it meets, or REACH px."""
    dx, dy = math.cos(ang), math.sin(ang)
    best = REACH
    for (px, py), (qx, qy) in segs:
        ex, ey = qx - px, qy - py
        den = dx * ey - dy * ex
        if abs(den) < 1e-9:
            continue
        t = ((px - x) * ey - (py - y) * ex) / den
        s = ((px - x) * dy - (py - y) * dx) / den
        if 0.5 < t < best and -1e-6 <= s <= 1 + 1e-6:
            best = t
    return x + dx * best, y + dy * best


def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy or 1e-9
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def _record(st, name, kind, segs_, keep=1):
    """Keep a globe's traced beams (world px): every one for the checks, every `keep`th for the Meta; check none
    leaves the station."""
    for p, q in segs_:
        for x, y in (p, q):
            a, b = st.ab(x, y)
            assert 0.25 <= a <= st.L - 0.25 and -0.6 <= b <= st.W + 0.6, \
                f"{st.label}: the beam of {name} leaves the station at a={a:.2f} b={b:.2f}"
    st.__dict__.setdefault("dense", []).append((name, segs_))
    st.__dict__.setdefault("beams", []).append(
        dict(name=name, kind=kind, segs=[[[round(p[0], 1), round(p[1], 1)], [round(q[0], 1), round(q[1], 1)]]
                                         for p, q in segs_[::keep]]))


# ---- globes -------------------------------------------------------------------------------------------------------

def _globe(st, a, b, da, db, spin=0.0, kind="SentryGlobe", enabled=True):
    """A globe at (a, b) aimed along station direction (da, db), turning `spin` radians a frame (positive: in the
    station's own sense from +a toward +b)."""
    base = _ang(st, da, db)
    xfer = {"BasePosRadian": round(base, 5), "RotateSpeed": round(_turn(st) * spin, 6),
            "CurrentPosRadian": round(base, 5)}
    return st.obj(kind, a, b, enabled=enabled, xfer=xfer), base


def _fixed(st, a, side, enabled=False, marks=True):
    """A globe on the NW (side 0) or SE (side 1) wall at a, its beam straight across the hall; a switched one
    (marks) gets candelabra at its foot and a dark strip along its line."""
    b, db = (IN, 1) if side == 0 else (st.W - IN, -1)
    name, base = _globe(st, a, b, 0, db, enabled=enabled)
    x, y = st.at(a, b)
    _record(st, name, "fixed", [((x, y), _ray(x, y, base, _segments(st)))])
    if marks:
        cb = 0.35 if side == 0 else st.W - 0.35
        for da in (-0.75, 0.75):
            st.spec.obj_px("Candleabra1", *st.at(a + da, cb))
        k = int(math.floor(a))
        for j in range(st.W):
            st.spec.floor[st.part.tile(k + 0.5, j + 0.5)] = STRIP
    return name


def _sweep(st, name, a, b, base, spin, step=0.25, keep=8):
    """Record a turning globe's beams round a full turn, every `step` degrees (every `keep`th in the Meta)."""
    segs = _segments(st)
    x, y = st.at(a, b)
    n = int(round(360 / step))
    sign = 1 if spin * _turn(st) >= 0 else -1
    _record(st, name, "turning", [((x, y), _ray(x, y, base + sign * TAU * k / n, segs)) for k in range(n)], keep)


def _carried(st, name, path, da, db, step=0.1, keep=4):
    """Record a carried globe's beams along its path (station points), every `step` squares."""
    segs = _segments(st)
    ang = _ang(st, da, db)
    out = []
    for (a0, b0), (a1, b1) in zip(path, path[1:]):
        n = max(1, int(math.hypot(a1 - a0, b1 - b0) / step))
        for k in range(n + 1):
            x, y = st.at(a0 + (a1 - a0) * k / n, b0 + (b1 - b0) * k / n)
            out.append(((x, y), _ray(x, y, ang, segs)))
    _record(st, name, "carried", out, keep)


def _cue(st, clock, sound, a, b, at):
    """A sound at station point (a, b) on frames `at` of the clock's period (SentryCue, traps_sentry.go)."""
    x, y = st.at(a, b)
    st.T.starts.append(f'SentryCue("{st.label}{clock}", "{sound}", {x:.1f}, {y:.1f}, '
                       + ", ".join(str(int(t) % st.T.clocks[f"{st.label}{clock}"]["period"]) for t in at) + ")")


def _sound(st, name, a, b, delay=0):
    return st.act("sound", text=name, src=st.at(a, b), delay=delay)


def _countdown(st, a, b, start, end, step):
    """Ticks while a beam is off (from frame `start` to `end`), the last ones twice as fast, then the warning."""
    acts, t = [], start
    while t < end - 12:
        acts.append(_sound(st, "GenerateTick", a, b, delay=t))
        t += step if t < end - 3 * step else max(4, step // 2)
    acts.append(_sound(st, "DeathRayCast", a, b, delay=end - 10))
    return acts


def _meta(st, **kw):
    """The Meta, with the beams; checks every rest spot stays CLEAR of every beam."""
    beams = st.__dict__.get("beams", [])
    for a, b in st.rest:
        p = st.at(a, b)
        for name, segs_ in st.__dict__.get("dense", []):
            for s in segs_:
                d = _seg_dist(p, s[0], s[1]) / SQ
                assert d >= CLEAR, f"{st.label}: rest spot ({a}, {b}) is {d:.2f} squares from {name}"
    return Meta(beams=beams, **kw)


# ---- 01 standard: one beam on a clock ------------------------------------------------------------------------------

@pattern("sentry", size=(16, 5), title="One beam on a clock")
def one_beam(st):
    g = _fixed(st, 8.5, 0)
    st.clock("C", st.group("B", [g]), 150, [(0, 60)])
    _cue(st, "C", "DeathRayCast", 8.5, IN, [135])
    st.rest += [(5.5, 2.5), (11.5, 2.5)]
    return _meta(st, tier="standard", tells="a beam across the hall over a dark strip: on 2 s, off 3 s, a crackle "
                                            "half a second before it comes on",
                 answer="wait a square back from the strip; when the beam dies, walk across (3 s; a walk needs "
                        "under half a second to clear the line)",
                 careless="walking on at an even pace meets the beam about two times in five: death",
                 timing="period 150 frames: on 0-60, the cue at 135")


# ---- 02 standard: two beams in turn ----------------------------------------------------------------------------------

@pattern("sentry", size=(18, 5), title="Two beams in turn")
def two_beams(st):
    a = _fixed(st, 6.5, 0)
    b = _fixed(st, 11.5, 1)
    st.clock("CA", st.group("A", [a]), 160, [(0, 75)])
    st.clock("CB", st.group("B", [b]), 160, [(80, 155)])
    _cue(st, "CA", "DeathRayCast", 6.5, IN, [148])
    _cue(st, "CB", "DeathRayCast", 11.5, st.W - IN, [68])
    st.rest += [(3.5, 2.5), (9.0, 2.5), (14.5, 2.5)]
    return _meta(st, tier="standard", tells="two beams, from either wall, taking turns: as one dies the other "
                                            "comes on",
                 answer="cross the first when it dies, wait on the floor between the strips (4 squares), cross the "
                        "second when the first comes back on (2.5 s each)",
                 careless="one beam is always on: walking straight through dies about three times in four",
                 timing="period 160: A on 0-75, B on 80-155 (5 frames of both off at each change); cues 12 frames "
                        "before each")


# ---- 03 standard: the lighthouse -----------------------------------------------------------------------------------

@pattern("sentry", size=(20, 10), title="The lighthouse")
def lighthouse(st):
    # a globe in a niche in the NW wall turns once in 22 s; for 4 s a turn its beam swings out across the room, the
    # rest of the time it sweeps the niche's own walls. Stone stubs in the room to hide behind.
    _wall(st, 8.5, 0, 8.5, 2)
    _wall(st, 11.5, 0, 11.5, 2)
    _wall(st, 9.5, 4, 10.5, 4)
    _wall(st, 5.5, 7, 6.5, 7)
    _wall(st, 13.5, 7, 14.5, 7)
    lap = 660
    spin = TAU / lap
    a, b = 10.0, IN
    g, base = _globe(st, a, b, 0, 1, spin=spin)
    _sweep(st, g, a, b, base, spin)
    st.rest += [(2.5, 5.0), (10.0, 5.6), (10.0, 8.5), (5.0, 8.5), (15.0, 8.5), (17.5, 5.0), (4.0, 1.2), (16.0, 1.2)]
    out = 2 * math.atan(1.5 / (2.5 - IN))
    return _meta(st, tier="standard", tells="a globe in a niche, its beam turning slowly; once a turn it swings out "
                                            "across the room",
                 answer="watch one turn: cross while the beam sweeps the inside of its niche (~18 s of 22); caught "
                        "in the open as it swings out, step behind a stone stub (its shadow is safe) or out of the fan",
                 careless="crossing the fan at a walk without looking: about one walker in three meets the swing",
                 timing=f"a turn {lap} frames (22 s); out of the niche ~{out / spin:.0f} frames a turn; the beam "
                        "moves ~1 px a frame three squares out, ~3-4 at the far wall")


# ---- 04 standard: the walking gap ----------------------------------------------------------------------------------

@pattern("sentry", size=(22, 5), title="The walking gap")
def walking_gap(st):
    # a fence of five beams (Westwood's Con10d): all on but one, the dark one stepping down the fence every 1.2 s,
    # then all on for a step; floor between the strips to wait on
    step, n = 36, 5
    period = step * (n + 1)
    for k in range(n):
        a = 5.5 + 3 * k
        g = _fixed(st, a, 0)
        on = [(t0, t1) for t0, t1 in ((0, step * k), (step * (k + 1), period)) if t1 > t0]
        st.clock(f"C{k}", st.group(f"B{k}", [g]), period, on)
    _cue(st, "C0", "GenerateTick", 3.0, 2.5, [step * k for k in range(n + 1)])
    st.rest += [(2.5, 2.5)] + [(7.0 + 3 * k, 2.5) for k in range(n - 1)] + [(20.0, 2.5)]
    return _meta(st, tier="standard", tells="a fence of five beams; one is dark, and the dark one steps down the "
                                            "fence with every tick",
                 answer="wait before the first strip; when it goes dark, walk to the floor beyond it (3 squares, "
                        "~30 frames) and the next one goes dark as you arrive; missed one, wait for the gap to come "
                        "round again (7 s)",
                 careless="the fence is all on but one beam: death",
                 timing=f"a step every {step} frames (1.2 s, the tick); beam k dark at steps k; all on at step 5; "
                        f"cycle {period}")


# ---- 05 standard: the off switch -----------------------------------------------------------------------------------

@pattern("sentry", size=(22, 6), title="The off switch")
def off_switch(st):
    # a beam that never stops bars the hall; a lever before it switches it off for 8 s (ticking); the lever lies past
    # a beam on a clock
    c = _fixed(st, 7.5, 0)
    st.clock("C", st.group("C", [c]), 120, [(0, 60)])
    _cue(st, "C", "DeathRayCast", 7.5, IN, [105])
    g = _fixed(st, 16.5, 1, enabled=True)
    st.group("G", [g])
    off = 240
    acts = [st.act("off", "G"), _sound(st, "LeverToggle", 12.0, 0.6)] + _countdown(st, 16.5, st.W - IN, 15, off, 15) \
        + [st.act("on", "G", delay=off)]
    x, y = st.at(12.0, 0.6)
    st.T.obj("FloorLever1", x, y, name=f"{st.label}Lever")
    st.T.zone(f"{st.label}L", (x, y), 34.0, shape="circle", who="player", toggle=True, rearm=off + 30, acts=acts,
              release=acts)
    st.rest += [(4.0, 3.0), (12.0, 3.0), (19.5, 3.0)]
    return _meta(st, tier="standard", tells="a beam that never stops across the hall, a lever by the wall before "
                                            "it, a beam on a clock before the lever",
                 answer="cross the clocked beam when it dies (2 s), pull the lever: the far beam is off for 8 s "
                        "(ticks, faster at the end, a crackle before it returns); walk through",
                 careless="without the lever the far beam is death; the clocked beam kills one walker in two",
                 timing=f"clocked beam period 120 (on 0-60); the lever's beam off {off} frames, the lever re-arms "
                        f"{off + 30} frames after you step away")


# ---- 06 hard: crossing beams ---------------------------------------------------------------------------------------

@pattern("sentry", size=(22, 7), tier="hard", title="Crossing beams")
def crossing(st):
    # two sets of three beams cross the room diagonally (one set from each wall) and cut it into diamonds; the sets
    # take turns: both on, then one off, both on, the other off. Move one diamond on each time a set goes dark.
    A, B = [], []
    for a in (4.5, 8.5, 12.5):
        g, base = _globe(st, a, IN, 1, 1, enabled=False)
        x, y = st.at(a, IN)
        _record(st, g, "fixed", [((x, y), _ray(x, y, base, _segments(st)))])
        A.append(g)
        g, base = _globe(st, a, st.W - IN, 1, -1, enabled=False)
        x, y = st.at(a, st.W - IN)
        _record(st, g, "fixed", [((x, y), _ray(x, y, base, _segments(st)))])
        B.append(g)
        for da in (-0.75, 0.75):
            st.spec.obj_px("Candleabra1", *st.at(a + da, 0.35))
            st.spec.obj_px("Candleabra1", *st.at(a + da, st.W - 0.35))
    period = 72
    st.clock("CA", st.group("A", A), period, [(0, 54)])
    st.clock("CB", st.group("B", B), period, [(0, 18), (36, 72)])
    _cue(st, "CA", "DeathRayCast", 8.5, IN, [62])
    _cue(st, "CB", "DeathRayCast", 8.5, st.W - IN, [26])
    st.rest += [(2.5, 3.5), (9.75, 3.5), (11.75, 1.5), (11.75, 5.5), (13.75, 3.5), (20.5, 3.5)]
    return _meta(st, tier="hard", tells="six beams criss-crossing the room from both walls; the NW set and the SE set "
                                        "go dark in turn",
                 answer="stand in the middle of a diamond (1.4 squares from its sides); when the set on one side of "
                        "you goes dark (0.6 s), step across that line into the next diamond; three or four moves",
                 careless="death: a walker meets a lit line within a second",
                 timing=f"period {period}: both on 0-18, NW only 18-36 (SE dark), both 36-54, SE only 54-72 (NW "
                        "dark); a line crossing (1 square) takes ~10 frames at a walk; cues 10 frames before each set "
                        "comes on")


# ---- 07 hard: the gliding beam -------------------------------------------------------------------------------------

@pattern("sentry", size=(24, 7), tier="hard", title="The gliding beam")
def gliding(st):
    # Westwood's "lift the key, flee the beam" (G_LOTD): a beam on a rail bars the end of the hall; take the gold
    # before it and the way back slams shut, and a second later the beam glides down the whole hall at more than a
    # running pace. Only the shadows behind three stone stubs are safe.
    for a0 in (4.5, 9.5, 14.5):
        _wall(st, a0, 2, a0 + 1, 2)
    mouth = _wall(st, -0.5, 1, -0.5, st.W - 1, secret="open")
    park, stop = (21.5, IN), (0.4, IN)
    g, base = _globe(st, *park, 0, 1, kind="SentryGlobeMovable")
    st.group("G", [g])
    speed, wait = 9.0, 20
    st.T.mover(f"{st.label}M", [g], [st.at(*park), st.at(*stop)], speed, mode="once", armed=False)
    _carried(st, g, [park, stop], 0, 1)
    arrive = wait + int(math.ceil((park[0] - stop[0]) * SQ / speed))
    ga, gb = 19.5, 4.5
    gold = st.T.obj("Gold", *st.at(ga, gb), name=st.nm("Gold"), xfer={"Amount": 150})
    st.T.watch(f"{st.label}W", gold, acts=[
        st.act("walls_close", walls=mouth, delay=3), _sound(st, "BigGong", ga, gb),
        _sound(st, "SpikeBlockMove", *park, delay=wait - 6), st.act("arm", "M", delay=wait),
        st.act("off", "G", delay=arrive + 2), st.act("walls_open", walls=mouth, delay=arrive + 5)])
    st.rest += [(5.0, 3.6), (10.0, 3.6), (15.0, 3.6)]
    # the race to the nearest shadow (a <= 15.6 behind the stub at a 14 .. 16): the beam (behind you) closes at
    # speed - your pace; caught when it reaches your back (0.35 squares)
    v = speed / SQ
    walk_t = (ga - 15.6) / (3.3 / SQ)
    run_t = (ga - 15.6) / (6.9 / SQ)
    caught = lambda pace: (park[0] - ga - 0.35 + v * wait) / (v - pace / SQ)
    return _meta(st, tier="hard", tells="a beam across the far end of the hall, gold before it, three short stone "
                                        "walls along the NW side",
                 answer="before taking the gold, look at the nearest stub; take it and run straight back along the "
                        "SE side into the stub's shadow (the side away from the NW wall): the way out slams, and "
                        "two thirds of a second later the beam glides the length of the hall faster than a run and "
                        "stops at the door",
                 careless="taking the gold and making for the door: it is shut and the beam arrives: death",
                 timing=f"the beam starts {wait} frames after the gold is lifted, {speed} px a frame (a run is 6.9); "
                        f"from the gold to the shadow ({ga - 15.6:.1f} squares) a walk takes {walk_t:.0f} frames and "
                        f"is caught at {caught(3.3):.0f}, a run takes {run_t:.0f}")


# ---- 08 hard: run the gates ----------------------------------------------------------------------------------------

GATE_OFF = (6, 51)            # frames after a plate: its gate dark (1.5 s), ticking, a crackle 10 frames before it returns
GATE_LAG = 35                 # frames between one gate's window and the next's in a plate's wave (a run's pace: 7 squares)


def _plate(st, s, a, b, acts, rearm=60):
    """A pressure plate the player steps on (a jump passes over it): `acts` every time, as T.plate, but written as a
    switch zone (the same acts on each press) so the simulator's planner tries pressing it."""
    x, y = st.at(a, b)
    st.T.obj("PressurePlate", x, y, name=f"{st.label}Plate{s}",
             xfer={"SizeX": 45, "SizeY": 45, "EdgeColor": [90, 90, 90], "BackColor": [10, 10, 10], "UnkInt1": 0,
                   "ScriptOnPressed": "", "ScriptOnReleased": "", "ScriptOnCollided": "", "AllowedObjClass": 4,
                   "IgnoredObjClass": 0, "AllowedTeamID": 0, "IgnoredTeamID": 0, "TriggerState": 0, "Unk7": 0,
                   "UnkInt2": 0})
    st.T.zone(f"{st.label}{s}", (x, y), 90 * 0.35355 + st.T.PLATE_PAD, shape="diamond", who="player", jump=True,
              toggle=True, rearm=rearm, acts=acts, release=acts)


def _gate_wave(st, gates, plates):
    """A plate before each gate (group G<k>); a plate darkens its gate and every gate after it in turn, GATE_LAG frames
    apart (a run takes them all in one go; a walker stops in a pocket and uses the next plate); while a wave runs every
    plate sleeps (one wave at a time)."""
    for k, (pa, pb) in enumerate(plates):
        acts = []
        for j in range(k, len(gates)):
            a, gb = gates[j]
            t0, t1 = GATE_OFF[0] + (j - k) * GATE_LAG, GATE_OFF[1] + (j - k) * GATE_LAG
            acts += [st.act("off", f"G{j}", delay=t0), st.act("on", f"G{j}", delay=t1)]
            acts += [_sound(st, "GenerateTick", a, gb, delay=d) for d in range(t0, t1 - 12, 9)]
            acts.append(_sound(st, "DeathRayCast", a, gb, delay=t1 - 10))
        end = GATE_OFF[1] + (len(gates) - 1 - k) * GATE_LAG
        acts += [st.act("disarm", f"P{j}") for j in range(len(plates))]
        acts += [st.act("arm", f"P{j}", delay=end) for j in range(len(plates))]
        _plate(st, f"P{k}", pa, pb, acts)


@pattern("sentry", size=(26, 6), tier="hard", title="Run the gates")
def run_the_gates(st):
    # three beams that never stop, a pressure plate five squares before each; a plate darkens the gates ahead of it
    # one after another at a running pace, each for 1.5 s (ticking): run from the first plate and all three are dark
    # as you reach them; a walker is too slow for any; stop in a pocket and its own plate starts the wave again
    gates = []
    for k, (a, side) in enumerate(((8.5, 0), (15.5, 1), (22.5, 0))):
        g = _fixed(st, a, side, enabled=True)
        st.group(f"G{k}", [g])
        gates.append((a, IN if side == 0 else st.W - IN))
    _gate_wave(st, gates, [(3.5, 2.0), (10.5, 4.0), (17.5, 2.0)])
    st.T.obj("Gold", *st.at(24.5, 3.0), name=st.nm("Gold"), xfer={"Amount": 200})
    st.rest += [(2.0, 4.5), (12.5, 2.0), (19.5, 4.0), (25.0, 4.8)]
    return _meta(st, tier="hard", tells="three beams that never stop, a pressure plate five squares before each, gold "
                                        "beyond the last",
                 answer="step on the first plate and run without stopping: the gates go dark one after another as "
                        "you reach them (each 1.5 s, ticking, a crackle before it returns); lose the pace and stop in "
                        "the pocket before the next gate, then use its plate",
                 careless="walking from a plate: you reach the gate as it comes back: death",
                 timing=f"from a plate, gate j dark {GATE_OFF[0]}-{GATE_OFF[1]} frames + {GATE_LAG} per gate after "
                        "it; a run reaches the gates at ~24, ~57, ~90 frames, a walk at ~49 (the line is lit again "
                        "at 51); plates sleep while a wave runs")


# ---- 09 hard: the courtyard ----------------------------------------------------------------------------------------

@pattern("sentry", size=(22, 12), tier="hard", title="The courtyard")
def courtyard(st):
    # a walled courtyard with four beams turning about its middle like the hands of a clock (one turn in 20 s, a beam
    # past any spot every 5 s); you come in at one corner and leave at the far one. Porches behind short walls at
    # both doors, and two stone stubs, are always in shadow.
    _wall(st, 3.5, 2, 3.5, st.W)            # the near wall, a door at b 0 .. 1.5
    _wall(st, 16.5, 0, 16.5, st.W - 2)      # the far wall, a door at b 10.5 .. 12
    _wall(st, 4.5, 3, 7.5, 3)               # the near porch's screen
    _wall(st, 12.5, st.W - 3, 15.5, st.W - 3)  # the far porch's screen
    _wall(st, 6.5, 6, 6.5, 8)               # stubs to hide behind
    _wall(st, 13.5, 4, 13.5, 6)
    lap = 600
    spin = TAU / lap
    ca, cb = 10.0, 6.0
    for k, (da, db) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
        g, base = _globe(st, ca, cb, da, db, spin=spin)
        _sweep(st, g, ca, cb, base, spin)
    st.rest += [(1.5, 6.0), (5.2, 1.5), (5.0, 7.0), (15.0, 5.0), (14.5, 10.6), (19.5, 6.0)]
    return _meta(st, tier="hard", tells="a courtyard with four beams turning slowly about its middle, a door at "
                                        "each far corner, short walls to stand behind",
                 answer="from the near porch, watch a beam pass and follow it round, staying in the quarter behind "
                        "it (the beams move ~1.5 px a frame five squares out); rest in a stub's shadow (the side away "
                        "from the middle); reach the far porch; keep away from the middle, where all four meet",
                 careless="walking across the middle: death",
                 timing=f"a turn {lap} frames (20 s); a beam past any spot every {lap // 4} frames; crossings between "
                        "shadows of 5-8 squares (50-80 frames at a walk)")


# ---- 10 hard: the long run -----------------------------------------------------------------------------------------

@pattern("sentry", size=(44, 7), tier="hard", title="The long run")
def long_run(st):
    # 1. a fence of four beams with a walking gap
    step, n = 36, 4
    period = step * (n + 1)
    for k in range(n):
        g = _fixed(st, 5.5 + 3 * k, 0)
        on = [(t0, t1) for t0, t1 in ((0, step * k), (step * (k + 1), period)) if t1 > t0]
        st.clock(f"F{k}", st.group(f"FB{k}", [g]), period, on)
    _cue(st, "F0", "GenerateTick", 3.0, 3.5, [step * k for k in range(n + 1)])
    # 2. a gate that never stops, its plate five squares before it
    gate = _fixed(st, 21.5, 1, enabled=True)
    st.group("G0", [gate])
    _gate_wave(st, [(21.5, st.W - IN)], [(16.5, 3.5)])
    # 3. a beam on a rail sweeping up and down the last stretch; stone stubs to shelter behind
    for a0 in (27.5, 31.5, 35.5):
        _wall(st, a0, 2, a0 + 1, 2)
    rail = [(26.0, IN), (40.0, IN)]
    g, base = _globe(st, *rail[0], 0, 1, kind="SentryGlobeMovable")
    st.T.mover(f"{st.label}M", [g], [st.at(*p) for p in rail], 5.0, mode="pingpong", pause=20)
    _carried(st, g, rail, 0, 1)
    st.rest += [(2.5, 3.5)] + [(7.0 + 3 * k, 3.5) for k in range(n - 1)] + [(18.5, 5.5), (23.8, 3.5),
                                                                          (28.0, 3.6), (32.0, 3.6), (36.0, 3.6),
                                                                          (42.0, 3.5)]
    return _meta(st, tier="hard", tells="a fence with a walking gap, a gate with its plate, a beam sliding up and down "
                                        "the far stretch past three stone stubs",
                 answer="walk the gap through the fence; plate and run the gate; shelter behind each stub as the "
                        "sliding beam passes (it turns at each end after 0.7 s), move on as it goes away",
                 careless="death at the first fence",
                 timing="fence: a step every 36 frames, cycle 180; gate: dark 6-51 frames after the plate, 5 squares: "
                        "a run (25 frames), not a walk (54); rail: 5 px a frame over 14 squares, 20 frames at each "
                        "end (period 222); shadows 4 squares apart (40 frames at a walk)")
