"""Originality: how close our lines and quests come to Westwood's campaign, measured against how close Westwood's own
lines and quests come to each other.

The story lab's best rounds wrote every line and quest from a Westwood "frame". The maps must still be our own
writing, so every line and quest is held to three checks, with thresholds taken from Westwood against Westwood
(each of its distinct lines against every *other* line of the campaign; "other" leaves out the same line reused,
i.e. a pair that matches at 0.8 or more once class words are masked, as the Brin chapter is in all three campaigns):

  line    ngram: the share of the line's word 3-grams (2-grams under 4 words) found in one Westwood line;
          edit: the word-level normalised edit similarity (difflib ratio, 2M/T) to one Westwood line.
          Both are the maximum over the campaign. A line is flagged when either is above Westwood's own 95th
          percentile for lines of its length band; a round or a map passes when its median is no higher than
          Westwood's median and no more than 10% of its lines are flagged (Westwood's own rate is 5% by definition).
  phrase  no run of 5 or more words in a row from a Westwood line with two or more content words in it (a run of
          plain English, "at the end of the", is no copy), unless every 5 words of it are a stock phrase Westwood
          itself uses in two or more different lines or one of the genre's stock phrases rules/DIALOGUE.md asks for
          ("as a token of my appreciation", STOCK_PHRASES).
  quest   the quest's skeleton: each part (offer, reminder, completion, afterwards, refusal) reduced to its function
          words and punctuation with every content word (noun, verb, adjective) as a slot "X", compared part for part
          with every Westwood quest (one speaker's offer, reminder, thanks...). A quest whose skeleton maps onto one
          Westwood quest above Westwood's own 99th percentile (each Westwood quest against its nearest other one:
          0.55; the frames rounds i10-i12 sat at 0.6-0.8 to the quest they were dealt) is flagged: its beats and slots
          follow that quest one to one. A round passes when no more than 10% of its quests are above Westwood's p95.

    py review/storylab/originality.py calibrate        Westwood against Westwood -> review/storylab/originality.json
    py tests/storylab.py originality --iter NAME        a round's lines and quests (and its frames) against Westwood
    py tests/storylab.py --check <design.py>            includes the map's originality
"""
import collections, difflib, json, os, re, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
CAL = os.path.join(HERE, "originality.json")

SPOKEN = {"offer", "reminder", "completion", "after", "refusal", "townsfolk", "guard", "shop", "bump", "foe", "talk"}
BANDS = ((1, 5), (6, 12), (13, 25), (26, 10 ** 6))
QUEST_PARTS = ("offer", "reminder", "completion", "after", "refusal")
_CLASS = re.compile(r"\b(Fire Knight|Warrior|Wizard|Conjurer|Mage|Apprentice|Adept|Adventurer|Wanderer)s?\b", re.I)

FUNCTION = set("""
a an the this that these those there here it its it's i i'm i'll i've i'd me my mine myself you you're you'll you've
you'd your yours yourself he he's him his himself she she's her hers herself we we're we'll we've our ours us they
they're they'll they've them their theirs what which who whom whose when where why how whatever whoever
and or but nor so yet if then than because as while though although unless until till since once whether
of in on at to from by with without about above below into onto out over under up down off through around across
between before after near past for against among upon within beyond toward towards along behind beside like
is are was were be been being am do does did done doing have has had having will would shall should can could may
might must ought won't wouldn't can't couldn't don't doesn't didn't isn't aren't wasn't weren't haven't hasn't
hadn't shouldn't mustn't let let's get got go going gone come came
not no yes nope yeah oh ah ahh ohh hmm hmmm well please thank thanks now just very too also still even only all
any some each every both either neither many much more most few less least such own same other another one
again ever never always already soon here's there's that's what's who's where's how's ok okay
""".split())


def words(t):
    return [w.lower() for w in re.findall(r"[A-Za-z']+(?:-[A-Za-z']+)*", t)]


def _norm(t):
    return _CLASS.sub("Class", t)


def band(n):
    for i, (lo, hi) in enumerate(BANDS):
        if lo <= n <= hi: return i
    return 0


def grams(ws, n=None):
    n = n or (3 if len(ws) >= 4 else 2 if len(ws) >= 2 else 1)
    return {tuple(ws[i:i + n]) for i in range(len(ws) - n + 1)}, n


