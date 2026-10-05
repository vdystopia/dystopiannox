"""Exterior dressing: composed prop groups that fill the empty stretches of outdoor ground (2026-10-05 playtest:
"exterior areas are way too empty ... use more object diversity and fill the spaces more", a long alley between a
castle's curtain wall and the buildings inside it held one bush and two pebbles).

What Westwood does (review/exteriors.py --westwood; per 100 open floor tiles, roads left out, pebbles and the
smallest rocks not counted): its towns carry 25 props (13 maps, 13.5-38), 6 of them made things (crates, barrels,
racks, carts, rubble...), and only 16% of their open ground lies more than 4 cells from any prop, 6% more than 6.
Galava's castle grounds are the sparsest built place (40% / 24%). Along walls it stands barrels and water barrels,
straw, steel barrels and crates, tombstones, fence debris, torch poles; in the open, barrels, stumps, straw, rubble
(Brick), benches, crates, armour racks, trader tents, statues. Its caves, lava and ice maps are emptier (50-60% of
the ground over 4 cells from a prop): rock pillars and boulders at the walls, bones, stalagmites, fire grates.

The kit: after everything else is placed (the story's places, the people, their routes), `Exterior.dress()` finds
the open ground farthest from any prop and puts a group there, then the next farthest, until no free ground lies
more than `reach` cells from a prop. Each group is a little scene with a reason, chosen by where it stands:
- against a built wall (a house, a fence, a curtain wall): supplies stacked along it, barrels, a woodpile, hay, a
  cart and its load; rubble at the foot of masonry; by a town wall a guard's brazier and stool, a rack of arms;
- against a natural wall (the forest, a cliff): a fallen log, a stump, a boulder in ferns, a heap of rock; in a
  cave rock pillars and stalagmites, on lava a fire grate among bones and rubble, in snow bones and boulders;
- in the open near buildings: a cart and its load, a woodcutter's block, a stack of goods, (castles) a weapon rack;
  away from buildings the natural groups.
Each kind of group matches the biome (green, ice, lava, cave, swamp). Groups never go on a road, path, lane, water,
building, yard or story place, never within reach of a door, gate, exit, the start, a creature or a waypoint route,
and never cut the walkable ground: a group whose squares would split their neighbours apart is taken back.
Builds stay reproducible: the dressing draws from its own generator (zlib.crc32 of the map's name), so the rest of
the map is unchanged.
"""
import collections, math, os, random, re, sqlite3, zlib
from kit.layout import N4, N8, square_px, px_square, cell_square
from nox import CELL

_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "corpus", "out",
                   "nox_corpus.db")
_THINGS = None


def things():
    global _THINGS
    if _THINGS is None:
        _THINGS = {}
        if os.path.exists(_DB):
            with sqlite3.connect(_DB) as db:
                for n, cls, ext, flags in db.execute("SELECT name, class, ext, flags FROM things"):
                    _THINGS[n] = (cls or "", ext or "", flags or "")
    return _THINGS


def blocks(t):
    """Whether a thing stops a walker (a crate, a cart, a rock), not a flat or no-collide one (straw, bones, plants)."""
    cls, ext, flags = things().get(t, ("", "", ""))
    if not ext or ext == "NULL" or "NO_COLLIDE" in flags or "MONSTER" in cls or "DOOR" in cls: return False
    if "NO_PUSH_CHARACTERS" in flags: return False
    return "OBSTACLE" in cls or "IMMOBILE" in cls or "SIMPLE" in cls


# objects that do not make ground look furnished (invisible, or too small to read from a player's height)
NOT_A_PROP = re.compile(r"^(ColorLight|Amb|Invisible|PlayerStart|CaveRocksPebbles|CaveRocksTiny|CaveRocksSmall|Extent)|Shadow")
NATURAL_WALL = re.compile(r"Coni|Decidious|Aspen|Cave|Ice|Volcano|Root|Dirt|Rock|Hedge|Swamp|Forest|Tree|Snow|Mud",
                          re.I)
