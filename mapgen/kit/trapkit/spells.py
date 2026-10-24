"""Spell traps: the engine's own spells cast by the map's script (kit/behaviours/traps_spell.go) from plates, statues,
hidden points and lights: fists, toxic clouds, fireballs, meteors, death rays, glyphs, and skull guns.

The numbers (gamedata.bin, SOLO; the OpenNox source; rules/traps/ENGINE.md 8, 10, 14):
- a cast from a point is level 1 (one shared invisible caster); from an object, level 3 unless a level is given.
  Fists and meteors are cast from their own objects (a plate, a light): a caster has one of each in the air at once.
- Fist lvl 1: 50 crush in r25, drops ~0.8 s after the cast. Meteor lvl 1: 45 in r80 (full within 30), ~1 s.
  Fireball lvl 1: ~64 and a splash (r64) where it bursts, ~19 units a frame. Death ray: 90 within 10-15 units of its
  point, at once, along a clear line. Toxic cloud: 15 s (the script blows it away sooner), 3-10 poison every 5-10
  frames within 75 units (2.3 squares) and the poison after. Skull gun: a fireball of ~96 along its one diagonal,
  at most one a second, while anyone stands in front of it within 350 units in sight.
- Every spell here hurts more than a spike: a standard station's mistake costs one hit (35-65), never a wizard's
  life from full health; a hard station's careless walk is death.
Movement (rules/TRAPS.md 1): walk 3.3 units a frame (a square in 10 frames), run 6.9, a jump ~3.8 squares.
"""
from kit.trapkit import pattern, Meta, frames, SQ
from kit.trapkit._spelltrig import (light, plate_obj, box_go, start, acts_go, shooter, secret_line, pillar, go_pt,
                                    go_strs, SKULL, VIOLET, RED, ORANGE, GREEN, WHITE, neg)


def _on(st):
    start(st, "SpellTrapsOn()")


def _shot(t, kind="cast", spell="", src="", frm=None, to=None, lvl=0, text="", r=0):
    parts = [f"T: {int(t)}", f'Kind: "{kind}"']
    if spell: parts.append(f'Spell: "{spell}"')
    if src: parts.append(f'Src: "{src}"')
    if frm is not None: parts.append(f"From: {go_pt(frm)}")
    if to is not None: parts.append(f"To: {go_pt(to)}")
    if lvl: parts.append(f"Lvl: {int(lvl)}")
    if text: parts.append(f'Text: "{text}"')
    if r: parts.append(f"R: {float(r):.1f}")
    return "{" + ", ".join(parts) + "}"


def _volley(st, s, period, shots, armed=False):
    """Casts on a clock (a spellVolley), armed by a gate or an action. Returns its name."""
    name = f"{st.label}{s}"
    start(st, f'SpellVolley(spellVolley{{Name: "{name}", Period: {int(period)}, Shots: []spellShot{{'
              + ", ".join(shots) + f"}}, Armed: {str(armed).lower()}}})")
    return name


def _gate(st, s, a0, a1, targets):
    """While a player is between a0 and a1, the targets are armed (a station's spells run only while someone is in
    it: they never fly out into the hall for nothing)."""
    start(st, f'SpellGate(spellGate{{Name: "{st.label}{s}", {box_go(st, a0, a1)}, Targets: {go_strs(targets)}}})')


def _hunt(st, s, a0, a1, spell, frm, period, delay, lvl=0, lead=0, sound="", src="", armed=True):
    name = f"{st.label}{s}"
    start(st, f'SpellHunt(spellHunt{{Name: "{name}", {box_go(st, a0, a1)}, Spell: "{spell}", Src: "{src}", '
              f'From: {go_pt(frm)}, Period: {int(period)}, Delay: {int(delay)}, Lvl: {int(lvl)}, Lead: {int(lead)}, '
              f'Sound: "{sound}", Armed: {str(armed).lower()}}})')
    return name


def _compass(d):
    return {(1, -1): "NE", (1, 1): "SE", (-1, 1): "SW", (-1, -1): "NW"}[(1 if d[0] > 0 else -1, 1 if d[1] > 0 else -1)]


