"""A story card (v2: shapes without quoted instances; i5 writers copied the quotes into one template): a map's own draw of Westwood's shapes and model lines, so that maps written by agents with one brief do
not all come out of one template.

    py tests/storylab.py card <seed>      (the map's name is a good seed) prints the card

i4 showed it: ten writers given one brief and one set of exemplars converge on the same lines ("Dead? All of 'em? Ha!",
"Psst! ... Heh, heh, heh", "Did X send you?", three rescued boys named Wim). Westwood's quests are spread over many
shapes; a card draws each map's shapes from that spread (the lists below are Westwood's, from the campaign), and gives
every part two or three model lines of its own, drawn from review/storylab/exemplars.
"""
import collections, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# per scenario: {dimension: [Westwood's options, each with an instance]}
SHAPES = {
    "guard_bark": {
        "first": ["a welcome and a pointer",
                  "the rules of the place",
                  "a refusal by order, with the reason, and the person who can change it",
                  "pride in the place or its lord",
                  "a warning about the road",
                  "a jailer's or warden's threat",
                  "urgent news and where to go",
                  "a plain statement of whose house or post this is"],
        "again": ["one or two curt words", "an afterthought",
                  "idle talk", "the same point again, shorter",
                  "a remark about the player's looks or gear"],
        "later": ["one plain line of thanks, no news",
                  "a new warning about what lies ahead", "the way is open, and hurry",
                  "nothing to do with the quest at all", "praise in civic stock words"],
    },
    "quest": {
        "opener": ["the trouble shouted first", "a stock greeting",
                   "a victim's cry", "a stiff official",
                   "a grumble", "mid-thought, as if already talking",
                   "a fright, then relief", "an insult at the thieves"],
        "register": ["plain and loud", "loud and over-explained: a long run-on speech", "grand and stiff, a little melodramatic",
                     "odd or fussy (a hermit, a con man, a nervous scholar)", "gruff and short"],
        "ask": ["a yes/no question at the end", "an order with no question at all",
                "a conditional", "a bargain"],
        "length": ["one page", "two pages", "three pages", "one page"],
        "reward": ["a named sum of gold at the handover", "\"a token of my appreciation\" with no sum named",
                   "a spell or a scroll", "a key, a pass or the way on",
                   "an item that is useful (a shield, boots, potions)", "a thing with an odd story (a scroll on bats, a used bow)"],
        "mechanics": ["hands over a key or an item at once",
                      "sends the player on to someone else after",
                      "says where with one bearing and nothing more (east of here, in the cemetery), once", "says nothing about where; the reminder gives the hint"],
    },
    "rumour": ["a brush-off", "a worry about the times",
               "gossip about a great person, with an opinion", "a tip about the game",
               "a pointer to a place", "a flirt or a tease",
               "a complaint about the town's own folly",
               "a plain statement of the map's trouble, with no joke", "the same news another townsperson gives, said again",
               "something odd and unexplained", "a warning"],
    "shop": ["a flat slogan", "a wink at the price",
             "a grumble or a rude keeper", "the keeper reacts to the player",
             "the times are bad for business", "an odd sideline (an undertaker's coffins)",
             "a boast taken back", "a stiff trade name"],
    "deal": ["a used thing sold cheap by a con man", "a bounty, dead or alive, from a warden", "a jailbreak for a smuggler's friend",
             "a house or inn for sale at an absurd price", "a lesson or a contest for a fee", "a charmed beast for sale",
             "a favour for a signature or a good word", "a bet"],
    "captive": ["a pet (Westwood: a frog)", "a group of workers", "a sister, wife or daughter", "an apprentice or a novice",
                "a master or a mentor", "a soldier or a scout", "an engineer or a craftsman", "a merchant"],
    "rescue_mech": ["the captive gives a key for the next captive", "the captive is behind a locked door and the giver gave the key",
                    "the captive follows the player and gives a hint on the way", "the captive must be led to a lift or a gate",
                    "the captive is found dying or already lost (Westwood's apprentice)"],
    "opening": ["arrival and orders", "grave news, then orders", "orders only, curt",
                "a long briefing from a great one (a warlord, an arch-wizard)"],
    "opening_gives": ["a weapon or a staff", "spells", "supplies and gold", "a key", "nothing"],
}

# a part (or its situation) -> (exemplar file, a word of the group heading to draw from, or "")
SITUATION_FILE = {"offer": ("offer", ""), "plea": ("offer", ""), "opening": ("opening", ""), "reminder": ("reminder", ""),
                  "completion": ("completion", ""), "after": ("after", "Afterwards"), "refusal": ("after", "Refusals"),
                  "townsfolk": ("townsfolk", ""), "rumour": ("townsfolk", ""), "guard": ("guard", ""), "shop": ("shop", ""),
                  "journal": ("journal", ""), "journal_done": ("journal", ""), "found": ("captive", "Found"),
                  "following": ("captive", "Following"), "herald": ("townsfolk", "trouble")}


def _exemplar_lines():
    """{situation file: [(group heading, line text)]} from review/storylab/exemplars/*.md."""
    out = {}
    d = os.path.join(HERE, "exemplars")
    for f in os.listdir(d):
        if not f.endswith(".md"): continue
        lines, head = [], ""
        for l in open(os.path.join(d, f), encoding="utf-8"):
            if l.startswith("## "): head = l[3:].strip()
            m = re.match(r"- (.*?)\s+`[^`]+`\s*$", l)
            if m: lines.append((head, m.group(1)))
        out[f[:-3]] = lines
    return out


