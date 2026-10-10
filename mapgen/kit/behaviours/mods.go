package PKG

// Creative additions to the base game (dystopiannox mods/MODLAB.md), run by OpenNox from the map's folder.
// Written against NoxScript ns/v4 v4.16.1, the version OpenNox v1.9.0-alpha13 bundles: no Obj.Vel(), and the
// stubbed calls (TellStoryStr, quest status, journal strings, MakeFriendly/MakeEnemy, GiveXp, SetRoamFlag,
// ObjGroup.Delete/Wander) are never used.
//
// Three systems, set up by the map's mods config (kit/mods.py writes it):
//
//   Weapons  named weapons with powers. A melee weapon's power fires when its wielder's blow lands: every creature
//            reports its hits (the IsHit event names the attacker), and a hit from the host player holding the
//            weapon runs the power. Ranged powers watch what the weapon fires: the Chakram Storm's thrown chakram,
//            the Stormcaller's fireball (deleted and replaced).
//   Monsters new creatures built from the game's own, each with a scripted ability set; they wait frozen in their
//            pen until the player comes in (or strikes them), and come back a while after they die.
//   Smithing a forge: lay a weapon by the anvil and step on the forge plate. A weapon of a known line becomes the
//            next tier, which is a copy made in the map (with the game's own enchantments: WeaponPower, Material,
//            FireRing, Impact, Stun...) kept in a sealed vault and brought to the anvil. The smith's level grows
//            with every piece worked; it opens the higher tiers and lowers the price.
//
// Projectiles flown by the script (chakrams) are ownerless and have NoCollide and NoUpdate set: the game's own
// update for a RoundChakramInMotion deletes one that carries no chakram, and an owned missile would run the game's
// collision code (rules/WEAPONS.md: a HarpoonBolt owned by a creature panics the server).
//
// With no host player (the dedicated server of tests/server_smoke.py) the script runs a self-test instead: every
// power, ability and forge step once against stand-in creatures, printing "modlab selftest: ..." lines.

import (
	"fmt"
	"math"

	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/class"
	"github.com/noxworld-dev/noxscript/ns/v4/damage"
	"github.com/noxworld-dev/noxscript/ns/v4/effect"
	"github.com/noxworld-dev/noxscript/ns/v4/enchant"
	"github.com/noxworld-dev/opennox-lib/object"
)

// ---- small helpers --------------------------------------------------------------------------------------------

func modAlive(o ns.Obj) bool {
	return o != nil && o.CurrentHealth() > 0 && !o.Flags().HasAny(object.FlagDead|object.FlagDestroyed)
}

func modDist(a, b ns.Pointf) float32 {
	return float32(math.Hypot(float64(a.X-b.X), float64(a.Y-b.Y)))
}

// modDir is the unit vector from a to b and the distance.
func modDir(a, b ns.Pointf) (float32, float32, float32) {
	d := modDist(a, b)
	if d < 0.01 {
		return 1, 0, 0
	}
	return (b.X - a.X) / d, (b.Y - a.Y) / d, d
}

func modSame(a, b ns.Obj) bool {
	return a != nil && b != nil && a.ObjScriptID() == b.ObjScriptID()
}

func modSay(msg string) {
	ns.PrintStrToAll(msg)
	println("modlab:", msg)
}

// ---- the creatures the scripts watch ------------------------------------------------------------------------------

// A watched creature: its IsHit and Death events, shared by every system (an object has one callback per event).
type modWatched struct {
	o          ns.Obj
	id         int
	dead       bool
	onHit      []func(attacker ns.Obj)
	onDeath    []func()
	scriptHit  int    // frame until which a hit is the script's own (a power's splash), not the wielder's blow
	lastKind   string // the power of the host's last blow on it, and when (for on-kill powers)
	lastHitAt  int
	frostCount int
	frostUntil int
}

var (
	modWatch     = map[int]*modWatched{}
	modProtected = map[int]bool{} // never struck by powers: the smith, the self-test's wielder
	modSelfTest  bool
	modTestFoe   ns.Obj
)

func modWatchObj(o ns.Obj) *modWatched {
	if o == nil {
		return nil
	}
	id := o.ObjScriptID()
	if w, ok := modWatch[id]; ok {
		return w
	}
	w := &modWatched{o: o, id: id}
	modWatch[id] = w
	o.OnEvent(ns.EventIsHit, func() {
		if w.dead {
			return
		}
		a := ns.GetCaller()
		for _, f := range w.onHit {
			f(a)
		}
	})
	o.OnEvent(ns.EventDeath, func() {
		if w.dead {
			return
		}
		w.dead = true
		for _, f := range w.onDeath {
			f()
		}
	})
	w.onHit = append(w.onHit, func(a ns.Obj) { modHostBlow(w, a) })
	w.onDeath = append(w.onDeath, func() { modHostKill(w) })
	return w
}

// ModLeaveAlone: creatures whose events another script owns (kit/behaviours/behaviours.go sets their IsHit,
// Death... callbacks; an object has one per event, so watching them here would undo those). Powers still strike
// them; only the Bloodthirst's feast and the Frostbite's count need their events.
var modLeave = map[int]bool{}

func ModLeaveAlone(names []string) {
	for _, n := range names {
		if o := ns.Object(n); o != nil {
			modLeave[o.ObjScriptID()] = true
		}
	}
}

func modIsTarget(o ns.Obj) bool {
	return o.HasClass(class.MONSTER) && modAlive(o) && !modProtected[o.ObjScriptID()]
}

var modTargetCond = ns.ObjCondFunc(modIsTarget)

func modStrike(src, o ns.Obj, dmg int, typ damage.Type) {
	if o == nil || src == nil || !modAlive(o) {
		return
	}
	if w := modWatch[o.ObjScriptID()]; w != nil {
		w.scriptHit = ns.Frame() + 4
	}
	modHurt(o, src, dmg, typ)
}

// modHurt: o takes dmg from src. The game ignores one creature's damage to another of the same side, so the
// self-test (whose stand-ins are all creatures) strikes with no source, which the game applies.
func modHurt(o, src ns.Obj, dmg int, typ damage.Type) {
	if modSelfTest && (src == nil || !src.HasClass(class.PLAYER)) {
		o.Damage(nil, dmg, typ)
		return
	}
	o.Damage(src, dmg, typ)
}

// The one the monsters fight: the host player, or the self-test's stand-in.
func modFoe() ns.Obj {
	if modSelfTest {
		if modAlive(modTestFoe) {
			return modTestFoe
		}
		return nil
	}
	h := ns.GetHost()
	if h == nil || h.CurrentHealth() <= 0 {
		return nil
	}
	return h
}

// ---- shoves (knockback) -------------------------------------------------------------------------------------------

