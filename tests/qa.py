"""The QA gate: everything a map must pass before the user sees it, in one command.

    py tests/qa.py <design> [seed] [--no-render] [--no-build] [--go path\\to\\go.exe]

    <design>     a design in mapgen/designs (starwell, ambermere, ...) or its path
    seed         passed to the design (py mapgen/designs/<design>.py <seed>)
    --no-build   use the map already in mapgen/out/<design>/ (the checker runs again)
    --no-render  skip the pictures (a quick re-check while fixing)
    --go         a Go compiler for the scripts' compile check (else $GO, then the known portable installs)

Steps (each prints PASS, FAIL or LOOK):
  1. build       the design builds (one at a time: never run two builds at once)
  2. checker     validate/checks.py: 0 errors; every warning is listed with its rule and whether the design accepts it
                 (QA_ACCEPT in the design: [("<rule or check>", "<regex on the message>", "<why>"), ...]); a warning the
                 design does not accept fails the gate. The rules cover routes and facing, the exterior, thresholds,
                 room identity, the minimap and the rest (validate/README.md; review/FEEDBACK.md says which feedback
                 each answers)
  3. scripts     the map's Go scripts compile against the game's NoxScript (tests/check_scripts.py)
  4. story       every talker has its dialogue title (NPC:<name>), string keys fit (31 characters), a gift is picked up
                 on a timer (never at once), the exit leads to a map that is built, every chest holds loot and the gold
                 stays in Westwood's budget, no Zombie, the map's name fits (9 characters)
     voice       every line said in a dialogue window (talkers' lines, told refusals, shop greetings) has its wave, made
                 from its present text, PCM 16-bit mono, neither silent nor clipped, at a speaking pace, 8-character
                 names, and (Breeze) passed the quality gate: Whisper's transcript, the part's pitch, the pace
                 (mapgen/voice.py check); a talker's refusal said over its head (A.chat) is a LOOK: it stays silent
  5. rooms       review/roomscore.py: rooms that miss their score are listed to LOOK at (the pictures show them)
  6. exterior    review/exteriors.py: the share of the open ground with no prop within 4 cells against Westwood's maps of
                 the map's environment (review/exteriors_baseline.json): over their 90th percentile fails, over the 75th
                 is a LOOK
     sight       tests/sightrows.py: no point of the floor from which a screen row crosses the edge of the player's sight
                 often enough to crash the OpenNox client (a long level forest edge in view; CL-1); a risk is a LOOK
  7. pictures    review/out/<Name>/qa/: the story map, the routes, close-ups of every named story place, every room,
                 the empty ground; index.md and index.html walk the reviewer through them, each with what to look for

It never installs the map nor starts the game or the server. After it passes, the main session installs the map
(mapgen/install.py) and runs the server smoke test (tests/server_smoke.py): the user may be playing on this PC.
Exit code 0 when every step passes (LOOK items are for the reviewer, not failures), 1 otherwise.
"""
import argparse, ast, collections, glob, html, json, os, re, shutil, subprocess, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "validate")); sys.path.insert(0, os.path.join(REPO, "review"))
sys.path.insert(0, os.path.join(REPO, "mapgen")); sys.path.insert(0, os.path.join(REPO, "rules"))
GO_CANDIDATES = [
    os.environ.get("GO", ""),
    r"C:/Users/DYSTOP~1/AppData/Local/Temp/claude/C--GOG-Games-Nox/2ef10e66-3ba1-4500-9040-634cb857884d/scratchpad/tools/go/bin/go.exe",
    os.path.join(REPO, ".tools", "go", "bin", "go.exe"),
]
GOLD_MAX = 1500        # a map's gold: Westwood's median about 500, at most 2,570 (rules/QUESTS.md); kit/loot.py keeps 1500

