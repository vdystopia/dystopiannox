"""Blades: RotatingSpikes (r 12, 4 HP a frame, armour-reduced) moved by the script (kit/traps.py T.mover: SetPos every
frame along a path). A blade shoves whoever it touches (measured: ~81 units at once), so a clean touch costs a frame
or two (~8 HP to an unarmoured wizard); the harm comes from being shoved into the next blade, ground against a wall
or between two blades (4 HP a frame for as long as it lasts), or knocked into a pit. Blades are NOT jumpable and are
never switched off (ObjectOff hides one but it may keep cutting): they move away.

Numbers (rules/TRAPS.md 1): walk ~3.3 px a frame (a square, 32.5 px, in ~10 frames), run ~6.9 (~5 frames). A blade
touches a player whose centre is within 22 px (0.68 squares) of its centre, so a blade's lane is a band 1.36 squares
deep; blades 1 square apart (or less) leave no gap a player (20 px across) can slip through.

The station frame: a along the run (0 at the way in), b across (0 .. W), in squares; b = 0 is the NW wall (the back
wall in the lab). Walls a pattern adds stand on square corners (integer a, b).
"""
import copy, math
from kit.trapkit import pattern, Meta, frames, SQ, Station

REACH = 22.0 / SQ                  # squares: blade (r 12) + player (r 10)


# ---- the station's real frame ---------------------------------------------------------------------------------------
# Part.at's box is the squares' box, but walls stand on Nox's wall lattice: in a part along j (the lab's stations) its
# side walls are at b = 0 and W and the walls across it at half-integer a; in a part along i (a gauntlet's) the side
# walls stand at b = -0.5 and W - 0.5 and walls across at whole a. Each pattern here works in a frame moved onto the
# real walls (measured from the map's walls, so it is (0, 0) in the lab and wherever the kit already agrees).

def _offset(st):
    """(da, db): how far this station's real walls sit from the lab frame's."""
    best = None
    x0, y0 = Station.at(st, st.L / 2, 0)
    for (X, Y) in st.spec.wallmap:
        x, y = (X + 0.5) * 23.0, (Y + 0.5) * 23.0
        if abs(x - x0) > 60 or abs(y - y0) > 60:
            continue
        a, b = Station.ab(st, x, y)
        if abs(b) <= 0.75 and (best is None or abs(b) < abs(best[1])):
            best = (a, b)
    if best is None:
        return 0.0, 0.0
    db = round(best[1] * 2) / 2
    frac = (best[0] - 0.5) % 1.0
    da = 0.0 if min(frac, 1 - frac) < 0.25 else -0.5
    return da, db


def _framed(st):
    da, db = _offset(st)
    if not da and not db:
        return st
    f = copy.copy(st)                     # shares rest, starts and the trap data; its own name counter
    f.at = lambda a, b: Station.at(st, a + da, b + db)
    f.ab = lambda x, y: tuple(v - o for v, o in zip(Station.ab(st, x, y), (da, db)))
    return f


def _pattern(kind, **kw):
    """kit.trapkit.pattern, the pattern run in the station's real frame (_framed)."""
    def deco(fn):
        def run(st):
            return fn(_framed(st))
        run.__name__, run.__doc__ = fn.__name__, fn.__doc__
        return pattern(kind, **kw)(run)
    return deco


# ---- helpers ------------------------------------------------------------------------------------------------------

def _blade(st, a, b):
    return st.obj("RotatingSpikes", a, b)


def _move(st, s, objs, pts, speed, mode="pingpong", pause=0, armed=True):
    """A mover through station points `pts` (squares); its first object must stand at pts[0]."""
    return st.T.mover(f"{st.label}{s}", objs, [st.at(a, b) for a, b in pts], speed, mode=mode, pause=pause,
                      armed=armed)


