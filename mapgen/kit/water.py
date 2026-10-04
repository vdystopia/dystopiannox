"""Water features and crossings, generated from rules learned from Westwood's maps
(rules/out/water.json, floors.json, decoration.json; geometry measured in corpus maps).

What Westwood does, and what this module reproduces:
- Streams are narrow (1-3 tiles, widest about 5) with irregular banks. Shallow water forms the
  bank band (1-2 tiles from land); deep water appears only 2+ tiles from shore. Water spills onto
  the bank tiles as edge overlays (ShallowWaterAndGrass on grass; deep over shallow with BlendEdge).
- Invisible walls sit on the shoreline water cells (68% of shore tiles are fenced), never on the
  map's outer boundary (that must be a visible wall).
- Plank bridges (Con05A) are a square deck of WoodSlatFloor laid across a narrow stream; the planks
  spill onto the water and banks around them with WoodSlatEdge overlays. Water cells beside the
  deck get the shore walls, which act as railings.
- Fords are a short land strip across shallow water; water edges spill onto it.
- Docks, rope bridges and lava bridges are object kits on a two-row floor strip: one walkable lane
  and a second row carrying invisible walls, plus a wall row beyond the lane. Piece order, spacing
  and offsets below were measured on Westwood's own examples (Con05A, Con03A, Con08e, G_Swamp,
  Con06a, Con06b).

Coordinates: tiles/walls in grid cells (x + y even); u = x + y, v = x - y. A tile at (x, y) is
drawn centred on corner (x+1, y+1), i.e. at uv (x + y + 2, x - y). Objects in world px (23/cell).

Usage:
    ww = Waterworks(spec, rng)
    s = ww.stream([(u0, v0), (u1, v1), ...], width=3)
    ww.plank_bridge(s, t=0.4)
    ww.ford(s, t=0.75)
    p = ww.pond((u, v), radius=7)
    ww.dock(p, direction="down")
    ww.finish()            # once, after all features: bank edges, shore walls, dressing
"""
import math, re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

from nox import CELL, load_rules

Cell = Tuple[int, int]
SQ2 = math.sqrt(2.0)
TILE = SQ2                      # distance between side-neighbour tile centres, in cells
REEDS = re.compile(r"Reed|Cattail|Rush|Grass|Plant", re.I)

# Water families: (shallow, deep, land the water spills onto by default, edge type water->land)
FAMILIES = {
    "clear": ("WaterShallow", "WaterDeep", "ShallowWaterAndGrass"),
    "swamp": ("WaterSwampShallow", "WaterSwampDeep", "SwampEdge"),
    "cave": ("Water", "Water", "DirtRidge"),
}
WATER_MATERIALS = {"Water", "WaterShallow", "WaterDeep", "WaterSwampShallow", "WaterSwampDeep",
                   "WaterDeepNoTeleport", "WaterShallowNoTeleport", "WaterNoTeleport",
                   "WaterSwampShallowNoTeleport", "WaterSwampDeepNoTeleport"}
LAVA_MATERIALS = {"Lava"}

# Kit geometry measured on Westwood maps. Each kit sits on a two-row floor strip: the walkable
# lane row and a second row that carries invisible walls, plus a wall row on the far side of the
# lane. Rows are tile-centre (visual) coordinates: v for kits along '\\' (axis "u"), u for kits
# along '/' (axis "v"). piece_side = piece line minus lane row. Measured on Con05A (DockDown),
# Con03A (DockUp), Con08e (RopeBridge1), G_Swamp (RopeBridge2), Con06a/Con06b (lava bridges).
KITS = {
    "DockDown": dict(axis="u", floor="WoodGray", piece_side=0.25,
                     steps=dict(first=5.0, mid=6.5, last=3.4)),
    "DockUp": dict(axis="v", floor="WoodGray2", piece_side=-1.0,
                   steps=dict(first=3.74, mid=3.74, last=3.74)),
    "RopeBridge1": dict(axis="u", floor="WoodDark", piece_side=-0.8, step=3.95, back_px=-30),
    "RopeBridge2": dict(axis="v", floor="WoodDark2", piece_side=0.0, step=3.95, back_px=-30),
    "LavaBridge1": dict(axis="u", floor="VolcanicCraggy", piece_side=-0.8, back_px=-29,
                        steps_px=dict(first=28, mid=44, last=61)),
    "LavaBridge2": dict(axis="v", floor="VolcanicCraggy", piece_side=0.0, back_px=-29,
                        steps_px=dict(first=28, mid=44, last=61)),
}
KIT_FLOORS = {k["floor"] for k in KITS.values() if k["floor"] != "VolcanicCraggy"}

