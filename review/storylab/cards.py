"""A story card (v2: shapes without quoted instances; i5 writers copied the quotes into one template): a map's own draw of Westwood's shapes and model lines, so that maps written by agents with one brief do
not all come out of one template.

    py tests/storylab.py card <seed>      (the map's name is a good seed) prints the card

i4 showed it: ten writers given one brief and one set of exemplars converge on the same lines ("Dead? All of 'em? Ha!",
"Psst! ... Heh, heh, heh", "Did X send you?", three rescued boys named Wim). Westwood's quests are spread over many
shapes; a card draws each map's shapes from that spread (the lists below are Westwood's, from the campaign), and gives
every part two or three model lines of its own, drawn from review/storylab/exemplars.
"""
import os, random, re, sys

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
                xs.append((r["key"], re.sub(r"\s*\n\s*\n\s*", " / ", r["text"].strip())))
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


def frames_card(dealer, scenarios):
    """The frames of one map: {scenario: {part: (key, text)}} and its markdown."""
    L = ["### Your frames: one Westwood line a part, to rewrite line for line", "",
         "Each part of your town is a rewrite of its frame. Keep the frame's shape: about as many sentences, its "
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
            if not fs: continue
            fr = dealer.deal(fs)
            if not fr: continue
            got.setdefault(sid, {})[part] = fr
            L.append(f"- `{sid}.{part}`: \"{fr[1]}\"  ({fr[0]})")
    L.append("")
    return got, "\n".join(L)
