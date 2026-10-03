"""Test map for mapgen/kit/water.py: a walled meadow with a winding stream (two plank bridges and a
ford), a pond with two docks, a wide inlet crossed by a rope bridge, and a lava flow with a lava
bridge. Built into mapgen/out/test_water/ for review (not installed into the game)."""
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, px
from kit.water import Waterworks

rng = random.Random(11)
m = Spec("TestWatr", summary="Water kit test", description="Streams, bridges, ford, docks, rope and lava bridges.",
         author="generated", version="0.1", date="Saturday, October 3 2026", type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [150, 150, 140]

U0, U1, V0, V1 = 180, 332, -64, 64
m.room(U0, U1, V0, V1, wall="DecidiousWallGreen", floor="GrassNorm")
for (x, y) in list(m.floor):                      # grass variety, as in Westwood meadows
    u, v = x + y + 2, x - y
    n = math.sin(u * 0.09 + 1.1) + math.sin(v * 0.11 + 0.4) + 0.5 * math.sin((u - v) * 0.05)
    if n > 1.0: m.floor[(x, y)] = "GrassSparse2"
    elif n < -1.2: m.floor[(x, y)] = "GrassDense"
m.blending("GrassSparse2", 2)                     # sparse grass spills onto normal grass (floors rules)
m.blending("GrassDense", 1)
m.blending("GrassNorm", 0)

ww = Waterworks(m, rng)
stream = ww.stream([(U0 + 2, -14), (215, -8), (250, -24), (285, -10), (U1 - 2, 6)], width=2.6, wiggle=2.5)
ww.plank_bridge(stream, t=0.32)
ww.plank_bridge(stream, t=0.66)
ww.ford(stream, t=0.86)
pond = ww.pond((222, 36), radius=10)
ww.dock(pond, "down", length=2)
ww.dock(pond, "up", length=2)
inlet = ww.stream([(292, 30), (312, 40), (U1 - 2, 44)], width=5.0, wiggle=1.0)
ww.rope_bridge((308, 26), (308, 52))
lava = ww.lava([(234, -50), (250, -42), (268, -48), (286, -40), (302, -48)], width=3.0)
ww.lava_bridge((268, -34), (268, -60))
ww.finish()

m.obj("PlayerStart", 200, 0)
m.polygon("TestWatr:Meadow", (150, 150, 140), [px(U0, V0), px(U0, V1), px(U1, V1), px(U1, V0)])

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "test_water")
    print("\n".join(l for l in m.build(os.path.abspath(out)) if not l.startswith("XFER")))
