package PKG

// Quests for generated maps (dystopiannox mapgen/kit/quests.py writes this file, with the map's package name, into the
// map's folder, beside quests_config.go which declares who says what and what happens).
//
// What the player hears is text from the game's string table, by key (TellStory, JournalEntry): mapgen/strings.py
// puts each map's own lines into nox.csf.json, which OpenNox reads in place of nox.csf. No audio is recorded yet.
//
// OpenNox v1.9.0-alpha13 leaves some NoxScript calls unimplemented (they panic): GetQuestStatus/SetQuestStatus,
// TellStoryStr, JournalEntryStr/JournalEdit, MakeFriendly/MakeEnemy, GiveXp. This file uses none of them: quest
// stages live in the script, text goes through TellStory and JournalEntry by key, and narration through PrintStr.
//
// The parts:
//   Talker:   an NPC whose conversation is picked by the quest stages and what the player carries: the first of its
//             lines whose conditions hold. A line may ask a yes/no question; its actions run when the talk ends (on
//             "yes" for a question, Else on "no").
//   OnDeath:  actions when a named creature dies (a leader drops what he carried; a stage moves on).
//   OnAllDead: actions when every creature of a group is dead (the wolves are gone).
//   Near:     actions when the player first comes within reach of a spot (a voice from the dark, a discovery).
//   OnPickup: actions when the player first carries an item of a type (the emerald is found).
//   Actions:  stage, flag, give, take, gold, journal, print, chat, unlock, lock, enable, disable, hunt, open.

import (
	"strings"

	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/audio"
)

// ---- state -------------------------------------------------------------------------------------------------------

var (
	stages = map[string]int{}
	flags  = map[string]bool{}
)

// Act is one thing that happens: Kind with its arguments (see run).
type Act struct {
	Kind string
	A    string
	B    string
	N    int
}

// Cond: when a line or an event applies. Quest "" or Stage -1 match any stage; Has: the player carries an item of
// that type; Flag / Not: a flag is set / not set.
type Cond struct {
	Quest string
	Stage int
	Has   string
	Flag  string
	Not   string
}

// Line is one thing a talker says (Text: a string key), when Cond holds; Do runs when the talk ends (on "yes" if Ask),
// Else on "no".
type Line struct {
	When Cond
	Text string
	Ask  bool
	Do   []Act
	Else []Act
}

func player() ns.Obj { return ns.GetHost() }

func carries(p ns.Obj, typ string) ns.Obj {
	if p == nil || typ == "" {
		return nil
	}
	for _, it := range p.Items() {
		if it != nil && it.Type() != nil && it.Type().Name() == typ {
			return it
		}
	}
	return nil
}

func holds(c Cond) bool {
	if c.Quest != "" && c.Stage >= 0 && stages[c.Quest] != c.Stage {
		return false
	}
	if c.Has != "" && carries(player(), c.Has) == nil {
		return false
	}
	if c.Flag != "" && !flagOn(c.Flag) {
		return false
	}
	if c.Not != "" && flagOn(c.Not) {
		return false
	}
	return true
}

