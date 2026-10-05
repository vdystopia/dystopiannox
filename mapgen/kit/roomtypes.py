"""Room types: what makes each kind of room good, as data the furnisher and the room score both read.

There is no one-size-fits-all room (Starwell playtest, 2026-10-05: "Different rooms have different dynamics and
identities. What made that room good was the fact that it had everything a study should have and in the right
arrangement. A throne room, however, is very different than a study and should, by its nature, be more open with less
object density"). Each type has its own brief (rules/rooms/<type>.md: purpose, focal point, pieces, composition,
density, mistakes, examples) and its own profile here. The kit's 27 room kinds (kit/identity.py ROOMS, each with its
recipe) map onto 19 types; a culture's kind (an ogre den, the Land of the Dead's chapel) is a variant of its type.

A profile holds:
- family: the structural family (FAMILIES): private, work, stores, public, ceremonial, martial, the dead;
- feel: "full" (cosy, every wall used), "balanced", or "open" (processional: floor to walk, few pieces, each placed);
- focal: the piece the room is arranged round: family, types (regex), where it stands ("back": against the NE or NW
  wall the camera sees; "door": on the wall across from a door, facing it; "middle"), and what flanks it;
- must: family -> least pieces; never: families that never belong (and never_types, a regex of object types);
- walls: what each wall and the middle do (the brief's composition, as text; the score checks walls_min and lined);
- cover (lo, target, hi): the share of the floor the furniture covers. The furnisher fills toward the target and never
  past hi (kit/identity.py ROOM_COVER is built from these); the score asks lo..hi;
- open (lo, hi): the share of the floor more than 1.2 units from every blocking piece (review/roommeasure.py);
- per_tile (lo, hi): furnishings per floor tile; types_min: distinct object types (variety: character);
- free_most (least, tiles per): the most pieces of one stand-alone kind (not the kinds that line walls or stand in
  rows, nor the families capped below, nor the seats of free_skip: chairs at their tables, by default): at most
  max(least, tiles / tiles per). A tavern counts its seats (2026-10-05: "too many of the same object (chapel benches,
  tavern tables and chairs)"), so its free_skip is empty;
- caps: family -> (floor tiles per piece, most): a large room's repeated set stops there (kit/identity.py
  ROOMS[kind]["repeat"] takes these; the furnisher holds them, the score checks them);
- walls_min: walls with a purpose; lined: least share of the back walls lined (None: the type does not line walls);
- tiles (lo, hi): the size the type wants (floor tiles inside the walls);
- signature: what the room reads as from its contents: family or ^type-regex -> (weight per piece, most counted), and
  needs: the families without which it is not this type at all. reads_as() ranks the types; the score flags a room that
  reads as another type (the college laboratory that looked like "some sort of shoddy mess hall");
- kin: types it may read as without losing its identity (a study rich in books reads as a library);
- westwood: rules/rooms/westwood.json types its numbers were measured on (n rooms each, in the brief);
- supplies_line: True where barrels, crates and sacks may line a wall corner to corner (a store); monotony: the
  share of a big room's furniture one kind may be before the checker calls it monotonous (validate/checks.py
  identity_flags reads both; default 0.6);
- fixed_top_up: families the furnisher's top-up does not multiply with the room's size (a lord's chamber takes one or
  two chests, not five);
- variants: kit kind -> overrides for a culture or a smaller sibling (an ogre den is a barracks of straw).

The ranges stand on Westwood's rooms of the type (rules/rooms/westwood.py), the playtester's verdicts and our own
praised rooms. Our rooms are fuller and bigger than Westwood's by the user's choice (TreePlace reviews: rooms at
Westwood's median read as empty), except where the type is open by nature.
"""
import re

FAMILIES = {
    "private": "rooms one person or a household lives in: cosy and full, every wall used, one group in the middle",
    "work": "rooms of a craft or of learning: the work station is the focus, tools and stock along the walls, zones",
    "stores": "rooms that keep things: stocked walls, tidy rows, aisles to walk; full by nature",
    "public": "rooms many people use at once: sets of tables or a counter, open floor to move between them",
    "ceremonial": "rooms of state and worship: open and processional, a way from the door to the focus, few pieces "
                  "each placed for effect, symmetry",
    "martial": "a garrison's rooms: rows of one kind (bunks, racks), orderly, the gear on show",
    "dead": "the dead's rooms: rows of tombs with aisles, quiet, sparse, the walls bare but for a few hangings",
}

