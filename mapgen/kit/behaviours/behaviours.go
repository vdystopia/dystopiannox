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
//   Patrol:     walks a route of waypoints in turn (round, or there and back), standing a while at each stop; fights
//               what it meets and takes up the route again when the enemy is lost.
//   Pack:       a leader wanders, the others follow it; when any of them sees or is hit by an enemy, all hunt; when
//               the leader dies, the rest flee.
//   Skittish:   wanders; when hit it flees from its attacker for a few seconds, then wanders again.
//   Ambush:     a group waits unseen (disabled) until the player comes within reach, then appears and attacks.
//   Tour:       a townsperson's day: walks a long route of waypoints round the town in order, along the roads (a
//               waypoint at each bend, three square-on through each doorway), and at each stop (a doorstep, the well,
//               a bench, a garden) stands still for its pause, about twenty seconds, facing what is there or the
//               player passing by; when a hostile creature comes near, runs for its home doorstep and waits there
//               until the danger has passed, then takes up its tour again from home.
//
// Every route walker is looked after by one shared ticker (twice a second): one that has not moved for six seconds
// on a leg is sent on again, and after twelve it skips to the next waypoint, so nobody stands stuck against a wall.

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

// ---- Route walkers (Tour, Patrol) ---------------------------------------------------------------------------------

// walker walks one creature round a route: Move to each waypoint in turn (the waypoints are never linked, so each
// Move ends at its waypoint and the game reports it). A waypoint with a pause is a stop, where it stands for the pause
// (and up to four seconds more) facing its look point; the others are bends and doorway points, passed straight
// through. Every callback is short: a stale timer (one set before the walk was taken over) does nothing.
type walker struct {
	o       ns.Obj
	wps     []ns.WaypointObj
	pause   []float32
	look    []ns.Pointf
	loop    bool
	i, step int
	gen     int  // bumped whenever the walk changes hands
	moving  bool // on a leg, between Move and its end
	held    bool // hiding or fighting: the route waits
	last    ns.Pointf
	still   int // ticker rounds without moving on a leg
	// Tour: running home from danger
	home    ns.WaypointObj
	homeIdx int
	fear    float32
	calm    int
	heldFor int // ticker rounds a patrol has been held by a fight
	k       int // the walker's number, for staggering the threat checks
}

var walkers []*walker
var walkTicks int

func newWalker(name string, route []string, pause []float32, look []float32, loop bool) *walker {
	o := find(name)
	if o == nil {
		return nil
	}
	w := &walker{o: o, loop: loop, step: 1, homeIdx: -1}
	for k, r := range route {
		wp := ns.Waypoint(r)
		if wp == nil {
			continue
		}
		w.wps = append(w.wps, wp)
		p := float32(0)
		if k < len(pause) {
			p = pause[k]
		}
		w.pause = append(w.pause, p)
		lp := ns.Ptf(0, 0)
		if 2*k+1 < len(look) {
			lp = ns.Ptf(look[2*k], look[2*k+1])
		}
		w.look = append(w.look, lp)
	}
	if len(w.wps) == 0 {
		o.Idle() // no route: stand still rather than wander
		return nil
	}
	w.k = len(walkers)
	walkers = append(walkers, w)
	if len(walkers) == 1 {
		ns.OnEachFrame(15, tickWalkers)
	}
	o.OnEvent(ns.EventEndOfWaypoint, w.arrived)
	return w
}

func (w *walker) alive() bool {
	return w.o != nil && w.o.IsEnabled() && w.o.CurrentHealth() > 0
}

func (w *walker) walk() {
	if w.held || !w.alive() {
		return
	}
	w.gen++
	w.moving, w.still, w.last = true, 0, w.o.Pos()
	w.o.Move(w.wps[w.i])
}

func (w *walker) advance() {
	n := len(w.wps)
	if n < 2 {
		return
	}
	if w.loop {
		w.i = (w.i + 1) % n
		return
	}
	if w.i+w.step < 0 || w.i+w.step >= n {
		w.step = -w.step
	}
	w.i += w.step
}

// later runs f after d unless the walk has changed hands meanwhile.
func (w *walker) later(d ns.Duration, f func()) {
	g := w.gen
	ns.NewTimer(d, func() {
		if g == w.gen {
			f()
		}
	})
}

func (w *walker) next() {
	w.advance()
	w.walk()
}

