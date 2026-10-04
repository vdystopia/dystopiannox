"""Biomes beyond the green world: caves, snow and ice, lava (rules/BIOMES.md, measured by rules/biomes.py and
rules/biome_places.py on Westwood's maps).

Each biome is a palette:
- its floors, with the patches that break them up and how they blend;
- its natural wall;
- what stands along the walls and in the open (Planter "forests": pillars or snow trees);
- what lies on its liquid (lava's flames and bubbles);
- its lights, ambient and region colours;
- its creatures.

A Dresser applies the palette to a carved Land:
    d = Dresser(spec, rng, land, "cave")
    d.reserve_pool(centre_uv, radius_uv)      # before land.carve(): liquid behind cliffs (lava, an underground lake)
    land.carve(...); land.apply(spec, wall=d.wall, floor=d.base)
    d.ground(); d.paint_pools(); d.vegetate(); d.dress_liquid(); d.scatter_open(); d.rim(); d.lights()
Densities are per 100 floor tiles of the context (open floor, along walls, on the liquid), as Westwood's.
"""
import math, random
from kit.layout import square_tile, square_px, bfs_distance, tile_square, N4
from kit.vegetation import FORESTS, Planter, Patches

N8 = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]

# ---- the palettes ------------------------------------------------------------------------------------------------
BIOMES = {
    "cave": dict(
        env="cave", ambient=(29, 34, 45), region_ambient=(32, 48, 48),
        wall="CaveWall2", base="CaveHardBrown",
        patches=[("CaveHardTan", 0.95), ("CaveHardDark", -1.15), ("DirtDark2", 1.55)],
        blends=[("CaveHardBrown", 0, "BlendEdge"), ("CaveHardDark", 1, "BlendEdge"), ("CaveHardTan", 2, "BlendEdge"),
                ("DirtDark2", 3, "DirtRidge"), ("ManaMineDirt", 4, "DirtRidge"), ("Water", 6, "DirtRidge")],
        forest=dict(wall="CaveWall2",
                    trees={"CaveRockPillarShort1": 30, "CaveRockPillarShort2": 26, "CaveRockPillarTall1": 26,
                           "CaveRockPillarTall2": 20, "LargeStalagmite": 5, "SmallStalagmite": 5},
                    undergrowth={"Mushroom3": 40, "CaveRocksPebbles": 22, "Mushroom1": 8, "Mushroom4": 6, "Mushroom5": 6,
                                 "Mushroom2": 6, "CaveRocksSmall": 8, "CaveRocksTiny": 5},
                    flowers={"Mushroom3": 3, "Mushroom5": 2, "Mushroom1": 2}),
        tree_depth=(0.75, 0.25, 0.05),
        open={"CaveRocksMedium": 1.0, "CaveRocksSmall": 0.7, "CaveRocksHuge": 0.45, "CaveBoulders": 0.4, "LegBone": 0.9,
              "ArmBone": 0.45, "Skull": 0.4, "SmallStalagmite": 0.28, "LargeStalagmite": 0.24, "CaveRocksLarge": 0.27},
        wallside={"SpiderWebNorthEast": 0.7, "SpiderWebEast": 0.65, "SpiderWebNorth": 0.7, "CaveRocksHuge": 0.9,
                  "CaveBoulders": 0.9, "CaveRocksLarge": 0.38, "Straw2": 0.3},
        liquid=dict(floor="Water", dress={}, edge=None),
        light_colours=[(128, 96, 32), (96, 64, 32), (96, 96, 64), (128, 96, 64)], light_per100=dict(open=3.0, wall=2.2),
        light_radius=150, light_intensity=40,
        sources=dict(wall={"TorchPole": 0.35}, open={"DunMirFlameBasinLit": 0.3}),
        creatures={"Bat": 6, "Spider": 2, "SmallSpider": 2, "Scorpion": 3, "GiantLeech": 1, "Urchin": 2},
        creatures_per100=1.0),
    "ice": dict(
        env="ice", ambient=(70, 70, 140), region_ambient=(64, 64, 128),
        # in the game's art IceFloorDeepBlue is the pale snowfield (where Westwood's snow trees stand), IceFloorRough
        # blue speckled ice, IceFloorDark dark slate ice (a frozen lake)
        wall="IceWall", base="IceFloorDeepBlue",
        patches=[("IceFloorRough", -0.9), ("IceFloorLight", 1.35), ("CaveHardBrown", 1.45), ("CaveHardTan", 1.95)],   # Westwood: rock 0.13 of its ice maps' floors
        patch_scale=1.35,                                # a finer patchwork of ice, snow and rock than the other biomes
        blends=[("IceFloorRough", 0, "BlendEdge"), ("IceFloorDeepBlue", 1, "BlendEdge"), ("IceFloorDark", 2, "BlendEdge"),
                ("IceFloorLight", 3, "BlendEdge"), ("CaveHardBrown", 4, "IceRidge"), ("CaveHardTan", 5, "IceRidge")],
        forest=dict(wall="IceWall",
                    trees={"TreeSnowCovered3": 28, "TreeSnowCovered6": 20, "TreeSnowCovered5": 19, "TreeSnowCovered4": 14,
                           "TreeSnowCovered2": 13, "TreeSnowCovered1": 6},
                    undergrowth={"CaveRocksSmall": 10, "CaveRocksTiny": 8, "CaveRocksPebbles": 8, "IceCrack2": 3,
                                 "IceCrack4": 2, "IceCrack6": 2},
                    flowers={"CaveRocksPebbles": 1}),
        # Westwood's ice maps are open snowfields: about 2.3 snow trees per 100 floor tiles and few other pieces (3.4-5.2
        # decorations per 100 tiles in all), the trees lining the cliffs
        tree_depth=(0.11, 0.03, 0.0), undergrowth=((0, 0), 0.03),
        open={"CaveRocksSmall": 0.2, "CaveRocksTiny": 0.2, "ArmBone": 0.2, "IceCrack2": 0.12, "IceCrack6": 0.06,
              "CaveRocksHuge": 0.1, "Skull": 0.08},
        wallside={"CaveRocksHuge": 0.6, "CaveRocksLarge": 0.35, "CaveBoulders": 0.25, "MineCrystal05": 0.2,
                  "MineCrystal02": 0.12, "CaveRockPillarTall1": 0.25, "CaveRockPillarShort2": 0.25},
        liquid=dict(floor="IceFloorDark", dress={}, edge=None),
        light_colours=[(96, 128, 224), (160, 160, 224), (64, 96, 192)], light_per100=dict(open=0.12, wall=0.2),   # Westwood: 0.09-0.23 per 100 tiles in all
        light_radius=170, light_intensity=35,
        sources=dict(wall={"Torch": 0.8}, open={}),      # Westwood: torches 0.1 per 100 floor tiles, by the walls
        creatures={"BlackWolf": 6, "WhiteWolf": 3, "Ghost": 2, "Skeleton": 2, "SkeletonLord": 1, "Bear": 1},
        creatures_per100=0.8),
    "lava": dict(
        env="lava", ambient=(45, 16, 15), region_ambient=(112, 0, 0),
        wall="Volcano", base="VolcanicCraggy",
        patches=[("CaveHardDark", 0.95), ("CaveHardBrown", -1.2), ("DirtDark2", 1.6)],
        blends=[("VolcanicCraggy", 0, "BlendEdge"), ("CaveHardBrown", 1, "BlendEdge"), ("CaveHardDark", 2, "BlendEdge"),
                ("DirtDark2", 3, "BlendEdge"), ("Lava", 6, "LavaEdgeBlackDirt")],
        edge_over={("Lava", "CaveHardBrown"): "LavaEdgeBrownDirt", ("Lava", "DirtDark2"): "LavaEdgeBrownDirt"},
        forest=dict(wall="Volcano",
                    trees={"CaveRockPillarTall1": 10, "CaveRockPillarShort1": 8, "Rock8": 6, "Rock6": 6, "Rock4": 5,
                           "CaveRocksHuge": 8},           # cooled-lava crusts read as puddles of lava: on the lava only
                    undergrowth={"CaveRocksPebbles": 14, "CaveRocksSmall": 10, "LegBone": 8, "Skull": 5, "ArmBone": 4,
                                 "GrassTuft3": 3, "Mushroom4": 2},
                    flowers={"CaveRocksPebbles": 1}),
        # Westwood's lava maps: 2.9-13.6 decorations per 100 floor tiles (typical 7.9)
        tree_depth=(0.3, 0.08, 0.0), undergrowth=((0, 1), 0.05),
        open={"LegBone": 1.2, "Skull": 0.7, "ArmBone": 0.5, "Rock8": 0.5, "CaveRocksMedium": 0.55, "FireGrate": 0.6,
              "CaveRocksSmall": 0.25, "GrassTuft3": 0.3},
        wallside={"CaveRocksHuge": 0.5, "Brick": 0.4, "CaveRocksLarge": 0.25, "Rock4": 0.2},
        liquid=dict(floor="Lava",
                    dress={"SmallFlame": 11.2, "MediumFlame": 4.3, "Flame": 2.2, "LargeFlame": 0.85, "SmallFlameImmobile": 1.5,
                           "LavaBubble4": 0.8, "LavaBubble5": 0.8, "LavaBubble6": 0.83, "LavaBubble7": 0.6, "LavaBubble8": 0.7,
                           "LavaBubble9": 0.95, "LavaFountain3": 0.5, "LavaHardened5": 0.45, "LavaHardened7": 0.35},
                    edge="LavaEdgeBlackDirt"),
        light_colours=[(224, 64, 0), (192, 32, 0), (128, 0, 0), (224, 96, 32)],
        light_per100=dict(open=5.0, wall=3.0, liquid=6.0), light_radius=180, light_intensity=60,
        sources=dict(wall={"Torch": 0.3}, open={"DunMirFlameBasinLit": 0.25}),
        creatures={"Imp": 5, "EmberDemon": 3, "MeleeDemon": 2, "Skeleton": 3, "Zombie": 2, "SkeletonLord": 1},
        creatures_per100=0.7),
}


