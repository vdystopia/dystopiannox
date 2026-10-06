"""How close outdoor things may stand (Starwell playtest, 2026-10-05: "Many object clusters like these crates are
simply too close to each other": barrels of several sizes overlapping, their sprites run into each other; "the
northeast stretch of fence overlaps with the row of crops ... this fence is literally on top of this row of plants").

- Pieces keep apart by Westwood's closest pairs (corpus, the representative maps, each piece's nearest of the other
  family, p05 rounded up): a stack touches only where Westwood's stacks touch, and nothing runs into anything.
  `py rules/spacing.py` re-measures them on the campaign maps alone (rules/out/spacing.json; the quest maps moved no
  pair by more than a pixel): every pair below is at or under the campaign's p05 (barrels 26, crates 32, a barrel
  and a crate 43, racks 28, cots 44, benches 46, stools 21, headstones 39) except sacks (17; 27 measured).
      barrels 25 px apart (p25 29), big barrels 31, a barrel and a big one 33, crates 31, a barrel and a crate 38,
      sacks 20, a sack and a crate 33, a sack and a barrel 30, racks 27, bedrolls 35, benches 45, stools 20,
      headstones 39, anything and a cart 48, anything and a fire 50 (its ring of stones excepted).
  Pairs not in the table keep most of their footprints apart (0.8 of both radii, at least 14 px); logs 30.
- Nothing stands on a wall or fence line: a piece keeps its sprite's half-width and a margin from the line through the
  wall's cells (`wall_clearance`), so a crop row lies inside its fence with a walkable strip between.
- Pickable things never dress the ground (playtest: "candle objects ... can actually be picked up by the player. they
  are not suitable exterior lights"): `pickable(t)`; outdoors a light is a torch pole, a brazier, a street lamp or a
  fire.

kit/dressing.py, kit/camps.py and kit/yards.py place by these; validate/checks.py check_exterior faults what breaks
them on a built map.
"""
import math, re

FAMILIES = [("barrel", r"^(Barrel|Barrel2|BarrelLOTD|BarrelSteel\d|BarrelWithTools\d|WaterBarrel|TargetBarrel\d)$"),
            ("bigbarrel", r"^(LargeBarrel\d|PiledBarrels\d)$"),
            ("crate", r"^(Crate\d|DarkCrate\d|CrateSteel\d|TraderAppleCrate)$"),
            ("sack", r"^SackChest"),
            ("cart", r"^(OutdoorTraderCart|MineOreCart\d|MineOreCartBroken\d)$"),
            ("rack", r"^(OutdoorTraderArmorRack\d|TraderPoleArm\d|TraderBowRack\d|TraderQuiverRack|OutdoorTraderHelmPoles)$"),
            ("cot", r"^Cot\d$"),
            ("ubed", r"^UrchinBed(Flat)?\d$"),
            ("bench", r"^(Bench\d|OgreBench\d)$"),
            ("stool", r"^(Stool\d?|OgreStool\d|UrchinStool\d)$"),
            ("tomb", r"^(Tombstone\d+|Cross\d)$"),
            ("log", r"^ForestLog0[124]$"),
            ("fire", r"^(CampFire|CampFireUnused)$")]
_FAM_RX = [(f, re.compile(rx)) for f, rx in FAMILIES]
# Westwood's closest pairs (px between centres), unordered
PAIR = {("barrel", "barrel"): 25, ("bigbarrel", "bigbarrel"): 31, ("barrel", "bigbarrel"): 33, ("crate", "crate"): 31,
        ("barrel", "crate"): 38, ("bigbarrel", "crate"): 38, ("sack", "sack"): 20, ("crate", "sack"): 33,
        ("barrel", "sack"): 30, ("bigbarrel", "sack"): 30, ("rack", "rack"): 27, ("cot", "cot"): 35,
        ("bench", "bench"): 45, ("stool", "stool"): 20, ("tomb", "tomb"): 39, ("log", "log"): 16, ("ubed", "ubed"): 28}
LOG_GAP = 30          # a log and anything else: logs are long and narrow, their footprint's radius overstates them
CART_GAP, FIRE_GAP = 48, 50
# things that may touch: a fire's ring of stones, small stuff strewn on the ground
LOOSE = re.compile(r"^(CaveRocks(Small|Pebbles|Tiny)|Rock\d|Flowers|Mushroom|Straw|Skull|ArmBone|LegBone|Brick\d|"
                   r"Corpse|Plant|Garden|IceCrack|Puddle|Weed|Grass|Foliage|Mining|MineOreCartWheel|SpiderWeb)")
