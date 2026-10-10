"""Builds the QA round's review page (an Artifact): every item's picture, cut from its type's contact sheet, with a
1-5 rating, a keep/fix/drop verdict and a note, saved to the artifact's database (collection `ratings`, one doc per
item ID; `typenotes`, one per type) so Claude can read the feedback back.

    py review/qa/page.py <round>     -> review/out/qa/<round>/site/index.html + site/sheets/*.jpg
"""
import json, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CATS = [("room", "Rooms"), ("exterior", "Exteriors"), ("bridge", "Bridges"), ("dock", "Docks"), ("gauntlet", "Gauntlets"),
        ("mod", "Mods"), ("campaign", "Campaign")]
COLS, TW, TH, HEAD = 5, 640, 540, 60


def main(rnd):
    base = os.path.join(REPO, "review", "out", "qa", rnd)
    items = []
    for f in ("items_rooms.json", "items_exteriors.json", "items_bridges.json", "items_docks.json", "items_gauntlets.json", "items_mods.json", "items_campaign.json",
              "items.json"):
        p = os.path.join(base, f)
        if os.path.exists(p): items += json.load(open(p, encoding="utf-8"))
    seen, uniq = set(), []
    for i in items:
        if i["id"] not in seen: seen.add(i["id"]); uniq.append(i)
    site = os.path.join(base, "site")
    os.makedirs(os.path.join(site, "sheets"), exist_ok=True)
    by_sheet = {}
    for i in uniq: by_sheet.setdefault(i["sheet"], []).append(i)
    data = []
    for sheet, group in by_sheet.items():
        src = os.path.join(base, sheet)
        name = os.path.basename(sheet)
        im = Image.open(src).convert("RGB")
        W, H = im.size
        im.save(os.path.join(site, "sheets", name), quality=80, optimize=True)
        rows = (len(group) + COLS - 1) // COLS
        for k, i in enumerate(group):
            c, r = k % COLS, k // COLS
            y_off = HEAD + r * TH
            data.append(dict(id=i["id"], cat=i["cat"], type=i["type"], cap=i["caption"], sheet="sheets/" + name,
                             bx=round(c / (COLS - 1) * 100, 4),
                             by=round(y_off / (H - TH) * 100, 4) if H > TH else 0,
                             bs=round(W / TW * 100, 3)))
    tpl = open(os.path.join(HERE, "page_template.html"), encoding="utf-8").read()
    html = tpl.replace("/*ITEMS*/[]", json.dumps(data, separators=(",", ":"))).replace("ROUND_NAME", rnd)
    open(os.path.join(site, "index.html"), "w", encoding="utf-8").write(html)
    print(f"{len(data)} items, {len(by_sheet)} sheets -> {site}")


if __name__ == "__main__":
    main(sys.argv[1])
