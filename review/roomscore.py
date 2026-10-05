"""Scores every declared room of a generated map (its <map>.rooms.json) on what the room reviews asked for:

- coverage: the share of the floor that furniture covers, against the kind's ROOM_COVER target (kit/identity.py)
  and Westwood's median for rooms of its kind and size;
- middle: coverage by pieces standing free in the room (more than 2.5 units from every wall);
- lined: the share of the back walls (NE and NW, the walls the camera sees) taken by tall pieces (a bed by the width
  of its headboard) and hangings,
  less 3 units for each doorway in them (the door and its clearance);
- types: distinct object types in the room;
- walls: how many of its four walls have a purpose (a piece other than a light stands against it);
- repeat: the most pieces of one kind against one wall, of the kinds that stand alone (not bookcases, shelves, a bench of
  workstations, racks, beds, pews, the pieces Westwood lines walls with: kit/furnish.py NEVER_LINED and the rest);
- identity: what reads as a room with no identity (Starwell playtest, 2026-10-05: the college laboratory "almost looks
  like some sort of shoddy mess hall with random objects stuffed in it"): a showpiece repeated (an alchemist's desk,
  a generator, a telescope: kit/furnish.py SHOWPIECES), four or more of one stand-alone kind along one wall, more
  free-standing tables than its kind sets, pieces outside the room's identity;
- warnings: the checker's findings that fall in the room.

The reference for a good room is the playtester's own (Starwell seed 4, room 9, the archmagister's study, 66 tiles:
"This is an example of a very, very good room"): coverage 0.11, 17 types, 26 pieces, all four walls used, back walls
51% lined, the most of one stand-alone kind on a wall 2 (statues between candelabras), one group in the middle (a round
table and two chairs on a carpet), a curio standing free. PROCESS.md, "What a good room is".

    py review/roomscore.py <map> [--md out.md]

Writes review/out/<map>/roomscore.md and prints the table. A room passes when its coverage reaches the kind's target
(or Westwood's median for its size, whichever is higher, capped at the target), it has no warnings, and its back walls
are at least 35% lined (25% in rooms under 40 tiles).
"""
import collections, math, os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "validate")); sys.path.insert(0, os.path.join(REPO, "mapgen"))
sys.path.insert(0, os.path.join(REPO, "rules"))
import mapdata as MD, checks as C, validate as V
from kit.identity import ROOM_COVER, ROOM_COVER_DEFAULT, WESTWOOD_KIND, ROOMS

from kit.furnish import TALL_PIECES as TALL        # one list: the furnisher lines walls by the same measure
from kit.furnish import SHOWPIECES, SHOWPIECE_LIMIT, SHOWPIECE_BIG

# kinds that stand in rows or line walls by design: not counted as a piece repeated along a wall
LINED = re.compile(r"^(Bookcase|MovableBookcase|LogShelves|PotionShelves|WizardWorkstation|Trader|Bed|WoodBed|Cot|Bench|"
                   r"LightBench|CushionedBench|Crypt|Coffin|Column|CathedralColumn|LOTD|Barrel|Crate|DarkCrate|Sack|"
                   r"PiledBarrels|LargeBarrel|WaterBarrel|BarrelWithTools|Candleabra|Nightstand|Chest|OgreStraw)")
TABLES = re.compile(r"^(Table\d|RoundTable\d|SquareTable\d|OvalTable\d|RoundTableWithFood|SmallTable\d|OgreTable\d)$")


def _kind(t):
    return re.sub(r"(\d+[a-z]?|HalfFull|Empty|NE|NW|SE|SW|N|S|E|W)$", "", t)