def template(t):
    """The skeleton of a text: function words kept, every other word an X, punctuation and page breaks as tokens."""
    t = t.replace("\n\n", " / ")
    toks = re.findall(r"[A-Za-z']+(?:-[A-Za-z']+)*|\.\.\.|--|[!?.,/]", t)
    out = []
    for x in toks:
        lx = x.lower()
        if lx in FUNCTION or not lx[0].isalpha(): out.append(lx)
        else: out.append("X")
    return out


# ---- Westwood's lines -------------------------------------------------------------------------------------------------

_LINES = None


def ww_lines():
    """[{key, situation, text, words, gset, n}] for every distinct spoken line and journal entry of the campaign."""
    global _LINES
    if _LINES is None:
        import westwood
        out, seen = [], set()
        for r in westwood.campaign():
            if r["situation"] not in SPOKEN | {"journal"}: continue
            t = r["text"].strip()
            if not t or t in seen: continue
            seen.add(t)
            ws = words(_norm(t))
            if not ws: continue
            out.append(dict(key=r["key"], situation=r["situation"], speaker=r["speaker"], map=r["map"], text=t, words=ws,
                            wset=set(ws)))
        _LINES = out
    return _LINES


_STOCK = None
# the genre's stock phrases rules/DIALOGUE.md asks for (rule 7), used straight: house style, not a copy
STOCK_PHRASES = ("as a token of my appreciation", "please accept this as a token of my appreciation",
                 "I will offer a worthy reward", "May all that is great bless you", "thanks again, brave Adventurer",
                 "take these as tokens of my appreciation", "I'll make it worth your while")


def stock5():
    """5-word phrases Westwood uses in two or more different lines: its house style, not a copy."""
    global _STOCK
    if _STOCK is None:
        c = collections.Counter()
        for l in ww_lines():
            c.update({tuple(l["words"][i:i + 5]) for i in range(len(l["words"]) - 4)})
        _STOCK = {g for g, k in c.items() if k >= 2}
        for ph in STOCK_PHRASES:
            w = words(ph)
            _STOCK |= {tuple(w[i:i + 5]) for i in range(len(w) - 4)}
    return _STOCK


def line_sims(text, skip=None):
    """The closest Westwood line: {"ngram", "edit", "ngram_key", "edit_key", "copied": [phrases of 5+ words]}.
    `skip(l)` leaves a Westwood line out (Westwood against itself: the line and its reused copies)."""
    ws = words(_norm(text))
    if not ws: return dict(ngram=0.0, edit=0.0, ngram_key="", edit_key="", copied=[], n=0)
    g, n = grams(ws)
    best_g, kg, best_e, ke, copied = 0.0, "", 0.0, "", []
    sm = difflib.SequenceMatcher(None, autojunk=False)
    sm.set_seq2(ws)
    wset = set(ws)
    st = stock5()
    for l in ww_lines():
        if not (wset & l["wset"]): continue
        if skip and skip(l): continue
        lg = {tuple(l["words"][i:i + n]) for i in range(len(l["words"]) - n + 1)}
        c = len(g & lg) / len(g) if g else 0.0
        if c > best_g: best_g, kg = c, l["key"]
        sm.set_seq1(l["words"])
        if sm.real_quick_ratio() > best_e and sm.quick_ratio() > best_e:
            r = sm.ratio()
            if r > best_e: best_e, ke = r, l["key"]
        if c > 0 and len(ws) >= 5:
            for m in sm.get_matching_blocks():
                if m.size >= 5:
                    run = l["words"][m.a:m.a + m.size]
                    if sum(1 for w in run if w not in FUNCTION) < 2: continue        # plain English ("at the end of the")
                    if all(tuple(run[i:i + 5]) in st for i in range(len(run) - 4)): continue
                    copied.append((" ".join(run), l["key"]))
    return dict(ngram=best_g, edit=best_e, ngram_key=kg, edit_key=ke, copied=copied, n=len(ws))


def _same_line(a, b):
    """Two Westwood lines that are one line reused (another campaign's copy, a class word changed)."""
    if a["key"].split(":", 1)[-1] == b["key"].split(":", 1)[-1] and a["map"][3:] == b["map"][3:]: return True
    return difflib.SequenceMatcher(None, a["words"], b["words"], autojunk=False).ratio() >= 0.8


# ---- Westwood's quests ----------------------------------------------------------------------------------------------

