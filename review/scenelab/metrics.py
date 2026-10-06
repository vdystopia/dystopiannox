"""The scene lab's metric judge: what a scene is made of and how it is laid out, compared with Westwood's campaign scenes
of the same type, and whether a classifier can tell ours from Westwood's.

    py review/scenelab/metrics.py <scene> <iter>     re-judge an iteration already generated (tests/scenelab.py does this)

## Features per scene (features(); the same code measures Westwood's scenes and ours)

- pieces and types: n (pieces), types (distinct kinds), most_share (the commonest kind's share), entropy (of the
  families), fam_<family> (each family's share: fire, seat, bed, tent, store, cart, rack, tool, tomb, crop, ...);
- extent: reach (p90 distance of a piece from the middle, px), spread (rms), aniso (the short axis over the long);
- zones: groups (clusters of the solid pieces at 48 px), grp_size (pieces per group), grp_gap (median gap from a group
  to its nearest other group, px), open (share of the ground inside the scene's hull more than 46 px from any piece);
- gaps: nn_med, nn_p10 (each solid piece's nearest solid piece, px); details["pairs"] the median gap by family pair;
- alignment: rows (share of solid pieces in a row of three, evenly stepped), diag (share of nearest-neighbour steps
  along the screen's diagonals, as Nox's walls run), bed_fire (share of bedrolls whose foot points to the fire),
  seat_fire (share of seats 40-95 px from a fire);
- site: wall_near (share of pieces within 46 px of any wall line), built_near (of a built wall or fence), water_d (px
  from the middle to the nearest water), path_share (pieces on a path), path_d (px to the nearest path);
- people: cr_n (creatures within the scene's reach), cr_nn (their median nearest neighbour, px), cr_rel (their median
  distance from the middle over the scene's reach);
- overlap: pairs of solid pieces nearer than 0.85 of kit/spacing's gap, per piece.

Needs numpy and scikit-learn (py -m pip install --user numpy scikit-learn).
"""
import collections, json, math, os, re, statistics, sys
import labenv as E
import pieces as P

NATURAL_WALL = re.compile(r"Coni|Decidious|Aspen|Cave|Ice|Volcano|Root|Dirt|Rock|Hedge|Swamp|Forest|Tree|Snow|Mud|"
                          r"ManaMine", re.I)
WATER = re.compile(r"^Water|Swamp(Deep|Shallow)|WaterSwamp")
CORE = ["n", "types", "most_share", "entropy", "reach", "spread", "aniso", "groups", "grp_size", "grp_gap", "open",
        "nn_med", "nn_p10", "rows", "diag", "wall_near", "built_near", "water_d", "path_share", "path_d", "cr_n", "cr_nn",
        "cr_rel", "overlap"]
CAMP = ["bed_fire", "seat_fire"]
NOT_CLASSIFIED = {"cr_n", "cr_nn", "cr_rel"}       # Westwood's scenes have their monsters; ours their posts: shown, not
                                                   # classified (the lab's people stand where the kit's posts put them)
