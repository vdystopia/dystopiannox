package PKG

// Sentry beams (dystopiannox mapgen/kit/trapkit/sentries.py): the tell before a beam comes on. A globe that is off
// is not drawn, so a switched beam warns with a sound: SentryCue (called from traps_config.go after StartTraps)
// plays an audio name at a point on given frames of a clock's period, while that clock runs. Westwood's sentries
// warn the same way, with GenerateTick countdowns and machinery sounds (rules/traps/WESTWOOD_SCRIPTS.md 3).

import (
	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/audio"
)

type sentryCue struct {
	clock string
	sound string
	p     ns.Pointf
	at    []int
}

var (
	sentryCues  []sentryCue
	sentryCueOn bool
)

// SentryCue plays `sound` at (x, y) whenever the clock named `clock` reaches one of the frames `at` of its period.
func SentryCue(clock, sound string, x, y float32, at ...int) {
	sentryCues = append(sentryCues, sentryCue{clock: clock, sound: sound, p: ns.Ptf(x, y), at: at})
	if !sentryCueOn {
		sentryCueOn = true
		ns.OnFrame(sentryCueTick)
	}
}

func sentryCueTick() {
	for _, q := range sentryCues {
		c := trapClocks[q.clock]
		if c == nil || !c.Armed || c.Period <= 0 {
			continue
		}
		t := (trapFrame - c.t0 + c.Phase) % c.Period
		if t < 0 {
			t += c.Period
		}
		for _, f := range q.at {
			if f == t {
				ns.AudioEvent(audio.Name(q.sound), q.p)
			}
		}
	}
}
