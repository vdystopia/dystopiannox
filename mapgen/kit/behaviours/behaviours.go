package PKG

// Behaviour sets for the creatures of generated maps (dystopiannox mapgen/kit/npcs.py writes this file, with the map's
// package name, into the map's folder, beside a config.go that lists who does what). OpenNox runs every .go file in a
// map's folder as the map's script (NoxScript 4, github.com/noxworld-dev/noxscript/ns/v4).
//
// Westwood moves its creatures the same way (rules/NPCS.md): Move along waypoints, Wander, Guard, Hunt, Follow and
// GoBackHome from script callbacks (enemy sighted, is hit, end of waypoint, lost enemy, death).
//
// The sets:
//   Sentry:     guards its post facing out; on sighting an enemy it calls out and rouses the allies listed, who hunt;
//               when the enemy is lost it walks back to its post.
//   Patrol:     walks a route of waypoints in turn (and back, or round), pausing at each; fights what it meets and
//               takes up the route again when the enemy is lost.
//   Pack:       a leader wanders, the others follow it; when any of them sees or is hit by an enemy, all hunt; when
//               the leader dies, the rest flee.
//   Skittish:   wanders; when hit it flees from its attacker for a few seconds, then wanders again.
//   Ambush:     a group waits unseen (disabled) until the player comes within reach, then appears and attacks.
//   Townsfolk:  walks between the town's named spots, lingers, and turns to look at the player passing by.
//   Villager:   a townsfolk who keeps an eye out: when a hostile creature comes near, runs for its home doorstep and
//               waits there until the danger has passed, then takes up its rounds again.

import (
	"strings"

	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/opennox-lib/object"
)

func find(name string) ns.Obj {
	return ns.Object(name)
}

func dist2(a, b ns.Pointf) float32 {
	dx, dy := a.X-b.X, a.Y-b.Y
	return dx*dx + dy*dy
}

// ---- Sentry ------------------------------------------------------------------------------------------------------

func Sentry(name string, faceX, faceY float32, rouse []string, shout string) {
	o := find(name)
	if o == nil {
		return
	}
	post := o.Pos()
	face := ns.Ptf(faceX, faceY)
	o.Guard(post, face, 160)
	alerted := false
	o.OnEvent(ns.EventEnemySighted, func() {
		if alerted {
			return
		}
		alerted = true
		if shout != "" {
			o.ChatStrTimer(shout, ns.Seconds(2))
		}
		for _, r := range rouse {
			if a := find(r); a != nil {
				a.AggressionLevel(0.83)
				a.Hunt()
			}
		}
	})
	o.OnEvent(ns.EventLostEnemy, func() {
		alerted = false
		o.WalkTo(post)
		ns.NewTimer(ns.Seconds(4), func() { o.Guard(post, face, 160) })
	})
}

// ---- Patrol ------------------------------------------------------------------------------------------------------

func Patrol(name string, route []string, pauseSec float64, loop bool) {
	o := find(name)
	if o == nil {
		return
	}
	var wps []ns.WaypointObj
	for _, r := range route {
		if w := ns.Waypoint(r); w != nil {
			wps = append(wps, w)
		}
	}
	if len(wps) == 0 {
		o.Wander()
		return
	}
	i, step := 0, 1
	walk := func() { o.Move(wps[i]) }
	o.OnEvent(ns.EventEndOfWaypoint, func() {
		if len(wps) > 1 {
			if loop {
				i = (i + 1) % len(wps)
			} else {
				if i+step < 0 || i+step >= len(wps) {
					step = -step
				}
				i += step
			}
		}
		o.Pause(ns.Seconds(pauseSec))
		ns.NewTimer(ns.Seconds(pauseSec+0.5), walk)
	})
	o.OnEvent(ns.EventLostEnemy, func() { ns.NewTimer(ns.Seconds(2), walk) })
	walk()
}

// ---- Pack --------------------------------------------------------------------------------------------------------

func Pack(leader string, members []string) {
	l := find(leader)
	if l == nil {
		return
	}
	var ms []ns.Obj
	for _, m := range members {
		if o := find(m); o != nil {
			ms = append(ms, o)
		}
	}
	l.Wander()
	for _, o := range ms {
		o.Follow(l)
	}
	hunting := false
	rouse := func() {
		if hunting {
			return
		}
		hunting = true
		l.Hunt()
		for _, o := range ms {
			o.Hunt()
		}
	}
	calm := func() {
		hunting = false
		l.Wander()
		for _, o := range ms {
			o.Follow(l)
		}
	}
	for _, o := range append([]ns.Obj{l}, ms...) {
		o.OnEvent(ns.EventEnemySighted, rouse)
		o.OnEvent(ns.EventIsHit, rouse)
	}
	l.OnEvent(ns.EventLostEnemy, func() { ns.NewTimer(ns.Seconds(5), calm) })
	l.OnEvent(ns.EventDeath, func() {
		h := ns.GetHost()
		for _, o := range ms {
			if h != nil {
				o.Flee(h, ns.Seconds(8))
			} else {
				o.Wander()
			}
		}
	})
}

