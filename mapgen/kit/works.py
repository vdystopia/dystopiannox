"""QA round 1's themes applied to the room types the user did not rate (the works, stores, sacred and dead rooms).

The user rated part of the room types in QA round 1 (2026-10-13: armoury .. great hall) and asked that "the high-level
feedback and recurring themes" be applied to the rest; unrated types inherit the round's verdict. "Much of the feedback
boiled down to" two themes (review/reviews/QA-round1.md, memory qa-round1-themes):
1. too empty, not enough object diversity;
2. no balance or symmetry: things placed randomly, not lined up with each other.

The lessons the rated rooms taught, as this pass applies them (ledger rows Q1B-n in review/qa1/works.md):
- fill the dead space: the S corner and the SE / SW walls get a secondary group (crates, barrels, a bench, tools), the
  walls are used to a share the type sets, and a big room's middle holds groups down its long axis ("Too much empty
  space", RM-ARMOURY-07/08; "Dead spaces in the south corner are too common", the bedroom set);
- diversity: groups mix kinds and variants (wood and steel barrels, crates, sacks, tool barrels), never the same piece
  side by side ("Many of these include only barrels ... Add metal barrels and tools. Use crates more often", cellar);
- the back walls (NE, NW) carry racks, shelves and hangings, whole walls lined where the type calls for it ("Larger rooms
  need to have things like weapon racks along their walls", armoury);
- balance: rows centred on their wall and evenly spaced, the same group in matching corners, the middle groups on the
  room's axis, a centrepiece with mirrored pairs about it ("When placing two mana obelisks, place them with symmetry.
  For example, in the corners", RM-BARRACKS-04), ceremonial rooms composed on the axis from the door to the centrepiece
  ("Chapels should always be aligned with the main door");
- floors: a forge stands on a bordered brick square ("place furnaces on a small brick square", nox17); a group stands
  centred on its carpet;
- human and ogre rooms differ (an ogre hoard stays minimal but balanced, its heaps in the corners).

How: the room's recipe (kit/identity.py) and the furnishing engines place the anchors; this pass (the engines' last
step: kit/furnish.py Furnisher.grammar_audit calls apply(), after the placement grammar's audit, so its deliberate
symmetry is not undone) takes up the loose pieces the recipe scattered (the spec's `keep`), then composes the room as a
whole: the type's programme (rows, lined walls, corner heaps, the ceremonial axis), mirrored lights, the walls topped up
to their share with the type's own units, the middle's groups on its axis. Every piece goes through the furnisher's gate
(Furnisher.try_put: walkability, the doors' ways in, the object knowledge base's clearances). Only the kinds in SPEC are
touched; kit/identity.py takes their new pieces into each kind's identity (extend_identity), kit/roomtypes.py waives
the grammar's irregularity rules for them (symmetry_ok). NOX_QA1_FINISH=0 turns the pass off (the before of every
comparison); NOX_QA1_DEBUG=1 logs why placements fail.

Generic pieces other room types may want (written narrowly here; the lead may merge them with other helpers'): mirrored
corner heaps, centred even rows, axis slots for the middle, a bordered brick square under a forge (brick_square).
"""
import math, os, random, re, zlib
from collections import Counter

ENABLED = os.environ.get("NOX_QA1_FINISH", "1") != "0"
DEBUG = os.environ.get("NOX_QA1_DEBUG") == "1"
NAME = {"/|BR": "NW", "/|TL": "SE", "\\|TR": "SW", "\\|BL": "NE"}
BACK, FRONT = ("NE", "NW"), ("SE", "SW")
CORNERS = {"N": ("NW", "NE"), "E": ("NE", "SE"), "S": ("SE", "SW"), "W": ("SW", "NW")}

# ---- palettes --------------------------------------------------------------------------------------------------------
BARRELS = ["Barrel", "Barrel2", "WaterBarrel", "BarrelSteel1", "BarrelSteel2"]
CRATES = ["Crate1", "Crate2", "DarkCrate1", "DarkCrate2", "CrateSteel1", "CrateSteel2", "CrateSteel3", "CrateSteel4"]
SACKS = ["SackChestSmall1", "SackChestSmall2", "SackChestMedium1", "SackChestMedium2", "SackChestLarge1", "SackChestLarge2"]
TOOLS = ["BarrelWithTools1", "BarrelWithTools2"]
STORE = BARRELS + CRATES + SACKS + TOOLS
STEEL = ["CrateSteel1", "CrateSteel2", "CrateSteel3", "CrateSteel4", "BarrelSteel1", "BarrelSteel2"]
BONES = ["Skull", "ArmBone", "LegBone"]
ARMS_RACKS = ["TraderHangingSwords1", "TraderHangingSwords2", "TraderPoleArm1", "TraderPoleArm2", "TraderPoleArm3",
              "TraderPoleArm4", "TraderBowRack1", "TraderBowRack2", "TraderQuiverRack"]
ARMOUR = ["TraderArmorRack1", "TraderArmorRack2"]
CHESTS = ["Chest1", "Chest2", "Chest3", "Chest4"]
BENCHES = ["Bench1", "Bench2", "Bench3", "Bench4"]
COFFINS = ["CoffinBreaking1", "CoffinBreaking2", "CoffinBreaking3", "CoffinBreaking4", "Coffin1", "Coffin2", "Coffin3",
           "Coffin4"]
BOOKS = ["Bookcase1", "Bookcase2", "Bookcase3", "Bookcase4"]
POTIONS = ["PotionShelves1", "PotionShelves2", "PotionShelves3", "PotionShelves4"]
LOGSHELVES = ["LogShelvesFull1", "LogShelvesFull2", "LogShelvesFull3", "LogShelvesFull4"]
POWDER = ["BlackPowderBarrel", "BlackPowderBarrel2"]
TAPESTRY = r"^(Red|Blue|Green|White)Tapestry[1-4]$"
# tiny loose pieces: hardly seen at full size, so never what makes a room full (counts, the top-up)
# a chest or a case: stands against a back wall, never loose on the floor (a sack of "SackChest" is a loose piece)
CASED = re.compile(r"^(?!Sack).*Chest|^Desk|Shelves|Bookcase")
TINY = re.compile(r"^(Skull|ArmBone|LegBone|Corpse|Candle\d|BottleCandle|FoilCandle|MechGear|MiningPickAxe|MiningHammer|"
                  r"Cobweb|Web|RedApple|Meat$|Bread|Cheese|.*Potion\d?$|Mushroom)")
UNIT_MOST = {"bench": 2, "chest": 2, "statue": 4, "piece": 3, "coffin": 4, "monument": 2, "restraint": 3, "basin": 2,
             "bones": 4, "rack": 4, "shelves": 4}

# ---- what each kind's identity takes in (kit/identity.py extend_identity): family -> regex of the new pieces ---------
ALLOW = {
    "guardroom": dict(storage=r"^Crate[12]$|^BarrelWithTools1$|^SackChestSmall1$|^TargetBarrel[12]$|^WaterBarrel$",
                      shop_rack=r"^TraderArmorRack[12]$|^TraderPoleArm[1-4]$|^TraderBowRack[12]$|^TraderHangingSwords[12]$",
                      bench=r"^Bench[1-4]$", table=r"^RoundTableWithFood$|^RoundTable[12]$"),
    "laboratory": dict(storage=r"^SackChest(Small|Medium)[12]$|^DarkCrate[12]$|^Chest\d$", stove=r"^CauldronAnimated$",
                       table=r"^Table[1-4]$", lab=r"^VandegrafLarge$|^WizardWorkstation\d[a-d]?$|^FairyJar$",
                       shelves=r"^PotionShelves[1-4]$|^Bookcase\d$"),
    "observatory": dict(storage=r"^Chest\d$|^SackChestSmall[12]$", table=r"^SquareTable[12]$|^Table[1-4]$", bench=r"^Bench[12]$",
                        statue=r"^Gargoyle1$",
                        lab=r"^Telescope\d[a-g]$|^Orrery2$|^FairyJar$", shelves=r"^Bookcase\d$"),
    "mausoleum": dict(statue=r"^Statue2[aceg]$|^Obelisk$", tomb=r"^Crypt(1|3|5|7|9|11)$|^Coffin(Breaking)?[1-4]$",
                      storage=r"^CryptChest[1-4]$"),
    "ossuary": dict(statue=r"^Obelisk$", tomb=r"^Coffin(Breaking)?[1-4]$|^Tombstone\d+$",
                    storage=r"^(Open)?CryptChest[1-4]$"),
    "shrine": dict(statue=r"^Obelisk$|^Statue2[aceg]$", bench=r"^Bench[1-4]$|^LightBench[12]$", storage=r"^Chest1$"),
    "dark_shrine": dict(statue=r"^LOTDManaObelisk$", tomb=r"^Coffin(Breaking)?[1-4]$"),
    "treasury": dict(storage=r"^Chest[1-4]$|^SackChest(Large|Medium|Small)[12]$|^LargeBarrel[12]$",
                     table=r"^SquareTable[12]$", statue=r"^Statue2[aceg]$"),
    "torture_chamber": dict(storage=r"^Chest[1-4]$|^Barrel2?$|^WaterBarrel$|^DarkCrate[12]$|^BarrelWithTools[12]$"),
    "smithy": dict(storage=r"^CrateSteel[1-4]$|^BarrelSteel[12]$|^BarrelWithTools[12]$|^DarkCrate[12]$|^WaterBarrel$",
                   shop_rack=r"^TraderArmorRack[12]$|^TraderPoleArm[1-4]$|^TraderHangingSwords[12]$"),
    "workshop": dict(storage=r"^CrateSteel[1-4]$|^BarrelWithTools[12]$|^(Dark)?Crate[12]$|^Barrel2?$|^SackChestSmall1$|"
                             r"^WaterBarrel$|^BarrelSteel[12]$",
                     bench=r"^Bench[12]$", table=r"^Table[1-4]$"),
    "winch_room": dict(storage=r"^CrateSteel[1-4]$|^BarrelSteel[12]$|^BarrelWithTools[12]$|^(Dark)?Crate[12]$"),
    "storeroom": dict(storage=r"^BarrelSteel[12]$|^CrateSteel[1-4]$|^WaterBarrel$", shelves=r"^LogShelvesFull[1-4]$"),
    "granary": dict(storage=r"^BarrelSteel[12]$|^WaterBarrel$", shop_rack=r"^TraderAppleCrate$",
                    shelves=r"^LogShelvesFull[1-4]$"),
    "ore_store": dict(storage=r"^BarrelSteel[12]$|^CrateSteel[1-4]$", shop_rack=r"^TraderShelves[12]$"),
    "ogre_hoard": dict(storage=r"^ChestOgre[1-4]$|^OgreSack[12]$|^PiledBarrels1$"),
    "powder_store": dict(storage=r"^CrateSteel[1-4]$|^BarrelSteel[12]$|^DarkCrate[12]$"),
}

# ---- the kinds' programmes -------------------------------------------------------------------------------------------
# keep: a regex of the recipe's pieces that stay (the rest is taken up and the room composed again); relight: the floor
# lights taken up and set again in mirrored pairs; mirror: every wall unit and middle group mirrored across the axis
# from the main door (the ceremonial rooms); goal: the reach (the floor within 1.6 units of a piece) the bare-floor fill
# works toward; cover: the most of the floor furniture may cover; program: the type's own composition, in order;
# walls: the units the back and front walls take, in turn, until each is used to its share (`fill`); pal: the units'
# palettes; middle: the groups down the middle on its axis (`centre` on the middle spot, `pairs` on the spots either
# side of it, `most` of each); hang: hangings on the bare back walls, last; least: (objects a tile, kinds a room) the
# room ends with at least (master's lab average); extra: the small pieces the top-up adds; repeat: at most so many pieces
# of a kind (the type's profile); statue_most: at most so many statues of a kind from the walls' statue unit.
SPEC = {}


def _spec(kinds, **kw):
    for k in kinds: SPEC[k] = kw


SEATS = r"Chair|Stool"
_spec(("guardroom",), least=(0.21, 8), extra=["TargetBarrel1", "WaterBarrel", "Crate2", "SackChestSmall1", "Barrel"],
      goal=0.82, cover=0.36, relight=True, keep=r"^$",
      program=[("row", dict(wall=("back_short", "back_long", "front_long", "SE", "SW"), types=["Cot1"], spacing=2.6,
                            least=1, most=2, gap=0.3)),
               ("row", dict(wall="back_long", types=ARMS_RACKS, spacing=2.2, least=2, ends=ARMOUR, walls=2)),
               ("corner_heap", dict(corner="S", types=["WaterBarrel", "Barrel", "Crate1", "Barrel2", "Crate2",
                                                       "BarrelWithTools1"], n=3)),
               ("corner_pair", dict(corners=("W", "E"), types=["Barrel", "Crate2", "WaterBarrel"], heap=2))],
      walls=dict(back=["racks", "chest", "bench"], front=["heap"], fill=(0.75, 0.45)),
      pal=dict(rack=ARMS_RACKS, rack_ends=ARMOUR, chest=CHESTS, bench=BENCHES,
               heap=["WaterBarrel", "Barrel", "Barrel2", "Crate1", "Crate2", "BarrelWithTools1", "SackChestSmall1"]),
      middle=dict(centre=["table_set"], pairs=["armour_pair", "target"], most={"table_set": 2, "target": 2},
                  pairs_from=60),
      hang=dict(pat=TAPESTRY + r"|^WallTrophy(Bear|Moose|MountainLion)[12]$", most=2))

STORE_WALLS = dict(back=["shelves", "heap"], front=["heap"], fill=(0.75, 0.6), most={"shelves": 2})
_spec(("storeroom",), least=(0.22, 5), extra=["SackChestSmall1", "BarrelWithTools2", "CrateSteel4", "WaterBarrel"],
      goal=0.8, cover=0.38, keep=r"^$",
      program=[("corner_heap", dict(corner="S", types=STORE, n=5)),
               ("corner_heap", dict(corner="N", types=STORE, n=4)),
               ("corner_pair", dict(corners=("W", "E"), types=STORE, heap=3))],
      walls=STORE_WALLS, pal=dict(heap=STORE, shelf=LOGSHELVES, shelf_n=2),
      middle=dict(centre=["stack"], pairs=["stack", "piled"], most={"piled": 2}, centre_from=60, pairs_from=60))
_spec(("granary",), least=(0.22, 5), extra=["SackChestSmall1", "SackChestSmall2", "TraderAppleCrate", "Barrel2"],
      goal=0.8, cover=0.38, keep=r"^$",
      program=[("corner_heap", dict(corner="S", types=SACKS + ["TraderAppleCrate", "Barrel"], n=5)),
               ("corner_heap", dict(corner="N", types=SACKS + ["Barrel2", "Crate2"], n=4)),
               ("corner_pair", dict(corners=("W", "E"), types=SACKS + ["Crate1", "TraderAppleCrate"], heap=3))],
      walls=STORE_WALLS,
      pal=dict(heap=SACKS + ["TraderAppleCrate", "Barrel", "Barrel2", "Crate1", "Crate2", "BarrelWithTools1"],
               shelf=LOGSHELVES, shelf_n=2),
      middle=dict(centre=["sackpile"], pairs=["stack", "sackpile"], centre_from=60, pairs_from=60))
