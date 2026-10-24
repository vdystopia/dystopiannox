"""Moving spike blocks: SpikeBlocks carried by the script's movers (kit/traps.py; SetPos each frame along a path), which
shove a player along and hurt him 1 HP a frame of contact, plus Crush damage when a stroke ends with him pinned
(behaviours/traps_push.go). A block cannot be jumped (rules/traps/ENGINE.md 1): the answers are timing, alcoves and
bays, reading a flow, speed, and a lever.

Numbers (rules/TRAPS.md 1, kit/trapkit/_moving.py): a block covers 1.85 squares and touches a player whose centre is
within 1.23 squares of its centre along both axes, so crossing its band takes 24 frames walking (0.8 s) and 12
running; a walk crosses a square in ~10 frames, a run in ~5. Standard stations leave a walker 0.7 s or more and a
mistake costs 20-35 HP; hard ones leave 0.3-0.6 s, or need a run, and a mistake costs 40-100 HP or the pit. Blocks
rest in bays cut into the lane walls (the hardware is in plain sight) and every stroke sounds (SpikeBlockMove,
HammerMissing on landing).
"""
from kit.trapkit import pattern, Meta, frames
from kit.trapkit._moving import (carve, lanes, block, mover, travel, loop_from, snap_acts, pits, wall_at, wake,
                                 TOUCH, WALK, RUN, SQ)
from kit.layout import square_tile

TRACK = "DungeonStoneDark"     # the floor a block's loop runs over (cross traffic)


def _f(x):
    return int(round(x))


def _walk(sq):
    return sq * SQ / WALK


def _run(sq):
    return sq * SQ / RUN


# ---- 01 ----------------------------------------------------------------------------------------------------------

@pattern("block", size=(22, 4), title="The sweeper")
def sweeper(st):
    """One block runs up and down a two-square lane; three alcoves in the north-west wall."""
    L = st.L
    alc = [(6, 8), (11, 13), (16, 18)]
    carve(st, lanes((0, 2, 0, 4), (2, L - 1, 2, 4), (L - 1, L, 0, 4), *[(a0, a1, 0, 2) for a0, a1 in alc]))
    b = block(st, 3.3, 3.0)
    path = [(3.3, 3.0), (L - 2.3, 3.0)]
    speed, pause = 4.0, 15
    mover(st, "M", [b], path, speed, pause=pause, impact=10)
    t = travel(path, speed)
    st.rest += [((a0 + a1) / 2, 1.0) for a0, a1 in alc]
    return Meta(tier="standard",
                tells="a spike block grinds up and down a narrow lane; three alcoves",
                answer=f"step into an alcove as the block comes down at you; once it has passed going down, walk "
                       f"out behind it: it turns at the hall end and follows at 4 px a frame against your 3.3, never "
                       f"catching you before the end (one way {t / 30:.1f} s, pause 0.5 s)",
                careless="meeting it in the lane: struck (10) and shoved back toward the hall at 4 px a frame, "
                         "1 HP a frame: 40-130 HP",
                numbers=dict(speed=speed, one_way=_f(t), period=_f(2 * t + 2 * pause), alcoves=[a for a, _ in alc]),
                route=[(1, 3), (7, 3), (7, 1), (7, 3), (L, 3)])


# ---- 02 ----------------------------------------------------------------------------------------------------------

