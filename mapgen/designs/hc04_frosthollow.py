"""Frosthollow: a snow village under a glacier, the third bell's shrine high above it, and act 4 of The Hollow Choir
(campaign/hollowchoir/BIBLE.md; the cast, tokens and chain are mapgen/kit/campaign.py). A town in snow: environment
"town" on the ice palette (kit/biome.py BIOMES["ice"]: ice walls, snowfields, snow pines).

The place
- The mine road from Greycrag (act 3) comes up out of the south valley into Frosthollow: log and stone houses round a
  paved square with its fire basin, the Mayor's house, the Last Fire inn, the trading post, Ulla's forge.
- North of the square the Keeper's Stair winds up the glacier in switchbacks (stairfoot, the wolves' ledge, the high
  ledge) to the bell shrine on its shelf of ice: a ring of standing stones round the empty cradle of the third bell,
  the founders' tablet beside it.
- East, through the snow pines, the ice cave where Ulla cuts her glacier iron. South-east, the valley road down to
  Thornkeep, barred by the valley gate (the exit, act 5).

The story
- The player arrives on the mine road, following the Choir from Greycrag. High above the village the third bell should
  be ringing; it is dumb. Liv, the bell-keeper's granddaughter, waits by the road (the hook): two nights ago she found
  her grandfather, Keeper Orm, dead under the bell, and a woman in grey standing over him who stepped out of the air.
  She sends the player to Mayor Gudrun.
- Main quest, the Keeper's Killer: Mayor Gudrun has barred the valley gate so the killer cannot slip down the valley
  road; the Choir's men took the bell's stone back over the glacier, but the woman stayed at the shrine as if she
  waited for someone, and the two hunters Gudrun sent up the stair have not come back. The player climbs the Keeper's
  Stair (white wolves on the first ledge, the Choir's rear guard on the high ledge) to the shrine and duels Vess, the
  Choir's assassin (the Blink Duelist, M5, as a named boss: campaign.FOES["Vess"]), who was left to stop whoever came
  after the stones. Beaten (below a quarter of her health: kit/hc_story yield_at), she drops her blade and kneels;
  she says the stone went over the glacier with Morvaine's singers, and that Morvaine has a man at the Baron's court in
  Thornkeep. Choice C: spare her (yes) and she gives her silvered eyeglass, the Choir's mark of rank, as her oath
  (VESS_OATH), and steps through the air and is gone; refuse (no) and she springs up and fights to the death: her
  blade, the Bloodthirst (W5), falls in the snow beside her (kit/hc_story prize: made with its power). A blow that
  kills her before she yields is the same as refusing. The bell's
  stone is gone, but the founders' tablet by the bell holds a verse of the ringing: one of the blue stones the keeper
  kept in its hollow for pilgrims takes the rubbing, VERSE_STONE (The Last Verse, acts 1, 3, 4, 7, 10), once, when
  Vess has yielded or fallen. Mayor Gudrun pays and opens the valley gate; the valley road leads to
  Thornkeep (the exit), where the Choir's man sits.
- The Frostsmith's Seam (local): a Troll and frost spiders have taken the ice cave where Ulla the frostsmith cuts her
  glacier iron. Clear them and she gives the best thing she ever made of that iron: the Frostbite (W6), a morning star
  that freezes what it strikes (made with its power and handed over by kit/hc_story give: A.give would make a plain
  morning star).
- Asa's Sons (local): Old Asa's sons were the two hunters Gudrun sent up the stair. The player finds them dead below
  the high ledge, where the Choir's men caught them; Asa pays with her sons' bow.
- The inn, the trading post and Ulla's forge buy and sell. The houses' stores, two caches in the snow and the
  hunters' packs hold loot; every soul in the village knows something.

    py mapgen/designs/hc04_frosthollow.py [seed]
"""
QA_ACCEPT = [   # (tests/qa.py)
    # the houses are the kit's own (generate_building + the furnisher at master 2026-10-09): every map rebuilt today
    # gets these (Ironcrag accepts the same, Thornwick's rebuild had 14); a room-lab matter, not this map's. The seed
    # was chosen from 8 tried for the fewest warnings (and the sight check's margin)
    ("composition", r"is sparse: furniture covers",
     "the kit's furnisher fills small house rooms under the half-median house rule on every map at master (Ironcrag, "
     "Thornwick); the room lab's work, not this map's"),
    ("density", r"^Many share of floor seams with edge pieces",
     "the ice palette blends every open seam (BIOMES['ice'] blends: ice floors, rock patches, the paths), as Rimehold's; "
     "the seams at walls are hard by rule (TW-12)"),
    ("rooms", r"holds (PiledBarrels1|OvalTable2), which does not belong",
     "the furnisher's top-up (kit/furnish.py) leaves one piled barrel in the trading post's shop room and an oval table in "
     "a bedroom; the room pictures read as a shop and a bedroom"),
]
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL, px
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import Land, square_tile, square_px, px_square, bfs_distance
from kit.biome import Dresser
from kit.vegetation import Planter, TOWN_PLANTING
from kit.village import Village
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT, NOTE
from kit import camps
from kit.story import StoryMap
from kit.posts import camp_posts
from kit.dressing import Exterior
from kit.mods import Mods, WEAPONS
from kit.hc_story import HcStory
from kit.campaign import CAST, act, token, has, cast_person, voice, exit_next, FOES

