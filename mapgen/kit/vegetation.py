"""Vegetation planner (generator v2): structured, not scattered (review/RUBRIC.md criterion 4).

What Westwood does (measured on Con03A, Con05A, Con08a, Wiz05A; review/design.py):
- Tree lines: nearly all trees stand 1-2 cells in front of the forest wall that bounds the land
  (Con03A: 219 of 233), several deep where the land is wide, so the edge reads as dense forest.
  Tree types match the wall: TreeForest with DecidiousWallGreen, TreePine with Coni-Wall1.
- Groves and clearings: a few single-species clumps stand in the open; roads, the village and the
  ground in front of doors stay clear.
- Undergrowth: Plant4, Plant5 and PlantForest1 dominate; they gather around trees and along the
  forest edge, in patches of one type (about half of small plants have a same-type nearest
  neighbour). Flowers grow in small single-type patches.
"""
import math
from kit.layout import SQ, N4, N8, square_px, bfs_distance

FORESTS = {
    "deciduous": dict(wall="DecidiousWallGreen",
                      trees={"TreeForest01": 42, "TreeForest03": 37, "TreeForest02": 33, "TreeForest04": 23,
                             "TreeForest05": 18, "TreeForest16": 10, "TreeForest08": 9, "TreeForest07": 8}),
    "conifer": dict(wall="Coni-Wall1",
                    trees={"TreePine06": 33, "TreePine10": 28, "TreePine09": 24, "TreePine08": 21, "TreePine05": 18,
                           "TreePine13": 12, "TreePine11": 11, "TreeForest15": 6}),
}
UNDERGROWTH = {"Plant4": 40, "Plant5": 20, "PlantForest1": 14, "Plant1": 7, "PlantBarren1": 5, "Plant2Flowered": 5, "Mushroom3": 6}
FLOWERS = {"FlowersYellowSparse": 4, "FlowersPurpleSparse": 2, "FlowersWhiteSparse": 2, "FlowersBlueSparse": 1}


def _pick(rng, weights):
    names = list(weights); return rng.choices(names, [weights[n] for n in names])[0]


class Patches:
    """Patch field: points near each other get the same type (single-type clumps)."""

    def __init__(self, rng, land, weights, size=6.0, loyalty=0.8):
        self.rng, self.weights, self.loyalty = rng, weights, loyalty
        sq = list(land.squares)
        n = max(4, int(len(sq) / (size * size)))
        self.seeds = [(s[0] + rng.random(), s[1] - rng.random(), _pick(rng, weights)) for s in rng.sample(sq, min(n, len(sq)))]

    def type_at(self, si, sj):
        t = min(self.seeds, key=lambda s: (s[0] - si) ** 2 + (s[1] - sj) ** 2)[2]
        return t if self.rng.random() < self.loyalty else _pick(self.rng, self.weights)


class Planter:
    def __init__(self, spec, rng, land, forest="deciduous", keep_clear=()):
        self.spec, self.rng, self.land = spec, rng, land
        self.forest = FORESTS[forest]
        self.edge = land.edge_distance()
        busy = set(land.roads) | land.plaza | land.water | land.taken | set(keep_clear)
        self.road_d = bfs_distance(list(set(land.roads) | land.plaza), land.squares, 12)
        self.busy_d = bfs_distance(list(busy), land.squares, 12)
        self.water_d = bfs_distance(list(land.water), land.squares, 6)
        self.trees, self.small = [], []           # (si, sj)
        self.tree_patches = Patches(rng, land, self.forest["trees"], size=7, loyalty=0.75)
        self.plant_patches = Patches(rng, land, UNDERGROWTH, size=5, loyalty=0.7)

    # ---- helpers -----------------------------------------------------------------------------------
    def _free(self, si, sj, r, pts):
        return all((si - a) ** 2 + (sj - b) ** 2 >= r * r for a, b in pts)

    def _square(self, si, sj):
        return int(math.floor(si)), int(math.floor(sj)) + 1

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
        (self.trees if kind == "tree" else self.small).append((si, sj))

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
            if self._ok_tree(si, sj) and self._free(si, sj, spacing, self.trees):
                self._put("tree", self.tree_patches.type_at(si, sj), si, sj)

    def groves(self, n=3, size=(6, 11), radius=3.0, spacing=1.2, avoid_areas=("village",)):
        """A few single-species groves in open ground away from roads, buildings and the edge, and
        outside settled areas (a village has yards and gardens, not groves)."""
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
            species = _pick(self.rng, self.forest["trees"])
            want = self.rng.randint(*size)
            for _ in range(want * 8):
                if want <= 0: break
                si, sj = c[0] + self.rng.gauss(0, radius / 1.6), c[1] + self.rng.gauss(0, radius / 1.6)
                if self._ok_tree(si, sj) and self._free(si, sj, spacing, self.trees):
                    self._put("tree", species if self.rng.random() < 0.85 else self.tree_patches.type_at(si, sj), si, sj)
                    want -= 1

    def waterside(self, p=0.35, spacing=1.3):
        """Trees down to the banks (Westwood's streams run between trees)."""
        for s, d in self.water_d.items():
            if d in (1, 2) and self.rng.random() < p * (1.0 if d == 1 else 0.5):
                si, sj = s[0] + self.rng.uniform(0.2, 0.8), s[1] - self.rng.uniform(0.2, 0.8)
                if self._ok_tree(si, sj) and self._free(si, sj, spacing, self.trees):
                    self._put("tree", self.tree_patches.type_at(si, sj), si, sj)

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
            if self._ok_small(si, sj) and self._free(si, sj, spacing, self.small) and self._free(si, sj, 0.6, self.trees):
                self._put("small", self.plant_patches.type_at(si, sj), si, sj)

    def flower_patches(self, n=6, size=(4, 9)):
        """Small single-type flower patches beside roads and in clearings."""
        cand = [s for s in self.land.squares if 2 <= self.road_d.get(s, 99) <= 4 and self.busy_d.get(s, 99) >= 1]
        for _ in range(n):
            if not cand: break
            c = self.rng.choice(cand)
            t = _pick(self.rng, FLOWERS)
            for _ in range(self.rng.randint(*size)):
                si, sj = c[0] + 0.5 + self.rng.gauss(0, 0.9), c[1] - 0.5 + self.rng.gauss(0, 0.9)
                if self._ok_small(si, sj) and self._free(si, sj, 0.35, self.small):
                    self._put("small", t, si, sj)

    def birds(self, n=8):
        sq = list(self.land.squares)
        for s in self.rng.sample(sq, min(n, len(sq))):
            x, y = square_px(s[0] + 0.5, s[1] - 0.5)
            self.spec.obj_px(self.rng.choice(["AmbBird1", "AmbBird2", "AmbCricket1"]), x, y)

    def plant_all(self, groves=3):
        self.tree_lines()
        self.waterside()
        self.groves(groves)
        self.undergrowth()
        self.flower_patches()
        self.birds()
        return len(self.trees), len(self.small)
