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

    def garden(self, building, size=(4, 3), crop=None, fence="auto"):
        """A household's vegetable garden beside the building, on the side away from its entrance, laid as Westwood
        lays its gardens (the scene lab, review/scenelab: Con05A, Con07B, Con09a, Wiz01A, Wiz03b): two or three beds
        side by side (on grass, or dug earth now and then), a different crop in each (corn, tomatoes, cabbage), two rows to a bed, the plants about
        20 px apart; a strip of grass between the beds to walk; the water barrel at a path's end, now and then a spade
        left in the ground; most unfenced, a few behind a low wooden fence (Dilapidated, Wiz01A's) with a gap for the gardener. Every plant stands
        clear of a fence's line (Ambermere playtest, 2026-10-05: "the northeast stretch of fence overlaps with the row
        of crops"). crop: one crop for every bed (a flower bed); fence: "auto" (a wooden fence now and then), a fence
        material, or None."""
        sizes, (w, h) = [], size
        if crop is None: sizes.append((w + 1, h + 1))   # Westwood's gardens run larger: a size up first, where it fits
        while True:
            sizes.append((w, h))
            if w * h <= 6: break
            w, h = (max(3, w - 1), max(2, h - 1)) if w >= h else (max(2, w - 1), max(3, h - 1))
        # each size with two squares of open land round it first (no crop against the wood's edge or in a pond: the
        # blind judge, 2026-10-05, "rows running into the pine edge, corn touching the tree line"), then with one; the
        # two largest sizes before any smaller one
        tries = [(s_, True) for s_ in sizes[:2]] + [(s_, False) for s_ in sizes[:2]]
        for s_ in sizes[2:]: tries += [(s_, True), (s_, False)]
        for s_, wide in tries:
            if self._garden_at(building, s_, crop, fence, wide): return True
        return False

    def _garden_at(self, building, size, crop, fence, wide):
        """One try of garden() at one size: True if laid."""
        import zlib, random as _random
        L = self.land
        foot = {L_sq for L_sq in _squares_of(building.footprint)}
        if not foot: return False
        i0, i1 = min(i for i, _ in foot), max(i for i, _ in foot)
        j0, j1 = min(j for _, j in foot), max(j for _, j in foot)
        w, h = size
        # the garden's own generator (the map, the house, the size): tuning a garden never shifts the rest of the map
        rng = _random.Random(zlib.crc32(f"{self.spec.d['name']}:garden-site:{i0},{j0}:{w}x{h}:{wide}".encode()))
        cands = [(i1 + 3, j0), (i1 + 3, j1 - h + 1), (i0 - 2 - w, j0), (i0 - 2 - w, j1 - h + 1),
                 (i0, j1 + 3), (i1 - w + 1, j1 + 3), (i0, j0 - 2 - h), (i1 - w + 1, j0 - 2 - h)]
        rng.shuffle(cands)

        # then anywhere along the four sides, a little further out (a bigger building fills its corners)
        more = [(i1 + d, j) for d in (3, 4, 5) for j in range(j0 - h, j1 + 2)] + \
               [(i0 - 1 - w - d + 1, j) for d in (2, 3, 4) for j in range(j0 - h, j1 + 2)] + \
               [(i, j1 + d) for d in (3, 4, 5) for i in range(i0 - w, i1 + 2)] + \
               [(i, j0 - 1 - h - d + 1) for d in (2, 3, 4) for i in range(i0 - w, i1 + 2)]
        rng.shuffle(more)
        cands += [c for c in more if c not in cands]
        # the squares the building's own margin took are free for its garden (never its walls or others')
        own = {(i + a, j + b) for i, j in foot for a in range(-2, 3) for b in range(-2, 3)} - foot
        clear = lambda s: self._clear(s) or (s in own and s in L.taken and s not in L.taken_strict and
                                             s in L.squares and s not in L.roads and s not in L.plaza and
                                             s not in L.water and s not in self.used)
        # two passes: first with two squares of open land round the beds (no crop against the wood's edge or in a
        # pond: the blind judge, 2026-10-05, "rows running into the pine edge, corn touching the tree line"), then
        # without, as before
        for gi, gj in cands:
            plot = {(gi + a, gj + b) for a in range(w) for b in range(h)}
            ring = {(gi + a, gj + b) for a in range(-1, w + 1) for b in range(-1, h + 1)}
            if not all(clear(s) for s in ring): continue
            ring2 = {(gi + a, gj + b) for a in range(-2, w + 2) for b in range(-2, h + 2)} - ring
            if wide and not all((s_ in L.squares and s_ not in L.water) or s_ in foot for s_ in ring2): continue
            if not wide: L.taken |= {s_ for s_ in ring2 if s_ in L.squares}     # the planting keeps two squares off
            one = crop
            crop = crop or rng.choice(CROPS)
            pts = [(p, q) for p in range(gi, gi + w + 1) for q in range(gj - 1, gj + h)
                   if p in (gi, gi + w) or q in (gj - 1, gj + h - 1)]
            gap = rng.choice([p for p in pts if p[0] == gi + w // 2 or p[1] == gj - 1 + h // 2] or pts)
            own_rng = _random.Random(zlib.crc32(f"{self.spec.d['name']}:garden:{gi},{gj}".encode()))
            if fence == "auto": fence = "DilapidatedShort" if own_rng.random() < 0.3 else None    # Wiz03b's low fence
            if fence and w * h < 20: fence = None          # (a little bed is never penned: its rows lost to the fence)
            from kit.spacing import off_walls
            fence_cells = {point_cell(p, q) for p, q in pts} if fence else set()
            walls = dict(self.spec.wallmap); walls.update({c: {} for c in fence_cells})
            # the beds: every other row of squares across the plot's short side, a strip of grass between; the plants
            # in two rows along each bed (the fence's points (p, q) are drawn at square coordinates (p, q - 0.5), so
            # the fenced ground runs gi..gi + w across i and gj - 1.5..gj + h - 1.5 across j: kit/yards Yard.centre)
            long_i = w >= h
            n_long, n_short = (w, h) if long_i else (h, w)
            beds = list(range(0, n_short, 2)) if n_short > 2 else list(range(n_short))     # narrow: a row to a bed
            rows = (0.3, 0.7) if n_short > 2 else (0.5,)
            dug = own_rng.random() < 0.4              # Westwood's beds are dug earth now and then, mostly grass
            kinds = [one] * len(beds) if one else ([crop] + own_rng.sample([c for c in CROPS if c != crop], 2))[:len(beds)]
            laid = 0
            for k, kind in zip(beds, kinds):
                for s_ in range(n_long if dug else 0):
                    sq = (gi + s_, gj + k) if long_i else (gi + k, gj + s_)
                    self.spec.floor[square_tile(*sq)] = "DirtDark2"
                start, end = 0.42, n_long - 0.42
                n = max(2, int((end - start) / 0.62) + 1)
                for row in rows:
                    for q in range(n):
                        a = start + (end - start) * q / (n - 1) + own_rng.uniform(-0.04, 0.04)
                        si, sj = (gi + a, gj - 1.5 + k + row) if long_i else (gi + k + row, gj - 1.5 + a)
                        x, y = square_px(si, sj)
                        if not fence or off_walls(walls, kind, x, y, margin=6):
                            self.spec.obj_px(kind, x, y); laid += 1
            # the water barrel at a path's end, a spade left in the ground at the other
            path = beds[0] + 1 if n_short > 2 else None
            if path is not None and path < n_short:
                ends = [(0.35, "WaterBarrel", 0.85), (n_long - 0.35, "MiningShovelInGround", 0.5)]
                if own_rng.random() < 0.5: ends = [(n_long - 0.35, "WaterBarrel", 0.85), (0.35, "MiningShovelInGround", 0.5)]
                for a, t, p in ends:
                    if own_rng.random() >= p: continue
                    si, sj = (gi + a, gj - 1.5 + path + 0.5) if long_i else (gi + path + 0.5, gj - 1.5 + a)
                    x, y = square_px(si, sj)
                    if not fence or off_walls(walls, t, x, y, margin=6): self.spec.obj_px(t, x, y)
            elif own_rng.random() < 0.85:              # a narrow plot: the barrel beside the bed's end, off the rows
                si, sj = (gi + n_long + 0.35, gj - 1.5 + n_short / 2) if long_i else (gi + n_short / 2, gj - 1.5 + n_long + 0.35)
                x, y = square_px(si, sj)
                if not fence: self.spec.obj_px("WaterBarrel", x, y)
            # the household round it (Westwood's gardens come with a crate of the crop, sacks, barrels: Con05A, Con09a):
            # a crate, a barrel or a sack on the long side now and then (flowers beyond a bed's end stood where a
            # townsman's walk stops to tend it: Ambermere, routes.facing)
            if own_rng.random() < 0.35 and not fence:
                u_ = n_long * own_rng.uniform(0.35, 0.65)                  # mid-way along a long side, off the ends
                si, sj = (gi + u_, gj - 1.5 - 0.45) if long_i else (gi - 0.45, gj - 1.5 + u_)
                self.spec.obj_px(own_rng.choice(("TraderAppleCrate", "Barrel", "SackChestLarge1")), *square_px(si, sj))
            if fence:                                # a low fence round it, a gap for the gardener
                for p in pts:
                    if p == gap: continue
                    x, y = point_cell(*p)
                    if (x, y) not in self.spec.wallmap: self.spec.wall(x, y, fence)
            self.used |= ring
            L.taken |= ring
            return laid > 0
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

    # what a business's sign reads, by building role: keys of the game's text file (nox.csf) that fit any town
    SIGN_TEXT = {"inn": "War03b:TavernSign",          # "Tavern"
                 "store": "War02a.scr:Sign3",         # "General Store"
                 "smithy": "War02a.scr:Sign1",        # "Blacksmith Shop"
                 "foreman": "Con03C.scr:Sign3",       # "Foreman"
                 "bunkhouse": "Con03C.scr:Sign2"}     # "Miner's Lodge"

    def scene(self, building, name, role=None):
        """An outdoor prop group with a reason (kit/identity.py SCENES), placed where it belongs:
        beside the door, against a side wall away from the entrance, or in front of the entrance. A sign reads what
        the building is (SIGN_TEXT, by its `role`)."""
        sc, L, rng = SCENES[name], self.land, self.rng
        ent = self._entrance(building)
        if not ent: return False
        (di, dj), (oi, oj), (pi, pj) = ent
        foot = _squares_of(building.footprint)
        doors = [px_square(*d.px) for r in building.rooms for d in r.doors] + [px_square(*d.px) for d in building.entrances]

        def free(s):
            if not (s in L.squares and s not in L.roads and s not in L.plaza and s not in L.water and
                    s not in self.used and s not in foot and s not in L.taken_strict): return False
            # never in a doorway: the lane in front of the entrance (a square either side of it, four out) stays
            # clear, and a square round every other door; beside the door is where a sign or a barrel stands (a
            # three-square box round each door had ruled out every spot beside one: no sign was ever placed)
            a_, o_ = (s[0] - di) * pi + (s[1] - dj) * pj, (s[0] - di) * oi + (s[1] - dj) * oj
            if abs(a_) <= 1 and -1 <= o_ <= 4: return False
            if any(abs(s[0] - d[0]) <= 1 and abs(s[1] - d[1]) <= 1 for d in doors): return False
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
        # each piece its Westwood gap after the one before (kit/spacing; Starwell playtest, 2026-10-05: "Many object
        # clusters like these crates are simply too close to each other"): they had stood 0.55 squares (18 px) apart
        # (the step is the widest gap the next piece may need, so the generator's draws stay as they were)
        from kit.spacing import gap as _gap
        off, prev = 0.0, None
        for k in range(n):
            if prev: off += (max([_gap(prev, x) for x in names] + [20.0]) + 3) / 32.5
            si = s0[0] + 0.5 + along[0] * off + rng.uniform(-0.05, 0.05)
            sj = s0[1] - 0.5 + along[1] * off + rng.uniform(-0.05, 0.05)
            if k and not free((int(si), int(sj) + 1)) and (int(si), int(sj) + 1) not in self.used: break
            qx, qy = square_px(si, sj)                  # never into any doorway (a woodpile's log had run into one)
            if k and any(abs(o["x"] - qx) < 56 and abs(o["y"] - qy) < 56 and math.hypot(o["x"] - qx, o["y"] - qy) < 56
                         for o in self.spec.d["objects"] if "Door" in (o.get("type") or "")): break
            t = rng.choice(names)
            prev = t
            text = self.SIGN_TEXT.get(role) if name == "sign" else None
            self.spec.obj_px(t, *square_px(si, sj), **({"xfer": {"Text": text}} if text else {}))
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
        from kit.spacing import wall_clearance
        for s in rng.sample(free, min(len(free), int(len(L.squares) * per_100 / 100))):
            t, x, y = _pick(rng, GROUND_BITS), *square_px(s[0] + rng.random(), s[1] - rng.random())
            if wall_clearance(self.spec.wallmap, x, y, reach=2) >= 16:     # never on a wall's line (a bush in a curtain)
                self.spec.obj_px(t, x, y)


def _squares_of(tiles):
    """Squares of a building's floor tiles (Building.footprint holds tile coordinates)."""
    from kit.layout import tile_square
    return {tile_square(x, y) for x, y in tiles}
