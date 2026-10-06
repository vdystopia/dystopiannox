"""Exterior dressing: the outdoor ground between the walls takes scenes with a purpose (kit/scenes.py), chosen by what
the place is for and what is near it.

History: the first dresser (2026-10-05 playtest: "exterior areas are way too empty", a castle alley held one bush and
two pebbles) filled every stretch of open ground with groups by wall type and biome until none lay more than 4 cells
from a prop. The same day's Greywatch playtest found the result "very random and purposeless. many instances of
randomly placed clusters of crates and barrels", and a lone stone block by a wall's corner. Now:

1. The purpose pass: each building calls for the scenes of its trade (kit/scenes.ROLE_SCENES): a sparring ring by the
   barracks, the smith's yard beside the smithy, a midden behind the inn, a cart loading at the store or the mill, a
   woodpile at a cottage's side; each gate gets a guard post against its wall.
2. The fill pass: the emptiest open ground first, a scene that belongs there (a wagon on a road's verge, a waystone
   by a road out of town, washing by the water, deadfall at the forest's edge), until no free ground lies more than
   `reach` cells from a prop, or nothing fits: every theme has a cap to a map, a spacing from others of its family,
   and scenes keep apart from each other, so some open ground stays open, as in Westwood's towns.
3. Every scene is laid whole or not at all: its must-have pieces fit, it holds at least `min_types` kinds of thing
   and `min_pieces` pieces (never a lone block or a pile of one type), and it cuts no way.

Groups never go on a road, path, lane, water, building, yard or story place, never within reach of a door, gate,
exit, the start, a creature or a waypoint route, and never cut the walkable ground apart. Builds stay reproducible:
the dressing draws from its own generator (zlib.crc32 of the map's name), so the rest of the map is unchanged.
"""
import collections, math, os, random, re, sqlite3, zlib
from kit.layout import N4, N8, square_px, px_square, cell_square
from kit import scenes as S
from kit import spacing as SP
from nox import CELL

_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "corpus", "out",
                   "nox_corpus.db")
_THINGS = None
SQ = CELL * math.sqrt(2)                    # a square's side in px (32.5)


def things():
    global _THINGS
    if _THINGS is None:
        _THINGS = {}
        if os.path.exists(_DB):
            with sqlite3.connect(_DB) as db:
                for n, cls, ext, ex, ey, flags in db.execute("SELECT name, class, ext, ex, ey, flags FROM things"):
                    _THINGS[n] = (cls or "", ext or "", flags or "", ex or 0, ey or 0)
    return _THINGS


def blocks(t):
    """Whether a thing stops a walker (a crate, a cart, a rock), not a flat or no-collide one (straw, bones, plants)."""
    cls, ext, flags = things().get(t, ("", "", "", 0, 0))[:3]
    if not ext or ext == "NULL" or "NO_COLLIDE" in flags or "MONSTER" in cls or "DOOR" in cls: return False
    if "NO_PUSH_CHARACTERS" in flags: return False
    return "OBSTACLE" in cls or "IMMOBILE" in cls or "SIMPLE" in cls


def radius(t):
    """About how far a thing reaches from its centre (px), for spacing pieces."""
    _, ext, flags, ex, ey = things().get(t, ("", "", "", 10, 0))
    if "NO_COLLIDE" in flags or "BELOW" in flags: return 6
    if ext == "BOX": return max(8, max(ex, ey) / 2)
    return max(6, ex)


def base(t):
    return re.sub(r"\d+$", "", t.replace("Immobile", ""))


# objects that do not make ground look furnished (invisible, or too small to read from a player's height)
NOT_A_PROP = re.compile(r"^(ColorLight|Amb|Invisible|PlayerStart|CaveRocksPebbles|CaveRocksTiny|CaveRocksSmall|Extent)|Shadow")
NATURAL_WALL = re.compile(r"Coni|Decidious|Aspen|Cave|Ice|Volcano|Root|Dirt|Rock|Hedge|Swamp|Forest|Tree|Snow|Mud",
                          re.I)
MASONRY_WALL = re.compile(r"Stone|Galava|Brick|Cobble|Town|Castle|Dungeon|DunMir|Ruin|LOTD|Marble|Ix", re.I)
MARTIAL_WALL = re.compile(r"TownWall|Galava", re.I)
MARTIAL_ROLES = ("barracks", "keep")
GAP = 6.0                                   # squares between any two scenes' anchors


