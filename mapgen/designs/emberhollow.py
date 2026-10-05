"""Emberhollow (map Emberhol): a smelters' town in a volcanic caldera below the Rime Pass, and the story of the three
vents (chapter three after Thornwick, the north road, Rimehold and the Rime Pass; lava biome, rules/BIOMES.md). Built
with kit/story.py on the lava palette (kit/biome.py), dressed as Emberdeep dresses its lava.

The story
- The road down from the Rime Pass arrives from the north. Ash lies on it; the mountain grumbles. Tamsin, an ash-runner
  resting at the milestone, tells the player Emberhollow is below and that its warden has shut the Cinder Gate.
  Below the milestone fire imps nest in the rocks by the road and swarm whoever passes.
- Emberhollow: smelters' houses round a yard with a flame basin, the warden's hall, the smithy, the trading post, the
  Slag & Bellows inn, Maren's house and Sister Ilsa's cell.
- Main quest, the Three Vents (an any-order quest, counted with A.advance): the mountain breathes through three old
  vents, and the demons of the forge in the east have capped them so the pressure builds under the town. Warden Kael
  has shut the Cinder Gate on the south road (the way on runs under the mountain's flank) until the vents breathe
  again. Each vent has its keepers: the imp nest in the western ashfield, the ember demons on the crater's rim in the
  north-east, the forge-wardens before the demon forge in the east. With a vent's keepers dead, walking onto its grate
  throws off the capstone; with all three open the mountain sighs, the gate opens and the road south (the exit) leads
  on. Kael pays.
- Brin in the Obsidian Mine (a rescue): Maren's brother Brin went to cut obsidian in the south-east diggings and is
  trapped there by scorpions. Kill the scorpions and talk to him: he makes for home. Maren pays (less, and grieves, if
  Brin died).
- The Ember Eye (a choice): the ash-cult's ruined temple in the south-west, where the cult's dead high priest still
  stands, holds the Ember Eye, a ruby the cult worshipped. Sister Ilsa wants it to break it on her anvil-altar and
  will bless the player; Corvin, a gem dealer waiting at the inn, will buy it for a lot of gold. One gets it.
- The smithy, the trading post and the inn buy and sell; the forge's storeroom and the temple hold chests; three
  caches lie in the ash by the cliffs.
- The exit leads to AshRoad, the road out of the caldera, which closes chapter three.

    py mapgen/designs/emberhollow.py [seed]
"""
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import Land, square_tile, square_px
from kit.biome import Dresser
from kit.village import Village
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT, NOTE
from kit.story import StoryMap
from kit import camps

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 3
rng = random.Random(SEED)
NAME = "Emberhol"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "emberhollow")
NEXT_MAP = "AshRoad"                 # the road out of the caldera (mapgen/designs/ashroad.py)
PATH = "CaveHardBrown"               # the trodden ways: packed brown rock through the black crags


def uv(X, Y):
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="a smelters' town in a volcanic caldera under the Rime Pass: stone houses round a flame-basin yard, a crater "
          "lake of lava, an ashfield of fire imps, a demon forge in the east, an ash-cult's ruined temple and an "
          "obsidian digging, the south road barred by the Cinder Gate",
    environment="town", mood="hot, uneasy, rumbling",
    areas=[AreaIdentity("north", "where the road down from the Rime Pass arrives: the start"),
           AreaIdentity("town", "Emberhollow's yard and houses", landmark="the flame basin"),
           AreaIdentity("ashfield", "the western ashfield and its vent, where the imps nest"),
           AreaIdentity("crater", "the crater lake of lava and the vent on its rim", landmark="the crater lake"),
           AreaIdentity("forge", "the demon forge and the vent before its door"),
           AreaIdentity("ruin", "the ash-cult's ruined temple"),
           AreaIdentity("mine", "the obsidian diggings where Brin is trapped"),
           AreaIdentity("gate", "the Cinder Gate, shut"),
           AreaIdentity("south", "the road south under the mountain's flank: the way on")],
    buildings=[BuildingIdentity("foreman", "town", "the warden's hall", "Warden Kael"),
               BuildingIdentity("smithy", "town", "the smithy", "the smith"),
               BuildingIdentity("store", "town", "the trading post", "the trader"),
               BuildingIdentity("inn", "town", "The Slag & Bellows", "the innkeeper"),
               BuildingIdentity("home", "town", "Maren's house", "Maren"),
               BuildingIdentity("cottage", "town", "", "Sister Ilsa")])

