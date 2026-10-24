"""Arrow traps (and, in the hard tier only, a skull gun): plates that fire a volley down a lane, delayed volleys,
volleys on a clock, rows that fire while anyone stands on them, streams of arrows that a lever silences.

The engine (rules/traps/ENGINE.md 8; GAME5.c nox_xxx_updateShootingTrap_54F9A0): an ArrowTrap shoots the way its
TYPE faces, in world coordinates (ArrowTrap1 SE, ArrowTrap2 SW), only while enabled. Switching it on clears its timers:
it looks at once (a player or a monster in front of it, inside the 700 x 700 square round it, in sight) and fires
at once, then looks and fires once a second while it still sees someone. So a trap switched on for 2 frames fires
one arrow (Westwood's volley); switched on again later it fires again at once (a stream: on 2 frames in every 4);
held on it fires once a second. The arrow is a point flying 50 px a frame along the trap's facing; it hits a player
whose centre it passes within 10 px of (25, impale, armour helps; a jump does not dodge it). A skull gun is the same
machine firing a fireball (12 px a frame, ~96 and a splash).

The lanes here run ACROSS the station (the arrow flies from one side wall to the other) and the traps sit on the
wall they can shoot from: computed from st.across(), so a station along j (TrapLab: across = SE, ArrowTrap1 on the
b = 0 wall) and one along i (across = NE: ArrowTrap2 on the b = W wall) both work. `c` is squares from that wall.
A skull at the far end shoots back down the station (its facing from st.along()).

Timing (rules/TRAPS.md 1): walk 3.3 px a frame, run 6.9. A lane plate's zone reaches 18 px before the lane's line
(a 25 x 25 plate and the kit's 8 px pad), so a walker stepping on is in the arrow's 10 px band 3-9 frames later; an
arrow switched on at frame F hits at F + 2 (the first 1.5 squares from the trap wall) to F + 5 (the far wall).
"""
import math
from kit.trapkit import pattern, Meta, frames, SQ
from kit.trapkit import pits as P

R2 = math.sqrt(2)
ARROWS = {"ArrowTrap1": (1, 1), "ArrowTrap2": (-1, 1)}
SKULLS = {"Skull1": (-1, -1), "Skull2": (1, -1), "Skull3": (-1, 1), "Skull4": (1, 1)}
IN_WALL = 0.3            # squares from the wall line to a wall-mounted trap (Westwood's: ~12 px from the wall)
PLATE = (25, 25)         # lane plates, one a square: the zone reaches 18 px round its centre
DOUBLE = 8               # frames between the two arrows of a hard lane's volley


def facing(st, f):
    """The station direction (da, db) a world facing f = (+-1, +-1) points along."""
    ux, uy = st.along()
    vx, vy = st.across()
    return (int(round((f[0] * ux + f[1] * uy) / R2)), int(round((f[0] * vx + f[1] * vy) / R2)))


def gun(st, want, kinds=ARROWS):
    for t, f in kinds.items():
        if facing(st, f) == want:
            return t
    return None


class Lanes:
    """Lanes across the station: the trap type that shoots across it and the wall it hangs on."""

    def __init__(self, st):
        self.st = st
        for sgn in (1, -1):
            t = gun(st, (0, sgn))
            if t:
                self.type, self.sgn = t, sgn
                break
        else:
            raise ValueError(f"{st.label}: no arrow trap shoots across this station")

    def b(self, c):
        return c if self.sgn > 0 else self.st.W - c

    def trap(self, a, enabled=False):
        return self.st.obj(self.type, a, self.b(IN_WALL), enabled=enabled)

    def plate(self, s, i, j, **kw):
        """A lane plate on square (i, j), j counted from the trap wall."""
        return self.st.plate(s, i + 0.5, self.b(j + 0.5), size=PLATE, **kw)

    def lane(self, s, i, enabled=False):
        """One trap on the line through square row i (a = i + 0.5), as a group."""
        return self.st.group(s, [self.trap(i + 0.5, enabled=enabled)])


def volley(st, g, delay=0, double=False):
    acts = [st.act("pulse", g, delay=delay, frames=2)]
    if double:
        acts.append(st.act("pulse", g, delay=delay + DOUBLE, frames=2))
    return acts


def stream(t0, t1, every=4):
    """Clock windows switching a trap on for 2 frames in every `every` from t0 to t1: an arrow each time."""
    return [(t, min(t + 2, t1)) for t in range(t0, t1, every) if t + 1 < t1]


