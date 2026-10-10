"""The Hollow Choir, act 10: The Last Bell (map LastBell; campaign/hollowchoir/BIBLE.md). Brackwater again, the town of
act 1 (mapgen/designs/hc01_brackwater.py), built from the same plan (kit/hc_brackwater.py: the same seed, land, river,
bridges, quay, square and buildings), now burning: the Ember Brood has broken out from beneath the town. The woods
round it are scorched red (FORESTS["dusk"]), the old brown wood downstream (FORESTS["ancient"]); the ground is
trampled and burnt; the square has split open over a rift of fire where the Bell Shrine's well stood.

The story
- The hook: the player comes home by the river road from the west and finds the River Gate open and the town on fire.
  Hob, a wounded watchman at the gate, tells it: at sundown the ground split under the square and the Brood climbed
  out; Brother Edric is in the Bell Shrine with the bell. If the player let Rusk go in act 1 (RUSK_KNIFE), Rusk keeps
  his promise: he and his crew hold the south landing, and his men fight the Brood there.
- The Brood holds the town: fire-imps and ember demons at the south landing, a brood-mother (M4) at the north end of
  the town bridge, another on the quay among the refugees, imps round the rift in the square. If the player handed
  Rusk to Ilsa (WATCH_SEAL), Captain Ilsa and her watch hold the square and fight the imps round it; without the seal
  Ilsa stands there alone, her watch lost.
- Main quest, the Last Bell (counted stones, counted verses, a boss): Edric needs the five Spirit Stones set in the bell
  (SPIRIT_STONE, counted: the player sets them at the altar, one at a time) and the founders' verses read (VERSE_STONE,
  counted 0-3: Edric takes them at the altar). A player short of stones is told where they were lost, and Edric sends
  him for the founders' cracked stones in the reliquary in the shrine's crypt, where a brood-mother has broken in: they
  make the bell ring, but not true. The token path is the better one: with five true stones and all three verses (or
  two, and Tam to read the third: TAM_FREED), the bells ring true and the Brood is cut off at the first peal (every
  brood-creature left in the town burns away) and the Ember Matriarch rises alone; with fewer, she rises with a wave of
  her brood. The Matriarch (FOES["Matriarch"]: M4, 1,400 health) rises from the rift in the square; her death ends the
  campaign: the five bells ring out over the river.
- The Reliquary (RELIQUARY, act 2's choice): the Matriarch calls to the bone reliquary. Give it up to Edric before the
  ringing and he breaks it on the bell; keep it, and when the Matriarch rises it calls an extra wave of imps, and
  Edric's last line is a warning.
- Every side quest pays off: Doran (DORAN_LETTER, his guild medallion: the starsteel blade was forged in act 8; with
  STARSTEEL still carried: never forged, the same reward) gives his own hammer, the Quake Hammer (W3) at its best tier,
  once the player clears the ember demons from his forge yard (without the medallion: his old hammer, W3 at its first
  tier); Wenna waits in the shrine with her potions, and with TAM_FREED Tam
  stands beside Edric and reads the third verse; Ilsa offers a captain's place (WATCH_SEAL); Rusk says he will turn
  honest (RUSK_KNIFE); Vess appears by the shrine at the end and is gone again (VESS_OATH).
- The Last Barge (act 10's own): Gorm's barge waits at the quay for the refugees, but a brood-mother and her imps hold
  it. Clear the quay and the townsfolk board; Gorm pays.
- Doran's forge (S1) still burns: his journeyman works it. Wenna's herb shop is shut (she has carried her potions to the
  shrine), but Hanne's inn and Bram's river store still sell.
- The end: a closing sign in the shrine sums up the road, and the journal notes what became of each friend.

Tokens read: SPIRIT_STONE (count), VERSE_STONE (count), TAM_FREED (Tam's bell-token), WENNA_ASK, RELIQUARY,
WATCH_SEAL, RUSK_KNIFE, VESS_OATH, DORAN_LETTER, STARSTEEL. Given: none (the last act). Every branch works with an empty
pack: the cracked stones fill the bell, Edric reads what he remembers, the Matriarch is fought with her waves.

    py mapgen/designs/hc10_lastbell.py [seed]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import square_px, px_square, square_tile, bfs_distance
from kit.vegetation import Planter, FORESTS, TOWN_PLANTING
from kit.village import Village, _squares_of
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT, NOTE
from kit import camps
from kit.dressing import Exterior
from kit.mods import Mods
from kit.campaign import token, has, cast_person, voice, CAST, FOES
from kit.hc_scripts import HcScript
from kit import hc_brackwater as HB

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else HB.SEED
NAME = "LastBell"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "hc10_lastbell")

# Warnings accepted, each with its reason (tests/qa.py)
QA_ACCEPT = [
    ("density.range", r"Few wall pieces per 100 floor tiles",
     "a river town: the Brack and the Brack Pool are about a tenth of the floor and carry only invisible shore walls, "
     "and the open streets of a town on two banks leave the forest islands little room (Land.thickets places what fits)"),
    ("composition", r".",
     "the rooms are furnished by the shared kit (kit/furnish.py, kit/archetypes.py), which at its present tuning "
     "leaves some rooms of every map built now a point under the house rules (the same warnings stand in "
     "Starwell's, Ambermere's, Mirewood's and OgreMarch's QA); each room was looked at in qa/rooms.png and "
     "reads as what it is: reported, not this design's to change"),
    ("rooms.stray", r"does not belong|do not belong",
     "the rooms are furnished by the shared kit (kit/furnish.py, kit/archetypes.py), which at its present tuning "
     "leaves some rooms of every map built now a point under the house rules (the same warnings stand in "
     "Starwell's, Ambermere's, Mirewood's and OgreMarch's QA); each room was looked at in qa/rooms.png and "
     "reads as what it is: reported, not this design's to change"),
    ("pieces", r".",
     "the rooms are furnished by the shared kit (kit/furnish.py, kit/archetypes.py), which at its present tuning "
     "leaves some rooms of every map built now a point under the house rules (the same warnings stand in "
     "Starwell's, Ambermere's, Mirewood's and OgreMarch's QA); each room was looked at in qa/rooms.png and "
     "reads as what it is: reported, not this design's to change"),
]

NAMES = {"village_chapel": ("the Bell Shrine", "Brother Edric, with the bell"),
         "barracks": ("the watch house, burnt out", "nobody now"),
         "inn": ("the Bargeman's Rest", "Hanne the innkeeper and the refugees"),
         "smithy": ("Ashforge's smithy", "Doran Ashforge, holding his forge"),
         "apothecary": ("Fell's herb shop, shut", "nobody: Wenna has gone to the shrine"),
         "store": ("the river store", "Bram the chandler"),
         "mill": ("the old mill, burnt", "nobody")}
BLDG = [BuildingIdentity(b.role, b.area, NAMES.get(b.role, (b.name, ""))[0] if b.role in NAMES else b.name,
                         NAMES.get(b.role, (b.name, b.occupant + ", fled"))[1] if b.role in NAMES else
                         (b.occupant + ", fled to the quay" if b.occupant else "fled"),
                         style=b.style, extra=b.extra) for b in HB.BUILDINGS]

ID = MapIdentity(
    name=NAME,
    theme="Brackwater burning: the river town of the first bell on the night the Ember Brood breaks out beneath it; the "
          "square split over a rift of fire, the Bell Shrine where the five stones must be set, the watch house burnt "
          "out, the refugees on the quay waiting for the last barge, the River Gate open on the road home",
    environment="town", mood="fire, smoke, the last stand of a town",
    areas=[AreaIdentity("mire", "the river road from the west: the start, home from the Spire"),
           AreaIdentity("gate", "the River Gate, open"),
           AreaIdentity("south", "the south landing, the Brood's first foothold over the river"),
           AreaIdentity("town", "Brackwater's square, split over the Brood's rift", landmark="the rift"),
           AreaIdentity("docks", "the quay, the refugees and Gorm's barge"),
           AreaIdentity("pool", "the Brack Pool, red with firelight", landmark="the pool"),
           AreaIdentity("lane", "the ferry lane, burnt"), AreaIdentity("mill", "the old mill, burnt"),
           AreaIdentity("camp", "the far clearing downstream"), AreaIdentity("reeds", "the reed bank"),
           AreaIdentity("glade", "the glade north-east of the square")],
    buildings=BLDG)

m = Spec(NAME, summary="The Last Bell", description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"The Hollow Choir, act 10. Generated by Claude.", author="vdystopia (generated by Claude)", version="1",
         date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [150, 104, 84]             # a town on fire: a low red light
q = QuestBook(NAME)
hc = HcScript(NAME)

REGIONS = dict(
    oak=dict(forest="dusk", ground=("GrassSparse2", "DirtLight2", "GrassNorm")),
    dusk=dict(forest="dusk", ground=("GrassSparse2", "DirtLight2", "GrassNorm")),
    old=dict(forest="ancient", ground=("GrassSparse2", "DirtLight2", "GrassNorm")),
)

# ---- 1-4. the plan: Brackwater's land, river, bridges, quay, square and buildings, as in act 1 -------------------------
FURNISH = int(os.environ.get("HC_FURNISH", "0")) or None
P = HB.plan(m, ID, wall_of=lambda r: FORESTS[REGIONS[r]["forest"]]["wall"], floor_of=lambda r: REGIONS[r]["ground"][0],
            seed=SEED, furnish_seed=FURNISH)
land, sm, placed, rng = P.land, P.sm, P.placed, P.rng
C = P.C
vc = C["town"]
gate_halves, gate_pts, gate_sq = P.gate
pop, B = sm.pop, sm.B
person, room_of, free_px = sm.person, sm.room_of, sm.free_px
vx, vy = square_px(*vc)

# ---- 5. the town on fire ----------------------------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Bargeman's Rest\nBeds, eel pie and river ale", "Sign"),
                     store=q.text("The River Store\nRope, lamps, arms and stores for the road", "Sign"),
                     smithy=q.text("Ashforge\nDoran Ashforge, smith", "Sign"),
                     apothecary=q.text("Fell's Herbs\nShut. Gone to the shrine. - W.", "Sign"),
                     village_chapel=q.text("The Bell Shrine\nThe first of the five bells", "Sign"))
for bid, b in placed:
    role = BUILDINGS[bid.role]
    for sc in role["scenes"]: vil.scene(b, sc, role=bid.role)
for r_ in REGIONS:
    g_ = REGIONS[r_]["ground"]
    land.ground_variety(m, base=g_[0], sparse=g_[1], dense=g_[2], clear=3, region=r_)

# the rift: where the well stood the square has split over a pit of fire, its lip of black volcanic rock
rift_c = (vc[0] + 0.5, vc[1] - 0.5)
rift_tiles, lip_tiles = [], []
for i in range(int(vc[0]) - 5, int(vc[0]) + 6):
    for j in range(int(vc[1]) - 5, int(vc[1]) + 6):
        d_ = math.hypot(i + 0.5 - rift_c[0], j - 0.5 - rift_c[1]) * (1 + 0.12 * math.sin(i * 1.7 + j * 0.9))
        t_ = square_tile(i, j)
        if t_ not in m.floor: continue
        if d_ <= 1.7: m.floor[t_] = "Lava"; rift_tiles.append(t_)
        elif d_ <= 3.3: m.floor[t_] = "VolcanicCraggy"; lip_tiles.append(t_)
m.blending("Lava", 7, "BlendEdge"); m.blending("VolcanicCraggy", 6, "BlendEdge")
for t_ in rift_tiles:                       # the lip walled off from the fire, as Westwood fences its lava
    if any(m.floor.get((t_[0] + a, t_[1] + b)) != "Lava" for a, b in ((1, 1), (1, -1), (-1, 1), (-1, -1))):
        m.wall(t_[0], t_[1], "InvisibleWallSet")
land.taken |= {(int(vc[0]) + a, int(vc[1]) + 1 + b) for a in range(-4, 5) for b in range(-4, 5)}
rift_xy = square_px(*rift_c)


def lamp(si, sj):
    x, y = square_px(si, sj)
    m.obj_px("StreetLampOrnate3", x, y); m.obj_px("StreetLampOrnate3Shadow", x - 15, y + 21)


for du, dv in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
    lamp(rift_c[0] + du * 4.6, rift_c[1] + dv * 4.6)

# fires: the houses that burnt are shut for good, flames along their walls and in their rooms; the rest scorched
BURNT = ("barracks", "home", "cottage", "mill", "apothecary")
doors_sq = [px_square(*d.px) for _, b in placed for d in b.entrances]
fire_xy = []


def flame_at(x, y, kind=None):
    if any(math.hypot(x - a, y - b) < 44 for a, b in fire_xy): return False
    s_ = px_square(x, y)
    if s_ not in land.squares or s_ in land.roads or s_ in land.plaza or s_ in land.water: return False
    if any(math.hypot(s_[0] - d[0], s_[1] - d[1]) < 3.5 for d in doors_sq): return False
    if any((int(x // CELL) + a, int(y // CELL) + b) in m.wallmap for a in (-1, 0, 1) for b in (-1, 0, 1)): return False
    m.obj_px(kind or rng.choice(("MediumFlame", "SmallFlame", "Flame", "SmallFlame", "LargeFlame")), x, y)
    fire_xy.append((x, y))
    return True


sealed = []
for k_, (bid, b) in enumerate(placed):
    if bid.role not in BURNT: continue
    sealed += sm.seal_entrance(b, f"Burnt{k_ + 1}_")
    for room in b.rooms:                     # the rooms burn: flames on their floors, out of reach behind shut doors
        tiles = sorted(room.tiles)
        for t_ in rng.sample(tiles, min(len(tiles), 3)):
            x_, y_ = (t_[0] + 1) * CELL, (t_[1] + 1) * CELL
            if not any((t_[0] + a, t_[1] + b2) in m.wallmap for a in (-1, 0, 1) for b2 in (-1, 0, 1)):
                m.obj_px(rng.choice(("MediumFlame", "Flame", "SmallFlame")), x_, y_)
    foot = set(_squares_of(b.footprint))
    ring_ = sorted({(i + a, j + c) for i, j in foot for a in (-2, -1, 0, 1, 2) for c in (-2, -1, 0, 1, 2)} - foot)
    n_ = 0
    for s_ in rng.sample(ring_, len(ring_)):
        if n_ >= 6: break
        if flame_at(*square_px(s_[0] + 0.5, s_[1] - 0.5)): n_ += 1
# the rift's lip burns
for k_ in range(10):
    a_ = k_ * 2 * math.pi / 10 + 0.2
    x_, y_ = square_px(rift_c[0] + 2.4 * math.cos(a_), rift_c[1] + 2.4 * math.sin(a_))
    m.obj_px(("Flame", "SmallFlame", "MediumFlame")[k_ % 3], x_, y_)
    fire_xy.append((x_, y_))
# the fires' glow
presets = json.load(open(os.path.join(HERE, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]


def preset(family):
    ps = [p for p in presets if p["family"] == family and p["animation"] == "steady" and p["intensity_class"] == "full"] or \
         [p for p in presets if p["family"] == family and p["intensity_class"] == "full"]
    return max(ps, key=lambda p: p["weighted_share"])["xfer"]


glows = []
for x_, y_ in fire_xy:
    if all(math.hypot(x_ - a, y_ - b) > 260 for a, b in glows):
        m.obj_px("ColorLight", x_, y_ - 6, xfer=dict(preset("orange")))
        glows.append((x_, y_))
m.obj_px("ColorLight", rift_xy[0], rift_xy[1] - 6, xfer=dict(preset("red")))

# ---- 6. the story's places ------------------------------------------------------------------------------------------
south_c, camp_c, mill_c, lane_c, reeds_c, docks_c, gate_c, mire_c, glade_c, pool_c = (
    C[k] for k in ("south", "camp", "mill", "lane", "reeds", "docks", "gate", "mire", "glade", "pool"))
shrine_b = sm.by_role["village_chapel"]
nave = room_of("village_chapel", "chapel")
crypt = room_of("village_chapel", "crypt")
assert nave and crypt, "the Bell Shrine was not built with its nave and crypt"
ncells = {(x + a, y + b) for x, y in nave.tiles for a in (-1, 0, 1) for b in (-1, 0, 1)}
altar = next((o for o in m.d["objects"] if "Altar" in o.get("type", "") and (int(o["x"] // CELL), int(o["y"] // CELL))
              in ncells), None)
nx_, ny_ = (sum(x for x, _ in nave.tiles) / len(nave.tiles) + 1) * CELL, (sum(y for _, y in nave.tiles) / len(nave.tiles) + 1) * CELL
bell_xy = (altar["x"], altar["y"]) if altar else free_px(nave)
# the bell's light over the altar, dark until the bells ring
m.obj_px("ColorLight", bell_xy[0], bell_xy[1] - 6, xfer=dict(preset("white")), scr="BellLight")
# the reliquary in the crypt: the founders' cracked stones, the first castings that failed
CRACKED = "Diamond"
rx_, ry_ = free_px(crypt, clear=32)
m.obj_px(CRACKED, rx_, ry_, scr="CrackedStones")          # spilled from the reliquary's broken casket
# Wenna's basket of potions by the altar: a chest in the nave
wx_, wy_ = free_px(nave, prefer=(bell_xy[0] + (nx_ - bell_xy[0]) * 0.5 + 40, bell_xy[1] + (ny_ - bell_xy[1]) * 0.5),
                   clear=34)
m.obj_px("Chest2", wx_, wy_, scr="WennasChest", items=["RedPotion", "RedPotion", "RedPotion", "BluePotion",
                                                       "BluePotion", "CurePoisonPotion"])
# the closing sign, in the nave by the door: it appears when the bells have rung and the Matriarch is dead
sdx, sdy = shrine_b.entrances[0].px
sgn_ = free_px(nave, prefer=((sdx + nx_) / 2, (sdy + ny_) / 2), clear=34)
CLOSING = q.text("THE LAST BELL\nHere the five bells were rung again.\nThe stones were carried home from the Mirewood, "
                 "the Greycrag deep, Frosthollow, the Marches, the Barrow, the Emberforge and the Spire.\nThe Brood "
                 "sleeps. Brackwater stands.", "Sign")
m.obj_px("Sign1", *sgn_, scr="ClosingSign", xfer={"Text": CLOSING})
# caches in the woods, off the ways
caches = []
for near_, loot_, stump_ in ((camp_c, [("Gold", {"Amount": 50}), "RedPotion", "BluePotion"], False),
                             (glade_c, [("Gold", {"Amount": 40}), "RedPotion", "CurePoisonPotion"], True)):
    s_ = sm.hidden_spot(near_, r=(8, 15))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
# the overturned carts of those who fled, on the docks road and at the south landing
wrecks = []
for c_, to_ in ((docks_c, vc), (south_c, gate_c)):
    rd_ = sm.road_near(c_)
    ws_ = min((s for s in land.squares if s not in land.roads and s not in land.taken and s not in land.water and
               1.0 <= min(math.hypot(s[0] - r[0], s[1] - r[1]) for r in land.roads if abs(r[0] - rd_[0]) + abs(r[1] - rd_[1]) < 10) <= 2.5),
              key=lambda s: math.hypot(s[0] - rd_[0], s[1] - rd_[1]), default=None)
    if ws_:
        wrecks.append(camps.wagon_wreck(m, rng, land, (ws_[0] + 0.5, ws_[1] - 0.5),
                                        math.atan2(to_[1] - c_[1], to_[0] - c_[0])))
        flame_at(*square_px(ws_[0] + 0.5, ws_[1] - 0.5), "MediumFlame")

# ---- 7. planting (thinner: the woods have burnt), the start ------------------------------------------------------------
keep = set()
for bid, b in placed:
    for d in b.entrances:
        di, dj = px_square(*d.px)
        keep |= {(di + a, dj + b2) for a in range(-2, 3) for b2 in range(-2, 3)}
vil.ground_bits(1.0)
planter = Planter(m, rng, land, "dusk", keep_clear=keep | P.lane, settled=("town", "docks"),
                  forest_of=lambda s: REGIONS[P.section(land.region_of(s))]["forest"])
n_trees, n_small = planter.plant_all(groves=2, profile=TOWN_PLANTING)
piles = planter.rock_piles(max(6, len(land.squares) // 700))
vignettes = planter.forest_floor(max(4, len(land.squares) // 900))
P.ww.finish()
# the player comes home by the river road, beyond the River Gate (where act 1's exit was)
edge_ = land.edge_distance()
st_sq = min(land.roads, key=lambda s: math.hypot(s[0] - mire_c[0], s[1] - mire_c[1]) + 0.2 * edge_.get(s, 0))
start_xy = square_px(st_sq[0] + 0.5, st_sq[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)

# ---- 8. the people --------------------------------------------------------------------------------------------------
mods = Mods(m, pop)
SEAL, KNIFE, RELIQ, OATH = token("WATCH_SEAL"), token("RUSK_KNIFE"), token("RELIQUARY"), token("VESS_OATH")
LETTER, STAR, CHARM, FREED = token("DORAN_LETTER"), token("STARSTEEL"), token("WENNA_ASK"), token("TAM_FREED")
STONE, VERSE = token("SPIRIT_STONE"), token("VERSE_STONE")
# Hob, the wounded watchman at the River Gate, on its town side
gq_ = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
sx_, sy_ = square_px(*south_c)
gdx, gdy = sx_ - gq_[0], sy_ - gq_[1]
gl = math.hypot(gdx, gdy) or 1
hob_xy = (gq_[0] + 70 * gdx / gl + 26, gq_[1] + 70 * gdy / gl)
person("Con02a", "Mayor's_Guard", *hob_xy, "Hob", face=start_xy)
# Rusk (RUSK_KNIFE) beside Hob; his crew at the south landing
rk_ = (gq_[0] + 70 * gdx / gl - 30, gq_[1] + 70 * gdy / gl + 20)
cast_person(sm, "Rusk", *rk_, face=start_xy)
town_bank, far_bank = HB.bridge_ends(P, 0)
fb_sq = px_square(*far_bank)
crew = []
for k_, donor_ in enumerate((("War01A", "Jesse"), ("War01A", "Daniel"), ("War01A", "Eric"))):
    ang = math.atan2(south_c[1] - fb_sq[1], south_c[0] - fb_sq[0]) + (k_ - 1) * 0.8
    x_, y_ = square_px(fb_sq[0] + 0.5 + 4.2 * math.cos(ang), fb_sq[1] - 0.5 + 4.2 * math.sin(ang))
    person(donor_[0], donor_[1], x_, y_, f"RuskMan{k_ + 1}", face=town_bank)
    crew.append(f"RuskMan{k_ + 1}")
# Captain Ilsa on the square before the shrine; her watch (WATCH_SEAL) beside her
sh_door = sm.outside_door(building=shrine_b) or (vx, vy)
il_ = sm.doorside("village_chapel", toward=rift_xy) or (sh_door[0] + 50, sh_door[1])
cast_person(sm, "Ilsa", il_[0], il_[1], face=rift_xy)
watch = []
watch_home = ((sh_door[0] + rift_xy[0]) / 2, (sh_door[1] + rift_xy[1]) / 2)     # between the shrine's door and the rift
for k_, donor_ in enumerate(("Contest_Guard", "IxGuard2")):
    a_ = math.atan2(sh_door[1] - rift_xy[1], sh_door[0] - rift_xy[0]) + (0.7 if k_ else -0.7)
    x_, y_ = rift_xy[0] + 190 * math.cos(a_), rift_xy[1] + 190 * math.sin(a_)
    person("Con02a", donor_, x_, y_, f"Watch{k_ + 1}", face=rift_xy)
    watch.append(f"Watch{k_ + 1}")
# Edric by the altar; Tam (TAM_FREED) beside him; Wenna by her potions
ex_, ey_ = sm.stand_px(nave)
cast_person(sm, "Edric", ex_, ey_, face=(nx_, ny_))
tx_, ty_ = sm.stand_px(nave, k=1)
cast_person(sm, "Tam", tx_, ty_, face=(nx_, ny_))
wn_ = free_px(nave, prefer=(wx_ + 40, wy_ + 30), clear=34)
cast_person(sm, "Wenna", wn_[0], wn_[1], face=(nx_, ny_))
# Doran at his forge; the forge (S1) with his journeyman; Doran's own hammer in his strongroom, both tiers
smithy = room_of("smithy", "smithy")
store = room_of("smithy", "storeroom")
assert smithy and store, "the smithy was not built with its forge and stock room"
smithy_b = sm.by_role["smithy"]
forge = HB.place_forge(m, mods, sm, smithy, store)
st_spots = [((x + 1) * CELL, (y + 1) * CELL) for x, y in sorted(store.tiles)
            if not any((x + a, y + b) in m.wallmap for a in (-1, 0, 1) for b in (-1, 0, 1))]
mods.weapon("W3", *st_spots[-1], tier=3, name="DoranHammer")
mods.weapon("W3", *st_spots[-2], tier=1, name="OldHammer")
dr_ = sm.doorside("smithy", toward=(vx, vy)) or (vx + 60, vy)
cast_person(sm, "Doran", dr_[0], dr_[1], face=(vx, vy))
# Gorm on the quay with the refugees waiting for his barge
dock = P.docks[0] if P.docks else None
if dock:
    du_, dv_ = dock["start"]
    root = ((du_ + dv_) / 2 * CELL, (du_ - dv_) / 2 * CELL)
else:
    root = square_px(docks_c[0] + 0.5, docks_c[1] - 0.5)
dx_, dy_ = square_px(*docks_c)
dl_ = math.hypot(dx_ - root[0], dy_ - root[1]) or 1
ux_, uy_ = (dx_ - root[0]) / dl_, (dy_ - root[1]) / dl_
gorm_xy = (root[0] + ux_ * 46 + uy_ * 52, root[1] + uy_ * 46 - ux_ * 52)
person("Con03A", "Kenneth", *gorm_xy, "Gorm", face=root)
REFUGEES = [("Con02a", "Tanya"), ("Con02a", "Clyde"), ("Con02a", "Julie"), ("Con03A", "Millard"),
            ("Con02a", "Jacob"), ("Con07B", "Kayla")]
REF_NAMES = ["Agna", "Colm", "Brisa", "Oswin", "Tobin", "Elsbet"]
refugees = []
for k_, ((donor_, src_), nm_) in enumerate(zip(REFUGEES, REF_NAMES)):
    along_, across_ = (110, 215)[k_ // 3], (-120, 0, 120)[k_ % 3] + (25 if k_ // 3 else -25)
    x_, y_ = root[0] + ux_ * along_ + uy_ * across_, root[1] + uy_ * along_ - ux_ * across_
    if px_square(x_, y_) not in land.squares or px_square(x_, y_) in land.water:
        x_, y_ = root[0] + ux_ * (along_ + 60), root[1] + uy_ * (along_ + 60)
    person(donor_, src_, x_, y_, nm_, face=root)
    refugees.append(nm_)
# two who flee from the square toward the quay as the map begins
FLEE = [("Con06a", "Townsman2", "Godric"), ("Con07B", "Dorian", "Maud")]
fleeing = []
for k_, (donor_, src_, nm_) in enumerate(FLEE):
    a_ = math.atan2(dy_ - vy, dx_ - vx) + (0.5 if k_ else -0.5)
    fx_, fy_ = vx + 300 * math.cos(a_), vy + 300 * math.sin(a_)
    s_ = px_square(fx_, fy_)
    if s_ not in land.squares or s_ in land.taken_strict:
        fx_, fy_ = square_px(*sm.road_near(s_))
    person(donor_, src_, fx_, fy_, nm_, face=(dx_, dy_))
    fleeing.append((nm_, sm.journey(nm_, f"{nm_}Flee", (root[0] + ux_ * 200 + uy_ * (k_ * 60 - 30),
                                                        root[1] + uy_ * 200 - ux_ * (k_ * 60 - 30)), look=root)))
# Vess (VESS_OATH): by the shrine at the end, and gone again
vs_ = sm.doorside("village_chapel", toward=(nx_ * 2 - sh_door[0], ny_ * 2 - sh_door[1])) or (sh_door[0] - 60, sh_door[1])
person(*CAST["Vess"]["donor"], vs_[0], vs_[1], "Vess", face=rift_xy)
# shopkeepers: the inn and the river store still sell
WARES = {"inn": [(6, "Bread"), (5, "Meat"), (4, "Cider"), (3, "RedApple"), (4, "RedPotion")],
         "store": [(4, "RedPotion"), (2, "BluePotion"), (2, "CurePoisonPotion"), (3, "Quiver"), (1, "Longsword"),
                   (1, "BattleAxe"), (1, "SteelShield"), (1, "ChainTunic"), (1, "ChainLeggings"), (1, "SteelHelm")]}
GREET = {"inn": q.text("Get away, you brute, before I call the watch! ...Oh. It's you. In, quick, and shut the door "
                       "behind you!", "Shop"),
         "store": q.text("Sorry, friend, my shelves are half bare. Fire makes folk grab whatever they can carry. Heh, "
                         "heh... take what's left.", "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"store": "ShopkeeperWarriorsRealm"})

# ---- 9. the fights ----------------------------------------------------------------------------------------------------
brood = []          # every creature of the Brood in the town (the true peal burns away what is left)


def foe(t, x, y, name, face, action="guard", group=None):
    pop.creature(t, x, y, action=action, face=face, scr=name, aggr=0.83)
    brood.append(name)
    if group is not None: group.append(name)
    return name


def ring_px(c_px, r, n, a0=0.0):
    return [(c_px[0] + r * math.cos(a0 + k * 2 * math.pi / n), c_px[1] + r * math.sin(a0 + k * 2 * math.pi / n))
            for k in range(n)]


# the south landing: imps and an ember demon on the Brood's first foothold over the river
south_px = square_px(*south_c)
g_south = []
for k_, (x_, y_) in enumerate(ring_px(south_px, 120, 4, 0.3)):
    foe(("Imp", "EmberDemon", "Imp", "FireSprite")[k_], x_, y_, f"SouthBrood{k_ + 1}", gq_, group=g_south)
# the town bridge's north end: a brood-mother (M4)
tb_ = (town_bank[0] + (vx - town_bank[0]) * 0.18, town_bank[1] + (vy - town_bank[1]) * 0.18)
mods.monster("M4", *tb_, name="BroodMother1", hp=380, wait=230, face=far_bank)
brood.append("BroodMother1")
# the quay: a brood-mother among the barrels, imps about the refugees
quay_xy = (root[0] + ux_ * 390, root[1] + uy_ * 390)
mods.monster("M4", *quay_xy, name="BroodMother2", hp=380, wait=230, face=root)
brood.append("BroodMother2")
g_quay = ["BroodMother2"]
for k_, (x_, y_) in enumerate(ring_px(quay_xy, 110, 3, 0.9)):
    foe("Imp", x_, y_, f"QuayImp{k_ + 1}", root, group=g_quay)
# the square: imps and fire sprites round the rift
g_square = []
for k_, (x_, y_) in enumerate(ring_px(rift_xy, 150, 5, 0.5)):
    foe(("Imp", "FireSprite", "Imp", "Imp", "FireSprite")[k_], x_, y_, f"RiftImp{k_ + 1}", rift_xy, group=g_square)
# Doran's forge yard: two ember demons by the smithy's back wall
sb_c = (sum(x for x, _ in store.tiles) / len(store.tiles) * CELL, sum(y for _, y in store.tiles) / len(store.tiles) * CELL)
sdoor_ = sm.outside_door(building=smithy_b) or (vx, vy)
g_yard = []
for k_ in range(2):
    a_ = math.atan2(sdoor_[1] - sb_c[1], sdoor_[0] - sb_c[0]) + math.pi / 2 * (1 if k_ else -1)
    for r_ in (150, 180, 210, 240):
        x_, y_ = sdoor_[0] + r_ * math.cos(a_), sdoor_[1] + r_ * math.sin(a_)
        s_ = px_square(x_, y_)
        if s_ in land.squares and s_ not in land.taken_strict and s_ not in land.water: break
    foe("EmberDemon", x_, y_, f"YardDemon{k_ + 1}", sdoor_, group=g_yard)
# the reliquary: a brood-mother broke into the shrine's crypt
cx_, cy_ = free_px(crypt, prefer=(rx_ + 60, ry_ + 60), clear=34)
mods.monster("M4", cx_, cy_, name="BroodMother3", hp=380, wait=200, face=(rx_, ry_))
brood.append("BroodMother3")
# the wave the Matriarch calls when the bells ring false, and the reliquary's wave: hidden until then
g_wave = []
for k_, (x_, y_) in enumerate(ring_px(rift_xy, 250, 5, 0.1)):
    foe(("EmberDemon", "Imp", "EmberDemon", "Imp", "Imp")[k_], x_, y_, f"Wave{k_ + 1}", rift_xy, action="idle",
        group=g_wave)
g_reliq = []
for k_, (x_, y_) in enumerate(ring_px(rift_xy, 210, 4, 0.9)):
    foe("Imp", x_, y_, f"BoneWave{k_ + 1}", rift_xy, action="idle", group=g_reliq)
# the Ember Matriarch: hidden in the rift until the bells ring (kit/mods M4 registered when she rises, as act 8 does)
far_from_shrine = (rift_xy[0] - (sh_door[0] - rift_xy[0]) * 0.45, rift_xy[1] - (sh_door[1] - rift_xy[1]) * 0.45)
pop.creature("EmberDemon", *far_from_shrine, action="idle", scr="Matriarch", aggr=0.83, face=sh_door, spread=False)
# the scorched woods' own creatures: imps and sprites the Brood loosed, bats driven out by the smoke
sm.wild({"Imp": 4, "FireSprite": 2, "Bat": 4, "EmberDemon": 1}, away_from=vc, per100=0.5, gap=7, min_away=30,
        avoid=(south_c, gate_c, mire_c, docks_c, px_square(*far_bank), px_square(*town_bank), gate_sq,
               px_square(*start_xy), px_square(*quay_xy)))

story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]] + \
           [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)

# ---- 10. the story ----------------------------------------------------------------------------------------------------
q.start([A.disable("Matriarch"), A.disable("BellLight"), A.disable("ClosingSign"), A.disable("Rusk"),
         A.disable("Vess"), A.disable("Tam")] + [A.disable(n) for n in crew + watch + g_wave + g_reliq] +
        [A.print("Smoke rolls down the river road. Ahead, beyond the River Gate, Brackwater is burning."),
         q.journal("Go home to Brackwater and find Brother Edric at the Bell Shrine.", HINT)])

# what the player carries decides who holds the town
q.when_true(has("RUSK_KNIFE"), [A.enable("Rusk"), A.flag("rusk_holds"), q.note("NOTE: Rusk kept his promise. His crew "
                                                                                 "holds the south landing.")])
q.when_true(has("WATCH_SEAL"), [A.flag("watch_holds"), q.note("NOTE: Captain Ilsa and the watch hold the square.")])
q.when_true(has("TAM_FREED"), [A.enable("Tam"), A.flag("tam_here")])
hc.ally("RuskMan1", g_south, follow=False, home=south_px, hold=340, dmg=8)
hc.ally("RuskMan2", g_south, follow=False, home=south_px, hold=340, dmg=8)
hc.ally("RuskMan3", g_south, follow=False, home=south_px, hold=340, dmg=8)
hc.on_flag("rusk_holds", hc.allies_go(*crew))
for n_ in watch:
    hc.ally(n_, g_square + g_wave + g_reliq, follow=False, home=watch_home, hold=380, dmg=9)
hc.on_flag("watch_holds", hc.allies_go(*watch))
hc.on_flag("matriarch_dead", hc.allies_release(*(crew + watch)))       # the fight is over: they are their own again

# the stones, set in the bell one at a time (counted: kit/campaign SPIRIT_STONE), the verses read the same way; each
# chain is declared last step first, so one step fires each half second (the stone taken is gone before the next)
ORD = ("first", "second", "third", "fourth", "fifth")
for k_ in range(5, 0, -1):
    q.near(*bell_xy, 120, [A.take(STONE), A.stage("stones", k_),
                           A.print(f"You set the {ORD[k_ - 1]} Spirit Stone in the bell. It hums under your hand.")],
           when=q.at("stones", k_ - 1, has=STONE))
for k_ in range(3, 0, -1):
    q.near(*bell_xy, 140, [A.take(VERSE), A.stage("verses", k_),
                           A.print(f"Brother Edric takes the {ORD[k_ - 1]} verse and reads it under his breath.")],
           when=q.at("verses", k_ - 1, has=VERSE))
q.when_true(q.at("stones", 5), [A.flag("stones_true"), A.flag("bell_full")])
q.when_true(q.at("verses", 3), [A.flag("verses_ok")])
q.when_true(q.at("verses", 2, flag="tam_here"), [A.flag("verses_ok"), A.flag("tam_reads")])
q.on_pickup(CRACKED, [q.journal("Bring the founders' cracked stones to Brother Edric.")], when=q.when(not_="bell_full"))
q.on_death("Matriarch", [A.flag("matriarch_dead"), A.enable("ClosingSign"),
                         A.print("The Ember Matriarch shrieks and falls back into the rift. Over the river the five "
                                 "bells ring out together, and the Brood burns away to ash."),
                         q.done("Kill the Ember Matriarch in the square."),
                         q.journal("Brackwater stands. Speak to your friends, and read the sign in the Bell Shrine.",
                                   HINT)])
# the endings in the journal, by what the player carried home
for tok_, text_ in (("WATCH_SEAL", "NOTE: Captain Ilsa and the watch held the square to the end."),
                    ("RUSK_KNIFE", "NOTE: Rusk's crew held the south landing. Rusk says he will turn honest."),
                    ("TAM_FREED", "NOTE: Tam came home, and read the old words beside Brother Edric."),
                    ("VESS_OATH", "NOTE: Vess kept her oath. She was there at the end, and gone again.")):
    q.when_true(q.when(has=token(tok_), flag="matriarch_dead"), [q.note(text_)])

# the bells ring: the Matriarch rises from the rift. A true peal (five true stones, the verses read) cuts off the Brood:
# every brood-creature left in the town burns away, and she rises alone. Otherwise her wave comes with her.
burn = [f'if o := ns.Object("{n}"); o != nil && o.CurrentHealth() > 0 {{ o.Damage(nil, 9999, 0) }}'
        for n in brood if n not in g_wave + g_reliq]
hc.on_flag("bells_rung", hc.rise("Matriarch", *far_from_shrine),
           [f'ModBoss("embermother", "Matriarch", "The Ember Matriarch", {FOES["Matriarch"]["hp"]}, 0, 0)'])
hc.on_flag("true_peal", burn)
ring_true = [A.flag("bells_rung"), A.flag("true_peal"), A.enable("BellLight"),
             A.print("Edric reads the last verse and the bell rings true. Far off, four more bells answer it. All "
                     "through the town the Brood shrieks and burns... and in the square, the rift heaves."),
             q.done("Set the five Spirit Stones in the Bell Shrine's bell."),
             q.journal("Kill the Ember Matriarch in the square.")]
ring_false = [A.flag("bells_rung"), A.enable("BellLight")] + [A.hunt(n) for n in g_wave] + [
    A.print("The bell rings, but not true. The rift heaves, and the Brood pours out of it with its mother."),
    q.done("Set the five Spirit Stones in the Bell Shrine's bell."),
    q.journal("Kill the Ember Matriarch in the square.")]
q.when_true(q.when(has=RELIQ, flag="bells_rung"), [A.hunt(n) for n in g_reliq] + [
    A.print("Something in your pack screams. The Choir's reliquary is calling the Brood to you!")])

# Brother Edric: the Last Bell
q.talker("Edric", [
    q.say("You still carry the Choir's rod of yellowed bone. The bells ring, child, but that thing will find another voice "
          "to sing for it. Break it. Promise me you'll break it.",
          when=q.when(has=RELIQ, flag="matriarch_dead"), who="Edric", mood="Grave and quiet, a last warning."),
    q.say("Hear them? All five at once, for the first time in a hundred years! Brackwater stands. Go and see who is "
          "waiting for you, my friend. And thank you.", when=q.when(flag="matriarch_dead"), who="Edric"),
    q.say("She's rising! Go to the square! The bell can do no more!", when=q.when(flag="bells_rung"), who="Edric"),
    q.say("You're back. Good. The last thing I'll ask of you is the hardest. / Something terrible is happening under "
          "Brackwater. At sundown the ground split open beneath the square, and the Brood is climbing out of it. / "
          "Their mother is waking. Only the bells, rung together, can send her down again. You can help me do it. / "
          "Set the Spirit Stones in the bell, here at the altar, one by one. Give me the verses you carried, if you "
          "found them. / Then speak to me, quickly, before she wakes in full.",
          when=q.when(not_="edric_told"), do=[A.flag("edric_told"), A.stage("main", 1),
              q.journal("Set the five Spirit Stones in the Bell Shrine's bell.")], who="Edric"),
    q.say("That thing in your pack! The Choir's reliquary, that rod of yellowed bone! It sings to her even now. Give "
          "it to me, and I'll break it on the bell's lip before we ring. Will you?",
          when=q.when(has=RELIQ, not_="reliq_kept"), ask=True,
          do=[A.take(RELIQ), A.flag("reliq_broken"),
              A.print("Edric smashes the bone reliquary against the bell. It shrieks once, and is dust.")],
          else_=[A.flag("reliq_kept"), q.tell("Edric", "Then keep it close, and pray she doesn't hear it.")],
          who="Edric"),
    q.say("Five true stones, and every verse read! Stand back, now. Let's wake the bells.",
          when=q.at("stones", 5, flag="verses_ok"), do=ring_true, who="Edric", mood="Fervent, rising."),
    q.say("Five true stones, but not all the words. I'll read what I remember. It will ring... but not true. Be "
          "ready!", when=q.at("stones", 5), do=ring_false, who="Edric"),
    q.say("The cracked stones! They'll make it sing, if not well. I'll read what verses I have. Stand ready, child. "
          "She'll come with all her brood.",
          when=q.when(has=CRACKED, not_="bell_full"),
          do=[A.take(CRACKED), A.flag("bell_full")] + ring_false, who="Edric"),
    q.say("Set the stones in the bell, here at the altar. Every one you carry.", when=q.when(has=STONE),
          who="Edric"),
    q.say("Not all five? Then some were lost on your road, in the Mirewood, the Greycrag deep, Frosthollow, the "
          "Marches or the Barrow. / The founders kept their cracked stones in the reliquary, in the crypt below us. "
          "They'll make the bell ring, if not true. But one of the Brood's mothers has broken in. / Bring them to me.",
          when=q.when(flag="edric_told"),
          do=[A.flag("edric_crypt"), q.journal("Bring the cracked stones from the reliquary in the crypt below the "
                                               "shrine.")], who="Edric")],
    voice=voice("Edric"), title=CAST["Edric"]["title"])

# Tam (TAM_FREED): beside Edric, reading the third verse
q.talker("Tam", [
    q.say("We did it! I read it right, didn't I? Wenna says I read it right.", when=q.when(flag="matriarch_dead"),
          who="Tam"),
    q.say("Ready. Thanks for coming. Let's ring it!", when=q.when(flag="tam_reads"), who="Tam"),
    q.say("You came back! The Choir made me read the old bells' words for them. I know them by heart now. If "
          "you've two of the verses, I can give Brother Edric the third!", who="Tam", mood="Eager, breathless.")],
    voice=voice("Tam"), title=CAST["Tam"]["title"])

# Wenna: her potions in the shrine; Tam home, or still lost
q.talker("Wenna", [
    q.say("He's home. You brought my brother home, and you saved the town besides. I'll never be able to thank you "
          "enough. Here, the last of my good potions.",
          when=q.when(flag="matriarch_dead", has=FREED, not_="wenna_paid"),
          do=[A.flag("wenna_paid"), A.give("RedPotion"), A.give("BluePotion")], who="Wenna"),
    q.say("The bells! I never thought I'd hear them again. And Tam... you still carry my green stone. Keep it. "
          "Perhaps it will find him yet.", when=q.when(flag="matriarch_dead", has=CHARM), who="Wenna"),
    q.say("The bells! I never thought I'd hear them again.", when=q.when(flag="matriarch_dead"), who="Wenna"),
    q.say("Tam's here! He's reading the bells' old words for Brother Edric like he was born to it! Take what you need "
          "from the chest. Every potion I could carry out before the roof caught is in it.",
          when=q.when(flag="tam_here"), who="Wenna"),
    q.say("Hello again. I suppose you've come for the potions. / There's a chest of them by the altar, every one I "
          "could carry out before the roof caught. / Be careful out there. Tam... if you ever hear word of Tam, "
          "tell me.", who="Wenna")],
    voice=voice("Wenna"), title=CAST["Wenna"]["title"])

# Doran: the yard, and the hammer (the Starsteel Blade's end)
q.on_all_dead(g_yard, [A.flag("yard_clear"), A.print("The last ember demon in Doran's yard gutters out.")])
hc.on_flag("hammer_best", hc.hand_over("DoranHammer", "Doran"))
hc.on_flag("hammer_old", hc.hand_over("OldHammer", "Doran"))
q.talker("Doran", [
    q.say("Swing it hard. It knows the way.", when=q.when(flag="doran_paid"), who="Doran"),
    q.say("Excellent! The yard's clear! / And you've still the starsteel in your pack? Never found a forge hot enough, "
          "eh? No matter. Take my hammer. It's the best thing I ever made. Good luck!",
          when=q.when(flag=q.dead(*g_yard), has=STAR, not_="doran_paid"),
          do=[A.flag("doran_paid"), A.flag("hammer_best")], who="Doran"),
    q.say("Excellent! The yard's clear! / And is that the blade? Starsteel, worked in the founders' own fire! My "
          "old medallion got you there... Then take my hammer, the best thing I ever made. Good luck!",
          when=q.when(flag=q.dead(*g_yard), has=LETTER, not_="doran_paid"),
          do=[A.flag("doran_paid"), A.flag("hammer_best")], who="Doran", mood="Gruff, moved, proud."),
    q.say("Excellent! The yard's clear! / Here's my old hammer. It's no starsteel, but it hits like a mule. Good "
          "luck!", when=q.when(flag=q.dead(*g_yard), not_="doran_paid"),
          do=[A.flag("doran_paid"), A.flag("hammer_old")], who="Doran"),
    q.say("Have faith! Two fire-imps are nothing to you now. Come back when they're done for.",
          when=q.at("yard", 1), who="Doran"),
    q.say("Good! You're home! The Brood's got into my yard, right outside the forge. Two of those fire-demons, "
          "eating my coal. / Kill them, and when you come back I'll have something for you. / The forge still "
          "burns, mind. My journeyman will work a blade for you, same as always.",
          do=[A.stage("yard", 1), q.journal("Kill the ember demons in Doran's forge yard.")], who="Doran")],
    voice=voice("Doran"), title=CAST["Doran"]["title"])

# Ilsa: the square
q.talker("Ilsa", [
    q.say("Thank you, friend of the watch! The watch needs a captain who doesn't run, and you're it. The place is "
          "yours, if you'll have it. Take this, as a token of my appreciation!",
          when=q.when(flag="matriarch_dead", has=SEAL, not_="ilsa_paid"),
          do=[A.flag("ilsa_paid"), A.gold(200), A.give("RedPotion")], who="Ilsa"),
    q.say("Thank you, sellsword! Brackwater owes you more than it can ever pay. Take this purse, with the whole "
          "town's thanks!", when=q.when(flag="matriarch_dead", not_="ilsa_paid"),
          do=[A.flag("ilsa_paid"), A.gold(150), A.give("RedPotion")], who="Ilsa"),
    q.say("The bells are rung. Brackwater stands.", when=q.when(flag="ilsa_paid"), who="Ilsa"),
    q.say("We're holding the square while we can. Get to the shrine and ring that bell!",
          when=q.when(flag="watch_holds"), who="Ilsa"),
    q.say("Help me, please! The Brood came up through the square and took my watch, every man! Ring that bell, and "
          "I promise you the town will pay!", who="Ilsa", mood="Desperate, hoarse.")],
    voice=voice("Ilsa"), title=CAST["Ilsa"]["title"])
for n_, (l1, l2) in zip(watch, (("I'd speak to the Captain first... / unless you want to face the Brood alone.",
                                 "Back into the fire, demon! Enjoy it!"),
                                ("Stand with us! The square holds while the Captain stands!",
                                 "Did you hear it? Five bells!"))):
    q.talker(n_, [q.say(l2, when=q.when(flag="matriarch_dead"), who="Watch"), q.say(l1, who="Watch")])
    q.portrait(n_, "Warrior3Pic" if n_ == "Watch1" else "IxGuard2Pic")

# Rusk (RUSK_KNIFE) at the gate
q.talker("Rusk", [
    q.say("What, still here? The bells are rung! I'm going honest after tonight, you'll see. Well... mostly honest.",
          when=q.when(flag="matriarch_dead"), who="Rusk"),
    q.say("Get up that road, friend! Unless you LIKE the smell of burning!", when=q.when(flag="met_rusk"), who="Rusk"),
    q.say("Stand there... it's you! I said I'd pay my debt, and here I am. / My lads hold the landing, and the Brood "
          "won't cross it while they stand. / Go up to the shrine. We'll keep your back.",
          do=[A.flag("met_rusk")], who="Rusk")],
    voice=voice("Rusk"), title=CAST["Rusk"]["title"])
for n_ in crew:
    q.talker(n_, [q.say("Rusk does the talking.", who="RuskMan")], title="Cutthroat")   # as act 9's
    q.portrait(n_, "MalePic11")

# Hob at the River Gate: the hook
q.talker("Hob", [
    q.say("The bells! You did it! The town's ours again!", when=q.when(flag="matriarch_dead"), who="Hob"),
    q.say("Only the brave go up that road tonight! Go on, then!", when=q.when(flag="hob_told"), who="Hob"),
    q.say("Stand right there! Oh, it's you! You came back! The ground split under the square at sundown, and the "
          "Brood climbed out of it! Half the town's burning! / Brother Edric is in the Bell Shrine with the bell. "
          "He's waiting for you!",
          do=[A.flag("hob_told"), q.journal("Find Brother Edric at the Bell Shrine, across the town bridge.")],
          who="Hob", mood="Wounded, breathless, relieved.")])

# the Last Barge: Gorm and the quay
q.on_all_dead(g_quay, [A.flag("quay_clear"), A.print("The quay is clear. The refugees run for Gorm's barge.")] +
              [A.disable(n) for n in refugees])
q.talker("Gorm", q.errand(
    "Gorm", "barge",
    offer="Ohhh, would you look at it! The whole town's burning! My barge can't take a soul on board while those "
          "fire-things hold the quay. Quickly -- clear them off, or the little ones burn with the rest of us! Will you?",
    refusal="Then we'll swim for it, and drown.",
    reminder="Please, I'm begging you. Clear the quay before my barge catches!",
    thanks="The quay is clear! The little ones can board now. Here, my purse and a potion. I'll not need "
           "either downriver.",
    after="You may have saved every child in Brackwater tonight. Well done! Now go! Edric needs you.",
    objective="Clear the Brood from the quay so Gorm's barge can sail.",
    done=q.when(flag=q.dead(*g_quay)),
    reward=[A.gold(100), A.give("RedPotion")]),
    voice={"desc": "A stout river bargeman in his fifties. Gruff, hoarse, carrying voice with a broad Bristol accent. "
                   "Blunt and unhurried.", "seed": 61})

# the refugees on the quay and the two who flee
REF_LINES = [
    "So you've come home! Welcome back! We've a barge to fill and no room to fill it.",
    "Yeeaah! Imps! Imps! Get to the barge!",
    "Fine work with the Choir, I hear! The Captain says you're the bravest soul on the river!",
    "WHAT? The square is... gone?",
    "Brackwater must not fall to the Brood! Fight on, for the bell!",
    "Don't lose heart now, friend. The Brood will burn out before morning!",
]
for n_, l_ in zip(refugees, REF_LINES):
    q.talker(n_, [q.say("The bells! Did you hear the bells? It's over!", when=q.when(flag="matriarch_dead"), who="Folk"),
                  q.say(l_, who="Folk")])
for (n_, jk_), l_ in zip(fleeing, ("No, I won't board while my mother's still up in the town!",
                                   "Hey, who set the river on fire?")):
    q.talker(n_, [q.say("The bells! Did you hear the bells? It's over!", when=q.when(flag="matriarch_dead"), who="Folk"),
                  q.say(l_, who="Folk")])
q.start([A.walk(n_, jk_) for n_, jk_ in fleeing])

# Vess (VESS_OATH): there at the end, and gone again
q.when_true(q.when(has=OATH, flag="matriarch_dead"), [A.enable("Vess")])
hc.on_flag("vess_gone", hc.vanish("Vess"))
q.talker("Vess", [q.say("You brought the Matriarch down!? You're impossible! Now my oath is kept. Farewell!",
                        do=[A.flag("vess_gone")], who="Vess", mood="Cool and amused, a hint of respect.")],
         voice={"desc": "A woman in her thirties, a duelist and an assassin. Cool, low, precise voice with a clipped "
                        "southern English accent. Amused and unhurried.", "seed": 49})

q.near(*rift_xy, 330, [A.print("The square is a pit of fire. Something vast stirs in it, far below.")])
q.near(*square_px(*south_c), 260, [A.print("Fire-imps dance on the south landing.")], when=q.when(not_="rusk_holds"))

for who_, pic_ in (("Gorm", "Townsman3Pic"), ("Ilsa", "IngridPic"), ("Edric", "ArchivistPic"),
                   ("Doran", "QuarterMasterPic"), ("Wenna", "MaidenPic4"), ("Rusk", "MalePic9"), ("Tam", "WoundedApprenticePic"),
                   ("Hob", "Warrior2Pic"), ("Vess", "MaidenPic6")):
    q.portrait(who_, pic_)
for n_, pic_ in zip(refugees + [n for n, _ in fleeing], ("MaidenPic3", "MalePic7", "MaidenPic4", "Townsman3Pic",
                                                         "MalePic8", "MaidenPic2", "Townsman1Pic", "MalePic11")):
    q.portrait(n_, pic_)

mods.attach(sm.B)
m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())
m.scripts.update(hc.files())

# ---- 11. the exteriors' dressing ---------------------------------------------------------------------------------------
dressed = Exterior(m, land, "green", placed=placed).dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed, os.path.join(OUT, f"{NAME}.rooms.json"), yards=P.built)
    from kit.campaign import apply_deliveries
    apply_deliveries(q)            # voice-gate deliveries (kit/campaign.py DELIVERIES)
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS", "VOICE"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} | sealed {len(sealed)} | "
          f"flames {len(fire_xy)} | shops {n_shops} | caches {len(caches)} | opened {len(opened)} | lines "
          f"{len(q.strings)} | brood {len(brood)} | docks {len(P.docks)} | dressing {sum(dressed.values())} groups")
