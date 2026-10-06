"""Room pictures for the room lab, drawn the same way for Westwood's rooms and ours, so a judge cannot tell them apart by
the picture itself:

- the map editor's full render (MapEditor.exe <map> --render-image <png> full:5880 [nowalls]: one image pixel per
  world pixel, no lighting), the same for both;
- the room cropped by its own cells (the checker's room finder, validate/checks.py find_rooms, for both kinds) plus a
  margin, with room above for the walls and tall pieces that rise up the screen;
- the walls in front of the room drawn half see-through over its floor, as the game draws them in front of the player
  (the render without walls blended in, as review/rooms.py does);
- everything outside the room and its walls darkened to near black, so neither the field round a lab building nor a
  Westwood town gives the picture away;
- one scale per room type (from Westwood's rooms of the type: labref.type_scale), the room centred on a fixed canvas;
  a room too big for the canvas at that scale is shrunk to fit (its `scale` is recorded, never drawn);
- no labels in the image.
"""
import os, subprocess
import labenv as E
from PIL import Image, ImageChops, ImageDraw, ImageFilter

CANVAS = (960, 720)
BG = (12, 12, 14)
OUTSIDE = 0.10          # brightness of everything outside the room and its walls
MARGIN = 30             # world px round the room's cells
RISE = 60               # world px above the room for walls and tall pieces
EDITOR = os.path.join(E.REPO, "MapEditor", "bin", "Release", "MapEditor.exe")
_cache = {}


def render_full(map_path, png, walls=True):
    """The editor's full render of a map into `png` (re-rendered when the map is newer). Returns the PIL image."""
    if not os.path.exists(png) or os.path.getmtime(png) < os.path.getmtime(map_path):
        os.makedirs(os.path.dirname(png), exist_ok=True)
        subprocess.run([EDITOR, os.path.abspath(map_path), "--render-image", os.path.abspath(png), "full:5880"]
                       + ([] if walls else ["nowalls"]), timeout=900)
    if not os.path.exists(png): raise RuntimeError(f"render of {map_path} failed")
    key = (png, os.path.getmtime(png))
    if key not in _cache:
        if len(_cache) > 6: _cache.clear()
        _cache[key] = Image.open(png).convert("RGB")
    return _cache[key]


def westwood_renders(m):
    """(full, bare) renders of a Westwood map, cached with review/review.py's renders (review/out/renders)."""
    d = os.path.join(E.REVIEW, "out", "renders")
    return (render_full(m.file, os.path.join(d, m.name + ".png")),
            render_full(m.file, os.path.join(d, m.name + ".nowalls.png"), walls=False))


def lab_renders(map_path):
    base = os.path.splitext(map_path)[0]
    return render_full(map_path, base + ".png"), render_full(map_path, base + ".nowalls.png", walls=False)


def box_of(cells):
    """World-pixel box of a room's cells, with its margin and the rise above it."""
    C = E.MD.CELL
    xs = [x for x, _ in cells]; ys = [y for _, y in cells]
    return (min(xs) * C - MARGIN, min(ys) * C - MARGIN - RISE, (max(xs) + 1) * C + MARGIN, (max(ys) + 1) * C + MARGIN)


def fit_scale(cells, canvas=CANVAS):
    x0, y0, x1, y1 = box_of(cells)
    return min(canvas[0] / (x1 - x0), canvas[1] / (y1 - y0))


def picture(full, bare, cells, scale, canvas=CANVAS):
    """The room's picture at `scale` (shrunk further if it would not fit). Returns (image, scale used)."""
    C = E.MD.CELL
    box = tuple(int(round(v)) for v in box_of(cells))
    ox, oy = box[0], box[1]
    c = full.crop(box)
    b = bare.crop(box)
    floor = Image.new("L", c.size, 0)
    d = ImageDraw.Draw(floor)
    for x, y in cells:
        d.rectangle((x * C - ox, y * C - oy, (x + 1) * C - ox - 1, (y + 1) * C - oy - 1), fill=255)
    # over the room's floor the walls show at half strength: the game draws the walls in front of the player see-through
    c = Image.composite(Image.blend(c, b, 0.55), c, floor.filter(ImageFilter.GaussianBlur(2)))
    # Kept bright: the floor, what rises from it up the screen, and the room's own wall pixels (where the render with
    # walls differs from the one without). Not a band of ground round the walls: in the lab that band is a building's
    # sunlit field and drew a glowing rim round every generated room (an independent judge's tell, 2026-10-05 night),
    # where Westwood's rooms sit among dark neighbours.
    up = Image.new("L", c.size, 0)
    up.paste(floor, (0, -42))                                    # tall pieces and back walls rise up the screen
    walls = ImageChops.difference(full.crop(box), b).convert("L").point(lambda p: 255 if p > 24 else 0)
    walls = ImageChops.multiply(walls, floor.filter(ImageFilter.MaxFilter(61)))   # this room's walls only
    keep = ImageChops.lighter(ImageChops.lighter(floor, up), walls).filter(ImageFilter.GaussianBlur(1.5))
    c = Image.composite(c, c.point(lambda p: int(p * OUTSIDE)), keep)
    s = min(scale, canvas[0] / c.width, canvas[1] / c.height)
    c = c.resize((max(1, int(c.width * s)), max(1, int(c.height * s))), Image.LANCZOS)
    pic = Image.new("RGB", canvas, BG)
    pic.paste(c, ((canvas[0] - c.width) // 2, (canvas[1] - c.height) // 2))
    return pic, s
