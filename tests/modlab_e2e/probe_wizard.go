package PKG

// QA1 play probe for the Stormcaller (tests/modlab_e2e/lab.py play probe_wizard.go wizard; not part of the mod):
// a real Wizard (OpenNox e2e mode clicks to the east every moment) shoots the Lightning Staff at a held target;
// the probe logs every green chain and any health the target loses after it (the game's lightning, if not cut). Copied into the private data
// dir's maps\ModLab only.

import (
	"fmt"

	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/damage"
	"github.com/noxworld-dev/noxscript/ns/v4/enchant"
	"github.com/noxworld-dev/opennox-lib/object"
)

var (
	prF, prStage, prStageAt int
	prBase                  ns.Pointf
	prTarget                ns.Obj
	prOn                    bool
	prWarps, prKills        int
	prMaxD, prMinD          float32
	prSeen                  map[string]bool
	prHP0, prMaxChak        int
)

func prLog(a ...any) { println("probe:", fmt.Sprint(a...)) }

type prStageDef struct {
	name, weapon string
	hp           int
	frames       int
}

var prStages = []prStageDef{
	{"W4 stormcaller", "W4_Stormcaller_T0", 2000, 3000},
}

func init() { ns.OnFrame(prFrame) }

func prFrame() {
	h := ns.GetHost()
	if h == nil || !modStarted || ns.Object("W3_QuakeHammer") == nil {
		return
	}
	prF++
	if h.CurrentHealth() < 120 && prStages[prStage].name != "M4 matriarch" {
		h.RestoreHealth(200)
	}
	if prF == 60 { // hold the FireRing Flamebrand until the scripted clicks begin: its ring shows the first swing
		prBase = ns.Ptf(3680, 3910)
		h.SetPos(prBase)
		if w := ns.Object("W4_Stormcaller_T0"); w != nil {
			h.Pickup(w)
			h.SetStrength(200)
			h.SetMaxHealth(400)
			h.SetHealth(400)
			prLog("wizard equips the Stormcaller: ", h.Equip(w))
		}
	}
	if prF > 60 && prF < 5000 && !prOn && prF%3 == 0 {
		if prTarget == nil || !modAlive(prTarget) {
			prSpawn(prStageDef{"wait", "", 2000, 0})
		} else if prF%30 == 0 {
			prTarget.Enchant(enchant.HELD, ns.Seconds(2))
		}
		if modPoisoned > 0 {
			prF = 5000
			prLog("first staff strike seen (a green chain)")
		}
	}
	if prF == 5000+60 {
		prBase = ns.Ptf(3680, 3910) // the gallery's east end, P(330, -10)
		prOn = true
		h.SetStrength(200) // a fresh Warrior cannot lift a great sword or a war hammer
		h.SetMaxHealth(400)
		h.SetHealth(400)
		prLog("strength ", h.Strength(), ", health ", modHP(h))
		prLog("start: host ", modHP(h), " at ", int(h.Pos().X), ",", int(h.Pos().Y))
		prBegin(h, 0)
	}
	if !prOn {
		return
	}
	st := prStages[prStage]
	t := prF - prStageAt
	prWatch(h, st, t)
	if t >= st.frames {
		prEnd(h, st)
		if prStage+1 >= len(prStages) {
			prOn = false
			prLog("done")
			return
		}
		prBegin(h, prStage+1)
	}
}

func prBegin(h ns.Obj, k int) {
	prStage, prStageAt = k, prF
	st := prStages[k]
	prWarps, prKills, prMaxD, prMinD, prSeen, prMaxChak = 0, 0, 0, 1e9, map[string]bool{}, 0
	h.SetPos(prBase)
	h.LookWithAngle(0)
	if st.weapon != "" {
		w := ns.Object(st.weapon)
		if w == nil {
			prLog(st.name, ": weapon ", st.weapon, " not found")
		} else {
			if w.GetHolder() == nil || !modSame(w.GetHolder(), h) {
				prLog(st.name, ": pickup ", h.Pickup(w))
			}
			prLog(st.name, ": equip ", h.Equip(w))
		}
		kind, tier := modWielded(h)
		prLog(st.name, ": wielding ", kind, " tier ", tier)
		prSpawn(st)
	}
	switch st.name {
	case "M1 harpoon":
		if b := modBossByKind("ogrelord"); b != nil {
			b.o.SetPos(ns.Ptf(prBase.X-250, prBase.Y))
			b.engage()
			b.t3 = 150
		}
	case "M5 duelist":
		if b := modBossByKind("duelist"); b != nil {
			b.o.SetPos(ns.Ptf(prBase.X+45, prBase.Y))
			b.engage()
		}
	case "M4 matriarch":
		if b := modBossByKind("embermother"); b != nil {
			b.o.SetPos(ns.Ptf(prBase.X-45, prBase.Y)) // west: the player's swings go east
			b.engage()
			b.o.SetHealth(150)
			prHP0 = modStruck["embermother"]
		}
	}
	prLog("== ", st.name, " (host ", modHP(h), ")")
}

func prSpawn(st prStageDef) {
	prTarget = ns.CreateObject("GruntAxe", ns.Ptf(prBase.X+36, prBase.Y))
	if prTarget != nil {
		prTarget.SetMaxHealth(st.hp)
		prTarget.SetHealth(st.hp)
		prTarget.Enchant(enchant.HELD, ns.Seconds(10))
	}
}

var prLastPois, prTrack, prTrackHP int

