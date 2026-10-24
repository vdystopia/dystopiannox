"""Trap patterns: each kind of trap (spikes, flames, blocks, pushers, arrows, pits, blades, sentries, spells,
triggers) as a set of stations, from short and simple to long and hard (rules/TRAPS.md; the engine and Westwood's
numbers there).

A station is a box of floor the player crosses (a Part of kit/dungeon.py): `a` runs along it from the way in
(a = 0) to the way out (a = L), `b` across it (0 .. W), both in squares (32.5 px). A pattern builds its trap
between them with the kit (kit/traps.py: objects, groups, clocks, movers, plates, levers) and returns its Meta:
what the player sees, the answer, what a careless run costs, its tier (standard or hard).

    from kit.trapkit import Station, PATTERNS
    st = Station(T, part, "TLSPIKE03", rng, fall_to=(x, y))
    meta = PATTERNS["spike"][2](st)                      # build the third spike variant in this station

Each kind module registers its variants in order (PATTERNS[kind] = [fn, ...], ten each for the TrapLab maps);
a pattern may ask for a size (`fn.size = (L, W)`, squares) and the builder makes the station that big.
"""
import math

PATTERNS = {}
KINDS = ["spike", "flame", "block", "push", "arrow", "pit", "blade", "sentry", "spell", "trigger"]
TITLES = {"spike": "Spikes", "flame": "Flames", "block": "Spike blocks", "push": "Pushers and pits",
          "arrow": "Arrow traps", "pit": "Pits and crumbling floors", "blade": "Blades",
          "sentry": "Sentry beams", "spell": "Spell traps", "trigger": "Switches, plates and sensors"}
SQ = 32.5                      # px a square
GRID = 11.5                    # px between the spikes of a Westwood spike carpet


class Meta(dict):
    """A station's description: title (a few words), tells (what warns), answer (how to pass), careless (what a
    walk straight through costs), tier (standard / hard), and for the simulator: route hints."""


def pattern(kind, size=(24, 6), tier="standard", title=""):
    """Register a pattern function for `kind` (in order: the TrapLab's NN), the station size it wants."""
    def deco(fn):
        fn.kind, fn.size, fn.tier, fn.title = kind, size, tier, title or fn.__name__.replace("_", " ")
        PATTERNS.setdefault(kind, []).append(fn)
        return fn
    return deco