def card(seed, scenarios=None):
    """The card for one map (markdown). `scenarios`: [(scenario id, [(part, situation)])] to give model lines for."""
    rng = random.Random(str(seed))
    ex = _exemplar_lines()
    pick = lambda xs, k=1: rng.sample(xs, k) if k > 1 else rng.choice(xs)
    L = [f"## Your card (seed {seed!r})", "",
         "Nine other writers get the same brief; whatever comes to you first comes to them too. This card is your map's "
         "own draw from Westwood's spread of shapes: follow it, and take the models below as the lines to imitate for "
         "each part (two or three each, drawn for you from the exemplars).", ""]
    g = SHAPES["guard_bark"]
    L += [f"- **Guard:** first words: {pick(g['first'])}; again: {pick(g['again'])}; later: {pick(g['later'])}."]
    q = SHAPES["quest"]
    for name in ("bounty_offer", "heirloom_fetch", "rescue", "two_givers (the respectable ask)"):
        L.append(f"- **{name}:** opens with {pick(q['opener'])}; {pick(q['register'])}; {pick(q['ask'])}; {pick(q['length'])}; "
                 f"reward: {pick(q['reward'])}; {pick(q['mechanics'])}.")
    L.append(f"- **two_givers (the odd one):** {pick(SHAPES['deal'])}.")
    L.append(f"- **rescue (the captive):** the captive is {pick(SHAPES['captive'])}; {pick(SHAPES['rescue_mech'])}.")
    L.append(f"- **Rumours:** {'; '.join(pick(SHAPES['rumour'], 3))}.")
    L.append(f"- **Shops:** {'; '.join(pick(SHAPES['shop'], 3))} (inn, arms, magic in that order).")
    L.append(f"- **Main opening:** {pick(SHAPES['opening'])}; the opener gives {pick(SHAPES['opening_gives'])}.")
    L.append(f"- **The town's one comic person** is the {pick(['innkeeper', 'arms dealer', 'magic seller', 'odd giver of the deal', 'third townsperson', 'guard', 'captive'])}; "
             "everyone else plays it straight.")
    L.append(f"- **One rough patch:** {pick(['a run-on sentence in the longest speech', 'a ?! in a reminder', 'a trailing Oh.... in a reminder', 'a stiff, slightly wrong formal word in an official line', 'a missing full stop at the end of one townsperson line', 'a sentence fragment as a whole line'])}.")
    L.append("")
    if scenarios:
        L += ["### Your model lines (imitate the manner, never the words)", ""]
        for sid, parts in scenarios:
            for part, sit in parts:
                f, grp = SITUATION_FILE.get(part) or SITUATION_FILE.get(sit) or ("", "")
                pool = [t for h, t in ex.get(f, []) if grp in h] or [t for _, t in ex.get(f, [])]
                if not pool: continue
                L.append(f"- `{sid}.{part}`: " + " | ".join(f'"{x}"' for x in rng.sample(pool, min(3, len(pool)))))
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    print(card(sys.argv[1] if len(sys.argv) > 1 else "1"))


# ---- frames (v3): one Westwood line a part, to be rewritten line for line ---------------------------------------------
# i6 showed that every instruction a brief gives ("one run-on speech", "an afterthought", "?!") is followed by all ten
# writers and becomes the template. A frame is one of Westwood's own lines given to one part of one map: its quirks
# (a slip, a stiff word, a run-on, an afterthought) come with it, spread over a map as unevenly as Westwood spread them.

FRAME_OF_PART = {"offer": "offer", "plea": "offer", "offer_a": "offer", "offer_b": "offer", "opening": "opening",
                 "reminder": "reminder", "completion": "completion", "outcome_a": "completion", "outcome_b": "completion",
                 "after": "after", "refusal": "refusal", "rumour1": "townsfolk", "rumour2": "townsfolk",
                 "rumour3": "townsfolk", "herald": "townsfolk", "first": "guard", "again": "guard", "later": "guard",
                 "inn": "shop", "arms": "shop", "magic": "shop", "journal": "journal", "journal_a": "journal",
                 "journal_b": "journal", "found": "captive", "following": "captive"}
FRAME_SOURCES = {"offer": ["offer", "talk"], "opening": ["offer", "talk"], "reminder": ["reminder", "talk", "after"],
                 "completion": ["completion", "talk"], "after": ["after", "bump", "completion"], "refusal": ["refusal", "after"],
                 "townsfolk": ["townsfolk"], "guard": ["guard", "townsfolk", "talk"], "shop": ["shop"],
                 "journal": ["journal"], "captive": ["talk", "reminder"]}
FRAME_WORDS = {"offer": (25, 140), "opening": (25, 160), "reminder": (2, 30), "completion": (5, 90), "after": (2, 30),
               "refusal": (3, 40), "townsfolk": (2, 35), "guard": (2, 45), "shop": (3, 45), "journal": (3, 25),
               "captive": (2, 30)}


def _frame_pools():
    import difflib, json
    import westwood
    d = json.load(open(os.path.join(HERE, "scenarios.json"), encoding="utf-8"))
    keys = set()
    for s in d["scenarios"]:
        for u in s["westwood"] + s.get("control_extra", []):
            for _, k in u: keys.update(k if isinstance(k, list) else [k])
    S = westwood.strings()
    pooltexts = [S[k] for k in keys if k in S]
    rows = [r for r in westwood.campaign() if not r["dup"] and r["key"] not in keys]
    out = {}
    for fs, srcs in FRAME_SOURCES.items():
        lo, hi = FRAME_WORDS[fs]
        tiers = []
        for src in srcs:                                # the situation's own lines first, then the fallbacks
            xs = []
            for r in rows:
                if r["situation"] != src: continue
                n = len(r["text"].split())
                if not lo <= n <= hi: continue
                if any(difflib.SequenceMatcher(None, r["text"], t).ratio() > 0.6 for t in pooltexts): continue
                xs.append((r["key"], re.sub(r"\s*\n\s*\n\s*", " / ", r["text"].strip()).replace(chr(10), " / ")))
            tiers.append(xs)
        out[fs] = tiers
    return out