m = Spec(NAME, summary="Emberhollow", description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"Generated by Claude.", author="vdystopia (generated by Claude)", version="1", date="2026", type=SOLO,
         minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
q = QuestBook(NAME)

# ---- 1. the plan ---------------------------------------------------------------------------------------------------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"north": ((128, 26), 18), "town": ((118, 108), 74), "ashfield": ((42, 92), 28), "crater": ((192, 46), 42),
         "forge": ((200, 128), 36), "ruin": ((50, 186), 30), "mine": ((196, 198), 26), "gate": ((122, 196), 14),
         "south": ((122, 226), 12)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "town", roughness=0.24)
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_ in (("north", "town", 14, True), ("town", "gate", 13, True), ("gate", "south", 12, True),
                          ("town", "ashfield", 12, False), ("town", "crater", 12, False), ("town", "forge", 13, False),
                          ("forge", "mine", 11, False), ("town", "ruin", 12, False), ("ashfield", "ruin", 10, False)):
    land.link(a_, b_, w_, bend=0.24, road=road_, road_material=PATH, pockets=(1, 2) if road_ else (0, 1))
d = Dresser(m, rng, land, "lava")
m.blending("RoughCobble", 7, edge="BlendEdge")
# the crater lake: lava behind black cliffs in the middle of the crater clearing; a small pool in the forge's yard
crater_c = land.areas["crater"]["c"]
lake = d.reserve_pool((crater_c[0] * 2 + 6, crater_c[1] * 2 + 6), 22, stretch=1.2, angle=0.4, roughness=0.25)
# the demon forge in the east, its door toward the town (placed before the land grows round it)
forge_b = d.structure("demon_forge", "forge", toward="town", scale=1.0, name="the demon forge")

# ---- 2. the centre: the yard and its flame basin -------------------------------------------------------------------
land.paint_square(m, "town", 9, "RoughCobble")
vc = land.areas["town"]["c"]
land.taken |= {(int(vc[0]) + a, int(vc[1]) + 1 + b) for a in (-1, 0, 1) for b in (-1, 0, 1)}
land.paint_roads(m, PATH, width_squares=2.6, skip=land.reserved)

# ---- 3. the houses from the yard outwards ----------------------------------------------------------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"north": 8, "gate": 8})
sm.connect_and_furnish(path_material=PATH)
furnished = d.furnish_structures()

# ---- 4. the land: crags breaking the ash, every way open --------------------------------------------------------------
land.carve(margin=4.0)
lanes = sm.keep_open({"north": 5, "ashfield": 7, "ruin": 7, "mine": 7, "forge": 4})
# the vents: one in the ashfield, one on the crater's rim toward the town, one before the forge's door
ash_c, ruin_c, mine_c, forge_c = (land.areas[k]["c"] for k in ("ashfield", "ruin", "mine", "forge"))
north_c, south_c = land.areas["north"]["c"], land.areas["south"]["c"]


def toward(a, b, dist):
    dx, dy = b[0] - a[0], b[1] - a[1]; l_ = math.hypot(dx, dy) or 1
    return (a[0] + dx * dist / l_, a[1] + dy * dist / l_)


lake_c = (crater_c[0] + 1.5, crater_c[1] + 1.5)
vent_sq = [(ash_c[0], ash_c[1]), toward(lake_c, vc, 15.0), None]
vent_sq[2] = toward(forge_c, vc, 13.0)
for vs in vent_sq:
    land.taken |= {(int(vs[0]) + a, int(vs[1]) + 1 + b) for a in range(-3, 4) for b in range(-3, 4)}
