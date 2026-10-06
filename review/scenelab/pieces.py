"""What a scene is made of, read the same way from Westwood's maps and ours: which objects are a scene's pieces, their
families, and the scene itself: the pieces grown out from its anchor.

- piece(o): whether an object is a placed piece (furniture of the outdoors: a barrel, a tent, a headstone, a crop, a
  torch pole, a rock heap), not nature (trees, plants, flowers, grass, fungi, reeds), not the trivial ground bits
  (pebbles), not lights' invisible glows, sounds, shadows, monsters, doors or exits;
- family(t): the piece's family (fire, seat, bed, tent, store, cart, rack, ...), for the type mix and the gaps between
  families;
- grow(pieces, seeds, link, radius): the scene: every piece within `link` px of a seed, then of a piece already in,
  never further than `radius` px from the seeds' middle (single linkage, bounded). The same call reads a Westwood scene
  round its anchor object and a generated one round the anchor the kit laid.
"""
import math, re

NATURE = re.compile(r"^(Tree|Coni|Decid|Aspen|Plant(?!Barren)|Bush|Flower|Foliage|Grass|Weed|Fern|PlantFern|Mushroom|"
                    r"Reed|Cattail|Rush|Lily|Ripple|WaterRipples|Puddle|Vine|Ivy|Moss|Hedge)", re.I)
TRIVIAL = re.compile(r"^(ColorLight|Amb|Invisible|PlayerStart|CaveRocksPebbles|CaveRocksTiny|Extent|Waypoint|"
                     r"Polygon|.*Shadow|.*ShadowDN\d|.*ShadowUP\d|SmallFlame|MediumFlame|LargeFlame|Flame$|"
                     r"BlackPowder|Arrow|Fist|Glyph|Rune|Spell|Ability|.*Potion|Gold|.*Key$|.*Wand$|Book|Scroll|"
                     r"Quiver$|Bow$|CrossBow$|.*Sword$|.*Mace$|.*Axe$|.*Helm$|.*Boots$|.*Gauntlets$|Mushroom|Meat$|"
                     r"RedApple|Bread|Cider|Ration|Corpse)", re.I)

FAMILIES = [
    ("fire", r"^(CampFire|CampFireUnused|OgreFirePit|OgreFirePitUnlit|FireGrate|Fireplace|FreestandingFireplace)"),
    ("light", r"^(TorchPole|Brazier|StreetLamp|SpikeBrazier|Torch$|OgreTorch|DunMirTorch|VictorianLantern|Lantern|"
              r"DunMirFlameBasin|Candleabra)"),
    ("tent", r"^(OutdoorTraderPupTent|TraderTent|OgreHut)"),
    ("bed", r"^(Cot\d|UrchinBed|UrchinHammock|OgreBed|Bed\d|BedRoll|OgreBearskin|WolfPelt)"),
    ("seat", r"^(Bench\d|LightBench|CushionedBench|OgreBench|Stool\d?|OgreStool|UrchinStool|CushionedStool|"
             r"DarkWoodenChair|OldDarkWoodenChair|WoodenChair|Chair)"),
    ("table", r"^(UrchinTable|OgreTable|SquareTable|OvalTable|RoundTable|SmallTable|Table|TraderDesk|Desk)"),
    ("cart", r"^(OutdoorTraderCart|MineOreCart\d|MineOreCartBroken\d|MineManaCart|MineOreCartWheel)"),
    ("store", r"^(Barrel\d?$|BarrelLOTD|LargeBarrel|PiledBarrels|WaterBarrel|Crate\d|DarkCrate|CrateSteel|BarrelSteel|"
              r"SackChest|OgreSack|TraderAppleCrate|Chest|DunMirChest|ChestUrchin|ChestOgre|StumpChest|Spitoon)"),
    ("rack", r"^(OutdoorTraderArmorRack|TraderArmorRack|TraderPoleArm|TraderBowRack|TraderQuiverRack|"
             r"OutdoorTraderHelmPoles|TraderClothesRack|TraderHelmShelf|TraderCrossedWeapons|TraderHanging|"
             r"TraderShelves|TraderShield)"),
    ("target", r"^(TargetBarrel|Dummy|StrawDummy)"),
    ("tool", r"^(BarrelWithTools|Mining|Anvil|Bellows|CinderBin|Cauldron|CauldronAnimated|Grindstone|Spinning)"),
    ("tomb", r"^(Tombstone|TombstoneReadable|LOTDTombstone|Cross\d|Coffin|Crypt$|Crypt\d)"),
    ("statue", r"^(Statue|MovableStatue|StatueVase|Monument|Obelisk|ObeliskPrimitive|DunMirMileStone|DunMirWolfStatue|"
               r"HorrendousStatue|Gargoyle|Column|CathedralColumn)"),
    ("water", r"^(WishingWell|Well$|Fountain|Dock|RopeBridge)"),
    ("crop", r"^(Garden|Windmill)"),
    ("hay", r"^(OgreStraw|Straw\d)"),
    ("log", r"^(ForestLog|Stump\d)"),
    ("bones", r"^(Skull|ArmBone|LegBone|OgreHutMeat|OgreHutCarcass|OgreMoundTusk|OgrePost|Bones)"),
    ("rock", r"^(CaveRocks|CaveBoulders|Rock\d|CaveRockPillar|SmallStalagmite|LargeStalagmite|SmallStoneBlock|Brick\d|"
             r"DunMirRocks|MineCrystal|PlantBarren)"),
    ("sign", r"^(Sign|PlankSign|WallSign|ClothSign|CrossroadArrow|MovableSign)"),
]
_FAM = [(f, re.compile(r)) for f, r in FAMILIES]
FAMS = [f for f, _ in FAMILIES] + ["other"]
LOOSE = re.compile(r"^(CaveRocksSmall|Straw\d|Skull|ArmBone|LegBone|Brick\d|OgreStraw|Garden|PlantBarren)")


