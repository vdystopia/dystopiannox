"""Builds the reference corpus of all stock Nox maps:

  corpus/out/json/<map>.json     every wall, tile, edge, object (with all settings), waypoint,
                                 polygon, group and script name, exported via the editor library
  corpus/out/images/<map>.png    the whole map rendered in game graphics (editor --render-image)
  corpus/out/thumbs/<map>.jpg    small previews
  corpus/out/nox_corpus.db       everything above in SQLite for querying
  corpus/out/atlas.md            one line per map: category, size, counts

Usage:  py corpus/build_corpus.py [--skip-images] [--only con07b,war01a]
Derived from the game's files, so corpus/out/ stays out of git.
"""
import argparse, glob, json, os, re, sqlite3, subprocess, sys, winreg

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
PS32 = os.path.join(os.environ["WINDIR"], "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
EDITOR = os.path.join(REPO, "MapEditor", "bin", "Release", "MapEditor.exe")
GENERATED = {"dyscrypt", "mossford"}          # our own maps are not reference material


def nox_dir():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Westwood\Nox") as k:
            return os.path.dirname(winreg.QueryValueEx(k, "InstallPath")[0])
    except OSError:
        return r"C:\GOG Games\Nox"


def category(name):
    n = name.lower()
    m = re.match(r"(con|war|wiz)(\d\d)([a-z])$", n)
    if m: return "campaign", {"con": "conjurer", "war": "warrior", "wiz": "wizard"}[m[1]], int(m[2]), m[3]
    if n.startswith("g_"): return "quest", None, None, None
    if n.startswith("so_"): return "social", None, None, None
    return "multiplayer", None, None, None


def export(maps):
    os.makedirs(os.path.join(OUT, "json"), exist_ok=True)
    lst = os.path.join(OUT, "maplist.txt")
    with open(lst, "w", encoding="utf-8") as f: f.write("\n".join(maps))
    res = subprocess.run([PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(HERE, "dump_maps.ps1"),
                          "-MapList", lst, "-OutDir", os.path.join(OUT, "json")], capture_output=True, text=True)
    fails = [l for l in res.stdout.splitlines() if l.startswith("FAIL")]
    print(f"exported {res.stdout.count('OK') - 1} maps, {len(fails)} failures", *fails, res.stderr.strip(), sep="\n")


def render(maps, size=2940, workers=4):
    """Renders maps with several editor processes at once; existing complete images are kept."""
    from concurrent.futures import ThreadPoolExecutor
    from PIL import Image
    for d in ("images", "thumbs"): os.makedirs(os.path.join(OUT, d), exist_ok=True)

    def complete(png):
        try:
            Image.open(png).load(); return True
        except Exception:
            return False

    def one(path):
        name = os.path.splitext(os.path.basename(path))[0]
        png = os.path.join(OUT, "images", name + ".png")
        if not (os.path.exists(png) and complete(png)):
            subprocess.run([EDITOR, path, "--render-image", png, str(size)], timeout=900)
        if os.path.exists(png) and complete(png):
            im = Image.open(png); im.thumbnail((900, 900)); im.convert("RGB").save(os.path.join(OUT, "thumbs", name + ".jpg"), quality=85)
            return None
        return name

    with ThreadPoolExecutor(workers) as pool:
        failed = [n for n in pool.map(one, maps) if n]
    print(f"rendered {len(maps) - len(failed)}/{len(maps)}", *(["failed: " + ", ".join(failed)] if failed else []), flush=True)


SCHEMA = """
CREATE TABLE maps(name TEXT PRIMARY KEY, category TEXT, class TEXT, chapter INT, part TEXT, type INT,
  summary TEXT, description TEXT, ambient TEXT, n_walls INT, n_tiles INT, n_objects INT, n_waypoints INT,
  n_polygons INT, n_script_funcs INT, min_x INT, max_x INT, min_y INT, max_y INT);
CREATE TABLE walls(map TEXT, x INT, y INT, facing INT, material TEXT, variation INT, minimap INT, props TEXT);
CREATE TABLE tiles(map TEXT, x INT, y INT, material TEXT, variation INT, n_edges INT);
CREATE TABLE edges(map TEXT, x INT, y INT, base TEXT, overlay TEXT, variation INT, dir INT, edge_type TEXT);
CREATE TABLE objects(map TEXT, id INT, parent INT, type TEXT, x REAL, y REAL, extent INT, team INT, scr TEXT,
  xtype TEXT, class TEXT, xfer TEXT, extra INT);
CREATE TABLE waypoints(map TEXT, n INT, name TEXT, x REAL, y REAL, flags INT);
CREATE TABLE waypoint_links(map TEXT, a INT, b INT, flag INT);
CREATE TABLE polygons(map TEXT, idx INT, name TEXT, ambient TEXT, minimap INT, enter_player TEXT, points TEXT);
CREATE TABLE groups_(map TEXT, name TEXT, type TEXT, n INT, members TEXT);
CREATE TABLE script_funcs(map TEXT, name TEXT);
CREATE TABLE things(name TEXT PRIMARY KEY, class TEXT, xfer TEXT, ext TEXT, ex INT, ey INT, health INT, flags TEXT);
"""


def build_db():
    db_path = os.path.join(OUT, "nox_corpus.db")
    if os.path.exists(db_path): os.remove(db_path)
    db = sqlite3.connect(db_path); db.executescript(SCHEMA)
    g = json.load(open(os.path.join(OUT, "json", "things.json"), encoding="utf-8"))
    F = [f["name"] for f in g["floors"]]; W = [w["name"] for w in g["walls"]]; E = [e["name"] for e in g["edges"]]
    tclass = {t["name"]: t["class"] for t in g["things"]}
    db.executemany("INSERT INTO things VALUES(?,?,?,?,?,?,?,?)",
                   [(t["name"], t["class"], t["xfer"], t["ext"], t["ex"], t["ey"], t["health"], t["flags"]) for t in g["things"]])
    atlas = []
    for jf in sorted(glob.glob(os.path.join(OUT, "json", "*.json"))):
        if jf.endswith("things.json"): continue
        d = json.load(open(jf, encoding="utf-8")); n = d["name"]
        cat, cls, ch, part = category(n)
        xs = [w[0] for w in d["walls"]] + [t[0] for t in d["tiles"]] or [0]
        ys = [w[1] for w in d["walls"]] + [t[1] for t in d["tiles"]] or [0]
        db.execute("INSERT INTO maps VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (n, cat, cls, ch, part, d["info"]["type"], d["info"]["summary"], d["info"]["description"],
                    json.dumps(d["ambient"]), len(d["walls"]), len(d["tiles"]), len(d["objects"]), len(d["waypoints"]),
                    len(d["polygons"]), len(d["script"]["funcs"]), min(xs), max(xs), min(ys), max(ys)))
        db.executemany("INSERT INTO walls VALUES(?,?,?,?,?,?,?,?)",
                       [(n, x, y, f, W[m], v, mm, json.dumps(p) if p else None) for x, y, f, m, v, mm, p in d["walls"]])
        tiles = {(t[0], t[1]): F[t[2]] for t in d["tiles"]}
        db.executemany("INSERT INTO tiles VALUES(?,?,?,?,?,?)", [(n, x, y, F[m], v, len(e)) for x, y, m, v, e in d["tiles"]])
        db.executemany("INSERT INTO edges VALUES(?,?,?,?,?,?,?,?)",
                       [(n, x, y, F[m], F[eg], ev, ed, E[et]) for x, y, m, v, es in d["tiles"] for eg, ev, ed, et in es])
        rows, oid = [], [0]

        def add(o, parent):
            oid[0] += 1; me = oid[0]
            rows.append((n, me, parent, o["t"], o["x"], o["y"], o["ext"], o["team"], o["scr"], o["xtype"],
                         tclass.get(o["t"]), json.dumps(o["xfer"]) if o["xfer"] else None, o["term"]))
            for i in o["inv"]: add(i, me)
        for o in d["objects"]: add(o, None)
        db.executemany("INSERT INTO objects VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        db.executemany("INSERT INTO waypoints VALUES(?,?,?,?,?,?)", [(n, w["n"], w["name"], w["x"], w["y"], w["flags"]) for w in d["waypoints"]])
        db.executemany("INSERT INTO waypoint_links VALUES(?,?,?,?)", [(n, w["n"], l[0], l[1]) for w in d["waypoints"] for l in w["links"]])
        db.executemany("INSERT INTO polygons VALUES(?,?,?,?,?,?,?)",
                       [(n, i, p["name"], json.dumps(p["amb"]), p["mm"], p["enterP"], json.dumps(p["pts"])) for i, p in enumerate(d["polygons"])])
        db.executemany("INSERT INTO groups_ VALUES(?,?,?,?,?)", [(n, gr["name"], gr["type"], len(gr["members"]), json.dumps(gr["members"])) for gr in d["groups"]])
        db.executemany("INSERT INTO script_funcs VALUES(?,?)", [(n, f) for f in d["script"]["funcs"]])
        atlas.append((cat, cls or "", n, d["info"]["summary"] or "", max(xs) - min(xs), max(ys) - min(ys), len(d["walls"]),
                      len(d["tiles"]), len(d["objects"]), len(d["waypoints"]), len(d["script"]["funcs"])))
    for idx in ("walls(map)", "tiles(map)", "edges(map)", "objects(map)", "objects(type)", "walls(material)", "edges(base, overlay)"):
        db.execute(f"CREATE INDEX IF NOT EXISTS ix_{re.sub(r'[^a-z]', '_', idx)} ON {idx}")
    db.commit(); db.close()
    with open(os.path.join(OUT, "atlas.md"), "w", encoding="utf-8") as f:
        f.write("# Nox map corpus\n\n| category | class | map | summary | w x h (cells) | walls | tiles | objects | waypoints | script funcs |\n|---|---|---|---|---|---|---|---|---|---|\n")
        for a in sorted(atlas):
            f.write(f"| {a[0]} | {a[1]} | {a[2]} | {a[3]} | {a[4]}x{a[5]} | {a[6]} | {a[7]} | {a[8]} | {a[9]} | {a[10]} |\n")
    print(f"database: {db_path} ({len(atlas)} maps)")


def build_layout_groups(threshold=0.6):
    """Groups single-player maps that share a layout (class campaigns reuse maps): wall-position
    overlap above `threshold` counts as the same layout. Writes table layout_group and
    layout_groups.json; rule mining weights maps by 1 / group size."""
    import itertools
    db = sqlite3.connect(os.path.join(OUT, "nox_corpus.db"))
    names = [r[0] for r in db.execute("SELECT name FROM maps WHERE category IN ('campaign','quest') ORDER BY name")]
    walls = {n: set(db.execute("SELECT x, y FROM walls WHERE map=?", (n,)).fetchall()) for n in names}
    parent = {n: n for n in names}

    def find(n):
        while parent[n] != n: n = parent[n]
        return n
    for a, b in itertools.combinations(names, 2):
        A, B = walls[a], walls[b]
        if A and B and len(A & B) / len(A | B) > threshold:
            parent[find(b)] = find(a)
    groups = {}
    for n in names: groups.setdefault(find(n), []).append(n)
    db.execute("DROP TABLE IF EXISTS layout_group")
    db.execute("CREATE TABLE layout_group(map TEXT PRIMARY KEY, rep TEXT, size INT)")
    db.executemany("INSERT INTO layout_group VALUES(?,?,?)", [(m, rep, len(g)) for rep, g in groups.items() for m in g])
    db.commit(); db.close()
    json.dump(groups, open(os.path.join(OUT, "layout_groups.json"), "w"), indent=1)
    print(f"layout groups: {len(names)} single-player maps -> {len(groups)} distinct layouts")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-images", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    maps = sorted(p for p in glob.glob(os.path.join(nox_dir(), "maps", "*", "*.map"))
                  if os.path.splitext(os.path.basename(p))[0].lower() not in GENERATED)
    if a.only:
        keep = {s.lower() for s in a.only.split(",")}
        maps = [p for p in maps if os.path.splitext(os.path.basename(p))[0].lower() in keep]
    # campaign and quest maps first: they are the main reference for single-player work
    maps.sort(key=lambda p: (category(os.path.splitext(os.path.basename(p))[0])[0] not in ("campaign", "quest"), p.lower()))
    export(maps)
    build_db()
    build_layout_groups()
    if not a.skip_images:
        render(maps)
