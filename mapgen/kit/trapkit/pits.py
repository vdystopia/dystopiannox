"""Pits, trapdoors, crumbling floors and floors that collapse as you walk (rules/TRAPS.md; rules/traps/ENGINE.md 5).

A Pit is a hole one square across (a 32 x 32 box: the player falls when his centre is over it). Open (enabled) it is a
hole you see; closed (stored disabled, ScriptTimeout 0) it is floor until the script opens it: a trapdoor. Falling
costs no health: the faller lands in the map's pit room (FallX/FallY: TrapLab sets it for every hole) and walks back.
A jump (18 frames, ~120 px: 3.7 squares, one a second for the stamina) passes over holes; landing on one drops you.

Crumbling floor is driven by the script, tile by tile: each PitCrumblingFloor is stored closed with ScriptTimeout 0
(the engine then never opens it by itself, and the script can close it again: a tile the engine crumbled keeps its
opening time and reopens itself, ENGINE.md 5), and an invisible zone the size of a touch (the player's circle, r 10,
meeting the tile's 16 px half-square) opens it `delay` frames after a walking player first touches it; a jumper
passes over without a touch. The rotten tiles lie on cracked floor (CRACKED), the tell. Stepping into a station
(its first square: the mouth zones) closes every hole its script opened and restarts its clocks, so a station is
the same at every try and a straight walk from the way in meets its clocks the same way every time.

Numbers (rules/TRAPS.md 1): walk 3.3 px a frame (a square in ~10 frames), run 6.9 (~4.7). A tile is touched 26 px
before its centre and left 16 px past it: 42 px on it, 12.7 frames walking, 6.1 running, so a tile opening 4 frames
after the touch drops anyone who steps on it, one opening after 8 drops a walker but not a runner. Standard jumps
are at most 2 squares of holes (a take-off window of 1.7 squares), hard ones 3 (0.7).
"""
import math
from kit.trapkit import pattern, Meta, frames, SQ

R2 = math.sqrt(2)
HOLE_XFER = {"UnknownScriptHandler": "", "ScriptTime1": 0, "ScriptTimeout": 0, "ScriptActivated": 0}
TOUCH = (16 + 10) * R2          # zone radius (a diamond: a square in station coordinates) of a touch on a tile
STEP = (16 + 8) * R2            # ... of standing on a tile (its centre over the tile, with a margin of 8 px)
CRACKED = "DirtCrackedDark"     # the floor under rotten tiles (Westwood lays crumbling floor on dirt and cave floor)
JUMP = 3.7                      # squares a jump carries the player (120 px)


def centre(st, i, j):
    """World px of the centre of square (i, j): i squares along the station, j across (integers)."""
    return st.at(i + 0.5, j + 0.5)


def hole(st, i, j, open=True, kind="Pit"):
    x = dict(HOLE_XFER)
    if st.fall_to:
        x.update(FallX=int(st.fall_to[0]), FallY=int(st.fall_to[1]))
    return st.T.obj(kind, *centre(st, i, j), name=st.nm("Pit"), enabled=open, xfer=x)


def holes(st, squares, open=True, kind="Pit"):
    return [hole(st, i, j, open, kind) for i, j in squares]


def rows(i0, i1, j0=0, j1=None, W=None):
    """The squares i0 <= i < i1, j0 <= j < j1."""
    j1 = W if j1 is None else j1
    return [(i, j) for i in range(i0, i1) for j in range(j0, j1)]


def grid(st, i0, lines):
    """Squares by letter from an ASCII plan: lines[n][j] is square (i0 + n, j); returns {letter: [squares]}."""
    out = {}
    for n, line in enumerate(lines):
        assert len(line) == st.W, (line, st.W)
        for j, ch in enumerate(line):
            out.setdefault(ch, []).append((i0 + n, j))
    return out


def cracked(st, squares):
    for i, j in squares:
        st.spec.floor[st.part.tile(i + 0.5, j + 0.5)] = CRACKED


