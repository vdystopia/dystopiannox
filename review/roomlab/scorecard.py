"""The room lab's scorecard for one iteration of one type: review/out/roomlab/<type>/<iter>/index.html and
scorecard.json. The generated renders with their metric findings, the batch AUC, the blind judge's accuracy and scores
once filled in, Westwood's examples of the type, and the comparison with the previous iteration.

    py review/roomlab/scorecard.py <type> <iter>     (tests/roomlab.py and blind.py score write it)

The stop criteria (review/roomlab/README.md): AUC at most 0.6; blind accuracy at most 60%; the generated rooms' blind
score at least Westwood's mean minus 0.5; no hard-rule findings.
"""
import datetime, html, json, os, sys
import labenv as E

STOP = dict(auc=0.60, blind_accuracy=0.60, score_gap=0.5, hard=0)


def _load(path):
    if not os.path.exists(path): return None
    with open(path, encoding="utf-8") as f: return json.load(f)


def history(typ):
    p = os.path.join(E.OUT, typ, "iterations.json")
    return _load(p) or []


def _record(typ, it, summary):
    p = os.path.join(E.OUT, typ, "iterations.json")
    h = [x for x in history(typ) if x["iter"] != it]
    h.append(dict(summary, iter=it, at=datetime.datetime.now().isoformat(timespec="seconds")))
    with open(p, "w", encoding="utf-8") as f: json.dump(h, f, indent=1)
    return h


def summarise(typ, it):
    d = E.iter_dir(typ, it)
    m = _load(os.path.join(d, "metrics.json"))
    b = _load(os.path.join(d, "blind", "result.json"))
    c = m["classifier"]
    s = dict(type=typ, auc=c.get("auc"), auc_sd=c.get("auc_sd"), fallback=c.get("fallback"),
             cross_auc=m["cross_classifier"].get("auc"), westwood_rooms=m["westwood_rooms"],
             rooms=len(m["rooms"]), rooms_with_hard=m["rooms_with_hard"], hard_rules=m["hard_rules"],
             findings_per_room=round(sum(len(r["findings"]) for r in m["rooms"]) / max(1, len(m["rooms"])), 2),
             worst=[w["example"] for w in m["worst"][:3]],
             blind_accuracy=b and b["accuracy"], blind_generated=b and b["score_generated"],
             blind_westwood=b and b["score_westwood"],
             template=(m.get("template") or {}).get("batch"), template_ww=(m.get("template") or {}).get("ww_p50"),
             template_ww90=(m.get("template") or {}).get("ww_p90"), template_flag=(m.get("template") or {}).get("flag"))
    ok = dict(auc=s["auc"] is not None and s["auc"] <= STOP["auc"],
              blind_accuracy=b is not None and b["accuracy"] <= STOP["blind_accuracy"],
              blind_score=b is not None and None not in (b["score_generated"], b["score_westwood"]) and
              b["score_generated"] >= b["score_westwood"] - STOP["score_gap"],
              hard=s["rooms_with_hard"] == 0)
    s["stop"] = ok
    s["done"] = all(ok.values())
    return s


