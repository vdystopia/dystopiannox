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
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
QUEST, COMPLETED, HINT, NOTE = 2, 4, 8, 1       # journal entry types (ns.EntryType: red quest, grey completed, ...)


def _go(s):
    return json.dumps(s, ensure_ascii=False)


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
    def walk(obj, waypoint): return ("walk", obj, waypoint, 0)


class QuestBook:
    def __init__(self, map_name):
        self.map = map_name
        self.strings = {}           # key -> text
        self.calls = []             # Go statements for the config's init
        self.names = set()          # creatures and objects the calls name (the self-check)
        self._n = {}
        self.quests = {}            # quest -> its title, for the report

    # ---- text --------------------------------------------------------------------------------------------------
    def text(self, text, stem="Line"):
        """A key in the map's string table for `text`."""
        stem = re.sub(r"[^A-Za-z0-9]", "", stem) or "Line"
        self._n[stem] = self._n.get(stem, 0) + 1
        key = f"{self.map}:{stem}{self._n[stem]}"
        # the dialogue message carries the key in 32 bytes (opennox nox_xxx_startShopDialog_548DE0)
        assert len(key) <= 31, f"string key too long for the game's dialogue message: {key}"
        self.strings[key] = text
        return key

    def journal(self, text, typ=QUEST):
        return ("journal", self.text(text, "Journal"), "", typ)

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
    def say(self, text, when=None, do=(), ask=False, else_=(), who="Line"):
        return dict(When=when or self.when(), Text=self.text(text, who), Ask=ask, Do=list(do), Else=list(else_))

    def talker(self, name, lines, pic=None):
        """An NPC who talks: the first of `lines` whose condition holds. pic: its portrait (Westwood's names)."""
        self.names.add(name)
        if pic: self.calls.append(f"Portrait({_go(name)}, {_go(pic)})")
        body = ",\n\t\t\t".join(self._line(l) for l in lines)
        self.calls.append(f"Talker({_go(name)}, []Line{{\n\t\t\t{body},\n\t\t}})")

    def portrait(self, name, pic):
        """The face in an NPC's dialogue window (Westwood's portraits: TheogrinPic, MaidenPic2, GalavaPriestPic...)."""
        self.names.add(name)
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
        return {"quests.go": lib, "quests_config.go": cfg}

    def write_strings(self, out_dir):
        """<Map>.strings.json beside the map (install copies it into maps/<Map>/)."""
        p = os.path.join(out_dir, f"{self.map}.strings.json")
        with open(p, "w", encoding="utf-8") as f: json.dump(self.strings, f, ensure_ascii=False, indent=1)
        return p
