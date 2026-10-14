"""Gather a QA round's ratings into one report.

    py review/qa/aggregate.py <round> <db_dir> [--shots <shots.json>]

<db_dir> holds the rating page's database as ArtifactData saved it: ratings/<ID>.json and typenotes/<key>.json.
The round's items_*.json (from package.py) give each ID its category, type and caption. Optional --shots is a
list of {"n", "file", "note"} for in-game screenshots reviewed alongside the round.

Writes review/out/qa/<round>/feedback.json (every item with its rating, verdict and note, and every set note) and
review/reviews/QA-<round>.md (per category and type: the set note, the score spread, and every per-item note).
"""
import argparse, glob, json, os, statistics
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAT_TITLES = [("room", "Rooms"), ("exterior", "Exteriors"), ("bridge", "Bridges"), ("dock", "Docks"),
              ("gauntlet", "Gauntlets"), ("mod", "Mods"), ("campaign", "Campaign")]


def load(path):
    with open(path, encoding="utf8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("round")
    ap.add_argument("db_dir")
    ap.add_argument("--shots")
    a = ap.parse_args()
    rdir = os.path.join(ROOT, "review", "out", "qa", a.round)
    items = []
    for f in sorted(glob.glob(os.path.join(rdir, "items*.json"))):
        items += load(f)
    by_id = {it["id"]: it for it in items}
    ratings = {os.path.splitext(os.path.basename(f))[0]: load(f) for f in glob.glob(os.path.join(a.db_dir, "ratings", "*.json"))}
    notes = {os.path.splitext(os.path.basename(f))[0]: load(f) for f in glob.glob(os.path.join(a.db_dir, "typenotes", "*.json"))}
    shots = load(a.shots) if a.shots else []

    rows, unknown = [], []
    for rid, r in ratings.items():
        it = by_id.get(rid)
        if not it:
            unknown.append(rid)
            continue
        if not (r.get("rating") or r.get("verdict") or (r.get("note") or "").strip()):
            continue
        rows.append({"id": rid, "cat": it["cat"], "type": it["type"], "caption": it.get("caption", ""),
                     "rating": r.get("rating"), "verdict": r.get("verdict"), "note": (r.get("note") or "").strip()})
    rows.sort(key=lambda x: x["id"])
    out = {"round": a.round, "items": rows, "typenotes": {k: v.get("note", "").strip() for k, v in sorted(notes.items())},
           "shots": shots, "unmatched_ids": sorted(unknown)}
    with open(os.path.join(rdir, "feedback.json"), "w", encoding="utf8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    groups = defaultdict(list)
    for r in rows:
        groups[(r["cat"], r["type"])].append(r)
    types = defaultdict(set)
    for it in items:
        types[it["cat"]].add(it["type"])
    L = [f"# QA {a.round}: the user's feedback", "",
         f"{len(rows)} of {len(items)} items carry a rating, verdict or note; {len(notes)} set notes"
         + (f"; {len(shots)} in-game screenshots" if shots else "") + ".",
         "Verdicts: " + ", ".join(f"{v} {sum(1 for r in rows if r['verdict'] == v)}" for v in ("keep", "fix", "drop")) + ".", ""]
    for cat, title in CAT_TITLES:
        if not types.get(cat):
            continue
        L += [f"## {title}", ""]
        for t in sorted(types[cat]):
            g = groups.get((cat, t), [])
            note = out["typenotes"].get(f"{cat}-{t}", "")
            if not g and not note:
                continue
            sc = [r["rating"] for r in g if r["rating"]]
            spread = f"mean {statistics.mean(sc):.1f} over {len(sc)} rated" if sc else "unrated"
            L += [f"### {t.replace('_', ' ')} ({spread})", ""]
            if note:
                L += ["**Whole set:** " + note.replace("\n", " "), ""]
            for r in g:
                bits = [str(r["rating"]) if r["rating"] else "-", r["verdict"] or "-"]
                L.append(f"- **{r['id']}** ({' / '.join(bits)}) {r['caption']}" + (f": {r['note']}" if r["note"] else ""))
            L.append("")
    if shots:
        L += ["## In-game screenshots", ""]
        for s in shots:
            L.append(f"{s['n']}. `{s['file']}`: {s['note']}")
        L.append("")
    if unknown:
        L += ["Ratings with no matching item: " + ", ".join(sorted(unknown)), ""]
    path = os.path.join(ROOT, "review", "reviews", f"QA-{a.round}.md")
    with open(path, "w", encoding="utf8") as f:
        f.write("\n".join(L))
    print(f"{len(rows)} items, {len(notes)} set notes -> {path}")


if __name__ == "__main__":
    main()
