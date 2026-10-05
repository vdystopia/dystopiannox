"""Where people walk: the ground a body of a townsperson's size can stand on and walk across, and routes over it.

Shared by the kit (routing the townsfolk's tours and the watch's beats, kit/story.py) and the checker
(validate/checks.py check_routes), so both judge a waypoint and a leg the same way:

- walls are drawn as Westwood's thin pieces, a line from the centre of their cell toward each neighbour they join
  (the arms of FACING_BY_ARMS), so a leg passing a door's jamb is measured against the jamb's real end;
- obstacles (trees, rocks, benches, wells, furniture) by their extent in the thing database (corpus things.json),
  as the checker's reachability measures them;
- a door opening is passed square-on: a leg crossing a door's wall cell runs along the door's normal through the
  middle of the opening (one cell for a single door, two for a double), never cutting the corner into the jamb.

    g = Ground.from_spec(spec)                      # or Ground.from_mapdata(m) in the checker
    g.point_ok(x, y); g.leg_problem((x0, y0), (x1, y1))
    r = Router(g, roads=cells); pts = r.route(a, b)  # world px points from a to b along the roads, a waypoint per bend
"""
import collections, heapq, json, math, os

CELL = 23
DIAG = ((-1, -1), (1, -1), (-1, 1), (1, 1))
BODY = 12                    # a townsperson's radius (NPC, Maiden: CIRCLE 12 in the thing database)
LINE_STEP = {"\\": (1, 1), "/": (1, -1)}
HERE = os.path.dirname(os.path.abspath(__file__))
THINGS = os.path.join(HERE, "..", "..", "corpus", "out", "json", "things.json")

_shapes = None


def thing_shapes():
    """type -> (ext, ex, ey, cls, flags) from the thing database (the checker's source for extents)."""
    global _shapes
    if _shapes is None:
        try:
            g = json.load(open(THINGS, encoding="utf-8"))
            _shapes = {t["name"]: (t.get("ext"), t.get("ex") or 0, t.get("ey") or 0, t.get("class") or "", t.get("flags") or "")
                       for t in g["things"]}
        except OSError:
            _shapes = {}
    return _shapes


def blocks(ext, ex, ey, cls, flags):
    """An obstacle a walker goes round (as validate/mapdata.MapData.blocking): not a door, creature or trigger."""
    if not ext or ext == "NULL" or "DOOR" in cls or "MONSTER" in cls or "TRIGGER" in cls or "NO_COLLIDE" in flags:
        return False
    return ("OBSTACLE" in cls or "IMMOBILE" in cls) and max(ex, ey) > 0


def _seg_dist(px_, py_, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px_ - ax) * dx + (py_ - ay) * dy) / L2))
    return math.hypot(px_ - ax - t * dx, py_ - ay - t * dy)


