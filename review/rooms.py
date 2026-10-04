"""Room review: every room of a map cropped from a full render, numbered and labelled.

    py review/rooms.py <map.map> [out.png]     one sheet of every room (review/out/<map>/rooms.png)
    py review/rooms.py <map.map> --each        also one close-up per room (review/out/<map>/rooms/NN.png),
                                               numbered so a playtester can give feedback room by room

Rooms come from <map>.rooms.json next to the map when present: generated maps and test maps write it
(kit/identity.rooms_sidecar), with each room's number, building, kind and purpose. Otherwise they come
from the checker's room finder (validate/checks.py find_rooms), labelled with the kind it reads.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "validate"))
import mapdata as md
import checks as C
from review import render, font
from PIL import Image, ImageDraw, ImageFilter


def rooms_of(path, m):
    """[dict(number, building, kind, purpose, tiles, box)] with box in grid cells."""
    side = os.path.splitext(path)[0] + ".rooms.json"
    if os.path.exists(side):
        rooms = json.load(open(side))
        for k, r in enumerate(rooms):
            r.setdefault("number", k + 1); r.setdefault("building", ""); r.setdefault("purpose", "")
        return rooms
    out = []
    for r in C.find_rooms(m):
        kind, _ = C.room_profile(r)
        xs = [c[0] for c in r["cells"]]; ys = [c[1] for c in r["cells"]]
        out.append(dict(building="", kind=kind, purpose="", tiles=r["tiles"],
                        box=(min(xs) - 1, min(ys) - 1, max(xs) + 2, max(ys) + 2)))
    out.sort(key=lambda r: -r["tiles"])
    for k, r in enumerate(out): r["number"] = k + 1
    return out


def label(r):
    head = f"{r['number']}. {r['building'] + ' - ' if r['building'] else ''}{(r['kind'] or '').replace('_', ' ')}"
    return head, (r["purpose"] + " - " if r["purpose"] else "") + f"{r['tiles']} floor tiles"


def each(path, size=(1100, 820), margin=2):
    """One close-up per room, numbered: review/out/<map>/rooms/NN.png. Returns the file paths."""
    m = md.load(path)
    im = render(path, m.name)
    bare = render(path, m.name, walls=False)       # the same without walls: front walls read see-through, as in game
    od = os.path.join(HERE, "out", m.name, "rooms")
    os.makedirs(od, exist_ok=True)
    files = []
    for r in rooms_of(path, m):
        x0, y0, x1, y1 = r["box"]
        ox, oy = (x0 - margin) * md.CELL, (y0 - margin) * md.CELL
        box = (ox, oy, (x1 + margin) * md.CELL, (y1 + margin) * md.CELL)
        c = im.crop(box)
        if r.get("floor"):                     # dim everything but this room: its floor, walls and what stands there
            mask = Image.new("L", c.size, 0)
            dm = ImageDraw.Draw(mask)
            for x, y in r["floor"]:            # a floor tile covers 2 x 2 cells
                dm.rectangle((x * md.CELL - ox, y * md.CELL - oy, (x + 2) * md.CELL - ox, (y + 2) * md.CELL - oy), fill=255)
            # over the room's own floor, walls show at half strength: the game draws the walls in front of
            # the player see-through, so what stands against them is seen
            c = Image.composite(Image.blend(c, bare.crop(box), 0.55), c, mask.filter(ImageFilter.GaussianBlur(2)))
            mask = mask.filter(ImageFilter.MaxFilter(25))            # the walls round the floor
            up = Image.new("L", c.size, 0)
            up.paste(mask, (0, -42))                                 # tall pieces and walls rise up the screen
            mask = Image.composite(Image.new("L", c.size, 255), mask, up).filter(ImageFilter.GaussianBlur(4))
            c = Image.composite(c, c.point(lambda p: int(p * 0.3)), mask)
        scale = min(size[0] / c.width, (size[1] - 64) / c.height)
        c = c.resize((int(c.width * scale), int(c.height * scale)), Image.LANCZOS)
        pic = Image.new("RGB", (size[0], size[1]), (14, 14, 16))
        pic.paste(c, ((size[0] - c.width) // 2, 64 + (size[1] - 64 - c.height) // 2))
        d = ImageDraw.Draw(pic)
        head, sub = label(r)
        d.text((14, 8), head, fill=(255, 215, 130), font=font(26))
        d.text((14, 40), sub, fill=(200, 200, 200), font=font(17))
        f = os.path.join(od, f"{r['number']:02d}.png")
        pic.save(f)
        files.append(f)
    return files


def sheet(path, out=None, cell=520, cols=4):
    m = md.load(path)
    im = render(path, m.name)
    rooms = rooms_of(path, m)
    if not rooms: raise SystemExit("no rooms found")
    rows = (len(rooms) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * cell, rows * (cell + 24)), (14, 14, 16))
    d = ImageDraw.Draw(canvas)
    for k, r in enumerate(rooms):
        x0, y0, x1, y1 = r["box"]
        c = im.crop((x0 * md.CELL, y0 * md.CELL, x1 * md.CELL, y1 * md.CELL))
        c.thumbnail((cell - 8, cell - 8))
        x, y = (k % cols) * cell, (k // cols) * (cell + 24)
        canvas.paste(c, (x + (cell - c.width) // 2, y + 24))
        d.text((x + 6, y + 3), f"{label(r)[0]} ({r['tiles']} tiles)", fill=(255, 215, 130), font=font(16))
    out = out or os.path.join(HERE, "out", m.name, "rooms.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    canvas.save(out)
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--each"]
    print(sheet(args[0], args[1] if len(args) > 1 else None))
    if "--each" in sys.argv:
        print("\n".join(each(args[0])))
