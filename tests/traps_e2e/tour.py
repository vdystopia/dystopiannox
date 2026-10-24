"""The trap tour: every station of a TrapLab map played in the real game along the simulator's routes, without
touching the game folder (the ModLab harness's private data dir: py tests/modlab_e2e/lab.py setup).

    py tests/traps_e2e/tour.py <kind> [--max s]          a TrapLab map (mapgen/designs/traplab.py <kind>)

1. builds the lab map, 2. runs the simulator (review/traps/sim.py: plans, careless walk and run, <Name>.runs.json),
3. puts the map in the shadow with probe_tour_traps.go (the routes embedded), 4. starts a Solo game in OpenNox's e2e
mode and loads the map; the probe walks the hero through each station three times (plan, walk, run), the game's
traps doing the damage, and logs each run; 5. writes <Name>.tour.json and .tour.md beside the build, the game's
numbers beside the simulator's, and prints the table.
"""
import argparse, json, os, re, runpy, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tests", "modlab_e2e"))
sys.path.insert(0, os.path.join(REPO, "review", "traps"))
sys.path.insert(0, HERE)
import lab  # noqa: E402
import sim  # noqa: E402
import run as e2e  # noqa: E402


def go_list(xs):
    return "[]string{" + ", ".join(json.dumps(x) for x in xs) + "}"


def build(kind):
    sys.path.insert(0, os.path.join(REPO, "mapgen"))
    os.chdir(REPO)
    out = os.path.join(lab.WORK, "tourbuild")
    name = "TL" + kind.capitalize()
    shutil.rmtree(os.path.join(out, name), ignore_errors=True)        # each lab keeps its own build (the page reads it)
    os.makedirs(out, exist_ok=True)
    argv, sys.argv = sys.argv, ["traplab.py", kind, out]
    runpy.run_path(os.path.join(REPO, "mapgen", "designs", "traplab.py"), run_name="__main__")
    sys.argv = argv
    return name, os.path.join(out, name)


def probe_source(name, bdir):
    labinfo = json.load(open(os.path.join(bdir, f"{name}.lab.json")))
    data = json.load(open(os.path.join(bdir, f"{name}.traps.json")))
    runs = json.load(open(os.path.join(bdir, f"{name}.runs.json")))
    secret = {tuple(map(int, k.split(","))): v for k, v in labinfo.get("secret", {}).items()}
    st_go, run_go = [], []
    for k, st in enumerate(labinfo["stations"]):
        sm = sim.StationModel(data, st, [tuple(w) for w in labinfo["walls"]], secret)
        pre = st.get("prefix") or f"S{k + 1:02d}"
        names = set(sm.objs)
        grouped = {o for g in data["groups"].values() for o in g}
        on = sorted(o for o in names & grouped if data["objects"][o].get("enabled", True))
        off = sorted(o for o in names if not data["objects"][o].get("enabled", True))
        # off while the hero waits, on as the run starts: a globe's beam back at its base angle, a gun's timer
        # cleared (it fires at once when it sees him, then once a second: the simulator's phase)
        sentries = sorted(o for o in names if data["objects"][o]["type"].startswith(("SentryGlobe", "Skull", "ArrowTrap"))
                          and data["objects"][o].get("enabled", True))
        clocks = [c for c in data["clocks"] if c["name"].startswith(pre)]
        movers = [m for m in data["movers"] if m["name"].startswith(pre)]
        zones = [z for z in data["zones"] if z["name"].startswith(pre)]
        watches = [w for w in data.get("watches", []) if w["name"].startswith(pre)]
        closed = [list(wc) for wc in sm.secret if secret.get(wc) == "closed"]
        opened = [list(wc) for wc in sm.secret if secret.get(wc) == "open"]
        ws = ", ".join(f'{{{json.dumps(w["name"])}, {json.dumps(w["obj"])}, {data["objects"][w["obj"]]["x"]}, '
                       f'{data["objects"][w["obj"]]["y"]}}}' for w in watches)
        st_go.append(
            f'\t{json.dumps(st["label"])}: {{clocks: {go_list(c["name"] for c in clocks if c["armed"])}, '
            f'clocksOff: {go_list(c["name"] for c in clocks if not c["armed"])}, '
            f'movers: {go_list(m["name"] for m in movers if m["armed"])}, '
            f'moversOff: {go_list(m["name"] for m in movers if not m["armed"])}, '
            f'zones: {go_list(z["name"] for z in zones if z["armed"])}, '
            f'zonesOff: {go_list(z["name"] for z in zones if not z["armed"])}, on: {go_list(on)}, off: {go_list(off)}, '
            f'sentries: {go_list(sentries)}, prefix: {json.dumps(pre)}, '
            f'closed: [][2]int{{{", ".join(f"{{{a}, {b}}}" for a, b in closed)}}}, '
            f'open: [][2]int{{{", ".join(f"{{{a}, {b}}}" for a, b in opened)}}}, watches: []ptWatch{{{ws}}}}},')
        for kind in ("plan", "walk", "run"):
            pts = runs.get(st["label"], {}).get(kind)
            if not pts: continue
            flat = ", ".join(f"{x:.1f}, {y:.1f}, {a}" for x, y, a in pts)
            run_go.append(f'\t{{{json.dumps(st["label"])}, {json.dumps(kind)}, []float32{{{flat}}}}},')
    src = open(os.path.join(HERE, "probe_tour_traps.go"), encoding="utf-8").read()
    src = src.replace("\t//STATIONS", "\n".join(st_go)).replace("\t//RUNS", "\n".join(run_go))
    if os.path.exists(os.path.join(bdir, f"{name}_scripts", "traps_trigger.go")):   # its eyes start their clock again
        eyes = """func ptEyes(prefix string) {
    for _, e := range trigEyes {
        if prefix != "" && len(e.Name) >= len(prefix) && e.Name[:len(prefix)] == prefix {
            e.t0, e.cool = trapFrame, 0
        }
    }
}
"""
    else:
        eyes = "func ptEyes(prefix string) {}"
    src = src.replace("//EYES", eyes)
    hx, hy = labinfo["hub_start"]
    src = src.replace("LIMBOX, LIMBOY", f"{hx}, {hy}")
    total = sum(len(runs[l][k]) for l in runs for k in runs[l]) + 30 * sum(len(runs[l]) for l in runs)
    return src, total


