package PKG

// Behaviour sets for the creatures of generated maps (dystopiannox mapgen/kit/npcs.py writes this file, with the map's
// package name, into the map's folder, beside a config.go that lists who does what). OpenNox runs every .go file in a
// map's folder as the map's script (NoxScript 4, github.com/noxworld-dev/noxscript/ns/v4).
//
// Westwood moves its creatures the same way (rules/NPCS.md): Move along waypoints, Wander, Guard, Hunt, Follow and
// GoBackHome from script callbacks (enemy sighted, is hit, end of waypoint, lost enemy, death).
//
// The sets:
//   Sentry:     guards its post facing out; on sighting an enemy it calls out and rouses the allies listed, who come
//               at it from their own sides (spreadOn); when the enemy is lost it walks back to its post.
//   Patrol:     walks a route of waypoints in turn (round, or there and back), standing a while at each stop; fights
//               what it meets and takes up the route again when the enemy is lost.
//   Pack:       the pack lies up spread about its den, each on its own spot; when any of them sees or is hit by an
//               enemy, all come at it from their own sides; when the leader dies, the rest flee.
//   Skittish:   wanders; when hit it flees from its attacker for a few seconds, then wanders again.
//   Ambush:     a group waits unseen (disabled) until the player comes within reach, then appears and attacks from
//               its own sides, archers shooting from where they stand.
//   Journey:    a long walk the story starts (quests.go "walk"): leg by leg along a route laid on the roads and paths
//               and square-on through each doorway, as a tour; at its end the walker stays.
//   Tour:       a townsperson's day: walks a long route of waypoints round the town in order, along the roads (a
//               waypoint at each bend, three square-on through each doorway), and at each stop (a doorstep, the well,
//               a bench, a garden) stands still for its pause, about twenty seconds, facing what is there or the
//               player passing by; when a hostile creature comes near, runs for its home doorstep and waits there
//               until the danger has passed, then takes up its tour again from home.
//
// Every route walker is looked after by one shared ticker (twice a second), which watches whether it gets nearer its
// waypoint: one that does not settles a little aside at a stop, goes on past a bend, or gives way and tries again,
// so nobody stands stuck against a wall or pushes another off a spot.

import (
	"math"
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

// ---- Spreading out -----------------------------------------------------------------------------------------------

// ranged: a creature that fights from afar (it keeps its ground and shoots rather than closing in).
func ranged(o ns.Obj) bool {
	if o == nil {
		return false
	}
	t := o.Type()
	if t == nil {
		return false
	}
	n := t.Name()
	return strings.Contains(n, "Archer") || strings.Contains(n, "Wizard") || strings.Contains(n, "Necromancer") ||
		n == "Lich" || n == "Shade" || n == "EmberDemon" || n == "Beholder"
}

// spreadOn sends a group at target from different sides, so it does not swarm one point (playtest 2026-10-05): each
// fighter first makes for its own point round the target, on the group's side of it and fanned out about fifty
// degrees apart, then attacks; those that fight from afar keep their ground and shoot.
func spreadOn(group []ns.Obj, target ns.Obj) {
	var live []ns.Obj
	var cx, cy float32
	for _, o := range group {
		if o != nil && o.CurrentHealth() > 0 {
			live = append(live, o)
			p := o.Pos()
			cx, cy = cx+p.X, cy+p.Y
		}
	}
	if len(live) == 0 {
		return
	}
	if target == nil {
		for _, o := range live {
			o.Hunt()
		}
		return
	}
	tp := target.Pos()
	n := float32(len(live))
	base := math.Atan2(float64(cy/n-tp.Y), float64(cx/n-tp.X))
	melee := 0
	for _, o := range live {
		if !ranged(o) {
			melee++
		}
	}
	k := 0
	for _, o := range live {
		o.AggressionLevel(0.83)
		if ranged(o) {
			p := o.Pos()
			o.Guard(p, tp, 320)
			continue
		}
		a := base + (float64(k)-float64(melee-1)/2)*0.9
		k++
		o.WalkTo(ns.Ptf(tp.X+float32(70*math.Cos(a)), tp.Y+float32(70*math.Sin(a))))
		f := o
		ns.NewTimer(ns.Seconds(1.0+0.4*float64(k%3)), func() {
			if f == nil || f.CurrentHealth() <= 0 {
				return
			}
			if h := ns.GetHost(); h != nil {
				f.Attack(h)
			} else {
				f.Hunt()
			}
		})
	}
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
		var group []ns.Obj
		for _, r := range rouse {
			if a := find(r); a != nil {
				group = append(group, a)
			}
		}
		spreadOn(group, ns.GetHost())
	})
	o.OnEvent(ns.EventLostEnemy, func() {
		alerted = false
		o.WalkTo(post)
		ns.NewTimer(ns.Seconds(4), func() { o.Guard(post, face, 160) })
	})
}

