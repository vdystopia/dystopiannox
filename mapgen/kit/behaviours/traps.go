package PKG

// Traps (dystopiannox mapgen/kit/traps.py writes this file and traps_config.go into a map's scripts).
//
// Westwood drives its traps from map scripts: a plate or a lever runs a function that switches a group of spikes,
// flames or arrow traps on and off, moves spike blocks along waypoints, opens walls, wakes monsters. This library
// does the same from data (traps_config.go): every frame it
//   - runs the clocks: a group of trap objects switched on and off in windows of a repeating period;
//   - moves the movers: an object (a spike block, a pushing wall block) along a path of points at a speed, there and
//     back or round a loop, pausing at the ends;
//   - watches the zones: a plate, a tripwire or a sensor (a diamond, circle or box a player, or any creature, stands
//     in); a zone fires its actions when entered (once, or again after it re-arms) and others when left;
//   - watches the switches: a lever or button object whose enabled state the player flips;
//   - runs the actions due: switch a group on, off or for a while (a pulse), arm or disarm a clock, mover or zone,
//     cast a spell from a point at a point (fireball and gas traps), open or close walls, wake monsters, say a line.
// Clocks, movers and zones may start disarmed: an action arms them (a lever that starts the blades turning).
// Every frame is 1/30 s.

import (
	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/audio"
	"github.com/noxworld-dev/noxscript/ns/v4/spell"
)

type trapAct struct {
	Kind   string // on off toggle pulse arm disarm cast walls_open walls_close wake say reset
	Target string // a group, clock, mover or zone name
	Delay  int    // frames after the trigger
	Frames int    // pulse: frames on
	Spell  string
	From   ns.Pointf
	To     ns.Pointf
	Walls  [][2]int
	Text   string
}

type trapGroup struct {
	Name string
	Objs []string
	objs []ns.Obj
	on   bool
	set  bool
}

type trapClock struct {
	Name   string
	Group  string
	Period int
	On     [][2]int // windows [t0, t1) in the period when the group is on
	Phase  int
	Armed  bool
	t0     int
}

type trapMover struct {
	Name  string
	Objs  []string // moved together, each keeping its offset from the first
	Path  []ns.Pointf
	Speed float32 // world units a frame
	Mode  string  // pingpong, loop, once
	Pause int     // frames at each end (pingpong) or at the start of each lap (loop)
	Armed bool
	// state
	objs  []ns.Obj
	offs  []ns.Pointf
	seg   int
	along float32
	dir   int
	wait  int
	done  bool
}

type trapZone struct {
	Name    string
	Shape   string // diamond (a pressure plate's box), circle, box (an axis box: C +- R, H)
	C       ns.Pointf
	R       float32
	H       float32
	Who     string // player, any
	Jump    bool   // a jumping player passes over it (a pressure plate; an invisible trigger catches jumpers)
	Toggle  bool   // a lever: each touch alternates Acts and Release (leave the zone before it flips again)
	Once    bool
	Rearm   int // frames before it can fire again after it was left
	Armed   bool
	Acts    []trapAct
	Release []trapAct
	in      bool
	fired   bool
	cool    int
	state   bool
	who     ns.Obj
}

type trapSwitch struct {
	Name string
	Obj  string
	Acts []trapAct // when flipped either way
	obj  ns.Obj
	last bool
	seen bool
}

// A watch: an object (a gold pile, a key) picked up or gone fires its actions once.
type trapWatch struct {
	Name  string
	Obj   string
	Acts  []trapAct
	obj   ns.Obj
	done  bool
	found bool
}

// Actions of a kind's own (kit/behaviours/traps_<kind>.go registers them in its init): trapDo calls
// trapExt[kind] for any kind it does not know.
var trapExt = map[string]func(a trapAct){}

type trapPending struct {
	at  int
	act trapAct
}

