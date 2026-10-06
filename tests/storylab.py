"""The story lab: dialogue and quests written for a situation, scored against Westwood's campaign, side by side.

The loop (review/storylab/README.md):
  1. brief: the scenarios (review/storylab/scenarios.json: a guard's barks, a bounty, an heirloom fetched, rumours,
     shop greetings, two givers, a rescue, the main quest's opening) on one template map, Brackenford.
  2. variants: an agent writes 10 variants of each scenario by the style guide (rules/DIALOGUE.md, rules/QUESTS.md)
     into review/storylab/variants/<iter>/<scenario>.json. The variants are written by an LLM agent and stored as
     data, as a map's story is: the lab improves the guide, the quest patterns and the QuestBook helpers that agents
     use, not a text generator.
  3. judges: the metric judge (review/storylab/metrics.py) scores every variant against Westwood's measured lines;
     the blind judge (review/storylab/JUDGE.md) gets 5 of ours and 5 of Westwood's, shuffled and masked, guesses
     which are ours and scores each; its JSON goes to review/storylab/judgements/<iter>/<scenario>.json.
  4. the scorecard: review/out/storylab/<scenario>/<iter>/scorecard.md (and SUMMARY.md across iterations).

    py tests/storylab.py list                              the scenarios
    py tests/storylab.py brief --iter NAME [--baseline]    the writer's brief for every scenario
    py tests/storylab.py <scenario|all> --iter NAME [--n 10]   judge the variants, write the packet and scorecard
    py tests/storylab.py summary                           every scenario and iteration in one table
    py tests/storylab.py westwood                          Westwood's measures, and its own units scored
    py tests/storylab.py --check <design.py>               a map design's story scored line by line
"""
import argparse, ast, collections, hashlib, json, os, random, re, statistics, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = os.path.join(REPO, "review", "storylab")
OUT = os.path.join(REPO, "review", "out", "storylab")
sys.path.insert(0, LAB)
import metrics, westwood  # noqa: E402

LETTERS = "ABCDEFGHIJ"


def scenarios():
    d = json.load(open(os.path.join(LAB, "scenarios.json"), encoding="utf-8"))
    return d["world"], {s["id"]: s for s in d["scenarios"]}


def _seed(*parts):
    return int(hashlib.sha1("|".join(parts).encode()).hexdigest()[:8], 16)


def _ww_text(k):
    S = westwood.strings()
    return "\n\n".join(S[x] for x in (k if isinstance(k, list) else [k]))


def ww_units(sc):
    """Westwood's units for a scenario: [{"parts": {part: text}, "keys": {part: key}}]."""
    out = []
    for u in sc["westwood"]:
        out.append(dict(parts={p: _ww_text(k) for p, k in u}, keys={p: k for p, k in u}))
    return out


def variants_of(it, sid):
    p = os.path.join(LAB, "variants", it, f"{sid}.json")
    if not os.path.exists(p): return None
    return json.load(open(p, encoding="utf-8"))


def judgement_of(it, sid):
    p = os.path.join(LAB, "judgements", it, f"{sid}.json")
    if not os.path.exists(p): return None
    return json.load(open(p, encoding="utf-8"))


def ctx_for(world, sc, v=None):
    names = dict(world["names"])
    if v: names.update(v.get("names") or {})
    rw = sc.get("reward") or {}
    return dict(names=names, budget=rw.get("budget", 10 ** 9), items=rw.get("items"), reward=(v or {}).get("reward"),
                needs_journal=any(s == "journal" for _, s, _ in sc["parts"]))


def unit_parts(sc, parts, speakers=None):
    sit = {p: s for p, s, _ in sc["parts"]}
    return [dict(part=p, situation=sit.get(p, p), speaker=(speakers or {}).get(p, ""), text=t) for p, t in parts.items()]


