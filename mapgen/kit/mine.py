"""Mine entrances: a rock face along one side of a work yard, with a timbered tunnel into it that a cave-in
blocks a few timber sets in (the mine beyond is not part of the map).

Learned from Westwood's mines (Con01A, Con03B):
- passages are 3 squares wide between ManaMineWall, on ManaMineDirt;
- a timber set every few squares: three MineBeam pieces 25 px apart across the passage (MineBeam1 runs
  along '\\', MineBeam2 along '/'), with a MinePost at an end of some sets (MinePost3 mostly with
  MineBeam1, MinePost4 with MineBeam2);
- the creaking ambience AmbMineCreaks inside (no xfer);
- Nox draws a wall's face toward the bottom of the screen, so a rock face that rises above a yard lies on
  the yard's north-west (side (-1, 0)) or north-east (side (0, 1)) side; on the other sides it reads as a
  drop (the edge of Con03B's plateau).

Order of operations (PROCESS.md): MineEntrance(...) and plan() right after the yard, before any building;
cut() right after Land.carve(); ground() after Land.apply(); dress() with the other props.
"""
import math
from .layout import Land, square_tile, square_px, N4

# timber across the passage, by the axis the passage's width runs along (i or j in squares)
BEAM_ACROSS = {"j": "MineBeam2", "i": "MineBeam1"}
POST_FOR = {"MineBeam1": "MinePost3", "MineBeam2": "MinePost4"}
# carts whose long side runs along the passage (BOX extents: ex along u = i, ey along v = j)
CARTS_ALONG = {"i": ("MineOreCart1", "MineManaCart2", "MineOreCartBroken1"),
               "j": ("MineOreCart2", "MineManaCart1", "MineOreCartBroken2")}
BEAM_STEP = 25 / 32.5          # Westwood's 25 px between beam pieces, in squares