class FrameDealer:
    """Deals frames for a round: no two maps of a round share a frame while the pool lasts."""
    def __init__(self, seed):
        self.rng = random.Random(f"frames|{seed}")
        self.pools = _frame_pools()
        self.decks = {}

    def deal(self, fs):
        deck = self.decks.get(fs)
        if not deck:
            deck = []
            for tier in self.pools.get(fs, []):
                t = list(tier); self.rng.shuffle(t); deck += t
            self.decks[fs] = deck
        return deck.pop(0) if deck else None


LONG = ("offer", "opening", "completion")


def frames_card(dealer, scenarios, long=True):
    """The frames of one map: {scenario: {part: (key, text)}} and its markdown."""
    L = ["### Your frames: one Westwood line a part, to rewrite line for line", "",
         ("Each part listed below is a rewrite of its frame (the quests are rewritten from their quest frames above)."
          if not long else "Each part of your town is a rewrite of its frame.") + " Keep the frame's shape: about as many sentences, its "
         "punctuation where it falls (! ? ... -- / page breaks), how it opens and how it ends, its stock words, its "
         "quirks (a slip, a stiff word, a run-on, an afterthought, a flat statement). Change its matter to your town's: "
         "who, what, where, the beast, the thing, the reward. Never keep five words of a frame in a row (a stock phrase "
         "like \"a token of my appreciation\" excepted) and never a Westwood name. Where the scenario needs a thing the "
         "frame lacks (a yes/no question, a reward, a place), add it in the frame's manner. A frame from another "
         "situation is a model of rhythm and register, not of content.", ""]
    got = {}
    for sid, parts in scenarios:
        for part, _ in parts:
            fs = FRAME_OF_PART.get(part)
            if not fs or (not long and fs in LONG): continue
            fr = dealer.deal(fs)
            if not fr: continue
            got.setdefault(sid, {})[part] = fr
            L.append(f"- `{sid}.{part}`: \"{fr[1]}\"  ({fr[0]})")
    L.append("")
    return got, "\n".join(L)


# ---- premises (v8): the quests' premises dealt from Westwood's kinds ---------------------------------------------------
# i7 showed that the line can be Westwood's while the quest is not: our premises were mundane (wolves eat the sheep,
# Imps raid the stores, a bounty on bears), Westwood's are personal, concrete and a little absurd.
PREMISES = ["a fear or phobia of the giver's that the trouble feeds (Westwood: a mayor hiding from spiders)",
            "an embarrassing loss (Westwood: boots stolen while their owner was bathing)",
            "a curse or a transformation of someone dear (Westwood: a wife turned into a wolf)",
            "a pet in danger (Westwood: a frog in a burning house)",
            "a thing the giver cannot do without (Westwood: a hermit's spectacles)",
            "someone who went first and did not come back (Westwood: a Warrior chased the urchins and hasn't returned)",
            "a business ruined by thieves (Westwood: an inn robbed by rogues)",
            "a friend or partner in jail again (Westwood: a smuggler who gets arrested to dodge work)",
            "a family member's precious thing that must be back before they come home (Westwood: a father's cloak)",
            "the giver's own blunder (Westwood: an apprentice who swapped bodies with a frog)",
            "a contest, a fee or a sale with a catch (Westwood: a used bow for the archery contest)",
            "an official duty the giver would rather not do himself (Westwood: a warden's bounty, dead or alive)"]


def premise_card(dealer):
    rng = dealer.rng
    deck = dealer.decks.setdefault("_premise", [])
    out = []
    for q in ("bounty_offer", "heirloom_fetch", "two_givers (the odd ask)", "rescue"):
        if not deck:
            deck += PREMISES; rng.shuffle(deck)
        ok = [p for p in deck if q != "rescue" or re.match(r"a pet|someone who went|a friend|a curse|the giver's own", p)]
        p = ok[0] if ok else rng.choice([x for x in PREMISES if re.match(r"a pet|someone who went|a friend|a curse", x)])
        if p in deck: deck.remove(p)
        out.append(f"- **{q}:** {p}.")
    return "\n".join(["### Your premises", "",
                      "The kind of trouble behind each quest, dealt to you: invent your own premise of that kind (never "
                      "Westwood's example), personal, concrete and a little absurd, said with an overstatement (\"These "
                      "cursed arachnids are worse than the pox!\"). The scenario's beast, thing or captive may change to "
                      "fit.", ""] + out + [""])


# ---- sentence frames (v9): the long lines built sentence by sentence ----------------------------------------------------
# i8: the short lines written from frames passed (townsfolk: 0 of 5 caught alone; guards and shops 80% side by side),
# the long ones written from exemplars and a dealt premise did not (the premise became the template). A long part gets
# the page-and-sentence plan of one of Westwood's own lines of its situation, each sentence with its own frame drawn
# from the sentences Westwood puts in that position (first, middle, last).

LONG_SOURCES = {"offer": ["offer"], "opening": ["offer"], "completion": ["completion"]}


def _sentence_pools():
    import json
    import westwood, metrics
    d = json.load(open(os.path.join(HERE, "scenarios.json"), encoding="utf-8"))
    keys = set()
    for s in d["scenarios"]:
        for u in s["westwood"] + s.get("control_extra", []):
            for _, k in u: keys.update(k if isinstance(k, list) else [k])
    rows = [r for r in westwood.campaign() if not r["dup"] and r["key"] not in keys]
    out = {}
    for fs, srcs in LONG_SOURCES.items():
        plans, pos = [], {"first": [], "middle": [], "last": []}
        for r in rows:
            if r["situation"] not in srcs: continue
            pages = [p for p in re.split(r"\s*\n\s*\n\s*", r["text"].strip()) if p.strip()]
            sents = [metrics.sentences(p) for p in pages]
            n = sum(len(s) for s in sents)
            if n < 2: continue
            plans.append((r["key"], [len(s) for s in sents]))
            flat = [x for s in sents for x in s]
            pos["first"].append((r["key"], flat[0])); pos["last"].append((r["key"], flat[-1]))
            pos["middle"] += [(r["key"], x) for x in flat[1:-1]]
        out[fs] = (plans, pos)
    return out