// ---- Skittish ----------------------------------------------------------------------------------------------------

func Skittish(name string, fleeSec float64) {
	o := find(name)
	if o == nil {
		return
	}
	o.Wander()
	o.OnEvent(ns.EventIsHit, func() {
		if h := ns.GetHost(); h != nil {
			o.Flee(h, ns.Seconds(fleeSec))
		}
		ns.NewTimer(ns.Seconds(fleeSec+1), func() { o.Wander() })
	})
}

// ---- Ambush ------------------------------------------------------------------------------------------------------

func Ambush(names []string, x, y, reach float32) {
	var group []ns.Obj
	for _, n := range names {
		if o := find(n); o != nil {
			o.Enable(false)
			group = append(group, o)
		}
	}
	if len(group) == 0 {
		return
	}
	spot := ns.Ptf(x, y)
	sprung := false
	ns.OnEachFrame(10, func() {
		if sprung {
			return
		}
		h := ns.GetHost()
		if h == nil || dist2(h.Pos(), spot) > reach*reach {
			return
		}
		sprung = true
		for _, o := range group {
			o.Enable(true)
			o.AggressionLevel(0.83)
			o.Attack(h)
		}
	})
}

// ---- Townsfolk ---------------------------------------------------------------------------------------------------

func Townsfolk(name string, spots []string, lingerSec float64) {
	o := find(name)
	if o == nil {
		return
	}
	var wps []ns.WaypointObj
	for _, s := range spots {
		if w := ns.Waypoint(s); w != nil {
			wps = append(wps, w)
		}
	}
	if len(wps) == 0 {
		o.Wander()
		return
	}
	next := func() { o.Move(wps[ns.Random(0, len(wps)-1)]) }
	o.OnEvent(ns.EventEndOfWaypoint, func() {
		if h := ns.GetHost(); h != nil && dist2(h.Pos(), o.Pos()) < 120*120 {
			o.LookAtObject(h)
		}
		ns.NewTimer(ns.Seconds(lingerSec+float64(ns.Random(0, 4))), next)
	})
	next()
}

// ---- Villager ----------------------------------------------------------------------------------------------------

// friendlyType: the town's own people, who are no threat to a villager.
func friendlyType(t string) bool {
	return t == "Maiden" || t == "NPC" || t == "AirshipCaptain" || strings.HasPrefix(t, "Shopkeeper") ||
		strings.HasPrefix(t, "Wounded")
}

// Villager walks between the town's spots like Townsfolk; twice a second it looks round, and when a living, hostile
// creature is within fearR pixels it runs to its home waypoint (a doorstep) and stays there, out of the way, until
// none has been near for a while.
func Villager(name string, spots []string, lingerSec float64, home string, fearR float64) {
	o := find(name)
	if o == nil {
		return
	}
	var wps []ns.WaypointObj
	for _, s := range spots {
		if w := ns.Waypoint(s); w != nil {
			wps = append(wps, w)
		}
	}
	hw := ns.Waypoint(home)
	hiding, calm := false, 0
	next := func() {
		if hiding {
			return
		}
		if len(wps) == 0 {
			o.Wander()
			return
		}
		o.Move(wps[ns.Random(0, len(wps)-1)])
	}
	o.OnEvent(ns.EventEndOfWaypoint, func() {
		if hiding {
			o.Idle()
			return
		}
		if h := ns.GetHost(); h != nil && dist2(h.Pos(), o.Pos()) < 120*120 {
			o.LookAtObject(h)
		}
		ns.NewTimer(ns.Seconds(lingerSec+float64(ns.Random(0, 4))), next)
	})
	threat := func() ns.Obj {
		return ns.FindClosestObject(o, ns.HasClass(object.ClassMonster), ns.InCirclef{Center: o, R: fearR},
			ns.ObjCondFunc(func(x ns.Obj) bool {
				return x != o && x.IsEnabled() && x.CurrentHealth() > 0 && !friendlyType(x.Type().Name())
			}))
	}
	ns.OnEachFrame(15, func() {
		if o.CurrentHealth() <= 0 {
			return
		}
		if t := threat(); t != nil {
			calm = 0
			if !hiding && hw != nil {
				hiding = true
				o.Move(hw)
			}
			return
		}
		if hiding {
			calm++
			if calm >= 16 { // eight quiet seconds: back to the rounds
				hiding, calm = false, 0
				next()
			}
		}
	})
	next()
}

// ---- Self-check --------------------------------------------------------------------------------------------------

// Diagnose prints, once the map has loaded, how many of the named creatures and waypoints the scripts can find
// (the server log shows it even with no player in the game, when MapInitialize has not fired yet).
func Diagnose(objs []string, wps []string) {
	done := false
	ns.OnEachFrame(15, func() {
		if done {
			return
		}
		done = true
		fo, fw := 0, 0
		for _, n := range objs {
			if ns.Object(n) != nil {
				fo++
			}
		}
		for _, n := range wps {
			if ns.Waypoint(n) != nil {
				fw++
			}
		}
		println("NPC behaviours self-check: creatures", fo, "of", len(objs), "- waypoints", fw, "of", len(wps))
	})
}