func prWatch(h ns.Obj, st prStageDef, t int) {
	if st.name == "W4 stormcaller" && prTarget != nil {
		if modPoisoned != prLastPois {
			prLastPois = modPoisoned
			prTrack, prTrackHP = 36, prTarget.CurrentHealth()
			if t < 700 { prLog(st.name, ": green chain at frame ", t, " (poison casts ", modPoisoned, "), host RUN ", h.HasEnchant(enchant.RUN), ", target ", modHP(prTarget)) }
		} else if prTrack > 0 {
			prTrack--
			if hp := prTarget.CurrentHealth(); hp != prTrackHP {
				prLog(st.name, ":   frame ", t, ": target hp ", prTrackHP, " -> ", hp)
				prTrackHP = hp
			}
		}
	}
	if len(modBoomerangs) > prMaxChak {
		prMaxChak = len(modBoomerangs)
	}
	d := modDist(h.Pos(), prBase)
	if d > prMaxD {
		prMaxD = d
	}
	if st.weapon != "" {
		if prTarget != nil && t%30 == 0 && modAlive(prTarget) {
			prTarget.Enchant(enchant.HELD, ns.Seconds(2))
		}
		if d > 60 { // warped (W3): log, then back to the target
			prWarps++
			prLog(st.name, ": host ", int(d), " px from its stand at frame ", t)
			h.SetPos(prBase)
			h.LookWithAngle(0)
		}
		if prTarget != nil && !modAlive(prTarget) {
			prKills++
			prLog(st.name, ": kill ", prKills, " at frame ", t, ": hasted ", h.HasEnchant(enchant.HASTED), ", invisible ",
				h.HasEnchant(enchant.INVISIBLE), ", force field ", h.HasEnchant(enchant.SHIELD))
			var none ns.Obj
			prTarget = none
			if st.hp <= 1 {
				ns.NewTimer(ns.Frames(25), func() { prSpawn(st) })
			}
		}
		if prTarget != nil && modAlive(prTarget) {
			for _, e := range []enchant.Enchant{enchant.FREEZE, enchant.SLOWED} {
				if prTarget.HasEnchant(e) && !prSeen[string(e)] {
					prSeen[string(e)] = true
					prLog(st.name, ": target ", e, " at frame ", t, ", ", modHP(prTarget))
				}
			}
		}
		if st.name == "W1 small" && t%20 == 5 {
			n := 0
			for _, f := range ns.FindAllObjects(modRingFlames) {
				if f.HasOwner(h) && !f.Flags().Has(object.FlagDestroyed) {
					n++
				}
			}
			if n > 0 && !prSeen["ring"] {
				prSeen["ring"] = true
				prLog(st.name, ": the game's ring of fire: ", n, " flames at frame ", t)
			}
		}
		return
	}
	switch st.name {
	case "M1 harpoon":
		b := modBossByKind("ogrelord")
		if b == nil {
			return
		}
		od := modDist(h.Pos(), b.o.Pos())
		if b.hook != nil && b.hook.hooked && !prSeen["hooked"] {
			prSeen["hooked"] = true
			prLog(st.name, ": hooked at frame ", t, ", host ", int(od), " px from him")
		}
		if prSeen["hooked"] && !prSeen["reeled"] && b.hook == nil {
			prSeen["reeled"] = true
			prLog(st.name, ": rope let go at frame ", t, ", host ", int(od), " px from him, reeled ", modReeled, " frames")
		}
	case "M5 duelist":
		b := modBossByKind("duelist")
		if b != nil && t == 10 {
			prLog(st.name, ": hasted ", b.o.HasEnchant(enchant.HASTED), ", infravision ", b.o.HasEnchant(enchant.INFRAVISION))
		}
		if h.HasEnchant(enchant.SLOWED) && !prSeen["slowed"] {
			prSeen["slowed"] = true
			prLog(st.name, ": host slowed at frame ", t, " (his blows so far ", modStruck["duelist"], ")")
		}
	case "M4 matriarch":
		b := modBossByKind("embermother")
		if b != nil && t == 10 {
			prLog(st.name, ": protected from fire ", b.o.HasEnchant(enchant.PROTECT_FROM_FIRE), ", vampirism ",
				b.o.HasEnchant(enchant.VAMPIRISM))
		}
		if b != nil {
			for _, m := range b.minions { // no imps: her health then rises only by what she drinks
				if !m.dead && modAlive(m.o) {
					m.o.Delete()
				}
			}
			if n := modStruck["embermother"]; n != prHP0 {
				prHP0 = n
				prLog(st.name, ": her blow ", n, " at frame ", t, ": her hp now ", b.o.CurrentHealth(), ", host ", modHP(h))
			}
		}
		if b != nil && t == st.frames-30 {
			hp := h.CurrentHealth()
			b.o.Damage(nil, 5000, damage.BLADE)
			ns.NewTimer(ns.Frames(25), func() {
				prLog(st.name, ": she fell: ring flames ", modRingFlamesMade, ", host hp ", hp, " -> ", h.CurrentHealth())
			})
		}
	}
}

func prEnd(h ns.Obj, st prStageDef) {
	switch st.name {
	case "M1 harpoon", "M5 duelist":
		k := map[string]string{"M1 harpoon": "ogrelord", "M5 duelist": "duelist"}[st.name]
		if b := modBossByKind(k); b != nil {
			b.o.Damage(nil, 5000, damage.BLADE)
		}
	}
	if prTarget != nil && modAlive(prTarget) {
		prTarget.Delete()
	}
	prLog(st.name, ": end: warps ", prWarps, ", kills ", prKills, ", waves ", len(modWaves), " (flames ", modWaveMade,
		"), mana touches ", len(modManaTouched), ", burns ", modBurnHits, ", most chakrams in flight ", prMaxChak,
		", hooked ", modHooked, ", reeled ", modReeled, ", duelist blows ", modStruck["duelist"], ", second blades ",
		modSecondBlades, ", matriarch blows ", modStruck["embermother"], ", host ", modHP(h))
}
