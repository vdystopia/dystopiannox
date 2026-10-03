"""Demo of the original building generator: a field of generated buildings in several styles and
shapes. Builds mapgen/out/test_buildings/BldTest.map, prints per-building stats next to Westwood's
(rules/out/buildings.json), and checks structure (every room reachable, doors in wall gaps).

    py mapgen/designs/test_buildings.py [seed]
"""
import json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from nox import Spec, SOLO, rect_tiles
from kit.building import generate_building, styles

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 3
rng = random.Random(seed)
m = Spec("BldTest", summary="Building generator test", description="Generated buildings", author="Claude",
         version="0", date="", type=SOLO, minPlayers=1, maxPlayers=1)
m.d["nxz"] = False
m.d["ambient"] = [170, 170, 160]
m.rng = random.Random(seed)

UA, UB, VA, VB = 168, 344, -88, 88
for x, y in rect_tiles(UA, UB, VA, VB):
    m.tile(x, y, "GrassNorm")
from nox import rect_wall_cells
for x, y in rect_wall_cells(UA, UB, VA, VB):
    m.wall(x, y, "DecidiousWallGreen")

STYLES = ["log_cabin", "stucco_house", "galava_townhouse", "dunmir_hall", "cobble_house", "stone_house",
          "ogre_hut", "ruined_shack", "stucco_dark_house", "log_cabin", "stucco_house", "galava_townhouse"]
occupied = set()
built = []
slots = [(u, v) for v in range(VA + 6, VB - 30, 44) for u in range(UA + 6, UB - 30, 44)]
MAXSPAN = (36, 36)
for k, (u, v) in enumerate(slots):
    st = STYLES[k % len(STYLES)]
    b = generate_building(m, rng, (u, v), MAXSPAN, st, occupied=occupied, building_id=f"B{k}")
    if b is None:
        print("no fit", st, u, v); continue
    occupied |= b.cells
    built.append(b)
m.obj("PlayerStart", UA + 4, 0)

print(f"{'id':4} {'style':18} {'shape':9} {'units':7} rooms doors(int/ext) tiles  unreachable")
for b in built:
    nint = len({d.gap for r in b.rooms for d in r.doors if d.connects[1] != 'outside'})
    print(f"{b.id:4} {b.style:18} {b.shape:9} {b.size_units[0]}x{b.size_units[1]:<4} {len(b.rooms):5} {nint:3}/{len(b.entrances):<3}"
          f"       {len(b.footprint):5}  {b.unreachable}")
S = styles()
print("\nWestwood reference (freestanding medians): long x short units, rooms")
for st in sorted(set(STYLES)):
    s = S[st]
    print(f"  {st:18} {s['size_units']['W'][1]} x {s['size_units']['H'][1]}  rooms {list(s['rooms'].items())[:3]}")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "test_buildings")
print("\n".join(l for l in m.build(os.path.abspath(out)) if l.startswith(("OK", "ERROR"))))
json.dump([dict(id=b.id, style=b.style, shape=b.shape, rooms=[dict(id=r.id, kind=r.kind, tiles=len(r.tiles), floor=r.floor,
                doors=[(d.gap, d.line, d.type, d.connects) for d in r.doors]) for r in b.rooms]) for b in built],
          open(os.path.join(os.path.abspath(out), "buildings.json"), "w"), indent=1)

# ---- checks: valid wall pieces, reachability, editor load/save round trip
import subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tests"))
import noxmap
from nox import load_rules
valid = load_rules("walls")["valid_variations"]
gd = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "corpus", "out", "json", "things.json"), encoding="utf-8"))
WN = [w["name"] for w in gd["walls"]]
mp = os.path.join(os.path.abspath(out), "BldTest.map")
secs = noxmap.sections(mp)
bad = [w for w in noxmap.walls(secs["WallMap"]) if str(w[4]) not in valid.get(WN[w[3]], {}).get(str(w[2] & 0x7F), {})]
print(f"check: invalid wall pieces {len(bad)}", [(WN[w[3]], w[2] & 0x7F, w[4]) for w in bad[:5]])
print("check: unreachable rooms", sum(len(b.unreachable) for b in built))
repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
lst = os.path.join(os.path.abspath(out), "list.txt")
open(lst, "w").write(mp)
ps32 = os.path.join(os.environ["WINDIR"], "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
r = subprocess.run([ps32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(repo, "tests", "resave.ps1"),
                    "-Dll", os.path.join(repo, "Shared", "bin", "Release", "NoxShared.dll"), "-OutDir",
                    os.path.join(os.path.abspath(out), "resaved"), "-MapList", lst], capture_output=True, text=True)
import importlib.util
spec_ = importlib.util.spec_from_file_location("roundtrip", os.path.join(repo, "tests", "roundtrip.py"))
rt = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(rt)
print("check: editor round trip", r.stdout.strip().split("	")[0], rt.compare(mp, os.path.join(os.path.abspath(out), "resaved", "BldTest.map")) or "identical content")
