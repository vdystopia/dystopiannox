"""The Hollow Choir, act 7: the Ashen Barrow (AshBarrow). Beyond the March Gate the road climbs into grey hills where
nothing grows but dead trees: the barrow-field of the founders, who cast the five bells in this hill and lie under it in
the Land of the Dead's manner (rules/CULTURES.md; campaign/hollowchoir/BIBLE.md; kit/campaign.py ACTS[6]). Two
sections above ground: the ash hills (FORESTS["camp"]: bare rock and dead trees on dark earth) round the barrow-field,
the barrow and the founders' road; the red wood (FORESTS["dusk"]) of the south-west, where the last ash-warden keeps
his lodge. Below ground, reached only by the barrow's stairs (TR-1, skills/nox-transporters), the founders' deep: a
cavern where the bells were cast (the foundry: cold furnaces round the casting pit) and the founders' crypt, built and
furnished in the Land of the Dead's manner (BUILDINGS["ice_temple"]: the founders' hall with the last founder's tablet,
the tombs, the bell-keepers' library), drawn walled off in the east of the grid.

The story
- The player comes over the hills from the Marches on the Choir's trail. The founders' road runs past the barrow to
  the Ash Gate and on to the Emberforge, but the gate is shut fast, and a low singing seems to come from its stones.
- Old Wystan, the last of the ash-wardens who kept the barrow, hides in his lodge in the red wood. A fortnight ago the
  Hollow Choir's grey priests came singing, went down into the barrow and the dead rose behind them; his brother-wardens
  went in after them and never came out. Below the barrow lie the founders and the last bell's stone.
- Main quest, the fifth stone (a guarded way down, a boss, the stone won): the barrow's outer wardens (the Choir's dead:
  skeleton lords and skeletons at the door and in its halls) keep the stairs down. Below, the Choir's Bone Callers (M3,
  the Choir's priests) sing up the dead in the foundry and the founders' hall; in the tombs Cantor Hulme (a Bone Caller,
  their chief) has pried the fifth Spirit Stone (SPIRIT_STONE) out of the last founder's tomb. Killed, he drops it (one
  stone, one death) and his song no longer holds the Ash Gate: it opens, and the exit beyond leads to the Emberforge.
  Wystan gives the act's reward when the singing stops.
- The reliquary (choice B read: RELIQUARY). A player who kept the Choir's bone reliquary in the Mirewood carries a rod of
  yellowed bone the dead know: while he carries it, the outer wardens take him for one of the Choir and stand aside,
  frozen at their posts (kit/hc_standaside.py); strike one and the whole guard wakes. The founders' deep still fights
  (its dead are the Bone Callers' own, and the priests know their own). Wystan sees the rod and says so. Without it, the
  outer wardens fight.
- The Last Verse (cross-map, Brother Edric's): before the last founder's tablet in the founders' hall lie the bones of
  Brother Anselm, a bell-keeper of Edric's order who came here long ago to take the last verse, with his journal (Edric's
  lore: the bells were cast here, each founder lies with his bell's verse, and Edric was his pupil) and the rubbing he
  made, a blue stone rubbed with the founder's words (VERSE_STONE: an item lying on the floor, taken once).
- Side quest, the ward-fires (things done in any order, a count read from the world): three ward-fires ringed the
  barrow-field and kept the old dead quiet; the priests put them out and sang the ash-wardens up out of their graves.
  Wystan asks the player to lay his three risen brothers to rest, one at each fire (north-west, east and south): each
  one's death relights his fire, and when all three are dead Wystan pays.
- The Stormcaller (W4), the bell-founders' storm-staff, for wizards and conjurers, lies in the bell-keepers' library.
- Loot: the library's chest, the founders' chests, caches in the hills and the lodge's stores.

Tokens: reads RELIQUARY (the outer wardens stand aside; Wystan's line); gives SPIRIT_STONE (the Cantor's, dropped once)
and VERSE_STONE (Anselm's rubbing, lying once on the floor of the founders' hall).

    py mapgen/designs/hc07_ashbarrow.py [seed]
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import Land, square_tile, square_px, px_square, bfs_distance, OUTDOOR_BLENDS
from kit.vegetation import Planter, FORESTS, TOWN_PLANTING
from kit.village import Village
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT
from kit import yards as Y
from kit import camps
from kit.story import StoryMap
from kit.dressing import Exterior
from kit.biome import Dresser
from kit.transport import Transporters
from kit.mods import Mods
from kit.campaign import act, token, has, exit_next
from kit.hc_standaside import StandAside

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 3
rng = random.Random(SEED)
ACT = act(7)
NAME = ACT["map"]                      # AshBarrow
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", ACT["design"])
STONE = token("SPIRIT_STONE")          # the fifth Spirit Stone (the campaign's counted token)
VERSE = token("VERSE_STONE")           # the last founder's verse, Anselm's rubbing (counted)
RELIQ = token("RELIQUARY")             # the Choir's bone reliquary, kept in the Mirewood
JOURNAL = "BlackBook1"                 # Brother Anselm's journal (no other on the map)


def deep(X, Y):
    """The founders' deep: the part of the grid (cells X right, Y down) drawn walled off, east of the hills."""
    return X >= 178 and 58 <= Y <= 212


