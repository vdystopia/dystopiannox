"""Checks the checks: how often each rule of the checker (checks.RULES) fires on our maps and on Westwood's, and which
rules the self-test plants a defect for. Finds dead rules (never fire anywhere and have no planted case), rules
Westwood trips often (miscalibrated: a warning on more than a quarter of Westwood's maps, an error on more than 5%),
findings no rule names ("<check>.other") and rules with no planted case.

    py validate/checkcheck.py                      our 11 campaign maps (mapgen/out) and every Westwood single-player map
    py validate/checkcheck.py --sample 30          a sample of Westwood's maps (every 4th)
    py validate/checkcheck.py --ours-only          only our maps
    py validate/checkcheck.py map.map [...]        these maps as "ours"

Reads validate/out/selftest/rules.json (written by validate/selftest.py) for the planted cases. Writes
validate/out/checkcheck.md and .json, and prints the table.
"""
import collections, glob, json, os, sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mapdata as md
import checks as C
import validate as V

DESIGNS = ["starwell", "ambermere", "greywatch", "thornwick", "tnorth", "rimehold", "rimepass", "emberhollow", "ashroad",
           "deepvault", "mirefen"]
WARN_MAPS, ERR_MAPS = 0.25, 0.05


def our_maps():
    out = []
    for d in DESIGNS:
        out += [p for p in glob.glob(os.path.join(md.REPO, "mapgen", "out", d, "*.map"))]
    return out


def tally(path):
    m = md.load(path)
    findings, _ = C.run_all(m, V.baseline())
    c = collections.Counter((f["rule"], f["severity"]) for f in findings if f["severity"] != "info")
    ex = {}
    for f in findings:
        if f["severity"] != "info": ex.setdefault(f["rule"], f["msg"][:110])
    return m.name, dict(c), ex


def main(argv):
    paths = [a for a in argv if a.endswith(".map")] or our_maps()
    ww = [] if "--ours-only" in argv else [md.corpus_json(n) for n, _ in md.sp_corpus_maps()]
    if "--sample" in argv:
        k = int(argv[argv.index("--sample") + 1]); step = max(1, len(ww) // k); ww = ww[::step][:k]
    paths = [md.export(p) for p in paths]       # one at a time: the editor's exporter shares its folder
    with ProcessPoolExecutor(6) as pool:
        ours = list(pool.map(tally, paths))
        west = list(pool.map(tally, ww))
    planted = {}
    pr = os.path.join(md.OUT, "selftest", "rules.json")
    if os.path.exists(pr): planted = json.load(open(pr))
    rows = []
    rules = [(r, c, fb) for r, c, _, fb in C.RULES]
    seen = {r for _, c, _ in ours + west for r, _ in c} | set(planted)
    rules += [(r, r.split(".")[0], "") for r in sorted(seen) if r not in {x[0] for x in rules}]
    for rule, chk, fb in rules:
        o_maps = [n for n, c, _ in ours if any(k[0] == rule for k in c)]
        o_n = sum(v for _, c, _ in ours for k, v in c.items() if k[0] == rule)
        w_maps = [n for n, c, _ in west if any(k[0] == rule for k in c)]
        w_n = sum(v for _, c, _ in west for k, v in c.items() if k[0] == rule)
        sev = {k[1] for _, c, _ in ours + west for k in c if k[0] == rule}
        ex = next((e[rule] for _, _, e in ours + west if rule in e), "")
        notes = []
        if rule.endswith(".other"): notes.append("UNNAMED: give its message a rule in checks.RULES")
        if not o_n and not w_n and rule not in planted: notes.append("DEAD: never fires and no planted case")
        if ww and "warning" in sev and len(w_maps) > WARN_MAPS * len(ww): notes.append(f"MISCALIBRATED? fires on "
                                                                                        f"{len(w_maps)}/{len(ww)} Westwood maps")
        if ww and "error" in sev and len(w_maps) > ERR_MAPS * len(ww): notes.append(f"ERROR on {len(w_maps)} Westwood maps")
        if rule not in planted: notes.append("no planted case")
        rows.append(dict(rule=rule, check=chk, feedback=fb, ours_maps=len(o_maps), ours=o_n, ww_maps=len(w_maps), ww=w_n,
                         planted=planted.get(rule, ""), notes=notes, example=ex, ours_names=o_maps[:6],
                         ww_names=w_maps[:6]))
    lines = [f"# Check of the checks", "",
             f"Our maps: {len(ours)} ({', '.join(n for n, _, _ in ours)}). Westwood's single-player maps: {len(west)}.", "",
             "| Rule | Feedback | Ours: maps / findings | Westwood: maps / findings | Planted case | Notes |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['rule']} | {r['feedback']} | {r['ours_maps']} / {r['ours']} | {r['ww_maps']} / {r['ww']} | "
                     f"{r['planted']} | {'; '.join(r['notes'])} |")
    text = "\n".join(lines) + "\n"
    os.makedirs(md.OUT, exist_ok=True)
    open(os.path.join(md.OUT, "checkcheck.md"), "w", encoding="utf-8").write(text)
    json.dump(dict(ours=ours, west=west, rows=rows), open(os.path.join(md.OUT, "checkcheck.json"), "w"), indent=1)
    print(text)
    print(f"Written: {os.path.join(md.OUT, 'checkcheck.md')}")


if __name__ == "__main__":
    main(sys.argv[1:])
