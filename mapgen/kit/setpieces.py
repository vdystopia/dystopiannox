"""Set pieces of QA round 1 (review/reviews/QA-round1.md; ledger review/qa1/setpieces.md): the well, the shrine, the
farmstead round a farmhouse, and the healing well every map's wells now are.

The user's two themes over every exterior: "spaces are too empty and lack object diversity", and "lack of balance and
symmetry: things placed randomly, not lined up with each other". So each set piece here is composed as a whole in its
yard's frame (kit/yards.Frame: u across, mirrored about 0; v from the way in to the back), its pieces in mirrored
pairs and even rows, on its own paving of whole squares (blended by the kit's ordinary edges), with several kinds of
thing round its centre.

- `healing_well(spec, x, y)`: the well every map lays (the town square's, a well yard's, a scene's). It is the
  WishingWell, the Nox campaign's well the player uses to be healed (Westwood's four campaign wells, Con02a's with the
  script MakeAWish; the plain Well is a prop that does nothing), named HealWell<n> (`HEAL_PREFIX`) so the map's
  behaviour scripts can hook it (fully heal health and mana).
- the well yard (kit/yards kind "well", `plan` before the land is carved, `build` after: `_well`): the well on a pad of
  cobblestone (whole squares of PAD over the grass), one of three archetypes: plain (barrels, the tool barrel
  and a bench by it, a sign before it, torch poles at its back corners), fenced (a low wooden fence and a gate round
  it, street lamps flanking the gate, barrels in the corners), market (the paving wider, benches facing it on its four
  sides, lamps at its corners, water barrels).
- the shrine court (kit/yards kind "shrine": `_shrine`): a rectangle of paving entered from the screen's bottom, its
  shape set by pieces at its corners and along both long sides in parallel rows, an aisle up its middle to the grand
  centrepiece at the back (QA round 1: "Give them a square or rectangular shape defined by obelisks and mana pillars
  or parallel statues that lead to a grand centerpiece. Needs much more structure"). Archetypes: obelisk court (mana
  obelisks at the corners, stone obelisks lining the sides, the great statue between flame basins), statue avenue
  (victory statues facing each other across the aisle, torch poles between, stone obelisks at the corners, the wolf
  statue or the great statue), mana court (dark mana obelisks at the corners and sides, a ring of mana crystals round
  a blue obelisk), open-air chapel (columns down the sides, benches in rows facing the altar, a statue behind it).
- `farmstead(...)`: what a farmhouse keeps round it (QA round 1, the farmyard: "the exteriors are too empty ... an
  apple tree with apples on the ground, a well, multiple gardens").
"""
import math
from kit.layout import square_tile, square_px

HEAL_WELL = "WishingWell"          # the campaign's healing well (TRIGGER: the player uses it)
HEAL_PREFIX = "HealWell"           # script names of the map's healing wells: HealWell1, HealWell2, ...
# a well's and a shrine's paving, and the town square's second ring: CobblestoneGrayLight, Westwood's grey cobbles over
# grass (BlendEdge, 10 campaign maps) and, set in rough cobbles, a ring with a brick kerb (CobbleStone, tried first, reads
# as bare earth: review/out/catalog/floorcat.png)
PAD = "CobblestoneGrayLight"
# a victory statue facing each square axis (its type's suffix: the way it looks on screen)
VICTORY_FACING = {"+i": "SE", "-i": "NW", "+j": "NE", "-j": "SW"}
BENCH_FACING = {"+i": "Bench1", "-i": "Bench5", "+j": "Bench4", "-j": "Bench2"}     # kit/scenes.BENCH_FACING
LAMP = ("StreetLampOrnate3", "StreetLampOrnate3Shadow", -15, 21)


def ensure_blends(spec):
    """The paving's edges: soft over grass and dirt (BlendEdge, as Westwood blends CobblestoneGrayLight onto GrassNorm),
    a brick kerb where it meets the rough cobbles of a square or a road (BrickEdgeBrown, Westwood's edge between its two
    cobbles, rules/out/floors.json)."""
    if PAD not in spec.blend: spec.blending(PAD, 6, "BlendEdge")
    spec.edge_over.setdefault((PAD, "RoughCobble"), "BrickEdgeBrown")
    if "RoughCobble" not in spec.blend: spec.blending("RoughCobble", 5, "BrickEdgeBrown")


def healing_well(spec, x, y):
    """The well that heals (HEAL_WELL), named for the map's behaviour scripts (HEAL_PREFIX + its number)."""
    n = sum(1 for o in spec.d["objects"] if o.get("type") == HEAL_WELL) + 1
    return spec.obj_px(HEAL_WELL, x, y, scr=f"{HEAL_PREFIX}{n}")


