"""The room lab's generator: N variants of one room type, each the main room of its own building shell, built and
furnished by the kit's real path (kit/building.py _build for walls, floors and doors in the host role's building style;
kit/originality.furnish_original, the furnisher every map uses, for furniture and lights).

Each variant varies, on a fixed schedule so a batch always covers the range:
- size: small, typical or large: Westwood's campaign p25, p50 or p90 floor tiles for the type
  (rules/rooms/westwood.json), at the kit's scale (kit/identity.BUILDING_SCALE on the area), held to the type's
  profile range (kit/roomtypes.py tiles);
- shape: square (1.0-1.25 long side over short) or long (1.6-2.2), either way round (a throne room always runs from its
  door to its throne);
- doors: drawn from Westwood's own door counts for the type (door_plan: its campaign rooms as the metric judge counts
  their doors, its pool's when it is thin; half of all Westwood's rooms have one door): the entrance, plus a
  neighbouring room (the host role's other rooms, furnished too) for each further door, each reached through its own
  door in the main room's wall; the kit places every door (_door_point) and sometimes adds a second entrance, as in a
  map. (Until 2026-10-06 a fixed 1, 2 or 3 doors, a third each: an independent judge's tell, FAIRNESS.md);
- culture and style: the type's kit kinds (a chapel or the Land of the Dead's dark chapel) in proportion to Westwood's
  campaign rooms of the type by culture, and the building roles that host the kind (kit/identity.py BUILDINGS: a
  bedroom in an inn, a home, a manor, a keep...), round-robin;
- seed: every variant its own, from (type, seed, variant) by crc32.

    from labgen import generate
    batch = generate("bedroom", n=10, seed=1, out_dir=..., name="R1a2b3c4")   # -> dict with the map path and variants

Builds are reproducible: the same type, n and seed give the same map.
"""
import json, math, os, random, sys
import labenv as E
from nox import Spec, SOLO, rect_tiles, rect_wall_cells
from kit import building as KB
from kit.identity import BUILDINGS, BUILDING_SCALE
from kit.roomtypes import TYPES, profile
from kit.originality import furnish_original

FIELD = (120, 390, -116, 116)         # u0, u1, v0, v1 of the open ground (x and y stay within the 256 x 256 grid)
GAP = 8                                # uv units between buildings
STYLE_FURNISH = {"lotd_ornate": "lotd", "lotd_crypt": "lotd", "dunmir_hall": "dunmir", "dungeon_block": "ogre",
                 "ogre_hut": "ogre"}
FURNISH_CULTURE = {"lotd": "lotd", "ogre": "ogre", "dunmir": "dunmir"}       # westwood.json's culture of a furnishing
# (size class, shape): the schedule every batch walks, so ten variants cover the range
SCHEDULE = [("typical", "square"), ("small", "long"), ("large", "square"), ("typical", "long"), ("small", "square"),
            ("large", "long"), ("typical", "square"), ("large", "square"), ("small", "square"), ("typical", "long")]
MAX_DOORS = 4                          # the entrance and a neighbour on each of the other three sides
SIZE_Q = {"small": "p25", "typical": "p50", "large": "p90"}


def _ww_types():
    with open(E.WW_INDEX, encoding="utf-8") as f:
        return json.load(f)["types"]


def hosts(kind):
    """[(role, building style, furnishing style)] of every building role whose program holds the kind."""
    out = []
    for role, r in BUILDINGS.items():
        if any(k == kind for k, _ in r["rooms"]):
            st = r["style"]
            out.append((role, st, r.get("furnish") or STYLE_FURNISH.get(st, "town")))
    return out or [("lab", "stone_house", "town")]


def culture_of(furnish):
    return FURNISH_CULTURE.get(furnish, "town")


