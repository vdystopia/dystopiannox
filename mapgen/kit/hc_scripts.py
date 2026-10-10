"""The Hollow Choir's own script pieces (campaign/hollowchoir), for what the shared kit does not do yet: a story flag
that runs a few lines of Go once (a boss rises out of the lava, a villain vanishes, a smith hands over a forged blade),
and allies who fight beside the player.

    from kit.hc_scripts import HcScript
    hc = HcScript(m.d["name"])
    hc.freeze("Morvaine")                                  # stands frozen where he was placed (a figure seen, not fought)
    hc.on_flag("ritual_broken", hc.vanish("Morvaine"), hc.rise("Matriarch", x, y))
    hc.on_flag("blade_forged", hc.hand_over("Forge_W1_3", "DoranAnvil"))
    hc.ally("Watch1", foes=[...], follow=True, dmg=9)      # fights beside the player once the story says so
    hc.on_flag("assault", hc.allies_go("Watch1", "Watch2"))
    hc.on_flag("morvaine_dead", hc.allies_release("Watch1", "Watch2"))
    m.scripts.update(hc.files())                           # hc_scripts.go + hc_scripts_config.go, beside quests.go

The flags are the story's own (kit/quests.py A.flag; quests.go's `flags`), or "dead:Name1,Name2" (every one dead):
both scripts are one package, so this file reads the story's flags directly and the story's lines read the flags set
here (`hc.set_flag` inside an action list).

Allies (OpenNox v1.9.0-alpha13 leaves MakeFriendly/MakeEnemy/BecomePet unimplemented: they panic). A creature whose
owner is the player is on the player's side: the engine's enemy test (server/object.go IsEnemyTo) follows each side's
owner chain to its player, so an owned creature and the player are never enemies and an owned creature and an
unowned one always are (as a conjurer's summoned creatures). SetOwner is implemented. So an ally is a creature (a
cloned person or a fighter) that the story hands to the player with SetOwner(host); it is ordered at the nearest foe
(Attack) and, because a cloned townsperson's own fighting cannot be relied on, its blows are also struck by the script
when it stands beside its foe (Damage), so the fight is won whatever the engine's AI makes of it. A follower comes after
the player through stairs and lifts (moved beside the player when he is suddenly far away); a holder keeps its floor
and, while the player is away, the fight there goes on off-screen. When the fight is over the story releases them
(SetOwner(nil), aggression 0): a creature the player owns would otherwise follow him into the next map.
"""
import json

