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
    "bedroom": dict(purpose="where someone sleeps: the bed, a chest for belongings with a rug before it, shelves",
                    core={"bed": (1, 1)},
                    optional={"rug": (0.9, 1), "nightstand": (0.8, 1), "storage": (0.9, 1), "shelves": (0.7, 1),
                              "wall_decor": (0.6, 2), "desk": (0.25, 1)},
                    types={"storage": CHEST, "shelves": r"Bookcase|Shelves"},
                    compose=[dict(fam="bed", slot="wall", at="any", clear=1.0),
                             dict(fam="storage", slot="wall", at="center", clear=2.3, rug=True),
                             dict(fam="shelves", slot="wall", at="center", clear=1.4),
                             dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                             dict(fam="rug", slot="center"),
                             dict(fam="wall_decor", slot="decor")]),
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
    "living_room": dict(purpose="the household's hearth room: the hearth with a rug before it, one table to eat and sit at",
                        core={"table": (1, 1), "chair": (2, 4)},
                        optional={"fireplace": (0.75, 1), "rug": (0.75, 1), "shelves": (0.5, 1), "storage": (0.4, 1),
                                  "wall_decor": (0.5, 2), "bench": (0.3, 1)},
                        types={"storage": CHEST + "|^WaterBarrel$"},
                        prefer={"fireplace": {"Fireplace4": 1, "Fireplace3": 1}},
                        compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4, rug=True),
                                 dict(fam="shelves", slot="wall", at="center", clear=1.4),
                                 dict(fam="storage", slot="wall", at="center", clear=2.3, rug=True),
                                 dict(fam="bench", slot="wall", at="center", clear=0),
                                 dict(fam="table", slot="center", seats=True),
                                 dict(fam="rug", slot="center"),
                                 dict(fam="wall_decor", slot="decor")]),
    "kitchen": dict(purpose="where food is cooked and kept: the hearth with the cooking cauldron beside it, a work "
                            "table with food set out, supplies in a row along the wall",
                    core={"fireplace": (1, 1), "stove": (1, 1), "table": (1, 1), "storage": (2, 4)},
                    optional={"shelves": (0.6, 1), "chair": (0.6, 2)},
                    types={"storage": r"Barrel$|Barrel\d|Crate|Sack|TraderAppleCrate$",
                           "table": r"RoundTableWithFood|^Table\d$|SquareTable|RoundTable\d"},
                    prefer={"fireplace": {"WallFireplace3": 1, "WallFireplace4": 1},
                            "stove": {"CauldronAnimated": 3, "Stove05": 1},
                            "table": {"RoundTableWithFood": 2, "Table4": 1, "SquareTable1": 1, "Table1": 1},
                            "storage": {"Barrel": 3, "Barrel2": 2, "TraderAppleCrate": 2, "SackChestLarge1": 1, "Crate1": 1}},
                    compose=[dict(fam="fireplace", slot="wall", at="center", clear=2.4),
                             dict(fam="stove", slot="wall", at="corner", clear=1.4, beside="fireplace"),
                             dict(fam="shelves", slot="wall", at="center", clear=1.4),
                             dict(fam="storage", slot="wall", at="corner", group=True),
                             dict(fam="table", slot="center", seats=True, food=True)]),
    "tavern": dict(purpose="the public drinking room: a long bar with kegs behind it, tables crowded with stools, "
                           "a hearth, things on the walls",
                   core={"counter_bar": (1, 1), "table": (3, 8), "chair": (6, 24), "storage": (3, 6)},
                   per_tiles={"table": 28},
                   optional={"fireplace": (0.8, 1), "bench": (0.6, 3), "wall_decor": (0.8, 3), "rug": (0.3, 1)},
                   types={"storage": r"Barrel$|Barrel\d|PiledBarrels|LargeBarrel",
                          "table": r"RoundTable|^Table\d$|SquareTable", "chair": r"Stool|Chair"}),
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
                 types={"storage": r"Crate|Barrel$|Barrel\d|Sack|Chest\d"}),
    "storeroom": dict(purpose="goods kept in crates, barrels and sacks, stacked in rows along the walls",
                      core={"storage": (3, 6)},
                      optional={"shelves": (0.5, 2)},
                      types={"storage": r"Crate|Barrel$|Barrel\d|Sack|PiledBarrels"},
                      compose=[dict(fam="storage", slot="wall", at="corner", group=True),
                               dict(fam="shelves", slot="wall", at="center", clear=1.2)]),
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
    "study": dict(purpose="a desk to write at, books on shelves",
                  core={"desk": (1, 1), "shelves": (1, 3)},
                  optional={"rug": (0.6, 1), "storage": (0.4, 1), "wall_decor": (0.4, 1)},
                  types={"storage": r"^Chest\d"},
                  compose=[dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                           dict(fam="shelves", slot="wall", at="center", clear=1.4),
                           dict(fam="storage", slot="wall", at="center", clear=2.3),
                           dict(fam="rug", slot="center"),
                           dict(fam="wall_decor", slot="decor")]),
    "library": dict(purpose="shelves of books along the walls with a reading table in the middle",
                    core={"shelves": (3, 8)},
                    optional={"desk": (0.5, 1), "table": (0.6, 1), "chair": (0.7, 2), "rug": (0.6, 1), "fireplace": (0.25, 1)},
                    compose=[dict(fam="shelves", slot="wall", at="center", clear=1.4),
                             dict(fam="desk", slot="wall", at="center", clear=0, seats=True),
                             dict(fam="table", slot="center", seats=True),
                             dict(fam="rug", slot="center")]),
    "barracks": dict(purpose="beds for several people and their chests",
                     core={"bed": (2, 6)},
                     optional={"storage": (0.8, 3), "table": (0.5, 1), "chair": (0.4, 2), "wall_decor": (0.3, 1)},
                     types={"storage": r"^Chest\d|^Chest[NS][EW]$"}),
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
