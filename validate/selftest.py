"""Proves the checker catches the defects we know about. Builds a small clean test map and one
variant per known defect (each planted on purpose, including every playtest finding so far), runs
the checks on each, and confirms: the clean map has no errors, and every variant raises the
expected finding.

    py validate/selftest.py          (builds into validate/out/selftest/, takes a few minutes)
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
    for i in range(5):
        for j in range(4):
            m.obj("Table1", 204 + 3.5 * i, -7 + 4 * j)


def doorway(m):
    m.obj_px("Barrel", DOOR_GAP[0] * CELL + 11.5, DOOR_GAP[1] * CELL + 11.5)


def rug_on_grass(m):
    for x, y in rect_tiles(186, 192, 20, 26): m.tile(x, y, "RugGreen")


def void_creature(m):
    m.obj_px("Wolf", 300, 300)


def sealed_room(m):
    m.room(240, 248, -32, -24, wall="StuccoLightWood", floor="WoodLight2")
    m.obj("Wolf", 244, -28)


def no_start(m):
    m.d["objects"] = [o for o in m.d["objects"] if o.get("type") != "PlayerStart"]


CASES = [  # (map name, defect, expected check, expected severity, description)
    ("STclean", None, None, None, "clean map: no errors"),
    ("STwall", black_wall, "wall_pieces", "error", "black wall (wall style with no artwork) - Mossford playtest"),
    ("SThole", hole, "boundary", "error", "hole in the outer wall"),
    ("STinvis", invisible_boundary, "boundary", "error", "outer wall replaced by invisible wall - Mossford playtest"),
    ("SThalf", lone_half_door, "doors", "error", "half of a double door alone in a 1-cell opening - DysVale playtest"),
    ("STjamb", jamb, "wall_shapes", "error", "corner beside a door shaped as a straight piece - DysVale playtest"),
    ("STdock", dock_misaligned, "kits", "error", "dock pieces off Westwood's steps - DysVale playtest"),
    ("STclutr", clutter, "rooms", "warning", "room crammed with furniture - DysVale playtest"),
    ("STdoorw", doorway, "doorways", "error", "barrel standing in a doorway"),
    ("STrug", rug_on_grass, "floors", "error", "rug laid straight onto grass"),
    ("STvoid", void_creature, "objects", "error", "creature standing in the void"),
    ("STseal", sealed_room, "reachability", "error", "creature in a room with no way in"),
    ("STnostrt", no_start, "setup", "error", "no player start"),
]


def main():
    base = V.baseline()
    ok = True
    print(f"{'map':9s} {'planted defect':66s} result")
    for name, defect, check, sev, desc in CASES:
        m = clean(name)
        if defect: defect(m)
        out_dir = os.path.join(OUT, name)
        m.build(out_dir, check=False)
        data = md.load(os.path.join(out_dir, name + ".map"))
        findings, _ = C.run_all(data, base)
        errors = [f for f in findings if f["severity"] == "error"]
        if defect is None:
            passed = not errors
            got = "no errors" if passed else "; ".join(f"{f['check']}: {f['msg'][:70]}" for f in errors[:4])
        else:
            hits = [f for f in findings if f["check"] == check and f["severity"] == sev]
            passed = bool(hits)
            got = f"caught ({check} {sev}): {hits[0]['msg'][:90]}" if hits else \
                f"MISSED; got: {[(f['check'], f['severity']) for f in findings if f['severity'] != 'info']}"
        ok &= passed
        print(f"{name:9s} {desc:66s} {'PASS' if passed else 'FAIL'}\n          {got}")
    print("\nAll checks behave as expected." if ok else "\nSOME CHECKS DID NOT BEHAVE AS EXPECTED.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
