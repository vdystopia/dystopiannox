"""Westwood's room shells: the shape, floor, walls and doors of every built room of the campaign maps (Con/War/Wiz), by
room type where rules/rooms/westwood.json types it. The numbers kit/building.py's shell pass (_shape_rooms, _floor_rooms)
and kit/furnish.py lay_carpet draw from.

Geometry. A room's floor is a set of lattice *units* (kit/building.py: unit (i, j) spans u in [2i, 2i + 2], v in
[2j, 2j + 2]); a unit's centre is the room cell with odd u = x + y. Walls stand on lattice points (even u). Measured per
room:
- shape: units, its box, fill (units / box), the outline's reflex corners, the largest rectangle inside it and what is
  left (each leftover piece a *bay* when it is small and shallow, a *wing* otherwise); a class: rect, L, bay (a rectangle
  with alcoves or bays), T/U/Z (two wings), irregular;
- inner walls: wall points with room units on all four sides, joined to the room's wall (a partial partition, a spur)
  or standing free (a pillar);
- floor: the materials of its units, one (main share 0.9 or more), mixed (a second material over 0.1, not rug),
  patterned (two materials alternating: half or more of the neighbouring pairs differ); carpets (Rug* tiles) as their
  pieces, each piece's size against the room and whether it reaches the room's edge (wall to wall);
- walls: the materials round it (one, or mixed);
- doors: how many, where along their wall (units from the nearer end; the share of the way along), and what lies
  through them (outside, a room, a passage: a corridor);
- building: the rooms joined to it by shared walls and doors, and its share of their floor.

Purposes (2026-10-06): for each second-floor piece and carpet, what stands on and beside it, its distance from the
doors, its share on the edge ring and in a wing (zone_measure), read as a purpose (zone_of: a plinth, the focal piece's
zone, under a group, an aisle, a wing, a border, by a door, or loose); the main floors' families by type; how often a
second floor lies at a tomb, a hearth, a throne, a bar (focal_rate) and in what (focal_pairs).

Only Westwood's curated rooms (rules/rooms/westwood.json's index, curated.json's verdicts applied; the void-bounded
throne halls included). The room-shape numbers kit/shells.py draws shapes and partitions from stay in
rules/rooms/shells_shape.json, as measured on 2026-10-05 (see its doc).

Writes rules/rooms/shells.json and prints the table. Run: py rules/rooms/shells.py
A room lab iteration's shells against Westwood's (and a shell AUC): py rules/rooms/shells.py --lab bedroom,crypt <iter>
"""
import collections, json, os, re, sys
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for p in ("validate", "review", "rules", "mapgen"):
    sys.path.insert(0, os.path.join(REPO, p))
import mapdata as md
import checks as C

NATURAL = re.compile(r"Cave|Rock|Dirt|Root|Tree|Decidious|Coni-|Aspen|Hedge|Shrub|Thorn|Volcano|IceWall|Shard|Invisible|Mine",
                     re.I)
RUG = re.compile(r"^Rug")
OUT = os.path.join(HERE, "shells.json")
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def uv(c): return c[0] + c[1], c[0] - c[1]
def xy(u, v): return (u + v) // 2, (u - v) // 2


def max_rect(units):
    """The largest rectangle (i0, i1, j0, j1), inclusive, inside a set of units."""
    if not units: return None
    i0 = min(i for i, _ in units); i1 = max(i for i, _ in units)
    j0 = min(j for _, j in units); j1 = max(j for _, j in units)
    best, bestA = None, 0
    h = [0] * (j1 - j0 + 1)
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            h[j - j0] = h[j - j0] + 1 if (i, j) in units else 0
        stack = []
        for k in range(len(h) + 1):
            cur = h[k] if k < len(h) else 0
            start = k
            while stack and stack[-1][1] >= cur:
                s, hh = stack.pop()
                a = hh * (k - s)
                if a > bestA: bestA, best = a, (i - hh + 1, i, j0 + s, j0 + k - 1)
                start = s
            stack.append((start, cur))
    return best


def pieces(units):
    out, seen = [], set()
    for s in units:
        if s in seen: continue
        comp, q = [], [s]; seen.add(s)
        while q:
            p = q.pop(); comp.append(p)
            for d in N4:
                n = (p[0] + d[0], p[1] + d[1])
                if n in units and n not in seen: seen.add(n); q.append(n)
        out.append(comp)
    return out


def reflex(units):
    """Reflex corners of the outline (a lattice vertex with three of its four units in the room; a vertex with two
    units diagonally across counts two)."""
    n = 0
    verts = {(i + a, j + b) for i, j in units for a in (0, 1) for b in (0, 1)}
    for (a, b) in verts:
        q = [(a - 1, b - 1) in units, (a, b - 1) in units, (a - 1, b) in units, (a, b) in units]
        k = sum(q)
        if k == 3: n += 1
        elif k == 2 and q[0] == q[3]: n += 2
    return n


