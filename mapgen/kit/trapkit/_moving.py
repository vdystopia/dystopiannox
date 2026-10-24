"""Helpers shared by the moving-block kinds (trapkit/blocks.py: spike blocks; trapkit/pushers.py: stone and iron
blocks, force fields, bumpers and pits): the station's floor shaped into lanes, bays and alcoves (squares cut out of
it, the walls redrawn round them), blocks on the script's movers with their sounds, slams and phases
(behaviours/traps_push.go), pits, force fields and bumpers.

Geometry (rules/traps/ENGINE.md 0.1, 5, 6): a square is 32.5 px; a block (SpikeBlock, StoneBlock, IronBlock) is a
60 x 60 box whose sides run along the squares, so it covers 1.85 squares each way and touches a player (radius 10)
whose centre is within TOUCH = 1.23 squares of its centre along both a and b; a Pit's 32 x 32 box fills one square
(place one per square centre); a player falls when his centre enters it. Movement (rules/TRAPS.md 1, measured):
walk 3.3 px a frame, run 6.9, a jump carries ~120 px in 18 frames, one jump a second.
"""
import json, math
from kit.trapkit import SQ
from kit.layout import point_cell, square_tile

BH = 30.0 / SQ                 # a block's half size, squares
PR = 10.0 / SQ                 # the player's radius
TOUCH = BH + PR                # 1.23: centre distance along a or b at which a block touches the player
REST = 1.0                     # a block's centre one square from the wall it rests against (a 2.6 px gap)
WALK, RUN, JUMP = 3.3, 6.9, 120.0
PIT_XFER = {"UnknownScriptHandler": "", "ScriptTime1": 0, "ScriptTimeout": 0, "ScriptActivated": 0}


def band_frames(px=2 * TOUCH * SQ, speed=WALK):
    """Frames a player needs to cross a block's band (80 px: the block's 60 plus his own 20) at `speed`."""
    return px / speed


# ---- the floor ---------------------------------------------------------------------------------------------------

def carve(st, keep):
    """Cut every station square (a, b) (integers: the square a..a+1 x b..b+1) for which keep(a, b) is false out of
    the floor, and redraw the walls round what is left by Dungeon.apply's rule (a wall point between floor and
    void; none inside the void)."""
    sp, part = st.spec, st.part
    gone = set()
    for a in range(st.L):
        for b in range(st.W):
            if not keep(a, b):
                s = part.square(a + 0.5, b + 0.5)
                sp.floor.pop(square_tile(*s), None)
                gone.add(s)
    corners = set()
    for i, j in gone:
        corners |= {(i, j), (i + 1, j), (i, j - 1), (i + 1, j - 1)}
    for p, q in corners:
        quad = [(p - 1, q), (p, q), (p - 1, q + 1), (p, q + 1)]
        n = sum(square_tile(*s) in sp.floor for s in quad)
        x, y = point_cell(p, q)
        if 0 < n < 4:
            if (x, y) not in sp.wallmap:
                sp.wall(x, y, part.wall)
        else:
            sp.remove_wall(x, y)
    return gone


def lanes(*boxes):
    """keep(a, b) for carve: the squares inside any of the boxes (a0, a1, b0, b1), half open."""
    return lambda a, b: any(a0 <= a < a1 and b0 <= b < b1 for a0, a1, b0, b1 in boxes)


def corner_cell(st, a, b):
    """The wall cell of the station's square corner (a, b) (integers)."""
    si, sj = st.part.sq(a, b)
    return point_cell(int(round(si)), int(round(sj)) - 1)


def wall_at(st, a, b, secret=None):
    x, y = corner_cell(st, a, b)
    st.spec.wall(x, y, st.part.wall, secret=secret)
    return x, y


# ---- blocks on movers --------------------------------------------------------------------------------------------

def block(st, a, b, type_="SpikeBlock"):
    return st.obj(type_, a, b)


def mover(st, s, objs, path, speed, mode="pingpong", pause=0, armed=True, delay=0, crush=0, home_wait=0,
          sound=True, impact=0):
    """A mover (kit/traps.py) carrying `objs` along `path` (station squares) at `speed` px a frame, watched by
    traps_push.go: armed `delay` frames after the start (then `armed` should be False), `crush` damage to whoever
    is pinned against its blocks when it reaches the far end, `home_wait` frames at the start of the path
    (pingpong; the far end keeps `pause`), `impact` damage to a player its moving blocks strike (once a contact),
    its sounds."""
    name = f"{st.label}{s}"
    pts = [st.at(a, b) for a, b in path]
    st.T.mover(name, objs, pts, speed, mode=mode, pause=pause, armed=armed and not delay)
    st.T.movers[name].update(delay=int(delay), crush=int(crush), home_wait=int(home_wait), impact=int(impact),
                             path_ab=[list(p) for p in path])
    st.T.starts.append(f"TrapPushMover(pushMover{{Mover: {json.dumps(name)}, Crush: {int(crush)}, Delay: {int(delay)}, "
                       f"HomeWait: {int(home_wait)}, Sound: {str(bool(sound)).lower()}, Impact: {int(impact)}}})")
    return name