def _statue(st, a, b, face):
    """A victory statue at (a, b) looking along world direction `face` (the visible caster of a death ray)."""
    st.spec.obj_px(f"StatueVictory4{_compass(face)}", *st.at(a, b))


def _lead_fists(st, rows, bs=(0.75, 2.25, 3.75, 5.25), s="P"):
    """Rows of lit plates; a plate drops a fist where its toucher is heading (24 frames on at his pace: the fist's
    fall), then goes dark for 4 s. Each plate casts its own fist (one per caster in the air)."""
    for i, a in enumerate(rows):
        for j, b in enumerate(bs):
            k = f"{s}{i}{j}"
            st.group(f"L{k}", [light(st, a, b, VIOLET, radius=38, intensity=40)])
            fist = st.T.act("cast_mark", plate_obj(st, k), spell="SPELL_FIST", src=st.at(a, b), text="lvl:1 lead:24")
            st.plate(k, a, b, who="creature", acts=[fist, st.act("off", f"L{k}"), st.act("disarm", k),
                                                     st.act("on", f"L{k}", delay=120), st.act("arm", k, delay=120)])


def _vents(st, sets, period, half, s="V"):
    """Gas vents (fire grates) in pairs across the hall; each set's clouds rise in its half of the period and are
    blown away when the next set rises. sets: [[a, ...], [a, ...]] (set 0 first)."""
    pts = [[st.at(a, b) for a in rows for b in (1.5, st.W - 1.5)] for rows in sets]
    for ps in pts:
        for p in ps:
            st.spec.obj_px("FireGrate", *p)
    shots = []
    for k, ps in enumerate(pts):
        t_on = k * half
        t_off = (t_on + half) % period
        for p in ps:
            shots.append(_shot(t_on, spell="SPELL_TOXIC_CLOUD", frm=p, to=p))
            shots.append(_shot(t_off, kind="clear", frm=p, text="ToxicCloud", r=40))
    return _volley(st, s, period, shots)


def _lanes(st, lanes, period, gaps=(0, 8), s="F", lvl=1, sides=None):
    """Fireball lanes across the hall from hidden points by one wall (a red glow) to the other: each lane a burst of
    shots (`gaps`: frames after its moment) at its moment of the period. lanes: [(a, t0)]; sides: 0 (from b = 0) or
    1 per lane."""
    shots = []
    for k, (a, t0) in enumerate(lanes):
        side = (sides[k] if sides else 0)
        b0, b1 = (0.5, st.W - 0.5) if side == 0 else (st.W - 0.5, 0.5)
        p, q = st.at(a, b0), st.at(a, b1)
        light(st, a, b0, RED, radius=34, intensity=50)
        for dt in gaps:
            shots.append(_shot((t0 + dt) % period, spell="SPELL_FIREBALL", frm=p, to=q, lvl=lvl))
    return _volley(st, s, period, shots)


def _gas_plate(st, k, a, b, who="creature"):
    """A plate that raises a toxic cloud on itself 0.4 s after it is trodden, blown away 3.5 s later; re-arms at 5 s."""
    c = st.at(a, b)
    st.plate(k, a, b, who=who, acts=[
        st.T.act("cast_lvl", spell="SPELL_TOXIC_CLOUD", src=c, dst=c, delay=12),
        st.T.act("spell_clear", src=c, frames=40, text="ToxicCloud", delay=12 + 105),
        st.act("disarm", k), st.act("arm", k, delay=150)])


# ---- the stations ---------------------------------------------------------------------------------------------

@pattern("spell", size=(22, 6), title="Fist plates")
def fist_plates(st):
    _on(st)
    _lead_fists(st, (5.0, 8.5, 12.0, 15.5))
    for a in (6.75, 10.25, 13.75):
        st.rest.append((a, st.W / 2))
    return Meta(tier="standard", tells="four rows of plates, each lit violet; a plate's light goes out when it fires",
                answer="tread a plate and stop (or turn aside) at once: the fist falls 0.8 s later where you were "
                       "heading, two squares on; or jump each row (a jump passes over plates)",
                careless="walking on at an even pace: every row drops a fist on you, 50 HP each (crush), 200 in all",
                mistake="50 HP (one fist)")