def mouth(st, acts, s="In"):
    """Invisible zones over the station's first square row: `acts` each time the player steps into the station."""
    for j in range(st.W):
        st.T.zone(f"{st.label}{s}{j}", centre(st, 0, j), 0.5 * SQ * R2, who="player", acts=list(acts))


def crumble(st, squares, delay, s="K", stand=0):
    """Rotten floor: each tile opens `delay` frames after a walker first touches it (a jumper does not), on cracked
    floor. Returns the tile groups (each one tile) for the reset."""
    groups = []
    for n, (i, j) in enumerate(squares):
        g = st.group(f"{s}{n}", [hole(st, i, j, open=False, kind="PitCrumblingFloor")])
        st.T.zone(f"{g}Z", centre(st, i, j), TOUCH, who="player", jump=True, acts=[st.act("on", g, delay=delay)])
        groups.append(g)
    cracked(st, squares)
    return groups


def collapsing(st, squares, after=12, stand=45, s="R"):
    """Floor that drops behind you: each tile (a closed Pit) opens `after` frames after the player steps off it,
    and `stand` frames after he steps on it if he lingers. Returns the tile groups."""
    groups = []
    for n, (i, j) in enumerate(squares):
        g = st.group(f"{s}{n}", [hole(st, i, j, open=False, kind="PitCrumblingFloor")])
        st.T.zone(f"{g}Z", centre(st, i, j), STEP, who="player", jump=True,
                  acts=[st.act("on", g, delay=stand)] if stand else [],
                  release=[st.act("on", g, delay=after)])
        groups.append(g)
    cracked(st, squares)
    return groups


def closes(st, groups):
    return [st.act("off", g) for g in groups]


def restarts(st, clocks):
    return [st.act("restart", c) for c in clocks]


def ticks(st, a, b, n, every=15, sound="Gear1"):
    return [st.act("sound", text=sound, src=st.at(a, b), delay=d) for d in range(0, n * every, every)]


# ---- the ten stations -------------------------------------------------------------------------------------------

@pattern("pit", size=(22, 6), tier="standard", title="Holes and a path")
def holes_and_path(st):
    lane = {(6, 1), (7, 1), (8, 1), (8, 2), (8, 3), (8, 4), (9, 4), (10, 4), (11, 4), (11, 3), (11, 2), (12, 2),
            (13, 2)}
    holes(st, [s for s in rows(6, 14, W=st.W) if s not in lane])
    st.rest.append((15.0, 2.5))
    return Meta(tier="standard", tells="eight rows of open holes from wall to wall, a lane of bare floor winding "
                                       "through them",
                answer="walk the lane, one square wide, three turns; at each turn step square to square (a cut "
                       "corner puts your centre over a hole). Or jump in where a hole row is short",
                careless="every straight line across meets a hole within three rows: the pit room",
                mistake="the pit room (no damage; the walk back from the hall)")


@pattern("pit", size=(22, 6), tier="standard", title="Leap the trenches")
def trenches(st):
    W = st.W
    holes(st, rows(5, 6, W=W))                                   # one square deep
    holes(st, rows(10, 12, W=W))                                 # two
    holes(st, rows(15, 18, 0, W - 2) + rows(15, 17, W - 2, W))   # three, but two at the far wall
    st.rest += [(8.0, W / 2), (13.5, W / 2)]
    return Meta(tier="standard", tells="three trenches across the hall, one, two and three squares deep; the last "
                                       "is a square shallower along the far wall",
                answer="jump each: a jump carries 3.7 squares, so take off within 2.7 squares of the first trench, 1.7 "
                       "of the second; jump the third where it is two deep (1.7 squares to take off in; three deep "
                       "leaves 0.7). Walk a few steps between jumps for the stamina",
                careless="walking on: the first trench, the pit room",
                mistake="the pit room")


