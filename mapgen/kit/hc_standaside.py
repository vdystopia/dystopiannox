"""The Hollow Choir: hostile creatures that stand aside while a story condition holds (acts 6 and 7).

Act 6: under Rusk's parley Gruthak's warband stands back to watch the duel (a quest flag). Act 7: while the player
carries the Choir's reliquary the barrow's outer wardens take him for one of the Choir (an item carried). The kit has
no way to keep a hostile creature visible and harmless (a disabled one vanishes; aggressiveness alone does not hold a
monster back), so the creatures are frozen in place while the condition holds, as kit/behaviours/mods.go freezes its
monsters until they wake. Struck while frozen (its health drops), the whole group wakes at once and falls on the
player, and stands aside no more: the disguise or the truce is broken.

    aside = StandAside(q)                                     # q: the map's QuestBook (its setup runs the calls)
    aside.group(["CampGrunt1", ...], flag="parley", wake="The parley is broken!", broken="parley_broken")
    aside.group(["Warden1", ...], item="WhiteOrb", wake="...", broken="wardens_woke")
    m.scripts.update(aside.files(NAME))                      # hc_standaside.go, beside quests.go (same package)

The condition: `flag` (a quest flag, kit/behaviours/quests.go `flags`) and/or `item` (the player carries an item of
that type, quests.go `carries`). `broken` sets a quest flag when the group wakes (lines can read it). Shared-kit
proposal: a `q.stand_aside(...)` in kit/quests.py and this loop in quests.go.
"""
import json

GO = r'''package PKG

// The Hollow Choir (dystopiannox mapgen/kit/hc_standaside.py): creatures that stand aside, frozen at their posts,
// while a story condition holds (a quest flag; the player carrying an item). Struck while frozen, the whole group wakes
// and falls on the player, and stands aside no more.

import "github.com/noxworld-dev/noxscript/ns/v4"

type hcAsideGroup struct {
	names  []string
	flag   string
	item   string
	wake   string
	broken string
	frozen map[string]bool
	hp     map[string]int
	done   bool
}

var hcAsideGroups []*hcAsideGroup

// StandAside registers a group: frozen while `flag` is set (if given) and the player carries `item` (if given).
func StandAside(names []string, flag, item, wake, broken string) {
	hcAsideGroups = append(hcAsideGroups, &hcAsideGroup{names: names, flag: flag, item: item, wake: wake,
		broken: broken, frozen: map[string]bool{}, hp: map[string]int{}})
}

func hcAsideHolds(g *hcAsideGroup) bool {
	if g.flag != "" && !flags[g.flag] {
		return false
	}
	if g.item != "" && carries(player(), g.item) == nil {
		return false
	}
	return true
}

func hcAsideWake(g *hcAsideGroup, h ns.Obj) {
	g.done = true
	if g.broken != "" {
		flags[g.broken] = true
	}
	if g.wake != "" {
		ns.PrintStrToAll(g.wake)
	}
	for _, n := range g.names {
		o := ns.Object(n)
		if o == nil || o.CurrentHealth() <= 0 {
			continue
		}
		o.Freeze(false)
		g.frozen[n] = false
		o.AggressionLevel(0.83)
		if h != nil {
			o.Attack(h)
		}
	}
}

func hcAsideFrame() {
	h := player()
	if h == nil {
		return
	}
	for _, g := range hcAsideGroups {
		if g.done {
			continue
		}
		hold := hcAsideHolds(g)
		struck := false
		for _, n := range g.names {
			o := ns.Object(n)
			if o == nil || o.CurrentHealth() <= 0 {
				continue
			}
			if hold {
				if !g.frozen[n] {
					o.Freeze(true)
					g.frozen[n] = true
					g.hp[n] = o.CurrentHealth()
				} else if o.CurrentHealth() < g.hp[n] {
					struck = true // a frozen creature may not report the hit: its health tells
				}
			} else if g.frozen[n] {
				o.Freeze(false)
				g.frozen[n] = false
			}
		}
		if struck {
			hcAsideWake(g, h)
		}
	}
}

func init() {
	ns.OnEachFrame(15, hcAsideFrame)
}
'''


class StandAside:
    def __init__(self, q):
        self.q = q
        self.groups = []

    def group(self, names, flag="", item="", wake="", broken=""):
        """Creatures `names` stand aside (frozen) while `flag` is set and/or the player carries `item`."""
        names = list(names)
        assert flag or item, "a group stands aside on a flag, an item carried, or both"
        self.groups.append(names)
        self.q.names |= set(names)
        self.q.calls.append(f"StandAside([]string{{{', '.join(json.dumps(n) for n in names)}}}, {json.dumps(flag)}, "
                            f"{json.dumps(item)}, {json.dumps(wake)}, {json.dumps(broken)})")
        return names

    def files(self, map_name):
        if not self.groups: return {}
        return {"hc_standaside.go": GO.replace("package PKG", f"package {map_name.lower()}", 1)}
