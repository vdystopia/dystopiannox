package PKG

// Human bosses (dystopiannox mods/BOSSLAB.md), run by OpenNox from the map's folder. Written against NoxScript ns/v4
// v4.16.1, the version OpenNox v1.9.0-alpha13 bundles (no stubbed calls: MakeFriendly/MakeEnemy, GiveXp, quest status,
// TellStoryStr are never used).
//
// A boss is a placed NPC (the human the game draws with the player's own armour and weapons: kit/bosses.py dresses
// it, colours its armour with the game's UserColor enchantments and gives it the game's own spells in its NPC
// settings). The game's AI walks it, swings or fires what it holds and casts those spells; this script adds what
// makes it a boss: a way of moving that is its own (keeping its distance, charging, circling, stalking unseen,
// standing its ground), abilities with a warning the player can read and answer (a ring of sparks where a blow will
// fall, a wind-up, a channel that a strong enough blow breaks), phases as its health falls and, for two of them,
// major minions.
//
// Each boss waits frozen in its arena until its foe comes within reach (or strikes it), and comes back a while after
// it dies: a script cannot dress a new NPC in coloured armour (NoxScript 4.16 cannot set an item's enchantments), so
// its spare copies, dressed the same, wait frozen in a sealed vault and the next one is brought to the arena.
//
// The foe is the host player. With no player (the dedicated server of tests/server_smoke.py) the script runs a
// self-test instead: a stand-in creature beside each boss, every ability counted, each boss killed and brought back,
// printing "bosslab selftest: ..." lines.

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

// ---- small helpers ----------------------------------------------------------------------------------------------

func bsAlive(o ns.Obj) bool {
	return o != nil && o.CurrentHealth() > 0 && !o.Flags().HasAny(object.FlagDead|object.FlagDestroyed)
}

func bsDist(a, b ns.Pointf) float32 {
	return float32(math.Hypot(float64(a.X-b.X), float64(a.Y-b.Y)))
}

// bsDir: the unit vector from a to b, and the distance.
func bsDir(a, b ns.Pointf) (float32, float32, float32) {
	d := bsDist(a, b)
	if d < 0.01 {
		return 1, 0, 0
	}
	return (b.X - a.X) / d, (b.Y - a.Y) / d, d
}

func bsAt(p ns.Pointf, a float64, r float32) ns.Pointf {
	return ns.Ptf(p.X+r*float32(math.Cos(a)), p.Y+r*float32(math.Sin(a)))
}

func bsAngle(dx, dy float32) int {
	return int(math.Atan2(float64(dy), float64(dx))/(2*math.Pi)*256) & 255
}

func bsWall(p ns.Pointf, r float32) bool {
	return ns.FindClosestWall(p, ns.InCirclef{Center: p, R: float64(r)}) != nil
}