def kind_plan(typ, n, ww):
    """The kit kind of each variant: the type's kinds in proportion to Westwood's rooms of the type by culture (each
    kind with a host at least once when n >= 2 * kinds), the main kind first."""
    kinds = list(TYPES[typ]["kinds"])
    cult = (ww.get(typ) or {}).get("cultures", {})
    w = []
    for k in kinds:
        c = culture_of(hosts(k)[0][2])
        w.append(cult.get(c, 0) + (1.0 if k == kinds[0] else 0.25))
    tot = sum(w)
    alloc = [max(1 if n >= 2 * len(kinds) else 0, int(n * x / tot)) for x in w]
    while sum(alloc) > n: alloc[alloc.index(max(alloc))] -= 1
    k = 0
    while sum(alloc) < n:
        i = max(range(len(kinds)), key=lambda i: n * w[i] / tot - alloc[i]) if k < len(kinds) else 0
        alloc[i] += 1; k += 1
    plan = []
    for kind, a in zip(kinds, alloc): plan += [kind] * a
    # interleave so a short batch (--n 3) still mixes cultures
    order = sorted(range(len(plan)), key=lambda i: (plan[:i + 1].count(plan[i]) / max(1, plan.count(plan[i])), i))
    return [plan[i] for i in order]


def door_plan(typ, n, seed):
    """The door count of each variant: Westwood's campaign rooms of the type (metrics.pool: its own, or its pool's when
    it has under metrics.MIN_WW), their doors as the metric judge counts them (westwood_features.json), drawn by
    quantile so a batch follows the distribution (bedroom: 19 of 28 with one door), then put in a seeded order. A room
    Westwood enters through an open arch (0 doors) counts as one door; over MAX_DOORS as MAX_DOORS."""
    import metrics
    rooms, _ = metrics.pool(typ)
    counts = sorted(min(MAX_DOORS, max(1, int(r["features"].get("doors") or 0))) for r in rooms) or [1]
    picks = [counts[min(len(counts) - 1, int((k + 0.5) * len(counts) / n))] for k in range(n)]
    random.Random(E.seed_of("doors", typ, seed)).shuffle(picks)
    return picks


def target_tiles(typ, size, ww, rng):
    """Floor tiles for a variant of size class `size` (small, typical, large)."""
    p = TYPES[typ]
    lo, hi = p["tiles"]
    src = (ww.get(typ) or {}).get("tiles")
    n = (ww.get(typ) or {}).get("n", 0)
    pos = {"small": 0.15, "typical": 0.45, "large": 0.85}
    sizes = None
    if src and n >= 4:
        sizes = {k: max(lo, min(hi, src[q] * BUILDING_SCALE)) for k, q in SIZE_Q.items()}
        if sizes["large"] < 1.5 * sizes["small"]:
            # Westwood's sizes run past the profile's range (its throne rooms are 84-492 tiles, the profile 60-260):
            # spread the classes over the part of the range they share
            a = max(lo, src["p10"] * BUILDING_SCALE); b = min(hi, src["p90"] * BUILDING_SCALE)
            if b < 1.5 * a: a, b = lo, hi
            sizes = {k: a + f * (b - a) for k, f in pos.items()}
    if sizes is None:          # too few Westwood rooms to say (a chapel, a tavern): the profile's range
        sizes = {k: lo + f * (hi - lo) for k, f in pos.items()}
    t = sizes[size] * rng.uniform(0.92, 1.08)
    return int(max(lo, min(hi, t)))


def spans(tiles, shape, rng, long_u=None):
    """(W, H) in footprint units for a room of about `tiles` floor tiles."""
    units = KB._units_for(tiles)
    a = rng.uniform(1.0, 1.25) if shape == "square" else rng.uniform(1.6, 2.2)
    short = max(4, round(math.sqrt(units / a)))
    long_ = max(4, round(units / short))
    if long_u is None: long_u = rng.random() < 0.5
    return (long_, short) if long_u else (short, long_)


OPP = {"u_min": "u_max", "u_max": "u_min", "v_min": "v_max", "v_max": "v_min"}


def layout(W, H, neighbours, sides, depth):
    """Footprint labels: the main room (label 0) W x H units, a neighbouring room (labels 1, 2) `depth` units deep along
    each of `sides`. Returns (labels, total W, total H)."""
    oi = depth if "u_min" in sides else 0
    oj = depth if "v_min" in sides else 0
    labels = {(oi + i, oj + j): 0 for i in range(W) for j in range(H)}
    for k, s in enumerate(sides[:neighbours]):
        lab = k + 1
        if s == "u_min": cells = [(i, oj + j) for i in range(depth) for j in range(H)]
        elif s == "u_max": cells = [(oi + W + i, oj + j) for i in range(depth) for j in range(H)]
        elif s == "v_min": cells = [(oi + i, j) for i in range(W) for j in range(depth)]
        else: cells = [(oi + i, oj + H + j) for i in range(W) for j in range(depth)]
        for c in cells: labels[c] = lab
    TW = max(i for i, _ in labels) + 1
    TH = max(j for _, j in labels) + 1
    return labels, TW, TH


