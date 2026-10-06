"""The exterior scene catalogue (2026-10-05 Greywatch playtest: "exterior objects are very random and purposeless
... instead of 3 crates and 2 barrels, try a cart, 2 barrels, a crate, a weapon stand, and a box ... a bandit camp, a
broken-down wagon with some goods, an outdoor sparring area for the guards ... give them a core identity with some
strategic built-in variance").

Every group of things on the outdoor ground is one of these themes. A theme is a little scene with a reason:
- `purpose`: what happened or happens there, in a sentence;
- where it belongs: `stand` "wall" (its back against a wall of one of the `walls` kinds: house, fence, masonry,
  martial, wild, cave) or "open" (free-standing); `places` it needs (any of: town, wild, road, square, gate, water,
  martial); `roles`, buildings it belongs beside (a sparring ring by the barracks, a midden behind the inn);
  `need`: True when it may stand only within `near` squares of one of those buildings; `sides` of that building
  (front, side, back: a midden behind, a market stall before); `biomes`;
- its pieces (`layouts`, one picked per scene): the first piece is the anchor; `must` pieces have to fit or nothing is
  laid; each piece stands at (along, out) px from the anchor's origin: along the wall or across the scene, and out
  from the wall or forward (toward the scene's front); `n` pieces in a row `step` px apart;
- its variance: one of the layouts; counts within ranges; types swapped among alternatives; pieces with a chance `p`;
  the whole layout mirrored; open scenes turned to face their road or their building, else any of the four ways;
- `orient` of a piece: "line" (a crate or rack lies along the scene's long line), "face" (a bench faces the scene's
  middle), "cot" (a bedroll's head away from the middle);
- `cap`: at most so many to a map (scaled with the map's open ground), `spacing` in squares from another of its
  `family`, `min_types` distinct kinds of thing (never a pile of one type), `tall` (kept off front walls: the camera
  looks over them), `clear`: a radius (px) round the origin kept open (a sparring ring's floor).

Westwood (corpus co-occurrence within 110 px): carts stand with barrels, apple crates, steel crates and racks; water
barrels by barrels and torch poles; armour racks in rows of two or three; target barrels in pairs; ore carts with
steel barrels, tools and shovels; milestones with small rocks; campfires ringed by eight small rocks at 22 px, seats at
55-65 px, pup tents 105-120 px out, the stores (cart, barrels in threes, steel crates) together on one side.
"""
from dataclasses import dataclass, field
from typing import Tuple

CRATES = ("Crate1", "Crate2", "DarkCrate1", "DarkCrate2")
DARK_CRATES = ("DarkCrate1", "DarkCrate2")
BARRELS = ("Barrel", "Barrel2", "Barrel")
BIG_BARRELS = ("LargeBarrel1", "LargeBarrel2", "PiledBarrels1", "PiledBarrels2")
SACKS = ("SackChestLarge1", "SackChestLarge2", "SackChestMedium1", "SackChestMedium2")
SMALL_SACKS = ("SackChestSmall1", "SackChestSmall2", "SackChestMedium1")
STEEL = ("BarrelSteel1", "BarrelSteel2", "CrateSteel1", "CrateSteel2")
STEEL_CRATES = ("CrateSteel1", "CrateSteel2")
TOOLS = ("BarrelWithTools1", "BarrelWithTools2")
LOGS = ("ForestLog01", "ForestLog02", "ForestLog04")
STUMPS = ("Stump1", "Stump2", "Stump9")
SEATS = ("Stump3", "Stump4", "Stump5", "Stump6")
HAY = ("OgreStraw1", "OgreStraw2", "OgreStraw3", "OgreStraw4", "OgreStraw5")
STRAW = ("Straw1", "Straw2")
RUBBLE = ("Brick0", "Brick1", "Brick2", "Brick3")     # (the ruins' column rubble stands in quest maps only)
ROCKS = ("CaveRocksLarge", "CaveRocksMedium", "CaveRocksMedium")
BIG_ROCKS = ("CaveRocksHuge", "CaveBoulders")
BONES = ("ArmBone", "LegBone", "Skull", "LegBone")
FUNGI = ("Mushroom1", "Mushroom2", "Mushroom3", "Mushroom4", "Mushroom5")
FERNS = ("PlantFern1", "PlantFern2", "Plant4", "FoliageDense1")
FLOWERS = ("FlowersWhiteSparse", "FlowersYellowSparse", "FlowersPurpleSparse")
RACKS = ("OutdoorTraderArmorRack1", "OutdoorTraderArmorRack3", "OutdoorTraderArmorRack5", "OutdoorTraderArmorRack2")
POLEARMS = ("TraderPoleArm1", "TraderPoleArm2")
TARGETS = ("TargetBarrel1", "TargetBarrel2")
STOOLS = ("Stool1", "Stool2", "Stool3")
GRAVES = ("Tombstone1", "Tombstone1", "Tombstone11", "Tombstone17", "Tombstone5")
PELTS = ("WolfPelt1", "WolfPelt2", "WolfPelt3", "WolfPelt4")
CRYSTALS = ("MineCrystal01", "MineCrystal02", "MineCrystal03", "MineCrystal04", "MineCrystal05")
TELESCOPES = ("Telescope1b", "Telescope1c")      # the ones Westwood's campaign maps place (1a: an arena map; 1e, 1g: none)
ALL = ("green", "ice", "lava", "cave", "swamp")
TOWNISH = ("green", "ice", "swamp")


def P(types, a=0, o=0, n=1, step=(22, 0), p=1.0, must=False, orient=None, ring=None):
    """A piece of a scene: `types` to pick from, at (a: along, o: out) px from the origin; n (or a range (lo, hi))
    pieces stepping `step` (along, out) px; chance p; must: the scene is not laid without it; ring=(r, k): k pieces
    round the origin at r px (stones round a fire)."""
    return dict(types=tuple(types), a=a, o=o, n=n, step=step, p=p, must=must, orient=orient, ring=ring)


@dataclass
class Theme:
    name: str
    purpose: str
    stand: str                                   # "wall" or "open"
    layouts: list
    walls: Tuple[str, ...] = ()                  # wall kinds a "wall" scene may stand against
    places: Tuple[str, ...] = ()                 # any of these (empty: anywhere its walls/roles allow)
    roles: Tuple[str, ...] = ()                  # buildings it belongs beside
    need: bool = False                           # only within `near` squares of one of `roles`
    near: int = 10
    sides: Tuple[str, ...] = ("front", "side", "back")
    biomes: Tuple[str, ...] = TOWNISH
    weight: float = 3.0
    cap: int = 2
    spacing: int = 24
    family: str = ""
    min_types: int = 3
    min_pieces: int = 4
    tall: bool = False
    clear: int = 0
    face: str = "any"                            # open scenes: "road" (back to the road), "any"
    min_share: float = 0.7                       # of the pieces it means to lay
    requires: Tuple[str, ...] = ()               # places it needs, all of them (a broken wagon: a road in the wild)
    size: int = 75                               # about how far its pieces reach from its anchor (px)
    scales: bool = False                         # its cap grows with the map's open ground (the wood's own heaps)
    mirror: bool = True
    house_roles: Tuple[str, ...] = ()           # a wall scene against a house only beside these roles (stone ones)
    culture: str = ""                            # a culture's own scene: laid only when the map names it
                                                 # (Exterior(culture=...): Starwell's wizards), never elsewhere
    loose: float = 0.0                           # px each piece (a row: its first) is set off its mark by hand
    loose_step: float = 0.0                      # a row's steps stretched or shrunk by up to this share, as it drifts
    archs: Tuple[str, ...] = ()                  # each layout's archetype (a lab or a design may ask for one)
    keep_layout: bool = False                    # its layout drawn once and kept until laid (the small layouts fit more
                                                 # easily: drawn afresh at every spot tried they win out of turn)
    screen: bool = False                         # an open scene drawn in the screen's own frame (o: down the screen,
                                                 # a: to the left), as Westwood's stand toward the camera (a well's sign)

    def __post_init__(self):
        self.family = self.family or self.name