HC_GO = r'''package PKG

// The Hollow Choir's own script pieces (dystopiannox mapgen/kit/hc_scripts.py): story flags that run Go once, and
// allies who fight beside the player (an ally is owned by the player: OpenNox's enemy test follows the owner chain,
// so it fights the Choir and never the player; MakeFriendly is not implemented in alpha13). Reads the story's flags
// (quests.go flagOn), which share this package.

import (
	"math"

	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/damage"
	"github.com/noxworld-dev/noxscript/ns/v4/effect"
	"github.com/noxworld-dev/opennox-lib/object"
)

func hcAlive(o ns.Obj) bool {
	// a cloned person has no health at all (max 0, immortal): alive while it exists (the play test, 2026-10-10:
	// Ilsa's watch counted as dead and never moved)
	return o != nil && (o.MaxHealth() == 0 || o.CurrentHealth() > 0) && !o.Flags().HasAny(object.FlagDead|object.FlagDestroyed)
}

func hcDist(a, b ns.Pointf) float32 {
	return float32(math.Hypot(float64(a.X-b.X), float64(a.Y-b.Y)))
}

func hcSame(a, b ns.Obj) bool {
	return a != nil && b != nil && a.ObjScriptID() == b.ObjScriptID()
}

// ---- story flags that run Go once ----------------------------------------------------------------------------------

type hcFlagAct struct {
	flag string
	fn   func()
	done bool
}

var hcFlagActs []*hcFlagAct

// HcOnFlag runs fn once, the first time the story's flag holds (a flag set by A.flag, or "dead:A,B").
func HcOnFlag(flag string, fn func()) {
	hcFlagActs = append(hcFlagActs, &hcFlagAct{flag: flag, fn: fn})
}

// HcFreeze holds a creature where it stands (a figure seen across the lava, not fought).
func HcFreeze(name string) {
	if o := ns.Object(name); o != nil {
		o.Freeze(true)
		o.AggressionLevel(0)
	}
}

// hcVanish: a creature goes in a burst of smoke (out of the map's play); one never brought into play stays unseen.
func hcVanish(name string) {
	o := ns.Object(name)
	if o == nil || !o.IsEnabled() {
		return
	}
	ns.Effect(effect.SMOKE_BLAST, o, nil)
	ns.Effect(effect.TELEPORT, o, nil)
	o.Freeze(false)
	o.Enable(false)
}

// hcSwap: the fighter `from` steps aside and the person `to` (placed out of the play) stands where it stood: a fighter
// with a word to say when the fight is done (a cloned person holds a dialogue, a fighter cannot). Nothing happens when
// the fighter never came into play or fell.
func hcSwap(from, to string) {
	f, t := ns.Object(from), ns.Object(to)
	if f == nil || t == nil || !f.IsEnabled() || !hcAlive(f) {
		return
	}
	p := f.Pos()
	f.Enable(false)
	t.Enable(true)
	t.SetPos(p)
	ns.Effect(effect.TELEPORT, p, nil)
}

// hcRise: a creature kept hidden comes up at (x, y) and goes for the player.
func hcRise(name string, x, y float32) {
	o := ns.Object(name)
	if o == nil {
		return
	}
	at := ns.Ptf(x, y)
	o.Enable(true)
	o.SetPos(at)
	ns.Effect(effect.SPARK_EXPLOSION, at, ns.Ptf(120, 0))
	ns.Effect(effect.JIGGLE, at, ns.Ptf(30, 0))
	if p := ns.GetHost(); p != nil {
		o.AggressionLevel(0.83)
		o.Attack(p)
	}
}

// hcMoveTo: a creature or person is moved to (x, y), with a puff (a swap off-screen: he went there).
func hcMoveTo(name string, x, y float32) {
	if o := ns.Object(name); o != nil {
		o.SetPos(ns.Ptf(x, y))
	}
}

// hcHandOver: the named item (a copy made in the map and kept sealed away) comes into the world at the giver's feet:
// the giver takes it into his pack and drops it, the game's own drop (a copy moved with SetPos falls out of the map's
// search index: kit/behaviours/mods.go modHandOver); failing that it goes into the player's pack. On a timer, as
// every pickup of these maps is (the copy was never just made, but the gate checks for it: TW-11).
func hcHandOver(item, giver string) {
	it, g := ns.Object(item), ns.Object(giver)
	if it == nil {
		println("hc: hand-over item", item, "not found")
		return
	}
	ns.NewTimer(ns.Frames(2), func() {
		if g != nil && g.Pickup(it) && g.Drop(it) {
			hcHanded(item, giver, g)
		} else if p := ns.GetHost(); p != nil && p.Pickup(it) {
			hcHanded(item, "the player's pack", p)
		} else if g != nil {
			it.SetPos(g.Pos())
		}
	})
}

func hcHanded(item, by string, at ns.Obj) {
	ns.Effect(effect.SPARK_EXPLOSION, at, ns.Ptf(90, 0))
	ns.Effect(effect.WHITE_FLASH, at, nil)
	println("hc:", item, "handed over by", by)
}

// ---- allies --------------------------------------------------------------------------------------------------------

type hcAllyT struct {
	name   string
	follow bool      // goes with the player (through stairs and lifts too); else holds its floor
	home   ns.Pointf // its post / the middle of the floor it holds
	hold   float32   // the floor's reach round home
	dmg    int       // a scripted blow, struck every second while it stands beside its foe
	foes   []string  // the Choir's creatures it fights, by name (and what the Choir raises: hcFoeTypes)
	blink  bool      // steps through space to stand behind its foe now and then (Vess, the Blink Duelist)
	blinkT int
	active bool
	target ns.Obj
	blowT  int
	orderT int
	farT   int
	awayT  int
}

var (
	hcAllies   []*hcAllyT
	hcFoeTypes = ns.HasTypeName{"Skeleton", "Imp"} // raised or birthed by the Choir's casters (unnamed)
)

// HcAlly declares an ally (the story starts it with hcAllyGo).
func HcAlly(name string, follow bool, hx, hy, hold float32, dmg int, blink bool, foes []string) {
	hcAllies = append(hcAllies, &hcAllyT{name: name, follow: follow, home: ns.Ptf(hx, hy), hold: hold, dmg: dmg,
		blink: blink, foes: foes})
}

// HcAllyHealth: an ally fighter's health set by script (a creature's HealthMultiplier in the map is not reliable:
// act 9's Vess, a Swordsman, came out with 64 of the 320 she was given, 2026-10-10)
func HcAllyHealth(name string, hp int) {
	if o := ns.Object(name); o != nil && hp > 0 {
		o.SetMaxHealth(hp)
		o.SetHealth(hp)
	}
}

func hcAllyOf(name string) *hcAllyT {
	for _, a := range hcAllies {
		if a.name == name {
			return a
		}
	}
	return nil
}

// hcAllyGo: the named allies come over to the player's side (owned by him) and fight.
func hcAllyGo(names ...string) {
	h := ns.GetHost()
	for _, n := range names {
		a, o := hcAllyOf(n), ns.Object(n)
		if a == nil || o == nil {
			println("hc: ally", n, "not found")
			continue
		}
		if !o.IsEnabled() {
			o.Enable(true)
		}
		o.Freeze(false)
		if h != nil {
			o.SetOwner(h)
		}
		o.AggressionLevel(0.83)
		a.active = true
		println("hc: ally", n, "fights")
	}
}

// hcAllyRelease: the fight is over; the allies are their own again (a creature the player owns would follow him into
// the next map) and stand down.
func hcAllyRelease(names ...string) {
	var none ns.Obj
	for _, n := range names {
		a, o := hcAllyOf(n), ns.Object(n)
		if a != nil {
			a.active = false
			a.target = none
		}
		if o == nil {
			continue
		}
		o.SetOwner(none)
		o.AggressionLevel(0)
		o.Idle()
	}
}

func (a *hcAllyT) isFoe(o ns.Obj) bool {
	if !hcAlive(o) || !o.IsEnabled() {
		return false
	}
	if h := ns.GetHost(); h != nil && (o.HasOwner(h) || hcSame(o, h)) {
		return false
	}
	return true
}

// pick: the nearest living foe within r of the point.
func (a *hcAllyT) pick(from ns.Pointf, r float32) ns.Obj {
	var best ns.Obj
	bd := r
	live := a.foes[:0]
	for _, n := range a.foes {
		f := ns.Object(n)
		if f == nil {
			continue // gone for good (a body removed): dropped, not looked up every frame again
		}
		live = append(live, n)
		if !a.isFoe(f) {
			continue
		}
		if d := hcDist(f.Pos(), from); d < bd {
			best, bd = f, d
		}
	}
	a.foes = live
	for _, f := range ns.FindAllObjects(ns.InCirclef{Center: from, R: float64(r)}, hcFoeTypes) {
		if !a.isFoe(f) {
			continue
		}
		if d := hcDist(f.Pos(), from); d < bd {
			best, bd = f, d
		}
	}
	return best
}

// beside: a clear point a step from p, toward q (where an ally who climbed after the player comes up).
func hcBeside(p, q ns.Pointf) ns.Pointf {
	for _, r := range []float32{46, 60, 34} {
		for k := 0; k < 8; k++ {
			ang := math.Atan2(float64(q.Y-p.Y), float64(q.X-p.X)) + float64(k)*math.Pi/4
			at := ns.Ptf(p.X+r*float32(math.Cos(ang)), p.Y+r*float32(math.Sin(ang)))
			if ns.FindClosestWall(at, ns.InCirclef{Center: at, R: 20.0}) == nil {
				return at
			}
		}
	}
	return p
}

func (a *hcAllyT) tick() {
	o := ns.Object(a.name)
	h := ns.GetHost()
	if o == nil || !a.active || !o.IsEnabled() || !hcAlive(o) || h == nil {
		return
	}
	pos := o.Pos()
	var none ns.Obj
	if a.follow {
		// the player took the stairs, a lift or a pentagram: the ally comes up after him
		if hcDist(pos, h.Pos()) > 650 {
			if a.farT++; a.farT >= 3 {
				a.farT = 0
				a.target = none
				o.SetPos(hcBeside(h.Pos(), pos))
				o.Follow(h)
			}
			return
		}
		a.farT = 0
	}
	// where it fights: round the player it goes with, or on the floor it holds
	from, reach := a.home, a.hold
	if a.follow {
		from, reach = h.Pos(), 420
	}
	if f := a.pick(from, reach); f != nil {
		if a.target == nil || !hcSame(a.target, f) {
			a.target = f
			a.orderT = 0
			o.Attack(f)
		}
		d := hcDist(pos, f.Pos())
		if a.blink {
			// the Blink Duelist steps through space to stand behind her foe and strike
			if a.blinkT++; a.blinkT >= 7 && d > 70 && d < 340 {
				fp := f.Pos()
				dx, dy := (fp.X-pos.X)/d, (fp.Y-pos.Y)/d
				to := ns.Ptf(fp.X+dx*45, fp.Y+dy*45)
				if ns.FindClosestWall(to, ns.InCirclef{Center: to, R: 20.0}) == nil {
					a.blinkT = 0
					ns.Effect(effect.TELEPORT, pos, nil)
					o.SetPos(to)
					ns.Effect(effect.TELEPORT, to, nil)
					o.LookAtObject(f)
					o.Attack(f)
					return
				}
			}
		}
		if d > 80 {
			a.blowT = 0
			if a.orderT++; a.orderT >= 4 { // the order renewed now and then (a lost path, a new foe in the way)
				a.orderT = 0
				o.Attack(f)
			}
		} else if a.blowT++; a.blowT >= 2 { // beside its foe: a blow a second, struck by the script
			a.blowT = 0
			o.LookAtObject(f)
			f.Damage(nil, a.dmg, damage.BLADE)
			ns.Effect(effect.DAMAGE_POOF, f, nil)
		}
		return
	}
	a.target = none
	if a.follow {
		if hcDist(pos, h.Pos()) > 110 {
			o.Follow(h)
		}
		return
	}
	if hcDist(pos, a.home) > 90 {
		o.WalkTo(a.home)
	}
}

// offScreen: an ally holding a floor while the player is far away keeps fighting there.
func (a *hcAllyT) offScreen() {
	o := ns.Object(a.name)
	h := ns.GetHost()
	if a.follow || !a.active || o == nil || !o.IsEnabled() || h == nil || hcDist(h.Pos(), a.home) < 600 {
		return
	}
	if f := a.pick(a.home, a.hold); f != nil {
		f.Damage(nil, a.dmg, damage.BLADE)
	}
}

// ---- the ticker ----------------------------------------------------------------------------------------------------

var (
	hcStarted bool
	hcTicks   int
	hcNames   []string // what the pieces name, for the self-check
)

// HcStart: once the config has declared everything.
func HcStart(names []string) {
	if hcStarted {
		return
	}
	hcStarted = true
	hcNames = names
	found := 0
	for _, n := range names {
		if ns.Object(n) != nil {
			found++
		} else {
			println("hc: missing", n)
		}
	}
	println("hc self-check: objects", found, "of", len(names), "- flag actions", len(hcFlagActs), "- allies", len(hcAllies))
	ns.OnEachFrame(15, hcTick)
}

func hcTick() {
	if ns.GetHost() == nil {
		return
	}
	hcTicks++
	for _, fa := range hcFlagActs {
		if !fa.done && flagOn(fa.flag) {
			fa.done = true
			fa.fn()
		}
	}
	for _, a := range hcAllies {
		a.tick()
		if hcTicks%4 == 0 {
			a.offScreen()
		}
	}
}
'''


