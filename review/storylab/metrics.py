"""The metric judge: a line, a quest's set of lines, or a map's whole story measured against Westwood's campaign.

Westwood's lines (westwood.py, sorted by situation) give the distributions: words per line, sentences, words per
sentence, paragraphs; how often a line exclaims, asks, addresses the listener ("lad", "kind sir", "stranger"), names a
place or a person, gives a direction; contractions; the punctuation it uses ("--" and "...", never ";"). A line is
scored 0-10 for its situation; a variant (a scenario's set of lines) is the mean of its lines, less what is wrong with
it as a whole (consistency: names that are not on the map, a reward over the budget, journal entries that are not
objectives, lines copied from Westwood).

    import metrics
    m = metrics.judge_line(text, situation, names)      # {"score", "flags", "features"}
    v = metrics.judge_unit(parts, situation_of, ctx)    # parts: [(part, speaker, text)]
"""
import collections, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# capitalised words that are not names: creature kinds (Westwood capitalises them: "the Ogres", "Urchins"), titles and
# roles, the world, interjections Westwood writes mid-line ("Heh", "Hmmm")
COMMON_CAPS = set("""I Nox Ogre Ogres Urchin Urchins Undead Spider Spiders Bandit Bandits Wolf Wolves Bat Bats Imp Imps
Troll Trolls Golem Golems Necromancer Necromancers Scorpion Scorpions Zombie Zombies Skeleton Skeletons Ghost Ghosts
Wisp Wisps Beast Beasts Demon Demons Rogue Rogues Shade Shades Mimic Leech Leeches Lich Liches Beholder Gargoyle Bear
Bears Dryad Mayor Captain Reeve Master Sir Lord Lady King Queen Warlord Guildmaster Priest Priests Warden Foreman Chief
Engineer Sergeant Farmer Father Mother Sister Brother Elder Archmagister Magister Gatekeeper Guard Guards Smith Miller
Elder Abbot Hermit Watch Watchman Constable Bailiff Steward Innkeeper Keeper Undertaker Archivist Apprentice Adept
Adventurer Adventurers Wanderer Traveler Traveller Stranger Friend Champion Intruder God Gods Heh Hmm Hmmm Hmmmph Ah Oh
Ahh Eh Aye Bah Psst Pssst Hiccup Arf Yay Ugh Ew Ooooh Ooh Ho Hail Greetings Welcome Thanks Please Yes No Not The A An
Hello Hey Well Now Then But And Or So If When While Go Get Take Bring Find Come Look Watch Mind Keep Stand Help Hurry
Quickly Good Very Many Fine Excellent Congratulations Sorry Halt Move Run Stop Remember Beware Tell Kill North South East
West Northeast Northwest Southeast Southwest NOTE Hint Quest COMPLETED Dark Black Arts Mother Nature""".split())

CLASSES = ["Fire Knights", "Fire Knight", "Warriors", "Warrior", "Conjurers", "Conjurer", "Wizards", "Wizard",
           "Mages", "Mage", "Arch-Wizard", "Arch-Mage", "Apprentice", "Adept"]