def _shrine_layouts():
    """The shrine's layouts [(archetype, layout)], each as often as Westwood's (see the shrine theme). Every piece's
    step to its nearest along a screen diagonal or axis, as Westwood's (metrics diag: 1.0 of their steps; round 8's
    first try had wall torches 16 px nearer the wall than the statues, the steps between them 18-30 degrees off)."""
    out = []
    for k in ("a", "b", "c", "e", "g", "h"):
        out += [("castle_row", [P((f"Statue2{k}",), -97, 28, n=3, step=(97, 0), must=True),
                                P(("Torch",), -48, 21, n=2, step=(97, 0), must=True), P(("Torch",), 145, 21, p=0.4)])] * 4
        out += [("tight_row", [P((f"Statue2{k}",), -30, 28, n=3, step=(49, 0), must=True),
                               P(("CryptChest1",), -82, 34, p=0.8, orient="line"),
                               P(("Torch",), -64, 22, p=0.8), P(("Torch",), 104, 22, p=0.5),
                               P(("TorchPole",), -50, 44, p=0.6), P(("Monument1",), -116, 20, p=0.5)])] * 2
        out += [("alt_row", [P((f"Statue2{k}",), -92, 28, n=3, step=(92, 0), must=True),
                             P(("StatueVictory1SW",), -46, 22, n=2, step=(92, 0), must=True, orient="line"),
                             P(("Monument1",), -150, 20, p=0.8)])] * 2
        out += [("pair", lay) for lay in (
            [P((f"Statue2{k}",), -44, 30, n=2, step=(88, 0), must=True), P(("Torch",), 0, 22, p=0.4)],
            [P((f"Statue2{k}",), -24, 26, must=True), P(("StatueVictory1SW",), 24, 23, must=True, orient="line")],
            [P((f"Statue2{k}",), -60, 33, n=2, step=(118, 12), must=True),
             P(("CryptChest1",), 6, 52, must=True, orient="line")],
            [P((f"Statue2{k}",), -70, 34, n=2, step=(120, -6), must=True),
             P(("CryptChest1",), -34, 60, p=0.7, orient="line"), P(("Torch",), -6, 20, n=2, step=(46, 2), p=0.8)],
            [P((f"Statue2{k}",), -30, 24, n=2, step=(62, 12), must=True), P(("TorchPole",), -52, 42, must=True)])]
        out += [("lone", [P((f"Statue2{k}",), -12, 31, must=True), P(("Torch",), 12, 15, must=True)])] * 2
        out += [("lone", [P((f"Statue2{k}",), -9, 24, must=True), P(("TorchPole",), 9, 27, must=True)])] * 2
        out += [("lone", [P((f"Statue2{k}",), -21, 28, must=True), P(("DunMirFlameBasinLit",), 21, 22, must=True)])]
    # the crypt court (Con04b's: two or three sarcophagi side by side along the wall, a stone pillar hugging the wall at
    # either end ~105 px out, a cross before them, ~93 px out, or a statue among them, torch poles or a wall torch)
    out += [("crypt", [P(("Crypt1", "Crypt4"), -58, 50, must=True), P(("Crypt4", "Crypt2"), 0, 46, must=True),
                       P(("Crypt3",), 58, 52, p=0.7), P(("Cross2", "Statue2b", "Statue2d"), 0, 94, must=True),
                       P(("Monument1",), -106, 14, n=2, step=(212, 0), p=0.85),
                       P(("TorchPole",), -30, 26, n=2, step=(64, -4), p=0.5), P(("Torch",), 0, 13, p=0.4)])] * 30
    # the chapel nave (a roofless chapel: Con07B, War07A)
    out += [("nave", [P(("WhiteTapestry2", "WhiteTapestry2", "BlueTapestry2"), -120, 12, n=(2, 4), step=(60, 0),
                        must=True, orient="line"),
                      P(("Column8",), -60, 60, n=(1, 2), step=(110, 4), must=True), P(("Statue1a",), 40, 34, must=True),
                      P(("Candleabra5",), -160, 16, p=0.8), P(("Candleabra2",), 70, 22, p=0.5),
                      P(("Bench5",), 20, 82, n=(0, 3), step=(36, 8), orient="face")])] * 18
    return out


SHRINE_LAYOUTS = _shrine_layouts()