# The order is the brief's ranking: how common the type is in Westwood's buildings (rules/rooms/westwood.json, rooms
# counted once across the three campaigns) and in our designs.
TYPES = {
    # ---- private -------------------------------------------------------------------------------------------------
    "bedroom": dict(
        family="private", feel="full", fixed_top_up=("storage", "bench"), kinds=("bedroom",), westwood=("bedroom",),
        focal=dict(fam="bed", types=r"^(Bed\d|WoodBed\d|Cot\d)", where="back"),
        must={"bed": 1, "storage": 1}, never=("counter_bar", "counter_shop", "stove", "smithy", "altar",
                                              "throne", "tomb", "shop_rack", "straw"),
        never_types=r"Barrel|Crate|Sack",
        walls=dict(back="the bed, headboard to a back wall, its nightstand beside it; a run of shelves end to end",
                   other_back="the chest snug and centred with a rug before it; hangings",
                   front="a desk or a small table and chair; a bench", middle="a rug, or a carpet; kept clear to walk"),
        cover=(0.08, 0.14, 0.28), open=(0.30, 0.80), per_tile=(0.25, 1.0), types_min=8, free_most=(3, 20),
        caps={"table": (12, 3)}, walls_min=3, lined=0.25, tiles=(14, 60),
        signature={"bed": (6, 2), "nightstand": (1, 2), "^Chest": (0.5, 1), "desk": (0.5, 1)}, needs=("bed",),
        kin=("living_room", "study")),
    "study": dict(
        family="private", feel="full", fixed_top_up=("storage", "bench"), kinds=("study",), westwood=("study", "library"),
        focal=dict(fam="desk", types=r"^Desk\d$", where="back"),
        must={"desk": 1, "shelves": 2, "storage": 1}, never=("bed", "stove", "smithy", "counter_bar", "counter_shop",
                                                               "shop_rack", "altar", "throne", "tomb", "straw"),
        never_types=r"Barrel|Crate|Sack|^Table[1-4]$",
        walls=dict(back="the desk centred with its chair, bookcases either side of it to the corners",
                   other_back="bookcases end to end with a hanging between, the chest",
                   front="statues between candelabras, plants in the front corners",
                   middle="one group that shows the use: a round table and two chairs on a carpet; one curio free"),
        cover=(0.09, 0.17, 0.30), open=(0.32, 0.85), per_tile=(0.25, 0.9), types_min=12, free_most=(3, 25),
        caps={}, walls_min=4, lined=0.35, tiles=(30, 120),
        signature={"desk": (6, 1), "shelves": (0.4, 10), "table": (1, 1), "lab": (0.5, 2)}, needs=("desk",),
        kin=("library", "laboratory")),
    "living_room": dict(
        family="private", feel="full", fixed_top_up=("storage", "bench"), kinds=("living_room", "dwelling"), westwood=("living_room",),
        focal=dict(fam="fireplace", types=r"Fireplace", where="back"),
        must={"fireplace": 1, "table": 1}, never=("counter_bar", "counter_shop", "smithy", "altar", "throne", "tomb",
                                                  "shop_rack", "lab", "straw"),
        never_types=r"PowderBarrel",
        walls=dict(back="the hearth centred, shelves end to end either side of it, a rug before it",
                   other_back="shelves end to end with trophies between, the chest",
                   front="a bench; plants in the corners", middle="the table with its chairs, on a carpet"),
        cover=(0.10, 0.17, 0.30), open=(0.30, 0.80), per_tile=(0.25, 0.9), types_min=9, free_most=(4, 20),
        caps={}, walls_min=3, lined=0.30, tiles=(20, 90),
        signature={"fireplace": (3, 1), "table": (2, 1), "chair": (0.5, 4), "shelves": (0.2, 6), "bench": (0.5, 2)},
        needs=("fireplace", "table"), kin=("bedroom", "dining_hall", "kitchen"),
        variants={"dwelling": dict(must={"fireplace": 1, "table": 1, "bed": 1}, never=("counter_bar", "counter_shop",
                                   "smithy", "altar", "throne", "tomb", "shop_rack", "lab", "straw"),
                                   cover=(0.12, 0.16, 0.30), open=(0.22, 0.80))}),
    # ---- work ----------------------------------------------------------------------------------------------------
    "kitchen": dict(
        family="work", feel="full", supplies_line=True, kinds=("kitchen",), westwood=("kitchen",),
        focal=dict(fam="fireplace", types=r"Fireplace", where="back", with_="stove"),
        must={"stove": 1, "storage": 4, "table": 1}, never=("bed", "desk", "altar", "throne", "tomb", "lab", "counter_bar",
                                                            "counter_shop", "smithy", "statue", "column"),
        never_types=r"^Bookcase|PowderBarrel",
        walls=dict(back="the hearth centred, the cauldron two units from it toward a corner",
                   other_back="log shelves of provisions end to end",
                   front="sacks, barrels, crates and apples in heaps and rows",
                   middle="a work table with its food and stools; a clear way from the hearth to the door"),
        cover=(0.15, 0.21, 0.32), open=(0.22, 0.65), per_tile=(0.3, 1.0), types_min=8, free_most=(3, 15),
        caps={}, walls_min=3, lined=0.30, tiles=(20, 80),
        signature={"stove": (5, 2), "storage": (0.3, 12), "table": (0.5, 1), "fireplace": (1, 1)}, needs=("stove",),
        kin=("storeroom", "herbalist")),
    "laboratory": dict(
        family="work", feel="balanced", kinds=("laboratory",), westwood=("laboratory",),
        focal=dict(fam="lab", types=r"^WizardWorkstation|^AlchemistDesk", where="back"),
        must={"lab": 3, "shelves": 2, "desk": 1}, never=("bed", "counter_bar", "counter_shop", "smithy",
                                                         "altar", "throne", "tomb", "straw", "bench"),
        never_types=r"^RoundTableWithFood$|^RoundTable\d|^OvalTable|Barrel|Crate|Sack",
        walls=dict(back="the study end: the desk near a corner with bookcases either side",
                   other_back="the work wall: a short bench of workstations of three kinds, a hanging between, one "
                              "alchemist's desk, a pair of potion shelves",
                   front="statues; a chest", middle="the alchemist's work table with stools and the cauldron; a "
                                                    "conjuring circle; generators apart"),
        cover=(0.08, 0.17, 0.30), open=(0.40, 0.85), per_tile=(0.2, 0.7), types_min=12, free_most=(2, 60),
        caps={"lab": (12, 10), "table": (1, 1)}, walls_min=3, lined=0.30, tiles=(30, 140),
        signature={"lab": (3, 5), "^AlchemistDesk|^WizardWorkstation|^Vandegraf": (1, 3), "desk": (1, 1),
                   "shelves": (0.2, 8)}, needs=("lab",), kin=("study", "library", "herbalist")),
    "herbalist": dict(
        family="work", feel="full", kinds=("herbalist",), westwood=("herbalist", "laboratory"),
        focal=dict(fam="stove", types=r"^Cauldron", where="any"),
        must={"stove": 1, "shelves": 3, "table": 1}, never=("bed", "counter_bar", "counter_shop", "smithy", "altar",
                                                            "throne", "tomb", "straw", "column"),
        never_types=r"PowderBarrel|^Crate",
        walls=dict(back="a pair of potion shelves; books of remedies end to end", other_back="the cauldron toward a corner",
                   front="sacks of herbs; pots of herbs in the corners", middle="the work table with its stool"),
        cover=(0.12, 0.17, 0.30), open=(0.30, 0.80), per_tile=(0.25, 0.9), types_min=10, free_most=(3, 20),
        caps={}, walls_min=3, lined=0.35, tiles=(25, 90),
        signature={"^PotionShelves": (2, 2), "^Cauldron": (3, 1), "shelves": (0.2, 8), "plant": (0.3, 3),
                   "lab": (0.5, 2)}, needs=("stove", "shelves"), kin=("kitchen", "laboratory", "study")),
    "library": dict(
        family="work", feel="full", kinds=("library",), westwood=("library",),
        focal=dict(fam="shelves", types=r"^Bookcase", where="back"),
        must={"shelves": 6, "table": 1}, never=("bed", "stove", "smithy", "counter_bar", "counter_shop", "shop_rack",
                                                "altar", "throne", "tomb", "straw"),
        never_types=r"Barrel|Crate|Sack",
        walls=dict(back="bookcases end to end, the desk among them", other_back="bookcases end to end",
                   front="a statue or a plant", middle="stacks of bookcases in rows in a big library; the reading "
                                                       "table on a carpet; a curio"),
        cover=(0.10, 0.17, 0.32), open=(0.30, 0.80), per_tile=(0.25, 0.9), types_min=8, free_most=(3, 40),
        caps={}, walls_min=3, lined=0.50, tiles=(30, 200),
        signature={"shelves": (0.6, 30), "table": (1, 2), "desk": (1, 1)}, needs=("shelves",),
        kin=("study", "laboratory")),
    "smithy": dict(
        family="work", feel="balanced", kinds=("smithy",), westwood=("smithy",),
        focal=dict(fam=None, types=r"^CinderBin", where="back", with_="Anvil"),
        must={"smithy": 2, "storage": 2, "counter_shop": 1}, never=("bed", "desk", "altar", "throne", "tomb", "lab",
                                                                     "counter_bar", "rug", "plant"),
        never_types=r"^Bookcase|PowderBarrel",
        walls=dict(back="the forge's coals centred, the bellows beside them, the anvil before them",
                   other_back="swords and pole arms on racks", front="water and tool barrels, crates of iron",
                   middle="the counter out from a back wall with the smith behind it; a row of armour, a row of arms"),
        cover=(0.10, 0.24, 0.38), open=(0.25, 0.80), per_tile=(0.2, 0.7), types_min=10, free_most=(3, 20),
        caps={}, walls_min=3, lined=None, tiles=(30, 110),
        signature={"smithy": (4, 3), "^CinderBin": (4, 1), "counter_shop": (1, 1), "shop_rack": (0.2, 6)},
        needs=("smithy",), kin=("shop", "armoury")),
    # ---- stores --------------------------------------------------------------------------------------------------
    "storeroom": dict(
        family="stores", feel="full", supplies_line=True, kinds=("storeroom", "ore_store", "ogre_hoard"), westwood=("storeroom",),
        focal=None,
        must={"storage": 4}, never=("bed", "desk", "table", "chair", "altar", "throne", "tomb", "lab", "counter_bar",
                                    "counter_shop", "fireplace", "stove", "statue"),
        never_types=r"^Bookcase|PowderBarrel",
        walls=dict(back="stocked log shelves end to end", other_back="crates side by side",
                   front="heaps of barrels and sacks in the corners", middle="clear, or one row of racks with aisles"),
        cover=(0.15, 0.30, 0.42), open=(0.15, 0.65), per_tile=(0.3, 1.1), types_min=4, free_most=(4, 20),
        caps={"shop_rack": (10, 6)}, walls_min=3, lined=0.30, tiles=(15, 90),
        signature={"storage": (0.8, 30), "^LogShelves": (0.5, 8)}, needs=("storage",),
        kin=("kitchen", "armoury"),
        variants={"ore_store": dict(must={"storage": 2, "shop_rack": 2}, cover=(0.15, 0.28, 0.42), focal=dict(fam=None, types=r"^Mine(Mana|Ore)Cart",
                                    where="any"), caps={"shop_rack": (8, 12)}),
                  "ogre_hoard": dict(lined=None, walls_min=2, cover=(0.15, 0.26, 0.42), never=("bed", "desk", "altar",
                                     "throne", "lab", "counter_bar", "counter_shop"))}),
    # ---- martial -------------------------------------------------------------------------------------------------
    "barracks": dict(
        family="martial", feel="full", kinds=("barracks", "ogre_den"), westwood=("barracks",),
        focal=dict(fam="bed", types=r"^(Cot\d|WoodBed\d|Bed\d)$", where="row"),
        must={"bed": 2}, never=("counter_bar", "counter_shop", "altar", "throne", "tomb", "lab", "smithy", "stove"),
        never_types=r"PowderBarrel",
        walls=dict(back="shelves for gear end to end; shields and trophies",
                   other_back="hangings", front="bunks of one kind in a row, a nightstand between neighbours, a chest "
                                                "a step beyond each foot", middle="a table with seats; a hearth"),
        cover=(0.12, 0.24, 0.34), open=(0.25, 0.75), per_tile=(0.2, 0.8), types_min=8, free_most=(4, 25),
        caps={"bed": (12, 12)}, walls_min=3, lined=0.30, tiles=(40, 200),
        signature={"bed": (2.5, 12), "straw": (1, 20), "nightstand": (0.3, 6)}, needs=("bed",),
        kin=("bedroom", "armoury"),
        variants={"ogre_den": dict(focal=dict(fam="fireplace", types=r"^OgreFirePit$", where="middle"),
                                   must={"straw": 4, "fireplace": 1}, lined=None, walls_min=2, types_min=6,
                                   cover=(0.10, 0.14, 0.30), needs=("straw",))}),
    "armoury": dict(
        family="martial", feel="balanced", supplies_line=True, kinds=("gear_store",), westwood=("armoury",),
        focal=dict(fam="shop_rack", types=r"^Trader(ArmorRack|PoleArm|BowRack|QuiverRack|ClothesRack)", where="rows"),
        must={"shop_rack": 3}, never=("bed", "desk", "table", "altar", "throne", "tomb", "lab", "counter_bar",
                                      "counter_shop", "stove", "fireplace"),
        never_types=r"^Bookcase|PowderBarrel",
        walls=dict(back="shelves end to end", other_back="helm shelves or hanging swords",
                   front="barrels, crates and tool barrels", middle="racks in rows of one kind each, at most five to a "
                                                                    "row, 1.2 apart, aisles of 2.2 between rows"),
        cover=(0.12, 0.24, 0.34), open=(0.25, 0.70), per_tile=(0.2, 0.8), types_min=7, free_most=(4, 25),
        caps={"shop_rack": (6, 16)}, walls_min=3, lined=0.30, tiles=(30, 120),
        signature={"shop_rack": (1.5, 12)}, needs=("shop_rack",), kin=("storeroom", "shop", "smithy")),
    # ---- public --------------------------------------------------------------------------------------------------
    "shop": dict(
        family="public", feel="balanced", kinds=("shop",), westwood=("shop",),
        focal=dict(fam="counter_shop", types=r"^TraderDesk", where="back", reach=3.6),
        must={"counter_shop": 1, "shop_rack": 2}, never=("bed", "desk", "altar", "throne", "tomb", "counter_bar",
                                                         "stove", "smithy"),
        never_types=r"PowderBarrel",
        walls=dict(back="the counter set out from a back wall, the keeper's spot behind it; trader's shelves",
                   other_back="trader's shelves of goods", front="crates of stock",
                   middle="racks for show, three to a row, a row of each kind; the floor before the counter open"),
        cover=(0.12, 0.24, 0.40), open=(0.30, 0.75), per_tile=(0.2, 0.8), types_min=9, free_most=(3, 20),
        caps={}, walls_min=3, lined=0.30, tiles=(30, 140),
        signature={"counter_shop": (8, 1), "shop_rack": (0.4, 8)}, needs=("counter_shop",),
        kin=("armoury", "smithy")),
    "tavern": dict(
        family="public", feel="balanced", kinds=("tavern",), westwood=("tavern",),
        focal=dict(fam="counter_bar", types=r"^(BarPiece|BarCorner|BarHinged)", where="any", with_="fireplace"),
        must={"counter_bar": 1, "table": 3, "fireplace": 1}, never=("bed", "desk", "altar", "throne", "tomb", "lab",
                                                                    "smithy", "counter_shop"),
        never_types=r"PowderBarrel|^Bookcase",
        walls=dict(back="the hearth centred with a rug before it and shelves of tankards beside it",
                   other_back="trophies and hangings; the bar against a wall, kegs behind it",
                   front="benches; kegs heaped toward the corners, never a whole wall of them",
                   middle="tables in three kinds of set (round tables with stools, a long table with benches, a "
                          "table of food), open floor between to walk to the bar"),
        cover=(0.10, 0.18, 0.30), open=(0.40, 0.80), per_tile=(0.15, 0.6), types_min=18, free_most=(10, 18), free_skip=(),
        caps={"table": (28, 12)}, walls_min=3, lined=0.20, tiles=(100, 360),
        signature={"counter_bar": (1, 10), "table": (0.5, 10), "chair": (0.1, 30), "storage": (0.2, 8)},
        needs=("counter_bar",), kin=("dining_hall",)),
    "dining_hall": dict(
        family="public", feel="balanced", kinds=("dining_hall", "mess_hall", "ogre_hall"), westwood=("dining_hall",),
        focal=dict(fam="table", types=r"^(Table[1-4]|OvalTable\d|OgreTable\d)$", where="rows", with_="fireplace"),
        must={"table": 2, "fireplace": 1}, never=("bed", "desk", "altar", "throne", "tomb", "lab", "smithy",
                                                  "counter_shop", "shop_rack"),
        never_types=r"PowderBarrel",
        walls=dict(back="the hearth centred, shelves of crockery either side", other_back="hangings above; a "
                                                                                         "sideboard of food",
                   front="benches; plants in the corners", middle="long tables in rows, seated along both sides"),
        cover=(0.10, 0.17, 0.32), open=(0.30, 0.80), per_tile=(0.2, 0.7), types_min=8, free_most=(4, 30), free_skip=("chair", "bench"),
        caps={"table": (16, 8)}, walls_min=3, lined=0.25, tiles=(50, 220),
        signature={"table": (1.5, 12), "chair": (0.3, 40), "bench": (0.3, 20)}, needs=("table",),
        kin=("great_hall", "tavern", "living_room"),
        variants={"mess_hall": dict(caps={"table": (17, 10)}, never_types=r"PowderBarrel|^RoundTable",
                                    cover=(0.12, 0.24, 0.34)),
                  "ogre_hall": dict(focal=dict(fam="fireplace", types=r"^OgreFirePit$", where="middle"),
                                    lined=None, walls_min=2, types_min=6, cover=(0.12, 0.17, 0.32), free_most=(6, 20),
                                    caps={"table": (22, 8)})}),
    # ---- ceremonial ----------------------------------------------------------------------------------------------
    "great_hall": dict(
        family="ceremonial", feel="open", kinds=("great_hall",), westwood=("great_hall", "hall"),
        focal=dict(fam="fireplace", types=r"Fireplace", where="back"),
        must={"table": 2, "fireplace": 1, "wall_decor": 2}, never=("bed", "desk", "stove", "smithy", "lab", "tomb",
                                                                    "counter_bar", "counter_shop", "shop_rack", "altar"),
        never_types=r"Barrel|Crate|Sack|^Bookcase",
        walls=dict(back="the hearth centred; banners and trophies", other_back="banners; a second hearth in a long hall",
                   front="a few benches; plants in the corners",
                   middle="long tables with benches down the middle on a great carpet, open floor round them and a "
                          "clear way from every door; open hearths at the ends of a long hall"),
        cover=(0.05, 0.10, 0.18), open=(0.55, 0.90), per_tile=(0.08, 0.35), types_min=10, free_most=(6, 40), free_skip=("chair", "bench"),
        caps={"bench": (11, 24), "table": (48, 6), "storage": (80, 3)}, walls_min=3, lined=None, tiles=(120, 400),
        signature={"table": (1, 6), "bench": (0.3, 24), "fireplace": (2, 2), "statue": (0.5, 4), "wall_decor": (0.2, 10)},
        needs=("table", "fireplace"), kin=("dining_hall", "hall")),
    "hall": dict(
        family="ceremonial", feel="open", kinds=("hall",), westwood=("hall",),
        focal=dict(fam="statue", types=r"^Statue|^LOTD|Gargoyle", where="any"),
        must={"column": 2, "statue": 2}, never=("bed", "desk", "stove", "smithy", "lab", "counter_bar", "counter_shop",
                                                "shop_rack", "straw"),
        never_types=r"Barrel|Crate|Sack|^Bookcase",
        walls=dict(back="hangings: shields, banners, tapestries", other_back="hangings",
                   front="benches by the walls; plants in the corners",
                   middle="a colonnade in pairs either side of a clear aisle; statues facing each other across it"),
        cover=(0.02, 0.04, 0.14), open=(0.65, 0.97), per_tile=(0.05, 0.30), types_min=6, free_most=(4, 30),
        caps={"column": (18, 10)}, walls_min=2, lined=None, tiles=(50, 260),
        signature={"column": (0.6, 10), "statue": (0.6, 6)}, needs=("column", "statue"),
        kin=("throne_room", "great_hall", "chapel")),
    "throne_room": dict(
        family="ceremonial", feel="open", kinds=("throne_room",), westwood=("throne_room", "hall"),
        focal=dict(fam="throne", types=r"^DunMirThrone|^LOTDLichThrone", where="door"),
        must={"throne": 1, "statue": 4, "wall_decor": 2, "column": 2},
        never=("bed", "desk", "stove", "smithy", "lab", "counter_bar", "counter_shop", "shop_rack", "table", "straw",
               "tomb"),
        never_types=r"Barrel|Crate|Sack|^Bookcase|Trophy",
        walls=dict(back="the throne centred on the NW wall facing the door across the room, statues flanking it, "
                        "braziers before the dais; tapestries of one colour",
                   other_back="tapestries of the same colour", front="the door, in line with the throne; a bench or "
                                                                   "two for those who wait; plants in the corners",
                   middle="a carpet runner and a clear aisle from the door to the throne; a few pairs of columns spread "
                          "down the length; pairs of statues between them facing across the aisle"),
        cover=(0.03, 0.06, 0.12), open=(0.65, 0.92), per_tile=(0.10, 0.35), types_min=9, free_most=(6, 30),
        caps={"column": (26, 8), "statue": (14, 10), "bench": (60, 2)}, walls_min=3, lined=None, tiles=(60, 260),
        signature={"throne": (12, 1)}, needs=("throne",), kin=("hall",)),
    "chapel": dict(
        family="ceremonial", feel="open", kinds=("chapel", "dark_chapel"), westwood=("chapel",),
        focal=dict(fam="altar", types=r"^DunMirAltar|^LOTDLichGodStatue", where="door"),
        must={"altar": 1, "bench": 4, "statue": 2}, never=("bed", "desk", "stove", "smithy", "lab", "counter_bar",
                                                           "counter_shop", "shop_rack", "table", "straw"),
        never_types=r"Barrel|Crate|Sack|^Bookcase|Trophy",
        walls=dict(back="the altar on the wall across from the main door, in line with it, statues either side",
                   other_back="tapestries", front="the door; plants in the corners",
                   middle="a carpeted aisle from the door to the altar; a few rows of pews either side of it, nearest "
                          "the altar; a colonnade down the nave; a pair of sarcophagi behind the pews; open floor "
                          "toward the doors"),
        cover=(0.05, 0.10, 0.18), open=(0.55, 0.88), per_tile=(0.08, 0.35), types_min=8, free_most=(4, 30),
        caps={"bench": (10, 16), "tomb": (60, 2), "column": (24, 8), "statue": (24, 6)}, walls_min=3, lined=None, tiles=(60, 260),
        signature={"altar": (8, 1), "bench": (0.4, 16)}, needs=("altar",), kin=("hall",),
        variants={"dark_chapel": dict(must={"altar": 1, "statue": 4}, types_min=6,
                                      caps={"statue": (18, 15), "tomb": (28, 10), "column": (30, 8)},
                                      signature={"altar": (8, 1), "statue": (0.3, 12)})}),
    # ---- the dead ------------------------------------------------------------------------------------------------
    "crypt": dict(
        family="dead", feel="open", kinds=("crypt", "dark_crypt"), westwood=("crypt",),
        focal=dict(fam="tomb", types=r"^Crypt\d|^Coffin|^LOTDTombstone|Sarcophag", where="rows"),
        must={"tomb": 2}, never=("bed", "desk", "table", "chair", "stove", "smithy", "lab", "counter_bar",
                                 "counter_shop", "shop_rack", "fireplace", "straw"),
        never_types=r"Barrel|Sack|^Bookcase",
        walls=dict(back="a tapestry or two; a crypt chest in a corner", other_back="statues of the dead",
                   front="bare", middle="sarcophagi and coffins side by side in rows with aisles between; columns"),
        cover=(0.08, 0.16, 0.30), open=(0.40, 0.85), per_tile=(0.06, 0.40), types_min=3, free_most=(4, 30),
        caps={"tomb": (7, 24)}, walls_min=1, lined=None, tiles=(30, 200),
        signature={"tomb": (1, 20), "statue": (0.2, 4)}, needs=("tomb",), kin=("chapel",),
        variants={"dark_crypt": dict(cover=(0.08, 0.16, 0.30))}),
}

