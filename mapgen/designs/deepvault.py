"""Deepvault (map Deepvault): a miners' settlement in the great caverns under the mountain, and the story of the
Lamp-Eater (chapter four after Thornwick, the north road, Rimehold, the Rime Pass, Emberhollow and the Ash Road; cave
biome, rules/BIOMES.md). Built with kit/story.py on the cave palette (kit/biome.py), with a mine head on the yard
(kit/mine.py).

The story
- The Ash Road runs into the mountain and arrives in the north-east, at the old lamp station. The lamps along the road
  down are dark: Pell, the lamplighter, sits by his cold lamps and says the spiders came up out of the deep galleries
  and put them out. Webbed rocks by the road below him hold a nest of spiders that falls on whoever passes.
- Deepvault: miners' houses round an ore-dust yard under the rock face of the mine head (a timbered tunnel, a cave-in
  beyond), the overseer's hall, the company store, the smithy, the Lamp & Pick inn, the bunkhouse, Ketil's house and
  Orla's infirmary.
- Main quest, the Lamp-Eater (a summoning: the beast must be drawn out): the miners broke into an old dwarf vault in
  the deep galleries east of town, and a brood of spiders came out; their mother, the Lamp-Eater, eats the light and
  the men who carry it. Overseer Dagna has barred the gallery gate to hold them in and shut the Underway Gate on the
  south road (the way on runs through the deeps) until the thing is dead. She opens the gallery gate for the player.
  The Lamp-Eater hides in the vault's dark: kill her brood round the vault, then light the vault's great lamp; the
  light draws her down from the roof. With her dead, Dagna pays and opens the Underway Gate; the south road (the exit)
  leads on.
- The Antidote (a delivery): Gunnar's crew went to the far camp by the underground lake and were bitten by the giant
  leeches of its shore; they cannot walk out. Orla, the healer, gives the player her antidote (a potion of poison
  protection) to carry to them. Kill the leeches and hand Gunnar the antidote: he and Pip walk home; Gunnar gives the
  player his battle axe, and Orla pays when they are back. Lose the antidote and Orla has one more.
- The Wage Diamond (clear an accused man): the company's payroll, cut as one diamond, was stolen from the strongroom.
  Wendel the paymaster blames Ketil, who stood the night watch. Ketil swears he saw urchins carry something west into
  the old workings. The urchins' warren lies there, their shaman at its heart; the diamond is in his chest. Bring it
  to Wendel: he pays, and Ketil, his name cleared, gives the player his own reward.
- The company store, the smithy and the inn buy and sell. The vault's hoard, the urchins' chest and three caches
  (in the crystal grotto, by the lake and the warren) hold loot.
- The exit leads to Mirefen, chapter five, in the Black Fen beyond the caverns.

    py mapgen/designs/deepvault.py [seed]
"""
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import Land, square_tile, square_px
from kit.biome import Dresser
from kit.village import Village
from kit.mine import MineEntrance
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT, NOTE
from kit.story import StoryMap
from kit import camps

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 3
rng = random.Random(SEED)
NAME = "Deepvault"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "deepvault")
NEXT_MAP = "Mirefen"                 # chapter five (mapgen/designs/mirefen.py)
PATH = "ManaMineDirt"                # the trodden ways: ore dust tramped into the cave floor


def uv(X, Y):
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="a miners' settlement in the great caverns under the mountain: stone houses round an ore-dust yard under "
          "the mine head's rock face, deep galleries to the east where a spider brood broke out of an old dwarf "
          "vault, an underground lake with a far camp, the urchins' warren in the old workings to the west, a "
          "crystal grotto, the south road barred by the Underway Gate",
    environment="town", mood="dark, close, lamplit",
    areas=[AreaIdentity("north", "the old lamp station where the Ash Road arrives: the start"),
           AreaIdentity("town", "Deepvault's yard and houses under the mine head", landmark="the mine head"),
           AreaIdentity("gallery", "the gallery gate, barred against the spiders"),
           AreaIdentity("nest", "the deep galleries and the broken dwarf vault where the brood nests"),
           AreaIdentity("shore", "the leech-haunted shore the way to the far camp follows"),
           AreaIdentity("lake", "the underground lake", landmark="the black lake"),
           AreaIdentity("farcamp", "the far camp where Gunnar's crew lies poisoned"),
           AreaIdentity("warren", "the urchins' warren in the old workings"),
           AreaIdentity("grotto", "a crystal grotto glowing blue"),
           AreaIdentity("gate", "the Underway Gate, shut"),
           AreaIdentity("south", "the road south through the deeps: the way on")],
    buildings=[BuildingIdentity("foreman", "town", "the overseer's hall", "Overseer Dagna"),
               BuildingIdentity("store", "town", "the company store", "the storekeeper"),
               BuildingIdentity("smithy", "town", "the smithy", "the smith"),
               BuildingIdentity("inn", "town", "The Lamp & Pick", "the innkeeper"),
               BuildingIdentity("bunkhouse", "town", "the bunkhouse", "the miners", style="stone_house"),
               BuildingIdentity("home", "town", "Ketil's house", "Ketil", style="stone_house"),
               BuildingIdentity("cottage", "town", "Orla's infirmary", "Orla", style="stone_house")])