# Westwood's own names, with a kind (person, place, thing, group) for the blind packets' masks
WW_NAMES = {
    "person": """Hecubah Horrendous Horvath Aldwyn Aldwin Theogrin Jandor Mordwyn Lewis Gerard Thavius Matilda Ingrid
        Glynda Gearhart Byzanti Maximillian Max Stravas Morgan Lightfingers Lightfinger Kalen Gavin Kincaid Grillf Mlurgh Henrick
        Delwin Brenneth Aidan Cain Lydia Daniel Marik Belfor Halric Loproc Garret Bing Ganem Jorgan Grunbar Albi Dorian
        Valkor Alark Kylerean Vows Allistor Grendel Azeruth Perlas Chump Gearhead Lucky Isabella Gustavius Balthorak
        Rust Bull Fenton Booth Hight Fulton Mystic Googinado Glurgin""".split(),
    "place": """Ix Brin Galava Torr Grok Mir Dün Dun Valor Crossroads Illusion Swamp Dismal Wasteland Underworld""".split(),
}
WW_PHRASES = [
    ("place", "Village of Ix"), ("place", "Hamlet of Brin"), ("place", "Village of Brin"), ("place", "Dün Mir"),
    ("place", "Dun Mir"), ("place", "Grok Torr"), ("place", "Tower of Illusion"), ("place", "Field of Valor"),
    ("place", "Tombs of Valor"), ("place", "Tomb of Valor"), ("place", "Mana Mines"), ("place", "Land of the Dead"),
    ("place", "Dismal Swamp"), ("place", "Southern Lands"), ("place", "Temple of Ix"), ("place", "Castle Galava"),
    ("place", "Spire Street"), ("place", "Xon Pools"), ("place", "Wizard's Keep"), ("place", "Bing's Tavern"),
    ("place", "Machinery Building"), ("place", "Main Power Room"), ("place", "Miner's Lodge"), ("place", "Griffon's Nest"),
    ("place", "Books-For-Less"), ("place", "Books For Less"), ("place", "Inn of the Urchin's Ear"),
    ("place", "Church of St. Allistor"), ("place", "the Gauntlet"), ("place", "The Gauntlet"),
    ("person", "Morgan Lightfingers"), ("person", "Bull Byzanti"), ("person", "Lewis the Talking Frog"),
    ("person", "St. Allistor"), ("person", "St. Grendel"), ("person", "Mayor Theogrin"), ("person", "Farmer Thavius"),
    ("person", "Bright Blades"),
    ("thing", "Heart of Nox"), ("thing", "Staff of Oblivion"), ("thing", "Halberd of Horrendous"),
    ("thing", "Book of Oblivion"), ("thing", "Amulet of Clarity"), ("thing", "Amulet of Teleportation"),
    ("thing", "Weirdling Beast"), ("thing", "Weirdling"), ("thing", "Orb"), ("thing", "Charm Creature"),
    ("group", "Order of Oblivion"), ("group", "Mystic Brotherhood"), ("group", "Mages' Guild"),
    ("group", "Wizards' Guild"), ("group", "Fire Knights"),
]

ADDRESS = re.compile(r"\b(lad|sir|kind sir|friend|stranger|travell?er|adventurer|wanderer|mate|my son|son|my boy|"
                     r"boy|young (?:man|one|sir|\w+)|brother|cell-brother|citizen)\b", re.I)
DIRECTION = re.compile(r"\b(north|south|east|west|north-?east|north-?west|south-?east|south-?west|northern|southern|"
                       r"eastern|western|of here|of town|across the|past the|beyond the|down the|up the|next to|"
                       r"behind|straight ahead|on the right|on the left|to your (?:right|left)|nearby|in the woods|"
                       r"at the end of|outside)\b", re.I)
NUMBER = re.compile(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|twenty|fifty|hundred|thousand|"
                    r"first|second|third|half|dozen)\b", re.I)
CONTRACTION = re.compile(r"\b\w+(n't|'s|'re|'ll|'ve|'d|'m)\b|\b(c'mon|'em|y'|ya|yer|fer)\b", re.I)
ASK = re.compile(r"\b(please|would you|could you|will you|can you|if you|bring|find|go|get|fetch|kill|rescue|"
                 r"return|recover|retrieve|save|help|free|take|find|clear|drive|deal with|put an end|stop)\b", re.I)
HANDOVER = re.compile(r"\b(take (?:this|these|it)|here(?:'s| is| are|,)|accept|please take|reward|gold|as promised|"
                      r"token|gift|yours|for you)\b", re.I)
THANKS = re.compile(r"\b(thank|thanks|grateful|gratitude|bless|indebted|well done|excellent|you did it|my .+!)", re.I)

IMPERATIVE = set("""find retrieve rescue go return kill defeat recover save escort bring speak meet locate survive search
charm break take follow sneak free chase battle enter discover request rendezvous energize stop escape show deliver
regain clear drive put get visit seek ask tell help hunt slay destroy protect guard investigate learn talk fetch open
light relight carry collect gather catch arrest cleanse explore reach climb burn banish""".split())