def _cell(st, a, b):
    """The wall cell whose centre is nearest station point (a, b). A cell (X, Y) (X + Y even) is centred at world
    ((X + .5) * 23, (Y + .5) * 23); in a lab station (along j) the centres fall at half-integer a and integer b: a wall
    along a lies on the squares' edges, a wall across (along b) runs through the middle of a row of squares."""
    x, y = st.at(a, b)
    fx, fy = x / 23.0 - 0.5, y / 23.0 - 0.5
    X0, Y0 = math.floor(fx), math.floor(fy)
    return min(((X, Y) for X in (X0, X0 + 1) for Y in (Y0, Y0 + 1) if (X + Y) % 2 == 0),
               key=lambda c: (c[0] - fx) ** 2 + (c[1] - fy) ** 2)


def _wall(st, a0, b0, a1, b1, breakable=False, material=None, facing=None):
    """Wall cells centred on the line from (a0, b0) to (a1, b1), one a square (in the lab: a = k + 0.5 along the
    run, b = whole squares across); each covers half a square either side of its centre. Returns its cells."""
    n = int(round(max(abs(a1 - a0), abs(b1 - b0))))
    cells = []
    for k in range(n + 1):
        c = _cell(st, a0 + (a1 - a0) * k / max(1, n), b0 + (b1 - b0) * k / max(1, n))
        if c not in cells:
            cells.append(c)
    for x, y in cells:
        st.spec.wall(x, y, material or st.part.wall or "DungeonStone", breakable=breakable, facing=facing)
    return cells


def _pit(st, a, b):
    """An open pit on the square whose centre is (a, b) (a Pit's diamond covers exactly one square); the lab sets
    FallX/FallY to its pit room. A named trap object, so the simulator sees it."""
    st.obj("Pit", a, b, xfer={"UnknownScriptHandler": "", "FallX": 0, "FallY": 0, "ScriptTime1": 0,
                              "ScriptTimeout": 0, "ScriptActivated": 0})


def _ring(ca, cb, r, n, start, sign=1):
    """A regular n-gon round (ca, cb), radius r squares, starting at angle `start` (station frame)."""
    return [(ca + r * math.cos(start + sign * 2 * math.pi * k / n), cb + r * math.sin(start + sign * 2 * math.pi * k / n))
            for k in range(n)]


def _perimeter(pts):
    return sum(math.dist(pts[k], pts[(k + 1) % len(pts)]) for k in range(len(pts))) * SQ


def _loop_from(pts, d):
    """The closed loop `pts` rotated to start `d` squares along it (a later start on the same track)."""
    n = len(pts)
    lens = [math.dist(pts[k], pts[(k + 1) % n]) for k in range(n)]
    d %= sum(lens)
    for k in range(n):
        if d < lens[k] - 1e-9:
            p, q = pts[k], pts[(k + 1) % n]
            t = d / lens[k]
            start = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
            out = [start] + [pts[(k + 1 + i) % n] for i in range(n)]
            if math.dist(out[-1], start) < 1e-9:
                out.pop()
            return out
        d -= lens[k]
    return list(pts)


def _orbit(st, s, ca, cb, radii, angles, lap, sign=1, n=40):
    """Blades orbiting (ca, cb): a blade at each radius on each spoke angle, every one on its own ring with a speed
    in proportion to its radius, so each spoke stays straight as it turns (a mover only translates); `lap` frames a
    turn."""
    for j, th in enumerate(angles):
        for i, r in enumerate(radii):
            pts = _ring(ca, cb, r, n, th, sign)
            _move(st, f"{s}{j}_{i}", [_blade(st, *pts[0])], pts, _perimeter(pts) / lap, mode="loop")


def _sound(st, name, a, b, delay=0):
    return st.act("sound", text=name, src=st.at(a, b), delay=delay)


def _shuttle(p0, p1, speed, dwell, e=0.15):
    """A closed loop p0 -> p1 -> p0 (station squares) that holds still `dwell` frames at each end: the blade shivers
    e squares back and forth there (a loop mover only pauses at its lap start). A loop, so a later start along it
    (_loop_from) is a later phase: blades on the same track keep a fixed stagger from the map's first frame."""
    def zig(p, q):
        n = max(1, int(math.ceil(dwell * speed / (2 * e * SQ))))
        d = math.dist(p, q)
        back = (p[0] + (q[0] - p[0]) * e / d, p[1] + (q[1] - p[1]) * e / d)
        return [back, p] * n
    return [p0, p1] + zig(p1, p0) + zig(p0, p1)[:-1]


