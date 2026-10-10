"""The Hollow Choir, act 8: The Emberforge (map Emberforg). A volcanic caldera where the realm's founders forged the
five bells' clappers, the Spirit Stones; lava biome (rules/BIOMES.md), dressed as Emberhollow dresses its lava.
campaign/hollowchoir/BIBLE.md is the story; kit/campaign.py the acts, tokens and cast.

The story
- The road down from the Ashen Barrow (act 7) comes into the caldera from the west. The mountain hums: the Choir is
  singing somewhere ahead. At the road's end stands the Wardens' Lodge, the last of the forge-wardens who kept the
  founders' forge, driven out three days ago when the Hollow Choir came over the ridge with its stolen stones.
- Main quest, the Breaking of the Song (the gate of the act): Warden Hesketh, the last warden, says it plainly: the
  Choir holds the Emberforge. Its Cantor has barred the Forge Gate on the road east, and beyond the forge, on the
  shore of the Well of Embers, the High Caller Morvaine and two Cantors sing over the stones they carry to wake the
  Ember Matriarch who sleeps under the mountain. The Cantor of the Gate stands before the gate with the Choir's
  blades: his death drops the bar (the gate opens). Through the forge's yard (the fire-things the song woke hold the
  forge itself) lies the Well: the two Cantors (Bone Callers, M3) sing at the ring of stones, Morvaine behind them on
  the shore, warded and still. Kill both Cantors and the song breaks; Morvaine says the Matriarch has heard enough,
  and goes up in smoke with the stones he holds (to his spire: act 9). The Matriarch stirs: a lesser rising, M4 with
  a moderate health and her imp brood, heaves out of the Well. Killed, she sinks back into the fire, the Spire Road
  gate east opens, and the exit leads to the Hollow Spire. Hesketh pays.
- The Starsteel Blade (the campaign's side quest, acts 1, 3, 8, 10): Doran Ashforge, Brackwater's old smith, waits at
  the lodge: he came by the ash road to the founders' anvil, the only one that can work starsteel, and found the Choir
  there first. When the Forge Gate opens he goes to the founders' anvil in the forge's yard (a swap off-screen: Doran
  at the lodge leaves, DoranAnvil at the anvil appears). With STARSTEEL (and DORAN_LETTER, his guild medallion, if the
  player still carries it) he asks to forge it: yes, and the forge takes the STARSTEEL and he hands over the
  Flamebrand at masterwork (W1 at tier 3: a copy made in the map and kept in the founders' strongroom, a sealed room
  of the forge's stone in its yard, its door locked for good; kit/hc_scripts hand_over). Without the
  tokens the founders' anvil still works plain steel: lay a longsword or battle axe beside it and stand on the forge
  plate (kit/mods S1 forge, Doran as its smith: fine, superb, masterwork for gold and smithing level).
- The Chained Smiths (this act's own side quest, a rescue): Odda at the lodge: the Choir took her husband Galt and his
  brother Fenn, the lodge's smiths, to the slag pens in the south-west to dig the slag the Choir's ritual burns. Kill
  the Choir's overseers there and talk to Galt: the brothers walk home along the paths (StoryMap.journey). Odda pays.
- The Risen Wardens (a second errand of this act): Corra, an old warden's widow at the lodge's end of the north path:
  the Choir's singers raised the Wardens' dead at their cairns north of the lodge, her Aldo among them, and the First
  Warden in his old mail. Lay them to rest (a Skeleton Lord and four Skeletons); the First Warden's chest is the
  reward, with Corra's potions.
- Fights with a reason: fire imps nest in the slag heaps south of the road to the gate; the Choir's blades keep the
  gate, the pens and the Well; the forge's own keepers (demons the song woke) hold the forge; the Wardens' dead at the
  cairns; the caldera's creatures by the cliffs. The lodge's storehouse sells potions; caches lie in the ash.
- How it is built: Morvaine at the Well is a Necromancer kept immortal, frozen and harmless (hc_scripts freeze) and
  vanishes when the song breaks; the Matriarch waits out of the play beside the ring (A.disable) as a plain Ember Demon
  and becomes the kit/mods M4 only when she rises (hc_scripts registers ModBoss then: registered at the start, her
  brood would be born round her while she hid). The forge's blanks and the masterwork Flamebrand lie in the founders'
  strongroom, a room of the forge's stone in its yard whose DunMirDoor is locked to a mechanism no script turns.

Tokens (by name, kit/campaign TOKENS): reads DORAN_LETTER (Doran's guild medallion: his words) and STARSTEEL (the
masterwork Flamebrand), takes STARSTEEL. Gives none: the Spirit Stones go with Morvaine (the player arrives with three,
from acts 3, 6 and 7, and wins the last two in act 9). A player who loads the act with an empty pack finishes it the
same way: the main quest reads no token.

    py mapgen/designs/hc08_emberforge.py [seed]
"""
QA_ACCEPT = [   # (tests/qa.py)
    ("composition", r"is sparse: furniture covers",
     "the kit's furnisher (generate_building + furnish_original) fills small rooms under the half-median house rule on "
     "every map built today (Ironcrag accepts the same; Thornwick's rebuild: 14): the lodge's shop and living room and "
     "the forge's Dun Mir hall of arms; the room lab's work, not this map's (seeds 1-7 tried: every one has 3 or more)"),
]
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL, px, uv_to_xy, rect_tiles, rect_wall_cells
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import Land, square_tile, square_px, px_square, bfs_distance
from kit.biome import Dresser
from kit.village import Village
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT, NOTE
from kit.story import StoryMap
from kit.posts import camp_posts
from kit.mods import Mods, FORGE_LINES, _ench
from kit.campaign import act, token, has, cast_person, voice, CAST, FOES, exit_next
from kit.hc_scripts import HcScript
from kit import camps

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 6
rng = random.Random(SEED)
ACT = act(8)
NAME = ACT["map"]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", ACT["design"])
PATH = "CaveHardBrown"               # the trodden ways: packed brown rock through the black crags
LETTER, STEEL = token("DORAN_LETTER"), token("STARSTEEL")   # by name (kit/campaign TOKENS), never by item type


