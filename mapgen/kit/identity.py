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
                    compose=[dict(fam="bed", slot="wall", at="any", clear=1.0),
                             dict(fam="storage", slot="wall", at="center", clear=2.3, rug=True),
                             dict(fam="shelves", slot="line", n=3),
                             dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                             dict(fam="carpet", slot="carpet", where="whole", chance=0.4),
                             dict(fam="wall_decor", slot="decor")],
                    fill=[dict(fam="shelves", slot="line", other=True, decor=2, max=8, min_area=100), dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1, min_area=140), dict(fam="table", slot="group", group="sitting", max=1, min_area=90), dict(fam="desk", slot="wall", at="center", clear=0, seats=True, once=True),
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
                        fill=[dict(fam="table", slot="group", group="dining", max=1, min_area=200), dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1, min_area=120), dict(fam="shelves", slot="line", other=True, decor=2, max=10, min_area=120), dict(fam="table", slot="group", group="sitting", max=1, min_area=120), dict(fam="statue", slot="group", group="statues", max=1, min_area=240), dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
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
                    fill=[dict(fam="table", slot="group", group="feast", max=1, min_area=120), dict(fam="table", slot="group", group="worktable", max=2, min_area=170), dict(fam="storage", slot="stock", coverage=1.0, kinds=("barrels", "sacks", "apples", "crates"),
                               pad=1.0, max=10),
                          dict(fam="storage", slot="stack", n=3, once=True)]),
    "herbalist": dict(purpose="an herb-lore room: one back wall lined end to end with shelves of potions and remedies, a "
                              "bubbling cauldron, a work table toward the front, sacks of herbs, herbs growing in pots",
                      base="study",
                      core={"shelves": (3, 10), "stove": (1, 1), "table": (1, 1), "chair": (1, 2)},
                      optional={"lab": (0.8, 2), "storage": (1.0, 6), "plant": (1.0, 3), "wall_decor": (0.8, 3)},
                      types={"lab": r"^AlchemistDesk\d$|^WizardWorkstation\d[a-d]?$", "shelves": r"^PotionShelves\d$|^Bookcase\d$", "stove": r"^Cauldron",
                             "storage": r"^Chest\d|^SackChest|(?<!Powder)Barrel$|(?<!Powder)Barrel\d", "plant": PLANTS},
                      prefer={"shelves": {"PotionShelves1": 1, "PotionShelves2": 1, "PotionShelves3": 1, "PotionShelves4": 1},
                              "stove": {"CauldronAnimated": 1}, "table": {"Table4": 1, "SquareTable1": 1}},
                      compose=[dict(fam="shelves", slot="line"),
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
                      compose=[dict(fam="shop_rack", slot="line"),
                               dict(fam="cart", slot="wall", at="any", clear=1.2),
                               dict(fam="shop_rack", slot="racks", kind="mine"),
                               dict(fam="storage", slot="stock", coverage=0.7, kinds=("crates", "tools", "barrels"), pad=1.2)],
                      fill=[dict(fam="shop_rack", slot="line", other=True, max=8, min_area=120), dict(fam="cart", slot="group", group="carts", max=2), dict(fam="storage", slot="stock", coverage=1.0, kinds=("crates", "barrels", "sacks", "tools"), pad=1.0),
                            dict(fam="storage", slot="stack", n=3, once=True)]),
    "tavern": dict(purpose="the public drinking room: a long bar with kegs behind it, round tables crowded with stools, "
                           "a hearth with shelves of tankards beside it, trophies on the walls, benches along the front "
                           "walls, a table laid with food",
                   core={"counter_bar": (1, 1), "table": (3, 12), "chair": (6, 48), "storage": (3, 10), "fireplace": (1, 1)},
                   per_tiles={"table": 20},
                   optional={"bench": (0.8, 4), "wall_decor": (1.0, 8), "rug": (0.3, 1), "shelves": (0.9, 10),
                             "plant": (0.6, 2)},
                   types={"storage": r"(?<!Powder)Barrel$|(?<!Powder)Barrel\d|PiledBarrels|LargeBarrel",
                          "table": r"RoundTable|^Table\d$|SquareTable", "chair": r"Stool|Chair",
                          "shelves": r"^LogShelvesFull\d$|^Bookcase\d(HalfFull)?$", "plant": PLANTS},
                   compose=[dict(fam="counter_bar", slot="bar"),
                            dict(fam="fireplace", slot="wall", at="center", clear=2.4),
                            dict(fam="shelves", slot="line", near="fireplace", decor=2),
                            dict(fam="table", slot="groups", group="dining"),
                            dict(fam="wall_decor", slot="decor")],
                   fill=[dict(fam="table", slot="group", group="feast", max=2, min_area=200),
                         dict(fam="table", slot="group", group="dining", max=4, min_area=60),
                         dict(fam="bench", slot="wall", max=3),
                         dict(fam="storage", slot="stock", coverage=0.25, kinds=("barrels",), pad=1.2, max=2),
                         dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2)]),
    "mess_hall": dict(purpose="where a crew eats together: long tables in rows with a bench along each side, the hearth "
                              "on a back wall flanked end to end by shelves of crockery, benches along the front walls, "
                              "trophies and hangings on the back walls",
                      base="dining_hall",
                      core={"fireplace": (1, 1), "table": (2, 8), "bench": (4, 20), "shelves": (2, 12)},
                      per_tiles={"table": 14},
                      optional={"wall_decor": (1.0, 6)},
                      types={"table": r"^Table[1-4]$", "bench": r"^Bench\d$|^LightBench\d$|^CushionedBench\d$",
                             "chair": r"Stool|Chair", "shelves": r"^LogShelvesFull\d$"},
                      prefer={"fireplace": {"Fireplace1": 1, "Fireplace2": 1, "Fireplace3": 2, "Fireplace4": 1}},
                      compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4),
                               dict(fam="shelves", slot="line", near="fireplace"),
                               dict(fam="table", slot="table_rows", seat="bench"),
                               dict(fam="wall_decor", slot="decor")],
                      fill=[dict(fam="bench", slot="wall", at="center", clear=0, max=3),
                            dict(fam="shelves", slot="line", max=8)]),
    "dining_hall": dict(purpose="a household's dining hall: long tables seated along both sides, the hearth on a back wall "
                                "flanked by shelves of crockery, hangings above, a table of food, plants in the corners",
                        core={"table": (1, 6), "chair": (4, 36), "fireplace": (1, 1)},
                        per_tiles={"table": 16},
                        optional={"rug": (0.6, 1), "wall_decor": (1.0, 8), "shelves": (1.0, 12), "bench": (0.6, 2),
                                  "plant": (0.8, 3), "statue": (0.5, 2), "storage": (0.5, 2)},
                        types={"table": r"^Table[1-4]$|^OvalTable[12]$|^RoundTableWithFood$|^RoundTable[123]$",
                               "shelves": r"^LogShelvesFull\d$|^Bookcase\d(HalfFull)?$", "statue": r"^Statue2[a-h]$",
                               "storage": CHEST, "plant": PLANTS},
                        compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4),
                                 dict(fam="shelves", slot="line", near="fireplace", decor=2),
                                 dict(fam="table", slot="table_rows", seat="chair"),
                                 dict(fam="carpet", slot="carpet", where="under", chance=0.5),
                                 dict(fam="wall_decor", slot="decor")],
                        fill=[dict(fam="table", slot="group", group="dining", max=2, min_area=140), dict(fam="table", slot="group", group="feast", max=1, min_area=90),
                              dict(fam="statue", slot="group", group="statues", max=1, min_area=260),
                              dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                              dict(fam="bench", slot="wall", max=2),
                              dict(fam="shelves", slot="line", other=True, decor=2, max=8, min_area=140)]),
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
    "gear_store": dict(purpose="a crew's gear in good order: armour stands and racks of pole arms, clothes and bows in "
                               "rows down the middle, a back wall lined with shelves, barrels, crates and tool barrels "
                               "along the front walls",
                       base="storeroom",
                       core={"storage": (4, 24), "shop_rack": (3, 16), "shelves": (2, 10)},
                       optional={},
                       types={"storage": SUPPLY, "shelves": r"^LogShelvesFull\d$", "shop_rack": RACKS},
                       compose=[dict(fam="shelves", slot="line"),
                                dict(fam="shop_rack", slot="racks", kind="gear"),
                                dict(fam="storage", slot="stock", coverage=0.8, kinds=("crates", "barrels", "tools", "sacks"))],
                       fill=[dict(fam="storage", slot="stack", n=3, once=True),
                             dict(fam="storage", slot="stock", coverage=1.0, kinds=("barrels", "crates", "tools"), pad=0.3)]),
    "smithy": dict(purpose="the forge: glowing coals with the bellows beside them, the anvil before the fire, water to "
                           "quench the iron, barrels and crates of tools and iron, finished weapons on racks along a "
                           "back wall and down the middle, a work table",
                   core={"forge": (1, 1), "bellows": (1, 1), "anvil": (1, 1), "storage": (2, 12)},
                   optional={"shop_rack": (1.0, 12), "table": (0.6, 1), "chair": (0.6, 2)},
                   types={"storage": r"WaterBarrel|BarrelWithTools\d$|DarkCrate\d|^Crate[12]$|(?<!Powder)Barrel\d?$",
                          "shop_rack": r"^TraderPoleArm\d|^TraderHangingSwords\d|^TraderArmorRack[12]$",
                          "table": r"^Table[1-4]$"},
                   prefer={"forge": {"CinderBin2": 1, "CinderBin1": 1},
                           "bellows": {f"Bellows{k}": 1 for k in range(1, 9)},
                           "anvil": {f"Anvil{k}": 1 for k in range(1, 9)},
                           "storage": {"WaterBarrel": 2, "BarrelWithTools1": 1, "BarrelWithTools2": 1, "DarkCrate1": 1,
                                       "DarkCrate2": 1, "Barrel2": 1},
                           "shop_rack": {"TraderPoleArm1": 1, "TraderPoleArm2": 1, "TraderPoleArm3": 1, "TraderPoleArm4": 1}},
                   compose=[dict(fam="forge", slot="wall", at="center", clear=2.4),
                            dict(fam="bellows", slot="wall", at="corner", beside="forge", clear=0),
                            dict(fam="anvil", slot="before", of="forge", gap=2.4),
                            dict(fam="shop_rack", slot="line", other=True),
                            dict(fam="storage", slot="stock", coverage=0.5, kinds=("barrels", "crates", "tools"), pad=1.2)],
                   fill=[dict(fam="shop_rack", slot="racks", kind="gear", max=10, min_area=150),
                         dict(fam="table", slot="group", group="worktable", max=1, min_area=120),
                         dict(fam="storage", slot="stock", coverage=0.8, kinds=("barrels", "crates", "tools"), pad=1.0, max=6),
                         dict(fam="storage", slot="stack", n=3, once=True)]),
    "study": dict(purpose="the desk centred on a back wall with books lining that wall end to end on both sides and "
                          "hangings between them, a chest on the other back wall, a meeting table with chairs toward the "
                          "front on a carpet, plants",
                  core={"desk": (1, 1), "shelves": (2, 14), "storage": (1, 2), "table": (1, 1)},
                  optional={"statue": (0.4, 2), "lab": (0.8, 3), "rug": (0.8, 1), "wall_decor": (1.0, 6), "plant": (0.8, 2), "table": (0.8, 1), "chair": (0.8, 3)},
                  types={"statue": r"^Statue2[a-h]$", "lab": r"^AlchemistDesk\d$|^WizardWorkstation\d[a-d]?$|^Telescope2[a-g]$|^Orrery2$|^SentryGlobeMovable$", "storage": r"^Chest\d", "shelves": r"^Bookcase\d(HalfFull)?$", "plant": PLANTS,
                         "table": r"^RoundTable[12]$|^SquareTable[12]$"},
                  compose=[dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                           dict(fam="shelves", slot="line", near="desk", decor=2), dict(fam="shelves", slot="line", other=True, decor=2),
                           dict(fam="storage", slot="wall", at="center", clear=2.3),
                           dict(fam="table", slot="center", seats=True),
                           dict(fam="carpet", slot="carpet", where="under", chance=0.7),
                           dict(fam="wall_decor", slot="decor")],
                  fill=[dict(fam="table", slot="group", group="dining", max=1, min_area=160), dict(fam="shelves", slot="line", other=True, decor=2, max=12), dict(fam="lab", slot="wall", at="center", clear=1.2, max=1), dict(fam="shelves", slot="racks", kind="books", max=8, min_area=200), dict(fam="lab", slot="group", group="curio", max=1, min_area=90), dict(fam="table", slot="group", group="sitting", max=1, min_area=120), dict(fam="shelves", slot="line", n=4, max=4),
                        dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                        dict(fam="storage", slot="wall", at="center", clear=1.6, max=1)]),
    "library": dict(purpose="books: bookcases lining both back walls end to end, stacks of bookcases in rows down the "
                            "middle of a big library, a reading table on a carpet, a desk, a curio",
                    core={"shelves": (4, 40)},
                    optional={"desk": (0.7, 1), "table": (0.8, 2), "chair": (0.8, 6), "rug": (0.6, 1),
                              "fireplace": (0.25, 1), "lab": (0.5, 1), "plant": (0.5, 2), "statue": (0.3, 2),
                              "wall_decor": (0.8, 4)},
                    types={"shelves": r"^Bookcase\d(HalfFull)?$", "lab": r"^Telescope2[a-g]$|^Orrery2$|^SentryGlobeMovable$",
                           "statue": r"^Statue2[a-h]$", "plant": PLANTS},
                    compose=[dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                             dict(fam="shelves", slot="line", near="desk"),
                             dict(fam="shelves", slot="line", other=True),
                             dict(fam="table", slot="center", seats=True),
                             dict(fam="carpet", slot="carpet", where="under", chance=0.6),
                             dict(fam="wall_decor", slot="decor")],
                    fill=[dict(fam="shelves", slot="racks", kind="books", max=16, min_area=150),
                          dict(fam="lab", slot="group", group="curio", max=1, min_area=120),
                          dict(fam="table", slot="group", group="sitting", max=1, min_area=200),
                          dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2)]),
    "laboratory": dict(purpose="a wizard's laboratory: workstations and alchemist's desks lining a back wall end to end, "
                               "bookcases lining the other, curios (a telescope, an orrery, a crackling generator) standing "
                               "free, a reading table on a carpet, potions on shelves, glowing jars",
                       core={"lab": (2, 12), "shelves": (2, 20), "table": (1, 1)},
                       optional={"chair": (0.8, 3), "desk": (0.5, 1), "plant": (0.6, 2), "rug": (0.5, 1),
                                 "wall_decor": (0.8, 4), "storage": (0.6, 2)},
                       types={"lab": r"^AlchemistDesk\d$|^WizardWorkstation\d[a-d]?$|^Telescope2[a-g]$|^Orrery2$|"
                                     r"^SentryGlobeMovable$|^VandegrafSmall$",
                              "shelves": r"^Bookcase\d(HalfFull)?$|^PotionShelves\d$", "storage": r"^Chest\d", "plant": PLANTS},
                       compose=[dict(fam="lab", slot="line"),
                                dict(fam="shelves", slot="line", other=True, decor=2),
                                dict(fam="table", slot="center", seats=True),
                                dict(fam="carpet", slot="carpet", where="under", chance=0.6),
                                dict(fam="wall_decor", slot="decor")],
                       fill=[dict(fam="lab", slot="group", group="curio", max=2, min_area=90),
                             dict(fam="shelves", slot="racks", kind="books", max=10, min_area=220),
                             dict(fam="table", slot="group", group="sitting", max=1, min_area=160),
                             dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                             dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1)]),
    "chapel": dict(purpose="a chapel: the altar centred on a back wall between statues, pews in rows facing it with an "
                           "aisle down the middle, tapestries on the walls, plants in the corners",
                   core={"altar": (1, 1), "bench": (4, 40)},
                   optional={"statue": (0.8, 4), "wall_decor": (1.0, 6), "plant": (0.6, 4), "storage": (0.4, 1)},
                   types={"altar": r"^DunMirAltar\d$", "statue": r"^Statue2[a-h]$", "bench": r"^Bench\d$|^LightBench\d$",
                          "storage": r"^DunMirChest\d|^Chest\d", "plant": PLANTS},
                   compose=[dict(fam="altar", slot="wall", at="center", clear=2.6),
                            dict(fam="statue", slot="wall", beside="altar", gap=0.8, clear=0),
                            dict(fam="statue", slot="wall", beside="altar", gap=0.8, clear=0),
                            dict(fam="bench", slot="pews", toward="altar"),
                            dict(fam="wall_decor", slot="decor")],
                   fill=[dict(fam="statue", slot="group", group="statues", max=1, min_area=120),
                         dict(fam="plant", slot="wall", at="room_corner", clear=0, max=4)]),
    "crypt": dict(purpose="a crypt: sarcophagi and coffins in rows with aisles between, columns, statues of the dead, "
                          "crypt chests, tapestries",
                  core={"tomb": (2, 30)},
                  optional={"column": (0.8, 12), "statue": (0.6, 4), "storage": (0.6, 3), "wall_decor": (0.7, 4),
                            "plant": (0.3, 3)},
                  types={"tomb": r"^Crypt\d+$|^Coffin\d$", "column": r"^CathedralColumn\d|^Column\d$",
                         "statue": r"^Statue2[a-h]$|^Gargoyle\d$", "storage": r"^Chest\d$",
                         "plant": r"^PlantBarren\d$|^Plant[15]$"},
                  compose=[dict(fam="tomb", slot="racks", kind="tombs", gap=0.6, side_by_side=True, aisle=1.8),
                           dict(fam="storage", slot="wall", at="corner", clear=1.2),
                           dict(fam="wall_decor", slot="decor")],
                  fill=[dict(fam="column", slot="racks", kind="cathedral", gap=3.2, aisle=1.2, min_area=180),
                        dict(fam="statue", slot="group", group="statues", max=1, min_area=150),
                        dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2)]),
    "hall": dict(purpose="a great hall: a colonnade down its length, statues facing each other, benches along the walls, "
                         "shields and banners on the back walls, plants in the corners",
                 core={"column": (4, 24)},
                 optional={"statue": (0.8, 4), "bench": (0.8, 6), "wall_decor": (1.0, 10), "plant": (0.8, 4),
                           "storage": (0.4, 2), "table": (0.4, 1), "chair": (0.4, 4)},
                 types={"column": r"^Column[5-8]$|^CathedralColumn\d", "statue": r"^Statue2[a-h]$",
                        "storage": r"^DunMirChest\d|^Chest\d", "plant": PLANTS},
                 compose=[dict(fam="column", slot="racks", kind="columns", gap=3.4, aisle=2.6),
                          dict(fam="wall_decor", slot="decor")],
                 fill=[dict(fam="statue", slot="group", group="statues", max=2, min_area=120),
                       dict(fam="bench", slot="wall", max=4),
                       dict(fam="plant", slot="wall", at="room_corner", clear=0, max=4),
                       dict(fam="storage", slot="wall", at="corner", clear=1.0, max=1)]),
    "throne_room": dict(purpose="a throne room: the throne centred on the NE wall facing the doors, a colonnade down the "
                                "room, statues flanking the way, banners, a carpet runner",
                        core={"throne": (1, 4), "column": (2, 16)},
                        optional={"statue": (0.8, 4), "wall_decor": (1.0, 8), "storage": (0.5, 2), "plant": (0.6, 4)},
                        types={"throne": r"^DunMirThrone", "column": r"^Column[5-8]$|^CathedralColumn\d",
                               "statue": r"^Statue2[a-h]$", "storage": r"^DunMirChest\d|^Chest\d", "plant": PLANTS},
                        compose=[dict(fam="throne", slot="throne"),
                                 dict(fam="column", slot="racks", kind="columns", gap=3.4, aisle=3.0),
                                 dict(fam="wall_decor", slot="decor")],
                        fill=[dict(fam="statue", slot="group", group="statues", max=2, min_area=100),
                              dict(fam="plant", slot="wall", at="room_corner", clear=0, max=4),
                              dict(fam="storage", slot="wall", at="corner", clear=1.0, max=2)]),
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
}