type modShove struct {
	o      ns.Obj
	w      *modWatched
	fx, fy float32
	frames int
}

var modShoves []*modShove

func modPush(o ns.Obj, from ns.Pointf, force float32, frames int) {
	dx, dy, _ := modDir(from, o.Pos())
	modShoves = append(modShoves, &modShove{o: o, w: modWatch[o.ObjScriptID()], fx: dx * force, fy: dy * force, frames: frames})
}

func modShoveFrame() {
	keep := modShoves[:0]
	for _, s := range modShoves {
		if s.frames <= 0 || (s.w != nil && s.w.dead) || !modAlive(s.o) {
			continue
		}
		s.o.ApplyForce(ns.Ptf(s.fx, s.fy))
		s.frames--
		keep = append(keep, s)
	}
	modShoves = keep
}

// ---- boomerangs: chakrams flown by the script -------------------------------------------------------------------

type modBoomerang struct {
	obj      ns.Obj
	home     func() ns.Obj // who it returns to (nil: gone, the chakram drops)
	src      ns.Obj        // the damage's source
	pos      ns.Pointf
	dx, dy   float32
	speed    float32
	out      float32
	reach    float32
	back     bool
	life     int
	dmg      int
	foeOnly  bool // a monster's chakram strikes only its foe; the player's strike monsters
	hit      map[int]bool
}

var modBoomerangs []*modBoomerang

func modThrow(src ns.Obj, home func() ns.Obj, from ns.Pointf, dx, dy, speed, reach float32, dmg int, foeOnly bool) {
	c := ns.CreateObject("RoundChakramInMotion", ns.Ptf(from.X+dx*18, from.Y+dy*18))
	if c == nil {
		return
	}
	c.FlagsEnable(object.FlagNoCollide | object.FlagNoUpdate)
	c.LookWithAngle(int(math.Atan2(float64(dy), float64(dx))/(2*math.Pi)*256) & 255)
	modBoomerangs = append(modBoomerangs, &modBoomerang{obj: c, home: home, src: src, pos: c.Pos(), dx: dx, dy: dy,
		speed: speed, reach: reach, dmg: dmg, foeOnly: foeOnly, hit: map[int]bool{}})
}

func modBoomerangFrame() {
	keep := modBoomerangs[:0]
	for _, b := range modBoomerangs {
		b.life++
		home := b.home()
		if b.life > 240 || (b.back && home == nil) {
			b.obj.Delete()
			continue
		}
		if b.back {
			dx, dy, d := modDir(b.pos, home.Pos())
			if d < 26 {
				b.obj.Delete()
				continue
			}
			b.dx, b.dy = dx, dy
		}
		b.pos = ns.Ptf(b.pos.X+b.dx*b.speed, b.pos.Y+b.dy*b.speed)
		b.obj.SetPos(b.pos)
		if !b.back {
			b.out += b.speed
			if b.out >= b.reach || ns.FindClosestWall(b.pos, ns.InCirclef{Center: b.pos, R: 12}) != nil {
				b.back, b.hit = true, map[int]bool{}
			}
		}
		if b.foeOnly {
			if f := modFoe(); f != nil && !b.hit[f.ObjScriptID()] && modDist(f.Pos(), b.pos) < 26 {
				b.hit[f.ObjScriptID()] = true
				modHurt(f, b.src, b.dmg, damage.BLADE)
				ns.Effect(effect.DAMAGE_POOF, f, nil)
			}
		} else {
			for _, m := range ns.FindAllObjects(ns.InCirclef{Center: b.pos, R: 26}, modTargetCond) {
				if b.hit[m.ObjScriptID()] || modSame(m, b.src) {
					continue
				}
				b.hit[m.ObjScriptID()] = true
				modStrike(b.src, m, b.dmg, damage.BLADE)
			}
		}
		keep = append(keep, b)
	}
	modBoomerangs = keep
}

// ---- weapons ----------------------------------------------------------------------------------------------------

// The power of each named weapon (and of its forged copies), by the object's script ID, and its tier.
var (
	modKind = map[int]string{}
	modTier = map[int]int{}
	modSeen = map[int]bool{} // thrown chakrams already answered
)

// ModWeapon names a weapon with a power: "flame" (W1, the game's own FireRing enchantment: no script), "chakram"
// (W2), "quake" (W3), "storm" (W4), "blood" (W5), "frost" (W6).
func ModWeapon(kind, name string, tier int) {
	o := ns.Object(name)
	if o == nil {
		println("modlab: weapon", name, "not found")
		return
	}
	modKind[o.ObjScriptID()] = kind
	modTier[o.ObjScriptID()] = tier
	modWeaponObjs = append(modWeaponObjs, o)
}

var modWeaponObjs []ns.Obj

func modWielded(h ns.Obj) (string, int) {
	if h == nil {
		return "", 0
	}
	for _, it := range h.Equipment() {
		if k, ok := modKind[it.ObjScriptID()]; ok {
			return k, modTier[it.ObjScriptID()]
		}
	}
	return "", 0
}

// A blow landed on a watched creature: the host's power runs if its weapon has one.
//
// The event's caller is the creature's last attacker as the game records it (OpenNox unit_ai.go: Obj130), which for
// a blow is the damage's direct source when there is one (legacy GAME3_2.c: the weapon, or a missile) and otherwise
// its owner: the host, the weapon it holds, or something it owns all count.
func modByHost(a, h ns.Obj) bool {
	return a != nil && (modSame(a, h) || h.HasEquipment(a) || a.HasOwner(h))
}

func modHostBlow(w *modWatched, attacker ns.Obj) {
	h := ns.GetHost()
	if h == nil || !modByHost(attacker, h) || ns.Frame() < w.scriptHit || !modAlive(w.o) {
		return
	}
	kind, tier := modWielded(h)
	if kind == "" {
		return
	}
	w.lastKind, w.lastHitAt = kind, ns.Frame()
	modOnBlow(kind, tier, h, w.o)
}

var modQuakeReady int