@pattern("spell", size=(24, 6), title="Gas vents")
def gas_vents(st):
    _on(st)
    v = _vents(st, [[6.0, 18.0], [12.0]], period=180, half=90)
    _gate(st, "G", 1.0, st.L - 0.3, [v])
    for a in (9.0, 15.0):
        st.rest.append((a, st.W / 2))
    return Meta(tier="standard", tells="three pairs of vents; the outer pairs and the middle pair breathe green gas "
                                       "in turn, 3 s each, the old cloud blown away as the new one rises",
                answer="wait at the edge of a cloud; when it blows away, walk to the clean air between the vents "
                       "(2.5 squares) and wait for the next to clear: 3 s for each 6-square leg",
                careless="walking through at an even pace meets one or two clouds: 30-40 HP each, then the poison",
                mistake="a few ticks at a cloud's edge: 10-25 HP and the poison")


@pattern("spell", size=(24, 6), title="Fireball crossing")
def fireball_crossing(st):
    _on(st)
    v = _lanes(st, [(6.0, 0), (9.5, 12), (13.0, 24), (16.5, 36)], period=48, gaps=(0, 7, 14))
    _gate(st, "G", 1.0, st.L - 0.3, [v])
    for a in (7.75, 11.25, 14.75):
        st.rest.append((a, st.W / 2))
    return Meta(tier="standard", tells="four red glows low on the left wall; each throws three fireballs across the "
                                       "hall every 1.6 s, the lanes a quarter of a beat apart",
                answer="stand between lanes, watch the next lane fire its three, cross it at once (0.9 s before the "
                       "next three); cross near the glows: the fireballs burst on the far wall",
                careless="walking through on no beat: two lanes in five catch you, ~64 HP a fireball",
                mistake="one fireball: ~64 HP")


@pattern("spell", size=(24, 6), title="Falling stars")
def falling_stars(st):
    _on(st)
    # each row's two stars fall when someone comes at the row at a pace that brings him to it within their fall
    # (~32 frames: a walker 3.2 squares off, a runner 6.8), so they burst as he arrives; then the row gathers 3.3 s
    for k, a in enumerate((6.0, 12.0, 18.0)):
        shots = []
        for b in (1.3, st.W - 1.3):
            lt = light(st, a, b, ORANGE, radius=52, intensity=55)
            shots.append(_shot(0, spell="SPELL_METEOR", src=lt, frm=st.at(a, b), to=st.at(a, b), lvl=1))
        a0 = max(0.5, a - 8.0)
        start(st, f'SpellAhead(spellAhead{{Name: "{st.label}R{k}", {box_go(st, a0, a)}, Row: {(a - a0) / 2 * SQ:.1f}, '
                  f'Fall: 32, Cool: 100, Shots: []spellShot{{' + ", ".join(shots) + "}})")
    for a in (9.0, 15.0):
        st.rest.append((a, st.W / 2))
    return Meta(tier="standard", tells="three rows of orange-lit spots; a row's stars fall when you come at it and burst "
                                       "2.5 squares around it as you would arrive",
                answer="walk at a row and stop short when its stars fall (you hear them, 1 s before they land); when "
                       "they burst, cross at once: the row gathers for 3 s. Standing or stepping sideways never "
                       "wakes it",
                careless="walking or running on: every row bursts round you, ~45 HP each",
                mistake="one row: 20-45 HP")


