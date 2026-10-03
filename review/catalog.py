"""Object catalog: renders game objects side by side with their names, to choose by eye.

    py review/catalog.py <name or regex> [<name or regex> ...] [--out file.png]

Builds a small map (review/out/catalog/Catalog.map) with each matching object on a floor tile grid,
renders it with the editor and writes a labelled contact sheet (default review/out/catalog/catalog.png).
"""
import os, re, sqlite3, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "mapgen"))
from nox import Spec, SOLO, px
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(HERE, "out", "catalog")
EDITOR = os.path.join(REPO, "MapEditor", "bin", "Release", "MapEditor.exe")
STEP = 10                     # uv units between objects (about 160 px)


def names(patterns):
    with sqlite3.connect(os.path.join(REPO, "corpus", "out", "nox_corpus.db")) as db:
        allnames = [r[0] for r in db.execute("SELECT name FROM things")]
    out = []
    for p in patterns:
        hits = [n for n in allnames if n == p] or sorted(n for n in allnames if re.search(p, n))
        out += [h for h in hits if h not in out]
    return out


def build(types, cols=6):
    rows = (len(types) + cols - 1) // cols
    m = Spec("Catalog", summary="catalog", description="catalog", author="catalog", version="0", date="2026",
             type=SOLO, minPlayers=1, maxPlayers=1)
    m.d["nxz"] = False
    m.d["ambient"] = [255, 255, 255]
    u0, v0 = 200, -40
    m.room(u0, u0 + STEP * cols + 4, v0, v0 + STEP * rows + 4, wall="StuccoLightWood", floor="WoodLight2")
    spots = []
    for k, t in enumerate(types):
        u, v = u0 + 6 + STEP * (k % cols), v0 + 6 + STEP * (k // cols)
        x, y = px(u, v)
        m.obj_px(t, x, y)
        spots.append((t, x, y))
    m.obj("PlayerStart", u0 + 2, v0 + 2)
    m.build(OUT, check=False)
    return os.path.join(OUT, "Catalog.map"), spots


def sheet(types, out_png):
    path, spots = build(types)
    full = os.path.join(OUT, "_render.png")
    if os.path.exists(full): os.remove(full)
    subprocess.run([EDITOR, path, "--render-image", full, "full:5880"], timeout=600)
    im = Image.open(full).convert("RGB")
    try: f = ImageFont.truetype("arialbd.ttf", 15)
    except OSError: f = ImageFont.load_default()
    cell, cols = 240, 6
    canvas = Image.new("RGB", (cell * cols, cell * ((len(spots) + cols - 1) // cols)), (16, 16, 18))
    d = ImageDraw.Draw(canvas)
    for k, (t, x, y) in enumerate(spots):
        c = im.crop((int(x - 110), int(y - 150), int(x + 110), int(y + 60)))
        X, Y = (k % cols) * cell, (k // cols) * cell
        canvas.paste(c, (X + 10, Y + 24))
        d.text((X + 8, Y + 4), t, fill=(255, 215, 130), font=f)
    canvas.save(out_png)
    os.remove(full)
    return out_png


if __name__ == "__main__":
    args = sys.argv[1:]
    out = os.path.join(OUT, "catalog.png")
    if "--out" in args:
        out = args[args.index("--out") + 1]; args = args[:args.index("--out")]
    os.makedirs(OUT, exist_ok=True)
    ts = names(args)
    print(f"{len(ts)} objects: {' '.join(ts)}")
    print(sheet(ts, out))
