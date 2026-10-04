"""Village dressing (generator v2): what fills the ground between Westwood's village buildings.

Measured on Con05A, Con08a, Con03A, Con07B and Con02a (outdoor ground):
- Gardens: rows of one crop (GardenCorn, GardenTomatos, GardenCabbage) on dirt or grass beside a
  building, fenced on some sides (IronFence in Con05A, town walls in Galava).
- Props against outer walls: barrels, water barrels, straw.
- Benches by the square, bushes in yards, pebbles and small rocks scattered on open ground.
"""
import math
from kit.layout import N4, square_tile, square_px, point_cell, bfs_distance, px_square
from kit.identity import SCENES

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
        # then anywhere along the four sides, a little further out (a bigger building fills its corners)
        more = [(i1 + d, j) for d in (3, 4, 5) for j in range(j0 - h, j1 + 2)] +                [(i0 - 1 - w - d + 1, j) for d in (2, 3, 4) for j in range(j0 - h, j1 + 2)] +                [(i, j1 + d) for d in (3, 4, 5) for i in range(i0 - w, i1 + 2)] +                [(i, j0 - 1 - h - d + 1) for d in (2, 3, 4) for i in range(i0 - w, i1 + 2)]
        rng.shuffle(more)
        cands += [c for c in more if c not in cands]
        # the squares the building's own margin took are free for its garden (never its walls or others')
        own = {(i + a, j + b) for i, j in foot for a in range(-2, 3) for b in range(-2, 3)} - foot
        clear = lambda s: self._clear(s) or (s in own and s in L.taken and s not in L.taken_strict and
                                             s in L.squares and s not in L.roads and s not in L.plaza and
                                             s not in L.water and s not in self.used)
        for gi, gj in cands:
            plot = {(gi + a, gj + b) for a in range(w) for b in range(h)}
            ring = {(gi + a, gj + b) for a in range(-1, w + 1) for b in range(-1, h + 1)}
            if not all(clear(s) for s in ring): continue
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
                if p == gap or not fence: continue
                x, y = point_cell(*p)
                if (x, y) not in self.spec.wallmap: self.spec.wall(x, y, fence)
            self.used |= ring
            L.taken |= ring
            return True
        return False

    def _entrance(self, building):
        """(door square, outward step, sideways step) of the building's main entrance."""
        foot = _squares_of(building.footprint)
        if not building.entrances: return None
        d = px_square(*building.entrances[0].px)
        outs = [(a, b) for a, b in N4 if (d[0] + a, d[1] + b) not in foot and (d[0] + a, d[1] + b) in self.land.squares]
        if not outs: return None
        ci = sum(i for i, _ in foot) / len(foot); cj = sum(j for _, j in foot) / len(foot)
        o = max(outs, key=lambda s: (d[0] + s[0] - ci) ** 2 + (d[1] + s[1] - cj) ** 2)
        return d, o, (o[1], o[0])

    def scene(self, building, name):
        """An outdoor prop group with a reason (kit/identity.py SCENES), placed where it belongs:
        beside the door, against a side wall away from the entrance, or in front of the entrance."""
        sc, L, rng = SCENES[name], self.land, self.rng
        ent = self._entrance(building)
        if not ent: return False
        (di, dj), (oi, oj), (pi, pj) = ent
        foot = _squares_of(building.footprint)
        doors = [px_square(*d.px) for r in building.rooms for d in r.doors] + [px_square(*d.px) for d in building.entrances]

        def free(s):
            if not (s in L.squares and s not in L.roads and s not in L.plaza and s not in L.water and
                    s not in self.used and s not in foot and s not in L.taken_strict): return False
            if any(abs(s[0] - d[0]) <= 3 and abs(s[1] - d[1]) <= 3 for d in doors): return False   # never at a door
            x, y = square_tile(*s)
            return not any((x + a, y + b) in self.spec.wallmap for a in (-1, 0, 1, 2) for b in (-1, 0, 1, 2))
        # one square of clearance from the wall: props stand beside it, never in it
        if sc["where"] == "door_side":
            spots = [(di + 2 * oi + pi * k, dj + 2 * oj + pj * k) for side in (1, -1) for k in (side * 2, side * 3)]
        elif sc["where"] == "front":
            spots = [(di + 3 * oi + pi * k, dj + 3 * oj + pj * k) for k in (2, -2, 3, -3)]
        else:   # side_wall: squares along an outside wall that does not hold the entrance
            ring1 = {(i + a, j + b) for i, j in foot for a, b in N4} - foot
            ring = {(i + a, j + b) for i, j in ring1 for a, b in N4} - foot - ring1
            spots = [s for s in ring if not any((s[0] - a, s[1] - b) in foot for a, b in [(oi, oj)]) and
                     abs((s[0] - di) * oi + (s[1] - dj) * oj) < 30 and (s[0] - di) * oi + (s[1] - dj) * oj <= 0]
            rng.shuffle(spots)
        spots = [s for s in spots if free(s)]
        if not spots: return False
        names = [t for t, w in sc["items"] for _ in range(w)]
        n = rng.randint(*sc["pieces"])
        s0 = spots[0]
        # a tight group: pieces side by side along the wall (or around the spot)
        along = (pi, pj) if sc["where"] != "side_wall" else next(((a, b) for a, b in N4 if
                                                                  ((s0[0] + a, s0[1] + b) in foot) is False and
                                                                  any((s0[0] + a + c, s0[1] + b + d) in foot for c, d in N4)), (pi, pj))
        for k in range(n):
            si = s0[0] + 0.5 + along[0] * 0.55 * k + rng.uniform(-0.1, 0.1)
            sj = s0[1] - 0.5 + along[1] * 0.55 * k + rng.uniform(-0.1, 0.1)
            if k and not free((int(si), int(sj) + 1)) and (int(si), int(sj) + 1) not in self.used: break
            self.spec.obj_px(rng.choice(names), *square_px(si, sj))
            self.used.add((int(si), int(sj) + 1))
        self.used.add(s0); L.taken.add(s0)
        return True

    # bench variant that faces each direction in uv (rules: room_types.chair_facing, "Bench")
    BENCH_FACING = {"+u": "Bench1", "-u": "Bench5", "+v": "Bench4", "-v": "Bench2"}

    def square_piece(self, centre, r_squares, pole=None, per_side=2):
        """The square as a composed set piece around its centre feature (a well):
        benches on the four sides facing the centre, `per_side` to a side, and four lights on the
        diagonals, all symmetric. `pole(si, sj)` places a light (e.g. a torch pole with its glow)."""
        ci, cj = centre
        d_bench = 0.68 * r_squares                     # benches inside the paving, facing in
        spread = (0.0,) if per_side == 1 else (-0.75, 0.75)
        for (du, dv), face in (((-1, 0), "+u"), ((1, 0), "-u"), ((0, -1), "+v"), ((0, 1), "-v")):
            for t in spread:
                si = ci + du * d_bench + (t if dv else 0)
                sj = cj + dv * d_bench + (t if du else 0)
                self.spec.obj_px(self.BENCH_FACING[face], *square_px(si, sj))
                self.used.add((int(si), int(sj) + 1))
        if pole:
            d_light = 0.5 * r_squares                  # on the diagonals, between the benches
            for du, dv in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                pole(ci + du * d_light, cj + dv * d_light)

    # Westwood's fountain squares (12 measured round their wells and fountains): potted plants in a ring close round
    # the fountain (median 2.5 cells; Plant4 at 10 of 12 squares, Plant5 at 7), blue flower beds just outside them
    # (2.5-3 cells), light benches facing in (4 cells), ornate street lamps at the edge (10-11 cells), each with its
    # shadow piece at a fixed offset, and bushes along the edge.
    LAMP_SHADOW = {"StreetLampOrnate1": ("StreetLampOrnate1Shadow", -15, 10),
                   "StreetLampOrnate3": ("StreetLampOrnate3Shadow", -15, 21),
                   "StreetLamp2": ("StreetLamp2Shadow", -23, 0)}

    def fountain_square(self, centre, r_squares, lamp="StreetLampOrnate3"):
        """A town square in Westwood's manner round a fountain (call it in place of a well and square_piece).
        r_squares: the paving's radius in squares (Land.paint_square takes uv units: half of them)."""
        import math
        ci, cj = centre
        rng = self.rng

        def put(t, si, sj):
            x, y = square_px(si, sj)
            self.spec.obj_px(t, x, y)
            self.used.add((int(si), int(sj) + 1))
            return x, y

        put("Fountain", ci, cj)
        r_pot = 1.35                                    # 2.7 cells: just round the basin
        for k in range(8):
            a = k * math.pi / 4 + math.pi / 8
            put("Plant4" if k % 2 else "Plant5", ci + r_pot * math.cos(a), cj + r_pot * math.sin(a))
        for k in range(4):                              # flower beds between the pots, on the axes
            a = k * math.pi / 2
            put(rng.choice(("FlowersBlueSparse", "FlowersBlueDense")), ci + 1.6 * math.cos(a), cj + 1.6 * math.sin(a))
        d_bench = max(2.2, 0.36 * r_squares)            # benches facing in, on the four sides
        for (du, dv), face in (((-1, 0), "+u"), ((1, 0), "-u"), ((0, -1), "+v"), ((0, 1), "-v")):
            put(self.BENCH_FACING[face], ci + du * d_bench, cj + dv * d_bench)
        d_lamp = 0.82 * r_squares / math.sqrt(2)        # lamps on the diagonals near the edge, with their shadows
        shadow, sx, sy = self.LAMP_SHADOW[lamp]
        for du, dv in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            x, y = put(lamp, ci + du * d_lamp, cj + dv * d_lamp)
            self.spec.obj_px(shadow, x + sx, y + sy)
        L = self.land
        for k in range(8):                              # bushes and flowers round the edge, between the streets, on
            a = k * math.pi / 4 + rng.uniform(-0.2, 0.2)          # the paving clear of the buildings and their doors
            si, sj = ci + 0.88 * r_squares * math.cos(a), cj + 0.88 * r_squares * math.sin(a)
            s_ = (int(si), int(sj) + 1)
            near = {(s_[0] + a_, s_[1] + b_) for a_ in (-2, -1, 0, 1, 2) for b_ in (-2, -1, 0, 1, 2)}
            if s_ in L.roads or near & L.taken_strict or near & L.taken or s_ in self.used: continue
            put(rng.choice(("Bush6", "Bush9", "Bush12", "FlowersPurpleDense", "FlowersYellowSparse")), si, sj)

    def ground_bits(self, per_100=4.0, max_edge=4):
        """Pebbles, small rocks and bushes where nature has them: toward the forest edge, never on
        roads, in yards or in front of doors."""
        L, rng = self.land, self.rng
        edge = L.edge_distance()
        free = [s for s in L.squares if self._clear(s) and edge.get(s, 99) <= max_edge]
        for s in rng.sample(free, min(len(free), int(len(L.squares) * per_100 / 100))):
            self.spec.obj_px(_pick(rng, GROUND_BITS), *square_px(s[0] + rng.random(), s[1] - rng.random()))


def _squares_of(tiles):
    """Squares of a building's floor tiles (Building.footprint holds tile coordinates)."""
    from kit.layout import tile_square
    return {tile_square(x, y) for x, y in tiles}