@pattern("block", size=(24, 8), title="Snapping jaws")
def snapping_jaws(st):
    """Three jaw pairs in bays either side of a four-square lane, each sprung by a plate strip before it."""
    L = st.L
    js = [7, 13, 19]
    boxes = [(0, 2, 0, 8), (2, L - 1, 2, 6), (L - 1, L, 0, 8)]
    for a in js:
        boxes += [(a - 1, a + 1, 0, 2), (a - 1, a + 1, 6, 8)]
    carve(st, lanes(*boxes))
    speed, hold, delay = 5.5, 20, 8
    stroke = travel([(0, 1.0), (0, 3.05)], speed)            # 66 px: 12 frames
    for k, a in enumerate(js):
        m1 = mover(st, f"J{k}a", [block(st, a, 1.0)], [(a, 1.0), (a, 3.05)], speed, pause=hold, armed=False, crush=12)
        m2 = mover(st, f"J{k}b", [block(st, a, 7.0)], [(a, 7.0), (a, 4.95)], speed, pause=hold, armed=False, crush=12)
        acts, done = snap_acts(st, [m1, m2], stroke, hold, delay=delay, sound_at=st.at(a, 4.0))
        plates = [f"P{k}a", f"P{k}b"]
        acts += [st.act("disarm", p) for p in plates] + [st.act("arm", p, delay=150) for p in plates]
        for p, b in zip(plates, (3.1, 4.9)):
            st.plate(p, a - 1.6, b, size=(60, 60), acts=acts)
        st.rest.append((a + 3.0, 4.0))
    shut = delay + stroke                                      # 20 frames: Westwood's jaw impact
    centre = delay + stroke * (1.77 / 2.05)                    # the blocks reach the lane's middle line
    return Meta(tier="standard",
                tells="spike blocks in bays either side, a strip of plates before each pair",
                answer=f"jump the plate strip from before it (2.2 squares deep, a jump carries 3.7) and walk on; or "
                       f"tread on its near edge and step back: the jaws snap {shut / 30:.2f} s later, hold "
                       f"{hold / 30:.2f} s, are home by {done / 30:.1f} s, and the plates sleep 5 s: walk through "
                       f"then ({_walk(3.9) / 30:.1f} s needed of {(150 - done) / 30:.1f} s)",
                careless=f"walking on over the plates: the jaws meet at the lane's middle {centre:.0f} frames after "
                         f"the first touch, when a walker is {(centre * WALK / SQ) - 1.47:.1f} squares into them: "
                         f"caught between two spike blocks, crushed 2 x 12 and held: ~35-50 HP a pair",
                numbers=dict(snap=_f(shut), hold=hold, open=_f(done), plate_sleep=150),
                route=[(1, 4), (L, 4)])


# ---- 03 ----------------------------------------------------------------------------------------------------------

@pattern("block", size=(24, 8), title="The rolling wave")
def rolling_wave(st):
    """Five rams slide across a four-square lane from bays on alternating sides, each 20 frames after the last; the
    wave wakes as you step into the lane."""
    L = st.L
    rows = [5 + 4 * k for k in range(5)]
    boxes = [(0, 2, 0, 8), (2, L - 1, 2, 6), (L - 1, L, 0, 8)]
    for k, a in enumerate(rows):
        boxes.append((a - 1, a + 1, 0, 2) if k % 2 == 0 else (a - 1, a + 1, 6, 8))
    carve(st, lanes(*boxes))
    # a ram's cycle: out 20 frames, 6 at the far wall (traps_push.go FarWait), back 20, 60 at home (the loop's pause)
    speed, far_wait, home_wait, stagger, first = 6.5, 6, 60, 20, 23
    rams = []
    for k, a in enumerate(rows):
        home, far = (1.0, 5.0) if k % 2 == 0 else (7.0, 3.0)
        rams.append(mover(st, f"R{k}", [block(st, a, home)], [(a, home), (a, far)], speed, mode="loop",
                          pause=home_wait, armed=False, crush=20, impact=10, far_wait=far_wait))
        if k:
            st.rest.append((a - 2.0, 4.0))
    # the first ram sets off 23 frames after the way in is crossed: a walker who goes straight on is in its band
    # (34-58 frames) the whole time it is out (32-60 at the lane's middle)
    wake(st, 2.0, 4.0, 2.0, [(r, first + stagger * k) for k, r in enumerate(rams)])
    stroke = travel([(0, 1.0), (0, 5.0)], speed)              # 130 px: 20 frames
    period = 2 * stroke + far_wait + home_wait
    far_open = home_wait + 2 * (3.42 * SQ / speed)
    mid_open = home_wait + 2 * (1.77 * SQ / speed)
    st.rest.append((1.0, 4.0))
    return Meta(tier="standard",
                tells=f"rams in bays on alternating sides slam across, a wave every {period / 30:.1f} s",
                answer=f"step in and stop: the wave wakes 0.8 s later and rolls down the hall every {period / 30:.1f} "
                       f"s; then cross each row as its ram goes home, on the side away from its bay, waiting on the "
                       f"strip between rows (1.5 squares): open {far_open / 30:.1f} s there ({mid_open / 30:.1f} s in "
                       f"the middle) for a {_walk(2 * TOUCH) / 30:.1f} s walk; the next row opens 0.67 s later",
                careless=f"walking straight on: the first ram fires as you reach it and the second as you reach it "
                         f"(each a blow of 10, the shove across, a crush of 20 on the far wall): ~60 HP",
                numbers=dict(stroke=_f(stroke), far=far_wait, home=home_wait, period=_f(period), stagger=stagger,
                             first=first, open_far=_f(far_open), open_mid=_f(mid_open)),
                route=[(1, 4), (L, 4)])