# Exact pixel steps between consecutive kit pieces (FarEnd -> ... -> NearEnd), measured on every
# Westwood map that uses the kit (rules: corpus objects). Pieces are not on a pure diagonal: the
# small sideways offsets are what make the planks line up. "back" = Back piece minus Front piece.
KIT_STEPS = {
    "DockDown": dict(first=(62, 53), mid=(75, 74), last=(36, 42)),
    "DockUp": dict(first=(-42, 44), mid=None, last=(-45, 47)),          # only one centre piece is attested
    "RopeBridge1": dict(first=(46, 38), mid=(46, 46), last=(45, 53), back=(0, -30)),
    "RopeBridge2": dict(first=(-45, 38), mid=(-46, 46), last=(-44, 56), back=(0, -30)),
    "LavaBridge1": dict(first=(28, 28), mid=(44, 44), last=(61, 61), back=(-1, -28)),
    "LavaBridge2": dict(first=(-28, 27), mid=(-42, 45), last=(-62, 60), back=(1, -28)),
}


def chain_positions(kit, start_px, n_centres):
    """Pixel positions of FarEnd, n centre pieces and NearEnd, using Westwood's exact steps."""
    st = KIT_STEPS[kit]
    x, y = start_px
    pts = [(x, y)]
    for i in range(n_centres):
        dx, dy = st["first"] if i == 0 else st["mid"]
        x, y = x + dx, y + dy; pts.append((x, y))
    dx, dy = st["last"]
    pts.append((x + dx, y + dy))
    return pts



def tile_centre_xy(x, y):
    return x + 1.0, y + 1.0


def uv_to_xy(u, v):
    return (u + v) / 2.0, (u - v) / 2.0


def xy_to_uv(x, y):
    return x + y, x - y


def tile_at_uv(u, v):
    """Tile cell whose visual centre is nearest to the uv point."""
    x, y = uv_to_xy(u - 2, v)
    xi, yi = round(x), round(y)
    if (xi + yi) % 2:
        cands = [(xi + 1, yi), (xi - 1, yi), (xi, yi + 1), (xi, yi - 1)]
        xi, yi = min(cands, key=lambda c: (c[0] - x) ** 2 + (c[1] - y) ** 2)
    return xi, yi


def px_of_uv(u, v):
    x, y = uv_to_xy(u, v)
    return x * CELL, y * CELL


@dataclass
class Body:
    kind: str                         # "stream", "pond", "lava"
    family: str
    tiles: Set[Cell] = field(default_factory=set)
    path_xy: List[Tuple[float, float]] = field(default_factory=list)   # centre line (cells)
    widths: List[float] = field(default_factory=list)                   # half-width per path point (cells)


