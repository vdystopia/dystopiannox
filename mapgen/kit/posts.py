"""Where a camp's people stand (playtest 2026-10-05: "groups of hostile npcs need to be spread out between each other a
bit more. they cluster too tightly on a central point like a swarm"; Starwell playtest, the same day: "These NPCs are
all on top of each other like a swarm ... A digger camp's workers work, they don't crowd the fire").

Westwood's grouped creatures (another of the kind within 6 cells) stand 49 px from their nearest at p25 and 70 at
the median (corpus, 3,091 creatures). At its camps at most two stand at the fire (War05A's grunts, 47 and 56 px out);
the rest stand 120-270 px out about the camp (Con03A's swordsmen 194-273 px from the fire, its archer 226). So a camp's
people take posts in its zones: the leader by his tent and the take, one or two at the fire, the others by their
tents, at the store, the arms or the dig, the watch at the way in; every post GAP px from every other.

    posts = camp_posts(spec, camp, toward=square_px(*pines_c), sit=2, tents=2, watch=2, work=0)
    posts["leader"], posts["sit"], posts["tent"], posts["watch"], posts["work"]      # world px

`sit` asks for that many idle men: the first two stand at the fire, any more at the camp's other posts (the store, the
racks, the pot). `tents` beyond the camp's tents stand at those posts too; `work` at the dig (bandit_camp trade "dig").
The camp is what kit/camps.bandit_camp (or urchin_camp) returns; for an older camp record without "tents", tents and
bedrolls are read from the map round the fire.
"""
import math

GAP = 64.0          # px between two posts of a camp (Westwood's median between grouped creatures: 70)
AT_FIRE = 2         # never more than two at the fire


def _unit(dx, dy):
    L = math.hypot(dx, dy) or 1.0
    return dx / L, dy / L


def camp_posts(spec, camp, toward, sit=2, tents=2, watch=2, work=0, gap=GAP):
    """Posts (world px) for a camp's people (see the module's notes). Returns dict(leader, sit, tent, watch, work):
    the leader one point, the others lists of points, every one `gap` px from every other where the ground allows."""
    fx, fy = camp["fire"]
    ix, iy = _unit(toward[0] - fx, toward[1] - fy)            # the way in
    taken = []
    # the camp's pieces a person must not stand in (bedrolls, racks, the torch pole...): within 28 px of a piece's
    # middle, a loose stone or a flower aside
    from kit.spacing import LOOSE
    pieces = [(o["x"], o["y"]) for o in spec.d["objects"] if "type" in o and abs(o["x"] - fx) < 520 and
              abs(o["y"] - fy) < 520 and not LOOSE.match(o["type"]) and "Shadow" not in o["type"] and
              not o["type"].startswith(("ColorLight", "CaveRocksSmall", "CaveRocksPebbles", "Amb"))]
    clear = lambda p: all((p[0] - a) ** 2 + (p[1] - b) ** 2 >= 28 * 28 for a, b in pieces)
    far = lambda p, g=gap: clear(p) and all(math.hypot(p[0] - a, p[1] - b) >= g for a, b in taken)

    def take(p):
        taken.append(p)
        return p

    def ring(c, r, n=12, a0=0.0):
        return [(c[0] + r * math.cos(a0 + k * 2 * math.pi / n), c[1] + r * math.sin(a0 + k * 2 * math.pi / n))
                for k in range(n)]

    def first(cands, fallback):
        """The first candidate apart from every post taken; else round each candidate in widening rings; else the
        fallback's farthest-off ring point."""
        for g in (gap, gap * 0.85):
            for p in cands:
                if far(p, g): return take(p)
            for p in cands:
                for r in (34, 56):
                    for q in ring(p, r, 10):
                        if far(q, g): return take(q)
        return take(max(ring(fallback, 70, 12), key=lambda q: min([math.hypot(q[0] - a, q[1] - b) for a, b in taken]
                                                                  or [999])))
    # the leader: before his tent (the awning) by the take, facing the way in
    ch = camp.get("chest")
    if camp.get("leader"):
        leader = take(tuple(camp["leader"]))
    elif ch and "x" in ch:
        ux, uy = _unit(fx - ch["x"], fy - ch["y"])
        leader = take((ch["x"] + ux * 34, ch["y"] + uy * 34))
    else:
        leader = take((fx - ix * 90, fy - iy * 90))
    posts = [tuple(p) for p in camp.get("posts") or []]
    # at the fire: one or two, on the seats
    seats = [tuple(p) for p in camp.get("seats") or []]
    if not seats:
        a0 = math.atan2(iy, ix)
        seats = [(fx + 44 * math.cos(a0 + d), fy + 44 * math.sin(a0 + d)) for d in (2.2, -2.2)]
    sitting = []
    for k in range(sit):
        if k < AT_FIRE and k < len(seats):
            p = next((s for s in seats if all(math.hypot(s[0] - a, s[1] - b) >= gap for a, b in taken)), None)   # a seat's
            # spot stands by its bench by design
            if p: sitting.append(take(p)); continue
        sitting.append(first(posts + [p for p in camp.get("tents") or []], (fx, fy)))
    # by the tents and bedrolls
    homes = [tuple(p) for p in camp.get("tents") or []]
    if not homes and "tents" not in camp:
        found = []
        for o in spec.d["objects"]:
            t = o.get("type") or ""
            if ("Tent" in t or t.startswith(("Cot", "UrchinBed"))) and math.hypot(o["x"] - fx, o["y"] - fy) < 300:
                ux, uy = _unit(fx - o["x"], fy - o["y"])
                d = 44 if "Tent" in t else 30
                found.append((0 if "Tent" in t else 1, (o["x"] + ux * d, o["y"] + uy * d)))
        homes = [p for _, p in sorted(found)]
    by_tents = [first(homes + posts, (fx - ix * 120, fy - iy * 120)) for _ in range(tents)]
    # at work: at the dig, then the store
    working = [first(list(camp.get("work") or []) + posts, (fx, fy)) for _ in range(work)]
    # the watch at the approach, well apart across it
    lx, ly = camp.get("lookout") or (fx + ix * 200, fy + iy * 200)
    px_, py_ = -iy, ix
    watching = []
    for k in range(watch):
        side = (k % 2) * 2 - 1 if watch > 1 else 0
        off = 40 * (1 + k // 2) if watch > 1 else 0
        watching.append(first([(lx + side * px_ * off, ly + side * py_ * off)], (lx, ly)))
    return dict(leader=leader, sit=sitting, tent=by_tents, watch=watching, work=working)
