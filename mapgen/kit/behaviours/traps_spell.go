package PKG

// Spell traps (dystopiannox mapgen/kit/trapkit/spells.py): the "spell" kind's own actions and watchers, added to
// the trap library (traps.go) through trapExt.
//
// What the engine does with a spell a script casts (OpenNox alpha13 source: script_ns_spell.go, spells.go,
// legacy GAME4_2.c; the numbers from gamedata.bin, SOLO):
//   - ns.CastSpell from a POINT moves one shared invisible caster (ImaginaryCaster) there; its spell power is
//     level 1. From an OBJECT (a plate, a statue, a light) the object casts, at level 3 unless a level is given
//     (CastSpellLvl honours it).
//   - a caster has at most one fist and one meteor in the air (ExecSpel.c TooManyFists / TooManyMeteors): fists
//     and meteors are cast from their own objects (a plate, a light), never from points, or they fail when two
//     fall at once anywhere on the map.
//   - Fireball lvl 1 is the "Fireball" missile (SparkExplosion 128: ~64, splash r64), lvl 2 StrongFireball (~96,
//     a skull gun's), lvl 3 TitanFireball; it flies ~19 units a frame. Fist (FistOfVengeanceDamage 50, 100, 200)
//     drops from z 255 at 10 a frame onto the point (~25 frames), lands in r25 / 30 / 35, crush. Meteor (45, 65,
//     85) drops at 8 a frame (~32 frames) and bursts in r80 (full within 30), explosion. Death ray: 90 within 10-15
//     units of the point, at once, only if the line from the caster is clear. Toxic cloud: 15 s, every 5-10 frames
//     3-10 poison to whoever is within 75 and in sight.
//
// Actions (trapAct; Text carries options "lvl:N lead:N"):
//   cast_lvl     Spell from Target (an object's script name) or From, at To; lvl:N (0 or none: the engine's level)
//   cast_mark    note where the last toucher (trapCaller) stands now, or where he will be in lead:N frames by his
//                last steps, and cast Spell there Frames frames later (from Target or From, lvl:N)
//   spell_clear  delete every object of type Text within Frames px of From (a toxic cloud blown away early)
//   spell_glyph  set off the glyph named Target as the engine would (its spells, then every glyph within 100 a
//                frame later), if the engine has not already: a glyph's touch is UNCONFIRMED in alpha13 (the bench's
//                probe stood on one and nothing happened), so each glyph is also a zone that calls this
// Watchers (start lines, after StartTraps): SpellTrapsOn(), SpellGlyph(name, lvl, spells...),
// SpellHunt(spellHunt{...}): while a player is in a box, a spell at where he stood every Period frames.

import (
	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/audio"
	"github.com/noxworld-dev/noxscript/ns/v4/effect"
	"github.com/noxworld-dev/noxscript/ns/v4/spell"
)

type spellGlyph struct {
	Name   string
	Lvl    int
	Spells []string
	pos    ns.Pointf
	posSet bool
	done   bool
}

// A hunt: while a player stands in the box (centre C, half sizes HU along U and HV across it), every Period frames
// Spell is cast at where he stands (or will be, Lead frames on) Delay frames later, from Src (an object) or From.
type spellHunt struct {
	Name   string
	C      ns.Pointf
	U      ns.Pointf // unit vector along the box
	HU     float32
	HV     float32
	Spell  string
	Src    string
	From   ns.Pointf
	Period int
	Delay  int
	Lvl    int
	Lead   int
	Sound  string // played at the mark, where he stands (the tell)
	Armed  bool
	t      int
}

// A volley: shots on a clock (each at frame T of every Period): Kind "cast" (Spell from Src or From at To, level
// Lvl), "clear" (delete objects of type Text within R of From: a cloud blown away) or "sound" (Text at From).
type spellShot struct {
	T     int
	Kind  string
	Spell string
	Src   string
	From  ns.Pointf
	To    ns.Pointf
	Lvl   int
	Text  string
	R     float32
}