def _phase(path, frames, speed):
    """The loop `path` started `frames` frames later in its cycle."""
    return _loop_from(path, frames * speed / SQ)


# ---- 01 standard: round the pillars -----------------------------------------------------------------------------

@_pattern("blade", size=(20, 8), title="Round the pillars")
def round_the_pillars(st):
    # two stone blocks make three corridors 2 squares wide; blade pairs circle each block, up an outer corridor,
    # across the far end, down the shared middle corridor, across the near end: the outer corridors carry the blades
    # away from you, the middle one brings them at you
    for b0 in (2, 5):
        _wall(st, 6.5, b0, 13.5, b0)                             # a block: a 6.5 .. 13.5, b b0 .. b0 + 1
        _wall(st, 6.5, b0 + 1, 13.5, b0 + 1)
        _wall(st, 6.5, b0, 6.5, b0 + 1)
        _wall(st, 13.5, b0, 13.5, b0 + 1)
    near, far, mid = 5.5, 14.5, 3.5
    tracks = [[(near, 0.5), (far, 0.5), (far, mid), (near, mid)],     # round the NW block (pairs ride +1 across)
              [(near, 6.5), (far, 6.5), (far, mid), (near, mid)]]     # round the SE block
    lap = _perimeter(tracks[0])                                       # 780 px
    speed = 4.0
    for t, track in enumerate(tracks):
        for k in range(2):
            path = _loop_from(track, (k * lap / 2 + t * lap / 4) / SQ)
            a, b = path[0]
            _move(st, f"P{t}{k}", [_blade(st, a, b), _blade(st, a, b + 1)], path, speed, mode="loop")
    st.rest += [(2.5, 4.0), (17.5, 4.0)]
    f_lap = lap / speed
    return Meta(tier="standard", tells="two stone blocks, three corridors: blade pairs go up the outer two and come "
                                       "back down the middle one",
                answer="go up an outer corridor right behind a pair as it turns into it and walk on without stopping: "
                       "it pulls away from you (4 px a frame) and the next is half a lap behind; step out at the far "
                       "end once the pair ahead has turned across; never take the middle",
                careless="walking up the middle meets a pair head-on every 1.6 s: shoved back touch after touch, "
                         "~30-50 HP",
                timing=f"lap {f_lap:.0f} frames ({f_lap / 30:.1f} s), two pairs a block half a lap apart, the blocks "
                       "a quarter lap out of step; an outer corridor takes ~90 frames at a walk, the next pair "
                       "reaches its mouth ~98 frames after the one you follow")


# ---- 02 standard: the jaws ----------------------------------------------------------------------------------------

@_pattern("blade", size=(22, 6), title="The jaws")
def jaws(st):
    # three lanes of jaws: two blades from the side walls close to the middle and open again; lanes alternate, so as
    # one shuts the next opens. Open: the middle is free; shut: the sides are free.
    W = st.W
    lo, hi = 0.45, W - 0.45
    sl, sr = W / 2 - 0.45, W / 2 + 0.45
    speed, pause = 4.0, 30
    for k, a in enumerate((7, 11, 15)):
        left, right = [(a, lo), (a, sl)], [(a, hi), (a, sr)]
        if k % 2:
            left, right = left[::-1], right[::-1]
        _move(st, f"L{k}", [_blade(st, *left[0])], left, speed, pause=pause)
        _move(st, f"R{k}", [_blade(st, *right[0])], right, speed, pause=pause)
    st.rest += [(9.0, W / 2), (13.0, W / 2)]
    stroke = (sl - lo) * SQ / speed
    period = 2 * (stroke + pause)
    return Meta(tier="standard", tells="three rows of blade jaws snapping shut and open, each row out of step with "
                                       "the next",
                answer="cross a row in the middle while its jaws stand open, or along a wall while they are shut "
                       "(each lasts 1 s; a walk crosses a row in ~14 frames); wait between rows",
                careless="walking down the middle: about one row in two closes on you and grinds you between two "
                         "blades, ~30-45 HP",
                timing=f"period {period:.0f} frames: open {pause} + closing {stroke:.0f} + shut {pause} + opening; "
                       "middle free ~60 frames a period, the wall side ~44")


