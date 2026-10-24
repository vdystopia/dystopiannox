"""Triggers: how traps are switched on and off (the user's step 2: switches, pressure plates, motion detection, other
conditions). Each station is a small trap built round one kind of trigger, plainly signposted; the effects are plain
ones (arrows, flames, spikes, secret walls) so the trigger is what the player learns.

Engine facts (rules/TRAPS.md, rules/traps/ENGINE.md 11): a visible plate is skipped by a jump, an invisible trigger
catches jumpers; plates are zones the script polls (players every frame; with who=creature, monsters every third);
a lever flips when the player steps up to it (or clicks it), and again only after he steps away; an arrow trap
switched on fires at once at anyone in front of it (one arrow, 25 impale) and then once a second while it is on.
Watchers of the kind's own (kit/behaviours/traps_trigger.go): hold rows, the motion eye, latched N-of-M sets,
countdowns, death watches.
Movement (rules/TRAPS.md 1): walk 3.3 units a frame (a square in 10 frames), run 6.9, a jump ~3.8 squares.
"""
from kit.trapkit import pattern, Meta, frames, SQ
from kit.trapkit._spelltrig import (light, box_go, start, acts_go, shooter, secret_line, go_pt, go_strs, creature,
                                    ARROW, BLUE, GREEN, WHITE, neg)

ROW_GAP = 0.62
PLATES = (0.75, 2.25, 3.75, 5.25)       # four plates fill a 6-square hall (a plate's zone reaches 0.87 each way)


def _arrows_across(st, a, offs=(-0.6, 0.0, 0.6)):
    """Arrow traps in a side wall shooting across the hall along a + off (the lines 0.6 apart leave no gap): in
    the left wall if a trap faces that way, else in the right."""
    t = shooter(st, ARROW, st.across())
    b = 0.4
    if t is None:
        t, b = shooter(st, ARROW, neg(st.across())), st.W - 0.4
    return [st.obj(t, a + o, b, enabled=False) for o in offs]


def _arrows_down(st, a, bs):
    """Arrow traps at a shooting back down the hall (toward the way in) along each b; from the other end if no
    trap faces that way."""
    t = shooter(st, ARROW, neg(st.along()))
    if t is None:
        return []
    return [st.obj(t, a, b, enabled=False) for b in bs]


def _fire(st, s, a0, a1, enabled=True, gap=0.5, flame="LargeFlame"):
    """A band of standing flames across the hall, rows `gap` apart (LargeFlame: 2 HP a frame each)."""
    b0, b1 = 0.4, st.W - 0.4
    n = int(round((b1 - b0) / ROW_GAP)) + 1
    names, a = [], a0
    while a <= a1 + 1e-6:
        names += [st.obj(flame, a, b0 + (b1 - b0) * k / (n - 1), enabled=enabled) for k in range(n)]
        a += gap
    return st.group(s, names)


def _short(st, g):
    return g.replace(st.label, "", 1)


# ---- the stations ---------------------------------------------------------------------------------------------

@pattern("trigger", size=(22, 6), title="Plates and lanes")
def plates_and_lanes(st):
    gaps = (3, 0, 3)
    for i, a in enumerate((6.0, 10.5, 15.0)):
        st.group(f"A{i}", _arrows_across(st, a))
        for j, b in enumerate(PLATES):
            if j != gaps[i]:
                st.plate(f"P{i}{j}", a, b, who="creature", acts=[st.act("pulse", f"A{i}", frames=2)])
        st.rest.append((a + 2.25, st.W / 2))
    return Meta(tier="standard", trigger="pressure plate (players and monsters)",
                tells="three rows of plates across the hall, a gap in each (right, left, right); arrow slits in the "
                      "left wall beside each row",
                answer="walk through the gaps: a plate fires its row's arrows across the hall at once (monsters "
                       "chasing you set them off too)",
                careless="straight down the middle: three plates, 25-50 HP each",
                mistake="one plate: 25-50 HP")