# ---- 04 ----------------------------------------------------------------------------------------------------------

@pattern("block", size=(20, 10), title="The carousel")
def carousel(st):
    """Four spike blocks circle a pit on a two-square ring; the way in and the way out open off opposite legs, so the
    straight way across is the pit."""
    L = st.L

    def keep(a, b):
        ring = 5 <= a < 15 and 1 <= b < 9
        return (a < 2 or a >= L - 1 or ring or (2 <= a < 5 and 4 <= b < 6) or (15 <= a < L - 1 and 4 <= b < 6))
    carve(st, keep)
    pits(st, 7, 13, 3, 7)                                     # the island: six squares by four of open pit
    loop = [(6, 8), (6, 2), (14, 2), (14, 8)]                 # the flow: up the near leg, along b = 2, down the far
    speed, n = 3.0, 4
    total = 0
    for k in range(n):
        path, total = loop_from(loop, k * 28 / n)
        mover(st, f"C{k}", [block(st, *path[0])], path, speed, mode="loop", pause=0, sound=False, impact=8)
    lap = total * SQ / speed
    gap = (total / n - 2 * TOUCH) * SQ / speed               # frames a point stays clear between two blocks
    st.rest += [(3.5, 5.0), (17.0, 5.0)]
    return Meta(tier="standard",
                tells="four spike blocks circle a pit on a narrow ring",
                answer=f"wait in the doorway (2 squares back), step in behind a block as it passes toward the "
                       f"north-west, walk with the flow round the pit (14 squares, on the ring's outer half) keeping "
                       f"your distance, and step out on the far side: {gap / 30:.1f} s of clear ring between blocks, "
                       f"and you walk 3.3 to their 3.0; the pit is too wide to jump",
                careless="walking straight on: across the ring into the pit; walking in against the flow or into a "
                         "passing block: struck (8) and shoved round the ring ahead of it (at the corners toward the "
                         "pit), 1 HP a frame: 30-80 HP or the pit",
                numbers=dict(speed=speed, lap=_f(lap), every=_f(lap / n), clear=_f(gap)),
                route=[(1, 5), (6, 5), (6, 2), (14, 2), (14, 5), (L, 5)])


# ---- 05 ----------------------------------------------------------------------------------------------------------

@pattern("block", size=(22, 8), title="The breathing vice")
def breathing_vice(st):
    """Two vices of spike blocks (three a side each) close and open together on a slow beat; a pocket between."""
    L = st.L
    halves = [(5, 7, 9), (14, 16, 18)]
    boxes = [(0, 2, 0, 8), (2, L - 1, 2, 6), (L - 1, L, 0, 8)]
    for h in halves:
        boxes += [(h[0] - 1, h[-1] + 1, 0, 2), (h[0] - 1, h[-1] + 1, 6, 8)]
    carve(st, lanes(*boxes))
    speed, shut, home = 4.4, 30, 85
    for k, h in enumerate(halves):
        nw = [block(st, a, 1.0) for a in h]
        se = [block(st, a, 7.0) for a in h]
        mover(st, f"V{k}a", nw, [(h[0], 1.0), (h[0], 3.05)], speed, pause=shut, home_wait=home, crush=15)
        mover(st, f"V{k}b", se, [(h[0], 7.0), (h[0], 4.95)], speed, pause=shut, home_wait=home, crush=15,
              sound=False)
    stroke = travel([(0, 1.0), (0, 3.05)], speed)
    period = 2 * stroke + shut + home
    open_mid = home + 2 * (1.77 * SQ / speed)
    half = (h[-1] - h[0]) + 2 * TOUCH
    st.rest.append((11.5, 4.0))
    return Meta(tier="standard",
                tells=f"the lane walls are spike blocks that close like a vice every {period / 30:.1f} s",
                answer=f"go as a vice opens: each stretch is {half:.1f} squares ({_walk(half) / 30:.1f} s walking) "
                       f"and stays open {open_mid / 30:.1f} s; walkers wait out the next squeeze in the pocket, a "
                       f"runner takes both in one breath ({_run(2 * half + 2.5) / 30:.1f} s)",
                careless="caught in a closing vice: crushed between blocks from both sides, 2 x 15 and held a second, "
                         "~50 HP",
                numbers=dict(stroke=_f(stroke), shut=shut, open_home=home, period=_f(period), open_mid=_f(open_mid)),
                route=[(1, 4), (11.5, 4), (L, 4)])