def loud(period, quiet0, quiet1, every=4):
    """Stream windows for the whole period except the quiet part [quiet0, quiet1) (taken modulo the period)."""
    q0, q1 = quiet0 % period, quiet1 % period
    if q0 < q1:
        spans = [(0, q0), (q1, period)]
    else:
        spans = [(q1, q0)]
    out = []
    for a, b in spans:
        if b - a >= 2:
            out += stream(a, b, every)
    return out


# ---- the ten stations -------------------------------------------------------------------------------------------

@pattern("arrow", size=(22, 6), tier="standard", title="Lane plates")
def lane_plates(st):
    ln = Lanes(st)
    for k, (i, bare) in enumerate(((6, 4), (11, 1), (16, 3))):
        g = ln.lane(f"L{k}", i)
        for j in range(st.W):
            if j != bare:
                ln.plate(f"P{k}{j}", i, j, acts=volley(st, g, delay=1))
    st.rest += [(9.0, 3.0), (14.0, 3.0)]
    return Meta(tier="standard", tells="three rows of plates across the hall, each with an arrow trap on the side "
                                       "wall at its end and one bare square in the row",
                answer="cross each row on its bare square (a different one each row), or jump a plate: a plate "
                       "fires its trap 1 frame after the press, one arrow along the row",
                careless="any straight walk crosses at least two plates: two or three arrows, 50-75 HP",
                mistake="one arrow, 25 HP (a runner crossing the far half of a row is past before it)")


@pattern("arrow", size=(22, 6), tier="standard", title="The click and the pause")
def click_and_pause(st):
    ln = Lanes(st)
    for k, i in enumerate((5, 10, 15)):
        g = ln.lane(f"L{k}", i + 2)
        for j in range(st.W):
            ln.plate(f"P{k}{j}", i, j, acts=volley(st, g, delay=22))
    st.rest += [(9.0, 3.0), (14.0, 3.0)]
    return Meta(tier="standard", tells="three rows of plates from wall to wall; each fires a trap whose lane crosses "
                                       "the hall two squares further on",
                answer="stop at the click: the arrow crosses two squares ahead 0.8 s later; then walk on. Or run "
                       "(you are past the lane by 0.45 s), or jump the plates",
                careless="walking on at an even pace meets each arrow: 3 x 25 = 75 HP",
                mistake="one arrow, 25 HP")


@pattern("arrow", size=(22, 6), tier="standard", title="Volley wall")
def volley_wall(st):
    ln = Lanes(st)
    # four lanes two squares apart, all firing a burst of four arrows (0.5 s) every 1.33 s: a walk crosses a lane
    # every 0.66 s, so an even walk meets the burst at every second lane whatever the moment it starts
    g = st.group("V", [ln.trap(i + 0.5) for i in (8, 10, 12, 14)])
    c = st.clock("C", g, 40, stream(0, 16))
    P.mouth(st, P.restarts(st, [c]))
    st.rest += [(7.0, st.W / 2), (9.5, st.W / 2), (11.5, st.W / 2), (13.5, st.W / 2)]
    return Meta(tier="standard", tells="four arrow traps on the side wall two squares apart, firing bursts of four "
                                       "arrows together, a burst every 1.33 s",
                answer="cross one lane after each burst and wait on the floor before the next lane (0.8 s of quiet; "
                       "a lane takes 0.2 s to cross at a walk); a runner takes three lanes in one quiet",
                careless="an even walk meets a burst at every second lane: 50 HP",
                mistake="an arrow or two, 25-50 HP")


@pattern("arrow", size=(22, 7), tier="standard", title="Hold at the brink")
def brink(st):
    ln = Lanes(st)
    W = st.W
    # the first strip lies before a gap one square deep, the second beyond a gap two deep
    P.holes(st, P.rows(7, 8, W=W) + P.rows(13, 15, W=W))
    for k, i in enumerate((6, 15)):
        g = ln.lane(f"H{k}", i)
        for j in range(W):
            ln.plate(f"P{k}{j}", i, j, acts=[st.act("arrow_hold", g)], release=[st.act("arrow_free", g)])
    st.rest.append((10.5, W / 2))
    return Meta(tier="standard", tells="two gaps across the hall, each with a strip of plates at its edge and an "
                                       "arrow trap on the side wall aimed along the strip",
                answer="the strip fires at once while anyone stands on it, then every second: jump the first strip "
                       "and its gap together from just before the plates (2.1 squares); jump the second gap far "
                       "enough to clear the strip beyond it (take off in the last 0.6 square), or land on it and "
                       "walk off at once (one arrow)",
                careless="walking onto the first strip: an arrow (25), then the gap: the pit room",
                mistake="one arrow a second on the strip (25 HP each), or the pit room")


