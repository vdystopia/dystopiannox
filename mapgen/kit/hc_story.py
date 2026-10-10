"""The Hollow Choir's story helpers (campaign/hollowchoir): what kit/behaviours/quests.go cannot say on its own, written
as one more Go file of the map's package (hcstory.go), beside quests.go (whose flags it reads and sets) and mods.go
(whose monsters and power weapons it uses). Built for acts 4 and 5 (a duelist who yields and is spared or killed; a
courtier unmasked as a Bone Caller); any act may use it.

    from kit.hc_story import HcStory
    hc = HcStory(m)                                            # m: the nox.Spec (for the once-markers)
    hc.yield_at("Vess", "VessYield", 25, "vess_beaten", park=(x, y), text="Vess drops her blade ...")
    hc.doom("vess_doomed", "VessYield", "Vess", text="...")    # the person springs up as the foe again and fights on
    hc.vanish("vess_spared", "VessYield", text="...")          # the person steps through space and is gone
    hc.prize("Vess", "W5", text="...")                         # her blade (the Bloodthirst, W5) falls where she dies
    hc.give("ulla_paid", "W6", text="...")                     # a giver's thanks hands over a power weapon (W6)
    hc.take_near(x, y, 70, ("vess_beaten", "dead:Vess"), "BlueOrbKeyOfTheLich", "verse_taken", text="...")
    hc.late_boss("severin_turned", "bonecaller", "SeverinFoe", "Chancellor Severin", 420)
    m.scripts.update(hc.files(NAME))                            # needs quests.go; late_boss, prize and give of a
                                                                # weapon need mods.go too (Mods.attach or Mods.files)

- yield_at: the foe (a named creature, say a kit/mods monster) fights until its health falls under `pct` percent; then
  it is disabled and parked at `park` (off the floor, far from the fight, so a mods duelist cannot blink while it
  waits), the person (a clone placed disabled: A.disable in q.start) stands where it stood, enabled, and `flag` is set.
  A blow that kills it outright skips the yield (the story then reads its death).
- doom: when `flag` is set, the person is disabled and the foe comes back at the person's spot and attacks.
- vanish: when `flag` is set, the person goes in a flash (a duelist stepping through space).
- prize: when the creature is dead, an item (a kit/mods power weapon by its id, with its power: mods.go knows a weapon
  by its object) lies where it fell: a blade dropped by its owner.
- give: when `flag` is set, an item (a power weapon by its id) is made at the player's feet and picked up a few frames
  later, as quests.go gives its gifts (TW-11).
- take_near: when the player comes within r of a spot while any of `when` holds (flags, "dead:Name", "has:Type"), an
  item is given (a token: a verse rubbed off a tablet) and `flag` set.
- late_boss: when `flag` is set, the named creature becomes a kit/mods monster (mods.go ModBoss), awake: a monster
  registered at the start would use its powers while it still hid as a person (a Bone Caller raising skeletons round a
  courtier in his study).
prize, give and take_near happen once even across a saved game: the scripts' own memory is lost when a game is loaded,
so each is tied to a marker object laid off the map's floor (a ColorLight named HcOnce<n>) that it deletes when it
fires, and it never fires once its marker is gone (a deleted object stays deleted in a saved game). A token handed out
twice by accident would miscount a later act's tokens.
"""
import json


def _go(s):
    return json.dumps(s, ensure_ascii=False)


