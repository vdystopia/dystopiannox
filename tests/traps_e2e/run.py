"""Trap maps with a real player, without touching the game folder: the ModLab harness's private data dir (the
"shadow", tests/modlab_e2e/lab.py setup) gets its own build of a trap design plus a probe script, then the installed
opennox-hd.exe in OpenNox's e2e mode (NOX_E2E: scripted input) starts a Solo game and loads the map. The probe
(a Go file in the map's package) stands the hero where the test wants and logs "probe: ..." lines; the e2e input may
walk, run and jump (steps). Screens land in %TEMP%\\modlab_e2e\\testdata (t*.png), the log in ...\\logs\\traps.txt.

    py tests/modlab_e2e/lab.py setup                    (once)
    py tests/traps_e2e/run.py traptest [class] [max_s]  the engine bench (mapgen/designs/traptest.py, probe_bench.go)
    py tests/traps_e2e/run.py <design> --probe <file.go> --steps <steps.json> [--class c] [--max s]

steps.json: a list of ["wait", frames] | ["walk"|"run", ang, frames] | ["jump"] | ["screen", name] |
["walkdir"|"rundir", ang] | ["walkstart"|"runstart", ang] | ["stop"]; ang in half-turns clockwise from up the screen
(0 north, 0.5 east, 1 south, 1.5 west), frames at 30 a second (OpenNox's e2e counts frames).
"""
import json, os, re, runpy, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tests", "modlab_e2e"))
import lab  # noqa: E402  (WORK, SH, LOGS, CLASS_X)

MENU = [("w", 900), ("c", 384, 168, "solo"), ("w", 500), ("c", None, 208, "class"), ("w", 100),
        ("c", 552, 653, "accept"), ("w", 400), ("c", 344, 605, "accept_name"), ("w", 300)]


def build(design, out_name=None):
    """Build mapgen/designs/<design>.py into the shadow's maps/<Name>/ (its own folder, not the junction)."""
    sys.path.insert(0, os.path.join(REPO, "mapgen"))
    os.chdir(REPO)
    tmp = os.path.join(lab.WORK, "trapbuild")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    argv, sys.argv = sys.argv, [f"{design}.py", tmp]
    g = runpy.run_path(os.path.join(REPO, "mapgen", "designs", f"{design}.py"), run_name="__main__")
    sys.argv = argv
    name = g["NAME"] if "NAME" in g else g["m"].d["name"]
    dst = os.path.join(lab.SH, "maps", name)
    if os.path.isjunction(dst):
        os.rmdir(dst)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst)
    shutil.copy2(os.path.join(tmp, f"{name}.map"), dst)
    sd = os.path.join(tmp, f"{name}_scripts")
    for f in os.listdir(sd) if os.path.isdir(sd) else []:
        shutil.copy2(os.path.join(sd, f), dst)
    sj = os.path.join(tmp, f"{name}.strings.json")
    if os.path.exists(sj):
        shutil.copy2(sj, dst)
        csf = os.path.join(lab.SH, "nox.csf.json")
        assert not os.path.exists(csf) or os.stat(csf).st_nlink == 1, "the shadow's nox.csf.json must be its own copy"
        subprocess.run([sys.executable, os.path.join(REPO, "mapgen", "strings.py"), "--nox", lab.SH], capture_output=True)
    return name, dst, tmp, g


def yaml_for(cls, steps):
    out = ["steps:"]
    for s in MENU:
        if s[0] == "w": out += ["  - action: wait", f"    dt: {s[1]}"]
        else: out += ["  - action: click", f"    x: {s[1] if s[1] is not None else lab.CLASS_X[cls]}", f"    y: {s[2]}",
                      f"    name: {s[3]}"]
    for s in steps:
        k = s[0]
        if k == "wait": out += ["  - action: wait", f"    dt: {int(s[1])}"]
        elif k in ("walk", "run"): out += [f"  - action: {k}", f"    ang: {s[1]}", f"    dt: {int(s[2])}"]
        elif k in ("walkdir", "rundir"): out += [f"  - action: {k[:-3]}-dir", f"    ang: {s[1]}"]
        elif k in ("walkstart", "runstart"): out += [f"  - action: {k[:-5]}-start", f"    ang: {s[1]}"]
        elif k == "stop": out += ["  - action: walk-stop"]
        elif k == "jump": out += ["  - action: jump"]
        elif k == "screen": out += ["  - action: screen", f"    name: {s[1]}"]
        elif k == "click": out += ["  - action: interact", f"    x: {s[1]}", f"    y: {s[2]}"]
        else: raise ValueError(s)
    out += ["  - action: wait", "    dt: 1", "    name: end"]
    return "\n".join(out) + "\n"