// modOnBlow: the melee powers, wielder striking target.
func modOnBlow(kind string, tier int, src, target ns.Obj) {
	switch kind {
	case "quake": // W3: a shockwave round the struck creature, throwing everything near it back
		if ns.Frame() < modQuakeReady {
			return
		}
		modQuakeReady = ns.Frame() + 12
		c := target.Pos()
		ns.Effect(effect.JIGGLE, c, ns.Ptf(float32(8+3*tier), 0))
		ns.Effect(effect.SMOKE_BLAST, c, nil)
		ns.Effect(effect.SPARK_EXPLOSION, c, ns.Ptf(float32(60+20*tier), 0))
		r := float64(100 + 20*tier)
		for _, m := range ns.FindAllObjects(ns.InCirclef{Center: c, R: r}, modTargetCond) {
			if modSame(m, src) {
				continue
			}
			if !modSame(m, target) {
				modStrike(src, m, 8+4*tier, damage.CRUSH)
			}
			modPush(m, src.Pos(), 5+float32(tier), 8)
		}
	case "blood": // W5: drinks from every blow
		src.RestoreHealth(3 + tier)
		ns.Effect(effect.VAMPIRISM, target, src)
	case "frost": // W6: slows; the third blow within five seconds freezes solid
		w := modWatch[target.ObjScriptID()]
		target.Enchant(enchant.SLOWED, ns.Seconds(4))
		ns.Effect(effect.CYAN_SPARKS, target, nil)
		if w == nil {
			return
		}
		if ns.Frame() > w.frostUntil {
			w.frostCount = 0
		}
		w.frostCount++
		w.frostUntil = ns.Frame() + 150
		if w.frostCount >= 3 {
			w.frostCount = 0
			target.Enchant(enchant.FREEZE, ns.Seconds(2.5))
			target.Enchant(enchant.HELD, ns.Seconds(2.5))
			ns.Effect(effect.WHITE_FLASH, target, nil)
			if !modSelfTest {
				modSay("Frostbite: frozen solid!")
			}
		}
	}
}

// A watched creature died: the Bloodthirst's feast when the host's blow killed it.
func modHostKill(w *modWatched) {
	if w.lastKind != "blood" || ns.Frame()-w.lastHitAt > 45 {
		return
	}
	if h := ns.GetHost(); h != nil {
		modFeast(h)
	}
}

func modFeast(h ns.Obj) {
	h.RestoreHealth(15)
	h.Enchant(enchant.HASTED, ns.Seconds(3))
	ns.Effect(effect.GREATER_HEAL, h, h)
}

// W2: the Chakram Storm's throw sends four more chakrams fanning out beside it, each coming back to the thrower.
func modChakramFan(h ns.Obj, dx, dy float32, tier int) {
	base := math.Atan2(float64(dy), float64(dx))
	for _, deg := range []float64{-30, -15, 15, 30} {
		a := base + deg*math.Pi/180
		modThrow(h, func() ns.Obj {
			if modSelfTest {
				return h
			}
			return ns.GetHost()
		}, h.Pos(), float32(math.Cos(a)), float32(math.Sin(a)), 12, float32(240+30*tier), 10+3*tier, false)
	}
}

// W4: the Stormcaller's shot is a chain of lightning: the first creature along the line it faces, then the
// nearest not yet struck, up to four, each strike weaker.
func modChainLightning(src ns.Obj, from ns.Pointf, dx, dy float32, tier int) int {
	var best ns.Obj
	bestD := float32(1e9)
	for _, m := range ns.FindAllObjects(ns.InCirclef{Center: from, R: 360}, modTargetCond) {
		if modSame(m, src) {
			continue
		}
		vx, vy, d := modDir(from, m.Pos())
		if d < 1 || vx*dx+vy*dy < 0.82 {
			continue
		}
		if d < bestD {
			best, bestD = m, d
		}
	}
	if best == nil {
		ns.Effect(effect.LIGHTNING, from, ns.Ptf(from.X+dx*220, from.Y+dy*220))
		return 0
	}
	prev := from
	dmg := 22 + 6*tier
	struck := map[int]bool{}
	n := 0
	for best != nil && n < 4+tier {
		ns.Effect(effect.LIGHTNING, prev, best)
		struck[best.ObjScriptID()] = true
		modStrike(src, best, dmg, damage.ELECTRIC)
		n++
		prev = best.Pos()
		dmg = dmg * 3 / 4
		var next ns.Obj
		nd := float32(1e9)
		for _, m := range ns.FindAllObjects(ns.InCirclef{Center: prev, R: 180}, modTargetCond) {
			if struck[m.ObjScriptID()] || modSame(m, src) {
				continue
			}
			if d := modDist(prev, m.Pos()); d < nd {
				next, nd = m, d
			}
		}
		best = next
	}
	return n
}

// Each frame: what the host's ranged weapons fired.
func modWeaponFrame() {
	h := ns.GetHost()
	if h == nil {
		return
	}
	kind, tier := modWielded(h)
	if kind == "storm" {
		for _, fb := range ns.FindAllObjects(ns.HasTypeName{"Fireball"}) {
			if !fb.HasOwner(h) {
				continue
			}
			dx, dy, _ := modDir(h.Pos(), fb.Pos())
			p := fb.Pos()
			fb.Delete()
			modChainLightning(h, p, dx, dy, tier)
		}
	}
	// a thrown chakram carries the chakram item: the Chakram Storm is in flight
	for _, c := range ns.FindAllObjects(ns.HasTypeName{"RoundChakramInMotion"}) {
		id := c.ObjScriptID()
		if modSeen[id] || !c.HasOwner(h) {
			continue
		}
		modSeen[id] = true
		for _, it := range c.Items() {
			if modKind[it.ObjScriptID()] == "chakram" {
				dx, dy, _ := modDir(h.Pos(), c.Pos())
				modChakramFan(h, dx, dy, modTier[it.ObjScriptID()])
				break
			}
		}
	}
}

// ---- monsters ---------------------------------------------------------------------------------------------------

type modBoss struct {
	kind, name, typ string
	label           string
	home            ns.Pointf
	hp              int
	engageR         float32
	respawn         int // frames
	trainee         bool
	o               ns.Obj
	w               *modWatched
	engaged         bool
	deadAt          int
	lastHP          int
	t, t2           int // ability timers
	exposed         int
	side            float32
	minions         []*modWatched
	shielded        bool
	spawns          int
}

var modBosses []*modBoss

// ModBoss: a placed creature named `name` becomes monster `kind` ("ogrelord", "crab", "bonecaller", "embermother",
// "duelist"), or a training target ("trainee"); it has hp health (0: its own), waits frozen until its foe comes
// within engageR px (0: awake from the start), and comes back respawnSec seconds after it dies (0: never).
func ModBoss(kind, name, label string, hp int, engageR float32, respawnSec float64) {
	o := ns.Object(name)
	if o == nil {
		println("modlab: creature", name, "not found")
		return
	}
	b := &modBoss{kind: kind, name: name, label: label, typ: o.Type().Name(), home: o.Pos(), hp: hp, engageR: engageR,
		respawn: int(respawnSec * 30), trainee: kind == "trainee", side: 1}
	modBosses = append(modBosses, b)
	b.adopt(o)
}

