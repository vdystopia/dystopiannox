"""The blind visual judge's sheet: 5 Westwood and 5 generated renders of one room type, shuffled and lettered A to J,
with the key saved apart. A vision-capable agent judges them by review/roomlab/JUDGE.md, then scores itself here.

    py review/roomlab/blind.py make  <type> <iter>              build the sheet (tests/roomlab.py does this)
    py review/roomlab/blind.py score <type> <iter> [judge.json] reveal the key, score the judge, update the scorecard

Files (review/out/roomlab/<type>/<iter>/):
    blind/A.png ... blind/J.png   the ten pictures, nothing in them but the room (look at each with the Read tool)
    blind/sheet.png               all ten, lettered, for an overview only
    blind/judge_template.json     the answer form (JUDGE.md's schema) to copy to blind/judge.json and fill in
    blind_key.json                the key: NOT in blind/; do not open it before judging
    blind/result.json             written by `score`: the key, the judge's accuracy and scores by source

The pictures: labrender.py draws Westwood's rooms and ours the same way (framing, see-through front walls, no
creatures, the surroundings blacked out, no labels). The generated five are spread over the batch's sizes and
cultures. The Westwood five (pick_westwood) are the type's own campaign rooms (its pool's when Westwood has under 5:
the key says which), each paired with a generated one by culture and by size (the same floor tiles, so neither side's
rooms look bigger), the rooms shown least on the type's earlier sheets first: the sheets rotate through Westwood's rooms
of the type, and review/out/roomlab/<type>/westwood_shown.json records which each sheet showed. Every picture of a
sheet is drawn at one scale (the smallest any of its rooms needs to fit the canvas), so no room's furniture is drawn
smaller than another's (FAIRNESS.md).
"""
import collections, json, math, os, random, shutil, sys
import labenv as E
from PIL import Image, ImageDraw, ImageFont

LETTERS = "ABCDEFGHIJ"


def font(size):
    try: return ImageFont.truetype("arialbd.ttf", size)
    except OSError: return ImageFont.load_default()


def ww_id(r):
    return f"{r['map']}:{r['centre'][0]},{r['centre'][1]}"


def shown_path(typ):
    return os.path.join(E.OUT, typ, "westwood_shown.json")


def shown(typ):
    """{iteration: [Westwood room ids its sheet showed]} for the type."""
    try:
        with open(shown_path(typ), encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError):
        return {}


def record_shown(typ, it, ids):
    led = shown(typ)
    led[it] = ids
    os.makedirs(os.path.dirname(shown_path(typ)), exist_ok=True)
    with open(shown_path(typ), "w", encoding="utf-8") as f: json.dump(led, f, indent=1)


def pick_westwood(typ, it, gens, gal):
    """Westwood's rooms for the sheet, one for each generated pick: of the same culture (a batch may hold no Dun Mir
    bedroom while Westwood has twelve: their walls alone would give the Westwood side away), the least shown on the
    type's other sheets, then the nearest in size (floor tiles, as drawn: our rooms are bigger by the kit's scale, so
    Westwood's bigger rooms of the type stand beside them); the type's own rooms before its pool's. The costs: a
    culture apart 4, a kin type's room 3, each earlier showing 1, size 2.5 per e-fold (a room a third the size
    costs as much as being shown three times before)."""
    led = shown(typ)
    uses = collections.Counter(i for k, ids in led.items() if k != it for i in ids)
    own = [r for r in gal["rooms"] if r["own"]]
    cands = own if len(own) >= len(gens) else gal["rooms"]
    chosen = []
    for g in sorted(gens, key=lambda v: (-v["floor_tiles"], v["index"])):
        left = [r for r in cands if r not in chosen]
        if not left: break
        cost = lambda r: (uses[ww_id(r)] + 4.0 * (r["culture"] != g["culture"]) + 3.0 * (not r["own"]) +
                          2.5 * abs(math.log(max(1, r["tiles"]) / max(1, g["floor_tiles"]))))
        chosen.append(min(left, key=lambda r: (round(cost(r), 6), r["map"], r["centre"])))
    return chosen