ACT = 4
NAME = act(ACT)["map"]                # Frosthol
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 3
rng = random.Random(SEED)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "hc04_frosthollow")
PATH = "CaveHardTan"                  # the trodden ways: bare rock through the snow (a floor of the ice palette)
# Vess: her body when she talks (Westwood's women are Maiden clones) and her voice: the same in act 9
# (proposed for campaign.CAST: see the report)
VESS_DONOR = CAST["Vess"]["donor"]                      # the same body in act 9 (kit/campaign.py)
VESS_VOICE = CAST["Vess"]["voice"]                    # the same voice in act 9


def uv(X, Y):
    """uv of a point given in map cells as seen on screen (X right, Y down, 0..255)."""
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="a snow village under a glacier: log and stone houses round a paved square and its fire basin, the Mayor's "
          "house, an inn, a trading post and the frostsmith's forge; the Keeper's Stair winding up the ice to the "
          "third bell's shrine on its shelf, its bell dumb; the frostsmith's ice cave in the east pines; the valley gate "
          "barred on the road down to Thornkeep",
    environment="town", mood="cold, grieving, watchful",
    areas=[AreaIdentity("south", "the mine road up out of the valley from Greycrag: the start"),
           AreaIdentity("village", "Frosthollow's square and its houses", landmark="the fire basin"),
           AreaIdentity("stairfoot", "the foot of the Keeper's Stair at the village's north edge"),
           AreaIdentity("ledge1", "the first switchback of the stair, the white wolves' ledge"),
           AreaIdentity("ledge2", "the high ledge, where the Choir's rear guard waits"),
           AreaIdentity("shrine", "the bell shrine on its shelf of ice: the empty cradle, the founders' tablet",
                        landmark="the ring of standing stones"),
           AreaIdentity("pines", "the snow pines on the way to the ice cave"),
           AreaIdentity("icecave", "the ice cave where Ulla cuts her glacier iron"),
           AreaIdentity("gate", "the valley gate, barred"),
           AreaIdentity("east", "the valley road on down to Thornkeep: the way out")],
    buildings=[BuildingIdentity("foreman", "village", "the Mayor's house", "Mayor Gudrun"),
               BuildingIdentity("inn", "village", "The Last Fire", "the innkeeper"),
               BuildingIdentity("store", "village", "the trading post", "the trader"),
               BuildingIdentity("smithy", "village", "Ulla's forge", "Ulla the frostsmith"),
               BuildingIdentity("home", "village", "", "Old Asa"),
               BuildingIdentity("home", "village", "", "a goatherd's family"),
               BuildingIdentity("cottage", "village", "the keeper's cottage", "Keeper Orm and Liv"),
               BuildingIdentity("cottage", "village", "", "a woodcutter")])

