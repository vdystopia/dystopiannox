"""Room types: what makes each kind of room good, as data the furnisher and the room score both read.

There is no one-size-fits-all room (Starwell playtest, 2026-10-05: "Different rooms have different dynamics and
identities. What made that room good was the fact that it had everything a study should have and in the right
arrangement. A throne room, however, is very different than a study and should, by its nature, be more open with less
object density"). Each type has its own brief (rules/rooms/<type>.md: purpose, focal point, pieces, composition,
density, mistakes, examples) and its own profile here. The kit's 46 room kinds (kit/identity.py ROOMS, each with its
recipe) map onto 35 types; a culture's kind (an ogre den, the Land of the Dead's chapel) is a variant of its type.

A profile holds:
- family: the structural family (FAMILIES): private, work, stores, public, ceremonial, martial, confinement, the dead;
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
- kin: types it may read as without losing its identity (a study rich in books reads as a library); a store is never
  the second room of a mixed one, since kegs, sacks and chests support most types;
- westwood: rules/rooms/westwood.json types its numbers were measured on (n rooms each, in the brief);
- supplies_line: True where barrels, crates and sacks may line a wall corner to corner (a store); monotony: the
  share of a big room's furniture one kind may be before the checker calls it monotonous (validate/checks.py
  identity_flags reads both; default 0.6);
- fixed_top_up: families the furnisher's top-up does not multiply with the room's size (a lord's chamber takes one or
  two chests, not five);
- variants: kit kind -> overrides for a culture or a smaller sibling (an ogre den is a barracks of straw);
- stands: where people stand in the room (STANDS below; kit/story.py StoryMap.stand_px reads it);
- evidence: for the types added for variety, the campaign rooms (map, centre cell) the type stands on.

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
    "confinement": "rooms that hold people against their will: bare, hard, few pieces, each of iron or straw; the "
                   "door is the room's one way, kept clear",
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
        kin=("living_room", "study", "library")),
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
        kin=("storeroom", "herbalist", "living_room")),
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
        signature={"^Bookcase|^MovableBookcase": (0.6, 30), "table": (1, 2), "desk": (1, 1)}, needs=("shelves",),
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
        family="stores", feel="full", supplies_line=True, kinds=("storeroom", "ore_store", "ogre_hoard", "granary"), westwood=("storeroom",),
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
        needs=("counter_bar",), kin=("dining_hall", "great_hall")),
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
                                    cover=(0.12, 0.24, 0.34), open=(0.25, 0.80)),
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
        caps={"bench": (16, 24), "table": (48, 6), "storage": (80, 3)}, walls_min=3, lined=None, tiles=(120, 400),
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
        caps={"bench": (14, 16), "tomb": (60, 2), "column": (24, 8), "statue": (24, 6)}, walls_min=3, lined=None, tiles=(60, 260),
        signature={"altar": (8, 1), "bench": (0.4, 16)}, needs=("altar",), kin=("hall", "shrine"),
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

# ---- more types (2026-10-05: "come up with more room types for more variety") -----------------------------------------
# Found by walking every enclosed campaign room (Con/War/Wiz, each layout once) the westwood.py finder types as empty,
# other, passage, hall, storeroom, armoury, barracks or laboratory, and reading what it holds: the guard rooms of Con03A
# and War03a, the cells of War07A and the ogres' pens of Con11a, the torture room of Wiz07C, the keg cellars of Con07B,
# Con06b and War02b, the powder stores of Con07C and Con09c, the winch rooms of Con06a, War07A and War02b, the
# telescopes of Con07B, the paintings of Con07E, the garden halls of Con07B and War07A, the shrines of Con10c, Con10d,
# Con07H and Wiz11A, the bone rooms and statue tombs of Con04a and Con04c, the lords' chambers of Con07D and Con06b.
# `evidence`: those rooms (map, room centre cell); an empty tuple where the type stands on design judgement alone (the
# infirmary). Westwood's own figures for each are in the type's brief (rules/rooms/<type>.md); the ranges here are
# fuller, as for every type, except where the type is bare by nature (a cell, an ossuary, a shrine).
# Pieces with no furniture family (rules/room_types.py FAMILIES: torture racks, stocks, iron maidens, gears, winches,
# bones) are not counted by the room score's coverage and variety; the signatures read them by kind (all_kinds).
TYPES.update({
    # ---- private -------------------------------------------------------------------------------------------------
    "solar": dict(
        family="private", feel="full", fixed_top_up=("storage", "bench"), kinds=("solar",), westwood=(),
        evidence=(("Con07D", (134, 63)), ("Con06b", (116, 182)), ("Con06b", (91, 158)), ("Wiz03b", (78, 85))),
        focal=dict(fam="fireplace", types=r"Fireplace", where="back"),
        must={"bed": 1, "fireplace": 1, "desk": 1, "shelves": 2}, never=("counter_bar", "counter_shop", "smithy", "altar",
                                                                          "throne", "tomb", "shop_rack", "straw", "stove"),
        never_types=r"Barrel|Crate|Sack",
        walls=dict(back="the bed end: the bed headboard to a back wall, its nightstand, the chest snug with a rug before it",
                   other_back="the sitting end: the hearth centred, bookcases either side of it; the desk on its own stretch",
                   front="a bench; plants in the corners",
                   middle="a small table with two or three chairs on a carpet before the sitting end; open between the ends"),
        cover=(0.05, 0.15, 0.28), open=(0.35, 0.85), per_tile=(0.15, 0.8), types_min=12, free_most=(3, 30),
        caps={"table": (40, 2), "bed": (200, 1)}, walls_min=3, lined=0.30, tiles=(60, 220),
        signature={"bed": (3, 1), "fireplace": (3, 1), "desk": (2, 1), "shelves": (0.3, 8), "table": (1, 1)},
        needs=("bed", "fireplace", "desk"), kin=("bedroom", "living_room", "study", "library")),
    # ---- work ----------------------------------------------------------------------------------------------------
    "workshop": dict(
        family="work", feel="balanced", supplies_line=True, kinds=("workshop",), westwood=(),
        evidence=(("Con06a", (102, 135)),),
        focal=dict(fam="table", types=r"^Table[1-4]$", where="any"),
        must={"table": 1, "storage": 3, "shop_rack": 1}, never=("bed", "desk", "altar", "throne", "tomb", "lab", "counter_bar",
                                                                "counter_shop", "fireplace", "stove"),
        never_types=r"^Bookcase|PowderBarrel|^CinderBin|^Bellows",
        walls=dict(back="trader's shelves of tools end to end", other_back="a second run of tool shelves, or a cart wheel "
                                                                           "or two against it",
                   front="tool barrels, crates of timber and iron, heaped toward the corners",
                   middle="the work bench (a long table) with its stool and a crate or barrel at its end; parts and "
                          "wheels lying by it; a clear way round it"),
        cover=(0.12, 0.20, 0.34), open=(0.30, 0.80), per_tile=(0.15, 0.9), types_min=5, free_most=(3, 15),
        caps={"table": (30, 3)}, walls_min=3, lined=0.20, tiles=(25, 110),
        signature={"^BarrelWithTools": (1.5, 4), "^MineOreCartWheel|^MechGear": (1.5, 6), "^Table": (1, 3),
                   "^TraderShelves": (0.5, 6)},
        needs=("table", "storage"), kin=("smithy", "storeroom")),
    "winch_room": dict(
        family="work", feel="open", kinds=("winch_room",), westwood=(), monotony=0.9,
        evidence=(("Con06a", (96, 146)), ("War07A", (134, 219)), ("War02A", (216, 208)), ("Con01A", (91, 146)),
                  ("War02b", (56, 224)), ("Wiz03a", (240, 22))),
        focal=dict(fam=None, types=r"^PulleyGear", where="any"),
        must={"storage": 1}, never=("bed", "desk", "table", "chair", "altar", "throne", "tomb", "lab", "counter_bar",
                                    "counter_shop", "fireplace", "stove", "shelves", "rug", "plant"),
        never_types=r"PowderBarrel",
        walls=dict(back="the gear trains against the back walls, turning the shafts that run through them",
                   other_back="a second gear train, or bare", front="tool barrels and crates of spare parts",
                   middle="the great winch (a pulley gear) standing free with room all round it to work it; small "
                          "gears and parts on the floor by it"),
        cover=(0.02, 0.10, 0.25), open=(0.45, 0.98), per_tile=(0.0, 0.6), types_min=1, free_most=(4, 20),
        caps={}, walls_min=1, lined=None, tiles=(12, 180),
        signature={"^Gear|^PulleyGear": (2, 8), "^MechGear": (0.5, 4), "^BarrelWithTools": (0.5, 3)},
        needs=(), kin=("storeroom", "workshop")),
    "observatory": dict(
        family="work", feel="balanced", kinds=("observatory",), westwood=(),
        evidence=(("Con07B", (121, 219)), ("Con07E", (172, 104))),
        focal=dict(fam="lab", types=r"^Telescope|^Orrery", where="any"),
        must={"lab": 1, "desk": 1, "shelves": 2}, never=("bed", "stove", "smithy", "counter_bar", "counter_shop",
                                                         "shop_rack", "altar", "throne", "tomb", "straw"),
        never_types=r"Barrel|Crate|Sack|^AlchemistDesk|^WizardWorkstation",
        walls=dict(back="star charts and zodiacs hung between the bookcases; the astronomer's desk near a corner",
                   other_back="a telescope at the wall, looking out", front="a chest; plants",
                   middle="a telescope or an orrery standing free with room round it; the chart table with its stools"),
        cover=(0.03, 0.12, 0.24), open=(0.45, 0.90), per_tile=(0.10, 0.6), types_min=8, free_most=(3, 40),
        caps={"lab": (20, 4)}, walls_min=3, lined=0.20, tiles=(40, 200),
        signature={"^Telescope": (4, 3), "^StarChart|^Zodiac": (1.5, 6), "^Orrery": (2, 1), "desk": (1, 1)},
        needs=("lab",), kin=("laboratory", "study", "library")),
    "infirmary": dict(
        family="work", feel="full", kinds=("infirmary",), westwood=(), evidence=(),
        focal=dict(fam="bed", types=r"^(Cot\d|WoodBed\d|Bed\d)$", where="row"),
        must={"bed": 2, "stove": 1, "shelves": 2, "table": 1}, never=("counter_bar", "counter_shop", "smithy", "altar",
                                                                       "throne", "tomb", "shop_rack", "straw", "lab"),
        never_types=r"PowderBarrel|^Crate",
        walls=dict(back="a pair of potion shelves and books of remedies; the cauldron toward a corner",
                   other_back="hangings of one colour", front="the sick in a row of cots, a nightstand between "
                                                              "neighbours",
                   middle="the healer's table with its stool, kept clear round it; a way down the row of cots"),
        cover=(0.10, 0.20, 0.32), open=(0.30, 0.80), per_tile=(0.2, 0.9), types_min=8, free_most=(4, 25),
        caps={"bed": (12, 10)}, walls_min=3, lined=0.25, tiles=(40, 200),
        signature={"bed": (2, 8), "^PotionShelves": (2, 2), "^Cauldron": (2, 1), "nightstand": (0.3, 6)},
        needs=("bed", "stove"), kin=("barracks", "herbalist", "bedroom")),
    # ---- stores --------------------------------------------------------------------------------------------------
    "cellar": dict(
        family="stores", feel="full", supplies_line=True, kinds=("cellar",), westwood=(), monotony=0.9,
        evidence=(("Con07B", (132, 196)), ("Con06b", (56, 62)), ("War02b", (194, 194)), ("Con06a", (153, 212))),
        focal=dict(fam="storage", types=r"^LargeBarrel", where="any"),
        must={"storage": 6}, never=("bed", "desk", "table", "chair", "altar", "throne", "tomb", "lab", "counter_bar",
                                    "counter_shop", "fireplace", "stove", "statue", "shelves", "shop_rack"),
        never_types=r"PowderBarrel|^Sack|^TraderAppleCrate",
        walls=dict(back="kegs in tight rows along the walls from the corners", other_back="kegs; a stack of piled barrels",
                   front="kegs and a few crates", middle="a great cask or two with kegs beside them, aisles all round"),
        cover=(0.12, 0.22, 0.42), open=(0.15, 0.70), per_tile=(0.3, 1.2), types_min=3, free_most=(8, 6),
        caps={}, walls_min=3, lined=None, tiles=(12, 80),
        signature={"^(Barrel|LargeBarrel|PiledBarrels)$": (0.8, 30)}, needs=("storage",), kin=("storeroom", "kitchen")),
    "treasury": dict(
        family="stores", feel="balanced", kinds=("treasury",), westwood=(),
        evidence=(("Con05B", (192, 58)), ("Wiz06c", (163, 93)), ("Con06b", (163, 93))),
        focal=dict(fam="storage", types=r"^Chest\d|^DunMirChest|^ChestOgre", where="back"),
        must={"storage": 3, "table": 1}, never=("bed", "stove", "smithy", "lab", "counter_bar", "counter_shop", "altar",
                                                "throne", "tomb", "straw", "fireplace", "plant"),
        never_types=r"PowderBarrel|^Bookcase|^Barrel|^Crate|^Sack",
        walls=dict(back="strongboxes in a row along the back walls, each with room before it to open",
                   other_back="hanging shields and crossed arms; the tally shelves",
                   front="bare, or a pair of guardian statues by the door",
                   middle="the counting table with the treasurer's chair, open floor round it"),
        cover=(0.03, 0.12, 0.24), open=(0.45, 0.90), per_tile=(0.08, 0.5), types_min=5, free_most=(3, 30),
        caps={"storage": (10, 6), "table": (60, 1)}, walls_min=2, lined=None, tiles=(20, 120),
        signature={"^Chest|^DunMirChest|^ChestOgre": (1.5, 8), "table": (1, 1)}, needs=("storage", "table"),
        kin=("storeroom", "study")),
    "powder_store": dict(
        family="stores", feel="full", supplies_line=True, kinds=("powder_store",), westwood=(), monotony=1.01,
        evidence=(("Con07C", (119, 195)), ("Con09c", (62, 232))),
        focal=dict(fam="storage", types=r"^BlackPowderBarrel", where="any"),
        must={"storage": 6}, never=("bed", "desk", "table", "chair", "altar", "throne", "tomb", "lab", "counter_bar",
                                    "counter_shop", "fireplace", "stove", "shelves", "rug", "plant", "statue"),
        never_types=r"^Sack|^Bookcase",
        walls=dict(back="powder kegs in tight rows from the corners", other_back="powder kegs",
                   front="a few plain barrels and crates by the door", middle="clear: a way to every row"),
        cover=(0.15, 0.30, 0.45), open=(0.10, 0.70), per_tile=(0.3, 1.3), types_min=2, free_most=(60, 1),
        caps={}, walls_min=2, lined=None, tiles=(12, 60),
        signature={"^BlackPowderBarrel": (2, 30)}, needs=("storage",), kin=("storeroom", "cellar")),
    # ---- martial -------------------------------------------------------------------------------------------------
    "guardroom": dict(
        family="martial", feel="balanced", kinds=("guardroom",), westwood=(),
        evidence=(("Con03A", (110, 112)), ("Con06a", (69, 199)), ("Con06b", (179, 71)), ("Con03A", (81, 83)),
                  ("Con02a", (93, 175))),
        focal=dict(fam="table", types=r"^RoundTableWithFood$|^RoundTable\d$|^Table\d$|^SquareTable\d$", where="any"),
        must={"table": 1, "bed": 1, "shop_rack": 1}, never=("counter_bar", "counter_shop", "altar", "throne", "tomb",
                                                            "lab", "smithy", "stove", "desk", "plant"),
        never_types=r"PowderBarrel|^Bookcase",
        walls=dict(back="two or three cots against a back wall for the watch off duty, a chest at each",
                   other_back="swords, pole arms and bows on the wall; shields and crossed arms hung between",
                   front="a barrel or two of water and ale; a bench",
                   middle="the watch's table with its chairs (a meal on it), a clear way from the door past it"),
        cover=(0.10, 0.18, 0.32), open=(0.30, 0.80), per_tile=(0.15, 0.9), types_min=8, free_most=(3, 20),
        caps={"bed": (12, 4), "table": (30, 2)}, walls_min=2, lined=0.20, tiles=(20, 90),
        signature={"shop_rack": (1, 6), "bed": (1.5, 3), "table": (2, 1), "chair": (0.3, 6)},
        needs=("bed", "table", "shop_rack"), kin=("barracks", "armoury", "bedroom", "living_room")),
    # ---- confinement ---------------------------------------------------------------------------------------------
    "cell": dict(
        family="confinement", feel="open", kinds=("cell", "ogre_pen"), westwood=(), monotony=1.01,
        evidence=(("War07A", (174, 236)), ("War07A", (160, 230)), ("War07A", (164, 226)), ("Con11a", (174, 44)),
                  ("Con11a", (166, 52)), ("Con11a", (194, 80)), ("Con11a", (182, 36))),
        focal=dict(fam="bed", types=r"^Cot\d$|^OgreBed\d$", where="back"),
        must={"straw": 2}, never=("table", "desk", "shelves", "counter_bar", "counter_shop", "altar", "throne", "tomb",
                                  "lab", "smithy", "stove", "fireplace", "rug", "plant", "statue", "wall_decor"),
        never_types=r"PowderBarrel|^Chest|^Bookcase",
        walls=dict(back="a cot against a back wall, or nothing but straw", other_back="the stocks, or bare",
                   front="bare: the door, barred", middle="straw strewn, a few bones; open"),
        cover=(0.02, 0.10, 0.25), open=(0.25, 0.98), per_tile=(0.05, 1.0), types_min=2, free_most=(12, 2),
        caps={}, walls_min=1, lined=None, tiles=(8, 40),
        signature={"straw": (1, 10), "^Stocks": (3, 1), "bed": (1, 1)}, needs=("straw",), kin=("barracks", "bedroom"),
        variants={"ogre_pen": dict(focal=dict(fam=None, types=r"^Stocks", where="any"), tiles=(20, 50),
                                   cover=(0.0, 0.06, 0.25), walls_min=0)}),
    "torture_chamber": dict(
        family="confinement", feel="open", kinds=("torture_chamber",), westwood=(),
        evidence=(("Wiz07C", (132, 124)), ("Con08d", (151, 170))),
        focal=dict(fam=None, types=r"^TortureRack", where="any"),
        must={"storage": 1, "desk": 1}, never=("bed", "shelves", "counter_bar", "counter_shop", "altar", "throne", "tomb", "lab",
                                    "smithy", "stove", "rug", "plant", "bench", "wall_decor"),
        never_types=r"PowderBarrel|^Bookcase|^Barrel|^Crate|^Sack",
        walls=dict(back="the iron maiden against a back wall; the questioner's desk and chair on its own stretch",
                   other_back="the stocks", front="the chest of instruments in a corner",
                   middle="the rack standing free with room all round it; bones and remains on the floor by it"),
        cover=(0.0, 0.08, 0.25), open=(0.45, 0.99), per_tile=(0.01, 0.5), types_min=2, free_most=(3, 20),
        caps={}, walls_min=1, lined=None, tiles=(20, 90),
        signature={"^TortureRack|^IronMaiden|^Stocks": (4, 4)}, needs=(), kin=("cell",)),
    # ---- ceremonial ----------------------------------------------------------------------------------------------
    "shrine": dict(
        family="ceremonial", feel="open", kinds=("shrine", "dark_shrine"), westwood=(),
        evidence=(("Con10c", (30, 140)), ("Con10d", (132, 51)), ("Con07H", (118, 85)), ("Wiz11A", (50, 215)),
                  ("Wiz02B", (120, 120)), ("Con07D", (118, 78))),
        focal=dict(fam="altar", types=r"^DunMirAltar|^LOTDLichGodStatue", where="door"),
        must={"altar": 1, "statue": 2}, never=("bed", "desk", "table", "stove", "smithy", "lab", "counter_bar",
                                               "counter_shop", "shop_rack", "straw", "shelves", "fireplace"),
        never_types=r"Barrel|Crate|Sack|^Bookcase|Trophy",
        walls=dict(back="the altar (or the relic) across from the door, in line with it, statues flanking it, "
                        "candles before it",
                   other_back="a tapestry or two of one colour", front="the door; a basin of fire in each front corner",
                   middle="a runner from the door to the altar; a kneeling bench or two; open"),
        cover=(0.0, 0.05, 0.14), open=(0.65, 0.97), per_tile=(0.04, 0.4), types_min=4, free_most=(4, 30),
        caps={"bench": (20, 3), "statue": (16, 6)}, walls_min=2, lined=None, tiles=(12, 120),
        signature={"altar": (8, 1), "^DunMirFlameBasin|^LOTDIncenseBasin": (2, 2), "statue": (0.5, 4)},
        needs=("altar",), kin=("chapel", "hall"),
        variants={"dark_shrine": dict(must={"altar": 1, "statue": 2}, types_min=3)}),
    "gallery": dict(
        family="ceremonial", feel="open", kinds=("gallery",), westwood=(),
        evidence=(("Con07E", (203, 112)),),
        focal=dict(fam="wall_decor", types=r"^Painting", where="back"),
        must={"wall_decor": 4, "bench": 1}, never=("bed", "desk", "table", "stove", "smithy", "counter_bar",
                                                   "counter_shop", "shop_rack", "straw", "tomb", "shelves", "altar"),
        never_types=r"Barrel|Crate|Sack|^Bookcase|Trophy",
        walls=dict(back="paintings hung along both back walls at even spacing, a tapestry of one colour between",
                   other_back="paintings", front="plants in the corners; a statue",
                   middle="a bench or two facing the paintings, a pair of statues, one curio (an orrery); open floor "
                          "to walk the walls"),
        cover=(0.0, 0.04, 0.14), open=(0.65, 0.97), per_tile=(0.04, 0.35), types_min=5, free_most=(4, 30),
        caps={"bench": (30, 6), "statue": (25, 8)}, walls_min=2, lined=None, tiles=(60, 260),
        signature={"^Painting": (2, 10), "statue": (0.5, 4), "bench": (0.3, 4)}, needs=("wall_decor",),
        kin=("hall", "great_hall")),
    "conservatory": dict(
        family="ceremonial", feel="open", kinds=("conservatory",), westwood=(), monotony=1.01,
        evidence=(("Con07B", (150, 198)), ("Con07B", (153, 226)), ("Wiz01A", (115, 105))),
        focal=None,                    # the fountain or the well where the room has the floor for it (24+ tiles open)
        must={"plant": 6, "bench": 1}, never=("bed", "desk", "table", "stove", "smithy", "lab", "counter_bar",
                                              "counter_shop", "shop_rack", "straw", "tomb", "shelves", "fireplace"),
        never_types=r"Barrel|Crate|Sack|^Bookcase|Trophy",
        walls=dict(back="plants massed along the back walls", other_back="plants; a pair of columns",
                   front="plants in the corners", middle="the fountain or the well, benches facing it, clumps of plants "
                                                         "with paths between"),
        cover=(0.0, 0.06, 0.25), open=(0.40, 0.95), per_tile=(0.08, 0.6), types_min=5, free_most=(40, 4),
        caps={"bench": (25, 6)}, walls_min=2, lined=None, tiles=(24, 220),
        signature={"plant": (0.5, 30), "^Fountain|^WishingWell": (4, 1)}, needs=("plant",), kin=("hall",)),
    # ---- the dead ------------------------------------------------------------------------------------------------
    "mausoleum": dict(
        family="dead", feel="open", kinds=("mausoleum",), westwood=(),
        evidence=(("Con04a", (148, 55)), ("Con04a", (230, 88)), ("Con04c", (220, 108)), ("Con04c", (75, 78))),
        focal=dict(fam="tomb", types=r"^Crypt\d", where="any"),
        must={"tomb": 1, "statue": 2}, never=("bed", "desk", "table", "chair", "stove", "smithy", "lab", "counter_bar",
                                              "counter_shop", "shop_rack", "fireplace", "straw", "bench"),
        never_types=r"Barrel|Sack|^Bookcase",
        walls=dict(back="monuments at the back corners; a tapestry", other_back="a tapestry, or bare",
                   front="bare", middle="the great tomb in the middle, statues of the dead in pairs facing it, a pair "
                                        "of columns in a big one"),
        cover=(0.02, 0.10, 0.20), open=(0.50, 0.92), per_tile=(0.04, 0.4), types_min=4, free_most=(4, 30),
        caps={"tomb": (40, 3), "statue": (14, 8), "column": (24, 6)}, walls_min=1, lined=None, tiles=(30, 160),
        signature={"^Monument": (2, 4), "statue": (1, 6), "tomb": (2, 3)}, needs=("tomb", "statue"),
        kin=("crypt", "hall", "chapel")),
    "ossuary": dict(
        family="dead", feel="open", kinds=("ossuary",), westwood=(), monotony=0.95,
        evidence=(("Con04a", (123, 107)), ("Con04a", (125, 160)), ("War04b", (239, 65)), ("Con04a", (114, 122))),
        focal=None,
        must={"storage": 1}, never=("bed", "desk", "table", "chair", "stove", "smithy", "lab", "counter_bar",
                                    "counter_shop", "shop_rack", "fireplace", "straw", "bench", "rug", "plant"),
        never_types=r"Barrel|Sack|^Bookcase",
        walls=dict(back="skulls and long bones heaped along the walls; crypt chests in the corners",
                   other_back="a monument or two", front="bones", middle="bones in heaps, a way kept through them"),
        cover=(0.01, 0.06, 0.18), open=(0.55, 0.99), per_tile=(0.0, 0.4), types_min=1, free_most=(4, 30),
        caps={}, walls_min=1, lined=None, tiles=(9, 120),
        signature={"^Skull|^ArmBone|^LegBone": (0.3, 40), "^CryptChest": (1, 3), "^Monument": (1, 3)},
        needs=(), kin=("crypt",)),
})

# Where people stand in each type (StoryMap.stand_px reads it): the spots in order of preference, each
#   ("keeper",)          the furnisher's own spot behind the counter or the bar (Furnisher.spots);
#   ("beside", regex)    beside the first piece of that type, at its side along its wall (the priest at the altar's side,
#                        the lord by his hearth, the gaoler by his table);
#   ("behind", regex)    on the far side of a free-standing piece from the door (the treasurer behind his counting table);
#   ("back",)            against a back wall in a free stretch, facing the room.
# Never between tables, never in a doorway or the way in from it, never on a runner or an aisle (2026-10-05: the user
# found a quest giver "in a weird place in between two tables" in a hall).
STANDS = {
    "bedroom": (("beside", r"^(Bed\d|WoodBed\d|Cot\d)$"), ("beside", r"^Chest\d|^DunMirChest"), ("back",)),
    "study": (("beside", r"^Desk\d$"), ("beside", r"^Bookcase"), ("back",)),
    "living_room": (("beside", r"Fireplace"), ("back",)),
    "kitchen": (("beside", r"^Cauldron|^Stove"), ("beside", r"Fireplace"), ("back",)),
    "laboratory": (("beside", r"^AlchemistDesk|^WizardWorkstation"), ("beside", r"^Desk\d$"), ("back",)),
    "herbalist": (("beside", r"^Cauldron"), ("beside", r"^PotionShelves"), ("back",)),
    "library": (("beside", r"^Desk\d$"), ("beside", r"^Bookcase"), ("back",)),
    "smithy": (("keeper",), ("beside", r"^Anvil"), ("beside", r"^CinderBin")),
    "storeroom": (("beside", r"^LogShelves"), ("back",)),
    "barracks": (("beside", r"^(Cot|WoodBed|Bed|OgreBed)\d$"), ("beside", r"^OgreFirePit$"), ("back",)),
    "armoury": (("beside", r"^Trader(ArmorRack|PoleArm|BowRack|QuiverRack|ClothesRack)"), ("back",)),
    "shop": (("keeper",), ("beside", r"^TraderDesk")),
    "tavern": (("keeper",), ("beside", r"Fireplace"), ("back",)),
    "dining_hall": (("beside", r"Fireplace|^OgreFirePit$"), ("back",)),
    "great_hall": (("beside", r"Fireplace"), ("beside", r"^Statue"), ("back",)),
    "hall": (("beside", r"^Statue|^LOTDManaObelisk"), ("back",)),
    "chapel": (("beside", r"^DunMirAltar|^LOTDLichGodStatue"), ("back",)),
    "throne_room": (("beside", r"^DunMirThrone|^LOTDLichThrone"), ("back",)),
    "crypt": (("beside", r"^CryptChest|^Statue|^LOTDManaObelisk"), ("back",)),
    "solar": (("beside", r"Fireplace"), ("beside", r"^Desk\d$"), ("back",)),
    "workshop": (("beside", r"^Table[1-4]$"), ("beside", r"^TraderShelves"), ("back",)),
    "winch_room": (("beside", r"^PulleyGear"), ("beside", r"^Gear"), ("back",)),
    "observatory": (("beside", r"^Telescope"), ("beside", r"^Desk\d$"), ("back",)),
    "infirmary": (("beside", r"^Cauldron"), ("beside", r"^PotionShelves"), ("back",)),
    "cellar": (("beside", r"^LargeBarrel"), ("back",)),
    "treasury": (("behind", r"^Table|^SquareTable|^RoundTable"), ("beside", r"^Chest\d|^DunMirChest"), ("back",)),
    "powder_store": (("back",),),
    "guardroom": (("beside", r"^Trader(HangingSwords|PoleArm|BowRack|QuiverRack)"), ("behind", r"Table"), ("back",)),
    "cell": (("beside", r"^Cot\d$|^OgreBed\d$"), ("beside", r"^Stocks"), ("back",)),
    "torture_chamber": (("beside", r"^TortureRack"), ("beside", r"^Desk\d$"), ("back",)),
    "shrine": (("beside", r"^DunMirAltar|^LOTDLichGodStatue"), ("back",)),
    "gallery": (("beside", r"^Statue"), ("back",)),
    "conservatory": (("beside", r"^Fountain$|^WishingWell$"), ("back",)),
    "mausoleum": (("beside", r"^Crypt\d"), ("beside", r"^Monument"), ("back",)),
    "ossuary": (("beside", r"^CryptChest"), ("back",)),
}
for _t, _s in STANDS.items(): TYPES[_t].setdefault("stands", _s)

KIND_TYPE ={k: t for t, p in TYPES.items() for k in p["kinds"]}


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
        if t == "library" and sum(n for k, n in kinds.items() if k.startswith(("Bookcase", "MovableBookcase"))) < 6: s = 0.0
        if t == "laboratory" and fam.get("lab", 0) < 2: s = 0.0
        if t == "storeroom" and fam.get("storage", 0) < 4: s = 0.0
        if t == "armoury" and (fam.get("shop_rack", 0) < 2 or fam.get("counter_shop")): s = 0.0
        if t in ("dining_hall", "great_hall") and (fam.get("table", 0) < 2 or fam.get("chair", 0) + fam.get("bench", 0) < 4):
            s = 0.0
        if t == "crypt" and fam.get("tomb", 0) < 2: s = 0.0
        # the types added for variety read only when what defines them is there in force, so no room of the older types
        # reads as one by a stray piece (a living room with a painting or two is no gallery)
        k = lambda rx: sum(n for kk, n in kinds.items() if re.match(rx, kk))
        if t == "solar" and (fam.get("desk", 0) < 1 or fam.get("bed", 0) > 1): s = 0.0
        if t == "workshop" and k(r"^BarrelWithTools|^MineOreCartWheel|^MechGear") < 3: s = 0.0
        if t == "winch_room" and k(r"^Gear|^PulleyGear") < 2: s = 0.0
        if t == "observatory" and not (k(r"^Telescope") >= 2 or (k(r"^Telescope") and k(r"^StarChart|^Zodiac") >= 2)):
            s = 0.0
        if t == "infirmary" and not k(r"^PotionShelves|^Cauldron"): s = 0.0
        kegs = k(r"^(Barrel|LargeBarrel|PiledBarrels)$")
        if t == "cellar" and (kegs < 6 or fam.get("shelves") or fam.get("table") or kegs < 0.7 * fam.get("storage", 0)):
            s = 0.0
        if t == "treasury" and (k(r"^Chest|^DunMirChest|^ChestOgre") < 3 or fam.get("bed")): s = 0.0
        if t == "powder_store" and k(r"^BlackPowderBarrel") < 4: s = 0.0
        if t == "cell" and (fam.get("fireplace") or fam.get("table") or fam.get("chair", 0) > 1): s = 0.0
        if t == "torture_chamber" and k(r"^TortureRack|^IronMaiden|^Stocks") < 2: s = 0.0
        if t == "shrine" and fam.get("bench", 0) >= 4: s = 0.0
        if t == "gallery" and (k(r"^Painting") < 4 or any(fam.get(f) for f in ("bed", "desk", "shelves", "table", "stove"))):
            s = 0.0
        if t == "conservatory" and fam.get("plant", 0) < 8: s = 0.0
        if t == "mausoleum" and (fam.get("tomb", 0) > 4 or fam.get("altar") or fam.get("bench", 0) >= 4): s = 0.0
        if t == "ossuary" and (k(r"^Skull|^ArmBone|^LegBone") < 8 or fam.get("tomb", 0) >= 2 or fam.get("altar")): s = 0.0
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