def sentence_frames_card(dealer, scenarios):
    """The long parts of one map, each a plan of pages and sentences with a frame for every sentence."""
    if not hasattr(dealer, "spools"): dealer.spools = _sentence_pools()
    rng = dealer.rng
    L = ["### Your sentence frames: the offers, thanks and openings, sentence by sentence", "",
         "Each long part below has a plan taken from one of Westwood's own lines of its kind: its pages (`/`) and, for "
         "every sentence, a frame (a Westwood sentence from the same place in such a speech). Write the part one "
         "sentence per frame, in the frame's manner (its length, punctuation, opening words, register, its quirk), "
         "about your town's matter. You may merge two sentences or drop one; keep the pages. The premise of the quest "
         "is yours: what the giver lost or fears, plainly; Westwood's errands are mostly plain, its humour incidental. "
         "Never five words of a frame in a row (stock phrases excepted), never a Westwood name.", ""]
    for sid, parts in scenarios:
        for part, _ in parts:
            fs = FRAME_OF_PART.get(part)
            if fs not in LONG_SOURCES: continue
            plans, pos = dealer.spools[fs]
            plan_key, pages = rng.choice(plans)
            n = sum(pages); i = 0; out = []
            for pg in pages:
                ss = []
                for _ in range(pg):
                    where = "first" if i == 0 else ("last" if i == n - 1 else "middle")
                    deck = dealer.decks.setdefault(f"_s_{fs}_{where}", [])
                    if not deck:
                        deck += pos[where] or pos["middle"]; rng.shuffle(deck)
                    ss.append(f"\"{deck.pop()[1]}\"")
                    i += 1
                out.append(" ".join(ss))
            L.append(f"- `{sid}.{part}` ({len(pages)} page{'s' if len(pages) > 1 else ''}, {n} sentences): " + " / ".join(out))
    L.append("")
    return "\n".join(L)


# ---- a map's own frames (for map agents) --------------------------------------------------------------------------------
DEFAULT_MAP_PARTS = ("main:opening,reminder,journal; "
                     "quest1:offer,refusal,reminder,completion,after,journal; quest2:offer,reminder,completion,journal; "
                     "quest3:offer,reminder,completion,journal; rescue:offer,reminder,found,following,completion,journal; "
                     "guard1:first,again,later; guard2:first,later; shops:inn,arms,magic; "
                     "townsfolk:rumour1,rumour2,rumour3,rumour1,rumour2,rumour3,rumour1,rumour2")


def map_frames(seed, spec=DEFAULT_MAP_PARTS, blend=True):
    """The frames card of one map: `spec` is "who:part,part; who:part" (parts as in FRAME_OF_PART: offer, opening,
    reminder, completion, after, refusal, rumour1, first/again/later, inn/arms/magic, journal, found, following)."""
    dealer = FrameDealer(f"map|{seed}")
    groups = []
    for chunk in spec.split(";"):
        if ":" not in chunk: continue
        who, parts = chunk.split(":", 1)
        groups.append((who.strip(), [(p.strip(), "") for p in parts.split(",") if p.strip()]))
    # each quest of the map gets a whole Westwood quest (v10, the lab's best round); the rest gets line frames
    qmap = {}
    for who, parts in groups:
        ps = {p for p, _ in parts}
        if "opening" in ps: qmap[who] = "main_opening"
        elif "found" in ps or "plea" in ps: qmap[who] = "rescue"
        elif "offer" in ps or "offer_a" in ps: qmap[who] = "heirloom_fetch" if "refusal" in ps else "bounty_offer"
    if not blend:
        qmd = quest_frames_card(dealer, [(qmap[w], ps) for w, ps in groups if w in qmap])[0]
        for w, sid in qmap.items(): qmd = qmd.replace(f"**{sid}**", f"**{w}**", 1)
        short = frames_card(dealer, [(w, ps) for w, ps in groups if w not in qmap], long=False)[1]
    else:                                   # (v13) each quest blended from two or three Westwood quests of other kinds
        qmd, need = [], []
        for i, (w, ps) in enumerate([(w, ps) for w, ps in groups if w in qmap]):
            md, _, _, nd = blend_card(dealer, [(qmap[w], ps)], intro=(i == 0))
            qmd.append(md.replace(f"#### {qmap[w]}\n", f"#### {w} ({qmap[w].replace('_', ' ')})\n", 1))
            need += [(w, p) for _, p in nd]
        qmd = "\n".join(qmd)
        short = frames_card(dealer, need + [(w, ps) for w, ps in groups if w not in qmap])[1]
    return "\n".join([f"# Story frames for {seed}", "",
                      "Write every line of the map from its frames (review/storylab/WRITER.md, rules/DIALOGUE.md). The "
                      "frames are Westwood's own lines, dealt to this map: take their shape and rhythm, never their "
                      "words (no five in a row) or names; then `py tests/storylab.py --check` the design (originality).",
                      "", qmd, short])


# ---- quest frames (v10): a whole Westwood quest a quest ---------------------------------------------------------------
# i7 (a line frame a part, from any situation) and i9 (a sentence frame a sentence) gave long lines that read as
# assembled: objects never introduced, a tag in the wrong slot, a speaker who changes mid-speech. A quest frame is one
# Westwood quest, all its parts by one speaker in one situation, rewritten part for part: the coherence comes with it.
# Its units are those of the scenario pools (the round's packets leave out any Westwood unit a writer was dealt).

QUEST_SCENARIOS = {"bounty_offer": ["bounty_offer", "heirloom_fetch"], "heirloom_fetch": ["heirloom_fetch", "bounty_offer"],
                   "rescue": ["rescue", "bounty_offer"], "two_givers": ["two_givers"], "main_opening": ["main_opening"]}