def uv(X, Y):
    return (X + Y, X - Y)


ID = MapIdentity(
    name=NAME,
    theme="a volcanic caldera where the realm's founders forged the bells' clappers: the forge-wardens' lodge at the "
          "end of the ash road, the Choir's slag pens, the Forge Gate barred on the road east, the Emberforge in its "
          "yard with the founders' anvil before its door, and beyond it the Well of Embers where the Choir sings to "
          "wake the Ember Matriarch; the Spire Road east, shut",
    environment="lava", mood="hot, droning, dread",
    areas=[AreaIdentity("road", "where the ash road from the Ashen Barrow comes into the caldera: the start"),
           AreaIdentity("lodge", "the forge-wardens' lodge and its yard", landmark="the wardens' flame basin"),
           AreaIdentity("cairns", "the Wardens' cairns, where the Choir has raised the Wardens' dead"),
           AreaIdentity("pens", "the Choir's slag pens, where the lodge's smiths dig slag in chains"),
           AreaIdentity("slag", "the slag heaps, where the fire imps nest"),
           AreaIdentity("gate", "the Forge Gate, barred by the Choir's Cantor"),
           AreaIdentity("forge", "the Emberforge and the founders' anvil before its door", landmark="the founders' anvil"),
           AreaIdentity("well", "the Well of Embers, where the Choir sings at a ring of stones", landmark="the lava well"),
           AreaIdentity("east", "the Spire Road east toward Morvaine's spire: the way on")],
    buildings=[BuildingIdentity("bunkhouse", "lodge", "the Wardens' Lodge", "Warden Hesketh and the wardens",
                                style="stone_house"),
               BuildingIdentity("store", "lodge", "the wardens' storehouse", "the quartermaster"),
               BuildingIdentity("home", "lodge", "Odda's house", "Odda and Galt")])

m = Spec(NAME, summary=ACT["title"], description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"The Hollow Choir, act 8. Generated by Claude.", author="vdystopia (generated by Claude)", version="1",
         date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
q = QuestBook(NAME)
hc = HcScript(NAME)

# ---- 1. the plan: the ash road east to the lodge, the gate, the forge and the well ------------------------------------
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"road": ((26, 150), 16), "lodge": ((74, 128), 52), "cairns": ((66, 58), 30), "pens": ((60, 206), 30),
         "slag": ((128, 206), 24), "gate": ((124, 130), 16), "forge": ((172, 122), 44), "well": ((180, 46), 52),
         "east": ((232, 140), 12)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "lodge", roughness=0.24)
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_ in (("road", "lodge", 14, True), ("lodge", "gate", 13, True), ("gate", "forge", 13, True),
                          ("forge", "well", 12, True), ("forge", "east", 12, True), ("lodge", "pens", 11, False),
                          ("pens", "slag", 10, False), ("slag", "gate", 10, False), ("lodge", "cairns", 11, False)):
    land.link(a_, b_, w_, bend=0.24, road=road_, road_material=PATH, pockets=(1, 2) if road_ else (0, 1))
d = Dresser(m, rng, land, "lava")
m.blending("RoughCobble", 7, edge="BlendEdge")
m.blending("LOTDBlackMarble", 8, edge="BlendEdge")
# the Well of Embers: lava behind black cliffs in the north of the well's clearing (the ritual's shore south of it)
well_c = land.areas["well"]["c"]
pool = d.reserve_pool(uv(186, 26), 24, stretch=1.25, angle=0.5, roughness=0.22)
# the Emberforge in its yard, its door toward the gate (placed before the land grows round it)
forge_b = d.structure("demon_forge", "forge", toward="gate", scale=1.0, name="the Emberforge")
assert forge_b, "the Emberforge found no room"

