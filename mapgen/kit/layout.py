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
import collections, math, zlib
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


def door_frame(doors, footprint):
    """Where a doorway is and which way it faces: (si, sj) of its middle on the wall line (the midpoint of
    both halves of a double door), the unit step outward (away from the building) and the unit step
    along the wall, in square coordinates. Uses the door's wall line, not the square under the door
    object, which can lie on either side of the wall."""
    doors = list(doors)
    x = sum(d.px[0] for d in doors) / len(doors); y = sum(d.px[1] for d in doors) / len(doors)
    u, v = (x + y) / CELL, (x - y) / CELL
    si, sj = (u - 1) / 2, (v - 1) / 2
    ci = sum(i for i, _ in footprint) / len(footprint) + 0.5
    cj = sum(j for _, j in footprint) / len(footprint) - 0.5
    if doors[0].line == "/":                      # a '/' wall runs along j: outward is across it, along i
        return (si, sj), (1 if si > ci else -1, 0), (0, 1)
    return (si, sj), (0, 1 if sj > cj else -1), (1, 0)


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
        self.forbidden = set()                # squares that must never become land (the rock behind a cliff)
        self.wall_cells = set()               # grid cells of building walls (set by the design as it builds)
        self.crossings = []                   # planned bridges and fords (plan_crossing)
        self.roads, self.plaza, self.water, self.taken = set(), set(), set(), set()
        self.taken_strict = set()             # building footprints only (taken also holds margins)
        self.road_paths = []

    # ---- planning ------------------------------------------------------------------------------------
    def area(self, name, centre_uv, radius_uv, stretch=1.0, angle=0.0, roughness=0.26, clearing=True, region=None):
        """A rounded area (village, glade, clearing). radius in uv units; stretch elongates it along
        `angle` (radians, in uv space); roughness gives the outline its irregular bulges."""
        r = self.rng
        waves = [(k, r.uniform(0, 2 * math.pi), roughness * r.uniform(0.5, 1.0) / (1 + 0.5 * n))
                 for n, k in enumerate((2, 3, 5, 7, 11))]
        # clearing=False: the area's extent comes from what is built in it (a village grows around its
        # square and buildings); radius then only bounds where its lots may go
        # region: the map section the area belongs to (its wall, ground and forest come from the section)
        self.areas[name] = dict(c=(centre_uv[0] / 2, centre_uv[1] / 2), r=radius_uv / 2, stretch=stretch, angle=angle,
                                waves=waves, clearing=clearing, region=region or name)

    def link(self, a, b, width_uv, bend=0.32, road=True, pockets=(1, 2), road_width=None, road_material=None):
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
        self.links.append(dict(a=a, b=b, half=width_uv / 4, path=path, waves=waves, road=road,
                               road_width=road_width, road_material=road_material))
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
                     flow=(0.0, 1.0) if axis == "u" else (1.0, 0.0), corridor=corridor,
                     kit="RopeBridge1" if axis == "u" else "RopeBridge2")
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
        keep = (content | {(i + a, j + b) for i, j in content for a, b in N8}) - self.forbidden
        sq = (sq | keep) - self.forbidden
        for _ in range(2):                                     # majority smoothing (placed content stays)
            nxt = set()
            for (i, j) in {(i + a, j + b) for i, j in sq for a, b in N8}:
                n = sum((i + a, j + b) in sq for a, b in N8)
                if n >= 5 or ((i, j) in sq and n >= 4): nxt.add((i, j))
            sq = (nxt | keep) - self.forbidden
        for _ in range(3):                                     # no spurs or 1-2 square necks
            sq = {s for s in sq if s in keep or sum((s[0] + a, s[1] + b) in sq for a, b in N4) >= 3 or
                  (sum((s[0] + a, s[1] + b) in sq for a, b in N4) == 2 and not self._neck(s, sq))}
        sq = self._largest(sq)
        sq |= self._holes(sq) - self.forbidden
        sq = self._fix_pinches(sq, avoid=self.forbidden)
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
    def _fix_pinches(sq, avoid=frozenset()):
        """A wall point whose land squares touch only diagonally would draw a cross through the
        passage; fill one of the void squares (one not in `avoid` when there is a choice)."""
        changed = True
        while changed:
            changed = False
            pts = {(i + a, j + b) for i, j in sq for a in (0, 1) for b in (-1, 0)}
            for p, q in pts:
                quad = [(p - 1, q), (p, q), (p - 1, q + 1), (p, q + 1)]
                ins = [s in sq for s in quad]
                if ins == [True, False, False, True] or ins == [False, True, True, False]:
                    gaps = [s for s, inside in zip(quad, ins) if not inside]
                    sq.add(next((s for s in gaps if s not in avoid), gaps[0])); changed = True
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

    def thickets(self, n, size=(1.2, 2.3), clear=3, regions=None, avoid=frozenset()):
        """Islands of forest in the open, before apply(): small holes in the land that apply() rings with
        the section's forest wall and the planter then fringes with trees. Westwood's forests break their
        glades up this way (their maps carry 21 to 52 wall pieces per 100 floor tiles; a ring of forest
        round open grass carries about 15). Each thicket keeps `clear` squares of open land around it,
        clear of roads, buildings, water, other thickets and `avoid`, so no passage narrows and nothing
        planned is blocked. Returns the thickets (sets of squares)."""
        r = self.rng
        busy = set(self.roads) | self.plaza | self.water | self.taken | self.reserved | set(avoid)
        cands = [s for s in self.squares if regions is None or self.region_of(s) in regions]
        cands.sort()
        r.shuffle(cands)
        made = []
        for c in cands:
            if len(made) >= n: break
            rad, ph = r.uniform(*size), r.uniform(0, 6.3)
            blob = {(c[0] + a, c[1] + b) for a in range(-3, 4) for b in range(-3, 4)
                    if math.hypot(a, b) <= rad * (1 + 0.25 * math.sin(3 * math.atan2(b, a) + ph))}
            ring = {(i + a, j + b) for i, j in blob for a in range(-clear, clear + 1) for b in range(-clear, clear + 1)}
            if not ring <= self.squares or ring & busy: continue
            self.squares -= blob
            busy |= ring
            made.append(blob)
        self.squares = self._fix_pinches(self.squares)
        return made

    def open_links(self, half=1.7):
        """Every passage open end to end, `half` squares either side of its centre line (call after carve and
        thickets, before apply): an area the carve or a clump pinched off is no longer cut off from the rest
        (Thornwick v0.2: the Red Hand's camp unreachable behind a pinch of forest). Returns the squares added."""
        add = set()
        k = int(math.ceil(half))
        for ln in self.links:
            for si, sj in ln["path"]:
                ci, cj = int(math.floor(si)), int(math.floor(sj)) + 1
                for a in range(-k, k + 1):
                    for b in range(-k, k + 1):
                        s = (ci + a, cj + b)
                        if math.hypot(a, b) <= half and s not in self.forbidden and 3 <= s[0] + s[1] <= 250                                 and 3 <= s[0] - s[1] <= 250:
                            add.add(s)
        add -= self.squares
        self.squares |= add
        return add

    def assign_regions(self, jitter=2.5):
        """Square -> region: the nearest area's region, the border between regions wavering with smooth
        noise so sections blend into each other instead of meeting on a straight line."""
        r = self.rng
        ph = [r.uniform(0, 6.3) for _ in range(4)]
        cents = [(a["c"], a["r"] * max(1.0, a["stretch"]), a["region"]) for a in self.areas.values()]
        self.region_map = {}
        for (i, j) in self.squares:
            n = jitter * (math.sin(i * 0.21 + ph[0]) + math.sin(j * 0.17 + ph[1]) + math.sin((i + j) * 0.13 + ph[2]))
            best = min(cents, key=lambda c: math.hypot(i + 0.5 - c[0][0], j - 0.5 - c[0][1]) - 0.35 * c[1]
                       + n * (zlib.crc32(str(c[2]).encode()) % 7 - 3) / 3.0)    # crc32: hash() of a str varies per run
            self.region_map[(i, j)] = best[2]
        return self.region_map

    def region_of(self, s):
        return getattr(self, "region_map", {}).get(s)

    def apply(self, spec, wall, floor):
        """Floor tiles on every land square and the forest wall around them. wall / floor: a material,
        or a function of the region (each section has its own wall and ground)."""
        wall_of = wall if callable(wall) else (lambda region: wall)
        floor_of = floor if callable(floor) else (lambda region: floor)
        for s in self.squares:
            spec.floor.setdefault(square_tile(*s), floor_of(self.region_of(s)))   # roads, squares, buildings stay
        for p in self.boundary_points():
            q = p[1]
            quad = [(p[0] - 1, q), (p[0], q), (p[0] - 1, q + 1), (p[0], q + 1)]
            region = next((self.region_of(s) for s in quad if s in self.squares), None)
            x, y = point_cell(*p)
            spec.wall(x, y, wall_of(region))

    def ground_variety(self, spec, base="GrassNorm", sparse="GrassSparse2", dense="GrassDense", scale=1.0, clear=3, region=None):
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
            if region is not None and self.region_of(s) != region: continue
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
            mat = ln.get("road_material") or material
            width = ln.get("road_width") or width_squares
            for k, (si, sj) in enumerate(path):
                half = width / 2 * (1 + 0.15 * math.sin(k * nz[1] + nz[0]))
                for i in range(int(si - half - 1), int(si + half + 2)):
                    for j in range(int(sj - half - 1), int(sj + half + 2)):
                        if (i, j) not in self.squares or (i, j) in skip or (i, j) in self.plaza: continue
                        if math.hypot(i + 0.5 - si, j - 0.5 - sj) <= half:
                            t = square_tile(i, j)
                            if "Water" in spec.floor.get(t, "") or "WoodSlat" in spec.floor.get(t, ""): continue
                            spec.floor[t] = mat
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
        straight line to the nearest wall). Returns the path squares, or None if unreachable. When
        Westwood never lets the path's floor touch the room's floor (packed dirt against marble), the
        path uses the floor Westwood puts between them."""
        inside = spec.floor.get(door.gap) or next((spec.floor.get((door.gap[0] + a, door.gap[1] + b))
                                                   for a, b in ((1, 1), (1, -1), (-1, 1), (-1, -1))
                                                   if spec.floor.get((door.gap[0] + a, door.gap[1] + b))), None)
        if inside:
            import json, os
            nt = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                             "rules", "out", "floors.json")))["never_touch"]
            for r in nt:
                if {r["a"], r["b"]} == {material, inside} and r.get("buffer_materials"):
                    material = max(r["buffer_materials"], key=r["buffer_materials"].get)
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
        # the threshold is drawn as Westwood draws it, the room's floor out onto the doorstep and the path's edge on that,
        # never on the floor inside (nox.Spec._door_thresholds; Starwell playtest, 2026-10-05: this had laid the dirt's
        # edge on the boards just inside every door)
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
        # a road whose end runs on past a door's path toward the building's wall (a satellite's road ending at its
        # only building): walk back from the end until the road is in the open or meets the door's path, and cut
        # the stretch beyond; a road two or three squares wide ends bluntly, so the one-neighbour rule below misses it
        foot = list(self.taken_strict)
        kept = [(i + 0.5, j - 0.5) for i, j in keep]
        for path in self.road_paths:
            for seq in (path[::-1], path):
                near = 0                                        # path points from the end that are by a building
                for pi_, pj_ in seq:
                    if not foot or min(abs(pi_ - (i + 0.5)) + abs(pj_ - (j - 0.5)) for i, j in foot) >= 4.5: break
                    near += 1
                if not near or near >= len(seq) - 1: continue
                # the junction: where a door's path meets this stretch; beyond it the road only leads to the wall
                to_keep = [min((math.hypot(seq[k][0] - a, seq[k][1] - b) for a, b in kept), default=99.0) for k in range(near)]
                cut = min(range(near), key=lambda k: to_keep[k]) if min(to_keep) <= 3.0 else near
                if not cut: continue
                spur, rest = seq[:cut], seq[cut:]
                for s in list(self.roads):
                    if s in keep or s in self.plaza: continue
                    c = (s[0] + 0.5, s[1] - 0.5)
                    d_spur = min(math.hypot(c[0] - a, c[1] - b) for a, b in spur)
                    if d_spur > 2.5 or d_spur >= min(math.hypot(c[0] - a, c[1] - b) for a, b in rest): continue
                    if any(other is not path and min(math.hypot(c[0] - a, c[1] - b) for a, b in other) < 2.5
                           for other in self.road_paths): continue
                    self.roads.discard(s)
                    spec.floor.pop(square_tile(*s), None)
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
                if s not in self.squares or s in self.water or s in self.reserved or s in self.taken or                         s in self.forbidden: return False
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
