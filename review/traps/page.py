"""The trap rating page: every TrapLab station (TL-<KIND>-NN), every gauntlet (TG-NN) and every mission (TD-NN) with
its picture, what it is, how it is meant to be passed and what the simulator and the in-game tour found, rated on the
QA rounds' page (review/qa/page_template.html: 1-5, keep/fix/drop, a note; a note per type).

    py review/traps/page.py <round> <built_dir> [<built_dir> ...]

Each built_dir holds a built trap map (<Name>.map, <Name>.lab.json, and if run <Name>.sim.json / <Name>.tour.json).
Writes review/out/qa/<round>/ (renders/, sheets/, items_traps.json) and site/index.html; publish the site folder.
"""
import json, math, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
EDITOR = os.path.join(REPO, "MapEditor", "bin", "Release", "MapEditor.exe")
COLS, TW, TH, HEAD = 5, 640, 540, 60
SCALE = {"TL": 1.5, "TG": 3, "TD": 3}    # a sheet's cells at this many times the page's cell: the zoomed view keeps detail
CATS = [("traplab", "TrapLab"), ("trapgaunt", "TrapGaunt"), ("trapdemo", "TrapDemo")]
Image.MAX_IMAGE_PIXELS = None


def font(n):
    for f in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try: return ImageFont.truetype(f, n)
        except OSError: pass
    return ImageFont.load_default()


def render(map_path, png):
    if not os.path.exists(png):
        subprocess.run([EDITOR, os.path.abspath(map_path), "--render-image", os.path.abspath(png), "full:5880"],
                       check=True, capture_output=True)
    return Image.open(png).convert("RGB")


def fit(im, w, h):
    im = im.copy()
    im.thumbnail((w, h))
    cell = Image.new("RGB", (w, h), (12, 12, 14))
    cell.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return cell


def crop_box(pts, pad=60):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return int(min(xs) - pad), int(min(ys) - pad), int(max(xs) + pad), int(max(ys) + pad)


def station_corners(st):
    (sx, sy), (ux, uy), (vx, vy) = st["start"], st["along"], st["across"]
    ox, oy = sx - 0.5 * 32.5 * ux - st["W"] / 2 * 32.5 * vx, sy - 0.5 * 32.5 * uy - st["W"] / 2 * 32.5 * vy
    return [(ox + 32.5 * (a * ux + b * vx), oy + 32.5 * (a * uy + b * vy)) for a in (0, st["L"]) for b in (0, st["W"])]


def sheet(cells, title, path, k=1.0):
    tw, th, head = int(TW * k), int(TH * k), int(HEAD * k)
    rows = (len(cells) + COLS - 1) // COLS
    S = Image.new("RGB", (COLS * tw, head + rows * th), (20, 20, 24))
    d = ImageDraw.Draw(S)
    d.text((int(16 * k), int(14 * k)), title, fill=(235, 225, 200), font=font(int(30 * k)))
    f = font(int(22 * k))
    bar = int(40 * k)
    for n, (label, im) in enumerate(cells):
        c, r = n % COLS, n // COLS
        x, y = c * tw, head + r * th
        S.paste(fit(im, tw - 8, th - bar - 6), (x + 4, y + bar + 2))
        d.rectangle((x + 2, y + 2, x + tw - 3, y + bar), fill=(40, 34, 26))
        d.text((x + int(12 * k), y + int(8 * k)), label, fill=(250, 215, 140), font=f)
    S.save(path, quality=85)


def focus(im, box, corners, pad=26):
    """The crop with everything outside the station (its floor and walls, pad px round) dimmed: the neighbours that
    the square crop takes in stay readable as context but do not compete."""
    c = im.crop(box)
    m = Image.new("L", c.size, 0)
    cx = sum(p[0] for p in corners) / 4
    cy = sum(p[1] for p in corners) / 4
    pts = []
    for x, y in (corners[0], corners[1], corners[3], corners[2]):      # round the quad in order
        dx, dy = x - cx, y - cy
        n = math.hypot(dx, dy) or 1
        pts.append((x - box[0] + dx / n * pad, y - box[1] + dy / n * pad))
    ImageDraw.Draw(m).polygon(pts, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(6))
    dim = c.point(lambda v: int(v * 0.35))
    return Image.composite(c, dim, m)


def caption(st, sim, tour):
    m = st.get("meta") or {}
    s = f"{st['title']} ({st.get('tier', '')}). {m.get('tells', '')}. The answer: {m.get('answer', '')}."
    if sim:
        s += (f" Simulated: a careful plan costs {sim.get('replay', sim.get('plan'))} HP, a careless walk "
              f"{sim.get('careless_walk')} ({sim.get('careless_walk_outcome')}), a run {sim.get('careless_run')}; "
              f"{sim.get('verdict')}.")
    if tour:
        g = tour.get("game", {})
        if g.get("plan"):
            s += f" In the game: plan {g['plan'][0]} HP {g['plan'][1]}"
            if g.get("walk"): s += f", careless walk {g['walk'][0]} HP {g['walk'][1]}"
            s += "."
    return s