def _quest_units():
    import json
    import westwood
    S = westwood.strings()
    d = json.load(open(os.path.join(HERE, "scenarios.json"), encoding="utf-8"))
    out = {}
    for s in d["scenarios"]:
        units = []
        for u in s["westwood"] + s.get("control_extra", []):
            parts = {}
            for p, k in u:
                ks = k if isinstance(k, list) else [k]
                parts[p] = (ks, " / ".join(re.sub(r"\s*\n\s*\n\s*", " / ", S[x].strip()) for x in ks if x in S))
            units.append(parts)
        out[s["id"]] = units
    return out


def quest_frames_card(dealer, scenarios):
    """One Westwood quest for each quest scenario of one map; returns (markdown, {scenario: [keys used]})."""
    if not hasattr(dealer, "qunits"): dealer.qunits = _quest_units()
    rng = dealer.rng
    L = ["### Your quest frames: one Westwood quest a quest, rewritten part for part", "",
         "Each quest below is dealt one of Westwood's own quests. Rewrite it part for part: the same shape (how many "
         "pages and sentences, where the ! and ? fall), the same register and quirks, the same kind of trouble and of "
         "reward, transposed to your town (spiders in the mayor's study -> another pest in another important person's "
         "room; boots stolen while bathing -> another thing lost in another embarrassing way). Keep its coherence: one "
         "speaker, one situation. Change every name and the matter; never five words of it in a row (stock phrases "
         "excepted). Where your scenario has a part the frame lacks, write it in the manner of the frame's other "
         "parts; where the frame has a part your scenario lacks, leave it out.", ""]
    used = {}
    for sid, parts in scenarios:
        if sid not in QUEST_SCENARIOS: continue
        deck = dealer.decks.setdefault(f"_q_{sid}", [])
        if not deck:
            for src in QUEST_SCENARIOS[sid]:
                t = list(dealer.qunits.get(src, [])); rng.shuffle(t); deck += t
        unit = deck.pop(0)
        used[sid] = [k for ks, _ in unit.values() for k in ks]
        L.append(f"- **{sid}**: " + " | ".join(f"*{p}*: \"{txt}\"" for p, (ks, txt) in unit.items()))
    L.append("")
    return "\n".join(L), used


# ---- blended quests (v13): beats dealt from two or three Westwood quests of other chapters and kinds -------------------
# i10-i12 rewrote one Westwood quest per quest. The judges recognised the skeleton under new nouns, and the originality
# check (originality.py) put those quests at 0.6-0.8 to the quest they were dealt where Westwood's own quests sit at
# 0.36 (p95 0.43) to their nearest neighbour. A blended quest takes the shape of its lines from a Westwood quest of
# *another kind* (A), the kind of trouble and its turn from a second (B), and, for some quests, the payoff or a
# complication from a third (C), all of other chapters; so no single Westwood quest maps onto it, while every line
# still has a Westwood line for its rhythm. The units come from every pool except the scenario's own, so a round's
# packets need leave nothing out.

FAMILY = {
    "Con02a:MayorGreeting": "pest", "Wiz01A.scr:HorvathTalk01": "rescue", "Wiz02:OldArchivistTalk01": "chase",
    "Wiz02A.scr:WardenTalk01": "bounty", "Wiz02A.scr:MaxTalk02": "bounty", "War01A.scr:GearhartTalk02": "pest",
    "Con03C.scr:ForemanA": "pest", "Con02a:BridgeGuardGuarding": "fetch", "Wiz05A.scr:CaptainGreeting": "briefing",
    "War05A.scr:SadVillagerGreeting": "rescue", "War05A.scr:IngridGreeting": "rescue",
    "War05A.scr:FarmerGreeting": "fetch", "War05A.scr:MaidenGreeting": "fetch", "Con05A.scr:HorvathGreeting": "fetch",
    "Con03A.scr:HermitMeet01": "fetch", "Wiz03a:HorvathIntro": "fetch", "War03b:MayorIntro": "fetch",
    "Wiz02B.scr:HorvathTalk04": "fetch", "War07A.scr:MorganTalk04": "deal", "Con02a:ConManSalesPitch3": "deal",
    "War01A.scr:QuaterMasterTalk01": "deal", "War05C.scr:SisterGreeting": "captive", "War07A.scr:MaxOffer01": "deal",
    "Con02a:ContestGuard": "deal", "Con02a:AldwinGreeting": "deal", "Wiz02B.scr:InversionBoyTalk01": "deal",
    "War02a:QuarterMasterTalk04": "rescue", "War05A.scr:CaptainGreeting": "rescue", "Con01a:CaptainGreet": "briefing",
    "War01A.scr:CaptainTalkStart": "briefing", "Con04a:CaptainGreet": "briefing", "Wiz06a:Captain1": "briefing",
    "Wiz02B.scr:HorvathTalk01": "briefing", "War02B.scr:HorrendousTalk1Start": "briefing",
    "Con05A.scr:CaptainGreeting": "briefing", "War09a:CaptainGreet": "briefing", "War08a:AldwynGreet": "briefing",
    # speakers outside the pools (originality.ww_quests ids)
    "War07a:MorganFriend": "deal", "War09a:Aidan": "captive", "War09c:Cain": "captive", "Wiz05c:Horvath": "captive",
    "War03b:Aldwyn": "gift", "War02a:Gearhart": "captive",
}
QUEST_PART_OF = {"offer": "offer", "plea": "offer", "opening": "offer", "offer_a": "offer", "offer_b": "offer",
                 "reminder": "reminder", "completion": "completion", "outcome_a": "completion",
                 "outcome_b": "completion", "after": "after", "refusal": "refusal"}