# Warnings accepted, each with its reason (tests/qa.py)
QA_ACCEPT = [
    ("composition", r"dark crypt room .* is sparse: furniture covers",
     "the kit's Land of the Dead crypt recipe (ROOMS dark_crypt, furnish.rack_rows) lays one short row of tombs in "
     "rooms of these shapes whatever the draw (five re-furnishings of each tried: 9-11 pieces); a shared furnisher "
     "matter. Their floors are the fights' ground: the stairs' landing among the outer wardens, the Cantor and his "
     "bones"),
]


def uv(X, Y):
    """uv of a point given in map cells as seen on screen (X right, Y down, 0..255)."""
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="the grey hills where the founders cast the five bells: dead trees on ash, the barrow-field with its three "
          "dark ward-fires, the Ashen Barrow of the founders where the Choir's dead keep the stairs down, the last "
          "ash-warden's lodge in the red wood, the Ash Gate shut on the founders' road; below, the founders' foundry "
          "and their crypt, where the Choir's priests sing up the dead",
    environment="forest", mood="grey, hushed, haunted",
    areas=[AreaIdentity("west", "the road in from the Marches: the start"),
           AreaIdentity("field", "the barrow-field: the founders' old graves", landmark="the barrow"),
           AreaIdentity("lodge", "the last ash-warden's lodge and the wardens' graveyard in the red wood"),
           AreaIdentity("fireN", "the north-west ward-fire"), AreaIdentity("fireE", "the east ward-fire"),
           AreaIdentity("fireS", "the south ward-fire"),
           AreaIdentity("barrow", "the Ashen Barrow: the wardens' hall and the stairs down"),
           AreaIdentity("gate", "the Ash Gate on the founders' road, shut by the Choir's song"),
           AreaIdentity("east", "the founders' road on to the Emberforge: the way out")],
    buildings=[BuildingIdentity("barrow", "barrow", "the Ashen Barrow", "the Choir's dead wardens"),
               BuildingIdentity("cottage", "lodge", "the wardens' lodge", "Old Wystan, the last ash-warden")])

m = Spec(NAME, summary=ACT["title"], description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"The Hollow Choir, act 7. Generated by Claude.", author="vdystopia (generated by Claude)", version="1",
         date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
AMBIENT = [118, 116, 122]                  # a grey, ash-hung light
m.d["ambient"] = list(AMBIENT)
q = QuestBook(NAME)

REGIONS = dict(
    ash=dict(forest="camp", ground=("DirtDark2", "GrassSparse2", "GrassNorm")),
    red=dict(forest="dusk", ground=("GrassSparse2", "GrassNorm", "DirtDark2")),
)
SECTION = {"west": "ash", "field": "ash", "fireN": "ash", "fireE": "ash", "barrow": "ash", "gate": "ash", "east": "ash",
           "lodge": "red", "fireS": "red"}


def section(r):
    if r in REGIONS: return r
    for part in (r or "").split("_")[1:]:
        if part in SECTION: return SECTION[part]
    return "ash"


# ---- 1. the plan: the road in, the barrow-field, the barrow, the founders' road out; the deep kept apart -------------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
land.forbidden |= {s for s in land.squares if s[0] + s[1] >= 172 and 52 <= s[0] - s[1] <= 218}   # the deep's part
AREAS = {"west": ((24, 150), 14), "field": ((92, 134), 46), "lodge": ((58, 206), 30), "fireN": ((46, 70), 12),
         "fireE": ((150, 168), 12), "fireS": ((118, 226), 12), "barrow": ((110, 52), 36), "gate": ((174, 36), 12),
         "east": ((228, 30), 12)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=True, region=SECTION[k_])
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_, bend_ in (("west", "field", 14, True, 0.15), ("field", "barrow", 13, True, 0.12),
                                 ("field", "lodge", 12, True, 0.18), ("barrow", "gate", 12, True, 0.15),
                                 ("gate", "east", 12, True, 0.12), ("field", "fireN", 9, False, 0.25),
                                 ("field", "fireE", 9, False, 0.25), ("lodge", "fireS", 9, False, 0.25)):
    land.link(a_, b_, w_, bend=bend_, road=road_, pockets=(1, 2) if road_ else (0, 1))
land.blends(m)
barrow_c0 = land.areas["barrow"]["c"]              # the founders' road stops short of the barrow's door
land.paint_roads(m, "DirtLight2", width_squares=2.6,
                 skip=land.reserved | {(i, j) for i in range(int(barrow_c0[0]) - 16, int(barrow_c0[0]) + 17)
                                       for j in range(int(barrow_c0[1]) - 16, int(barrow_c0[1]) + 17)
                                       if math.hypot(i - barrow_c0[0], j - barrow_c0[1]) < 13})

# ---- 2. the buildings: the barrow on its rise, the lodge in the red wood ----------------------------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"west": 8, "field": 20, "fireN": 6, "fireE": 6, "fireS": 6, "gate": 6},
                            first=("lodge",), centred={"barrow": "field"})
sm.connect_and_furnish(path_material="DirtLight2")

# the yards: the ash-wardens' graveyard by the lodge, the founders' old graves in the barrow-field
yards = []


def ring_of(c, radii):
    return [(c[0] + r * math.cos(a * math.pi / 6), c[1] + r * math.sin(a * math.pi / 6)) for r in radii for a in range(12)]


