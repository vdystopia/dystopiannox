"""ModLab's powers tested with a real player, and its self-test on the dedicated server, without touching the game
folder (QA round 1, review/qa1/mods.md).

Everything runs on a private data dir (the "shadow", default %TEMP%\\modlab_e2e\\shadow, or MODLAB_E2E_DIR): hard links
to the game's files, its own copies of the files the game or the tools write (nox.cfg, autoexec.rul, nox.csf.json),
junctions to the big folders and to every installed map but ModLab, which is the worktree's own build. OpenNox runs
with `-data <shadow>`.

    py tests/modlab_e2e/lab.py setup                     make the shadow
    py tests/modlab_e2e/lab.py server [seconds]          arena build into the shadow, the dedicated server's self-test
    py tests/modlab_e2e/lab.py play <probe> [class] [max_s]
          Solo build plus a probe script (probe_warrior.go, probe_wizard.go, probe_fx.go) in the shadow's ModLab; then
          the installed opennox-hd.exe in OpenNox's e2e mode (NOX_E2E: scripted input) starts a Solo game as `class`
          (warrior, wizard, conjurer), loads ModLab (autoexec.rul, NOX_DEV) and clicks melee to the east over and over,
          with a screenshot (the e2e "screen" action) every 13 clicks into <dir>\\testdata. The probe logs "probe: ..."
          lines into <dir>\\logs\\play.txt.
    py tests/modlab_e2e/lab.py teardown                  remove the shadow's links and junctions (never follows one)

A game window opens while `play` runs (OpenNox has no headless client); e2e mode never writes nox.cfg, and the runner
checks the game's nox.cfg is unchanged.
"""
import json, os, re, runpy, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
NOX = r"C:\GOG Games\Nox"
WORK = os.environ.get("MODLAB_E2E_DIR") or os.path.join(tempfile.gettempdir(), "modlab_e2e")
SH = os.path.join(WORK, "shadow")
LOGS = os.path.join(WORK, "logs")
COPIED = (".log", ".cfg", ".rul", ".json", ".yml")
CFG = """game:
  data: {data}
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
video:
  size:
    height: 768
    width: 1024
"""
# the class portraits and buttons on OpenNox's 1024x768 menu (measured on a screenshot)
CLASS_X = {"warrior": 256, "conjurer": 520, "wizard": 768}


def junction(link, target):
    subprocess.run(["cmd", "/c", "mklink", "/J", link, target], check=True, capture_output=True)


def setup():
    os.makedirs(SH, exist_ok=True)
    for f in os.listdir(NOX):
        src, dst = os.path.join(NOX, f), os.path.join(SH, f)
        if not os.path.isfile(src) or os.path.exists(dst):
            continue
        if f.lower().endswith(COPIED):
            shutil.copy2(src, dst)
        else:
            os.link(src, dst)
    for d in ("Dialog", "MOVIES", "MUSIC", "window"):
        if os.path.isdir(os.path.join(NOX, d)) and not os.path.exists(os.path.join(SH, d)):
            junction(os.path.join(SH, d), os.path.join(NOX, d))
    md = os.path.join(SH, "maps")
    os.makedirs(md, exist_ok=True)
    for m in os.listdir(os.path.join(NOX, "maps")):
        src = os.path.join(NOX, "maps", m)
        if m.lower() != "modlab" and os.path.isdir(src) and not os.path.exists(os.path.join(md, m)):
            junction(os.path.join(md, m), src)
    for d in ("Save", "logs", "testdata"):
        os.makedirs(os.path.join(SH if d == "Save" else WORK, d), exist_ok=True)
    open(os.path.join(WORK, "lab.yml"), "w").write(CFG.format(data=SH.replace("\\", "/")))
    print("shadow ready:", SH, len(os.listdir(md)), "maps")


def teardown():
    md = os.path.join(SH, "maps")
    for m in os.listdir(md) if os.path.isdir(md) else []:
        p = os.path.join(md, m)
        if os.path.isjunction(p):
            os.rmdir(p)
    for d in ("Dialog", "MOVIES", "MUSIC", "window"):
        p = os.path.join(SH, d)
        if os.path.isjunction(p):
            os.rmdir(p)
    for f in os.listdir(SH):
        p = os.path.join(SH, f)
        if os.path.isfile(p):
            os.remove(p)
    print("left in the shadow:", os.listdir(SH))


