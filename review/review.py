"""Visual review of a map against Westwood's: comparison pictures plus design measurements.

Usage:
  py review/review.py <map>            a .map path or a game map folder name (e.g. DysVale)
  py review/review.py --calibrate      re-measure Westwood's outdoor maps (writes review/baseline.json)

Writes review/out/<map>/:
  sheet.png   the map beside the 3 most similar Westwood maps at the same scale: whole map, then
              close-ups at in-game zoom (a building entrance, woodland, waterside, paths/open ground)
  review.md   design measurements against Westwood's range, and the rubric to apply to the sheet
Full-size renders are cached in review/out/renders/.
"""
import collections, json, math, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design as DS
import mapdata as md
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(HERE, "out")
BASELINE = os.path.join(HERE, "baseline.json")
EDITOR = os.path.join(md.REPO, "MapEditor", "bin", "Release", "MapEditor.exe")
NOX = os.path.dirname(md.REPO)
VIEW = (1280, 800)          # world px shown by a close-up (about one game screen)
TILE = (512, 320)           # close-up size on the sheet
OVER = 520                  # overview cell size on the sheet
OVER_SCALE = 1 / 9          # overview: image px per world px (the same for every map)
TOWN_BUILDINGS = 5         # maps with this many buildings are compared with Westwood's towns
TOWN_MEASURES = {"path_share", "path_connected", "doors_on_path", "building_spacing"}
FAMS = ["grass", "dirt", "cobble", "brick", "water", "swamp", "ice", "lava", "cave", "dungeon_stone", "interior_wood"]
# direction of "better" for each design measurement (used for the wording only)
HIGHER_IS_STRUCTURED = {"path_share": True, "path_connected": True, "doors_on_path": True, "tree_clustering": False,
                        "tree_edge_share": True, "plant_same_type": True, "building_spacing": False,
                        "road_near_water": False}


def font(size):
    try: return ImageFont.truetype("arialbd.ttf", size)
    except OSError: return ImageFont.load_default()


# ---- measurements ---------------------------------------------------------------------------------
def profile(m, od):
    """Theme vector for choosing references: floor family shares and whether there are buildings/water."""
    c = collections.Counter(DS.family(t["material"]) for t in m.tiles.values())
    tot = sum(c.values()) or 1
    v = [c[f] / tot for f in FAMS]
    v.append(0.3 if len(od.buildings()) >= 3 else 0.0)
    return v


def _measure(name):
    m = md.load(md.corpus_json(name))
    od = DS.Outdoor(m)
    return name, od.metrics(), profile(m, od)


def calibrate():
    import common
    from concurrent.futures import ProcessPoolExecutor
    weights = dict(md.sp_corpus_maps())
    with ProcessPoolExecutor(6) as pool:
        res = list(pool.map(_measure, sorted(weights)))
    with common.db() as c:
        group = {r["map"]: r["rep"] for r in c.execute("SELECT * FROM layout_group")}
    outdoor = [(n, mt, pr) for n, mt, pr in res if DS.is_outdoor_map(mt)]
    def ranges_of(maps):
        out = {}
        for k in HIGHER_IS_STRUCTURED:
            vals = sorted((mt[k], weights[n]) for n, mt, _ in maps if mt[k] is not None)
            tot = sum(w for _, w in vals); q = {}
            for p in (10, 25, 50, 75, 90):
                acc = 0
                for v, w in vals:
                    acc += w
                    if acc >= tot * p / 100: q[f"p{p}"] = round(v, 3); break
            out[k] = q
        return out
    ranges = ranges_of(outdoor)
    towns = [r for r in outdoor if r[1]["buildings"] >= TOWN_BUILDINGS]
    town_ranges = ranges_of(towns)
    env_of = {n: r["type"] for n, r in md.rules("environments")["maps"].items()}
    by_env = collections.defaultdict(list)
    for r in res: by_env[env_of.get(r[0])].append(r)
    env_ranges = {e: ranges_of(rs) for e, rs in by_env.items() if e and len(rs) >= 4}
    refs = {}
    for n, mt, pr in outdoor:
        g = group.get(n, n)
        if g not in refs or n.startswith("Con"): refs[g] = dict(map=n, profile=pr, metrics=mt, env=env_of.get(n))
    json.dump(dict(ranges=ranges, town_ranges=town_ranges, env_ranges=env_ranges, references=list(refs.values())),
              open(BASELINE, "w"), indent=1)
    print(f"{len(outdoor)} Westwood outdoor maps ({len(refs)} distinct layouts), {len(towns)} with towns; ranges:")
    for k, q in ranges.items():
        print(f"  {k:18s} all   {q}")
        print(f"  {'':18s} towns {town_ranges[k]}")


