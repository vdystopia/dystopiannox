"""Village dressing (generator v2): what fills the ground between Westwood's village buildings.

Measured on Con05A, Con08a, Con03A, Con07B and Con02a (outdoor ground):
- Gardens: rows of one crop (GardenCorn, GardenTomatos, GardenCabbage) on dirt or grass beside a
  building, fenced on some sides (IronFence in Con05A, town walls in Galava).
- Props against outer walls: barrels, water barrels, straw.
- Benches by the square, bushes in yards, pebbles and small rocks scattered on open ground.
"""
import math
from kit.layout import N4, square_tile, square_px, point_cell, bfs_distance

CROPS = ["GardenCorn", "GardenTomatos", "GardenCabbage"]
WALL_PROPS = {"Barrel2": 5, "WaterBarrel": 4, "Barrel": 3, "Straw2": 3, "Straw1": 2}
GROUND_BITS = {"CaveRocksPebbles": 6, "CaveRocksSmall": 4, "Bush6": 2, "Bush9": 1, "Bush11": 1, "FoliageDense1": 2}


def _pick(rng, w):
    k = list(w); return rng.choices(k, [w[x] for x in k])[0]


class Village:
    def __init__(self, spec, rng, land):
        self.spec, self.rng, self.land = spec, rng, land
        self.used = set()

    def _clear(self, s):
        L = self.land
        return s in L.squares and s not in L.roads and s not in L.plaza and s not in L.water and \
            s not in L.taken and s not in self.used

    def garden(self, building, size=(4, 3), crop=None, fence="IronFence"):
        """A fenced crop plot beside the building, on the side away from its entrance."""
        L, rng = self.land, self.rng
        foot = {L_sq for L_sq in _squares_of(building.footprint)}
        if not foot: return False
        i0, i1 = min(i for i, _ in foot), max(i for i, _ in foot)
        j0, j1 = min(j for _, j in foot), max(j for _, j in foot)
        w, h = size
        cands = [(i1 + 3, j0), (i1 + 3, j1 - h + 1), (i0 - 2 - w, j0), (i0 - 2 - w, j1 - h + 1),
                 (i0, j1 + 3), (i1 - w + 1, j1 + 3), (i0, j0 - 2 - h), (i1 - w + 1, j0 - 2 - h)]
        rng.shuffle(cands)
        for gi, gj in cands:
            plot = {(gi + a, gj + b) for a in range(w) for b in range(h)}
            ring = {(gi + a, gj + b) for a in range(-1, w + 1) for b in range(-1, h + 1)}
            if not all(self._clear(s) for s in ring): continue
            crop = crop or rng.choice(CROPS)
            for s in plot:
                self.spec.floor[square_tile(*s)] = "DirtDark2"
                for k in range(2):                              # two plants per tile, in rows
                    self.spec.obj_px(crop, *square_px(s[0] + 0.3 + 0.4 * k, s[1] - 0.5))
            # fence on the wall points around the plot, with a gap for the gardener
            pts = [(p, q) for p in range(gi, gi + w + 1) for q in range(gj - 1, gj + h)
                   if p in (gi, gi + w) or q in (gj - 1, gj + h - 1)]
            gap = rng.choice([p for p in pts if p[0] == gi + w // 2 or p[1] == gj - 1 + h // 2] or pts)
            for p in pts:
                if p == gap: continue
                x, y = point_cell(*p)
                if (x, y) not in self.spec.wallmap: self.spec.wall(x, y, fence)
            self.used |= ring
            L.taken |= ring
            return True
        return False

    def wall_props(self, building, n=(1, 3)):
        """Barrels, water barrels and straw against the building's outside walls."""
        L, rng = self.land, self.rng
        foot = _squares_of(building.footprint)
        outside = [s for s in {(i + a, j + b) for i, j in foot for a, b in N4} - foot
                   if s in L.squares and s not in L.roads and s not in L.plaza and s not in L.water and s not in self.used]
        door_sq = set()
        for d in building.entrances:
            from kit.layout import px_square
            di, dj = px_square(*d.px)
            door_sq |= {(di + a, dj + b) for a in range(-2, 3) for b in range(-2, 3)}
        outside = [s for s in outside if s not in door_sq]
        rng.shuffle(outside)
        k = rng.randint(*n)
        for s in outside[:k]:
            t = _pick(rng, WALL_PROPS)
            for c in range(rng.randint(1, 2)):
                self.spec.obj_px(t, *square_px(s[0] + 0.3 + 0.35 * c, s[1] - 0.5 + rng.uniform(-0.15, 0.15)))
            self.used.add(s); L.taken.add(s)

    def benches(self, area, n=2):
        """Benches facing the square."""
        L, rng = self.land, self.rng
        edge = [s for s in {(i + a, j + b) for i, j in L.plaza for a, b in N4} - L.plaza if self._clear(s)]
        rng.shuffle(edge)
        for s in edge[:n]:
            self.spec.obj_px("Bench4", *square_px(s[0] + 0.5, s[1] - 0.5))
            self.used.add(s); L.taken.add(s)

    def ground_bits(self, per_100=4.0):
        """Pebbles, small rocks and bushes on open ground (not on roads, never blocking doors)."""
        L, rng = self.land, self.rng
        free = [s for s in L.squares if self._clear(s)]
        for s in rng.sample(free, min(len(free), int(len(L.squares) * per_100 / 100))):
            self.spec.obj_px(_pick(rng, GROUND_BITS), *square_px(s[0] + rng.random(), s[1] - rng.random()))


def _squares_of(cells):
    from kit.layout import cell_square
    return {cell_square(x, y) for x, y in cells}
