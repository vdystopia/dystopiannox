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
                      # the room lab (2026-10-05): Westwood's two herbalists (Con07D, Con09a) hold a desk with its chair,
                      # potion shelves (a pair), a few bookcases, glowing jars, a square table with chairs, a crate or an
                      # apple crate; no plants, no hangings, no sacks along the walls; coverage 0.07-0.12
                      core={"shelves": (3, 10), "stove": (1, 1), "table": (1, 1), "chair": (1, 3), "desk": (1, 1)},
                      optional={"lab": (0.8, 2), "storage": (0.8, 2)},
                      types={"lab": r"^FairyJar$", "shelves": r"^PotionShelves\d$|^Bookcase\d(HalfFull)?$", "stove": r"^Cauldron",
                             "storage": r"^DarkCrate[12]$|^TraderAppleCrate$|^Barrel$", "table": r"^SquareTable[12]$|^Table[1-4]$"},
                      prefer={"shelves": {"PotionShelves1": 1, "PotionShelves2": 1, "PotionShelves3": 1, "PotionShelves4": 1,
                                          "Bookcase1": 1, "Bookcase2": 1, "Bookcase3": 1, "Bookcase4": 1},
                              "stove": {"CauldronAnimated": 1}, "table": {"SquareTable1": 1, "Table4": 1}},
                      top_up=(), decor_max=0, lined_goal=0.2,
                      # potion shelves stand in a pair, never a wall of them (2026-10-05 Starwell playtest; kit/furnish.py
                      # PAIRED_PIECES): the pair first, then the desk among a few books
                      compose=[dict(fam="shelves", slot="line", n=2, only=r"^PotionShelves"),
                               dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                               dict(fam="shelves", slot="line", near="desk", n=2, only=r"^Bookcase"),
                               dict(fam="stove", slot="wall", at="corner", clear=1.6),
                               dict(fam="table", slot="center", seats=True),
                               dict(fam="lab", slot="wall", at="corner", clear=0.6, n=1)],
                      # (Westwood's herbalists stand their pieces off the walls: wall_gap)
                      wall_gap={"desk": 0.3, "stove": 0.3, "storage": 0.3, "lab": 0.3},
                      fill=[dict(fam="storage", slot="wall", at="corner", clear=0.6, max=3),
                            dict(fam="lab", slot="wall", at="any", clear=0.6, max=2),
                            dict(fam="stove", slot="wall", at="any", clear=1.2, max=1, missing=True),
                            dict(fam="table", slot="group", group="sitting", max=1, min_area=170),
                            dict(fam="shelves", slot="line", other=True, n=2, max=4, only=r"^Bookcase", min_area=100)]),
    "ore_store": dict(purpose="mana ore and the miners' gear: loaded carts with room to move them, racks of gear in rows "
                              "down the middle, trader shelves of tools and helmets along a back wall, crates and barrels of "
                              "tools along the front walls",
                      base="storeroom",
                      core={"cart": (1, 2), "storage": (2, 16)},
                      optional={"shop_rack": (0.5, 2)},
                      types={"storage": SUPPLY, "shop_rack": r"^TraderShelves[12]$"},
                      prefer={"cart": {"MineManaCart1": 2, "MineManaCart2": 2, "MineOreCart1": 1, "MineOreCart2": 1},
                              "storage": {"DarkCrate1": 2, "DarkCrate2": 2, "BarrelWithTools1": 1, "Barrel": 1},
                              "shop_rack": {"TraderShelves1": 1, "TraderShelves2": 1}},
                      # the carts are the town-furnished ore shed's own pieces (the "town" style had excluded every Mine
                      # piece, so the lab's ore stores never had their carts: the profile's focal missed in 3 of 3);
                      # the store heaped as a storeroom's (store_heaps), a shelf of tools or two at most
                      lift=("Mine|",), lights_per100=0,
                      store=dict(lead={"crates": 2, "tools": 1, "barrels": 1}, second={"tools": 2, "barrels": 2},
                                 accent={"large": 1, "piled": 1}),
                      top_up=(),
                      compose=[dict(fam="cart", slot="groups", group="carts", n=1),
                               dict(fam="cart", slot="wall", at="any", clear=1.2),
                               dict(fam="storage", slot="heaps", n=4),
                               dict(fam="shop_rack", slot="wall", at="center", clear=1.0, n=1)],
                      fill=[dict(fam="storage", slot="heaps")]),
    "tavern": dict(purpose="the public drinking room: a long bar with kegs behind it, round tables with stools, a long "
                           "table with benches, a table laid with food, the hearth with a rug before it and shelves of "
                           "tankards beside it, kegs heaped by the walls, trophies on the walls, benches along the front "
                           "walls, open floor between",
                   # 2026-10-05 playtest: 24 tables and 76 chairs in a 342-tile common room were too many; Westwood's
                   # taverns hold a table per 27-42 tiles, so a table per 28 tiles, at most 12, in three kinds of set
                   core={"counter_bar": (1, 1), "table": (3, 12), "chair": (6, 34), "storage": (3, 10), "fireplace": (1, 1)},
                   per_tiles={"table": 28},
                   optional={"bench": (0.9, 4), "wall_decor": (1.0, 8), "rug": (1.0, 2), "shelves": (0.9, 10),
                             "plant": (0.8, 2)},
                   types={"storage": r"(?<!Powder)Barrel$|(?<!Powder)Barrel\d|PiledBarrels|LargeBarrel",
                          "table": r"RoundTable|^Table\d$|SquareTable", "chair": r"Stool|Chair",
                          "bench": r"^LightBench\d$|^CushionedBench\d$|^Bench\d$",
                          # shelves of tankards and crockery, never a bookcase (rules/rooms/tavern.md)
                          "shelves": r"^LogShelvesFull\d$", "plant": PLANTS},
                   # Westwood's room statistics count hearths as lights: the tavern names its own (it had stood without)
                   prefer={"fireplace": {"Fireplace1": 1, "Fireplace2": 1, "Fireplace3": 2, "Fireplace4": 1}},
                   compose=[dict(fam="counter_bar", slot="bar"),
                            dict(fam="fireplace", slot="wall", at="center", clear=2.4, rug=True),
                            dict(fam="shelves", slot="line", near="fireplace", decor=2),
                            dict(fam="fireplace", slot="groups", group="hearth", n=1, min_area=500, extra=True),
                            dict(fam="table", slot="groups", group="longtable", n=1),
                            dict(fam="table", slot="groups", group="feast", n=1),
                            dict(fam="table", slot="groups", group="round", n=4),
                            # one dining set composed, a second only by the fill in a big room (Harrowby's 324-tile common
                            # room seated 19 of one chair at three: rules/rooms/tavern.md, seats counted)
                            dict(fam="table", slot="groups", group="dining", n=1),
                            dict(fam="wall_decor", slot="decor")],
                   fill=[dict(fam="table", slot="group", group="longtable", max=1, min_area=300),
                         dict(fam="shelves", slot="line", other=True, decor=2, max=8, min_area=300),
                         dict(fam="fireplace", slot="group", group="hearth", max=1, min_area=680, fixed=True),
                         # kegs heaped by the walls, never a wall lined with them (per_wall)
                         dict(fam="storage", slot="stock", coverage=0.65, kinds=("barrels",), pad=1.2, max=3,
                              per_wall=0.4),
                         dict(fam="bench", slot="wall", max=4),
                         dict(fam="storage", slot="group", group="kegs", max=1, min_area=400),
                         dict(fam="table", slot="group", group="feast", max=1, min_area=400),
                         dict(fam="table", slot="group", group="round", max=2, min_area=60),
                         dict(fam="table", slot="group", group="dining", max=1, min_area=200),
                         dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2)]),
    "mess_hall": dict(purpose="where a crew eats together: long tables in rows with a bench along each side, the hearth "
                              "on a back wall flanked end to end by shelves of crockery, benches along the front walls, "
                              "trophies and hangings on the back walls",
                      base="dining_hall",
                      core={"fireplace": (1, 1), "table": (2, 8), "bench": (4, 20), "shelves": (2, 12)},
                      per_tiles={"table": 14},
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
                      fill=[dict(fam="table", slot="group", group="longtable", max=1, fixed=True),
                            dict(fam="bench", slot="wall", at="center", clear=0, max=3),
                            dict(fam="shelves", slot="line", max=8)]),
    "dining_hall": dict(purpose="a household's dining hall: long tables seated along both sides, the hearth on a back wall "
                                "flanked by shelves of crockery, hangings above, a table of food, plants in the corners",
                        core={"table": (1, 6), "chair": (4, 36), "fireplace": (1, 1)},
                        per_tiles={"table": 16},
                        optional={"rug": (0.6, 1), "wall_decor": (1.0, 8), "shelves": (1.0, 12), "bench": (0.6, 2),
                                  "plant": (0.8, 3), "statue": (0.5, 2), "storage": (0.5, 2)},
                        types={"table": r"^Table[1-4]$|^OvalTable[12]$|^RoundTableWithFood$|^RoundTable[123]$",
                               "shelves": r"^LogShelvesFull\d$|^Bookcase\d(HalfFull)?$", "statue": r"^Statue2[a-h]$",
                               "storage": CHEST, "plant": PLANTS, "chair": r"Chair"},
                        # Westwood's room statistics count hearths as lights, so a recipe names its own
                        prefer={"fireplace": {"Fireplace1": 1, "Fireplace2": 1, "Fireplace3": 2, "Fireplace4": 1}},
                        compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4),
                                 dict(fam="shelves", slot="line", near="fireplace", decor=2),
                                 dict(fam="table", slot="table_rows", seat="chair"),
                                 dict(fam="carpet", slot="carpet", where="under", chance=0.5),
                                 dict(fam="wall_decor", slot="decor")],
                        fill=[dict(fam="table", slot="group", group="dining", max=2, min_area=90), dict(fam="table", slot="group", group="feast", max=1, min_area=90),
                              dict(fam="statue", slot="group", group="statues", max=1, min_area=260),
                              dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                              dict(fam="bench", slot="wall", max=2),
                              dict(fam="shelves", slot="line", other=True, decor=2, max=8, min_area=140)]),
    "shop": dict(purpose="a trader's shop: the counter set out before a back wall with the keeper's space behind it, "
                         "trader's shelves of goods lining the back walls, racks of arms and armour in rows down the "
                         "middle, crates of stock along the front walls",
                 # the room lab (2026-10-05): each of Westwood's 16 campaign shops keeps one trade: an apothecary's
                 # (potion shelves, a glowing jar: Con02a, War03b, War07A), an armourer's (pole arms, armour stands,
                 # trader's shelves, swords and shields hung: Con06a, War01A, War07A) or a general store (steel crates
                 # and barrels by the counter: Con03A, Con03B); 5-16 types (median 7), no plants. The old recipe mixed
                 # crates, barrels, sacks, racks, potion shelves and plants in every shop (AUC 0.91)
                 core={"counter_shop": (1, 1), "shop_rack": (0, 24)},
                 optional={"storage": (0.9, 8), "shelves": (0.9, 8), "chair": (0.5, 1), "lab": (0.8, 3), "stove": (1.0, 1)},
                 types={"storage": r"Crate|(?<!Powder)Barrel$|(?<!Powder)Barrel\d|BarrelSteel\d|Sack|Chest\d",
                        "shop_rack": RACKS + r"|^TraderHangingSwords\d$|^TraderShieldWallHanging\d$|^TraderHangingCrossbow\d$",
                        "shelves": r"^PotionShelves\d$|^Bookcase\d(HalfFull)?$", "lab": r"^FairyJar$",
                        "stove": r"^CauldronAnimated$"},
                 prefer={"counter_shop": {f"TraderDesk{k}": 1 for k in range(1, 7)}},
                 trades={"armourer": dict(only={"storage": r"Steel|^Barrel$|^Crate[12]$"}, skip=("shelves", "lab", "stove")),
                         "apothecary": dict(only={"shop_rack": r"^TraderShelves\d$", "storage": r"^Barrel$|^Crate[12]$"},
                                            skip=("slot:racks", "slot:heaps")),
                         "general": dict(only={"storage": r"Steel|^Barrel$",
                                               "shop_rack": r"^TraderShelves\d$"}, skip=("shelves", "lab", "stove", "slot:racks"))},
                 # the independent judge (r4): racks in ruler-straight rows dead centre ("three and three" taken too
                 # literally: the user meant variety), crates and barrels alternating one by one down the front walls,
                 # three hanging themes on a wall. Racks now stand against the walls, a short row only in a big shop;
                 # the stock heaps as a store's (store_heaps); no hangings but the trade's own
                 store=dict(lead={"steel": 3, "barrels": 1}, second={"steel": 1, "crates": 1, "barrels": 1}, second_p=0.6,
                            accent={"tools": 1}, accent_p=0.3),
                 top_up=(), decor_max=0, back_only=("shop_rack",),
                 compose=[dict(fam="counter_shop", slot="counter", depth=2.2, clear=1.8),
                          dict(fam="shop_rack", slot="line", n=3, only=r"^TraderShelves"),
                          dict(fam="shelves", slot="line", other=True, n=4),
                          dict(fam="shop_rack", slot="wall", at="corner", clear=1.0,
                               only=r"^Trader(PoleArm|ArmorRack|BowRack|ClothesRack|QuiverRack)", n=3),
                          dict(fam="lab", slot="wall", at="corner", clear=0.6, n=1),
                          # an apothecary's brewing cauldron (Westwood's Con02a, Con09b's stove)
                          dict(fam="stove", slot="wall", at="corner", clear=1.4),
                          dict(fam="storage", slot="heaps", n=3)],
                 fill=[dict(fam="shop_rack", slot="wall", at="center", clear=0, only=r"^TraderHanging|^TraderShield",
                            max=2),
                       dict(fam="shop_rack", slot="racks", kind="gear", max=3, min_area=260),
                       dict(fam="shop_rack", slot="wall", at="any", clear=1.0,
                            only=r"^Trader(PoleArm|ArmorRack|BowRack|ClothesRack|QuiverRack)", max=3),
                       dict(fam="shelves", slot="line", other=True, n=3, max=6, only=r"^Bookcase"),
                       dict(fam="lab", slot="wall", at="center", clear=0.6, max=2),
                       dict(fam="storage", slot="heaps", max=2)]),
    # the room lab (2026-10-05): Westwood's 22 campaign storerooms hold 1-5 types (median 3), barrels the commonest, heaped
    # against two walls with the rest of the floor bare, crates side by side or stacked free; no shelves, no racks (the
    # user: "armor and weapon racks in storerooms are just a little bit too dense and numerous"; "Repeating the same item
    # along the entire length of a wall is not realistic ... try a cluster of sacks (three different sizes), and then a
    # barrel, and then something else"). The old recipe (shelves, a row of hunting racks, every wall stocked with a
    # cluster of every kind) gave 8-15 types round all four walls: AUC 0.96 against Westwood's. store: the weights of the
    # room's lead kind, its second kind and its odd piece (kit/furnish.py store_heaps)
    "storeroom": dict(purpose="stores kept in good order: barrels heaped in the corner furthest from the door, crates side "
                              "by side along the same walls or stacked in the middle, the odd cask; an aisle to walk",
                      core={"storage": (4, 24)},
                      optional={},
                      types={"storage": SUPPLY},
                      store=dict(lead={"barrels": 6, "crates": 2, "sacks": 1}, second={"crates": 3, "barrels": 2, "sacks": 2},
                                 accent={"piled": 2, "large": 2, "water": 1, "tools": 1, "apples": 1}),
                      top_up=(), lights_per100=0,
                      compose=[dict(fam="storage", slot="heaps", n=4)],
                      fill=[dict(fam="storage", slot="heaps")]),
    # a mill's or a farm's grain store (Harrowby): a storeroom of sacks, never racks of arms (the mill's first
    # storeroom held a row of axe racks down its middle: rules/rooms/storeroom.md)
    "granary": dict(base="storeroom", purpose="grain kept dry: sacks heaped in the corners in their three sizes, barrels and "
                            "crates along the same walls, an aisle to walk",
                    core={"storage": (5, 28)}, optional={},
                    types={"storage": SUPPLY},
                    store=dict(lead={"sacks": 1}, second={"barrels": 2, "crates": 2}, second_p=0.9,
                               accent={"large": 1, "piled": 1}),
                    top_up=(), lights_per100=0,
                    compose=[dict(fam="storage", slot="heaps", n=4)],
                    fill=[dict(fam="storage", slot="heaps")]),
    # the room lab (2026-10-05): Westwood's 16 campaign armouries hold 3-13 types (median 6), 0-0.73 supplies per 10 tiles
    # (median 0.3), no shelves, a rack or a few against the walls rather than rows (most of one kind: 1-3), swords,
    # crossbows and shields hung on the walls (Con03A, Con06a, Con06b, Wiz06c), a Dun Mir chest; the old recipe's log
    # shelves, rows of racks and walls stocked with sacks and tool barrels gave every one away (AUC 1.0)
    "gear_store": dict(purpose="a crew's arms in good order: pole arms, armour stands and bow racks standing against the "
                               "walls, a short row of one kind in a big one, swords and shields hung on the back walls, a "
                               "chest, a barrel or two",
                       base="storeroom",
                       core={"shop_rack": (2, 12), "storage": (1, 6)},
                       # the guards' table with its chairs (6 of Westwood's 16: Con03A, Con05A, Con06a, Con06b, War03a/b;
                       # after the curation those are guardrooms, but the lab compares a 4-room type with its martial pool,
                       # and the pool holds them: without the table the AUC rose from 0.87 to 0.99)
                       optional={"table": (0.6, 1), "chair": (0.6, 4)},
                       types={"storage": SUPPLY + r"|^Chest[1-4]$", "table": r"^Table[1-4]$|^SquareTable[12]$|^RoundTable[12]$", "shop_rack": RACKS + r"|^TraderHangingSwords\d$|"
                              r"^TraderShieldWallHanging\d$|^TraderHangingCrossbow\d$|^TraderCrossedWeapons\d$"},
                       store=dict(lead={"barrels": 3, "crates": 1}, second={}, second_p=0.0, accent={"water": 1, "tools": 1},
                                  accent_p=0.4),
                       # Westwood's armouries show their racks on the back walls (the focal piece on NE or NW in all 16)
                       top_up=(), lights_per100=2.5, back_only=("shop_rack",),
                       compose=[dict(fam="shop_rack", slot="wall", at="corner", clear=1.0,
                                     only=r"^Trader(PoleArm|ArmorRack|BowRack|ClothesRack|QuiverRack)", n=2),
                                dict(fam="shop_rack", slot="wall", at="center", clear=0,
                                     only=r"^TraderHanging|^TraderShield|^TraderCrossed|^TraderHelmShelf", n=1),
                                dict(fam="storage", slot="wall", at="corner", clear=1.2, only=r"^Chest", n=1),
                                dict(fam="table", slot="center", seats=True),
                                dict(fam="storage", slot="heaps", n=1)],
                       fill=[dict(fam="shop_rack", slot="racks", kind="gear", max=3, min_area=300),
                             dict(fam="shop_rack", slot="wall", at="corner", clear=1.0,
                                  only=r"^Trader(PoleArm|ArmorRack|BowRack|ClothesRack|QuiverRack)", max=1, fixed=True),
                             dict(fam="shop_rack", slot="wall", at="center", clear=0,
                                  only=r"^TraderHanging|^TraderShield|^TraderCrossed", max=2)]),
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
                   # the room lab (2026-10-05): Westwood's one curated smithy (Con06b, 47 tiles) is the forge's
                   # bellows and anvil, water barrels and barrels in a knot, a dark crate, two stools: coverage 0.06.
                   # The racks stand against the walls (the independent judge of the shops: rows of racks dead centre
                   # read as generated); the stores heap as a store's (store_heaps)
                   store=dict(lead={"water": 2, "barrels": 1}, second={"crates": 1, "tools": 1}, second_p=0.9,
                              accent={"barrels": 1}, accent_p=0.4),
                   top_up=(), back_only=("shop_rack",),
                   compose=[dict(fam="forge", slot="wall", at="center", clear=2.4),
                            dict(fam="bellows", slot="wall", at="corner", beside="forge", clear=0),
                            dict(fam="anvil", slot="before", of="forge", gap=2.4),
                            dict(fam="counter_shop", slot="counter", depth=2.2, clear=1.8),
                            dict(fam="shop_rack", slot="wall", at="corner", clear=1.0, n=2),
                            dict(fam="storage", slot="heaps", n=3)],
                   fill=[dict(fam="shop_rack", slot="wall", at="any", clear=1.0, max=2),
                         dict(fam="table", slot="group", group="worktable", max=1, min_area=200),
                         dict(fam="storage", slot="heaps", max=2)]),
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
                    # the room lab (2026-10-05): Westwood's 7 campaign libraries keep the middle bare (0-0.03 covered
                    # more than 2.5 units from a wall), hold no plants and no curios, line their back walls 0.04-0.29
                    # and warm themselves at a hearth (3 of 7: Con02a's two, War07A, Wiz01A): bookcases along a wall or
                    # two, a round or an oval table with its chairs, a desk. Our stacks of bookcases down the middle,
                    # plants, telescopes and statues gave every one away (AUC 0.99). The user wants a lined wall lined
                    # end to end (HB-4), so one back wall is, the other only near the desk
                    core={"shelves": (4, 40), "table": (1, 2)},
                    optional={"desk": (0.7, 1), "chair": (0.8, 6), "rug": (0.3, 1), "fireplace": (0.45, 1),
                              "statue": (0.3, 2), "wall_decor": (0.6, 2), "storage": (0.5, 1)},
                    types={"shelves": r"^Bookcase\d(HalfFull)?$", "statue": r"^Statue2[a-h]$", "storage": r"^Chest\d",
                           "table": r"^RoundTable[12]$|^OvalTable[12]$|^SquareTable[12]$"},
                    lined_goal=0.3, decor_max=1, top_up=("storage",),
                    compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.0),
                             dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                             dict(fam="shelves", slot="line", near="desk"),
                             dict(fam="table", slot="center", seats=True),
                             dict(fam="carpet", slot="carpet", where="under", chance=0.3)],
                    fill=[dict(fam="shelves", slot="line", other=True, max=12),
                          dict(fam="table", slot="center", seats=True, max=2, min_area=150),
                          dict(fam="storage", slot="wall", at="center", clear=2.0, max=1, min_area=150),
                          dict(fam="shelves", slot="racks", kind="books", max=8, min_area=250),
                          dict(fam="statue", slot="wall", at="corner", clear=0.6, max=2, min_area=300, fixed=True)]),
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
                       # the room lab (2026-10-05): Westwood's 19 campaign laboratories keep their middle bare (the
                       # floor a piece covers more than 2.5 units from a wall: 0-0.02), hold no cauldron, plant or rug,
                       # line their back walls 0.06-0.35 and hold 4-15 types (median 7): the desk among a bookcase or
                       # two, a bench of workstations, the alchemist's desk, coils along a wall (Con07C, Wiz02B), a
                       # table in a big one. The old middle (a work table on a rug with its cauldron, a conjuring circle
                       # of candelabras) and the plants and statues gave every room away (AUC 1.0)
                       core={"lab": (2, 12), "shelves": (1, 16), "desk": (1, 1)},
                       optional={"table": (1.0, 1), "chair": (1.0, 3), "wall_decor": (0.7, 1), "storage": (0.8, 1),
                                 "statue": (0.6, 2)},
                       types={"lab": r"^AlchemistDesk\d$|^WizardWorkstation\d[a-d]?$|^Telescope2[a-g]$|^Orrery2$|"
                                     r"^Vandegraf(Small|Large)$|^FairyJar$",
                              "shelves": r"^Bookcase\d(HalfFull)?$|^PotionShelves\d$", "storage": r"^Chest\d",
                              "table": r"^Table[1-4]$", "statue": r"^Gargoyle[1-8]$",
                              "chair": r"^Stool\d$|^CushionedStool\d$|^DarkWoodenChair\d$|^WoodenChair\d$"},
                       decor_themes=("blue", "red", "paintings"),
                       # the independent judge (r8): workstations one at a time at even spacing, on the front walls
                       # showing their backs, a lone table in the middle of a bare floor, the bookcase-desk-bookcase
                       # formula. Westwood's curated six hold three workstations or alchemist's desks as a work bench
                       # (Con07C: three side by side), the table against a wall with its chairs (Con07C's corner)
                       lined_goal=0.15, decor_max=1,
                       # Westwood's labs stand their pieces a little off the walls (0.49 units against our snug 0.25)
                       wall_gap={"lab": 0.3, "desk": 0.25, "storage": 0.25, "table": 0.3},
                       top_up=("storage",), lights_per100=4.0,
                       compose=[dict(fam="lab", slot="line", n=3, only=r"^WizardWorkstation"),
                                dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                                dict(fam="shelves", slot="line", near="desk", n=1),
                                dict(fam="lab", slot="wall", at="corner", clear=1.2, only=r"^AlchemistDesk"),
                                dict(fam="storage", slot="wall", at="corner", clear=1.0)],
                       fill=[dict(fam="desk", slot="wall", at="any", clear=0, seats=True, once=True, missing=True),
                             dict(fam="table", slot="wall", at="corner", clear=0, seats=True, max=1, min_area=90, fixed=True),
                             dict(fam="lab", slot="wall", at="center", clear=0.8, only=r"^Vandegraf", max=2, min_area=200,
                                  fixed=True),
                             dict(fam="shelves", slot="line", other=True, n=2, max=4, min_area=150),
                             dict(fam="lab", slot="wall", at="center", clear=0.6, only=r"^FairyJar", max=1, fixed=True),
                             dict(fam="statue", slot="wall", at="corner", clear=0.6, max=2, min_area=220, fixed=True)]),
    "chapel": dict(purpose="a chapel: the altar centred on a back wall between statues, a few rows of pews facing it "
                           "split by a carpeted aisle, a colonnade down the nave, a pair of statues, tapestries on the "
                           "walls, plants in the corners, open floor toward the doors",
                   # 2026-10-05 playtest: 46 pews filled the Greywatch nave wall to wall; a pew per 10 tiles, at most 16
                   core={"altar": (1, 1), "bench": (4, 16), "statue": (2, 4)},
                   optional={"column": (1.0, 8), "tomb": (0.7, 2), "wall_decor": (1.0, 6), "plant": (0.8, 4),
                             "storage": (0.4, 1)},
                   types={"altar": r"^DunMirAltar\d$", "statue": r"^Statue2[a-h]$", "bench": r"^Bench\d$|^LightBench\d$",
                          "column": r"^CathedralColumn[123]$|^Column[5-8]$", "tomb": r"^Crypt(1|3|5|6|7|8|9|10|11|12)$",
                          "storage": r"^DunMirChest\d|^Chest\d", "plant": PLANTS},
                   # tapestries of one colour, never hunting trophies (rules/rooms/chapel.md; Ambermere's chapel held a bear's head)
                   decor_themes=("blue", "red", "white", "green"),
                   # the pews stand in their rows, never topped up along the walls (Mirefen's nave had five benches lining
                   # its front walls: rules/rooms/chapel.md, open floor toward the door)
                   top_up=("plant",),
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
                         dict(fam="tomb", slot="wall", at="center", clear=1.2, max=1, min_area=140),
                         dict(fam="tomb", slot="wall", at="center", clear=1.2, max=1, min_area=200),
                         dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1),
                         dict(fam="plant", slot="wall", at="room_corner", clear=0, max=4)]),
    "crypt": dict(purpose="a crypt: sarcophagi and coffins in rows with aisles between, columns, statues of the dead, "
                          "crypt chests, tapestries",
                  # the room lab (2026-10-05): Westwood's 25 campaign crypts (Con04a-c, War03b-d) hold 1-5 types
                  # (median 2): two to six sarcophagi and tombstones against the walls (nothing free in the middle:
                  # mid_share median 0), a crypt chest, an obelisk or statues in a few; 0.67 tombs per 10 tiles,
                  # coverage 0.08. The old rows of sarcophagi and coffins down the middle with columns, statues,
                  # tapestries and plants gave every one away (AUC 0.98-1.0)
                  core={"tomb": (2, 12)},
                  optional={"statue": (0.3, 2), "storage": (0.6, 1)},
                  types={"tomb": r"^Crypt(1|3|5|6|7|8|9|10|11|12)$|^Coffin\d$",
                         "statue": r"^Statue2[a-h]$", "storage": r"^CryptChest\d$"},
                  top_up=(), lights_per100=2.0,
                  # a step out from the walls (Westwood's: none against a wall, none further than 2.5 units from one):
                  # sarcophagi along the walls a pace out, the chest in a corner, held to the type's cap
                  wall_gap={"tomb": 1.1},
                  # two rows of sarcophagi side by side with a wide aisle between (Westwood's stand in rows: align 1.0),
                  # so each row keeps near its wall; a narrow crypt takes them along its walls a pace out
                  compose=[dict(fam="tomb", slot="racks", kind="tombs", gap=0.5, side_by_side=True, aisle=3.6),
                           dict(fam="storage", slot="wall", at="corner", clear=1.2)],
                  fill=[dict(fam="tomb", slot="wall", at="any", clear=1.0, max=3),
                        dict(fam="statue", slot="wall", at="corner", clear=0.8, max=2, min_area=200, fixed=True)]),
    "hall": dict(purpose="a great hall: a colonnade down its length, statues facing each other, benches along the walls, "
                         "shields and banners on the back walls, plants in the corners",
                 core={"column": (4, 24)},
                 optional={"statue": (0.8, 4), "bench": (0.8, 6), "wall_decor": (1.0, 10), "plant": (0.8, 4),
                           "storage": (0.4, 2), "table": (0.4, 1), "chair": (0.4, 4)},
                 types={"column": r"^Column[5-8]$|^CathedralColumn\d", "statue": r"^Statue2[a-h]$",
                        "storage": r"^DunMirChest\d|^Chest\d", "plant": PLANTS},
                 # 2026-10-05 playtest (Greywatch's keep): paired rows of columns flanking a clear aisle, never a row
                 # down the middle in line with the door
                 # Westwood's halls: 6 columns at the median (Starwell playtest, 2026-10-05)
                 compose=[dict(fam="column", slot="colonnade", gap=3.4, aisle=2.6),
                          dict(fam="wall_decor", slot="decor")],
                 fill=[dict(fam="statue", slot="group", group="statues", max=2, min_area=120, fixed=True),
                       dict(fam="bench", slot="wall", max=4),
                       dict(fam="plant", slot="wall", at="room_corner", clear=0, max=4),
                       dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1)]),
    "great_hall": dict(purpose="a lord's great hall, the heart of the house every other room opens onto: the hearth on a "
                               "back wall, long tables with benches down the middle, banners and trophies on the back "
                               "walls, statues in pairs, benches along the walls, aisles clear along the doors",
                       base="hall",
                       # 2026-10-04 review: "the sheer number of tables and chairs was too much", 4-6 sets fewer;
                       # a table per 48 tiles (was 30), at most 6, and a carpet of floor tiles over the open floor
                       core={"table": (2, 6), "bench": (4, 24), "fireplace": (1, 2)},
                       per_tiles={"table": 48},
                       # 2026-10-05 playtest: benches along every wall and 8 chests (Thornwick) beside the tables'
                       # benches; a bench per 11 tiles in all (the tables' and the hearths' with them), at most 24, a chest
                       # per 80 tiles; open hearths with benches round them fill the ends of a long hall
                       optional={"statue": (0.8, 4), "wall_decor": (1.0, 12), "plant": (0.8, 4), "storage": (0.5, 2),
                                 "column": (0.5, 12), "chair": (0.5, 4)},
                       types={"table": r"^Table[1-4]$|^OvalTable[12]$", "bench": r"^Bench\d$|^CushionedBench\d$",
                              "column": r"^Column[5-8]$", "statue": r"^Statue2[a-h]$", "storage": CHEST,
                              "plant": PLANTS},
                       prefer={"fireplace": {"Fireplace1": 1, "Fireplace2": 1, "Fireplace3": 2, "Fireplace4": 1}},
                       # shields and crossed arms, banners of one colour, or trophies of the hunt (rules/rooms/great_hall.md)
                       decor_themes=("arms", "red", "blue", "green", "trophies"),
                       compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.6),
                                dict(fam="table", slot="table_rows", seat="bench"),
                                dict(fam="carpet", slot="carpet", where="under", margin=3.0, chance=1.0),
                                # hangings either side of the hearth: two at least, the walls carry an open hall
                                # (rules/rooms/great_hall.md; Harrowby's moot hall had one)
                                dict(fam="wall_decor", slot="decor"), dict(fam="wall_decor", slot="decor")],
                       fill=[dict(fam="statue", slot="group", group="statues", max=1, min_area=200, fixed=True),
                             dict(fam="fireplace", slot="wall", at="center", clear=2.6, max=1, min_area=320, fixed=True),
                             dict(fam="fireplace", slot="group", group="hearth", max=1, min_area=300, fixed=True),
                             dict(fam="fireplace", slot="group", group="hearth", max=1, min_area=500, fixed=True),
                             # a few benches by the front walls, no more: the tables' benches already make up most of
                             # the hall's pieces (Harrowby's moot hall: 20 of 32, identity.monotony); one in each front
                             # corner first, where those who wait sit (Harrowby playtest, HB-2: "a little bit too empty.
                             # It needs some more objects and fill along the southeast wall in the south corner")
                             dict(fam="bench", slot="wall", at="room_corner", clear=0, max=2, fixed=True),
                             dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                             dict(fam="statue", slot="wall", at="corner", clear=0.6, max=2, min_area=300, fixed=True),
                             dict(fam="bench", slot="wall", max=3),
                             dict(fam="plant", slot="wall", at="room_corner", clear=0, max=4),
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
                                "the throne, a few pairs of columns spread down its length with pairs of statues between "
                                "them facing across the aisle, tapestries of one colour on the back walls, a bench or two "
                                "for those who wait, plants in the corners",
                        core={"throne": (1, 4), "column": (2, 8)},
                        optional={"statue": (1.0, 6), "wall_decor": (1.0, 8), "storage": (0.5, 1), "plant": (0.6, 4),
                                  "bench": (0.8, 2)},
                        types={"throne": r"^DunMirThrone", "column": r"^Column[5-8]$|^CathedralColumn\d",
                               "statue": r"^Statue2[a-h]$", "storage": r"^DunMirChest\d|^Chest\d", "plant": PLANTS,
                               "bench": r"^Bench[1-4]$|^LightBench\d$|^CushionedBench\d$"},
                        decor_themes=("blue", "red", "white", "green"),
                        top_up=("plant",),           # never chests or benches down the walls to fill the floor
                        compose=[dict(fam="throne", slot="throne"),
                                 dict(fam="statue", slot="flank", of="throne", gap=0.8),
                                 dict(fam="light", slot="flank_lights", of="throne", gap=0.9),
                                 dict(fam="column", slot="colonnade", gap=5.0, aisle=3.0),
                                 dict(fam="statue", slot="groups", group="statues", n=2, extra=True, min_area=100),
                                 dict(fam="bench", slot="wall", at="center", clear=0, n=2),
                                 dict(fam="wall_decor", slot="decor")],
                        fill=[dict(fam="plant", slot="wall", at="room_corner", clear=0, max=4),
                              dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1, fixed=True)]),
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
    # the room lab (2026-10-05): Westwood's 12 ogre barracks (Con05C, Con09c, Con11a, War02A) have no fire pit: straw
    # heaped on the floor is most of the room (median share of the commonest kind 0.64), barrels in a knot, a crude bed
    # or three, a table with a bench and a stool or two, meat, a primitive obelisk; the old den's fire pit ringed by
    # stools (two to five pits in a big den) gave every one away (AUC 1.0)
    "ogre_den": dict(purpose="where the ogres sleep: straw heaped over the floor, crude beds against the back walls, "
                             "barrels in a knot by a wall, a crude table with a bench and stools, meat left about",
                     base="barracks",
                     core={"straw": (5, 80)},
                     optional={"bed": (0.8, 3), "chair": (0.8, 3), "table": (0.6, 1), "bench": (0.5, 1),
                               "storage": (1.0, 8), "clutter": (0.8, 6), "statue": (0.4, 2)},
                     types={"straw": r"^OgreStraw\d$", "bed": r"^OgreBed\d$", "table": r"^OgreTable\d$",
                            "chair": r"^OgreStool\d$", "bench": r"^OgreBench\d$", "statue": r"^ObeliskPrimitive$",
                            "storage": r"^Barrel2?$|^OgreSack\d$|^PiledBarrels\d$|^Chest\d$",
                            "clutter": r"^OgreHutMeat$|^OgreHutCarcass(Big)?$"},
                     prefer={"straw": {"OgreStraw1": 5, "OgreStraw2": 2, "OgreStraw3": 2, "OgreStraw4": 1, "OgreStraw5": 1},
                             "bed": {"OgreBed1": 1, "OgreBed2": 1}, "chair": {"OgreStool1": 2, "OgreStool2": 1},
                             "clutter": {"OgreHutMeat": 4, "OgreHutCarcass": 1}},
                     store=dict(lead={"barrels": 1}, second={}, second_p=0.0, accent={"piled": 1, "ogre": 1}, accent_p=0.5),
                     lights={"TorchPole": 1}, lights_per100=2.0, top_up=(),
                     compose=[dict(fam="straw", slot="scatter", per100=6, cluster=(2, 4)),
                              dict(fam="bed", slot="wall", at="any", clear=0.6, n=2),
                              dict(fam="storage", slot="heaps", n=4),
                              dict(fam="table", slot="groups", group="ogre_table", n=1, extra=True, min_area=130),
                              dict(fam="clutter", slot="scatter", per100=2, cluster=(1, 2))],
                     fill=[dict(fam="straw", slot="scatter", per100=2, max=6),
                           dict(fam="statue", slot="wall", at="corner", clear=0.6, max=1, min_area=150),
                           dict(fam="storage", slot="heaps", max=2)]),
    "ogre_hall": dict(purpose="where the ogres feast: crude round tables ringed by stools, a fire pit, carcasses and meat "
                              "on the floor, straw in the corners, barrels by the walls",
                      base="dining_hall",
                      core={"table": (2, 12), "fireplace": (1, 1)},
                      optional={"chair": (1.0, 30), "storage": (1.0, 8), "clutter": (1.0, 12), "straw": (0.7, 12)},
                      types={"table": r"^OgreTable[123]$", "chair": r"^OgreStool\d$|^OgreBench[34]$",
                             "fireplace": r"^OgreFirePit$", "storage": r"^Barrel2?$|^OgreSack\d$|^PiledBarrels\d$",
                             "clutter": r"^OgreHutMeat$|^OgreHutCarcass(Big)?$", "straw": r"^OgreStraw\d$"},
                      prefer={"table": {"OgreTable1": 2, "OgreTable2": 1, "OgreTable3": 2},
                              "chair": {"OgreStool1": 3, "OgreStool2": 2, "OgreBench3": 1, "OgreBench4": 1},
                              "fireplace": {"OgreFirePit": 1},
                              "storage": {"Barrel": 2, "Barrel2": 1, "OgreSack1": 1, "PiledBarrels2": 1},
                              "clutter": {"OgreHutMeat": 3, "OgreHutCarcass": 1, "OgreHutCarcassBig": 1},
                              "straw": {"OgreStraw1": 3, "OgreStraw2": 1, "OgreStraw3": 1}},
                      per_tiles={"table": 22},
                      lights={"TorchPole": 1},
                      compose=[dict(fam="fireplace", slot="groups", group="firepit", n=1),
                               dict(fam="table", slot="groups", group="ogre_table"),
                               dict(fam="storage", slot="wall", at="corner", clear=0.4, group=True),
                               dict(fam="clutter", slot="scatter", per100=5, cluster=(1, 2))],
                      fill=[dict(fam="table", slot="group", group="ogre_table", max=4),
                            dict(fam="straw", slot="scatter", per100=4, max=12),
                            dict(fam="storage", slot="wall", at="corner", clear=0.4, max=6)]),
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
                       # the ogres' sacks stand two or three to a room (they do not line walls: kit/objects.py), barrels lead
                       store=dict(lead={"barrels": 1}, second={"crates": 2, "piled": 1}, accent={"ogre": 2}),
                       top_up=(),
                       compose=[dict(fam="storage", slot="heaps", n=4),
                                dict(fam="clutter", slot="scatter", per100=3, cluster=(1, 2)),
                                dict(fam="bones", slot="scatter", per100=4, cluster=(1, 3))],
                       fill=[dict(fam="storage", slot="heaps")]),
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
                     # the room lab: the stores heap in touching clumps (store_heaps), never stocked down the walls (the
                     # independent judges of the storeroom and the shop: supplies at even spacing along a wall read as
                     # generated); one shelf of tools, not a lined wall
                     store=dict(lead={"tools": 2, "crates": 1}, second={"crates": 1, "barrels": 1}, second_p=0.9,
                                accent={}, accent_p=0.0),
                     top_up=(), lights_per100=3.0,
                     compose=[dict(fam="shop_rack", slot="line", n=2),
                              dict(fam="shop_rack", slot="wall", at="center", clear=1.0, missing=True),
                              dict(fam="table", slot="groups", group="worktable", n=1, extra=True),
                              dict(fam="anvil", slot="wall", at="corner", clear=1.4),
                              dict(fam="gearwork", slot="wall", at="center", clear=1.0),
                              dict(fam="storage", slot="heaps", n=3),
                              dict(fam="parts", slot="scatter", per100=4, cluster=(1, 2), wall_gap=1.0)],
                     fill=[dict(fam="table", slot="group", group="worktable", max=1, min_area=200, fixed=True),
                           dict(fam="storage", slot="heaps")]),
    # the winch rooms that work a castle's gates, lifts and bridges (Con06a, 110 tiles: 18 gears, a pulley gear, a
    # lever; War07A; War02b's lift room): gear trains on the walls, the great winch standing free
    "winch_room": dict(base="storeroom",
                       purpose="the machinery that works a gate, a lift or a bridge: gear trains against the back walls, "
                               "the great winch (a pulley gear) standing free with room to work it, small gears by it, "
                               "tool barrels and crates of spare parts by the front walls",
                       core={"gearwork": (2, 6), "winch": (1, 1), "storage": (1, 6)},
                       optional={"parts": (0.8, 4)},
                       types={"gearwork": r"^Gear[1-6]$", "winch": r"^PulleyGear[13468]$",
                              "storage": r"^BarrelWithTools[12]$|^(Dark)?Crate[12]$|^Barrel$|^CrateSteel[1-4]$|^BarrelSteel[12]$",
                              "parts": r"^MechGear$"},
                       prefer={"winch": {"PulleyGear1": 1, "PulleyGear3": 2, "PulleyGear6": 1, "PulleyGear8": 1},
                               "gearwork": {f"Gear{k}": 1 for k in range(1, 7)}, "parts": {"MechGear": 1},
                               "storage": {"BarrelWithTools1": 2, "BarrelWithTools2": 2, "DarkCrate1": 1, "Crate2": 1}},
                       lift=("Pulley|",),
                       # the room lab: Westwood's 4 curated winch rooms (Con01A, Con06a, War02b, Wiz03a) keep their stores
                       # in a knot or two (tool barrels, steel crates and barrels, a crate), 0.01-0.06 of the floor
                       store=dict(lead={"tools": 2, "steel": 2}, second={"steel": 1, "barrels": 1, "crates": 1}, second_p=0.8,
                                  accent={}, accent_p=0.0),
                       top_up=(), lights_per100=2.0,
                       compose=[dict(fam="gearwork", slot="wall", at="center", clear=1.2, n=2),
                                dict(fam="winch", slot="center"),
                                dict(fam="storage", slot="heaps", n=2),
                                dict(fam="parts", slot="scatter", per100=3, cluster=(1, 2), wall_gap=1.0)],
                       fill=[dict(fam="winch", slot="center", max=1, min_area=300, fixed=True),
                             dict(fam="gearwork", slot="wall", at="corner", clear=1.0, max=2),
                             dict(fam="storage", slot="heaps", max=1)]),
    # an astronomer's room (Con07B, 97 tiles: three telescopes, a desk, statues; Con07E's star hall: eight star charts,
    # blue tapestries): telescopes at the walls and one free, star charts hung between the bookcases
    "observatory": dict(base="laboratory",
                        purpose="an astronomer's observatory: the desk near a corner of a back wall with bookcases either "
                                "side, star charts and zodiacs hung on the back walls, a telescope at a wall and a "
                                "telescope or an orrery standing free with room round it, the chart table with its stools, "
                                "a chest, plants",
                        core={"lab": (2, 4), "desk": (1, 1), "shelves": (2, 10), "wall_decor": (2, 8)},
                        optional={"table": (0.8, 1), "chair": (0.8, 3), "storage": (0.7, 1)},
                        types={"lab": r"^Telescope(1[bc]|2[aceg]|3[af])$|^Orrery2$", "shelves": r"^Bookcase\d(HalfFull)?$",
                               "storage": r"^Chest\d$", "table": r"^Table[1-4]$|^SquareTable[12]$", "plant": PLANTS,
                               "chair": r"^Stool\d$|^CushionedStool\d$|^DarkWoodenChair\d$|^WoodenChair\d$",
                               "desk": r"^Desk[12]$"},
                        prefer={"wall_decor": {"StarChart1a": 1, "StarChart2a": 1, "StarChart4a": 1, "StarChart2c": 1,
                                               "Zodiac1c": 1, "Zodiac2a": 1}},
                        decor_at="any",
                        # the room lab (the laboratory's lessons): no plants (Westwood's work rooms have none), the
                        # chart table against a wall with its stools rather than alone in the middle, the pieces a step
                        # off the walls
                        top_up=("storage",), wall_gap={"lab": 0.3, "desk": 0.25, "table": 0.3},
                        compose=[dict(fam="lab", slot="groups", group="curio", n=1, extra=True),
                                 dict(fam="lab", slot="wall", at="any", clear=1.2, only=r"^Telescope"),
                                 dict(fam="desk", slot="wall", at="corner", clear=0, seats=True, deep=True),
                                 dict(fam="shelves", slot="line", near="desk", n=2),
                                 dict(fam="table", slot="wall", at="corner", clear=0, seats=True),
                                 dict(fam="wall_decor", slot="decor"), dict(fam="wall_decor", slot="decor"),
                                 dict(fam="wall_decor", slot="decor")],
                        fill=[dict(fam="shelves", slot="line", other=True, max=6),
                              dict(fam="lab", slot="wall", at="any", clear=1.2, only=r"^Orrery", max=1, min_area=150, fixed=True),
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
    # the room lab (2026-10-05): Westwood's 4 curated cellars (Con06a, Con06b, Con07B, War02b) hold barrels, dark crates
    # and a piled barrel or a great cask (1-4 types), the barrels in knots, some standing free (mid_share up to 0.46),
    # coverage 0.06-0.23; no lights inside. Heaped as a store's (kit/furnish.py store_heaps), barrels leading
    "cellar": dict(base="storeroom",
                   purpose="a cellar of kegs and casks: barrels in knots in the corners and along the walls, dark crates by "
                           "them, a great cask or a piled barrel, aisles to walk",
                   core={"storage": (5, 30)},
                   optional={},
                   types={"storage": r"^(Barrel|Barrel2|LargeBarrel[12]|PiledBarrels[1-4]|DarkCrate[12]|Crate[12])$"},
                   store=dict(lead={"barrels": 1}, second={"crates": 1}, second_p=0.4, accent={"piled": 1, "large": 1},
                              accent_p=0.7),
                   top_up=(), lights_per100=0,
                   compose=[dict(fam="storage", slot="heaps", n=4)],
                   fill=[dict(fam="storage", slot="heaps")]),
    # a strongroom (Con05B: the ogres' chests and gold; Wiz06c: Dun Mir chests under hanging shields; Con06b: chests and a
    # round table with four chairs)
    # the room lab (2026-10-05; the object knowledge agent: "the lab's treasuries read as armouries", trader's shelves and
    # hung shields dominating): Westwood's one curated strongroom (Con05B, the ogres', 54 tiles) holds two chests, sacks
    # of loot of two sizes and a great cask, spread over a bare floor (coverage 0.03). The treasury keeps its strongboxes
    # (three to a room, the knowledge base's cap), the sacks and a cask, the counting table and its chair; no shelves of
    # wares, no hung arms
    "treasury": dict(base="storeroom",
                     purpose="a strongroom: strongboxes along the back walls each with room before it to open, sacks of "
                             "coin heaped by them, a cask, the treasurer's counting table and chair, open floor",
                     core={"storage": (3, 8), "table": (1, 1), "chair": (1, 2)},
                     optional={},
                     types={"storage": r"^Chest[1-4]$|^SackChest(Large|Medium)[12]$|^LargeBarrel[12]$",
                            "table": r"^SquareTable[12]$|^Table[1-4]$", "chair": r"Chair"},
                     store=dict(lead={"sacks": 1}, second={"large": 1}, second_p=0.7, accent={}, accent_p=0.0),
                     top_up=(), lights_per100=2.0, decor_max=0,
                     compose=[dict(fam="storage", slot="wall", at="center", clear=2.0, only=r"^Chest", n=3),
                              dict(fam="storage", slot="heaps", n=2),
                              dict(fam="table", slot="center", seats=True)],
                     fill=[dict(fam="storage", slot="heaps", max=1)]),
    # a powder magazine (Con07C, 31 tiles: 22 powder kegs; Con09c, 30 tiles: 11 powder kegs and 2 barrels): the one room
    # black powder belongs in, kept apart
    "powder_store": dict(base="storeroom",
                         # the room lab: Westwood's Con09c (30 tiles): 11 kegs of black powder in knots, some free of the
                         # walls (mid_share 0.31), two plain barrels; no lights (an open flame by powder)
                         purpose="a powder magazine: kegs of black powder in knots along the walls and standing free, a "
                                 "few plain barrels, the way in clear",
                         core={"storage": (6, 30)},
                         optional={},
                         types={"storage": r"^BlackPowderBarrel2?$|^Barrel$|^DarkCrate[12]$"},
                         store=dict(lead={"powder": 1}, second={"barrels": 1}, second_p=0.6, accent={}, accent_p=0.0),
                         top_up=(), lights_per100=0,
                         compose=[dict(fam="storage", slot="heaps", n=4)],
                         fill=[dict(fam="storage", slot="heaps")]),
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
                            # the room lab: its pool lights nothing inside (0 lights a tile); the brazier is light enough
                            top_up=(), lights_per100=1.5,
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
                   optional={"bench": (0.8, 2), "basin": (0.9, 2), "wall_decor": (1.0, 3), "plant": (0.5, 2)},
                   types={"altar": r"^DunMirAltar\d$", "statue": r"^Statue2[a-h]$", "bench": r"^Bench\d$|^LightBench\d$",
                          "basin": r"^DunMirFlameBasinLit$", "plant": PLANTS},
                   prefer={"altar": {"DunMirAltar1": 3, "DunMirAltar2": 1}, "basin": {"DunMirFlameBasinLit": 1}},
                   decor_themes=("blue", "red", "white", "green"),
                   lift=("DunMir|",),
                   top_up=("plant",),
                   compose=[dict(fam="altar", slot="wall", at="center", clear=2.6, deep=True, door=True),
                            dict(fam="statue", slot="flank", of="altar", gap=0.8),
                            dict(fam="light", slot="flank_lights", of="altar", gap=0.9),
                            dict(fam="bench", slot="pews", toward="altar", runner=True),
                            dict(fam="basin", slot="wall", at="corner", clear=0.8, n=2),
                            dict(fam="wall_decor", slot="decor")],
                   fill=[dict(fam="statue", slot="wall", at="corner", clear=0.8, max=2, fixed=True, min_area=70),
                         dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2)]),
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
                    core={"wall_decor": (6, 14), "bench": (1, 4)},
                    optional={"statue": (0.9, 4), "plant": (1.0, 4), "lab": (0.6, 1)},
                    types={"bench": r"^Bench[1-4]$|^CushionedBench\d$", "statue": r"^Statue2[aceg]$", "plant": PLANTS,
                           "lab": r"^Orrery2$"},
                    prefer={"wall_decor": {"Painting1": 1, "Painting2": 1}},
                    decor_at="any",           # paintings at the ends of each stretch of wall as well as its middle
                    top_up=("plant",),
                    compose=[dict(fam="bench", slot="center"),
                             dict(fam="statue", slot="groups", group="statues", n=1, extra=True, min_area=80),
                             dict(fam="plant", slot="wall", at="room_corner", clear=0, n=4),
                             dict(fam="wall_decor", slot="decor")],
                    # statues toward the far corners carry the room's length (validate/checks.py SPREAD_MIN)
                    fill=[dict(fam="statue", slot="wall", at="corner", clear=0.8, max=2, fixed=True, min_area=120),
                          dict(fam="lab", slot="group", group="curio", max=1, min_area=140, fixed=True),
                          dict(fam="bench", slot="center", max=1, min_area=120)]),
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
    # the room lab: Westwood's 6 curated mausoleums (Con04a's three, Con04c, Con09b, Con10c) hold no great tomb: statues of
    # the dead (2-12) along the walls in pairs, a crypt chest, columns in Con04c, obelisks in Con09b and Con10c; coverage
    # 0.03-0.10, nothing free in the middle
    "mausoleum": dict(base="crypt", grand=True,
                      purpose="a mausoleum: statues of the dead along the walls in pairs facing into the room, a crypt chest, "
                              "a pair of columns in a big one; the floor bare",
                      core={"statue": (2, 12), "storage": (1, 2)},
                      optional={"column": (0.5, 4)},
                      types={"statue": r"^Statue2[aceg]$", "storage": r"^CryptChest[1-4]$", "column": r"^Column[5-8]$"},
                      prefer={"storage": {"CryptChest1": 1, "CryptChest2": 1, "CryptChest3": 1, "CryptChest4": 1}},
                      lift=("Crypt|",),
                      # Westwood's are symmetric (mirror symmetry 0.85-1) and lit (0.06 lights a tile): the statues
                      # stand in mirrored pairs (GROUPS statues), the chest centred on a back wall
                      top_up=(), lights_per100=6.0, decor_max=0,
                      # (statues standing free in the middle read wrong: Westwood's stand by the walls, 0.04 in the
                      # middle) the chest centred on a back wall with a pair of statues flanking it, more statues by the
                      # walls in the corners
                      # (r3-r4 stood them by the walls flanking the chest: AUC 0.93-1.0; the mirrored pairs of r2 read
                      # closer, 0.88, once the crypt chests took their wall's variant)
                      compose=[dict(fam="statue", slot="groups", group="statues", n=2, extra=True),
                               dict(fam="storage", slot="wall", at="center", clear=1.2)],
                      fill=[dict(fam="statue", slot="group", group="statues", max=2, min_area=120),
                            dict(fam="column", slot="racks", kind="columns", gap=4.0, aisle=3.0, min_area=240, max=4,
                                 fixed=True)]),
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
