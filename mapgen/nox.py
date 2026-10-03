"""Helpers for writing Nox maps from Python. A design script builds a spec with these helpers
and calls build(); build_map.ps1 then writes the map with the editor's own library.

Grid facts (verified against stock maps and the editor):
- Walls and floor tiles sit on cells where x + y is even.
- Rooms are rectangles in rotated coordinates u = x + y, v = x - y; on screen they look like
  diamonds. room() takes u/v bounds.
- Wall facing: 0 = '/' run (constant u), 1 = '\\' run (constant v), corners 7-10.
- Objects use world pixels: 23 px per grid cell.
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PS32 = os.path.join(os.environ["WINDIR"], "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
CELL = 23

# Weapon durability Westwood used in its multiplayer maps (most common value per weapon,
# surveyed from the stock maps). Higher than thing.bin's base health, which the editor uses.
STOCK_DURABILITY = {
    "BattleAxe": 300, "Bow": 1000, "CrossBow": 500, "ForceWand": 500, "GreatSword": 400,
    "LesserFireballWand": 100, "Longsword": 180, "MorningStar": 200, "RoundChakram": 300,
    "Sword": 200, "WarHammer": 350,
}

# Corner facings for a u/v rectangle, keyed by (u is min, v is min).
_CORNERS = {(True, True): 8, (True, False): 9, (False, True): 7, (False, False): 10}


def uv_to_xy(u, v):
    return (u + v) / 2, (u - v) / 2


def px(u, v):
    """World pixel position of a point given in u/v coordinates (may be fractional)."""
    x, y = uv_to_xy(u, v)
    return round(x * CELL, 1), round(y * CELL, 1)


class Spec:
    def __init__(self, name, **info):
        assert len(name) <= 8, "map names are limited to 8 characters"
        self.d = dict(name=name, info=info, ambient=[150, 150, 150], walls=[], tiles=[], objects=[])

    def room(self, u0, u1, v0, v1, wall, floor, variations=1, seed=0):
        """Walled rectangular room in u/v coordinates (all bounds even)."""
        assert all(n % 2 == 0 for n in (u0, u1, v0, v1))
        walls = {}
        for v in range(v0, v1 + 2, 2):
            for u in (u0, u1): walls[(u, v)] = 0
        for u in range(u0, u1 + 2, 2):
            for v in (v0, v1): walls[(u, v)] = 1
        for u in (u0, u1):
            for v in (v0, v1): walls[(u, v)] = _CORNERS[(u == u0, v == v0)]
        for i, ((u, v), facing) in enumerate(sorted(walls.items())):
            x, y = uv_to_xy(u, v)
            self.d["walls"].append(dict(x=int(x), y=int(y), facing=facing, material=wall,
                                        variation=(i * 7 + seed) % variations))
        # Floor fills the room offset by one tile, matching stock maps.
        for u in range(u0, u1 - 1, 2):
            for v in range(v0 + 2, v1 + 1, 2):
                x, y = uv_to_xy(u, v)
                self.d["tiles"].append(dict(x=int(x), y=int(y), material=floor))

    def obj(self, type_, u, v, team=None):
        x, y = px(u, v)
        o = dict(type=type_, x=x, y=y)
        if team is not None: o["team"] = team
        if type_ in STOCK_DURABILITY: o["durability"] = STOCK_DURABILITY[type_]
        self.d["objects"].append(o)

    def build(self, out_dir):
        """Write the map (and .nxz) into out_dir. Returns the builder's report lines."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(self.d, f, indent=1)
        try:
            res = subprocess.run([PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                  os.path.join(HERE, "build_map.ps1"), "-Spec", f.name, "-OutDir", out_dir],
                                 capture_output=True, text=True)
        finally:
            os.unlink(f.name)
        lines = (res.stdout + res.stderr).strip().splitlines()
        if res.returncode or not any(l.startswith("OK") for l in lines):
            sys.exit("map build failed:\n" + "\n".join(lines))
        return lines
