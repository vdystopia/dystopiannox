"""Greywatch: a border keep on the hill road north out of the Black Fen, and the story of the turncoat (chapter six
after Thornwick, the north road, Rimehold, the Rime Pass, Emberhollow, the Ash Road, Deepvault and Mirefen; the green
world, a pine forest, FORESTS["pine"]). Built with kit/story.py, the castle's curtain wall with kit/story.Curtain.

The story
- The fen causeway gives onto the hill road at its foot, in the south-west. Sergeant Brom sits wounded by the
  milestone: his patrol of six rode into an ambush in the gully above the road, and only he came back. The reivers
  knew their road and their hour: someone in Greywatch is selling the watch rota. A few of Ottar's reivers still lie
  behind the rocks of the gully and fall on whoever passes. Brom sends the player up to the castle.
- Greywatch: a curtain wall of Galava stone with towers at its corners, a gatehouse on the hill road (the south gate,
  open) and the north gate, shut; inside, a cobbled courtyard round a well, the keep (throne room, great hall, the
  steward's study, the lord's chamber, the stores), the barracks, the chapel, the armourer's forge, the cells and the
  training ground. Outside the gate, the hamlet on the hill road: the Grey Gate inn, the trading post, the
  laundress's cottage and a farm.
- Main quest, the Turncoat (an investigation ending in an accusation): Lord Castellan Osric has shut the north gate
  (the road home to Thornwick): no rider and no letter leaves Greywatch until he knows who is selling his patrols.
  The player, who came out of the fen that morning, is the one soul he knows is not in the traitor's pay. Ottar, the
  reivers' chief, camps in the Hollow in the west wood; he carries the traitor's last letter, signed only "C".
  Three men in the keep sign so: Corvin the steward, Captain Conrad and Brother Cuthbert the chaplain. The letter
  speaks of the rota copied from the tower ledger and silver left at the Grey Gate inn; the castle's folk know who
  keeps the ledgers, who can write, and who drinks at the inn without drinking. The player puts the letter before the
  one they suspect (a yes/no question): an innocent man is insulted and points at the ledger; Corvin drops his mask,
  turns hedge-wizard and calls his two hired swords out of the stores. With the turncoat dead, Osric pays and opens
  the north gate.
- The Gauntlet (a trial of arms, bouts in turn): by border law a reiver taken alive may fight the keep's champion for
  his freedom. Greywatch's champion died in the gully, and three of Ottar's men in the cells demand their right.
  Hedda, the master-at-arms, asks the player to stand champion: first one prisoner out of the first cell, then the
  two brothers together out of the second. Hedda pays from the armoury.
- The Deserter (a choice about a person, not an item): Wil Fenn ran from the wall the night the reivers came. His
  mother Agnes, the laundress, begs the player to find him before Captain Conrad's men do; deserters hang. He is
  hiding in the old beacon tower on the east crag, kept there by bears. With the bears dead, Wil asks whether the
  player will take him back: yes, and he walks back to the barracks, where Conrad pays and spares him the rope; no,
  and he walks east over the border, and Agnes pays with her late husband's sword.
- The armourer, the trading post and the inn buy and sell. The Hollow's chest, the beacon's old store and three
  caches in the pines hold loot; every soul in the castle and the hamlet knows something.
- The exit: the north road beyond the north gate leads home to Thornwick, where the campaign began (chapter one's
  map, mapgen/designs/thornwick.py): the campaign comes home.

    py mapgen/designs/greywatch.py [seed]
"""
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import Land, square_tile, square_px, px_square
from kit.vegetation import Planter, FORESTS, TOWN_PLANTING
from kit.village import Village
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT, NOTE
from kit import yards as Y
from kit import camps
from kit.story import StoryMap, Curtain

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 5
rng = random.Random(SEED)
NAME = "Greywatch"
FOREST = "pine"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "greywatch")
NEXT_MAP = "Thornwick"               # the campaign comes home (mapgen/designs/thornwick.py)
LETTER = "SponsorshipLetter"         # the traitor's letter: a letter the player can carry (things: LIGHT, SIMPLE)


def uv(X, Y):
    """uv of a point given in map squares as seen on screen (X right, Y down, 0..255)."""
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="a border keep on the hill road north out of the Black Fen: a curtain wall with corner towers and a "
          "gatehouse round a courtyard, the keep, the barracks, the chapel and the forge; a hamlet outside the gate; "
          "the reivers' camp in the west wood, an old beacon tower on the east crag, the north gate shut on the road "
          "home to Thornwick",
    environment="town", mood="watchful, suspicious",
    areas=[AreaIdentity("foot", "the foot of the hill road where the fen causeway arrives: the start"),
           AreaIdentity("gully", "the rocky gully above the road where the patrol was ambushed"),
           AreaIdentity("hamlet", "the hamlet on the hill road outside the castle gate"),
           AreaIdentity("castle", "Greywatch's courtyard inside the curtain wall", landmark="Well"),
           AreaIdentity("north", "the north road beyond the north gate: the way home to Thornwick"),
           AreaIdentity("wood", "the west wood on the way to the Hollow"),
           AreaIdentity("hollow", "Ottar's reivers' camp in the Hollow"),
           AreaIdentity("farm", "the castle farm below the walls"),
           AreaIdentity("beacon", "the old beacon tower on the east crag, a bears' haunt now")],
    buildings=[BuildingIdentity("keep", "castle", "the keep", "Lord Castellan Osric"),
               BuildingIdentity("barracks", "castle", "the barracks", "Captain Conrad and the garrison"),
               BuildingIdentity("chapel", "castle", "the castle chapel", "Brother Cuthbert"),
               BuildingIdentity("smithy", "castle", "the armourer's forge", "the armourer"),
               BuildingIdentity("inn", "hamlet", "The Grey Gate", "the innkeeper"),
               BuildingIdentity("store", "hamlet", "the trading post", "the trader"),
               BuildingIdentity("cottage", "hamlet", "Agnes's cottage", "Agnes Fenn"),
               BuildingIdentity("home", "hamlet", "", "a carter's family"),
               BuildingIdentity("home", "farm", "the farmhouse", "the castle's tenant farmer")])