SCEN_FAMILY = {"bounty_offer": {"pest", "bounty", "chase"}, "heirloom_fetch": {"fetch", "chase"},
               "rescue": {"rescue", "captive"}, "two_givers": {"deal"}, "main_opening": {"briefing"}}

# Westwood's own loose spots: a stake half said, an aside, a non sequitur, a slip, a speech that runs on or stops
# short. A quest may be dealt one (about half are), each a different one, so no rule reaches every writer.
UNTIDY = [
    ("War05A.scr:MaidenGreeting", "If I don't get it back, he'll be destroyed. He's supposed to arrive soon!", "the stake half said: why it matters is left to the player"),
    ("War05A.scr:MaidenGreeting", "Could you... would you get it back for us?", "the ask stumbles and starts again"),
    ("Con04a:CaptainGreet", "See if Hecubah's been here. You'll know. And careful.", "a hint that explains nothing; a fragment"),
    ("Con02a:ConManSalesPitch3", "This bow is a beauty. The previous owner only used it on weekends.", "an aside that does nothing for the quest"),
    ("War07A.scr:MorganFriendTalk01", "Sometimes I think he does this just to get away from his responsibilities. It's not easy running a smuggling ring, you know.", "a grumble about someone, off the point"),
    ("Con02a:MayorsGuardIdle", "Beautiful weather today, don't you think?", "small talk with nothing to do with anything"),
    ("War02a:GearhartTalk06", "It worked! It worked! Um... You go first.", "a speaker who loses his nerve mid-line"),
    ("War03b:AldwynIntro", "Well, I don't really care for Theogrin and his petty conundrums, but allow me to assist you.", "an opinion about another townsman, unasked"),
    ("Con01a:CaptainGreet", "I'll bring you no further, lad. Too many prying eyes the closer we get by air to the Village of Ix.", "a reason half given, in a clumsy order"),
    ("Wiz02B.scr:HorvathTalk01", "Wildlife incursions in the settled areas is on a steady rise.", "a stiff word and a grammar slip"),
    ("War03b:AldwynPre", "Good luck with those urchins. They can be sneaky and ruthless bunch.", "a dropped word"),
    ("War07A.scr:MorganTalk06", "Accept this gold as token of my gratitude. Ah, yes! And here's a key", "a stock phrase a word short, then an afterthought"),
    ("Con03A.scr:HermitMeet02", "Have you recovered my spectacles?! Oh.... Well, the rogues who took them have a hideout in the woods nearby.", "the speaker trails off, then gives the hint late"),
    ("Wiz05C.scr:Horvath1", "Who is that? Can anybody hear me?", "the speech ends on a question to nobody"),
    ("Con05A.scr:HorvathReturned", "Here, these bottles of Mana and the Infravision spell will come in handy... sooner than you think.", "a hint of trouble ahead, not explained"),
    ("War03b:MayorPre", "Those nettlesome urchins are causing too much trouble these days.", "a reminder that reminds of nothing"),
    ("War07A.scr:MaxOffer01", "Actually, business has fallen off quite a bit, with Hecubah running loose. I'm moving out of here to set up shop further south.", "an offer that never quite asks"),
    ("War05A.scr:IngridReturned", "Thank you so much, kind Adventurer! Take these as tokens of my appreciation!", "a thanks far shorter than the ask"),
    ("Wiz05A.scr:CaptainGreeting", "The Ogres overran the Village of Brin and we'd have lost it to them if Horvath's powerful wizardry were not thrown into the fray at the last moment!", "one sentence that runs on past its point"),
    ("Wiz01A.scr:HorvathTalk04", "Perhaps you might make a good apprentice. Hmmm... Yes.", "the speaker thinking aloud"),
    ("Wiz02A.scr:WardenTalk02", "Ho, there! The priest told me of strange sounds coming from here, so I came to investigate.", "the speaker explains why he turned up, which nobody asked"),
    ("Con03C.scr:ForemanA", "What took you so long to get here!? We have a horrible problem!", "a gripe before the greeting"),
    ("War09a:AidanGreet1", "My companion died two days ago and the stench of his rotting corpse is a constant and nauseating reminder of my certain fate.", "one grim detail too many, stiffly said"),
    ("War05C.scr:SisterFollowing1C", "By the way, the Ogres mentioned something about a secret passage...", "something already said, said again as news"),
    ("War03b:T4Post", "Hmmm. I thought I locked the door.", "a line to himself"),
    ("War07A.scr:TurnMaxDown", "Ah, that's alright, lad. I'm sure I'll be able to sell my two buildings to someone else.", "a shrug where a giver would plead"),
    ("Wiz02B.scr:LewisTalk08", "Hmmm... don't tell Horvath about this. I'll try to sort it out on my own.", "a secret blurted out"),
    ("Wiz02A.scr:WardenTalk04", "You eliminated Morgan, eh? Well, I had hoped to bring him in alive, but I'll lose no sleep fretting about his soul!", "the giver's second thoughts about the job, after it is done"),
]

_POOLKEYS = None


def _pools_of_key(k):
    """The scenarios whose packet pool holds the string key k."""
    global _POOLKEYS
    if _POOLKEYS is None:
        import json
        d = json.load(open(os.path.join(HERE, "scenarios.json"), encoding="utf-8"))
        _POOLKEYS = collections.defaultdict(set)
        for s in d["scenarios"]:
            for u in s["westwood"] + s.get("control_extra", []):
                for _, kk in u:
                    for x in (kk if isinstance(kk, list) else [kk]): _POOLKEYS[x].add(s["id"])
    return _POOLKEYS.get(k, set())


