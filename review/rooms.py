"""Room review sheet: every room of a map cropped from a full render, labelled with its kind.

    py review/rooms.py <map.map> [out.png]

Rooms come from <map>.rooms.json next to the map when present (test maps), else from the checker's
room finder (validate/checks.py find_rooms). Writes review/out/<map>/rooms.png by default.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "validate"))
import mapdata as md
import checks as C
from review import render, font
from PIL import Image, ImageDraw


def rooms_of(path, m):
    side = os.path.splitext(path)[0] + ".rooms.json"
    if os.path.exists(side):
        return [(r["kind"], r["tiles"], tuple(r["box"])) for r in json.load(open(side))]
    out = []
    for r in C.find_rooms(m):
        kind, _ = C.room_profile(r)
        xs = [c[0] for c in r["cells"]]; ys = [c[1] for c in r["cells"]]
        out.append((kind, r["tiles"], (min(xs) - 1, min(ys) - 1, max(xs) + 2, max(ys) + 2)))
    return sorted(out, key=lambda r: -r[1])


def sheet(path, out=None, cell=520, cols=4):
    m = md.load(path)
    im = render(path, m.name)
    rooms = rooms_of(path, m)
    if not rooms: raise SystemExit("no rooms found")
    rows = (len(rooms) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * cell, rows * (cell + 24)), (14, 14, 16))
    d = ImageDraw.Draw(canvas)
    for k, (kind, tiles, (x0, y0, x1, y1)) in enumerate(rooms):
        c = im.crop((x0 * md.CELL, y0 * md.CELL, x1 * md.CELL, y1 * md.CELL))
        c.thumbnail((cell - 8, cell - 8))
        x, y = (k % cols) * cell, (k // cols) * (cell + 24)
        canvas.paste(c, (x + (cell - c.width) // 2, y + 24))
        d.text((x + 6, y + 3), f"{kind} ({tiles} tiles)", fill=(255, 215, 130), font=font(16))
    out = out or os.path.join(HERE, "out", m.name, "rooms.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    canvas.save(out)
    return out


if __name__ == "__main__":
    print(sheet(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