# ---- 2. the centre: the lodge's yard and its flame basin -------------------------------------------------------------
land.paint_square(m, "lodge", 9, "RoughCobble")
vc = land.areas["lodge"]["c"]
land.taken |= {(int(vc[0]) + a, int(vc[1]) + 1 + b) for a in (-1, 0, 1) for b in (-1, 0, 1)}
# the founders' strongroom: a small sealed room of the forge's stone in its yard, behind the forge (its door locked to a
# mechanism no script turns: the forge's blanks and the masterwork Flamebrand wait there for the smith)
fc_, gc_ = land.areas["forge"]["c"], land.areas["gate"]["c"]
SW_, SH_ = 12, 10                                            # uv
busy_ = land.taken_strict | land.forbidden | d.pools | land.reserved
best_ = None
for di in range(-17, 18):
    for dj in range(-17, 18):
        ci_, cj_ = fc_[0] + di, fc_[1] + dj
        if not 8 <= math.hypot(di, dj) <= land.areas["forge"]["r"] - 5: continue
        u0_, v0_ = 2 * int(round(ci_ - SW_ / 4)), 2 * int(round(cj_ - SH_ / 4))
        sq_ = {(i, j) for i in range(u0_ // 2, (u0_ + SW_) // 2) for j in range(v0_ // 2 + 1, (v0_ + SH_) // 2 + 1)}
        ring_ = {(i + a, j + b) for i, j in sq_ for a in range(-3, 4) for b in range(-3, 4)}
        if ring_ & busy_: continue
        key_ = math.hypot(ci_ - gc_[0], cj_ - gc_[1])           # behind the forge: far from the gate
        if best_ is None or key_ > best_[0]: best_ = (key_, (u0_, u0_ + SW_, v0_, v0_ + SH_), sq_)
assert best_, "no room for the founders' strongroom"
STRONG, strong_sq = best_[1], best_[2]
land.taken |= {(i + a, j + b) for i, j in strong_sq for a in range(-2, 3) for b in range(-2, 3)}
land.taken_strict |= strong_sq
land.reserved |= strong_sq
land.paint_roads(m, PATH, width_squares=2.6, skip=land.reserved)

# ---- 3. the lodge's houses round the yard ----------------------------------------------------------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"road": 8, "gate": 8, "pens": 12, "slag": 10}, square_area="lodge")
sm.connect_and_furnish(path_material=PATH)
furnished = d.furnish_structures()

# ---- 4. the land: crags breaking the ash, every way open --------------------------------------------------------------
land.carve(margin=4.0)
C = {k: land.areas[k]["c"] for k in AREAS}
road_c, pens_c, slag_c, gate_c, forge_c, east_c = (C[k] for k in ("road", "pens", "slag", "gate", "forge", "east"))
cairns_c = C["cairns"]
DOORS_SQ = [px_square(*dr.px) for _, b in placed for dr in b.entrances] + [px_square(*dr.px) for dr in forge_b.entrances]


def off_road(c, clear=3.5, reach=12, doors=5, room=0):
    """The square nearest `c` with no road within `clear` squares, on open land, `doors` squares from every door and,
    with `room`, open land all round for `room` squares: a place beside its way, not on it."""
    near_road = bfs_distance(list(land.roads), land.squares, int(clear) + 1)
    def roomy(s):
        return all((s[0] + a, s[1] + b) in land.squares and (s[0] + a, s[1] + b) not in land.taken_strict
                   for a in range(-room, room + 1) for b in range(-room, room + 1))
    cands = [s for s in land.squares if near_road.get(s, 99) >= clear and s not in land.taken_strict and
             s not in land.taken and math.hypot(s[0] - c[0], s[1] - c[1]) <= reach and
             all(math.hypot(s[0] - dd[0], s[1] - dd[1]) >= doors for dd in DOORS_SQ) and (not room or roomy(s))]
    s = min(cands, key=lambda s: math.hypot(s[0] - c[0], s[1] - c[1])) if cands else (int(c[0]), int(c[1]))
    return (s[0] + 0.5, s[1] - 0.5)


def toward(a, b, dist):
    dx, dy = b[0] - a[0], b[1] - a[1]; l_ = math.hypot(dx, dy) or 1
    return (a[0] + dx * dist / l_, a[1] + dy * dist / l_)


# the ritual's shore: between the well's pool and the road arriving from the forge
pool_c = (sum(s[0] for s in pool) / len(pool), sum(s[1] for s in pool) / len(pool))
edge_ = land.edge_distance()
# Morvaine's stand: on the shore nearest the lava, clear of the cliff; the ring of stones between him and the forge
morv_sq = min((s_ for s_, dd in edge_.items() if dd >= 3 and math.hypot(s_[0] - well_c[0], s_[1] - well_c[1]) <= 16),
              key=lambda s_: math.hypot(s_[0] - pool_c[0], s_[1] - pool_c[1]))
ring_sq = off_road(toward(morv_sq, C["forge"], 4.5), clear=2.0, reach=4, doors=6, room=3)
land.taken |= {(int(ring_sq[0]) + a, int(ring_sq[1]) + 1 + b) for a in range(-5, 6) for b in range(-5, 6)}
land.taken |= {(morv_sq[0] + a, morv_sq[1] + b) for a in range(-2, 3) for b in range(-2, 3)}
# the founders' anvil: beside the forge's door, off the road, open ground round it for the forge plate
fdoor_sq = px_square(*forge_b.entrances[0].px)
anvil_sq = off_road(toward(fdoor_sq, gate_c, 3.0), clear=2.5, reach=10, doors=3, room=3)
land.taken |= {(int(anvil_sq[0]) + a, int(anvil_sq[1]) + 1 + b) for a in range(-4, 5) for b in range(-4, 5)}
lanes = sm.keep_open({"road": 5, "pens": 7, "slag": 6, "gate": 6, "well": 4, "forge": 3, "cairns": 6})
# (few crags in the pens and the slag heaps: rays of sight between many crags crash the client, CL-1)
calm = lanes | {s for s in land.squares if math.hypot(s[0] - vc[0], s[1] - vc[1]) < 8 or
                math.hypot(s[0] - pens_c[0], s[1] - pens_c[1]) < 17 or math.hypot(s[0] - slag_c[0], s[1] - slag_c[1]) < 12}
crags = land.thickets(90, size=(1.2, 2.4), clear=1, avoid=frozenset(calm))
land.open_links()
land.apply(m, wall=d.wall, floor=d.base, unlevel=True)
d.cap_islands(crags, "VolcanicCraggy")
d.ground()
d.paint_pools()
# the Choir's camp in the slag pens: backed onto the cliff, off the path
pens_site = camps.camp_site(m, land, pens_c, reach=12, road_clear=3.0, room=7)

# the Forge Gate across the road from the gate's clearing to the forge's yard, barred; the Spire Road gate, shut
fgate_halves, fgate_pts, fgate_sq = sm.gate_across(("gate", "forge"), prefix="ForgeGate", material="Cobblestone")
sgate_halves, sgate_pts, sgate_sq = sm.gate_across(("forge", "east"), prefix="SpireGate", material="Cobblestone")

# the founders' strongroom: its walls and floor, its door toward the forge's yard, locked for good
m.room(*STRONG, wall="DunMirCathedral", floor="DunMirBrick1")
strong_tiles = set(rect_tiles(*STRONG))
for t_ in strong_tiles: m.indoor[t_] = "DunMirBrick1"
su_, sv_ = (STRONG[0] + STRONG[1]) / 2, (STRONG[2] + STRONG[3]) / 2
du_, dv_ = (fc_[0] * 2 - su_), (fc_[1] * 2 - sv_)            # uv toward the forge yard's middle
if abs(dv_) >= abs(du_):
    sgap_, sline_ = uv_to_xy(int(su_) // 2 * 2, STRONG[3] if dv_ > 0 else STRONG[2]), "\\"
else:
    sgap_, sline_ = uv_to_xy(STRONG[1] if du_ > 0 else STRONG[0], int(sv_) // 2 * 2), "/"
sdoor = m.door("DunMirDoor", tuple(int(c) for c in sgap_), sline_)
sdoor["scr"] = "Strongroom"
sdoor.setdefault("xfer", {})["LockType"] = "Mechanism"
land.wall_cells |= set(rect_wall_cells(*STRONG))
mods = None                                   # (made with the people: one Population for the whole map)

# ---- 5. the places of the story --------------------------------------------------------------------------------------
vil = Village(m, rng, land)
m.obj_px("DunMirFlameBasinLit", *square_px(vc[0], vc[1] - 0.5))
for k in range(4):
    a = k * math.pi / 2 + math.pi / 4
    m.obj_px(("Bench1", "Bench4", "Bench5", "Bench2")[k], *square_px(vc[0] + 2.6 * math.cos(a), vc[1] - 0.5 + 2.6 * math.sin(a)))
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, bunkhouse=q.text("The Wardens' Lodge\nKeepers of the Emberforge", "Sign"),
                     store=q.text("Wardens' Storehouse\nPotions and gear for the road", "Sign"))
for bid, b in placed:
    for sc_ in BUILDINGS[bid.role]["scenes"]: vil.scene(b, sc_, role=bid.role)
# the ritual's ring of stones on the Well's shore, its song-light burning violet while the Choir sings
ring_xy = camps.stone_ring(m, rng, land, ring_sq, n=6, radius=2.8, stone="ObeliskPrimitive", core=None,
                           light=d._light_xfer((150, 40, 220), 220, 70), light_name="SongLight", clear=3)
# the founders' anvil and its forge plate (a square of black marble the smith's striker stands on)
anvil_xy = square_px(*anvil_sq)
fdx, fdy = forge_b.entrances[0].px
ax_, ay_ = anvil_xy[0] - fdx, anvil_xy[1] - fdy
al_ = math.hypot(ax_, ay_) or 1
ux_, uy_ = ax_ / al_, ay_ / al_                                      # from the forge's door out to the anvil
smith_xy = (anvil_xy[0] - uy_ * 38, anvil_xy[1] + ux_ * 38)          # beside the anvil
plate_xy = (anvil_xy[0] + uy_ * 128, anvil_xy[1] - ux_ * 128)        # across from the smith, 128 px off
for pt_, r_ in ((anvil_xy, 0), (plate_xy, 0)):
    s_ = px_square(*pt_)
    assert s_ in land.squares, f"the forge's {pt_} is off the land"
m.obj_px("Anvil2", *anvil_xy, scr="S1_Anvil")
pcx, pcy = int(plate_xy[0] // 23), int(plate_xy[1] // 23)
for dx_ in range(-1, 3):
    for dy_ in range(-1, 3):
        m.tile(pcx + dx_, pcy + dy_, "LOTDBlackMarble")
for t_, off_ in (("Bellows1", (-uy_ * 70 + ux_ * 34, ux_ * 70 + uy_ * 34)), ("BarrelWithTools1", (ux_ * 70, uy_ * 70))):
    m.obj_px(t_, anvil_xy[0] + off_[0], anvil_xy[1] + off_[1])
# the Choir's camp in the slag pens: their fire and tents, the store, and the dig where the smiths work in chains
pens_camp = camps.bandit_camp(m, rng, land, pens_site, vc, loot=[("Gold", {"Amount": 60}), "RedPotion", "BluePotion",
                                                                 "Quiver"],
                              sleepers=4, tents=2, trade="dig", finds=("LavaHardened5", "Rock8", "CaveRocksMedium"))
# the slag heaps' imp nest beside the path to the gate
slag_mid = off_road(slag_c, clear=2.0, reach=8)
nest = camps.wolf_den(m, rng, land, slag_mid, pens_c)
d.clusters({"LavaHardened5": 1, "Rock8": 2, "CaveRocksMedium": 2},
           [s for s in land.squares if math.hypot(s[0] - slag_c[0], s[1] - slag_c[1]) < 9 and s not in land.taken],
           4, size=(2, 4), radius=1.3, gap=0.9, spacing=4.0)
# signposts
camps.signpost(m, land, (road_c[0] + 2.5, road_c[1] + 1.5),
               q.text("THE EMBERFORGE\nThe Wardens' Lodge is ahead. Mind the slag.", "Sign"))
gs_ = sm.road_near(((fgate_sq[0] * 2 + gate_c[0]) / 3, (fgate_sq[1] * 2 + gate_c[1]) / 3))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 1.5),
               q.text("THE FORGE GATE\nNo one passes but the Wardens.", "Sign"))
ps_ = sm.road_near(((pens_c[0] + vc[0]) / 2, (pens_c[1] + vc[1]) / 2))
camps.signpost(m, land, (ps_[0] + 1.5, ps_[1] + 1.5), q.text("SLAG PENS\nThis way to the old diggings.", "Sign"),
               kind="PlankSign2")
# the Wardens' cairns: heaps of black stone over the Wardens' dead in an arc, torn open by the Choir, bones strewn
cairn_sq = off_road(cairns_c, clear=2.0, reach=6, room=3)
csc = camps.Scene(m, rng, land, cairn_sq)
cairn_pts = []
for k in range(5):
    a_ = math.pi * (0.15 + 0.175 * k) * 2
    cx3, cy3 = csc.at(3.6, a_)
    if csc.put("CaveRocksHuge", cx3, cy3):
        cairn_pts.append(square_px(cx3, cy3))
        csc.put(("CaveRocksMedium", "CaveRocksLarge")[k % 2], *csc.at(4.5, a_ + 0.12))
for k in range(9):
    csc.put(("Skull", "LegBone", "ArmBone", "CorpseRibCageS")[k % 4], *csc.at(rng.uniform(1.2, 2.6), rng.uniform(0, 6.28)))
first_chest = csc.put("Chest3", *csc.at(4.9, math.pi * 1.95), items=[("Gold", {"Amount": 85}), "SteelShield", "RedPotion"])
camps.signpost(m, land, (cairn_sq[0] + 5.5, cairn_sq[1] + 2.5), q.text("THE WARDENS' CAIRNS\nThey kept the fire. Let them "
                                                                        "rest.", "Sign"))
# caches in the ash by the cliffs
caches = []
for near_, loot_ in ((road_c, [("Gold", {"Amount": 55}), "RedPotion", "FireProtectPotion"]),
                     (slag_c, [("Gold", {"Amount": 70}), "BluePotion", "CurePoisonPotion"]),
                     (C["east"], [("Gold", {"Amount": 45}), "RedPotion", "RedPotion"])):
    s_ = sm.hidden_spot(near_, r=(6, 14))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_))

