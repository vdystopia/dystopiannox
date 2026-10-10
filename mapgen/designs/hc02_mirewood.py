"""The Hollow Choir, act 2: the Mirewood (map Mirewood). A drowned wood of black water and root walls on the road east
from Brackwater, where the Choir sings the dead up out of the mud (campaign/hollowchoir/BIBLE.md; swamp palette,
kit/biome.py BIOMES["swamp"]; built with kit/story.py as mirefen.py is).

The story
- The player follows the Choir's trail out of Brackwater along the old road and comes into the Mirewood from the west.
  Sib, an old eel-fisher mending traps by the road, saw them pass three nights back: robed folk singing as they walked,
  a boy on a rope among them. He sends the player up the causeway to Hesketh, the headman of Eelbank. Further up the
  road the drowned dead climb out of the reeds at whoever passes.
- Eelbank: the eel-fishers' huts on the one dry bank of the Mirewood, round a fire basin: Hesketh's house, Ness the
  leech-doctor's hut, Gudrun the eel-trader's (she buys and sells) and two fishers' huts. Corran keeps the causeway
  gate on the way east.
- Main quest, the Singing in the Mire: every night singing comes from the old standing stones in the east mire, where
  the old graves went under, and the drowned dead come up out of the mud to hear it. The singers took Hesketh's son
  Wat. Hesketh has barred the causeway east until it stops. The player
  1. searches the Choir's camp in the north mire (their hired blades and the camp's captain, Cantor Hale): the camp's
     chest holds the Choir's road-book, a black book of maps (marking the Greycrag mines, a bell drawn deep beneath
     them), and Tam's satchel;
  2. kills the Bone Caller (the new monster M3) who sings at the stones with the Choir's reliquary, among the drowned
     dead, and frees Wat;
  3. CHOICE B (the reliquary): Wat begs the player to smash the reliquary on the altar stone. Yes: it bursts, and the
     Mirewood's roaming dead sink back into the mud (they are disabled). No: the player keeps it, a rod of yellowed
     bone (token RELIQUARY, read in acts 7 and 10). Wat walks home either way (a journey).
  4. brings the road-book to Hesketh, who keeps it, pays and opens the causeway gate; the causeway east (the exit)
     leads to Greycrag (act 3).
- The Missing Brother (Wenna's cross-map side quest): Tam's satchel lies in the Choir's camp chest with a Choir order:
  "the ringer's boy goes on to Thornkeep, to our friend at court" (token TAM_SATCHEL, read in act 5). With Wenna's
  charm (WENNA_ASK) the satchel is known for Tam's and Ness knows the charm and saw the boy; without it the satchel is
  "a boy's satchel" and the order still says Thornkeep.
- The Bog Mother (local side quest): Ness the leech-doctor wants the green seed from the heart of the Bog Mother, a
  man-eating plant as big as a cart that has woken in the sunken hollow south of Eelbank and swallowed two eel-fishers.
  Kill it (it drops the seed, an Emerald) and bring her the seed: potions, a charm and gold.
- Gudrun's shop buys and sells; the Choir's chest, three caches in the reeds and the huts' stores hold loot.

Tokens: gives TAM_SATCHEL (a placed item: the camp chest), RELIQUARY (A.give, only on "keep"); reads WENNA_ASK
(Ness's line, the satchel's note). No other token is read here; a player with an empty pack finishes the act.

    py mapgen/designs/hc02_mirewood.py [seed]
"""
QA_ACCEPT = [   # (tests/qa.py)
    ("composition", r"is sparse: furniture covers",
     "the eel-fishers' huts and Gudrun's shop are the kit's own houses (generate_building + the furnisher at master "
     "2026-10-09): every seed of 12 tried left four to six small rooms under the half-median house rule, as every map "
     "rebuilt at master does (Ironcrag, Thornwick); the room lab's work, not this map's"),
    ("composition", r"bunched into one part of the room \(offset 0\.(77|92)",
     "two small rooms of the kit's furnisher (a 24-tile bedroom, Gudrun's shop), 0.01 and 0.16 over the line; the room "
     "pictures read as a bedroom and a shop"),
]
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import Land, square_tile, square_px, px_square, bfs_distance
from kit.biome import Dresser
from kit.village import Village
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT, NOTE
from kit.story import StoryMap
from kit.posts import camp_posts
from kit.mods import Mods
from kit.campaign import act, token, has, exit_next
from kit import camps

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 5
rng = random.Random(SEED)
ACT = act(2)
NAME = ACT["map"]                                  # Mirewood
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", ACT["design"])
PATH = "DirtLight2"                                 # the trodden ways of the mire (a floor of the swamp palette)
MAP = "BlackBook1"                                  # the Choir's road-book, its map inside: carried to Hesketh, who keeps it
                                                    # (no token's item: kit/campaign.py TOKENS)
