"""Furnishing test: a grid of plain rooms, each furnished by kit.furnish with a different room
type and seed. Builds mapgen/out/test_rooms/RoomTest.map, renders it with the editor, and prints
per-room statistics.

    py mapgen/designs/test_rooms.py [seed]
"""
import collections, os, random, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, uv_to_xy, rect_tiles, rect_wall_cells
from kit.model import Room, Door
from kit.furnish import furnish_room, _family_of

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "mapgen", "out", "test_rooms")
ROOMS = [  # kind, u span, v span, wall, floor
    ("bedroom", 12, 10, "Log", "OakWoodFloor"),
    ("living_room", 14, 12, "StuccoLightWood", "WoodLight2"),
    ("kitchen", 12, 12, "Log", "WoodSlatFloor"),
    ("dining_hall", 20, 16, "StuccoLightWood", "RedwoodFloor"),
    ("tavern", 24, 18, "StuccoLightWood", "WoodLight2"),
    ("shop", 18, 14, "StuccoLightWood", "OakWoodFloor"),
    ("library", 18, 14, "BrickPlain", "RugGreen"),
    ("study", 12, 12, "StuccoLightWood", "RugTanLightNorm"),
    ("smithy", 16, 14, "BrickPlain", "CobbleStone"),
    ("storeroom", 10, 10, "Log", "WoodSlatFloor"),
    ("barracks", 18, 12, "StuccoLightWood", "WoodGray2"),
    ("laboratory", 16, 14, "BrickPlain", "RugBlueNorm"),
]


def build(seed=1):
    rng = random.Random(seed)
    m = Spec("RoomTest", summary="Furnishing test", description="Generated rooms of every type", author="Claude",
             version="0", date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
    m.d["nxz"] = False
    m.d["ambient"] = [110, 105, 100]
    rooms = []
    u, v, row_h = 160, -60, 0
    for i, (kind, us, vs, wall, floor) in enumerate(ROOMS):
        if v + vs > 70:
            v, u = -60, u + row_h + 8
            row_h = 0
        u0, u1, v0, v1 = u, u + us, v, v + vs
        m.room(u0, u1, v0, v1, wall=wall, floor=floor)
        gap_u = (u0 + u1) // 2 // 2 * 2
        gap = tuple(int(c) for c in uv_to_xy(gap_u, v0))       # door in the front-left wall
        door_obj = m.door(None, gap, "\\")
        r = Room(id=f"r{i}", tiles=set(rect_tiles(u0, u1, v0, v1)), floor=floor, walls=rect_wall_cells(u0, u1, v0, v1),
                 doors=[Door(gap=gap, line="\\", type=door_obj["type"], connects=(f"r{i}", "outside"), px=(door_obj["x"], door_obj["y"]))])
        rooms.append((r, kind))
        v += vs + 8
        row_h = max(row_h, us)
    stats = []
    for i, (r, kind) in enumerate(rooms):
        objs = furnish_room(m, r, kind, random.Random(seed * 1000 + i))
        fams = collections.Counter(_family_of(o["type"]) or ("colorlight" if o["type"] == "ColorLight" else o["type"]) for o in objs)
        stats.append((kind, len(r.tiles), len(objs), dict(fams)))
    u_mid = sum(uu for (r, _) in rooms for (x, y) in r.tiles for uu in [x + y]) / sum(len(r.tiles) for r, _ in rooms)
    m.obj("PlayerStart", 166, -58)
    print("\n".join(l for l in m.build(OUT) if l.startswith(("OK", "ERROR"))))
    import json                                 # room boxes for review/rooms.py (grid cells)
    with open(os.path.join(OUT, "RoomTest.rooms.json"), "w") as f:
        json.dump([dict(kind=k, tiles=len(r.tiles), box=[min(x for x, _ in r.tiles) - 1, min(y for _, y in r.tiles) - 1,
                                                        max(x for x, _ in r.tiles) + 3, max(y for _, y in r.tiles) + 3])
                   for r, k in rooms], f)
    for s in stats:
        print(f"{s[0]:12} tiles={s[1]:4} objects={s[2]:3} per100={100 * s[2] / s[1]:5.1f}  {s[3]}")
    return os.path.join(OUT, "RoomTest.map")


if __name__ == "__main__":
    path = build(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    png = os.path.join(REPO, "corpus", "out", "scratch", "rooms", "RoomTest.png")
    os.makedirs(os.path.dirname(png), exist_ok=True)
    if os.path.exists(png): os.remove(png)
    subprocess.run([os.path.join(REPO, "MapEditor", "bin", "Release", "MapEditor.exe"), path, "--render-image", png, "5880"], timeout=600)
    print("render:", png if os.path.exists(png) else "FAILED")