calm = lanes | {s for s in land.squares if math.hypot(s[0] - vc[0], s[1] - vc[1]) < 8}
crags = land.thickets(110, size=(1.2, 2.4), clear=1, avoid=frozenset(calm))
land.open_links()
land.apply(m, wall=d.wall, floor=d.base)
d.cap_islands(crags, "VolcanicCraggy")
d.ground()
d.paint_pools()

# the Cinder Gate: a wall across the south road beyond the gate clearing, shut
gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "south"), prefix="CinderGate", material="Cobblestone")
sm.exit_to("south", NEXT_MAP, prefix="SouthExit")

# ---- 5. the places of the story ------------------------------------------------------------------------------------
# the three vents: an iron grate over the vent, a ring of fallen brick and rock round it, a dark light that wakes red
vents = []
for k, vs in enumerate(vent_sq):
    sc = camps.Scene(m, rng, land, (vs[0] + 0.5, vs[1] - 0.5))
    sc.put("FireGrate", sc.ci, sc.cj)
    for n in range(7):
        sc.put(("Brick", "CaveRocksMedium", "CaveRocksLarge", "Rock4")[n % 4], *sc.at(1.9 + 0.2 * (n % 2), n * 2 * math.pi / 7))
    x_, y_ = square_px(sc.ci, sc.cj)
    m.obj_px("ColorLight", x_, y_ - 4, scr=f"VentLight{k + 1}", xfer=d._light_xfer((255, 90, 20), 240, 70))
    vents.append((x_, y_))
    d.taken |= {(int(vs[0]) + a, int(vs[1]) + 1 + b) for a in range(-3, 4) for b in range(-3, 4)}
# the yard: a flame basin at its middle, benches round it
vil = Village(m, rng, land)
m.obj_px("DunMirFlameBasinLit", *square_px(vc[0], vc[1] - 0.5))
for k in range(4):
    a = k * math.pi / 2 + math.pi / 4
    vil.spec.obj_px(("Bench1", "Bench4", "Bench5", "Bench2")[k], *square_px(vc[0] + 2.6 * math.cos(a), vc[1] - 0.5 + 2.6 * math.sin(a)))
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Slag & Bellows\nAle, stew and a cool cellar bed", "Sign"),
                     store=q.text("Emberhollow Trading Post\nObsidian bought, gear sold", "Sign"),
                     smithy=q.text("The Smithy", "Sign"))
for bid, b in placed:
    for sc_ in BUILDINGS[bid.role]["scenes"]: vil.scene(b, sc_, role=bid.role)
# the ash-cult's ruined temple in the south-west: the Ember Eye in the chest at the back
temple = camps.ruined_tower(m, rng, land, ruin_c, vc, loot=["Ruby", ("Gold", {"Amount": 140}), "BluePotion", "MorningStar"],
                            size=(9, 9), material="AncientRuin")
# the obsidian diggings: Brin's rock shelter, carts and spoil, his pick and lamp
mine_sc = camps.Scene(m, rng, land, (mine_c[0], mine_c[1]))
for t, r, a in (("CaveRocksHuge", 1.6, 0.4), ("CaveRocksLarge", 1.5, 1.6), ("CaveRocksHuge", 1.7, 2.8),
                ("CaveRocksLarge", 1.6, 4.4), ("MineOreCart1", 3.2, 5.4), ("BarrelWithTools1", 3.0, 0.9),
                ("Crate1", 3.4, 2.0), ("CaveRocksMedium", 3.1, 3.4)):
    mine_sc.put(t, *mine_sc.at(r, a))
d.clusters({"LavaHardened5": 1, "Rock8": 2, "CaveRocksMedium": 2},
           [s for s in land.squares if math.hypot(s[0] - mine_c[0], s[1] - mine_c[1]) < 10 and s not in land.taken],
           4, size=(2, 4), radius=1.3, gap=0.9, spacing=4.0)
camps.signpost(m, land, (mine_c[0] - 5, mine_c[1] - 2), q.text("OBSIDIAN DIGGINGS\nKeep out unless you're Brin.", "Sign"),
               kind="PlankSign2")