TEXT = {   # feature: (name, low text, high text, where to change it)
    "n": ("pieces", "only {v} pieces: thinner than Westwood's", "{v} pieces: fuller than Westwood's",
          "the scene's recipe: counts (kit/camps.py, kit/yards.py, kit/scenes.py CATALOGUE)"),
    "types": ("kinds", "only {v} kinds of thing", "{v} kinds of thing: more variety than Westwood shows",
              "the recipe's must/may pieces"),
    "most_share": ("one kind's share", "", "one kind makes {v} of the pieces", "the recipe's counts"),
    "entropy": ("mix of families", "a narrow mix of families ({v})", "a wide mix of families ({v})", "the recipe"),
    "reach": ("reach", "packed into {v} px", "spread {v} px from its middle", "the recipe's radii (camps CAMP_R...)"),
    "spread": ("spread", "packed tight (rms {v} px)", "spread wide (rms {v} px)", "the recipe's radii"),
    "aniso": ("shape", "laid out long and thin ({v})", "round, no main line ({v})", "the layout's rows"),
    "groups": ("zones", "{v} group(s): one heap, no zones", "{v} groups: broken into many bits", "zones and their gaps"),
    "grp_size": ("pieces per zone", "zones of {v} pieces: scattered singles", "zones of {v} pieces: big heaps", "zones"),
    "grp_gap": ("gap between zones", "zones only {v} px apart: they run together", "zones {v} px apart: they fall apart",
                "zone radii"),
    "open": ("open ground", "only {v} of its ground open: crammed", "{v} of its ground open: sparse", "density"),
    "nn_med": ("gap to the nearest piece", "pieces {v} px from their nearest: crowded",
               "pieces {v} px from their nearest: scattered", "kit/spacing.py and the recipe's steps"),
    "nn_p10": ("closest gaps", "the closest pairs {v} px apart: touching", "even the closest pairs {v} px apart: no stacks",
               "kit/spacing.py PAIR"),
    "rows": ("pieces in rows", "only {v} of the pieces in rows", "{v} of the pieces in rows: mechanical", "the layout"),
    "diag": ("on the wall lines", "only {v} of the steps along the screen diagonals: off Nox's grid",
             "{v} of the steps along the diagonals", "orient rows along the wall lines (scenes.line_of)"),
    "wall_near": ("against walls", "only {v} of the pieces near a wall", "{v} of the pieces against walls", "the site"),
    "built_near": ("against built walls", "only {v} near a built wall or fence", "{v} against built walls or fences",
                   "the site"),
    "water_d": ("water", "water {v} px from its middle", "water {v} px away", "the site"),
    "path_share": ("on the path", "", "{v} of its pieces on a path or road", "the site: keep off roads"),
    "path_d": ("road", "a path {v} px from its middle", "the nearest path {v} px away", "the site"),
    "cr_n": ("people", "{v} creatures", "{v} creatures", "kit/posts.py"),
    "cr_nn": ("people's spacing", "people {v} px from each other: a swarm", "people {v} px apart", "kit/posts.py GAP"),
    "cr_rel": ("people's places", "people huddled at the middle ({v} of the reach)", "people out at the edge ({v})",
               "kit/posts.py"),
    "overlap": ("overlaps", "", "{v} overlapping pairs per piece", "kit/spacing.py (pieces nearer than Westwood's gaps)"),
    "bed_fire": ("bedrolls to the fire", "only {v} of the bedrolls point their foot at the fire", "", "kit/camps.py beds"),
    "seat_fire": ("seats round the fire", "only {v} of the seats sit round the fire", "", "kit/camps.py hearth"),
}
MIN_WW = 5


def _pct(vals, p):
    v = sorted(vals)
    if not v: return None
    k = (len(v) - 1) * p / 100.0
    a, b = int(math.floor(k)), int(math.ceil(k))
    return v[a] + (v[b] - v[a]) * (k - a)


