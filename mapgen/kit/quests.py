"""Quests, dialogue and events for a generated map (kit/behaviours/quests.go runs them in OpenNox).

A map's story is declared here: who says what at each stage of each quest, what each line does (give an item, pay
gold, write the journal, unlock a door, open the gate), and what happens when a creature dies, the player reaches a
spot or picks up an item. Every line of text gets a key in the map's own string table (<Name>.strings.json, merged
into the game's by mapgen/strings.py), so it shows in Nox's own dialogue window and journal.

    q = QuestBook("Thornwick")
    q.talker("Reeve", [
        q.say("The bandits are dead? Then the road is yours.", when=q.at("main", 2), do=[A.stage("main", 3), A.gold(200)]),
        q.say("Bring me word of Garrick.", when=q.at("main", 1)),
        q.say("You there! A word...", do=[A.stage("main", 1), q.journal("Find the Red Hand's camp.")]),
    ])
    q.on_death("Garrick", [A.stage("main", 2), A.drop("RubyKey")])
    spec.scripts.update(q.files()); q.write_strings(out_dir)

Lines are tried in order and the first whose `when` holds is spoken, so later stages go first. Text is plain: a
line break is "\\n". Keys are "<Map>:<Name><n>" (n counts within the map).

Every line said in a dialogue window is voiced (mapgen/voice.py, run by Spec.build): a talker's lines and what
q.tell has a giver say after the talk. write_strings records who says each (<Map>.speech.json) with their portraits,
any voice a design pins (q.talker(..., voice=), q.voice) and how a line is said where it matters (q.say(..., spoken=
"(sigh) ...", mood="...")). Text over a head (A.chat) and on screen (A.print) has no key and
stays silent, as Westwood's does.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
QUEST, COMPLETED, HINT, NOTE = 2, 4, 8, 1       # journal entry types (ns.EntryType: red quest, grey completed, ...)


def events_go(pkg):
    """kit/behaviours/events.go for a map's package: the creature events every script shares (OnObjEvent)."""
    return open(os.path.join(HERE, "behaviours", "events.go"), encoding="utf-8").read().replace("package PKG", f"package {pkg}", 1)


def _go(s):
    return json.dumps(s, ensure_ascii=False)


# script-name stems that read better as a role than split apart
_ROLE_TITLES = {"Watch": "Watchman", "Folk": "Townsfolk", "Guard": "Guard", "Keeper": "Keeper"}


def display_name(scr):
    """A title for a script name: "NorthGuard" -> "North Guard", "Watch2" -> "Watchman", "FatherOdo" -> "Father Odo"."""
    stem = re.sub(r"\d+$", "", scr)
    return _ROLE_TITLES.get(stem) or re.sub(r"(?<=[a-z])(?=[A-Z])", " ", stem)


class A:
    """Actions (kit/behaviours/quests.go run)."""
    @staticmethod
    def stage(quest, n): return ("stage", quest, "", n)
    @staticmethod
    def advance(quest, n=1):
        """The quest's stage moves on by n: a count of things done in any order (three vents opened)."""
        return ("advance", quest, "", n)
    @staticmethod
    def flag(name): return ("flag", name, "", 0)
    @staticmethod
    def unflag(name): return ("unflag", name, "", 0)
    @staticmethod
    def give(t, n=1): return ("give", t, "", n)
    @staticmethod
    def drop(t): return ("drop", t, "", 0)
    @staticmethod
    def take(t): return ("take", t, "", 0)
    @staticmethod
    def spawn(t, at_obj): return ("spawn", t, at_obj, 0)
    @staticmethod
    def turn(person, foe):
        """`person` (a cloned townsperson, who cannot be made hostile) steps aside and `foe`, a creature placed
        disabled at the same spot, turns on the player: a traitor unmasked (Greywatch)."""
        return ("turn", person, foe, 0)
    @staticmethod
    def gold(n): return ("gold", "", "", n)
    @staticmethod
    def print(text): return ("print", text, "", 0)
    @staticmethod
    def chat(obj, text): return ("chat", obj, text, 0)
    @staticmethod
    def unlock(obj): return ("unlock", obj, "", 0)
    @staticmethod
    def lock(obj): return ("lock", obj, "", 0)
    @staticmethod
    def enable(obj): return ("enable", obj, "", 0)
    @staticmethod
    def disable(obj): return ("disable", obj, "", 0)
    @staticmethod
    def hunt(obj): return ("hunt", obj, "", 0)
    @staticmethod
    def walk(obj, journey):
        """`obj` sets off on a long walk laid along the roads and paths (StoryMap.journey's key), leg by leg; never
        a single Move to a far waypoint, which the game walks straight at, into the trees (Greywatch's Wil)."""
        return ("walk", obj, journey, 0)