CATALOGUE = [
    # ---- the town's work and life --------------------------------------------------------------------------------
    Theme("cart_loading", "a cart drawn up beside a storehouse, its load stacked between it and the wall", "wall",
          [[P(("OutdoorTraderCart",), 0, 78, must=True), P(CRATES, -52, 30, n=(1, 2), step=(32, 0), must=True,
                                                            orient="line"),
            P(SACKS, 14, 30, n=(1, 2), step=(22, 4), must=True), P(BARRELS, 66, 30), P(BARRELS, 70, 58, p=0.6),
            P(("TraderAppleCrate",), -74, 62, p=0.5)],
           [P(("OutdoorTraderCart",), 0, 80, must=True), P(BIG_BARRELS, -44, 32, must=True),
            P(CRATES, -6, 30, must=True, orient="line"), P(("TraderAppleCrate",), 30, 30, n=(1, 2), step=(32, 0)),
            P(SMALL_SACKS, 96, 32, p=0.7)]],
          walls=("house",), roles=("store", "mill", "inn", "keep", "manor", "mess", "barracks", "townhall"), sides=("side", "back"),
          cap=2, spacing=30, size=100, family="cart", tall=True, weight=2.5),
    Theme("wagon_verge", "a wagon pulled off the road to rest the horse: barrels and a crate down at its tail, the "
          "carter's spear stood by, straw for the horse", "open",
          [[P(("OutdoorTraderCart",), 0, 0, must=True), P(BARRELS, -34, 44, n=2, step=(28, 8), must=True),
            P(CRATES, 34, 40, must=True, orient="line"), P(("TraderAppleCrate",), 70, 14, p=0.8),
            P(RACKS + POLEARMS, -66, 20, p=0.6, orient="line"), P(STRAW, 70, -10, p=0.6),
            P(("WaterBarrel",), 10, 80, p=0.4)]],
          places=("road",), size=100, cap=2, spacing=34, family="cart", face="road", weight=2.0),
    Theme("broken_wagon", "a wagon broken down by the road: a wheel off, its goods unloaded and left", "open",
          [[P(("OutdoorTraderCart",), 0, 0, must=True), P(("MineOreCartWheel",), -52, 14, must=True),
            P(CRATES, 36, 40, n=(1, 2), step=(32, 10), must=True, orient="line"),
            P(BARRELS, -24, 58, n=(1, 2), step=(-30, 16)), P(SACKS, 70, 84, n=(1, 2), step=(22, 14)),
            P(STRAW, -64, 46, p=0.5), P(("TraderAppleCrate",), 8, 80, p=0.5)]],
          places=("road",), requires=("road", "wild"), size=100, cap=1, spacing=60, family="cart", face="road", weight=1.5),
    Theme("market_stall", "a trader's awning with the wares set out before it", "open",
          # (the wares: the apple crates must stand, the rest where they fit: with every piece a must, the stall had laid
          # in none of the scene lab's market squares, 2026-10-06)
          # Westwood's (Con02a, Con03A, Con09d: an awning with barrels in twos and threes, a water barrel, a steel crate,
          # crates of apples, a torch pole or two, a cart now and then): the wares before it and at its ends, clear of
          # its cloths
          # three trades (the judge, 2026-10-06: "near-empty ... nothing says what is sold"): a provisioner (apples, a
          # knot of barrels, sacks, the cart), an armourer (racks and helm poles), a potion seller (Con03A's cauldron,
          # stool and ore cart); each with its stock in knots, not singles
          # (round 7, the judges: "four to seven pieces each standing alone a tile apart": Westwood's stalls hold five to
          # ten wares besides the awning, packed: barrels touching in a knot with the water barrel, apple crates side by
          # side and a second row, the steel crates together; every stock piece more often, set down by hand)
          [[P(("@tent",), 0, 0, must=True), P(("TraderAppleCrate",), -24, 60, n=(2, 3), step=(29, 4), must=True),
            P(("TraderAppleCrate",), -8, 90, n=(1, 2), step=(29, 3), p=0.6),
            P(("Barrel2", "Barrel"), -44, -80, n=(2, 3), step=(26, 4)),
            P(("Barrel2", "Barrel"), -31, -56, n=(1, 2), step=(26, -2), p=0.8), P(("WaterBarrel",), -76, -50, p=0.8),
            P(("CrateSteel3", "CrateSteel4"), 56, 66, n=(1, 2), step=(28, 6)),
            P(SACKS, 82, 98, n=(1, 3), step=(22, 8), p=0.7),
            P(("TorchPole",), 104, 30, p=0.7), P(("TorchPole",), -100, 52, p=0.3),
            P(("OutdoorTraderCart",), 150, -10, p=0.5)],
           [P(("@tent",), 0, 0, must=True),
            # (one rack, a second set off it, never three in a ruler line: the judge, 2026-10-06; Con09d's one rack
            # among its barrels and apple crates)
            P(("OutdoorTraderArmorRack1", "OutdoorTraderArmorRack2", "OutdoorTraderArmorRack3"), -66, 64, must=True),
            P(("OutdoorTraderArmorRack1", "OutdoorTraderArmorRack3"), -28, 100, p=0.6),
            P(("OutdoorTraderHelmPoles",), 70, 74, p=0.8),
            P(("Barrel2", "Barrel"), -40, -84, n=(3, 4), step=(26, 4)), P(("WaterBarrel",), -72, -58, p=0.7),
            P(("CrateSteel3", "CrateSteel4"), 98, 40, n=(1, 2), step=(26, 6), p=0.8),
            P(POLEARMS, 30, 104, p=0.4, orient="line"),
            P(("TorchPole",), -104, 40, p=0.7), P(("TorchPole",), 104, 36, p=0.3),
            P(("OutdoorTraderCart",), -150, 0, p=0.3)],
           [P(("@tent",), 0, 0, must=True), P(("CauldronAnimated",), -10, 70, must=True),
            P(("CushionedStool2",), 36, 92), P(("WaterBarrel",), -58, 58, p=0.8),
            P(("CrateSteel3", "CrateSteel4"), 60, 60, n=(1, 2), step=(26, 6)), P(SMALL_SACKS, 88, 36, p=0.5),
            P(("MineOreCart2",), -130, 20, p=0.6), P(("Barrel2", "Barrel"), -40, -84, n=(2, 3), step=(27, 3)),
            P(("TorchPole",), 104, 36, p=0.6), P(("Rock6",), 110, 100, p=0.4)]],
          roles=("store", "inn"), need=True, near=12, cap=1, spacing=40, family="stall", weight=1.2, size=170,
          min_types=3, loose=10, loose_step=0.15),
    Theme("supply_corner", "a household's stores kept outside the back door: barrels, a crate, sacks", "wall",
          [[P(BIG_BARRELS, -40, 30, must=True), P(CRATES, 2, 28, must=True, orient="line"), P(SACKS, 36, 30, must=True),
            P(BARRELS, 10, 68, p=0.6), P(TOOLS + ("TraderAppleCrate",), 72, 30, p=0.5)],
           [P(CRATES, 0, 28, must=True, orient="line"), P(SMALL_SACKS + SACKS, -36, 30, n=(1, 2), step=(-22, 8),
                                                           must=True),
            P(("WaterBarrel", "Barrel"), 40, 28, must=True), P(STOOLS, 8, 60, p=0.5), P(("TraderAppleCrate",), 80, 34, p=0.4)]],
          walls=("house",), sides=("side", "back"), places=("town",), cap=5, spacing=16, family="stores", weight=2.0),
    Theme("woodpile", "split logs stacked along the wall for the hearth, the block before them", "wall",
          [[P(LOGS, -30, 30, n=3, step=(30, 0), must=True), P(STUMPS, 6, 70, must=True),
            P(TOOLS + ("Barrel", "SackChestMedium1"), 66, 30, must=True), P(STRAW, -30, 64, p=0.4)]],
          walls=("house", "fence"), roles=("home", "cottage", "woodcutter", "inn", "mess", "bunkhouse", "grovelord",
                                           "barracks", "smithy", "fisher", "herbwife"),
          sides=("side", "back"), places=("town",), biomes=("green", "swamp", "ice"), cap=3, spacing=18, family="wood",
          tall=True, weight=2.0),
    Theme("chopping_yard", "where wood is split: the block, logs waiting, the tools", "open",
          [[P(STUMPS, 0, 0, must=True), P(LOGS, -46, 14, n=2, step=(0, 26), must=True), P(("ForestLog03",), 46, 24),
            P(TOOLS, 20, -40, must=True), P(STRAW, -14, 46, p=0.4)]],
          roles=("woodcutter", "home", "cottage", "grovelord"), places=("town",), biomes=("green", "swamp"), cap=2,
          spacing=26, family="wood", weight=1.5),
    Theme("hay_store", "hay heaped by a farmstead, sacks of feed", "wall",
          # Westwood's (Con08d, War03c, Wiz03a, Wiz03b: three to ten heaps of straw (OgreStraw1 most) spread along a wall
          # over ~90 px, a barrel or two, a torch, a rock): the heaps loose and many, the sacks now and then
          [[P(("OgreStraw1", "OgreStraw1", "OgreStraw2", "OgreStraw3"), -50, 34, n=(2, 4), step=(48, 8), must=True),
            P(("OgreStraw1",), -30, 76, p=0.5), P(("Barrel",), 120, 34, n=(1, 2), step=(26, 4), must=True),
            P(("SackChestLarge1", "SackChestLarge2"), 104, 70, p=0.35), P(("TorchPole",), -110, 44, p=0.35),
            P(("CaveRocksLarge", "CaveRocksHuge"), 150, 40, p=0.25)]],
          walls=("house", "fence"), roles=("mill", "home", "cottage", "grovelord", "barracks"), need=True, near=8,
          biomes=("green", "swamp"), cap=2, spacing=26, family="hay", tall=True, weight=1.5),
    Theme("midden", "the refuse heap behind a kitchen: old straw, bones, a broken crate", "wall",
          [[P(HAY, 0, 34, must=True), P(BONES, -34, 30, n=2, step=(-16, 18), must=True),
            P(DARK_CRATES, 40, 30, orient="line", must=True), P(("Barrel2",), 54, 68, p=0.7), P(("Spitoon",), -6, 66, p=0.6)]],
          walls=("house",), roles=("inn", "mess", "barracks", "bunkhouse", "keep", "home"), need=True, near=6,
          sides=("back", "side"), biomes=ALL, cap=2, spacing=40, family="midden", weight=2.0),
    Theme("smithy_yard", "the smith's yard: an anvil, the quench barrel, ore heaped, finished work racked", "wall",
          [[P(("Anvil1", "Anvil2"), 0, 58, must=True), P(("WaterBarrel",), 40, 40, must=True),
            P(("CaveRocksMedium", "CaveRocksLarge"), -42, 32, n=2, step=(-22, 10), must=True),
            P(TOOLS, 70, 30), P(POLEARMS, -88, 32, p=0.6, orient="line"), P(STOOLS, 26, 86, p=0.5)]],
          walls=("house",), roles=("smithy", "demon_forge"), need=True, near=6, sides=("side", "front", "back"),
          biomes=ALL, cap=2, spacing=30, family="smith", tall=True, weight=6.0),
    # the well alone, clear on every side, a public landmark near a road (Westwood's four campaign wells, Con02a, Con07B,
    # Con09a, War07A: the well and at most a sign a little apart; no barrels, buckets, benches or troughs by it. Westwood's
    # well is the WishingWell; the kit keeps its Well, the user has not chosen: rules/scenes/well.md)
    # (a sign a little apart in two of three: Con02a's SignIx, Con07B's and War07A's Sign1; the judge, 2026-10-06: "no
    # road or path, no sign")
    Theme("well_side", "a draw well where water is fetched, standing clear", "open",
          # (round 8: Westwood's four wells, rules/scenes/well.md, measured in the screen's own frame: the sign 50-56 px
          # before the well, straight down the screen (Con07B, War07A: -2, 56) or down and to the right (Con02a: 35,
          # 36), never behind it; one well bare (Con09a); one a market well (Con07B: the sign, and a street lamp 190 px
          # before it; its trader's racks stand inside the shop beside it, not round the well). Round 7's sign anywhere
          # round the well at 60-110 px read as "the same pair" with no reason to it; the layouts in Westwood's
          # frequencies)
          [[P(("Well",), 0, 0, must=True)],
           [P(("Well",), 0, 0, must=True), P(("Sign1",), 2, 56, must=True)],
           [P(("Well",), 0, 0, must=True), P(("Sign1",), -35, 36, must=True)],
           [P(("Well",), 0, 0, must=True), P(("Sign1",), 2, 56, must=True), P(("StreetLampOrnate3",), -4, 190, p=0.8)]],
          places=("town",), biomes=("green", "swamp", "ice"), cap=1, spacing=50, family="well", weight=0.8,
          min_types=1, min_pieces=1, clear=60, loose=4, screen=True),
    Theme("washing_place", "linen hung to dry by the water, the tub and baskets", "open",
          [[P(("TraderClothesRack1", "TraderClothesRack2"), 0, 0, must=True), P(("WaterBarrel",), 42, 22, must=True),
            P(SMALL_SACKS, -36, 24, n=(1, 2), step=(-20, 14), must=True), P(STOOLS, 20, 48), P(("Barrel2",), -56, -6, p=0.5)]],
          places=("water",), biomes=("green", "swamp"), cap=1, spacing=40, family="wash", weight=3.0),
    Theme("unhitched_cart", "a cart left for the night, the horse's hay and water by it, a sack of oats", "open",
          [[P(("OutdoorTraderCart",), 0, 0, must=True), P(HAY, -50, 34, must=True), P(("WaterBarrel",), 46, 30, must=True),
            P(("SackChestLarge1", "SackChestLarge2"), 10, 58, must=True), P(STRAW, -20, -44, p=0.5)]],
          places=("town",), biomes=("green", "swamp", "ice"), cap=2, spacing=30, family="cart", size=95, weight=1.2),
    Theme("timber_stack", "timber stacked for building work: trunks in a row, the saw-horse stump, the tool barrel",
          "open",
          [[P(LOGS, -30, 0, n=3, step=(30, 0), must=True), P(("ForestLog03",), -10, -40), P(STUMPS, 20, 40, must=True),
            P(TOOLS, 60, 34, must=True)]],
          places=("town",), biomes=("green", "swamp", "ice"), cap=1, spacing=50, family="timber", weight=1.0),
    # ---- the garrison --------------------------------------------------------------------------------------------
    Theme("sparring_ring", "the guards' sparring ground: dummies to strike, racks of practice arms, a bench for the "
          "watchers and their water", "open",
          [[P(TARGETS, -36, 40, must=True), P(TARGETS, 36, 40, must=True),
            P(RACKS, -44, 86, n=2, step=(40, 0), must=True), P(POLEARMS, 58, 86, orient="line"),
            P(("Bench1", "Bench2", "Bench4", "Bench5"), 0, -80, orient="face"), P(("WaterBarrel",), 40, -74),
            P(("TraderQuiverRack",), -46, -70, p=0.5), P(STRAW, -80, 20, p=0.4)],
           [P(TARGETS, -34, 50, n=3, step=(34, 0), must=True), P(RACKS, -82, 30, must=True),
            P(RACKS + POLEARMS, 82, 30, must=True, orient="line"), P(("Bench1", "Bench2", "Bench4", "Bench5"), -20, -76,
                                                                      orient="face"),
            P(("WaterBarrel", "Barrel"), 24, -78)]],
          places=("martial",), roles=("barracks", "keep"), biomes=ALL, cap=2, spacing=34, size=110, family="arms", clear=40,
          weight=4.0, min_pieces=5),
    Theme("watch_fire", "a brazier in the open where the off-watch warm themselves, benches drawn up to it", "open",
          [[P(("Brazier",), 0, 0, must=True), P(("Bench1", "Bench2", "Bench4", "Bench5"), -50, 20, orient="face",
                                                 must=True),
            P(("Bench1", "Bench2", "Bench4", "Bench5"), 46, 26, orient="face"), P(("WaterBarrel", "Barrel"), 0, 56,
                                                                                    must=True),
            P(POLEARMS, 4, -54, orient="line", p=0.6)]],
          places=("martial",), biomes=ALL, cap=2, spacing=36, family="watchfire", weight=1.5, min_pieces=3),
    Theme("archers_mark", "a straw mark set up for the bowmen, their bows racked and quivers ready", "open",
          [[P(TARGETS, 0, 0, must=True), P(STRAW + HAY, 0, 30, must=True), P(("TraderBowRack2", "TraderBowRack1"), -30,
                                                                              -96, must=True),
            P(("TraderQuiverRack",), 14, -98, must=True), P(TARGETS, 40, 6, p=0.5)]],
          places=("martial",), roles=("barracks", "keep"), biomes=ALL, cap=1, spacing=40, family="archery", size=100,
          weight=1.2),
    Theme("guard_post", "a sentry's post: the brazier he warms his hands at, his stool, his spear, his water", "wall",
          [[P(("Brazier",), 0, 36, must=True), P(STOOLS, -30, 34, must=True), P(POLEARMS, -64, 30, orient="line"),
            P(("WaterBarrel", "Barrel"), 34, 30, must=True), P(("TraderQuiverRack",), 58, 36, p=0.5),
            P(DARK_CRATES, 40, 70, p=0.4, orient="line")]],
          walls=("martial", "masonry"), places=("gate", "martial"), biomes=ALL, cap=3, spacing=22, family="post",
          tall=True, weight=3.0),
    Theme("arms_store", "the garrison's spare arms stood against the wall", "wall",
          [[P(POLEARMS, 0, 32, must=True, orient="line"), P(("TraderBowRack2", "TraderBowRack1"), -48, 32),
            P(RACKS, 48, 34, must=True), P(("TraderQuiverRack",), 78, 38, p=0.6), P(DARK_CRATES, -88, 30, orient="line")]],
          walls=("house", "martial"), roles=("barracks", "keep"), places=("martial",), biomes=ALL, cap=2,
          spacing=30, family="arms", tall=True, weight=2.0),
    Theme("masons_work", "masons mending the wall: cut blocks stacked ready, the old stone broken out, the pick, "
          "the tool barrel and the mortar crate", "wall",
          [[P(("SmallStoneBlock",), -14, 30, n=2, step=(28, 0), must=True), P(RUBBLE, -48, 28, n=2, step=(-20, 12),
                                                                              must=True),
            P(("MiningPickAxeInGround1", "MiningPickAxeInGround2"), 6, 66, must=True), P(TOOLS, 46, 30, must=True),
            P(DARK_CRATES, 86, 34, orient="line", must=True), P(RUBBLE, 34, 62, p=0.5)]],
          walls=("masonry", "martial"), biomes=ALL, cap=1, spacing=50, family="mason", weight=1.0, min_types=4,
          min_pieces=6),
    Theme("archery_butts", "the garrison's butts: straw targets against the wall, the shooting line marked by "
          "the bow rack and the quivers", "wall",
          [[P(TARGETS, -34, 32, n=3, step=(34, 0), must=True), P(STRAW + HAY, -70, 36, p=0.7),
            P(STRAW, 70, 34, p=0.6), P(("TraderBowRack2", "TraderBowRack1"), -30, 120, must=True),
            P(("TraderQuiverRack",), 14, 122, must=True), P(("Barrel",), 44, 118, p=0.6)]],
          walls=("martial", "masonry"), places=("martial",), roles=("barracks", "keep"), biomes=ALL, cap=1,
          spacing=40, family="archery", weight=2.5, min_pieces=5, size=120),
    Theme("firewood_cart", "a cart of firewood come in for the kitchen fires, the logs being stacked off it", "wall",
          [[P(("OutdoorTraderCart",), 0, 80, must=True), P(LOGS, -44, 30, n=2, step=(30, 0), must=True),
            P(STUMPS, 26, 34, must=True), P(TOOLS, 52, 56, p=0.7), P(STRAW, -60, 66, p=0.4)]],
          walls=("house",), roles=("keep", "inn", "barracks", "mess", "manor", "chapel", "village_chapel"), places=("town",),
          sides=("side", "back"), biomes=("green", "swamp", "ice"), cap=1, spacing=40, size=100, family="wood", tall=True,
          weight=1.5),
    Theme("drying_line", "washing hung out to dry against the house, the basket and the tub beside it", "wall",
          [[P(("TraderClothesRack1", "TraderClothesRack2"), 0, 40, must=True), P(SMALL_SACKS, -40, 30, must=True),
            P(("WaterBarrel",), 40, 30, must=True), P(STOOLS, 18, 70, p=0.6)]],
          walls=("house",), roles=("home", "cottage", "inn", "fisher", "herbwife"), need=True, near=4,
          sides=("side", "back"), biomes=("green", "swamp"), cap=2, spacing=36, family="wash", tall=True, weight=1.2),
    Theme("loafers_bench", "a bench against the wall in the sun, a barrel for a table, a stool pulled up", "wall",
          [[P(("Bench1", "Bench2", "Bench4", "Bench5"), 0, 34, orient="out", must=True), P(BARRELS, 40, 34, must=True),
            P(STOOLS, 44, 66, must=True), P(("TraderAppleCrate", "SackChestSmall1"), -40, 32, p=0.5)]],
          walls=("house",), roles=("inn", "store", "home", "barracks", "mess", "fisher", "townhall"), places=("town",),
          sides=("front", "side"), biomes=ALL, cap=3, spacing=24, family="bench", weight=1.5, min_pieces=3),
    # ---- the road and the wilds ------------------------------------------------------------------------------------
    # Westwood's waystones (Con03A, War03a): two to four milestones (DunMirMileStone) in a row along a screen diagonal,
    # 30-45 px apart, an altar stone (DunMirAltar2) at the row's end, a second now and then; no offerings
    Theme("waystone", "waystones in a row by the way, an altar stone at its end", "open",
          [[P(("DunMirAltar2",), 0, 0, must=True), P(("DunMirMileStone",), 32, 0, n=(2, 4), step=(32, 1), must=True),
            P(("DunMirAltar2",), 150, 2, p=0.3)],
           [P(("DunMirMileStone",), 0, 0, n=2, step=(62, 0), must=True), P(("DunMirAltar2",), 31, -4, must=True)]],
          places=("road",), requires=("road", "wild"), biomes=("green", "swamp", "ice"), cap=2, spacing=50, family="stone", face="road",
          weight=1.5, min_types=2, min_pieces=3),
    # no candles outdoors: the player can pick them up (Starwell playtest, 2026-10-05); torch poles light a shrine.
    # Westwood's (Con04b, Con05A, Con07C, War03c, War04b, Wiz02B, 28 scenes): statues of one kind, three in a row along a
    # screen diagonal ~49 px apart (or two ~160 px apart flanking a way), a torch pole by them, a pair of stone pillars
    # (Monument1) ~100 px either side of a lone statue; flowers never
    Theme("shrine", "a shrine against a wall: statues of one kind in a row, a torch pole by them", "wall",
          # (round 8, the judges on round 7: "the same statue, torch pole and obelisk trio every time". Westwood's 26
          # shrines against walls clustered by their pieces, each layout as often as Westwood's (rules/scenes/shrine.md
          # "Structures", measured from the wall's centre line: statues 16-51 px out, median 29; the stone pillars
          # hugging the wall, 11-22; wall torches 10-20; torch poles 20-47; sarcophagi 41-67; benches 67-121):
          #   castle row 4 (Con07C, Wiz02B: three statues ~97 px apart, wall torches between them);
          #   tight row 2 (Con04b: three ~49 px apart, a chest at one end, wall torches and a torch pole, a pillar);
          #   alternating row 2 (Con04b: three statues ~92 px apart, victory statues between, a pillar at one end);
          #   pair 5 (Con04b, Con05A, War04a, War04b: two statues 48-88 px apart, now and then a crypt chest or a
          #   torch);
          #   lone statue 5 (a wall torch beside it 2, a torch pole 2: War03c, a flame basin 1: Con07E);
          #   crypt court 5 (Con04b: sarcophagi along the wall, pillars at both ends, a cross before them);
          #   chapel nave 3 (Con07B, War07A: tapestries on the wall, columns, candelabra, a statue, benches facing it)
          [lay for _, lay in SHRINE_LAYOUTS], archs=tuple(arch for arch, _ in SHRINE_LAYOUTS),
          # (Westwood's stand against a castle's or a town's walls: 0.94 of their pieces within two cells of one)
          # (masonry, a castle's walls, or a stone house: the judge, 2026-10-06, "set against wooden peasant cabins")
          walls=("masonry", "martial", "house"), sides=("side", "back", "front"), places=("wild", "town"),
          house_roles=("chapel", "village_chapel", "shrine", "mausoleum", "keep", "manor", "townhall", "barracks", "tower",
                       "gatehouse", "gaol", "observatory"),
          roles=("chapel", "village_chapel"), biomes=("green", "swamp", "ice"), cap=1, spacing=50,
          family="shrine", weight=0.8, min_types=2, min_pieces=2, tall=True, loose=2, loose_step=0.04,
          keep_layout=True),
    Theme("graveside", "a few graves at the wood's edge, headstones in a row, flowers laid before them, an urn, a "
          "torch pole at the end of the row", "open",
          [[P(GRAVES, -48, 0, n=3, step=(48, 0), must=True), P(FLOWERS, -48, 34, n=3, step=(48, 0), p=0.8),
            P(("TorchPole",), 92, 10, must=True), P(("StatueVase1S", "StatueVase2S"), -96, 12, p=0.6)]],
          roles=("chapel", "village_chapel"), need=True, near=16, biomes=("green", "swamp", "ice"), cap=1, spacing=60, family="grave",
          weight=1.0, min_types=2),
    Theme("hunters_rack", "a hunter's drying frame, hides pegged out, the seat where he scrapes them", "wall",
          [[P(("TraderClothesRack1", "TraderClothesRack2"), 0, 42, must=True), P(PELTS, -30, 80, n=2, step=(58, 0),
                                                                                   must=True),
            P(SEATS, 54, 36, must=True), P(("Barrel",), -50, 34, p=0.7), P(LOGS, 74, 72, p=0.4)]],
          walls=("wild",), places=("wild",), biomes=("green", "swamp", "ice"), cap=2, spacing=50, family="hunt",
          tall=True, weight=0.9),
    # seats round a fire are logs, benches and stools, never stumps (Starwell playtest, 2026-10-05: "the stumps around
    # the fires in bandit camps arent the right object for that use case"; Westwood: Stool1 59 px out, ogres' benches)
    Theme("campfire_logs", "a cold fire pit ringed with stones where woodsmen sit on logs", "open",
          [[P(("CampFireUnused",), 0, 0, must=True), P(("CaveRocksSmall",), ring=(22, 6), must=True),
            P(LOGS, 0, 64, must=True), P(LOGS, -62, -20, must=True), P(STOOLS, 56, -30, p=0.7),
            P(SMALL_SACKS, -46, 52, p=0.5)]],
          places=("wild",), biomes=("green", "swamp", "ice"), cap=2, spacing=50, family="fire", weight=0.8,
          min_types=3, clear=0),
    Theme("felling", "a stretch where trees were felled: fresh stumps, a trunk waiting to be hauled, the tools", "open",
          [[P(("ForestLog03",), 0, 0, must=True), P(STUMPS, -40, 30, n=2, step=(26, 22), must=True),
            P(STUMPS, 46, -20), P(TOOLS, 30, 40, must=True), P(LOGS, -36, -34, p=0.6)]],
          places=("wild",), biomes=("green", "swamp"), cap=2, spacing=40, family="fell", weight=0.8),
    # the wood's own heaps (the forest's floor, not people's things; they read as nature)
    Theme("deadfall", "a fallen trunk rotting at the wood's edge, fungi on it, a stump", "wall",
          [[P(LOGS, 0, 34, must=True), P(FUNGI, -26, 26, n=2, step=(14, 10), must=True), P(STUMPS, 36, 40),
            P(FERNS, -8, 62, must=True)]],
          walls=("wild",), biomes=("green", "swamp"), cap=14, spacing=12, family="log", weight=3.0, scales=True),
    Theme("boulders", "a rockfall at the foot of the wood, ferns grown through it", "wall",
          [[P(BIG_ROCKS, 0, 32, must=True), P(ROCKS, -30, 26, n=2, step=(-14, 16), must=True), P(FERNS, 30, 44, must=True),
            P(("CaveRocksSmall",), 8, 62, n=2, step=(16, 6))]],
          walls=("wild",), biomes=("green", "swamp"), cap=14, spacing=12, family="rock", weight=3.0, scales=True),
    Theme("glade_log", "an old trunk lying in the grass, fungi and ferns round it", "open",
          [[P(LOGS, 0, 0, must=True), P(FUNGI, -24, 18, n=2, step=(14, 8), must=True), P(FERNS, 30, -14, must=True)]],
          places=("wild",), biomes=("green", "swamp"), cap=10, spacing=12, family="log", weight=2.0, scales=True, min_pieces=3),
    Theme("glade_rock", "a boulder in the grass with smaller stones round it", "open",
          [[P(BIG_ROCKS, 0, 0, must=True), P(ROCKS, -26, 14, n=2, step=(-12, 14), must=True), P(FERNS, 26, 16, must=True),
            P(("CaveRocksSmall",), 6, -30)]],
          places=("wild",), biomes=("green", "swamp"), cap=10, spacing=12, family="rock", weight=2.0, scales=True),
    # ---- a wizards' town (culture "wizard": Starwell) ---------------------------------------------------------------
    Theme("alchemists_yard", "the alchemist's yard: the brewing kettle against the wall, sacks of herbs and roots, the "
          "water barrel, a crate of empty flasks, the stool she sits on to stir", "wall",
          [[P(("Cauldron",), 0, 40, must=True), P(SMALL_SACKS, -38, 30, n=(1, 2), step=(-20, 12), must=True),
            P(("WaterBarrel",), 40, 30, must=True), P(DARK_CRATES, 80, 34, orient="line", p=0.8),
            P(STOOLS, 6, 78, p=0.6)]],
          walls=("house",), roles=("apothecary", "herbwife", "college"), need=True, near=6, sides=("side", "back"),
          biomes=("green",), cap=2, spacing=30, family="brew", tall=True, weight=3.0, culture="wizard"),
    Theme("stargazers_post", "a stargazer's post: the telescope on its stand turned to the sky, a bench for the night's "
          "watch, the crate the charts are kept in, a candle", "open",
          [[P(TELESCOPES, 0, 0, must=True), P(("Bench1", "Bench2", "Bench4", "Bench5"), -8, 62, orient="face", must=True),
            P(DARK_CRATES, 46, 24, orient="line", must=True), P(("TorchPole",), -48, 20, p=0.5),
            P(("CaveRocksSmall",), 30, -30, p=0.4)]],
          places=("town", "wild"), roles=("college", "observatory"), biomes=("green",), cap=2, spacing=40,
          family="stars", weight=1.5, min_types=3, min_pieces=3, culture="wizard"),
    Theme("star_shards", "shards of the fallen star broken up through the turf round a boulder, as they lie all "
          "through the wood", "open",
          [[P(BIG_ROCKS, 0, 0, must=True), P(CRYSTALS, -28, 14, n=2, step=(-12, 16), must=True),
            P(CRYSTALS, 28, 18, must=True), P(("CaveRocksSmall", "CaveRocksMedium"), 6, -30, p=0.7)]],
          places=("wild",), biomes=("green",), cap=6, spacing=14, family="crystal", weight=1.6, scales=True,
          min_types=2, culture="wizard"),
    Theme("shard_wall", "star crystals grown out of the rock at the wood's foot, stones fallen round them", "wall",
          [[P(CRYSTALS, 0, 30, must=True), P(CRYSTALS, -30, 34, p=0.7), P(ROCKS, 30, 30, must=True),
            P(FERNS, -8, 62, must=True)]],
          walls=("wild",), biomes=("green",), cap=6, spacing=14, family="crystal", weight=1.6, scales=True,
          min_types=3, culture="wizard"),
    # ---- a farming town's (Harrowby, culture "farm"): the harvest brought in -------------------------------------
    Theme("threshing_floor", "where the sheaves are threshed: the straw heaped, the grain sacked in a row, the flails "
          "and forks in the tool barrel", "open",
          [[P(HAY, 0, 0, must=True), P(HAY, 44, 12, p=0.7), P(SACKS, -24, 52, n=(2, 3), step=(26, 6), must=True),
            P(TOOLS, 62, -24, must=True), P(STRAW, -54, -8, p=0.5)]],
          places=("town",), biomes=("green",), cap=3, spacing=26, family="harvest", weight=2.0, culture="farm"),
    Theme("harvest_wain", "a wain come in from the fields: the hay it brought heaped by it, the grain sacks unloaded, "
          "apples from the orchard", "open",
          [[P(("OutdoorTraderCart",), 0, 0, must=True), P(HAY, -54, 30, must=True),
            P(SACKS, 18, 52, n=(2, 3), step=(24, 6), must=True), P(("TraderAppleCrate",), 64, 18, p=0.7),
            P(TOOLS, -14, -48, p=0.5)]],
          places=("town", "road"), biomes=("green",), cap=2, spacing=34, family="cart", face="road", size=100,
          weight=1.5, culture="farm"),
    Theme("windmill", "a little wind-mill pumping by the fields, the sacks waiting at its foot", "open",
          [[P(("Windmill2",), 0, 0, must=True), P(SACKS, -40, 34, n=2, step=(-22, 8), must=True),
            P(HAY, 42, 30, must=True), P(TOOLS, 6, 64, p=0.6)]],
          places=("town", "wild"), biomes=("green",), cap=2, spacing=50, family="windmill", weight=1.0,
          culture="farm"),
    # ---- the ogres' (culture "ogre", by their lair: Westwood's ogre village, Con05B) --------------------------------
    Theme("ogre_midden", "the ogres' refuse: old straw, gnawed bones, a carcass picked clean, a broken barrel", "open",
          [[P(HAY, 0, 0, must=True), P(BONES, -34, 22, n=2, step=(-16, 18), must=True),
            P(("OgreHutCarcass", "OgreHutCarcassBig"), 36, 16, must=True), P(("Barrel2",), 10, 54, p=0.6)]],
          roles=("ogre_keep",), need=True, near=24, biomes=ALL, cap=4, spacing=16, family="ogre", weight=4.0,
          culture="ogre"),
    Theme("ogre_cookpit", "a cold cooking pit where the ogres roast what they take: stools round it, meat waiting, bones",
          "open",
          [[P(("OgreFirePitUnlit",), 0, 0, must=True), P(("OgreStool1", "OgreStool2"), -62, 12, must=True),
            P(("OgreStool1", "OgreStool2"), 54, 34, p=0.7), P(("OgreHutMeat",), 12, 60, must=True),
            P(BONES, 44, -40, n=(1, 2), step=(16, -10))]],
          roles=("ogre_keep",), need=True, near=24, biomes=ALL, cap=3, spacing=20, family="ogre", weight=3.0,
          culture="ogre"),
    # ---- caves and mines -----------------------------------------------------------------------------------------
    Theme("mine_cache", "an ore cart left by the wall with the miners' steel crates, tools and a spare wheel", "wall",
          [[P(("MineOreCart1", "MineOreCartBroken1"), 0, 38, must=True), P(STEEL_CRATES, -50, 28, must=True,
                                                                         orient="line"),
            P(("BarrelSteel1", "BarrelSteel2"), 52, 26, n=(1, 2), step=(26, 10), must=True),
            P(("MiningShovelInGround", "MiningPickAxeInGround1"), 18, 70), P(("MineOreCartWheel",), -26, 64, p=0.6)]],
          walls=("house", "cave"), places=("town",), biomes=("cave", "lava"), cap=3, spacing=30, family="cart",
          tall=True, weight=2.5),
    Theme("mine_stores", "the miners' stores: steel barrels, a tool barrel, sacks", "wall",
          [[P(STEEL_CRATES, 0, 28, must=True, orient="line"), P(("BarrelSteel1", "BarrelSteel2"), -40, 28, n=2,
                                                                 step=(-24, 12), must=True),
            P(TOOLS, 40, 28, must=True), P(SMALL_SACKS, 14, 62, p=0.6)]],
          walls=("house",), places=("town",), biomes=("cave", "lava"), cap=4, spacing=18, family="stores", weight=2.0),
    Theme("pillars", "rock pillars standing out from the cave wall, fallen stone at their feet", "wall",
          [[P(("CaveRockPillarShort1", "CaveRockPillarShort2", "CaveRockPillarTall1"), 0, 32, must=True),
            P(ROCKS, -34, 26, n=2, step=(-14, 14), must=True), P(("SmallStalagmite",), 30, 44, must=True),
            P(("Mushroom3",), -10, 60, n=2, step=(16, 6))]],
          walls=("wild", "cave"), biomes=("cave",), cap=16, spacing=10, family="pillar", tall=True, weight=3.0, scales=True),
    Theme("stalagmites", "stalagmites grown up from the cave floor", "open",
          [[P(("LargeStalagmite", "SmallStalagmite"), 0, 0, must=True), P(("SmallStalagmite",), -26, 18, n=2,
                                                                          step=(-10, 14), must=True),
            P(ROCKS, 24, -18, must=True), P(BONES, 30, 30, p=0.5)]],
          places=("wild", "town"), biomes=("cave",), cap=12, spacing=10, family="pillar", weight=2.0, scales=True, min_types=2),
    Theme("remains", "the bones of something that died here, a rock it lay against", "open",
          [[P(BIG_ROCKS, 0, 0, must=True), P(BONES, -24, 20, n=3, step=(12, 10), must=True),
            P(("CaveRocksSmall", "CaveRocksMedium"), 26, -16, must=True)]],
          places=("wild",), biomes=("cave", "lava", "ice", "swamp"), cap=6, spacing=24, family="bones", weight=1.0, scales=True,
          min_types=3),
    Theme("bonepile", "a beast's leavings against the rock: bones round a boulder", "wall",
          [[P(BIG_ROCKS, 0, 30, must=True), P(BONES, -30, 36, n=3, step=(12, 10), must=True),
            P(("CaveRocksMedium",), 30, 30, must=True), P(BONES, 24, 58, p=0.5)]],
          walls=("wild", "cave"), biomes=("cave", "lava", "ice", "swamp"), cap=8, spacing=22, family="bones",
          weight=1.5, scales=True),
    # ---- fire and ice ---------------------------------------------------------------------------------------------
    Theme("ashheap", "a grate of embers against the rock, slag and bones raked round it", "wall",
          [[P(("FireGrate",), 0, 46, must=True), P(RUBBLE, -34, 26, n=2, step=(-16, 14), must=True),
            P(ROCKS, 36, 30, must=True), P(BONES, 10, 74, p=0.6)]],
          walls=("wild", "cave"), biomes=("lava",), cap=10, spacing=14, family="fire", weight=3.0, scales=True),
    Theme("cinders", "a fire grate in the open, cinder rocks and bones about it", "open",
          [[P(("FireGrate",), 0, 0, must=True), P(ROCKS, -34, 14, n=2, step=(-12, 14), must=True),
            P(BONES, 30, 24, n=2, step=(10, 12), must=True), P(RUBBLE, 0, -34)]],
          places=("wild", "town"), biomes=("lava",), cap=8, spacing=14, family="fire", weight=2.0, scales=True),
    Theme("frost", "a boulder frozen into the snow at the wall's foot, the ice cracked round it", "wall",
          [[P(BIG_ROCKS, 0, 30, must=True), P(ROCKS, -32, 28, must=True),
            P(("IceCrack2", "IceCrack4", "IceCrack6"), 26, 64, must=True), P(BONES, 34, 34, p=0.6)]],
          walls=("wild",), biomes=("ice",), cap=12, spacing=12, family="rock", weight=3.0, scales=True),
    Theme("snowrock", "a boulder out on the snow, stones and cracked ice by it", "open",
          [[P(BIG_ROCKS, 0, 0, must=True), P(ROCKS, -28, 14, n=2, step=(-12, 14), must=True),
            P(("IceCrack2", "IceCrack4", "IceCrack6"), 30, 30, must=True)]],
          places=("wild", "town"), biomes=("ice",), cap=10, spacing=12, family="rock", weight=2.0, scales=True, min_pieces=3),
]
THEMES = {t.name: t for t in CATALOGUE}