// bsClear: no wall within r of the straight way from a to b (checked every 14 px).
func bsClear(a, b ns.Pointf, r float32) bool {
	dx, dy, d := bsDir(a, b)
	s := float32(14)
	if s > d {
		s = d
	}
	for {
		q := ns.Ptf(a.X+dx*s, a.Y+dy*s)
		if bsWall(q, r) {
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

// bsFacing: the unit vector an object faces (ns.Direction is the 3x3 grid NW=0 .. SE=8).
func bsFacing(o ns.Obj) (float32, float32) {
	d := o.Direction()
	dx, dy := float32(d%3-1), float32(d/3-1)
	if dx == 0 && dy == 0 {
		return 0, 1
	}
	l := float32(math.Hypot(float64(dx), float64(dy)))
	return dx / l, dy / l
}

func bsSay(msg string) {
	ns.PrintStrToAll(msg)
	println("bosslab:", msg)
}

var (
	bsSelfTest bool
	bsFrames   int
	bsStarted  bool
	bsFoeSkip  = map[int]int{} // by creature: the frame its wound is the script's own (not a boss's blow)
)

// bsHurt: o takes dmg from src. The game ignores one creature's damage to another of its side, so in the self-test
// (whose stand-ins are creatures) the script strikes with no source, which the game applies.
func bsHurt(o, src ns.Obj, dmg int, typ damage.Type) {
	if !bsAlive(o) {
		return
	}
	bsFoeSkip[o.ObjScriptID()] = ns.Frame() + 1
	if bsSelfTest {
		o.Damage(nil, dmg, typ)
		return
	}
	o.Damage(src, dmg, typ)
}

// ---- flames, marks, shots: what the abilities leave in the world -----------------------------------------------

func bsFlame(typ string, p ns.Pointf, sec float64) ns.Obj {
	if bsWall(p, 9) {
		return nil
	}
	f := ns.CreateObject(typ, p)
	if f != nil {
		f.DeleteAfter(ns.Seconds(sec))
	}
	return f
}

// A mark: a ring of sparks where a blow will fall, drawn every 6 frames until it falls (fire frames after it is
// laid). The player sees it and steps out.
type bsMark struct {
	b    *bsBoss
	at   ns.Pointf
	t    int
	fire int
	r    float32
	kind string
	fx   effect.Effect
}

var bsMarks []*bsMark

func bsLayMark(b *bsBoss, at ns.Pointf, fire int, r float32, kind string, fx effect.Effect) {
	bsMarks = append(bsMarks, &bsMark{b: b, at: at, fire: fire, r: r, kind: kind, fx: fx})
}

func bsMarksFrame() {
	keep := bsMarks[:0]
	for _, m := range bsMarks {
		if m.t%6 == 0 {
			n := 8
			if m.r > 70 {
				n = 12
			}
			for j := 0; j < n; j++ {
				ns.Effect(m.fx, bsAt(m.at, 2*math.Pi*float64(j)/float64(n)+float64(m.t)*0.05, m.r), nil)
			}
		}
		m.t++
		if m.t >= m.fire {
			bsMarkFalls(m)
			continue
		}
		keep = append(keep, m)
	}
	bsMarks = keep
}

// bsMarkFalls: the blow the mark warned of.
func bsMarkFalls(m *bsMark) {
	b := m.b
	foe := b.foe()
	in := foe != nil && bsDist(foe.Pos(), m.at) < m.r+10
	var src ns.Obj
	if b != nil && bsAlive(b.o) {
		src = b.o
	}
	switch m.kind {
	case "deathray": // Vael: the ray strikes down from him into the ring
		if src != nil {
			ns.Effect(effect.DEATH_RAY, src.Pos(), m.at)
		}
		ns.Effect(effect.WHITE_FLASH, m.at, nil)
		if in {
			bsHurt(foe, src, 40, damage.ZAP_RAY)
		}
	case "meteor": // Ignis: a burst of fire, and flames left burning
		ns.Effect(effect.EXPLOSION, m.at, nil)
		ns.Effect(effect.JIGGLE, m.at, ns.Ptf(8, 0))
		for j := 0; j < 5; j++ {
			bsFlame("MediumFlame", bsAt(m.at, 2*math.Pi*float64(j)/5, 28), 3)
		}
		bsFlame("Flame", m.at, 3)
		if in {
			bsHurt(foe, src, 30, damage.FLAME)
		}
	case "arrows": // Garet: a rain of arrows over the ring
		for j := 0; j < 10; j++ {
			q := bsAt(m.at, float64(ns.RandomFloat(0, 2*math.Pi)), ns.RandomFloat(0, m.r))
			ns.Effect(effect.DAMAGE_POOF, q, nil)
			if a := ns.CreateObject("ArcherArrow", q); a != nil {
				a.FlagsEnable(object.FlagNoCollide | object.FlagNoUpdate)
				a.DeleteAfter(ns.Frames(20))
			}
		}
		if in {
			bsHurt(foe, src, 18, damage.IMPALE)
			foe.Enchant(enchant.SLOWED, ns.Seconds(2))
		}
	case "slam": // Aurelian: his hammer's judgement
		ns.Effect(effect.WHITE_FLASH, m.at, nil)
		ns.Effect(effect.JIGGLE, m.at, ns.Ptf(10, 0))
		if in {
			bsHurt(foe, src, 16, damage.CRUSH)
			foe.Enchant(enchant.HELD, ns.Seconds(1))
		}
	}
	if b != nil {
		b.n[m.kind+" fell"]++
		if in {
			b.n[m.kind+" struck"]++
		}
	}
}

// A shot: a missile the script flies (NoCollide and NoUpdate: the game neither collides nor moves it; an owned
// missile would run the game's collision code), striking the foe once within 24 px.
type bsShot struct {
	b      *bsBoss
	obj    ns.Obj
	pos    ns.Pointf
	dx, dy float32
	speed  float32
	life   int
	dmg    int
	typ    damage.Type
	back   bool // a boomerang: it turns at its reach and returns to its thrower
	out    float32
	reach  float32
	hit    bool
}

var bsShots []*bsShot

func bsShoot(b *bsBoss, typ string, from ns.Pointf, dx, dy, speed, reach float32, dmg int, dt damage.Type, boomerang bool) {
	o := ns.CreateObject(typ, ns.Ptf(from.X+dx*20, from.Y+dy*20))
	if o == nil {
		return
	}
	o.FlagsEnable(object.FlagNoCollide | object.FlagNoUpdate)
	o.LookWithAngle(bsAngle(dx, dy))
	bsShots = append(bsShots, &bsShot{b: b, obj: o, pos: o.Pos(), dx: dx, dy: dy, speed: speed, reach: reach, dmg: dmg,
		typ: dt, back: boomerang})
}

// bsFan: n shots spread `spread` degrees apart, centred on the line to the foe.
func bsFan(b *bsBoss, typ string, foe ns.Obj, n int, spread float64, speed, reach float32, dmg int, dt damage.Type, boomerang bool) {
	p := b.o.Pos()
	dx, dy, _ := bsDir(p, foe.Pos())
	base := math.Atan2(float64(dy), float64(dx))
	for k := 0; k < n; k++ {
		a := base + (float64(k)-float64(n-1)/2)*spread*math.Pi/180
		bsShoot(b, typ, p, float32(math.Cos(a)), float32(math.Sin(a)), speed, reach, dmg, dt, boomerang)
	}
	b.o.LookAtObject(foe)
}

func bsShotsFrame() {
	keep := bsShots[:0]
	for _, s := range bsShots {
		foe := s.b.foe()
		s.life++
		home := s.b.o
		if s.life > 150 || (s.back && s.out >= s.reach && !bsAlive(home)) {
			s.obj.Delete()
			continue
		}
		if s.back && s.out >= s.reach {
			dx, dy, d := bsDir(s.pos, home.Pos())
			if d < 24 {
				s.obj.Delete()
				continue
			}
			s.dx, s.dy = dx, dy
		}
		s.pos = ns.Ptf(s.pos.X+s.dx*s.speed, s.pos.Y+s.dy*s.speed)
		s.obj.SetPos(s.pos)
		if s.out < s.reach {
			s.out += s.speed
			if bsWall(s.pos, 10) {
				if !s.back {
					s.obj.Delete()
					continue
				}
				s.out, s.hit = s.reach, false
			}
			if !s.back && s.out >= s.reach {
				s.obj.Delete()
				continue
			}
		}
		if foe != nil && !s.hit && bsDist(foe.Pos(), s.pos) < 24 {
			s.hit = true
			var src ns.Obj
			if bsAlive(s.b.o) {
				src = s.b.o
			}
			bsHurt(foe, src, s.dmg, s.typ)
			ns.Effect(effect.DAMAGE_POOF, foe, nil)
			s.b.n["shot struck"]++
			if !s.back {
				s.obj.Delete()
				continue
			}
		}
		keep = append(keep, s)
	}
	bsShots = keep
}

// A ring of fire spreading from p: rings of flames every 4 frames from r0 out by 34 px a ring, each burning 2 s; the
// foe takes dmg when a ring is laid over it. (The game's own ring, the Cleansing Flame, is refused to a caster that
// still owns one.)
type bsRing struct {
	b     *bsBoss
	p     ns.Pointf
	t, n  int
	r0    float32
	dmg   int
}

var bsRings []*bsRing

func bsFireRing(b *bsBoss, p ns.Pointf, rings int, r0 float32, dmg int) {
	bsRings = append(bsRings, &bsRing{b: b, p: p, n: rings, r0: r0, dmg: dmg})
	ns.Effect(effect.SPARK_EXPLOSION, p, ns.Ptf(90, 0))
}

func bsRingsFrame() {
	keep := bsRings[:0]
	for _, r := range bsRings {
		foe := r.b.foe()
		if r.t%4 == 0 && r.t/4 < r.n {
			rad := r.r0 + float32(34*(r.t/4))
			n := int(2 * math.Pi * float64(rad) / 34)
			for j := 0; j < n; j++ {
				typ := "Flame"
				if j%2 == 1 {
					typ = "MediumFlame"
				}
				bsFlame(typ, bsAt(r.p, 2*math.Pi*float64(j)/float64(n), rad), 2)
			}
			if foe != nil {
				if d := bsDist(foe.Pos(), r.p); d > rad-22 && d < rad+22 {
					var src ns.Obj
					if bsAlive(r.b.o) {
						src = r.b.o
					}
					bsHurt(foe, src, r.dmg, damage.FLAME)
					r.b.n["ring struck"]++
				}
			}
		}
		r.t++
		if r.t < 4*r.n {
			keep = append(keep, r)
		}
	}
	bsRings = keep
}

// ---- the bosses ---------------------------------------------------------------------------------------------------

type bsBoss struct {
	kind, label string
	names       []string // the arena's NPC, then the vault's spare copies in the order they come
	next        int
	home        ns.Pointf
	hp          int
	engageR     float32
	respawn     int // frames
	o           ns.Obj
	engaged     bool
	deadAt      int
	lastHP      int
	t1, t2, t3  int // ability timers, frames since each last fired
	t4, t5      int
	state       string // what it is doing now ("" = fighting as the game's AI does), and for how long
	stateT      int
	phase       int // 0 at full strength; 1 and 2 as its health falls past its thresholds
	vx, vy      float32
	target      ns.Pointf
	taken       int // damage taken in the current state (a channel breaks when it reaches its limit)
	minions     []ns.Obj
	majors      []ns.Obj
	traps       []ns.Obj // the ranger's bear traps (objects, not creatures: kept by count)
	summonNext  string
	orbit       float32
	foeHP       int
	n           map[string]int // what it did (the self-test reports it)
	testFoe     ns.Obj
}

var bsBosses []*bsBoss

// BossDef: the NPC named names[0] becomes boss `kind`, with hp health; it waits frozen until its foe comes within
// engageR px (0: awake from the start) and comes back respawnSec seconds after it dies (0: never) as the next of its
// spare copies (names[1:], frozen in the sealed vault), as many times as there are copies.
func BossDef(kind, label string, hp int, engageR float32, respawnSec float64, names []string) {
	o := ns.Object(names[0])
	if o == nil {
		println("bosslab: boss", names[0], "not found")
		return
	}
	b := &bsBoss{kind: kind, label: label, names: names, next: 1, home: o.Pos(), hp: hp, engageR: engageR,
		respawn: int(respawnSec * 30), n: map[string]int{}}
	for _, nm := range names[1:] {
		if s := ns.Object(nm); s != nil {
			s.Freeze(true)
		}
	}
	bsBosses = append(bsBosses, b)
	b.adopt(o)
}

func (b *bsBoss) adopt(o ns.Obj) {
	b.o = o
	b.engaged = false
	b.t1, b.t2, b.t3, b.t4, b.t5 = 0, 0, 0, 0, 0
	b.state, b.stateT, b.phase, b.taken = "", 0, 0, 0
	b.summonNext = ""
	b.target = o.Pos()
	if b.hp > 0 {
		o.SetMaxHealth(b.hp)
		o.SetHealth(b.hp)
	}
	b.lastHP = o.CurrentHealth()
	if b.engageR > 0 {
		o.Freeze(true)
	} else {
		b.engage()
	}
}

// BossWake wakes the named boss now, as if its foe had come near.
func BossWake(name string) {
	for _, b := range bsBosses {
		if b.names[0] == name {
			b.engage()
		}
	}
}

func (b *bsBoss) foe() ns.Obj {
	if bsSelfTest {
		if bsAlive(b.testFoe) {
			return b.testFoe
		}
		return nil
	}
	return bsFoe()
}

func bsFoe() ns.Obj {
	h := ns.GetHost()
	if h == nil || h.CurrentHealth() <= 0 {
		return nil
	}
	return h
}

func (b *bsBoss) say(s string, sec float64) {
	if b.o != nil {
		b.o.ChatStrTimer(s, ns.Seconds(sec))
	}
}

func (b *bsBoss) engage() {
	if b.o == nil || b.engaged {
		return
	}
	b.engaged = true
	b.o.Freeze(false)
	b.buffs(true)
	if f := b.foe(); f != nil && !bsSelfTest {
		b.o.Attack(f)
	} else if !bsSelfTest {
		b.o.Hunt()
	}
	bsSay(b.label + " wakes!")
	b.say(bsGreeting[b.kind], 3)
	b.opening()
}

var bsGreeting = map[string]string{
	"archmage":   "You have walked into my lecture. Pay attention.",
	"warlord":    "Stand still, so I can split you!",
	"golemwright": "Stone, wake! We have a guest.",
	"necromancer": "Another soul for the choir.",
	"assassin":   "You will not see the knife.",
	"ranger":     "Run, little deer. I like a chase.",
	"stormblade": "Steel first. Then thunder.",
	"whirlwind":  "Can you keep up?",
	"pyromancer": "Everything burns. You first.",
	"paladin":    "Kneel, and be judged.",
}

// buffs: the standing enchantments of a boss, laid when it wakes and renewed every 10 s (each lasts 15 s);
// enchantments laid on a frozen creature do not take.
func (b *bsBoss) buffs(now bool) {
	if b.o == nil || (!now && b.t5 < 300) {
		return
	}
	b.t5 = 0
	switch b.kind {
	case "pyromancer":
		b.o.Enchant(enchant.PROTECT_FROM_FIRE, ns.Seconds(15))
	case "stormblade":
		b.o.Enchant(enchant.PROTECT_FROM_ELECTRICITY, ns.Seconds(15))
	case "whirlwind":
		b.o.Enchant(enchant.HASTED, ns.Seconds(15))
	case "necromancer":
		b.o.Enchant(enchant.PROTECT_FROM_POISON, ns.Seconds(15))
	case "warlord", "ranger":
		if b.phase > 0 {
			b.o.Enchant(enchant.HASTED, ns.Seconds(15))
		}
		if b.kind == "warlord" && b.phase > 0 {
			b.o.Enchant(enchant.VAMPIRISM, ns.Seconds(15))
		}
	}
}

// opening: what a boss does the moment it wakes.
func (b *bsBoss) opening() {
	foe := b.foe()
	switch b.kind {
	case "golemwright":
		b.summon("BlackWolf", 2, foe, false)
	case "necromancer":
		b.summon("Skeleton", 2, foe, false)
	case "assassin":
		b.vanish(foe, false)
	case "archmage":
		b.o.Enchant(enchant.SHIELD, ns.Seconds(20))
	}
}

func (b *bsBoss) died() {
	at := b.home
	if b.o != nil {
		at = b.o.Pos()
	}
	var none ns.Obj // (yaegi panics on "b.o, b.engaged = nil, false")
	b.o = none
	b.engaged = false
	b.deadAt = ns.Frame()
	b.n["died"]++
	// a summoner's servants fall with it: the stone crumbles, the bones lie down
	for _, list := range [][]ns.Obj{b.minions, b.majors} {
		for _, m := range list {
			if bsAlive(m) {
				ns.Effect(effect.SMOKE_BLAST, m, nil)
				m.Delete()
			}
		}
	}
	b.minions = nil
	b.majors = nil
	for _, t := range b.traps {
		t.Delete()
	}
	b.traps = nil
	switch b.kind {
	case "pyromancer": // his death is a last ring of fire
		bsFireRing(b, at, 4, 40, 8)
	case "necromancer":
		ns.Effect(effect.SMOKE_BLAST, at, nil)
	}
	if b.respawn > 0 && b.next < len(b.names) {
		bsSay(fmt.Sprintf("%s is slain. %s returns in %d seconds.", b.label, b.label, b.respawn/30))
	} else {
		bsSay(b.label + " is slain.")
	}
}

func (b *bsBoss) frame() {
	if b.o != nil && !bsAlive(b.o) {
		b.died()
	}
	if b.o == nil {
		if b.respawn > 0 && b.next < len(b.names) && ns.Frame()-b.deadAt >= b.respawn {
			if o := ns.Object(b.names[b.next]); o != nil {
				b.next++
				o.SetPos(b.home)
				ns.Effect(effect.TELEPORT, b.home, nil)
				b.adopt(o)
				b.n["returned"]++
				println("bosslab:", b.label, "returned as", b.names[b.next-1])
			} else {
				b.next = len(b.names)
			}
		}
		return
	}
	foe := b.foe()
	cur := b.o.CurrentHealth()
	if !b.engaged {
		if (foe != nil && bsDist(foe.Pos(), b.o.Pos()) < b.engageR) || cur < b.lastHP {
			b.engage()
		}
		b.lastHP = cur
		return
	}
	b.t1++
	b.t2++
	b.t3++
	b.t4++
	b.t5++
	b.stateT++
	drop := b.lastHP - cur
	if drop > 0 {
		b.taken += drop
		b.wounded(foe, drop)
	}
	if b.o == nil || !bsAlive(b.o) {
		return
	}
	// phases: past 60% and 30% of its health (some bosses use one, some both)
	pct := b.o.CurrentHealth() * 100 / b.o.MaxHealth()
	if b.phase == 0 && pct <= 60 {
		b.phase = 1
		b.phaseUp(foe)
	} else if b.phase == 1 && pct <= 30 {
		b.phase = 2
		b.phaseUp(foe)
	}
	b.buffs(false)
	b.prune()
	switch b.kind {
	case "archmage":
		b.archmage(foe)
	case "warlord":
		b.warlord(foe)
	case "golemwright":
		b.golemwright(foe)
	case "necromancer":
		b.necromancer(foe)
	case "assassin":
		b.assassin(foe)
	case "ranger":
		b.ranger(foe)
	case "stormblade":
		b.stormblade(foe)
	case "whirlwind":
		b.whirlwind(foe)
	case "pyromancer":
		b.pyromancer(foe)
	case "paladin":
		b.paladin(foe)
	}
	b.foeBlows(foe)
	if b.o != nil {
		b.lastHP = b.o.CurrentHealth()
	}
}

func (b *bsBoss) setState(s string) {
	b.state, b.stateT, b.taken = s, 0, 0
}

func (b *bsBoss) prune() {
	keep := b.minions[:0]
	for _, m := range b.minions {
		if bsAlive(m) {
			keep = append(keep, m)
		} else {
			b.minionFell(m)
		}
	}
	b.minions = keep
	keepM := b.majors[:0]
	for _, m := range b.majors {
		if bsAlive(m) {
			keepM = append(keepM, m)
		} else {
			b.minionFell(m)
		}
	}
	b.majors = keepM
}

// minionFell: Mortivane drinks the soul of every servant that falls.
func (b *bsBoss) minionFell(m ns.Obj) {
	if b.kind == "necromancer" && b.o != nil {
		b.o.RestoreHealth(15)
		ns.Effect(effect.VAMPIRISM, b.o.Pos(), b.o.Pos())
		ns.Effect(effect.VIOLET_SPARKS, b.o, nil)
		b.n["soul drunk"]++
	}
}

// summon: n creatures of typ round the boss, a puff of the game's summoning where each stands; major ones are kept
// apart (they count against the boss's cap of major minions).
func (b *bsBoss) summon(typ string, n int, foe ns.Obj, major bool) int {
	return b.summonAt(b.o.Pos(), typ, n, foe, major)
}

func (b *bsBoss) summonAt(p ns.Pointf, typ string, n int, foe ns.Obj, major bool) int {
	made := 0
	for k := 0; k < n; k++ {
		at := p
		for try := 0; try < 6; try++ {
			q := bsAt(p, float64(ns.RandomFloat(0, 2*math.Pi)), 60)
			if !bsWall(q, 22) && bsClear(p, q, 10) {
				at = q
				break
			}
		}
		s := ns.CreateObject(typ, at)
		if s == nil {
			continue
		}
		made++
		ns.Effect(effect.SUMMON, at, nil)
		ns.Effect(effect.SMOKE_BLAST, at, nil)
		if major {
			b.majors = append(b.majors, s)
		} else {
			b.minions = append(b.minions, s)
		}
		if foe != nil {
			s.Attack(foe)
		}
	}
	b.n["summoned "+typ] += made
	return made
}

// blinkTo: the boss steps through space to `to` (the game's teleport flash at both ends).
func (b *bsBoss) blinkTo(to ns.Pointf) {
	ns.Effect(effect.TELEPORT, b.o.Pos(), nil)
	b.o.SetPos(to)
	ns.Effect(effect.TELEPORT, to, nil)
}

// away: a clear spot r px (trying shorter) from the boss, away from the foe, through no wall.
func (b *bsBoss) away(foe ns.Obj, rs []float32) (ns.Pointf, bool) {
	p := b.o.Pos()
	dx, dy, _ := bsDir(foe.Pos(), p)
	base := math.Atan2(float64(dy), float64(dx))
	for _, deg := range []float64{0, 35, -35, 70, -70, 110, -110} {
		a := base + deg*math.Pi/180
		for _, r := range rs {
			to := bsAt(p, a, r)
			if bsClear(p, to, 18) && !bsWall(to, 22) {
				return to, true
			}
		}
	}
	return p, false
}

// wounded: the boss lost drop health this frame.
func (b *bsBoss) wounded(foe ns.Obj, drop int) {
	switch b.kind {
	case "paladin": // his shield turns a blow from the front: 70% of it comes back
		if foe != nil && b.state != "consecrate" {
			fx, fy := bsFacing(b.o)
			dx, dy, d := bsDir(b.o.Pos(), foe.Pos())
			if d < 160 && fx*dx+fy*dy > 0.5 {
				back := drop * 7 / 10
				if back > 0 {
					b.o.RestoreHealth(back)
					ns.Effect(effect.RICOCHET, b.o, nil)
					b.n["blocked"]++
				}
			}
		}
	case "stormblade": // the storm's ward halves what reaches him while he channels it
		if b.state == "storm" {
			b.o.RestoreHealth(drop / 2)
		}
	case "warlord": // dazed against a wall, he takes half again
		if b.state == "dazed" && b.o.CurrentHealth() > drop/2 {
			b.o.Damage(nil, drop/2, damage.CRUSH)
			b.lastHP = b.o.CurrentHealth()
			b.n["dazed blow"]++
		}
	case "assassin": // struck while unseen: he is found, and stumbles
		if b.state == "stalk" {
			b.o.EnchantOff(enchant.INVISIBLE)
			b.o.Enchant(enchant.HELD, ns.Frames(30))
			b.say("You... see me?", 2)
			b.setState("fight")
			b.n["found"]++
		}
	case "golemwright", "necromancer": // a strong enough blow breaks a summoning
		if b.state == "ritual" && b.taken >= 30 {
			ns.Effect(effect.SUMMON_CANCEL, b.target, nil)
			b.o.EnchantOff(enchant.HELD)
			b.say("No! The binding breaks!", 2)
			b.setState("")
			b.t2 = 0
			b.n["ritual broken"]++
		}
	}
}

// foeBlows: a boss's blow on the player raises no event, so the script reads it from the foe's health: a drop the
// script did not cause itself, with the boss within 80 px, is the boss's blow.
func (b *bsBoss) foeBlows(foe ns.Obj) {
	if foe == nil || b.o == nil {
		b.foeHP = 0
		return
	}
	hp := foe.CurrentHealth()
	drop := b.foeHP - hp
	b.foeHP = hp
	// (3 or more: a poison or burn tick takes 1 or 2)
	if drop < 3 || ns.Frame() <= bsFoeSkip[foe.ObjScriptID()] || bsDist(foe.Pos(), b.o.Pos()) > 80 {
		return
	}
	b.n["blow"]++
	switch b.kind {
	case "assassin": // his blade is poisoned
		if b.n["blow"]%2 == 1 {
			ns.CastSpellLvl(spell.POISON, 2, b.o, foe)
			b.n["poisoned"]++
		}
	case "stormblade": // his blade carries the storm
		ns.Effect(effect.LIGHTNING, b.o, foe)
		bsHurt(foe, b.o, 4, damage.ELECTRIC)
	}
}

// phaseUp: what a boss does as its health falls past 60% (phase 1) and 30% (phase 2).
func (b *bsBoss) phaseUp(foe ns.Obj) {
	b.n[fmt.Sprintf("phase %d", b.phase)]++
	switch b.kind {
	case "archmage":
		if b.phase == 1 {
			b.say("Enough tutoring. Now the examination.", 3)
		} else {
			b.say("Impossible! ...Fine.", 2)
			b.o.Enchant(enchant.INVULNERABLE, ns.Seconds(2))
		}
	case "warlord":
		if b.phase == 1 {
			b.say("BLOOD! MORE BLOOD!", 3)
			b.buffs(true)
		}
	case "golemwright":
		if b.phase == 2 {
			b.say("Protect your master!", 3)
		}
	case "necromancer": // at 60% two skeleton lords, at 30% a lich
		b.setState("ritual")
		b.summonNext = "SkeletonLord"
		if b.phase == 2 {
			b.summonNext = "Lich"
		}
	case "ranger":
		if b.phase == 1 {
			b.say("Now I'm serious.", 2)
			b.buffs(true)
		}
	case "stormblade":
		if b.phase == 1 {
			b.say("The storm answers!", 2)
		}
	case "whirlwind":
		if b.phase == 1 {
			b.say("Faster!", 2)
		}
	case "pyromancer":
		if b.phase == 2 {
			b.say("Burn with me!", 3)
			bsFireRing(b, b.o.Pos(), 3, 50, 10)
		}
	case "paladin":
		if b.phase == 1 {
			b.say("The light shields me!", 3)
			b.o.Enchant(enchant.INVULNERABLE, ns.Seconds(3))
			b.o.RestoreHealth(b.o.MaxHealth() / 10)
			ns.Effect(effect.GREATER_HEAL, b.o, nil)
		}
	}
}

// ---- 1. Vael the Unbound, archmage: keeps his distance, blinks away from the blade, rains death rays ---------

func (b *bsBoss) archmage(foe ns.Obj) {
	if foe == nil {
		return
	}
	p := b.o.Pos()
	d := bsDist(p, foe.Pos())
	if d < 170 {
		if b.t1 >= 180 { // the blink: away, and a parting volley
			if to, ok := b.away(foe, []float32{260, 220, 180}); ok {
				b.t1 = 0
				b.blinkTo(to)
				b.say([]string{"Too slow.", "Mind the gap.", "Not today."}[ns.Random(0, 2)], 2)
				ns.CastSpellLvl(spell.MAGIC_MISSILE, 2, b.o, foe)
				b.n["blink"]++
			}
		} else if b.t4%20 == 0 {
			b.o.Flee(foe, ns.Seconds(1))
		}
	}
	if b.t2 >= 150 && d < 480 && (bsSelfTest || b.o.CanSee(foe)) { // a volley of missiles
		b.t2 = 0
		b.o.LookAtObject(foe)
		ns.CastSpellLvl(spell.MAGIC_MISSILE, 3, b.o, foe)
		b.n["missiles"]++
	}
	every := 240
	if b.phase > 0 {
		every = 170
	}
	if b.t3 >= every && d < 520 { // the death ray: a ring where it will strike, then the ray
		b.t3 = 0
		b.o.LookAtObject(foe)
		b.say("Hold still...", 1.5)
		if b.phase == 2 { // three at once, round the foe
			for k := 0; k < 3; k++ {
				bsLayMark(b, bsAt(foe.Pos(), 2*math.Pi*float64(k)/3, 55), 42, 40, "deathray", effect.VIOLET_SPARKS)
			}
		}
		bsLayMark(b, foe.Pos(), 42, 40, "deathray", effect.VIOLET_SPARKS)
		b.n["death ray"]++
	}
	if b.phase > 0 && !b.o.HasEnchant(enchant.SHIELD) && b.t4 >= 450 {
		b.t4 = 0
		b.o.Enchant(enchant.SHIELD, ns.Seconds(10))
	}
}

// ---- 2. Sir Garrick the Verdant, warlord: winds up, charges in a straight line, dazed if he meets a wall -------

func (b *bsBoss) warlord(foe ns.Obj) {
	switch b.state {
	case "windup":
		if b.stateT%10 == 0 {
			ns.Effect(effect.JIGGLE, b.o, ns.Ptf(4, 0))
		}
		if b.stateT >= 30 {
			b.setState("charge")
			b.n["charge"]++
		}
		return
	case "charge":
		p := b.o.Pos()
		q := ns.Ptf(p.X+b.vx*17, p.Y+b.vy*17)
		if bsWall(q, 16) { // into the wall: dazed for 2 s, and he takes half again
			ns.Effect(effect.JIGGLE, p, ns.Ptf(9, 0))
			ns.Effect(effect.DAMAGE_POOF, p, nil)
			b.o.Enchant(enchant.HELD, ns.Seconds(2))
			b.say("Ugh...", 2)
			b.setState("dazed")
			b.n["dazed"]++
			return
		}
		b.o.SetPos(q)
		b.o.LookWithAngle(bsAngle(b.vx, b.vy))
		if foe != nil && bsDist(q, foe.Pos()) < 40 {
			bsHurt(foe, b.o, 28, damage.CRUSH)
			foe.PushTo(b.o.Pos(), 60)
			foe.Enchant(enchant.HELD, ns.Seconds(1))
			ns.Effect(effect.JIGGLE, foe, ns.Ptf(8, 0))
			b.n["charge struck"]++
			b.setState("")
			b.o.Attack(foe)
			return
		}
		if b.stateT >= 30 {
			b.setState("")
			if foe != nil {
				b.o.Attack(foe)
			}
		}
		return
	case "dazed":
		if b.stateT >= 60 {
			b.setState("")
			if foe != nil {
				b.o.Attack(foe)
			}
		}
		return
	}
	if foe == nil {
		return
	}
	d := bsDist(b.o.Pos(), foe.Pos())
	every := 200
	if b.phase > 0 {
		every = 120
	}
	if b.t1 >= every && d > 110 && d < 430 && bsClear(b.o.Pos(), foe.Pos(), 12) {
		b.t1 = 0
		b.vx, b.vy, _ = bsDir(b.o.Pos(), foe.Pos())
		b.o.LookAtObject(foe)
		b.o.Enchant(enchant.HELD, ns.Frames(30))
		b.say("RAAAAGH!", 1.5)
		b.setState("windup")
		return
	}
	if d < 70 { // a stamp that throws a foe who stays in his face
		if b.t2 >= 210 {
			b.t2 = 0
			ns.Effect(effect.JIGGLE, b.o, ns.Ptf(10, 0))
			bsHurt(foe, b.o, 12, damage.CRUSH)
			foe.PushTo(b.o.Pos(), 45)
			b.n["stamp"]++
		}
	}
}

// ---- 3. Oskar Thorne, the Golemwright, conjurer: wolves at once, golems by ritual, keeps behind them --------------

func (b *bsBoss) golemwright(foe ns.Obj) {
	if b.state == "ritual" { // channelling a golem: held, the summoning's glow where it will stand
		if b.stateT%8 == 0 {
			ns.Effect(effect.SUMMON, b.target, nil)
		}
		if b.stateT >= 60 {
			b.o.EnchantOff(enchant.HELD)
			b.summonAt(b.target, b.summonNext, 1, foe, true)
			b.say("Crush them!", 2)
			b.setState("")
		}
		return
	}
	if foe == nil {
		return
	}
	p := b.o.Pos()
	d := bsDist(p, foe.Pos())
	if d < 170 && b.t4%20 == 0 { // he keeps behind his servants
		b.o.Flee(foe, ns.Seconds(1))
	}
	if b.t2 >= 330 && len(b.majors) < 2 && d < 520 { // a golem, stone and steel in turn
		b.t2 = 0
		b.summonNext = "StoneGolem"
		if b.n["summoned StoneGolem"] > b.n["summoned MechanicalGolem"] {
			b.summonNext = "MechanicalGolem"
		}
		dx, dy, _ := bsDir(p, foe.Pos())
		b.target = ns.Ptf(p.X+dx*70, p.Y+dy*70)
		if bsWall(b.target, 24) {
			b.target = p
		}
		b.o.Enchant(enchant.HELD, ns.Frames(60))
		b.say("Earth and iron, take shape!", 2)
		b.setState("ritual")
		b.n["ritual"]++
		return
	}
	if b.t1 >= 360 && len(b.minions) < 3 && d < 500 { // more wolves
		b.t1 = 0
		b.summon("BlackWolf", 2, foe, false)
	}
	if b.t3 >= 240 && len(b.minions)+len(b.majors) > 0 { // the hunt: his servants hasted
		b.t3 = 0
		for _, m := range append(append([]ns.Obj{}, b.minions...), b.majors...) {
			m.Enchant(enchant.HASTED, ns.Seconds(4))
			m.Attack(foe)
		}
		b.say("Hunt!", 1.5)
		b.n["hunt"]++
	}
	if b.phase == 2 && b.t5 >= 600 && len(b.minions) > 0 { // a servant given up to mend him
		b.t5 = 0
		m := b.minions[0]
		ns.Effect(effect.GREATER_HEAL, m.Pos(), b.o.Pos())
		ns.Effect(effect.SMOKE_BLAST, m, nil)
		m.Delete()
		b.o.RestoreHealth(45)
		b.say("Your life for mine.", 2)
		b.n["sacrifice"]++
	}
}

// ---- 4. Lord Mortivane, necromancer: drains life along a tether, raises the dead, trades places with them -----

func (b *bsBoss) necromancer(foe ns.Obj) {
	switch b.state {
	case "ritual": // a major raising, by threshold: two skeleton lords, then a lich
		if b.stateT == 1 {
			b.o.Enchant(enchant.HELD, ns.Frames(60))
			b.target = b.o.Pos()
			b.say("Rise, my lords of bone!", 2.5)
			if b.summonNext == "Lich" {
				b.say("Come forth, Lich, and bring the cold!", 2.5)
			}
			b.n["ritual"]++
		}
		if b.stateT%8 == 0 {
			ns.Effect(effect.VIOLET_SPARKS, b.o, nil)
			ns.Effect(effect.SUMMON, b.target, nil)
		}
		if b.stateT >= 60 {
			b.o.EnchantOff(enchant.HELD)
			n := 2
			if b.summonNext == "Lich" {
				n = 1
			}
			b.summon(b.summonNext, n, foe, true)
			b.setState("")
		}
		return
	case "drain": // the tether: 3 health a third of a second, foe to master, while it holds
		if foe == nil || bsDist(b.o.Pos(), foe.Pos()) > 340 || (!bsSelfTest && !b.o.CanSee(foe)) || b.stateT > 90 {
			if b.stateT <= 90 {
				b.n["drain broken"]++
			}
			b.setState("")
			return
		}
		if b.stateT%10 == 0 {
			ns.Effect(effect.VAMPIRISM, b.o.Pos(), foe.Pos())
			ns.Effect(effect.DRAIN_MANA, foe.Pos(), b.o.Pos())
			bsHurt(foe, b.o, 3, damage.DRAIN)
			b.o.RestoreHealth(3)
			b.n["drained"]++
		}
		return
	}
	if foe == nil {
		return
	}
	p := b.o.Pos()
	d := bsDist(p, foe.Pos())
	if b.t1 >= 270 && d < 300 && (bsSelfTest || b.o.CanSee(foe)) {
		b.t1 = 0
		b.o.LookAtObject(foe)
		b.say("Your warmth... give it to me.", 2)
		b.setState("drain")
		b.n["drain"]++
		return
	}
	if b.t2 >= 360 && len(b.minions) < 4 && d < 500 {
		b.t2 = 0
		b.say("Rise!", 1.5)
		b.summon("Skeleton", 2, foe, false)
	}
	if d < 90 && b.t3 >= 300 { // cornered: he trades places with a servant
		var swap ns.Obj
		for _, m := range append(append([]ns.Obj{}, b.majors...), b.minions...) {
			if bsDist(m.Pos(), foe.Pos()) > 150 {
				swap = m
				break
			}
		}
		if swap != nil {
			b.t3 = 0
			a, s := b.o.Pos(), swap.Pos()
			ns.Effect(effect.TELEPORT, a, nil)
			ns.Effect(effect.TELEPORT, s, nil)
			b.o.SetPos(s)
			swap.SetPos(a)
			swap.Attack(foe)
			b.say("You face my servant instead.", 2)
			b.n["swap"]++
		} else if b.t4%20 == 0 {
			b.o.Flee(foe, ns.Seconds(1))
		}
	}
	if len(b.majors) > 0 && b.t4%30 == 0 { // while a major servant stands, he mends
		b.o.RestoreHealth(2)
	}
}

// ---- 5. Silas Vane, the Quiet Knife, assassin: stalks unseen, strikes from behind, smoke and gone again ---------------

func (b *bsBoss) vanish(foe ns.Obj, smoke bool) {
	if smoke {
		ns.Effect(effect.SMOKE_BLAST, b.o, nil)
		if foe != nil && bsDist(foe.Pos(), b.o.Pos()) < 130 {
			foe.Enchant(enchant.CONFUSED, ns.Seconds(1))
		}
		if foe != nil {
			if to, ok := b.away(foe, []float32{170, 130, 90}); ok {
				b.blinkTo(to)
			}
		}
		b.n["smoke"]++
	}
	b.o.Enchant(enchant.INVISIBLE, ns.Seconds(8))
	b.setState("stalk")
}

func (b *bsBoss) assassin(foe ns.Obj) {
	switch b.state {
	case "stalk": // unseen: to the spot behind the foe, faint footfalls on the way
		if foe == nil {
			return
		}
		if b.stateT%16 == 0 {
			ns.Effect(effect.DAMAGE_POOF, b.o.Pos(), nil)
		}
		fx, fy := bsFacing(foe)
		fp := foe.Pos()
		behind := ns.Ptf(fp.X-fx*38, fp.Y-fy*38)
		if bsWall(behind, 14) {
			behind = fp
		}
		if b.stateT%6 == 0 {
			b.o.WalkTo(behind)
		}
		if bsDist(b.o.Pos(), fp) < 48 || b.stateT > 200 {
			b.o.EnchantOff(enchant.INVISIBLE)
			b.o.LookAtObject(foe)
			if bsDist(b.o.Pos(), fp) < 60 {
				bsHurt(foe, b.o, 24, damage.BLADE)
				foe.Enchant(enchant.HELD, ns.Frames(20))
				ns.Effect(effect.RICOCHET, foe, nil)
				b.say("Shh.", 1.5)
				b.n["backstab"]++
			}
			b.o.Attack(foe)
			b.setState("fight")
		}
		return
	case "fight": // seen: he fights, then smokes and is gone
		limit := 150
		if b.phase > 0 {
			limit = 100
		}
		if b.stateT >= limit {
			b.vanish(foe, true)
		}
		return
	}
	b.vanish(foe, false)
}

// ---- 6. Garet Hawkeye, ranger: keeps his range, leaps back leaving traps, volleys and rains of arrows ----------

func (b *bsBoss) ranger(foe ns.Obj) {
	if foe == nil {
		return
	}
	p := b.o.Pos()
	d := bsDist(p, foe.Pos())
	if d < 190 && b.t1 >= 150 { // the leap back, and a bear trap where he stood
		if to, ok := b.away(foe, []float32{190, 150, 110}); ok {
			b.t1 = 0
			if t := ns.CreateObject("BearTrap", p); t != nil {
				b.traps = append(b.traps, t)
				if len(b.traps) > 4 {
					b.traps[0].Delete()
					b.traps = b.traps[1:]
				}
				b.n["trap"]++
			}
			ns.Effect(effect.SMOKE_BLAST, p, nil)
			b.o.SetPos(to)
			b.o.LookAtObject(foe)
			b.say("Watch your step.", 1.5)
			b.n["leap"]++
		}
	} else if d < 160 && b.t4%25 == 0 {
		b.o.Flee(foe, ns.Seconds(1))
	}
	volley := 210
	if b.phase > 0 {
		volley = 140
	}
	if b.t2 >= volley && d < 460 && (bsSelfTest || b.o.CanSee(foe)) { // a fan of five arrows
		b.t2 = 0
		bsFan(b, "ArcherArrow", foe, 5, 12, 16, 460, 8, damage.IMPALE, false)
		b.n["volley"]++
	}
	if b.t3 >= 330 && d < 520 { // the rain: a ring where the arrows will fall
		b.t3 = 0
		b.say("Arrows, up!", 1.5)
		bsLayMark(b, foe.Pos(), 40, 65, "arrows", effect.YELLOW_SPARKS)
		b.n["arrow rain"]++
	}
}

// ---- 7. Dravik Stormblade, spellsword: a blade stance that hunts, a storm stance that holds and strikes ---------

func (b *bsBoss) stormblade(foe ns.Obj) {
	blade, storm := 300, 180
	if b.phase > 0 {
		blade = 210
	}
	if b.state == "storm" {
		if b.stateT%45 == 0 && foe != nil && bsDist(b.o.Pos(), foe.Pos()) < 320 { // bolts at the foe
			ns.Effect(effect.LIGHTNING, b.o, foe)
			bsHurt(foe, b.o, 9, damage.ELECTRIC)
			b.n["bolt"]++
		}
		if b.stateT%30 == 15 { // a crackling field round him
			for j := 0; j < 6; j++ {
				ns.Effect(effect.BLUE_SPARKS, bsAt(b.o.Pos(), 2*math.Pi*float64(j)/6, 90), nil)
			}
			if foe != nil && bsDist(b.o.Pos(), foe.Pos()) < 110 {
				bsHurt(foe, b.o, 6, damage.ELECTRIC)
				b.n["field"]++
			}
		}
		if b.stateT >= storm {
			b.o.EnchantOff(enchant.HELD)
			b.o.Enchant(enchant.HASTED, ns.Seconds(float64(blade)/30))
			b.say("Steel!", 1.5)
			b.setState("blade")
			if foe != nil {
				b.o.Attack(foe)
			}
		}
		return
	}
	if b.state == "" {
		b.o.Enchant(enchant.HASTED, ns.Seconds(float64(blade)/30))
		b.setState("blade")
	}
	if foe != nil && b.t1 >= 120 && bsDist(b.o.Pos(), foe.Pos()) > 220 { // the lightning step, to the foe's side
		fp := foe.Pos()
		dx, dy, _ := bsDir(fp, b.o.Pos())
		to := ns.Ptf(fp.X+dx*45, fp.Y+dy*45)
		if !bsWall(to, 20) {
			b.t1 = 0
			ns.Effect(effect.LIGHTNING, b.o.Pos(), to)
			b.o.SetPos(to)
			b.o.LookAtObject(foe)
			b.o.Attack(foe)
			b.n["lightning step"]++
		}
	}
	if b.stateT >= blade {
		b.o.Enchant(enchant.HELD, ns.Frames(storm))
		b.say("Thunder!", 2)
		b.setState("storm")
		b.n["storm"]++
	}
}

// ---- 8. Kesh of the Red Sands, chakram dancer: circles at range, throws, spins into a whirlwind if pressed ------

func (b *bsBoss) whirlwind(foe ns.Obj) {
	if b.state == "spin" {
		b.o.LookWithAngle((b.stateT * 32) & 255)
		if b.stateT%8 == 0 {
			for j := 0; j < 6; j++ {
				ns.Effect(effect.DAMAGE_POOF, bsAt(b.o.Pos(), 2*math.Pi*float64(j)/6+float64(b.stateT), 60), nil)
			}
			if foe != nil && bsDist(b.o.Pos(), foe.Pos()) < 95 {
				bsHurt(foe, b.o, 7, damage.BLADE)
				foe.PushTo(b.o.Pos(), 18)
				b.n["spin struck"]++
			}
		}
		if b.stateT >= 45 {
			b.setState("")
			if foe != nil {
				if to, ok := b.away(foe, []float32{160, 120}); ok {
					b.o.WalkTo(to)
				}
			}
		}
		return
	}
	if foe == nil {
		return
	}
	p, fp := b.o.Pos(), foe.Pos()
	d := bsDist(p, fp)
	if d < 85 && b.t3 >= 200 {
		b.t3 = 0
		b.say("Whirlwind!", 1.5)
		b.setState("spin")
		b.n["whirlwind"]++
		return
	}
	if b.t4%20 == 0 { // he circles, 210 px out; he turns the other way every 8 s
		if b.orbit == 0 {
			b.orbit = 1
		}
		if b.t4%240 == 0 {
			b.orbit = -b.orbit
		}
		dx, dy, _ := bsDir(fp, p)
		a := math.Atan2(float64(dy), float64(dx)) + float64(b.orbit)*0.6
		to := bsAt(fp, a, 210)
		if !bsWall(to, 20) && bsClear(p, to, 12) {
			b.o.WalkTo(to)
		} else {
			b.orbit = -b.orbit
		}
	}
	throw := 90
	n := 1
	if b.phase > 0 {
		n = 3
	}
	if b.t2 >= throw && d < 420 && (bsSelfTest || b.o.CanSee(foe)) {
		b.t2 = 0
		bsFan(b, "RoundChakramInMotion", foe, n, 18, 14, 330, 10, damage.BLADE, true)
		b.n["throw"]++
	}
}

// ---- 9. Ignis Varr, pyromancer: a trail of fire, walls of flame, meteors, a ring if you come close -------------

func (b *bsBoss) pyromancer(foe ns.Obj) {
	p := b.o.Pos()
	if b.t4%14 == 0 { // flames where he has walked
		if bsDist(p, b.target) > 12 {
			bsFlame("SmallFlame", b.target, 4)
			b.n["trail"]++
		}
		b.target = p
	}
	if foe == nil {
		return
	}
	fp := foe.Pos()
	d := bsDist(p, fp)
	if d < 95 && b.t1 >= 240 { // too close: a ring of fire bursts from him
		b.t1 = 0
		b.say("Back!", 1)
		bsFireRing(b, p, 3, 45, 10)
		b.n["ring"]++
	} else if d < 160 && b.t4%25 == 0 {
		b.o.Flee(foe, ns.Seconds(1))
	}
	if b.t2 >= 270 && d < 420 { // a wall of flame across the way between them
		b.t2 = 0
		dx, dy, _ := bsDir(p, fp)
		mid := ns.Ptf(p.X+dx*d*0.5, p.Y+dy*d*0.5)
		for k := -4; k <= 4; k++ {
			bsFlame("Flame", ns.Ptf(mid.X-dy*float32(k)*26, mid.Y+dx*float32(k)*26), 5)
		}
		b.say("Burn!", 1.5)
		b.n["fire wall"]++
	}
	every := 200
	if b.phase == 2 {
		every = 130
	}
	if b.t3 >= every && d < 520 { // a meteor: a ring where it will fall
		b.t3 = 0
		bsLayMark(b, fp, 36, 45, "meteor", effect.YELLOW_SPARKS)
		b.n["meteor"]++
	}
}

// ---- 10. High Warden Aurelian, paladin: a shield that turns blows from the front, a channelled heal, judgement --

func (b *bsBoss) paladin(foe ns.Obj) {
	if b.state == "consecrate" { // kneeling in prayer: mends 2% a third of a second; 40 damage breaks it
		if b.stateT%10 == 0 {
			b.o.RestoreHealth(b.o.MaxHealth() / 50)
			ns.Effect(effect.GREATER_HEAL, b.o, nil)
			for j := 0; j < 8; j++ {
				ns.Effect(effect.YELLOW_SPARKS, bsAt(b.o.Pos(), 2*math.Pi*float64(j)/8, 70), nil)
			}
		}
		if b.taken >= 40 {
			b.o.EnchantOff(enchant.HELD)
			b.o.Enchant(enchant.HELD, ns.Seconds(2))
			b.say("The light... falters!", 2)
			b.setState("")
			b.n["prayer broken"]++
			return
		}
		if b.stateT >= 75 {
			b.o.EnchantOff(enchant.HELD)
			b.setState("")
			if foe != nil {
				b.o.Attack(foe)
			}
		}
		return
	}
	if foe == nil {
		return
	}
	d := bsDist(b.o.Pos(), foe.Pos())
	hurt := b.o.CurrentHealth() < b.o.MaxHealth()*85/100
	if hurt && b.t1 >= 360 {
		b.t1 = 0
		b.o.Enchant(enchant.HELD, ns.Frames(75))
		b.say("Light, mend your servant.", 2.5)
		b.setState("consecrate")
		b.n["prayer"]++
		return
	}
	if d > 200 && d < 420 && b.t2 >= 270 && (bsSelfTest || b.o.CanSee(foe)) { // judgement: drawn in, then the hammer
		b.t2 = 0
		b.say("Come to judgement!", 2)
		ns.CastSpellLvl(spell.PULL, 3, b.o, foe)
		foe.PushTo(b.o.Pos(), -70)
		dx, dy, _ := bsDir(b.o.Pos(), foe.Pos())
		bsLayMark(b, ns.Ptf(b.o.Pos().X+dx*60, b.o.Pos().Y+dy*60), 30, 60, "slam", effect.YELLOW_SPARKS)
		b.n["judgement"]++
	}
}

// ---- the frame, the start, the self-test ---------------------------------------------------------------------------

func StartBosses() {
	if bsStarted {
		return
	}
	bsStarted = true
	println("bosslab: started:", len(bsBosses), "bosses")
}

func init() {
	ns.OnFrame(bsFrame)
}

func bsFrame() {
	if !bsStarted {
		return
	}
	bsFrames++
	if bsFrames == bsTestAt && ns.GetHost() == nil {
		bsRunSelfTest()
	}
	for _, b := range bsBosses {
		b.frame()
	}
	bsMarksFrame()
	bsShotsFrame()
	bsRingsFrame()
	if bsSelfTest {
		bsTestFrame()
	}
}

const bsTestAt = 60

var bsTestStart int

// bsRunSelfTest: a stand-in (a bear with 4000 health, held in place) 190 px from each boss, which wakes at once; the
// script's foe for each boss is its own stand-in.
func bsRunSelfTest() {
	bsSelfTest = true
	bsTestStart = bsFrames
	println("bosslab selftest: start,", len(bsBosses), "bosses")
	for _, b := range bsBosses {
		if b.o == nil {
			continue
		}
		var at ns.Pointf
		found := false
		for _, a := range []float64{0, 1.6, 3.1, 4.7, 0.8, 2.4, 3.9, 5.5} {
			q := bsAt(b.home, a, 190)
			if !bsWall(q, 24) && bsClear(b.home, q, 12) {
				at, found = q, true
				break
			}
		}
		if !found {
			at = bsAt(b.home, 0, 60)
		}
		f := ns.CreateObject("Bear", at)
		if f == nil {
			println("bosslab selftest:", b.kind, "no stand-in")
			continue
		}
		f.SetMaxHealth(4000)
		f.SetHealth(4000)
		println(fmt.Sprintf("bosslab selftest: %s stand-in %d/%d at %.0f px", b.kind, f.CurrentHealth(), f.MaxHealth(), bsDist(at, b.home)))
		f.Enchant(enchant.HELD, ns.Seconds(120))
		f.AggressionLevel(0)
		b.testFoe = f
		b.engage()
	}
}

func bsTestFrame() {
	t := bsFrames - bsTestStart
	switch t {
	case 300: // the paladin is wounded (his prayer); every boss to 55% at 600 (phase 1)
		for _, b := range bsBosses {
			if b.o != nil && b.kind == "paladin" { // (health set, not struck: armour would take most of a blow)
				b.o.SetHealth(b.hp * 78 / 100)
			}
		}
	case 450: // the stand-ins brought close (70 px): the bosses' answers to a foe in their face
		for _, b := range bsBosses {
			if b.o != nil && b.testFoe != nil {
				dx, dy, _ := bsDir(b.o.Pos(), b.testFoe.Pos())
				q := ns.Ptf(b.o.Pos().X+dx*70, b.o.Pos().Y+dy*70)
				if !bsWall(q, 20) {
					b.testFoe.SetPos(q)
				}
			}
		}
	case 600:
		for _, b := range bsBosses {
			if b.o != nil {
				b.o.SetHealth(b.hp * 55 / 100)
			}
		}
	case 750: // and to 28% (phase 2: the lich, the berserk, the triple ray ...)
		for _, b := range bsBosses {
			if b.o != nil {
				b.o.SetHealth(b.hp * 28 / 100)
			}
		}
	case 900: // 30 s of fighting: report, then each boss slain to see it come back
		for _, b := range bsBosses {
			lost := 0
			if b.testFoe != nil {
				lost = 4000 - b.testFoe.CurrentHealth()
			}
			hp := "dead"
			if b.o != nil {
				hp = fmt.Sprintf("%d/%d", b.o.CurrentHealth(), b.o.MaxHealth())
			}
			println(fmt.Sprintf("bosslab selftest: %s ok hp %s, stand-in lost %d, did %v", b.kind, hp, lost, b.n))
			if b.o != nil { // (its force field or ward off first: Vael's shield turned the first test's blow)
				b.o.EnchantOff(enchant.SHIELD)
				b.o.EnchantOff(enchant.INVULNERABLE)
				b.o.SetHealth(1)
				b.o.Damage(nil, 500, damage.BLADE)
			}
		}
	case 900 + 30*34:
		back := 0
		for _, b := range bsBosses {
			if b.o != nil && b.n["returned"] > 0 {
				back++
			} else {
				println("bosslab selftest:", b.kind, "did not return (died", b.n["died"], ")")
			}
		}
		println(fmt.Sprintf("bosslab selftest: returned %d/%d", back, len(bsBosses)))
	}
}

var _ = class.MONSTER
