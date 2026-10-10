"""Labelled pictures of the gauntlets (mapgen/designs/gauntlet.py) for a QA round: each map's whole play area with
its arenas marked (S the armoury, A1.. the arenas, B the boss) and labelled GT-NN, plus the armoury close up; and the
ModLab feature pictures (review/out/qa/modlab) and the Spirit class screenshot, as items of the round's page.

    py review/qa/gauntlet_pics.py <round>     -> review/out/qa/<round>/{gauntlets,mods}/ and items_gauntlets.json,
                                                 items_mods.json (read by page.py)
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qarender as Q                                     # noqa: E402
from PIL import Image, ImageDraw                         # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "review", "out")
GDIR = os.path.join(REPO, "mapgen", "out", "gauntlets")


def mark(img, box, centres, scale):
    d = ImageDraw.Draw(img)
    f = Q._font(26)
    for k, (x, y) in centres.items():
        X, Y = (x - box[0]) * scale, (y - box[1]) * scale
        lab = "ARMOURY" if k == "S" else "BOSS" if k == "B" else k
        w = d.textlength(lab, font=f)
        d.rounded_rectangle((X - w / 2 - 8, Y - 18, X + w / 2 + 8, Y + 18), 6, fill=(20, 18, 14), outline=(217, 180, 90), width=2)
        d.text((X - w / 2, Y - 15), lab, font=f, fill=(245, 232, 180))


def gauntlets(rnd):
    items = []
    for nm in sorted(os.listdir(GDIR)):
        info_p = os.path.join(GDIR, nm, nm + ".gauntlet.json")
        if not os.path.exists(info_p): continue
        info = json.load(open(info_p, encoding="utf-8"))
        full = Q.render_full(os.path.join(GDIR, nm, nm + ".map"))
        xs = [v[0] for v in info["centres"].values()]; ys = [v[1] for v in info["centres"].values()]
        box = (int(min(xs)) - 560, int(min(ys)) - 560, int(max(xs)) + 560, int(max(ys)) + 560)
        c = full.crop(box)
        scale = min(1600 / c.size[0], 1100 / c.size[1])
        c = c.resize((int(c.size[0] * scale), int(c.size[1] * scale)), Image.LANCZOS)
        mark(c, box, info["centres"], scale)
        cap = (f"load {info['name']} - {info['title']} - {info['setting']}, {info['layout']}, {info['arenas']} arenas - featured "
               f"{info['featured_monster']}, boss {'+'.join(info['boss'])}")
        dst = os.path.join(OUT, "qa", rnd, "gauntlets", info["id"] + ".png")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        Q.banner(c, info["id"], cap).save(dst)
        items.append(dict(id=info["id"], cat="gauntlet", type="gauntlet", png=dst, caption=cap, map=info["name"]))
    items.sort(key=lambda i: i["id"])
    dst = os.path.join(OUT, "qa", rnd, "sheets", "GT.jpg")
    Q.contact_sheet([i["png"] for i in items], dst, f"Gauntlets (GT-01..{len(items):02d})", cols=5, thumb=(640, 540))
    for i in items: i["sheet"] = dst
    return items


def mods(rnd):
    src = os.path.join(OUT, "qa", "modlab")
    items = []
    texts = {"W": "weapon", "M": "monster", "T": "training yard", "S": "forge"}
    sys.path.insert(0, os.path.join(REPO, "mapgen"))
    from kit.mods import WEAPONS, MONSTERS
    for fid in ["W1", "W2", "W3", "W4", "W5", "W6", "M1", "M2", "M3", "M4", "M5", "T1", "S1"]:
        p = os.path.join(src, fid + ".png")
        if not os.path.exists(p): continue
        cap = (WEAPONS[fid]["name"] if fid in WEAPONS else MONSTERS[fid]["name"][4:] if fid in MONSTERS else
               "Training yard" if fid == "T1" else "Smithing forge") + f" ({texts[fid[0]]}, ModLab)"
        dst = os.path.join(OUT, "qa", rnd, "mods", fid + ".png")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im = Image.open(p).convert("RGB")
        if im.size[1] > 900: im.thumbnail((1200, 900))
        im.save(dst)
        items.append(dict(id=fid, cat="mod", type="modlab", png=dst, caption=cap))
    sp = os.path.join(OUT, "qa", "spirit", "tubes_mana_vs_spirit.png")
    if os.path.exists(sp):
        dst = os.path.join(OUT, "qa", rnd, "mods", "SP1.png")
        Q.label_image(sp, "SP1", "Spirit class: mana tube (left) and cyan Spirit tube (right)", dst)
        items.append(dict(id="SP1", cat="mod", type="spirit_class", png=dst, caption="Mystic class with the cyan Spirit bar"))
    groups = {}
    for i in items: groups.setdefault(i["type"], []).append(i)
    for t, g in groups.items():
        dst = os.path.join(OUT, "qa", rnd, "sheets", f"MOD-{t.upper()}.jpg")
        Q.contact_sheet([i["png"] for i in g], dst, f"Mods: {t}", cols=5, thumb=(640, 540))
        for i in g: i["sheet"] = dst
    return items


def main(rnd):
    base = os.path.join(OUT, "qa", rnd)
    for name, fn in (("gauntlets", gauntlets), ("mods", mods)):
        items = fn(rnd)
        for i in items:
            i["png"] = os.path.relpath(i["png"], base).replace("\\", "/")
            i["sheet"] = os.path.relpath(i["sheet"], base).replace("\\", "/")
        json.dump(items, open(os.path.join(base, f"items_{name}.json"), "w", encoding="utf-8"), indent=1)
        print(f"{len(items)} {name} items")


if __name__ == "__main__":
    main(sys.argv[1])