// ---- Pack --------------------------------------------------------------------------------------------------------

// Pack: a pack lies up spread about its den, each on its own spot (not trailing its leader in a knot); when any of
// them sees or is hit by an enemy, all come at it from their own sides; when it is lost they go back to their spots;
// when the leader dies, the rest flee.
func Pack(leader string, members []string) {
	l := find(leader)
	if l == nil {
		return
	}
	all := []ns.Obj{l}
	for _, m := range members {
		if o := find(m); o != nil {
			all = append(all, o)
		}
	}
	posts := make([]ns.Pointf, len(all))
	var cx, cy float32
	for k, o := range all {
		posts[k] = o.Pos()
		cx, cy = cx+posts[k].X, cy+posts[k].Y
	}
	den := ns.Ptf(cx/float32(len(all)), cy/float32(len(all)))
	settle := func() {
		for k, o := range all {
			if o == nil || o.CurrentHealth() <= 0 {
				continue
			}
			p := posts[k]
			out := ns.Ptf(2*p.X-den.X, 2*p.Y-den.Y) // facing out from the den
			o.Guard(p, out, 120)
		}
	}
	settle()
	hunting := false
	rouse := func() {
		if hunting {
			return
		}
		hunting = true
		spreadOn(all, ns.GetHost())
	}
	calm := func() {
		hunting = false
		for k, o := range all {
			if o != nil && o.CurrentHealth() > 0 {
				o.WalkTo(posts[k])
			}
		}
		ns.NewTimer(ns.Seconds(5), settle)
	}
	for _, o := range all {
		o.OnEvent(ns.EventEnemySighted, rouse)
		o.OnEvent(ns.EventIsHit, rouse)
	}
	l.OnEvent(ns.EventLostEnemy, func() { ns.NewTimer(ns.Seconds(5), calm) })
	l.OnEvent(ns.EventDeath, func() {
		h := ns.GetHost()
		for _, o := range all[1:] {
			if o == nil || o.CurrentHealth() <= 0 {
				continue
			}
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
		}
		spreadOn(group, h)
	})
}

// ---- Route walkers (Tour, Patrol, Journey) ------------------------------------------------------------------------