KIND_TYPE = {k: t for t, p in TYPES.items() for k in p["kinds"]}


def profile(kind):
    """The profile a room of kit kind `kind` is furnished and judged by: its type's, with the kind's variant on top."""
    t = KIND_TYPE.get(kind)
    if not t: return None
    p = dict(TYPES[t], type=t, kind=kind)
    p.update(TYPES[t].get("variants", {}).get(kind, {}))
    return p


def _count(key, fam, kinds):
    if key.startswith("^"):
        rx = re.compile(key)
        return sum(n for k, n in kinds.items() if rx.match(k))
    return fam.get(key, 0)


def strength(t, fam, kinds, kind=None):
    """How strongly contents read as type t (0 when a family it needs is missing)."""
    p = profile(kind) if kind and KIND_TYPE.get(kind) == t else TYPES[t]
    if any(fam.get(f, 0) == 0 for f in p.get("needs", ())): return 0.0
    return sum(w * min(_count(key, fam, kinds), most) for key, (w, most) in p["signature"].items())


def reads_as(fam, kinds, kind=None):
    """[(type, strength)] best first: what a room with these families (family -> n) and kinds (piece kind -> n,
    review/roommeasure.py kind_of) reads as. Some types need more of their defining family than one piece."""
    fam = dict(fam)
    out = []
    for t in TYPES:
        s = strength(t, fam, kinds, kind)
        if t == "barracks" and fam.get("bed", 0) < 3 and fam.get("straw", 0) < 3: s = 0.0
        if t == "library" and fam.get("shelves", 0) < 6: s = 0.0
        if t == "laboratory" and fam.get("lab", 0) < 2: s = 0.0
        if t == "storeroom" and fam.get("storage", 0) < 4: s = 0.0
        if t == "armoury" and (fam.get("shop_rack", 0) < 2 or fam.get("counter_shop")): s = 0.0
        if t in ("dining_hall", "great_hall") and (fam.get("table", 0) < 2 or fam.get("chair", 0) + fam.get("bench", 0) < 4):
            s = 0.0
        if t == "crypt" and fam.get("tomb", 0) < 2: s = 0.0
        if s > 0: out.append((t, round(s, 1)))
    return sorted(out, key=lambda x: -x[1])


def apply(rooms, cover):
    """Writes the profiles into kit/identity.py's tables: each kind's coverage (target, limit) and its repeat caps.
    Called once when kit/identity.py loads, so the furnisher and the checker hold rooms to their type."""
    for kind in rooms:
        p = profile(kind)
        if not p: continue
        cover[kind] = (p["cover"][1], p["cover"][2])
        if p.get("caps"):
            rooms[kind]["repeat"] = dict(p["caps"])