class Ground:
    """walls: {cell: arms (diagonal steps it joins)}; cover: cells with a floor tile; wet: cells on water;
    doors: [(opening cells, line)]; blockers: [(x, y, 'CIRCLE', r, 0) or (x, y, 'BOX', half w, half h)]."""

    def __init__(self, walls, cover, wet, doors, blockers):
        self.walls, self.cover, self.wet = walls, cover, wet
        self.gap_door = {}                       # door cell -> (centre px, unit normal, half width px)
        for cells, line in doors:
            cx = sum(c[0] for c in cells) / len(cells) * CELL + CELL / 2
            cy = sum(c[1] for c in cells) / len(cells) * CELL + CELL / 2
            nx, ny = (1, -1) if line == "\\" else (1, 1)
            n = (nx / math.sqrt(2), ny / math.sqrt(2))
            for c in cells: self.gap_door[c] = ((cx, cy), n, len(cells) * CELL * math.sqrt(2) / 2)
        self.blockers = blockers
        self._obj = collections.defaultdict(list)
        for b in blockers:
            r = b[3] if b[2] == "CIRCLE" else math.hypot(b[3], b[4])
            for i in range(int((b[0] - r - 40) // 92), int((b[0] + r + 40) // 92) + 1):
                for j in range(int((b[1] - r - 40) // 92), int((b[1] + r + 40) // 92) + 1):
                    self._obj[(i, j)].append(b)
        self._wd = {}

    # ---- building one ------------------------------------------------------------------------------------------------
    @classmethod
    def from_spec(cls, spec):
        """From a map being built (nox.Spec): its walls (shaped as _finalize shapes them), floors, doors, objects."""
        from nox import FACING_BY_ARMS
        arms_of = {f: arms for arms, f in FACING_BY_ARMS.items() if len(arms) >= 2}
        walls = {}
        for c, w in spec.wallmap.items():
            f = w.get("facing")
            if f is None:             # shaped from its neighbours, as Spec._finalize shapes it
                f = FACING_BY_ARMS[frozenset(a for a in DIAG if (c[0] + a[0], c[1] + a[1]) in spec.wallmap
                                             or (c[0] + a[0], c[1] + a[1]) in spec.door_gaps)]
            walls[c] = tuple(arms_of.get(f, ()))         # as the checker reads the piece back (MapData.arms)
        cover, wet = set(), set()
        for (x, y), mat in spec.floor.items():
            if mat == "Black": continue
            cs = ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1))
            cover.update(cs)
            if "Water" in mat: wet.update(cs)
        doors = _door_openings(spec.door_gaps, lambda c: _line_of(c, spec.door_gaps, spec.wallmap))
        shapes = thing_shapes()
        blockers = []
        for o in spec.d["objects"]:
            t = o.get("type")
            if not t or t not in shapes: continue
            ext, ex, ey, cl, fl = shapes[t]
            if not blocks(ext, ex, ey, cl, fl): continue
            blockers.append((o["x"], o["y"], "CIRCLE", ex, 0) if ext != "BOX" else (o["x"], o["y"], "BOX", ex / 2, ey / 2))
        return cls(walls, cover, wet, doors, blockers)

    @classmethod
    def from_mapdata(cls, m):
        """From a map read back by the checker (validate/mapdata.MapData)."""
        walls = {c: tuple(m.arms(c)) for c in m.walls}
        wet = set()
        for (x, y), t in m.tiles.items():
            if "Water" in t["material"]: wet.update(((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)))
        lines = {d["gap"]: d["line"] for d in m.doors}
        doors = _door_openings(set(lines), lambda c: lines[c])
        blockers = []
        for o in m.objects:
            if not blocks(o["ext"], o["ex"], o["ey"], o["cls"], o["flags"]): continue
            blockers.append((o["x"], o["y"], "CIRCLE", o["ex"], 0) if o["ext"] != "BOX" else
                            (o["x"], o["y"], "BOX", o["ex"] / 2, o["ey"] / 2))
        return cls(walls, m.cover, wet, doors, blockers)

    # ---- measuring ---------------------------------------------------------------------------------------------------
    def wall_dist(self, x, y, reach=2):
        """Distance (px) from (x, y) to the nearest wall piece within `reach` cells (reach * 23 + if none)."""
        cx, cy = int(x // CELL), int(y // CELL)
        best = (reach + 0.5) * CELL
        for i in range(cx - reach, cx + reach + 1):
            for j in range(cy - reach, cy + reach + 1):
                arms = self.walls.get((i, j))
                if arms is None: continue
                mx, my = i * CELL + CELL / 2, j * CELL + CELL / 2
                if not arms: best = min(best, math.hypot(x - mx, y - my) - 4); continue
                for a, b in arms:
                    best = min(best, _seg_dist(x, y, mx, my, mx + a * CELL / 2, my + b * CELL / 2))
        return best

    def obstacle_at(self, x, y, margin):
        """The obstacle (x, y, ...) within `margin` px of the point, or None."""
        for b in self._obj.get((int(x // 92), int(y // 92)), ()):
            if b[2] == "CIRCLE":
                if math.hypot(x - b[0], y - b[1]) < b[3] + margin: return b
            else:
                dx = max(0.0, abs(x - b[0]) - b[3]); dy = max(0.0, abs(y - b[1]) - b[4])
                if math.hypot(dx, dy) < margin: return b
        return None

    def floor_ok(self, x, y):
        c = (int(x // CELL), int(y // CELL))
        return c in self.cover and c not in self.wet and c not in self.walls

    def point_problem(self, x, y, wall_clear=BODY, obj_clear=BODY - 2):
        """Why a body cannot stand at (x, y), or None."""
        c = (int(x // CELL), int(y // CELL))
        if c not in self.cover: return "no floor"
        if c in self.wet: return "water"
        if c in self.walls: return "in a wall"
        if self.wall_dist(x, y) < wall_clear: return "against a wall"
        b = self.obstacle_at(x, y, obj_clear)
        if b: return f"in an obstacle at ({b[0]:.0f}, {b[1]:.0f})"
        return None

    def point_ok(self, x, y, wall_clear=BODY, obj_clear=BODY - 2):
        return self.point_problem(x, y, wall_clear, obj_clear) is None

    def leg_problem(self, a, b, wall_clear=BODY - 2, obj_clear=BODY - 4, step=4.0, square_on=25.0):
        """Why a walker going straight from a to b (world px) would hit something, or None: the void, a wall piece
        (fences and forest walls are walls), an obstacle, or a door opening entered off its normal (more than
        `square_on` degrees) or off its middle."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        n = max(1, int(L / step))
        seen_doors = set()
        for k in range(n + 1):
            x, y = a[0] + dx * k / n, a[1] + dy * k / n
            c = (int(x // CELL), int(y // CELL))
            if c not in self.cover: return f"crosses the void at ({x:.0f}, {y:.0f})"
            if c in self.walls: return f"crosses a wall at ({x:.0f}, {y:.0f})"
            if self.wall_dist(x, y) < wall_clear: return f"scrapes a wall at ({x:.0f}, {y:.0f})"
            o = self.obstacle_at(x, y, obj_clear)
            if o: return f"runs into an obstacle at ({o[0]:.0f}, {o[1]:.0f})"
            door = self.gap_door.get(c)
            if door and door[0] not in seen_doors and L > 0:
                seen_doors.add(door[0])
                (ox, oy), nrm, half = door
                cos = abs(dx * nrm[0] + dy * nrm[1]) / L
                if cos < math.cos(math.radians(square_on)):
                    return f"cuts through a doorway at an angle at ({ox:.0f}, {oy:.0f})"
                if _seg_dist(ox, oy, a[0], a[1], b[0], b[1]) > max(6.0, half - BODY - 4):
                    return f"passes a doorway off its middle at ({ox:.0f}, {oy:.0f})"
        return None

    # ---- doors -------------------------------------------------------------------------------------------------------
    def passage(self, gap, outward_to, outs=(40, 48, 34, 56, 64), ins=(36, 44, 30, 52), clear=BODY + 2):
        """The points that take a walker square-on through the door whose opening holds wall cell `gap`: (out, mid,
        inn): a point straight out in front of the opening (on the side of `outward_to`, world px), the opening's
        centre, and a point straight in behind it, each the first of the distances (px) that a body stands clear
        on, and the legs between them clear. out or inn is None where no distance works (a doorstep against a
        fence, a bed behind the door); mid is None when the threshold has no floor (the legs still pass
        square-on). None if the door is unknown."""
        d = self.gap_door.get(gap)
        if not d: return None
        (cx, cy), (nx, ny), _ = d
        if (outward_to[0] - cx) * nx + (outward_to[1] - cy) * ny < 0: nx, ny = -nx, -ny
        mid = (cx, cy) if self.point_ok(cx, cy) else None
        def first(ds, sign):
            for dd in ds:
                p = (cx + sign * nx * dd, cy + sign * ny * dd)
                if self.point_ok(p[0], p[1], wall_clear=clear, obj_clear=BODY) and \
                        self.leg_problem(p, (cx - sign * nx * 8, cy - sign * ny * 8)) is None:
                    return p
            return None
        return first(outs, 1), mid, first(ins, -1)


def _line_of(c, gaps, wallmap):
    """A door cell's wall line from the cells it joins (a door gap runs along its wall)."""
    for line, (a, b) in LINE_STEP.items():
        for s in (1, -1):
            n = (c[0] + a * s, c[1] + b * s)
            if n in wallmap or n in gaps: return line
    return "\\"


def _door_openings(gaps, line_of):
    """[(cells, line)]: each door's opening, the two cells of a double door together."""
    out, done = [], set()
    for c in sorted(gaps):
        if c in done: continue
        line = line_of(c)
        st = LINE_STEP[line]
        cells = [c]
        for s in (1, -1):
            n = (c[0] + st[0] * s, c[1] + st[1] * s)
            if n in gaps and n not in done and len(cells) < 2: cells.append(n)
        done.update(cells)
        out.append((cells, line))
    return out


class Router:
    """Routes over a Ground for a walker: cells whose centre a body stands clear on (walls `clear` px off), roads
    cheaper than open ground, so the way follows the roads and paths wherever there are any; then the cell path is
    pulled straight into legs that stay within `bend` px of it, a waypoint at each bend, each leg under `max_leg`."""

    def __init__(self, ground, roads=frozenset(), clear=BODY + 3, off_road=2.6, bend=16.0, max_leg=230.0):
        self.g, self.roads, self.clear, self.off_road, self.bend, self.max_leg = ground, roads, clear, off_road, bend, max_leg
        self._ok = {}

    def ok(self, c):
        v = self._ok.get(c)
        if v is None:
            x, y = c[0] * CELL + CELL / 2, c[1] * CELL + CELL / 2
            # door openings are passed only by the explicit three-point passages (Ground.passage), never routed
            v = self._ok[c] = c not in self.g.gap_door and self.g.point_ok(x, y, wall_clear=self.clear, obj_clear=BODY)
        return v

    def _start(self, p):
        c0 = (int(p[0] // CELL), int(p[1] // CELL))
        if self.ok(c0): return c0
        near = [(c0[0] + a, c0[1] + b) for a in range(-2, 3) for b in range(-2, 3)]
        near = [c for c in near if self.ok(c) and self.g.leg_problem(p, (c[0] * CELL + 11.5, c[1] * CELL + 11.5)) is None]
        return min(near, key=lambda c: (c[0] - c0[0]) ** 2 + (c[1] - c0[1]) ** 2, default=None)

    def costs_from(self, p, limit):
        """Cell -> cost of the cheapest way from point p (road cells cost 1, open ground `off_road`), up to `limit`."""
        s = self._start(p)
        if s is None: return {}
        dist, pq = {s: 0.0}, [(0.0, s)]
        while pq:
            d, c = heapq.heappop(pq)
            if d > dist.get(c, 1e18) or d > limit: continue
            for a_, b_ in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nb = (c[0] + a_, c[1] + b_)
                if not self.ok(nb): continue
                if a_ and b_ and not (self.ok((c[0] + a_, c[1])) and self.ok((c[0], c[1] + b_))): continue
                nd = d + (1.414 if a_ and b_ else 1.0) * (1.0 if nb in self.roads else self.off_road)
                if nd < dist.get(nb, 1e18) and nd <= limit:
                    dist[nb] = nd
                    heapq.heappush(pq, (nd, nb))
        return dist

    def cells(self, a, b, limit=60000):
        """The cheapest cell path from point a to point b (8-connected, no corner cutting), or None."""
        s, t = self._start(a), self._start(b)
        if s is None or t is None: return None
        h = lambda c: math.hypot(c[0] - t[0], c[1] - t[1])
        dist, prev = {s: 0.0}, {s: None}
        pq = [(h(s), 0.0, s)]
        n = 0
        while pq:
            f, d, c = heapq.heappop(pq)
            if c == t: break
            if d > dist.get(c, 1e18): continue
            n += 1
            if n > limit: return None
            for a_, b_ in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nb = (c[0] + a_, c[1] + b_)
                if not self.ok(nb): continue
                if a_ and b_ and not (self.ok((c[0] + a_, c[1])) and self.ok((c[0], c[1] + b_))): continue
                w = (1.414 if a_ and b_ else 1.0) * (1.0 if nb in self.roads else self.off_road)
                nd = d + w
                if nd < dist.get(nb, 1e18):
                    dist[nb], prev[nb] = nd, c
                    heapq.heappush(pq, (nd + h(nb), nd, nb))
        if t not in prev: return None
        path, c = [], t
        while c is not None: path.append(c); c = prev[c]
        return path[::-1]

    def route(self, a, b):
        """World px points from a to b (a excluded, b included): straight legs along the cell path, or None."""
        cells = self.cells(a, b)
        if cells is None: return None
        return self._pull([a] + [(c[0] * CELL + CELL / 2, c[1] * CELL + CELL / 2) for c in cells[1:-1]] + [b])

    def _pull(self, pts):
        """The points pts[1:] pulled straight: from each point the farthest later one whose leg stays within `bend`
        px of the path between, is clear and under `max_leg`. None if even a single step is not clear."""
        out, i = [], 0
        while i < len(pts) - 1:
            j = i + 1
            for k in range(len(pts) - 1, i, -1):
                if math.hypot(pts[k][0] - pts[i][0], pts[k][1] - pts[i][1]) > self.max_leg: continue
                if all(_seg_dist(p[0], p[1], *pts[i], *pts[k]) <= self.bend for p in pts[i + 1:k]) and                         self.g.leg_problem(pts[i], pts[k]) is None:
                    j = k
                    break
            if self.g.leg_problem(pts[i], pts[j]) is not None: return None
            out.append(pts[j])
            i = j
        return out

    # ---- far: across the map, through doorways and gates -------------------------------------------------------------
    def portals(self, shut=()):
        """{cell: [(other cell, cost, (out, mid, in))]}: every doorway a walker can pass, both ways, as the three
        square-on points (Ground.passage) between a clear cell before it and one behind it. Doors within 40 px of a
        point of `shut` (locked doors and gates) are left out."""
        key = tuple(sorted(shut))
        if getattr(self, "_portals", None) and self._portals[0] == key: return self._portals[1]
        out, seen = {}, set()
        for gap, (c, n, half) in sorted(self.g.gap_door.items()):
            if c in seen: continue
            seen.add(c)
            if any(math.hypot(c[0] - q[0], c[1] - q[1]) < 40 for q in shut): continue
            ps = self.g.passage(gap, (c[0] + n[0] * 60, c[1] + n[1] * 60))
            if not ps or not ps[0] or not ps[2]: continue
            a, mid, b = ps
            if self.g.leg_problem(a, b) is not None: continue
            ca, cb = self._start(a), self._start(b)
            if ca is None or cb is None or ca == cb: continue
            cost = math.hypot(b[0] - a[0], b[1] - a[1]) / CELL + 2.0
            out.setdefault(ca, []).append((cb, cost, (a, mid, b)))
            out.setdefault(cb, []).append((ca, cost, (b, mid, a)))
        self._portals = (key, out)
        return out

    def route_far(self, a, b, shut=(), limit=600000):
        """World px points from a to b (a excluded, b included) anywhere on the map: along the roads and paths, and
        through any doorway or gate on the way square-on (out in front, its middle, in behind: Ground.passage),
        never through one within 40 px of a point of `shut`. A long walk (a rescued man going home) is walked leg by
        leg on these points, as the tours are: the game's own path search gives up on far goals and walks
        straight at them, into the trees. None when there is no way."""
        s, t = self._start(a), self._start(b)
        if s is None or t is None: return None
        doors = self.portals(shut)
        h = lambda c: math.hypot(c[0] - t[0], c[1] - t[1])
        dist, prev = {s: 0.0}, {s: None}
        pq = [(h(s), 0.0, s)]
        n = 0
        while pq:
            f, d, c = heapq.heappop(pq)
            if c == t: break
            if d > dist.get(c, 1e18): continue
            n += 1
            if n > limit: return None
            steps = []
            for a_, b_ in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nb = (c[0] + a_, c[1] + b_)
                if not self.ok(nb): continue
                if a_ and b_ and not (self.ok((c[0] + a_, c[1])) and self.ok((c[0], c[1] + b_))): continue
                steps.append((nb, (1.414 if a_ and b_ else 1.0) * (1.0 if nb in self.roads else self.off_road), None))
            steps += doors.get(c, [])
            for nb, w, via in steps:
                nd = d + w
                if nd < dist.get(nb, 1e18):
                    dist[nb], prev[nb] = nd, (c, via)
                    heapq.heappush(pq, (nd + h(nb), nd, nb))
        if t not in prev: return None
        # the cell path back from t, cut at each doorway into pieces walked on the ground
        pieces, cur, c = [], [t], t
        while prev[c] is not None:
            p_, via = prev[c]
            if via is not None:
                pieces.append((cur[::-1], via)); cur = [p_]       # cells after the doorway, the doorway before them
            else:
                cur.append(p_)
            c = p_
        pieces.append((cur[::-1], None))
        pieces.reverse()                  # [(cells, the doorway passed before them or None)], the first from a
        centre = lambda c: (c[0] * CELL + CELL / 2, c[1] * CELL + CELL / 2)
        out, start = [], a
        for k, (cells, via) in enumerate(pieces):
            if via:
                if via[1]: out.append(via[1])
                out.append(via[2])
                start = via[2]
            end = pieces[k + 1][1][0] if k + 1 < len(pieces) else b
            pts = [start] + [centre(c) for c in cells] + [end]
            pts = [p for j, p in enumerate(pts) if j == 0 or math.hypot(p[0] - pts[j - 1][0], p[1] - pts[j - 1][1]) > 1]
            legs = self._pull(pts) if len(pts) > 1 else []
            if legs is None: return None
            out += legs
        return out


# ---- which way a body faces where it stands (playtest 2026-10-05, Starwell: "a lot of NPCs seem to face random
# directions when they get to stopping points ... if an NPC is standing next to a building, have them face away from
# the building") -------------------------------------------------------------------------------------------------------
FACE_REACH = 40.0     # px straight ahead a standing body keeps open: no wall, building, tree or obstacle (a stride and a half)
FACE_SIDE = 22.0      # degrees either side of straight ahead also kept open, to FACE_REACH * 0.7
NEAR_WALL = 34.0      # px: a body this near a wall or building stands beside it, and faces away from it
AWAY_SLACK = 80.0     # degrees off straight away from that wall a body beside it may face
FACE_FAR = 240.0      # px out along a facing to the point the game is told to face (one the walker cannot reach)


def _unit(a):
    return math.cos(a), math.sin(a)


def facing_problem(g, p, look, feature=None, reach=FACE_REACH, step=4.0):
    """Why a body standing at p (world px) and facing toward `look` faces into something within `reach` px straight
    ahead, or None: the void, a wall (a building, a fence, a forest wall), or an obstacle (a tree, a rock, a stall)
    other than the feature it stands there for (an obstacle centred within 10 px of `feature`: the well it looks at)."""
    dx, dy = look[0] - p[0], look[1] - p[1]
    L = math.hypot(dx, dy)
    if L < 1: return "faces nowhere"
    ux, uy = dx / L, dy / L
    for k in range(1, int(reach / step) + 1):
        d = k * step
        x, y = p[0] + ux * d, p[1] + uy * d
        c = (int(x // CELL), int(y // CELL))
        if c not in g.cover: return f"faces the void {d:.0f} px ahead"
        if c in g.walls or g.wall_dist(x, y) < 3: return f"faces a wall {d:.0f} px ahead"
        if feature and math.hypot(x - feature[0], y - feature[1]) < 6: return None    # reached what it looks at
        o = g.obstacle_at(x, y, 2)
        if o and not (feature and math.hypot(o[0] - feature[0], o[1] - feature[1]) < 10):
            return f"faces an obstacle {d:.0f} px ahead at ({o[0]:.0f}, {o[1]:.0f})"
    return None


def _open_ahead(g, p, a, feature=None):
    """True when the facing at angle a (radians) from p is open: straight ahead to FACE_REACH and a little either side."""
    q = lambda b, r: (p[0] + r * math.cos(b), p[1] + r * math.sin(b))
    if facing_problem(g, p, q(a, FACE_FAR), feature) is not None: return False
    side = math.radians(FACE_SIDE)
    return all(facing_problem(g, p, q(a + s, FACE_FAR), feature, reach=FACE_REACH * 0.7) is None for s in (-side, side))


def wall_away(g, p, near=NEAR_WALL):
    """The direction (radians) straight away from the walls within `near` px of p, or None when none is that near:
    the sum, over 32 directions, of each one that meets a wall (or the void) within `near`, weighted by how near."""
    sx = sy = 0.0
    for k in range(32):
        a = k * math.pi / 16
        ux, uy = _unit(a)
        for d in range(4, int(near) + 1, 3):
            x, y = p[0] + ux * d, p[1] + uy * d
            c = (int(x // CELL), int(y // CELL))
            if c not in g.cover or c in g.walls or g.wall_dist(x, y) < 3:
                sx -= ux * (near - d + 3); sy -= uy * (near - d + 3)
                break
    if math.hypot(sx, sy) < 1e-6: return None
    return math.atan2(sy, sx)


def _run(g, p, a, reach):
    """How far (px, to `reach`) the ground runs open from p at angle a: no void, wall or obstacle."""
    ux, uy = _unit(a)
    for d in range(4, int(reach) + 1, 4):
        x, y = p[0] + ux * d, p[1] + uy * d
        c = (int(x // CELL), int(y // CELL))
        if c not in g.cover or c in g.walls or g.wall_dist(x, y) < 3 or g.obstacle_at(x, y, 2): return d
    return reach


def _open_way(g, p, reach=120.0):
    """The direction (radians) of the most open ground about p: each of 32 directions weighted by how far it runs
    open (to `reach`)."""
    sx = sy = 0.0
    for k in range(32):
        a = k * math.pi / 16
        r = _run(g, p, a, reach)
        sx += math.cos(a) * r; sy += math.sin(a) * r
    return math.atan2(sy, sx) if math.hypot(sx, sy) > 1e-6 else 0.0


def stop_facing(g, p, prefer=None, feature=None):
    """Where a body standing at stop p faces (a point the game turns it toward): toward `prefer` (a point: the
    feature it is there for, the square's middle, a point straight out from a door), turned as little as it takes
    to face open ground (facing_problem: nothing within FACE_REACH ahead, nor a little either side), and, beside a
    wall or building (within NEAR_WALL), within AWAY_SLACK degrees of straight away from it. With no preference, the
    most open way. Returns the feature itself when the body faces it unturned, else a point FACE_FAR px out."""
    if prefer is not None and math.hypot(prefer[0] - p[0], prefer[1] - p[1]) >= 1:
        base = math.atan2(prefer[1] - p[1], prefer[0] - p[0])
    else:
        base, prefer, feature = _open_way(g, p), None, None
    away = wall_away(g, p)
    out = lambda a: (p[0] + FACE_FAR * math.cos(a), p[1] + FACE_FAR * math.sin(a))
    away_ok = lambda a: away is None or math.degrees(abs((a - away + math.pi) % (2 * math.pi) - math.pi)) <= AWAY_SLACK
    ahead_ok = lambda a: facing_problem(g, p, out(a), feature) is None
    # turning 11.25 degrees at a time, the nearer way first; each test tried over every turn before the next, looser
    turns = [base] + [base + s * k * math.pi / 16 for k in range(1, 16) for s in (1, -1)] + [base + math.pi]
    for fits in (lambda a: away_ok(a) and _open_ahead(g, p, a, feature),
                 lambda a: away_ok(a) and ahead_ok(a),
                 ahead_ok):
        for k, a in enumerate(turns):
            if fits(a):
                return tuple(prefer) if k == 0 and feature is not None and prefer is not None else out(a)
    return out(max((k * math.pi / 16 for k in range(32)), key=lambda a: _run(g, p, a, FACE_REACH + 8)))
