"""Thornkeep: the Baron's walled town on the high road east, and act 5 of The Hollow Choir (campaign/hollowchoir/
BIBLE.md; the cast, tokens and chain are mapgen/kit/campaign.py). The green world in pines, FORESTS["pine"]. The town
inside a curtain wall (kit/story.Curtain: Galava town wall, corner towers, the west gate and the east gate) round the
keep's square; the foregate outside the west gate; under it all, the old sewers and the Chancellor's dungeon.

The transporters (skills/nox-transporters), each to a place of its own drawn walled off in the south-east of the grid:
- The old outfall (passage, two-way): the sewer's great pipe in the ravine south of the walls, where the river-rats and
  smugglers go in and out, into the Old Sewers. Why: the way into Thornkeep for a player without the watch's warrant
  (choice A, act 1); and the way down for Brenna's errand. Open from the start.
- The cistern lift (lift, dungeon style: CaveElevator on its base): in the back lane of the town, the well-diggers'
  old lift down to the shaft chamber of the Old Sewers. Two-way by nature: up into the town from the sewers, down to
  the cistern from the town. Open from the start.
- The gaol stair (stairs, castle): the old gaol tower in the courtyard (a guard room, the stair down in its west
  corner) to the Chancellor's dungeon (the stair hall, the cells, the question room), drawn elsewhere. Why: Tam Fell is
  held there. Two-way. The tower's door is locked until the gaoler lets the player in (Tam's satchel, or the watch's
  rumour after the Baron's audience).

The story
- The player comes up the west road from Frosthollow (act 4), after the Choir: the Choir has a friend at the Baron's
  court, and Baron Aldric Thorne has the only men in the north who could stand against it. The west gate is shut: by
  the Chancellor's order no stranger enters Thornkeep. Dobbin the pedlar, waiting outside it, says so (the hook).
- Choice A (act 1) at the west gate: with WATCH_SEAL (the Brackwater watch's warrant, sealed by Captain Ilsa), Captain
  Osmund of the gate honours it and opens the gate. Without it the gate stays shut; Dobbin knows the old outfall in
  the ravine south of the walls, where the river-rats get in. In the sewers Nettle the fence deals with smugglers;
  with RUSK_KNIFE (Rusk's lucky charm, his promise, act 1) he knows it and gives the player potions and a word about the old
  gaol. The cistern lift at the sewers' far end comes up in the town's back lane. A player with neither token takes
  the sewers.
- Main quest, the Chancellor's Shadow: the Baron hears the player in his throne room and will not march on a tale
  his Chancellor calls bandits' work; he wants proof. Tam Fell (Wenna's brother, The Missing Brother: acts 1, 2, 5,
  10), the bell-ringer's apprentice the Choir took to read the bells' old script, is held in the dungeon under the old
  gaol tower. With TAM_SATCHEL (act 2: the Choir's order to take "the ringer's boy" to Thornkeep) the player knows to
  look there: Gaoler Moss knows the satchel's mark and opens the tower. Without it, once the player has seen the
  Baron, a watchman's rumour (the Chancellor's men took a boy down to the old cells by night) leads there; the gaoler
  opens the tower then. In the dungeon the Chancellor's men hold the cells; with them dead Tam's cell opens and he is
  freed: TAM_FREED (his bell-token, given in thanks), the satchel given back to him. Tam names his jailer: Chancellor
  Severin, who brought him the High Caller Morvaine's letters each night to read. Tam goes up to wait at the inn.
  With Tam's word the player puts it to Severin (a yes/no question in his study): Severin drops the mask (A.turn),
  a caller of the Choir (the Bone Caller, M3, woken late by kit/hc_story), his two hired swords out of the keep's
  stores. Severin dead, the Baron, ashamed, has read his Chancellor's papers: the Choir's seat is the Hollow Spire
  beyond the Ogre Marches, and it gathers the stolen stones at the Emberforge, the founders' forge in the fire
  mountains, to wake the Matriarch; the warlord Gruthak holds the Marches road, paid with a stolen stone. He pays and
  opens the east gate on the road to the Ogre Marches (act 6: the exit).
- Foul Water (local): the town well has gone foul. Brenna the alewife asks the player to go down into the sewers and
  clear the Giant Leeches nesting in the old cistern under the well. She pays in potions and gold.
- The Pedlar's Ruby (local): Urchins in the west wood stole Dobbin's ruby, his whole stake, while he slept outside the
  shut gate. He pays from his pack.
- The inn, the trading post and the armourer buy and sell. Nettle's stash, the question room's chest, two caches in
  the pines and the houses' stores hold loot; every soul in the town knows something.

    py mapgen/designs/hc05_thornkeep.py [seed]
"""
QA_ACCEPT = [   # (tests/qa.py)
    # the houses are the kit's own (generate_building + the furnisher at master 2026-10-09): every map rebuilt today
    # gets these (Ironcrag accepts the same, Thornwick's rebuild had 14); a room-lab matter, not this map's. The seed
    # was chosen from 8 tried for the fewest warnings (and the sight check's margin)
    ("composition", r"is sparse: furniture covers",
     "the kit's furnisher fills small house rooms under the half-median house rule on every map at master (Ironcrag, "
     "Thornwick); the room lab's work, not this map's"),
]
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL, px, uv_to_xy, rect_tiles, rect_wall_cells
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import Land, square_tile, square_px, px_square, bfs_distance
from kit.vegetation import Planter, FORESTS, TOWN_PLANTING
from kit.village import Village
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT, NOTE
from kit.model import Room, Door
from kit.originality import furnish_original
from kit.transport import Transporters, geometry as tp_geometry
from kit import camps
from kit import yards as Y
from kit.story import StoryMap, Curtain
from kit.posts import camp_posts
from kit.dressing import Exterior
from kit.mods import Mods
from kit.hc_story import HcStory
from kit.campaign import act, token, has, cast_person, voice, exit_next, CAST

ACT = 5
NAME = act(ACT)["map"]                # Thornkeep
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 8
rng = random.Random(SEED)
FOREST = "pine"
PATH = "DirtDark2"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "hc05_thornkeep")
FAR_I = 180                           # squares: the grid with i >= this is the far places' (never the town's land)
RUBY = "Ruby"                         # Dobbin's ruby (a gem the player can carry)


def uv(X, Y):
    """uv of a point given in map cells as seen on screen (X right, Y down, 0..255)."""
    return (X + Y, X - Y)


def P(X, Y):
    """World px of a map cell point."""
    return (X * CELL, Y * CELL)


def sq_of(X, Y):
    """Continuous square coordinates (for square_px and camps.Scene) of a map cell point."""
    return ((X + Y - 1) / 2, (X - Y - 1) / 2)


ID = MapIdentity(
    name=NAME,
    theme="the Baron's walled town on the high road east: a curtain wall with corner towers round the keep's square, "
          "the keep, the barracks, the inn, the trading post, the armourer and the old gaol tower; the foregate's "
          "houses outside the shut west gate, an Urchins' den in the west wood, the old outfall in the ravine; under "
          "the town the old sewers and the Chancellor's dungeon",
    environment="town", mood="guarded, suspicious, proud",
    areas=[AreaIdentity("west", "the west road out of the pines from Frosthollow: the start"),
           AreaIdentity("foregate", "the houses outside the shut west gate"),
           AreaIdentity("town", "Thornkeep's square inside the curtain wall", landmark="Well"),
           AreaIdentity("east", "the east road beyond the east gate: the way to the Ogre Marches"),
           AreaIdentity("outfall", "the ravine south of the walls where the old sewer runs out"),
           AreaIdentity("den", "the Urchins' den in the west wood"),
           AreaIdentity("bailey", "the garrison's yard inside the walls, the barracks and the training ground")],
    buildings=[BuildingIdentity("keep", "town", "the keep", "Baron Aldric Thorne and Chancellor Severin"),
               BuildingIdentity("bunkhouse", "bailey", "the barracks", "the Baron's garrison", style="stone_house"),
               BuildingIdentity("inn", "town", "The Thorn and Crown", "the innkeeper"),
               BuildingIdentity("store", "foregate", "the trading post", "the trader"),
               BuildingIdentity("smithy", "town", "the armourer's forge", "the armourer"),
               BuildingIdentity("home", "foregate", "", "a carter's family"),
               BuildingIdentity("home", "foregate", "", "a tanner's family"),
               BuildingIdentity("cottage", "foregate", "", "an old woman who takes in washing")])

