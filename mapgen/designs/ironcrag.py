"""Ironcrag: a mining town under a crag at the foot of the high pass, and the story of the Silent Shift (a map of its
own, loadable directly; the pass road north leads to the Rime Pass, mapgen/designs/rimepass.py). The first story map
built round transporters (TR-1, skills/nox-transporters): four of the five places the story needs cannot be walked to.

The town: log and stone houses round the pithead yard, under the rock face of the old mine (a timbered tunnel that a
rockfall closed years ago); beside the tunnel's mouth the Deep Lift, the company's new shaft down to the deep level.
The Warden's stone tower stands on the rise north-east of the yard; the pass gate north of the town; Wren's hut and
her ring of standing stones in the east pines.

The transporters, each to a place of its own drawn walled off in the east of the grid (none can be walked to):
- The Deep Lift (lift, mine style: Elevator and its pit; laid switched OFF): from the pithead yard down to the Deep
  Level, the company's new galleries. Why: the main quest. The deep shift rode it down three days ago and the cage came
  back empty; Bram the overseer stopped it. When the Warden gives the player the quest, Bram throws the brake off
  (A.enable): the lift runs from then on. Two-way by nature. The Deep Level: the shaft chamber, a gallery south-east
  past the side pocket where the shift made its stand (Tam's lantern lies there: Dunstan's quest), and the far cavern
  where Gnash the Troll lairs on the shift's bones with the company's lost pay chest. Gnash dead, the Warden opens the
  pass gate.
- The tower stairs (stairs, castle: GalavaStairsUp1 on the ground floor, GalavaStairsDown on the upper floor): the
  Warden's tower is two floors; its ground floor (the guard room, on the town's land, Sergeant Coll at the door) has the
  flight up against its north-east wall; the upper floor (the Warden's solar, drawn elsewhere) has the flight down in
  its west corner. Why: Warden Halvard, who gives the main quest and pays for it, sits upstairs; the player climbs to
  him and comes back down. Two-way.
- Wren's Ring (portal: TeleportPentagram pads; laid switched OFF): a pentagram in a ring of standing stones by Wren's
  hut in the east pines, to the Eyrie, the old shrine on top of the crag (a crag top drawn walled off: no path climbs
  to it). Why: Wren's quest, the Ankh of the Eyrie. She wakes the ring (A.enable on both pads and the ring's light)
  when the player takes it; a pentagram at the Eyrie leads back.
- The crawl-hole (passage: a scripted fade): at the end of the old mine tunnel, in front of the rockfall, a gap the
  Urchins use; step into it and the screen fades, and the player wakes in the Old Workings, the caved-in galleries
  beyond (a cave drawn elsewhere). Why: Corwin the paymaster's quest, the Urchins who steal the miners' pay. Two-way:
  a spot in the Old Workings leads back.

The story
- The player comes up the south road. Old Dunstan waits by the road: his son Tam went down with the deep shift.
- Main quest, the Silent Shift: Warden Halvard (upstairs in his tower) has shut the pass gate until the deep is open
  again. He sends the player down the Deep Lift; Bram starts it. In the Deep Level, scorpions in the galleries and Gnash
  the Troll in the far cavern. Gnash dead, the Warden pays, gives mail and opens the pass gate; the pass road north
  (the exit) leads to the Rime Pass.
- Tam's Lantern (the fate of a missing man): Dunstan asks the player to find his son. Tam's remains and his lantern lie
  in the side pocket of the Deep Level; Dunstan gives his old helm for the lantern.
- The Ankh of the Eyrie (a fetch through a portal): Wren wakes her ring; the Eyrie's shrine is haunted by the ghosts of
  its keepers and a will-o'-the-wisp; the Ankh is in the shrine's chest. Wren pays in potions, an amulet and gold.
- The Urchins in the Old Workings (a bounty through a passage): Corwin the paymaster pays when the Urchins and their
  shaman, Nib, are dead.
- The store, the smithy and the inn buy and sell; chests in every far place, two caches in the pines and the houses'
  stores hold loot; everyone in town knows something.

    py mapgen/designs/ironcrag.py [seed]
"""
QA_ACCEPT = [   # (tests/qa.py)
    # the town's houses are the kit's own (generate_building + the furnisher at master 2026-10-08): the same warnings
    # come out of every map rebuilt today (Thornwick rebuilt at master: 14 sparse rooms, 2 bunched); a furnisher
    # matter for the room lab, not this map's (seed 5 had the fewest of 12 seeds tried: 1-12)
    ("composition", r"is sparse: furniture covers",
     "the kit's furnisher fills small house rooms under the half-median house rule on every map at master (Thornwick's "
     "rebuild: 14); the room lab's work, not this map's"),
    ("composition", r"bunched into one part of the room \(offset 0\.77",
     "a 16-tile bedroom of a kit house, 0.01 over the line; the room picture reads as a bedroom"),
    ("composition", r"beds scattered about the room",
     "the bunkhouse's bunks stand in two rows, one along each long wall of an L-shaped barracks (room picture 8); "
     "the check reads two rows as scattered"),
    ("floors", r"outdoor Redbrick3 lies on a room's floor",
     "a hearthstone (kit/shells.py lay_zones) of a kit house laid by its doorway; a shells matter, not this map's"),
    ("exterior", r"A Lantern lies outdoors",
     "Tam's lantern is Dunstan's quest item, lying by his remains in the Deep Level (underground, not decor)"),
    ("density", r"^Many share of floor seams with edge pieces",
     "every open seam blended, as the kit always blends them; the seams at walls are hard by rule (TW-12)"),
]
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL, px, uv_to_xy, rect_tiles, rect_wall_cells
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import Land, square_tile, square_px, px_square, bfs_distance
from kit.vegetation import Planter, TOWN_PLANTING, FORESTS
from kit.village import Village
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT
from kit.mine import MineEntrance
from kit.model import Room, Door
from kit.originality import furnish_original
from kit.transport import Transporters, geometry as tp_geometry
from kit.posts import camp_posts
from kit import camps
from kit.story import StoryMap
from kit.dressing import Exterior

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 5
rng = random.Random(SEED)
NAME = "Ironcrag"
FOREST = "pine"
PATH = "DirtDark2"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "ironcrag")
NEXT_MAP = "RimePass"                 # the pass road north comes over the saddle into the Rime Pass
FAR_X = 180                           # cells: the grid east of this is the far places' (never the town's land)


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
    theme="a mining town under a crag at the foot of the high pass: log and stone houses round the pithead yard, the "
          "old mine's rock face and the Deep Lift beside its mouth, the Warden's stone tower on the rise, the pass gate "
          "shut on the road north, Wren's hut and ring of stones in the east pines; below and above, reached only by "
          "lift, stairs, portal and a crawl-hole: the Deep Level, the Warden's solar, the Eyrie shrine and the Old "
          "Workings",
    environment="town", mood="grim, watchful, cold",
    areas=[AreaIdentity("south", "the south road coming up out of the pines: the start"),
           AreaIdentity("town", "the pithead yard under the rock face and the houses round it", landmark="the Deep Lift"),
           AreaIdentity("keep", "the rise where the Warden's tower stands"),
           AreaIdentity("ring", "Wren's hut and her ring of standing stones in the east pines"),
           AreaIdentity("gate", "the pass gate, shut"),
           AreaIdentity("north", "the pass road on north: the way out")],
    buildings=[BuildingIdentity("foreman", "town", "the company office", "Corwin the paymaster"),
               BuildingIdentity("store", "town", "the company store", "the storekeeper"),
               BuildingIdentity("smithy", "town", "the smithy", "Torra the smith"),
               BuildingIdentity("inn", "town", "The Cage & Candle", "the innkeeper"),
               BuildingIdentity("bunkhouse", "town", "the bunkhouse", "the miners", style="stone_house"),
               BuildingIdentity("home", "town", "Dunstan's house", "Dunstan and Tam"),
               BuildingIdentity("home", "town", "", "a miner's family"),
               BuildingIdentity("herbwife", "ring", "Wren's hut", "Wren")])

