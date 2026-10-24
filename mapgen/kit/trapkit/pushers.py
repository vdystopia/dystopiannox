"""Pushers and pits: what shoves the player into a hole. Stone and iron blocks on the script's movers (no damage, a pure
shove: a shove that carries his centre over an open Pit drops him into the pit room, rules/traps/ENGINE.md 5), floors
and winds that push every frame (force fields, behaviours/traps_push.go: a conveyor belt, a gust, a tilt), and
bumpers that throw (a ForceOrb; Westwood's G_Mines force zones and Con10 bumpers, rules/traps/WESTWOOD_SCRIPTS.md 1.3
and 1.5). A fall costs no health: it costs the walk back from the pit room (T5), so the mistake here is the pit.

The pushes (kit/trapkit/_moving.py): a field's force is added to the player's own each frame; it drifts a standing
player about its strength in px a frame (the walk's own force of 3.1 moves him 3.3; the game's physics would allow up
to twice that: an in-game check), a walking player can lean into it, and a jump rides over it (the game sets a
jumper's force itself). Belts are laid in riveted slats; every gust and tilt sounds, with a tick before it.
"""
from kit.trapkit import pattern, Meta
from kit.trapkit._moving import (carve, lanes, block, mover, travel, pits, force, bumper, TOUCH, WALK, RUN, SQ)
from kit.layout import square_tile

BELT = "WoodSlatFloorRIVETS"


def _f(x):
    return int(round(x))


def _meta(st, **kw):
    """The station's Meta, with its force fields (for the simulator: box, direction, strength, gusts)."""
    m = Meta(**kw)
    if getattr(st, "forces", None):
        m["forces"] = st.forces
    return m


def _walk(sq):
    return sq * SQ / WALK


def _run(sq):
    return sq * SQ / RUN


def _paint(st, a0, a1, b0, b1, material):
    for a in range(a0, a1):
        for b in range(b0, b1):
            t = square_tile(*st.part.square(a + 0.5, b + 0.5))
            if t in st.spec.floor:
                st.spec.floor[t] = material


def _causeway(line):
    """The squares of a two-square causeway along a centre line of right-angled legs (integer points)."""
    out = set()
    for (a0, b0), (a1, b1) in zip(line, line[1:]):
        if b0 == b1:
            for a in range(min(a0, a1) - 1, max(a0, a1) + 1):
                out |= {(a, b0 - 1), (a, b0)}
        else:
            for b in range(min(b0, b1) - 1, max(b0, b1) + 1):
                out |= {(a0 - 1, b), (a0, b)}
    return out


# ---- 01 ----------------------------------------------------------------------------------------------------------

@pattern("push", size=(18, 6), title="Pushers on the beat")
def pushers_on_the_beat(st):
    """Three stone pushers in wall slots shove across a three-square walkway to a row of pits, all on one 3 s beat."""
    L, W = st.L, st.W
    ks = [5, 9, 13]
    carve(st, lanes((0, 2, 0, W), (2, L - 1, 0, 4), (L - 1, L, 0, W), *[(a - 1, a + 1, 4, 6) for a in ks]))
    pits(st, 3, L - 2, 0, 1)
    speed, far, home = 4.4, 15, 31
    for k, a in enumerate(ks):
        mover(st, f"P{k}", [block(st, a, 5.0, "StoneBlock")], [(a, 5.0), (a, 2.0)], speed, pause=far,
              home_wait=home, sound=k == 1)
        if k:
            st.rest.append((a - 2.0, 2.5))
    stroke = travel([(0, 5.0), (0, 2.0)], speed)
    period = 2 * stroke + far + home
    edge_open = home + 2 * (2.47 * SQ / speed)               # the pit-side line b = 1.3
    mid_open = home + 2 * (1.27 * SQ / speed)                # the middle, b = 2.5
    band = _walk(2 * TOUCH)
    return _meta(st, tier="standard",
                tells="stone blocks in wall slots shove across the walkway to a row of pits",
                answer=f"cross each pusher as it goes home, on the line beside the pits (it reaches there last): "
                       f"open {edge_open / 30:.1f} s there, {mid_open / 30:.1f} s in the middle, for a "
                       f"{band / 30:.1f} s walk; wait on the floor between them (1.5 squares) for the next beat",
                careless=f"walking the middle at an even pace: a pusher catches you ~70% of the beats and shoves "
                         f"you into the pits",
                numbers=dict(stroke=_f(stroke), far=far, home=home, period=_f(period), open_edge=_f(edge_open),
                             open_mid=_f(mid_open), band=_f(band)),
                route=[(1, 1.3), (L, 1.3)], careless_route=[(1, 2.5), (L, 2.5)])