@pattern("trigger", size=(22, 6), title="Step off")
def step_off(st):
    for i, a in enumerate((6.0, 13.0)):
        f = _short(st, _fire(st, f"F{i}", a + 1.2, a + 2.4, enabled=False))
        for j, b in enumerate(PLATES):
            st.plate(f"P{i}{j}", a, b, who="player",
                     release=[st.act("on", f, delay=5), st.act("off", f, delay=5 + 60)])
        st.rest.append((a + 4.0, st.W / 2))
    return Meta(tier="standard", trigger="plate released (step-off)",
                tells="two rows of plates wall to wall, each with a line of dead fire just beyond it",
                answer="treading a plate does nothing; stepping OFF it lights the fire ahead 0.15 s later for 2 s: "
                       "jump from the plate (a jump clears the fire) or run off it",
                careless="walking off the plate into the fire: 40-70 HP a row",
                mistake="a slow run off the plate: 10-20 HP")


@pattern("trigger", size=(22, 6), title="Hold the row")
def hold_row(st):
    for i, a in enumerate((7.0, 14.0)):
        g = st.group(f"A{i}", _arrows_across(st, a))
        zones = []
        for j, b in enumerate(PLATES):
            zones.append(st.plate(f"P{i}{j}", a, b, who="creature"))
        start(st, f'TrigHold(trigHold{{Name: "{st.label}H{i}", Group: "{g}", Zones: {go_strs(zones)}, Delay: 8}})')
        st.rest.append((a + 3.5, st.W / 2))
    return Meta(tier="standard", trigger="hold (on while anyone stands on the row)",
                tells="two rows of plates wall to wall; arrow slits in the left wall beside each",
                answer="the arrows fire from 0.25 s after anyone (or anything) steps on a row until the row is "
                       "empty, once a second: run across in one go or jump the row; never stop or fight on it",
                careless="walking across: 25-50 HP a row; standing on it: 25-75 HP a second",
                mistake="a walk across one row: 25-50 HP")


@pattern("trigger", size=(22, 6), title="The hidden wire")
def hidden_wire(st):
    a_plate, a_wire = 7.0, 9.8
    st.group("AP", _arrows_across(st, a_plate))
    st.group("AW", _arrows_across(st, a_wire))
    for j, b in enumerate(PLATES[:3]):                      # the gap: the square by the right wall
        st.plate(f"P{j}", a_plate, b, who="creature", acts=[st.act("pulse", "AP", frames=2)], rearm=20)
        st.plate(f"W{j}", a_wire, b, who="creature", visible=False, acts=[st.act("pulse", "AW", frames=2)], rearm=20)
    st.rest.append((13.0, st.W / 2))
    return Meta(tier="standard", trigger="invisible trigger (catches jumpers)",
                tells="a row of plates with a gap by the right wall; arrow slits in the left wall at the plates and "
                      "again three squares beyond them, where nothing shows on the floor",
                answer="walk the gap by the right wall and keep to that side until past the second slits: a hidden "
                       "wire lies across the rest of the hall where a jump over the plates comes down",
                careless="walking the middle: the plates' arrows, then the wire's, 50-100 HP; jumping the plates: "
                         "the wire's arrows hit you in the air, 25-50",
                mistake="one volley: 25-50 HP")


