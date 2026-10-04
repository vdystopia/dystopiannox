"""Scores every declared room of a generated map (its <map>.rooms.json) on what the room reviews asked for:

- coverage: the share of the floor that furniture covers, against the kind's ROOM_COVER target (kit/identity.py)
  and Westwood's median for rooms of its kind and size;
- middle: coverage by pieces standing free in the room (more than 2.5 units from every wall);
- lined: the share of the back walls (NE and NW, the walls the camera sees) taken by tall pieces and hangings;
- types: distinct object types in the room;
- warnings: the checker's findings that fall in the room.

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
from kit.identity import ROOM_COVER, ROOM_COVER_DEFAULT, WESTWOOD_KIND

TALL = re.compile(r"^(Bookcase|PotionShelves|LogShelves|TraderShelves|TraderHelmShelf|Desk\d|Fireplace|WallFireplace|"
                  r"Stove0|Cauldron|CinderBin|Bellows|AlchemistDesk|WizardWorkstation|Chest\d|DunMirChest|Bed\d|WoodBed|Cot\d|Bench|"
                  r"LightBench|CushionedBench|TraderPoleArm|TraderArmorRack|TraderBowRack|TraderClothesRack)")


def score(map_path):
    m = MD.load(map_path)
    _, findings, _ = V.validate(map_path)
    base = V.baseline().get("room_kinds", {})
    rows = []
    for r in C.find_rooms(m):
        d = r.get("declared")
        if not d: continue
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
        for (line, coord), (a0, a1) in runs.items():
            if C._wall_name(line, coord, cu, cv) in ("NE", "NW"): back_len += a1 - a0
        for o in r["objects"]:
            u, v = C.uv_of(o)
            dist = min((abs(u - c) if l == "/" else abs(v - c)) for (l, c) in runs) if runs else 0
            if dist > 2.5 and m.blocking(o) and C.RT.family(o["type"]) in C.RT.BLOCKING_FAMILIES: mid += C.piece_area(o)
            if TALL.match(o["type"]) or C.RT.family(o["type"]) == "wall_decor":
                hit = C._against(o, runs, cu, cv, m, reach=1.6)
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
        box = (min(x for x, _ in cells), min(y for _, y in cells), max(x for x, _ in cells), max(y for _, y in cells))
        warns = [f for f in findings if f["severity"] != "info" and f.get("x") is not None and
                 box[0] <= f["x"] / 23 <= box[2] + 1 and box[1] <= f["y"] / 23 <= box[3] + 1]
        target = min(lo, max(ww * 1.25, 0.10))
        from kit.identity import ROOMS
        lines_walls = any(st.get("slot") == "line" for st in (ROOMS.get(kind, {}).get("compose") or []) + (ROOMS.get(kind, {}).get("fill") or []))
        ok = cover >= target and not warns and (not lines_walls or lined >= (0.35 if r["tiles"] >= 40 else 0.25))
        rows.append(dict(number=d["number"], kind=kind, purpose=d.get("purpose", ""), tiles=r["tiles"], cover=cover,
                         target=target, lo=lo, hi=hi, ww=ww, middle=mid / (2 * len(cells)), lined=lined,
                         types=len({o["type"] for o in r["objects"]}), pieces=len(r["objects"]), warns=warns, ok=ok))
    rows.sort(key=lambda x: x["number"])
    return rows


def report(map_path, rows):
    name = os.path.splitext(os.path.basename(map_path))[0]
    out = [f"# Room scores: {name}", "",
           f"{sum(r['ok'] for r in rows)} of {len(rows)} rooms pass (coverage at target, no warnings, back walls 35% "
           f"lined).", "",
           "| # | Kind | Size | Tiles | Coverage | Target | Westwood | Middle | Lined | Types | Pieces | Warnings |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        mark = "" if r["ok"] else " **x**"
        out.append(f"| {r['number']}{mark} | {r['kind']} | {r['purpose'].split(',')[0]} | {r['tiles']} | {r['cover']:.2f} | "
                   f"{r['target']:.2f} | {r['ww']:.2f} | {r['middle']:.2f} | {r['lined']:.2f} | {r['types']} | "
                   f"{r['pieces']} | {'; '.join(w['msg'][:70] for w in r['warns'])} |")
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
