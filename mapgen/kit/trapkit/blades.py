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
import math
from kit.trapkit import pattern, Meta, frames, SQ

REACH = 22.0 / SQ                  # squares: blade (r 12) + player (r 10)


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
    FallX/FallY to its pit room."""
    st.spec.obj_px("Pit", *st.at(a, b), xfer={"UnknownScriptHandler": "", "FallX": 0, "FallY": 0, "ScriptTime1": 0,
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


# ---- 01 standard: round the pillar ------------------------------------------------------------------------------

@pattern("blade", size=(20, 6), title="Round the pillar")
def round_the_pillar(st):
    # a pillar block splits the hall into two corridors 2 squares wide; two blade pairs circle it, half a lap apart:
    # up the NW corridor, across the far end, down the SE corridor, across the near end
    _wall(st, 6.5, 2, 13.5, 2)                                   # the block: a 6.5 .. 13.5, b 2 .. 4
    _wall(st, 6.5, 4, 13.5, 4)
    _wall(st, 6.5, 2, 6.5, 4)
    _wall(st, 13.5, 2, 13.5, 4)
    track = [(5.5, 0.5), (14.5, 0.5), (14.5, 4.5), (5.5, 4.5)]  # the first blade of a pair; its mate rides 1 across
    lap = _perimeter(track)                                      # 845 px
    speed = 3.0
    for k, d in enumerate((0.0, 13.0)):
        path = _loop_from(track, d)
        a, b = path[0]
        _move(st, f"P{k}", [_blade(st, a, b), _blade(st, a, b + 1)], path, speed, mode="loop")
    st.rest += [(2.5, 3.0), (17.5, 3.0)]
    f_lap = lap / speed
    return Meta(tier="standard", tells="two pairs of blades circle a stone block, up one side and down the other",
                answer="go with them: step into the NW corridor two squares behind a pair as it starts up, follow it "
                       "(it moves 3 px a frame, a walk 3.3) and step out at the far end once it has turned across; "
                       "the other pair is half a lap behind you",
                careless="walking up the SE corridor meets a pair head-on: shoved back down it touch after touch, "
                         "~30-50 HP",
                timing=f"lap {f_lap:.0f} frames ({f_lap / 30:.1f} s); a pair spends ~98 frames in each corridor; "
                       "following needs no window, only the right corridor")


# ---- 02 standard: the jaws ----------------------------------------------------------------------------------------

@pattern("blade", size=(22, 6), title="The jaws")
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

@pattern("blade", size=(18, 8), title="The orbit")
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

@pattern("blade", size=(20, 7), title="The revolving door")
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

@pattern("blade", size=(24, 6), title="The saw")
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


# ---- 06 hard: the pendulum row ------------------------------------------------------------------------------------

@pattern("blade", size=(22, 6), tier="hard", title="The pendulum row")
def pendulum_row(st):
    # eight blades swing from wall to wall, a lane each, 1.5 squares apart (their bands overlap: nowhere to stand
    # between them); each starts 7 frames after the one before, so a gap runs down the hall at running pace. They
    # wait by the NW wall until someone steps in.
    W = st.W
    lo, hi = 0.45, W - 0.45
    speed, pause, lag = 8.0, 9, 7
    acts = [_sound(st, "SpikeBlockMove", 5.0, 1.0)]
    for k in range(8):
        a = 5.5 + 1.5 * k
        _move(st, f"P{k}", [_blade(st, a, lo)], [(a, lo), (a, hi)], speed, pause=pause, armed=False)
        acts.append(st.act("arm", f"P{k}", delay=lag * k))
    st.T.zone(f"{st.label}Z", st.at(1.2, W / 2), 60.0, shape="circle", who="player", once=True, acts=acts)
    st.rest += [(2.0, W / 2), (19.5, W / 2)]
    stroke = (hi - lo) * SQ / speed
    period = 2 * (stroke + pause)
    return Meta(tier="hard", tells="a row of blades by the wall that start to swing, one after another, as you step "
                                   "in",
                answer="run, not walk: start just behind the wave of blades along a wall and keep pace with it (the "
                       "gap moves 1.5 squares every 7 frames, a run's pace); a walker drifts out of the gap after "
                       "four or five blades with nowhere to stop",
                careless="walking down the middle: blade after blade, pinned at the walls, ~60-100 HP",
                timing=f"swing period {period:.0f} frames ({stroke:.0f} each way, {pause} at the walls); a spot by "
                       f"the wall is free ~45 frames a period, the middle two windows of ~25")


# ---- 07 hard: find the gap ----------------------------------------------------------------------------------------

@pattern("blade", size=(22, 7), tier="hard", title="Find the gap")
def find_the_gap(st):
    # three walls of blades plough up and down the hall, each with a two-blade gap in a different place (by the NW
    # wall, in the middle, by the SE wall): stand in a wall's gap and it passes over you
    W = st.W
    a0, a1 = 4.0, 18.0
    speed, pause = 4.5, 15
    full = [0.5 + k for k in range(W)]
    gaps = {"A": (0.5, 1.5), "B": (5.5, 6.5), "C": (2.5, 3.5)}
    period = 2 * ((a1 - a0) * SQ / speed + pause)
    acts = [_sound(st, "SpikeBlockMove", a0, W / 2)]
    for s, path, delay in (("A", [(a0, 0), (a1, 0)], 0), ("B", [(a1, 0), (a0, 0)], 0),
                           ("C", [(a0, 0), (a1, 0)], int(period / 4))):
        bs = [b for b in full if b not in gaps[s]]
        start = path[0][0]
        objs = [_blade(st, start, b) for b in bs]
        _move(st, s, objs, [(a, bs[0]) for a, _ in path], speed, pause=pause, armed=False)
        acts.append(st.act("arm", s, delay=delay))
    st.T.zone(f"{st.label}Z", st.at(1.2, W / 2), 60.0, shape="circle", who="player", once=True, acts=acts)
    st.rest += [(2.0, W / 2), (20.0, W / 2)]
    return Meta(tier="hard", tells="three rows of blades across the hall, each missing two blades in a different "
                                   "place: by the NW wall, in the middle, by the SE wall",
                answer="read each row as it comes and stand in its gap (the gap's middle +-0.8 square) while it "
                       "passes; between rows walk on and cross over to the next row's gap (up to 5 squares across)",
                careless="walking up the middle meets the rows with gaps by the walls: bulldozed along the hall, "
                         "~40-80 HP",
                timing=f"each row {speed} px a frame over {a1 - a0:.0f} squares, {pause} frames at each end (period "
                       f"{period:.0f}); A and B start together from either end, C a quarter period later; a row "
                       "passes a spot every ~1.5-3 s, a shift between gaps takes up to ~50 frames")


# ---- 08 hard: the ledge -------------------------------------------------------------------------------------------

@pattern("blade", size=(22, 5), tier="hard", title="The ledge")
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

@pattern("blade", size=(24, 4), tier="hard", title="The zipper")
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

@pattern("blade", size=(44, 6), tier="hard", title="The long run")
def long_run(st):
    W = st.W
    lo, hi = 0.45, W - 0.45
    # 1. four pendulums, a travelling gap, started when you step in
    acts = [_sound(st, "SpikeBlockMove", 5.0, 1.0)]
    for k in range(4):
        a = 5.0 + 1.5 * k
        _move(st, f"P{k}", [_blade(st, a, lo)], [(a, lo), (a, hi)], 8.0, pause=9, armed=False)
        acts.append(st.act("arm", f"P{k}", delay=7 * k))
    st.T.zone(f"{st.label}Z", st.at(1.2, W / 2), 60.0, shape="circle", who="player", once=True, acts=acts)
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
    a0, a1 = 29.0, 39.0
    gaps = {"A": (0.5, 1.5), "B": (3.5, 4.5)}
    for s, path in (("A", [a0, a1]), ("B", [a1, a0])):
        bs = [0.5 + k for k in range(W) if 0.5 + k not in gaps[s]]
        objs = [_blade(st, path[0], b) for b in bs]
        _move(st, s, objs, [(a, bs[0]) for a in path], 4.5, pause=15)
    st.rest.append((42.0, W / 2))
    return Meta(tier="hard", tells="a row of pendulums, a ledge over a pit with stabbing blades, two rows of blades "
                                   "with gaps",
                answer="run with the pendulum wave; rest; take the ledge blade by blade as each pulls back; rest; "
                       "stand in each row's gap as it passes (by the NW wall, then in the middle-SE)",
                careless="the pit, or a hundred HP or more of blades: no class walks it")