# what the buildings call for first (the purpose pass): role -> [(theme, chance)]
ROLE_SCENES = {
    "barracks": [("sparring_ring", 0.9), ("arms_store", 0.6), ("midden", 0.5)],
    "keep": [("cart_loading", 0.6), ("arms_store", 0.4), ("midden", 0.4)],
    "smithy": [("smithy_yard", 1.0)],
    "demon_forge": [("smithy_yard", 0.8)],
    "inn": [("midden", 0.8), ("cart_loading", 0.6), ("market_stall", 0.3)],
    "store": [("market_stall", 0.6), ("cart_loading", 0.5)],
    "mill": [("hay_store", 0.8), ("cart_loading", 0.6), ("threshing_floor", 0.6), ("windmill", 0.5)],
    "woodcutter": [("chopping_yard", 0.9)],
    "home": [("woodpile", 0.3), ("supply_corner", 0.3)],
    "cottage": [("hay_store", 0.3), ("supply_corner", 0.3)],
    "grovelord": [("chopping_yard", 0.5), ("hay_store", 0.4)],
    "chapel": [("graveside", 0.5), ("shrine", 0.5)],
    "village_chapel": [("graveside", 0.5), ("shrine", 0.5)],
    "mess": [("midden", 0.7), ("cart_loading", 0.5)],
    "bunkhouse": [("woodpile", 0.5), ("mine_stores", 0.5)],
    "ore_shed": [("mine_cache", 0.9)],
    "foreman": [("mine_stores", 0.6)],
    "manor": [("cart_loading", 0.6), ("well_side", 0.4)],
    # a shore town's (Ambermere, 2026-10-05: its fishers' houses, the herbwife's hut and the moot hall had called for
    # nothing, and stood bare among the town's scenes)
    "fisher": [("drying_line", 0.7), ("woodpile", 0.5), ("supply_corner", 0.4)],
    "herbwife": [("drying_line", 0.6), ("woodpile", 0.4)],
    "townhall": [("cart_loading", 0.5), ("loafers_bench", 0.6)],
    "college": [("stargazers_post", 0.8), ("cart_loading", 0.4)],
    "apothecary": [("alchemists_yard", 1.0)],
    "observatory": [("stargazers_post", 0.7)],
    # the ogres' lair (Harrowby's hill-fort; a biome map's ogre keep took none, AMR-5)
    "ogre_keep": [("ogre_midden", 0.9), ("ogre_cookpit", 0.8)],
}