m = Spec(NAME, summary="Ironcrag", description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"Generated by Claude.", author="vdystopia (generated by Claude)", version="1", date="2026", type=SOLO,
         minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [136, 138, 148]          # a cold mountain light
q = QuestBook(NAME)
presets = json.load(open(os.path.join(HERE, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]


def preset(family, intensity="full"):
    ps = [p for p in presets if p["family"] == family and p["intensity_class"] == intensity] or \
         [p for p in presets if p["family"] == family]
    return dict(max(ps, key=lambda p: p["weighted_share"])["xfer"])


# ---- 1. the plan: the south road up to the pithead yard, the ways to the tower, the ring and the pass -----------------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"south": ((100, 222), 18), "town": ((92, 140), 60), "keep": ((140, 96), 16), "ring": ((146, 178), 26),
         "gate": ((124, 58), 12), "north": ((132, 26), 12)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "town")
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_ in (("south", "town", 14, True), ("town", "keep", 12, True), ("town", "gate", 13, True),
                          ("gate", "north", 12, True), ("town", "ring", 12, True)):
    land.link(a_, b_, w_, bend=0.2, road=road_, pockets=(1, 2))
land.blends(m)
# the east of the grid is the far places': the town's land never grows there
land.forbidden |= {(i, j) for i in range(0, 260) for j in range(-130, 130) if i + j + 1 >= FAR_X}

# ---- 2. the centre: the pithead yard, the old mine's rock face on its north-west side, the roads leaving it ----------
land.paint_square(m, "town", 12, "RoughCobble")
vc = land.areas["town"]["c"]
mine = MineEntrance(land, set(land.plaza), (-1, 0), rng, depth=12, width=3, gap=4, reach=4, rock=12)
mine.plan()
lm, half = mine.lm, mine.width // 2
LIFT_OL = (-2.2, lm + 4.2)                       # the Deep Lift: in the forecourt, beside the tunnel's mouth
lift_xy = mine.px(*LIFT_OL)
lift_sq = px_square(*lift_xy)
land.taken |= {(lift_sq[0] + a, lift_sq[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1)}
CRAWL_O = 12 - 5.6                               # the crawl-hole: in the tunnel, in front of the rockfall
crawl_xy = mine.px(CRAWL_O, lm)
crawl_back_xy = mine.px(CRAWL_O - 1.9, lm)       # where the player comes back out of the Old Workings
# the Warden's tower: a square of Galava stone on the rise, its door on the south-west wall at the road's end
kc = land.areas["keep"]["c"]                     # squares
KU, KV = int(round(kc[0])) * 2, int(round(kc[1])) * 2    # the road ends at the square in front of the door
TOWER = (KU - 10, KU + 10, KV, KV + 20)          # u0, u1, v0, v1 (the SW wall on v0)
tower_sq = {(i, j) for i in range(TOWER[0] // 2, TOWER[1] // 2) for j in range(TOWER[2] // 2 + 1, TOWER[3] // 2 + 1)}
land.taken |= {(i + a, j + b) for i, j in tower_sq for a in (-1, 0, 1) for b in (-1, 0, 1)}
land.taken_strict |= tower_sq
land.reserved |= tower_sq                       # no road paved into it

land.paint_roads(m, PATH, width_squares=2.6, skip=land.reserved)

# ---- 3. buildings from the yard outwards; none on the tower's rise or by the start ------------------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"south": 8, "keep": 8, "gate": 6}, first=("ring",))
sm.connect_and_furnish(path_material=PATH)

# ---- 4. the land grows round everything, ending in the pines -------------------------------------------------------
land.carve(margin=3.5)
mine.cut()
lane_ = sm.keep_open({"south": 5, "ring": 4, "keep": 3})
clumps = land.thickets(110, size=(0.9, 1.8), clear=1, avoid=frozenset(lane_ & land.squares))
land.open_links()
land.apply(m, wall=FORESTS[FOREST]["wall"], floor="GrassNorm", unlevel=True)
mine.ground(m, track=PATH)
gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "north"), prefix="PassGate", material="StoneGray")

# the tower's ground floor: the guard room, the stairs up against its north-east wall
m.room(*TOWER, wall="GalavaTownWall", floor="GalavaBrick")
tower_tiles = set(rect_tiles(*TOWER))
for t_ in tower_tiles: m.indoor[t_] = "GalavaBrick"
door_gap = tuple(int(c) for c in uv_to_xy(KU, TOWER[2]))
tdoor = m.door(None, door_gap, "\\")
land.wall_cells |= set(rect_wall_cells(*TOWER))
tower_room = Room(id="tower", tiles=tower_tiles, floor="GalavaBrick", walls=rect_wall_cells(*TOWER),
                  doors=[Door(gap=door_gap, line="\\", type=tdoor["type"], connects=("tower", "outside"),
                              px=(tdoor["x"], tdoor["y"]))], kind="guardroom", building="the Warden's tower")

# ---- the far places, each drawn walled off east of the town's land -------------------------------------------------
def cave(circles, capsules=(), wall="CaveWall", floor="DirtDark2"):
    """A walled-off place of its own: the squares within the circles [(X, Y, r) in cells] and along the capsules
    [((X0, Y0), (X1, Y1), half width)], walled round as the land is (a Land of its own, so the town's planting and
    dressing never reach it). Returns the Land."""
    def inside(X, Y):
        if any(math.hypot(X - cx, Y - cy) <= r for cx, cy, r in circles): return True
        for (x0, y0), (x1, y1), w in capsules:
            dx, dy = x1 - x0, y1 - y0
            t = max(0.0, min(1.0, ((X - x0) * dx + (Y - y0) * dy) / (dx * dx + dy * dy)))
            if math.hypot(X - x0 - t * dx, Y - y0 - t * dy) <= w: return True
        return False
    sq = {(i, j) for i in range(60, 250) for j in range(-40, 130) if inside(i + j + 1, i - j + 1)}
    L = Land(rng)
    L.squares = Land._largest(Land._fix_pinches(sq))
    assert all(i + j + 1 >= FAR_X for i, j in L.squares)
    L.apply(m, wall=wall, floor=floor, unlevel=True)
    return L


# the Deep Level: the shaft chamber, the gallery, the side pocket of the shift's last stand, Gnash's cavern
DEEP_PIT, DEEP_POCKET, DEEP_LAIR = (200, 180), (219, 182), (227, 214)
deep = cave([(*DEEP_PIT, 8), (*DEEP_POCKET, 6), (*DEEP_LAIR, 11)],
            [((200, 180), (214, 200), 4.2), ((207, 184), (219, 182), 3.4), ((214, 200), (227, 214), 4.6)],
            wall="ManaMineWall", floor="ManaMineDirt")
# the Old Workings: the entry chamber where the crawl-hole comes out, the passage, the Urchins' cavern
OLD_IN, OLD_DEN = (196, 134), (224, 132)
old = cave([(*OLD_IN, 6), (*OLD_DEN, 10)], [(OLD_IN, OLD_DEN, 3.4)], wall="CaveWall", floor="CaveHardBrown")
# the Eyrie: the crag top with the shrine, a ledge where the pentagram from the ring lands
EYRIE_C, EYRIE_LEDGE = (216, 80), (200, 70)
eyrie = cave([(*EYRIE_C, 12), (*EYRIE_LEDGE, 6)], [(EYRIE_LEDGE, EYRIE_C, 4.0)], wall="Rock", floor="GrassSparse2")
# the Warden's solar: the tower's upper floor, the stairs down in its west corner
SOLAR = (238, 262, 166, 188)
m.room(*SOLAR, wall="GalavaTownWall", floor="GalavaBrick")
solar_room = Room(id="solar", tiles=set(rect_tiles(*SOLAR)), floor="GalavaBrick", walls=rect_wall_cells(*SOLAR),
                  doors=[], kind="solar", building="the Warden's tower")

# the stairs' ends (kit/transport STAIRS castle; Westwood's offsets, rules/out/transporters.json)
geo = tp_geometry()["stairs"]
STAIR_DOWN = px(SOLAR[0] + 5, SOLAR[2] + 6)       # in the solar's west corner
STAIR_UP = px(KU, TOWER[3] - 2)                   # against the guard room's north-east wall


def stairs_zone(main, at):
    g = geo[main]
    pts = [at, (at[0] + g["pad"][0], at[1] + g["pad"][1]), (at[0] + g["arrive"][0], at[1] + g["arrive"][1])]
    pts += [(at[0] + dx, at[1] + dy) for _, dx, dy in g["pieces"]]
    return pts


def clear_round(pts, r, keep=()):
    """Takes out the furniture within r px of the points (the stairs and their landing stay clear)."""
    keep = {id(o) for o in keep}
    gone = [o for o in m.d["objects"] if id(o) not in keep and "x" in o and
            any(math.hypot(o["x"] - x, o["y"] - y) < r for x, y in pts)]
    ids = {id(o) for o in gone}
    m.d["objects"][:] = [o for o in m.d["objects"] if id(o) not in ids]
    return gone


furnish_original(m, tower_room, kind="guardroom", rng=random.Random(SEED * 31 + 1), style="town")
furnish_original(m, solar_room, kind="solar", rng=random.Random(SEED * 31 + 2), style="town")
clear_round(stairs_zone("GalavaStairsUp1", STAIR_UP), 62)
clear_round(stairs_zone("GalavaStairsDown", STAIR_DOWN), 62)

# ---- 5. the town's life ------------------------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Cage & Candle\nAle and a bunk", "Sign"),
                     store=q.text("Ironcrag Company Store", "Sign"),
                     foreman=q.text("Company Office\nPay on the last day", "Sign"),
                     smithy=q.text("Torra's Smithy", "Sign"))
for bid, b in placed:
    role = BUILDINGS[bid.role]
    for sc in role["scenes"]: vil.scene(b, sc, role=bid.role)
    if rng.random() < role["garden"]: vil.garden(b, size=(rng.randint(3, 5), rng.randint(2, 4)))
land.ground_variety(m, clear=3)

# ---- 6. the story's places ------------------------------------------------------------------------------------------
C = {k: land.areas[k]["c"] for k in AREAS}
south_c, ring_c, keep_c, gate_c, north_c = C["south"], C["ring"], C["keep"], C["gate"], C["north"]


DOORS_SQ = [px_square(*d.px) for _, b in placed for d in b.entrances]


def off_road(c, clear=4.5, reach=12, doors=6):
    """The square nearest `c` with no road within `clear` squares, on open land, `doors` squares from every door: a
    place beside its way, not on it."""
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


# the old mine's mouth: timbers, the rockfall, torches; the Deep Lift beside it with its winch and gears and a lamp
mine.dress(m, torch=torch_pole)
lift_keep = []
for t_, o_, l_ in (("Gear3", -0.35, lm + 5.6), ("Gear3", -0.4, lm + 6.3)):
    lift_keep.append(m.obj_px(t_, *mine.px(o_, l_)))
lift_keep.append(m.obj_px("ColorLight", lift_xy[0], lift_xy[1] - 6, xfer=preset("orange")))
clear_round([lift_xy], 46, keep=lift_keep)
# Wren's ring in the east pines: seven stones round the pentagram, its light dark until she wakes it
ring_at = off_road((ring_c[0] + 2.0, ring_c[1] - 2.0), clear=3.0, reach=11)
ring_xy = camps.stone_ring(m, rng, land, ring_at, n=7, radius=2.6, stone="ObeliskPrimitive", light=preset("blue"),
                           light_name="RingLight", clear=3)
# caches in the pines, off the ways
caches = []
for near_, loot_, stump_ in ((south_c, [("Gold", {"Amount": 45}), "CurePoisonPotion", "RedPotion"], True),
                             (ring_c, [("Gold", {"Amount": 50}), "LeatherBoots", "BluePotion"], False)):
    s_ = sm.hidden_spot(near_, r=(6, 14))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
# signposts
camps.signpost(m, land, (south_c[0] + 2.5, south_c[1] - 1.5), q.text("IRONCRAG\nMind the ore carts.", "Sign"))
gs_ = sm.road_near(((gate_sq[0] * 2 + vc[0]) / 3, (gate_sq[1] * 2 + vc[1]) / 3))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 1.5), q.text("PASS CLOSED\nBy order of the Warden.", "Sign"))
ls_ = mine.pt(-3.4, lm + 6.6)
camps.signpost(m, land, ls_, q.text("THE DEEP LIFT\nNo riders without the Overseer!", "Sign"))