# ---- 02 ----------------------------------------------------------------------------------------------------------

@pattern("push", size=(22, 6), title="Belts")
def belts(st):
    """Three conveyor belts across the hall, each running to a chasm at one end, in turn toward either side."""
    L, W = st.L, st.W
    strength = 1.3
    spans = [(4, 8, +1), (10, 14, -1), (16, 20, +1)]
    for k, (a0, a1, d) in enumerate(spans):
        _paint(st, a0, a1, 0, W, BELT)
        if d > 0:
            pits(st, a0, a1, 3, W)
        else:
            pits(st, a0, a1, 0, 3)
        force(st, f"B{k}", a0, a1, 0, W, (0, d), strength, sound=f"Gear{k + 1}", tick=60)
        st.rest.append((a1 + 1.0, 3.0))
    cross = _walk(4)
    drift = strength * cross / SQ
    return _meta(st, tier="standard",
                tells="three belts of riveted slats cross the hall, each running into a chasm",
                answer=f"step onto each belt at its upstream edge (away from its chasm) and walk across leaning into "
                       f"the drift (a third off straight is enough); walking straight drifts you "
                       f"~{drift:.1f} squares over the {cross / 30:.1f} s, a run {strength * _run(4) / SQ:.1f}, and "
                       f"a jump rides most of it; the belts alternate sides",
                careless="walking down the middle of the hall: straight into the first chasm, or drifted into one",
                numbers=dict(strength=strength, cross_walk=_f(cross), drift_sq=round(drift, 2)),
                route=[(1, 0.6), (9, 0.6), (9, 5.4), (15, 5.4), (15, 0.6), (L, 0.6)],
                careless_route=[(1, 1.5), (L, 1.5)])


# ---- 03 ----------------------------------------------------------------------------------------------------------

@pattern("push", size=(22, 8), title="The orb causeway")
def orb_causeway(st):
    """A winding two-square causeway over a pit field; glowing force orbs at its bends and edges throw whoever
    touches them."""
    L, W = st.L, st.W
    line = [(1, 2), (6, 2), (6, 6), (11, 6), (11, 2), (16, 2), (16, 6), (L, 6)]
    road = _causeway(line)
    pits(st, 3, 19, 0, W, skip=road)
    # bumpers: inside each bend, 0.4 squares in from its inner corner (where a walker cuts it), and on the inner edge
    # of each long leg, so each leg has one clear line (its outer half) and each turn between bends a crossover
    bends = [(5.4, 2.6), (6.6, 5.4), (10.4, 5.4), (11.6, 2.6), (15.4, 2.6), (16.6, 5.4)]
    edges = [(3.8, 2.85), (8.5, 5.15), (13.5, 2.85), (18.0, 5.15)]
    strength = 40
    for k, (a, b) in enumerate(bends + edges):
        bumper(st, f"O{k}", a, b, strength)
    return _meta(st, tier="standard",
                tells="a narrow causeway winds over pits; glowing orbs stand at its bends",
                answer="keep to the outer half of each leg and swing wide round every bend, crossing over between "
                       "bends (an orb reaches 0.9 squares; about 1 is left beside it); or jump an orb (it is low): "
                       "touching one throws you ~2.5 squares away from it",
                careless="cutting the corners: the bend orbs throw you off the causeway into the pits",
                numbers=dict(strength=strength, orbs=len(bends) + len(edges)),
                route=[(1, 1.5), (6.4, 1.6), (6.4, 3.6), (5.6, 4.6), (5.6, 6.4), (11.4, 6.4), (11.4, 4.4),
                       (10.6, 3.4), (10.6, 1.6), (16.4, 1.6), (16.4, 3.6), (15.6, 4.6), (15.6, 6.4), (L, 6.4)],
                careless_route=[(1, 2), (6, 2), (6, 6), (11, 6), (11, 2), (16, 2), (16, 6), (L, 6)])


# ---- 04 ----------------------------------------------------------------------------------------------------------