@pattern("trigger", size=(24, 6), title="Switchback levers")
def switchback(st):
    a = _short(st, _fire(st, "A", 6.0, 11.0, enabled=True))
    b = _short(st, st.carpet("B", 14.0, 19.0, 0.35, st.W - 0.35, enabled=False))
    st.lever("L1", "FloorLever1", 4.6, 0.55, acts=[st.act("off", a), st.act("on", b)],
             release=[st.act("on", a), st.act("off", b)])
    st.lever("L2", "FloorLever2", 12.5, st.W - 0.55, acts=[st.act("off", b), st.act("on", a)],
             release=[st.act("on", b), st.act("off", a)])
    st.rest.append((12.5, st.W / 2))
    return Meta(tier="standard", trigger="levers (off and on)",
                tells="a hall of fire, then a bed of sunken spikes; a lever before the fire (left) and one between "
                      "them (right)",
                answer="the first lever puts the fire out and raises the spikes; cross, pull the second: the spikes "
                       "sink and the fire behind you comes back. Each lever flips back if touched again",
                careless="walking into the fire: five squares of it, 100+ HP",
                mistake="pulling the wrong way and stepping on: a step of fire or spikes, 10-30 HP")


@pattern("trigger", size=(22, 6), title="Race the gate")
def race_gate(st):
    gate = secret_line(st, 17, state="closed")
    st.carpet("S", 9.0, 11.0, 0.35, st.W - 0.35, enabled=True)
    clock = f"{st.label}C"
    start(st, f'TrigCountdown(trigCount{{Name: "{clock}", Ticks: 9, Every: 30, Faster: true, Sound: "Gear1", '
              f'At: {go_pt(st.at(16.0, st.W / 2))}, Acts: {acts_go(st, [st.act("walls_close", walls=gate)])}}})')
    press = [st.act("walls_open", walls=gate), st.T.act("trig_count", clock)]
    st.lever("B", "Button2", 3.4, 0.45, acts=list(press), release=list(press))
    st.rest.append((13.5, st.W / 2))
    return Meta(tier="standard", trigger="button with a timer",
                tells="a button by the left wall, a strip of standing spikes, a closed wall across the hall beyond",
                answer="press the button: the wall slides open for 7 s while gears tick (faster at the end); jump the "
                       "spikes and walk through. If it shuts, walk back and press again",
                careless="walking into the spikes: two squares, ~100 HP",
                mistake="a short jump onto the spikes' edge: 10-25 HP")


@pattern("trigger", size=(24, 6), tier="hard", title="Hold still")
def hold_still(st):
    lamps = [st.obj("MediumBlueFlame", 19.7, 0.35, enabled=False),
             st.obj("MediumBlueFlame", 19.7, st.W - 0.35, enabled=False),
             light(st, 12.0, st.W / 2, BLUE, radius=150, intensity=55, enabled=False)]
    g = st.group("E", lamps)
    st.spec.obj_px("StatueVictory4" + {(1, -1): "NE", (1, 1): "SE", (-1, 1): "SW", (-1, -1): "NW"}[
        tuple(1 if v > 0 else -1 for v in neg(st.along()))], *st.at(st.L - 0.7, st.W / 2))
    ray = st.act("cast_at_caller", spell="SPELL_DEATH_RAY", src=st.at(st.L - 1.6, st.W / 2))
    start(st, f'TrigEye(trigEye{{Name: "{st.label}Eye", {box_go(st, 4.5, 19.5)}, Lamps: "{g}", Period: 120, '
              f'Open: 45, Grace: 12, Thresh: 4.0, Cool: 30, Sound: "Chime", Acts: {acts_go(st, [ray])}, Armed: true}})')
    return Meta(tier="hard", trigger="motion detection",
                tells="a statue at the end of the hall; every 4 s a chime and blue lamps light for 1.5 s",
                answer="move only while the lamps are dark; at the chime stop dead (0.4 s): anything that moves in "
                       "the hall while they burn is rayed. 14 squares need one stop on the way",
                careless="walking on through a lit spell: a 90 HP ray, and another a second later",
                mistake="a late stop: 90 HP")


