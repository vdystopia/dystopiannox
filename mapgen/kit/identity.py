"""Identity (generator v3): every area, building, room and prop group has a purpose, and the
generators place only what serves it.

The playtest of DysVale v0.3 showed what statistics alone produce: a back room with four table sets,
barrels with no reason to be where they are. Westwood's places read as genuine because each was
designed as something: the inn's kitchen, the innkeeper's bedroom, the woodcutter's woodpile.

A map starts from a MapIdentity (written by the designer, or by Claude from a brief): the theme, the
environment type, and for each area, building and room its purpose. The tables below turn purposes
into contents:
- ROOMS: for each room kind, what it is for, what it must contain (core), what it may contain
  (optional), and the object types allowed for a family (a bedroom's storage is a chest, never a
  barrel). Everything else is excluded.
- BUILDINGS: building roles (inn, general store, smithy, home, mill, woodcutter's hut): room
  program, wall style and the outdoor scenes that show the trade.
- SCENES: outdoor prop groups, each with the reason it exists and where it goes.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---- rooms --------------------------------------------------------------------------------------------
# core: family -> (min, max) pieces; optional: family -> (probability, max); types: family -> regex of
# allowed object types; prefer: family -> {type: weight} chosen first. Families are rules/room_types.py's
# (seats are placed with their tables).
#
# compose: the room's composition, in order (kit/furnish.py Furnisher.compose). Each step places the
# planned pieces of one family:
#   slot "wall"   against a wall: the back walls the camera sees first, away from the pieces already
#                 placed (one anchor per wall where the room allows); at "center" of the free stretch,
#                 "corner" toward its end, or "any"; `clear` uv units kept free in front (nothing may
#                 stand there); rug=True lays the room's rug before it; group=True makes a row of
#                 supplies from a corner; seats=True gives a desk its chair
#   slot "center" in the open middle of the room (tables, with their chairs if seats=True; food=True
#                 sets food out on a kitchen table)
#   slot "decor"  hangings centred on free stretches of the back walls
#   fam "rug"     a rug no anchor called for lies in the middle of the room
# repeat: family -> (floor tiles per piece, most pieces), set by the room's type (kit/roomtypes.py caps): a large room's repeated set (pews, tables, benches) stops
# there, whatever the plan, the fill steps or the top-up ask, and the room fills with a mix of other pieces instead
# (2026-10-05 playtest: "way too many benches and not enough object diversity ... too many of the same object
# (chapel benches, tavern tables and chairs)"). Westwood's big rooms: its taverns hold 4-8 tables (one per 27-42
# tiles, Con07B 8 in 216, Con06a 4 in 166); its halls and temples with benches 6-8 (2-6.5 per 100 tiles: Wiz07F 8
# in 123, Wiz07D 8 in 304, Con07C 8 in 383) among columns, statues, tapestries and plants; no room past 16 benches.
# Westwood: fireplaces stand centred on a back wall and nothing ever blocks them; beds, chests and
# shelves stand mostly on the back walls; stoves toward a corner; rugs lie near the middle; 88% of
# chairs stand at a table.
CHEST = r"^Chest\d|^Chest[NS][EW]$|^DunMirChest\d"
PLANTS = r"^(Plant1|Plant3|Plant4|Plant5)$"
RACKS = r"^Trader(ArmorRack|PoleArm|ClothesRack|BowRack|QuiverRack|Shelves|HelmShelf)\d*$"
SUPPLY = r"Crate|(?<!Powder)Barrel$|(?<!Powder)Barrel\d|PiledBarrels|LargeBarrel|Sack|BarrelWithTools"
ROOMS = {
    "bedroom": dict(purpose="where someone sleeps: the bed with its nightstand, a chest snug against a back wall with a "
                            "rug before it, a run of shelves end to end, a desk or a small table toward the front, a "
                            "carpet sometimes, hangings on the back walls, plants",
                    core={"bed": (1, 1), "storage": (1, 1)},
                    optional={"rug": (1.0, 2), "nightstand": (1.0, 1), "shelves": (0.9, 3), "wall_decor": (1.0, 5),
                              "desk": (0.5, 1), "bench": (0.6, 1), "plant": (0.7, 2), "table": (0.6, 1), "chair": (0.6, 2)},
                    types={"storage": CHEST, "shelves": r"^Bookcase\d(HalfFull)?$|^PotionShelves\d$", "plant": PLANTS,
                           "table": r"^RoundTable[12]$|^SquareTable[12]$"},
                    # three tables at most, however big the chamber (kit/roomtypes.py caps: Thornwick's 105-tile lord's chamber
                    # took five round tables with their chairs and read as a dining room: rules/rooms/bedroom.md)
                    compose=[dict(fam="bed", slot="wall", at="any", clear=1.0),
                             dict(fam="storage", slot="wall", at="center", clear=2.3, rug=True),
                             dict(fam="shelves", slot="line", n=3),
                             dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                             dict(fam="carpet", slot="carpet", where="whole", chance=0.4),
                             dict(fam="wall_decor", slot="decor")],
                    fill=[dict(fam="shelves", slot="line", other=True, decor=2, max=8, min_area=100), dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1, min_area=70), dict(fam="table", slot="group", group="sitting", max=1, min_area=90), dict(fam="desk", slot="wall", at="center", clear=0, seats=True, once=True),
                          dict(fam="table", slot="center", seats=True, once=True, rug=True),
                          dict(fam="shelves", slot="line", n=3, max=3),
                          dict(fam="bench", slot="wall", at="center", clear=0, once=True),
                          dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2)]),
    "dwelling": dict(purpose="a one-room home: the hearth on a back wall with shelves beside it, the bed against a wall, "
                             "a table to eat at toward the front, a chest for belongings, a pot on the fire",
                     base="living_room",
                     core={"bed": (1, 1), "table": (1, 1), "chair": (1, 2), "storage": (1, 2), "fireplace": (1, 1)},
                     optional={"rug": (0.8, 2), "shelves": (0.9, 6), "wall_decor": (0.8, 4), "stove": (0.6, 1),
                               "bench": (0.6, 1), "plant": (0.6, 2)},
                     types={"storage": CHEST + r"|^SackChest|(?<!Powder)Barrel$", "stove": r"^Cauldron", "plant": PLANTS},
                     prefer={"fireplace": {"Fireplace4": 1, "Fireplace3": 1}},
                     compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4),
                              dict(fam="bed", slot="wall", at="any", clear=1.0),
                              dict(fam="shelves", slot="line", near="fireplace", n=4),
                              dict(fam="storage", slot="wall", at="center", clear=1.4),
                              dict(fam="table", slot="center", seats=True),
                              dict(fam="carpet", slot="carpet", where="under", chance=0.4),
                              dict(fam="wall_decor", slot="decor")],
                     fill=[dict(fam="stove", slot="wall", at="corner", clear=1.4, max=1, min_area=100),
                           dict(fam="table", slot="group", group="sitting", max=1, min_area=150),
                           dict(fam="shelves", slot="line", other=True, decor=2, max=6, min_area=140),
                           dict(fam="bench", slot="wall", max=1),
                           dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                           dict(fam="storage", slot="stock", coverage=0.3, kinds=("sacks", "barrels"), pad=1.2, max=3)]),
    "living_room": dict(purpose="the household's hearth room: the hearth on a back wall flanked by shelves end to end, "
                                "a rug before it or a carpet under the table, a table with its chairs toward the front, a "
                                "chest, benches, trophies and hangings on the back walls, plants",
                        core={"fireplace": (1, 1), "table": (1, 1), "chair": (2, 4), "shelves": (2, 8)},
                        optional={"statue": (0.5, 2), "rug": (1.0, 2), "storage": (0.8, 1), "wall_decor": (1.0, 6), "bench": (0.8, 2),
                                  "plant": (0.8, 2)},
                        types={"statue": r"^Statue2[a-h]$", "storage": CHEST, "shelves": r"^Bookcase\d(HalfFull)?$|^LogShelvesFull\d$", "plant": PLANTS},
                        prefer={"fireplace": {"Fireplace4": 1, "Fireplace3": 1}},
                        compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4, rug=True),
                                 dict(fam="shelves", slot="line", near="fireplace", decor=2), dict(fam="shelves", slot="line", other=True, decor=2),
                                 dict(fam="storage", slot="wall", at="center", clear=2.3, rug=True),
                                 dict(fam="table", slot="center", seats=True),
                                 dict(fam="carpet", slot="carpet", where="under", chance=0.6),
                                 dict(fam="bench", slot="wall", at="center", clear=0),
                                 dict(fam="wall_decor", slot="decor")],
                        fill=[dict(fam="table", slot="group", group="dining", max=1, min_area=200), dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1, min_area=70), dict(fam="shelves", slot="line", other=True, decor=2, max=10, min_area=80), dict(fam="table", slot="group", group="sitting", max=1, min_area=60), dict(fam="statue", slot="group", group="statues", max=1, min_area=240), dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                              dict(fam="bench", slot="wall", at="center", clear=0, max=1),
                              dict(fam="shelves", slot="line", n=3, max=3)]),
    "kitchen": dict(purpose="where food is cooked and kept: the hearth on a back wall with the cooking cauldron a step "
                            "away, the other back wall lined with shelves of provisions, a work table with stools toward "
                            "the front, heaps and rows of sacks, barrels, crates and apples along the front walls",
                    core={"fireplace": (1, 1), "stove": (1, 1), "table": (1, 1), "storage": (4, 24), "shelves": (2, 10)},
                    optional={"chair": (1.0, 3)},
                    types={"storage": SUPPLY + "|TraderAppleCrate$", "table": r"RoundTableWithFood|^Table4$",
                           "shelves": r"^LogShelvesFull\d$", "chair": r"^Stool\d$"},
                    prefer={"fireplace": {"WallFireplace3": 1, "WallFireplace4": 1},
                            "stove": {"CauldronAnimated": 3, "Stove05": 1},
                            "table": {"RoundTableWithFood": 5, "Table4": 1},
                            "storage": {"Barrel": 3, "Barrel2": 2, "TraderAppleCrate": 2, "SackChestLarge1": 1, "Crate1": 1}},
                    compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4),
                             dict(fam="stove", slot="wall", at="corner", clear=1.4, beside="fireplace", gap=2.0),
                             dict(fam="shelves", slot="line"),
                             dict(fam="table", slot="center", seats=True),
                             dict(fam="storage", slot="stock", coverage=0.7, kinds=("sacks", "barrels", "apples", "crates"),
                                  pad=1.3)],
                    fill=[dict(fam="table", slot="group", group="feast", max=1, min_area=120), dict(fam="table", slot="group", group="worktable", max=2, min_area=80), dict(fam="storage", slot="stock", coverage=1.0, kinds=("barrels", "sacks", "apples", "crates"),
                               pad=1.0, max=10),
                          dict(fam="storage", slot="stack", n=3, once=True),
                          dict(fam="shelves", slot="line", other=True, max=8)]),
    "herbalist": dict(purpose="an herb-lore room: a pair of potion shelves on a back wall, books of remedies lining a back "
                              "wall end to end, a bubbling cauldron, a work table toward the front, sacks of herbs, herbs "
                              "growing in pots",
                      base="study",
                      core={"shelves": (3, 10), "stove": (1, 1), "table": (1, 1), "chair": (1, 2)},
                      optional={"lab": (0.8, 2), "storage": (1.0, 6), "plant": (1.0, 3), "wall_decor": (0.8, 3)},
                      types={"lab": r"^AlchemistDesk\d$|^WizardWorkstation\d[a-d]?$", "shelves": r"^PotionShelves\d$|^Bookcase\d(HalfFull)?$", "stove": r"^Cauldron",
                             "storage": r"^Chest\d|^SackChest|(?<!Powder)Barrel$|(?<!Powder)Barrel\d", "plant": PLANTS},
                      prefer={"shelves": {"PotionShelves1": 1, "PotionShelves2": 1, "PotionShelves3": 1, "PotionShelves4": 1,
                                          "Bookcase1": 1, "Bookcase2": 1, "Bookcase3": 1, "Bookcase4": 1},
                              "stove": {"CauldronAnimated": 1}, "table": {"Table4": 1, "SquareTable1": 1}},
                      # potion shelves stand in a pair, never a wall of them (2026-10-05 Starwell playtest; kit/furnish.py
                      # PAIRED_PIECES): the pair first, then the books line a wall
                      compose=[dict(fam="shelves", slot="line", n=2, only=r"^PotionShelves"),
                               dict(fam="shelves", slot="line"),
                               dict(fam="stove", slot="wall", at="corner", clear=1.6),
                               dict(fam="table", slot="center", seats=True),
                               dict(fam="carpet", slot="carpet", where="under", chance=0.5),
                               dict(fam="storage", slot="stock", coverage=0.3, kinds=("sacks", "barrels"), pad=1.2)],
                      fill=[dict(fam="lab", slot="wall", at="center", clear=1.2, max=1), dict(fam="table", slot="group", group="worktable", max=1, min_area=120), dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                            dict(fam="storage", slot="stock", coverage=0.5, kinds=("sacks",), pad=1.2, max=4)]),
    "ore_store": dict(purpose="mana ore and the miners' gear: loaded carts with room to move them, racks of gear in rows "
                              "down the middle, trader shelves of tools and helmets along a back wall, crates and barrels of "
                              "tools along the front walls",
                      base="storeroom",
                      core={"cart": (2, 3), "storage": (2, 16), "shop_rack": (2, 12)},
                      optional={},
                      types={"storage": SUPPLY, "shop_rack": RACKS},
                      prefer={"cart": {"MineManaCart1": 2, "MineManaCart2": 2, "MineOreCart1": 1, "MineOreCart2": 1},
                              "storage": {"DarkCrate1": 2, "DarkCrate2": 2, "BarrelWithTools1": 1, "Barrel": 1},
                              "shop_rack": {"TraderShelves1": 1, "TraderShelves2": 1}},
                      compose=[dict(fam="shop_rack", slot="line"), dict(fam="shop_rack", slot="line", other=True),
                               dict(fam="cart", slot="wall", at="any", clear=1.2),
                               dict(fam="shop_rack", slot="racks", kind="mine"),
                               dict(fam="storage", slot="stock", coverage=0.7, kinds=("crates", "tools", "barrels"), pad=1.2)],
                      fill=[dict(fam="shop_rack", slot="line", other=True, max=8, min_area=80), dict(fam="shop_rack", slot="line", max=6), dict(fam="cart", slot="group", group="carts", max=2), dict(fam="storage", slot="stock", coverage=1.0, kinds=("crates", "barrels", "sacks", "tools"), pad=1.0),
                            dict(fam="storage", slot="stack", n=3, once=True)]),
    "tavern": dict(purpose="the public drinking room: a long bar ringed by stools with kegs behind it, round tables with "
                           "stools, long tables with benches, a table laid with food, the hearth with a rug before it, "
                           "a cask by the bar, trophies on the walls, benches along the front walls, open floor between",
                   # 2026-10-05 playtest: 24 tables and 76 chairs in a 342-tile common room were too many; Westwood's
                   # taverns hold a table per 27-42 tiles, so a table per 28 tiles, at most 12. Room lab (tuneB): its five
                   # campaign taverns (Con02a, Con06a, Con07B's two, Wiz05A) keep 5-8 kegs and casks, by the bar; one or
                   # two kinds of set, each of one table and one seat (Con06a: four RoundTable2 with cushioned stools;
                   # Con07B: tables of food with chairs and long tables with benches); a bar of 9-14 pieces ringed by
                   # stools; a bearskin before the hearth or a woven carpet under the tables, never rugs under them; no
                   # plants, no shelves of tankards but a pair at most
                   core={"counter_bar": (1, 1), "table": (3, 12), "chair": (6, 34), "storage": (2, 5), "fireplace": (1, 1)},
                   per_tiles={"table": 28},
                   optional={"bench": (0.9, 4), "wall_decor": (1.0, 5), "rug": (0.7, 1)},
                   types={"storage": r"(?<!Powder)Barrel$|(?<!Powder)Barrel\d|PiledBarrels|LargeBarrel",
                          "table": r"RoundTable|^Table\d$|SquareTable", "chair": r"Stool|Chair",
                          "bench": r"^LightBench\d$|^CushionedBench\d$|^Bench\d$",
                          # shelves of tankards and crockery, never a bookcase (rules/rooms/tavern.md)
                          "shelves": r"^LogShelvesFull\d$", "rug": r"^BearskinRug\d$"},
                   # Westwood's room statistics count hearths as lights: the tavern names its own (it had stood without)
                   prefer={"fireplace": {"Fireplace1": 1, "Fireplace2": 1, "Fireplace3": 2, "Fireplace4": 1}},
                   one_set=("round", "longtable", "feast", "dining", "kegs"), group_rugs=False,
                   # seats pulled out from the tables, as Westwood's patrons leave them (its taverns' median gap to the
                   # nearest piece 0.7 units; ours had stood 0.2 off every table)
                   seat_gaps={"round": 0.5, "feast": 0.45, "longtable": 0.3},
                   group_seats={"round": (2, 3)},
                   by_walls=("longtable", "feast"),     # along the walls and in the corners, the middle left open
                   compose=[dict(fam="counter_bar", slot="bar"),
                            dict(fam="fireplace", slot="wall", at="center", clear=2.4, rug=True),
                            dict(fam="fireplace", slot="groups", group="hearth", n=1, min_area=500, extra=True),
                            dict(fam="table", slot="groups", group="round", n=2),
                            dict(fam="table", slot="groups", group="longtable", n=2),
                            dict(fam="table", slot="groups", group="feast", n=1),
                            dict(fam="table", slot="groups", group="round", n=1, min_area=440),
                            dict(fam="carpet", slot="carpet", where="under", margin=1.2, chance=0.45),
                            dict(fam="wall_decor", slot="decor")],
                   fill=[dict(fam="fireplace", slot="group", group="hearth", max=1, min_area=680, fixed=True),
                         dict(fam="table", slot="group", group="longtable", max=1, min_area=220),
                         dict(fam="table", slot="group", group="round", max=1, min_area=300),
                         dict(fam="table", slot="group", group="feast", max=1, min_area=200),
                         dict(fam="bench", slot="wall", max=4),
                         # a few barrels heaped on a front wall, never lining it (Con02a's by its door)
                         dict(fam="storage", slot="stock", coverage=0.3, kinds=("kegs",), pad=1.2, max=3, per_wall=0.25)]),
    "mess_hall": dict(purpose="where a crew eats together: long tables in rows with a bench along each side, the hearth "
                              "on a back wall flanked end to end by shelves of crockery, benches along the front walls, "
                              "trophies and hangings on the back walls",
                      base="dining_hall",
                      core={"fireplace": (1, 1), "table": (2, 8), "bench": (4, 20), "shelves": (2, 12)},
                      per_tiles={"table": 22},
                      # Westwood's mess (Con06b): 12 tables in 208 tiles
                      optional={"wall_decor": (1.0, 6)},
                      types={"table": r"^Table[1-4]$", "bench": r"^Bench\d$|^LightBench\d$|^CushionedBench\d$",
                             "chair": r"Stool|Chair", "shelves": r"^LogShelvesFull\d$"},
                      prefer={"fireplace": {"Fireplace1": 1, "Fireplace2": 1, "Fireplace3": 2, "Fireplace4": 1}},
                      compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4),
                               dict(fam="shelves", slot="line", near="fireplace"),
                               dict(fam="table", slot="table_rows", seat="bench"),
                               dict(fam="wall_decor", slot="decor")],
                      # a mess too small for rows still eats at one long table (Greywatch's 32-tile mess had none:
                      # rules/rooms/dining_hall.md)
                      top_up=(),
                      fill=[dict(fam="table", slot="group", group="longtable", max=1, fixed=True),
                            dict(fam="bench", slot="wall", at="room_corner", clear=0, max=1),
                            dict(fam="shelves", slot="line", max=4)]),
    "dining_hall": dict(purpose="a household's dining hall: two or three long tables seated along both sides by benches "
                                "and chairs, the hearth on a back wall, a cask or two, hangings above",
                        # room lab (tuneB): Westwood's dining halls (Con06a 55 tiles, Con03B's mess 108, the ogres'
                        # Con05C 110) hold two or three tables, never a grid of eight; benches with a chair or two at
                        # the ends; a bookcase at most; casks and barrels by the walls; no plants, no statues
                        core={"table": (1, 4), "chair": (2, 12), "fireplace": (1, 1)},
                        per_tiles={"table": 26},
                        optional={"rug": (0.4, 1), "wall_decor": (1.0, 5), "shelves": (0.4, 2), "bench": (1.0, 6),
                                  "storage": (0.5, 2)},
                        types={"table": r"^Table[1-4]$|^OvalTable[12]$|^RoundTableWithFood$|^RoundTable[123]$",
                               "shelves": r"^LogShelvesFull\d$",      # crockery, not books (dining halls read as libraries)
                               "storage": CHEST + r"|^LargeBarrel[12]$|^Barrel2?$|^PiledBarrels[1-4]$",
                               "chair": r"Chair", "bench": r"^LightBench\d$|^Bench[1245]$"},
                        # Westwood's room statistics count hearths as lights, so a recipe names its own
                        prefer={"fireplace": {"Fireplace1": 1, "Fireplace2": 1, "Fireplace3": 2, "Fireplace4": 1}},
                        one_set=("dining", "feast"), group_rugs=False, statues_along=True, decor_max=5,
                        top_up=(),                           # never benches or barrels down the walls to fill the floor
                        compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4),
                                 dict(fam="table", slot="table_rows", seat="bench"),
                                 dict(fam="carpet", slot="carpet", where="under", chance=0.5),
                                 dict(fam="wall_decor", slot="decor")],
                        fill=[dict(fam="table", slot="group", group="feast", max=1, min_area=160),
                              dict(fam="table", slot="group", group="dining", max=2, min_area=160),
                              dict(fam="storage", slot="stock", coverage=0.2, kinds=("kegs",), pad=1.2, max=1,
                                   per_wall=0.2, fixed=True),
                              dict(fam="shelves", slot="line", near="fireplace", n=2, max=1, fixed=True)]),
    "shop": dict(purpose="a trader's shop: the counter set out before a back wall with the keeper's space behind it, "
                         "trader's shelves of goods lining the back walls, racks of arms and armour in rows down the "
                         "middle, crates of stock along the front walls",
                 core={"counter_shop": (1, 1), "shop_rack": (2, 24)},
                 optional={"storage": (0.9, 8), "shelves": (0.6, 8), "plant": (0.5, 2), "chair": (0.5, 1)},
                 types={"storage": r"Crate|(?<!Powder)Barrel$|(?<!Powder)Barrel\d|Sack|Chest\d", "shop_rack": RACKS,
                        "shelves": r"^PotionShelves\d$", "plant": PLANTS},
                 prefer={"counter_shop": {f"TraderDesk{k}": 1 for k in range(1, 7)}},
                 compose=[dict(fam="counter_shop", slot="counter", depth=2.2, clear=1.8),
                          dict(fam="shop_rack", slot="line"),
                          dict(fam="shop_rack", slot="line", other=True),
                          dict(fam="shop_rack", slot="racks", kind="gear"),
                          dict(fam="storage", slot="stock", coverage=0.5, kinds=("crates", "barrels"), pad=1.2)],
                 fill=[dict(fam="shelves", slot="line", other=True, max=6),
                       dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                       dict(fam="storage", slot="stock", coverage=0.8, kinds=("crates", "sacks"), pad=1.0, max=4)]),
    "storeroom": dict(purpose="stores kept in good order: a back wall lined with shelves of provisions, heaps of barrels "
                              "and sacks in the corners, crates side by side along the walls, racks of hunting gear in rows "
                              "down the middle with aisles to walk",
                      core={"storage": (4, 24), "shelves": (2, 10)},
                      optional={"shop_rack": (1.0, 12)},
                      types={"storage": SUPPLY, "shelves": r"^LogShelvesFull\d$", "shop_rack": RACKS},
                      compose=[dict(fam="shelves", slot="line"),
                               dict(fam="shop_rack", slot="racks", kind="hunt"),
                               dict(fam="storage", slot="stock", coverage=0.8, kinds=("crates", "barrels", "sacks"))],
                      fill=[dict(fam="storage", slot="stack", n=3, once=True),
                            dict(fam="storage", slot="stock", coverage=1.0, kinds=("barrels", "sacks", "crates"), pad=0.3)]),
    # a mill's or a farm's grain store (Harrowby): a storeroom of sacks, never racks of arms (the mill's first
    # storeroom held a row of axe racks down its middle: rules/rooms/storeroom.md)
    "granary": dict(base="storeroom", purpose="grain kept dry: sacks heaped in the corners and stacked down the middle, shelves of "
                            "provisions on a back wall, barrels and crates along the walls, an aisle to walk",
                    core={"storage": (5, 28), "shelves": (1, 8)}, optional={},
                    types={"storage": SUPPLY, "shelves": r"^LogShelvesFull\d$"},
                    compose=[dict(fam="shelves", slot="line"),
                             dict(fam="storage", slot="stack", n=3, once=True),
                             dict(fam="storage", slot="stock", coverage=0.9, kinds=("sacks", "barrels", "crates"))],
                    fill=[dict(fam="storage", slot="wall", at="corner", clear=0.4, group=True, max=8),
                          dict(fam="storage", slot="stock", coverage=1.0, kinds=("sacks", "crates", "barrels"), pad=0.3)]),
    "gear_store": dict(purpose="a crew's gear in good order: armour stands and racks of pole arms, clothes and bows in "
                               "rows down the middle, a back wall lined with shelves, barrels, crates and tool barrels "
                               "along the front walls",
                       base="storeroom",
                       core={"storage": (4, 24), "shop_rack": (3, 16), "shelves": (2, 10)},
                       optional={},
                       types={"storage": SUPPLY, "shelves": r"^LogShelvesFull\d$", "shop_rack": RACKS},
                       compose=[dict(fam="shelves", slot="line"),
                                dict(fam="shop_rack", slot="racks", kind="gear"),
                                # the stock by the front walls, the racks the show (rules/rooms/armoury.md: Greywatch's 28-tile
                                # armoury stocked to 0.33 covered, 0.16 of its floor open)
                                dict(fam="storage", slot="stock", coverage=0.5, kinds=("crates", "barrels", "tools", "sacks"))],
                       fill=[dict(fam="storage", slot="stack", n=3, once=True),
                             dict(fam="storage", slot="stock", coverage=0.7, kinds=("barrels", "crates", "tools"), pad=0.6)]),
    # 2026-10-05, Starwell playtest: "The shopkeeper is standing in the middle of the shop, surrounded by a random scattering
    # of objects ... He needs to be standing somewhere that makes sense, like behind a desk. Instead of six armor racks,
    # use three armor racks and three weapon racks": the smith sells over a counter (the keeper's spot behind it,
    # StoryMap.shops), the racks stand three to a row, a row of armour and a row of weapons (kit/furnish.py rack_rows)
    "smithy": dict(purpose="the forge and the smith's counter: glowing coals with the bellows beside them, the anvil before "
                           "the fire, water to quench the iron, barrels of tools and crates of iron, the counter set out "
                           "from a back wall with the smith behind it, swords and pole arms on the walls, a row of armour "
                           "stands and a row of weapon racks",
                   core={"forge": (1, 1), "bellows": (1, 1), "anvil": (1, 1), "storage": (2, 12), "counter_shop": (1, 1)},
                   optional={"shop_rack": (1.0, 12), "table": (0.6, 1), "chair": (0.6, 2)},
                   types={"storage": r"WaterBarrel|BarrelWithTools\d$|DarkCrate\d|^Crate[12]$|(?<!Powder)Barrel\d?$",
                          "shop_rack": r"^TraderPoleArm\d|^TraderHangingSwords\d|^TraderArmorRack[12]$",
                          "table": r"^Table[1-4]$", "counter_shop": r"^TraderDesk\d$"},
                   prefer={"forge": {"CinderBin2": 1, "CinderBin1": 1},
                           "counter_shop": {f"TraderDesk{k}": 1 for k in range(1, 7)},
                           "bellows": {f"Bellows{k}": 1 for k in range(1, 9)},
                           "anvil": {f"Anvil{k}": 1 for k in range(1, 9)},
                           "storage": {"WaterBarrel": 2, "BarrelWithTools1": 1, "BarrelWithTools2": 1, "DarkCrate1": 1,
                                       "DarkCrate2": 1, "Barrel2": 1},
                           "shop_rack": {"TraderPoleArm1": 1, "TraderPoleArm2": 1, "TraderPoleArm3": 1, "TraderPoleArm4": 1}},
                   compose=[dict(fam="forge", slot="wall", at="center", clear=2.4),
                            dict(fam="bellows", slot="wall", at="corner", beside="forge", clear=0),
                            dict(fam="anvil", slot="before", of="forge", gap=2.4),
                            dict(fam="counter_shop", slot="counter", depth=2.2, clear=1.8),
                            dict(fam="shop_rack", slot="line", other=True),
                            dict(fam="storage", slot="stock", coverage=0.5, kinds=("barrels", "crates", "tools"), pad=1.2)],
                   fill=[dict(fam="shop_rack", slot="line", other=True, max=8), dict(fam="shop_rack", slot="line", max=6), dict(fam="shop_rack", slot="racks", kind="gear", max=6, min_area=150),
                         dict(fam="table", slot="group", group="worktable", max=1, min_area=120),
                         dict(fam="storage", slot="stock", coverage=0.8, kinds=("barrels", "crates", "tools"), pad=1.0, max=6),
                         dict(fam="storage", slot="stack", n=3, once=True)]),
    "study": dict(purpose="the desk centred on a back wall with books lining that wall end to end on both sides and "
                          "hangings between them, a chest on the other back wall, a meeting table with chairs toward the "
                          "front on a carpet, plants",
                  core={"desk": (1, 1), "shelves": (2, 14), "storage": (1, 2), "table": (1, 1)},
                  optional={"statue": (0.4, 2), "lab": (0.8, 3), "rug": (0.8, 1), "wall_decor": (1.0, 6), "plant": (0.8, 2), "table": (0.8, 1), "chair": (0.8, 3)},
                  types={"statue": r"^Statue2[a-h]$", "lab": r"^AlchemistDesk\d$|^WizardWorkstation\d[a-d]?$|^Telescope2[a-g]$|^Orrery2$", "storage": r"^Chest\d", "shelves": r"^Bookcase\d(HalfFull)?$", "plant": PLANTS,
                         "table": r"^RoundTable[12]$|^SquareTable[12]$"},
                  compose=[dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                           dict(fam="shelves", slot="line", near="desk", decor=2), dict(fam="shelves", slot="line", other=True, decor=2),
                           dict(fam="storage", slot="wall", at="center", clear=2.3),
                           dict(fam="table", slot="center", seats=True),
                           dict(fam="carpet", slot="carpet", where="under", chance=0.7),
                           dict(fam="wall_decor", slot="decor")],
                  # (no dining set: a second table group turns a study toward a dining room, rules/rooms/study.md;
                  # Harrowby's 143-tile reeve's study had three)
                  fill=[dict(fam="shelves", slot="line", other=True, decor=2, max=12), dict(fam="lab", slot="wall", at="center", clear=1.2, max=1), dict(fam="shelves", slot="racks", kind="books", max=8, min_area=120), dict(fam="lab", slot="group", group="curio", max=1, min_area=90), dict(fam="table", slot="group", group="sitting", max=1, min_area=120), dict(fam="shelves", slot="line", n=4, max=4),
                        dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                        dict(fam="storage", slot="wall", at="center", clear=1.6, max=1)]),
    "library": dict(purpose="books: bookcases lining both back walls end to end, stacks of bookcases in rows down the "
                            "middle of a big library, a reading table on a carpet, a desk, a curio",
                    core={"shelves": (4, 40), "table": (1, 2)},
                    optional={"desk": (0.7, 1), "chair": (0.8, 6), "rug": (0.6, 1),
                              "fireplace": (0.25, 1), "lab": (0.5, 1), "plant": (0.5, 2), "statue": (0.3, 2),
                              "wall_decor": (0.8, 4)},
                    types={"shelves": r"^Bookcase\d(HalfFull)?$", "lab": r"^Telescope2[a-g]$|^Orrery2$",
                           "statue": r"^Statue2[a-h]$", "plant": PLANTS},
                    compose=[dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                             dict(fam="shelves", slot="line", near="desk"),
                             dict(fam="shelves", slot="line", other=True),
                             dict(fam="table", slot="center", seats=True),
                             dict(fam="carpet", slot="carpet", where="under", chance=0.6),
                             dict(fam="plant", slot="wall", at="room_corner", clear=0),
                             dict(fam="wall_decor", slot="decor")],
                    fill=[dict(fam="shelves", slot="racks", kind="books", max=16, min_area=80),
                          dict(fam="shelves", slot="line", other=True, max=8),
                          dict(fam="lab", slot="group", group="curio", max=1, min_area=120),
                          dict(fam="table", slot="group", group="sitting", max=1, min_area=200),
                          dict(fam="shelves", slot="line", max=6),
                          dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2)]),
    # 2026-10-05, Starwell playtest: the college laboratory "almost looks like some sort of shoddy mess hall with random
    # objects stuffed in it. This room has no sense of identity or purpose" (eight tesla coils end to end down its long
    # wall, five dining and reading tables with their chairs scattered down the middle). Westwood's laboratories (Wiz07D:
    # bookcases with a desk among them, a work island of workstations in the middle, a table, the tesla coils apart; 104
    # rooms: 1-9 lab pieces, median 3, a table in a quarter of them) and the playtester's reference room, the
    # archmagister's study (PROCESS.md, "What a good room is"): each wall has a purpose, one group in the middle shows
    # the room's use, pieces of one theme. A long room is used in zones along its length: the study end, the work wall,
    # the work table, the conjuring circle.
    "laboratory": dict(purpose="a wizard's laboratory, used in zones along its length: the study end, the desk near a "
                               "corner of a back wall with bookcases either side; the work wall, a bench of wizards' "
                               "workstations of three kinds with a hanging between, one alchemist's desk and a pair of "
                               "potion shelves; in the middle the alchemist's work table with its stools, glowing jars and a "
                               "bubbling cauldron beside it, and a conjuring circle of candelabras round a crystal globe or an orrery; a "
                               "pair of generators apart; a chest for the reagents; statues by the front walls, as the "
                               "archmagister's study has them; tapestries on the back walls. Never "
                               "a dining table",
                       core={"lab": (3, 10), "shelves": (2, 20), "desk": (1, 1)},
                       optional={"table": (1.0, 1), "chair": (1.0, 3), "plant": (0.5, 2), "rug": (0.4, 1),
                                 "wall_decor": (1.0, 5), "storage": (1.0, 1), "stove": (1.0, 1), "statue": (0.8, 2)},
                       types={"lab": r"^AlchemistDesk\d$|^WizardWorkstation\d[a-d]?$|^Telescope2[a-g]$|^Orrery2$|"
                                     r"^Vandegraf(Small|Large)$|^FairyJar$",
                              "shelves": r"^Bookcase\d(HalfFull)?$|^PotionShelves\d$", "storage": r"^Chest\d", "plant": PLANTS,
                              "table": r"^Table[1-4]$", "stove": r"^CauldronAnimated$", "statue": r"^Statue2[aceg]$",
                              "chair": r"^Stool\d$|^CushionedStool\d$|^DarkWoodenChair\d$|^WoodenChair\d$"},
                       decor_themes=("blue", "white", "paintings"),
                       # the benches stand in a short run with a hanging between (2026-10-05: sixteen like workstations
                       # end to end down a wall), the showpieces once each (kit/furnish.py SHOWPIECES); one work table
                       # topped up with a chest or a plant, never a lone showpiece against a wall (the old recipe's
                       # top-up had stood generators and alchemist's desks singly down the walls)
                       top_up=("storage", "plant"),
                       # the desk on the back wall with the most room before it (a long room's end wall: the study end),
                       # the bench in the longest free stretch left (the long wall)
                       compose=[dict(fam="desk", slot="wall", at="corner", clear=0, seats=True, deep=True),
                                dict(fam="shelves", slot="line", near="desk", n=3, decor=2),
                                dict(fam="lab", slot="line", n=4, decor=2),
                                dict(fam="lab", slot="wall", at="center", clear=1.2, only=r"^AlchemistDesk"),
                                dict(fam="shelves", slot="line", n=2, only=r"^PotionShelves"),
                                dict(fam="storage", slot="wall", at="corner", clear=1.0),
                                dict(fam="table", slot="groups", group="alchemy", n=1, extra=True),
                                dict(fam="lab", slot="groups", group="conjuring", n=1, extra=True, min_area=100),
                                dict(fam="carpet", slot="carpet", where="under", chance=0.5),
                                dict(fam="wall_decor", slot="decor")],
                       fill=[dict(fam="desk", slot="wall", at="any", clear=0, seats=True, once=True, missing=True),
                             dict(fam="lab", slot="group", group="generators", max=1, min_area=150, fixed=True),
                             dict(fam="lab", slot="line", n=3, max=3),     # a second short bench where a wall is free
                             dict(fam="shelves", slot="line", other=True, decor=2, max=12),
                             dict(fam="lab", slot="group", group="curio", max=1, min_area=200, fixed=True),
                             dict(fam="shelves", slot="racks", kind="books", max=10, min_area=320),
                             dict(fam="statue", slot="wall", at="center", clear=0.6, max=2, fixed=True),
                             dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                             dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1)]),
    "chapel": dict(purpose="a chapel: the altar centred on a back wall between statues, a few rows of pews facing it "
                           "split by a carpeted aisle, a colonnade down the nave, a pair of statues, tapestries on the "
                           "walls, plants in the corners, open floor toward the doors",
                   # 2026-10-05 playtest: 46 pews filled the Greywatch nave wall to wall; a pew per 10 tiles, at most 16
                   core={"altar": (1, 1), "bench": (4, 16), "statue": (2, 4)},
                   # room lab (tuneB): Westwood's chapel (Con07B) holds 8 pews, 6 columns ringing the nave near its
                   # walls, tapestries, candelabras, statues by the altar: no plants, no tombs in the nave
                   optional={"column": (1.0, 8), "tomb": (0.25, 2), "wall_decor": (1.0, 6), "storage": (0.4, 1)},
                   columns_by_walls=True, statues_along=True, decor_max=6,
                   types={"altar": r"^DunMirAltar\d$", "statue": r"^Statue2[a-h]$", "bench": r"^Bench\d$|^LightBench\d$",
                          "column": r"^CathedralColumn[123]$|^Column[5-8]$", "tomb": r"^Crypt(1|3|5|6|7|8|9|10|11|12)$",
                          "storage": r"^DunMirChest\d|^Chest\d", "plant": PLANTS},
                   # tapestries of one colour, never hunting trophies (rules/rooms/chapel.md; Ambermere's chapel held a bear's head)
                   decor_themes=("blue", "red", "white", "green"),
                   # the pews stand in their rows, never topped up along the walls (Mirefen's nave had five benches lining
                   # its front walls: rules/rooms/chapel.md, open floor toward the door)
                   top_up=(),
                   # the game's altars (Westwood stands them outside its rooms, so the room statistics hold none)
                   prefer={"altar": {"DunMirAltar1": 3, "DunMirAltar2": 1},
                           "bench": {"Bench1": 1, "Bench2": 1, "Bench4": 1, "LightBench1": 1, "LightBench2": 1}},
                   compose=[dict(fam="altar", slot="wall", at="center", clear=2.6, deep=True, door=True),
                            dict(fam="statue", slot="wall", beside="altar", gap=0.8, clear=0),
                            dict(fam="statue", slot="wall", beside="altar", gap=0.8, clear=0),
                            dict(fam="bench", slot="pews", toward="altar", runner=True, columns=True, tombs=True),
                            dict(fam="wall_decor", slot="decor")],
                   # a free group of statues only in a big nave, where the open floor toward the door holds it (Harrowby's
                   # 108-tile nave had set a pair among its pews)
                   fill=[dict(fam="statue", slot="group", group="statues", max=1, min_area=180),
                         # a nave whose pews left half its floor bare (Ambermere seed 7: 6% covered; Harrowby's 108-tile
                         # nave 5%) takes a colonnade
                         dict(fam="column", slot="racks", kind="cathedral", gap=2.6, aisle=3.0, min_area=180, max=8,
                              fixed=True),
                         dict(fam="statue", slot="wall", at="corner", clear=0.6, max=2, fixed=True),
                         # a founder's tomb against a side wall where no pair lay behind the pews (a stone nave with
                         # no runner: Harrowby's, 5% covered, 12 of its 20 pieces pews)
                         dict(fam="tomb", slot="wall", at="center", clear=1.2, max=1, min_area=200, missing=True),
                         dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1)]),
    "crypt": dict(purpose="a crypt: sarcophagi and coffins in rows with aisles between, columns, statues of the dead, "
                          "crypt chests, tapestries",
                  core={"tomb": (2, 30)},
                  optional={"column": (0.8, 12), "statue": (0.6, 4), "storage": (0.6, 3), "wall_decor": (0.7, 4),
                            "plant": (0.3, 3)},
                  types={"tomb": r"^Crypt\d+$|^Coffin\d$", "column": r"^CathedralColumn\d|^Column\d$",
                         "statue": r"^Statue2[a-h]$|^Gargoyle\d$", "storage": r"^Chest\d$|^CryptChest\d$",
                         "plant": r"^PlantBarren\d$|^Plant[15]$"},
                  compose=[dict(fam="tomb", slot="racks", kind="tombs", gap=0.6, side_by_side=True, aisle=1.8),
                           dict(fam="storage", slot="wall", at="corner", clear=1.2),
                           # statues of the dead on a back wall (rules/rooms/crypt.md; Harrowby's crypt was a block of
                           # sarcophagi and nothing else)
                           dict(fam="statue", slot="wall", at="center", clear=1.0),
                           dict(fam="wall_decor", slot="decor")],
                  # an L-shaped or narrow crypt has no room for rows: its dead lie along the walls instead
                  # (Thornwick v0.1: one sarcophagus in a 58-tile crypt, 5% covered)
                  fill=[dict(fam="tomb", slot="wall", at="corner", clear=1.0, max=8),
                        dict(fam="tomb", slot="wall", at="center", clear=1.0, max=4),
                        dict(fam="column", slot="racks", kind="cathedral", gap=3.2, aisle=1.2, min_area=180),
                        dict(fam="statue", slot="group", group="statues", max=1, min_area=150),
                        # statues of the dead in the corners where the centre took none (Ambermere's 119-tile crypt
                        # held tombs and one other kind)
                        dict(fam="statue", slot="wall", at="corner", clear=0.8, max=2),
                        dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2)]),
    "hall": dict(purpose="a great hall: a colonnade down its length, statues facing each other, benches along the walls, "
                         "shields and banners on the back walls, plants in the corners",
                 core={"column": (4, 24)},
                 # room lab (tuneB): Westwood's three halls (Con04c's colonnade, Con06b's bare hall of shields and two
                 # statues, Con10c's ring of columns round its obelisks) hold no plants, benches or tables, a chest at
                 # most, a few hangings: open floor and columns
                 optional={"statue": (1.0, 6), "bench": (0.25, 2), "wall_decor": (1.0, 4), "storage": (0.3, 1)},
                 decor_max=4, statues_along=True, top_up=(),
                 types={"column": r"^Column[5-8]$|^CathedralColumn\d", "statue": r"^Statue2[a-h]$",
                        "storage": r"^DunMirChest\d|^Chest\d", "plant": PLANTS},
                 # 2026-10-05 playtest (Greywatch's keep): paired rows of columns flanking a clear aisle, never a row
                 # down the middle in line with the door
                 # Westwood's halls: 6 columns at the median (Starwell playtest, 2026-10-05)
                 compose=[dict(fam="column", slot="colonnade", gap=3.4, aisle=2.6),
                          dict(fam="wall_decor", slot="decor")],
                 fill=[dict(fam="statue", slot="group", group="statues", max=2, min_area=120, fixed=True),
                       # statues in the corners and along the walls, turned along them (Con04c's sixteen, Con06b's pair)
                       dict(fam="statue", slot="wall", at="corner", clear=0.6, max=2, fixed=True),
                       dict(fam="bench", slot="wall", max=1, fixed=True),
                       dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1, fixed=True)]),
    "great_hall": dict(purpose="a lord's great hall, the heart of the house every other room opens onto: the hearth on a "
                               "back wall, long tables with benches down the middle, banners and trophies on the back "
                               "walls, statues in pairs, benches along the walls, aisles clear along the doors",
                       base="dining_hall",    # its density and pieces are a feast hall's (a hall's trimmed its boards to four tables)
                       # 2026-10-04 review: "the sheer number of tables and chairs was too much", 4-6 sets fewer;
                       # a table per 48 tiles (was 30), at most 6, and a carpet of floor tiles over the open floor
                       # room lab (tuneB): Westwood's great halls (Con06b, Con07E) set their tables end to end into
                       # long boards (Con06b: twelve Table1/2 in a U round a free hearth, benches down both sides of
                       # each board), hang their walls with shields and banners, keep no plants and no statues; a free
                       # hearth or two, not a wall hearth and two free ones. A long board counts its pieces, so a
                       # table piece per 24 tiles reads as two or three boards (2026-10-04: "4-6 sets fewer")
                       core={"table": (2, 12), "bench": (4, 24), "fireplace": (1, 2)},
                       per_tiles={"table": 24},
                       optional={"wall_decor": (1.0, 12), "storage": (0.5, 1), "chair": (0.5, 4)},
                       types={"table": r"^Table[1-4]$|^OvalTable[12]$", "bench": r"^Bench\d$|^CushionedBench\d$",
                              "storage": CHEST},
                       prefer={"fireplace": {"Fireplace1": 1, "Fireplace2": 1, "Fireplace3": 2, "Fireplace4": 1}},
                       # shields and crossed arms, banners of one colour, or trophies of the hunt (rules/rooms/great_hall.md)
                       decor_themes=("arms", "red", "blue", "green", "trophies"),
                       group_seats={"hearth": (0, 0)},          # Westwood's free hearths stand alone (Con06b's three)
                       by_walls=("hearth",), decor_max=6,       # toward a corner, not before the door; banners in a few places
                       top_up=(),
                       compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.6),
                                dict(fam="table", slot="table_rows", seat="bench", joined=3),
                                dict(fam="carpet", slot="carpet", where="under", margin=2.0, chance=1.0),
                                # hangings either side of the hearth: two at least, the walls carry an open hall
                                # (rules/rooms/great_hall.md; Harrowby's moot hall had one)
                                dict(fam="wall_decor", slot="decor"), dict(fam="wall_decor", slot="decor")],
                       fill=[dict(fam="fireplace", slot="group", group="hearth", max=1, min_area=440, fixed=True),
                             # a bench in each front corner, where those who wait sit (Harrowby playtest, HB-2: "a
                             # little bit too empty. It needs some more objects and fill along the southeast wall in the
                             # south corner")
                             dict(fam="bench", slot="wall", at="room_corner", clear=0, max=2, fixed=True),
                             dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1)]),
    # 2026-10-05 playtest (Greywatch's keep: the throne "facing sideways towards the store room", "the pillars are in the
    # dead center of the room", statues facing the wall): Westwood's Dun Mir throne faces SE only, so it stands on the NW
    # wall across the room from the door in the SE wall (kit/building.py puts that door there), a runner and a clear aisle
    # between them, columns in pairs of rows either side, statues flanking the throne and lining the aisle facing in
    # 2026-10-05, Starwell playtest: "The throne room is also kind of empty and barren. It's just a long room with tons of
    # the same exact pillars. It doesn't have any character" (the Hall of the Star: 22 columns 3.4 units apart down both
    # sides of the runner, hunting trophies on the walls). Westwood's halls hold about 6 columns, 4 statues, tapestries:
    # a few pairs of columns spread down the length, statues between them facing across the aisle, candelabras before
    # the throne, tapestries of one colour on the back walls, a bench or two; nothing in the aisle (an orrery tried there
    # stood in the way of the throne's view of its door)
    "throne_room": dict(purpose="a throne room: the throne centred on the NW wall facing the door across the room, statues "
                                "flanking it and braziers before it, a clear aisle and a carpet runner from the door to "
                                "the throne, a few pairs of columns spread down its length, a pair of statues facing "
                                "across the aisle and braziers lining it, a few tapestries of one colour",
                        core={"throne": (1, 4), "column": (2, 8)},
                        # room lab (tuneB): Westwood's four throne rooms hold no plants or benches, a chest at most
                        # (Con11a's two), their hangings in a few places (Hecubah's war poles by the door, the Lich
                        # Lord's tapestries in pairs), not evenly down every wall; flame basins line the runner in pairs
                        optional={"statue": (1.0, 6), "wall_decor": (1.0, 4), "storage": (0.3, 1)},
                        types={"throne": r"^DunMirThrone", "column": r"^Column[5-8]$|^CathedralColumn\d",
                               "statue": r"^Statue2[a-h]$", "storage": r"^DunMirChest\d|^Chest\d"},
                        decor_themes=("blue", "red", "white", "green"),
                        decor_max=4, statues_along=True,
                        top_up=(),                   # never chests, benches or plants down the walls to fill the floor
                        compose=[dict(fam="throne", slot="throne"),
                                 dict(fam="statue", slot="flank", of="throne", gap=0.8),
                                 dict(fam="light", slot="flank_lights", of="throne", gap=0.9),
                                 dict(fam="column", slot="colonnade", gap=5.0, aisle=3.0),
                                 dict(fam="light", slot="aisle_lights", n=2),
                                 dict(fam="statue", slot="groups", group="statues", n=1, extra=True, min_area=100),
                                 # statues of the house in the back corners where the aisle took no pair
                                 dict(fam="statue", slot="wall", at="corner", clear=0.6, n=2),
                                 dict(fam="wall_decor", slot="decor")],
                        fill=[dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1, fixed=True)]),
    "barracks": dict(purpose="bunks for a crew: beds of one kind spaced along a front wall, a nightstand between "
                             "neighbours, a chest a step beyond each bed's foot, a rug before each bed, shelves for their "
                             "gear end to end on a back wall, shields and trophies on the back walls, a table with seats",
                     core={"bed": (2, 8), "storage": (0, 10), "shelves": (2, 8)}, per_tiles={"bed": 15},
                     optional={"fireplace": (0.3, 1), "bench": (0.3, 4), "table": (0.6, 1), "chair": (0.6, 4), "rug": (1.0, 8), "wall_decor": (1.0, 5),
                               "nightstand": (1.0, 6)},
                     types={"fireplace": r"^FreestandingFireplace$", "storage": r"^Chest\d$", "bed": r"^Cot\d|^WoodBed\d|^Bed\d",
                            "shelves": r"^LogShelvesFull\d$|^Bookcase\d$", "chair": r"Stool|Chair"},
                     prefer={"bed": {"Cot1": 2, "Cot4": 1, "WoodBed2": 1},
                             "rug": {"RedRug1": 1, "RedRug2": 1, "RedRug3": 1, "RedRug4": 1},
                             "shelves": {"LogShelvesFull1": 1, "LogShelvesFull2": 1, "LogShelvesFull3": 1, "LogShelvesFull4": 1}},
                     compose=[dict(fam="bed", slot="bed_row"),
                              dict(fam="shelves", slot="line", n=6),
                              dict(fam="table", slot="center", seats=True),
                              dict(fam="wall_decor", slot="decor")],
                     fill=[dict(fam="shelves", slot="line", other=True, max=8, min_area=120), dict(fam="table", slot="group", group="dining", max=1, min_area=170), dict(fam="fireplace", slot="group", group="hearth", max=1, min_area=300), dict(fam="shelves", slot="line", n=6, max=6),
                           dict(fam="storage", slot="wall", at="center", clear=1.6, max=1)]),
    # ---- the cultures' rooms (rules/cultures.py, rules/out/cultures.json): Westwood furnishes its ogre lairs and the
    # Land of the Dead's temples with their own pieces. Ogre rooms (18 measured, median 42 tiles): straw heaped free on
    # the floor in 72% of them, crude beds against the back walls, stools, round tables, meat and carcasses, barrels,
    # torch poles. Land of the Dead rooms (47, median 45 tiles): sconces on the back walls (88-94%), mana obelisks and
    # tombstones, tapestries on the back walls, bones and skulls strewn free (10 and 8 per 100 tiles).
    "ogre_den": dict(purpose="where the ogres sleep: straw heaped over the floor, crude beds against the back walls, a "
                             "fire pit ringed by stools, meat and carcasses left about, barrels by the walls",
                     base="barracks",
                     core={"straw": (4, 80), "fireplace": (1, 2)},
                     optional={"bed": (0.8, 4), "chair": (1.0, 8), "storage": (1.0, 8), "clutter": (1.0, 16)},
                     types={"straw": r"^OgreStraw\d$", "fireplace": r"^OgreFirePit$", "bed": r"^OgreBed\d$",
                            "chair": r"^OgreStool\d$", "storage": r"^Barrel2?$|^OgreSack\d$|^PiledBarrels\d$",
                            "clutter": r"^OgreHutMeat$|^OgreHutCarcass(Big)?$"},
                     prefer={"straw": {"OgreStraw1": 5, "OgreStraw2": 2, "OgreStraw3": 2, "OgreStraw4": 1, "OgreStraw5": 1},
                             "fireplace": {"OgreFirePit": 1}, "bed": {"OgreBed1": 1, "OgreBed2": 1},
                             "chair": {"OgreStool1": 2, "OgreStool2": 1},
                             "storage": {"Barrel": 2, "Barrel2": 1, "OgreSack1": 1, "OgreSack2": 1},
                             "clutter": {"OgreHutMeat": 4, "OgreHutCarcass": 1, "OgreHutCarcassBig": 1}},
                     lights={"TorchPole": 1},
                     compose=[dict(fam="fireplace", slot="groups", group="firepit", n=1),
                              dict(fam="bed", slot="wall", at="any", clear=0.6, n=3),
                              # Westwood's ogre rooms: straw 8.6 per 100 tiles where it lies (rules/CULTURES.md); per100
                              # counts heaps of 2-3: Harrowby's 80-tile den had 26 of its 32 pieces straw (TW-8)
                              dict(fam="straw", slot="scatter", per100=4, cluster=(2, 3)),
                              dict(fam="storage", slot="wall", at="corner", clear=0.4, group=True),
                              dict(fam="clutter", slot="scatter", per100=3, cluster=(1, 2))],
                     fill=[dict(fam="fireplace", slot="group", group="firepit", max=1, min_area=260),
                           dict(fam="straw", slot="scatter", per100=1, max=12),
                           dict(fam="storage", slot="wall", at="corner", clear=0.4, max=6)]),
    "ogre_hall": dict(purpose="where the ogres feast: crude round tables ringed by stools, a fire pit, carcasses and meat "
                              "on the floor, straw in the corners, barrels by the walls",
                      base="dining_hall",
                      core={"table": (2, 12), "fireplace": (1, 1)},
                      # room lab (tuneB): the ogres' feasting room (Con05C) holds two crude tables ringed by stools,
                      # barrels heaped by the walls, skull posts; no straw on its floor
                      optional={"chair": (1.0, 16), "storage": (1.0, 8), "clutter": (1.0, 5)},
                      types={"table": r"^OgreTable[123]$", "chair": r"^OgreStool\d$|^OgreBench[34]$",
                             "fireplace": r"^OgreFirePit$", "storage": r"^Barrel2?$|^OgreSack\d$|^PiledBarrels\d$",
                             "clutter": r"^OgreHutMeat$|^OgreHutCarcass(Big)?$", "straw": r"^OgreStraw\d$"},
                      prefer={"table": {"OgreTable1": 2, "OgreTable2": 1, "OgreTable3": 2},
                              "chair": {"OgreStool1": 3, "OgreStool2": 2, "OgreBench3": 1, "OgreBench4": 1},
                              "fireplace": {"OgreFirePit": 1},
                              "storage": {"Barrel": 2, "Barrel2": 1, "OgreSack1": 1, "PiledBarrels2": 1},
                              "clutter": {"OgreHutMeat": 3, "OgreHutCarcass": 1, "OgreHutCarcassBig": 1},
                              "straw": {"OgreStraw1": 3, "OgreStraw2": 1, "OgreStraw3": 1}},
                      per_tiles={"table": 45},
                      lights={"TorchPole": 1},
                      compose=[dict(fam="fireplace", slot="groups", group="firepit", n=1),
                               dict(fam="table", slot="groups", group="ogre_table"),
                               dict(fam="storage", slot="wall", at="corner", clear=0.4, group=True),
                               dict(fam="clutter", slot="scatter", per100=1.5, cluster=(1, 2))],
                      top_up=(),
                      fill=[dict(fam="table", slot="group", group="ogre_table", max=3),
                            dict(fam="storage", slot="wall", at="corner", clear=0.4, max=2, fixed=True)]),
    "ogre_hoard": dict(purpose="the ogres' hoard: barrels, sacks and crates heaped along the walls, a chest at the back, "
                               "carcasses hung to cure, bones about",
                       base="storeroom",
                       core={"storage": (6, 40)},
                       optional={"clutter": (1.0, 8), "bones": (0.8, 12)},
                       types={"storage": r"^Barrel2?$|^OgreSack\d$|^PiledBarrels\d$|^Crate[12]$|^DarkCrate[12]$|^Chest\d$",
                              "clutter": r"^OgreHutMeat$|^OgreHutCarcass(Big)?$"},
                       prefer={"clutter": {"OgreHutCarcass": 2, "OgreHutCarcassBig": 1, "OgreHutMeat": 2},
                               "bones": {"Skull": 1, "ArmBone": 2, "LegBone": 2}},
                       lights={"TorchPole": 1},
                       compose=[dict(fam="storage", slot="stock", coverage=0.8, kinds=("barrels", "sacks", "crates"), pad=1.0),
                                dict(fam="clutter", slot="scatter", per100=4, cluster=(1, 2)),
                                dict(fam="bones", slot="scatter", per100=6, cluster=(1, 3))],
                       fill=[dict(fam="storage", slot="stock", coverage=1.0, kinds=("barrels", "sacks", "crates"), pad=0.8, max=20),
                             dict(fam="storage", slot="stack", n=3, once=True)]),
    "dark_chapel": dict(purpose="the Land of the Dead's chapel: the lich god's statue on a back wall, mana obelisks and "
                                "arks along the walls, judgement balances standing in a pair, tapestries and sconces on "
                                "the back walls, bones and skulls strewn about",
                        base="chapel",
                        core={"altar": (1, 1), "statue": (4, 14)},
                        # 2026-10-05 playtest rule (large rooms mix their pieces): Ambermere's 300-tile barrow hall held
                        # a block of 20 obelisks and arks down its middle
                        optional={"wall_decor": (1.0, 6), "tomb": (0.5, 4), "bones": (1.0, 30), "column": (0.6, 8)},
                        types={"altar": r"^LOTDLichGodStatue[12]$",
                               "statue": r"^LOTDManaObelisk$|^LOTDJudgementBalance[12]$|^LOTDArk[12]$",
                               "wall_decor": r"^LOTDTapestry[12]$|^LOTDBanner[12]$", "tomb": r"^LOTDTombstone[1-4]$",
                               "column": r"^LOTDColumn1$"},
                        prefer={"altar": {"LOTDLichGodStatue1": 1, "LOTDLichGodStatue2": 1},
                                "statue": {"LOTDManaObelisk": 3, "LOTDArk1": 1, "LOTDArk2": 1},
                                "wall_decor": {"LOTDTapestry1": 2, "LOTDTapestry2": 2, "LOTDBanner1": 1},
                                "tomb": {"LOTDTombstone1": 2, "LOTDTombstone3": 1, "LOTDTombstone4": 1},
                                "bones": {"Skull": 3, "ArmBone": 3, "LegBone": 2}},
                        lights={"LOTDWallSconse1": 2, "LOTDCandleabra1": 1},
                        # the god's statue across the hall from the way in, looking down it; columns in pairs either
                        # side of the aisle, never a block in the middle (2026-10-05 playtest rule, the keep's throne)
                        compose=[dict(fam="altar", slot="wall", at="center", clear=2.6, door=True),
                                 dict(fam="column", slot="colonnade", gap=3.4, aisle=3.0),
                                 dict(fam="statue", slot="wall", at="corner", clear=0.8, n=4),
                                 dict(fam="statue", slot="groups", group="balances", n=1),
                                 dict(fam="bones", slot="scatter", per100=10, cluster=(1, 3)),
                                 dict(fam="wall_decor", slot="decor")],
                        fill=[dict(fam="tomb", slot="racks", kind="lotd_tombs", gap=1.0, aisle=1.8, min_area=400, max=12),
                              dict(fam="statue", slot="racks", kind="obelisks", gap=2.6, aisle=3.0, min_area=200, max=20),
                              dict(fam="statue", slot="wall", at="center", clear=0.8, max=6),
                              dict(fam="tomb", slot="wall", at="corner", clear=0.6, max=4, min_area=150),
                              dict(fam="statue", slot="group", group="balances", max=1, min_area=260)]),
    "dark_crypt": dict(purpose="the Land of the Dead's crypt: tombstones in rows with aisles between, mana obelisks at the "
                               "walls, sconces and candles, bones and skulls strewn over the floor",
                       base="crypt",
                       core={"tomb": (4, 40)},
                       optional={"statue": (0.8, 4), "wall_decor": (0.6, 3), "bones": (1.0, 40)},
                       types={"tomb": r"^LOTDTombstone[1-4]$", "statue": r"^LOTDManaObelisk$",
                              "wall_decor": r"^LOTDTapestry[12]$"},
                       prefer={"statue": {"LOTDManaObelisk": 1}, "wall_decor": {"LOTDTapestry1": 1, "LOTDTapestry2": 1},
                               "bones": {"Skull": 3, "ArmBone": 3, "LegBone": 2}},
                       lights={"LOTDWallSconse1": 2, "LOTDCandleabra1": 1},
                       compose=[dict(fam="tomb", slot="racks", kind="lotd_tombs", gap=1.0, aisle=1.8),
                                dict(fam="statue", slot="wall", at="corner", clear=0.8, n=2),
                                dict(fam="bones", slot="scatter", per100=12, cluster=(1, 3)),
                                dict(fam="wall_decor", slot="decor")],
                       fill=[dict(fam="tomb", slot="racks", kind="lotd_tombs", gap=1.0, aisle=1.8, max=24),
                             dict(fam="tomb", slot="wall", at="center", clear=0.6, max=8),
                             dict(fam="statue", slot="wall", at="corner", clear=0.8, max=4)]),
    # ---- more types for variety (2026-10-05; kit/roomtypes.py, rules/rooms/<type>.md). Each is composed from the
    # furnisher's existing steps. `lift`: the furnishing style's excluded prefixes a kind takes back (a torture chamber's
    # racks in a town keep: kit/furnish.py STYLE_EXCLUDE drops Torture, Pulley, Mine, Crypt, Coffin and DunMir from a
    # town house); `grand`: statues and columns stand in it in a town house, as in kit/furnish.py GRAND_ROOMS.
    # the lord's private chamber (Con07D's, 102 tiles: the bed, the hearth, twelve bookcases, two small tables,
    # tapestries; Con06b's Dun Mir chambers): a bedroom at one end, a sitting room at the other
    "solar": dict(base="laboratory",
                  purpose="the lord's private chamber, used in two ends: the bed headboard to a back wall with its "
                          "nightstand and a chest snug before a rug; the hearth centred on the other back wall between "
                          "bookcases, the desk on a stretch of its own, a small table and chairs on a carpet before the "
                          "sitting end, tapestries, a bench, plants",
                  core={"bed": (1, 1), "fireplace": (1, 1), "desk": (1, 1), "shelves": (2, 10), "storage": (1, 2),
                        "table": (1, 1), "chair": (2, 4)},
                  optional={"nightstand": (1.0, 1), "rug": (1.0, 2), "wall_decor": (1.0, 6), "bench": (0.7, 1),
                            "plant": (0.7, 2)},
                  types={"bed": r"^Bed[2-4]$|^WoodBed[1-3]$", "storage": CHEST, "shelves": r"^Bookcase\d(HalfFull)?$",
                         "table": r"^RoundTable[12]$|^SquareTable[12]$|^SmallTable2$", "plant": PLANTS,
                         "desk": r"^Desk[12]$"},
                  prefer={"fireplace": {"Fireplace3": 2, "Fireplace4": 1}},
                  decor_themes=("blue", "red", "white", "green", "trophies"),
                  top_up=("storage", "plant", "bench"),
                  compose=[dict(fam="bed", slot="wall", at="corner", clear=1.0),
                           dict(fam="fireplace", slot="wall", at="center", clear=2.4, rug=True),
                           dict(fam="shelves", slot="line", near="fireplace", n=4, decor=2),
                           dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                           dict(fam="storage", slot="wall", at="center", clear=2.3),
                           dict(fam="table", slot="center", seats=True, rug=True),
                           dict(fam="carpet", slot="carpet", where="under", chance=0.5),
                           dict(fam="wall_decor", slot="decor")],
                  fill=[dict(fam="shelves", slot="line", other=True, decor=2, max=8),
                        dict(fam="bench", slot="wall", at="center", clear=0, max=1),
                        dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                        dict(fam="table", slot="group", group="sitting", max=1, min_area=180),
                        dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1)]),
    # a wheelwright's or a carpenter's shop (Con06a / War01A, 25-29 tiles: an anvil, a tool barrel, gears, cart wheels,
    # trader's shelves): the work bench, the tools on the shelves, wheels and parts by the bench. No forge: that is the
    # smithy's
    "workshop": dict(base="smithy",
                     purpose="a craftsman's workshop: trader's shelves of tools lining a back wall, the work bench (a long "
                             "table) with its stool and a crate or barrel by it, cart wheels and gears lying by the bench, "
                             "tool barrels and crates of timber and iron heaped toward the front corners",
                     core={"table": (1, 3), "storage": (3, 14), "shop_rack": (1, 6)},
                     optional={"chair": (1.0, 3), "parts": (1.0, 6), "anvil": (0.7, 1), "gearwork": (0.6, 1)},
                     types={"table": r"^Table[1-4]$", "storage": r"^BarrelWithTools[12]$|^(Dark)?Crate[12]$|^Barrel2?$",
                            "shop_rack": r"^TraderShelves[12]$", "chair": r"^Stool\d$|^CushionedStool\d$",
                            "parts": r"^MineOreCartWheel$|^MechGear$", "anvil": r"^Anvil[2468]$", "gearwork": r"^Gear[1-4]$"},
                     prefer={"storage": {"BarrelWithTools1": 3, "BarrelWithTools2": 3, "Crate1": 1, "Crate2": 1,
                                         "DarkCrate1": 1, "Barrel": 1},
                             "parts": {"MineOreCartWheel": 3, "MechGear": 1}, "anvil": {"Anvil2": 1, "Anvil6": 1},
                             "gearwork": {"Gear1": 1, "Gear2": 1, "Gear3": 1, "Gear4": 1}},
                     lift=("Mine|",),
                     compose=[dict(fam="shop_rack", slot="line", n=3),
                              dict(fam="table", slot="groups", group="worktable", n=1, extra=True),
                              dict(fam="anvil", slot="wall", at="corner", clear=1.4),
                              dict(fam="gearwork", slot="wall", at="center", clear=1.0),
                              dict(fam="storage", slot="stock", coverage=0.5, kinds=("tools", "crates", "barrels"), pad=1.2),
                              dict(fam="parts", slot="scatter", per100=4, cluster=(1, 2), wall_gap=1.0)],
                     fill=[dict(fam="table", slot="group", group="worktable", max=2, min_area=70),
                           dict(fam="shop_rack", slot="line", other=True, max=3),
                           dict(fam="storage", slot="stock", coverage=0.8, kinds=("tools", "crates", "barrels"), pad=1.0, max=6),
                           dict(fam="storage", slot="stack", n=3, once=True)]),
    # the winch rooms that work a castle's gates, lifts and bridges (Con06a, 110 tiles: 18 gears, a pulley gear, a
    # lever; War07A; War02b's lift room): gear trains on the walls, the great winch standing free
    "winch_room": dict(base="storeroom",
                       purpose="the machinery that works a gate, a lift or a bridge: gear trains against the back walls, "
                               "the great winch (a pulley gear) standing free with room to work it, small gears by it, "
                               "tool barrels and crates of spare parts by the front walls",
                       core={"gearwork": (2, 6), "winch": (1, 1), "storage": (1, 6)},
                       optional={"parts": (0.8, 4)},
                       types={"gearwork": r"^Gear[1-6]$", "winch": r"^PulleyGear[13468]$",
                              "storage": r"^BarrelWithTools[12]$|^(Dark)?Crate[12]$|^Barrel$", "parts": r"^MechGear$"},
                       prefer={"winch": {"PulleyGear1": 1, "PulleyGear3": 2, "PulleyGear6": 1, "PulleyGear8": 1},
                               "gearwork": {f"Gear{k}": 1 for k in range(1, 7)}, "parts": {"MechGear": 1},
                               "storage": {"BarrelWithTools1": 2, "BarrelWithTools2": 2, "DarkCrate1": 1, "Crate2": 1}},
                       lift=("Pulley|",),
                       top_up=(),
                       compose=[dict(fam="gearwork", slot="wall", at="center", clear=1.2, n=2),
                                dict(fam="winch", slot="center"),
                                dict(fam="storage", slot="stock", coverage=0.25, kinds=("tools", "crates"), pad=1.4),
                                dict(fam="parts", slot="scatter", per100=3, cluster=(1, 2), wall_gap=1.0)],
                       fill=[dict(fam="winch", slot="center", max=1, min_area=300, fixed=True),
                             dict(fam="gearwork", slot="wall", at="corner", clear=1.0, max=2),
                             dict(fam="storage", slot="wall", at="corner", clear=0.4, group=True, max=3)]),
    # an astronomer's room (Con07B, 97 tiles: three telescopes, a desk, statues; Con07E's star hall: eight star charts,
    # blue tapestries): telescopes at the walls and one free, star charts hung between the bookcases
    "observatory": dict(base="laboratory",
                        purpose="an astronomer's observatory: the desk near a corner of a back wall with bookcases either "
                                "side, star charts and zodiacs hung on the back walls, a telescope at a wall and a "
                                "telescope or an orrery standing free with room round it, the chart table with its stools, "
                                "a chest, plants",
                        core={"lab": (2, 4), "desk": (1, 1), "shelves": (2, 10), "wall_decor": (2, 8)},
                        optional={"table": (0.8, 1), "chair": (0.8, 3), "storage": (0.7, 1), "plant": (0.6, 2)},
                        types={"lab": r"^Telescope(1[bc]|2[aceg]|3[af])$|^Orrery2$", "shelves": r"^Bookcase\d(HalfFull)?$",
                               "storage": r"^Chest\d$", "table": r"^Table[1-4]$|^SquareTable[12]$", "plant": PLANTS,
                               "chair": r"^Stool\d$|^CushionedStool\d$|^DarkWoodenChair\d$|^WoodenChair\d$",
                               "desk": r"^Desk[12]$"},
                        prefer={"wall_decor": {"StarChart1a": 1, "StarChart2a": 1, "StarChart4a": 1, "StarChart2c": 1,
                                               "Zodiac1c": 1, "Zodiac2a": 1}},
                        decor_at="any",
                        top_up=("storage", "plant"),
                        compose=[dict(fam="lab", slot="groups", group="curio", n=1, extra=True),
                                 dict(fam="lab", slot="wall", at="any", clear=1.2, only=r"^Telescope"),
                                 dict(fam="desk", slot="wall", at="corner", clear=0, seats=True, deep=True),
                                 dict(fam="shelves", slot="line", near="desk", n=3),
                                 dict(fam="table", slot="center", seats=True),
                                 dict(fam="wall_decor", slot="decor"), dict(fam="wall_decor", slot="decor"),
                                 dict(fam="wall_decor", slot="decor")],
                        fill=[dict(fam="shelves", slot="line", other=True, max=6),
                              dict(fam="lab", slot="group", group="curio", max=1, min_area=150, fixed=True),
                              dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                              dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1)]),
    # no campaign room nurses the sick: a barracks' row of cots with a herbalist's shelves and cauldron (rules/rooms/
    # infirmary.md stands on design judgement)
    "infirmary": dict(base="barracks",
                      purpose="where the sick are nursed: a row of cots with a nightstand between neighbours, a pair of "
                              "potion shelves and books of remedies on a back wall, the cauldron toward a corner, the "
                              "healer's table with its stool, a chest of linen, hangings of one colour",
                      core={"bed": (2, 8), "shelves": (2, 8), "stove": (1, 1), "table": (1, 1)},
                      per_tiles={"bed": 15},
                      optional={"nightstand": (1.0, 6), "chair": (1.0, 2), "storage": (0.8, 2), "wall_decor": (1.0, 4),
                                "plant": (0.5, 2)},
                      types={"bed": r"^Cot\d$|^WoodBed[12]$", "shelves": r"^PotionShelves[1-4]$|^Bookcase\d(HalfFull)?$",
                             "stove": r"^CauldronAnimated$", "table": r"^Table4$|^SquareTable[12]$",
                             "storage": r"^Chest\d$|^SackChest(Medium|Small)[12]$", "plant": PLANTS,
                             "chair": r"^Stool\d$|^CushionedStool\d$"},
                      prefer={"bed": {"Cot1": 2, "Cot4": 1, "WoodBed2": 1},
                              "shelves": {"PotionShelves1": 1, "PotionShelves2": 1, "PotionShelves3": 1, "PotionShelves4": 1,
                                          "Bookcase1": 1, "Bookcase2": 1, "Bookcase3": 1, "Bookcase4": 1}},
                      decor_themes=("white", "blue", "green"),
                      compose=[dict(fam="bed", slot="bed_row"),
                               dict(fam="stove", slot="wall", at="corner", clear=1.6),
                               dict(fam="shelves", slot="line", n=2, only=r"^PotionShelves"),
                               dict(fam="shelves", slot="line", n=3, only=r"^Bookcase"),
                               dict(fam="table", slot="center", seats=True),
                               dict(fam="wall_decor", slot="decor")],
                      fill=[dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1),
                            dict(fam="shelves", slot="line", other=True, max=4, only=r"^Bookcase"),
                            dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2)]),
    # a keg cellar (Con07B's 17 tiles: eight kegs and two crates; Con06b and War02b: five kegs; Con06a / War01A: seven
    # barrels, a great cask, piled barrels, crates)
    "cellar": dict(base="storeroom",
                   purpose="a cellar of kegs and casks: kegs in tight rows along the walls from the corners, a great "
                           "cask or two standing free with kegs beside them, piled barrels, a few crates, aisles to walk",
                   core={"storage": (6, 30)},
                   optional={},
                   types={"storage": r"^(Barrel|Barrel2|LargeBarrel[12]|PiledBarrels[1-4]|DarkCrate[12]|Crate[12])$"},
                   prefer={"storage": {"Barrel2": 4, "Barrel": 2, "PiledBarrels1": 1, "PiledBarrels2": 1, "DarkCrate1": 1}},
                   compose=[dict(fam="storage", slot="wall", at="corner", clear=0.4, group=True, n=6),
                            dict(fam="storage", slot="groups", group="kegs", n=1, extra=True, min_area=40),
                            dict(fam="storage", slot="stock", coverage=0.8, kinds=("barrels", "crates"), pad=1.0)],
                   fill=[dict(fam="storage", slot="group", group="kegs", max=1, min_area=80, fixed=True),
                         dict(fam="storage", slot="stock", coverage=1.0, kinds=("barrels",), pad=0.6),
                         dict(fam="storage", slot="wall", at="corner", clear=0.4, group=True, max=6)]),
    # a strongroom (Con05B: the ogres' chests and gold; Wiz06c: Dun Mir chests under hanging shields; Con06b: chests and a
    # round table with four chairs)
    "treasury": dict(base="storeroom",
                     purpose="a strongroom: strongboxes in a row along the back walls, each with room before it to open, "
                             "the treasurer's counting table and chair in the middle, tally shelves, shields and crossed "
                             "arms hung on the walls",
                     core={"storage": (3, 6), "table": (1, 1), "chair": (1, 2)},
                     optional={"shop_rack": (0.7, 2), "wall_decor": (1.0, 4)},
                     types={"storage": r"^Chest[1-4]$", "table": r"^SquareTable[12]$|^Table[1-4]$",
                            "shop_rack": r"^TraderShelves[12]$|^TraderShieldWallHanging\d$|^TraderCrossedWeapons\d$",
                            "chair": r"Chair"},
                     prefer={"shop_rack": {"TraderShelves1": 1, "TraderShelves2": 1}},
                     decor_themes=("arms",),
                     top_up=("storage",),
                     compose=[dict(fam="storage", slot="wall", at="center", clear=2.0, group=True, n=3),
                              dict(fam="table", slot="center", seats=True),
                              dict(fam="shop_rack", slot="line", n=2, other=True),
                              dict(fam="wall_decor", slot="decor"), dict(fam="wall_decor", slot="decor")],
                     fill=[dict(fam="storage", slot="wall", at="any", clear=2.0, max=2, fixed=True)]),
    # a powder magazine (Con07C, 31 tiles: 22 powder kegs; Con09c, 30 tiles: 11 powder kegs and 2 barrels): the one room
    # black powder belongs in, kept apart
    "powder_store": dict(base="storeroom",
                         purpose="a powder magazine: kegs of black powder in tight rows along the walls from the corners, "
                                 "a few plain barrels and crates by the door, the middle clear",
                         core={"storage": (6, 30)},
                         optional={},
                         types={"storage": r"^BlackPowderBarrel2?$|^Barrel$|^DarkCrate[12]$"},
                         prefer={"storage": {"BlackPowderBarrel": 4, "BlackPowderBarrel2": 2}},
                         top_up=(),
                         compose=[dict(fam="storage", slot="wall", at="corner", clear=0.4, group=True, n=12),
                                  dict(fam="storage", slot="stock", coverage=0.3, kinds=("barrels", "crates"), pad=1.2)],
                         fill=[dict(fam="storage", slot="wall", at="corner", clear=0.4, group=True, max=12),
                               dict(fam="storage", slot="wall", at="center", clear=0.4, group=True, max=8)]),
    # the watch's room (Con03A / War03a, 63 tiles: two cots, chests, a table with a meal and four chairs, hanging swords,
    # a bear's head, the archer and the swordsman on watch; Con06a's 55 tiles: tables, benches, shields; Con02a's
    # gaoler's room by the cells: a table, racks of bows and swords)
    "guardroom": dict(base="barracks",
                      purpose="where the watch waits between rounds: two or three cots against a back wall with a chest "
                              "at each, swords, pole arms and bows racked on the walls with shields and crossed arms hung "
                              "between, the watch's table with its chairs and a meal on it, barrels of water and ale by "
                              "the front walls, a bench",
                      core={"table": (1, 2), "chair": (2, 6), "bed": (1, 3), "shop_rack": (1, 6), "storage": (1, 4)},
                      optional={"bench": (0.6, 1), "wall_decor": (1.0, 3)},
                      types={"table": r"^RoundTableWithFood$|^RoundTable[12]$|^SquareTable[12]$",
                             "chair": r"Chair|Stool", "bed": r"^Cot\d$",
                             "shop_rack": r"^Trader(HangingSwords[12]|PoleArm[1-4]|BowRack[12]|QuiverRack|"
                                          r"ShieldWallHanging\d|CrossedWeapons\d)$",
                             "storage": r"^Chest[1-4]$|^Barrel2?$|^WaterBarrel$",
                             "wall_decor": r"^WallTrophy(Bear|Moose|MountainLion)[12]$",
                             "bench": r"^Bench[1-4]$|^LightBench\d$"},
                      prefer={"shop_rack": {"TraderHangingSwords1": 2, "TraderHangingSwords2": 2, "TraderPoleArm1": 1,
                                            "TraderPoleArm3": 1, "TraderBowRack2": 1, "TraderQuiverRack": 1},
                              "table": {"RoundTableWithFood": 3, "RoundTable1": 1, "SquareTable1": 1},
                              "bed": {"Cot1": 2, "Cot4": 1}},
                      decor_themes=("arms", "trophies"),
                      top_up=("storage", "bench"),
                      compose=[dict(fam="bed", slot="wall", at="corner", clear=1.0, n=2),
                               dict(fam="storage", slot="wall", at="center", clear=2.3, only=r"^Chest"),
                               dict(fam="shop_rack", slot="line", n=4),
                               dict(fam="table", slot="center", seats=True),
                               dict(fam="storage", slot="stock", coverage=0.25, kinds=("barrels",), pad=1.2, per_wall=0.4),
                               dict(fam="wall_decor", slot="decor")],
                      fill=[dict(fam="shop_rack", slot="line", other=True, max=3),
                            dict(fam="bed", slot="wall", at="corner", clear=1.0, max=1, min_area=50),
                            dict(fam="bench", slot="wall", at="center", clear=0, max=1)]),
    # a cell (War07A, 13 tiles: a cot, straw, a jail door; Con11a's ogre pens, 30-35 tiles: straw, the stocks)
    "cell": dict(base="bedroom",
                 purpose="a cell: straw strewn over the floor, a cot against a back wall, the stocks in a bigger cell, a "
                         "few bones; nothing else",
                 core={"straw": (2, 10), "bed": (1, 1)},
                 optional={"stocks": (0.4, 1), "bones": (0.6, 4)},
                 types={"straw": r"^Straw[12]$", "bed": r"^Cot\d$", "stocks": r"^Stocks[1-5]$"},
                 prefer={"straw": {"Straw2": 3, "Straw1": 1}, "bed": {"Cot1": 1, "Cot4": 1},
                         "stocks": {"Stocks3": 1, "Stocks4": 1}, "bones": {"Skull": 1, "ArmBone": 2, "LegBone": 2}},
                 top_up=(),
                 compose=[dict(fam="bed", slot="wall", at="corner", clear=0.8),
                          dict(fam="stocks", slot="wall", at="center", clear=1.0, min_area=20),
                          dict(fam="straw", slot="scatter", per100=10, cluster=(1, 3), wall_gap=1.0),
                          dict(fam="bones", slot="scatter", per100=4, cluster=(1, 2))],
                 fill=[dict(fam="straw", slot="scatter", per100=4, max=6)]),
    "ogre_pen": dict(base="bedroom",
                     purpose="the ogres' pen for their captives (Con11a): straw heaped on the floor, the stocks against a "
                             "wall, bones",
                     core={"straw": (3, 12), "stocks": (1, 1)},
                     optional={"bones": (0.8, 6)},
                     types={"straw": r"^OgreStraw\d$", "stocks": r"^Stocks[1-5]$"},
                     prefer={"straw": {"OgreStraw1": 4, "OgreStraw2": 1, "OgreStraw3": 1, "OgreStraw5": 1},
                             "stocks": {"Stocks3": 1, "Stocks4": 1}, "bones": {"Skull": 1, "ArmBone": 2, "LegBone": 2}},
                     top_up=(),
                     compose=[dict(fam="stocks", slot="wall", at="center", clear=1.0),
                              dict(fam="straw", slot="scatter", per100=4, cluster=(1, 3), wall_gap=1.0),
                              dict(fam="bones", slot="scatter", per100=5, cluster=(1, 2))],
                     fill=[]),
    # the torture room (Wiz07C, 40 tiles: a rack, a body's remains, a chest, a candelabra; Con08d: remains and a chest)
    "torture_chamber": dict(base="storeroom",
                            purpose="the question room: the rack standing free with room round it, the iron maiden and "
                                    "the stocks against the walls, the questioner's desk and chair, a chest of "
                                    "instruments in a corner, bones on the floor",
                            core={"torture": (1, 1), "restraint": (1, 3), "storage": (1, 1), "desk": (1, 1)},
                            optional={"bones": (0.8, 6), "basin": (0.8, 1)},
                            types={"torture": r"^TortureRack[468]$", "restraint": r"^IronMaiden1$|^Stocks[1-5]$",
                                   "storage": r"^Chest[1-4]$", "desk": r"^Desk[12]$", "basin": r"^DunMirFlameBasinLit$"},
                            prefer={"torture": {"TortureRack6": 2, "TortureRack4": 1, "TortureRack8": 1},
                                    "restraint": {"IronMaiden1": 2, "Stocks3": 1, "Stocks4": 1},
                                    "bones": {"Skull": 1, "ArmBone": 2, "LegBone": 2}, "basin": {"DunMirFlameBasinLit": 1}},
                            lift=("Torture|", "DunMir|"),
                            top_up=(),
                            compose=[dict(fam="torture", slot="center"),
                                     dict(fam="restraint", slot="wall", at="center", clear=1.2, n=2),
                                     dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                                     dict(fam="storage", slot="wall", at="corner", clear=1.2),
                                     dict(fam="basin", slot="wall", at="corner", clear=0.8),
                                     dict(fam="bones", slot="scatter", per100=5, cluster=(1, 2))],
                            fill=[dict(fam="torture", slot="center", max=1, min_area=110, fixed=True),
                                  dict(fam="restraint", slot="wall", at="corner", clear=1.0, max=1)]),
    # a shrine round one holy thing (Con10c / Wiz10c, 66-72 tiles: four incense basins, a chest; Con07H's pedestal;
    # Wiz11A's obelisk niches with a book; Con07D: four candelabras, four obelisks, a chest)
    "shrine": dict(base="study", grand=True,
                   purpose="a shrine: the altar across from the door with statues flanking it and candles before it, a "
                           "basin of fire in each front corner, a runner to the altar with a kneeling bench, a tapestry "
                           "or two of one colour, plants",
                   core={"altar": (1, 1), "statue": (2, 4)},
                   # room lab (tuneB): Westwood's shrines (Con07D, Wiz02B, Wiz11A's three, curated) set four obelisks
                   # round the holy thing, candelabras, a chest; no plants, no statues of the town's kind
                   optional={"bench": (0.5, 1), "basin": (1.0, 2), "wall_decor": (1.0, 2), "storage": (0.4, 1)},
                   types={"altar": r"^DunMirAltar\d$", "statue": r"^Obelisk$|^Statue2[a-h]$",
                          "bench": r"^Bench\d$|^LightBench\d$", "basin": r"^DunMirFlameBasinLit$",
                          "storage": r"^Chest\d$"},
                   prefer={"altar": {"DunMirAltar1": 3, "DunMirAltar2": 1}, "basin": {"DunMirFlameBasinLit": 1},
                           "statue": {"Obelisk": 1}},
                   statues_along=True,
                   decor_themes=("blue", "red", "white", "green"),
                   lift=("DunMir|",),
                   top_up=(),
                   compose=[dict(fam="altar", slot="relic_ring", ring="statue", d=1.9, **{"else": ("basin", "none")}),
                            # a room too small for the ring: the altar on the wall across from the door, obelisks by it
                            dict(fam="altar", slot="wall", at="center", clear=2.6, deep=True, door=True),
                            dict(fam="statue", slot="flank", of="altar", gap=0.8),
                            dict(fam="basin", slot="wall", at="corner", clear=0.8, n=2),
                            dict(fam="wall_decor", slot="decor")],
                   fill=[dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1, fixed=True)]),
    "dark_shrine": dict(base="study", grand=True,
                        purpose="the Land of the Dead's shrine: the lich god's statue on the wall across from the door, "
                                "mana obelisks either side, incense basins burning, tapestries and sconces, bones",
                        core={"altar": (1, 1), "statue": (2, 4)},
                        optional={"basin": (1.0, 2), "wall_decor": (1.0, 3), "bones": (1.0, 12)},
                        types={"altar": r"^LOTDLichGodStatue[12]$", "statue": r"^LOTDManaObelisk$",
                               "basin": r"^LOTDIncenseBasinLit$", "wall_decor": r"^LOTDTapestry[12]$"},
                        prefer={"altar": {"LOTDLichGodStatue1": 1, "LOTDLichGodStatue2": 1},
                                "statue": {"LOTDManaObelisk": 1}, "basin": {"LOTDIncenseBasinLit": 1},
                                "wall_decor": {"LOTDTapestry1": 1, "LOTDTapestry2": 1},
                                "bones": {"Skull": 3, "ArmBone": 3, "LegBone": 2}},
                        lights={"LOTDWallSconse1": 2, "LOTDCandleabra1": 1},
                        lift=("LOTD|", "Lich|"),     # its own pieces in any building (a town house had shown none)
                        top_up=(),
                        compose=[dict(fam="altar", slot="wall", at="center", clear=2.6, deep=True, door=True),
                                 dict(fam="statue", slot="flank", of="altar", gap=0.8),
                                 dict(fam="basin", slot="wall", at="corner", clear=0.8, n=2),
                                 dict(fam="bones", slot="scatter", per100=8, cluster=(1, 3)),
                                 dict(fam="wall_decor", slot="decor")],
                        fill=[dict(fam="statue", slot="wall", at="corner", clear=0.8, max=2)]),
    # a gallery (Con07E / War07D, 208-210 tiles: seven paintings, sixteen lanterns, nine plants, an orrery, tapestries,
    # two flame basins, a statue)
    "gallery": dict(base="hall", grand=True,
                    purpose="a gallery: paintings hung along both back walls at even spacing, a bench or two in the middle "
                            "facing them, a pair of statues, one curio (an orrery), plants in the corners, open floor to "
                            "walk the walls",
                    # room lab (tuneB): Westwood's gallery (Con07E, 210 tiles) shows its pieces apart along the walls,
                    # each in its own bay: an orrery, a flame basin on a plinth, crystals among plants, a statue;
                    # paintings and blue tapestries between them; lanterns; not a bench group in the middle
                    core={"wall_decor": (6, 14), "bench": (0, 2)},
                    optional={"statue": (0.9, 2), "plant": (1.0, 4), "lab": (0.9, 1), "basin": (0.8, 2),
                              "bench": (0.5, 1)},
                    types={"bench": r"^Bench[1-4]$|^CushionedBench\d$", "statue": r"^Statue2[aceg]$", "plant": PLANTS,
                           "lab": r"^Orrery2$", "basin": r"^DunMirFlameBasinLit$", "wall_decor": r"^Painting[12]$"},
                    prefer={"wall_decor": {"Painting1": 1, "Painting2": 1}, "basin": {"DunMirFlameBasinLit": 1},
                            "lab": {"Orrery2": 1}},
                    decor_max=10,
                    decor_at="any",           # paintings at the ends of each stretch of wall as well as its middle
                    lift=("DunMir|",), by_walls=("curio", "statues"), statues_along=True,
                    top_up=(),
                    compose=[dict(fam="lab", slot="groups", group="curio", n=1, extra=True, min_area=80),
                             dict(fam="statue", slot="groups", group="statues", n=1, extra=True, min_area=80),
                             dict(fam="basin", slot="wall", at="center", clear=1.0, n=2),
                             dict(fam="plant", slot="wall", at="corner", clear=0, n=4),
                             dict(fam="wall_decor", slot="decor")],
                    fill=[dict(fam="statue", slot="wall", at="center", clear=0.8, max=2, fixed=True, min_area=120),
                          dict(fam="bench", slot="center", max=1, min_area=160, fixed=True)]),
    # a garden hall (Con07B / War07A, 155-177 tiles: 33-35 potted plants and a pair of columns; Wiz01A, 24 tiles: a
    # fountain with lily pads among barren plants)
    "conservatory": dict(base="hall", grand=True,
                         purpose="a garden room: the fountain or the well in the middle with benches facing it, plants "
                                 "massed along the back walls and in clumps on the floor with paths between, a pair of "
                                 "statues, plants in every corner",
                         core={"plant": (6, 40), "bench": (1, 4)},
                         optional={"feature": (1.0, 1), "statue": (0.6, 4)},
                         types={"plant": r"^Plant[1-5]$|^Plant2Flowered$|^PlantFern[1-4]$", "bench": r"^Bench[1-4]$|^LightBench\d$",
                                "feature": r"^Fountain$|^WishingWell$", "statue": r"^Statue2[aceg]$"},
                         prefer={"plant": {"Plant4": 3, "Plant5": 3, "Plant3": 2, "Plant1": 1, "Plant2Flowered": 1,
                                           "PlantFern2": 1}, "feature": {"Fountain": 2, "WishingWell": 1}},
                         top_up=("plant",),
                         compose=[dict(fam="feature", slot="center"),
                                  dict(fam="bench", slot="center", n=2),
                                  dict(fam="plant", slot="wall", at="room_corner", clear=0, n=4),
                                  dict(fam="plant", slot="scatter", per100=10, cluster=(2, 4), wall_gap=0.4),
                                  dict(fam="statue", slot="groups", group="statues", n=1, extra=True, min_area=120)],
                         fill=[dict(fam="statue", slot="wall", at="corner", clear=0.8, max=2, fixed=True, min_area=120),
                               dict(fam="plant", slot="scatter", per100=4, cluster=(2, 3), wall_gap=0.4, max=12),
                               dict(fam="bench", slot="center", max=1, min_area=100)]),
    # a tomb of statues (Con04a, 58 tiles: four monuments, twelve statues, crypt chests, a tombstone; Con04c: columns,
    # monuments, statues): one great tomb, the statues of the dead about it
    "mausoleum": dict(base="crypt", grand=True,
                      purpose="a mausoleum: one great tomb in the middle, statues of the dead in pairs facing it, "
                              "monuments at the back corners, a pair of columns in a big one, a tapestry",
                      core={"tomb": (1, 1), "statue": (2, 6), "monument": (2, 4)},
                      optional={"column": (0.6, 4), "wall_decor": (0.7, 2), "plant": (0.4, 2)},
                      types={"tomb": r"^Crypt(1|3|5|6|7|8|9|12)$", "statue": r"^Statue2[aceg]$",
                             "monument": r"^Monument1$", "storage": r"^CryptChest[1-4]$",
                             "column": r"^Column[5-8]$", "plant": r"^PlantBarren[12]$"},
                      prefer={"monument": {"Monument1": 1}},
                      lift=("Crypt|",),
                      top_up=("plant",),
                      compose=[dict(fam="tomb", slot="center"),
                               dict(fam="statue", slot="groups", group="statues", n=1, extra=True),
                               dict(fam="monument", slot="wall", at="corner", clear=0.8, n=2),
                               dict(fam="wall_decor", slot="decor")],
                      fill=[dict(fam="statue", slot="group", group="statues", max=1, min_area=90, fixed=True),
                            dict(fam="column", slot="racks", kind="columns", gap=4.0, aisle=3.0, min_area=120, max=4,
                                 fixed=True),
                            dict(fam="monument", slot="wall", at="corner", clear=0.8, max=2),
                            dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2)]),
    # a bone room (Con04a, 64-81 tiles: crypt chests, monuments, bones; War04b: 21 bones heaped round a crypt chest)
    "ossuary": dict(base="storeroom",
                    purpose="an ossuary: skulls and long bones heaped along the walls and in the corners, crypt chests in "
                            "the corners, a monument or two, a coffin, a way kept through",
                    core={"bones": (8, 60), "storage": (1, 3)},
                    optional={"monument": (0.8, 2), "tomb": (0.4, 1)},
                    types={"storage": r"^CryptChest[1-4]$", "monument": r"^Monument1$", "tomb": r"^Coffin[1-4]$"},
                    prefer={"bones": {"Skull": 3, "ArmBone": 3, "LegBone": 3}, "monument": {"Monument1": 1}},
                    lift=("Crypt|", "Coffin|"),
                    top_up=(),
                    compose=[dict(fam="storage", slot="wall", at="corner", clear=1.2, n=2),
                             dict(fam="monument", slot="wall", at="center", clear=0.8, n=2),
                             dict(fam="tomb", slot="wall", at="center", clear=1.0),
                             dict(fam="bones", slot="scatter", per100=24, cluster=(4, 7), wall_gap=0.0)],
                    fill=[]),
}

# ---- buildings ---------------------------------------------------------------------------------------
# rooms: (kind, purpose) in order, the first is the largest and takes the entrance;
# scenes: outdoor prop groups that show the building's trade.
BUILDINGS = {
    "inn": dict(purpose="food, drink and a bed for travellers", style="stucco_house", size=(40, 32), shape="rect", min_units=300,
                rooms=[("tavern", "the common room"), ("kitchen", "the inn's kitchen"), ("bedroom", "the innkeeper's room")],
                scenes=["deliveries", "bench_by_door", "sign"], garden=0.0, faces="square"),
    "store": dict(purpose="the village's general store", style="cobble_house", size=(26, 22), min_units=100,
                  rooms=[("shop", "the shop floor"), ("storeroom", "the stock room")],
                  scenes=["goods_display", "sign"], garden=0.0, faces="square"),
    "smithy": dict(purpose="the blacksmith's forge", style="stone_house", size=(24, 20), min_units=90,
                   rooms=[("smithy", "the forge"), ("storeroom", "iron and coal")],
                   scenes=["water_barrel", "woodpile"], garden=0.0, faces="square"),
    "home": dict(purpose="a villager's house", style="log_cabin", size=(20, 18),
                 rooms=[("living_room", "the hearth room"), ("bedroom", "the family's bedroom")],
                 scenes=["woodpile", "water_barrel"], garden=0.7, faces="road"),
    "cottage": dict(purpose="a small one-room house", style="log_cabin", size=(16, 14),
                    rooms=[("dwelling", "bed, hearth and table in one room")],
                    scenes=["woodpile"], garden=0.5, faces="road"),
    "mill": dict(purpose="the miller's house by the pond", style="log_cabin", size=(22, 18), min_units=80,
                 rooms=[("living_room", "the miller's hearth room"), ("granary", "sacks of grain")],
                 scenes=["grain_sacks", "water_barrel"], garden=0.0, faces="road"),
    "grovelord": dict(purpose="the grovelord's large shack in the heart of the north wood", style="log_cabin",
                      size=(36, 30), min_units=200,
                      rooms=[("living_room", "the grovelord's hall, its hearth and table"),
                             ("herbalist", "herb lore: potions, remedies, the cauldron"),
                             ("bedroom", "the grovelord's bed"), ("storeroom", "seeds, roots and stores")],
                      scenes=["woodpile", "water_barrel", "bench_by_door"], garden=1.0, faces="road"),
    "bunkhouse": dict(purpose="where the miners sleep", style="log_cabin", size=(30, 24), min_units=120,
                      rooms=[("barracks", "the miners' bunks"), ("gear_store", "their gear")],
                      scenes=["woodpile", "water_barrel"], garden=0.0, faces="square"),
    "foreman": dict(purpose="the mine foreman's house and office", style="stone_house", size=(30, 24), min_units=140,
                    rooms=[("study", "the foreman's office and ledgers"), ("bedroom", "the foreman's room")],
                    scenes=["sign"], garden=0.0, faces="square"),
    "mess": dict(purpose="the miners' mess hall and camp kitchen", style="log_cabin", size=(34, 28), min_units=160,
                 rooms=[("mess_hall", "the tables where the miners eat"), ("kitchen", "the camp kitchen")],
                 scenes=["deliveries", "bench_by_door"], garden=0.0, faces="square"),
    "ore_shed": dict(purpose="the ore shed where mana carts wait to be hauled", style="log_cabin", size=(22, 18),
                     min_units=70, rooms=[("ore_store", "carts of mana ore")],
                     scenes=["mine_carts"], garden=0.0, faces="square"),
    "woodcutter": dict(purpose="the woodcutter's hut", style="log_cabin", size=(14, 12),
                       rooms=[("dwelling", "the woodcutter's one room")],
                       scenes=["woodpile", "chopping_block"], garden=0.0, faces="road"),
    # large houses for the bigger maps (the user: "we are going to ultimately produce much larger maps and a larger
    # scale than anything in the original game")
    "manor": dict(purpose="a lord's manor: the great hall, the dining hall and its kitchen, the library and the lord's "
                          "study, bedrooms and the stores", style="stone_house", size=(72, 56), min_units=760,
                  rooms=[("great_hall", "the great hall"), ("dining_hall", "the lord's table"), ("kitchen", "the manor kitchen"),
                         ("library", "the library"), ("study", "the lord's study"), ("bedroom", "the lord's chamber"),
                         ("bedroom", "the guest chamber"), ("storeroom", "the stores")],
                  scenes=["deliveries", "water_barrel"], garden=0.0, faces="square"),
    # a town's hall (Ambermere's moot hall): smaller than a lord's manor, for a town of a reeve or a mayor
    "townhall": dict(purpose="the town's hall: the hall where the reeve holds the moot, his study and ledgers, his "
                             "chamber and the town's stores", style="stone_house", size=(46, 34), min_units=320,
                     rooms=[("great_hall", "the moot hall"), ("study", "the reeve's study and the town's ledgers"),
                            ("bedroom", "the reeve's chamber"), ("storeroom", "the town's stores")],
                     scenes=["deliveries", "sign"], garden=0.0, faces="square"),
    "chapel": dict(purpose="the town's chapel: the nave with its altar and pews, and behind it the crypt where an old "
                           "family lies", style="stone_house", size=(40, 30), min_units=220,
                   rooms=[("chapel", "the nave: the altar, the pews facing it"), ("crypt", "the family crypt behind the nave")],
                   scenes=["sign"], garden=0.0, faces="square"),
    # a village's chapel (Harrowby): the town's chapel at a village's size, so its nave stays within the chapel brief's
    # 60-260 tiles (the town chapel's nave came out 288-323 tiles in Harrowby, 4-6% covered: rules/rooms/chapel.md)
    "village_chapel": dict(purpose="a village's chapel: a small nave with its altar and pews, and behind it the crypt "
                                   "of its old families", style="stone_house", size=(34, 26), min_units=180,
                           rooms=[("chapel", "the nave: the altar, the pews facing it"),
                                  ("crypt", "the crypt of the old families behind the nave")],
                           scenes=["sign"], garden=0.0, faces="square"),
    # a lake town's houses (Ambermere): the fisher's house on the shore, the herbwife's hut
    "fisher": dict(purpose="a fisher's house on the shore: the hearth room, and the loft where the nets, oars, salt and "
                           "the day's catch are kept", style="log_cabin", size=(20, 18),
                   rooms=[("living_room", "the fisher's hearth room"), ("storeroom", "nets, oars, salt and the catch")],
                   scenes=["catch", "woodpile"], garden=0.3, faces="road"),
    "herbwife": dict(purpose="a herbwife's hut: her herb room with the cauldron and the shelves of remedies, and her bed",
                     style="log_cabin", size=(20, 16), min_units=70,
                     rooms=[("herbalist", "herbs, the cauldron and remedies"), ("bedroom", "the herbwife's bed")],
                     scenes=["water_barrel"], garden=1.0, faces="road"),
    # a castle's buildings (Greywatch): the keep in Galava's tower stone, the garrison's barracks
    "keep": dict(purpose="a castle's keep: the throne room where its lord holds court, the great hall, the steward's "
                         "study, the lord's chamber and the stores", style="galava_tower", size=(44, 32), min_units=360,
                 rooms=[("throne_room", "the throne room"), ("great_hall", "the great hall"), ("study", "the steward's study"),
                        ("bedroom", "the lord's chamber"), ("storeroom", "the keep's stores")],
                 scenes=["deliveries"], garden=0.0, faces="square"),
    "barracks": dict(purpose="the garrison's barracks: the soldiers' bunks, their mess and the armoury of their gear",
                     style="stone_house", size=(38, 28), min_units=230,
                     rooms=[("barracks", "the soldiers' bunks"), ("mess_hall", "the garrison's mess"),
                            ("gear_store", "racks of arms and armour")],
                     scenes=["water_barrel", "woodpile"], garden=0.0, faces="square"),
    # a wizards' town's buildings (Starwell, in Ix's manner: rules/out/buildings.json stucco_dark_house is Ix's
    # dark-timbered stucco, Wiz01A): the college on the square, the alchemist's shop, the old observatory on its crag
    "college": dict(purpose="a wizards' college: the hall where the archmagister sits in state, the library, the "
                            "laboratory, the archmagister's study and chamber",
                    style="galava_townhouse", size=(56, 42), min_units=420,
                    rooms=[("throne_room", "the Hall of the Star, where the archmagister sits in state"),
                           ("library", "the college library"),
                           ("laboratory", "the college laboratory"), ("study", "the archmagister's study"),
                           ("bedroom", "the archmagister's chamber")],
                    scenes=["sign"], garden=0.0, faces="square"),
    "apothecary": dict(purpose="an alchemist's shop: the shop floor with its counter, and the herb room where the "
                               "potions are brewed", style="stucco_dark_house", size=(28, 22), min_units=110,
                       rooms=[("shop", "the shop floor"), ("herbalist", "the brewing room")],
                       scenes=["goods_display", "sign"], garden=0.0, faces="square"),
    "observatory": dict(purpose="an old observatory of grey stone on a crag: the star-chamber where the sky was "
                                "watched, the workroom, the library of star charts",
                        # stone_house (StoneGray): the blue stone house style was learned from the quest maps only
                        # (G_Castle and its kin); the campaign builds no house of StoneBlue
                        style="stone_house",
                        size=(40, 30), min_units=240,
                        rooms=[("hall", "the star-chamber"), ("laboratory", "the workroom"),
                               ("library", "the star charts")],
                        scenes=[], garden=0.0, faces="road"),
    # the biomes' structures (rules/BIOMES.md, rules/cultures.py): the built parts of Westwood's lava, ice and cave
    # maps in their own building styles, furnished by their culture
    "demon_forge": dict(purpose="a demon forge of black stone above the lava: the forge, the hall where its arms are "
                                "racked, the store of iron and coal", style="dunmir_hall", furnish="dunmir",
                        size=(40, 30), min_units=220,
                        rooms=[("smithy", "the demon forge"), ("hall", "the hall of arms"), ("storeroom", "iron and coal")],
                        scenes=[], garden=0.0, faces="road"),
    "ice_temple": dict(purpose="a dark temple sunk in the ice: the lich god's chapel, the crypt of the frozen dead and the "
                               "priests' library", style="lotd_ornate", furnish="lotd", size=(52, 40), min_units=380,
                       rooms=[("dark_chapel", "the lich god's chapel"), ("dark_crypt", "the crypt of the frozen dead"),
                              ("library", "the priests' library")],
                       scenes=[], garden=0.0, faces="road"),
    "barrow": dict(purpose="a barrow-hall of the old kings in the Land of the Dead's manner: the hall of the dead god "
                           "where the kings' seal lay on the altar, and the crypt of their tombs", style="lotd_ornate",
                   furnish="lotd", size=(44, 34), min_units=260,
                   rooms=[("dark_chapel", "the hall of the dead kings, the old god's statue over the altar"),
                          ("dark_crypt", "the tombs of the kings")],
                   scenes=[], garden=0.0, faces="road"),
    "ogre_keep": dict(purpose="an old keep of dungeon stone the ogres took over: their feasting hall, their straw beds and "
                              "their hoard", style="dungeon_block", furnish="ogre", size=(38, 30), min_units=240,
                      rooms=[("ogre_hall", "the ogres' feasting hall"), ("ogre_den", "their straw beds"),
                             ("ogre_hoard", "their hoard")],
                      scenes=[], garden=0.0, faces="road"),
}

# The roles added with the room types for variety (kit/roomtypes.py, rules/rooms/README.md): a town's gaol, a castle's
# gatehouse, a healer's house, a wheelwright's workshop, a family's mausoleum, a wayside shrine.
BUILDINGS.update({
    "gaol": dict(purpose="the town's gaol: the gaoler's guardroom and the cells behind it", style="stone_house",
                 size=(30, 22), min_units=140,
                 rooms=[("guardroom", "the gaoler's room"), ("cell", "a cell"), ("cell", "a cell")],
                 scenes=["water_barrel"], garden=0.0, faces="road"),
    "gatehouse": dict(purpose="a castle's gatehouse: the watch room, the winch that works the gate, the gate's arms",
                      style="stone_house", size=(30, 24), min_units=150,
                      rooms=[("guardroom", "the gate's watch room"), ("winch_room", "the gate's winch"),
                             ("gear_store", "the gate's arms")],
                      scenes=["water_barrel"], garden=0.0, faces="square"),
    "healer": dict(purpose="a healer's house: the sick room with its cots, the healer's remedies, the healer's bed",
                   style="stucco_house", size=(32, 24), min_units=160,
                   rooms=[("infirmary", "the sick room"), ("herbalist", "the healer's remedies"),
                          ("bedroom", "the healer's bed")],
                   scenes=["water_barrel", "sign"], garden=0.6, faces="road"),
    "wheelwright": dict(purpose="a wheelwright's workshop and its store of timber and iron", style="log_cabin",
                        size=(24, 20), min_units=90,
                        rooms=[("workshop", "the workshop"), ("storeroom", "timber and iron")],
                        scenes=["woodpile", "chopping_block"], garden=0.0, faces="road"),
    "mausoleum": dict(purpose="an old family's mausoleum: the great tomb, and below it the bones of the older dead",
                      style="stone_house", size=(28, 22), min_units=110,
                      rooms=[("mausoleum", "the family's tomb"), ("ossuary", "the bones of the older dead")],
                      scenes=[], garden=0.0, faces="road"),
    "shrine": dict(purpose="a wayside shrine: one small holy room", style="stone_house", size=(18, 16), min_units=50,
                   rooms=[("shrine", "the shrine")], scenes=[], garden=0.3, faces="road"),
})

# Rooms a role may add to its program (BuildingIdentity.extra), each with its purpose: the program above stays each role's
# default, so the maps built so far keep their buildings (StoryMap.place_buildings appends the extras a design asks for).
ROLE_OPTIONS = {
    "inn": [("cellar", "the inn's cellar of ale and wine")],
    "manor": [("solar", "the lord's solar"), ("gallery", "the long gallery"), ("conservatory", "the garden hall"),
              ("cellar", "the wine cellar"), ("treasury", "the strongroom"), ("shrine", "the family's shrine")],
    "townhall": [("treasury", "the town's treasury"), ("guardroom", "the watch room"), ("cell", "the lock-up"),
                 ("cellar", "the cellar")],
    "keep": [("solar", "the lord's solar"), ("guardroom", "the guard room"), ("treasury", "the strongroom"),
             ("cell", "a cell"), ("torture_chamber", "the question room"), ("cellar", "the buttery"),
             ("shrine", "the keep's shrine"), ("powder_store", "the powder store"), ("winch_room", "the winch room")],
    "barracks": [("guardroom", "the guard room"), ("cell", "the lock-up"), ("powder_store", "the powder store"),
                 ("infirmary", "the infirmary")],
    "chapel": [("ossuary", "the bone room"), ("shrine", "the side shrine"), ("mausoleum", "the founder's tomb")],
    "village_chapel": [("ossuary", "the bone room"), ("shrine", "the side shrine")],
    "college": [("observatory", "the observatory"), ("gallery", "the gallery of the archmagisters"),
                ("conservatory", "the garden hall"), ("shrine", "the shrine")],
    "observatory": [("observatory", "the telescope room")],
    "apothecary": [("infirmary", "the sick room")],
    "smithy": [("workshop", "the workshop")],
    "mill": [("winch_room", "the mill's gear room")],
    "ore_shed": [("powder_store", "the blasting powder")],
    "foreman": [("treasury", "the strongroom of the mine's pay")],
    "grovelord": [("shrine", "the grove's shrine")],
    "demon_forge": [("winch_room", "the forge's gear room"), ("powder_store", "the powder store")],
    "ice_temple": [("dark_shrine", "the lich god's shrine"), ("ossuary", "the bones of the frozen dead")],
    "barrow": [("dark_shrine", "the old god's shrine"), ("ossuary", "the bone room")],
    "ogre_keep": [("ogre_pen", "the captives' pen")],
    "gaol": [("torture_chamber", "the question room"), ("cell", "another cell")],
    "gatehouse": [("cell", "the lock-up"), ("powder_store", "the powder store")],
    "healer": [("shrine", "the healer's shrine")],
    "wheelwright": [("winch_room", "the gear room")],
    "mausoleum": [("shrine", "the mourners' shrine")],
}
for _r, _opts in ROLE_OPTIONS.items(): BUILDINGS[_r]["options"] = _opts


def role_program(role, extra=()):
    """[(kind, purpose)] of a role: its default rooms, then each of `extra` (kinds from its options) in turn."""
    r = BUILDINGS[role]
    opts = dict(r.get("options", ()))
    bad = [k for k in extra if k not in opts]
    if bad: raise ValueError(f"{role} takes no {', '.join(bad)} (its options: {', '.join(opts) or 'none'})")
    return list(r["rooms"]) + [(k, opts[k]) for k in extra]

# ---- outdoor scenes ------------------------------------------------------------------------------------
# where: "door_side" (beside the entrance, not in front of it), "side_wall" (an outside wall away from
# the entrance), "front" (in front of the entrance, clear of the doorway).
SCENES = {
    "deliveries": dict(reason="barrels and crates delivered to the kitchen", where="side_wall",
                       items=[("Barrel", 2), ("Barrel2", 1), ("DarkCrate1", 1), ("DarkCrate2", 1)], pieces=(3, 5)),
    "goods_display": dict(reason="the trader shows wares by the door", where="door_side",
                          items=[("TraderAppleCrate", 2), ("Crate1", 1), ("Crate2", 1), ("Barrel2", 1)], pieces=(2, 4)),
    "water_barrel": dict(reason="water for the household or to quench iron", where="door_side",
                         items=[("WaterBarrel", 1)], pieces=(1, 1)),
    "woodpile": dict(reason="firewood stacked against the wall for the hearth", where="side_wall",
                     items=[("ForestLog01", 1), ("ForestLog02", 1), ("ForestLog03", 1), ("ForestLog04", 1)], pieces=(2, 4)),
    "chopping_block": dict(reason="where the woodcutter splits logs", where="front",
                           items=[("Stump1", 1), ("Stump2", 1)], pieces=(1, 1)),
    "grain_sacks": dict(reason="the miller's sacks waiting by the door", where="door_side",
                        items=[("SackChestLarge1", 1), ("SackChestLarge2", 1), ("SackChestMedium1", 1), ("SackChestMedium2", 1)],
                        pieces=(2, 4)),
    "mine_carts": dict(reason="ore carts waiting by the shed to be loaded", where="door_side",
                       items=[("MineOreCart1", 1), ("MineOreCart2", 1), ("MineOreCartWheel", 1)], pieces=(1, 2)),
    "bench_by_door": dict(reason="a seat outside the inn", where="door_side", items=[("Bench4", 1)], pieces=(1, 1)),
    "catch": dict(reason="the day's catch in barrels and crates by the fisher's door, a water barrel to wash it",
                  where="door_side", items=[("Barrel", 2), ("Barrel2", 1), ("Crate1", 1), ("WaterBarrel", 1)],
                  pieces=(2, 4)),
    "sign": dict(reason="the business shows its sign", where="door_side", items=[("Sign1", 1), ("Sign2", 1)], pieces=(1, 1)),
}


# ---- map identity --------------------------------------------------------------------------------------
@dataclass
class AreaIdentity:
    name: str
    purpose: str
    landmark: Optional[str] = None            # e.g. "Well", "ObeliskPrimitive"


@dataclass
class BuildingIdentity:
    role: str                                 # key of BUILDINGS
    area: str                                 # area it stands in
    name: str = ""                            # e.g. "The Mossy Tankard"
    occupant: str = ""                        # who lives or works there
    style: str = ""                           # a building style in place of the role's (stone houses in a volcanic town)
    extra: Tuple[str, ...] = ()               # rooms from the role's options added to its program (ROLE_OPTIONS)


# The Westwood room kind each generated kind is measured against (validate/baseline.json room_kinds).
WESTWOOD_KIND = {"herbalist": "laboratory", "mess_hall": "dining_hall", "ore_store": "storeroom", "study": "library",
                 "dwelling": "living_room", "gear_store": "storeroom", "ogre_den": "barracks", "ogre_hall": "dining_hall",
                 "ogre_hoard": "storeroom", "granary": "storeroom", "dark_chapel": "chapel", "dark_crypt": "crypt", "great_hall": "hall"}
# How much of a room's floor its furniture covers: (target, limit). The furnisher fills toward the target and never
# past the limit, which the checker holds generated rooms to (TreePlace room reviews: rooms furnished to Westwood's
# typical counts read as empty, and a store room holds more than any other room). Coverage grows with the room, so
# rooms bigger than Westwood's get more. Westwood's house rooms: p50 0.10-0.14, p75 0.15-0.19; storerooms p75 0.23,
# barracks 0.25.
# Each kind's (target, limit) comes from its room type (kit/roomtypes.py cover, rules/rooms/<type>.md): a throne room
# or a chapel is open by nature, a storeroom full (Starwell playtest, 2026-10-05: "There is really no one-size-fits-all
# approach for room design").
ROOM_COVER = {}
ROOM_COVER_DEFAULT = (0.16, 0.30)
# the room types set each kind's coverage and its repeat caps (ROOMS[kind]["repeat"])
from kit.roomtypes import apply as _apply_room_types
_apply_room_types(ROOMS, ROOM_COVER)
# Buildings are larger than Westwood's (the user, during the TreePlace v0.3 review: "bias towards bigger rooms and
# structures than westwood"): each role's size and floor below are scaled by this much in each direction.
BUILDING_SCALE = 1.25


def role_size(role):
    """A building role's size (uv units, even) and least floor, at the house scale (BUILDING_SCALE)."""
    w, h = role["size"]
    return (2 * round(w * BUILDING_SCALE / 2), 2 * round(h * BUILDING_SCALE / 2)), int(role.get("min_units", 0) * BUILDING_SCALE ** 2)