@pattern("push", size=(24, 10), title="Gusts on the bridge")
def gusts(st):
    """A two-square bridge along the north-west wall over a pit field; a wind gusts across it toward the pits."""
    L, W = st.L, st.W
    pads = [(8, 10), (14, 16)]
    solid = {(a, b) for a in range(4, 20) for b in range(0, 2)}
    solid |= {(a, b) for a0, a1 in pads for a in range(a0, a1) for b in range(0, 4)}
    pits(st, 4, 20, 0, W, skip=solid)
    period, gust, strength = 100, 30, 2.0
    force(st, "G", 4, 20, 0, W, (0, 1), strength, period=period, on=[(0, gust)], sound="PushCast")
    force(st, "T", 4, 20, 0, W, (0, 1), 0.0, period=period, on=[(period - 30, period)], sound="GenerateTick", tick=15)
    for a0, a1 in pads:
        st.rest.append(((a0 + a1) / 2, 0.6))
    calm = period - gust
    seg = _walk(4)
    drift = strength * gust / SQ
    return _meta(st, tier="standard",
                tells="a narrow bridge along the wall over pits; a wind gusts across it",
                answer=f"two ticks, then a 1 s gust every {period / 30:.1f} s: cross a stretch of bridge (4 squares, "
                       f"{seg / 30:.1f} s) in the {calm / 30:.1f} s calm and stand out the gust on a pad, against the "
                       f"wall; caught on the bridge, walk into the wall (you out-walk the wind) or jump",
                careless=f"standing or walking straight on the bridge when the gust comes: it carries you "
                         f"~{drift:.1f} squares, off the two-square bridge into the pits",
                numbers=dict(period=period, gust=gust, strength=strength, calm=calm, stretch_walk=_f(seg),
                             drift_sq=round(drift, 2)),
                route=[(1, 0.6), (L, 0.6)], careless_route=[(1, 1.0), (L, 1.0)])


# ---- 05 ----------------------------------------------------------------------------------------------------------

@pattern("push", size=(20, 9), title="The sliding wall")
def sliding_wall(st):
    """A wall of four iron blocks slides across the hall from one trench of pits to the other and back; the hall
    must be crossed along its whole length."""
    L, W = st.L, st.W
    pits(st, 4, 16, 0, 1)
    pits(st, 4, 16, W - 1, W)                                  # the wall rests over a second trench
    blocks = [block(st, a, W - 1.0, "IronBlock") for a in (7, 9, 11, 13)]
    speed, far, home = 3.0, 20, 75
    path = [(7, W - 1.0), (7, 2.0)]
    mover(st, "W", blocks, path, speed, pause=far, home_wait=home)
    stroke = travel(path, speed)
    period = 2 * stroke + far + home
    span = (13 + TOUCH) - (7 - TOUCH)
    trench_open = home + 2 * ((W - 1 - 0.35 - TOUCH - 1.0) * SQ / speed)
    mid_open = home + 2 * ((W / 2 - TOUCH - 1.0) * SQ / speed)
    st.rest.append((17.5, W / 2))
    return _meta(st, tier="standard",
                tells="a wall of iron blocks slides across the hall from trench to trench",
                answer=f"cross the wall's whole length ({span:.1f} squares, {_walk(span) / 30:.1f} s) as it goes "
                       f"home, on the line beside the trench (it reaches there last): open {trench_open / 30:.1f} s "
                       f"there, {mid_open / 30:.1f} s in the middle; the wall comes every {period / 30:.1f} s",
                careless=f"walking the middle when it moves: it shoves you sideways at {speed} px a frame, faster than "
                         f"you can walk out of its 8-square face: into one trench or the other",
                numbers=dict(stroke=_f(stroke), far=far, home=home, period=_f(period), open_trench=_f(trench_open),
                             open_mid=_f(mid_open), walk_span=_f(_walk(span))),
                route=[(1, 1.4), (L, 1.4)], careless_route=[(1, W / 2), (L, W / 2)])


# ---- 06 ----------------------------------------------------------------------------------------------------------