var (
	trapsOn      bool
	trapFrame    int
	trapGroups   = map[string]*trapGroup{}
	trapClocks   = map[string]*trapClock{}
	trapMovers   = map[string]*trapMover{}
	trapZones    = map[string]*trapZone{}
	trapSwitches []*trapSwitch
	trapWatches  []*trapWatch
	trapCaller   ns.Obj // the last zone's toucher: "cast_at_caller" aims at him
	trapQueue    []trapPending
	trapOrder    []string // clocks, then movers, then zones, in the order defined (deterministic)
)

func TrapGroup(name string, objs ...string) {
	trapGroups[name] = &trapGroup{Name: name, Objs: objs}
}

func TrapClock(c trapClock) {
	cc := c
	trapClocks[c.Name] = &cc
}

func TrapMover(m trapMover) {
	mm := m
	mm.dir = 1
	trapMovers[m.Name] = &mm
}

func TrapZone(z trapZone) {
	zz := z
	trapZones[z.Name] = &zz
	trapOrder = append(trapOrder, z.Name)
}

func TrapWatch(w trapWatch) {
	ww := w
	trapWatches = append(trapWatches, &ww)
}

func TrapSwitch(s trapSwitch) {
	ss := s
	trapSwitches = append(trapSwitches, &ss)
}

func (g *trapGroup) resolve() {
	if g.objs != nil {
		return
	}
	for _, n := range g.Objs {
		if o := ns.Object(n); o != nil {
			g.objs = append(g.objs, o)
		}
	}
}

func (g *trapGroup) setOn(on bool) {
	g.resolve()
	if g.set && g.on == on {
		return
	}
	g.on, g.set = on, true
	for _, o := range g.objs {
		o.Enable(on)
	}
}

func trapSetGroup(name string, on bool) {
	if g := trapGroups[name]; g != nil {
		g.setOn(on)
	}
}

// StartTraps begins the clocks at the current frame and puts every clocked group in its first state.
func StartTraps() {
	if trapsOn {
		return
	}
	trapsOn = true
	for _, c := range trapClocks {
		c.t0 = trapFrame
	}
	for _, m := range trapMovers {
		trapMoverResolve(m)
	}
	ns.OnFrame(trapTick)
}

func trapTick() {
	trapFrame++
	// the actions due
	if len(trapQueue) > 0 {
		keep := trapQueue[:0]
		var due []trapAct
		for _, p := range trapQueue {
			if p.at <= trapFrame {
				due = append(due, p.act)
			} else {
				keep = append(keep, p)
			}
		}
		trapQueue = keep
		for _, a := range due {
			trapDo(a)
		}
	}
	for _, c := range trapClocks {
		if !c.Armed {
			continue
		}
		t := (trapFrame - c.t0 + c.Phase) % c.Period
		if t < 0 {
			t += c.Period
		}
		on := false
		for _, w := range c.On {
			if t >= w[0] && t < w[1] {
				on = true
				break
			}
		}
		trapSetGroup(c.Group, on)
	}
	for _, m := range trapMovers {
		if m.Armed && !m.done {
			trapMoverStep(m)
		}
	}
	for _, name := range trapOrder {
		trapZoneStep(trapZones[name])
	}
	for _, w := range trapWatches {
		if w.done {
			continue
		}
		if w.obj == nil {
			w.obj = ns.Object(w.Obj)
			if w.obj != nil {
				w.found = true
			} else if w.found {
				w.done = true
				trapFire(w.Acts)
			}
			continue
		}
		if w.obj.GetHolder() != nil {
			w.done = true
			trapCaller = w.obj.GetHolder()
			trapFire(w.Acts)
		}
	}
	for _, s := range trapSwitches {
		if s.obj == nil {
			s.obj = ns.Object(s.Obj)
			if s.obj == nil {
				continue
			}
		}
		e := s.obj.IsEnabled()
		if s.seen && e != s.last {
			trapFire(s.Acts)
		}
		s.last, s.seen = e, true
	}
}

func trapFire(acts []trapAct) {
	for _, a := range acts {
		if a.Delay > 0 {
			trapQueue = append(trapQueue, trapPending{at: trapFrame + a.Delay, act: a})
		} else {
			trapDo(a)
		}
	}
}

