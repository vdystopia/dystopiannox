package PKG

// Triggers (dystopiannox mapgen/kit/trapkit/triggers.py): the "trigger" kind's own watchers and actions, added to
// the trap library (traps.go) through trapExt and start lines (run after StartTraps):
//   TrigHold(trigHold{...})       a hold row: a group on while anyone stands on any of its zones (Westwood's hold
//                                 counter, G_Castle arrow rows), switched on Delay frames after the first step
//   TrigEye(trigEye{...})         motion detection: lamps light on a clock; while they are lit (after a grace),
//                                 a player in the box who moves more than Thresh px in three frames sets off Acts
//   TrigLatchSet(trigLatch{...})  N of M: each key latched for Window frames by "trig_latch" (Target set, Text key),
//                                 its lamp lit while it lasts; all latched at once fires Acts (once)
//   TrigCountdown(trigCount{...}) a countdown: "trig_count" (Target) starts it, "trig_cancel" stops it; a tick sound
//                                 every Every frames (faster near the end if Faster), Acts when it runs out
//   TrigDeath(trigDeath{...})     a creature's death (or its body gone) fires Acts once: kill the guard, open the way
// Every frame is 1/30 s.

import (
	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/audio"
)

type trigHold struct {
	Name  string
	Group string
	Zones []string
	Delay int
	held  int
	on    bool
}

type trigEye struct {
	Name   string
	C      ns.Pointf
	U      ns.Pointf // unit vector along the box
	HU     float32
	HV     float32
	Lamps  string // group lit while the eye is open
	Period int
	Open   int // frames lit at the start of each period
	Grace  int // frames after lighting before it sees
	Thresh float32
	Cool   int
	Sound  string // when the lamps light
	Acts   []trapAct
	Armed  bool
	t0     int
	cool   int
}

type trigLatch struct {
	Name   string
	Keys   []string
	Lamps  []string // a group per key (or "")
	Window int
	Sound  string
	Acts   []trapAct
	until  []int
	done   bool
}

type trigCount struct {
	Name   string
	Ticks  int
	Every  int
	Faster bool
	Sound  string
	At     ns.Pointf
	Acts   []trapAct
	run    bool
	n      int
	next   int
}

type trigDeath struct {
	Name  string
	Obj   string
	Acts  []trapAct
	obj   ns.Obj
	found bool
	done  bool
}

type trigPos struct {
	hist [4]ns.Pointf
	n    int
}

var (
	trigOn      bool
	trigHolds   []*trigHold
	trigEyes    []*trigEye
	trigLatches = map[string]*trigLatch{}
	trigLatchL  []*trigLatch
	trigCounts  = map[string]*trigCount{}
	trigCountL  []*trigCount
	trigDeaths  []*trigDeath
	trigTrack   = map[int]*trigPos{}
)

func init() {
	trapExt["trig_latch"] = trigLatchAct
	trapExt["trig_count"] = func(a trapAct) {
		if c := trigCounts[a.Target]; c != nil && !c.run {
			c.run, c.n, c.next = true, 0, trapFrame
		}
	}
	trapExt["trig_cancel"] = func(a trapAct) {
		if c := trigCounts[a.Target]; c != nil {
			c.run = false
		}
	}
	trapExt["trig_arm_eye"] = func(a trapAct) {
		for _, e := range trigEyes {
			if e.Name == a.Target {
				if !e.Armed {
					e.t0 = trapFrame
				}
				e.Armed = true
			}
		}
	}
	trapExt["trig_disarm_eye"] = func(a trapAct) {
		for _, e := range trigEyes {
			if e.Name == a.Target {
				e.Armed = false
				trapSetGroup(e.Lamps, false)
			}
		}
	}
}

func trigStart() {
	if trigOn {
		return
	}
	trigOn = true
	ns.OnFrame(trigTick)
}

func TrigHold(h trigHold) {
	trigStart()
	hh := h
	trigHolds = append(trigHolds, &hh)
}

func TrigEye(e trigEye) {
	trigStart()
	ee := e
	ee.t0 = trapFrame
	trigEyes = append(trigEyes, &ee)
}

func TrigLatchSet(l trigLatch) {
	trigStart()
	ll := l
	ll.until = make([]int, len(l.Keys))
	trigLatches[l.Name] = &ll
	trigLatchL = append(trigLatchL, &ll)
}

func TrigCountdown(c trigCount) {
	trigStart()
	cc := c
	trigCounts[c.Name] = &cc
	trigCountL = append(trigCountL, &cc)
}

func TrigDeath(d trigDeath) {
	trigStart()
	dd := d
	trigDeaths = append(trigDeaths, &dd)
}

