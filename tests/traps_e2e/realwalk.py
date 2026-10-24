"""The careless player with real input: every station of a built trap map walked (or run) straight through by OpenNox's
e2e input, the game's own physics doing the rest (shoves, belts, gusts, pits, plates, blades), to see what a player
who does not read the trap pays. The tour (tour.py) moves the hero by script and so cannot be shoved; this can.

    py tests/traps_e2e/realwalk.py <built_dir> [--run] [--max s]

The probe holds the hero at each station's way in for a moment, lets the input walk him in the station's direction
for as long as a crossing takes (plus a margin), then logs what he lost and whether he got through, fell or stuck,
and moves him on to the next station at a fixed time (the input's schedule is known to the probe, counted from the
first step). Writes <Name>.realwalk.json beside the build and prints a table.
"""
import argparse, json, math, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tests", "modlab_e2e"))
sys.path.insert(0, HERE)
import lab  # noqa: E402
import run as e2e  # noqa: E402

SQ = 32.5
HOLD, AFTER = 40, 20

PROBE = r'''package PKG

// The careless walker (tests/traps_e2e/realwalk.py): stations walked by real input; the probe holds the hero at each
// way in until the input's next walk starts, counted from the first step, and logs each crossing.

import (
	"fmt"

	"github.com/noxworld-dev/noxscript/ns/v4"
)

type rwStation struct {
	label  string
	start  ns.Pointf
	ux, uy float32
	length float32
	t0, t1 int // frames after the first step: the walk starts, the window closes
}

var rwStations = []rwStation{
//STATIONS
}

var (
	rwF, rwT, rwK, rwLost, rwLast int
	rwBase, rwMin                 int // health as the walk starts, the lowest since
	rwGo, rwDone, rwFell, rwOut   bool
	rwHold                         = ns.Ptf(0, 0)
)

func init() { ns.OnFrame(rwFrame) }

func rwFrame() {
	h := ns.GetHost()
	if h == nil {
		return
	}
	rwF++
	if rwF == 30 {
		h.SetMaxHealth(3000)
		h.SetHealth(3000)
	}
	if rwF < 60 || len(rwStations) == 0 {
		return
	}
	if !rwGo { // hold at the first way in until the input's first step
		s := rwStations[0]
		h.SetHealth(3000)
		p := h.Pos()
		if rwT > 10 && (p.X-s.start.X)*(p.X-s.start.X)+(p.Y-s.start.Y)*(p.Y-s.start.Y) > 1 {
			rwGo, rwT = true, 0
			rwLast = h.CurrentHealth()
			println("probe: go")
			return
		}
		rwT++
		h.SetPos(s.start)
		return
	}
	if rwK >= len(rwStations) {
		if !rwDone {
			rwDone = true
			println("probe: realwalk done")
		}
		return
	}
	rwT++
	s := rwStations[rwK]
	if rwT < s.t0 { // between walks: held at this station's way in
		h.SetHealth(3000)
		h.SetPos(s.start)
		rwLast, rwLost, rwFell, rwOut = h.CurrentHealth(), 0, false, false
		return
	}
	hp := h.CurrentHealth()
	if rwT == s.t0 { // the walk starts: count from here
		rwBase, rwMin, rwLost, rwLast = hp, hp, 0, hp
	}
	if hp < rwLast {
		rwLost += rwLast - hp
	}
	if hp < rwMin {
		rwMin = hp
	}
	rwLast = hp
	p := h.Pos()
	a := ((p.X-s.start.X)*s.ux + (p.Y-s.start.Y)*s.uy) / 32.5
	outcome := ""
	if uint32(h.Flags())&0x20000 != 0 {
		outcome = "fell"
	} else if rwLost >= 2000 {
		outcome = "died"
	} else if a >= s.length {
		outcome = "passed"
	} else if rwT >= s.t1 {
		outcome = fmt.Sprintf("stuck at %.1f", a)
	}
	if outcome != "" {
		println(fmt.Sprintf("probe: %s lost=%d outcome=%s frames=%d hp0=%d low=%d", s.label, rwLost, outcome, rwT-s.t0, rwBase, rwMin))
		rwK++
		rwLost = 0
		h.SetHealth(3000)
	}
}
'''