class _Put:
    """Pieces placed in a frame, mirrored pairs and singles, each recorded (u, v, room)."""
    def __init__(self, spec, fr):
        self.spec, self.fr, self.placed = spec, fr, []

    def one(self, t, u, v, room=0.6, **extra):
        x, y = self.fr.px(u, v)
        o = self.spec.obj_px(t, x, y, **extra)
        if t.startswith("StreetLamp"):
            self.spec.obj_px(LAMP[1], x + LAMP[2], y + LAMP[3])
        self.placed.append((u, v, room))
        return o

    def pair(self, t, u, v, room=0.6, t2=None):
        self.one(t, u, v, room)
        self.one(t2 or t, -u, v, room)


def _pave(spec, land, squares, material):
    for s in squares:
        if land is None or (s in land.squares and s not in land.water):
            spec.floor[square_tile(*s)] = material


def build_set(spec, land, y, fr):
    """Lays a well yard or a shrine court planned by kit/yards (`y.kind`, `y.arch`) in its frame `fr`."""
    import random as _random, zlib
    rng = _random.Random(zlib.crc32(f"{spec.d['name']}:{y.kind}:{y.gi},{y.gj}:{getattr(y, 'arch', '')}".encode()))
    ensure_blends(spec)
    if y.kind == "well": return _well(spec, land, y, fr, rng)
    return _shrine(spec, land, y, fr, rng)


# ---------------------------------------------------------------------------------------------------- the well
def _well(spec, land, y, fr, rng):
    """The well as a feature (QA round 1, the well: "This isn't so much a feature as it is just a well ± a sign. Try to
    make the well a larger feature. Give it a small area of cobblestone beneath it. Add more objects like buckets.
    Surround some wells by a fence or a gate"). Nox has no bucket: the bucket of tools (BarrelWithTools) and water
    barrels stand for them."""
    arch = getattr(y, "arch", "plain")
    P = _Put(spec, fr)
    half, D = fr.half, fr.D
    c = D / 2                                            # the well at the yard's middle, on its axis
    R = {"plain": 2.0, "fenced": 1.5, "market": 3.0}.get(arch, 2.0)
    _pave(spec, land, fr.squares(-R, R, c - R, c + R), PAD)
    if arch == "fenced":                                 # the whole fenced ground paved
        from kit.yards import yard_ground
        _pave(spec, land, yard_ground(y, land), PAD)
    healing_well(spec, *fr.px(0, c))
    P.placed.append((0, c, 1.2))
    if arch == "plain":
        # the barrels the water is drawn into either side, the bucket of tools and a barrel behind, a bench before it
        # facing it, a torch pole at each corner of the paving (no sign: a sign needs its text, and the big signs read
        # badly, nox1)
        P.pair("WaterBarrel", 1.35, c, 0.6)
        P.pair("BarrelWithTools1", 1.25, c + 1.35, 0.6, t2="Barrel")
        P.one(BENCH_FACING[fr.axis(0, 1)], 0, c - 1.7, 0.8)
        for dv in (-1, 1):
            P.pair("TorchPole", R + 0.15, c + dv * (R + 0.15), 0.6)
    elif arch == "fenced":
        # a low fence and its gate round it (kit/yards: the yard's fence), street lamps or torch poles flanking the gate
        # outside; inside, round the well as the plain well has them, the water barrels, the bucket of tools and a barrel,
        # a bench before it facing it
        P.pair("StreetLampOrnate3" if rng.random() < 0.5 else "TorchPole", 1.6, -0.75, 0.6)
        P.pair("WaterBarrel", 1.35, c, 0.6)
        P.pair("BarrelWithTools1", 1.25, c + 1.3, 0.6, t2="Barrel2")
        P.one(BENCH_FACING[fr.axis(0, 1)], 0, c - 1.55, 0.8)
        if half >= 3.4:                                  # a bigger yard: barrels in its back corners
            P.pair("Barrel", half - 0.75, D - 0.75, 0.6)
    else:
        # the market well: benches facing it on its four sides, lamps at the paving's corners, water barrels and the
        # bucket of tools on its diagonals
        for (du, dv) in ((0, -1), (0, 1), (1, 0), (-1, 0)):
            P.one(BENCH_FACING[fr.axis(-du, -dv)], 2.1 * du, c + 2.1 * dv, 0.8)
        for dv in (-1, 1):
            P.pair("StreetLampOrnate3", 2.5, c + 2.5 * dv, 0.6)
        P.pair("WaterBarrel", 1.0, c + 1.0, 0.5)
        P.pair("BarrelWithTools1", 1.0, c - 1.0, 0.5, t2="Barrel")
    return P.placed


# ---------------------------------------------------------------------------------------------------- the shrine
SHRINE_CENTRE = {"obelisk_court": ("HorrendousStatue1", "DunMirWolfStatue"),
                 "statue_avenue": ("DunMirWolfStatue", "HorrendousStatue1"),
                 "mana_court": ("Obelisk",), "open_chapel": ("DunMirAltar2",)}


