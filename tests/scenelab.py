"""The scene lab's harness: one iteration of the loop for one exterior scene type (or every type), steps 1-2 of
review/scenelab/README.md and the metric judge. The outdoor twin of tests/roomlab.py.

    py tests/scenelab.py <scene> [--n 10] [--seed S] [--iter NAME]     one scene type (review/scenelab/scenecat.py)
    py tests/scenelab.py all [--n 10] [--seed S] [--iter NAME]        every type with a recipe, then a summary table
    py tests/scenelab.py list                                         the types and their Westwood evidence
    py tests/scenelab.py <scene|all> --iter NAME --rejudge             judge an iteration again (after changing a judge)

Each run:
1. generates N variants of the scene (review/scenelab/labgen.py): each in its own clearing of a template outdoor map,
   laid by the kit's real code (recipes.py), varying size (small, typical, large), site (an open glade, against a
   wall, by a road, on a shore), forest and seed; the map goes to review/out/scenelab/<scene>/<iter>/map/;
2. finds each scene on the built map as Westwood's are found (labref.find_scenes: the type's signature, its pieces
   grown from it), measures and judges it against Westwood's campaign scenes of the type (metrics.py: features,
   percentiles, plain-English findings, hard rules, the batch's classifier AUC) into metrics.json;
3. renders each scene as Westwood's are rendered (labrender.py) to renders/NN.png, and Westwood's into the cached
   gallery (review/out/scenelab/_westwood/<scene>/);
4. builds the blind sheet (blind.py: blind/A-J.png, the key apart in blind_key.json);
5. writes the scorecard (scorecard.py: index.html, scorecard.json) and records the iteration in
   review/out/scenelab/<scene>/iterations.json, which the next iteration's scorecard compares with.

The same scene, N and seed always give the same map (crc32 seeds, never hash()). Iteration names: letters, digits,
'-' and '_' (default "scratch"). Needs numpy and scikit-learn. Never installs, never launches the game or the server:
the only program it starts is the map editor's headless renderer.
"""
import argparse, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "review", "scenelab"))
import labenv as E   # noqa: E402  (sets the import paths)


def render(scene, it, log=print):
    import labref, labrender
    d = E.iter_dir(scene, it)
    with open(os.path.join(d, "metrics.json"), encoding="utf-8") as f: m = json.load(f)
    with open(os.path.join(d, "variants.json"), encoding="utf-8") as f: batch = json.load(f)
    win = tuple(labref.gallery(scene, log=lambda *_: None)["window"])
    rd = os.path.join(d, "renders")
    os.makedirs(rd, exist_ok=True)
    full = labrender.lab_render(os.path.abspath(os.path.join(d, "map", batch["variants"][0]["map"] + ".map")))
    for r in m["scenes"]:
        s = r.get("scene") or dict(anchor=r["variant"]["anchor"], pieces=[])
        labrender.picture(full, s, win).save(os.path.join(rd, f"{r['index']:02d}.png"))


def rejudge(scene, it, log=print):
    import metrics, blind, scorecard
    d = E.iter_dir(scene, it)
    metrics.judge_batch(scene, it, log=log)
    render(scene, it, log)
    if not os.path.exists(os.path.join(d, "blind", "judge.json")): blind.make(scene, it)
    scorecard.write(scene, it)
    return report(scene, it, log)


def report(scene, it, log=print):
    import scorecard, metrics
    s = scorecard.summarise(scene, it)
    with open(os.path.join(E.iter_dir(scene, it), "metrics.json"), encoding="utf-8") as f: m = json.load(f)
    log(f"{scene} [{it}]: {s['scenes']} scenes ({s['missing']} missing); AUC {s['auc']}; {s['scenes_with_hard']} with "
        f"hard-rule findings {json.dumps(s['hard_rules']) if s['hard_rules'] else ''}; Westwood evidence "
        f"{s['westwood_scenes']} scenes")
    for line in metrics.findings_text(m, 5)[1:]:
        log("   " + line)
    log(f"   scorecard: {E.rel(os.path.join(E.iter_dir(scene, it), 'index.html'))}")
    return s