// flagOn: a flag set by the story, or "dead:Name1,Name2", true when every one of those creatures is dead. Deaths are
// read from the world, not remembered, so they hold after a saved game is loaded and the script starts afresh.
func flagOn(f string) bool {
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

// run performs the actions in turn. at: where something dropped should land (a creature that died), or nil.
func run(acts []Act, at ns.Positioner) {
	p := player()
	for _, a := range acts {
		switch a.Kind {
		case "stage": // A quest, N stage
			stages[a.A] = a.N
		case "advance": // A quest, N steps on (things done in any order, counted)
			stages[a.A] += a.N
		case "flag":
			flags[a.A] = true
		case "unflag":
			flags[a.A] = false
		case "give": // A item type, N count: into the player's pack
			n := a.N
			if n < 1 {
				n = 1
			}
			for i := 0; i < n && p != nil; i++ {
				if it := ns.CreateObject(a.A, p); it != nil {
					p.Pickup(it)
				}
			}
		case "drop": // A item type at the spot (where the creature fell)
			if at == nil {
				at = p
			}
			if at != nil {
				ns.CreateObject(a.A, at)
			}
		case "spawn": // A object type at the place of object B (a flame on a relit shrine)
			if o := ns.Object(a.B); o != nil {
				ns.CreateObject(a.A, o)
			}
		case "take": // A item type out of the player's pack
			if it := carries(p, a.A); it != nil {
				it.Delete()
			}
		case "gold":
			if p != nil {
				p.ChangeGold(a.N)
			}
		case "journal": // A string key, N entry type (2 quest, 4 completed, 8 hint)
			if p != nil {
				ns.JournalEntry(p, ns.StringID(a.A), ns.EntryType(a.N))
			}
		case "print": // A plain text for the player's screen
			ns.PrintStrToAll(a.A)
		case "chat": // A object, B plain text over its head
			if o := ns.Object(a.A); o != nil {
				o.ChatStrTimer(a.B, ns.Seconds(4))
			}
		case "unlock":
			if o := ns.Object(a.A); o != nil {
				o.Lock(false)
			}
		case "lock":
			if o := ns.Object(a.A); o != nil {
				o.Lock(true)
			}
		case "enable":
			if o := ns.Object(a.A); o != nil {
				o.Enable(true)
			}
		case "disable":
			if o := ns.Object(a.A); o != nil {
				o.Enable(false)
			}
		case "hunt": // A creature turns on the player
			if o := ns.Object(a.A); o != nil && p != nil {
				o.Enable(true)
				o.AggressionLevel(0.83)
				o.Attack(p)
			}
		case "walk": // A creature walks to waypoint B
			if o, w := ns.Object(a.A), ns.Waypoint(a.B); o != nil && w != nil {
				o.Move(w)
			}
		}
	}
}

// ---- talkers -----------------------------------------------------------------------------------------------------

type talker struct {
	obj   ns.Obj
	lines []Line
	cur   int  // the line picked when the talk began
	ask   bool // the dialog type set on the creature: yes/no or plain
	set   bool
}

var talkers = map[string]*talker{}

// lineKeys: every string key the story uses (set by the config, for the self-check)
var lineKeys []string

func pick(t *talker) int {
	for i, l := range t.lines {
		if holds(l.When) {
			return i
		}
	}
	return -1
}

// arm sets the creature's dialog to the type its next line needs (a question needs the yes/no dialog).
func arm(t *talker) {
	i := pick(t)
	ask := i >= 0 && t.lines[i].Ask
	if t.set && ask == t.ask {
		return
	}
	typ := ns.DialogNormal
	if ask {
		typ = ns.DialogYesNo
	}
	ns.SetDialog(t.obj, typ, dialogStart, dialogEnd)
	t.ask, t.set = ask, true
}

func talkerOf(o ns.Obj) *talker {
	if o == nil {
		return nil
	}
	for _, t := range talkers {
		if t.obj == o {
			return t
		}
	}
	return nil
}

// dialogStart and dialogEnd serve every talker: OpenNox calls them with the player as the caller and the creature
// spoken to as the trigger.
func dialogStart() {
	t := talkerOf(ns.GetTrigger())
	if t == nil {
		t = talkerOf(ns.GetCaller())
	}
	if t == nil {
		return
	}
	t.cur = pick(t)
	if t.cur < 0 {
		return
	}
	if p := player(); p != nil {
		t.obj.LookAtObject(p)
	}
	ns.TellStory(audio.Name(""), ns.StringID(t.lines[t.cur].Text))
}

func dialogEnd() {
	t := talkerOf(ns.GetTrigger())
	if t == nil {
		t = talkerOf(ns.GetCaller())
	}
	if t == nil || t.cur < 0 || t.cur >= len(t.lines) {
		return
	}
	l := t.lines[t.cur]
	t.cur = -1
	if l.Ask {
		switch ns.GetAnswer(t.obj) {
		case ns.AnswerYes:
			run(l.Do, t.obj)
		case ns.AnswerNo:
			run(l.Else, t.obj)
		}
	} else {
		run(l.Do, t.obj)
	}
	arm(t)
}

// Talker gives a named creature its lines (first match wins, so put the later stages first).
func Talker(name string, lines []Line) {
	o := ns.Object(name)
	if o == nil {
		println("quests: no talker", name)
		return
	}
	t := &talker{obj: o, lines: lines, cur: -1}
	talkers[name] = t
	arm(t)
}

// ---- events ------------------------------------------------------------------------------------------------------

// OnDeath runs acts when the named creature dies, dropping things where it fell.
func OnDeath(name string, acts []Act) {
	o := ns.Object(name)
	if o == nil {
		println("quests: no creature", name)
		return
	}
	done := false
	o.OnEvent(ns.EventDeath, func() {
		if done {
			return
		}
		done = true
		run(acts, ns.Ptf(o.Pos().X, o.Pos().Y))
	})
}

// OnAllDead runs acts when every named creature is dead.
func OnAllDead(names []string, acts []Act) {
	left := 0
	for _, n := range names {
		o := ns.Object(n)
		if o == nil {
			continue
		}
		left++
		dead := false
		o.OnEvent(ns.EventDeath, func() {
			if dead {
				return
			}
			dead = true
			left--
			if left == 0 {
				run(acts, ns.Ptf(o.Pos().X, o.Pos().Y))
			}
		})
	}
}

type watch struct {
	kind  string // "near" or "pickup"
	x, y  float32
	r     float32
	typ   string
	when  Cond
	acts  []Act
	fired bool
}

var watches []*watch

// Near runs acts once, the first time the player comes within r px of (x, y) while `when` holds.
func Near(x, y, r float32, when Cond, acts []Act) {
	watches = append(watches, &watch{kind: "near", x: x, y: y, r: r, when: when, acts: acts})
}

// OnPickup runs acts once, the first time the player carries an item of type typ while `when` holds.
func OnPickup(typ string, when Cond, acts []Act) {
	watches = append(watches, &watch{kind: "pickup", typ: typ, when: when, acts: acts})
}

// Quests starts the watchers: twice a second the spots and the player's pack are checked, and each talker's dialog
// is re-armed (what the player carries can change which line comes next).
func Quests() {
	ns.OnEachFrame(15, func() {
		p := player()
		if p == nil {
			return
		}
		for _, w := range watches {
			if w.fired || !holds(w.when) {
				continue
			}
			switch w.kind {
			case "near":
				dx, dy := p.Pos().X-w.x, p.Pos().Y-w.y
				if dx*dx+dy*dy > w.r*w.r {
					continue
				}
			case "pickup":
				if carries(p, w.typ) == nil {
					continue
				}
			}
			w.fired = true
			run(w.acts, p)
		}
		for _, t := range talkers {
			if t.cur < 0 {
				arm(t)
			}
		}
	})
}

// Start runs acts once the map has begun (lock the gate, hide the exit, the opening journal entry).
func Start(acts []Act) {
	started := false
	ns.OnEachFrame(10, func() {
		if started || player() == nil {
			return
		}
		started = true
		run(acts, nil)
	})
}

// QuestCheck prints, once the map runs, how many of the objects the story names the script can find (the server log
// shows it with no player in the game).
func QuestCheck(names []string) {
	done := false
	ns.OnEachFrame(15, func() {
		if done {
			return
		}
		done = true
		found := 0
		for _, n := range names {
			if ns.Object(n) != nil {
				found++
			} else {
				println("quests: missing", n)
			}
		}
		println("quests self-check: objects", found, "of", len(names), "- lines", len(lineKeys))
	})
}

// Portrait sets the face shown in the creature's dialogue window (Westwood's: TheogrinPic, MaidenPic2,
// GalavaPriestPic, Warrior2Pic, MalePic1-9, Townsman2Pic-4Pic, ...).
func Portrait(name, pic string) {
	if o := ns.Object(name); o != nil {
		ns.StoryPic(o, pic)
	}
}
