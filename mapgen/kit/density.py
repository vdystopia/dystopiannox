"""Room density: how much of a room's floor its groups reach, filled toward Westwood's rooms of the type.

Independent blind judges named density the most common giveaway of generated rooms, on every type and with both
furnishing engines (review/NIGHTLOG.md, 2026-10-06: "a lone piece in the middle of a huge bare floor", "everything
bunched in one corner, the rest bare", "one or two table sets in a big room", "nine tenths of the floor empty"). The
density study (review/roomlab/README.md, Density) found why: our rooms hold Westwood's piece counts (the recipes' and
motifs' counts follow Westwood's rooms per room) but are built at the kit's scale (kit/identity.py BUILDING_SCALE: 1.25
times Westwood's in length, about 1.6 times in floor), so the same pieces reach far less of the floor, and what they
reach is gathered at one end. The measure that tells ours from Westwood's best is the share of the floor within REACH
units of a piece (furniture, rugs and clutter; not lights or hangings): bedroom 0.45-0.51 against Westwood's 0.68,
living room 0.44-0.51 against 0.80, laboratory 0.32-0.35 against 0.59, tavern 0.53 against 0.75 (AUC 0.76-1.0); the
largest bare rectangle and the furniture's offset from the middle follow it.

So both engines end their composition with fill() (before the lights and the placement grammar's audit): while the
room's reach is under its target, the bare spot farthest from every piece takes another group of the room's own: a wall
group on the wall nearest it (the motif engine: a cluster mined from Westwood's rooms of the type; the recipe engine:
one of the recipe's own families), or, where Westwood's rooms of the type stand groups free in the middle (their
mid_share) and the bare spot is out in the floor, a free group there (a table set, a workbench). Groups go where the
room is bare, so a big room is zoned through (a bed end and a sitting end) instead of one group and bare floor.

The target is a draw from Westwood's p25-p75 reach for the type (rules/out/density.json, from its curated campaign
rooms: py review/roomlab/labref.py density), less Westwood's own fall of reach with size within a type (its
reach_slope per e-fold of floor over the type's median), never under its p10. Every piece goes through the engine's
own gate (the object knowledge base's caps: one cauldron, one table set in a bedroom; the recipe's repeat caps: a
chapel's benches; the room's coverage limit), so the user's rules hold.

    target(rtype, cells, rng) -> reach the room should have
    reach(f) -> (share of the floor reached, [(distance, u, v, wall distance)] of the bare cells, farthest first)
    fill(f, rng) -> groups added; f is a kit/furnish.py Furnisher with density_wall(spot) and density_free(spot)
"""
import json, math, os
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(os.path.dirname(os.path.dirname(HERE)), "rules", "out", "density.json")
REACH = 2.0              # uv units: floor this close to a piece is in a group's reach (review/roomlab/metrics.py REACH)
CELL_TILES = 0.45        # the checker's floor tiles per furnisher cell (the lab's rooms: 49 tiles of 113 cells)
WALL_BAND = 2.6          # a bare spot this close to a wall takes a wall group
FREE_BAND = 3.2          # a bare spot this far from every wall may take a free group
TRIES = 40
LONE_AREA = 2.8          # square uv units: a piece standing free on its own is at least this big (a table, a long bench)
INWARD = 3.6             # uv units from a front wall: where a bare spot by it takes a free group instead
FRONT_IN = 0.75          # how often a bare spot by a front wall does so (else the wall takes what may stand there)
from kit.furnish import BACK_SIDES as FRONT_OK   # the back walls (NE, NW), whose pieces face the camera
DEBUG = os.environ.get("NOX_DENSITY_DEBUG") == "1"
FAIL_R = 2.2             # a spot that took nothing rules out the bare floor this close to it


