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
//            weapon runs the power (the Warp Hammer, the Flamebrand Wave, Frostbite, the Stormcaller's lightning);
//            a kill is seen by the creature's Death event (Bloodthirst). Other powers watch what the weapon makes:
//            the Chakram Storm's thrown chakram, the blue ring of the Flamebrand of Mana.
//   Monsters new creatures built from the game's own, each with a scripted ability set; they wait frozen in their
//            pen until the player comes in (or strikes them), and come back a while after they die. A monster's
//            blow on the player raises no event: the script reads it from the player's health (modFoeFrame).
//   Smithing a forge: lay a weapon by the anvil and step on the forge plate. A weapon of a known line becomes the
//            next tier, which is a copy made in the map (with the game's own enchantments: WeaponPower, Material,
//            FireRing, Impact, Stun...) kept in a sealed vault and brought to the anvil. The smith's level grows
//            with every piece worked; it opens the higher tiers and lowers the price.
//
// Projectiles flown by the script (chakrams, the Ogre Lord's harpoon) are ownerless and have NoCollide and NoUpdate set: the game's own
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
	"github.com/noxworld-dev/noxscript/ns/v4/spell"
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
	lastKind   string // the power of the host's last blow on it, its tier, and when (for on-kill powers)
	lastTier   int
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
	OnObjEvent(o, ns.EventIsHit, func() {
		if w.dead {
			return
		}
		a := ns.GetCaller()
		for _, f := range w.onHit {
			f(a)
		}
	})
	OnObjEvent(o, ns.EventDeath, func() {
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
	if f := modFoe(); f != nil && modSame(o, f) {
		modFoeSkip = ns.Frame() + 1 // the script's own wound, not a monster's blow (modFoeFrame)
	}
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

// ModWeapon names a weapon with a power: "flame" (W1, the game's own FireRing enchantment: no script), "manaflame"
// (W1B, the game's BlueFireRing plus a slow), "flamewave" (W1C), "chakram" (W2), "warp" (W3), "storm" (W4), "blood"
// (W5), "frost" (W6). tier: 0-3 (what it changes is said at each power).
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

// The self-test's stand-in wielder and the power it pretends to hold (the weapon frame powers run for it as they
// would for the host).
var (
	modTestWielder ns.Obj
	modTestKind    string
	modTestTier    int
)

func modWielder() (ns.Obj, string, int) {
	if modSelfTest {
		if modTestWielder == nil || modTestKind == "" {
			return nil, "", 0
		}
		return modTestWielder, modTestKind, modTestTier
	}
	h := ns.GetHost()
	if h == nil {
		return nil, "", 0
	}
	k, t := modWielded(h)
	return h, k, t
}

// A blow landed on a watched creature: the host's power runs if its weapon has one.
//
// The event's caller is the creature's last attacker as the game records it (OpenNox unit_ai.go: Obj130), which for
// a blow is the damage's direct source when there is one (legacy GAME3_2.c: the weapon, or a missile) and otherwise
// its owner: the host, the weapon it holds, or something it owns all count. The game raises the event from the
// creature's own update and only while it lives, so a blow that kills raises none (the Bloodthirst's kill is found
// by its Death event instead, modHostKill).
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
	if kind == "storm" && !modSame(attacker, h) {
		return // the Stormcaller answers its own lightning (no missile, no weapon: the caster is the source)
	}
	w.lastKind, w.lastTier, w.lastHitAt = kind, tier, ns.Frame()
	modOnBlow(kind, tier, h, w.o)
}

// modOnBlow: the powers that answer a landed blow, wielder striking target.
func modOnBlow(kind string, tier int, src, target ns.Obj) {
	switch kind {
	case "warp": // W3
		modWarp(src, target, tier)
	case "flamewave": // W1C
		modFlameWave(src, target, tier)
	case "storm": // W4
		modStormStrike(src, target, tier)
	case "frost": // W6
		modFrost(src, target, tier)
	}
}

// ---- W1B and W1C: the Flamebrand's variants ----

// The flames of the game's ring of fire (Nox's Cleansing Flame spell, which the FireRing and BlueFireRing
// enchantments cast at the wielder on every swing: OpenNox modifiers.go nox_xxx_fireRingEffect_4E05B0), smallest
// first.
var modRingFlames = ns.HasTypeName{"SmallFlameCleanse", "MediumFlameCleanse", "FlameCleanse", "LargeFlameCleanse"}
var modBlueRingFlames = ns.HasTypeName{"SmallBlueFlameCleanse", "MediumBlueFlameCleanse", "BlueFlameCleanse", "LargeBlueFlameCleanse"}

// W1B: a creature the wielder's blue ring touches is slowed for 3 s and loses a little life. (The flames' own
// ManaDrainCollide drains mana from players only: Nox's creatures have none, so the script's drain stands in.)
var modManaTouched = map[int]int{}

func modManaFlameFrame(h ns.Obj, tier int) int {
	n := 0
	for _, f := range ns.FindAllObjects(modBlueRingFlames) {
		if !f.HasOwner(h) {
			continue
		}
		for _, m := range ns.FindAllObjects(ns.InCirclef{Center: f, R: 28}, modTargetCond) {
			id := m.ObjScriptID()
			if ns.Frame() < modManaTouched[id] || modSame(m, h) {
				continue
			}
			modManaTouched[id] = ns.Frame() + 20
			m.Enchant(enchant.SLOWED, ns.Seconds(3))
			ns.Effect(effect.CYAN_SPARKS, m, nil)
			modStrike(h, m, 1+tier, damage.DRAIN)
			n++
		}
	}
	return n
}

// W1C: the Flamebrand Wave. Every blow that lands sends two waves of fire over the quarter circle facing the creature
// struck, the second 8 frames behind the first. The waves are the game's plain flames (SmallFlame, MediumFlame,
// Flame by tier), owned by the wielder so their burns are his and do not hurt him, laid an arc at a time outward;
// each wave burns a creature in it once. Two blows' waves burn at once: the game's own ring refuses a new ring
// while the old one's flames last (legacy GAME4_2.c nox_xxx_spellCastCleansingFlame_52D5C0, "TooManySpells"), these
// are the script's.
//
// Why on a blow and not on every swing as the ring is: no script event fires on a swing. The one sign of a swing a
// script can see is the FireRing enchantment's ring itself, and putting that ring out the frame after does not
// take it off the player's screen: the game sends each ring flame to the client once, as a flame for the client
// to move by itself (legacy GAME4_2.c nox_xxx_netClientPredictLinear_523530, MSG_CLIENT_PREDICT_LINEAR), and the
// client keeps drawing it. A play test (2026-10-13) showed that ghost ring round every swing, so the wave answers
// the blow instead.
type modWave struct {
	src        ns.Obj
	o          ns.Pointf
	ang        float64
	tier       int
	t          int
	hit0, hit1 map[int]bool
}

var (
	modWaves     []*modWave
	modWaveReady int
	modWaveFlame = [][]string{{"SmallFlame"}, {"SmallFlame", "MediumFlame"}, {"MediumFlame"}, {"Flame", "MediumFlame"}}
	modWaveDmg   = []int{5, 7, 9, 12}
	modWaveMade  int // flames laid (the self-test reads it)
)

func modFlameWave(src, target ns.Obj, tier int) bool {
	if ns.Frame() < modWaveReady {
		return false
	}
	modWaveReady = ns.Frame() + 5
	dx, dy, _ := modDir(src.Pos(), target.Pos())
	modWaves = append(modWaves, &modWave{src: src, o: src.Pos(), ang: math.Atan2(float64(dy), float64(dx)), tier: tier,
		hit0: map[int]bool{}, hit1: map[int]bool{}})
	return true
}

func modWavesFrame() {
	keep := modWaves[:0]
	for _, w := range modWaves {
		for k := 0; k < 2; k++ {
			i := w.t - 8*k
			if i >= 0 && i%2 == 0 && i/2 <= 6 {
				modWaveArc(w, k, float32(34+20*(i/2)))
			}
		}
		w.t++
		if w.t <= 22 {
			keep = append(keep, w)
		}
	}
	modWaves = keep
}

// half the wave's arc, with a little grace: pi/4 + 0.25 (a literal: yaegi refuses math.Pi/4+0.25, "mismatched
// types untyped float64 and untyped float")
const modQuarterArc = 1.0354

func modAngDiff(a, b float64) float64 {
	d := math.Mod(a-b+3*math.Pi, 2*math.Pi) - math.Pi
	return math.Abs(d)
}

func modWaveArc(w *modWave, k int, r float32) {
	types := modWaveFlame[w.tier]
	n := 3 + int(r/45)
	for j := 0; j < n; j++ {
		a := w.ang - math.Pi/4 + math.Pi/2*(float64(j)+0.5)/float64(n)
		p := ns.Ptf(w.o.X+r*float32(math.Cos(a)), w.o.Y+r*float32(math.Sin(a)))
		if ns.FindClosestWall(p, ns.InCirclef{Center: p, R: 10}) != nil {
			continue
		}
		f := ns.CreateObject(types[(j+k)%len(types)], p)
		if f == nil {
			continue
		}
		if modAlive(w.src) {
			f.SetOwner(w.src)
		}
		f.DeleteAfter(ns.Frames(10))
		modWaveMade++
	}
	hit := w.hit0
	if k == 1 {
		hit = w.hit1
	}
	for _, m := range ns.FindAllObjects(ns.InCirclef{Center: w.o, R: float64(r + 18)}, modTargetCond) {
		id := m.ObjScriptID()
		if hit[id] || modSame(m, w.src) {
			continue
		}
		dx, dy, d := modDir(w.o, m.Pos())
		if d < r-24 || modAngDiff(math.Atan2(float64(dy), float64(dx)), w.ang) > modQuarterArc {
			continue
		}
		hit[id] = true
		modStrike(w.src, m, modWaveDmg[w.tier], damage.FLAME)
	}
}

// ---- W2: the Chakram Storm ----

// The fan's angles by tier: 1 two more chakrams, 2 four, 3 six in a wider fan (0: four, the first version).
var modFanDeg = [][]float64{{-30, -15, 15, 30}, {-15, 15}, {-24, -12, 12, 24}, {-48, -32, -16, 16, 32, 48}}

// W2: the Chakram Storm's throw sends more chakrams fanning out beside it, each coming back to the thrower.
func modChakramFan(h ns.Obj, dx, dy float32, tier int) int {
	if tier < 0 || tier > 3 {
		tier = 0
	}
	base := math.Atan2(float64(dy), float64(dx))
	for _, deg := range modFanDeg[tier] {
		a := base + deg*math.Pi/180
		modThrow(h, func() ns.Obj {
			if modSelfTest {
				return h
			}
			return ns.GetHost()
		}, h.Pos(), float32(math.Cos(a)), float32(math.Sin(a)), 12, float32(240+30*tier), 10+3*tier, false)
	}
	return len(modFanDeg[tier])
}

// ---- W3: the Warp Hammer ----

// A blow that lands warps the wielder a short way back from the creature struck (100 px, 15 more each tier), or
// aside when a wall is in the way; at most once a second.
var modWarpReady int

func modWarp(src, target ns.Obj, tier int) bool {
	if ns.Frame() < modWarpReady {
		return false
	}
	p, tp := src.Pos(), target.Pos()
	dx, dy, _ := modDir(tp, p) // from the creature back through the wielder
	base := math.Atan2(float64(dy), float64(dx))
	dist := float32(100 + 15*tier)
	for _, deg := range []float64{0, 35, -35, 70, -70, 110, -110} {
		a := base + deg*math.Pi/180
		for _, f := range []float32{1, 0.7, 0.45} {
			to := ns.Ptf(p.X+float32(math.Cos(a))*dist*f, p.Y+float32(math.Sin(a))*dist*f)
			if !modClear(p, to, 14) {
				continue
			}
			modWarpReady = ns.Frame() + 30
			ns.Effect(effect.TELEPORT, p, nil)
			ns.Effect(effect.SMOKE_BLAST, p, nil)
			src.SetPos(to)
			ns.Effect(effect.TELEPORT, to, nil)
			return true
		}
	}
	return false
}

// modClear: no wall within r px of the way from a to b (sampled every 14 px from 16 px out), so a warp or teleport
// never passes through a wall into another room.
func modClear(a, b ns.Pointf, r float32) bool {
	dx, dy, d := modDir(a, b)
	s := float32(16)
	if s > d {
		s = d
	}
	for {
		q := ns.Ptf(a.X+dx*s, a.Y+dy*s)
		if ns.FindClosestWall(q, ns.InCirclef{Center: q, R: float64(r)}) != nil {
			return false
		}
		if s >= d {
			return true
		}
		s += 14
		if s > d {
			s = d
		}
	}
}

// ---- W4: the Stormcaller ----

// The Stormcaller is a Lightning Staff (the game's ForceWand), whose use casts the game's chain lightning
// (thing.bin: WandCastUse 60 1.0 SPELL_CHAIN_LIGHTNING) and draws it in the engine's own colour, which no script
// can change. So the moment that lightning first strikes a creature (its IsHit names the wielder himself), the
// script ends it (the game ends a chain lightning whose caster carries ENCHANT_RUN: legacy GAME4_3.c
// nox_xxx_onFrameLightning_52F8A0; the wielder gets two frames of it) and throws its own chain in its place: green
// beams, up to four creatures, each strike three quarters of the one before, every creature struck poisoned (the
// game's Poison spell at level 4 + tier: the game's poison takes 1 health every 128 >> (level - 1) frames, a second
// after it takes hold, and wanes a level every 1000 frames: OpenNox server.go; the game tints a poisoned creature
// green). The beam is the game's CHARM ray, a stream of green sparks drawn like the lightning's blue ones, renewed
// every 2 frames for 0.8 s along each link of the chain. (The GREEN_BOLT effect NoxScript also offers draws
// nothing in OpenNox alpha13's client: a play test drew it beside LIGHTNING and CHARM, 2026-10-13.)
var (
	modStormReady int
	modPoisoned   int // the self-test reads it
	modBeams      []*modBeam
)

type modBeam struct {
	from, to ns.Obj
	at       ns.Pointf // where the link starts when from is gone
	until    int
}

func modBeamsFrame() {
	keep := modBeams[:0]
	for _, b := range modBeams {
		if ns.Frame() > b.until || !modAlive(b.to) {
			continue
		}
		if (b.until-ns.Frame())%2 == 0 {
			a := b.at
			if b.from != nil && !b.from.Flags().Has(object.FlagDestroyed) {
				a = b.from.Pos()
			}
			ns.Effect(effect.CHARM, a, b.to)
		}
		keep = append(keep, b)
	}
	modBeams = keep
}

func modStormStrike(src, first ns.Obj, tier int) int {
	if ns.Frame() < modStormReady || !modAlive(first) {
		return 0
	}
	modStormReady = ns.Frame() + 20
	src.Enchant(enchant.RUN, ns.Frames(2))
	return modGreenChain(src, first, tier)
}

func modGreenChain(src, first ns.Obj, tier int) int {
	prev := src.Pos()
	from := src
	cur := first
	dmg := 18 + 4*tier
	struck := map[int]bool{}
	n := 0
	for cur != nil && n < 4 {
		ns.Effect(effect.CHARM, prev, cur)
		modBeams = append(modBeams, &modBeam{from: from, to: cur, at: prev, until: ns.Frame() + 24})
		from = cur
		struck[cur.ObjScriptID()] = true
		modStrike(src, cur, dmg, damage.ELECTRIC)
		modPoison(cur, 4+tier)
		n++
		prev = cur.Pos()
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
		cur = next
	}
	return n
}

// modPoison: the game's Poison spell on o, cast from o itself (a creature casting at itself skips the spell's flight).
func modPoison(o ns.Obj, lvl int) {
	if !modAlive(o) {
		return
	}
	ns.CastSpellLvl(spell.POISON, lvl, o, o)
	modPoisoned++
}

// ---- W5: the Bloodthirst ----

// A watched creature died: the Bloodthirst feeds the host when he killed it: either his blow landed on it in the last
// 1.5 s, or (a killing blow raises no IsHit) he stands within reach of it holding the Bloodthirst.
func modHostKill(w *modWatched) {
	h := ns.GetHost()
	if h == nil || w.o == nil {
		return
	}
	kind, tier := modWielded(h)
	recent := w.lastKind == "blood" && ns.Frame()-w.lastHitAt <= 45
	if recent {
		tier = w.lastTier
	}
	if recent || (kind == "blood" && modDist(h.Pos(), w.o.Pos()) < 130) {
		modFeast(h, tier)
	}
}

var (
	modShieldGen  int
	modInvisUntil int // the tier-2 feast's invisibility holds until this frame
	modInvisObj   ns.Obj
)

// modFeast: the Bloodthirst's reward for a kill, by tier: 1 (and 0) five seconds of haste; 2 haste and invisibility
// for five seconds (the game ends invisibility at its wearer's next attack: a play test saw it gone by the next kill,
// so for those five seconds the script lays it again whenever the game takes it off, modInvisFrame); 3 a force
// field (the game's Force Field spell, SPELL_SHIELD, at level 3: each blow on its wearer is halved and the half it
// turns comes off the field's 50, gamedata ShieldHealth, so it breaks once it has soaked 50; a blow that would kill
// leaves 2 health and breaks it), which the script ends after 15 s if it still stands.
func modFeast(h ns.Obj, tier int) string {
	ns.Effect(effect.VAMPIRISM, h, h)
	switch {
	case tier >= 3:
		ns.CastSpellLvl(spell.SHIELD, 3, h, h)
		modShieldGen++
		g := modShieldGen
		ns.NewTimer(ns.Seconds(15), func() {
			if g == modShieldGen && h != nil {
				h.EnchantOff(enchant.SHIELD)
			}
		})
		return "force field"
	case tier == 2:
		h.Enchant(enchant.HASTED, ns.Seconds(5))
		h.Enchant(enchant.INVISIBLE, ns.Seconds(5))
		modInvisObj, modInvisUntil = h, ns.Frame()+150
		return "haste and invisibility"
	default:
		h.Enchant(enchant.HASTED, ns.Seconds(5))
		return "haste"
	}
}

func modInvisFrame() {
	if modInvisObj == nil || ns.Frame() >= modInvisUntil || !modAlive(modInvisObj) {
		return
	}
	if !modInvisObj.HasEnchant(enchant.INVISIBLE) {
		modInvisObj.Enchant(enchant.INVISIBLE, ns.Frames(modInvisUntil-ns.Frame()))
	}
}

// ---- W6: Frostbite ----

// Every blow slows the creature 4 s. The third blow on it within 5 s freezes it solid for 3 s (FREEZE and HELD:
// stunned); at tier 2 a mana flame burns under it while it stands frozen, at tier 3 a fire.
func modFrost(src, target ns.Obj, tier int) {
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
	if w.frostCount < 3 {
		return
	}
	w.frostCount = 0
	target.Enchant(enchant.FREEZE, ns.Seconds(3))
	target.Enchant(enchant.HELD, ns.Seconds(3))
	ns.Effect(effect.WHITE_FLASH, target, nil)
	switch {
	case tier == 2:
		modUnderFlame(src, target, "MediumBlueFlame", true)
	case tier >= 3:
		modUnderFlame(src, target, "MediumFlame", false)
	}
	if !modSelfTest {
		modSay("Frostbite: frozen solid!")
	}
}

// A flame laid under a stunned creature for 3 s, owned by the wielder. The flame's own touch is the game's (fire
// burns; a blue flame drains a player's mana), but a creature held still in a still flame is not touched again, so
// the script burns it every 10 frames while it stands in it: 4 fire damage, or 2 for the mana flame (Nox's creatures
// have no mana to burn).
type modBurn struct {
	flame, target, src ns.Obj
	mana               bool
	until              int
}

var (
	modBurns    []*modBurn
	modBurnHits int // the self-test reads it
)

func modUnderFlame(src, target ns.Obj, typ string, mana bool) {
	f := ns.CreateObject(typ, target.Pos())
	if f == nil {
		return
	}
	if modAlive(src) {
		f.SetOwner(src)
	}
	f.DeleteAfter(ns.Seconds(3))
	modBurns = append(modBurns, &modBurn{flame: f, target: target, src: src, mana: mana, until: ns.Frame() + 90})
}

func modBurnsFrame() {
	keep := modBurns[:0]
	for _, b := range modBurns {
		if ns.Frame() > b.until || !modAlive(b.target) {
			continue
		}
		if (b.until-ns.Frame())%10 == 0 && modDist(b.target.Pos(), b.flame.Pos()) < 30 {
			if b.mana {
				modStrike(b.src, b.target, 2, damage.DRAIN)
				ns.Effect(effect.CYAN_SPARKS, b.target, nil)
			} else {
				modStrike(b.src, b.target, 4, damage.FLAME)
			}
			modBurnHits++
		}
		keep = append(keep, b)
	}
	modBurns = keep
}

// Each frame: the powers that watch what the wielder's weapon does (the Flamebrand's variants, the Chakram Storm's
// throw), and the fires and waves already set going.
func modWeaponFrame() {
	if w, kind, tier := modWielder(); w != nil {
		if kind == "manaflame" && ns.Frame()%3 == 0 {
			modManaFlameFrame(w, tier)
		}
	}
	modWavesFrame()
	modBurnsFrame()
	modBeamsFrame()
	modInvisFrame()
	h := ns.GetHost()
	if h == nil {
		return
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
	t, t2, t3       int // ability timers
	buffAt          int // when its standing enchantments are next renewed
	exposed         int
	side            float32
	minions         []*modWatched
	ghosts          []*modWatched
	shielded        bool
	spawns          int
	hook            *modHook
	blade           int // the frame the Blink Duelist's second blade falls
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
	b.t, b.t2, b.t3, b.exposed, b.shielded, b.buffAt, b.blade = 0, 0, 0, 0, false, 0, 0
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
		b.buffs()
	}
}

// buffs: the standing enchantments of a monster, renewed every 10 s (each lasts 15 s): the Ember Matriarch's
// protection from fire (the game draws its red orbiting sparks) and vampirism (the game heals an attacker carrying it
// by a share of every blow it lands: legacy GAME3_2.c, VampirismCoeff), the Blink Duelist's haste and infravision.
func (b *modBoss) buffs() {
	if b.o == nil || ns.Frame() < b.buffAt {
		return
	}
	b.buffAt = ns.Frame() + 300
	switch b.kind {
	case "embermother":
		b.o.Enchant(enchant.PROTECT_FROM_FIRE, ns.Seconds(15))
		b.o.Enchant(enchant.VAMPIRISM, ns.Seconds(15))
	case "duelist":
		b.o.Enchant(enchant.HASTED, ns.Seconds(15))
		b.o.Enchant(enchant.INFRAVISION, ns.Seconds(15))
	}
}

// ModWake wakes the named boss now, as if the player had come near (a frozen unit takes no damage: an ally striking a
// sleeping boss did nothing, act 9's Vess at Morvaine, 2026-10-10)
func ModWake(name string) {
	for _, b := range modBosses {
		if b.name == name {
			b.engage()
		}
	}
}

func (b *modBoss) engage() {
	if b.o == nil || b.engaged {
		return
	}
	b.engaged = true
	b.o.Freeze(false)
	b.buffAt = 0 // enchantments laid on a frozen creature do not take: lay them now
	b.buffs()
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
	at := ns.Ptf(0, 0)
	if b.o != nil {
		at = b.o.Pos()
	}
	b.o = none
	b.engaged = false
	b.deadAt = ns.Frame()
	if b.hook != nil {
		b.hook.bolt.Delete()
		b.hook = nil
	}
	switch b.kind {
	case "bonecaller": // the bones (and the ghosts) crumble with their master
		for _, list := range [][]*modWatched{b.minions, b.ghosts} {
			for _, m := range list {
				if !m.dead {
					m.dead = true
					ns.Effect(effect.SMOKE_BLAST, m.o, nil)
					m.o.Delete()
					modCrumbled++
				}
			}
		}
		b.minions = nil // (one at a time: yaegi panics on "b.minions, b.ghosts = nil, nil", reflect: New(nil))
		b.ghosts = nil
	case "embermother": // her brood bursts into flame, and a great ring of fire bursts from her
		for _, m := range b.minions {
			if !m.dead && modAlive(m.o) {
				p := m.o.Pos()
				m.dead = true
				m.o.Delete()
				modFlameBurst(p)
			}
		}
		b.minions = nil
		modFireRing(at)
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
	if b.engaged {
		b.buffs()
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
	b.t3++
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

// ---- the foe's wounds: which monster's blow struck it ----

// The game raises no script event when a creature strikes the player, so the script watches the foe's health: a drop
// it did not deal itself (modHurt marks those) is the blow of the nearest living creature within 80 px. A boss that
// struck answers it (the Ember Matriarch's burning touch, the Blink Duelist's slow and second blade).
var (
	modFoeID, modFoeHP, modFoeSkip int
)

func modFoeFrame() {
	foe := modFoe()
	if foe == nil {
		modFoeID = 0
		return
	}
	hp := foe.CurrentHealth()
	if foe.ObjScriptID() != modFoeID {
		modFoeID, modFoeHP = foe.ObjScriptID(), hp
		return
	}
	drop := modFoeHP - hp
	modFoeHP = hp
	if drop <= 0 || ns.Frame() <= modFoeSkip {
		return
	}
	near := ns.FindClosestObject(foe, ns.InCirclef{Center: foe, R: 80}, modTargetCond)
	if near == nil {
		return
	}
	for _, b := range modBosses {
		if b.o != nil && modSame(b.o, near) {
			b.struck(foe, drop)
		}
	}
}

// struck: this boss's blow took drop health from its foe.
var modStruck = map[string]int{} // blows seen, by monster kind (the self-test and the play test read it)

func (b *modBoss) struck(foe ns.Obj, drop int) {
	modStruck[b.kind]++
	switch b.kind {
	case "embermother": // her blows burn: added fire, a burst of embers
		modHurt(foe, b.o, 5, damage.FLAME)
		ns.Effect(effect.SPARK_EXPLOSION, foe, ns.Ptf(35, 0))
		ns.Effect(effect.YELLOW_SPARKS, foe, nil)
	case "duelist": // each cut slows the foe 3 s; a second blade follows it
		foe.Enchant(enchant.SLOWED, ns.Seconds(3))
		if b.blade == 0 {
			b.blade = ns.Frame() + 7
		}
	}
}

// ---- M1 Ogre Lord ----

// M1 Ogre Lord: hurls boomerang chakrams, three in a fan once wounded below half, and catches them as they return;
// every 5 s, if he sees his foe 90-380 px off, he throws a harpoon that hooks the foe and drags it to him.
func (b *modBoss) ogreLord(foe ns.Obj) {
	b.hookFrame()
	if foe == nil || b.o == nil {
		return
	}
	p, fp := b.o.Pos(), foe.Pos()
	d := modDist(p, fp)
	sees := modSelfTest || b.o.CanSee(foe)
	// the harpoon wants only a clear line: the game's CanSee also asks which way he faces (a play test saw him walk
	// up to the player without a throw)
	if b.hook == nil && b.t3 >= 150 && d > 90 && d < 380 && (sees || modClear(p, fp, 8)) {
		b.t3 = 0
		b.harpoon(foe)
		return
	}
	if b.t < 70 || d > 420 || !sees || b.hook != nil {
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

// The Ogre Lord's harpoon: the game's HarpoonBolt, flown by the script (ownerless, NoCollide, NoUpdate: the game's
// harpoon code panics for an owner that is not a player, rules/WEAPONS.md) at 26 px a frame along the line to where
// the foe stood. It hooks the foe within 26 px of it (10 damage), then drags it to him for up to 1.2 s, until it is
// within 55 px. The warrior's harpoon pulls with HarpoonForce 10 (gamedata.bin) divided by the target's mass
// (OpenNox object_update.go applyForce); this one adds modHarpoonPull to the foe's force every frame whatever it
// weighs (Obj.PushTo), and holds it slowed while it is reeled so it cannot walk against the rope.
const modHarpoonPull = 9

type modHook struct {
	bolt   ns.Obj
	foe    ns.Obj
	pos    ns.Pointf
	dx, dy float32
	dist   float32
	reel   int
	hooked bool
	start  float32 // the foe's distance when hooked (the self-test reads it)
}

var modHooked, modReeled int // the self-test reads them

func (b *modBoss) harpoon(foe ns.Obj) {
	p := b.o.Pos()
	dx, dy, _ := modDir(p, foe.Pos())
	bolt := ns.CreateObject("HarpoonBolt", ns.Ptf(p.X+dx*24, p.Y+dy*24))
	if bolt == nil {
		return
	}
	bolt.FlagsEnable(object.FlagNoCollide | object.FlagNoUpdate)
	bolt.LookWithAngle(int(math.Atan2(float64(dy), float64(dx))/(2*math.Pi)*256) & 255)
	b.o.LookAtObject(foe)
	b.o.ChatStrTimer("Come here!", ns.Seconds(2))
	b.hook = &modHook{bolt: bolt, foe: foe, pos: bolt.Pos(), dx: dx, dy: dy}
}

func (b *modBoss) hookFrame() {
	k := b.hook
	if k == nil {
		return
	}
	if b.o == nil || !modAlive(k.foe) {
		k.bolt.Delete()
		b.hook = nil
		return
	}
	if !k.hooked {
		k.pos = ns.Ptf(k.pos.X+k.dx*26, k.pos.Y+k.dy*26)
		k.dist += 26
		k.bolt.SetPos(k.pos)
		if modDist(k.pos, k.foe.Pos()) < 26 {
			k.hooked, k.reel = true, 36
			k.start = modDist(k.foe.Pos(), b.o.Pos())
			modHooked++
			modHurt(k.foe, b.o, 10, damage.IMPALE)
			ns.Effect(effect.DAMAGE_POOF, k.foe, nil)
			if !modSelfTest {
				modSay("The Ogre Lord's harpoon drags you in!")
			}
		} else if k.dist > 420 || ns.FindClosestWall(k.pos, ns.InCirclef{Center: k.pos, R: 12}) != nil {
			k.bolt.Delete()
			b.hook = nil
		}
		return
	}
	d := modDist(k.foe.Pos(), b.o.Pos())
	if k.reel <= 0 || d < 55 {
		k.bolt.Delete()
		b.hook = nil
		b.o.Attack(k.foe)
		return
	}
	k.reel--
	modReeled++
	k.foe.PushTo(b.o, -modHarpoonPull) // a negative force pulls (server/object.go Push: obj.Pos() - p)
	if k.reel%10 == 0 {
		k.foe.Enchant(enchant.SLOWED, ns.Frames(12))
	}
	k.bolt.SetPos(k.foe.Pos())
}

// ---- M2 Giant Crab ----

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

// ---- M3 Bone Caller ----

// M3 Bone Caller: every 5 s he raises two Skeletons or one Skeleton Lord (six standing at most); while two or more
// stand, a bone ward turns half of every blow. Every 2.5 s, if he sees his foe within 400 px, he casts the game's
// Slow at it (while it is not slowed) or Magic Missile. He runs from a foe that comes within 190 px, and one that
// catches him (within 110 px) sees him teleport 150-260 px away, at most every 8 s, a Ghost rising where he stood
// (three at most). When he falls, his bones and ghosts crumble.
const modBoneMax, modGhostMax = 6, 3

func (b *modBoss) prune() {
	live := b.minions[:0]
	for _, m := range b.minions {
		if !m.dead {
			live = append(live, m)
		}
	}
	b.minions = live
	g := b.ghosts[:0]
	for _, m := range b.ghosts {
		if !m.dead {
			g = append(g, m)
		}
	}
	b.ghosts = g
}

func (b *modBoss) boneCaller(foe ns.Obj) {
	b.prune()
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
	if foe == nil {
		return
	}
	d := modDist(b.o.Pos(), foe.Pos())
	if b.t >= 150 && len(b.minions) < modBoneMax && d < 450 {
		b.t = 0
		b.raise(foe)
	}
	if b.t2 >= 75 && d < 400 && (modSelfTest || b.o.CanSee(foe)) {
		b.t2 = 0
		b.boneSpell(foe)
	}
	if d < 110 && b.t3 >= 240 {
		if b.boneTeleport(foe) {
			b.t3 = 0
		}
	} else if d < 190 && b.t%20 == 0 {
		b.o.Flee(foe, ns.Seconds(1))
	}
}

// raise: two Skeletons, or one Skeleton Lord (about two times in five, and always when only one more may stand).
func (b *modBoss) raise(foe ns.Obj) int {
	room := modBoneMax - len(b.minions)
	if room <= 0 {
		return 0
	}
	typ, n := "Skeleton", 2
	if room < 2 || ns.Random(0, 99) < 40 {
		typ, n = "SkeletonLord", 1
	}
	p := b.o.Pos()
	if n == 1 {
		b.o.ChatStrTimer("Rise, my lord!", ns.Seconds(1.5))
	} else {
		b.o.ChatStrTimer("Rise!", ns.Seconds(1.5))
	}
	made := 0
	for k := 0; k < n; k++ {
		a := ns.RandomFloat(0, 2*math.Pi)
		at := ns.Ptf(p.X+50*float32(math.Cos(float64(a))), p.Y+50*float32(math.Sin(float64(a))))
		if ns.FindClosestWall(at, ns.InCirclef{Center: at, R: 18}) != nil {
			at = p
		}
		s := ns.CreateObject(typ, at)
		if s == nil {
			continue
		}
		made++
		ns.Effect(effect.SMOKE_BLAST, at, nil)
		b.minions = append(b.minions, modWatchObj(s))
		if foe != nil {
			s.Attack(foe)
		}
	}
	return made
}

var modBoneSpells int // the self-test reads it

func (b *modBoss) boneSpell(foe ns.Obj) {
	b.o.LookAtObject(foe)
	if !foe.HasEnchant(enchant.SLOWED) {
		ns.CastSpellLvl(spell.SLOW, 3, b.o, foe)
	} else {
		ns.CastSpellLvl(spell.MAGIC_MISSILE, 3, b.o, foe)
	}
	modBoneSpells++
}

// boneTeleport: away from the foe, through no wall; a Ghost rises where he stood.
func (b *modBoss) boneTeleport(foe ns.Obj) bool {
	p, fp := b.o.Pos(), foe.Pos()
	dx, dy, _ := modDir(fp, p)
	base := math.Atan2(float64(dy), float64(dx))
	for _, deg := range []float64{0, 40, -40, 80, -80, 120, -120} {
		a := base + deg*math.Pi/180
		for _, r := range []float32{260, 200, 150} {
			to := ns.Ptf(p.X+float32(math.Cos(a))*r, p.Y+float32(math.Sin(a))*r)
			if !modClear(p, to, 16) {
				continue
			}
			ns.Effect(effect.TELEPORT, p, nil)
			b.o.SetPos(to)
			ns.Effect(effect.TELEPORT, to, nil)
			b.o.ChatStrTimer("You cannot catch me.", ns.Seconds(2))
			b.prune()
			if len(b.ghosts) < modGhostMax {
				if g := ns.CreateObject("Ghost", p); g != nil {
					ns.Effect(effect.SMOKE_BLAST, p, nil)
					b.ghosts = append(b.ghosts, modWatchObj(g))
					g.Attack(foe)
				}
			}
			return true
		}
	}
	return false
}

// ---- M4 Ember Matriarch ----

// M4 Ember Matriarch: births imps (five at most) that burst into flame when they die; she mends a little for every
// imp alive; her blows burn and drink life (struck, buffs); fire cannot hurt her (the game's protection from fire);
// when she falls her brood bursts and a great ring of fire spreads from her (modFireRing).
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

var modBursts, modCrumbled, modRingFlamesMade int

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

// modFireRing: a great ring of fire spreading from p: five rings of the game's flames, one every four frames, 50 to
// 190 px out, each burning 2 s; the foe takes 10 fire damage when a ring is laid over it (and the flames' own burn
// if it stands in them). (The game's own ring, the
// Cleansing Flame spell, is refused to a caster that still owns one, so two rings at once need the script's.)
type modRingFire struct {
	p ns.Pointf
	t int
}

var modRingFires []*modRingFire

func modFireRing(p ns.Pointf) {
	modRingFires = append(modRingFires, &modRingFire{p: p})
	ns.Effect(effect.SPARK_EXPLOSION, p, ns.Ptf(120, 0))
	ns.Effect(effect.JIGGLE, p, ns.Ptf(10, 0))
}

func modRingFireFrame() {
	keep := modRingFires[:0]
	for _, r := range modRingFires {
		if r.t%4 == 0 && r.t/4 < 5 {
			rad := float32(50 + 35*(r.t/4))
			n := int(2 * math.Pi * float64(rad) / 34)
			for j := 0; j < n; j++ {
				a := 2 * math.Pi * float64(j) / float64(n)
				q := ns.Ptf(r.p.X+rad*float32(math.Cos(a)), r.p.Y+rad*float32(math.Sin(a)))
				if ns.FindClosestWall(q, ns.InCirclef{Center: q, R: 10}) != nil {
					continue
				}
				typ := "Flame"
				if j%2 == 1 {
					typ = "LargeFlame"
				}
				if f := ns.CreateObject(typ, q); f != nil {
					f.DeleteAfter(ns.Seconds(2))
					modRingFlamesMade++
				}
			}
			if foe := modFoe(); foe != nil {
				if d := modDist(foe.Pos(), r.p); d > rad-22 && d < rad+22 {
					modHurt(foe, nil, 10, damage.FLAME)
				}
			}
		}
		r.t++
		if r.t < 20 {
			keep = append(keep, r)
		}
	}
	modRingFires = keep
}

// ---- M5 Blink Duelist ----

// M5 Blink Duelist: hasted and seeing in the dark (buffs); every 110 frames, his foe 70-340 px off, he steps through
// space to stand behind it and strikes; each of his cuts slows the foe 3 s and a second blade follows 7 frames later
// (6 damage, if the foe is still within 75 px): Nox's swordsman is drawn with a sword and a shield in every frame of
// his art, so the second sword is in the blows, not the picture. Once, when badly hurt, he wraps himself in a ward
// that nothing pierces for two seconds.
var modSecondBlades int // the self-test reads it

func (b *modBoss) duelist(foe ns.Obj) {
	if !b.shielded && b.o.CurrentHealth()*100 < b.hp*35 {
		b.shielded = true
		b.o.Enchant(enchant.INVULNERABLE, ns.Seconds(2))
		b.o.ChatStrTimer("You cannot touch me!", ns.Seconds(2))
	}
	if b.blade > 0 && ns.Frame() >= b.blade {
		b.blade = 0
		if foe != nil && modDist(b.o.Pos(), foe.Pos()) < 75 {
			modHurt(foe, b.o, 6, damage.BLADE)
			foe.Enchant(enchant.SLOWED, ns.Seconds(3))
			ns.Effect(effect.RICOCHET, foe, nil)
			modSecondBlades++
		}
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
	modFoeFrame()
	for _, b := range modBosses {
		b.frame()
	}
	modRingFireFrame()
	modForgeFrame()
	if modSelfTest {
		modTestFrame()
	}
	if modSelfTest && modFrames == modTestAt+420 {
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
	var wielder, victim, victim2, victim3, victim4, victim5, victim6, control, guard ns.Obj
	near := func(dx, dy float32) ns.Pointf { return ns.Ptf(at.X+dx, at.Y+dy) }
	var w5hp, hookStart, ctlhp int
	var pois, unpois ns.Obj
	steps := []modTestStep{
		{1, "stand-ins", func() string {
			wielder = ns.CreateObject("GruntAxe", at)
			modTestFoe = ns.CreateObject("GruntAxe", near(30, 0))
			victim = ns.CreateObject("OgreBrute", near(60, 10))
			victim2 = ns.CreateObject("OgreBrute", near(120, 30))
			victim3 = ns.CreateObject("OgreBrute", near(-150, -150)) // the W4 target: no other stand-in within the chain's reach
			victim4 = ns.CreateObject("OgreBrute", near(0, 90))      // in front of the W1C wave (south)
			victim5 = ns.CreateObject("OgreBrute", near(90, -90))    // the W1B target
			victim6 = ns.CreateObject("OgreBrute", near(0, -90))     // behind the W1C wave (north)
			control = ns.CreateObject("GruntAxe", near(-100, 100))   // the force field's control: the same blow, no field
			guard = ns.CreateObject("GruntAxe", near(-140, 140))     // wears the force field
			for _, o := range []ns.Obj{wielder, modTestFoe, victim, victim2, victim3, victim4, victim5, victim6, control, guard} {
				if o == nil {
					panic("stand-in creature not created")
				}
				o.SetMaxHealth(2000)
				o.SetHealth(2000)
			}
			modTestWielder = wielder
			modProtected[wielder.ObjScriptID()] = true
			modProtected[modTestFoe.ObjScriptID()] = true
			modProtected[control.ObjScriptID()] = true
			modProtected[guard.ObjScriptID()] = true
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
			wielder.LookWithAngle(64)
			return fmt.Sprint("victim slowed (frames) ", victim.HasEnchant(enchant.SLOWED), ", wielder facing 64 reads ",
				wielder.Direction())
		}},
		{8, "damage probe: no source", func() string {
			before := victim.CurrentHealth()
			victim.Damage(nil, 9, damage.BLADE)
			return fmt.Sprintf("victim hp %d -> %d", before, victim.CurrentHealth())
		}},
		{10, "W2 chakram fan by tier", func() string {
			a := modChakramFan(wielder, 1, 0, 1)
			b := modChakramFan(wielder, 1, 0, 2)
			c := modChakramFan(wielder, 1, 0, 3)
			return fmt.Sprint("tier 1/2/3 threw ", a, "/", b, "/", c, ", ", len(modBoomerangs), " in flight")
		}},
		{12, "W3 warp", func() string {
			p := wielder.Pos()
			ok := modWarp(wielder, victim, 1)
			return fmt.Sprintf("warped %v, %d px from where it struck, now %d px from the victim", ok,
				int(modDist(p, wielder.Pos())), int(modDist(victim.Pos(), wielder.Pos())))
		}},
		{14, "W3 back to the stand", func() string { wielder.SetPos(at); return "" }},
		{30, "W4 storm strike", func() string {
			n := modStormStrike(wielder, victim3, 1)
			return fmt.Sprint(n, " struck, the wielder's lightning cut (RUN) ", wielder.HasEnchant(enchant.RUN),
				", victim3 ", modHP(victim3), ", poison casts ", modPoisoned)
		}},
		{32, "W5 feast tiers 1 and 2", func() string {
			a := modFeast(wielder, 1)
			h1 := wielder.HasEnchant(enchant.HASTED)
			wielder.EnchantOff(enchant.HASTED)
			b := modFeast(wielder, 2)
			return fmt.Sprint(a, ": hasted ", h1, "; ", b, ": hasted ", wielder.HasEnchant(enchant.HASTED), ", invisible ",
				wielder.HasEnchant(enchant.INVISIBLE))
		}},
		{34, "W5 feast tier 3", func() string { return modFeast(guard, 3) }},
		{36, "W5 force field takes blows", func() string {
			w5hp, ctlhp = guard.CurrentHealth(), control.CurrentHealth()
			sh := guard.HasEnchant(enchant.SHIELD)
			guard.Damage(nil, 30, damage.BLADE)
			control.Damage(nil, 30, damage.BLADE)
			return fmt.Sprint("field ", sh, "; a 30 blow: with the field hp ", w5hp, " -> ", guard.CurrentHealth(),
				", the control without ", ctlhp, " -> ", control.CurrentHealth())
		}},
		{37, "W5 the field after 30", func() string {
			w5hp, ctlhp = guard.CurrentHealth(), control.CurrentHealth()
			guard.Damage(nil, 30, damage.BLADE)
			control.Damage(nil, 30, damage.BLADE)
			return fmt.Sprint("field ", guard.HasEnchant(enchant.SHIELD), "; another 30: with ", w5hp, " -> ", guard.CurrentHealth(),
				", control ", ctlhp, " -> ", control.CurrentHealth())
		}},
		{39, "W5 the field after 60", func() string {
			return fmt.Sprint("field ", guard.HasEnchant(enchant.SHIELD), ", guard ", modHP(guard))
		}},
		{38, "W6 frost x3 at tiers 2 and 3", func() string {
			for k := 0; k < 3; k++ {
				modOnBlow("frost", 2, wielder, victim)
				modOnBlow("frost", 3, wielder, victim2)
			}
			return fmt.Sprint("victim2 frozen ", victim2.HasEnchant(enchant.FREEZE), ", held ", victim2.HasEnchant(enchant.HELD),
				", flames burning ", len(modBurns))
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
		{46, "M3 bone caller raises up to six", func() string {
			b := modBossByKind("bonecaller")
			if b == nil {
				return "absent"
			}
			made := []int{}
			for k := 0; k < 5; k++ {
				made = append(made, b.raise(modTestFoe))
			}
			lords := 0
			for _, m := range b.minions {
				if m.o.Type().Name() == "SkeletonLord" {
					lords++
				}
			}
			return fmt.Sprint("raised ", made, ": ", len(b.minions), " standing, ", lords, " of them skeleton lords")
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
		{51, "M5 duelist buffs, and his cut", func() string {
			b := modBossByKind("duelist")
			if b == nil {
				return "absent"
			}
			modTestFoe.EnchantOff(enchant.SLOWED)
			b.struck(modTestFoe, 5)
			return fmt.Sprint("hasted ", b.o.HasEnchant(enchant.HASTED), ", infravision ", b.o.HasEnchant(enchant.INFRAVISION),
				", foe slowed ", modTestFoe.HasEnchant(enchant.SLOWED), ", foe ", int(modDist(b.o.Pos(), modTestFoe.Pos())), " px off")
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
		{62, "M5 second blade", func() string { return fmt.Sprint(modSecondBlades, " second blades, foe ", modHP(modTestFoe)) }},
		{63, "M3 bone caller casts (slow)", func() string {
			b := modBossByKind("bonecaller")
			if b == nil {
				return "absent"
			}
			b.o.SetPos(near(150, -60))
			modTestFoe.EnchantOff(enchant.SLOWED)
			b.boneSpell(modTestFoe)
			return fmt.Sprint(modBoneSpells, " spells")
		}},
		{64, "M1 harpoon", func() string {
			b := modBossByKind("ogrelord")
			if b == nil {
				return "absent"
			}
			b.o.SetPos(near(-170, 40))
			b.t3 = 0
			b.harpoon(modTestFoe)
			hookStart = int(modDist(b.o.Pos(), modTestFoe.Pos()))
			return fmt.Sprint("thrown at ", hookStart, " px")
		}},
		{66, "M4 matriarch buffs, and her touch", func() string {
			b := modBossByKind("embermother")
			if b == nil {
				return "absent"
			}
			before := modTestFoe.CurrentHealth()
			b.struck(modTestFoe, 5)
			return fmt.Sprint("protected from fire ", b.o.HasEnchant(enchant.PROTECT_FROM_FIRE), ", vampirism ",
				b.o.HasEnchant(enchant.VAMPIRISM), ", her touch: foe hp ", before, " -> ", modTestFoe.CurrentHealth())
		}},
		{70, "W6 burns so far", func() string {
			return fmt.Sprint(modBurnHits, " burns, victim ", modHP(victim), ", victim2 ", modHP(victim2))
		}},
		{80, "M3 bone caller casts (magic missile)", func() string {
			b := modBossByKind("bonecaller")
			if b == nil {
				return "absent"
			}
			sl := modTestFoe.HasEnchant(enchant.SLOWED)
			b.boneSpell(modTestFoe)
			return fmt.Sprint("the foe slowed by his first spell ", sl, ", ", modBoneSpells, " spells")
		}},
		{81, "M3 magic missiles in flight", func() string {
			return fmt.Sprint(len(ns.FindAllObjects(ns.HasTypeName{"MagicMissile"})), " MagicMissile objects")
		}},
		{85, "M3 bone caller teleports", func() string {
			b := modBossByKind("bonecaller")
			if b == nil {
				return "absent"
			}
			p := b.o.Pos()
			ok := b.boneTeleport(modTestFoe)
			return fmt.Sprint("teleported ", ok, " ", int(modDist(p, b.o.Pos())), " px, ghosts ", len(b.ghosts))
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
		{96, "M1 harpoon result", func() string {
			b := modBossByKind("ogrelord")
			d := -1
			if b != nil {
				d = int(modDist(b.o.Pos(), modTestFoe.Pos()))
			}
			return fmt.Sprint("hooked ", modHooked, ", reeled ", modReeled, " frames: foe ", hookStart, " -> ", d, " px from him")
		}},
		{100, "M5 duelist killed (respawn check)", func() string {
			b := modBossByKind("duelist")
			if b == nil {
				return "absent"
			}
			b.respawn = 150
			b.o.Damage(nil, 5000, damage.BLADE)
			return "duelist " + modHP(b.o)
		}},
		{210, "M4 matriarch killed (ring of fire)", func() string {
			b := modBossByKind("embermother")
			if b == nil {
				return "absent"
			}
			b.respawn = 150
			b.o.SetPos(near(-120, 40))
			b.o.Damage(nil, 5000, damage.BLADE)
			return "matriarch " + modHP(b.o)
		}},
		{226, "M4 ring of fire", func() string { return fmt.Sprint(modRingFlamesMade, " flames laid") }},
		{230, "W4 poison alone: two fresh stand-ins, one poisoned (level 5)", func() string {
			pois = ns.CreateObject("OgreBrute", near(100, 180))
			unpois = ns.CreateObject("OgreBrute", near(-100, -180))
			for _, o := range []ns.Obj{pois, unpois} {
				o.SetMaxHealth(500)
				o.SetHealth(500)
			}
			modPoison(pois, 5)
			return ""
		}},
		{410, "W4 poison alone after 6 s", func() string {
			return fmt.Sprint("poisoned ", modHP(pois), ", not poisoned ", modHP(unpois))
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
		{130, "W1C flame wave: a blow on victim4 (south)", func() string {
			wielder.SetPos(at)
			before := fmt.Sprint("victim4 ", modHP(victim4), ", victim6 ", modHP(victim6))
			modOnBlow("flamewave", 2, wielder, victim4)
			return fmt.Sprint(before, ", ", len(modWaves), " waves")
		}},
		{132, "W1C the wave going", func() string { return fmt.Sprint(len(modWaves), " waves, ", modWaveMade, " wave flames") }},
		{136, "W1C a second blow", func() string {
			modOnBlow("flamewave", 2, wielder, victim4)
			return ""
		}},
		{138, "W1C two at once", func() string { return fmt.Sprint(len(modWaves), " waves burning") }},
		{160, "W1C result", func() string {
			return fmt.Sprint(modWaveMade, " wave flames laid, victim4 (in front) ", modHP(victim4), ", victim6 (behind) ", modHP(victim6))
		}},
		{170, "W1B mana flames: a swing", func() string {
			modTestKind, modTestTier = "manaflame", 2
			victim5.EnchantOff(enchant.SLOWED)
			ns.CastSpellLvl(spell.CLEANSING_MANA_FLAME, 4, wielder, wielder)
			return "victim5 " + modHP(victim5)
		}},
		{200, "W1B result", func() string {
			modTestKind = ""
			return fmt.Sprint("victim5 slowed ", victim5.HasEnchant(enchant.SLOWED), ", ", modHP(victim5), "; touched ", len(modManaTouched))
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
	println("modlab selftest: after 14 s:", len(modBoomerangs), "chakrams in flight,", resp, "of", len(modBosses),
		"creatures standing, smithing xp", modSmithXP, "- flame bursts", modBursts, "- skeletons crumbled", modCrumbled)
	println("modlab selftest: done")
}
