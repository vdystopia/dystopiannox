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
# allowed object types. Families are rules/room_types.py's (seats are placed with their tables).
ROOMS = {
    "bedroom": dict(purpose="where someone sleeps",
                    core={"bed": (1, 1)},
                    optional={"rug": (0.9, 1), "nightstand": (0.8, 1), "storage": (0.85, 1), "shelves": (0.7, 1),
                              "wall_decor": (0.6, 2), "chair": (0.3, 1)},
                    types={"storage": r"^Chest\d|^Chest[NS][EW]$", "shelves": r"Bookcase|Shelves"}),
    "dwelling": dict(purpose="a one-room home: bed, hearth, a table to eat at, a chest for belongings",
                     base="living_room",
                     core={"bed": (1, 1), "table": (1, 1), "chair": (1, 2), "storage": (1, 1)},
                     optional={"fireplace": (0.7, 1), "rug": (0.7, 1), "shelves": (0.6, 1), "wall_decor": (0.5, 1)},
                     types={"storage": r"^Chest\d|^Chest[NS][EW]$"}),
    "living_room": dict(purpose="the household's hearth room: one table to eat and sit at",
                        core={"table": (1, 1), "chair": (2, 4)},
                        optional={"fireplace": (0.7, 1), "rug": (0.7, 1), "shelves": (0.5, 1), "storage": (0.4, 1),
                                  "wall_decor": (0.5, 2), "bench": (0.3, 1)},
                        types={"storage": r"^Chest\d|^Chest[NS][EW]$"}),
    "kitchen": dict(purpose="where food is cooked and kept",
                    core={"stove": (1, 1), "table": (1, 1)},
                    optional={"storage": (0.9, 3), "shelves": (0.6, 1), "clutter": (0.7, 3), "chair": (0.4, 1)},
                    types={"storage": r"Barrel$|Barrel\d|Crate|Sack", "clutter": r"Meat|Food|Bread|Cheese|Apple|Cabbage|Bottle|Mug|Bucket"}),
    "tavern": dict(purpose="the public drinking room: a bar with barrels, tables to sit at",
                   core={"counter_bar": (1, 1), "table": (2, 5), "chair": (4, 14)}, per_tiles={"table": 35},
                   optional={"storage": (0.9, 3), "fireplace": (0.6, 1), "bench": (0.4, 2), "wall_decor": (0.6, 2), "rug": (0.3, 1)},
                   types={"storage": r"Barrel$|Barrel\d|PiledBarrels"}),
    "dining_hall": dict(purpose="a household's dining room: one long table",
                        core={"table": (1, 2), "chair": (4, 8)},
                        optional={"fireplace": (0.6, 1), "rug": (0.6, 1), "wall_decor": (0.6, 3), "shelves": (0.3, 1)}),
    "shop": dict(purpose="a trader's counter with goods on racks",
                 core={"counter_shop": (1, 1), "shop_rack": (2, 4)},
                 optional={"storage": (0.8, 3), "shelves": (0.5, 2)},
                 types={"storage": r"Crate|Barrel$|Barrel\d|Sack|Chest\d"}),
    "storeroom": dict(purpose="goods kept in crates, barrels and sacks",
                      core={"storage": (3, 6)},
                      optional={"shelves": (0.5, 2)},
                      types={"storage": r"Crate|Barrel$|Barrel\d|Sack|PiledBarrels"}),
    "smithy": dict(purpose="the forge: anvil, bellows and a water barrel",
                   core={"smithy": (2, 3)},
                   optional={"storage": (0.8, 2), "shelves": (0.3, 1)},
                   types={"storage": r"WaterBarrel|Barrel$|Barrel\d|BarrelWithTools"}),
    "study": dict(purpose="a desk to write at, books on shelves",
                  core={"desk": (1, 1), "shelves": (1, 3)},
                  optional={"chair": (0.8, 1), "rug": (0.6, 1), "storage": (0.4, 1), "wall_decor": (0.4, 1)},
                  types={"storage": r"^Chest\d"}),
    "library": dict(purpose="shelves of books with a reading table",
                    core={"shelves": (3, 8)},
                    optional={"desk": (0.5, 1), "table": (0.5, 1), "chair": (0.7, 2), "rug": (0.6, 1)}),
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
