"""Vegetation planner: structured, not scattered (review/RUBRIC.md criterion 4).

What Westwood does (measured on Con03A, Con05A, Con08a, Wiz05A; review/design.py):
- Tree lines: nearly all trees stand 1-2 cells in front of the forest wall that bounds the land
  (Con03A: 219 of 233), several deep where the land is wide, so the edge reads as dense forest.
  Tree types match the wall: TreeForest with DecidiousWallGreen, TreePine with Coni-Wall1.
- Groves and clearings: a few single-species clumps stand in the open; roads, the village and the
  ground in front of doors stay clear.
- Undergrowth: Plant4, Plant5 and PlantForest1 dominate; they gather around trees and along the
  forest edge, in patches of one type (about half of small plants have a same-type nearest
  neighbour). Flowers grow in small single-type patches.

A map may have several forest sections (generator v3): forest_of(square) names the forest for each
part of the land, so each section has its own wall, trees, undergrowth and flowers.
Props spread from where they belong (scatter): density falls off with distance from their source
and they keep their spacing, so no kind of prop sits bunched in one spot and nowhere else.
"""
import collections, math
from kit.layout import SQ, N4, N8, square_px, px_square, bfs_distance

UNDERGROWTH = {"Plant4": 40, "Plant5": 20, "PlantForest1": 14, "Plant1": 7, "PlantBarren1": 5, "Plant2Flowered": 5, "Mushroom3": 6}
# Aspens (the yellow TreeForest13-17) read as a bright fringe when they stand right against the boundary wall: the first
# row before the wall takes few of them (2026-10-04 review: "use fewer aspen trees on the map edges").
ASPEN = ("TreeForest13", "TreeForest14", "TreeForest15", "TreeForest16", "TreeForest17")
EDGE_ASPEN_KEEP = 0.25

# Rock piles as Westwood heaps them outdoors (its 35 town and forest maps hold 582 clusters of 4 or more rocks within
# 50 px of each other): one big anchor (huge rocks, boulders or a rock pillar), large and medium rocks against it,
# small ones and pebbles round the rim. Each size by its share in those piles.
ROCK_PILE = {"anchor": {"CaveRocksHuge": 5, "CaveBoulders": 4, "CaveRockPillarTall1": 2, "CaveRockPillarTall2": 2,
                        "CaveRockPillarShort1": 2, "CaveRockPillarShort2": 1},
             "large": {"CaveRocksLarge": 3, "CaveRocksMedium": 2},
             "small": {"CaveRocksSmall": 3, "CaveRocksTiny": 1},
             "rim": {"CaveRocksPebbles": 4, "CaveRocksTiny": 1}}

# trees drawn in two parts, the trunk and its crown, stacked as Westwood stacks them (Con09a: the top 1 px right and
# 4-8 px down of its trunk)
TREE_TOPS = {"TreeSwampTrunk1": "TreeSwampTop1", "TreeSwampTrunk2": "TreeSwampTop2"}

FLOWERS = {"FlowersYellowSparse": 4, "FlowersPurpleSparse": 2, "FlowersWhiteSparse": 2, "FlowersBlueSparse": 1}

# How much grows in a town (Westwood's 17 town maps, per 100 floor tiles): 1.7 trees (p75 2.2), three quarters of them
# within 3 cells of the forest wall, the rest single trees in the open; 7.1 plants (Plant4, Plant5, Plant3, PlantForest1),
# half at the wall's foot and a quarter out in the open; 3.2 flowers and mushrooms, most 1.5-3 cells out from the wall.
# The forest wall is drawn as trees, so tree objects in a town are accents, not the forest (a forest map's planting
# gave the town lab 11.3 trees per 100 tiles).
TOWN_PLANTING = dict(depth=(0.16, 0.07, 0.02), per_tree=(0, 2), edge_p=0.2, open_p=0.03, flower_patches=(36, (4, 8)))

