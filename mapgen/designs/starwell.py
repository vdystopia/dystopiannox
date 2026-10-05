"""Starwell: a wizards' college town in a silver birch wood, built round the well where a fallen star's heart lies,
and the story of the Stolen Star (a map of its own, loadable directly; its north road leads to Thornwick, chapter
one's map, mapgen/designs/thornwick.py). The green world in four sections: the silver wood of the town and the south
road (FORESTS["silver"]), the old brown wood of the herbarium and the quarry in the west (FORESTS["ancient"]), the
dark pines of the observatory's crag in the north-east (FORESTS["conifer"]) and the Scar, the bare crater where the
star fell, ringed by crystal rock (FORESTS["camp"]). The houses are built in Ix's manner (Westwood's wizards' town,
Wiz01A: dark-timbered stucco, StuccoDarkWood), the college in Galava's town stone, the old observatory in blue stone;
the square is paved in Ix's brick round the Starwell.

The story
- The player comes up the south road out of the wood. By the road stands the south ward-ring, seven stones round a
  star crystal that has always burned blue; it is dark, and imps flit among the stones. Magister Edda, the ward-keeper,
  kneels there trying to wake it: every ward round Starwell went out three nights ago, when the Starwell itself went
  dark. The imps come for whoever passes. She sends the player up to the Archmagister.
- Starwell: a square paved in Ix's brick round the Starwell; the College of the Star (its hall, library, laboratory
  and the Archmagister's study), Ottilie's apothecary, the Fallen Star inn, the forge, the watch house, the houses;
  a park and the old graveyard; the herbarium in the west wood, the masons' quarry in the north-west, the old
  observatory on the crag in the north-east, the Scar in the east wood; the north gate on the road to Thornwick.
- Main quest, the Stolen Star (a sealed place broken open, a boss, the object brought home to light the town):
  Archmagister Aldous has sealed the north gate with a word: with the wards dark, the north road is the way the
  wood's summoned things come in. Magister Morvane, master of the stars, took the Starstone, the fallen star's heart,
  out of the Starwell three nights ago and shut himself in the old observatory on the crag, behind the old College's
  lock: three binding-stones on the crag hold its door, and Morvane has set a summoned thing to keep each. Magister
  Quill the librarian knows the lock. The player breaks the three bindings (their purple light goes out as each
  keeper falls), the door opens, and Morvane dies in his workroom among his summoned guard. Lowered back into the
  Starwell, the Starstone lights the town and every ward again; Aldous pays and opens the north gate.
- Weeds of the Herbarium (a bounty on a place gone wrong): Ottilie the alchemist's herbarium in the west wood ran
  wild when the wards failed: her man-eating plants broke their beds and the wasps' hive split. She pays in potions,
  a charm and gold when the beds are cleared.
- Old Hob (a beast to put down, with a reason): the masons cut the College's stone with Old Hob, a stone golem the
  College bound three hundred years ago. With the Starwell dark his binding slipped, and he strikes at anyone who
  comes into the quarry. Master Harl, who has worked beside him forty years, asks the player to put him down.
- The Diggers in the Scar (a choice between a bribe and the law): Vask's band of star-iron diggers are digging the
  Scar, the crater east of town where the star fell, which is the College's ground. Captain Brannoc of the watch
  wants them driven out. Vask offers the player a purse to say they found nobody: take it, and the diggers dig on
  and Brannoc pays nothing; refuse, and the diggers take up their picks against the player, and Brannoc pays.
- The apothecary, the forge and the inn buy and sell. The diggers' chest, three caches in the wood and the
  houses' and the observatory's stores hold loot; every soul in town knows something.
- The exit: the north road beyond the north gate leads to Thornwick.

    py mapgen/designs/starwell.py [seed]
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

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 4
rng = random.Random(SEED)
NAME = "Starwell"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "starwell")
NEXT_MAP = "Thornwick"                # the north road runs down to Thornwick
STAR = "Orb"                          # the Starstone, the fallen star's heart (things: LIGHT, SIMPLE; Westwood's orb)
HOUSE = "stucco_dark_house"           # Ix's dark-timbered stucco


def uv(X, Y):
    """uv of a point given in map squares as seen on screen (X right, Y down, 0..255)."""
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="a wizards' college town in a silver birch wood, built round the Starwell where a fallen star's heart lies: "
          "a square of Ix brick round the well, the College of the Star, an apothecary, an inn, the forge and the "
          "watch house, houses of dark-timbered stucco; the herbarium and the masons' quarry in the west wood, the old "
          "observatory on the north-east crag, the Scar where the star fell in the east wood; the north gate sealed on "
          "the road to Thornwick",
    environment="town", mood="hushed, uneasy, starlit",
    areas=[AreaIdentity("south", "the south road out of the wood and the dark south ward-ring: the start"),
           AreaIdentity("town", "Starwell's square and its streets", landmark="Well"),
           AreaIdentity("herb", "the College's herbarium in the west wood, its plants run wild"),
           AreaIdentity("quarry", "the masons' quarry in the north-west, where Old Hob stands"),
           AreaIdentity("gate", "the north gate, sealed"),
           AreaIdentity("north", "the north road on to Thornwick: the way out"),
           AreaIdentity("crag", "the climb to the old observatory, below its binding-stones"),
           AreaIdentity("bind1", "the west binding-stone"), AreaIdentity("bind2", "the south binding-stone"),
           AreaIdentity("bind3", "the east binding-stone"),
           AreaIdentity("observ", "the old observatory on its crag, sealed"),
           AreaIdentity("scar", "the Scar, the crater where the star fell, and the diggers' camp")],
    buildings=[BuildingIdentity("college", "town", "the College of the Star", "Archmagister Aldous and the magisters"),
               BuildingIdentity("apothecary", "town", "Ottilie's apothecary", "Ottilie the alchemist"),
               BuildingIdentity("inn", "town", "The Fallen Star", "the innkeeper", style=HOUSE),
               BuildingIdentity("smithy", "town", "the forge", "the smith"),
               BuildingIdentity("barracks", "town", "the watch house", "Captain Brannoc and the watch"),
               BuildingIdentity("home", "town", "", "Master Harl the mason", style=HOUSE),
               BuildingIdentity("home", "town", "", "a scribe's family", style=HOUSE),
               BuildingIdentity("home", "town", "", "a glass-blower's family", style=HOUSE),
               BuildingIdentity("home", "town", "", "a candle-maker's family", style=HOUSE),
               BuildingIdentity("cottage", "town", "", "an old star-reader", style=HOUSE),
               BuildingIdentity("cottage", "town", "", "a widow who binds books", style=HOUSE),
               BuildingIdentity("herbwife", "herb", "the herbarium's potting house", "the herbarium's gardener"),
               BuildingIdentity("observatory", "observ", "the old observatory", "Magister Morvane, now")])

m = Spec(NAME, summary="Starwell", description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"Generated by Claude.", author="vdystopia (generated by Claude)", version="1", date="2026", type=SOLO,
         minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [124, 132, 156]           # a cool, starlit light
q = QuestBook(NAME)

# sections: each its own forest (walls, trees, undergrowth) and ground (base, sparse, dense)
REGIONS = dict(
    silver=dict(forest="silver", ground=("GrassNorm", "GrassSparse2", "GrassDense")),
    old=dict(forest="ancient", ground=("GrassDense", "GrassNorm", "GrassSparse2")),
    pine=dict(forest="conifer", ground=("GrassSparse2", "GrassNorm", "GrassDense")),
    scar=dict(forest="camp", ground=("DirtLight2", "GrassSparse2", "DirtDark2")),
)
SECTION = {"south": "silver", "town": "silver", "gate": "silver", "north": "silver", "herb": "old", "quarry": "old",
           "crag": "pine", "bind1": "pine", "bind2": "pine", "bind3": "pine", "observ": "pine", "scar": "scar"}


def section(r):
    """The section of a region name: an area's own, or a passage's side pocket's (pocket_<a>_<b>_<k>), its first end's."""
    if r in REGIONS: return r
    for part in (r or "").split("_")[1:]:
        if part in SECTION: return SECTION[part]
    return "silver"


# ---- 1. the plan: the south road up to the town, the north road out, the ways to the wild places ---------------------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"south": ((150, 234), 18), "town": ((122, 136), 66), "herb": ((30, 196), 28), "quarry": ((38, 62), 28),
         "gate": ((104, 56), 12), "north": ((92, 26), 12), "crag": ((174, 80), 26), "bind1": ((146, 44), 12),
         "bind2": ((202, 108), 12), "bind3": ((230, 74), 12), "observ": ((208, 36), 38), "scar": ((214, 170), 32)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "town", region=SECTION[k_])
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_, bend_ in (("south", "town", 14, True, 0.18), ("town", "gate", 13, True, 0.12),
                                 ("gate", "north", 12, True, 0.12), ("town", "herb", 12, True, 0.22),
                                 ("town", "quarry", 12, True, 0.2), ("town", "crag", 12, True, 0.2),
                                 ("crag", "observ", 12, True, 0.15), ("crag", "bind1", 9, False, 0.25),
                                 ("crag", "bind2", 9, False, 0.25), ("crag", "bind3", 9, False, 0.25),
                                 ("town", "scar", 11, False, 0.22), ("south", "scar", 12, False, 0.28),
                                 ("herb", "quarry", 13, True, 0.3)):
    land.link(a_, b_, w_, bend=bend_, road=road_, pockets=(1, 2) if road_ else (0, 1))
land.blends(m)
m.blending("IxBrickFancy", 6, "BlendEdge")          # the square's Ix brick, as Westwood edges it (Wiz01A, War03b)

# ---- 2. the centre: the square round the Starwell, the roads leaving it ------------------------------------------------
vc = land.areas["town"]["c"]
land.paint_square(m, "town", 12, "IxBrickFancy")
land.taken |= {(int(vc[0]) + a, int(vc[1]) + 1 + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}
obs_c0 = land.areas["observ"]["c"]                 # the star road stops short of the observatory's door
land.paint_roads(m, "DirtLight2", width_squares=2.8,
                 skip=land.reserved | {(i, j) for i in range(int(obs_c0[0]) - 16, int(obs_c0[0]) + 17)
                                       for j in range(int(obs_c0[1]) - 16, int(obs_c0[1]) + 17)
                                       if math.hypot(i - obs_c0[0], j - obs_c0[1]) < 12})

# ---- 3. buildings from the square outwards; none on the wild places --------------------------------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"south": 9, "quarry": 15, "crag": 13, "bind1": 7, "bind2": 7, "bind3": 7,
                                      "scar": 17},
                            first=("herb",), centred={"observ": "crag"})
by_role = sm.by_role
sm.connect_and_furnish(path_material="DirtLight2")

# the yards: the herbarium's beds, the masons' quarry, the town's park and its old graveyard
yards = []


def ring_of(c, radii):
    return [(c[0] + r * math.cos(a * math.pi / 6), c[1] + r * math.sin(a * math.pi / 6)) for r in radii for a in range(12)]


for kind_, area_, rs_, toward_ in (("field", "herb", (5, 7, 9, 11), "town"), ("quarry", "quarry", (0, 3, 6), "town"),
                                   ("park", "town", (14, 18, 22, 26, 30, 34, 38), "town"),
                                   ("graveyard", "town", (26, 30, 34, 38, 42, 46), "town")):
    y_ = Y.plan_any(land, rng, kind_, ring_of(land.areas[area_]["c"], rs_), toward=land.areas[toward_]["c"])
    if y_: yards.append(y_)
    else: print(f"no room for the {kind_}")
herb_beds = next((y_ for y_ in yards if y_.kind == "field"), None)
pit_yard = next((y_ for y_ in yards if y_.kind == "quarry"), None)

# ---- 4. the land grows round everything, ending in the forest wall ---------------------------------------------------
land.carve(margin=3.5)
lane_ = sm.keep_open({"south": 5, "quarry": 7, "crag": 4, "bind1": 4, "bind2": 4, "bind3": 4, "scar": 10, "herb": 4})
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

# the north gate: a wall of grey stone across the road from forest to forest, a sealed double gate in it
gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "north"), prefix="NorthGate")

# ---- 5. the town's life ------------------------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Fallen Star\nSupper, ale and a bed under the stars", "Sign"),
                     smithy=q.text("The Forge\nBlades, mail and mending", "Sign"),
                     apothecary=q.text("Ottilie's Apothecary\nRemedies, philtres, wands", "Sign"),
                     college=q.text("THE COLLEGE OF THE STAR\nFounded where the star fell.", "Sign"),
                     barracks=q.text("The Watch House", "Sign"))
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
south_c, herb_c, quarry_c, crag_c, observ_c, scar_c, north_c, gate_c = (
    C[k] for k in ("south", "herb", "quarry", "crag", "observ", "scar", "north", "gate"))


def off_road(c, clear=4.5, reach=12):
    """The square nearest `c` with no road within `clear` squares, on open land: a place beside its way, not on it."""
    near_road = bfs_distance(list(land.roads), land.squares, int(clear) + 1)
    fenced = set().union(*({(y_.gi + a, y_.gj + b) for a in range(-2, y_.w + 2) for b in range(-2, y_.h + 2)}
                           for y_ in yards))
    cands = [s for s in land.squares if near_road.get(s, 99) >= clear and s not in land.taken_strict and
             s not in fenced and s not in land.water and math.hypot(s[0] - c[0], s[1] - c[1]) <= reach]
    s = min(cands, key=lambda s: math.hypot(s[0] - c[0], s[1] - c[1])) if cands else (int(c[0]), int(c[1]))
    return (s[0] + 0.5, s[1] - 0.5)


# the Starwell's light, dark until the Starstone is home: a blue glow, star crystals round the well's foot
m.obj_px("ColorLight", well_xy[0], well_xy[1] - 6, xfer=dict(preset("blue")), scr="StarLight")
wsc = camps.Scene(m, rng, land, (vc[0] + 0.5, vc[1] - 0.5))
for k_ in range(3):
    o_ = m.obj_px(("MineCrystal02", "MineCrystal04", "MineCrystal05")[k_],
                  *square_px(vc[0] + 0.5 + 1.0 * math.cos(k_ * 2.1 + 0.5), vc[1] - 0.5 + 1.0 * math.sin(k_ * 2.1 + 0.5)))
# the south ward-ring beside the road, up from where the player comes out of the wood
toward_town = math.atan2(vc[1] - south_c[1], vc[0] - south_c[0])
ward_c = off_road((south_c[0] + 7 * math.cos(toward_town), south_c[1] + 7 * math.sin(toward_town)), clear=3.5, reach=9)
ward_xy = camps.stone_ring(m, rng, land, ward_c, n=7, radius=2.6, stone="ObeliskPrimitive", core="MineCrystal03",
                           light=preset("blue"), light_name="SouthWard", clear=3)
# the herbarium: the beds gone wild round the potting house
herb_bed_c = herb_beds.centre if herb_beds and "field" in built else herb_c
# the quarry: Old Hob in the cut; the masons' blocks and tools left where they dropped them
pit_c = pit_yard.centre if pit_yard and "quarry" in built else quarry_c
qsc = camps.Scene(m, rng, land, quarry_c)
for k_, (r_, a_) in enumerate(((6.5, 0.3), (7.0, 1.4), (6.0, 2.6))):
    qsc.put(("SmallStoneBlock", "SmallStoneBlock", "MiningPickAxeInGround1")[k_], *qsc.at(r_, a_))
# the three binding-stones on the crag: four obelisks round a star crystal each, burning purple while bound
bind_xy = []
for k_ in (1, 2, 3):
    bc_ = off_road(C[f"bind{k_}"], clear=1.5, reach=4)
    bind_xy.append(camps.stone_ring(m, rng, land, bc_, n=4, radius=1.8, stone="ObeliskPrimitive", core="MineCrystal01",
                                    light=preset("purple"), light_name=f"Binding{k_}", clear=3))
# the Scar: the diggers' camp on the crater's floor, their diggings among the star's shards
scar_camp = camps.bandit_camp(m, rng, land, off_road(scar_c, clear=4.5, reach=10), vc,
                              loot=[("Gold", {"Amount": 70}), "RedPotion", "RedPotion", "BluePotion", "Quiver"],
                              sleepers=4, tents=2)
dig = camps.Scene(m, rng, land, scar_c)
for k_, (r_, a_, t_) in enumerate(((9.0, 3.6, "MiningPickAxeInGround1"), (9.5, 4.2, "MineCrystal03"),
                                   (8.5, 4.8, "MiningShovelInGround"), (10.0, 5.3, "MineCrystal05"),
                                   (9.0, 2.9, "MineCrystal01"), (10.5, 3.2, "BarrelWithTools1"))):
    dig.put(t_, *dig.at(r_, a_))
# caches in the wood, off the ways
caches = []
for near_, loot_, stump_ in ((herb_c, [("Gold", {"Amount": 45}), "CurePoisonPotion", "RedPotion"], True),
                             (quarry_c, [("Gold", {"Amount": 50}), "LeatherBoots", "BluePotion"], False),
                             (scar_c, [("Gold", {"Amount": 40}), "RedPotion", "SpellBook"], False)):
    s_ = sm.hidden_spot(near_, r=(9, 16))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
# signposts
camps.signpost(m, land, (south_c[0] + 2.5, south_c[1] - 1.5),
               q.text("STARWELL\nUp the road, where the star fell.\nThe College of the Star welcomes the learned.", "Sign"))
gs_ = sm.road_near(((gate_sq[0] * 2 + vc[0]) / 3, (gate_sq[1] * 2 + vc[1]) / 3))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 1.5),
               q.text("THE NORTH GATE IS SEALED\nUntil the Starwell burns again.\n- Aldous, Archmagister", "Sign"))
cr_ = sm.road_near(((crag_c[0] + vc[0]) / 2, (crag_c[1] + vc[1]) / 2))
camps.signpost(m, land, (cr_[0] + 2.0, cr_[1] - 1.5), q.text("THE OLD OBSERVATORY\nClosed by order of the College.", "Sign"))
qr_ = sm.road_near(((quarry_c[0] + vc[0]) / 2, (quarry_c[1] + vc[1]) / 2))
camps.signpost(m, land, (qr_[0] + 2.0, qr_[1] - 1.5), q.text("THE QUARRY\nKeep clear of Old Hob.", "Sign"))

# ---- 7. lights and planting -----------------------------------------------------------------------------------------
keep = set()
for bid, b in placed:
    for d in b.entrances:
        di, dj = px_square(*d.px)
        keep |= {(di + a, dj + b2) for a in range(-2, 3) for b2 in range(-2, 3)}
vil.ground_bits(1.4)
planter = Planter(m, rng, land, "silver", keep_clear=keep | lane_, settled=("town",),
                  forest_of=lambda s: REGIONS[section(land.region_of(s))]["forest"])
n_trees, n_small = planter.plant_all(groves=4, profile=TOWN_PLANTING)
piles = planter.rock_piles(max(4, len(land.squares) // 900))
vignettes = planter.forest_floor(max(6, len(land.squares) // 700))
start_xy = square_px(south_c[0] + 0.5, south_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
sm.exit_to("north", NEXT_MAP, prefix="NorthExit")

# ---- 8. the people --------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
person, room_of, free_px = sm.person, sm.room_of, sm.free_px
vx, vy = square_px(*vc)
# Magister Edda at the dark ward-ring, between the road and the stones
ex_, ey_ = square_px(ward_c[0] + 3.6 * math.cos(toward_town + math.pi), ward_c[1] + 3.6 * math.sin(toward_town + math.pi))
person("Wiz02A", "TowerMaiden", ex_, ey_, "Edda", face=start_xy)
# Archmagister Aldous in the College's hall, Magister Quill among his books, Ottilie at her shop door
hall = room_of("college", "throne_room") or room_of("college", "library")
ax_, ay_ = free_px(hall) if hall else (vx, vy)
person("Wiz02A", "TowerNPC", ax_, ay_, "Aldous")
lib = room_of("college", "library")
qx_, qy_ = free_px(lib, clear=26) if lib else (vx + 40, vy)
person("Wiz02A", "TowerNPC2", qx_, qy_, "Quill")
ot_ = sm.outside_door("apothecary") or (vx + 60, vy)
person("Wiz02A", "Eowynn", ot_[0] + 18, ot_[1] + 14, "Ottilie", face=(vx, vy))
# Captain Brannoc at the watch house door
br_ = sm.outside_door("barracks") or (vx - 60, vy)
person("Wiz02A", "Warden", br_[0] - 16, br_[1] + 16, "Brannoc", face=(vx, vy))
# Master Harl on the quarry road at the edge of town
hr_ = sm.road_near(((quarry_c[0] + vc[0] * 2) / 3, (quarry_c[1] + vc[1] * 2) / 3))
hsc = camps.Scene(m, rng, land, (hr_[0], hr_[1]))
hpos = None
for da_ in (1.8, -1.8, 2.6, -2.6):
    p_ = (hr_[0] + 0.5 + da_ * 0.7, hr_[1] - 0.5 - da_ * 0.7)
    if hsc.ok(*p_):
        hpos = square_px(*p_); break
hx_, hy_ = hpos or square_px(hr_[0] + 2.5, hr_[1] - 0.5)
person("War01A", "QuarterMaster", hx_, hy_, "Harl", face=square_px(*quarry_c))
# the gate guard, on the town side of the north gate
gq_ = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
gdx, gdy = vx - gq_[0], vy - gq_[1]
gl = math.hypot(gdx, gdy) or 1
person("Con02a", "IxGuard1", gq_[0] + 70 * gdx / gl + 26, gq_[1] + 70 * gdy / gl, "GateWarden", face=(vx, vy))
# Vask's diggers in the Scar: men at their posts round the camp, each with the fighter he turns into hidden at his spot
dig_posts = camp_posts(m, scar_camp, (vx, vy), sit=2, tents=1, watch=1)
diggers, digger_foes = ["Vask"], ["VaskFoe"]
person("Con03A", "Rastur", *dig_posts["leader"], "Vask", face=(vx, vy))
pop.creature("Swordsman", dig_posts["leader"][0] + 6, dig_posts["leader"][1] + 6, action="guard", scr="VaskFoe",
             aggr=0.83, HealthMultiplier=2.5, spread=False)
for k, ((x, y), donor_, foe_) in enumerate(zip(dig_posts["sit"] + dig_posts["tent"] + dig_posts["watch"],
                                              (("War01A", "Jesse"), ("War01A", "Daniel"), ("War01A", "Eric"),
                                               ("War01A", "Tyler")),
                                              ("Swordsman", "Swordsman", "Swordsman", "Archer"))):
    n = f"Digger{k + 1}"
    person(donor_[0], donor_[1], x, y, n, face=scar_camp["fire"])
    pop.creature(foe_, x + 6, y + 6, action="guard", scr=f"DiggerFoe{k + 1}", aggr=0.83, spread=False)
    diggers.append(n); digger_foes.append(f"DiggerFoe{k + 1}")
# shopkeepers
WARES = {"apothecary": [(5, "RedPotion"), (4, "BluePotion"), (3, "CurePoisonPotion"), (1, "LesserFireballWand"),
                        (1, "ForceWand"), (2, "SpellBook"), (1, "WizardRobe"), (1, "WizardHelm")],
         "inn": [(6, "RedApple"), (5, "Meat"), (4, "Cider"), (4, "Bread"), (2, "RedPotion")],
         "smithy": [(2, "Sword"), (1, "Longsword"), (1, "BattleAxe"), (1, "WarHammer"), (1, "WoodenShield"),
                    (1, "SteelShield"), (1, "ChainCoif"), (1, "ChainTunic"), (1, "ChainLeggings"), (1, "LeatherBoots")]}
GREET = {"apothecary": q.text("Ottilie's apothecary. Remedies, philtres, a wand or two for the road. Mind the jars; "
                              "some of them bite.", "Shop"),
         "inn": q.text("Welcome to the Fallen Star. Sit anywhere but the window seat; that's the old star-reader's, "
                       "and he's been sitting in it fifty years.", "Shop"),
         "smithy": q.text("The forge. The College makes the wards; I make what you hit things with when the wards "
                          "fail.", "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"apothecary": "ShopkeeperMagicShop", "smithy": "ShopkeeperWarriorsRealm"})
# townsfolk on their rounds, each with something to tell
FOLK = [("Wiz02A", "Albi"), ("Wiz02A", "Maiden2"), ("Wiz02A", "Kelvin"), ("Wiz02A", "Maiden5"),
        ("Wiz02A", "Fenton"), ("Wiz02A", "Maiden8"), ("Wiz02A", "Jorgan"), ("Con08a", "Apprentice")]
RUMOURS = [
    "The Starwell went dark three nights ago. Three hundred years it burned, and now look at it: just a well.",
    "Magister Morvane left the College the same night the well went dark. Took his star charts, they say, and "
    "something else besides.",
    "There's a light in the old observatory on the crag at night. Nobody's used it since my grandmother's day.",
    "Ottilie won't go near her herbarium in the west wood. Says her plants got loose. Plants!",
    "Old Hob stands in the quarry swinging at anyone who comes near. He was gentle as a lamb, Hob, for three hundred "
    "years.",
    "There's a camp of diggers in the Scar, east of town, where the star fell. Captain Brannoc's spitting nails about it.",
    "Imps in the wood. Little burning things. They never came past the wards before.",
    "The Archmagister sealed the north gate with a word. Nobody goes to Thornwick till the Starwell burns again.",
]
for c_, r_ in ((scar_c, 16), (quarry_c, 14), (herb_c, 12), (crag_c, 14), (ward_c, 8)):    # folk keep off foes' ground
    sm.keep_folk_away(c_, r_)
ring = sm.townsfolk(FOLK, vc, q=q, rumours=RUMOURS,
                    after=("star_lit", "Look at the well! You can read by it again. The College says you brought the "
                                       "star home. The north gate's open, too."),
                    pics=("MalePic14", "MaidenPic2", "FentonPic", "MaidenPic3", "Townsman1Pic", "MaidenPic6",
                          "MalePic10", "WoundedApprenticePic"),
                    radius=7.0)
# the watch, each on a beat through the town
for k_, donor_ in enumerate(("IxGuard2", "Mayor's_Guard")):
    wx2, wy2 = ring[k_ * 4]
    person("Con02a", donor_, wx2, wy2, f"Watch{k_ + 1}", action=0)
    sm.beat(f"Watch{k_ + 1}", vc, radius=7.0, stops=7)

# ---- 9. the fights ----------------------------------------------------------------------------------------------------
# the imps at the dark ward-ring, who come for whoever passes on the road
ward_imps = []
for k, a in enumerate((0.6, 2.2, 3.8, 5.2)):
    x, y = square_px(ward_c[0] + 3.4 * math.cos(toward_town + a), ward_c[1] + 3.4 * math.sin(toward_town + a))
    n = f"WardImp{k + 1}"
    pop.creature("FireSprite" if k == 3 else "Imp", x, y, action="idle", face=start_xy, scr=n, aggr=0.5, sight=80)
    ward_imps.append(n)
# the herbarium's man-eating plants on and round the beds, the wasps out of the split hive
hsc2 = camps.Scene(m, rng, land, herb_bed_c)
plants = []
for k, (r_, a_) in enumerate(((0.8, 0.4), (2.6, 1.6), (2.6, 3.2), (2.8, 4.6), (4.6, 5.8), (4.4, 2.4))):
    x, y = hsc2.px(r_, a_)
    n = f"HerbPlant{k + 1}"
    pop.creature("CarnivorousPlant", x, y, action="guard", scr=n, aggr=0.83)
    plants.append(n)
wasps = []
for k, a_ in enumerate((0.9, 3.0, 5.1)):
    x, y = hsc2.px(6.5, a_)
    n = f"HerbWasp{k + 1}"
    pop.creature("Wasp", x, y, action="guard", scr=n, aggr=0.83)
    wasps.append(n)
# Old Hob in the quarry's cut
hob_xy = square_px(pit_c[0], pit_c[1] - 0.5)
pop.creature("StoneGolem", *hob_xy, action="guard", scr="OldHob", aggr=0.83, face=(vx, vy))
# the bindings' keepers: a summoned thing or two at each stone
binders = {1: ("FlyingGolem", "FlyingGolem"), 2: ("WillOWisp",), 3: ("EmberDemon", "EmberDemon")}
bind_keepers = {}
for k_, (bx_, by_) in zip((1, 2, 3), bind_xy):
    names_ = []
    for j, t_ in enumerate(binders[k_]):
        a_ = j * math.pi + 0.8
        n = f"Binder{k_}{chr(65 + j)}"
        pop.creature(t_, bx_ + 72 * math.cos(a_), by_ + 72 * math.sin(a_), action="guard", scr=n, aggr=0.83,
                     face=square_px(*crag_c))
        names_.append(n)
    bind_keepers[k_] = names_
all_binders = [n for k_ in (1, 2, 3) for n in bind_keepers[k_]]
# the observatory: sealed; Morvane's summoned guard in the star-chamber and the library, Morvane in his workroom
obs = sm.building_in("observ")
assert obs, "the observatory was not built"
obs_door = sm.seal_entrance(obs, "ObsDoor")
star_hall = room_of("observatory", "hall")
work = room_of("observatory", "laboratory")
charts = room_of("observatory", "library")
assert star_hall and work and charts, "the observatory's rooms were not built"
hall_guard = sm.keepers(star_hall, ("FlyingGolem", "Imp", "EvilCherub", "Imp", "FlyingGolem"), "StarGuard")
chart_guard = sm.keepers(charts, ("EvilCherub", "Imp", "EvilCherub"), "ChartGuard")
work_guard = sm.keepers(work, ("EmberDemon", "Shade"), "WorkGuard")
mx_, my_ = free_px(work, clear=26)
pop.creature("Wizard", mx_, my_, action="guard", scr="Morvane", aggr=0.83, HealthMultiplier=3.0)
# the wood's own creatures by the forest's edge: imps and sprites drawn in since the wards went dark
sm.wild({"Imp": 3, "Bat": 3, "Wolf": 2, "SmallAlbinoSpider": 2, "FireSprite": 1}, away_from=vc, per100=0.4, gap=7,
        min_away=36, avoid=(south_c, herb_c, quarry_c, crag_c, observ_c, scar_c, north_c, gate_sq, ward_c,
                            C["bind1"], C["bind2"], C["bind3"]) +
                           tuple((observ_c[0] + 11 * math.cos(a), observ_c[1] + 11 * math.sin(a))     # the crag behind
                                 for a in (0, 1.57, 3.14, 4.71)))                                     # the observatory

story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]] + \
           [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)

# ---- 10. the story ----------------------------------------------------------------------------------------------------
q.start([A.lock("NorthGate1"), A.lock("NorthGate2"), A.disable("NorthExit1"), A.disable("NorthExit2"),
         A.disable("NorthExit3"), A.disable("StarLight"), A.disable("SouthWard")] +
        [A.lock(n) for n in obs_door] + [A.disable(n) for n in digger_foes] +
        [q.journal("The south road climbs out of a silver birch wood toward Starwell, the wizards' town where a star "
                   "once fell.", HINT)])

# the ward-ring: the imps come for whoever passes on the road
q.near(*ward_xy, 190, [A.hunt(n) for n in ward_imps] + [A.print("Sparks scatter from the dark stones: imps!")])
q.on_all_dead(ward_imps, [A.flag("ward_clear"), A.print("The last imp winks out among the stones.")])
q.talker("Edda", [
    q.say("Gone, all of them? Then I can work in peace, for what good it does. Take these, and my thanks; a "
          "ward-keeper's wage doesn't run to much more.", when=q.when(flag=q.dead(*ward_imps), not_="edda_paid"),
          do=[A.flag("edda_paid"), A.give("RedPotion", 2), A.give("BluePotion"), A.gold(30),
              q.journal("I cleared the imps from the south ward-ring. Magister Edda gave me potions and her wage.",
                        COMPLETED)], who="Edda"),
    q.say("It burns! Blue as the day it was set. Whatever you did up there, the whole ring sang with it.",
          when=q.when(flag="star_lit"), who="Edda"),
    q.say("Go on up to the College. Archmagister Aldous is in the Hall of the Star. Tell him the south ring is dead.",
          when=q.when(flag="met_edda"), who="Edda"),
    q.say("Careful, traveller! Don't go near the stones. This is the south ward-ring; for three hundred years it has "
          "burned blue and kept the wood's wild things out of Starwell. Three nights ago it went dark, and every other "
          "ward with it, the night the Starwell itself went out. Now imps nest in the stones and come for anyone on "
          "the road. Go up to the town, to the College. The Archmagister will want every pair of hands.",
          do=[A.flag("met_edda"), A.stage("main", 1),
              q.journal("The wards round Starwell went dark three nights ago, when the Starwell itself went out. "
                        "Magister Edda, the ward-keeper at the south ward-ring, sent me up to the College of the Star "
                        "to see Archmagister Aldous.")], who="Edda")])

# Aldous: the main quest and the gate
q.talker("Aldous", [
    q.say("The Starwell burns. I felt it in my bones before I heard the bells. Starwell owes you its light, and I owe "
          "you more than this, but take it: the College's thanks, a robe of the College and gold. And the north gate "
          "is open; the road runs down to Thornwick.",
          when=q.when(flag="star_lit", not_="aldous_paid"),
          do=[A.flag("aldous_paid"), A.gold(250), A.give("WizardRobe"), A.give("BluePotion", 2), A.give("RedPotion", 2),
              A.unlock("NorthGate1"), A.unlock("NorthGate2"), A.enable("NorthExit1"), A.enable("NorthExit2"),
              A.enable("NorthExit3"),
              q.journal("The Starstone is back in the Starwell and the wards burn again. Archmagister Aldous paid me "
                        "and opened the north gate. The north road leads to Thornwick.", COMPLETED)], who="Aldous"),
    q.say("The gate is open, and Starwell's door is yours whenever you pass this way.", when=q.when(flag="aldous_paid"),
          who="Aldous"),
    q.say("You have it! The Starstone. Don't bring it to me: take it to the well in the square and give it back to "
          "the water. It knows the way down.", when=q.when(has=STAR), who="Aldous"),
    q.say("The old observatory is up the crag road, north-east of the square. Quill knows the old College's lock; "
          "speak to him in the library if the stones defeat you.", when=q.when(flag="aldous_told"), who="Aldous"),
    q.say("Edda sent you? Then you know the wards are dark. Here is the rest. Three nights ago Magister Morvane, our "
          "master of the stars, lifted the Starstone, the heart of the star that fell here, out of the Starwell. He "
          "means to read the sky with it, and he does not care that it is all that keeps the wood's wild things out. "
          "He has shut himself in the old observatory on the crag, behind the old College's lock. I have sealed the "
          "north gate: with the wards dark that road is how the summoned things come in. Bring the star home and the "
          "gate opens.",
          do=[A.flag("aldous_told"), A.stage("main", 2),
              q.journal("Magister Morvane took the Starstone out of the Starwell and has shut himself in the old "
                        "observatory on the crag, north-east of the square. Archmagister Aldous has sealed the north "
                        "gate until the star is brought home to the well. Magister Quill in the College library knows "
                        "the observatory's lock.", QUEST)], who="Aldous")])
q.talker("Quill", [
    q.say("The well burns and my lamp is out for the first time in three nights. Here: the College's book of the "
          "stars. Morvane would have wanted someone to read it who isn't Morvane.",
          when=q.when(flag="star_lit", not_="quill_paid"),
          do=[A.flag("quill_paid"), A.give("SpellBook"), A.give("BluePotion", 2)], who="Quill"),
    q.say("I'll be cataloguing his notes for a year.", when=q.when(flag="quill_paid"), who="Quill"),
    q.say("The door stands open? Then the bindings are broken. Morvane will be in the workroom at the back; he always "
          "worked with his back to the door, the fool.", when=q.when(flag="seal_broken"), who="Quill"),
    q.say("The old College's lock: three binding-stones on the crag round the observatory, west, south and east of "
          "the climb, each burning purple while it holds. The door opens only when all three are dark. Morvane has "
          "set one of his summoned things to keep each stone. Kill the keeper and the stone goes out.",
          when=q.when(flag="aldous_told"),
          do=[A.flag("quill_told"),
              q.journal("Magister Quill says three binding-stones on the crag hold the observatory's door: west, south "
                        "and east of the climb. Each is kept by one of Morvane's summoned things; when a keeper dies "
                        "its stone goes dark, and when all three are dark the door opens.", QUEST)], who="Quill"),
    q.say("Quill, librarian. If you're here for the books, they're in order. If you're here about the well, see the "
          "Archmagister.", who="Quill")])
for k_ in (1, 2, 3):
    q.on_all_dead(bind_keepers[k_], [A.disable(f"Binding{k_}"), A.advance("bindings"),
                                     A.print("The binding-stone's purple fire gutters and goes out.")])
q.on_all_dead(all_binders, [A.flag("seal_broken")] + [A.unlock(n) for n in obs_door] +
              [A.print("Far up the crag, the observatory's door groans open."),
               q.journal("All three binding-stones are dark, and the old observatory's door has opened.", QUEST)])
q.near(*square_px(*crag_c), 260, [A.print("Purple fire burns on the crag above the road: the binding-stones.")],
       when=q.when(flag="aldous_told", not_="seal_broken"))
q.on_death("Morvane", [A.drop(STAR), A.drop("WizardHelm"), A.flag("morvane_dead"),
                       A.print("Morvane falls among his star charts. The Starstone rolls from his hands, still glowing."),
                       q.journal("Morvane is dead. The Starstone must go back into the Starwell in the square.", QUEST)])
q.on_pickup(STAR, [q.journal("I have the Starstone, warm and humming in my hand. It belongs in the Starwell.", QUEST)],
            when=q.when(not_="star_lit"))
q.near(*well_xy, 90, [A.take(STAR), A.flag("star_lit"), A.enable("StarLight"), A.enable("SouthWard"),
                      A.print("You lower the Starstone into the Starwell. Light wells up out of the water, blue as "
                              "noon, and far off a bell begins to ring."),
                      q.journal("The Starstone is home in the Starwell, and the wards burn again. Archmagister Aldous "
                                "will open the north gate.", QUEST)],
       when=q.when(has=STAR, not_="star_lit"))

# the gate warden and the watch
q.talker("GateWarden", [
    q.say("Gate's open, by the Archmagister's word. North road runs to Thornwick. Safe road.",
          when=q.when(flag="aldous_paid"), who="Guard"),
    q.say("The gate's sealed with a word, not a bar; I couldn't open it if I wanted to. Take it up with the "
          "Archmagister at the College.", who="Guard")])
for k_ in range(2):
    q.talker(f"Watch{k_ + 1}", [
        q.say("Wards are lit. I'll sleep tonight.", when=q.when(flag="star_lit"), who="Watch"),
        q.say("Keep to the lit streets after dark. Not that there are any, now.", who="Watch")])
    q.portrait(f"Watch{k_ + 1}", ("IxGuard2Pic", "Warrior2Pic")[k_])

# Weeds of the Herbarium
herb_foes = plants + wasps
q.on_all_dead(herb_foes, [A.flag("herb_clear"), A.print("The last of the herbarium's horrors is still.")])
q.talker("Ottilie", [
    q.say("All of them? Even the big one by the beds? You're braver than my gardener; he's still up a tree. Here: "
          "remedies from my own shelves, the charm my teacher gave me, and silver.",
          when=q.when(flag=q.dead(*herb_foes), not_="ottilie_paid"),
          do=[A.flag("ottilie_paid"), A.give("RedPotion", 3), A.give("CurePoisonPotion", 2),
              A.give("AmuletofNature"), A.gold(60),
              q.journal("I cleared Ottilie's herbarium of its plants and wasps. She paid me in remedies, a charm and "
                        "silver.", COMPLETED)], who="Ottilie"),
    q.say("I'll replant in spring. Smaller things. Things without teeth.", when=q.when(flag="ottilie_paid"),
          who="Ottilie"),
    q.say("The herbarium's down the garden walk, west of the square. Mind the wasps; the hive's split.",
          when=q.at("herb", 1), who="Ottilie"),
    q.say("You look like someone who can use a blade. My herbarium in the west wood: the College's beds, where I "
          "grow what goes in my jars. Some of what I grow eats meat, and it was the wards that kept it in its beds. "
          "Since they went dark the plants have broken out and the wasps' hive has split. My gardener's still up a "
          "tree. Clear the beds and I'll pay you well.",
          do=[A.stage("herb", 1), q.journal("Ottilie the alchemist's herbarium in the west wood has run wild: her "
                                            "man-eating plants have broken their beds and the wasps' hive has split. "
                                            "She will pay me to clear them.", QUEST)], who="Ottilie")])
q.near(*square_px(*herb_bed_c), 240, [A.print("The herbarium. Something in the beds turns toward you.")],
       when=q.at("herb", 1))

# Old Hob
q.on_death("OldHob", [A.flag("hob_dead"), A.print("Old Hob slows, and stops, and is only stone.")])
q.talker("Harl", [
    q.say("He's down? ...Forty years I worked beside him. He'd hand me the stones before I asked. It wasn't him "
          "swinging at you, you understand; it was what's left when the binding goes. Here. His pay, I always said, "
          "since he never took any. And my old hammer; I'll not lift it again this year.",
          when=q.when(flag=q.dead("OldHob"), not_="harl_paid"),
          do=[A.flag("harl_paid"), A.gold(100), A.give("WarHammer"),
              q.journal("I put Old Hob, the masons' golem, to rest. Master Harl paid me and gave me his hammer.",
                        COMPLETED)], who="Harl"),
    q.say("We'll cut by hand now, like our grandfathers. Slower. Quieter.", when=q.when(flag="harl_paid"), who="Harl"),
    q.say("Up the masons' road, north-west. He stands in the cut. Don't let him get his hands on you.",
          when=q.at("hob", 1), who="Harl"),
    q.say("You're going past the quarry? Then hear me. Old Hob's a stone golem the College bound three hundred years "
          "ago to cut its stone. Gentlest thing in Starwell. When the Starwell went dark his binding slipped, and now "
          "he strikes at anyone who comes into the cut; he near killed my apprentice. He'll not come back from it. "
          "Put him down for me. I can't do it myself.",
          do=[A.stage("hob", 1), q.journal("Master Harl the mason asked me to put down Old Hob, the College's stone "
                                           "golem, whose binding slipped when the Starwell went dark. He stands in "
                                           "the quarry up the masons' road, north-west of town.", QUEST)], who="Harl")])

# the Diggers in the Scar
q.on_all_dead(digger_foes, [A.flag("diggers_dead"), A.print("The last digger drops his pick. The Scar is quiet.")])
turn_all = [A.turn(p_, f_) for p_, f_ in zip(diggers, digger_foes)]
q.talker("Vask", [
    q.say("We had a deal. Go on, then, before the captain asks you where you've been.", when=q.when(flag="bribed"),
          who="Vask"),
    q.say("Star-iron, friend. The star left it all through this ground, and the College sits on it like a hen. We dig, "
          "we sell, nobody's hurt. If the captain sent you, here's a purse that says you looked and found the Scar "
          "empty. A hundred and twenty in silver. Do we have a deal?",
          when=q.when(not_="refused"), ask=True,
          do=[A.flag("bribed"), A.gold(120),
              q.journal("I took Vask's purse to say the Scar was empty. The diggers dig on.", COMPLETED)],
          else_=[A.flag("refused"), A.print("Vask spits. 'Then you can dig your own grave. Lads!'"),
                 q.journal("I refused Vask's purse. His diggers have taken up their picks against me.", QUEST)] +
                turn_all, who="Vask")])
for n in diggers[1:]:
    q.talker(n, [q.say("Vask does the talking.", who="Digger")])
    q.portrait(n, "MalePic9")
q.talker("Brannoc", [
    q.say("Dead, all of them? I'd have settled for gone, but I'll not weep for diggers on College ground. The watch's "
          "thanks, and this mail; it's better on you than in my stores.",
          when=q.when(flag=q.dead(*digger_foes), not_="brannoc_paid"),
          do=[A.flag("brannoc_paid"), A.gold(80), A.give("ChainTunic"), A.give("ChainLeggings"),
              q.journal("I drove Vask's diggers out of the Scar. Captain Brannoc paid me and gave me mail.", COMPLETED)],
          who="Brannoc"),
    q.say("Empty, you say? Then why does my scout still see their smoke? Get out of my watch house.",
          when=q.when(flag="bribed"), who="Brannoc"),
    q.say("The Scar's clean. Good work.", when=q.when(flag="brannoc_paid"), who="Brannoc"),
    q.say("The Scar's east of town, through the birches. Follow the path from the square.",
          when=q.at("scar", 1), who="Brannoc"),
    q.say("Captain Brannoc, of the watch. With the wards dark I've no men to spare, and there's a band of diggers in "
          "the Scar, the crater east of town where the star fell. College ground, and they're stripping it of "
          "star-iron. Vask leads them. Drive them out and the watch will pay.",
          do=[A.stage("scar", 1), q.journal("Captain Brannoc of the watch wants Vask's band of diggers driven out of "
                                            "the Scar, the crater east of town where the star fell.", QUEST)],
          who="Brannoc")])
q.near(*scar_camp["fire"], 300, [A.print("A crater of bare earth and crystal, tents, a fire: the diggers' camp in the "
                                         "Scar.")])

for who_, pic_ in (("Edda", "GlyndaPic"), ("Aldous", "HorvathPic"), ("Quill", "ArchivistPic"),
                   ("Ottilie", "MaidenPic4"), ("Brannoc", "WardenPic"), ("Harl", "QuarterMasterPic"),
                   ("Vask", "MalePic9"), ("GateWarden", "IxGuard1Pic")):
    q.portrait(who_, pic_)

m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())

# ---- 11. the exteriors' dressing: the empty ground filled with the town's and the wood's things --------------------------
dressed = Exterior(m, land, "green", placed=placed, culture="wizard").dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed, os.path.join(OUT, f"{NAME}.rooms.json"), yards=[y_ for y_ in yards if y_.kind in built])
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| trees {n_trees} | shops {n_shops} | caches {len(caches)} | opened {len(opened)} | lines {len(q.strings)} "
          f"| yards {', '.join(built) or 'none'} | dressing {sum(dressed.values())} groups")