type spellVolley struct {
	Name   string
	Period int
	Shots  []spellShot
	Armed  bool
	t0     int
}

// A gate: while a player is in the box, its targets (volleys, hunts, clocks, zones) are armed; when the last
// leaves they are disarmed (a volley or a clock starts its period again when armed): a station's spells run only
// while someone is in it.
type spellGate struct {
	Name    string
	C       ns.Pointf
	U       ns.Pointf
	HU      float32
	HV      float32
	Targets []string
	in      bool
}

type spellPos struct {
	hist [6]ns.Pointf
	n    int
}

var (
	spellOn      bool
	spellGlyphs  = map[string]*spellGlyph{}
	spellOrder   []string
	spellHunts   []*spellHunt
	spellVolleys []*spellVolley
	spellGates   []*spellGate
	spellTrack   = map[int]*spellPos{} // each player's last positions (ObjScriptID), for lead aiming
	spellChain   []string              // glyphs to set off next frame
)

func init() {
	trapExt["cast_lvl"] = spellCastLvl
	trapExt["cast_mark"] = spellCastMark
	trapExt["spell_clear"] = spellClear
	trapExt["spell_glyph"] = func(a trapAct) { spellDetonate(a.Target, trapCaller) }
	trapExt["spell_arm"] = func(a trapAct) { spellArm(a.Target, true) }
	trapExt["spell_disarm"] = func(a trapAct) { spellArm(a.Target, false) }
}

func SpellVolley(v spellVolley) {
	SpellTrapsOn()
	vv := v
	vv.t0 = trapFrame
	spellVolleys = append(spellVolleys, &vv)
}

func SpellGate(g spellGate) {
	SpellTrapsOn()
	gg := g
	spellGates = append(spellGates, &gg)
}

// spellArm arms or disarms a volley, hunt, clock or zone by name.
func spellArm(name string, on bool) {
	for _, v := range spellVolleys {
		if v.Name == name {
			if on && !v.Armed {
				v.t0 = trapFrame
			}
			v.Armed = on
		}
	}
	for _, h := range spellHunts {
		if h.Name == name {
			h.Armed, h.t = on, 0
		}
	}
	if c := trapClocks[name]; c != nil {
		if on && !c.Armed {
			c.t0 = trapFrame
		}
		c.Armed = on
		if !on {
			trapSetGroup(c.Group, false)
		}
	}
	if z := trapZones[name]; z != nil {
		z.Armed = on
	}
}

// SpellTrapsOn starts the kind's frame tick (idempotent; every start line calls it).
func SpellTrapsOn() {
	if spellOn {
		return
	}
	spellOn = true
	ns.OnFrame(spellTick)
}

func SpellGlyph(name string, lvl int, spells ...string) {
	SpellTrapsOn()
	spellGlyphs[name] = &spellGlyph{Name: name, Lvl: lvl, Spells: spells}
	spellOrder = append(spellOrder, name)
}

func SpellHunt(h spellHunt) {
	SpellTrapsOn()
	hh := h
	spellHunts = append(spellHunts, &hh)
}

// spellOpt reads "key:N" from an option string ("lvl:2 lead:18").
func spellOpt(s, key string, def int) int {
	n := len(key)
	for i := 0; i+n < len(s); i++ {
		if s[i:i+n] != key || s[i+n] != ':' || (i > 0 && s[i-1] != ' ') {
			continue
		}
		v, j, neg := 0, i+n+1, false
		if j < len(s) && s[j] == '-' {
			neg = true
			j++
		}
		for ; j < len(s) && s[j] >= '0' && s[j] <= '9'; j++ {
			v = v*10 + int(s[j]-'0')
		}
		if neg {
			v = -v
		}
		return v
	}
	return def
}

// spellSource: the object named src if it is there, else the point.
func spellSource(src string, from ns.Pointf) ns.Positioner {
	if src != "" {
		if o := ns.Object(src); o != nil {
			return o
		}
	}
	return from
}