class Waterworks:
    def __init__(self, spec, rng, inside=None):
        """inside(x, y) -> bool limits features to the playable area (default: any floor tile)."""
        self.spec, self.rng = spec, rng
        self.inside = inside
        self.bodies: List[Body] = []
        self.no_walls: Set[Cell] = set()      # cells that must stay free of shore walls (crossings)
        self.kit_walls: Set[Cell] = set()
        self.kit_lanes: List[List[Cell]] = []
        self.bridge_materials = set()
        self.floors = load_rules("floors")
        self.water_rules = load_rules("water")
        self.deco = load_rules("decoration")

    # ------------------------------------------------------------------ helpers
    def _land(self, cell):
        m = self.spec.floor.get(cell)
        return m is not None and m not in WATER_MATERIALS and m not in LAVA_MATERIALS

    def _ok(self, cell):
        if cell not in self.spec.floor: return False
        return self.inside(*cell) if self.inside else True

    @staticmethod
    def _noise(rng, n=3):
        """Smooth 1-D noise: sum of a few random sines, roughly in [-1, 1]."""
        parts = [(rng.uniform(0.15, 0.6) / (k + 1), rng.uniform(0, 2 * math.pi), rng.uniform(0.6, 1.0) / (k + 1)) for k in range(n)]
        tot = sum(a for _, _, a in parts)
        return lambda s: sum(a * math.sin(f * s + p) for f, p, a in parts) / tot

    @staticmethod
    def _densify(pts, step=0.5):
        out = []
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(bx - ax, by - ay) / step))
            out += [(ax + (bx - ax) * i / n, ay + (by - ay) * i / n) for i in range(n)]
        out.append(pts[-1])
        return out

    @staticmethod
    def _calm(calm, x, y):
        """0 at a calm point (a planned crossing), rising to 1 beyond its radius: the stream runs
        straight and keeps its width where a bridge or ford crosses it."""
        f = 1.0
        for (cu, cv), r_uv in calm:
            cx, cy = uv_to_xy(cu, cv)
            r = r_uv / SQ2
            d = math.hypot(x - cx, y - cy)
            if d < r: f = min(f, 0.0)
            elif d < 2 * r: f = min(f, (d - r) / r)
        return f

    def _smooth_path(self, path_uv, wiggle, calm=()):
        """Polyline (uv) -> dense, gently meandering centre line in cell coordinates (straight within
        the calm stretches)."""
        pts = [uv_to_xy(u, v) for u, v in path_uv]
        dense = self._densify(pts, 0.5)
        if wiggle <= 0 or len(dense) < 3: return dense
        nz = self._noise(self.rng, 3)
        out = []
        for i, (x, y) in enumerate(dense):
            a, b = dense[max(0, i - 1)], dense[min(len(dense) - 1, i + 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(tx, ty) or 1
            off = wiggle * nz(i * 0.12) * self._calm(calm, x, y)
            out.append((x - ty / ln * off, y + tx / ln * off))
        return out

    # ------------------------------------------------------------------ bodies of water
    def stream(self, path_uv, width=3.0, family="clear", wiggle=2.0, deep=None, calm=()):
        """Natural stream along a uv polyline. width is in tiles (Westwood: typically 1-3, widest
        about 5). Deep water only where at least 2 tiles from the bank (deep=None: automatic).
        calm: [(uv point, radius uv)] where the stream runs straight at its plain width (planned
        crossings: a bridge goes on a straight stretch, square to the water, never on a bend)."""
        shallow_m, deep_m, _ = FAMILIES[family]
        line = self._smooth_path(path_uv, wiggle, calm)
        nz = self._noise(self.rng, 4)
        half = [max(0.75, width * TILE / 2 * (1 + 0.28 * nz(i * 0.09) * self._calm(calm, *line[i]))) for i in range(len(line))]
        body = Body("stream", family, path_xy=line, widths=half)
        xs, ys = [p[0] for p in line], [p[1] for p in line]
        pad = max(half) + 2
        for (x, y) in list(self.spec.floor):
            cx, cy = tile_centre_xy(x, y)
            if not (min(xs) - pad <= cx <= max(xs) + pad and min(ys) - pad <= cy <= max(ys) + pad): continue
            if not self._ok((x, y)): continue
            d, h = self._dist_to_line(cx, cy, line, half)
            jitter = 0.25 * math.sin(x * 1.7 + y * 2.3)
            if d <= h + jitter:
                body.tiles.add((x, y))
        for (x, y) in body.tiles:
            cx, cy = tile_centre_xy(x, y)
            d, h = self._dist_to_line(cx, cy, line, half)
            from_bank = h - d
            is_deep = (deep is True or (deep is None and width >= 3.5)) and from_bank >= 2 * TILE - 0.2
            self.spec.floor[(x, y)] = deep_m if is_deep else shallow_m
        self.bodies.append(body)
        return body

    def pond(self, centre_uv, radius=6.0, family="clear", roughness=0.35):
        """Pond or lake with an irregular round shore. radius in tiles."""
        shallow_m, deep_m, _ = FAMILIES[family]
        cx0, cy0 = uv_to_xy(*centre_uv)
        nz = self._noise(self.rng, 4)
        r_cells = radius * TILE
        body = Body("pond", family, path_xy=[(cx0, cy0)], widths=[r_cells])
        for (x, y) in list(self.spec.floor):
            cx, cy = tile_centre_xy(x, y)
            dx, dy = cx - cx0, cy - cy0
            d = math.hypot(dx, dy)
            if d > r_cells * (1 + roughness) + 1 or not self._ok((x, y)): continue
            ang = math.atan2(dy, dx)
            rr = r_cells * (1 + roughness * (0.7 * nz(ang * 2.0) + 0.3 * math.sin(ang * 7 + 1.3)))
            if d <= rr:
                body.tiles.add((x, y))
                self.spec.floor[(x, y)] = deep_m if rr - d >= 2 * TILE - 0.2 else shallow_m
        self.bodies.append(body)
        return body

    def lava(self, path_uv, width=3.0, wiggle=4.5, bank="VolcanicCraggy", bank_width=1.5):
        """Lava flow along a uv polyline with a craggy volcanic bank (Westwood: Lava next to
        VolcanicCraggy, never directly next to other floors)."""
        line = self._smooth_path(path_uv, wiggle)
        nz = self._noise(self.rng, 4)
        half = [max(0.75, width * TILE / 2 * (1 + 0.4 * nz(i * 0.11))) for i in range(len(line))]
        body = Body("lava", "lava", path_xy=line, widths=half)
        for (x, y) in list(self.spec.floor):
            if not self._ok((x, y)): continue
            cx, cy = tile_centre_xy(x, y)
            d, h = self._dist_to_line(cx, cy, line, half)
            h += 0.35 * math.sin(x * 1.9 + y * 1.1) + 0.25 * math.sin(x * 0.7 - y * 2.3)   # ragged edge
            if d <= h:
                body.tiles.add((x, y)); self.spec.floor[(x, y)] = "Lava"
            elif d <= h + bank_width * TILE + 0.3 * math.sin(x * 1.3 + y * 0.7):
                self.spec.floor[(x, y)] = bank
        self.bodies.append(body)
        return body

    @staticmethod
    def _dist_to_line(px_, py_, line, half):
        best, bh = 1e9, 0
        for i in range(len(line) - 1):
            (ax, ay), (bx, by) = line[i], line[i + 1]
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy or 1e-9
            t = max(0.0, min(1.0, ((px_ - ax) * dx + (py_ - ay) * dy) / L2))
            d = math.hypot(px_ - (ax + t * dx), py_ - (ay + t * dy))
            if d < best: best, bh = d, half[i] + (half[i + 1] - half[i]) * t
        return best, bh

    # ------------------------------------------------------------------ crossings
    def _crossing_frame(self, body, t):
        """Point on the body's centre line at fraction t, with its tangent (cells) and half-width."""
        i = min(len(body.path_xy) - 2, max(0, int(t * (len(body.path_xy) - 1))))
        (ax, ay), (bx, by) = body.path_xy[i], body.path_xy[i + 1]
        tx, ty = bx - ax, by - ay
        ln = math.hypot(tx, ty) or 1
        return (ax, ay), (tx / ln, ty / ln), body.widths[i]

    def _crossing_rect(self, body, t, deck_width, landing, at=None, along=None):
        """uv rectangle across the body at t: (axis along which the crossing runs, u0, u1, v0, v1).
        at (uv) and along ('u'/'v'): a crossing planned with the road (Land.plan_crossing)."""
        if at is not None:
            ax, ay = uv_to_xy(*at)
            i = min(range(len(body.path_xy)), key=lambda k: (body.path_xy[k][0] - ax) ** 2 + (body.path_xy[k][1] - ay) ** 2)
            h = body.widths[i]
            (cu, cv), across = at, along
        else:
            (cx, cy), (tx, ty), h = self._crossing_frame(body, t)
            cu, cv = xy_to_uv(cx, cy)
            tu, tv = tx + ty, tx - ty                   # tangent in uv
            across = "v" if abs(tu) >= abs(tv) else "u"  # cross perpendicular-ish to the flow
        span = h * SQ2 + landing * 2                     # half-length in uv units (+ landing tiles)
        half_w = deck_width                              # in uv units: 2 per tile
        r2 = lambda a: int(round(a / 2.0)) * 2
        if across == "v":
            return across, r2(cu - half_w), r2(cu + half_w), r2(cv - span), r2(cv + span)
        return across, r2(cu - span), r2(cu + span), r2(cv - half_w), r2(cv + half_w)

    def _rect_tiles(self, u0, u1, v0, v1):
        out = []
        for u in range(u0, u1 + 1, 2):
            for v in range(v0, v1 + 1, 2):
                x, y = uv_to_xy(u - 2, v)
                if x == int(x) and (int(x), int(y)) in self.spec.floor:
                    out.append((int(x), int(y)))
        return out

    def plank_bridge(self, body, t=0.5, deck_width=2, landing=1, material="WoodSlatFloor", at=None, along=None):
        """Square plank deck across a stream (Con05A style): planks spill onto the water and banks
        around them (WoodSlatEdge); shore walls beside the deck act as railings. at/along: a crossing
        planned with the road (Land.plan_crossing), so the deck runs in the road's direction."""
        across, u0, u1, v0, v1 = self._crossing_rect(body, t, deck_width, landing, at, along)
        tiles = self._rect_tiles(u0, u1, v0, v1)
        for c in tiles:
            self.spec.floor[c] = material
            # clear shore walls only: a visible wall here is the map's boundary and must stay
            if self.spec.wallmap.get(c, {}).get("material", "Invisible").startswith("Invisible"):
                self.spec.remove_wall(*c)
            self.no_walls.add(c)
        self.bridge_materials.add(material)
        return dict(kind="plank_bridge", tiles=tiles, rect=(u0, u1, v0, v1), across=across)

    def ford(self, body, t=0.5, width=3, material="DirtDark2"):
        """Natural ford: a short land strip across shallow water (water spills onto it)."""
        across, u0, u1, v0, v1 = self._crossing_rect(body, t, width, 0)
        tiles = [c for c in self._rect_tiles(u0, u1, v0, v1) if c in body.tiles]
        shallow_m = FAMILIES[body.family][0]
        for c in tiles:
            self.spec.floor[c] = material
            self.no_walls.add(c)
        # deepen nothing: ensure the water touching the ford is shallow, as at a real ford
        for (x, y) in list(body.tiles):
            if self.spec.floor.get((x, y)) in WATER_MATERIALS and any(
                    (x + a, y + b) in tiles for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)):
                self.spec.floor[(x, y)] = shallow_m
        return dict(kind="ford", tiles=tiles)

    # ------------------------------------------------------------------ object kits
    def _strip(self, kit, lane, a0, a1):
        """Two-row floor strip for a kit from a0 to a1 along its axis (visual coordinates): the lane
        row stays walkable; walls go on the second row and on the row beyond the lane."""
        k = KITS[kit]
        axis = k["axis"]
        second = lane + (2 if axis == "u" else -2)
        lo, hi = int(math.ceil(min(a0, a1))), int(math.floor(max(a0, a1)))
        lo += lo % 2
        fluid = WATER_MATERIALS | LAVA_MATERIALS
        lane_tiles = []
        for a in range(lo, hi + 1, 2):
            open_here = False
            for r in (lane, second):
                c = tile_at_uv(a, r) if axis == "u" else tile_at_uv(r, a)
                if self.spec.floor.get(c) is not None and self.spec.floor[c] not in fluid:
                    continue                          # banks keep their own ground
                open_here = True
                self.spec.floor[c] = k["floor"]
                self.spec.remove_wall(*c)
                if r == lane:
                    lane_tiles.append(c)
                    self.no_walls.add(c)
            if not open_here:
                continue
            # wall cells use raw coordinates (a tile's visual u is its raw u + 2)
            if axis == "u":
                cells = [uv_to_xy(a - 2, lane - 2), uv_to_xy(a - 2, lane + 2)]
            else:
                cells = [uv_to_xy(lane - 4, a), uv_to_xy(lane, a)]
            for wx, wy in cells:
                c = (int(wx), int(wy))
                if wx == int(wx) and c not in self.no_walls and (self.spec.floor.get(c) in fluid | {k["floor"]} or c not in self.spec.floor):
                    self.kit_walls.add(c)
        self.kit_lanes.append(lane_tiles)
        return lane_tiles

    def dock(self, body, direction="down", length=2, at=None, barrels=True, beyond=0, near=None):
        """Dock into a pond/lake. direction 'down' = DockDown running down-right (along '\\'),
        'up' = DockUp running down-left (along '/'). length = number of centre pieces.
        at: land tile-centre (uv) on the shore to start from; default: picked on the shore."""
        kit = "DockDown" if direction == "down" else "DockUp"
        k = KITS[kit]
        st = k["steps"]
        reach = st["first"] + st["mid"] * (length - 1) + st["last"]
        start = at or self._shore_start(body, kit, reach, beyond, near)
        if start is None:
            return None
        su, sv = start
        if kit == "DockDown":
            lane = int(round((sv - k["piece_side"]) / 2.0)) * 2
            pos, sign = su + 1.0, 1                    # ramp sits on the waterline
        else:
            lane = int(round((su - k["piece_side"]) / 2.0)) * 2
            pos, sign = sv - 1.0, -1
        if kit == "DockUp": length = 1                     # Westwood's DockUp has one centre piece
        names = ["FarRamp" if kit == "DockDown" else "FarEnd"] + ["Center1"] * length + ["NearEnd"]
        u0, v0 = (pos, lane + k["piece_side"]) if kit == "DockDown" else (lane + k["piece_side"], pos)
        pts = chain_positions(kit, px_of_uv(u0, v0), length)
        pieces = []
        for name, (x, y) in zip(names, pts):
            self.spec.obj_px(kit + name, x, y)
            pu, pv = (x + y) / CELL, (x - y) / CELL         # back to u/v for the floor strip and barrels
            pieces.append((name, pu if kit == "DockDown" else pv))
        far = pieces[0][1]
        pos = pieces[-1][1]
        self._strip(kit, lane, far, pos + sign)
        if barrels:                                    # Con05A docks carry a barrel or two near the tip
            for i in range(self.rng.choice((0, 1, 2))):
                p = pos - sign * (2.0 + 1.6 * i)
                u, v = (p, lane + k["piece_side"] + 0.4) if kit == "DockDown" else (lane + k["piece_side"] + 0.4, p)
                self.spec.obj_px(self.rng.choice(("Barrel", "Barrel2")), *px_of_uv(u, v))
        tip = int(round(pos / 2.0)) * 2 + 4 * sign      # wall closing the end of the dock
        cx, cy = uv_to_xy(tip - 2, lane) if kit == "DockDown" else uv_to_xy(lane - 2, tip)
        if cx == int(cx):
            self.kit_walls.add((int(cx), int(cy)))
        return dict(kind=kit, start=start, pieces=pieces, lane=lane)

    def _shore_start(self, body, kit, reach, beyond=0, near=None):
        """A land tile on the shore from which a dock can run `reach` uv units over water, with
        `beyond` more tiles of open water past its tip (a dock reaches out into a lake; it never
        spans a puddle to the far bank). near (uv): prefer the shore spot closest to it, e.g.
        where the road arrives."""
        step = (1, 1) if kit == "DockDown" else (-1, 1)        # next tile along the dock direction
        side = ((1, -1), (-1, 1)) if kit == "DockDown" else ((1, 1), (-1, -1))
        n = int(reach / 2) + 3 + beyond
        taken = [c for lane in self.kit_lanes for c in lane]
        cands = []
        for (x, y) in body.tiles:
            land = (x - step[0], y - step[1])
            if not self._land(land) or land in self.no_walls:
                continue
            path = [(land[0] + step[0] * i, land[1] + step[1] * i) for i in range(1, n)]
            if not all(self.spec.floor.get(c) in WATER_MATERIALS for c in path):
                continue
            if not all(self.spec.floor.get((c[0] + sx, c[1] + sy)) in WATER_MATERIALS for c in path[1:] for sx, sy in side):
                continue
            if any(abs(c[0] - t[0]) + abs(c[1] - t[1]) < 12 for c in [land] + path for t in taken):
                continue                               # keep docks well apart
            cands.append(xy_to_uv(*tile_centre_xy(*land)))
        if not cands:
            return None
        if near:
            return min(cands, key=lambda c: (c[0] - near[0]) ** 2 + (c[1] - near[1]) ** 2)
        cands.sort()
        return cands[len(cands) // 2]

    def rope_bridge(self, a_uv, b_uv, kit=None, broken=False):
        """Rope bridge between two uv points (over water or a chasm). The axis is chosen from the
        span direction: RopeBridge1 along '\\' (u changes), RopeBridge2 along '/' (v changes)."""
        (au, av), (bu, bv) = a_uv, b_uv
        kit = kit or ("RopeBridge1" if abs(bu - au) >= abs(bv - av) else "RopeBridge2")
        return self._chain_bridge(kit, a_uv, b_uv, centres=("Center2", "Center"))

    def lava_bridge(self, a_uv, b_uv):
        (au, av), (bu, bv) = a_uv, b_uv
        kit = "LavaBridge1" if abs(bu - au) >= abs(bv - av) else "LavaBridge2"
        return self._chain_bridge(kit, a_uv, b_uv, centres=("Center",))

    def _chain_bridge(self, kit, a_uv, b_uv, centres):
        k = KITS[kit]
        (au, av), (bu, bv) = a_uv, b_uv
        if k["axis"] == "u":                 # FarEnd at the smaller u (up-left)
            line = (av + bv) / 2
            lane = int(round((line - k["piece_side"]) / 2.0)) * 2
            a0, a1 = min(au, bu), max(au, bu)
        else:                                # FarEnd at the larger v (up-right)
            line = (au + bu) / 2
            lane = int(round((line - k["piece_side"]) / 2.0)) * 2
            a0, a1 = max(av, bv), min(av, bv)
        length = abs(a1 - a0)
        if "steps_px" in k:
            sp = k["steps_px"]; f, m, l = (sp["first"] / CELL * 2, sp["mid"] / CELL * 2, sp["last"] / CELL * 2)
            n_mid = max(0, round((length - f - l) / m))
            offs = [0.0, f] + [f + m * (i + 1) for i in range(n_mid)]
            offs.append(offs[-1] + l)
            names = ["FarEnd"] + [centres[0]] * (len(offs) - 2) + ["NearEnd"]
        else:
            n = max(3, round(length / k["step"]) + 1)
            offs = [k["step"] * i for i in range(n)]
            names = ["FarEnd"] + [centres[i % len(centres)] for i in range(n - 2)] + ["NearEnd"]
        sgn = 1 if k["axis"] == "u" else -1
        u0, v0 = (a0, lane + k["piece_side"]) if k["axis"] == "u" else (lane + k["piece_side"], a0)
        pts = chain_positions(kit, px_of_uv(u0, v0), len(names) - 2)
        bx, by = KIT_STEPS[kit]["back"]
        for name, (x, y) in zip(names, pts):
            self.spec.obj_px(f"{kit}{name}Front", x, y)
            self.spec.obj_px(f"{kit}{name}Back", x + bx, y + by)
        lx, ly = pts[-1]
        end = (lx + ly) / CELL if k["axis"] == "u" else (lx - ly) / CELL
        self._strip(kit, lane, a0 - 2 * sgn, end + 2 * sgn)
        return dict(kind=kit, pieces=list(zip(names, offs)), lane=lane)

    # ------------------------------------------------------------------ finishing
    def finish(self, dress=True, shore_wall_material="InvisibleWallSet"):
        """Bank edge blending, shore walls, kit walls and (optionally) water dressing."""
        self._register_blending()
        fluid = WATER_MATERIALS | LAVA_MATERIALS
        for (x, y), m in list(self.spec.floor.items()):
            if m not in fluid or (x, y) in self.no_walls or (x, y) in self.spec.wallmap: continue
            nbrs = [(x + a, y + b) for a, b in ((1, 1), (1, -1), (-1, 1), (-1, -1))]
            if any(n not in self.spec.floor for n in nbrs + [(x + 2, y), (x - 2, y), (x, y + 2), (x, y - 2)]):
                # next to the void: the outer boundary must be a visible wall (Westwood places the
                # boundary material on water cells by the void), never an invisible one
                near = [(abs(wx - x) + abs(wy - y), w["material"]) for (wx, wy), w in self.spec.wallmap.items()
                        if abs(wx - x) <= 3 and abs(wy - y) <= 3 and not w["material"].startswith("Invisible")]
                if near and any(self.spec.floor.get(n) not in fluid and n in self.spec.floor for n in nbrs):
                    self.spec.wall(x, y, min(near)[1])
                continue
            if self.inside and not self.inside(x, y): continue
            if any(self.spec.floor.get(n) not in fluid for n in nbrs):
                self.spec.wall(x, y, shore_wall_material)
        for c in self.kit_walls:
            if c not in self.spec.wallmap and c not in self.no_walls:
                self.spec.wall(c[0], c[1], shore_wall_material)
        if dress: self._dress()

    def _register_blending(self):
        """Water/lava/plank materials spill onto what they touch, with the edge type Westwood uses
        for that pair (floors.json blend table); kit floors (docks, rope bridges) get no edges."""
        sp = self.spec
        pairs = {(e["overlay"], e["base"]): e for e in self.floors["blend"]}
        prio = {}
        for b in self.bodies:
            if b.family == "lava":
                prio.update({"Lava": (7, "BlendEdge"), "VolcanicCraggy": (3, "BlendEdge")})
            else:
                sh, dp, edge = FAMILIES[b.family]
                prio[sh] = (5, edge)
                if dp != sh:
                    prio[dp] = (6, "BlendEdge")
        for m in self.bridge_materials:
            prio[m] = (8, "WoodSlatEdge" if m == "WoodSlatFloor" else "WoodSlatEdge2" if m == "WoodSlatFloor2" else "BlendEdge")
        touched = set()
        for (x, y), m in sp.floor.items():
            if m in prio:
                for a, bb in ((1, 1), (1, -1), (-1, 1), (-1, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
                    n = sp.floor.get((x + a, y + bb))
                    if n and n not in prio and n not in KIT_FLOORS:
                        touched.add(n)
        for m, (p, e) in prio.items():
            if m not in sp.blend or sp.blend[m][0] < p:
                sp.blending(m, p, e)
        for n in touched:
            if n in sp.blend:
                continue
            # rank it just above the existing materials it draws over in Westwood's maps
            over = [sp.blend[b][0] for b in sp.blend if b not in prio and ((pairs.get((n, b)) or {}).get("overlay_direction_share") or 0) >= 0.5]
            sp.blending(n, max(over) + 0.5 if over else -10)
        for m in prio:
            if m in self.bridge_materials:
                continue                              # planks always use their own edge
            for n in touched | set(prio):
                e = pairs.get((m, n))
                if e and e.get("edge_share_sp", 0) >= 0.5 and e.get("overlay_direction_share", 0) >= 0.5 and e.get("preferred_edge_type"):
                    sp.edge_over[(m, n)] = e["preferred_edge_type"]

    def _dress(self):
        """Reeds, ripples and lily pads on water; bubbles and crust on lava (decoration palettes),
        plus a brook sound now and then. Kept off crossings and kit lanes."""
        pal = self.deco["palettes_by_material"]
        skip = ("Stalag", "Pillar", "Sewer", "Brick", "CaveRock", "Gargoyle", "Bridge", "Column")
        occupied = set(self.no_walls)
        for b in self.bodies:
            tiles = [c for c in b.tiles if self.spec.floor.get(c) in WATER_MATERIALS | LAVA_MATERIALS and c not in occupied]
            if not tiles: continue
            mat = "Lava" if b.family == "lava" else FAMILIES[b.family][0]
            p = pal.get(mat)
            if not p: continue
            types = [(t, w) for t, w in p["top_types"] if not any(s in t for s in skip)]
            if not types: continue
            names, weights = zip(*types)
            n = int(len(tiles) * p["objects_per_100_tiles"] / 100 * 0.8)
            # reeds and rushes grow in the shallows: within two tiles of the bank; ripples and lily
            # pads may float anywhere
            fluid = WATER_MATERIALS | LAVA_MATERIALS
            shore = {c for c in tiles if any((c[0] + a, c[1] + b) in self.spec.floor and self.spec.floor[(c[0] + a, c[1] + b)] not in fluid
                                             for a in range(-4, 5) for b in range(-4, 5) if (a + b) % 2 == 0 and abs(a) + abs(b) <= 4)}
            for c in self.rng.sample(tiles, min(n, len(tiles))):
                t = self.rng.choices(names, weights)[0]
                if REEDS.search(t) and c not in shore: continue
                cx, cy = tile_centre_xy(*c)
                self.spec.obj_px(t, (cx + self.rng.uniform(-0.4, 0.4)) * CELL, (cy + self.rng.uniform(-0.4, 0.4)) * CELL)
            if b.family != "lava":
                for c in self.rng.sample(tiles, min(len(tiles), max(1, len(tiles) // 60))):
                    cx, cy = tile_centre_xy(*c)
                    self.spec.obj_px(self.rng.choice(["AmbBrook1", "AmbBrook2", "AmbBrook3"]), cx * CELL, cy * CELL)