# ---- 06 ----------------------------------------------------------------------------------------------------------

@pattern("block", size=(22, 10), tier="hard", title="Cross traffic")
def cross_traffic(st):
    """Two racetracks of spike blocks cross the hall: four lanes of traffic, two medians, a strip between."""
    L, W = st.L, st.W
    lo, hi = 1.05, W - 1.05
    tracks = [((5.0, 9.0), False), ((13.0, 17.0), True)]
    for a0, a1 in ((4, 10), (12, 18)):                       # the racetracks laid in a darker stone
        for a in range(a0, a1):
            for b in range(W):
                if a in (a0, a0 + 1, a1 - 2, a1 - 1) or b in (0, 1, W - 2, W - 1):
                    t = square_tile(*st.part.square(a + 0.5, b + 0.5))
                    if t in st.spec.floor:
                        st.spec.floor[t] = TRACK
    speed, n = 5.0, 3
    every = 0
    for t, ((a0, a1), flip) in enumerate(tracks):
        loop = [(a0, lo), (a0, hi), (a1, hi), (a1, lo)]
        if flip:
            loop = [(a0, hi), (a0, lo), (a1, lo), (a1, hi)]
        per = sum(abs(loop[i][0] - loop[i - 1][0]) + abs(loop[i][1] - loop[i - 1][1]) for i in range(4))
        for k in range(n):
            path, total = loop_from(loop, k * per / n + t * per / (2 * n))
            mover(st, f"T{t}{k}", [block(st, *path[0])], path, speed, mode="loop", pause=0, sound=False, impact=15)
        every = per / n * SQ / speed
    occupied = 2 * TOUCH * SQ / speed
    free = every - occupied
    st.rest += [(7.0, W / 2), (11.0, W / 2), (15.0, W / 2), (20.0, W / 2)]
    return Meta(tier="hard",
                tells="spike blocks circle two racetracks: four lanes of traffic",
                answer=f"cross one lane at a time from median to median (the medians, 1.5 squares, are safe away from "
                       f"the turns at the walls): a lane is clear {free:.0f} frames between blocks; a walk across "
                       f"takes {_walk(2 * TOUCH):.0f} ({(free - _walk(2 * TOUCH)) / 30:.2f} s spare), a run "
                       f"{_run(2 * TOUCH):.0f} ({(free - _run(2 * TOUCH)) / 30:.2f} s); go as a block passes",
                careless=f"walking straight across without waiting: struck in about half the lanes (15 a blow) and "
                         f"shoved along toward the turns, 1 HP a frame: 40-90 HP",
                numbers=dict(speed=speed, every=_f(every), occupied=_f(occupied), free=_f(free)),
                route=[(1, W / 2), (7.0, W / 2), (11.0, W / 2), (15.0, W / 2), (L, W / 2)])


# ---- 07 ----------------------------------------------------------------------------------------------------------

