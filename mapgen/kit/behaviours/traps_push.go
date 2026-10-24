package PKG

// Moving blocks, pushers, force fields and bumpers for the trap kinds "block" and "push" (dystopiannox
// mapgen/kit/trapkit/blocks.py and pushers.py; the numbers behind them: rules/TRAPS.md, rules/traps/ENGINE.md 5, 6, 14).
//
// traps.go moves the blocks (its movers: SetPos each frame, which shoves a player along and lets a spike block hurt
// him 1 HP a frame). This file adds, every frame:
//   - block events (TrapPushMover): a mover's blocks set off (SpikeBlockMove) and land at the far end of their stroke
//     (HammerMissing, a small shake, and Crush damage to whoever is pinned against a block there: the game's own
//     contact damage is only 1 HP a frame); a phase delay (the mover is armed Delay frames after the start, so rows
//     of blocks run as a wave); a dwell at the start of the path (HomeWait) that differs from the far one (the
//     mover's Pause), so a pusher can rest long at home and slam briefly; Impact damage to a player the moving
//     blocks strike (once a contact: a ram's blow, on top of the game's 1 HP a frame);
//   - force fields (TrapPushField): a box of floor that adds a force to every creature standing in it each frame (a
//     conveyor belt; a gust of wind on a clock). A jumping player rides over it: the game sets a jumper's force
//     itself every frame of the jump (object_update.go, PlayerState12), so the push is lost while airborne;
//   - actions: "push_bump" (a bumper throws its toucher away from its centre: From, force Frames),
//     "push_force_on" and "push_force_off" (a field), "push_retract" (a mover runs back to the start of its path at
//     Frames/10 px a frame and stops there, armed again by its next "arm"), "push_crush" (whoever touches the mover
//     Target's blocks now takes Frames damage).

import (
	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/audio"
	"github.com/noxworld-dev/noxscript/ns/v4/damage"
	"github.com/noxworld-dev/noxscript/ns/v4/effect"
)

type pushMover struct {
	Mover    string
	Crush    int  // damage to whoever touches one of its blocks when the stroke ends at the far end
	Delay    int  // frames after the start before the mover is armed (a phase offset)
	HomeWait int  // frames at the start of the path (0: the mover's own Pause)
	Sound    bool // SpikeBlockMove when it sets off, HammerMissing and a shake when it lands
	Impact   int  // damage to a player a moving block of it strikes (once until he is clear of it again)
	m        *trapMover
	touch    map[int]bool
	lastDir  int
	lastDone bool
	lastPos  ns.Pointf
	moving   bool
	seen     bool
	speed    float32 // the mover's own speed, kept while it retracts
	back     bool
}

type pushField struct {
	Name   string
	C      ns.Pointf // the centre of the box
	U      ns.Pointf // unit vector along its length
	HL, HW float32   // half length (along U) and half width
	F      ns.Pointf // the force added each frame
	Period int       // 0: always on while armed; otherwise on in the windows On of each period (a gust)
	On     [][2]int
	Phase  int
	Armed  bool
	Sound  string // played at C when it comes on (a gust), and every Tick frames while on (0: once)
	Tick   int
	t0     int
	was    bool
	ticks  int
}

var (
	pushMovers   []*pushMover
	pushMoverBy  = map[string]*pushMover{}
	pushFields    []*pushField
	pushFieldBy   = map[string]*pushField{}
	pushTicking bool
)

// TrapPushMover watches a mover of traps.go (call after StartTraps: traps_config.go's extra start lines).
func TrapPushMover(p pushMover) {
	pp := p
	pp.m = trapMovers[p.Mover]
	if pp.m != nil {
		pp.speed = pp.m.Speed
		pp.lastDir = pp.m.dir
	}
	pushMovers = append(pushMovers, &pp)
	pushMoverBy[p.Mover] = &pp
	if p.Delay > 0 {
		trapQueue = append(trapQueue, trapPending{at: trapFrame + p.Delay, act: trapAct{Kind: "arm", Target: p.Mover}})
	}
	pushStart()
}

// TrapPushField adds a force field (call after StartTraps).
func TrapPushField(f pushField) {
	ff := f
	ff.t0 = trapFrame
	pushFields = append(pushFields, &ff)
	pushFieldBy[f.Name] = &ff
	pushStart()
}

func pushStart() {
	if pushTicking {
		return
	}
	pushTicking = true
	ns.OnFrame(pushTick)
}

func init() {
	trapExt["push_bump"] = func(a trapAct) {
		if trapCaller == nil || trapCaller.CurrentHealth() <= 0 {
			return
		}
		trapCaller.PushTo(a.From, float32(a.Frames))
		ns.AudioEvent(audio.BallBounce, a.From)
		ns.Effect(effect.WHITE_FLASH, a.From, a.From)
	}
	trapExt["push_force_on"] = func(a trapAct) {
		if f := pushFieldBy[a.Target]; f != nil {
			if !f.Armed {
				f.t0 = trapFrame
			}
			f.Armed = true
		}
	}
	trapExt["push_force_off"] = func(a trapAct) {
		if f := pushFieldBy[a.Target]; f != nil {
			f.Armed = false
		}
	}
	trapExt["push_retract"] = func(a trapAct) {
		m := trapMovers[a.Target]
		if m == nil {
			return
		}
		p := pushMoverBy[a.Target]
		if p == nil {
			p = &pushMover{Mover: a.Target, m: m, speed: m.Speed, lastDir: m.dir}
			pushMovers = append(pushMovers, p)
			pushMoverBy[a.Target] = p
			pushStart()
		}
		if !p.back {
			p.speed = m.Speed
		}
		if a.Frames > 0 {
			m.Speed = float32(a.Frames) / 10
		}
		m.dir, m.wait, m.done, m.Armed = -1, 0, false, true
		p.back, p.lastDir = true, -1
	}
	trapExt["push_crush"] = func(a trapAct) {
		if m := trapMovers[a.Target]; m != nil {
			pushCrush(m, a.Frames)
		}
	}
}

