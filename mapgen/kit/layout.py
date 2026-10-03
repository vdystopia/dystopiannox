"""Layout planner (generator v3): the walkable shape, roads, a village square and building lots.

Order of work: from the centre outwards. The central feature (the square) is placed first, then the
buildings around it, then the roads out to the other areas and their features, and only then does
the land grow around everything that was placed (a margin of open ground with an irregular edge),
ending in the forest wall. Working inward from fixed borders instead squeezes the village into
whatever room is left.

Westwood's outdoor maps (review/RUBRIC.md, criteria 1-3) are winding, branching corridors cut out of
darkness by forest walls. Distinct areas (village, glades, clearings) are joined by narrower passages,
a dirt road runs down every passage to every area, and the village packs its buildings along the
roads around a square.

Geometry: the land is a set of "squares", one per floor tile. Square (i, j) is the tile at uv
(2i, 2j), which is grid cell (i + j, i - j), and it covers u in [2i, 2i+2] and v in [2j-2, 2j], as
Spec.room lays out tiles. Wall points (p, q) sit at uv (2p, 2q), grid cell (p + q, p - q). A point
gets a wall when the four squares touching it are partly land and partly void. Spec then shapes
each piece from its neighbours, so staircase outlines draw as Westwood's zigzag forest walls.
"""
import collections, math
from nox import CELL, px

OUTDOOR_FLOORS = ("Grass", "Dirt", "RoughCobble", "Water", "WoodSlat")
SQ = 2 * CELL / math.sqrt(2)          # one square's side in world px (32.5)
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))

# floor blending for the outdoor set, ordered as Westwood overlays them (rules/out/floors.json blend)
OUTDOOR_BLENDS = [("GrassNorm", 0, "BlendEdge"), ("GrassSparse2", 1, "BlendEdge"), ("GrassDense", 2, "BlendEdge"),
                  ("DirtLight2", 3, "BlendEdge"), ("DirtDark2", 4, "BlendEdge"), ("RoughCobble", 5, "BrickEdgeBrown")]


def square_tile(i, j):
    return i + j, i - j


def point_cell(p, q):
    return p + q, p - q


def square_px(si, sj):
    """World px of a point in square coordinates (square (i, j) spans si in [i, i+1], sj in [j-1, j]).
    The square's centre (i + 0.5, j - 0.5) is the centre of its tile (i + j, i - j), which the game
    draws at grid corner (x + 1, y + 1)."""
    return px(2 * si + 1, 2 * sj + 1)


def px_square(x, y):
    """Square whose tile contains a world-px point (inverse of square_px)."""
    u, v = (x + y) / CELL, (x - y) / CELL
    return int(math.floor((u - 1) / 2)), int(math.floor((v - 1) / 2)) + 1


def tile_square(x, y):
    """Square of a floor tile (x, y) (x + y even): inverse of square_tile."""
    return (x + y) // 2, (x - y) // 2


def cell_square(x, y):
    return px_square((x + 0.5) * CELL, (y + 0.5) * CELL)


def _chaikin(pts, n=3):
    for _ in range(n):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        out.append(pts[-1])
        pts = out
    return pts


def _densify(pts, step=0.5):
    out = []
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    return out + [pts[-1]]


def dist_to_path(p, path):
    best, bi = 1e9, 0
    for k in range(len(path) - 1):
        (ax, ay), (bx, by) = path[k], path[k + 1]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy or 1e-9
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        d = math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)
        if d < best: best, bi = d, k
    return best, bi


def bfs_distance(sources, allowed, limit=40):
    """Square -> 4-step distance from the nearest source, over `allowed` squares."""
    dist = {s: 0 for s in sources}
    q = collections.deque(sources)
    while q:
        s = q.popleft()
        if dist[s] >= limit: continue
        for a, b in N4:
            n = (s[0] + a, s[1] + b)
            if n in allowed and n not in dist:
                dist[n] = dist[s] + 1; q.append(n)
    return dist