# the Deep Level's contents: the shaft chamber's timbers and lamp, the shift's last stand, Gnash's lair and the pay chest
dsc = camps.Scene(m, rng, deep, sq_of(*DEEP_PIT))
pit_xy = P(*DEEP_PIT)
m.obj_px("ColorLight", pit_xy[0], pit_xy[1] - 6, xfer=preset("orange"))
for t_, r_, a_ in (("MinePost3", 4.2, 0.4), ("MinePost3", 4.2, 2.0), ("MineOreCart1", 4.0, 3.6), ("BarrelWithTools1", 4.4, 4.6),
                   ("MiningPickAxeOnGround2", 3.6, 5.4), ("AmbMineCreaks", 2.5, 1.2)):
    dsc.put(t_, *dsc.at(r_, a_))
psc = camps.Scene(m, rng, deep, sq_of(*DEEP_POCKET))
for t_, r_, a_ in (("CorpseSkullS", 0.6, 0.3), ("CorpseRibCageS", 0.9, 1.2), ("CorpseLeftLowerLegE", 1.1, 2.0),
                   ("MineOreCartBroken1", 2.6, 3.4), ("MiningPickAxeInGround1", 2.0, 4.6), ("Skull", 2.4, 5.6),
                   ("ArmBone", 1.6, 0.9)):
    psc.put(t_, *psc.at(r_, a_))
