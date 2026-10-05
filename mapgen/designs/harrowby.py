"""Harrowby: a farming and milling town at harvest time in a green oak wood, and the story of Grukh's Tithe (a map of
its own, loadable directly; its west road leads to Thornwick, chapter one's map, mapgen/designs/thornwick.py). The
green world in four sections: the oak wood of the town, its fields and the south road (FORESTS["oak"], a new forest of
broad oaks, bracken and meadow flowers), the red autumn wood of the west, where the woodcutter works and the wolves
den (FORESTS["dusk"]), the old brown wood of Ashby in the east where the poachers camp (FORESTS["ancient"]) and the
pine hills of the north where the ogres hold the old hill-fort of Grimtusk (FORESTS["pine"], trodden earth). Two
cultures dress its ground: the farmers' (threshing floors, harvest wains, wind-mills by the fields) and the ogres'
(Westwood's ogre village, Con05B: a fire pit, straw bedding, tusk palisades and skull posts, middens and cooking pits
round their lair; the keep furnished in the ogres' manner, rules/CULTURES.md).

The story
- The player comes up the south road out of the oak wood at harvest time. Where the Hawkins' track leaves the road
  the harvest wain lies overturned, its sacks slit; three ogre grunts are still trampling the Hawkins' corn and come for
  whoever passes. Tobias the carter hid under his wain. He sends the player up to Harrowby: tell the reeve the ogres
  are on the south road now.
- Harrowby: a cobbled square round its well, the Moot Hall of Reeve Aldwin, the chapel of the Sheaf with its
  graveyard, the Golden Sheaf inn, Corbet's chandlery, the forge, the forester's house and the townsfolk's houses; the
  mill and its fields in the south-east; the woodcutter's hut in the red west wood; Ashby wood in the east; the pine
  hills and the hill-fort of Grimtusk in the north; the west gate on the road to Thornwick.
- Main quest, Grukh's Tithe (a camp with a sentry, a lair, a boss, proof brought home): for three weeks Grukh, the
  ogre warlord who took the old hill-fort of Grimtusk, has come down out of the pines to take a tithe of the harvest:
  grain, beasts, and anyone who stands in his way. His ogres hold the west road at night, so Reeve Aldwin has shut the
  west gate. The player passes the ogres' village before the fort (tusk palisades, a fire pit, a lookout who rouses
  the rest), fights through the keep's feasting hall and kills Grukh. His great axe, brought to the reeve, is proof:
  Aldwin pays, lights the harvest fire on the square and opens the west gate.
- The Wolves of the Red Wood (a beast to put down, with a reason): a pack has denned in the rocks of the west wood and
  mauled Osric the woodcutter's son. Osric, at his hut on the edge of the wood, pays when the pack and its black
  leader are dead.
- The Poachers of Ashby (a choice: the law or mercy): Forester Garrick wants the poachers in Ashby wood driven out and
  pays for it. Their leader, Tam, is a Harrowby man whose family's harvest the ogres took: he asks the player to carry
  his plea to the reeve instead. Refuse, and the poachers take up their bows; the forester pays. Carry the plea, and
  the reeve pardons them: Tam walks home to his mother's cottage and gives the player his bow; the forester grumbles,
  and pays a little for the trouble.
- The Reliquary (an heirloom from a guarded ruin): Sister Maud of the chapel of the Sheaf asks for the chapel's ankh,
  carried off by thieves a generation ago and hidden in the old watchtower in the south-west wood, where spiders nest.
  She pays in remedies, a charm and the chapel's alms.
- The chandlery, the forge and the inn buy and sell. The ogres' hoard, the poachers' take, the watchtower's chest,
  three caches in the woods and the houses' stores hold loot; every soul in town knows something.
- The exit: the west road beyond the west gate leads to Thornwick.

    py mapgen/designs/harrowby.py [seed]
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

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 3
rng = random.Random(SEED)
NAME = "Harrowby"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "harrowby")
NEXT_MAP = "Thornwick"                 # the west road runs on to Thornwick
AXE = "OgreAxe"                        # Grukh's great axe: the proof the reeve asks for
ANKH = "AnkhTradable"                  # the chapel of the Sheaf's reliquary ankh

# Warnings accepted, each with its reason (tests/qa.py)
QA_ACCEPT = []


def uv(X, Y):
    """uv of a point given in map squares as seen on screen (X right, Y down, 0..255)."""
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="a farming and milling town at harvest time in a green oak wood: a cobbled square round a well, the reeve's "
          "moot hall, the chapel of the Sheaf and its graveyard, an inn, a chandlery and a forge, the mill among its "
          "fields, a woodcutter's hut in the red west wood, poachers in Ashby wood to the east and the ogres of the "
          "hill-fort Grimtusk in the northern pines, who take a tithe of the harvest; the west gate shut on the road "
          "to Thornwick",
    environment="town", mood="golden, besieged, stubborn",
    areas=[AreaIdentity("south", "the south road out of the oak wood: the start"),
           AreaIdentity("steading", "the Hawkins' corn, trampled by ogres, where the harvest wain was overturned"),
           AreaIdentity("town", "Harrowby's square and its streets", landmark="Well"),
           AreaIdentity("mill", "the mill and its fields, the threshing floors"),
           AreaIdentity("wood", "the woodcutter's hut at the edge of the red west wood"),
           AreaIdentity("den", "the wolves' den in the rocks of the west wood"),
           AreaIdentity("tower", "the old watchtower in the south-west wood, where spiders nest"),
           AreaIdentity("ashby", "Ashby wood in the east and the poachers' camp"),
           AreaIdentity("foot", "the ogres' village below the hill-fort: tusk palisades and a fire pit"),
           AreaIdentity("fort", "Grimtusk, the old hill-fort the ogres took"),
           AreaIdentity("gate", "the west gate, shut"),
           AreaIdentity("west", "the west road on to Thornwick: the way out")],
    buildings=[BuildingIdentity("mill", "mill", "the mill", "Hamon the miller"),
               BuildingIdentity("home", "mill", "", "the Hawkins family"),
               BuildingIdentity("woodcutter", "wood", "Osric's hut", "Osric the woodcutter and his son"),
               BuildingIdentity("townhall", "town", "the Moot Hall", "Reeve Aldwin"),
               BuildingIdentity("village_chapel", "town", "the chapel of the Sheaf", "Sister Maud"),
               BuildingIdentity("inn", "town", "The Golden Sheaf", "the innkeeper"),
               BuildingIdentity("store", "town", "Corbet's chandlery", "Corbet the chandler"),
               BuildingIdentity("smithy", "town", "the forge", "the smith"),
               BuildingIdentity("home", "town", "the forester's house", "Forester Garrick"),
               BuildingIdentity("home", "town", "", "Tobias the carter's family"),
               BuildingIdentity("home", "town", "", "a reaper's family"),
               BuildingIdentity("cottage", "town", "Tam's cottage", "old Bess, Tam the poacher's mother"),
               BuildingIdentity("cottage", "town", "", "a gleaner widow"),
               BuildingIdentity("ogre_keep", "fort", "Grimtusk", "Grukh the warlord and his ogres")])

m = Spec(NAME, summary="Harrowby", description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"Generated by Claude.", author="vdystopia (generated by Claude)", version="1", date="2026", type=SOLO,
         minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [164, 150, 120]           # a warm harvest afternoon
q = QuestBook(NAME)

# sections: each its own forest (walls, trees, undergrowth) and ground (base, sparse, dense)
REGIONS = dict(
    oak=dict(forest="oak", ground=("GrassNorm", "GrassSparse2", "GrassDense")),
    red=dict(forest="dusk", ground=("GrassNorm", "GrassSparse2", "GrassDense")),
    ash=dict(forest="ancient", ground=("GrassDense", "GrassNorm", "GrassSparse2")),
    hills=dict(forest="pine", ground=("GrassSparse2", "DirtDark2", "GrassNorm")),
)
SECTION = {"south": "oak", "steading": "oak", "town": "oak", "mill": "oak", "gate": "oak", "west": "oak",
           "wood": "red", "den": "red", "tower": "red", "ashby": "ash", "foot": "hills", "fort": "hills"}


def section(r):
    """The section of a region name: an area's own, or a passage's side pocket's (pocket_<a>_<b>_<k>), its first end's."""
    if r in REGIONS: return r
    for part in (r or "").split("_")[1:]:
        if part in SECTION: return SECTION[part]
    return "oak"


# ---- 1. the plan: the south road up to the town, the west road out, the ways to the fields and the wild places --------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"south": ((128, 232), 14), "steading": ((88, 210), 16), "town": ((122, 140), 80), "mill": ((196, 192), 32),
         "wood": ((40, 150), 18), "den": ((36, 100), 16), "tower": ((44, 206), 16), "ashby": ((220, 120), 28),
         "foot": ((160, 70), 38), "fort": ((184, 34), 36), "gate": ((72, 78), 12), "west": ((32, 48), 12)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "town", region=SECTION[k_])
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_, bend_ in (("south", "town", 14, True, 0.18), ("south", "steading", 10, False, 0.25),
                                 ("town", "mill", 13, True, 0.15), ("town", "wood", 12, True, 0.2),
                                 ("wood", "den", 9, False, 0.28), ("steading", "tower", 9, False, 0.28),
                                 ("town", "ashby", 11, False, 0.24), ("town", "foot", 13, True, 0.18),
                                 ("foot", "fort", 12, True, 0.15), ("town", "gate", 13, True, 0.15),
                                 ("gate", "west", 12, True, 0.12)):
    land.link(a_, b_, w_, bend=bend_, road=road_, pockets=(1, 2) if road_ else (0, 1))
land.blends(m)

# ---- 2. the centre: the square round its well, the roads leaving it ----------------------------------------------------
vc = land.areas["town"]["c"]
land.paint_square(m, "town", 12, "RoughCobble")
land.taken |= {(int(vc[0]) + a, int(vc[1]) + 1 + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}
fort_c0 = land.areas["fort"]["c"]                  # the ogres' track stops short of the keep's door
land.paint_roads(m, "DirtDark2", width_squares=2.8,
                 skip=land.reserved | {(i, j) for i in range(int(fort_c0[0]) - 16, int(fort_c0[0]) + 17)
                                       for j in range(int(fort_c0[1]) - 16, int(fort_c0[1]) + 17)
                                       if math.hypot(i - fort_c0[0], j - fort_c0[1]) < 13})

# ---- 3. buildings from the square outwards; none on the wild places ---------------------------------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"south": 8, "steading": 11, "den": 10, "tower": 11, "ashby": 16, "foot": 19},
                            first=("mill", "wood"), centred={"fort": "foot"})
by_role = sm.by_role
sm.connect_and_furnish(path_material="DirtDark2")

# the yards: the Hawkins' corn by the south road, the mill's fields, the town's orchard and the chapel's graveyard
yards = []


def ring_of(c, radii):
    return [(c[0] + r * math.cos(a * math.pi / 6), c[1] + r * math.sin(a * math.pi / 6)) for r in radii for a in range(12)]


from kit.village import _squares_of
ch_sq = _squares_of(by_role["village_chapel"].footprint) if "village_chapel" in by_role else None
chapel_c = (sum(i for i, _ in ch_sq) / len(ch_sq), sum(j for _, j in ch_sq) / len(ch_sq)) if ch_sq else None
for kind_, area_, rs_, toward_ in (("field", "steading", (0, 3, 6), "south"), ("field", "mill", (9, 12, 15), "mill"),
                                   ("field", "mill", (10, 13, 16, 19), "mill"),
                                   ("orchard", "town", (22, 26, 30, 34), "town"),
                                   ("graveyard", "chapel", (10, 12, 14, 16, 18, 20, 24), "town"),
                                   ("field", "town", (30, 34, 38, 42, 46), "town")):
    near_c = chapel_c if area_ == "chapel" and chapel_c else land.areas["town" if area_ == "chapel" else area_]["c"]
    wild_ = [land.areas[k]["c"] for k in ("foot", "ashby", "steading")]       # the town's yards keep off the foes'
    cands_ = [p for p in ring_of(near_c, rs_) if kind_ != "field" or area_ != "town" or  # ground (a field had
              all(math.hypot(p[0] - w[0], p[1] - w[1]) > 24 for w in wild_)]          # hemmed the ogres' camp in)
    y_ = Y.plan_any(land, rng, kind_, cands_, toward=land.areas[toward_]["c"])
    if y_: yards.append(y_)
    else: print(f"no room for the {kind_} by the {area_}")
corn = next((y_ for y_ in yards if y_.kind == "field"), None)

# ---- 4. the land grows round everything, ending in the forest wall ---------------------------------------------------
land.carve(margin=3.5)
lane_ = sm.keep_open({"south": 4, "steading": 6, "den": 6, "tower": 7, "ashby": 10, "foot": 13, "wood": 4})
land.assign_regions()
clumps = land.thickets(240, size=(0.9, 1.8), clear=1, avoid=frozenset(lane_ & land.squares))
clumps += land.thickets(120, size=(0.6, 1.1), clear=1, avoid=frozenset(lane_ & land.squares))   # copses in the glades
land.open_links()
land.region_map = {s_: section(r_) for s_, r_ in land.region_map.items()}
land.apply(m, wall=lambda r: FORESTS[REGIONS[r]["forest"]]["wall"], floor=lambda r: REGIONS[r]["ground"][0])
built = []
for y_ in yards:
    if not y_.plot <= land.squares:
        print(f"the {y_.kind} lies off the land"); continue
    Y.build(m, rng, land, y_)
    built.append(y_)

# the west gate: a wall of grey stone across the road from forest to forest, a barred double gate in it
gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "west"), prefix="WestGate")

# ---- 5. the town's life ------------------------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Golden Sheaf\nAle, bread and a bed of clean straw", "Sign"),
                     store=q.text("Corbet's Chandlery\nRope, candles, seed and goods for the road", "Sign"),
                     smithy=q.text("The Forge\nBlades, mail, scythes ground sharp", "Sign"),
                     village_chapel=q.text("The Chapel of the Sheaf", "Sign"), townhall=q.text("The Moot Hall", "Sign"),
                     mill=q.text("Harrowby Mill\nYour grain ground for a tenth", "Sign"))
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
presets = json.load(open(os.path.join(HERE, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]


def preset(family):
    return max((p for p in presets if p["family"] == family and p["animation"] == "steady" and p["intensity_class"] == "full"),
               key=lambda p: p["weighted_share"])["xfer"]


C = {k: land.areas[k]["c"] for k in AREAS}
south_c, steading_c, mill_c, wood_c, den_c, tower_c, ashby_c, foot_c, fort_c, west_c = (
    C[k] for k in ("south", "steading", "mill", "wood", "den", "tower", "ashby", "foot", "fort", "west"))
fenced = set().union(*({(y_.gi + a, y_.gj + b) for a in range(-2, y_.w + 2) for b in range(-2, y_.h + 2)}
                       for y_ in yards))         # the yards and a margin round their fences


def off_road(c, clear=4.5, reach=12):
    """The square nearest `c` with no road within `clear` squares, on open land: a place beside its way, not on it."""
    near_road = bfs_distance(list(land.roads), land.squares, int(clear) + 1)
    cands = [s for s in land.squares if near_road.get(s, 99) >= clear and s not in land.taken_strict and
             s not in fenced and s not in land.water and math.hypot(s[0] - c[0], s[1] - c[1]) <= reach]
    s = min(cands, key=lambda s: math.hypot(s[0] - c[0], s[1] - c[1])) if cands else (int(c[0]), int(c[1]))
    return (s[0] + 0.5, s[1] - 0.5)


# the harvest fire on the square, dark until the ogres are beaten: a warm glow by the well
m.obj_px("ColorLight", well_xy[0] + 40, well_xy[1] + 20, xfer=dict(preset("orange")), scr="HarvestLight")
# the harvest wain overturned on the verge where the Hawkins' track leaves the south road
track = sm.road_near(((steading_c[0] + south_c[0] * 2) / 3, (steading_c[1] + south_c[1] * 2) / 3))
road_dir = math.atan2(vc[1] - south_c[1], vc[0] - south_c[0])
wsq = min((s for s in land.squares if s not in land.roads and s not in land.taken and s not in fenced and
           1.0 <= min(math.hypot(s[0] - r[0], s[1] - r[1]) for r in land.roads
                      if abs(r[0] - track[0]) + abs(r[1] - track[1]) < 12) <= 2.5),
          key=lambda s: math.hypot(s[0] - track[0], s[1] - track[1]))
wreck = camps.wagon_wreck(m, rng, land, (wsq[0] + 0.5, wsq[1] - 0.5), road_dir)
corn_c = corn.centre if corn and corn in built else steading_c
# the ogres' village below Grimtusk, where it has room beside the hill road, open toward the town road
ogre_site = camps.camp_site(m, land, foot_c, reach=14, road_clear=3.5, room=9, avoid=fenced)
ogre_way = sm.road_near(ogre_site)
ogres = camps.ogre_camp(m, rng, land, ogre_site, ogre_way,
                        loot=[("Gold", {"Amount": 90}), "RedPotion", "RedPotion", "Meat", "LeatherHelm"], sleepers=4)
# the poachers' camp in Ashby wood, open toward the path from the town
poach_site = camps.camp_site(m, land, ashby_c, reach=14, road_clear=3.0, room=8, avoid=fenced)
poach_way = sm.road_near(poach_site)
poachers_camp = camps.bandit_camp(m, rng, land, poach_site, poach_way,
                                  loot=[("Gold", {"Amount": 60}), "Quiver", "RedPotion", "Meat"],
                                  sleepers=4, tents=2, trade="bandit")
# the wolves' den in the rocks of the west wood, its mouth toward the woodcutter's path
den_spots = camps.wolf_den(m, rng, land, off_road(den_c, clear=3.0, reach=8), wood_c)
# the old watchtower in the south-west wood, broken open toward the path; the chapel's ankh in its chest
tw_c = off_road(tower_c, clear=5.5, reach=9)
tower = camps.ruined_tower(m, rng, land, tw_c, steading_c, loot=[ANKH, ("Gold", {"Amount": 35}), "BluePotion"],
                           size=(8, 8))
tsc = camps.Scene(m, rng, land, tw_c)
for k_ in range(5):
    tsc.put(rng.choice(("SpiderWebNorth", "SpiderWebEast", "SpiderWebNorthEast")), *tsc.at(5.4, k_ * 1.25 + 0.4))
# caches in the woods, off the ways
caches = []
for near_, loot_, stump_ in ((den_c, [("Gold", {"Amount": 45}), "CurePoisonPotion", "RedPotion"], True),
                             (ashby_c, [("Gold", {"Amount": 50}), "LeatherBoots", "BluePotion"], False),
                             (tower_c, [("Gold", {"Amount": 35}), "RedPotion", "Quiver"], False)):
    s_ = sm.hidden_spot(near_, r=(9, 16))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
# signposts
camps.signpost(m, land, (south_c[0] + 2.5, south_c[1] - 1.5),
               q.text("HARROWBY\nUp the road. Mill, market and moot.\nMind the harvest carts.", "Sign"))
gs_ = sm.road_near(((gate_sq[0] * 2 + vc[0]) / 3, (gate_sq[1] * 2 + vc[1]) / 3))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 1.5),
               q.text("THE WEST GATE IS SHUT\nOgres hold the west road by night.\n- Aldwin, Reeve of Harrowby", "Sign"))
fr_ = sm.road_near(((foot_c[0] + vc[0]) / 2, (foot_c[1] + vc[1]) / 2))
camps.signpost(m, land, (fr_[0] + 2.0, fr_[1] - 1.5), q.text("THE HILL ROAD\nGrimtusk. Turn back.", "Sign"))
mr_ = sm.road_near(((mill_c[0] + vc[0]) / 2, (mill_c[1] + vc[1]) / 2))
camps.signpost(m, land, (mr_[0] + 2.0, mr_[1] - 1.5), q.text("HARROWBY MILL\nAnd the south fields.", "Sign"))

# ---- 7. planting and the start ----------------------------------------------------------------------------------------
keep = set()
for bid, b in placed:
    for d in b.entrances:
        di, dj = px_square(*d.px)
        keep |= {(di + a, dj + b2) for a in range(-2, 3) for b2 in range(-2, 3)}
vil.ground_bits(1.4)
planter = Planter(m, rng, land, "oak", keep_clear=keep | lane_, settled=("town", "mill"),
                  forest_of=lambda s: REGIONS[section(land.region_of(s))]["forest"])
n_trees, n_small = planter.plant_all(groves=4, profile=TOWN_PLANTING)
piles = planter.rock_piles(max(4, len(land.squares) // 900))
vignettes = planter.forest_floor(max(6, len(land.squares) // 700))
start_xy = square_px(south_c[0] + 0.5, south_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
sm.exit_to("west", NEXT_MAP, prefix="WestExit")

# ---- 8. the people --------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
person, room_of, free_px = sm.person, sm.room_of, sm.free_px
vx, vy = square_px(*vc)
bld = {bid.occupant: b for bid, b in placed}
# Tobias the carter by his overturned wain
tx_, ty_ = wreck["carter"]
person("Con03A", "Millard", tx_, ty_, "Tobias", face=start_xy)
# Reeve Aldwin in the Moot Hall
gh = room_of("townhall", "great_hall")
ax_, ay_ = free_px(gh) if gh else (vx, vy)
person("Con02a", "Mayor_Theogrin", ax_, ay_, "Aldwin")
# Sister Maud beside her altar, off the aisle
ch = room_of("village_chapel", "chapel")
ch_cells = {(x + a, y + b) for x, y in ch.tiles for a in (-1, 0, 1) for b in (-1, 0, 1)} if ch else set()
ch_altar = next((o for o in m.d["objects"] if o.get("type", "").startswith("DunMirAltar") and
                 (int(o["x"] // CELL), int(o["y"] // CELL)) in ch_cells), None)
if ch_altar:
    ccx = sum(x for x, _ in ch.tiles) / len(ch.tiles) * CELL; ccy = sum(y for _, y in ch.tiles) / len(ch.tiles) * CELL
    dl_ = math.hypot(ccx - ch_altar["x"], ccy - ch_altar["y"]) or 1
    ux_, uy_ = (ccx - ch_altar["x"]) / dl_, (ccy - ch_altar["y"]) / dl_
    hx_, hy_ = free_px(ch, prefer=(ch_altar["x"] + ux_ * 40 - uy_ * 50, ch_altar["y"] + uy_ * 40 + ux_ * 50), clear=26)
else:
    hx_, hy_ = free_px(ch) if ch else (vx, vy + 40)
person("Con02a", "Gretchen", hx_, hy_, "Maud", face=(ccx, ccy) if ch_altar else None)
# Forester Garrick beside his door, looking east toward Ashby
gb_ = bld.get("Forester Garrick")
ga_ = (sm.doorside(building=gb_, toward=square_px(*ashby_c)) if gb_ else None) or (vx + 60, vy)
person("Con02a", "Contest_Guard", ga_[0], ga_[1], "Garrick", face=square_px(*ashby_c))
# Osric beside his hut's door, looking toward the den
ob_ = bld.get("Osric the woodcutter and his son")
os_ = (sm.doorside(building=ob_, toward=square_px(*den_c)) if ob_ else None) or square_px(*wood_c)
person("Con03A", "Osborn", os_[0], os_[1], "Osric", face=square_px(*den_c))
# Hamon the miller beside his door
mb_ = bld.get("Hamon the miller")
hm_ = (sm.doorside(building=mb_, toward=(vx, vy)) if mb_ else None) or square_px(*mill_c)
person("Con03A", "Kenneth", hm_[0], hm_[1], "Hamon", face=(vx, vy))
# old Bess at her cottage door: where Tam walks home to if he is pardoned
tb_ = bld.get("old Bess, Tam the poacher's mother")
bess_ = (sm.doorside(building=tb_, toward=(vx, vy)) if tb_ else None) or (vx - 60, vy + 40)
person("Con02a", "Joyce", bess_[0], bess_[1], "Bess", face=(vx, vy))
tam_door = (sm.outside_door(building=tb_) if tb_ else None) or bess_
# the gate guard, on the town side of the west gate
gq_ = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
gdx, gdy = vx - gq_[0], vy - gq_[1]
gl = math.hypot(gdx, gdy) or 1
person("Con02a", "Mayor's_Guard", gq_[0] + 70 * gdx / gl + 26, gq_[1] + 70 * gdy / gl, "GateGuard", face=(vx, vy))
# Tam's poachers at their posts in Ashby: Tam by his tent and the take, one at the fire, one by the tents, one watching
# the path; the fighter each turns into, hidden exactly on his spot
pposts = camp_posts(m, poachers_camp, square_px(*poach_way), sit=1, tents=1, watch=1, work=0)
poachers, poacher_foes = ["Tam"], ["TamFoe"]
person("Con03A", "Rastur", *pposts["leader"], "Tam", face=square_px(*poach_way))
pop.creature("Archer", *pposts["leader"], action="guard", scr="TamFoe", aggr=0.83, HealthMultiplier=2.0, spread=False)
for k, ((x, y), donor_, foe_) in enumerate(zip(pposts["sit"] + pposts["tent"] + pposts["watch"],
                                              (("War01A", "Jesse"), ("War01A", "Daniel"), ("War01A", "Eric")),
                                              ("Swordsman", "Swordsman", "Archer"))):
    n = f"Poacher{k + 1}"
    person(donor_[0], donor_[1], x, y, n, face=poachers_camp["fire"])
    pop.creature(foe_, x, y, action="guard", scr=f"PoacherFoe{k + 1}", aggr=0.83, spread=False)
    poachers.append(n); poacher_foes.append(f"PoacherFoe{k + 1}")
# Tam's walk home to his mother's door, if the reeve pardons him: laid along the paths once the map stands
tam_home = sm.journey("Tam", "TamHome", tam_door, look=(vx, vy))
# shopkeepers
WARES = {"store": [(4, "RedPotion"), (3, "BluePotion"), (2, "CurePoisonPotion"), (3, "RedApple"), (3, "Bread"),
                   (3, "Quiver"), (1, "Bow"), (1, "CrossBow"), (1, "LeatherBoots"), (1, "LeatherHelm"),
                   (1, "LeatherArmor"), (1, "LeatherLeggings")],
         "inn": [(6, "Bread"), (5, "RedApple"), (5, "Meat"), (4, "Cider"), (2, "RedPotion")],
         "smithy": [(2, "Sword"), (1, "Longsword"), (1, "BattleAxe"), (1, "MorningStar"), (1, "WoodenShield"),
                    (1, "SteelShield"), (1, "ChainCoif"), (1, "ChainTunic"), (1, "ChainLeggings"), (1, "SteelHelm")]}
GREET = {"store": q.text("Corbet's chandlery. Rope, candles, seed corn, and arrows; since the ogres came I sell more "
                         "arrows than seed.", "Shop"),
         "inn": q.text("Welcome to the Golden Sheaf. New bread, old ale, and the reaper's song every night whether "
                       "you want it or not.", "Shop"),
         "smithy": q.text("The forge. Sickles in the morning, swords in the afternoon. Ogres have changed the order.",
                          "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"smithy": "ShopkeeperWarriorsRealm"})
# townsfolk on their rounds, each with something to tell
FOLK = [("Con02a", "Tanya"), ("Con02a", "Clyde"), ("Con07B", "Shari"), ("Con02a", "Jacob"), ("Con07B", "Kayla"),
        ("Con06a", "Townsman2"), ("Con02a", "Lydia"), ("Con07B", "Dorian")]
RUMOURS = [
    "Three weeks the ogres have come down out of the pines. They take the grain off the carts and the carts too.",
    "The reeve's shut the west gate. Ogres on the west road by night; he lost two carters before he'd believe it.",
    "Grukh, they call the big one. He sits up in old Grimtusk on the hill and eats what we grow.",
    "Osric the woodcutter's boy was mauled by wolves in the red wood. Osric sits by his door with his axe across his knees.",
    "Tam Bessson's gone poaching in Ashby wood with three lads. The forester's spitting nails, but they've a winter to eat.",
    "Sister Maud still prays for the chapel's ankh. Thieves took it when I was a girl; hid it in the old watchtower, they say.",
    "Hamon at the mill won't grind past dusk. Says the ogres can smell flour.",
    "There's a harvest fire on the square every year when the last sheaf is in. Not this year, the reeve says. Not yet.",
]
for c_, r_ in ((foot_c, 18), (fort_c, 16), (ashby_c, 14), (den_c, 12), (tower_c, 11), (steading_c, 12), (south_c, 10),
               (track, 10)):
    sm.keep_folk_away(c_, r_)                                        # folk keep off foes' ground
ring = sm.townsfolk(FOLK, vc, q=q, rumours=RUMOURS,
                    after=("harvest_lit", "The harvest fire's lit! First time I've slept since the ogres came. The "
                                          "west gate's open too, if you're bound for Thornwick."),
                    pics=("MaidenPic3", "MalePic7", "MaidenPic4", "MalePic8", "MaidenPic2", "Townsman1Pic",
                          "IngridPic", "MalePic11"),
                    radius=7.0)
# the reeve's watch, each on a beat through the town
for k_, donor_ in enumerate(("IxGuard2", "Mayor's_Guard")):
    wx2, wy2 = ring[k_ * 4]
    person("Con02a", donor_, wx2, wy2, f"Watch{k_ + 1}", action=0)
    sm.beat(f"Watch{k_ + 1}", vc, radius=7.0, stops=7)

# ---- 9. the fights ----------------------------------------------------------------------------------------------------
# the ogre grunts trampling the Hawkins' corn, who come for whoever passes on the road
csc = camps.Scene(m, rng, land, corn_c)
grunts = []
for k, a in enumerate((0.5, 2.6, 4.6)):
    x, y = csc.px(2.2, a)
    n = f"CornGrunt{k + 1}"
    pop.creature("GruntAxe", x, y, action="idle", face=start_xy, scr=n, aggr=0.5, sight=110)
    grunts.append(n)
# the ogres' village: the chief by the take, two at the fire, one by the bedding, two watching the way in
oposts = camp_posts(m, ogres, square_px(*ogre_way), sit=2, tents=1, watch=2, work=0)
camp_ogres = []
pop.creature("OgreBrute", *oposts["leader"], action="guard", face=square_px(*vc), scr="OgreChief", aggr=0.83,
             HealthMultiplier=1.5)
for k, (x, y) in enumerate(oposts["sit"] + oposts["tent"]):
    n = f"CampGrunt{k + 1}"
    pop.creature("GruntAxe", x, y, action="idle", face=ogres["fire"], scr=n, aggr=0.83)
    camp_ogres.append(n)
for k, (x, y) in enumerate(oposts["watch"]):
    n = f"OgreWatch{k + 1}"
    pop.creature("GruntAxe", x, y, action="guard", face=square_px(*vc), scr=n, aggr=0.83)
    camp_ogres.append(n)
B.sentry("OgreWatch1", square_px(*vc), rouse=["OgreChief"] + camp_ogres[:3], shout="Hoom! Little men! Up!")
camp_ogres.append("OgreChief")
# Grimtusk: the ogres' feasting hall, their den and their hoard; Grukh at his feast
keep_b = sm.building_in("fort")
assert keep_b, "Grimtusk was not built"
hall = room_of("ogre_keep", "ogre_hall")
den_r = room_of("ogre_keep", "ogre_den")
hoard = room_of("ogre_keep", "ogre_hoard")
assert hall and den_r and hoard, "Grimtusk's rooms were not built"
hall_guard = sm.keepers(hall, ("OgreBrute", "GruntAxe", "GruntAxe"), "HallOgre")
den_guard = sm.keepers(den_r, ("GruntAxe", "OgreBrute"), "DenOgre")
hoard_guard = sm.keepers(hoard, ("GruntAxe",), "HoardOgre")
# two grunts keep Grimtusk's door, either side of the doorstep
kd_ = sm.outside_door(building=keep_b)
door_guard = []
if kd_:
    kx_, ky_ = square_px(*fort_c)
    ux_, uy_ = kd_[0] - kx_, kd_[1] - ky_
    ul_ = math.hypot(ux_, uy_) or 1
    for k, s_ in enumerate((1, -1)):
        n = f"DoorOgre{k + 1}"
        pop.creature("GruntAxe", kd_[0] + ux_ / ul_ * 30 - uy_ / ul_ * 56 * s_, kd_[1] + uy_ / ul_ * 30 + ux_ / ul_ * 56 * s_,
                     action="guard", scr=n, aggr=0.83, face=square_px(*foot_c))
        door_guard.append(n)
gx_, gy_ = free_px(hall, clear=30)
pop.creature("OgreWarlord", gx_, gy_, action="guard", scr="Grukh", aggr=0.83, HealthMultiplier=2.0)
# the wolves at their den
wolves = []
for k, (x, y) in enumerate(den_spots + [((den_spots[0][0] + den_spots[-1][0]) / 2 + 50 * math.cos(a_),
                                          (den_spots[0][1] + den_spots[-1][1]) / 2 + 50 * math.sin(a_)) for a_ in (0.6, 3.7)]):
    n = f"DenWolf{k + 1}"
    pop.creature("BlackWolf" if k == 0 else "Wolf", x, y, action="guard", scr=n, aggr=0.83, face=square_px(*wood_c))
    wolves.append(n)
# the spiders in and round the old watchtower
spiders = []
for k, (x, y) in enumerate(tower["inside"][:3] + [tsc.px(4.4, a) for a in (0.9, 2.2, 3.5, 4.9)]):
    n = f"TowerSpider{k + 1}"
    pop.creature("BlackWidow" if k == 0 else "Spider" if k % 2 else "SmallSpider", x, y, action="guard", scr=n,
                 aggr=0.83, face=square_px(*steading_c))
    spiders.append(n)
# the woods' own creatures by the forest's edge
sm.wild({"Wolf": 3, "Bat": 4, "Bear": 1, "BlackBear": 1, "SmallSpider": 3, "Urchin": 2}, away_from=vc, per100=0.6, gap=7, min_away=36,
        avoid=(south_c, steading_c, mill_c, wood_c, den_c, tower_c, ashby_c, foot_c, fort_c, west_c, gate_sq))

story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]] + \
           [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)

# ---- 10. the story ----------------------------------------------------------------------------------------------------
q.start([A.lock("WestGate1"), A.lock("WestGate2"), A.disable("WestExit1"), A.disable("WestExit2"),
         A.disable("WestExit3"), A.disable("HarvestLight")] + [A.disable(n) for n in poacher_foes] +
        [q.journal("The south road climbs out of a green oak wood toward Harrowby, a town of millers and farmers. It "
                   "should be harvest time.", HINT)])

# the Hawkins' corn: the grunts come for whoever passes on the road
cx3, cy3 = square_px(*track)
q.near(cx3, cy3, 190, [A.hunt(n) for n in grunts] + [A.print("Something huge straightens up in the trampled corn. "
                                                             "Ogres!")])
q.on_all_dead(grunts, [A.flag("corn_clear"), A.print("The last grunt falls among the broken stalks.")])
q.talker("Tobias", [
    q.say("They're dead? All three? Then I'll right the wain and save what grain they left. Here, take these, and "
          "what's in my purse. Go on up to Harrowby.", when=q.when(flag=q.dead(*grunts), not_="tobias_paid"),
          do=[A.flag("tobias_paid"), A.give("RedPotion", 2), A.gold(25),
              q.journal("I killed the ogre grunts in the Hawkins' corn. Tobias the carter gave me potions and his purse.",
                        COMPLETED)], who="Tobias"),
    q.say("Up the road to Harrowby. Tell Reeve Aldwin the ogres are on the south road now. He'll be in the Moot Hall.",
          when=q.when(flag="met_tobias"), who="Tobias"),
    q.say("Down! Get down, stranger! ...You came up the south road? Then you walked right past them. Ogres, out of the "
          "pines, in broad day. They turned my wain over and they're still in the Hawkins' corn, eating the ears off "
          "the stalks. Three weeks this has gone on. Go up to Harrowby and tell the reeve they've come down to the "
          "south road now.",
          do=[A.flag("met_tobias"), A.stage("main", 1),
              q.journal("Ogres overturned Tobias the carter's harvest wain on the south road below Harrowby. He asked "
                        "me to tell Reeve Aldwin, in the Moot Hall, that they have come down to the south road.")],
          who="Tobias")])

# Aldwin: the main quest, the gate, and the poachers' plea
q.talker("Aldwin", [
    q.say("Grukh's axe. Lay it there, on the moot table, where the whole town can see it... Harrowby owes you its "
          "harvest. Here is the tithe we'd have paid him, and better spent. Light the harvest fire! And the west gate "
          "is open; the road runs on to Thornwick.",
          when=q.when(has=AXE, not_="aldwin_paid"),
          do=[A.flag("aldwin_paid"), A.flag("harvest_lit"), A.take(AXE), A.gold(250), A.give("ChainTunic"),
              A.give("RedPotion", 2), A.enable("HarvestLight"), A.unlock("WestGate1"), A.unlock("WestGate2"),
              A.enable("WestExit1"), A.enable("WestExit2"), A.enable("WestExit3"),
              A.print("Out on the square they are lighting the harvest fire."),
              q.journal("I brought Grukh's axe to Reeve Aldwin. He paid me the tithe, lit the harvest fire and opened "
                        "the west gate. The west road leads to Thornwick.", COMPLETED)], who="Aldwin"),
    q.say("Tam Bessson and his lads poaching the forester's deer? ...And their winter's grain in an ogre's belly. "
          "Tell Tam he's pardoned, him and his lads, if they come home and help bring the harvest in. I'll square it "
          "with Garrick.", when=q.when(flag="plea", not_="pardoned"),
          do=[A.flag("pardoned"),
              q.journal("Reeve Aldwin has pardoned Tam and his poachers if they come home. I should tell Tam in "
                        "Ashby wood.", QUEST)], who="Aldwin"),
    q.say("The gate's open and the fire's lit. Harrowby won't forget you.", when=q.when(flag="aldwin_paid"),
          who="Aldwin"),
    q.say("Grimtusk is up the hill road, north of the square, past their village. Bring me Grukh's axe; nothing less "
          "will make the town believe it.", when=q.when(flag="aldwin_told"), who="Aldwin"),
    q.say("Tobias sent you? On the south road, in daylight... Then it's worse than I feared. I am Aldwin, reeve of "
          "Harrowby. Three weeks ago an ogre called Grukh took the old hill-fort of Grimtusk in the northern pines, and "
          "since then he comes down for his tithe: grain, beasts, carters. His ogres hold the west road by night, so "
          "I've shut the west gate; I'll not send another cart to die on it. Kill Grukh and bring me his axe, so the "
          "town can see it, and I'll pay you what we'd have paid him, and open the gate.",
          do=[A.flag("aldwin_told"), A.stage("main", 2),
              q.journal("Reeve Aldwin has shut Harrowby's west gate, the road to Thornwick: Grukh the ogre warlord, who "
                        "holds the old hill-fort of Grimtusk in the northern pines, takes a tithe of the harvest and "
                        "his ogres hold the road. The reeve will pay and open the gate when I bring him Grukh's axe. "
                        "Grimtusk is up the hill road north of the square.", QUEST)], who="Aldwin")])
q.on_death("Grukh", [A.drop(AXE), A.drop("SteelHelm"), A.flag("grukh_dead"),
                     A.print("Grukh crashes down among his feast. His great axe rings on the stones."),
                     q.journal("Grukh is dead. Reeve Aldwin wanted his axe brought to the Moot Hall.", QUEST)])
q.on_pickup(AXE, [q.journal("I have Grukh's great axe, almost too heavy to carry. The reeve is waiting for it in the "
                            "Moot Hall.", QUEST)], when=q.when(not_="aldwin_paid"))
q.near(*ogres["fire"], 320, [A.print("Tusk palisades, skull posts and the smell of roasting meat: the ogres' village "
                                     "below Grimtusk.")])
q.near(*square_px(*fort_c), 300, [A.print("Grimtusk: the old hill-fort, its stones black with the ogres' smoke.")],
       when=q.when(flag="aldwin_told"))
q.on_all_dead(camp_ogres, [A.flag("village_clear"), A.print("The ogres' village is quiet. Grimtusk's door stands above.")])

# the gate guard and the watch
q.talker("GateGuard", [
    q.say("Gate's open by the reeve's word. West road runs to Thornwick. Mind the ruts.", when=q.when(flag="aldwin_paid"),
          who="Guard"),
    q.say("Gate's shut by the reeve's order. There's ogres on that road after dark. Talk to Aldwin in the Moot Hall.",
          who="Guard")])
for k_ in range(2):
    q.talker(f"Watch{k_ + 1}", [
        q.say("Harvest fire's lit. I'll drink to you tonight.", when=q.when(flag="harvest_lit"), who="Watch"),
        q.say("Keep inside the town after dark. If you hear something big in the corn, don't go and look.", who="Watch")])
    q.portrait(f"Watch{k_ + 1}", ("IxGuard2Pic", "Warrior2Pic")[k_])

# the Wolves of the Red Wood
q.on_all_dead(wolves, [A.flag("wolves_dead"), A.print("The black wolf lies still among the rocks. The den is empty.")])
q.talker("Osric", [
    q.say("The black one too? ...My boy will walk with a limp, the herbwife says, but he'll walk. Here: the bounty, "
          "and my father's boots; they've done more miles in that wood than I have.",
          when=q.when(flag=q.dead(*wolves), not_="osric_paid"),
          do=[A.flag("osric_paid"), A.gold(80), A.give("LeatherArmoredBoots"), A.give("RedPotion"),
              q.journal("I killed the wolves of the red wood. Osric the woodcutter paid me and gave me his father's "
                        "boots.", COMPLETED)], who="Osric"),
    q.say("I'll take the boy into the wood again in spring. Not before.", when=q.when(flag="osric_paid"), who="Osric"),
    q.say("North up the woodcutters' path, into the rocks. The black one leads them.", when=q.at("wolves", 1),
          who="Osric"),
    q.say("You've a sword. I've an axe, and a boy in bed with his leg torn open. A pack has denned in the rocks up the "
          "path, north of my hut, and a black wolf leads it, big as a calf. I'd go myself but I'd not come back, and "
          "then who'd feed him? Kill them and the woodcutters will pay you.",
          do=[A.stage("wolves", 1), q.journal("Osric the woodcutter's son was mauled by wolves. The pack dens in the "
                                              "rocks up the path north of his hut in the red west wood, led by a black "
                                              "wolf. Osric will pay when they are dead.", QUEST)], who="Osric")])

# the Poachers of Ashby: the law or mercy
q.on_all_dead(poacher_foes, [A.flag("poachers_dead"), A.print("The last poacher falls in the bracken.")])
turn_all = [A.turn(p_, f_) for p_, f_ in zip(poachers, poacher_foes)]
q.talker("Tam", [
    q.say("Home's warm. Mam's cried twice. Go on, take the bow; I'll not need it now.", when=q.when(flag="tam_paid"),
          who="Tam"),
    q.say("Pardoned? All of us? ...Then we're going home, lads. Take my bow, friend, and the arrows; I'll swing a "
          "scythe from now on. Tell Mam I'm coming up the road.",
          when=q.when(flag="pardoned", not_="tam_paid"),
          do=[A.flag("tam_paid"), A.give("Bow"), A.give("Quiver"), A.walk("Tam", tam_home)] +
             [A.disable(n) for n in poachers[1:]] +
             [A.print("Tam's lads shoulder their packs and slip away through the trees toward Harrowby."),
              q.journal("The reeve's pardon brought Tam and his poachers home from Ashby wood. Tam gave me his bow.",
                        COMPLETED)], who="Tam"),
    q.say("Has the reeve heard us? Go on, then. We'll wait.", when=q.when(flag="plea"), who="Tam"),
    q.say("Garrick sent you? Thought he might. Look: I'm Tam, Bess's son, from Harrowby. The ogres took our grain, all "
          "of it, and Garrick's deer don't care whose they are. We're not thieves; we're hungry. Take our plea to the "
          "reeve instead of our heads to the forester. Will you?",
          when=q.when(not_="refused"), ask=True,
          do=[A.flag("plea"), q.journal("Tam the poacher, a Harrowby man whose family's grain the ogres took, asked "
                                        "me to carry his plea to Reeve Aldwin instead of fighting.", QUEST)],
          else_=[A.flag("refused"), A.print("Tam sighs and nocks an arrow. 'Then I'm sorry for it.'"),
                 q.journal("I refused Tam's plea. His poachers have taken up their bows against me.", QUEST)] + turn_all,
          who="Tam")])
for n in poachers[1:]:
    q.talker(n, [q.say("Tam speaks for us.", who="Poacher")])
    q.portrait(n, "MalePic9")
q.talker("Garrick", [
    q.say("Dead, then. A sorry business, but the law's the law and my deer are my deer. The forester's bounty, and "
          "this; you shoot better than they did.", when=q.when(flag=q.dead(*poacher_foes), not_="garrick_paid"),
          do=[A.flag("garrick_paid"), A.gold(110), A.give("LeatherArmor"),
              q.journal("I drove the poachers out of Ashby wood. Forester Garrick paid the bounty.", COMPLETED)],
          who="Garrick"),
    q.say("Pardoned! The reeve's soft as new bread. ...Still, I'd rather Tam at a scythe than in my bracken. Here, for "
          "your trouble.", when=q.when(flag="pardoned", not_="garrick_paid"),
          do=[A.flag("garrick_paid"), A.gold(40)], who="Garrick"),
    q.say("Ashby's quiet. I'll take that.", when=q.when(flag="garrick_paid"), who="Garrick"),
    q.say("East through the oaks into Ashby wood. Their fire's easy to find; they're not good poachers.",
          when=q.at("poach", 1), who="Garrick"),
    q.say("Garrick, the reeve's forester. With the ogres on the hill I've no men to spare, and there's a band of "
          "poachers camped in Ashby wood, east of town, taking the deer. Drive them out, however you must, and the "
          "forester's bounty is yours.",
          do=[A.stage("poach", 1), q.journal("Forester Garrick wants the poachers in Ashby wood, east of town, driven "
                                             "out. He will pay the forester's bounty.", QUEST)], who="Garrick")])
q.near(*poachers_camp["fire"], 300, [A.print("A fire in the bracken, two tents, a deer hung from a branch: the "
                                             "poachers' camp.")])
q.talker("Bess", [
    q.say("He came up the road with his bow on your back and mud to his knees. I could have killed him. I hugged him "
          "instead.", when=q.when(flag="tam_paid"), who="Bess"),
    q.say("My Tam's in Ashby wood with those lads, poaching. He's a good boy. If the forester sends you, remember "
          "he's a good boy.", who="Bess")])

# the Reliquary
q.on_pickup(ANKH, [A.stage("ankh", 2), q.journal("I found the chapel's ankh in the old watchtower. Sister Maud will "
                                                 "want it back.", QUEST)], when=q.when(not_="maud_paid"))
q.talker("Maud", [
    q.say("The ankh of the Sheaf. Forty years... Thank you. Take the chapel's thanks: remedies, a charm the old priest "
          "wore, and the alms box; the Sheaf would want it spent on you.", when=q.when(has=ANKH, not_="maud_paid"),
          do=[A.flag("maud_paid"), A.take(ANKH), A.give("CurePoisonPotion", 2), A.give("RedPotion", 2),
              A.give("AmuletofNature"), A.gold(50),
              q.journal("I brought the chapel's ankh home from the old watchtower. Sister Maud gave me remedies, a "
                        "charm and the alms.", COMPLETED)], who="Maud"),
    q.say("It's back on the altar where it belongs. Come to the harvest blessing, if you're still here.",
          when=q.when(flag="maud_paid"), who="Maud"),
    q.say("The old watchtower is in the south-west wood, past the Hawkins' corn. Spiders, they say. Go carefully.",
          when=q.at("ankh", 1), who="Maud"),
    q.say("A traveller at harvest. Sit a moment. Forty years ago thieves broke into this chapel and took the ankh of "
          "the Sheaf from the altar. They hid it in the old watchtower in the south-west wood and never came back for "
          "it; the spiders saw to that. Nobody's dared fetch it since. If you're braver than Harrowby, bring it home.",
          do=[A.stage("ankh", 1), q.journal("Sister Maud of the chapel of the Sheaf asked me to bring home the chapel's "
                                            "ankh, hidden by thieves in the old watchtower in the south-west wood, "
                                            "where spiders nest.", QUEST)], who="Maud")])
q.near(*tower["boss"], 220, [A.print("The old watchtower, webbed over. Something moves in the dark of it.")])
q.on_all_dead(spiders, [A.flag("spiders_dead"), A.print("The watchtower is still.")])

# Hamon the miller: news and a line after
q.talker("Hamon", [
    q.say("Fire's lit and the stones are turning. Bring me your grain any time; I'll grind it for nothing.",
          when=q.when(flag="harvest_lit"), who="Hamon"),
    q.say("I won't grind past dusk; the ogres smell flour, I swear it. If you're going up to Grimtusk, their village "
          "sits below the fort, with a lookout at the palisade. Kill him quiet or the lot of them come running.",
          who="Hamon")])

for who_, pic_ in (("Tobias", "Townsman3Pic"), ("Aldwin", "TheogrinPic"), ("Maud", "MaidenPic"),
                   ("Garrick", "Warrior3Pic"), ("Osric", "Miner2Pic"), ("Hamon", "QuarterMasterPic"),
                   ("Bess", "MaidenPic6"), ("Tam", "MalePic10"), ("GateGuard", "Warrior2Pic")):
    q.portrait(who_, pic_)

m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())

# ---- 11. the exteriors' dressing: the farmers' and the ogres' scenes on the empty ground ------------------------------
dressed = Exterior(m, land, "green", placed=placed, culture=("farm", "ogre")).dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed, os.path.join(OUT, f"{NAME}.rooms.json"), yards=built)
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| trees {n_trees} | shops {n_shops} | caches {len(caches)} | opened {len(opened)} | lines {len(q.strings)} "
          f"| yards {', '.join(y_.kind for y_ in built) or 'none'} | dressing {sum(dressed.values())} groups")
    print("dressing:", dict(dressed))