class QuestBook:
    def __init__(self, map_name):
        self.map = map_name
        self.strings = {}           # key -> text
        self.calls = []             # Go statements for the config's init
        self.names = set()          # creatures and objects the calls name (the self-check)
        self._n = {}
        self.quests = {}            # quest -> its title, for the report
        self.spoken = {}            # key -> who says it in a dialogue window (voiced by mapgen/voice.py)
        self.pics = {}              # talker -> portrait
        self.voices = {}            # talker -> the voice a design pins (mapgen/voice.py cast)
        self.delivery = {}          # key -> how it is said: {"spoken": its words with vocal events, "mood": direction}

    # ---- text --------------------------------------------------------------------------------------------------
    def text(self, text, stem="Line"):
        """A key in the map's string table for `text`."""
        stem = re.sub(r"[^A-Za-z0-9]", "", stem) or "Line"
        stem = stem[:max(1, 31 - len(self.map) - 4)]       # a long script name is cut to fit (room for n up to 999)
        self._n[stem] = self._n.get(stem, 0) + 1
        key = f"{self.map}:{stem}{self._n[stem]}"
        # the dialogue message carries the key in 32 bytes (opennox nox_xxx_startShopDialog_548DE0)
        assert len(key) <= 31, f"string key too long for the game's dialogue message: {key}"
        self.strings[key] = text
        return key

    def journal(self, text, typ=QUEST):
        """A journal entry. Westwood's are orders, 5-14 words, naming the goal and the place ("Retrieve Matilda's
        cloak from an Ogre near the docks of Brin."): never the first person (rules/DIALOGUE.md)."""
        return ("journal", self.text(text, "Journal"), "", typ)

    def done(self, objective):
        """The quest's entry done: Westwood greys the same entry (JournalEdit to COMPLETED), which OpenNox alpha13
        lacks, so this writes a COMPLETED entry in the objective's own words."""
        return self.journal(objective, COMPLETED)

    def note(self, text):
        """News the player overheard, as Westwood's "NOTE: According to a pair of bridge guards, ..."."""
        return self.journal(text if text.startswith("NOTE:") else "NOTE: " + text, NOTE)

    def errand(self, giver, quest, offer, reminder, thanks, after, objective, done, reward=(), refusal=None,
               again=None, on_take=(), take=True):
        """Westwood's side quest (rules/QUESTS.md, "five lines and a journal entry"): the giver's lines, later stages
        first, to put in q.talker(giver, ...) (with any other lines of the giver after them).

        offer      the trouble, where, the ask and the reward, ending in a yes/no question (it is asked: yes takes
                   the quest and writes `objective` in the journal; no runs `refusal`)
        refusal    the sulk on "no", in a window of its own as Westwood's (q.tell); the next talk asks `again`
                   (default: the offer)
        reminder   while the quest is open; thanks: when `done` holds (a condition: q.when(has="SilverSeal"),
                   q.when(flag=q.dead("Greyjaw")), q.at(quest, 2) set by an event), with `reward` (A.give, A.gold),
                   the item taken back (`take`, when `done` is carrying something) and the objective done
        after      afterwards ("Thanks again, brave Adventurer!")
        Stages: 0 not taken, 1 taken, 2 done (if an event sets it), 3 paid."""
        take_it = [A.take(done["Has"])] if take and done.get("Has") else []
        if not done.get("Quest"): done = dict(done, Quest=quest, Stage=1)
        refused = f"{quest}_refused"
        yes = [A.stage(quest, 1), A.unflag(refused), self.journal(objective)] + list(on_take)
        no = [A.flag(refused)] + ([self.tell(giver, refusal)] if refusal else [])
        lines = [
            self.say(after, when=self.at(quest, 3), who=giver),
            self.say(thanks, when=done, do=list(reward) + take_it + [A.stage(quest, 3), self.done(objective)], who=giver),
            self.say(reminder, when=self.at(quest, 1), who=giver),
        ]
        if again:       # with no `again` the offer is asked again as it was: one line, one key
            lines.append(self.say(again, when=self.at(quest, 0, flag=refused), ask=True, do=yes, else_=no, who=giver))
        return lines + [self.say(offer, when=self.at(quest, 0), ask=True, do=yes, else_=no, who=giver)]

    # ---- conditions --------------------------------------------------------------------------------------------
    def dead(self, *names):
        """A flag that holds when every named creature is dead (read from the world, so it survives a saved game)."""
        self.names |= set(names)
        return "dead:" + ",".join(names)

    @staticmethod
    def at(quest, stage, has="", flag="", not_="", gold=0):
        return dict(Quest=quest, Stage=stage, Has=has, Flag=flag, Not=not_, Gold=gold)

    @staticmethod
    def when(has="", flag="", not_="", gold=0):
        """A condition: carrying an item (`has`), a flag set or not, at least `gold` gold (a toll, a bribe)."""
        return dict(Quest="", Stage=-1, Has=has, Flag=flag, Not=not_, Gold=gold)

    # ---- declarations ------------------------------------------------------------------------------------------
    def say(self, text, when=None, do=(), ask=False, else_=(), who="Line", spoken=None, mood=None):
        """A talker's line. spoken, mood: how it is said (q.deliver)."""
        key = self.text(text, who)
        if spoken or mood: self.deliver(key, spoken, mood)
        return dict(When=when or self.when(), Text=key, Ask=ask, Do=list(do), Else=list(else_))

    def tell(self, giver, text, spoken=None, mood=None):
        """An action: when the talk ends, `giver` says `text` in a dialogue window of its own, voiced like its other
        lines (Westwood's refusal, War05A's "Fine then, don't return my magical staff!", is such a second TellStory).
        Only in a talker line's do= or else_= (it needs the talk's window); A.chat says a line over the head, silent."""
        key = self.text(text, giver)
        self.spoken[key] = giver
        if spoken or mood: self.deliver(key, spoken, mood)
        return ("tell", key, giver, 0)

    def deliver(self, key, spoken=None, mood=None):
        """How a spoken line is said (mapgen/voice.py, Breeze): `spoken` is its text with inline vocal events where the
        line warrants one ("(sigh) Gate's barred by order of the reeve." ; (laugh), (chuckle), (sigh), (scoff),
        (cough), (clears throat), (gasp), (sniff), (groan)), the words exactly the line's; `mood` a few words of
        direction for this line alone ("cold and bitter"). Use them where a line clearly calls for it, not on every
        line. Returns the key."""
        import sys
        if os.path.dirname(HERE) not in sys.path: sys.path.insert(0, os.path.dirname(HERE))
        import voice as _V
        if spoken:
            why = _V.delivery_problem(self.strings[key], spoken)
            if why: raise ValueError(f"{key}: the delivery {spoken!r}: {why}")
        d = self.delivery.setdefault(key, {})
        if spoken: d["spoken"] = spoken
        if mood: d["mood"] = mood
        return key

    def voice(self, who, voice):
        """Pins the voice of a speaker who is not a q.talker of this design, or by one of its lines' keys (a
        shopkeeper's greeting: q.voice(greet_key, {...})). The forms are q.talker's voice=."""
        self.voices[who] = voice

    def talker(self, name, lines, pic=None, title=None, voice=None):
        """An NPC who talks: the first of `lines` whose condition holds. pic: its portrait (Westwood's names). title:
        the name over its dialogue window (default: from the script name, "NorthGuard" -> "North Guard"). voice: pins
        its voice (mapgen/voice.py cast_breeze): a part such as "elder", a description ("An old blacksmith in his
        seventies. Deep, gravelly voice, a northern English accent. Slow and warm.") or {"desc": ..., "seed": n} for
        that very voice (and "ref_text"/"ref_desc" to reproduce an auditioned take); a Kokoro voice ("bm_george") or
        recipe ({"mix": ..., "speed": ...}) serves only the Kokoro engine; a dict may carry both. Pin a character who
        speaks on two maps; by default the voice is cast from its body, portrait and title."""
        self.names.add(name)
        self.title(name, title or display_name(name))
        for l in lines: self.spoken.setdefault(l["Text"], name)
        if voice: self.voices[name] = voice
        if pic:
            self.pics[name] = pic
            self.calls.append(f"Portrait({_go(name)}, {_go(pic)})")
        body = ",\n\t\t\t".join(self._line(l) for l in lines)
        self.calls.append(f"Talker({_go(name)}, []Line{{\n\t\t\t{body},\n\t\t}})")

    def title(self, name, text):
        """The name the dialogue window shows for creature `name`: the game reads the string "NPC:<script name>" (as
        Westwood's "NPC:Horst"), else it shows MISSING:NPC:<name>. The table is shared by every map, so a script name
        used in two maps must carry the same title (mapgen/strings.py refuses a clash)."""
        assert len(f"NPC:{name}") <= 31, f"script name too long for its dialogue title's string key: NPC:{name}"
        self.strings[f"NPC:{name}"] = text

    def portrait(self, name, pic):
        """The face in an NPC's dialogue window (Westwood's portraits: TheogrinPic, MaidenPic2, GalavaPriestPic...)."""
        self.names.add(name)
        self.pics[name] = pic
        self.calls.append(f"Portrait({_go(name)}, {_go(pic)})")

    def on_death(self, name, acts):
        self.names.add(name)
        self.calls.append(f"OnDeath({_go(name)}, {self._acts(acts)})")

    def on_all_dead(self, names, acts):
        self.names |= set(names)
        self.calls.append(f"OnAllDead([]string{{{', '.join(_go(n) for n in names)}}}, {self._acts(acts)})")

    def near(self, x, y, r, acts, when=None):
        self.calls.append(f"Near({x:.1f}, {y:.1f}, {r:.1f}, {self._cond(when or self.when())}, {self._acts(acts)})")

    def on_pickup(self, t, acts, when=None):
        self.calls.append(f"OnPickup({_go(t)}, {self._cond(when or self.when())}, {self._acts(acts)})")

    def when_true(self, when, acts):
        """Acts once, the first time `when` holds (all three vents open; every keeper dead), wherever the player is."""
        self.calls.append(f"WhenTrue({self._cond(when)}, {self._acts(acts)})")

    def start(self, acts):
        self.calls.append(f"Start({self._acts(acts)})")

    # ---- Go ----------------------------------------------------------------------------------------------------
    @staticmethod
    def _cond(c):
        return (f"Cond{{Quest: {_go(c['Quest'])}, Stage: {int(c['Stage'])}, Has: {_go(c['Has'])}, "
                f"Flag: {_go(c['Flag'])}, Not: {_go(c['Not'])}, Gold: {int(c.get('Gold', 0))}}}")

    def _acts(self, acts):
        out = []
        for k, a, b, n in acts:
            if k in ("unlock", "lock", "enable", "disable", "hunt", "walk", "chat", "turn"): self.names.add(a)
            if k == "turn": self.names.add(b)
            if k == "spawn": self.names.add(b)
            out.append(f"{{Kind: {_go(k)}, A: {_go(a)}, B: {_go(b)}, N: {int(n)}}}")
        return "[]Act{" + ", ".join(out) + "}"

    def _line(self, l):
        return (f"{{When: {self._cond(l['When'])}, Text: {_go(l['Text'])}, Ask: {'true' if l['Ask'] else 'false'}, "
                f"Do: {self._acts(l['Do'])}, Else: {self._acts(l['Else'])}}}")

    def files(self):
        """{filename: Go source} for the map's folder."""
        if not self.calls: return {}
        pkg = self.map.lower()
        lib = open(os.path.join(HERE, "behaviours", "quests.go"), encoding="utf-8").read().replace("package PKG", f"package {pkg}", 1)
        # the story is set up once, on MapInitialize or, if that never fires (the dedicated server with no player in
        # it does not fire it), after a second of frames: the quests never hang on one event alone
        cfg = (f"package {pkg}\n\n// The story of {self.map}: who says what, and what happens (written by dystopiannox "
               f"mapgen/kit/quests.py).\n\nimport \"github.com/noxworld-dev/noxscript/ns/v4\"\n\n"
               "var storySetUp bool\n\nfunc setUpStory() {\n\tif storySetUp {\n\t\treturn\n\t}\n\tstorySetUp = true\n" +
               "".join(f"\t{c}\n" for c in self.calls) + "\tQuests()\n}\n\nfunc init() {\n"
               "\tns.OnMapEvent(ns.MapInitialize, setUpStory)\n"
               "\tframes := 0\n\tns.OnEachFrame(1, func() {\n\t\tif frames++; frames == 30 {\n\t\t\tsetUpStory()\n\t\t}\n\t})\n"
               f"\tlineKeys = []string{{{', '.join(_go(k) for k in self.strings)}}}\n"
               f"\tQuestCheck([]string{{{', '.join(_go(n) for n in sorted(self.names))}}})\n}}\n")
        return {"quests.go": lib, "quests_config.go": cfg, "events.go": events_go(pkg)}

    def write_strings(self, out_dir):
        """<Map>.strings.json beside the map (install copies it into maps/<Map>/), and <Map>.speech.json: who says
        each line in a dialogue window, their portraits, pinned voices and deliveries (Spec.build's voice step reads it)."""
        p = os.path.join(out_dir, f"{self.map}.strings.json")
        with open(p, "w", encoding="utf-8") as f: json.dump(self.strings, f, ensure_ascii=False, indent=1)
        with open(os.path.join(out_dir, f"{self.map}.speech.json"), "w", encoding="utf-8") as f:
            json.dump(dict(lines=self.spoken, pics=self.pics, voices=self.voices, delivery=self.delivery), f,
                      ensure_ascii=False, indent=1)
        return p