func pushTick() {
	if !trapsOn {
		return
	}
	for _, p := range pushMovers {
		p.step()
	}
	for _, f := range pushFields {
		f.step()
	}
}

func (p *pushMover) step() {
	m := p.m
	if m == nil {
		if m = trapMovers[p.Mover]; m == nil {
			return
		}
		p.m, p.speed = m, m.Speed
	}
	if len(m.objs) == 0 {
		return
	}
	pos := m.objs[0].Pos()
	moved := p.seen && trapDist(pos, p.lastPos) > 0.5
	if p.back && m.dir > 0 { // home again after a retract: stop there until the next "arm"
		m.Armed, m.Speed, m.wait = false, p.speed, 0
		p.back = false
	} else if p.lastDir < 0 && m.dir > 0 && p.HomeWait > 0 && m.Mode == "pingpong" {
		m.wait = p.HomeWait
	}
	if p.Sound && moved && !p.moving {
		ns.AudioEvent(audio.SpikeBlockMove, pos)
	}
	if p.Impact > 0 {
		p.strike(m, moved)
	}
	if (p.lastDir > 0 && m.dir < 0 && !p.back) || (!p.lastDone && m.done) {
		if p.Sound {
			ns.AudioEvent(audio.HammerMissing, pos)
			ns.Effect(effect.JIGGLE, pos, ns.Ptf(3, 0))
		}
		if p.Crush > 0 {
			pushCrush(m, p.Crush)
		}
	}
	p.lastDir, p.lastDone, p.lastPos, p.moving, p.seen = m.dir, m.done, pos, moved, true
}

// strike: a player newly touching one of the mover's blocks while it moves takes the Impact damage.
func (p *pushMover) strike(m *trapMover, moved bool) {
	if p.touch == nil {
		p.touch = map[int]bool{}
	}
	for k, pl := range ns.Players() {
		u := pl.Unit()
		if u == nil || u.CurrentHealth() <= 0 {
			p.touch[k] = false
			continue
		}
		q := u.Pos()
		on := false
		for _, o := range m.objs {
			c := o.Pos()
			dx, dy := q.X-c.X, q.Y-c.Y
			if dx < 0 {
				dx = -dx
			}
			if dy < 0 {
				dy = -dy
			}
			if dx+dy < 56 {
				on = true
				break
			}
		}
		if on && moved && !p.touch[k] {
			u.Damage(nil, p.Impact, damage.IMPALE)
		}
		p.touch[k] = on
	}
}

// pushCrush hurts every creature touching one of the mover's blocks (a 60x60 block is a diamond |dx|+|dy| < 42.4;
// a creature of radius 10 pressed against it has its centre within ~56 of it in that measure).
func pushCrush(m *trapMover, dmg int) {
	if dmg <= 0 {
		return
	}
	for _, o := range m.objs {
		c := o.Pos()
		for _, v := range ns.FindAllObjects(ns.InCirclef{Center: c, R: 64}) {
			if v.CurrentHealth() <= 0 || v.MaxHealth() <= 0 {
				continue
			}
			q := v.Pos()
			dx, dy := q.X-c.X, q.Y-c.Y
			if dx < 0 {
				dx = -dx
			}
			if dy < 0 {
				dy = -dy
			}
			if dx+dy < 54 {
				v.Damage(nil, dmg, damage.CRUSH)
			}
		}
	}
}

func (f *pushField) step() {
	if !f.Armed {
		f.was = false
		return
	}
	on := true
	if f.Period > 0 {
		t := (trapFrame - f.t0 + f.Phase) % f.Period
		if t < 0 {
			t += f.Period
		}
		on = false
		for _, w := range f.On {
			if t >= w[0] && t < w[1] {
				on = true
				break
			}
		}
	}
	if on && f.Sound != "" {
		if !f.was || (f.Tick > 0 && f.ticks >= f.Tick) {
			ns.AudioEvent(audio.Name(f.Sound), f.C)
			f.ticks = 0
		}
		f.ticks++
	}
	f.was = on
	if !on {
		return
	}
	mag := sqrt32(f.F.X*f.F.X + f.F.Y*f.F.Y)
	if mag <= 0 {
		return
	}
	ux, uy := f.F.X/mag, f.F.Y/mag
	r := sqrt32(f.HL*f.HL + f.HW*f.HW)
	for _, v := range ns.FindAllObjects(ns.InCirclef{Center: f.C, R: float64(r + 2)}) {
		if v.CurrentHealth() <= 0 || v.MaxHealth() <= 0 {
			continue
		}
		q := v.Pos()
		dx, dy := q.X-f.C.X, q.Y-f.C.Y
		al := dx*f.U.X + dy*f.U.Y
		ac := -dx*f.U.Y + dy*f.U.X
		if al < -f.HL || al > f.HL || ac < -f.HW || ac > f.HW {
			continue
		}
		if uint32(v.Flags())&0x4000 != 0 { // AIRBORNE: a jump rides over it
			continue
		}
		v.PushTo(ns.Ptf(q.X-ux*20, q.Y-uy*20), mag)
	}
}