def plan(typ, n=10, seed=1):
    """The variants' plans (no map yet): [dict(index, kind, role, style, furnish, culture, size, shape, tiles, W, H,
    neighbours, sides, entrance, seed)]."""
    ww = _ww_types()
    kinds = kind_plan(typ, n, ww)
    doors = door_plan(typ, n, seed)
    host_turn = {}
    out = []
    for i in range(n):
        size, shape = SCHEDULE[i % len(SCHEDULE)]
        vseed = E.seed_of("roomlab", typ, seed, i)
        rng = random.Random(vseed)
        kind = kinds[i]
        hs = hosts(kind)
        t = host_turn.get(kind, E.seed_of(typ, seed, kind) % len(hs))
        host_turn[kind] = t + 1
        role, style, furnish = hs[t % len(hs)]
        tiles = target_tiles(typ, size, ww, rng)
        throne = profile(kind)["type"] == "throne_room"
        W, H = spans(tiles, shape, rng, long_u=True if throne else None)
        st = KB.styles()[style]
        if throne:
            entrance = "u_max"
            free = ["v_min", "v_max"]
        else:
            ent = {k: v for k, v in (st.get("entrance_sides") or {"v_min": 1}).items() if v > 0} or {"v_min": 1}
            keys = sorted(ent)
            entrance = rng.choices(keys, [ent[k] for k in keys])[0]
            free = [s for s in ("u_min", "u_max", "v_min", "v_max") if s != entrance]
        rng.shuffle(free)
        nb = min(len(free), doors[i] - 1)
        others = [k for k, _ in BUILDINGS.get(role, {}).get("rooms", []) if k != kind] or ["storeroom"]
        nkinds = [others[k % len(others)] for k in range(nb)]
        out.append(dict(index=i + 1, kind=kind, type=typ, role=role, style=style, furnish=furnish,
                        culture=culture_of(furnish), size=size, shape=shape, tiles_target=tiles, W=W, H=H,
                        doors_planned=nb + 1, neighbours=nb, sides=free[:nb], neighbour_kinds=nkinds, entrance=entrance, seed=vseed))
    return out