@pattern("pit", size=(22, 6), tier="standard", title="Look before you leap")
def look_before(st):
    W = st.W
    groups = []
    for k, p in enumerate((5, 10, 15)):
        g = st.group(f"D{k}", holes(st, rows(p + 2, p + 4, W=W), open=False))
        groups.append(g)
        for j in range(W):
            st.plate(f"P{k}{j}", p + 0.5, j + 0.5, size=(25, 25),
                     acts=[st.act("on", g, delay=8), st.act("off", g, delay=8 + 60)])
    mouth(st, closes(st, groups))
    return Meta(tier="standard", tells="three rows of plates across the hall; a click, and the two rows of floor "
                                       "two squares beyond the plates fall open for 2 s",
                answer="stop at the click and let the floor ahead open and close (2 s), then walk on; or jump the "
                       "plates (no click). The floor opens 0.27 s after the click: a walker is 0.8 squares short "
                       "of it, a runner 0.1",
                careless="walking or running on after the click: into the open rows, the pit room",
                mistake="the pit room")


@pattern("pit", size=(22, 6), tier="standard", title="The breathing floor")
def breathing(st):
    W = st.W
    clocks = []
    # three bands of two rows open 1.5 s and closed 2 s, each opening 0.4 s after the one before; a straight walk
    # from the way in reaches the first band just as it opens
    for k, (i, t0) in enumerate(((6, 60), (11, 72), (16, 84))):
        g = st.group(f"B{k}", holes(st, rows(i, i + 2, W=W), open=False))
        on = [(t0 % 105, min(105, t0 % 105 + 45))]
        if t0 % 105 + 45 > 105:
            on.append((0, t0 % 105 + 45 - 105))
        clocks.append(st.clock(f"C{k}", g, 105, on))
    mouth(st, restarts(st, clocks))
    st.rest += [(9.5, W / 2), (14.5, W / 2)]
    return Meta(tier="standard", tells="three bands of floor, two rows each, that fall open for 1.5 s and close for "
                                       "2 s, one after another down the hall",
                answer="wait at a band's edge until it closes, then walk over (2 s closed; the band takes 0.7 s at a "
                       "walk); the floor between the bands is solid",
                careless="a straight walk from the way in reaches the first band as it opens: the pit room",
                mistake="the pit room")


@pattern("pit", size=(22, 6), tier="standard", title="The lever bridge")
def lever_bridge(st):
    W = st.W
    b0, b1 = W // 2 - 1, W // 2 + 1                         # the bridge: two squares wide down the middle
    holes(st, [s for s in rows(8, 14, W=W) if not b0 <= s[1] < b1])
    g = st.group("B", holes(st, rows(8, 14, b0, b1)))
    open_again = frames(6)
    acts = [st.act("off", g), st.act("on", g, delay=open_again)] + ticks(st, 6.5, 0.6, 12)
    st.lever("L", "FloorLever1", 6.5, 0.55, acts=acts, release=acts)
    mouth(st, [st.act("on", g)])
    return Meta(tier="standard", tells="a chasm six squares deep from wall to wall, too wide to jump; a lever by the "
                                       "wall before it",
                answer="pull the lever: a bridge two squares wide closes over the middle of the chasm for 6 s (the "
                       "gears tick); the crossing is 2.5 s at a walk",
                careless="walking on without the lever: the chasm; dawdling on the bridge: it opens under you at 6 s",
                mistake="the pit room")