func (b *modBoss) adopt(o ns.Obj) {
	b.o = o
	b.engaged = false
	b.t, b.t2, b.exposed, b.shielded = 0, 0, 0, false
	if b.hp > 0 {
		o.SetMaxHealth(b.hp)
		o.SetHealth(b.hp)
	}
	b.lastHP = o.CurrentHealth()
	b.w = modWatchObj(o)
	w := b.w
	w.onHit = append(w.onHit, func(a ns.Obj) {
		if b.w == w && !b.engaged {
			b.engage()
		}
	})
	w.onDeath = append(w.onDeath, func() {
		if b.w == w {
			b.died()
		}
	})
	if b.engageR > 0 {
		o.Freeze(true)
	} else {
		b.engaged = true // awake from the start: the game's own AI hunts until the abilities' foe is near
	}
}

func (b *modBoss) engage() {
	if b.o == nil || b.engaged {
		return
	}
	b.engaged = true
	b.o.Freeze(false)
	if f := modFoe(); f != nil {
		b.o.Attack(f)
	} else {
		b.o.Hunt()
	}
	if !b.trainee {
		modSay(b.label + " wakes!")
		switch b.kind {
		case "ogrelord":
			b.o.ChatStrTimer("You'll eat steel, little one!", ns.Seconds(3))
		case "crab":
			b.o.ChatStrTimer("*click click*", ns.Seconds(2))
		case "bonecaller":
			b.o.ChatStrTimer("My servants never tire.", ns.Seconds(3))
		case "embermother":
			b.o.ChatStrTimer("Children! Feed!", ns.Seconds(3))
		case "duelist":
			b.o.ChatStrTimer("En garde.", ns.Seconds(2))
		}
	}
}

func (b *modBoss) died() {
	var none ns.Obj // (yaegi panics on "b.o, b.engaged = nil, false": the self-test caught it)
	b.o = none
	b.engaged = false
	b.deadAt = ns.Frame()
	switch b.kind {
	case "bonecaller": // the bones crumble with their master
		for _, m := range b.minions {
			if !m.dead {
				m.dead = true
				ns.Effect(effect.SMOKE_BLAST, m.o, nil)
				m.o.Delete()
				modCrumbled++
			}
		}
		b.minions = nil
	case "embermother": // her brood bursts into flame
		for _, m := range b.minions {
			if !m.dead && modAlive(m.o) {
				p := m.o.Pos()
				m.dead = true
				m.o.Delete()
				modFlameBurst(p)
			}
		}
		b.minions = nil
	}
	if !b.trainee && b.respawn > 0 {
		modSay(fmt.Sprintf("%s is slain. It returns in %d seconds.", b.label, b.respawn/30))
	} else if !b.trainee {
		modSay(b.label + " is slain.")
	}
}

func (b *modBoss) frame() {
	if b.o == nil {
		if b.respawn > 0 && ns.Frame()-b.deadAt >= b.respawn {
			o := ns.CreateObject(b.typ, b.home)
			if o != nil {
				ns.Effect(effect.TELEPORT, b.home, nil)
				b.adopt(o)
				println("modlab:", b.name, "respawned")
			}
		}
		return
	}
	foe := modFoe()
	if !b.engaged {
		// wakes when its foe comes near, or when struck from afar (a frozen creature may not report the hit)
		if (foe != nil && modDist(foe.Pos(), b.o.Pos()) < b.engageR) || b.o.CurrentHealth() < b.lastHP {
			b.engage()
		}
		b.lastHP = b.o.CurrentHealth()
		return
	}
	b.t++
	b.t2++
	switch b.kind {
	case "ogrelord":
		b.ogreLord(foe)
	case "crab":
		b.crab(foe)
	case "bonecaller":
		b.boneCaller(foe)
	case "embermother":
		b.emberMother(foe)
	case "duelist":
		b.duelist(foe)
	}
	if b.o != nil {
		b.lastHP = b.o.CurrentHealth()
	}
}

func (b *modBoss) self() func() ns.Obj {
	return func() ns.Obj {
		if b.o == nil || b.w == nil || b.w.dead {
			return nil
		}
		return b.o
	}
}

// M1 Ogre Lord: hurls boomerang chakrams, three in a fan once wounded below half, and catches them as they return.
func (b *modBoss) ogreLord(foe ns.Obj) {
	if foe == nil || b.t < 70 {
		return
	}
	p, fp := b.o.Pos(), foe.Pos()
	if modDist(p, fp) > 420 || (!modSelfTest && !b.o.CanSee(foe)) {
		return
	}
	b.t = 0
	b.ogreThrow(foe)
}

func (b *modBoss) ogreThrow(foe ns.Obj) {
	p := b.o.Pos()
	dx, dy, d := modDir(p, foe.Pos())
	b.o.LookAtObject(foe)
	spread := []float64{0}
	if b.o.CurrentHealth()*2 < b.hp {
		spread = []float64{-18, 0, 18}
	}
	base := math.Atan2(float64(dy), float64(dx))
	reach := d + 60
	if reach > 380 {
		reach = 380
	}
	for _, deg := range spread {
		a := base + deg*math.Pi/180
		modThrow(b.o, b.self(), p, float32(math.Cos(a)), float32(math.Sin(a)), 11, reach, 12, true)
	}
}

// M2 Giant Crab: its shell turns two thirds of every blow, except for two seconds after it snaps; it scuttles
// sideways round its foe, and its snap pins the foe in place.
func (b *modBoss) crab(foe ns.Obj) {
	cur := b.o.CurrentHealth()
	if b.exposed > 0 {
		b.exposed--
		if b.exposed == 0 {
			b.o.ChatStrTimer("*the shell closes*", ns.Seconds(1))
		}
	} else if cur < b.lastHP && cur > 0 {
		back := (b.lastHP - cur) * 2 / 3
		if back > 0 {
			b.o.RestoreHealth(back)
			ns.Effect(effect.RICOCHET, b.o, nil)
		}
	}
	if foe == nil {
		return
	}
	p, fp := b.o.Pos(), foe.Pos()
	d := modDist(p, fp)
	if d < 75 && b.t >= 90 {
		b.t = 0
		b.crabSnap(foe)
		return
	}
	if b.t2 >= 50 && d < 300 && d > 80 {
		b.t2 = 0
		dx, dy, _ := modDir(p, fp)
		b.side = -b.side
		to := ns.Ptf(p.X-dy*70*b.side+dx*20, p.Y+dx*70*b.side+dy*20)
		if ns.FindClosestWall(to, ns.InCirclef{Center: to, R: 20}) == nil {
			b.o.WalkTo(to)
		}
	} else if b.t2 == 25 {
		b.o.Attack(foe)
	}
}

