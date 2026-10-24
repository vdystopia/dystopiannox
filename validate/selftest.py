"""Proves the checker catches the defects we know about. Builds a small clean test map and one
variant per known defect (each planted on purpose, including every playtest finding so far), runs
the checks on each, and confirms: the clean map has no errors, and every variant raises the
expected finding.

    py validate/selftest.py              (builds into validate/out/selftest/, about three minutes)
    py validate/selftest.py STkeep ...   only these cases (and the clean map)

Each case's caught finding names its rule (checks.RULES); the rules with a planted case are written to
validate/out/selftest/rules.json for validate/checkcheck.py. A finding no rule names fails the self-test.
"""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mapdata as md
import checks as C
import validate as V
sys.path.insert(0, os.path.join(md.REPO, "mapgen"))
from nox import Spec, SOLO, CELL, px, rect_tiles
from kit.water import Waterworks

OUT = os.path.join(md.OUT, "selftest")
DOOR_GAP = (100, 100)        # left wall of the house (u = 200, v = 0), a '/' line
CORNER_GAP = (96, 104)       # next to the house's corner at (95, 105)


def clean(name, **info):
    """A walled meadow with a house (double door, single door beside a corner), a pond with a dock,
    a creature in the house and a player start outside."""
    m = Spec(name, summary="Checker self-test", description="Checker self-test", author="generated", version="0.1",
             date="2026", **{**dict(type=SOLO, minPlayers=1, maxPlayers=1), **info})
    m.d["nxz"] = False
    m.d["ambient"] = [150, 150, 140]
    m.room(180, 260, -40, 40, wall="BrickPlain", floor="GrassNorm")
    m.room(200, 222, -10, 10, wall="StuccoLightWood", floor="WoodLight2")
    m.door("WoodAndSteelHalfDoor", DOOR_GAP, "/")
    m.door("ArchedDoor", CORNER_GAP, "/")
    ww = Waterworks(m, random.Random(3))
    pond = ww.pond((240, 22), radius=8)
    ww.dock(pond, "down", length=1)          # (a third of this pond, clipped by the meadow: QA round 1)
    ww.finish()
    m.obj("PlayerStart", 190, 0)
    m.obj("Wolf", 212, 0)
    m.obj("WoodBed2", 218, 6)
    m.obj("Table1", 214, -6)
    m.obj("Lantern", 204, 8)
    return m


def black_wall(m):
    # style 2 exists for straight BrickPlain pieces but not for corners: the corner draws black
    m.wallmap[(70, 110)]["variation"] = 2
    m._wall_variation = lambda material, facing, wanted: wanted if wanted is not None else 0


def hole(m):
    for c in ((90, 90), (91, 89)): m.remove_wall(*c)


def invisible_boundary(m):
    for c in ((90, 90), (91, 89), (92, 88)): m.wallmap[c]["material"] = "InvisibleWallSet"


def lone_half_door(m):
    m.wall(102, 98, "StuccoLightWood")                        # close the double door's second cell...
    for c in ((100, 100), (101, 99)): m.door_gaps.discard(c)
    m.d["objects"] = [o for o in m.d["objects"] if o.get("type") != "WoodAndSteelHalfDoor"]
    m.wall(101, 99, "StuccoLightWood")
    m.door_gaps.add(DOOR_GAP)                                 # ...and hang one half alone in a 1-cell opening
    m.obj_px("WoodAndSteelHalfDoor", DOOR_GAP[0] * CELL, (DOOR_GAP[1] + 1) * CELL, door=8)


def jamb(m):
    m.door_gaps.discard(CORNER_GAP)                           # shape walls as if the opening were empty


def dock_misaligned(m):
    docks = [o for o in m.d["objects"] if str(o.get("type", "")).startswith("DockDown")]
    docks[-1]["x"] += 7


def clutter(m):
    for i in range(6):          # 30 tables: Westwood's bedrooms of this size hold up to about 23 pieces
        for j in range(5):
            m.obj("Table1", 203 + 3 * i, -8 + 3.3 * j)


def doorway(m):
    m.obj_px("Barrel", DOOR_GAP[0] * CELL + 11.5, DOOR_GAP[1] * CELL + 11.5)


def rug_on_grass(m):
    m.raw_floors = True                        # the map writer would put a buffer floor between them
    for x, y in rect_tiles(186, 192, 20, 26): m.tile(x, y, "RugGreen")


def void_creature(m):
    m.obj_px("Wolf", 300, 300)


def sealed_room(m):
    m.room(240, 248, -32, -24, wall="StuccoLightWood", floor="WoodLight2")
    m.obj("Wolf", 244, -28)


def dock_across_puddle(m):
    ww = Waterworks(m, random.Random(5))
    puddle = ww.pond((190, -24), radius=3)
    ww.dock(puddle, "down", length=2, at=(183.0, -24.0))     # forced: the kit itself refuses a puddle
    ww.finish()


def lights_side_by_side(m):
    for k in range(2):
        m.obj("Candleabra1", 216 + 1.2 * k, 8)


def chest_blocked(m):
    m.obj("Chest4", 202, 4)                                    # a chest against the house's back wall...
    m.obj("Table1", 204.2, 4)                                  # ...with a table right in front of it


def bridge_into_wall(m):
    ww = Waterworks(m, random.Random(7))
    brook = ww.stream([(184, 30), (256, 30)], width=2.0, wiggle=0.0)
    ww.plank_bridge(brook, at=(221.0, 30.0), along="v")       # the deck runs into the boundary wall
    ww.finish()


def chest_across_wall(m):
    m.obj("Chest3", 202.1, 0)                                  # long side across the house NW wall


