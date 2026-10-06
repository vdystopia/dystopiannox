"""The blind visual judge's sheet: 5 Westwood and 5 generated pictures of one scene type, shuffled and lettered A to J,
with the key saved apart. A vision-capable agent judges them by review/scenelab/JUDGE.md, then scores itself here.
(The room lab's review/roomlab/blind.py, copied and adapted to scenes.)

    py review/scenelab/blind.py make  <scene> <iter>              build the sheet (tests/scenelab.py does this)
    py review/scenelab/blind.py score <scene> <iter> [judge.json] reveal the key, score the judge, update the scorecard

Files (review/out/scenelab/<scene>/<iter>/):
    blind/A.png ... blind/J.png   the pictures, nothing in them but the scene (look at each with the Read tool)
    blind/sheet.png               all of them, lettered, for an overview only
    blind/judge_template.json     the answer form (JUDGE.md's schema) to copy to blind/judge.json and fill in
    blind_key.json                the key: NOT in blind/; do not open it before judging
    blind/result.json             written by `score`: the key, the judge's accuracy and scores by source

The pictures: labrender.py draws Westwood's scenes and ours the same way. The generated five are spread over the
batch's sizes and sites; the Westwood five are drawn at random (seeded) from the type's campaign scenes, all of them
when it has five or fewer.
"""
import json, os, random, shutil, sys
import labenv as E
from PIL import Image, ImageDraw, ImageFont

LETTERS = "ABCDEFGHIJKL"


def font(size):
    try: return ImageFont.truetype("arialbd.ttf", size)
    except OSError: return ImageFont.load_default()


def make(scene, it, n_each=5):
    import labref
    d = E.iter_dir(scene, it)
    with open(os.path.join(d, "variants.json"), encoding="utf-8") as f:
        batch = json.load(f)
    rng = random.Random(E.seed_of("blind", scene, it))
    missing = set()
    if os.path.exists(os.path.join(d, "metrics.json")):
        with open(os.path.join(d, "metrics.json"), encoding="utf-8") as f:
            missing = {r["index"] for r in json.load(f)["scenes"] if r.get("missing")}
    gens = [v for v in batch["variants"] if os.path.exists(os.path.join(d, "renders", f"{v['index']:02d}.png"))
            and v["index"] not in missing]
    start = rng.randrange(max(1, len(gens)))
    order = gens[start:] + gens[:start]
    pick_g = (order[::2] + order[1::2])[:n_each]
    gal = labref.gallery(scene)
    ww = list(gal["scenes"])
    rng.shuffle(ww)
    pick_w = ww[:n_each]
    items = [dict(source="generated", file=os.path.join(d, "renders", f"{v['index']:02d}.png"), variant=v["index"],
                  size=v["size"], site=v["site"]) for v in pick_g]
    items += [dict(source="westwood", file=os.path.join(labref.gallery_dir(scene), s["file"]), map=s["map"], id=s["id"])
              for s in pick_w]
    rng.shuffle(items)
    bd = os.path.join(d, "blind")
    if os.path.isdir(bd): shutil.rmtree(bd)
    os.makedirs(bd)
    key, thumbs = {}, []
    for L, it_ in zip(LETTERS, items):
        dst = os.path.join(bd, f"{L}.png")
        shutil.copyfile(it_["file"], dst)
        key[L] = {k: v for k, v in it_.items() if k != "file"}
        im = Image.open(dst).convert("RGB")
        im.thumbnail((480, 360))
        thumbs.append((L, im))
    cols, cw, ch = 5, 480, 400
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows * ch), (24, 24, 28))
    dr = ImageDraw.Draw(sheet)
    for k, (L, im) in enumerate(thumbs):
        x, y = (k % cols) * cw, (k // cols) * ch
        sheet.paste(im, (x + (cw - im.width) // 2, y + 36))
        dr.text((x + 10, y + 4), L, fill=(255, 215, 130), font=font(26))
    sheet.save(os.path.join(bd, "sheet.png"))
    with open(os.path.join(d, "blind_key.json"), "w", encoding="utf-8") as f:
        json.dump(dict(scene=scene, iter=it, key=key), f, indent=1)
    template = dict(scene=scene, iter=it, judge="<your name or model>", pictures={
        L: dict(guess="westwood or generated", confidence=0.5, score=5, critique=["<concrete fault or strength>"])
        for L in LETTERS[:len(items)]}, overall="<what gives the generated scenes away, in one or two sentences>")
    with open(os.path.join(bd, "judge_template.json"), "w", encoding="utf-8") as f:
        json.dump(template, f, indent=1)
    return bd


def score(scene, it, judge_path=None):
    """Reveals the key against the judge's answers (blind/judge.json): accuracy, mean scores by source. Writes
    blind/result.json and returns it."""
    d = E.iter_dir(scene, it)
    judge_path = judge_path or os.path.join(d, "blind", "judge.json")
    with open(judge_path, encoding="utf-8") as f: j = json.load(f)
    with open(os.path.join(d, "blind_key.json"), encoding="utf-8") as f: key = json.load(f)["key"]
    rows, right = [], 0
    for L, k in sorted(key.items()):
        a = j["pictures"].get(L)
        if not a: continue
        guess = str(a.get("guess", "")).lower().strip()
        ok = guess.startswith(k["source"][:3])
        right += ok
        rows.append(dict(letter=L, source=k["source"], guess=guess, correct=ok, confidence=a.get("confidence"),
                         score=a.get("score"), critique=a.get("critique"),
                         **{x: k.get(x) for x in ("variant", "map", "id", "size", "site")}))
    by = lambda s: [r["score"] for r in rows if r["source"] == s and isinstance(r["score"], (int, float))]
    mean = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
    res = dict(scene=scene, iter=it, judge=j.get("judge"), n=len(rows), accuracy=round(right / max(1, len(rows)), 3),
               score_generated=mean(by("generated")), score_westwood=mean(by("westwood")), overall=j.get("overall"),
               pictures=rows)
    with open(os.path.join(d, "blind", "result.json"), "w", encoding="utf-8") as f: json.dump(res, f, indent=1)
    return res


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "make":
        print(make(sys.argv[2], sys.argv[3]))
    elif len(sys.argv) >= 4 and sys.argv[1] == "score":
        r = score(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
        print(f"accuracy {r['accuracy']:.0%} over {r['n']} pictures; mean score generated {r['score_generated']}, "
              f"Westwood {r['score_westwood']}")
        import scorecard
        print(scorecard.write(sys.argv[2], sys.argv[3]))
    else:
        print(__doc__)
