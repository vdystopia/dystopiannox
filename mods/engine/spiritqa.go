package spiritqa

// QA map script for the Spirit class engine mod (see SPIRIT.md, "Verification").
// To use: make a folder maps\SpiritQA, copy maps\estate\Estate.map into it as SpiritQA.map, put this file beside it,
// then run (from C:\GOG Games\Nox):
//   opennox-spirit-hd.exe -swindow -config opennox-test.yml -autosrv -autoexec "load SpiritQA" -autoclass conjurer -port 18600
// and again with "-spirit off" added. The numbers appear in logs\opennox.log as "[console]: spiritqa: ...".
// Delete maps\SpiritQA afterwards.

import (
	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/damage"
)

var (
	frames int
	target ns.Obj
)

func logMana(tag string) {
	h := ns.GetHost()
	if h == nil {
		println("spiritqa:", tag, "no host")
		return
	}
	println("spiritqa:", tag, "sec", frames/30, "mana", h.CurrentMana(), "/", h.MaxMana())
}

func init() {
	ns.OnEachFrame(1, func() {
		frames++
		if frames%30 != 0 {
			return
		}
		sec := frames / 30
		h := ns.GetHost()
		if h == nil {
			return
		}
		switch {
		case sec == 3: // passive regeneration from empty for 30 s
			h.SetMana(0)
			logMana("drained")
		case sec > 3 && sec <= 33 && sec%5 == 3:
			logMana("passive")
		case sec == 34: // a paused troll beside the player to hit
			p := h.Pos()
			target = ns.CreateObject("Troll", ns.Ptf(p.X+60, p.Y))
			if target != nil {
				target.Pause(ns.Seconds(60))
			} else {
				println("spiritqa: no troll")
			}
			h.SetMana(0)
			logMana("hit-start")
		case sec >= 35 && sec <= 39 && target != nil: // five physical hits of 10 by the player
			target.Damage(h, 10, damage.BLADE)
			logMana("after-blade10")
		case sec == 40 && target != nil: // one magical hit: no Spirit
			target.Damage(h, 10, damage.FLAME)
			logMana("after-flame10")
		case sec == 41: // a mana obelisk beside the player
			p := h.Pos()
			var ob ns.Obj
			for _, t := range []string{"Obelisk", "InvisibleObelisk", "ObeliskPrimitive", "LOTDObelisk"} {
				if ob = ns.CreateObject(t, ns.Ptf(p.X+25, p.Y+25)); ob != nil {
					println("spiritqa: created", t)
					break
				}
			}
			h.SetMana(0)
			logMana("obelisk-start")
		case sec > 41 && sec <= 47:
			logMana("near-obelisk")
		case sec == 48:
			println("spiritqa: done")
		}
	})
}