MASONRY_WALL = re.compile(r"Stone|Galava|Brick|Cobble|Town|Castle|Dungeon|DunMir|Ruin|LOTD|Marble|Ix", re.I)
MARTIAL_WALL = re.compile(r"TownWall|Galava", re.I)

CRATES = ("Crate1", "Crate2", "DarkCrate1", "DarkCrate2")
BARRELS = ("Barrel", "Barrel2", "Barrel", "WaterBarrel")
BIG_BARRELS = ("LargeBarrel1", "LargeBarrel2", "PiledBarrels1", "PiledBarrels2")
STEEL = ("BarrelSteel1", "BarrelSteel2", "CrateSteel1", "CrateSteel2", "CrateSteel3", "CrateSteel4")
LOGS = ("ForestLog01", "ForestLog02", "ForestLog03", "ForestLog04")
STUMPS = ("Stump1", "Stump2", "Stump9")
HAY = ("OgreStraw1", "OgreStraw2", "OgreStraw3", "OgreStraw4", "OgreStraw5")
STRAW = ("Straw1", "Straw2")
RUBBLE = ("RuinsColumnOutdoorRubble05", "RuinsColumnOutdoorRubble06", "RuinsColumnOutdoorRubble07",
          "RuinsColumnOutdoorRubble08", "RuinsColumnOutdoorRubble09", "Brick0", "Brick1", "Brick2", "Brick3")
ROCKS = ("CaveRocksLarge", "CaveRocksMedium", "CaveRocksMedium")
BIG_ROCKS = ("CaveRocksHuge", "CaveBoulders")
BONES = ("ArmBone", "LegBone", "Skull", "LegBone")
FUNGI = ("Mushroom1", "Mushroom2", "Mushroom3", "Mushroom4", "Mushroom5")
FERNS = ("PlantFern1", "PlantFern2", "Plant4", "FoliageDense1")