# What only an eye can judge, by picture (review/FEEDBACK.md "Review only").
LOOK = {
    "storymap": ("The story map", [
        "every story place the docstring names is there and reachable along roads or paths",
        "camps stand in their own clearing off the road, with room round them (AMR-1)",
        "the gate seals the way out; the exit lies beyond it"]),
    "routes": ("The routes people walk", [
        "every route follows the roads and paths, never cutting across grass, trees or buildings (GW-1, TW-9)",
        "no red legs and no red facing arrows; stops are spread, none shared (GW-6)",
        "arrows at doorsteps point away from the building; at a feature, toward it (SW-2)",
        "doorways are passed square-on through their middle (TW-1)"]),
    "spots": ("The story places, close up", [
        "a camp is laid in zones: the hearth (fire, ring of stones, log benches or stools, never stumps), the sleeping "
        "row behind it, the store on one flank, the racks or the dig on the other, the lookout at the way in (GW-4, SW-1, "
        "SW-3); its men at their posts, at most two at the fire, never a swarm (GW-5)",
        "outdoor groups are scenes with a purpose: a cart with barrels and a crate, a rack, a box; never a heap of crates "
        "and barrels, never a lone block by a wall's corner (GW-2)",
        "graveyards have graves in rows on dug earth, the gravedigger's corner, flowers (SW-9)",
        "a dock runs out square from the bank into open water (AM-2, DV4-1); crops stand inside their fence (AM-1)",
        "a person waiting at a door stands beside the doorstep, off the way in (AMR-7)"]),
    "rooms": ("Every room", [
        "each room reads as its purpose at a glance, like the reference room (Starwell's study, SW-7): every wall with a "
        "purpose, one group in the middle that shows the use, one theme, full but balanced (SW-6)",
        "a showpiece (telescope, generator, alchemist's desk, desk) stands once; only bookcases, shelves of goods and "
        "workstations line a wall (SWR-1)",
        "a shop's keeper stands behind his counter, the racks in rows of three, mixed kinds (SWR-2)",
        "a throne faces its door down a clear aisle; columns in a few pairs, never a row down the middle; statues face in "
        "(GW-7, SW-6); a chapel's altar faces the main door (AMR-3)",
        "big rooms mix their pieces: no hall of pews or tables wall to wall (TW-8); no barrels along a whole wall outside "
        "a store (AMR-4)",
        "inside each door the room's own floor runs to the threshold, with no grass or dirt on the boards (SW-4)",
        "facing pieces on the NE and NW walls, free pieces toward the front (TP3-a); nothing before a chest or hearth"]),
    "empty": ("The empty ground", [
        "red is open ground with no prop within 4 cells, dark red within 6: no long empty alleys or yards (TW-10)",
        "the dressing is scenes with a purpose, not scattered single props (GW-2)"]),
    "ingame": ("After install, in the game (the main session)", [
        "a talk that gives an item, a fight with archers and the player's death do not freeze the game (TW-2, TW-3, "
        "TW-4, TW-11)",
        "the minimap shows the walls (TW-5, GW-3); dialogue windows show each speaker's name (TW-6)",
        "people turn to the player and back, and never stare at a wall (SW-2); nobody sticks in a door frame (TW-1)",
        "lights and mood: the story's lights (ward rings, shrines) read lit and dark as the story says"]),
}


def find_go(arg):
    for c in [arg] + GO_CANDIDATES:
        if c and os.path.exists(c): return c
    return shutil.which("go")


def design_path(d):
    if os.path.exists(d): return os.path.abspath(d)
    p = os.path.join(REPO, "mapgen", "designs", d + ".py")
    if not os.path.exists(p): sys.exit(f"no design {d}")
    return p