def ww_quests():
    """[{"id", "keys", "parts": {situation: text}}]: the scenario pools' units and every campaign speaker with an offer
    and another quest part (grouped by map and speaker)."""
    import westwood
    S = westwood.strings()
    d = json.load(open(os.path.join(HERE, "scenarios.json"), encoding="utf-8"))
    SIT = {"offer": "offer", "offer_a": "offer", "plea": "offer", "opening": "offer", "reminder": "reminder",
           "completion": "completion", "outcome_a": "completion", "after": "after", "refusal": "refusal"}
    out, seenkeys = [], set()
    for s in d["scenarios"]:
        if s["id"] in ("guard_bark", "rumour", "shop_greeting", "town"): continue
        for u in s["westwood"] + s.get("control_extra", []):
            parts, keys = {}, []
            for p, k in u:
                ks = k if isinstance(k, list) else [k]
                if p not in SIT: continue
                parts.setdefault(SIT[p], []).extend(S[x] for x in ks if x in S)
                keys += ks
            if not parts.get("offer"): continue
            ks = frozenset(keys)
            if ks in seenkeys: continue
            seenkeys.add(ks)
            out.append(dict(id=f"{s['id']}:{keys[0]}", keys=set(keys), parts={p: "\n\n".join(v) for p, v in parts.items()}))
    used = set().union(*(q["keys"] for q in out))
    g = collections.defaultdict(list)
    for r in westwood.campaign():
        if r["dup"] or r["situation"] not in QUEST_PARTS: continue
        g[(r["map"], r["speaker"])].append(r)
    for (m, sp), rs in sorted(g.items()):
        sits = {r["situation"] for r in rs}
        if "offer" not in sits or len(sits) < 2: continue
        keys = {r["key"] for r in rs}
        if keys <= used: continue
        parts = {}
        for r in rs: parts.setdefault(r["situation"], []).append(r["text"])
        out.append(dict(id=f"{m}:{sp}", keys=keys, parts={p: "\n\n".join(v) for p, v in parts.items()}))
    return out


def quest_sim(parts, unit):
    """How far a quest's skeleton follows one Westwood quest: the length-weighted mean, over the quest's own parts, of
    the part's template against the Westwood quest's part of the same situation (0 where it has none)."""
    num = den = 0.0
    detail = {}
    for p, t in parts.items():
        if p not in QUEST_PARTS or not t.strip(): continue
        a = template(t)
        w = len(a)
        den += w
        if p in unit["parts"]:
            r = difflib.SequenceMatcher(None, a, template(unit["parts"][p]), autojunk=False).ratio()
            num += w * r
            detail[p] = round(r, 2)
    return (num / den if den else 0.0), detail


def nearest_quest(parts, skip_keys=()):
    best = (0.0, None, {})
    for u in ww_quests():
        if u["keys"] & set(skip_keys): continue
        s, det = quest_sim(parts, u)
        if s > best[0]: best = (s, u["id"], det)
    return best


# ---- calibration: Westwood against Westwood -------------------------------------------------------------------------

def _pct(xs, q):
    xs = sorted(xs)
    if not xs: return 0.0
    i = q * (len(xs) - 1)
    lo = int(i)
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (i - lo)


def calibrate():
    lines = ww_lines()
    by_band = collections.defaultdict(lambda: {"ngram": [], "edit": []})
    st = stock5()
    copies = sum(1 for l in lines if any(tuple(l["words"][i:i + 5]) in st for i in range(len(l["words"]) - 4)))
    for i, l in enumerate(lines):
        r = line_sims(l["text"], skip=lambda m, l=l: m is l or _same_line(l, m))
        b = band(r["n"])
        by_band[b]["ngram"].append(r["ngram"]); by_band[b]["edit"].append(r["edit"])
    cal = {"_doc": "Westwood against Westwood (review/storylab/originality.py): per length band of words, the "
                   "percentiles of each distinct line's closest *other* campaign line; quests: each Westwood quest "
                   "against its nearest other one.",
           "bands": {}, "lines": len(lines), "lines_sharing_a_5word_run_with_another_line (Westwood's stock phrases)": copies}
    for b, d in sorted(by_band.items()):
        lo, hi = BANDS[b]
        cal["bands"][str(b)] = dict(words=f"{lo}-{hi if hi < 10 ** 6 else ''}", n=len(d["ngram"]),
                                    **{f"{m}_p{q}": round(_pct(d[m], q / 100), 3) for m in ("ngram", "edit")
                                       for q in (50, 90, 95, 99)})
    qs = ww_quests()
    qv = []
    for u in qs:
        best = 0.0
        for v in qs:
            if v is u or v["keys"] & u["keys"]: continue
            if difflib.SequenceMatcher(None, u["parts"].get("offer", ""), v["parts"].get("offer", "")).ratio() > 0.6: continue
            best = max(best, quest_sim(u["parts"], v)[0])
        qv.append(best)
    cal["quests"] = dict(n=len(qs), **{f"p{q}": round(_pct(qv, q / 100), 3) for q in (50, 90, 95, 99)},
                         max=round(max(qv), 3))
    json.dump(cal, open(CAL, "w", encoding="utf-8"), indent=1)
    return cal