# A group: (where, biomes, place, weight, pieces). where: "wall" (against a wall of the place's kind) or "open";
# place: "built", "masonry", "martial" (a town or curtain wall, or a castle's courtyard) or "wild". Pieces:
# (types, along, out, count): along the wall (px; open: across) and out from it (px; open: forward), `count`
# pieces stepping 22 px (crates 27) along from there. The first piece is the group's anchor: without it nothing is placed.
G = "green"
ALL = ("green", "ice", "lava", "cave", "swamp")
GROUPS = {
    # against a built wall: the household's and the garrison's things
    "stores": ("wall", (G, "ice", "swamp"), "built", 5,
               [(CRATES, -32, 26, 3), (BARRELS, 34, 24, 2), (CRATES + BARRELS, -20, 50, 1)]),
    "barrels": ("wall", (G, "ice", "swamp", "lava"), "built", 4,
                [(BIG_BARRELS, -18, 26, 1), (BARRELS, 6, 24, 3), (("WaterBarrel",), -6, 48, 1)]),
    "woodpile": ("wall", (G, "swamp"), "built", 4,
                 [(("ForestLog03",), 0, 30, 1), (LOGS, -40, 28, 1), (LOGS, 38, 30, 1), (STUMPS, 10, 62, 1),
                  (("BarrelWithTools1", "BarrelWithTools2"), -26, 56, 1)]),
    "hay": ("wall", (G, "swamp"), "built", 3,
            [(HAY, 0, 34, 1), (STRAW, -36, 30, 2), (("Barrel", "TraderAppleCrate"), 40, 26, 1)]),
    "rubble": ("wall", ALL, "masonry", 3,
               [(("SmallStoneBlock",), 0, 28, 1), (RUBBLE, -34, 24, 3), (RUBBLE, 30, 46, 2),
                (("CaveRocksMedium", "CaveRocksSmall"), 26, 22, 1)]),
    "cart": ("wall", (G, "ice", "swamp"), "built", 2,
             [(("OutdoorTraderCart",), 0, 40, 1), (CRATES, -58, 28, 1), (("TraderAppleCrate", "Barrel"), 52, 26, 2),
              (STRAW, -20, 66, 1)]),
    "guardpost": ("wall", (G, "ice", "swamp", "lava"), "martial", 4,
                  [(("Brazier",), 0, 34, 1), (("Stool1", "Stool2"), -30, 30, 1), (("WaterBarrel", "Barrel"), 32, 24, 1),
                   (("TraderQuiverRack",), 52, 30, 1)]),
    "armsrack": ("wall", (G, "ice", "swamp", "lava"), "martial", 4,
                 [(("TraderPoleArm1", "TraderPoleArm2"), 0, 34, 1), (("TraderBowRack2",), -44, 30, 1),
                  (("TraderArmorRack1", "TraderArmorRack2"), 44, 30, 1), (CRATES, 70, 26, 1)]),
    "minestores": ("wall", ("cave", "lava"), "built", 5,
                   [(STEEL, -30, 26, 3), (("BarrelWithTools1", "BarrelWithTools2"), 40, 26, 1),
                    (("MiningShovelInGround", "MiningPickAxeInGround1", "MineOreCartWheel"), 6, 52, 1)]),
    "orecart": ("wall", ("cave",), "built", 3,
                [(("MineOreCart1", "MineOreCartBroken1"), 0, 34, 1), (STEEL, -48, 26, 1), (ROCKS, 40, 30, 2),
                 (("MineOreCartWheel",), 20, 62, 1)]),
    # against a natural wall: the wood's and the rock's own heaps
    "deadfall": ("wall", (G, "swamp"), "wild", 4,
                 [(LOGS, 0, 34, 1), (FUNGI, -26, 26, 2), (STUMPS, 36, 40, 1), (FERNS, -8, 62, 1)]),
    "boulders": ("wall", (G, "swamp"), "wild", 4,
                 [(BIG_ROCKS, 0, 32, 1), (ROCKS, -30, 26, 2), (FERNS, 30, 44, 1), (("CaveRocksSmall",), 8, 62, 2)]),
    "pillars": ("wall", ("cave",), "wild", 5,
                [(("CaveRockPillarShort1", "CaveRockPillarShort2", "CaveRockPillarTall1"), 0, 32, 1),
                 (ROCKS, -34, 26, 2), (("SmallStalagmite",), 30, 44, 1), (("Mushroom3",), -10, 60, 2)]),
    "bonepile": ("wall", ("cave", "lava", "ice", "swamp"), "wild", 3,
                 [(BIG_ROCKS, 0, 30, 1), (BONES, -30, 36, 3), (BONES, 24, 56, 2)]),
    "ashheap": ("wall", ("lava",), "wild", 4,
                [(("FireGrate",), 0, 46, 1), (RUBBLE, -34, 26, 3), (ROCKS, 36, 30, 1), (BONES, 10, 72, 1)]),
    "frost": ("wall", ("ice",), "wild", 4,
              [(BIG_ROCKS, 0, 30, 1), (ROCKS, -32, 28, 1), (("IceCrack2", "IceCrack4", "IceCrack6"), 26, 64, 1),
               (BONES, 34, 34, 1)]),
    # in the open near buildings
    "wagon": ("open", (G, "ice", "swamp"), "built", 2,
              [(("OutdoorTraderCart",), 0, 0, 1), (CRATES, -56, 22, 1), (("TraderAppleCrate", "Barrel"), 50, 18, 1),
               (STRAW, -16, -46, 1)]),
    "chopping": ("open", (G, "swamp"), "built", 4,
                 [(STUMPS, 0, 0, 1), (LOGS, -40, 10, 1), (("ForestLog03",), 38, 16, 1), (("Barrel",), 20, -34, 1)]),
    "goods": ("open", (G, "ice", "swamp", "lava"), "built", 3,
              [(CRATES, -20, 0, 2), (BARRELS, -12, 26, 2), (("TraderAppleCrate",), 30, -22, 1)]),
    "drill": ("open", (G, "ice", "swamp", "lava"), "martial", 4,
              [(("TraderArmorRack1", "TraderArmorRack2"), 0, 0, 1), (("TraderArmorRack1", "TraderArmorRack2"), 32, 0, 1),
               (("TargetBarrel1", "TargetBarrel2"), 16, 46, 1), (("TraderQuiverRack",), -30, 10, 1)]),
    "miners": ("open", ("cave",), "built", 4,
               [(("MineOreCartBroken1", "MineOreCart1"), 0, 0, 1), (STEEL, -40, 20, 2), (("MiningPickAxeInGround1",), 30, 30, 1)]),
    # in the open away from buildings
    "glade_log": ("open", (G, "swamp"), "wild", 4,
                  [(LOGS, 0, 0, 1), (FUNGI, -24, 18, 2), (FERNS, 30, -14, 1)]),
    "glade_rock": ("open", (G, "swamp"), "wild", 4,
                   [(BIG_ROCKS, 0, 0, 1), (ROCKS, -26, 14, 2), (FERNS, 26, 16, 1), (("CaveRocksSmall",), 6, -30, 1)]),
    "stalagmites": ("open", ("cave",), "wild", 4,
                    [(("LargeStalagmite", "SmallStalagmite"), 0, 0, 1), (("SmallStalagmite",), -26, 18, 2),
                     (ROCKS, 24, -18, 1), (BONES, 30, 30, 1)]),
    "cinders": ("open", ("lava",), "wild", 4,
                [(("FireGrate",), 0, 0, 1), (ROCKS, -34, 14, 2), (BONES, 30, 24, 2), (RUBBLE, 0, -34, 1)]),
    "snowrock": ("open", ("ice",), "wild", 4,
                 [(BIG_ROCKS, 0, 0, 1), (ROCKS, -28, 14, 2), (("IceCrack2", "IceCrack4", "IceCrack6"), 30, 30, 1)]),
    "remains": ("open", ("cave", "lava", "ice", "swamp"), "wild", 2,
                [(BIG_ROCKS, 0, 0, 1), (BONES, -24, 20, 3), (("CaveRocksSmall",), 26, -16, 1)]),
}
# groups that read alike: a second of the family nearby is avoided
FAMILY = {"wagon": "cart", "cart": "cart", "orecart": "cart", "miners": "cart", "goods": "stores", "stores": "stores",
          "barrels": "stores", "minestores": "stores", "chopping": "wood", "woodpile": "wood", "drill": "arms",
          "armsrack": "arms", "glade_log": "log", "deadfall": "log", "snowrock": "rock", "glade_rock": "rock", "boulders": "rock",
          "frost": "rock", "remains": "bones", "bonepile": "bones", "cinders": "fire", "ashheap": "fire",
          "pillars": "pillar", "stalagmites": "pillar"}