def _go(s):
    return json.dumps(s, ensure_ascii=False)


class HcScript:
    """A map's own Go pieces (hc_scripts.go, the library, and hc_scripts_config.go, this map's calls)."""

    def __init__(self, map_name):
        self.map = map_name
        self.calls = []
        self.names = set()
        self.flags_set = set()

    # ---- Go statements for on_flag (each returns a list of statements) ---------------------------------------------
    def vanish(self, name):
        self.names.add(name)
        return [f"hcVanish({_go(name)})"]

    def swap(self, fighter, person):
        self.names |= {fighter, person}
        return [f"hcSwap({_go(fighter)}, {_go(person)})"]

    def rise(self, name, x, y):
        self.names.add(name)
        return [f"hcRise({_go(name)}, {x:.1f}, {y:.1f})"]

    def move_to(self, name, x, y):
        self.names.add(name)
        return [f"hcMoveTo({_go(name)}, {x:.1f}, {y:.1f})"]

    def hand_over(self, item, giver):
        self.names |= {item, giver}
        return [f"hcHandOver({_go(item)}, {_go(giver)})"]

    def allies_go(self, *names):
        self.names |= set(names)
        return [f"hcAllyGo({', '.join(_go(n) for n in names)})"]

    def allies_release(self, *names):
        return [f"hcAllyRelease({', '.join(_go(n) for n in names)})"]

    def set_flag(self, flag):
        """Sets a story flag (quests.go `flags`): the story's lines and events read it."""
        self.flags_set.add(flag)
        return [f"flags[{_go(flag)}] = true"]

    def chat(self, name, text, secs=4.0):
        self.names.add(name)
        return [f"if o := ns.Object({_go(name)}); o != nil {{ o.ChatStrTimer({_go(text)}, ns.Seconds({secs})) }}"]

    def say(self, text):
        return [f"ns.PrintStrToAll({_go(text)})"]

    # ---- declarations ----------------------------------------------------------------------------------------------
    def freeze(self, name):
        self.names.add(name)
        self.calls.append(f"HcFreeze({_go(name)})")

    def on_flag(self, flag, *stmts):
        """Runs the Go statements (from vanish, rise, hand_over, allies_go, ...) once, when the flag first holds."""
        body = "; ".join(s for part in stmts for s in part)
        self.calls.append(f"HcOnFlag({_go(flag)}, func() {{ {body} }})")

    def later(self, secs, *stmts):
        """Go statements run `secs` seconds later (inside an on_flag)."""
        body = "; ".join(x for part in stmts for x in part)
        return [f"ns.NewTimer(ns.Seconds({float(secs)}), func() {{ {body} }})"]

    def ally(self, name, foes, follow=True, home=(0.0, 0.0), hold=400.0, dmg=9, blink=False, hp=0):
        """An ally (started by allies_go): follow=True goes with the player (through transporters too); else it holds
        the floor round `home` (world px) within `hold` px, fighting there off-screen while the player is away."""
        self.names.add(name)
        self.calls.append(f"HcAlly({_go(name)}, {'true' if follow else 'false'}, {home[0]:.1f}, {home[1]:.1f}, "
                          f"{float(hold):.1f}, {int(dmg)}, {'true' if blink else 'false'}, []string{{{', '.join(_go(f) for f in foes)}}})")
        if hp: self.calls.append(f"HcAllyHealth({_go(name)}, {int(hp)})")

    def files(self):
        if not self.calls: return {}
        pkg = self.map.lower()
        cfg = (f"package {pkg}\n\n// {self.map}'s own script pieces (written by dystopiannox mapgen/kit/hc_scripts.py).\n\n"
               'import "github.com/noxworld-dev/noxscript/ns/v4"\n\n'
               "var hcSetUp bool\n\nfunc setUpHc() {\n\tif hcSetUp {\n\t\treturn\n\t}\n\thcSetUp = true\n" +
               "".join(f"\t{c}\n" for c in self.calls) +
               f"\tHcStart([]string{{{', '.join(_go(n) for n in sorted(self.names))}}})\n}}\n\n"
               "func init() {\n\tns.OnMapEvent(ns.MapInitialize, setUpHc)\n\thframes := 0\n"
               "\tns.OnEachFrame(1, func() {\n\t\tif hframes++; hframes == 30 {\n\t\t\tsetUpHc()\n\t\t}\n\t})\n}\n")
        return {"hc_scripts.go": HC_GO.replace("package PKG", f"package {pkg}", 1), "hc_scripts_config.go": cfg}