class Station:
    """One trap stage on a Part: placing in station coordinates, names prefixed with the station's label."""

    def __init__(self, T, part, label, rng, fall_to=None, spec=None, tier=None, pop=None):
        self.T, self.part, self.label, self.rng = T, part, label, rng
        self.spec = spec or T.spec
        self.L, self.W = part.length, part.width
        self.fall_to = fall_to                 # where a pit drops the player (the map's pit room)
        self.pop = pop                         # kit.npcs Population, for monsters (gauntlets)
        self.tier = tier
        self.k = 0
        self.monsters = []
        self.starts = []                       # clocks the station's run restarts (the playtest syncs on them)
        self.rest = []                         # (a, b) of the safe spots the pattern leaves (potions, waiting)

    # ---- coordinates ----------------------------------------------------------------------------------------
    def at(self, a, b):
        return self.part.at(a, b)

    def along(self):
        return self.part.direction()

    def across(self):
        return self.part.across()

    def nm(self, s):
        self.k += 1
        return f"{self.label}{s}{self.k}"

    # ---- objects ----------------------------------------------------------------------------------------------
    def obj(self, type_, a, b, enabled=True, **kw):
        return self.T.obj(type_, *self.at(a, b), name=self.nm(type_[:6]), enabled=enabled, **kw)

    def objs_px(self, type_, pts, enabled=True, **kw):
        return [self.T.obj(type_, x, y, name=self.nm(type_[:6]), enabled=enabled, **kw) for x, y in pts]

    def group(self, s, objs):
        return self.T.group(f"{self.label}{s}", objs)

    def clock(self, s, group, period, on, phase=0, armed=True):
        name = self.T.clock(f"{self.label}{s}", group, period, on, phase=phase, armed=armed)
        self.starts.append(name)
        return name

    def lattice(self, a0, a1, b0, b1, step=GRID, margin=0.0):
        """World points on a square grid `step` px apart (in world x, y as Westwood lays spike carpets) inside
        the station rectangle a0..a1, b0..b1 (squares)."""
        corners = [self.at(a, b) for a in (a0, a1) for b in (b0, b1)]
        xs, ys = [c[0] for c in corners], [c[1] for c in corners]
        pts = []
        y = min(ys) + step / 2
        while y < max(ys):
            x = min(xs) + step / 2
            while x < max(xs):
                a, b = self.ab(x, y)
                if a0 + margin <= a <= a1 - margin and b0 + margin <= b <= b1 - margin:
                    pts.append((round(x, 1), round(y, 1)))
                x += step
            y += step
        return pts

    def ab(self, x, y):
        """Station coordinates (a, b) of a world point."""
        x0, y0 = self.at(0, 0)
        ux, uy = self.along()
        vx, vy = self.across()
        dx, dy = x - x0, y - y0
        return (dx * ux + dy * uy) / SQ, (dx * vx + dy * vy) / SQ

    def carpet(self, s, a0, a1, b0, b1, type_="Spike", enabled=True, step=GRID):
        """A spike carpet (Westwood's: ~11 px grid) over a0..a1 x b0..b1, as one group named s."""
        names = self.objs_px(type_, self.lattice(a0, a1, b0, b1, step), enabled=enabled)
        return self.group(s, names)

    def row(self, type_, a, b0, b1, gap, enabled=True, **kw):
        """Objects across the station at `a`, from b0 to b1, `gap` squares apart."""
        n = max(1, int(round((b1 - b0) / gap)) + 1)
        step = (b1 - b0) / max(1, n - 1)
        return [self.obj(type_, a, b0 + k * step, enabled=enabled, **kw) for k in range(n)]

    def plate(self, s, a, b, **kw):
        return self.T.plate(f"{self.label}{s}", *self.at(a, b), **kw)

    def lever(self, s, type_, a, b, **kw):
        return self.T.lever(f"{self.label}{s}", type_, *self.at(a, b), **kw)

    def act(self, kind, target="", **kw):
        if target and not target.startswith(self.label) and kind not in ("say", "log", "sound"):
            target = f"{self.label}{target}"
        return self.T.act(kind, target, **kw)

    def wall_cell(self, a, b):
        """The grid cell of the wall point nearest station point (a, b) (on the square corners)."""
        from kit.layout import point_cell
        si, sj = self.part.sq(a, b)
        return point_cell(int(round(si)), int(round(sj)))

    def gate(self, a, state="closed", material=None):
        """A row of secret walls across the station at `a` (on the square corners): a gate the script opens
        (walls_open) or shuts (walls_close). Returns the wall cells."""
        from kit.layout import point_cell
        cells = []
        for k in range(1, self.W):
            si, sj = self.part.sq(a, k)
            x, y = point_cell(int(round(si)), int(round(sj)))
            mat = material or self.part.wall or "DungeonStone"
            self.spec.wall(x, y, mat, secret=state)
            cells.append((x, y))
        return cells

    def potion(self, a, b, kind="RedPotion"):
        self.spec.obj_px(kind, *self.at(a, b))
        self.rest.append((a, b))


def frames(seconds):
    return int(round(seconds * 30))


# the kinds' modules (kit/trapkit/<kind>.py) register themselves on import, in KINDS order
def _load():
    import importlib, os
    here = os.path.dirname(os.path.abspath(__file__))
    mods = {f[:-3] for f in os.listdir(here) if f.endswith(".py") and not f.startswith("_")}
    order = {"spike": "spikes", "flame": "flames", "block": "blocks", "push": "pushers", "arrow": "arrows",
             "pit": "pits", "blade": "blades", "sentry": "sentries", "spell": "spells", "trigger": "triggers"}
    for kind in KINDS:
        if order[kind] in mods:
            importlib.import_module(f"kit.trapkit.{order[kind]}")
    for m in sorted(mods - set(order.values())):
        importlib.import_module(f"kit.trapkit.{m}")


_load()