@pattern("arrow", size=(22, 6), tier="standard", title="The quiet lever")
def quiet_lever(st):
    ln = Lanes(st)
    clocks = []
    for k, i in enumerate((8, 11, 14)):
        g = ln.lane(f"S{k}", i)
        clocks.append(st.clock(f"C{k}", g, 6, [(0, 2)], phase=2 * k))
    quiet = frames(5)
    acts = ([st.act("disarm", c) for c in clocks] + [st.act("arm", c, delay=quiet) for c in clocks] +
            P.ticks(st, 6.5, ln.b(0.6), quiet // 15))
    st.lever("L", "FloorLever1", 6.5, ln.b(0.55), acts=acts, release=acts)
    return Meta(tier="standard", tells="three streams of arrows across the hall, five a second each while anyone is "
                                       "in front of them; a lever by the wall before them",
                answer="pull the lever: the streams stop for 5 s (the gears tick); the nine squares take 3 s at a "
                       "walk",
                careless="walking through the streams: an arrow or two at each, 75-150 HP",
                mistake="the gears stop before you are through: an arrow or two, 25-50 HP")


@pattern("arrow", size=(26, 7), tier="hard", title="The lane hall")
def lane_hall(st):
    ln = Lanes(st)
    bare = [1, 4, 2, 5, 0, 3, 5, 2]           # counted from the trap wall; never the row under the front wall
    for k, i in enumerate(range(5, 21, 2)):
        g = ln.lane(f"L{k}", i)
        for j in range(st.W):
            if j != bare[k]:
                ln.plate(f"P{k}{j}", i, j, acts=volley(st, g, delay=1, double=True))
    return Meta(tier="hard", tells="eight rows of plates two squares apart, each with its trap on the side wall and "
                                   "one bare square, the bare squares zig-zagging across the hall",
                answer="read the whole hall from the door; cross each row on its bare square, moving sideways on "
                       "the clear rows between (two to four squares each time); eight decisions in a row",
                careless="a straight walk crosses at least six plates: a double volley at each, 150+ HP (death)",
                mistake="a double volley: the first arrow staggers, the second lands, ~50 HP")


@pattern("arrow", size=(24, 6), tier="hard", title="Walk with the quiet")
def walk_with_quiet(st):
    ln = Lanes(st)
    clocks = []
    # five streams two squares apart; each falls quiet for 0.8 s, the next 0.67 s later: a quiet that travels down
    # the hall at a walking pace. A straight walk from the way in meets every stream loud.
    period, q, step, q0 = 100, 24, 20, 30
    for k, i in enumerate((6, 8, 10, 12, 14)):
        g = ln.lane(f"S{k}", i)
        clocks.append(st.clock(f"C{k}", g, period, loud(period, q0 + step * k, q0 + step * k + q)))
    P.mouth(st, P.restarts(st, clocks))
    return Meta(tier="hard", tells="five streams of arrows across the hall (seven a second); each goes quiet for "
                                   "0.8 s in turn, the quiet moving down the hall",
                answer="wait a square before the first stream, step off as its quiet begins (a 0.6 s window to "
                       "start in) and walk on at an even pace: the quiet moves with you. A runner must wait at each",
                careless="a straight walk from the way in meets every stream loud: an arrow or two at each, death",
                mistake="one stream met loud: one or two arrows, 25-50 HP")


@pattern("arrow", size=(24, 7), tier="hard", title="Run the rotten floor")
def run_rot(st):
    ln = Lanes(st)
    W = st.W
    groups = P.crumble(st, P.rows(7, 15, W=W), delay=10)
    # two streams over the rot, quiet in turn: the first for 0.67 s, the second 0.47 s later (a runner's time)
    period = 60
    c1 = st.clock("C1", ln.lane("S1", 9), period, loud(period, 0, 20))
    c2 = st.clock("C2", ln.lane("S2", 12), period, loud(period, 14, 34))
    P.mouth(st, P.closes(st, groups) + P.restarts(st, [c1, c2]))
    return Meta(tier="hard", tells="eight rows of cracked floor that give way 0.33 s after a touch, two streams of "
                                   "arrows over them that go quiet in turn",
                answer="run (a walk is too slow for the rot); start from the solid floor so that you cross the first "
                       "stream in its quiet: the second falls quiet as you reach it. Watch two cycles from the edge",
                careless="walking onto the rot: the pit room",
                mistake="a stream met loud: an arrow (25), the stagger on the rot: the pit room")


@pattern("arrow", size=(22, 5), tier="hard", title="The skull's causeway")
def skull_causeway(st):
    W = st.W
    mid = W // 2
    skull = gun(st, (-1, 0), SKULLS)
    # a causeway one square wide down the middle over a chasm, ledges two squares wide beside it every second row,
    # left and right in turn; a skull gun at the far end firing down the causeway
    ledges = {}
    for n, i in enumerate(range(6, 18, 2)):
        side = range(0, mid) if n % 2 == 0 else range(mid + 1, W)
        for j in side:
            ledges[(i, j)] = True
    P.holes(st, [s for s in P.rows(5, 18, W=W) if s[1] != mid and s not in ledges])
    g = st.group("G", [st.obj(skull, st.L - IN_WALL, mid + 0.5, enabled=True)])
    st.plate("Off", 18.5, mid + 0.5, size=(45, 45), who="player", acts=[st.act("off", g)])
    P.mouth(st, [st.act("on", g)])
    st.rest += [(i + 0.5, 0.8 if n % 2 == 0 else W - 0.8) for n, i in enumerate(range(6, 18, 2))]
    return Meta(tier="hard", tells="a causeway one square wide over a chasm, ledges beside it, a skull gun at the far "
                                   "end that fires down it once a second while it sees you",
                answer="stand on a ledge (out of the line), let a fireball pass, run to the next ledge two rows on: "
                       "a start window of 0.35-0.55 s in each second; walking the hop is too slow. The plate at the "
                       "end of the causeway silences the gun",
                careless="walking the causeway: a fireball a second, ~96 each: death",
                mistake="one fireball, ~96 HP; a step off a ledge: the pit room")


@pattern("arrow", size=(42, 7), tier="hard", title="The long gallery")
def long_gallery(st):
    ln = Lanes(st)
    W = st.W
    # 1. lane plates, double volleys (4-8)
    for k, (i, bare) in enumerate(((4, 2), (6, 5), (8, 0))):
        g = ln.lane(f"L{k}", i)
        for j in range(W):
            if j != bare:
                ln.plate(f"P{k}{j}", i, j, acts=volley(st, g, delay=1, double=True))
    st.potion(10.5, 0.8)
    # 2. two click rows: the arrow crosses two squares on (12 -> 14, 17 -> 19)
    for k, i in enumerate((12, 17)):
        g = ln.lane(f"D{k}", i + 2)
        for j in range(W):
            ln.plate(f"Q{k}{j}", i, j, acts=volley(st, g, delay=22, double=True))
    # 3. a strip at the brink (22) of a gap one deep (23)
    P.holes(st, P.rows(23, 24, W=W))
    g = ln.lane("H", 22)
    for j in range(W):
        ln.plate(f"B{j}", 22, j, acts=[st.act("arrow_hold", g)], release=[st.act("arrow_free", g)])
    st.potion(26.0, 0.8)
    # 4. four streams with a travelling quiet (28-34), the quiet 0.67 s, 0.67 s between streams
    period, q, step = 80, 20, 20
    clocks = []
    for k, i in enumerate((28, 30, 32, 34)):
        clocks.append(st.clock(f"C{k}", ln.lane(f"S{k}", i), period, loud(period, step * k, step * k + q)))
    P.mouth(st, P.restarts(st, clocks))
    st.rest += [(10.5, W / 2), (15.5, W / 2), (20.5, W / 2), (26.0, W / 2), (37.0, W / 2)]
    return Meta(tier="hard", tells="lane plates, two click rows, a strip at the brink of a gap, four streams with a "
                                   "travelling quiet, one after another",
                answer="bare squares through the lanes, stop at each click, jump the strip and the gap together, "
                       "walk with the quiet; a potion after the lanes and after the gap",
                careless="several hundred HP: no class walks it",
                mistake="~50 HP at each stage (double volleys), or the pit room at the gap")