def make(typ, it, n_each=5):
    import labref, labrender as R
    d = E.iter_dir(typ, it)
    with open(os.path.join(d, "variants.json"), encoding="utf-8") as f:
        batch = json.load(f)
    rng = random.Random(E.seed_of("blind", typ, it))
    gens = [v for v in batch["variants"] if os.path.exists(os.path.join(d, "renders", f"{v['index']:02d}.png"))]
    # spread over the batch: every other variant from a seeded start, so sizes and cultures mix
    start = rng.randrange(max(1, len(gens)))
    order = gens[start:] + gens[:start]
    gal = labref.gallery(typ)
    # A thin type (Westwood has 2-4 rooms of it) is judged against its own rooms only, as many of ours as of them: a
    # sheet filled from kin types' rooms (a kitchen's labs and winch room) gives ours away for being of the type
    # (independent judge, 2026-10-06 night, FAIRNESS.md)
    own_n = sum(1 for r in gal["rooms"] if r["own"])
    if 2 <= own_n < n_each: n_each = own_n
    pick_g = (order[::2] + order[1::2])[:n_each]
    pick_w = pick_westwood(typ, it, pick_g, gal)
    items = [dict(source="generated", file=os.path.join(d, "renders", f"{v['index']:02d}.png"), variant=v["index"],
                  kind=v["kind"], culture=v["culture"], tiles=v["floor_tiles"], _v=v) for v in pick_g]
    items += [dict(source="westwood", file=os.path.join(labref.gallery_dir(typ), r["file"]), map=r["map"],
                   type=r["type"], centre=r["centre"], culture=r["culture"], tiles=r["tiles"], _w=r) for r in pick_w]
    # one scale for the sheet: the type's, or less when one of its rooms needs less to fit the canvas
    cells = {}
    if any("_v" in x for x in items):
        maps = {}
        for x in items:
            if "_v" not in x: continue
            v = x["_v"]
            if v["map"] not in maps:
                m = E.MD.load(os.path.join(d, "map", v["map"] + ".map"))
                maps[v["map"]] = (m, {r["declared"]["number"]: r for r in E.C.find_rooms(m, max_tiles=1500)
                                      if r.get("declared")})
            r = maps[v["map"]][1].get(v["number"])
            if r: cells[id(x)] = r["cells"]
    fits = [R.fit_scale(c) for c in cells.values()] + [x["_w"]["fit"] for x in items if "_w" in x]
    sheet_scale = round(min([gal["scale"]] + fits), 3)
    bd = os.path.join(d, "blind")
    if os.path.isdir(bd): shutil.rmtree(bd)
    os.makedirs(bd)
    for k, x in enumerate(items):
        if "_w" in x: drawn = x["_w"]["scale"]
        elif id(x) in cells: drawn = min(gal["scale"], R.fit_scale(cells[id(x)]))
        else: continue
        if abs(drawn - sheet_scale) < 1e-3: continue
        if "_w" in x:
            pic, _ = labref.redraw(x["_w"], sheet_scale)
        elif id(x) in cells:
            full, bare = R.lab_renders(os.path.join(d, "map", x["_v"]["map"] + ".map"))
            pic, _ = R.picture(full, bare, cells[id(x)], sheet_scale)
        else:
            continue
        x["file"] = os.path.join(bd, f"_redrawn{k}.png")
        pic.save(x["file"])
    for x in items:
        x.pop("_v", None); x.pop("_w", None)
    record_shown(typ, it, [ww_id(r) for r in pick_w])
    rng.shuffle(items)
    key = {}
    thumbs = []
    for L, it_ in zip(LETTERS, items):
        dst = os.path.join(bd, f"{L}.png")
        if os.path.dirname(it_["file"]) == bd: os.replace(it_["file"], dst)
        else: shutil.copyfile(it_["file"], dst)
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
        json.dump(dict(type=typ, iter=it, key=key, scale=sheet_scale,
                       westwood_shown=[ww_id(r) for r in pick_w]), f, indent=1)
    template = dict(type=typ, iter=it, judge="<your name or model>", pictures={
        L: dict(guess="westwood or generated", confidence=0.5, score=5, critique=["<concrete fault or strength>"])
        for L in LETTERS[:len(items)]}, overall="<what gives the generated rooms away, in one or two sentences>")
    with open(os.path.join(bd, "judge_template.json"), "w", encoding="utf-8") as f:
        json.dump(template, f, indent=1)
    return bd


def score(typ, it, judge_path=None):
    """Reveals the key against the judge's answers (blind/judge.json): accuracy, mean scores by source, the critiques
    of the generated pictures. Writes blind/result.json and returns it."""
    d = E.iter_dir(typ, it)
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
                         score=a.get("score"), critique=a.get("critique"), **{x: k.get(x) for x in
                                                                              ("variant", "map", "type", "culture", "tiles")}))
    by = lambda s: [r["score"] for r in rows if r["source"] == s and isinstance(r["score"], (int, float))]
    mean = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
    res = dict(type=typ, iter=it, judge=j.get("judge"), n=len(rows), accuracy=round(right / max(1, len(rows)), 3),
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