_spec(("ore_store",), least=(0.22, 5), extra=["MiningPickAxeOnGround1", "MiningHammer1", "CrateSteel4", "BarrelWithTools2"],
      goal=0.78, cover=0.38, keep=r"^Mine(Mana|Ore)Cart",
      program=[("corner_heap", dict(corner="S", types=STEEL + TOOLS + ["DarkCrate1"], n=5)),
               ("corner_heap", dict(corner="N", types=STEEL + TOOLS, n=4)),
               ("corner_pair", dict(corners=("W", "E"), types=STEEL + TOOLS, heap=3))],
      walls=dict(back=["shelves", "heap"], front=["heap"], fill=(0.7, 0.55), most={"shelves": 1}),
      pal=dict(heap=STEEL + TOOLS + ["DarkCrate1", "DarkCrate2"], shelf=["TraderShelves1", "TraderShelves2"]),
      middle=dict(centre=["cart"], pairs=["stack", "cart"], most={"cart": 3}, pairs_from=60))
# the ogres' hoard: minimal is fine, but balanced, not bare in a corner (the ogre den and pen notes)
OGRE = ["OgreSack1", "Barrel", "Barrel2", "Crate1", "DarkCrate1", "PiledBarrels1"]
_spec(("ogre_hoard",), least=(0.22, 5), extra=["OgreHutMeat", "Skull", "ArmBone", "LegBone"],
      goal=0.55, cover=0.3, keep=r"^$",
      program=[("centred", dict(types=["ChestOgre1", "ChestOgre2", "ChestOgre3", "ChestOgre4"], wall="back_long")),
               ("corner_heap", dict(corner="S", types=OGRE, n=4)),
               ("corner_pair", dict(corners=("W", "E"), types=OGRE, heap=3)),
               ("around", dict(pat=r"^ChestOgre", types=["OgreHutMeat", "Skull", "ArmBone"], d=1.6))],
      walls=dict(back=["heap"], front=["heap"], fill=(0.45, 0.35)), pal=dict(heap=OGRE),
      middle=dict(centre=["bones"], pairs=["bones"], centre_from=40))

_spec(("powder_store",), least=(0.31, 2), extra=["BlackPowderBarrel", "CrateSteel2", "BarrelSteel1"],
      goal=0.8, cover=0.4, keep=r"^$",
      program=[("corner_heap", dict(corner="N", types=POWDER + ["CrateSteel1", "BarrelSteel2"], n=5)),
               ("corner_heap", dict(corner="S", types=POWDER + ["CrateSteel1", "BarrelSteel1", "DarkCrate1"], n=5)),
               ("corner_pair", dict(corners=("W", "E"), types=POWDER + ["CrateSteel2", "BarrelSteel2"], heap=3))],
      walls=dict(back=["heap"], front=["heap"], fill=(0.7, 0.55)),
      pal=dict(heap=POWDER + ["CrateSteel1", "CrateSteel3", "BarrelSteel1", "DarkCrate1", "DarkCrate2"]),
      middle=dict(centre=["powder"], pairs=["powder"], centre_from=60, pairs_from=60))

_spec(("treasury",), least=(0.3, 9), extra=["Statue2c", "SackChestLarge1", "LargeBarrel2", "SackChestSmall1", "SackChestMedium2"],
      goal=0.66, cover=0.3, mirror=True, relight=True, keep=r"^$",
      program=[("row", dict(wall=("far", "back_long", "back_short"), types=["Chest1"], spacing=2.8, least=1, most=3,
                            back=True, walls=2)),
               ("corner_pair", dict(corners=("W", "E"), types=["SackChestLarge1", "SackChestMedium1", "SackChestSmall2"],
                                    heap=3)),
               ("corner_heap", dict(corner="S", types=["LargeBarrel1", "SackChestLarge2", "SackChestMedium2"], n=3)),
               ("axis", dict(flank=["Statue2a", "Statue2c"], avenue=[], pairs=[], hang=TAPESTRY))],
      walls=dict(back=["heap"], front=["heap"], fill=(0.5, 0.35)),
      pal=dict(heap=SACKS + ["LargeBarrel1"]),
      middle=dict(centre=["counting"], pairs=["sackpile"], most={"counting": 1, "sackpile": 4}, pairs_from=90),
      # a tapestry on a bare back wall where the far wall's pair found no room (never the recipe's trophies: shop
      # racks, which the type's profile forbids)
      hang=dict(pat=TAPESTRY, most=2))

_spec(("torture_chamber",), least=(0.12, 8), extra=["Skull", "ArmBone", "LegBone", "WaterBarrel", "BarrelWithTools1", "DarkCrate1"],
      goal=0.62, cover=0.26, relight=True, keep=r"^(TortureRack\d|Desk\d|.*Chair\d|.*Stool\d)$",
      program=[("row", dict(wall="back_free", types=["IronMaiden1", "Stocks3", "Stocks4"], spacing=2.6, least=1,
                            walls=2, gap=0.45)),
               ("corner_pair", dict(corners=("W", "E"), types=["DunMirFlameBasinLit"], light=True)),
               ("around", dict(pat=r"^TortureRack", types=BONES, d=2.0, heaps=True)),
               ("corner_heap", dict(corner="S", types=["Barrel", "WaterBarrel", "DarkCrate1", "BarrelWithTools1"], n=3)),
               ("centred", dict(types=CHESTS, wall="back_short"))],
      walls=dict(back=["restraint", "heap", "chest"], front=["heap", "bones"], fill=(0.6, 0.45)),
      pal=dict(restraint=["IronMaiden1", "Stocks3", "Stocks4"], chest=CHESTS,
               heap=["Barrel", "WaterBarrel", "DarkCrate1", "BarrelWithTools1", "Barrel2"]),
      middle=dict(centre=["rack"], pairs=["bones"]))

_spec(("smithy",), least=(0.16, 9), extra=["WaterBarrel", "BarrelWithTools2", "CrateSteel3", "MechGear", "DarkCrate2", "Barrel2"],
      goal=0.76, cover=0.34, relight=True,
      keep=r"^(CinderBin\d|Bellows\d|Anvil\d|TraderDesk\d|.*Chair\d|.*Stool\d)$",
      program=[("brick_square", dict(pat=r"^CinderBin")),
               ("row", dict(wall="back_free", types=["TraderHangingSwords1", "TraderHangingSwords2", "TraderPoleArm1",
                                                     "TraderPoleArm3"], spacing=2.2, least=2, ends=ARMOUR, walls=1)),
               ("corner_heap", dict(corner="S", types=["WaterBarrel", "CrateSteel1", "BarrelWithTools1", "DarkCrate1",
                                                       "BarrelSteel1", "BarrelWithTools2"], n=4)),
               ("corner_pair", dict(corners=("W", "E"), types=["WaterBarrel", "CrateSteel2", "BarrelSteel2"], heap=2))],
      walls=dict(back=["racks", "heap"], front=["heap"], fill=(0.6, 0.45)),
      pal=dict(rack=["TraderHangingSwords1", "TraderHangingSwords2", "TraderPoleArm1", "TraderPoleArm3"], rack_ends=ARMOUR,
               heap=["WaterBarrel", "CrateSteel1", "CrateSteel2", "BarrelSteel1", "BarrelSteel2", "BarrelWithTools1",
                     "BarrelWithTools2", "DarkCrate1", "DarkCrate2"]),
      middle=dict(centre=[], pairs=["stack"], pairs_from=80))

_spec(("workshop",), least=(0.32, 13), extra=["MineOreCartWheel", "MechGear", "Anvil2", "Gear1", "SackChestSmall1", "BarrelWithTools2", "WaterBarrel", "DarkCrate2", "BarrelSteel1", "Crate2", "CrateSteel1"],
      goal=0.78, cover=0.34, relight=True, keep=r"^$",
      program=[("line", dict(wall="back_long", types=["TraderShelves1", "TraderShelves2"])),
               ("row", dict(wall="back_short", types=["Gear1", "Gear2", "Gear3", "Gear4"], spacing=2.4, least=2,
                            walls=1)),
               ("corner_heap", dict(corner="S", types=["BarrelWithTools1", "Crate1", "BarrelWithTools2", "CrateSteel2",
                                                       "Barrel", "DarkCrate1"], n=4)),
               ("corner_pair", dict(corners=("W", "E"), types=["BarrelWithTools1", "Crate2", "MineOreCartWheel"],
                                    heap=2))],
      walls=dict(back=["heap"], front=["heap", "bench"], fill=(0.6, 0.45)),
      pal=dict(bench=["Bench1", "Bench2"],
               heap=["BarrelWithTools1", "BarrelWithTools2", "Crate1", "Crate2", "DarkCrate1", "CrateSteel1",
                     "CrateSteel2", "Barrel"]),
      middle=dict(centre=["workbench"], pairs=["parts", "stack"], most={"workbench": 1}, pairs_from=60),
      hang=dict(pat=TAPESTRY, most=2))

_spec(("winch_room",), least=(0.25, 8), extra=["MechGear", "MineOreCartWheel", "BarrelWithTools1", "CrateSteel1", "DarkCrate2", "Crate2", "BarrelSteel2", "MechGear"],
      goal=0.7, cover=0.3, relight=True, keep=r"^PulleyGear\d$",
      program=[("row", dict(wall="back_free", types=["Gear1", "Gear2", "Gear3", "Gear4", "Gear5", "Gear6"], spacing=2.4,
                            least=2, walls=2)),
               ("around", dict(pat=r"^PulleyGear", types=["MechGear", "MineOreCartWheel"], d=2.2)),
               ("corner_heap", dict(corner="S", types=["BarrelWithTools1", "CrateSteel1", "BarrelSteel1", "DarkCrate1",
                                                       "BarrelWithTools2"], n=4)),
               ("corner_pair", dict(corners=("W", "E"), types=["CrateSteel2", "BarrelWithTools2", "BarrelSteel2"],
                                    heap=2))],
      walls=dict(back=["heap"], front=["heap"], fill=(0.55, 0.42)),
      pal=dict(heap=["BarrelWithTools1", "BarrelWithTools2", "CrateSteel1", "CrateSteel2", "CrateSteel3", "BarrelSteel1",
                     "BarrelSteel2", "DarkCrate1", "DarkCrate2"]),
      middle=dict(centre=["winch"], pairs=["parts", "stack"]))

_spec(("laboratory",), least=(0.19, 8), extra=["FairyJar", "SackChestSmall1", "SackChestSmall2"],
      goal=0.74, cover=0.32, relight=True, keep=r"^(Desk\d|.*Chair\d|.*Stool\d)$",
      program=[("desk", dict()),
               ("line", dict(wall="desk", types=BOOKS, mix=POTIONS)),
               ("row", dict(wall="other_back", types=["WizardWorkstation1", "WizardWorkstation2a", "WizardWorkstation3a"],
                            spacing=1.9, least=2, ends=["PotionShelves1", "PotionShelves2"], walls=1, touch=False)),
               ("corner_pair", dict(corners=("W", "E"), types=["VandegrafLarge"])),
               ("corner_heap", dict(corner="S", types=["SackChestSmall1", "DarkCrate2", "SackChestMedium1",
                                                       "SackChestSmall2"], n=3))],   # (no chest: its back to the camera)
      walls=dict(back=["ends", "chest", "piece"], front=["heap"], fill=(0.7, 0.35),
                 most={"chest": 1, "piece": 2, "ends": 2}),
      pal=dict(chest=CHESTS, piece=["AlchemistDesk1", "FairyJar"], ends=["PotionShelves1", "PotionShelves2"],
               heap=["SackChestSmall1", "SackChestMedium1", "DarkCrate2", "SackChestSmall2"]),
      middle=dict(centre=["alchemy"], pairs=["lab_island", "book_stack", "generator"],
                  most={"alchemy": 1, "lab_island": 4, "book_stack": 4}),
      hang=dict(pat=r"^(Blue|Red)Tapestry[1-4]$", most=2))

_spec(("observatory",), statue_most=3, least=(0.12, 9), extra=["FairyJar", "SackChestSmall1", "Gargoyle1"],
      goal=0.7, cover=0.3, relight=True, keep=r"^(Desk\d|.*Chair\d|.*Stool\d)$",
      program=[("desk", dict()),
               ("line", dict(wall="desk", types=BOOKS)),
               ("corner_pair", dict(corners=("W", "E"), types=["Telescope2e", "Telescope2g", "Telescope1b"])),
               ("corner_group", dict(corner="S", group="chart_table"))],
      walls=dict(back=["ends", "chest"], front=["statue", "piece"], fill=(0.5, 0.35),
                 most={"chest": 1, "ends": 2, "statue": 2, "piece": 2}),
      pal=dict(chest=CHESTS, statue=["Gargoyle1"], piece=["FairyJar"],
               ends=["Telescope2e", "Telescope2g", "Telescope1b", "Telescope1c"]),
      middle=dict(centre=["curio"], pairs=["book_stack", "telescope", "chart_table"], step=4.6,
                  most={"telescope": 2, "curio": 1, "book_stack": 10, "chart_table": 2}),
      hang=dict(pat=r"^StarChart[1-4][a-d]$|^Zodiac[12][a-d]$", most=4))

_spec(("shrine",), least=(0.17, 5), extra=["Chest1"],
      goal=0.5, cover=0.22, mirror=True, relight=True, keep=r"^$",
      program=[("altar_wall", dict(types=["DunMirAltar1", "DunMirAltar2"], flank=["Obelisk"])),
               ("must_statues", dict(types=["Obelisk"])),
               ("axis", dict(runner=False, benches=["Bench1", "Bench2", "LightBench1"], flank=[],
                             avenue=[], pairs=["DunMirFlameBasinLit"], hang=TAPESTRY))],
      walls=dict(back=["statue", "chest"], front=["statue"], fill=(0.3, 0.15), most={"statue": 2, "chest": 1}),
      pal=dict(statue=["Statue2a", "Statue2c"], chest=["Chest1", "Chest2"]),
      middle=dict(centre=["shrine_square"], pairs=[], most={"shrine_square": 1}),
      hang=dict(pat=TAPESTRY, most=2))
_spec(("dark_shrine",), least=(0.17, 5), extra=["CoffinBreaking2", "Skull", "ArmBone"],
      goal=0.55, cover=0.22, mirror=True, keep=r"^(LOTDLichGodStatue\d|LOTDManaObelisk|LOTDIncenseBasinLit|LOTDTapestry\d)$",
      program=[("altar_wall", dict(types=["LOTDLichGodStatue1", "LOTDLichGodStatue2"], flank=["LOTDManaObelisk"])),
               ("axis", dict(runner=False, benches=[], flank=["LOTDManaObelisk"], avenue=[],
                             pairs=["LOTDIncenseBasinLit"], hang=r"^LOTDTapestry[12]$|^LOTDBanner[12]$", coffins=True)),
               ("must_statues", dict(types=["LOTDManaObelisk"]))],
      walls=dict(back=["statue", "coffin", "bones"], front=["coffin", "bones"], fill=(0.4, 0.25),
                 most={"statue": 2, "coffin": 2}),
      pal=dict(statue=["LOTDManaObelisk"], coffin=COFFINS),
      middle=dict(centre=["dark_square"], pairs=["bones"], most={"dark_square": 1}),
      hang=dict(pat=r"^LOTDTapestry[12]$|^LOTDBanner[12]$", most=2))
