"""Fire: flame jets over fire grates (FireGrateFlame, 5 HP a frame), standing flames (Flame 1, LargeFlame 2 a frame),
switched instantly by the script (fire is the one class ObjectOff fully disables), and blue flames that drain mana.
A jump clears any flame (rules/TRAPS.md 1): a strip of fire two squares deep is the classic jump.
"""
from kit.trapkit import pattern, Meta, frames

ROW_GAP = 0.62           # squares between flames across a row (20 px: a player cannot slip between)


def _grates(st, s, a, enabled=False, flame="FireGrateFlame", grate=True, b0=0.4, b1=None):
    """A row of fire grates across the station at `a`, each with its flame (a group)."""
    b1 = st.W - 0.4 if b1 is None else b1
    names = []
    n = max(2, int(round((b1 - b0) / ROW_GAP)) + 1)
    for k in range(n):
        b = b0 + (b1 - b0) * k / (n - 1)
        if grate and k % 2 == 0:
            st.obj("FireGrate", a, b)
        names.append(st.obj(flame, a, b, enabled=enabled))
    return st.group(s, names)


def _field(st, s, a0, a1, flame="LargeFlame", enabled=True, gap=0.5, b0=0.4, b1=None):
    """A field of standing flames, rows `gap` squares apart (a strip to jump, or to put out)."""
    b1 = st.W - 0.4 if b1 is None else b1
    names = []
    a = a0
    while a <= a1 + 1e-6:
        n = max(2, int(round((b1 - b0) / ROW_GAP)) + 1)
        for k in range(n):
            names.append(st.obj(flame, a, b0 + (b1 - b0) * k / (n - 1), enabled=enabled))
        a += gap
    return st.group(s, names)


@pattern("flame", size=(22, 6), title="Flame jets on a clock")
def jets(st):
    gs = [_grates(st, f"R{k}", 9 + k) for k in range(3)]
    for k, g in enumerate(gs):
        st.clock(f"C{k}", g, 90, [(0, 30)])
    return Meta(tier="standard", tells="three rows of grates roar for a second every 3 s",
                answer="wait for the flames to drop, walk across the grates in the 2 s of quiet",
                careless="walking into the jets: 5 HP a frame per flame touched, ~60 HP")


@pattern("flame", size=(22, 6), title="Jump the fire")
def jump_fire(st):
    _field(st, "F", 10, 12)
    return Meta(tier="standard", tells="a strip of fire that never goes out, two squares deep",
                answer="run up and jump: a jump clears almost four squares",
                careless="walking through: ~2 HP a frame per flame for most of a second, ~80 HP")


@pattern("flame", size=(24, 6), title="The fire wave")
def fire_wave(st):
    for k in range(10):
        g = _grates(st, f"R{k}", 5 + k, grate=(k % 2 == 0))
        st.clock(f"C{k}", g, 80, [(4 * k, 4 * k + 20)])
    return Meta(tier="standard", tells="ten rows of grates burning one after another: a wave of fire down the hall",
                answer="let the wave pass and walk behind it; each row burns for less than a second",
                careless="walking into the oncoming wave: several rows at 5 HP a frame, ~80 HP")


@pattern("flame", size=(22, 6), title="Sprung fire")
def sprung_fire(st):
    g = _field(st, "F", 7, 11, flame="FireGrateFlame", enabled=False)
    gg = g.replace(st.label, "")
    for k, b in enumerate((1.1, 3.0, 4.9)):
        st.plate(f"P{k}", 9.0, b, who="player", acts=[st.act("pulse", gg, delay=12, frames=90)])
    for a in (7, 8.5, 10, 11):
        for b in (0.8, 3.0, 5.2):
            st.obj("FireGrate", a, b)
    return Meta(tier="standard", tells="a band of grates with three plates across its middle",
                answer="jump over the plates: stepping on one sets the whole band alight 0.4 s later for 3 s",
                careless="treading on a plate: the band flares around you, ~60-120 HP to get out")


@pattern("flame", size=(24, 8), title="The burning maze")
def burning_maze(st):
    # a 14 x 8 field of 1-square cells, all burning but a winding path the player can see
    rng = st.rng
    cols, rows = 14, 8
    path = set()
    j = rng.randrange(1, rows - 1)
    for i in range(cols):
        path.add((i, j))
        if i < cols - 1 and rng.random() < 0.7:
            nj = max(0, min(rows - 1, j + rng.choice((-1, 1)) * rng.choice((1, 2))))
            for jj in range(min(j, nj), max(j, nj) + 1):
                path.add((i, jj))
            j = nj
    names = []
    for i in range(cols):
        for j2 in range(rows):
            if (i, j2) in path:
                continue
            for da in (0.28, 0.72):
                for db in (0.28, 0.72):
                    names.append(st.obj("Flame", 5 + i + da, j2 + db))
    st.group("F", names)
    return Meta(tier="standard", tells="a floor on fire but for a winding lane of bare stone",
                answer="walk the lane; where it jinks, step, don't cut the corner",
                careless="cutting corners: 1 HP a frame per flame, ~40-80 HP")


