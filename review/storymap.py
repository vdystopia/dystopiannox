"""A story map's overview for the playtester: the whole map, with each named story object (quest givers, bosses,
gates, exits, the start) marked and labelled, and a legend of who they are.

    py review/storymap.py <map> [--size 1800] [--out file.png]
    py review/storymap.py <map> --routes [--who Name,Name]   # the routes people walk (<map>.routes.json), close up

With --routes it draws, cropped to the town, every route the scripts walk: a line per person through its waypoints
(legs that the checker faults in red), a dot at each stop sized by how long they stand there, an arrow the way they
face there (red where it faces into something), and the person's name at the start. Writes review/out/<map>/routes.png.

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
    ap.add_argument("--routes", action="store_true"); ap.add_argument("--who")
    a = ap.parse_args()
    if a.routes: return routes(a)
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


ROUTE_COLOURS = [(255, 255, 255), (90, 200, 255), (255, 210, 60), (150, 255, 120), (230, 120, 255), (255, 150, 60),
                 (80, 255, 220), (255, 120, 190), (180, 180, 255), (220, 255, 90)]


def routes(a):
    sys.path.insert(0, os.path.join(REPO, "mapgen"))
    from kit.walkways import Ground, facing_problem
    import json, math
    m = MD.load(a.map)
    name = os.path.splitext(os.path.basename(a.map))[0]
    side = os.path.splitext(a.map)[0] + ".routes.json"
    rs = json.load(open(side, encoding="utf-8"))
    if a.who: rs = [r for r in rs if r["who"] in a.who.split(",")]
    wp = {w["name"].split(":")[-1]: (w["x"], w["y"]) for w in m.waypoints}
    g = Ground.from_mapdata(m)
    out_dir = os.path.join(HERE, "out", name); os.makedirs(out_dir, exist_ok=True)
    full = os.path.join(out_dir, "full.png")
    if not os.path.exists(full) or os.path.getmtime(full) < os.path.getmtime(a.map):
        subprocess.run([EDITOR, a.map, "--render-image", full, "full:5880"], timeout=900)
    im = Image.open(full).convert("RGB")
    pts = [wp[n] for r in rs for n in r["waypoints"] if n in wp]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = 120
    x0, y0 = max(0, int(min(xs)) - pad), max(0, int(min(ys)) - pad)
    x1, y1 = min(im.width, int(max(xs)) + pad), min(im.height, int(max(ys)) + pad)
    im = im.crop((x0, y0, x1, y1))
    k = a.size / max(im.size)
    im = im.resize((int(im.width * k), int(im.height * k)))
    d = ImageDraw.Draw(im)
    try: font = ImageFont.truetype("arialbd.ttf", 15)
    except OSError: font = ImageFont.load_default()
    P = lambda p: ((p[0] - x0) * k, (p[1] - y0) * k)
    for ri, r in enumerate(rs):
        col = ROUTE_COLOURS[ri % len(ROUTE_COLOURS)]
        ps = [wp[n] for n in r["waypoints"] if n in wp]
        pauses = r.get("pauses") or [0] * len(ps)
        legs = list(zip(ps, ps[1:])) + ([(ps[-1], ps[0])] if r.get("loop") and len(ps) > 2 else [])
        for p, q in legs:
            bad = g.leg_problem(p, q)
            d.line([P(p), P(q)], fill=(0, 0, 0), width=6)
            d.line([P(p), P(q)], fill=(255, 0, 0) if bad else col, width=3)       # red is kept for faults
        for p, s in zip(ps, pauses):
            x, y = P(p)
            rr = 3 + s / 3 if s else 2
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=col if s else (0, 0, 0), outline=(0, 0, 0), width=2)
        # which way each stop faces: an arrow 40 px (world) out from it, red where the checker faults the facing
        looks, feats = r.get("looks") or [], r.get("features") or []
        for kk, n in enumerate(r["waypoints"]):
            if n not in wp or kk >= len(looks) or not looks[kk] or kk >= len(pauses) or pauses[kk] <= 0: continue
            p, lk = wp[n], looks[kk]
            L = math.hypot(lk[0] - p[0], lk[1] - p[1]) or 1.0
            ux, uy = (lk[0] - p[0]) / L, (lk[1] - p[1]) / L
            tip = (p[0] + ux * 40, p[1] + uy * 40)
            bad = facing_problem(g, p, lk, feats[kk] if kk < len(feats) else None)
            ac = (255, 0, 0) if bad else col
            head = [P(tip), P((tip[0] - ux * 9 - uy * 6, tip[1] - uy * 9 + ux * 6)),
                    P((tip[0] - ux * 9 + uy * 6, tip[1] - uy * 9 - ux * 6))]
            d.line([P(p), P(tip)], fill=(0, 0, 0), width=5)
            d.polygon(head, fill=(0, 0, 0))
            d.line([P(p), P(tip)], fill=ac, width=2)
            d.polygon([P((tip[0] - ux * 1.5, tip[1] - uy * 1.5)), head[1], head[2]], fill=ac)
        x, y = P(ps[0])
        for dx, dy in ((-1, -1), (1, 1), (-1, 1), (1, -1)):
            d.text((x + 9 + dx, y - 20 + dy), r["who"], fill=(0, 0, 0), font=font)
        d.text((x + 9, y - 20), r["who"], fill=col, font=font)
    d.rectangle((0, 0, 1180, 26), fill=(12, 12, 14))
    d.text((8, 5), f"{name}: routes walked (dots: stops, size = seconds standing; arrows: the way each stop faces; "
                   f"red: a leg or facing the checker faults)",
           fill=(230, 230, 230), font=font)
    out = a.out or os.path.join(out_dir, "routes.png")
    im.save(out)
    print(out)


if __name__ == "__main__":
    main()