m = Spec(NAME, summary="Deepvault", description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"Generated by Claude.", author="vdystopia (generated by Claude)", version="1", date="2026", type=SOLO,
         minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
q = QuestBook(NAME)

# ---- 1. the plan ---------------------------------------------------------------------------------------------------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"north": ((196, 30), 18), "town": ((122, 106), 72), "gallery": ((184, 112), 14), "nest": ((216, 128), 34),
         "shore": ((180, 178), 28), "lake": ((148, 202), 38), "farcamp": ((222, 220), 16), "warren": ((40, 134), 30), "grotto": ((52, 48), 26),
         "gate": ((98, 192), 14), "south": ((86, 226), 12)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "town", roughness=0.24)
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_ in (("north", "town", 14, True), ("town", "gallery", 13, True), ("gallery", "nest", 12, True),
                          ("town", "gate", 13, True), ("gate", "south", 12, True),
                          ("town", "shore", 12, False), ("shore", "farcamp", 11, False), ("shore", "lake", 12, False), ("town", "warren", 12, False),
                          ("warren", "grotto", 10, False), ("grotto", "north", 10, False)):
    land.link(a_, b_, w_, bend=0.24, road=road_, road_material=PATH, pockets=(1, 2) if road_ else (0, 1))
d = Dresser(m, rng, land, "cave")
m.blending("RoughCobble", 7, edge="BlendEdge")
# the underground lake: black water behind low cliffs in its own cavern off the shore, a dead end: a pool where a
# through way's links meet walls the way off in some seeds (the far camp cut off)
lake_c0 = land.areas["lake"]["c"]
lake = d.reserve_pool((lake_c0[0] * 2, lake_c0[1] * 2), 15, stretch=1.2, angle=0.5, roughness=0.25)

# ---- 2. the centre: the yard, and the mine head's rock face on its north-west side ----------------------------------
land.paint_square(m, "town", 10, "RoughCobble")
vc = land.areas["town"]["c"]
mine = MineEntrance(land, set(land.plaza), (-1, 0), rng, depth=9, width=3, gap=4, reach=4, rock=12)
mine.plan()
land.paint_roads(m, PATH, width_squares=2.6, skip=land.reserved)

# ---- 3. the houses from the yard outwards ----------------------------------------------------------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"north": 8, "gate": 8, "gallery": 7})
sm.connect_and_furnish(path_material=PATH)

# ---- 4. the land: pillars break the caverns, every way open ------------------------------------------------------------
land.carve(margin=4.0)
mine.cut()
lanes = sm.keep_open({"north": 5, "nest": 9, "warren": 8, "farcamp": 6, "grotto": 5})
nest_c, war_c, far_c, gro_c = (land.areas[k]["c"] for k in ("nest", "warren", "farcamp", "grotto"))
north_c, south_c, lake_c = land.areas["north"]["c"], land.areas["south"]["c"], land.areas["lake"]["c"]


def toward(a, b, dist):
    dx, dy = b[0] - a[0], b[1] - a[1]; l_ = math.hypot(dx, dy) or 1
    return (a[0] + dx * dist / l_, a[1] + dy * dist / l_)


calm = lanes | {s for s in land.squares if math.hypot(s[0] - vc[0], s[1] - vc[1]) < 9}
crags = land.thickets(90, size=(1.2, 2.4), clear=1, avoid=frozenset(calm))
land.open_links()
land.apply(m, wall=d.wall, floor=d.base)
d.cap_islands(crags)
d.ground()
d.paint_pools()
mine.ground(m, track=PATH)
# the houses' wooden floors meet the cave floor where their walls turn a corner: let the cave floor's edge lie
# over the wood there (Westwood blends CaveHardBrown and WoodGray2)
m.blending("WoodGray2", -1)

# the Underway Gate: a wall across the south road, shut; the gallery gate across the road into the deeps, barred
gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "south"), prefix="UnderGate", material="DungeonStone")
gal_halves, gal_pts, gal_sq = sm.gate_across(("gallery", "nest"), prefix="GalleryGate", material="DungeonStone",
                                             ts=(0.3, 0.4, 0.2, 0.5))
sm.exit_to("south", NEXT_MAP, prefix="SouthExit")

# ---- 5. the places of the story ------------------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Lamp & Pick\nAle, stew and a bunk out of the drip", "Sign"),
                     store=q.text("Deepvault Company Store\nOre bought, gear sold", "Sign"),
                     smithy=q.text("The Smithy", "Sign"))
for bid, b in placed:
    for sc_ in BUILDINGS[bid.role]["scenes"]: vil.scene(b, sc_, role=bid.role)
