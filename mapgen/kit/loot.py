"""Loot in containers: what Westwood's chests, sacks, barrels, crates and coffins hold, filled in at build time.

Measured 2026-10-05 on the 107 campaign maps (corpus/out/nox_corpus.db; an object's inventory is the objects whose
`parent` is its id). The place is read from what stands round a container (within about 6 cells): coffins and
tombstones make a crypt, a bed a bedroom, a stove a kitchen, ogre furniture an ogre lair, two or more other barrels,
crates or sacks a storeroom; otherwise the map's environment. rules/QUESTS.md has the gold.

| container | count | hold something | items (median, mean) | gold: share of all, median |
|---|---|---|---|---|
| chests (Chest*, DunMirChest*, CryptChest*, StumpChest1, ChestLOTD*, ...) | 1461 | 97% (100% indoors) | 1, 1.8 | 43%, 42 |
| sacks (SackChest*) | 77 | 88% | 1, 2.0 | 25%, 61 |
| Barrel, Barrel2, BarrelLOTD | 1956 | 42% | 1, 1.8 | 5%, 22 |
| LargeBarrel*, PiledBarrels* | 260 | 15% | | |
| Crate1-2, DarkCrate1-2 | 285 | 51% | 1, 1.6 | 5%, 25 |
| Coffin1-4 | 407 | 41% | 1, 2.5 | 1% |
| WaterBarrel, BlackPowderBarrel, BarrelSteel, BarrelWithTools, CrateSteel, TraderAppleCrate, TargetBarrel, Open*Chest, OgreSack | 1300+ | 0-1% | | |

What they hold, by place (the commonest first):
- chests in bedrooms (193, all full): gold in 55% (median 30), red and blue potions, apples, cure poison, clothes
  (shirt, boots, cloak, leggings), a quiver or chakram now and then;
- chests in crypts (220): leg and arm bones and skulls, red potions, gold in 16% (median 27), blue potions, spell books;
- chests in dungeons and caves: bones and gold (median 25-46), red potions, keys;
- chests in storerooms (55): gold in 60% (median 39), potions, chakrams, quivers, boots;
- chests in ogre lairs (94): gold in 67% (median 92), potions, meat, quivers;
- barrels (stores 40% full, kitchens 38%, bedrooms 37%, crypts 35%, camps 33%, in the streets of towns 62%): apples and
  meat above all, then potions, mushrooms, cider; gold in 1 barrel in 20 (median 20); rats and frogs that jump out;
- crates (stores 54%, bedrooms 45%, ogre lairs 73%): potions, quivers, clothes (cloak, shirt, pants, boots), cider,
  apples, a staff, a sword or morning star now and then; gold rarely;
- sacks (ogre lairs and camps, 90%): meat and apples, gold in a quarter (median 46-61);
- coffins (crypts, 41%): arm and leg bones, skulls, a red potion, sometimes the undead rising out of it.

How they open: chests and sacks are IMMOBILE and are opened (used) by the player, who takes what is inside. Barrels,
crates and coffins are breakable obstacles (MISSILE_HIT, 7-10 health): a blow smashes them and what they hold drops on
the floor. So an empty barrel is a normal barrel, and only some are worth breaking.

The rules, as implemented (`fill`): every chest that holds nothing gets loot; sacks, barrels, crates and coffins get
loot at Westwood's share for their place; containers Westwood never fills stay empty; a container that already has
`items` (a story chest, a cache) keeps them. Creatures in containers are left out (they would count in a quest's
kills and wake in town). The map's gold stays in Westwood's budget: the gold already placed (story chests, caches,
gold on the floor) and paid by its quests (the scripts' gold actions) counts first; the containers add what is left
under GOLD_CEILING (between AMBIENT_GOLD_MIN and AMBIENT_GOLD_MAX), every purse shrunk alike when that is less than
Westwood's shares would give. Potions and arms or armour are capped per map (CAPS, Westwood's p90), since our maps
stand about three times Westwood's containers; past a cap containers hold food, plain clothes or bones, and a chest is
never left empty. Each filled container holds 1 thing at the median, up to 4 (COUNT); gold counts as one.

Places: `tag(spec, objects, place)` marks where objects stand (furnish_room tags a room's pieces with its room kind,
the camps their goods with "camp"); untagged containers are "outdoor". A separate random generator seeded from the
map's name keeps the map's own draws, and so its layout, unchanged.
"""
import random, re, zlib

GOLD_CEILING = 1500            # a map's gold, all told (Westwood: median 524, p75 1096; rules/QUESTS.md)
AMBIENT_GOLD_MAX = 400         # the most the containers add, however little the story placed
AMBIENT_GOLD_MIN = 60          # a few coins in a chest or two, even on a rich map