def _blend_units():
    """{id: {"family", "chapter", "keys", "parts": {part: text}, "pools": {scenario}}}: every Westwood quest a blend
    may draw from (originality.ww_quests, one per first key, labelled by FAMILY)."""
    import originality as O
    out = {}
    for q in O.ww_quests():
        head, _, rest = q["id"].partition(":")
        first = rest if head in ("bounty_offer", "heirloom_fetch", "two_givers", "rescue", "main_opening") else q["id"]
        if first not in FAMILY or first in out: continue
        m = re.match(r"^(Con|War|Wiz)(\d+)", first, re.I)
        out[first] = dict(id=first, family=FAMILY[first], chapter=(m.group(1).capitalize() + m.group(2)) if m else first,
                          keys=set(q["keys"]), pools=set().union(*(_pools_of_key(k) for k in q["keys"])),
                          parts={p: re.sub(r"\s*\n\s*\n\s*", " / ", t.strip()).replace("\n", " ") for p, t in q["parts"].items()})
    return out


def _near_pool(unit, sid, S, d):
    import difflib
    texts = []
    for s in d["scenarios"]:
        if s["id"] != sid: continue
        for u in s["westwood"]:
            for _, k in u:
                texts += [S[x] for x in (k if isinstance(k, list) else [k]) if x in S]
    return any(difflib.SequenceMatcher(None, t, x).ratio() > 0.6 for t in unit["parts"].values() for x in texts)


BLEND_INTRO = [
    "### Your quests: each built from two or three Westwood quests", "",
    "Each quest below is dealt Westwood quests of other kinds and chapters. Build one new quest from them:", "",
    "- **Shape (A)**, a Westwood quest of another kind: each of your parts takes its size and rhythm from A's part of "
    "the same name (as many pages and sentences, where the ! and ? fall, how it opens and how it ends, its register "
    "and its quirks), not A's matter or the order of A's errand.",
    "- **Trouble (B):** the kind of trouble behind your quest and its turn (who is to blame, what went wrong first, "
    "what is odd about it), transposed to your scenario and town.",
    "- **Payoff or complication (C)**, where dealt: what the reward is (an item, a spell, a key, a pass, the way on, "
    "gold), or the snag in the job (a condition, a second person to see, a thing to do first).",
    "- **A loose spot**, where dealt: one Westwood line that is loose in one way, and what is loose about it. Your "
    "quest may be loose that way, once, where it falls naturally. Not its words.", "",
    "Where A has no part your scenario needs, write that part in the manner of A's other parts, or from its line "
    "frame below. No one of A, B or C may show through: a judge who knows Nox must not recognise any of them under "
    "new nouns.", ""]


def blend_card(dealer, scenarios, intro=True):
    """The blended quests of one map: for each quest a shape (A, of another kind), a trouble (B) and for two in three a
    payoff or complication (C), from three chapters, none from the scenario's own packet pool or near it; about half
    get one loose spot. Returns (markdown, {scenario: [keys dealt]}, {quest: arm}, [(scenario, parts A has no part
    for)])."""
    import json
    import westwood
    if not hasattr(dealer, "bunits"):
        dealer.bunits = _blend_units()
        dealer.buse = collections.Counter()
        dealer.bscen = collections.defaultdict(set)
        dealer.untidy = []
        S = westwood.strings()
        d = json.load(open(os.path.join(HERE, "scenarios.json"), encoding="utf-8"))
        dealer.bnear = {sid: {u for u, x in dealer.bunits.items() if _near_pool(x, sid, S, d)} for sid in SCEN_FAMILY}
    rng, U = dealer.rng, dealer.bunits
    L = list(BLEND_INTRO) if intro else []
    used, arms, need, mine = {}, {}, {}, set()           # mine: no Westwood quest twice on one map
    pick = lambda xs: (rng.shuffle(xs), xs.sort(key=lambda u: dealer.buse[u]), xs[0])[2] if xs else None
    for sid, parts in scenarios:
        if sid not in SCEN_FAMILY: continue
        for sub in (("a", "b") if sid == "two_givers" else ("",)):
            fam = SCEN_FAMILY[sid] if sid != "two_givers" else ({"deal"} if sub == "b" else {"deal", "bounty"})
            ok = lambda u: sid not in U[u]["pools"] and u not in dealer.bnear[sid] and u not in mine
            a = pick([u for u in U if ok(u) and U[u]["family"] not in fam and u not in dealer.bscen[sid]
                      and "offer" in U[u]["parts"] and len(U[u]["parts"]) >= 2])
            b = pick([u for u in U if ok(u) and u != a and U[u]["chapter"] != U[a]["chapter"]
                      and U[u]["family"] not in fam | {U[a]["family"], "gift"}])
            arm = rng.choice(["AB", "ABC", "ABC"])
            c = pick([u for u in U if ok(u) and u not in (a, b)
                      and U[u]["chapter"] not in (U[a]["chapter"], U[b]["chapter"])]) if arm == "ABC" else None
            for u in (a, b, c):
                if u: dealer.buse[u] += 1; mine.add(u)
            dealer.bscen[sid].add(a)
            un = None
            if rng.random() < 0.5:
                if not dealer.untidy:
                    dealer.untidy = list(UNTIDY); rng.shuffle(dealer.untidy)
                for i, x in enumerate(dealer.untidy):
                    if sid not in _pools_of_key(x[0]):
                        un = dealer.untidy.pop(i); break
            q = sid + (f"_{sub}" if sub else "")
            role_c = rng.choice(["payoff", "complication"]) if c else ""
            arms[q] = dict(arm=arm, c=role_c, loose=bool(un), A=a, B=b, C=c, U=un[0] if un else None)
            used.setdefault(sid, [])
            used[sid] += [k for u in (a, b, c) if u for k in U[u]["keys"]] + ([un[0]] if un else [])
            show = lambda u: " | ".join(f"*{p}*: \"{t}\"" for p, t in U[u]["parts"].items())
            title = {"a": "two_givers, the first ask (offer_a, outcome_a, journal_a)",
                     "b": "two_givers, the odd ask (offer_b, outcome_b, journal_b)"}.get(sub, sid)
            L += [f"#### {title}", "",
                  f"- **Shape (A)**, a {U[a]['family']} quest: {show(a)}",
                  f"- **Trouble (B)**, from a {U[b]['family']} quest: {show(b)}"]
            if c: L.append(f"- **{'Payoff' if role_c == 'payoff' else 'Complication'} (C)**, from a {U[c]['family']} quest: {show(c)}")
            if un: L.append(f"- **A loose spot:** \"{un[1]}\" ({un[2]})")
            L.append("")
            for p, st in parts:                         # the parts A has no part for get a line frame
                if sid == "two_givers" and not p.endswith("_" + sub): continue
                qp = QUEST_PART_OF.get(p)
                if qp is None or qp not in U[a]["parts"]: need.setdefault(sid, []).append((p, st))
    return "\n".join(L), used, arms, [(sid, ps) for sid, ps in need.items()]