tam_lantern = psc.put("Lantern", *psc.at(0.4, 4.0))
assert tam_lantern, "Tam's lantern found no floor"
lsc = camps.Scene(m, rng, deep, sq_of(*DEEP_LAIR))
for t_, r_, a_ in (("Skull", 1.2, 0.2), ("LegBone", 1.5, 0.9), ("ArmBone", 1.3, 1.6), ("Skull", 1.7, 2.5),
                   ("LegBone", 1.9, 3.3), ("CorpseRibCageS", 1.6, 4.2), ("ArmBone", 2.1, 5.1), ("CaveBoulders", 4.6, 2.2),
                   ("CaveRocksLarge", 4.4, 5.8), ("MineCrystal03", 4.8, 0.6), ("MineCrystal05", 4.9, 3.8)):
    lsc.put(t_, *lsc.at(r_, a_))
lair_chest = lsc.put("Chest3", *lsc.at(3.6, 4.8), items=[("Gold", {"Amount": 120}), "RedPotion", "RedPotion",
                                                        "BluePotion", "ChainCoif"])
assert lair_chest, "the pay chest found no floor"
lair_xy = P(*DEEP_LAIR)
m.obj_px("ColorLight", lair_xy[0], lair_xy[1] - 6, xfer=preset("red", "dim"))
for X_, Y_, t_ in ((208, 191, "MineCrystalUp02"), (211, 197, "MineCrystal01"), (218, 205, "MineCrystal04")):
    camps.Scene(m, rng, deep, sq_of(X_, Y_)).put(t_, *sq_of(X_, Y_))

