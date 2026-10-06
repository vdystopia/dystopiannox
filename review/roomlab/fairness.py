"""Before and after pictures of the blind sheets' fairness fixes (FAIRNESS.md), for looking at by eye.

    py review/roomlab/fairness.py [type] [before_iter] [after_iter]     (default: bedroom before fair)

Writes review/out/roomlab/_fairness/<type>_<fix>.png: each a strip of rooms, the picture as drawn before the fix above
the picture as drawn now. "before" is an iteration of the type made before the fixes (its variants had the old door
schedule), "after" one made since. The old drawing is redrawn here from the same renders with the old settings
(creatures kept, the surroundings at 0.10, the walls kept within 30 px), so only the fix differs.
"""
import json, os, sys
import labenv as E
import labref, labrender as R
from PIL import Image, ImageDraw

OUT = os.path.join(E.OUT, "_fairness")
THUMB = (480, 360)


def _font():
    from PIL import ImageFont
    try: return ImageFont.truetype("arialbd.ttf", 20)
    except OSError: return ImageFont.load_default()


def strip(rows, labels, path):
    """rows: [(name, [image, ...]) or (name, [image, ...], [label, ...])]; labels: one per column (unless the row has
    its own)."""
    W = Image.new("RGB", (THUMB[0] * len(labels), (THUMB[1] + 30) * len(rows)), (24, 24, 28))
    d = ImageDraw.Draw(W)
    for j, row in enumerate(rows):
        name, ims = row[:2]
        labs = row[2] if len(row) > 2 else labels
        for i, im in enumerate(ims):
            W.paste(im.resize(THUMB), (i * THUMB[0], j * (THUMB[1] + 30) + 30))
            d.text((i * THUMB[0] + 8, j * (THUMB[1] + 30) + 5), f"{name}: {labs[i]}", fill=(255, 215, 130),
                   font=_font())
    os.makedirs(OUT, exist_ok=True)
    W.save(path)
    print(E.rel(path))


class Old:
    """The drawing as it was before the fixes."""
    def __enter__(self):
        self.saved = (R.OUTSIDE, R.WALL_REACH)
        R.OUTSIDE, R.WALL_REACH = 0.10, 30
    def __exit__(self, *a):
        R.OUTSIDE, R.WALL_REACH = self.saved


def ww_cells(room):
    e = dict(map=room["map"], type=room["type"], culture=room["culture"], centre=room["centre"], tiles=room["tiles"],
             by_hand=room.get("by_hand"))
    _, m, r = labref.rooms_of_map(room["map"], [e])[0]
    return m, r["cells"]


def ww_pic(room, scale, creatures=False, old=False):
    m, cells = ww_cells(room)
    if creatures:
        d = os.path.join(E.REVIEW, "out", "renders")
        full = R.render_full(m.file, os.path.join(d, m.name + ".png"))
        bare = R.render_full(m.file, os.path.join(d, m.name + ".nowalls.png"), walls=False)
    else:
        full, bare = R.westwood_renders(m)
    if old:
        with Old(): return R.picture(full, bare, cells, scale)[0]
    return R.picture(full, bare, cells, scale)[0]


def gen_rooms(typ, it):
    d = E.iter_dir(typ, it)
    vs = json.load(open(os.path.join(d, "variants.json"), encoding="utf-8"))["variants"]
    path = os.path.join(d, "map", vs[0]["map"] + ".map")
    m = E.MD.load(path)
    rooms = {r["declared"]["number"]: r for r in E.C.find_rooms(m, max_tiles=1500) if r.get("declared")}
    return path, vs, rooms


def gen_pic(path, cells, scale, old=False, creatures=False):
    if creatures:
        base = os.path.splitext(path)[0]
        full = R.render_full(path, base + ".png"); bare = R.render_full(path, base + ".nowalls.png", walls=False)
    else:
        full, bare = R.lab_renders(path)
    if old:
        with Old(): return R.picture(full, bare, cells, scale)[0]
    return R.picture(full, bare, cells, scale)[0]