@pattern("spell", size=(22, 6), title="Gas plates")
def gas_plates(st):
    _on(st)
    bs = (0.75, 2.25, 3.75, 5.25)
    gaps = (3, 0, 2, 1, 3)
    for i, a in enumerate((5.5, 8.5, 11.5, 14.5, 17.5)):
        for j, b in enumerate(bs):
            if j != gaps[i]:
                _gas_plate(st, f"P{i}{j}", a, b)
    for a in (7.0, 10.0, 13.0, 16.0):
        st.rest.append((a, st.W / 2))
    return Meta(tier="standard", tells="five rows of plates, one gap in each, never in line",
                answer="weave through the gaps (or jump a row): a trodden plate breathes a toxic cloud on itself "
                       "0.4 s later for 3.5 s",
                careless="walking straight: four plates, four clouds around you, ~60 HP and the poison",
                mistake="one plate: step on through its cloud, 15-25 HP and the poison")


@pattern("spell", size=(24, 6), tier="hard", title="Glyphs and the warden")
def glyph_field(st):
    _on(st)
    bs = (0.6, 1.8, 3.0, 4.2, 5.4)                           # 1.2 squares apart: no way between two (20 px each)
    gaps = (1, 4, 0, 3)
    for i, a in enumerate((6.0, 9.5, 13.0, 16.5)):           # rows 3.5 squares apart: a row's chain stays in it
        for j, b in enumerate(bs):
            if j == gaps[i]:
                continue
            x, y = st.at(a, b)
            g = st.T.obj("Glyph", x, y, name=st.nm("Glyph"),
                         xfer={"Angle": 0, "TargX": int(x), "TargY": int(y),
                               "Spells": ["SPELL_SLOW", "SPELL_TOXIC_CLOUD"]})
            light(st, a, b, VIOLET, radius=26, intensity=35)
            start(st, f'SpellGlyph("{g}", 2, "SPELL_SLOW", "SPELL_TOXIC_CLOUD")')
            # the script's copy of the glyph's touch (UNCONFIRMED in alpha13): a jump passes over it, as over a glyph
            st.T.zone(f"{st.label}Z{i}{j}", (x, y), 20.0, shape="circle", who="player", jump=True, once=True,
                      acts=[st.T.act("spell_glyph", g)])
    # the warden: a statue at the far end that rays where you stood 0.5 s before, every 1.5 s, while you are among
    # the glyphs (the second threat: keep moving)
    _statue(st, st.L - 0.7, st.W / 2, neg(st.along()))
    _hunt(st, "H", 4.0, 18.5, "SPELL_DEATH_RAY", st.at(st.L - 1.6, st.W / 2), period=45, delay=15, sound="ManaClick")
    return Meta(tier="hard", tells="four rows of faint violet runes (glyphs) wall to wall, one gap in each, never in "
                                   "line; a statue at the end that clicks where you stand and rays that spot half a "
                                   "second later",
                answer="weave through the gaps or jump a row, and never stand still for half a second among the "
                       "glyphs: the warden rays every 1.5 s where you stood",
                careless="treading a glyph sets off its row: slowed, in four toxic clouds for 15 s, 60-100 HP; "
                         "stopping to think: 90 HP a ray",
                mistake="one row of glyphs (~50 HP and the poison) or one ray (90)",
                uncertain="the engine's glyph touch did not fire on the bench; the script fires each glyph itself "
                          "(a zone on it) unless the engine already has")


@pattern("spell", size=(26, 6), tier="hard", title="The statues lead")
def statues_lead(st):
    _on(st)
    srcs = []
    for a, side in ((9.0, 0), (13.0, 1), (17.0, 0)):
        b, bf = (0.55, 1.6) if side == 0 else (st.W - 0.55, st.W - 1.6)
        face = st.across() if side == 0 else neg(st.across())
        _statue(st, a, b, face)
        srcs.append(st.at(a, bf))
    turn = f"{st.label}T"
    start(st, f"SpellTurn(\"{turn}\", " + ", ".join(go_pt(p) for p in srcs) + ")")
    bs = (0.75, 2.25, 3.75, 5.25)
    a = 5.0
    i = 0
    while a <= 19.01:
        for j, b in enumerate(bs):
            st.plate(f"P{i}{j}", a, b, who="creature",
                     acts=[st.T.act("cast_mark", turn, spell="SPELL_DEATH_RAY", frames=24, text="lead:24")])
        a += 2.2
        i += 1
    return Meta(tier="hard", tells="seven rows of plates between three statues; each tread makes the next statue ray "
                                   "the spot where you will be 0.8 s on",
                answer="every time a plate clicks, stop dead or turn: the ray lands where you were heading, two "
                       "squares on; step, stop, step; or jump a row and stop where you land",
                careless="walking on: a 90 HP ray each tread, dead by the second plate",
                mistake="one ray: 90 HP")