for kind_, area_, rs_, toward_ in (("graveyard", "lodge", (8, 10, 12, 14), "lodge"),
                                   ("graveyard", "field", (10, 13, 16, 19), "field")):
    y_ = Y.plan_any(land, rng, kind_, ring_of(land.areas[area_]["c"], rs_), toward=land.areas[toward_]["c"])
    if y_: yards.append(y_)
    else: print(f"no room for the {kind_} by the {area_}")

# ---- 3. the founders' deep: its own land in the east of the grid, the crypt it grows round -----------------------------
deepL = Land(rng, u_range=(24, 488), v_range=(-232, 232))
deepL.squares = {s for s in deepL.squares if deep(s[0] + s[1], s[0] - s[1])}
DEEP = {"foot": ((198, 76), 12), "foundry": ((216, 116), 28), "crypt": ((212, 170), 40)}
for k_, ((X_, Y_), r_) in DEEP.items():
    deepL.area(k_, uv(X_, Y_), r_, clearing=k_ != "crypt", region=k_, roughness=0.3)
for a_, b_, w_ in (("foot", "foundry", 12), ("foundry", "crypt", 14)):
    deepL.link(a_, b_, w_, bend=0.25, road=False, pockets=(1, 2))
dd = Dresser(m, rng, deepL, "cave")
m.d["ambient"] = list(AMBIENT)                     # the Dresser sets the cave's ambient: the hills keep theirs
for mat_, prio_, edge_ in OUTDOOR_BLENDS:            # and the cave's blends had put DirtDark2 level with the hills'
    m.blending(mat_, prio_, edge_)                   # roads (DirtLight2): the hills' order again, so they blend
crypt_b = dd.structure("ice_temple", "crypt", toward="foundry", scale=1.0, name="the founders' crypt")
assert crypt_b, "the founders' crypt was not built"

# ---- 4. the land grows round everything, ending in the dead wood and the rock ----------------------------------------
land.carve(margin=3.5)
lane_ = sm.keep_open({"west": 4, "fireN": 5, "fireE": 5, "fireS": 5, "gate": 3, "east": 3})
land.assign_regions()
open_ = {s for s in land.squares if math.hypot(s[0] - land.areas["field"]["c"][0], s[1] - land.areas["field"]["c"][1]) < 18}
clumps = land.thickets(160, size=(0.9, 1.8), clear=1, avoid=frozenset((lane_ | open_) & land.squares))
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
# the deep: the cavern round the crypt, its rock walls
deepL.carve(margin=3.0)
deepL.assign_regions()
deepL.apply(m, wall=dd.wall, floor=dd.base, unlevel=True)
dd.ground()
furnished = dd.furnish_structures()
# the Ash Gate: the founders' wall of grey stone across their road, shut by the Choir's song
gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "east"), prefix="AshGate", material="StoneGray")

# ---- 5. the lodge's life, the ground ------------------------------------------------------------------------------
vil = Village(m, rng, land)
for bid, b in placed:
    role = BUILDINGS[bid.role]
    for sc in role["scenes"]: vil.scene(b, sc, role=bid.role)
for r_ in REGIONS:
    g_ = REGIONS[r_]["ground"]
    land.ground_variety(m, base=g_[0], sparse=g_[1], dense=g_[2], clear=3, region=r_)

# ---- 6. the story's places ------------------------------------------------------------------------------------------
presets = json.load(open(os.path.join(HERE, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]


def preset(family, intensity="full"):
    ps = [p for p in presets if p["family"] == family and p["intensity_class"] == intensity and p["animation"] == "steady"] \
        or [p for p in presets if p["family"] == family]
    return dict(max(ps, key=lambda p: p["weighted_share"])["xfer"])


C = {k: land.areas[k]["c"] for k in AREAS}
west_c, field_c, lodge_c, barrow_c, gate_c, east_c = (C[k] for k in ("west", "field", "lodge", "barrow", "gate", "east"))
fenced = set().union(*({(y_.gi + a, y_.gj + b) for a in range(-2, y_.w + 2) for b in range(-2, y_.h + 2)}
                       for y_ in yards)) if yards else set()


def off_road(c, clear=4.5, reach=12):
    near_road = bfs_distance(list(land.roads), land.squares, int(clear) + 1)
    cands = [s for s in land.squares if near_road.get(s, 99) >= clear and s not in land.taken_strict and
             s not in fenced and s not in land.water and math.hypot(s[0] - c[0], s[1] - c[1]) <= reach]
    s = min(cands, key=lambda s: math.hypot(s[0] - c[0], s[1] - c[1])) if cands else (int(c[0]), int(c[1]))
    return (s[0] + 0.5, s[1] - 0.5)


# the three ward-fires: a ring of grave-stones round a cold hearth, dark until its warden is laid to rest (then a lit
# incense basin is made at its named light: an immobile basin is not a script name the game knows)
FIRES = []
for k_, area_ in enumerate(("fireN", "fireE", "fireS")):
    at_ = off_road(C[area_], clear=2.0, reach=5)
    xy_ = camps.stone_ring(m, rng, land, at_, n=6, radius=2.2, stone="Obelisk", light=preset("orange"),
                           light_name=f"WardLight{k_ + 1}", clear=3)
    FIRES.append((at_, xy_))
# caches in the hills, off the ways
caches = []
for near_, loot_, stump_ in ((C["fireN"], [("Gold", {"Amount": 40}), "BluePotion", "RedPotion"], False),
                             (lodge_c, [("Gold", {"Amount": 35}), "CurePoisonPotion", "RedPotion"], True)):
    s_ = sm.hidden_spot(near_, r=(7, 15))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_, stump=stump_))