func (b *modBoss) crabSnap(foe ns.Obj) {
	b.o.LookAtObject(foe)
	modHurt(foe, b.o, 14, damage.CLAW)
	foe.Enchant(enchant.HELD, ns.Seconds(1.2))
	ns.Effect(effect.DAMAGE_POOF, foe, nil)
	b.exposed = 60
	b.o.ChatStrTimer("*SNAP* (the shell gapes open)", ns.Seconds(2))
}

// M3 Bone Caller: raises skeletons two at a time (four at most); while two or more stand, a bone ward turns half
// of every blow; when he falls they crumble.
func (b *modBoss) boneCaller(foe ns.Obj) {
	live := b.minions[:0]
	for _, m := range b.minions {
		if !m.dead {
			live = append(live, m)
		}
	}
	b.minions = live
	cur := b.o.CurrentHealth()
	ward := len(b.minions) >= 2
	if ward && cur < b.lastHP && cur > 0 {
		b.o.RestoreHealth((b.lastHP - cur) / 2)
		ns.Effect(effect.VIOLET_SPARKS, b.o, nil)
	}
	if ward != b.shielded {
		b.shielded = ward
		if ward {
			b.o.ChatStrTimer("The bones shield me.", ns.Seconds(2))
		}
	}
	if foe != nil && b.t >= 150 && len(b.minions) < 4 && modDist(b.o.Pos(), foe.Pos()) < 420 {
		b.t = 0
		b.raise(foe)
	}
}

func (b *modBoss) raise(foe ns.Obj) {
	p := b.o.Pos()
	b.o.ChatStrTimer("Rise!", ns.Seconds(1.5))
	for k := 0; k < 2; k++ {
		a := ns.RandomFloat(0, 2*math.Pi)
		at := ns.Ptf(p.X+50*float32(math.Cos(float64(a))), p.Y+50*float32(math.Sin(float64(a))))
		if ns.FindClosestWall(at, ns.InCirclef{Center: at, R: 18}) != nil {
			at = p
		}
		s := ns.CreateObject("Skeleton", at)
		if s == nil {
			continue
		}
		ns.Effect(effect.SMOKE_BLAST, at, nil)
		b.minions = append(b.minions, modWatchObj(s))
		if foe != nil {
			s.Attack(foe)
		}
	}
}

// M4 Ember Matriarch: births imps (five at most) that burst into flame when they die; she mends a little for every
// imp alive; when she falls her brood bursts.
func (b *modBoss) emberMother(foe ns.Obj) {
	live := b.minions[:0]
	for _, m := range b.minions {
		if !m.dead {
			live = append(live, m)
		}
	}
	b.minions = live
	if b.t2 >= 60 && len(b.minions) > 0 {
		b.t2 = 0
		b.o.RestoreHealth(3 * len(b.minions))
	}
	if foe != nil && b.t >= 120 && len(b.minions) < 5 && modDist(b.o.Pos(), foe.Pos()) < 450 {
		b.t = 0
		b.brood(foe)
	}
}

func (b *modBoss) brood(foe ns.Obj) {
	p := b.o.Pos()
	a := ns.RandomFloat(0, 2*math.Pi)
	at := ns.Ptf(p.X+40*float32(math.Cos(float64(a))), p.Y+40*float32(math.Sin(float64(a))))
	if ns.FindClosestWall(at, ns.InCirclef{Center: at, R: 16}) != nil {
		at = p
	}
	imp := ns.CreateObject("Imp", at)
	if imp == nil {
		return
	}
	ns.Effect(effect.SPARK_EXPLOSION, at, ns.Ptf(40, 0))
	w := modWatchObj(imp)
	w.onDeath = append(w.onDeath, func() { modFlameBurst(imp.Pos()) })
	b.minions = append(b.minions, w)
	if foe != nil {
		imp.Attack(foe)
	}
}

var modBursts, modCrumbled int

func modFlameBurst(p ns.Pointf) {
	modBursts++
	f := ns.CreateObject("MediumFlame", p)
	if f != nil {
		f.DeleteAfter(ns.Seconds(4))
	}
	ns.Effect(effect.SPARK_EXPLOSION, p, ns.Ptf(70, 0))
	if foe := modFoe(); f != nil && foe != nil && modDist(foe.Pos(), p) < 60 {
		modHurt(foe, f, 6, damage.FLAME)
	}
}

// M5 Blink Duelist: steps through space to stand behind his foe and strikes; once, when badly hurt, he wraps
// himself in a ward that nothing pierces for two seconds.
func (b *modBoss) duelist(foe ns.Obj) {
	if !b.shielded && b.o.CurrentHealth()*100 < b.hp*35 {
		b.shielded = true
		b.o.Enchant(enchant.INVULNERABLE, ns.Seconds(2))
		b.o.ChatStrTimer("You cannot touch me!", ns.Seconds(2))
	}
	if foe == nil || b.t < 110 {
		return
	}
	d := modDist(b.o.Pos(), foe.Pos())
	if d > 340 || d < 70 {
		return
	}
	b.t = 0
	b.blink(foe)
}

func (b *modBoss) blink(foe ns.Obj) bool {
	p, fp := b.o.Pos(), foe.Pos()
	dx, dy, _ := modDir(p, fp)
	to := ns.Ptf(fp.X+dx*45, fp.Y+dy*45)
	if ns.FindClosestWall(to, ns.InCirclef{Center: to, R: 20}) != nil {
		return false
	}
	ns.Effect(effect.TELEPORT, p, nil)
	b.o.SetPos(to)
	ns.Effect(effect.TELEPORT, to, nil)
	b.o.LookAtObject(foe)
	b.o.Attack(foe)
	return true
}

// ---- smithing ---------------------------------------------------------------------------------------------------

type modLine struct {
	key, label, base, kind string
	tiers                  [][]ns.Obj // tiers[1..3]: the vault's copies, used in turn
	used                   []int
}

var (
	modLines     []*modLine
	modLineOf    = map[int]*modLine{} // forged copies and named tier-0 weapons, by script ID
	modLineTier  = map[int]int{}
	modAnvil     ns.Obj
	modPlate     ns.Pointf
	modSmith     ns.Obj
	modOnPlate   int
	modSmithXP   int
	modSmithTalk int
)

var modTierName = []string{"plain", "fine", "superb", "masterwork"}
var modTierCost = []int{0, 100, 200, 400}
var modLevelXP = []int{0, 0, 2, 5, 9, 14} // XP for smithing levels 1..5

func modSmithLevel() int {
	lv := 1
	for k := 2; k < len(modLevelXP); k++ {
		if modSmithXP >= modLevelXP[k] {
			lv = k
		}
	}
	return lv
}

func modCost(tier int) int {
	return modTierCost[tier] * (100 - 8*(modSmithLevel()-1)) / 100
}

