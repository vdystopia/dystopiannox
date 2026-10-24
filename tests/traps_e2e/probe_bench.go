package traptest

// The trap bench probe (tests/traps_e2e/run.py traptest): the hero, given 3000 health, is stood in each trap of
// TrapTest in turn and left there (no input), and the probe logs his health and position every 10 frames and at the
// end of each test. Then it holds him before the flame line until the e2e input starts to walk, and logs his
// path and health every 3 frames while the input walks, jumps and walks on.

import (
	"fmt"

	"github.com/noxworld-dev/noxscript/ns/v4"
)

type prTest struct {
	name   string
	at     ns.Pointf
	frames int
}

var prTests = []prTest{
//TESTS
}

var (
	prF      int
	prK      = -1
	prT      int
	prStart  ns.Pointf
	prPhase  int
	prJumpT  int
	prWallXY = [2]int{WALLX, WALLY}
)

func init() {
	ns.OnFrame(prFrame)
}

func prLog(s string) { println("probe: " + s) }

func prFrame() {
	h := ns.GetHost()
	if h == nil {
		return
	}
	prF++
	if prF == 30 {
		h.SetMaxHealth(3000)
		h.SetHealth(3000)
		prLog(fmt.Sprintf("host %d/%d at %.0f,%.0f", h.CurrentHealth(), h.MaxHealth(), h.Pos().X, h.Pos().Y))
	}
	if prF < 60 {
		return
	}
	if prPhase == 0 {
		prBench(h)
		return
	}
	prJumpTest(h)
}

func prBench(h ns.Obj) {
	if prK < 0 || prT >= prTests[prK].frames+15 {
		if prK >= 0 {
			t := prTests[prK]
			p := h.Pos()
			prLog(fmt.Sprintf("%s end lost=%d moved=%.0f,%.0f", t.name, 3000-h.CurrentHealth(), p.X-prStart.X, p.Y-prStart.Y))
			if t.name == "wall" {
				if w := ns.Wall(prWallXY[0], prWallXY[1]); w != nil {
					w.Enable(true)
				}
			}
		}
		prK++
		prT = 0
		if prK >= len(prTests) {
			prPhase = 1
			prLog("bench done")
			return
		}
		t := prTests[prK]
		h.SetHealth(3000)
		h.SetPos(t.at)
		prStart = t.at
		prLog(fmt.Sprintf("%s start at %.0f,%.0f frame %d", t.name, t.at.X, t.at.Y, ns.Frame()))
		if t.name == "wall" {
			w := ns.Wall(prWallXY[0], prWallXY[1])
			if w == nil {
				prLog("wall: no wall at that cell")
			} else {
				prLog(fmt.Sprintf("wall: enabled=%v", w.IsEnabled()))
				w.Enable(false)
				prLog(fmt.Sprintf("wall: after Enable(false) enabled=%v", w.IsEnabled()))
			}
		}
	}
	t := prTests[prK]
	prT++
	if t.name == "push" && prT == 5 {
		p := h.Pos()
		h.PushTo(ns.Ptf(p.X-50, p.Y-50), 30)
	}
	if t.name == "plate" && prT == 30 {
		h.SetPos(ns.Ptf(t.at.X-60, t.at.Y-60))
	}
	if t.name == "lever" && prT == 40 {
		h.SetPos(ns.Ptf(t.at.X-60, t.at.Y-60))
	}
	if t.name == "lever" && prT == 60 {
		h.SetPos(t.at)
	}
	if t.name == "wall" && prT == 30 {
		if w := ns.Wall(prWallXY[0], prWallXY[1]); w != nil {
			w.Enable(true)
			prLog(fmt.Sprintf("wall: after Enable(true) enabled=%v", w.IsEnabled()))
		}
	}
	if prT%10 == 0 && prT <= t.frames {
		p := h.Pos()
		prLog(fmt.Sprintf("%s t=%d hp=%d pos=%.0f,%.0f", t.name, prT, h.CurrentHealth(), p.X, p.Y))
	}
}

// the input tests, in the order the e2e input runs them: hold the hero at the point until the input moves him
// ("move") or for a fixed time ("fixed": a click test), then log his path and health for `logs` frames
type prInput struct {
	name  string
	at    ns.Pointf
	fixed int
	logs  int
}

var prInputs = []prInput{
	{"jump", ns.Ptf(JUMPX, JUMPY), 0, 90},
	{"walkin", ns.Ptf(JUMPX, JUMPY), 0, 90},
	{"run", ns.Ptf(RUNX, RUNY), 0, 60},
	{"runjump", ns.Ptf(RUNX, RUNY), 0, 60},
	{"lever", ns.Ptf(LEVERX, LEVERY), 0, 90},
}

var (
	prIn     int
	prHolding = true
)

func prJumpTest(h ns.Obj) {
	if prIn >= len(prInputs) {
		return
	}
	in := prInputs[prIn]
	if prHolding {
		h.SetHealth(3000)
		p := h.Pos()
		dx, dy := p.X-in.at.X, p.Y-in.at.Y
		moved := in.fixed == 0 && prJumpT > 5 && dx*dx+dy*dy > 1.0
		if moved || (in.fixed > 0 && prJumpT >= in.fixed) {
			prHolding = false
			prJumpT = 0
			prLog(fmt.Sprintf("%s go at frame %d", in.name, ns.Frame()))
			return
		}
		prJumpT++
		h.SetPos(in.at)
		return
	}
	prJumpT++
	if prJumpT%3 == 0 && prJumpT <= in.logs {
		p := h.Pos()
		prLog(fmt.Sprintf("%s t=%d hp=%d pos=%.0f,%.0f", in.name, prJumpT, h.CurrentHealth(), p.X, p.Y))
	}
	if prJumpT >= in.logs {
		prIn++
		prHolding = true
		prJumpT = 0
		if prIn >= len(prInputs) {
			prLog("done")
		}
	}
}