def play(design, probe_src, steps, cls="warrior", max_s=200, log_name="traps.txt"):
    name, dst, tmp, g = build(design)
    pkg = name.lower()
    open(os.path.join(dst, "zz_probe.go"), "w", encoding="utf-8", newline="\n").write(
        re.sub(r"^package \w+", f"package {pkg}", probe_src, count=1, flags=re.M))
    open(os.path.join(lab.SH, "autoexec.rul"), "w").write(f"load {pkg}\n")
    save = os.path.join(lab.SH, "Save")
    if os.listdir(save):
        os.rename(save, os.path.join(lab.WORK, f"oldsave_{os.getpid()}"))
        os.makedirs(save)
    shots = os.path.join(lab.WORK, "testdata")
    for f in os.listdir(shots) if os.path.isdir(shots) else []:
        if f.startswith("t"): os.remove(os.path.join(shots, f))
    yml = os.path.join(lab.WORK, "traps.yaml")
    open(yml, "w").write(yaml_for(cls, steps))
    log = os.path.join(lab.LOGS, log_name)
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(REPO, "tests", "modlab_e2e", "e2e.ps1"), "-Yaml", yml, "-Max", str(max_s),
                        "-Out", log, "-Shadow", lab.SH, "-Config", os.path.join(lab.WORK, "lab.yml")],
                       capture_output=True, text=True)
    print(" / ".join(l for l in r.stdout.splitlines() if l.strip()))
    lines = []
    for l in open(log, encoding="utf-8", errors="replace"):
        if "probe:" in l or "traps:" in l or "panic" in l.lower() or "error" in l.lower() and "script" in l.lower():
            lines.append(l.split("[console]: ")[-1].rstrip())
    return lines, tmp


def bench(cls="warrior", max_s=240):
    """TrapTest: the probe stands the hero in each trap in turn (probe_bench.go reads TrapTest.tests.json)."""
    name, dst, tmp, g = build("traptest")
    info = json.load(open(os.path.join(tmp, "TrapTest.tests.json")))
    tests = "\n".join(f"\t{{{json.dumps(t['name'])}, ns.Ptf({t['at'][0]}, {t['at'][1]}), {t['frames']}}},"
                      for t in info["tests"])
    src = open(os.path.join(HERE, "probe_bench.go"), encoding="utf-8").read()
    src = src.replace("//TESTS", tests).replace("JUMPX, JUMPY", f"{info['jump_from'][0]}, {info['jump_from'][1]}")
    src = src.replace("WALLX, WALLY", f"{info['wall'][0]}, {info['wall'][1]}")
    src = src.replace("RUNX, RUNY", f"{info['run_from'][0]}, {info['run_from'][1]}")
    src = src.replace("LEVERX, LEVERY", f"{info['lever_from'][0]}, {info['lever_from'][1]}")
    total = sum(t["frames"] + 15 for t in info["tests"]) + 120
    # the input, mirrored by the probe's prInputs: nothing while the probe tours the traps; then (1) walk south-east
    # and jump over a plate and a flame line, (2) walk onto the plate and through the flames, (3) run, (4) run and
    # jump, (5) click the lever one square south-east of the hero (the camera centres him on the 1024x768 screen)
    dx, dy = (info["lever_at"][0] - info["lever_from"][0], info["lever_at"][1] - info["lever_from"][1])
    steps = [("wait", total + 200), ("screen", "t_before"),
             ("walkstart", 0.75), ("wait", 4), ("jump",), ("wait", 12), ("screen", "t_jump"), ("wait", 30), ("stop",),
             ("wait", 120),
             ("walkstart", 0.75), ("wait", 20), ("screen", "t_walkin"), ("wait", 20), ("stop",), ("wait", 120),
             ("runstart", 0.75), ("wait", 30), ("stop",), ("wait", 100),
             ("runstart", 0.75), ("wait", 6), ("jump",), ("wait", 30), ("stop",), ("wait", 100),
             ("wait", 60), ("click", int(512 + dx), int(384 + dy - 8)), ("wait", 60), ("screen", "t_lever"),
             ("wait", 120)]
    lines, _ = play("traptest", src, steps, cls, max_s)
    for l in lines: print("  ", l)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: raise SystemExit(__doc__)
    if a[0] == "traptest":
        bench(*(a[1:2] or ["warrior"]), *([int(a[2])] if len(a) > 2 else []))
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("design"); ap.add_argument("--probe", required=True); ap.add_argument("--steps", required=True)
        ap.add_argument("--class", dest="cls", default="warrior"); ap.add_argument("--max", type=int, default=200)
        o = ap.parse_args(a)
        lines, _ = play(o.design, open(o.probe, encoding="utf-8").read(), json.load(open(o.steps)), o.cls, o.max)
        for l in lines: print("  ", l)