def stumps_bunched(m):
    for k in range(6):
        m.obj("Stump%d" % (1 + k % 4), 230 + 1.6 * (k % 3), -26 + 1.8 * (k // 3))


def wide_bridge(m):
    ww = Waterworks(m, random.Random(9))
    brook = ww.stream([(184, -30), (256, -30)], width=2.2, wiggle=0.0)
    ww.plank_bridge(brook, at=(236.0, -30.0), along="v", deck_width=4)
    ww.finish()


def pair_on_wrong_line(m):
    a, b = (110, 100), (111, 101)                              # the house's NE wall, a '\\' line
    for c in (a, b):
        m.remove_wall(*c); m.door_gaps.add(c)
    m.obj_px("BandedPlankDoor", a[0] * CELL, a[1] * CELL, door=16)              # North half
    m.obj_px("BandedPlankDoor", (b[0] + 1) * CELL, (b[1] + 1) * CELL, door=0)   # South half


def torch_in_house(m): m.obj("Torch", 206, -6)


def food_by_table(m): m.obj("Meat", 215.6, -6)


def seated_at_ends(m):
    m.obj("WoodenChair2", 214, -8.7); m.obj("WoodenChair3", 214, -3.3)


def mixed_bunks(m):
    m.obj("Cot2", 205, 6); m.obj("Bed3", 210.5, 6)


def table_no_seats(m):
    m.obj("WoodBed2", 210, 6); m.obj("WoodBed2", 214, 6)       # with the house's own: a bunk room


def lopsided(m):
    for u, v in ((220, -2), (220, 0), (219.5, 2.5)): m.obj("Barrel", u, v)


def packed_bunks(m):
    for v in (-6.0, -3.0, 0.0): m.obj("WoodBed2", 204, v)              # 0.24 units apart (WoodBed2 is 2.76 long)


def hearth_crowded(m):
    m.obj("Fireplace3", 202.5, -4); m.obj("CauldronAnimated", 202.5, -2.14)    # 0.2 units from the hearth


def table_half_on_rug(m): m.obj("RedRug2", 212.5, -6)


def double_door_inside(m):
    for x in range(100, 111): m.wall(x, 210 - x, "StuccoLightWood")     # a partition across the house (u = 210)
    m.door("ArchedHalfDoor", (105, 105), "/")


def mixed_doors(m):
    m.door("WoodenDoor", (111, 101), "\\")                               # a third kind of door in the house


def sparse_room(m):
    m.declare_rooms = [dict(number=1, building="test house", kind="living_room", purpose="", tiles=0,
                            box=[0, 0, 0, 0], floor=[list(t) for t in rect_tiles(200, 222, -10, 10)])]


def shelf_on_front_wall(m):
    m.obj("Bookcase3", 222.38, 0)                              # against the SE wall: the camera sees only its back


def scattered_shelves(m):
    m.obj("Bookcase2", 205, 9.43)                              # two bookcases on the NE wall, bare wall between
    m.obj("Bookcase2", 216, 9.43)


def floating_chest(m):
    m.obj("Chest3", 210, 8.09)                                 # 1.4 units off the NE wall, alone in the room


def no_start(m):
    m.d["objects"] = [o for o in m.d["objects"] if o.get("type") != "PlayerStart"]


def path_to_wall(m):
    # a dirt road along the meadow, and a thin spur from it that ends against the house's north wall, far from both
    # of its doors (the house's own floor half under its walls is no such path: town lab)
    for u in range(186, 254, 2):
        for v in (24, 26):
            m.tile((u + v) // 2, (u - v) // 2, "DirtDark2")
    for k in range(6):                               # u = 216, v from 12 up to 22, one tile wide
        m.tile(114 + k, 102 - k, "DirtDark2")


def waypoint_at_jamb(m):
    # a doorstep waypoint pressed against the jamb beside the double door (the 2026-10-05 playtest: an NPC stuck on the
    # frame beside a door)
    a = m.waypoint(99 * CELL - 2, 101 * CELL + 11.5, name="Step_1")
    b = m.waypoint(97 * CELL, 101 * CELL, name="Step_2")
    m.routes = [dict(who="Folk", kind="tour", waypoints=["Step_1", "Step_2"], loop=False, pauses=[20, 20])]


def route_cuts_doorway(m):
    # a leg through the double door at 45 degrees to its opening: walkers cut the corner into the jamb
    cx, cy = 100.5 * CELL + 11.5, 99.5 * CELL + 11.5
    m.waypoint(cx - 40, cy, name="Cut_1"); m.waypoint(cx + 40, cy, name="Cut_2")
    m.routes = [dict(who="Folk", kind="tour", waypoints=["Cut_1", "Cut_2"], loop=False, pauses=[20, 20])]


def barrels_overlap(m):
    m.obj("Barrel", 190, -20)                                  # two barrels outdoors, their sprites run together
    m.obj("Barrel2", 190.8, -20)


def crop_on_fence(m):
    for k in range(4):                                         # a stretch of iron fence in the meadow, crops on its line
        m.wall(80 + k, 104 - k, "IronFence")
    for k in range(3):
        m.obj_px("GardenTomatos", (80.5 + k + 0.5) * CELL, (104.5 - k - 0.5) * CELL)


def candle_outdoors(m):
    m.obj("Candle1", 186, 12)                                  # a candle as a wayside light


def camp_swarm(m):
    for k in range(5):                                         # five men round one spot
        m.obj("Swordsman", 186 + 1.2 * (k % 3), -30 + 1.3 * (k // 3))


def _declare(m, kind="bedroom", extra=()):
    m.declare_rooms = [dict(number=1, building="test house", kind=kind, purpose="", tiles=0, box=[0, 0, 0, 0],
                            floor=[list(t) for t in rect_tiles(200, 222, -10, 10)])] + list(extra)


def blend_across_wall(m):
    # the meadow's grass blended onto the house's boards across its wall (TW-12, Thornwick 2026-10-08: "There does not
    # need to be blending on a wall"); the generator draws none there now, so the edge is planted after it
    from nox import EDGE_SIDES, SIDE_PIECES
    orig = m._edges
    def edges(seams=frozenset()):
        out = orig(seams)
        step = {v: k for k, v in EDGE_SIDES.items()}
        t, n = min((t, n) for t, n in seams if m.floor.get(t) == "WoodLight2" and m.floor.get(n) == "GrassNorm"
                   and (n[0] - t[0], n[1] - t[1]) in step)
        out.setdefault(t, []).append(["GrassNorm", "BlendEdge", SIDE_PIECES[step[(n[0] - t[0], n[1] - t[1])]][0]])
        return out
    m._edges = edges


def _fenced_pen(m):
    # an iron-fenced pen of cobble in the meadow, its \ sides (v = -36, v = -24) across a floor change
    m.room(184, 196, -36, -24, wall="IronFence", floor="RoughCobble")
    m.blending("GrassNorm", 0); m.blending("RoughCobble", 5, "BrickEdgeBrown")


def blend_beside_fence(m):
    # floors blend across iron fences (FN-1, "Always blending for fences"), never across any other wall: with a fenced
    # pen blending in the meadow, an edge across the house's wall is still an error
    _fenced_pen(m)
    blend_across_wall(m)


def ground_in_room(m):
    # a tile of the meadow's grass laid on the boards just inside the door (SW-4: "Tile blending on the inside of doors
    # seems consistently off")
    _declare(m)
    m.raw_floors = True
    t = min(rect_tiles(200, 222, -10, 10), key=lambda t: (abs(t[0] - t[1]), t[0] + t[1]))   # by the door, inside
    m.tile(t[0], t[1], "GrassNorm")


def piece_in_way(m):
    m.obj("Table1", 203.6, 0.5)                                # straight in from the double door in the NW wall


def statue_at_wall(m):
    m.obj("Statue2a", 221.0, 4.0)                              # faces SE, a unit from the SE wall (GW-7)


def _tour(m, who, pts, pauses, looks=None, kind="tour"):
    names = []
    for k, (x, y) in enumerate(pts):
        names.append(f"{who}_{k + 1}"); m.waypoint(x, y, name=names[-1])
    r = dict(who=who, kind=kind, waypoints=names, loop=True, pauses=pauses)
    if looks is not None: r["looks"] = looks; r["features"] = [None] * len(pts)
    m.routes = getattr(m, "routes", []) + [r]


def shared_stop(m):
    a, b = px(186, 20), px(190, -30)                           # Ann's and Bob's stops 14 px apart (GW-6)
    _tour(m, "Ann", [a, px(192, 30)], [20, 20], kind="beat")
    _tour(m, "Bob", [(a[0] + 10, a[1] + 10), b], [20, 20], kind="beat")


def facing_wall(m):
    # a stop just outside the house's NW wall, turned to face it (SW-2: "If an NPC is standing next to a building, have
    # them face away from the building")
    a = px(198.6, 3)
    _tour(m, "Cid", [a, px(188, 3)], [20, 20], looks=[list(px(213.4, 3)), list(px(173, 3))], kind="beat")


def short_tour(m):
    _tour(m, "Dot", [px(186, 25), px(192, 25)], [8, 8])        # two stops of 8 s (TW-9)


def dock_on_bank(m):
    for o in m.d["objects"]:                                   # the pond's dock moved up onto the meadow (AM-2)
        if str(o.get("type", "")).startswith("DockDown"): o["x"] -= 170; o["y"] -= 170


def minimap_on_corners(m):
    m.polygon("ST:World", (150, 150, 140), [(0, 0), (5888, 0), (5888, 5888), (0, 5888)])   # corners on the diagonal


def showpieces(m):
    for u, v in ((206, -6), (216, 4), (210, 6)): m.obj("Telescope1a", u, v)   # three telescopes in one room (SWR-1)


def statues_along_wall(m):
    for u in (204, 208, 212, 216): m.obj("Statue2g", u, 9.2)       # four statues lining the NE wall (SW-6)


def barrels_along_wall(m):
    _declare(m)                                                # a bedroom with barrels from corner to corner (AMR-4)
    for k in range(10): m.obj("Crate1", 202.0 + 1.9 * k, -9.0)


def one_kind_fills(m):
    for i in range(4):                                         # a hall of pews: 18 benches and the house's two pieces
        for j in range(5): m.obj("Bench1", 204 + 3.6 * i, -7 + 3.2 * j)


def keeper_off_counter(m):
    from kit.npcs import Population
    m.obj("TraderDesk1", 204, 6)                               # the counter by the NE wall...
    Population(m, random.Random(1)).shopkeeper("ShopkeeperYellow", *px(214, -4), [(1, "RedApple")])   # ...keeper mid-room


def civic_room(m):
    # the test house declared a living room (a kind kit/civic.py composes): its bed, table and lantern leave the S corner
    # bare, the NW wall bare and only three kinds of piece (QA round 1: "Much of the feedback boiled down to" too empty,
    # not enough diversity; "Dead spaces in the south corner are too common"; "more wall objects ... are needed")
    _declare(m, "living_room")


def throne_from_door(m):
    m.obj("DunMirThroneBase", 219.5, -2)                      # by the SE wall, its back to the room's doors (GW-7)


def stump_by_fire(m):
    m.obj("CampFire", 186, -30); m.obj("Stump1", 189.5, -30)   # a stump as a seat by a camp fire (SW-3)


def lone_bedroll(m):
    m.obj("CampFire", 236, -26); m.obj("Cot2", 230, -20)       # a bedroll strewn in a camp, no tent, no row (GW-4)
    # (on the meadow: at (236, 26) it had stood in the pond, open while the player could wade in, QA round 1)


def heap_of_crates(m):
    for k, t in enumerate(("Crate1", "Crate1", "Barrel", "Crate1", "Barrel", "Barrel")):   # a purposeless heap (GW-2)
        m.obj(t, 235 + 2.4 * (k % 3), -32 + 2.4 * (k // 3))


def empty_graveyard(m):
    _declare(m, "bedroom", [dict(number=2, building="", kind="graveyard", purpose="", tiles=0, box=[0, 0, 0, 0],
                                 yard=True, floor=[list(t) for t in rect_tiles(232, 250, 20, 34)])])
    m.obj("Tombstone1", 240, 26)                               # one headstone in a graveyard (SW-9)


def crate_by_apples(m):
    m.obj("Crate1", 186, -36); m.obj("TraderAppleCrate", 187.8, -36)     # a large crate 29 px off an apple crate (Q1K-1)


def bare_camp(m):
    m.obj("CampFire", 236, -26)                                # a camp of a fire and two bedrolls (Q1K-3)
    for v in (-22, -18): m.obj("Cot2", 230, v)                 # (on the meadow: (236, 26) is in the walled pond)


def beds_in_block(m):
    m.obj("CampFire", 236, -26)                                # three urchin beds side by side by their fire (Q1K-4)
    for k in range(3): m.obj("UrchinBed1", 226 + 2.5 * k, -32)


def racks_floating(m):
    for k in range(3): m.obj("OutdoorTraderArmorRack1", 190 + 2.5 * k, -20)     # a row of racks mid-meadow (Q1K-13)


def bare_jail(m):
    # two cells of a jail, each behind its JailDoor, both empty (Q1K-10)
    for v0, gap in ((-32, (101, 129)), (-22, (106, 124))):
        m.room(230, 240, v0, v0 + 8, wall="Cobblestone", floor="RoughCobble")
        m.door("JailDoor", gap, "/")


def mp_object(m): m.obj("Crown", 190, 10)                      # an arena's crown in a single-player map


def crammed_room(m):
    _declare(m, "living_room"); clutter(m)                     # a declared room furnished past its kind's cover


def tavern_tables(m):
    _declare(m, "tavern"); clutter(m)                          # 30 tables where a tavern of this size sets at most 4


def scattered_beds(m):
    for u, v in ((204, -6), (212, 2), (208, 7)): m.obj("WoodBed2", u, v)   # three beds of one kind at random spots


def stray_in_bedroom(m):
    _declare(m); m.obj("BlackPowderBarrel", 216, 8)            # a powder barrel in a bedroom (TP1-4, DV3-4)


def person_in_the_way(m):
    _tour(m, "Eve", [px(184, -20), px(196, -20)], [20, 20])
    from kit.npcs import Population                            # a townswoman standing on Eve's way (AMR-7)
    Population(m, random.Random(2)).creature("Maiden", *px(190, -20.3), action="guard", scr="Ida", aggr=0.0)


# ---- QA round 1's set pieces (review/qa1/setpieces.md, Q1X; validate/checks.py setpiece_faults) ---------------------
def _sqobj(m, t, si, sj, **extra):
    from kit.layout import square_px
    return m.obj_px(t, *square_px(si, sj), **extra)


def plain_well(m): m.obj("Well", 190, -30)                    # Q1X-4: a well that does not heal


def bare_well(m): _sqobj(m, "WishingWell", 95.5, -15.5, scr="HealWell1")   # Q1X-5: a well alone on the grass


def scattered_graves(m):
    for a, b in ((0, 0), (1.6, 0.7), (2.9, -0.4), (0.8, 2.1), (2.4, 1.6), (3.7, 1.2)):   # Q1X-8: graves at random
        _sqobj(m, "Tombstone1", 115.5 + a, -15.5 + b)


def graves_alone(m):
    for a in (0, 2, 4, 6):                                     # Q1X-11: graves in rows, mirrored, and nothing else
        for b in (0, 2):
            _sqobj(m, "Tombstone1", 113.5 + a, -15.5 + b)


def path_off_gate(m):
    # Q1X-10 (EX-GRAVEYARD-10, nox7): an iron fence with its gate centred on its side, the cobbled path through it a
    # square off the gate's middle
    from kit import yards as Y
    from kit.layout import point_cell, square_tile
    y = Y.Yard("graveyard", 92, -17, 5, 5, "j0")
    for side, ps in Y._fence_points(y).items():
        for p in ps: m.wall(*point_cell(*p), "IronFence")
    ps = Y._fence_points(y)["j0"]
    Y.door_between(m, "Gate", ps[2], ps[3])                    # its middle at i = 94.5
    for i in (94, 95, 96):                                     # the path's middle at 95.5
        for j in (-19, -18, -17, -16, -15):
            m.floor[square_tile(i, j)] = "RoughCobble"


def crops_on_grass(m):
    for r in (0, 1.2):                                         # Q1X-13: even rows of crops on the meadow's grass
        for k in range(5): _sqobj(m, "GardenCorn", 113.5 + 0.7 * k, -15.5 + r)


def crops_scattered(m):
    from kit.layout import square_tile
    for i in range(112, 118):
        for j in range(-17, -12): m.floor[square_tile(i, j)] = "DirtDark2"
    for a, b in ((0, 0), (0.9, 0.3), (1.5, -0.4), (2.6, 0.2), (0.4, 1.3), (1.7, 1.0), (2.2, 1.9), (3.1, 1.4)):
        _sqobj(m, "GardenTomatos", 113.2 + a, -15.8 + b)      # Q1X-14: crops strewn, not in rows


def _yard_rec(kind, side, gate, i0, i1, j0, j1):
    tiles = [[i + j, i - j] for i in range(i0, i1) for j in range(j0, j1)]
    return dict(number=2, building="", kind=kind, purpose="", tiles=len(tiles), box=[0, 0, 0, 0], yard=True,
                floor=tiles, side=side, gate=gate)


def shrine_of_one_kind(m):
    # Q1X-1: a shrine court of mana obelisks and nothing else
    _declare(m, "bedroom", [_yard_rec("shrine", "j0", [114.5, -18.5], 112, 117, -18, -12)])
    for a in (-2, 2):
        for b in (1, 4): _sqobj(m, "Obelisk", 114.5 + a, -18.5 + b)


def lopsided_well(m):
    # Q1X-2: a well yard whose barrels and bench all stand on one side of its axis
    _declare(m, "bedroom", [_yard_rec("well", "j0", [114.5, -18.5], 112, 117, -18, -12)])
    _sqobj(m, "WishingWell", 114.5, -16.0, scr="HealWell1")
    for t, a, b in (("WaterBarrel", 1.4, 2.5), ("Barrel", 1.6, 3.6), ("BarrelWithTools1", 2.0, 1.4), ("Bench1", 1.5, 4.4)):
        _sqobj(m, t, 114.5 + a, -18.5 + b)
    from kit.layout import square_tile
    for i in range(113, 117):
        for j in range(-18, -13): m.floor[square_tile(i, j)] = "CobblestoneGrayLight"


# ---- QA round 2 (2026-10-14): floors end at a hard line, a missing scene is an error [Q2T-6, Q2T-7] -------------------
def path_off_gate_i(m):
    # Q2X-2 (EX-GRAVEYARD-03/04: "The cobblestone path is not aligned correctly with the gate and mausoleum"): a gate in
    # an i side, its path of two squares laid where QA round 1's frame put them, half a square toward -j of the gate's
    # middle as the tiles are drawn (kit/yards.TILE_DJ)
    from kit import yards as Y
    from kit.layout import point_cell, square_tile
    y = Y.Yard("graveyard", 92, -17, 5, 5, "i1")
    for side, ps in Y._fence_points(y).items():
        for p in ps: m.wall(*point_cell(*p), "IronFence")
    ps = Y._fence_points(y)["i1"]
    Y.door_between(m, "Gate", ps[2], ps[3])                    # its middle at j = -16.0
    for i in range(93, 97):
        for j in (-16, -15):                                   # drawn over j -17.5..-15.5: their middle at -16.5
            m.floor[square_tile(i, j)] = "RoughCobble"


def empty_yard(m):
    # Q2T-7 (EX-GARDEN-02 "There is no garden"): a well yard declared, with nothing laid in it
    _declare(m, "bedroom", [_yard_rec("well", "j0", [114.5, -18.5], 112, 117, -17, -12)])


def paving_past_fence(m):
    # Q2T-6 (EX-WELL-02/05 "The brick extends outside of the enclosure"): a fenced well yard paved a row past its j0
    # fence, as QA round 1's ground (gj - 1..) had laid it
    from kit import yards as Y
    from kit.layout import point_cell, square_tile
    y = Y.Yard("well", 112, -17, 5, 5, "j0")
    for side, ps in Y._fence_points(y).items():
        for p in ps: m.wall(*point_cell(*p), "DilapidatedShort")
    _declare(m, "bedroom", [_yard_rec("well", "j0", [114.5, -18.5], 112, 117, -17, -12)])
    _sqobj(m, "WishingWell", 114.5, -15.0, scr="HealWell1")
    for i in range(112, 117):
        for j in range(-18, -12): m.floor[square_tile(i, j)] = "CobblestoneGrayLight"


def blended_pad(m):
    # Q2T-6 (the well set: "Instead of blending the stone floor with the surrounding grass and dirt, use a hard edge like
    # a curb"): an open well yard's grey cobbles blended into the meadow's grass
    from kit.layout import square_tile
    m.blending("GrassNorm", 0, "BlendEdge")
    m.blending("CobblestoneGrayLight", 6, "BlendEdge")
    _declare(m, "bedroom", [_yard_rec("well", "j0", [114.5, -18.5], 112, 117, -17, -12)])
    _sqobj(m, "WishingWell", 114.5, -15.0, scr="HealWell1")
    for i in range(113, 116):
        for j in range(-16, -13): m.floor[square_tile(i, j)] = "CobblestoneGrayLight"


def cobbles_under_bridge(m):
    # Q2T-6, Q2X-6 (BR-01, BR-11: "have that cobblestone path terminate where the bridge starts. Do not bring the
    # cobblestone all the way up to the bank of the river"): a rope bridge's span paved down to the water
    from kit.water import tile_at_uv, WATER_MATERIALS
    ww = Waterworks(m, random.Random(5))
    ww.stream([(184, -24), (256, -24)], width=2.2, wiggle=0.0)
    ww.rope_bridge((236, -36), (236, -12))
    for u in (234, 236, 238):
        for v in range(-36, -10, 2):
            t = tile_at_uv(u, v)
            if m.floor.get(t) and m.floor[t] not in WATER_MATERIALS and not m.floor[t].startswith("Wood"):
                m.floor[t] = "RoughCobble"
    ww.finish()


def _paved_crossing(m, stream, rows, along, a_uv, b_uv):
    """A stream, a RoughCobble road on `rows` across it (`along`: the axis it runs on, over the range given) and a rope
    bridge laid by the kit, which meets the road's paving with the deck's ends exactly (kit/water._road_to_deck)."""
    from kit.water import tile_at_uv, WATER_MATERIALS
    ww = Waterworks(m, random.Random(5))
    ww.stream(stream, width=2.2, wiggle=0.0)
    along_u = a_uv[1] == b_uv[1]                         # the bridge (and its road) runs along u
    for r in rows:
        for a in range(*along, 2):
            t = tile_at_uv(a, r) if along_u else tile_at_uv(r, a)
            if m.floor.get(t) and m.floor[t] not in WATER_MATERIALS: m.floor[t] = "RoughCobble"
    ww.rope_bridge(a_uv, b_uv)
    return ww


def road_short_of_bridge(m):
    # Q3X-1 (BR-01, BR-06, BR-11: "On one side of the bridge, the cobblestone ends before the bridge with a small gap of
    # dirt"): a RopeBridge2 (along v) whose road's last tile on the south-west bank is lifted, a tile of earth between
    from kit.water import tile_at_uv
    ww = _paved_crossing(m, [(184, -24), (256, -24)], (234, 236), (-40, -6), (236, -36), (236, -12))
    for u in (234, 236):
        v = max(v for v in range(-40, -24, 2) if m.floor.get(tile_at_uv(u, v)) == "RoughCobble")
        m.floor[tile_at_uv(u, v)] = "GrassNorm"
    ww.finish()


def road_under_bridge_end(m):
    # Q3X-1 ("On the other side of the bridge, it ends on the cobblestone"): a RopeBridge1 (along u) whose road runs a tile
    # on under the deck's north-west end
    from kit.water import tile_at_uv
    ww = _paved_crossing(m, [(244, -38), (244, 0)], (-28, -26), (222, 260), (236, -28), (252, -28))
    for v in (-28, -26):
        u = max(u for u in range(222, 244, 2) if m.floor.get(tile_at_uv(u, v)) == "RoughCobble")
        m.floor[tile_at_uv(u + 2, v)] = "RoughCobble"
    ww.finish()


# ---- the object knowledge base (Harrowby playtest, HB-1..HB-5; validate/checks.py check_pieces) ------------------------
def two_cauldrons(m):
    for u, v in ((206, -6), (214, 3)): m.obj("CauldronAnimated", u, v)          # HB-1: "Why are there two cauldrons?"


def four_chests(m):
    _declare(m)                                                # HB-3: "Why are there four treasure chests?"
    for u in (204, 208.5, 213): m.obj("Chest3", u, 9.2)
    m.obj("Chest2", 207, -9.2)


def bedroom_table_sets(m):
    _declare(m)                                                # HB-3: a bedroom with three table sets
    m.obj("RoundTable1", 206, -4); m.obj("SquareTable1", 210, 3)


def chest_by_hearth(m):
    m.obj("Fireplace3", 206, 9.0); m.obj("Chest3", 209.2, 9.2)  # HB-2: "chests ... too close to the hearth"


def shelves_wall(m):
    _declare(m, "storeroom")                                   # HB-5: a wall of identical log shelves
    for k in range(5): m.obj("LogShelvesFull4", 205 + 1.25 * k, 9.15)


def trophy_over_statue(m):
    m.obj("Statue2g", 205, 9.2); m.obj("WallTrophyMoose1", 205, 9.4)   # HB-2: "trophies ... with statues right on top"


def candelabras(m):
    for u, v in ((201.5, -8.5), (201.5, 8.5), (220.5, -8.5), (220.5, 8.5), (206, -9), (212, -9), (206, 9), (212, 9.2),
                 (216, -9)):
        m.obj("Candleabra1", u, v)                             # HB-4: "Too many candelabras"


def two_bellows(m):
    for u in (205, 211): m.obj("Bellows1", u, 9.0)             # a showpiece twice (HB-1: one of a kind)


# ---- Westwood's placement grammar (kit/grammar.py; the blind judges' faults, 2026-10-06) ---------------------------
def g_free_lights(m):
    _declare(m)
    m.obj("Bed1", 206, 8.6)
    for u, v in ((209, -3), (214, 3), (215, -5)): m.obj("Candleabra1", u, v)   # candelabras loose on the floor


def g_floating_tables(m):
    _declare(m, "living_room")
    for u, v in ((209, -3), (214, 4)): m.obj("RoundTable1", u, v)        # two tables out in the open, no carpet


def g_lone_chairs(m):
    _declare(m)
    for u, v in ((207, -4), (212, 2), (208, 4)): m.obj("WoodenChair1", u, v)    # chairs drawn up to nothing


def g_lone_stock(m):
    _declare(m, "storeroom")
    for u, v in ((206, -3), (211, 3), (207, 4)): m.obj("Barrel", u, v)   # three barrels alone in the open


def g_even_rows(m):
    _declare(m, "storeroom")
    for u in (203, 207, 211, 215): m.obj("Crate1", u, 9.2)               # crates at equal gaps on two walls
    for v in (-6, -3, 0, 3): m.obj("Barrel", 221.9, v)


def g_plant(m):
    _declare(m)
    m.obj("Plant1", 220.5, 8.5)                                          # a plant in a bedroom (Westwood: none in 28)


def g_twins(m):
    _declare(m, "storeroom")
    for u in (203, 209, 215): m.obj("Barrel", u, 9.2); m.obj("Barrel", u + 1.3, 9.2)   # three stamped pairs


def g_ring(m):
    _declare(m, "living_room")
    for c in ((207, -4), (215, 4)):                                       # four chairs at each table's quarter points
        m.obj("RoundTable1", c[0], c[1])
        for du, dv in ((-1.6, 0), (1.6, 0), (0, 1.6), (0, -1.6)): m.obj("WoodenChair1", c[0] + du, c[1] + dv)


def g_corners(m):
    _declare(m, "storeroom")
    for u, v in ((220.6, -8.6), (202.4, 8.4)): m.obj("Barrel", u, v)    # one barrel to a corner


def g_stepped(m):
    _declare(m, "storeroom")
    for k in range(3): m.obj("Barrel", 207 + 1.6 * k, -5 + 1.6 * k)      # barrels in an evenly stepped diagonal


def g_mixed_beds(m):
    _declare(m, "barracks")
    for k, t in enumerate(("Cot1", "WoodBed1", "Cot1", "WoodBed1", "Cot1")): m.obj(t, 203 + 3.6 * k, 8.4)   # two kinds


# ---- QA round 1, rooms (review/qa1/rooms.md Q1R-*; validate/checks.py check_qa1_rooms) --------------------------------
def q1_nightstand(m):
    _declare(m); m.obj("Nightstand3", 216.6, 6.8)              # Q1R-3: a nightstand on one side of the bed only


def q1_chest_corner(m):
    _declare(m); m.obj("Chest3", 220.8, 9.0)                   # Q1R-4: "the chest in the north corner looks out of place"


def q1_south(m):
    _declare(m)                                                # Q1R-6: "dead spaces in the south corner are too common"


def q1_obelisks(m):
    _declare(m, "ogre_den")                                    # Q1R-10: three obelisks, no symmetric pair
    for u, v in ((202, 8), (220, 8), (210, -8)): m.obj("ObeliskPrimitive", u, v)


def q1_cell(m):
    _declare(m, "cell"); m.obj("Cot1", 203, 8.4)               # Q1R-11: "very large for a single cell with one bed"


def q1_cellar_kinds(m):
    _declare(m, "cellar")                                      # Q1R-13: "This entire room includes only barrels"
    for k in range(6): m.obj("Barrel", 202 + 1.4 * k, 9.2)


def q1_cask(m):
    _declare(m, "cellar")                                      # Q1R-13: "the gigantic wine barrels are way too close"
    m.obj("LargeBarrel2", 212, 0); m.obj("Barrel", 213.2, 1.6)


def q1_garden_floor(m):
    _declare(m, "conservatory"); m.obj("Plant4", 208, 2)       # Q1R-14: "Plants coming out of the floor tile"


def q1_wells(m):
    _declare(m, "conservatory")                                # Q1R-14: "a maximum of one well"
    for u in (205, 212): m.obj("Well", u, 2)


def q1_counter(m):
    _declare(m, "gear_store")                                  # Q1R-1: "I don't see where the merchant would fit"
    for u in (203, 206): m.obj("TraderArmorRack1", u, 8.6)


def q2_off_centre(m):
    # QA round 2, Q2T-1 (RM-GALLERY-01/02: "The gallery is not centered in the room"): a declared gallery whose three
    # statue pairs are mirrored about v = -1, the room's middle being v = 0 (walls at -10 and 10)
    _declare(m, "gallery")
    for u in (205, 210, 216): m.obj("Statue2c", u, -6); m.obj("Statue2g", u, 4)


def q2_benches_away(m):
    # QA round 2, Q2T-3 (RM-HALL-01: "The benches are facing the wrong way ... they should face southwest"): a declared
    # hall whose benches by the side walls turn their backs to the aisle (Bench2 faces -v, Bench4 +v)
    _declare(m, "hall")
    for u in (204, 209): m.obj("Bench2", u, -6.5); m.obj("Bench4", u, 6.5)


def q2_shop_blocked(m):
    # QA round 2, Q2C-7 (RM-SHOP-05: "No path from the door to the shopkeeper's desk"): the counter across the shop from
    # its door, a steel crate in the walk between them
    _declare(m, "shop")
    m.obj("TraderDesk1", 218, 0)
    m.obj("CrateSteel1", 208, 0)


def bar_in_open(m):
    # QA round 2, RM-TAVERN-04: "The bar must be connected to the wall at both ends": a run of bar standing in the middle
    # of the room, more than six units from any wall at either end (the gap rule had looked for a wall near the end only)
    for u in (207, 209, 211): m.obj("BarPiece4A", u, 0)


def q1_racks(m):
    _declare(m, "barracks")                                    # Q1R-9: a wall of beds and nothing of a soldier's gear
    for k in range(3): m.obj("Cot2", 203 + 3.0 * k, 8.4)


def q1_empty(m):
    _declare(m, "cellar")                                      # Q1R-23: "spaces are too empty": a cellar of three barrels
    for u in (204, 206, 208): m.obj("Barrel", u, 9.2)


def q1_bare_bedroom(m):
    _declare(m)                                                # Q1R-23 round 3: a bed, a lone table, two identical rugs
    m.obj("Chest3", 210, 9.2); m.obj("SquareTable1", 206, -6); m.obj("WoodenChair1", 207.6, -6)
    for u in (205, 215): m.obj("RedRug4", u, 2)


def q1_hearth(m):
    _declare(m, "living_room"); m.obj("Fireplace3", 206, 9.1)  # Q1R-19: a hearth on the bare boards


# ---- QA round 2's shared room rules (review/qa2/ledger.md Q2T-4, Q2T-5; validate/checks.py check_qa2_space) --------
def q2_crates_touch(m):
    _declare(m, "cellar")                                      # Q2T-4: RM-CELLAR-04 "two crates ... touching"
    for u in (206, 209): m.obj("Crate1", u, 9.1)


def q2_big_close(m):
    _declare(m, "shrine")                                      # Q2T-4: RM-SHRINE-02 "The mana obelisk is too close to the statue"
    m.obj("Statue2a", 210, 0); m.obj("ObeliskPrimitive", 211.4, 0)


def q2_rug_fire(m):
    _declare(m, "living_room")                                 # Q2T-4: RM-TAVERN-01 "the bearskin rug ... too close to the fireplace"
    m.obj("Fireplace3", 206, 9.1); m.obj("BearskinRug1", 206, 6.24)


def q2_chest_out(m):
    _declare(m); m.obj("Chest3", 210, 8.6)                     # Q2T-5: RM-BEDROOM-03 a chest "sticking out too far"


def q2_bench_mid(m):
    _declare(m); m.obj("Bench1", 208, 0)                       # Q2T-5: RM-BEDROOM-01 a bench "in the middle of the room"


def q2_chests_unlined(m):
    _declare(m)                                                # Q2T-5: RM-BEDROOM-03 "lined up with the one on the left"
    m.obj("Chest3", 205, 9.5); m.obj("Chest3", 209, 9.2)


def q2_chests_scattered(m):
    _declare(m, "barracks")                                    # Q2F-2: "fix chest": three beds, two chests anywhere
    for k in range(3): m.obj("Cot2", 203 + 3.0 * k, 8.4)
    m.obj("Chest3", 206, -9.2); m.obj("Chest3", 214, -9.2)


# ---- QA round 3, the barracks' chests (validate/checks.py qa2_space_flags; review/qa3/ledger-rooms.md Q3R-6..8) --------
def q3_chests_sideways(m):
    _declare(m, "barracks")                                    # Q3R-6: RM-BARRACKS-01 "perpendicular to the beds"
    for u in (203, 207, 211):
        m.obj("Cot2", u, 8.4); m.obj("Chest4", u, 5.75)       # the NW wall's chest at the foot of a bed headed NE


def q3_chests_far(m):
    _declare(m, "barracks")                                    # Q3R-7: RM-BARRACKS-02 "slightly closer to the three beds"
    for u in (203, 207, 211):
        m.obj("Cot2", u, 8.4); m.obj("Chest3", u, 5.65)       # facing away, 0.6 units off the foot


def q3_pair_gap_bare(m):
    _declare(m, "barracks")                                    # Q3R-8: RM-BARRACKS-03 "the empty gap between the pairs"
    for u in (203, 205, 209, 211):
        m.obj("Cot2", u, 8.4); m.obj("Chest3", u, 6.05)       # two pairs of beds, a chest snug at every foot, none between


def q2_ogre_pen_in_house(m):
    _declare(m, "ogre_pen")                                    # Q2F-6: "This is using human buildings and floors"
    m.obj("OgreStraw1", 204, 6)


def _cellar(m):
    """A walled cellar away from the meadow (no way in on foot)."""
    m.room(280, 300, -10, 10, wall="BrickPlain", floor="GreenBrick")
    return px(290, 0)


def tp_unlinked(m):
    m.obj("CaveElevator", 196, 20)                            # a working platform that names no pit


def tp_in_wall(m):
    m.obj_px("TeleportPentagram", *px(196, 20), key="P", link="M")
    m.obj_px("InvisibleTeleportPentagram", 91 * CELL + 11.5, 89 * CELL + 11.5, key="M")   # the landing in the outer wall


def tp_stranded(m):
    from kit.transport import Transporters
    Transporters(m).add("portal", px(196, 20), _cellar(m), "TpOne", two_way=False)


def tp_bounce(m):
    from kit.transport import Transporters
    tp = Transporters(m)
    tp.add("portal", px(196, 20), _cellar(m), "TpBack")
    tp.add("portal", px(190, -24), px(196, 20), "TpOnto", two_way=False, arrive_b=px(197, 21))


def tp_serves(m):
    from kit.transport import Transporters
    far = _cellar(m)
    m.room(304, 316, -6, 6, wall="BrickPlain", floor="GreenBrick")      # a second cellar beside it, sealed off
    Transporters(m).add("lift", px(196, 20), far, "TpLift", serves=[px(310, 0)])


def tp_near_wall(m):
    m.obj_px("TeleportPentagram", *px(196, 20), key="P", link="M")
    m.obj_px("InvisibleTeleportPentagram", 91 * CELL + 3, 90 * CELL + 3, key="M")     # a landing against the outer wall


def tp_pocket(m):
    from kit.transport import Transporters
    m.room(282, 286, -2, 2, wall="BrickPlain", floor="GreenBrick")        # a closet of a few cells
    Transporters(m).add("portal", px(196, 20), px(284, 0), "TpPkt", two_way=False)


def tp_missing(m):
    from kit.transport import Transporters
    t = Transporters(m).add("portal", px(196, 20), _cellar(m), "TpMis")
    x, y = px(200, 24)                                    # the sidecar names a pad the map does not hold
    t.objects.append(("pad", dict(type="TeleportPentagram", x=x, y=y, scr="TpMisGone")))


def tp_unreached(m):
    from kit.transport import Transporters
    Transporters(m).add("portal", _cellar(m), px(196, 20), "TpUnr", two_way=False)   # starts in the sealed cellar


# ---- in-game behaviour (QA round 1, 2026-10-13: validate/checks_game.py) ------------------------------------------
def _strings(m, table):
    """The map's string table beside where the self-test builds it (a design's q.write_strings)."""
    import json
    d = os.path.join(OUT, m.d["name"])
    os.makedirs(d, exist_ok=True)
    json.dump(table, open(os.path.join(d, m.d["name"] + ".strings.json"), "w", encoding="utf-8"))


def plank_sign(m):
    m.obj_px("PlankSign1", *px(190, 6), xfer={"Text": "GeneralPrint:WellSign"})


def sign_two_lines(m):
    key = m.d["name"] + ":Sign1"
    _strings(m, {key: "THE OLD BRIDGE\nTo the mill."})
    m.obj_px("Sign1", *px(190, 6), xfer={"Text": key})


def dry_well(m):
    m.obj("Well", 190, -20)
    m.heal_wells = False                      # as if the build had not written wells.go


def still_fish(m):
    m.obj_px("FishSmall", *px(240, 22), xfer={"DefaultAction": 10, "ActionRoamPathFlag": 255})


def _villager(m, x, y, face=None, name=None):
    from kit.npcs import facing
    xf = {"DefaultAction": 4, "Aggressiveness": 0.0}
    if face: xf["DirectionId"] = facing(face[0] - x, face[1] - y)
    return m.clone(r"C:\GOG Games\Nox\maps\Con02a\Con02a.map", "Con02a:Lydia", x, y, name=name or "", xfer=xf)


def villager_in_door(m):
    _villager(m, DOOR_GAP[0] * CELL + 2, DOOR_GAP[1] * CELL + 25, name="Doorman")


def villagers_at_door(m):
    import math
    c = (CORNER_GAP[0] * CELL + CELL / 2, CORNER_GAP[1] * CELL + CELL / 2)
    t = (-1 / math.sqrt(2), 1 / math.sqrt(2)); n = (1 / math.sqrt(2), 1 / math.sqrt(2))
    for k, side in enumerate((1, -1)):
        _villager(m, c[0] - n[0] * 20 + t[0] * 50 * side, c[1] - n[1] * 20 + t[1] * 50 * side, name=f"Waiter{k + 1}")


def villager_faces_wall(m):
    x, y = px(198.6, -4)                      # outside the house's NW wall (u = 200), facing it
    _villager(m, x, y, face=px(201, -4), name="WallStarer")


def nameless_item(m):
    m.obj("BlackPotion", 214, 0)              # Westwood's placeholder name "BlackPotionPrettyName"


def _shop(m, wares):
    m.obj_px("ShopkeeperYellow", *px(212, 4), xfer={"DefaultAction": 4, "Aggressiveness": 0.0, "Immortal": True,
                                             "ShopkeeperInfo": {"BuyValueMultiplier": 1.0, "SellValueMultiplier": 0.33,
                                                                "ShopkeeperGreetingText": "", "ShopItems": [
                                                                    {"Name": n, "Count": 1, "SpellID": "", "Ench1": "",
                                                                     "Ench2": "", "Ench3": "", "Ench4": ""} for n in wares]}})


def useless_ware(m):
    _shop(m, ["AmuletofCombat"])              # no price, no use: a shop sells it for nothing and it does nothing


def dear_ware(m):
    m.d["info"]["description"] += " [act:1]"        # the Hollow Choir's first act: Westwood's chapter 2 shops, 550 at most
    _shop(m, ["BattleAxe"])
# ---- QA round 1 (2026-10-12): water, crossings, docks, doorsteps, floor patches -----------------------------------------
def _water(m, c):
    return "Water" in m.floor.get(c, "")


def wade(m):
    for c in [c for c, w in m.wallmap.items() if w["material"].startswith("Invisible") and _water(m, c)]:
        m.remove_wall(*c)                                     # the pond's shore walls gone: the player walks in


def fingers(m):
    shore = sorted(c for c in m.floor if _water(m, c) and c not in m.wallmap or (_water(m, c) and any(
        not _water(m, (c[0] + a, c[1] + b)) for a, b in ((1, 1), (-1, -1), (1, -1), (-1, 1)))))
    shore = [c for c in shore if sum(not _water(m, (c[0] + a, c[1] + b)) for a, b in ((1, 1), (-1, -1), (1, -1), (-1, 1))) == 1]
    for c in shore[::3][:12]:
        m.floor[c] = "GrassNorm"                              # a tile of bank poking into the water, three sides wet
        m.remove_wall(*c)


def _brook_bridge(m):
    ww = Waterworks(m, random.Random(9))
    brook = ww.stream([(184, -30), (256, -30)], width=2.2, wiggle=0.0)
    res = ww.plank_bridge(brook, at=(236.0, -30.0), along="v", deck_width=2)
    ww.finish()
    return res


def road_off_bridge(m):
    res = _brook_bridge(m)
    vs = [x - y for x, y in res["tiles"]]
    for v in (min(vs) - 2, min(vs) - 4, max(vs) + 2, max(vs) + 4):
        u = 240                                               # one row of road, beside the deck's rows
        x, y = (u - 2 + v) // 2, (u - 2 - v) // 2
        m.floor[(x, y)] = "DirtDark2"


def bridge_uneven(m):
    res = _brook_bridge(m)
    us = sorted({x + y + 2 for x, y in res["tiles"]}); vs = [x - y for x, y in res["tiles"]]
    for u in us:
        for v in (max(vs) + 2, max(vs) + 4, max(vs) + 6):    # the deck runs three tiles more onto one bank
            m.floor[((u - 2 + v) // 2, (u - 2 - v) // 2)] = "WoodSlatFloor"


def dock_too_long(m):
    ww = Waterworks(m, random.Random(11))
    pond = ww.pond((196, -26), radius=5, roughness=0.0)
    ww.dock(pond, "down", length=3, at=(184.0, -26.0))        # forced: the kit itself keeps a dock to a third
    ww.finish()


def dock_on_wall(m):
    ww = Waterworks(m, random.Random(5))
    puddle = ww.pond((190, -24), radius=3)
    ww.dock(puddle, "down", length=1, at=(183.0, -24.0))     # forced: its landing against the meadow's west wall
    ww.finish()


def two_docks(m):
    ww = Waterworks(m, random.Random(11))
    pond = ww.pond((196, -26), radius=6, roughness=0.0)
    ww.dock(pond, "down", length=1, at=(182.0, -26.0))
    pond.docks = []                                           # forced: the kit allows one to a pond this size
    ww.dock(pond, "up", length=1, at=(196.0, -12.0))
    ww.finish()


def dock_by_bank(m):
    ww = Waterworks(m, random.Random(13))
    brook = ww.stream([(190, -30), (256, -30)], width=5.0, wiggle=0.0)
    ww.dock(brook, "down", length=2, at=(186.0, -26.0))       # forced: along the stream, a tile off its bank
    ww.finish()


def doorstep(m):
    # the house's floor laid out onto the doorstep of its west door (the old _door_thresholds)
    for t in ((98, 98), (99, 99), (97, 99), (99, 97), (98, 100), (100, 98)):
        m.floor[t] = "WoodLight2"


def hard_patch(m):
    m._ground_blend = lambda: None                           # the kit's blending of every ground left out
    for t in ((104, 124), (105, 125), (105, 123), (106, 124)):     # u 228, v -20: open meadow
        m.floor[t] = "DirtLight2"
# ---- the sacred rooms (QA round 1, review/qa1/sacred.md Q1C): the test house declared a chapel, its double door in the
# middle of its NW wall (v = 0), so the altar belongs at the SE wall's middle (u ~ 220.5, v = 0)
def _chapel(m, kind="chapel"):
    _declare(m, kind)
    m.d["objects"] = [o for o in m.d["objects"] if o.get("type") not in ("WoodBed2", "Table1", "Wolf")]


def altar_off_axis(m):
    _chapel(m)
    m.obj("DunMirAltar1", 220.4, 6.5)                          # Q1C-2: the altar off the door's line


def pews_one_side(m):
    _chapel(m)
    m.obj("DunMirAltar1", 220.4, 0)
    for u in (210, 213, 216): m.obj("Bench1", u, 4.5)          # Q1C-1: pews on one side of the aisle only


def carpet_one_side(m):
    _chapel(m)
    m.obj("DunMirAltar1", 220.4, 0)
    m.raw_floors = True
    for t in rect_tiles(206, 216, 2, 8): m.tile(t[0], t[1], "RugRed")     # Q1C-3: the runner off the middle line


def runner_unit_off(m):
    # QA round 2 (Q2T-2, recurring Q1C-3): "The carpet is slightly off-center with the door and altar" (RM-CHAPEL-01..03):
    # a runner two squares wide, centred on the door's line (v = 1, between the double door's cells) as the kit read a
    # tile (centre x - y), a unit off it as the editor draws one (x - y - 1): drawn, its middle stands at v = 0
    _chapel(m)
    m.obj("DunMirAltar1", 220.4, 1)
    m.raw_floors = True
    for x, y in [(x, y) for x in range(80, 120) for y in range(80, 120)
                 if 204 <= x + y <= 216 and (x + y) % 2 == 0 and x - y in (0, 2)]:
        m.tile(x, y, "RugRed")


def ring_off_carpet(m):
    # QA round 2 (Q2T-2): "The mana obelisk arrangement is not centered on the carpet" (RM-SHRINE-03; round 2's mana
    # rooms likewise): a ring of four obelisks (2 units out) round an altar at (212, 0) on a carpet of three by three
    # squares centred
    # there as the kit read a tile, drawn a unit toward -v
    _chapel(m, "mana_room")
    m.obj("DunMirAltar1", 212, 0)
    for du, dv in ((2, 2), (-2, -2), (2, -2), (-2, 2)): m.obj("Obelisk", 212 + du, dv)
    m.raw_floors = True
    for x, y in [(x, y) for x in range(80, 120) for y in range(80, 120)
                 if 208 <= x + y <= 212 and (x + y) % 2 == 0 and x - y in (-2, 0, 2)]:
        m.tile(x, y, "RugRed")


def same_altars(m):
    # Q1C-4: three chapels, each ending in the same Dun Mir altar
    m.room(204, 222, -36, -20, wall="StuccoLightWood", floor="WoodLight2")
    m.room(228, 246, -36, -20, wall="StuccoLightWood", floor="WoodLight2")
    m.door("WoodenDoor", (88, 116), "/"); m.door("WoodenDoor", (100, 128), "/")
    extra = [dict(number=k + 2, building=f"chapel {k}", kind="chapel", purpose="", tiles=0, box=[0, 0, 0, 0],
                  floor=[list(t) for t in rect_tiles(u0, u0 + 18, -36, -20)]) for k, u0 in enumerate((204, 228))]
    _declare(m, "chapel", extra)
    m.d["objects"] = [o for o in m.d["objects"] if o.get("type") not in ("WoodBed2", "Table1", "Wolf")]
    for u, v in ((220.4, 0), (220.4, -28), (244.4, -28)): m.obj("DunMirAltar1", u, v)


def same_shrine_altars(m):
    # Q3R-2: three shrines, each round Dun Mir's square stone altar ("stop using that same altar so often")
    m.room(204, 222, -36, -20, wall="StuccoLightWood", floor="WoodLight2")
    m.room(228, 246, -36, -20, wall="StuccoLightWood", floor="WoodLight2")
    m.door("WoodenDoor", (88, 116), "/"); m.door("WoodenDoor", (100, 128), "/")
    extra = [dict(number=k + 2, building=f"shrine {k}", kind="shrine", purpose="", tiles=0, box=[0, 0, 0, 0],
                  floor=[list(t) for t in rect_tiles(u0, u0 + 18, -36, -20)]) for k, u0 in enumerate((204, 228))]
    _declare(m, "shrine", extra)
    m.d["objects"] = [o for o in m.d["objects"] if o.get("type") not in ("WoodBed2", "Table1", "Wolf")]
    for u, v in ((211, 0), (213, -28), (237, -28)): m.obj("DunMirAltar1", u, v)


def bare_chapel(m):
    _chapel(m)
    m.obj("DunMirAltar1", 220.4, 0)                             # Q1C-19: an altar and one pair of pews, nothing else
    for v in (-3.5, 3.5): m.obj("Bench1", 214, v)


def crypt_without_dead(m):
    _chapel(m, "crypt")
    m.obj("Coffin1", 214, 0)                                   # Q1C-14, Q1C-17: one coffin and nothing else


def crypt_crates(m):
    _chapel(m, "crypt")                                        # Q3R-1: "the pair of crates in each room look off"
    for v in (-4, 4): m.obj("Coffin1", 212, v)
    for v in (-8.6, 8.6): m.obj("Crate1", 206, v)


def wooden_door_in_lotd(m):
    for c, w in m.wallmap.items():                            # Q1C-18: the house in the Land of the Dead's walls...
        if w.get("material") == "StuccoLightWood": w["material"] = "LOTDOrnate"
    # (...its corner door a plain wooden one)
# ---- QA round 1, the unrated works rooms (validate/checks.py works_flags; review/qa1/works.md Q1B) ----------------------
def q1_shrine_off_axis(m):
    _declare(m, "shrine")                                      # the main door at (201, 0): the axis runs along v = 0
    m.obj("DunMirAltar1", 219, 0)
    for u, v in ((206, -5), (212, 3), (216, -7)): m.obj("Obelisk", u, v)     # obelisks with no partner across it


def q1_store_of_barrels(m):
    _declare(m, "storeroom")                                   # a storeroom of one kind of barrel
    for k in range(8): m.obj("Barrel", 204 + 1.3 * (k % 4), -8.5 + 1.3 * (k // 4))


def q1_forge_on_boards(m):
    _declare(m, "smithy")                                      # the forge on the bare boards
    m.obj("CinderBin1", 210, 8.8)


def q1_bare_s_corner(m):
    _declare(m, "guardroom")                                   # everything at the N end, the S corner (222, -10) bare
    for u, v in ((204, 6), (204, -6), (206, 0)): m.obj("Barrel", u, v)


# ---- QA round 2, the works rooms (validate/checks.py qa2_works_flags; review/qa2/ledger.md Q2V-3, Q2V-4, Q2T-8) ----------
def q2_winch_crates(m):
    _declare(m, "winch_room")                                  # Q2V-4: "too cluttered with crates and barrels"
    for k in range(30): m.obj("Barrel" if k % 2 else "CrateSteel1", 203.5 + 3.2 * (k % 5), -8 + 3.2 * (k // 5))


def q2_keeper_space(m):
    _declare(m, "smithy")                                      # Q2V-3: "a barrel and a mannequin behind the desk"
    m.obj("TraderDesk1", 211, 7.0); m.obj("Barrel", 211, 9.0)


def q3_smithy_mid_stock(m):
    _declare(m, "smithy")                                      # Q3R-9: RM-SMITHY-04 "A little overcrowded with objects"
    for k in range(18): m.obj("Barrel2" if k % 2 else "BarrelSteel1", 205 + 1.4 * (k % 6), -4 + 3.0 * (k // 6))


# ---- QA round 3's floor and batch rules (review/qa3/ledger-civic.md; validate/checks.py check_qa3) -------------------
def _drawn_tile(u, v):
    """The floor tile drawn centred at uv (u, v) (u even, v odd: tile (x, y) at (x + y + 2, x - y - 1))."""
    return (u + v - 1) // 2, (u - v - 3) // 2


def q3_carpet_blended(m):
    # Q3C-1 (the tavern set: "The other carpets are all blended into the floor ... A carpet doesn't blend into the floor
    # underneath. It has solid, distinct edges"): a declared tavern's carpet of three by three squares spilling a
    # BlendEdge onto the boards round it
    _declare(m, "tavern")
    m.raw_floors = True
    rect = {_drawn_tile(u, v) for u in (208, 210, 212) for v in (-3, -1, 1)}
    for t in rect: m.tile(*t, "RugRed")
    m.blending("RugRed", 40, "BlendEdge")
    for t in rect:
        for a, b in ((1, -1), (-1, -1), (1, 1), (-1, 1), (0, 2), (0, -2), (2, 0), (-2, 0)):
            n = (t[0] + a, t[1] + b)
            if n not in rect: m.local_blend[n] = -60; m.local_from.setdefault(n, set()).add("RugRed")


def q3_patch_unbordered(m):
    # Q3C-4 (RM-GREATHALL-01..03: "The brick tiling along the exterior of this room is not properly bordered"): a declared
    # great hall's band of brick along its NE wall laid with hard edges
    _declare(m, "great_hall")
    m.raw_floors = True
    for u in range(204, 220, 2): m.tile(*_drawn_tile(u, 9), "RedBrick")


def q3_bar_opening(m):
    # Q3C-2 (the tavern set: "All taverns need to have the floor properly transitioned between the bar floor and the
    # main tavern floor where the bar entrance / gap is"): a bar in the house's E corner, brick behind it, the counter's
    # opening at v = 7 with the brick meeting the boards there unbordered
    _declare(m, "tavern")
    m.raw_floors = True
    for u in (218, 220, 222):
        for v in (5, 7, 9): m.tile(*_drawn_tile(u, v), "RedBrick")
    m.obj("BarCorner1C", 216, 3)
    for u in (218, 220): m.obj("BarPiece2A", u, 3)
    for v in (5, 9): m.obj("BarPiece1A", 216, v)
    m.obj("BarHingedTop", 216, 7)


def q3_same_throne_rooms(m):
    # Q3C-6 (the throne room set: "Individually, they are all very good. But as a whole, they are very repetitive and
    # all too similar"): three declared throne rooms of the same pieces
    rooms = [(182, 196, -36, -22), (230, 252, -36, -22)]
    for k, (u0, u1, v0, v1) in enumerate(rooms):
        m.room(u0, u1, v0, v1, wall="StuccoLightWood", floor="WoodLight2")
    _declare(m, "throne_room", [dict(number=2 + k, building=f"test hall {k}", kind="throne_room", purpose="", tiles=0,
                                     box=[0, 0, 0, 0], floor=[list(t) for t in rect_tiles(*r)])
                                for k, r in enumerate(rooms)])
    m.d["objects"] = [o for o in m.d["objects"] if o.get("type") not in ("WoodBed2", "Table1", "Wolf")]
    for cu, cv in ((211, 0), (189, -29), (241, -29)):
        for t, du, dv in (("Statue2a", -3, -3), ("Statue2a", -3, 3), ("Column5", 2, -3), ("Column5", 2, 3),
                          ("Brazier", 4, -2), ("Brazier", 4, 2)):
            m.obj(t, cu + du, cv + dv)


def q3_hall_ranks(m):
    # Q3C-7 (RM-HALL-01/03: "Incoherent, random , cluttered with too many pillars and statues"): a declared hall whose
    # columns and statues stand in four ranks across its width
    _declare(m, "hall")
    for v in (-6, -2, 2, 6):
        for u in (205, 211, 217): m.obj("Column5" if v in (-2, 2) else "Statue2c", u, v)


CASES = [  # (map name, defect, expected check, expected severity, description)
    ("STclean", None, None, None, "clean map: no errors"),
    ("STwall", black_wall, "wall_pieces", "error", "black wall (wall style with no artwork) - Mossford playtest"),
    ("SThole", hole, "boundary", "error", "hole in the outer wall"),
    ("STinvis", invisible_boundary, "boundary", "error", "outer wall replaced by invisible wall - Mossford playtest"),
    ("SThalf", lone_half_door, "doors", "error", "half of a double door alone in a 1-cell opening - DysVale playtest"),
    ("STjamb", jamb, "wall_shapes", "error", "corner beside a door shaped as a straight piece - DysVale playtest"),
    ("STdock", dock_misaligned, "kits", "error", "dock pieces off Westwood's steps - DysVale playtest"),
    ("STclutr", clutter, "rooms", "warning", "room crammed with furniture - DysVale playtest"),
    ("STwpjmb", waypoint_at_jamb, "routes", "error", "waypoint pressed against a door's jamb - 2026-10-05 playtest",
     "against a wall"),
    ("STwpcut", route_cuts_doorway, "routes", "error", "route cutting through a doorway at an angle - 2026-10-05 playtest",
     "doorway"),
    ("STdoorw", doorway, "doorways", "error", "barrel standing in a doorway"),
    ("STrug", rug_on_grass, "floors", "error", "rug laid straight onto grass"),
    ("STvoid", void_creature, "objects", "error", "creature standing in the void"),
    ("STseal", sealed_room, "reachability", "error", "creature in a room with no way in"),
    ("STnostrt", no_start, "setup", "error", "no player start"),
    ("STpuddl", dock_across_puddle, "composition", "warning", "dock spanning a puddle to the far bank - DysVale v0.4 playtest"),
    ("STlites", lights_side_by_side, "composition", "warning", "two candelabras side by side - DysVale v0.4 playtest"),
    ("STchest", chest_blocked, "composition", "warning", "table standing right in front of a chest - DysVale v0.5 playtest"),
    ("STbridg", bridge_into_wall, "composition", "warning", "bridge ending against the boundary wall - DysVale v0.5 playtest"),
    ("STchacr", chest_across_wall, "composition", "warning", "chest standing across the wall - DysVale v0.6 playtest"),
    ("STstump", stumps_bunched, "composition", "warning", "stumps bunched in one spot - DysVale v0.6 playtest"),
    ("STwideb", wide_bridge, "composition", "warning", "plank bridge 4 tiles wide on a narrow stream - DysVale v0.6 playtest"),
    ("STpairl", pair_on_wrong_line, "doors", "error", "door pair whose halves do not line up - DysVale v0.6 playtest"),
    ("STtorch", torch_in_house, "composition", "warning", "open torch inside a house - TreePlace v0.1 playtest", "open torch"),
    ("STfood", food_by_table, "composition", "warning", "meat lying by a table - TreePlace v0.1 playtest", "lies by"),
    ("STends", seated_at_ends, "composition", "warning", "long table seated only at its ends - TreePlace v0.1 playtest",
     "only at its ends"),
    ("STbunks", mixed_bunks, "composition", "warning", "bunk room of mixed bed kinds - TreePlace v0.1 playtest", "kinds"),
    ("STnoset", table_no_seats, "composition", "warning", "barracks table with no seats - TreePlace v0.1 playtest",
     "has no seats"),
    ("STlopsd", lopsided, "composition", "warning", "furniture packed into one end of a room - TreePlace v0.1 playtest",
     "fills only"),
    ("STbeds", packed_bunks, "composition", "warning", "beds packed side by side - TreePlace v0.2 room review", "next bed"),
    ("SThearth", hearth_crowded, "composition", "warning", "cauldron against the hearth - TreePlace v0.2 room review", "crowds"),
    ("STrugtb", table_half_on_rug, "composition", "warning", "table half on a rug - TreePlace v0.2 room review", "half on"),
    ("STddoor", double_door_inside, "doors", "warning", "double door between two rooms of a house - TreePlace v0.2 room review",
     "between two rooms"),
    ("STsparse", sparse_room, "composition", "warning", "a room sparser than Westwood's median - TreePlace v0.2 room review",
     "sparse"),
    ("STdkind", mixed_doors, "doors", "warning", "three kinds of door in one building - TreePlace v0.2 room review",
     "kinds of door"),
    ("STfront", shelf_on_front_wall, "composition", "warning", "bookcase against the SE wall - TreePlace v0.3 room review",
     "SE wall"),
    ("STscatr", scattered_shelves, "composition", "warning", "shelves scattered along a wall - TreePlace v0.3 room review",
     "end to end"),
    ("STfloat", floating_chest, "composition", "warning", "chest standing off its wall - TreePlace v0.3 room review",
     "units off the"),
    ("STspur", path_to_wall, "composition", "warning", "a path ending at a house wall with no door - town lab",
     "paths lead to doors"),
    ("STbarrl", barrels_overlap, "exterior", "warning", "barrels overlapping outdoors - Starwell playtest", "overlap"),
    ("STcrop", crop_on_fence, "exterior", "warning", "crops on a fence line - Ambermere playtest", "fence"),
    ("STcandl", candle_outdoors, "exterior", "warning", "a candle as an outdoor light - Starwell playtest", "pick it up"),
    ("STswarm", camp_swarm, "exterior", "warning", "five men round one spot - Starwell playtest", "swarm"),
    ("STthrsh", ground_in_room, "floors", "warning", "the meadow's grass on a room's floor by the door - SW-4", "a room's"),
    ("STwallb", blend_across_wall, "floors", "error", "grass blended onto a house's boards across its wall - TW-12",
     "across a wall"),
    ("STfncbl", blend_beside_fence, "floors", "error", "fences blend, a house's wall does not - FN-1",
     "across a wall"),
    ("STwayin", piece_in_way, "composition", "warning", "a table straight in from the door - GW-7", "way in"),
    ("STstatw", statue_at_wall, "composition", "warning", "a statue facing the wall a unit away - GW-7", "a statue faces"),
    ("STshare", shared_stop, "routes", "error", "two walkers' stops 14 px apart - GW-6", "one spot for two"),
    ("STface", facing_wall, "routes", "error", "a stop facing the house wall beside it - SW-2", "face open ground"),
    ("STtour", short_tour, "routes", "warning", "a tour of two stops of 8 s - TW-9", "townsperson's tour"),
    ("STdockb", dock_on_bank, "exterior", "warning", "a dock lying on the bank, not over the water - AM-2", "reach out"),
    ("STmmap", minimap_on_corners, "minimap", "error", "the minimap polygon's corners on the map's corners - TW-5",
     "starts outside"),
    ("STshow", showpieces, "identity", "warning", "three telescopes in one room - SWR-1", "showpiece"),
    ("STrepw", statues_along_wall, "identity", "warning", "four statues lining one wall - SW-6", "repeated along"),
    ("STsupw", barrels_along_wall, "identity", "warning", "crates from corner to corner in a bedroom - AMR-4",
     "supplies line"),
    ("STmono", one_kind_fills, "identity", "warning", "a room filled with benches - TW-8", "one kind fills"),
    ("STkeep", keeper_off_counter, "identity", "warning", "a shopkeeper in the middle of his shop - SWR-2", "counter"),
    ("STcivS", civic_room, "civic", "warning", "a declared living room with a bare S corner - Q1A-1", "S corner"),
    ("STcivW", civic_room, "civic", "warning", "a declared living room with a bare NW wall - Q1A-3", "stand bare"),
    ("STcivK", civic_room, "civic", "warning", "a declared living room of three kinds of piece - Q1A-2", "kinds of piece"),
    ("STthron", throne_from_door, "identity", "warning", "a throne with its back to the doors - GW-7", "throne"),
    ("STseat", stump_by_fire, "exterior", "warning", "a stump as a seat by a camp fire - SW-3", "never stumps"),
    ("STroll", lone_bedroll, "exterior", "warning", "a bedroll alone in the open - GW-4", "alone in the open"),
    ("STheap", heap_of_crates, "exterior", "warning", "a heap of crates and barrels with no purpose - GW-2", "heaped"),
    ("STgrave", empty_graveyard, "exterior", "warning", "a graveyard of one headstone - SW-9", "graveyard"),
    ("STwellh", plain_well, "exterior", "warning", "a Well that does not heal - Q1X-4", "not the healing well"),
    ("STwellf", bare_well, "exterior", "warning", "a well alone on the grass - Q1X-5", "not a feature"),
    ("STgrows", scattered_graves, "exterior", "warning", "six headstones at random - Q1X-8", "in rows"),
    ("STgvar", graves_alone, "exterior", "warning", "graves in rows and nothing else - Q1X-11", "has graves and"),
    ("STgatep", path_off_gate, "exterior", "warning", "a cobbled path a square off its gate - Q1X-10", "off the gate"),
    ("STcropg", crops_on_grass, "exterior", "warning", "crops growing in grass - Q1X-13", "grow in grass"),
    ("STcropr", crops_scattered, "exterior", "warning", "crops strewn, not in rows - Q1X-14", "straight rows"),
    ("STsetv", shrine_of_one_kind, "exterior", "warning", "a shrine of obelisks alone - Q1X-1", "a set piece is never"),
    ("STsetm", lopsided_well, "exterior", "warning", "a well yard with everything on one side - Q1X-2", "mirrored about"),
    ("STgatei", path_off_gate_i, "exterior", "warning", "a path half a square off a gate in an i side - Q2X-2",
     "off the gate"),
    ("STsetE", empty_yard, "exterior", "error", "a declared well yard with nothing in it - Q2T-7", "none of its own"),
    ("STyspil", paving_past_fence, "exterior", "warning", "a fenced well's paving a row past its fence - Q2T-6",
     "past its fence"),
    ("STyblnd", blended_pad, "exterior", "warning", "a well's cobbles blended into the grass - Q2T-6", "blends into"),
    ("STcrate", crate_by_apples, "exterior", "warning", "a large crate 29 px from an apple crate - Q1K-1", "large crate"),
    ("STcampb", bare_camp, "exterior", "warning", "a camp of a fire and two bedrolls - Q1K-3", "lived in"),
    ("STbedsb", beds_in_block, "exterior", "warning", "three urchin beds side by side - Q1K-4", "one block"),
    ("STrowf", racks_floating, "exterior", "warning", "a row of racks in the middle of a meadow - Q1K-13", "away from every wall"),
    ("STjailc", bare_jail, "exterior", "warning", "a jail of two bare cells - Q1K-10", "cells have no cot"),
    ("STmpobj", mp_object, "setup", "warning", "an arena's crown in a single-player map", "Multiplayer-only"),
    ("STcram", crammed_room, "rooms", "warning", "a declared room furnished past its cover - DysVale playtest", "crammed"),
    ("STtabl", tavern_tables, "identity", "warning", "a tavern of 30 tables - TW-8", "free-standing tables"),
    ("STscbed", scattered_beds, "composition", "warning", "three beds of one kind at random spots - TreePlace v0.1",
     "beds scattered"),
    ("STstray", stray_in_bedroom, "rooms", "warning", "a powder barrel in a declared bedroom - TP1-4", "not belong"),
    ("STpers", person_in_the_way, "routes", "warning", "a person standing on a townsperson's way - AMR-7", "stands there"),
    ("STcauld", two_cauldrons, "pieces", "warning", "two cauldrons in one room - HB-1", "cauldrons"),
    ("STchst4", four_chests, "pieces", "warning", "four chests in a bedroom - HB-3", "chests by the room type"),
    ("STsets", bedroom_table_sets, "pieces", "warning", "three table sets in a bedroom - HB-3", "table-and-chair"),
    ("SThclr", chest_by_hearth, "pieces", "warning", "a chest beside the hearth - HB-2", "keeps off the fires"),
    ("STlogw", shelves_wall, "pieces", "warning", "five log shelves end to end along a wall - HB-5", "short runs"),
    ("SThung", trophy_over_statue, "pieces", "warning", "a trophy hung above a statue - HB-2", "bare wall"),
    ("STcand", candelabras, "pieces", "warning", "nine candelabras in a small house - HB-4", "candelabras by"),
    ("STshw2", two_bellows, "pieces", "warning", "two bellows in one room - HB-1", "showpiece stands once"),
    ("STgLite", g_free_lights, "composition", "warning", "three candelabras loose on a bedroom floor - judges 10-06", "[grammar light"),
    ("STgTabl", g_floating_tables, "composition", "warning", "two table sets floating mid-floor - judges 10-06", "[grammar table]"),
    ("STgChr", g_lone_chairs, "composition", "warning", "three chairs drawn up to nothing - judges 10-06", "[grammar chair]"),
    ("STgLone", g_lone_stock, "composition", "warning", "three barrels alone in the open - judges 10-06", "[grammar lone]"),
    ("STgEven", g_even_rows, "composition", "warning", "crates and barrels at equal gaps along walls - judges 10-06", "[grammar even]"),
    ("STgPlnt", g_plant, "composition", "warning", "a plant in a bedroom - judges 10-06", "[grammar plant]"),
    ("STgTwin", g_twins, "composition", "warning", "three stamped barrel pairs - judges 10-06", "[grammar twin]"),
    ("STgRing", g_ring, "composition", "warning", "four chairs at two tables' quarter points - judges 10-06", "[grammar ring]"),
    ("STgCorn", g_corners, "composition", "warning", "one barrel to a corner - judges 10-06", "[grammar corners]"),
    ("STgStep", g_stepped, "composition", "warning", "barrels in an evenly stepped row - judges 10-06", "[grammar stepped]"),
    ("STgMix", g_mixed_beds, "composition", "warning", "cots and wooden beds in one room - judges 10-06", "[grammar mixed]"),
    ("STsAxis", altar_off_axis, "sacred", "warning", "a chapel's altar off its main door's line - Q1C-2", "main door's line"),
    ("STsSym", pews_one_side, "sacred", "warning", "a chapel's pews on one side of the aisle only - Q1C-1", "no twin"),
    ("STsCarp", carpet_one_side, "sacred", "warning", "a chapel's carpet off its middle line - Q1C-3", "carpet squares"),
    ("STsAltr", same_altars, "sacred", "warning", "three chapels ending in the same altar - Q1C-4", "same altar"),
    ("STsShrA", same_shrine_altars, "sacred", "warning", "three shrines round the same stone altar - Q3R-2",
     "shrine rooms end in the same altar"),
    ("STcAxis", runner_unit_off, "sacred", "warning", "a runner a unit off the door's line as drawn - Q2T-2",
     "the carpet's middle stands"),
    ("STcOn", ring_off_carpet, "sacred", "warning", "a ring of obelisks a unit off its carpet as drawn - Q2T-2",
     "the middle of what stands on it"),
    ("STsFull", bare_chapel, "sacred", "warning", "a chapel of an altar and two pews - Q1C-19", "kinds of piece"),
    ("STsDead", crypt_without_dead, "sacred", "warning", "a crypt of one coffin - Q1C-14", "the dead lie here"),
    ("STsCrat", crypt_crates, "sacred", "warning", "a crypt with a pair of crates - Q3R-1", "holds no crates"),
    ("STdLotd", wooden_door_in_lotd, "doors", "warning", "a plain door in the Land of the Dead's walls - Q1C-18",
     "Land of the Dead"),
    ("STq1Nst", q1_nightstand, "rooms", "warning", "a bed with a nightstand on one side - Q1R-3", "one side only"),
    ("STq1Chc", q1_chest_corner, "rooms", "warning", "a bedroom chest in a corner - Q1R-4", "into a corner"),
    ("STq1Sth", q1_south, "rooms", "warning", "a bedroom's bare S corner - Q1R-6", "S corner"),
    ("STq1Obl", q1_obelisks, "rooms", "warning", "three mana obelisks in an ogre den - Q1R-10", "symmetric pair"),
    ("STq1Cel", q1_cell, "rooms", "warning", "one cot in a big cell - Q1R-11", "one cot"),
    ("STq1Clr", q1_cellar_kinds, "rooms", "warning", "a cellar of barrels only - Q1R-13", "kinds"),
    ("STq1Csk", q1_cask, "rooms", "warning", "a barrel against a great cask - Q1R-13", "crowds a great cask"),
    ("STq1Grd", q1_garden_floor, "rooms", "warning", "a conservatory plant on floorboards - Q1R-14", "grows out of"),
    ("STq1Wel", q1_wells, "rooms", "warning", "two wells in a conservatory - Q1R-14", "2 wells"),
    ("STq1Ctr", q1_counter, "rooms", "warning", "an armoury with no counter - Q1R-1", "no counter"),
    ("STq1Rck", q1_racks, "rooms", "warning", "a barracks with no racks - Q1R-9", "no racks"),
    ("STq2Ctr", q2_off_centre, "qa2", "warning", "a gallery's statue pairs a unit off the room's middle - Q2T-1",
     "off the room's middle line"),
    ("STq2Fac", q2_benches_away, "qa2", "warning", "a hall's benches turning their backs to the aisle - Q2T-3",
     "back to the aisle"),
    ("STq2Way", q2_shop_blocked, "qa2", "warning", "a crate in the walk from a shop's door to its counter - Q2C-7",
     "in the way from the door to the counter"),
    ("STbarOp", bar_in_open, "composition", "warning", "a bar run ending in the open - RM-TAVERN-04", "stops in the open"),
    ("STq1Hth", q1_hearth, "rooms", "warning", "a hearth on the bare boards - Q1R-19", "no hearth of brick"),
    ("STq1Emp", q1_empty, "rooms", "warning", "a big cellar of three barrels - Q1R-23", "too empty"),
    ("STq1Bed", q1_bare_bedroom, "rooms", "warning", "a bare bedroom with a twin rug - Q1R-23", "one rug repeated"),
    ("STq2Gap", q2_crates_touch, "rooms", "warning", "two crates touching in a cellar - Q2T-4", "units apart (separate"),
    ("STq2Big", q2_big_close, "rooms", "warning", "an obelisk by a statue - Q2T-4", "a big piece keeps"),
    ("STq2Rug", q2_rug_fire, "rooms", "warning", "a rug against a fireplace - Q2T-4", "clear of a fire"),
    ("STq2Wal", q2_chest_out, "rooms", "warning", "a chest standing out from its wall - Q2T-5", "units off the"),
    ("STq2Mid", q2_bench_mid, "rooms", "warning", "a bench alone mid-floor - Q2T-5", "alone in the middle"),
    ("STq2Lin", q2_chests_unlined, "rooms", "warning", "two chests at two depths on one wall - Q2T-5", "not lined up"),
    ("STq2Chs", q2_chests_scattered, "rooms", "warning", "a barracks' chests off the beds' feet - Q2F-2", "at a bed's foot"),
    ("STq3Fac", q3_chests_sideways, "rooms", "warning", "a barracks' foot chests side-on to their beds - Q3R-6",
     "not away from the bed"),
    ("STq3Far", q3_chests_far, "rooms", "warning", "a barracks' foot chests 0.6 units off the beds - Q3R-7",
     "units off the foot of"),
    ("STq3Gap", q3_pair_gap_bare, "rooms", "warning", "two pairs of beds with no chest between them - Q3R-8",
     "holds no chest"),
    ("STq2Ogr", q2_ogre_pen_in_house, "rooms", "warning", "an ogre pen in a town house - Q2F-6", "a town house's"),
    ("STtpLnk", tp_unlinked, "transport", "error", "a lift platform that names no pit - TR-1", "moves nobody"),
    ("STtpWal", tp_in_wall, "transport", "error", "a pentagram landing the player in a wall - TR-1", "in a wall"),
    ("STtpStr", tp_stranded, "transport", "error", "a one-way portal into a sealed cellar - TR-1", "strands"),
    ("STtpBnc", tp_bounce, "transport", "error", "a portal landing the player on another pad - TR-1", "sends him on"),
    ("STtpSrv", tp_serves, "transport", "error", "a lift whose far end cannot reach what it serves - TR-1",
     "cannot be walked to"),
    ("STtpNWl", tp_near_wall, "transport", "warning", "a pentagram landing the player against a wall - TR-1", "from a wall"),
    ("STtpPkt", tp_pocket, "transport", "error", "a portal into a closet of a few cells - TR-1", "pocket"),
    ("STtpMis", tp_missing, "transport", "error", "a declared portal whose pad is missing from the map - TR-1", "missing"),
    ("STtpUnr", tp_unreached, "transport", "warning", "a portal that starts in a sealed room - TR-1", "cannot get"),
    ("STsignL", plank_sign, "signs", "error", "a tall plank sign - QA round 1, nox1/nox10", "plank sign"),
    ("STsignT", sign_two_lines, "signs", "error", "a sign of two lines, which the game runs together - nox1", "line break"),
    ("STwell", dry_well, "wells", "error", "a well that does not heal - nox13", "does not heal"),
    ("STfish", still_fish, "fish", "error", "a fish with no loop to swim - nox4", "no linked waypoint"),
    ("STdoorp", villager_in_door, "people", "error", "a villager standing in a doorway - nox10", "in a doorway"),
    ("STcrowd", villagers_at_door, "people", "warning", "two villagers waiting at one door - nox10", "at one door"),
    ("STfacew", villager_faces_wall, "people", "warning", "a villager facing the house wall beside him - nox10",
     "faces open ground"),
    ("STiname", nameless_item, "items", "error", "an item with no name - nox19", "has no name"),
    ("STiware", useless_ware, "items", "error", "a shop selling an item with no price or use - nox12", "has no price"),
    ("STiprce", dear_ware, "items", "warning", "a battle axe sold in act 1 - nox12", "the dearest"),
    ("STwade", wade, "water", "error", "a pond without its shore walls: the player walks on it - Q1W-12", "walk on the water"),
    ("STfingr", fingers, "water", "warning", "tiles of bank poking into a pond - Q1W-11", "ragged bank"),
    ("STbrrd", road_off_bridge, "water", "warning", "a one-row road beside a plank deck's rows - Q1W-1", "narrower than"),
    ("STbrpav", cobbles_under_bridge, "water", "warning", "a rope bridge's span paved to the water - Q2T-6",
     "runs under the bridge"),
    ("STbrgap", road_short_of_bridge, "water", "warning", "a paved road a tile short of a rope bridge's end - Q3X-1",
     "short of the RopeBridge2 bridge's south-west end"),
    ("STbrovr", road_under_bridge_end, "water", "warning", "a paved road a tile on under a rope bridge's end - Q3X-1",
     "under the RopeBridge1 bridge's north-west end"),
    ("STbreven", bridge_uneven, "water", "warning", "a deck reaching three tiles more onto one bank - Q1W-2",
     "farther onto one bank"),
    ("STdklong", dock_too_long, "water", "warning", "a long dock in a small pond - Q1W-6", "a third of the way"),
    ("STdkwall", dock_on_wall, "water", "warning", "a dock out of the meadow's wall - Q1W-9", "starts against a wall"),
    ("STdk2", two_docks, "water", "warning", "two docks in one small pond - Q1W-5", "docks on one pond"),
    ("STdkside", dock_by_bank, "water", "warning", "a dock along a stream a tile off its bank - Q1W-7",
     "close along one bank"),
    ("STdoorst", doorstep, "floors", "warning", "the house's boards out on its doorstep - Q1W-13", "doorstep"),
    ("STpatch", hard_patch, "floors", "warning", "a patch of dirt in the meadow with hard edges - Q1W-14", "hard edges"),
    ("STq1axs", q1_shrine_off_axis, "composition", "warning", "a shrine's obelisks off the door's axis - QA1 Q1B",
     "no mirrored partner"),
    ("STq1sto", q1_store_of_barrels, "composition", "warning", "a storeroom of barrels only - QA1 Q1B", "its stock is"),
    ("STq1frg", q1_forge_on_boards, "composition", "warning", "a forge on the bare floor - QA1 Q1B (nox17)",
     "bare floor"),
    ("STq1scr", q1_bare_s_corner, "composition", "warning", "a guardroom's bare S corner - QA1 Q1B", "S corner is bare"),
    ("STq2sig", q2_winch_crates, "composition", "warning", "a winch room of 30 crates and barrels - Q2T-8 Q2V-4",
     "past its cap of"),
    ("STq3mid", q3_smithy_mid_stock, "composition", "warning", "18 barrels out on a smithy's floor - Q3R-9",
     "out on the floor"),
    ("STq2kpr", q2_keeper_space, "composition", "warning", "a barrel behind a smithy's counter - Q2V-3",
     "where the keeper stands"),
    ("STq3Blnd", q3_carpet_blended, "qa3", "warning", "a tavern's carpet blended into its boards - Q3C-1",
     "blend into the floor"),
    ("STq3Brd", q3_patch_unbordered, "qa3", "warning", "a great hall's brick band with hard edges - Q3C-4",
     "with no border"),
    ("STq3Bar", q3_bar_opening, "qa3", "warning", "a bar's brick unbordered at the counter's opening - Q3C-2",
     "at the bar's opening"),
    ("STq3Rep", q3_same_throne_rooms, "qa3", "warning", "three throne rooms of the same pieces - Q3C-6",
     "s repeat one another"),
    ("STq3Rnk", q3_hall_ranks, "qa3", "warning", "a hall of four ranks of columns and statues - Q3C-7",
     "stand in 4 ranks"),
]


def main(argv=()):
    import json
    base = V.baseline()
    ok = True
    planted, other = {}, []
    only = set(argv)
    print(f"{'map':9s} {'planted defect':66s} result")
    for name, defect, check, sev, desc, *contains in CASES:
        if only and name not in only and name != "STclean": continue
        m = clean(name)
        if defect: defect(m)
        out_dir = os.path.join(OUT, name)
        os.makedirs(out_dir, exist_ok=True)
        side = os.path.join(out_dir, name + ".rooms.json")
        if getattr(m, "declare_rooms", None):          # the rooms as a generator would declare them
            json.dump(m.declare_rooms, open(side, "w"))
        elif os.path.exists(side):
            os.remove(side)
        m.build(out_dir, check=False)
        data = md.load(os.path.join(out_dir, name + ".map"))
        findings, _ = C.run_all(data, base)
        errors = [f for f in findings if f["severity"] == "error"]
        other += [f"{name}: {f['msg'][:80]}" for f in findings if f.get("rule", "").endswith(".other")]
        if defect is None:
            passed = not errors
            warns = sorted({f["rule"] for f in findings if f["severity"] == "warning"})
            got = ("no errors" if passed else "; ".join(f"{f['check']}: {f['msg'][:70]}" for f in errors[:4]))
            got += f"; warnings: {', '.join(warns)}" if warns else ""
        else:
            hits = [f for f in findings if f["check"] == check and f["severity"] == sev and
                    (not contains or contains[0] in f["msg"])]
            passed = bool(hits)
            if hits: planted.setdefault(hits[0]["rule"], name)
            got = (f"caught [{hits[0]['rule']}]: {hits[0]['msg'][:90]}" if hits else
                   f"MISSED; got: {[(f['check'], f['severity']) for f in findings if f['severity'] != 'info']}")
        ok &= passed
        print(f"{name:9s} {desc:66s} {'PASS' if passed else 'FAIL'}\n          {got}")
    if not only:
        json.dump(planted, open(os.path.join(OUT, "rules.json"), "w"), indent=1)
        print(f"\nRules with a planted case: {len(planted)} (written to validate/out/selftest/rules.json)")
    if other:
        ok = False
        print("\nFindings no rule in checks.RULES names (give each message a rule):\n  " + "\n  ".join(other[:20]))
    print("\nAll checks behave as expected." if ok else "\nSOME CHECKS DID NOT BEHAVE AS EXPECTED.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
