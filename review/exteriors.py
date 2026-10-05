"""How full a map's exteriors are: props on the outdoor ground against Westwood's maps of the same environment.

    py review/exteriors.py <map or json> [...]        our maps
    py review/exteriors.py --westwood [type ...]      Westwood's single-player maps by environment (town, castle...)
    py review/exteriors.py --westwood --save          ...and write review/exteriors_baseline.json (each environment's
                                                      median, p75 and p90 of every measure), which tests/qa.py reads
    py review/exteriors.py <map> --holes [--out png]  also draws the empty ground over the map's render

Open ground: outdoor floor tiles (review/design.Outdoor: outside rooms, no water, lava or void) that are not a road
or path. A prop: any decoration on the ground (rules/decoration.classify), plants and trees included, but not
pebbles or the tiniest rocks, which read as nothing from a player's height (2026-10-05 playtest: an alley with "one
bush and a couple of tiny pebbles" is empty). Measures, per 100 open tiles: props, distinct prop types; and the
share of open tiles with no prop within 4 and within 6 cells (92 and 138 px): the empty stretches.
Where props stand: "wall" within 1.5 cells of a wall, else "open"; the commonest non-plant types of each.
"""
import collections, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "validate"))
sys.path.insert(0, os.path.join(REPO, "rules"))
sys.path.insert(0, HERE)
import mapdata as md
import decoration as D
import design as DS

BASELINE = os.path.join(HERE, "exteriors_baseline.json")      # Westwood's measures by environment (--westwood --save)
TRIVIAL = {"CaveRocksPebbles", "CaveRocksTiny", "CaveRocksSmall"}
NATURE = {"tree", "plant", "flower_tuft"}
SKIP = {None, "ambient_sound", "blocker"}
CELL = md.CELL


def props_of(m, od):
    out = []
    for cat, objs in od.deco.items():
        if cat in SKIP: continue
        for o in objs:
            t = o["type"].replace("Immobile", "")
            if t in TRIVIAL or t.startswith("ColorLight") or "Shadow" in t: continue
            out.append((cat, o))
    return out


