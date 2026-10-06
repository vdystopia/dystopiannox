"""The scene lab's scorecard for one iteration of one scene type: review/out/scenelab/<scene>/<iter>/index.html and
scorecard.json. The generated renders with their metric findings, the batch AUC, the plain-English findings, the blind
judge's accuracy and scores once filled in, Westwood's scenes of the type, and the comparison with the previous
iteration. (The room lab's review/roomlab/scorecard.py, copied and adapted.)

    py review/scenelab/scorecard.py <scene> <iter>     (tests/scenelab.py and blind.py score write it)

The stop criteria (review/scenelab/README.md): AUC at most 0.6; blind accuracy near chance (at most 60%); the generated
scenes' blind score at least Westwood's mean minus 0.5; no hard-rule findings.
"""
import datetime, html, json, os, sys
import labenv as E

STOP = dict(auc=0.60, blind_accuracy=0.60, score_gap=0.5, hard=0)


def _load(path):
    if not os.path.exists(path): return None
    with open(path, encoding="utf-8") as f: return json.load(f)


def history(scene):
    return _load(os.path.join(E.OUT, scene, "iterations.json")) or []


def _record(scene, it, summary):
    p = os.path.join(E.OUT, scene, "iterations.json")
    h = [x for x in history(scene) if x["iter"] != it]
    h.append(dict(summary, iter=it, at=datetime.datetime.now().isoformat(timespec="seconds")))
    with open(p, "w", encoding="utf-8") as f: json.dump(h, f, indent=1)
    return h


def summarise(scene, it):
    d = E.iter_dir(scene, it)
    m = _load(os.path.join(d, "metrics.json"))
    b = _load(os.path.join(d, "blind", "result.json"))
    c = m["classifier"]
    sc = m["scenes"]
    s = dict(scene=scene, auc=c.get("auc"), auc_sd=c.get("auc_sd"), westwood_scenes=m["westwood_scenes"],
             scenes=len(sc), missing=m.get("missing", 0), scenes_with_hard=m["scenes_with_hard"],
             hard_rules=m["hard_rules"],
             findings_per_scene=round(sum(len(r["findings"]) for r in sc) / max(1, len(sc)), 2),
             worst=[w["example"] for w in m["worst"][:3]],
             blind_accuracy=b and b["accuracy"], blind_generated=b and b["score_generated"],
             blind_westwood=b and b["score_westwood"])
    ok = dict(auc=s["auc"] is not None and s["auc"] <= STOP["auc"],
              blind_accuracy=b is not None and b["accuracy"] <= STOP["blind_accuracy"],
              blind_score=b is not None and None not in (b["score_generated"], b["score_westwood"]) and
              b["score_generated"] >= b["score_westwood"] - STOP["score_gap"],
              hard=s["scenes_with_hard"] == 0)
    s["stop"] = ok
    s["done"] = all(ok.values())
    return s