def judge_variant(world, sc, v):
    parts = {p: (x["text"] if isinstance(x, dict) else x) for p, x in v["parts"].items()}
    speakers = {p: (x.get("speaker", "") if isinstance(x, dict) else "") for p, x in v["parts"].items()}
    missing = [p for p, _, _ in sc["parts"] if p not in parts]
    r = metrics.judge_unit(unit_parts(sc, parts, speakers), ctx_for(world, sc, v))
    if missing:
        r["score"] = max(0.0, r["score"] - 1.0 * len(missing)); r["flags"].append(f"-{len(missing)}.0 missing parts: {missing}")
    return r


def judge_ww(sc, u):
    return metrics.judge_unit(unit_parts(sc, u["parts"]), dict(names=None))


# ---- the blind packet -----------------------------------------------------------------------------------------------

def packet(world, sc, it, vs, n_each=5):
    """The 10 texts (5 ours, 5 Westwood's), shuffled, masked; returns (markdown, key)."""
    rng = random.Random(_seed(sc["id"], it))
    pp = sc["packet_parts"]
    ours = [v for v in vs if all(p in v["parts"] for p in pp)]
    ours = rng.sample(ours, min(n_each, len(ours)))
    ww = [u for u in ww_units(sc) if all(p in u["parts"] for p in pp)]
    ww = rng.sample(ww, min(n_each, len(ww)))
    items = [("generated", v.get("id"), {p: (v["parts"][p]["text"] if isinstance(v["parts"][p], dict) else v["parts"][p]) for p in pp},
              dict(world["names"], **(v.get("names") or {}))) for v in ours]
    items += [("westwood", "|".join(str(u["keys"][p]) for p in pp), {p: u["parts"][p] for p in pp}, {}) for u in ww]
    rng.shuffle(items)
    md = [f"# Blind packet: {sc['title']} ({it})", "",
          "Ten texts of one kind, each the lines of one quest or one place in a Nox single-player map. Some are from "
          "Westwood's Nox campaign, some were written for new maps. Names are masked: [Person], [Place], [Thing], "
          "[Group], [Class]. Judge by JUDGE.md (review/storylab/JUDGE.md) and answer in its JSON.", ""]
    key = {}
    for L, (src, ref, parts, names) in zip(LETTERS, items):
        key[L] = dict(source=src, ref=ref)
        md += [f"## Text {L}", ""]
        for p in pp:
            t = metrics.mask(parts[p], {k: v for k, v in names.items() if k[:1].isupper()})
            md.append(f"**{sc['labels'].get(p, p)}:** " + t.replace("\n\n", " / ").replace("\n", " / "))
            md.append("")
    return "\n".join(md), key


# ---- the scorecard --------------------------------------------------------------------------------------------------

def blind_results(key, jd):
    if not jd: return None
    items = {i["label"]: i for i in jd["items"]}
    correct = sum(1 for L, k in key.items() if L in items and items[L]["verdict"] == k["source"])
    gen = [L for L, k in key.items() if k["source"] == "generated"]
    ww = [L for L, k in key.items() if k["source"] == "westwood"]
    sc = lambda Ls: statistics.mean(items[L]["score"] for L in Ls if L in items) if Ls else 0
    return dict(accuracy=correct / max(1, len(key)), detected=sum(1 for L in gen if items.get(L, {}).get("verdict") == "generated") / max(1, len(gen)),
                score_gen=sc(gen), score_ww=sc(ww), items=items, tells=jd.get("tells", []))