SEED_ITEM = "Emerald"                               # the Bog Mother's heart-seed
SATCHEL, RELIQ, CHARM = token("TAM_SATCHEL"), token("RELIQUARY"), token("WENNA_ASK")


def uv(X, Y):
    """uv of a point given in map squares as seen on screen (X right, Y down, 0..255)."""
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="a drowned wood of black water and root walls on the road east from Brackwater: the eel-fishers' huts of "
          "Eelbank on the one dry bank, the Choir's camp in the north mire, the singing stones on the drowned graves in "
          "the east mire where a Bone Caller raises the dead, the Bog Mother's sunken hollow in the south, the causeway "
          "east to the Greycrag hills barred",
    environment="swamp", mood="dank, fearful, haunted by singing",
    areas=[AreaIdentity("west", "the old Brackwater road coming into the Mirewood: the start"),
           AreaIdentity("town", "Eelbank, the eel-fishers' huts on the dry bank", landmark="the fire basin"),
           AreaIdentity("hollow", "the Bog Mother's sunken hollow in the south mire"),
           AreaIdentity("camp", "the Choir's camp on a hummock in the north mire"),
           AreaIdentity("circle", "the singing stones on the drowned graves in the east mire", landmark="the stones"),
           AreaIdentity("gate", "the causeway gate, barred"),
           AreaIdentity("east", "the causeway on east to the Greycrag hills: the way out")],
    buildings=[BuildingIdentity("home", "town", "Hesketh's house", "Hesketh the headman and his son Wat"),
               BuildingIdentity("herbwife", "town", "Ness's hut", "Ness the leech-doctor"),
               BuildingIdentity("store", "town", "Gudrun's", "Gudrun the eel-trader"),
               BuildingIdentity("fisher", "town", "", "an eel-fisher's family"),
               BuildingIdentity("fisher", "town", "", "an old eel-fisher and his wife")])

m = Spec(NAME, summary="The Mirewood", description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"The Hollow Choir, act 2. Generated by Claude.", author="vdystopia (generated by Claude)", version="1",
         date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
q = QuestBook(NAME)

# ---- 1. the plan: the Brackwater road into Eelbank, the causeway east, the ways out into the mire ---------------------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"west": ((24, 150), 16), "town": ((80, 144), 62), "hollow": ((70, 220), 26), "camp": ((126, 60), 30),
         "circle": ((188, 112), 40), "gate": ((178, 192), 14), "east": ((214, 222), 12)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "town", roughness=0.3)
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_ in (("west", "town", 13, True), ("town", "gate", 13, True), ("gate", "east", 12, True),
                          ("town", "hollow", 11, False), ("town", "camp", 11, False), ("camp", "circle", 10, False),
                          ("gate", "circle", 11, False)):
    land.link(a_, b_, w_, bend=0.3, road=road_, road_material=PATH, pockets=(1, 2) if road_ else (1, 1))
d = Dresser(m, rng, land, "swamp")
m.blending("RoughCobble", 7, edge="BlendEdge")

# ---- 2. the centre: the dry bank and its fire basin ---------------------------------------------------------------
land.paint_square(m, "town", 8, "RoughCobble")
vc = land.areas["town"]["c"]
land.taken |= {(int(vc[0]) + a, int(vc[1]) + 1 + b) for a in (-1, 0, 1) for b in (-1, 0, 1)}
land.paint_roads(m, PATH, width_squares=2.4, skip=land.reserved)