@pattern("pit", size=(22, 6), tier="hard", title="Stepping stones")
def stepping_stones(st):
    # rotten floor that gives way 4 frames after a touch (nobody walks off a tile that fast) with solid stones to jump
    # between: a gap of two rows (1.7 squares to take off in), then three (0.7)
    plan = grid(st, 5, [
        "kkkkkk",   # 5
        "kkkkkk",   # 6
        "...kkk",   # 7  stone 1
        "...kkk",   # 8
        "kkkkkk",   # 9
        "kkkkkk",   # 10
        "k...kk",   # 11 stone 2
        "k...kk",   # 12
        "kkkkkk",   # 13
        "kkkkkk",   # 14
        "kkkkkk",   # 15
        "kk...k",   # 16 stone 3
        "kk...k",   # 17
        "kkkkkk",   # 18
        "kkkkkk",   # 19
    ])
    groups = crumble(st, plan["k"], delay=4)
    mouth(st, closes(st, groups))
    st.rest += [(8.0, 1.5), (12.0, 2.5), (17.0, 3.5)]
    return Meta(tier="hard", tells="a cracked, rotten floor across the hall with three patches of sound stone; the "
                                   "rot gives way 0.13 s after a touch",
                answer="jump stone to stone: two rows of rot to the first and second (take off in the last 1.7 "
                       "squares), three to the third (take off in the last 0.7 square), two to the far floor; stand "
                       "a second on each stone for the stamina",
                careless="the first step on the rot: the pit room",
                mistake="the pit room (a short jump or a long one)")


@pattern("pit", size=(22, 6), tier="hard", title="Run!")
def run_across(st):
    W = st.W
    sound = [(11, 2), (11, 3), (12, 2), (12, 3)]
    groups = crumble(st, [s for s in rows(6, 18, W=W) if s not in sound], delay=8)
    mouth(st, closes(st, groups))
    st.rest.append((12.0, 3.0))
    return Meta(tier="hard", tells="twelve rows of cracked floor from wall to wall, four squares of sound stone in "
                                   "the middle; each tile falls 0.27 s after a touch",
                answer="run: a running foot is off a tile 0.2 s after touching it (6.1 frames of the 8), a walking "
                       "foot needs 0.42 s. Run straight; stop only on the sound stone; never turn on the rot",
                careless="walking in: the first tile drops under you, the pit room",
                mistake="the pit room (a stop, a turn, a walk)")


@pattern("pit", size=(24, 7), tier="hard", title="The floor falls behind you")
def falls_behind(st):
    # a causeway two squares wide over a chasm: every tile drops 0.4 s after you step off it and 1.5 s after you step
    # on it; it turns twice and has two gaps to jump, so there is no going back and no standing still
    plan = grid(st, 4, [
        ".......",  # 4  the way in (solid)
        "orroooo",  # 5
        "orroooo",  # 6
        "orroooo",  # 7
        "orrrrro",  # 8
        "orrrrro",  # 9
        "oooorro",  # 10
        "oooorro",  # 11
        "ooooooo",  # 12 gap (one row)
        "oooorro",  # 13
        "oooorro",  # 14
        "oooorro",  # 15
        "orrrrro",  # 16
        "orrrrro",  # 17
        "orroooo",  # 18
        "orroooo",  # 19
        "ooooooo",  # 20 gap (two rows)
        "ooooooo",  # 21
    ])
    holes(st, plan["o"])
    groups = collapsing(st, plan["r"], after=12, stand=45)
    mouth(st, closes(st, groups))
    return Meta(tier="hard", tells="a causeway of cracked floor over a chasm, turning twice, two gaps in it",
                answer="keep moving: each tile drops 0.4 s after you leave it and 1.5 s after you stand on it, so no "
                       "turning back and no long waits; step the corners square by square; jump the one-row gap "
                       "from the last three squares before it, the two-row gap from the last 1.7 to the far floor",
                careless="walking on at the gaps: the pit room; stopping to look: the tile drops at 1.5 s",
                mistake="the pit room")


