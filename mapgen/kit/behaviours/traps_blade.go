package PKG

// Blades (dystopiannox mapgen/kit/trapkit/blades.py): Westwood's saw that grinds through walls (G_Mines
// "Smash1-9", G_Swamp "BreakRotatingSpikeWall", G_Lava "BreakClearWalls": WallGroupBreak as the blades reach each
// section). The action "blade_break" breaks the breakable walls in Walls (written breakable by the map; others
// ignore it) and plays Text, an audio name, at From: the saw's lever schedules one per wall section, timed to the
// saw's arrival.

import (
	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/audio"
)

func init() {
	trapExt["blade_break"] = func(a trapAct) {
		for _, w := range a.Walls {
			if wl := ns.Wall(w[0], w[1]); wl != nil {
				wl.Destroy()
			}
		}
		if a.Text != "" {
			ns.AudioEvent(audio.Name(a.Text), a.From)
		}
	}
}