# ---- 03 standard: the orbit ---------------------------------------------------------------------------------------

@_pattern("blade", size=(18, 8), title="The orbit")
def orbit(st):
    # four bars of three blades turn round a stone pillar like the spokes of a wheel; inside them a calm ring (the
    # eye) round the pillar; the bars reach the side walls, so there is no way round
    ca, cb = 9.5, st.W / 2                                       # a wall cell's centre (half-integer a)
    _wall(st, ca, cb, ca, cb, facing=2)                          # a cross-shaped stone pillar
    lap = 280
    radii = (2.2, 3.0, 3.8)
    _orbit(st, "O", ca, cb, radii, [k * math.pi / 2 for k in range(4)], lap)
    st.rest += [(2.5, cb), (ca, cb - 1.1), (15.5, cb)]
    gap = lap / 4
    block = (2 * REACH * SQ) / (2 * math.pi * radii[1] * SQ / lap)
    return Meta(tier="standard", tells="four spokes of blades sweep round a pillar; a calm ring round the pillar "
                                       "inside them",
                answer="step in right behind a passing spoke and walk (or curve with it) into the calm ring, rest, "
                       "then out the far side the same way",
                careless="walking straight through: a spoke catches you on the way in or out and drags you round, "
                         "~25-35 HP",
                timing=f"a turn {lap} frames; a spoke passes every {gap:.0f} frames and blocks a spot for "
                       f"~{block:.0f}; crossing the 3-square band takes ~29 frames at a walk")


# ---- 04 standard: the revolving door ------------------------------------------------------------------------------

@_pattern("blade", size=(20, 7), title="The revolving door")
def revolving_door(st):
    # a cross of four blade arms turning about a blade hub in the middle of the hall, its arms long enough to scrape
    # both side walls: a revolving door. Ride a quarter round from the near side to the far side.
    ca, cb = 10.0, st.W / 2
    _blade(st, ca, cb)                                            # the hub: a blade that never moves
    lap = 360
    radii = (0.7, 1.4, 2.1, 2.8, 3.5, 4.2)
    _orbit(st, "D", ca, cb, radii, [k * math.pi / 2 for k in range(4)], lap)
    st.rest += [(4.0, cb), (16.0, cb)]
    return Meta(tier="standard", tells="four arms of blades turning slowly about a hub, wall to wall: a revolving door",
                answer="step into the quarter that opens toward you just behind an arm, walk round with it (an arm "
                       "moves ~1 px a frame two squares out) and step out when the quarter opens to the far side",
                careless="walking into the door: an arm sweeps you round and its tip grinds you along the side wall, "
                         "~20-40 HP",
                timing=f"a turn {lap} frames (12 s); a quarter needs ~180 frames to carry you across; the wall "
                       "strips are scraped for ~80 of every 90 degrees, so there is no way round")


# ---- 05 standard: the saw -----------------------------------------------------------------------------------------