# the Old Workings: the Urchins' den in the cavern (kit/camps: their beds, table, pickings and the shaman's place)
old_in_xy, old_den_sq = P(*OLD_IN), sq_of(*OLD_DEN)
m.obj_px("ColorLight", old_in_xy[0], old_in_xy[1] - 6, xfer=preset("orange", "full"))
den = camps.urchin_camp(m, rng, old, old_den_sq, sq_of(*OLD_IN),
                        loot=[("Gold", {"Amount": 70}), "RedPotion", "CurePoisonPotion", "Quiver"], sleepers=4)
osc = camps.Scene(m, rng, old, sq_of(*OLD_IN))
for t_, r_, a_ in (("CaveRocksLarge", 3.6, 1.0), ("CaveRocksMedium", 3.8, 2.6),
                   ("MineOreCartBroken2", 3.4, 4.4)):
    osc.put(t_, *osc.at(r_, a_))

# the Eyrie: the shrine's ring of stones round its dead fire, the keepers' chest with the Ankh
eyrie_sq = sq_of(*EYRIE_C)
shrine_xy = camps.stone_ring(m, rng, eyrie, eyrie_sq, n=6, radius=2.4, stone="Obelisk", core="DunMirAltar1",
                             light=preset("white", "dim"), light_name="ShrineLight", clear=2)
esc = camps.Scene(m, rng, eyrie, eyrie_sq)
shrine_chest = esc.put("Chest4", *esc.at(4.0, 5.5), items=["AnkhTradable", ("Gold", {"Amount": 40}), "BluePotion"])
assert shrine_chest, "the shrine's chest found no floor"
for t_, r_, a_ in (("Skull", 4.6, 1.0), ("LegBone", 5.0, 1.6), ("CaveRocksLarge", 6.4, 3.0), ("CaveRocksMedium", 6.0, 0.2),
                   ("Boulder", 7.0, 4.4)):
    esc.put(t_, *esc.at(r_, a_))

# ---- 7. lights and planting, the start and the exit ------------------------------------------------------------------
keep = set()
for bid, b in placed:
    for d in b.entrances:
        di, dj = px_square(*d.px)
        keep |= {(di + a, dj + b2) for a in range(-2, 3) for b2 in range(-2, 3)}