def run(world, sc, it, n):
    vd = variants_of(it, sc["id"])
    if not vd:
        print(f"{sc['id']}: no variants for {it} (review/storylab/variants/{it}/{sc['id']}.json)"); return None
    vs = vd["variants"][:n]
    res = [(v, judge_variant(world, sc, v)) for v in vs]
    wres = [(u, judge_ww(sc, u)) for u in ww_units(sc)]
    md_packet, key = packet(world, sc, it, vs)
    d = os.path.join(OUT, sc["id"], it); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "packet.md"), "w", encoding="utf-8").write(md_packet)
    kd = os.path.join(OUT, "_keys", it); os.makedirs(kd, exist_ok=True)
    json.dump(key, open(os.path.join(kd, f"{sc['id']}.json"), "w", encoding="utf-8"), indent=1)
    br = blind_results(key, judgement_of(it, sc["id"]))
    m_gen = statistics.mean(r["score"] for _, r in res)
    m_ww = statistics.mean(r["score"] for _, r in wres)
    # the scorecard
    L = [f"# {sc['title']}: {it}", "", f"Writer: {vd.get('writer', '?')}; guide: {vd.get('guide', '?')}", "",
         f"**Metric judge:** ours {m_gen:.2f} / 10 (n={len(res)}), Westwood's units {m_ww:.2f} (n={len(wres)}).", ""]
    if br:
        L += [f"**Blind judge:** accuracy {br['accuracy']:.0%} (chance 50%), ours detected {br['detected']:.0%}; "
              f"score ours {br['score_gen']:.1f}, Westwood {br['score_ww']:.1f}.", ""]
    else:
        L += ["**Blind judge:** not yet judged (review/storylab/judgements/%s/%s.json)." % (it, sc["id"]), ""]
    L += ["## Variants (metric judge)", "", "| # | score | specifics | flags |", "|---|---|---|---|"]
    for v, r in res:
        fl = r["flags"] + [f"{l['part']}: {f}" for l in r["lines"] for f in l["flags"]]
        L.append(f"| {v.get('id')} | {r['score']:.1f} | {v.get('specifics', '')[:60]} | {'; '.join(fl)[:400]} |")
    L += ["", "## Westwood's units (metric judge, for calibration)", "", "| unit | score | flags |", "|---|---|---|"]
    for u, r in wres:
        fl = [f"{l['part']}: {f}" for l in r["lines"] for f in l["flags"]]
        L.append(f"| {list(u['keys'].values())[0]} | {r['score']:.1f} | {'; '.join(fl)[:300]} |")
    if br:
        L += ["", "## Blind judge, item by item", "", "| text | source | guess | score | critique |", "|---|---|---|---|---|"]
        for Lt, k in sorted(key.items()):
            i = br["items"].get(Lt, {})
            ok = "ok" if i.get("verdict") == k["source"] else "WRONG"
            L.append(f"| {Lt} | {k['source']} {k['ref']} | {i.get('verdict')} ({i.get('confidence')}) {ok} | {i.get('score')} | {i.get('critique', '')} |")
        if br["tells"]: L += ["", "Tells: " + " ".join(f"- {t}" for t in br["tells"])]
    L += ["", "## The variants", ""]
    for v, r in res:
        L.append(f"### {v.get('id')}: {v.get('specifics', '')} ({r['score']:.1f})")
        for p, x in v["parts"].items():
            t = x["text"] if isinstance(x, dict) else x
            L.append(f"- **{p}** ({x.get('speaker', '') if isinstance(x, dict) else ''}): {t}")
        if v.get("reward"): L.append(f"- reward: {v['reward']}")
        L.append("")
    open(os.path.join(d, "scorecard.md"), "w", encoding="utf-8").write("\n".join(L))
    row = dict(scenario=sc["id"], iter=it, metric_gen=m_gen, metric_ww=m_ww,
               accuracy=br["accuracy"] if br else None, detected=br["detected"] if br else None,
               blind_gen=br["score_gen"] if br else None, blind_ww=br["score_ww"] if br else None)
    acc = f"blind acc {br['accuracy']:.0%}, scores {br['score_gen']:.1f} vs {br['score_ww']:.1f}" if br else "not judged"
    print(f"{sc['id']:15s} {it:10s} metric {m_gen:.2f} (Westwood {m_ww:.2f}); {acc}  -> {os.path.relpath(d, REPO)}")
    return row