def build(arena):
    sys.path.insert(0, os.path.join(REPO, "mapgen"))
    os.chdir(REPO)
    argv, sys.argv = sys.argv, ["modlab.py", "-"]
    g = runpy.run_path(os.path.join(REPO, "mapgen", "designs", "modlab.py"), run_name="lab")
    sys.argv = argv
    from nox import ARENA
    m = g["m"]
    if arena:
        m.d["info"]["type"] = ARENA
    tmp = os.path.join(WORK, "build")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    m.build(tmp, check=False)
    dst = os.path.join(SH, "maps", "ModLab")
    assert not os.path.isjunction(dst)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst)
    shutil.copy2(os.path.join(tmp, "ModLab.map"), dst)
    for f in os.listdir(os.path.join(tmp, "ModLab_scripts")):
        shutil.copy2(os.path.join(tmp, "ModLab_scripts", f), dst)
    json.dump(g["TEXT"], open(os.path.join(dst, "ModLab.strings.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    csf = os.path.join(SH, "nox.csf.json")
    assert not os.path.exists(csf) or os.stat(csf).st_nlink == 1, "the shadow's nox.csf.json must be its own copy"
    r = subprocess.run([sys.executable, os.path.join(REPO, "mapgen", "strings.py"), "--nox", SH], capture_output=True, text=True)
    print((r.stdout + r.stderr).strip().splitlines()[-1:])
    return dst


def server(seconds):
    build(True)
    log = os.path.join(LOGS, f"server_{int(time.time())}.log")
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        p = subprocess.Popen([os.path.join(NOX, "opennox-server.exe"), "-config", os.path.join(WORK, "lab.yml"),
                              "-port", "18657", "-autoexec", "load modlab"], cwd=SH, stdout=f, stderr=subprocess.STDOUT)
        time.sleep(seconds)
        p.kill(); p.wait()
    text = open(log, encoding="utf-8", errors="replace").read()
    print("log:", log, "| map scripts loaded:", 'map script(s) loaded: "modlab"' in text)
    for l in text.splitlines():
        if ("selftest" in l and "IsHit event" not in l) or "panic" in l.lower() or "ERROR" in l:
            print("  ", l.split("[console]: ")[-1].strip()[:300])


def play(probe, cls="warrior", max_s=200):
    dst = build(False)
    src = open(os.path.join(HERE, probe), encoding="utf-8").read()
    open(os.path.join(dst, "zz_probe.go"), "w", encoding="utf-8", newline="\n").write(
        re.sub(r"^package \w+", "package modlab", src, count=1, flags=re.M))
    open(os.path.join(SH, "autoexec.rul"), "w").write("load modlab\n")
    save = os.path.join(SH, "Save")
    if os.listdir(save):
        os.rename(save, os.path.join(WORK, f"oldsave_{int(time.time())}"))
        os.makedirs(save)
    steps = [("w", 900), ("c", 384, 168, "solo"), ("w", 500), ("c", CLASS_X[cls], 208, "class"), ("w", 100),
             ("c", 552, 653, "accept"), ("w", 400), ("c", 344, 605, "accept_name"), ("w", 300)] + [("m",)] * 10
    for k in range(60):
        steps += [("m",)] * 13 + [("s", f"s{k:03d}")]
    out = ["steps:"]
    for s in steps:
        if s[0] == "w": out += ["  - action: wait", f"    dt: {s[1]}"]
        elif s[0] == "c": out += ["  - action: click", f"    x: {s[1]}", f"    y: {s[2]}", f"    name: {s[3]}"]
        elif s[0] == "m": out += ["  - action: melee", "    dt: 20", "    ang: 0.5"]
        elif s[0] == "s": out += ["  - action: screen", f"    name: {s[1]}"]
    out += ["  - action: wait", "    dt: 1", "    name: end"]
    yml = os.path.join(WORK, "play.yaml")      # e2e "screen" files land in <the yaml's folder>\testdata
    open(yml, "w").write("\n".join(out) + "\n")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(HERE, "e2e.ps1"),
                        "-Yaml", yml, "-Max", str(max_s), "-Out", os.path.join(LOGS, "play.txt"), "-Shadow", SH,
                        "-Config", os.path.join(WORK, "lab.yml")], capture_output=True, text=True)
    print(" / ".join(l for l in r.stdout.splitlines() if l.strip()))
    for l in open(os.path.join(LOGS, "play.txt"), encoding="utf-8", errors="replace"):
        if "probe:" in l or "panic" in l.lower():
            print("  ", l.split("[console]: ")[-1].rstrip())


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "setup": setup()
    elif cmd == "teardown": teardown()
    elif cmd == "server": server(int(sys.argv[2]) if len(sys.argv) > 2 else 50)
    elif cmd == "play": play(sys.argv[2], *(sys.argv[3:4] or ["warrior"]), *([int(sys.argv[4])] if len(sys.argv) > 4 else []))
    else: raise SystemExit(__doc__)