def references(prof, base, env=None, n=3):
    """The most similar Westwood maps, from the same environment type when it has enough."""
    def cos(a, b):
        return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1)
    pool = [r for r in base["references"] if r.get("env") == env]
    if len(pool) < n: pool = base["references"]
    return sorted(pool, key=lambda r: -cos(prof, r["profile"]))[:n]


# ---- pictures ----------------------------------------------------------------------------------------
def render(map_file, name):
    os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
    png = os.path.join(OUT, "renders", name + ".png")
    if not os.path.exists(png) or os.path.getmtime(png) < os.path.getmtime(map_file):
        subprocess.run([EDITOR, map_file, "--render-image", png, "full:5880"], timeout=900)
    if not os.path.exists(png): raise RuntimeError(f"render of {name} failed")
    return Image.open(png).convert("RGB")


def views(m, od):
    """World-pixel centres of the close-ups: entrance, woodland, waterside, paths/open ground."""
    out = {}
    doors = od.outside_doors()
    if doors:
        cx = sum(d["obj"]["x"] for d, _ in doors) / len(doors); cy = sum(d["obj"]["y"] for d, _ in doors) / len(doors)
        d = min(doors, key=lambda dc: (dc[0]["obj"]["x"] - cx) ** 2 + (dc[0]["obj"]["y"] - cy) ** 2)[0]
        out["entrance"] = (d["obj"]["x"], d["obj"]["y"])
    trees = od.deco["tree"]
    if trees:
        grid = collections.Counter((int(o["x"] // 400), int(o["y"] // 400)) for o in trees)
        (gx, gy), _ = grid.most_common(1)[0]
        out["woodland"] = (gx * 400 + 200, gy * 400 + 200)
    water = [t for t, d in m.tiles.items() if DS.family(d["material"]) == "water"]
    shore = [t for t in water if any((t[0] + a, t[1] + b) in od.ground for a, b in DS.SIDES)]
    if shore:
        sx = sorted(t[0] for t in shore)[len(shore) // 2]
        t = min(shore, key=lambda t: abs(t[0] - sx) + abs(t[1] - sorted(u[1] for u in shore)[len(shore) // 2]))
        out["waterside"] = ((t[0] + 1) * md.CELL, (t[1] + 1) * md.CELL)
    pts = list(od.paths) or list(od.ground)
    if pts:
        mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts)
        t = min(pts, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)
        out["paths"] = ((t[0] + 1) * md.CELL, (t[1] + 1) * md.CELL)
    return out


def overview(im, m):
    xs = [x for x, _ in m.cover]; ys = [y for _, y in m.cover]
    box = (min(xs) * md.CELL, min(ys) * md.CELL, max(xs) * md.CELL, max(ys) * md.CELL)
    crop = im.crop(box)
    w, h = max(1, int(crop.width * OVER_SCALE)), max(1, int(crop.height * OVER_SCALE))
    crop = crop.resize((w, h), Image.LANCZOS)
    if w > OVER or h > OVER: crop.thumbnail((OVER, OVER))      # very large maps: fit (noted on the sheet)
    cell = Image.new("RGB", (OVER, OVER), (20, 20, 24))
    cell.paste(crop, ((OVER - crop.width) // 2, (OVER - crop.height) // 2))
    return cell


def closeup(im, centre):
    if not centre:
        cell = Image.new("RGB", TILE, (40, 40, 44))
        ImageDraw.Draw(cell).text((TILE[0] // 2 - 40, TILE[1] // 2 - 10), "(none)", fill=(150, 150, 150), font=font(20))
        return cell
    x, y = centre
    box = (int(x - VIEW[0] / 2), int(y - VIEW[1] / 2), int(x + VIEW[0] / 2), int(y + VIEW[1] / 2))
    return im.crop(box).resize(TILE, Image.LANCZOS)


ROWS = [("overview", "Whole map\n(same scale)"), ("entrance", "Building\nentrance"), ("woodland", "Woodland"),
        ("waterside", "Waterside"), ("paths", "Paths /\nopen ground")]


def sheet(columns, path):
    """columns: [(title, image, map, views)] -> one comparison picture."""
    lab, colw = 150, max(OVER, TILE[0]) + 12
    heights = [OVER + 12 if r == "overview" else TILE[1] + 12 for r, _ in ROWS]
    W, H = lab + colw * len(columns), 46 + sum(heights)
    out = Image.new("RGB", (W, H), (12, 12, 14))
    d = ImageDraw.Draw(out)
    for i, (title, im, m, vw) in enumerate(columns):
        d.text((lab + i * colw + 8, 12), title, fill=(255, 210, 120) if i == 0 else (220, 220, 220), font=font(22))
        y = 46
        for (row, _), h in zip(ROWS, heights):
            cell = overview(im, m) if row == "overview" else closeup(im, vw.get(row))
            out.paste(cell, (lab + i * colw + 6 + (colw - 12 - cell.width) // 2, y + 6))
            y += h
    y = 46
    for (_, label), h in zip(ROWS, heights):
        d.multiline_text((10, y + h // 2 - 22), label, fill=(200, 200, 200), font=font(18))
        y += h
    out.save(path)


# ---- report ------------------------------------------------------------------------------------------
def judge(k, v, q):
    if v is None or not q: return "n/a"
    if q["p10"] <= v <= q["p90"]: return "within Westwood's range"
    low = v < q["p10"]
    structured = HIGHER_IS_STRUCTURED[k]
    return ("**below** Westwood's range" if low else "**above** Westwood's range") + \
        (" (less structured)" if low == structured else " (more structured)")


def review(arg):
    base = json.load(open(BASELINE))
    path = arg if os.path.exists(arg) else os.path.join(NOX, "maps", arg, arg + ".map")
    m = md.load(path)
    od = DS.Outdoor(m)
    mt = od.metrics()
    import checks as CK
    env = CK.environment(m)
    refs = references(profile(m, od), base, env)
    out_dir = os.path.join(OUT, m.name); os.makedirs(out_dir, exist_ok=True)
    cols = [(m.name + " (generated)", render(path, m.name), m, views(m, od))]
    for r in refs:
        rm = md.load(md.corpus_json(r["map"]))
        cols.append((f"{r['map']} (Westwood)", render(rm.file, r["map"]), rm, views(rm, DS.Outdoor(rm))))
    sheet(cols, os.path.join(out_dir, "sheet.png"))
    lines = [f"# Visual review: {m.name}", "",
             f"Compared with the most similar Westwood maps: {', '.join(r['map'] for r in refs)}. "
             f"Picture: `sheet.png` (whole maps at the same scale, then close-ups of about one game screen).", "",
             "## Design measurements", "",
             f"Environment: **{env}** (ranges and references from Westwood's {env} maps). "
             f"Outdoor ground {mt['outdoor_tiles']} tiles, {mt['trees']} trees, {mt['buildings']} buildings. "
             "Westwood's range is the 10th to 90th percentile over their maps of the same environment.", "",
             "| Measure | This map | Westwood typical (range) | Verdict | " + " | ".join(r["map"] for r in refs) + " |",
             "|---|---|---|---|" + "---|" * len(refs)]
    flags = []
    for k, label in DS.NAMES.items():
        q = (base.get("env_ranges", {}).get(env) or base["ranges"]).get(k)
        v = mt[k]
        verdict = judge(k, v, q)
        if "**" in verdict: flags.append(f"{label}: {v} ({verdict.replace('**', '')})")
        rng = f"{q['p50']} ({q['p10']}-{q['p90']})" if q else ""
        lines.append(f"| {label} | {v if v is not None else 'n/a'} | {rng} | {verdict} | " +
                     " | ".join(str(r["metrics"].get(k)) for r in refs) + " |")
    lines += ["", "## Flags", ""] + ([f"- {f}" for f in flags] or ["- none"])
    lines += ["", "## Visual review", "", "Apply `review/RUBRIC.md` to `sheet.png` and record the findings in "
              "`review/reviews/`.", ""]
    with open(os.path.join(out_dir, "review.md"), "w", encoding="utf-8") as f: f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"\nSheet: {os.path.join(out_dir, 'sheet.png')}")
    return mt, flags


if __name__ == "__main__":
    if "--calibrate" in sys.argv: calibrate()
    elif len(sys.argv) > 1: review(sys.argv[1])
    else: print(__doc__)
