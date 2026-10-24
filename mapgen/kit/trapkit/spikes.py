"""Spike floors: carpets of Spike (Westwood's ~11 px grid; up = ~5 HP a frame to whoever stands on them, down =
harmless and hidden) switched by the script: clocks, waves, alternations, plates, levers, a greed trap.

Movement for the numbers (rules/TRAPS.md 1): a walk crosses a square in ~10 frames, a run in ~5; a jump clears
~3.8 squares; stamina allows one jump a second. Standard windows leave a walk 1.5x the time it needs; hard ones
need a run or a read of two rhythms at once.
"""
from kit.trapkit import pattern, Meta, frames


def _edge(st):
    return 0.35, st.W - 0.35


@pattern("spike", size=(22, 6), title="One field on a clock")
def clocked_field(st):
    b0, b1 = _edge(st)
    g = st.carpet("F", 8, 11, b0, b1, enabled=False)
    st.clock("C", g, 120, [(0, 60)])
    return Meta(tier="standard", tells="the field rises and sinks every 2 s",
                answer="wait at its edge, walk across when it sinks (2 s; a walk needs 1)",
                careless="walking in while it is up: ~5 HP a frame for a second or more")


@pattern("spike", size=(24, 6), title="Two fields in turn")
def alternating_fields(st):
    b0, b1 = _edge(st)
    a = st.carpet("A", 6, 9, b0, b1, enabled=False)
    b = st.carpet("B", 12, 15, b0, b1, enabled=False)
    st.clock("CA", a, 120, [(0, 60)])
    st.clock("CB", b, 120, [(60, 120)])
    st.rest.append((10.5, st.W / 2))
    return Meta(tier="standard", tells="two fields, one up while the other is down",
                answer="cross the first as it sinks, wait on the strip between, cross the second as it sinks",
                careless="walking on at an even pace meets one field up: ~150 HP")


@pattern("spike", size=(24, 6), title="The wave")
def wave(st):
    b0, b1 = _edge(st)
    for k in range(8):
        g = st.carpet(f"R{k}", 5 + k, 6 + k, b0, b1, enabled=False)
        st.clock(f"C{k}", g, 90, [(8 * k, 8 * k + 30)] if 8 * k + 30 <= 90 else [(8 * k, 90), (0, 8 * k + 30 - 90)])
    return Meta(tier="standard", tells="the spikes rise row by row down the hall, a wave every 3 s",
                answer="step in just behind the crest and follow it; the rows behind it stay down for 2 s",
                careless="walking into the crest: each row it meets costs ~25-50 HP")


@pattern("spike", size=(24, 6), title="Sprung floor")
def sprung_floor(st):
    b0, b1 = _edge(st)
    g = st.carpet("F", 6, 15, b0, b1, enabled=False)
    # plates on the field in a checker the player can read and weave through (or jump)
    spots = [(7.5, 1.2), (9.0, 4.6), (10.5, 1.6), (12.0, 4.4), (13.5, 1.2), (9.6, 2.9), (12.6, 3.0)]
    for k, (a, b) in enumerate(spots):
        st.plate(f"P{k}", a, b, who="player", acts=[st.act("pulse", g.replace(st.label, ""), delay=10, frames=75)])
    return Meta(tier="standard", tells="plates on a field that lies down",
                answer="weave between the plates or jump them: a plate raises the whole field 0.3 s later for 2.5 s",
                careless="treading on a plate mid-field: the field rises under you, ~100 HP to get off")


@pattern("spike", size=(22, 6), title="The greed trap")
def greed(st):
    b0, b1 = _edge(st)
    g = st.carpet("F", 6, 16, b0, b1, enabled=False)
    gold = st.T.obj("Gold", *st.at(13.5, st.W / 2), name=st.nm("Gold"), xfer={"Amount": 150})
    cloud_a, cloud_b = st.at(9.0, st.W / 2), st.at(12.0, st.W / 2)
    st.T.watch(f"{st.label}W", gold, acts=[
        st.act("on", g.replace(st.label, "")),
        st.act("cast", spell="SPELL_TOXIC_CLOUD", src=cloud_a, dst=cloud_a, delay=20),
        st.act("cast", spell="SPELL_TOXIC_CLOUD", src=cloud_b, dst=cloud_b, delay=20),
        st.act("off", g.replace(st.label, ""), delay=frames(5))])
    return Meta(tier="hard", tells="a pile of gold on a quiet floor",
                answer="take the gold and jump straight out toward the far side (2.5 squares), before the gas",
                careless="taking it and walking back: every spike rises under you, then poison: 150+ HP")


