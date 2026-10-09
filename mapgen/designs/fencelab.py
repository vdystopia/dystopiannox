"""Fence lab: iron fences in their common situations, built under either fence policy (FN-1) so the two can be compared
in the game.

    py mapgen/designs/fencelab.py cut      # FenceCut: no blending at a fence (the default policy, TW-12)
    py mapgen/designs/fencelab.py blend    # FenceBlnd: floors blend across iron fences as Westwood's do

A walled meadow of plain grass (GrassNorm) holding, laid as the kit lays a yard's fence (kit/yards.py: wall points
round a plot of squares; the gate a two-cell opening in the middle of a side):
- pen A: rough cobble (RoughCobble) inside the grass, its gate (Gate) in its SE side (a / line);
- pen B: dark dirt (DirtDark2) inside the grass, its gate in its SW side (a \\ line);
- pen C: light stone (StoneLight) inside a patch of dark dirt (dirt | stone);
- an L of fence over the same grass on both sides, a / run and a \\ run joined by a corner.
Each pen has both diagonals, all four corners and the floor change under its fence. Under the cut policy a pen's own
floor stops a tile inside its \\ sides (a \\ fence runs through the middle of its tiles, so a cut cannot lie on its
line: PROCESS.md "Iron fences: cut or blend"); under the blend policy it runs to the fence and blends across it.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO
from kit.layout import square_tile, point_cell, square_px, OUTDOOR_BLENDS

POLICY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("cut", "blend") else "cut"
NAME = {"cut": "FenceCut", "blend": "FenceBlnd"}[POLICY]
m = Spec(NAME, summary=f"Iron fences ({POLICY})", description="Iron fences over grass, dirt, cobble and stone: straight "
         "runs both ways, corners, gates.", author="generated", version="0.1", date="Thursday, October 8 2026",
         type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [230, 230, 220]          # bright, so the floors under the fences read in the frames
m.fence_policy = POLICY

# ---- the meadow -----------------------------------------------------------------------------------------------------
I0, I1, J0, J1 = 104, 152, -22, 22                 # squares; the room's walls on their outline
m.room(2 * I0, 2 * I1, 2 * J0, 2 * J1, wall="DecidiousWallGreen", floor="GrassNorm")
for mat, prio, edge in OUTDOOR_BLENDS: m.blending(mat, prio, edge)
m.blending("StoneLight", 6, "BrickEdgeBrown")       # Westwood: StoneLight over DirtDark2 with BrickEdgeBrown


def fence_points(gi, gj, w, h):
    """Wall points round a plot of squares gi..gi+w-1 x gj..gj+h-1, by side (kit/yards.py _fence_points)."""
    return {"i0": [(gi, q) for q in range(gj - 1, gj + h)], "i1": [(gi + w, q) for q in range(gj - 1, gj + h)],
            "j0": [(p, gj - 1) for p in range(gi, gi + w + 1)], "j1": [(p, gj + h - 1) for p in range(gi, gi + w + 1)]}


def pen(gi, gj, w, h, floor, gate=None):
    for a in range(w):
        for b in range(h): m.floor[square_tile(gi + a, gj + b)] = floor
    sides = fence_points(gi, gj, w, h)
    for pts in sides.values():
        for p in pts: m.wall(*point_cell(*p), "IronFence")
    if gate:
        pts = sides[gate]; k = len(pts) // 2
        a, b = point_cell(*pts[k - 1]), point_cell(*pts[k])
        m.door("Gate", a, "\\" if (b[0] - a[0], b[1] - a[1]) == (1, 1) else "/")


PENS = {"A": (112, -12, 7, 6, "RoughCobble", "i1"), "B": (112, 6, 7, 6, "DirtDark2", "j0"),
        "C": (132, -12, 7, 6, "StoneLight", None)}
gi, gj, w, h = PENS["C"][:4]
for a in range(-3, w + 3):                          # pen C stands in a patch of dark dirt
    for b in range(-3, h + 3): m.floor[square_tile(gi + a, gj + b)] = "DirtDark2"
for k, rec in PENS.items(): pen(*rec)

# the L over grass: a / run (fixed p) and a \ run (fixed q) meeting in a corner
LP, LQ = 132, 8
for q in range(LQ, LQ + 10): m.wall(*point_cell(LP, q), "IronFence")
for p in range(LP, LP + 10): m.wall(*point_cell(p, LQ), "IronFence")

m.obj_px("PlayerStart", *square_px(124, 0))

# where the player stands for the game's frames (world px; the camera centres on him): below each pen on screen, and
# left of the L's corner
SPOTS = {"penA": (2438, 3130), "penB": (2852, 2716), "penC": (2898, 3530), "same": (3150, 3000)}

QA_ACCEPT = [
    ("density", r"Few |Many ", "a test map: fences only, nothing else"),
    ("exterior_holes", r".", "a test map: the meadow is bare so each fence stands out"),
]

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "fencelab_" + POLICY)
    print("\n".join(l for l in m.build(os.path.abspath(out)) if not l.startswith("XFER")))