def shape(units):
    r = max_rect(units)
    rect = {(i, j) for i in range(r[0], r[1] + 1) for j in range(r[2], r[3] + 1)}
    rest = pieces(set(units) - rect)
    n = len(units)
    parts = []
    for p in rest:
        # depth: how far it reaches out of the rectangle; width: along it
        di = max(i for i, _ in p) - min(i for i, _ in p) + 1
        dj = max(j for _, j in p) - min(j for _, j in p) + 1
        side_i = all(r[0] <= i <= r[1] for i, _ in p)         # it lies beside the rectangle across j
        depth, width = (dj, di) if side_i else (di, dj)
        parts.append(dict(units=len(p), share=round(len(p) / n, 3), depth=depth, width=width))
    bays = [p for p in parts if p["share"] <= 0.2 and p["depth"] <= 3]
    wings = [p for p in parts if p not in bays]
    rx = reflex(set(units))
    if not parts or sum(p["units"] for p in parts) <= max(1, 0.03 * n): cls = "rect"
    elif not wings: cls = "bay"
    elif len(wings) == 1 and rx <= 2: cls = "L" if rx == 1 else "T"
    elif len(wings) == 2 and rx <= 4: cls = "TUZ"
    else: cls = "irregular"
    box = (max(i for i, _ in units) - min(i for i, _ in units) + 1) * (max(j for _, j in units) - min(j for _, j in units) + 1)
    return dict(units=n, box=box, fill=round(n / box, 3), reflex=rx, core=round(len(rect) / n, 3), parts=parts, cls=cls,
                bays=len(bays), wings=len(wings), core_dims=sorted((r[1] - r[0] + 1, r[3] - r[2] + 1)))