def write(scene, it):
    import labref, metrics, scenecat
    d = E.iter_dir(scene, it)
    m = _load(os.path.join(d, "metrics.json"))
    v = _load(os.path.join(d, "variants.json"))
    b = _load(os.path.join(d, "blind", "result.json"))
    s = summarise(scene, it)
    prev = next((x for x in reversed(history(scene)) if x["iter"] != it), None)
    _record(scene, it, s)
    gal = labref.gallery(scene)
    plain = metrics.findings_text(m)
    with open(os.path.join(d, "scorecard.json"), "w", encoding="utf-8") as f:
        json.dump(dict(summary=s, previous=prev, classifier=m["classifier"], findings=plain, worst=m["worst"], blind=b,
                       scenes=[dict(index=r["index"], size=r["variant"]["size"], site=r["variant"]["site"],
                                    hard=[h["text"] for h in r["hard"]],
                                    findings=[x["text"] for x in r["findings"][:8]]) for r in m["scenes"]]),
                  f, indent=1)
    e = html.escape
    c = m["classifier"]
    bad = lambda ok: "ok" if ok else "no"
    acc = f"{b['accuracy']:.0%}" if b else "-"
    spec = scenecat.SCENES[scene]
    out = [f"<!doctype html><html><head><meta charset='utf-8'><title>Scene lab: {e(scene)} {e(it)}</title><style>",
           "body{font-family:Segoe UI,Arial,sans-serif;background:#16161a;color:#ddd;margin:20px;max-width:1500px}",
           "h1,h2{color:#f0d090}a{color:#9cf}table{border-collapse:collapse;margin:8px 0}td,th{border:1px solid #444;"
           "padding:4px 8px;vertical-align:top;font-size:14px}th{background:#24242a}.ok{color:#8d8}.no{color:#f88}"
           ".card{display:flex;gap:16px;border-top:1px solid #333;padding:12px 0}.card img{width:560px;height:auto;"
           "border:1px solid #333}.facts{font-size:14px}.hard{color:#f88}.find{color:#eec}.cross{color:#aaa}"
           ".gal{display:flex;flex-wrap:wrap;gap:8px}.gal figure{margin:0;width:360px;font-size:12px}.gal img{width:360px}"
           "small{color:#999}</style></head><body>",
           f"<h1>Scene lab: {e(spec['title'])}, iteration {e(it)}</h1>",
           f"<p>{e(spec['purpose'])}.<br><small>{len(m['scenes'])} generated variants (seed {v.get('seed')}) against "
           f"{m['westwood_scenes']} Westwood campaign scenes of the type. Brief: rules/scenes/{e(scene)}.md; recipe: "
           f"review/scenelab/recipes.py RECIPES['{e(scene)}'].</small></p>",
           "<h2>Stop criteria</h2><table><tr><th>criterion</th><th>now</th><th>target</th><th>met</th></tr>",
           f"<tr><td>classifier AUC (Westwood vs generated)</td><td>{s['auc']} &plusmn; {s['auc_sd']}</td>"
           f"<td>&le; {STOP['auc']}</td><td class={bad(s['stop']['auc'])}>{bad(s['stop']['auc'])}</td></tr>",
           f"<tr><td>blind judge accuracy</td><td>{acc}</td><td>&le; {STOP['blind_accuracy']:.0%}</td>"
           f"<td class={bad(s['stop']['blind_accuracy'])}>{bad(s['stop']['blind_accuracy']) if b else 'not judged'}</td></tr>",
           f"<tr><td>blind score: generated vs Westwood</td><td>{b and b['score_generated']} vs {b and b['score_westwood']}"
           f"</td><td>&ge; Westwood &minus; {STOP['score_gap']}</td><td class={bad(s['stop']['blind_score'])}>"
           f"{bad(s['stop']['blind_score']) if b else 'not judged'}</td></tr>",
           f"<tr><td>scenes with hard-rule findings</td><td>{s['scenes_with_hard']} of {s['scenes']} "
           f"{e(json.dumps(s['hard_rules']))}</td><td>0</td><td class={bad(s['stop']['hard'])}>{bad(s['stop']['hard'])}</td></tr>",
           "</table>", "<h2>Findings</h2><ul>" + "".join(f"<li>{e(x)}</li>" for x in plain) + "</ul>"]
    if prev:
        out.append("<h2>Against the previous iteration</h2><table><tr><th></th><th>" + e(prev["iter"]) + "</th><th>"
                   + e(it) + "</th></tr>")
        for k in ("auc", "scenes_with_hard", "findings_per_scene", "missing", "blind_accuracy", "blind_generated",
                  "blind_westwood"):
            out.append(f"<tr><td>{k}</td><td>{prev.get(k)}</td><td>{s.get(k)}</td></tr>")
        out.append("</table>")
    out.append("<h2>What gives the batch away</h2><p><small>Each feature's own AUC (1.0: it alone separates them), "
               "the generated median against Westwood's.</small></p><table><tr><th>feature</th><th>AUC</th>"
               "<th>generated is</th><th>generated median</th><th>Westwood median</th></tr>")
    for name, a, dirn, gm, wm in c.get("top", []):
        out.append(f"<tr><td>{e(name)}</td><td>{a}</td><td>{dirn}</td><td>{gm}</td><td>{wm}</td></tr>")
    out.append("</table><h2>The batch's worst findings</h2><table><tr><th>scenes</th><th>finding</th>"
               "<th>where to change it</th></tr>")
    for w in m["worst"]:
        out.append(f"<tr><td>{w['scenes']}</td><td>{e(w['example'])}</td><td><small>{e(w['where'])}</small></td></tr>")
    out.append("</table>")
    if b:
        out.append(f"<h2>Blind judge ({e(str(b.get('judge')))})</h2><p>Accuracy {b['accuracy']:.0%}; mean score "
                   f"generated {b['score_generated']}, Westwood {b['score_westwood']}. {e(str(b.get('overall') or ''))}</p>"
                   "<table><tr><th>letter</th><th>was</th><th>guess</th><th>conf.</th><th>score</th><th>critique</th></tr>")
        for r in b["pictures"]:
            src = r["source"] + (f" #{r['variant']}" if r.get("variant") else f" {r.get('map')}")
            crit = r["critique"] if isinstance(r["critique"], str) else "; ".join(r["critique"] or [])
            out.append(f"<tr><td>{r['letter']}</td><td>{e(src)}</td><td class={'ok' if r['correct'] else 'no'}>"
                       f"{e(r['guess'])}</td><td>{r['confidence']}</td><td>{r['score']}</td><td>{e(crit)}</td></tr>")
        out.append("</table>")
    else:
        out.append(f"<h2>Blind judge</h2><p>Not judged yet: <code>blind/</code> holds the sheet; follow "
                   f"review/scenelab/JUDGE.md, then <code>py review/scenelab/blind.py score {e(scene)} {e(it)}</code>.</p>")
    out.append("<h2>The generated scenes</h2>")
    for r in m["scenes"]:
        vv = r["variant"]
        img = f"renders/{r['index']:02d}.png"
        f = r.get("features") or {}
        facts = (f"<b>#{r['index']}</b> {e(vv['size'])}, {e(vv['site'])}, {e(vv['forest'])} wood"
                 + (f"; {e(str(vv.get('theme') or vv.get('kind') or vv.get('trade') or ''))}") + "<br>"
                 + (f"{f['n']} pieces, {f['types']} kinds, reach {f['reach']:.0f} px, {f['groups']} zones, open "
                    f"{f['open']:.2f}, nn {f['nn_med']:.0f} px, creatures {f['cr_n']}" if f else "missing"))
        hard = "".join(f"<li class=hard>{e(h['text'])}</li>" for h in r["hard"])
        finds = "".join(f"<li class=find>{e(x['text'])}</li>" for x in r["findings"][:8])
        st = "".join(f"<li class=cross>Westwood never puts a {e(k)} in a scene of the type</li>" for k in r.get("strangers", [])[:4])
        out.append(f"<div class=card><a href='{img}'><img src='{img}'></a><div class=facts>{facts}<ul>{hard}{finds}{st}"
                   f"</ul></div></div>")
    rel = os.path.relpath(labref.gallery_dir(scene), d).replace("\\", "/")
    out.append(f"<h2>Westwood's scenes of the type</h2><p><small>{len(gal['scenes'])} campaign scenes, drawn the same way "
               f"(a {gal['window'][0]} x {gal['window'][1]} px window).</small></p><div class=gal>")
    for g in gal["scenes"][:24]:
        out.append(f"<figure><a href='{rel}/{g['file']}'><img src='{rel}/{g['file']}'></a><figcaption>{e(g['map'])} "
                   f"{[int(a) for a in g['anchor']]}, {g['n']} pieces</figcaption></figure>")
    out.append("</div></body></html>")
    p = os.path.join(d, "index.html")
    with open(p, "w", encoding="utf-8") as fh: fh.write("\n".join(out))
    return p


if __name__ == "__main__":
    print(write(sys.argv[1], sys.argv[2]))