_spec(("mausoleum",), least=(0.16, 4), extra=["CoffinBreaking1", "Skull", "ArmBone"],
      goal=0.62, cover=0.26, mirror=True, relight=True, keep=r"^$",
      program=[("axis", dict(runner=True, benches=[], flank=["Statue2a", "Statue2c", "Statue2e", "Statue2g"],
                             avenue=["Statue2a", "Statue2c", "Statue2e", "Statue2g"], pairs=["Obelisk"],
                             hang=TAPESTRY, coffins=True, tomb=True, chest=True))],
      walls=dict(back=["bones", "monument"], front=["bones"], fill=(0.35, 0.2)),
      pal=dict(monument=["Monument1"]),
      middle=dict(centre=["tomb"], pairs=["coffin", "statue", "bones"], most={"tomb": 1, "coffin": 4}))
_spec(("ossuary",), least=(0.09, 5), repeat=4, extra=["OpenCryptChest1", "Tombstone1", "Skull"],
      goal=0.62, cover=0.26, mirror=True, relight=True, keep=r"^$",
      program=[("axis", dict(runner=False, benches=[], flank=[], avenue=[], pairs=["Candleabra3"], hang=None,
                             coffins=False, chest=True)),
               ("centred", dict(types=["CryptChest1", "CryptChest2", "CryptChest3", "CryptChest4"], wall="back_long")),
               # a pair of monuments in the side corners, else one in the middle on the axis (a showpiece stands twice
               # only 10 units apart: never as a pair across a narrow room's axis)
               ("corner_pair", dict(corners=("W", "E"), types=["Monument1"]))],
      walls=dict(back=["bones", "grave", "monument", "bones"], front=["bones", "grave"], fill=(0.55, 0.4),
                 most={"bones": 10, "grave": 1, "monument": 1}),
      pal=dict(coffin=COFFINS, grave=["Tombstone1", "Tombstone3", "Tombstone5", "Tombstone7"], monument=["Monument1"]),
      middle=dict(centre=["monument", "bones"], pairs=["bones"], most={"bones": 3, "monument": 1},   # (more bone heaps read as strewn)
                  centre_from=60))


def extend_identity(rooms):
    """Takes the pieces this pass places into each kind's identity (kit/identity.py ROOMS[kind]["allow"]: family -> a
    regex of more types), so the checker's identity rule (validate/checks.py identity_strays) reads them as the room's
    own. A key of its own, so the recipe's plan and its random draws stay as they were."""
    for kind, fams in ALLOW.items():
        r = rooms.get(kind)
        if r is None: continue
        r["allow"] = dict(fams)


# ---- the pass --------------------------------------------------------------------------------------------------------
def apply(f):
    """Applies the QA round 1 themes to a furnished room of a kind in SPEC (the furnishing engines' last step)."""
    if not ENABLED or f.kind not in SPEC: return None
    x = Finish(f, SPEC[f.kind])
    saved = (f.in_required, f.composing, f.placing_light, f.ceiling, f._pairing)
    f.in_required, f.composing, f.placing_light, f.ceiling = True, False, False, None
    try:
        x.run()
    finally:
        f.in_required, f.composing, f.placing_light, f.ceiling, f._pairing = saved
    f.qa1_log = dict(x.log)
    # recorded with the audit's log, so the labs' variants.json carry it (grammar_log)
    gl = getattr(f, "grammar_log", None)
    if gl is None: gl = f.grammar_log = Counter()
    for k, n in x.log.items(): gl["qa1 " + k] = n
    return x.log