func (w *walker) arrived() {
	if w.held || !w.moving {
		return
	}
	w.moving = false
	p := w.pause[w.i]
	if p <= 0 {
		w.later(ns.Frames(2), w.next)
		return
	}
	if h := ns.GetHost(); h != nil && dist2(h.Pos(), w.o.Pos()) < 120*120 {
		w.o.LookAtObject(h)
	} else if lp := w.look[w.i]; lp.X != 0 || lp.Y != 0 {
		w.o.LookAtObject(lp)
	}
	w.later(ns.Seconds(float64(p)+float64(ns.Random(0, 4))), w.next)
}

// hold suspends the route (a fight, a run for home); resume takes it up again after d.
func (w *walker) hold() {
	w.held, w.moving = true, false
	w.gen++
}

func (w *walker) resume(d ns.Duration) {
	w.held = false
	w.gen++
	w.later(d, w.walk)
}

func (w *walker) threat() ns.Obj {
	o := w.o
	return ns.FindClosestObject(o, ns.HasClass(object.ClassMonster), ns.InCirclef{Center: o, R: float64(w.fear)},
		ns.ObjCondFunc(func(x ns.Obj) bool {
			return x != o && x.IsEnabled() && x.CurrentHealth() > 0 && !friendlyType(x.Type().Name())
		}))
}

// tickWalkers: twice a second, every walker. A walker that has not moved on a leg for six seconds is sent on again,
// and after twelve it skips to the next waypoint; a townsperson looks round once a second for danger.
func tickWalkers() {
	walkTicks++
	for _, w := range walkers {
		if w == nil || !w.alive() {
			continue
		}
		if w.fear > 0 && (walkTicks+w.k)%2 == 0 {
			if t := w.threat(); t != nil {
				w.calm = 0
				if w.home != nil && !w.held {
					w.hold()
					w.o.Move(w.home)
				}
			} else if w.held {
				w.calm++
				if w.calm >= 10 { // ten quiet seconds: back on the tour, from home
					w.calm = 0
					if w.homeIdx >= 0 {
						w.i = w.homeIdx
					}
					w.resume(ns.Frames(2))
				}
			}
		}
		if w.held && w.fear <= 0 {
			// a patrol whose fight never reported its end (the enemy gone some other way): back on its beat
			if w.heldFor++; w.heldFor >= 60 {
				w.heldFor = 0
				w.resume(ns.Frames(2))
			}
			continue
		}
		w.heldFor = 0
		if !w.moving || w.held {
			continue
		}
		p := w.o.Pos()
		if dist2(p, w.last) > 9 {
			w.last, w.still = p, 0
			continue
		}
		w.still++
		if w.still == 12 {
			w.o.Move(w.wps[w.i])
		} else if w.still >= 24 {
			w.next()
		}
	}
}

// friendlyType: the town's own people, who are no threat to a villager.
func friendlyType(t string) bool {
	return t == "Maiden" || t == "NPC" || t == "AirshipCaptain" || strings.HasPrefix(t, "Shopkeeper") ||
		strings.HasPrefix(t, "Wounded")
}

// Tour walks a townsperson round its route (see the walker); pause[k] > 0 makes waypoint k a stop, look holds an
// x, y pair per waypoint to face there. With a home waypoint and fearR > 0, it runs home from hostile creatures.
func Tour(name string, route []string, pause []float32, look []float32, home string, fearR float32) {
	w := newWalker(name, route, pause, look, true)
	if w == nil {
		return
	}
	if home != "" {
		w.home = ns.Waypoint(home)
		for k, wp := range w.wps {
			if w.home != nil && wp == w.home {
				w.homeIdx = k
				break
			}
		}
	}
	w.fear = fearR
	w.walk()
}

// Patrol walks a route of waypoints (round when loop, else there and back), standing pause[k] seconds at each stop
// facing look[k]; it fights what it meets and takes up the route again two seconds after the enemy is lost.
func Patrol(name string, route []string, pause []float32, look []float32, loop bool) {
	w := newWalker(name, route, pause, look, loop)
	if w == nil {
		return
	}
	fight := func() {
		if !w.held {
			w.hold()
		}
	}
	w.o.OnEvent(ns.EventEnemySighted, fight)
	w.o.OnEvent(ns.EventIsHit, fight)
	w.o.OnEvent(ns.EventLostEnemy, func() { w.resume(ns.Seconds(2)) })
	w.walk()
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