# at most so many scenes of a family to a map, whatever their themes (carts are memorable: a few to a map)
FAMILY_CAP = {"cart": 3, "arms": 3, "wood": 3, "stores": 5, "bones": 6}

# families whose things already on the map (a camp's cart, the training ground's targets, a woodpile by a door)
# count as one of the family for spacing
FAMILY_SIGNS = {"cart": ("OutdoorTraderCart", "MineOreCart"), "arms": ("TargetBarrel", "OutdoorTraderArmorRack"),
                "wood": ("ForestLog03",), "fire": ("CampFire",), "well": ("Well",), "stall": ("TraderTent",),
                "stone": ("DunMirMileStone",), "grave": ("Tombstone", "Cross"), "post": ("Brazier",)}

# a trader's awning (Westwood's TraderTent kit, measured on Con02a, Con03A, Con04a and War05A): the pieces' offsets
# (px) from the front side. "DN" runs back toward the upper left, "UP" toward the upper right; colours as Westwood
# pairs them with each way.
TENT = {"DN": [("TraderTentShadowDN1", -22, 11), ("TraderTentShadowDN2", -79, -42), ("TraderTentShadowDN3", -124, -90),
               ("TraderTentPoleDN1", -83, -40), ("TraderTentPoleDN2", -28, -92), ("{c}Top2", -82, -53),
               ("{c}Top1", -19, 8), ("{c}FrontSide", 0, 0), ("{c}BackSide", -117, -118)],
        "UP": [("TraderTentShadowUP1", -6, 9), ("TraderTentShadowUP2", 45, -46), ("TraderTentShadowUP3", 89, -95),
               ("TraderTentPoleUP1", 88, -39), ("TraderTentPoleUP2", 35, -96), ("{c}Top2", 96, -60),
               ("{c}Top1", 33, 1), ("{c}FrontSide", 0, 0), ("{c}BackSide", 119, -114)]}