def summary():
    world, S = scenarios()
    vdir = os.path.join(LAB, "variants")
    its = sorted(os.listdir(vdir)) if os.path.isdir(vdir) else []
    rows = []
    for it in its:
        for sid, sc in S.items():
            if variants_of(it, sid):
                import io, contextlib
                with contextlib.redirect_stdout(io.StringIO()):
                    r = run(world, sc, it, 10)
                if r: rows.append(r)
    f = lambda x, p="{:.2f}": "-" if x is None else p.format(x)
    L = ["# Story lab: every scenario and iteration", "",
         "metric: the metric judge's mean (0-10) for our 10 variants and for Westwood's units; blind: the blind "
         "judge's accuracy telling ours from Westwood's (chance 50%), the share of ours it caught, and its 1-10 "
         "scores for ours and Westwood's.", "",
         "| scenario | iter | metric ours | metric WW | blind acc | ours caught | blind ours | blind WW |",
         "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['scenario']} | {r['iter']} | {f(r['metric_gen'])} | {f(r['metric_ww'])} | {f(r['accuracy'], '{:.0%}')} | "
                 f"{f(r['detected'], '{:.0%}')} | {f(r['blind_gen'], '{:.1f}')} | {f(r['blind_ww'], '{:.1f}')} |")
    by = collections.defaultdict(list)
    for r in rows: by[r["iter"]].append(r)
    L += ["", "| iter | metric ours | blind acc | blind ours | blind WW |", "|---|---|---|---|---|"]
    for it, rs in by.items():
        j = [r for r in rs if r["accuracy"] is not None]
        L.append(f"| {it} | {statistics.mean(r['metric_gen'] for r in rs):.2f} | "
                 + (f"{statistics.mean(r['accuracy'] for r in j):.0%} | {statistics.mean(r['blind_gen'] for r in j):.1f} | "
                    f"{statistics.mean(r['blind_ww'] for r in j):.1f} |" if j else "- | - | - |"))
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "SUMMARY.md"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))


# ---- the writer's brief ---------------------------------------------------------------------------------------------

def brief(it, baseline=False):
    world, S = scenarios()
    L = [f"# Story lab brief: {it}", "",
         "You write dialogue and quest text for Nox single-player maps (OpenNox). For each scenario below write 10 "
         "variants, as JSON, to `review/storylab/variants/%s/<scenario id>.json` in the worktree." % it, ""]
    if baseline:
        L += ["Write the way the map-building agents write today: read `skills/nox-story-map/SKILL.md` (section 1, "
              "'Write the story first') and the story of `mapgen/designs/starwell.py` (its q.say, q.journal, RUMOURS "
              "and GREET text) as the house style. Do not read rules/DIALOGUE.md, the game's string table (nox.csf) or "
              "anything under review/storylab/: this brief has all you need.", ""]
    else:
        L += ["Follow the style guide `rules/DIALOGUE.md` and the quest patterns in `rules/QUESTS.md` closely. Do "
              "not read the game's string table (nox.csf) or anything under review/storylab/ (this brief has all you "
              "need): write new lines; lines copied from the campaign are penalised.", ""]
    L += ["## The map", "", world["summary"], "",
          "Names already on the map: " + ", ".join(f"{k} ({v})" for k, v in world["names"].items()), "",
          "## The variants", "",
          "Variant 1 takes the scenario as written. Variants 2-10 each change its specifics (who asks, which beast, "
          "item, captive or place, and why) within Brackenford's world and the same kind of situation, so that no two "
          "read alike. Every person, place or named thing a variant mentions that is not on the map's list goes in "
          "the variant's `names` ({name: person|place|thing|group}). Rewards: gold within the scenario's budget, items "
          "only from its list.", "",
          "```json", json.dumps({"scenario": "<id>", "iter": it, "writer": "<who wrote it>", "guide": "<the guide you followed>",
                                 "variants": [{"id": 1, "specifics": "<one line: who, what, where>",
                                               "names": {"<New Name>": "person"},
                                               "parts": {"<part>": {"speaker": "<name>", "text": "<the line>"}},
                                               "reward": {"gold": 0, "items": []}}]}, indent=1), "```", "",
          "Text is plain: a page break inside a long speech is a blank line (\"\\n\\n\"). A journal entry's speaker is "
          "\"\".", ""]
    for sid, sc in S.items():
        L += [f"## {sid}: {sc['title']}", "", sc["situation"], "",
              "Parts: " + "; ".join(f"`{p}` ({s}{', ' + who if who else ''})" for p, s, who in sc["parts"])]
        if sc.get("reward"):
            L.append(f"Reward: at most {sc['reward']['budget']} gold; items from {sc['reward']['items']}.")
        L.append("")
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"brief_{it}.md")
    open(p, "w", encoding="utf-8").write("\n".join(L))
    print(f"wrote {os.path.relpath(p, REPO)}")


