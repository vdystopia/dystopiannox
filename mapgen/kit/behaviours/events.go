package PKG

// A creature's events shared by every script of the map (dystopiannox, 2026-10-09). An object keeps one callback per
// event, so the story (quests.go: a boss's death moves the quest on), the behaviour sets (behaviours.go: a sentry
// roused when hit) and the mods (mods.go: the new monsters' powers, the weapons' hit effects) each setting their own
// would undo one another. OnObjEvent subscribes instead: the object's event is set once, and it calls every
// subscriber in turn.

import "github.com/noxworld-dev/noxscript/ns/v4"

var evSubs = map[int]map[ns.ObjectEvent][]func(){}

// OnObjEvent runs f whenever o's event e fires, after the subscribers before it.
func OnObjEvent(o ns.Obj, e ns.ObjectEvent, f func()) {
	if o == nil {
		return
	}
	id := o.ObjScriptID()
	subs := evSubs[id]
	if subs == nil {
		subs = map[ns.ObjectEvent][]func(){}
		evSubs[id] = subs
	}
	if _, ok := subs[e]; !ok {
		subs[e] = nil
		o.OnEvent(e, func() {
			for _, g := range subs[e] {
				g()
			}
		})
	}
	subs[e] = append(subs[e], f)
}
