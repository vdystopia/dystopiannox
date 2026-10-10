"""Packages a QA round for the user's review: every room, exterior scene, bridge and dock picture labelled with a stable
ID, one contact sheet per type, and items.json (every ID with its type, sheet, picture and caption).

    py review/qa/package.py <round> [--room-iter qa1] [--scene-iter qa1] [--dock-iters qa1,qa1b]

Labels: RM-<TYPE>-NN (rooms), EX-<TYPE>-NN (exteriors), BR-NN (bridges), DK-NN (docks), e.g. RM-LIBRARY-03.
Writes review/out/qa/<round>/{rooms,exteriors,bridges,docks}/<label>.png, sheets/<group>.jpg and items.json.
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qarender as Q                                         # noqa: E402
from PIL import Image                                        # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "review", "out")


def code(t):
    return t.upper().replace("_", "")


def room_caption(v):
    return f"{v.get('kind', '')} - {v.get('size')} {v.get('shape')} {v.get('floor_tiles', '?')} tiles - " \
           f"{v.get('culture')} - {v.get('style', '').replace('_', ' ')}"


def scene_caption(v):
    return f"{v.get('kind') or v.get('archetype') or ''} {v.get('size')} - site {v.get('site')} - {v.get('forest')} wood".strip()


def rooms(rnd, it, items):
    base = os.path.join(OUT, "roomlab")
    for t in sorted(os.listdir(base)):
        vf = os.path.join(base, t, it, "variants.json")
        if not os.path.exists(vf): continue
        vs = json.load(open(vf, encoding="utf-8"))["variants"]
        group = []
        for v in vs:
            src = os.path.join(base, t, it, "renders", f"{v['index']:02d}.png")
            if not os.path.exists(src): continue
            label = f"RM-{code(t)}-{v['index']:02d}"
            dst = Q.label_image(src, label, room_caption(v), os.path.join(OUT, "qa", rnd, "rooms", t, label + ".png"))
            group.append(dict(id=label, cat="room", type=t, png=dst, caption=room_caption(v)))
        items += group
        if group: sheet(rnd, f"RM-{code(t)}", f"Rooms: {t.replace('_', ' ')} (RM-{code(t)}-01..{len(group):02d})", group)


def scene_window(v):
    w = max(900, int(2.4 * v.get("reach", 380)))
    return w, int(w * 0.75)


def exteriors(rnd, it, items, only=None, prefix=None, iters=None):
    base = os.path.join(OUT, "scenelab")
    for t in sorted(os.listdir(base)):
        if t.startswith("_") or (only and t != only) or (not only and t == "pond_dock"): continue
        group, n = [], 0
        for it_ in (iters or [it]):
            d = os.path.join(base, t, it_)
            vf = os.path.join(d, "variants.json")
            if not os.path.exists(vf): continue
            data = json.load(open(vf, encoding="utf-8"))
            mp = os.path.join(REPO, data["maps"][0]) if "maps" in data else None
            mname = os.path.splitext(os.path.basename(mp))[0]
            clean = os.path.join(os.path.dirname(mp), "clean", mname + ".png")
            full = Image.open(clean if os.path.exists(clean) else Q.render_full(mp)).convert("RGB") \
                if os.path.exists(clean) else Q.render_full(mp)
            for v in data["variants"]:
                n += 1
                label = f"{prefix}-{n:02d}" if prefix else f"EX-{code(t)}-{n:02d}"
                cap = scene_caption(v)
                w, h = scene_window(v)
                x, y = v["anchor"]
                dst = os.path.join(OUT, "qa", rnd, "docks" if prefix else "exteriors", "" if prefix else t)
                p = Q.crop_labelled(None, [(label, (x, y), cap)], dst, window=(w, h), full=full)[0]
                im = Image.open(p)
                if im.size[0] > 1000:                       # one size for every picture
                    im = im.resize((1000, int(im.size[1] * 1000 / im.size[0])), Image.LANCZOS); im.save(p)
                group.append(dict(id=label, cat="dock" if prefix else "exterior", type=t, png=p, caption=cap))
        items += group
        if group:
            key = prefix or f"EX-{code(t)}"
            sheet(rnd, key, (f"Docks in ponds ({prefix}-01..{len(group):02d})" if prefix else
                             f"Exteriors: {t.replace('_', ' ')} ({key}-01..{len(group):02d})"), group)


def bridges(rnd, items):
    d = os.path.join(OUT, "qa", "bridges")
    data = json.load(open(os.path.join(d, "variants.json"), encoding="utf-8"))
    sys.path.insert(0, HERE)
    import bridgelab
    group = []
    for v in data["variants"]:
        src = os.path.join(d, "renders", v["label"] + ".png")
        dst = os.path.join(OUT, "qa", rnd, "bridges", v["label"] + ".png")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        Image.open(src).save(dst)
        group.append(dict(id=v["label"], cat="bridge", type="bridge", png=dst, caption=bridgelab.describe(v)))
    items += group
    sheet(rnd, "BR", f"Bridges over a river (BR-01..{len(group):02d})", group)


def sheet(rnd, key, title, group):
    dst = os.path.join(OUT, "qa", rnd, "sheets", key + ".jpg")
    Q.contact_sheet([g["png"] for g in group], dst, title, cols=5, thumb=(640, 540))
    for g in group: g["sheet"] = dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("round")
    ap.add_argument("--room-iter", default="qa1")
    ap.add_argument("--scene-iter", default="qa1")
    ap.add_argument("--dock-iters", default="qa1,qa1b")
    ap.add_argument("--only", choices=("rooms", "exteriors", "bridges", "docks"))
    a = ap.parse_args()
    items = []
    if a.only in (None, "rooms"): rooms(a.round, a.room_iter, items)
    if a.only in (None, "exteriors"): exteriors(a.round, a.scene_iter, items, prefix="")
    if a.only in (None, "bridges"): bridges(a.round, items)
    if a.only in (None, "docks"): exteriors(a.round, None, items, only="pond_dock", prefix="DK", iters=a.dock_iters.split(","))
    for i in items:
        i["png"] = os.path.relpath(i["png"], os.path.join(OUT, "qa", a.round)).replace("\\", "/")
        i["sheet"] = os.path.relpath(i["sheet"], os.path.join(OUT, "qa", a.round)).replace("\\", "/")
    path = os.path.join(OUT, "qa", a.round, f"items{'_' + a.only if a.only else ''}.json")
    json.dump(items, open(path, "w", encoding="utf-8"), indent=1)
    print(f"{len(items)} items -> {path}")


if __name__ == "__main__":
    main()