def measure(m, radii=(4, 6), holes=False):
    od = DS.Outdoor(m)
    import checks as C
    indoor = {t for t, rec in C.declared_rooms(m).items() if not rec.get("yard")}   # a generated map's own rooms
    for t in indoor: od.ground.pop(t, None)
    for cat in od.deco:
        od.deco[cat] = [o for o in od.deco[cat] if m.tile_at_cell(m.cell_of(o["x"], o["y"])) in od.ground]
    open_ = [t for t in od.ground if t not in od.paths]
    props = props_of(m, od)
    grid = collections.defaultdict(list)
    for _, o in props: grid[(int(o["x"] // 92), int(o["y"] // 92))].append((o["x"], o["y"]))

    def nearest(x, y, lim):
        best = lim + 1
        k = int(lim // 92) + 1
        for a in range(int(x // 92) - k, int(x // 92) + k + 1):
            for b in range(int(y // 92) - k, int(y // 92) + k + 1):
                for px, py in grid.get((a, b), ()):
                    d = math.hypot(px - x, py - y)
                    if d < best: best = d
        return best
    empty = {r: [] for r in radii}
    for t in open_:
        x, y = (t[0] + 1) * CELL, (t[1] + 1) * CELL
        d = nearest(x, y, max(radii) * CELL)
        for r in radii:
            if d > r * CELL: empty[r].append(t)
    wall_cells = set(m.walls)
    place = {"wall": collections.Counter(), "open": collections.Counter()}
    for cat, o in props:
        c = m.cell_of(o["x"], o["y"])
        near_wall = any((c[0] + a, c[1] + b) in wall_cells for a in (-1, 0, 1) for b in (-1, 0, 1))
        if cat in NATURE or cat == "rock": continue
        place["wall" if near_wall else "open"][D.base_name(o["type"])] += 1
    n = max(1, len(open_))
    made = [o for c, o in props if c not in NATURE and c != "rock"]
    res = dict(open=len(open_), props=round(100 * len(props) / n, 1), made=round(100 * len(made) / n, 1),
               types=len({o["type"] for _, o in props}), made_types=len({D.base_name(o["type"]) for o in made}),
               **{f"empty{r}": round(len(empty[r]) / n, 3) for r in radii}, place=place)
    if holes: res["holes"] = empty
    return res


def show(name, r, top=10):
    print(f"{name:12s} open {r['open']:5d}  props/100 {r['props']:5.1f}  made/100 {r['made']:5.1f}  types {r['types']:3d} "
          f"made types {r['made_types']:3d}  empty>4 {r['empty4']:.2f}  empty>6 {r['empty6']:.2f}")
    for k in ("wall", "open"):
        c = r["place"][k]
        if c: print(f"    {k:4s}: " + ", ".join(f"{t} {v}" for t, v in c.most_common(top)))


def draw_holes(map_path, m, r, out):
    """The empty ground (no prop within 4 cells) tinted red, within 6 cells darker, over the map's render."""
    import subprocess
    from PIL import Image, ImageDraw
    name = os.path.splitext(os.path.basename(map_path))[0]
    full = os.path.join(HERE, "out", name, "full.png")
    if not os.path.exists(full) or os.path.getmtime(full) < os.path.getmtime(map_path):
        os.makedirs(os.path.dirname(full), exist_ok=True)
        subprocess.run([os.path.join(REPO, "MapEditor", "bin", "Release", "MapEditor.exe"), map_path,
                        "--render-image", full, "full:5880"], timeout=900)
    im = Image.open(full).convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for rad, col in ((4, (255, 60, 40, 70)), (6, (255, 0, 0, 90))):
        for t in r["holes"][rad]:
            x, y = (t[0] + 1) * CELL, (t[1] + 1) * CELL
            d.polygon([(x, y - CELL), (x + CELL, y), (x, y + CELL), (x - CELL, y)], fill=col)
    im = Image.alpha_composite(im, ov).convert("RGB")
    bbox = im.point(lambda v: 255 if v > 12 else 0).getbbox()
    if bbox: im = im.crop(bbox)
    k = 1800 / max(im.size)
    im.resize((int(im.width * k), int(im.height * k))).save(out)
    print(out)


def main():
    args = sys.argv[1:]
    if args and args[0] == "--westwood":
        import json
        env = json.load(open(os.path.join(REPO, "rules", "out", "environments.json")))["maps"]
        types = [a for a in args[1:] if not a.startswith("--")] or ["town", "castle", "forest", "swamp", "cave", "ice", "lava"]
        groups = {}
        for t in types:
            names = sorted(n for n, v in env.items() if v["type"] == t)
            agg, place = collections.defaultdict(list), {"wall": collections.Counter(), "open": collections.Counter()}
            seen = set()
            for n in names:
                if n[3:] in seen: continue                 # one map of each layout (Con/War/Wiz share most)
                seen.add(n[3:])
                m = md.load(md.corpus_json(n))
                r = measure(m)
                if r["open"] < 200: continue
                show(n, r, top=6)
                for k in ("props", "made", "types", "made_types", "empty4", "empty6"): agg[k].append(r[k])
                for k in place: place[k].update(r["place"][k])
            if not agg: continue
            q = lambda v, f: sorted(v)[min(len(v) - 1, int(f * len(v)))]
            med = {k: q(v, 0.5) for k, v in agg.items()}
            print(f"== {t}: {len(agg['props'])} maps, median " + "  ".join(f"{k} {v}" for k, v in med.items()))
            for k in place: print(f"   {k}: " + ", ".join(f"{a} {b}" for a, b in place[k].most_common(24)))
            groups[t] = {k: dict(n=len(v), p25=q(v, 0.25), p50=q(v, 0.5), p75=q(v, 0.75), p90=q(v, 0.9))
                         for k, v in agg.items()}
        if "--save" in args:
            import json
            with open(BASELINE, "w") as f: json.dump(groups, f, indent=1, sort_keys=True)
            print(f"written: {BASELINE}")
        return
    holes = "--holes" in args
    out = args[args.index("--out") + 1] if "--out" in args else None
    paths = [a for a in args if not a.startswith("--") and a != out]
    for p in paths:
        m = md.load(p)
        r = measure(m, holes=holes)
        show(os.path.splitext(os.path.basename(p))[0], r)
        if holes:
            name = os.path.splitext(os.path.basename(p))[0]
            draw_holes(p, m, r, out or os.path.join(HERE, "out", name, "empty.png"))


if __name__ == "__main__":
    main()