func spellCast(sp string, lvl int, src ns.Positioner, to ns.Positioner) {
	if lvl > 0 {
		ns.CastSpellLvl(spell.Spell(sp), lvl, src, to)
	} else {
		ns.CastSpell(spell.Spell(sp), src, to)
	}
}

func spellCastLvl(a trapAct) {
	spellCast(a.Spell, spellOpt(a.Text, "lvl", 0), spellSource(a.Target, a.From), a.To)
}

// spellAim: where a unit will be `lead` frames from now, by its last steps (a player's; others: where it stands).
func spellAim(u ns.Obj, lead int) ns.Pointf {
	p := u.Pos()
	if lead <= 0 {
		return p
	}
	t := spellTrack[u.ObjScriptID()]
	if t == nil || t.n < 4 {
		return p
	}
	last := t.hist[(t.n-1)%len(t.hist)]
	old := t.hist[(t.n-4)%len(t.hist)] // three frames before the last
	vx, vy := (last.X-old.X)/3, (last.Y-old.Y)/3
	return ns.Ptf(p.X+vx*float32(lead), p.Y+vy*float32(lead))
}

// A turn: casters taking turns (Westwood's death-ray statues): cast_mark with Target = the turn's name casts from
// its next point.
type spellTurn struct {
	pts []ns.Pointf
	k   int
}

var spellTurns = map[string]*spellTurn{}

func SpellTurn(name string, pts ...ns.Pointf) {
	SpellTrapsOn()
	spellTurns[name] = &spellTurn{pts: pts}
}

func spellCastMark(a trapAct) {
	if trapCaller == nil {
		return
	}
	src, from := a.Target, a.From
	if t := spellTurns[a.Target]; t != nil && len(t.pts) > 0 {
		from, src = t.pts[t.k%len(t.pts)], ""
		t.k++
	}
	to := spellAim(trapCaller, spellOpt(a.Text, "lead", 0))
	later := trapAct{Kind: "cast_lvl", Spell: a.Spell, Target: src, From: from, To: to,
		Text: "lvl:" + spellItoa(spellOpt(a.Text, "lvl", 0))}
	if a.Frames > 0 {
		trapQueue = append(trapQueue, trapPending{at: trapFrame + a.Frames, act: later})
	} else {
		spellCastLvl(later)
	}
}

func spellItoa(v int) string {
	if v == 0 {
		return "0"
	}
	neg := v < 0
	if neg {
		v = -v
	}
	var b []byte
	for v > 0 {
		b = append([]byte{byte('0' + v%10)}, b...)
		v /= 10
	}
	if neg {
		b = append([]byte{'-'}, b...)
	}
	return string(b)
}

func spellClear(a trapAct) {
	r := float64(a.Frames)
	if r <= 0 {
		r = 40
	}
	for _, o := range ns.FindAllObjects(ns.InCirclef{Center: a.From, R: r}, ns.HasTypeName{a.Text}) {
		o.Delete()
	}
}

func spellDist(a, b ns.Pointf) float32 {
	dx, dy := a.X-b.X, a.Y-b.Y
	return sqrt32(dx*dx + dy*dy)
}

// spellDetonate sets off a glyph as the engine's triggerTrap does: unowned, level 2 (or its own), each spell from
// the glyph (targeted ones at the toucher, place spells at the glyph's spot), blue sparks, then every glyph within
// 100 a frame later at the nearest player within 75.
func spellDetonate(name string, who ns.Obj) {
	g := spellGlyphs[name]
	if g == nil || g.done {
		return
	}
	o := ns.Object(name)
	if o != nil && !g.posSet {
		g.pos, g.posSet = o.Pos(), true
	}
	g.done = true
	if o == nil || uint32(o.Flags())&0x20 != 0 { // gone or being destroyed: the engine's glyph went off itself
		return
	}
	if who == nil {
		for _, pl := range ns.Players() {
			u := pl.Unit()
			if u != nil && u.CurrentHealth() > 0 && spellDist(u.Pos(), g.pos) <= 75 {
				who = u
				break
			}
		}
	}
	for _, sp := range g.Spells {
		switch sp {
		case "SPELL_SLOW", "SPELL_STUN", "SPELL_CONFUSE", "SPELL_FUMBLE", "SPELL_ANCHOR":
			if who != nil {
				spellCast(sp, g.Lvl, o, who)
			}
		default:
			spellCast(sp, g.Lvl, o, g.pos)
		}
	}
	ns.Effect(effect.BLUE_SPARKS, g.pos, g.pos)
	ns.AudioEvent(audio.Name("GlyphDetonate"), g.pos)
	o.Delete()
	for _, n := range spellOrder {
		h := spellGlyphs[n]
		if h == nil || h.done || n == name {
			continue
		}
		if !h.posSet {
			if ho := ns.Object(n); ho != nil {
				h.pos, h.posSet = ho.Pos(), true
			} else {
				continue
			}
		}
		if spellDist(h.pos, g.pos) <= 100 {
			spellChain = append(spellChain, n)
		}
	}
}