# signposts
camps.signpost(m, land, (west_c[0] + 2.5, west_c[1] - 1.5),
               q.text("THE ASHEN BARROW\nThe founders sleep here.\nLet them.", "Sign"))
gs_ = sm.road_near(((gate_sq[0] * 2 + barrow_c[0]) / 3, (gate_sq[1] * 2 + barrow_c[1]) / 3))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 1.5),
               q.text("THE ASH GATE\nThe founders' road to the Emberforge", "Sign"))
lr_ = sm.road_near(((lodge_c[0] + field_c[0]) / 2, (lodge_c[1] + field_c[1]) / 2))
camps.signpost(m, land, (lr_[0] + 2.0, lr_[1] - 1.5), q.text("WARDENS' LODGE\nKnock loud. We are old.", "Sign"))
# the hills' lights: grey and cold over the field, warm at the lodge
for (lx_, ly_), fam_ in ((square_px(*west_c), "white"), (square_px(*lodge_c), "orange"), (square_px(*barrow_c), "purple"),
                         (square_px(gate_c[0], gate_c[1]), "purple"), (square_px(*field_c), "white"),
                         (square_px(*east_c), "white")):
    m.obj_px("ColorLight", lx_, ly_ - 6, xfer=preset(fam_, "dim" if fam_ == "purple" else "full"))


# ---- the deep's places: the foot of the stairs, the foundry, the founders' crypt ------------------------------------
DC = {k: deepL.areas[k]["c"] for k in DEEP}
foot_c, foundry_c, crypt_c = DC["foot"], DC["foundry"], DC["crypt"]
rooms2 = {r.kind: r for r in crypt_b.rooms}
hall2, tombs2, library2 = rooms2.get("dark_chapel"), rooms2.get("dark_crypt"), rooms2.get("library")
assert hall2 and tombs2 and library2, f"the founders' crypt's rooms: {sorted(rooms2)}"


def clear_round(pts, r, keep=()):
    """Takes out the furniture within r px of the points (a landing, a tablet's floor stay clear)."""
    keep = {id(o) for o in keep}
    gone = [o for o in m.d["objects"] if id(o) not in keep and "x" in o and "door" not in o and
            any(math.hypot(o["x"] - x, o["y"] - y) < r for x, y in pts)]
    ids = {id(o) for o in gone}
    m.d["objects"][:] = [o for o in m.d["objects"] if id(o) not in ids]
    return gone