# words and turns of phrase that never came out of Westwood's Nox
MODERN = re.compile(r"\b(okay|ok|guys|cool|awesome|no worries|hang out|deal with it|you got this|level up|xp|npc|"
                    r"loot|respawn|spawn|boss fight|grind|nerf|buff|stats|teleporter pad|vibe|super|basically|"
                    r"literally|totally|whatever|kids|deadline|team|update|status|focus|process|issue|feedback|"
                    r"weekend plans|stressed|cheers mate)\b", re.I)
ANACHRONISM = re.compile(r"\b(guns?|pistols?|rifles?|cannons?|phones?|cars?|trains?|engines?|computers?|radios?|"
                         r"photographs?|factor(?:y|ies)|police|cops?|sheriffs?|dollars?|cents|coffee|potato(?:es)?|"
                         r"tomato(?:es)?|tobacco|cigars?|o'clock|seconds|percent|okay)\b", re.I)
# typography Westwood's table never has: it writes "--" and "...", straight quotes
TYPO = [("—", "an em dash (Westwood writes --)"), ("–", "an en dash (Westwood writes --)"),
        ("…", "a typographic ellipsis (Westwood writes ...)"), ("’", "a curly quote"), ("“", "a curly quote"),
        ("”", "a curly quote")]

SITUATION_FALLBACK = {"rumour": "townsfolk", "bark": "townsfolk", "greeting": "shop", "objective": "journal",
                      "journal_done": "journal", "opening": "offer", "plea": "offer", "following": "reminder",
                      "found": "offer", "outcome": "completion"}


def words(t):
    return re.findall(r"[A-Za-zÀ-ÿ']+(?:-[A-Za-zÀ-ÿ']+)*", t)


def sentences(t):
    t = re.sub(r"\.\.\.+(?=\s+[a-z])", ",", t)              # "...and" carries on
    parts = re.split(r"(?<=[.!?])\s+|\n+|(?<=\.\.\.)\s+(?=[A-Z])", t.strip())
    return [p for p in parts if words(p)]


def _initial_positions(t):
    """Character offsets where a sentence (or a line, or a clause after -- or ...) starts."""
    pos = {0}
    for m in re.finditer(r"([.!?:]['\"]?\s+|\n+|--\s*|\.\.\.\s*|^['\"]|\(\s*)", t):
        pos.add(m.end())
    return pos


def name_spans(t, known=None):
    """[(start, end, word)] of the proper nouns in t: capitalised words not starting a sentence and not common, plus
    any word or phrase in `known` (a set of names) wherever it stands."""
    known = known or set()
    starts = _initial_positions(t)
    spans = []
    for ph in sorted(known, key=len, reverse=True):
        if " " in ph:
            for m in re.finditer(r"\b" + re.escape(ph) + r"\b", t):
                if not any(a < m.end() and m.start() < b for a, b, _ in spans): spans.append((m.start(), m.end(), ph))
    for m in re.finditer(r"\b[A-ZÀ-Ý][A-Za-zÀ-ÿ]+(?:-[A-Z][a-z]+)?(?:'s)?", t):
        w = re.sub(r"'s$", "", m.group(0))
        if any(a <= m.start() < b for a, b, _ in spans): continue
        if w in COMMON_CAPS or any(w == c for c in CLASSES): continue
        if w in known or m.start() not in starts:
            if w.isupper() and len(w) > 1 and w not in known: continue          # shouting: "MURDERER", "GUARDS"
            spans.append((m.start(), m.start() + len(w), w))
    return sorted(spans)


def features(t, known=None):
    w = words(t)
    s = sentences(t) or [t]
    nw = max(1, len(w))
    sps = [len(words(x)) for x in s]
    f = dict(words=len(w), sentences=len(s), wps=sum(sps) / len(sps), long_sentence=max(sps),
             paragraphs=len([p for p in re.split(r"\n\s*\n", t) if p.strip()]),
             excl=int("!" in t), quest=int("?" in t), semicolons=t.count(";"),
             colons=len(re.findall(r":(?!\s*$)", t)), dash=t.count("--"), ellipsis=t.count("..."),
             address=int(bool(ADDRESS.search(t))), contractions=len(CONTRACTION.findall(t)) / nw,
             names=len(name_spans(t, known)), direction=int(bool(DIRECTION.search(t))),
             numbers=len(NUMBER.findall(t)), first_person=len(re.findall(r"\b(I|me|my|mine|I'm|I've|I'll)\b", t)),
             second_person=len(re.findall(r"\b(you|your|yours|you're|you'll|you've)\b", t, re.I)),
             imperatives=sum(1 for x in s if words(x) and words(x)[0].lower() in IMPERATIVE),
             caps_shout=len(re.findall(r"\b[A-Z]{3,}\b", t)),
             excl_share=sum(1 for x in s if x.rstrip(" .'\"").endswith("!") or "!" in x[-3:]) / len(s))
    f["info"] = (f["names"] + f["direction"] + min(f["numbers"], 2) + f["imperatives"]) * 10.0 / nw
    f["rare"] = rare_share(t, known)
    return f


