"""Loads a generated map in the OpenNox dedicated server to prove it loads and its scripts start: the server refuses
Solo maps, so an arena-flagged build of the design is swapped into maps/<Name>/ for the test and the installed Solo
files are put back afterwards (the folder's scripts and text stay as installed).

    py tests/server_smoke.py mapgen/designs/thornwick.py [--seconds 25]

Prints whether the map loaded, any panic or script error lines, and the scripts' self-check lines (NPC behaviours,
quests). The server runs with a private config: no lobby listing, no port forwarding, no xwis registration.
"""
import argparse, os, runpy, shutil, subprocess, sys, tempfile, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOX = r"C:\GOG Games\Nox"
CFG = """game:
  data: {nox}
network:
  lobby:
    address: ""
  port_forward: false
  xwis:
    register: false
server:
  control:
    allow_cmds: false
    allow_map_change: false
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design"); ap.add_argument("--seconds", type=int, default=25)
    a = ap.parse_args()
    sys.path.insert(0, os.path.join(REPO, "mapgen"))
    tmp = tempfile.mkdtemp(prefix="nox_smoke_")
    argv = sys.argv
    sys.argv = [a.design]
    g = runpy.run_path(os.path.abspath(a.design), run_name="smoke")
    sys.argv = argv
    from nox import ARENA
    m = g["m"]
    name = m.d["name"]
    m.d["info"]["type"] = ARENA
    m.build(tmp, check=False)
    dst = os.path.join(NOX, "maps", name)
    os.makedirs(dst, exist_ok=True)
    keep = {}
    for ext in (".map", ".nxz"):
        p = os.path.join(dst, name + ext)
        if os.path.exists(p):
            keep[p] = p + ".smoke_keep"; shutil.move(p, keep[p])
    shutil.copy2(os.path.join(tmp, name + ".map"), dst)
    sd = os.path.join(tmp, name + "_scripts")
    if os.path.isdir(sd) and not any(f.endswith(".go") for f in os.listdir(dst)):   # not installed yet: the scripts too
        for f in os.listdir(sd): shutil.copy2(os.path.join(sd, f), dst)
    cfg = os.path.join(tmp, "smoke.yml")
    open(cfg, "w").write(CFG.format(nox=NOX))
    log = os.path.join(tmp, "server.log")
    try:
        with open(log, "w", encoding="utf-8", errors="replace") as f:
            p = subprocess.Popen([os.path.join(NOX, "opennox-server.exe"), "-config", cfg, "-autoexec", f"load {name.lower()}"],
                                 cwd=NOX, stdout=f, stderr=subprocess.STDOUT)
            time.sleep(a.seconds)
            p.kill(); p.wait()
    finally:
        os.remove(os.path.join(dst, name + ".map"))
        for orig, k in keep.items(): shutil.move(k, orig)
    text = open(log, encoding="utf-8", errors="replace").read()
    loaded = f'map script(s) loaded: "{name.lower()}"' in text
    bad = [l for l in text.splitlines() if any(w in l.lower() for w in ("panic", "error:", "undefined", "cannot", "failed"))
           and "registry" not in l and "CRC check failed" not in l            # every map, stock ones too
           and "Failed to load compressed file" not in l]                      # no .nxz: the .map is read
    print(f"{name}: server loaded={loaded} problems={len(bad)}")
    for l in bad[:30]: print("  !", l.strip())
    for l in text.splitlines():
        if "self-check" in l or "quests:" in l or "go scripts" in l: print("   ", l.strip())
    if "quests self-check" in text and "quests: started" not in text:
        print("  ! the quests never started: MapInitialize did not fire in the server")
    os.makedirs(os.path.join(REPO, "tests", "out"), exist_ok=True)
    shutil.copy2(log, os.path.join(REPO, "tests", "out", f"{name}_server.log"))
    shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(0 if loaded and not bad else 1)


if __name__ == "__main__":
    main()