@pattern("trigger", size=(22, 6), tier="hard", title="Locked in")
def locked_in(st):
    back = secret_line(st, 3, state="open")
    front = secret_line(st, 18, state="open")
    m = st.W / 2
    q1 = st.carpet("Q1", 5.0, 11.0, 0.35, m, enabled=False)
    q2 = st.carpet("Q2", 5.0, 11.0, m, st.W - 0.35, enabled=False)
    q3 = st.carpet("Q3", 11.0, 17.0, m, st.W - 0.35, enabled=False)
    q4 = st.carpet("Q4", 11.0, 17.0, 0.35, m, enabled=False)
    p13 = st.group("P13", st.T.groups.pop(q1) + st.T.groups.pop(q3))
    p24 = st.group("P24", st.T.groups.pop(q2) + st.T.groups.pop(q4))
    c13 = st.clock("C13", p13, 140, [(0, 60)], armed=False)
    c24 = st.clock("C24", p24, 140, [(70, 130)], armed=False)
    clocks = [_short(st, c13), _short(st, c24)]
    wires = [f"W{j}" for j in range(4)]
    count = f"{st.label}C"
    end = [st.act("disarm", c) for c in clocks] + [st.act("walls_open", walls=back + front)] \
        + [st.act("arm", w, delay=150) for w in wires]
    start(st, f'TrigCountdown(trigCount{{Name: "{count}", Ticks: 12, Every: 30, Sound: "GenerateTick", '
              f'At: {go_pt(st.at(11.0, m))}, Acts: {acts_go(st, end)}}})')
    seal = [st.act("walls_close", walls=back + front), st.T.act("trig_count", count),
            st.act("sound", text="BigGong", src=st.at(4.5, m))] + [st.act("disarm", w) for w in wires] \
        + [st.act("arm", c, delay=20) for c in clocks]
    for j, b in enumerate(PLATES):
        st.plate(wires[j], 4.6, b, who="player", visible=False, acts=list(seal))
    done = [st.T.act("trig_cancel", count), st.act("sound", text="Chime", src=st.at(16.4, st.W - 0.6))] + end
    st.lever("L", "FloorLever1", 16.4, st.W - 0.55, acts=list(done), release=list(done))
    st.rest.append((3.8, m))
    return Meta(tier="hard", trigger="lock-in with a countdown (and a lever that ends it)",
                tells="a room whose doorways slam shut as you enter (a gong), a clock ticking twelve times, a floor of "
                      "four spike quarters, a lever in the far right corner",
                answer="opposite quarters rise together and swap every 2.3 s with a third of a second all down: stand "
                       "by a corner where four quarters meet and step across at each swap, working toward the lever "
                       "(it stops the spikes and opens the room); or wait out the 12 ticks in the strip by the door",
                careless="walking in: a quarter rises under you within 2 s, ~5 HP a frame till you get off",
                mistake="a late step at a swap: 20-50 HP")


@pattern("trigger", size=(22, 6), tier="hard", title="All at once")
def all_at_once(st):
    gate = secret_line(st, 19, state="closed")
    st.carpet("S", 7.0, 14.5, 1.9, st.W - 1.9, enabled=True)
    spots = [(5.5, 0.9), (16.0, 0.9), (16.0, st.W - 0.9)]
    keys, lamps = [], []
    for k, (a, b) in enumerate(spots):
        lamps.append(st.group(f"L{k}", [light(st, a, b, GREEN, radius=48, intensity=60, enabled=False),
                                        st.obj("SmallBlueFlame", a + 0.75, b, enabled=False)]))
        keys.append(st.plate(f"P{k}", a, b, who="creature",
                             acts=[st.T.act("trig_latch", f"{st.label}N", text=f"{st.label}P{k}")]))
    win = [st.act("walls_open", walls=gate), st.act("sound", text="Chime", src=st.at(18.0, st.W / 2))]
    start(st, f'TrigLatchSet(trigLatch{{Name: "{st.label}N", Keys: {go_strs(keys)}, Lamps: {go_strs(lamps)}, '
              f'Window: 120, Sound: "SwitchToggle", Acts: {acts_go(st, win)}}})')
    return Meta(tier="hard", trigger="N of M plates (all three at once)",
                tells="a closed wall at the far end, a bed of standing spikes in the middle, three plates in the "
                      "corners round it",
                answer="each plate lights its lamp for 4 s; all three lit at once opens the wall: tread the near "
                       "plate and run round the spikes to the far two (a walk is too slow)",
                careless="cutting across the spikes: 7 squares of them, death",
                mistake="clipping the spikes' edge on the run: 10-30 HP")