m = Spec(NAME, summary="Greywatch", description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"Generated by Claude.", author="vdystopia (generated by Claude)", version="1", date="2026", type=SOLO,
         minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [132, 132, 128]
q = QuestBook(NAME)

# ---- 1. the plan: the hill road from the fen through the hamlet and the castle to the north road ---------------------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"foot": ((50, 228), 18), "gully": ((24, 206), 14), "hamlet": ((70, 190), 40), "castle": ((128, 116), 30),
         "north": ((200, 40), 14), "wood": ((40, 156), 16), "hollow": ((26, 106), 26), "farm": ((140, 214), 22),
         "beacon": ((210, 196), 26)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ not in ("hamlet", "castle"))
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_, bend_ in (("foot", "hamlet", 14, True, 0.2), ("hamlet", "castle", 14, True, 0.06),
                                 ("castle", "north", 13, True, 0.06), ("foot", "gully", 9, False, 0.25),
                                 ("hamlet", "wood", 10, False, 0.25), ("wood", "hollow", 10, False, 0.25),
                                 ("hamlet", "farm", 12, True, 0.2), ("farm", "beacon", 10, False, 0.25)):
    pk_ = (0, 0) if "castle" in (a_, b_) else (1, 2) if road_ else (0, 1)    # no bays off the roads at the walls
    land.link(a_, b_, w_, bend=bend_, road=road_, pockets=pk_)
land.blends(m)

# ---- 2. the castle: the curtain wall planned round the courtyard, the courtyard's paving, the roads ---------------------
castle_c = land.areas["castle"]["c"]
cw = Curtain(land, castle_c, (30, 28), gates=("j0", "j1"))
land.paint_square(m, "castle", 10, "RoughCobble")
land.taken |= {(int(castle_c[0]) + a, int(castle_c[1]) + 1 + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}
land.paint_roads(m, "DirtDark2", width_squares=2.8, skip=land.reserved | land.forbidden)
for s_ in land.roads & cw.plot:                     # inside the walls the road is cobbled
    m.floor[square_tile(*s_)] = "RoughCobble"
cw.plan_gates(m)
cw.hold()

# ---- 3. buildings: the keep and the garrison round the courtyard, the hamlet along the road ------------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"gully": 10, "foot": 9, "hollow": 14, "beacon": 12, "wood": 8},
                            square_area="castle")
cw.release()
by_role = sm.by_role
sm.connect_and_furnish()


def free_block(centre, half, inside, gap=1):
    """The free square block (2*half+1) nearest `centre` with every square in `inside` and none taken or paved."""
    busy = land.taken | land.roads | land.plaza | land.taken_strict
    best = None
    for di in range(-32, 33):
        for dj in range(-32, 33):
            c = (int(centre[0]) + di, int(centre[1]) + dj)
            blk = {(c[0] + a, c[1] + b) for a in range(-half - gap, half + gap + 1) for b in range(-half - gap, half + gap + 1)}
            if blk <= inside and not blk & busy:
                d = abs(di) + abs(dj)
                if best is None or d < best[0]: best = (d, c)
    return best and best[1]


# the cells and the training ground in the courtyard, the farm's field outside
inner = {s for s in cw.plot if min(s[0] - cw.gi, cw.gi + cw.w - 1 - s[0], s[1] - cw.gj, cw.gj + cw.h - 1 - s[1]) >= 3}
yards = []


def inner_yard(kind, radii=(8, 11, 14, 17, 20)):
    """A yard of `kind` inside the walls, as near the well as it fits, its gate toward the well."""
    for r_ in radii:
        for a_ in range(12):
            c_ = (castle_c[0] + r_ * math.cos(a_ * math.pi / 6), castle_c[1] + r_ * math.sin(a_ * math.pi / 6))
            before = set(land.taken)
            y_ = Y.plan(land, rng, kind, c_, toward=castle_c)
            if y_ and {(y_.gi + a, y_.gj + b) for a in range(-1, y_.w + 1) for b in range(-1, y_.h + 1)} <= inner:
                yards.append(y_); return y_
            land.taken = before
    print(f"no room for the {kind} in the courtyard")
    return None


jail = inner_yard("jail")
tg_c = free_block(castle_c, 4, inner)
assert tg_c, "no room for the training ground"
land.taken |= {(tg_c[0] + a, tg_c[1] + b) for a in range(-5, 6) for b in range(-5, 6)}
memorial = inner_yard("monument", radii=(14, 17, 20, 23, 26))       # to the watch's fallen
garden = inner_yard("field", radii=(17, 20, 23))                # the castle's kitchen garden
farm_c = land.areas["farm"]["c"]
for kind_ in ("field", "orchard"):
    near_ = [(farm_c[0] + r * math.cos(a * math.pi / 6), farm_c[1] + r * math.sin(a * math.pi / 6)) for r in (8, 11, 14) for a in range(12)]
    y_ = Y.plan_any(land, rng, kind_, near_)
    if y_: yards.append(y_)
    else: print(f"no room for the {kind_}")