def identity_flags(r, kind, runs, cu, cv, m):
    """What makes a room read as having no identity (see the module's notes). Returns (walls used, repeat, flags)."""
    flags, per_wall, used = [], collections.defaultdict(collections.Counter), set()
    show = collections.Counter()
    for o in r["objects"]:
        t = o["type"]
        hit = C._against(o, runs, cu, cv, m, reach=1.6, across=True)
        if hit and C.RT.family(t) not in (None, "light") and not t.startswith("Candleabra"): used.add(hit[0])
        if hit and not LINED.match(t) and C.RT.family(t) not in (None, "wall_decor", "light"): per_wall[hit[0]][_kind(t)] += 1
        sm = SHOWPIECES.match(t)
        if sm: show[sm.group(1)] += 1
    big = r["tiles"] >= SHOWPIECE_BIG
    for base, n in show.items():
        if n > SHOWPIECE_LIMIT.get(base, 1) + (1 if big else 0): flags.append(f"{n} {base}")
    rep_ = max((n for c in per_wall.values() for n in c.values()), default=0)
    if rep_ >= 4:
        w, (k, n) = max(((w, c.most_common(1)[0]) for w, c in per_wall.items()), key=lambda x: x[1][1])
        flags.append(f"{n} {k} on the {w} wall")
    ident = ROOMS.get(kind, {})
    tables = sum(1 for o in r["objects"] if TABLES.match(o["type"]))
    most = (ident.get("repeat", {}).get("table") or (None, None))[1]
    if most is not None and tables > most: flags.append(f"{tables} tables")
    pats = ident.get("types", {})
    strays = sorted({o["type"] for o in r["objects"] if (C.RT.family(o["type"]) in pats and
                     not re.search(pats[C.RT.family(o["type"])], o["type"]))})
    if strays: flags.append("outside its identity: " + ", ".join(strays[:3]))
    return len(used), rep_, flags