def run(scene, n=10, seed=1, it="scratch", log=print):
    import labgen, labref, metrics, blind, scorecard
    t0 = time.time()
    d = E.iter_dir(scene, it)
    os.makedirs(d, exist_ok=True)
    # the map's name from the scene and seed only, never the iteration's name: the kit seeds its scenes' own generators
    # from the map's name (camps.own_rng, the dressing, the garden, the dock, the yards), so a name drawn from the
    # iteration had given the same code and seed different scenes run to run (bandit camps of 24 and 19 pieces)
    name = "S" + format(E.seed_of(scene, seed) & 0xFFFFFF, "06x")
    batch = labgen.generate(scene, n, seed, out_dir=os.path.join(d, "map"), name=name, log=log)
    with open(os.path.join(d, "variants.json"), "w", encoding="utf-8") as f:
        json.dump(dict(scene=scene, iter=it, n=n, seed=seed, maps=[E.rel(p) for p in batch["maps"]],
                       variants=batch["variants"]), f, indent=1)
    t1 = time.time()
    labref.gallery(scene, log=lambda *_: None)
    metrics.judge_batch(scene, it, log=log)
    t2 = time.time()
    render(scene, it, log)
    t3 = time.time()
    blind.make(scene, it)
    scorecard.write(scene, it)
    log(f"   (build {t1 - t0:.0f}s, judge {t2 - t1:.0f}s, render {t3 - t2:.0f}s)")
    return report(scene, it, log)


def summary_table(rows, it):
    lines = [f"# Scene lab: iteration {it}", "",
             "| Scene | Westwood scenes | AUC | Blind acc. | Blind gen/WW | Hard-rule scenes | Missing | Worst findings |",
             "|---|---|---|---|---|---|---|---|"]
    for s in rows:
        auc = "-" if s["auc"] is None else f"{s['auc']:.2f}"
        acc = "-" if s.get("blind_accuracy") is None else f"{s['blind_accuracy']:.0%}"
        bs = "-" if s.get("blind_generated") is None else f"{s['blind_generated']}/{s['blind_westwood']}"
        worst = "; ".join(w.split(" (Westwood")[0] for w in s["worst"][:2])
        lines.append(f"| {s['scene']} | {s['westwood_scenes']} | {auc} | {acc} | {bs} | {s['scenes_with_hard']}/{s['scenes']} "
                     f"{json.dumps(s['hard_rules']) if s['hard_rules'] else ''} | {s['missing']} | {worst} |")
    return "\n".join(lines) + "\n"


def main():
    import scenecat, recipes
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scene")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--iter", default="scratch")
    ap.add_argument("--rejudge", action="store_true", help="judge an iteration already generated again")
    a = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", a.iter): sys.exit("--iter: letters, digits, '-' and '_' only")
    types = [t for t in scenecat.ranked() if t in recipes.RECIPES]
    if a.scene == "list":
        import labref
        for t in scenecat.ranked():
            ww = labref.westwood(t)
            maps = sorted({s["map"] for s in ww})
            print(f"{scenecat.SCENES[t]['rank']:2d} {t:16s} Westwood scenes: {len(ww):3d}  {'recipe' if t in recipes.RECIPES else 'no recipe':9s} "
                  f"{', '.join(maps[:8])}{' ...' if len(maps) > 8 else ''}")
        return
    todo = types if a.scene == "all" else [a.scene]
    for t in todo:
        if t not in types: sys.exit(f"unknown scene {t}; one of: {', '.join(types)}")
    rows = []
    for t in todo:
        try:
            rows.append(rejudge(t, a.iter) if a.rejudge else run(t, a.n, a.seed, a.iter))
        except Exception as ex:
            import traceback; traceback.print_exc()
            print(f"{t}: failed: {ex}")
    if len(todo) > 1:
        import scorecard
        rows = [scorecard.summarise(t, a.iter) for t in todo if os.path.exists(os.path.join(E.iter_dir(t, a.iter), "metrics.json"))]
        text = summary_table(rows, a.iter)
        p = os.path.join(E.OUT, f"summary_{a.iter}.md")
        with open(p, "w", encoding="utf-8") as f: f.write(text)
        print(text)
        print(E.rel(p))


if __name__ == "__main__":
    main()