func trapDo(a trapAct) {
	switch a.Kind {
	case "on":
		trapSetGroup(a.Target, true)
	case "off":
		trapSetGroup(a.Target, false)
	case "toggle":
		if g := trapGroups[a.Target]; g != nil {
			g.setOn(!g.on)
		}
	case "pulse":
		trapSetGroup(a.Target, true)
		trapQueue = append(trapQueue, trapPending{at: trapFrame + a.Frames, act: trapAct{Kind: "off", Target: a.Target}})
	case "arm", "disarm":
		armed := a.Kind == "arm"
		if c := trapClocks[a.Target]; c != nil {
			if armed && !c.Armed {
				c.t0 = trapFrame
			}
			c.Armed = armed
			if !armed {
				trapSetGroup(c.Group, false)
			}
		}
		if m := trapMovers[a.Target]; m != nil {
			m.Armed = armed
		}
		if z := trapZones[a.Target]; z != nil {
			z.Armed = armed
		}
	case "cast":
		ns.CastSpell(spell.Spell(a.Spell), a.From, a.To)
	case "cast_at_caller": // a statue's death ray at whoever pressed the plate, where he stood
		if trapCaller != nil {
			ns.CastSpell(spell.Spell(a.Spell), a.From, trapCaller.Pos())
		}
	case "walls_open", "walls_close":
		for _, w := range a.Walls {
			if wl := ns.Wall(w[0], w[1]); wl != nil {
				wl.Enable(a.Kind == "walls_close")
			}
		}
	case "wake":
		if g := trapGroups[a.Target]; g != nil {
			g.resolve()
			for _, o := range g.objs {
				if o.CurrentHealth() > 0 {
					o.Freeze(false)
					o.Hunt()
				}
			}
		}
	case "say":
		ns.PrintStrToAll(a.Text)
	case "log": // for tests: a line in the game's log
		println("traps: " + a.Text)
	case "sound": // a sound at a point (Text: the audio name, From: where)
		ns.AudioEvent(audio.Name(a.Text), a.From)
	case "restart": // a clock starts its period again from now (a station's run begins)
		if c := trapClocks[a.Target]; c != nil {
			c.t0 = trapFrame
		}
	default:
		if f := trapExt[a.Kind]; f != nil {
			f(a)
		} else {
			println("traps: unknown action " + a.Kind)
		}
	case "reset":
		if m := trapMovers[a.Target]; m != nil {
			m.seg, m.along, m.dir, m.wait, m.done = 0, 0, 1, 0, false
			trapMoverPlace(m)
		}
		if z := trapZones[a.Target]; z != nil {
			z.fired, z.in, z.cool = false, false, 0
		}
	}
}

// ---- movers -----------------------------------------------------------------------------------------------------

func trapMoverResolve(m *trapMover) {
	if m.objs != nil {
		return
	}
	for k, n := range m.Objs {
		o := ns.Object(n)
		if o == nil {
			continue
		}
		m.objs = append(m.objs, o)
		p := o.Pos()
		if k == 0 {
			m.offs = append(m.offs, ns.Ptf(0, 0))
		} else {
			f := m.objs[0].Pos()
			m.offs = append(m.offs, ns.Ptf(p.X-f.X, p.Y-f.Y))
		}
	}
	trapMoverPlace(m)
}

func trapMoverPoint(m *trapMover) ns.Pointf {
	a := m.Path[m.seg]
	b := m.Path[(m.seg+1)%len(m.Path)]
	L := trapDist(a, b)
	if L <= 0 {
		return a
	}
	t := m.along / L
	return ns.Ptf(a.X+(b.X-a.X)*t, a.Y+(b.Y-a.Y)*t)
}

func trapMoverPlace(m *trapMover) {
	if len(m.objs) == 0 || len(m.Path) < 2 {
		return
	}
	p := trapMoverPoint(m)
	for k, o := range m.objs {
		o.SetPos(ns.Ptf(p.X+m.offs[k].X, p.Y+m.offs[k].Y))
	}
}

