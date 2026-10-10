"""The Hollow Choir, act 3: the Greycrag mines (map Greycrag). A miners' town in the great cavern under the Greycrag
hills, where the Choir digs for the second bell, sunk in the flooded deep (campaign/hollowchoir/BIBLE.md; cave palette,
kit/biome.py BIOMES["cave"], with a mine head (kit/mine.py) and a lift (kit/transport.py) as ironcrag.py and
deepvault.py have them).

The town: stone and log houses round the pithead yard under the old mine's rock face; beside the tunnel's mouth the
Deep Lift, the company's shaft down to the Low Workings; the mine forge in its yard north of the town, where Garran
Ashforge, Doran's cousin, keeps the anvil; the glimmer grotto of blue crystal in the north-west; the black lake in the
south; the High Road gate north on the road to Frosthollow.

The transporter, to a place of its own drawn walled off in the east of the grid (it cannot be walked to):
- The Deep Lift (lift, mine style: Elevator and its pit; laid switched OFF): from the pithead yard down to the Low
  Workings, where the Choir digs. Why: the main quest. Pike the liftman chained its brake when dead men came up it;
  once Overseer Brenna sends the player down he knocks the chain off (A.enable) and the lift runs from then on, both
  ways. Below: the Low Workings (the Choir's dig camp at the shaft's foot), the drowned gallery that runs down into
  the flooded deep (Giant Crabs in the black water, the starsteel seam in a side pocket) and, at its bottom, the old
  bell shrine where the second bell lies drowned, its Spirit Stone and the founders' tablet. The way back is the lift.

The story
- The player comes up the causeway from the Mirewood, following the Choir's map, into the cavern from the west. Tull
  the carter, stopped at the cavern mouth, takes the player for one of the Choir at first; he sends them to the
  Overseer.
- Main quest, the Second Bell: a fortnight ago the Choir came up the causeway with gold and a string of dead men from
  the Mirewood and took the Deep Lift for itself; it digs in the Low Workings toward the flooded deep, where Greycrag's
  old story says the second bell went down when the deep flooded. Overseer Brenna has barred the High Road so nothing
  the Choir digs up leaves Greycrag. She sends the player down; Pike starts the lift. Below: Digmaster Gant and the
  Choir's diggers (hired blades and the drowned dead, set to dig), then the Giant Crabs (the new monster M2) in the
  flooded deep. In the bell shrine the player takes the bell's clapper, its Spirit Stone (token SPIRIT_STONE, a red
  stone that hums, the first the player holds). With the stone in hand and Gant dead, Brenna opens the High Road (the exit, to Frosthollow,
  act 4) and pays; the stone stays with the player.
- The Last Verse (Edric's cross-map side quest): the founders' tablet in the bell shrine gives a VERSE_STONE (a blue
  stone set below the tablet's words, the verse worn into it). Given once (a WhenTrue reads a carried verse back after
  a saved game, before the tablet's trigger). Edric's ask is not carried (kit/campaign.py), so nothing is read for it.
- The Starsteel Blade (Doran's cross-map side quest): Garran Ashforge at the mine forge knows Doran's guild medallion
  (DORAN_LETTER) and asks for starsteel from the flooded deep; without the medallion he asks a stranger all the same.
  The starsteel (token STARSTEEL, a red-glinting lump) lies in the seam among the crabs. Shown it, Garran says only the
  founders' forge, where the bells were cast, can work it; the player keeps it (act 8 forges it).
- The Eye in the Grotto (local side quest): a Beholder came up through the floor of the glimmer grotto and the cutters
  will not work it. Nim, a glimmer-cutter, pays with the best stone she ever cut.
- The mine forge (S1, kit/mods.py): lay a longsword or a battle axe by the anvil and stand on the forge plate; Garran's
  journeyman works it, tier by tier, for gold. The company store, the Sunk Bell inn and the smithy buy and sell; the
  Choir's chest, three caches and the houses' stores hold loot.

Tokens: gives SPIRIT_STONE and STARSTEEL (placed items, picked up once) and VERSE_STONE (once, at the tablet); reads
DORAN_LETTER (Garran's lines). A player with an empty pack finishes the act.

    py mapgen/designs/hc03_greycrag.py [seed]
"""
QA_ACCEPT = [   # (tests/qa.py)
    ("composition", r"is sparse: furniture covers",
     "the town's houses are the kit's own (generate_building + the furnisher at master 2026-10-09): every seed of 8 "
     "tried left five to seven house rooms under the half-median house rule, as every map rebuilt at master does "
     "(Ironcrag, Thornwick); the room lab's work, not this map's"),
    ("composition", r"bunched into one part of the room \(offset 1\.54",
     "a bedroom of the kit's furnisher (seed 3 had the fewest warnings and no errors of the 8 seeds tried; seeds 2 and 6 "
     "broke the town's ways, seed 8 the sight limit); the room picture reads as a bedroom"),
    ("composition", r"Bookcase1 and PotionShelves1 stand 1\.2 units apart",
     "the company store's shelves as the kit's furnisher lines them; a room-lab matter"),
    ("composition", r"tavern room: 4 chairs drawn up to nothing",
     "the Sunk Bell's stools along its bar as the kit's furnisher lays a tavern; a room-lab matter"),
]
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL, px
from kit.identity import MapIdentity, AreaIdentity, BuildingIdentity, BUILDINGS, rooms_sidecar
from kit.layout import Land, square_tile, square_px, px_square, bfs_distance
from kit.biome import Dresser
from kit.village import Village
from kit.mine import MineEntrance
from kit.quests import QuestBook, A, QUEST, COMPLETED, HINT, NOTE
from kit.transport import Transporters
from kit.posts import camp_posts
from kit.story import StoryMap, STOCK
from kit.mods import Mods, FORGE_LINES, _ench
from kit.npcs import facing
from kit.campaign import act, token, has, exit_next
from kit import camps

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 3
rng = random.Random(SEED)
ACT = act(3)
NAME = ACT["map"]                                  # Greycrag
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", ACT["design"])
PATH = "ManaMineDirt"                               # the trodden ways: ore dust tramped into the cave floor
FAR_X = 176                                        # cells: the grid east of this is the far places' (never the town's)
STONE, VERSE, STEEL = token("SPIRIT_STONE"), token("VERSE_STONE"), token("STARSTEEL")
LETTER = token("DORAN_LETTER")                      # Doran's guild medallion
GLIMMER = "Diamond"                                 # Nim's best stone


def uv(X, Y):
    """uv of a point given in map squares as seen on screen (X right, Y down, 0..255)."""
    return (X + Y, X - Y)


def P(X, Y):
    """World px of a map cell point."""
    return (X * CELL, Y * CELL)


def sq_of(X, Y):
    """Continuous square coordinates (for square_px and camps.Scene) of a map cell point."""
    return ((X + Y - 1) / 2, (X - Y - 1) / 2)