# the broken dwarf vault in the deep galleries: walls of dungeon stone fallen in, the great lamp in its middle, the
# vault's hoard at the back
vault = camps.ruined_tower(m, rng, land, nest_c, gal_sq, loot=[("Gold", {"Amount": 130}), "OrnateHelm", "BluePotion",
                                                              "RedPotion"], size=(9, 9), material="DungeonStone")
# (the road into the deeps ends in the vault, so the basin goes down directly: a Scene keeps pieces off roads)
lamp_xy = square_px(nest_c[0], nest_c[1])
m.obj_px("DunMirFlameBasinUnlit", *lamp_xy)
m.obj_px("ColorLight", lamp_xy[0], lamp_xy[1] - 4, scr="VaultLamp", xfer=d._light_xfer((255, 200, 120), 260, 80))
# webs and bones about the galleries
nest_sq = [s for s in land.squares if math.hypot(s[0] - nest_c[0], s[1] - nest_c[1]) < 16 and s not in land.taken]
d._place({"SpiderWebNorthEast": 3, "SpiderWebEast": 3, "SpiderWebNorth": 3}, nest_sq, 8, min_gap=1.3, wall_clear=0)
d.clusters({"LegBone": 3, "ArmBone": 2, "Skull": 2}, nest_sq, 5, size=(3, 6), radius=1.4, gap=0.6, spacing=5.0)
# the far camp: a cold fire, bedrolls, crates and a cart where Gunnar's crew lies
far_sc = camps.Scene(m, rng, land, (far_c[0], far_c[1]))
shore_c = land.areas["shore"]["c"]
a_lake = math.atan2(shore_c[1] - far_c[1], shore_c[0] - far_c[0])         # toward the way in from the shore
far_sc.put("CampFire", far_sc.ci, far_sc.cj)
for k, (t, r, da) in enumerate((("Cot1", 2.2, 2.4), ("Cot3", 2.3, 3.4), ("Crate1", 3.0, 4.4), ("DarkCrate2", 3.4, 4.9),
                                 ("MineOreCart1", 3.6, 1.6), ("BarrelWithTools1", 3.0, 3.9), ("MiningPickAxeOnGround1", 2.6, 5.4))):
    far_sc.put(t, *far_sc.at(r, a_lake + da))
camps.signpost(m, land, far_sc.at(3.0, a_lake - 1.2), q.text("FAR CAMP\nGunnar's crew. Mind the shore.", "Sign"), kind="PlankSign2")
# the urchins' warren: their beds, hammocks and shelves round a fire, the shaman's chest at the back
war_sc = camps.Scene(m, rng, land, (war_c[0], war_c[1]))
a_in = math.atan2(vc[1] - war_c[1], vc[0] - war_c[0])
war_sc.put("CampFire", war_sc.ci, war_sc.cj)
for k, (t, r, da) in enumerate((("UrchinBed1", 3.0, 1.9), ("UrchinBed3", 3.1, 2.6), ("UrchinBedFlat1", 3.2, 3.6),
                                 ("UrchinHammock2", 4.2, 4.3), ("UrchinShelvesFull1", 4.6, 3.1), ("UrchinShelvesEmpty1", 4.5, 2.2),
                                 ("UrchinTableLarge", 1.9, 1.0), ("UrchinStool1", 2.0, 0.4), ("UrchinStool2", 2.1, 1.6),
                                 ("UrchinTableSmall", 2.4, 5.0), ("UrchinStool1", 2.6, 5.6), ("UrchinBedFlat2", 3.3, 4.9))):
    war_sc.put(t, *war_sc.at(r, a_in + da))
war_chest = None
for r in (4.0, 3.6, 4.6, 3.2):
    war_chest = war_sc.put("ChestUrchin2", *war_sc.at(r, a_in + math.pi),
                           items=["Diamond", ("Gold", {"Amount": 60}), "RedPotion", "CurePoisonPotion"])
    if war_chest: break
assert war_chest, "no room for the urchins' chest"
war_chest_xy = (war_chest["x"], war_chest["y"])
# the crystal grotto: blue crystal formations, a cyan glow over some
grotto = [s for s in land.squares if math.hypot(s[0] - gro_c[0], s[1] - gro_c[1]) < 11 and s not in land.taken]
for ci, cj in d.clusters({"MineCrystal01": 3, "MineCrystal02": 3, "MineCrystal03": 2, "MineCrystal04": 2,
                          "MineCrystal05": 3}, grotto, 5, size=(5, 8), radius=1.7, gap=0.8, spacing=6.0, core="MineCrystalUp02"):
    m.obj_px("ColorLight", *square_px(ci, cj), xfer=d._light_xfer((64, 160, 224), 200, 50))
# the lake shore: glowing mushrooms in patches
shore = [s for s in land.squares if s not in land.taken and
         any((s[0] + a, s[1] + b) in lake for a in range(-3, 4) for b in range(-3, 4))]