m = Spec(NAME, summary=act(ACT)["title"], description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"The Hollow Choir, act {ACT}. Generated by Claude.", author="vdystopia (generated by Claude)", version="1",
         date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
q = QuestBook(NAME)
presets = json.load(open(os.path.join(HERE, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]


def preset(family, intensity="full"):
    ps = [p for p in presets if p["family"] == family and p["intensity_class"] == intensity] or \
         [p for p in presets if p["family"] == family]
    return dict(max(ps, key=lambda p: p["weighted_share"])["xfer"])


# ---- 1. the plan: the mine road up to the village, the stair up the glacier, the ways east -------------------------------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"south": ((66, 224), 18), "village": ((106, 158), 64), "stairfoot": ((124, 98), 14), "ledge1": ((172, 82), 16),
         "ledge2": ((118, 56), 18), "shrine": ((176, 32), 27), "pines": ((178, 140), 16), "icecave": ((216, 120), 22),
         "gate": ((176, 196), 12), "east": ((214, 214), 14)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "village", roughness=0.24)
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_, bend_ in (("south", "village", 14, True, 0.18), ("village", "stairfoot", 12, True, 0.1),
                                 ("stairfoot", "ledge1", 10, True, 0.14), ("ledge1", "ledge2", 10, True, 0.14),
                                 ("ledge2", "shrine", 10, True, 0.14), ("village", "pines", 11, False, 0.22),
                                 ("pines", "icecave", 11, False, 0.22), ("village", "gate", 13, True, 0.12),
                                 ("gate", "east", 12, True, 0.12)):
    pk_ = (0, 0) if {a_, b_} & {"ledge1", "ledge2", "shrine"} else (1, 2) if road_ else (0, 1)
    land.link(a_, b_, w_, bend=bend_, road=road_, road_material=PATH, pockets=pk_)
d = Dresser(m, rng, land, "ice")
m.d["ambient"] = [116, 122, 152]          # a snow village by day: Westwood's ice light, brighter
m.blending("RoughCobble", 7, edge="BlendEdge")

# ---- 2. the centre: the square and its fire basin, the roads leaving it ----------------------------------------------
vc = land.areas["village"]["c"]
land.paint_square(m, "village", 10, "RoughCobble")
land.taken |= {(int(vc[0]) + a, int(vc[1]) + 1 + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}
land.paint_roads(m, PATH, width_squares=2.6, skip=land.reserved | land.forbidden)

# ---- 3. the village's houses from the square outwards; none on the stair or the wild places --------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"south": 9, "stairfoot": 8, "pines": 10, "icecave": 14, "gate": 6},
                            square_area="village")
sm.connect_and_furnish(path_material=PATH)

# ---- 4. the land: cliffs of ice round the village and the stair, every way open ---------------------------------------
land.carve(margin=3.5)
taken0 = set(land.taken)
lanes = sm.keep_open({"south": 4, "stairfoot": 5, "ledge1": 8, "ledge2": 9, "shrine": 16, "icecave": 10, "gate": 3})
held_open = land.taken - taken0             # kept open for the forest only (below)
outcrops = land.thickets(270, size=(0.9, 2.0), clear=1, avoid=frozenset(lanes & land.squares))
land.open_links()
land.apply(m, wall=d.wall, floor=d.base, unlevel=True)
d.cap_islands(outcrops)
d.ground()
gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "east"), prefix="ValleyGate", material="Cobblestone")
land.taken -= held_open                     # the ice is laid: the story's places may be dressed now

PARK = (46.0, 46.0)                        # off the map's floor (Westwood parks scripted creatures so): where the
                                           # beaten Vess waits, hidden, while she kneels

# ---- 5. the village's life --------------------------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Last Fire\nBroth, beds and a seat by the fire", "Sign"),
                     store=q.text("Trading Post\nFurs bought, rope and lamp oil sold", "Sign"),
                     smithy=q.text("Ulla's Forge\nGlacier iron", "Sign"),
                     foreman=q.text("Mayor of Frosthollow", "Sign"))
for bid, b in placed:
    role = BUILDINGS[bid.role]
    for sc in role["scenes"]: vil.scene(b, sc, role=bid.role)
basin_xy = square_px(vc[0] + 0.5, vc[1] - 0.5)
m.obj_px("DunMirFlameBasinLit", *basin_xy)