@pattern("flame", size=(24, 6), tier="hard", title="Two lanes of fire")
def two_lanes(st):
    rows_a, rows_b = [], []
    for k in range(16):
        rows_a += st.T.groups.pop(_grates(st, f"A{k}", 4 + k, b0=0.4, b1=2.6, grate=(k % 2 == 0)))
        rows_b += st.T.groups.pop(_grates(st, f"B{k}", 4 + k, b0=3.4, b1=5.6, grate=(k % 2 == 1)))
    st.clock("CA", st.group("LA", rows_a), 90, [(0, 42)])
    st.clock("CB", st.group("LB", rows_b), 90, [(48, 90)])
    return Meta(tier="hard", tells="two lanes of grates side by side, burning in turn every 1.5 s",
                answer="walk in the quiet lane and cross to the other in the 0.2 s when both are out; "
                       "16 squares need three crossings",
                careless="staying in one lane: it flares under you, 5 HP a frame per flame")


@pattern("flame", size=(22, 6), title="Douse the inferno")
def douse(st):
    _field(st, "J", 4.5, 6.0)                       # a strip to jump to reach the lever
    g = _field(st, "F", 9, 16, flame="LargeFlame", enabled=True)
    gg = g.replace(st.label, "")
    st.lever("L", "FloorLever2", 7.5, 0.55, acts=[st.act("off", gg), st.act("on", gg, delay=frames(4))],
             release=[st.act("off", gg), st.act("on", gg, delay=frames(4))])
    return Meta(tier="standard", tells="a hall ablaze, a lever beyond a strip of fire",
                answer="jump the strip, pull the lever: the fire goes out for 4 s, walk through",
                careless="walking into the blaze: 7 squares of fire, ~300 HP")


@pattern("flame", size=(26, 6), tier="hard", title="Skulls and fire")
def skulls_and_fire(st):
    # a skull gun at the far end firing back down the hall (fireballs ~90 HP); pillars to hide behind; flame rows
    ux, uy = st.along()
    gun = {(1, 1): "Skull1", (1, -1): "Skull3", (-1, 1): "Skull2", (-1, -1): "Skull4"}[(round(ux / abs(ux)), round(uy / abs(uy)))]
    st.obj(gun, st.L - 0.5, st.W / 2)
    for a in (8, 13, 18):
        x, y = st.wall_cell(a, 2)
        st.spec.wall(x, y, "DungeonStone", facing=2)
        x, y = st.wall_cell(a, st.W - 2)
        st.spec.wall(x, y, "DungeonStone", facing=2)
    for k, a in enumerate((10.5, 15.5, 20.5)):
        g = _grates(st, f"R{k}", a)
        st.clock(f"C{k}", g, 75, [(10 * k, 10 * k + 25)])
    return Meta(tier="hard", tells="a skull gun at the end of the hall, stone pillars, rows of grates between",
                answer="move from pillar to pillar, out of the gun's line, crossing each grate row as it drops; the gun "
                       "fires once a second at most",
                careless="walking the middle: a fireball a second, ~90 HP each")


@pattern("flame", size=(22, 6), title="Blue and red")
def blue_and_red(st):
    reds = [_grates(st, f"R{k}", 7 + 3 * k) for k in range(4)]
    for k, g in enumerate(reds):
        st.clock(f"C{k}", g, 100, [(0, 40)] if k % 2 == 0 else [(50, 90)])
    for k in range(4):
        _field(st, f"B{k}", 8.5 + 3 * k, 8.5 + 3 * k, flame="MediumBlueFlame", gap=1.0)
    return Meta(tier="standard", tells="red grates on a beat; lines of blue flame between them that never go out",
                answer="cross the red rows when they drop; jump or accept the blue (it drains mana, not health)",
                careless="red rows met burning: ~50 HP each; a caster walking the blue loses its mana")


@pattern("flame", size=(42, 6), tier="hard", title="Trial by fire")
def trial(st):
    for k in range(8):
        g = _grates(st, f"W{k}", 4 + k, grate=(k % 2 == 0))
        st.clock(f"CW{k}", g, 60, [(3 * k, 3 * k + 15)])
    st.rest.append((13.0, st.W / 2))
    _field(st, "J", 14.5, 16.5)
    rows_a, rows_b = [], []
    for k in range(8):
        rows_a += st.T.groups.pop(_grates(st, f"A{k}", 19 + k, b0=0.4, b1=2.6, grate=(k % 2 == 0)))
        rows_b += st.T.groups.pop(_grates(st, f"B{k}", 19 + k, b0=3.4, b1=5.6, grate=(k % 2 == 1)))
    st.clock("CA", st.group("LA", rows_a), 70, [(0, 32)])
    st.clock("CB", st.group("LB", rows_b), 70, [(36, 70)])
    st.rest.append((28.5, st.W / 2))
    g = _field(st, "F", 31, 38, flame="LargeFlame")
    gg = g.replace(st.label, "")
    st.lever("L", "FloorLever2", 29.5, 0.55, acts=[st.act("off", gg), st.act("on", gg, delay=frames(2.5))],
             release=[st.act("off", gg), st.act("on", gg, delay=frames(2.5))])
    return Meta(tier="hard", tells="a fire wave, a strip, two lanes in turn, and a blaze with its lever",
                answer="trail the wave, jump the strip, switch lanes on the beat, pull the lever and run: 2.5 s",
                careless="several hundred HP")
