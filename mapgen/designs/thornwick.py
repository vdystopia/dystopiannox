"""Thornwick: a frontier market town on the King's Road, and the story of the Red Hand.

The first map with a whole story (overnight brief 2026-10-04): a start, fights, rewards, missions and an exit, every
creature placed for a reason. Built with the town lab's pipeline (generator v3, the 2026-10-04 house rules).

The story
- The player comes up the King's Road from the south and finds Tobin the carter beside his plundered wagon: the Red
  Hand robbed him, and some of them are still in the trees by the road. He sends the player to the reeve.
- Just past the wreck, in a grove off the road, four of the Red Hand sit round their fire with crates of Tobin's
  goods. They burst out of the trees when the player passes on the road. Tobin pays for their deaths.
- Thornwick: the reeve, Aldric, has barred the north gate, the only road on, until the Red Hand is broken. Their
  camp lies deep in the old pines to the north-west, past the graveyard. Garrick the Red leads them.
  Garrick dead, the reeve pays the bounty and opens the gate; the road north (the map's exit) is the way out.
- The Varn Emerald: Mirela, at the inn, asks the player to fetch her grandmother's emerald from the Varn crypt behind
  the chapel. Father Odo sealed it when the Varn dead began to walk; Mirela has a copy of the key. With the emerald
  the player chooses: give it to Mirela for gold, or to Father Odo, who lays the dead to rest and blesses the player.
- Wolves at the Mill: Hobb the miller's goats are being taken by a wolf pack denned in the east wood.
- The trader, the smith and the innkeeper buy and sell. Chests hold loot: the bandits' take, the crypt's grave goods,
  and three caches hidden in the woods.

    py mapgen/designs/thornwick.py [seed]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, role_size, rooms_sidecar
from kit.layout import Land, square_tile, square_px, px_square, point_cell, cell_square
from kit.water import Waterworks
from kit.vegetation import Planter, FORESTS, TOWN_PLANTING
from kit.village import Village, _squares_of
from kit.building import generate_building
from kit.originality import furnish_original
from kit.npcs import Population
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT
from kit import yards as Y
from kit import camps
from kit.story import StoryMap

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7
rng = random.Random(SEED)
NAME = "Thornwick"
FOREST = "deciduous"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "thornwick")
NEXT_MAP = "TNorth"                    # the road north: the exit leads there
STOCK = r"C:\GOG Games\Nox\maps"


def uv(X, Y):
    """uv of a point given in map squares as seen on screen (X right, Y down, 0..255)."""
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="a frontier market town at the end of the King's Road, its north gate barred while the Red Hand bandits "
          "rob the road; a chapel with an old family's crypt, a mill by the east wood, a bandit camp in the north-west "
          "pines",
    environment="town", mood="uneasy, watchful",
    areas=[AreaIdentity("south", "where the King's Road comes in from the south: the player's start"),
           AreaIdentity("fork", "the bend in the road where the wreck lies and the grove path leaves it"),
           AreaIdentity("grove", "the bandits' lookout grove off the road"),
           AreaIdentity("town", "the square and the streets round it", landmark="Fountain"),
           AreaIdentity("graves", "the graveyard west of the town"),
           AreaIdentity("pines", "the old pine wood on the way to the camp"),
           AreaIdentity("camp", "the Red Hand's camp deep in the pines"),
           AreaIdentity("mill", "the mill and its field on the east road"),
           AreaIdentity("den", "the wolves' den in the east wood"),
           AreaIdentity("gate", "the north gate, barred"),
           AreaIdentity("north", "the King's Road going on north: the way out"),
           AreaIdentity("ford", "the stream the town is named for, and the rope bridge over it"),
           AreaIdentity("farm", "the Pells' farm in the south-east, its fields and orchard"),
           AreaIdentity("tower", "the old watchtower's stump in the north-east wood, an ogre's lair now")],
    buildings=[BuildingIdentity("manor", "town", "the reeve's hall", "Aldric the reeve"),
               BuildingIdentity("inn", "town", "The Lantern", "the innkeeper"),
               BuildingIdentity("store", "town", "the general store", "the trader"),
               BuildingIdentity("smithy", "town", "the forge", "the smith"),
               BuildingIdentity("chapel", "town", "the chapel", "Father Odo"),
               BuildingIdentity("home", "town", "", "a family"), BuildingIdentity("home", "town", "", "a family"),
               BuildingIdentity("home", "town", "", "a family"), BuildingIdentity("cottage", "town", "", "an old couple"),
               BuildingIdentity("cottage", "town", "", "a widow"),
               BuildingIdentity("mill", "mill", "the mill", "Hobb the miller"),
               BuildingIdentity("home", "farm", "the farmhouse", "the Pell family")])

m = Spec(NAME, summary="Thornwick", description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"Generated by Claude.", author="vdystopia (generated by Claude)", version="1", date="2026", type=SOLO,
         minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [140, 136, 118]
q = QuestBook(NAME)

# ---- 1. the plan: the road from the south through the town to the north gate, the side ways off it ----------------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"south": ((120, 226), 22), "fork": ((122, 196), 14), "grove": ((92, 190), 15),
         "town": ((128, 128), 100), "graves": ((66, 132), 22), "pines": ((60, 90), 16), "camp": ((50, 50), 30),
         "mill": ((196, 152), 24), "den": ((226, 112), 18), "gate": ((150, 66), 14), "north": ((160, 26), 14),
         "farm": ((196, 218), 20), "tower": ((214, 54), 22)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "town")
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_ in (("south", "fork", 14, True), ("fork", "town", 14, True), ("town", "gate", 13, True),
                          ("gate", "north", 12, True), ("town", "graves", 12, True), ("town", "mill", 13, True),
                          ("fork", "grove", 9, False), ("graves", "pines", 10, False), ("pines", "camp", 10, False),
                          ("mill", "den", 10, False), ("south", "farm", 12, True), ("den", "tower", 10, False)):
    land.link(a_, b_, w_, bend=0.22 if road_ else 0.3, road=road_, pockets=(1, 2) if road_ else (0, 1))
land.blends(m)

# the ford the town is named for: a stream across the whole south of the map, from the west wood to the east wood,
# flowing straight under the road between the fork and the town where a rope bridge carries it (Westwood's stream
# bridges are rope-bridge kits); planned now, with the road, so nothing is built on it
cross = land.plan_crossing("fork", "town", t=0.45, approach=8)
C = cross["uv"]
fu, fv = cross["flow"]
W_, E_ = uv(42, 150), uv(214, 180)          # it comes out of the forest west of the graves and goes back in past the mill
if (W_[0] - C[0]) * fu + (W_[1] - C[1]) * fv > 0: fu, fv = -fu, -fv        # (fu, fv) points toward the east end
STREAM = [W_, uv(70, 156), (C[0] - 14 * fu, C[1] - 14 * fv), C, (C[0] + 14 * fu, C[1] + 14 * fv), uv(185, 174), E_]
land.reserve_band(STREAM, 3.5)

# ---- 2. the centre: the square and its fountain, the streets leaving it --------------------------------------------
land.paint_square(m, "town", 14, "RoughCobble")
vc = land.areas["town"]["c"]
land.taken |= {(int(vc[0]) + a, int(vc[1]) + 1 + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}
land.paint_roads(m, "DirtDark2", width_squares=2.8, skip=land.reserved)

# ---- 3. buildings from the square outwards, never beside the bandits' grove or the wreck; doors, paths, rooms -----
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"grove": 13, "fork": 9, "south": 8})
by_role = sm.by_role
sm.connect_and_furnish()

# ---- the graveyard beside the chapel's road, a field by the mill ---------------------------------------------------
yards = []
for kind_, area_, rs_ in (("graveyard", "graves", (0, 4, 8)), ("field", "mill", (10, 14, 18)),
                          ("field", "farm", (8, 11, 14)), ("orchard", "farm", (8, 11, 14)), ("field", "farm", (10, 13, 16))):
    c_ = land.areas[area_]["c"]
    near_ = [(c_[0] + r * math.cos(a * math.pi / 6), c_[1] + r * math.sin(a * math.pi / 6)) for r in rs_ for a in range(12)]
    y_ = Y.plan_any(land, rng, kind_, near_)
    if y_: yards.append(y_)
    else: print(f"no room for the {kind_}")

# ---- 4. the land grows round everything, ending in the forest wall ---------------------------------------------------
land.carve(margin=3.5)
# the story's places stay open ground, and the side paths stay open: no clump of forest on them
lane_ = sm.keep_open({"grove": 6, "camp": 8, "den": 5, "fork": 3, "tower": 7})
clumps = land.thickets(160, size=(0.9, 1.8), clear=1, avoid=frozenset(lane_ & land.squares))
land.open_links()
land.apply(m, wall=FORESTS[FOREST]["wall"], floor="GrassNorm")
built = []
for y_ in yards:
    if not y_.plot <= land.squares:
        print(f"the {y_.kind} lies off the land"); continue
    Y.build(m, rng, land, y_)
    built.append(y_.kind)


# ---- the water: the stream dug into the land, the rope bridge on the planned crossing --------------------------------
ww = Waterworks(m, rng, inside=lambda x, y: m.floor.get((x, y), "").startswith(("Grass", "Dirt")))
brook = ww.stream(STREAM, width=2.6, wiggle=1.4, calm=[(C, 16)])
span = 10
a_uv, b_uv = ((C[0] - span, C[1]), (C[0] + span, C[1])) if cross["axis"] == "u" else ((C[0], C[1] + span), (C[0], C[1] - span))
ww.rope_bridge(a_uv, b_uv, kit=cross["kit"])
for b_ in ww.bodies:
    for t in b_.tiles:
        if "Water" in m.floor.get(t, ""): land.water.add(cell_square(*t))


# ---- the north gate: a stone wall across the road from forest to forest, a barred double gate in it -------------------
def road_square_near(X, Y):
    """The road square nearest a screen point (squares)."""
    tx, ty = (X + Y) / 2, (X - Y) / 2
    return min(land.roads, key=lambda s: (s[0] - tx) ** 2 + (s[1] - ty) ** 2)


# the gate stands on the forest road beyond the gate clearing, the wall square across the road
gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "north"), prefix="NorthGate")

# ---- the old watchtower in the north-east wood --------------------------------------------------------------------
tower_c = land.areas["tower"]["c"]
tower = camps.ruined_tower(m, rng, land, tower_c, land.areas["den"]["c"],
                           loot=["GreatSword", ("Gold", {"Amount": 150}), "BluePotion", "OrnateHelm"], size=(9, 9))

# ---- 5. the town's life ------------------------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Lantern\nFood, drink and a bed", "Sign"),
                     chapel=q.text("The Chapel of the Ford", "Sign"))
for bid, b in placed:
    role = BUILDINGS[bid.role]
    for sc in role["scenes"]: vil.scene(b, sc, role=bid.role)
    if rng.random() < role["garden"]: vil.garden(b, size=(rng.randint(3, 5), rng.randint(2, 4)))
vil.fountain_square(vc, 7)
land.ground_variety(m, clear=3)

# ---- 6. the scenes of the story, before the planting so the trees keep clear of them --------------------------------
fork_c = land.areas["fork"]["c"]; south_c = land.areas["south"]["c"]
road_dir = math.atan2(fork_c[1] - south_c[1], fork_c[0] - south_c[0])
# the wreck: on the verge where the road bends at the fork
wsq = min((s for s in land.squares if s not in land.roads and s not in land.taken and
           1.0 <= min(math.hypot(s[0] - r[0], s[1] - r[1]) for r in land.roads if abs(r[0] - fork_c[0]) + abs(r[1] - fork_c[1]) < 14) <= 2.5),
          key=lambda s: math.hypot(s[0] - (fork_c[0] + south_c[0]) / 2, s[1] - (fork_c[1] + south_c[1]) / 2))
wreck = camps.wagon_wreck(m, rng, land, (wsq[0] + 0.5, wsq[1] - 0.5), road_dir)
# the grove's lookout camp: the fire in the middle of the grove, open toward the road
grove_c = land.areas["grove"]["c"]
ambush_camp = camps.bandit_camp(m, rng, land, (grove_c[0], grove_c[1]), fork_c,
                                loot=[("Gold", {"Amount": 60}), "RedPotion", "RedPotion", "Bow", ("Quiver", None, 1)],
                                sleepers=3, tents=1)
# the Red Hand's camp
camp_c = land.areas["camp"]["c"]; pines_c = land.areas["pines"]["c"]
red_camp = camps.bandit_camp(m, rng, land, (camp_c[0], camp_c[1]), pines_c,
                             loot=[("Gold", {"Amount": 150}), "BluePotion", "RedPotion", "RedPotion", "ChainCoif",
                                   "Longsword"], sleepers=6, tents=3)
# the wolves' den, its mouth toward the mill path
den_c = land.areas["den"]["c"]; mill_c = land.areas["mill"]["c"]
den_spots = camps.wolf_den(m, rng, land, (den_c[0], den_c[1]), mill_c)
# caches hidden in the woods, off the ways: by the pine path, in the east wood, behind the graveyard
edge = land.edge_distance()
hidden_spot = sm.hidden_spot
caches = []
for near_, loot_, stump_ in ((pines_c, [("Gold", {"Amount": 45}), "CurePoisonPotion", "RedPotion"], True),
                             (den_c, [("Gold", {"Amount": 70}), "LeatherBoots", "RedPotion"], False),
                             (land.areas["graves"]["c"], [("Gold", {"Amount": 35}), "BluePotion", "SpellBook"], False)):
    s_ = hidden_spot(near_)
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
# signposts
camps.signpost(m, land, (south_c[0] + 2.5, south_c[1] - 1.5),
               q.text("Thornwick, one league north.\nTravellers: the road is watched. Keep to it and keep moving.", "Sign"))
gs_ = road_square_near(AREAS["gate"][0][0] + 4, AREAS["gate"][0][1] + 8)
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 0.5),
               q.text("BY ORDER OF THE REEVE\nThe north road is closed until the Red Hand is dealt with.", "Sign"))

keep = set()
for bid, b in placed:
    for d in b.entrances:
        di, dj = px_square(*d.px)
        keep |= {(di + a, dj + b2) for a in range(-2, 3) for b2 in range(-2, 3)}
vil.ground_bits(1.6)
planter = Planter(m, rng, land, FOREST, keep_clear=keep | lane_)      # no tree stands in a forest path
n_trees, n_small = planter.plant_all(groves=4, profile=TOWN_PLANTING)
piles = planter.rock_piles(max(4, len(land.squares) // 900))
vignettes = planter.forest_floor(max(6, len(land.squares) // 700))
start_xy = square_px(south_c[0] + 0.5, south_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)

# the exit: beyond the gate where the road leaves the map
sm.exit_to("north", NEXT_MAP, prefix="NorthExit")

# ---- 7. the people, each with a reason to be where they stand ---------------------------------------------------------
pop, B = sm.pop, sm.B
room_of, free_px, person = sm.room_of, sm.free_px, sm.person
outside_door = lambda role: sm.outside_door(role)


# Tobin the carter, beside his wagon
tx, ty = wreck["carter"]
person("Con02a", "Bryan", tx, ty, "Tobin", face=start_xy)
# the reeve in his great hall
gh = room_of("manor", "great_hall")
rx, ry = free_px(gh) if gh else square_px(vc[0], vc[1])
person("Con02a", "Mayor_Theogrin", rx, ry, "Aldric")
# Mirela at the inn
tv = room_of("inn", "tavern")
mx, my = free_px(tv) if tv else square_px(vc[0] + 3, vc[1])
person("Con02a", "Joyce", mx, my, "Mirela")
# Father Odo before his altar
ch = room_of("chapel", "chapel")
ox, oy = free_px(ch) if ch else square_px(vc[0] - 3, vc[1])
person("Con04c", "Keeper", ox, oy, "FatherOdo")
# Hobb at his door
hx, hy = outside_door("mill") or square_px(*mill_c)
person("Con03A", "Osborn", hx + 20, hy + 10, "Hobb")
# the gate guard, inside the gate
gx, gy = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
vx, vy = square_px(*vc)
gdx, gdy = vx - gx, vy - gy; gl = math.hypot(gdx, gdy) or 1
person("Con02a", "Mayor's_Guard", gx + 70 * gdx / gl + 30, gy + 70 * gdy / gl, "GateGuard", face=(vx, vy))
person("Con02a", "IxGuard1", gx + 70 * gdx / gl - 30, gy + 70 * gdy / gl, "GateGuard2", face=(vx, vy))

# old Brannoc, the smith's father, on the bench outside the forge
bx_, by_ = outside_door("smithy") or square_px(vc[0] + 4, vc[1])
person("Con02a", "Jacob", bx_ - 25, by_ + 15, "Brannoc", face=(vx, vy))
# Pell the farmer by his door
farm_home = sm.building_in("farm")
px_, py_ = (sm.outside_door(building=farm_home) if farm_home else None) or square_px(*land.areas["farm"]["c"])
person("Con03A", "Millard", px_ + 20, py_ + 15, "Pell")
# shopkeepers behind their counters (the spots the furnisher left), and the smith at his forge
WARES = {"store": [(4, "RedPotion"), (3, "BluePotion"), (2, "CurePoisonPotion"), (4, "RedApple"), (2, "Meat"),
                   (2, "Quiver"), (1, "Bow"), (1, "LeatherBoots"), (1, "LeatherHelm"), (1, "LeatherArmor")],
         "inn": [(6, "RedApple"), (5, "Meat"), (4, "Cider"), (2, "RedPotion")],
         "smithy": [(2, "Sword"), (1, "Longsword"), (1, "MorningStar"), (1, "WarHammer"), (1, "WoodenShield"),
                    (1, "SteelShield"), (1, "ChainCoif"), (1, "ChainTunic"), (1, "ChainLeggings"), (1, "LeatherArmor")]}
GREET = {"store": q.text("Welcome to my shop! Potions, food and gear for the road. Since the Red Hand took the road, "
                         "I sell more arrows than apples.", "Shop"),
         "inn": q.text("Welcome to the Lantern. Sit, eat. If you are going north you'll have a long wait.", "Shop"),
         "smithy": q.text("Steel for sale. Good steel, too: you'll want it if you mean to go after the Red Hand.", "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"smithy": "ShopkeeperWarriorsRealm"})

# townsfolk on their rounds between the square and the doorsteps
FOLK = [("Con02a", "Lydia"), ("Con02a", "Tanya"), ("Con02a", "Julie"), ("Con02a", "Heckler"), ("Con02a", "Morgan"),
        ("Con03A", "Millard"), ("Con02a", "Clyde"), ("Con08a", "Gretchen")]
ring = sm.townsfolk(FOLK, vc)

# ---- 8. the fights ------------------------------------------------------------------------------------------------
# the grove's lookouts round their fire, who come out of the trees when the player passes on the road
ambushers = []
for k, (x, y) in enumerate(ambush_camp["seats"][:3] + [ambush_camp["lookout"]]):
    t = "Archer" if k == 3 else "Swordsman"
    n = f"Lookout{k + 1}"
    pop.creature(t, x, y, action="idle", face=ambush_camp["fire"] if k < 3 else square_px(*fork_c), scr=n, aggr=0.5,
                 sight=60 if k < 3 else 150)
    ambushers.append(n)
# the Red Hand at their camp: Garrick by his fire, his men round it, archers watching the way in
redhand = []
gx_, gy_ = red_camp["leader"]                  # before his awning, where the take is
pop.creature("Swordsman", gx_, gy_, action="guard", face=square_px(*pines_c), scr="Garrick", aggr=0.83,
             HealthMultiplier=3.0)
for k, (x, y) in enumerate((red_camp["seats"][:2] + red_camp["posts"] + red_camp["seats"][2:])[:4]):
    n = f"RedHand{k + 1}"
    pop.creature("Swordsman", x, y, action="idle", face=red_camp["fire"], scr=n, aggr=0.83)
    redhand.append(n)
lx, ly = red_camp["lookout"]
for k in range(2):
    n = f"RedArcher{k + 1}"
    pop.creature("Archer", lx + (k * 2 - 1) * 40, ly, action="guard", face=square_px(*pines_c), scr=n, aggr=0.83)
    redhand.append(n)
B.sentry("RedArcher1", square_px(*pines_c), rouse=["Garrick"] + redhand[:4], shout="The Red Hand! To arms!")
# the town watch, each on a beat of its own through the town (laid along the roads once the map is placed)
for k_, donor_ in enumerate(("Contest_Guard", "IxGuard2")):
    wx_, wy_ = ring[k_ * 4]
    person("Con02a", donor_, wx_, wy_, f"Watch{k_ + 1}", action=0)
    sm.beat(f"Watch{k_ + 1}", vc, stops=7)
# the ogre warlord in the old watchtower, two grunts at the breach
pop.creature("OgreWarlord", *tower["boss"], action="guard", face=square_px(*land.areas["den"]["c"]), scr="TowerOgre", aggr=0.83)
for k_, (x_, y_) in enumerate(tower["inside"][:2]):
    pop.creature("GruntAxe", x_, y_, action="guard", face=square_px(*land.areas["den"]["c"]), scr=f"TowerGrunt{k_ + 1}", aggr=0.83)
# the wolf pack at its den
wolves = []
for k, (x, y) in enumerate(den_spots):
    n = f"Wolf{k + 1}"
    pop.creature("Wolf" if k else "BlackWolf", x, y, action="idle", scr=n)
    wolves.append(n)
B.pack(wolves[0], wolves[1:])
# the Varn crypt's restless dead, and the guardian over the grave goods
crypt = room_of("chapel", "crypt")
dead = []
if crypt:
    cx_, cy_ = free_px(crypt)
    pts_ = sorted(((x + 1) * CELL, (y + 1) * CELL) for x, y in crypt.tiles)
    dead = sm.keepers(crypt, ("Skeleton", "Skeleton", "Ghost", "Ghost", "Skeleton"), "VarnDead")
    pop.creature("SkeletonLord", cx_, cy_, action="guard", scr="VarnGuardian", aggr=0.83)
    # the grave goods: the emerald in the family's chest, at the back of the crypt
    gpx = free_px(crypt, prefer=max(pts_, key=lambda p: -p[1] + p[0] * 0.0), clear=26)
    m.obj_px("CryptChest3", *gpx, items=["Emerald", ("Gold", {"Amount": 120}), "SpellBook", "CurePoisonPotion"])
    sm.lock_room(crypt, "Silver")                 # the door from the nave: Father Odo's lock
# the woods' own creatures by the forest's edge, well away from the town and the story's places
sm.wild({"SmallAlbinoSpider": 3, "Bat": 3, "Urchin": 2, "Spider": 1, "Bear": 1}, away_from=vc, per100=0.55, gap=6, min_away=32,
        avoid=(camp_c, grove_c, den_c, south_c, fork_c, tower_c, gate_sq, land.areas["north"]["c"]))

# ---- 9. the story ----------------------------------------------------------------------------------------------------
fx, fy = square_px(*fork_c)
q.start([A.lock("NorthGate1"), A.lock("NorthGate2"), A.disable("NorthExit1"), A.disable("NorthExit2"),
         A.disable("NorthExit3"),
         q.journal("I have come up the King's Road to Thornwick, the last town before the north.", HINT)])

# the ambush: the lookouts come out of the trees when the player passes the bend
q.near(fx, fy, 150, [A.hunt(n) for n in ambushers] + [A.print("Shouts from the trees! Men with red-daubed hands "
                                                             "come running.")])
q.on_all_dead(ambushers, [A.flag("lookouts_dead"), A.print("The lookouts are dead. Their fire still burns in the grove.")])

# Tobin: the hook, then thanks for the lookouts
q.talker("Tobin", [
    q.say("You killed them! The ones in the grove! Bless you, stranger. It isn't much, but take these, and the coin "
          "I had sewn in my boot.", when=q.when(flag=q.dead(*ambushers), not_="tobin_paid"),
          do=[A.give("RedPotion", 3), A.gold(40), A.flag("tobin_paid"),
              q.journal("Tobin the carter paid me for killing the Red Hand's lookouts.", COMPLETED)], who="Tobin"),
    q.say("Thornwick is up the road. Tell Reeve Aldric what happened here. Somebody has to do something about the "
          "Red Hand.", when=q.when(flag="met_tobin"), who="Tobin"),
    q.say("Stranger! Thank the gods. The Red Hand took my whole load, crates, barrels, the lot, and left me for dead. "
          "Some of them are still about, in the trees past the bend. Watch yourself on the road. Thornwick is just "
          "north. The reeve there, Aldric, must hear of this.",
          do=[A.flag("met_tobin"), A.stage("main", 1),
              q.journal("Tobin the carter was robbed by the Red Hand bandits on the King's Road. He asked me to tell "
                        "Reeve Aldric of Thornwick. Some of the bandits are still in the trees past the bend.")],
          who="Tobin")])

# the reeve: the main quest
q.talker("Aldric", [
    q.say("Garrick is dead? Then the Red Hand is finished, and Thornwick owes you. Here is the bounty, as promised. "
          "I have sent word to the gate: the north road is yours.",
          when=q.when(flag=q.dead("Garrick"), not_="bounty_paid"),
          do=[A.gold(200), A.give("BluePotion", 2), A.give("ChainTunic"), A.flag("bounty_paid"), A.stage("main", 4),
              A.unlock("NorthGate1"), A.unlock("NorthGate2"), A.enable("NorthExit1"), A.enable("NorthExit2"),
              A.enable("NorthExit3"),
              q.journal("Garrick the Red is dead. Reeve Aldric paid the bounty and opened the north gate. The King's "
                        "Road north is open.", COMPLETED)], who="Aldric"),
    q.say("The gate is open and the road is yours. Thornwick will remember what you did.",
          when=q.when(flag="bounty_paid"), who="Aldric"),
    q.say("Their camp is in the old pines, north-west, past the graveyard. Garrick the Red leads them. Kill him and "
          "the rest will scatter.", when=q.at("main", 2), who="Aldric"),
    q.say("A traveller? From the south? Then you've seen what the Red Hand does to honest folk. I have barred the "
          "north gate: no one goes up that road while those butchers hold it. Their camp is in the old pines to the "
          "north-west, past the graveyard. Their leader is Garrick the Red. Bring me word that he's dead and I will "
          "pay you two hundred gold, and open the gate myself.",
          do=[A.stage("main", 2),
              q.journal("Reeve Aldric has barred the north gate until the Red Hand is broken. Their camp lies in the old "
                        "pines north-west of town, past the graveyard. He will pay 200 gold for Garrick the Red's "
                        "death and open the gate.")], who="Aldric")])
q.on_death("Garrick", [A.flag("garrick_dead"), A.print("Garrick the Red falls, and the Red Hand with him."),
                       q.journal("Garrick the Red is dead. I should tell Reeve Aldric.", QUEST)])

# the gate guards
for g_ in ("GateGuard", "GateGuard2"):
    q.talker(g_, [
        q.say("The reeve's word came down. Gate's open. Safe travels, friend.", when=q.when(flag="bounty_paid"), who="Guard"),
        q.say("Gate's barred by order of the reeve. Nobody goes north while the Red Hand holds the road. Talk to "
              "Aldric in his hall if you don't like it.", who="Guard")])

# Mirela and the Varn emerald
q.talker("Mirela", [
    q.say("You gave it to the priest? My grandmother's emerald, back in the ground? ...Get out of my sight.",
          when=q.at("gem", 4), who="Mirela"),
    q.say("It's beautiful. Just as she wore it. You've done me a kindness I can't repay. But I'll try.",
          when=q.at("gem", 3), who="Mirela"),
    q.say("You have it! The Varn emerald! Give it to me and the two hundred gold is yours. Will you?",
          when=q.when(has="Emerald", not_="gem_done"), ask=True,
          do=[A.flag("gem_done"), A.take("Emerald"), A.gold(200), A.stage("gem", 3),
              q.journal("I gave the Varn emerald to Mirela. She paid 200 gold.", COMPLETED)],
          else_=[A.chat("Mirela", "Then what good are you?")], who="Mirela"),
    q.say("You had it, didn't you? I can see it in your face. Where is my grandmother's emerald?",
          when=q.at("gem", 2), who="Mirela"),
    q.say("The key fits the crypt door behind the nave. Grandmother lies at the back. Please, be quick, before Odo "
          "notices it's gone.", when=q.at("gem", 1), who="Mirela"),
    q.say("You look like someone who can handle themselves. My grandmother was a Varn. She was buried with the family "
          "emerald, and now Father Odo has sealed the crypt and says the dead walk there. Walk! I have a copy of his "
          "key. Bring me the emerald and I will give you two hundred gold. Will you do it?",
          ask=True, do=[A.stage("gem", 1), A.give("SilverKey"),
                        q.journal("Mirela at the Lantern gave me a copy of Father Odo's key to the Varn crypt behind "
                                  "the chapel. She will pay 200 gold for her grandmother's emerald.")],
          else_=[A.chat("Mirela", "Then forget I asked.")], who="Mirela")])
q.on_pickup("Emerald", [A.stage("gem", 2), q.journal("I have the Varn emerald. Mirela is waiting at the Lantern, but "
                                                     "Father Odo might want it back where it belongs.")],
            when=q.at("gem", 1))
q.talker("FatherOdo", [
    q.say("The Varn dead are quiet now. You did a good thing, whatever Mirela tells you.", when=q.at("gem", 4), who="Odo"),
    q.say("You opened the crypt? And you carry the Varn emerald... Mirela put you up to this. It was buried with old "
          "Agna Varn, and the dead will not rest while it is gone. Give it to me and I will lay it back with her. Will "
          "you?", when=q.when(has="Emerald", not_="gem_done"), ask=True,
          do=[A.flag("gem_done"), A.take("Emerald"), A.give("CurePoisonPotion", 2), A.give("RedPotion", 2), A.gold(80), A.stage("gem", 4),
              q.journal("I gave the Varn emerald to Father Odo, who laid it back in the crypt. He blessed me with "
                        "potions and the chapel's alms.", COMPLETED)],
          else_=[A.chat("FatherOdo", "Then the dead will come for it.")], who="Odo"),
    q.say("The Varn crypt is sealed, child. Since the spring the dead there have not rested. Stay out of it.",
          who="Odo")])

# Hobb and the wolves
q.on_all_dead(wolves, [A.flag("wolves_dead"), A.print("The last of the wolf pack lies dead.")])
q.talker("Hobb", [
    q.say("The pack's gone? All of them? Ha! Here, for your trouble, and a loaf and a jug from the mill.",
          when=q.when(flag=q.dead(*wolves), not_="hobb_paid"),
          do=[A.gold(120), A.give("Meat"), A.give("Cider"), A.flag("hobb_paid"), A.stage("wolves", 2),
              q.journal("I killed the wolves of the east wood. Hobb the miller paid me 120 gold.", COMPLETED)],
          who="Hobb"),
    q.say("Goats are safe now. You're welcome at the mill any time.", when=q.when(flag="hobb_paid"), who="Hobb"),
    q.say("The wolves den in the rocks up the east path. A big black one leads them.", when=q.at("wolves", 1), who="Hobb"),
    q.say("You've a sword, have you? Wolves have been at my goats every night this month. They den in the rocks up the "
          "east path. Kill the pack and I'll pay you a hundred and twenty gold.",
          do=[A.stage("wolves", 1), q.journal("Hobb the miller will pay 120 gold to whoever kills the wolf pack "
                                              "denning in the rocks up the east path.")], who="Hobb")])
# old Brannoc and the family greatsword
q.talker("Brannoc", [
    q.say("My grandfather's sword, back in the forge where it was made. You've given an old man his family back. "
          "Take this breastplate. My son made it; he'd want it worn by someone who earned it.",
          when=q.when(has="GreatSword", not_="sword_done"), ask=True,
          do=[A.flag("sword_done"), A.take("GreatSword"), A.give("Breastplate"), A.gold(150), A.stage("sword", 3),
              q.journal("I returned the Brannoc greatsword. Old Brannoc gave me a breastplate and 150 gold.", COMPLETED)],
          else_=[A.chat("Brannoc", "Then keep it. Use it well.")], who="Brannoc"),
    q.say("Every time I hear the forge ring I think of that sword. Thank you, friend.", when=q.at("sword", 3), who="Brannoc"),
    q.say("You found it and then lost it? Go back and look, friend. That sword has been lost once already.",
          when=q.at("sword", 2), who="Brannoc"),
    q.say("The tower's up past the wolves' den, in the east wood. Mind the brute who lives there now.",
          when=q.at("sword", 1), who="Brannoc"),
    q.say("Forty years I worked that forge before my son took it. My grandfather's greatsword hung over it, until it "
          "went to the old watchtower with a Thornwick soldier who never came back. An ogre lairs in the ruin now; "
          "folk hear it bellow at night. If you bring that sword home, the Brannocs will make it worth your while.",
          do=[A.stage("sword", 1), q.journal("Old Brannoc's family greatsword was lost at the old watchtower in the "
                                             "east wood, past the wolves' den. An ogre lairs there now.")],
          who="Brannoc")])
q.on_pickup("GreatSword", [A.stage("sword", 2), q.journal("I found a fine old greatsword in the watchtower ruin. "
                                                          "Old Brannoc will want to see it.")])
q.on_death("TowerOgre", [A.print("The ogre warlord crashes down among the old stones.")])
# Pell the farmer: the road's news
q.talker("Pell", [
    q.say("Bridge held up, did it? Built it with my own hands, me and the Hobbs. Stream's what the town's named for: "
          "Thorn Wick, the ford by the thorns. Here, have an apple or three.",
          when=q.when(not_="pell_fed"), do=[A.give("RedApple", 3), A.flag("pell_fed")], who="Pell"),
    q.say("If you're walking the east wood, mind the old watchtower. Something big took it over last winter. "
          "And the wolves are bold this year; Hobb's lost goats.", who="Pell")])
# the town watch
for w_ in ("Watch1", "Watch2"):
    q.talker(w_, [
        q.say("Red Hand's broken, they say. Quiet watch tonight, then.", when=q.when(flag=q.dead("Garrick")), who="Watch"),
        q.say("Keep your blade sheathed in town. If you're after trouble, the Red Hand's out in the north-west pines, "
              "and the reeve pays for heads.", who="Watch")])

# the folk of the square: each knows one thing worth hearing
RUMOURS = [
    "The reeve's barred the north gate. Merchants are stuck here, eating the inn bare.",
    "Mirela at the Lantern has been asking after hired swords. Something about her grandmother.",
    "Father Odo locked the Varn crypt in the spring. My cousin swears she heard knocking from inside.",
    "Hobb's lost three goats to the wolves this month. He'd pay to be rid of them.",
    "Old Brannoc sits outside the forge all day, staring east. Ask him about his grandfather's sword.",
    "The Red Hand camp is out past the graveyard, in the old pines. Nobody who's gone looking has come back.",
    "Tobin the carter came through last week with a full wagon. I hope he made it.",
    "There's an ogre in the old watchtower. You can hear it on still nights, east of the mill.",
]
for k_, text_ in enumerate(RUMOURS):
    q.talker(sm.folk_names[k_], [q.say("The Red Hand's finished? Then the road's open again. Thank you!",
                                     when=q.when(flag="bounty_paid"), who="Folk"),
                               q.say(text_, who="Folk")])
for k_, pic_ in enumerate(("MaidenPic", "MaidenPic3", "MaidenPic2", "MalePic1", "MorganPic", "Townsman3Pic",
                           "MalePic7", "MaidenPic")):
    q.portrait(sm.folk_names[k_], pic_)

# the reeve's hint at the camp's way, and a hint from the folk of the square
q.near(*square_px(*land.areas["pines"]["c"]), 160, [A.print("Old pines close in. Somewhere ahead, smoke.")],
       when=q.when(flag="met_tobin"))
q.near(*red_camp["fire"], 300, [A.print("A camp: tents, a fire, crates of stolen goods. The Red Hand.")])

for who_, pic_ in (("Tobin", "MalePic5"), ("Aldric", "TheogrinPic"), ("Mirela", "MaidenPic2"),
                   ("FatherOdo", "GalavaPriestPic"), ("Hobb", "Townsman2Pic"), ("GateGuard", "Warrior2Pic"),
                   ("GateGuard2", "IxGuard2Pic"), ("Brannoc", "MalePic8"), ("Pell", "Townsman4Pic"),
                   ("Watch1", "Warrior3Pic"), ("Watch2", "IxGuard2Pic")):
    q.portrait(who_, pic_)

m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())

# the exteriors' dressing: composed groups of the place's things on the empty ground (kit/dressing.py)
from kit.dressing import Exterior
dressed = Exterior(m, land, "green", placed=placed).dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed, os.path.join(OUT, f"{NAME}.rooms.json"), yards=[y_ for y_ in yards if y_.kind in built])
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| trees {n_trees} | plants {n_small} | rock piles {len(piles)} | shopkeepers {n_shops} | caches {len(caches)} "
          f"| lines {len(q.strings)} | yards {', '.join(built) or 'none'}")