# ---- 6. rocks, bones and red light -----------------------------------------------------------------------------------
keep_clear = {(int(vc[0]) + a, int(vc[1]) + b) for a in range(-6, 7) for b in range(-6, 7)}
n_trees, n_small = d.vegetate(keep_clear=keep_clear, groves=2)
n_liq = d.dress_liquid()
d.scatter_open(scale=0.5)
d.rim(scale=0.6)
n_lights = d.lights(scale=1.1)
piles = d.planter.rock_piles(max(4, len(land.squares) // 1000))
start_xy = square_px(road_c[0] + 0.5, road_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
exit_next(sm, "east", 8, prefix="SpireExit")

# ---- 7. the people ---------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
mods = Mods(m, pop)
vx, vy = square_px(*vc)
person = sm.person
# Warden Hesketh at the lodge's door, Doran in the yard by the basin, Odda at her door
hx_, hy_ = sm.doorside("bunkhouse", toward=(vx, vy)) or square_px(vc[0] + 3, vc[1])
person("Con03A", "Lance", hx_, hy_, "Hesketh", face=(vx, vy))
dx_, dy_ = square_px(vc[0] - 2.4, vc[1] + 2.0)
cast_person(sm, "Doran", dx_, dy_, face=(vx, vy))
ox_, oy_ = sm.doorside("home", toward=(vx, vy)) or square_px(vc[0], vc[1] - 3)
person("Con02a", "Lydia", ox_, oy_, "Odda", face=(vx, vy))
# Doran at the founders' anvil: there from the start, out of the play (disabled) until the Forge Gate opens
person(CAST["Doran"]["donor"][0], CAST["Doran"]["donor"][1], *smith_xy, "DoranAnvil", face=anvil_xy)
# Galt and Fenn at the Choir's dig in chains; the overseers at their posts round the camp
pens_posts = camp_posts(m, pens_camp, square_px(*vc), sit=2, tents=1, watch=1, work=2)
(gx_, gy_), (fx_, fy_) = pens_posts["work"][:2]
person("Con03B", "Naldo", gx_, gy_, "Galt", face=pens_camp["fire"])
person("Con03B", "Logan", fx_, fy_, "Fenn", face=pens_camp["fire"])
# home: the yard by the basin, on the side of Odda's house (a journey ends at the first free spot round its end)
hdx_, hdy_ = ox_ - vx, oy_ - vy
hl_ = math.hypot(hdx_, hdy_) or 1
hdx_, hdy_ = hdx_ / hl_, hdy_ / hl_                                  # from the basin toward Odda's door
galt_home = sm.journey("Galt", "GaltHome", (vx + hdx_ * 120 - hdy_ * 50, vy + hdy_ * 120 + hdx_ * 50), look=(ox_, oy_))
fenn_home = sm.journey("Fenn", "FennHome", (vx + hdx_ * 120 + hdy_ * 50, vy + hdy_ * 120 - hdx_ * 50), look=(ox_, oy_))
WARES = {"store": [(5, "RedPotion"), (3, "BluePotion"), (3, "FireProtectPotion"), (2, "CurePoisonPotion"),
                   (2, "Quiver"), (1, "LeatherArmoredBoots"), (1, "ChainCoif"), (1, "SteelShield")]}
GREET = {"store": q.text("Potions, mostly. The Choir took the rest! What do you need?", "Shop")}
n_shops = sm.shops(WARES, GREET)
# Corra, an old warden, at the lodge's end of the path to the cairns
cr_sq = off_road(toward(vc, cairns_c, 8.0), clear=1.5, reach=5, doors=4)
person("Con02a", "Gretchen", *square_px(*cr_sq), "Corra", face=square_px(*cairns_c))
sm.keep_folk_away(pens_c, 14)
sm.keep_folk_away(slag_c, 12)
sm.keep_folk_away(anvil_sq, 4)
FOLK = [("Con03A", "Millard"), ("Con02a", "Tanya"), ("Con02a", "Clyde"), ("Con08a", "Gretchen")]
RUMOURS = ["Hear that hum in the rock? That's them. Singing. Day and night.",
           "The Cantor at the Forge Gate won't move off it. Kill him and the bar drops. That's how they rig it.",
           "Out of my way, wanderer! I've buckets to haul.",
           "Imps nest in the slag heaps south of the road. Little things, but they bite like coals!"]
sm.townsfolk(FOLK, vc, q=q, rumours=RUMOURS,
             after=("matriarch_down", "It's quiet in the rock tonight. I'd forgotten how quiet."),
             pics=("MalePic1", "MaidenPic3", "MalePic7", "MaidenPic"), radius=7.0)

# ---- 8. the fights ---------------------------------------------------------------------------------------------------
# the fire imps of the slag heaps, who swarm whoever passes on the path
nest_imps = []
for k, (x, y) in enumerate(nest[:4]):
    n = f"SlagImp{k + 1}"
    pop.creature("Imp", x, y, action="idle", scr=n, aggr=0.5, sight=90)
    nest_imps.append(n)
# the Forge Gate: its Cantor (a Bone Caller) with the Choir's blades before the bar
gate_xy = square_px(fgate_sq[0] + 0.5, fgate_sq[1] - 0.5)
gcx, gcy = square_px(*toward(fgate_sq, gate_c, 3.5))
mods.monster("M3", gcx, gcy, name="GateCantor", hp=340, wait=260, face=square_px(*gate_c))
gate_band = []
for k, (t_, a_) in enumerate((("Swordsman", 0.9), ("Swordsman", -0.9), ("Archer", 2.6))):
    gx2, gy2 = square_px(*toward(fgate_sq, gate_c, 4.5))
    n = f"GateBlade{k + 1}"
    pop.creature(t_, gx2 + 70 * math.cos(a_), gy2 + 70 * math.sin(a_), action="guard", scr=n, aggr=0.83,
                 face=square_px(*gate_c))
    gate_band.append(n)
B.sentry("GateBlade3", square_px(*gate_c), rouse=gate_band[:2], shout="Hold! The Choir sings here!")
# the slag pens: the overseer by the take, the blades at the fire, the tents and the way in
overseers = []
pop.creature("Swordsman", *pens_posts["leader"], action="guard", scr="Overseer", aggr=0.83, HealthMultiplier=2.0,
             face=square_px(*vc))
overseers.append("Overseer")
for k, (x, y) in enumerate(pens_posts["sit"] + pens_posts["tent"] + pens_posts["watch"]):
    n = f"PenGuard{k + 1}"
    pop.creature("Archer" if k == len(pens_posts["sit"]) + len(pens_posts["tent"]) else "Swordsman", x, y,
                 action="guard", scr=n, aggr=0.83, face=square_px(*vc))
    overseers.append(n)
B.sentry(overseers[-1], square_px(*vc), rouse=overseers[:-1], shout="Back to the slag, you dogs! Intruder!")
# the risen Wardens at their cairns: the Choir sang them up; the First Warden stands by his chest
risen = []
pop.creature("SkeletonLord", *csc.px(2.6, math.pi * 1.95), action="guard", scr="FirstWarden", aggr=0.83,
             HealthMultiplier=1.5, face=square_px(*vc))
risen.append("FirstWarden")
for k, (x, y) in enumerate(cairn_pts[:4]):
    n = f"RisenWarden{k + 1}"
    pop.creature("Skeleton", x + 30, y + 30, action="guard", scr=n, aggr=0.83, face=square_px(*vc))
    risen.append(n)
# the forge's own keepers inside (the fire-things the song woke)
d.population = pop
n_garrison = d.garrison()
# the Well: Morvaine behind the ring on the shore (warded, still: he is fought in act 9), the two Cantors at the ring,
# the Choir's blades round it
rcx, rcy = ring_xy
morv_xy = square_px(morv_sq[0] + 0.5, morv_sq[1] - 0.5)
mux, muy = (morv_xy[0] - rcx), (morv_xy[1] - rcy)
ml_ = math.hypot(mux, muy) or 1
mux, muy = mux / ml_, muy / ml_                                     # from the ring toward the lava
pop.creature("Necromancer", *morv_xy, action="idle", scr="Morvaine", aggr=0.0, Immortal=True, face=(rcx, rcy),
             spread=False)
hc.freeze("Morvaine")
cantors = []
for k, sgn in enumerate((1, -1)):
    cx2, cy2 = rcx - muy * 72 * sgn + mux * 20, rcy + mux * 72 * sgn + muy * 20
    n = f"Cantor{k + 1}"
    mods.monster("M3", cx2, cy2, name=n, hp=320, wait=300, face=(rcx - mux * 100, rcy - muy * 100))
    cantors.append(n)
well_band = []
for k, (t_, a_) in enumerate((("Swordsman", 2.2), ("Swordsman", 4.1), ("Archer", 3.15))):
    ang = math.atan2(-muy, -mux) + (a_ - 3.15) * 0.55
    n = f"WellBlade{k + 1}"
    pop.creature(t_, rcx + 150 * math.cos(ang), rcy + 150 * math.sin(ang), action="guard", scr=n, aggr=0.83,
                 face=(rcx - mux * 300, rcy - muy * 300))
    well_band.append(n)
# the Matriarch sleeps under the Well (out of the play) until the song breaks; she rises in the ring, and only then
# does she become the Ember Matriarch (kit/mods M4, registered by hc_scripts.go when she rises: a lesser rising, about
# three eighths of the health she has in act 10)
rise_xy = (rcx + mux * 30, rcy + muy * 30)
MATRIARCH_HP = FOES["Matriarch"]["hp"] * 3 // 8
pop.creature("EmberDemon", *rise_xy, action="idle", scr="Matriarch", aggr=0.83, face=(rcx - mux * 200, rcy - muy * 200),
             spread=False)
# the caldera's own creatures by the cliffs, well away from the lodge and the story's places (never a Zombie)
sm.wild({"Imp": 2, "EmberDemon": 1, "Skeleton": 2}, away_from=vc,
        avoid=(road_c, pens_c, slag_c, gate_c, forge_c, ring_sq, east_c, anvil_sq, cairns_c, fgate_sq),
        per100=0.25, min_away=25)
story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]
            if px_square(o["x"], o["y"]) in land.squares] + [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)

# ---- the founders' anvil: the forge (kit/mods S1) with Doran as its smith, its blanks in the strongroom ------------
mods.calls.append(f'ModForge("S1_Anvil", {plate_xy[0]:.1f}, {plate_xy[1]:.1f}, "DoranAnvil")')
slot = 0
for key in ("longsword", "battleaxe"):
    L_ = FORGE_LINES[key]
    names_ = []
    for t in (1, 2, 3):
        tn = []
        for c_ in range(2):
            nm = f"Forge_{key}_{t}_{c_ + 1}"
            x_ = {"Enchantments": _ench(L_["tiers"][t])} if L_["tiers"][t] else {}
            m.obj_px(L_["base"], *px(STRONG[0] + 1 + 2 * (slot % 5), STRONG[2] + 3 + 2 * (slot // 5)), scr=nm,
                     **({"xfer": x_} if x_ else {}))
            slot += 1
            tn.append(nm)
        names_.append(tn)
    mods.forge_line(key, L_["label"], L_["base"], "", [], *names_)
# the masterwork Flamebrand Doran forges from the starsteel (W1 at tier 3)
mods.weapon("W1", *px(STRONG[0] + 1 + 2 * (slot % 5), STRONG[2] + 3 + 2 * (slot // 5)), tier=3, name="Flamebrand3")

# ---- 9. the story ----------------------------------------------------------------------------------------------------
MAIN = "Break the Choir's song at the Well of Embers, beyond the Emberforge."
BLADE = "Bring the starsteel to Doran at the founders' anvil."
q.start([A.lock("ForgeGate1"), A.lock("ForgeGate2"), A.lock("Strongroom"), A.lock("SpireGate1"), A.lock("SpireGate2"),
         A.disable("SpireExit1"), A.disable("SpireExit2"), A.disable("SpireExit3"), A.disable("DoranAnvil"),
         A.disable("Matriarch"),
         q.journal("Follow the ash road east to the Wardens' Lodge.", HINT)])
q.on_pickup(LETTER, [A.flag("letter")])
# the hum in the rock on the way in; the imps of the slag heaps
nx_, ny_ = square_px(*slag_mid)
q.near(nx_, ny_, 200, [A.hunt(n) for n in nest_imps] + [A.print("Shrieks from the slag! Fire imps boil out of the "
                                                                "heap.")])
q.near(*square_px(*toward(road_c, vc, 6.0)), 140, [A.print("The ground hums under your boots. Somewhere ahead, "
                                                           "many voices are singing.")])
# the Forge Gate: the Cantor's death drops the bar; Doran goes to the anvil
q.near(gcx, gcy, 330, [A.print("A robed figure stands before the barred gate, singing. Bones stir round his feet.")])
q.on_death("GateCantor", [A.flag("gate_open"), A.unlock("ForgeGate1"), A.unlock("ForgeGate2"), A.disable("Doran"),
                          A.enable("DoranAnvil"),
                          A.print("The Cantor falls, and his song with him. With a clang the bar of the Forge Gate "
                                  "drops."),
                          q.journal("Go through the Forge Gate to the Well of Embers.", QUEST)])
# the Well: the song, the breaking, the rising
q.near(rcx, rcy, 420, [A.chat("Morvaine", "Sing, my Cantors! She is listening!"),
                       A.print("Voices rise from the shore of the Well. Behind a ring of stones, a figure in black "
                               "raises two glowing stones over the lava.")])
q.on_all_dead(cantors, [A.flag("ritual_broken"), A.disable("SongLight"),
                        A.chat("Morvaine", "Too late, sellsword. She has heard us. Come to my spire if you want "
                                           "the rest of them."),
                        A.print("The song breaks off. The lava in the Well heaves and splits..."),
                        q.journal("Kill the Ember Matriarch before she wakes in full.", QUEST)])
hc.on_flag("ritual_broken", hc.vanish("Morvaine"), hc.rise("Matriarch", *rise_xy),
           [f'ModBoss("embermother", "Matriarch", "The Ember Matriarch", {MATRIARCH_HP}, 0, 0)'],
           hc.say("Morvaine is gone in a burst of smoke. Something vast climbs out of the Well of Embers!"))
q.on_death("Matriarch", [A.flag("matriarch_down"), A.unlock("SpireGate1"), A.unlock("SpireGate2"),
                         A.enable("SpireExit1"), A.enable("SpireExit2"), A.enable("SpireExit3"),
                         A.print("The Ember Matriarch shrieks and sinks back into the fire. The mountain goes still. "
                                 "Far to the east, the Spire Road gate grinds open."),
                         q.done(MAIN), q.journal("Follow Morvaine east along the Spire Road to his spire.", QUEST)])
for n_ in cantors + ["GateCantor", "Matriarch"]:
    q.names.add(n_)
# Warden Hesketh: the main quest
q.talker("Hesketh", [
    q.say("Back from the Well, and in one piece! Here -- the Wardens' purse, what the Choir left of it. Morvaine "
          "went east, up the Spire Road. The gate there is open now.",
          when=q.when(flag="matriarch_down", not_="hesketh_paid"),
          do=[A.flag("hesketh_paid"), A.gold(250), A.give("RedPotion", 3), A.give("FireProtectPotion", 2)],
          who="Hesketh"),
    q.say("The rock is still. The Wardens will keep the forge again, thanks to you.", when=q.when(flag="hesketh_paid"),
          who="Hesketh"),
    q.say("She's up? Then put her down again! Hurry, before she gets her strength!",
          when=q.when(flag="ritual_broken"), who="Hesketh"),
    q.say("The gate's open! Through the forge yard to the Well. Break their song!", when=q.when(flag="gate_open"),
          who="Hesketh"),
    q.say("The Cantor still stands before the Forge Gate. Nothing moves until he falls.", when=q.at("main", 1),
          who="Hesketh"),
    q.say("Off the ash road at last, and not a moment too soon! The Hollow Choir holds the Emberforge.\n\n"
          "Their Cantor has barred the Forge Gate east of here. Past the forge, at the Well of Embers, Morvaine and "
          "his singers call to the Ember Matriarch with the stones they stole. The whole mountain hums with it.\n\n"
          "Kill the Cantor at the gate and the bar drops. Then go to the Well and stop that song.",
          do=[A.stage("main", 1), q.journal(MAIN)], who="Hesketh")])
# Doran at the lodge: what he came for, by what the player carries
q.talker("Doran", [
    q.say("Starsteel! You found it in the deep after all! The founders' anvil is past the Forge Gate. Get that gate "
          "open and I'll be at the anvil before you.", when=q.when(has=STEEL, not_="blade_told"),
          do=[q.journal(BLADE), A.flag("blade_told")], who="Doran"),
    q.say("Keep that lump safe till the gate's open. Don't go losing it in the slag!", when=q.when(has=STEEL),
          who="Doran"),
    q.say("Still wearing my guild medallion? Good lad. The starsteel's the thing, though. No starsteel, no blade.",
          when=q.when(flag="letter"), who="Doran"),
    q.say("Brackwater's a long walk behind me. I came for the founders' anvil -- the one anvil hot enough for the "
          "old steel. The Choir got here first. Open the Forge Gate and I'll get the fire going.", who="Doran")],
    title=CAST["Doran"]["title"], voice=voice("Doran"))
# Doran at the founders' anvil: the Starsteel Blade, or plain steel for gold
q.talker("DoranAnvil", [
    q.say("Swing it once, just once, and watch the fire go round you. That's founders' work!",
          when=q.when(flag="blade_forged"), who="DoranAnvil"),
    q.say("My medallion, and the starsteel with it! This is the anvil it was meant for. Give it here and I'll make you "
          "the finest blade Brackwater ever sent out. Shall I forge it?",
          when=q.when(has=STEEL, flag="letter"), ask=True,
          do=[A.take(STEEL), A.flag("blade_forged"), A.print("Doran works the starsteel on the founders' anvil. The "
                                                             "forge roars."),
              q.done(BLADE)],
          else_=[q.tell("DoranAnvil", "Then I'll wait. The anvil's not going anywhere.")], who="DoranAnvil"),
    q.say("Starsteel, and a fine lump! Never mind where my medallion got to. Give it here and I'll make you a blade "
          "worth the walk. Shall I forge it?",
          when=q.when(has=STEEL), ask=True,
          do=[A.take(STEEL), A.flag("blade_forged"), A.print("Doran works the starsteel on the founders' anvil. The "
                                                             "forge roars."),
              q.done(BLADE)],
          else_=[q.tell("DoranAnvil", "Then I'll wait. The anvil's not going anywhere.")], who="DoranAnvil"),
    q.say("The anvil's hot again! Lay a blade beside it and stand on the black plate. I'll do the rest -- for a fee, "
          "mind.", who="DoranAnvil")],
    title=CAST["Doran"]["title"], voice=voice("Doran"))
hc.on_flag("blade_forged", hc.hand_over("Flamebrand3", "DoranAnvil"))
# Odda and the Chained Smiths
q.talker("Odda", q.errand(
    "Odda", "smiths",
    offer="Oh, please, help me! The Choir took my Galt and his brother Fenn, the Lodge's smiths. They dragged them "
          "off in chains to the slag pens south-west of here.\n\nThey make them dig the slag those devils burn in "
          "their song. Fenn's arm was broken already!\n\nWould you go and free them? I'll give you whatever we have "
          "left.",
    reminder="Have you been to the pens? Oh, every hour they're down there...",
    thanks="Galt! He's coming up the path, I can see him! Fenn too, the stubborn fool!\n\nHere. It's not much, but "
           "it's yours. Thank you, thank you!",
    after="Galt says he'll never dig another bucket of slag. We'll see.",
    objective="Free Galt and Fenn from the Choir's slag pens.",
    done=q.when(flag="smiths_free"),
    reward=[A.give("ChainLeggings"), A.give("FireProtectPotion", 2), A.gold(90)],
    refusal="Then I'll go myself, and they can chain me too!"))
q.talker("Galt", [
    q.say("Home, then. Fenn, up! Mind the arm.", when=q.when(flag="smiths_free"), who="Galt"),
    q.say("The overseers are dead? All of them? You beautiful madman! Fenn, drop that bucket -- we're going home to "
          "Odda!",
          when=q.when(flag=q.dead(*overseers), not_="smiths_free"),
          do=[A.flag("smiths_free"), A.walk("Galt", galt_home), A.walk("Fenn", fenn_home),
              q.note("Galt and Fenn are free and walking home to the Lodge.")], who="Galt"),
    q.say("Get away from here, they'll see you! There's too many of them!", who="Galt")])
q.talker("Fenn", [
    q.say("Free! Ha! My arm's still broken, but I'm free!", when=q.when(flag="smiths_free"), who="Fenn"),
    q.say("Don't talk to me. Talk to my brother. The overseer has eyes in his head.", who="Fenn")])
# Corra and the risen Wardens
q.talker("Corra", q.errand(
    "Corra", "cairns",
    offer="My Aldo's bones are walking. Walking! The Choir's singers came by the cairns north of the Lodge and sang "
          "our dead up out of the stones.\n\nThe First Warden too, in his old mail. They stand there now and wait "
          "for orders.\n\nLay them down for me, would you? The First Warden's chest is yours if you do.",
    reminder="They'll stand there till the stones wear away, poor dead things.",
    thanks="Quiet. You can hear it, can't you? No more scraping on the stones.\n\nGo and take what's in the First "
           "Warden's chest, as I said. And this, from me.",
    after="I sit with Aldo in the evenings again. Just his cairn now. That's how it should be.",
    objective="Destroy the risen Wardens at the cairns north of the Lodge.",
    done=q.when(flag=q.dead(*risen)), reward=[A.give("BluePotion", 2), A.give("RedPotion", 2), A.gold(60)],
    refusal="Then I'll sit here and listen to them scrape."))
q.near(*csc.px(0, 0), 260, [A.print("Bones clatter between the cairns. Things in rusted mail turn to face you.")])
for who_, pic_ in (("Corra", "MaidenPic4"), ("Hesketh", "Warrior3Pic"), ("Doran", "QuarterMasterPic"), ("DoranAnvil", "QuarterMasterPic"), ("Odda", "MaidenPic2"),
                   ("Galt", "MalePic5"), ("Fenn", "MalePic9")):
    q.portrait(who_, pic_)

mods.attach(B)
m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())
m.scripts.update(hc.files())

# the exteriors' dressing: composed groups of the place's things on the empty ground (kit/dressing.py)
from kit.dressing import Exterior
dressed = Exterior(m, land, "lava", placed=placed).dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    keep_ids = [(BuildingIdentity(role, area, nm, "the Choir's fire-things"), b) for role, area, b, nm in d.structures]
    rooms_sidecar(placed + keep_ids, os.path.join(OUT, f"{NAME}.rooms.json"))
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS", "VOICE"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| forge {'yes' if forge_b else 'NO'} garrison {n_garrison} | rocks {n_trees} | on lava {n_liq} | shops {n_shops} "
          f"| caches {len(caches)} | opened {len(opened)} | lines {len(q.strings)} | dressing {sum(dressed.values())}")
