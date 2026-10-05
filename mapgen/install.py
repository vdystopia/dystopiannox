"""Installs a built map into the game: maps/<Name>/<Name>.map (and .nxz), its scripts (<Name>_scripts/*.go, which
OpenNox runs from the map's folder) and its own text (<Name>.strings.json), then rebuilds the game's string table
with every installed map's text (mapgen/strings.py writes nox.csf.json).

    py mapgen/install.py <out dir> <Name> [--nox "C:\\GOG Games\\Nox"]

Old script files in the map's folder are removed first, so a script dropped from the design does not linger.
"""
import argparse, glob, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def install(out_dir, name, nox=r"C:\GOG Games\Nox"):
    dst = os.path.join(nox, "maps", name)
    os.makedirs(dst, exist_ok=True)
    for f in glob.glob(os.path.join(dst, "*.go")): os.remove(f)
    done = []
    for ext in (".map", ".nxz", ".strings.json"):
        src = os.path.join(out_dir, name + ext)
        if os.path.exists(src):
            shutil.copy2(src, dst); done.append(name + ext)
        elif ext == ".nxz" and os.path.exists(os.path.join(dst, name + ext)):
            os.remove(os.path.join(dst, name + ext))      # a stale compressed copy would be loaded instead
    sd = os.path.join(out_dir, name + "_scripts")
    for f in glob.glob(os.path.join(sd, "*.go")):
        shutil.copy2(f, dst); done.append(os.path.basename(f))
    r = subprocess.run([sys.executable, os.path.join(HERE, "strings.py"), "--nox", nox], capture_output=True, text=True)
    print(f"installed {name}: {', '.join(done)}")
    print((r.stdout + r.stderr).strip())
    if r.returncode: sys.exit(r.returncode)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir"); ap.add_argument("name")
    ap.add_argument("--nox", default=r"C:\GOG Games\Nox")
    a = ap.parse_args()
    install(a.out_dir, a.name, a.nox)