# ---- Westwood -------------------------------------------------------------------------------------------------------

def show_westwood():
    st = metrics.ww_stats()
    print("Westwood's campaign lines by situation (distinct lines): words p10/p50/p90, words a sentence p50, share "
          "exclaiming, asking, addressing, naming, directing; contractions a word; semicolons a line")
    for s in ("offer", "reminder", "completion", "after", "refusal", "townsfolk", "guard", "shop", "journal", "foe",
              "talk", "dialogue"):
        d = st[s]
        print(f"  {s:10s} n={d['n']:3d} words {d['words']['p10']:.0f}/{d['words']['p50']:.0f}/{d['words']['p90']:.0f} "
              f"wps {d['wps']['p50']:.1f}  ! {d['excl']['mean']:.0%} ? {d['quest']['mean']:.0%} addr {d['address']['mean']:.0%} "
              f"names {d['names']['mean']:.1f} dir {d['direction']['mean']:.0%} contr {d['contractions']['mean']:.3f} "
              f"; {d['semicolons']['mean']:.3f} -- {d['dash']['mean']:.2f} ... {d['ellipsis']['mean']:.2f}")
    world, S = scenarios()
    print("\nWestwood's own units under the metric judge (calibration):")
    allr = []
    for sid, sc in S.items():
        rs = [judge_ww(sc, u)["score"] for u in ww_units(sc)]
        allr += rs
        print(f"  {sid:15s} {statistics.mean(rs):.2f}  (min {min(rs):.1f})")
    print(f"  all             {statistics.mean(allr):.2f}")


# ---- a design's story -----------------------------------------------------------------------------------------------