d.clusters({"Mushroom3": 6, "Mushroom5": 3, "Mushroom1": 2, "Mushroom4": 2}, shore, 8, size=(4, 8), radius=1.6,
           gap=0.7, spacing=5.0)
# the arrival: the lamp station's milestone and sign; the spiders' webbed rocks below it
camps.signpost(m, land, (north_c[0] + 2.5, north_c[1] + 1.5),
               q.text("DEEPVAULT\nThe Ash Road ends here, under the mountain. Keep to the lamps.", "Sign"))
mid_road = sm.road_near(toward(north_c, vc, 15.0))
web_c = None
for off in (3.5, -3.5, 4.5, -4.5):
    c_ = (mid_road[0] + off, mid_road[1] - off)
    if (int(c_[0]), int(c_[1]) + 1) in land.squares and (int(c_[0]), int(c_[1]) + 1) not in land.roads:
        web_c = c_; break
web_c = web_c or (mid_road[0] + 3.5, mid_road[1] - 3.5)
web_spots = camps.wolf_den(m, rng, land, web_c, mid_road)
web_sc = camps.Scene(m, rng, land, web_c)
for k in range(3):
    web_sc.put(("SpiderWebNorthEast", "SpiderWebEast", "SpiderWebNorth")[k], *web_sc.at(2.2, k * 2.1))
gs_ = sm.road_near((gate_sq[0] - 3, gate_sq[1] + 3))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 0.5),
               q.text("THE UNDERWAY GATE IS SHUT\nNo one goes into the deeps while the Lamp-Eater lives. - Dagna, "
                      "Overseer", "Sign"))
gl_ = sm.road_near((gal_sq[0] - 3, gal_sq[1] - 3))
camps.signpost(m, land, (gl_[0] + 1.5, gl_[1] + 1.5),
               q.text("GALLERY GATE\nBarred. Spiders beyond. By order of the overseer.", "Sign"))
# caches in the dark by the cavern walls
caches = []
for near_, loot_ in ((gro_c, [("Gold", {"Amount": 60}), "RedPotion", "BluePotion"]),
                     (lake_c, [("Gold", {"Amount": 45}), "CurePoisonPotion", "RedPotion"]),
                     (war_c, [("Gold", {"Amount": 50}), "LeatherHelm"])):
    s_ = sm.hidden_spot(near_, r=(8, 16))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_))


# ---- 6. pillars, mushrooms, the mine head's timber and the lamps --------------------------------------------------------
def light(si, sj, rgb):
    x, y = square_px(si, sj)
    m.obj_px("ColorLight", x, y - 5, xfer=d._light_xfer(rgb, 180, 50))