@lru_cache(None)
def table():
    try:
        with open(PATH, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {"types": {}, "reach_slope": 0.0}


def stats(rtype):
    return table()["types"].get(rtype)


def target(rtype, cells, rng):
    """The reach this room should have: a draw from Westwood's p25-p75 for the type, less Westwood's own fall with size
    over the type's median, never under its p10. None when Westwood has nothing to say."""
    d = stats(rtype)
    if not d or "reach" not in d: return None
    r = d["reach"]
    t = rng.uniform(r["p25"], r["p75"])
    tiles = max(1.0, cells * CELL_TILES)
    p50 = max(1.0, (d.get("tiles") or {}).get("p50") or tiles)
    t += table().get("reach_slope", 0.0) * max(0.0, math.log(tiles / p50))
    return max(r["p10"], t)


def free_share(rtype):
    """How readily a bare spot out in the floor takes a free group: Westwood's share of pieces standing free in the
    middle of rooms of the type (p50 and p75), scaled."""
    d = stats(rtype) or {}
    m = d.get("mid_share") or {}
    return min(0.85, max(0.1, 1.25 * (m.get("p50", 0.0) + m.get("p75", 0.0))))


def grow(f):
    """How much more Westwood's rooms of the type would hold at this room's size: the square root of its floor over
    their median (Westwood's pieces grow with about the 0.47th power of a room's floor within a type)."""
    d = stats(f.rtype) or {}
    return math.sqrt(max(1.0, len(f.g.cells) * CELL_TILES / max(1.0, (d.get("tiles") or {}).get("p50") or 1.0)))


def family_ok(f, fam, have, rng):
    """Whether the density pass may add another piece of family `fam` (have: how many the room holds): a family
    Westwood's rooms of the type seldom hold comes in at its rate (a bench in a seventh of its bedrooms), and one the
    room already holds Westwood's share of (grown with the room) only now and then."""
    memo = f.__dict__.setdefault("_density_fam_ok", {})        # one draw per family and count in a room
    if (fam, have) in memo: return memo[(fam, have)]
    want = ((stats(f.rtype) or {}).get("fams") or {}).get(fam, 0.0) * grow(f)
    ok = not ((have >= want and rng.random() > 0.15) or (have == 0 and want < 0.5 and rng.random() > want))
    memo[(fam, have)] = ok
    return ok


def group_most(f, fam):
    """Most groups led by one family the density pass adds to a room: two, or as many as Westwood's rooms of the type
    hold of it grown with the room (a tavern's tables)."""
    want = ((stats(f.rtype) or {}).get("fams") or {}).get(fam, 0.0) * grow(f)
    return max(2, int(round(want)))


def _pieces(f):
    from kit.furnish import _family_of
    out = []
    for t, rec in f._typed:
        if rec[5] == "wall": continue
        fam = _family_of(t)
        if fam is None or fam == "wall_decor": continue
        out.append(rec)
    return out


def _dist(u, v, rec):
    return math.hypot(max(0.0, abs(u - rec[0]) - rec[2]), max(0.0, abs(v - rec[1]) - rec[3]))


GAIN_R = 3.0             # uv units: a group's reach round its spot, for the bare floor it would take in
_OFFS = [(a, b) for a in range(-3, 4) for b in range(-3, 4) if (a + b) % 2 == 0 and math.hypot(a, b) <= GAIN_R]


def reach(f):
    """(share of the room's floor within REACH of a piece, the bare cells as (distance to the nearest piece, u, v, wall
    distance), the heart of the bare floor first: the most bare cells within GAIN_R, then the farthest from a piece; a
    group there takes in the most bare floor, where the farthest bare cell lies in a corner)."""
    recs = _pieces(f)
    cells = list(f.g.cells)
    near, bare = 0, []
    for x, y in cells:
        u, v = x + y + 1.0, x - y
        d = min((_dist(u, v, r) for r in recs), default=99.0)
        if d <= REACH: near += 1
        else: bare.append((d, u, v, f.g.wall_dist(u, v)))
    at = {(int(u), int(v)) for _, u, v, _ in bare}
    gain = {(int(u), int(v)): sum(1 for a, b in _OFFS if (int(u) + a, int(v) + b) in at) for _, u, v, _ in bare}
    bare.sort(key=lambda s: (-gain[(int(s[1]), int(s[2]))], -s[0]))
    return near / max(1, len(cells)), bare


def _nearest_run(f, u, v):
    best = None
    for r in f.g.runs:
        a = v if r["line"] == "/" else u
        if not r["lo"] - 0.5 <= a <= r["hi"] + 0.5: continue
        d = abs((u if r["line"] == "/" else v) - r["coord"])
        if best is None or d < best[0]: best = (d, r)
    return best and best[1]


def fill(f, rng, log=None):
    """Groups added where the room is bare until its reach meets its target (see the module's doc). Returns how many
    groups went in; f.density_log records the target and each step."""
    goal = target(f.rtype, len(f.g.cells), rng)
    f.density_log = []
    if goal is None: return 0
    r0, bare = reach(f)
    # and up to Westwood's median cover for the type (its curated rooms), within the room's coverage limit: a room
    # whose few big pieces reach its floor can still read bare (the checker's composition.sparse)
    cov = ((stats(f.rtype) or {}).get("cover") or {}).get("p50")
    cov_goal = min(cov, 0.9 * getattr(f, "cover_max", 1.0)) if cov else 0.0
    f.density_log.append(f"density: reach {r0:.2f}, target {goal:.2f}; cover {f.coverage():.3f}, goal {cov_goal:.3f}")
    fs = free_share(f.rtype)
    d = stats(f.rtype) or {}
    over = len(f.g.cells) * CELL_TILES / max(1.0, (d.get("tiles") or {}).get("p50") or 1.0)
    fs = max(fs, min(0.8, 0.5 * math.log(max(1.0, over))))     # a room well over Westwood's size uses its middle
    failed, added = [], 0
    for _ in range(TRIES):
        r, bare = reach(f)
        if r >= goal and f.coverage() >= cov_goal: break
        ok = [b for b in bare if all(math.hypot(b[1] - a, b[2] - c) > FAIL_R for a, c in failed)]
        if not ok: break
        spot = ok[0]
        free_first = spot[3] >= FREE_BAND and rng.random() < fs
        inward = None
        run = _nearest_run(f, spot[1], spot[2])
        if run is not None and spot[3] <= WALL_BAND and run["side"] not in FRONT_OK and rng.random() < FRONT_IN:
            # by a front wall, where the camera sees only the backs of what stands against it (the user's rule; Westwood
            # keeps its front walls light): a free group a step in from it instead, the wall left bare
            k = INWARD - spot[3]
            inward = (spot[1] + run["sign"] * k, spot[2]) if run["line"] == "/" else (spot[1], spot[2] + run["sign"] * k)
            free_first = True
        order = ("free", "wall") if free_first else ("wall", "free")
        got, how = None, None
        for how in order:
            if how == "free" and spot[3] < FREE_BAND - 0.8 and inward is None: continue   # no room off the wall
            at = inward if how == "free" and inward is not None else (spot[1], spot[2])
            if how == "wall" and spot[3] > WALL_BAND and run is not None:
                # out in the floor: the nearest wall, level with the spot (a back wall's group reaches toward it)
                at = (run["coord"] + run["sign"] * 1.0, spot[2]) if run["line"] == "/" else (spot[1], run["coord"] + run["sign"] * 1.0)
            got = f.density_free(at) if how == "free" else f.density_wall(at)
            if got: break
        if got:
            added += 1
            f.density_log.append(f"  {how} group at {spot[1]:.0f},{spot[2]:.0f} (bare {spot[0]:.1f}, wall "
                                 f"{spot[3]:.1f}): {' '.join(o['type'] for o in got)}")
        else:
            failed.append((spot[1], spot[2]))
            if DEBUG: f.density_log.append(f"  miss at {spot[1]:.0f},{spot[2]:.0f} (bare {spot[0]:.1f}, wall {spot[3]:.1f}, "
                                           f"free first {free_first}): {getattr(f, '_density_why', '')}")
    r1, _ = reach(f)
    f.density_log.append(f"density: reach {r0:.2f} -> {r1:.2f} with {added} groups (target {goal:.2f}); cover "
                         f"{f.coverage():.3f}")
    if log is not None: log += f.density_log
    return added
