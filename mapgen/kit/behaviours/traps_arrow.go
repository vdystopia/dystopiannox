package PKG

// Arrow traps' own actions (kit/trapkit/arrows.py; shipped with traps.go by kit/traps.py).
//
// A hold row keeps its arrow traps switched on while anyone stands on any of its plates, as Westwood's G_Castle and
// G_LOTD rows do with a counter: +1 on each plate pressed, -1 on each plate released, the traps on while the count
// is above 0. A row is several plates (one a square), and a player stepping from one plate to the next is on both
// for a moment, so a plain on/off per plate would switch the row off under him.
//
//	{Kind: "arrow_hold", Target: group}   a plate of the row pressed
//	{Kind: "arrow_free", Target: group}   a plate of the row released
//
// An enabled ArrowTrap fires at once when it is switched on with someone in front of it, then once a second while
// it still sees him (GAME5.c nox_xxx_updateShootingTrap_54F9A0: switching it on clears its scan and reload timers).

var arrowHolds = map[string]int{}

func init() {
	trapExt["arrow_hold"] = func(a trapAct) {
		arrowHolds[a.Target]++
		if arrowHolds[a.Target] == 1 {
			trapSetGroup(a.Target, true)
		}
	}
	trapExt["arrow_free"] = func(a trapAct) {
		if arrowHolds[a.Target] > 0 {
			arrowHolds[a.Target]--
		}
		if arrowHolds[a.Target] == 0 {
			trapSetGroup(a.Target, false)
		}
	}
}