ID = MapIdentity(
    name=NAME,
    theme="a miners' town in the great cavern under the Greycrag hills: houses round the pithead yard under the old "
          "mine's rock face, the Deep Lift beside its mouth, the mine forge in its yard, a glimmer grotto of blue "
          "crystal, a black lake, the High Road gate barred; below, reached only by the lift, the Choir's dig in the "
          "Low Workings, the flooded deep where the crabs live and the drowned bell shrine",
    environment="town", mood="dark, close, watchful",
    areas=[AreaIdentity("west", "the cavern mouth where the causeway from the Mirewood comes in: the start"),
           AreaIdentity("town", "the pithead yard and the houses round it", landmark="the Deep Lift"),
           AreaIdentity("forge", "the mine forge's yard north of the town"),
           AreaIdentity("grotto", "the glimmer grotto of blue crystal, where the Eye came up"),
           AreaIdentity("lake", "the black lake in the south of the cavern", landmark="the black lake"),
           AreaIdentity("gate", "the High Road gate, barred"),
           AreaIdentity("north", "the High Road north toward Frosthollow: the way out")],
    buildings=[BuildingIdentity("foreman", "town", "the Overseer's hall", "Overseer Brenna"),
               BuildingIdentity("store", "town", "the company store", "the storekeeper"),
               BuildingIdentity("inn", "town", "The Sunk Bell", "the innkeeper"),
               BuildingIdentity("smithy", "town", "the smithy", "the smith"),
               BuildingIdentity("bunkhouse", "town", "the bunkhouse", "the miners", style="stone_house"),
               BuildingIdentity("home", "town", "Nim's house", "Nim the glimmer-cutter", style="stone_house")])