m = Spec(NAME, summary=act(ACT)["title"], description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"The Hollow Choir, act {ACT}. Generated by Claude.", author="vdystopia (generated by Claude)", version="1",
         date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [134, 134, 132]
q = QuestBook(NAME)
presets = json.load(open(os.path.join(HERE, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]


def preset(family, intensity="full"):
    ps = [p for p in presets if p["family"] == family and p["intensity_class"] == intensity] or \
         [p for p in presets if p["family"] == family]
    return dict(max(ps, key=lambda p: p["weighted_share"])["xfer"])


# ---- 1. the plan: the west road to the foregate and the west gate, the town, the east road; the ways to the wild -------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"west": ((40, 220), 18), "foregate": ((80, 174), 34), "town": ((140, 110), 40), "east": ((212, 58), 14),
         "outfall": ((126, 208), 16), "den": ((42, 122), 22), "bailey": ((162, 134), 30)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ not in ("foregate", "town", "bailey"))
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_, bend_ in (("west", "foregate", 14, True, 0.2), ("foregate", "town", 14, True, 0.06),
                                 ("town", "east", 13, True, 0.06), ("town", "bailey", 12, True, 0.05),
                                 ("foregate", "outfall", 10, False, 0.25),
                                 ("foregate", "den", 10, False, 0.25)):
    pk_ = (0, 0) if {"town", "bailey"} & {a_, b_} else (1, 2) if road_ else (0, 1)    # no bays off the roads at the walls
    land.link(a_, b_, w_, bend=bend_, road=road_, pockets=pk_)
land.blends(m)
# the south-east of the grid is the far places': the town's land never grows there
land.forbidden |= {(i, j) for i in range(FAR_I - 6, 260) for j in range(-130, 130)}

# ---- 2. the town: the curtain wall planned round the square, the square's paving, the roads -------------------------
town_c = land.areas["town"]["c"]
cw = Curtain(land, town_c, (32, 30), gates=("j0", "j1"))
land.paint_square(m, "town", 10, "RoughCobble")
land.taken |= {(int(town_c[0]) + a, int(town_c[1]) + 1 + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}
land.paint_roads(m, PATH, width_squares=2.8, skip=land.reserved | land.forbidden)
for s_ in land.roads & cw.plot:                     # inside the walls the road is cobbled
    m.floor[square_tile(*s_)] = "RoughCobble"
cw.plan_gates(m)
cw.hold()
inner = {s for s in cw.plot if min(s[0] - cw.gi, cw.gi + cw.w - 1 - s[0], s[1] - cw.gj, cw.gj + cw.h - 1 - s[1]) >= 3}


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


# the old gaol tower: a square of Galava stone toward the courtyard's top corner, its door on its south-east wall
gc_ = free_block((cw.gi + 9, cw.gj + cw.h - 9), 6, inner)
assert gc_, "no room for the gaol tower"
GU0, GV0 = 2 * (gc_[0] - 6), 2 * (gc_[1] - 5) - 2
GAOL = (GU0, GU0 + 24, GV0, GV0 + 20)              # u0, u1, v0, v1: the door on the u1 (south-east) wall
gaol_sq = {(i, j) for i in range(GAOL[0] // 2, GAOL[1] // 2) for j in range(GAOL[2] // 2 + 1, GAOL[3] // 2 + 1)}
land.taken |= {(i + a, j + b) for i, j in gaol_sq for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}
land.taken_strict |= gaol_sq
land.reserved |= gaol_sq
# the cistern lift in the back lane: a clear block toward the courtyard's bottom corner, off the roads
lc_ = free_block((cw.gi + cw.w - 10, cw.gj + 9), 2, inner)
assert lc_, "no room for the cistern lift"
land.taken |= {(lc_[0] + a, lc_[1] + b) for a in range(-3, 4) for b in range(-3, 4)}

# ---- 3. buildings: the keep and the trades round the square, the foregate's houses along the road ---------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"west": 9, "den": 13, "outfall": 9}, square_area="town")
cw.release()
by_role = sm.by_role
sm.connect_and_furnish(path_material=PATH)
# the furnisher sometimes sets two of the throne room's statues shoulder to shoulder (pieces.clearance, HB-4): one goes
tr0_ = sm.room_of("keep", "throne_room")
if tr0_:
    near_ = {(x + a, y + b) for x, y in tr0_.tiles for a in (-1, 0, 1, 2) for b in (-1, 0, 1, 2)}
    sts_ = [o for o in m.d["objects"] if str(o.get("type", "")).startswith("Statue") and
            (int(o["x"] // CELL), int(o["y"] // CELL)) in near_]
    gone_ = set()
    for k_, a_ in enumerate(sts_):
        if id(a_) in gone_: continue
        for b_ in sts_[k_ + 1:]:
            if id(b_) not in gone_ and math.hypot(a_["x"] - b_["x"], a_["y"] - b_["y"]) < 50:
                gone_.add(id(b_))
    m.d["objects"][:] = [o for o in m.d["objects"] if id(o) not in gone_]

# the garrison's training ground in the bailey, the Thornes' monument in the courtyard
yards = []
tg_c = free_block(land.areas["bailey"]["c"], 4, inner)
assert tg_c, "no room for the training ground"
land.taken |= {(tg_c[0] + a, tg_c[1] + b) for a in range(-5, 6) for b in range(-5, 6)}


def inner_yard(kind, near):
    """A yard of `kind` inside the walls, as near `near` (squares) as it fits, its gate toward the square."""
    for c_ in sorted(inner, key=lambda s: math.hypot(s[0] - near[0], s[1] - near[1]))[:600:5]:
        before = set(land.taken)
        y_ = Y.plan(land, rng, kind, c_, toward=town_c)
        if y_ and {(y_.gi + a, y_.gj + b) for a in range(-1, y_.w + 1) for b in range(-1, y_.h + 1)} <= inner:
            yards.append(y_); return y_
        land.taken = before
    print(f"no room for the {kind} inside the walls")
    return None


inner_yard("orchard", (cw.gi + cw.w - 9, cw.gj + cw.h - 9))          # the keep's orchard in the right corner
inner_yard("graveyard", (cw.gi + cw.w - 14, cw.gj + 12))             # the garrison's dead, by the south wall
inner_yard("monument", (cw.gi + 12, cw.gj + 10))                     # the Thornes' monument by the west wall
# the foregate's yards: a kitchen garden field and an orchard by the houses
fg_c = land.areas["foregate"]["c"]
for kind_ in ("field", "orchard"):
    near_ = [(fg_c[0] + r * math.cos(a * math.pi / 6), fg_c[1] + r * math.sin(a * math.pi / 6)) for r in (9, 12, 15) for a in range(12)]
    y_ = Y.plan_any(land, rng, kind_, near_, toward=fg_c)
    if y_: yards.append(y_)
    else: print(f"no room for the {kind_}")

# ---- 4. the land grows round everything; the courtyard all land, the forest kept off the walls -------------------------
land.carve(margin=3.5)
cw.fill()
lane_ = sm.keep_open({"west": 5, "den": 11, "outfall": 7, "east": 4})
clumps = land.thickets(250, size=(0.9, 1.8), clear=1, avoid=frozenset((lane_ | cw.plot) & land.squares))
land.open_links()
land.squares -= cw.forb
land.squares = {s for s in land.squares if s[0] < FAR_I - 6}
land.apply(m, wall=FORESTS[FOREST]["wall"], floor="GrassNorm", unlevel=True)
gates = cw.build(m, prefix={"j0": "WestGate", "j1": "EastGate"}, lock={"j0": "Mechanism", "j1": "Mechanism"})
assert "j1" in gates and "j0" in gates, "the roads do not cross the wall where the gates go"
built = []
for y_ in yards:
    if not y_.plot <= land.squares:
        print(f"the {y_.kind} lies off the land"); continue
    Y.build(m, rng, land, y_)
    built.append(y_.kind)
training = camps.training_ground(m, rng, land, (tg_c[0] + 0.5, tg_c[1] - 0.5), town_c, r=4.5)

# the gaol tower's guard room: the stair down in its west corner, the door on the south-east wall
m.room(*GAOL, wall="GalavaTownWall", floor="GalavaBrick")
gaol_tiles = set(rect_tiles(*GAOL))
for t_ in gaol_tiles: m.indoor[t_] = "GalavaBrick"
gdoor_gap = tuple(int(c) for c in uv_to_xy(GAOL[1], (GAOL[2] + GAOL[3]) // 2))
gdoor = m.door(None, gdoor_gap, "/")
gdoor["scr"] = "GaolDoor"
gdoor.setdefault("xfer", {})["LockType"] = "Mechanism"
land.wall_cells |= set(rect_wall_cells(*GAOL))
gaol_room = Room(id="gaol", tiles=gaol_tiles, floor="GalavaBrick", walls=rect_wall_cells(*GAOL),
                 doors=[Door(gap=gdoor_gap, line="/", type=gdoor["type"], connects=("gaol", "outside"),
                             px=(gdoor["x"], gdoor["y"]))], kind="guardroom", building="the old gaol tower")
gaol_out = (gdoor["x"] + 2.4 * CELL, gdoor["y"] - 0.2 * CELL)       # before the door, outside (south-east)

# ---- the far places, drawn walled off in the south-east of the grid ----------------------------------------------------
def cave(circles, capsules=(), wall="SewerWall", floor="GreenBrick"):
    """A walled-off place of its own: the squares within the circles [(X, Y, r) in cells] and along the capsules
    [((X0, Y0), (X1, Y1), half width)], walled round as the land is. Returns the Land."""
    def inside(X, Y):
        if any(math.hypot(X - cx, Y - cy) <= r for cx, cy, r in circles): return True
        for (x0, y0), (x1, y1), w in capsules:
            dx, dy = x1 - x0, y1 - y0
            t = max(0.0, min(1.0, ((X - x0) * dx + (Y - y0) * dy) / (dx * dx + dy * dy)))
            if math.hypot(X - x0 - t * dx, Y - y0 - t * dy) <= w: return True
        return False
    sq = {(i, j) for i in range(FAR_I, 250) for j in range(-60, 130) if inside(i + j + 1, i - j + 1)}
    L = Land(rng)
    L.squares = Land._largest(Land._fix_pinches(sq))
    assert all(i >= FAR_I for i, j in L.squares)
    L.apply(m, wall=wall, floor=floor, unlevel=True)
    return L


# the Old Sewers: the outfall's inside, Nettle's nook, the junction, the cistern under the well, the lift's shaft chamber
SW_IN, SW_NOOK, SW_JUNC, SW_CIST, SW_SHAFT = (222, 150), (237, 141), (228, 166), (233, 187), (212, 177)
sewer = cave([(*SW_IN, 6), (*SW_NOOK, 5), (*SW_JUNC, 5), (*SW_CIST, 7), (*SW_SHAFT, 6)],
             [(SW_IN, SW_NOOK, 2.6), (SW_IN, SW_JUNC, 3.0), (SW_JUNC, SW_CIST, 3.0), (SW_JUNC, SW_SHAFT, 3.0)])

# the Chancellor's dungeon: the stair hall, the cells corridor and its two cells, the question room (uv rooms)
DU, DV = 380, -20
D_HALL = (DU, DU + 26, DV, DV + 20)
D_CORR = (DU + 26, DU + 52, DV, DV + 16)
D_CELL1 = (DU + 28, DU + 38, DV + 16, DV + 28)
D_CELL2 = (DU + 40, DU + 50, DV + 16, DV + 28)
D_QUEST = (DU + 52, DU + 70, DV, DV + 20)
DUNGEON = {"hall": D_HALL, "corr": D_CORR, "cell1": D_CELL1, "cell2": D_CELL2, "quest": D_QUEST}
for k_, R_ in DUNGEON.items():
    m.room(*R_, wall="DungeonStone", floor="DungeonStoneDark" if k_ != "quest" else "GreenBrick")


def inner_door(gap_uv, line, type_=None, name=None, lock=None):
    gap = tuple(int(c) for c in uv_to_xy(*gap_uv))
    o = m.door(type_, gap, line)
    if name: o["scr"] = name
    if lock: o.setdefault("xfer", {})["LockType"] = lock
    return gap, o


d_hc, o_hc = inner_door((DU + 26, DV + 10), "/", "WoodenDoor")
d_cq, o_cq = inner_door((DU + 52, DV + 8), "/", "WoodenDoor")
d_c1, o_c1 = inner_door((DU + 32, DV + 16), "\\", "JailDoor", name="TamCell", lock="Mechanism")
d_c2, o_c2 = inner_door((DU + 44, DV + 16), "\\", "JailDoor", name="EmptyCell")


def far_room(rid, R_, kind, doors):
    tiles = set(rect_tiles(*R_))
    for t_ in tiles: m.indoor[t_] = m.floor.get(t_, "DungeonStoneDark")
    return Room(id=rid, tiles=tiles, floor=m.floor.get(next(iter(tiles))), walls=rect_wall_cells(*R_),
                doors=[Door(gap=g, line=l, type=o["type"], connects=(rid, other), px=(o["x"], o["y"]))
                       for g, l, o, other in doors], kind=kind, building="the Chancellor's dungeon")


hall_room = far_room("dhall", D_HALL, "guardroom", [(d_hc, "/", o_hc, "dcorr")])
corr_room = far_room("dcorr", D_CORR, "cell", [(d_hc, "/", o_hc, "dhall"), (d_cq, "/", o_cq, "dquest"),
                                               (d_c1, "\\", o_c1, "dcell1"), (d_c2, "\\", o_c2, "dcell2")])
cell1_room = far_room("dcell1", D_CELL1, "cell", [(d_c1, "\\", o_c1, "dcorr")])
cell2_room = far_room("dcell2", D_CELL2, "cell", [(d_c2, "\\", o_c2, "dcorr")])
quest_room = far_room("dquest", D_QUEST, "torture_chamber", [(d_cq, "/", o_cq, "dcorr")])

# the stairs' ends (kit/transport STAIRS castle; Westwood's offsets, rules/out/transporters.json)
geo = tp_geometry()["stairs"]
STAIR_DOWN = px(GAOL[0] + 5, GAOL[2] + 6)          # in the gaol tower's west corner
STAIR_UP = px((D_HALL[0] + D_HALL[1]) // 2, D_HALL[3] - 2)   # against the stair hall's north-east wall


def stairs_zone(main, at):
    g = geo[main]
    pts = [at, (at[0] + g["pad"][0], at[1] + g["pad"][1]), (at[0] + g["arrive"][0], at[1] + g["arrive"][1])]
    pts += [(at[0] + dx, at[1] + dy) for _, dx, dy in g["pieces"]]
    return pts


def clear_round(pts, r, keep=()):
    """Takes out the furniture within r px of the points (the stairs and their landing stay clear)."""
    keep = {id(o) for o in keep}
    gone = [o for o in m.d["objects"] if id(o) not in keep and "x" in o and "clone" not in o and
            o.get("type") not in ("JailDoor", "WoodenDoor") and
            any(math.hypot(o["x"] - x, o["y"] - y) < r for x, y in pts)]
    ids = {id(o) for o in gone}
    m.d["objects"][:] = [o for o in m.d["objects"] if id(o) not in ids]
    return gone


rs_ = random.Random(SEED * 31)
furnish_original(m, gaol_room, kind="guardroom", rng=random.Random(rs_.random()), style="town")
furnish_original(m, hall_room, kind="guardroom", rng=random.Random(rs_.random()), style="dungeon")
furnish_original(m, corr_room, kind="cell", rng=random.Random(rs_.random()), style="dungeon")
furnish_original(m, cell1_room, kind="cell", rng=random.Random(rs_.random()), style="dungeon")
furnish_original(m, cell2_room, kind="cell", rng=random.Random(rs_.random()), style="dungeon")
furnish_original(m, quest_room, kind="torture_chamber", rng=random.Random(rs_.random()), style="dungeon")
clear_round(stairs_zone("GalavaStairsDown", STAIR_DOWN), 62)
clear_round(stairs_zone("GalavaStairsUp1", STAIR_UP), 62)
clear_round([gaol_out], 40)

# ---- 5. the town's and the foregate's life ----------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Thorn and Crown\nBeds, beer and a hot supper", "Sign"),
                     store=q.text("Trading Post\nRope, lamp oil, arrows, salt", "Sign"),
                     smithy=q.text("The Baron's Armourer", "Sign"))
for bid, b in placed:
    role = BUILDINGS[bid.role]
    for sc in role["scenes"]: vil.scene(b, sc, role=bid.role)
    if rng.random() < role["garden"]: vil.garden(b, size=(rng.randint(3, 5), rng.randint(2, 4)))
well_xy = square_px(town_c[0] + 0.5, town_c[1] - 0.5)
m.obj_px("Well", *well_xy)


def lamp(si, sj):
    x, y = square_px(si, sj)
    m.obj_px("StreetLampOrnate3", x, y); m.obj_px("StreetLampOrnate3Shadow", x - 15, y + 21)


vil.square_piece((town_c[0] + 0.5, town_c[1] - 0.5), 5, pole=lamp, per_side=1)
land.ground_variety(m, clear=3)

# ---- 6. the story's places ------------------------------------------------------------------------------------------
C = {k: land.areas[k]["c"] for k in AREAS}
west_c, fore_c, east_c, out_c, den_c = C["west"], C["foregate"], C["east"], C["outfall"], C["den"]
DOORS_SQ = [px_square(*d.px) for _, b in placed for d in b.entrances]


def off_road(c, clear=4.5, reach=12, doors=6):
    """The square nearest `c` with no road within `clear` squares, on open land, `doors` squares from every door."""
    near_road = bfs_distance(list(land.roads), land.squares, int(clear) + 1)
    cands = [s for s in land.squares if near_road.get(s, 99) >= clear and s not in land.taken_strict and
             s not in land.taken and s not in land.water and math.hypot(s[0] - c[0], s[1] - c[1]) <= reach and
             all(math.hypot(s[0] - d[0], s[1] - d[1]) >= doors for d in DOORS_SQ)]
    s = min(cands, key=lambda s: math.hypot(s[0] - c[0], s[1] - c[1])) if cands else (int(c[0]), int(c[1]))
    return (s[0] + 0.5, s[1] - 0.5)


def torch_pole(si, sj):
    s = (int(si), int(sj) + 1)
    if s not in land.squares or s in land.water or s in land.taken_strict: return False
    x, y = square_px(si, sj)
    cx, cy = int(x // 23), int(y // 23)
    if any((cx + a, cy + b) in m.wallmap or (cx + a, cy + b) in m.door_gaps for a in (-1, 0, 1) for b in (-1, 0, 1)):
        return False
    m.obj_px("TorchPole", x, y)
    return True


# the old outfall: the sewer's great pipe running out of the ravine's back wall, its mouth turned to the clearing, a
# torch either side; the passage's spot just before the mouth
edge_ = land.edge_distance()
sq_cont = lambda x, y: (((x + y) / CELL - 1) / 2, ((x - y) / CELL - 1) / 2)    # world px -> square coordinates
oc_X, oc_Y = out_c[0] + out_c[1], out_c[0] - out_c[1]
rim_ = [s_ for s_ in land.squares if edge_.get(s_, 0) == 1 and
        math.hypot(s_[0] - out_c[0], s_[1] - out_c[1]) <= land.areas["outfall"]["r"] + 3]
upper_ = [s_ for s_ in rim_ if (s_[0] - s_[1]) - oc_Y < -3]                   # the clearing's back (upper) wall
mouth_sq = min(upper_ or rim_, key=lambda s_: abs((s_[0] + s_[1]) - oc_X) + 0.3 * abs((s_[0] - s_[1]) - oc_Y))
pipe_xy = square_px(mouth_sq[0] + 0.5, mouth_sq[1] - 0.5)
cx_, cy_ = square_px(*out_c)
ux_, uy_ = cx_ - pipe_xy[0], cy_ - pipe_xy[1]
ul_ = math.hypot(ux_, uy_) or 1.0
ux_, uy_ = ux_ / ul_, uy_ / ul_                                          # from the pipe toward the clearing
m.obj_px("SewerPipe02" if ux_ < 0 else "SewerPipe03", *pipe_xy)         # its open mouth faces the clearing
mouth_xy = (round(pipe_xy[0] + 46 * ux_, 1), round(pipe_xy[1] + 46 * uy_, 1))
for sgn_ in (-1, 1):                                                      # a torch either side of the mouth
    tx_, ty_ = pipe_xy[0] + 40 * ux_ - 52 * sgn_ * uy_, pipe_xy[1] + 40 * uy_ + 52 * sgn_ * ux_
    if not torch_pole(*sq_cont(tx_, ty_)):
        torch_pole(*sq_cont(tx_ + 12 * ux_, ty_ + 12 * uy_))
osc = camps.Scene(m, rng, land, sq_cont(*mouth_xy))
for t_, r_, a_ in (("CaveRocksLarge", 2.6, math.atan2(-uy_, ux_) + 2.0), ("CaveRocksMedium", 2.8, math.atan2(-uy_, ux_) - 2.0),
                   ("Skull", 1.9, 3.3)):
    osc.put(t_, *osc.at(r_, a_))
outfall_in = square_px(*off_road((mouth_sq[0] + (out_c[0] - mouth_sq[0]) * 0.35,
                                  mouth_sq[1] + (out_c[1] - mouth_sq[1]) * 0.35), clear=0, reach=4, doors=0))
# the Urchins' den in the west wood: their beds, table and pickings round a fire, Dobbin's ruby in the hoard
den = camps.urchin_camp(m, rng, land, camps.camp_site(m, land, den_c, reach=8, room=6), fore_c,
                        loot=[RUBY, ("Gold", {"Amount": 35}), "RedPotion"], sleepers=4)
# caches in the pines, off the ways
caches = []
for near_, loot_, stump_ in ((west_c, [("Gold", {"Amount": 45}), "CurePoisonPotion", "RedPotion"], True),
                             (out_c, [("Gold", {"Amount": 40}), "BluePotion", "LeatherHelm"], False)):
    s_ = sm.hidden_spot(near_, r=(6, 14))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
# signposts
camps.signpost(m, land, (west_c[0] + 2.5, west_c[1] - 1.5),
               q.text("THORNKEEP\nSeat of Baron Aldric Thorne.\nThe east road runs on to the Marches.", "Sign"))
wg_ = sm.road_near(px_square(*cw.gate_px("j0", 5.0)))
camps.signpost(m, land, (wg_[0] + 2.0, wg_[1] - 1.5),
               q.text("BY ORDER OF THE CHANCELLOR\nNo strangers within the walls.", "Sign"))
eg_ = sm.road_near(px_square(*cw.gate_px("j1", -4.0)))
camps.signpost(m, land, (eg_[0] - 1.5, eg_[1] - 2.0), q.text("THE EAST ROAD IS CLOSED\nBy the Baron's word.", "Sign"))
camps.signpost(m, land, (mouth_sq[0] + 0.5 + 2.6, mouth_sq[1] - 0.5 + 0.8), q.text("OLD OUTFALL\nKeep out.", "Sign"))

# the Old Sewers' places: the outfall's inside, Nettle's nook and his stash, the cistern, the lift's shaft chamber
in_xy, nook_xy, junc_xy, cist_xy, shaft_xy = (P(*p_) for p_ in (SW_IN, SW_NOOK, SW_JUNC, SW_CIST, SW_SHAFT))
for p_, fam_ in ((in_xy, "orange"), (nook_xy, "orange"), (cist_xy, "green"), (shaft_xy, "orange")):
    m.obj_px("ColorLight", p_[0], p_[1] - 6, xfer=preset(fam_, "dim"))
isc = camps.Scene(m, rng, sewer, sq_of(*SW_IN))
for t_, r_, a_ in (("SewerPipe04", 4.2, 0.4), ("WaterBarrel", 4.0, 2.4), ("Barrel2", 4.4, 3.0), ("AmbDripCave1", 2.0, 1.0)):
    isc.put(t_, *isc.at(r_, a_))
nsc = camps.Scene(m, rng, sewer, sq_of(*SW_NOOK))
nettle_stash = nsc.put("Chest2", *nsc.at(2.4, 0.9), items=[("Gold", {"Amount": 60}), "BluePotion", "Quiver"])
for t_, r_, a_ in (("Barrel", 2.6, 2.0), ("Barrel2", 2.9, 2.5), ("Crate1", 2.8, 3.4), ("SackChestMedium1", 2.5, 4.4)):
    nsc.put(t_, *nsc.at(r_, a_))
csc = camps.Scene(m, rng, sewer, sq_of(*SW_CIST))
for t_, r_, a_ in (("SewerPipe06", 5.2, 0.8), ("SewerPipe05", 5.2, 3.6), ("AmbDripCave2", 1.0, 0.0),
                   ("Skull", 3.0, 2.0), ("ArmBone", 3.4, 4.8), ("LegBone", 2.6, 5.6)):
    csc.put(t_, *csc.at(r_, a_))
ssc = camps.Scene(m, rng, sewer, sq_of(*SW_SHAFT))
for t_, r_, a_ in (("SewerPipe01", 4.6, 2.0), ("BarrelWithTools1", 4.2, 3.4), ("CaveRocksMedium", 4.4, 5.2)):
    ssc.put(t_, *ssc.at(r_, a_))
# the dungeon's lights, the question room's chest
for R_ in (D_HALL, D_CORR, D_QUEST):
    cx_, cy_ = px((R_[0] + R_[1]) / 2, (R_[2] + R_[3]) / 2)
    m.obj_px("ColorLight", cx_, cy_ - 6, xfer=preset("orange", "dim"))

# ---- 7. planting, the start and the exit ----------------------------------------------------------------------------
keep = set(cw.plot)
for bid, b in placed:
    for d in b.entrances:
        di, dj = px_square(*d.px)
        keep |= {(di + a, dj + b2) for a in range(-2, 3) for b2 in range(-2, 3)}
keep |= {(i + a, j + b) for i, j in gaol_sq for a in range(-2, 3) for b in range(-2, 3)}
keep |= {(mouth_sq[0] + a, mouth_sq[1] + b) for a in range(-3, 4) for b in range(-3, 4)}
vil.ground_bits(1.4)
planter = Planter(m, rng, land, FOREST, keep_clear=keep | lane_)
n_trees, n_small = planter.plant_all(groves=4, profile=TOWN_PLANTING)
piles = planter.rock_piles(max(4, len(land.squares) // 900))
vignettes = planter.forest_floor(max(6, len(land.squares) // 700))
start_xy = square_px(west_c[0] + 0.5, west_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
exits = exit_next(sm, "east", ACT, prefix="EastExit")

# ---- the transporters (skills/nox-transporters): each to its far place, each with its purpose ------------------------
tp = Transporters(m)
lift_xy = square_px(lc_[0] + 0.5, lc_[1] - 0.5)
outfall = tp.add("passage", mouth_xy, in_xy, "Outfall",
                 serves=[(nettle_stash["x"], nettle_stash["y"])] if nettle_stash else [])
lift = tp.add("lift", lift_xy, shaft_xy, "CisternLift", style="dungeon", serves=[cist_xy, nook_xy])
stairs = tp.add("stairs", STAIR_DOWN, STAIR_UP, "GaolStair", style="castle")
for p_ in (mouth_xy, outfall_in, lift_xy):           # the town's dressing and folk keep off every end and landing
    s_ = px_square(*p_)
    land.taken |= {(s_[0] + a, s_[1] + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}
m.obj_px("ColorLight", lift_xy[0], lift_xy[1] - 6, xfer=preset("orange"))

# ---- 8. the people --------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
person, room_of, free_px = sm.person, sm.room_of, sm.free_px
vx, vy = square_px(*town_c)
# Dobbin the pedlar by the road before the west gate, looking down it toward the start
wg_px = cw.gate_px("j0", 6.5)
dsc_ = camps.Scene(m, rng, land, px_square(*wg_px))
dob_ = next((square_px(*p_) for p_ in (dsc_.at(2.2, a_) for a_ in (0.4, 2.0, 3.6, 5.2)) if dsc_.ok(*p_)), wg_px)
person("Con03A", "Millard", dob_[0], dob_[1], "Dobbin", face=start_xy)
# Captain Osmund before the west gate, outside
og_ = cw.gate_px("j0", 2.6)
person("Con02a", "Contest_Guard", og_[0] + 26, og_[1] - 10, "Osmund", face=start_xy)
# the east gate's guard, inside
eg_px = cw.gate_px("j1", -2.4)
person("Con02a", "IxGuard2", eg_px[0] - 24, eg_px[1] + 18, "EastGuard", face=(vx, vy))
# the Baron in his throne room; Severin in the study, his hidden self on his spot; his hired swords in the stores
tr = room_of("keep", "throne_room") or room_of("keep", "great_hall")
bx_, by_ = sm.stand_px(tr) if tr else (vx, vy)
cast_person(sm, "Baron", bx_, by_)
st = room_of("keep", "study") or tr
sx_, sy_ = sm.stand_px(st) if st else (vx + 40, vy)
cast_person(sm, "Severin", sx_, sy_)
pop.creature("Necromancer", sx_, sy_, action="guard", scr="SeverinFoe", aggr=0.83, spread=False)
sto = room_of("keep", "storeroom") or st
blades = []
for k in range(2):
    kx_, ky_ = free_px(sto, clear=26) if sto else (sx_ + 30 * k, sy_ + 30)
    pop.creature("Swordsman", kx_, ky_, action="guard", scr=f"KeepBlade{k + 1}", aggr=0.83)
    blades.append(f"KeepBlade{k + 1}")
# Gaoler Moss by the gaol tower's door
gm_ = gaol_out
person("Con02a", "Heckler", gm_[0] + 14, gm_[1] + 30, "Moss", face=(vx, vy))
# Brenna the alewife by the well
bw_ = square_px(town_c[0] + 0.5 + 2.6, town_c[1] - 0.5 + 1.0)
person("Con02a", "Julie", bw_[0], bw_[1], "Brenna", face=well_xy)
# Nettle the fence in his nook in the sewers
nx_, ny_ = nsc.px(1.0, 3.0)
person("Con03A", "Rastur", nx_, ny_, "Nettle", face=in_xy)
# Tam in his cell (cast: the same body and voice in every act); at the inn once he is free
c1x, c1y = px((D_CELL1[0] + D_CELL1[1]) / 2, (D_CELL1[2] + D_CELL1[3]) / 2 + 1)
cast_person(sm, "Tam", c1x, c1y, face=o_c1 and (o_c1["x"], o_c1["y"]))
inn_room = room_of("inn", "tavern")
tix, tiy = sm.stand_px(inn_room, k=1) if inn_room else (vx - 40, vy + 40)
sm.person(CAST["Tam"]["donor"][0], CAST["Tam"]["donor"][1], tix, tiy, "TamInn")
# shopkeepers
WARES = {"store": [(4, "RedPotion"), (3, "BluePotion"), (2, "CurePoisonPotion"), (3, "RedApple"), (2, "Bread"),
                   (2, "Quiver"), (1, "Bow"), (1, "LeatherBoots"), (1, "LeatherHelm"), (1, "LeatherArmor")],
         "inn": [(6, "RedApple"), (5, "Meat"), (4, "Cider"), (3, "Bread"), (2, "RedPotion")],
         "smithy": [(2, "Sword"), (1, "Longsword"), (1, "GreatSword"), (1, "BattleAxe"), (1, "SteelShield"),
                    (1, "ChainCoif"), (1, "ChainTunic"), (1, "ChainLeggings"), (1, "SteelHelm"), (1, "PlateBoots")]}
GREET = {"store": q.text("Trading post. Prices went up when the gates shut. Didn't they come down? No, they did not.",
                         "Shop"),
         "inn": q.text("Welcome to the Thorn and Crown! Hot supper, cold beer! Don't drink the well water.", "Shop"),
         "smithy": q.text("The Baron's own armourer. Steel for the garrison, and for you, if you're paying.", "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"smithy": "ShopkeeperWarriorsRealm"})
# townsfolk, each with something to tell
for c_, r_ in ((den_c, 14), (out_c, 8), (px_square(*lift_xy), 4), (gc_, 7)):
    sm.keep_folk_away(c_, r_)
FOLK = [("Con02a", "Tanya"), ("Con02a", "Clyde"), ("Con03A", "Osborn"), ("Con02a", "Lydia"), ("Con08a", "Gretchen"),
        ("Con02a", "Jacob"), ("Con03A", "Millard")]
RUMOURS = [
    "The Chancellor runs this town now. The Baron just signs what he's given.",
    "Since the well went bad we drink beer at breakfast. My head hurts all day!",
    "The Chancellor's men go in and out of the old gaol at night. Nobody's been locked up there in years.",
    "Urchins in the west wood again. They took my washing right off the line!",
    "Not now. I've a cart to load.",
    "Ogres have the Marches road. Nobody's come in from the east all summer.",
    "Mind the Baron's armourer. He'll sell you a sword and then tell you how to hold it.",
]
ring = sm.townsfolk(FOLK, town_c, q=q, rumours=RUMOURS,
                    after=("severin_dead", "The Chancellor! A cultist, at the Baron's own elbow! The east gate's open, "
                                           "they say."),
                    pics=("MaidenPic3", "MalePic7", "Townsman2Pic", "MaidenPic", "MaidenPic2", "MalePic8", "Townsman3Pic"),
                    radius=7.0)
# the watch walking the courtyard
inset = 5.0
corners = [square_px(cw.gi + inset, cw.gj - 1 + inset), square_px(cw.gi + inset, cw.gj + cw.h - 1 - inset),
           square_px(cw.gi + cw.w - inset, cw.gj + cw.h - 1 - inset), square_px(cw.gi + cw.w - inset, cw.gj - 1 + inset)]
for k_, donor_ in enumerate(("Contest_Guard", "IxGuard1")):
    wx2, wy2 = corners[k_ * 2]
    person("Con02a", donor_, wx2, wy2, f"Watch{k_ + 1}", action=0)
    sm.beat(f"Watch{k_ + 1}", town_c, radius=7.0, stops=6)

# ---- 9. the fights ----------------------------------------------------------------------------------------------------
# the Urchins at their posts in the den, their shaman by the hoard
den_posts = camp_posts(m, den, square_px(*fore_c), sit=2, tents=1, watch=1)
urchins = ["DenShaman"]
pop.creature("UrchinShaman", *den_posts["leader"], action="guard", scr="DenShaman", aggr=0.83, face=square_px(*fore_c))
for k_, (x_, y_) in enumerate(den_posts["sit"] + den_posts["tent"] + den_posts["watch"]):
    n_ = f"DenUrchin{k_ + 1}"
    pop.creature("Urchin", x_, y_, action="guard", scr=n_, aggr=0.83, face=square_px(*fore_c))
    urchins.append(n_)
# the sewers: rats and bats in the ways, the leeches in the cistern
sewer_foes = []
for k_, (X_, Y_, t_) in enumerate(((226, 145, "Rat"), (219, 157, "Rat"), (229, 160, "Bat"), (217, 173, "Rat"),
                                    (224, 171, "Bat"))):
    n_ = f"SewerRat{k_ + 1}"
    pop.creature(t_, *P(X_, Y_), action="guard", scr=n_, aggr=0.83, face=in_xy)
    sewer_foes.append(n_)
leeches = []
for k_, a_ in enumerate((0.4, 1.9, 3.4, 4.9)):
    n_ = f"CisternLeech{k_ + 1}"
    pop.creature("GiantLeech", *csc.px(3.2 + 0.6 * (k_ % 2), a_), action="guard", scr=n_, aggr=0.83, face=cist_xy)
    leeches.append(n_)
# the dungeon: the Chancellor's men at the stair hall, the corridor and the question room
dungeon_men = []
for k_, (R_, t_) in enumerate(((D_HALL, "Swordsman"), (D_CORR, "Swordsman"), (D_CORR, "Archer"), (D_QUEST, "Swordsman"))):
    room_ = {D_HALL: hall_room, D_CORR: corr_room, D_QUEST: quest_room}[R_]
    x_, y_ = free_px(room_, clear=30)
    n_ = f"CellGuard{k_ + 1}"
    pop.creature(t_, x_, y_, action="guard", scr=n_, aggr=0.83, face=STAIR_UP)
    dungeon_men.append(n_)
q_chest = None
qx_, qy_ = free_px(quest_room, prefer=px(D_QUEST[1] - 4, D_QUEST[3] - 4), clear=28)
q_chest = m.obj_px("Chest3", qx_, qy_, items=[("Gold", {"Amount": 70}), "RedPotion", "BluePotion", "ChainCoif"])
# the pines' own creatures by the forest's edge
sm.wild({"Wolf": 2, "Bat": 3, "SmallSpider": 2, "Spider": 1}, away_from=town_c, per100=0.45, gap=7, min_away=40,
        avoid=(west_c, fore_c, den_c, out_c, east_c))

story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]
            if px_square(o["x"], o["y"])[0] < FAR_I] + [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)

# ---- the mods and the story's helpers: Severin is a Bone Caller (M3) woken when he drops the mask -------------------
mods = Mods(m, pop)
hc = HcStory(m)
hc.late_boss("severin_turned", "bonecaller", "SeverinFoe", "Chancellor Severin", 360)

# ---- 10. the story ----------------------------------------------------------------------------------------------------
SEAL, KNIFE, SATCHEL, FREED, WENNA = (token(k) for k in ("WATCH_SEAL", "RUSK_KNIFE", "TAM_SATCHEL", "TAM_FREED", "WENNA_ASK"))
MAIN = "Win Baron Aldric Thorne's help against the Choir."
q.start([A.lock("WestGate1"), A.lock("WestGate2"), A.lock("EastGate1"), A.lock("EastGate2"), A.lock("TamCell"),
         A.lock("GaolDoor"), A.disable("SeverinFoe"), A.disable("TamInn")] +
        [A.disable(n) for n in exits] + [A.disable(n) for n in blades] +
        [q.journal("Find a way into Thornkeep, the Baron's walled town.", HINT)])
q.when_true(q.when(has=SATCHEL), [q.note("NOTE: The Choir's order in Tam's satchel sent the ringer's boy to Thornkeep.")])

# the west gate: Captain Osmund honours the Brackwater watch's warrant
q.talker("Osmund", [
    q.say("I knew there was something off about that Chancellor. Pass freely, friend of Thornkeep.",
          when=q.when(flag=q.dead("SeverinFoe")), who="Guard"),
    q.say("Go on in! And no trouble inside the walls.", when=q.when(flag="west_open"), who="Guard"),
    q.say("What's this, a warrant? ...The Brackwater watch, under Captain Rook's own seal! Her word is good in "
          "Thornkeep, Chancellor or no Chancellor. Open the gate!",
          when=q.when(has=SEAL, not_="west_open"),
          do=[A.flag("west_open"), A.unlock("WestGate1"), A.unlock("WestGate2"),
              A.print("Captain Osmund waves to the gatehouse. The west gate swings open."),
              q.note("NOTE: Captain Osmund opened the west gate for the Brackwater warrant.")], who="Guard"),
    q.say("No strangers inside the walls! The Chancellor's own order. Move along.", when=q.when(not_="osmund_no"),
          do=[A.flag("osmund_no"), q.note("NOTE: The west gate is shut to strangers by the Chancellor's order.")],
          who="Guard"),
    q.say("Still here? I said move along!", who="Guard")])

# Dobbin: the hook, and the Pedlar's Ruby
RUBY_OBJ = "Recover Dobbin's ruby from the Urchins in the west wood."
q.talker("Dobbin", q.errand(
    "Dobbin", "ruby",
    offer="Shut! Shut for a week, and me with a pack full of needles nobody can buy! The Chancellor says no strangers, "
          "so here I sit. The river-rats still get in, mind, by the old outfall in the ravine south of the walls.\n\n"
          "And while I slept, the Urchins from the west wood came and took my ruby. My whole stake, that stone was!\n\n"
          "You look like you could frighten a few Urchins. Bring it back and you can have the pick of my pack. Well?",
    reminder="Those Urchins! I can hear them laughing in the trees at night.",
    thanks="My ruby! Warm from some little thief's pocket, but mine!\n\nTake your pick, as I promised. No, take both. "
           "And here's coin besides.",
    after="If they ever open that gate, I'll sell you needles at cost.",
    objective=RUBY_OBJ, done=q.when(has=RUBY),
    reward=[A.give("LeatherArmoredBoots"), A.give("Quiver"), A.gold(50)],
    refusal="Then go and knock on the gate. See how far that gets you."))
q.near(*den["fire"], 260, [A.print("Little cooking fires, stolen washing, a stink of Urchin: their den.")])

# the Baron: the main quest
q.talker("Baron", [
    q.say("The gate is open and the road is yours. Thornkeep owes you more than coin.",
          when=q.when(flag="baron_paid"), who="Baron"),
    q.say("Severin. Eleven years he sat at my right hand and read me my letters. I read his, this morning.\n\nThe Choir "
          "keeps its seat in a tower beyond the Ogre Marches: the Hollow Spire. And it gathers its stolen stones at the "
          "Emberforge, the founders' forge in the fire mountains, to wake the thing under the world. Gruthak the Ogre "
          "Lord holds the Marches road for them, paid with one of the stones.\n\nTake this, and my thanks. The east "
          "gate is open. Bring the Choir down.",
          when=q.when(flag=q.dead("SeverinFoe"), not_="baron_paid"),
          do=[A.flag("baron_paid"), A.gold(200), A.give("SteelHelm"), A.give("RedPotion", 2),
              A.unlock("EastGate1"), A.unlock("EastGate2"), A.unlock("WestGate1"), A.unlock("WestGate2")] +
             [A.enable(n) for n in exits] +
             [q.done(MAIN),
              q.journal("Take the east road through the Ogre Marches toward the Hollow Spire.", QUEST),
              q.note("NOTE: Severin's papers name the Hollow Spire, the Choir's seat, and the Emberforge, where it "
                     "gathers the stones.")], who="Baron"),
    q.say("My Chancellor a cultist? Then he has shown it in my own house. Cut him down!",
          when=q.when(flag="severin_turned"), who="Baron"),
    q.say("The boy says Severin held him? In my dungeon, under my own walls? ...Put it to him, then. To his face.",
          when=q.when(flag="tam_told"), who="Baron"),
    q.say("Proof, I said. Not stories. Ask my own watch what goes on in Thornkeep, since I seem to be the last to "
          "hear of it.", when=q.when(flag="baron_met"), who="Baron"),
    q.say("A cult? Stealing the clappers out of bells? My Chancellor tells me the shrines were robbed by common "
          "bandits, and Severin is rarely wrong.\n\nI will not march the garrison on a traveller's tale. Bring me "
          "proof that the Choir has a hand in Thornkeep, and you will have my men.",
          do=[A.flag("baron_met"), A.unlock("WestGate1"), A.unlock("WestGate2"), A.stage("main", 1),
              q.journal(MAIN)], who="Baron")], voice=voice("Baron"))

# Severin: smooth, then unmasked
q.talker("Severin", [
    q.say("The boy talks too much. Do you mean to accuse me, traveller? Here, before my lord's own door?",
          when=q.when(flag="tam_told", not_="severin_turned"), ask=True,
          do=[A.flag("severin_turned"), A.turn("Severin", "SeverinFoe")] + [A.hunt(n) for n in blades] +
             [A.print("Severin's smile goes thin. 'Then sing with me.' The dead stir in the stones of the keep."),
              q.journal("Kill Chancellor Severin, the Choir's man at court.", QUEST)],
          else_=[q.tell("Severin", "Wise. Very wise. Go home, traveller.")], who="Severin"),
    q.say("Bandits rob shrines, traveller. Bandits, not choirs. You would do better to go home.",
          when=q.when(flag="baron_met"), who="Severin"),
    q.say("I see few strangers in Thornkeep. His lordship is in the throne room.", who="Severin")],
    voice=voice("Severin"))
q.on_death("SeverinFoe", [A.flag("severin_dead"), A.print("Severin falls, and the bones he raised fall with him."),
                          q.note("NOTE: Chancellor Severin is dead. The Baron will want to see his papers.")])

# the gaoler: the satchel or the rumour opens the gaol tower
q.talker("Moss", [
    q.say("The boy's out? Good. I never liked what went on down there.", when=q.when(flag="tam_freed"), who="Guard"),
    q.say("Down the stair, then. The Chancellor's men won't be glad to see you.", when=q.when(flag="gaol_open"),
          who="Guard"),
    q.say("That satchel! The boy they brought in had one just like it. He's below, in the old cells. Chancellor's "
          "orders, nobody goes down.\n\n...Go on, then. I never saw you.",
          when=q.when(has=SATCHEL, not_="gaol_open"),
          do=[A.flag("gaol_open"), A.unlock("GaolDoor"), A.stage("main", 2),
              A.print("Gaoler Moss turns his key in the gaol tower's door."),
              q.journal("Free the ringer's boy from the dungeon under the old gaol.", QUEST)], who="Guard"),
    q.say("So the watch talks. Aye, there's a boy below. The Chancellor's men keep the key, but I keep a spare.",
          when=q.when(flag="rumour_heard", not_="gaol_open"),
          do=[A.flag("gaol_open"), A.unlock("GaolDoor"), A.stage("main", 2),
              A.print("Gaoler Moss turns his key in the gaol tower's door."),
              q.journal("Free the ringer's boy from the dungeon under the old gaol.", QUEST)], who="Guard"),
    q.say("Nobody goes below. Not without the Chancellor's say-so.", when=q.when(flag="baron_met"), who="Guard"),
    q.say("Wanna try the cells? No? Then move on.", who="Guard")])

# the watch: one of them lets slip the rumour once the Baron has turned the player away
q.talker("Watch1", [
    q.say("The Chancellor's gone, they say. I won't miss him.", when=q.when(flag="severin_dead"), who="Watch"),
    q.say("Between us? The Chancellor's men took a boy down the old gaol's stair one night. Nobody's seen him since. "
          "Ask Moss, by the tower.",
          when=q.when(flag="baron_met", not_="rumour_heard"),
          do=[A.flag("rumour_heard"),
              q.note("NOTE: A watchman says the Chancellor's men took a boy down the old gaol's stair.")], who="Watch"),
    q.say("Keep it civil inside the walls.", who="Watch")])
q.talker("Watch2", [
    q.say("East gate's open! Never thought I'd see it.", when=q.when(flag="baron_paid"), who="Watch"),
    q.say("You didn't hear it from me. There's a prisoner under the old gaol that nobody wrote in the book. Moss keeps "
          "the door.", when=q.when(flag="baron_met", not_="rumour_heard"),
          do=[A.flag("rumour_heard"),
              q.note("NOTE: A watchman says there is a prisoner under the old gaol. Gaoler Moss keeps its door.")],
          who="Watch"),
    q.say("Move along. The square's no place for loitering.", who="Watch")])
q.talker("EastGuard", [
    q.say("The Baron says you may pass. The road runs east to the Ogre Marches. Watch for Ogres!",
          when=q.when(flag="baron_paid"), who="Guard"),
    q.say("The east road's shut. Nobody rides east without the Baron's leave!", who="Guard")])

# the dungeon: the cell opens when the Chancellor's men are dead; Tam
q.on_all_dead(dungeon_men, [A.unlock("TamCell"), A.flag("cells_clear"),
                            A.print("Keys jangle on the last guard's belt. The cell door swings loose.")])
q.near(*STAIR_UP, 220, [A.print("Damp stone, a cold draught, someone weeping behind a door.")])
q.talker("Tam", [
    q.say("You came! And that's Wenna's green stone you've got! She sent you, didn't she?\n\nIt was the Chancellor "
          "who kept me. Severin. Every night he brought me letters from the High Caller and made me read the bells' old "
          "script. Here, my bell-token, for your trouble. Oh, and my satchel! I'll go up and wait at the inn.",
          when=q.when(has=WENNA, flag="cells_clear", not_="tam_freed"),
          do=[A.flag("tam_freed"), A.flag("tam_told"), A.take(SATCHEL), A.give(FREED), A.stage("main", 3),
              A.disable("Tam"), A.enable("TamInn"),
              A.print("Tam runs for the stair."),
              q.journal("Put Tam's word to Chancellor Severin in the keep.", QUEST)], who="Tam"),
    q.say("Who are you? Not one of his! ...It was the Chancellor who kept me. Severin. Every night he brought me "
          "letters from the High Caller and made me read the bells' old script.\n\nTake my bell-token, for your "
          "trouble. If you ever go to Brackwater, tell my sister Wenna I'm alive. Is that my satchel? I'll go up and "
          "wait at the inn.",
          when=q.when(flag="cells_clear", not_="tam_freed"),
          do=[A.flag("tam_freed"), A.flag("tam_told"), A.take(SATCHEL), A.give(FREED), A.stage("main", 3),
              A.disable("Tam"), A.enable("TamInn"),
              A.print("Tam runs for the stair."),
              q.journal("Put Tam's word to Chancellor Severin in the keep.", QUEST)], who="Tam"),
    q.say("Help! Get me out of here! They've got the key!", who="Tam")], voice=voice("Tam"))
q.talker("TamInn", [
    q.say("Severin's dead? Then I can sleep. Wenna will never believe it.", when=q.when(flag="severin_dead"),
          who="Tam"),
    q.say("Go on, tell them! Tell the Baron what his Chancellor is!", who="Tam")], title="Tam", voice=voice("Tam"))

# Foul Water: the leeches in the cistern
q.talker("Brenna", q.errand(
    "Brenna", "water",
    offer="Faugh! Smell that bucket! The well's gone foul, and I can't brew good ale from bad water!\n\nSomething's "
          "nesting in the old cistern under the square. Leeches, the well-diggers say, big as a dog. The old lift in "
          "the back lane goes down to the sewers.\n\nKill them for me and I'll pay. Will you?",
    reminder="Every bucket's worse than the last! Hurry, please!",
    thanks="The water's running clear! I can taste it already!\n\nHere's your pay, and a few bottles from the "
           "apothecary's shelf.",
    after="First barrel of the new brew is yours!",
    objective="Kill the Giant Leeches in the cistern under the well.",
    done=q.when(flag=q.dead(*leeches)), reward=[A.gold(80), A.give("RedPotion", 3), A.give("CurePoisonPotion", 2)],
    refusal="Then you can drink beer like the rest of us."))
q.near(*cist_xy, 240, [A.print("The old cistern. Something heavy slides through the muck.")])

# Nettle the fence, in the sewers: Rusk's lucky charm
q.talker("Nettle", [
    q.say("Good doing business. Mind the leeches on your way.", when=q.when(flag="nettle_paid"), who="Nettle"),
    q.say("Rusk's lucky charm! He never let a soul touch that. So the old dog's alive! Any friend of Rusk's...\n\nHere, "
          "something for the road. And a word for free: the Chancellor's men use the old gaol, and not for thieves.",
          when=q.when(has=KNIFE, not_="nettle_paid"),
          do=[A.flag("nettle_paid"), A.give("RedPotion", 2), A.give("BluePotion"), A.gold(40),
              q.note("NOTE: Nettle the fence says the Chancellor's men use the old gaol.")], who="Nettle"),
    q.say("Psst... you're no river-rat. Lost? The lift at the far end goes up into the town. Don't say who showed you.",
          who="Nettle")])
q.near(*in_xy, 200, [A.print("A low tunnel, ankle-deep in muck. Somewhere ahead, water drips.")])

for who_, pic_ in (("Dobbin", "Townsman3Pic"), ("Osmund", "Warrior2Pic"), ("EastGuard", "IxGuard2Pic"),
                   ("Baron", "TheogrinPic"), ("Severin", "MorganPic"), ("Moss", "MalePic5"), ("Brenna", "MaidenPic4"),
                   ("Nettle", "MalePic9"), ("Tam", "WoundedApprenticePic"), ("TamInn", "WoundedApprenticePic"),
                   ("Watch1", "Warrior3Pic"), ("Watch2", "Warrior2Pic")):
    q.portrait(who_, pic_)

m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())
m.scripts.update(mods.files(NAME))          # the mods library (ModBoss) for Severin's late waking
m.scripts.update(hc.files(NAME))

# ---- 11. the exteriors' dressing ---------------------------------------------------------------------------------------
dressed = Exterior(m, land, "green", martial=True, placed=placed).dress(reach=3.5)

# no wild flowers in the trodden courtyard or at the foot of its wall (a run of them had grown along it: pieces.run)
near_wall_ = {(i, j) for i in range(cw.gi - 3, cw.gi + cw.w + 3) for j in range(cw.gj - 3, cw.gj + cw.h + 3)}
m.d["objects"][:] = [o for o in m.d["objects"] if not (str(o.get("type", "")).startswith("Flowers") and
                                                       px_square(o["x"], o["y"]) in near_wall_)]

class _Far:                                          # the hand-drawn rooms, for the rooms sidecar
    def __init__(self, rooms): self.rooms = rooms


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed + [(BuildingIdentity("gaol", "town", "the old gaol tower", "Gaoler Moss"), _Far([gaol_room])),
                            (BuildingIdentity("gaol", "town", "the Chancellor's dungeon", "the Chancellor's men"),
                             _Far([hall_room, corr_room, cell1_room, cell2_room, quest_room]))],
                  os.path.join(OUT, f"{NAME}.rooms.json"), yards=[y_ for y_ in yards if y_.kind in built])
    from kit.campaign import apply_deliveries
    apply_deliveries(q)            # voice-gate deliveries (kit/campaign.py DELIVERIES)
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS", "VOICE"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| trees {n_trees} | shops {n_shops} | caches {len(caches)} | opened {len(opened)} | lines {len(q.strings)} "
          f"| yards {', '.join(built) or 'none'} | dressing {sum(dressed.values())} groups | sewer {len(sewer.squares)} squares")
