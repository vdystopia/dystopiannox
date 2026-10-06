"""Scene pictures for the scene lab, drawn the same way for Westwood's scenes and ours, so a judge cannot tell them apart
by the picture itself:

- the map editor's full render (MapEditor.exe <map> --render-image <png> full:5880 [nowalls]: one image pixel per world
  pixel, no lighting), the same for both;
- a fixed world window per scene type (labref.window: Westwood's scenes of the type fit it), centred on the scene's
  pieces, scaled onto a fixed 960 x 720 canvas: one scale for every picture of the type;
- **the scene's own footprint only** (since round 7): the hull of its pieces plus MARGIN px round it (and RISE px above
  it, for the tall sprites and the back walls that rise up the screen), and the walls it leans on: the wall pixels (where
  the render with walls differs from the one without) within LEAN px of that footprint: a graveyard's fence, a jail's
  masonry, a camp's cliff, a den's earth, a house's side a garden lies along. The road, shore or water the scene stands
  on shows inside the margin. Everything further out is the canvas colour, as the room lab's pictures are
  (review/roomlab/labrender.py): Westwood's scenes stand in whole towns and the lab's in a hamlet or a glade, and the
  judges had kept scoring that setting ("the well serves nothing", "no castle round the jail"). Whether a scene sits
  well in its town is judged on whole maps (tests/qa.py's pictures), not here (review/roomlab/FAIRNESS.md 6);
- no creatures: both are rendered from a creature-free copy of the map (review/roomlab/nocreatures.ps1: monsters,
  NPCs and players removed with the editor's own library), since Westwood's maps have their monsters and the lab its
  posts (an independent blind judge's tell, review/roomlab/FAIRNESS.md);
- no labels in the image.
"""
import os, subprocess, tempfile
import labenv as E
from PIL import Image, ImageChops, ImageDraw, ImageFilter

VERSION = 4              # 3: drawn without creatures; 4: the footprint only, the rest the canvas colour
CANVAS = (960, 720)
BG = (12, 12, 14)        # the canvas colour (the room lab's)
MARGIN = 40              # world px round the hull of the scene's pieces
RISE = 50                # world px above it: tall sprites and back walls rise up the screen
LEAN = 90                # world px beyond the footprint where the walls the scene leans on still show
MIN_R = 46               # a scene of one or two pieces: at least this round each
EDITOR = os.path.join(E.REPO, "MapEditor", "bin", "Release", "MapEditor.exe")
NOXSHARED = os.path.join(E.REPO, "MapEditor", "bin", "Release", "NoxShared.dll")
STRIP = os.path.join(E.REPO, "review", "roomlab", "nocreatures.ps1")
PS32 = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
CLEAN = os.path.join(E.OUT, "_clean")          # creature-free copies of Westwood's maps and their renders
_cache = {}


def creature_free(src, dst):
    """Writes `dst`, a copy of the map `src` without creatures (as review/roomlab/labrender.py creature_free)."""
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
        if len(_cache) > 4: _cache.clear()
        _cache[key] = Image.open(png).convert("RGB")
    return _cache[key]


def westwood_render(m):
    """(full, bare) renders of a Westwood map without its creatures, with and without walls."""
    clean = creature_free(m.file, os.path.join(CLEAN, m.name + ".map"))
    return (render_full(clean, os.path.join(CLEAN, m.name + ".png")),
            render_full(clean, os.path.join(CLEAN, m.name + ".nowalls.png"), walls=False))


def lab_render(map_path):
    """(full, bare) renders of a lab map without creatures (a copy in its folder's clean/)."""
    d, fn = os.path.split(map_path)
    clean = creature_free(map_path, os.path.join(d, "clean", fn))
    base = os.path.splitext(clean)[0]
    return render_full(clean, base + ".png"), render_full(clean, base + ".nowalls.png", walls=False)


def centre_of(s):
    pts = [(x, y) for _, x, y in s["pieces"]] or [tuple(s["anchor"])]
    return sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)


def _hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3: return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0: hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def footprint(size, pts, grow, rise=0):
    """A mask (L, `size`) of the hull of `pts` grown by `grow` px, and the same again `rise` px up the screen."""
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    h = _hull([(round(x), round(y)) for x, y in pts])
    r = max(grow, MIN_R) if len(pts) <= 2 else grow
    for dy in ((0, -rise) if rise else (0,)):
        hh = [(x, y + dy) for x, y in h]
        if len(hh) >= 3: d.polygon(hh, fill=255)
        for k, (x, y) in enumerate(hh):
            d.ellipse((x - r, y - r, x + r, y + r), fill=255)
            if len(hh) >= 2:
                x2, y2 = hh[(k + 1) % len(hh)]
                d.line((x, y, x2, y2), fill=255, width=int(2 * r))
    return mask


def picture(full, bare, s, window, canvas=CANVAS):
    """The scene's picture: the window (w, h world px) round its pieces, scaled to the canvas; only the scene's
    footprint and the walls it leans on shown, the rest the canvas colour."""
    cx, cy = centre_of(s)
    w, h = window
    box = (int(cx - w / 2), int(cy - h / 2 - 20), int(cx + w / 2), int(cy + h / 2 - 20))   # a little room above for
    c = full.crop(box)                                                                     # tall sprites
    pts = [(x - box[0], y - box[1]) for _, x, y in s["pieces"]] or [(cx - box[0], cy - box[1])]
    foot = footprint(c.size, pts, MARGIN, RISE)
    lean = footprint(c.size, pts, MARGIN + LEAN, RISE)
    walls = ImageChops.difference(c, bare.crop(box)).convert("L").point(lambda p: 255 if p > 24 else 0)
    walls = ImageChops.multiply(walls.filter(ImageFilter.MaxFilter(5)), lean)
    keep = ImageChops.lighter(foot, walls).filter(ImageFilter.GaussianBlur(3))
    c = Image.composite(c, Image.new("RGB", c.size, BG), keep)
    return c.resize(canvas, Image.LANCZOS)