# ---- buildings ---------------------------------------------------------------------------------------
# rooms: (kind, purpose) in order, the first is the largest and takes the entrance;
# scenes: outdoor prop groups that show the building's trade.
BUILDINGS = {
    "inn": dict(purpose="food, drink and a bed for travellers", style="stucco_house", size=(40, 32), shape="rect", min_units=240,
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
    "mill": dict(purpose="the miller's house by the pond", style="log_cabin", size=(18, 16),
                 rooms=[("living_room", "the miller's hearth room"), ("storeroom", "sacks of grain")],
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
}

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


# The Westwood room kind each generated kind is measured against (validate/baseline.json room_kinds).
WESTWOOD_KIND = {"herbalist": "laboratory", "mess_hall": "dining_hall", "ore_store": "storeroom", "study": "library",
                 "dwelling": "living_room", "gear_store": "storeroom"}
# How much of a room's floor its furniture covers: (target, limit). The furnisher fills toward the target and never
# past the limit, which the checker holds generated rooms to (TreePlace room reviews: rooms furnished to Westwood's
# typical counts read as empty, and a store room holds more than any other room). Coverage grows with the room, so
# rooms bigger than Westwood's get more. Westwood's house rooms: p50 0.10-0.14, p75 0.15-0.19; storerooms p75 0.23,
# barracks 0.25.
ROOM_COVER = {"tavern": (0.20, 0.34), "dining_hall": (0.17, 0.32), "shop": (0.24, 0.40), "laboratory": (0.17, 0.30), "chapel": (0.18, 0.34),
              "crypt": (0.18, 0.36), "hall": (0.03, 0.22), "throne_room": (0.04, 0.24),
              "smithy": (0.24, 0.38), "library": (0.17, 0.32), "storeroom": (0.30, 0.42), "gear_store": (0.30, 0.42), "ore_store": (0.28, 0.42), "kitchen": (0.21, 0.32),
              "barracks": (0.24, 0.34), "mess_hall": (0.24, 0.34), "living_room": (0.17, 0.30), "herbalist": (0.17, 0.30),
              "study": (0.17, 0.30), "bedroom": (0.14, 0.28), "dwelling": (0.16, 0.30)}
ROOM_COVER_DEFAULT = (0.16, 0.30)
# Buildings are larger than Westwood's (the user, during the TreePlace v0.3 review: "bias towards bigger rooms and
# structures than westwood"): each role's size and floor below are scaled by this much in each direction.
BUILDING_SCALE = 1.25


def role_size(role):
    """A building role's size (uv units, even) and least floor, at the house scale (BUILDING_SCALE)."""
    w, h = role["size"]
    return (2 * round(w * BUILDING_SCALE / 2), 2 * round(h * BUILDING_SCALE / 2)), int(role.get("min_units", 0) * BUILDING_SCALE ** 2)


def rooms_sidecar(placed, path):
    """Writes <map>.rooms.json next to a built map for review/rooms.py: every room numbered in building order,
    with its building, kind, purpose (from the building's room program), floor tiles and box (grid cells).
    placed: [(BuildingIdentity, Building)] as the design placed them."""
    import json
    out = []
    for bid, b in placed:
        program = list(BUILDINGS.get(bid.role, {}).get("rooms", []))
        for r in b.rooms:
            purpose = next((p for kind, p in program if kind == r.kind), "")
            program = [kp for kp in program if kp != (r.kind, purpose)]
            xs = [x for x, _ in r.tiles]; ys = [y for _, y in r.tiles]
            out.append(dict(number=len(out) + 1, building=bid.name or bid.role, kind=r.kind, purpose=purpose,
                            tiles=len(r.tiles), box=[min(xs) - 1, min(ys) - 1, max(xs) + 3, max(ys) + 3],
                            floor=sorted([x, y] for x, y in r.tiles)))
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
            rooms = ", ".join(f"{k} ({p})" for k, p in r["rooms"])
            lines.append(f"- {b.name or b.role} in the {b.area}: {r['purpose']}"
                         + (f", home of {b.occupant}" if b.occupant else "") + f". Rooms: {rooms}.")
        return "\n".join(lines)
