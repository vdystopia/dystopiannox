"""Close-ups of a map's named objects (quest givers, camps, gates): the whole map rendered once by the editor, then a
square crop round each named object, labelled, side by side on one sheet.

    py review/spots.py <map> <script name> [<script name> ...] [--size 700] [--out sheet.png] [--nowalls]

Script names are matched case-insensitively as prefixes ("Lookout" finds Lookout1). Each crop is centred on the first
match. Writes review/out/<map>/spots.png (or --out) and prints its path.
"""
import argparse, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "validate"))
import mapdata as MD

EDITOR = os.path.join(REPO, "MapEditor", "bin", "Release", "MapEditor.exe")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map"); ap.add_argument("names", nargs="+")
    ap.add_argument("--size", type=int, default=700); ap.add_argument("--out")
    ap.add_argument("--nowalls", action="store_true")
    ap.add_argument("--cols", type=int, default=3)
    a = ap.parse_args()
    m = MD.load(a.map)
    name = os.path.splitext(os.path.basename(a.map))[0]
    out_dir = os.path.join(HERE, "out", name); os.makedirs(out_dir, exist_ok=True)
    full = os.path.join(out_dir, "full_nowalls.png" if a.nowalls else "full.png")
    if not os.path.exists(full) or os.path.getmtime(full) < os.path.getmtime(a.map):
        subprocess.run([EDITOR, a.map, "--render-image", full, "full:5880"] + (["nowalls"] if a.nowalls else []), timeout=900)
    im = Image.open(full).convert("RGB")
    crops = []
    for n in a.names:
        o = next((o for o in m.objects if (o.get("scr") or "").split(":")[-1].lower().startswith(n.lower())), None)
        if not o:
            print(f"no object named {n}"); continue
        h = a.size // 2
        c = im.crop((int(o["x"]) - h, int(o["y"]) - h, int(o["x"]) + h, int(o["y"]) + h))
        d = ImageDraw.Draw(c)
        d.rectangle((0, 0, a.size, 26), fill=(15, 15, 18))
        d.text((8, 6), f"{n}: {o['type']} at ({o['x']:.0f}, {o['y']:.0f})", fill=(255, 220, 140))
        crops.append(c)
    if not crops: return
    cols = min(a.cols, len(crops)); rows = (len(crops) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * a.size, rows * a.size), (10, 10, 12))
    for k, c in enumerate(crops): sheet.paste(c, ((k % cols) * a.size, (k // cols) * a.size))
    out = a.out or os.path.join(out_dir, "spots.png")
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