class Finish:
    LIGHT_RX = re.compile(r"^(Candleabra\d|LOTDCandleabra\d)$")

    def __init__(self, f, spec):
        from kit import furnish as F
        self.F, self.f, self.s = F, f, spec
        self.rng = random.Random(zlib.crc32(f"qa1:{f.spec.d.get('name')}:{f.room.id}:{f.kind}".encode()))
        self.log = Counter()
        self.runs = {n: [] for n in NAME.values()}
        for r in f.g.runs: self.runs[NAME[r["side"]]].append(r)
        self.main = {n: max(rs, key=lambda r: r["hi"] - r["lo"]) for n, rs in self.runs.items() if rs}
        self.cu, self.cv = f.g.centroid
        self.tiles = len(f.room.tiles)
        us = [x + y + 1 for x, y in f.g.cells]; vs = [x - y for x, y in f.g.cells]
        self.box = (min(us), max(us) + 1, min(vs), max(vs))
        self.axis_long = "u" if (self.box[1] - self.box[0]) >= (self.box[3] - self.box[2]) else "v"
        self.cur = ""
        self.mcount = Counter()        # the middle's groups placed, by name (their `most`)
        # one kind of coffin to a room (the grammar's "beds or tombs of one kind"): breakable ones more often (the user,
        # of crypts: "Use the breakable coffin objects sometimes")
        self.coffin = "CoffinBreaking" if self.rng.random() < 0.6 else "Coffin"

    # ---- small helpers ---------------------------------------------------------------------------------------------
    def ok(self, t):
        if t and t.startswith("Coffin") and re.sub(r"\d+$", "", t) != self.coffin: return False
        return bool(t) and t in self.f.things and self.f.ok_type(t)

    def oks(self, types):
        return [t for t in types if self.ok(t)]

    def half(self, t):
        return self.f.half(t)

    def fam(self, t):
        return self.F._family_of(t)

    def cover_ok(self, t):
        return self.f.coverage(self.f.footprint(t)) <= self.s.get("cover", 0.3)

    def capped(self, t):
        """Whether one more piece of t's family passes the type's caps (kit/roomtypes.py caps: tiles per piece, most)."""
        fam = self.fam(t)
        caps = (self.F.room_profile(self.f.kind) or {}).get("caps", {})
        if fam not in caps: return False
        per, most = caps[fam]
        have = sum(1 for tt, _ in self.f._typed if self.fam(tt) == fam)
        return have >= min(most, max(1, int(self.tiles / per)))

    def put(self, t, u, v, touch=False, blocking=True, **kw):
        if self.capped(t):
            if DEBUG: self.log["why cap " + (self.fam(t) or "")] += 1
            return None
        if blocking and not self.cover_ok(t):
            if DEBUG: self.log["why cover"] += 1
            return None
        o = self.f.try_put(t, u, v, blocking=blocking, touch=touch, **kw)
        if o: self.log["+" + (self.fam(t) or "piece")] += 1
        elif DEBUG: self.log["why " + self.cur + " " + self.why(t, u, v, blocking, touch, kw.get("snug", False))] += 1
        return o

    def remove(self, objs):
        for o in objs or ():
            if o: self.f._remove(o)

    def why(self, t, u, v, blocking, touch, snug):
        """Why a placement failed (NOX_QA1_DEBUG=1): the furnisher's gates in turn."""
        f, g = self.f, self.f.g
        hu, hv = self.half(t)
        pts = [(u + a * hu, v + b * hv) for a in (-1, 0, 1) for b in (-1, 0, 1)]
        if not all(g.inside(*p) for p in pts): return "outside"
        if min(g.wall_dist(*p) for p in pts) < (0.1 if snug else 0.25): return "wall"
        if not g.before_back_wall(u, v): return "wallcell"
        if blocking:
            for du, dv in g.doors:
                if math.hypot(u - du, v - dv) < self.F.DOOR_CLEAR + max(hu, hv): return "door"
            for z in g.zones:
                if u + hu > z[0] and u - hu < z[1] and v + hv > z[2] and v - hv < z[3]:
                    return "zone " + getattr(self, "zone_tag", {}).get(z, "?")
        for (pu, pv, phu, phv, pb, player) in g.placed:
            if pb != blocking or player == "wall": continue
            gap = 0.02 if touch else 0.15
            if abs(u - pu) < hu + phu + gap and abs(v - pv) < hv + phv + gap: return "overlap"
        if blocking and self.fam(t) in self.F.WAY_TALL and any(u + hu > b[0] and u - hu < b[1] and v + hv > b[2] and
                                                               v - hv < b[3] for b in f.far_ways): return "far way"
        if blocking and any(u + hu > b[0] and u - hu < b[1] and v + hv > b[2] and v - hv < b[3] for b in f.runner_boxes):
            return "runner"
        if not f._one_of_a_kind_ok(t, u, v): return "oneofakind"
        before = dict(f.kb_refused)
        f._kb_ok(t, u, v, hu, hv, f.placing_light is False and blocking, "floor")
        d = [k for k in f.kb_refused if f.kb_refused[k] != before.get(k, 0)]
        if d: return "kb " + d[0]
        if not f._one_of_a_kind_ok(t, u, v): return "oneofakind"
        if blocking and not g.reachable_ok((u, v, hu, hv, True, "floor")): return "reach"
        return "other"

    def depth(self, t, r):
        hu, hv = self.half(t)
        return hu if r["line"] == "/" else hv

    def along_half(self, t, r):
        hu, hv = self.half(t)
        return hv if r["line"] == "/" else hu

    def uv(self, r, depth, a):
        return self.f._uv_on(r, depth, a)

    def variant(self, t0, r, fam=None):
        f = self.f
        try:
            t = f.side_variant(t0, r, fam or self.fam(t0))
        except Exception:
            t = None
        if t and self.ok(t): return t
        hu, hv = self.half(t0)
        if abs(hu - hv) < 0.12: return t0             # round enough to stand either way
        return t0 if f._along_wall(t0, r["line"]) else None

    def name_of(self, r):
        return NAME[r["side"]]

    def door_cuts(self, r):
        out = []
        for du, dv in self.f.g.doors:
            perp, along = (du, dv) if r["line"] == "/" else (dv, du)
            if abs(perp - r["coord"]) < 1.6: out.append((along - 2.6, along + 2.6))
        for op in self.f.openings:
            if op["line"] == r["line"] and abs(op["coord"] - r["coord"]) < 1.6:
                out.append((op["along"] - op["half"] - 1.2, op["along"] + op["half"] + 1.2))
        return out

    def wall_pieces(self, r, reach=1.3, hang=False):
        """(along0, along1) of the pieces standing against (or hung on: hang) run r; a hanging keeps off every piece
        it may not hang above (the furnisher's rule, kit/objects.py hangs_over: only rugs and other hangings)."""
        from kit import objects as _O
        out = []
        for t, rec in self.f._typed:
            u, v, hu, hv, blocking, layer = rec
            if (layer == "wall") != hang:
                if not hang or _O.hangs_over(_O.category(t)): continue
            perp, along = (u, v) if r["line"] == "/" else (v, u)
            dp, da = (hu, hv) if r["line"] == "/" else (hv, hu)
            off = (perp - r["coord"]) * r["sign"]
            if off <= 0 or off - dp > (2.6 if hang else reach): continue
            if along + da < r["lo"] - 0.3 or along - da > r["hi"] + 0.3: continue
            out.append((along - da, along + da))
        return out

    def interior(self, r):
        """The stretches of run r the room's floor actually lies along (a run's ends reach a cell past the corner, and
        an L room's walls past its inner corner): sampled 0.6 and 1.6 units in from the wall."""
        key = (r["line"], r["coord"], r["lo"], r["hi"])
        memo = self.__dict__.setdefault("_interior", {})
        if key in memo: return memo[key]
        out, cur, step = [], None, 0.2
        a = r["lo"]
        while a <= r["hi"] + 1e-6:
            ok = self.f.g.inside(*self.uv(r, 0.6, a)) and self.f.g.inside(*self.uv(r, 1.6, a))
            if ok and cur is None: cur = a
            if not ok and cur is not None: out.append((cur, a - step)); cur = None
            a += step
        if cur is not None: out.append((cur, r["hi"]))
        memo[key] = [(x + 0.15, y - 0.15) for x, y in out if y - x > 0.6]
        return memo[key]

    def free_stretches(self, r, pad=0.25, hang=False):
        free = list(self.interior(r))
        for c0, c1 in [(a - pad, b + pad) for a, b in self.wall_pieces(r, hang=hang)] + self.door_cuts(r):
            nxt = []
            for f0, f1 in free:
                if c1 <= f0 or c0 >= f1: nxt.append((f0, f1)); continue
                if c0 > f0: nxt.append((f0, c0))
                if c1 < f1: nxt.append((c1, f1))
            free = nxt
        return [(a, b) for a, b in free if b - a > 0.6]

    def longest(self, r, pad=0.35, least=0.0):
        st = [s for s in self.free_stretches(r, pad=pad) if s[1] - s[0] >= least]
        return max(st, key=lambda s: s[1] - s[0]) if st else None

    def put_wall(self, t0, r, a, gap=0.25, fam=None, touch=False):
        t = self.variant(t0, r, fam)
        if not t: return None
        # against a front wall the saw-tooth of its wall cells reaches further in: a step more
        for g in ((gap,) if self.name_of(r) in BACK else (gap, gap + 0.25, gap + 0.5)):
            o = self.put(t, *self.uv(r, self.depth(t, r) + g, a), touch=touch, snug=True)
            if o: return o
        return None

    def put_hang(self, t0, r, a):
        t = self.variant(t0, r, "wall_decor")
        if not t: return None
        perp = (self.f.T.get("inventory", {}).get("wall_decor") or {}).get("perp_px")
        d = self.f.perp_for(t, perp)
        before = dict(self.f.kb_refused) if DEBUG else None
        o = self.f.try_put(t, *self.uv(r, d, a), blocking=False, wall_ok=True, layer="wall")
        if o: self.log["+hanging"] += 1
        elif DEBUG:
            k = next((k for k in self.f.kb_refused if self.f.kb_refused[k] != before.get(k, 0)), "other")
            self.log[f"why {self.cur} hang {k}"] += 1
        return o

    def corner(self, name):
        """(u, v, su, sv) of a corner of the room's main walls (su, sv: the way into the room), or None."""
        a, b = CORNERS[name]
        ra, rb = self.main.get(a), self.main.get(b)
        if not ra or not rb: return None
        r1, r2 = (ra, rb) if ra["line"] == "/" else (rb, ra)
        u, v = r1["coord"], r2["coord"]
        if not (r1["lo"] - 1.0 <= v <= r1["hi"] + 1.0 and r2["lo"] - 1.0 <= u <= r2["hi"] + 1.0): return None
        return u, v, r1["sign"], r2["sign"]

    def pick_seq(self, types, n):
        """n types from a palette, never the same twice in a row, the palette's kinds spread through."""
        pool = self.oks(types)
        if not pool: return []
        out, last = [], None
        for i in range(n):
            choice = [t for t in pool if t != last and (len(pool) < 3 or t not in out[-2:])] or pool
            t = self.rng.choice(choice)
            out.append(t); last = t
        return out

    def wall_by(self, which):
        """A main wall run by role: back_long / back_short (the longer, shorter back wall), back_free (the back wall with
        the longest bare stretch), front_long, far (across from the main door), desk (the back wall with the desk),
        other_back (the other one), or a name (NE, NW, SE, SW)."""
        backs = [self.main[n] for n in BACK if n in self.main]
        fronts = [self.main[n] for n in FRONT if n in self.main]
        if which in NAME.values(): return self.main.get(which)
        if which == "back_long": return max(backs, key=lambda r: r["hi"] - r["lo"], default=None)
        if which == "back_short": return min(backs, key=lambda r: r["hi"] - r["lo"], default=None)
        if which == "back_free":
            return max(backs, key=lambda r: (lambda s: s[1] - s[0] if s else 0)(self.longest(r)), default=None)
        if which == "front_long": return max(fronts, key=lambda r: r["hi"] - r["lo"], default=None)
        if which == "far": return self.axis_back_run()
        if which in ("desk", "other_back"):
            desk = next((rec for t, rec in self.f._typed if re.match(r"^Desk\d$", t)), None)
            if desk is None: return self.wall_by("back_long" if which == "desk" else "back_short")
            def d(r): return abs((desk[0] if r["line"] == "/" else desk[1]) - r["coord"])
            best = min(backs, key=d, default=None)
            if which == "desk": return best
            return next((r for r in backs if r is not best), None)
        return None

    # ---- groups ----------------------------------------------------------------------------------------------------
    def heap_at(self, u0, v0, su, sv, types, n, first_gap=0.3, swap=False):
        """A tight heap of mixed pieces from the corner (u0, v0) into the room (su, sv): the first snug in the corner,
        then along both walls and one before them; swap: along the other wall first (a mirrored corner)."""
        seq = self.pick_seq(types, n * 2)
        got, used, cell = [], set(), None
        slots = [(0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2), (3, 0), (2, 1), (1, 2)]
        if swap: slots = [(b, a) for a, b in slots]
        for t in seq:
            if len(got) >= n: break
            hu, hv = self.half(t)
            cell = cell or 2 * max(hu, hv) + 0.08
            for s in slots:
                if s in used: continue
                if s != (0, 0) and not any((s[0] - a, s[1] - b) in used for a, b in ((1, 0), (0, 1))): continue
                o = self.put(t, u0 + su * (first_gap + hu + s[0] * cell), v0 + sv * (first_gap + hv + s[1] * cell),
                             touch=True)
                if o:
                    used.add(s); got.append(o); break
        if len(got) == 1 and n > 1:                      # a lone barrel in a corner reads as stray (grammar lone)
            self.remove(got); return []
        return got

    def wall_heap(self, r, a, types, n, lo=None, hi=None):
        """A row of n touching mixed pieces against run r centred at a (kept within the stretch lo..hi when given:
        fewer pieces where it is short)."""
        seq = self.pick_seq(types, n)
        if not seq: return []
        widths = [2 * self.along_half(t, r) + 0.08 for t in seq]
        if lo is not None and hi is not None:
            while len(seq) > 1 and sum(widths) > hi - lo:
                seq.pop(); widths.pop()
            x = min(max(a - sum(widths) / 2, lo), hi - sum(widths))
        else:
            x = a - sum(widths) / 2
        got = []
        for t, w in zip(seq, widths):
            o = self.put_wall(t, r, x + w / 2, gap=0.25, touch=True)
            if o: got.append(o)
            elif got: break                       # a gap would leave the rest standing alone
            x += w
        if len(got) < min(2, n):
            self.remove(got)
            return []
        return got

    def row_on(self, r, lo, hi, types, spacing, least=2, ends=None, touch=False, gap=0.25):
        """A row of pieces centred on the stretch (lo, hi) of run r at even spacing; the kinds alternate symmetrically
        (A B A, A B B A); `ends`: a pair of pieces closing the row at both ends (armour stands). Symmetric pairs go in
        together, both or neither."""
        pool = self.oks(types)
        if not pool: return []
        n = min(9, max(0, int((hi - lo - 0.6) // spacing) + 1))
        if n < least: return []
        mid = (lo + hi) / 2
        kinds = self.rng.sample(pool, min(len(pool), 2 if n < 5 else 3))
        half = (n + 1) // 2
        seq_half = [kinds[i % len(kinds)] for i in range(half)]
        seq = seq_half + list(reversed(seq_half[:n // 2]))
        e = self.oks(ends or [])
        if e and n >= 3: seq[0] = seq[-1] = self.rng.choice(e)
        offs = [mid + (k - (n - 1) / 2) * spacing for k in range(n)]
        got = []
        self.f._pairing = True
        try:
            for i in range((n + 1) // 2):
                j = n - 1 - i
                o1 = self.put_wall(seq[i], r, offs[i], touch=touch, gap=gap)
                if o1 and self.F.NEEDS_FRONT.search(o1["type"]) and not self.claim_front(o1, r):
                    self.remove([o1]); o1 = None
                if i == j:
                    if o1: got.append(o1)
                    continue
                o2 = self.put_wall(seq[j], r, offs[j], touch=touch, gap=gap) if o1 else None
                if o2 and self.F.NEEDS_FRONT.search(o2["type"]) and not self.claim_front(o2, r):
                    self.remove([o2]); o2 = None
                if o1 and o2: got += [o1, o2]
                else: self.remove((o1, o2))
        finally:
            self.f._pairing = False
        return got

    # ---- the pass ---------------------------------------------------------------------------------------------------
    def essential_zones(self):
        """The floor kept clear that matters here: the doors' ways in and the space before every chest, hearth, stove
        and forge (the recipes' other `clear` zones, kept for their own composing, had left the pass no floor)."""
        f, F = self.f, self.F
        # the straight way in kept clear 4.3 units deep (review/roomscore.py's way-in rule: nothing within 4 units)
        zs = [f._way_box(op, 0.5, min(4.3, op["extent"] - 1.0)) for op in f.openings]
        self.zone_tag = {z: "door" for z in zs}
        for t, rec in f._typed:
            if not F.NEEDS_FRONT.search(t): continue
            u, v, hu, hv = rec[:4]
            for r in f.g.runs:
                hp, ha = (hu, hv) if r["line"] == "/" else (hv, hu)
                off = ((u if r["line"] == "/" else v) - r["coord"]) * r["sign"]
                along = v if r["line"] == "/" else u
                if 0 < off <= hp + 0.7 and r["lo"] - 0.5 <= along <= r["hi"] + 0.5:
                    zs.append(f.front_zone(r, u, v, max(0.8, ha) + 0.3, hp, 2.3))
                    self.zone_tag[zs[-1]] = t
        return zs

    def walk(self, extra=None):
        """(doors reached from the first, share of the walkable grid reached) of the room, as _Room.reachable_ok walks it."""
        from collections import deque
        g, AG = self.f.g, self.F.AGENT
        step = 0.5
        us = [x + y for x, y in g.cells]; vs = [x - y for x, y in g.cells]
        blocks = [p for p in g.placed if p[4]] + ([extra] if extra else [])
        grid = set()
        for i in range(int(min(us) / step) - 1, int((max(us) + 2) / step) + 1):
            for j in range(int((min(vs) - 1) / step) - 1, int((max(vs) + 1) / step) + 1):
                u, v = i * step, j * step
                if not g.inside(u, v) or g.wall_dist(u, v) < AG * 0.9: continue
                if any(abs(u - b[0]) < b[2] + AG and abs(v - b[1]) < b[3] + AG for b in blocks): continue
                grid.add((i, j))
        if not grid: return 0, 0.0
        starts = [min(grid, key=lambda k: (k[0] * step - du) ** 2 + (k[1] * step - dv) ** 2) for du, dv in g.doors] or             [next(iter(grid))]
        seen, q = set(), deque([starts[0]])
        while q:
            k = q.popleft()
            if k in seen or k not in grid: continue
            seen.add(k)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)): q.append((k[0] + d[0], k[1] + d[1]))
        return sum(1 for s_ in starts if s_ in seen), len(seen) / len(grid)

    SKIP = re.compile(r"Door|ColorLight|NPC|PlayerStart|Trigger")

    def counts(self):
        """(visible pieces, distinct kinds) of the room's own pieces: doors, lights' colour and people left out, the tiny
        loose pieces (bones, candles, small gears, tools on the ground: TINY) not counted as pieces and as one kind at
        most (the coordinator: "judge fullness by visible pieces only")."""
        from kit import objects as _O
        ts = [o["type"] for o in self.f.objects if not self.SKIP.search(o["type"])]
        big = [t for t in ts if not TINY.match(t)]
        return len(big), len({_O.kind(t) for t in big}) + (1 if len(big) < len(ts) else 0)

    def run(self):
        g = self.f.g
        saved = list(g.zones)
        self.before = self.counts()
        # a room whose shell already fails the walkability test (an L room whose doors meet it at a pinch) took nothing:
        # here a piece may stand if it cuts off no door and no more of the floor than the room had reached
        broken = not g.reachable_ok((-9999.0, -9999.0, 0.0, 0.0, True, "floor"))
        if broken:
            d0, n0 = self.walk()
            g.reachable_ok = lambda extra: (lambda r: r[0] >= d0 and r[1] >= n0 - 0.03)(self.walk(extra))
            self.log["broken shell"] += 1
        try:
            self.cur = "strip"
            self.strip()
            g.zones[:] = self.essential_zones()
            self._run()
        finally:
            g.zones[:] = saved + [z for z in g.zones if z not in saved]
            if broken: del g.reachable_ok

    def _run(self):
        # the focal group first (the watch's table, the alchemist's table): the room is arranged round it
        self.cur = "centre"
        self.middle_fill(part="centre")
        for name, kw in self.s.get("program", ()):
            self.step(name, kw)
        if self.s.get("relight"):
            self.cur = "lights"
            self.light_pairs()
        self.cur = "middle"
        self.middle_fill(part="pairs")
        self.cur = "wall"
        self.wall_fill()
        self.cur = "bare"
        self.bare_fill()
        self.cur = "topup"
        self.top_up()
        if self.s.get("hang"):
            self.step("hang_row", self.s["hang"])
        self.cur = "face"
        self.f.face_statues()                       # every statue faces into the room (GW-7)
        self.log["reach x100"] = int(100 * self.reach()[0])
        if DEBUG:
            for r in self.f.g.runs:
                self.log[f"share {self.name_of(r)} {r['hi'] - r['lo']:.0f}"] = int(100 * self.used_share(r))

    def step(self, name, kw):
        self.cur = name
        try:
            getattr(self, "step_" + name)(**kw)
        except Exception as e:                       # a step that fails leaves the room as it was
            self.log["step failed " + name + ": " + type(e).__name__] += 1
            if DEBUG: raise

    def strip(self):
        """The recipe's loose pieces taken up before the room is composed again (spec `keep`: a regex of the types that
        stay); seats left with no table or desk and rugs with no table on them go with them; the floor candelabras when
        the spec relights the room in mirrored pairs; the recipe's carpets when anything is taken up."""
        keep = self.s.get("keep")
        relight = self.s.get("relight")
        if keep is None and not relight: return
        f = self.f
        rx = re.compile(keep) if keep is not None else None
        by_rec = {id(rec): o for o in list(f.objects) for rec in [f._placed_of.get(id(o))] if rec is not None}
        for t, rec in list(f._typed):
            o = by_rec.get(id(rec))
            if o is None: continue
            light = bool(self.LIGHT_RX.match(t))
            if light and not relight: continue
            if light or (rx is not None and not rx.search(t)):
                f._remove(o); self.log["stripped"] += 1
        anchors = [rec for t, rec in f._typed if self.fam(t) in ("table", "desk", "counter_shop")]
        for t, rec in list(f._typed):
            if self.fam(t) not in ("chair", "rug"): continue
            near = any(max(abs(rec[0] - a[0]) - rec[2] - a[2], abs(rec[1] - a[1]) - rec[3] - a[3]) < 1.0 for a in anchors)
            if not near:
                o = by_rec.get(id(rec))
                if o is not None: f._remove(o); self.log["stripped seat"] += 1
        # a chest, desk or shelf the recipe left on a front wall shows the camera its back: it goes too (the walls'
        # top-up stands its own on a back wall)
        for t, rec in list(f._typed):
            if not re.match(r"^(Chest\d|Desk\d|Bookcase|PotionShelves|TraderShelves)", t): continue
            r = self.nearest_run(rec[0], rec[1])
            if r is not None and self.name_of(r) in FRONT and f.g.wall_dist(rec[0], rec[1]) < max(rec[2], rec[3]) + 0.8:
                o = by_rec.get(id(rec))
                if o is not None: f._remove(o); self.log["stripped front"] += 1
        if relight: f.ring_lights = []
        if rx is not None and getattr(f, "carpet_undo", None):
            from kit import grammar as GR
            for rec in list(f.carpet_undo):
                GR.lift_carpet(f, rec); self.log["carpet lifted"] += 1

    # ---- programme steps ---------------------------------------------------------------------------------------------
    def step_row(self, wall, types, spacing=2.2, least=2, ends=None, walls=1, touch=False, gap=0.25, most=9, back=False):
        """A row centred on the longest bare stretch of a wall, evenly spaced, the kinds mirrored (racks, gear trains,
        restraints, workstations); `walls` 2: the other back wall too in a room of 90 tiles or more."""
        rs = [self.wall_by(w) for w in ([wall] if isinstance(wall, str) else wall)]
        rs = [r for i, r in enumerate(rs) if r is not None and r not in rs[:i] and
              (not back or self.name_of(r) in BACK)]
        if walls >= 2 and self.tiles >= 90:
            rs += [r for r in (self.main.get(n) for n in BACK) if r is not None and r is not rs[0]]
        done = 0
        for r in rs:
            if r is None or (done and walls < 2): continue
            s = self.longest(r, pad=0.4)
            if not s: continue
            lo, hi = s[0] + 0.3, s[1] - 0.3
            if (hi - lo - 0.6) // spacing + 1 > most:           # a row of `most` at the stretch's middle
                c, w = (lo + hi) / 2, (most - 1) * spacing + 0.7
                lo, hi = c - w / 2, c + w / 2
            got = self.row_on(r, lo, hi, types, spacing, least, ends, touch=touch, gap=gap)
            if got: done += 1; self.log["row"] += 1
        if not done:                     # the type's must: one at least, centred on the longest bare back stretch
            for r in [self.main[n] for n in BACK if n in self.main]:
                s = self.longest(r, pad=0.3, least=1.4)
                if s and self.put_wall(self.rng.choice(self.oks(types) or types), r, (s[0] + s[1]) / 2, gap=gap):
                    self.log["row one"] += 1; break

    def step_line(self, wall, types, mix=None):
        """Shelves lining a wall end to end on its longest bare stretch (a whole wall, never one shelf here and there);
        `mix`: a pair of these at either end of the run (potion shelves among the books). A run is laid whole or not at
        all: a piece that does not fit shortens it from the ends, never leaves a gap in it."""
        r = self.wall_by(wall)
        pool = self.oks(types)
        if r is None or not pool: return
        st = sorted(self.free_stretches(r, pad=0.1), key=lambda s_: s_[0] - s_[1])[:1]
        if not st: return
        lo, hi = st[0]
        t = self.variant(self.rng.choice(pool), r, "shelves")
        if not t: return
        w = 2 * self.along_half(t, r) + 0.02
        mx = self.oks(mix or [])
        m = self.variant(self.rng.choice(mx), r, "shelves") if mx else None
        if m and abs(self.along_half(m, r) - self.along_half(t, r)) > 0.05: m = None
        for n in range(int((hi - lo) // w), 1, -1):
            x0 = (lo + hi) / 2 - n * w / 2
            seq = [t] * n
            if m and n >= 4: seq[0] = seq[-1] = m
            got = []
            self.f._pairing = True
            try:
                for k, tt in enumerate(seq):
                    o = self.put(tt, *self.uv(r, self.depth(tt, r) + 0.18, x0 + w * (k + 0.5)), touch=True, snug=True)
                    if not o: break
                    got.append(o)
            finally:
                self.f._pairing = False
            if len(got) == n:
                self.log["line"] += 1; return
            self.remove(got)

    def step_desk(self, wall="back_long"):
        """The desk with its chair centred on a back wall's bare stretch, when the recipe left none."""
        if any(re.match(r"^Desk\d$", t) for t, _ in self.f._typed): return
        for w in (wall, "back_short", "back_long"):
            r = self.wall_by(w)
            s_ = self.longest(r, pad=0.4, least=2.6) if r else None
            if not s_: continue
            o = self.put_wall("Desk1", r, (s_[0] + s_[1]) / 2, gap=0.25)
            if o:
                rec = self.f._placed_of.get(id(o))
                self.f.seats_around(rec[:2], o["type"], 1)
                self.log["desk"] += 1
                return

    def step_altar_wall(self, types, flank):
        """The holy thing on the wall across from the main door, on its axis, a pair flanking it: when the middle's square
        found no room (a narrow shrine)."""
        pool = self.oks(types)
        if not pool: return
        have = next((o for o in self.f.objects if re.match(r"^(DunMirAltar|LOTDLichGodStatue)", o["type"])), None)
        if have is not None:                        # the recipe's: flanked where it stands, if nothing flanks it yet
            if sum(1 for t, _ in self.f._typed if self.fam(t) == "statue") >= 2: return
            rec = self.f._placed_of.get(id(have))
            far = self.nearest_run(rec[0], rec[1]) if rec else None
            o = have if far is not None else None
            if o is None: return
        else:
            far = self.axis_back_run()
            o = self.put_wall(pool[0], far, self.axis_along(), gap=0.4) if far is not None else None
        if not o:                                   # else centred on a back wall's longest bare stretch
            for w in ("back_long", "back_short"):
                r = self.wall_by(w)
                st = self.longest(r, pad=0.5, least=2.0) if r else None
                if st and (o := self.put_wall(pool[0], r, (st[0] + st[1]) / 2, gap=0.4)): far = r; break
        if not o: return
        if have is None: self.log["altar on the wall"] += 1
        fl = self.oks(flank)
        rec = self.f._placed_of.get(id(o))
        if fl and rec:                              # a pair flanking it along its wall
            a = rec[1] if far["line"] == "/" else rec[0]
            ah = rec[3] if far["line"] == "/" else rec[2]
            m = max(self.half(fl[0]))
            self.f._pairing = True
            try:
                for off in (ah + m + 0.5, ah + m + 0.9, ah + m + 1.4):
                    p1 = self.put_wall(fl[0], far, a - off, gap=0.4)
                    p2 = self.put_wall(fl[0], far, a + off, gap=0.4) if p1 else None
                    if p1 and p2: self.log["flank pair"] += 1; break
                    self.remove((p1, p2))
            finally:
                self.f._pairing = False

    def step_must_statues(self, types):
        """The type's statues (its profile's must) as a pair in the two side corners when nothing else stood them."""
        need = ((self.F.room_profile(self.f.kind) or {}).get("must") or {}).get("statue", 0)
        if sum(1 for t, _ in self.f._typed if self.fam(t) == "statue") >= need: return
        self.step_corner_pair(("W", "E"), types)
        if sum(1 for t, _ in self.f._typed if self.fam(t) == "statue") < need:
            self.step_corner_pair(("N", "S"), types)
        # a small room crowded by its doors: one centred on each wall's longest bare stretch, back walls first
        for n in ("NE", "NW", "SE", "SW"):
            if sum(1 for t, _ in self.f._typed if self.fam(t) == "statue") >= need: break
            r = self.main.get(n)
            st = self.longest(r, pad=0.4, least=1.6) if r else None
            pool = self.oks(types)
            if st and pool:
                self.f._pairing = True
                try:
                    if self.put_wall(pool[0], r, (st[0] + st[1]) / 2, gap=0.5): self.log["must statue"] += 1
                finally:
                    self.f._pairing = False

    def step_hang_row(self, pat, most=2):
        """Hangings on the bare stretches of the back walls, centred, a pair evenly spaced on a long stretch."""
        pool = sorted(t for t in self.f.things if re.match(pat, t) and self.ok(t))
        if not pool: return
        placed = 0
        for n in BACK:
            r = self.main.get(n)
            if not r or placed >= most: continue
            st = [(a, b) for a, b in self.free_stretches(r, pad=0.3, hang=True) if b - a >= 2.0]
            if not st: continue
            lo, hi = max(st, key=lambda s: s[1] - s[0])
            k = 2 if hi - lo >= 6.0 else 1
            t0 = self.rng.choice(pool)
            got = [self.put_hang(t0, r, lo + (hi - lo) * (i + 1) / (k + 1)) for i in range(k)]
            if k == 2 and not all(got): self.remove(got); got = [self.put_hang(t0, r, (lo + hi) / 2)]
            placed += sum(1 for o in got if o)

    def step_corner_group(self, corner, group):
        """One of the free groups a step out of a corner (the S corner's chart table): the dead corner used."""
        c = self.corner(corner)
        if not c: return
        for k in (3.2, 3.8, 2.8, 4.6):
            if self.free_group(group, c[0] + c[2] * k, c[1] + c[3] * k):
                self.log["corner group"] += 1; return

    def step_corner_heap(self, corner, types, n):
        c = self.corner(corner)
        if not c: return
        n = n + (1 if self.tiles > 80 else 0) + (1 if self.tiles > 140 else 0)
        if self.heap_at(*c, types, n): self.log["corner heap"] += 1

    def step_corner_pair(self, corners, types, heap=1, light=False):
        """The same piece (or heap, mirrored) in two matching corners: both or neither."""
        cs = [self.corner(c) for c in corners]
        if not all(cs): return
        seq = self.pick_seq(types, heap)
        if not seq: return
        if light: self.f.placing_light = True
        self.f._pairing = True
        try:
            got = []
            for k, c in enumerate(cs):
                one = []
                for i, t in enumerate(seq):
                    hu, hv = self.half(t)
                    du, dv = 0.45 + hu + (2 * hu + 0.08) * i, 0.45 + hv
                    if k == 1: du, dv = 0.45 + hu, 0.45 + hv + (2 * hv + 0.08) * i      # mirrored: along the other wall
                    o = self.put(t, c[0] + c[2] * du, c[1] + c[3] * dv, touch=True)
                    if not o: break
                    one.append(o)
                got.append(one)
        finally:
            self.f._pairing = False
            self.f.placing_light = False
        if len(got[0]) != len(got[1]) or not got[0] or (heap > 1 and len(got[0]) < 2):
            for one in got: self.remove(one)
        else:
            self.log["corner pair"] += 1

    def step_centred(self, types, wall):
        """A piece centred on the longest bare stretch of a wall (a chest, an ogre's hoard chest)."""
        r = self.wall_by(wall)
        pool = self.oks(types)
        if r is None or not pool: return
        s = self.longest(r, pad=0.5, least=2.0)
        if s and self.put_wall(self.rng.choice(pool), r, (s[0] + s[1]) / 2, gap=0.25): self.log["centred"] += 1

    def step_around(self, pat, types, d=2.0, heaps=False):
        """Pieces about an anchor (bones by the rack, gears and a lever by the winch, meat by the hoard's chest) in a
        mirrored pair along the room's long axis, else across it."""
        anchor = next((rec for t, rec in self.f._typed if re.match(pat, t)), None)
        pool = self.oks(types)
        if anchor is None or not pool: return
        u, v = anchor[0], anchor[1]
        offs = [(d + anchor[2], 0), (0, d + anchor[3])] if self.axis_long == "u" else [(0, d + anchor[3]), (d + anchor[2], 0)]
        for du, dv in offs:
            if heaps:
                a = self.bone_heap(u - du, v - dv); b = self.bone_heap(u + du, v + dv) if a else []
                if a and b: self.log["around"] += 1; return
                self.remove(a + b)
            else:
                t = self.rng.choice(pool)
                bl = self.fam(t) is not None
                a = self.put(t, u - du, v - dv, blocking=bl); b = self.put(t, u + du, v + dv, blocking=bl) if a else None
                if a and b: self.log["around"] += 1; return
                self.remove((a, b))

    def bone_heap(self, u, v):
        pool = self.oks(BONES)
        if not pool: return []
        got = []
        offs = [(0, 0), (0.95, 0.2), (-0.6, 0.8), (0.3, -0.95), (-0.95, -0.4)]     # (a bone is 0.74 across)
        for i, (du, dv) in enumerate(offs[:self.rng.randint(3, 5)]):
            o = self.put(pool[i % len(pool)], u + du, v + dv, blocking=False)
            if o: got.append(o)
        if len(got) < 2: self.remove(got); return []
        return got

    def step_brick_square(self, pat):
        """The forge (a cinder bin) on a small bordered square of brick, centred under it ("place furnaces on a small
        brick square", nox17; "the brick hearth around the stove is not properly bordered", nox21)."""
        for t, rec in list(self.f._typed):
            if re.search(pat, t):
                if brick_square(self.f, rec[0], rec[1]): self.log["brick square"] += 1
                return

    def light_pairs(self):
        """Floor lights in mirrored pairs: the two side corners (W and E on screen), then the N and S corners; Westwood's
        count for the room's size at most (kit/objects.py light_cap), none in a dark store (`lights_per100` 0)."""
        f = self.f
        lp = f.ident.get("lights_per100")
        if lp is not None and lp <= 0: return
        try:
            lt = f.light_type()
        except Exception:
            lt = None
        if not lt or not self.ok(lt): lt = next((t for t in ("Candleabra3", "Candleabra1") if self.ok(t)), None)
        if not lt: return
        from kit import objects as OBJ
        from kit import objects as _O
        have = sum(1 for t, _ in f._typed if self.LIGHT_RX.match(t) or _O.category(t) == "light")
        want = min(OBJ.light_cap(self.tiles), 2 if self.tiles < 70 else 4) - have
        hu, hv = self.half(lt)
        f.placing_light = True
        try:
            for pair in (("W", "E"), ("N", "S")):
                if want < 2: break
                cs = [self.corner(c) for c in pair]
                if not all(cs): continue
                for inset in (0.75, 1.1, 1.5, 2.0):
                    p = [(c[0] + c[2] * (inset + hu), c[1] + c[3] * (inset + hv)) for c in cs]
                    if any(f._before_anchor(*q) for q in p): continue
                    o1 = self.put(lt, *p[0]); o2 = self.put(lt, *p[1]) if o1 else None
                    if o1 and o2:
                        want -= 2; self.log["light pair"] += 1
                        f.ring_lights += p
                        break
                    self.remove((o1, o2))
            # no corner would take a pair and the room has no light left: a ceremonial room's pair by its side walls,
            # mirrored across the axis; another room's one centred on each back wall's longest bare stretch
            dark = not any(self.LIGHT_RX.match(t) or _O.category(t) == "light" for t, _ in f._typed)
            if dark and self.s.get("mirror"):
                D, W = getattr(self, "_axis_dw", (0.0, 0.0))
                done = False
                for d in (D * 0.5, D * 0.3, D * 0.7, D - 1.5):
                    for off in (W - 0.8, W - 1.3, W - 2.0):
                        if D >= 4 and off >= 1.0 and self.pair_at(lt, d, off, light=True):
                            self.log["light side pair"] += 1; done = True; break
                    if done: break
            elif dark:
                for n in BACK:
                    r = self.main.get(n)
                    s = self.longest(r, pad=0.4, least=1.2) if r else None
                    if s and self.put_wall(lt, r, (s[0] + s[1]) / 2, gap=0.3): self.log["light wall"] += 1
        finally:
            f.placing_light = False

    # ---- the ceremonial axis -----------------------------------------------------------------------------------------
    def axis_back_run(self):
        """The wall across from the main door."""
        op = self.f.main_door()
        if not op: return None
        cands = [r for r in self.f.g.runs if r["line"] == op["line"] and r["sign"] == -op["sign"] and
                 r["lo"] - 0.5 <= op["along"] <= r["hi"] + 0.5]
        return max(cands, key=lambda r: abs(r["coord"] - op["coord"]), default=None)

    def axis_along(self):
        """The along coordinate of the room's axis: the main door's line (the user: "Chapels should always be aligned
        with the main door. The character should walk in and be on the main path facing the altar"), the centrepiece's
        when it stands within a unit of it."""
        if hasattr(self, "_axis_a"): return self._axis_a
        op = self.f.main_door()
        a = self.cv if not op else op["along"]
        far = self.axis_back_run() if op else None
        if far:
            # a door well off the middle of the room: the room is composed about its own middle (the door's line would
            # leave it lopsided); the middle of the far wall's floor
            st = self.interior(far)
            if st:
                lo, hi = max(st, key=lambda s_: s_[1] - s_[0])
                mid = (lo + hi) / 2
                if abs(mid - a) > 2.0: a = mid
            for t, rec in self.f._typed:
                if re.match(r"^(DunMirAltar|LOTDLichGodStatue)", t):
                    al = rec[1] if far["line"] == "/" else rec[0]
                    if abs(al - a) <= 1.0: a = al
        self._axis_a = a
        return a

    def mirror(self, u, v):
        op = self.f.main_door()
        if op is None: return (2 * self.cu - u, v)
        a0 = self.axis_along()
        return (u, 2 * a0 - v) if op["line"] == "/" else (2 * a0 - u, v)

    def at(self, d, off):
        """uv at depth d from the main door's wall, `off` along it from the axis."""
        op = self.f.main_door()
        return self.f._uv_on(op_run(op), d, self.axis_along() + off)

    def pair_at(self, t, d, off, light=False, t2=None):
        """t at both (d, -off) and (d, +off) (t2 on the + side when given): both or neither."""
        self.f._pairing = True
        if light: self.f.placing_light = True
        try:
            o1 = self.put(t, *self.at(d, -off))
            o2 = self.put(t2 or t, *self.at(d, off)) if o1 else None
        finally:
            self.f._pairing = False
            self.f.placing_light = False
        if o1 and o2: return [o1, o2]
        self.remove((o1, o2))
        return []

    def step_axis(self, runner=False, benches=(), flank=(), pairs=(), hang=None, coffins=False, tomb=False,
                  chest=False, avenue=(), ring=None):
        """A ceremonial room composed on the axis from the main door to the wall across from it ("chapels should have a
        much more symmetric layout. The carpet that runs down the middle with benches and / or pillars ... evenly and
        symmetrically placed on either side and an altar at the end, centered"): the centrepiece on the axis (the
        recipe's altar on the far wall, a great tomb in the middle, a crypt chest), the flanking pair beside the far
        wall's centrepiece, a runner down the axis, an avenue of pillars in mirrored pairs at even steps either side of
        it, benches in mirrored pairs, lights or basins in the two far corners (and the near ones in a big room), coffins
        in mirrored pairs along the side walls, hangings in a pair on the far wall; a ring of obelisks round a basin in
        the middle of a big shrine."""
        f = self.f
        op = f.main_door()
        far = self.axis_back_run()
        if not op or not far:
            self.log["axis: no door or far wall"] += 1; return
        D = abs(far["coord"] - op["coord"])
        sides = [r for r in f.g.runs if r["line"] != op["line"]]
        a0 = self.axis_along()
        lo_r = max((r for r in sides if r["sign"] == 1 and r["coord"] < a0), key=lambda r: r["coord"], default=None)
        hi_r = min((r for r in sides if r["sign"] == -1 and r["coord"] > a0), key=lambda r: r["coord"], default=None)
        if not lo_r or not hi_r:
            self.log["axis: no side walls"] += 1; return
        W = min(a0 - lo_r["coord"], hi_r["coord"] - a0)       # the half width the composition mirrors into
        self.log[f"axis D{D:.0f} W{W:.1f}"] += 1
        self._axis_dw = (D, W)
        if W < 2.5 or D < 5: return
        mid_d = D * 0.5
        if tomb and not any(re.match(r"^Crypt\d", t) for t, _ in f._typed):   # the great tomb in the middle
            tt = self.oks(["Crypt1", "Crypt3", "Crypt5", "Crypt7", "Crypt9", "Crypt11"])
            done = False
            for t in self.rng.sample(tt, len(tt)):
                hu, hv = self.half(t)
                if (hu > hv) != (op["line"] == "/"): continue
                for k in (0.5, 0.55, 0.45, 0.6):
                    if self.put(t, *self.at(D * k, 0)):
                        self.log["great tomb"] += 1; mid_d = D * k; done = True; break
                if done: break
        if chest:
            ct = self.oks(["CryptChest1", "CryptChest2", "CryptChest3", "CryptChest4"])
            if ct and self.put_wall(ct[0], far, a0, gap=0.3): self.log["axis chest"] += 1
        # the runner from the door to the centrepiece, centred on the axis: a carpet of 2-unit squares is centred on a
        # square's middle (even coordinates) with 3 squares, between two squares with 2
        rw = 0.0
        even = abs(a0 / 2 - round(a0 / 2)) < 0.26
        if runner and W >= (7.0 if even else 4.5) and abs(a0 - op["along"]) < 0.6:
            w = 2.2 if even else 1.6
            p0 = op["coord"] + op["sign"] * 3.0
            p1 = op["coord"] + op["sign"] * ((mid_d - 1.8) if tomb else (D - 2.6))
            box = (min(p0, p1), max(p0, p1), a0 - w, a0 + w) if op["line"] == "/" else (a0 - w, a0 + w, min(p0, p1),
                                                                                         max(p0, p1))
            try:
                if f.lay_carpet(box, margin=0.0): self.log["runner"] += 1; rw = 6.0 if even else 4.0   # its full width
            except Exception:
                pass
        fl = self.oks(flank)
        if fl:                                    # the flanking pair beside the far wall's centrepiece
            t = self.rng.choice(fl)
            m = max(self.half(t)) + 0.6
            for off in (2.4, 2.9, 3.4, 2.0, 3.9, 4.4, 5.0):     # (wider: past a row of chests before the wall)
                if off + m > W - 0.3: continue
                if self.pair_at(t, D - m, off): self.log["flank pair"] += 1; break
        av = self.oks(avenue)
        if av:                                    # the avenue of pillars at even steps either side of the runner
            t = self.rng.choice(av)
            m = max(self.half(t))
            off = max(rw / 2 + m + 0.5, 1.9, op["half"] + m + 0.35)     # lining the way in (and the runner), never in it
            if off + m < W - 0.6:
                d0, d1 = 3.6, ((mid_d - 2.4) if tomb else D - 4.0)
                n = max(1, int((d1 - d0) // 3.2) + 1) if d1 >= d0 else 0
                for k in range(n):
                    d = d0 + k * (d1 - d0) / (n - 1) if n > 1 else (d0 + d1) / 2
                    if self.pair_at(t, d, off): self.log["avenue pair"] += 1
                if tomb:                          # and beyond the tomb, the same pillars
                    for d in (mid_d + 2.6,):
                        if d < D - 2.4 and self.pair_at(t, d, off): self.log["avenue pair"] += 1
        bt = self.oks(benches)
        if bt and W >= 5.0:                       # benches in mirrored pairs further out
            t = self.bench_variant(self.rng.choice(bt), op)
            m = max(self.half(t))
            for frac in ((0.5,) if self.f.kind == "shrine" else (0.4, 0.62)):
                for off in (W * 0.55, W * 0.5, W * 0.62):
                    if off - m < rw / 2 + 2.2 or off + m > W - 0.5: continue
                    if self.pair_at(t, D * frac, off): self.log["bench pair"] += 1; break
        pt = self.oks(pairs)
        if pt:                                    # lights, basins or obelisks in the two far corners (and near ones)
            t = self.rng.choice(pt)
            m = max(self.half(t)) + 0.6
            light = bool(re.search(r"Basin|Candle|Brazier", t))
            for d in ((D - m, 3.2) if self.tiles >= 40 else (D - m,)):
                for off in (W - m, W - m - 0.5, W - m - 1.0):
                    if self.pair_at(t, d, off, light=light): self.log["corner pair"] += 1; break
        if coffins:                               # coffins in mirrored pairs along the side walls, end to the wall
            ct = self.oks(COFFINS)
            if ct:
                base = self.rng.choice(ct)
                t1, t2 = self.variant(base, lo_r, "tomb") or base, self.variant(base, hi_r, "tomb") or base
                fracs = (0.38, 0.66) if D >= 12 and coffins != 1 else (0.55,)
                for frac in fracs:
                    for dd in (0.0, 0.6, -0.6):
                        perp = self.depth(t1, lo_r)
                        if self.pair_at(t1, D * frac + dd, W - perp - 0.4, t2=t2): self.log["coffin pair"] += 1; break
        if ring and self.tiles >= 60 and W >= 6.5:
            self.ring_at(ring, D * 0.45)
        need = ((self.F.room_profile(f.kind) or {}).get("must") or {}).get("statue", 0)
        if need and sum(1 for t, _ in f._typed if self.fam(t) == "statue") < need:
            st = self.oks(["Statue2a", "Statue2c", "Obelisk", "LOTDManaObelisk"])
            for t in st:
                m = max(self.half(t)) + 0.6
                for off in (2.2, 2.8, 1.8, 3.4):
                    if off + m <= W - 0.3 and self.pair_at(t, D - m - 0.4, off): self.log["must pair"] += 1; break
                else: continue
                break
        if hang and self.name_of(far) in BACK:    # a pair of hangings on the far wall either side of the centrepiece
            pool = sorted(t for t in f.things if re.match(hang, t) and self.ok(t))
            if pool:
                t0 = self.rng.choice(pool)
                for off in (4.6, 5.2, 4.0, 3.6):
                    if off > W - 0.8: continue
                    o1 = self.put_hang(t0, far, a0 - off); o2 = self.put_hang(t0, far, a0 + off) if o1 else None
                    if o1 and o2: self.log["hanging pair"] += 1; break
                    self.remove((o1, o2))

    def ring_at(self, spec, d):
        """Four pillars round a centre piece at depth d on the axis, at the room's screen axes, the carpet under them
        centred on the ring (the ring's centre snapped to a floor square's middle)."""
        ring_t, centre_t = spec
        rt, ct = self.oks([ring_t]), self.oks([centre_t])
        if not rt: return
        u, v = self.at(d, 0)
        u, v = 2 * round(u / 2), 2 * round(v / 2)
        R = 2.0
        f = self.f
        f._pairing = True
        got = []
        try:
            for du, dv in ((R, R), (-R, -R), (R, -R), (-R, R)):
                o = self.put(rt[0], u + du, v + dv)
                if not o: break
                got.append(o)
        finally:
            f._pairing = False
        if len(got) < 4:
            self.remove(got); return
        if ct:
            f.placing_light = bool(re.search(r"Basin", ct[0]))
            try:
                self.put(ct[0], u, v)
            finally:
                f.placing_light = False
        if not f.carpet_boxes:
            try:
                f.lay_carpet((u - R - 0.9, u + R + 0.9, v - R - 0.9, v + R + 0.9), margin=0.0)
            except Exception:
                pass
        self.log["ring"] += 1

    def bench_variant(self, t, op):
        """A bench turned to face the far wall (its long side across the axis)."""
        hu, hv = self.half(t)
        want_long_u = op["line"] == "\\"          # the axis runs along v when the door wall is a "\" line
        if (hu > hv) == want_long_u: return t
        m = re.fullmatch(r"(.*?)(\d)", t)
        if m:
            for d in "123456":
                s = f"{m.group(1)}{d}"
                if self.ok(s):
                    a, b = self.half(s)
                    if (a > b) == want_long_u: return s
        return t

    # ---- the walls ----------------------------------------------------------------------------------------------------
    def used_share(self, r):
        """The share of run r's usable length (less its doorways) pieces stand against."""
        def total(ivs):
            out, cur = 0.0, None
            for a, b in sorted(ivs):
                if b <= a: continue
                if cur and a <= cur[1]: cur[1] = max(cur[1], b)
                else:
                    if cur: out += cur[1] - cur[0]
                    cur = [a, b]
            return out + (cur[1] - cur[0] if cur else 0.0)
        inner = sum(b - a for a, b in self.interior(r)) or 0.5
        cut = total([(max(r["lo"], a), min(r["hi"], b)) for a, b in self.door_cuts(r)])
        used = total([(max(r["lo"], a), min(r["hi"], b)) for a, b in self.wall_pieces(r)])
        return min(1.0, used / max(0.5, inner - cut))

    def wall_fill(self):
        """Every wall used toward the type's share (back walls more, front walls a secondary group), a unit at a time
        centred on the longest bare stretch of the wall furthest below its share ("centred on a wall, or centred between
        another object and a wall", the v0.6 playtest), the kinds in turn so no wall repeats one piece; mirrored across
        the axis in a ceremonial room."""
        w = self.s.get("walls")
        if not w: return
        tb, tf = w.get("fill", (0.5, 0.3))
        most = dict(UNIT_MOST, **(w.get("most") or {}))
        failed, turn, used = set(), Counter(), Counter()
        for _ in range(40):
            cands = []
            for r in self.f.g.runs:
                if r["hi"] - r["lo"] < 2.4: continue
                tgt = tb if self.name_of(r) in BACK else tf
                frac = self.used_share(r)
                if frac >= tgt: continue
                sts = [(lo, hi) for lo, hi in self.free_stretches(r, pad=0.35) if hi - lo >= 1.3 and
                       (id(r), round(lo, 1)) not in failed]
                if not sts: continue
                lo, hi = max(sts, key=lambda s: s[1] - s[0])
                cands.append(((tgt - frac) * (r["hi"] - r["lo"]), r, lo, hi))
            if not cands: break
            _, r, lo, hi = max(cands, key=lambda c: c[0])
            side = "back" if self.name_of(r) in BACK else "front"
            units = list(w.get(side) or []) + (["filler"] if w.get(side) else [])
            k0, got = turn[side], None
            for i in range(len(units)):
                unit = units[(k0 + i) % len(units)]
                if used[unit] >= most.get(unit, 99) * (2 if self.tiles >= 120 else 1): continue
                if self.over_repeat(unit): continue
                if unit in ("heap", "filler") and not self.supplies_line and self.supply_share(r) >= 0.22: continue
                L = hi - lo
                for a in ((lo + hi) / 2, lo + L / 4, hi - L / 4) if L >= 3.0 else ((lo + hi) / 2,):
                    got = self.wall_unit(unit, r, lo, hi, exact=None if a == (lo + hi) / 2 else a)
                    if got: break
                if got:
                    turn[side] = k0 + i + 1
                    used[unit] += 1
                    self.log["wall " + unit] += 1
                    if self.s.get("mirror"): self.mirror_unit(unit, r, (lo + hi) / 2, got)
                    break
            if not got: failed.add((id(r), round(lo, 1)))

    def over_repeat(self, unit):
        """Whether one more of a unit (its mirrored twin too) would pass the type's repeat rule (spec `repeat`: at most
        so many pieces of a kind in the room; tiny pieces aside)."""
        rep = self.s.get("repeat") or (self.s.get("statue_most") if unit == "statue" else None)
        pal = (self.s.get("pal") or {}).get(unit)
        if not rep or not pal: return False
        from kit import objects as _O
        ks = {_O.kind(t) for t in pal if not TINY.match(t)}
        have = sum(1 for o in self.f.objects if _O.kind(o["type"]) in ks)
        return have + (2 if self.s.get("mirror") else 1) > rep

    @property
    def supplies_line(self):
        return bool((self.F.room_profile(self.f.kind) or {}).get("supplies_line"))

    def supply_share(self, r):
        """The share of run r's length that barrels, crates and sacks stand against (the checker's identity.supplies_wall
        warns past half a wall outside a store)."""
        L = sum(b - a for a, b in self.interior(r)) or 1.0
        tot = 0.0
        for t, rec in self.f._typed:
            if not re.search(r"Barrel|Crate|Sack", t) or rec[5] == "wall": continue
            perp, along = (rec[0], rec[1]) if r["line"] == "/" else (rec[1], rec[0])
            dp, da = (rec[2], rec[3]) if r["line"] == "/" else (rec[3], rec[2])
            off = (perp - r["coord"]) * r["sign"]
            if 0 < off and off - dp <= 1.3 and r["lo"] - 0.3 <= along <= r["hi"] + 0.3: tot += 2 * da
        return tot / L

    def top_up(self):
        """Never emptier than the recipe left it (the coordinator, 2026-10-13: "Every type you touch must end with at least
        as many objects and kinds as its current version, and more in large rooms"): while the room holds fewer pieces
        or kinds than before the pass (a tenth more pieces in a room of 80 tiles), the walls take more of the type's
        units (their shares raised a step at a time), then the type's extra small pieces beside what stands."""
        n0, k0 = self.before
        # the floor: what the recipe left, and the lab's own average for the type on master (objects a tile, kinds a
        # room: spec `least`), a tenth more in a room of 80 tiles
        per, kinds = self.s.get("least", (0.0, 0))
        big = 1.1 if self.tiles >= 80 else 1.0
        tn = int(max(n0, per * self.tiles) * big + 0.99)
        k0 = max(k0, kinds - (1 if self.tiles < 40 else 0))
        w = self.s.get("walls")
        for step in range(1, 5):
            n, k = self.counts()
            if n >= tn and k >= k0: break
            if w:
                tb, tf = w.get("fill", (0.5, 0.3))
                most = {u: m * (1 if self.s.get("repeat") else step + 1)       # (a repeat rule: as many as before)
                        for u, m in dict(UNIT_MOST, **(w.get("most") or {})).items()}
                saved = self.s
                self.s = dict(saved, walls=dict(w, fill=(min(0.95, tb + 0.12 * step), min(0.8, tf + 0.12 * step if tf
                                                                                         else 0.0)), most=most))
                try:
                    self.wall_fill()
                finally:
                    self.s = saved
            n, k = self.counts()
            if n < tn or k < k0: self.extras(tn - n)
            if step >= 2 and (n < tn or k < k0):         # past the walls: the middle's groups at the bare spots too
                saved = self.s
                self.s = dict(saved, bare=True, goal=0.95)
                try:
                    self.bare_fill()
                finally:
                    self.s = saved
        n, k = self.counts()
        self.log[f"count {n0}->{n} kinds {k0}->{k}"] += 1

    def extras(self, want):
        """Small pieces of the type's own (spec `extra`: bones, gears, jars, sacks...) set beside the room's pieces, a
        new kind first."""
        from kit import objects as _O
        pool = self.oks(self.s.get("extra") or [])
        if not pool: return
        have = {_O.kind(o["type"]) for o in self.f.objects}
        pool.sort(key=lambda t: _O.kind(t) in have)
        want = max(want, sum(1 for t in pool if _O.kind(t) not in have))
        placed = 0

        most = self.s.get("repeat", 99)      # the type's repeat rule (spec `repeat`: at most so many of a kind)

        def room_for(t):
            if TINY.match(t): return True
            k = _O.kind(t)
            cap = min(most, 3) if self.fam(t) == "statue" else most      # (a statue's kind: three at most)
            return sum(1 for o in self.f.objects if _O.kind(o["type"]) == k) < cap

        def on_walls(cands, back=False):
            nonlocal placed
            have = {_O.kind(o["type"]) for o in self.f.objects}
            rest = sorted(cands, key=lambda t: _O.kind(t) in have)
            for r in sorted(self.f.g.runs, key=lambda r: (self.name_of(r) not in BACK, r["lo"] - r["hi"])):
                if back and self.name_of(r) not in BACK: continue
                for lo, hi in self.free_stretches(r, pad=0.35):
                    rest = [t for t in rest if room_for(t)]
                    if placed >= want or not rest: return
                    t = rest[0]
                    L = hi - lo
                    if L < 2 * max(self.half(t)) + 0.3: continue
                    for a in ((lo + hi) / 2, lo + L / 4, hi - L / 4) if L >= 3.0 else ((lo + hi) / 2,):
                        if self.put_wall(t, r, a, gap=0.3):
                            placed += 1; rest = rest[1:] + rest[:1]; break

        # a chest or a case stands against a wall (a bare stretch, a back wall first), never loose on the floor
        on_walls([t for t in pool if CASED.search(t) and not TINY.match(t)], back=True)
        loose = [t for t in pool if not CASED.search(t) or TINY.match(t)]
        anchors = [rec for t, rec in self.f._typed if rec[5] != "wall" and rec[4]]
        self.rng.shuffle(anchors)
        n = 0
        for rec in anchors:
            cands = [t for t in loose if room_for(t)]
            if placed >= want or not cands: break
            t = cands[n % len(cands)]; n += 1
            hu, hv = self.half(t)
            bl = self.fam(t) not in (None, "rug")
            for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if self.put(t, rec[0] + du * (rec[2] + hu + 0.25), rec[1] + dv * (rec[3] + hv + 0.25), blocking=bl):
                    placed += 1; break
        # what found no room beside a piece: on a bare stretch of wall, new kinds first
        on_walls([t for t in pool if not CASED.search(t) or TINY.match(t)])
        self.log["extras"] += placed

    def mirror_unit(self, unit, r, a, got):
        """The same unit at the mirrored spot across the room's axis: both or neither (mirrored from where the unit
        actually stands, not from the stretch it was given)."""
        recs = [self.f._placed_of.get(id(o)) for o in got]
        recs = [q for q in recs if q is not None]
        if recs:
            al = [(q[1], q[3]) if r["line"] == "/" else (q[0], q[2]) for q in recs]
            a = (min(x - h for x, h in al) + max(x + h for x, h in al)) / 2
        u, v = self.uv(r, 1.0, a)
        mu, mv = self.mirror(u, v)
        mr = self.nearest_run(mu, mv)
        if mr is None or (mr is r and abs((mv if r["line"] == "/" else mu) - a) < 1.5): return
        ma = mv if mr["line"] == "/" else mu
        # (both or neither; a niche under 40 tiles keeps its one unit: an empty room is the worse fault, theme 1)
        if not self.wall_unit(unit, mr, ma - 2.0, ma + 2.0, exact=ma) and self.tiles >= 40: self.remove(got)

    def wall_unit(self, unit, r, lo, hi, exact=None):
        """One unit of the type's wall furniture centred on the stretch (lo, hi) of run r. Returns the pieces placed."""
        pal = self.s.get("pal") or {}
        a = exact if exact is not None else (lo + hi) / 2
        L = hi - lo
        if unit == "heap":
            p = pal.get("heap") or []
            n = 2 if L < 3.0 else (3 if L < 5.0 else 4)
            return self.wall_heap(r, a, p, n, lo, hi) if p else []
        if unit == "racks":                         # a centred row of racks (two or more), else one
            if L >= 4.4 and exact is None:
                got = self.row_on(r, lo + 0.3, hi - 0.3, pal.get("rack") or ARMS_RACKS, 2.2, 2, pal.get("rack_ends"))
                if got: return got
            unit = "rack"
        if unit in ("rack", "chest", "bench", "statue", "restraint", "piece", "coffin", "monument", "grave"):
            p = self.oks(pal.get(unit) or [])
            if not p: return []
            t0 = self.rng.choice(p)
            ah = max(self.half(t0))
            if L < 2 * ah + 0.2: return []
            a = min(max(a, lo + ah + 0.1), hi - ah - 0.1)
            gap = {"bench": 0.3, "restraint": 0.45, "statue": 0.5, "coffin": 0.35}.get(unit, 0.25)
            if unit == "statue": self.f._pairing = True
            try:
                o = self.put_wall(t0, r, a, gap=gap)
            finally:
                self.f._pairing = False
            if o and self.F.NEEDS_FRONT.search(o["type"]) and not self.claim_front(o, r):
                self.remove([o]); return []
            return [o] if o else []
        if unit == "shelves":                       # a run of shelves end to end on the stretch
            p = self.oks(pal.get("shelf") or [])
            if not p or L < 2.0: return []
            t = self.variant(self.rng.choice(p), r, "shelves")
            if not t: return []
            wd = 2 * self.along_half(t, r) + 0.02
            n = max(1, min(int((L - 0.2) // wd), pal.get("shelf_n", 6)))
            if n < 2: return []
            x0 = a - n * wd / 2
            got = []
            self.f._pairing = True
            try:
                for k in range(n):
                    o = self.put(t, *self.uv(r, self.depth(t, r) + 0.18, x0 + wd * (k + 0.5)), touch=True, snug=True)
                    if not o: break
                    got.append(o)
            finally:
                self.f._pairing = False
            if len(got) < n: self.remove(got); return []          # whole, never with a gap
            return got
        if unit == "ends":                          # a pair of one piece at both ends of the stretch (telescopes)
            p = self.oks(pal.get("ends") or [])
            if not p or L < 4.0 or exact is not None: return []
            t0 = self.rng.choice(p)
            ah = max(self.half(t0))
            self.f._pairing = True
            try:
                o1 = self.put_wall(t0, r, lo + ah + 0.3)
                o2 = self.put_wall(t0, r, hi - ah - 0.3) if o1 else None
            finally:
                self.f._pairing = False
            if o1 and o2: return [o1, o2]
            self.remove((o1, o2)); return []
        if unit == "bones":
            return self.bone_heap(*self.uv(r, 0.8, a))
        if unit == "filler":                        # a short stretch: a piece or two snug against what bounds it
            p = pal.get("heap") or []
            seq = self.pick_seq(p, 2)
            for end in (0, 1):
                got, x = [], (lo if end == 0 else hi)
                for t in seq:
                    w = 2 * self.along_half(t, r) + 0.06
                    if (hi - lo) < w + 0.1: break
                    o = self.put_wall(t, r, x + w / 2 if end == 0 else x - w / 2, touch=True)
                    if not o: break
                    got.append(o)
                    x = x + w if end == 0 else x - w
                    if L < 2 * w + 0.3: break
                if got: return got
            return []
        return []

    def claim_front(self, o, r):
        """The space before a chest (as the checker looks: 2.6 units out, its width and a little) is clear of every
        blocking piece and floor light; it is kept clear from now on. False if something stands there."""
        f = self.f
        rec = f._placed_of.get(id(o))
        if rec is None: return True
        u, v, hu, hv = rec[:4]
        hp, ha = (hu, hv) if r["line"] == "/" else (hv, hu)
        z = f.front_zone(r, u, v, max(0.8, ha) + 0.4, hp, 2.4)
        for t, q in f._typed:
            if q is rec or q[5] == "wall" or self.fam(t) in ("rug",): continue
            if q[0] + q[2] > z[0] and q[0] - q[2] < z[1] and q[1] + q[3] > z[2] and q[1] - q[3] < z[3]: return False
        f.g.zones.append(z)
        return True

    def nearest_run(self, u, v):
        best = None
        for r in self.f.g.runs:
            a = v if r["line"] == "/" else u
            if not r["lo"] - 0.5 <= a <= r["hi"] + 0.5: continue
            d = abs((u if r["line"] == "/" else v) - r["coord"])
            if best is None or d < best[0]: best = (d, r)
        return best and best[1]

    # ---- the middle ---------------------------------------------------------------------------------------------------
    def axis_slots(self):
        """A ceremonial room's middle spots, mirrored across its axis from the main door: the centre on the axis half way
        in, pairs on the axis before and beyond it, and pairs either side of it."""
        f = self.f
        op, far = f.main_door(), self.axis_back_run()
        if not op or not far: return None
        D = abs(far["coord"] - op["coord"])
        a0 = self.axis_along()
        sides = [r for r in f.g.runs if r["line"] != op["line"]]
        lo_r = max((r for r in sides if r["sign"] == 1 and r["coord"] < a0), key=lambda r: r["coord"], default=None)
        hi_r = min((r for r in sides if r["sign"] == -1 and r["coord"] > a0), key=lambda r: r["coord"], default=None)
        if not lo_r or not hi_r: return None
        W = min(a0 - lo_r["coord"], hi_r["coord"] - a0)
        step = (self.s.get("middle") or {}).get("step", 5.5)

        def ok(p): return f.g.inside(*p) and f.g.wall_dist(*p) >= 2.2
        centre = [p for p in (self.at(D / 2 + dd, 0) for dd in (0, 0.8, -0.8, 1.6, -1.6)) if ok(p)]
        pairs = []
        k = 1
        while D / 2 + k * step <= D - 3.0:
            a, b = self.at(D / 2 - k * step, 0), self.at(D / 2 + k * step, 0)
            if ok(a) and ok(b): pairs.append([(a, b)])
            k += 1
        if W >= 5.0:
            for dd in (0.0, -step, step):
                if not 3.0 <= D / 2 + dd <= D - 3.0: continue
                cands = [(self.at(D / 2 + dd, -off), self.at(D / 2 + dd, off)) for off in (W * 0.5, W * 0.45, W * 0.55)]
                cands = [(a, b) for a, b in cands if ok(a) and ok(b)]
                if cands: pairs.append(cands)
        return {0: (centre, pairs)}

    def middle_slots(self):
        """Spots down the middle of the room on its long axis (two lines in a wide room): the centre of each line, then
        pairs of spots at even steps either side of it. The groups stand there, lined up and mirrored about the middle,
        not where the bare floor happened to be. {line: (centre or None, [(spot, spot) pairs])}."""
        f = self.f
        u0, u1, v0, v1 = self.box
        long_u = self.axis_long == "u"
        L0, L1 = (u0, u1) if long_u else (v0, v1)
        S0, S1 = (v0, v1) if long_u else (u0, u1)
        w = S1 - S0
        k = 1 if w < 13 else (2 if w < 21 else 3)
        lines = [S0 + w * (i + 1) / (k + 1) for i in range(k)]
        mid = (L0 + L1) / 2
        step = self.s.get("middle", {}).get("step", 5.5)
        m = max(0, int((L1 - L0 - 7.0) / 2 // step))

        def spots(a, c, sign=1):
            """The spot and the nearby ones to try in turn (a passage room's doors keep its very middle clear)."""
            out = []
            for da in (0.0, 0.8, -0.8, 1.6, -1.6, 2.6, -2.6):
                for dc in (0.0, 1.2, -1.2):
                    u, v = (a + sign * da, c + dc) if long_u else (c + dc, a + sign * da)
                    if f.g.inside(u, v) and f.g.wall_dist(u, v) >= 2.2: out.append((u, v))
            return out
        out = {}
        for li, c in enumerate(lines):
            pairs = []
            for k in range(1, m + 1):
                p, q = spots(mid - k * step, c, -1), spots(mid + k * step, c, 1)
                if p and q: pairs.append(list(zip(p, q)))
            out[li] = (spots(mid, c), pairs)
        return out

    def middle_fill(self, part="both"):
        """The type's middle groups on the spots down the room (middle_slots): its centre group on the middle spot, a
        pair of one group on each pair of spots either side of it (the same group, both or neither), so the middle reads
        A B A; a spot with a piece already near it is left as it is."""
        m = self.s.get("middle")
        if not m: return
        centre, pairs, most = list(m.get("centre") or []), list(m.get("pairs") or []), m.get("most") or {}
        count = self.mcount

        def taken(u, v):
            return any(math.hypot(max(0.0, abs(u - r[0]) - r[2]), max(0.0, abs(v - r[1]) - r[3])) < 1.8
                       for t, r in self.f._typed if r[5] != "wall" and r[4])
        slots = (self.axis_slots() if self.s.get("mirror") else None) or self.middle_slots()
        for li, (cs, prs) in sorted(slots.items()):
            if part == "pairs" or self.tiles < m.get("centre_from", 0): cs = []
            if part == "centre": prs = []
            if cs and not taken(*cs[0]):
                done = False
                for name in (centre or pairs):
                    if count[name] >= most.get(name, 99): continue
                    for c in cs:
                        if self.free_group(name, *c):
                            count[name] += 1; self.log["middle " + name] += 1; done = True; break
                    if done: break
            for i, cands in enumerate(prs):
                if self.tiles < m.get("pairs_from", 0): break
                if taken(*cands[0][0]) or taken(*cands[0][1]): continue
                k, done = i % max(1, len(pairs)), False
                for name in pairs[k:] + pairs[:k]:
                    if count[name] + 2 > most.get(name, 99): continue
                    for a, b in cands:
                        g1 = self.free_group(name, *a)
                        g2 = self.free_group(name, *b) if g1 else []
                        if g1 and g2:
                            count[name] += 2; self.log["middle " + name] += 2; done = True; break
                        self.remove((g1 or []) + (g2 or []))
                    if done: break
        # the type's centre group (its focal: the watch's table) where the floor is barest, if the spots had no room
        if part != "pairs" and centre and not count[centre[0]] and self.tiles >= m.get("centre_from", 0):
            for d, u, v, wd in self.reach()[1][:40]:
                if wd < 2.2: continue
                if self.free_group(centre[0], u, v):
                    count[centre[0]] += 1; self.log["middle " + centre[0] + " (bare)"] += 1; break

    def reach(self, radius=1.6):
        """(share of the floor within `radius` of a piece, bare cells as (distance, u, v, wall distance), the heart of the
        bare floor first): kit/density.py's measure at a tighter radius (a piece reaching 2 units had let rooms the user
        found empty pass as full)."""
        f = self.f
        recs = [rec for t, rec in f._typed if rec[5] != "wall" and self.fam(t) != "wall_decor"
                and not self.LIGHT_RX.match(t)]
        near, bare = 0, []
        for x, y in f.g.cells:
            u, v = x + y + 1.0, x - y
            d = min((math.hypot(max(0.0, abs(u - r[0]) - r[2]), max(0.0, abs(v - r[1]) - r[3])) for r in recs),
                    default=99.0)
            if d <= radius: near += 1
            else: bare.append((d, u, v, f.g.wall_dist(u, v)))
        at = {(int(u), int(v)) for _, u, v, _ in bare}
        offs = [(p, q) for p in range(-3, 4) for q in range(-3, 4) if (p + q) % 2 == 0 and math.hypot(p, q) <= 3]
        gain = {(int(u), int(v)): sum(1 for p, q in offs if (int(u) + p, int(v) + q) in at) for _, u, v, _ in bare}
        bare.sort(key=lambda s: (-gain[(int(s[1]), int(s[2]))], -s[0]))
        return near / max(1, len(f.g.cells)), bare

    def bare_fill(self):
        """Where the floor is still bare (the reach under the type's goal): the middle's pair groups at the bare spot,
        mirrored across the axis in a ceremonial room, else the walls topped up past their share."""
        m = self.s.get("middle") or {}
        if not self.s.get("mirror") and not self.s.get("bare"): return   # groups at random bare spots read as scattered
        free = list(m.get("pairs") or []) + list(m.get("centre") or [])
        goal = self.s.get("goal", 0.7)
        failed, k = [], 0
        if self.tiles < m.get("pairs_from", 0): free = []
        for _ in range(12):
            reach, bare = self.reach()
            if reach >= goal or not free: break
            ok = [b for b in bare if all(math.hypot(b[1] - a, b[2] - c) > 2.0 for a, c in failed) and b[3] >= 2.2]
            if not ok: break
            d, u, v, wd = ok[0]
            got = False
            for i in range(len(free)):
                name = free[(k + i) % len(free)]
                if name in ("table_set", "alchemy", "counting", "curio", "winch", "rack", "chart_table", "workbench"):
                    continue                                   # the room's one centre group stays one
                cnt = self.mcount
                if cnt[name] + (2 if self.s.get("mirror") else 1) > ((self.s.get("middle") or {}).get("most") or {}).get(name, 99):
                    continue
                g1 = self.free_group(name, u, v)
                if not g1: continue
                if self.s.get("mirror"):
                    mu, mv = self.mirror(u, v)
                    if math.hypot(mu - u, mv - v) > 2.5:
                        g2 = self.free_group(name, mu, mv)
                        if not g2: self.remove(g1); continue
                got = True; k += i + 1
                break
            if got:
                self.log["bare fill"] += 1
                self.mcount[name] += 2 if self.s.get("mirror") else 1
            else: failed.append((u, v))

    def free_group(self, name, u, v):
        """One of the free-standing groups at (u, v), laid along the room's long axis. Returns the pieces placed ([] if
        it does not fit: nothing is left of it)."""
        f = self.f
        if f.g.wall_dist(u, v) < 1.6 and name != "bones": return []
        along_u = self.axis_long == "u"
        ax = (lambda d: (d, 0.0)) if along_u else (lambda d: (0.0, d))        # a step along the long axis
        n0 = len(f.objects)

        def done(ok):
            new = f.objects[n0:]
            if not ok:
                self.remove(list(new)); return []
            return list(new)

        def table_with(tt, n_seats, pat=None, ends=(), carpet=False):
            tt = self.oks(tt)
            if not tt: return False
            t = self.rng.choice(tt)
            hu, hv = self.half(t)
            if carpet: u_, v_ = 2 * round(u / 2), 2 * round(v / 2)
            else: u_, v_ = u, v
            if not self.put(t, u_, v_): return False
            if f.seats_around((u_, v_), t, n_seats, "chair", pat=pat) < min(2, n_seats): return False
            for i, e in enumerate(ends):          # a piece at each end of the table, along the axis
                e = self.oks([e] if isinstance(e, str) else e)
                if not e: continue
                eh = max(self.half(e[0]))
                d = ((hu if along_u else hv) + eh + 0.9) * (1 if i == 0 else -1)
                du, dv = ax(d)
                self.put(e[0], u_ + du, v_ + dv)
            if carpet:
                cap = (self.F.room_profile(f.kind) or {}).get("caps", {})
                try:
                    f.lay_carpet((u_ - hu - 1.0, u_ + hu + 1.0, v_ - hv - 1.0, v_ + hv + 1.0), margin=0.0)
                except Exception:
                    pass
            return True

        if name == "table_set":
            cap = (self.F.room_profile(f.kind) or {}).get("caps", {}).get("table")
            have = sum(1 for t, _ in f._typed if self.fam(t) == "table")
            if cap and have >= min(cap[1], max(1, int(self.tiles / cap[0]))): return []
            if table_with(["RoundTableWithFood", "RoundTable1"], self.rng.randint(3, 4), carpet=True): return done(True)
            done(False)
            n0 = len(f.objects)
            return done(table_with(["RoundTableWithFood", "RoundTable1"], 2, carpet=False))
        if name == "counting":
            return done(table_with(["SquareTable1", "SquareTable2"], 2, carpet=True))
        if name == "chart_table":
            return done(table_with(["SquareTable1", "SquareTable2"], 2, ends=(["FairyJar"],)))
        if name == "alchemy":
            return done(table_with(["Table1", "Table3"], 2, pat=r"Stool", ends=(["CauldronAnimated"], ["FairyJar"])))
        if name == "workbench":
            return done(table_with(["Table1", "Table2", "Table3", "Table4"], 2, pat=r"Stool",
                                   ends=(["BarrelWithTools1"], ["Crate1", "CrateSteel2"])))
        if name in ("stack", "powder", "sackpile"):
            pal = {"stack": (self.s.get("pal") or {}).get("heap") or STORE,
                   "powder": POWDER + ["CrateSteel1", "BarrelSteel1", "DarkCrate2"],
                   "sackpile": SACKS}[name]
            seq = self.pick_seq(pal, 4)
            if not seq: return []
            hu, hv = self.half(seq[0])
            step = 2 * max(hu, hv) + 0.06
            offs = [(0, 0), (step, 0), (0, step), (step, step)]
            got = 0
            for i, (du, dv) in enumerate(offs[:self.rng.randint(3, 4)]):
                if self.put(seq[i], u + du - step / 2, v + dv - step / 2, touch=True): got += 1
                elif i == 0: break
            return done(got >= 2)
        if name == "piled":
            pt = self.oks(["PiledBarrels1", "PiledBarrels2", "PiledBarrels3", "LargeBarrel1"])
            return done(bool(pt) and bool(self.put(self.rng.choice(pt), u, v)))
        if name == "cart":
            ct = self.oks(["MineManaCart1", "MineManaCart2", "MineOreCart1", "MineOreCart2"])
            if not ct or not self.put(self.rng.choice(ct), u, v): return []
            return done(True)
        if name == "parts":
            p = self.oks(["MineOreCartWheel", "MechGear"])
            return done(len(p) == 2 and bool(self.put(p[0], u, v)) and bool(self.put(p[1], *(u + ax(1.3)[0], v + ax(1.3)[1]), blocking=False)))
        if name == "winch":
            p = self.oks(["PulleyGear3", "PulleyGear1"])
            return done(bool(p) and bool(self.put(p[0], u, v)))
        if name == "rack":
            p = self.oks(["TortureRack6", "TortureRack4"])
            return done(bool(p) and bool(self.put(p[0], u, v)))
        if name == "curio":                         # the orrery (or a telescope) with a pair of lights either side
            p = self.oks(["Orrery2", "Telescope2a", "Telescope2c"])
            if not p or not self.put(p[0], u, v): return []
            lt = next((t for t in ("Candleabra3", "Candleabra1") if self.ok(t)), None)
            if lt:
                du, dv = ax(2.0)
                f.placing_light = True
                try:
                    a = self.put(lt, u + dv, v + du); b = self.put(lt, u - dv, v - du) if a else None
                    if not (a and b): self.remove((a, b))
                    else: f.ring_lights += [(u + dv, v + du), (u - dv, v - du)]
                finally:
                    f.placing_light = False
            return done(True)
        if name == "telescope":
            p = self.oks(["Telescope2e", "Telescope2g", "Telescope1b"])
            return done(bool(p) and bool(self.put(p[0], u, v)))
        if name == "lab_island":                    # two or three workstations side by side: a work bench in the open
            p = self.oks(["WizardWorkstation1", "WizardWorkstation2a", "WizardWorkstation3a"])
            if len(p) < 2: return []
            a, b = self.rng.sample(p, 2)
            ha = self.half(a)[0 if along_u else 1]; hb = self.half(b)[0 if along_u else 1]
            ok = 0
            for t, d in ((a, -(ha + 0.06)), (b, hb + 0.06)):
                du, dv = ax(d)
                if self.put(t, u + du, v + dv, touch=True): ok += 1
            return done(ok == 2)
        if name == "book_stack":                    # a stack of bookcases back to back, two long, down the axis
            a, b = ("Bookcase2", "Bookcase4") if along_u else ("Bookcase1", "Bookcase3")
            if not (self.ok(a) and self.ok(b)): return []
            hu, hv = self.half(a)
            thick, length = (hv, hu) if along_u else (hu, hv)
            ok = 0
            f._pairing = True
            try:
                for k in (-1, 1):
                    du, dv = ax(k * (length + 0.02))
                    pa = (u + du, v + dv - (thick + 0.02)) if along_u else (u + du - (thick + 0.02), v + dv)
                    pb = (u + du, v + dv + (thick + 0.02)) if along_u else (u + du + (thick + 0.02), v + dv)
                    ok += bool(self.put(a, *pa, touch=True)) + bool(self.put(b, *pb, touch=True))
            finally:
                f._pairing = False
            return done(ok == 4)
        if name in ("coffin", "obelisk", "statue", "monument"):  # one piece (the middle's spots come in mirrored pairs)
            pool = self.oks({"coffin": COFFINS, "obelisk": ["Obelisk", "LOTDManaObelisk"],
                             "statue": ["Statue2a", "Statue2c", "Statue2e"], "monument": ["Monument1"]}[name])
            if name == "coffin":
                pool = [t for t in pool if (self.half(t)[0] > self.half(t)[1]) == along_u]
            if not pool: return []
            f._pairing = True
            try:
                return done(bool(self.put(pool[0], u, v)))
            finally:
                f._pairing = False
        if name in ("shrine_square", "dark_square"):
            # the holy thing in the middle of a square of pillars, on a carpet centred under it (the user, of shrines:
            # "Give them a square or rectangular shape defined by obelisks and mana pillars ... that lead to a grand
            # centerpiece"): four pillars at the corners of a rectangle on the axis from the door, wide enough to stand
            # clear of the door's line (no pillar in line with a door: GW-7)
            dark = name == "dark_square"
            pil = self.oks(["LOTDManaObelisk"] if dark else ["Obelisk"])
            mid = self.oks(["LOTDIncenseBasinLit"] if dark else ["DunMirAltar1", "DunMirAltar2"])
            op = f.main_door()
            if not pil or not mid or not op: return []
            m = max(self.half(pil[0]))
            across = max(op["half"] + m + 0.3, 1.9)
            line_u = op["line"] == "/"                 # the axis runs along u from a "/" door wall
            snap = lambda x: 2 * round(x / 2)
            u_, v_ = (u, snap(v)) if not line_u else (u, v)
            u_, v_ = (snap(u_), v_) if not line_u else (u_, v_)
            for Rd in (2.4, 2.0):
                for Ra in (across, across + 0.4):
                    n1 = len(f.objects)
                    f.placing_light = dark
                    try:
                        c = self.put(mid[0], u_, v_)
                    finally:
                        f.placing_light = False
                    ok = bool(c)
                    f._pairing = True
                    try:
                        for sd in (-1, 1):
                            for sa in (-1, 1):
                                if not ok: break
                                du, dv = (sd * Rd, sa * Ra) if line_u else (sa * Ra, sd * Rd)
                                ok = bool(self.put(pil[0], u_ + du, v_ + dv))
                    finally:
                        f._pairing = False
                    if ok:
                        if not dark and not f.carpet_boxes:
                            hu_, hv_ = (Rd, Ra) if line_u else (Ra, Rd)
                            try:
                                f.lay_carpet((u_ - hu_ - 0.9, u_ + hu_ + 0.9, v_ - hv_ - 0.9, v_ + hv_ + 0.9), margin=0.0)
                            except Exception:
                                pass
                        return done(True)
                    self.remove(list(f.objects[n1:]))
            return []
        if name == "tomb":                          # the great tomb, its length along the room's long axis
            tt = self.oks(["Crypt1", "Crypt3", "Crypt5", "Crypt7", "Crypt9", "Crypt11"])
            for t in self.rng.sample(tt, len(tt)):
                hu, hv = self.half(t)
                if (hu > hv) != along_u: continue
                if self.put(t, u, v): return done(True)
            return []
        if name == "generator":
            p = self.oks(["VandegrafLarge", "VandegrafSmall"])
            return done(bool(p) and bool(self.put(p[0], u, v)))
        if name == "armour_pair":
            at = self.oks(ARMOUR)
            if not at: return []
            t = self.rng.choice(at)
            hu, hv = self.half(t)
            du, dv = ax((hu if along_u else hv) + 0.3)
            f._pairing = True
            try:
                a = self.put(t, u - du, v - dv); b = self.put(t, u + du, v + dv) if a else None
            finally:
                f._pairing = False
            return done(bool(a and b))
        if name == "target":
            tt = self.oks(["TargetBarrel1", "TargetBarrel2"])
            if len(tt) < 2: return []
            hu, hv = self.half(tt[0])
            du, dv = ax(max(hu, hv) + 0.25)
            a = self.put(tt[0], u - du, v - dv); b = self.put(tt[1], u + du, v + dv) if a else None
            return done(bool(a and b))
        if name == "bones":
            return done(bool(self.bone_heap(u, v)))
        if name in ("obelisk_pair", "statue_pair", "coffin_pair"):
            pool = {"obelisk_pair": ["LOTDManaObelisk", "Obelisk"], "statue_pair": ["Statue2a", "Statue2c", "Statue2e"],
                    "coffin_pair": COFFINS}[name]
            pool = self.oks(pool)
            if not pool: return []
            t = pool[0] if name == "obelisk_pair" else self.rng.choice(pool)
            mu, mv = self.mirror(u, v) if self.s.get("mirror") else (u + 2 * ax(2.0)[0], v + 2 * ax(2.0)[1])
            if math.hypot(mu - u, mv - v) < 3.0: return []
            f._pairing = True
            try:
                a = self.put(t, u, v); b = self.put(t, mu, mv) if a else None
            finally:
                f._pairing = False
            return done(bool(a and b))
        return []


def op_run(op):
    """A pseudo wall run for the main door's wall (for _uv_on: depth into the room from the door's wall)."""
    return dict(line=op["line"], coord=op["coord"], sign=op["sign"])


def brick_square(f, u, v, size=1):
    """A bordered square of brick floor under a piece at (u, v): the floor square under it and those round it, as far as
    the room's floor goes (3 x 3 squares, or 3 x 2 against a wall), blended into the room's floor with an edge all round,
    as Westwood lays a hearthstone (kit/shells.py lay_zones' material and blending). Returns the tiles laid. A generic
    piece the hearths of other room types may share (the user, nox17: "place furnaces on a small brick square")."""
    from kit import shells as SH
    room, spec = f.room, f.spec
    main = room.floor
    if not main or not hasattr(spec, "floor") or not hasattr(spec, "tile"): return {}
    rng = random.Random(zlib.crc32(f"brick:{room.id}".encode()))
    mat = SH.zone_material(rng, "hearth", main)
    if not mat: return {}
    sq = {((x + y) // 2, (x - y) // 2) for (x, y) in room.tiles}
    tile = lambda s: (s[0] + s[1], s[0] - s[1])
    s0 = min(sq, key=lambda s: ((2 * s[0] + 2 - u) ** 2 + (2 * s[1] - v) ** 2, s))
    want = {(s0[0] + a, s0[1] + b) for a in range(-size, size + 1) for b in range(-size, size + 1)} & sq
    gaps = [d.gap for d in (getattr(room, "doors", None) or ())]
    out = {}
    for s in sorted(want):
        t = tile(s)
        if spec.floor.get(t, main) != main or t in (getattr(spec, "local_blend", {}) or {}): continue
        if any(max(abs(t[0] - g[0]), abs(t[1] - g[1])) <= 2 for g in gaps): continue
        out[t] = mat
    if len(out) < 2: return {}
    for t, m in out.items(): spec.tile(*t, m)
    SH.blend_pattern(spec, {t: spec.floor.get(t, main) for t in room.tiles}, gaps)
    return out