@pattern("block", size=(26, 6), tier="hard", title="The runaway block")
def runaway(st):
    """A tripwire lets a spike block loose behind you down a long two-square lane crossed by two pit strips: run, and
    jump them without breaking stride."""
    L, W = st.L, st.W
    carve(st, lanes((0, 2, 0, W), (2, L - 1, 2, 4), (2, 4, 4, 6), (L - 1, L, 0, W)))
    strips = [(9, 11), (17, 19)]
    for a0, a1 in strips:
        pits(st, a0, a1, 2, 4)
    path = [(3.0, 5.0), (3.0, 3.0), (L - 2.0, 3.0)]
    speed, start = 6.6, 8
    mv = mover(st, "R", [block(st, 3.0, 5.0)], path, speed, mode="once", armed=False, crush=20, impact=15)
    run = travel(path, speed)
    back = start + run + 60
    rel = mv.replace(st.label, "")
    st.T.zone(f"{st.label}Z", st.at(5.0, 3.0), SQ * 2 ** 0.5, shape="diamond", who="player",
              acts=[st.act("sound", text="BigGong", src=st.at(3.0, 5.0)),
                    st.act("reset", rel), st.act("arm", rel, delay=start),
                    st.act("push_retract", rel, delay=_f(back), frames=80),
                    st.act("disarm", "Z"), st.act("arm", "Z", delay=_f(back + run * speed / 8.0 + 60))])
    # the race from the tripwire's near edge (a = 4): the block comes out of its bay (2 squares) and down the lane
    turn = start + 2 * SQ / speed

    def gap(a):                                                  # squares between a runner at a and the block's reach
        t = (a - 4.0) * SQ / RUN
        return a - (3.0 + TOUCH + max(0.0, t - turn) * speed / SQ)
    spare = [gap(a0) * SQ / speed / 30 for a0, _ in strips]
    t_walk = (4.0 - 3.0 - TOUCH + turn * speed / SQ) / (speed / SQ - WALK / SQ)   # a walker is caught after
    st.rest.append((1.0, 3.0))
    return Meta(tier="hard",
                tells="a spike block waits in a bay; a tripwire, a long lane, two pit strips",
                answer=f"run the moment the gong sounds and keep running; jump each pit strip (2 squares) without "
                       f"breaking stride: the block follows at {speed} px a frame against your 6.9 "
                       f"({_run(L - 4) / 30:.1f} s; {spare[0]:.2f} and {spare[1]:.2f} s to spare at the strips); it "
                       f"stops at the end and goes home 2 s later",
                careless=f"walking: caught {t_walk / 30:.1f} s after the gong, struck (15) and shoved into the first "
                         f"pit strip; running straight on: into the first pit strip",
                numbers=dict(speed=speed, run=_f(run), start=start, spare_s=[round(x, 2) for x in spare],
                             walk_caught=_f(t_walk)),
                route=[(1, 3), (L, 3)])


# ---- 08 ----------------------------------------------------------------------------------------------------------

@pattern("block", size=(24, 10), tier="hard", title="Pendulums over the drop")
def pendulums(st):
    """A two-square bridge over a pit field; four spike blocks swing across it, each on its own beat."""
    L, W = st.L, st.W
    pits(st, 4, 20, 0, 4)
    pits(st, 4, 20, 6, W)
    lo, hi = 1.05, W - 1.05
    swings = [(6.0, 5.5, 8), (9.5, 6.5, 4), (13.0, 4.8, 4), (16.5, 6.0, 6)]
    info = []
    for k, (a, speed, pause) in enumerate(swings):
        home = lo if k % 2 == 0 else hi
        far = hi if k % 2 == 0 else lo
        mover(st, f"P{k}", [block(st, a, home)], [(a, home), (a, far)], speed, pause=pause, sound=True, impact=10)
        one = travel([(a, lo), (a, hi)], speed)
        between = one + pause
        danger = 2 * TOUCH * SQ / speed
        info.append((a, _f(between), _f(danger), _f(between - danger)))
    worst = min(i[3] for i in info)
    st.rest += [(7.75, 5.0), (11.25, 5.0), (14.75, 5.0), (21.5, 5.0)]
    return Meta(tier="hard",
                tells="a narrow bridge over pits, four spike blocks swinging across it",
                answer=f"cross one swing at a time, waiting on the bridge between them (1 square clear): the swings "
                       f"cross the bridge every {', '.join(str(i[1]) for i in info)} frames and are on it "
                       f"{min(i[2] for i in info)}-{max(i[2] for i in info)}; clear {worst}-{max(i[3] for i in info)} "
                       f"frames against a {_walk(2 * TOUCH):.0f}-frame walk (0.2-0.6 s spare) or a "
                       f"{_run(2 * TOUCH):.0f}-frame run: go the moment a swing has passed",
                careless="walking onto the bridge without watching: struck by a swing (10) and swept off the bridge "
                         "into the pit, about half the time; the rest wait where the blocks stop them and live",
                numbers=dict(swings=info),
                route=[(1, 5), (L, 5)])


# ---- 09 ----------------------------------------------------------------------------------------------------------

