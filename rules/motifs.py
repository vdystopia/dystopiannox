"""Westwood's arrangements, mined from its curated campaign rooms: the motifs the motif engine (mapgen/kit/motifs.py)
composes rooms from, instead of hand-written recipes.

The room lab's blind judges tell our recipe-built rooms from Westwood's by the same few things in every type: single
pieces evenly spaced along the walls, one stamped layout per type, a lone table dead centre, barrels in stepped lines
instead of heaps, formulas ("bookcase-desk-bookcase"). Westwood's rooms read as heaped, irregular and lived in. So this
learns the arrangements themselves, from the rooms of rules/rooms/westwood.json's index with the verdicts by eye of
rules/rooms/curated.json applied (kept and retyped rooms only; excluded rooms never), campaign maps only (Con, War,
Wiz; never the quest or multiplayer maps).

Every room is measured in its uv frame (u = x + y grows toward the SE wall, v = x - y toward the NE wall), with the
checker's own room finder, wall runs and doors (validate/checks.py), as the room lab measures it:

- **wall motifs**: for every stretch of wall (a wall run split at its doors), the pieces standing against it from one
  end to the other: each piece's type, category (kit/objects.py) and furniture family, its centre along the stretch
  (from the stretch's canonical start: the N corner's end on the back walls NE and NW, the S corner's end on the front
  walls SE and SW, so a motif carries to the mirror wall unchanged), its half length along the wall and depth into the
  room, its gap from the wall line (snugness), whether it hangs on the wall, and the heaps (pieces touching along the
  wall); the stretch's length, what bounds each end (a corner or a door) and the share of it in use (bare, half or
  full). Bare stretches are motifs too: they carry how often a wall stays bare.
- **corner motifs**: the small pieces heaped in a corner (supplies, plants, statues, clutter, lights; never a bed, a
  table or a shelf, which belong to their wall), each piece's distance from the two walls that meet there.
- **centre motifs**: the free-standing groups (pieces within GROUP_GAP of each other, edge to edge, rugs with what
  stands on them): each piece's offset from the group's centre, the group's place in the room (normalised 0-1 over the
  room's u and v), its distance from the nearest wall.
- **rooms**: per room, which motifs it holds on which wall, the focal piece's wall (kit/roomtypes.py focal) and where
  that wall lies from the main door (opposite, beside or the door's own wall), how many corner and centre motifs, and
  whether the middle stays empty. The engine takes one Westwood room as a skeleton (which walls are used, how many
  corners and groups) and fills it with motifs from other rooms.
- **stats** per type: walls bare / half / full on the back and front walls, corners and groups per room, the middle
  empty, lights per room, the share of rooms with a carpet laid in floor tiles, the focal's wall, and which motif contents occur together in one room (co-occurrence of the motifs' leading
  categories).

Writes rules/out/motifs.json and prints the counts. Run: py rules/motifs.py
"""
import collections, json, math, os, re, sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "review", "roomlab"))
import labenv as E            # noqa: E402  (sets the import paths: validate, mapgen, rules, review)
import labref                 # noqa: E402
C = E.C
RT = C.RT
from kit import objects as OBJ   # noqa: E402

OUT = os.path.join(HERE, "out", "motifs.json")
WALL_REACH = 1.0          # a floor piece's back within this of the wall line stands against the wall (as metrics.py)
HANG_REACH = 2.6          # a hanging or a mounted light
CORNER_BOX = 3.2          # a corner motif's pieces stand within this of both walls (centre to wall line, uv units)
CORNER_CATS = {"supply", "plant", "statue", "light", "clutter", "bones", "straw", "monument", "feature"}
CORNER_MAX_HALF = 1.4     # bigger pieces belong to their wall, never to a corner heap
GROUP_GAP = 1.0           # free pieces within this (edge to edge) form one centre group
HEAP_GAP = 0.4            # pieces along a wall within this of each other form a heap
DOOR_HALF = 1.0           # a doorway cuts this much either side of its centre from its wall's stretch
WALL_OF_CORNER = {frozenset(("NW", "NE")): "N", frozenset(("NE", "SE")): "E", frozenset(("SE", "SW")): "S",
                  frozenset(("SW", "NW")): "W"}
FROM_HI = {"NW", "SW"}    # the walls whose canonical start (the N or S corner) lies at the high end of the run