# the arrival: a milestone and a sign; the imps' rocks below it
camps.signpost(m, land, (north_c[0] + 2.5, north_c[1] + 1.5),
               q.text("EMBERHOLLOW\nThe road down from the Rime Pass. Mind the ash.", "Sign"))
gs_ = sm.road_near((gate_sq[0] - 3, gate_sq[1] + 3))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 0.5),
               q.text("THE CINDER GATE IS SHUT\nNo one goes south while the mountain is choked. - Kael, Warden", "Sign"))
# the imps' nest beside the road below the milestone: a heap of rock and bones
mid_road = sm.road_near(toward(north_c, vc, 14.0))
nest_c = None
for off in (3.5, -3.5, 4.5, -4.5):
    c_ = (mid_road[0] + off, mid_road[1] - off)
    if (int(c_[0]), int(c_[1]) + 1) in land.squares and (int(c_[0]), int(c_[1]) + 1) not in land.roads:
        nest_c = c_; break
nest_c = nest_c or (mid_road[0] + 3.5, mid_road[1] - 3.5)
nest = camps.wolf_den(m, rng, land, nest_c, mid_road)
# caches in the ash by the cliffs
caches = []
for near_, loot_ in ((ash_c, [("Gold", {"Amount": 70}), "RedPotion", "RedPotion"]),
                     (mine_c, [("Gold", {"Amount": 90}), "BluePotion", "CurePoisonPotion"]),
                     (crater_c, [("Gold", {"Amount": 60}), "SteelShield"])):
    s_ = sm.hidden_spot(near_, r=(6, 14))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_))