class MineEntrance:
    def __init__(self, land, yard, side, rng, depth=9, width=3, gap=4, reach=5, rock=14, mouth_at=0.5):
        """yard: the work yard's squares. side: from the yard toward the rock, (-1, 0) or (0, 1).
        depth: tunnel length in squares (the cave-in fills its last three); width: tunnel width;
        gap: forecourt depth between the yard and the face; reach: how far the face runs past the
        yard at each end before curving back; rock: how deep the rock is kept free of land."""
        assert side in ((-1, 0), (0, 1)), "a rock face shows only toward the bottom of the screen"
        self.L, self.rng, self.side = land, rng, side
        self.perp = (abs(side[1]), abs(side[0]))
        self.lat_axis = "j" if self.perp == (0, 1) else "i"
        self.axis = "i" if self.lat_axis == "j" else "j"
        self.depth, self.width, self.gap = depth, width, gap
        proj = lambda s: s[0] * side[0] + s[1] * side[1]
        lat = lambda s: s[0] * self.perp[0] + s[1] * self.perp[1]
        self.base = max(proj(s) for s in yard) + gap
        lats = [lat(s) for s in yard]
        self.l0, self.l1 = min(lats) - reach, max(lats) + reach
        self.lm = round(min(lats) + (max(lats) - min(lats)) * mouth_at)
        half = width // 2
        # the face: straight either side of the mouth (the portal frame lines up with it), elsewhere
        # stepping back a square or two now and then like Westwood's rock edges
        ph = rng.uniform(0, 6.3)
        self.face = {l: 0 if abs(l - self.lm) <= half + 3 else int(round(0.8 + 0.9 * math.sin(l * 0.45 + ph)))
                     for l in range(self.l0 - 10, self.l1 + 11)}
        self.tunnel = {self.sq(o, l) for o in range(1, depth + 1) for l in range(self.lm - half, self.lm + half + 1)}
        self.forecourt = {self.sq(o, l) for l in range(self.l0, self.l1 + 1) for o in range(1 - gap, self.face[l] + 1)}
        self.rock = set()
        for l, f in self.face.items():
            back = max(0, self.l0 - l, l - self.l1)               # past the yard the face curves away
            for o in range(f + 1 + back, rock + 1 + back):
                s = self.sq(o, l)
                if s not in self.tunnel: self.rock.add(s)
        self.track = {self.sq(o, l) for o in range(1 - gap, 1) for l in range(self.lm - half, self.lm + half + 1)}

    # ---- geometry: o = depth into the rock (0 = the last forecourt square), l = lateral position -----------
    def sq(self, o, l):
        return (self.side[0] * (self.base + o) + self.perp[0] * l, self.side[1] * (self.base + o) + self.perp[1] * l)

    def pt(self, o, l):
        """Continuous square coordinates (for square_px) of depth o, lateral l; the face line is o = 0.5."""
        c = self.sq(0, 0)
        return (c[0] + 0.5 + o * self.side[0] + l * self.perp[0], c[1] - 0.5 + o * self.side[1] + l * self.perp[1])

    def px(self, o, l):
        return square_px(*self.pt(o, l))

    @property
    def mouth(self):
        """The square in front of the tunnel's middle lane."""
        return self.sq(0, self.lm)

    # ---- steps ------------------------------------------------------------------------------------------
    def plan(self):
        """With the yard, before buildings: the forecourt and tunnel stay land, the rock may never be land."""
        self.L.reserved |= self.forecourt | self.tunnel
        self.L.forbidden |= self.rock

    def cut(self):
        """Right after Land.carve(): the forecourt and tunnel are land, nothing beyond the face is."""
        L = self.L
        L.squares = Land._largest(Land._fix_pinches((L.squares - self.rock) | self.forecourt | self.tunnel,
                                                    avoid=self.rock))
        L.taken |= self.tunnel

    def ground(self, spec, wall="ManaMineWall", floor="ManaMineDirt", track="DirtHard"):
        """After Land.apply(): the face and tunnel walls in mine rock, ore-dust floor in the tunnel and
        spilling out of the mouth, a packed cart track from the mouth to the yard."""
        rockish = self.rock | self.tunnel
        for (x, y), w in spec.wallmap.items():
            p, q = (x + y) // 2, (x - y) // 2
            if any(s in rockish for s in ((p - 1, q), (p, q), (p - 1, q + 1), (p, q + 1))):
                w["material"] = wall
        half = self.width // 2
        for s in self.track:
            if s in self.L.squares:
                spec.floor[square_tile(*s)] = track
                self.L.roads.add(s)
        for o in (-1, 0):
            for l in range(self.lm - half - 1, self.lm + half + 2):
                s = self.sq(o, l)
                if s in self.L.squares and (o == 0 or abs(l - self.lm) <= half): spec.floor[square_tile(*s)] = floor
        for s in self.tunnel: spec.floor[square_tile(*s)] = floor

    def dress(self, spec, light=None, torch=None, glow=None):
        """The portal and timber sets, the cave-in that blocks the tunnel, crystals at the wall feet, a
        faint glow and creaking beyond the rubble; outside, torches flanking the mouth, a loaded cart on
        the track, the winch and a barrel of tools against the face, picks and shovels left about.
        light(si, sj, xfer) and torch(si, sj) are the design's own helpers; glow is the light's colour."""
        rng, d, lm, half = self.rng, self.depth, self.lm, self.width // 2
        put = lambda t, o, l: spec.obj_px(t, *self.px(o, l))
        beam = BEAM_ACROSS[self.lat_axis]
        n = self.width
        for k, o in enumerate([0.7] + [0.7 + 3 * t for t in range(1, 9) if 0.7 + 3 * t < d - 2.6]):
            for b in range(n):
                put(beam, o, lm + (b - (n - 1) / 2) * BEAM_STEP)
            ends = (-1, 1) if k == 0 else ((-1,) if k % 2 else (1,))
            for e in ends:
                put(POST_FOR[beam], o + 0.1, lm + e * (half + 0.3))
        # the cave-in: a great boulder at the back, boulders and rocks across the width, rubble spilling forward
        for t, o, l in (("BoulderIndestructible", d - 0.9, 0.0), ("CaveBoulders", d - 1.2, -1.0), ("CaveRocksHuge", d - 1.1, 1.0),
                        ("Boulder", d - 1.9, -0.45), ("CaveBoulders", d - 2.0, 0.6), ("CaveRocksLarge", d - 2.4, -1.05),
                        ("CaveRocksLarge", d - 2.6, 0.2), ("CaveRocksMedium", d - 2.8, 1.0), ("CaveRocksMedium", d - 3.1, -0.5),
                        ("CaveRocksSmall", d - 3.4, 0.55), ("CaveRocksSmall", d - 3.6, -1.0), ("CaveRocksPebbles", d - 3.8, 0.1),
                        ("CaveRocksPebbles", d - 4.3, 0.9)):
            put(t, o, lm + l)
        put(CARTS_ALONG[self.axis][2], d - 4.6, lm - 0.75)             # a cart smashed by the fall
        for k, o in enumerate(x / 10 for x in range(25, int((d - 3.5) * 10), 28)):
            side_ = 1 if k % 2 else -1
            put("MineCrystalUp0%d" % (1 + k % 5), o, lm + side_ * (half + 0.25))
        if light and glow: light(*self.pt(d - 1.6, lm), glow)          # mana glow from beyond the rubble
        put("AmbMineCreaks", d - 2.0, lm)
        # outside: torches flanking the mouth, a loaded cart on the track, the winch and tools against the face
        if torch:
            for e in (-1, 1): torch(*self.pt(-0.45, lm + e * (half + 1.0)))
        put(CARTS_ALONG[self.axis][1], -1.6, lm + 0.55)
        put("PulleyGear1", -0.35, lm + half + 2.7)
        put("BarrelWithTools1", -0.4, lm - half - 2.5)
        put("MiningPickAxeOnGround2", -0.6, lm - half - 3.6)
        for s in (self.sq(-1, lm), self.sq(-2, lm), self.sq(-1, lm + half + 2), self.sq(-1, lm - half - 2)):
            self.L.taken.add(s)
        spots = [(o, l) for o in range(-self.gap + 1, 1) for l in range(self.l0 + 1, self.l1)
                 if abs(l - lm) > half + 3 and self.sq(o, l) in self.L.squares]
        rng.shuffle(spots)
        tools = ["MiningPickAxeInGround1", "MiningShovelInGround", "MiningPickAxeInGround2", "MiningShovelInGround"]
        placed = []
        for o, l in spots:
            if len(placed) == len(tools): break
            if all(abs(o - a) + abs(l - b) >= 4 for a, b in placed):
                put(tools[len(placed)], o + rng.uniform(-0.2, 0.2), l + rng.uniform(-0.2, 0.2))
                placed.append((o, l))
                self.L.taken.add(self.sq(o, l))