# ---------------------------------------------------------------------------------------------------- features
def _ctx(m):
    """Per map: wall lines (all, built), water and path tiles, grids for nearest queries."""
    if getattr(m, "_scn_ctx", None) is None:
        import decoration as D
        walls = {c: w for c, w in m.walls.items() if not w.invisible}
        built = {c: w for c, w in walls.items() if not NATURAL_WALL.search(w.material)}
        water = [((x + 1) * 23, (y + 1) * 23) for (x, y), t in m.tiles.items() if WATER.search(t["material"])]
        fam = {t: D.family(d["material"]) for t, d in m.tiles.items()}
        g = collections.defaultdict(list)
        for p in water: g[(int(p[0] // 92), int(p[1] // 92))].append(p)
        m._scn_ctx = dict(walls=walls, built=built, water=g, fam=fam)
    return m._scn_ctx


def _nearest(grid, x, y, cap):
    best = cap
    k = int(cap // 92) + 1
    for a in range(int(x // 92) - k, int(x // 92) + k + 1):
        for b in range(int(y // 92) - k, int(y // 92) + k + 1):
            for px, py in grid.get((a, b), ()):
                d = math.hypot(px - x, py - y)
                if d < best: best = d
    return best


def _hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3: return pts
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0: hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def _inside(poly, x, y):
    n, c = len(poly), False
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-9) + x1: c = not c
    return c


def _groups(pts, link=48.0):
    n = len(pts); parent = list(range(n))
    def f(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            if math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]) <= link: parent[f(i)] = f(j)
    g = collections.defaultdict(list)
    for i in range(n): g[f(i)].append(i)
    return list(g.values())


COT_FOOT = {"Cot1": (1, 1), "Cot2": (-1, 1), "Cot3": (-1, -1), "Cot4": (1, -1)}      # screen direction of the foot


def features(m, s):
    """(features, details) of a scene s (dict: pieces [[type, x, y]], seeds) on map m (validate/mapdata.MapData)."""
    from kit import spacing as SP
    ctx = _ctx(m)
    pcs = [(t, float(x), float(y)) for t, x, y in s["pieces"]]
    n = len(pcs)
    xs = [x for _, x, _ in pcs]; ys = [y for _, _, y in pcs]
    cx, cy = (sum(xs) / n, sum(ys) / n) if n else tuple(s["anchor"])
    f, d = {}, {}
    kinds = collections.Counter(P.base(t) for t, _, _ in pcs)
    fams = collections.Counter(P.family(t) for t, _, _ in pcs)
    f["n"] = n
    f["types"] = len(kinds)
    f["most_share"] = round(max(kinds.values()) / n, 3) if n else 0
    f["entropy"] = round(-sum(c / n * math.log(c / n) for c in fams.values()), 3) if n else 0
    for fam in P.FAMS: f[f"fam_{fam}"] = round(fams.get(fam, 0) / n, 3) if n else 0
    dist = [math.hypot(x - cx, y - cy) for _, x, y in pcs]
    f["reach"] = round(_pct(dist, 90), 1) if dist else 0
    f["spread"] = round(math.sqrt(sum(v * v for v in dist) / n), 1) if n else 0
    if n >= 3:
        sxx = sum((x - cx) ** 2 for x in xs) / n; syy = sum((y - cy) ** 2 for y in ys) / n
        sxy = sum((x - cx) * (y - cy) for x, y in zip(xs, ys)) / n
        tr, det = sxx + syy, sxx * syy - sxy * sxy
        l1 = tr / 2 + math.sqrt(max(0, tr * tr / 4 - det)); l2 = tr / 2 - math.sqrt(max(0, tr * tr / 4 - det))
        f["aniso"] = round(math.sqrt(max(0, l2) / l1), 3) if l1 > 0 else 1.0
    else: f["aniso"] = 0.0
    solid = [(t, x, y) for t, x, y in pcs if not P.LOOSE.match(t)] or pcs
    sp = [(x, y) for _, x, y in solid]
    gs = _groups(sp)
    f["groups"] = len(gs)
    f["grp_size"] = round(len(sp) / max(1, len(gs)), 2)
    gaps = []
    for gi in gs:
        others = [j for g2 in gs if g2 is not gi for j in g2]
        if others:
            gaps.append(min(math.hypot(sp[i][0] - sp[j][0], sp[i][1] - sp[j][1]) for i in gi for j in others))
    f["grp_gap"] = round(statistics.median(gaps), 1) if gaps else 0.0
    nn, steps = [], []
    for i, (x, y) in enumerate(sp):
        best = None
        for j, (x2, y2) in enumerate(sp):
            if i == j: continue
            dd = math.hypot(x - x2, y - y2)
            if best is None or dd < best[0]: best = (dd, x2 - x, y2 - y)
        if best:
            nn.append(best[0])
            a = math.degrees(math.atan2(best[2], best[1])) % 90
            steps.append(min(abs(a - 45), 45 - abs(a - 45)) <= 12 or False)
    f["nn_med"] = round(statistics.median(nn), 1) if nn else 0.0
    f["nn_p10"] = round(_pct(nn, 10), 1) if nn else 0.0
    f["diag"] = round(sum(steps) / len(steps), 3) if steps else 0.0
    # rows: a piece with two others on either side of it, near and in line
    row_r = max(70.0, 1.5 * f["nn_med"])
    inrow = set()
    for i, (x, y) in enumerate(sp):
        nb = [(j, x2 - x, y2 - y) for j, (x2, y2) in enumerate(sp) if j != i and 12 < math.hypot(x2 - x, y2 - y) < row_r]
        for a in range(len(nb)):
            for b in range(a + 1, len(nb)):
                _, ax, ay = nb[a]; _, bx, by = nb[b]
                la, lb = math.hypot(ax, ay), math.hypot(bx, by)
                if (ax * bx + ay * by) / (la * lb) < -0.94 and abs(la - lb) < 0.35 * max(la, lb):
                    inrow |= {i, nb[a][0], nb[b][0]}
    f["rows"] = round(len(inrow) / len(sp), 3) if sp else 0.0
    # open ground inside the hull
    hull = _hull([(round(x), round(y)) for x, y in sp + [(x, y) for _, x, y in pcs]])
    if len(hull) >= 3:
        x0, x1, y0, y1 = min(p[0] for p in hull), max(p[0] for p in hull), min(p[1] for p in hull), max(p[1] for p in hull)
        cells = [(x, y) for x in range(int(x0), int(x1) + 1, 23) for y in range(int(y0), int(y1) + 1, 23) if _inside(hull, x, y)]
        far = sum(1 for x, y in cells if min(math.hypot(x - a, y - b) for _, a, b in pcs) > 46)
        f["open"] = round(far / len(cells), 3) if cells else 0.0
    else: f["open"] = 0.0
    # the site
    f["wall_near"] = round(sum(SP.wall_clearance(ctx["walls"], x, y, reach=3) < 46 for _, x, y in pcs) / n, 3) if n else 0
    f["built_near"] = round(sum(SP.wall_clearance(ctx["built"], x, y, reach=3) < 46 for _, x, y in pcs) / n, 3) if n else 0
    f["water_d"] = round(_nearest(ctx["water"], cx, cy, 600.0), 1)
    fam = ctx["fam"]
    around = collections.Counter(v for (tx, ty), v in fam.items() if abs((tx + 1) * 23 - cx) < 300 and abs((ty + 1) * 23 - cy) < 300)
    ground = next((g for g, _ in around.most_common() if g not in ("water",)), "grass")
    path_fams = {"dirt", "town_paving"} - {ground}
    on = lambda x, y: fam.get(m.tile_at_cell(m.cell_of(x, y))) in path_fams
    f["path_share"] = round(sum(on(x, y) for _, x, y in pcs) / n, 3) if n else 0
    pd = 400.0
    for (tx, ty), v in fam.items():
        if v in path_fams:
            dd = math.hypot((tx + 1) * 23 - cx, (ty + 1) * 23 - cy)
            if dd < pd: pd = dd
    f["path_d"] = round(pd, 1)
    # the people
    R = max(f["reach"], 120.0) + 60
    cr = [(o["x"], o["y"]) for o in m.objects if P.creature(o) and math.hypot(o["x"] - cx, o["y"] - cy) <= R]
    f["cr_n"] = len(cr)
    cnn = [min(math.hypot(a[0] - b[0], a[1] - b[1]) for b in cr if b is not a) for a in cr] if len(cr) > 1 else []
    f["cr_nn"] = round(statistics.median(cnn), 1) if cnn else 0.0
    f["cr_rel"] = round(statistics.median([math.hypot(x - cx, y - cy) for x, y in cr]) / max(f["reach"], 60), 3) if cr else 0.0
    # overlap
    ov = 0
    for i in range(len(solid)):
        for j in range(i + 1, len(solid)):
            g = SP.gap(solid[i][0], solid[j][0]) * 0.85
            if g and math.hypot(solid[i][1] - solid[j][1], solid[i][2] - solid[j][2]) < g: ov += 1
    f["overlap"] = round(ov / max(1, len(solid)), 3)
    # the camp's hearth: seats round the fire, bedrolls' feet to it
    fires = [(x, y) for t, x, y in pcs if P.family(t) == "fire"]
    seats = [(x, y) for t, x, y in pcs if P.family(t) == "seat"]
    cots = [(t, x, y) for t, x, y in pcs if t in COT_FOOT]
    if fires:
        near_f = lambda x, y: min(math.hypot(x - a, y - b) for a, b in fires)
        f["seat_fire"] = round(sum(40 <= near_f(x, y) <= 95 for x, y in seats) / len(seats), 3) if seats else 0.0
        good = 0
        for t, x, y in cots:
            fx, fy = min(fires, key=lambda p: math.hypot(p[0] - x, p[1] - y))
            ux, uy = COT_FOOT[t]; L = math.hypot(fx - x, fy - y) or 1
            good += ((fx - x) * ux + (fy - y) * uy) / (L * math.sqrt(2)) > 0.5
        f["bed_fire"] = round(good / len(cots), 3) if cots else 0.0
    else:
        f["seat_fire"] = f["bed_fire"] = None
    pairs = collections.defaultdict(list)
    for i, (t, x, y) in enumerate(solid):
        best = None
        for j, (t2, x2, y2) in enumerate(solid):
            if i == j: continue
            dd = math.hypot(x - x2, y - y2)
            if best is None or dd < best[0]: best = (dd, P.family(t2))
        if best: pairs["-".join(sorted((P.family(t), best[1])))].append(best[0])
    d["pairs"] = {k: round(statistics.median(v), 1) for k, v in pairs.items()}
    d["kinds"] = dict(kinds)
    d["families"] = dict(fams)
    d["centre"] = [round(cx, 1), round(cy, 1)]
    return f, d


# ---------------------------------------------------------------------------------------------------- comparison
def westwood(typ):
    import labref
    return labref.westwood(typ)


def _fmt(v):
    if v is None: return "-"
    if isinstance(v, float) and abs(v - round(v)) > 1e-9: return f"{v:.2f}" if abs(v) < 10 else f"{v:.0f}"
    return str(int(round(v)))


def _percentile(vals, v):
    lo = sum(1 for x in vals if x < v); eq = sum(1 for x in vals if x == v)
    return round(100.0 * (lo + 0.5 * eq) / len(vals), 1)


def judge_feature(name, v, vals, label):
    vals = [x for x in vals if x is not None]
    if v is None or not vals: return None, None
    pc = _percentile(vals, v)
    if len(vals) >= 10: lo, hi = _pct(vals, 10), _pct(vals, 90)
    else: lo, hi = min(vals), max(vals)
    spread = (_pct(vals, 75) - _pct(vals, 25)) or (statistics.pstdev(vals) if len(vals) > 1 else 0) or max(0.05, abs(lo) * 0.2)
    if v < lo - 1e-9: side, dist = "low", (lo - v) / spread
    elif v > hi + 1e-9: side, dist = "high", (v - hi) / spread
    else: return pc, None
    nm, low, high, where = TEXT.get(name, (name, "{v} is low", "{v} is high", "the recipe"))
    if name.startswith("fam_"):
        fam = name[4:]
        nm, low, high, where = (f"{fam} share", f"{{v}} of the pieces are {fam} (fewer than Westwood's)",
                                f"{{v}} of the pieces are {fam} (more than Westwood's)", "the recipe's pieces")
    text = low if side == "low" else high
    if not text: return pc, None
    text = text.format(v=_fmt(v)) + f" (Westwood's {label}: {_fmt(lo)}-{_fmt(hi)}, median {_fmt(_pct(vals, 50))})"
    return pc, dict(feature=name, value=v, side=side, severity=round(min(dist, 10.0), 2), percentile=pc,
                    range=[lo, hi], text=text, where=where)


def names_for(typ):
    fams = [f"fam_{x}" for x in P.FAMS]
    return CORE + (CAMP if typ in ("bandit_camp", "ogre_camp", "urchin_camp") else []) + fams


def compare(f, typ):
    ww = westwood(typ)
    label = f"{len(ww)} {typ.replace('_', ' ')} scenes"
    pct, finds = {}, []
    for k in names_for(typ):
        vals = [s["features"].get(k) for s in ww]
        if k.startswith("fam_") and not any(vals) and not f.get(k): continue
        pc, fd = judge_feature(k, f.get(k), vals, label)
        pct[k] = pc
        if fd: finds.append(fd)
    finds.sort(key=lambda x: -x["severity"])
    return dict(pct=pct, findings=finds)


def strangers(kinds, typ):
    """Kinds of piece no Westwood scene of the type holds (with 4 or more Westwood scenes to say so)."""
    ww = westwood(typ)
    if len(ww) < 4: return []
    seen = {k for s in ww for k in s["details"]["kinds"]}
    fams_seen = {P.family(k) for s in ww for k in s["details"]["kinds"]}
    return sorted(k for k in kinds if k not in seen and P.family(k) not in fams_seen)


# ---------------------------------------------------------------------------------------------------- hard rules
def hard_rules(m, s, f, warns, typ):
    """The user's rules (review/FEEDBACK.md) as findings that fail a scene outright: the checker's exterior warnings
    round the scene (overlaps, a piece on a fence line, a pickable light, a swarm, a dock that does not reach out, a
    stump by a fire, a bedroll strewn alone, a heap with no purpose, a graveyard without graves), and the lab's own."""
    out = []
    for w in warns:
        rule = w.get("rule") or w.get("check")
        tag = {"exterior.camp_seat": "SW-3", "exterior.bedroll": "GW-4", "exterior.pile": "GW-2",
               "exterior.graveyard": "SW-9"}.get(rule, "")
        msg = w["msg"]
        if "overlap" in msg: tag = tag or "SW-5"
        if "fence or wall line" in msg: tag = tag or "AM-1"
        if "picks" in msg or "pick it up" in msg: tag = tag or "SW-8"
        if "swarm" in msg or "two bodies" in msg: tag = tag or "SW-1"
        if "dock" in msg: tag = tag or "AM-2"
        out.append(dict(rule=rule, text=f"{msg[:160]} [{tag}]".replace(" []", ""), source="validate/checks.py"))
    if typ == "graveyard" and f["fam_tomb"] * f["n"] < 4:
        out.append(dict(rule="graves", text="a graveyard with fewer than 4 graves [SW-9]", source="lab"))
    if typ == "pond_dock" and f["water_d"] > 120:
        out.append(dict(rule="dock water", text="the dock stands away from the water [AM-2]", source="lab"))
    return out


# ---------------------------------------------------------------------------------------------------- classifier
def classify(gen_feats, typ, seed=0):
    """Cross-validated AUC of Westwood against generated over the type's features. Returns dict(auc, auc_sd,
    n_westwood, n_generated, top=[(feature, own AUC, direction, generated median, Westwood median)])."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    ww = westwood(typ)
    wwf = [s["features"] for s in ww]
    allf = wwf + list(gen_feats)
    names = [k for k in names_for(typ) if k not in NOT_CLASSIFIED]
    names = [k for k in names if len({round(float(x.get(k) or 0), 4) for x in allf}) > 1]
    med = {k: statistics.median([float(x[k]) for x in allf if x.get(k) is not None] or [0.0]) for k in names}
    X = np.array([[float(x[k]) if x.get(k) is not None else med[k] for k in names] for x in allf])
    y = np.array([0] * len(wwf) + [1] * len(gen_feats))
    out = dict(n_westwood=len(wwf), n_generated=len(gen_feats), features=len(names))
    k = min(5, len(wwf), len(gen_feats))
    if k < 2 or not names:
        out.update(auc=None, auc_sd=None, top=[]); return out
    aucs = []
    for rep in range(10):
        skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed + rep)
        p = np.zeros(len(y))
        for tr, te in skf.split(X, y):
            clf = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=3000, class_weight="balanced"))
            clf.fit(X[tr], y[tr])
            p[te] = clf.predict_proba(X[te])[:, 1]
        aucs.append(roc_auc_score(y, p))
    out["auc"] = round(float(np.mean(aucs)), 3)
    out["auc_sd"] = round(float(np.std(aucs)), 3)
    top = []
    for j, kname in enumerate(names):
        a = roc_auc_score(y, X[:, j])
        top.append((kname, round(float(max(a, 1 - a)), 3), "higher" if a >= 0.5 else "lower",
                    round(float(np.median(X[y == 1, j])), 3), round(float(np.median(X[y == 0, j])), 3)))
    top.sort(key=lambda t: -t[1])
    out["top"] = top[:10]
    return out


# ---------------------------------------------------------------------------------------------------- an iteration
def judge_batch(typ, it, log=print):
    """Measures and judges an iteration's generated scenes (variants.json), writes metrics.json and returns it."""
    import labref
    d = E.iter_dir(typ, it)
    with open(os.path.join(d, "variants.json"), encoding="utf-8") as fh:
        batch = json.load(fh)
    import checks as C
    out = []
    by_map = collections.defaultdict(list)
    for v in batch["variants"]: by_map[v["map"]].append(v)
    for mname, vs in by_map.items():
        path = os.path.join(d, "map", mname + ".map")
        m = E.MD.load(path)
        try:
            warns_all = [w for w in C.check_exterior(m, None, None) if w["severity"] != "info" and w.get("x") is not None]
        except Exception as ex:
            log(f"  checker failed on {mname}: {ex}"); warns_all = []
        found = labref.find_scenes(m, "lab")
        for v in vs:
            ax, ay = v["anchor"]
            cands = [s for s in found if s["type"] == typ and math.hypot(s["anchor"][0] - ax, s["anchor"][1] - ay) < v["reach"]]
            if not cands:
                out.append(dict(index=v["index"], missing=True, variant=v, features=None, findings=[],
                                hard=[dict(rule="missing", text="no scene of the type found where the kit laid it",
                                           source="lab")]))
                continue
            s = min(cands, key=lambda s: math.hypot(s["anchor"][0] - ax, s["anchor"][1] - ay))
            f, det = features(m, s)
            cx, cy = det["centre"]
            R = max(f["reach"], 100) + 50
            warns = [w for w in warns_all if math.hypot(w["x"] - cx, w["y"] - cy) <= R]
            cmp_ = compare(f, typ)
            hard = hard_rules(m, s, f, warns, typ)
            st = strangers(det["kinds"], typ)
            out.append(dict(index=v["index"], variant=v, scene=dict(anchor=s["anchor"], pieces=s["pieces"]),
                            features=f, details=det, pct=cmp_["pct"], findings=cmp_["findings"], hard=hard,
                            strangers=st))
    out.sort(key=lambda x: x["index"])
    gen = [x["features"] for x in out if x.get("features")]
    cls = classify(gen, typ, seed=E.seed_of(typ) % 1000)
    tally = collections.defaultdict(list)
    for x in out:
        for fd in x["findings"]: tally[(fd["feature"], fd["side"])].append(fd)
    worst = sorted(tally.items(), key=lambda kv: (-len(kv[1]), -statistics.mean(q["severity"] for q in kv[1])))
    worst = [dict(feature=k[0], side=k[1], scenes=len(v), example=max(v, key=lambda q: q["severity"])["text"],
                  where=v[0]["where"]) for k, v in worst[:10]]
    hard_tally = collections.Counter(h["rule"] for x in out for h in x["hard"])
    res = dict(type=typ, iter=it, classifier=cls, westwood_scenes=len(westwood(typ)), worst=worst,
               hard_rules=dict(hard_tally), scenes_with_hard=sum(1 for x in out if x["hard"]),
               missing=sum(1 for x in out if x.get("missing")), scenes=out)
    with open(os.path.join(d, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    return res


def findings_text(res, n=6):
    """Plain-English findings for the batch: what gives it away, worst first."""
    lines = []
    c = res["classifier"]
    if c.get("auc") is not None:
        lines.append(f"A classifier tells ours from Westwood's with AUC {c['auc']:.2f} (0.5: it cannot).")
        for name, a, dirn, g, w in c["top"][:4]:
            nm = TEXT.get(name, (name.replace("fam_", "") + " share",))[0]
            lines.append(f"- {nm}: ours {_fmt(g)} against Westwood's {_fmt(w)} (alone it separates them at {a:.2f})")
    for w in res["worst"][:n]:
        lines.append(f"- {w['scenes']} of {len(res['scenes'])} scenes: {w['example']}. Where: {w['where']}")
    if res["hard_rules"]:
        lines.append("Hard rules broken: " + ", ".join(f"{k} x{v}" for k, v in res["hard_rules"].items()))
    return lines


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        r = judge_batch(sys.argv[1], sys.argv[2])
        print("\n".join(findings_text(r)))
    else:
        print(__doc__)
