package PKG

// The trap tour (tests/traps_e2e/tour.py): the hero, given 3000 health, walks every station of a trap map along
// routes the simulator wrote (review/traps/sim.py: the best plan, a careless walk and a careless run). The probe
// moves him frame by frame (SetPos), so the game's own traps and damage decide what each route costs. A script
// cannot make him jump (the engine clears an AIRBORNE flag set from a script: the first tour, 2026-10-23), so for a
// plan's jump frames he waits at LIMBO (the hall's start, no traps) and lands where the jump lands: what a jump
// clears is measured with real input apart (tests/traps_e2e/jumptest.py). Before each run the station's traps are put back as they started (clocks restarted,
// movers and zones reset, objects and secret walls in their first state, items back on their spots).

import (
	"fmt"

	"github.com/noxworld-dev/noxscript/ns/v4"
)

type ptWatch struct {
	name, obj string
	x, y      float32
}

type ptStation struct {
	clocks, clocksOff, movers, moversOff, zones, zonesOff []string
	on, off                                                []string
	sentries                                               []string // switched off while the hero waits: the beam back at its base angle
	prefix                                                 string   // the station's object prefix (its eyes are <prefix>Eye)
	closed, open                                           [][2]int
	watches                                                []ptWatch
}

type ptRun struct {
	label, kind string
	pts         []float32 // x, y, airborne (0/1) per frame
}

var ptStations = map[string]*ptStation{
	//STATIONS
}

var ptRuns = []ptRun{
	//RUNS
}

var ptLimbo = ns.Ptf(LIMBOX, LIMBOY)

var (
	ptGF, ptK, ptPhase, ptF, ptHold, ptLost, ptLast int
	ptDone, ptFell                                   bool
)

func init() {
	ns.OnFrame(ptFrame)
}

func ptLog(s string) { println("probe: " + s) }

func ptPt(r ptRun, k int) (ns.Pointf, bool) {
	return ns.Ptf(r.pts[3*k], r.pts[3*k+1]), r.pts[3*k+2] > 0.5
}

func ptReset(label string) {
	st := ptStations[label]
	if st == nil {
		return
	}
	trapQueue = nil
	ptEyes(st.prefix)
	for _, c := range st.clocks {
		if cl := trapClocks[c]; cl != nil {
			cl.Armed = true
			cl.t0 = trapFrame
		}
	}
	for _, c := range st.clocksOff {
		if cl := trapClocks[c]; cl != nil {
			cl.Armed = false
		}
	}
	for _, m := range st.movers {
		trapDo(trapAct{Kind: "reset", Target: m})
		if mv := trapMovers[m]; mv != nil {
			mv.Armed = true
		}
	}
	for _, m := range st.moversOff {
		trapDo(trapAct{Kind: "reset", Target: m})
		if mv := trapMovers[m]; mv != nil {
			mv.Armed = false
		}
	}
	for _, z := range st.zones {
		if zz := trapZones[z]; zz != nil {
			zz.fired, zz.in, zz.cool, zz.state, zz.Armed = false, false, 0, false, true
		}
	}
	for _, z := range st.zonesOff {
		if zz := trapZones[z]; zz != nil {
			zz.fired, zz.in, zz.cool, zz.state, zz.Armed = false, false, 0, false, false
		}
	}
	for _, g := range trapGroups {
		g.set = false
	}
	for _, n := range st.sentries {
		if o := ns.Object(n); o != nil {
			o.Enable(true)
		}
	}
	for _, n := range st.on {
		if o := ns.Object(n); o != nil {
			o.Enable(true)
		}
	}
	for _, n := range st.off {
		if o := ns.Object(n); o != nil {
			o.Enable(false)
		}
	}
	for _, w := range st.closed {
		if wl := ns.Wall(w[0], w[1]); wl != nil {
			wl.Enable(true)
		}
	}
	for _, w := range st.open {
		if wl := ns.Wall(w[0], w[1]); wl != nil {
			wl.Enable(false)
		}
	}
	h := ns.GetHost()
	for _, wt := range st.watches {
		it := ns.Object(wt.obj)
		if it == nil {
			continue
		}
		if h != nil && it.GetHolder() != nil {
			h.Drop(it)
		}
		it.SetPos(ns.Ptf(wt.x, wt.y))
		for _, tw := range trapWatches {
			if tw.Name == wt.name {
				tw.done, tw.obj, tw.found = false, it, true
			}
		}
	}
}

func ptEnd(h ns.Obj, r ptRun, outcome string) {
	ptLog(fmt.Sprintf("%s %s lost=%d outcome=%s frames=%d", r.label, r.kind, ptLost, outcome, ptF))
	ptFell = outcome == "fell"
	ptK++
	ptPhase, ptHold = 0, 0
}

func ptFrame() {
	h := ns.GetHost()
	if h == nil {
		return
	}
	ptGF++
	if ptGF == 30 {
		h.SetMaxHealth(3000)
		h.SetHealth(3000)
		ptLog(fmt.Sprintf("tour of %d runs", len(ptRuns)))
	}
	if ptGF < 90 || !trapsOn {
		return
	}
	if ptK >= len(ptRuns) {
		if !ptDone {
			ptDone = true
			ptLog("tour done")
		}
		return
	}
	r := ptRuns[ptK]
	if ptPhase == 0 { // hold at the run's first point (longer after a fall: let the fall end)
		p, _ := ptPt(r, 0)
		h.SetHealth(3000)
		h.SetPos(p)
		if st := ptStations[r.label]; st != nil {
			for _, n := range st.sentries { // a globe's angle goes back to its base only while it is off
				if o := ns.Object(n); o != nil {
					o.Enable(false)
				}
			}
		}
		ptHold++
		hold := 20
		if ptFell {
			hold = 45
		}
		if ptHold >= hold {
			ptReset(r.label)
			ptPhase, ptF, ptLost = 1, 0, 0
			ptLast = h.CurrentHealth()
		}
		return
	}
	hp := h.CurrentHealth()
	if hp < ptLast {
		d := ptLast - hp
		ptLost += d
		if d >= 400 { // a sentry's beam: death
			ptEnd(h, r, "died")
			return
		}
	}
	ptLast = hp
	if uint32(h.Flags())&0x20000 != 0 { // FALLING: into a pit
		ptEnd(h, r, "fell")
		return
	}
	n := len(r.pts) / 3
	if ptF >= n {
		ptEnd(h, r, "passed")
		return
	}
	p, air := ptPt(r, ptF)
	if air {
		h.SetPos(ptLimbo)
	} else {
		h.SetPos(p)
	}
	if st := ptStations[r.label]; st != nil {
		for _, wt := range st.watches {
			it := ns.Object(wt.obj)
			if it != nil && it.GetHolder() == nil {
				ip := it.Pos()
				if (ip.X-p.X)*(ip.X-p.X)+(ip.Y-p.Y)*(ip.Y-p.Y) < 400 {
					h.Pickup(it)
				}
			}
		}
	}
	ptF++
}

//EYES