def score(map_path):
    m = MD.load(map_path)
    _, findings, _ = V.validate(map_path)
    base = V.baseline().get("room_kinds", {})
    rows = []
    for r in C.find_rooms(m):
        d = r.get("declared")
        if not d or d.get("yard"): continue              # yards (kit/yards.py) are not rooms
        kind = d["kind"]
        cells = r["cells"]
        cover = C.room_coverage(m, r)
        lo, hi = ROOM_COVER.get(kind, ROOM_COVER_DEFAULT)
        k = base.get(WESTWOOD_KIND.get(kind, kind)) or {}
        band = "coverage_large" if r["tiles"] >= 50 and k.get("coverage_large") else "coverage"
        ww = ((k.get(band) or {}).get("p50")) or 0.0
        runs = C.room_runs(m, cells)
        cu = sum(x + y + 1 for x, y in cells) / len(cells); cv = sum(x - y for x, y in cells) / len(cells)
        mid = 0.0
        back_len, back_used = 0.0, collections.defaultdict(list)
        doors = [(d["gap"][0] + d["gap"][1] + 1, d["gap"][0] - d["gap"][1]) for d in m.doors]
        for (line, coord), (a0, a1) in runs.items():
            if C._wall_name(line, coord, cu, cv) not in ("NE", "NW"): continue
            back_len += a1 - a0
            for du, dv in doors:                            # a doorway and its clearance cannot be lined
                if abs((du if line == "/" else dv) - coord) < 1.6 and a0 < (dv if line == "/" else du) < a1:
                    back_len -= 3.0
        for o in r["objects"]:
            u, v = C.uv_of(o)
            dist = min((abs(u - c) if l == "/" else abs(v - c)) for (l, c) in runs) if runs else 0
            if dist > 2.5 and m.blocking(o) and C.RT.family(o["type"]) in C.RT.BLOCKING_FAMILIES: mid += C.piece_area(o)
            if TALL.match(o["type"]) or C.RT.family(o["type"]) == "wall_decor":
                hit = C._against(o, runs, cu, cv, m, reach=1.6, across=True)   # a bed's headboard uses its wall too
                if hit and hit[0] in ("NE", "NW"):
                    ha = C._half_uv(o)[1] if hit[3] == "/" else C._half_uv(o)[0]
                    back_used[(hit[3], hit[4])].append((hit[2] - ha, hit[2] + ha))
        used = 0.0
        for spans in back_used.values():                    # union of the stretches along each wall
            spans.sort(); end = -1e9
            for a, b in spans:
                if b <= end: continue
                used += b - max(a, end); end = b
        lined = used / back_len if back_len else 0.0
        near = {(x + a, y + b) for x, y in cells for a in (-1, 0, 1) for b in (-1, 0, 1)}   # its floor and walls
        warns = [f for f in findings if f["severity"] != "info" and f.get("x") is not None and
                 (int(f["x"] // 23), int(f["y"] // 23)) in near]
        target = min(lo, max(ww * 1.25, 0.10))
        from kit.identity import ROOMS
        lines_walls = any(st.get("slot") == "line" for st in (ROOMS.get(kind, {}).get("compose") or []) + (ROOMS.get(kind, {}).get("fill") or []))
        ok = cover >= target and not warns and (not lines_walls or lined >= (0.35 if r["tiles"] >= 40 else 0.25))
        walls, rep_, flags = identity_flags(r, kind, runs, cu, cv, m)
        ok = ok and not flags
        rows.append(dict(number=d["number"], kind=kind, purpose=d.get("purpose", ""), tiles=r["tiles"], cover=cover,
                         target=target, lo=lo, hi=hi, ww=ww, middle=mid / (2 * len(cells)), lined=lined,
                         types=len({o["type"] for o in r["objects"]}), pieces=len(r["objects"]), warns=warns, ok=ok,
                         walls=walls, repeat=rep_, flags=flags))
    rows.sort(key=lambda x: x["number"])
    return rows


def report(map_path, rows):
    name = os.path.splitext(os.path.basename(map_path))[0]
    out = [f"# Room scores: {name}", "",
           f"{sum(r['ok'] for r in rows)} of {len(rows)} rooms pass (coverage at target, no warnings, back walls 35% "
           f"lined, an identity: no showpiece repeated, no stand-alone piece four times along a wall, no stray tables or "
           f"pieces). The reference room (Starwell's study): coverage 0.11, 17 types, 4 walls, repeat 2.", "",
           "| # | Kind | Size | Tiles | Coverage | Target | Westwood | Middle | Lined | Types | Walls | Repeat | Pieces | "
           "Identity | Warnings |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        mark = "" if r["ok"] else " **x**"
        out.append(f"| {r['number']}{mark} | {r['kind']} | {r['purpose'].split(',')[0]} | {r['tiles']} | {r['cover']:.2f} | "
                   f"{r['target']:.2f} | {r['ww']:.2f} | {r['middle']:.2f} | {r['lined']:.2f} | {r['types']} | "
                   f"{r['walls']} | {r['repeat']} | {r['pieces']} | {'; '.join(r['flags'])} | "
                   f"{'; '.join(w['msg'][:70] for w in r['warns'])} |")
    by_kind = collections.defaultdict(list)
    for r in rows: by_kind[r["kind"]].append(r)
    out += ["", "## By kind", "", "| Kind | Rooms | Pass | Mean coverage | Mean middle | Mean lined |", "|---|---|---|---|---|---|"]
    for k, rs in sorted(by_kind.items()):
        out.append(f"| {k} | {len(rs)} | {sum(r['ok'] for r in rs)} | {sum(r['cover'] for r in rs) / len(rs):.2f} | "
                   f"{sum(r['middle'] for r in rs) / len(rs):.2f} | {sum(r['lined'] for r in rs) / len(rs):.2f} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    path = sys.argv[1]
    rows = score(path)
    text = report(path, rows)
    name = os.path.splitext(os.path.basename(path))[0]
    od = os.path.join(REPO, "review", "out", name)
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "roomscore.md"), "w", encoding="utf-8") as f: f.write(text)
    print(text)