HC_GO = r'''package PKG

// The Hollow Choir's story helpers (written by dystopiannox mapgen/kit/hc_story.py): a foe who yields when beaten and
// is then spared or killed, a person who vanishes, an item handed over on a death, a flag or a spot, a monster woken
// late. It reads and sets the quests' flags (quests.go), wakes monsters with mods.go's ModBoss and arms weapons as
// mods.go knows them. A hand-over fires once even across a saved game: its marker object is deleted when it fires.

import (
	"strings"

	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/effect"
)

type hcYieldT struct {
	foe, person, flag, text string
	pct                     int
	park                    ns.Pointf
	done                    bool
}

type hcOnFlagT struct {
	kind, flag, a, b, text, marker string
	hp                             int
	done                           bool
}

type hcPrizeT struct {
	creature, typ, kind, text, marker string
	done                              bool
}

type hcTakeT struct {
	at                      ns.Pointf
	r                       float32
	when                    []string
	typ, flag, text, marker string
	done                    bool
}

var (
	hcYields  []*hcYieldT
	hcOnFlags []*hcOnFlagT
	hcPrizes  []*hcPrizeT
	hcTakes   []*hcTakeT
	hcReady   bool
	hcFrames  int
)

// HcYield: foe yields below pct percent of its health: parked at (px, py), disabled; person stands in its place.
func HcYield(foe, person string, pct int, flag string, px, py float32, text string) {
	hcYields = append(hcYields, &hcYieldT{foe: foe, person: person, pct: pct, flag: flag, park: ns.Ptf(px, py), text: text})
}

// HcDoom: when flag is set, person is disabled and foe springs up at its spot and attacks.
func HcDoom(flag, person, foe, text string) {
	hcOnFlags = append(hcOnFlags, &hcOnFlagT{kind: "doom", flag: flag, a: person, b: foe, text: text})
}

// HcVanish: when flag is set, person goes in a flash.
func HcVanish(flag, person, text string) {
	hcOnFlags = append(hcOnFlags, &hcOnFlagT{kind: "vanish", flag: flag, a: person, text: text})
}

// HcLateBoss: when flag is set, creature name becomes mods monster kind, awake, with hp health.
func HcLateBoss(flag, kind, name, label string, hp int) {
	hcOnFlags = append(hcOnFlags, &hcOnFlagT{kind: "boss", flag: flag, a: name, b: kind, text: label, hp: hp})
}

// HcGive: when flag is set, an item of type typ (a power weapon of mods.go when kind is one: "blood", "frost", ...)
// is made at the player's feet and picked up a few frames later, as quests.go gives its gifts; once (marker).
func HcGive(flag, typ, kind, text, marker string) {
	hcOnFlags = append(hcOnFlags, &hcOnFlagT{kind: "give", flag: flag, a: typ, b: kind, text: text, marker: marker})
}

// HcPrize: when creature is dead, an item of type typ (a power weapon when kind is one) lies where it fell; once.
func HcPrize(creature, typ, kind, text, marker string) {
	hcPrizes = append(hcPrizes, &hcPrizeT{creature: creature, typ: typ, kind: kind, text: text, marker: marker})
}

// HcTakeNear: when the player is within r of (x, y) and any of when (flags, "dead:Name,...") holds, an item of type
// typ is given and flag set; once.
func HcTakeNear(x, y, r float32, when []string, typ, flag, text, marker string) {
	hcTakes = append(hcTakes, &hcTakeT{at: ns.Ptf(x, y), r: r, when: when, typ: typ, flag: flag, text: text, marker: marker})
}

// hcOnce: the marker still stands (the hand-over has not happened in this game, saved or not): delete it and go on.
func hcOnce(marker string) bool {
	if marker == "" {
		return true
	}
	m := ns.Object(marker)
	if m == nil {
		return false
	}
	m.Delete()
	return true
}

// hcHolds: a flag of the quests, "dead:Name1,Name2" (every one dead, read from the world) or "has:Type" (the player
// carries an item of the type: a token).
func hcHolds(f string) bool {
	if strings.HasPrefix(f, "has:") {
		h := ns.GetHost()
		if h == nil {
			return false
		}
		for _, it := range h.Items() {
			if it != nil && it.Type() != nil && it.Type().Name() == f[4:] {
				return true
			}
		}
		return false
	}
	if strings.HasPrefix(f, "dead:") {
		for _, n := range strings.Split(f[5:], ",") {
			if o := ns.Object(n); o != nil && o.CurrentHealth() > 0 {
				return false
			}
		}
		return true
	}
	return flags[f]
}

// hcArm gives a weapon made at run time its power (mods.go: the weapons are known by their objects' script ids).
func hcArm(it ns.Obj, kind string) {
	if it == nil || kind == "" {
		return
	}
	modKind[it.ObjScriptID()] = kind
	modTier[it.ObjScriptID()] = 0
	modWeaponObjs = append(modWeaponObjs, it)
}

// hcHandOver makes an item at the player's feet and picks it up a few frames later (TW-11: never at once).
func hcHandOver(typ, kind string) {
	h := ns.GetHost()
	if h == nil {
		return
	}
	it := ns.CreateObject(typ, h)
	if it == nil {
		return
	}
	hcArm(it, kind)
	holder, item := h, it
	ns.NewTimer(ns.Frames(6), func() {
		if holder != nil && item != nil && item.GetHolder() == nil {
			holder.Pickup(item)
		}
	})
}

func hcSay(text string) {
	if text != "" {
		ns.PrintStrToAll(text)
	}
}

func hcYieldFrame(y *hcYieldT) {
	if y.done {
		return
	}
	f := ns.Object(y.foe)
	if f == nil || !f.IsEnabled() || f.CurrentHealth() <= 0 {
		return
	}
	mx := f.MaxHealth()
	if mx <= 0 || f.CurrentHealth()*100 >= mx*y.pct {
		return
	}
	y.done = true
	at := f.Pos()
	ns.Effect(effect.SMOKE_BLAST, at, nil)
	f.Enable(false)
	f.SetPos(y.park)
	if p := ns.Object(y.person); p != nil {
		p.SetPos(at)
		p.Enable(true)
		if h := ns.GetHost(); h != nil {
			p.LookAtObject(h)
		}
	}
	flags[y.flag] = true
	hcSay(y.text)
	println("hcstory:", y.foe, "yields")
}

func hcOnFlagFrame(t *hcOnFlagT) {
	if t.done || !flags[t.flag] {
		return
	}
	t.done = true
	switch t.kind {
	case "doom":
		p := ns.Object(t.a)
		f := ns.Object(t.b)
		if f == nil {
			return
		}
		at := f.Pos()
		if p != nil {
			at = p.Pos()
			p.Enable(false)
		}
		f.SetPos(at)
		f.Enable(true)
		f.AggressionLevel(0.83)
		if h := ns.GetHost(); h != nil {
			f.Attack(h)
		}
		ns.Effect(effect.SMOKE_BLAST, at, nil)
		hcSay(t.text)
	case "vanish":
		if p := ns.Object(t.a); p != nil {
			ns.Effect(effect.TELEPORT, p.Pos(), nil)
			p.Enable(false)
		}
		hcSay(t.text)
	case "boss":
		if ns.Object(t.a) != nil {
			ModBoss(t.b, t.a, t.text, t.hp, 0, 0)
		}
	case "give":
		if !hcOnce(t.marker) {
			return
		}
		hcHandOver(t.a, t.b)
		hcSay(t.text)
	}
	println("hcstory:", t.kind, t.a, "on", t.flag)
}

func hcPrizeFrame(p *hcPrizeT) {
	if p.done {
		return
	}
	c := ns.Object(p.creature)
	if c != nil && c.CurrentHealth() > 0 {
		return
	}
	p.done = true
	if !hcOnce(p.marker) {
		return
	}
	var at ns.Pointf
	if c != nil {
		at = c.Pos()
	} else if h := ns.GetHost(); h != nil {
		at = h.Pos()
	} else {
		return
	}
	it := ns.CreateObject(p.typ, at)
	hcArm(it, p.kind)
	hcSay(p.text)
	println("hcstory: prize", p.typ, "for", p.creature)
}

func hcTakeFrame(t *hcTakeT) {
	h := ns.GetHost()
	if t.done || h == nil {
		return
	}
	hp := h.Pos()
	dx, dy := hp.X-t.at.X, hp.Y-t.at.Y
	if dx*dx+dy*dy > t.r*t.r {
		return
	}
	ok := false
	for _, w := range t.when {
		if hcHolds(w) {
			ok = true
			break
		}
	}
	if !ok {
		return
	}
	t.done = true
	if !hcOnce(t.marker) {
		return
	}
	hcHandOver(t.typ, "")
	flags[t.flag] = true
	hcSay(t.text)
	println("hcstory: took", t.typ)
}

func hcFrame() {
	if !hcReady {
		return
	}
	if hcFrames++; hcFrames%3 != 0 || ns.GetHost() == nil {
		return
	}
	for _, y := range hcYields {
		hcYieldFrame(y)
	}
	for _, t := range hcOnFlags {
		hcOnFlagFrame(t)
	}
	for _, p := range hcPrizes {
		hcPrizeFrame(p)
	}
	for _, t := range hcTakes {
		hcTakeFrame(t)
	}
}

var hcSetUpDone bool

func hcSetUp() {
	if hcSetUpDone {
		return
	}
	hcSetUpDone = true
/*CALLS*/	hcReady = true
	found, names := 0, []string{/*NAMES*/}
	for _, n := range names {
		if ns.Object(n) != nil {
			found++
		} else {
			println("hcstory: missing", n)
		}
	}
	println("hcstory self-check: objects", found, "of", len(names))
}

func init() {
	ns.OnFrame(hcFrame)
	ns.OnMapEvent(ns.MapInitialize, hcSetUp)
	hcf := 0
	ns.OnEachFrame(1, func() {
		if hcf++; hcf == 30 {
			hcSetUp()
		}
	})
}
'''


