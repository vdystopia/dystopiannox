"""What every item the kit places, sells or gives must have (QA round 1, 2026-10-13: nox12, "Most of the new items don't
seem to actually have a function. They don't have a correct name or description. And their prices are not correct";
nox19, "The loaf of bread does not have a proper name or seem to do anything").

What the game does:
- An item's name and description are the strings thing.db:<Type>PrettyName and thing.db:<Type>Description, looked up by
  the client for every type (opennox client/object_type.go), so they can be given or mended in our string table
  (nox.csf.json, which mapgen/strings.py writes; TEXT below goes into it). Westwood left some as placeholders: Bread
  reads "BreadPrettyName", "BreadDescription" (it is a food: ConsumeUse 10, the same 10 health as Meat). Ruby and the
  gems have no string at all; the orbs and amulets a blank description.
- Its price is its WORTH in thing.bin (a shop sells at worth x BuyValueMultiplier); its function is its USE (food
  heals, a potion restores, a wand casts) or its class (a weapon or armour is worn). FACTS (items_facts.json) holds,
  for each of the 155 types the player can pick up, its worth, use, pickup and classes, read from the game's thing.bin
  with opennox-lib's things.Reader (Thing.Price, OnUse, OnPickup, Class).
- A spell book teaches the spell its shop entry names (ShopItemInfo.SpellID; Westwood's mystics: SPELL_POISON,
  SPELL_LESSER_HEAL...): one sold with none teaches nothing.

So every item sold has a name, a description, a price and a use, and a price in Westwood's range for the chapter the
act stands in (CAP: the dearest thing Westwood's shops sell by then); every item placed or given has a name.
Population.shopkeeper refuses wares that break this; the checker's items.* rules (validate/checks_game.py) read the
built map.
"""
import functools, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
NOX = r"C:\GOG Games\Nox"
FACTS = json.load(open(os.path.join(HERE, "items_facts.json"), encoding="utf-8"))

# names and descriptions the game's table lacks, leaves as a placeholder or blank, for the types we use (and their
# kin). Each is a type Westwood's maps never place, or one it leaves nameless, so no Westwood text changes.
TEXT = {
    "Bread": ("Loaf of Bread", "Eat this bread to restore some health."),
    "Corn": ("Ear of Corn", "Eat this corn to restore a bit of health."),
    "Soup": ("Bowl of Soup", "Eat this soup to restore some health."),
    "RottenMeat": ("Rotten Meat", "This meat has spoiled. Eating it will make you ill."),
    "Ruby": ("Ruby", "A large red gem. A trader will pay well for it."),
    "Emerald": ("Emerald", "A large green gem. A trader will pay well for it."),
    "Diamond": ("Diamond", "A flawless diamond. A trader will pay a fortune for it."),
    "AmuletofNature": ("Amulet of Nature", "A charm of carved wood and green stone. While you carry it, your wounds "
                                           "slowly close."),
    "BlackBook1": ("Black Book", "A road-book bound in black leather. A map is folded inside its cover."),
    # the Hollow Choir's tokens (kit/campaign.py TOKENS) that Westwood never places: named as the story names them
    "AmuletofCombat": ("Guild Medallion", "Doran Ashforge's guild medallion. Any smith of his guild will know it."),
    "RedOrb": ("Starsteel", "A lump of starsteel, red-glinting. Only a smith of the old guild can work it."),
    "GreenOrb": ("Wenna's Charm", "A green stone charm from Wenna, the herbalist of Brackwater. Tam will know it."),
    "BlueOrb": ("Bell-Token", "Tam's bell-token, given in thanks for his freedom."),
    "TreasureBag": ("Tam's Satchel", "A bell-ringer's satchel, mud-stained, left behind in the Mirewood."),
}

# charms: items with no use of their own in the game that the kit's scripts give a power while carried (charms.go,
# written into every map with scripts by Spec.build, so a charm works in every act it is carried into): type ->
# health restored every CHARM_EVERY frames while the carrier is hurt
CHARMS = {"AmuletofNature": 1}
CHARM_EVERY = 60

SPELL_BOOKS = re.compile(r"SpellBook$")
WORN = {"WEAPON", "ARMOR", "WAND"}
# the dearest thing Westwood's shops sell by each chapter (worth x the shop's BuyValueMultiplier, the three campaigns'
# maps; War01A 200, Con02a/Wiz02A ~500, War03b's chain tunic 2000, War05A 2640, War06a's great sword 7000, War07A 8400,
# War09 12250)
CAP = {1: 550, 2: 550, 3: 2000, 4: 2000, 5: 2640, 6: 7000, 7: 8400, 8: 8400, 9: 12250, 10: 12250, 11: 12250}