func trigLatchAct(a trapAct) {
	l := trigLatches[a.Target]
	if l == nil || l.done {
		return
	}
	for k, key := range l.Keys {
		if key != a.Text {
			continue
		}
		l.until[k] = trapFrame + l.Window
		if k < len(l.Lamps) && l.Lamps[k] != "" {
			trapSetGroup(l.Lamps[k], true)
		}
	}
	if l.Sound != "" {
		if z := trapZones[a.Text]; z != nil {
			ns.AudioEvent(audio.Name(l.Sound), z.C)
		}
	}
	for _, u := range l.until {
		if u <= trapFrame {
			return
		}
	}
	l.done = true
	trapFire(l.Acts)
}

func trigInBox(c, u ns.Pointf, hu, hv float32, p ns.Pointf) bool {
	dx, dy := p.X-c.X, p.Y-c.Y
	a := dx*u.X + dy*u.Y
	b := -dx*u.Y + dy*u.X
	if a < 0 {
		a = -a
	}
	if b < 0 {
		b = -b
	}
	return a <= hu && b <= hv
}

func trigTick() {
	for _, pl := range ns.Players() {
		u := pl.Unit()
		if u == nil {
			continue
		}
		id := u.ObjScriptID()
		t := trigTrack[id]
		if t == nil {
			t = &trigPos{}
			trigTrack[id] = t
		}
		t.hist[t.n%len(t.hist)] = u.Pos()
		t.n++
	}
	// hold rows
	for _, h := range trigHolds {
		occ := false
		for _, zn := range h.Zones {
			if z := trapZones[zn]; z != nil && z.Armed && z.in {
				occ = true
				break
			}
		}
		if occ {
			h.held++
			if !h.on && h.held > h.Delay {
				h.on = true
				trapSetGroup(h.Group, true)
			}
		} else {
			h.held = 0
			if h.on {
				h.on = false
				trapSetGroup(h.Group, false)
			}
		}
	}
	// eyes
	for _, e := range trigEyes {
		if !e.Armed || e.Period <= 0 {
			continue
		}
		if e.cool > 0 {
			e.cool--
		}
		t := (trapFrame - e.t0) % e.Period
		if t < 0 {
			t += e.Period
		}
		open := t < e.Open
		trapSetGroup(e.Lamps, open)
		if t == 0 && e.Sound != "" {
			ns.AudioEvent(audio.Name(e.Sound), e.C)
		}
		if !open || t < e.Grace || e.cool > 0 {
			continue
		}
		for _, pl := range ns.Players() {
			u := pl.Unit()
			if u == nil || u.CurrentHealth() <= 0 || !trigInBox(e.C, e.U, e.HU, e.HV, u.Pos()) {
				continue
			}
			tr := trigTrack[u.ObjScriptID()]
			if tr == nil || tr.n < 4 {
				continue
			}
			p := tr.hist[(tr.n-1)%len(tr.hist)]
			q := tr.hist[(tr.n-4)%len(tr.hist)]
			dx, dy := p.X-q.X, p.Y-q.Y
			if dx*dx+dy*dy > e.Thresh*e.Thresh {
				e.cool = e.Cool
				trapCaller = u
				trapFire(e.Acts)
				break
			}
		}
	}
	// latches: lamps out when their time is up
	for _, l := range trigLatchL {
		if l.done {
			continue
		}
		for k, u := range l.until {
			if u > 0 && u <= trapFrame {
				l.until[k] = 0
				if k < len(l.Lamps) && l.Lamps[k] != "" {
					trapSetGroup(l.Lamps[k], false)
				}
			}
		}
	}
	// countdowns
	for _, c := range trigCountL {
		if !c.run || trapFrame < c.next {
			continue
		}
		if c.n >= c.Ticks {
			c.run = false
			trapFire(c.Acts)
			continue
		}
		if c.Sound != "" {
			ns.AudioEvent(audio.Name(c.Sound), c.At)
		}
		c.n++
		step := c.Every
		if c.Faster && c.Ticks-c.n < 4 {
			step = c.Every / 2
		}
		if step < 1 {
			step = 1
		}
		c.next = trapFrame + step
	}
	// deaths
	for _, d := range trigDeaths {
		if d.done {
			continue
		}
		if d.obj == nil {
			d.obj = ns.Object(d.Obj)
			if d.obj != nil {
				d.found = true
			} else if d.found || trapFrame > 90 {
				d.done = true
				trapFire(d.Acts)
			}
			continue
		}
		if d.obj.CurrentHealth() <= 0 || uint32(d.obj.Flags())&0x20 != 0 {
			d.done = true
			trapCaller = d.obj
			trapFire(d.Acts)
		}
	}
}