class HcStory:
    MARK_AT = (30.0, 30.0)          # world px off the map's floor, in its top corner: where the once-markers lie

    def __init__(self, spec):
        self.spec = spec
        self.calls, self.names, self.late = [], set(), False
        self._marks = 0

    def _marker(self):
        """A ColorLight off the map's floor, named for the script: deleted when its hand-over fires."""
        import os
        self._marks += 1
        name = f"HcOnce{self._marks}"
        here = os.path.dirname(os.path.abspath(__file__))
        presets = json.load(open(os.path.join(here, "..", "..", "rules", "out", "lighting.json")))["colorlight"]["presets"]
        xf = dict(min(presets, key=lambda p: p["xfer"].get("LightIntensity", 99))["xfer"])     # Westwood's faintest
        self.spec.obj_px("ColorLight", self.MARK_AT[0] + 4 * self._marks, self.MARK_AT[1], scr=name, xfer=xf)
        self.names.add(name)
        return name

    @staticmethod
    def _item(item):
        """(type, power) of an item: a kit/mods weapon id (W5) or a plain item type."""
        from kit.mods import WEAPONS
        if item in WEAPONS: return WEAPONS[item]["base"], WEAPONS[item]["kind"]
        return item, ""

    def yield_at(self, foe, person, pct, flag, park, text=""):
        self.calls.append(f"HcYield({_go(foe)}, {_go(person)}, {int(pct)}, {_go(flag)}, {park[0]:.1f}, {park[1]:.1f}, "
                          f"{_go(text)})")
        self.names |= {foe, person}

    def doom(self, flag, person, foe, text=""):
        self.calls.append(f"HcDoom({_go(flag)}, {_go(person)}, {_go(foe)}, {_go(text)})")
        self.names |= {person, foe}

    def vanish(self, flag, person, text=""):
        self.calls.append(f"HcVanish({_go(flag)}, {_go(person)}, {_go(text)})")
        self.names.add(person)

    def late_boss(self, flag, kind, name, label, hp):
        self.calls.append(f"HcLateBoss({_go(flag)}, {_go(kind)}, {_go(name)}, {_go(label)}, {int(hp)})")
        self.names.add(name)
        self.late = True

    def give(self, flag, item, text=""):
        """When `flag` is set (a giver's thanks), `item` (a kit/mods weapon id such as "W6", or a plain type) is made at
        the player's feet with its power and picked up a few frames later: A.give makes a plain object of the type,
        which a power weapon's script would not know. A weapon's tier is its first (W2, W4, W5, W6 have one). Once."""
        t, kind = self._item(item)
        self.calls.append(f"HcGive({_go(flag)}, {_go(t)}, {_go(kind)}, {_go(text)}, {_go(self._marker())})")

    def prize(self, creature, item, text=""):
        """When `creature` is dead, `item` (a kit/mods weapon id or a plain type) lies where it fell, with its power.
        Once."""
        t, kind = self._item(item)
        self.calls.append(f"HcPrize({_go(creature)}, {_go(t)}, {_go(kind)}, {_go(text)}, {_go(self._marker())})")
        self.names.add(creature)

    def take_near(self, x, y, r, when, item, flag, text=""):
        """When the player is within `r` px of (x, y) and any of `when` holds (flags; "dead:Name" and "has:Type" read
        from the world, so they hold after a saved game is loaded), `item` (a type: a token) is given and `flag` set
        (q.when_true can write the journal). Once."""
        t, _ = self._item(item)
        ws = "[]string{" + ", ".join(_go(w) for w in when) + "}"
        self.calls.append(f"HcTakeNear({x:.1f}, {y:.1f}, {float(r):.1f}, {ws}, {_go(t)}, {_go(flag)}, {_go(text)}, "
                          f"{_go(self._marker())})")

    def files(self, map_name):
        """{"hcstory.go": source} for the map's package (map_name.lower())."""
        if not self.calls: return {}
        src = HC_GO.replace("package PKG", f"package {map_name.lower()}", 1)
        src = src.replace("/*CALLS*/", "".join(f"\t{c}\n" for c in self.calls))
        src = src.replace("/*NAMES*/", ", ".join(_go(n) for n in sorted(self.names)))
        return {"hcstory.go": src}