def travel(path, speed):
    """Frames a mover takes along `path` (squares) at `speed` px a frame."""
    L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:]))
    return L * SQ / speed


def loop_from(path, start):
    """A closed loop (a list of corners) re-started `start` squares along it, for loop movers spaced round it."""
    pts = list(path) + [path[0]]
    segs = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    total = sum(segs)
    start %= total
    k, acc = 0, 0.0
    while acc + segs[k] <= start:
        acc += segs[k]
        k += 1
    t = (start - acc) / segs[k]
    a, b = pts[k], pts[k + 1]
    first = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    rest = pts[k + 1:-1] + pts[:k + 1]
    out = [first] + [p for p in rest if math.hypot(p[0] - first[0], p[1] - first[1]) > 1e-6]
    return out, total


def jaws(st, s, a, b_home, b_shut, speed, hold, delay=8, crush=0, type_="SpikeBlock"):
    """A block that slams from b_home to b_shut and back when sprung (pingpong, sprung by snap_acts)."""
    name = block(st, a, b_home, type_)
    mv = mover(st, s, [name], [(a, b_home), (a, b_shut)], speed, mode="pingpong", pause=hold, armed=False,
               crush=crush)
    return mv


def snap_acts(st, movers, speed_frames, hold, delay=8, sound_at=None):
    """The actions that spring a set of pingpong movers once: out, `hold` frames shut, back, stop (each
    mover's stroke takes `speed_frames`). Returns (acts, frames until all are home)."""
    acts = []
    if sound_at is not None:
        acts.append(st.act("sound", text="SpikeBlockMove", src=sound_at))
    done = delay + 2 * int(math.ceil(speed_frames)) + hold + 3
    for mv in movers:
        mv = mv.replace(st.label, "")
        acts += [st.act("reset", mv), st.act("arm", mv, delay=delay), st.act("disarm", mv, delay=done)]
    return acts, done


# ---- pits, forces, bumpers ---------------------------------------------------------------------------------------

def pit(st, a, b, enabled=True):
    xf = dict(PIT_XFER)
    if st.fall_to:
        xf.update(FallX=int(st.fall_to[0]), FallY=int(st.fall_to[1]))
    return st.obj("Pit", a, b, enabled=enabled, xfer=xf)


def pits(st, a0, a1, b0, b1, enabled=True, skip=()):
    """A Pit on every square centre of a0..a1 x b0..b1 (integers, half open)."""
    return [pit(st, a + 0.5, b + 0.5, enabled) for a in range(a0, a1) for b in range(b0, b1) if (a, b) not in skip]


def vec(st, da, db):
    ux, uy = st.along()
    vx, vy = st.across()
    return da * ux + db * vx, da * uy + db * vy


def force(st, s, a0, a1, b0, b1, d, strength, period=0, on=(), phase=0, armed=True, sound="", tick=0):
    """A force field over the station box a0..a1 x b0..b1 (squares) pushing along d = (da, db) (station terms)
    with `strength` (PushTo force added each frame: a drift of about 1-2 x strength px a frame on a standing
    player, added to his walk; a jump rides over it). period/on: gusts (windows of each period, like a clock)."""
    name = f"{st.label}{s}"
    n = math.hypot(*d)
    fx, fy = vec(st, d[0] / n * strength, d[1] / n * strength)
    cx, cy = st.at((a0 + a1) / 2, (b0 + b1) / 2)
    ux, uy = st.along()
    on_go = "[][2]int{" + ", ".join(f"{{{int(t0)}, {int(t1)}}}" for t0, t1 in on) + "}"
    st.T.starts.append(
        f"TrapPushField(pushField{{Name: {json.dumps(name)}, C: ns.Ptf({cx:.1f}, {cy:.1f}), U: ns.Ptf({ux:.4f}, {uy:.4f}), "
        f"HL: {(a1 - a0) / 2 * SQ:.1f}, HW: {(b1 - b0) / 2 * SQ:.1f}, F: ns.Ptf({fx:.3f}, {fy:.3f}), "
        f"Period: {int(period)}, On: {on_go}, Phase: {int(phase)}, Armed: {str(armed).lower()}, "
        f"Sound: {json.dumps(sound)}, Tick: {int(tick)}}})")
    info = dict(name=name, box=[a0, a1, b0, b1], dir=list(d), strength=strength, period=period,
                on=[list(w) for w in on], phase=phase, armed=armed)
    if not hasattr(st, "forces"):
        st.forces = []
    st.forces.append(info)
    return name


def bumper(st, s, a, b, strength=40):
    """A ForceOrb (a glowing red orb, SHORT: a jump passes over it) that throws whoever touches it away from its
    centre: PushTo `strength` (30 throws ~60 px, measured)."""
    st.obj("ForceOrb", a, b)
    x, y = st.at(a, b)
    return st.T.zone(f"{st.label}{s}", (x, y), 15 + 10 + 4, shape="circle", who="any", jump=True, rearm=8,
                     acts=[st.act("push_bump", src=(x, y), frames=strength)])
