"""A story map's overview for the playtester: the whole map, with each named story object (quest givers, bosses,
gates, exits, the start) marked and labelled, and a legend of who they are.

    py review/storymap.py <map> [--size 1800] [--out file.png]

Labels come from the script names in the map (Tobin, Garrick, NorthGate1, ...); numbered groups (Lookout1-4,
Folk1-8) are marked once each, labelled by their stem. Writes review/out/<map>/storymap.png and prints its path.
"""
import argparse, collections, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "validate"))
import mapdata as MD

EDITOR = os.path.join(REPO, "MapEditor", "bin", "Release", "MapEditor.exe")
KIND_COLOUR = {"start": (120, 230, 120), "npc": (255, 220, 140), "foe": (255, 110, 100), "gate": (150, 190, 255),
               "exit": (150, 190, 255), "chest": (230, 200, 90)}


def kind_of(o):
    t, c = o["type"], o["cls"]
    if t == "PlayerStart": return "start"
    if t == "InvisibleExitArea": return "exit"
    if "DOOR" in c: return "gate"
    if "MONSTER" in c:
        return "npc" if (t in ("NPC", "Maiden") or t.startswith("Shopkeeper")) else "foe"
    return "chest"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map"); ap.add_argument("--size", type=int, default=1800); ap.add_argument("--out")
    a = ap.parse_args()
    m = MD.load(a.map)
    name = os.path.splitext(os.path.basename(a.map))[0]
    out_dir = os.path.join(HERE, "out", name); os.makedirs(out_dir, exist_ok=True)
    full = os.path.join(out_dir, "full.png")
    if not os.path.exists(full) or os.path.getmtime(full) < os.path.getmtime(a.map):
        subprocess.run([EDITOR, a.map, "--render-image", full, "full:5880"], timeout=900)
    im = Image.open(full).convert("RGB")
    # crop to the land (non-black) with a margin, then scale
    bbox = im.point(lambda v: 255 if v > 12 else 0).getbbox() or (0, 0, im.width, im.height)
    pad = 60
    x0, y0, x1, y1 = max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(im.width, bbox[2] + pad), min(im.height, bbox[3] + pad)
    im = im.crop((x0, y0, x1, y1))
    k = a.size / max(im.size)
    im = im.resize((int(im.width * k), int(im.height * k)))
    d = ImageDraw.Draw(im)
    try: font = ImageFont.truetype("arialbd.ttf", 16)
    except OSError: font = ImageFont.load_default()
    seen = set()
    marks = []
    for o in m.objects:
        scr = (o.get("scr") or "").split(":")[-1]
        if o["type"] == "PlayerStart": scr = "Start"
        if not scr: continue
        stem = re.sub(r"\d+$", "", scr)
        key = stem if re.search(r"\d$", scr) else scr
        if key in seen: continue
        seen.add(key)
        marks.append((key, kind_of(o), (o["x"] - x0) * k, (o["y"] - y0) * k))
    for key, kd, x, y in marks:
        col = KIND_COLOUR.get(kd, (255, 255, 255))
        d.ellipse((x - 7, y - 7, x + 7, y + 7), outline=(0, 0, 0), width=4)
        d.ellipse((x - 7, y - 7, x + 7, y + 7), outline=col, width=2)
        for dx, dy in ((-1, -1), (1, 1), (-1, 1), (1, -1)):
            d.text((x + 10 + dx, y - 9 + dy), key, fill=(0, 0, 0), font=font)
        d.text((x + 10, y - 9), key, fill=col, font=font)
    d.rectangle((0, 0, 560, 30), fill=(12, 12, 14))
    d.text((10, 6), f"{name}: green start, gold people, red foes, blue gates/exits", fill=(230, 230, 230), font=font)
    out = a.out or os.path.join(out_dir, "storymap.png")
    im.save(out)
    print(out)


if __name__ == "__main__":
    main()