def piece_info(m, o):
    t = o["type"]
    fam = RT.family(t)
    cat = OBJ.category(t)
    if fam is None and cat != "light": return None
    if t in ("ColorLight",) or re.search(r"Door|Trigger|NPC|PlayerStart", t): return None
    hu, hv = C._half_uv(o)
    u, v = C.uv_of(o)
    blocking = bool(m.blocking(o))
    hang = fam == "wall_decor" or (cat == "light" and not blocking)
    return dict(t=t, cat=cat or fam, fam=fam or cat, u=u, v=v, hu=hu, hv=hv, blocking=blocking, hang=hang)


def _runs_with_names(m, cells, cu, cv):
    runs = C.room_runs(m, cells)
    out = {}
    for (line, coord), (lo, hi) in runs.items():
        out[(line, coord)] = dict(line=line, coord=coord, lo=lo, hi=hi, name=C._wall_name(line, coord, cu, cv))
    return runs, out


def mine_room(entry, m, r):
    """The motifs of one Westwood room. Returns (room record, [wall], [corner], [centre])."""
    import metrics
    cells = r["cells"]
    cu = sum(x + y + 1 for x, y in cells) / len(cells); cv = sum(x - y for x, y in cells) / len(cells)
    us = [x + y + 1 for x, y in cells]; vs = [x - y for x, y in cells]
    U0, U1, V0, V1 = min(us), max(us), min(vs), max(vs)
    runs, named = _runs_with_names(m, cells, cu, cv)
    rid = f"{entry['map']}@{entry['centre'][0]},{entry['centre'][1]}"
    pieces = []
    for o in r["objects"]:
        p = piece_info(m, o)
        if p: pieces.append((o, p))
    doors = metrics.room_doors(m, r, cu, cv)
    # every piece against a wall: (line, coord), along, gap
    for o, p in pieces:
        a = C._against(o, runs, cu, cv, m, reach=HANG_REACH if p["hang"] else WALL_REACH, across=True)
        p["wall"] = None
        if a:
            name, gap, along, line, coord = a
            p["wall"] = (line, coord); p["along"] = along; p["gap"] = round(gap, 3); p["wname"] = name
    # corners: where a '/' run meets a '\\' run inside the room
    corners = []
    slash = [x for x in named.values() if x["line"] == "/"]
    back = [x for x in named.values() if x["line"] == "\\"]
    for a in slash:
        for b in back:
            if not (b["lo"] - 1.5 <= a["coord"] <= b["hi"] + 1.5 and a["lo"] - 1.5 <= b["coord"] <= a["hi"] + 1.5): continue
            name = WALL_OF_CORNER.get(frozenset((a["name"], b["name"])))
            if not name: continue
            su = 1 if cu > a["coord"] else -1; sv = 1 if cv > b["coord"] else -1
            corners.append(dict(name=name, u=a["coord"], v=b["coord"], su=su, sv=sv))
    used = set()
    corner_motifs = []
    for c in corners:
        items = []
        for o, p in pieces:
            if id(o) in used: continue
            if p["cat"] not in CORNER_CATS or max(p["hu"], p["hv"]) > CORNER_MAX_HALF: continue
            da = (p["u"] - c["u"]) * c["su"]; db = (p["v"] - c["v"]) * c["sv"]
            if 0 < da <= CORNER_BOX and 0 < db <= CORNER_BOX:
                items.append(dict(t=p["t"], cat=p["cat"], fam=p["fam"], da=round(da, 3), db=round(db, 3),
                                  blocking=p["blocking"], hang=p["hang"]))
                used.add(id(o))
        if items:
            corner_motifs.append(dict(corner=c["name"], items=items))
    # wall stretches: each run split at its doors, measured from its canonical start
    wall_motifs = []
    for key, w in named.items():
        lo, hi = w["lo"] + 1.0, w["hi"] - 1.0
        if hi - lo < 1.5: continue
        cuts = []
        for du, dv, _, dname in doors:
            perp, along = (du, dv) if w["line"] == "/" else (dv, du)
            if abs(perp - w["coord"]) < 1.6 and lo - 1 <= along <= hi + 1: cuts.append(along)
        cuts.sort()
        bounds, start, kind0 = [], lo, "corner"
        for a in cuts:
            if a - DOOR_HALF - start >= 1.0: bounds.append((start, a - DOOR_HALF, kind0, "door"))
            start, kind0 = a + DOOR_HALF, "door"
        if hi - start >= 1.0: bounds.append((start, hi, kind0, "corner"))
        on_wall = [(o, p) for o, p in pieces if p["wall"] == key and id(o) not in used]
        for s0, s1, e0, e1 in bounds:
            L = s1 - s0
            hi_start = w["name"] in FROM_HI
            if hi_start: e0, e1 = e1, e0
            items = []
            for o, p in on_wall:
                if not (s0 - 0.5 <= p["along"] <= s1 + 0.5): continue
                ha, hp = (p["hv"], p["hu"]) if w["line"] == "/" else (p["hu"], p["hv"])
                s = (s1 - p["along"]) if hi_start else (p["along"] - s0)
                items.append(dict(t=p["t"], cat=p["cat"], fam=p["fam"], s=round(s, 3), ha=round(ha, 3),
                                  hp=round(hp, 3), gap=p["gap"], blocking=p["blocking"], hang=p["hang"]))
                used.add(id(o))
            items.sort(key=lambda x: x["s"])
            # heaps: floor pieces along the wall within HEAP_GAP of each other
            heap, hid = None, 0
            for x in items:
                if x["hang"]: x["heap"] = None; continue
                if heap is not None and x["s"] - x["ha"] - (heap["s"] + heap["ha"]) <= HEAP_GAP: x["heap"] = hid
                else:
                    hid += 1; x["heap"] = hid
                heap = x
            floor_len = sum(2 * x["ha"] for x in items if not x["hang"])
            share = min(1.0, floor_len / L) if L > 0 else 0.0
            wall_motifs.append(dict(wall=w["name"], back=w["name"] in ("NE", "NW"), L=round(L, 3), ends=[e0, e1],
                                    used=round(share, 3), items=items,
                                    heaps=sum(1 for k, n in collections.Counter(x["heap"] for x in items
                                                                                 if x.get("heap")).items() if n >= 2)))
    # centre groups: the rest, joined when within GROUP_GAP edge to edge (rugs with what stands on them)
    rest = [p for o, p in pieces if id(o) not in used]
    groups, seen = [], set()

    def edge(a, b):
        du = abs(a["u"] - b["u"]) - a["hu"] - b["hu"]; dv = abs(a["v"] - b["v"]) - a["hv"] - b["hv"]
        return max(du, dv)
    for i, p in enumerate(rest):
        if i in seen: continue
        comp, todo = [], [i]
        seen.add(i)
        while todo:
            k = todo.pop(); comp.append(rest[k])
            for j, q in enumerate(rest):
                if j not in seen and edge(rest[k], q) <= GROUP_GAP:
                    seen.add(j); todo.append(j)
        groups.append(comp)
    centre_motifs = []
    for g in groups:
        gu = (min(p["u"] - p["hu"] for p in g) + max(p["u"] + p["hu"] for p in g)) / 2
        gv = (min(p["v"] - p["hv"] for p in g) + max(p["v"] + p["hv"] for p in g)) / 2
        span = (round(max(p["u"] + p["hu"] for p in g) - min(p["u"] - p["hu"] for p in g), 3),
                round(max(p["v"] + p["hv"] for p in g) - min(p["v"] - p["hv"] for p in g), 3))
        wd = min([abs(gu - w["coord"]) if w["line"] == "/" else abs(gv - w["coord"]) for w in named.values()] or [0.0])
        centre_motifs.append(dict(pos=[round((gu - U0) / max(1, U1 - U0), 3), round((gv - V0) / max(1, V1 - V0), 3)],
                                  wall_dist=round(wd, 3), span=list(span),
                                  items=[dict(t=p["t"], cat=p["cat"], fam=p["fam"], du=round(p["u"] - gu, 3),
                                              dv=round(p["v"] - gv, 3), blocking=p["blocking"]) for p in g]))
    # the focal piece's wall, and where it lies from the main door
    from kit.roomtypes import TYPES
    fo = (TYPES.get(entry["type"]) or {}).get("focal")
    focal = None
    if fo:
        for wm in wall_motifs:
            if any(re.search(fo["types"], x["t"]) for x in wm["items"]):
                focal = dict(wall=wm["wall"]); break
        if focal is None and any(re.search(fo["types"], x["t"]) for cm in centre_motifs for x in cm["items"]):
            focal = dict(wall="centre")
    door_walls = [d[3] for d in doors]
    main = door_walls[0] if door_walls else None
    if focal and main and focal["wall"] != "centre":
        opp = {"NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW"}
        focal["rel"] = "door" if focal["wall"] == main else "opposite" if opp[main] == focal["wall"] else "beside"
    lights = sum(1 for o, p in pieces if p["cat"] == "light")
    # a carpet laid in floor tiles (Westwood's carpets are floor, not rug objects): the share of the floor it covers
    mats = [m.tiles[c]["material"] for c in cells if c in m.tiles]
    carpet = round(sum(1 for t in mats if re.search(r"Carpet|Rug", t or "")) / max(1, len(mats)), 3)
    # the raw plan: every piece in the room's frame (u - U0, v - V0), the wall it stands against, and the walls and doors
    # themselves, so the engine can measure Westwood's clusters and zones (kit/motifs.py clusters)
    raw = []
    for o, p in pieces:
        raw.append(dict(t=p["t"], cat=p["cat"], fam=p["fam"], u=round(p["u"] - U0, 3), v=round(p["v"] - V0, 3),
                        hu=round(p["hu"], 3), hv=round(p["hv"], 3), blocking=p["blocking"], hang=p["hang"],
                        wall=p.get("wname") if p["wall"] else None, gap=p.get("gap")))
    walls_raw = [dict(name=w["name"], line=w["line"], coord=round(w["coord"] - (U0 if w["line"] == "/" else V0), 3),
                      lo=round(w["lo"] - (V0 if w["line"] == "/" else U0), 3),
                      hi=round(w["hi"] - (V0 if w["line"] == "/" else U0), 3)) for w in named.values()]
    doors_raw = [dict(u=round(du - U0, 3), v=round(dv - V0, 3), wall=dn) for du, dv, _, dn in doors]
    room = dict(id=rid, map=entry["map"], type=entry["type"], culture=entry["culture"], tiles=entry["tiles"],
                U=[U0, U1], V=[V0, V1], doors=door_walls, focal=focal, lights=lights, carpet=carpet,
                pieces=raw, walls=walls_raw, door_at=doors_raw, floor=len(cells),
                middle_empty=not any(cm["wall_dist"] > 2.5 and any(x["blocking"] for x in cm["items"])
                                     for cm in centre_motifs))
    for lst in (wall_motifs, corner_motifs, centre_motifs):
        for x in lst: x.update(room=rid, type=entry["type"], culture=entry["culture"])
    return room, wall_motifs, corner_motifs, centre_motifs