func trapMoverStep(m *trapMover) {
	if len(m.objs) == 0 || len(m.Path) < 2 {
		return
	}
	if m.wait > 0 {
		m.wait--
		return
	}
	n := len(m.Path)
	last := n - 1
	if m.Mode == "loop" {
		last = n
	}
	left := m.Speed
	for left > 0 {
		a := m.Path[m.seg]
		b := m.Path[(m.seg+1)%n]
		L := trapDist(a, b)
		if m.dir > 0 {
			if m.along+left < L {
				m.along += left
				left = 0
				break
			}
			left -= L - m.along
			m.seg++
			m.along = 0
			if m.seg >= last {
				switch m.Mode {
				case "loop":
					m.seg = 0
					m.wait = m.Pause
				case "once":
					m.seg, m.along, m.done = last-1, trapDist(m.Path[last-1], m.Path[last]), true
				default: // pingpong: back from the far end
					m.seg = last - 1
					m.along = trapDist(m.Path[last-1], m.Path[last])
					m.dir = -1
					m.wait = m.Pause
				}
				left = 0
			}
		} else {
			if m.along-left > 0 {
				m.along -= left
				left = 0
				break
			}
			left -= m.along
			if m.seg == 0 {
				m.along = 0
				m.dir = 1
				m.wait = m.Pause
				left = 0
				break
			}
			m.seg--
			m.along = trapDist(m.Path[m.seg], m.Path[m.seg+1])
		}
	}
	trapMoverPlace(m)
}

func trapDist(a, b ns.Pointf) float32 {
	dx, dy := b.X-a.X, b.Y-a.Y
	return float32(sqrt32(dx*dx + dy*dy))
}

func sqrt32(v float32) float32 {
	if v <= 0 {
		return 0
	}
	x := v
	for i := 0; i < 20; i++ {
		x = 0.5 * (x + v/x)
	}
	return x
}

// ---- zones ------------------------------------------------------------------------------------------------------

func trapInZone(z *trapZone, p ns.Pointf) bool {
	dx, dy := p.X-z.C.X, p.Y-z.C.Y
	switch z.Shape {
	case "circle":
		return dx*dx+dy*dy <= z.R*z.R
	case "box":
		return dx >= -z.R && dx <= z.R && dy >= -z.H && dy <= z.H
	default: // diamond: a thing.bin BOX extent (|dx| + |dy| < R)
		if dx < 0 {
			dx = -dx
		}
		if dy < 0 {
			dy = -dy
		}
		return dx+dy <= z.R
	}
}

func trapZoneOccupied(z *trapZone) bool {
	for _, pl := range ns.Players() {
		u := pl.Unit()
		if u == nil || u.CurrentHealth() <= 0 || !trapInZone(z, u.Pos()) {
			continue
		}
		if z.Jump && uint32(u.Flags())&0x4000 != 0 { // AIRBORNE: in a jump
			continue
		}
		z.who = u
		return true
	}
	if z.Who == "any" && trapFrame%3 == 0 {
		r := z.R
		if z.H > r {
			r = z.H
		}
		for _, o := range ns.FindAllObjects(ns.InCirclef{Center: z.C, R: float64(r + 4)}) {
			if o.CurrentHealth() > 0 && o.MaxHealth() > 0 && trapInZone(z, o.Pos()) {
				z.who = o
				return true
			}
		}
	}
	return false
}

func trapZoneStep(z *trapZone) {
	if z == nil || !z.Armed {
		return
	}
	if z.cool > 0 {
		z.cool--
	}
	occ := trapZoneOccupied(z)
	if z.Who == "any" && trapFrame%3 != 0 && !occ {
		occ = z.in // creatures are checked every third frame: hold the last answer between checks
	}
	if occ && !z.in {
		z.in = true
		if (!z.Once || !z.fired) && z.cool == 0 {
			z.fired = true
			trapCaller = z.who
			if z.Toggle && z.state {
				z.state = false
				trapFire(z.Release)
			} else {
				z.state = true
				trapFire(z.Acts)
			}
		}
	} else if !occ && z.in {
		z.in = false
		z.cool = z.Rearm
		if !z.Toggle {
			trapFire(z.Release)
		}
	}
}
