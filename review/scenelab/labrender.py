"""Scene pictures for the scene lab, drawn the same way for Westwood's scenes and ours, so a judge cannot tell them apart
by the picture itself:

- the map editor's full render (MapEditor.exe <map> --render-image <png> full:5880: one image pixel per world pixel,
  no lighting), the same for both;
- a fixed world window per scene type (labref.window: Westwood's scenes of the type fit it), centred on the scene's
  pieces, scaled onto a fixed 960 x 720 canvas: one scale for every picture of the type;
- the ground away from the scene dimmed (to DIM of its brightness, softly, beyond REACH px of every piece), so
  neither a Westwood town round it nor the lab's glade gives the picture away, while the fence, the wall, the shore
  or the road it stands by still shows;
- no labels in the image.
"""
import os, subprocess
import labenv as E
from PIL import Image, ImageDraw, ImageFilter

VERSION = 2
CANVAS = (960, 720)
DIM = 0.42
REACH = 110
EDITOR = os.path.join(E.REPO, "MapEditor", "bin", "Release", "MapEditor.exe")
_cache = {}


def render_full(map_path, png):
    """The editor's full render of a map into `png` (re-rendered when the map is newer). Returns the PIL image."""
    if not os.path.exists(png) or os.path.getmtime(png) < os.path.getmtime(map_path):
        os.makedirs(os.path.dirname(png), exist_ok=True)
        subprocess.run([EDITOR, os.path.abspath(map_path), "--render-image", os.path.abspath(png), "full:5880"],
                       timeout=900)
    if not os.path.exists(png): raise RuntimeError(f"render of {map_path} failed")
    key = (png, os.path.getmtime(png))
    if key not in _cache:
        if len(_cache) > 4: _cache.clear()
        _cache[key] = Image.open(png).convert("RGB")
    return _cache[key]


def westwood_render(m):
    return render_full(m.file, os.path.join(E.RENDERS, m.name + ".png"))


def lab_render(map_path):
    return render_full(map_path, os.path.splitext(map_path)[0] + ".png")


def centre_of(s):
    pts = [(x, y) for _, x, y in s["pieces"]] or [tuple(s["anchor"])]
    return sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)


def picture(full, s, window, canvas=CANVAS):
    """The scene's picture: the window (w, h world px) round its pieces, the ground away from them dimmed, scaled to
    the canvas."""
    cx, cy = centre_of(s)
    w, h = window
    box = (int(cx - w / 2), int(cy - h / 2 - 20), int(cx + w / 2), int(cy + h / 2 - 20))   # a little room above for
    c = full.crop(box)                                                                     # tall sprites
    mask = Image.new("L", c.size, 0)
    d = ImageDraw.Draw(mask)
    pts = [(x - box[0], y - box[1]) for _, x, y in s["pieces"]] + [(cx - box[0], cy - box[1])]
    for x, y in pts:
        d.ellipse((x - REACH, y - REACH - 30, x + REACH, y + REACH), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(28))
    c = Image.composite(c, c.point(lambda p: int(p * DIM)), mask)
    return c.resize(canvas, Image.LANCZOS)