def _mine_map(args):
    name, entries = args
    out = []
    for e, m, r in labref.rooms_of_map(name, entries):
        out.append(mine_room(e, m, r))
    return out


def lead(items):
    """A motif's leading category: its biggest blocking piece's (or its first piece's)."""
    bl = [x for x in items if x.get("blocking")] or items
    if not bl: return "bare"
    return max(bl, key=lambda x: x.get("ha", 0.5) * x.get("hp", 0.5) if "ha" in x else 1.0)["cat"]


def stats(rooms, walls, corners, centres):
    by = collections.defaultdict(lambda: dict(rooms=0, wall=collections.Counter(), corners=[], groups=[],
                                              middle_empty=0, focal=collections.Counter(),
                                              cooc=collections.Counter(), lights=[], carpet=[]))
    wall_of = collections.defaultdict(list)
    for w in walls: wall_of[w["room"]].append(w)
    corner_of = collections.Counter(c["room"] for c in corners)
    centre_of = collections.defaultdict(list)
    for c in centres: centre_of[c["room"]].append(c)
    for r in rooms:
        s = by[r["type"]]
        s["rooms"] += 1
        for w in wall_of[r["id"]]:
            cls = "back" if w["back"] else "front"
            s["wall"][f"{cls}:{'bare' if w['used'] < 0.05 else 'half' if w['used'] < 0.5 else 'full'}"] += 1
        s["corners"].append(corner_of[r["id"]])
        s["groups"].append(len(centre_of[r["id"]]))
        s["middle_empty"] += r["middle_empty"]
        s["lights"].append(r["lights"])
        s["carpet"].append(r["carpet"])
        if r["focal"]: s["focal"][f"{r['focal']['wall']}:{r['focal'].get('rel', '-')}"] += 1
        leads = sorted({lead(w["items"]) for w in wall_of[r["id"]] if w["items"]} |
                       {lead(c["items"]) for c in centre_of[r["id"]]})
        for i, a in enumerate(leads):
            for b in leads[i + 1:]: s["cooc"][f"{a}+{b}"] += 1
    out = {}
    for t, s in by.items():
        n = s["rooms"]
        wall = {}
        for cls in ("back", "front"):
            tot = sum(v for k, v in s["wall"].items() if k.startswith(cls)) or 1
            wall[cls] = {k.split(":")[1]: round(v / tot, 3) for k, v in s["wall"].items() if k.startswith(cls)}
        out[t] = dict(rooms=n, walls=wall, corners_per_room=round(sum(s["corners"]) / n, 2),
                      groups_per_room=round(sum(s["groups"]) / n, 2), middle_empty=round(s["middle_empty"] / n, 2),
                      lights_per_room=round(sum(s["lights"]) / n, 2),
                      carpeted=round(sum(1 for c in s["carpet"] if c >= 0.2) / n, 2),
                      focal=dict(s["focal"].most_common()),
                      cooccur=dict(s["cooc"].most_common(12)))
    return out


