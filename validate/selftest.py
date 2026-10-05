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
    ww.dock(pond, "down", length=2)
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


def throne_from_door(m):
    m.obj("DunMirThroneBase", 219.5, -2)                      # by the SE wall, its back to the room's doors (GW-7)


def stump_by_fire(m):
    m.obj("CampFire", 186, -30); m.obj("Stump1", 189.5, -30)   # a stump as a seat by a camp fire (SW-3)


def lone_bedroll(m):
    m.obj("CampFire", 236, 26); m.obj("Cot2", 230, 32)         # a bedroll strewn in a camp, no tent, no row (GW-4)


def heap_of_crates(m):
    for k, t in enumerate(("Crate1", "Crate1", "Barrel", "Crate1", "Barrel", "Barrel")):   # a purposeless heap (GW-2)
        m.obj(t, 235 + 2.4 * (k % 3), -32 + 2.4 * (k // 3))


def empty_graveyard(m):
    _declare(m, "bedroom", [dict(number=2, building="", kind="graveyard", purpose="", tiles=0, box=[0, 0, 0, 0],
                                 yard=True, floor=[list(t) for t in rect_tiles(232, 250, 20, 34)])])
    m.obj("Tombstone1", 240, 26)                               # one headstone in a graveyard (SW-9)


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
    ("STthron", throne_from_door, "identity", "warning", "a throne with its back to the doors - GW-7", "throne"),
    ("STseat", stump_by_fire, "exterior", "warning", "a stump as a seat by a camp fire - SW-3", "never stumps"),
    ("STroll", lone_bedroll, "exterior", "warning", "a bedroll alone in the open - GW-4", "alone in the open"),
    ("STheap", heap_of_crates, "exterior", "warning", "a heap of crates and barrels with no purpose - GW-2", "heaped"),
    ("STgrave", empty_graveyard, "exterior", "warning", "a graveyard of one headstone - SW-9", "graveyard"),
    ("STmpobj", mp_object, "setup", "warning", "an arena's crown in a single-player map", "Multiplayer-only"),
    ("STcram", crammed_room, "rooms", "warning", "a declared room furnished past its cover - DysVale playtest", "crammed"),
    ("STtabl", tavern_tables, "identity", "warning", "a tavern of 30 tables - TW-8", "free-standing tables"),
    ("STscbed", scattered_beds, "composition", "warning", "three beds of one kind at random spots - TreePlace v0.1",
     "beds scattered"),
    ("STstray", stray_in_bedroom, "rooms", "warning", "a powder barrel in a declared bedroom - TP1-4", "not belong"),
    ("STpers", person_in_the_way, "routes", "warning", "a person standing on a townsperson's way - AMR-7", "stands there"),
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
