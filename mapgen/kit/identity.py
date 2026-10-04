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
ROOMS = {
    "bedroom": dict(purpose="where someone sleeps: the bed with a nightstand, a chest for belongings, a wardrobe of "
                            "shelves, a rug, hangings on the walls, a desk or a bench",
                    core={"bed": (1, 1), "storage": (1, 1)},
                    optional={"rug": (1.0, 2), "nightstand": (1.0, 1), "shelves": (0.9, 3), "wall_decor": (1.0, 3),
                              "desk": (0.5, 1), "bench": (0.6, 1), "plant": (0.5, 2), "table": (0.6, 1), "chair": (0.6, 2)},
                    types={"storage": CHEST, "shelves": r"Bookcase|Shelves", "plant": r"^(Plant4|Plant5)$", "table": r"^RoundTable[12]$|^SquareTable[12]$"},
                    compose=[dict(fam="bed", slot="wall", at="any", clear=1.0),
                             dict(fam="storage", slot="wall", at="center", clear=2.3, rug=True),
                             dict(fam="shelves", slot="wall", at="center", clear=1.4),
                             dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                             dict(fam="wall_decor", slot="decor")],
                    fill=[dict(fam="desk", slot="wall", at="center", clear=0, seats=True, once=True),
                          dict(fam="shelves", slot="wall", at="center", clear=1.4, max=2),
                          dict(fam="table", slot="center", seats=True, once=True, rug=True),
                          dict(fam="bench", slot="wall", at="center", clear=0, once=True),
                          dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2)]),
    "dwelling": dict(purpose="a one-room home: bed, hearth, a table to eat at, a chest for belongings",
                     base="living_room",
                     core={"bed": (1, 1), "table": (1, 1), "chair": (1, 2), "storage": (1, 1)},
                     optional={"fireplace": (0.7, 1), "rug": (0.8, 1), "shelves": (0.6, 1), "wall_decor": (0.5, 1)},
                     types={"storage": CHEST},
                     prefer={"fireplace": {"Fireplace4": 1, "Fireplace3": 1}},
                     compose=[dict(fam="bed", slot="wall", at="any", clear=1.0),
                              dict(fam="fireplace", slot="wall", at="center", clear=2.4, rug=True),
                              dict(fam="storage", slot="wall", at="center", clear=2.3, rug=True),
                              dict(fam="shelves", slot="wall", at="center", clear=1.4),
                              dict(fam="table", slot="center", seats=True),
                              dict(fam="rug", slot="center"),
                              dict(fam="wall_decor", slot="decor")]),
    "living_room": dict(purpose="the household's hearth room: the hearth with a rug before it, a table with its chairs, "
                                "shelves and a chest along the walls, trophies and hangings on the walls, a bench, plants",
                        core={"fireplace": (1, 1), "table": (1, 1), "chair": (2, 4), "shelves": (1, 2)},
                        optional={"rug": (1.0, 2), "storage": (0.8, 1), "wall_decor": (1.0, 4), "bench": (0.8, 1),
                                  "plant": (0.7, 2)},
                        types={"storage": CHEST, "shelves": r"^Bookcase\d$|^LogShelvesFull\d$",
                               "plant": r"^(Plant4|Plant5)$"},
                        prefer={"fireplace": {"Fireplace4": 1, "Fireplace3": 1}},
                        compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4, rug=True),
                                 dict(fam="shelves", slot="wall", at="center", clear=1.4),
                                 dict(fam="storage", slot="wall", at="center", clear=2.3, rug=True),
                                 dict(fam="bench", slot="wall", at="center", clear=0),
                                 dict(fam="table", slot="center", seats=True, rug=True),
                                 dict(fam="wall_decor", slot="decor")],
                        fill=[dict(fam="shelves", slot="wall", at="center", clear=1.4, max=1),
                              dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                              dict(fam="bench", slot="wall", at="center", clear=0, max=1)]),
    "kitchen": dict(purpose="where food is cooked and kept: the hearth with the cooking cauldron beside it, a table "
                            "with a meal set out and stools round it, provisions on shelves, sacks and barrels of "
                            "supplies along the walls",
                    core={"fireplace": (1, 1), "stove": (1, 1), "table": (1, 1), "storage": (2, 10)},
                    optional={"shelves": (1.0, 2), "chair": (1.0, 3)},
                    types={"storage": r"Crate|(?<!Powder)Barrel$|(?<!Powder)Barrel\d|PiledBarrels|Sack|TraderAppleCrate$",
                           "table": r"RoundTableWithFood|^Table4$", "shelves": r"^LogShelvesFull\d$",
                           "chair": r"^Stool\d$"},
                    prefer={"fireplace": {"WallFireplace3": 1, "WallFireplace4": 1},
                            "stove": {"CauldronAnimated": 3, "Stove05": 1},
                            "table": {"RoundTableWithFood": 5, "Table4": 1},
                            "storage": {"Barrel": 3, "Barrel2": 2, "TraderAppleCrate": 2, "SackChestLarge1": 1, "Crate1": 1}},
                    compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4),
                             dict(fam="stove", slot="wall", at="corner", clear=1.4, beside="fireplace", gap=2.0),
                             dict(fam="table", slot="center", seats=True),
                             dict(fam="storage", slot="stock", coverage=0.25, kinds=("sacks", "barrels", "shelves", "apples"),
                                  pad=1.3)],
                    fill=[dict(fam="storage", slot="stock", coverage=0.35, kinds=("barrels", "sacks", "apples"), pad=1.3, max=4),
                          dict(fam="shelves", slot="wall", at="center", clear=1.4, max=1)]),
    "herbalist": dict(purpose="an herb-lore room: one wall lined with shelves of potions and remedies, a bubbling "
                              "cauldron in a corner, a work table with a stool, sacks of herbs, herbs growing in pots",
                      base="study",
                      core={"shelves": (3, 8), "stove": (1, 1), "table": (1, 1), "chair": (1, 2)},
                      optional={"storage": (1.0, 4), "plant": (1.0, 3), "wall_decor": (0.6, 2)},
                      types={"shelves": r"^PotionShelves\d$|^Bookcase\d$", "stove": r"^Cauldron",
                             "storage": r"^Chest\d|^SackChest|(?<!Powder)Barrel$|(?<!Powder)Barrel\d", "plant": r"^(Plant4|Plant5)$"},
                      prefer={"shelves": {"PotionShelves1": 1, "PotionShelves2": 1, "PotionShelves3": 1, "PotionShelves4": 1},
                              "stove": {"CauldronAnimated": 1}, "table": {"Table4": 1, "SquareTable1": 1}},
                      compose=[dict(fam="shelves", slot="shelf_wall", cover=0.9),
                               dict(fam="stove", slot="wall", at="corner", clear=1.6),
                               dict(fam="table", slot="center", seats=True),
                               dict(fam="storage", slot="stock", coverage=0.2, kinds=("sacks", "barrels"), pad=1.2)],
                      fill=[dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2),
                            dict(fam="storage", slot="stock", coverage=0.3, kinds=("sacks",), pad=1.2, max=4),
                            dict(fam="shelves", slot="wall", at="center", clear=1.4, max=2)]),
    "ore_store": dict(purpose="mana ore waiting to be hauled: loaded carts spaced along the walls with room to move "
                              "them, crates and barrels of tools between",
                      base="storeroom",
                      core={"cart": (2, 3), "storage": (2, 8)},
                      optional={},
                      types={"storage": r"Crate|(?<!Powder)Barrel$|(?<!Powder)Barrel\d|BarrelWithTools|Sack"},
                      prefer={"cart": {"MineManaCart1": 2, "MineManaCart2": 2, "MineOreCart1": 1, "MineOreCart2": 1},
                              "storage": {"DarkCrate1": 2, "DarkCrate2": 2, "BarrelWithTools1": 1, "Barrel": 1}},
                      compose=[dict(fam="cart", slot="wall", at="any", clear=1.2),
                               dict(fam="storage", slot="stock", coverage=0.45, kinds=("crates", "tools", "barrels"), pad=1.4)],
                      fill=[dict(fam="storage", slot="stock", coverage=0.6, kinds=("crates", "barrels", "sacks"), pad=1.4)]),
    "tavern": dict(purpose="the public drinking room: a long bar with kegs behind it, tables crowded with stools, "
                           "a hearth, things on the walls",
                   core={"counter_bar": (1, 1), "table": (3, 8), "chair": (6, 24), "storage": (3, 6)},
                   per_tiles={"table": 28},
                   optional={"fireplace": (0.8, 1), "bench": (0.6, 3), "wall_decor": (0.8, 3), "rug": (0.3, 1)},
                   types={"storage": r"(?<!Powder)Barrel$|(?<!Powder)Barrel\d|PiledBarrels|LargeBarrel",
                          "table": r"RoundTable|^Table\d$|SquareTable", "chair": r"Stool|Chair"}),
    "mess_hall": dict(purpose="where a crew eats together: long tables in rows with a bench along each side, a hearth "
                              "to warm the room, shelves of crockery, benches along the walls, trophies on the walls",
                      base="dining_hall",
                      core={"fireplace": (1, 1), "table": (2, 6), "bench": (4, 14), "shelves": (2, 4)},
                      per_tiles={"table": 14},
                      optional={"wall_decor": (1.0, 4)},
                      types={"table": r"^Table[1-4]$", "bench": r"^Bench[1245]$|^LightBench[12]$",
                             "chair": r"Stool|Chair", "shelves": r"^LogShelvesFull\d$"},
                      prefer={"fireplace": {"Fireplace1": 1, "Fireplace2": 1, "Fireplace3": 2, "Fireplace4": 1}},
                      compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4),
                               dict(fam="table", slot="table_rows", seat="bench"),
                               dict(fam="shelves", slot="wall", at="center", clear=1.4, n=1),
                               dict(fam="shelves", slot="wall", beside="shelves", gap=0.15, clear=1.4),
                               dict(fam="wall_decor", slot="decor")],
                      fill=[dict(fam="bench", slot="wall", at="center", clear=0, max=3),
                            dict(fam="shelves", slot="wall", at="center", clear=1.4, max=3)]),
    "dining_hall": dict(purpose="a household's dining room: one long table",
                        core={"table": (1, 2), "chair": (4, 8)},
                        optional={"fireplace": (0.6, 1), "rug": (0.6, 1), "wall_decor": (0.6, 3), "shelves": (0.3, 1)},
                        compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4),
                                 dict(fam="shelves", slot="wall", at="center", clear=1.4),
                                 dict(fam="table", slot="center", seats=True),
                                 dict(fam="rug", slot="center"),
                                 dict(fam="wall_decor", slot="decor")]),
    "shop": dict(purpose="a trader's counter with goods on racks",
                 core={"counter_shop": (1, 1), "shop_rack": (2, 4)},
                 optional={"storage": (0.8, 3), "shelves": (0.5, 2)},
                 types={"storage": r"Crate|(?<!Powder)Barrel$|(?<!Powder)Barrel\d|Sack|Chest\d"}),
    "storeroom": dict(purpose="goods kept in good order: shelves of provisions, heaps of barrels and sacks in the "
                              "corners, crates side by side, the middle left clear to carry things in and out",
                      core={"storage": (4, 20)},
                      optional={"shelves": (1.0, 4)},
                      types={"storage": r"Crate|(?<!Powder)Barrel$|(?<!Powder)Barrel\d|PiledBarrels|Sack",
                             "shelves": r"^LogShelvesFull\d$"},
                      compose=[dict(fam="storage", slot="stock", coverage=0.85, kinds=("shelves", "crates", "barrels", "sacks"))],
                      fill=[dict(fam="storage", slot="stack", n=3, once=True),
                            dict(fam="storage", slot="stock", coverage=1.0, kinds=("barrels", "sacks", "crates"), pad=0.3)]),
    "smithy": dict(purpose="the forge: glowing coals with the bellows beside them, the anvil before the fire, "
                           "water to quench the iron, barrels of tools, finished weapons on racks",
                   core={"forge": (1, 1), "bellows": (1, 1), "anvil": (1, 1), "storage": (2, 3)},
                   optional={"shop_rack": (0.75, 2)},
                   types={"storage": r"WaterBarrel|BarrelWithTools\d$|DarkCrate\d", "shop_rack": r"^TraderPoleArm\d|^TraderHangingSwords\d"},
                   prefer={"forge": {"CinderBin2": 1, "CinderBin1": 1},
                           "bellows": {"Bellows3": 1, "Bellows4": 1, "Bellows6": 1},
                           "anvil": {"Anvil2": 1, "Anvil6": 1, "Anvil7": 1, "Anvil8": 1},
                           "storage": {"WaterBarrel": 2, "BarrelWithTools1": 1, "BarrelWithTools2": 1, "DarkCrate1": 1},
                           "shop_rack": {"TraderPoleArm1": 1, "TraderPoleArm2": 1, "TraderPoleArm3": 1, "TraderPoleArm4": 1}},
                   compose=[dict(fam="forge", slot="wall", at="center", clear=2.4),
                            dict(fam="bellows", slot="wall", at="corner", beside="forge", clear=0),
                            dict(fam="anvil", slot="before", of="forge", gap=2.4),
                            dict(fam="storage", slot="wall", at="corner", group=True),
                            dict(fam="shop_rack", slot="wall", at="center", clear=1.2)]),
    "study": dict(purpose="a desk to write at with its chair, books lining a wall, a chest, a rug, hangings on the walls",
                  core={"desk": (1, 1), "shelves": (2, 8), "storage": (1, 2)},
                  optional={"rug": (0.8, 1), "wall_decor": (1.0, 2), "plant": (0.5, 1), "table": (0.7, 1), "chair": (0.7, 3)},
                  types={"storage": r"^Chest\d", "shelves": r"^Bookcase\d$", "plant": r"^(Plant4|Plant5)$", "table": r"^RoundTable[12]$|^SquareTable[12]$"},
                  compose=[dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                           dict(fam="shelves", slot="shelf_wall", cover=0.6),
                           dict(fam="storage", slot="wall", at="center", clear=2.3),
                           dict(fam="wall_decor", slot="decor")],
                  fill=[dict(fam="table", slot="center", seats=True, once=True, rug=True),
                        dict(fam="shelves", slot="wall", at="center", clear=1.4, max=3),
                        dict(fam="storage", slot="wall", at="center", clear=1.6, max=1),
                        dict(fam="plant", slot="wall", at="room_corner", clear=0, max=2)]),
    "library": dict(purpose="shelves of books along the walls with a reading table in the middle",
                    core={"shelves": (3, 8)},
                    optional={"desk": (0.5, 1), "table": (0.6, 1), "chair": (0.7, 2), "rug": (0.6, 1), "fireplace": (0.25, 1)},
                    compose=[dict(fam="shelves", slot="wall", at="center", clear=1.4),
                             dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                             dict(fam="table", slot="center", seats=True),
                             dict(fam="rug", slot="center")]),
    "barracks": dict(purpose="bunks for a crew: beds of one kind spaced along the walls, a nightstand between "
                             "neighbours, a chest at each bed's foot, rugs along the aisle, shelves for their gear, a "
                             "table with its seats, hangings on the walls",
                     core={"bed": (2, 6), "storage": (0, 8), "shelves": (2, 3)}, per_tiles={"bed": 15},
                     optional={"table": (0.6, 1), "chair": (0.6, 4), "rug": (1.0, 3), "wall_decor": (1.0, 3),
                               "nightstand": (1.0, 4)},
                     types={"storage": r"^Chest\d$", "bed": r"^Cot\d|^WoodBed\d|^Bed\d",
                            "shelves": r"^LogShelvesFull\d$|^Bookcase\d$", "chair": r"Stool|Chair"},
                     prefer={"bed": {"Cot1": 2, "Cot4": 1, "WoodBed2": 1},
                             "rug": {"RedRug1": 1, "RedRug2": 1, "RedRug3": 1, "RedRug4": 1, "BearskinRug1": 1},
                             "shelves": {"LogShelvesFull1": 1, "LogShelvesFull2": 1, "LogShelvesFull3": 1, "LogShelvesFull4": 1}},
                     compose=[dict(fam="bed", slot="bed_row"),
                              dict(fam="shelves", slot="wall", at="center", clear=1.4, n=1),
                              dict(fam="shelves", slot="wall", beside="shelves", gap=0.15, clear=1.4),
                              dict(fam="table", slot="center", seats=True),
                              dict(fam="wall_decor", slot="decor")],
                     fill=[dict(fam="shelves", slot="wall", at="center", clear=1.4, max=1),
                           dict(fam="storage", slot="wall", at="center", clear=1.6, max=1)]),
    "laboratory": dict(purpose="a mage's workbenches and apparatus",
                       core={"lab": (2, 4)},
                       optional={"shelves": (0.7, 2), "desk": (0.4, 1), "table": (0.3, 1), "storage": (0.3, 1)},
                       types={"storage": r"^Chest\d"}),
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
                      rooms=[("barracks", "the miners' bunks"), ("storeroom", "their gear")],
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


# The Westwood room kind each generated kind is measured against (furniture counts, validate/baseline.json).
WESTWOOD_KIND = {"herbalist": "laboratory", "mess_hall": "dining_hall", "ore_store": "storeroom", "study": "library",
                 "dwelling": "living_room"}


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
