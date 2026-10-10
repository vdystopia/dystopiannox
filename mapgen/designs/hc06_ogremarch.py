"""The Hollow Choir, act 6: the Ogre Marches (OgreMarch). The road east from Thornkeep runs through the Marches, a
border land of oak and beech woods and pine hills that the ogres hold, to the barrow-lands beyond the March Gate
(campaign/hollowchoir/BIBLE.md; the act's place in the chain: mapgen/kit/campaign.py ACTS[5]). The green world in three
sections: the oak wood of the west road, the waystation and the Marlow farm (FORESTS["oak"]); the red beech wood of the
south-east where the raiders camp (FORESTS["dusk"]); the pine hills of the north where Gruthak's warband holds the
Tusk Hold, the trapper works and the wolves den (FORESTS["pine"], trodden earth). Two cultures: the travellers' and
farmers' ground of the waystation, and the ogres' (Westwood's ogre fires: a fire pit, benches and the take, middens
and cooking pits round their lair; the Hold furnished in the ogres' manner, rules/CULTURES.md).

The story
- The player comes in on the west road from Thornkeep, on the Choir's trail. Tull's Waystation stands where the
  roads cross: an inn, a farrier's forge and the ostlers' houses round a cobbled yard. It is full of travellers who
  cannot go on: Gruthak the Ogre Lord has barred the March Gate on the east road.
- Main quest, the Ogre Lord's toll (a camp with a sentry, a hall, a boss, the stone won back): Oswin Tull, master of
  the waystation, tells the player that the Hollow Choir came through a week ago with a covered cart; Gruthak let them
  by and they paid him with a red stone that hums like a struck bell (the fourth Spirit Stone): since then his
  ogres turn everyone else back, so nobody follows the Choir east. The player goes up the hill road past the warband's
  camp (a fire pit, a lookout who rouses the rest) to the Tusk Hold and kills Gruthak in his feasting
  hall (the Ogre Lord, M1, FOES["Gruthak"]). He falls with the Spirit Stone (SPIRIT_STONE, dropped where he dies: one
  stone, one death), the March Gate's bar is his to lift: his ogres leave the gate and it opens. His hoard holds the
  Chakram Storm (W2). Tull pays when the player comes back.
- Rusk's parley (choice A read: RUSK_KNIFE). If the player freed Rusk in Brackwater and carries his lucky charm, Rusk
  waits by the hill road: he ran east from the Choir, and he knows these ogres (he carried the Choir's silver up the
  hill once). Ogres keep an old law: a chief challenged one against one fights alone while his warband stands back to
  watch. If the player says yes, Rusk carries the challenge: the warband (the camp, the Hold's keepers and the gate's
  grunts) stands aside, frozen at their posts (kit/hc_standaside.py), and Gruthak duels the player alone in his hall.
  Strike one of the warband and the parley is broken: they all fall on the player. Without the charm Rusk is not
  here (he is in Captain Ilsa's cells) and the player fights through the warband to Gruthak.
- Side quest, the Marlow farm (a rescue, the rescued walks home): ogres from the red beech wood raid the Marlow farm
  south of the waystation for its pigs. Jory the farmhand went after them with a pitchfork and never came home:
  Goodwife Marlow asks the player to find him and kill the raiders. Jory is hiding in the old March tower by the
  raiders' camp; with the raiders dead he walks home along the paths and the goodwife pays.
- Side quest, the black wolf (a bounty): Fenn the trapper, at his hut in the north-west pines, pays a bounty on the
  black wolf whose pack dens in the rocks north of his hut and robs his snares.
- The inn and the farrier buy and sell; the Hold's hoard, the raiders' take, the old tower's chest, caches in the
  woods and the houses' stores hold loot; every traveller at the waystation knows something.
- The exit: the east road beyond the March Gate leads to the Ashen Barrow (act 7).

Tokens: reads RUSK_KNIFE (Rusk and his parley); gives SPIRIT_STONE (Gruthak's, dropped once where he dies).

    py mapgen/designs/hc06_ogremarch.py [seed]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import Land, square_tile, square_px, px_square, bfs_distance
from kit.vegetation import Planter, FORESTS, TOWN_PLANTING
from kit.village import Village
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT
from kit import yards as Y
from kit import camps
from kit.story import StoryMap
from kit.posts import camp_posts
from kit.dressing import Exterior
from kit.mods import Mods
from kit.campaign import act, token, has, cast_person, voice, exit_next, FOES
from kit.hc_standaside import StandAside

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7
rng = random.Random(SEED)
ACT = act(6)
NAME = ACT["map"]                      # OgreMarch
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", ACT["design"])
STONE = token("SPIRIT_STONE")          # the fourth Spirit Stone (the campaign's counted token)
KNIFE = token("RUSK_KNIFE")            # Rusk's lucky charm: he was freed in Brackwater

# Warnings accepted, each with its reason (tests/qa.py)
QA_ACCEPT = [
    ("composition", r"is sparse: furniture covers",
     "the kit's furnisher (generate_building + furnish_original at master 2026-10-09) leaves small house rooms, the "
     "inn's big common room and the ogres' feasting hall under the half-median house rule on every map (Ironcrag "
     "accepts the same); the room lab's work, not this act's. The feasting hall's floor is the duel ground"),
    ("composition", r"bunched into one part of the room \(offset 0\.8",
     "a small bedroom of a kit house, a little over the line; the room picture reads as a bedroom"),
    ("density", r"^Many share of floor seams with edge pieces",
     "every open seam blended, as the kit always blends them; the seams at walls are hard by rule (TW-12)"),
]


def uv(X, Y):
    """uv of a point given in map cells as seen on screen (X right, Y down, 0..255)."""
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="a border land of oak and beech woods and pine hills on the road east: Tull's Waystation where the roads "
          "cross, full of travellers who cannot go on; the Marlow farm south of it, raided by ogres from the red "
          "beech wood; the trapper's hut and the wolves' den in the north-west pines; the warband's camp and the Tusk "
          "Hold of Gruthak the Ogre Lord in the northern hills; the March Gate barred on the east road",
    environment="town", mood="wild, uneasy, held",
    areas=[AreaIdentity("west", "the west road in from Thornkeep: the start"),
           AreaIdentity("town", "Tull's Waystation: the cobbled yard round its well, the inn and the farrier",
                        landmark="Well"),
           AreaIdentity("farm", "the Marlow farm and its barley, raided by ogres"),
           AreaIdentity("beech", "the red beech wood: the raiders' camp and the old March tower"),
           AreaIdentity("trap", "the trapper's hut at the edge of the north-west pines"),
           AreaIdentity("den", "the wolves' den in the rocks of the pines"),
           AreaIdentity("camp", "the warband's camp below the Hold: a fire pit and its lookouts"),
           AreaIdentity("hold", "the Tusk Hold, Gruthak's keep of old stone"),
           AreaIdentity("gate", "the March Gate on the east road, barred"),
           AreaIdentity("east", "the east road on to the barrow-lands: the way out")],
    buildings=[BuildingIdentity("inn", "town", "Tull's Waystation", "Oswin Tull and his potboy"),
               BuildingIdentity("smithy", "town", "the farrier's forge", "the farrier"),
               BuildingIdentity("home", "town", "", "the ostler's family"),
               BuildingIdentity("cottage", "town", "", "a drover's widow"),
               BuildingIdentity("home", "farm", "the Marlow farm", "Goodwife Marlow and Jory her farmhand"),
               BuildingIdentity("woodcutter", "trap", "the trapper's hut", "Fenn the trapper"),
               BuildingIdentity("ogre_keep", "hold", "the Tusk Hold", "Gruthak the Ogre Lord and his warband")])

m = Spec(NAME, summary=ACT["title"], description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"The Hollow Choir, act 6. Generated by Claude.", author="vdystopia (generated by Claude)", version="1",
         date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [150, 146, 128]           # a grey-gold afternoon in the hills
q = QuestBook(NAME)

# sections: each its own forest (walls, trees, undergrowth) and ground (base, sparse, dense)
REGIONS = dict(
    oak=dict(forest="oak", ground=("GrassNorm", "GrassSparse2", "GrassDense")),
    beech=dict(forest="dusk", ground=("GrassNorm", "GrassSparse2", "GrassDense")),
    hills=dict(forest="pine", ground=("GrassSparse2", "DirtDark2", "GrassNorm")),
)
SECTION = {"west": "oak", "town": "oak", "farm": "oak", "gate": "oak", "east": "oak", "beech": "beech",
           "trap": "hills", "den": "hills", "camp": "hills", "hold": "hills"}


def section(r):
    """The section of a region name: an area's own, or a passage's side pocket's (pocket_<a>_<b>_<k>), its first end's."""
    if r in REGIONS: return r
    for part in (r or "").split("_")[1:]:
        if part in SECTION: return SECTION[part]
    return "oak"


# ---- 1. the plan: the west road to the waystation, the east road through the March Gate, the hill road to the Hold --
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"west": ((26, 132), 14), "town": ((88, 130), 52), "farm": ((96, 200), 30), "beech": ((168, 212), 26),
         "trap": ((52, 66), 18), "den": ((32, 30), 14), "camp": ((146, 78), 28), "hold": ((182, 36), 34),
         "gate": ((182, 132), 12), "east": ((230, 126), 12)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "town", region=SECTION[k_])
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_, bend_ in (("west", "town", 14, True, 0.15), ("town", "gate", 13, True, 0.15),
                                 ("gate", "east", 12, True, 0.12), ("town", "camp", 13, True, 0.18),
                                 ("camp", "hold", 12, True, 0.15), ("town", "trap", 12, True, 0.2),
                                 ("trap", "den", 9, False, 0.28), ("town", "farm", 12, True, 0.18),
                                 ("farm", "beech", 10, False, 0.25)):
    land.link(a_, b_, w_, bend=bend_, road=road_, pockets=(1, 2) if road_ else (0, 1))
land.blends(m)

# ---- 2. the centre: the waystation's cobbled yard round its well, the roads leaving it -------------------------------
vc = land.areas["town"]["c"]
land.paint_square(m, "town", 10, "RoughCobble")
land.taken |= {(int(vc[0]) + a, int(vc[1]) + 1 + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}
hold_c0 = land.areas["hold"]["c"]                  # the ogres' track stops short of the Hold's door
land.paint_roads(m, "DirtDark2", width_squares=2.8,
                 skip=land.reserved | {(i, j) for i in range(int(hold_c0[0]) - 16, int(hold_c0[0]) + 17)
                                       for j in range(int(hold_c0[1]) - 16, int(hold_c0[1]) + 17)
                                       if math.hypot(i - hold_c0[0], j - hold_c0[1]) < 13})

# ---- 3. buildings from the yard outwards; none on the wild places -------------------------------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"west": 8, "beech": 13, "den": 9, "camp": 19, "gate": 6},
                            first=("farm", "trap"), centred={"hold": "camp"})
by_role = sm.by_role
sm.connect_and_furnish(path_material="DirtDark2")


def ring_of(c, radii):
    return [(c[0] + r * math.cos(a * math.pi / 6), c[1] + r * math.sin(a * math.pi / 6)) for r in radii for a in range(12)]


# the yards: the Marlows' barley and their second field by the farm
yards = []
wild_ = [land.areas[k]["c"] for k in ("beech", "camp", "den")]
for kind_, area_, rs_, toward_ in (("field", "farm", (8, 11, 14), "farm"), ("field", "farm", (10, 13, 16, 19), "farm")):
    cands_ = [p for p in ring_of(land.areas[area_]["c"], rs_)
              if all(math.hypot(p[0] - w[0], p[1] - w[1]) > 22 for w in wild_)]     # the fields keep off the foes'
    y_ = Y.plan_any(land, rng, kind_, cands_, toward=land.areas[toward_]["c"])      # ground
    if y_: yards.append(y_)
    else: print(f"no room for the {kind_} by the {area_}")
barley = next((y_ for y_ in yards if y_.kind == "field"), None)

# ---- 4. the land grows round everything, ending in the forest wall ---------------------------------------------------
land.carve(margin=3.5)
lane_ = sm.keep_open({"west": 4, "beech": 9, "den": 6, "camp": 12, "trap": 4, "gate": 3, "east": 3})
land.assign_regions()
# the hills' glade below the Hold stays open (a glade full of small copses is a saw of forest edges that the OpenNox
# client cannot draw: tests/sightrows.py, CL-1)
hills_open = {s for s in land.squares for k_, r_ in (("camp", 24), ("beech", 18)) if
              math.hypot(s[0] - land.areas[k_]["c"][0], s[1] - land.areas[k_]["c"][1]) < r_}
clumps = land.thickets(200, size=(0.9, 1.8), clear=1, avoid=frozenset((lane_ | hills_open) & land.squares))
clumps += land.thickets(70, size=(0.6, 1.1), clear=1, avoid=frozenset((lane_ | hills_open) & land.squares))   # copses
land.open_links()
land.region_map = {s_: section(r_) for s_, r_ in land.region_map.items()}
land.apply(m, wall=lambda r: FORESTS[REGIONS[r]["forest"]]["wall"], floor=lambda r: REGIONS[r]["ground"][0],
           unlevel=True)
built = []
for y_ in yards:
    if not y_.plot <= land.squares:
        print(f"the {y_.kind} lies off the land"); continue
    Y.build(m, rng, land, y_)
    built.append(y_)

# the March Gate: the old border wall of grey stone across the east road, its gate barred from the ogres' side
gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "east"), prefix="MarchGate", material="StoneGray")

# ---- 5. the waystation's life ---------------------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("Tull's Waystation\nBeds, stew and stabling", "Sign"),
                     smithy=q.text("Farrier\nShoes, nails and blades", "Sign"))
for bid, b in placed:
    role = BUILDINGS[bid.role]
    for sc in role["scenes"]: vil.scene(b, sc, role=bid.role)
    if rng.random() < role["garden"]: vil.garden(b, size=(rng.randint(3, 5), rng.randint(2, 4)))
well_xy = square_px(vc[0] + 0.5, vc[1] - 0.5)
m.obj_px("Well", *well_xy)


def pole(si, sj):
    x, y = square_px(si, sj)
    m.obj_px("TorchPole", x, y)


vil.square_piece((vc[0] + 0.5, vc[1] - 0.5), 4, pole=pole, per_side=1)
for r_ in REGIONS:
    g_ = REGIONS[r_]["ground"]
    land.ground_variety(m, base=g_[0], sparse=g_[1], dense=g_[2], clear=3, region=r_)

# ---- 6. the story's places ------------------------------------------------------------------------------------------
presets = json.load(open(os.path.join(HERE, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]


def preset(family):
    return max((p for p in presets if p["family"] == family and p["animation"] == "steady" and p["intensity_class"] == "full"),
               key=lambda p: p["weighted_share"])["xfer"]


C = {k: land.areas[k]["c"] for k in AREAS}
west_c, farm_c, beech_c, trap_c, den_c, camp_c, hold_c, gate_c, east_c = (
    C[k] for k in ("west", "farm", "beech", "trap", "den", "camp", "hold", "gate", "east"))
fenced = set().union(*({(y_.gi + a, y_.gj + b) for a in range(-2, y_.w + 2) for b in range(-2, y_.h + 2)}
                       for y_ in yards)) if yards else set()


def off_road(c, clear=4.5, reach=12):
    """The square nearest `c` with no road within `clear` squares, on open land: a place beside its way, not on it."""
    near_road = bfs_distance(list(land.roads), land.squares, int(clear) + 1)
    cands = [s for s in land.squares if near_road.get(s, 99) >= clear and s not in land.taken_strict and
             s not in fenced and s not in land.water and math.hypot(s[0] - c[0], s[1] - c[1]) <= reach]
    s = min(cands, key=lambda s: math.hypot(s[0] - c[0], s[1] - c[1])) if cands else (int(c[0]), int(c[1]))
    return (s[0] + 0.5, s[1] - 0.5)


# the old March tower in the red beech wood, broken open toward the path from the farm: where Jory hides
tw_c = off_road((beech_c[0] - 4, beech_c[1] + 3), clear=4.0, reach=9)
tower = camps.ruined_tower(m, rng, land, tw_c, farm_c, loot=[("Gold", {"Amount": 30}), "RedPotion", "Quiver"],
                           size=(7, 7))
tower_sq = {(int(tw_c[0]) + a, int(tw_c[1]) + b) for a in range(-6, 7) for b in range(-6, 7)}
# the raiders' camp beside it, open toward the path
raid_site = camps.camp_site(m, land, (beech_c[0] + 4, beech_c[1] - 3), reach=12, road_clear=2.5, room=8,
                            avoid=fenced | tower_sq)
raid_way = sm.road_near(raid_site)
raiders_camp = camps.ogre_camp(m, rng, land, raid_site, raid_way,
                               loot=[("Gold", {"Amount": 50}), "RedPotion", "Meat", "Meat"], sleepers=3)
# the warband's camp below the Hold, where it has room beside the hill road, open toward the waystation
war_site = camps.camp_site(m, land, camp_c, reach=14, road_clear=3.5, room=9, avoid=fenced)
war_way = sm.road_near(war_site)
warcamp = camps.ogre_camp(m, rng, land, war_site, war_way,
                          loot=[("Gold", {"Amount": 80}), "RedPotion", "RedPotion", "Meat", "LeatherHelm"], sleepers=4)
# the fires' glow: the ogres' fire pits, the waystation's yard, the Hold's door, the farm and the trapper's hut
# (Westwood's towns carry about 0.3 coloured lights per 100 floor tiles)
for (lx_, ly_), fam_ in ((warcamp["fire"], "orange"), (raiders_camp["fire"], "orange"),
                         (square_px(vc[0] + 2.5, vc[1] - 2.5), "yellow"), (square_px(vc[0] - 3.5, vc[1] + 2.5), "yellow"),
                         (square_px(hold_c[0] - 6, hold_c[1] + 6), "orange"), (square_px(farm_c[0], farm_c[1]), "yellow"),
                         (square_px(trap_c[0], trap_c[1]), "yellow"), (square_px(gate_c[0], gate_c[1]), "orange"),
                         (square_px(west_c[0], west_c[1]), "white"), (square_px(east_c[0], east_c[1]), "white")):
    m.obj_px("ColorLight", lx_, ly_ - 6, xfer=dict(preset(fam_)))
# the wolves' den in the rocks of the pines, its mouth toward the trapper's path
den_at = off_road(den_c, clear=3.0, reach=8)
camps.wolf_den(m, rng, land, den_at, trap_c)
a_den = math.atan2(trap_c[1] - den_at[1], trap_c[0] - den_at[0])       # the den's mouth, toward the trapper's path
den_spots = [square_px(den_at[0] + r * math.cos(a_den + d), den_at[1] + r * math.sin(a_den + d))   # the pack lies up
             for r, d in ((2.5, 0.0), (3.4, 1.0), (3.1, -1.05), (4.4, 0.4), (4.2, -0.5), (2.9, 2.0))]  # spread about it
# caches in the woods, off the ways
caches = []
for near_, loot_, stump_ in ((den_c, [("Gold", {"Amount": 40}), "CurePoisonPotion", "RedPotion"], True),
                             (beech_c, [("Gold", {"Amount": 45}), "LeatherBoots", "BluePotion"], False),
                             (west_c, [("Gold", {"Amount": 30}), "RedPotion", "Quiver"], True)):
    s_ = sm.hidden_spot(near_, r=(8, 16))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
# signposts
camps.signpost(m, land, (west_c[0] + 2.5, west_c[1] - 1.5),
               q.text("TULL'S WAYSTATION\nEast. Beds and stabling.\nThornkeep: west.", "Sign"))
gs_ = sm.road_near(((gate_sq[0] * 2 + vc[0]) / 3, (gate_sq[1] * 2 + vc[1]) / 3))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 1.5),
               q.text("THE MARCH GATE\nToll by order of Gruthak.\nNo toll taken. Turn back.", "Sign"))
hr_ = sm.road_near(((camp_c[0] + vc[0]) / 2, (camp_c[1] + vc[1]) / 2))
camps.signpost(m, land, (hr_[0] + 2.0, hr_[1] - 1.5), q.text("THE HILL ROAD\nOgres. Go back.", "Sign"))
fr_ = sm.road_near(((farm_c[0] + vc[0]) / 2, (farm_c[1] + vc[1]) / 2))
camps.signpost(m, land, (fr_[0] + 2.0, fr_[1] - 1.5), q.text("MARLOW FARM\nEggs and milk.", "Sign"))

# ---- 7. planting and the start ----------------------------------------------------------------------------------------
keep = set()
for bid, b in placed:
    for d in b.entrances:
        di, dj = px_square(*d.px)
        keep |= {(di + a, dj + b2) for a in range(-2, 3) for b2 in range(-2, 3)}
vil.ground_bits(1.4)
planter = Planter(m, rng, land, "oak", keep_clear=keep | lane_, settled=("town", "farm"),
                  forest_of=lambda s: REGIONS[section(land.region_of(s))]["forest"])
n_trees, n_small = planter.plant_all(groves=4, profile=TOWN_PLANTING)
piles = planter.rock_piles(max(4, len(land.squares) // 900))
vignettes = planter.forest_floor(max(6, len(land.squares) // 700))
start_xy = square_px(west_c[0] + 0.5, west_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
exits = exit_next(sm, "east", 6, prefix="EastExit")

# ---- 8. the people --------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
person, room_of, free_px = sm.person, sm.room_of, sm.free_px
vx, vy = square_px(*vc)
bld = {bid.occupant: b for bid, b in placed}
# Oswin Tull at his waystation's door, looking down the east road
tb_ = bld.get("Oswin Tull and his potboy")
tull_ = (sm.doorside(building=tb_, toward=square_px(*gate_c)) if tb_ else None) or (vx + 60, vy)
person("Con03B", "Garrit", tull_[0], tull_[1], "Tull", face=square_px(*gate_c))
# Goodwife Marlow at her farmhouse door, looking toward the beech wood
mb_ = bld.get("Goodwife Marlow and Jory her farmhand")
marl_ = (sm.doorside(building=mb_, toward=square_px(*beech_c)) if mb_ else None) or square_px(*farm_c)
person("Con02a", "Joyce", marl_[0], marl_[1], "Marlow", face=square_px(*beech_c))
jory_door = (sm.outside_door(building=mb_) if mb_ else None) or marl_
# Fenn the trapper at his hut's door, looking up toward the den
fb_ = bld.get("Fenn the trapper")
fenn_ = (sm.doorside(building=fb_, toward=square_px(*den_c)) if fb_ else None) or square_px(*trap_c)
person("Con03A", "Osborn", fenn_[0], fenn_[1], "Fenn", face=square_px(*den_c))
# Jory hiding in the old March tower, at its back, watching the way in
jx_, jy_ = tower["boss"]
person("War01A", "Jesse", jx_, jy_, "Jory", face=square_px(*farm_c))
jory_home = sm.journey("Jory", "JoryHome", jory_door, look=square_px(*beech_c))
# Rusk, if he was freed in Brackwater: by the hill road, a bowshot below the warband's camp, looking up at it
rk_t = ((camp_c[0] * 11 + vc[0] * 9) / 20, (camp_c[1] * 11 + vc[1] * 9) / 20)    # half way up the hill road
near_road_ = bfs_distance(list(land.roads), land.squares, 4)
in_clump = set().union(*clumps) if clumps else set()


def open_ground(s, r=2):
    """A square of open ground: no wall (the forest's or a copse's) within r cells of its middle."""
    x, y = square_px(s[0] + 0.5, s[1] - 0.5)
    cx, cy = int(x // CELL), int(y // CELL)
    return not any((cx + a, cy + b) in m.wallmap for a in range(-r, r + 1) for b in range(-r, r + 1))


rk_s = min((s for s in land.squares if s not in land.taken_strict and s not in fenced and s not in in_clump and
            open_ground(s, 2) and 2 <= near_road_.get(s, 99) <= 4 and math.hypot(s[0] - rk_t[0], s[1] - rk_t[1]) <= 14),
           key=lambda s: math.hypot(s[0] - rk_t[0], s[1] - rk_t[1]), default=None)
rk_ = (rk_s[0] + 0.5, rk_s[1] - 0.5) if rk_s else off_road(rk_t, clear=2.5, reach=10)
rusk_xy = square_px(*rk_)
cast_person(sm, "Rusk", *rusk_xy, face=square_px(*camp_c))
# shopkeepers
WARES = {"inn": [(6, "Bread"), (5, "RedApple"), (5, "Meat"), (4, "Cider"), (3, "RedPotion"), (2, "BluePotion"),
                 (2, "CurePoisonPotion")],
         "smithy": [(2, "Sword"), (1, "Longsword"), (1, "BattleAxe"), (1, "WarHammer"), (1, "WoodenShield"),
                    (1, "SteelShield"), (1, "ChainCoif"), (1, "ChainTunic"), (1, "ChainLeggings"), (2, "Quiver"),
                    (1, "Bow")]}
GREET = {"inn": q.text("Stew's hot and the beds are dry! Not many inns between here and the barrow-lands. None, in "
                       "fact.", "Shop"),
         "smithy": q.text("Horseshoes or blades? I do both, but the blades cost more.", "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"smithy": "ShopkeeperWarriorsRealm"})
# the travellers stranded at the waystation, each with something to tell
for c_, r_ in ((camp_c, 20), (hold_c, 16), (beech_c, 14), (den_c, 12), (gate_c, 9), (rk_, 5), (trap_c, 6)):
    sm.keep_folk_away(c_, r_)                                       # folk keep off foes' ground
FOLK = [("Con02a", "Tanya"), ("Con02a", "Clyde"), ("Con07B", "Dorian"), ("Con06a", "Townsman2"), ("Con07B", "Kayla")]
RUMOURS = [
    "Talk to Tull, by the inn door. Nobody knows the Marches better.",
    "I wonder where an Ogre buys his boots? Nobody's that size.",
    "My wife says not to talk to sellswords.",
    "Going east? Nobody's going east. Not past the March Gate.",
    "Goodwife Marlow at the farm is looking for her farmhand. Jory, I think.",
]
ring = sm.townsfolk(FOLK, vc, q=q, rumours=RUMOURS,
                    after=("gate_open", "They say the Ogre Lord is dead! The road east is open, for those mad "
                                        "enough to take it."),
                    pics=("MaidenPic3", "MalePic7", "MalePic11", "Townsman1Pic", "MaidenPic4"),
                    radius=6.0)
# the waystation's guard, on his beat round the yard
wx2, wy2 = ring[0]
person("Con02a", "IxGuard2", wx2, wy2, "Watch1", action=0)
sm.beat("Watch1", vc, radius=6.0, stops=6)

# ---- 9. the fights ----------------------------------------------------------------------------------------------------
mods = Mods(m, pop)
warband = []
# the warband's camp: the chief by the take, two at the fire, one by the bedding, two watching the way in
wposts = camp_posts(m, warcamp, square_px(*war_way), sit=2, tents=1, watch=2, work=0)
pop.creature("OgreBrute", *wposts["leader"], action="guard", face=square_px(*vc), scr="CampChief", aggr=0.83,
             HealthMultiplier=1.5)
camp_ogres = []
for k, (x, y) in enumerate(wposts["sit"] + wposts["tent"]):
    n = f"CampGrunt{k + 1}"
    pop.creature("GruntAxe", x, y, action="idle", face=warcamp["fire"], scr=n, aggr=0.83)
    camp_ogres.append(n)
for k, (x, y) in enumerate(wposts["watch"]):
    n = f"CampWatch{k + 1}"
    pop.creature("GruntAxe", x, y, action="guard", face=square_px(*vc), scr=n, aggr=0.83)
    camp_ogres.append(n)
B.sentry("CampWatch1", square_px(*vc), rouse=["CampChief"] + camp_ogres[:3], shout="Hoom! Little man come! Up!")
camp_ogres.append("CampChief")
warband += camp_ogres
# the Tusk Hold: the feasting hall, the den, the hoard; Gruthak at his feast
hold_b = sm.building_in("hold")
assert hold_b, "the Tusk Hold was not built"
hall = room_of("ogre_keep", "ogre_hall")
den_r = room_of("ogre_keep", "ogre_den")
hoard = room_of("ogre_keep", "ogre_hoard")
assert hall and den_r and hoard, "the Tusk Hold's rooms were not built"
warband += sm.keepers(hall, ("OgreBrute", "GruntAxe", "GruntAxe"), "HallOgre")
warband += sm.keepers(den_r, ("GruntAxe", "OgreBrute"), "DenOgre")
warband += sm.keepers(hoard, ("GruntAxe",), "HoardOgre")
# two grunts keep the Hold's door, either side of the doorstep
kd_ = sm.outside_door(building=hold_b)
if kd_:
    kx_, ky_ = square_px(*hold_c)
    ux_, uy_ = kd_[0] - kx_, kd_[1] - ky_
    ul_ = math.hypot(ux_, uy_) or 1
    for k, s_ in enumerate((1, -1)):
        n = f"DoorOgre{k + 1}"
        pop.creature("GruntAxe", kd_[0] + ux_ / ul_ * 30 - uy_ / ul_ * 56 * s_, kd_[1] + uy_ / ul_ * 30 + ux_ / ul_ * 56 * s_,
                     action="guard", scr=n, aggr=0.83, face=square_px(*camp_c))
        warband.append(n)
# Gruthak the Ogre Lord (M1): frozen at his feast until the player comes near, then he hurls his chakrams
gx_, gy_ = free_px(hall, clear=34)
G = FOES["Gruthak"]
pop.creature("OgreWarlord", gx_, gy_, action="guard", face=kd_ or square_px(*camp_c), scr="Gruthak", aggr=0.83)
mods.monster_call("ogrelord", "Gruthak", G["title"], G["hp"], 230.0, 0.0)
# his hoard: the Chakram Storm (W2) and the Choir's silver in the hoard's chest
hoard_chest = None
for pad_ in (0, 1):                     # the chest the furnisher stood in the hoard: on its tiles first, then by its walls
    cells_ = {(x + a, y + b) for x, y in hoard.tiles for a in range(-pad_, pad_ + 1) for b in range(-pad_, pad_ + 1)}
    hoard_chest = next((o for o in m.d["objects"] if "Chest" in o.get("type", "") and "Sack" not in o.get("type", "")
                        and (int(o["x"] // CELL), int(o["y"] // CELL)) in cells_), None)
    if hoard_chest: break
hoard_loot = [mods.weapon_item("W2", name="ChakramStorm"), ("Gold", {"Amount": 150}), "RedPotion", "RedPotion"]
if hoard_chest:
    hoard_chest["items"] = m.items_at(hoard_loot, hoard_chest["x"], hoard_chest["y"])
else:
    hx_, hy_ = free_px(hoard, clear=30)
    hoard_chest = m.obj_px("Chest3", hx_, hy_, items=hoard_loot)
# the March Gate's keepers, on the waystation side of the gate
gq_ = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
gdx, gdy = vx - gq_[0], vy - gq_[1]
gl = math.hypot(gdx, gdy) or 1
gate_ogres = []
for k, s_ in enumerate((1, -1)):
    n = f"GateOgre{k + 1}"
    pop.creature("GruntAxe", gq_[0] + 80 * gdx / gl - 50 * gdy / gl * s_, gq_[1] + 80 * gdy / gl + 50 * gdx / gl * s_,
                 action="guard", scr=n, aggr=0.83, face=(vx, vy))
    gate_ogres.append(n)
warband += gate_ogres
# the raiders in the red beech wood: their leader by the take, the rest about their fire and the tower
rposts = camp_posts(m, raiders_camp, square_px(*raid_way), sit=2, tents=1, watch=1, work=0)
pop.creature("OgreBrute", *rposts["leader"], action="guard", face=square_px(*farm_c), scr="RaidChief", aggr=0.83)
raiders = ["RaidChief"]
for k, (x, y) in enumerate(rposts["sit"] + rposts["tent"] + rposts["watch"]):
    n = f"Raider{k + 1}"
    pop.creature("GruntAxe", x, y, action="idle" if k < 2 else "guard", face=raiders_camp["fire"], scr=n, aggr=0.83)
    raiders.append(n)
# the wolves at their den, the black wolf at their head
wolves = []
for k, (x, y) in enumerate(den_spots):
    n = "PackLeader" if k == 0 else f"DenWolf{k}"
    pop.creature("BlackWolf" if k == 0 else "Wolf", x, y, action="guard", scr=n, aggr=0.83, face=square_px(*trap_c))
    wolves.append(n)
B.pack(wolves[0], wolves[1:])
# the woods' own creatures by the forest's edge
sm.wild({"Wolf": 2, "Bat": 3, "Bear": 1, "BlackBear": 1, "SmallSpider": 2, "Spider": 1}, away_from=vc, per100=0.5,
        gap=7, min_away=36, avoid=(west_c, farm_c, beech_c, trap_c, den_c, camp_c, hold_c, gate_c, east_c, rk_))

story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]] + \
           [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)

# ---- 10. the story ----------------------------------------------------------------------------------------------------
GATE = [A.unlock("MarchGate1"), A.unlock("MarchGate2")] + [A.enable(n) for n in exits]
q.start([A.lock("MarchGate1"), A.lock("MarchGate2"), A.disable("Rusk"), A.stage("began", 1)] +
        [A.disable(n) for n in exits] +
        [q.journal("Follow the Hollow Choir east through the Ogre Marches.", HINT)])
# Rusk is here only if the player freed him in Brackwater (he carries Rusk's lucky charm)
q.when_true(q.at("began", 1, has=KNIFE), [A.enable("Rusk")])
# the March Gate opens once Gruthak lies dead (read from the world: it holds after a saved game is loaded too)
q.when_true(q.at("began", 1, flag=q.dead("Gruthak")), GATE + [A.flag("gate_open")])

MAIN = "Kill Gruthak the Ogre Lord and win back the Spirit Stone."
q.on_death("Gruthak", [A.drop(STONE), A.drop("OgreAxe"), A.flag("gruthak_dead")] +
          [A.disable(n) for n in gate_ogres] + [                     # the gate's grunts run off into the hills
                       A.print("Gruthak crashes down among the bones of his feast. A red stone on a thong rolls "
                               "from his neck, humming."),
                       q.note("NOTE: Gruthak is dead. His ogres have left the March Gate, and the east road is open.")])
q.near(*warcamp["fire"], 330, [A.print("A fire pit, crude benches and the stink of roast meat: the warband's camp.")])
q.near(*square_px(*hold_c), 300, [A.print("The Tusk Hold. Its old stones are black with the ogres' smoke.")])

# Tull: the hook, the main quest and its reward
q.talker("Tull", [
    q.say("Safe roads, stranger. The barrow-lands are no place to linger.", when=q.when(flag="tull_paid"), who="Tull"),
    q.say("Gruthak dead! I heard the horns from the hill! The east road's open again!\n\nHere -- take this for your "
          "trouble, and food for the road. The Choir's cart went east, toward the barrow-lands. They won't be far "
          "ahead now.",
          when=q.when(flag=q.dead("Gruthak"), not_="tull_paid"),
          do=[A.flag("tull_paid"), A.gold(120), A.give("ChainTunic"), A.give("Bread", 2), A.give("RedPotion", 2),
              q.done(MAIN)], who="Tull"),
    q.say("That gate won't lift itself. Go on, up the hill road!", when=q.when(flag="tull_told"), who="Tull"),
    q.say("Nothing goes east any more, stranger. Gruthak, the Ogre Lord, has barred the March Gate.\n\nA week ago men "
          "of the Hollow Choir came through with a covered cart. Gruthak let them by. They paid him with a red stone "
          "that hums like a bell when he strikes it! Since then his Ogres turn everyone else back.\n\nHis Hold is up "
          "the hill road, north-east of here. Kill him and the gate is yours. The stone too, I expect.",
          do=[A.flag("tull_told"), A.stage("main", 1), q.journal(MAIN)], who="Tull")],
    voice={"desc": "A stout innkeeper in his fifties. Warm, husky, carrying voice, a broad Lancashire accent. "
                   "Speaks plainly and quickly.", "seed": 6061})

# Rusk's parley (RUSK_KNIFE)
aside = StandAside(q)
aside.group(warband, flag="parley", wake="The parley is broken! Gruthak's warband falls on you!",
            broken="parley_broken")
q.talker("Rusk", [
    q.say("Gruthak's dead?! Ha! I owe you twice now. Keep my lucky charm. I'll be seeing you, friend.",
          when=q.when(flag=q.dead("Gruthak")), who="Rusk"),
    q.say("You hit one of his lads! Now they're all after you, and there's nothing I can do about it!",
          when=q.when(flag="parley_broken"), who="Rusk"),
    q.say("It's done. Gruthak waits in his Hold, alone. Don't you swing at the others, mind, or the deal's off!",
          when=q.when(flag="parley"), who="Rusk"),
    q.say("Oi! Don't draw on me! It's Rusk, from Brackwater! You let me walk, remember?\n\nI kept my word. I'm "
          "finished with the Choir. But I know these Ogres. I carried the Choir's silver up that hill myself, back "
          "before it all went wrong.\n\nOgres keep an old law. Challenge the chief, one against one, and his warband "
          "stands back to watch. Shall I carry your challenge up to Gruthak?",
          ask=True, do=[A.flag("parley"),
                        A.print("Rusk cups his hands and bellows up the hill in the ogres' tongue. A horn answers "
                                "from the Hold."),
                        q.note("NOTE: According to Rusk, Gruthak's warband will stand aside for the duel -- "
                               "unless one of them is struck.")],
          else_=[q.tell("Rusk", "Your neck, not mine. I'll be here if you change your mind.")], who="Rusk")],
    voice=voice("Rusk"))

# Goodwife Marlow and Jory: the rescue
q.on_all_dead(raiders, [A.flag("raiders_dead"), A.print("The last raider falls among the beech roots.")])
q.talker("Marlow", q.errand(
    "Marlow", "jory",
    offer="Are you deaf, or just slow? Ogres, stranger! Ogres in the barley again!\n\nThey come out of the red beech "
          "wood every night for our pigs. Last night Jory, my farmhand, went after them with a pitchfork. He never "
          "came back!\n\nThe wood's south-east of the farm. Find Jory and kill those brutes, and I'll pay you well. "
          "Will you go?",
    reminder="Oh, why are you still here? Jory could be in a cooking pot!",
    thanks="Jory! Home, you great fool!\n\nYou're a hero, stranger. Here, take this. We were saving it for the "
           "winter, and it's gladly given.",
    after="Thanks again! The pigs sleep sound for once.",
    objective="Find Jory in the red beech wood and kill the Ogre raiders.",
    done=q.when(flag="jory_home"), reward=[A.gold(70), A.give("SteelShield"), A.give("RedPotion", 2)],
    refusal="Then I'll go myself, pitchfork and all."))
q.talker("Jory", [
    q.say("Go on ahead. I know the path.", when=q.when(flag="jory_home"), who="Jory"),
    q.say("You killed them all? Thank you! I'm going home before more come. I'll follow the path back to the farm.",
          when=q.when(flag=q.dead(*raiders)),
          do=[A.flag("jory_home"), A.walk("Jory", jory_home),
              A.print("Jory slips out of the old tower and down the path toward the farm.")], who="Jory"),
    q.say("Psst! Keep your voice down! They're still out there! I'm not coming down till they're dead!", who="Jory")])
q.near(*square_px(*tw_c), 260, [A.print("An old tower of the March, broken open. Something moves at the top of the "
                                        "rubble.")])

# Fenn's bounty on the black wolf
q.on_death("PackLeader", [A.flag("blackwolf_dead"), A.print("The black wolf is dead. Its pack scatters into the "
                                                            "pines.")])
q.talker("Fenn", q.errand(
    "Fenn", "wolf",
    offer="Hello there. You'll be after the bounty, I expect.\n\nThe black wolf of the north wood. Him and his pack "
          "have robbed my snares all spring. Last week they took a drover's mule off the road!\n\nThey den in the rocks "
          "north of my hut. Mind yourself up there. Will you hunt him?",
    reminder="The black wolf's still out there. I hear him every night.",
    thanks="Ha! That's him, all right! Biggest wolf I ever saw!\n\nMy snares are safe, and maybe my neck too. "
           "Here's your bounty -- 80 in gold, and my spare bow.",
    after="Good hunting, stranger!",
    objective="Hunt down the black wolf of the north wood.",
    done=q.when(flag=q.dead("PackLeader")), reward=[A.gold(80), A.give("Bow"), A.give("Quiver")],
    refusal="Suit yourself. The bounty keeps."))
q.near(*den_spots[0], 260, [A.print("Bones and fur in the rocks. The wolves' den.")])

# the waystation's guard
q.talker("Watch1", [
    q.say("The gate's open! Good riddance to the Ogres!", when=q.when(flag="gate_open"), who="Watch"),
    q.say("No brawling in the yard, and no drawn steel! Tull's rules.", who="Watch")])

for who_, pic_ in (("Tull", "Townsman3Pic"), ("Marlow", "MaidenPic6"), ("Jory", "MalePic10"), ("Fenn", "MalePic8"),
                   ("Rusk", "MalePic9"), ("Watch1", "IxGuard2Pic")):
    q.portrait(who_, pic_)

mods.attach(B)
m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())
m.scripts.update(aside.files(NAME))

# ---- 11. the exteriors' dressing: the waystation's and the ogres' scenes on the empty ground ---------------------------
dressed = Exterior(m, land, "green", placed=placed, culture=("farm", "ogre")).dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed, os.path.join(OUT, f"{NAME}.rooms.json"), yards=built)
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS", "VOICE"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| trees {n_trees} | shops {n_shops} | caches {len(caches)} | opened {len(opened)} | lines {len(q.strings)} "
          f"| yards {', '.join(y_.kind for y_ in built) or 'none'} | dressing {sum(dressed.values())} groups "
          f"| warband {len(warband)} | raiders {len(raiders)} | wolves {len(wolves)}")
    print("dressing:", dict(dressed))