# containers Westwood never (or almost never) fills
NEVER = re.compile(r"^(WaterBarrel|BlackPowderBarrel\d?|BarrelSteel\d|BarrelWithTools\d|CrateSteel\d|TraderAppleCrate"
                   r"|TargetBarrel\d|Open\w*Chest\d|OgreSack\d)$")


def family(t):
    """chest, sack, barrel, big_barrel, crate, coffin, or None (not a container we fill)."""
    if NEVER.match(t): return None
    if t.startswith("SackChest"): return "sack"
    if "Chest" in t: return "chest"
    if re.match(r"^(Barrel2?|BarrelLOTD)$", t): return "barrel"
    if re.match(r"^(LargeBarrel|PiledBarrels)\d$", t): return "big_barrel"
    if re.match(r"^(Dark)?Crate\d$", t): return "crate"
    if re.match(r"^Coffin\d$", t): return "coffin"
    return None


# room kinds (kit/identity.ROOMS) -> the place whose loot they keep
PLACE = {
    "bedroom": "home", "dwelling": "home", "living_room": "home", "barracks": "home", "study": "home",
    "library": "home", "herbalist": "home", "laboratory": "hall", "great_hall": "hall", "hall": "hall",
    "throne_room": "hall", "dining_hall": "kitchen", "kitchen": "kitchen", "tavern": "kitchen", "mess_hall": "kitchen",
    "storeroom": "store", "gear_store": "store", "ore_store": "store", "shop": "store", "smithy": "store",
    "crypt": "crypt", "dark_crypt": "crypt", "chapel": "crypt", "dark_chapel": "crypt",
    "ogre_den": "ogre", "ogre_hall": "ogre", "ogre_hoard": "ogre", "camp": "camp", "outdoor": "outdoor",
}

# share of containers that hold something, by family and place (Westwood's, above)
SHARE = {
    "chest": 1.0, "big_barrel": 0.15, "coffin": 0.4,
    # Westwood's sacks lie in ogre lairs and camps; a storeroom's or kitchen's sack of grain is kept like a barrel
    "sack": {"ogre": 0.9, "camp": 0.9, "outdoor": 0.5, "*": 0.4},
    "barrel": {"store": 0.4, "kitchen": 0.38, "home": 0.37, "hall": 0.4, "crypt": 0.35, "camp": 0.33, "ogre": 0.38,
               "outdoor": 0.5},
    "crate": {"store": 0.54, "home": 0.45, "kitchen": 0.35, "hall": 0.5, "crypt": 0.4, "camp": 0.45, "ogre": 0.7,
              "outdoor": 0.35},
}

# chance that a filled container holds gold, and the amount (Westwood's quartiles by place, rounded to 5)
GOLD = {
    "chest": {"home": (0.55, 10, 50), "hall": (0.6, 20, 80), "store": (0.6, 15, 60), "kitchen": (0.6, 10, 40),
              "crypt": (0.2, 10, 40), "ogre": (0.65, 30, 100), "camp": (0.5, 15, 50), "outdoor": (0.5, 15, 50)},
    "sack": (0.25, 15, 60), "barrel": (0.08, 5, 30), "big_barrel": (0.0, 0, 0), "crate": (0.08, 5, 30),
    "coffin": (0.03, 5, 20),
}

CLOTHES = [("MedievalCloak", 3), ("LeatherBoots", 3), ("LeatherLeggings", 1), ("LeatherArmbands", 1), ("LeatherHelm", 1)]
# plain clothes (Westwood's bedroom chests and crates hold them; their durability is 0 in all Westwood's 800+)
PLAIN = [("MedievalShirt", 2), ("MedievalPants", 2)]
NO_WEAR = {"MedievalShirt", "MedievalPants"}
POTIONS = [("RedPotion", 6), ("BluePotion", 4), ("CurePoisonPotion", 2)]
FOOD = [("RedApple", 6), ("Meat", 4), ("Mushroom", 1), ("Cider", 1)]
BONES = [("ArmBone", 4), ("LegBone", 4), ("Skull", 2)]


def _w(*groups):
    """Weighted list from (table, scale) pairs."""
    out = []
    for table, k in groups: out += [(t, w * k) for t, w in table]
    return out