@pattern("spell", size=(24, 6), tier="hard", title="The skull gallery")
def skull_gallery(st):
    across, back = st.across(), neg(st.along())
    side_gun = shooter(st, SKULL, across)
    end_gun = shooter(st, SKULL, back)
    guns = [st.obj(side_gun, 6.0 + 1.5 * k, 0.4, enabled=False) for k in range(9)]
    guns += [st.obj(end_gun, st.L - 0.4, b, enabled=False) for b in (1.5, st.W - 1.5)]
    st.group("G", guns)
    bs = (0.75, 2.25, 3.75, 5.25)
    gaps = (2, 0, 3, 1, 2)
    # awake, the end also throws a fireball at where you stand every second (it bites at any moment; strafe)
    _on(st)
    eye = _hunt(st, "E", 2.0, st.L - 1.5, "SPELL_FIREBALL", st.at(st.L - 1.0, st.W / 2), period=30, delay=0, lvl=1,
                sound="FireballCast", armed=False)
    wake = [st.act("on", "G"), st.act("sound", text="BigGong", src=st.at(3.0, st.W / 2)),
            st.T.act("spell_arm", eye), st.act("off", "G", delay=150), st.T.act("spell_disarm", eye, delay=150)]
    for i, a in enumerate((5.5, 8.5, 11.5, 14.5, 17.5)):
        for j, b in enumerate(bs):
            if j != gaps[i]:
                st.plate(f"P{i}{j}", a, b, who="creature", acts=list(wake))
    return Meta(tier="hard", tells="nine skull guns along the left wall and two at the end, asleep; five rows of "
                                   "plates, one gap in each",
                answer="weave through the gaps without a single tread; if a plate wakes the guns (a gong), go sideways "
                       "between their lines for the 5 s they fire: the side guns shoot straight across every 1.5 "
                       "squares, all together once a second, and the end throws a fireball at where you stand each "
                       "second (moving across its line makes it miss)",
                careless="treading a plate wakes the gallery for 5 s: walking or running on toward the end takes its "
                         "fireballs head on, ~64 each, and the side guns' (~96)",
                mistake="one tread: 5 s of crossfire, 64-190 HP unless you strafe between the lines")