def torch_pole(si, sj):
    s = (int(si), int(sj) + 1)
    if s not in land.squares or s in land.water or s in land.taken_strict: return False
    x, y = square_px(si, sj)
    cx, cy = int(x // 23), int(y // 23)
    if any((cx + a, cy + b) in m.wallmap or (cx + a, cy + b) in m.door_gaps for a in (-1, 0, 1) for b in (-1, 0, 1)):
        return False
    m.obj_px("TorchPole", x, y)
    m.obj_px("ColorLight", x, y - 5, xfer=d._light_xfer((224, 140, 64), 170, 55))
    return True


mine.dress(m, light=light, torch=torch_pole, glow=(64, 160, 224))
# lamps on the yard's corners and along the road toward the gates
for k in range(4):
    a = k * math.pi / 2 + math.pi / 4
    torch_pole(vc[0] + 8.5 * math.cos(a), vc[1] - 0.5 + 8.5 * math.sin(a))
m.obj_px("DunMirFlameBasinLit", *square_px(vc[0] + 1.5, vc[1] - 0.5))
keep_clear = {(int(vc[0]) + a, int(vc[1]) + b) for a in range(-7, 8) for b in range(-7, 8)}
# no pillar on the lake's cliffs: the checker reads a pool ringed by cliffs (under 400 tiles) as an enclosed room, and
# a pillar whose centre falls in a cliff's cell as furniture in it ("hall room holds CaveRockPillar...")
keep_clear |= {(i + a, j + b) for i, j in lake for a in range(-2, 3) for b in range(-2, 3)}
n_trees, n_small = d.vegetate(keep_clear=keep_clear, groves=3)
d.scatter_open(scale=0.5)
d.rim(scale=0.6)
n_lights = d.lights(scale=0.6)
piles = d.planter.rock_piles(max(4, len(land.squares) // 1100))
start_xy = square_px(north_c[0] + 0.5, north_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)

# ---- 7. the people ---------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
vx, vy = square_px(*vc)
person = sm.person
st = sm.room_of("foreman", "study")
hx, hy = sm.free_px(st) if st else square_px(vc[0] + 3, vc[1])
person("Con03A", "Lance", hx, hy, "Dagna")
fx_, fy_ = sm.outside_door("foreman") or square_px(vc[0] + 3, vc[1] + 2)
person("Con03A", "Osborn", fx_ + 15, fy_ + 15, "Wendel", face=(vx, vy))
kx_, ky_ = sm.outside_door("home") or square_px(vc[0] - 3, vc[1])
person("Con03A", "Millard", kx_ + 20, ky_ + 10, "Ketil", face=(vx, vy))
ox_, oy_ = sm.outside_door("cottage") or square_px(vc[0], vc[1] - 3)
person("Con02a", "Julie", ox_ + 15, oy_ + 15, "Orla", face=(vx, vy))
px_, py_ = square_px(north_c[0] + 1.5, north_c[1] + 0.5)
person("Con02a", "Clyde", px_, py_, "Pell", face=square_px(*vc))
gx, gy = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
gdx, gdy = vx - gx, vy - gy; gl = math.hypot(gdx, gdy) or 1
person("Con02a", "Contest_Guard", gx + 70 * gdx / gl, gy + 70 * gdy / gl, "GateGuard", face=(vx, vy))
lx, ly = square_px(gal_sq[0] + 0.5, gal_sq[1] - 0.5)
ldx, ldy = vx - lx, vy - ly; ll = math.hypot(ldx, ldy) or 1
person("Con02a", "Contest_Guard", lx + 70 * ldx / ll, ly + 70 * ldy / ll, "GalleryGuard", face=(vx, vy))
# Gunnar and Pip at the far camp, poisoned by their fire
gux, guy = far_sc.px(1.2, a_lake + 2.9)
person("Con03A", "Millard", gux, guy, "Gunnar", face=square_px(*far_c))
pix, piy = far_sc.px(1.3, a_lake + 4.0)
person("Con02a", "Heckler", pix, piy, "Pip", face=square_px(*far_c))
home_wp = pop.waypoint_path("CrewHome", [(ox_ - 25, oy_ + 30), (ox_ - 45, oy_ + 15)])
WARES = {"store": [(4, "RedPotion"), (3, "BluePotion"), (3, "CurePoisonPotion"), (2, "Meat"), (2, "Quiver"),
                   (1, "Bow"), (1, "LeatherBoots"), (1, "ChainCoif"), (1, "LeatherArmor")],
         "inn": [(5, "Meat"), (4, "Cider"), (3, "Bread"), (2, "RedPotion")],
         "smithy": [(2, "Sword"), (1, "Longsword"), (1, "WarHammer"), (1, "SteelShield"), (1, "ChainTunic"),
                    (1, "ChainLeggings"), (1, "SteelHelm"), (1, "MorningStar")]}
GREET = {"store": q.text("Company store. Ore bought, gear sold, no credit since the wages went missing.", "Shop"),
         "inn": q.text("Welcome to the Lamp & Pick! Sit near the fire; it's the only warm rock in the mountain.", "Shop"),
         "smithy": q.text("Picks mended, blades sharpened. Spider legs don't dent a good shield.", "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"smithy": "ShopkeeperWarriorsRealm"})
FOLK = [("Con02a", "Tanya"), ("Con02a", "Heckler"), ("Con03A", "Millard"), ("Con02a", "Clyde"),
        ("Con08a", "Gretchen"), ("Con02a", "Lydia")]
RUMOURS = ["We broke into an old vault in the east galleries. Dwarf work. Should have left it shut. The spiders came out.",
           "They call the big one the Lamp-Eater. She hides in the dark and only comes for the light.",
           "Gunnar's crew went to the far camp by the lake a week back. Nobody's heard. The leeches on that shore are huge.",
           "Wendel says Ketil stole the payroll diamond. Ketil? He can't keep a secret from his own wife.",
           "Things go missing at night. Lamp oil, bread, a pick. Little feet in the ore dust, heading west.",
           "Orla patches us up at the infirmary. If you're bitten, go to her before you go to bed."]
sm.townsfolk(FOLK, vc, q=q, rumours=RUMOURS,
             after=("eater_dead", "The lamps are lit in the deep galleries again. We'll be cutting by next week."),
             pics=("MaidenPic3", "MalePic1", "Townsman2Pic", "MalePic7", "MaidenPic", "MaidenPic2"), radius=5.0)

# ---- 8. the fights -----------------------------------------------------------------------------------------------
# the spiders in the webbed rocks by the road down, who fall on whoever passes
road_spiders = []
for k, (x, y) in enumerate(web_spots[:4]):
    n = f"RoadSpider{k + 1}"
    pop.creature("SmallSpider" if k < 3 else "Spider", x, y, action="idle", scr=n, aggr=0.5, sight=80)
    road_spiders.append(n)
# the brood round the vault, and the Lamp-Eater hidden in its dark
brood = []
for k, a in enumerate((0.2, 1.3, 2.4, 3.5, 4.6, 5.6)):
    x, y = square_px(nest_c[0] + 7.0 * math.cos(a), nest_c[1] - 0.5 + 7.0 * math.sin(a))
    n = f"Brood{k + 1}"
    pop.creature(("Spider", "SmallSpider", "SpittingSpider")[k % 3], x, y, action="guard", scr=n, aggr=0.83,
                 face=lamp_xy)
    brood.append(n)
for k, (x, y) in enumerate(vault["inside"][:2]):
    n = f"Brood{len(brood) + 1}"
    pop.creature("Spider", x, y, action="guard", scr=n, aggr=0.83, face=lamp_xy)
    brood.append(n)
pop.creature("AlbinoSpider", *vault["boss"], action="guard", scr="LampEater", aggr=0.83, face=lamp_xy,
             HealthMultiplier=4.0)
# the leeches of the lake shore between the lake and the far camp
leeches = []
for k, a in enumerate((-0.6, 0.0, 0.6, 1.2)):
    x, y = far_sc.px(5.5 + 0.6 * (k % 2), a_lake + a)
    n = f"Leech{k + 1}"
    pop.creature("GiantLeech", x, y, action="guard", scr=n, aggr=0.83, face=square_px(*far_c))
    leeches.append(n)
# the urchins of the warren, their shaman watching the way in
urchins = []
for k, a in enumerate((0.5, 1.6, 2.7, 3.8, 4.9)):
    x, y = war_sc.px(5.6, a_in + a)
    n = f"Urchin{k + 1}"
    pop.creature("Urchin", x, y, action="guard", scr=n, aggr=0.83, face=square_px(*vc))
    urchins.append(n)
pop.creature("UrchinShaman", *war_sc.px(1.4, a_in + math.pi * 0.85), action="guard", scr="Shaman", aggr=0.83,
             face=square_px(*vc), HealthMultiplier=1.5)
B.sentry("Shaman", square_px(*vc), rouse=urchins, shout="Thieves! Thieves in the warren!")
# the caverns' own creatures by the walls, away from the town and the story's places (never a Zombie)
sm.wild({"Bat": 4, "Scorpion": 2, "SmallSpider": 2}, away_from=vc,
        avoid=(nest_c, lake_c, shore_c, far_c, war_c, gro_c, north_c, web_c, gate_sq, gal_sq, south_c),
        per100=0.3, min_away=26)
# a few bats in the grotto: skittish
for k in range(3):
    x, y = square_px(gro_c[0] + 3 * math.cos(k * 2.1), gro_c[1] - 0.5 + 3 * math.sin(k * 2.1))
    pop.creature("Bat", x, y, action="idle", scr=f"GrottoBat{k + 1}")
    B.skittish(f"GrottoBat{k + 1}", 3.0)

# every creature, person and chest can be walked to: pillars closing a narrow neck come out
story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]] + [(c["x"], c["y"]) for c in caches + [war_chest] if c]
opened = sm.open_ways(story_xy)

# ---- 9. the story ----------------------------------------------------------------------------------------------------
q.start([A.lock("UnderGate1"), A.lock("UnderGate2"), A.lock("GalleryGate1"), A.lock("GalleryGate2"),
         A.disable("SouthExit1"), A.disable("SouthExit2"), A.disable("SouthExit3"), A.disable("VaultLamp"),
         A.disable("LampEater"),
         q.journal("The Ash Road ran into the mountain and down into dark caverns. The lamps along the road are out. "
                   "Below lies a miners' town: Deepvault.", HINT)])
wx_, wy_ = square_px(*web_c)
q.near(wx_, wy_, 190, [A.hunt(n) for n in road_spiders] +
       [A.print("Webs tear: spiders drop from the rocks beside the road!")])
# the Lamp-Eater: the brood rises when the player comes near the vault; with the brood dead, the great lamp lit draws
# their mother down out of the dark
q.near(*lamp_xy, 300, [A.hunt(n) for n in brood] + [A.print("The galleries stir. Spiders pour out of the vault.")])
q.near(*lamp_xy, 70, [A.flag("lamp_lit"), A.enable("VaultLamp"), A.spawn("LargeFlameImmobile", "VaultLamp"),
                      A.hunt("LampEater"),
                      A.print("You light the vault's great lamp. Light floods the broken hall, and something huge and "
                              "pale comes down from the dark above it."),
                      q.journal("I lit the great lamp in the dwarf vault, and the Lamp-Eater came for the light.", NOTE)],
       when=q.when(flag=q.dead(*brood), not_="lamp_lit"))
q.near(*lamp_xy, 120, [A.print("The great lamp of the vault stands cold. Its light would draw anything that hunts by "
                               "it, if the brood were not here to swarm whoever lit it.")],
       when=q.when(not_="lamp_lit"))
q.on_death("LampEater", [A.flag("eater_dead"), A.print("The Lamp-Eater crashes down across the cold stones and is still."),
                         q.journal("The Lamp-Eater is dead. Overseer Dagna will want to hear it.", QUEST)])
q.talker("Dagna", [
    q.say("Dead? The Lamp-Eater, dead? Then the deeps are ours again. The Underway Gate is open, and this is from the "
          "company, with my thanks.", when=q.when(flag="eater_dead", not_="dagna_paid"),
          do=[A.flag("dagna_paid"), A.unlock("UnderGate1"), A.unlock("UnderGate2"), A.enable("SouthExit1"),
              A.enable("SouthExit2"), A.enable("SouthExit3"), A.gold(300), A.give("ChainLeggings"),
              A.give("RedPotion", 2),
              q.journal("The Lamp-Eater is dead and Overseer Dagna has opened the Underway Gate. The south road "
                        "through the deeps is open.", COMPLETED)], who="Dagna"),
    q.say("The south road runs through the deeps a long way. Keep your lamp lit.", when=q.when(flag="dagna_paid"),
          who="Dagna"),
    q.say("She hides in the vault's dark. Kill her brood, then light the great lamp in the vault: she can't keep away "
          "from light. The gallery gate is open for you.", when=q.when(flag="dagna_told"), who="Dagna"),
    q.say("You came down the Ash Road? Then you came to a dark town. We broke into an old dwarf vault in the east "
          "galleries and a spider brood came out, and their mother with them. The Lamp-Eater, the men call her: she "
          "puts out the lamps and takes whoever carried them. I've barred the gallery gate and shut the Underway, "
          "the road south, until she's dead. Kill her and I'll open it myself. I'll have the gallery gate unbarred "
          "for you.",
          do=[A.flag("dagna_told"), A.unlock("GalleryGate1"), A.unlock("GalleryGate2"),
              q.journal("Overseer Dagna has shut the Underway Gate until the Lamp-Eater, mother of the spider brood "
                        "in the dwarf vault east of town, is dead. She has opened the gallery gate. The beast hides "
                        "in the dark: kill the brood and light the vault's great lamp to draw her out.", QUEST)],
          who="Dagna")])
q.talker("Pell", [
    q.say("I saw it from here: light in the deep galleries. Real light. I'll be lighting the road again by morning.",
          when=q.when(flag="eater_dead"), who="Pell"),
    q.say("Twenty years I've lit this road. Then the spiders came up and ate my lamps, and worse. Deepvault's below. "
          "See Overseer Dagna in her hall by the yard. And mind the webbed rocks beside the road.", who="Pell")])
q.talker("GateGuard", [
    q.say("Gate's open. Long way through the deeps; walk it with a lamp.", when=q.when(flag="dagna_paid"), who="Guard"),
    q.say("The Underway is shut by the overseer's order. Her hall is on the yard.", who="Guard")])
q.talker("GalleryGuard", [
    q.say("You did it? The galleries are quiet. I'll sleep tonight.", when=q.when(flag="eater_dead"), who="Guard"),
    q.say("The overseer said to let you through. Rather you than me.", when=q.when(flag="dagna_told"), who="Guard"),
    q.say("Gallery's barred. There are spiders the size of carts back there. Overseer's orders.", who="Guard")])
# the antidote for Gunnar's crew
q.talker("Gunnar", [
    q.say("Home. We're going home. Tell Orla we're coming.", when=q.when(flag="crew_saved"), who="Gunnar"),
    q.say("The leeches are dead? And that's Orla's antidote? Give it here. ...Ah. I can feel my legs again. Take my "
          "axe; I'm done with the deep for a while. Pip, up. We're walking.",
          when=q.when(has="PoisonProtectPotion", flag=q.dead(*leeches), not_="crew_saved"),
          do=[A.flag("crew_saved"), A.take("PoisonProtectPotion"), A.give("BattleAxe"), A.gold(60),
              A.walk("Gunnar", home_wp[0]), A.walk("Pip", home_wp[1]),
              q.journal("I brought Orla's antidote to Gunnar's crew at the far camp. They are walking home.", QUEST)],
          who="Gunnar"),
    q.say("Leeches, all along the shore. They bit us both and they're still out there. Kill them, or we'll never get "
          "past.", when=q.when(flag="", not_=q.dead(*leeches)), who="Gunnar"),
    q.say("Bitten. Both of us. Can't stand. If Orla sent something, now's the time.", who="Gunnar")])
q.talker("Pip", [
    q.say("Walking! I'm walking!", when=q.when(flag="crew_saved"), who="Pip"),
    q.say("Can't feel my legs. Gunnar does the talking.", who="Pip")])
q.talker("Orla", [
    q.say("They're back. Thin and leech-bitten, but back. You did what I couldn't. Take these.",
          when=q.when(flag="crew_saved", not_="orla_paid"),
          do=[A.flag("orla_paid"), A.gold(100), A.give("RedPotion", 3), A.give("LeatherArmoredBoots"),
              q.journal("Gunnar's crew is home. Orla paid me.", COMPLETED)], who="Orla"),
    q.say("Bitten? Sit. Breathe. You'll live.", when=q.when(flag="orla_paid"), who="Orla"),
    q.say("Go! The far camp is south-east, past the lake. Don't drink it yourself.",
          when=q.when(has="PoisonProtectPotion", not_="crew_saved"), who="Orla"),
    q.say("You lost it? ...Here. My last one. Guard it with your life, theirs depend on it.",
          when=q.when(flag="antidote_given", not_="second_dose"),
          do=[A.flag("second_dose"), A.give("PoisonProtectPotion")], who="Orla"),
    q.say("I have nothing more to give. Gunnar's crew will have to hold on.", when=q.when(flag="second_dose",
                                                                                        not_="crew_saved"), who="Orla"),
    q.say("Gunnar's crew went to the far camp by the underground lake, south-east of town, and a runner came back "
          "saying they're leech-bitten and can't walk. I can't leave the infirmary. Take this antidote to them. "
          "Don't drink it.",
          do=[A.flag("antidote_given"), A.give("PoisonProtectPotion"),
              q.journal("Orla the healer gave me an antidote for Gunnar's crew, poisoned by leeches at the far camp "
                        "by the underground lake, south-east of town.", QUEST)], who="Orla")])
# the wage diamond: Wendel blames Ketil; Ketil saw the urchins
q.on_pickup("Diamond", [q.journal("I found the company's payroll diamond in the urchins' warren. Wendel will want "
                                  "it back, and Ketil's name cleared.", QUEST)], when=q.when(not_="wages_done"))
q.talker("Wendel", [
    q.say("The payroll diamond! Where... the urchins? In the old workings? Then Ketil... oh. Oh, I have wronged that "
          "man. Here, the company's reward, and I'll go to him myself.",
          when=q.when(has="Diamond", not_="wages_done"),
          do=[A.flag("wages_done"), A.take("Diamond"), A.gold(150), A.give("SteelShield"),
              q.journal("I returned the payroll diamond to Wendel. The urchins took it, not Ketil.", COMPLETED)],
          who="Wendel"),
    q.say("I owe Ketil an apology. And a month's ale.", when=q.when(flag="wages_done"), who="Wendel"),
    q.say("Still nothing? Ketil knows where it is. I'd stake my ledgers on it.", when=q.when(flag="wendel_told"),
          who="Wendel"),
    q.say("Wendel, paymaster. The company's payroll, cut as one diamond so it's easy to carry down, was stolen from "
          "the strongroom three nights ago. Ketil stood the watch. It was Ketil, mark me. Get it back and the company "
          "will reward you.",
          do=[A.flag("wendel_told"), q.journal("Wendel the paymaster says the company's payroll diamond was stolen "
                                               "from the strongroom, and blames Ketil, who stood the night watch.",
                                               QUEST)], who="Wendel")])
q.talker("Ketil", [
    q.say("Wendel came to my door with his hat in his hands. My name's clean again. Take these; they were my father's.",
          when=q.when(flag="wages_done", not_="ketil_thanked"),
          do=[A.flag("ketil_thanked"), A.give("ChainCoif"), A.give("BluePotion", 2), A.gold(40)], who="Ketil"),
    q.say("A clean name. Best thing a man can own down here.", when=q.when(flag="ketil_thanked"), who="Ketil"),
    q.say("I told you: urchins. In the old workings to the west. Their shaman sits on everything they steal.",
          when=q.when(flag="ketil_told"), who="Ketil"),
    q.say("Wendel says I took it? I didn't! I saw them that night: little ones in rags, two of them, carrying "
          "something bright out of the strongroom and away west, into the old workings. The urchins. Nobody "
          "believes me.", when=q.when(flag="wendel_told"),
          do=[A.flag("ketil_told"), q.journal("Ketil says he saw urchins carry something bright out of the strongroom "
                                              "and away west, into the old workings.", QUEST)], who="Ketil"),
    q.say("Folk look at me sideways since the wages went. Ask Wendel why; he started it.", who="Ketil")])
q.near(*war_chest_xy, 260, [A.print("Little beds, little stools, stolen lamps. And someone in feathers by the fire.")])
q.on_death("Shaman", [A.print("The urchin shaman falls. Behind his fire, a chest.")])
for who_, pic_ in (("Dagna", "Warrior3Pic"), ("Wendel", "MalePic9"), ("Ketil", "Townsman3Pic"), ("Orla", "MaidenPic2"),
                   ("Pell", "MalePic4"), ("GateGuard", "Warrior2Pic"), ("GalleryGuard", "Warrior2Pic"),
                   ("Gunnar", "MalePic5"), ("Pip", "Townsman4Pic")):
    q.portrait(who_, pic_)

m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())

# the exteriors' dressing: composed groups of the place's things on the empty ground (kit/dressing.py)
from kit.dressing import Exterior
dressed = Exterior(m, land, "cave").dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed, os.path.join(OUT, f"{NAME}.rooms.json"))
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| pillars {n_trees} (opened {len(opened)}) | shops {n_shops} | caches {len(caches)} | lines {len(q.strings)}")