def register_forests():
    """The biomes' wall plants (pillars, snow trees, volcanic rocks) as Planter forests: cave, ice, lava."""
    for k, b in BIOMES.items():
        FORESTS.setdefault(k, b["forest"])


class Dresser:
    def __init__(self, spec, rng, land, biome):
        register_forests()
        self.spec, self.rng, self.land = spec, rng, land
        self.b = BIOMES[biome]
        self.biome = biome
        self.wall, self.base = self.b["wall"], self.b["base"]
        self.pools = set()                   # squares of liquid behind the cliffs (outside the land)
        self.taken = set()                   # squares holding props, lights and sources
        self.structures = []                 # [(role, area, Building)]: the biome's built parts (structure())
        spec.d["ambient"] = list(self.b["ambient"])
        for mat, prio, edge in self.b["blends"]:
            spec.blending(mat, prio, edge=edge)
        for (ov, base), edge in self.b.get("edge_over", {}).items():
            spec.edge_over[(ov, base)] = edge

    # ---- liquid behind cliffs --------------------------------------------------------------------------------------
    def reserve_pool(self, centre_uv, radius_uv, stretch=1.0, angle=0.0, roughness=0.3):
        """A pool of the biome's liquid (a lava lake, an underground lake) the land keeps out of: the cliffs of the
        biome's wall ring it, and the liquid shows beyond them. Call before land.carve(). Returns its squares."""
        r = self.rng
        waves = [(k, r.uniform(0, 2 * math.pi), roughness * r.uniform(0.5, 1.0) / (1 + 0.5 * n))
                 for n, k in enumerate((2, 3, 5, 7))]
        ci, cj = centre_uv[0] / 2, centre_uv[1] / 2
        R0 = radius_uv / 2
        ca, sa = math.cos(-angle), math.sin(-angle)
        out = set()
        for i in range(int(ci - R0 * stretch - 3), int(ci + R0 * stretch + 4)):
            for j in range(int(cj - R0 * stretch - 3), int(cj + R0 * stretch + 4)):
                dx, dy = i + 0.5 - ci, j - 0.5 - cj
                rx, ry = dx * ca - dy * sa, dx * sa + dy * ca
                rx /= stretch
                th = math.atan2(ry, rx)
                R = R0 * (1 + sum(a * math.sin(k * th + p) for k, p, a in waves))
                if math.hypot(rx, ry) <= R: out.add((i, j))
        self.pools |= out
        self.land.forbidden |= out
        return out

    def reserve_channel(self, path_uv, half_squares):
        """A river of the liquid between cliffs, along a uv polyline (lava flowing between pools)."""
        from kit.layout import _densify
        pts = _densify([(u / 2, v / 2) for u, v in path_uv], 0.5)
        out = set()
        for si, sj in pts:
            for i in range(int(si - half_squares - 1), int(si + half_squares + 2)):
                for j in range(int(sj - half_squares - 1), int(sj + half_squares + 2)):
                    if math.hypot(i + 0.5 - si, j - 0.5 - sj) <= half_squares: out.add((i, j))
        self.pools |= out
        self.land.forbidden |= out
        return out

    def paint_pools(self):
        """The liquid's tiles: the pools plus one square under the cliffs all round (the liquid runs under them)."""
        mat = self.b["liquid"]["floor"]
        ring = {(i + a, j + b) for i, j in self.pools for a, b in N8} - self.land.squares
        for s in self.pools | ring:
            i, j = s
            if 3 <= i + j <= 250 and 3 <= i - j <= 250:
                self.spec.floor[square_tile(*s)] = mat

    def cap_islands(self, islands, material=None):
        """Floor on top of the islands the land rings with cliffs (ice outcrops, rock pillars): seen from above they
        read as the top of the rock, not as a pit into the void."""
        mat = material or self.base
        for blob in islands:
            for s in blob:
                i, j = s
                if 3 <= i + j <= 250 and 3 <= i - j <= 250: self.spec.floor[square_tile(*s)] = mat
            self.taken |= set(blob)              # nothing grows or stands on top of the rock (the checker would read
                                                 # a capped island holding pillars as a room of columns)

    # ---- the ground -----------------------------------------------------------------------------------------------
    def ground(self, clear=2):
        """Patches of the biome's other floors on its base (smooth noise, each material with a field of its own, so
        patches of different floors overlap and meet as Westwood's do: its ice maps have 1.85-2.65 spots per 100 floor
        tiles where three floors meet; one shared field nested the patches in bands, and a patch whose threshold lay
        beyond an earlier one's was never laid), keeping `clear` squares from what is already painted (paths, yards,
        buildings) so every seam has room to blend."""
        r = self.rng
        phs = [[r.uniform(0, 6.3) for _ in range(4)] for _ in self.b["patches"]]
        L = self.land
        features = [s for s in L.squares if self.spec.floor.get(square_tile(*s)) not in (None, self.base)] + list(L.taken)
        near = bfs_distance(features, L.squares, clear)
        k = self.b.get("patch_scale", 1.0)
        for s in L.squares:
            t = square_tile(*s)
            if self.spec.floor.get(t) != self.base or near.get(s, 99) < clear: continue
            i, j = s[0] * k, s[1] * k
            for (mat, th), ph in zip(self.b["patches"], phs):
                n = (math.sin(i * 0.15 + ph[0]) + math.sin(j * 0.19 + ph[1]) + 0.6 * math.sin((i - j) * 0.1 + ph[2])
                     + 0.4 * math.sin((i + j) * 0.27 + ph[3]))
                if (th > 0 and n > th) or (th < 0 and n < th):
                    self.spec.floor[t] = mat
                    break

    # ---- what grows or stands -------------------------------------------------------------------------------------
    def vegetate(self, keep_clear=(), groves=3, flowers=0):
        """Pillars, stalagmites or snow trees in front of the walls, thinning inward, and the biome's undergrowth."""
        p = Planter(self.spec, self.rng, self.land, forest=self.biome,     # never inside or against a structure
                    keep_clear=set(keep_clear) | self.taken | self.land.taken)
        p.tree_lines(depth=self.b["tree_depth"], spacing=1.25)
        if groves: p.groves(n=groves, size=(4, 8), radius=2.5, spacing=1.3, avoid_areas=())
        per_tree, edge_p = self.b.get("undergrowth", ((0, 1), 0.12))
        p.undergrowth(per_tree=per_tree, edge_p=edge_p)
        if flowers: p.flower_patches(flowers, size=(3, 6))
        self.planter = p
        return len(p.trees), len(p.small)

    def _contexts(self):
        L = self.land
        edge = [s for s in L.squares if any((s[0] + a, s[1] + b) not in L.squares for a, b in N8)]
        wall = set(edge)
        busy = set(L.roads) | L.plaza | L.water | L.taken
        opn = {s for s in L.squares if s not in wall and s not in busy}
        return opn, wall

    def _place(self, types, squares, per100, min_gap=1.6, jitter=0.35, wall_clear=1):
        """types {name: per 100 floor tiles} spread over `squares` (a square is one floor tile), each keeping
        `min_gap` squares from the other props placed here. wall_clear=1 keeps a prop's cell and the cells beside it
        free of walls (a crate never stands in a wall piece); 0 only its own cell (a web hung on the wall)."""
        sq = list(squares)
        self.rng.shuffle(sq)
        placed = []
        total = sum(types.values())
        if not sq or total <= 0: return 0
        n = int(round(len(sq) * total / 100 * per100))
        names = list(types); w = [types[t] for t in names]
        grid = {}
        for s in sq:
            if len(placed) >= n: break
            if s in self.taken: continue
            si, sj = s[0] + self.rng.uniform(0.5 - jitter, 0.5 + jitter), s[1] - self.rng.uniform(0.5 - jitter, 0.5 + jitter)
            cell = (int(si // 3), int(sj // 3))
            if any((si - x) ** 2 + (sj - y) ** 2 < min_gap ** 2 for a in (-1, 0, 1) for b in (-1, 0, 1)
                   for x, y in grid.get((cell[0] + a, cell[1] + b), ())): continue
            x, y = square_px(si, sj)
            cx, cy = int(x // 23), int(y // 23)
            near = [(cx, cy)] + ([(cx + a, cy + b) for a, b in N8] if wall_clear else [])
            if any(c in self.spec.wallmap for c in near): continue
            t = self.rng.choices(names, w)[0]
            self.spec.obj_px(t, x, y)
            grid.setdefault(cell, []).append((si, sj)); placed.append(t)
            self.taken.add(s)
        return len(placed)

    def clusters(self, types, squares, n, size=(3, 7), radius=1.8, gap=0.9, spacing=7.0, core=None):
        """n groups of props (a crystal formation, a stack of crates, a mushroom patch) with open floor between
        them: group centres keep `spacing` squares apart; each holds size[0]-size[1] pieces within `radius` squares,
        `gap` apart, the `core` type (a big crystal, a cart) at its middle. Returns the centres (si, sj)."""
        sq = [s for s in squares if s not in self.taken]
        self.rng.shuffle(sq)
        names = list(types); w = [types[t] for t in names]
        centres = []
        for s in sq:
            if len(centres) >= n: break
            si, sj = s[0] + 0.5, s[1] - 0.5
            if any(math.hypot(si - x, sj - y) < spacing for x, y in centres): continue
            pts = []
            k = self.rng.randint(*size)
            for t_ in range(k * 6):
                if len(pts) >= k: break
                if not pts and core: a, b = si, sj
                else:
                    r_ = radius * math.sqrt(self.rng.random()); th = self.rng.uniform(0, 2 * math.pi)
                    a, b = si + r_ * math.cos(th), sj + r_ * math.sin(th)
                q = (int(math.floor(a)), int(math.floor(b)) + 1)
                if q not in self.land.squares or any(math.hypot(a - x, b - y) < gap for x, y in pts): continue
                x, y = square_px(a, b)
                cx, cy = int(x // 23), int(y // 23)
                if any((cx + c, cy + e) in self.spec.wallmap for c in (-1, 0, 1) for e in (-1, 0, 1)): continue
                t = core if (core and not pts) else self.rng.choices(names, w)[0]
                self.spec.obj_px(t, x, y)
                pts.append((a, b)); self.taken.add(q)
            if pts: centres.append((si, sj))
        return centres

    def scatter_open(self, scale=1.0):
        opn, _ = self._contexts()
        return self._place(self.b["open"], opn, scale, min_gap=1.8)

    def rim(self, scale=1.0):
        _, wall = self._contexts()
        return self._place(self.b["wallside"], wall, scale, min_gap=1.5, jitter=0.25, wall_clear=0)

    def dress_liquid(self, scale=1.0):
        """Flames, bubbles, fountains and crusts on the liquid (Westwood: 11 small flames per 100 lava tiles)."""
        d = self.b["liquid"]["dress"]
        if not d: return 0
        visible = {s for s in self.pools if all((s[0] + a, s[1] + b) in self.pools for a, b in N4)}
        return self._place(d, visible, scale, min_gap=0.9, jitter=0.45)

    # ---- light ----------------------------------------------------------------------------------------------------
    def _light_xfer(self, rgb, radius=None, intensity=None):
        import json, os
        here = os.path.dirname(os.path.abspath(__file__))
        presets = json.load(open(os.path.join(here, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]
        base = dict(max((p for p in presets if p["animation"] == "steady" and p["intensity_class"] == "full"),
                        key=lambda p: p["weighted_share"])["xfer"])
        base.update(R=rgb[0], G=rgb[1], B=rgb[2])
        if "Color1" in base: base["Color1"] = list(rgb)
        if radius: base["LightRadius"] = radius
        if intensity: base["LightIntensity"] = intensity
        return base

    def lights(self, scale=1.0):
        """Coloured lights in the biome's colours (lava glows red over its liquid; caves amber; ice cold blue) and the
        visible sources (torch poles, flame basins). Lights keep 4 squares apart."""
        opn, wall = self._contexts()
        per = self.b["light_per100"]
        cols = self.b["light_colours"]
        placed = []
        ctx = [("open", opn), ("wall", wall), ("liquid", {s for s in self.pools if all((s[0] + a, s[1] + b) in self.pools for a, b in N4)})]
        for name, squares in ctx:
            k = per.get(name, 0) * scale
            if not k: continue
            sq = list(squares); self.rng.shuffle(sq)
            n = int(round(len(sq) * k / 100))
            for s in sq:
                if n <= 0: break
                si, sj = s[0] + 0.5, s[1] - 0.5
                if any((si - x) ** 2 + (sj - y) ** 2 < 16 for x, y in placed): continue
                rgb = self.rng.choice(cols)
                x, y = square_px(si, sj)
                self.spec.obj_px("ColorLight", x, y, xfer=self._light_xfer(rgb, self.b["light_radius"], self.b["light_intensity"]))
                placed.append((si, sj)); n -= 1
        for name, squares in (("wall", wall), ("open", opn)):
            self._place(self.b["sources"].get(name, {}), [s for s in squares if s not in self.taken], scale, min_gap=5.0, jitter=0.2)
        return len(placed)

    PACKS = {"BlackWolf": "Wolf", "WhiteWolf": "Wolf", "Wolf": "Wolf"}      # pack animals: a leader and its pack
    SKITTISH = {"Bat", "Rat"}

    # ---- built parts: Westwood's biome maps hold buildings in their own styles (rules/BIOMES.md: dungeon stone in the
    # caves, the Land of the Dead's ornate walls in the ice, Dun Mir's black halls by the lava), furnished by their
    # culture (rules/cultures.py)
    # Each structure's keepers and how they behave (kit/behaviours): (type, count, room kind, behaviour). A sentry
    # faces the way in and rouses the others when it sees an intruder; patrollers walk a loop of waypoints through the
    # rooms and their doorways; ambushers stand still until the player comes near, then all spring at once; skittish
    # ones flee when hit; guards stand their ground (Westwood: 38% of its hostiles guard, rules/NPCS.md).
    GARRISON = {"ogre_keep": [("OgreWarlord", 1, "ogre_hall", "sentry"), ("OgreBrute", 2, "ogre_den", "guard"),
                              ("GruntAxe", 2, None, "patrol")],
                "ice_temple": [("SkeletonLord", 1, "dark_chapel", "sentry"), ("Skeleton", 3, "dark_crypt", "ambush"),
                               ("Ghost", 2, None, "patrol")],
                "demon_forge": [("MeleeDemon", 1, "smithy", "sentry"), ("EmberDemon", 2, None, "patrol"),
                                ("Imp", 2, "storeroom", "skittish")]}

    def structure(self, role, area, toward=None, scale=1.25, shrink=(1.0, 0.92, 0.84, 0.76), name=""):
        """A building of kit/identity.py BUILDINGS[role] (the demon forge, the ice temple, the ogre keep) centred in
        `area`, its entrance on the side facing area `toward`. Call it before land.carve(): the cavern then grows round
        the building. Returns the building, or None when none fits."""
        from kit.building import generate_building
        from kit.identity import BUILDINGS
        L = self.land
        r = BUILDINGS[role]
        cx, cy = L.areas[area]["c"]
        side = None
        if toward:
            tx, ty = L.areas[toward]["c"]
            dx, dy = tx - cx, ty - cy
            side = ("u_max" if dx > 0 else "u_min") if abs(dx) >= abs(dy) else ("v_max" if dy > 0 else "v_min")
        for k in shrink:
            W, H = 2 * round(r["size"][0] * scale * k / 2), 2 * round(r["size"][1] * scale * k / 2)
            origin = (2 * round(cx - W / 4), 2 * round(cy - H / 4))
            b = generate_building(self.spec, self.rng, origin, (W, H), r["style"], program=[kd for kd, _ in r["rooms"]],
                                  entrance_side=side, building_id=role, occupied=set(), tries=24,
                                  shape=r.get("shape"), min_units=int(r.get("min_units", 0) * (scale * k) ** 2))
            if b: break
        else:
            return None
        L.take_cells(b.cells, margin=1)
        L.taken_strict |= {tile_square(x, y) for x, y in b.footprint}
        L.wall_cells |= set(self.spec.wallmap)
        self.structures.append((role, area, b, name))
        return b

    def furnish_structures(self):
        """Furnishes every room of the structures in its culture (BUILDINGS[role]["furnish"]). Returns
        [(role, room kind, pieces)]."""
        from kit.identity import BUILDINGS
        from kit.originality import furnish_original
        out = []
        for role, area, b, name in self.structures:
            style = BUILDINGS[role].get("furnish") or "town"
            for room in b.rooms:
                objs, res = furnish_original(self.spec, room, kind=room.kind, rng=random.Random(self.rng.random()),
                                             style=style)
                out.append((role, room.kind, len(objs)))
        return out

    def _room_spots(self, room):
        """Free standing spots in a room (world pixels): off the walls and clear of the furniture."""
        objs = self.spec.d["objects"]
        out = []
        for (x, y) in sorted(room.tiles):
            px_, py_ = (x + 1) * 23, (y + 1) * 23
            if any((int(px_ // 23) + a, int(py_ // 23) + c) in self.spec.wallmap for a in (-1, 0, 1) for c in (-1, 0, 1)):
                continue
            if any(abs(o["x"] - px_) < 30 and abs(o["y"] - py_) < 30 for o in objs): continue
            out.append((px_, py_))
        return out

    def _route(self, b):
        """A loop through a building's rooms: each room's free spot nearest its middle, and the doorway into the next
        room when they share one (world pixels)."""
        pts = []
        rooms = list(b.rooms)
        for k, room in enumerate(rooms):
            spots = self._room_spots(room)
            if spots:
                mx = sum(x for x, _ in spots) / len(spots); my = sum(y for _, y in spots) / len(spots)
                pts.append(min(spots, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2))
            nxt = rooms[(k + 1) % len(rooms)]
            door = next((d for d in room.doors if nxt.id in d.connects), None)
            if door and len(rooms) > 1: pts.append(((door.gap[0] + 0.5) * 23, (door.gap[1] + 0.5) * 23))
        return pts

    def garrison(self, pop=None):
        """The structures' keepers (GARRISON) in their rooms, with their behaviours. Returns the creatures placed."""
        from kit.npcs import Population
        pop = pop or getattr(self, "population", None) or Population(self.spec, self.rng)
        self.population = pop
        B = pop.behaviours
        placed = 0
        for role, area, b, name in self.structures:
            door = b.entrances[0].gap if b.entrances else None
            face = ((door[0] + 0.5) * 23, (door[1] + 0.5) * 23) if door else None
            used, sentries, others = [], [], []
            route = None
            for t, n, kind, how in self.GARRISON.get(role, []):
                rooms = [r for r in b.rooms if kind is None or r.kind == kind] or list(b.rooms)
                spots = [p for r in rooms for p in self._room_spots(r)]
                self.rng.shuffle(spots)
                group = []
                for _ in range(n):
                    spot = next((p for p in spots if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) > 60 for q in used)), None)
                    if spot is None: break
                    used.append(spot)
                    scr = pop.name(t)
                    if how == "patrol" and route is None:     # one loop through the rooms for the patrollers
                        pts = self._route(b)
                        route = pop.waypoint_path(pop.name(f"{t}Route"), pts) if len(pts) >= 2 else []
                    pop.creature(t, *spot, action="idle" if how in ("patrol", "ambush", "skittish") else "guard",
                                 face=face, scr=scr)
                    group.append(scr)
                    placed += 1
                if how == "sentry": sentries += group
                else: others += group
                if how == "patrol" and route:
                    for g in group: B.patrol(g, route, pause=2.0, loop=True)
                elif how == "ambush" and group:
                    ax = sum(p[0] for p in used[-len(group):]) / len(group); ay = sum(p[1] for p in used[-len(group):]) / len(group)
                    B.ambush(group, (ax, ay), reach=150.0)
                elif how == "skittish":
                    for g in group: B.skittish(g, 3.0)
            for snt in sentries:
                B.sentry(snt, face or (0, 0), rouse=[o for o in others], shout="Intruders!")
        return placed

    def declare_rooms(self, path):
        """<map>.rooms.json for review/rooms.py and review/roomscore.py: the structures' rooms, numbered."""
        from kit.identity import rooms_sidecar, BuildingIdentity
        return rooms_sidecar([(BuildingIdentity(role, area, name), b) for role, area, b, name in self.structures], path)

    def creatures(self, scale=1.0, avoid=(), groups=None, pop=None, min_start=20):
        """The biome's creatures as Westwood places them (rules/NPCS.md): most alone (a few in twos and threes), about 2
        squares from a wall, at least `min_start` squares from the arrival (`avoid`); 62% idle and 38% on guard,
        Westwood's sight range for each type, aggressiveness 0.5. With `pop` (kit/npcs.Population) wolves run as a
        scripted pack and bats and rats are skittish (kit/behaviours). Returns the creatures placed."""
        from kit.npcs import Population
        pop = pop or getattr(self, "population", None) or Population(self.spec, self.rng)
        edge = self.land.edge_distance()
        sq = [s for s, dd in edge.items() if 1 <= dd <= 3 and s not in self.taken and s not in self.land.taken
              and all(math.hypot(s[0] - a[0], s[1] - a[1]) >= min_start for a in avoid)]
        self.rng.shuffle(sq)
        n = int(round(len(self.land.squares) * self.b["creatures_per100"] * scale / 100))
        names = list(self.b["creatures"]); w = [self.b["creatures"][t] for t in names]
        placed, centres = 0, []
        for s in sq:
            if placed >= n: break
            if any(math.hypot(s[0] - x, s[1] - y) < 8 for x, y in centres): continue
            t = self.rng.choices(names, w)[0]
            if t in self.PACKS: k = self.rng.randint(3, 5)
            elif t in self.SKITTISH: k = self.rng.randint(1, 3)
            else: k = self.rng.choices((1, 2, 3), (0.75, 0.17, 0.08))[0]
            action = "guard" if self.rng.random() < 0.38 else "idle"
            members = []
            for q in range(k):
                si, sj = s[0] + 0.5 + (self.rng.uniform(-1.2, 1.2) if q else 0), s[1] - 0.5 + (self.rng.uniform(-1.2, 1.2) if q else 0)
                if (int(math.floor(si)), int(math.floor(sj)) + 1) not in self.land.squares: continue
                x, y = square_px(si, sj)
                if any((int(x // 23) + a, int(y // 23) + b) in self.spec.wallmap for a in (-1, 0, 1) for b in (-1, 0, 1)): continue
                tt = t if (q == 0 or t not in self.PACKS) else self.PACKS[t]
                scr = pop.name(tt) if (t in self.PACKS or t in self.SKITTISH) else None
                pop.creature(tt, x, y, action=action, scr=scr)
                if scr: members.append(scr)
                placed += 1
            if t in self.PACKS and len(members) >= 2: pop.behaviours.pack(members[0], members[1:])
            if t in self.SKITTISH:
                for nme in members: pop.behaviours.skittish(nme, 3.0)
            centres.append(s)
        self.population = pop
        return placed