def main(rnd, dirs):
    base = os.path.join(REPO, "review", "out", "qa", rnd)
    for sub in ("renders", "sheets", "site/sheets"):
        os.makedirs(os.path.join(base, sub), exist_ok=True)
    items, sheets = [], {}
    for bdir in dirs:
        lab = next((f for f in os.listdir(bdir) if f.endswith(".lab.json")), None)
        if not lab: continue
        info = json.load(open(os.path.join(bdir, lab), encoding="utf-8"))
        name = info["name"]
        im = render(os.path.join(bdir, name + ".map"), os.path.join(base, "renders", name + ".png"))
        bb = im.convert("L").point(lambda v: 255 if v > 8 else 0).getbbox()
        sims = {r["label"]: r for r in json.load(open(os.path.join(bdir, name + ".sim.json")))} \
            if os.path.exists(os.path.join(bdir, name + ".sim.json")) else {}
        tours = {r["label"]: r for r in json.load(open(os.path.join(bdir, name + ".tour.json")))} \
            if os.path.exists(os.path.join(bdir, name + ".tour.json")) else {}
        if name.startswith("TL"):
            kind = info["kind"]
            cells = []
            for st in info["stations"]:
                corners = station_corners(st)
                box = crop_box(corners)
                cells.append((f"{st['label']}  {st['title']}", focus(im, box, corners)))
                items.append(dict(id=st["label"], cat="traplab", type=kind,
                                  caption=caption(st, sims.get(st["label"]), tours.get(st["label"])),
                                  sheet=f"sheets/TL-{kind}.jpg"))
            sheet(cells, f"TrapLab {name}: {kind}", os.path.join(base, "sheets", f"TL-{kind}.jpg"), SCALE["TL"])
        else:
            cat = "trapgaunt" if name.startswith("TrapGnt") else "trapdemo"
            iid = info.get("id") or ("TD-" + name[-2:])
            def stage(s):
                g = (tours.get(s["label"]) or {}).get("game") or {}
                out = f"{s['label'].split('-')[-1]} {s['title']} ({s['kind'] if 'kind' in s else ''}{', ' if 'kind' in s else ''}{s['tier']}"
                if g.get("plan"):
                    out += f"; in the game a careful pass cost {g['plan'][0]} HP ({g['plan'][1]})"
                    if g.get("walk"): out += f", a careless walk {g['walk'][0]} HP ({g['walk'][1]})"
                out += ")"
                return out
            stages = "; ".join(stage(s) for s in info["stations"])
            cap = f"{info.get('title', name)}: {len(info['stations'])} trap stages ({stages})"
            if info.get("creatures") is not None:
                cap += f"; creatures {info['creatures']}"
            cap += "."
            key = "TG" if cat == "trapgaunt" else "TD"
            sheets.setdefault(key, []).append((f"{iid}  {info.get('title', name)}", im.crop(bb)))
            items.append(dict(id=iid, cat=cat, type="gauntlet" if cat == "trapgaunt" else "mission", caption=cap,
                              sheet=f"sheets/{key}.jpg"))
    for key, cells in sheets.items():
        sheet(cells, "TrapGaunt: the gauntlets" if key == "TG" else "TrapDemo: the missions",
              os.path.join(base, "sheets", f"{key}.jpg"), SCALE[key])
    json.dump(items, open(os.path.join(base, "items_traps.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    # the page: the QA template with the trap tabs
    sys.path.insert(0, os.path.join(REPO, "review", "qa"))
    by_sheet = {}
    for i in items: by_sheet.setdefault(i["sheet"], []).append(i)
    data = []
    for sh, group in by_sheet.items():
        src = os.path.join(base, sh)
        imx = Image.open(src).convert("RGB")
        W, H = imx.size
        k = SCALE[os.path.basename(sh).split("-")[0].split(".")[0]]
        tw, th, head = int(TW * k), int(TH * k), int(HEAD * k)
        imx.save(os.path.join(base, "site", "sheets", os.path.basename(sh)), quality=80, optimize=True)
        for n, i in enumerate(group):
            c, r = n % COLS, n // COLS
            y_off = head + r * th
            data.append(dict(id=i["id"], cat=i["cat"], type=i["type"], cap=i["caption"], sheet="sheets/" + os.path.basename(sh),
                             bx=round(c / (COLS - 1) * 100, 4), by=round(y_off / (H - th) * 100, 4) if H > th else 0,
                             bs=round(W / tw * 100, 3)))
    tpl = open(os.path.join(REPO, "review", "qa", "page_template.html"), encoding="utf-8").read()
    cats_js = json.dumps([list(c) for c in CATS])
    tpl = re.sub(r"const CATS = \[.*?\];", f"const CATS = {cats_js};", tpl, count=1)
    tpl = tpl.replace('cat = "room";', 'cat = "traplab";').replace('localStorage.getItem("qa-cat")', 'localStorage.getItem("trap-cat")') \
             .replace('localStorage.setItem("qa-cat", k)', 'localStorage.setItem("trap-cat", k)')
    html = (tpl.replace("/*ITEMS*/[]", json.dumps(data, separators=(",", ":")))
               .replace("/*CONTEXT*/{}", "{}").replace("ROUND_NAME", rnd))
    open(os.path.join(base, "site", "index.html"), "w", encoding="utf-8").write(html)
    print(f"{len(data)} items, {len(by_sheet)} sheets -> {os.path.join(base, 'site')}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