_CALD = None


def cal():
    global _CALD
    if _CALD is None:
        if not os.path.exists(CAL): calibrate()
        _CALD = json.load(open(CAL, encoding="utf-8"))
    return _CALD


def judge_line(text):
    """line_sims plus the flags against Westwood's own thresholds."""
    r = line_sims(text)
    c = cal()["bands"][str(band(r["n"]))]
    fl = []
    if r["ngram"] > c["ngram_p95"]: fl.append(f"3-grams {r['ngram']:.2f} of {r['ngram_key']} (Westwood p95 {c['ngram_p95']:.2f})")
    if r["edit"] > c["edit_p95"]: fl.append(f"edit {r['edit']:.2f} to {r['edit_key']} (Westwood p95 {c['edit_p95']:.2f})")
    for ph, k in r["copied"][:2]: fl.append(f"copies \"{ph}\" ({k})")
    r["flags"] = fl
    r["band"] = band(r["n"])
    return r


def judge_quest(parts):
    s, uid, det = nearest_quest(parts)
    q = cal()["quests"]
    return dict(sim=s, nearest=uid, detail=det, flag=s > q["p99"], above95=s > q["p95"], threshold=q["p99"])


def summarise(line_results, quest_results=()):
    """{lines, median ngram/edit and Westwood's, flagged share, copies, quests flagged, pass}."""
    C = cal()["bands"]
    L = list(line_results)
    if not L: return dict(lines=0, ok=True)
    med = lambda xs: statistics.median(xs) if xs else 0.0
    # Westwood's medians weighted by our band mix
    bands = collections.Counter(r["band"] for r in L)
    ww_ng = sum(C[str(b)]["ngram_p50"] * k for b, k in bands.items()) / len(L)
    ww_ed = sum(C[str(b)]["edit_p50"] * k for b, k in bands.items()) / len(L)
    flagged = sum(1 for r in L if any(not f.startswith("copies") for f in r["flags"])) / len(L)
    copies = sum(1 for r in L if r["copied"])
    QR = list(quest_results)
    qf = [q for q in QR if q["flag"]]
    q95 = sum(1 for q in QR if q["above95"]) / len(QR) if QR else 0.0
    # band-relative medians: our line's value over Westwood's p50 for its band (1.0 = as close as Westwood to itself)
    rel_ng = med([r["ngram"] / max(1e-6, C[str(r["band"])]["ngram_p50"]) for r in L])
    rel_ed = med([r["edit"] / max(1e-6, C[str(r["band"])]["edit_p50"]) for r in L])
    ok = rel_ng <= 1.0 and rel_ed <= 1.0 and flagged <= 0.10 and copies == 0 and not qf and (len(QR) < 10 or q95 <= 0.10)
    return dict(lines=len(L), ngram_med=med([r["ngram"] for r in L]), ngram_ww=ww_ng, edit_med=med([r["edit"] for r in L]),
                edit_ww=ww_ed, rel_ngram=rel_ng, rel_edit=rel_ed, flagged=flagged, copies=copies,
                quests=len(QR), quests_flagged=len(qf), quests_above95=q95, ok=ok)


def report(summary):
    s = summary
    if not s.get("lines"): return "originality: no lines"
    return (f"originality {'PASS' if s['ok'] else 'FAIL'}: {s['lines']} lines; closest Westwood line, median 3-gram "
            f"share {s['ngram_med']:.2f} (Westwood to itself {s['ngram_ww']:.2f}), edit similarity {s['edit_med']:.2f} "
            f"({s['edit_ww']:.2f}); relative to Westwood's median for the length {s['rel_ngram']:.2f} / {s['rel_edit']:.2f} "
            f"(at most 1.00); above Westwood's p95 {s['flagged']:.0%} (at most 10%); lines with a copied 5-word run "
            f"{s['copies']} (none); quests whose skeleton follows one Westwood quest closer than Westwood's p99 "
            f"{s['quests_flagged']} of {s['quests']} (none), above its p95 {s['quests_above95']:.0%}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "calibrate":
        import time
        t0 = time.time()
        print(json.dumps(calibrate(), indent=1))
        print(f"{time.time() - t0:.0f}s")
    else:
        print(__doc__)