// ModForge: the anvil (named object), the plate's centre (px) and the smith (named creature).
func ModForge(anvil string, plateX, plateY float32, smith string) {
	modAnvil = ns.Object(anvil)
	modPlate = ns.Ptf(plateX, plateY)
	modSmith = ns.Object(smith)
	if modSmith != nil {
		modProtected[modSmith.ObjScriptID()] = true
		modSmith.Freeze(true)
	}
	if modAnvil == nil {
		println("modlab: anvil", anvil, "not found")
	}
}

// ModForgeLine: a line of weapons the forge knows. base: the plain weapon's type (any unnamed one is tier 0);
// named0: named tier-0 weapons (a power weapon); t1..t3 the vault's copies of each tier; kind: the power the
// copies carry ("" for none).
func ModForgeLine(key, label, base, kind string, named0, t1, t2, t3 []string) {
	l := &modLine{key: key, label: label, base: base, kind: kind, tiers: make([][]ns.Obj, 4), used: make([]int, 4)}
	for _, n := range named0 {
		if o := ns.Object(n); o != nil {
			modLineOf[o.ObjScriptID()], modLineTier[o.ObjScriptID()] = l, 0
		}
	}
	for t, names := range [][]string{nil, t1, t2, t3} {
		for _, n := range names {
			o := ns.Object(n)
			if o == nil {
				println("modlab: forge copy", n, "not found")
				continue
			}
			l.tiers[t] = append(l.tiers[t], o)
			modLineOf[o.ObjScriptID()], modLineTier[o.ObjScriptID()] = l, t
		}
	}
	modLines = append(modLines, l)
}

func modSmithSay(msg string) {
	if modSmith != nil {
		modSmith.ChatStrTimer(msg, ns.Seconds(4))
	}
	modSay(msg)
}

func modIsWeapon(o ns.Obj) bool {
	return (o.HasClass(class.WEAPON) || o.HasClass(class.WAND)) && o.GetHolder() == nil
}

// modHandOver brings a forged copy out of the vault to the anvil. Moving an item with SetPos leaves it out of the
// map's search index (the self-test showed a SetPos'd copy found by a full scan but by no area search, so the player
// could not have picked it up), so the smith takes it into his pack and drops it at his feet by the anvil, which is
// the game's own drop; failing that it goes straight into the player's pack.
func modHandOver(it ns.Obj, at ns.Pointf, h ns.Obj) string {
	if modSmith != nil && modSmith.Pickup(it) {
		if modSmith.Drop(it) {
			return "the smith"
		}
	}
	if h != nil && h.Pickup(it) {
		return "the player's pack"
	}
	it.SetPos(at)
	return "SetPos"
}

// The weapon lying nearest the anvil, within 110 px.
func modOnAnvil() ns.Obj {
	if modAnvil == nil {
		return nil
	}
	var best ns.Obj
	bd := float32(1e9)
	for _, it := range ns.FindAllObjects(ns.InCirclef{Center: modAnvil, R: 110}, ns.ObjCondFunc(modIsWeapon)) {
		if d := modDist(it.Pos(), modAnvil.Pos()); d < bd {
			best, bd = it, d
		}
	}
	return best
}

// modForgeStrike works the weapon by the anvil; free in the self-test. Returns what happened.
func modForgeStrike(h ns.Obj, free bool) string {
	it := modOnAnvil()
	if it == nil {
		modSmithSay("Lay a weapon beside the anvil, then step on the plate.")
		if modSelfTest {
			n := len(ns.FindAllObjects(ns.InCirclef{Center: modAnvil, R: 400}, ns.ObjCondFunc(modIsWeapon)))
			return fmt.Sprint("empty (", n, " weapons within 400 px)")
		}
		return "empty"
	}
	id := it.ObjScriptID()
	l, tier := modLineOf[id], modLineTier[id]
	if l == nil {
		for _, c := range modLines {
			if c.base == it.Type().Name() && c.kind == "" {
				l, tier = c, 0
			}
		}
	}
	if l == nil {
		if modKind[id] != "" {
			modSmithSay("That one carries a power I dare not touch.")
			return "refused"
		}
		// melt it down: a little gold and experience
		ns.Effect(effect.SPARK_EXPLOSION, it, ns.Ptf(50, 0))
		it.Delete()
		if h != nil {
			h.ChangeGold(20)
		}
		modSmithXP++
		modSmithSay(fmt.Sprintf("Melted down for 20 gold. Smithing level %d (xp %d).", modSmithLevel(), modSmithXP))
		return "salvaged"
	}
	if tier >= 3 {
		modSmithSay("That is already a masterwork. Nothing left to teach that steel.")
		return "max"
	}
	next := tier + 1
	if modSmithLevel() < next {
		modSmithSay(fmt.Sprintf("A %s %s needs smithing level %d; we are level %d. Work more steel first (melt spare weapons too).",
			modTierName[next], l.label, next, modSmithLevel()))
		return "level"
	}
	cost := modCost(next)
	if !free {
		if h == nil || h.GetGold() < cost {
			modSmithSay(fmt.Sprintf("A %s %s costs %d gold.", modTierName[next], l.label, cost))
			return "gold"
		}
	}
	if l.used[next] >= len(l.tiers[next]) {
		modSmithSay(fmt.Sprintf("I have no more %s %s blanks.", modTierName[next], l.label))
		return "stock"
	}
	copyObj := l.tiers[next][l.used[next]]
	l.used[next]++
	at := it.Pos()
	it.Delete()
	how := modHandOver(copyObj, at, h)
	if modSelfTest {
		cid := copyObj.ObjScriptID()
		ns.NewTimer(ns.Frames(3), func() {
			found := false
			for _, o := range ns.FindAllObjects(ns.InCirclef{Center: modAnvil, R: 100}) {
				found = found || o.ObjScriptID() == cid
			}
			sp := ns.Ptf(0, 0)
			if modSmith != nil {
				sp = modSmith.Pos()
			}
			println("modlab selftest: forged copy handed over by", how, "- found by the anvil:", found, "- copy",
				int(modDist(copyObj.Pos(), modAnvil.Pos())), "px from the anvil, smith", int(modDist(sp, modAnvil.Pos())),
				"px, held", copyObj.GetHolder() != nil)
		})
	}
	if l.kind != "" {
		modKind[copyObj.ObjScriptID()] = l.kind
		modTier[copyObj.ObjScriptID()] = next
	}
	if !free && h != nil {
		h.ChangeGold(-cost)
	}
	ns.Effect(effect.SPARK_EXPLOSION, at, ns.Ptf(90, 0))
	ns.Effect(effect.YELLOW_SPARKS, at, nil)
	ns.Effect(effect.WHITE_FLASH, at, nil)
	lv := modSmithLevel()
	modSmithXP += next
	up := ""
	if modSmithLevel() > lv {
		up = fmt.Sprintf(" Smithing level up: %d!", modSmithLevel())
	}
	if free {
		cost = 0
	}
	modSmithSay(fmt.Sprintf("Forged: %s %s (tier %d) for %d gold. Smithing level %d, xp %d.%s",
		modTierName[next], l.label, next, cost, modSmithLevel(), modSmithXP, up))
	return "forged"
}