m = Spec(NAME, summary="The Greycrag Mines", description=f"[env:{ID.environment}] {ID.theme[0].upper() + ID.theme[1:]}. "
         f"The Hollow Choir, act 3. Generated by Claude.", author="vdystopia (generated by Claude)", version="1",
         date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
q = QuestBook(NAME)
presets = json.load(open(os.path.join(HERE, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]


def preset(family, intensity="full"):
    ps = [p for p in presets if p["family"] == family and p["intensity_class"] == intensity] or \
         [p for p in presets if p["family"] == family]
    return dict(max(ps, key=lambda p: p["weighted_share"])["xfer"])


# ---- 1. the plan: the cavern mouth to the pithead yard, the ways to the forge, the grotto, the lake and the High Road -
land = Land(rng, u_range=(24, 488), v_range=(-232, 232))
AREAS = {"west": ((22, 132), 16), "town": ((86, 128), 64), "forge": ((116, 70), 16), "grotto": ((42, 60), 26),
         "lake": ((76, 210), 30), "gate": ((146, 62), 12), "north": ((156, 26), 12)}
for k_, ((X_, Y_), r_) in AREAS.items():
    land.area(k_, uv(X_, Y_), r_, clearing=k_ != "town", roughness=0.24)
    ar = land.areas[k_]
    x_, y_ = ar["c"][0] + ar["c"][1], ar["c"][0] - ar["c"][1]
    assert 12 + ar["r"] <= x_ <= 243 - ar["r"] and 12 + ar["r"] <= y_ <= 243 - ar["r"], (k_, x_, y_)
for a_, b_, w_, road_ in (("west", "town", 14, True), ("town", "forge", 12, True), ("forge", "gate", 12, True),
                          ("gate", "north", 12, True), ("town", "grotto", 11, False), ("grotto", "forge", 10, False),
                          ("town", "lake", 11, False)):
    land.link(a_, b_, w_, bend=0.24, road=road_, road_material=PATH, pockets=(1, 2) if road_ else (0, 1))
d = Dresser(m, rng, land, "cave")
m.blending("RoughCobble", 7, edge="BlendEdge")
# the east of the grid is the far places': the town's land never grows there
land.forbidden |= {(i, j) for i in range(0, 260) for j in range(-130, 130) if i + j + 1 >= FAR_X}
# the black lake behind low cliffs in its own cavern, a dead end
lake_c0 = land.areas["lake"]["c"]
lake = d.reserve_pool((lake_c0[0] * 2 + 4, lake_c0[1] * 2 - 4), 14, stretch=1.2, angle=0.6, roughness=0.25)

# ---- 2. the centre: the pithead yard, the old mine's rock face on its north-west side, the Deep Lift by its mouth ----
land.paint_square(m, "town", 11, "RoughCobble")
vc = land.areas["town"]["c"]
mine = MineEntrance(land, set(land.plaza), (-1, 0), rng, depth=11, width=3, gap=4, reach=4, rock=12)
mine.plan()
lm = mine.lm
LIFT_OL = (-2.2, lm + 4.2)                       # the Deep Lift: in the forecourt, beside the tunnel's mouth
lift_xy = mine.px(*LIFT_OL)
lift_sq = px_square(*lift_xy)
land.taken |= {(lift_sq[0] + a, lift_sq[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1)}
land.paint_roads(m, PATH, width_squares=2.6, skip=land.reserved)

# ---- 3. buildings from the yard outwards ------------------------------------------------------------------------------
sm = StoryMap(m, rng, land, ID)
placed = sm.place_buildings(no_build={"west": 8, "forge": 9, "grotto": 12, "lake": 12, "gate": 7})
sm.connect_and_furnish(path_material=PATH)

# ---- 4. the land: pillars break the cavern, every way open --------------------------------------------------------
land.carve(margin=4.0)
mine.cut()
C = {k: land.areas[k]["c"] for k in AREAS}
west_c, forge_c, grotto_c, lake_c, gate_c, north_c = (C[k] for k in ("west", "forge", "grotto", "lake", "gate", "north"))
lanes = sm.keep_open({"west": 5, "forge": 6, "grotto": 8, "lake": 5})
calm = lanes | {s for s in land.squares if math.hypot(s[0] - vc[0], s[1] - vc[1]) < 9}
crags = land.thickets(80, size=(1.2, 2.4), clear=1, avoid=frozenset(calm))
land.open_links()
land.apply(m, wall=d.wall, floor=d.base, unlevel=True)
d.cap_islands(crags)
d.ground()
d.paint_pools()
mine.ground(m, track=PATH)
# the houses' floors meet the cave floor under their walls: the cave floor's edge lies over them there (as Deepvault's
# WoodGray2; Westwood blends the cave floors over its house floors)
for f_ in ("WoodGray2", "GalavaBrick2"):
    if f_ not in m.blend: m.blending(f_, -1)
gate_halves, gate_pts, gate_sq = sm.gate_across(("gate", "north"), prefix="HighGate", material="DungeonStone")


# ---- the far place: the Low Workings, the drowned gallery and the bell shrine, walled off east of the town ----------
def cave(circles, capsules=(), wall="CaveWall", floor="DirtDark2"):
    """A walled-off place of its own: the squares within the circles [(X, Y, r) in cells] and along the capsules
    [((X0, Y0), (X1, Y1), half width)], walled round (a Land of its own, so the town's planting and dressing never
    reach it), as ironcrag.py draws its far places. Returns the Land."""
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


LOW, LOW_PIT, BEND, ORE, BELL = (200, 50), (192, 42), (206, 96), (227, 86), (212, 132)
deep = cave([(*LOW, 13), (*ORE, 6.5), (*BELL, 12)],
            [((198, 54), BEND, 4.6), (BEND, (225, 87), 3.4), (BEND, BELL, 4.8)],
            wall="ManaMineWall", floor="ManaMineDirt")
# the flood: black water filling the gallery below the bend and the bell shrine's floor round its dais
flood = {s for s in deep.squares
         if (s[0] + s[1] + 1 >= 0 and (s[0] - s[1] + 1) >= 90 and
             math.hypot(s[0] + s[1] + 1 - BELL[0], s[0] - s[1] + 1 - BELL[1]) > 6.5)}
for s in flood:
    m.floor[square_tile(*s)] = "Water"
deep.water |= flood
# the bell shrine's dais: old founders' paving round the altar, dry above the flood
for s in deep.squares:
    X_, Y_ = s[0] + s[1] + 1, s[0] - s[1] + 1
    if math.hypot(X_ - BELL[0], Y_ - BELL[1]) <= 5.5:
        m.floor[square_tile(*s)] = "RoughCobble"
pit_xy = P(*LOW_PIT)

# ---- 5. the town's life ------------------------------------------------------------------------------------------
vil = Village(m, rng, land)
vil.SIGN_TEXT = dict(vil.SIGN_TEXT, inn=q.text("The Sunk Bell\nAle, pie and a bunk", "Sign"),
                     store=q.text("Greycrag Company Store", "Sign"),
                     foreman=q.text("The Overseer", "Sign"),
                     smithy=q.text("The Smithy\nBlades and mail", "Sign"))
for bid, b in placed:
    for sc_ in BUILDINGS[bid.role]["scenes"]: vil.scene(b, sc_, role=bid.role)


def light(si, sj, rgb):
    x, y = square_px(si, sj)
    m.obj_px("ColorLight", x, y - 5, xfer=d._light_xfer(rgb, 180, 50))


def torch_pole(si, sj):
    s = (int(si), int(sj) + 1)
    if s not in land.squares or s in land.water or s in land.taken_strict: return False
    x, y = square_px(si, sj)
    cx, cy = int(x // 23), int(y // 23)
    if any((cx + a, cy + b) in m.wallmap or (cx + a, cy + b) in m.door_gaps for a in (-1, 0, 1) for b in (-1, 0, 1)):
        return False
    m.obj_px("TorchPole", x, y)
    m.obj_px("ColorLight", x, y - 5, xfer=d._light_xfer((224, 140, 64), 170, 55))
    return True


def clear_round(pts, r, keep=()):
    """Takes out the dressing within r px of the points (the lift and its landing stay clear)."""
    keep = {id(o) for o in keep}
    gone = {id(o) for o in m.d["objects"] if id(o) not in keep and "x" in o and "clone" not in o and
            any(math.hypot(o["x"] - x, o["y"] - y) < r for x, y in pts)}
    m.d["objects"][:] = [o for o in m.d["objects"] if id(o) not in gone]


mine.dress(m, light=light, torch=torch_pole, glow=(64, 160, 224))
for k in range(4):                                 # lamps on the yard's corners
    a = k * math.pi / 2 + math.pi / 4
    torch_pole(vc[0] + 9.5 * math.cos(a), vc[1] - 0.5 + 9.5 * math.sin(a))
lift_keep = []
for t_, o_, l_ in (("Gear3", -0.35, lm + 5.6), ("Gear3", -0.4, lm + 6.3)):
    lift_keep.append(m.obj_px(t_, *mine.px(o_, l_)))
lift_keep.append(m.obj_px("ColorLight", lift_xy[0], lift_xy[1] - 6, xfer=preset("orange")))
clear_round([lift_xy], 46, keep=lift_keep)

# ---- 6. the story's places ------------------------------------------------------------------------------------------
# the yard's middle: a fire basin with benches round it, as the cave towns keep theirs
m.obj_px("DunMirFlameBasinLit", *square_px(vc[0], vc[1] - 0.5))
for k in range(4):
    a = k * math.pi / 2 + math.pi / 4
    m.obj_px(("Bench1", "Bench4", "Bench5", "Bench2")[k], *square_px(vc[0] + 2.6 * math.cos(a), vc[1] - 0.5 + 2.6 * math.sin(a)))
# the company's notice board on the yard's edge, and a trader's cart by the company store: places the folk stop at
ysc = camps.Scene(m, rng, land, (vc[0], vc[1]))
notice = q.text("GREYCRAG COMPANY\nShifts by the Overseer's word.\nNo riders on the Deep Lift.", "Sign")
for a_ in [k_ * math.pi / 8 for k_ in range(16)]:
    if ysc.put("Sign1", *ysc.at(6.5, a_), xfer={"Text": notice}):
        break
store_door = sm.outside_door("store")
if store_door:
    csc = camps.Scene(m, rng, land, px_square(*store_door))
    for r_, a_ in [(r_, k_ * math.pi / 6) for r_ in (2.6, 3.2, 3.8) for k_ in range(12)]:
        if csc.put("OutdoorTraderCart", *csc.at(r_, a_)): break
# the mine forge's yard (kit/mods.py S1, laid as Mods.forge lays it): the anvil, the forge plate (a patch of the yard's
# cobble), Garran's journeyman beside the anvil; the finished copies the anvil hands out are kept not in a vault sealed
# off the land (the checker counts those as weapons no one can reach) but in the smithy's strongroom, its door locked to
# a mechanism no script turns (as act 1's forge keeps them: kit/hc_brackwater.place_forge)
JOURNEYMAN = ("Con03A", "Janero")                   # no double of Doran (CAST: Con02a:Bryan)
mods = Mods(m, sm.pop)


def strongroom():
    """A stock room no entrance opens into: the smithy's, else the bunkhouse's gear store."""
    for role_, kind_ in (("smithy", "storeroom"), ("bunkhouse", "gear_store"), ("store", "storeroom")):
        r_ = sm.room_of(role_, kind_)
        if r_ and not any("outside" in d_.connects for d_ in r_.doors): return r_
    raise AssertionError("no stock room to keep the forge's copies in")


def forge_yard(anvil, smith, plate, store, lines=("longsword", "battleaxe"), copies=2, plate_floor="RoughCobble"):
    m.obj_px("Anvil2", *anvil, scr="S1_Anvil")
    pcx, pcy = int(plate[0] // CELL), int(plate[1] // CELL)
    for dx in range(-1, 3):
        for dy in range(-1, 3):
            m.tile(pcx + dx, pcy + dy, plate_floor)
    m.clone(os.path.join(STOCK, JOURNEYMAN[0], JOURNEYMAN[0] + ".map"), f"{JOURNEYMAN[0]}:{JOURNEYMAN[1]}", *smith,
            name="S1_Smith", xfer={"DirectionId": facing(anvil[0] - smith[0], anvil[1] - smith[1])})
    mods.calls.append(f'ModForge("S1_Anvil", {plate[0]:.1f}, {plate[1]:.1f}, "S1_Smith")')
    near_wall = lambda x, y: any((int(x // CELL) + i, int(y // CELL) + j) in m.wallmap for i in (-1, 0, 1) for j in (-1, 0, 1))
    spots = sorted({((x + 1) * CELL, (y + 1) * CELL) for x, y in store.tiles if not near_wall((x + 1) * CELL, (y + 1) * CELL)},
                   key=lambda p: (p[1], p[0]))
    taken = []
    for key in lines:
        L = FORGE_LINES[key]
        base, kind, tiers, n = L["base"], "", L["tiers"], copies
        names = []
        for t in (1, 2, 3):
            tn = []
            for c in range(n):
                nm = f"Forge_{key}_{t}_{c + 1}"
                at = next((p for p in spots if all(math.hypot(p[0] - a, p[1] - b) >= 20 for a, b in taken)), spots[0])
                taken.append(at)
                x_ = {"Enchantments": _ench(tiers[t])} if tiers[t] else {}
                m.obj_px(base, *at, scr=nm, **({"xfer": x_} if x_ else {}))
                tn.append(nm)
            names.append(tn)
        mods.forge_line(key, L["label"], base, kind, [], *names)
    sm.lock_room(store, lock="Mechanism")


# the yard beside the High Road, not on it: the anvil four squares or more off the road, the plate between the anvil
# and the road (the player steps on it from the road), the journeyman on the anvil's far side
near_road_ = bfs_distance(list(land.roads), land.squares, 8)
yard_cands = [s_ for s_ in land.squares if near_road_.get(s_, 99) >= 4 and s_ not in land.taken_strict and
              s_ not in land.taken and s_ not in land.water and math.hypot(s_[0] - forge_c[0], s_[1] - forge_c[1]) <= 10
              and all((s_[0] + a, s_[1] + b) in land.squares for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2))]
assert yard_cands, "no ground off the road for the forge yard"
yard_sq = min(yard_cands, key=lambda s_: (near_road_.get(s_, 99) > 5, math.hypot(s_[0] - forge_c[0], s_[1] - forge_c[1])))
fsc = camps.Scene(m, rng, land, (yard_sq[0] + 0.5, yard_sq[1] - 0.5))
anvil_xy = fsc.px(0.0, 0.0)
road_sq = min(land.roads, key=lambda s_: math.hypot(s_[0] - yard_sq[0], s_[1] - yard_sq[1]))
rx_, ry_ = square_px(road_sq[0] + 0.5, road_sq[1] - 0.5)
ux_, uy_ = rx_ - anvil_xy[0], ry_ - anvil_xy[1]; ul_ = math.hypot(ux_, uy_) or 1
ux_, uy_ = ux_ / ul_, uy_ / ul_
plate_xy = (anvil_xy[0] + 128 * ux_, anvil_xy[1] + 128 * uy_)
smith_xy = (anvil_xy[0] - 40 * ux_ + 12 * uy_, anvil_xy[1] - 40 * uy_ - 12 * ux_)
forge_yard(anvil_xy, smith_xy, plate_xy, strongroom())
land.taken |= {(yard_sq[0] + a, yard_sq[1] + b) for a in range(-4, 5) for b in range(-4, 5)}
a_road = math.atan2(ry_ - anvil_xy[1], rx_ - anvil_xy[0])
for t_, r_, da_ in (("Bellows1", 1.5, 1.9), ("WaterBarrel", 1.6, -1.8), ("CaveRocksMedium", 3.0, 2.8),
                    ("CaveRocksLarge", 3.3, 3.2), ("BarrelWithTools1", 2.6, -2.7)):
    fsc.put(t_, *fsc.at(r_, a_road + da_))
torch_pole(*fsc.at(2.4, a_road + 2.3))
camps.signpost(m, land, fsc.at(2.6, a_road - 1.2),
               q.text("THE MINE FORGE\nLay a longsword or a battle axe by the anvil, then stand on the paving. "
                      "Better steel costs gold.", "Sign"))
# the glimmer grotto: blue crystal formations, a cyan glow over some, the cutters' tools left where they fled
grotto = [s for s in land.squares if math.hypot(s[0] - grotto_c[0], s[1] - grotto_c[1]) < 11 and s not in land.taken]
for ci, cj in d.clusters({"MineCrystal01": 3, "MineCrystal02": 3, "MineCrystal03": 2, "MineCrystal04": 2,
                          "MineCrystal05": 3}, grotto, 5, size=(5, 8), radius=1.7, gap=0.8, spacing=6.0, core="MineCrystalUp02"):
    m.obj_px("ColorLight", *square_px(ci, cj), xfer=d._light_xfer((64, 160, 224), 200, 50))
gsc = camps.Scene(m, rng, land, (grotto_c[0], grotto_c[1]))
for t_, r_, a_ in (("MiningPickAxeOnGround1", 3.0, 0.8), ("MineOreCart1", 4.2, 2.0), ("MiningPickAxeInGround1", 2.6, 4.1)):
    gsc.put(t_, *gsc.at(r_, a_))
eye_xy = gsc.px(0.0, 0.0)
# the black lake's shore: glowing mushrooms in patches
shore = [s for s in land.squares if s not in land.taken and
         any((s[0] + a, s[1] + b) in lake for a in range(-3, 4) for b in range(-3, 4))]
d.clusters({"Mushroom3": 6, "Mushroom5": 3, "Mushroom1": 2, "Mushroom4": 2}, shore, 6, size=(4, 8), radius=1.6,
           gap=0.7, spacing=5.0)
# caches in the dark by the cavern walls
caches = []
for near_, loot_ in ((grotto_c, [("Gold", {"Amount": 50}), "RedPotion", "BluePotion"]),
                     (lake_c, [("Gold", {"Amount": 45}), "CurePoisonPotion", "RedPotion"]),
                     (west_c, [("Gold", {"Amount": 40}), "LeatherHelm"])):
    s_ = sm.hidden_spot(near_, r=(8, 16))
    if s_: caches.append(camps.cache(m, rng, land, (s_[0] + 0.5, s_[1] - 0.5), loot_))
camps.signpost(m, land, (west_c[0] + 2.5, west_c[1] - 1.5), q.text("GREYCRAG\nMind the carts.", "Sign"))
gs_ = sm.road_near(((gate_sq[0] * 2 + forge_c[0]) / 3, (gate_sq[1] * 2 + forge_c[1]) / 3))
camps.signpost(m, land, (gs_[0] + 2.0, gs_[1] - 1.5), q.text("HIGH ROAD BARRED\nBy order of the Overseer.", "Sign"))
ls_ = mine.pt(-3.4, lm + 6.6)
camps.signpost(m, land, ls_, q.text("THE DEEP LIFT\nChained. Ask Pike.", "Sign"))
gr_ = sm.road_near(((grotto_c[0] + vc[0]) / 2, (grotto_c[1] + vc[1]) / 2))
camps.signpost(m, land, (gr_[0] + 1.5, gr_[1] + 1.5), q.text("GLIMMER GROTTO\nKeep out! The Eye!", "Sign"))

# the Low Workings: the Choir's dig at the shaft's foot, open toward the pit; their take in the chest
low_sq = sq_of(*LOW)
dig_site = camps.camp_site(m, deep, sq_of(*LOW), reach=7, road_clear=0, room=6)   # backed onto the rock, by the pit
dig = camps.bandit_camp(m, rng, deep, dig_site, sq_of(*LOW_PIT),
                        loot=[("Gold", {"Amount": 80}), "RedPotion", "RedPotion", "BluePotion", "ChainLeggings"],
                        sleepers=4, tents=2, trade="dig", finds=("MineCrystal03", "MineCrystal05", "MineCrystal01"))
dig_chest = dig["chest"]
assert dig_chest, "the Choir's dig has no chest"
m.obj_px("ColorLight", pit_xy[0], pit_xy[1] - 6, xfer=preset("orange"))
psc = camps.Scene(m, rng, deep, sq_of(*LOW_PIT))
for t_, r_, a_ in (("MinePost3", 3.6, 0.6), ("MinePost3", 3.6, 2.2), ("AmbMineCreaks", 2.4, 4.0)):
    psc.put(t_, *psc.at(r_, a_))
# the drowned gallery: shells and bones in the shallows, crystal in the walls; the starsteel seam in the side pocket
for X_, Y_, t_ in ((204, 80, "BeachShellLarge"), (207, 88, "BeachShellSmall"), (203, 104, "BeachShellLarge"),
                   (209, 112, "BeachShellSmall"), (208, 118, "Skull"), (201, 92, "MineCrystal04"),
                   (211, 101, "MineCrystal01"), (205, 70, "CaveRocksLarge"), (209, 64, "CaveRocksMedium")):
    camps.Scene(m, rng, deep, sq_of(X_, Y_)).put(t_, *sq_of(X_, Y_))
osc = camps.Scene(m, rng, deep, sq_of(*ORE))
for t_, r_, a_ in (("MineCrystal05", 3.6, 0.4), ("MineCrystal02", 3.8, 1.6), ("MineCrystalUp03", 4.0, 5.4),
                   ("MiningPickAxeInGround1", 2.4, 3.0), ("BeachShellLarge", 2.0, 4.4), ("LegBone", 2.6, 2.2)):
    osc.put(t_, *osc.at(r_, a_))
steel_o = osc.put(STEEL, *osc.at(1.2, 5.0))
assert steel_o, "the starsteel found no floor"
m.obj_px("ColorLight", *P(*ORE), xfer=preset("blue", "dim"))
# the bell shrine: the altar on its dais, the founders' tablet behind it, standing stones round it, the second bell
# lying drowned at the dais' foot (the player is told of it on the way in); the Spirit Stone on the altar's step
bsc = camps.Scene(m, rng, deep, sq_of(*BELL))
for k_ in range(6):
    a_ = k_ * 2 * math.pi / 6 + 0.3
    bsc.put("Obelisk", *bsc.at(4.6, a_))
altar_xy = P(*BELL)
m.obj_px("DunMirAltar1", *altar_xy)
tablet_o = bsc.put("SignDunMir04", *bsc.at(2.6, -math.pi / 2),
                   xfer={"Text": q.text("THE SECOND BELL\nHung by the founders. Let it ring at the turning of the "
                                        "year.", "Sign")})
tablet_xy = (tablet_o["x"], tablet_o["y"]) if tablet_o else (altar_xy[0], altar_xy[1] - 60)
stone_o = bsc.put(STONE, *bsc.at(1.1, math.pi / 2))
assert stone_o, "the Spirit Stone found no floor"
m.obj_px("ColorLight", altar_xy[0], altar_xy[1] - 6, xfer=preset("white", "dim"), scr="ShrineLight")
for t_, r_, a_ in (("CaveRocksLarge", 7.5, 1.0), ("BeachShellLarge", 7.0, 2.4), ("Skull", 7.8, 3.6),
                   ("CaveRocksMedium", 8.2, 5.2), ("BeachStarfish", 6.8, 4.4)):
    bsc.put(t_, *bsc.at(r_, a_))

# ---- 7. lights and pillars, the start and the exit ------------------------------------------------------------------
keep_clear = {(int(vc[0]) + a, int(vc[1]) + b) for a in range(-7, 8) for b in range(-7, 8)}
keep_clear |= {(i + a, j + b) for i, j in lake for a in range(-2, 3) for b in range(-2, 3)}
n_trees, n_small = d.vegetate(keep_clear=keep_clear, groves=2)
d.scatter_open(scale=0.5)
d.rim(scale=0.6)
n_lights = d.lights(scale=0.6)
piles = d.planter.rock_piles(max(4, len(land.squares) // 1100))
start_xy = square_px(west_c[0] + 0.5, west_c[1] - 0.5)
m.obj_px("PlayerStart", *start_xy)
exits = exit_next(sm, "north", 3, prefix="HighExit")

# ---- the transporter (skills/nox-transporters): the Deep Lift down to the Low Workings --------------------------------
tp = Transporters(m)
lift = tp.add("lift", lift_xy, pit_xy, "DeepLift", style="mine", enabled=False,
              serves=[(dig_chest["x"], dig_chest["y"]), (steel_o["x"], steel_o["y"]),
                      (stone_o["x"], stone_o["y"]), tablet_xy])
s_ = px_square(*lift_xy)
land.taken |= {(s_[0] + a, s_[1] + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2)}

# ---- 8. the people --------------------------------------------------------------------------------------------------
pop, B = sm.pop, sm.B
person = sm.person
vx, vy = square_px(*vc)
st = sm.room_of("foreman", "study")
bx_, by_ = sm.free_px(st) if st else square_px(vc[0] + 3, vc[1])
person("War01A", "Kristine", bx_, by_, "Brenna")
# Tull the carter at the cavern mouth, his cart stopped by the road
tull_sq = sm.road_near((west_c[0] + 4.0, west_c[1]))
tsc = camps.Scene(m, rng, land, (tull_sq[0] + 0.5, tull_sq[1] - 0.5))
tull_xy = None
for da_ in (2.0, -2.0, 2.6, -2.6):
    p_ = (tull_sq[0] + 0.5 + da_ * 0.7, tull_sq[1] - 0.5 - da_ * 0.7)
    if tsc.ok(*p_):
        tull_xy = square_px(*p_); break
tull_xy = tull_xy or square_px(tull_sq[0] + 2.5, tull_sq[1] - 0.5)
person("Con03A", "Kenneth", *tull_xy, "Tull", face=start_xy)
tl_ = camps.Scene(m, rng, land, px_square(*tull_xy))
for r_, a_ in [(r_, k_ * math.pi / 6) for r_ in (2.4, 3.0, 3.6) for k_ in range(12)]:
    if tl_.put("OutdoorTraderCart", *tl_.at(r_, a_)): break
# Pike at the mine head, beside the lift's winch, off the cage
pk_ = mine.px(-2.0, lm + 6.9)
person("Con03B", "Foreman", *pk_, "Pike", face=(vx, vy))
# Garran Ashforge at his forge, by the anvil, his journeyman (S1_Smith) at its other side
gr_xy = (anvil_xy[0] + 52, anvil_xy[1] - 40)
person("Con03A", "Horst", *gr_xy, "Garran", face=plate_xy)
# Nim at her door
nim_b = next((b for bid, b in placed if bid.occupant.startswith("Nim")), None)
nm_ = (sm.doorside(building=nim_b, toward=(vx, vy)) if nim_b else None) or (vx - 60, vy + 20)
person("War01A", "Jennifer", *nm_, "Nim", face=(vx, vy))
# the High Road's guard, on the town side of the gate
gq_ = square_px(gate_sq[0] + 0.5, gate_sq[1] - 0.5)
gdx, gdy = vx - gq_[0], vy - gq_[1]
gl = math.hypot(gdx, gdy) or 1
person("Con02a", "Guard2", gq_[0] + 70 * gdx / gl, gq_[1] + 70 * gdy / gl, "RoadGuard", face=(vx, vy))
# shopkeepers
WARES = {"store": [(4, "RedPotion"), (3, "BluePotion"), (2, "CurePoisonPotion"), (2, "ShieldPotion"), (2, "Meat"),
                   (2, "Quiver"), (1, "Bow"), (1, "LeatherBoots"), (1, "LeatherHelm"), (1, "LeatherArmor")],
         "inn": [(6, "RedApple"), (5, "Meat"), (4, "Cider"), (4, "Bread"), (2, "RedPotion")],
         "smithy": [(2, "Sword"), (2, "Longsword"), (2, "BattleAxe"), (1, "WarHammer"), (1, "SteelShield"),
                    (1, "ChainCoif"), (1, "ChainTunic"), (1, "ChainLeggings"), (1, "SteelHelm")]}
GREET = {"store": q.text("Well... not the cheapest picks in the hills... But they'll outlast you!", "Shop"),
         "inn": q.text("Pssst! Over here, friend! Mushroom pie? Cheapest in the hills, and grown in our own dark!",
                       "Shop"),
         "smithy": q.text("Welcome to Greycrag! Need an edge? The forge yard's the place to make it a better one.",
                          "Shop")}
n_shops = sm.shops(WARES, GREET, keeper={"smithy": "ShopkeeperWarriorsRealm"})
# townsfolk on their rounds of the yard; none stops by the lift, the forge's anvil, the grotto or the gate
for c_, r_ in ((lift_sq, 4), (yard_sq, 5), (grotto_c, 14), (lake_c, 8)):
    sm.keep_folk_away(c_, r_)
FOLK = [("Con03B", "Alex"), ("Con03B", "Claude"), ("Con03B", "Naldo"), ("War01A", "Melissa"), ("Con02a", "Joyce")]
RUMOURS = [
    "Out of the way! Ore cart!",
    "Well, you don't look like much. I hope the Overseer knows what she's doing.",
    "I've heard the Choir paid for the Deep Lift in old gold, older than Greycrag. Strange folk.",
    "What're you gawping at? Got coal on my nose?",
    "Something sings down the shaft at night -- nobody goes near the lift now.",
]
ring = sm.townsfolk(FOLK, vc, q=q, rumours=RUMOURS,
                    after=("road_open", "The Choir's out of the deep! The Overseer says you beat them to the bell!"),
                    pics=("MalePic1", "MalePic7", "Townsman1Pic", "MaidenPic3", "MaidenPic2"),
                    radius=7.0, stops=(6, 8))
# the watch, on a beat round the yard
wx2, wy2 = ring[0]
person("Con01A", "Contest_Guard", wx2, wy2, "Watch1", action=0)
sm.beat("Watch1", vc, radius=7.0, stops=7)

# ---- 9. the fights ----------------------------------------------------------------------------------------------------
# the Low Workings: Digmaster Gant by the take, his hired blades at their posts, the Mirewood's drowned dead at the dig
dig_posts = camp_posts(m, dig, pit_xy, sit=1, tents=1, watch=1, work=2)
pop.creature("Swordsman", *dig_posts["leader"], action="guard", scr="Gant", aggr=0.83, HealthMultiplier=2.5,
             face=pit_xy)
diggers = []
for k_, (x_, y_) in enumerate(dig_posts["sit"] + dig_posts["tent"]):
    n_ = f"ChoirDigger{k_ + 1}"
    pop.creature("Swordsman", x_, y_, action="idle", scr=n_, aggr=0.83, face=dig["fire"])
    diggers.append(n_)
for k_, (x_, y_) in enumerate(dig_posts["watch"]):
    n_ = f"ChoirBow{k_ + 1}"
    pop.creature("Archer", x_, y_, action="guard", scr=n_, aggr=0.83, face=pit_xy)
    diggers.append(n_)
for k_, (x_, y_) in enumerate(dig_posts["work"]):
    n_ = f"DeadDigger{k_ + 1}"
    pop.creature("Skeleton", x_, y_, action="guard", scr=n_, aggr=0.83, face=dig["fire"])
    diggers.append(n_)
# one of the drowned dead set to watch the gallery's mouth, where the dig breaks through toward the flood
pop.creature("Skeleton", *P(202, 68), action="guard", scr="DeadWatch1", aggr=0.83, face=P(*LOW))
if "ChoirBow1" in diggers:
    B.sentry("ChoirBow1", pit_xy, rouse=["Gant"] + [n for n in diggers if n != "ChoirBow1"][:4],
             shout="The lift! Someone's come down! Up, up!")
# the flooded deep: Giant Crabs (M2) in the gallery's water, in the starsteel pocket and at the bell shrine's foot
crab_sq = [(206, 108), (222, 86), (212, 122)]
crabs = []
for k_, (X_, Y_) in enumerate(crab_sq):
    n_ = f"Crab{k_ + 1}"
    mods.monster("M2", *P(X_, Y_), name=n_, wait=230, hp=(320, 360, 450)[k_], face=P(*BEND))
    crabs.append(n_)
for k_, (X_, Y_) in enumerate(((203, 76), (208, 98))):
    pop.creature("GiantLeech", *P(X_, Y_), action="guard", scr=f"DeepLeech{k_ + 1}", aggr=0.83, face=P(*LOW))
for k_, (X_, Y_) in enumerate(((207, 68), (201, 84), (220, 89))):     # bats under the gallery's roof, off the pit
    pop.creature("Bat", *P(X_, Y_), action="guard", scr=f"DeepBat{k_ + 1}", aggr=0.83)
# the glimmer grotto: the Eye
pop.creature("Beholder", *eye_xy, action="guard", scr="TheEye", aggr=0.83, face=square_px(*vc))
# the cavern's own creatures by the walls, away from the town and the story's places (never a Zombie)
sm.wild({"Bat": 4, "Scorpion": 1, "SmallSpider": 2, "Spider": 1}, away_from=vc,
        avoid=(west_c, forge_c, grotto_c, lake_c, gate_sq, north_c), per100=0.7, min_away=22)
# bats under the grotto's roof, skittish; spiders by the black lake
for k_ in range(3):
    x_, y_ = square_px(grotto_c[0] + 5.5 * math.cos(k_ * 2.1 + 0.4), grotto_c[1] - 0.5 + 5.5 * math.sin(k_ * 2.1 + 0.4))
    pop.creature("Bat", x_, y_, action="idle", scr=f"GrottoBat{k_ + 1}")
    B.skittish(f"GrottoBat{k_ + 1}", 3.0)
walk_ = sm.walkable() or set()
lake_spots = []
for s_ in sorted(shore, key=lambda s: (s[0], s[1])):
    x_, y_ = square_px(s_[0] + 0.5, s_[1] - 0.5)
    if s_ in land.taken or s_ in land.roads or (int(x_ // CELL), int(y_ // CELL)) not in walk_: continue
    if any((int(x_ // CELL) + a, int(y_ // CELL) + b) in m.wallmap for a in (-1, 0, 1) for b in (-1, 0, 1)): continue
    if all(math.hypot(x_ - p_[0], y_ - p_[1]) > 160 for p_ in lake_spots): lake_spots.append((x_, y_))
    if len(lake_spots) == 3: break
for k_, (x_, y_) in enumerate(lake_spots):
    pop.creature("SmallSpider" if k_ else "Spider", x_, y_, action="guard", scr=f"LakeSpider{k_ + 1}", aggr=0.83)
story_xy = [(o["x"], o["y"]) for o in pop.placed + [o for o in m.d["objects"] if "clone" in o]
            if o["x"] < FAR_X * CELL] + [(c["x"], c["y"]) for c in caches if c]
opened = sm.open_ways(story_xy)

# ---- 10. the story --------------------------------------------------------------------------------------------------
MAIN = "Reach the second bell in the flooded deep before the Choir."
STEEL_Q = "Bring Garran Ashforge a lump of starsteel from the flooded deep."
EYE = "Kill the Eye in the glimmer grotto north-west of the yard."
q.start([A.lock("HighGate1"), A.lock("HighGate2")] + [A.disable(n) for n in exits] +
        [q.journal("Find out what the Choir wants in the Greycrag mines.", QUEST)])
# what the player carries from the earlier acts, read once and before anything else checks it (a verse already
# carried after a saved game keeps the tablet from giving another)
q.when_true(has("DORAN_LETTER"), [A.flag("doran_letter")])
q.when_true(q.when(has=VERSE), [A.flag("verse_taken")])

# Tull: the hook
q.talker("Tull", [
    q.say("Good. Right. Off you go, then.", when=q.when(flag="road_open"), who="Tull"),
    q.say("The Overseer's hall is on the yard, lad! Unless you'd RATHER stand here in the dust with me!",
          when=q.when(flag="met_tull"), who="Tull"),
    q.say("More robed folk!? No... no, you're not one of them. Sorry, stranger! That Choir's had this town by the "
          "throat a fortnight! Go and see Overseer Brenna!",
          do=[A.flag("met_tull"), q.note("NOTE: Tull the carter says the Choir has held Greycrag by the throat for a "
                                         "fortnight. Overseer Brenna runs the mines.")], who="Tull")])

# Overseer Brenna: the main quest and the High Road
OPEN = [A.unlock("HighGate1"), A.unlock("HighGate2")] + [A.enable(n) for n in exits]
PAY = [A.flag("road_open"), A.gold(250), A.give("ChainTunic"), A.give("RedPotion", 2), q.done(MAIN)]
q.talker("Brenna", [
    q.say("The High Road's open. Keep that stone close.", when=q.when(flag="road_open"), who="Brenna"),
    q.say("The bell's stone! You got there first!\n\nKeep it, and keep it from that Choir. Greycrag can't hold it. The "
          "High Road is open, and here's the company's thanks. Go carefully!",
          when=q.when(has=STONE, flag=q.dead("Gant"), not_="road_open"), do=OPEN + PAY, who="Brenna"),
    q.say("Gant's dead and the stone's safe with you, whatever's become of it. The High Road is open. Here, the "
          "company's thanks.",
          when=q.at("stone", 1, flag=q.dead("Gant"), not_="road_open"), do=OPEN + PAY, who="Brenna"),
    q.say("You have it! But Gant and his diggers still hold the Low Workings. They'll come up after it. Finish them "
          "first!", when=q.when(has=STONE), who="Brenna"),
    q.say("Gant's dead? Good! But the bell's stone -- did you reach it? Back down with you!",
          when=q.when(flag=q.dead("Gant")), who="Brenna"),
    q.say("That Choir must be stopped! YOU have the blade for it.\n\nDown the lift with you! They dig deeper every "
          "hour.", when=q.when(flag="brenna_told"), who="Brenna"),
    q.say("Greetings. You're no miner, and you're no Choir. Good.\n\nA fortnight ago that Choir came up the causeway "
          "with gold in their hands and dead men at their heels, and took the Deep Lift for themselves. Now they dig in "
          "the Low Workings, down toward the flooded deep. The old folk say the second bell went down there the year "
          "the deep flooded.\n\nGet down there before they find it. Pike will start the lift for you. I've barred the "
          "High Road, so nothing they dig up leaves Greycrag.",
          do=[A.flag("brenna_told"), A.stage("main", 1), q.journal(MAIN, QUEST)], who="Brenna")],
    voice={"desc": "A hard-bitten woman in her fifties, overseer of a mining town. Low, firm, gravelly voice, a broad "
                   "Yorkshire accent. Speaks bluntly and fast.", "seed": 3101})

# Pike and the Deep Lift
q.talker("Pike", [
    q.say("Hey, you should wash that crab-muck off before supper.", when=q.when(flag="road_open"), who="Pike"),
    q.say("She's running! Step on the cage when you're ready. She brings you back up the same way.",
          when=q.when(flag="lift_on"), who="Pike"),
    q.say("The Overseer says so? Then stand clear. I'll knock the chain off the brake.\n\nMind yourself at the bottom!",
          when=q.when(flag="brenna_told", not_="lift_on"),
          do=[A.flag("lift_on")] + [A.enable(n) for n in lift.sources] +
             [A.print("Pike knocks the chain off the brake. Far down the shaft, the Deep Lift's gears begin to "
                      "grind.")], who="Pike"),
    q.say("Hold it, stranger! Nobody rides my lift! The Choir paid good gold for it, and look what came back up! Dead "
          "men! The brake's chained, and chained it stays! Want to argue it with the Overseer?", who="Pike")])

# the Low Workings, the flooded deep and the bell shrine
q.near(*pit_xy, 260, [A.print("The air down here is wet and cold, and somewhere below, water drips into water.")])
q.near(*P(*BEND), 260, [A.print("Black water fills the gallery from wall to wall. Something with a shell moves in "
                                "it.")])
q.near(*altar_xy, 330, [A.print("An old shrine stands out of the flood. At its foot the second bell lies on its side "
                                "in the black water, green with age, big as a cart.")])
q.on_death("Gant", [A.flag("gant_dead"), A.print("Digmaster Gant falls across his diggings. The dead he set to dig "
                                                 "stand still."),
                    q.note("NOTE: Digmaster Gant is dead. The Choir's dig in the Low Workings is broken.")])
q.on_pickup(STONE, [A.stage("stone", 1),
                    A.print("The second bell's clapper: a Spirit Stone, a red stone that hums in your hand. Without "
                            "it the bell is dumb."),
                    q.note("NOTE: The Choir must never have the second bell's Spirit Stone.")])
# the founders' tablet: one verse, given once
q.near(*tablet_xy, 80, [A.flag("verse_taken"), A.give(VERSE),
                        A.print("A founders' tablet, its letters cut deep. Below them sits a blue stone rubbed with "
                                "the founders' words: a verse of the bells. You prise it free."),
                        q.note("NOTE: A verse of the bells, rubbed into a blue stone, lay under the founders' "
                               "tablet.")],
       when=q.when(not_="verse_taken"))

# Garran Ashforge: Doran's letter and the starsteel
q.on_pickup(STEEL, [A.stage("steelfound", 1),
                    A.print("A lump of starsteel, red-glinting and colder than the water."),
                    q.note("NOTE: Starsteel from the flooded deep, the seam the crabs keep.")])
steel_yes = [A.stage("steel", 1), A.unflag("steel_refused"), q.journal(STEEL_Q, QUEST)]
steel_no = [A.flag("steel_refused"), q.tell("Garran", "Then I'll go on dreaming of it.")]
steel_pay = [A.give("SteelHelm"), A.give("ShieldPotion", 2), A.stage("steel", 3), q.done(STEEL_Q)]
q.talker("Garran", [
    q.say("Lay your blade by the anvil and stand on the paving. My lad works the steel.", when=q.at("steel", 3),
          who="Garran"),
    q.say("Starsteel, and a fine lump of it! Doran was right.\n\nBut no fire in Greycrag is hot enough to work it. Only "
          "the founders' forge could, where the bells were cast. Keep it for Doran, and take this for your trouble.",
          when=q.at("steel", 1, has=STEEL, flag="doran_letter"), do=steel_pay, who="Garran"),
    q.say("Starsteel, and a fine lump of it!\n\nBut no fire in Greycrag is hot enough to work it. Only the founders' "
          "forge could, where the bells were cast. Keep it safe, and take this for your trouble.",
          when=q.at("steel", 1, has=STEEL), do=steel_pay, who="Garran"),
    q.say("Please, the starsteel! Before the Choir dig it out and melt it for nails!", when=q.at("steel", 1),
          who="Garran"),
    q.say("Ooh, is that Doran's guild medallion? The old goat still lives! He'll be wanting starsteel, and there's a "
          "seam of it in the flooded deep, under the crabs. Quickly, before the Choir's diggers find it! Will you bring "
          "me a lump?",
          when=q.at("steel", 0, flag="doran_letter"), ask=True, do=steel_yes, else_=steel_no, who="Garran"),
    q.say("You've a fighter's hands. There's starsteel in the flooded deep, the best ore under these hills, and the "
          "crabs sit on it now. Bring me a lump and I'll tell you what it's good for. Will you?",
          when=q.at("steel", 0), ask=True, do=steel_yes, else_=steel_no, who="Garran")],
    voice={"desc": "A broad-chested smith in his fifties, cousin of an old West Country blacksmith. Deep, warm, rough "
                   "voice, a West Country English accent. Speaks steadily.", "seed": 3102})

# Nim: the Eye in the Grotto
q.on_death("TheEye", [A.print("The Eye bursts like a rotten egg and drops among the crystals.")])
q.near(*eye_xy, 300, [A.print("Blue crystal glows all round, and in the middle of it something huge and round "
                              "hangs in the air, watching.")])
q.talker("Nim", q.errand(
    "Nim", "eye",
    offer="It's horrible! A great floating Eye came up through the floor of the glimmer grotto, north-west of the yard! "
          "It stared at a cutter and he dropped like a sack!\n\nNobody will cut glimmer with that thing there. Will you "
          "kill it? I'll give you the best stone I ever cut.",
    reminder="Please, the Eye! There's no glimmer to cut and no bread on my table!",
    thanks="It's dead? Truly? Thank goodness!\n\nHere, the best glimmer I ever cut. Please accept it as a token of my "
           "appreciation!",
    after="My thanks again, brave Adventurer!",
    objective=EYE, done=q.when(flag=q.dead("TheEye")),
    reward=[A.give(GLIMMER), A.gold(60), A.give("BluePotion", 2)],
    refusal="Then I'll sit here and starve. Thank you so much."),
    voice={"desc": "A young woman in her twenties, a crystal-cutter in a mining town. Bright, quick, anxious voice, a "
                   "Yorkshire accent.", "seed": 3103})

# the High Road's guard and the watch
q.talker("RoadGuard", [
    q.say("I'd thank the Overseer myself...\n\nif I were you. She doesn't forget a favour.",
          when=q.when(flag="road_open"), who="Guard"),
    q.say("None leave by the High Road!", who="Guard")])
q.talker("Watch1", [
    q.say("Quiet down the shaft, they say. Good.", when=q.when(flag="gant_dead"), who="Watch"),
    q.say("Keep your hand off your sword in the yard. We've trouble enough.", who="Watch")])

for who_, pic_ in (("Brenna", "WardenPic"), ("Tull", "MalePic8"), ("Pike", "MalePic5"), ("Garran", "QuarterMasterPic"),
                   ("Nim", "MaidenPic4"), ("RoadGuard", "Warrior2Pic"), ("Watch1", "Warrior3Pic")):
    q.portrait(who_, pic_)

mods.attach(B)                                      # the crabs and the forge (kit/mods.py), last of the placing
m.scripts.update(B.files(m.d["name"]))
m.scripts.update(q.files())

# ---- 11. the exteriors' dressing, after the people's routes are laid -----------------------------------------------
from kit.dressing import Exterior
dressed = Exterior(m, land, "cave", placed=placed).dress()

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rooms_sidecar(placed, os.path.join(OUT, f"{NAME}.rooms.json"))
    from kit.campaign import apply_deliveries
    apply_deliveries(q)            # voice-gate deliveries (kit/campaign.py DELIVERIES)
    q.write_strings(OUT)
    lines = m.build(os.path.abspath(OUT))
    print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS", "VOICE", "CAMPAIGN"))))
    print(f"land {len(land.squares)} squares | buildings {len(placed)}/{len(ID.buildings)} (missed: {', '.join(sm.missed) or 'none'}) "
          f"| pillars {n_trees} | shops {n_shops} | caches {len(caches)} | opened {len(opened)} | lines {len(q.strings)} "
          f"| deep {len(deep.squares)} squares | dressing {sum(dressed.values())} groups")
