"""Every well heals (QA round 1, nox13 and the well set's note, 2026-10-13: "Make sure that when wells appear in maps,
the player can interact with them to fully heal health and mana, like in the original nox campaign").

Westwood's campaign well is a `WishingWell`, a trigger whose ScriptOnPressed is the map's MakeAWish (Con02a, Con07B,
War01A, Wiz02A, decompiled): it restores the caller's health to full, prints GeneralPrint:WellSignRefresh ("You feel
refreshed after drinking from the well.") and plays RestoreHealth; a sign beside it reads GeneralPrint:WellSign
("Magical Well") in all thirteen of its campaign wells. The kit's town well is the plain `Well` (the user praised its
square, nox13), which is no trigger, so the healing is the script's: `wells.go` (written here into the map's scripts
by Spec.build) watches every player, and one who walks up against a well (within REACH px of its middle: the well's
own radius is 20, a player's about 12) drinks: health and mana to full, Westwood's line and sound. Once per visit: a
player drinks again after stepping LEAVE px away. Both kinds of well heal; a sign standing by a well with no text gets
Westwood's "Magical Well".

Spec.build calls apply(spec) before it writes the map; the checker's wells.heal rule (validate/checks_game.py) reads
wells.go back and errs on any well it does not cover. A test map can set `spec.heal_wells = False`.
"""
import math, re

WELLS = re.compile(r"^(Well|WishingWell)$")
REACH = 46.0                    # px from the well's middle: touching it
LEAVE = 90.0                    # px: stepped away, may drink again
SIGN_TEXT = "GeneralPrint:WellSign"      # "Magical Well"
SIGN_NEAR = 110.0               # px: a sign this near a well is the well's sign

GO = """package PKG

// Every well heals (dystopiannox mapgen/kit/wells.py; QA round 1, 2026-10-13). Westwood's MakeAWish (Con02a): the
// caller's health to full, GeneralPrint:WellSignRefresh, the RestoreHealth sound; ours fills mana too. A player who
// walks up against a well (within wellReach px of its middle) drinks once; he drinks again after stepping wellLeave px
// away.

import (
	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/audio"
)

const wellReach, wellLeave = REACH, LEAVE

var wellSpots = []ns.Pointf{
SPOTS}

var wellDrunk = map[int]bool{}   // player unit -> drank at the well he stands by (until he steps away)

func init() {
	ns.OnEachFrame(5, wellsTick)
}

func wellsTick() {
	for _, p := range ns.Players() {
		u := p.Unit()
		if u == nil || u.CurrentHealth() <= 0 {
			continue
		}
		id := u.ObjScriptID()
		near := float32(1e9)
		at := u.Pos()
		for _, w := range wellSpots {
			dx, dy := at.X-w.X, at.Y-w.Y
			if d := dx*dx + dy*dy; d < near {
				near = d
			}
		}
		if near > wellLeave*wellLeave {
			wellDrunk[id] = false
			continue
		}
		if near > wellReach*wellReach || wellDrunk[id] {
			continue
		}
		wellDrunk[id] = true
		WellDrink(u)
		p.Print("GeneralPrint:WellSignRefresh")
	}
}

// WellDrink restores u's health and mana to full, with Westwood's sound.
func WellDrink(u ns.Obj) {
	if u == nil {
		return
	}
	if lost := u.MaxHealth() - u.CurrentHealth(); lost > 0 {
		u.RestoreHealth(lost)
	}
	u.SetMana(u.MaxMana())
	ns.AudioEvent(audio.RestoreHealth, u)
}
"""


def spots(spec):
    return [(o["x"], o["y"]) for o in spec.d["objects"] if WELLS.match(str(o.get("type", "")))]


def go_source(pkg, pts):
    body = "".join(f"\t{{X: {x:.1f}, Y: {y:.1f}}},\n" for x, y in pts)
    return (GO.replace("package PKG", f"package {pkg}", 1).replace("REACH", f"{REACH:.1f}").replace("LEAVE", f"{LEAVE:.1f}")
            .replace("SPOTS}", body + "}"))


def apply(spec):
    """wells.go into spec.scripts when the map has a well; Westwood's "Magical Well" on a textless sign beside one.
    Returns the number of wells."""
    pts = spots(spec)
    if not pts or getattr(spec, "heal_wells", True) is False:
        spec.scripts.pop("wells.go", None)
        return 0
    spec.scripts["wells.go"] = go_source(spec.d["name"].lower(), pts)
    for o in spec.d["objects"]:
        if str(o.get("type", "")).startswith("Sign") and not (o.get("xfer") or {}).get("Text") and \
                any(math.hypot(o["x"] - x, o["y"] - y) <= SIGN_NEAR for x, y in pts):
            o.setdefault("xfer", {})["Text"] = SIGN_TEXT
    return len(pts)


def covered(src):
    """The well spots a wells.go source covers: [(x, y)]."""
    return [(float(a), float(b)) for a, b in re.findall(r"\{X: ([-\d.]+), Y: ([-\d.]+)\}", src or "")]
