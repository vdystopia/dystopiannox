"""The previous round beside the new one on the rating page: per type, a strip of five pictures from the previous
round, its mean rating, the user's set note on it, and one line on what changed (review/qa/changes/<round>.json).

    py review/qa/context.py <prev> <round>   -> review/out/qa/<round>/before/<cat>-<type>.jpg + context.json

page.py embeds context.json when it exists. Types split out of an older one (coven from chapel) show the parent's
pictures, rating and note. A type re-rendered in part with its labels kept (round 4's three cobble-road bridges of
round 3's fifteen) shows those same items of the previous round and their mean.
"""
import collections, json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
Q = os.path.join(os.path.dirname(os.path.dirname(HERE)), "review", "out", "qa")
CELL = (560, 440)
SPLIT = {"coven": "chapel", "mana_room": "chapel", "ogre_den": "barracks", "ogre_pen": "cell"}


def load_items(rnd):
    base, items = os.path.join(Q, rnd), []
    for f in ("items_rooms.json", "items_exteriors.json", "items_bridges.json", "items_docks.json", "items.json"):
        p = os.path.join(base, f)
        if os.path.exists(p): items += json.load(open(p, encoding="utf-8"))
    seen, out = set(), []
    for i in items:
        if i["id"] not in seen: seen.add(i["id"]); out.append(i)
    return out


def crop(im):
    b = ImageOps.grayscale(im).point(lambda v: 255 if v > 30 else 0).getbbox()
    if not b: return im
    return im.crop((max(0, b[0] - 12), max(0, b[1] - 12), min(im.width, b[2] + 12), min(im.height, b[3] + 12)))


def strip(items, base, dst, font):
    sheet = Image.new("RGB", (CELL[0] * 5, CELL[1]), (18, 18, 22))
    d = ImageDraw.Draw(sheet)
    for k, it in enumerate(items[:5]):
        im = Image.open(os.path.join(base, it["png"])).convert("RGB")
        im = im.crop((0, 56 if it["cat"] == "room" else 44, im.width, im.height))   # the package's own label strip
        if it["cat"] == "room": im = crop(im)
        im.thumbnail((CELL[0] - 12, CELL[1] - 40), Image.LANCZOS)
        sheet.paste(im, (k * CELL[0] + (CELL[0] - im.width) // 2, 34 + (CELL[1] - 40 - im.height) // 2))
        d.text((k * CELL[0] + 10, 6), it["id"], font=font, fill=(235, 225, 200))
    sheet.save(dst, quality=80, optimize=True)


def main(prev, rnd):
    out = os.path.join(Q, rnd)
    os.makedirs(os.path.join(out, "before"), exist_ok=True)
    fb = json.load(open(os.path.join(Q, prev, "feedback.json"), encoding="utf-8"))
    rate = collections.defaultdict(list)
    by_prev, by_new = collections.defaultdict(list), collections.defaultdict(list)
    for it in load_items(prev): by_prev[(it["cat"], it["type"])].append(it)
    for it in load_items(rnd): by_new[(it["cat"], it["type"])].append(it)
    # a type re-rendered in part with its labels kept (round 4: BR-01, BR-06, BR-11 of round 3's fifteen) is shown
    # beside those same items of the previous round, and their mean
    part = {}
    for (cat, t), new in by_new.items():
        src, ids = (cat, SPLIT.get(t, t)), {i["id"] for i in new}
        same = [i for i in by_prev.get(src, []) if i["id"] in ids]
        if same and len(same) < len(by_prev[src]):
            by_prev[src] = same
            part[src] = {i["id"] for i in same}
    for it in fb["items"]:
        src = (it["cat"], it["type"])
        if it.get("rating") and (src not in part or it["id"] in part[src]): rate[src].append(it["rating"])
    cp = os.path.join(HERE, "changes", rnd + ".json")
    changes = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
    try: font = ImageFont.truetype("arialbd.ttf", 22)
    except OSError: font = ImageFont.load_default()
    ctx = {"_prev": prev, "_intro": changes.get("_intro", [])}
    for (cat, t) in by_new:
        src = (cat, SPLIT.get(t, t))
        before, rs = by_prev.get(src, []), rate.get(src, [])
        slug = f"{cat}-{t}"
        if before: strip(before, os.path.join(Q, prev), os.path.join(out, "before", slug + ".jpg"), font)
        ckey = t + ("__ext" if cat == "exterior" and t == "shrine" else "")
        ctx[slug] = dict(split=SPLIT.get(t), before=f"before/{slug}.jpg" if before else None,
                         ids_before=[i["id"] for i in before[:5]], rated=len(rs),
                         avg=round(sum(rs) / len(rs), 1) if rs else None,
                         note=fb["typenotes"].get(f"{src[0]}-{src[1]}", ""), change=changes.get(ckey, ""))
    json.dump(ctx, open(os.path.join(out, "context.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{len(ctx) - 2} types, {sum(1 for k, v in ctx.items() if not k.startswith('_') and v['before'])} strips -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