def _strval(node):
    """The text of a string expression: a constant, implicit or + concatenation, an f-string with its holes as 'X'."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str): return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "X" for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _strval(node.left), _strval(node.right)
        if a is not None and b is not None: return a + b
    return None


def _callname(n):
    f = n.func
    if isinstance(f, ast.Attribute):
        base = f.value.id if isinstance(f.value, ast.Name) else (f.value.attr if isinstance(f.value, ast.Attribute) else "")
        return f"{base}.{f.attr}"
    return f.id if isinstance(f, ast.Name) else ""


def _kw(n, name):
    for k in n.keywords:
        if k.arg == name: return k.value
    return None


def extract_design(path):
    """[{"kind": say|journal|text|rumour, "talker", "text", "role", "line"}] from a design's source."""
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    out = []
    parent_talker = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _callname(n).endswith(".talker") and n.args:
            nm = _strval(n.args[0]) or "?"
            for c in ast.walk(n):
                if isinstance(c, ast.Call) and _callname(c).endswith(".say"): parent_talker[id(c)] = nm
    order = collections.Counter()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call): continue
        cn = _callname(n)
        if cn.endswith(".say") and n.args:
            t = _strval(n.args[0])
            if t is None: continue
            talker = parent_talker.get(id(n), "?")
            order[talker] += 1
            ask = _kw(n, "ask"); when = _kw(n, "when"); do = _kw(n, "do")
            dsrc = ast.unparse(do) if do is not None else ""
            wsrc = ast.unparse(when) if when is not None else ""
            if ask is not None and getattr(ask, "value", False): role = "offer"
            elif re.search(r"A\.(gold|give)\(", dsrc) or re.search(r"COMPLETED", dsrc): role = "completion"
            elif re.search(r"journal\(", dsrc) and re.search(r"A\.stage\([^)]*,\s*1\)|A\.flag", dsrc): role = "offer"
            elif re.search(r"_paid|_done|flag=", wsrc): role = "after"
            elif re.search(r"q\.at\(", wsrc): role = "reminder"
            elif re.search(r"Guard|Watch|Gate|Warden", talker): role = "guard"
            else: role = "talk"
            out.append(dict(kind="say", talker=talker, text=t, role=role, line=n.lineno, n=order[talker]))
        elif cn.endswith(".errand"):
            names = ["giver", "quest", "offer", "reminder", "thanks", "after", "objective", "done", "reward", "refusal", "again"]
            args = {names[i]: a for i, a in enumerate(n.args) if i < len(names)}
            args.update({k.arg: k.value for k in n.keywords if k.arg})
            giver = _strval(args["giver"]) if "giver" in args else "?"
            for k, role in (("offer", "offer"), ("again", "offer"), ("refusal", "refusal"), ("reminder", "reminder"),
                            ("thanks", "completion"), ("after", "after")):
                t = _strval(args[k]) if k in args else None
                if t: out.append(dict(kind="say", talker=giver, text=t, role=role, line=n.lineno, n=0))
            t = _strval(args["objective"]) if "objective" in args else None
            if t: out.append(dict(kind="journal", talker="", text=t, role="journal", line=n.lineno, type="QUEST"))
        elif cn.endswith((".done", ".note")) and n.args and _strval(n.args[0]):
            out.append(dict(kind="journal", talker="", text=_strval(n.args[0]), role="journal", line=n.lineno,
                            type="COMPLETED" if cn.endswith(".done") else "NOTE"))
        elif cn.endswith(".journal") and n.args:
            t = _strval(n.args[0])
            if t is not None:
                typ = ast.unparse(n.args[1]) if len(n.args) > 1 else "QUEST"
                out.append(dict(kind="journal", talker="", text=t, role="journal", line=n.lineno, type=typ))
        elif cn.endswith(".text") and n.args:
            t = _strval(n.args[0])
            stem = _strval(n.args[1]) if len(n.args) > 1 else "Line"
            if t is not None:
                role = {"Sign": "sign", "Shop": "shop"}.get(stem, "talk")
                out.append(dict(kind="text", talker=stem, text=t, role=role, line=n.lineno))
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and re.search(r"RUMOU?R", t.id) for t in n.targets):
            if isinstance(n.value, (ast.List, ast.Tuple)):
                for e in n.value.elts:
                    t = _strval(e)
                    if t: out.append(dict(kind="rumour", talker="Folk", text=t, role="rumour", line=e.lineno))
        if isinstance(n, ast.Call) and _callname(n).endswith(".townsfolk"):
            a = _kw(n, "after")
            if isinstance(a, ast.Tuple) and len(a.elts) == 2 and _strval(a.elts[1]):
                out.append(dict(kind="rumour", talker="Folk", text=_strval(a.elts[1]), role="after", line=a.lineno))
    return out, src