def rooms_sidecar(placed, path, yards=()):
    """Writes <map>.rooms.json next to a built map for review/rooms.py: every room numbered in building order,
    with its building, kind, purpose (from the building's room program), floor tiles and box (grid cells).
    placed: [(BuildingIdentity, Building)] as the design placed them. yards: kit/yards.py Yards, recorded after the
    rooms with yard=True (the checker holds them to no indoor room's rules)."""
    import json
    out = []
    for bid, b in placed:
        program = role_program(bid.role, getattr(bid, "extra", ())) if bid.role in BUILDINGS else []
        for r in b.rooms:
            purpose = next((p for kind, p in program if kind == r.kind), "")
            program = [kp for kp in program if kp != (r.kind, purpose)]
            xs = [x for x, _ in r.tiles]; ys = [y for _, y in r.tiles]
            out.append(dict(number=len(out) + 1, building=bid.name or bid.role, kind=r.kind, purpose=purpose,
                            tiles=len(r.tiles), box=[min(xs) - 1, min(ys) - 1, max(xs) + 3, max(ys) + 3],
                            floor=sorted([x, y] for x, y in r.tiles)))
    for y in yards:
        from kit.yards import YARDS
        tiles = sorted([i + j, i - j] for i, j in y.plot)
        xs = [x for x, _ in tiles]; ys = [y_ for _, y_ in tiles]
        out.append(dict(number=len(out) + 1, building="", kind=y.kind, purpose=YARDS[y.kind].get("purpose", ""),
                        tiles=len(tiles), box=[min(xs) - 1, min(ys) - 1, max(xs) + 3, max(ys) + 3], floor=tiles,
                        yard=True))
    with open(path, "w", encoding="utf-8") as f: json.dump(out, f, indent=1)
    return out


@dataclass
class MapIdentity:
    name: str
    theme: str                                # one sentence: what this place is
    environment: str                          # rules/environments.py type (town, forest, ...)
    mood: str = ""
    areas: List[AreaIdentity] = field(default_factory=list)
    buildings: List[BuildingIdentity] = field(default_factory=list)

    def describe(self):
        """Readable concept, for the map's description and the review record."""
        lines = [f"{self.name}: {self.theme}", f"Environment: {self.environment}. Mood: {self.mood}"]
        for a in self.areas:
            lines.append(f"- {a.name}: {a.purpose}" + (f" (landmark: {a.landmark})" if a.landmark else ""))
        for b in self.buildings:
            r = BUILDINGS[b.role]
            rooms = ", ".join(f"{k} ({p})" for k, p in role_program(b.role, b.extra))
            lines.append(f"- {b.name or b.role} in the {b.area}: {r['purpose']}"
                         + (f", home of {b.occupant}" if b.occupant else "") + f". Rooms: {rooms}.")
        return "\n".join(lines)