@_pattern("blade", size=(24, 6), title="The saw")
def saw(st):
    # a lane 4 squares wide, blocked by three breakable walls; bays 2 deep along its SE side between stone stubs. A
    # lever releases the saw (three blades across the lane): it grinds up the lane, bursting each wall as it reaches
    # it, then patrols the lane for good.
    lane = 4
    a0, a1 = 4.0, 21.0
    speed, pause = 3.0, 45
    bars = (9.5, 14.5, 19.5)                                        # walls across run through square middles
    walls = {}
    for a in bars:
        _wall(st, a, lane, a, st.W)                                 # the stub (bay divider), b 3.5 .. 6
        walls[a] = _wall(st, a, 1, a, lane - 1, breakable=True)     # the breakable barrier, b 0.5 .. 3.5
    bs = (0.7, 2.0, 3.3)
    saw_ = [_blade(st, a0, b) for b in bs]
    _move(st, "S", saw_, [(a0, bs[0]), (a1, bs[0])], speed, pause=pause, armed=False)
    acts = [st.act("arm", "S"), _sound(st, "BigGong", 2.0, 0.6), _sound(st, "SpikeBlockMove", a0, 2.0)]
    for a in bars:
        t = (a - 0.6 - a0) * SQ / speed
        acts.append(st.act("blade_break", walls=walls[a], text="WallDestroyedStone", src=st.at(a, 2.0),
                           delay=int(round(t))))
    st.lever("L", "FloorLever1", 2.0, 0.6, acts=acts, once=True)
    st.rest += [(1.5, 3.0), (12.0, 5.2), (17.0, 5.2), (22.5, 5.0)]
    return Meta(tier="standard", tells="a lane walled off three times, a saw of blades parked at its mouth, a lever "
                                       "by the wall, bays along the side",
                answer="pull the lever and follow the saw a few squares back as it bursts each wall; when it turns "
                       "back at the end, step into a bay (beyond the lane's edge) and let it pass, then walk on",
                careless="standing in the lane when it comes back: shoved back down the lane touch after touch, "
                         "~30-40 HP",
                timing=f"the saw {speed} px a frame (a walk is faster: keep back); walls burst at ~54, ~108 and "
                       f"~162 frames; it pauses {pause} frames at each end of its {a1 - a0:.0f}-square stroke")


# ---- 06 hard: the sliding doors ----------------------------------------------------------------------------------

@_pattern("blade", size=(22, 6), tier="hard", title="The sliding doors")
def sliding_doors(st):
    # six walls of blades across the hall, 1.5 squares apart (nowhere to stand between them), each with a door two
    # blades wide; the doors line up and slide together from one side wall to the other and back, pausing at each:
    # a corridor through the blades that will not keep still
    W = st.W
    lo, hi = 1.5, W - 1.5                                      # the door's middle, at each end of its slide
    speed, pause = 2.5, 30
    offs = [d for k in range(1, W) for d in (-(k + 0.5), k + 0.5)]   # blades either side of the door, into the walls
    for k in range(6):
        a = 6.0 + 1.5 * k
        objs = [_blade(st, a, lo + d) for d in offs]
        _move(st, f"D{k}", objs, [(a, lo + offs[0]), (a, hi + offs[0])], speed, pause=pause)
    st.rest += [(2.5, W / 2), (17.5, W / 2)]
    slide = (hi - lo) * SQ / speed
    return Meta(tier="hard", tells="six walls of blades across the hall, a door in each; the doors line up and slide "
                                   "from wall to wall together",
                answer="step into the doors' corridor while it waits by a wall and walk in along it; when it slides, "
                       "slide with it (2.5 px a frame, nearly a walk: no time to go forward too); go forward again at "
                       "the next pause; about two pauses take you through",
                careless="walking straight through: a sliding wall of blades catches you and grinds you against the "
                         "side wall, ~60-100 HP or worse",
                timing=f"the doors slide {slide:.0f} frames, wait {pause} at each wall (period "
                       f"{2 * (slide + pause):.0f}); the door's middle +-0.8 square is safe; 6 walls over 8 squares")


def _pendulums(st, s, lanes, speed, dwell, lag):
    """Blades swinging wall to wall, one lane each at the given a, each `lag` frames behind the one before (a wave
    rolling down the hall at 1.5 squares per lag); loops from the map's first frame."""
    W = st.W
    loop = _shuttle((0.0, 0.45), (0.0, W - 0.45), speed, dwell)
    for k, a in enumerate(lanes):
        path = [(a, b) for _, b in _phase(loop, -lag * k, speed)]
        _move(st, f"{s}{k}", [_blade(st, *path[0])], path, speed, mode="loop")