def _shrine(spec, land, y, fr, rng):
    """A shrine court: a rectangle of paving whose shape the pieces set (corners and both long sides in parallel rows),
    an aisle up its axis to the grand centrepiece at the back, every piece mirrored (QA round 1, the shrine: all ten
    "awful": "Change shrines drastically. Give them a square or rectangular shape defined by obelisks and mana pillars
    or parallel statues that lead to a grand centerpiece. Needs much more structure")."""
    from kit.yards import yard_ground
    arch = getattr(y, "arch", "obelisk_court")
    P = _Put(spec, fr)
    half, D = fr.half, fr.D
    court, aisle = ("RoughCobble", PAD) if rng.random() < 0.6 else (PAD, "RoughCobble")
    _pave(spec, land, yard_ground(y, land), court)
    ah = 1.0 if fr.lat == 0.5 else 0.5                   # the aisle 2 squares wide (1 on a j side's centred lattice)
    if fr.lat == 0.0 and half >= 5: ah = 1.5
    cz = D - 2.4                                         # the centrepiece
    _pave(spec, land, fr.squares(-ah + 0.05, ah - 0.05, -0.6, cz - 1.0), aisle)
    _pave(spec, land, fr.squares(-1.6, 1.6, cz - 1.6, cz + 1.6), aisle)            # its dais
    ci = rng.choice(SHRINE_CENTRE[arch])
    cu = half - 0.75                                     # the long sides' line, inside the paving's edge
    # the corners
    corner = {"obelisk_court": "Obelisk", "statue_avenue": "Monument1", "mana_court": "LOTDManaObelisk",
              "open_chapel": "Column8"}[arch]
    for v in (0.6, D - 0.6):
        P.pair(corner, cu, v, 0.9)
    # the long sides: a row each side, evenly spaced between the corners
    side_t = {"obelisk_court": "Monument1", "statue_avenue": "TorchPole", "mana_court": "Obelisk",
              "open_chapel": "MarbleColumn"}[arch]
    n_side = max(1, int((D - 3.2) / 2.2))
    side_vs = [0.6 + (D - 1.2) * (k + 1) / (n_side + 1) for k in range(n_side)]
    for v in side_vs:
        P.pair(side_t, cu, v, 0.7)
    # the way in: braziers or flame basins either side of the aisle's mouth
    P.pair("DunMirFlameBasinLit" if arch in ("obelisk_court", "mana_court") else "Brazier", ah + 0.9, 0.3, 0.6)
    # the centrepiece and what flanks it
    if arch == "mana_court":
        P.one("Obelisk", 0, cz, 1.0)
        for k in range(8):                               # a ring of mana crystals round it
            a = k * math.pi / 4 + math.pi / 8
            P.one(f"MineManaCrystal{1 + (k % 2) * 4}", 1.25 * math.cos(a), cz + 1.25 * math.sin(a), 0.4)
        P.pair("LOTDManaObelisk", 2.6, cz, 0.8)
        v = 2.0                                          # stone obelisks lining the aisle up to it
        while v <= cz - 2.6:
            P.pair("Monument1", ah + 0.8, v, 0.5)
            v += 2.0
    elif arch == "open_chapel":
        P.one("DunMirAltar2", 0, cz, 0.9)
        P.one("Statue1a", 0, cz + 1.3, 0.7)
        P.pair("DunMirFlameBasinLit", 1.5, cz, 0.6)
        P.pair("StatueVase1S", 2.6, cz + 0.8, 0.6)
        # benches in rows facing the altar, both sides of the aisle
        face = BENCH_FACING[fr.axis(0, 1)]
        v = 2.0
        while v <= cz - 2.2:
            for u in (ah + 0.9, ah + 2.2):
                if u <= cu - 1.0: P.pair(face, u, v, 0.7)
            v += 1.5
    else:
        P.one(ci, 0, cz + 0.2, 1.6)
        P.pair("DunMirFlameBasinLit", 2.3, cz - 0.4, 0.6)
        if arch == "statue_avenue":
            # victory statues facing each other across the aisle, the length of it
            kind = rng.choice((1, 2, 3, 4))
            v = 2.0
            while v <= cz - 2.4:
                for sd in (1, -1):
                    t = f"StatueVictory{kind}{VICTORY_FACING[fr.axis(-sd, 0)]}"
                    P.one(t, sd * (ah + 1.0), v, 0.7)
                v += 2.0
        else:
            # urns lining the aisle, a pair every two squares
            v, k = 2.0, 0
            while v <= cz - 2.4:
                P.pair(("StatueVase1S", "StatueVase3S")[k % 2], ah + 0.8, v, 0.5)
                v += 2.0; k += 1
    return P.placed


# ---------------------------------------------------------------------------------------------------- the farmstead
def apple_tree(spec, x, y, rng, apples=(1, 3), crate=False):
    """An apple tree with apples fallen under it that the player can pick up (QA round 1, the farmyard: "An apple tree
    with apples on the ground (the item that players can pick up)"), a crate of apples by it now and then."""
    spec.obj_px("TreeApple", x, y)
    for _ in range(rng.randint(*apples)):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(26, 40)
        spec.obj_px("RedApple", x + r * math.cos(a), y + 0.6 * r * abs(math.sin(a)) + 8)
    if crate:
        spec.obj_px("TraderAppleCrate", x + 44, y + 18)