TENT_COLOURS = {"DN": ("TraderTentRed&Blue", "TraderTentYellow&Green"),
                "UP": ("TraderTentPurple&Orange", "TraderTentGreen&Red")}
# the awning's middle, from its front side; a tent is laid by its middle
TENT_MID = {"DN": (-60, -58), "UP": (60, -57)}


def tent_pieces(way, colour, cx, cy):
    """The pieces of a trader's awning whose middle is at (cx, cy) px: [(type, x, y)]."""
    mx, my = TENT_MID[way]
    return [(t.format(c=colour), cx - mx + dx, cy - my + dy) for t, dx, dy in TENT[way]]


# which crate, rack or bench of a family lies along a line that runs this way on screen ("\\" or "/")
ALONG = {"\\": {"Crate1": "Crate1", "Crate2": "Crate1", "DarkCrate1": "DarkCrate1", "DarkCrate2": "DarkCrate1",
                "CrateSteel1": "CrateSteel1", "CrateSteel2": "CrateSteel1",
                "TraderPoleArm1": "TraderPoleArm1", "TraderPoleArm2": "TraderPoleArm2"},
         "/": {"Crate1": "Crate2", "Crate2": "Crate2", "DarkCrate1": "DarkCrate2", "DarkCrate2": "DarkCrate2",
               "CrateSteel1": "CrateSteel2", "CrateSteel2": "CrateSteel2",
               "TraderPoleArm1": "TraderPoleArm3", "TraderPoleArm2": "TraderPoleArm4"}}