def _try_build(m, p, U0, V0, occupied):
    """Builds one variant's shell at (U0, V0); returns the kit Building or None. Tries the planned neighbours, then
    fewer, with fresh draws for the doors."""
    st = KB.styles()[p["style"]]
    for attempt in range(12):
        nb = max(0, p["neighbours"] - attempt // 4)
        depth = max(3, min(5, min(p["W"], p["H"]) // 2))
        labels, TW, TH = layout(p["W"], p["H"], nb, p["sides"], depth)
        program = [p["kind"]] + p["neighbour_kinds"][:nb]
        cells = KB._cells_of(U0, V0, labels)
        if cells & occupied: return None
        rng = random.Random(E.seed_of("shell", p["seed"], attempt))
        b = KB._build(m, rng, st, p["style"], U0, V0, TW, TH, labels, program, p["entrance"],
                      f"lab{p['index']:02d}", cells, "rect", strict=attempt < 8)
        if b is not None:
            b.lab_neighbours = nb
            return b
    return None


def size_uv(p):
    depth = max(3, min(5, min(p["W"], p["H"]) // 2))
    _, TW, TH = layout(p["W"], p["H"], p["neighbours"], p["sides"], depth)
    return 2 * TW, 2 * TH


def new_spec(name, typ):
    m = Spec(name, summary=f"Room lab: {typ}", description=f"Room lab variants of the {typ} type. Generated by Claude.",
             author="vdystopia (generated by Claude)", version="1", date="2026", type=SOLO, minPlayers=1, maxPlayers=1)
    m.d["nxz"] = False
    m.d["ambient"] = [165, 160, 155]
    m.loot = False
    u0, u1, v0, v1 = FIELD
    for mat, prio in (("GrassNorm", 0), ("GrassSparse2", 1), ("GrassDense", 2), ("DirtDark2", 3), ("DirtHard", 4)):
        m.blending(mat, prio)
    for x, y in rect_tiles(u0, u1, v0, v1): m.tile(x, y, "GrassNorm")
    for x, y in rect_wall_cells(u0, u1, v0, v1): m.wall(x, y, "BrickPlain")
    return m


def generate(typ, n=10, seed=1, out_dir=None, name="RoomLab", log=print, engine=None):
    """Builds the batch: one or more maps (`name`, then name + page) of the variants. Returns dict(maps=[paths],
    variants=[plan + map, building, room id, floor tiles, doors]). engine: the furnisher of each variant's main room
    ("recipe" or "motifs", kit/originality.furnish_original); None: the type's own (the recipe engine by default).
    The neighbouring rooms keep their type's own engine."""
    plans = plan(typ, n, seed)
    os.makedirs(out_dir, exist_ok=True)
    pending = sorted(plans, key=lambda p: -size_uv(p)[0] * size_uv(p)[1])
    maps, done = [], []
    page = 0
    while pending:
        page += 1
        mname = name if page == 1 else f"{name[:7]}{page}"
        m = new_spec(mname, typ)
        u0, u1, v0, v1 = FIELD
        u, v, row = u0 + 6, v0 + 6, 0
        occupied, left, built = set(), [], []
        for p in pending:
            us, vs = size_uv(p)
            if v + vs > v1 - 6: u, v, row = u + row + GAP, v0 + 6, 0
            if u + us > u1 - 6: left.append(p); continue
            b = _try_build(m, p, u, v, occupied)
            if b is None:
                log(f"  variant {p['index']} ({p['kind']} in a {p['style']}) did not build; skipped")
                v += vs + GAP; row = max(row, us); continue
            occupied |= b.cells
            built.append((p, b))
            v += vs + GAP
            row = max(row, us)
        if not built and left:
            for p in left: log(f"  variant {p['index']} too big for the field; skipped")
            left = []
        rooms_json = []
        for p, b in built:
            main = next(r for r in b.rooms if r.kind == p["kind"])
            orig = {}
            for r in b.rooms:          # the neighbours too: their furniture shows through the doors, as in a map
                _, res = furnish_original(m, r, kind=r.kind, rng=random.Random(E.seed_of("furnish", p["seed"], r.id)),
                                          style=p["furnish"], engine=engine if r is main else None)
                orig[r.id] = res
            for r in b.rooms:
                xs = [x for x, _ in r.tiles]; ys = [y for _, y in r.tiles]
                rooms_json.append(dict(number=len(rooms_json) + 1, building=f"{p['role']} ({p['style']})", kind=r.kind,
                                       purpose=("variant %d" % p["index"]) if r is main else f"neighbour of variant {p['index']}",
                                       tiles=len(r.tiles), box=[min(xs) - 1, min(ys) - 1, max(xs) + 3, max(ys) + 3],
                                       floor=sorted([x, y] for x, y in r.tiles)))
                if r is main:
                    done.append(dict(p, map=mname, room=r.id, number=len(rooms_json), floor_tiles=len(r.tiles),
                                     doors=len(r.doors), floor_material=r.floor, engine=engine or "default",
                                     originality=dict(max_sim=orig[r.id]["max_sim"], nearest=orig[r.id]["nearest"],
                                                      ok=orig[r.id]["ok"]),
                                     motif_log=getattr(r, "motif_log", None),
                                     centre=[round(sum(xs) / len(xs)), round(sum(ys) / len(ys))]))
        m.obj("PlayerStart", u0 + 3, v0 + 3)
        with open(os.path.join(out_dir, f"{mname}.rooms.json"), "w", encoding="utf-8") as f:
            json.dump(rooms_json, f, indent=1)
        lines = m.build(out_dir, check=False)
        bad = [l for l in lines if l.startswith("ERROR")]
        if bad: log("\n".join(bad))
        maps.append(os.path.join(out_dir, f"{mname}.map"))
        pending = left
    done.sort(key=lambda d: d["index"])
    return dict(maps=maps, variants=done)