# ---- 4. the land grows round everything; the courtyard all land, the forest kept off the walls -------------------------
land.carve(margin=3.5)
cw.fill()
lane_ = sm.keep_open({"gully": 6, "hollow": 9, "beacon": 8, "foot": 3, "wood": 3})
clumps = land.thickets(150, size=(0.9, 1.8), clear=1, avoid=frozenset((lane_ | cw.plot) & land.squares))
land.open_links()
land.squares -= cw.forb
land.apply(m, wall=FORESTS[FOREST]["wall"], floor="GrassNorm")
gates = cw.build(m, prefix={"j0": "SouthGate", "j1": "NorthGate"}, lock={"j1": "Mechanism"})
assert "j1" in gates and "j0" in gates, "the roads do not cross the wall where the gates go"
built = []
for y_ in yards:
    if not y_.plot <= land.squares:
        print(f"the {y_.kind} lies off the land"); continue
    Y.build(m, rng, land, y_)
    built.append(y_.kind)
training = camps.training_ground(m, rng, land, (tg_c[0] + 0.5, tg_c[1] - 0.5), castle_c, r=4.5)

# ---- 5. the castle's and the hamlet's life ----------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Grey Gate\nAle, a hot dinner and a bed under the walls", "Sign"),
                     store=q.text("Trading Post\nGoods from the fen and the north road", "Sign"),
                     smithy=q.text("The Armoury", "Sign"), chapel=q.text("The Chapel of the Watch", "Sign"))
for bid, b in placed:
    role = BUILDINGS[bid.role]
    for sc in role["scenes"]: vil.scene(b, sc, role=bid.role)
    if rng.random() < role["garden"]: vil.garden(b, size=(rng.randint(3, 5), rng.randint(2, 4)))
# the courtyard's well, benches round it and lamps on the paving's corners
m.obj_px("Well", *square_px(castle_c[0] + 0.5, castle_c[1] - 0.5))


def lamp(si, sj):
    x, y = square_px(si, sj)
    m.obj_px("StreetLampOrnate3", x, y); m.obj_px("StreetLampOrnate3Shadow", x - 15, y + 21)


vil.square_piece((castle_c[0] + 0.5, castle_c[1] - 0.5), 5, pole=lamp, per_side=1)
land.ground_variety(m, clear=3)

# ---- 6. the story's places ------------------------------------------------------------------------------------------
foot_c, gully_c, hollow_c = land.areas["foot"]["c"], land.areas["gully"]["c"], land.areas["hollow"]["c"]
wood_c, beacon_c, hamlet_c, north_c = (land.areas[k]["c"] for k in ("wood", "beacon", "hamlet", "north"))
# the gully: the reivers' fire behind the rocks, open toward the road
gully_camp = camps.bandit_camp(m, rng, land, gully_c, foot_c, loot=[("Gold", {"Amount": 40}), "RedPotion", "Quiver"],
                               sleepers=2, tents=0)
# the Hollow: Ottar's camp
hollow_camp = camps.bandit_camp(m, rng, land, hollow_c, wood_c,
                                loot=[("Gold", {"Amount": 120}), "BluePotion", "RedPotion", "RedPotion", "SteelHelm",
                                      "Longsword"], sleepers=6, tents=3)
# the old beacon on the east crag: a ruined tower, the beacon's cold basin in the middle, its old store at the back
beacon = camps.ruined_tower(m, rng, land, beacon_c, farm_c,
                            loot=[("Gold", {"Amount": 70}), "RedPotion", "BluePotion", "LeatherArmoredBoots"],
                            size=(9, 9), material="StoneGray")
bsc = camps.Scene(m, rng, land, beacon_c)
bsc.put("DunMirFlameBasinUnlit", *bsc.at(0.0, 0.0))
# caches in the pines, off the ways
caches = []
for near_, loot_, stump_ in ((wood_c, [("Gold", {"Amount": 45}), "CurePoisonPotion", "RedPotion"], True),
                             (beacon_c, [("Gold", {"Amount": 60}), "ChainCoif", "RedPotion"], False),
                             (farm_c, [("Gold", {"Amount": 35}), "BluePotion", "SpellBook"], False)):
    s_ = sm.hidden_spot(near_, r=(5, 12))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
# signposts
camps.signpost(m, land, (foot_c[0] + 2.5, foot_c[1] - 1.5),
               q.text("GREYWATCH\nThe border keep, up the hill road.\nState your business at the gate.", "Sign"))
sg_ = sm.road_near(px_square(*cw.gate_px("j0", 5.0)))
camps.signpost(m, land, (sg_[0] + 2.0, sg_[1] - 1.5), q.text("GREYWATCH CASTLE\nThe Lord Castellan's peace is kept here.", "Sign"))
ng_ = sm.road_near(px_square(*cw.gate_px("j1", -4.0)))
camps.signpost(m, land, (ng_[0] - 1.5, ng_[1] - 2.0),
               q.text("THE NORTH GATE IS SHUT\nNo rider and no letter leaves Greywatch.\n- Osric, Lord Castellan", "Sign"))

# ---- 7. planting: none in the courtyard ----------------------------------------------------------------------------
keep = set(cw.plot)
for bid, b in placed:
    for d in b.entrances:
        di, dj = px_square(*d.px)
        keep |= {(di + a, dj + b2) for a in range(-2, 3) for b2 in range(-2, 3)}