def main(bdir, run=False, max_s=None):
    labf = next(f for f in os.listdir(bdir) if f.endswith(".lab.json"))
    info = json.load(open(os.path.join(bdir, labf)))
    name = info["name"]
    speed = 6.9 if run else 3.3
    t0, rows, steps = 0, [], []
    for k, st in enumerate(info["stations"]):
        L = st["L"]
        T = int((L + 1.5) * SQ / speed) + 40
        ux, uy = st["along"]
        rows.append(f'	{{{json.dumps(st["label"])}, ns.Ptf({st["start"][0]}, {st["start"][1]}), {ux:.4f}, {uy:.4f}, '
                    f'{L + 0.3}, {t0}, {t0 + T}}},')
        ang = (math.atan2(ux, -uy) / math.pi) % 2.0          # half-turns clockwise from up the screen
        if k:
            steps.append(("wait", HOLD))
        steps += [("runstart" if run else "walkstart", round(ang, 4)), ("wait", T), ("stop",), ("wait", AFTER)]
        t0 += T + 5 + AFTER + HOLD                             # a stop holds 5 frames more (e2e runEnd)
    t = t0
    # the first station starts at the first step (t0 = 0): the others at their t0
    src = PROBE.replace("//STATIONS", "\n".join(rows)).replace("package PKG", f"package {name.lower()}", 1)
    dst = os.path.join(lab.SH, "maps", name)
    if os.path.isjunction(dst): os.rmdir(dst)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst)
    shutil.copy2(os.path.join(bdir, f"{name}.map"), dst)
    for f in os.listdir(os.path.join(bdir, f"{name}_scripts")):
        shutil.copy2(os.path.join(bdir, f"{name}_scripts", f), dst)
    sj = os.path.join(bdir, f"{name}.strings.json")
    if os.path.exists(sj):
        shutil.copy2(sj, dst)
        subprocess.run([sys.executable, os.path.join(REPO, "mapgen", "strings.py"), "--nox", lab.SH], capture_output=True)
    open(os.path.join(dst, "zz_probe.go"), "w", encoding="utf-8", newline="\n").write(src)
    open(os.path.join(lab.SH, "autoexec.rul"), "w").write(f"load {name.lower()}\n")
    save = os.path.join(lab.SH, "Save")
    if os.listdir(save):
        os.rename(save, os.path.join(lab.WORK, f"oldsave_{os.getpid()}"))
        os.makedirs(save)
    yml = os.path.join(lab.WORK, "realwalk.yaml")
    open(yml, "w").write(e2e.yaml_for("warrior", [("wait", 420)] + steps + [("wait", 60)]))
    log = os.path.join(lab.LOGS, f"realwalk_{name}.txt")
    max_s = max_s or int((t + 600) / 30) + 90
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(REPO, "tests", "modlab_e2e", "e2e.ps1"), "-Yaml", yml, "-Max", str(max_s),
                        "-Out", log, "-Shadow", lab.SH, "-Config", os.path.join(lab.WORK, "lab.yml")],
                       capture_output=True, text=True)
    print(" / ".join(l for l in r.stdout.splitlines() if l.strip()))
    res = {}
    for l in open(log, encoding="utf-8", errors="replace"):
        m = re.search(r"probe: (T[LGD]-\S+) lost=(\d+) outcome=(.+?) frames=(\d+)", l)
        hm = re.search(r"hp0=(\d+) low=(\d+)", l)
        if m:
            res[m.group(1)] = dict(lost=int(m.group(2)), outcome=m.group(3), frames=int(m.group(4)),
                                   hp0=int(hm.group(1)) if hm else None, low=int(hm.group(2)) if hm else None)
        elif "panic" in l.lower():
            print("  ", l.strip()[:200])
    key = "run" if run else "walk"
    out = os.path.join(bdir, f"{name}.realwalk.json")
    old = json.load(open(out)) if os.path.exists(out) else {}
    old[key] = res
    json.dump(old, open(out, "w"), indent=1)
    for st in info["stations"]:
        r_ = res.get(st["label"])
        print(f"  {st['label']:14s} {st.get('tier', ''):8s} careless {key}: " +
              (f"{r_['lost']} HP, {r_['outcome']} (health {r_.get('hp0')}, lowest {r_.get('low')})" if r_ else "no result"))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("built")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--max", type=int)
    a = ap.parse_args()
    main(a.built, a.run, a.max)
