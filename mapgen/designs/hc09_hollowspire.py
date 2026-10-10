"""The Hollow Choir, act 9: The Hollow Spire (map HollowSpr). Morvaine's tower on a blighted heath east of the
Emberforge: an old castle's court within a curtain wall (kit/story.Curtain, as Greywatch's), the spire's ground floor
on the land, and three floors above it drawn walled off in the grid's south-east corner, joined by stairs, a lift and
a pentagram (kit/transport.Transporters, skills/nox-transporters, as Ironcrag's far places).
campaign/hollowchoir/BIBLE.md is the story; kit/campaign.py the acts, tokens and cast.

The transporters, each to a floor of its own (none can be walked to):
- The spire stair (stairs, castle: GalavaStairsUp1 against the Gate Hall's north-east wall, GalavaStairsDown in the
  Bone Hall's west corner): from the ground floor up to the Bone Hall, the Choir's quarters and cells. Why: the climb.
  Two-way.
- The bone lift (lift, castle: WhiteElevator in the Bone Hall, its pit in the Library of Voices): up to the floor
  where the Choir keeps its books and Morvaine his letters. Two-way by nature.
- The song gate (portal, TeleportPentagram pads): from the Library to the Singing Chamber at the top of the spire,
  where Morvaine sings over his stones (a magic place: the Choir's own pentagram). Two-way.
- The Choir's door (portal, one way, laid switched OFF): from the Singing Chamber down to the court. Morvaine's death
  wakes it (A.enable), so the player need not climb down floor by floor.

The story
- The road from the Emberforge (act 8) comes onto the heath from the west. Merra, a charcoal-burner, keeps her camp
  by the road: the Choir came back to the spire yesterday with Morvaine at its head, and took her husband Ansel up it
  a week ago. The spire stands in its court to the east; the north gate of the court is the road home to Brackwater,
  shut.
- Main quest, the Hollow Spire (gates the act): climb the spire and kill High Caller Morvaine (Bone Caller, M3, as a
  named boss: FOES["Morvaine"], 900 health) in the Singing Chamber at the top. His death drops the two Spirit Stones
  he carries (SPIRIT_STONE x2: the first and the third bells' clappers, stolen in acts 1 and 4), wakes the Choir's door
  down to the court and opens the north gate; the road beyond (the exit) leads home to Brackwater (act 10).
- Choice A pays off: with WATCH_SEAL, Captain Ilsa Rook and two of the watch wait at the court's south gate. Talk to
  her (or walk past her into the court) and they come with the player and fight beside him, up the stairs, the lift
  and the pentagram after him (kit/hc_scripts allies: owned by the player, so OpenNox's enemy test puts them on his
  side; ordered at the nearest Choir foe; their blows also struck by the script, so the fight is won whatever the
  engine's AI makes of a cloned townsperson). With RUSK_KNIFE, Rusk and two of his crew came up the spire's sewer
  first: they hold the Bone Hall (the lower floor) and fight the Choir there, off-screen while the player is away;
  Rusk talks when the player arrives. Neither: the player climbs alone.
- Choice C pays off: with VESS_OATH, Vess steps out of the dark in the Singing Chamber as Morvaine begins to sing and
  turns her blade on him (an ally that blinks behind him, as the Blink Duelist does; her fighter's body is act 4's
  Swordsman). When he falls with Vess still standing, she becomes the woman of act 4 (CAST["Vess"]: her body and
  voice) for a word of farewell, then steps through space and is gone. Without it Vess is dead (act 4).
- The Spire's Prisoner (this act's own side quest, a rescue): Merra's husband Ansel is in the cell off the Bone Hall,
  the Choir's jailer before its door. Kill the jailer (the cell's door opens), talk to Ansel and he slips down the
  stair (he is next seen at the camp: a swap, since no one walks a transporter). Merra pays.
- Fights with a reason: the Choir's blades and raised dead hold the court and the Gate Hall; the Bone Hall is the
  Choir's quarters; a Cantor (Bone Caller) keeps the Library; Morvaine and two Skeleton Lords hold the top; the heath's
  walking dead by the cliffs. Rewards: Merra's purse, the Library's chest, the camp's chest, caches on the heath.

Tokens: reads WATCH_SEAL (Ilsa and the watch), RUSK_KNIFE (Rusk's crew), VESS_OATH (Vess); gives SPIRIT_STONE x2 (on
Morvaine's death, once: he never comes back). A player who loads the act with an empty pack climbs alone and finishes
it the same way.

    py mapgen/designs/hc09_hollowspire.py [seed]
"""
QA_ACCEPT = []
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL, px, uv_to_xy, rect_tiles, rect_wall_cells
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, rooms_sidecar
from kit.layout import Land, square_tile, square_px, px_square, bfs_distance
from kit.vegetation import Planter, FORESTS
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT, NOTE
from kit.model import Room, Door
from kit.originality import furnish_original
from kit.transport import Transporters, geometry as tp_geometry
from kit.posts import camp_posts
from kit.mods import Mods
from kit.campaign import act, token, has, cast_person, voice, CAST, FOES, exit_next
from kit.hc_scripts import HcScript
from kit import camps
from kit import yards as Y
from kit.story import StoryMap, Curtain
from kit.dressing import Exterior

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 3
rng = random.Random(SEED)
ACT = act(9)
NAME = ACT["map"]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", ACT["design"])
FOREST = "dusk"
PATH = "DirtDark2"
FAR_U = 296                       # uv: the grid's south-east corner beyond this u is the spire's upper floors' (never land)
STONE = token("SPIRIT_STONE")