def creature_count(m, cells):
    C = E.MD.CELL
    cs = set(cells)
    return sum(1 for o in m.objects if "MONSTER" in o["cls"] and (int(o["x"] // C), int(o["y"] // C)) in cs)


def main(typ="bedroom", before="before", after="fair"):
    gal = labref.gallery(typ, log=lambda *_: None)
    sc = gal["scale"]
    # Westwood rooms with creatures in them
    withc = []
    for r in gal["rooms"]:
        m, cells = ww_cells(r)
        n = creature_count(m, cells)
        if n: withc.append((n, r))
    withc.sort(key=lambda t: (-t[0], t[1]["file"]))
    ww2 = [r for _, r in withc[:2]] or gal["rooms"][:2]
    path_a, vs_a, rooms_a = gen_rooms(typ, after)
    g2 = [v for v in vs_a if v["number"] in rooms_a][:2]
    cols = [f"Westwood {r['map']} {r['centre']}" for r in ww2] + [f"generated {after} #{v['index']}" for v in g2]
    strip([("before", [ww_pic(r, sc, creatures=True, old=True) for r in ww2] +
            [gen_pic(path_a, rooms_a[v["number"]]["cells"], sc, old=True, creatures=True) for v in g2]),
           ("after", [ww_pic(r, sc) for r in ww2] + [gen_pic(path_a, rooms_a[v["number"]]["cells"], sc) for v in g2])],
          cols, os.path.join(OUT, f"{typ}_1_creatures.png"))
    # the surroundings (black outside, the room's own walls only): Westwood rooms among neighbours, generated with some
    nb = sorted(gal["rooms"], key=lambda r: -r["tiles"])[:2]
    gn = sorted([v for v in vs_a if v["number"] in rooms_a], key=lambda v: -v["doors"])[:2]
    cols = [f"Westwood {r['map']} {r['centre']}" for r in nb] + [f"generated {after} #{v['index']} ({v['doors']} doors)"
                                                                  for v in gn]
    strip([("before", [ww_pic(r, sc, old=True) for r in nb] +
            [gen_pic(path_a, rooms_a[v["number"]]["cells"], sc, old=True) for v in gn]),
           ("after", [ww_pic(r, sc) for r in nb] + [gen_pic(path_a, rooms_a[v["number"]]["cells"], sc) for v in gn])],
          cols, os.path.join(OUT, f"{typ}_5_surroundings.png"))
    # doors: the same variants under the old schedule and the new
    path_b, vs_b, rooms_b = gen_rooms(typ, before)
    changed = [i for i, (a, b) in enumerate(zip(vs_a, vs_b)) if a["doors"] != b["doors"]
               and a["number"] in rooms_a and b["number"] in rooms_b][:2]
    w1 = [r for r in gal["rooms"] if r["own"]][:2]
    cols = [f"generated #{vs_a[i]['index']}: {vs_b[i]['doors']} -> {vs_a[i]['doors']} doors" for i in changed] + \
           [f"Westwood {r['map']} {r['centre']} (unchanged)" for r in w1]
    strip([("before", [gen_pic(path_b, rooms_b[vs_b[i]["number"]]["cells"], sc) for i in changed] +
            [ww_pic(r, sc) for r in w1]),
           ("after", [gen_pic(path_a, rooms_a[vs_a[i]["number"]]["cells"], sc) for i in changed] +
            [ww_pic(r, sc) for r in w1])],
          cols, os.path.join(OUT, f"{typ}_3_doors.png"))
    # scale and size: the sheets' Westwood picks before (paired at a fifth smaller, each drawn at its own fit) and now
    kb = json.load(open(os.path.join(E.iter_dir(typ, before), "blind_key.json"), encoding="utf-8"))
    ka = json.load(open(os.path.join(E.iter_dir(typ, after), "blind_key.json"), encoding="utf-8"))
    def sheet_pics(it, key, n=4):
        out, lab = [], []
        for L in sorted(key["key"])[:n]:
            out.append(Image.open(os.path.join(E.iter_dir(typ, it), "blind", f"{L}.png")).convert("RGB"))
            k = key["key"][L]; lab.append(f"{L} {k['source'][:3]} {k['tiles']} tiles")
        return out, lab
    pb, lb = sheet_pics(before, kb); pa, la = sheet_pics(after, ka)
    strip([("before", pb, lb), ("after", pa, la)], lb, os.path.join(OUT, f"{typ}_scale_sheets.png"))
    # rotation: the Westwood rooms of the type's sheets, in the order they were made
    import blind
    led = blind.shown(typ)
    rows = []
    for it, ids in list(led.items())[-2:]:
        rooms = [r for i in ids for r in gal["rooms"] if blind.ww_id(r) == i][:4]
        rows.append((it, [Image.open(os.path.join(labref.gallery_dir(typ), r["file"])).convert("RGB") for r in rooms],
                     [blind.ww_id(r) for r in rooms]))
    if len(rows) == 2:
        strip(rows, rows[0][2], os.path.join(OUT, f"{typ}_4_rotation.png"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