# what a filled container holds, by family and place (weights; gold is drawn separately)
ITEMS = {
    "chest": {
        "home": _w((POTIONS, 6), ([("RedApple", 3), ("Cider", 1)], 3), (CLOTHES, 2), (PLAIN, 3),
                   ([("Quiver", 1), ("FanChakram", 1)], 2)),
        "hall": _w((POTIONS, 6), (CLOTHES, 1), ([("Quiver", 1), ("FanChakram", 1)], 2), ([("Cider", 1)], 3), (PLAIN, 1)),
        "store": _w((POTIONS, 4), ([("Quiver", 2), ("FanChakram", 3)], 2), (CLOTHES, 1), ([("RedApple", 1), ("Cider", 1)], 3),
                    (PLAIN, 1)),
        "kitchen": _w(([("RedApple", 3), ("Cider", 3), ("Meat", 2)], 3), (POTIONS, 2)),
        "crypt": _w((BONES, 4), (POTIONS, 4)),
        "ogre": _w((POTIONS, 4), ([("Meat", 3), ("Quiver", 3), ("FanChakram", 2)], 2)),
        "camp": _w((POTIONS, 4), (FOOD, 3), ([("Quiver", 2)], 2)),
        "outdoor": _w((POTIONS, 4), (FOOD, 2), (CLOTHES, 1), (PLAIN, 1)),
    },
    "sack": {"*": _w(([("Meat", 8), ("RedApple", 4), ("Cider", 1)], 3), (POTIONS, 1))},
    "barrel": {
        "*": _w((FOOD, 6), (POTIONS, 1)),
        "crypt": _w((POTIONS, 3), ([("RedApple", 1)], 3)),
        "ogre": _w(([("Meat", 6), ("RedApple", 4), ("Cider", 1)], 4), (BONES, 1)),
    },
    "big_barrel": {"*": _w(([("RedApple", 3), ("Cider", 2)], 1))},
    "crate": {
        "*": _w((POTIONS, 3), ([("RedApple", 2), ("Cider", 3), ("Meat", 1)], 3), (CLOTHES, 2), (PLAIN, 1),
                ([("Quiver", 3), ("FanChakram", 1), ("StaffWooden", 1)], 2)),
        "kitchen": _w(([("RedApple", 3), ("Cider", 3), ("Meat", 2)], 3), (POTIONS, 1)),
        "ogre": _w(([("RedApple", 3), ("Cider", 1)], 3), (CLOTHES, 2), (POTIONS, 1)),
    },
    "coffin": {"*": _w((BONES, 6), ([("RedPotion", 3), ("CurePoisonPotion", 1)], 2))},
}
# how many things a filled container holds (gold counts as one): Westwood's median 1, p90 4
COUNT = {"chest": ((1, 55), (2, 30), (3, 12), (4, 3)), "sack": ((1, 50), (2, 35), (3, 15)),
         "barrel": ((1, 65), (2, 25), (3, 10)), "big_barrel": ((1, 70), (2, 30)), "crate": ((1, 65), (2, 28), (3, 7)),
         "coffin": ((1, 40), (2, 35), (3, 25))}


# the most a map's containers hold of the things worth having, all told (Westwood's p90 per campaign map: potions
# 14, arms and armour 9; their median 6 and 2). Our maps stand more containers than Westwood's (a town of ours ~150,
# Westwood's ~50), so the caps, not the shares, bound the value: past a cap a container draws from the cheap kinds
# (food, plain clothes, bones). Food and plain clothes are not capped.
CAPS = {"potion": 14, "gear": 9}
CAP_FLOOR = {"potion": 4, "gear": 2}      # what containers may still add when the story placed a lot
GEAR = {t for t, _ in CLOTHES} | {"Quiver", "FanChakram", "StaffWooden"}
FOODS = {"RedApple", "Meat", "Mushroom", "Cider"}


def kind_of(name):
    if "Potion" in name: return "potion"
    if name in GEAR: return "gear"
    if name in FOODS: return "food"
    return None


def tag(spec, objects, place):
    """Records where these objects stand (a room kind or 'camp'), for fill. Keeps the object with its place, so a
    removed piece's id is never mistaken for a new one's."""
    places = spec.__dict__.setdefault("loot_places", {})
    for o in objects or ():
        if o is not None and id(o) not in places: places[id(o)] = (o, place)


def place_of(spec, o):
    rec = getattr(spec, "loot_places", {}).get(id(o))
    kind = rec[1] if rec and rec[0] is o else "outdoor"
    return PLACE.get(kind, "home")


def _pick(rng, table):
    names, weights = zip(*table)
    return rng.choices(names, weights)[0]