keep |= {(i + a, j + b) for i, j in tower_sq for a in range(-2, 3) for b in range(-2, 3)}
vil.ground_bits(1.4)
planter = Planter(m, rng, land, FOREST, keep_clear=keep | lane_, settled=("town",))
n_trees, n_small = planter.plant_all(groves=4, profile=TOWN_PLANTING)
piles = planter.rock_piles(max(4, len(land.squares) // 900))
vignettes = planter.forest_floor(max(6, len(land.squares) // 700))
start_xy = square_px(south_c[0] + 0.5, south_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
sm.exit_to("north", NEXT_MAP, prefix="PassExit")

# ---- the transporters (skills/nox-transporters): each to its far place, each with its purpose ------------------------
tp = Transporters(m)
lift = tp.add("lift", lift_xy, pit_xy, "DeepLift", style="mine", enabled=False, serves=[(lair_chest["x"], lair_chest["y"]),
                                                                                         (tam_lantern["x"], tam_lantern["y"])])
stairs = tp.add("stairs", STAIR_DOWN, STAIR_UP, "TowerStair", style="castle")
portal = tp.add("portal", ring_xy, P(*EYRIE_LEDGE), "CragRing", enabled=False,
                serves=[(shrine_chest["x"], shrine_chest["y"])])
den_chest = den.get("chest")
den_chest = (den_chest["x"], den_chest["y"]) if isinstance(den_chest, dict) else den_chest
crawl = tp.add("passage", crawl_xy, P(*OLD_IN), "CrawlHole", arrive_a=crawl_back_xy, serves=[den_chest] if den_chest else [])
for t_ in (lift, portal, crawl):                 # the town's dressing and folk keep off every end and landing
    for p_ in (t_.a, t_.arrive_a):
        if p_:
            s_ = px_square(*p_)
            land.taken |= {(s_[0] + a, s_[1] + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}

# ---- 8. the people --------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
person, room_of, free_px = sm.person, sm.room_of, sm.free_px
vx, vy = square_px(*vc)
# Dunstan by the south road, looking up it toward the town
dx_, dy_ = square_px(south_c[0] - 1.5, south_c[1] + 2.5)
person("Con03B", "Dudley", dx_, dy_, "Dunstan", face=start_xy)
# Warden Halvard in his solar, Sergeant Coll inside the tower's door
wx_, wy_ = free_px(solar_room, prefer=px((SOLAR[0] + SOLAR[1]) / 2, (SOLAR[2] + SOLAR[3]) / 2), clear=34)
person("Con02a", "Mayor_Theogrin", wx_, wy_, "Halvard", face=STAIR_DOWN)
cx_, cy_ = free_px(tower_room, prefer=(tdoor["x"] + 50, tdoor["y"] - 40), clear=32)
person("War02A", "F2Sargent", cx_, cy_, "Coll", face=(tdoor["x"], tdoor["y"]))
# Bram at the mine head, beside the lift's winch, off the cage
bx_, by_ = mine.px(-2.0, lm + 6.9)
person("Con03B", "Foreman", bx_, by_, "Bram", face=(vx, vy))
# Corwin at the company office's door, Wren at her hut's door
cw_ = sm.doorside("foreman", toward=(vx, vy)) or (vx + 60, vy)
person("Con03B", "Garrit", cw_[0], cw_[1], "Corwin", face=(vx, vy))
wr_ = sm.doorside("herbwife", toward=ring_xy) or square_px(*ring_c)
person("War01A", "Evelyn", wr_[0], wr_[1], "Wren", face=ring_xy)
# the gate warden on the town side of the pass gate
gq_ = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
gdx, gdy = vx - gq_[0], vy - gq_[1]
gl = math.hypot(gdx, gdy) or 1
person("Con02a", "IxGuard1", gq_[0] + 70 * gdx / gl + 26, gq_[1] + 70 * gdy / gl, "GateWarden", face=(vx, vy))
# shopkeepers
WARES = {"store": [(4, "RedPotion"), (3, "BluePotion"), (2, "CurePoisonPotion"), (4, "RedApple"), (2, "Meat"),
                   (2, "Quiver"), (1, "Bow"), (1, "LeatherBoots"), (1, "LeatherHelm"), (1, "LeatherArmor")],
         "inn": [(6, "RedApple"), (5, "Meat"), (4, "Cider"), (4, "Bread"), (2, "RedPotion")],
         "smithy": [(2, "Sword"), (1, "Longsword"), (1, "BattleAxe"), (1, "WarHammer"), (1, "WoodenShield"),
                    (1, "SteelShield"), (1, "ChainCoif"), (1, "ChainTunic"), (1, "ChainLeggings"), (1, "SteelHelm")]}
GREET = {"store": q.text("Bad days down the shaft, lad. Eight men gone and the lift stopped! Buy what you need now. "
                         "Prices go up with every funeral.", "Shop"),
         "inn": q.text("Sorry, stranger, the larder's half empty. Nobody drinks to a lost shift. Heh, heh...", "Shop"),
         "smithy": q.text("You and I could do business! Provided you buy more than you haggle!", "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"smithy": "ShopkeeperWarriorsRealm"})
# townsfolk, each with something to say; none stops by the lift, the crawl-hole or the ring
for c_, r_ in ((lift_sq, 4), (px_square(*crawl_xy), 6), (ring_at, 6), (keep_c, 4)):
    sm.keep_folk_away(c_, r_)
FOLK = [("Con03B", "Alex"), ("Con03B", "Claude"), ("Con01A", "Tanya2"), ("Con03B", "Naldo"), ("Con03B", "Logan"),
        ("War01A", "Melissa")]
RUMOURS = [
    "Hm? Not now. I'm due on shift.",
    "Out of the way! This ore won't haul itself!",
    "There's a ring of old stones by Wren's hut in the east pines. They say it once carried the shrine-keepers up to "
    "the Eyrie!",
    "What're y' starin' at? Never seen a miner?",
    "The Urchins have been at the company strongroom again! Corwin's looking for help!",
    "Mother says strangers are trouble. Are you trouble?",
]
ring = sm.townsfolk(FOLK, vc, q=q, rumours=RUMOURS,
                    after=("warden_paid", "Nice work down the shaft! I hear the Warden's well pleased!"),
                    pics=("MalePic1", "MalePic7", "MaidenPic3", "Townsman1Pic", "MalePic10", "MaidenPic2"),
                    radius=7.0)
# the watch, on a beat round the yard
wx2, wy2 = ring[0]
person("Con01A", "Contest_Guard", wx2, wy2, "Watch1", action=0)
sm.beat("Watch1", vc, radius=7.0, stops=7)

# ---- 9. the fights ----------------------------------------------------------------------------------------------------
# the Deep Level: scorpions in the gallery and the pocket, Gnash and two more in his cavern (none by the pit, which
# would carry them up)
deep_foes = []
for k_, (X_, Y_) in enumerate(((209, 192), (215, 199), (221, 184), (217, 180), (222, 207), (231, 207), (233, 220),
                                (223, 189))):
    n_ = f"DeepScorp{k_ + 1}"
    pop.creature("Scorpion", *P(X_, Y_), action="guard", scr=n_, aggr=0.83, face=pit_xy)
    deep_foes.append(n_)
pop.creature("Troll", *P(DEEP_LAIR[0] + 2, DEEP_LAIR[1] + 2), action="guard", scr="Gnash", aggr=0.83,
             HealthMultiplier=2.0, face=P(214, 200))
# the Old Workings: the Urchins at their posts in the den, Nib the shaman by the pickings
den_posts = camp_posts(m, den, old_in_xy, sit=3, tents=2, watch=1)
urchins = []
pop.creature("UrchinShaman", *den_posts["leader"], action="guard", scr="Nib", aggr=0.83, face=old_in_xy)
for k_, (x_, y_) in enumerate(den_posts["sit"] + den_posts["tent"] + den_posts["watch"]):
    n_ = f"OldUrchin{k_ + 1}"
    pop.creature("Urchin", x_, y_, action="guard", scr=n_, aggr=0.83, face=old_in_xy)
    urchins.append(n_)
all_urchins = ["Nib"] + urchins
# the Eyrie: the dead keepers walk the crag top round the shrine, the wisp at the shrine
eyrie_foes = []
for k_, a_ in enumerate((0.8, 2.3, 3.8, 5.0)):
    n_ = f"EyrieGhost{k_ + 1}"
    pop.creature("Ghost", *square_px(eyrie_sq[0] + 5.2 * math.cos(a_), eyrie_sq[1] + 5.2 * math.sin(a_)), action="guard",
                 scr=n_, aggr=0.83, face=shrine_xy)
    eyrie_foes.append(n_)
pop.creature("WillOWisp", *square_px(eyrie_sq[0] + 3.4 * math.cos(5.6), eyrie_sq[1] + 3.4 * math.sin(5.6)),
             action="guard", scr="EyrieWisp", aggr=0.83, face=shrine_xy)
eyrie_foes.append("EyrieWisp")
# white wolves down from the heights on the pass road beyond the gate: one more reason it is shut
pass_wolves = []
for k_, (a_, r_) in enumerate(((0.6, 2.4), (2.4, 2.8), (4.4, 2.2))):
    n_ = f"PassWolf{k_ + 1}"
    pop.creature("WhiteWolf" if k_ else "BlackWolf", *square_px(north_c[0] + r_ * math.cos(a_), north_c[1] + r_ * math.sin(a_)),
                 action="idle", scr=n_, aggr=0.83, face=square_px(*gate_c))
    pass_wolves.append(n_)
B.pack(pass_wolves[0], pass_wolves[1:])
# the pines' own creatures by the forest's edge, away from the town and the story's places
for k_, (X_, Y_) in enumerate(((211, 194), (205, 188))):        # bats under the gallery's roof, off the pit
    pop.creature("Bat", *P(X_, Y_), action="guard", scr=f"DeepBat{k_ + 1}", aggr=0.83)
for k_, (X_, Y_) in enumerate(((210, 133), (204, 129))):        # bats in the Old Workings' passage
    pop.creature("Bat", *P(X_, Y_), action="guard", scr=f"OldBat{k_ + 1}", aggr=0.83)
sm.wild({"Wolf": 2, "Bat": 3, "SmallAlbinoSpider": 2}, away_from=vc, per100=0.55, gap=7, min_away=30,
        avoid=(south_c, ring_c, keep_c, gate_sq, north_c))
story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]
            if o["x"] < FAR_X * CELL] + [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)

# ---- 10. the story ----------------------------------------------------------------------------------------------------
q.start([A.lock("PassGate1"), A.lock("PassGate2"), A.disable("PassExit1"), A.disable("PassExit2"),
         A.disable("PassExit3"), A.disable("RingLight"),
         q.journal("Find someone in Ironcrag who can open the pass north.", HINT)])

# Dunstan: the hook, and Tam's Lantern
q.talker("Dunstan", q.errand(
    "Dunstan", "tam",
    offer="Merciful stars, a traveller! My boy Tam rode the Deep Lift down with the deep shift. None of them came "
          "back up!\n\nThe Warden won't let a soul down that shaft. He sits up in his tower, on the rise past the "
          "pithead.\n\nIf you go down there, find my Tam. I'll give you my old helm. Will you look for him?",
    reminder="Any word of my Tam? Oh, I can't eat for thinking of him.",
    thanks="His lantern! My poor boy. Dark luck took him in that hole.\n\nYou went where the rest of us couldn't. "
           "Here, my old helm. Wear it below ground.",
    after="Tam would have liked you, I think.",
    objective="Learn what became of Dunstan's son Tam in the deep galleries.",
    done=q.when(has="Lantern"), reward=[A.give("SteelHelm")],
    refusal="Then I'll keep waiting by the road."))
q.on_pickup("Lantern", [q.note("NOTE: Tam's lantern lay by the bones of the deep shift's last stand.")],
            when=q.at("tam", 1))

# Warden Halvard, upstairs: the main quest and the gate
MAIN = "Descend the Deep Lift and slay what killed the deep shift."
q.talker("Halvard", [
    q.say("The pass is open, Adventurer. Ironcrag won't forget this.", when=q.when(flag="warden_paid"), who="Halvard"),
    q.say("A Troll! In my own deep galleries! Then it's finished, and Ironcrag owes you its pass.\n\nTake this "
          "breastplate and the purse. The gate's open. Good luck!",
          when=q.when(flag=q.dead("Gnash"), not_="warden_paid"),
          do=[A.flag("warden_paid"), A.gold(200), A.give("Breastplate"), A.give("RedPotion", 2),
              A.unlock("PassGate1"), A.unlock("PassGate2"), A.enable("PassExit1"), A.enable("PassExit2"),
              A.enable("PassExit3"), A.stage("main", 4), q.done(MAIN)], who="Halvard"),
    q.say("Get down that shaft! I won't open the pass while my miners lie unavenged. Hurry! Whatever it is, it grows "
          "bolder every night.", when=q.when(flag="main_given"), who="Halvard"),
    q.say("So you want the pass. The gate stays shut. Three days ago the deep shift rode the Deep Lift down, and the "
          "cage came back up empty. Bram stopped the lift.\n\nGo down. Find what took my miners and kill it, and I'll "
          "open the gate myself. Bram runs the lift at the pithead. And careful, lad. Whatever's down there bends iron.",
          do=[A.flag("main_given"), A.stage("main", 1), q.journal(MAIN)], who="Halvard")])
q.on_death("Gnash", [A.flag("gnash_dead"), A.print("The Troll crashes down among the bones of the deep shift."),
                     q.note("NOTE: Gnash the Troll is dead. Warden Halvard waits in his tower.")])

# Bram, at the lift
q.talker("Bram", [
    q.say("You came back up! Most days that's all I ask of a man.", when=q.when(flag="gnash_dead"), who="Bram"),
    q.say("She's running. Step on the cage when you're ready. She brings you back the same way.",
          when=q.when(flag="lift_on"), who="Bram"),
    q.say("The Warden sent you? Then stand back from the cage. I'll take the brake off.\n\nShe runs on her own once "
          "she's going. Keep your blade out down there.",
          when=q.when(flag="main_given", not_="lift_on"),
          do=[A.flag("lift_on"), A.stage("main", 2)] + [A.enable(n) for n in lift.sources] +
             [A.print("Bram throws off the brake. Deep in the shaft, the lift's gears begin to grind.")], who="Bram"),
    q.say("Lift's stopped. Warden's orders. Nobody goes down.", who="Bram")])

# Sergeant Coll and the gate warden
q.talker("Coll", [
    q.say("The pass is open. Off with you, then.", when=q.when(flag="warden_paid"), who="Guard"),
    q.say("The Warden's up the stairs. Don't keep him waiting!", who="Guard")])
q.talker("GateWarden", [
    q.say("Warden says you're free to pass! Safe roads.", when=q.when(flag="warden_paid"), who="Guard"),
    q.say("Wanna argue with a shut gate? Go and see the Warden.", who="Guard")])
q.talker("Watch1", [
    q.say("Quiet down the shaft, they say. Good.", when=q.when(flag="gnash_dead"), who="Watch"),
    q.say("I don't get many strangers on my rounds.", who="Watch")])

# Wren and the Ankh of the Eyrie: she wakes the ring
q.talker("Wren", q.errand(
    "Wren", "ankh",
    offer="The Ankh of the Eyrie comes down to me at every thaw. This year the shrine-keepers never brought it.\n\n"
          "My ring of stones beside the hut is the old way up to the Eyrie, the shrine on top of the crag. I will wake "
          "it for you. Step into the circle and bring me the Ankh. Will you go?",
    reminder="Bring the Ankh down to me -- whatever it costs! Mind the stones up there. Something cold walks the crag.",
    thanks="The Ankh of the Eyrie! Thank goodness!\n\nSo the keepers are dead. I'll mourn them when the town can spare "
           "me. Ironcrag needs every blessing it can get.\n\nTake these, Adventurer, and go carefully!",
    after="The ring still hums at night. Leave it be.",
    objective="Retrieve the Ankh of the Eyrie from the shrine atop the crag.",
    done=q.when(has="AnkhTradable"),
    reward=[A.give("AmuletofNature"), A.give("CurePoisonPotion", 2), A.give("BluePotion", 2), A.gold(60)],
    refusal="Then the Eyrie keeps its Ankh.",
    on_take=[A.enable(n) for n in portal.sources] + [A.enable("RingLight"),
             A.print("Wren speaks a word. The stones hum, and the pentagram in the ring begins to glow.")]))
q.on_pickup("AnkhTradable", [q.note("NOTE: The Ankh of the Eyrie. Wren waits by her ring of stones.")],
            when=q.at("ankh", 1))

# Corwin and the Urchins of the Old Workings
q.talker("Corwin", q.errand(
    "Corwin", "urchins",
    offer="These thieving Urchins are worse than rats! The watch has run them off twice, but back they come! They take "
          "the miners' pay right out of the strongroom!\n\nThey come and go by a crawl-hole in the rockfall, at the end "
          "of the old tunnel by the pithead. Clear them out of the old workings and the company will pay. Will you?",
    reminder="I'll not sleep till those Urchins are gone! Kill their shaman and the rest are nothing! Hurry, before "
             "pay day!",
    thanks="Brave Adventurer, the company is in your debt! The miners get paid this week after all.\n\nTake this "
           "gold for your trouble. I insist.",
    after="The strongroom's quiet. I count the pay twice anyway.",
    objective="Drive the Urchins out of the old workings beyond the rockfall.",
    done=q.when(flag=q.dead(*all_urchins)), reward=[A.gold(120), A.give("RedPotion", 2)],
    refusal="Then the company will find someone who wants the money."))

# what the player sees on the way
q.near(*crawl_xy, 120, [A.print("A cold draught blows through a gap in the fallen rock.")])
q.near(*pit_xy, 200, [A.print("The air down here is hot and stinks of Troll.")])
q.near(*old_in_xy, 200, [A.print("This tunnel is dank and smells of Urchin...")])
q.near(*P(*EYRIE_LEDGE), 200, [A.print("Wind howls over the top of the crag. The shrine's fire is out.")])
q.on_all_dead(eyrie_foes, [A.print("The last of the Eyrie's dead fades into the wind.")])

for who_, pic_ in (("Dunstan", "MalePic8"), ("Halvard", "WardenPic"), ("Bram", "MalePic5"), ("Coll", "Warrior2Pic"),
                   ("GateWarden", "IxGuard1Pic"), ("Watch1", "Warrior3Pic"), ("Wren", "MaidenPic4"),
                   ("Corwin", "QuarterMasterPic")):
    q.portrait(who_, pic_)

m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())

# ---- 11. the exteriors' dressing ---------------------------------------------------------------------------------------
dressed = Exterior(m, land, "green", placed=placed).dress()


class _Far:                                          # the tower's two floors, for the rooms sidecar
    def __init__(self, rooms): self.rooms = rooms


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed + [(BuildingIdentity("tower", "keep", "the Warden's tower", "Warden Halvard"),
                             _Far([tower_room, solar_room]))], os.path.join(OUT, f"{NAME}.rooms.json"))
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS", "VOICE"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| trees {n_trees} | shops {n_shops} | caches {len(caches)} | opened {len(opened)} | lines {len(q.strings)} "
          f"| dressing {sum(dressed.values())} groups | far: deep {len(deep.squares)} old {len(old.squares)} "
          f"eyrie {len(eyrie.squares)} squares")