@pattern("block", size=(22, 11), tier="hard", title="The closing room")
def closing_room(st):
    """Step in and the door slams: a wall of spike blocks creeps across the room at you. The lever that stops it is
    in an alcove halfway; the way out opens in the side wall."""
    L, W = st.L, st.W
    # the entry corridor three squares wide, centred on the station's line (b 5.5): two wide, a walker on the line
    # caught the post at its corner (a real walker stopped at the doorway, 2026-10-24)
    carve(st, lanes((0, 2, 0, W), (2, 4, 4, 7), (4, 16, 2, 8), (6, 8, 0, 2), (11, 13, 0, 2), (9, 11, 8, 9),
                    (9, L - 1, 9, 11), (L - 1, L, 0, W)))
    entry = [wall_at(st, 4, 5, secret="open"), wall_at(st, 4, 6, secret="open")]   # the door across its mouth
    exit_ = wall_at(st, 10, 8, secret="closed")
    blocks = [block(st, 15.0, b, t) for b, t in ((3.0, "IronBlock"), (5.0, "SpikeBlock"), (7.0, "IronBlock"))]
    speed, start, hold = 1.15, 20, 20
    path = [(15.0, 3.0), (5.0, 3.0)]
    mv = mover(st, "W", blocks, path, speed, mode="once", armed=False, crush=30, impact=30).replace(st.label, "")
    creep = travel(path, speed)
    fail = start + creep + hold
    st.T.zone(f"{st.label}Z", st.at(7.0, 5.0), 2.4 * SQ * 2 ** 0.5, shape="diamond", who="player",
              acts=[st.act("walls_close", walls=entry), st.act("sound", text="BigGong", src=st.at(10, 5)),
                    st.act("reset", mv), st.act("arm", mv, delay=start), st.act("disarm", "Z"),
                    st.act("push_retract", mv, delay=_f(fail), frames=20),
                    st.act("walls_open", walls=entry, delay=_f(fail + 90)),
                    st.act("arm", "Z", delay=_f(fail + 330))])
    pull = [st.act("disarm", mv), st.act("push_retract", mv, frames=60), st.act("walls_open", walls=[exit_]),
            st.act("walls_open", walls=entry, delay=30), st.act("sound", text="LeverToggle", src=st.at(12, 0.5)),
            st.act("walls_close", walls=[exit_], delay=360), st.act("arm", "Z", delay=360)]
    st.lever("L", "FloorLever3", 12.0, 0.55, acts=pull, release=pull)
    # the race to the lever alcove (its near end at a = 11.3): the wall must still be 1.23 squares beyond it
    reach = (15.0 - (11.3 + TOUCH)) * SQ / speed + start
    walk_to = _walk(((11.3 - 4.6) ** 2 + 3.0 ** 2) ** 0.5)
    run_to = _run(((12.0 - 4.6) ** 2 + 3.0 ** 2) ** 0.5)
    st.rest.append((7.0, 1.0))
    return Meta(tier="hard",
                tells="a wall of iron and spike blocks at the far end; a lever in an alcove",
                answer=f"the door slams as you enter and the wall creeps at you ({creep / 30:.1f} s to cross); go "
                       f"straight for the lever alcove: a walk gets there with {(reach - walk_to) / 30:.1f} s to "
                       f"spare, a run with {(reach - run_to) / 30:.1f}; pull the lever: the wall goes home and the "
                       f"side door opens for 12 s. Slow but safe: hide in the first alcove, let the wall pass and "
                       f"go home, follow it and pull the lever",
                careless=f"walking on into the room: the wall strikes you (30), pushes you back against the shut door "
                         f"(the middle block's spikes: 1 HP a frame) and crushes you there (30): 55-110 HP",
                numbers=dict(creep=_f(creep), reach_alcove=_f(reach), walk_to=_f(walk_to), run_to=_f(run_to)),
                route=[(1, 5), (5, 5), (11.5, 2.2), (11.9, 1.1), (10, 6.5), (10, 9.5), (L - 1, 9.5), (L, 9.5)],
                careless_route=[(1, 5), (15, 5)])


# ---- 10 ----------------------------------------------------------------------------------------------------------