@pattern("spell", size=(22, 6), tier="hard", title="The sealed fire room")
def sealed_room(st):
    _on(st)
    back = secret_line(st, 3, state="open")
    front = secret_line(st, 19, state="open")
    v = _lanes(st, [(7.0, 0), (10.0, 11), (13.0, 22), (16.0, 33)], period=45, gaps=(0, 7), s="F", sides=(0, 1, 0, 1))
    across, down = st.across(), neg(st.along())
    guns = [st.obj(shooter(st, SKULL, down), 17.9, b, enabled=False) for b in (1.0, st.W / 2, st.W - 1.0)]
    guns += [st.obj(shooter(st, SKULL, across), a, 0.4, enabled=False) for a in (4.6, 8.5, 12.5)]
    st.group("G", guns)
    wires = [f"W{j}" for j in range(4)]
    count = f"{st.label}C"
    shut = [st.act("walls_open", walls=back + front, delay=150), st.act("off", "G", delay=150)]
    rearm = [st.act("arm", w, delay=240) for w in wires]
    expire = [st.act("on", "G"), st.T.act("spell_disarm", v), st.act("sound", text="BigGong", src=st.at(11, 3))] \
        + shut + rearm
    start(st, f'TrigCountdown(trigCount{{Name: "{count}", Ticks: 10, Every: 30, Sound: "GenerateTick", '
              f'At: {go_pt(st.at(11, st.W / 2))}, Acts: {acts_go(st, expire)}}})')
    seal = [st.act("walls_close", walls=back + front), st.T.act("spell_arm", v), st.T.act("trig_count", count),
            st.act("sound", text="BigGong", src=st.at(5, st.W / 2))] + [st.act("disarm", w) for w in wires]
    for j, b in enumerate((0.75, 2.25, 3.75, 5.25)):
        st.plate(wires[j], 4.6, b, who="player", visible=False, acts=list(seal))
    done = [st.T.act("trig_cancel", count), st.T.act("spell_disarm", v), st.act("off", "G"),
            st.act("walls_open", walls=back + front), st.act("sound", text="Chime", src=st.at(17.5, st.W - 0.6))] \
        + [st.act("arm", w, delay=150) for w in wires]
    st.lever("L", "FloorLever1", 17.6, st.W - 0.55, acts=list(done), release=list(done))
    st.rest.append((17.6, st.W - 1.2))
    return Meta(tier="hard", tells="a room whose doorways close behind you (a gong) and a clock that ticks ten times; "
                                   "four fireball lanes across it on a fast beat; a lever in the far corner; sleeping "
                                   "skull guns",
                answer="cross the lanes on their beat (each fires a pair every 1.5 s) and pull the lever within 10 s: "
                       "the lanes stop and both ways open; at the tenth tick the skull guns fire for 5 s, then the "
                       "room opens",
                careless="walking the lanes on no beat: a fireball or two (64 each); dawdling: 5 s of skull guns",
                mistake="one fireball (~64), or the guns (96 a hit) if the clock runs out")


@pattern("spell", size=(44, 6), tier="hard", title="The long run")
def long_run(st):
    _on(st)
    # 1. fists that lead you
    _lead_fists(st, (4.5, 8.0), s="P")
    st.potion(10.3, 0.5)
    st.rest.append((10.5, st.W / 2))
    # 2. gas vents in turn
    v = _vents(st, [[13.0], [18.0]], period=150, half=75, s="V")
    _gate(st, "GV", 11.0, 21.0, [v])
    st.rest.append((15.5, st.W / 2))
    st.potion(21.3, 0.5)
    # 3. the fire-eye: a statue at the end of the stage throws a fireball at where you stand every 1.3 s
    _statue(st, 32.6, st.W / 2, neg(st.along()))
    _hunt(st, "E", 22.0, 31.0, "SPELL_FIREBALL", st.at(31.8, st.W / 2), period=40, delay=0, lvl=1,
          sound="FireballCast")
    st.potion(33.6, 0.5)
    # 4. the statues lead
    srcs = []
    for a, side in ((36.5, 0), (39.5, 1)):
        b, bf = (0.55, 1.6) if side == 0 else (st.W - 0.55, st.W - 1.6)
        _statue(st, a, b, st.across() if side == 0 else neg(st.across()))
        srcs.append(st.at(a, bf))
    turn = f"{st.label}T"
    start(st, f"SpellTurn(\"{turn}\", " + ", ".join(go_pt(p) for p in srcs) + ")")
    for i, a in enumerate((35.0, 37.2, 39.4, 41.6)):
        for j, b in enumerate((0.75, 2.25, 3.75, 5.25)):
            st.plate(f"R{i}{j}", a, b, who="creature",
                     acts=[st.T.act("cast_mark", turn, spell="SPELL_DEATH_RAY", frames=24, text="lead:24")])
    return Meta(tier="hard", tells="lit fist plates, vents breathing in turn, a statue that throws fireballs, then a "
                                   "floor of plates between ray statues; red potions between the stages",
                answer="tread and stop on the fist rows; cross the vents when they clear; zigzag toward the fire-eye "
                       "(it throws at where you stand now: moving across its line, never along it, makes it miss); "
                       "step and stop on the ray plates",
                careless="several hundred HP: no class walks it",
                mistake="50 (a fist), 30 (a cloud), 64 (a fireball), 90 (a ray)")