FORESTS = {
    "deciduous": dict(wall="DecidiousWallGreen",
                      trees={"TreeForest01": 42, "TreeForest03": 37, "TreeForest02": 33, "TreeForest04": 23,
                             "TreeForest05": 18, "TreeForest16": 10, "TreeForest08": 9, "TreeForest07": 8}),
    "conifer": dict(wall="Coni-Wall1",
                    trees={"TreePine06": 33, "TreePine10": 28, "TreePine09": 24, "TreePine08": 21, "TreePine05": 18,
                           "TreePine13": 12, "TreePine11": 11, "TreeForest15": 6}),
    # generator v3 sections
    "ancient": dict(wall="DecidiousWallBrown",
                    trees={"TreeForest01": 30, "TreeForest02": 30, "TreeForest03": 20, "TreeForest04": 16,
                           "TreeForest07": 12, "TreeForest08": 10, "TreeForest05": 8},
                    undergrowth={"Plant4": 30, "Plant5": 18, "PlantForest1": 16, "PlantForest2": 8, "FoliageDense1": 8,
                                 "FoliageDense2": 4, "Bush6": 4, "Mushroom3": 8, "Mushroom4": 4},
                    flowers={"FlowersWhiteSparse": 3, "FlowersPurpleSparse": 2, "FlowersBlueSparse": 1}),
    "silver": dict(wall="DecidiousWallGreen",
                   trees={"TreeGreen2": 4, "TreeGreen3": 4, "TreeGreen1": 1},
                   undergrowth={"FoliageSparse1": 10, "FoliageSparse2": 8, "Plant2": 6, "Mushroom3": 6, "Mushroom5": 4,
                                "PlantForest1": 6},
                   flowers={"FlowersBlueDense": 3, "FlowersBlueSparse": 3, "FlowersWhiteDense": 3, "FlowersWhiteSparse": 3,
                            "FlowersPurpleDense": 2}),
    "aspen": dict(wall="AspenSparse",
                  trees={"TreeForest13": 14, "TreeForest14": 14, "TreeForest15": 12, "TreeForest16": 12, "TreeForest17": 8,
                         "TreeOgre01": 4, "TreeOgre02": 4, "TreeOgre05": 4, "TreeOgre06": 3},
                  undergrowth={"PlantBarren1": 20, "PlantBarren2": 12, "Plant2Flowered": 10, "Plant2": 8, "Bush4": 4,
                               "GrassTuft3": 10, "GrassTuft2": 5, "Mushroom4": 4},
                  flowers={"FlowersYellowDense": 4, "FlowersYellowSparse": 5, "FlowersWhiteSparse": 1}),
    "pine": dict(wall="Coni-Wall1",
                 trees={"TreePine06": 30, "TreePine05": 18, "TreePine08": 18, "TreePine09": 14, "TreePine07": 10,
                        "TreePine03": 10, "TreePine01": 8, "TreePine02": 8},
                 undergrowth={"PlantFern1": 26, "PlantFern2": 12, "PlantFern3": 6, "PlantFern4": 6, "Bush10": 5, "Bush13": 5,
                              "Bush3": 4, "Mushroom1": 4, "Mushroom2": 4, "Mushroom5": 4, "CaveRocksSmall": 4},
                 flowers={"FlowersPurpleSparse": 2, "FlowersBlueSparse": 1}),
    "dusk": dict(wall="DecidiousWallRed",
                 trees={"TreeForest03": 14, "TreeForest04": 12, "TreeForest13": 8, "TreeForest14": 8, "TreeOgre03": 6,
                        "TreeOgre04": 5, "TreeForest06": 5},
                 undergrowth={"Plant4": 16, "Plant5": 10, "PlantBarren1": 10, "Plant3": 6, "GrassTuft3": 8, "Mushroom3": 4},
                 flowers={"FlowersYellowSparse": 2, "FlowersWhiteSparse": 2}),
    "camp": dict(wall="ManaMineWall",
                 trees={"TreeOgre03": 6, "TreeOgre04": 6, "TreeForest06": 4, "TreeForest05": 4},
                 undergrowth={"PlantBarren1": 14, "PlantBarren2": 6, "GrassTuft3": 10, "GrassTuft1": 6, "CaveRocksPebbles": 8,
                              "CaveRocksSmall": 4},
                 flowers={"FlowersWhiteSparse": 1}),
}


def _pick(rng, weights):
    names = list(weights); return rng.choices(names, [weights[n] for n in names])[0]


class Patches:
    """Patch field: points near each other get the same type (single-type clumps)."""

    def __init__(self, rng, land, weights, size=6.0, loyalty=0.8, squares=None):
        self.rng, self.weights, self.loyalty = rng, weights, loyalty
        sq = list(squares if squares is not None else land.squares) or list(land.squares)
        n = max(4, int(len(sq) / (size * size)))
        self.seeds = [(s[0] + rng.random(), s[1] - rng.random(), _pick(rng, weights)) for s in rng.sample(sq, min(n, len(sq)))]

    def type_at(self, si, sj):
        t = min(self.seeds, key=lambda s: (s[0] - si) ** 2 + (s[1] - sj) ** 2)[2]
        return t if self.rng.random() < self.loyalty else _pick(self.rng, self.weights)