# ---- part frames (v14): each part of a quest from a different Westwood quest's line of the same kind -------------------
# i13's blends (a shape, a trouble and a payoff from three Westwood quests, and a loose spot) were original but
# overstuffed: every source added matter (backstory, helpers, logistics, a persona), and the loose spots read as
# performed. i10's whole-quest frames kept Westwood's plainness but were Westwood's quests under new nouns. A part frame
# gives each part of a quest (offer, refusal, reminder, thanks, afterwards) one Westwood line of that kind, each from a
# different Westwood quest, never from the scenario's own packet pool: the size and rhythm are Westwood's part by part,
# the quest as a whole is no one quest of Westwood's, and the matter is only the scenario's.

PART_SIT = {"offer": "offer", "plea": "offer", "opening": "offer", "offer_a": "offer", "offer_b": "offer",
            "reminder": "reminder", "completion": "completion", "outcome_a": "completion", "outcome_b": "completion",
            "after": "after", "refusal": "refusal"}
PART_WORDS = {"offer": (12, 130), "reminder": (3, 40), "completion": (6, 80), "after": (2, 30), "refusal": (3, 40)}


def _part_pools():
    """{situation: [(key, speaker id, text)]}: every distinct campaign line of a quest part, with its map and speaker."""
    import westwood
    out = collections.defaultdict(list)
    for r in westwood.campaign():
        if r["dup"] or r["situation"] not in PART_WORDS: continue
        lo, hi = PART_WORDS[r["situation"]]
        if not lo <= len(r["text"].split()) <= hi: continue
        out[r["situation"]].append((r["key"], f"{r['map']}:{r['speaker']}",
                                    re.sub(r"\s*\n\s*\n\s*", " / ", r["text"].strip()).replace("\n", " ")))
    return out


def part_frames_card(dealer, scenarios):
    """Each quest part a Westwood line of its kind, every part of a quest from another Westwood speaker, none from the
    scenario's own pool or near it. Returns (markdown, {scenario: [keys]}, [(scenario, parts left to line frames)])."""
    import difflib, json
    import westwood
    if not hasattr(dealer, "ppools"):
        dealer.ppools = _part_pools()
        import originality as O                         # quest givers' offers (not shop pitches), but for the odd ask
        dealer.qoffers = {k for q in O.ww_quests() for k in q["keys"]}
        S = westwood.strings()
        d = json.load(open(os.path.join(HERE, "scenarios.json"), encoding="utf-8"))
        pooltexts = {}
        for s in d["scenarios"]:
            pooltexts[s["id"]] = [S[x] for u in s["westwood"] + s.get("control_extra", []) for _, k in u
                                  for x in (k if isinstance(k, list) else [k]) if x in S]
        dealer.pnear = {}
        for sid, pts in pooltexts.items():
            dealer.pnear[sid] = {k for xs in dealer.ppools.values() for k, _, t in xs
                                 if sid in _pools_of_key(k) or any(difflib.SequenceMatcher(None, t, p).ratio() > 0.6 for p in pts)}
    L = ["### Your quests: each part from its own Westwood line", "",
         "Each part of each quest below is dealt one of Westwood's own lines of the same kind (an offer for your offer, "
         "a reminder for your reminder, a thanks for your thanks), each from a different Westwood quest. Write each "
         "part to its line's size and rhythm: the same number of pages and sentences, about as many words (never more "
         "than a tenth over), its ! and ? where they fall, how it opens and ends, its register and its quirks, stock "
         "phrases where it has them. The matter is your scenario's: each of the line's sentences becomes a sentence "
         "about your quest that does the same job (an outcry stays an outcry, the trouble becomes your trouble, a place "
         "your place, the ask your ask, a reward your reward, a stray remark a stray remark). Nothing the line has no "
         "sentence for. Never five of its words in a row, never a Westwood name.", ""]
    used, need = {}, []
    for sid, parts in scenarios:
        if sid not in SCEN_FAMILY: continue
        speakers = set()
        lines = []
        for p, st in parts:
            sit = PART_SIT.get(p)
            if not sit:
                need.append((sid, [(p, st)])); continue
            deck = dealer.decks.setdefault(f"_part_{sit}", [])
            pick = None
            for _ in range(2):
                for i, (k, spk, t) in enumerate(deck):
                    if k not in dealer.pnear[sid] and spk not in speakers and (
                            sit != "offer" or p == "offer_b" or k in dealer.qoffers):
                        pick = deck.pop(i); break
                if pick: break
                fresh = list(dealer.ppools[sit]); dealer.rng.shuffle(fresh); deck += fresh
            if not pick:
                need.append((sid, [(p, st)])); continue
            speakers.add(pick[1])
            used.setdefault(sid, []).append(pick[0])
            lines.append(f"- `{sid}.{p}`: \"{pick[2]}\"  ({pick[0]})")
        L += lines
    L.append("")
    merged = collections.OrderedDict()
    for sid, ps in need: merged.setdefault(sid, []).extend(ps)
    return "\n".join(L), used, list(merged.items())
