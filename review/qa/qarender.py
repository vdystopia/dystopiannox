"""Labelled pictures for the user's QA rounds (review/qa/README.md): every picture carries its label (ROOM-LIBRARY-03,
EXT-GRAVEYARD-07, BR-12, DOCK-05) in a banner along its top, so the user's feedback can name each one, and the pictures
of a set are gathered onto numbered contact sheets.

    crop_labelled(map_path, [(label, (x, y) world px, caption)], out_dir, window=(w, h))
    label_image(src_png, label, caption, dst_png)
    contact_sheet([png...], dst_png, title, cols=5)
"""
import os, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
EDITOR = os.path.join(REPO, "MapEditor", "bin", "Release", "MapEditor.exe")
BANNER = 54
BG = (18, 18, 22)
FG = (245, 232, 180)


def _font(size, bold=True):
    for f in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans-Bold.ttf"):
        try: return ImageFont.truetype(f, size)
        except OSError: pass
    return ImageFont.load_default()


def render_full(map_path, png=None, walls=True):
    png = png or os.path.splitext(map_path)[0] + (".png" if walls else ".nowalls.png")
    if not os.path.exists(png) or os.path.getmtime(png) < os.path.getmtime(map_path):
        subprocess.run([EDITOR, os.path.abspath(map_path), "--render-image", os.path.abspath(png), "full:5880"]
                       + ([] if walls else ["nowalls"]), timeout=900)
    return Image.open(png).convert("RGB")


def banner(img, label, caption=""):
    w, h = img.size
    out = Image.new("RGB", (w, h + BANNER), BG)
    out.paste(img, (0, BANNER))
    d = ImageDraw.Draw(out)
    d.text((14, 8), label, font=_font(34), fill=FG)
    if caption:
        lw = d.textlength(label, font=_font(34))
        d.text((28 + lw, 18), caption, font=_font(18, bold=False), fill=(200, 200, 200))
    return out


def label_image(src, label, caption, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    banner(Image.open(src).convert("RGB"), label, caption).save(dst)
    return dst


def crop_labelled(map_path, items, out_dir, window=(1000, 750), full=None):
    """Crops the map's full render round each item's centre and labels it. Returns the written paths."""
    full = full or render_full(map_path)
    os.makedirs(out_dir, exist_ok=True)
    w, h = window
    out = []
    for label, (x, y), caption in items:
        box = (int(x - w / 2), int(y - h / 2), int(x + w / 2), int(y + h / 2))
        dst = os.path.join(out_dir, label + ".png")
        banner(full.crop(box), label, caption).save(dst)
        out.append(dst)
    return out


def contact_sheet(pngs, dst, title, cols=5, thumb=(480, 386)):
    """The set's pictures in a grid, each with its label, under a title."""
    rows = (len(pngs) + cols - 1) // cols
    W, H = cols * thumb[0], rows * thumb[1] + 60
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((16, 12), title, font=_font(32), fill=FG)
    for i, p in enumerate(pngs):
        im = Image.open(p).convert("RGB")
        im.thumbnail(thumb, Image.LANCZOS)
        x, y = (i % cols) * thumb[0], 60 + (i // cols) * thumb[1]
        sheet.paste(im, (x + (thumb[0] - im.size[0]) // 2, y))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    sheet.save(dst, quality=88)
    return dst