def uv(X, Y):
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="a blighted heath east of the Emberforge where High Caller Morvaine's spire stands in an old castle's court: "
          "the charcoal-burners' camp by the road, the court's curtain wall and gates, the spire's Gate Hall, and above "
          "it, by stair, lift and pentagram, the Bone Hall, the Library of Voices and the Singing Chamber at the top",
    environment="forest", mood="cold, hollow, watched",
    areas=[AreaIdentity("road", "where the road from the Emberforge comes onto the heath: the start"),
           AreaIdentity("burners", "the charcoal-burners' camp by the road", landmark="the burners' fire"),
           AreaIdentity("heath", "the blighted heath south of the road, where the dead walk"),
           AreaIdentity("approach", "the way up to the court's south gate, where the watch waits"),
           AreaIdentity("court", "the spire's court within the curtain wall", landmark="the Hollow Spire"),
           AreaIdentity("north", "the road home to Brackwater beyond the north gate: the way on"),
           AreaIdentity("stocks", "the Choir's stocks on the hill, an old shrine's stump where its punished dead walk")],
    buildings=[])

m = Spec(NAME, summary=ACT["title"], description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"The Hollow Choir, act 9. Generated by Claude.", author="vdystopia (generated by Claude)", version="1",
         date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [118, 112, 126]          # a grey, sunless light
q = QuestBook(NAME)
hc = HcScript(NAME)
presets = json.load(open(os.path.join(HERE, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]


def preset(family, intensity="full"):
    ps = [p for p in presets if p["family"] == family and p["intensity_class"] == intensity] or \
         [p for p in presets if p["family"] == family]
    return dict(max(ps, key=lambda p: p["weighted_share"])["xfer"])


# ---- 1. the plan: the road east past the burners to the court, the road home north-east beyond it -------------------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"road": ((24, 158), 18), "burners": ((48, 98), 34), "heath": ((56, 194), 32), "approach": ((86, 162), 22),
         "court": ((126, 110), 44), "north": ((186, 44), 16), "stocks": ((100, 42), 28)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "court")
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_, bend_ in (("road", "approach", 14, True, 0.18), ("approach", "court", 14, True, 0.05),
                                 ("court", "north", 13, True, 0.05), ("road", "burners", 11, False, 0.25),
                                 ("approach", "heath", 10, False, 0.25), ("burners", "approach", 10, False, 0.3),
                                 ("burners", "stocks", 10, False, 0.25), ("road", "heath", 10, False, 0.3)):
    pk_ = (0, 0) if "court" in (a_, b_) else (1, 2) if road_ else (0, 1)    # no bays off the roads at the walls
    land.link(a_, b_, w_, bend=bend_, road=road_, pockets=pk_)
land.blends(m)
for mat_, prio_ in (("GrassSparseYellow", 0.3), ("GrassNormYellow", 0.5)):     # the heath's dry grass
    m.blending(mat_, prio_)
# the grid's south-east corner is the upper floors': the heath never grows there
land.forbidden |= {(i, j) for i in range(0, 260) for j in range(-130, 130) if 2 * i >= FAR_U - 4}

# ---- 2. the court: the curtain wall round it, the spire's base in its middle, the roads -------------------------------
court_c = land.areas["court"]["c"]
cw = Curtain(land, court_c, (22, 22), gates=("j0", "j1"))
KU, KV = int(round(court_c[0])) * 2, int(round(court_c[1])) * 2
TOWER = (KU - 14, KU + 14, KV - 14, KV + 14)     # u0, u1, v0, v1: the Gate Hall (the SW wall on v0, the door in it)
tower_sq = {(i, j) for i in range(TOWER[0] // 2, TOWER[1] // 2) for j in range(TOWER[2] // 2 + 1, TOWER[3] // 2 + 1)}
land.taken |= {(i + a, j + b) for i, j in tower_sq for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}
land.taken_strict |= tower_sq
land.reserved |= tower_sq
land.paint_roads(m, PATH, width_squares=2.8, skip=land.reserved | land.forbidden)
for s_ in land.roads & cw.plot:                  # inside the walls the road is flagged
    m.floor[square_tile(*s_)] = "RoughCobble"
cw.plan_gates(m)
cw.hold()
# the Choir's graveyard in the court, where it raises what it needs: in a corner of the courtyard, its gate toward the
# spire
inner = {s for s in cw.plot if min(s[0] - cw.gi, cw.gi + cw.w - 1 - s[0], s[1] - cw.gj, cw.gj + cw.h - 1 - s[1]) >= 3}
graveyard = None
for r_ in (14, 16, 12, 18):
    for a_ in range(12):
        c_ = (court_c[0] + r_ * math.cos(a_ * math.pi / 6 + 0.3), court_c[1] + r_ * math.sin(a_ * math.pi / 6 + 0.3))
        before = set(land.taken)
        y_ = Y.plan(land, rng, "graveyard", c_, toward=court_c, arch="pen")
        if y_ and {(y_.gi + a, y_.gj + b) for a in range(-1, y_.w + 1) for b in range(-1, y_.h + 1)} <= inner:
            graveyard = y_; break
        land.taken = before
    if graveyard: break
print(f"graveyard: {'at ' + str((graveyard.gi, graveyard.gj)) if graveyard else 'NONE'}")

# ---- 3. no buildings but the spire: the land grows round the court ---------------------------------------------------
sm = StoryMap(m, rng, land, ID)
placed = []
cw.release()

# ---- 4. the land: the heath grows round everything, the courtyard all land --------------------------------------------
land.carve(margin=3.5)
cw.fill()
C = {k: land.areas[k]["c"] for k in AREAS}
road_c, burn_c, heath_c, appr_c, north_c, stocks_c = (C[k] for k in ("road", "burners", "heath", "approach", "north",
                                                                       "stocks"))
lane_ = sm.keep_open({"road": 4, "burners": 7, "heath": 6, "approach": 6, "north": 3, "stocks": 7})
# (few clumps in the open places: rays of sight between many clumps crash the client, CL-1)
calm_ = {s_ for s_ in land.squares if any(math.hypot(s_[0] - c_[0], s_[1] - c_[1]) < r_ for c_, r_ in
                                          ((burn_c, 16), (heath_c, 17), (stocks_c, 12), (road_c, 9), (appr_c, 9)))}
clumps = land.thickets(60, size=(1.2, 2.2), clear=1, avoid=frozenset((lane_ | cw.plot | calm_) & land.squares))
land.open_links()
land.squares -= cw.forb
land.apply(m, wall=FORESTS[FOREST]["wall"], floor="GrassSparse2", unlevel=True)
gates = cw.build(m, prefix={"j0": "SouthGate", "j1": "NorthGate"}, lock={"j1": "Mechanism"})
assert "j1" in gates and "j0" in gates, "the roads do not cross the wall where the gates go"
if graveyard: Y.build(m, rng, land, graveyard)
land.ground_variety(m, base="GrassSparse2", sparse="GrassSparseYellow", dense="GrassNormYellow", clear=3)
# bare earth and dead grass in patches of their own over the heath's grasses, so floors meet three at a time as on
# Westwood's moors (a field of its own for each, as kit/biome Dresser.ground lays its patches)
HEATH = ("GrassSparse2", "GrassSparseYellow", "GrassNormYellow")
near_ = bfs_distance([s_ for s_ in land.squares if m.floor.get(square_tile(*s_)) not in HEATH] + list(land.taken),
                     land.squares, 2)
for mat_, f_, th_ in (("DirtLight2", 0.23, 1.55), ("GrassDense", 0.19, 1.6)):
    ph_ = [rng.uniform(0, 6.3) for _ in range(3)]
    for s_ in land.squares:
        t_ = square_tile(*s_)
        if m.floor.get(t_) not in HEATH or near_.get(s_, 99) < 2 or s_ in cw.plot: continue
        i_, j_ = s_
        n_ = math.sin(i_ * f_ + ph_[0]) + math.sin(j_ * f_ * 1.3 + ph_[1]) + 0.6 * math.sin((i_ + j_) * f_ * 0.7 + ph_[2])
        if n_ > th_: m.floor[t_] = mat_

# the Gate Hall: the spire's ground floor on the court's land, its door toward the south gate
m.room(*TOWER, wall="GalavaTownWall", floor="GalavaBrick")
tower_tiles = set(rect_tiles(*TOWER))
for t_ in tower_tiles: m.indoor[t_] = "GalavaBrick"
door_gap = tuple(int(c) for c in uv_to_xy(KU, TOWER[2]))
tdoor = m.door(None, door_gap, "\\")
land.wall_cells |= set(rect_wall_cells(*TOWER))
gate_hall = Room(id="gatehall", tiles=tower_tiles, floor="GalavaBrick", walls=rect_wall_cells(*TOWER),
                 doors=[Door(gap=door_gap, line="\\", type=tdoor["type"], connects=("gatehall", "outside"),
                             px=(tdoor["x"], tdoor["y"]))], kind="guardroom", building="the Hollow Spire")

# ---- the upper floors, each a walled-off room of its own in the grid's south-east corner ------------------------------
BONE = (326, 370, 30, 66)          # the Bone Hall: the Choir's quarters (barracks)
CELL_R = (370, 384, 40, 56)        # the cell off the Bone Hall's south-east wall
LIB = (348, 388, -50, -18)         # the Library of Voices
SONG = (404, 448, -12, 28)         # the Singing Chamber, the spire's top
for R_ in (BONE, CELL_R, LIB, SONG):
    assert R_[0] >= FAR_U, R_
m.room(*BONE, wall="GalavaTownWall", floor="GalavaBrick")
m.room(*CELL_R, wall="GalavaTownWall", floor="GalavaBrick")
m.room(*LIB, wall="GalavaTownWall", floor="GalavaBrick")
m.room(*SONG, wall="LOTDOrnate", floor="LOTDBlackMarble")
cell_gap = tuple(int(c) for c in uv_to_xy(CELL_R[0], 48))
cdoor = m.door("JailDoor", cell_gap, "/")
cdoor["scr"] = "AnselCell"
cdoor.setdefault("xfer", {})["LockType"] = "Mechanism"
cell_door = Door(gap=cell_gap, line="/", type="JailDoor", connects=("bonehall", "cell"), px=(cdoor["x"], cdoor["y"]))
bone_hall = Room(id="bonehall", tiles=set(rect_tiles(*BONE)), floor="GalavaBrick", walls=rect_wall_cells(*BONE),
                 doors=[cell_door], kind="barracks", building="the Hollow Spire")
cell_room = Room(id="cell", tiles=set(rect_tiles(*CELL_R)), floor="GalavaBrick", walls=rect_wall_cells(*CELL_R),
                 doors=[cell_door], kind="cell", building="the Hollow Spire")
library = Room(id="library", tiles=set(rect_tiles(*LIB)), floor="GalavaBrick", walls=rect_wall_cells(*LIB), doors=[],
               kind="library", building="the Hollow Spire")
chamber = Room(id="chamber", tiles=set(rect_tiles(*SONG)), floor="LOTDBlackMarble", walls=rect_wall_cells(*SONG),
               doors=[], kind="dark_chapel", building="the Hollow Spire")
FLOORS = [gate_hall, bone_hall, cell_room, library, chamber]

# where each transporter's ends stand (kit/transport STAIRS castle and the lift's and pads' rules: open floor, off the
# walls; the flight down in the upper room's west corner, the flight up against the lower room's north-east wall)
geo = tp_geometry()["stairs"]
STAIR_DOWN = px(BONE[0] + 5, BONE[2] + 6)
STAIR_UP = px(KU + 4, TOWER[3] - 2)
LIFT_A = px(BONE[1] - 7, BONE[3] - 7)                 # the bone lift's platform, in the Bone Hall's north corner
LIFT_B = px(LIB[0] + 7, LIB[3] - 7)                   # its pit in the Library
SONG_A = px(LIB[1] - 7, LIB[2] + 7)                   # the song gate's pad in the Library's south corner
SONG_B = px(SONG[0] + 7, SONG[3] - 8)                 # its pad in the Singing Chamber's west corner
DOOR_A = px(SONG[0] + 7, SONG[2] + 8)                 # the Choir's door down, in the Chamber's south corner
MORV = px(SONG[1] - 9, (SONG[2] + SONG[3]) / 2)       # where Morvaine sings, across the chamber


def stairs_zone(main, at):
    g = geo[main]
    pts = [at, (at[0] + g["pad"][0], at[1] + g["pad"][1]), (at[0] + g["arrive"][0], at[1] + g["arrive"][1])]
    pts += [(at[0] + dx, at[1] + dy) for _, dx, dy in g["pieces"]]
    return pts


def clear_round(pts, r, keep=()):
    """Takes out the furniture within r px of the points (the transporters and their landings stay clear)."""
    keep = {id(o) for o in keep}
    gone = [o for o in m.d["objects"] if id(o) not in keep and "x" in o and "clone" not in o and
            any(math.hypot(o["x"] - x, o["y"] - y) < r for x, y in pts)]
    ids = {id(o) for o in gone}
    m.d["objects"][:] = [o for o in m.d["objects"] if id(o) not in ids]
    return gone


for room_, kind_, style_ in ((gate_hall, "guardroom", "town"), (bone_hall, "barracks", "town"),
                             (cell_room, "cell", "town"), (library, "library", "town"), (chamber, "dark_chapel", "lotd")):
    furnish_original(m, room_, kind=kind_, rng=random.Random(SEED * 31 + len(room_.id)), style=style_)
clear_round(stairs_zone("GalavaStairsUp1", STAIR_UP), 62)
clear_round(stairs_zone("GalavaStairsDown", STAIR_DOWN), 62)
clear_round([LIFT_A, LIFT_B], 58)
clear_round([SONG_A, SONG_B, DOOR_A], 76)
clear_round([MORV], 50)
for p_ in (LIFT_A, LIFT_B, SONG_A, SONG_B, DOOR_A):
    m.obj_px("ColorLight", p_[0], p_[1] - 6, xfer=preset("blue", "dim"))

# ---- 5. the places of the story on the heath -----------------------------------------------------------------------
DOORS_SQ = [px_square(tdoor["x"], tdoor["y"])]


def off_road(c, clear=3.5, reach=12, doors=5):
    """The square nearest `c` with no road within `clear` squares, on open land, `doors` squares from the spire's door."""
    near_road = bfs_distance(list(land.roads), land.squares, int(clear) + 1)
    cands = [s for s in land.squares if near_road.get(s, 99) >= clear and s not in land.taken_strict and
             s not in land.taken and math.hypot(s[0] - c[0], s[1] - c[1]) <= reach and
             all(math.hypot(s[0] - d[0], s[1] - d[1]) >= doors for d in DOORS_SQ)]
    s = min(cands, key=lambda s: math.hypot(s[0] - c[0], s[1] - c[1])) if cands else (int(c[0]), int(c[1]))
    return (s[0] + 0.5, s[1] - 0.5)


def toward(a, b, dist):
    dx, dy = b[0] - a[0], b[1] - a[1]; l_ = math.hypot(dx, dy) or 1
    return (a[0] + dx * dist / l_, a[1] + dy * dist / l_)


# the charcoal-burners' camp: their fire and tents, a store with their chest, the dig where they cut wood for the kilns
burn_site = camps.camp_site(m, land, burn_c, reach=10, road_clear=3.0, room=7)
burn_camp = camps.bandit_camp(m, rng, land, burn_site, road_c, loot=[("Gold", {"Amount": 40}), "RedPotion", "Bread"],
                              sleepers=2, tents=2)
# the court: the Choir's bone-heaps by the walls and a gibbet of a fire where they burn what they do not raise
court_sc = camps.Scene(m, rng, land, toward(court_c, appr_c, 8.0))
for t_, r_, a_ in (("Skull", 1.0, 0.3), ("LegBone", 1.4, 1.2), ("ArmBone", 1.2, 2.4), ("CorpseRibCageS", 1.8, 3.6),
                   ("Skull", 2.0, 4.8), ("LegBone", 1.6, 5.6)):
    court_sc.put(t_, *court_sc.at(r_, a_))
# the landing of the Choir's door down from the top: in the court, beside the Gate Hall's door
land_sq = off_road(toward(court_c, appr_c, 6.0), clear=0.0, reach=6, doors=3)
DOOR_B = square_px(land_sq[0] + 3.0, land_sq[1] - 1.5)
# signposts
camps.signpost(m, land, (road_c[0] + 2.5, road_c[1] + 1.5),
               q.text("THE HOLLOW SPIRE\nTurn back, traveller. The Choir sings here.", "Sign"))
sg_ = sm.road_near(px_square(*cw.gate_px("j0", 5.0)))
camps.signpost(m, land, (sg_[0] + 2.0, sg_[1] - 1.5), q.text("THE SPIRE COURT\nNone enter who do not sing.", "Sign"))
ng_ = sm.road_near(px_square(*cw.gate_px("j1", -4.0)))
camps.signpost(m, land, (ng_[0] - 1.5, ng_[1] - 2.0), q.text("THE ROAD WEST\nBrackwater, eleven days.", "Sign"))
# the Choir's stocks on the hill: an old shrine's stump, the stocks before it, the bones of those who would not sing
shrine = camps.ruined_tower(m, rng, land, stocks_c, burn_c, loot=[("Gold", {"Amount": 75}), "BluePotion", "ChainCoif"],
                            size=(8, 8), material="StoneGray")
ssc = camps.Scene(m, rng, land, toward(stocks_c, burn_c, 7.0))
for t_, r_, a_ in (("Stocks1", 0.0, 0.0), ("Stocks2", 1.8, 1.0), ("Skull", 0.9, 2.0), ("LegBone", 1.3, 3.1),
                   ("CorpseRibCageS", 2.0, 4.2), ("Stocks3", 1.9, 5.0), ("ArmBone", 2.6, 5.8)):
    ssc.put(t_, *ssc.at(r_, a_))
camps.signpost(m, land, toward(stocks_c, burn_c, 10.0), q.text("THE CHOIR'S STOCKS\nFor those who will not sing.", "Sign"))
# caches on the heath
caches = []
for near_, loot_, stump_ in ((heath_c, [("Gold", {"Amount": 60}), "RedPotion", "BluePotion"], True),
                             (burn_c, [("Gold", {"Amount": 45}), "CurePoisonPotion", "RedPotion"], False),
                             (north_c, [("Gold", {"Amount": 50}), "RedPotion", "RedPotion"], False)):
    s_ = sm.hidden_spot(near_, r=(5, 13))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))

# ---- 6. planting: none in the court ----------------------------------------------------------------------------------
keep = set(cw.plot) | {px_square(*DOOR_B)}
planter = Planter(m, rng, land, FOREST, keep_clear=keep | lane_, settled=())
n_trees, n_small = planter.plant_all(groves=4, flowers=2)
piles = planter.rock_piles(max(4, len(land.squares) // 900))
vignettes = planter.forest_floor(max(6, len(land.squares) // 700))
start_xy = square_px(road_c[0] + 0.5, road_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
exit_next(sm, "north", 9, prefix="HomeExit")

# ---- the transporters (skills/nox-transporters): each to its floor, each with its purpose -----------------------------
tp = Transporters(m)
pop, B = sm.pop, sm.B
mods = Mods(m, pop)
stair = tp.add("stairs", STAIR_DOWN, STAIR_UP, "SpireStair", style="castle")
lift = tp.add("lift", LIFT_A, LIFT_B, "BoneLift", style="castle")
song = tp.add("portal", SONG_A, SONG_B, "SongGate", serves=[MORV])
down = tp.add("portal", DOOR_A, DOOR_B, "ChoirDoor", two_way=False, enabled=False)
for p_ in (DOOR_B,):
    s_ = px_square(*p_)
    land.taken |= {(s_[0] + a, s_[1] + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}

# ---- 7. the people ---------------------------------------------------------------------------------------------------
person, free_px = sm.person, sm.free_px
ax_, ay_ = square_px(*appr_c)
cx_, cy_ = square_px(*court_c)
# Merra and Osk at the burners' camp, by their fire
burn_posts = camp_posts(m, burn_camp, square_px(*road_c), sit=1, tents=1, watch=0, work=0)
person("Con02a", "Gretchen", *burn_posts["leader"], "Merra", face=burn_camp["fire"])
person("Con03B", "Naldo", *(burn_posts["sit"] + burn_posts["tent"])[0], "Osk", face=burn_camp["fire"])
mx_, my_ = burn_posts["leader"]
# Ansel, home again (out of the play until he is freed): beside Merra
hx_, hy_ = burn_camp["fire"]
ad_ = math.hypot(mx_ - hx_, my_ - hy_) or 1
person("Con03B", "Logan", mx_ + (my_ - hy_) / ad_ * 46, my_ - (mx_ - hx_) / ad_ * 46, "AnselHome",
       face=burn_camp["fire"])
# Captain Ilsa and two of the watch at the court's south gate (out of the play without the watch's seal)
sgx, sgy = cw.gate_px("j0", 4.5)
gdx, gdy = sgx - ax_, sgy - ay_
gl_ = math.hypot(gdx, gdy) or 1
gdx, gdy = gdx / gl_, gdy / gl_                                     # from the approach toward the gate
wait_ = (sgx - gdx * 110, sgy - gdy * 110)
cast_person(sm, "Ilsa", wait_[0] - gdy * 70, wait_[1] + gdx * 70, face=(sgx, sgy))
person("Con02a", "IxGuard2", wait_[0] + gdy * 70, wait_[1] - gdx * 70, "SpireWatch1", face=(sgx, sgy))
person("Con02a", "Mayor's_Guard", wait_[0] - gdx * 60, wait_[1] - gdy * 60, "SpireWatch2", face=(sgx, sgy))
# Rusk and his crew in the Bone Hall (out of the play without Rusk's promise)
bx_, by_ = px((BONE[0] + BONE[1]) / 2, (BONE[2] + BONE[3]) / 2)
rk_ = free_px(bone_hall, prefer=px(BONE[0] + 10, BONE[2] + 14), clear=34)
cast_person(sm, "Rusk", *rk_, face=(bx_, by_))
crew = []
for k, pref_ in enumerate((px(BONE[0] + 16, BONE[2] + 8), px(BONE[0] + 8, BONE[2] + 20))):
    n = f"RuskMan{k + 1}"
    person("War01A", ("Jesse", "Daniel")[k], *free_px(bone_hall, prefer=pref_, clear=34), n, face=(bx_, by_))
    crew.append(n)
# Ansel in his cell
an_ = free_px(cell_room, clear=26)
person("Con03B", "Logan", *an_, "Ansel", face=(cdoor["x"], cdoor["y"]))

# ---- 8. the fights ---------------------------------------------------------------------------------------------------
# the court: the Choir's blades at the gate's inside, the raised dead by the bone-heaps
court_foes = []
for k, (t_, d_, s_) in enumerate((("Swordsman", 5.0, 2.5), ("Swordsman", 5.5, -2.5), ("Skeleton", 9.0, 3.5),
                                   ("Skeleton", 9.0, -3.5), ("Archer", 11.0, 0.0))):
    c_ = toward(court_c, appr_c, 21.0 - d_ * 0.8)        # between the south gate and the Gate Hall's door
    dx_, dy_ = appr_c[0] - court_c[0], appr_c[1] - court_c[1]
    l2 = math.hypot(dx_, dy_) or 1
    sq_ = (c_[0] - dy_ / l2 * s_, c_[1] + dx_ / l2 * s_)
    n = f"CourtFoe{k + 1}"
    pop.creature(t_, *square_px(*sq_), action="guard", scr=n, aggr=0.83, face=(sgx, sgy))
    court_foes.append(n)
B.sentry("CourtFoe5", (sgx, sgy), rouse=court_foes[:4], shout="Intruder at the gate! Sing them down!")
# the Gate Hall: its wardens
hall_foes = []
for k, (t_, pref_) in enumerate((("SkeletonLord", px(KU, KV + 6)), ("Swordsman", px(KU - 6, KV - 2)),
                                  ("Swordsman", px(KU + 6, KV - 2)))):
    n = f"HallFoe{k + 1}"
    pop.creature(t_, *free_px(gate_hall, prefer=pref_, clear=30), action="guard", scr=n, aggr=0.83,
                 face=(tdoor["x"], tdoor["y"]))
    hall_foes.append(n)
# the Bone Hall: the Choir's blades at their quarters, the jailer before the cell
bone_foes = []
for k, (t_, pref_) in enumerate((("Swordsman", px(BONE[0] + 24, BONE[2] + 10)), ("Swordsman", px(BONE[0] + 30, BONE[2] + 22)),
                                  ("Archer", px(BONE[0] + 20, BONE[3] - 6)), ("Skeleton", px(BONE[0] + 14, BONE[3] - 8)))):
    n = f"BoneFoe{k + 1}"
    pop.creature(t_, *free_px(bone_hall, prefer=pref_, clear=30), action="guard", scr=n, aggr=0.83,
                 face=STAIR_DOWN)
    bone_foes.append(n)
pop.creature("OgreBrute", *free_px(bone_hall, prefer=px(BONE[1] - 6, 50), clear=30), action="guard", scr="Jailer",
             aggr=0.83, face=STAIR_DOWN)
bone_foes.append("Jailer")
# the Library: its Cantor (a Bone Caller) and two blades; the Choir's chest
lib_foes = []
mods.monster("M3", *free_px(library, prefer=px((LIB[0] + LIB[1]) / 2, (LIB[2] + LIB[3]) / 2), clear=30),
             name="LibCantor", hp=300, wait=240, face=LIFT_B)
lib_foes.append("LibCantor")
for k, pref_ in enumerate((px(LIB[0] + 14, LIB[2] + 8), px(LIB[1] - 10, LIB[3] - 8))):
    n = f"LibBlade{k + 1}"
    pop.creature("Swordsman", *free_px(library, prefer=pref_, clear=30), action="guard", scr=n, aggr=0.83, face=LIFT_B)
    lib_foes.append(n)
lib_chest = m.obj_px("Chest4", *free_px(library, prefer=px(LIB[1] - 4, LIB[3] - 4), clear=30),
                     items=[("Gold", {"Amount": 110}), "BluePotion", "RedPotion", "RedPotion", "SteelHelm"])
# the Singing Chamber: High Caller Morvaine (Bone Caller, M3, as a named boss) and two Skeleton Lords of his honour guard
mods.monster("M3", *MORV, name="Morvaine", hp=FOES["Morvaine"]["hp"], wait=280, face=SONG_B)
top_foes = ["Morvaine"]
for k, sgn in enumerate((1, -1)):
    n = f"HonourGuard{k + 1}"
    pop.creature("SkeletonLord", MORV[0] - 90 + sgn * 40, MORV[1] + sgn * 60, action="guard", scr=n, aggr=0.83,
                 face=SONG_B)
    top_foes.append(n)
# Vess, out of the dark behind the altar (out of the play without her oath): the Blink Duelist's body, on our side
vx2, vy2 = free_px(chamber, prefer=px(SONG[1] - 6, SONG[2] + 6), clear=30)
pop.creature("Swordsman", vx2, vy2, action="idle", scr="Vess", aggr=0.0, face=MORV, spread=False,
             HealthMultiplier=FOES["Vess"]["hp"] / 150.0)
# the woman she is when the fight is done (her body and voice as in act 4: kit/campaign CAST["Vess"]), out of the play
# until Morvaine falls with Vess still standing; she says her piece and steps through space
person(CAST["Vess"]["donor"][0], CAST["Vess"]["donor"][1], vx2 + 40, vy2, "VessTalk", face=MORV)
# the punished dead in the shrine's stump on the stocks hill
stocks_dead = []
for k, (x, y) in enumerate(shrine["inside"][:3]):
    n = f"StocksGhost{k + 1}"
    pop.creature("Ghost", x, y, action="guard", scr=n, aggr=0.83, face=square_px(*burn_c))
    stocks_dead.append(n)
# the heath's walking dead by the cliffs, away from the road and the camp
heath_foes = []
for k, a_ in enumerate((0.4, 1.9, 3.5, 5.0)):
    n = f"HeathDead{k + 1}"
    pop.creature("Ghost" if k % 2 else "Skeleton", *square_px(heath_c[0] + 4.5 * math.cos(a_), heath_c[1] + 4.5 * math.sin(a_)),
                 action="guard", scr=n, aggr=0.83, face=square_px(*appr_c))
    heath_foes.append(n)
sm.wild({"Bat": 2, "Wolf": 2, "Skeleton": 1}, away_from=square_px(*court_c), per100=0.25, gap=7, min_away=24,
        avoid=(road_c, burn_c, appr_c, heath_c, north_c, court_c, stocks_c))
story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]
            if px_square(o["x"], o["y"]) in land.squares] + [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)

# ---- 9. the allies (kit/hc_scripts): the watch goes with the player; Rusk's crew holds the Bone Hall; Vess the top ----
ALL_FOES = court_foes + hall_foes + bone_foes + lib_foes + top_foes
for n_, dmg_ in (("Ilsa", 7), ("SpireWatch1", 10), ("SpireWatch2", 10)):
    hc.ally(n_, ALL_FOES, follow=True, dmg=dmg_)
for n_ in ["Rusk"] + crew:
    hc.ally(n_, bone_foes, follow=False, home=(bx_, by_), hold=430, dmg=12)
hc.ally("Vess", top_foes, follow=True, dmg=14, blink=True, hp=FOES["Vess"]["hp"])
WATCH, CREW = ["Ilsa", "SpireWatch1", "SpireWatch2"], ["Rusk"] + crew
hc.on_flag("watch_go", hc.allies_go(*WATCH))
hc.on_flag("rusk_go", hc.allies_go(*CREW))
hc.on_flag("vess_go", hc.allies_go("Vess") + hc.wake("Morvaine"))     # he wakes to her blade
hc.on_flag("morvaine_dead", hc.allies_release(*WATCH, *CREW, "Vess"), hc.later(2, hc.swap("Vess", "VessTalk")))
hc.on_flag("vess_farewell", hc.later(2, hc.vanish("VessTalk")))
hc.on_flag("ansel_free", hc.later(1, [f'flags["ansel_home"] = true']))

# ---- 10. the story ---------------------------------------------------------------------------------------------------
MAIN = "Climb the Hollow Spire and kill High Caller Morvaine."
q.start([A.lock("NorthGate1"), A.lock("NorthGate2"), A.lock("AnselCell"), A.disable("HomeExit1"),
         A.disable("HomeExit2"), A.disable("HomeExit3"), A.disable("AnselHome"), A.disable("Vess"),
         A.disable("VessTalk")] +
        [A.disable(n) for n in WATCH + CREW] +
        [q.journal(MAIN, QUEST)])
# the choices of act 1 and 4, read from what the player carries
q.when_true(has("WATCH_SEAL"), [A.enable(n) for n in WATCH] + [A.flag("watch_here")])
q.when_true(has("RUSK_KNIFE"), [A.enable(n) for n in CREW] + [A.flag("rusk_here"), A.flag("rusk_go")])
q.near(sgx, sgy, 150, [A.flag("watch_go")], when=q.when(flag="watch_here"))
q.near(*SONG_B, 260, [A.enable("Vess"), A.flag("vess_go"),
                      A.chat("Vess", "You sent me to die on the ice, Morvaine. I came back to return the favour."),
                      A.print("A figure steps out of the dark behind the altar. Vess! Her blade is turned on Morvaine.")],
       when=q.when(has=token("VESS_OATH")))
q.near(*SONG_B, 240, [A.chat("Morvaine", "The sellsword climbs to the top of my spire. Then hear the last verse, and "
                                         "be still."),
                      A.print("At the far end of the chamber the High Caller turns from his altar.")])
# what the player sees on the way
q.near(*square_px(*stocks_c), 300, [A.print("Stocks on the hilltop, and bones in them. Pale shapes drift in the old "
                                            "shrine's stump.")])
q.near(*STAIR_DOWN, 220, [A.print("The Bone Hall. It smells of old bones and new blood.")])
q.near(*LIFT_B, 220, [A.print("Shelves of books in a dead tongue. A lamp still burns on the reading desk.")])
q.near(*lib_chest and (lib_chest["x"], lib_chest["y"]), 160,
       [A.print("A letter lies open on the reading desk, in Morvaine's hand: the Brood will break loose under "
                "Brackwater, where the first bell hangs."),
        q.journal("Hurry home: Morvaine's letter says the Brood will rise under Brackwater.", NOTE)])
q.on_death("Jailer", [A.unlock("AnselCell"), A.print("The jailer falls. His keys clatter across the floor; the cell "
                                                     "door swings loose.")])
q.on_death("Morvaine", [A.drop(STONE), A.drop(STONE), A.flag("morvaine_dead"), A.unlock("NorthGate1"),
                        A.unlock("NorthGate2"), A.enable("HomeExit1"), A.enable("HomeExit2"), A.enable("HomeExit3")] +
                       [A.enable(n) for n in down.sources] +
                       [A.print("High Caller Morvaine falls, and his song with him. Two Spirit Stones roll from his "
                                "hand, red stones that hum: the first and third bells' clappers. A pentagram flares at the chamber's door: the Choir's way down."),
                        q.done(MAIN),
                        q.journal("Take the Spirit Stones home to Brackwater by the road beyond the spire's north "
                                  "gate.", QUEST)])
q.near(*DOOR_B, 130, [A.print("Far off to the north, the spire's north gate stands open.")],
       when=q.when(flag="morvaine_dead"))
for n_ in top_foes + lib_foes:
    q.names.add(n_)
# Captain Ilsa and the watch
q.talker("Ilsa", [
    q.say("That's the High Caller finished. Now home. If the Brood is loose under Brackwater, I want my watch on the "
          "square.", when=q.when(flag="morvaine_dead"), who="Ilsa"),
    q.say("Lead on! We're right behind you.", when=q.when(flag="watch_go"), who="Ilsa"),
    q.say("There you are. The Baron's riders said you'd come this way, so I brought two of my best. You carry the "
          "warrant I sealed for you -- the watch goes where its warrant goes. Up the spire, then!",
          do=[A.flag("watch_go"), q.note("Captain Ilsa and two of the watch fight at your side.")], who="Ilsa")],
    voice=voice("Ilsa"))
for k, n_ in enumerate(("SpireWatch1", "SpireWatch2")):
    q.talker(n_, [
        q.say(("Home, then. I've seen enough of this place.", "Brackwater! Never thought I'd miss the smell of it.")[k],
              when=q.when(flag="morvaine_dead"), who=n_),
        q.say(("Stay close, we'll take the ones on your flanks!", "Captain's orders. Where you go, we go.")[k],
              who=n_)], title="Watchman")
# Vess, when Morvaine has fallen with her blade in him
q.talker("VessTalk", [
    q.say("He sent me onto the ice to die, and now he lies cold himself. My oath is kept. Ring your bells, sellsword. "
          "And do not look for me.", do=[A.flag("vess_farewell")], who="Vess", mood="Cool and level, unhurried.")],
    title="Vess", voice=voice("Vess"))
# Rusk and his crew in the Bone Hall
q.talker("Rusk", [
    q.say("Dead, is he? Then I'd say my debt's paid twice over. Brackwater, is it? We'll be along. Probably.",
          when=q.when(flag="morvaine_dead"), who="Rusk"),
    q.say("The floor's ours! Not bad for a bunch of cutthroats, eh? Go on up. We'll keep the stair for you.",
          when=q.when(flag=q.dead(*bone_foes)), who="Rusk"),
    q.say("About time! You kept my lucky charm, then. A promise is a promise -- me and the lads came up the sewer and "
          "took this floor. Well, most of it! Get stuck in!", who="Rusk")],
    voice=voice("Rusk"))
for k, n_ in enumerate(crew):
    q.talker(n_, [
        q.say(("Rusk said you'd come. Rusk says a lot of things.", "Mind the bones, they still twitch.")[k], who=n_)],
        title="Cutthroat")
# Merra and the Spire's Prisoner
q.talker("Merra", q.errand(
    "Merra", "ansel",
    offer="Stranger! You're going up there? Into the spire? The Choir took my husband Ansel a week ago. They said "
          "Morvaine wanted strong backs.\n\nThey keep their prisoners in a cell off the hall above the gate. If he's "
          "alive, he's there.\n\nBring him out and I'll pay you all I have. Will you look for him?",
    reminder="Is he alive? Please, just tell me he's alive.",
    thanks="Ansel! He came down the road at a run, filthy and laughing! You did it!\n\nHere, take this. All of "
           "it. We'll burn charcoal for a year to fill that purse again, and gladly!",
    after="Ansel sleeps by the fire now. He won't go near a stair.",
    objective="Find Merra's husband Ansel in the Hollow Spire's cells.",
    done=q.when(flag="ansel_home"), reward=[A.gold(140), A.give("RedPotion", 3), A.give("LeatherArmoredBoots")],
    refusal="Then I'll pray someone braver comes along this road.") + [])
q.talker("Ansel", [
    q.say("Go on up, I'll find my own way down. Tell Merra I'm coming!", when=q.when(flag="ansel_free"), who="Ansel"),
    q.say("The jailer's dead? Ha! Then I'm off -- down the stair and out, and I won't stop running till I see "
          "Merra's fire. Thank you!",
          when=q.when(flag=q.dead("Jailer"), not_="ansel_free"),
          do=[A.flag("ansel_free"), A.disable("Ansel"), A.enable("AnselHome"),
              q.journal("Return to Merra at the burners' camp.", NOTE)], who="Ansel"),
    q.say("Psst! Over here! Kill that brute and get me out of this cage!", who="Ansel")])
q.talker("AnselHome", [
    q.say("Merra's feeding me burnt bread and I've never been happier.", who="AnselHome")], title="Ansel")
q.talker("Osk", [
    q.say("The singing's stopped. First quiet night in a month.", when=q.when(flag="morvaine_dead"), who="Osk"),
    q.say("We sell charcoal to the spire. Did. Before the singing. Now we just keep our heads down.", who="Osk")])
for who_, pic_ in (("VessTalk", "MaidenPic6"), ("Ilsa", "IngridPic"), ("SpireWatch1", "IxGuard2Pic"), ("SpireWatch2", "Warrior2Pic"),
                   ("Rusk", "MalePic9"), ("RuskMan1", "MalePic11"), ("RuskMan2", "MalePic12"), ("Merra", "MaidenPic3"),
                   ("Ansel", "MalePic9"), ("AnselHome", "MalePic9"), ("Osk", "Townsman2Pic")):
    q.portrait(who_, pic_)

mods.attach(B)
m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())
m.scripts.update(hc.files())

# ---- 11. the exteriors' dressing -----------------------------------------------------------------------------------------
dressed = Exterior(m, land, "green", placed=placed, martial=True).dress()


class _Far:                                          # the spire's floors, for the rooms sidecar
    def __init__(self, rooms): self.rooms = rooms


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar([(BuildingIdentity("tower", "court", "the Hollow Spire", "High Caller Morvaine"), _Far(FLOORS))],
                  os.path.join(OUT, f"{NAME}.rooms.json"), yards=[graveyard] if graveyard else [])
    from kit.campaign import apply_deliveries
    apply_deliveries(q)            # voice-gate deliveries (kit/campaign.py DELIVERIES)
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS", "VOICE"))))
    print(f"land {len(land.squares)} squares | trees {n_trees} | caches {len(caches)} | opened {len(opened)} "
          f"| lines {len(q.strings)} | dressing {sum(dressed.values())} groups")