def torch_pole(si, sj):
    s = (int(si), int(sj) + 1)
    if s not in land.squares or s in land.water or s in land.taken_strict: return False
    x, y = square_px(si, sj)
    cx, cy = int(x // 23), int(y // 23)
    if any((cx + a, cy + b) in m.wallmap or (cx + a, cy + b) in m.door_gaps for a in (-1, 0, 1) for b in (-1, 0, 1)):
        return False
    m.obj_px("TorchPole", x, y)
    return True


vil.square_piece((vc[0] + 0.5, vc[1] - 0.5), 5, pole=torch_pole, per_side=1)

# ---- 6. the story's places ------------------------------------------------------------------------------------------
C = {k: land.areas[k]["c"] for k in AREAS}
south_c, foot_c, l1_c, l2_c, shrine_c, pines_c, cave_c, gate_c, east_c = (
    C[k] for k in ("south", "stairfoot", "ledge1", "ledge2", "shrine", "pines", "icecave", "gate", "east"))
DOORS_SQ = [px_square(*dd.px) for _, b in placed for dd in b.entrances]


def off_road(c, clear=4.5, reach=12, doors=6):
    """The square nearest `c` with no road within `clear` squares, on open land, `doors` squares from every door."""
    near_road = bfs_distance(list(land.roads), land.squares, int(clear) + 1)
    cands = [s for s in land.squares if near_road.get(s, 99) >= clear and s not in land.taken_strict and
             s not in land.taken and s not in land.water and math.hypot(s[0] - c[0], s[1] - c[1]) <= reach and
             all(math.hypot(s[0] - dd[0], s[1] - dd[1]) >= doors for dd in DOORS_SQ)]
    s = min(cands, key=lambda s: math.hypot(s[0] - c[0], s[1] - c[1])) if cands else (int(c[0]), int(c[1]))
    return (s[0] + 0.5, s[1] - 0.5)


# the bell shrine: a ring of standing stones round the empty cradle, ice columns round the shelf, the founders' tablet
ring_c = off_road(shrine_c, clear=2.5, reach=8)
shrine_xy = camps.stone_ring(m, rng, land, ring_c, n=8, radius=3.0, stone="Obelisk", core="DunMirAltar1",
                             core_name="BellCradle", light=preset("blue", "dim"), light_name="BellLight", clear=4)
ssc = camps.Scene(m, rng, land, ring_c)
toward_stair = math.atan2(l2_c[1] - ring_c[1], l2_c[0] - ring_c[0])
tablet = None
for a_ in (toward_stair + 2.4, toward_stair - 2.4, toward_stair + math.pi):
    tablet = ssc.put("SignDunMir01", *ssc.at(4.4, a_), xfer={"Text": q.text(
        "THE FOUNDERS' TABLET\nRing the five together at the year's turning,\nand what sleeps below sleeps on.", "Sign")})
    if tablet: break
assert tablet, "the founders' tablet found no floor"
tablet_xy = (tablet["x"], tablet["y"])
for k_ in range(5):
    a_ = toward_stair + math.pi + (k_ - 2) * 0.55
    ssc.put(("IceColumn", "IceColumn2")[k_ % 2], *ssc.at(6.4 + 0.5 * (k_ % 2), a_))
for t_, a_ in (("MineCrystal02", toward_stair + 1.3), ("MineCrystal05", toward_stair - 1.4)):     # ice glittering
    ssc.put(t_, *ssc.at(7.4, a_))                                                               # in the glacier
# the stair: the foot's signpost, the high ledge where the hunters fell (their bones, their bows)
camps.signpost(m, land, (foot_c[0] + 2.0, foot_c[1] - 1.5),
               q.text("THE KEEPER'S STAIR\nTo the bell shrine.\nMind the ice.", "Sign"))
hsc = camps.Scene(m, rng, land, off_road(l2_c, clear=2.0, reach=6))
hunters_xy = square_px(hsc.ci, hsc.cj)
for t_, r_, a_ in (("CorpseSkullSW", 0.6, 0.4), ("CorpseRibCageS", 0.9, 1.4), ("CorpseLeftLowerLegE", 1.1, 2.3),
                   ("CorpseSkullNE", 1.8, 3.6), ("CorpseRibCageW", 2.1, 4.2), ("Bow", 1.4, 5.2), ("Quiver", 2.4, 5.7)):
    hsc.put(t_, *hsc.at(r_, a_))
# the ice cave: Ulla's seam (crystals), her tools left where she dropped them
cave_sq = off_road(cave_c, clear=3.0, reach=8)
csc = camps.Scene(m, rng, land, cave_sq)
for t_, r_, a_ in (("MineCrystal05", 3.4, 0.4), ("MineCrystal02", 3.8, 1.0), ("MineCrystal04", 3.6, 1.6),
                   ("MiningPickAxeInGround1", 2.4, 2.8), ("BarrelWithTools1", 3.0, 3.6), ("MineCrystal03", 4.0, 4.6)):
    csc.put(t_, *csc.at(r_, a_))
rc_ = land.areas["icecave"]["r"] * 1.15
m.polygon(f"{NAME}:IceCave", (52, 58, 104),
          [square_px(cave_c[0] + rc_ * math.cos(a), cave_c[1] + rc_ * math.sin(a)) for a in (k * math.pi / 8 for k in range(16))])
# caches in the snow
caches = []
for near_, loot_, stump_ in ((south_c, [("Gold", {"Amount": 40}), "RedPotion", "CurePoisonPotion"], False),
                             (pines_c, [("Gold", {"Amount": 55}), "BluePotion", "LeatherArmoredBoots"], False)):
    s_ = sm.hidden_spot(near_, r=(5, 12))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
camps.signpost(m, land, (south_c[0] + 2.5, south_c[1] - 1.5),
               q.text("FROSTHOLLOW\nUnder the bell.", "Sign"))
gs_ = sm.road_near(((gate_sq[0] * 2 + vc[0]) / 3, (gate_sq[1] * 2 + vc[1]) / 3))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 1.5),
               q.text("THE VALLEY GATE IS BARRED\nUntil the keeper's killer is found.\n- Gudrun, Mayor", "Sign"))

# ---- 7. planting and the start; the exit -------------------------------------------------------------------------------
keep = {(int(vc[0]) + a, int(vc[1]) + b) for a in range(-7, 8) for b in range(-7, 8)}
for bid, b in placed:
    for dd in b.entrances:
        di, dj = px_square(*dd.px)
        keep |= {(di + a, dj + b2) for a in range(-2, 3) for b2 in range(-2, 3)}
