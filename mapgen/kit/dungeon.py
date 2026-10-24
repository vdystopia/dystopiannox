"""Walled dungeons: rooms and corridors with straight walls on the square grid, as Westwood's castles, crypts and
temples are built (the trap maps: kit/traps.py).

Geometry is Land's (kit/layout.py): square (i, j) is one floor tile, covering u in [2i, 2i+2] and v in [2j-2, 2j];
a wall point sits on a square corner and gets a wall when the four squares round it are partly floor and partly
void. A room is a box of squares; rooms that touch or overlap merge into one floor (a corridor running into a room
opens into it), so the outline is always closed and the walls are shaped by Spec from their neighbours.

    d = Dungeon(spec, rng, wall="DungeonStone", floor="GreenBrick")
    a = d.box("hall", 120, 30, 10, 6)            # name, i0, j0, length along i, width along j (squares)
    b = d.corridor("run", (130, 33), (160, 33), 3)
    d.apply()                                     # floors, then the walls round the whole shape

Each named part keeps its squares (d.parts[name]), its floor and its wall, and d.at(name, a, b) gives the world px of
a point in the part's own frame: a along its length from its start, b across it from its left edge, in squares.
"""
import json, math, os
from nox import px
from kit.layout import Land, square_px, square_tile, point_cell, N4

# a room's standing light by setting: no open torches indoors (they never look fixed to the wall), candelabras and
# braziers instead; a passage is lit by an unseen ColorLight (glow), which stands in no trap's way
LIGHTS = {"crypt": "Candleabra3", "castle": "Candleabra3", "lotd": "LOTDCandleabra1", "forge": "Brazier",
          "temple": "Brazier", "mine": "Brazier"}
_GLOW = None


def glow(spec, x, y):
    """An unseen warm light at (x, y) px: Westwood's commonest steady orange or yellow ColorLight preset."""
    global _GLOW
    if _GLOW is None:
        here = os.path.dirname(os.path.abspath(__file__))
        presets = json.load(open(os.path.join(here, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]
        _GLOW = dict(max((p for p in presets if p["animation"] == "steady" and p["intensity_class"] == "full"
                          and p["family"] in ("orange", "yellow")), key=lambda p: p["weighted_share"])["xfer"])
    return spec.obj_px("ColorLight", x, y, xfer=dict(_GLOW))


class Part:
    """A box of squares: origin (i0, j0), `length` squares along `axis` ("i" or "j"), `width` across. sign -1 runs
    the part the other way: `a` grows toward smaller i (or j) from the origin edge (squares i0 - length .. i0 - 1)."""

    def __init__(self, name, i0, j0, length, width, axis="i", floor=None, wall=None, kind="room", sign=1):
        self.name, self.i0, self.j0, self.length, self.width, self.axis = name, i0, j0, length, width, axis
        self.floor, self.wall, self.kind, self.sign = floor, wall, kind, sign

    @property
    def squares(self):
        s = self.sign
        if self.axis == "i":
            return {(self.i0 + a if s > 0 else self.i0 - 1 - a, self.j0 + b)
                    for a in range(self.length) for b in range(self.width)}
        return {(self.i0 + b, self.j0 + a if s > 0 else self.j0 - 1 - a)
                for a in range(self.length) for b in range(self.width)}

    def sq(self, a, b):
        """Square coordinates (fractional) of the point a squares along the part and b across it."""
        if self.axis == "i":
            return self.i0 + self.sign * a, self.j0 + b
        return self.i0 + b, self.j0 + self.sign * a

    def at(self, a, b):
        """World px of the point a along, b across (squares; the part spans a in [0, length], b in [0, width]).
        The frame sits on the walls as Nox draws and collides them (a wall cell's line runs through the cell's middle):
        in a part along i the side walls stand at b = 0 and b = width (before 2026-10-24 they stood at b = -0.5 and
        width - 0.5 of this frame: things set by the far wall stood in it); in a part along j the side walls are at
        b = 0 and width and the walls across it at a = -0.5 and length - 0.5 (its ends are open in the trap maps)."""
        si, sj = self.sq(a, b)
        if self.axis == "i":
            return square_px(si, sj - 1.5)
        return square_px(si, sj - 1)

    def square(self, a, b):
        """The square (integers) a along, b across."""
        si, sj = self.sq(a, b)
        return int(math.floor(si)), int(math.floor(sj))

    def tile(self, a, b):
        return square_tile(*self.square(a, b))

    @property
    def centre(self):
        return self.at(self.length / 2, self.width / 2)

    def direction(self):
        """Unit world-px step along the part (a +1 square)."""
        x0, y0 = self.at(0, 0)
        x1, y1 = self.at(1, 0)
        L = math.hypot(x1 - x0, y1 - y0)
        return (x1 - x0) / L, (y1 - y0) / L

    def across(self):
        x0, y0 = self.at(0, 0)
        x1, y1 = self.at(0, 1)
        L = math.hypot(x1 - x0, y1 - y0)
        return (x1 - x0) / L, (y1 - y0) / L


class Dungeon:
    def __init__(self, spec, rng, wall="DungeonStone", floor="GreenBrick"):
        self.spec, self.rng, self.wall, self.floor = spec, rng, wall, floor
        self.parts = {}
        self.void = set()                    # squares cut out of a part after it was laid (a pit's hole, a pillar)

    def box(self, name, i0, j0, length, width, axis="i", floor=None, wall=None, kind="room", sign=1):
        p = Part(name, i0, j0, length, width, axis, floor or self.floor, wall or self.wall, kind, sign)
        self.parts[name] = p
        return p

    def corridor(self, name, a, b, width, floor=None, wall=None):
        """A straight corridor from square a to square b (same i or same j), `width` squares wide, centred on the
        line between them."""
        (ai, aj), (bi, bj) = a, b
        assert ai == bi or aj == bj, "corridors run along i or j"
        if aj == bj:
            i0, L = min(ai, bi), abs(bi - ai) + 1
            return self.box(name, i0, aj - width // 2, L, width, "i", floor, wall, kind="corridor")
        j0, L = min(aj, bj), abs(bj - aj) + 1
        return self.box(name, ai - width // 2, j0, L, width, "j", floor, wall, kind="corridor")

    @property
    def squares(self):
        out = set()
        for p in self.parts.values():
            out |= p.squares
        return out - self.void

    def owner(self, s):
        """The part a square belongs to (rooms win over corridors, later parts over earlier)."""
        best = None
        for p in self.parts.values():
            if s in p.squares and (best is None or p.kind != "corridor" or best.kind == "corridor"):
                best = p
        return best

    def apply(self, floors=True):
        """Lay every part's floor and the walls round the whole shape (Land.apply's rule: a wall point between
        floor and void). A wall point takes the wall material of the part beside it."""
        sq = self.squares
        land = Land(self.rng, u_range=(0, 2), v_range=(0, 2))
        land.squares = set(sq)
        owners = {s: self.owner(s) for s in sq}
        if floors:
            for s, p in owners.items():
                self.spec.floor.setdefault(square_tile(*s), p.floor)
        for p_, q in land.boundary_points():
            quad = [(p_ - 1, q), (p_, q), (p_ - 1, q + 1), (p_, q + 1)]
            o = next((owners[s] for s in quad if s in owners), None)
            x, y = point_cell(p_, q)
            self.spec.wall(x, y, o.wall if o else self.wall)
        return land

    def wall_points(self):
        land = Land(self.rng, u_range=(0, 2), v_range=(0, 2))
        land.squares = set(self.squares)
        return land.boundary_points()
