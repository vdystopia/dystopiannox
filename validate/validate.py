"""Checks a Nox map for defects and for departures from Westwood's style.

Usage:
  py validate/validate.py <map>  [--image] [--only check,check] [--quiet]
    <map>    a .map file, a map folder name in the game's maps folder (e.g. DysVale), or the name of a
             Westwood map in the reference corpus (e.g. Con07B)
    --image  also draws the problems on a picture of the map (needs the built editor): an overview
             with numbered markers (red = error, orange = warning) and a close-up per error
    --only   run only the named checks (setup, wall_pieces, wall_shapes, boundary, doors, kits,
             objects, doorways, floors, rooms, density)

Writes validate/out/<map>/report.md and report.json (plus overview.png and errors/*.png with
--image). Exit code: 0 when there are no errors, 1 when there are errors, 2 when the map can't be read.
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mapdata as md
import checks as C

EDITOR = os.path.join(md.REPO, "MapEditor", "bin", "Release", "MapEditor.exe")
NOX = os.path.dirname(md.REPO)
ORDER = {"error": 0, "warning": 1, "info": 2}
LABEL = dict(setup="Map setup", wall_pieces="Wall pieces", wall_shapes="Wall shapes", boundary="Outer boundary",
             doors="Doors", kits="Bridges and docks", objects="Object placement", reachability="Reachability",
             doorways="Doorways", routes="Where creatures walk", floors="Floor transitions", rooms="Rooms", density="Density and style",
             exterior="The outdoor ground")


def resolve(arg):
    """Path of a .map / exported .json for a file path, a game map folder name, or a corpus map name."""
    if os.path.exists(arg): return arg
    game = os.path.join(NOX, "maps", arg, arg + ".map")
    if os.path.exists(game): return game
    gen = os.path.join(md.REPO, "mapgen", "out", arg + ".map")
    if os.path.exists(gen): return gen
    js = md.corpus_json(arg)
    if os.path.exists(js): return js
    raise FileNotFoundError(f"no map named {arg}")


def baseline():
    with open(os.path.join(HERE, "baseline.json")) as f:
        return json.load(f)


def validate(path, only=None):
    m = md.load(path)
    findings, ctx = C.run_all(m, baseline(), only)
    findings.sort(key=lambda f: (ORDER[f["severity"]], f["check"]))
    for i, f in enumerate(x for x in findings if x["severity"] != "info"):
        f["n"] = i + 1
    return m, findings, ctx


def where(f):
    if f["x"] is None: return "map-wide"
    return f"x={f['x']:.0f}, y={f['y']:.0f} (grid cell {int(f['x'] // md.CELL)}, {int(f['y'] // md.CELL)})"


def report_md(m, findings):
    errs = [f for f in findings if f["severity"] == "error"]
    warns = [f for f in findings if f["severity"] == "warning"]
    lines = [f"# Check report: {m.name}", "",
             f"**{len(errs)} error(s), {len(warns)} warning(s).** Errors are defects a player will see or hit; "
             "warnings are departures from the range Westwood's single-player maps stay within.", ""]
    for sev, title in (("error", "Errors"), ("warning", "Warnings")):
        fs = [f for f in findings if f["severity"] == sev]
        if not fs: continue
        lines += [f"## {title}", ""]
        by = {}
        for f in fs: by.setdefault(f["check"], []).append(f)
        for chk, items in by.items():
            lines += [f"### {LABEL.get(chk, chk)} ({len(items)})", ""]
            lines += [f"{f['n']}. {f['msg']} ({where(f)})" for f in items]
            lines.append("")
    info = [f for f in findings if f["severity"] == "info"]
    if info:
        lines += ["## Notes", ""] + [f"- {f['msg']}" for f in info] + [""]
    return "\n".join(lines)


def render(map_file, png):
    """Whole map at 1 image pixel per world pixel (5880 x 5880), uncropped."""
    if os.path.exists(png): os.remove(png)
    subprocess.run([EDITOR, map_file, "--render-image", png, "full:5880"], timeout=900)
    if not os.path.exists(png): raise RuntimeError("the editor did not render the map")


def draw(m, findings, out_dir):
    from PIL import Image, ImageDraw, ImageFont
    full_png = os.path.join(out_dir, "_render.png")
    render(m.file, full_png)
    im = Image.open(full_png).convert("RGB")
    xs = [x for x, _ in m.cover] or [0]; ys = [y for _, y in m.cover] or [0]
    box = (max(0, min(xs) * md.CELL - 60), max(0, min(ys) * md.CELL - 60),
           min(5880, max(xs) * md.CELL + 60), min(5880, max(ys) * md.CELL + 60))
    try:
        font = ImageFont.truetype("arialbd.ttf", 28); small = ImageFont.truetype("arialbd.ttf", 16)
    except OSError:
        font = small = ImageFont.load_default()
    shown = [f for f in findings if f["severity"] in ("error", "warning") and f["x"] is not None]
    # close-ups of errors before markers are drawn over the picture
    err_dir = os.path.join(out_dir, "errors")
    os.makedirs(err_dir, exist_ok=True)
    for old in os.listdir(err_dir): os.remove(os.path.join(err_dir, old))
    for f in shown:
        if f["severity"] != "error": continue
        x, y = f["x"], f["y"]
        crop = im.crop((int(x - 300), int(y - 220), int(x + 300), int(y + 220))).copy()
        d = ImageDraw.Draw(crop)
        d.ellipse([270, 190, 330, 250], outline=(255, 40, 40), width=4)
        d.rectangle([0, 0, 600, 26], fill=(0, 0, 0))
        d.text((6, 4), f"#{f['n']} {f['check']}: {f['msg'][:80]}", fill=(255, 255, 255), font=small)
        crop.save(os.path.join(err_dir, f"error_{f['n']:03d}.png"))
    d = ImageDraw.Draw(im)
    for f in sorted(shown, key=lambda f: -ORDER[f["severity"]]):
        col = (255, 40, 40) if f["severity"] == "error" else (255, 160, 0)
        r = 34 if f["severity"] == "error" else 26
        x, y = f["x"], f["y"]
        d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=6)
        d.text((x + r, y - r - 10), str(f["n"]), fill=col, font=font, stroke_width=3, stroke_fill=(0, 0, 0))
    over = im.crop(box)
    over.thumbnail((2400, 2400))
    over.save(os.path.join(out_dir, "overview.png"))
    os.remove(full_png)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__); return 2
    only = None
    if "--only" in argv:
        only = set(argv[argv.index("--only") + 1].split(",")); args = [a for a in args if a != argv[argv.index("--only") + 1]]
    try:
        path = resolve(args[0])
        m, findings, ctx = validate(path, only)
    except Exception as e:
        print(f"Could not check {args[0]}: {e}"); return 2
    out_dir = os.path.join(md.OUT, m.name)
    os.makedirs(out_dir, exist_ok=True)
    text = report_md(m, findings)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f: f.write(text)
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump([{k: v for k, v in x.items() if k != "metrics"} for x in findings], f, indent=1, default=str)
    if "--image" in argv:
        if not m.file or not os.path.exists(m.file):
            print("(no .map file to draw: skipped the picture)")
        else:
            draw(m, findings, out_dir)
    if "--quiet" not in argv: print(text)
    errs = sum(1 for f in findings if f["severity"] == "error")
    warns = sum(1 for f in findings if f["severity"] == "warning")
    print(f"{m.name}: {errs} error(s), {warns} warning(s). Report: {out_dir}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
