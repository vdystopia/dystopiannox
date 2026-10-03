"""Round-trip test: load stock maps with the built editor library, save them, and check
nothing was lost.

Compares walls, floor tiles, objects and waypoints as unordered collections, because the
editor legitimately reorders entries when it writes. Exits non-zero on any difference.

    py tests/roundtrip.py                 # small default set
    py tests/roundtrip.py --all           # every map in <nox>/maps
    py tests/roundtrip.py --nox "D:/Nox" --config Debug

Requires: pip install pycryptodome
"""
import argparse, collections, glob, os, subprocess, sys, winreg
import noxmap

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_MAPS = ["So_Galav", "So_Druid", "MiniMine", "Estate", "CapFlag", "Bunker", "con01a", "G_Castle"]
PS32 = os.path.join(os.environ["WINDIR"], "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")


def nox_dir():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Westwood\Nox") as k:
            return os.path.dirname(winreg.QueryValueEx(k, "InstallPath")[0])
    except OSError:
        return r"C:\GOG Games\Nox"


def compare(orig, saved):
    a, b = noxmap.sections(orig), noxmap.sections(saved)
    checks = {
        "sections": (sorted(a), sorted(b)),
        "walls": (noxmap.walls(a["WallMap"]), noxmap.walls(b["WallMap"])),
        "tiles": (noxmap.tiles(a["FloorMap"]), noxmap.tiles(b["FloorMap"])),
        "waypoints": (noxmap.waypoints(a["WayPoints"]), noxmap.waypoints(b["WayPoints"])),
        "objects": (noxmap.objects(a["ObjectTOC"], a["ObjectData"]), noxmap.objects(b["ObjectTOC"], b["ObjectData"])),
    }
    problems = []
    for name, (x, y) in checks.items():
        cx, cy = collections.Counter(map(repr, x)), collections.Counter(map(repr, y))
        if cx != cy:
            lost, added = cx - cy, cy - cx
            problems.append(f"{name}: {sum(lost.values())} lost, {sum(added.values())} added "
                            f"(e.g. {next(iter(lost), '-')} -> {next(iter(added), '-')})")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nox", default=nox_dir())
    ap.add_argument("--config", default="Release")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    dll = os.path.join(REPO, "Shared", "bin", args.config, "NoxShared.dll")
    if not os.path.exists(dll):
        sys.exit(f"{dll} not found - run build.ps1 first")
    if args.all:
        maps = sorted(glob.glob(os.path.join(args.nox, "maps", "*", "*.map")))
    else:
        maps = [m for d in DEFAULT_MAPS for m in glob.glob(os.path.join(args.nox, "maps", d, "*.map"))]
    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    maplist = os.path.join(out, "maps.txt")
    with open(maplist, "w", encoding="utf-8") as f:
        f.write("\n".join(maps))

    res = subprocess.run([PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(HERE, "resave.ps1"),
                          "-Dll", dll, "-OutDir", out, "-MapList", maplist],
                         capture_output=True, text=True)
    if res.returncode:
        sys.exit(res.stdout + res.stderr)

    passed = 0
    for line in res.stdout.splitlines():
        status, src, *err = line.split("\t")
        name = os.path.basename(src)
        if status != "OK":
            print(f"FAIL {name}: editor could not load/save: {err[0] if err else ''}"); continue
        problems = compare(src, os.path.join(out, name))
        passed += not problems
        print(f"{'FAIL' if problems else 'PASS'} {name}" + "".join(f"\n     {p}" for p in problems))
    print(f"\n{passed}/{len(maps)} maps round-trip cleanly")
    sys.exit(0 if passed == len(maps) else 1)


if __name__ == "__main__":
    main()