def main():
    by = collections.defaultdict(list)
    idx = labref.index()          # the curated index: kept and retyped rooms only, never the excluded ones
    for e in idx:
        if not re.match(r"^(Con|War|Wiz)", e["map"]): continue      # campaign maps only
        if e["type"] == "passage": continue
        by[e["map"]].append(e)
    with ProcessPoolExecutor(6) as pool:
        res = [x for xs in pool.map(_mine_map, sorted(by.items())) for x in xs]
    rooms, walls, corners, centres = [], [], [], []
    for room, w, c, g in res:
        rooms.append(room); walls += w; corners += c; centres += g
    rooms.sort(key=lambda r: (r["type"], r["id"]))
    for lst, tag in ((walls, "w"), (corners, "c"), (centres, "g")):
        lst.sort(key=lambda x: (x["type"], x["room"], x.get("wall", x.get("corner", "")), json.dumps(x.get("pos", 0))))
        for k, x in enumerate(lst): x["id"] = f"{tag}{k}"
    st = stats(rooms, walls, corners, centres)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(dict(source="rules/rooms/westwood.json index with rules/rooms/curated.json applied (campaign maps "
                              "Con/War/Wiz, kept and retyped rooms only)", made_by="rules/motifs.py",
                       rooms=rooms, wall=walls, corner=corners, centre=centres, stats=st), f, indent=0)
    print(f"{len(rooms)} rooms: {len(walls)} wall stretches ({sum(1 for w in walls if w['items'])} furnished), "
          f"{len(corners)} corner motifs, {len(centres)} centre groups -> {os.path.relpath(OUT, REPO)}")
    print(f"{'type':14} {'rooms':>5} {'walls':>6} {'used':>5} {'corner':>6} {'centre':>6}  back bare/half/full   front bare/half/full  middle empty")
    cnt = collections.defaultdict(collections.Counter)
    for w in walls:
        cnt[w["type"]]["walls"] += 1; cnt[w["type"]]["used"] += bool(w["items"])
    for c in corners: cnt[c["type"]]["corner"] += 1
    for g in centres: cnt[g["type"]]["centre"] += 1
    for t in sorted(st, key=lambda t: -st[t]["rooms"]):
        s, c = st[t], cnt[t]
        b, fr = s["walls"].get("back", {}), s["walls"].get("front", {})
        print(f"{t:14} {s['rooms']:5} {c['walls']:6} {c['used']:5} {c['corner']:6} {c['centre']:6}  "
              f"{b.get('bare', 0):.2f}/{b.get('half', 0):.2f}/{b.get('full', 0):.2f}       "
              f"{fr.get('bare', 0):.2f}/{fr.get('half', 0):.2f}/{fr.get('full', 0):.2f}       {s['middle_empty']:.2f}")


if __name__ == "__main__":
    main()
