"""What a real jump clears: JumpTest (mapgen/designs/jumptest.py) played with real input in OpenNox's e2e mode.

    py tests/traps_e2e/jumptest.py [--lead 0.6]

The probe holds the hero at the start until the input moves him, then logs his place and health every frame; the
input runs south-east down the hall and presses jump `lead` squares before each strip (timed from the run speed
measured on 2026-10-23: 6.83 units a frame after a first frame of 3.7). Prints, per strip depth, the damage taken
on it: 0 means the jump cleared it.
"""
import argparse, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run as e2e  # noqa: E402

SQ, RUN = 32.5, 6.83

PROBE = """package jumptest

import (
	"fmt"

	"github.com/noxworld-dev/noxscript/ns/v4"
)

var jtF, jtT int
var jtGo bool
var jtStart = ns.Ptf(STARTX, STARTY)

func init() { ns.OnFrame(jtFrame) }

func jtFrame() {
	h := ns.GetHost()
	if h == nil {
		return
	}
	jtF++
	if jtF == 30 {
		h.SetMaxHealth(3000)
	}
	if jtF < 60 {
		return
	}
	if !jtGo {
		h.SetHealth(3000)
		p := h.Pos()
		if jtT > 5 && (p.X-jtStart.X)*(p.X-jtStart.X)+(p.Y-jtStart.Y)*(p.Y-jtStart.Y) > 1 {
			jtGo = true
			jtT = 0
			println("probe: go")
			return
		}
		jtT++
		h.SetPos(jtStart)
		return
	}
	jtT++
	if jtT <= 320 {
		p := h.Pos()
		println(fmt.Sprintf("probe: jt %d %.1f %.1f %d", jtT, p.X, p.Y, h.CurrentHealth()))
	}
}
"""


def main(lead=0.6):
    info_dir = None
    steps = []
    # the start is at a = 1.0; jump `lead` squares before each strip
    strips = [(6.0, 1.5), (14.0, 2.0), (22.0, 2.5), (30.0, 3.0), (38.0, 3.5)]
    t_prev = 0
    steps.append(("wait", 420))
    steps.append(("runstart", 0.75))
    for a, dep in strips:
        dist = (a - lead - 1.0) * SQ
        t = 1 + (dist - 3.7) / RUN
        dt = int(round(t)) - t_prev
        steps.append(("wait", max(1, dt)))
        steps.append(("jump",))
        t_prev += max(1, dt) + 1
    steps.append(("wait", 60))
    steps.append(("stop",))
    steps.append(("wait", 60))
    from run import build
    name, dst, tmp, g = build("jumptest")
    info = json.load(open(os.path.join(tmp, "JumpTest.jump.json")))
    src = PROBE.replace("STARTX, STARTY", f"{info['start'][0]}, {info['start'][1]}")
    lines, _ = e2e.play("jumptest", src, steps, "warrior", 150, log_name="jumptest.txt")
    ox, oy = info["origin"]; ux, uy = info["along"]
    track = []
    for l in lines:
        m_ = re.search(r"probe: jt (\d+) ([\d.]+) ([\d.]+) (\d+)", l)
        if m_:
            t, x, y, hp = int(m_.group(1)), float(m_.group(2)), float(m_.group(3)), int(m_.group(4))
            a = ((x - ox) * ux + (y - oy) * uy) / SQ
            track.append((t, a, hp))
    print(f"{len(track)} frames logged; lead {lead}")
    res = []
    for a0, dep in strips:
        lost = 0
        for (t1, a1, h1), (t2, a2, h2) in zip(track, track[1:]):
            if a0 - 0.6 <= a2 <= a0 + dep + 0.6 and h2 < h1: lost += h1 - h2
        res.append((dep, lost))
        print(f"  strip {dep} squares deep at a={a0}: lost {lost}")
    if track:
        print("  speed check: a at frames 10/20/30:", [round(a, 2) for t, a, h in track if t in (10, 20, 30)])
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lead", type=float, default=0.6)
    a = ap.parse_args()
    main(a.lead)
