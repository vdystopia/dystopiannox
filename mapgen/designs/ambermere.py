"""Ambermere: an amber-gatherers' and fishers' town on the shore of a lake in a golden autumn wood, and the story of
the Drowned Crown (a map of its own, loadable directly; its west road leads to Thornwick, chapter one's map,
mapgen/designs/thornwick.py). The green world in three sections: the golden aspen wood round the town and the lake
(FORESTS["aspen"], yellow grass), the red dusk wood of the barrow-field in the north-west (FORESTS["dusk"]) and the old
brown wood of the reed shore and the north-east point (FORESTS["ancient"]). The barrow of the old lake-kings is built
and furnished in the Land of the Dead's manner (rules/CULTURES.md; BUILDINGS["barrow"]).

The story
- The player comes up the pilgrims' road from the south. By the roadside cairn the autumn pilgrims' cart lies
  overturned: last night the dead climbed out of the cairn's graves and fell on the pilgrims bringing candles to the
  chapel. Sister Ysolt alone hid and lived. Some of the risen still stand among the cairn's stones, and come for whoever
  passes on the road. She sends the player up to Ambermere.
- Ambermere: a square round a well, the Moot Hall of Reeve Osmund, the chapel of the Mere, the Amber Eel inn, Severin's
  amber house (the trader), the forge, houses; down the shore road the fishers' houses, the herbwife's hut and the
  dock on the Amber Mere; the amber pits in the south-west wood; the west gate on the road to Thornwick.
- Main quest, the Drowned Crown (several places, a boss, an object laid back where it belongs): Reeve Osmund has shut
  the west gate. Every night since the turn of the moon the dead walk the west road, and a traveller who leaves is
  walking to his grave. He sends the player to Prioress Hildreth. She knows why: diggers broke open the Barrow of the
  Lake-Kings in the north-west, and with them came a necromancer, Malvo, who took the Drowned Crown from the barrow's
  altar. The crown kept the kings asleep; with it in his hands he raises the dead to dig for him. The player passes
  the diggers' camp in the barrow-field (a sentry rouses the rest), fights through the risen kings' guard in the
  barrow's hall and kills Malvo in the crypt. Laid back on the altar under the old god's statue, the crown puts the
  dead to sleep (the hall's flame relights). Osmund pays and opens the west gate.
- The Amber Pits (a bounty on a band and its chief): urchins came up out of the old diggings and drove Garth's
  amber-diggers off the pits in the south-west wood; their shaman squats on the amber heaps. Garth, waiting on the
  pit road at the edge of town, pays when the shaman and his band are dead.
- Pip in the Reeds (a rescue; the rescued walks home): Morwen the net-mender's boy went egging on the reed shore north
  of the mere and has hidden two days in the old smokehouse while spiders nest round it. With the spiders dead, Pip
  walks home to his mother's door, and Morwen gives her late husband's bow.
- The Heart of the Mere (a choice between two givers who want the same thing): Severin the amber-cutter wants the
  Heart of the Mere, the great red stone the lake-folk set on the shrine of the north-east point, which an ogre took
  when he and his grunts made the shrine their lair. Severin pays two hundred gold for it. Old Rue the herbwife, on
  the shore, says it belongs to the mere and asks for it to go back: she pays in remedies and a charm.
- The forge, Severin's amber house and the inn buy and sell. The diggers' chest, the urchins' hoard, the smokehouse's
  store and three caches in the wood hold loot, and Malvo wears a dead king's helm; every soul in town knows something.
- The exit: the west road beyond the west gate joins the King's Road below Thornwick.

    py mapgen/designs/ambermere.py [seed]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import Land, square_tile, square_px, px_square, cell_square
from kit.water import Waterworks
from kit.vegetation import Planter, FORESTS, TOWN_PLANTING
from kit.village import Village
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT
from kit import yards as Y
from kit import camps
from kit.story import StoryMap
from kit.dressing import Exterior

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7
rng = random.Random(SEED)
NAME = "Ambermere"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "ambermere")
NEXT_MAP = "Thornwick"                 # the west road joins the King's Road below Thornwick
CROWN = "Crown"                        # the Drowned Crown (things: LIGHT, SIMPLE)
HEART = "Ruby"                         # the Heart of the Mere, a great red stone


def uv(X, Y):
    """uv of a point given in map squares as seen on screen (X right, Y down, 0..255)."""
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="an amber-gatherers' and fishers' town on the shore of a lake in a golden autumn wood: a square round a well, "
          "the reeve's moot hall, a chapel, an inn and an amber-cutter's house, fishers' houses and a dock down the "
          "shore road, amber pits in the south-west wood taken by urchins, the barrow of the old lake-kings in the red "
          "wood to the north-west, a smokehouse on the reed shore and an ogre in the shrine on the north-east point; "
          "the west gate shut on the road to Thornwick",
    environment="town", mood="mournful, uneasy, autumnal",
    areas=[AreaIdentity("south", "the pilgrims' road from the south: the start"),
           AreaIdentity("cairn", "the roadside cairn whose dead rose and fell on the pilgrims"),
           AreaIdentity("town", "Ambermere's square and its streets", landmark="Well"),
           AreaIdentity("shore", "the shore road's end: the fishers' houses, the herbwife's hut and the dock"),
           AreaIdentity("mere", "the Amber Mere", landmark="the lake"),
           AreaIdentity("pits", "the amber pits in the south-west wood, taken by urchins"),
           AreaIdentity("gate", "the west gate, shut"),
           AreaIdentity("west", "the west road on to Thornwick: the way out"),
           AreaIdentity("barrows", "the old barrow-field in the red wood, the diggers' camp"),
           AreaIdentity("barrow", "the Barrow of the Lake-Kings"),
           AreaIdentity("reeds", "the reed shore north of the mere and its old smokehouse"),
           AreaIdentity("shrine", "the shrine of the mere on the north-east point, an ogre's lair now")],
    buildings=[BuildingIdentity("fisher", "shore", "Morwen's house", "Morwen the net-mender and her boy Pip"),
               BuildingIdentity("fisher", "shore", "", "a fisher's family"),
               BuildingIdentity("herbwife", "shore", "Rue's hut", "old Rue the herbwife"),
               BuildingIdentity("townhall", "town", "the Moot Hall", "Reeve Osmund"),
               BuildingIdentity("chapel", "town", "the chapel of the Mere", "Prioress Hildreth"),
               BuildingIdentity("inn", "town", "The Amber Eel", "the innkeeper"),
               BuildingIdentity("store", "town", "Severin's amber house", "Severin the amber-cutter"),
               BuildingIdentity("smithy", "town", "the forge", "the smith"),
               BuildingIdentity("home", "town", "", "an amber-digger's family"),
               BuildingIdentity("home", "town", "", "Garth the pit-boss"),
               BuildingIdentity("home", "town", "", "a carter's family"),
               BuildingIdentity("cottage", "town", "", "a widow"),
               BuildingIdentity("cottage", "town", "", "an old net-maker"),
               BuildingIdentity("barrow", "barrow", "the Barrow of the Lake-Kings", "the old kings, asleep")])

m = Spec(NAME, summary="Ambermere", description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"Generated by Claude.", author="vdystopia (generated by Claude)", version="1", date="2026", type=SOLO,
         minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [148, 132, 108]           # a low amber autumn light
q = QuestBook(NAME)

# sections: each its own forest (walls, trees, undergrowth) and ground (base, sparse, dense)
REGIONS = dict(
    gold=dict(forest="aspen", ground=("GrassNormYellow", "GrassSparseYellow", "GrassDenseYellow")),
    dusk=dict(forest="dusk", ground=("GrassNorm", "GrassSparse2", "GrassDense")),
    old=dict(forest="ancient", ground=("GrassDense", "GrassNorm", "GrassSparse2")),
)
SECTION = {"south": "gold", "cairn": "gold", "town": "gold", "shore": "gold", "mere": "gold", "pits": "gold",
           "gate": "gold", "west": "gold", "barrows": "dusk", "barrow": "dusk", "reeds": "old", "shrine": "old"}



def section(r):
    """The section of a region name: an area's own, or a passage's side pocket's (pocket_<a>_<b>_<k>), its first end's."""
    if r in REGIONS: return r
    for part in (r or "").split("_")[1:]:
        if part in SECTION: return SECTION[part]
    return "gold"


# ---- 1. the plan: the pilgrims' road up to the town, the shore road to the mere, the ways out to the wild places -----
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"south": ((126, 234), 16), "cairn": ((90, 216), 14), "town": ((110, 150), 80), "shore": ((178, 162), 24),
         "mere": ((212, 140), 36), "pits": ((40, 190), 26), "gate": ((52, 120), 12), "west": ((20, 108), 12),
         "barrows": ((98, 62), 30), "barrow": ((62, 40), 36), "reeds": ((178, 80), 26), "shrine": ((222, 34), 20)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "town", region=SECTION[k_])
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_, bend_ in (("south", "town", 14, True, 0.18), ("town", "shore", 13, True, 0.12),
                                 ("shore", "mere", 14, False, 0.1), ("town", "gate", 13, True, 0.15),
                                 ("gate", "west", 12, True, 0.15), ("town", "pits", 12, True, 0.22),
                                 ("south", "cairn", 9, False, 0.25), ("town", "barrows", 11, True, 0.22),
                                 ("barrows", "barrow", 11, True, 0.2), ("shore", "reeds", 12, True, 0.2),
                                 ("reeds", "shrine", 10, False, 0.28)):
    land.link(a_, b_, w_, bend=bend_, road=road_, pockets=(1, 2) if road_ else (0, 1))
land.blends(m)
for mat_, prio_ in (("GrassSparseYellow", 0.3), ("GrassNormYellow", 0.5), ("GrassDenseYellow", 0.7)):
    m.blending(mat_, prio_)

# the mere: a lake in its own dead-end clearing past the shore road's end, reserved before anything is built
mere_c = land.areas["mere"]["c"]
LAKE_R = 10                                   # tiles (squares), up to 1.35 times that with the shore's roughness
land.reserve_band([uv(*AREAS["mere"][0])], LAKE_R * 1.35 + 1.5)

# ---- 2. the centre: the square and its well, the roads leaving it --------------------------------------------------
vc = land.areas["town"]["c"]
land.paint_square(m, "town", 12, "RoughCobble")
land.taken |= {(int(vc[0]) + a, int(vc[1]) + 1 + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}
barrow_c0 = land.areas["barrow"]["c"]              # the old kings' way stops short of the barrow's door
land.paint_roads(m, "DirtDark2", width_squares=2.8,
                 skip=land.reserved | {(i, j) for i in range(int(barrow_c0[0]) - 16, int(barrow_c0[0]) + 17)
                                       for j in range(int(barrow_c0[1]) - 16, int(barrow_c0[1]) + 17)
                                       if math.hypot(i - barrow_c0[0], j - barrow_c0[1]) < 13})

# ---- 3. buildings from the square outwards; none at the cairn, the camps or the wild places ---------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"cairn": 10, "south": 8, "pits": 15, "barrows": 15, "reeds": 13, "shrine": 11},
                            first=("shore",), centred={"barrow": "barrows"})
by_role = sm.by_role
sm.connect_and_furnish()

# the yards: the old graves of the barrow-field, the amber pits, the drowned fishers' memorial, the town's orchard
yards = []


def ring_of(c, radii):
    return [(c[0] + r * math.cos(a * math.pi / 6), c[1] + r * math.sin(a * math.pi / 6)) for r in radii for a in range(12)]


for kind_, area_, rs_, toward_ in (("graveyard", "barrows", (6, 8, 10), "town"), ("quarry", "pits", (0, 3, 6), "town"),
                                   ("monument", "shore", (6, 9, 12, 15), "shore"), ("orchard", "town", (18, 22, 26, 30, 34), "town")):
    y_ = Y.plan_any(land, rng, kind_, ring_of(land.areas[area_]["c"], rs_), toward=land.areas[toward_]["c"])
    if y_: yards.append(y_)
    else: print(f"no room for the {kind_}")
pit_yard = next((y_ for y_ in yards if y_.kind == "quarry"), None)

# ---- 4. the land grows round everything, ending in the forest wall ---------------------------------------------------
land.carve(margin=3.5)
lane_ = sm.keep_open({"cairn": 6, "barrows": 9, "reeds": 8, "shrine": 8, "pits": 6, "south": 3})
land.assign_regions()
clumps = land.thickets(170, size=(0.9, 1.8), clear=1, avoid=frozenset(lane_ & land.squares))
land.open_links()
land.region_map = {s_: section(r_) for s_, r_ in land.region_map.items()}
land.apply(m, wall=lambda r: FORESTS[REGIONS[r]["forest"]]["wall"], floor=lambda r: REGIONS[r]["ground"][0])
built = []
for y_ in yards:
    if not y_.plot <= land.squares:
        print(f"the {y_.kind} lies off the land"); continue
    Y.build(m, rng, land, y_)
    built.append(y_.kind)

# the water: the mere dug into its clearing, the shore round it walled by the water's edge
ww = Waterworks(m, rng, inside=lambda x, y: m.floor.get((x, y), "").startswith("Grass") and
                cell_square(x, y) not in land.roads)
lake = ww.pond(uv(*AREAS["mere"][0]), radius=LAKE_R, roughness=0.3)
for t in lake.tiles:
    if "Water" in m.floor.get(t, ""): land.water.add(cell_square(*t))

# the west gate: a wall of grey stone across the road from forest to forest, a barred double gate in it
gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "west"), prefix="WestGate")

# ---- 5. the town's life ------------------------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Amber Eel\nSmoked eel, cider and a bed by the fire", "Sign"),
                     store=q.text("Severin's Amber House\nAmber cut and set. Goods for the road.", "Sign"),
                     smithy=q.text("The Forge\nBlades, mail and mending", "Sign"),
                     chapel=q.text("The Chapel of the Mere", "Sign"), townhall=q.text("The Moot Hall", "Sign"))
for bid, b in placed:
    role = BUILDINGS[bid.role]
    for sc in role["scenes"]: vil.scene(b, sc, role=bid.role)
    if rng.random() < role["garden"]: vil.garden(b, size=(rng.randint(3, 5), rng.randint(2, 4)))
m.obj_px("Well", *square_px(vc[0] + 0.5, vc[1] - 0.5))


def lamp(si, sj):
    x, y = square_px(si, sj)
    m.obj_px("StreetLampOrnate3", x, y); m.obj_px("StreetLampOrnate3Shadow", x - 15, y + 21)


vil.square_piece((vc[0] + 0.5, vc[1] - 0.5), 5, pole=lamp, per_side=1)
for r_ in REGIONS:
    g_ = REGIONS[r_]["ground"]
    land.ground_variety(m, base=g_[0], sparse=g_[1], dense=g_[2], clear=3, region=r_)

# the dock: where the shore road reaches the mere, out into open water; a path from it to the road
shore_c = land.areas["shore"]["c"]
dock = None
for dir_ in ("down", "up"):
    dock = ww.dock(lake, dir_, length=2, beyond=4, near=(2 * shore_c[0], 2 * shore_c[1]))
    if dock: break
if dock:
    du_, dv_ = dock["start"]
    land.connect(m, px_square((du_ + dv_) / 2 * CELL, (du_ - dv_) / 2 * CELL))
else:
    print("no room for the dock")
for c in list(ww.no_walls): land.taken.add(cell_square(*c))

# ---- 6. the story's places ------------------------------------------------------------------------------------------
C = {k: land.areas[k]["c"] for k in AREAS}
south_c, cairn_c, pits_c, barrows_c, barrow_c, reeds_c, shrine_c, west_c = (
    C[k] for k in ("south", "cairn", "pits", "barrows", "barrow", "reeds", "shrine", "west"))


def off_road(c, clear=4.5, reach=12):
    """The square nearest `c` with no road within `clear` squares, on open land: a camp beside its way, not on it."""
    from kit.layout import bfs_distance
    near_road = bfs_distance(list(land.roads), land.squares, int(clear) + 1)
    fenced = set().union(*({(y_.gi + a, y_.gj + b) for a in range(-2, y_.w + 2) for b in range(-2, y_.h + 2)}
                           for y_ in yards))
    cands = [s for s in land.squares if near_road.get(s, 99) >= clear and s not in land.taken_strict and
             s not in fenced and s not in land.water and math.hypot(s[0] - c[0], s[1] - c[1]) <= reach]
    s = min(cands, key=lambda s: math.hypot(s[0] - c[0], s[1] - c[1])) if cands else (int(c[0]), int(c[1]))
    return (s[0] + 0.5, s[1] - 0.5)


# the pilgrims' cart, overturned on the verge where the cairn's path leaves the road
cairn_road = sm.road_near(((cairn_c[0] + south_c[0]) / 2, (cairn_c[1] + south_c[1]) / 2))
road_dir = math.atan2(vc[1] - south_c[1], vc[0] - south_c[0])
wsq = min((s for s in land.squares if s not in land.roads and s not in land.taken and
           1.0 <= min(math.hypot(s[0] - r[0], s[1] - r[1]) for r in land.roads
                      if abs(r[0] - cairn_road[0]) + abs(r[1] - cairn_road[1]) < 12) <= 2.5),
          key=lambda s: math.hypot(s[0] - cairn_road[0], s[1] - cairn_road[1]))
wreck = camps.wagon_wreck(m, rng, land, (wsq[0] + 0.5, wsq[1] - 0.5), road_dir)
# the cairn: a ring of old stones round the graves the dead broke out of
cairn_px = camps.stone_ring(m, rng, land, cairn_c, n=6, radius=2.8, stone="ObeliskPrimitive", clear=4)
csc = camps.Scene(m, rng, land, cairn_c)
graves = []
for k_ in range(3):
    a_ = k_ * 2 * math.pi / 3 + 0.4
    for t_ in ("CoffinBreaking1", "CoffinBreaking2", "CoffinBreaking3"):
        o_ = csc.put(t_, *csc.at(1.3, a_))
        if o_: graves.append(csc.px(1.3, a_)); break
for k_ in range(4):
    csc.put(rng.choice(("Skull", "ArmBone", "LegBone")), *csc.at(rng.uniform(1.8, 3.6), rng.uniform(0, 6.28)))
# the diggers' camp in the barrow-field, open toward the town road
barrows_camp = camps.bandit_camp(m, rng, land, off_road(barrows_c), vc,
                                 loot=[("Gold", {"Amount": 80}), "RedPotion", "RedPotion", "Quiver", "LeatherHelm"],
                                 sleepers=4, tents=2)
for k_ in range(3):                                   # their spades in the opened barrows
    camps.Scene(m, rng, land, barrows_c).put(rng.choice(("MiningShovelInGround", "MiningPickAxeInGround1")),
                                             *camps.Scene(m, rng, land, barrows_c).at(5.5, k_ * 2.1 + 0.7))
# the amber pits: the urchins' squat among the diggers' heaps
pits_sc = camps.Scene(m, rng, land, pits_c)
urchin_spots = []
pit_c = pit_yard.centre if pit_yard and "quarry" in built else pits_c
psc = camps.Scene(m, rng, land, (pit_c[0], pit_c[1]))
hoard = None
for r_, a_ in ((1.2, 0.3), (1.6, 2.2), (2.0, 4.0)):
    hoard = psc.put("Chest2", *psc.at(r_, a_), items=[("Gold", {"Amount": 60}), "BluePotion", "LeatherArmoredBoots"])
    if hoard: break
for k_, t_ in enumerate(("UrchinBed1", "UrchinBedFlat1", "UrchinHammock1", "UrchinStool1", "UrchinTableSmall",
                         "UrchinStool2", "UrchinBed3", "UrchinBedFlat2")):
    pits_sc.put(t_, *pits_sc.at(rng.uniform(6.0, 8.5), k_ * 0.785 + rng.uniform(-0.2, 0.2)))
for k_ in range(6):
    urchin_spots.append(pits_sc.px(rng.uniform(3.0, 6.5), k_ * 1.05 + 0.5))
# the old smokehouse on the reed shore, its door toward the town path; the spiders' webs round it
smoke_c = off_road(reeds_c, clear=6.5)
smokehouse = camps.ruined_tower(m, rng, land, smoke_c, reeds_c, loot=[("Gold", {"Amount": 40}), "RedPotion", "Bread"],
                                size=(7, 7), material="Log")
rsc = camps.Scene(m, rng, land, smoke_c)
for k_ in range(4):
    rsc.put(rng.choice(("SpiderWebNorth", "SpiderWebEast", "SpiderWebNorthEast")), *rsc.at(5.2, k_ * 1.57 + 0.6))
# the shrine of the mere on the north-east point: standing stones round the empty socket of the Heart
shrine_px = camps.stone_ring(m, rng, land, shrine_c, n=7, radius=2.8, stone="ObeliskPrimitive",
                             core="DunMirFlameBasinUnlit", clear=4)
ssc = camps.Scene(m, rng, land, shrine_c)
for k_ in range(5):
    ssc.put(rng.choice(("OgreStraw1", "OgreStraw2", "OgreStraw3", "ArmBone", "Skull")), *ssc.at(rng.uniform(4.3, 6.0),
                                                                                           rng.uniform(0, 6.28)))
# caches in the wood, off the ways
caches = []
for near_, loot_, stump_ in ((pits_c, [("Gold", {"Amount": 45}), "CurePoisonPotion", "RedPotion"], True),
                             (reeds_c, [("Gold", {"Amount": 55}), "LeatherBoots", "RedPotion"], False),
                             (barrows_c, [("Gold", {"Amount": 35}), "BluePotion", "SpellBook"], False)):
    s_ = sm.hidden_spot(near_, r=(9, 16))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
# signposts
camps.signpost(m, land, (south_c[0] + 2.5, south_c[1] - 1.5),
               q.text("AMBERMERE\nUp the road, on the shore of the Amber Mere.\nPilgrims welcome at the chapel.", "Sign"))
gs_ = sm.road_near(((gate_sq[0] * 2 + vc[0]) / 3, (gate_sq[1] * 2 + vc[1]) / 3))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 1.5),
               q.text("THE WEST GATE IS SHUT\nThe dead walk the west road by night.\n- Osmund, Reeve of Ambermere", "Sign"))
pr_ = sm.road_near(((pits_c[0] + vc[0]) / 2, (pits_c[1] + vc[1]) / 2))
camps.signpost(m, land, (pr_[0] + 2.0, pr_[1] - 1.5), q.text("THE AMBER PITS\nDiggers only.", "Sign"))

# ---- 7. lights and planting -----------------------------------------------------------------------------------------
presets = json.load(open(os.path.join(HERE, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]


def preset(family):
    return max((p for p in presets if p["family"] == family and p["animation"] == "steady" and p["intensity_class"] == "full"),
               key=lambda p: p["weighted_share"])["xfer"]


keep = set()
for bid, b in placed:
    for d in b.entrances:
        di, dj = px_square(*d.px)
        keep |= {(di + a, dj + b2) for a in range(-2, 3) for b2 in range(-2, 3)}
vil.ground_bits(1.4)
planter = Planter(m, rng, land, "aspen", keep_clear=keep | lane_, settled=("town", "shore"),
                  forest_of=lambda s: REGIONS[section(land.region_of(s))]["forest"])
n_trees, n_small = planter.plant_all(groves=4, profile=TOWN_PLANTING)
piles = planter.rock_piles(max(4, len(land.squares) // 900))
vignettes = planter.forest_floor(max(6, len(land.squares) // 700))
ww.finish()
start_xy = square_px(south_c[0] + 0.5, south_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
sm.exit_to("west", NEXT_MAP, prefix="WestExit")

# ---- 8. the people --------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
person, room_of, free_px = sm.person, sm.room_of, sm.free_px
vx, vy = square_px(*vc)
# Sister Ysolt by the pilgrims' cart
yx_, yy_ = wreck["carter"]
person("Con07B", "Kayla", yx_, yy_, "Ysolt", face=start_xy)
# Reeve Osmund in the Moot Hall
gh = room_of("townhall", "great_hall")
ox_, oy_ = free_px(gh) if gh else (vx, vy)
person("Con02a", "Mayor_Theogrin", ox_, oy_, "Osmund")
# Prioress Hildreth before her altar
ch = room_of("chapel", "chapel")
hx_, hy_ = free_px(ch) if ch else (vx, vy + 40)
person("Con02a", "Gretchen", hx_, hy_, "Hildreth")
# Severin outside his amber house
sv_ = sm.outside_door("store") or (vx + 60, vy)
person("Con07B", "Dorian", sv_[0] + 18, sv_[1] + 14, "Severin", face=(vx, vy))
# Garth on the pit road at the edge of town, by the diggers' handcart
gr_ = sm.road_near(((pits_c[0] + vc[0] * 2) / 3, (pits_c[1] + vc[1] * 2) / 3))
gsc = camps.Scene(m, rng, land, (gr_[0], gr_[1]))
gpos = None
for da_ in (1.8, -1.8, 2.6, -2.6):
    p_ = (gr_[0] + 0.5 + da_ * 0.7, gr_[1] - 0.5 - da_ * 0.7)
    if gsc.ok(*p_):
        gpos = square_px(*p_); break
gx_, gy_ = gpos or square_px(gr_[0] + 2.5, gr_[1] - 0.5)
person("Con03A", "Kenneth", gx_, gy_, "Garth", face=square_px(*pits_c))
# Morwen at her door on the shore, Rue in her herb room
fishers = [b for bid, b in placed if bid.role == "fisher"]
mw_ = (sm.outside_door(building=fishers[0]) if fishers else None) or square_px(*shore_c)
person("Con02a", "Lydia", mw_[0] + 16, mw_[1] + 16, "Morwen", face=square_px(*mere_c))
hr = room_of("herbwife", "herbalist")
rx_, ry_ = free_px(hr) if hr else square_px(shore_c[0] + 3, shore_c[1])
person("Con02a", "Julie", rx_, ry_, "Rue")
# Pip hiding in the smokehouse
px_, py_ = smokehouse["boss"]
person("Con02a", "Tommy", px_, py_, "Pip", face=square_px(*vc))
# the gate guard, on the town side of the west gate
gq_ = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
gdx, gdy = vx - gq_[0], vy - gq_[1]
gl = math.hypot(gdx, gdy) or 1
person("Con02a", "Mayor's_Guard", gq_[0] + 70 * gdx / gl + 26, gq_[1] + 70 * gdy / gl, "GateGuard", face=(vx, vy))
# Pip's way home, to his mother's door
pip_wps = pop.waypoint_path("PipHome", [(mw_[0] - 14, mw_[1] + 26)])
# shopkeepers
WARES = {"store": [(4, "RedPotion"), (3, "BluePotion"), (2, "CurePoisonPotion"), (3, "RedApple"), (2, "Bread"),
                   (3, "Quiver"), (1, "Bow"), (1, "CrossBow"), (1, "LeatherBoots"), (1, "LeatherHelm"),
                   (1, "LeatherArmor"), (1, "LeatherLeggings")],
         "inn": [(6, "RedApple"), (5, "Meat"), (4, "Cider"), (4, "Bread"), (2, "RedPotion")],
         "smithy": [(2, "Sword"), (1, "Longsword"), (1, "BattleAxe"), (1, "MorningStar"), (1, "WoodenShield"),
                    (1, "SteelShield"), (1, "ChainCoif"), (1, "ChainTunic"), (1, "ChainLeggings"), (1, "SteelHelm")]}
GREET = {"store": q.text("Severin's amber house. Amber cut and set, and goods for the road. Since the gate shut I sell "
                         "more candles than amber.", "Shop"),
         "inn": q.text("Welcome to the Amber Eel. The eel's smoked this morning, the cider's from the orchard, and the "
                       "fire's for everyone.", "Shop"),
         "smithy": q.text("The forge. If you're going where the dead walk, you'll want steel that bites.", "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"smithy": "ShopkeeperWarriorsRealm"})
# townsfolk on their rounds, each with something to tell
FOLK = [("Con02a", "Tanya"), ("Con02a", "Clyde"), ("Con07B", "Shari"), ("Con03A", "Millard"), ("Con02a", "Jacob"),
        ("Con06a", "Townsman2"), ("Con02a", "Joyce"), ("Con03A", "Osborn")]
RUMOURS = [
    "The reeve's shut the west gate. Says the dead walk the west road by night. My cousin saw them, swaying in the road.",
    "Diggers came through at the turn of the moon, with picks and a pale man in black. They went up the old kings' way.",
    "Prioress Hildreth knows the old barrows better than anyone. Ask her what's wrong out there.",
    "Garth's diggers were run off the amber pits by urchins. He sits on the pit road all day, cursing.",
    "Morwen's boy Pip went egging on the reed shore two days ago and never came home. She's half out of her mind.",
    "Severin would sell his own mother for a good stone. He's been asking after the Heart of the Mere.",
    "There's an ogre in the old shrine on the north-east point. Rue says the fish went when the Heart was taken.",
    "The pilgrims are late with the autumn candles. They should have come up the south road yesterday.",
]
for c_, r_ in ((barrows_c, 16), (pits_c, 14), (cairn_c, 10), (cairn_road, 9), (reeds_c, 12)):    # the folk keep away from the foes
    sm.keep_folk_away(c_, r_)
ring = sm.townsfolk(FOLK, vc, q=q, rumours=RUMOURS,
                    after=("crown_laid", "The dead are quiet again, and the west gate's open. You'll be off to "
                                         "Thornwick, then? Safe road."),
                    pics=("MaidenPic3", "MalePic7", "MaidenPic4", "Townsman3Pic", "MalePic8", "Townsman1Pic",
                          "MaidenPic2", "Townsman2Pic"),
                    radius=7.0)
# the reeve's watch, each on a beat through the town
for k_, donor_ in enumerate(("Contest_Guard", "IxGuard2")):
    wx2, wy2 = ring[k_ * 4]
    person("Con02a", donor_, wx2, wy2, f"Watch{k_ + 1}", action=0)
    sm.beat(f"Watch{k_ + 1}", vc, radius=7.0, stops=7)

# ---- 9. the fights ----------------------------------------------------------------------------------------------------
# the cairn's risen dead, standing by the graves they broke out of; they come for whoever passes on the road
risen = []
for k, (x, y) in enumerate(graves + [csc.px(2.0, 3.6)]):
    n = f"Risen{k + 1}"
    pop.creature("Ghost" if k == 3 else "Skeleton", x, y, action="idle", face=square_px(*south_c), scr=n, aggr=0.5,
                 sight=90)
    risen.append(n)
# the diggers round their fire in the barrow-field, archers at the way in
diggers = []
for k, (x, y) in enumerate(barrows_camp["seats"][:4]):
    n = f"Digger{k + 1}"
    pop.creature("Swordsman", x, y, action="idle", face=barrows_camp["fire"], scr=n, aggr=0.83)
    diggers.append(n)
lx_, ly_ = barrows_camp["lookout"]
for k in range(2):
    n = f"DiggerArcher{k + 1}"
    pop.creature("Archer", lx_ + (k * 2 - 1) * 40, ly_, action="guard", face=square_px(*vc), scr=n, aggr=0.83)
    diggers.append(n)
B.sentry("DiggerArcher1", square_px(*vc), rouse=diggers[:4], shout="Someone's on the kings' way! Up!")
# the barrow: the kings' risen guard in the hall, Malvo among the tombs with his raised dead
hall = room_of("barrow", "dark_chapel")
crypt = room_of("barrow", "dark_crypt")
assert hall and crypt, "the barrow was not built with its hall and crypt"
kings_guard = sm.keepers(hall, ("Skeleton", "Skeleton", "SkeletonLord", "Skeleton", "Ghost"), "KingsGuard")
crypt_dead = sm.keepers(crypt, ("Skeleton", "Ghost", "Skeleton"), "CryptDead")
mx_, my_ = free_px(crypt, clear=26)
pop.creature("Necromancer", mx_, my_, action="guard", scr="Malvo", aggr=0.83, HealthMultiplier=3.0)
# the altar: the old god's statue in the hall; the flame before it relights when the crown is laid back
altar = next((o for o in m.d["objects"] if o.get("type", "").startswith("LOTDLichGodStatue") and
              (int(o["x"] // CELL), int(o["y"] // CELL)) in {(x, y) for x, y in hall.tiles} |
              {(x + a, y + b) for x, y in hall.tiles for a in (-1, 0, 1) for b in (-1, 0, 1)}), None)
ax_, ay_ = (altar["x"], altar["y"]) if altar else free_px(hall)
hx2, hy2 = sum(x for x, _ in hall.tiles) / len(hall.tiles), sum(y for _, y in hall.tiles) / len(hall.tiles)
hcx, hcy = (hx2 + 1) * CELL, (hy2 + 1) * CELL
dl_ = math.hypot(hcx - ax_, hcy - ay_) or 1
flame_xy = free_px(hall, prefer=(ax_ + (hcx - ax_) / dl_ * 46, ay_ + (hcy - ay_) / dl_ * 46), clear=24)
m.obj_px("ColorLight", flame_xy[0], flame_xy[1] - 5, xfer=dict(preset("orange")), scr="AltarLight")
m.obj_px("DunMirFlameBasinUnlit", *flame_xy, scr="AltarBasin")
# the urchins on the amber pits and their shaman on the heaps
urchins = []
for k, (x, y) in enumerate(urchin_spots):
    n = f"PitUrchin{k + 1}"
    pop.creature("Urchin", x, y, action="guard" if k % 2 else "idle", scr=n, aggr=0.83, face=square_px(*vc))
    urchins.append(n)
shx_, shy_ = square_px(pit_c[0], pit_c[1] - 0.5)
pop.creature("UrchinShaman", shx_, shy_, action="guard", scr="PitShaman", aggr=0.83, HealthMultiplier=2.0)
urchins.append("PitShaman")
# the spiders round the smokehouse
spiders = []
for k, a in enumerate((0.4, 1.9, 3.3, 4.6, 5.8)):
    x, y = rsc.px(4.2, a)
    n = f"ReedSpider{k + 1}"
    pop.creature("BlackWidow" if k == 0 else "Spider" if k % 2 else "SmallSpider", x, y, action="guard", scr=n,
                 aggr=0.83, face=square_px(*reeds_c))
    spiders.append(n)
# the ogre in the shrine and his grunts
pop.creature("OgreBrute", shrine_px[0] + 40, shrine_px[1] + 20, action="guard", scr="Grukk", aggr=0.83,
             face=square_px(*reeds_c), HealthMultiplier=1.5)
grunts = []
for k, a in enumerate((0.8, 2.6, 4.4)):
    x, y = ssc.px(3.8, a)
    n = f"ShrineGrunt{k + 1}"
    pop.creature("GruntAxe", x, y, action="guard", scr=n, aggr=0.83, face=square_px(*reeds_c))
    grunts.append(n)
# the golden wood's own creatures by the forest's edge
sm.wild({"Wolf": 3, "Bat": 3, "SmallSpider": 2, "Urchin": 1, "Bear": 1}, away_from=vc, per100=0.4, gap=7, min_away=34,
        avoid=(cairn_c, pits_c, barrows_c, barrow_c, reeds_c, shrine_c, south_c, west_c, gate_sq, shore_c, mere_c))

story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]] + \
           [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)
# fish in the mere (Westwood's lakes and streams carry them)
fish = 0
for k in range(40):
    if fish >= 8: break
    a, r = rng.uniform(0, 6.28), rng.uniform(2.0, LAKE_R * 0.75)
    s_ = (int(mere_c[0] + r * math.cos(a)), int(mere_c[1] + r * math.sin(a)) + 1)
    if s_ not in land.water or any((s_[0] + a2, s_[1] + b2) not in land.water for a2 in (-1, 0, 1) for b2 in (-1, 0, 1)):
        continue
    pop.creature("FishBig" if fish % 3 == 0 else "FishSmall", *square_px(s_[0] + 0.5, s_[1] - 0.5), action=0,
                 roamflag=255)
    fish += 1

# ---- 10. the story ----------------------------------------------------------------------------------------------------
q.start([A.lock("WestGate1"), A.lock("WestGate2"), A.disable("WestExit1"), A.disable("WestExit2"),
         A.disable("WestExit3"), A.disable("AltarLight"),
         q.journal("The pilgrims' road climbs through a golden wood toward Ambermere, on the shore of the Amber Mere.",
                   HINT)])

# the cairn: the risen dead come for whoever passes on the road below
cx3, cy3 = square_px(*cairn_road)
q.near(cx3, cy3, 170, [A.hunt(n) for n in risen] + [A.print("Bones rattle among the cairn stones. The dead are "
                                                             "coming down to the road!")])
q.on_all_dead(risen, [A.flag("cairn_clear"), A.print("The last of the risen falls, and lies still.")])
q.talker("Ysolt", [
    q.say("They're down? All of them? Then the brothers can be buried properly. Take these, and the alms purse; "
          "the chapel would want it spent on you.", when=q.when(flag=q.dead(*risen), not_="ysolt_paid"),
          do=[A.flag("ysolt_paid"), A.give("RedPotion", 2), A.gold(30),
              q.journal("I laid the cairn's risen dead to rest. Sister Ysolt gave me potions and the pilgrims' alms.",
                        COMPLETED)], who="Ysolt"),
    q.say("Go up to Ambermere and tell the Prioress what happened here. Tell her the cairn has opened.",
          when=q.when(flag="met_ysolt"), who="Ysolt"),
    q.say("Stranger! Are you real? Gods... We were bringing the autumn candles up to the chapel of the Mere. Last night "
          "the cairn by the road broke open and the dead climbed out of it. Brother Aled and Brother Cai... I hid "
          "under the cart. Some of them are still there among the stones. Ambermere is up the road. Tell Prioress "
          "Hildreth the cairn has opened. Something is very wrong.",
          do=[A.flag("met_ysolt"), A.stage("main", 1),
              q.journal("The autumn pilgrims were attacked by the dead from the roadside cairn below Ambermere. Sister "
                        "Ysolt survived and asked me to tell Prioress Hildreth at the chapel of the Mere.")],
          who="Ysolt")])

# Osmund: the gate
q.talker("Osmund", [
    q.say("The crown is back on its altar and the dead lie still. My watch walked the west road at dawn and found "
          "nothing but leaves. Here is the reward, and more than coin: the west gate is open. Thornwick is down "
          "that road, if you're bound for the King's Road.",
          when=q.when(flag="crown_laid", not_="osmund_paid"),
          do=[A.flag("osmund_paid"), A.gold(250), A.give("ChainTunic"), A.give("BluePotion", 2),
              A.unlock("WestGate1"), A.unlock("WestGate2"), A.enable("WestExit1"), A.enable("WestExit2"),
              A.enable("WestExit3"),
              q.journal("The Drowned Crown is back in the barrow and the dead sleep. Reeve Osmund paid me and opened "
                        "the west gate. The west road leads to Thornwick.", COMPLETED)], who="Osmund"),
    q.say("The gate's open. Ambermere won't forget you.", when=q.when(flag="osmund_paid"), who="Osmund"),
    q.say("Malvo dead and the crown in your hand? Then don't stand here; lay it back on the barrow's altar before "
          "nightfall.", when=q.when(has=CROWN), who="Osmund"),
    q.say("Hildreth will tell you what lies out there. I only know I've lost two watchmen on that road already.",
          when=q.when(flag="osmund_told"), who="Osmund"),
    q.say("A traveller, through all this? I am Osmund, reeve of Ambermere. If you meant to go on west to Thornwick, "
          "you'll wait: I've shut the west gate. Every night since the turn of the moon the dead walk the west road, "
          "and anyone who leaves by it walks to his grave. I won't open it until they're laid. Prioress Hildreth at "
          "the chapel knows the old barrows; she says she knows the cause. If you can end it, the town will pay.",
          do=[A.flag("osmund_told"), A.stage("main", 2),
              q.journal("Reeve Osmund has shut Ambermere's west gate, the road to Thornwick: the dead walk it by "
                        "night. He will not open it until they are laid. Prioress Hildreth at the chapel knows the "
                        "cause.", QUEST)], who="Osmund")])
# Hildreth: the cause, and the crown
q.talker("Hildreth", [
    q.say("The kings sleep again; I felt it, like a held breath let go. Bless you. Take the chapel's blessing with "
          "you: these remedies, and my prayers on the road.", when=q.when(flag="crown_laid", not_="hildreth_paid"),
          do=[A.flag("hildreth_paid"), A.give("CurePoisonPotion", 2), A.give("RedPotion", 2)], who="Hildreth"),
    q.say("Go with the Mere's grace.", when=q.when(flag="hildreth_paid"), who="Hildreth"),
    q.say("The Drowned Crown! Don't keep it a moment longer than you must. Take it back to the barrow and lay it on "
          "the altar under the old god's statue, where it lay for six hundred years.",
          when=q.when(has=CROWN), who="Hildreth"),
    q.say("The barrow is up the old kings' way, north-west past the barrow-field. The diggers' fire burns there "
          "still. Malvo will be in the crypt, among the kings.", when=q.when(flag="hildreth_told"), who="Hildreth"),
    q.say("The cairn opened? Then it has reached even the pilgrims' road. Listen. At the turn of the moon a band of "
          "diggers broke into the Barrow of the Lake-Kings, up the old kings' way in the red wood, after their "
          "amber. A necromancer came with them, Malvo, a pale man in black. He took the Drowned Crown from the "
          "barrow's altar. While it lay there the kings slept; in his hands it wakes every grave in the wood, and the "
          "dead dig for him. Kill him, bring back the crown and lay it on the altar again, and they will sleep.",
          do=[A.flag("hildreth_told"), A.stage("main", 3),
              q.journal("Prioress Hildreth says diggers broke into the Barrow of the Lake-Kings, up the old kings' way "
                        "in the red wood to the north-west, and a necromancer named Malvo took the Drowned Crown from "
                        "its altar. It raises the dead. I must kill Malvo and lay the crown back on the barrow's "
                        "altar.", QUEST)], who="Hildreth")])
q.on_death("Malvo", [A.drop(CROWN), A.drop("OrnateHelm"), A.flag("malvo_dead"),
                     A.print("Malvo crumples among the tombs. A crown of black gold and amber rolls from his hands, "
                             "and the helm of a dead king he had taken for himself."),
                     q.journal("Malvo the necromancer is dead and the Drowned Crown is free. It must go back on the "
                               "barrow's altar.", QUEST)])
q.on_pickup(CROWN, [q.journal("I have the Drowned Crown. It is cold as lake water. The altar is in the barrow's hall, "
                              "under the old god's statue.", QUEST)], when=q.when(not_="crown_laid"))
q.near(ax_, ay_, 80, [A.take(CROWN), A.flag("crown_laid"), A.enable("AltarLight"), A.spawn("DunMirFlameBasinLit",
                                                                                         "AltarBasin")] +
       [A.disable(n) for n in kings_guard + crypt_dead] + [          # the risen still standing sink down: gone
                      A.print("You lay the Drowned Crown on the altar. A flame leaps up in the cold basin, and all "
                              "through the barrow the dead sink down and are still."),
                      q.journal("I laid the Drowned Crown back on the barrow's altar. The dead sleep again. Reeve "
                                "Osmund will open the west gate.", QUEST)],
       when=q.when(has=CROWN, not_="crown_laid"))
q.near(*barrows_camp["fire"], 300, [A.print("Opened barrows, spoil heaps, a fire: the diggers' camp.")])
q.near(*square_px(*barrow_c), 330, [A.print("The Barrow of the Lake-Kings. Cold air breathes from its open door.")],
       when=q.when(flag="hildreth_told"))

# the gate guard and the watch
q.talker("GateGuard", [
    q.say("Gate's open, by the reeve's word. West road runs to Thornwick. Go safe.", when=q.when(flag="osmund_paid"),
          who="Guard"),
    q.say("Gate's shut by the reeve's order. You'd not want to walk that road after dark, believe me. Talk to Osmund "
          "in the Moot Hall.", who="Guard")])
for k_ in range(2):
    q.talker(f"Watch{k_ + 1}", [
        q.say("Quiet nights again. I'd almost forgotten what they were like.", when=q.when(flag="crown_laid"),
              who="Watch"),
        q.say("Keep to the town after dark. If you hear bones on the west road, don't go and look.", who="Watch")])
    q.portrait(f"Watch{k_ + 1}", ("Warrior3Pic", "IxGuard2Pic")[k_])

# the Amber Pits
q.on_all_dead(urchins, [A.flag("pits_clear"), A.print("The last urchin falls. The amber pits are quiet.")])
q.talker("Garth", [
    q.say("The pits are clear? The shaman too? Ha! My lads will be digging by noon. Here's the bounty, and boots "
          "fit for the pits; you've earned them.", when=q.when(flag=q.dead(*urchins), not_="garth_paid"),
          do=[A.flag("garth_paid"), A.gold(100), A.give("LeatherArmoredBoots"),
              q.journal("I cleared the amber pits of urchins. Garth the pit-boss paid me 100 gold.", COMPLETED)],
          who="Garth"),
    q.say("Amber's coming up again. Best colour in years.", when=q.when(flag="garth_paid"), who="Garth"),
    q.say("Down the pit road, south-west. Mind the shaman; he throws fire.", when=q.at("pits", 1), who="Garth"),
    q.say("You've the look of someone who can swing a blade. Urchins came up out of the old diggings and ran my "
          "diggers off the amber pits, and their shaman squats on our heaps like a toad. Clear them out, every one, "
          "and I'll pay a hundred gold.",
          do=[A.stage("pits", 1), q.journal("Garth the pit-boss will pay 100 gold to whoever clears the urchins and "
                                            "their shaman off the amber pits, down the pit road to the south-west.",
                                            QUEST)], who="Garth")])

# Pip in the Reeds
q.on_all_dead(spiders, [A.flag("spiders_dead"), A.print("The last spider curls up in the reeds.")])
q.talker("Pip", [
    q.say("I'm going home! Mam's going to kill me.", when=q.when(flag="pip_home"), who="Pip"),
    q.say("Are they dead? The big black one too? ...I'm going home. Thank you! Tell Mam I'm coming!",
          when=q.when(flag=q.dead(*spiders)),
          do=[A.flag("pip_home"), A.walk("Pip", pip_wps[0]),
              q.journal("Pip is walking home to his mother Morwen on the shore.", QUEST)], who="Pip"),
    q.say("Don't go out there! Spiders, big ones, all round the hut. I've been in here two days. I'm so hungry.",
          who="Pip")])
q.talker("Morwen", [
    q.say("Pip! He came in the door covered in reed-mud, and I've never been so glad to see dirt. Take this. It was "
          "his father's bow, before the mere took him. Pip will never use it, and you might.",
          when=q.when(flag="pip_home", not_="morwen_paid"),
          do=[A.flag("morwen_paid"), A.give("Bow"), A.give("Quiver"), A.gold(40),
              q.journal("I brought Pip home from the reed shore. Morwen gave me her late husband's bow.", COMPLETED)],
          who="Morwen"),
    q.say("He's asleep by the fire. He won't go egging again in a hurry.", when=q.when(flag="morwen_paid"), who="Morwen"),
    q.say("The reed shore's north of the mere, through the old wood. The old smokehouse; he always hides in there.",
          when=q.at("pip", 1), who="Morwen"),
    q.say("Have you seen my boy? Pip, so high, freckles? He went egging on the reed shore two days ago, north of the "
          "mere, and he hasn't come back. Old Tam says there are spiders out there now, big ones. Please. I'd go "
          "myself but I'd be no use.",
          do=[A.stage("pip", 1), q.journal("Morwen the net-mender's son Pip went egging on the reed shore north of the "
                                           "mere two days ago and has not come back. Spiders nest out there.",
                                           QUEST)], who="Morwen")])

# the Heart of the Mere
q.on_death("Grukk", [A.drop(HEART), A.print("The ogre falls across the shrine stones. A great red stone rolls from "
                                            "the pouch at his belt: the Heart of the Mere.")])
q.on_pickup(HEART, [A.stage("heart", 2), q.journal("I have the Heart of the Mere. Severin will pay for it, but old Rue "
                                                   "the herbwife says it belongs to the mere.", QUEST)],
            when=q.when(not_="heart_done"))
q.talker("Severin", [
    q.say("You gave it to that old witch? The finest stone on this shore, and she'll throw it in a lake.",
          when=q.at("heart", 4), who="Severin"),
    q.say("I'll have it cut by spring. They'll hear of the Heart of the Mere in Galava. A pleasure doing business.",
          when=q.at("heart", 3), who="Severin"),
    q.say("The Heart of the Mere! Look at the fire in it. Two hundred gold, as I said, counted out now. Will you sell?",
          when=q.when(has=HEART, not_="heart_done"), ask=True,
          do=[A.flag("heart_done"), A.take(HEART), A.gold(200), A.stage("heart", 3),
              q.journal("I sold the Heart of the Mere to Severin the amber-cutter for 200 gold.", COMPLETED)],
          else_=[A.chat("Severin", "Think it over. Nobody else on this shore can pay what I pay.")], who="Severin"),
    q.say("The shrine's on the north-east point, past the reed shore. The ogre wears the stone on his belt, they say.",
          when=q.at("heart", 1), who="Severin"),
    q.say("Severin, amber-cutter. You've a fighter's look. On the north-east point there's an old shrine where the "
          "lake-folk set a great red stone, the Heart of the Mere. An ogre and his grunts have made the shrine their "
          "lair, and he's taken the stone. Bring it to me and I'll pay two hundred gold. Nobody else will pay you "
          "half that.", when=q.when(not_="heart_done"),
          do=[A.stage("heart", 1), q.journal("Severin the amber-cutter will pay 200 gold for the Heart of the Mere, "
                                             "a great red stone an ogre took from the shrine on the north-east "
                                             "point, past the reed shore.", QUEST)], who="Severin")])
q.talker("Rue", [
    q.say("It's home. Feel the water already, how it moves. The eels will be back by the new moon.",
          when=q.at("heart", 4), who="Rue"),
    q.say("Sold it to Severin. Well. Stones go where gold goes. The mere will be empty a while yet.",
          when=q.at("heart", 3), who="Rue"),
    q.say("You have it. I can feel it from here, warm as a hearth. Severin will cut it into rings for Galava ladies. "
          "Give it to me, and I'll take it back to the shrine at dawn, where it belongs. I've no gold, but I have "
          "remedies, and the charm my mother made. Will you?",
          when=q.when(has=HEART, not_="heart_done"), ask=True,
          do=[A.flag("heart_done"), A.take(HEART), A.give("RedPotion", 3), A.give("CurePoisonPotion", 2),
              A.give("AmuletofNature"), A.gold(40), A.stage("heart", 4),
              q.journal("I gave the Heart of the Mere to old Rue, who will set it back on the shrine. She gave me "
                        "remedies and her mother's charm.", COMPLETED)],
          else_=[A.chat("Rue", "Then go to Severin, and the mere stays empty.")], who="Rue"),
    q.say("Since the ogre took the Heart from the shrine the eels have gone and the reeds are dying. The mere has "
          "lost its heart, child. Severin wants it for his cutting wheel. If it ever comes to your hand, bring it to "
          "me instead.", who="Rue")])

for who_, pic_ in (("Ysolt", "MaidenPic4"), ("Osmund", "TheogrinPic"), ("Hildreth", "MaidenPic"),
                   ("Severin", "MalePic11"), ("Garth", "Miner2Pic"), ("Morwen", "IngridPic"), ("Rue", "MaidenPic3"),
                   ("Pip", "MalePic12"), ("GateGuard", "Warrior2Pic")):
    q.portrait(who_, pic_)

m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())

# ---- 11. the exteriors' dressing: the empty ground filled with the town's and the wood's things --------------------------
dressed = Exterior(m, land, "green").dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed, os.path.join(OUT, f"{NAME}.rooms.json"), yards=[y_ for y_ in yards if y_.kind in built])
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| trees {n_trees} | shops {n_shops} | caches {len(caches)} | opened {len(opened)} | lines {len(q.strings)} "
          f"| yards {', '.join(built) or 'none'} | fish {fish} | dock {'yes' if dock else 'no'} "
          f"| dressing {sum(dressed.values())} groups")