# ---- 07 hard: find the gap ----------------------------------------------------------------------------------------

@_pattern("blade", size=(22, 7), tier="hard", title="Find the gap")
def find_the_gap(st):
    # two walls of blades plough up and down the hall in counter-step (they pass through each other mid-hall), each
    # with a two-blade gap by a different wall: stand in a wall's gap and it passes over you
    W = st.W
    a0, a1 = 4.0, 18.0
    speed, pause = 4.5, 15
    _ploughs(st, a0, a1, speed, pause, {"A": (0.5, 1.5), "B": (W - 1.5, W - 0.5)})
    st.rest += [(2.0, W / 2), (20.0, W / 2)]
    period = 2 * ((a1 - a0) * SQ / speed + pause)
    mid = (a0 + a1) / 2
    return Meta(tier="hard", tells="two rows of blades sweeping up and down the hall in turn, one missing two blades "
                                   "by the NW wall, the other by the SE wall",
                answer="stand in a row's gap (its middle +-0.8 square) as it passes over you; cross the hall to the "
                       "other row's gap before that one comes (4.5 squares, ~45 frames), and make the crossings near "
                       f"the ends of the hall: the rows meet in the middle (a {mid:.0f}), where no gap is safe",
                careless="walking up the middle: both rows bulldoze you along the hall, ~40-80 HP",
                timing=f"each row {speed} px a frame over {a1 - a0:.0f} squares, {pause} frames at each end (period "
                       f"{period:.0f}), the two half a period apart; at a spot d squares from the middle the rows "
                       f"pass ~{2 * SQ / speed:.0f}*d frames apart (a 6 or 16: ~58)")


def _ploughs(st, a0, a1, speed, pause, gaps):
    """Rows of blades across the hall (one a square) shuttling between a0 and a1, each missing the blades at its gap;
    the first starts at a0, the second at a1 (counter-step)."""
    full = [0.5 + k for k in range(st.W)]
    for k, (s, gap) in enumerate(gaps.items()):
        bs = [b for b in full if b not in gap]
        ends = [a0, a1] if k % 2 == 0 else [a1, a0]
        objs = [_blade(st, ends[0], b) for b in bs]
        _move(st, s, objs, [(a, bs[0]) for a in ends], speed, pause=pause)


# ---- 08 hard: the ledge -------------------------------------------------------------------------------------------

@_pattern("blade", size=(22, 5), tier="hard", title="The ledge")
def ledge(st):
    # a ledge 1 square wide along the NW wall over a pit 4 squares across; blades punch out of the wall across the
    # ledge and back, in turn (two in step, two out of step): one in the wrong place and you go over the edge
    W = st.W
    p0, p1 = 5, 19
    for a in range(p0, p1):
        for b in range(1, W):
            _pit(st, a + 0.5, b + 0.5)
    speed, pause = 7.0, 18
    inn, out = -0.75, 0.55
    for k, a in enumerate((7, 10, 13, 16)):
        path = [(a, inn), (a, out)] if k % 2 == 0 else [(a, out), (a, inn)]
        _move(st, f"K{k}", [_blade(st, *path[0])], path, speed, pause=pause)
    st.rest += [(2.5, 2.5), (8.5, 0.5), (11.5, 0.5), (14.5, 0.5), (20.5, 2.5)]
    stroke = (out - inn) * SQ / speed
    period = 2 * (stroke + pause)
    return Meta(tier="hard", tells="a narrow ledge along the wall above a pit; blades stab out of the wall across it "
                                   "and back, two in step and two out of step",
                answer="wait on the ledge between two blades (1.6 squares of room), cross each blade's line the "
                       "moment it pulls back into the wall: ~23 frames, a walk needs ~14, a run ~7",
                careless="walking the ledge at an even pace: about four blades in five catch you and knock you into "
                         "the pit",
                timing=f"period {period:.0f} frames: out {stroke:.0f}, held {pause}, back {stroke:.0f}, in {pause}; "
                       "the next blade is always half a period off")