func modForgeFrame() {
	h := ns.GetHost()
	if h == nil || modAnvil == nil {
		return
	}
	if modDist(h.Pos(), modPlate) < 34 {
		modOnPlate++
		if modOnPlate == 20 {
			modForgeStrike(h, false)
		}
	} else {
		modOnPlate = 0
	}
	if modSmith != nil && ns.Frame() > modSmithTalk && modDist(h.Pos(), modSmith.Pos()) < 110 {
		modSmithTalk = ns.Frame() + 30*20
		lv := modSmithLevel()
		nextXP := "max"
		if lv+1 < len(modLevelXP) {
			nextXP = fmt.Sprint(modLevelXP[lv+1])
		}
		modSmith.ChatStrTimer(fmt.Sprintf("Smithing level %d (xp %d/%s). Fine %dg, superb %dg, masterwork %dg.",
			lv, modSmithXP, nextXP, modCost(1), modCost(2), modCost(3)), ns.Seconds(6))
	}
}

// ---- start, frames, self-test ------------------------------------------------------------------------------------

var (
	modStarted bool
	modFrames  int
	modTestAt  = 120
)

// StartMods runs once the config has named everything (config's setUpMods).
func StartMods() {
	if modStarted {
		return
	}
	modStarted = true
	println("modlab: started:", len(modKind), "power weapons,", len(modBosses), "creatures,", len(modLines), "forge lines")
}

func init() {
	ns.OnFrame(modFrame)
}

func modFrame() {
	if !modStarted {
		return
	}
	modFrames++
	if modFrames%10 == 0 { // every creature reports its hits (minions and respawns too)
		for _, m := range ns.FindAllObjects(ns.ObjCondFunc(func(o ns.Obj) bool { return o.HasClass(class.MONSTER) && modAlive(o) })) {
			if _, ok := modWatch[m.ObjScriptID()]; !ok && !modLeave[m.ObjScriptID()] {
				modWatchObj(m)
			}
		}
	}
	if modFrames == modTestAt && ns.GetHost() == nil {
		modRunSelfTest()
	}
	modWeaponFrame()
	modBoomerangFrame()
	modShoveFrame()
	for _, b := range modBosses {
		b.frame()
	}
	modForgeFrame()
	if modSelfTest {
		modTestFrame()
	}
	if modSelfTest && modFrames == modTestAt+360 {
		modSelfTestReport()
	}
}

func modTry(step string, fn func() string) {
	defer func() {
		if r := recover(); r != nil {
			println("modlab selftest:", step, "PANIC:", fmt.Sprint(r))
		}
	}()
	println("modlab selftest:", step, "ok", fn())
}

func modBossByKind(kind string) *modBoss {
	for _, b := range modBosses {
		if b.kind == kind && b.o != nil {
			return b
		}
	}
	return nil
}


// ModTestCell names the waypoint in the sealed room where the self-test stands its stand-ins (kit/mods.py test_cell).
var modTestSpot string

func ModTestCell(waypoint string) {
	modTestSpot = waypoint
}

type modTestStep struct {
	at   int
	name string
	fn   func() string
}

var (
	modTestSteps []modTestStep
	modTestStart int
)

func modTestFrame() {
	t := modFrames - modTestStart
	for _, st := range modTestSteps {
		if st.at == t {
			modTry(st.name, st.fn)
		}
	}
}

func modHP(o ns.Obj) string {
	if o == nil {
		return "gone"
	}
	return fmt.Sprintf("%d/%d", o.CurrentHealth(), o.MaxHealth())
}

