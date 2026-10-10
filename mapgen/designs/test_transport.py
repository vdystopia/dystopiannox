"""Test map for mapgen/kit/transport.py (skills/nox-transporters/SKILL.md): every kind of transporter, each to a part
of the map that cannot be walked to.

A walled meadow (the start) with:
- a cave lift down to a cellar (CaveElevator on its base; the pit in a cave cellar with a chest): two-way by nature;
- a pentagram on the lake shore to an island in the lake (two-way: a pentagram on the island leads back; the island's
  chest is what it serves);
- a stone keep whose stairs up (GalavaStairsUp1) lead to the upper floor, a castle room elsewhere on the map with the
  stairs down (GalavaStairsDown) back;
- a passage between two torches by the meadow's wall: step on it, the screen fades, and you wake in a crypt (two-way:
  the crypt has its own spot back).
Each far place holds a chest. Built into mapgen/out/test_transport/; installed as TestTrans for the user to try.
"""
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, CELL, px, uv_to_xy
from kit.water import Waterworks, TILE
from kit.transport import Transporters

NAME = "TestTrans"
rng = random.Random(7)
m = Spec(NAME, summary="Transporters test", description="A lift, a portal, stairs and a passage, each to a place "
         "that cannot be walked to.", author="generated", version="0.1", date="Thursday, October 8 2026",
         type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [150, 150, 140]

# ---- the meadow (start), its keep and the lake -------------------------------------------------------------------
U0, U1, V0, V1 = 180, 300, -60, 60
m.room(U0, U1, V0, V1, wall="DecidiousWallGreen", floor="GrassNorm")
KEEP = (200, 224, -50, -26)
m.room(*KEEP, wall="GalavaTownWall", floor="GalavaBrick")
m.door("ArchedDoor", (81, 119), "/")               # the keep's NW wall (u = 200), facing the meadow
m.blending("GrassNorm", 0)

LAKE, LAKE_R, ISLE_R = (262, 30), 9.0, 3.6         # uv centre; radii in tiles
ww = Waterworks(m, rng)
pond = ww.pond(LAKE, radius=LAKE_R, roughness=0.15)
lx, ly = uv_to_xy(*LAKE)
for (x, y), mat in list(m.floor.items()):          # the island, and shallow water round it
    d = math.hypot(x + 1 - lx, y + 1 - ly)
    if d <= ISLE_R * TILE: m.floor[(x, y)] = "GrassNorm"
    elif d <= (ISLE_R + 2.2) * TILE and mat == "WaterDeep":
        m.floor[(x, y)] = "WaterShallow"
ww.finish(dress=False)

# ---- the far places, none joined to the meadow ---------------------------------------------------------------------
CELLAR = (330, 356, -70, -44)                      # below the meadow: a cave cellar
m.room(*CELLAR, wall="CaveWall", floor="DirtDark2")
UPPER = (330, 362, 30, 62)                         # the keep's upper floor
m.room(*UPPER, wall="GalavaTownWall", floor="GalavaBrick")
CRYPT = (120, 146, -20, 6)                         # behind the meadow's wall
m.room(*CRYPT, wall="DungeonStone", floor="GreenBrick")

# ---- what each far place holds -------------------------------------------------------------------------------------
cellar_chest = px(CELLAR[0] + 6, CELLAR[3] - 6)
isle_chest = px(LAKE[0] + 3, LAKE[1] + 4)
upper_chest = px(UPPER[1] - 6, UPPER[3] - 6)
crypt_box = px(CRYPT[1] - 6, CRYPT[2] + 6)
m.obj_px("Chest3", *cellar_chest, items=["RedPotion", ("Gold", {"Amount": 25})])
m.obj_px("Chest4", *isle_chest, items=["CurePoisonPotion"])
m.obj_px("DunMirChest3", *upper_chest, items=["BluePotion"])
m.obj_px("CryptChest2", *crypt_box, items=[("Gold", {"Amount": 40})])
for (u0, u1, v0, v1) in (CELLAR, UPPER, CRYPT):
    m.obj_px("Candleabra1", *px(u0 + 3, v1 - 3))

# ---- the transporters ---------------------------------------------------------------------------------------------
tp = Transporters(m)
tp.add("lift", px(196, 40), px((CELLAR[0] + CELLAR[1]) / 2, (CELLAR[2] + CELLAR[3]) / 2), "CellarLift",
       style="cave", serves=[cellar_chest])
tp.add("portal", px(232, 30), px(*LAKE), "IslePortal", serves=[isle_chest])
tp.add("stairs", px(UPPER[0] + 5, UPPER[2] + 6), px(212, KEEP[3] - 2), "KeepStair", style="castle",
       serves=[upper_chest])
tp.add("passage", px(186, -10), px(CRYPT[0] + 6, CRYPT[2] + 7), "CryptWay", serves=[crypt_box])
for dv in (-4, 4):                                 # torches flank the passage's spot
    m.obj_px("TorchPole", *px(184, -10 + dv))

m.obj("PlayerStart", 190, 0)

QA_ACCEPT = [
    ("density", r"Few |Many ", "a test map: one of each transporter, nothing else"),
    ("rooms", r"nearly bare|is small|is sparse", "a test map: each far room holds only its chest and a light"),
    ("composition", r"is sparse|furniture fills only", "a test map: each far room holds only its chest and a light"),
    ("exterior_holes", r".", "a test map: the meadow is bare so each transporter stands out"),
]

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "test_transport")
    print("\n".join(l for l in m.build(os.path.abspath(out)) if not l.startswith("XFER")))
