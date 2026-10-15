package bosslab

// The BossLab tour, for a real player in OpenNox's e2e mode (tests/bosslab_e2e/run.py): the hero (given 4000 health)
// is set down 230 px from each boss in turn, inside its arena, for 14 s; at 6 s the boss is brought to 55% health
// (its first phase); at the end the probe logs what the boss did and what the hero lost, and the boss is slain.

import (
	"fmt"

	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/damage"
)

const prPer = 420

// the first boss toured (run.py --from)
const prFirst = 0

var (
	prFrames    int
	prSpareHome []ns.Pointf
)

func init() {
	ns.OnFrame(prFrame)
}

func prFrame() {
	h := ns.GetHost()
	if h == nil || !bsStarted {
		return
	}
	prFrames++
	if prFrames == 30 {
		h.SetMaxHealth(4000)
		h.SetHealth(4000)
		println(fmt.Sprintf("probe: host %d/%d", h.CurrentHealth(), h.MaxHealth()))
	}
	if prFrames == 35 { // a group photo: the first spare of each boss (frozen) in two rows before the hero
		hp := h.Pos()
		for i, b := range bsBosses {
			if s := ns.Object(b.names[1]); s != nil {
				prSpareHome = append(prSpareHome, s.Pos())
				along, across := float32(110+(i%5)*65), float32(-55+(i/5)*110) // along the hall (east), across it
				s.SetPos(ns.Ptf(hp.X+0.707*(along+across), hp.Y+0.707*(along-across)))
				s.LookAtObject(h)
			}
		}
		println("probe: parade")
	}
	if prFrames == 900 {
		for i, b := range bsBosses {
			if s := ns.Object(b.names[1]); s != nil && i < len(prSpareHome) {
				s.SetPos(prSpareHome[i])
			}
		}
	}
	if prFrames < 930 {
		return
	}
	k, t := (prFrames-930)/prPer+prFirst, (prFrames-930)%prPer
	if k >= len(bsBosses) {
		if t == 0 && k == len(bsBosses) {
			println("probe: done")
		}
		return
	}
	b := bsBosses[k]
	switch t {
	case 0: // down 230 px from the boss toward the hall (NE arenas have x - y > 0 in their uv, SW < 0)
		hx, hy := b.home.X, b.home.Y
		s := float32(1)
		if hx-hy < 0 {
			s = -1
		}
		at := ns.Ptf(hx-s*163, hy+s*163)
		h.SetPos(at)
		h.SetHealth(4000)
		println(fmt.Sprintf("probe: %s start (%s) frame %d", b.kind, b.label, ns.Frame()))
	case 180:
		if b.o != nil {
			b.o.SetHealth(b.hp * 55 / 100)
		}
	case prPer - 10:
		hp := "dead"
		if b.o != nil {
			hp = fmt.Sprintf("%d/%d", b.o.CurrentHealth(), b.o.MaxHealth())
		}
		println(fmt.Sprintf("probe: %s end: hero lost %d, boss %s, did %v", b.kind, 4000-h.CurrentHealth(), hp, b.n))
		if b.o != nil {
			b.o.SetHealth(1)
			b.o.Damage(nil, 200, damage.BLADE)
		}
	}
}