@pattern("trigger", size=(44, 6), tier="hard", title="Guard, key and combination")
def guard_key_combination(st):
    m = st.W / 2
    # 1. the guard: kill it and the first gate opens; the plates before it are shared with monsters
    g1 = secret_line(st, 12, state="closed")
    st.group("A", _arrows_across(st, 6.5))
    for j, b in enumerate(PLATES):
        st.plate(f"P{j}", 6.5, b, who="creature", acts=[st.act("pulse", "A", frames=2)], rearm=20)
    guard, _ = creature(st, "Skeleton", 10.0, m, face=(0.0, m))
    start(st, f'TrigDeath(trigDeath{{Name: "{st.label}D", Obj: "{guard}", Acts: '
              f'{acts_go(st, [st.act("walls_open", walls=g1), st.act("sound", text="Chime", src=st.at(11.5, m))])}}})')
    st.potion(12.6, 0.5)
    # 2. the key: lift it and the far wall rises section by section, left to right, a section a 0.67 s; sealed in,
    # the arrows fire for 2 s before it opens again
    g2 = secret_line(st, 24, state="open")
    key = st.obj("SilverKey", 17.0, m)
    k = st.group("K", _arrows_down(st, 23.6, [0.6 + 0.6 * i for i in range(9)]))
    lift = [st.act("walls_close", walls=[c], delay=20 * (i + 1)) for i, c in enumerate(g2)]
    lift += [st.act("sound", text="GenerateTick", src=st.at(22.0, m), delay=d) for d in (0, 20, 40, 60, 80)]
    lift += [st.act("on", _short(st, k), delay=20 * len(g2) + 5), st.act("off", _short(st, k), delay=20 * len(g2) + 65),
             st.act("walls_open", walls=g2, delay=20 * len(g2) + 70)]
    st.T.watch(f"{st.label}KeyW", key, acts=lift)
    st.potion(24.6, 0.5)
    # 3. the combination: three bands of fire, six squares in all (no jump clears it); three levers, each toggling
    # some of them: L1 the first two, L2 the last two, L3 the first
    bands = [_short(st, _fire(st, n, a0, a0 + 1.5)) for n, a0 in (("BA", 30.5), ("BB", 32.5), ("BC", 34.5))]
    for bnd in bands:
        start(st, f'trapSetGroup("{st.label}{bnd}", true)')
    for name, a, side, which in (("L1", 26.0, 0, (0, 1)), ("L2", 27.0, 1, (1, 2)), ("L3", 28.0, 0, (0,))):
        flip = [st.act("toggle", bands[w]) for w in which]
        st.lever(name, "FloorLever1", a, 0.55 if side == 0 else st.W - 0.55, acts=list(flip), release=list(flip))
    st.rest.append((29.0, m))
    return Meta(tier="hard", trigger="a creature's death, an item lifted, a combination of levers (and plates monsters "
                                     "press)",
                tells="a skeleton behind a row of plates and a closed wall; a silver key before an open wall; three "
                      "levers before a hall of fire",
                answer="fight the skeleton off the plates (its tread fires the arrows too): its death opens the wall. "
                       "Take the key and walk at once to the right of the far wall (it rises left to right, a section "
                       "every 0.67 s). Pull the levers and watch the fire: L2 and L3 put all of it out",
                careless="fighting on the plates: 25-50 HP a volley; dawdling with the key: sealed in with 2 s of "
                         "arrows, 50-100; walking into the fire: six squares of it, death",
                mistake="a volley (25-50) or a lever pulled wrong (no harm: watch the fire)")