_VOCAB = None


def ww_vocab():
    """Counter of the lower-case words in Westwood's distinct campaign lines."""
    global _VOCAB
    if _VOCAB is None:
        import westwood
        _VOCAB = collections.Counter()
        for r in westwood.campaign():
            if not r["dup"]: _VOCAB.update(x.lower() for x in words(r["text"]))
    return _VOCAB


def rare_share(t, known=None, own=False):
    """The share of a line's common words (not names, not short) that Westwood's lines never use; own: the line is
    Westwood's, so its own words are taken out of the count first (leave-one-out)."""
    v = ww_vocab()
    names = {w.lower() for _, _, w in name_spans(t, known)}
    ws = [x.lower() for x in words(t) if len(x) > 3 and x.lower() not in names and not x[0].isupper()]
    if not ws: return 0.0
    mine = collections.Counter(ws) if own else collections.Counter()
    return sum(1 for x in ws if v[x] - mine[x] <= 0) / len(ws)


def _q(xs, p):
    xs = sorted(xs)
    if not xs: return 0
    i = (len(xs) - 1) * p
    lo = int(math.floor(i)); hi = min(len(xs) - 1, lo + 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


# ---- Westwood's distributions ---------------------------------------------------------------------------------------

_STATS = None
NUMERIC = ["words", "sentences", "wps", "long_sentence", "paragraphs", "info", "rare"]
RATES = ["excl", "quest", "semicolons", "colons", "dash", "ellipsis", "address", "contractions", "names", "direction",
         "numbers", "first_person", "imperatives"]


def ww_lexicon():
    import westwood
    names = set(westwood.proper_nouns()) | {p for _, p in WW_PHRASES}
    for kind, ws in WW_NAMES.items(): names |= set(ws)
    return names


def ww_stats():
    """{situation: {feature: {p10, p25, p50, p75, p90, mean}}} over Westwood's distinct campaign lines."""
    global _STATS
    if _STATS is not None: return _STATS
    import westwood
    known = ww_lexicon()
    by = collections.defaultdict(list)
    for r in westwood.campaign():
        if r["dup"]: continue
        f = features(r["text"], known)
        f["rare"] = rare_share(r["text"], known, own=True)
        by[r["situation"]].append(f)
        if r["situation"] not in ("journal", "hint", "sign", "system", "narration"): by["dialogue"].append(f)
    out = {}
    for s, fs in by.items():
        d = {"n": len(fs)}
        for k in NUMERIC + RATES:
            xs = [f[k] for f in fs]
            d[k] = dict(p05=_q(xs, .05), p10=_q(xs, .1), p25=_q(xs, .25), p50=_q(xs, .5), p75=_q(xs, .75), p90=_q(xs, .9), p95=_q(xs, .95),
                        mean=sum(xs) / len(xs))
        out[s] = d
    _STATS = out
    return out


_NGRAMS = None


def ww_ngrams(n=6):
    """{6-gram: in how many of Westwood's distinct lines}."""
    global _NGRAMS
    if _NGRAMS is None:
        import westwood
        g = collections.Counter()
        for r in westwood.campaign():
            if r["dup"]: continue
            w = [x.lower() for x in words(r["text"])]
            g.update({tuple(w[i:i + n]) for i in range(len(w) - n + 1)})
        _NGRAMS = g
    return _NGRAMS


_MODES = None


def modes():
    """The phrases the lab's writers all reach for (review/storylab/modes.json, from `py tests/storylab.py modes`):
    four words that three or more towns of one round wrote and Westwood never did. The model's first idea, which every
    map agent has too."""
    global _MODES
    if _MODES is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modes.json")
        _MODES = [tuple(x.split()) for x in json.load(open(p, encoding="utf-8"))["phrases"]] if os.path.exists(p) else []
    return _MODES


def mode_hits(t):
    w = [x.lower() for x in words(t)]
    g = {tuple(w[i:i + 4]) for i in range(len(w) - 3)}
    return [" ".join(m) for m in modes() if m in g]


def copied(t, n=6):
    """Westwood's phrases a line repeats. A stock phrase Westwood itself uses in two lines or more ("as a token of my
    appreciation", "thanks again for your help") is the house style the guide asks for, not a copy."""
    w = [x.lower() for x in words(t)]
    g6 = ww_ngrams(n)
    return [" ".join(g) for g in (tuple(w[i:i + n]) for i in range(len(w) - n + 1)) if g6.get(g, 0) == 1]


# ---- judging --------------------------------------------------------------------------------------------------------

def _range_penalty(x, d, weight, log=True):
    lo, hi = d["p05"], d["p95"]
    if lo <= x <= hi: return 0.0
    if log:
        x, lo, hi = math.log(max(x, .5)), math.log(max(lo, .5)), math.log(max(hi, .5))
        span = max(.3, hi - lo)
    else:
        span = max(1.0, hi - lo)
    dist = (lo - x) if x < lo else (x - hi)
    return min(weight, weight * dist / span * 1.5)


def judge_line(t, situation, known=None, allowed=None, westwood=False):
    """Score one line (0-10) for its situation; `known`: the names the map has (for the masks and the consistency
    check), `allowed`: names the line may use (None: no check)."""
    st = ww_stats()
    sit = situation if situation in st else SITUATION_FALLBACK.get(situation, "dialogue")
    d = st.get(sit) or st["dialogue"]
    f = features(t, known)
    if westwood: f["rare"] = rare_share(t, known, own=True)
    flags, pen = [], 0.0

    def hit(p, msg):
        nonlocal pen
        if p > 0.05:
            pen += p
            flags.append(f"-{p:.1f} {msg}")

    hit(_range_penalty(f["words"], d["words"], 2.5), f"{f['words']} words (Westwood's {sit}: {d['words']['p05']:.0f}-{d['words']['p95']:.0f})")
    if f["sentences"] > 0 and sit != "sign":
        hit(_range_penalty(f["wps"], d["wps"], 1.5), f"{f['wps']:.1f} words a sentence (Westwood {d['wps']['p05']:.0f}-{d['wps']['p95']:.0f})")
        if f["long_sentence"] > max(d["long_sentence"]["p95"], 14):
            hit(min(1.0, (f["long_sentence"] - max(d["long_sentence"]["p95"], 14)) / 12), f"a {f['long_sentence']}-word sentence")
    if f["rare"] > d["rare"]["p90"] and f["words"] >= 6:
        hit(min(2.0, 6 * (f["rare"] - d["rare"]["p90"])), f"{f['rare']:.0%} of its words Westwood never uses (its {sit} lines: at most {d['rare']['p90']:.0%})")
    if f["paragraphs"] > max(1, d["paragraphs"]["p90"]):
        hit(0.7 * (f["paragraphs"] - max(1, d["paragraphs"]["p90"])), f"{f['paragraphs']} paragraphs")
    if f["semicolons"]: hit(min(2.0, 0.8 * f["semicolons"]), f"{f['semicolons']} semicolon(s): Westwood's dialogue has none")
    if f["colons"] and sit not in ("sign", "journal"):
        hit(min(1.0, 0.5 * f["colons"]), f"{f['colons']} colon(s) mid-line: Westwood almost never")
    for ch, msg in TYPO:
        if ch in t: hit(0.7, msg)
    for m in MODERN.findall(t): hit(1.5, f"modern idiom: {m if isinstance(m, str) else m[0]!r}")
    for m in ANACHRONISM.findall(t): hit(1.5, f"anachronism: {m if isinstance(m, str) else m[0]!r}")
    mh = [] if westwood else mode_hits(t)
    if mh: hit(min(2.0, 0.8 * len(mh)), f"a phrase every writer reaches for: {mh[0]!r} (review/storylab/modes.json)")
    cp = [] if westwood else copied(t)
    if cp: hit(min(3.0, 1.0 + 0.3 * len(cp)), f"copied from Westwood: {cp[0]!r}")
    if allowed is not None:
        unknown = sorted({w for _, _, w in name_spans(t, known) if w not in allowed})
        if unknown: hit(min(3.0, 1.0 * len(unknown)), "names not on the map: " + ", ".join(unknown))
    # what each situation must carry
    if sit == "journal":
        t = re.sub(r"^COMPLETED:\s*", "", t)          # a done entry: the objective's own words (q.done)
        w0 = (words(t) or [""])[0].lower()
        if w0 not in IMPERATIVE and not t.startswith("NOTE"):
            hit(2.0, f"a journal entry starts with an order (Find, Retrieve, Rescue...), not {w0!r}")
        if f["first_person"]: hit(2.0, "a journal entry in the first person: Westwood's are objectives")
        if f["names"] == 0 and not f["direction"]: hit(0.4, "the objective names no person, place or thing")
    elif situation in ("offer", "opening", "plea"):
        if not ASK.search(t) and "?" not in t: hit(1.5, "an offer that asks nothing")
        if f["names"] == 0 and not f["direction"]: hit(0.5, "an offer that names no place or person and gives no way")
    elif situation in ("completion", "outcome"):
        if not THANKS.search(t) and "!" not in t: hit(0.5, "a completion with no thanks or delight")
        if not HANDOVER.search(t): hit(0.5, "a completion that hands nothing over (take this, here is, as promised)")
    elif situation == "reminder":
        if f["words"] > max(25, d["words"]["p90"]): hit(1.0, "a reminder longer than Westwood's: one or two short sentences")
    elif situation == "rumour":
        if f["names"] == 0 and not f["direction"]: hit(0.4, "a rumour that names no person or place")
    f["situation"] = sit
    return dict(score=max(0.0, 10.0 - pen), flags=flags, features=f)


def judge_unit(parts, ctx=None):
    """parts: [{"part", "speaker", "text"}]; ctx: the scenario's map context ({"names": {name: kind}, "budget": gold,
    "items": [...]}) or None. Returns {"score", "lines": [...], "flags"}."""
    ctx = ctx or {}
    if ctx.get("names") is None:                      # Westwood's own lines: its names, no consistency check
        known, allowed = ww_lexicon(), None
    else:
        known = {n for n in ctx["names"] if n[:1].isupper()}
        allowed = known
    lines = []
    for p in parts:
        r = judge_line(p["text"], p.get("situation") or p["part"], known, allowed, westwood=allowed is None)
        r.update(part=p["part"], speaker=p.get("speaker", ""), text=p["text"])
        lines.append(r)
    flags, pen = [], 0.0
    vs, vflags = voice([l["features"] for l in lines])
    flags += vflags
    rw = ctx.get("reward") or {}
    if rw:
        if rw.get("gold", 0) > ctx.get("budget", 10 ** 9):
            pen += 2; flags.append(f"-2.0 reward {rw['gold']} gold over the budget {ctx['budget']}")
        bad = [i for i in rw.get("items", []) if ctx.get("items") and i not in ctx["items"]]
        if bad: pen += 1; flags.append(f"-1.0 reward items not in the scenario's list: {bad}")
    jn = [l for l in lines if l["part"].startswith("journal")]
    if ctx.get("needs_journal") and not jn:
        pen += 1.5; flags.append("-1.5 no journal entry")
    score = 0.75 * (sum(l["score"] for l in lines) / max(1, len(lines))) + 0.25 * vs - pen
    return dict(score=max(0.0, score), lines=lines, flags=flags, voice=vs)


def voice(fs):
    """How a set of lines sounds together (0-10), against Westwood's dialogue as a whole: how many exclaim or ask,
    address the player, run on with semicolons. Few lines say little, so the bounds widen for small sets."""
    st = ww_stats()["dialogue"]
    talk = [f for f in fs if f.get("situation") not in ("journal", "sign", "narration", "system", "hint")]
    if not talk: return 10.0, []
    n = len(talk)
    slack = 0.15 + 0.5 / math.sqrt(n)               # one line: anything goes; forty: within 0.23
    out, pen = [], 0.0
    lively = sum(1 for f in talk if f["excl"] or f["quest"]) / n
    ww_lively = 0.66
    if lively < ww_lively - slack:
        p = min(4.0, 12 * (ww_lively - slack - lively)); pen += p
        out.append(f"-{p:.1f} voice: {lively:.0%} of the lines exclaim or ask (Westwood's {ww_lively:.0%})")
    # and not every sentence: Westwood's lines exclaim in about half their sentences, at most
    sent = [s for f in talk for s in [f.get("excl_share", None)] if s is not None]
    ns = sum(f["sentences"] for f in talk)
    if ns >= 6 and sent:
        ex = sum(s * f["sentences"] for s, f in zip(sent, talk)) / ns
        lim = 0.37 + 0.12 + 0.5 / math.sqrt(ns)       # Westwood: 37% of the sentences of its dialogue exclaim
        if ex > lim:
            p = min(3.0, 10 * (ex - lim)); pen += p
            out.append(f"-{p:.1f} voice: {ex:.0%} of the sentences exclaim (Westwood's 37%)")
    dash = sum(1 for f in talk if f["dash"]) / n
    if n >= 4 and dash > 0.05 + slack:
        p = min(1.5, 5 * (dash - 0.05 - slack)); pen += p
        out.append(f"-{p:.1f} voice: {dash:.0%} of the lines use ' -- ' (Westwood's 5%)")
    num = sum(1 for f in talk if f["numbers"]) / n
    if n >= 4 and num > st["numbers"]["mean"] + 0.1 + slack:
        p = min(1.0, 4 * (num - st["numbers"]["mean"] - 0.1 - slack)); pen += p
        out.append(f"-{p:.1f} voice: {num:.0%} of the lines count or number things")
    ad = sum(f["address"] for f in talk) / n
    if n >= 8 and ad > 2.5 * st["address"]["mean"]:
        p = min(1.5, 6 * (ad - 2.5 * st["address"]["mean"])); pen += p
        out.append(f"-{p:.1f} voice: {ad:.0%} of the lines address the player (Westwood {st['address']['mean']:.0%}): "
                   "one address word a quest at most")
    if n >= 6 and ad < 0.04:
        pen += 1.0; out.append(f"-1.0 voice: no line addresses the player (lad, stranger, friend, kind sir; Westwood {st['address']['mean']:.0%})")
    sem = sum(f["semicolons"] for f in talk)
    if sem:
        p = min(3.0, 30.0 * sem / n / 10); pen += p
        out.append(f"-{p:.1f} voice: {sem} semicolons in {n} lines (Westwood: 3 in 854)")
    rare = sum(f["rare"] for f in talk) / n
    if rare > st["rare"]["mean"] + 0.06:
        p = min(2.0, 15 * (rare - st["rare"]["mean"] - 0.06)); pen += p
        out.append(f"-{p:.1f} voice: {rare:.0%} of the words are ones Westwood never uses (its mean {st['rare']['mean']:.0%})")
    return max(0.0, 10.0 - pen), out


# ---- masks for the blind packets ------------------------------------------------------------------------------------

def mask(t, names):
    """Proper nouns replaced by their kind in brackets: [Person], [Place], [Thing], [Group]; names: {name: kind}."""
    kinds = dict(names)
    for k, ws in WW_NAMES.items():
        for w in ws: kinds.setdefault(w, k)
    for k, p in WW_PHRASES: kinds.setdefault(p, k)
    for i, c in enumerate(CLASSES):                    # classes first, so "Fire Knight" is not two names
        t = re.sub(r"\b" + re.escape(c) + r"\b", "\x00%d\x00" % i, t)
    out, last = [], 0
    for a, b, w in name_spans(t, set(kinds)):
        out.append(t[last:a]); out.append(f"[{kinds.get(w, 'thing').capitalize()}]"); last = b
    out.append(t[last:])
    s = "".join(out)
    s = re.sub(r"\[(\w+)\](?:'s?)?( of (?:the )?\[\1\])+", r"[\1]", s)   # [Place] of [Place] -> [Place]
    return re.sub("\x00\\d+\x00", "[Class]", s)