vil.ground_bits(1.4)
planter = Planter(m, rng, land, FOREST, keep_clear=keep | lane_)
n_trees, n_small = planter.plant_all(groves=4, profile=TOWN_PLANTING)
piles = planter.rock_piles(max(4, len(land.squares) // 900))
vignettes = planter.forest_floor(max(6, len(land.squares) // 700))
start_xy = square_px(foot_c[0] + 0.5, foot_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
sm.exit_to("north", NEXT_MAP, prefix="NorthExit")

# ---- 8. the people --------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
person, room_of, free_px = sm.person, sm.room_of, sm.free_px
vx, vy = square_px(*castle_c)
# Sergeant Brom by the milestone, wounded
bx_, by_ = square_px(foot_c[0] + 1.5, foot_c[1] + 0.5)
person("Con02a", "Mayor's_Guard", bx_, by_, "Brom", face=start_xy)
# Lord Castellan Osric in his throne room
tr = room_of("keep", "throne_room") or room_of("keep", "great_hall")
ox_, oy_ = free_px(tr) if tr else (vx, vy)
person("Con02a", "Mayor_Theogrin", ox_, oy_, "Osric")
# the steward at his ledgers; the turncoat he really is waits, hidden, in the same place
st = room_of("keep", "study") or tr
cx_, cy_ = free_px(st, clear=26) if st else (vx + 40, vy)
person("Con02a", "Morgan", cx_, cy_, "Corvin")
pop.creature("Wizard", cx_ + 6, cy_ + 6, action="guard", scr="Turncoat", aggr=0.83, HealthMultiplier=3.0)
sto = room_of("keep", "storeroom") or st
sellswords = []
for k in range(2):
    sx_, sy_ = free_px(sto, clear=26) if sto else (cx_ + 30 * k, cy_ + 30)
    pop.creature("Swordsman", sx_, sy_, action="guard", scr=f"Sellsword{k + 1}", aggr=0.83)
    sellswords.append(f"Sellsword{k + 1}")
# Captain Conrad in the barracks' mess, Brother Cuthbert in the chapel
mh = room_of("barracks", "mess_hall") or room_of("barracks", "barracks")
kx_, ky_ = free_px(mh) if mh else (vx - 40, vy)
person("Con02a", "Contest_Guard", kx_, ky_, "Conrad")
ch = room_of("chapel", "chapel")
ux_, uy_ = free_px(ch) if ch else (vx, vy + 40)
person("Con04c", "Keeper", ux_, uy_, "Cuthbert")
# Hedda at the training ground
hx_, hy_ = training["watch"]
person("Con03A", "Lance", hx_, hy_, "Hedda", face=training["centre"])
# Agnes at her cottage door in the hamlet
ag_ = sm.outside_door("cottage") or square_px(*hamlet_c)
person("Con02a", "Lydia", ag_[0] + 15, ag_[1] + 15, "Agnes", face=square_px(*hamlet_c))
# Wil hiding in the beacon tower
wx_, wy_ = beacon["boss"]
person("Con02a", "Heckler", wx_, wy_, "Wil", face=square_px(*farm_c))
# the gate guards: inside the south gate and before the north gate
for face_, nm_, donor_ in (("j0", "SouthGuard", "IxGuard1"), ("j1", "NorthGuard", "IxGuard2")):
    gx_, gy_ = cw.gate_px(face_, -2.2)
    person("Con02a", donor_, gx_ + 22, gy_ + 22, nm_, face=(vx, vy))
# waypoints: Wil's way home to the barracks, or away east
bar_door = sm.outside_door("barracks") or (vx - 60, vy)
far_east = square_px(beacon_c[0] + 9.0, beacon_c[1] - 0.5)
wil_wps = pop.waypoint_path("WilHome", [bar_door]) + pop.waypoint_path("WilAway", [far_east])
# shopkeepers
WARES = {"store": [(4, "RedPotion"), (3, "BluePotion"), (2, "CurePoisonPotion"), (3, "RedApple"), (2, "Bread"),
                   (2, "Quiver"), (1, "Bow"), (1, "LeatherBoots"), (1, "LeatherHelm"), (1, "LeatherArmor")],
         "inn": [(6, "RedApple"), (5, "Meat"), (4, "Cider"), (3, "Bread"), (2, "RedPotion")],
         "smithy": [(2, "Sword"), (1, "Longsword"), (1, "BattleAxe"), (1, "WarHammer"), (1, "SteelShield"),
                    (1, "ChainCoif"), (1, "ChainTunic"), (1, "ChainLeggings"), (1, "SteelHelm"), (1, "PlateBoots")]}
GREET = {"store": q.text("Trading post. Fen eel, north-road salt, arrows by the sheaf. Since the gate shut, nothing "
                         "goes north and nobody's buying.", "Shop"),
         "inn": q.text("Welcome to the Grey Gate. Soldiers drink on the left, travellers on the right, and nobody "
                       "talks about the rota.", "Shop"),
         "smithy": q.text("The armoury. Castle steel, made for the wall. If you mean to stand champion, buy a shield.",
                          "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"smithy": "ShopkeeperWarriorsRealm"})
# townsfolk between the courtyard and the doorsteps, each with something to tell
FOLK = [("Con02a", "Tanya"), ("Con02a", "Julie"), ("Con02a", "Clyde"), ("Con03A", "Millard"), ("Con08a", "Gretchen"),
        ("Con02a", "Jacob"), ("Con03A", "Osborn")]
RUMOURS = [
    "The watch rota is written in the tower ledger. Only the steward and his lordship ever open it.",
    "Steward Corvin goes down to the Grey Gate of an evening. Sits by the casks. Never seen him drink a drop.",
    "Brother Cuthbert can't write more than a cross, bless him. Signs the alms book with it.",
    "Agnes Fenn's boy ran from the wall the night the reivers came. She cries at the well every morning.",
    "Hedda's champion died in the gully with Brom's patrol. Now the prisoners are shouting for their trial.",
    "Ottar's reivers hole up in the Hollow, out in the west wood. You can see their smoke from the wall.",
    "Bears on the beacon crag this spring. Nobody's lit that old beacon in forty years.",
]
ring = sm.townsfolk(FOLK, castle_c, q=q, rumours=RUMOURS,
                    after=("traitor_dead", "The steward! Of all people. Well, the north gate's open, and the road runs "
                                           "all the way home to Thornwick."),
                    pics=("MaidenPic3", "MaidenPic", "MalePic7", "Townsman3Pic", "MaidenPic2", "MalePic8", "Townsman2Pic"),
                    radius=7.0)
# the watch walking the courtyard inside the walls
inset = 5.0
corners = [square_px(cw.gi + inset, cw.gj - 1 + inset), square_px(cw.gi + inset, cw.gj + cw.h - 1 - inset),
           square_px(cw.gi + cw.w - inset, cw.gj + cw.h - 1 - inset), square_px(cw.gi + cw.w - inset, cw.gj - 1 + inset)]
for k_, donor_ in enumerate(("Contest_Guard", "IxGuard2")):
    wx2, wy2 = corners[k_ * 2]
    person("Con02a", donor_, wx2, wy2, f"Watch{k_ + 1}", action=0)
    sm.beat(f"Watch{k_ + 1}", castle_c, radius=7.0, stops=6)      # a beat round the courtyard, along its paths

# ---- 9. the fights ----------------------------------------------------------------------------------------------------
# the reivers in the gully, who come down on whoever passes on the road below
ambushers = []
for k, (x, y) in enumerate(gully_camp["seats"][:3] + [gully_camp["lookout"]]):
    n = f"Reiver{k + 1}"
    pop.creature("Archer" if k == 3 else "Swordsman", x, y, action="idle", face=square_px(*foot_c), scr=n, aggr=0.5,
                 sight=60 if k < 3 else 150)
    ambushers.append(n)
# Ottar's band in the Hollow: Ottar by his fire, his men round it, archers at the way in
hollow_band = []
ox2, oy2 = hollow_camp["fire"]
pop.creature("Swordsman", ox2 + 30, oy2 - 10, action="guard", face=square_px(*wood_c), scr="Ottar", aggr=0.83,
             HealthMultiplier=3.0)
for k, (x, y) in enumerate(hollow_camp["seats"][:4]):
    n = f"HollowReiver{k + 1}"
    pop.creature("Swordsman", x, y, action="idle", face=hollow_camp["fire"], scr=n, aggr=0.83)
    hollow_band.append(n)
lx, ly = hollow_camp["lookout"]
for k in range(2):
    n = f"HollowArcher{k + 1}"
    pop.creature("Archer", lx + (k * 2 - 1) * 40, ly, action="guard", face=square_px(*wood_c), scr=n, aggr=0.83)
    hollow_band.append(n)
B.sentry("HollowArcher1", square_px(*wood_c), rouse=["Ottar"] + hollow_band[:4], shout="Greywatch men! Up, up!")
# the prisoners in the cells: one in the first, the brothers in the second
cells = sorted((o for o in m.d["objects"] if o.get("type") == "JailDoor"), key=lambda o: (o["x"], o["y"]))
prisoners = []
if jail and len(cells) >= 2:
    along_i = jail.side in ("j0", "j1")
    L_ = jail.w if along_i else jail.h
    centres = []
    for c in range(2):
        lo, hi = c * L_ // 2, (c + 1) * L_ // 2
        if along_i: centres.append(square_px(jail.gi + (lo + hi) / 2, jail.gj - 1 + jail.h / 2))
        else: centres.append(square_px(jail.gi + jail.w / 2, jail.gj - 1 + (lo + hi) / 2))
    for c, (x, y) in enumerate(centres):
        door = min(cells, key=lambda o: math.hypot(o["x"] - x, o["y"] - y))
        door["scr"] = f"Cell{c + 1}"
        door.setdefault("xfer", {})["LockType"] = "Mechanism"
        for k in range(1 if c == 0 else 2):
            n = f"Prisoner{len(prisoners) + 1}"
            pop.creature("Swordsman", x + (k * 2 - 1) * 9 * c, y + (k * 2 - 1) * 9 * c, action="idle", scr=n, aggr=0.0,
                         sight=40, face=(vx, vy))
            prisoners.append(n)
assert len(prisoners) == 3, "the cells were not built"
# the bears round the beacon crag
bears = []
for k, a in enumerate((0.5, 2.0, 3.6, 5.1)):
    x, y = square_px(beacon_c[0] + 7.5 * math.cos(a), beacon_c[1] - 0.5 + 7.5 * math.sin(a))
    n = f"CragBear{k + 1}"
    pop.creature("BlackBear" if k == 0 else "Bear", x, y, action="guard", scr=n, aggr=0.83, face=square_px(*beacon_c))
    bears.append(n)
# the pines' own creatures by the forest's edge
sm.wild({"Wolf": 2, "Bat": 3, "SmallSpider": 2, "Spider": 1, "Urchin": 1}, away_from=castle_c, per100=0.45, gap=7,
        min_away=40, avoid=(hollow_c, gully_c, beacon_c, foot_c, north_c, hamlet_c, farm_c))

story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]] + \
           [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)

# ---- 10. the story ----------------------------------------------------------------------------------------------------
q.start([A.lock("NorthGate1"), A.lock("NorthGate2"), A.lock("Cell1"), A.lock("Cell2"), A.disable("NorthExit1"),
         A.disable("NorthExit2"), A.disable("NorthExit3"), A.disable("Turncoat")] + [A.disable(n) for n in sellswords] +
        [q.journal("The fen causeway ends at the foot of a hill road. At the top stands Greywatch, the border keep.", HINT)])

# the gully: the reivers come down when the player passes below
gx3, gy3 = square_px(*sm.road_near(((gully_c[0] + foot_c[0]) / 2, (gully_c[1] + foot_c[1]) / 2)))
q.near(gx3, gy3, 170, [A.hunt(n) for n in ambushers] + [A.print("Shouts from the rocks above the road: reivers!")])
q.on_all_dead(ambushers, [A.flag("gully_clear"), A.print("The last of the gully's reivers falls.")])

# Brom: the hook
q.talker("Brom", [
    q.say("You cleared the gully? Then my lads can rest easier. Take these; I'll not need them on a sickbed.",
          when=q.when(flag=q.dead(*ambushers), not_="brom_paid"),
          do=[A.flag("brom_paid"), A.give("RedPotion", 2), A.gold(40),
              q.journal("I killed the reivers in the gully. Sergeant Brom gave me potions and his pay.", COMPLETED)],
          who="Brom"),
    q.say("Up the hill. Tell Lord Osric what happened in the gully, and that the reivers knew our hour.",
          when=q.when(flag="met_brom"), who="Brom"),
    q.say("Hold, stranger. You came up the fen causeway? ...Six of us rode out on the border patrol. They were "
          "waiting for us in the gully up there: knew our road, knew our hour. Only I came back. Someone in "
          "Greywatch is selling the watch rota to Ottar's reivers. Go up to the castle; tell Lord Osric. And mind "
          "the gully as you pass. Some of them are still in the rocks.",
          do=[A.flag("met_brom"), A.stage("main", 1),
              q.journal("Sergeant Brom's border patrol was ambushed in the gully above the hill road; he alone came "
                        "back. He believes someone in Greywatch is selling the watch rota to Ottar's reivers, and "
                        "asked me to tell Lord Osric.")], who="Brom")])

# Osric: the main quest
q.talker("Osric", [
    q.say("Corvin. Twelve years at my right hand, and he sold my men by the head. You have done Greywatch a service I "
          "cannot repay in coin, but here is coin, and the north gate is open. The road north runs home to "
          "Thornwick; go with my thanks.",
          when=q.when(flag=q.dead("Turncoat"), not_="osric_paid"),
          do=[A.flag("osric_paid"), A.gold(250), A.give("PlateArms"), A.give("BluePotion", 2),
              A.unlock("NorthGate1"), A.unlock("NorthGate2"), A.enable("NorthExit1"), A.enable("NorthExit2"),
              A.enable("NorthExit3"),
              q.journal("The turncoat is dead. Lord Osric paid me and opened the north gate. The north road leads "
                        "home to Thornwick.", COMPLETED)], who="Osric"),
    q.say("The gate is open. Ride safe, and if you pass this way again, Greywatch's door is yours.",
          when=q.when(flag="osric_paid"), who="Osric"),
    q.say("So it was Corvin, and he has shown his true face in my own keep. Kill him before he gets out of it.",
          when=q.when(flag="accused"), who="Osric"),
    q.say("Ottar's letter. 'The rota for the new moon, copied from the tower ledger. Silver in the cask at the Grey "
          "Gate, as before. C.' Three men in my keep sign with a C: Corvin my steward, Captain Conrad, Brother "
          "Cuthbert. Ask about them, think on it, and when you are sure, put the letter before him. I will not "
          "hang a man on a guess.", when=q.when(has=LETTER, not_="accused"),
          do=[A.flag("read_letter"),
              q.journal("Ottar's letter reads: 'The rota for the new moon, copied from the tower ledger. Silver in the "
                        "cask at the Grey Gate, as before. C.' Corvin the steward, Captain Conrad and Brother "
                        "Cuthbert sign with a C. When I am sure, I should put the letter before the traitor.", QUEST)],
          who="Osric"),
    q.say("The Hollow is in the west wood, past the hamlet. Ottar keeps his letters on him; he trusts no one either.",
          when=q.when(flag="osric_told"), who="Osric"),
    q.say("Brom lives? Thank the gods for that much. Listen: I have shut the north gate. No rider and no letter "
          "leaves Greywatch until I know who sells my patrols. You came out of the fen this morning; you are the "
          "one soul in this keep I know is not in his pay. Ottar, the reivers' chief, camps in the Hollow in the west "
          "wood. Whoever pays him writes to him. Bring me what he carries.",
          do=[A.flag("osric_told"), A.stage("main", 2),
              q.journal("Lord Castellan Osric has shut the north gate until he knows who in Greywatch sells the watch "
                        "rota to the reivers. Their chief, Ottar, camps in the Hollow in the west wood; he carries "
                        "the traitor's letters.", QUEST)], who="Osric")])
q.on_death("Ottar", [A.drop(LETTER), A.print("Ottar falls. A folded letter slips from his jerkin.")])
q.on_pickup(LETTER, [q.journal("Ottar carried a letter signed 'C'. Lord Osric will want to read it.", QUEST)],
            when=q.when(not_="read_letter"))
q.near(*hollow_camp["fire"], 300, [A.print("Smoke, tents, stolen Greywatch harness: the reivers' Hollow.")])

# the accusation: put the letter before the man you suspect
q.talker("Corvin", [
    q.say("You are holding something of mine, I think. Are you going to accuse me, outlander?",
          when=q.when(has=LETTER, flag="read_letter", not_="accused"), ask=True,
          do=[A.flag("accused"), A.disable("Corvin"), A.hunt("Turncoat")] + [A.hunt(n) for n in sellswords] +
             [A.print("The steward's face changes. 'Ottar pays better than Osric ever did. Guards! My guards!'"),
              q.journal("I accused Corvin the steward. He threw off his mask and called his hired swords.", QUEST)],
          else_=[A.chat("Corvin", "Then stop wasting my time. The ledgers will not keep themselves.")], who="Corvin"),
    q.say("The tower ledger? I keep it, of course. Every coin, every rota, every sack of oats. Somebody must.",
          when=q.when(flag="read_letter"), who="Corvin"),
    q.say("Corvin, steward of Greywatch. If you need lodging, the Grey Gate is outside the walls. If you need his "
          "lordship, he is busy.", who="Corvin")])
q.talker("Conrad", [
    q.say("You brought the Fenn boy back. He won't hang; I've buried enough of my lads this month. He'll stand "
          "double watches on the north wall till midsummer. Take this, for sparing me a hanging.",
          when=q.when(flag="wil_back", not_="conrad_paid"),
          do=[A.flag("conrad_paid"), A.gold(80), A.give("ChainTunic"),
              q.journal("I brought Wil Fenn back to Greywatch. Captain Conrad spared him the rope and paid me.",
                        COMPLETED)], who="Conrad"),
    q.say("Accuse me? I've bled on this wall for twenty years. And I can't read a ledger to save my life; the "
          "steward keeps those. Think about who keeps them.",
          when=q.when(has=LETTER, flag="read_letter", not_="accused"), ask=True,
          do=[A.flag("conrad_asked")], else_=[A.chat("Conrad", "Then put that away.")], who="Conrad"),
    q.say("The Fenn boy's on the wall again. Good lad, when he isn't frightened.", when=q.when(flag="conrad_paid"),
          who="Conrad"),
    q.say("Captain Conrad. If you see Wil Fenn, the boy who ran, bring him back. Desertion is a hanging matter, "
          "but I'd rather have him on the wall than on a rope.", who="Conrad")])
q.talker("Cuthbert", [
    q.say("Me, child? I sign with a cross; I never learned my letters. The steward reads me the alms book every "
          "month. Go and ask him who writes in the ledger.",
          when=q.when(has=LETTER, flag="read_letter", not_="accused"), ask=True,
          do=[A.flag("cuthbert_asked")], else_=[A.chat("Cuthbert", "Peace be with you, then.")], who="Cuthbert"),
    q.say("The traitor is dead and the gate is open. I will pray for Brom's patrol, and for Corvin too.",
          when=q.when(flag="traitor_dead"), who="Cuthbert"),
    q.say("Brother Cuthbert. I keep the chapel and bury the watch. Six this month, from the gully. Something is "
          "rotten in this keep.", who="Cuthbert")])
q.on_death("Turncoat", [A.flag("traitor_dead"), A.print("The turncoat steward falls among his own stores."),
                        q.journal("Corvin the turncoat is dead. Lord Osric should hear it.", QUEST)])

# the gate guards
q.talker("NorthGuard", [
    q.say("Gate's open, by his lordship's word. The north road runs home to Thornwick. Safe road.",
          when=q.when(flag="osric_paid"), who="Guard"),
    q.say("North gate's shut. Nobody leaves till his lordship finds his traitor. Take it up with him in the keep.",
          who="Guard")])
q.talker("SouthGuard", [
    q.say("Welcome to Greywatch, stranger. His lordship's in the keep, across the courtyard.", who="Guard")])

# the Gauntlet
q.on_death("Prisoner1", [A.flag("bout1"), A.print("The first prisoner goes down. Hedda raises a hand: 'Greywatch!'")])
q.on_all_dead(["Prisoner2", "Prisoner3"], [A.flag("bout2"), A.print("The brothers lie in the sand. The trial is over.")])
q.talker("Hedda", [
    q.say("Three of Ottar's men tried by combat, and Greywatch still has a champion. The armoury's best, as promised.",
          when=q.when(flag=q.dead(*prisoners), not_="hedda_paid"),
          do=[A.flag("hedda_paid"), A.give("Breastplate"), A.give("SteelShield"), A.gold(100),
              q.journal("I won the Gauntlet for Greywatch. Hedda paid me from the armoury.", COMPLETED)], who="Hedda"),
    q.say("You fought well. Come and spar when the north road bores you.", when=q.when(flag="hedda_paid"), who="Hedda"),
    q.say("Fight them! They're out of the cell and they want your blood.", when=q.when(flag="bout2_called", not_="bout2"),
          who="Hedda"),
    q.say("One down. The brothers are next, and they fight together. Ready?",
          when=q.when(flag=q.dead("Prisoner1"), not_="bout2_called"), ask=True,
          do=[A.flag("bout2_called"), A.unlock("Cell2"), A.hunt("Prisoner2"), A.hunt("Prisoner3"),
              A.print("Hedda unbars the second cell. The brothers come out together.")],
          else_=[A.chat("Hedda", "Catch your breath, then.")], who="Hedda"),
    q.say("He's out! Fight him!", when=q.when(flag="gauntlet", not_="bout1"), who="Hedda"),
    q.say("By border law a reiver taken alive may fight the keep's champion for his freedom. Our champion died in "
          "the gully, and three of Ottar's men in the cells are shouting for their right. Will you stand champion "
          "for Greywatch? One of them first, then the two brothers. Win, and the armoury's best is yours.",
          ask=True, when=q.when(not_="gauntlet"),
          do=[A.flag("gauntlet"), A.unlock("Cell1"), A.hunt("Prisoner1"),
              A.print("Hedda unbars the first cell. The prisoner comes out swinging."),
              q.journal("I stand champion for Greywatch in the Gauntlet: Ottar's men in the cells fight me in turn "
                        "for their freedom. Hedda, the master-at-arms, will pay from the armoury.", QUEST)],
          else_=[A.chat("Hedda", "Then the cells stay shut. For now.")], who="Hedda")])

# the Deserter
q.on_all_dead(bears, [A.flag("bears_dead"), A.print("The last bear of the crag falls.")])
q.talker("Agnes", [
    q.say("He's alive, and on the wall, and the captain says he won't hang. Bless you. Take these; it's all I have.",
          when=q.when(flag="wil_back", not_="agnes_paid"),
          do=[A.flag("agnes_paid"), A.give("RedApple", 3), A.give("Bread", 2), A.gold(20)], who="Agnes"),
    q.say("Gone east, over the border. I'll never see him again. But he's alive. Take his father's sword; Wil "
          "never wanted it.", when=q.when(flag="wil_fled", not_="agnes_paid"),
          do=[A.flag("agnes_paid"), A.give("Longsword"), A.gold(60),
              q.journal("Wil Fenn has gone east over the border. His mother Agnes gave me her husband's sword.",
                        COMPLETED)], who="Agnes"),
    q.say("Every morning I look up at the wall and think of him.", when=q.when(flag="agnes_paid"), who="Agnes"),
    q.say("The old beacon, on the east crag past the farm. Please hurry.", when=q.when(flag="agnes_asked"), who="Agnes"),
    q.say("You're not one of Conrad's men? Then listen. My boy Wil ran from the wall the night the reivers came. "
          "He's no traitor, only frightened. Conrad has posted his name, and deserters hang. The farm lad saw him "
          "go up to the old beacon on the east crag, where the bears are. Find him before the captain does.",
          do=[A.flag("agnes_asked"), q.journal("Agnes Fenn's son Wil deserted from the wall the night of the raid. "
                                               "He was seen going up to the old beacon on the east crag, past the "
                                               "farm, where bears roam. Captain Conrad wants him back to hang.",
                                               QUEST)], who="Agnes")])
q.talker("Wil", [
    q.say("I'm going. Tell my mother.", when=q.when(flag="wil_fled"), who="Wil"),
    q.say("I'll face the captain. Better than hiding with the bears.", when=q.when(flag="wil_back"), who="Wil"),
    q.say("You killed them? All of them? Did my mother send you, or the captain? ...It doesn't matter. Will you "
          "take me back to Greywatch, to face Captain Conrad?", when=q.when(flag=q.dead(*bears)), ask=True,
          do=[A.flag("wil_back"), A.walk("Wil", wil_wps[0]),
              q.journal("Wil Fenn is walking back to Greywatch to face Captain Conrad.", QUEST)],
          else_=[A.flag("wil_fled"), A.walk("Wil", wil_wps[1]),
                 q.journal("I let Wil Fenn go. He is walking east, over the border. His mother should hear it.",
                           QUEST)], who="Wil"),
    q.say("Bears! Four of them, round the tower, two days now. I can't get out. Please...", who="Wil")])
q.near(*square_px(*beacon_c), 320, [A.print("Claw marks on the old beacon's stones. Something huge moves among the "
                                            "rocks.")], when=q.when(flag="agnes_asked"))

for who_, pic_ in (("Brom", "Warrior2Pic"), ("Osric", "HorvathPic"), ("Corvin", "MalePic3"), ("Conrad", "Warrior3Pic"),
                   ("Cuthbert", "GalavaPriestPic"), ("Hedda", "WardenPic"), ("Agnes", "MaidenPic"),
                   ("Wil", "Townsman4Pic"), ("NorthGuard", "IxGuard2Pic"), ("SouthGuard", "Warrior2Pic")):
    q.portrait(who_, pic_)
for k_ in range(2):
    q.talker(f"Watch{k_ + 1}", [
        q.say("Traitor's dead, they say. I'll sleep tonight.", when=q.when(flag="traitor_dead"), who="Watch"),
        q.say("Keep moving. And keep your purse close; somebody in this keep sells more than oats.", who="Watch")])
    q.portrait(f"Watch{k_ + 1}", "Warrior3Pic")

m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed, os.path.join(OUT, f"{NAME}.rooms.json"), yards=[y_ for y_ in yards if y_.kind in built])
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| trees {n_trees} | shops {n_shops} | caches {len(caches)} | opened {len(opened)} | lines {len(q.strings)} "
          f"| yards {', '.join(built) or 'none'}")