def placed_gold(spec):
    """Gold already in the map: in containers' and creatures' items, lying on the floor, and paid by the map's
    scripts (every positive gold action of the quest book, both branches of a choice counted)."""
    n = 0
    for o in spec.d["objects"]:
        for it in [o] + list(o.get("items") or ()):
            if it.get("type") == "Gold": n += int((it.get("xfer") or {}).get("Amount", 0) or 0)
    for src in getattr(spec, "scripts", {}).values():
        n += sum(int(a) for a in re.findall(r'Kind: "gold", A: "[^"]*", B: "[^"]*", N: (\d+)', src))
    return n


def fill(spec):
    """Gives the map's containers their loot (see the module's notes). Returns a report: per family, the number of
    containers and of those filled, the gold added, and the gold already placed."""
    rng = random.Random(zlib.crc32(("loot:" + spec.d["name"]).encode()))
    before = placed_gold(spec)
    budget = min(AMBIENT_GOLD_MAX, max(AMBIENT_GOLD_MIN, GOLD_CEILING - before))
    report = dict(gold_before=before, gold_added=0, families={})
    plans, groups = [], {}
    have = {k: 0 for k in CAPS}
    for o in spec.d["objects"]:
        if family(o.get("type", "")):
            for it in o.get("items") or ():
                k = kind_of(it.get("type", ""))
                if k in have: have[k] += 1
    room = {k: max(CAP_FLOOR[k], CAPS[k] - have[k]) for k in CAPS}
    for o in spec.d["objects"]:
        f = family(o.get("type", ""))
        if not f: continue
        st = report["families"].setdefault(f, dict(n=0, filled=0, story=0, items={}))
        st["n"] += 1
        if o.get("items"):
            st["story"] += 1; st["filled"] += 1
            continue
        place = place_of(spec, o)
        st.setdefault("places", {})[place] = st.get("places", {}).get(place, 0) + 1
        groups.setdefault((f, place), []).append(o)
    # each kind of container in each place is filled at Westwood's share exactly (a coin decides the odd one), the
    # filled ones drawn at random
    for (f, place), objs in groups.items():
        share = SHARE[f] if not isinstance(SHARE[f], dict) else SHARE[f].get(place, SHARE[f].get("*", 0.4))
        k = int(share * len(objs) + rng.random())
        plans += [(o, f, place) for o in rng.sample(objs, k)]
    # chests first (gold goes to them first, while the budget lasts), the rest in a random order, so the caps fall
    # anywhere on the map
    rng.shuffle(plans)
    gold_of = lambda f, place: GOLD[f][place] if isinstance(GOLD[f], dict) else GOLD[f]
    # the gold Westwood's shares would put in these containers; on a map the story already made rich, every purse
    # shrinks alike (a few coins in many chests rather than Westwood's 40 in the first few)
    expected = sum(g[0] * (g[1] + g[2]) / 2 for g in (gold_of(f, pl) for _, f, pl in plans))
    scale = min(1.0, budget / expected) if expected else 1.0
    for o, f, place in sorted(plans, key=lambda p: p[1] != "chest"):
        n = rng.choices(*zip(*COUNT[f]))[0]
        g = gold_of(f, place)
        items = []
        if rng.random() < g[0]:
            amount = max(5, 5 * round(scale * rng.uniform(g[1], g[2]) / 5))
            if 0 < amount <= budget - report["gold_added"]:
                items.append(("Gold", {"Amount": amount}))
                report["gold_added"] += amount
        tables = ITEMS[f]
        table = tables.get(place) or tables.get("*") or next(iter(tables.values()))
        while len(items) < n:
            left = [(t, w) for t, w in table if room.get(kind_of(t), 1) > 0]
            if not left:
                if f == "chest" and not items: left = [("RedApple", 1), ("Cider", 1)]      # a chest is never empty
                else: break
            t = _pick(rng, left)
            if kind_of(t) in room: room[kind_of(t)] -= 1
            items.append(t)
        if not items: continue
        o["items"] = spec.items_at(items, o["x"], o["y"])
        for it in o["items"]:
            if it["type"] in NO_WEAR: it["durability"] = 0
        st = report["families"][f]
        st["filled"] += 1
        for it in items:
            name = it if isinstance(it, str) else it[0]
            st["items"][name] = st["items"].get(name, 0) + 1
    spec.loot_report = report
    return report


def summary(report):
    """One line: per family filled/total, and the gold."""
    fams = ", ".join(f"{f} {s['filled']}/{s['n']}" for f, s in sorted(report["families"].items()))
    return (f"LOOT {fams} | gold placed {report['gold_before']} + containers {report['gold_added']} = "
            f"{report['gold_before'] + report['gold_added']}")