@pattern("spike", size=(22, 6), title="Lane by lane")
def lanes(st):
    w = st.W / 3
    gs = [st.carpet(f"L{k}", 4, 18, k * w + 0.3, (k + 1) * w - 0.3 if k < 2 else st.W - 0.35, enabled=False)
          for k in range(3)]
    # two lanes up, one down; the down lane moves over every 2 s, the old one rising 0.3 s after the new one sinks
    for k, g in enumerate(gs):
        down0, down1 = 60 * k - 10, 60 * k + 60
        on = [(t0, t1) for t0, t1 in ((0, max(0, down0)), (min(180, down1), 180)) if t1 > t0]
        if down0 < 0:
            on = [(down1, 180 + down0)]
        st.clock(f"C{k}", g, 180, on)
    return Meta(tier="hard", tells="three lanes; two are always up, the low one moves sideways every 2 s",
                answer="walk in the low lane and step into the next as it sinks (a third of a second when both "
                       "are down); 14 squares need three switches",
                careless="staying in one lane: it rises under you, ~5 HP a frame")


@pattern("spike", size=(22, 6), title="Checkerboard")
def checker(st):
    tiles_a, tiles_b = [], []
    for i in range(4):
        for j in range(3):
            names = st.objs_px("Spike", st.lattice(6 + 2 * i, 8 + 2 * i, 2 * j + 0.1, 2 * j + 1.9), enabled=False)
            (tiles_a if (i + j) % 2 == 0 else tiles_b).extend(names)
    a = st.group("A", tiles_a)
    b = st.group("B", tiles_b)
    st.clock("CA", a, 70, [(0, 31)])
    st.clock("CB", b, 70, [(35, 66)])
    return Meta(tier="hard", tells="a checkerboard of spike tiles that swap every second",
                answer="step diagonally onto a sunk tile each time the board swaps (a tenth of a second when all "
                       "are down)",
                careless="walking straight: half the tiles are up at any moment, ~80 HP across")


@pattern("spike", size=(24, 6), title="The spike gate")
def lever_gate(st):
    b0, b1 = _edge(st)
    g = st.carpet("F", 8, 16, b0, b1, enabled=True)
    gg = g.replace(st.label, "")
    tick = [st.act("sound", text="Gear1", src=st.at(7.0, 0.6), delay=d) for d in range(0, 150, 15)]
    st.lever("L", "FloorLever1", 6.5, 0.55, acts=[st.act("off", gg), st.act("on", gg, delay=frames(5))] + tick,
             release=[st.act("off", gg), st.act("on", gg, delay=frames(5))] + tick)
    return Meta(tier="standard", tells="a field of standing spikes and a lever by the wall before it",
                answer="pull the lever: the spikes sink for 5 s (the gears tick), enough to walk across",
                careless="walking in without the lever: 8 squares of spikes, ~400 HP (death)")


@pattern("spike", size=(24, 6), title="Jump the strips")
def jump_strips(st):
    b0, b1 = _edge(st)
    for k, a in enumerate((6, 11, 16)):
        st.carpet(f"S{k}", a, a + 2, b0, b1, enabled=True)
        st.rest.append((a + 3.5, st.W / 2))
    return Meta(tier="standard", tells="three strips of standing spikes, two squares deep, floor between",
                answer="jump each strip (a jump clears almost four squares); the floor between lets the stamina "
                       "come back",
                careless="walking each strip: ~100 HP a strip")


@pattern("spike", size=(42, 6), tier="hard", title="The long run")
def long_run(st):
    b0, b1 = _edge(st)
    # 1. a fast wave
    for k in range(6):
        g = st.carpet(f"W{k}", 4 + k, 5 + k, b0, b1, enabled=False)
        t0 = 6 * k
        st.clock(f"CW{k}", g, 60, [(t0, t0 + 24)])
    st.rest.append((11.5, st.W / 2))
    # 2. two jump strips
    for k, a in enumerate((13.0, 17.5)):
        st.carpet(f"J{k}", a, a + 2.5, b0, b1, enabled=True)
    # 3. a quick alternating pair
    a = st.carpet("A", 23, 25, b0, b1, enabled=False)
    b = st.carpet("B", 27, 29, b0, b1, enabled=False)
    st.clock("CA", a, 60, [(0, 30)])
    st.clock("CB", b, 60, [(30, 60)])
    st.rest.append((31.0, st.W / 2))
    # 4. a sprung floor to finish
    f = st.carpet("F", 33, 39, b0, b1, enabled=False)
    for k, (aa, bb) in enumerate([(34.0, 1.3), (35.6, 4.6), (37.2, 1.6), (38.0, 4.2), (36.0, 3.0)]):
        st.plate(f"P{k}", aa, bb, who="player", acts=[st.act("pulse", f.replace(st.label, ""), delay=8, frames=60)])
    return Meta(tier="hard", tells="a fast wave, two strips, a quick pair and a field of plates, one after another",
                answer="follow the wave, jump the strips, take the pair on the beat, weave the plates; rest on the "
                       "floor between",
                careless="several hundred HP: no class walks it")
