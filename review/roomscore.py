"""Scores every declared room of a generated map (its <map>.rooms.json) against its own room type.

There is no one yardstick for a good room (Starwell playtest, 2026-10-05: "A throne room, however, is very different
than a study and should, by its nature, be more open with less object density ... There is really no one-size-fits-all
approach for room design"). Each room's kind maps to a type (mapgen/kit/roomtypes.py: bedroom, study, throne room,
chapel...), whose brief is rules/rooms/<type>.md and whose profile sets what the room is judged on:

- cover: the share of the floor furniture covers, in the type's range (a throne room 0.03-0.12, a storeroom 0.15-0.42);
- open: the share of the floor clear of every blocking piece, in the type's range (review/roommeasure.py);
- per tile: furnishings per floor tile, in range; types: distinct object types, at least the type's least (fewer in a
  small room);
- repeat: the most pieces of one stand-alone kind, under the type's cap for the room's size; caps: the repeated sets
  (columns, pews, benches, tables, racks) under the type's caps (the furnisher holds the same caps);
- must / never: the families the type needs, and those that never belong in it;
- focal: the piece the room is arranged round is there and where the type puts it (a desk on a back wall, a throne
  or an altar on the wall across from a door);
- walls: walls with a purpose; lined: the back walls lined, for the types that line them;
- reads as: what the contents read as (kit/roomtypes.py reads_as). A room that reads as another type, not its kin, is
  flagged (the college laboratory that read as "some sort of shoddy mess hall"), a room that reads strongly as a second,
  unrelated type too (two rooms in one), and a room whose type is unclear (its defining piece missing);
- warnings: the checker's findings that fall in the room.

A room passes when every check holds. The score is the share of checks that hold.

    py review/roomscore.py <map> [--md out.md]

Writes review/out/<map>/roomscore.md and prints it: every room, then a table by type.
"""
import collections, math, os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "validate")); sys.path.insert(0, os.path.join(REPO, "mapgen"))
sys.path.insert(0, os.path.join(REPO, "rules")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapdata as MD, checks as C, validate as V
import roommeasure as RM
from kit.roomtypes import profile, reads_as, TYPES

OPPOSITE = {"NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW"}


def room_doors(m, r, cu, cv):
    """Names of the walls (NE, NW, SE, SW) the room's doorways stand in."""
    cells = set(r["cells"])
    out = []
    for d in m.doors:
        gx, gy = d["gap"]
        if not any((gx + a, gy + b) in cells for a in (-1, 0, 1) for b in (-1, 0, 1)): continue
        coord = gx + gy + 1 if d["line"] == "/" else gx - gy
        out.append(C._wall_name(d["line"], coord, cu, cv))
    return out


def cap_for(spec, tiles, least=0):
    per, most = spec
    return max(least, min(most, int(tiles / per)))


def judge(m, r, kind, tiles_declared, warns):
    """[(check, ok, detail)] for room r of kit kind `kind` against its type's profile, and the measure."""
    p = profile(kind)
    me = RM.measure(m, r)
    tiles = me["tiles"]
    fam, kinds = me["fam"], me["kinds"]
    out = []
    if not p:
        return [("type", False, f"no room type for kind {kind}")], me, None
    lo, _, hi = p["cover"]
    out.append(("cover", lo <= me["cover"] <= hi, f"{me['cover']:.2f} (wants {lo:.2f}-{hi:.2f})"))
    olo, ohi = p["open"]
    out.append(("open", olo <= me["open"] <= ohi, f"{me['open']:.2f} (wants {olo:.2f}-{ohi:.2f})"))
    plo, phi = p["per_tile"]
    out.append(("per tile", plo <= me["per_tile"] <= phi, f"{me['per_tile']:.2f} (wants {plo:.2f}-{phi:.2f})"))
    tmin = min(p["types_min"], round(2 + tiles / 6))          # a small room has room for fewer kinds of piece
    out.append(("types", me["types"] >= tmin, f"{me['types']} (wants {tmin}+)"))
    least, per = p["free_most"]
    skip = set(p.get("free_skip", ("chair",))) | set(p.get("caps", {}))
    free = collections.Counter(RM.kind_of(o["type"]) for o in r["objects"]
                               if C.RT.family(o["type"]) and not RM.LINED.match(o["type"]) and
                               C.RT.family(o["type"]) not in {"wall_decor", "rug"} | skip)
    fk, fn = free.most_common(1)[0] if free else ("", 0)
    fcap = max(least, int(tiles / per))
    out.append(("repeat", fn <= fcap, f"{fn} {fk} (at most {fcap})"))
    over = []
    for f, spec in p.get("caps", {}).items():
        c = cap_for(spec, tiles_declared, p["must"].get(f, 0))
        n = fam.get(f, 0)
        if f == "throne": n = min(n, 1)
        if n > c: over.append(f"{n} {f} (cap {c})")
    out.append(("caps", not over, "; ".join(over)))
    short = [f"{f} {fam.get(f, 0)}/{n}" for f, n in p["must"].items() if fam.get(f, 0) < n and
             not (f == "smithy" and fam.get(f, 0) >= 1)]
    out.append(("must", not short, "; ".join(short)))
    bad = sorted({f for f in p.get("never", ()) if fam.get(f)})
    if p.get("never_types"):
        rx = re.compile(p["never_types"])
        bad += sorted({o["type"] for o in r["objects"] if C.RT.family(o["type"]) and rx.search(o["type"])})
    out.append(("never", not bad, ", ".join(bad[:4])))
    fo = p.get("focal")
    if fo:
        rx = re.compile(fo["types"])
        foc = [o for o in r["objects"] if rx.search(o["type"])]
        cu, cv = me["centre"]
        if not foc:
            out.append(("focal", False, f"no {fo['types'].strip('^')}"))
        elif fo["where"] in ("back", "door"):
            walls = {(C._against(o, me["runs"], cu, cv, m, reach=fo.get("reach", 1.8), across=True) or (None,))[0]
                     for o in foc}
            walls.discard(None)
            if fo["where"] == "back":
                ok = bool(walls & {"NE", "NW"})
                out.append(("focal", ok, f"{foc[0]['type']} on {'/'.join(sorted(walls)) or 'no wall'} (wants a back wall)"))
            else:
                doors = room_doors(m, r, cu, cv)
                ok = any(OPPOSITE.get(w) in doors for w in walls)
                out.append(("focal", ok, f"{foc[0]['type']} on {'/'.join(sorted(walls)) or 'no wall'}, doors "
                                         f"{'/'.join(sorted(set(doors))) or 'none'} (wants the wall across from a door)"))
        else:
            out.append(("focal", True, foc[0]["type"]))
    wmin = p["walls_min"] - (1 if tiles < 32 else 0)          # a small room's door and its way in take a wall
    out.append(("walls", me["walls"] >= wmin, f"{me['walls']} (wants {wmin}+)"))
    if p.get("lined") is not None:
        want = p["lined"] - (0.10 if tiles < 40 else 0.0)
        out.append(("lined", me["lined"] >= want, f"{me['lined']:.2f} (wants {want:.2f}+)"))
    ranked = reads_as(fam, me["all_kinds"], kind)
    mine = next((s for t, s in ranked if t == p["type"]), 0.0)
    top, ts = ranked[0] if ranked else (None, 0.0)
    if mine == 0:
        out.append(("reads as", False, f"unclear: reads as {top or 'nothing'}, not a {p['type'].replace('_', ' ')}"))
    elif top != p["type"] and top not in p.get("kin", ()) and ts >= 1.25 * mine:
        out.append(("reads as", False, f"{top.replace('_', ' ')} ({ts} against {mine})"))
    elif any(t != p["type"] and t not in p.get("kin", ()) + ("storeroom",) and s_ >= max(8.0, 0.6 * mine) for t, s_ in ranked):
        # two rooms in one: the old college laboratory's tesla coils with a mess hall's tables and chairs down its middle
        t, s_ = next((t, s_) for t, s_ in ranked if t != p["type"] and t not in p.get("kin", ()) + ("storeroom",) and s_ >= max(8.0, 0.6 * mine))
        out.append(("reads as", False, f"mixed: a {p['type'].replace('_', ' ')} ({mine}) and a {t.replace('_', ' ')} ({s_})"))
    else:
        out.append(("reads as", True, p["type"] if top == p["type"] else f"{p['type']} (or its kin {top})"))
    out.append(("warnings", not warns, "; ".join(w["msg"][:70] for w in warns[:2])))
    return out, me, p


def score(map_path):
    m = MD.load(map_path)
    _, findings, _ = V.validate(map_path)
    rows = []
    for r in C.find_rooms(m):
        d = r.get("declared")
        if not d or d.get("yard"): continue              # yards (kit/yards.py) are not rooms
        cells = r["cells"]
        near = {(x + a, y + b) for x, y in cells for a in (-1, 0, 1) for b in (-1, 0, 1)}   # its floor and walls
        warns = [f for f in findings if f["severity"] != "info" and f.get("x") is not None and
                 (int(f["x"] // 23), int(f["y"] // 23)) in near]
        checks, me, p = judge(m, r, d["kind"], d.get("tiles") or r["tiles"], warns)
        ok = all(c[1] for c in checks)
        rows.append(dict(number=d["number"], kind=d["kind"], type=(p or {}).get("type", "?"),
                         family=(p or {}).get("family", "?"), purpose=d.get("purpose", ""), tiles=r["tiles"],
                         cover=me["cover"], open=me["open"], per_tile=me["per_tile"], types=me["types"],
                         pieces=me["pieces"], walls=me["walls"], lined=me["lined"], middle=me["middle"],
                         target=(p or {}).get("cover", (0.0,))[0],     # the least its type covers (tests/qa.py)
                         score=sum(c[1] for c in checks) / len(checks), ok=ok, checks=checks, warns=warns,
                         flags=[f"{c[0]}: {c[2]}" for c in checks if not c[1]]))
    rows.sort(key=lambda x: x["number"])
    return rows


def report(map_path, rows):
    name = os.path.splitext(os.path.basename(map_path))[0]
    out = [f"# Room scores by type: {name}", "",
           f"{sum(r['ok'] for r in rows)} of {len(rows)} rooms pass their type's profile (mapgen/kit/roomtypes.py; the "
           f"briefs: rules/rooms/<type>.md). Score: the share of the type's checks that hold.", "",
           "| # | Type (kind) | Room | Tiles | Cover | Open | Per tile | Types | Walls | Lined | Score | Falls short |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        mark = "" if r["ok"] else " **x**"
        kind = r["type"].replace("_", " ") + ("" if r["kind"] == r["type"] else f" ({r['kind'].replace('_', ' ')})")
        out.append(f"| {r['number']}{mark} | {kind} | {r['purpose'].split(',')[0]} | {r['tiles']} | {r['cover']:.2f} | "
                   f"{r['open']:.2f} | {r['per_tile']:.2f} | {r['types']} | {r['walls']} | {r['lined']:.2f} | "
                   f"{r['score']:.2f} | {'; '.join(r['flags'])} |")
    out += ["", "## By type", "",
            "| Family | Type | Rooms | Pass | Mean score | Cover | Open | Wants cover | Wants open |",
            "|---|---|---|---|---|---|---|---|---|"]
    by = collections.defaultdict(list)
    for r in rows: by[r["type"]].append(r)
    order = {t: i for i, t in enumerate(TYPES)}
    for t, rs in sorted(by.items(), key=lambda kv: order.get(kv[0], 99)):
        p = TYPES.get(t, {})
        n = len(rs)
        out.append(f"| {p.get('family', '?')} | {t} | {n} | {sum(r['ok'] for r in rs)} | {sum(r['score'] for r in rs) / n:.2f} | "
                   f"{sum(r['cover'] for r in rs) / n:.2f} | {sum(r['open'] for r in rs) / n:.2f} | "
                   f"{p.get('cover', (0, 0, 0))[0]:.2f}-{p.get('cover', (0, 0, 0))[2]:.2f} | "
                   f"{p.get('open', (0, 0))[0]:.2f}-{p.get('open', (0, 0))[1]:.2f} |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    path = sys.argv[1]
    rows = score(path)
    text = report(path, rows)
    name = os.path.splitext(os.path.basename(path))[0]
    od = os.path.join(REPO, "review", "out", name)
    os.makedirs(od, exist_ok=True)
    md_out = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else os.path.join(od, "roomscore.md")
    with open(md_out, "w", encoding="utf-8") as f: f.write(text)
    print(text)