@pattern("block", size=(44, 8), tier="hard", title="The block gauntlet")
def gauntlet(st):
    """Jaws, a fast wave, a rest, a pendulum bridge and a vice, one after another."""
    L, W = st.L, st.W
    boxes = [(0, 2, 0, W), (2, 17, 2, 6), (17, 29, 0, W), (29, L - 1, 2, 6), (L - 1, L, 0, W)]
    # 1. a jaw pair sprung by a plate strip (a = 5)
    boxes += [(4, 6, 0, 2), (4, 6, 6, 8)]
    # 2. three fast rams, alternating sides, 15 frames apart (a = 9, 12, 15)
    rams = [9, 12, 15]
    boxes += [(a - 1, a + 1, 0, 2) if k % 2 == 0 else (a - 1, a + 1, 6, 8) for k, a in enumerate(rams)]
    # 5. a vice (a = 32, 34, 36, 38)
    boxes += [(31, 39, 0, 2), (31, 39, 6, 8)]
    carve(st, lanes(*boxes))
    # 1
    jspeed, jhold = 6.0, 15
    stroke = travel([(0, 1.0), (0, 3.05)], jspeed)
    m1 = mover(st, "Ja", [block(st, 5, 1.0)], [(5, 1.0), (5, 3.05)], jspeed, pause=jhold, armed=False, crush=15)
    m2 = mover(st, "Jb", [block(st, 5, 7.0)], [(5, 7.0), (5, 4.95)], jspeed, pause=jhold, armed=False, crush=15)
    acts, done = snap_acts(st, [m1, m2], stroke, jhold, delay=6, sound_at=st.at(5, 4))
    acts += [st.act("disarm", p) for p in ("Pa", "Pb")] + [st.act("arm", p, delay=120) for p in ("Pa", "Pb")]
    for p, b in (("Pa", 3.1), ("Pb", 4.9)):
        st.plate(p, 2.6, b, size=(60, 60), acts=acts)
    # 2
    rspeed, rpause, rstag = 8.0, 25, 15
    ram_rows, rams = rams, []
    for k, a in enumerate(ram_rows):
        home, far = (1.0, 5.0) if k % 2 == 0 else (7.0, 3.0)
        rams.append(mover(st, f"R{k}", [block(st, a, home)], [(a, home), (a, far)], rspeed, mode="loop",
                          pause=rpause, armed=False, crush=20, impact=10, far_wait=6))
    wake(st, 2.0, 4.0, 2.0, [(r, 20 + rstag * k) for k, r in enumerate(rams)])
    rstroke = travel([(0, 1.0), (0, 5.0)], rspeed)
    r_open = rpause + 2 * (3.42 * SQ / rspeed)
    # 3. rest: potions on the wide floor
    st.potion(18.0, 0.8)
    st.potion(18.0, 7.2)
    st.rest.append((18.0, 4.0))
    # 4. a pendulum bridge over pits (a = 20 .. 28; the bridge b = 3 .. 5)
    pits(st, 20, 28, 0, 3)
    pits(st, 20, 28, 5, W)
    swings = [(22.0, 6.0, 6), (25.5, 5.0, 10)]
    sw = []
    for k, (a, sp, pa) in enumerate(swings):
        home, far = (1.05, W - 1.05) if k % 2 == 0 else (W - 1.05, 1.05)
        mover(st, f"S{k}", [block(st, a, home)], [(a, home), (a, far)], sp, pause=pa, impact=10)
        sw.append(_f(travel([(a, 1.05), (a, W - 1.05)], sp) + pa - 2 * TOUCH * SQ / sp))
    st.rest.append((30.0, 4.0))
    # 5. the vice: four blocks a side, open 2.3 s, shut 1 s
    vspeed, vshut, vhome = 5.0, 30, 70
    hs = [32, 34, 36, 38]
    mover(st, "Va", [block(st, a, 1.0) for a in hs], [(32, 1.0), (32, 3.05)], vspeed, pause=vshut, home_wait=vhome,
          crush=15)
    mover(st, "Vb", [block(st, a, 7.0) for a in hs], [(32, 7.0), (32, 4.95)], vspeed, pause=vshut, home_wait=vhome,
          crush=15, sound=False)
    v_open = vhome + 2 * (1.77 * SQ / vspeed)
    v_len = (hs[-1] - hs[0]) + 2 * TOUCH
    return Meta(tier="hard",
                tells="plates and jaws, a ram wave, a rest, a swept bridge, a vice",
                answer=f"jump the plates; cross each ram as it goes home ({r_open / 30:.1f} s open on the far side, "
                       f"rows 0.5 s apart); drink and watch the bridge; cross one swing at a time ({min(sw)}-{max(sw)} "
                       f"frames clear); take the vice as it opens: {v_len:.1f} squares in {v_open / 30:.1f} s, a "
                       f"walk needs {_walk(v_len) / 30:.1f}",
                careless="several hundred HP, or the pit from the bridge",
                numbers=dict(jaw_snap=_f(6 + stroke), ram_stroke=_f(rstroke), ram_open=_f(r_open), swing_clear=sw,
                             vice_open=_f(v_open), vice_walk=_f(_walk(v_len))),
                route=[(1, 4), (L, 4)])