@pattern("push", size=(24, 10), tier="hard", title="Switchback trench")
def switchback(st):
    """Two walkways either side of a trench, each lined with pushers that fire together, the two sides in turn: walk
    one side while it is quiet and jump the trench to the other before it fires."""
    L, W = st.L, st.W
    nw = [5, 8, 11, 14, 17, 20]
    se = [6, 9, 12, 15, 18]
    boxes = [(0, 2, 0, W), (2, L - 1, 2, 8), (L - 1, L, 0, W)]
    boxes += [(a - 1, a + 1, 0, 2) for a in nw] + [(a - 1, a + 1, 8, 10) for a in se]
    carve(st, lanes(*boxes))
    pits(st, 3, L - 2, 4, 6)
    speed, far, home, period = 6.5, 6, 54, 80
    stroke = travel([(0, 1.0), (0, 3.0)], speed)
    home = period - 2 * _f(stroke) - far
    for k, a in enumerate(nw):
        mover(st, f"N{k}", [block(st, a, 1.0, "StoneBlock")], [(a, 1.0), (a, 3.0)], speed, pause=far,
              home_wait=home, sound=k == 2)
    for k, a in enumerate(se):
        mover(st, f"S{k}", [block(st, a, 9.0, "StoneBlock")], [(a, 9.0), (a, 7.0)], speed, pause=far,
              home_wait=home, armed=False, delay=period // 2, sound=k == 2)
    reach = 0.77 * SQ / speed                                  # a pusher reaches the walkway's middle line
    danger = 2 * stroke + far - 2 * reach
    both_quiet = period / 2 - danger
    return _meta(st, tier="hard",
                tells="walkways either side of a trench, lined with stone pushers that fire side by side",
                answer=f"each side fires every {period / 30:.1f} s, the other side half a beat later, so each is "
                       f"quiet {(period - danger) / 30:.1f} s and both are quiet {both_quiet / 30:.2f} s twice a beat: "
                       f"walk a side while it is quiet (about 5 squares), jump the trench (2 squares) to the other "
                       f"side in the both-quiet moment, and again; or stand on the thin strip midway between two "
                       f"pushers (0.5 square) through a slam",
                careless="walking down one side: the next slam of that side shoves you into the trench",
                numbers=dict(period=period, stroke=_f(stroke), danger=_f(danger), both_quiet=_f(both_quiet)),
                route=[(1, 3), (L, 3)])


# ---- 07 ----------------------------------------------------------------------------------------------------------

@pattern("push", size=(22, 8), tier="hard", title="Belt and pistons")
def belt_and_pistons(st):
    """A long belt runs toward a trench; pistons in the upstream wall punch out across it on a wave, so the safe
    line against the drift is the line the pistons strike first."""
    L, W = st.L, st.W
    ps = [6, 10, 14]
    carve(st, lanes((0, 2, 0, W), (2, L - 1, 0, 6), (L - 1, L, 0, W), *[(a - 1, a + 1, 6, 8) for a in ps]))
    a0, a1 = 4, 18
    _paint(st, a0, a1, 0, W, BELT)
    pits(st, a0, a1, 0, 2)
    strength = 1.3
    force(st, "B", a0, a1, 0, W, (0, -1), strength, sound="Gear2", tick=60)
    speed, far, home, stagger = 7.0, 4, 35, 20
    path_b = (7.0, 3.5)
    for k, a in enumerate(ps):
        mover(st, f"P{k}", [block(st, a, 7.0, "StoneBlock")], [(a, path_b[0]), (a, path_b[1])], speed, pause=far,
              home_wait=home, armed=k == 0, delay=stagger * k)
        if k:
            st.rest.append((a - 2.0, 5.6))
    stroke = travel([(0, path_b[0]), (0, path_b[1])], speed)
    period = 2 * stroke + far + home
    quiet = home + 2 * (0.12 * SQ / speed)
    lean = (1 - (strength / WALK) ** 2) ** 0.5 * WALK
    cross = 2 * TOUCH * SQ / lean
    return _meta(st, tier="hard",
                tells="a long belt runs into a trench; pistons wait in the wall it runs from",
                answer=f"keep to the wall side leaning into the drift (it pulls {strength} px a frame; leaning you "
                       f"make {lean:.1f}) and wait pressed to the wall between pistons; pass each in its quiet: "
                       f"{quiet / 30:.1f} s every {period / 30:.1f} s against a {cross / 30:.2f} s crossing leaning, "
                       f"{_run(2 * TOUCH) / 30:.2f} s running; the pistons fire as a wave, 0.67 s apart",
                careless="walking the middle: the belt alone carries you into the trench in under 2 s; a piston "
                         "throws anyone it reaches past the middle",
                numbers=dict(strength=strength, stroke=_f(stroke), home=home, period=_f(period), quiet=_f(quiet),
                             cross_lean=_f(cross)),
                route=[(1, 5.6), (L, 5.6)], careless_route=[(1, 4.0), (L, 4.0)])


# ---- 08 ----------------------------------------------------------------------------------------------------------

@pattern("push", size=(24, 8), tier="hard", title="The shove chain")
def shove_chain(st):
    """A ledge above a pit field, its wall a row of stone keys; a tripwire sets them off one after another behind
    you, each as the last lands: run the ledge ahead of the chain."""
    L, W = st.L, st.W
    keys = list(range(4, 21, 2))
    carve(st, lanes((0, 2, 0, W), (2, L - 1, 2, W), (L - 1, L, 0, W), (3, 21, 0, 2)))
    pits(st, 3, L - 2, 4, W)
    speed, hold, start = 6.5, 20, 10
    stroke = travel([(0, 1.0), (0, 3.0)], speed)
    step = _f(stroke)                                          # the next key sets off when this one lands
    acts = [st.act("sound", text="BigGong", src=st.at(3.0, 3.0))]
    movers = []
    for k, a in enumerate(keys):
        mv = mover(st, f"K{k}", [block(st, a, 1.0, "StoneBlock")], [(a, 1.0), (a, 3.0)], speed, pause=hold,
                   armed=False, sound=k % 2 == 0).replace(st.label, "")
        movers.append(mv)
        at = start + step * k
        acts += [st.act("reset", mv), st.act("arm", mv, delay=at),
                 st.act("disarm", mv, delay=at + 2 * step + hold + 3)]
    end = start + step * (len(keys) - 1) + 2 * step + hold + 3
    acts += [st.act("disarm", "Z"), st.act("arm", "Z", delay=end + 60)]
    st.T.zone(f"{st.label}Z", st.at(4.0, 3.0), 46, shape="diamond", who="player", acts=acts)
    reach = 0.77 * SQ / speed
    margin_run = min((start + step * k + reach) - (keys[k] + TOUCH - 3.0) * SQ / RUN for k in range(len(keys)))
    margin_walk = min((start + step * k + reach) - (keys[k] + TOUCH - 3.0) * SQ / WALK for k in range(len(keys)))
    return _meta(st, tier="hard",
                tells="a ledge over pits; its wall is a row of stone keys; a gong when you step on",
                answer=f"run the moment the gong sounds and do not stop: each key slams {step} frames after the "
                       f"last, a wave down the ledge at {2 * SQ / step:.1f} px a frame against your run's 6.9 "
                       f"({margin_run / 30:.2f} s to spare at the closest key); it resets "
                       f"{(end + 60) / 30:.0f} s after it starts",
                careless=f"walking: the wave catches you by the second key ({-margin_walk / 30:.2f} s short) and "
                         f"shoves you off the ledge",
                numbers=dict(step=step, hold=hold, start=start, run_margin=_f(margin_run),
                             walk_margin=_f(margin_walk)),
                route=[(1, 3), (L, 3)])


# ---- 09 ----------------------------------------------------------------------------------------------------------

@pattern("push", size=(22, 10), tier="hard", title="The tilting floor")
def tilting_floor(st):
    """A four-square walkway between two pit fields; the floor drifts one way, rests, drifts the other way, rests."""
    L, W = st.L, st.W
    a0, a1 = 4, 18
    pits(st, a0, a1, 0, 3)
    pits(st, a0, a1, 7, W)
    period, tilt, strength = 130, 55, 1.6
    force(st, "R", a0, a1, 0, W, (0, 1), strength, period=period, on=[(0, tilt)], sound="PushCast")
    force(st, "L", a0, a1, 0, W, (0, -1), strength, period=period, on=[(period // 2, period // 2 + tilt)],
          sound="PushCast")
    force(st, "T", a0, a1, 0, W, (0, 1), 0.0, period=period // 2, on=[(period // 2 - 15, period // 2)],
          sound="GenerateTick")
    drift = strength * tilt / SQ
    lean = (1 - (strength / WALK) ** 2) ** 0.5 * WALK
    st.rest += [(2.0, 5.0), (19.5, 5.0)]
    return _meta(st, tier="hard",
                tells="a walkway between two pit fields; the floor slides one way, then the other",
                answer=f"a tick, then the floor slides toward one pit field for {tilt / 30:.1f} s, rests "
                       f"{(period / 2 - tilt) / 30:.1f} s, slides toward the other, rests: a slide carries a standing "
                       f"player {drift:.1f} squares of the walkway's 4; "
                       f"before each slide step to its uphill edge, or lean into it as you walk (you still make "
                       f"{lean:.1f} px a frame), or jump; ~5 slides to cross",
                careless=f"walking the middle without a thought: the first slide carries you {drift:.1f} squares, "
                         f"past the edge",
                numbers=dict(period=period, tilt=tilt, strength=strength, drift_sq=round(drift, 2),
                             lean=round(lean, 2)),
                route=[(1, 5), (L, 5)])


# ---- 10 ----------------------------------------------------------------------------------------------------------

@pattern("push", size=(44, 8), tier="hard", title="The long fall")
def long_fall(st):
    """A belt, pushers on the beat, a rest, an orb causeway and a gusting ledge, one after another, pits all the way."""
    L, W = st.L, st.W
    ks = [12, 16]
    boxes = [(0, 10, 0, W), (10, 18, 2, 6), (18, 44, 0, W)] + [(a - 1, a + 1, 6, 8) for a in ks]
    carve(st, lanes(*boxes))
    # 1. a belt (a = 3 .. 8) into a chasm on the left
    _paint(st, 3, 8, 0, W, BELT)
    pits(st, 3, 8, 0, 3)
    force(st, "B", 3, 8, 0, W, (0, -1), 1.4, sound="Gear1", tick=60)
    # 2. two stone pushers to a pit row (a = 10 .. 18)
    pits(st, 10, 18, 2, 3)
    speed, far, home = 5.0, 8, 40
    for k, a in enumerate(ks):
        mover(st, f"P{k}", [block(st, a, 7.0, "StoneBlock")], [(a, 7.0), (a, 4.0)], speed, pause=far,
              home_wait=home, armed=k == 0, delay=30 * k)
    p_open = home + 2 * (2.47 * SQ / speed)
    # 3. rest
    st.potion(19.5, 1.0)
    st.potion(19.5, 7.0)
    st.rest.append((19.5, 4.0))
    # 4. an orb causeway (a = 21 .. 31)
    line = [(19, 2), (24, 2), (24, 6), (28, 6), (28, 2), (32, 2)]
    road = _causeway(line)
    pits(st, 21, 31, 0, W, skip=road)
    for k, (a, b) in enumerate([(23.4, 2.6), (24.6, 5.4), (27.4, 5.4), (28.6, 2.6)]):
        bumper(st, f"O{k}", a, b, 40)
    # 5. a gusting ledge along the wall (a = 32 .. 42), a pad halfway
    solid = {(a, b) for a in range(32, 42) for b in range(0, 2)} | {(a, b) for a in range(36, 38) for b in range(0, 4)}
    pits(st, 32, 42, 0, W, skip=solid)
    force(st, "G", 32, 42, 0, W, (0, 1), 2.0, period=90, on=[(0, 30)], sound="PushCast")
    force(st, "T", 32, 42, 0, W, (0, 1), 0.0, period=90, on=[(60, 90)], sound="GenerateTick", tick=15)
    return _meta(st, tier="hard",
                tells="a belt, stone pushers, a rest, an orb causeway and a gusting ledge, over pits",
                answer=f"cross the belt from its upstream edge leaning into it; pass each pusher as it goes home on "
                       f"the pit-side line ({p_open / 30:.1f} s open); drink; take the causeway's bends wide; cross the "
                       f"ledge in the 2 s calms and stand the gust out on the pad against the wall",
                careless="the first chasm, or the next one",
                numbers=dict(pusher_open=_f(p_open)),
                route=[(1, 7.2), (8.5, 7.2), (9.5, 3.3), (18, 3.3), (19.5, 1.6), (24.4, 1.6), (24.4, 3.6),
                       (23.6, 4.6), (23.6, 6.4), (28.4, 6.4), (28.4, 4.4), (27.6, 3.4), (27.6, 1.6), (32, 1.6),
                       (32.5, 0.6), (L, 0.6)],
                careless_route=[(1, 3.0), (L, 3.0)])