class Planter:
    def __init__(self, spec, rng, land, forest="deciduous", keep_clear=(), forest_of=None, settled=()):
        """forest: the forest everywhere, or forest_of(square) -> key of FORESTS per square (sections).
        settled: area names that hold yards and buildings (no groves there)."""
        self.spec, self.rng, self.land = spec, rng, land
        self.forest_key = forest_of or (lambda s: forest)
        self.settled = tuple(settled) or ("village",)
        self.edge = land.edge_distance()
        # forest paths (passages without a road) stay walkable: trees lining both edges of a narrow path meet in the
        # middle and close it (Thornwick v0.2: the bandit camp cut off by its own tree line)
        lanes = set()
        for ln in getattr(land, "links", []):
            if ln.get("road"): continue
            for si, sj in ln["path"]:
                ci, cj = int(math.floor(si)), int(math.floor(sj)) + 1
                lanes |= {(ci + a, cj + b) for a in (-1, 0, 1) for b in (-1, 0, 1)}
        busy = set(land.roads) | land.plaza | land.water | land.taken | set(keep_clear) | (lanes & land.squares) |             set(getattr(land, "taken_strict", ()))                    # never a tree (or a biome's pillar) in a building
        self.road_d = bfs_distance(list(set(land.roads) | land.plaza), land.squares, 12)
        # every doorway and gate already standing, two squares round (Ambermere, 2026-10-05: a patch of flowers grew
        # in the west gate's opening, which the checker counts as a blocked doorway)
        for o in spec.d["objects"]:
            if o.get("door") is None: continue
            i0, j0 = px_square(o["x"], o["y"])
            busy |= {(i0 + a, j0 + b) for a in range(-2, 3) for b in range(-2, 3)}
        self.busy_d = bfs_distance(list(busy), land.squares, 12)
        self.water_d = bfs_distance(list(land.water), land.squares, 6)
        self.trees, self.small = [], []           # (si, sj)
        self._grid = {"tree": collections.defaultdict(list), "small": collections.defaultdict(list)}
        by_forest = collections.defaultdict(list)
        for s in land.squares: by_forest[self.forest_key(s)].append(s)
        self.tree_patches = {k: Patches(rng, land, FORESTS[k]["trees"], size=7, loyalty=0.75, squares=v) for k, v in by_forest.items()}
        self.plant_patches = {k: Patches(rng, land, FORESTS[k].get("undergrowth", UNDERGROWTH), size=5, loyalty=0.7, squares=v)
                              for k, v in by_forest.items()}

    # ---- helpers -----------------------------------------------------------------------------------
    def _free(self, si, sj, r, kind):
        g = self._grid[kind]
        bi, bj = int(si // 2), int(sj // 2)
        k = int(r // 2) + 1
        for a in range(bi - k, bi + k + 1):
            for b in range(bj - k, bj + k + 1):
                for (x, y) in g.get((a, b), ()):
                    if (si - x) ** 2 + (sj - y) ** 2 < r * r: return False
        return True

    def _square(self, si, sj):
        return int(math.floor(si)), int(math.floor(sj)) + 1

    def _forest(self, si, sj):
        return self.forest_key(self._square(si, sj)) or next(iter(self.tree_patches))

    def _tree_type(self, si, sj):
        return self.tree_patches[self._forest(si, sj)].type_at(si, sj)

    def _plant_type(self, si, sj):
        return self.plant_patches[self._forest(si, sj)].type_at(si, sj)

    def _ok_tree(self, si, sj):
        s = self._square(si, sj)
        if s not in self.land.squares: return False
        return self.busy_d.get(s, 99) >= 2 and self.water_d.get(s, 99) >= 1

    def _ok_small(self, si, sj):
        s = self._square(si, sj)
        return s in self.land.squares and self.busy_d.get(s, 99) >= 1 and self.water_d.get(s, 99) >= 1

    def _put(self, kind, t, si, sj):
        x, y = square_px(si, sj)
        self.spec.obj_px(t, x, y)
        if t in TREE_TOPS: self.spec.obj_px(TREE_TOPS[t], x + 1, y + 6)     # a swamp tree is a trunk and its top
        (self.trees if kind == "tree" else self.small).append((si, sj))
        self._grid[kind][(int(si // 2), int(sj // 2))].append((si, sj))

    # ---- planting ----------------------------------------------------------------------------------
    def tree_lines(self, depth=(0.85, 0.45, 0.12), spacing=1.15):
        """Trees in front of the forest wall: dense in the first row, thinning inward."""
        rows = sorted(self.edge.items(), key=lambda kv: kv[1])
        order = [s for s, d in rows if d <= len(depth)]
        self.rng.shuffle(order)
        for s in sorted(order, key=lambda s: self.edge[s]):
            p = depth[self.edge[s] - 1]
            if self.rng.random() > p: continue
            si, sj = s[0] + self.rng.uniform(0.15, 0.85), s[1] - self.rng.uniform(0.15, 0.85)
            if self._ok_tree(si, sj) and self._free(si, sj, spacing, "tree"):
                t = self._tree_type(si, sj)
                if self.edge[s] == 1 and t in ASPEN and self.rng.random() > EDGE_ASPEN_KEEP:
                    others = {k: w for k, w in FORESTS[self._forest(si, sj)]["trees"].items() if k not in ASPEN}
                    if not others: continue               # an aspen wood: thinner at the wall instead
                    t = _pick(self.rng, others)
                self._put("tree", t, si, sj)

    def groves(self, n=3, size=(6, 11), radius=3.0, spacing=1.2, avoid_areas=None):
        """A few single-species groves in open ground away from roads, buildings and the edge, and
        outside settled areas (a village has yards and gardens, not groves)."""
        avoid_areas = avoid_areas or self.settled

        def settled(s):
            for a in avoid_areas:
                ar = self.land.areas.get(a)
                if ar and math.hypot(s[0] - ar["c"][0], s[1] - ar["c"][1]) < ar["r"] * ar["stretch"] * 1.1: return True
            return False
        open_sq = [s for s in self.land.squares if self.edge.get(s, 0) >= 6 and self.busy_d.get(s, 99) >= 4 and not settled(s)]
        centres = []
        for _ in range(n * 20):
            if len(centres) >= n or not open_sq: break
            c = self.rng.choice(open_sq)
            if all(math.hypot(c[0] - a, c[1] - b) > 14 for a, b in centres): centres.append(c)
        for c in centres:
            species = _pick(self.rng, FORESTS[self._forest(c[0] + 0.5, c[1] - 0.5)]["trees"])
            want = self.rng.randint(*size)
            for _ in range(want * 8):
                if want <= 0: break
                si, sj = c[0] + self.rng.gauss(0, radius / 1.6), c[1] + self.rng.gauss(0, radius / 1.6)
                if self._ok_tree(si, sj) and self._free(si, sj, spacing, "tree"):
                    self._put("tree", species if self.rng.random() < 0.85 else self._tree_type(si, sj), si, sj)
                    want -= 1

    def waterside(self, p=0.35, spacing=1.3):
        """Trees down to the banks (Westwood's streams run between trees)."""
        for s, d in self.water_d.items():
            if d in (1, 2) and self.rng.random() < p * (1.0 if d == 1 else 0.5):
                si, sj = s[0] + self.rng.uniform(0.2, 0.8), s[1] - self.rng.uniform(0.2, 0.8)
                if self._ok_tree(si, sj) and self._free(si, sj, spacing, "tree"):
                    self._put("tree", self._tree_type(si, sj), si, sj)

    def undergrowth(self, per_tree=(0, 2), edge_p=0.14, spacing=0.5):
        """Plants around trees and along the forest edge, in single-type patches."""
        spots = []
        for (si, sj) in self.trees:
            for _ in range(self.rng.randint(*per_tree)):
                a, r = self.rng.uniform(0, 6.28), self.rng.uniform(0.6, 1.5)
                spots.append((si + r * math.cos(a), sj + r * math.sin(a)))
        for s, d in self.edge.items():
            if d <= 2 and self.rng.random() < edge_p * (1.0 if d == 1 else 0.5):
                spots.append((s[0] + self.rng.random(), s[1] - self.rng.random()))
        for si, sj in spots:
            if self._ok_small(si, sj) and self._free(si, sj, spacing, "small") and self._free(si, sj, 0.6, "tree"):
                self._put("small", self._plant_type(si, sj), si, sj)

    def flower_patches(self, n=6, size=(4, 9), near=None):
        """Small single-type flower patches beside roads and in clearings (near: squares to prefer)."""
        cand = list(near) if near else [s for s in self.land.squares if 2 <= self.road_d.get(s, 99) <= 4 and self.busy_d.get(s, 99) >= 1]
        for _ in range(n):
            if not cand: break
            c = self.rng.choice(cand)
            t = _pick(self.rng, FORESTS[self._forest(c[0] + 0.5, c[1] - 0.5)].get("flowers", FLOWERS))
            for _ in range(self.rng.randint(*size)):
                si, sj = c[0] + 0.5 + self.rng.gauss(0, 0.9), c[1] - 0.5 + self.rng.gauss(0, 0.9)
                if self._ok_small(si, sj) and self._free(si, sj, 0.35, "small"):
                    self._put("small", t, si, sj)

    def birds(self, n=8):
        sq = list(self.land.squares)
        for s in self.rng.sample(sq, min(n, len(sq))):
            x, y = square_px(s[0] + 0.5, s[1] - 0.5)
            self.spec.obj_px(self.rng.choice(["AmbBird1", "AmbBird2", "AmbCricket1"]), x, y)

    def meadow(self, p=0.03, spacing=1.5):
        """Single plants out in the open, away from the edge and from what is built (a quarter of a Westwood town's
        plants stand 6 cells or more from any wall)."""
        for s in sorted(self.land.squares):
            if self.edge.get(s, 0) < 4 or self.busy_d.get(s, 0) < 2 or self.rng.random() >= p: continue
            si, sj = s[0] + self.rng.random(), s[1] - self.rng.random()
            if self._ok_small(si, sj) and self._free(si, sj, spacing, "small") and self._free(si, sj, 0.6, "tree"):
                self._put("small", self._plant_type(si, sj), si, sj)

    def rock_piles(self, n, min_edge=1, max_edge=6, gap=12.0, avoid=()):
        """n heaps of rock in Westwood's manner (ROCK_PILE): an anchor, then large rocks against it, small ones and
        pebbles further out, about 1.5 squares across; on open ground near the forest wall (the edge distance in
        [min_edge, max_edge]), clear of roads, doors, water and what is built, `gap` squares apart (2026-10-04 review:
        "a concentrated pile of rocks here and there"). avoid: squares to keep clear too. Returns the pile centres."""
        avoid = set(avoid)
        cands = [s for s, d in self.edge.items() if min_edge <= d <= max_edge and self.busy_d.get(s, 99) >= 3
                 and self.water_d.get(s, 99) >= 2 and s not in avoid]
        self.rng.shuffle(cands)
        centres = []
        for s in cands:
            if len(centres) >= n: break
            if any((s[0] - a) ** 2 + (s[1] - b) ** 2 < gap * gap for a, b in centres): continue
            ci, cj = s[0] + 0.5, s[1] - 0.5
            if not self._free(ci, cj, 1.4, "tree"): continue
            centres.append(s)
            rings = [("anchor", 0.0, 1)] + [("large", 0.55, self.rng.randint(1, 3)), ("small", 0.95, self.rng.randint(2, 4)),
                                           ("rim", 1.35, self.rng.randint(3, 6))]
            a0 = self.rng.uniform(0, 2 * math.pi)
            for kind, r, k in rings:
                for q in range(k):
                    a = a0 + 2 * math.pi * (q + self.rng.uniform(-0.3, 0.3)) / max(1, k) + (0.6 if kind == "small" else 0)
                    rr = r * self.rng.uniform(0.75, 1.15)
                    si, sj = ci + rr * math.cos(a), cj + rr * math.sin(a)
                    if not self._ok_small(si, sj): continue
                    self._put("small", _pick(self.rng, ROCK_PILE[kind]), si, sj)
        return centres

    # small scenes of the forest floor, each a few pieces composed round one (2026-10-04 review: the exterior needs
    # more variety of objects): a fallen log grown with mushrooms, a stump with the log split from it, a boulder in
    # ferns; the pieces as Westwood strews them along its woods' edges (ForestLog, Stump, Mushroom, Plant*)
    VIGNETTES = {
        "fallen_log": [("ForestLog01|ForestLog02|ForestLog03|ForestLog04", 0.0, 1),
                       ("Mushroom1|Mushroom2|Mushroom3|Mushroom4|Mushroom5", 0.9, (2, 4)), ("PlantFern1|Plant4|Plant5", 1.2, (0, 2))],
        "stump": [("Stump1|Stump2|Stump9", 0.0, 1), ("ForestLog01|ForestLog03", 1.1, 1), ("Mushroom3|Mushroom4", 0.7, (1, 2))],
        "boulder": [("CaveRocksHuge|CaveBoulders", 0.0, 1), ("PlantFern1|PlantFern2|FoliageDense1|Plant4", 1.0, (2, 3)),
                    ("CaveRocksPebbles|CaveRocksSmall", 1.3, (1, 3))],
    }

    def forest_floor(self, n, kinds=("fallen_log", "stump", "boulder"), min_edge=2, max_edge=4, gap=9.0):
        """n vignettes of the forest floor (VIGNETTES) near the forest's edge, off roads, doors and what is built,
        `gap` squares apart. Returns their centres."""
        import re as _re
        cands = [s for s, d in self.edge.items() if min_edge <= d <= max_edge and self.busy_d.get(s, 99) >= 3
                 and self.water_d.get(s, 99) >= 2]
        self.rng.shuffle(cands)
        done = []
        for s in cands:
            if len(done) >= n: break
            if any((s[0] - a) ** 2 + (s[1] - b) ** 2 < gap * gap for a, b in done): continue
            ci, cj = s[0] + 0.5, s[1] - 0.5
            if not (self._free(ci, cj, 1.6, "tree") and self._free(ci, cj, 1.0, "small")): continue
            kind = kinds[len(done) % len(kinds)]
            a0 = self.rng.uniform(0, 2 * math.pi)
            for pat, r, k in self.VIGNETTES[kind]:
                types = pat.split("|")
                cnt = k if isinstance(k, int) else self.rng.randint(*k)
                for q in range(cnt):
                    a = a0 + 2 * math.pi * q / max(1, cnt) + self.rng.uniform(-0.4, 0.4)
                    si, sj = ci + r * math.cos(a), cj + r * math.sin(a)
                    if not self._ok_small(si, sj): continue
                    self._put("small", self.rng.choice(types), si, sj)
            done.append(s)
        return done

    def plant_all(self, groves=3, flowers=6, birds=8, profile=None):
        """Everything that grows. profile: a planting profile (TOWN_PLANTING) in place of the forest maps' density."""
        if profile:
            self.tree_lines(depth=profile["depth"])
            self.waterside()
            self.groves(groves)
            self.undergrowth(per_tree=profile["per_tree"], edge_p=profile["edge_p"])
            self.meadow(profile["open_p"])
            # flowers and mushrooms a little way out from the forest wall
            n, size = profile["flower_patches"]
            near = [s for s, d in self.edge.items() if 2 <= d <= 3 and self.busy_d.get(s, 0) >= 1]
            self.flower_patches(n, size, near=near)
        else:
            self.tree_lines()
            self.waterside()
            self.groves(groves)
            self.undergrowth()
            self.flower_patches(flowers)
        self.birds(birds)
        return len(self.trees), len(self.small)


def scatter(spec, rng, land, types, sources, n, reach=12.0, min_gap=3.0, ok=None, taken=None):
    """Props that belong somewhere, spread out from there: density falls off with distance from the
    sources (squares, e.g. the woodcutter's hut), out to `reach` squares, each keeping `min_gap`
    squares from the others, so they read as spread from their source rather than bunched in one
    spot. ok(square) filters places; taken collects the squares used. Returns the placed points."""
    placed, tries = [], 0
    names = list(types); weights = [types[t] for t in names]
    while len(placed) < n and tries < n * 60:
        tries += 1
        sx, sy = rng.choice(sources)
        d = reach * math.sqrt(rng.random())               # more near the source, fewer farther out
        a = rng.uniform(0, 2 * math.pi)
        si, sj = sx + 0.5 + d * math.cos(a), sy - 0.5 + d * math.sin(a)
        s = (int(math.floor(si)), int(math.floor(sj)) + 1)
        if s not in land.squares or (ok and not ok(s)): continue
        if any((si - x) ** 2 + (sj - y) ** 2 < min_gap * min_gap for x, y in placed): continue
        spec.obj_px(rng.choices(names, weights)[0], *square_px(si, sj))
        placed.append((si, sj))
        if taken is not None: taken.add(s)
    return placed