def check(design):
    lines, src = extract_design(design)
    if not lines:
        print(f"{design}: no story found (q.say, q.journal, q.text, RUMOURS)"); return 1
    # the map's names: every capitalised word or phrase its strings use; one met in only one line and nowhere else in
    # the source (comments, identity, script names) is flagged
    allnames = collections.Counter()
    for l in lines:
        for _, _, w in metrics.name_spans(l["text"]): allnames[w] += 1
    once = {w for w, c in allnames.items() if c == 1 and len(re.findall(r"\b" + re.escape(w) + r"\b", src)) <= 1}
    by_role = collections.defaultdict(list)
    rows = []
    for l in lines:
        if l["role"] in ("sign",): continue
        r = metrics.judge_line(l["text"], l["role"], set(allnames))
        fl = list(r["flags"])
        nm = [w for _, _, w in metrics.name_spans(l["text"]) if w in once]
        if nm: fl.append(f"named once in the whole design: {', '.join(nm)} (is it on the map?)")
        if l["kind"] == "journal" and l.get("type") == "COMPLETED" and r["features"]["first_person"]:
            fl.append("a completed entry in the first person: Westwood greys the objective itself")
        rows.append((l, r, fl))
        by_role[r["features"]["situation"]].append(r["score"])
    name = os.path.splitext(os.path.basename(design))[0]
    L = [f"# Story check: {name}", "",
         f"{len(rows)} lines scored against Westwood's campaign (0-10 each; review/storylab/metrics.py).", "",
         "| situation | lines | mean score |", "|---|---|---|"]
    for s, xs in sorted(by_role.items()):
        L.append(f"| {s} | {len(xs)} | {statistics.mean(xs):.1f} |")
    allx = [r["score"] for _, r, _ in rows]
    vs, vflags = metrics.voice([r["features"] for _, r, _ in rows])
    overall = 0.75 * statistics.mean(allx) + 0.25 * vs
    L += ["", f"**Overall: {overall:.2f} / 10**: lines {statistics.mean(allx):.2f} (0.75), voice {vs:.1f} (0.25); "
          f"{sum(1 for x in allx if x >= 7)} of {len(allx)} lines at 7 or more", ""] + [f"- {f}" for f in vflags] + [""]
    # map-level measures
    sem = sum(l["text"].count(";") for l in lines if l["role"] not in ("sign",))
    j = [l for l in lines if l["kind"] == "journal"]
    j1 = [l for l in j if re.search(r"\bI\b|\bmy\b|\bme\b", l["text"])]
    talk = [r for l, r, _ in rows if r["features"]["situation"] not in ("journal",)]
    ex = sum(r["features"]["excl"] for r in talk) / max(1, len(talk))
    ad = sum(r["features"]["address"] for r in talk) / max(1, len(talk))
    st = metrics.ww_stats()["dialogue"]
    per_talker = collections.Counter(l["talker"] for l in lines if l["kind"] == "say")
    L += ["## The story as a whole", "",
          f"- semicolons: {sem} (Westwood's 854 dialogue lines have {st['semicolons']['mean'] * st['n']:.0f})",
          f"- journal entries: {len(j)}, in the first person: {len(j1)} (Westwood: objectives, 'Retrieve the ...', never 'I')",
          f"- lines that exclaim: {ex:.0%} (Westwood {st['excl']['mean']:.0%}); that address the player: {ad:.0%} (Westwood {st['address']['mean']:.0%})",
          f"- lines per talker: " + ", ".join(f"{k} {v}" for k, v in per_talker.most_common()), ""]
    L += ["## Lines below 7", "", "| line | situation | score | text | flags |", "|---|---|---|---|---|"]
    for l, r, fl in sorted(rows, key=lambda x: x[1]["score"]):
        if r["score"] >= 7 and not any("named once" in f for f in fl): continue
        L.append(f"| {l['line']} | {l['role']}/{l['talker']} | {r['score']:.1f} | {l['text'][:140]} | {'; '.join(fl)} |")
    d = os.path.join(OUT, "check"); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{name}.md")
    open(p, "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L[:L.index("## Lines below 7")]))
    print(f"wrote {os.path.relpath(p, REPO)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", nargs="?", default="list")
    ap.add_argument("--iter", default="i0")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--check", metavar="DESIGN")
    a = ap.parse_args()
    if a.check: sys.exit(check(a.check))
    world, S = scenarios()
    if a.what == "list":
        for sid, sc in S.items(): print(f"{sid:15s} {sc['title']}  ({len(sc['westwood'])} Westwood units)")
    elif a.what == "brief": brief(a.iter, a.baseline)
    elif a.what == "summary": summary()
    elif a.what == "westwood": show_westwood()
    elif a.what == "all":
        for sc in S.values(): run(world, sc, a.iter, a.n)
    elif a.what in S: run(world, S[a.what], a.iter, a.n)
    else: sys.exit(f"unknown scenario {a.what}: {', '.join(S)}")


if __name__ == "__main__":
    main()