def measure(m, r, comp_of, rooms_all):
    cells = set(r["cells"])
    U = {}
    for c in cells:
        u, v = uv(c)
        if u % 2: U[((u - 1) // 2, (v - 1) // 2)] = c
    if len(U) < 4: return None
    units = set(U)
    out = dict(shape=shape(units))
    # inner walls: wall points with room units on all four sides
    inner = set()
    for (i, j) in units:
        for a, b in ((0, 0), (1, 0), (0, 1), (1, 1)):
            p = xy(2 * (i + a), 2 * (j + b))
            if p in m.walls and all(q in units for q in ((i + a - 1, j + b - 1), (i + a, j + b - 1), (i + a - 1, j + b), (i + a, j + b))):
                inner.add(p)
    spurs, pillars = [], []
    for comp in pieces_xy(inner):
        attached = any((p[0] + a, p[1] + b) in m.walls and (p[0] + a, p[1] + b) not in inner
                       for p in comp for a in (-1, 1) for b in (-1, 1))
        (spurs if attached else pillars).append(len(comp))
    out["spurs"], out["pillars"] = spurs, pillars
    # floors
    mats = {}
    for k, c in U.items():
        t = (c[0], c[1] - 1) if (c[0], c[1] - 1) in m.tiles else m.tile_at_cell(c)
        if t: mats[k] = m.tiles[t]["material"]
    cnt = collections.Counter(mats.values())
    plain = collections.Counter({k: v for k, v in cnt.items() if not RUG.search(k)})
    tot = max(1, sum(plain.values()))
    main = plain.most_common(1)[0][0] if plain else None
    second = plain.most_common(2)[1] if len(plain) > 1 else (None, 0)
    pairs = diff = 0
    for (i, j), a in mats.items():
        for n in ((i + 1, j), (i, j + 1)):
            b = mats.get(n)
            if b is None or RUG.search(a) or RUG.search(b): continue
            pairs += 1; diff += a != b
    depth = depth_of(units)
    ring = {k for k, dd in depth.items() if dd == 1}
    sec_ring = sum(1 for k, mm in mats.items() if mm == second[0] and k in ring) / max(1, second[1])
    fl = dict(main=main, main_share=round(plain[main] / tot, 3) if main else 0, second=second[0],
              second_share=round(second[1] / tot, 3), materials=len(plain), alternate=round(diff / max(1, pairs), 3),
              second_on_ring=round(sec_ring, 3))
    sec = [p for p in pieces({k for k, mm in mats.items() if mm == second[0]})] if second[0] else []
    if not sec: fl["pattern"] = None
    elif sec_ring >= 0.8 and len(sec) <= 2: fl["pattern"] = "border"
    elif len(sec) >= 3 and second[1] / len(sec) <= 4.5:
        fl["pattern"] = "patches" if re.search(r"Dirt|Cave|Grass|Weeds|Mud", second[0]) else "panels"
    else: fl["pattern"] = "region"
    fl["kind"] = ("patterned" if fl["second_share"] >= 0.2 and fl["alternate"] >= 0.5 else
                  "mixed" if fl["second_share"] >= 0.1 else "one")
    rugs = {k for k, mm in mats.items() if RUG.search(mm)}
    fl["carpets"] = []
    for p in pieces(rugs):
        di = max(i for i, _ in p) - min(i for i, _ in p) + 1; dj = max(j for _, j in p) - min(j for _, j in p) + 1
        fl["carpets"].append(dict(units=len(p), share=round(len(p) / len(units), 3), dims=sorted((di, dj)),
                                  fill=round(len(p) / (di * dj), 2), edge=round(sum(1 for k in p if k in ring) / len(p), 2),
                                  margin=min(depth[k] for k in p) - 1,
                                  material=collections.Counter(mats[k] for k in p).most_common(1)[0][0]))
    out["floor"] = fl
    # what each second-floor piece and each carpet lies under or beside (the purpose measures, `zone_of`)
    objs = []
    for o in r.get("objects") or ():
        if m.is_door(o) or "MONSTER" in o["cls"] or "PLAYER" in o["cls"]: continue
        fam = obj_family(o["type"])
        if not fam: continue
        u, v = (o["x"] + o["y"]) / 23.0 - 1, (o["x"] - o["y"]) / 23.0
        objs.append((fam, o["type"], (int(u // 2), int(v // 2)), (u / 2, v / 2)))
    gaps = []
    for g in m.door_gaps:
        if any((g[0] + a, g[1] + b) in cells for a, b in N4):
            gu, gv = uv(g); gaps.append((gu / 2, gv / 2))
    core = max_rect(units)
    core = {(i, j) for i in range(core[0], core[1] + 1) for j in range(core[2], core[3] + 1)}
    fl["zones"] = []
    sec_units = {k for k, mm in mats.items() if second[0] and mm == second[0]}
    for what, us in (("second", sec_units), ("carpet", rugs)):
        for p in pieces(us):
            fl["zones"].append(dict(what=what, **zone_measure(set(p), units, ring, core, objs, gaps)))
    out["objects"] = [(f, t, list(k)) for f, t, k, _ in objs]
    # walls round it
    wm = collections.Counter()
    for c in cells:
        for a, b in N4:
            n = (c[0] + a, c[1] + b)
            if n in m.walls: wm[m.walls[n].material] += 1
    wt = max(1, sum(wm.values()))
    out["walls"] = dict(main=wm.most_common(1)[0][0] if wm else None, main_share=round(wm.most_common(1)[0][1] / wt, 3) if wm else 0,
                        materials=sum(1 for v in wm.values() if v / wt >= 0.1))
    # doors
    doors, done = [], set()
    for g, d in sorted(m.door_gaps.items()):
        if not any((g[0] + a, g[1] + b) in cells for a, b in N4): continue
        if any((g[0] + a, g[1] + b) in done for a in (-1, 1) for b in (-1, 1)): continue     # a double door's other half
        done.add(g)
        other = {comp_of.get((g[0] + a, g[1] + b)) for a, b in N4} - {None, id(r)}
        through = "outside"
        if other:
            o = rooms_all.get(next(iter(other)))
            through = "room" if o is not None else "outside"
        # where along its wall: walk the wall line both ways while the room lies beside it (segments of 2 uv)
        gu, gv = uv(g)
        best = None
        for st_ in ((0, 1), (1, 0)):
            ext = []
            for sgn in (1, -1):
                k = 0
                while k < 60:
                    mu, mv = gu + sgn * (2 * k + 1) * st_[0], gv + sgn * (2 * k + 1) * st_[1]
                    if not any(xy(mu + e * st_[1], mv + e * st_[0]) in cells for e in (1, -1)): break
                    k += 1
                    p = xy(gu + sgn * 2 * k * st_[0], gv + sgn * 2 * k * st_[1])
                    if not (p in m.walls or p in m.door_gaps): break
                ext.append(k)
            if best is None or sum(ext) > sum(best): best = ext
        a, b = best
        doors.append(dict(through=through, other=next(iter(other)) if other else None, end=min(a, b),
                          along=round(min(a, b) / max(1, a + b), 2), run=a + b, gap=list(g)))
    out["doors"] = doors
    return out


# object families for the purpose measures: what a second floor or a carpet lies under
FAMILIES = (("tomb", r"^Crypt\d|Coffin|Sarcophag|Tombstone|LOTDTomb"), ("throne", r"Throne"),
            ("altar", r"Altar|LichGodStatue"), ("bed", r"^Bed\d|^Cot\d|WoodBed|BedCot"), ("bar", r"^Bar(Piece|Corner|Hinged)"),
            ("seat", r"Chair|Bench|Stool|Pew"), ("table", r"Table|Desk"), ("hearth", r"Fireplace|FirePit|Stove|Cauldron"),
            ("statue", r"Statue|Obelisk|Column|Pillar|Crystal|Gargoyle"),
            ("light", r"Candle|Brazier|Torch|Lamp|Flame|Basin|Lantern"),
            ("storage", r"Chest|Barrel|Crate|Sack|Bookcase|Shelf|Rack|Cabinet|Wardrobe|Cupboard|Pot"))
FOCAL = ("tomb", "throne", "altar", "bed", "bar", "hearth")
_FAM_RE = [(f, re.compile(p, re.I)) for f, p in FAMILIES]


def obj_family(t):
    return next((f for f, rx in _FAM_RE if rx.search(t)), None)


def zone_measure(p, units, ring, core, objs, gaps):
    """Where a second-floor piece or a carpet lies: its size, its box fill and length against breadth, its share on the
    edge ring and outside the room's largest rectangle (a wing or an alcove), the object families standing on it and
    within a unit of it, and its distance in units from the nearest door."""
    di = max(i for i, _ in p) - min(i for i, _ in p) + 1; dj = max(j for _, j in p) - min(j for _, j in p) + 1
    on = collections.Counter(f for f, _, k, _ in objs if k in p)
    near = collections.Counter(f for f, _, k, _ in objs
                               if k not in p and any(abs(k[0] - a) <= 1 and abs(k[1] - b) <= 1 for a, b in p))
    door = min((max(abs(g[0] - (i + 0.5)), abs(g[1] - (j + 0.5))) for g in gaps for i, j in p), default=99)
    return dict(units=len(p), share=round(len(p) / len(units), 3), dims=sorted((di, dj)), fill=round(len(p) / (di * dj), 2),
                ring=round(sum(1 for k in p if k in ring) / len(p), 2),
                wing=round(sum(1 for k in p if k not in core) / len(p), 2), on=dict(on), near=dict(near),
                door=round(door, 1))


def zone_of(z):
    """A zone's purpose, as read from where it lies: `pad` (a plinth: a small pad with a showpiece on it, a tomb's, an
    obelisk's), `focal` (round the room's focal piece: a throne's dais, an altar's, a bed's end), `group` (under a group:
    seats, tables), `aisle` (a runner from a door: long and narrow), `wing` (filling a wing or an alcove), `border` (along
    the walls), `door` (worn by a door), else `loose` (no relation the measures see)."""
    on, near = z["on"], z["near"]
    nfur = sum(v for k, v in on.items() if k not in ("light",))
    if any(k in on or k in near for k in FOCAL) and z["units"] <= 40: kind = "focal"
    elif z["units"] <= 4 and nfur: kind = "pad"
    elif sum(on.get(k, 0) for k in ("seat", "table", "bed")) >= 2: kind = "group"
    elif z["dims"][1] >= 2.5 * z["dims"][0] and z["dims"][1] >= 4 and z["door"] <= 2.5: kind = "aisle"
    elif z["wing"] >= 0.6: kind = "wing"
    elif z["ring"] >= 0.8 and z["dims"][1] >= 4: kind = "border"
    elif z["door"] <= 2.5: kind = "door"
    elif nfur: kind = "pad" if z["units"] <= 6 else "group"
    else: kind = "loose"
    return kind


def depth_of(units):
    """Each unit's distance from the room's edge (1 for a unit with a neighbour, diagonals too, outside the room)."""
    depth, q = {}, collections.deque()
    for k in units:
        if any((k[0] + a, k[1] + b) not in units for a in (-1, 0, 1) for b in (-1, 0, 1)): depth[k] = 1; q.append(k)
    while q:
        k = q.popleft()
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                n = (k[0] + a, k[1] + b)
                if n in units and n not in depth: depth[n] = depth[k] + 1; q.append(n)
    return depth


def pieces_xy(points):
    """Components of wall points joined as walls join (diagonal neighbours in x, y)."""
    out, seen = [], set()
    for s in points:
        if s in seen: continue
        comp, q = [], [s]; seen.add(s)
        while q:
            p = q.pop(); comp.append(p)
            for a in (-1, 1):
                for b in (-1, 1):
                    n = (p[0] + a, p[1] + b)
                    if n in points and n not in seen: seen.add(n); q.append(n)
        out.append(comp)
    return out


def one(name):
    m = md.load(md.corpus_json(name))
    rooms = C.find_rooms(m, max_tiles=1500)
    built = {}
    for r in rooms:
        wall = [m.walls[(x + a, y + b)] for x, y in r["cells"] for a, b in N4 if (x + a, y + b) in m.walls]
        if r["tiles"] < 8 or not wall: continue
        if sum(1 for w in wall if not NATURAL.search(w.material)) < 0.6 * len(wall): continue
        built[id(r)] = r
    comp_of = {c: id(r) for r in rooms for c in r["cells"]}
    # buildings: built rooms joined by a shared wall cell or a door
    parent = {k: k for k in built}

    def find(k):
        while parent[k] != k: parent[k] = parent[parent[k]]; k = parent[k]
        return k
    for w in list(m.walls) + list(m.door_gaps):
        near = {comp_of.get((w[0] + a, w[1] + b)) for a, b in N4} & set(built)
        near = sorted(near)
        for k in near[1:]: parent[find(k)] = find(near[0])
    btiles = collections.Counter(); brooms = collections.Counter()
    for k, r in built.items(): btiles[find(k)] += r["tiles"]; brooms[find(k)] += 1
    # the index's rooms the walled flood misses (westwood.py HAND: a throne hall ending in the void), void-bounded
    def key(r):
        xs = [c[0] for c in r["cells"]]; ys = [c[1] for c in r["cells"]]
        return r["tiles"], (round(sum(xs) / len(xs)), round(sum(ys) / len(ys)))
    have = {key(r) for r in built.values()}
    want = {(e["tiles"], tuple(e["centre"])) for e in _index() if e["map"] == name} - have
    if want:
        for r in C.find_rooms(m, max_tiles=1500, void_bounds=True):
            if key(r) in want:
                built[id(r)] = r; parent[id(r)] = id(r); btiles[id(r)] += r["tiles"]; brooms[id(r)] += 1
                for c in r["cells"]: comp_of.setdefault(c, id(r))
    out = []
    for k, r in built.items():
        res = measure(m, r, comp_of, built)
        if res is None: continue
        xs = [c[0] for c in r["cells"]]; ys = [c[1] for c in r["cells"]]
        res.update(map=name, tiles=r["tiles"], centre=[round(sum(xs) / len(xs)), round(sum(ys) / len(ys))],
                   building_rooms=brooms[find(k)], building_share=round(r["tiles"] / btiles[find(k)], 3), key=k)
        out.append(res)
    # what a door leads to, by the other room's centre (typed afterwards)
    cen = {res["key"]: (res["tiles"], tuple(res["centre"])) for res in out}
    for res in out:
        for d in res["doors"]:
            d["other"] = list(cen[d["other"]][1]) + [cen[d["other"]][0]] if d["other"] in cen else None
        del res["key"]
    return out


_IDX = None


def _index():
    """Westwood's curated room index (rules/rooms/westwood.json, curated.json's verdicts applied)."""
    global _IDX
    if _IDX is None:
        sys.path.insert(0, HERE)
        import curated
        with open(os.path.join(HERE, "westwood.json"), encoding="utf-8") as f:
            _IDX = curated.apply(json.load(f)["index"])
    return _IDX


def pct(vals, ps=(10, 25, 50, 75, 90)):
    s = sorted(vals)
    if not s: return None
    return {f"p{p}": round(s[min(len(s) - 1, int(p / 100 * len(s)))], 3) for p in ps}


def share(rs, f):
    return round(sum(1 for r in rs if f(r)) / max(1, len(rs)), 3)


def floor_family(mat):
    """wood (planks), stone (brick, cobble, tile, flagstones), marble, earth (dirt, cave), rug, or other."""
    if not mat: return None
    if RUG.search(mat): return "rug"
    if re.search(r"Marble", mat): return "marble"
    if re.search(r"Wood|Oak|Redwood|Slat|Plank", mat): return "wood"
    if re.search(r"Dirt|Cave|Mud|Grass|Weeds|Sand|Swamp", mat): return "earth"
    if re.search(r"Brick|Cobble|Tile|Stone|Rough|LOTD|DunMir|Galava|Pitted|Mine", mat): return "stone"
    return "other"


def purposes(rs):
    """What a group of rooms' second floors and carpets are for (zone_of, weighted by their floor), their main floors
    by material and family, and how far a carpet lies from the room's middle."""
    out = {}
    for what in ("second", "carpet"):
        zs = [(z, r) for r in rs for z in r["floor"].get("zones", ()) if z["what"] == what
              and (what == "carpet" and z["units"] >= 2 or what == "second" and r["floor"]["second_share"] >= 0.03)]
        cnt = collections.Counter()
        for z, r in zs: cnt[zone_of(z)] += z["units"]
        tot = max(1, sum(cnt.values()))
        out[what + "_purpose"] = {k: round(v / tot, 3) for k, v in cnt.most_common()}
        out[what + "_pieces"] = pct([sum(1 for z in r["floor"].get("zones", ()) if z["what"] == what and z["units"] >= 1)
                                     for r in rs if any(z["what"] == what for z in r["floor"].get("zones", ()))])
        out[what + "_on"] = dict(collections.Counter(f for z, r in zs for f in z["on"]).most_common(8))
    out["main_floor"] = dict(collections.Counter(r["floor"]["main"] for r in rs if r["floor"]["main"]).most_common(8))
    out["main_family"] = {k: round(v / len(rs), 3) for k, v in
                          collections.Counter(floor_family(r["floor"]["main"]) for r in rs).most_common()}
    return out


def summarise(rs):
    carp = [c for r in rs for c in r["floor"]["carpets"] if c["units"] >= 2]
    doors = [d for r in rs for d in r["doors"]]
    cls = collections.Counter(r["shape"]["cls"] for r in rs)
    return dict(
        n=len(rs),
        shape={k: round(v / len(rs), 3) for k, v in cls.most_common()},
        fill=pct([r["shape"]["fill"] for r in rs]),
        reflex=pct([r["shape"]["reflex"] for r in rs]),
        with_bay=share(rs, lambda r: r["shape"]["bays"] > 0),
        bay_units=pct([p["units"] for r in rs for p in r["shape"]["parts"] if p["share"] <= 0.2 and p["depth"] <= 3]),
        wing_share=pct([p["share"] for r in rs for p in r["shape"]["parts"] if not (p["share"] <= 0.2 and p["depth"] <= 3)]),
        with_spur=share(rs, lambda r: bool(r["spurs"])),
        spur_points=pct([s for r in rs for s in r["spurs"]]),
        with_pillar=share(rs, lambda r: bool(r["pillars"])),
        pillars=pct([len(r["pillars"]) for r in rs if r["pillars"]]),
        pillar_points=pct([s for r in rs for s in r["pillars"]]),
        floor={k: share(rs, lambda r, k=k: r["floor"]["kind"] == k) for k in ("one", "mixed", "patterned")},
        second_on_ring=pct([r["floor"]["second_on_ring"] for r in rs if r["floor"]["kind"] != "one"]),
        with_carpet=share(rs, lambda r: any(c["units"] >= 2 for c in r["floor"]["carpets"])),
        carpets_per_room=pct([sum(1 for c in r["floor"]["carpets"] if c["units"] >= 2) for r in rs
                              if any(c["units"] >= 2 for c in r["floor"]["carpets"])]),
        carpet_share=pct([c["share"] for c in carp]), carpet_units=pct([c["units"] for c in carp]),
        carpet_short=pct([c["dims"][0] for c in carp]), carpet_long=pct([c["dims"][1] for c in carp]),
        carpet_fill=pct([c["fill"] for c in carp]), carpet_edge=pct([c["edge"] for c in carp]),
        carpet_margin=pct([c["margin"] for c in carp]),
        carpet_wall_to_wall=round(sum(1 for c in carp if c["edge"] >= 0.5) / max(1, len(carp)), 3),
        carpet_materials=dict(collections.Counter(c["material"] for c in carp).most_common(8)),
        floor_touched=share(rs, lambda r: r["floor"]["second_share"] >= 0.03),
        touched_share=pct([r["floor"]["second_share"] for r in rs if r["floor"]["second_share"] >= 0.03]),
        touched_pattern=dict(collections.Counter(r["floor"]["pattern"] for r in rs if r["floor"]["second_share"] >= 0.03).most_common()),
        floor_pattern=dict(collections.Counter(r["floor"]["pattern"] for r in rs if r["floor"]["kind"] != "one").most_common()),
        walls_mixed=share(rs, lambda r: r["walls"]["materials"] > 1),
        doors=dict(collections.Counter(min(len(r["doors"]), 4) for r in rs).most_common()),
        door_end=pct([d["end"] for d in doors]), door_along=pct([d["along"] for d in doors]),
        door_at_end=round(sum(1 for d in doors if d["end"] <= 1) / max(1, len(doors)), 3),
        door_middle=round(sum(1 for d in doors if d["along"] >= 0.4) / max(1, len(doors)), 3),
        door_outside=round(sum(1 for d in doors if d["through"] == "outside") / max(1, len(doors)), 3),
        off_passage=share(rs, lambda r: any(d.get("to_type") == "passage" for d in r["doors"])),
        building_share=pct([r["building_share"] for r in rs if "building_share" in r]),
        building_rooms=pct([r["building_rooms"] for r in rs if "building_rooms" in r]),
    )


def main():
    import common
    maps = sorted(common.campaign_maps())
    with ProcessPoolExecutor(6) as pool:
        found = [r for rs in pool.map(one, maps) for r in rs]
    seen, rooms = set(), []
    for r in found:                                   # each layout's room once
        key = (r["tiles"], tuple(r["centre"]))
        if key in seen: continue
        seen.add(key); rooms.append(r)
    typed = {(e["tiles"], tuple(e["centre"])): e for e in _index()}
    for r in rooms:
        e = typed.get((r["tiles"], tuple(r["centre"])))
        r["type"] = e["type"] if e else None
        r["culture"] = e["culture"] if e else None
    # Westwood's curated rooms only (rules/rooms/curated.json): the rooms its index keeps, typed
    found_n = len(rooms)
    rooms = [r for r in rooms if r["type"]]
    print(f"{found_n} built rooms found, {len(rooms)} of them curated")
    by_key = {(r["tiles"], tuple(r["centre"])): r for r in rooms}
    for r in rooms:
        for d in r["doors"]:
            o = by_key.get((d["other"][2], tuple(d["other"][:2]))) if d["other"] else None
            d["to_type"] = (o or {}).get("type")
    groups = {"all built rooms": rooms, "typed": [r for r in rooms if r["type"]]}
    for t in sorted({r["type"] for r in rooms if r["type"]}):
        groups[t] = [r for r in rooms if r["type"] == t]
    for c in ("town", "dunmir", "lotd", "ogre"):
        groups["culture:" + c] = [r for r in rooms if r["culture"] == c]
    for lo, hi in ((0, 30), (30, 80), (80, 200), (200, 5000)):
        groups[f"tiles:{lo}-{hi}"] = [r for r in rooms if lo <= r["tiles"] < hi]
    summ = {k: summarise(v) for k, v in groups.items() if v}
    for k, v in groups.items():
        if v: summ[k].update(purposes(v))
    pairs = collections.defaultdict(collections.Counter)
    for r in rooms:
        if r["floor"]["kind"] != "one" and r["floor"]["second"]: pairs[r["floor"]["main"]][r["floor"]["second"]] += 1
    summ["floor_pairs"] = {k: dict(v) for k, v in pairs.items()}
    # under the room's focal pieces (kit/shells.py lay_zones): how often a second floor (a throne's: or a carpet) lies at
    # them, and which on which main floor
    rate, fpairs = {}, collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for fam in ("tomb", "hearth", "throne", "bar"):
        rs = [r for r in rooms if any(o[0] == fam and not o[1].startswith("Cauldron") for o in r["objects"])]
        at = lambda r, w: [z for z in r["floor"]["zones"] if z["what"] in w and (fam in z["on"] or fam in z["near"])]
        hit = [r for r in rs if at(r, ("second", "carpet") if fam == "throne" else ("second",))]
        rate[fam] = round(len(hit) / max(1, len(rs)), 3)
        for r in rs:
            if at(r, ("second",)): fpairs[fam][r["floor"]["main"]][r["floor"]["second"]] += 1
    summ["focal_rate"] = rate
    summ["focal_pairs"] = {f: {m: dict(c) for m, c in d.items()} for f, d in fpairs.items()}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(dict(maps="campaign (Con/War/Wiz), each room once", summary=summ,
                       rooms=[dict(r, doors=[{k: v for k, v in d.items() if k != "other"} for d in r["doors"]]) for r in rooms]),
                  f, indent=None, separators=(",", ":"))
    print(f"{len(rooms)} built rooms, {sum(1 for r in rooms if r['type'])} typed")
    print(f"{'group':18} {'n':>4}  rect   L    bay  TUZ  irr  | spur pill | one  mix  pat | carp  c.share c.edge w2w | "
          f"doors 1/2/3+  end1  mid  out  offpass | bshare")
    for k, s in summ.items():
        if k in ("floor_pairs", "focal_rate", "focal_pairs"): continue
        sh = s["shape"]; fl = s["floor"]; dd = s["doors"]; nd = max(1, sum(dd.values()))
        print(f"{k:18} {s['n']:4}  {sh.get('rect', 0):.2f} {sh.get('L', 0) + sh.get('T', 0):.2f} {sh.get('bay', 0):.2f} "
              f"{sh.get('TUZ', 0):.2f} {sh.get('irregular', 0):.2f} | {s['with_spur']:.2f} {s['with_pillar']:.2f} | "
              f"{fl['one']:.2f} {fl['mixed']:.2f} {fl['patterned']:.2f} | {s['with_carpet']:.2f} "
              f"{(s['carpet_share'] or {}).get('p50', 0):.2f}   {(s['carpet_edge'] or {}).get('p50', 0):.2f}  "
              f"{s['carpet_wall_to_wall']:.2f} | {dd.get(1, 0) / nd:.2f}/{dd.get(2, 0) / nd:.2f}/"
              f"{(dd.get(3, 0) + dd.get(4, 0)) / nd:.2f}  {s['door_at_end']:.2f} {s['door_middle']:.2f} "
              f"{s['door_outside']:.2f} {s['off_passage']:.2f} | {(s['building_share'] or {}).get('p50', 0):.2f}")


SHELL_FEATURES = ("fill", "reflex", "core", "bays", "wings", "spurs", "second_share", "alternate", "carpet_share",
                  "carpet_edge", "carpet_margin", "doors", "door_along", "second_loose", "focal_zone", "main_wood")


def shell_features(r):
    sh, fl = r["shape"], r["floor"]
    carp = [c for c in fl["carpets"] if c["units"] >= 2]
    return dict(fill=sh["fill"], reflex=min(sh["reflex"], 6), core=sh["core"], bays=min(sh["bays"], 3),
                wings=min(sh["wings"], 3), spurs=min(len(r["spurs"]), 3), second_share=fl["second_share"],
                alternate=fl["alternate"], carpet_share=sum(c["share"] for c in carp),
                carpet_edge=max((c["edge"] for c in carp), default=0.0),
                carpet_margin=min((c["margin"] for c in carp), default=0),
                doors=min(len(r["doors"]), 4), door_along=min((d["along"] for d in r["doors"]), default=0.5),
                # what the second floors and carpets are for: the share of the floor in zones with no purpose the
                # measures see (zone_of `loose`), a zone at a focal piece (a tomb, a hearth, a throne, a bar, a bed),
                # a plank main floor
                second_loose=sum(z["share"] for z in fl.get("zones", ()) if z["what"] == "second" and zone_of(z) == "loose"),
                focal_zone=float(any(k in z["on"] or k in z["near"] for z in fl.get("zones", ()) for k in FOCAL)),
                main_wood=float(floor_family(fl["main"]) == "wood"))


def lab(typ, it):
    """The shells of a room lab iteration's variants (review/out/roomlab/<type>/<iter>/) against Westwood's rooms of
    the type: the summary side by side and a shell AUC (cross-validated logistic regression on SHELL_FEATURES)."""
    d = os.path.join(REPO, "review", "out", "roomlab", typ, it)
    with open(os.path.join(d, "variants.json"), encoding="utf-8") as f:
        vs = json.load(f)["variants"]
    ours = []
    for mname in sorted({v["map"] for v in vs}):
        m = md.load(os.path.join(d, "map", mname + ".map"))
        rooms = C.find_rooms(m, max_tiles=1500)
        comp_of = {c: id(r) for r in rooms for c in r["cells"]}
        by_num = {r["declared"]["number"]: r for r in rooms if r.get("declared")}
        for v in vs:
            if v["map"] != mname or v["number"] not in by_num: continue
            res = measure(m, by_num[v["number"]], comp_of, {id(r): r for r in rooms})
            if res: res.update(index=v["index"], tiles=by_num[v["number"]]["tiles"]); ours.append(res)
    with open(OUT, encoding="utf-8") as f:
        ww = [r for r in json.load(f)["rooms"] if r["type"] == typ]
    a, b = summarise(ww), summarise(ours)
    rows = [("rect / L+T / bay / TUZ / irregular", lambda s: " / ".join(f"{sum(s['shape'].get(x, 0) for x in k.split('+')):.2f}" for k in ("rect", "L+T", "bay", "TUZ", "irregular"))),
            ("with a spur (partition)", lambda s: f"{s['with_spur']:.2f}"),
            ("floor one / mixed / patterned", lambda s: " / ".join(f"{s['floor'][k]:.2f}" for k in ("one", "mixed", "patterned"))),
            ("with a carpet", lambda s: f"{s['with_carpet']:.2f}"),
            ("carpet share p25-p50-p75", lambda s: "-".join(f"{(s['carpet_share'] or {}).get(q, 0):.2f}" for q in ("p25", "p50", "p75"))),
            ("carpet on the edge ring p50", lambda s: f"{(s['carpet_edge'] or {}).get('p50', 0):.2f}"),
            ("doors 1 / 2 / 3+", lambda s: " / ".join(f"{v:.2f}" for v in _doorshare(s))),
            ("door along p25-p50", lambda s: f"{s['door_along']['p25'] if s['door_along'] else 0}-{s['door_along']['p50'] if s['door_along'] else 0}")]
    print(f"{typ} [{it}]: Westwood {a['n']} rooms, ours {b['n']}")
    for name, f in rows: print(f"  {name:36} Westwood {f(a):34} ours {f(b)}")
    auc = shell_auc(ww, ours)
    print(f"  shell AUC {auc['auc']:.2f}; most telling: " + ", ".join(f"{k} {v:.2f}" for k, v in auc["top"][:5]))
    for r in sorted(ours, key=lambda r: r["index"]):
        print(f"   {r['index']:2d}: {r['tiles']:3d} tiles {r['shape']['cls']:9} reflex {r['shape']['reflex']} "
              f"floor {r['floor']['kind']:6} carpets {[c['units'] for c in r['floor']['carpets']]} spurs {r['spurs']} doors {len(r['doors'])}")
    return auc


def _doorshare(s):
    dd = s["doors"]; n = max(1, sum(dd.values()))
    return dd.get(1, 0) / n, dd.get(2, 0) / n, sum(v for k, v in dd.items() if int(k) >= 3) / n


def shell_auc(ww, ours):
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    X = np.array([[shell_features(r)[k] for k in SHELL_FEATURES] for r in ww + ours], dtype=float)
    y = np.array([0] * len(ww) + [1] * len(ours))
    top = []
    for i, k in enumerate(SHELL_FEATURES):
        try: a = roc_auc_score(y, X[:, i])
        except ValueError: a = 0.5
        top.append((k, max(a, 1 - a)))
    top.sort(key=lambda t: -t[1])
    k = min(5, int(min(len(ww), len(ours))))
    if k < 2: return dict(auc=float("nan"), top=top)
    aucs = []
    for seed in range(5):
        cv = StratifiedKFold(k, shuffle=True, random_state=seed)
        p = cross_val_predict(make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000)), X, y, cv=cv,
                              method="predict_proba")[:, 1]
        aucs.append(roc_auc_score(y, p))
    return dict(auc=float(np.mean(aucs)), top=top)


def maps(paths):
    """The shells of the rooms of built maps (each map's declared rooms; a design's <map>.rooms.json), summarised as
    Westwood's are: py rules/rooms/shells.py --maps mapgen/out/Thornwick.map ..."""
    for path in paths:
        m = md.load(path)
        rooms = C.find_rooms(m, max_tiles=1500)
        comp_of = {c: id(r) for r in rooms for c in r["cells"]}
        mine = [r for r in rooms if r.get("declared") and not r.get("yard")]
        res = [x for x in (measure(m, r, comp_of, {id(q): q for q in rooms}) for r in mine) if x]
        if not res: print(f"{os.path.basename(path)}: no declared rooms"); continue
        s = summarise(res)
        sh = s["shape"]
        print(f"{os.path.basename(path):16} {len(res):3} rooms: rect {sh.get('rect', 0):.2f} L/T {sh.get('L', 0) + sh.get('T', 0):.2f} "
              f"bay {sh.get('bay', 0):.2f} more {sh.get('TUZ', 0) + sh.get('irregular', 0):.2f} | spur {s['with_spur']:.2f} | "
              f"second floor {s['floor_touched']:.2f} | carpet {s['with_carpet']:.2f} share p50 "
              f"{(s['carpet_share'] or {}).get('p50', 0):.2f} | walls {len(m.walls)} tiles {len(m.tiles)}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--maps":
        maps(sys.argv[2:])
    elif len(sys.argv) >= 4 and sys.argv[1] == "--lab":
        for t in sys.argv[2].split(","): lab(t, sys.argv[3])
    else:
        main()
