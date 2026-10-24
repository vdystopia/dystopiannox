"""Helpers shared by the spell and trigger kinds (kit/trapkit/spells.py, triggers.py): lights, plate object names,
station boxes for the Go watchers (kit/behaviours/traps_spell.go, traps_trigger.go), start lines, shooter facings,
secret wall gates, creatures.
"""
from kit.trapkit import SQ

# Westwood's fist-plate light (G_Crypts FistTrapLight12): a steady ColorLight, coloured and sized per use
_LIGHT = {"Unknown2": [2, 0, 0, 0, 0, 0], "NumOfColors": 0, "LightIntensity": 50, "LightRadius": 144,
          "UnknownVal": [0, 0, 0, 0, 255, 255, 0, 0], "R": 131, "G": 0, "B": 255, "R2": 0, "G2": 0, "B2": 0,
          "R3": 0, "G3": 0, "B3": 0, **{f"{k}Radius{n}": 0 for n in range(2, 11) for k in ("Min", "Max")},
          "Color1": [131, 0, 255], **{f"Color{n}": [0, 0, 0] for n in range(2, 11)}, "Unknown3": [0] * 18,
          "Unknown4": [0] * 11, "UnknownR": 0, "UnknownG": 0, "UnknownB": 0, "UnknownR2": 0, "UnknownG2": 0,
          "UnknownB2": 0, "PulseSpeed": 0, "PulseSpeedSingle": 0, "ChangeIntensitySingle": 50, "Unknown11": 0,
          "type": 0, "Unknown5": 0, "Unknown6": 0, "ChangeColors": None, "ChangeIntensity": 21, "ChangeRadius": None,
          "ColorChangeIndex": 0, "IntensityChangeIndex": 0, "RadiusChangeIndex": 0, "Unknown7": 72, "Unknown8": 66,
          "Unknown10": 0, "IsAntiLight": 0, "Unknown80": 128, "Unknown30": [0] * 12, "Unknown9": [0, 0, 0]}

VIOLET, RED, ORANGE, GREEN, BLUE, WHITE = (131, 0, 255), (255, 40, 20), (255, 140, 40), (90, 255, 60), \
    (60, 120, 255), (230, 230, 210)

# shooters face one diagonal each (rules/traps/ENGINE.md 8): world (dx, dy) signs -> type
SKULL = {(-1, -1): "Skull1", (1, -1): "Skull2", (-1, 1): "Skull3", (1, 1): "Skull4"}
ARROW = {(1, 1): "ArrowTrap1", (-1, 1): "ArrowTrap2"}


def diag(d):
    return (1 if d[0] > 0 else -1, 1 if d[1] > 0 else -1)


def neg(d):
    return (-d[0], -d[1])


def go_pt(p):
    return f"ns.Ptf({float(p[0]):.1f}, {float(p[1]):.1f})"


def go_strs(xs):
    return "[]string{" + ", ".join(f'"{x}"' for x in xs) + "}"


def light(st, a, b, rgb=VIOLET, radius=60, intensity=45, enabled=True):
    x = dict(_LIGHT)
    x.update(R=rgb[0], G=rgb[1], B=rgb[2], Color1=list(rgb), LightRadius=int(radius), LightIntensity=int(intensity),
             ChangeIntensitySingle=int(intensity))
    return st.T.obj("ColorLight", *st.at(a, b), name=st.nm("Light"), enabled=enabled, xfer=x)


def plate_obj(st, s):
    """The script name kit/traps.py gives the PressurePlate object of station plate `s`."""
    return f"{st.T.prefix}Plate{st.T.go_name(st.label + s)}"


def box(st, a0, a1, b0=0.0, b1=None):
    """A station box for the Go watchers: centre, the unit vector along the station, half sizes along and across."""
    b1 = st.W if b1 is None else b1
    c = st.at((a0 + a1) / 2, (b0 + b1) / 2)
    return c, st.along(), (a1 - a0) / 2 * SQ, (b1 - b0) / 2 * SQ


def box_go(st, a0, a1, b0=0.0, b1=None):
    c, u, hu, hv = box(st, a0, a1, b0, b1)
    return f"C: {go_pt(c)}, U: ns.Ptf({u[0]:.5f}, {u[1]:.5f}), HU: {hu:.1f}, HV: {hv:.1f}"


def start(st, line):
    if line not in st.T.starts:
        st.T.starts.append(line)


def acts_go(st, acts):
    return st.T._acts_go(list(acts))


def shooter(st, table, d):
    """The type in `table` (SKULL or ARROW) that shoots along world direction d, or None."""
    return table.get(diag(d))


def secret_line(st, a, b0=1, b1=None, state="closed", material=None):
    """Secret walls across the station at a (a square corner), on the inner corners b0..b1 (the side walls stand at
    b = 0 and W): a gate the script opens and closes (walls_open / walls_close). Returns the wall cells."""
    b1 = st.W - 1 if b1 is None else b1
    mat = material or st.part.wall or "DungeonStone"
    cells = []
    for b in range(int(b0), int(b1) + 1):
        x, y = st.wall_cell(a, b)
        st.spec.wall(x, y, mat, secret=state)
        cells.append((x, y))
    return cells


def pillar(st, a, b, material=None):
    """A wall post at the square corner nearest (a, b): cover from missiles and beams."""
    x, y = st.wall_cell(a, b)
    st.spec.wall(x, y, material or st.part.wall or "DungeonStone")
    return x, y


def creature(st, type_, a, b, face=None, action="guard", aggr=0.83, **kw):
    """A creature (kit/npcs Population) at station point (a, b) with a script name; faces station point `face`."""
    from kit.npcs import Population
    pop = st.pop or getattr(st.spec, "_trap_pop", None)
    if pop is None:
        pop = Population(st.spec, st.rng)
        st.spec._trap_pop = pop
    name = st.nm(type_[:6])
    x, y = st.at(a, b)
    o = pop.creature(type_, x, y, action=action, face=st.at(*face) if face else None, scr=name, aggr=aggr, **kw)
    st.monsters.append(name)
    return name, o