# ---- 6. rocks, bones and red light ----------------------------------------------------------------------------------
keep_clear = {(int(vc[0]) + a, int(vc[1]) + b) for a in range(-6, 7) for b in range(-6, 7)}
n_trees, n_small = d.vegetate(keep_clear=keep_clear, groves=2)
n_liq = d.dress_liquid()
d.scatter_open(scale=0.5)
d.rim(scale=0.6)
n_lights = d.lights(scale=0.5)
piles = d.planter.rock_piles(max(4, len(land.squares) // 1000))
start_xy = square_px(north_c[0] + 0.5, north_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)

# ---- 7. the people ---------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
vx, vy = square_px(*vc)
person = sm.person
st = sm.room_of("foreman", "study")
hx, hy = sm.free_px(st) if st else square_px(vc[0] + 3, vc[1])
person("Con03A", "Lance", hx, hy, "Kael")
mx_, my_ = sm.outside_door("home") or square_px(vc[0] - 3, vc[1])
person("Con02a", "Lydia", mx_ + 20, my_ + 10, "Maren", face=(vx, vy))
ix_, iy_ = sm.outside_door("cottage") or square_px(vc[0], vc[1] - 3)
person("Con02a", "Julie", ix_ + 15, iy_ + 15, "Ilsa", face=(vx, vy))
tav = sm.room_of("inn", "tavern")
cx_, cy_ = sm.free_px(tav) if tav else square_px(vc[0], vc[1] + 3)
person("Con03A", "Osborn", cx_, cy_, "Corvin")
tx_, ty_ = square_px(north_c[0] + 1.5, north_c[1] + 0.5)
person("Con02a", "Morgan", tx_, ty_, "Tamsin", face=square_px(*vc))
gx, gy = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
gdx, gdy = vx - gx, vy - gy; gl = math.hypot(gdx, gdy) or 1
person("Con02a", "Contest_Guard", gx + 70 * gdx / gl, gy + 70 * gdy / gl, "GateGuard", face=(vx, vy))
# Brin, in his rock shelter at the diggings
bx_, by_ = mine_sc.px(0.0, 0.0)
person("Con03A", "Millard", bx_, by_, "Brin")
home_wp = [sm.journey("Brin", "BrinHome", (mx_ - 20, my_ + 25))]
WARES = {"store": [(4, "RedPotion"), (3, "BluePotion"), (3, "CurePoisonPotion"), (2, "Meat"), (2, "Quiver"),
                   (1, "Bow"), (1, "LeatherArmoredBoots"), (1, "ChainCoif"), (1, "MedievalCloak")],
         "inn": [(5, "Meat"), (4, "Cider"), (3, "RedApple"), (2, "RedPotion")],
         "smithy": [(2, "Sword"), (1, "Longsword"), (1, "WarHammer"), (1, "SteelShield"), (1, "ChainTunic"),
                    (1, "ChainLeggings"), (1, "OrnateHelm"), (1, "GreatSword")]}
GREET = {"store": q.text("Obsidian, sulphur, potions and gear. Everything here's a little singed, but it works.", "Shop"),
         "inn": q.text("Welcome to the Slag & Bellows! The cellar's the coolest place in the caldera. Sit.", "Shop"),
         "smithy": q.text("Best steel this side of the pass. Forged on the mountain's own fire, while it lasts.", "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"smithy": "ShopkeeperWarriorsRealm"})
FOLK = [("Con02a", "Tanya"), ("Con02a", "Heckler"), ("Con03A", "Millard"), ("Con02a", "Clyde"),
        ("Con08a", "Gretchen"), ("Con02a", "Lydia")]
RUMOURS = ["Feel that? The ground shakes every night now. Three vents used to breathe for the mountain. Now nothing.",
           "Demons came out of the old forge in the east and dropped stones on the vents. Who does that? Demons do.",
           "Fire imps nest in the western ashfield, round the old vent there. Little biters. Bring a shield.",
           "Brin's been gone two days at the obsidian diggings, south-east past the forge. Maren's beside herself.",
           "The ash-cult's temple in the south-west is a ruin, but their high priest never left it. Dead or not.",
           "There's a gem dealer drinking at the Slag & Bellows. Corvin. Asks everyone about the cult's ruby."]
sm.townsfolk(FOLK, vc, q=q, rumours=RUMOURS, after=("vents_open", "The ground's quiet tonight. First time in weeks."),
             pics=("MaidenPic3", "MalePic1", "Townsman2Pic", "MalePic7", "MaidenPic", "MaidenPic2"), radius=4.5)

# ---- 8. the fights -----------------------------------------------------------------------------------------------
# the imps of the roadside nest, who swarm whoever passes on the road below the milestone
nest_imps = []
for k, (x, y) in enumerate(nest[:4]):
    n = f"NestImp{k + 1}"
    pop.creature("Imp", x, y, action="idle", scr=n, aggr=0.5, sight=80)
    nest_imps.append(n)
# the keepers of the three vents
ash_keep = []
for k, a in enumerate((0.3, 1.5, 2.7, 3.9, 5.1)):
    x, y = square_px(vent_sq[0][0] + 0.5 + 3.4 * math.cos(a), vent_sq[0][1] - 0.5 + 3.4 * math.sin(a))
    n = f"AshImp{k + 1}"
    pop.creature("Imp" if k < 4 else "EmberDemon", x, y, action="guard", scr=n, aggr=0.83, face=vents[0])
    ash_keep.append(n)
B.sentry("AshImp5", vents[0], rouse=ash_keep[:4], shout="Skree!")
rim_keep = []
for k, a in enumerate((0.0, 2.1, 4.2)):
    x, y = square_px(vent_sq[1][0] + 0.5 + 3.2 * math.cos(a), vent_sq[1][1] - 0.5 + 3.2 * math.sin(a))
    n = f"RimDemon{k + 1}"
    pop.creature("EmberDemon" if k < 2 else "MeleeDemon", x, y, action="guard", scr=n, aggr=0.83, face=vents[1])
    rim_keep.append(n)
forge_keep = []
for k, a in enumerate((0.8, 3.9)):
    x, y = square_px(vent_sq[2][0] + 0.5 + 3.0 * math.cos(a), vent_sq[2][1] - 0.5 + 3.0 * math.sin(a))
    n = f"ForgeWard{k + 1}"
    pop.creature("MeleeDemon", x, y, action="guard", scr=n, aggr=0.83, face=(vx, vy), HealthMultiplier=1.5)
    forge_keep.append(n)
# the demon forge's own keepers inside, and a chest in its hall of arms
d.population = pop
n_garrison = d.garrison()
arms_r = next((r for role, area, b, nm in d.structures for r in b.rooms if r.kind == "hall"), None)
if arms_r:
    m.obj_px("DunMirChest1", *sm.free_px(arms_r, clear=26), items=[("Gold", {"Amount": 180}), "ChainTunic", "RedPotion",
                                                             "RedPotion"])
# the ash-cult's dead: the high priest by the Ember Eye, his acolytes at the breach
pop.creature("SkeletonLord", *temple["boss"], action="guard", face=square_px(*vc), scr="HighPriest", aggr=0.83,
             HealthMultiplier=2.0)
cult = []
for k, (x, y) in enumerate(temple["inside"]):
    n = f"Acolyte{k + 1}"
    pop.creature("Skeleton", x, y, action="guard", face=square_px(*vc), scr=n, aggr=0.83)
    cult.append(n)
# the scorpions round Brin's shelter
crawlers = []
for k, a in enumerate((0.9, 2.2, 3.7, 5.0)):
    x, y = mine_sc.px(4.6, a)
    n = f"MineScorpion{k + 1}"
    pop.creature("Scorpion", x, y, action="guard", scr=n, aggr=0.83, face=(bx_, by_))
    crawlers.append(n)
# the caldera's own creatures by the cliffs, well away from the town and the story's places (never a Zombie)
sm.wild({"Imp": 3, "EmberDemon": 1, "Skeleton": 2, "Scorpion": 2}, away_from=vc,
        avoid=(ash_c, lake_c, forge_c, ruin_c, mine_c, north_c, nest_c, gate_sq, south_c) + tuple(vent_sq),
        per100=0.35, min_away=25)

# ---- 9. the story ----------------------------------------------------------------------------------------------------
q.start([A.lock("CinderGate1"), A.lock("CinderGate2"), A.disable("SouthExit1"), A.disable("SouthExit2"),
         A.disable("SouthExit3"), A.disable("VentLight1"), A.disable("VentLight2"), A.disable("VentLight3"),
         q.journal("The road down from the Rime Pass has brought me into a caldera of black rock and lava. A town "
                   "lies below: Emberhollow.", HINT)])
nx_, ny_ = square_px(*nest_c)
q.near(nx_, ny_, 190, [A.hunt(n) for n in nest_imps] + [A.print("Shrieks from the rocks! Fire imps pour out of a "
                                                                    "crack beside the road.")])
VENT_NAMES = ("the ashfield vent", "the crater vent", "the forge vent")
for k, (keep_, (x_, y_)) in enumerate(zip((ash_keep, rim_keep, forge_keep), vents)):
    q.near(x_, y_, 260, [A.hunt(n) for n in keep_], when=q.when(not_=f"vent{k + 1}"))
    q.near(x_, y_, 60, [A.flag(f"vent{k + 1}"), A.advance("vents", 1), A.enable(f"VentLight{k + 1}"),
                        A.spawn("LargeFlameImmobile", f"VentLight{k + 1}"),
                        A.print(f"You heave the capstone off {VENT_NAMES[k]}. Fire roars up out of the rock and the "
                                f"ground shudders."),
                        q.journal(f"I opened {VENT_NAMES[k]}.", NOTE)],
           when=q.when(flag=q.dead(*keep_)))
# with the third vent open the mountain breathes: the gate opens (checked every half second wherever the player is)
sx_, sy_ = start_xy
q.near(sx_, sy_, 100000, [A.flag("vents_open"), A.unlock("CinderGate1"), A.unlock("CinderGate2"),
                          A.enable("SouthExit1"), A.enable("SouthExit2"), A.enable("SouthExit3"),
                          A.print("A long sigh runs through the mountain. Far to the south, chains rattle: the Cinder "
                                  "Gate is opening."),
                          q.journal("All three vents breathe again and the mountain has quieted. The Cinder Gate is "
                                    "open; Warden Kael will want to see me.", COMPLETED)],
       when=q.at("vents", 3))
q.talker("Kael", [
    q.say("Hear that? Nothing. No rumbling for the first time in a month. The gate's open, and this is yours with the "
          "town's thanks.", when=q.when(flag="vents_open", not_="kael_paid"),
          do=[A.gold(300), A.give("BluePotion", 2), A.give("RedPotion", 2), A.flag("kael_paid")], who="Kael"),
    q.say("The south road's open. It runs under the mountain's flank; walk it quickly.", when=q.when(flag="kael_paid"),
          who="Kael"),
    q.say("Two of three. One more vent and the mountain can breathe.", when=q.at("vents", 2), who="Kael"),
    q.say("One vent open; I felt it from here. Two to go.", when=q.at("vents", 1), who="Kael"),
    q.say("The vents: the ashfield to the west where the imps nest, the crater's rim to the north-east, and the old "
          "forge in the east. Kill what guards each and throw the capstone off.", when=q.when(flag="kael_told"),
          who="Kael"),
    q.say("You came over the pass? Then you came at a bad time. The mountain breathes through three vents, and the "
          "demons of the old forge have capped every one. The pressure's building under us. The south road runs under "
          "the mountain's flank, and I'll not let anyone walk it until the vents are open. Open them and I'll open the "
          "Cinder Gate myself.",
          do=[A.flag("kael_told"),
              q.journal("Warden Kael has shut the Cinder Gate. Three vents are capped: in the western ashfield, on the "
                        "crater's rim north-east of town, and before the demon forge in the east. Kill each vent's "
                        "keepers and open it.", QUEST)], who="Kael")])
q.talker("Tamsin", [
    q.say("You did it, didn't you? The ground's stopped shaking. I'll carry that news over the pass.",
          when=q.when(flag="vents_open"), who="Tamsin"),
    q.say("Over the pass, are you? Emberhollow's below, down the road. Warden Kael shut the Cinder Gate south of town; "
          "nobody's going on. And watch the rocks beside the road. Imps.", who="Tamsin")])
q.talker("GateGuard", [
    q.say("Gate's open. Quick on the south road, the mountain's moody.", when=q.when(flag="vents_open"), who="Guard"),
    q.say("Cinder Gate is shut by the warden's order. His hall's on the yard.", who="Guard")])
# Brin in the obsidian diggings
q.talker("Brin", [
    q.say("Home! I'm going home. Tell Maren I'm coming.", when=q.when(flag="brin_free"), who="Brin"),
    q.say("They're dead? All of them? Fire bless you! I've been hiding in these rocks two days. I'm going home, now, "
          "before anything else crawls out.", when=q.when(flag=q.dead(*crawlers), not_="brin_free"),
          do=[A.flag("brin_free"), A.walk("Brin", home_wp[0]),
              q.journal("I found Brin alive in the obsidian diggings and killed the scorpions. He is going home to "
                        "Maren.", QUEST)], who="Brin"),
    q.say("Scorpions! Big ones, all round. Kill them or get out of here, I can't run past them.", who="Brin")])
q.talker("Maren", [
    q.say("Brin's home! Dusty and starving, but home. Take this, all of it; you've earned it twice.",
          when=q.when(flag="brin_free", not_="maren_paid"),
          do=[A.flag("maren_paid"), A.gold(150), A.give("LeatherArmoredBoots"), A.give("RedPotion", 2),
              q.journal("Brin is home. Maren paid me.", COMPLETED)], who="Maren"),
    q.say("He's dead? ...I knew. I think I knew. Take this, for trying.", when=q.when(flag=q.dead("Brin"), not_="maren_paid"),
          do=[A.flag("maren_paid"), A.gold(60), q.journal("Brin died at the diggings. I told Maren.", COMPLETED)],
          who="Maren"),
    q.say("Thank you. Truly.", when=q.when(flag="maren_paid"), who="Maren"),
    q.say("My brother Brin went to cut obsidian at the diggings, south-east past the forge. Two days. Someone saw "
          "scorpions out that way. Please, find him.",
          do=[A.stage("brin", 1), q.journal("Maren's brother Brin went to the obsidian diggings south-east of the "
                                            "forge two days ago and has not come back.", QUEST)], who="Maren")])
# the Ember Eye: two who want it
q.on_pickup("Ruby", [q.journal("I have the Ember Eye from the cult's temple. Sister Ilsa wants it broken; Corvin at "
                               "the inn wants to buy it.", QUEST)], when=q.when(not_="eye_done"))
q.talker("Ilsa", [
    q.say("The Ember Eye. Will you give it to me to break? The cult drew the mountain's anger through it; with it gone, "
          "the fire will settle. I can't pay much, but I can bless you.",
          when=q.when(has="Ruby", not_="eye_done"), ask=True,
          do=[A.flag("eye_done"), A.take("Ruby"), A.give("BluePotion", 3), A.give("CurePoisonPotion", 2),
              A.give("MedievalCloak"), A.gold(50),
              q.journal("I gave the Ember Eye to Sister Ilsa, who broke it and blessed me.", COMPLETED)],
          else_=[A.chat("Ilsa", "Think on it. That stone has killed enough.")], who="Ilsa"),
    q.say("Go with the cool of the deep rock.", when=q.when(flag="eye_done"), who="Ilsa"),
    q.say("The ash-cult worshipped a ruby they called the Ember Eye. Their dead priest still guards it in the ruined "
          "temple south-west of town. If you bring it to me, I will break it.",
          do=[A.stage("eye", 1)], who="Ilsa")])
q.talker("Corvin", [
    q.say("Is that it? The Ember Eye? Four hundred gold, right now, in your hand. What do you say?",
          when=q.when(has="Ruby", not_="eye_done"), ask=True,
          do=[A.flag("eye_done"), A.take("Ruby"), A.gold(250),
              q.journal("I sold the Ember Eye to Corvin for 250 gold.", COMPLETED)],
          else_=[A.chat("Corvin", "Your loss. The offer stands.")], who="Corvin"),
    q.say("A pleasure doing business.", when=q.when(flag="eye_done"), who="Corvin"),
    q.say("Corvin, dealer in rare stones. The ash-cult's temple, south-west, holds a ruby they called the Ember Eye. "
          "Bring it to me and I'll make you rich. Don't listen to the priestess.",
          do=[A.stage("eye", 1), q.journal("Corvin, a gem dealer at the Slag & Bellows, will pay well for the Ember "
                                           "Eye, a ruby in the ash-cult's ruined temple south-west of town. Sister "
                                           "Ilsa wants it too.", QUEST)], who="Corvin")])
q.on_death("HighPriest", [A.print("The high priest crumbles into ash and bone. Behind him, a chest.")])
q.near(*temple["boss"], 300, [A.print("Broken walls, black with old fire. Something in robes stands at the back.")])
for who_, pic_ in (("Kael", "Warrior3Pic"), ("Maren", "MaidenPic"), ("Ilsa", "MaidenPic2"), ("Corvin", "MalePic9"),
                   ("Tamsin", "MorganPic"), ("Brin", "Townsman3Pic"), ("GateGuard", "Warrior2Pic")):
    q.portrait(who_, pic_)

m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())

# the exteriors' dressing: composed groups of the place's things on the empty ground (kit/dressing.py)
from kit.dressing import Exterior
dressed = Exterior(m, land, "lava", placed=placed).dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    keep_ids = [(BuildingIdentity(role, area, nm, "the demons"), b) for role, area, b, nm in d.structures]
    rooms_sidecar(placed + keep_ids, os.path.join(OUT, f"{NAME}.rooms.json"))
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| forge {'yes' if forge_b else 'NO'} garrison {n_garrison} | rocks {n_trees} | on lava {n_liq} | shops {n_shops} "
          f"| caches {len(caches)} | lines {len(q.strings)}")
