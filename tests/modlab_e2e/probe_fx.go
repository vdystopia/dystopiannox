package PKG

// QA1 FX gallery probe (tests/modlab_e2e/lab.py play probe_fx.go): draws every ray effect NoxScript offers, side by
// side, west to east (50 px apart, in the order of fxList), beside the player, for the screenshots. OpenNox alpha13
// drew CHARM as green sparks, LIGHTNING as blue ones, DEATH_RAY a magenta beam, and nothing for GREEN_BOLT.

import (
	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/effect"
)

var fxF int

var fxList = []effect.Effect{effect.LIGHTNING, effect.ENERGY_BOLT, effect.GREEN_BOLT, effect.DRAIN_MANA, effect.CHARM,
	effect.GREATER_HEAL, effect.DEATH_RAY, effect.SENTRY_RAY, effect.PLASMA, effect.VAMPIRISM}

func init() { ns.OnFrame(fxFrame) }

func fxFrame() {
	h := ns.GetHost()
	if h == nil || !modStarted || ns.Object("W3_QuakeHammer") == nil {
		return
	}
	fxF++
	if fxF == 30 {
		h.SetPos(ns.Ptf(3680, 3910))
		h.Freeze(true)
		println("fxprobe: start; order west to east:", len(fxList))
	}
	if fxF > 30 && fxF%8 == 0 {
		p := h.Pos()
		for i, fx := range fxList {
			x := p.X - 225 + 50*float32(i)
			ns.Effect(fx, ns.Ptf(x, p.Y-120), ns.Ptf(x+20, p.Y+80))
		}
	}
}