class Exterior:
    def __init__(self, spec, land, biome="green", martial=False, seed=0, avoid=(), placed=None, culture=None):
        """biome: green, ice, lava, cave or swamp. martial: the settled ground is a garrison's (with no `placed`,
        where the buildings' roles are unknown). avoid: squares to keep clear. placed: the design's [(identity,
        building)] (StoryMap.place_buildings), so scenes find the buildings they belong to. culture: the map's own
        scenes (kit/scenes.py Theme.culture: "wizard" for Starwell's) join the catalogue's common ones."""
        self.spec, self.land, self.biome, self.martial = spec, land, biome, martial
        # one culture (Starwell's "wizard") or several (Harrowby's farmers and the ogres of its hill-fort: each theme
        # still keeps to the buildings and places it belongs to)
        self.cultures = {culture} if isinstance(culture, str) else set(culture or ())
        self.culture = culture
        self.rng = random.Random(zlib.crc32(f"{spec.d['name']}:exterior:{seed}".encode()))
        self.avoid = set(avoid)
        self.placed_b = list(placed or getattr(land, "buildings", None) or [])
        self.placed = collections.Counter()
        self.where = []                     # (theme, square, (x, y)) of each scene

    # ---- the ground --------------------------------------------------------------------------------------------
    def _dilate(self, squares, r):
        return {(i + a, j + b) for i, j in squares for a in range(-r, r + 1) for b in range(-r, r + 1)}

    def _route_squares(self):
        """Squares on and beside the ways people walk: the legs of the routes already laid (spec.routes, tours and
        patrols: consecutive waypoints, linked ones), and round every waypoint. Waypoints on no route yet (laid
        before their route is) keep the straight ways to every other such waypoint near them clear."""
        wps = self.spec.d.get("waypoints", [])
        by_name = {w["name"]: (w["x"], w["y"]) for w in wps if w.get("name")}
        by_id = {w["id"]: (w["x"], w["y"]) for w in wps}
        out, legs, on_route = set(), [], set()

        def line(p, q):
            (x0, y0), (x1, y1) = p, q
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / 12))
            for k in range(n + 1):
                out.add(px_square(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n))
        for r in getattr(self.spec, "routes", []) or []:
            pts = [by_name[n] for n in r.get("waypoints", []) if n in by_name]
            on_route |= set(pts)
            for k in range(len(pts) - 1): legs.append((pts[k], pts[k + 1]))
            if r.get("loop") and len(pts) > 2: legs.append((pts[-1], pts[0]))
        for w in wps:
            for l in w.get("links", []):
                if l in by_id: legs.append(((w["x"], w["y"]), by_id[l]))
        for p, q in legs: line(p, q)
        loose = [(w["x"], w["y"]) for w in wps if (w["x"], w["y"]) not in on_route]
        for p in loose + list(on_route): out |= self._dilate({px_square(*p)}, 1)
        for a in range(len(loose)):
            for b in range(a + 1, len(loose)):
                if math.hypot(loose[b][0] - loose[a][0], loose[b][1] - loose[a][1]) <= 24 * 32.5:
                    line(loose[a], loose[b])
        return self._dilate(out, 1)

    @staticmethod
    def _bfs(sources, cap):
        """Distance in squares (4-way steps) from the nearest source, up to cap: {square: (d, label)}."""
        out = {}
        q = collections.deque()
        for s, lab in sources:
            if s not in out: out[s] = (0, lab); q.append(s)
        while q:
            s = q.popleft()
            d, lab = out[s]
            if d >= cap: continue
            for a, b in N4:
                n = (s[0] + a, s[1] + b)
                if n not in out: out[n] = (d + 1, lab); q.append(n)
        return out

    def _setup(self):
        L, spec = self.land, self.spec
        lanes = set()
        for ln in getattr(L, "links", []):
            if ln.get("road"): continue
            for si, sj in ln["path"]:
                lanes.add((int(math.floor(si)), int(math.floor(sj)) + 1))
        strict = set(getattr(L, "taken_strict", ()))
        margin = self._dilate(strict, 3)
        self.why = dict(roads=self._dilate(set(L.roads) | L.plaza, 1), water=self._dilate(L.water, 1),
                        buildings=strict, lanes=self._dilate(lanes, 2), taken=L.taken - margin,
                        avoid=self.avoid, routes=self._route_squares())
        no = set().union(*self.why.values())
        self.props, self.colliders, self.gates = [], [], []
        self.tgrid = collections.defaultdict(list)            # (type, x, y) of every thing, for Westwood's spacing
        self.signs = collections.defaultdict(list)          # family -> px of things already on the map
        for o in spec.d["objects"]:
            t, x, y = o.get("type", "NPC"), o["x"], o["y"]        # a clone is a person
            cls = things().get(t, ("", "", "", 0, 0))[0] if "type" in o else "MONSTER"
            if "DOOR" in cls or "Door" in t or "Gate" in t:
                no |= self._dilate({px_square(x, y)}, 3)
                if "Gate" in t or "Gate" in (o.get("scr") or ""): self.gates.append((x, y))
            elif re.match(r"PlayerStart|InvisibleExit|.*Exit", t) or "EXIT" in cls:
                no |= self._dilate({px_square(x, y)}, 4)
            elif "MONSTER" in cls or o.get("scr"):
                no |= self._dilate({px_square(x, y)}, 1)
            self.colliders.append((x, y))
            if "type" in o and not NOT_A_PROP.search(t): self.tgrid[(int(x // 92), int(y // 92))].append((t, x, y))
            if not NOT_A_PROP.search(t): self.props.append((x, y))
            for fam, stems in S.FAMILY_SIGNS.items():
                if t.startswith(stems): self.signs[fam].append((x, y))
        self.free = {s for s in L.squares if s not in no}
        # walkable squares, for the check that a group cuts nothing off
        wall_sq = {cell_square(*c) for c in spec.wallmap}
        self.walk = set(L.squares) - L.water - strict - wall_sq
        for o in spec.d["objects"]:
            if blocks(o.get("type", "")): self.walk.discard(px_square(o["x"], o["y"]))
        self.walls = spec.wallmap
        self._buildings()
        roads = set(L.roads) - set(L.plaza)
        self.d_road = self._bfs([(s, s) for s in roads], 6)
        self.d_plaza = self._bfs([(s, 0) for s in L.plaza], 8)
        self.d_water = self._bfs([(s, 0) for s in L.water], 4)
        mw = {cell_square(*c) for c, w in self.walls.items() if MARTIAL_WALL.search(w["material"])
              and c not in self.cell_b}
        self.d_martial = self._bfs([(s, 0) for s in mw], 4)
        # built walls that are no building's (a curtain, a yard's fence, a ruin): ground near them is settled
        bw = {cell_square(*c) for c, w in self.walls.items() if c not in self.cell_b and
              not (NATURAL_WALL.search(w["material"]) and not MASONRY_WALL.search(w["material"]))}
        self.d_built = self._bfs([(s, 0) for s in bw], 10)
        n_free = len(self.free)
        self.scale = min(2.5, max(1.0, n_free / 3000))

    def _buildings(self):
        """The buildings: role, squares, middle and doors (px); the wall cells round each, by building."""
        from kit.village import _squares_of
        self.B, self.cell_b = [], {}
        for k, (bid, b) in enumerate(self.placed_b):
            foot = _squares_of(b.footprint)
            if not foot: continue
            pts = [square_px(i + 0.5, j - 0.5) for i, j in foot]
            mid = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
            doors = [d.px for d in b.entrances if d.px != (0.0, 0.0)]
            self.B.append(dict(role=bid.role, foot=foot, mid=mid, doors=doors, k=len(self.B)))
            for x, y in b.footprint:
                for a in (-1, 0, 1):
                    for c in (-1, 0, 1):
                        self.cell_b.setdefault((x + a, y + c), len(self.B) - 1)
        self.d_bld = self._bfs([(s, B["k"]) for B in self.B for s in B["foot"]], 16)

    # ---- what a place is ---------------------------------------------------------------------------------------
    def _context(self, s):
        """Tags for square s (town, wild, road, square, water, gate, martial) and its nearest building (or None)."""
        tags = set()
        db = self.d_bld.get(s)
        bld = self.B[db[1]] if db and db[0] <= 14 else None
        if bld or s in self.d_plaza or s in self.d_built: tags.add("town")
        else: tags.add("wild")
        if s in self.d_road and 1 <= self.d_road[s][0] <= 4: tags.add("road")
        if s in self.d_plaza: tags.add("square")
        if s in self.d_water: tags.add("water")
        x, y = square_px(s[0] + 0.5, s[1] - 0.5)
        if any(math.hypot(x - gx, y - gy) < 9 * SQ for gx, gy in self.gates): tags.add("gate")
        if (bld and bld["role"] in MARTIAL_ROLES and db[0] <= 12) or s in self.d_martial or \
                (self.martial and not self.B and "town" in tags):
            tags.add("martial")
        return tags, bld, (db[0] if db else 99)

    def _side(self, bld, x, y):
        """Which side of building bld a point lies on: front (its door's), back or side."""
        if not bld or not bld["doors"]: return "side"
        mx, my = bld["mid"]
        vx, vy = x - mx, y - my
        dx, dy = min(bld["doors"], key=lambda d: math.hypot(d[0] - x, d[1] - y))
        ux, uy = dx - mx, dy - my
        n = math.hypot(vx, vy) * math.hypot(ux, uy) or 1
        c = (vx * ux + vy * uy) / n
        return "front" if c > 0.55 else ("back" if c < -0.25 else "side")

    def _wall_kinds(self, cell):
        """The kinds of wall a cell is: house (with its building), martial, masonry, fence, wild, cave."""
        if cell in self.cell_b: return {"house"}, self.B[self.cell_b[cell]]
        mat = self.walls[cell]["material"]
        if NATURAL_WALL.search(mat) and not MASONRY_WALL.search(mat):
            return ({"wild", "cave"} if self.biome in ("cave", "lava") else {"wild"}), None
        if MARTIAL_WALL.search(mat): return {"martial", "masonry"}, None
        if MASONRY_WALL.search(mat) and not re.search("Cobble|Dilapidated", mat): return {"masonry"}, None
        return {"fence"}, None

    # ---- geometry helpers ---------------------------------------------------------------------------------------
    @staticmethod
    def _grid(pts, size=92):
        g = collections.defaultdict(list)
        for x, y in pts: g[(int(x // size), int(y // size))].append((x, y))
        return g

    def _near(self, grid, x, y, r, size=92):
        k = int(r // size) + 1
        for a in range(int(x // size) - k, int(x // size) + k + 1):
            for b in range(int(y // size) - k, int(y // size) + k + 1):
                for p in grid.get((a, b), ()):
                    if (p[0] - x) ** 2 + (p[1] - y) ** 2 < r * r: return True
        return False

    def _wall_near(self, x, y, clear=22.0):
        """A wall's cell under the point, or a wall's centre line (through its cells' centres) within `clear` px."""
        cx, cy = int(x // CELL), int(y // CELL)
        if (cx, cy) in self.walls: return True
        return any((cx + a, cy + b) in self.walls and
                   math.hypot((cx + a + 0.5) * CELL - x, (cy + b + 0.5) * CELL - y) < clear
                   for a in (-1, 0, 1) for b in (-1, 0, 1))

    def _nearest_wall(self, x, y, reach=3):
        cx, cy = int(x // CELL), int(y // CELL)
        best = None
        for a in range(-reach, reach + 1):
            for b in range(-reach, reach + 1):
                c = (cx + a, cy + b)
                if c in self.walls:
                    d = (a * a + b * b, c)
                    if best is None or d < best: best = d
        return best and best[1]

    def _ok(self, t, x, y, mine):
        s = px_square(x, y)
        dbg = getattr(self, "okwhy", None)
        if s not in self.free:
            if dbg is not None: dbg["notfree"] += 1
            return False
        if self._wall_near(x, y):
            if dbg is not None: dbg["wall"] += 1
            return False
        r = radius(t)
        if self._near(self.cgrid, x, y, max(20, r + 8)):
            if dbg is not None: dbg["collider"] += 1
            return False
        # Westwood's closest pairs (kit/spacing; Starwell playtest: "these crates are simply too close to each
        # other"), with the scene's own pieces and with what already stands round it; and off every wall line
        near = [p for a in (-1, 0, 1) for b in (-1, 0, 1)
                for p in self.tgrid.get((int(x // 92) + a, int(y // 92) + b), ())]
        if not SP.spaced(t, x, y, near + getattr(self, "_typed", [])):
            if dbg is not None: dbg["spacing"] += 1
            return False
        if SP.wall_clearance(self.walls, x, y, reach=2) < max(14.0, 0.8 * SP.sprite_half(t)):
            if dbg is not None: dbg["wall line"] += 1
            return False
        return not any((x - a) ** 2 + (y - b) ** 2 < max(14, 0.7 * (r + rb)) ** 2 for a, b, rb in mine)

    def _cuts(self, F):
        """Whether blocking the squares F splits the walkable squares round them (within a window)."""
        F = set(F) & self.walk
        if not F: return False
        win = self._dilate(F, 4) & self.walk
        rest = win - F
        nb = {(i + a, j + b) for i, j in F for a, b in N8} & rest
        if not nb: return False
        start = min(nb)
        seen, q = {start}, [start]
        while q:
            i, j = q.pop()
            for a, b in N4:
                n = (i + a, j + b)
                if n in rest and n not in seen: seen.add(n); q.append(n)
        return not nb <= seen

    # ---- choosing a theme --------------------------------------------------------------------------------------
    def _cap(self, th):
        return int(round(th.cap * self.scale)) if th.scales else th.cap

    def _spaced(self, th, s, x, y):
        """Whether a scene of theme th may stand at square s: apart from every scene, and its family's spacing from
        others of its family (scenes, and like things already on the map)."""
        for k2, s2, (x2, y2) in self.where:
            d = math.hypot(s[0] - s2[0], s[1] - s2[1])
            th2 = S.THEMES[k2]
            if th.scales and th2.scales:                # the wood's own heaps may lie closer together
                if d < GAP - 2 or math.hypot(x - x2, y - y2) < 0.6 * (th.size + th2.size): return False
            elif d < GAP or math.hypot(x - x2, y - y2) < 0.9 * (th.size + th2.size): return False
            if S.THEMES[k2].family == th.family and d < th.spacing: return False
        return not any(math.hypot(x - a, y - b) < th.spacing * SQ for a, b in self.signs.get(th.family, ()))

    def _fits(self, th, tags, bld, dist, kinds=None, side=None, front=False):
        """Whether theme th belongs at a place: its biome, walls, places, buildings and sides."""
        if self.biome not in th.biomes or self.placed[th.name] >= self._cap(th): return False
        if th.culture and th.culture not in self.cultures: return False
        if th.family in S.FAMILY_CAP and                 sum(1 for k2, _, _ in self.where if S.THEMES[k2].family == th.family) >= S.FAMILY_CAP[th.family]:
            return False
        if kinds is not None and not (kinds & set(th.walls)): return False
        if th.places and not (tags & set(th.places)): return False
        if th.requires and not set(th.requires) <= tags: return False
        if front and th.tall: return False
        if th.need and not (bld and bld["role"] in th.roles and dist <= th.near): return False
        if side and kinds and "house" in kinds and side not in th.sides: return False
        if th.house_roles and kinds and "house" in kinds and not (bld and bld["role"] in th.house_roles): return False
        if bld and dist <= 3 and th.name in self._own_scenes(bld): return False    # its door scenes have one
        return True

    @staticmethod
    def _own_scenes(bld):
        from kit.identity import BUILDINGS
        same = {"chopping_block": "chopping_yard", "deliveries": "supply_corner", "mine_carts": "mine_cache"}
        return {same.get(k, k) for k in BUILDINGS.get(bld["role"], {}).get("scenes", ())}

    def _weight(self, th, bld, dist):
        fam_seen = sum(1 for k2, _, _ in self.where if S.THEMES[k2].family == th.family)
        w = th.weight / (1 + 0.6 * fam_seen)
        if bld and bld["role"] in th.roles and dist <= th.near: w *= 4
        return w

    # ---- laying a scene ----------------------------------------------------------------------------------------
    def _lay(self, th, origin, n, tdir):
        """Lay one of theme th's layouts from origin (px) with forward direction n and along direction tdir (unit
        px vectors). Returns the pieces laid [(type, x, y)], or None (nothing laid) when a must-have piece does not fit,
        the scene comes out too thin or of too few kinds, or it would cut a way."""
        spec, rng = self.spec, self.rng
        ox, oy = origin
        if th.clear and (self._near(self.cgrid, ox + n[0] * 0, oy, th.clear) or
                         any(px_square(ox + th.clear * math.cos(a), oy + th.clear * math.sin(a)) not in self.free
                             for a in [k * math.pi / 4 for k in range(8)])):
            return None
        layout = rng.choice(th.layouts)
        # a loose theme's pieces set down by hand (scene lab round 7: "the sign at the same step every time", "every
        # piece at a fixed offset"): each piece off its mark by up to th.loose px, a row's steps stretched or shrunk by
        # up to th.loose_step; from the scene's own generator, so the dressing's draws are as before
        hand = random.Random(zlib.crc32(f"{spec.d['name']}:hand:{th.name}:{int(ox)},{int(oy)}".encode()))
        why = self.why_fail = collections.Counter() if not hasattr(self, "why_fail") else self.why_fail
        mir = -1 if (th.mirror and rng.random() < 0.5) else 1
        line = S.line_of(*tdir)
        plan, mine, want = [], [], 0
        self._typed = []
        for k, pc in enumerate(layout):
            if pc["p"] < 1 and rng.random() >= pc["p"]:
                continue
            got = 0
            if pc["types"] == ("@tent",):
                way = "DN" if line == "\\" else "UP"
                if th.name == "market_stall": way = "UP"      # (Westwood's three stalls: UP awnings, purple and orange
                #                                              or green and red; the judge read red/blue as not theirs)
                # the awning's open side faces the camera: its wares go before it (DN: south-west, UP: south-east)
                n = (-1 / math.sqrt(2), 1 / math.sqrt(2)) if way == "DN" else (1 / math.sqrt(2), 1 / math.sqrt(2))
                tdir = (-n[1], n[0])
                parts = S.tent_pieces(way, rng.choice(S.TENT_COLOURS[way]), ox, oy)
                if not all(self._ok(t, x, y, []) or "Shadow" in t for t, x, y in parts): return None
                for t, x, y in parts:
                    plan.append((t, x, y)); mine.append((x, y, 30 if "Side" in t else 10 if "Top" in t else 0))
                # (the cloths overhead: the stock stands under the awning's front, Con09d's apples)
                continue
            if pc["ring"]:
                r, kk = pc["ring"]
                ph = rng.uniform(0, 2 * math.pi)
                pts = [(ox + r * math.cos(ph + 2 * math.pi * q / kk), oy + r * math.sin(ph + 2 * math.pi * q / kk))
                       for q in range(kk)]
                for x, y in pts:
                    t = rng.choice(pc["types"])
                    if px_square(x, y) in self.free:
                        plan.append((t, x, y)); got += 1
                if pc["must"] and got < len(pts) - 1: return None
                continue
            cnt = pc["n"] if isinstance(pc["n"], int) else rng.randint(*pc["n"])
            want += cnt
            da, do, ca = 0.0, 0.0, 0.0
            for c in range(cnt):
                a = mir * (pc["a"] + pc["step"][0] * c) + rng.uniform(-3, 3)
                o = pc["o"] + pc["step"][1] * c + rng.uniform(-3, 3)
                if th.loose or th.loose_step:
                    if c == 0: da, do = hand.uniform(-th.loose, th.loose), hand.uniform(-th.loose, th.loose)
                    else:                                           # a row drifts as it goes, its steps uneven
                        ca += pc["step"][0] * hand.uniform(-th.loose_step, th.loose_step)
                        do += hand.uniform(-0.35, 0.35) * th.loose
                    a += mir * (da + ca); o += do
                x, y = ox + n[0] * o + tdir[0] * a, oy + n[1] * o + tdir[1] * a
                t = rng.choice(pc["types"])
                if pc["orient"] == "line": t = S.ALONG[line].get(t, t)
                elif pc["orient"] == "face" and t.startswith("Bench"):
                    t = S.BENCH_FACING[S.axis_of(ox - x, oy - y)]
                elif pc["orient"] == "out" and t.startswith("Bench"):
                    t = S.BENCH_FACING[S.axis_of(*n)]
                elif pc["orient"] == "cot":
                    t = S.COT_FOOT[S.axis_of(ox - x, oy - y)]
                if not self._ok(t, x, y, mine): continue
                plan.append((t, x, y)); mine.append((x, y, radius(t))); self._typed.append((t, x, y)); got += 1
            if (pc["must"] or k == 0) and got == 0:
                why[(th.name, "must", k)] += 1; return None
        kinds = {base(t) for t, _, _ in plan if "Shadow" not in t}
        if len(kinds) < th.min_types or len(plan) < th.min_pieces:
            why[(th.name, "thin")] += 1; return None
        if want and len(mine) < th.min_share * want:
            why[(th.name, "share")] += 1; return None          # the scene laid whole, or not at all
        F = set()
        for t, x, y in plan:                       # the squares a piece's body covers, not only its centre's
            if not blocks(t): continue
            F.add(px_square(x, y))
            r = radius(t)
            if r >= 14:
                F |= {px_square(x + r * math.cos(q * math.pi / 4), y + r * math.sin(q * math.pi / 4)) for q in range(8)}
        tent = [(x, y) for t, x, y in plan if t.startswith("TraderTent") and "Shadow" not in t]
        if tent:
            # the ground under an awning counts as blocked with its cloths and poles: else the open square between its
            # sides read as a pocket it cut off, and no stall was ever laid (the scene lab, 2026-10-06)
            xs, ys = [x for x, _ in tent], [y for _, y in tent]
            for x in range(int(min(xs)), int(max(xs)) + 1, 12):
                for y in range(int(min(ys)), int(max(ys)) + 1, 12):
                    F.add(px_square(x, y))
        if self._cuts(F):
            why[(th.name, "cuts")] += 1; return None
        for t, x, y in plan:
            spec.obj_px(t, x, y)
            self.cgrid[(int(x // 92), int(y // 92))].append((x, y))
            self.tgrid[(int(x // 92), int(y // 92))].append((t, x, y))
        self._typed = []
        self.walk -= F
        return plan

    def _frames_open(self, th, s):
        """(origin, n, tdir) to try for an open scene at square s."""
        cx, cy = square_px(s[0] + 0.5, s[1] - 0.5)
        r2 = 1 / math.sqrt(2)
        diag = [(r2, r2), (-r2, r2), (r2, -r2), (-r2, -r2)]
        if th.face == "road" and s in self.d_road:
            rs = self.d_road[s][1]
            rx, ry = square_px(rs[0] + 0.5, rs[1] - 0.5)
            dx, dy = cx - rx, cy - ry
            n = (math.copysign(r2, dx or 1), math.copysign(r2, dy or 1))
            if abs(abs(dx) - abs(dy)) > 0.6 * max(abs(dx), abs(dy)):     # the road lies square off: either diagonal
                n2 = (n[0], -n[1]) if abs(dx) > abs(dy) else (-n[0], n[1])
                opts = [n, n2]
            else:
                opts = [n]
        else:
            opts = diag[:]
            self.rng.shuffle(opts)
        out = []
        for di, dj in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            if (s[0] + di, s[1] + dj) not in self.free: continue
            ox, oy = square_px(s[0] + di + 0.5, s[1] + dj - 0.5)
            out += [((ox, oy), n, (-n[1], n[0])) for n in opts[:3]]
        return out

    def _wall_spots(self, s, r=4):
        """Free squares near s with a wall within 2 cells, the nearest first, one for each wall (a building's, the
        curtain, the forest): [(square, wall cell)]."""
        found = []
        for a in range(-r, r + 1):
            for b in range(-r, r + 1):
                t = (s[0] + a, s[1] + b)
                if t not in self.free: continue
                x, y = square_px(t[0] + 0.5, t[1] - 0.5)
                w = self._nearest_wall(x, y, 2)
                if w is None: continue
                found.append((a * a + b * b, t, w))
        found.sort()
        out, seen = [], set()
        for _, t, w in found:
            kinds, wb = self._wall_kinds(w)
            key = (wb["k"] if wb else None, tuple(sorted(kinds)))
            if key in seen: continue
            seen.add(key); out.append((t, w))
        return out[:3]

    def _try_wall(self, t, w, only=None):
        """A wall scene at free square t against wall cell w (only: the theme names allowed)."""
        kinds, wb = self._wall_kinds(w)
        wx, wy = (w[0] + 0.5) * CELL, (w[1] + 0.5) * CELL
        x, y = square_px(t[0] + 0.5, t[1] - 0.5)
        dx, dy = x - wx, y - wy
        if abs(dx) < 4 and abs(dy) < 4: return None
        # out from the wall: snapped to a diagonal of the screen, as Nox's walls run
        n = (math.copysign(1, dx) / math.sqrt(2), math.copysign(1, dy) / math.sqrt(2))
        # a wall below the group on screen is a front wall: the camera looks over it, so tall or wide
        # sprites (a hay heap, a cart, racks) would be drawn over its top; they keep to the back walls
        front = n[1] < 0
        tags, bld, dist = self._context(t)
        if wb: bld, dist = wb, 0
        side = self._side(bld, x, y) if "house" in kinds else None
        cands = [th for th in S.CATALOGUE if th.stand == "wall" and (only is None or th.name in only)
                 and self._fits(th, tags, bld, dist, kinds, side, front) and self._spaced(th, t, x, y)]
        tdir = (-n[1], n[0])
        for _ in range(3):
            if not cands: return None
            th = self.rng.choices(cands, [self._weight(c, bld, dist) for c in cands])[0]
            cands.remove(th)
            extra = 12 if front else 0
            plan = self._lay(th, (wx + n[0] * extra, wy + n[1] * extra), n, tdir)
            if plan:
                return self._done(th, t, plan[0][1:])
        return None

    def _try_open(self, s, only=None):
        tags, bld, dist = self._context(s)
        x, y = square_px(s[0] + 0.5, s[1] - 0.5)
        cands = [th for th in S.CATALOGUE if th.stand == "open" and (only is None or th.name in only)
                 and self._fits(th, tags, bld, dist) and self._spaced(th, s, x, y)]
        for _ in range(3):
            if not cands: return None
            th = self.rng.choices(cands, [self._weight(c, bld, dist) for c in cands])[0]
            cands.remove(th)
            for origin, n, tdir in self._frames_open(th, s):
                if self._lay(th, origin, n, tdir):
                    return self._done(th, px_square(*origin), origin)
        return None

    def _done(self, th, s, xy):
        self.placed[th.name] += 1
        self.where.append((th.name, s, xy))
        return th.name

    def _try(self, s):
        """A scene at or near the empty square s: against the nearest wall within 4 squares (mostly), else open."""
        ws = self._wall_spots(s)
        order = ["wall", "open"] if ws and self.rng.random() < 0.75 else ["open", "wall"]
        for where in order:
            if where == "wall":
                for t, w in ws:
                    if self._try_wall(t, w): return True
            elif where == "open":
                if self._try_open(s): return True
        return False

    # ---- the passes --------------------------------------------------------------------------------------------
    def _emptiness(self, s):
        x, y = square_px(s[0] + 0.5, s[1] - 0.5)
        best = 400.0
        for a in range(int(x // 92) - 4, int(x // 92) + 5):
            for b in range(int(y // 92) - 4, int(y // 92) + 5):
                for p in self.pgrid.get((a, b), ()):
                    d = math.hypot(p[0] - x, p[1] - y)
                    if d < best: best = d
        return best

    def _purpose(self):
        """Each building's own scenes, then a guard post by each gate."""
        for bld in self.B:
            for name, chance in S.ROLE_SCENES.get(bld["role"], ()):
                th = S.THEMES[name]
                if self.biome not in th.biomes or (th.culture and th.culture not in self.cultures) or                         self.rng.random() >= chance: continue
                ring = {(i + a, j + b) for i, j in bld["foot"] for a in range(-th.near, th.near + 1)
                        for b in range(-th.near, th.near + 1)} & self.free
                if th.stand == "wall":
                    ring = {s for s in ring if self.d_bld.get(s, (99,))[0] <= 2 and self.d_bld[s][1] == bld["k"]}
                else:
                    ring = {s for s in ring if 3 <= self.d_bld.get(s, (99,))[0] <= th.near}
                cands = sorted(ring, key=lambda s: (-round(self._emptiness(s) / 23), s))[:40]
                self.rng.shuffle(cands)
                cands.sort(key=lambda s: -round(self._emptiness(s) / 46))
                for s in cands[:14]:
                    if th.stand == "wall":
                        x, y = square_px(s[0] + 0.5, s[1] - 0.5)
                        w = self._nearest_wall(x, y, 2)
                        if w is None or self.cell_b.get(w) != bld["k"]: continue
                        if self._try_wall(s, w, only={name}): self._refresh(); break
                    elif self._try_open(s, only={name}): self._refresh(); break
        for gx, gy in self.gates:
            g = px_square(gx, gy)
            cands = [s for s in self._dilate({g}, 7) if s in self.free and
                     3.5 <= math.hypot(s[0] - g[0], s[1] - g[1]) <= 7]
            cands.sort(key=lambda s: (-round(self._emptiness(s) / 46), s))
            for s in cands[:12]:
                x, y = square_px(s[0] + 0.5, s[1] - 0.5)
                w = self._nearest_wall(x, y, 2)
                if w is not None and self._try_wall(s, w, only={"guard_post"}): self._refresh(); break

    def _refresh(self):
        self.pgrid = self._grid([(x, y) for x, y in self.props] +
                                [(o["x"], o["y"]) for o in self.spec.d["objects"][self.n0:]])

    # ---- the whole map ----------------------------------------------------------------------------------------
    def dress(self, reach=4.5, max_groups=400):
        """Purpose first, then fill: while a free square lies more than `reach` cells from every prop, put a scene
        that belongs there (the emptiest first), until nothing fits. Returns {theme: count}. NOX_NODRESS=1 leaves the
        ground as it was (for comparisons)."""
        if os.environ.get("NOX_NODRESS"): return {}
        self._setup()
        if os.environ.get("NOX_DRESS_LOG"): self.okwhy = collections.Counter()
        self.n0 = len(self.spec.d["objects"])
        self.cgrid = self._grid(self.colliders)
        self._refresh()
        self._purpose()
        R = reach * CELL
        dist = {s: self._emptiness(s) for s in self.free}
        tried = set()
        while len(self.where) < max_groups:
            cand = [(d, s) for s, d in dist.items() if d > R and s not in tried]
            if not cand: break
            d, s = max(cand, key=lambda c: (round(c[0], 1), c[1]))
            n0 = len(self.spec.d["objects"])
            if not self._try(s):
                tried.add(s); continue
            new = [(o["x"], o["y"]) for o in self.spec.d["objects"][n0:]]
            for p in new: self.pgrid[(int(p[0] // 92), int(p[1] // 92))].append(p)
            for t in list(dist):
                if dist[t] <= R: continue
                x, y = square_px(t[0] + 0.5, t[1] - 0.5)
                for p in new:
                    dd = math.hypot(p[0] - x, p[1] - y)
                    if dd < dist[t]: dist[t] = dd
        if os.environ.get("NOX_DRESS_LOG"):
            print("dressing:", ", ".join(f"{k} {v}" for k, v in sorted(self.placed.items())))
            for k, s_, (x, y) in self.where: print(f"   {k:14s} {int(x):5d} {int(y):5d}")
            print("  ok-fails", dict(getattr(self, "okwhy", {})))
            for k, v in sorted(getattr(self, "why_fail", {}).items(), key=lambda kv: -kv[1])[:30]: print("  fail", k, v)
        return dict(self.placed)