@pattern("pit", size=(25, 6), tier="hard", title="Sinking islands")
def islands(st):
    W = st.W
    # three islands of floor three rows deep across a chasm (two-row gaps between); each sinks (its holes open) for
    # 1.7 s in a 4 s cycle, the next one 1.5 s later: hop on as an island rises, hop off before it sinks
    holes(st, rows(5, 7, W=W) + rows(10, 12, W=W) + rows(15, 17, W=W) + rows(20, 22, W=W))
    clocks = []
    P, down = 120, 60
    for k, i in enumerate((7, 12, 17)):
        g = st.group(f"I{k}", holes(st, rows(i, i + 3, W=W), open=False))
        t0 = (45 * k) % P
        on = [(t0, min(P, t0 + down))] + ([(0, t0 + down - P)] if t0 + down > P else [])
        clocks.append(st.clock(f"C{k}", g, P, on))
    mouth(st, restarts(st, clocks))
    return Meta(tier="hard", tells="a chasm with three rafts of floor across it; each sinks out of sight for 1.7 s "
                                   "and rises again, the next 1.5 s after",
                answer="jump to each island as it rises and off it before it sinks: each hop has a window of ~0.8 s "
                       "and a jump needs a second of stamina between, so leave each island early in its window",
                careless="walking on: the first gap; waiting on an island: it sinks under you",
                mistake="the pit room")


@pattern("pit", size=(42, 6), tier="hard", title="The long descent")
def long_descent(st):
    W = st.W
    # 1. a field of holes with a lane (4-8)
    lane = {(4, 4), (5, 4), (6, 4), (6, 3), (6, 2), (6, 1), (7, 1), (8, 1)}
    holes(st, [s for s in rows(4, 9, W=W) if s not in lane])
    st.rest.append((10.0, 2.5))
    # 2. trapdoor plates: the floor under a plate drops 0.1 s after the press, closes 3 s later (11-14); the bare
    # squares wind, two wide
    bare = {(11, 0), (11, 1), (12, 1), (12, 2), (13, 2), (13, 3), (14, 3), (14, 4)}
    traps = []
    for n, (i, j) in enumerate(s for s in rows(11, 15, W=W) if s not in bare):
        g = st.group(f"T{n}", [hole(st, i, j, open=False)])
        traps.append(g)
        st.plate(f"P{n}", i + 0.5, j + 0.5, size=(25, 25), acts=[st.act("on", g, delay=3),
                                                                 st.act("off", g, delay=3 + 90)])
    # 3. a trench two deep (17-18)
    holes(st, rows(17, 19, W=W))
    st.rest.append((21.0, 3.0))
    # 4. a band that breathes (23-24): open 1 s in 2.5
    band = st.group("B", holes(st, rows(23, 25, W=W), open=False))
    clocks = [st.clock("CB", band, 75, [(0, 30)])]
    # 5. run the rot (27-32), with a stone in the middle
    rot = [s for s in rows(27, 33, W=W) if s not in {(29, 2), (29, 3), (30, 2), (30, 3)}]
    groups = crumble(st, rot, delay=8)
    st.rest.append((34.5, 3.0))
    # 6. the lever bridge, quick (36-39): the lever by the wall, the bridge closed 3 s
    b0, b1 = W // 2 - 1, W // 2 + 1
    holes(st, [s for s in rows(36, 40, W=W) if not b0 <= s[1] < b1])
    br = st.group("BR", holes(st, rows(36, 40, b0, b1)))
    acts = [st.act("off", br), st.act("on", br, delay=frames(3))] + ticks(st, 35.0, 0.6, 6, every=15)
    st.lever("L", "FloorLever1", 35.0, 0.55, acts=acts, release=acts)
    mouth(st, closes(st, groups + traps) + restarts(st, clocks) + [st.act("on", br)])
    return Meta(tier="hard", tells="a lane through holes, a field of plates, a trench, a breathing band, a run of rot "
                                   "and a chasm with its lever, one after another",
                answer="walk the lane, step between the plates (they are trapdoors), jump the trench, cross the band "
                       "as it closes, run the rot (a stop on the stone), pull the lever and walk the bridge in 3 s",
                careless="the pit room at the first stage",
                mistake="the pit room, each stage")