class Land:
    """The walkable shape of an outdoor map, built from areas joined by curving passages."""

    def __init__(self, rng, u_range=(150, 380), v_range=(-110, 110)):
        self.rng = rng
        self.i_range = (u_range[0] // 2, u_range[1] // 2)
        self.j_range = (v_range[0] // 2, v_range[1] // 2)
        self.areas, self.links = {}, []
        # before carve() the whole planning canvas is available; carve() shrinks it to the land
        self.squares = {(i, j) for i in range(*self.i_range) for j in range(*self.j_range)
                        if 3 <= i + j <= 250 and 3 <= i - j <= 250}
        self.reserved = set()                 # squares kept for planned features (a stream and its banks)
        self.wall_cells = set()               # grid cells of building walls (set by the design as it builds)
        self.crossings = []                   # planned bridges and fords (plan_crossing)
        self.roads, self.plaza, self.water, self.taken = set(), set(), set(), set()
        self.taken_strict = set()             # building footprints only (taken also holds margins)
        self.road_paths = []

    # ---- planning ------------------------------------------------------------------------------------
    def area(self, name, centre_uv, radius_uv, stretch=1.0, angle=0.0, roughness=0.26, clearing=True):
        """A rounded area (village, glade, clearing). radius in uv units; stretch elongates it along
        `angle` (radians, in uv space); roughness gives the outline its irregular bulges."""
        r = self.rng
        waves = [(k, r.uniform(0, 2 * math.pi), roughness * r.uniform(0.5, 1.0) / (1 + 0.5 * n))
                 for n, k in enumerate((2, 3, 5, 7, 11))]
        # clearing=False: the area's extent comes from what is built in it (a village grows around its
        # square and buildings); radius then only bounds where its lots may go
        self.areas[name] = dict(c=(centre_uv[0] / 2, centre_uv[1] / 2), r=radius_uv / 2, stretch=stretch, angle=angle,
                                waves=waves, clearing=clearing)

    def link(self, a, b, width_uv, bend=0.32, road=True, pockets=(1, 2)):
        """A curving passage between two areas (and, with road=True, a road along its middle)."""
        ca, cb = self.areas[a]["c"], self.areas[b]["c"]
        dx, dy = cb[0] - ca[0], cb[1] - ca[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        k1, k2 = self.rng.uniform(-bend, bend) * L, self.rng.uniform(-bend, bend) * L
        pts = [ca, (ca[0] + dx / 3 + nx * k1, ca[1] + dy / 3 + ny * k1),
               (ca[0] + 2 * dx / 3 + nx * k2, ca[1] + 2 * dy / 3 + ny * k2), cb]
        path = _densify(_chaikin(pts), 0.5)
        waves = [(self.rng.uniform(0.15, 0.9), self.rng.uniform(0, 6.3)) for _ in range(3)]
        self.links.append(dict(a=a, b=b, half=width_uv / 4, path=path, waves=waves, road=road))
        # side pockets: small bays off the passage, as in Westwood's forest corridors
        for k in range(self.rng.randint(*pockets)):
            t = self.rng.uniform(0.25, 0.75)
            si, sj = path[int(t * (len(path) - 1))]
            side = self.rng.choice((-1, 1))
            off = width_uv / 4 * self.rng.uniform(0.9, 1.3)
            r_uv = width_uv * self.rng.uniform(0.35, 0.6)
            self.area(f"pocket_{a}_{b}_{k}", (2 * (si + side * nx * off), 2 * (sj + side * ny * off)), r_uv, roughness=0.3)

    def _in_area(self, s, ar):
        cx, cy = ar["c"]
        dx, dy = s[0] - cx, s[1] - cy
        ca, sa = math.cos(-ar["angle"]), math.sin(-ar["angle"])
        rx, ry = dx * ca - dy * sa, dx * sa + dy * ca
        rx /= ar["stretch"]
        d = math.hypot(rx, ry)
        th = math.atan2(ry, rx)
        R = ar["r"] * (1 + sum(a * math.sin(k * th + p) for k, p, a in ar["waves"]))
        return d <= R

    def plan_crossing(self, a, b, t=0.5, approach=7.0):
        """Plans where the road between areas a and b crosses water, before anything is built: a bridge
        fitted onto an existing stream ends up jammed against the forest. The road is straightened
        through the crossing along the nearest grid axis for `approach` squares on each side, so the deck
        runs in the road's direction and lands on the road at both ends. Returns the crossing: centre
        (square coordinates), uv centre, axis ('u' or 'v': the way the deck runs) and the direction the
        water must flow there (across the road)."""
        ln = next(l for l in self.links if (l["a"], l["b"]) == (a, b))
        path = ln["path"]
        k = int(t * (len(path) - 1))
        P = path[k]
        pa, pb = path[max(0, k - 4)], path[min(len(path) - 1, k + 4)]
        ti, tj = pb[0] - pa[0], pb[1] - pa[1]
        axis = "u" if abs(ti) >= abs(tj) else "v"
        d = (1.0 if ti >= 0 else -1.0, 0.0) if axis == "u" else (0.0, 1.0 if tj >= 0 else -1.0)
        A = (P[0] - d[0] * approach, P[1] - d[1] * approach)
        B = (P[0] + d[0] * approach, P[1] + d[1] * approach)
        near = lambda pt, lo, hi: min(range(lo, hi), key=lambda i: (path[i][0] - pt[0]) ** 2 + (path[i][1] - pt[1]) ** 2)
        i0, i1 = near(A, 0, k + 1), near(B, k, len(path))
        ln["path"] = (path[:i0] + _densify([path[i0], A], 0.5)[:-1] + _densify([A, B], 0.5) +
                      _densify([B, path[i1]], 0.5)[1:] + path[i1 + 1:])
        corridor = set()
        for s_ in _densify([A, B], 0.5):              # the straight road through the crossing
            for i in range(int(s_[0]) - 2, int(s_[0]) + 3):
                for j in range(int(s_[1]) - 2, int(s_[1]) + 4):
                    corridor.add((i, j))
        cross = dict(link=(a, b), centre=P, uv=(2 * P[0] + 1, 2 * P[1] + 1), axis=axis,
                     flow=(0.0, 1.0) if axis == "u" else (1.0, 0.0), corridor=corridor)
        self.crossings.append(cross)
        return cross

    def reserve_band(self, path_uv, half_squares):
        """Keeps squares within `half_squares` of a uv polyline for a planned feature (a stream and its
        banks), so buildings and roads placed before the water leave room for it."""
        pts = _densify([(u / 2, v / 2) for u, v in path_uv], 0.5)
        for si, sj in pts:
            for i in range(int(si - half_squares - 1), int(si + half_squares + 2)):
                for j in range(int(sj - half_squares - 1), int(sj + half_squares + 2)):
                    if math.hypot(i + 0.5 - si, j - 0.5 - sj) <= half_squares: self.reserved.add((i, j))

    def carve(self, margin=4.0, roughness=0.45):
        """Grows the land around everything placed so far: squares within `margin` squares (varied
        by smooth noise for an irregular edge) of the roads, the square, buildings, reserved water and
        props, plus the clearing areas. Then smooths the outline so every wall line is continuous and
        no passage is narrower than 3 squares; placed content is never cut away."""
        canvas = self.squares
        content = (set(self.roads) | self.plaza | self.taken | self.water | self.reserved) & canvas
        r = self.rng
        ph = [r.uniform(0, 6.3) for _ in range(6)]
        noise = lambda i, j: (math.sin(i * 0.23 + ph[0]) + math.sin(j * 0.19 + ph[1]) + math.sin((i + j) * 0.11 + ph[2])
                              + 0.6 * math.sin((i - j) * 0.37 + ph[3])) / 3.6
        dist = bfs_distance(list(content), canvas, int(margin * (1 + roughness)) + 2)
        sq = {s for s, d in dist.items() if d <= margin * (1 + roughness * noise(*s))}
        for (i, j) in canvas:
            s = (i + 0.5, j - 0.5)
            if any(ar["clearing"] and self._in_area(s, ar) for ar in self.areas.values()):
                sq.add((i, j)); continue
            for ln in self.links:
                if ln["road"]: continue                       # road passages grow from the road itself
                d, k = dist_to_path(s, ln["path"])
                if d <= ln["half"]: sq.add((i, j)); break
        keep = content | {(i + a, j + b) for i, j in content for a, b in N8}
        sq |= keep
        for _ in range(2):                                     # majority smoothing (placed content stays)
            nxt = set()
            for (i, j) in {(i + a, j + b) for i, j in sq for a, b in N8}:
                n = sum((i + a, j + b) in sq for a, b in N8)
                if n >= 5 or ((i, j) in sq and n >= 4): nxt.add((i, j))
            sq = nxt | keep
        for _ in range(3):                                     # no spurs or 1-2 square necks
            sq = {s for s in sq if s in keep or sum((s[0] + a, s[1] + b) in sq for a, b in N4) >= 3 or
                  (sum((s[0] + a, s[1] + b) in sq for a, b in N4) == 2 and not self._neck(s, sq))}
        sq = self._largest(sq)
        sq |= self._holes(sq)
        sq = self._fix_pinches(sq)
        # stay on the map grid with room for the boundary walls
        self.squares = {s for s in sq if 3 <= s[0] + s[1] <= 250 and 3 <= s[0] - s[1] <= 250}
        return self.squares

    @staticmethod
    def _neck(s, sq):
        i, j = s
        return ((i + 1, j) in sq and (i - 1, j) in sq and (i, j + 1) not in sq and (i, j - 1) not in sq) or \
               ((i, j + 1) in sq and (i, j - 1) in sq and (i + 1, j) not in sq and (i - 1, j) not in sq)

    @staticmethod
    def _largest(sq):
        left, best = set(sq), set()
        while left:
            s = left.pop(); comp = {s}; q = [s]
            while q:
                a = q.pop()
                for d in N4:
                    n = (a[0] + d[0], a[1] + d[1])
                    if n in left: left.remove(n); comp.add(n); q.append(n)
            if len(comp) > len(best): best = comp
        return best

    @staticmethod
    def _holes(sq):
        i0 = min(i for i, _ in sq) - 1; i1 = max(i for i, _ in sq) + 1
        j0 = min(j for _, j in sq) - 1; j1 = max(j for _, j in sq) + 1
        outside, q = {(i0, j0)}, [(i0, j0)]
        while q:
            a = q.pop()
            for d in N4:
                n = (a[0] + d[0], a[1] + d[1])
                if i0 <= n[0] <= i1 and j0 <= n[1] <= j1 and n not in sq and n not in outside:
                    outside.add(n); q.append(n)
        # only small enclosed gaps are holes; a loop of passages encloses forest that must stay void
        enclosed = {(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1) if (i, j) not in sq and (i, j) not in outside}
        holes = set()
        while enclosed:
            s = enclosed.pop(); comp = {s}; q = [s]
            while q:
                a = q.pop()
                for d in N4:
                    n = (a[0] + d[0], a[1] + d[1])
                    if n in enclosed: enclosed.remove(n); comp.add(n); q.append(n)
            if len(comp) <= 40: holes |= comp
        return holes

    @staticmethod
    def _fix_pinches(sq):
        """A wall point whose land squares touch only diagonally would draw a cross through the
        passage; fill one of the void squares."""
        changed = True
        while changed:
            changed = False
            pts = {(i + a, j + b) for i, j in sq for a in (0, 1) for b in (-1, 0)}
            for p, q in pts:
                quad = [(p - 1, q), (p, q), (p - 1, q + 1), (p, q + 1)]
                ins = [s in sq for s in quad]
                if ins == [True, False, False, True] or ins == [False, True, True, False]:
                    sq.add(quad[ins.index(False)]); changed = True
        return sq

    # ---- writing ------------------------------------------------------------------------------------
    def boundary_points(self):
        pts = set()
        for i, j in self.squares:
            for p, q in ((i, j), (i + 1, j), (i, j - 1), (i + 1, j - 1)):
                quad = [(p - 1, q), (p, q), (p - 1, q + 1), (p, q + 1)]
                n = sum(s in self.squares for s in quad)
                if 0 < n < 4: pts.add((p, q))
        return pts

    def apply(self, spec, wall, floor):
        """Floor tiles on every land square and the forest wall around them."""
        for s in self.squares:
            spec.floor.setdefault(square_tile(*s), floor)      # roads, the square and buildings stay
        for p in self.boundary_points():
            x, y = point_cell(*p)
            spec.wall(x, y, wall)

    def ground_variety(self, spec, base="GrassNorm", sparse="GrassSparse2", dense="GrassDense", scale=1.0, clear=3):
        """Patches of sparse and dense grass on the base (smooth noise, as in Westwood's meadows).
        Call it after roads, water and the square: patches keep `clear` squares away from them, so
        every transition has room for its own blend (no three-way seams by a road or a bank)."""
        r = self.rng
        ph = [r.uniform(0, 6.3) for _ in range(4)]
        features = [s for s in self.squares if spec.floor.get(square_tile(*s)) != base] + list(self.taken)
        near = bfs_distance(features, self.squares, clear)
        for s in self.squares:
            t = square_tile(*s)
            if spec.floor.get(t) != base or near.get(s, 99) < clear: continue
            i, j = s
            n = math.sin(i * 0.17 * scale + ph[0]) + math.sin(j * 0.21 * scale + ph[1]) + 0.6 * math.sin((i - j) * 0.11 * scale + ph[2])
            if n > 1.05: spec.floor[t] = sparse
            elif n < -1.35: spec.floor[t] = dense

    def blends(self, spec):
        for mat, prio, edge in OUTDOOR_BLENDS:
            if mat not in spec.blend: spec.blending(mat, prio, edge)

    def edge_distance(self):
        """Square -> distance (squares) from the forest edge (1 = touching it)."""
        edge = [s for s in self.squares if any((s[0] + a, s[1] + b) not in self.squares for a, b in N8)]
        d = bfs_distance(edge, self.squares)
        return {s: v + 1 for s, v in d.items()}

    # ---- roads and the square -------------------------------------------------------------------------
    def paint_roads(self, spec, material="DirtDark2", width_squares=2.4, skip=()):
        """A dirt road down the middle of every passage, from area centre to area centre. Squares in
        `skip` (reserved water) are left, except on a planned crossing, where the road runs on to meet
        its bridge."""
        skip = set(skip) - set().union(*(c["corridor"] for c in self.crossings)) if self.crossings else skip
        for ln in self.links:
            if not ln["road"]: continue
            path = ln["path"]
            self.road_paths.append(path)
            nz = (self.rng.uniform(0, 6.3), self.rng.uniform(0.2, 0.5))
            for k, (si, sj) in enumerate(path):
                half = width_squares / 2 * (1 + 0.15 * math.sin(k * nz[1] + nz[0]))
                for i in range(int(si - half - 1), int(si + half + 2)):
                    for j in range(int(sj - half - 1), int(sj + half + 2)):
                        if (i, j) not in self.squares or (i, j) in skip or (i, j) in self.plaza: continue
                        if math.hypot(i + 0.5 - si, j - 0.5 - sj) <= half:
                            t = square_tile(i, j)
                            if "Water" in spec.floor.get(t, "") or "WoodSlat" in spec.floor.get(t, ""): continue
                            spec.floor[t] = material
                            self.roads.add((i, j))
        return self.roads

    def paint_square(self, spec, area, radius_uv, material="RoughCobble"):
        """A paved village square at the area's centre."""
        cx, cy = self.areas[area]["c"]
        r = radius_uv / 2
        for i in range(int(cx - r - 1), int(cx + r + 2)):
            for j in range(int(cy - r - 1), int(cy + r + 2)):
                # a rounded diamond in screen space reads as a square plaza
                if (i, j) in self.squares and abs(i + 0.5 - cx) + abs(j - 0.5 - cy) <= r * 1.25 and \
                        max(abs(i + 0.5 - cx), abs(j - 0.5 - cy)) <= r:
                    spec.floor[square_tile(i, j)] = material
                    self.plaza.add((i, j))
        return self.plaza

    def door_outside(self, door, footprint):
        """The square just outside a door: of the cells beside the door's wall cell (across its wall
        line), the one whose square is not part of the building."""
        gx, gy = door.gap
        sides = [(gx + 1, gy), (gx - 1, gy), (gx, gy + 1), (gx, gy - 1)]
        outs = [cell_square(*c) for c in sides if c not in self.wall_cells]
        outs = [s for s in outs if s not in footprint]
        if not outs: return None
        ci = sum(i for i, _ in footprint) / max(1, len(footprint)); cj = sum(j for _, j in footprint) / max(1, len(footprint))
        return max(outs, key=lambda s: (s[0] - ci) ** 2 + (s[1] - cj) ** 2)

    def connect_door(self, spec, door, footprint, material="DirtDark2"):
        """A path from the outside of a door to the road network, routed around buildings (never a
        straight line to the nearest wall). Returns the path squares, or None if unreachable."""
        return self.connect(spec, self.door_outside(door, footprint), footprint, material)

    def connect(self, spec, start, footprint=frozenset(), material="DirtDark2"):
        """Shortest path of `material` from square `start` to the nearest road or square tile."""
        if start is None: return None
        targets = self.roads | self.plaza
        if start in targets: return [start]
        blocked = self.taken_strict | footprint | self.water | self.reserved
        prev, q = {start: None}, collections.deque([start])
        end = None
        while q:
            s = q.popleft()
            if s in targets: end = s; break
            for a, b in N4:
                n = (s[0] + a, s[1] + b)
                if n in prev or n not in self.squares or n in blocked: continue
                prev[n] = s; q.append(n)
        if end is None: return None
        path, s = [], prev[end]
        while s is not None:
            path.append(s); s = prev[s]
        for s in path:
            t = square_tile(*s)
            if not spec.floor.get(t, "").startswith(("RoughCobble",)):
                spec.floor[t] = material
            self.roads.add(s)
        # the threshold: building floor tiles touching the doorstep get the path's edge (dirt carried in)
        x0, y0 = square_tile(*start)
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            nb = (x0 + dx, y0 + dy)
            if tile_square(*nb) in footprint and nb in spec.floor:
                spec.local_blend[nb] = -50
        return path

    def clear_walls(self, spec):
        """Streets keep a strip of ground along building walls (call once the buildings stand,
        before routing the doors' paths)."""
        near_building = {(i + a, j + b) for i, j in self.taken_strict for a in (-1, 0, 1) for b in (-1, 0, 1)}
        for s in list(self.roads):
            if s in near_building and s not in self.plaza:
                self.roads.discard(s)
                spec.floor.pop(square_tile(*s), None)

    def trim_dead_ends(self, spec, keep=frozenset()):
        """Roads that end against a building wall are cut back until they end in the open: a road
        leads to a door (through that door's own path, kept in `keep`) or into a clearing, never
        into the side of a building."""
        near_building = {(i + a, j + b) for i, j in self.taken_strict for a in (-1, 0, 1) for b in (-1, 0, 1)}
        changed = True
        while changed:
            changed = False
            for s in list(self.roads):
                if s in keep or s in self.plaza or s not in near_building: continue
                if sum((s[0] + a, s[1] + b) in self.roads or (s[0] + a, s[1] + b) in self.plaza for a, b in N4) <= 1:
                    self.roads.discard(s)
                    spec.floor.pop(square_tile(*s), None)      # becomes ground again when the land is laid
                    changed = True

    # ---- building lots --------------------------------------------------------------------------------
    def lots(self, area, size_uv, setback=(0, 4), reach=1.3):
        """Candidate building origins along the roads in `area`, nearest the area centre first.
        Returns [(origin_uv, entrance_side)]: the entrance faces the road."""
        cx, cy = self.areas[area]["c"]
        R = self.areas[area]["r"] * self.areas[area]["stretch"] * reach
        w, h = size_uv[0] / 2, size_uv[1] / 2
        out = []
        for path in self.road_paths:
            for k in range(1, len(path) - 1):
                si, sj = path[k]
                if math.hypot(si - cx, sj - cy) > R: continue
                tx, ty = path[k + 1][0] - path[k - 1][0], path[k + 1][1] - path[k - 1][1]
                L = math.hypot(tx, ty) or 1
                nx, ny = -ty / L, tx / L
                for side in (1, -1):
                    for sb in range(setback[0], setback[1] + 1):
                        # the road is in direction -side*n from the lot: face that way
                        fx, fy = -side * nx, -side * ny
                        if abs(fx) >= abs(fy): ent = "u_min" if fx < 0 else "u_max"
                        else: ent = "v_min" if fy < 0 else "v_max"
                        depth = w if ent in ("u_min", "u_max") else h
                        lx = si + side * nx * (1.2 + sb + depth / 2)
                        ly = sj + side * ny * (1.2 + sb + depth / 2)
                        oi, oj = int(round(lx - w / 2)), int(round(ly - h / 2))
                        out.append((math.hypot(lx - cx, ly - cy), (2 * oi, 2 * oj), ent))
        out.sort(key=lambda t: t[0])
        seen, res = set(), []
        for _, o, e in out:
            if (o, e) not in seen: seen.add((o, e)); res.append((o, e))
        return res

    def square_lots(self, size_uv, margin=2):
        """Lots around the village square, the building facing it across a clear margin.
        Returns [(origin_uv, entrance_side)], the most central first."""
        if not self.plaza: return []
        pi0, pi1 = min(i for i, _ in self.plaza), max(i for i, _ in self.plaza)
        pj0, pj1 = min(j for _, j in self.plaza), max(j for _, j in self.plaza)
        ci, cj = (pi0 + pi1) / 2, (pj0 + pj1) / 2
        w, h = size_uv[0] // 2, size_uv[1] // 2
        out = []
        for oj in range(pj0 - h + 1, pj1 + 1):              # east and west of the square
            out.append(((pi1 + 1 + margin, oj), "u_min"))
            out.append(((pi0 - margin - w, oj), "u_max"))
        for oi in range(pi0 - w + 1, pi1 + 1):              # north and south
            out.append(((oi, pj1 + margin), "v_min"))
            out.append(((oi, pj0 - 1 - margin - h), "v_max"))
        out.sort(key=lambda o: abs(o[0][0] + w / 2 - ci) + abs(o[0][1] + h / 2 + 0.5 - cj))
        return [((2 * oi, 2 * oj), side) for (oi, oj), side in out]

    def lot_free(self, origin_uv, size_uv, margin=2):
        """The footprint is land clear of roads, the square, water and other lots; the margin around
        it is land clear of water and other lots (a road may pass through the margin)."""
        oi, oj = origin_uv[0] // 2, origin_uv[1] // 2
        w, h = size_uv[0] // 2, size_uv[1] // 2
        for i in range(oi - margin, oi + w + margin):
            for j in range(oj + 1 - margin, oj + h + 1 + margin):
                s = (i, j)
                if s not in self.squares or s in self.water or s in self.reserved or s in self.taken: return False
                inside = oi <= i < oi + w and oj + 1 <= j < oj + h + 1
                if s in self.plaza: return False                  # the square keeps a clear margin
                if inside and s in self.roads: return False
        return True

    def take_cells(self, cells, margin=1):
        """Marks the squares under grid cells (e.g. a building's cells) as taken."""
        for (x, y) in cells:
            i, j = cell_square(x, y)
            for a in range(-margin, margin + 1):
                for b in range(-margin, margin + 1):
                    self.taken.add((i + a, j + b))
