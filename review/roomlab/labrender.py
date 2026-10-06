"""Room pictures for the room lab, drawn the same way for Westwood's rooms and ours, so a judge cannot tell them apart by
the picture itself:

- the map editor's full render (MapEditor.exe <map> --render-image <png> full:5880 [nowalls]: one image pixel per
  world pixel, no lighting), the same for both;
- the room cropped by its own cells (the checker's room finder, validate/checks.py find_rooms, for both kinds) plus a
  margin, with room above for the walls and tall pieces that rise up the screen;
- the walls in front of the room drawn half see-through over its floor, as the game draws them in front of the player
  (the render without walls blended in, as review/rooms.py does);
- everything outside the room and its walls blacked out (the canvas colour), so neither the field round a lab building
  nor a Westwood town, nor the furnished neighbours round a Westwood room, gives the picture away;
- no creatures: both renders are of a creature-free copy of the map (nocreatures.ps1: monsters, NPCs and players
  removed with the editor's own library), since Westwood's rooms hold monsters and NPCs and the lab's none;
- one scale per room type (from Westwood's rooms of the type: labref.type_scale), the room centred on a fixed canvas;
  a room too big for the canvas at that scale is shrunk to fit (its `scale` is recorded, never drawn);
- no labels in the image.
"""
import os, subprocess, tempfile
import labenv as E
from PIL import Image, ImageChops, ImageDraw, ImageFilter

CANVAS = (960, 720)
BG = (12, 12, 14)
OUTSIDE = 0.0           # brightness of everything outside the room and its walls (0: the canvas colour). It was 0.10:
                        # Westwood's rooms then showed their furnished neighbours faintly round them, the lab's mostly
                        # an empty field (a judge's tell, FAIRNESS.md)
MARGIN = 30             # world px round the room's cells
RISE = 60               # world px above the room for walls and tall pieces
WALL_REACH = 17         # world px round the floor where the room's own walls are kept bright
EDITOR = os.path.join(E.REPO, "MapEditor", "bin", "Release", "MapEditor.exe")
NOXSHARED = os.path.join(E.REPO, "MapEditor", "bin", "Release", "NoxShared.dll")
STRIP = os.path.join(E.HERE, "nocreatures.ps1")
PS32 = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
CLEAN = os.path.join(E.OUT, "_clean")          # creature-free copies of Westwood's maps and their renders
_cache = {}


def creature_free(src, dst):
    """Writes `dst`, a copy of the map `src` with every creature (monsters, NPCs, players) removed, loaded and saved by
    the editor's own library (nocreatures.ps1); re-made when `src` is newer. Returns `dst`."""
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src): return dst
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(f"{os.path.abspath(src)}\t{os.path.abspath(dst)}\n")
        jobs = f.name
    try:
        res = subprocess.run([PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", STRIP, "-Dll", NOXSHARED,
                              "-JobList", jobs], capture_output=True, text=True, timeout=300)
    finally:
        os.remove(jobs)
    if not res.stdout.startswith("OK") or not os.path.exists(dst):
        raise RuntimeError(f"creature-free copy of {src} failed: {res.stdout.strip()} {res.stderr.strip()[:300]}")
    return dst


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
    """(full, bare) renders of a Westwood map without its creatures, cached in review/out/roomlab/_clean/."""
    clean = creature_free(m.file, os.path.join(CLEAN, m.name + ".map"))
    return (render_full(clean, os.path.join(CLEAN, m.name + ".png")),
            render_full(clean, os.path.join(CLEAN, m.name + ".nowalls.png"), walls=False))


def lab_renders(map_path):
    """(full, bare) renders of a lab map without creatures (a copy in its folder's clean/; the map itself, which the
    metrics read, is untouched)."""
    d, fn = os.path.split(map_path)
    clean = creature_free(map_path, os.path.join(d, "clean", fn))
    base = os.path.splitext(clean)[0]
    return render_full(clean, base + ".png"), render_full(clean, base + ".nowalls.png", walls=False)


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
    # this room's walls only: within WALL_REACH of its floor. It was 30 px: the stubs of the walls running on past the
    # room's corners showed, and Westwood's rooms, set in their buildings, had many more of them than the lab's
    # (FAIRNESS.md)
    walls = ImageChops.multiply(walls, floor.filter(ImageFilter.MaxFilter(2 * WALL_REACH + 1)))
    keep = ImageChops.lighter(ImageChops.lighter(floor, up), walls).filter(ImageFilter.GaussianBlur(1.5))
    c = Image.composite(c, c.point(lambda p: int(p * OUTSIDE)) if OUTSIDE else Image.new("RGB", c.size, BG), keep)
    s = min(scale, canvas[0] / c.width, canvas[1] / c.height)
    c = c.resize((max(1, int(c.width * s)), max(1, int(c.height * s))), Image.LANCZOS)
    pic = Image.new("RGB", canvas, BG)
    pic.paste(c, ((canvas[0] - c.width) // 2, (canvas[1] - c.height) // 2))
    return pic, s