def write(typ, it):
    d = E.iter_dir(typ, it)
    m = _load(os.path.join(d, "metrics.json"))
    v = _load(os.path.join(d, "variants.json"))
    b = _load(os.path.join(d, "blind", "result.json"))
    s = summarise(typ, it)
    prev = next((x for x in reversed(history(typ)) if x["iter"] != it), None)
    _record(typ, it, s)
    import labref
    gal = labref.gallery(typ)
    with open(os.path.join(d, "scorecard.json"), "w", encoding="utf-8") as f:
        json.dump(dict(summary=s, previous=prev, classifier=m["classifier"], cross_classifier=m["cross_classifier"],
                       worst=m["worst"], blind=b,
                       rooms=[dict(index=r["index"], kind=r["kind"], culture=r["culture"], style=r["style"],
                                   size=r["size"], shape=r["shape"], tiles=r["tiles"], doors=r["doors"],
                                   hard=[h["text"] for h in r["hard"]], findings=[x["text"] for x in r["findings"][:8]],
                                   cross=[x["text"] for x in r["cross"][:4]], warnings=r["warnings"])
                              for r in m["rooms"]]), f, indent=1)
    e = html.escape
    c = m["classifier"]
    bad = lambda ok: "ok" if ok else "no"
    acc = f"{b['accuracy']:.0%}" if b else "-"
    out = [f"<!doctype html><html><head><meta charset='utf-8'><title>Room lab: {e(typ)} {e(it)}</title><style>",
           "body{font-family:Segoe UI,Arial,sans-serif;background:#16161a;color:#ddd;margin:20px;max-width:1500px}",
           "h1,h2{color:#f0d090}a{color:#9cf}table{border-collapse:collapse;margin:8px 0}td,th{border:1px solid #444;"
           "padding:4px 8px;vertical-align:top;font-size:14px}th{background:#24242a}.ok{color:#8d8}.no{color:#f88}"
           ".card{display:flex;gap:16px;border-top:1px solid #333;padding:12px 0}.card img{width:560px;height:auto;"
           "border:1px solid #333}.facts{font-size:14px}.hard{color:#f88}.find{color:#eec}.cross{color:#aaa}"
           ".gal{display:flex;flex-wrap:wrap;gap:8px}.gal figure{margin:0;width:360px;font-size:12px}.gal img{width:360px}"
           "small{color:#999}</style></head><body>",
           f"<h1>Room lab: {e(typ.replace('_', ' '))}, iteration {e(it)}</h1>",
           f"<p><small>{len(m['rooms'])} generated variants (seed {v.get('seed')}) against {m['westwood_rooms']} Westwood "
           f"campaign rooms of the type ({e(json.dumps(m['westwood_cultures']))}). Brief: rules/rooms/{e(typ)}.md; "
           f"profile: mapgen/kit/roomtypes.py TYPES['{e(typ)}'].</small></p>",
           "<h2>Stop criteria</h2><table><tr><th>criterion</th><th>now</th><th>target</th><th>met</th></tr>",
           f"<tr><td>classifier AUC (Westwood vs generated)</td><td>{s['auc']} &plusmn; {s['auc_sd']}"
           f"{' (fallback pool)' if s['fallback'] else ''}</td><td>&le; {STOP['auc']}</td>"
           f"<td class={bad(s['stop']['auc'])}>{bad(s['stop']['auc'])}</td></tr>",
           f"<tr><td>blind judge accuracy</td><td>{acc}</td><td>&le; {STOP['blind_accuracy']:.0%}</td><td class={bad(s['stop']['blind_accuracy'])}>"
           f"{bad(s['stop']['blind_accuracy']) if b else 'not judged'}</td></tr>",
           f"<tr><td>blind score: generated vs Westwood</td><td>{b and b['score_generated']} vs {b and b['score_westwood']}"
           f"</td><td>&ge; Westwood &minus; {STOP['score_gap']}</td><td class={bad(s['stop']['blind_score'])}>"
           f"{bad(s['stop']['blind_score']) if b else 'not judged'}</td></tr>",
           f"<tr><td>rooms with hard-rule findings</td><td>{s['rooms_with_hard']} of {s['rooms']} "
           f"{e(json.dumps(s['hard_rules']))}</td><td>0</td><td class={bad(s['stop']['hard'])}>{bad(s['stop']['hard'])}</td></tr>",
           f"<tr><td>cross-type AUC (type-free features, every Westwood room)</td><td>{s['cross_auc']}</td><td>(context)</td><td></td></tr>",
           f"<tr><td>template similarity (mean pairwise layout similarity of the batch; metrics.template)</td>"
           f"<td>{s.get('template')} (Westwood p50 {s.get('template_ww')}, p90 {s.get('template_ww90')}; twins "
           f"{e(json.dumps((m.get('template') or {}).get('twins', [])))})</td><td>&le; Westwood's p90</td>"
           f"<td class={bad(not s.get('template_flag'))}>{'MORE ALIKE THAN WESTWOOD' if s.get('template_flag') else 'ok'}</td></tr>",
           "</table>", f"<p><small>{e(c['note'])}</small></p>"]
    if prev:
        out.append("<h2>Against the previous iteration</h2><table><tr><th></th><th>" + e(prev["iter"]) + "</th><th>"
                   + e(it) + "</th></tr>")
        for k in ("auc", "cross_auc", "template", "rooms_with_hard", "findings_per_room", "blind_accuracy",
                  "blind_generated", "blind_westwood"):
            out.append(f"<tr><td>{k}</td><td>{prev.get(k)}</td><td>{s.get(k)}</td></tr>")
        out.append("</table>")
    out.append("<h2>What gives the batch away</h2><p><small>Each feature's own AUC (1.0: it alone separates them), "
               "the generated median against Westwood's.</small></p><table><tr><th>feature</th><th>AUC</th>"
               "<th>generated is</th><th>generated median</th><th>Westwood median</th></tr>")
    for name, a, dirn, gm, wm in c.get("top", []):
        out.append(f"<tr><td>{e(name)}</td><td>{a}</td><td>{dirn}</td><td>{gm}</td><td>{wm}</td></tr>")
    out.append("</table><h2>The batch's worst findings</h2><table><tr><th>rooms</th><th>finding</th><th>where to change it</th></tr>")
    for w in m["worst"]:
        out.append(f"<tr><td>{w['rooms']}</td><td>{e(w['example'])}</td><td><small>{e(w['where'])}</small></td></tr>")
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
                   f"review/roomlab/JUDGE.md, then <code>py review/roomlab/blind.py score {e(typ)} {e(it)}</code>.</p>")
    out.append("<h2>The generated rooms</h2>")
    for r in m["rooms"]:
        f = r["features"]
        img = f"renders/{r['index']:02d}.png"
        facts = (f"<b>#{r['index']}</b> {e(r['kind'])} ({e(r['culture'])}) in a {e(r['role'])} ({e(r['style'])}); "
                 f"{e(r['size'])}, {e(r['shape'])}; {r['tiles']} tiles, {r['doors']} door(s)<br>"
                 f"cover {f['cover']:.2f}, open {f['open']:.2f}, {f['types']} types, per tile {f['per_tile']:.2f}, "
                 f"walls {f['walls']}, lined {f['lined']:.2f}, way in {f['way_in']:.1f}")
        hard = "".join(f"<li class=hard>{e(h['text'])}</li>" for h in r["hard"])
        finds = "".join(f"<li class=find>{e(x['text'])}</li>" for x in r["findings"][:8])
        cross = "".join(f"<li class=cross>{e(x['text'])}</li>" for x in r["cross"][:3])
        warns = "".join(f"<li class=cross>checker: {e(w)}</li>" for w in r["warnings"][:3])
        out.append(f"<div class=card><a href='{img}'><img src='{img}'></a><div class=facts>{facts}<ul>{hard}{finds}"
                   f"{cross}{warns}</ul></div></div>")
    rel = os.path.relpath(labref.gallery_dir(typ), d).replace("\\", "/")
    out.append(f"<h2>Westwood's rooms of the type</h2><p><small>{e(gal['note'])}; drawn at the same scale "
               f"({gal['scale']}).</small></p><div class=gal>")
    for g in sorted(gal["rooms"], key=lambda g: (not g["own"], g["map"]))[:16]:
        out.append(f"<figure><a href='{rel}/{g['file']}'><img src='{rel}/{g['file']}'></a><figcaption>{e(g['map'])} "
                   f"{g['centre']} {e(g['type'])}, {e(g['culture'])}, {g['tiles']} tiles</figcaption></figure>")
    out.append("</div></body></html>")
    p = os.path.join(d, "index.html")
    with open(p, "w", encoding="utf-8") as fh: fh.write("\n".join(out))
    return p


if __name__ == "__main__":
    print(write(sys.argv[1], sys.argv[2]))