def wall_gap(p):
    """px from p to the nearest wall cell's centre (within 6 cells)."""
    cx, cy = int(p[0] // CELL), int(p[1] // CELL)
    ds = [math.hypot((cx + a + 0.5) * CELL - p[0], (cy + b + 0.5) * CELL - p[1]) for a in range(-6, 7)
          for b in range(-6, 7) if (cx + a, cy + b) in m.wallmap]
    return min(ds) if ds else 999.0


def room_spot(room, prefer, need=(), clear=46):
    """A floor point of the room nearest `prefer` whose own spot and offsets `need` stand `clear` px off every wall."""
    pts = [((x + 1) * CELL, (y + 1) * CELL) for x, y in room.tiles]
    for p in sorted(pts, key=lambda p: math.hypot(p[0] - prefer[0], p[1] - prefer[1])):
        if all(wall_gap((p[0] + dx, p[1] + dy)) >= clear for dx, dy in ((0, 0),) + tuple(need)):
            return p
    return None


# the founders' foundry: the casting pit (a ring of furnace-stones round the cold pit), the bell-founders' gear
fsc = camps.Scene(m, rng, deepL, foundry_c)
pit_xy = camps.stone_ring(m, rng, deepL, foundry_c, n=8, radius=2.8, stone="CaveRockPillarShort1",
                          core="DunMirFlameBasinUnlit", light=preset("red", "dim"), clear=4)
for t_, r_, a_ in (("Anvil2", 5.2, 0.6), ("Bellows3", 5.6, 1.1), ("Anvil5", 5.4, 3.3), ("Bellows6", 5.8, 3.8),
                   ("BarrelWithTools1", 6.0, 5.0), ("CaveRocksLarge", 6.4, 2.2), ("Skull", 4.4, 4.4), ("LegBone", 4.6, 4.8),
                   ("ArmBone", 4.2, 5.6)):
    fsc.put(t_, *fsc.at(r_, a_))
q.near(*pit_xy, 260, [A.print("The founders' foundry: cold furnaces round the great pit where the bells were cast.")])

# the founders' hall: the last founder's tablet before the altar, Brother Anselm's bones, his journal and his rubbing
hcx = sum((x + 1) * CELL for x, _ in hall2.tiles) / len(hall2.tiles)
hcy = sum((y + 1) * CELL for _, y in hall2.tiles) / len(hall2.tiles)
altar = next((o for o in m.d["objects"] if o.get("type", "").startswith("LOTDLichGodStatue") and
              (int(o["x"] // CELL), int(o["y"] // CELL)) in {(x + a, y + b) for x, y in hall2.tiles
                                                            for a in (-1, 0, 1) for b in (-1, 0, 1)}), None)
ax_, ay_ = (altar["x"], altar["y"]) if altar else (hcx, hcy)
ux_, uy_ = hcx - ax_, hcy - ay_
ul_ = math.hypot(ux_, uy_) or 1
tab_pref = (ax_ + ux_ / ul_ * 70, ay_ + uy_ / ul_ * 70)
tab_xy = room_spot(hall2, tab_pref, need=((ux_ / ul_ * 50, uy_ / ul_ * 50),), clear=40) or tab_pref
clear_round([tab_xy, (tab_xy[0] + ux_ / ul_ * 45, tab_xy[1] + uy_ / ul_ * 45)], 58, keep=[altar] if altar else ())
m.obj_px("TombstoneReadable3", *tab_xy, xfer={"Text": q.text(
    "HERE LIES ALDGAR\nLAST OF THE FOUNDERS\nWho cast the fifth bell.\n\nRing five as one\nand the deep shall sleep.",
    "Sign")})
bx_, by_ = tab_xy[0] + ux_ / ul_ * 42, tab_xy[1] + uy_ / ul_ * 42       # Anselm fell before the tablet
for t_, dx_, dy_ in (("CorpseSkullS", 0, 0), ("CorpseRibCageS", 12, 10), ("CorpseLeftLowerLegE", 24, 4),
                     ("CorpseRightUpperArmE", -10, 12)):
    m.obj_px(t_, bx_ + dx_, by_ + dy_)
journal = m.obj_px(JOURNAL, bx_ - 22, by_ - 6)
verse = m.obj_px(VERSE, bx_ + 4, by_ + 24)
q.near(*tab_xy, 150, [A.print("Before the founder's tablet lie the bones of a monk in a bell-keeper's robe, a black "
                              "book, and a blue stone rubbed with the tablet's words.")])

# the bell-keepers' library: the founders' storm-staff (W4) and the keepers' gold in its chest
mods = Mods(m, sm.pop)
def room_chest(room, used=()):
    """The chest the furnisher stood in the room (on its own tiles first, then by its walls), not one of `used`."""
    for pad in (0, 1):
        cells = {(x + a, y + b) for x, y in room.tiles for a in range(-pad, pad + 1) for b in range(-pad, pad + 1)}
        o = next((o for o in m.d["objects"] if "Chest" in o.get("type", "") and "Sack" not in o.get("type", "")
                  and all(o is not u for u in used) and (int(o["x"] // CELL), int(o["y"] // CELL)) in cells), None)
        if o: return o
    return None


lib_chest = room_chest(library2)
lib_loot = [mods.weapon_item("W4", name="Stormcaller"), ("Gold", {"Amount": 60}), "BluePotion", "BluePotion"]
if lib_chest:
    lib_chest["items"] = m.items_at(lib_loot, lib_chest["x"], lib_chest["y"])
else:
    lx_, ly_ = sm.free_px(library2, clear=30)
    lib_chest = m.obj_px("CryptChest2", lx_, ly_, items=lib_loot)
# the tombs: the last founder's tomb, broken open; the founders' chest beside it
tcx = sum((x + 1) * CELL for x, _ in tombs2.tiles) / len(tombs2.tiles)
tcy = sum((y + 1) * CELL for _, y in tombs2.tiles) / len(tombs2.tiles)
tomb_chest = room_chest(tombs2, used=(lib_chest,))         # the founders' chest, if the tombs hold one
if tomb_chest:
    tomb_chest["items"] = m.items_at([("Gold", {"Amount": 70}), "RedPotion", "RedPotion", "CurePoisonPotion"],
                                     tomb_chest["x"], tomb_chest["y"])
tomb_floor = sm.free_px(tombs2, prefer=(tcx, tcy), clear=34)     # where the Cantor stands, over the broken tomb
# the deep's lights (the cave's, sparse) and its own darkness: a polygon with the cave's ambient
deep_px = [square_px(s[0] + 0.5, s[1] - 0.5) for s in deepL.squares]
X0, X1 = min(p[0] for p in deep_px) - 46, max(p[0] for p in deep_px) + 46
Y0, Y1 = min(p[1] for p in deep_px) - 46, max(p[1] for p in deep_px) + 46
m.polygon(f"{NAME}:Deep", (44, 40, 52), [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)])

# ---- 7. the stairs down: in the barrow's crypt, to the foot of the founders' deep -----------------------------------------
barrow_b = sm.building_in("barrow")
assert barrow_b, "the barrow was not built"
bhall = sm.room_of("barrow", "dark_chapel")
bcrypt = sm.room_of("barrow", "dark_crypt")
assert bhall and bcrypt, "the barrow's rooms were not built"
# the flight down at the crypt's east end (its landing up-left of it: kit/transport STAIRS_EXTRA), clear of the tombs
bcx = sum((x + 1) * CELL for x, _ in bcrypt.tiles) / len(bcrypt.tiles)
bcy = sum((y + 1) * CELL for _, y in bcrypt.tiles) / len(bcrypt.tiles)
east_pt = max(((x + 1) * CELL, (y + 1) * CELL) for x, y in bcrypt.tiles)
down_xy = room_spot(bcrypt, (east_pt[0] - 60, east_pt[1]), need=((-29, -31), (1, 0)), clear=46)
assert down_xy, "no floor for the stairs down in the barrow's crypt"
clear_round([down_xy, (down_xy[0] - 29, down_xy[1] - 31)], 60)
# the flight up at the deep's foot, against its north-west rock, its landing down-right of it
fpx = square_px(*foot_c)
up_pts = [square_px(s[0] + 0.5, s[1] - 0.5) for s in deepL.squares
          if math.hypot(s[0] - foot_c[0], s[1] - foot_c[1]) < 7]
up_xy = next((p for p in sorted(up_pts, key=lambda p: p[0] + p[1])
              if all(wall_gap((p[0] + dx, p[1] + dy)) >= 40 for dx, dy in ((0, 0), (33, 30), (-1, -2))) and
              wall_gap(p) <= 90), fpx)
dd.taken |= {(px_square(*up_xy)[0] + a, px_square(*up_xy)[1] + b) for a in range(-3, 4) for b in range(-3, 4)}
dd.taken |= {(int(foundry_c[0]) + a, int(foundry_c[1]) + 1 + b) for a in range(-7, 8) for b in range(-7, 8)}

# ---- 8. planting, the start, the exit, the transporter ---------------------------------------------------------------
keep = set()
for bid, b in placed:
    for d in b.entrances:
        di, dj = px_square(*d.px)
        keep |= {(di + a, dj + b2) for a in range(-2, 3) for b2 in range(-2, 3)}
vil.ground_bits(1.0)
planter = Planter(m, rng, land, "camp", keep_clear=keep | lane_, settled=("lodge",),
                  forest_of=lambda s: REGIONS[section(land.region_of(s))]["forest"])
n_trees, n_small = planter.plant_all(groves=3, profile=TOWN_PLANTING)
piles = planter.rock_piles(max(4, len(land.squares) // 800))
vignettes = planter.forest_floor(max(5, len(land.squares) // 800))
# the deep: pillars and stalagmites along its rock, rubble and bones, its few lights
d_trees, d_small = dd.vegetate(keep_clear=dd.taken, groves=1)
dd.scatter_open(0.6)
dd.rim(0.7)
n_dl = dd.lights(0.7)
m.d["ambient"] = list(AMBIENT)
start_xy = square_px(west_c[0] + 0.5, west_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
exits = exit_next(sm, "east", 7, prefix="AshExit")
tp = Transporters(m)
stairs = tp.add("stairs", down_xy, up_xy, "BarrowStair", style="crypt",
                serves=[(lib_chest["x"], lib_chest["y"]), (verse["x"], verse["y"]), tomb_floor])

# ---- 9. the people and the dead ---------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
person, free_px = sm.person, sm.free_px
lb_ = sm.building_in("lodge")
wy_ = (sm.doorside(building=lb_, toward=square_px(*field_c)) if lb_ else None) or square_px(*lodge_c)
person("Con03A", "Kenneth", wy_[0], wy_[1], "Wystan", face=square_px(*field_c))
for c_, r_ in ((barrow_c, 16), (field_c, 10)):
    sm.keep_folk_away(c_, r_)

# the outer wardens: the Choir's dead at the barrow's door and in its halls (they stand aside for the reliquary)
wardens = []
kd_ = sm.outside_door(building=barrow_b)
if kd_:
    kx_, ky_ = square_px(*barrow_c)
    ux2, uy2 = kd_[0] - kx_, kd_[1] - ky_
    ul2 = math.hypot(ux2, uy2) or 1
    for k, s_ in enumerate((1, -1)):
        n = f"DoorWarden{k + 1}"
        pop.creature("SkeletonLord", kd_[0] + ux2 / ul2 * 34 - uy2 / ul2 * 58 * s_,
                     kd_[1] + uy2 / ul2 * 34 + ux2 / ul2 * 58 * s_, action="guard", scr=n, aggr=0.83,
                     face=square_px(*field_c))
        wardens.append(n)
wardens += sm.keepers(bhall, ("SkeletonLord", "Skeleton", "Skeleton"), "HallWarden")
wardens += sm.keepers(bcrypt, ("Skeleton", "Skeleton", "Ghost"), "CryptWarden")
# the risen ash-wardens, one at each dark ward-fire, a skeleton beside each
risen = []
for k_, (at_, xy_) in enumerate(FIRES):
    n = f"Risen{k_ + 1}"
    pop.creature("SkeletonLord", xy_[0] + 70, xy_[1] + 30, action="guard", scr=n, aggr=0.83, face=xy_)
    pop.creature("Skeleton", xy_[0] - 60, xy_[1] + 50, action="guard", scr=f"RisenBone{k_ + 1}", aggr=0.83, face=xy_)
    risen.append(n)
# the hills' own: ghosts over the barrow-field, bats and spiders in the dead wood, wolves in the red wood
sm.wild({"Ghost": 3, "Bat": 4, "SmallSpider": 2, "Spider": 1, "Wolf": 2}, away_from=square_px(*lodge_c), per100=0.4,
        gap=7, min_away=20, avoid=(west_c, lodge_c, barrow_c, gate_c, east_c) + tuple(at_ for at_, _ in FIRES))

# the founders' deep: the Choir's priests (Bone Callers, M3) and the dead they sang up; Cantor Hulme in the tombs
deep_foes = []
for k_, (r_, a_) in enumerate(((2.0, 0.5), (2.6, 3.0))):
    n = f"FootBones{k_ + 1}"
    pop.creature("Skeleton", *square_px(foot_c[0] + r_ * math.cos(a_) + 1.5, foot_c[1] + r_ * math.sin(a_) + 1.5),
                 action="guard", scr=n, aggr=0.83, face=fpx)
    deep_foes.append(n)
fcx, fcy = square_px(*foundry_c)
for k_, a_ in enumerate((1.9, 4.1, 5.6)):
    n = f"FoundryBones{k_ + 1}"
    pop.creature("Skeleton" if k_ < 2 else "SkeletonLord", fcx + 150 * math.cos(a_), fcy + 150 * math.sin(a_),
                 action="guard", scr=n, aggr=0.83, face=(fcx, fcy))
    deep_foes.append(n)
pop.creature("Necromancer", fcx + 110 * math.cos(0.4), fcy + 110 * math.sin(0.4), action="guard", scr="FoundryCaller",
             aggr=0.83, face=fpx)
mods.monster_call("bonecaller", "FoundryCaller", "A Bone Caller of the Choir", 320, 230.0, 0.0)
deep_foes += sm.keepers(hall2, ("Skeleton", "SkeletonLord"), "HallBones")
hx2, hy2 = free_px(hall2, prefer=(hcx, hcy), clear=34)
pop.creature("Necromancer", hx2, hy2, action="guard", scr="HallCaller", aggr=0.83, face=tab_xy)
mods.monster_call("bonecaller", "HallCaller", "A Bone Caller of the Choir", 320, 230.0, 0.0)
deep_foes += sm.keepers(library2, ("Ghost", "Skeleton"), "LibraryDead")
deep_foes += sm.keepers(tombs2, ("Skeleton", "SkeletonLord", "Skeleton"), "TombBones")
cx2, cy2 = tomb_floor
pop.creature("Necromancer", cx2, cy2, action="guard", scr="Cantor", aggr=0.83, face=(tcx, tcy))
mods.monster_call("bonecaller", "Cantor", "Cantor Hulme of the Choir", 460, 230.0, 0.0)
for k_, (X_, Y_) in enumerate(((206, 98), (222, 132))):
    pop.creature("Bat", *square_px((X_ + Y_) / 2, (X_ - Y_) / 2), action="guard", scr=f"DeepBat{k_ + 1}", aggr=0.83)

story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]
            if not deep(int(o["x"] // CELL), int(o["y"] // CELL))] + [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)

# ---- 10. the story ----------------------------------------------------------------------------------------------------
GATE = [A.unlock("AshGate1"), A.unlock("AshGate2")] + [A.enable(n) for n in exits]
q.start([A.lock("AshGate1"), A.lock("AshGate2"), A.stage("began", 1)] + [A.disable(n) for n in exits] +
        [A.disable(f"WardLight{k + 1}") for k in range(3)] +
        [A.print("Grey ash lies over the hills. Nothing sings in the dead trees."),
         q.journal("Find the fifth Spirit Stone in the Ashen Barrow, where the bells were cast.", HINT)])
# the Ash Gate opens once the Cantor lies dead (read from the world: it holds after a saved game is loaded too)
q.when_true(q.at("began", 1, flag=q.dead("Cantor")), GATE + [A.flag("gate_open")])

MAIN = "Take the fifth Spirit Stone from the founders' crypt below the barrow."
q.on_death("Cantor", [A.drop(STONE), A.flag("cantor_dead"),
                      A.print("The Cantor's song breaks off. A red stone falls from his hand, humming. Far above, "
                              "something heavy grinds open."),
                      q.note("NOTE: Cantor Hulme is dead. His song held the Ash Gate shut. It stands open now.")])
# the reliquary: the outer wardens take its bearer for one of the Choir
aside = StandAside(q)
aside.group(wardens, item=RELIQ, wake="The wardens wake! The dead are not fooled twice!", broken="wardens_woke")
q.near(*(kd_ or square_px(*barrow_c)), 300,
       [A.flag("rod_seen"),
        A.print("The dead at the barrow's door turn their empty eyes on the bone rod in your hand... and do not move. "
                "They take you for one of the Choir."),
        q.note("NOTE: The barrow's dead wardens let the Choir's own pass. Striking one would wake them all.")],
       when=q.when(has=RELIQ))
q.near(*(kd_ or square_px(*barrow_c)), 300, [A.print("The Ashen Barrow. Its dead stand guard at the door.")],
       when=q.when(not_="rod_seen"))
q.near(*up_xy, 220, [A.print("The air below is warm and smells of old smoke. Somewhere ahead, someone is singing.")])
q.near(*square_px(gate_c[0], gate_c[1]), 200, [A.print("The Ash Gate is shut fast. A low singing seems to come from "
                                                      "the stones themselves.")], when=q.when(not_="gate_open"))
# Brother Anselm's journal: Brother Edric's lore
q.on_pickup(JOURNAL, [q.note("NOTE: Brother Anselm's journal: the five bells were cast in this hill, and each founder "
                             "lies with his bell's verse."),
                      q.note("NOTE: Anselm's last page: 'Edric is young, but he must keep the verses now. The fifth "
                             "lies here.'")])

# Old Wystan: the hook, the ward-fires and the act's reward
FIRES_Q = "Lay the three risen wardens to rest and relight the ward-fires."
wy_lines = q.errand(
    "Wystan", "fires",
    offer="These cursed priests are worse than the plague! They put out our three ward-fires and sang my brothers up "
          "out of their graves!\n\nEach risen warden keeps his own fire, north-west, east and south of the "
          "barrow-field. Lay them to rest and the fires will burn again. Will you do it?",
    reminder="I shan't sleep till the ward-fires burn again! Hurry, before the priests sing up more!",
    thanks="My deepest thanks! The fires burn, and my brothers rest at last.\n\nTake this gold, and my old "
           "warden's helm. I insist.",
    after="The ward-fires burn bright again. A thousand thanks!",
    objective=FIRES_Q,
    done=q.when(flag=q.dead(*risen)), reward=[A.gold(90), A.give("OrnateHelm"), A.give("RedPotion", 2)],
    refusal="Then my brothers walk till the world ends.")
wy_lines[-1]["When"]["Flag"] = "wystan_told"          # the ward-fires are asked for once the barrow is told of
q.talker("Wystan", [
    q.say("The singing's stopped! I heard it stop!\n\nHere, take this as a gift from the last of the ash-wardens. "
          "The Ash Gate stands open. The founders' road runs on to the Emberforge, where the Choir has gone. Go swiftly.",
          when=q.when(flag=q.dead("Cantor"), not_="wystan_paid"),
          do=[A.flag("wystan_paid"), A.gold(110), A.give("BluePotion", 2), A.give("RedPotion", 2), q.done(MAIN)],
          who="Wystan"),
] + wy_lines + [
    q.say("I have nothing more to give but my thanks. Mind the founders' road.", when=q.when(flag="wystan_paid"),
          who="Wystan"),
    q.say("Those singing priests are a curse on this hill.", when=q.when(flag="wystan_told"), who="Wystan"),
    q.say("Stranger! Living, and armed! The stars be thanked!\n\nThe Hollow Choir came a fortnight past. Grey priests, "
          "singing. They went down into the barrow and the dead rose up behind them! My brother-wardens went after "
          "them and never came out.\n\nAnd that rod of bone in your hand! The Choir's priests carry those. The dead at "
          "the barrow door will take you for one of them.\n\nThe barrow stands north of the field. Below it lie the "
          "founders, and the last bell's stone with them. Go down and take it, before the priests do.",
          when=q.when(has=RELIQ), do=[A.flag("wystan_told"), A.stage("main", 1), q.journal(MAIN)], who="Wystan"),
    q.say("Stranger! Living, and armed! The stars be thanked!\n\nThe Hollow Choir came a fortnight past. Grey priests, "
          "singing. They went down into the barrow and the dead rose up behind them! My brother-wardens went after "
          "them and never came out.\n\nThe barrow stands north of the field. Below it lie the founders, and the last "
          "bell's stone with them. Go down and take it, before the priests do.",
          do=[A.flag("wystan_told"), A.stage("main", 1), q.journal(MAIN)], who="Wystan")],
    voice={"desc": "An old gravekeeper in his seventies. Cracked, gravelly, quavering voice, a broad Northumbrian "
                   "accent. Speaks in bursts, frightened but stubborn.", "seed": 7071})
q.portrait("Wystan", "UndertakerPic")
# the ward-fires: each risen warden's death relights his fire
for k_, n in enumerate(risen):
    q.on_death(n, [A.spawn("LOTDIncenseBasinLit", f"WardLight{k_ + 1}"), A.enable(f"WardLight{k_ + 1}"),
                   A.print("The risen warden falls, and his ward-fire flares up again.")])
    q.near(*FIRES[k_][1], 230, [A.print("A ring of grave-stones round a cold hearth: one of the ash-wardens' "
                                        "ward-fires.")])

mods.attach(B)
m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())
m.scripts.update(aside.files(NAME))

# ---- 11. the hills' dressing ----------------------------------------------------------------------------------------
dressed = Exterior(m, land, "green", placed=placed).dress()


class _Far:                                          # the founders' crypt, for the rooms sidecar
    def __init__(self, rooms): self.rooms = rooms


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed + [(BuildingIdentity("ice_temple", "crypt", "the founders' crypt", "the founders, and the "
                                              "Choir's Cantor"), crypt_b)],
                  os.path.join(OUT, f"{NAME}.rooms.json"), yards=built)
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS", "VOICE"))))
    print(f"land {len(land.squares)} squares, deep {len(deepL.squares)} | buildings {len(placed)}/{len(ID.buildings)} "
          f"(missed: {', '.join(sm.missed) or 'none'}) | trees {n_trees} | caches {len(caches)} | opened {len(opened)} "
          f"| lines {len(q.strings)} | yards {', '.join(y_.kind for y_ in built) or 'none'} | dressing "
          f"{sum(dressed.values())} groups | wardens {len(wardens)} | deep foes {len(deep_foes)} | deep lights {n_dl} "
          f"| stairs {down_xy} -> {up_xy}")