# pieces a wall scene stands on its back wall, by the line the wall runs (a "\\" wall: the room's NE wall, the piece
# below and left of it; "/": the NW wall, below and right; furnish.WALL_SIDE_TYPE; Westwood's victory statues face out
# from their wall, its tapestries hang 2 on a "/" wall)
for _l, _v in (("\\", dict(CryptChest1="CryptChest1", StatueVictory1SW="StatueVictory1SW", WhiteTapestry2="WhiteTapestry4",
                            BlueTapestry2="BlueTapestry4")),
               ("/", dict(CryptChest1="CryptChest4", StatueVictory1SW="StatueVictory1SE", WhiteTapestry2="WhiteTapestry2",
                          BlueTapestry2="BlueTapestry2"))):
    ALONG[_l].update(_v)
ALONG["\\"].update(TraderBowRack1="TraderBowRack1", TraderBowRack2="TraderBowRack1")    # (Westwood's guardhouses: the
ALONG["/"].update(TraderBowRack1="TraderBowRack2", TraderBowRack2="TraderBowRack2")      # bow rack 2 on a "/" wall)
# a bench by the way it faces, in squares (Village.BENCH_FACING): +i, -i, +j, -j
BENCH_FACING = {"+i": "Bench1", "-i": "Bench5", "+j": "Bench4", "-j": "Bench2"}
# a bedroll by the square axis its foot points along (the pillow at the other end; kit/furnish NUMBERING_OVERRIDES:
# Cot1 head NW, Cot2 NE, Cot3 SE, Cot4 SW)
COT_FOOT = {"+i": "Cot1", "-i": "Cot3", "+j": "Cot4", "-j": "Cot2"}


def axis_of(dx, dy):
    """The square axis ("+i", "-i", "+j", "-j") nearest a screen vector (px)."""
    di, dj = (dx + dy) / 2, (dx - dy) / 2
    if abs(di) >= abs(dj): return "+i" if di > 0 else "-i"
    return "+j" if dj > 0 else "-j"


def line_of(tx, ty):
    """The screen line ("\\" or "/") a px direction runs along."""
    return "\\" if tx * ty > 0 else "/"