# ---- 09 hard: the zipper ------------------------------------------------------------------------------------------

@_pattern("blade", size=(24, 4), tier="hard", title="The zipper")
def zipper(st):
    # a lane 2 squares wide with alcoves 2 deep along its SE side; trains of blade pairs burst from the far wall,
    # rush down the lane faster than a run and vanish into the wall at the near end (they go back up inside it)
    lane = 2
    for a in (3.5, 6.5, 9.5, 12.5, 15.5, 18.5, 21.5):              # stubs b 2.5 .. 4 (walls across: k + 0.5)
        _wall(st, a, lane + 1, a, st.W)
    track = [(21, 0.5), (3, 0.5), (3, -1.5), (21, -1.5)]
    speed, spacing, pairs = 7.0, 6, 5
    total = _perimeter(track)
    for t in range(2):
        for k in range(pairs):
            d = (-(k * spacing * speed) - t * total / 2) / SQ
            path = _loop_from(track, d)
            a, b = path[0]
            _move(st, f"Z{t}_{k}", [_blade(st, a, b), _blade(st, a, b + 1)], path, speed, mode="loop")
    st.rest += [(1.5, 1.0)] + [(a + 1.5, 3.2) for a in (3.5, 6.5, 9.5, 12.5, 15.5, 18.5)] + [(23.0, 1.0)]
    lap = total / speed
    return Meta(tier="hard", tells="a narrow lane with alcoves; trains of blades burst from the far wall and rush "
                                   "down it",
                answer="move alcove to alcove between trains: when a train has passed, step out, walk 3 squares and "
                       "duck into the next alcove before the next one bursts out (you see it come from 13+ squares)",
                careless="walking up the lane: two trains of five pairs, shoved back again and again, ~60-100 HP",
                timing=f"lap {lap:.0f} frames, two trains a lap (one every {lap / 2:.0f} frames), each 5 pairs 6 "
                       "frames apart (~40 frames to pass); trains move 7 px a frame (faster than a run)")


# ---- 10 hard: the long run ----------------------------------------------------------------------------------------

@_pattern("blade", size=(44, 6), tier="hard", title="The long run")
def long_run(st):
    W = st.W
    lo, hi = 0.45, W - 0.45
    # 1. four pendulums, a travelling gap
    _pendulums(st, "P", [5.0 + 1.5 * k for k in range(4)], 8.0, 9, 7)
    st.rest.append((12.0, W / 2))
    # 2. the ledge: pits from a = 14 to 25, three blades punching across the ledge in turn
    for a in range(14, 25):
        for b in range(1, W):
            _pit(st, a + 0.5, b + 0.5)
    for k, a in enumerate((16, 19, 22)):
        path = [(a, -0.75), (a, 0.55)] if k % 2 == 0 else [(a, 0.55), (a, -0.75)]
        _move(st, f"K{k}", [_blade(st, *path[0])], path, 7.0, pause=16)
    st.rest += [(17.5, 0.5), (20.5, 0.5), (26.5, W / 2)]
    # 3. two ploughs with gaps on opposite sides
    _ploughs(st, 29.0, 39.0, 4.5, 15, {"A": (0.5, 1.5), "B": (3.5, 4.5)})
    st.rest.append((42.0, W / 2))
    return Meta(tier="hard", tells="a row of pendulums, a ledge over a pit with stabbing blades, two rows of blades "
                                   "with gaps",
                answer="watch the pendulum wave and run in behind its crest; rest; take the ledge blade by blade as "
                       "each pulls back into the wall; rest; stand in each row's gap as it passes (one by the NW wall, "
                       "one in the middle-SE) and cross between them near the ends, not where they meet (a 34)",
                careless="the pit, or a hundred HP or more of blades: no class walks it",
                timing="pendulums: period 60, 7 frames apart (the wave runs at 7 px a frame); ledge: blades out 6, "
                       "held 16, back 6, in 16 (period 44), alternate blades half a period off; rows: 4.5 px a frame "
                       "over 10 squares, 15 frames at each end (period 174), half a period apart")
