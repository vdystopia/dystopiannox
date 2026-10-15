"""BossLab with a real player, without touching the game folder: the ModLab harness's private data dir (the "shadow",
tests/modlab_e2e/lab.py setup) gets its own BossLab build plus a probe script, then the installed opennox-hd.exe in
OpenNox's e2e mode (NOX_E2E: scripted input) starts a Solo game, loads BossLab and takes a screenshot every ~2 s while
the probe tours the bosses (probe_tour.go). Screens land in %TEMP%\\modlab_e2e\\testdata, the log in ...\\logs\\boss.txt.

    py tests/modlab_e2e/lab.py setup              (once)
    py tests/bosslab_e2e/run.py [class] [max_s] [--from=k]   (class: warrior, wizard, conjurer; k: first boss, 0-9)
"""
import json, os, re, runpy, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tests", "modlab_e2e"))
import lab  # noqa: E402  (WORK, SH, LOGS, CLASS_X)


def build():
    sys.path.insert(0, os.path.join(REPO, "mapgen"))
    os.chdir(REPO)
    argv, sys.argv = sys.argv, ["bosslab.py", "-"]
    g = runpy.run_path(os.path.join(REPO, "mapgen", "designs", "bosslab.py"), run_name="lab")
    sys.argv = argv
    m = g["m"]
    tmp = os.path.join(lab.WORK, "bossbuild")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    m.build(tmp, check=False)
    dst = os.path.join(lab.SH, "maps", "BossLab")
    if os.path.isjunction(dst):           # the shadow links every installed map: BossLab gets its own folder
        os.rmdir(dst)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst)
    shutil.copy2(os.path.join(tmp, "BossLab.map"), dst)
    for f in os.listdir(os.path.join(tmp, "BossLab_scripts")):
        shutil.copy2(os.path.join(tmp, "BossLab_scripts", f), dst)
    json.dump(g["TEXT"], open(os.path.join(dst, "BossLab.strings.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    csf = os.path.join(lab.SH, "nox.csf.json")
    assert not os.path.exists(csf) or os.stat(csf).st_nlink == 1, "the shadow's nox.csf.json must be its own copy"
    subprocess.run([sys.executable, os.path.join(REPO, "mapgen", "strings.py"), "--nox", lab.SH], capture_output=True)
    return dst


def play(cls="warrior", max_s=330, first=0):
    dst = build()
    src = open(os.path.join(HERE, "probe_tour.go"), encoding="utf-8").read().replace(
        "const prFirst = 0", f"const prFirst = {first}")
    open(os.path.join(dst, "zz_probe.go"), "w", encoding="utf-8", newline="\n").write(src)
    open(os.path.join(lab.SH, "autoexec.rul"), "w").write("load bosslab\n")
    save = os.path.join(lab.SH, "Save")
    if os.listdir(save):
        os.rename(save, os.path.join(lab.WORK, f"oldsave_{os.getpid()}"))
        os.makedirs(save)
    shots = os.path.join(lab.WORK, "testdata")
    for f in os.listdir(shots) if os.path.isdir(shots) else []:
        if f.startswith("b"): os.remove(os.path.join(shots, f))
    steps = [("w", 900), ("c", 384, 168, "solo"), ("w", 500), ("c", lab.CLASS_X[cls], 208, "class"), ("w", 100),
             ("c", 552, 653, "accept"), ("w", 400), ("c", 344, 605, "accept_name"), ("w", 300)]
    for k in range(120):
        steps += [("w", 60), ("s", f"b{k:03d}")]
    out = ["steps:"]
    for s in steps:
        if s[0] == "w": out += ["  - action: wait", f"    dt: {s[1]}"]
        elif s[0] == "c": out += ["  - action: click", f"    x: {s[1]}", f"    y: {s[2]}", f"    name: {s[3]}"]
        elif s[0] == "s": out += ["  - action: screen", f"    name: {s[1]}"]
    out += ["  - action: wait", "    dt: 1", "    name: end"]
    yml = os.path.join(lab.WORK, "boss.yaml")
    open(yml, "w").write("\n".join(out) + "\n")
    log = os.path.join(lab.LOGS, "boss.txt")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(REPO, "tests", "modlab_e2e", "e2e.ps1"), "-Yaml", yml, "-Max", str(max_s),
                        "-Out", log, "-Shadow", lab.SH, "-Config", os.path.join(lab.WORK, "lab.yml")],
                       capture_output=True, text=True)
    print(" / ".join(l for l in r.stdout.splitlines() if l.strip()))
    for l in open(log, encoding="utf-8", errors="replace"):
        if "probe:" in l or "panic" in l.lower() or "STATE: b0" in l or "bosslab:" in l:
            print("  ", l.rstrip()[:400])


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--from=")]
    first = next((int(x[7:]) for x in sys.argv[1:] if x.startswith("--from=")), 0)
    play(*(a[0:1] or ["warrior"]), *([int(a[1])] if len(a) > 1 else [330]), first=first)
