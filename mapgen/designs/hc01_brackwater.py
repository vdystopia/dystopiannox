"""The Hollow Choir, act 1: Brackwater (map Brackwatr; campaign/hollowchoir/BIBLE.md). A river town in a green oak wood
on the Brack, a slow river that widens into the Brack Pool where the barges tie up; the first of the realm's five
bells hangs in the Bell Shrine on its square. The town's plan is kit/hc_brackwater.py, shared with act 10 (LastBell,
the same town burning). Sections: the oak wood of the town and its roads (FORESTS["oak"]), the red wood of the old mill
upriver (FORESTS["dusk"]), the old brown wood downstream, the reed bank and the far clearing (FORESTS["ancient"]).

The story
- The hook: the player steps off Gorm's river barge onto Brackwater's quay at midnight. The shrine bell rang out once
  and stopped dead. Gorm sends the player up to the square.
- Brackwater: the square round its well; the Bell Shrine of Brother Edric, the watch house of Captain Ilsa Rook, the
  Bargeman's Rest, Doran Ashforge's smithy with its forge (S1), Wenna Fell's herb shop, Bram's river store, houses;
  the quay and the bargemen's houses on the Brack Pool; the town bridge to the south landing on the far bank; the
  ferry lane and the old bridge to the old mill upriver; the reed bank downstream; the River Gate on the road south-west
  toward the Mirewood.
- Main quest, the Stolen Stone (a robbery traced to a camp; a captive; choice A): bandits broke into the Bell Shrine
  at midnight, struck down Brother Edric and cut the Spirit Stone, the bell's clapper, out of the bell. Captain Ilsa
  hires the player and shuts the River Gate. Two of the band hold the far end of the town bridge to slow pursuit; their
  camp is downriver on the far bank, with a lookout who rouses the rest. With his crew dead, Rusk, their leader, a
  coward with a conscience, gives up: a man in grey of the Hollow Choir paid them in silver for the stone and took it
  west to the Mirewood at dusk, and the ringer's boy with it. Choice A: Rusk begs to be let go.
  - Let him go: he presses his lucky charm into the player's hand, his promise to repay (token RUSK_KNIFE), and slips
    off into the wood. Ilsa is cold about it and pays half.
  - Refuse: Rusk walks to Ilsa's cells himself; Ilsa gives the player the watch's warrant under her seal (token
    WATCH_SEAL) and the full wage.
  Either way Ilsa opens the River Gate: the road to the Mirewood (act 2) lies beyond.
- Side quests that run through the campaign begin here: Doran asks for starsteel, which only the deep mines of
  Greycrag hold, and gives his guild medallion for his cousin there (DORAN_LETTER); he shows the forge (S1): lay a
  blade by the anvil, stand on the black stone. Wenna's brother Tam, the bell-ringer's boy, went to ring the midnight
  bell and never came home; she gives her charm, a green stone (WENNA_ASK). Brother Edric asks for the verses of the
  ringing, carved on three of the founders' tablets far away (nothing carried: the verses are what act 10 reads).
- The Leeches (a bounty, act 1's own): Nell the eel-wife's traps on the reed bank east of the quay are overrun by
  giant leeches. She pays when they are dead.
- The Old Mill (a beast to put down, act 1's own): a troll came up the river and took Abel's mill across the old bridge.
  Abel pays with his father's longsword when it is dead (a blade to try at the forge), and walks home.
- The inn, the river store and Wenna's herb shop buy and sell. The bandits' chest, three caches in the wood and the
  houses' stores hold loot; every soul in town knows something.
- The exit: the road beyond the River Gate leads to the Mirewood (act 2).

Tokens: gives WATCH_SEAL or RUSK_KNIFE (choice A), DORAN_LETTER, WENNA_ASK, each once; reads none. (Edric's request
is not carried: kit/campaign.py.)

    py mapgen/designs/hc01_brackwater.py [seed]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL
from kit.identity import MapIdentity, AreaIdentity, BUILDINGS, rooms_sidecar
from kit.layout import square_px, px_square, bfs_distance
from kit.vegetation import Planter, FORESTS, TOWN_PLANTING
from kit.village import Village
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT
from kit import camps
from kit.posts import camp_posts
from kit.dressing import Exterior
from kit.mods import Mods
from kit.campaign import token, has, cast_person, voice, exit_next, CAST
from kit import hc_brackwater as HB

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else HB.SEED
NAME = "Brackwatr"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "hc01_brackwater")

# Warnings accepted, each with its reason (tests/qa.py)
QA_ACCEPT = [
    ("density.range", r"Few wall pieces per 100 floor tiles",
     "a river town: the Brack and the Brack Pool are about a tenth of the floor and carry only invisible shore walls, "
     "and the open streets of a town on two banks leave the forest islands little room (Land.thickets places what fits)"),
    ("composition", r".",
     "the rooms are furnished by the shared kit (kit/furnish.py, kit/archetypes.py), which at its present tuning "
     "leaves some rooms of every map built now a point under the house rules (the same warnings stand in "
     "Starwell's, Ambermere's, Mirewood's and OgreMarch's QA); each room was looked at in qa/rooms.png and "
     "reads as what it is: reported, not this design's to change"),
    ("rooms.stray", r"does not belong|do not belong",
     "the rooms are furnished by the shared kit (kit/furnish.py, kit/archetypes.py), which at its present tuning "
     "leaves some rooms of every map built now a point under the house rules (the same warnings stand in "
     "Starwell's, Ambermere's, Mirewood's and OgreMarch's QA); each room was looked at in qa/rooms.png and "
     "reads as what it is: reported, not this design's to change"),
    ("pieces", r".",
     "the rooms are furnished by the shared kit (kit/furnish.py, kit/archetypes.py), which at its present tuning "
     "leaves some rooms of every map built now a point under the house rules (the same warnings stand in "
     "Starwell's, Ambermere's, Mirewood's and OgreMarch's QA); each room was looked at in qa/rooms.png and "
     "reads as what it is: reported, not this design's to change"),
]

ID = MapIdentity(
    name=NAME,
    theme="a river town in a green oak wood on the Brack, which widens into the Brack Pool where the barges tie up: a "
          "square round a well, the Bell Shrine where the first of the five bells hangs, the watch house, an inn, the "
          "smithy, the herb shop and the river store; the quay on the pool, the town bridge to the south landing, the "
          "old bridge to the old mill upriver, the reed bank downstream; the bandits' camp on the far bank; the River "
          "Gate shut on the road to the Mirewood",
    environment="town", mood="midnight, alarm, a river town woken",
    areas=[AreaIdentity("docks", "the quay on the Brack Pool, where the barge ties up: the start"),
           AreaIdentity("pool", "the Brack Pool", landmark="the pool"),
           AreaIdentity("town", "Brackwater's square and its streets", landmark="Well"),
           AreaIdentity("lane", "the ferry lane at the town's upriver end, before the old bridge"),
           AreaIdentity("mill", "the old mill across the old bridge, a troll's den now"),
           AreaIdentity("south", "the south landing at the far end of the town bridge, a crossroads"),
           AreaIdentity("gate", "the River Gate, shut"),
           AreaIdentity("mire", "the road on toward the Mirewood: the way out"),
           AreaIdentity("camp", "the bandits' camp downriver on the far bank"),
           AreaIdentity("reeds", "the reed bank east of the quay, Nell's eel-traps"),
           AreaIdentity("glade", "a glade in the oak wood north-east of the square")],
    buildings=list(HB.BUILDINGS))

m = Spec(NAME, summary="Brackwater", description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"The Hollow Choir, act 1. Generated by Claude.", author="vdystopia (generated by Claude)", version="1",
         date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [112, 120, 152]            # midnight on the river: a cool, dim light
q = QuestBook(NAME)

REGIONS = dict(
    oak=dict(forest="oak", ground=("GrassNorm", "GrassSparse2", "GrassDense")),
    dusk=dict(forest="dusk", ground=("GrassNorm", "GrassSparse2", "GrassDense")),
    old=dict(forest="ancient", ground=("GrassNorm", "GrassDense", "GrassSparse2")),
)

# ---- 1-4. the plan: land, river, pool, bridges, quay, roads, square, buildings, yards, the River Gate ------------------
FURNISH = int(os.environ.get("HC_FURNISH", "0")) or None     # the rooms' furnishing draws (kit/hc_brackwater plan)
P = HB.plan(m, ID, wall_of=lambda r: FORESTS[REGIONS[r]["forest"]]["wall"], floor_of=lambda r: REGIONS[r]["ground"][0],
            seed=SEED, furnish_seed=FURNISH)
land, sm, placed, rng = P.land, P.sm, P.placed, P.rng
C = P.C
vc = C["town"]
gate_halves, gate_pts, gate_sq = P.gate

# ---- 5. the town's life ------------------------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Bargeman's Rest\nBeds, eel pie and river ale", "Sign"),
                     store=q.text("The River Store\nRope, lamps, arms and stores for the road", "Sign"),
                     smithy=q.text("Ashforge\nDoran Ashforge, smith", "Sign"),
                     apothecary=q.text("Fell's Herbs\nRemedies and potions", "Sign"),
                     village_chapel=q.text("The Bell Shrine\nThe first of the five bells", "Sign"))
for bid, b in placed:
    role = BUILDINGS[bid.role]
    for sc in role["scenes"]: vil.scene(b, sc, role=bid.role)
    if rng.random() < role["garden"]: vil.garden(b, size=(rng.randint(3, 5), rng.randint(2, 4)))
well_xy = square_px(vc[0] + 0.5, vc[1] - 0.5)
m.obj_px("Well", *well_xy)


def lamp(si, sj):
    x, y = square_px(si, sj)
    m.obj_px("StreetLampOrnate3", x, y); m.obj_px("StreetLampOrnate3Shadow", x - 15, y + 21)


vil.square_piece((vc[0] + 0.5, vc[1] - 0.5), 5, pole=lamp, per_side=1)
for r_ in REGIONS:
    g_ = REGIONS[r_]["ground"]
    land.ground_variety(m, base=g_[0], sparse=g_[1], dense=g_[2], clear=3, region=r_)

# ---- 6. the story's places ------------------------------------------------------------------------------------------
fenced = set().union(*({(y_.gi + a, y_.gj + b) for a in range(-2, y_.w + 2) for b in range(-2, y_.h + 2)}
                       for y_ in P.built)) if P.built else set()
south_c, camp_c, mill_c, lane_c, reeds_c, docks_c, gate_c, mire_c, glade_c, pool_c = (
    C[k] for k in ("south", "camp", "mill", "lane", "reeds", "docks", "gate", "mire", "glade", "pool"))


def off_road(c, clear=4.5, reach=12):
    """The square nearest `c` with no road within `clear` squares, on open land: a place beside its way, not on it."""
    near_road = bfs_distance(list(land.roads), land.squares, int(clear) + 1)
    cands = [s for s in land.squares if near_road.get(s, 99) >= clear and s not in land.taken_strict and
             s not in fenced and s not in land.water and math.hypot(s[0] - c[0], s[1] - c[1]) <= reach]
    s = min(cands, key=lambda s: math.hypot(s[0] - c[0], s[1] - c[1])) if cands else (int(c[0]), int(c[1]))
    return (s[0] + 0.5, s[1] - 0.5)


# the bandits' camp downriver on the far bank, in the old wood, open toward the camp road
camp_site = camps.camp_site(m, land, camp_c, reach=14, road_clear=3.5, room=7, avoid=fenced)
camp_way = sm.road_near(camp_site)
bandits = camps.bandit_camp(m, rng, land, camp_site, camp_way,
                            loot=[("Gold", {"Amount": 90}), "RedPotion", "RedPotion", "Quiver", "LeatherHelm"],
                            sleepers=4, tents=2, trade="bandit")
# the reed bank: Nell's eel-traps, baskets and a barrel by the water
rsc = camps.Scene(m, rng, land, reeds_c)
for k_, (r_, a_) in enumerate(((2.2, 0.4), (2.6, 1.9), (3.0, 3.6))):
    rsc.put(("Barrel", "Crate1", "Barrel2")[k_], *rsc.at(r_, a_))
# the old mill: the troll's leavings at its door
mill_b = sm.building_in("mill")
assert mill_b, "the old mill was not built"
mill_door = sm.outside_door(building=mill_b) or square_px(*mill_c)
msc = camps.Scene(m, rng, land, px_square(*mill_door))
for k_ in range(4):
    msc.put(rng.choice(("ArmBone", "LegBone", "Skull", "SackChestMedium1")), *msc.at(rng.uniform(2.4, 3.6), k_ * 1.6 + 0.3))
# caches in the wood, off the ways
caches = []
for near_, loot_, stump_ in ((mill_c, [("Gold", {"Amount": 45}), "CurePoisonPotion", "RedPotion"], True),
                             (glade_c, [("Gold", {"Amount": 50}), "LeatherBoots", "BluePotion"], False),
                             (camp_c, [("Gold", {"Amount": 40}), "RedPotion", "Quiver"], False)):
    s_ = sm.hidden_spot(near_, r=(9, 16))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
# signposts
dock = P.docks[0] if P.docks else None
gs_ = sm.road_near(((gate_sq[0] * 2 + south_c[0]) / 3, (gate_sq[1] * 2 + south_c[1]) / 3))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 1.5),
               q.text("THE RIVER GATE IS SHUT\nNobody leaves till the stone is found.\n- Ilsa Rook, Captain", "Sign"))
ls_ = sm.road_near(lane_c)
camps.signpost(m, land, (ls_[0] + 2.0, ls_[1] - 1.5), q.text("THE OLD BRIDGE\nTo the mill.", "Sign"))
qs_ = sm.road_near(docks_c)
camps.signpost(m, land, (qs_[0] + 2.0, qs_[1] - 1.5), q.text("BRACKWATER QUAY\nBarges to the Mirewood and the sea", "Sign"))

# ---- 7. planting, the start and the exit --------------------------------------------------------------------------------
keep = set()
for bid, b in placed:
    for d in b.entrances:
        di, dj = px_square(*d.px)
        keep |= {(di + a, dj + b2) for a in range(-2, 3) for b2 in range(-2, 3)}
vil.ground_bits(1.4)
planter = Planter(m, rng, land, "oak", keep_clear=keep | P.lane, settled=("town", "docks"),
                  forest_of=lambda s: REGIONS[P.section(land.region_of(s))]["forest"])
n_trees, n_small = planter.plant_all(groves=4, profile=TOWN_PLANTING)
piles = planter.rock_piles(max(4, len(land.squares) // 900))
vignettes = planter.forest_floor(max(6, len(land.squares) // 700))
P.ww.finish()
# the player steps off the barge at the foot of the dock
if dock:
    du_, dv_ = dock["start"]
    root = ((du_ + dv_) / 2 * CELL, (du_ - dv_) / 2 * CELL)
else:
    root = square_px(docks_c[0] + 0.5, docks_c[1] - 0.5)
dx_, dy_ = square_px(*docks_c)
dl_ = math.hypot(dx_ - root[0], dy_ - root[1]) or 1
start_xy = (root[0] + (dx_ - root[0]) / dl_ * 46, root[1] + (dy_ - root[1]) / dl_ * 46)
m.obj_px("PlayerStart", *start_xy)
exits = exit_next(sm, "mire", 1, prefix="MireExit")

# ---- 8. the people --------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
person, room_of, free_px = sm.person, sm.room_of, sm.free_px
mods = Mods(m, pop)
vx, vy = square_px(*vc)
# Gorm the bargemaster on the quay, beside where the player steps off
gx_, gy_ = start_xy[0] + (dy_ - root[1]) / dl_ * 52, start_xy[1] - (dx_ - root[0]) / dl_ * 52
person("Con03A", "Kenneth", gx_, gy_, "Gorm", face=start_xy)
# Captain Ilsa at the Bell Shrine's door; Brother Edric in the nave beside the altar, where they struck him down
shrine = room_of("village_chapel", "chapel")
assert shrine, "the Bell Shrine was not built with its nave"
il_ = sm.doorside("village_chapel", toward=(vx, vy)) or (vx, vy + 60)
cast_person(sm, "Ilsa", il_[0], il_[1], face=(vx, vy))
ex_, ey_ = sm.stand_px(shrine)
cast_person(sm, "Edric", ex_, ey_, face=free_px(shrine))
# Doran at his smithy's door; his journeyman at the forge inside (S1)
smithy = room_of("smithy", "smithy")
assert smithy, "the smithy was not built with its forge"
store = room_of("smithy", "storeroom")
smithy_b = sm.by_role["smithy"]
assert store and not any(math.dist(d.px, e.px) < 40 for d in store.doors for e in smithy_b.entrances),     "the smithy's stock room opens to the street: it cannot be Doran's locked strongroom"
forge = HB.place_forge(m, mods, sm, smithy, store)
dr_ = sm.doorside("smithy", toward=(vx, vy)) or (vx + 60, vy)
cast_person(sm, "Doran", dr_[0], dr_[1], face=(vx, vy))
# Wenna at her herb shop's door, watching the shrine
shrine_b = sm.by_role["village_chapel"]
sh_door = sm.outside_door(building=shrine_b) or (vx, vy)
wn_ = sm.doorside("apothecary", toward=sh_door) or (vx - 60, vy)
cast_person(sm, "Wenna", wn_[0], wn_[1], face=sh_door)
# Abel on the ferry lane before the old bridge, looking across at his mill
mill_bank, lane_bank = HB.bridge_ends(P, 1)[::-1]            # the far end (the mill's bank), the near end (the lane's)
lsc = camps.Scene(m, rng, land, px_square(*lane_bank))
ab_ = None
for r_, a_ in ((2.2, 0.8), (2.2, -0.8), (2.8, 1.6), (2.8, -1.6), (3.4, 2.4), (3.4, -2.4)):
    p_ = lsc.at(r_, math.atan2(lane_c[1] - mill_c[1], lane_c[0] - mill_c[0]) + a_)
    if lsc.ok(*p_): ab_ = square_px(*p_); break
ab_ = ab_ or square_px(lane_c[0] + 1.5, lane_c[1] - 0.5)
person("Con03A", "Osborn", ab_[0], ab_[1], "Abel", face=mill_bank)
# Nell at her door on the docks road, looking toward the reeds
fishers = [b for bid, b in placed if bid.role == "fisher"]
nl_ = (sm.doorside(building=fishers[0], toward=square_px(*reeds_c)) if fishers else None) or square_px(*docks_c)
person("Con02a", "Lydia", nl_[0], nl_[1], "Nell", face=square_px(*reeds_c))
# the gate guard on the town side of the River Gate
gq_ = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
sx_, sy_ = square_px(*south_c)
gdx, gdy = sx_ - gq_[0], sy_ - gq_[1]
gl = math.hypot(gdx, gdy) or 1
person("Con02a", "Mayor's_Guard", gq_[0] + 70 * gdx / gl + 26, gq_[1] + 70 * gdy / gl, "GateWarden", face=(sx_, sy_))
# Rusk at the head of his camp, by his tent and the take; his crew at their posts (kit/posts)
cposts = camp_posts(m, bandits, square_px(*camp_way), sit=2, tents=1, watch=2, work=0)
cast_person(sm, "Rusk", *cposts["leader"], face=square_px(*camp_way))
# Rusk's walk to the watch house (handed over), or off into the old wood (let go): laid once the map stands
wh_b = sm.by_role["barracks"]
wh_door = sm.doorside("barracks", toward=(vx, vy)) or (vx, vy)
rusk_cells = sm.journey("Rusk", "RuskCells", wh_door, look=(vx, vy))
# (let go, he slips away up the camp road toward the river road and the wide world)
far_ = sm.road_near((camp_c[0] + (south_c[0] - camp_c[0]) * 0.35, camp_c[1] + (south_c[1] - camp_c[1]) * 0.35))
rusk_away = sm.journey("Rusk", "RuskAway", square_px(far_[0] + 0.5, far_[1] - 0.5), look=square_px(*south_c))
# Abel's walk home over the old bridge
abel_home = sm.journey("Abel", "AbelHome", mill_door, look=square_px(*lane_c))
# shopkeepers: the inn, the river store, the herb shop (the smithy's floor is the forge's)
WARES = {"inn": [(6, "Bread"), (5, "Meat"), (4, "Cider"), (4, "RedApple"), (2, "RedPotion")],
         "store": [(3, "RedPotion"), (2, "BluePotion"), (3, "Quiver"), (1, "Bow"), (1, "CrossBow"), (2, "Longsword"),
                   (1, "BattleAxe"), (1, "Sword"), (1, "WoodenShield"), (1, "LeatherBoots"), (1, "LeatherHelm"),
                   (1, "LeatherArmor"), (1, "LeatherLeggings"), (1, "ChainCoif")],
         "apothecary": [(6, "RedPotion"), (4, "BluePotion"), (3, "CurePoisonPotion"), (1, "LesserFireballWand"),
                        (2, "SpellBook"), (1, "AmuletofNature")]}
GREET = {"inn": q.text("Bad business tonight, lad. Who robs a shrine at midnight? Strange times indeed! Eat while "
                       "there's still bread in the house!", "Shop"),
         "store": q.text("I can tell we'll get on famously! As long as you buy something, that is!", "Shop"),
         "apothecary": q.text("I hear the Captain's hiring. If you're going after them, take a potion or three.",
                              "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"apothecary": "ShopkeeperMagicShop", "store": "ShopkeeperWarriorsRealm"})
# townsfolk on their rounds, each with something to tell
FOLK = [("Con02a", "Tanya"), ("Con02a", "Clyde"), ("Con02a", "Julie"), ("Con03A", "Millard"), ("Con02a", "Jacob"),
        ("Con06a", "Townsman2"), ("Con07B", "Kayla"), ("Con07B", "Dorian")]
RUMOURS = [
    "Hurry! The Captain is down by the shrine. She's paying anyone who can swing a sword.",
    "A man in grey took a room at the Bargeman's last week. One day he was asking all about the bell, and the next "
    "he was gone!",
    "Rope pays, if nobody steals it.",
    "WHAT? The bell is... silent?",
    "That's it! First the shrine, then our houses. I'm sleeping with the poker tonight!",
    "Shouldn't you be chasing those bandits by now?",
    "Nell says the leeches on her eel-traps are big as dogs. I hear she'll pay to be rid of them!",
    "Old Abel lost his mill to a troll, they say. Strange things come up the river these days.",
]
for c_, r_ in ((camp_c, 18), (mill_c, 12), (reeds_c, 10), (south_c, 8), (glade_c, 8)):
    sm.keep_folk_away(c_, r_)
ring = sm.townsfolk(FOLK, vc, q=q, rumours=RUMOURS,
                    after=("ilsa_paid", "They say the bandits are dead and the Captain has opened the River Gate. "
                                        "Safe travels!"),
                    pics=("MaidenPic3", "MalePic7", "MaidenPic4", "Townsman3Pic", "MalePic8", "Townsman1Pic",
                          "MaidenPic2", "MalePic11"),
                    radius=7.0)
# the watch, each on a beat through the town
for k_, donor_ in enumerate(("Contest_Guard", "IxGuard2")):
    wx2, wy2 = ring[k_ * 4]
    person("Con02a", donor_, wx2, wy2, f"Watch{k_ + 1}", action=0)
    sm.beat(f"Watch{k_ + 1}", vc, radius=7.0, stops=7)

# ---- 9. the fights ----------------------------------------------------------------------------------------------------
# the rearguard at the far end of the town bridge, left to slow whoever follows
town_bank, far_bank = HB.bridge_ends(P, 0)
fb_sq = px_square(*far_bank)
rear = []
for k, (t_, a_) in enumerate((("Swordsman", 0.9), ("Archer", -0.9))):
    ang = math.atan2(south_c[1] - fb_sq[1], south_c[0] - fb_sq[0]) + a_
    x, y = square_px(fb_sq[0] + 0.5 + 3.2 * math.cos(ang), fb_sq[1] - 0.5 + 3.2 * math.sin(ang))
    n = f"Rearguard{k + 1}"
    pop.creature(t_, x, y, action="guard", face=town_bank, scr=n, aggr=0.83)
    rear.append(n)
# the crew about their camp: one at the fire, one by the tents, two watching the road
crew = []
for k, (x, y) in enumerate(cposts["sit"] + cposts["tent"]):
    n = f"Bandit{k + 1}"
    pop.creature("Swordsman", x, y, action="idle", face=bandits["fire"], scr=n, aggr=0.83)
    crew.append(n)
for k, (x, y) in enumerate(cposts["watch"]):
    n = f"CampWatch{k + 1}"
    pop.creature("Archer", x, y, action="guard", face=square_px(*camp_way), scr=n, aggr=0.83)
    crew.append(n)
B.sentry("CampWatch1", square_px(*camp_way), rouse=[n for n in crew if n != "CampWatch1"],
         shout="On the road! Up, lads, up!")
# the troll at the old mill's door
tx_, ty_ = mill_door
mdx, mdy = tx_ - square_px(*mill_c)[0], ty_ - square_px(*mill_c)[1]
mdl = math.hypot(mdx, mdy) or 1
pop.creature("Troll", tx_ + mdx / mdl * 50, ty_ + mdy / mdl * 50, action="guard", face=mill_bank, scr="MillTroll",
             aggr=0.83)
# the leeches on the reed bank by Nell's traps
leeches = []
for k, a_ in enumerate((0.3, 1.5, 2.7, 3.9, 5.1)):
    x, y = rsc.px(4.2 + 0.6 * (k % 2), a_)
    n = f"Leech{k + 1}"
    pop.creature("GiantLeech", x, y, action="guard", face=square_px(*docks_c), scr=n, aggr=0.83)
    leeches.append(n)
# the wood's own creatures by the forest's edge
sm.wild({"Wolf": 3, "Bat": 4, "SmallSpider": 3, "Spider": 1, "Urchin": 2}, away_from=vc, per100=0.5, gap=7,
        min_away=36, avoid=(south_c, camp_c, mill_c, lane_c, reeds_c, docks_c, gate_c, mire_c, gate_sq, glade_c,
                            px_square(*far_bank), px_square(*town_bank)))

story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]] + \
           [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)
# fish in the pool
fish = 0
for k in range(40):
    if fish >= 6: break
    a, r = rng.uniform(0, 6.28), rng.uniform(2.0, HB.LAKE_R * 0.7)
    s_ = (int(pool_c[0] + r * math.cos(a)), int(pool_c[1] + r * math.sin(a)) + 1)
    if s_ not in land.water or any((s_[0] + a2, s_[1] + b2) not in land.water for a2 in (-1, 0, 1) for b2 in (-1, 0, 1)):
        continue
    pop.creature("FishBig" if fish % 3 == 0 else "FishSmall", *square_px(s_[0] + 0.5, s_[1] - 0.5), action=0,
                 roamflag=255)
    fish += 1

# ---- 10. the story ----------------------------------------------------------------------------------------------------
SEAL, KNIFE = token("WATCH_SEAL"), token("RUSK_KNIFE")
LETTER, CHARM = token("DORAN_LETTER"), token("WENNA_ASK")
q.start([A.lock("RiverGate1"), A.lock("RiverGate2")] + [A.disable(n) for n in exits] +
        [A.print("The barge bumps against Brackwater's quay. Somewhere up in the town, a bell rings once and stops."),
         q.journal("Go up to the square and find the Captain of the watch.", HINT)])

# Gorm the bargemaster, on the quay
q.talker("Gorm", [
    q.say("They've opened the River Gate, I hear. I'll take on cargo at dawn and not before.",
          when=q.when(flag="ilsa_paid"), who="Gorm"),
    q.say("Hey, you'd best get up to the square. That bell never rings at midnight -- and now it's stopped dead.",
          who="Gorm")], voice={"desc": "A stout river bargeman in his fifties. Gruff, hoarse, carrying voice with a "
                                       "broad Bristol accent. Blunt and unhurried.", "seed": 61})

# Ilsa: the main quest, choice A's ending
q.talker("Ilsa", [
    q.say("The gate's open. Go after that stone, and watch the Mirewood. It eats people.",
          when=q.when(flag="ilsa_paid"), who="Ilsa"),
    q.say("So Rusk is on his way to my cells, and on his own feet! Well done! A man in grey, the Hollow Choir... "
          "and the stone gone west to the Mirewood. / Take this warrant, under my seal. Any watch or gate in the realm "
          "will know you for a friend of the law. Here's your wage -- the River Gate is open. Follow that stone!",
          when=q.when(flag="rusk_handed", not_="ilsa_paid"),
          do=[A.flag("ilsa_paid"), A.give(SEAL), A.gold(150),
              A.unlock("RiverGate1"), A.unlock("RiverGate2")] + [A.enable(n) for n in exits] +
             [q.done("Find the bandits who robbed the Bell Shrine."),
              q.journal("Follow the Spirit Stone west through the River Gate to the Mirewood.")], who="Ilsa",
          mood="Brisk and grudgingly pleased."),
    q.say("You let Rusk go?! He'll be halfway to the sea by morning. I'll not thank you for it... but the stone "
          "matters more than one river rat. / The Hollow Choir, the Mirewood -- that's where your road goes now. "
          "Here's half your wage. The River Gate is open. Go.",
          when=q.when(flag="rusk_freed", not_="ilsa_paid"),
          do=[A.flag("ilsa_paid"), A.gold(75), A.give("RedPotion"),
              A.unlock("RiverGate1"), A.unlock("RiverGate2")] + [A.enable(n) for n in exits] +
             [q.done("Find the bandits who robbed the Bell Shrine."),
              q.journal("Follow the Spirit Stone west through the River Gate to the Mirewood.")], who="Ilsa",
          mood="Cold and clipped, angry but controlled."),
    q.say("Their camp's broken? Then find Rusk. He'll know where the stone went.",
          when=q.when(flag=q.dead(*crew), not_="ilsa_paid"), who="Ilsa"),
    q.say("The trail's going cold, sellsword. Move.", when=q.when(flag="ilsa_told"), who="Ilsa"),
    q.say("You're off the barge? Then you came in on a bad night. Brackwater -- the town of the first bell! And "
          "now the bell is dumb as a stone! / Bandits broke into the shrine at midnight and cut the Spirit Stone out "
          "of the bell -- its clapper. Track them to their camp downriver, over the town bridge, and bring me the "
          "stone and Rusk, who leads them. The watch pays a fair wage.",
          do=[A.flag("ilsa_told"), A.stage("main", 1),
              q.journal("Find the bandits who robbed the Bell Shrine.")], who="Ilsa")],
    voice=voice("Ilsa"), title=CAST["Ilsa"]["title"])

# the rearguard at the bridge, the camp and Rusk
q.near(*far_bank, 210, [A.hunt(n) for n in rear] + [A.print("Two figures rise from the reeds at the end of the "
                                                            "bridge: the bandits left a rearguard!")])
q.near(*bandits["fire"], 320, [A.print("Tents, a fire and a cart by the water: the bandits' camp.")])
q.on_all_dead(crew, [A.flag("camp_clear"), A.print("The last of Rusk's crew falls. Someone whimpers by the tents.")])
turn_crew = [A.hunt(n) for n in crew]
q.talker("Rusk", [
    q.say("I'm going, I'm going! You'll not see Rusk again... not unless you need him.",
          when=q.when(flag="rusk_freed"), who="Rusk"),
    q.say("Ilsa's cells are dry, at least. Drier than the river.", when=q.when(flag="rusk_handed"), who="Rusk"),
    q.say("Aaah! No! Don't cut me! / It's you -- the one off the barge?! I only rowed the boat! A man in grey paid us "
          "in silver for the stone. The Hollow Choir, he called them. He took it west to the Mirewood at dusk -- and "
          "the ringer's boy with it! / Let me go, and I'll owe you a life. I swear it on my mother's grave. Will you "
          "let me go?",
          when=q.when(flag=q.dead(*crew), not_="rusk_handed"), ask=True,
          do=[A.flag("rusk_freed"), A.give(KNIFE), A.walk("Rusk", rusk_away),
              A.print("Rusk presses his lucky charm into your hand: his promise to repay you. Then he is off into the "
                      "trees."),
              q.note("NOTE: According to Rusk, the Hollow Choir took the Spirit Stone and the ringer's boy west to the "
                     "Mirewood.")],
          else_=[A.flag("rusk_handed"), A.walk("Rusk", rusk_cells),
                 q.tell("Rusk", "Fine, then... I'll walk to Ilsa's cells myself. Better a cell than the river."),
                 q.note("NOTE: According to Rusk, the Hollow Choir took the Spirit Stone and the ringer's boy west to "
                        "the Mirewood.")],
          who="Rusk", mood="Terrified, gabbling, then wheedling."),
    q.say("Keep away from me! Lads! Lads, he's here!", do=turn_crew, who="Rusk")],
    voice=voice("Rusk"), title=CAST["Rusk"]["title"])

# Brother Edric: the Last Verse begins
q.talker("Edric", [
    q.say("Any tablet, any verse. I will be here, praying they still read true.",
          when=q.when(flag="edric_asked"), who="Edric"),
    q.say("That saddens me. Think on it again, I pray -- the bell will not wait forever. Will you look for the verses?",
          when=q.when(flag="edric_refused"), ask=True,
          do=[A.flag("edric_asked"), q.journal("Bring Brother Edric the verses of the founders' tablets.")],
          else_=[q.tell("Edric", "Then go with my blessing, and nothing else.")], who="Edric"),
    q.say("Greetings, young traveller. I surmise the Captain has told you of our loss. / The founders carved the words "
          "of the ringing on three stone tablets -- far from here, and long forgotten. Without the stone the bell is "
          "dumb, and without the words it may never ring true again. / If your road passes a founder's tablet, rub its "
          "verse onto a stone and bring it to me. Will you?",
          ask=True, do=[A.flag("edric_asked"), q.journal("Bring Brother Edric the verses of the founders' tablets.")],
          else_=[A.flag("edric_refused"), q.tell("Edric", "Then go with my blessing, and nothing else.")],
          who="Edric")],
    voice=voice("Edric"), title=CAST["Edric"]["title"])

# Doran: the Starsteel Blade begins, and the forge
q.talker("Doran", [
    q.say("Been to Greycrag yet? No... I'm too old to go myself. The forge is hot, though. Lay a blade by the anvil "
          "and stand on the black stone, and my journeyman will work it for the price of the coal.",
          when=q.when(flag="doran_asked"), who="Doran"),
    q.say("Changed your mind about Greycrag? The medallion's still here, and so am I. Will you take it?",
          when=q.when(flag="doran_refused"), ask=True,
          do=[A.flag("doran_asked"), A.give(LETTER),
              q.journal("Carry Doran's medallion to the Greycrag forge and find him starsteel.")],
          else_=[q.tell("Doran", "Suit yourself. The forge is hot, if you've a blade to work.")], who="Doran"),
    q.say("Thieving river rats! They broke our bell and took my best tongs besides! / I'm Doran Ashforge. All my life "
          "I've wanted one thing -- to work starsteel. Only the deep mines of Greycrag hold it. / If your road ever "
          "takes you there, show my guild medallion to my cousin at the Greycrag forge -- any smith of our guild will "
          "know it -- and bring the starsteel home. Do that, and I'll make you a blade they'll sing of. Will you "
          "take it?",
          ask=True, do=[A.flag("doran_asked"), A.give(LETTER),
                        q.journal("Carry Doran's medallion to the Greycrag forge and find him starsteel.")],
          else_=[A.flag("doran_refused"), q.tell("Doran", "Bah. Then the starsteel stays in the dark, where it's "
                                                          "always been.")],
          who="Doran")],
    voice=voice("Doran"), title=CAST["Doran"]["title"])

# Wenna: the Missing Brother begins
q.talker("Wenna", [
    q.say("Please, I beg you. Find my brother, wherever they took him.", when=q.when(flag="wenna_asked"), who="Wenna"),
    q.say("Ohhh, where can he be? My brother Tam went up to ring the midnight bell, and he never came home. Nobody "
          "has seen him since the robbery. / Take my charm, this green stone. If you find him, show it to him -- "
          "he'll know you come from me. Will you look for Tam?",
          ask=True, do=[A.flag("wenna_asked"), A.give(CHARM),
                        q.journal("Find Wenna's brother Tam and bring him home.")],
          else_=[q.tell("Wenna", "Then I'll pray someone else will.")], who="Wenna", mood="Anxious, close to tears.")],
    voice=voice("Wenna"), title=CAST["Wenna"]["title"])

# the gate warden and the watch
q.talker("GateWarden", [
    q.say("Captain says you may pass. Off you go, then -- and good riddance to the robbers!",
          when=q.when(flag="ilsa_paid"), who="Guard"),
    q.say("The River Gate stays shut tonight, by the Captain's order. Nobody leaves till the stone is found! Off with "
          "you!", who="Guard")])
for k_ in range(2):
    q.talker(f"Watch{k_ + 1}", [
        q.say("The Captain's in a better mood. Thank you for that.", when=q.when(flag="ilsa_paid"), who="Watch"),
        q.say(("Only the watch goes in the shrine tonight! Speak to the Captain at the door.",
               "I'd speak to the Captain first... / unless you want a night in a cell.")[k_], who="Watch")])
    q.portrait(f"Watch{k_ + 1}", ("Warrior3Pic", "IxGuard2Pic")[k_])

# the Leeches: Nell's eel-traps
q.on_all_dead(leeches, [A.flag("leeches_dead"), A.print("The last leech bursts in the reeds.")])
q.talker("Nell", q.errand(
    "Nell", "leeches",
    offer="Help! Oh, help me, stranger! Leeches as long as my arm have crawled out of the reeds and onto my "
          "eel-traps, east along the bank! / Kill them for me and I'll owe you till the day I die! Will you?",
    refusal="Then my eels feed the leeches, and my children feed on nothing.",
    reminder="Are they dead yet? Hurry, before they eat the lot!",
    thanks="They're dead? Thank goodness! What can I give you for it?! / Coin, is it? Well, then... here's my eel "
           "money, and a potion for your trouble.",
    after="Bless you again, stranger!",
    objective="Kill the leeches at Nell's traps east of the quay.",
    done=q.when(flag=q.dead(*leeches)),
    reward=[A.gold(60), A.give("RedPotion")]))

# the Old Mill: Abel and the troll
q.on_death("MillTroll", [A.flag("troll_dead"), A.print("The troll crashes down in the mill yard and does not get up.")])
q.talker("Abel", [
    q.say("Mill's mine again. Come by for bread, any day.", when=q.when(flag="abel_paid"), who="Abel"),
    q.say("In a better week the whole lane would drink to a dead troll! Well done, lad! But the shrine's bell is "
          "still dumb, and the troll was the least of it. / Here -- my father's sword, and my purse, with the thanks "
          "of every hungry belly on the lane! I'm going home.",
          when=q.when(flag=q.dead("MillTroll"), not_="abel_paid"),
          do=[A.flag("abel_paid"), A.give("Longsword"), A.gold(70), A.walk("Abel", abel_home),
              q.done("Kill the troll at Abel's mill across the old bridge.")], who="Abel"),
    q.say("I can hear him from here, smashing my millstones! Go quickly!", when=q.at("mill", 1), who="Abel"),
    q.say("Blast it! Where were you yesterday, lad!? A troll came up the river and took my mill on the far bank -- "
          "and he'd have had me too if I hadn't run like a hare! / But I left everything behind -- my grain, my "
          "stones, my father's sword! Now the whole lane will go without bread! / Cross the old bridge to my mill, "
          "west of here. Kill that troll, or Brackwater goes hungry!",
          do=[A.stage("mill", 1), q.journal("Kill the troll at Abel's mill across the old bridge.")], who="Abel")])
q.near(*mill_door, 260, [A.print("The old mill. Something big has been gnawing on the door.")])

for who_, pic_ in (("Gorm", "Townsman3Pic"), ("Ilsa", "IngridPic"), ("Edric", "ArchivistPic"),
                   ("Doran", "QuarterMasterPic"), ("Wenna", "MaidenPic4"), ("Rusk", "MalePic9"),
                   ("Nell", "MaidenPic6"), ("Abel", "Miner2Pic"), ("GateWarden", "Warrior2Pic")):
    q.portrait(who_, pic_)

mods.attach(sm.B)
m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())

# ---- 11. the exteriors' dressing: the empty ground filled with the town's and the wood's things --------------------------
dressed = Exterior(m, land, "green", placed=placed).dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed, os.path.join(OUT, f"{NAME}.rooms.json"), yards=P.built)
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS", "VOICE"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: "
          f"{', '.join(sm.missed) or 'none'}) | trees {n_trees} | shops {n_shops} | caches {len(caches)} | opened "
          f"{len(opened)} | lines {len(q.strings)} | yards {', '.join(y_.kind for y_ in P.built) or 'none'} | fish "
          f"{fish} | docks {len(P.docks)} | forge {forge} | dressing {sum(dressed.values())} groups")