def accepted(design):
    """The design's QA_ACCEPT: [(rule or check, message regex, why)], read without running the design."""
    tree = ast.parse(open(design, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "QA_ACCEPT" for t in node.targets):
            return [tuple(x) for x in ast.literal_eval(node.value)]
    return []


def acceptance(f, acc):
    for rule, rx, why in acc:
        if (f.get("rule") == rule or f["check"] == rule or (f.get("rule") or "").startswith(rule + ".")) and \
                re.search(rx, f["msg"]):
            return why
    return None


class Gate:
    def __init__(self):
        self.rows = []

    def add(self, step, status, text, details=()):
        self.rows.append((step, status, text, list(details)))
        print(f"[{status:4s}] {step:9s} {text}", flush=True)
        for d in list(details)[:40]: print(f"         - {d}")
        if len(details) > 40: print(f"         - ... and {len(details) - 40} more")

    @property
    def ok(self):
        return all(s != "FAIL" for _, s, _, _ in self.rows)


def run(args, timeout=1800):
    r = subprocess.run([sys.executable] + args, cwd=REPO, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


def story_checks(map_path, name, m):
    """[(ok, text)]: the story's text, gifts, exit, loot (TW-6, TW-7, TW-11) and the engine's limits."""
    out = []
    d = os.path.dirname(map_path)
    sd = os.path.join(d, name + "_scripts")
    strings_p = os.path.join(d, name + ".strings.json")
    strings = json.load(open(strings_p, encoding="utf-8")) if os.path.exists(strings_p) else {}
    src = {fn: open(os.path.join(sd, fn), encoding="utf-8").read() for fn in os.listdir(sd)} if os.path.isdir(sd) else {}
    talkers = sorted({t for s in src.values() for t in re.findall(r'\bTalker\("([^"]+)"', s)})
    untitled = [t for t in talkers if f"NPC:{t}" not in strings]
    out.append((not untitled, f"{len(talkers)} talkers, each with its dialogue title" if not untitled else
                f"talkers with no title (the window shows MISSING:NPC:<name>; QuestBook.talker sets it): {', '.join(untitled)}"))
    long_keys = [k for k in strings if len(k) > 31]
    out.append((not long_keys, f"{len(strings)} strings, keys of 31 characters or less" if not long_keys else
                f"string keys over 31 characters: {', '.join(long_keys[:5])}"))
    bad_pick = []
    for fn, s in src.items():
        lines = s.splitlines()
        for i, l in enumerate(lines):
            if re.search(r"\.Pickup\(", l) and not any("NewTimer" in x for x in lines[max(0, i - 4):i]):
                bad_pick.append(f"{fn}:{i + 1}")
    out.append((not bad_pick, "gifts are picked up on a timer after they are made" if not bad_pick else
                f"Pickup at once after CreateObject freezes the game (TW-11): {', '.join(bad_pick)}"))
    exits = [o for o in m.objects if o["type"] == "InvisibleExitArea"]
    targets = sorted({os.path.splitext(str((o["xfer"] or {}).get("MapName") or (o["xfer"] or {}).get("Map") or ""))[0]
                      for o in exits})
    for target in targets:
        built = glob.glob(os.path.join(REPO, "mapgen", "out", "**", target + ".map"), recursive=True) if target else []
        out.append((bool(built), f"the exit leads to {target}, which is built" if built else
                    f"the exit leads to '{target}', which is not built here (build the next map first)"))
    if not exits: out.append((True, "no exit (a closing map)"))
    loot_p = os.path.join(d, name + ".loot.json")
    if os.path.exists(loot_p):
        lt = json.load(open(loot_p))
        ch = lt.get("families", {}).get("chest", {})
        gold = (lt.get("gold_before") or 0) + (lt.get("gold_added") or 0)
        out.append((ch.get("filled", 0) >= ch.get("n", 0), f"chests: {ch.get('filled', 0)} of {ch.get('n', 0)} hold loot"))
        out.append((gold <= GOLD_MAX, f"gold in the map {gold} (at most {GOLD_MAX})"))
        fam = lt.get("families", {})
        shares = ", ".join(f"{k} {v.get('filled', 0)}/{v.get('n', 0)}" for k, v in sorted(fam.items()) if k != "chest")
        out.append((True, f"other containers filled at Westwood's shares: {shares}"))
    else:
        out.append((False, "no loot tally (<Name>.loot.json): Spec.build fills containers (kit/loot.py)"))
    out.append((not any(o["type"] == "Zombie" for o in m.objects), "no Zombie (OpenNox cannot read a map with one back)"))
    out.append((len(name) <= 9, f"map name {name} ({len(name)} characters, at most 9)"))
    return out


def pictures(map_path, name, m, qa_dir, gate):
    """Render the review pictures into qa_dir; returns {section: [(file, caption)]}."""
    out = collections.defaultdict(list)
    ro = os.path.join(REPO, "review", "out", name)
    t0 = time.time()
    rc, o = run([os.path.join("review", "storymap.py"), map_path, "--out", os.path.join(qa_dir, "storymap.png")])
    if rc == 0: out["storymap"].append(("storymap.png", "the whole map, every named object labelled"))
    if os.path.exists(os.path.splitext(map_path)[0] + ".routes.json"):
        rc, o = run([os.path.join("review", "storymap.py"), map_path, "--routes", "--out", os.path.join(qa_dir, "routes.png")])
        if rc == 0: out["routes"].append(("routes.png", "every route walked, its stops and the way each stop faces"))
    walkers = set()
    rp = os.path.splitext(map_path)[0] + ".routes.json"
    if os.path.exists(rp): walkers = {r.get("who") for r in json.load(open(rp, encoding="utf-8"))}
    names, seen = [], set()
    for o_ in m.objects:
        scr = (o_.get("scr") or "").split(":")[-1]
        if not scr or scr in walkers or o_["type"] in ("PlayerStart",): continue
        stem = re.sub(r"\d+$", "", scr)
        key = stem if re.search(r"\d$", scr) else scr
        if key in seen or re.search(r"Way_\d+$|_\d+$", scr): continue
        seen.add(key); names.append(scr)
    for k in range(0, len(names), 9):
        f = f"spots_{k // 9 + 1}.png"
        rc, o = run([os.path.join("review", "spots.py"), map_path] + names[k:k + 9] + ["--out", os.path.join(qa_dir, f)])
        if rc == 0: out["spots"].append((f, ", ".join(re.sub(r"\d+$", "", n) for n in names[k:k + 9])))
    rc, o = run([os.path.join("review", "rooms.py"), map_path, "--each"], timeout=3600)
    if rc == 0:
        shutil.copy(os.path.join(ro, "rooms.png"), os.path.join(qa_dir, "rooms.png"))
        out["rooms"].append(("rooms.png", "every room on one sheet"))
        rd = os.path.join(qa_dir, "rooms"); os.makedirs(rd, exist_ok=True)
        for p in sorted(glob.glob(os.path.join(ro, "rooms", "*.png"))):
            shutil.copy(p, rd); out["rooms"].append((f"rooms/{os.path.basename(p)}", f"room {os.path.basename(p)[:-4]}"))
    rc, o = run([os.path.join("review", "exteriors.py"), map_path, "--holes", "--out", os.path.join(qa_dir, "empty.png")])
    if rc == 0: out["empty"].append(("empty.png", "open ground with no prop within 4 cells (red) and 6 (dark red)"))
    side = os.path.splitext(map_path)[0] + ".rooms.json"
    has_rooms = os.path.exists(side) and any(not r.get("yard") for r in json.load(open(side, encoding="utf-8")))
    missing = [k for k in ("storymap", "empty") + (("rooms",) if has_rooms else ()) if not out.get(k)]
    gate.add("pictures", "FAIL" if missing else "PASS",
             f"{sum(len(v) for v in out.values())} pictures in {qa_dir} ({time.time() - t0:.0f} s)" +
             (f"; not rendered: {', '.join(missing)}" if missing else ""))
    return out


def write_index(qa_dir, name, gate, pics, room_rows):
    md_ = [f"# QA: {name}", "", f"Gate: **{'PASS' if gate.ok else 'FAIL'}**", "", "| Step | Result | |", "|---|---|---|"]
    for step, st, text, _ in gate.rows: md_.append(f"| {step} | {st} | {text} |")
    md_ += ["", "Walk through the pictures in order; under each, what to look for (review/FEEDBACK.md).", ""]
    h = [f"<!doctype html><meta charset='utf-8'><title>QA {html.escape(name)}</title><style>body{{background:#111;"
         f"color:#ddd;font:15px sans-serif;margin:16px}} img{{max-width:100%}} li{{margin:3px 0}} .FAIL{{color:#f66}}"
         f" .PASS{{color:#6d6}} .LOOK{{color:#fc6}} td{{padding:2px 8px}}</style><h1>QA: {html.escape(name)}</h1>",
         "<table>" + "".join(f"<tr><td>{s}</td><td class='{st}'>{st}</td><td>{html.escape(t)}</td></tr>"
                             for s, st, t, _ in gate.rows) + "</table>"]
    fails = [(s, d) for s, st, _, ds in gate.rows if st in ("FAIL", "LOOK") for d in ds]
    if fails:
        md_ += ["## To fix or look at", ""] + [f"- {s}: {d}" for s, d in fails[:120]] + [""]
        h.append("<h2>To fix or look at</h2><ul>" + "".join(f"<li>{s}: {html.escape(d)}</li>" for s, d in fails[:120]) + "</ul>")
    for sec in ("storymap", "routes", "spots", "rooms", "empty", "ingame"):
        title, looks = LOOK[sec]
        md_ += [f"## {title}", ""] + [f"- [ ] {x}" for x in looks] + [""]
        h.append(f"<h2>{html.escape(title)}</h2><ul>" + "".join(f"<li>&#9744; {html.escape(x)}</li>" for x in looks) + "</ul>")
        for f, cap in pics.get(sec, []):
            extra = ""
            if sec == "rooms" and f.startswith("rooms/"):
                num = int(re.sub(r"\D", "", os.path.basename(f)) or 0)
                r = room_rows.get(num)
                if r: extra = (f" — {r['kind']}, {r['tiles']} tiles, coverage {r['cover']:.2f}" +
                               ("" if r["ok"] else f", MISSES its score: {'; '.join(r['flags'] + [w['msg'][:60] for w in r['warns']]) or 'coverage or lining'}"))
            md_ += [f"![{cap}]({f})", f"*{cap}{extra}*", ""]
            h.append(f"<p><b>{html.escape(cap + extra)}</b><br><a href='{f}'><img src='{f}' loading='lazy'></a></p>")
    open(os.path.join(qa_dir, "index.md"), "w", encoding="utf-8").write("\n".join(md_) + "\n")
    open(os.path.join(qa_dir, "index.html"), "w", encoding="utf-8").write("\n".join(h))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("design"); ap.add_argument("seed", nargs="?")
    ap.add_argument("--no-render", action="store_true"); ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--go", default="")
    a = ap.parse_args()
    design = design_path(a.design)
    dname = os.path.splitext(os.path.basename(design))[0]
    gate = Gate()
    t0 = time.time()
    # 1. build
    out_dir = os.path.join(REPO, "mapgen", "out", dname)
    if not a.no_build:
        rc, o = run([design] + ([a.seed] if a.seed else []))
        okl = re.search(r"^OK\t(.+?\.map)\t", o, re.M)
        if rc or not okl:
            gate.add("build", "FAIL", "the design did not build", o.strip().splitlines()[-15:])
            return finish(gate, None, None)
        map_path = okl.group(1)
        gate.add("build", "PASS", f"{os.path.relpath(map_path, REPO)} ({time.time() - t0:.0f} s)")
    else:
        maps = glob.glob(os.path.join(out_dir, "*.map"))
        if not maps: gate.add("build", "FAIL", f"no map in {out_dir}"); return finish(gate, None, None)
        map_path = maps[0]
        gate.add("build", "PASS", f"{os.path.relpath(map_path, REPO)} (not rebuilt)")
    name = os.path.splitext(os.path.basename(map_path))[0]
    # 2. checker
    import validate as V
    m, findings, _ = V.validate(map_path)
    acc = accepted(design)
    errs = [f for f in findings if f["severity"] == "error"]
    warns = [f for f in findings if f["severity"] == "warning"]
    gate.add("checker", "FAIL" if errs else "PASS", f"{len(errs)} errors",
             [f"[{f['rule']}] {f['msg'][:150]}" for f in errs])
    rows, unacc = [], 0
    for f in warns:
        why = acceptance(f, acc)
        unacc += why is None
        rows.append(f"[{f['rule']}] {'accepted: ' + why if why else 'NOT ACCEPTED'} - {f['msg'][:140]}")
    by_rule = collections.Counter(f["rule"] for f in warns)
    gate.add("warnings", "FAIL" if unacc else "PASS",
             f"{len(warns)} warnings, {unacc} not accepted" + (f" ({', '.join(f'{r} {n}' for r, n in by_rule.most_common())})"
                                                               if warns else ""), rows)
    info = [f["msg"] for f in findings if f["severity"] == "info" and f["check"] in ("routes", "density")]
    for i in info:
        if i.startswith("Routes:"): gate.add("routes", "PASS" if " 0 problems" in i else "FAIL", i)
    # 3. scripts
    sd = os.path.join(os.path.dirname(map_path), name + "_scripts")
    if os.path.isdir(sd):
        go = find_go(a.go)
        if not go:
            gate.add("scripts", "FAIL", "no Go compiler found: pass --go or set GO (tests/check_scripts.py)")
        else:
            rc, o = run([os.path.join("tests", "check_scripts.py"), sd, "--go", go], timeout=900)
            gate.add("scripts", "PASS" if rc == 0 else "FAIL", o.strip().splitlines()[-1] if o.strip() else "no output",
                     [] if rc == 0 else o.strip().splitlines()[-20:])
    else:
        gate.add("scripts", "PASS", "no scripts (a map without a story)")
    # 4. story
    sc = story_checks(map_path, name, m)
    gate.add("story", "PASS" if all(ok for ok, _ in sc) else "FAIL",
             f"{sum(ok for ok, _ in sc)} of {len(sc)} story checks pass", [("" if ok else "FAILED: ") + t for ok, t in sc])
    import voice as VO
    vc = VO.check(os.path.dirname(map_path), name)
    silent = []
    if os.path.isdir(sd):
        cfg = os.path.join(sd, "quests_config.go")
        for ln in (open(cfg, encoding="utf-8").read().splitlines() if os.path.exists(cfg) else []):   # a Line a line
            if "Else: []Act{" in ln: silent += re.findall(r'\{Kind: "chat", A: "([^"]+)"', ln.split("Else: ", 1)[1])
    gate.add("voice", "FAIL" if not all(ok for ok, _ in vc) else "LOOK" if silent else "PASS",
             f"{sum(ok for ok, _ in vc)} of {len(vc)} voice checks pass" +
             (f"; {len(silent)} refusals said over a head stay silent (q.tell voices them): {', '.join(silent)}" if silent else ""),
             [("" if ok else "FAILED: ") + t for ok, t in vc])
    # 5. rooms
    room_rows = {}
    if os.path.exists(os.path.splitext(map_path)[0] + ".rooms.json"):
        import roomscore as RS
        rs = RS.score(map_path)
        room_rows = {r["number"]: r for r in rs}
        miss = [r for r in rs if not r["ok"]]
        gate.add("rooms", "LOOK" if miss else "PASS", f"{len(rs) - len(miss)} of {len(rs)} rooms pass the room score",
                 [f"room {r['number']} {r['kind']} ({r['tiles']} tiles): coverage {r['cover']:.2f} of {r['target']:.2f}, "
                  f"lined {r['lined']:.2f}" + (f", {'; '.join(r['flags'])}" if r["flags"] else "") +
                  (f", {len(r['warns'])} warnings" if r["warns"] else "") for r in miss])
    # 6. exterior
    import exteriors as EX, checks as C
    env = C.environment(m)
    ext = EX.measure(m)
    base = json.load(open(EX.BASELINE)) if os.path.exists(EX.BASELINE) else {}
    ref = base.get(env, {}).get("empty4")
    e4 = ext["empty4"]
    if ref:
        st = "FAIL" if e4 > ref["p90"] else "LOOK" if e4 > ref["p75"] else "PASS"
        if st == "FAIL" and any(r == "exterior_holes" for r, _, _ in acc): st = "LOOK"
        made = base[env].get("made", {})
        gate.add("exterior", st, f"{e4:.0%} of the open ground has no prop within 4 cells (Westwood's {env} maps: median "
                 f"{ref['p50']:.0%}, p75 {ref['p75']:.0%}, p90 {ref['p90']:.0%}); made things {ext['made']} per 100 open "
                 f"tiles (Westwood median {made.get('p50', '?')})")
    else:
        gate.add("exterior", "LOOK", f"{e4:.0%} of the open ground has no prop within 4 cells (no Westwood reference for {env})")
    # 6b. sight: where the OpenNox client would crash on the edge of the player's sight [CL-1]
    import sightrows as SR
    sr = SR.scan(map_path)
    crash = [r for r in sr if r[2] >= SR.CRASH]
    risk = [r for r in sr if SR.RISK <= r[2] < SR.CRASH]
    gate.add("sight", "FAIL" if crash else "LOOK" if risk else "PASS",
             f"most crossings of the sight's edge on one screen row: {max(r[2] for r in sr)} ({len(sr)} points; the "
             f"client panics at 31; the estimate, tests/sightrows.py, fails at {SR.CRASH}+, {SR.RISK}-"
             f"{SR.CRASH - 1} is a risk)", [f"({x}, {y}): {c} crossings on screen row {row}" +
                                           (" CRASH" if c >= SR.CRASH else "")
                                           for x, y, c, row in sorted(crash + risk, key=lambda r: -r[2])])
    # 7. pictures
    pics = {}
    qa_dir = os.path.join(REPO, "review", "out", name, "qa")
    if not a.no_render:
        if os.path.isdir(qa_dir): shutil.rmtree(qa_dir)
        os.makedirs(qa_dir, exist_ok=True)
        pics = pictures(map_path, name, m, qa_dir, gate)
    else:
        os.makedirs(qa_dir, exist_ok=True)
        gate.add("pictures", "LOOK", "not rendered (--no-render): render them before handing the map over")
    return finish(gate, qa_dir, (name, pics, room_rows), t0)


def finish(gate, qa_dir, extra, t0=None):
    if qa_dir and extra:
        name, pics, room_rows = extra
        if pics or not os.path.exists(os.path.join(qa_dir, "index.html")):   # --no-render keeps the last pictures' index
            write_index(qa_dir, name, gate, pics, room_rows)
        json.dump([dict(step=s, status=st, text=t, details=d) for s, st, t, d in gate.rows],
                  open(os.path.join(qa_dir, "qa.json"), "w"), indent=1)
    print()
    print(f"QA gate: {'PASS' if gate.ok else 'FAIL'}" + (f" in {time.time() - t0:.0f} s" if t0 else "") +
          ("" if not qa_dir else f". Review: {os.path.join(qa_dir, 'index.html')}"))
    print("Not done here: installing (mapgen/install.py) and the server smoke test (tests/server_smoke.py) come after, "
          "run by the main session (the user may be playing on this PC).")
    return 0 if gate.ok else 1


if __name__ == "__main__":
    sys.exit(main())