vil.ground_bits(1.2)
planter = Planter(m, rng, land, "ice", keep_clear=keep | lanes | d.taken, settled=("village",))
n_trees, n_small = planter.plant_all(groves=3, profile=TOWN_PLANTING)
d.scatter_open(scale=0.7)            # the snowfields' own loose pieces: rocks, ice cracks, old bones
d.rim(scale=0.8)
n_lights = d.lights(scale=0.4)
piles = planter.rock_piles(max(4, len(land.squares) // 1000))
start_xy = square_px(south_c[0] + 0.5, south_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
exits = exit_next(sm, "east", ACT, prefix="ValleyExit")

# ---- 8. the people --------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
person, room_of, free_px = sm.person, sm.room_of, sm.free_px
vx, vy = square_px(*vc)
# Liv by the mine road, looking up it
lx_, ly_ = square_px(south_c[0] - 1.5, south_c[1] + 2.5)
person("Con02a", "Gretchen", lx_, ly_, "Liv", face=start_xy)
# Mayor Gudrun in her study
st = room_of("foreman", "study")
gx_, gy_ = sm.stand_px(st) if st else (vx + 40, vy)
person("Con02a", "Lydia", gx_, gy_, "Gudrun")
# Ulla by her forge's door, Old Asa by hers
ul_ = sm.doorside("smithy", toward=(vx, vy)) or (vx - 60, vy)
person("Con02a", "Joyce", ul_[0], ul_[1], "Ulla", face=(vx, vy))
asa_b = next((b for bid, b in placed if bid.occupant == "Old Asa"), None)
as_ = sm.doorside(building=asa_b, toward=(vx, vy)) if asa_b else None
as_ = as_ or (vx + 60, vy + 30)
person("Con02a", "Tanya", as_[0], as_[1], "Asa", face=(vx, vy))
# the valley gate's guard, on the village side
gq_ = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
gdx, gdy = vx - gq_[0], vy - gq_[1]
gl = math.hypot(gdx, gdy) or 1
person("Con02a", "Contest_Guard", gq_[0] + 70 * gdx / gl + 24, gq_[1] + 70 * gdy / gl, "ValleyGuard", face=(vx, vy))
# Vess at the shrine: the duelist (M5, named: kit/mods), and the woman she is when she yields (placed disabled)
vsx, vsy = square_px(ring_c[0] + 1.6 * math.cos(toward_stair), ring_c[1] + 1.6 * math.sin(toward_stair))
mods = Mods(m, pop)
pop.creature("Swordsman", vsx, vsy, action="guard", scr="Vess", aggr=0.83, face=square_px(*l2_c), spread=False)
mods.monster_call("duelist", "Vess", FOES["Vess"]["title"], FOES["Vess"]["hp"], 230.0, 0.0)
person(VESS_DONOR[0], VESS_DONOR[1], vsx, vsy, "VessYield", face=square_px(*l2_c))
# shopkeepers
WARES = {"store": [(4, "RedPotion"), (3, "BluePotion"), (3, "CurePoisonPotion"), (3, "Meat"), (2, "Quiver"),
                   (1, "Bow"), (1, "MedievalCloak"), (1, "LeatherArmoredBoots"), (1, "LeatherHelm"), (1, "LeatherArmor")],
         "inn": [(5, "Meat"), (4, "Cider"), (4, "Bread"), (3, "RedApple"), (2, "RedPotion")],
         "smithy": [(2, "Sword"), (1, "Longsword"), (1, "MorningStar"), (1, "BattleAxe"), (1, "WoodenShield"),
                    (1, "SteelShield"), (1, "ChainCoif"), (1, "ChainTunic"), (1, "ChainLeggings"), (1, "PlateBoots")]}
GREET = {"store": q.text("Furs in, rope out. And lamp oil, if you mean to go up the stair after dark.", "Shop"),
         "inn": q.text("Come in out of the snow! Sit by the fire. The broth's hot, if nothing else is.", "Shop"),
         "smithy": q.text("Ulla's forge. I keep the counter while she's out. Glacier iron, the best in the north!",
                          "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"smithy": "ShopkeeperWarriorsRealm"})
# townsfolk, each with something to tell
for c_, r_ in ((foot_c, 6), (cave_c, 14), (pines_c, 8), (gate_c, 5)):
    sm.keep_folk_away(c_, r_)
FOLK = [("Con02a", "Julie"), ("Con02a", "Clyde"), ("Con03A", "Osborn"), ("Con02a", "Jacob"), ("Con08a", "Gretchen"),
        ("Con03A", "Millard")]
RUMOURS = [
    "Run, if you've any sense! There's a killer on the mountain!",
    "The bell rang every dusk for a hundred years. Now listen. Nothing.",
    "Men in grey came over the glacier the night Orm died. Singing, Liv says. Singing!",
    "Ulla's not been to her ice cave for a week. Something big lives in there now.",
    "Who'd kill an old man for a bell? What's the world coming to?",
    "The valley gate's barred. My mule's stuck on this side and my wife's on the other.",
]
ring = sm.townsfolk(FOLK, vc, q=q, rumours=RUMOURS,
                    after=("main_done", "They say you went up the stair and came back down! The valley gate's open."),
                    pics=("MaidenPic3", "MalePic7", "Townsman2Pic", "MalePic8", "MaidenPic2", "Townsman3Pic"),
                    radius=6.5)
wx2, wy2 = ring[0]
person("Con02a", "IxGuard2", wx2, wy2, "Watch1", action=0)
sm.beat("Watch1", vc, radius=6.5, stops=6)

# ---- 9. the fights ----------------------------------------------------------------------------------------------------
# the white wolves on the first ledge, a pack round their leader
l1_wolves = []
for k_, (r_, a_) in enumerate(((0.0, 0.0), (2.6, 0.8), (2.4, 2.6), (2.8, 4.4))):
    n_ = f"LedgeWolf{k_ + 1}"
    pop.creature("WhiteWolf" if k_ else "BlackWolf", *square_px(l1_c[0] + r_ * math.cos(a_), l1_c[1] + r_ * math.sin(a_)),
                 action="idle", scr=n_, aggr=0.83, face=square_px(*foot_c))
    l1_wolves.append(n_)
B.pack(l1_wolves[0], l1_wolves[1:])
# the Choir's rear guard on the high ledge, a lookout who rouses the others
rear = []
for k_, (r_, a_, t_) in enumerate(((3.2, 0.3, "Swordsman"), (3.4, 2.3, "Swordsman"), (4.0, 4.3, "Archer"))):
    n_ = f"ChoirBlade{k_ + 1}"
    pop.creature(t_, *square_px(l2_c[0] + r_ * math.cos(a_), l2_c[1] + r_ * math.sin(a_)), action="guard", scr=n_,
                 aggr=0.83, face=square_px(*l1_c))
    rear.append(n_)
B.sentry("ChoirBlade3", square_px(*l1_c), rouse=rear[:2], shout="Someone on the stair! Up, up!")
# the ice cave: the Troll on Ulla's seam, frost spiders round it
cave_foes = []
tx_, ty_ = csc.px(1.2, 2.0)
pop.creature("Troll", tx_, ty_, action="guard", scr="CaveTroll", aggr=0.83, HealthMultiplier=1.6)
cave_foes.append("CaveTroll")
for k_, a_ in enumerate((0.6, 2.2, 3.9, 5.4)):
    n_ = f"FrostSpider{k_ + 1}"
    pop.creature("AlbinoSpider" if k_ % 2 else "SmallAlbinoSpider", *csc.px(5.0, a_), action="guard", scr=n_,
                 aggr=0.83, face=square_px(*pines_c))
    cave_foes.append(n_)
# the snowfields' own creatures, away from the village and the story's places
sm.wild({"WhiteWolf": 2, "Bat": 2, "SmallAlbinoSpider": 2}, away_from=vc, per100=0.5, gap=7, min_away=30,
        avoid=(south_c, foot_c, l1_c, l2_c, shrine_c, cave_c, gate_c, east_c))

story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]
            if px_square(o["x"], o["y"])[0] > 40] + [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)

# ---- the story's helpers (kit/hc_story): Vess yields, is spared or killed; the prizes -----------------------------------
hc = HcStory(m)
hc.yield_at("Vess", "VessYield", 25, "vess_beaten", park=PARK,
            text="Vess staggers back, lets her blade fall and goes down on one knee in the snow.")
hc.doom("vess_doomed", "VessYield", "Vess", text="'So be it.' Vess snatches up her blade and springs at you.")
hc.vanish("vess_spared", "VessYield", text="Vess steps into the air and is gone, as if she had never stood there.")
hc.prize("Vess", "W5", text="Vess's blade falls in the snow beside her: the Bloodthirst.")
hc.give("ulla_paid", "W6", text="Ulla puts the Frostbite in your hands.")

# ---- 10. the story ----------------------------------------------------------------------------------------------------
OATH, VERSE = token("VESS_OATH"), token("VERSE_STONE")
MAIN = "Climb to the bell shrine and stop the keeper's killer."
q.start([A.lock("ValleyGate1"), A.lock("ValleyGate2"), A.disable("VessYield")] + [A.disable(n) for n in exits] +
        [q.journal("Find out why the bell above Frosthollow is silent.", HINT)])
q.near(*start_xy, 200, [A.print("High above the village a bell should be ringing. It is silent.")])

# Liv: the hook
q.talker("Liv", [
    q.say("You came back down! Did you see her? Is she gone?", when=q.when(flag="main_done"), who="Liv"),
    q.say("Gudrun's house is on the square. Please, go!", when=q.when(flag="met_liv"), who="Liv"),
    q.say("Are you one of them, stranger? ...No. You came up the mine road.\n\nThey killed my grandfather! Up at the bell, two "
          "nights ago. A woman in grey stood over him -- she stepped right out of the air! The bell hasn't rung since."
          "\n\nGo to Mayor Gudrun. Please!",
          do=[A.flag("met_liv"), A.stage("main", 1), q.journal("Speak to Mayor Gudrun in Frosthollow.")], who="Liv")])

# Mayor Gudrun: the main quest and the gate
q.talker("Gudrun", [
    q.say("The gate's open, and you've Frosthollow's thanks for as long as the bell hangs.", when=q.when(flag="main_done"),
          who="Gudrun"),
    q.say("You let her go? With Orm's blood hardly dry?\n\n...She'll not come back to Frosthollow, I'll grant you that. "
          "Take your pay. The valley gate is open. If the Choir has a man in Thornkeep, the road there is yours.",
          when=q.when(has=OATH, not_="main_done"),
          do=[A.flag("main_done"), A.gold(150), A.give("RedPotion", 2), A.unlock("ValleyGate1"), A.unlock("ValleyGate2")] +
             [A.enable(n) for n in exits] + [q.done(MAIN),
              q.journal("Follow the valley road down to Thornkeep, where the Choir has a man at court.", QUEST)],
          who="Gudrun"),
    q.say("She's dead? Then Orm can rest, and so can we!\n\nHere, as I promised. The valley gate is open. The Choir's "
          "men went down that road too, the shepherds say. Thornkeep's at the end of it.",
          when=q.when(flag=q.dead("Vess"), not_="main_done"),
          do=[A.flag("main_done"), A.gold(150), A.give("RedPotion", 2), A.unlock("ValleyGate1"), A.unlock("ValleyGate2")] +
             [A.enable(n) for n in exits] + [q.done(MAIN),
              q.journal("Follow the valley road down to Thornkeep, where the Choir has a man at court.", QUEST)],
          who="Gudrun"),
    q.say("The stair starts at the north edge of the village. Go carefully!", when=q.when(flag="gudrun_told"),
          who="Gudrun"),
    q.say("Liv sent you? Then you know. Keeper Orm is dead, and the bell's stone is gone. Men in grey came over the "
          "glacier and carried it off the way they came. But one stayed. A woman. She's still up at the shrine, as if "
          "she was waiting for someone.\n\nI sent two hunters up the stair. They haven't come back.\n\nI've barred the "
          "valley gate so she can't slip away down the valley. Go up the Keeper's Stair and deal with her, traveller, and "
          "I'll open it.",
          do=[A.flag("gudrun_told"), A.stage("main", 2), q.journal(MAIN)], who="Gudrun")])

# the climb
q.near(*square_px(*l1_c), 260, [A.print("Wolf tracks in the snow, and something white moving on the ledge above.")])
q.on_all_dead(rear, [A.flag("rear_dead"), A.print("The last of the Choir's men falls on the high ledge.")])
q.near(*hunters_xy, 110, [A.flag("hunters_found"), A.print("Two of Frosthollow's hunters lie among the rocks, their "
                                                         "bows beside them."),
                          q.note("NOTE: Old Asa's sons lie dead on the high ledge of the Keeper's Stair.")])
q.near(*shrine_xy, 330, [A.print("A woman in grey waits by the empty bell, a long blade across her knees.")])

# Vess: beaten, she kneels; the choice
q.talker("VessYield", [
    q.say("Enough! You've won. Hear me first.\n\nThe stone went over the glacier with Morvaine's singers. You came "
          "too late for it. And Morvaine has a man at the Baron's elbow in Thornkeep -- that's who sent me here, to wait "
          "for whoever followed the stones.\n\nSo. Will you let me live?",
          ask=True,
          do=[A.flag("vess_spared"), A.give(OATH),
              A.print("Vess presses a silvered eyeglass into your hand: the Choir's mark of rank, given as her oath."),
              q.note("NOTE: Vess, the Choir's blade, gave her eyeglass as her oath. She says Morvaine has a man at the "
                     "Baron's court in Thornkeep."),
              q.journal("Tell Mayor Gudrun that the keeper's killer is gone.", QUEST)],
          else_=[A.flag("vess_doomed"),
                 q.note("NOTE: Vess says Morvaine has a man at the Baron's court in Thornkeep.")],
          who="Vess", mood="Cool and level, catching her breath.")], title="Vess", voice=VESS_VOICE)
q.on_death("Vess", [A.flag("vess_dead"), q.journal("Tell Mayor Gudrun that the keeper's killer is dead.", QUEST)])

# the founders' tablet: the verse of the bells, rubbed onto one of the keeper's blue stones, once Vess has yielded or
# fallen; once even across a saved game (kit/hc_story take_near: a token given twice would miscount act 10's verses)
hc.take_near(*tablet_xy, 70, ("vess_beaten", "dead:Vess", "has:" + OATH), VERSE, "verse_taken",
             text="A smooth blue stone lies in the tablet's hollow, kept for pilgrims. You press it to the founders' "
                  "words, and the verse stays on it.")
q.when_true(q.when(flag="verse_taken"), [q.note("NOTE: A verse of the bells, rubbed from the founders' tablet onto a "
                                                "blue stone.")])

# the valley gate's guard and the watch
q.talker("ValleyGuard", [
    q.say("Gate's open! The road goes down the valley to Thornkeep. Mind the ice on the bends.",
          when=q.when(flag="main_done"), who="Guard"),
    q.say("Barred, by the Mayor's word! Nobody goes down the valley till Orm's killer is found.", who="Guard")])
q.talker("Watch1", [
    q.say("You did it! I'll ring that bell myself when they bring a new stone.", when=q.when(flag="main_done"), who="Watch"),
    q.say("Keep off the stair after dark. Hopeless, the pair of them that went up!", who="Watch")])

# The Frostsmith's Seam: Ulla and the Frostbite
q.talker("Ulla", q.errand(
    "Ulla", "seam",
    offer="There's a Troll in my ice cave! It came down off the glacier and sat itself right on my seam of glacier "
          "iron, with frost spiders round it like hens!\n\nPlease, I can't work without that iron. The cave's east of "
          "the village, through the snow pines.\n\nWould you clear it out for me?",
    reminder="Please hurry! My forge has been cold for a week!",
    thanks="The cave's clear? Oh, thank you so much!\n\nHere. The finest thing I ever made of that iron. I call it the "
           "Frostbite. Whatever it strikes, the cold gets into.",
    after="My forge is roaring again, thanks to you!",
    objective="Clear the Troll from Ulla's ice cave, east of the village.",
    done=q.when(flag=q.dead(*cave_foes)), reward=[A.flag("ulla_paid")],
    refusal="Then I'll sit by a cold forge and wait."))
q.near(*square_px(*cave_sq), 260, [A.print("Blue light, cold air, the stink of Troll: Ulla's ice cave.")])

# Asa's Sons
q.talker("Asa", q.errand(
    "Asa", "sons",
    offer="My boys, Arn and Bodvar. Gudrun sent them up the Keeper's Stair to fetch Orm down. That was yesterday "
          "morning.\n\nThey know that stair like their own doorstep. They should have been home by dark.\n\nIf you go "
          "up, kind stranger, look for them. Will you?",
    reminder="Find my boys, at whatever the cost. The stair is bad in the wind.",
    thanks="Both of them? ...Then my worst fears have come to pass.\n\nTake their father's bow. There's nobody left "
           "here to draw it. Good luck to you on the mountain.",
    after="Light a candle for them, if you pass a shrine.",
    objective="Discover the fate of Old Asa's sons on the Keeper's Stair.",
    done=q.when(flag="hunters_found"), reward=[A.give("Bow"), A.give("Quiver"), A.gold(40)],
    refusal="Then I'll go up myself, old as I am."))

for who_, pic_ in (("Liv", "MaidenPic2"), ("Gudrun", "MaidenPic3"), ("Ulla", "MaidenPic4"), ("Asa", "MaidenPic"),
                   ("VessYield", "MaidenPic6"), ("ValleyGuard", "Warrior2Pic"), ("Watch1", "Warrior3Pic")):
    q.portrait(who_, pic_)

mods.attach(sm.B)
m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())
m.scripts.update(hc.files(NAME))

# ---- 11. the exteriors' dressing ---------------------------------------------------------------------------------------
# the stair and the shrine take the ice's own pieces only (no carts or woodpiles up a glacier stair)
high_ = {s for s in land.squares for k_ in ("ledge1", "ledge2", "shrine")
         if math.hypot(s[0] - C[k_][0], s[1] - C[k_][1]) <= land.areas[k_]["r"] + 3}
dressed = Exterior(m, land, "ice", placed=placed, avoid=high_).dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed, os.path.join(OUT, f"{NAME}.rooms.json"))
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS", "VOICE"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| trees {n_trees} | shops {n_shops} | caches {len(caches)} | opened {len(opened)} | lines {len(q.strings)} "
          f"| dressing {sum(dressed.values())} groups")