// modRunSelfTest: every power, ability and forge step once, against stand-ins (no player on a dedicated server),
// a step every few frames (an object made this frame is found by searches from the next).
func modRunSelfTest() {
	modSelfTest = true
	modTestStart = modFrames
	println("modlab: no host player: running the self-test")
	var at ns.Pointf
	var wp ns.WaypointObj
	if modTestSpot != "" {
		wp = ns.Waypoint(modTestSpot)
	}
	if wp != nil { // a sealed room off the map's play area
		at = wp.Pos()
	} else if len(modBosses) > 0 { // no test cell: beside the first creature's post
		at = ns.Ptf(modBosses[0].home.X+60, modBosses[0].home.Y)
	} else if modAnvil != nil {
		at = modAnvil.Pos()
	} else {
		println("modlab selftest: nowhere to stand the stand-ins (no ModTestSpot waypoint, creature or anvil): skipped")
		modSelfTest = false
		return
	}
	var wielder, victim, victim2 ns.Obj
	steps := []modTestStep{
		{1, "stand-ins", func() string {
			wielder = ns.CreateObject("GruntAxe", at)
			modTestFoe = ns.CreateObject("GruntAxe", ns.Ptf(at.X+30, at.Y))
			victim = ns.CreateObject("OgreBrute", ns.Ptf(at.X+60, at.Y+10))
			victim2 = ns.CreateObject("OgreBrute", ns.Ptf(at.X+120, at.Y+30))
			for _, o := range []ns.Obj{wielder, modTestFoe, victim, victim2} {
				if o == nil {
					panic("stand-in creature not created")
				}
			}
			modProtected[wielder.ObjScriptID()] = true
			modProtected[modTestFoe.ObjScriptID()] = true
			for _, v := range []ns.Obj{victim, victim2} {
				v.SetMaxHealth(2000)
				v.SetHealth(2000)
			}
			return "victim " + modHP(victim)
		}},
		{3, "power weapons found by name", func() string {
			held := 0
			for _, o := range modWeaponObjs {
				if o.GetHolder() != nil {
					held++
				}
			}
			return fmt.Sprint(len(modWeaponObjs), " found, ", held, " of them inside a container")
		}},
		{5, "IsHit names the attacker", func() string {
			w := modWatchObj(victim)
			w.onHit = append(w.onHit, func(a ns.Obj) {
				println("modlab selftest: IsHit event on the victim: attacker is the wielder:", modSame(a, wielder))
			})
			before := victim.CurrentHealth()
			victim.Damage(wielder, 7, damage.BLADE)
			return fmt.Sprintf("victim hp %d -> %d", before, victim.CurrentHealth())
		}},
		{7, "enchant probe", func() string {
			victim.Enchant(enchant.SLOWED, ns.Frames(90))
			wielder.Enchant(enchant.HASTED, ns.Seconds(3))
			return fmt.Sprint("victim slowed (frames) ", victim.HasEnchant(enchant.SLOWED), ", wielder hasted (seconds) ",
				wielder.HasEnchant(enchant.HASTED))
		}},
		{8, "damage probe: no source", func() string {
			before := victim.CurrentHealth()
			victim.Damage(nil, 9, damage.BLADE)
			return fmt.Sprintf("victim hp %d -> %d", before, victim.CurrentHealth())
		}},
		{10, "W2 chakram fan", func() string { modChakramFan(wielder, 1, 0, 1); return fmt.Sprint(len(modBoomerangs), " in flight") }},
		{12, "W3 quake", func() string {
			modOnBlow("quake", 1, wielder, victim)
			return "victim2 " + modHP(victim2) + ", shoves " + fmt.Sprint(len(modShoves))
		}},
		{30, "W4 chain lightning", func() string {
			dx, dy, _ := modDir(wielder.Pos(), victim.Pos())
			n := modChainLightning(wielder, wielder.Pos(), dx, dy, 1)
			return fmt.Sprint(n, " struck, victim ", modHP(victim), ", victim2 ", modHP(victim2))
		}},
		{32, "W5 blood", func() string {
			wielder.SetHealth(wielder.MaxHealth() / 2)
			b := wielder.CurrentHealth()
			modOnBlow("blood", 0, wielder, victim)
			modFeast(wielder)
			return fmt.Sprintf("wielder hp %d -> %d, hasted %v", b, wielder.CurrentHealth(), wielder.HasEnchant(enchant.HASTED))
		}},
		{34, "W6 frost x3", func() string {
			for k := 0; k < 3; k++ {
				modOnBlow("frost", 0, wielder, victim2)
			}
			return fmt.Sprint("slowed ", victim2.HasEnchant(enchant.SLOWED), ", frozen ", victim2.HasEnchant(enchant.FREEZE),
				", held ", victim2.HasEnchant(enchant.HELD))
		}},
		{40, "monsters wake", func() string {
			for _, b := range modBosses {
				if b.o != nil && !b.trainee {
					b.engage()
				}
			}
			return ""
		}},
		{42, "M1 ogre lord throw", func() string {
			b := modBossByKind("ogrelord")
			if b == nil {
				return "absent"
			}
			b.o.SetHealth(b.hp / 3) // below half: the fan of three
			b.ogreThrow(modTestFoe)
			return fmt.Sprint(len(modBoomerangs), " in flight")
		}},
		{44, "M2 crab snap", func() string {
			b := modBossByKind("crab")
			if b == nil {
				return "absent"
			}
			before := modTestFoe.CurrentHealth()
			b.crabSnap(modTestFoe)
			return fmt.Sprintf("foe hp %d -> %d, foe held %v, shell open %d frames", before, modTestFoe.CurrentHealth(),
				modTestFoe.HasEnchant(enchant.HELD), b.exposed)
		}},
		{46, "M3 bone caller raise", func() string {
			b := modBossByKind("bonecaller")
			if b == nil {
				return "absent"
			}
			b.raise(modTestFoe)
			return fmt.Sprint(len(b.minions), " minions")
		}},
		{48, "M4 ember brood", func() string {
			b := modBossByKind("embermother")
			if b == nil {
				return "absent"
			}
			b.brood(modTestFoe)
			b.brood(modTestFoe)
			return fmt.Sprint(len(b.minions), " imps")
		}},
		{50, "M5 duelist blink", func() string {
			b := modBossByKind("duelist")
			if b == nil {
				return "absent"
			}
			return fmt.Sprint("blinked ", b.blink(modTestFoe))
		}},
		{58, "M4 an imp dies (flame burst)", func() string {
			b := modBossByKind("embermother")
			if b == nil || len(b.minions) == 0 {
				return "no imps"
			}
			im := b.minions[0].o
			im.Damage(nil, 500, damage.BLADE)
			return "imp " + modHP(im)
		}},
		{60, "M5 duelist killed (respawn check)", func() string {
			b := modBossByKind("duelist")
			if b == nil {
				return "absent"
			}
			b.respawn = 150
			b.o.Damage(nil, 5000, damage.BLADE)
			return "duelist " + modHP(b.o)
		}},
		{90, "M3 bone caller killed (minions crumble)", func() string {
			b := modBossByKind("bonecaller")
			if b == nil {
				return "absent"
			}
			b.respawn = 150
			b.o.Damage(nil, 5000, damage.BLADE)
			return "bone caller " + modHP(b.o)
		}},
		{120, "M2 shell turns blows", func() string {
			b := modBossByKind("crab")
			if b == nil {
				return "absent"
			}
			b.o.Damage(nil, 60, damage.BLADE)
			return "crab " + modHP(b.o) + " (the next frame gives back two thirds)"
		}},
		{122, "M2 shell after two frames", func() string {
			b := modBossByKind("crab")
			if b == nil {
				return "absent"
			}
			return "crab " + modHP(b.o)
		}},
	}
	// the forge: a plain weapon through every tier, then a sword melted down
	if modAnvil != nil {
		var line *modLine
		for _, l := range modLines {
			if l.kind == "" {
				line = l
				break
			}
		}
		if line != nil {
			steps = append(steps, modTestStep{20, "S1 forge: a " + line.base + " by the anvil", func() string {
				return fmt.Sprint(ns.CreateObject(line.base, modAnvil.Pos()) != nil)
			}})
			for k := 0; k < 4; k++ {
				steps = append(steps, modTestStep{30 + 10*k, "S1 forge strike", func() string {
					r := modForgeStrike(nil, true)
					modSmithXP += 3 // the self-test levels the smith to reach every tier
					return r
				}})
			}
			steps = append(steps, modTestStep{75, "S1 forge: clear the anvil, lay a sword", func() string {
				if it := modOnAnvil(); it != nil {
					it.SetPos(ns.Ptf(it.Pos().X+150, it.Pos().Y+150))
				}
				return fmt.Sprint(ns.CreateObject("Sword", modAnvil.Pos()) != nil)
			}})
			steps = append(steps, modTestStep{85, "S1 forge strike (melt)", func() string { return modForgeStrike(nil, true) }})
		}
	}
	modTestSteps = steps
}

func modSelfTestReport() {
	resp := 0
	for _, b := range modBosses {
		if b.o != nil {
			resp++
		}
	}
	println("modlab selftest: after 12 s:", len(modBoomerangs), "chakrams in flight,", resp, "of", len(modBosses),
		"creatures standing, smithing xp", modSmithXP, "- flame bursts", modBursts, "- skeletons crumbled", modCrumbled)
	println("modlab selftest: done")
}