# pickable things (rules/lighting.py PICKUP_CLASSES and xfers; the lights a player can carry off)
PICK_CLASSES = ("FOOD", "KEY", "WEAPON", "ARMOR", "WAND")
PICK_XFERS = {"GoldXfer", "AmmoXfer", "WeaponXfer", "ArmorXfer"}
PICK_TYPES = re.compile(r"^(Candle\d|Candle\dUnlit|Lantern\d?|TorchFresh|TorchInventory|TorchSpent)$")


def family(t):
    for f, rx in _FAM_RX:
        if rx.match(t or ""): return f
    return None


def _shape(t):
    from kit.walkways import thing_shapes
    return thing_shapes().get(t)


def radius(t):
    """About how far a thing's footprint reaches from its centre (px)."""
    sh = _shape(t)
    if not sh or not sh[0] or sh[0] == "NULL": return 8.0
    ext, ex, ey = sh[0], sh[1], sh[2]
    return max(6.0, max(ex, ey) / 2 if ext == "BOX" else ex)


def gap(a, b):
    """The least distance (px) between the centres of two outdoor pieces of types a and b; 0: they may touch."""
    if LOOSE.match(a or "") or LOOSE.match(b or ""): return 0.0
    fa, fb = family(a), family(b)
    if "fire" in (fa, fb): return FIRE_GAP
    if "cart" in (fa, fb): return CART_GAP
    if fa and fb:
        g = PAIR.get((fa, fb)) or PAIR.get((fb, fa))
        if g: return float(g)
    if "log" in (fa, fb): return LOG_GAP
    return max(14.0, 0.8 * (radius(a) + radius(b)))


def sprite_half(t):
    """Half the width a piece is drawn (px), for keeping it off a wall line: crops and bushes are drawn far wider
    than their footprint (GardenTomatos: a 5 px footprint, a plant 30 px across)."""
    if re.match(r"^(Garden|Plant|Bush|Flowers)", t or ""): return 15.0
    return max(12.0, radius(t))


def _seg(px_, py_, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    s = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px_ - ax) * dx + (py_ - ay) * dy) / L2))
    return math.hypot(px_ - ax - s * dx, py_ - ay - s * dy)


def wall_clearance(walls, x, y, reach=3, only=None):
    """Distance (px) from a point to the nearest wall line: the lines joining the centres of diagonal wall cells (a
    run of fence or wall), or a lone cell's centre. walls: {cell: ...} (spec.wallmap or MapData.walls); only: a
    predicate on the cell's wall, to count only some walls (fences, built walls). 999 when none is within reach."""
    C = 23
    cx, cy = int(x // C), int(y // C)
    best = 999.0
    for a in range(-reach, reach + 1):
        for b in range(-reach, reach + 1):
            c = (cx + a, cy + b)
            w = walls.get(c)
            if w is None or (only and not only(w)): continue
            ax, ay = (c[0] + 0.5) * C, (c[1] + 0.5) * C
            joined = False
            for d in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                wn = walls.get(n)
                if wn is None or (only and not only(wn)): continue
                joined = True
                best = min(best, _seg(x, y, ax, ay, (n[0] + 0.5) * C, (n[1] + 0.5) * C))
            if not joined: best = min(best, math.hypot(x - ax, y - ay))
    return best


def off_walls(walls, t, x, y, margin=8.0):
    """Whether a piece of type t at (x, y) px stands clear of every wall line by its drawn half-width and a margin."""
    return wall_clearance(walls, x, y) >= sprite_half(t) + margin


def pickable(t, cls="", xfer=""):
    """Whether a player can pick the thing up (and so it is never ground decor)."""
    if PICK_TYPES.match(t or ""): return True
    if any(k in (cls or "") for k in PICK_CLASSES): return True
    if xfer in PICK_XFERS: return True
    if not cls:
        sh = _shape(t)
        if sh: return any(k in sh[3] for k in PICK_CLASSES)
    return False


def spaced(t, x, y, others, scale=1.0):
    """Whether (t, x, y) keeps its gap from every (t2, x2, y2) in others."""
    for t2, x2, y2 in others:
        g = gap(t, t2) * scale
        if g and (x - x2) ** 2 + (y - y2) ** 2 < g * g: return False
    return True