def main(kind, max_s=None, built=None):
    if built:                                   # an already built trap map (a gauntlet, a mission): tour its passages
        bdir = built
        name = json.load(open(next(os.path.join(bdir, f) for f in os.listdir(bdir) if f.endswith(".lab.json"))))["name"]
    else:
        name, bdir = build(kind)
    rows = sim.analyse(bdir)
    src, frames = probe_source(name, bdir)
    dst = os.path.join(lab.SH, "maps", name)
    if os.path.isjunction(dst): os.rmdir(dst)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst)
    shutil.copy2(os.path.join(bdir, f"{name}.map"), dst)
    for f in os.listdir(os.path.join(bdir, f"{name}_scripts")):
        shutil.copy2(os.path.join(bdir, f"{name}_scripts", f), dst)
    shutil.copy2(os.path.join(bdir, f"{name}.strings.json"), dst)
    subprocess.run([sys.executable, os.path.join(REPO, "mapgen", "strings.py"), "--nox", lab.SH], capture_output=True)
    pkg = name.lower()
    open(os.path.join(dst, "zz_probe.go"), "w", encoding="utf-8", newline="\n").write(
        src.replace("package PKG", f"package {pkg}", 1))
    open(os.path.join(lab.SH, "autoexec.rul"), "w").write(f"load {pkg}\n")
    save = os.path.join(lab.SH, "Save")
    if os.listdir(save):
        os.rename(save, os.path.join(lab.WORK, f"oldsave_{os.getpid()}"))
        os.makedirs(save)
    steps = [("wait", frames + 400)]
    yml = os.path.join(lab.WORK, "tour.yaml")
    open(yml, "w").write(e2e.yaml_for("warrior", steps))
    log = os.path.join(lab.LOGS, f"tour_{name}.txt")
    max_s = max_s or int(frames / 30) + 120
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(REPO, "tests", "modlab_e2e", "e2e.ps1"), "-Yaml", yml, "-Max", str(max_s),
                        "-Out", log, "-Shadow", lab.SH, "-Config", os.path.join(lab.WORK, "lab.yml")],
                       capture_output=True, text=True)
    print(" / ".join(l for l in r.stdout.splitlines() if l.strip()))
    game = {}
    for l in open(log, encoding="utf-8", errors="replace"):
        m = re.search(r"probe: (T[LGD]-\S+) (plan|walk|run) lost=(\d+) outcome=(\w+) frames=(\d+)", l)
        if m:
            game.setdefault(m.group(1), {})[m.group(2)] = (int(m.group(3)), m.group(4))
        elif "panic" in l.lower():
            print("  ", l.strip()[:300])
    report = []
    md = [f"# {name}: the tour in the game", "", "Each station played by the probe along the simulator's routes "
          "(tests/traps_e2e/tour.py): the game's damage and outcome beside the simulator's replay.", "",
          "| Station | Tier | Plan: game / sim | Careless walk: game / sim | Careless run: game / sim | Verdict |",
          "|---|---|---|---|---|---|"]
    for row in rows:
        g = game.get(row["label"], {})
        rec = dict(label=row["label"], tier=row["tier"], sim=row, game=g)
        report.append(rec)
        gp, gw, gr = g.get("plan"), g.get("walk"), g.get("run")
        fmt = lambda v: f"{v[0]} {v[1]}" if v else "-"
        md.append(f"| {row['label']} {row['title']} | {row['tier']} | {fmt(gp)} / {row.get('replay')} "
                  f"{row.get('replay_outcome', '')} | {fmt(gw)} / {fmt(row.get('careless_walk_0'))} | {fmt(gr)} / "
                  f"{fmt(row.get('careless_run_0'))} | {row['verdict']} |")
    json.dump(report, open(os.path.join(bdir, f"{name}.tour.json"), "w"), indent=1)
    open(os.path.join(bdir, f"{name}.tour.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", help="a TrapLab kind, or - with --built")
    ap.add_argument("--max", type=int)
    ap.add_argument("--built", help="the folder of a built trap map (TrapGnt, TrapDem): tour it as built")
    a = ap.parse_args()
    main(a.kind, a.max, a.built)