def family(t):
    for f, rx in _FAM:
        if rx.match(t or ""): return f
    return "other"


def base(t):
    """A type without its number (Crate1 and Crate2 are one kind); a trader's awning's frame and cloths one kind."""
    if (t or "").startswith("TraderTent"): return "TraderTent"
    return re.sub(r"(\d+[a-hA-H]?|NE|NW|SE|SW|N|S|E|W)$", "", (t or "").replace("Immobile", "")) or t


def is_nature(t):
    return bool(NATURE.match(t or ""))


def piece(o):
    """Whether an object (a MapData object dict: type, cls, xtype) is a scene piece."""
    t = o.get("type") or ""
    cls = o.get("cls") or o.get("class") or ""
    if "MONSTER" in cls or "DOOR" in cls or "EXIT" in cls or "TRIGGER" in cls and not t.startswith("WishingWell"):
        return False
    if (o.get("xtype") or "DefaultXfer") not in ("DefaultXfer", "", None) and not t.startswith(("Chest", "DunMirChest",
                                                                                            "ChestUrchin", "StumpChest",
                                                                                            "SackChest", "Sign", "PlankSign")):
        return False
    if NATURE.match(t) or TRIVIAL.match(t): return False
    return True


def creature(o):
    cls = o.get("cls") or o.get("class") or ""
    return "MONSTER" in cls and not re.match(r"^(Bat|Rat|Frog|Bird|Fish|Firefly|Wisp|Imp|.*Spider)", o.get("type") or "")


def grow(pieces, seeds, link, radius):
    """The scene round seed points [(x, y)]: indices of `pieces` [(type, x, y)] grown by single linkage at `link` px
    from the seeds, kept within `radius` px of the seeds' middle."""
    if not seeds: return []
    cx = sum(x for x, _ in seeds) / len(seeds); cy = sum(y for _, y in seeds) / len(seeds)
    grid = {}
    for i, (_, x, y) in enumerate(pieces):
        grid.setdefault((int(x // link), int(y // link)), []).append(i)

    def near(x, y):
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                for j in grid.get((int(x // link) + a, int(y // link) + b), ()):
                    _, px, py = pieces[j]
                    if (px - x) ** 2 + (py - y) ** 2 <= link * link: yield j
    inside = lambda j: math.hypot(pieces[j][1] - cx, pieces[j][2] - cy) <= radius
    got, todo = set(), []
    for sx, sy in seeds:
        for j in near(sx, sy):
            if j not in got and inside(j): got.add(j); todo.append(j)
    while todo:
        i = todo.pop()
        for j in near(pieces[i][1], pieces[i][2]):
            if j not in got and inside(j): got.add(j); todo.append(j)
    return sorted(got)