# ---- 3. the huts on the bank -------------------------------------------------------------------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"west": 8, "hollow": 12, "camp": 14, "circle": 16, "gate": 8})
sm.connect_and_furnish(path_material=PATH)
# Gudrun sells salt and eels, not brews: the furnisher's cauldron goes from her shop floor (rooms.stray)
shop_r = sm.room_of("store", "shop")
if shop_r:
    shop_cells = {(x + a, y + b) for x, y in shop_r.tiles for a in (-1, 0, 1) for b in (-1, 0, 1)}
    m.d["objects"][:] = [o for o in m.d["objects"] if not (o.get("type", "").startswith("Cauldron") and
                                                          (int(o["x"] // CELL), int(o["y"] // CELL)) in shop_cells)]

# ---- 4. the land: the mire's pools, root walls, every way open -----------------------------------------------------
land.carve(margin=4.0)
C = {k: land.areas[k]["c"] for k in AREAS}
west_c, hollow_c, camp_c, circle_c, gate_c, east_c = (C[k] for k in ("west", "hollow", "camp", "circle", "gate", "east"))
lanes = sm.keep_open({"west": 4, "hollow": 6, "camp": 8, "circle": 9})


def toward(a, b, dist):
    dx, dy = b[0] - a[0], b[1] - a[1]; l_ = math.hypot(dx, dy) or 1
    return (a[0] + dx * dist / l_, a[1] + dy * dist / l_)


# pools of black water: the Black Mere between the bank and the stones, the Bog Mother's pool in the hollow, the drowned
# graves' pools round the stones, a pool or two at the bank's edge
POOLS = [(toward(circle_c, vc, 16.0), 5.5), ((hollow_c[0] + 2.5, hollow_c[1] - 2.0), 4.0),
         ((circle_c[0] + 6.5, circle_c[1] + 3.0), 3.0), ((circle_c[0] - 3.0, circle_c[1] - 7.0), 3.0),
         ((vc[0] - 13.0, vc[1] + 15.0), 3.5), ((vc[0] + 18.0, vc[1] - 14.0), 3.5)]
ring_keep = {(int(circle_c[0]) + a, int(circle_c[1]) + b) for a in range(-5, 6) for b in range(-5, 6)}
near_house = bfs_distance(list(land.taken_strict), land.squares, 4) if land.taken_strict else {}
pools = []
for c_, r_ in POOLS:                                # (the water keeps 3 squares off the huts: never against a porch)
    pools.append({s for s in land.squares if s not in land.roads and near_house.get(s, 99) >= 3 and s not in ring_keep
                  and math.hypot(s[0] - c_[0], s[1] - c_[1]) <=
                  r_ * (1 + 0.22 * math.sin(3 * math.atan2(s[1] - c_[1], s[0] - c_[0])))})
water = set().union(*pools)
calm = water | lanes
# no islands of root wall in the singing stones' wide clearing: a ring of islands seen from its middle crosses the
# edge of the sight too often on one screen row (CL-1)
stone_ground = {s for s in land.squares if math.hypot(s[0] - circle_c[0], s[1] - circle_c[1]) < 24}
outcrops = land.thickets(90, size=(1.0, 2.2), clear=1, avoid=frozenset(calm | land.taken | stone_ground))
land.open_links()
land.apply(m, wall=d.wall, floor=d.base, unlevel=True)
d.cap_islands(outcrops)
d.ground(clear=3)
for pool in pools:
    shore = [s for s in pool if any((s[0] + a, s[1] + b) not in pool for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    depth = bfs_distance(shore, pool, 6)
    for s in pool:
        if s not in land.squares: continue
        m.floor[square_tile(*s)] = "WaterSwampDeep" if depth.get(s, 0) >= 2 else "WaterSwampShallow"
    land.water |= pool & land.squares

# the causeway gate: a log palisade across the causeway east, barred
gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "east"), prefix="CausewayGate", material="Log",
                                                gate="BarredGate")

# ---- 5. the places of the story ------------------------------------------------------------------------------------
vil = Village(m, rng, land)
m.obj_px("DunMirFlameBasinLit", *square_px(vc[0], vc[1] - 0.5))
for k in range(4):
    a = k * math.pi / 2 + math.pi / 4
    m.obj_px(("Bench1", "Bench4", "Bench5", "Bench2")[k], *square_px(vc[0] + 2.6 * math.cos(a), vc[1] - 0.5 + 2.6 * math.sin(a)))
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, store=q.text("Gudrun's\nEels, salt, cures", "Sign"),
                     herbwife=q.text("Ness\nLeeches and cures", "Sign"))
for bid, b in placed:
    for sc in BUILDINGS[bid.role]["scenes"]: vil.scene(b, sc, role=bid.role)
# the singing stones: seven standing stones round an altar on the drowned graves, a sick green light over them
presets = json.load(open(os.path.join(HERE, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]


def preset(family, intensity="full"):
    ps = [p for p in presets if p["family"] == family and p["intensity_class"] == intensity] or \
         [p for p in presets if p["family"] == family]
    return dict(max(ps, key=lambda p: p["weighted_share"])["xfer"])


ring_c = (circle_c[0], circle_c[1])
ring_xy = camps.stone_ring(m, rng, land, ring_c, n=7, radius=3.2, stone="ObeliskPrimitive", core="DunMirAltar1",
                           light=preset("green"), light_name="CircleLight", clear=3)
gsc = camps.Scene(m, rng, land, ring_c)
graves = []
for k_ in range(6):                                 # the drowned graves round the stones: headstones and opened coffins
    a_ = k_ * 2 * math.pi / 6 + 0.35
    for r_ in (6.0, 6.8, 5.4, 7.6):
        o_ = gsc.put(("Tombstone3", "CoffinBreaking1", "Tombstone7", "CoffinBreaking2", "Tombstone5", "Tombstone9")[k_],
                     *gsc.at(r_, a_))
        if o_: graves.append(gsc.px(r_, a_)); break
for k_ in range(6):
    gsc.put(rng.choice(("Skull", "ArmBone", "LegBone")), *gsc.at(rng.uniform(4.2, 8.0), rng.uniform(0, 6.28)))
# the Bog Mother's hollow: bones on the pool's shore, a broken eel trap
hsc = camps.Scene(m, rng, land, (hollow_c[0], hollow_c[1]))
for k_ in range(6):
    hsc.put(rng.choice(("ArmBone", "LegBone", "Skull", "ArmBone")), *hsc.at(rng.uniform(1.0, 3.2), rng.uniform(0, 6.3)))
hsc.put("Barrel2", *hsc.at(3.4, 4.0))
# the Choir's camp on its hummock in the north mire, open toward the path from the bank; their take in the chest
camp_site = camps.camp_site(m, land, camp_c, reach=10, road_clear=2.0, room=7)
camp_way = toward(camp_site, vc, 9.0)
choir_camp = camps.bandit_camp(m, rng, land, camp_site, camp_way,
                               loot=[MAP, SATCHEL, ("Gold", {"Amount": 60}), "RedPotion", "Quiver"],
                               sleepers=4, tents=2, trade="bandit")
camp_chest = choir_camp["chest"]
assert camp_chest, "the Choir's camp has no chest for the map and the satchel"
# caches in the reeds
caches = []
for near_, loot_, stump_ in ((hollow_c, [("Gold", {"Amount": 45}), "CurePoisonPotion", "CurePoisonPotion"], True),
                             (circle_c, [("Gold", {"Amount": 55}), "BluePotion", "RedPotion"], False),
                             (camp_c, [("Gold", {"Amount": 35}), "LeatherArmoredBoots"], True)):
    s_ = sm.hidden_spot(near_, r=(10, 16))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
camps.signpost(m, land, (west_c[0] + 2.5, west_c[1] - 1.5),
               q.text("THE MIREWOOD\nEelbank up the causeway.\nKeep to the planks after dark.", "Sign"))
gs_ = sm.road_near(toward(gate_sq, vc, 4.0))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 0.5),
               q.text("CAUSEWAY BARRED\nNobody goes east while the dead walk.\n- Hesketh", "Sign"))

# ---- 6. what grows, light, the start ---------------------------------------------------------------------------------
keep_clear = {(int(vc[0]) + a, int(vc[1]) + b) for a in range(-6, 7) for b in range(-6, 7)}
n_trees, n_small = d.vegetate(keep_clear=keep_clear, groves=1)
# the root walls' undergrowth thinned by a third: the biome's rate under these walls gave 16 decorations per 100 floor
# tiles, over Westwood's swamps (7.3-14.9); every third plant of the undergrowth goes, the same ones each build
_k = 0
_keep = []
for o_ in m.d["objects"]:
    if o_.get("type") in ("Plant3", "Plant4", "Plant5", "Mushroom3", "PlantBarren1") and "scr" not in o_:
        _k += 1
        if _k % 3 == 0: continue
    _keep.append(o_)
m.d["objects"][:] = _keep
d.scatter_open(scale=0.6)
d.rim(scale=0.6)
n_lights = d.lights()
d.pools |= land.water                               # bubbles, frogs and flies on the black water
n_liq = d.dress_liquid(scale=0.5)
piles = d.planter.rock_piles(max(4, len(land.squares) // 1100))
vign = d.planter.forest_floor(3, kinds=("fallen_log", "stump"))
start_xy = square_px(west_c[0] + 0.5, west_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
exits = exit_next(sm, "east", 2, prefix="CausewayExit")

# ---- 7. the people -------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
person = sm.person
mods = Mods(m, pop)
vx, vy = square_px(*vc)
hesk_b = next(b for bid, b in placed if bid.role == "home")
hx_, hy_ = sm.doorside(building=hesk_b, toward=(vx, vy)) or (vx + 60, vy)
person("Con03A", "Osborn", hx_, hy_, "Hesketh", face=(vx, vy))
nx_, ny_ = sm.doorside("herbwife", toward=(vx, vy)) or (vx - 60, vy)
person("Con02a", "Julie2", nx_, ny_, "Ness", face=(vx, vy))
# Sib by the road, a little way in from the start, looking down it toward the player
sib_sq = sm.road_near(toward(west_c, vc, 8.0))
ssc = camps.Scene(m, rng, land, (sib_sq[0] + 0.5, sib_sq[1] - 0.5))
sib_xy = None
for da_ in (2.2, -2.2, 2.8, -2.8):
    p_ = (sib_sq[0] + 0.5 + da_ * 0.7, sib_sq[1] - 0.5 - da_ * 0.7)
    if ssc.ok(*p_):
        sib_xy = square_px(*p_); break
sib_xy = sib_xy or square_px(sib_sq[0] + 2.5, sib_sq[1] - 0.5)
person("Con03A", "Millard", *sib_xy, "Sib", face=start_xy)
ssc.put("BarrelWithTools1", *ssc.at(1.6, 0.4))
# Corran at the causeway gate, on the bank's side
gx, gy = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
gdx, gdy = vx - gx, vy - gy; gl = math.hypot(gdx, gdy) or 1
person("Con02a", "Bridge_Guard", gx + 70 * gdx / gl, gy + 70 * gdy / gl, "Corran", face=(vx, vy))
# Wat at the singing stones, among the graves, where the singers left him
wat_xy = gsc.px(4.4, math.atan2(vc[1] - ring_c[1], vc[0] - ring_c[0]) + 0.5)
person("Con02a", "Heckler", *wat_xy, "Wat", face=ring_xy)
wat_home = sm.journey("Wat", "WatHome", (hx_ + 40, hy_ + 30), look=(vx, vy))
# Gudrun behind her counter
WARES = {"store": [(4, "CurePoisonPotion"), (3, "RedPotion"), (2, "BluePotion"), (2, "PoisonProtectPotion"),
                   (3, "Meat"), (2, "Quiver"), (1, "Bow"), (1, "LeatherBoots"), (1, "ChainCoif"), (1, "WoodenShield")]}
GREET = {"store": q.text("Ah, hello! Is that coin I hear in your purse? Music to my ears! Eels, salt and cures, "
                         "come in!", "Shop")}
n_shops = sm.shops(WARES, GREET)
# the eel-fishers on their rounds of the bank, each with something to say; none stops near the mire's foes
for c_, r_ in ((hollow_c, 14), (camp_c, 16), (circle_c, 18)):
    sm.keep_folk_away(c_, r_)
FOLK = [("Con02a", "Tanya"), ("Con02a", "Clyde"), ("Con02a", "Lydia"), ("Con03B", "Logan"), ("Con01A", "Tanya2")]
RUMOURS = [
    "The frogs have gone quiet out there -- that's a bad sign.",
    "I smoke the eels for the whole bank. Nobody's bought one since the singing started.",
    "Ugh! I saw a dead man walk right past Ness's door last night, dripping!",
    "Run, stranger, run! The dead are right behind you! Ha, ha, ha...!",
    "Eel-spears against the Undead? We'll all be drowned in our beds. What's to be done?",
]
sm.townsfolk(FOLK, vc, q=q, rumours=RUMOURS,
             after=("causeway_open", "The singing's stopped. Hesketh says it was your doing."),
             pics=("MaidenPic3", "MalePic1", "MaidenPic", "MalePic7", "MaidenPic2"), radius=6.0)

# ---- 8. the fights -----------------------------------------------------------------------------------------------
# the drowned dead in the reeds beside the road, who climb out at whoever passes
mid_road = sm.road_near(toward(west_c, vc, 18.0))
risen = []
rsc = camps.Scene(m, rng, land, (mid_road[0] + 0.5, mid_road[1] - 0.5))
for r_, a_ in [(r_, k_ * math.pi / 6 + 0.3) for r_ in (3.0, 3.8, 4.6) for k_ in range(12)]:
    si_, sj_ = rsc.at(r_, a_)
    s_ = (int(math.floor(si_)), int(math.floor(sj_)) + 1)
    if s_ not in land.squares or s_ in land.roads or s_ in land.water or s_ in land.taken_strict or not rsc.ok(si_, sj_):
        continue
    x_, y_ = square_px(si_, sj_)
    if any(math.hypot(x_ - o_["x"], y_ - o_["y"]) < 60 for o_ in pop.placed): continue
    n_ = f"Risen{len(risen) + 1}"
    pop.creature("Skeleton", x_, y_, action="idle", scr=n_, aggr=0.5, sight=80, face=square_px(*mid_road))
    risen.append(n_)
    if len(risen) == 3: break
# the dead that walk the mire: they sink back into the mud when the reliquary is smashed
mired = []
for k_, (c_, t_) in enumerate(((toward(vc, circle_c, 30.0), "Skeleton"), (toward(camp_c, circle_c, 22.0), "Ghost"),
                               (toward(gate_c, circle_c, 14.0), "Skeleton"), (toward(hollow_c, vc, 14.0), "Ghost"))):
    s_ = min((s for s in land.squares if s not in land.water and s not in land.taken_strict and s not in land.roads),
             key=lambda s: math.hypot(s[0] - c_[0], s[1] - c_[1]))
    n_ = f"Mired{k_ + 1}"
    pop.creature(t_, *square_px(s_[0] + 0.5, s_[1] - 0.5), action="guard", scr=n_, aggr=0.83)
    mired.append(n_)
# the singing stones: the Bone Caller (M3) at the altar with the reliquary, the drowned dead at the graves
bc_xy = gsc.px(1.4, math.atan2(vc[1] - ring_c[1], vc[0] - ring_c[0]) + math.pi * 0.8)
mods.monster("M3", *bc_xy, name="BoneCaller", wait=260, face=wat_xy)
stone_dead = []
for k_, (x_, y_) in enumerate(graves[:3]):
    n_ = f"Drowned{k_ + 1}"
    pop.creature(("Skeleton", "Ghost", "SkeletonLord")[k_], x_, y_, action="guard", scr=n_, aggr=0.83, face=ring_xy)
    stone_dead.append(n_)
# the Choir's camp: Cantor Hale by the chest, his hired blades at their posts, archers watching the path in
choir_posts = camp_posts(m, choir_camp, square_px(*camp_way), sit=2, tents=1, watch=2)
pop.creature("Swordsman", *choir_posts["leader"], action="guard", scr="CantorHale", aggr=0.83, HealthMultiplier=2.0,
             face=square_px(*camp_way))
choir = []
for k_, (x_, y_) in enumerate(choir_posts["sit"] + choir_posts["tent"]):
    n_ = f"ChoirBlade{k_ + 1}"
    pop.creature("Swordsman", x_, y_, action="idle", scr=n_, aggr=0.83, face=choir_camp["fire"])
    choir.append(n_)
for k_, (x_, y_) in enumerate(choir_posts["watch"]):
    n_ = f"ChoirBow{k_ + 1}"
    pop.creature("Archer", x_, y_, action="guard", scr=n_, aggr=0.83, face=square_px(*camp_way))
    choir.append(n_)
B.sentry("ChoirBow1", square_px(*camp_way), rouse=["CantorHale"] + choir[:3], shout="Someone's in the reeds! Up!")
# the Bog Mother and her brood in the sunken hollow
bm_xy = hsc.px(0.0, 0.0)
pop.creature("CarnivorousPlant", *bm_xy, action="guard", scr="BogMother", aggr=0.83, HealthMultiplier=4.0)
brood = []
for k_, (t_, r_, a_) in enumerate((("CarnivorousPlant", 3.0, 0.6), ("CarnivorousPlant", 3.2, 2.6),
                                   ("CarnivorousPlant", 3.0, 4.6), ("GiantLeech", 4.8, 1.6), ("GiantLeech", 4.8, 3.8))):
    n_ = f"BogBrood{k_ + 1}"
    pop.creature(t_, *hsc.px(r_, a_), action="guard", scr=n_, aggr=0.83, face=bm_xy)
    brood.append(n_)
# the mire's own creatures by the root walls, away from the bank and the story's places
sm.wild({"GiantLeech": 2, "Wasp": 2, "WillOWisp": 1, "Bat": 2, "SpittingSpider": 2, "CarnivorousPlant": 1},
        away_from=vc, min_away=24, avoid=(hollow_c, camp_c, circle_c, west_c, gate_sq, east_c, mid_road),
        per100=0.4, gap=6)
story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]] + \
           [(c["x"], c["y"]) for c in caches + [camp_chest] if c]
opened = sm.open_ways(story_xy)

# ---- 9. the story ----------------------------------------------------------------------------------------------------
MAIN1 = "Rescue Wat from the singers at the old stones in the east mire."
MAIN2 = "Search the Choir's camp in the north mire for where they are bound."
MAIN3 = "Follow the causeway east to the Greycrag mines."
BOG = "Bring Ness the green seed from the Bog Mother's heart."
q.start([A.lock("CausewayGate1"), A.lock("CausewayGate2")] + [A.disable(n) for n in exits] +
        [q.journal("Follow the Choir's trail east into the Mirewood.", QUEST)])
# a player who carries Wenna's charm from Brackwater: read once, before anything else checks it
q.when_true(has("WENNA_ASK"), [A.flag("wenna_asked")])

# the road: the drowned dead climb out at whoever passes
mx_, my_ = square_px(*mid_road)
q.near(mx_, my_, 200, [A.hunt(n) for n in risen] + [A.print("The mud heaves beside the causeway. The drowned dead "
                                                             "are climbing out!")])
q.near(*choir_camp["fire"], 320, [A.print("Tents among the reeds and a smoky fire: the Choir's camp.")])
q.near(*ring_xy, 330, [A.print("Standing stones in black water. Someone among them is singing, and the mud is "
                               "moving.")])
q.near(*bm_xy, 300, [A.print("The hollow reeks of rot. Something huge and green is breathing in it.")])

# Sib: the hook
q.talker("Sib", [
    q.say("What are you still doing here? The causeway's open! Get after them, if you mean to catch those singers. "
          "The hills won't wait.", when=q.when(flag="causeway_open"), who="Sib"),
    q.say("Still here? Eelbank's up the road.", when=q.when(flag="met_sib"), who="Sib"),
    q.say("Hold it right there, stranger! You'll be after the singers, by the look of you. They came down this road "
          "three nights back in their robes, with a boy on a rope. Hesketh in Eelbank will want a word with you. Will "
          "you go up and see him?",
          do=[A.flag("met_sib"), q.note("NOTE: The Choir came this way three nights ago with a boy on a rope.")],
          who="Sib")])

# Hesketh: the main quest and the causeway
OPEN = [A.unlock("CausewayGate1"), A.unlock("CausewayGate2")] + [A.enable(n) for n in exits]
PAY = [A.flag("causeway_open"), A.gold(150), A.give("SteelShield"), A.give("RedPotion", 2), q.journal(MAIN3, QUEST)]
q.talker("Hesketh", [
    q.say("The causeway's open. Mind the soft ground out past the gate.", when=q.when(flag="causeway_open"),
          who="Hesketh"),
    q.say("My Wat's home! Thank the stars! You'll do, stranger. Here, it isn't much, but it's yours.",
          when=q.when(flag="wat_free", not_="wat_paid"),
          do=[A.flag("wat_paid"), A.gold(50), A.give("PoisonProtectPotion"), A.give("RedPotion")], who="Hesketh"),
    q.say("Greycrag! The old mines in the hills, at the far end of the causeway. Leave their book with me.\n\nThe singing's "
          "done and the dead lie still. The causeway is open, and Eelbank pays its debts. Go after them!",
          when=q.when(has=MAP, flag=q.dead("BoneCaller"), not_="causeway_open"),
          do=[A.take(MAP)] + OPEN + PAY, who="Hesketh"),
    q.say("You found where they're bound? Greycrag, the mines in the hills! The singing's done, too.\n\nThe causeway is "
          "open. Here, with Eelbank's thanks. Go after them!",
          when=q.at("map", 1, flag=q.dead("BoneCaller"), not_="causeway_open"),     # found, then lost or sold
          do=OPEN + PAY, who="Hesketh"),
    q.say("The singing's stopped! I heard it go quiet from here.\n\nBut where are the rest of them going? Search their camp "
          "in the north mire.", when=q.when(flag=q.dead("BoneCaller")), who="Hesketh"),
    q.say("That's their hand, all right. But they're still singing out there. Stop that first.",
          when=q.when(has=MAP), who="Hesketh"),
    q.say("Nothing yet? Then get back out in the mire. That singing has to stop, tonight!",
          when=q.when(flag="hesk_told"), who="Hesketh"),
    q.say("You came up the Brackwater road? Good. Something evil has come into the Mirewood.\n\nEvery night there's "
          "singing out at the old stones in the east mire, where the graves went under, and the drowned dead crawl out "
          "of the mud to hear it. Three nights ago the singers came through Eelbank. They took my son Wat!\n\nTheir camp "
          "is in the north mire. Stop that singing, bring Wat home and find out where they're bound. I've barred the "
          "causeway east till then.",
          do=[A.flag("hesk_told"), A.stage("main", 1), q.journal(MAIN1, QUEST), q.journal(MAIN2, QUEST)],
          who="Hesketh")],
    voice={"desc": "A weathered eel-fisher and village headman in his fifties. Deep, rough, worried voice, a broad "
                   "Lincolnshire accent. Speaks plainly and quickly.", "seed": 2101})

# the Choir's camp: the map and the satchel
q.on_pickup(MAP, [A.flag("map_found"), A.stage("map", 1), A.print("The Choir's road-book, a black book of maps: the Mirewood, the "
                                               "causeway east, and the Greycrag mines with a bell drawn deep beneath "
                                               "them."),
                  q.done(MAIN2),
                  q.note("NOTE: The Choir's road-book marks the Greycrag mines, and a bell deep beneath them.")])
ORDER = "'The ringer's boy goes on to Thornkeep, to our friend at court.'"
q.on_pickup(SATCHEL, [A.print("Tam Fell's satchel! A bell-ringer's chalk inside, and a Choir order: " + ORDER),
                      q.note("NOTE: The Choir is taking Tam Fell to Thornkeep, to a friend at court.")],
            when=q.when(flag="wenna_asked"))
q.on_pickup(SATCHEL, [A.print("A boy's satchel. A bell-ringer's chalk inside, and a Choir order: " + ORDER),
                      q.note("NOTE: The Choir is taking a bell-ringer's boy to Thornkeep, to a friend at court.")],
            when=q.when(not_="wenna_asked"))
q.on_death("CantorHale", [A.print("Cantor Hale falls among his tents. His men's take is in the chest behind him.")])

# the singing stones: the Bone Caller, Wat and the reliquary (choice B)
q.on_death("BoneCaller", [A.flag("caller_dead"), A.disable("CircleLight"),
                          A.print("The singing breaks off. Across the mire, the dead stop where they stand."),
                          q.note("NOTE: The singer at the old stones is dead. Wat is still out among the graves.")])
SMASH = [A.flag("reliq_done"), A.flag("wat_free"), A.walk("Wat", wat_home)] + [A.disable(n) for n in mired] + \
        [A.print("You bring the bone rod down on the altar stone. It shatters, and the whispering stops. All across the "
                 "Mirewood the dead sink back into the mud."),
         q.done(MAIN1)]
KEEP = [A.flag("reliq_done"), A.flag("reliq_kept"), A.flag("wat_free"), A.give(RELIQ), A.walk("Wat", wat_home),
        A.print("You keep the Choir's reliquary, a rod of yellowed bone. It is cold as the mere, and it whispers."),
        q.note("NOTE: The Choir's bone reliquary whispers in the dark."),
        q.done(MAIN1), q.tell("Wat", "Then keep it! But keep it away from me!")]
q.talker("Wat", [
    q.say("Thanks again. Just keep that thing shut, please. I'm going home.", when=q.when(has=RELIQ), who="Wat"),
    q.say("Thanks again! It's gone quiet! I know the way home through the reeds. I'm going to my father!",
          when=q.when(flag="wat_free"), who="Wat"),
    q.say("Hey, it's you! You killed him!\n\nHe sang over that rod of bone all night, and the dead came up out of the "
          "water to listen. It's still whispering. Can you hear it?\n\nSmash it on the altar stone! Will you smash it?",
          when=q.when(flag=q.dead("BoneCaller"), not_="reliq_done"), ask=True, do=SMASH, else_=KEEP, who="Wat"),
    q.say("Why are you standing there? He's singing them up out of the mud! Kill him!", who="Wat")],
    voice={"desc": "A lad of seventeen, an eel-fisher's son. Light, frightened, quick voice, a Lincolnshire accent. "
                   "Breathless.", "seed": 2102})

# Ness: the Bog Mother; Wenna's charm; the reliquary
q.on_death("BogMother", [A.drop(SEED_ITEM), A.print("The Bog Mother shudders and sags into the mud. A green seed rolls "
                                                    "out of her heart.")])
q.talker("Ness", [
    q.say("That green stone you carry... that's Wenna Fell's charm, from Brackwater! Her brother went by here with the "
          "singers. A boy with chalk on his hands. They had him on a rope!",
          when=q.when(flag="wenna_asked", not_="ness_charm"),
          do=[A.flag("ness_charm"), q.note("NOTE: Ness knew Wenna Fell's charm. She saw Wenna's brother Tam go by with "
                                           "the Choir, roped.")], who="Ness"),
    q.say("What's that bone rod you carry? It whispers! I can hear it from here. Break it, or bury it deep!",
          when=q.when(has=RELIQ, not_="ness_reliq"), do=[A.flag("ness_reliq")], who="Ness"),
] + q.errand(
    "Ness", "bog",
    offer="While the dead walk, my leeches go hungry. And there's another job here that wants a blade.\n\nThe Bog Mother "
          "has woken in the sunken hollow south of here. She's a plant as big as a cart, and she's swallowed two "
          "eel-fishers this month.\n\nHer heart is a green seed, hard as a stone. I need it for my cures. Kill her and "
          "bring me the seed. I will give you a worthy reward. Will you go?",
    reminder="Go to the hollow! Before she takes another one!",
    thanks="The Bog Mother's seed! Wonderful!\n\nTwo good men went into that hollow and never came out. I'll grieve "
           "them later. For now, take this charm and my cures.\n\nGood luck, stranger!",
    after="Thank you again, kind stranger.",
    objective=BOG, done=q.when(has=SEED_ITEM, flag=q.dead("BogMother")),
    reward=[A.give("AmuletofNature"), A.give("CurePoisonPotion", 2), A.give("RedPotion", 2), A.gold(60)],
    refusal="Then mind where you step in the south reeds."),
    voice={"desc": "An old swamp herb-woman and leech-doctor in her seventies. Dry, crackly, knowing voice, a rural "
                   "Fenland accent. Speaks briskly.", "seed": 2103})

# Corran at the gate
q.talker("Corran", [
    q.say("Passable work out at the stones. It won't make an eel-fisher of you, mind! Go on, the causeway's open.",
          when=q.when(flag="causeway_open"), who="Guard"),
    q.say("Back again!? The bar stays down till Hesketh says! Go on! I've got eels to smoke!",
          when=q.when(flag="hesk_told"), who="Guard"),
    q.say("Barred. Hesketh's orders. Go see him.", who="Guard")])

for who_, pic_ in (("Hesketh", "Townsman3Pic"), ("Ness", "MaidenPic4"), ("Wat", "MalePic5"), ("Sib", "MalePic8"),
                   ("Corran", "Warrior2Pic")):
    q.portrait(who_, pic_)

mods.attach(B)                                      # the Bone Caller's script (kit/mods.py), last of the placing
m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())

# the exteriors' dressing: composed groups of the mire's things on the empty ground (kit/dressing.py), after the
# people's routes are laid
from kit.dressing import Exterior
dressed = Exterior(m, land, "swamp", placed=placed).dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed, os.path.join(OUT, f"{NAME}.rooms.json"))
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS", "VOICE", "CAMPAIGN"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| trees {n_trees} | lights {n_lights} | shops {n_shops} | caches {len(caches)} | opened {len(opened)} "
          f"| lines {len(q.strings)} | dressing {sum(dressed.values())} groups")