def chapter(act):
    """The Westwood chapter an act of the Hollow Choir stands level with (act 1, the first town, is Ix's chapter 2)."""
    return min(11, act + 1)


@functools.lru_cache(None)
def _table(nox=NOX):
    """{key lower: text} of the game's own string table (nox.csf), with TEXT laid over it."""
    import sys
    sys.path.insert(0, os.path.dirname(HERE))
    from strings import read_csf
    out = {}
    p = os.path.join(nox, "nox.csf")
    if os.path.exists(p):
        for e in read_csf(p)[1]:
            out[e["id"].lower()] = e["vals"][0]["str"] if e["vals"] else ""
    for k, v in csf_entries().items(): out[k.lower()] = v
    return out


def csf_entries():
    """{"thing.db:<Type>PrettyName": name, "thing.db:<Type>Description": text} for TEXT (mapgen/strings.py writes them
    into nox.csf.json, over the game's placeholders)."""
    out = {}
    for t, (n, d) in TEXT.items():
        out[f"thing.db:{t}PrettyName"] = n
        out[f"thing.db:{t}Description"] = d
    return out


def _real(s, t, what):
    return bool(s) and s.strip() and s != f"{t}{what}" and not s.startswith("MISSING")


def name(t):
    s = _table().get(f"thing.db:{t}prettyname".lower())
    return s if _real(s, t, "PrettyName") else None


def description(t):
    s = _table().get(f"thing.db:{t}description".lower())
    return s if _real(s, t, "Description") else None


def problems(t, sold=False, spell="", act=None, buy=1.0):
    """[(severity, why)] for an item of type t: placed or given (a name), or sold (a name, a description, a price, a
    use, a spell for a spell book, a price within Westwood's for the act's chapter)."""
    f = FACTS.get(t)
    out = []
    if f is None:
        return [("error", "is no item the player can pick up")] if sold else []
    if not name(t): out.append(("error", "has no name in the game's text (thing.db:%sPrettyName): add it to kit/items.py TEXT" % t))
    if not sold: return out
    if not description(t): out.append(("error", "has no description: add it to kit/items.py TEXT"))
    if not f["worth"]: out.append(("error", "has no price (no WORTH in thing.bin): a shop cannot sell it"))
    if not f["use"] and not (set(f["cls"]) & WORN) and t not in CHARMS:
        out.append(("error", "does nothing: it is no food, potion, weapon, armour or wand"))
    if SPELL_BOOKS.search(t) and (not spell or spell == "SPELL_INVALID"):
        out.append(("error", "is a spell book with no spell: it teaches nothing (give the ware a SpellID)"))
    if act and f["worth"] and f["worth"] * buy > CAP[chapter(act)]:
        out.append(("warning", f"sells at {f['worth'] * buy:.0f} gold: over {CAP[chapter(act)]}, the dearest thing "
                               f"Westwood's shops sell by chapter {chapter(act)}"))
    return out


def act_of(map_name):
    """The Hollow Choir act a map is (kit/campaign.py ACTS), or None."""
    try:
        from kit.campaign import ACTS
    except Exception:
        return None
    return next((a["n"] for a in ACTS if a["map"].lower() == str(map_name).lower()), None)


CHARMS_GO = """package PKG

// Charms (dystopiannox mapgen/kit/items.py CHARMS; QA round 1, nox12: "most of the new items don't seem to actually
// have a function"): items with no use of their own in the game, given one while carried. Every charmEvery frames a
// hurt player carrying one is restored by its amount.

import "github.com/noxworld-dev/noxscript/ns/v4"

const charmEvery = EVERY

var charmHeal = map[string]int{
HEALS}

func init() {
	ns.OnEachFrame(charmEvery, charmsTick)
}

func charmsTick() {
	for _, p := range ns.Players() {
		u := p.Unit()
		if u == nil || u.CurrentHealth() <= 0 || u.CurrentHealth() >= u.MaxHealth() {
			continue
		}
		for name, n := range charmHeal {
			if len(u.Items(ns.HasTypeName{name})) > 0 {
				u.RestoreHealth(n)
				break
			}
		}
	}
}
"""


def charms_go(pkg):
    heals = "".join(f"\t{json.dumps(t)}: {n},\n" for t, n in CHARMS.items())
    return CHARMS_GO.replace("package PKG", f"package {pkg}", 1).replace("EVERY", str(CHARM_EVERY)).replace("HEALS}", heals + "}")


def apply(spec):
    """charms.go into a map that has scripts (Spec.build): a charm the player carries in from another act works here."""
    if spec.scripts and "charms.go" not in spec.scripts:
        spec.scripts["charms.go"] = charms_go(spec.d["name"].lower())
        return True
    return False