// spellInBox: is p in the box centred on c, hu along the unit vector u and hv across it?
func spellInBox(c, u ns.Pointf, hu, hv float32, p ns.Pointf) bool {
	dx, dy := p.X-c.X, p.Y-c.Y
	a := dx*u.X + dy*u.Y
	b := -dx*u.Y + dy*u.X
	if a < 0 {
		a = -a
	}
	if b < 0 {
		b = -b
	}
	return a <= hu && b <= hv
}

func spellTick() {
	// each player's last positions
	for _, pl := range ns.Players() {
		u := pl.Unit()
		if u == nil {
			continue
		}
		id := u.ObjScriptID()
		t := spellTrack[id]
		if t == nil {
			t = &spellPos{}
			spellTrack[id] = t
		}
		t.hist[t.n%len(t.hist)] = u.Pos()
		t.n++
	}
	// gates: a station's spells armed while someone is in it
	for _, g := range spellGates {
		occ := false
		for _, pl := range ns.Players() {
			u := pl.Unit()
			if u != nil && u.CurrentHealth() > 0 && spellInBox(g.C, g.U, g.HU, g.HV, u.Pos()) {
				occ = true
				break
			}
		}
		if occ != g.in {
			g.in = occ
			for _, t := range g.Targets {
				spellArm(t, occ)
			}
		}
	}
	// volleys
	for _, v := range spellVolleys {
		if !v.Armed || v.Period <= 0 {
			continue
		}
		t := (trapFrame - v.t0) % v.Period
		if t < 0 {
			t += v.Period
		}
		for _, s := range v.Shots {
			if s.T != t {
				continue
			}
			switch s.Kind {
			case "clear":
				spellClear(trapAct{From: s.From, Frames: int(s.R), Text: s.Text})
			case "sound":
				ns.AudioEvent(audio.Name(s.Text), s.From)
			default:
				spellCast(s.Spell, s.Lvl, spellSource(s.Src, s.From), s.To)
			}
		}
	}
	// glyphs set off by a neighbour last frame
	if len(spellChain) > 0 {
		chain := spellChain
		spellChain = nil
		for _, n := range chain {
			spellDetonate(n, nil)
		}
	}
	// hunts
	for _, h := range spellHunts {
		if !h.Armed {
			continue
		}
		var who ns.Obj
		for _, pl := range ns.Players() {
			u := pl.Unit()
			if u != nil && u.CurrentHealth() > 0 && spellInBox(h.C, h.U, h.HU, h.HV, u.Pos()) {
				who = u
				break
			}
		}
		if who == nil {
			h.t = 0
			continue
		}
		h.t++
		if h.t < h.Period {
			continue
		}
		h.t = 0
		to := spellAim(who, h.Lead)
		if h.Sound != "" {
			ns.AudioEvent(audio.Name(h.Sound), to)
		}
		trapQueue = append(trapQueue, trapPending{at: trapFrame + h.Delay, act: trapAct{Kind: "cast_lvl",
			Spell: h.Spell, Target: h.Src, From: h.From, To: to, Text: "lvl:" + spellItoa(h.Lvl)}})
	}
}