# groups with tall or wide sprites, kept off the front walls (the SE and SW faces the camera looks over)
TALL = {"hay", "cart", "armsrack", "woodpile", "orecart", "pillars"}
# how fast a family's weight falls with each one placed anywhere (carts are memorable: a few to a map)
DECAY = {"cart": 1.0, "wood": 0.5, "stores": 0.4}
# which crate or rack of a pair lies along a wall that runs this way on screen (the wall's direction: "\\" or "/")
ALONG = {"\\": {"Crate1": "Crate1", "Crate2": "Crate1", "DarkCrate1": "DarkCrate1", "DarkCrate2": "DarkCrate1",
                "TraderPoleArm1": "TraderPoleArm1", "TraderPoleArm2": "TraderPoleArm2"},
         "/": {"Crate1": "Crate2", "Crate2": "Crate2", "DarkCrate1": "DarkCrate2", "DarkCrate2": "DarkCrate2",
               "TraderPoleArm1": "TraderPoleArm3", "TraderPoleArm2": "TraderPoleArm4"}}


class Exterior:
    def __init__(self, spec, land, biome="green", martial=False, seed=0, avoid=()):
        """biome: green, ice, lava, cave or swamp. martial: open ground near buildings is a garrison's (a castle's
        courtyard: weapon racks); walls of a town or curtain wall are martial anyway. avoid: squares to keep clear."""
        self.spec, self.land, self.biome, self.martial = spec, land, biome, martial
        self.rng = random.Random(zlib.crc32(f"{spec.d['name']}:exterior:{seed}".encode()))
        self.avoid = set(avoid)
        self.placed = collections.Counter()
        self.where = []                     # (kind, square) of each group

    # ---- the ground --------------------------------------------------------------------------------------------
    def _dilate(self, squares, r):
        return {(i + a, j + b) for i, j in squares for a in range(-r, r + 1) for b in range(-r, r + 1)}

    def _route_squares(self):
        """Squares on and beside the straight ways between waypoints: townsfolk and patrols walk them."""
        wps = self.spec.d.get("waypoints", [])
        out = set()
        pts = [(w["x"], w["y"]) for w in wps]
        for a in range(len(pts)):
            out |= self._dilate({px_square(*pts[a])}, 2)
            for b in range(a + 1, len(pts)):
                (x0, y0), (x1, y1) = pts[a], pts[b]
                d = math.hypot(x1 - x0, y1 - y0)
                if d > 24 * 32.5: continue
                n = max(1, int(d / 16))
                for k in range(n + 1):
                    out.add(px_square(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n))
        return self._dilate(out, 1)

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
                        buildings=self._dilate(strict, 1), lanes=self._dilate(lanes, 2), taken=L.taken - margin,
                        avoid=self.avoid, routes=self._route_squares())
        no = set().union(*self.why.values())
        self.props, self.colliders = [], []
        for o in spec.d["objects"]:
            t, x, y = o.get("type", "NPC"), o["x"], o["y"]        # a clone is a person
            cls = things().get(t, ("", "", ""))[0] if "type" in o else "MONSTER"
            if "DOOR" in cls or "Door" in t or "Gate" in t:
                no |= self._dilate({px_square(x, y)}, 3)
            elif re.match(r"PlayerStart|InvisibleExit|.*Exit", t) or "EXIT" in cls:
                no |= self._dilate({px_square(x, y)}, 4)
            elif "MONSTER" in cls or o.get("scr"):
                no |= self._dilate({px_square(x, y)}, 1)
            self.colliders.append((x, y))
            if not NOT_A_PROP.search(t): self.props.append((x, y))
        self.free = {s for s in L.squares if s not in no}
        # walkable squares, for the check that a group cuts nothing off
        wall_sq = {cell_square(*c) for c in spec.wallmap}
        self.walk = set(L.squares) - L.water - strict - wall_sq
        for o in spec.d["objects"]:
            if blocks(o.get("type", "")): self.walk.discard(px_square(o["x"], o["y"]))
        self.walls = spec.wallmap

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

    def _kind_of_wall(self, cell):
        mat = self.walls[cell]["material"]
        if NATURAL_WALL.search(mat) and not MASONRY_WALL.search(mat): return "wild"
        if MARTIAL_WALL.search(mat): return "martial"
        if MASONRY_WALL.search(mat): return "masonry"
        return "built"

    def _ok(self, t, x, y, mine):
        s = px_square(x, y)
        if s not in self.free or self._wall_near(x, y): return False
        if self._near(self.cgrid, x, y, 22): return False
        return not any((x - a) ** 2 + (y - b) ** 2 < 15 * 15 for a, b in mine)

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

    # ---- placing a group --------------------------------------------------------------------------------------
    def _choose(self, where, place, at, front=False):
        kinds, side = [], []
        for k, (w, biomes, pl, wt, _) in GROUPS.items():
            if w != where or self.biome not in biomes or (front and k in TALL): continue
            if pl == "martial" and place != "martial": continue
            if pl == "masonry" and place not in ("masonry", "martial"): continue
            if pl == "wild" and place != "wild": continue
            if pl == "built" and place == "wild": continue
            # spread the kinds: one of the family nearby makes a second there much less likely, and every one
            # placed anywhere a little less (a cart by the wall and a wagon in the open are both carts)
            fam = FAMILY.get(k, k)
            close = [abs(s[0] - at[0]) + abs(s[1] - at[1]) for k2, s in self.where if FAMILY.get(k2, k2) == fam]
            near = sum(1 for d in close if d < 36)
            seen = sum(1 for k2, _ in self.where if FAMILY.get(k2, k2) == fam)
            w = wt / (1 + 8 * near) / (1 + DECAY.get(fam, 0.3) * seen)
            # never two of a family side by side while another kind fits
            (side if any(d < 18 for d in close) else kinds).append((k, w))
        kinds = kinds or side
        if not kinds: return None
        return self.rng.choices([k for k, _ in kinds], [w for _, w in kinds])[0]

    def _place(self, kind, origin, n, tdir, line=None, extra=0):
        """Lay group `kind` from origin (px) with out-direction n and along-direction tdir (unit px vectors).
        Returns the objects laid, or None (nothing laid) when the anchor does not fit or it would cut a way."""
        spec, rng = self.spec, self.rng
        n0 = len(spec.d["objects"])
        mine, F, total = [], set(), 0
        for k, (types, along, out, count) in enumerate(GROUPS[kind][4]):
            t0 = types[0]
            for c in range(count):
                total += 1
                a = along + (27 if t0 in CRATES else 22) * c + rng.uniform(-3, 3)
                o = out + extra + rng.uniform(-3, 3)
                x, y = origin[0] + n[0] * o + tdir[0] * a, origin[1] + n[1] * o + tdir[1] * a
                t = rng.choice(types)
                if line: t = ALONG[line].get(t, t)
                if not self._ok(t, x, y, mine):
                    if k == 0 and c == 0: del spec.d["objects"][n0:]; return None
                    continue
                spec.obj_px(t, x, y)
                mine.append((x, y))
                if blocks(t): F.add(px_square(x, y))
        if len(mine) < max(2, total // 2) or self._cuts(F):
            del spec.d["objects"][n0:]
            return None
        self.walk -= F
        for p in mine:
            self.cgrid[(int(p[0] // 92), int(p[1] // 92))].append(p)
        return mine

    def _try(self, s):
        """A group at or near the empty square s: against the nearest wall within 3 squares, else in the open."""
        cx, cy = square_px(s[0] + 0.5, s[1] - 0.5)
        L = self.land
        near_bld = any(abs(s[0] - i) + abs(s[1] - j) < 14 for i, j in self._strict_sample(s))
        # the nearest square beside a wall
        best = None
        for a in range(-4, 5):
            for b in range(-4, 5):
                t = (s[0] + a, s[1] + b)
                if t not in self.free: continue
                x, y = square_px(t[0] + 0.5, t[1] - 0.5)
                w = self._nearest_wall(x, y, 2)
                if w is None: continue
                d = a * a + b * b
                if best is None or d < best[0]: best = (d, t, w)
        tries = []
        if best and self.rng.random() < 0.8:
            tries.append("wall")
        tries.append("open")
        if "wall" not in tries and best: tries.append("wall")
        for where in tries:
            if where == "wall":
                _, t, w = best
                place = self._kind_of_wall(w)
                wx, wy = (w[0] + 0.5) * CELL, (w[1] + 0.5) * CELL
                x, y = square_px(t[0] + 0.5, t[1] - 0.5)
                # out from the wall: snapped to a diagonal of the screen, as Nox's walls run
                dx, dy = x - wx, y - wy
                if abs(dx) < 4 and abs(dy) < 4: continue
                n = (math.copysign(1, dx) / math.sqrt(2), math.copysign(1, dy) / math.sqrt(2))
                # a wall below the group on screen is a front wall: the camera looks over it, so tall or wide
                # sprites (a hay heap, a cart, racks) would be drawn over its top; they keep to the back walls
                front = n[1] < 0
                kind = self._choose("wall", place, t, front=front)
                if not kind: continue
                tdir = (-n[1], n[0])
                line = "\\" if n[0] * n[1] < 0 else "/"
                if self._place(kind, (wx, wy), n, tdir, line, extra=12 if front else 0):
                    self.placed[kind] += 1; self.where.append((kind, t)); return True
            else:
                place = ("martial" if self.martial else "built") if near_bld else "wild"
                kind = self._choose("open", place, s)
                if not kind: continue
                ang = self.rng.choice((0.25, 0.75, 1.25, 1.75)) * math.pi
                n = (math.cos(ang), math.sin(ang))
                tdir = (-n[1], n[0])
                line = "\\" if n[0] * n[1] < 0 else "/"
                if self._place(kind, (cx, cy), n, tdir, line):
                    self.placed[kind] += 1; self.where.append((kind, s)); return True
        return False

    def _strict_sample(self, s):
        return self._strict_grid.get((s[0] // 14, s[1] // 14), ()) + tuple(
            p for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)
            for p in self._strict_grid.get((s[0] // 14 + a, s[1] // 14 + b), ()))

    # ---- the whole map ----------------------------------------------------------------------------------------
    def dress(self, reach=4.0, max_groups=400):
        """Fill the ground: while a free square lies more than `reach` cells from every prop, put a group there
        (the emptiest first). Returns {kind: count}. NOX_NODRESS=1 leaves the ground as it was (for comparisons)."""
        if os.environ.get("NOX_NODRESS"): return {}
        self._setup()
        sg = collections.defaultdict(list)
        for i, j in getattr(self.land, "taken_strict", ()): sg[(i // 14, j // 14)].append((i, j))
        self._strict_grid = {k: tuple(v) for k, v in sg.items()}
        self.cgrid = self._grid(self.colliders)
        pgrid = self._grid(self.props)
        R = reach * CELL
        lim = 2.5 * R

        def far(s):
            x, y = square_px(s[0] + 0.5, s[1] - 0.5)
            best = lim
            k = int(lim // 92) + 1
            for a in range(int(x // 92) - k, int(x // 92) + k + 1):
                for b in range(int(y // 92) - k, int(y // 92) + k + 1):
                    for p in pgrid.get((a, b), ()):
                        d = math.hypot(p[0] - x, p[1] - y)
                        if d < best: best = d
            return best
        dist = {s: far(s) for s in self.free}
        tried = set()
        groups = 0
        while groups < max_groups:
            cand = [(d, s) for s, d in dist.items() if d > R and s not in tried]
            if not cand: break
            d, s = max(cand, key=lambda c: (round(c[0], 1), c[1]))
            n0 = len(self.spec.d["objects"])
            if not self._try(s):
                tried.add(s); continue
            groups += 1
            new = [(o["x"], o["y"]) for o in self.spec.d["objects"][n0:]]
            for p in new: pgrid[(int(p[0] // 92), int(p[1] // 92))].append(p)
            for t in list(dist):
                if dist[t] <= R: continue
                x, y = square_px(t[0] + 0.5, t[1] - 0.5)
                for p in new:
                    dd = math.hypot(p[0] - x, p[1] - y)
                    if dd < dist[t]: dist[t] = dd
        return dict(self.placed)