// walker walks one creature round a route: Move to each waypoint in turn (the waypoints are never linked, so each
// Move ends at its waypoint and the game reports it). A waypoint with a pause is a stop, where it stands for the pause
// (and up to four seconds more) facing its look point; the others are bends and doorway points, passed straight
// through. Every callback is short: a stale timer (one set before the walk was taken over) does nothing.
//
// Nobody pushes (playtest 2026-10-05: two people pushing each other off one stop for ever). The ticker measures how
// near a walker has come to its waypoint, not whether it moved: a walker pushing against another jostles about
// without getting nearer. Near a stop it cannot reach, it stops where it is, a little aside, and takes its pause
// there; near a bend or doorway point, it goes on to the next; anywhere else (a doorway or gate someone else is in)
// it gives way, standing a second or two, then tries again, and after two tries goes on to the next waypoint.
type walker struct {
	o        ns.Obj
	wps      []ns.WaypointObj
	pause    []float32
	look     []ns.Pointf
	loop     bool
	once     bool // a journey: walked once, and at its last waypoint the walker stays
	done     bool // finished, or taken over by a journey: the ticker leaves it be
	i, step  int
	gen      int     // bumped whenever the walk changes hands
	moving   bool    // on a leg, between Move and its end
	held     bool    // hiding or fighting: the route waits
	waiting  bool    // giving way: standing a moment before trying the leg again
	standing bool    // standing its pause at a stop: the ticker keeps it facing the stop's way (or the player)
	best     float32 // the nearest it has come to its waypoint on this leg (px)
	still    int     // ticker rounds without coming nearer
	tries    int     // times it has given way on this leg
	// Tour: running home from danger, along the route
	homeIdx int
	fleeing bool
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

func dist(a, b ns.Pointf) float32 {
	return float32(math.Sqrt(float64(dist2(a, b))))
}

// walk starts the leg to waypoint i afresh.
func (w *walker) walk() {
	w.tries = 0
	w.leg()
}

// leg sends the walker on to waypoint i (again, after giving way).
func (w *walker) leg() {
	if w.held || w.done || !w.alive() || w.i < 0 || w.i >= len(w.wps) {
		return
	}
	w.gen++
	w.moving, w.waiting, w.standing, w.still = true, false, false, 0
	w.best = dist(w.o.Pos(), w.wps[w.i].Pos())
	w.o.Move(w.wps[w.i])
}

func (w *walker) advance() {
	n := len(w.wps)
	if n < 2 {
		return
	}
	if w.loop {
		w.i = (w.i + w.step + n) % n
		return
	}
	if w.i+w.step < 0 || w.i+w.step >= n {
		if w.once {
			return
		}
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
	if w.once && w.i >= len(w.wps)-1 {
		w.finish()
		return
	}
	w.advance()
	w.walk()
}

// isStop: the walker stands at waypoint i (a stop, or a journey's end).
func (w *walker) isStop() bool {
	return w.pause[w.i] > 0 || (w.once && w.i == len(w.wps)-1)
}

// finish: a journey's end. The walker stays where it is, facing on.
func (w *walker) finish() {
	w.done, w.moving, w.waiting, w.standing = true, false, false, false
	w.gen++
	if !w.alive() {
		return
	}
	p := w.o.Pos()
	face := w.look[len(w.look)-1]
	if face.X == 0 && face.Y == 0 {
		face = p
	}
	w.o.Guard(p, face, 40)
}

func (w *walker) arrived() {
	if w.held || w.done || !w.moving {
		return
	}
	w.moving = false
	if w.once && w.i == len(w.wps)-1 {
		w.finish()
		return
	}
	if w.fleeing {
		if w.i == w.homeIdx { // home: it waits there until the danger has passed
			w.fleeing, w.step = false, 1
			w.hold()
			return
		}
		w.later(ns.Frames(2), w.next)
		return
	}
	p := w.pause[w.i]
	if p <= 0 {
		w.later(ns.Frames(2), w.next)
		return
	}
	w.standing = true
	w.face()
	w.later(ns.Seconds(float64(p)+float64(ns.Random(0, 4))), w.next)
}

// face keeps a walker standing at a stop turned the stop's way (laid at build time toward open ground: away from a
// building it stands beside, toward the well it stands at, out from a door; kit/walkways stop_facing), or toward the
// player while they are within nearPlayer px, turning back when they leave. Called on arrival and by the ticker twice
// a second: the game's own idling turns a body bumped by a passer-by toward where it was pushed from, and nothing
// else turns it back (Starwell playtest 2026-10-05: "NPCs seem to face random directions when they get to stopping
// points"). It turns only a body more than 20 degrees off, so it does nothing most rounds.
const nearPlayer = 110

func (w *walker) face() {
	o := w.o
	if o == nil || w.i < 0 || w.i >= len(w.look) {
		return
	}
	p := o.Pos()
	t := w.look[w.i]
	if h := ns.GetHost(); h != nil && dist2(h.Pos(), p) < nearPlayer*nearPlayer {
		t = h.Pos()
	} else if t.X == 0 && t.Y == 0 {
		return
	}
	dx, dy := t.X-p.X, t.Y-p.Y
	if dx*dx+dy*dy < 4 {
		return
	}
	// the game's own measure: 256 steps to a turn, 0 along +x (server DirFromVec)
	want := int(math.Atan2(float64(dy), float64(dx))*40.743664+0.5) & 255
	off := (want - int(o.Direction())) & 255
	if off > 128 {
		off = 256 - off
	}
	if off <= 14 {
		return
	}
	if w.fear > 0 {
		o.Idle() // a townsperson: drop any turn the game is making toward a bump, and stand
	}
	o.LookAtObject(t)
}

// hold suspends the route (a fight, waiting at home); resume takes it up again after d.
func (w *walker) hold() {
	w.held, w.moving, w.waiting, w.standing = true, false, false, false
	w.gen++
}

func (w *walker) resume(d ns.Duration) {
	if w.done {
		return
	}
	w.held = false
	w.gen++
	w.later(d, w.walk)
}

// flee: a townsperson runs for home along its own route, the shorter way round, without stopping.
func (w *walker) flee() {
	n := len(w.wps)
	if w.homeIdx < 0 || n < 2 || w.fleeing || w.held {
		return
	}
	if w.i == w.homeIdx && !w.moving { // standing at home already
		w.hold()
		return
	}
	fwd := (w.homeIdx - w.i + n) % n
	w.fleeing, w.step = true, 1
	if fwd > n-fwd { // back the way it came: the waypoint behind it first
		w.step = -1
		w.i = (w.i - 1 + n) % n
	}
	w.walk()
}

func (w *walker) threat() ns.Obj {
	o := w.o
	return ns.FindClosestObject(o, ns.HasClass(object.ClassMonster), ns.InCirclef{Center: o, R: float64(w.fear)},
		ns.ObjCondFunc(func(x ns.Obj) bool {
			return x != o && x.IsEnabled() && x.CurrentHealth() > 0 && !friendlyType(x.Type().Name())
		}))
}

// tickWalkers: twice a second, every walker (see walker for how it keeps anyone from pushing); a townsperson looks
// round once a second for danger.
func tickWalkers() {
	walkTicks++
	for _, w := range walkers {
		if w == nil || w.done || !w.alive() {
			continue
		}
		if w.fear > 0 && (walkTicks+w.k)%2 == 0 {
			if t := w.threat(); t != nil {
				w.calm = 0
				w.flee()
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
		if w.standing && !w.held && !w.moving {
			w.face()
			continue
		}
		if !w.moving || w.held || w.waiting {
			continue
		}
		d := dist(w.o.Pos(), w.wps[w.i].Pos())
		if d < w.best-6 {
			w.best, w.still = d, 0
			continue
		}
		w.still++
		stop := w.isStop()
		if w.fleeing {
			stop = w.i == w.homeIdx
		}
		switch {
		case stop && d < 48 && w.still >= 3:
			// its spot is taken, or it is being pushed off it: it stands here, a little aside
			w.o.Idle()
			w.arrived()
		case !stop && d < 36 && w.still >= 3:
			// near enough a bend or a doorway point: on to the next
			w.next()
		case w.still >= 4 && w.tries < 2:
			// blocked (someone in the doorway, someone pushing back): give way a moment, then try again
			w.tries++
			w.waiting = true
			w.o.Idle()
			w.later(ns.Seconds(float64(1+ns.Random(0, 2))), w.leg)
		case w.still >= 4:
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
// x, y pair per waypoint to face there. With a home waypoint and fearR > 0, it runs home (along the route) from
// hostile creatures.
func Tour(name string, route []string, pause []float32, look []float32, home string, fearR float32) {
	w := newWalker(name, route, pause, look, true)
	if w == nil {
		return
	}
	if home != "" {
		if hw := ns.Waypoint(home); hw != nil {
			for k, wp := range w.wps {
				if wp == hw {
					w.homeIdx = k
					break
				}
			}
		}
	}
	w.fear = fearR
	// people set out a little apart, not all in the same frame
	w.later(ns.Frames(1+15*(w.k%8)), w.walk)
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

// ---- Journeys ----------------------------------------------------------------------------------------------------

type journeyDef struct {
	name  string
	route []string
	look  ns.Pointf
}

var journeys = map[string]*journeyDef{}
var journeysStarted int

// Journey declares a long walk (kit/story StoryMap.journey): the route from where `name` stands to where it ends,
// a waypoint at each bend of the roads and paths and three square-on through each doorway. The story starts it
// (quests.go "walk"); it is walked leg by leg as a tour is, and at its end the walker stays, facing look.
func Journey(key, name string, route []string, lookX, lookY float32) {
	journeys[key] = &journeyDef{name: name, route: route, look: ns.Ptf(lookX, lookY)}
}

// startJourney starts journey `key` for creature `name`: any walk it was on is given up. False when there is no
// such journey (the story then sends it straight to the waypoint of that name).
func startJourney(name, key string) bool {
	j := journeys[key]
	if j == nil {
		return false
	}
	o := find(name)
	if o == nil {
		return true
	}
	for _, w := range walkers {
		if w != nil && w.o == o && !w.done {
			w.hold()
			w.done = true
		}
	}
	n := len(j.route)
	pause := make([]float32, n)
	look := make([]float32, 2*n)
	if n > 0 {
		look[2*n-2], look[2*n-1] = j.look.X, j.look.Y
	}
	w := newWalker(name, j.route, pause, look, false)
	if w == nil {
		return true
	}
	w.once = true
	// two set off by one word (a crew walking home) leave a second and a half apart, not shoulder to shoulder
	w.later(ns.Frames(2+45*(journeysStarted%4)), w.walk)
	journeysStarted++
	return true
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
