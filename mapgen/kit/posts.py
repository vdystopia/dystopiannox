"""Where a hostile group's fighters stand (playtest 2026-10-05: "groups of hostile npcs need to be spread out between
each other a bit more. they cluster too tightly on a central point like a swarm").

Westwood's grouped creatures (another of the kind within 6 cells) stand 49 px from their nearest at p25 and 70 at
the median (corpus, 3,091 creatures). A camp's men take posts round it the way a camp is lived in: some sitting by the
fire on seats spaced round it, some by their tents and bedrolls, the leader at the head of the camp by the chest, the
watch at the approach, two of them well apart. Population.creature keeps every hostile creature GROUP_GAP px from the
others besides; when roused they come at the player from their own sides (kit/behaviours spreadOn).

    posts = camp_posts(spec, camp, toward=square_px(*pines_c), sit=2, tents=2, watch=2)
    posts["leader"], posts["sit"], posts["tent"], posts["watch"]      # world px; posts["face"]: what each faces

The camp is what kit/camps.bandit_camp returns (fire, seats, lookout, chest); tents and bedrolls are read from the map
round the fire, whatever the camp's layout.
"""
import math

GAP = 52.0          # px between two posts of a camp


def _unit(dx, dy):
    L = math.hypot(dx, dy) or 1.0
    return dx / L, dy / L


def camp_posts(spec, camp, toward, sit=2, tents=2, watch=2, gap=GAP):
    """Posts (world px) for a camp's men: `sit` by the fire, `tents` by the tents and bedrolls, `watch` at the
    approach (toward: world px where the way in comes from), and the leader's. Returns dict(leader, sit, tent, watch)
    with a list of points each (leader: one point)."""
    fx, fy = camp["fire"]
    ix, iy = _unit(toward[0] - fx, toward[1] - fy)            # the way in
    taken = []
    far = lambda p: all(math.hypot(p[0] - a, p[1] - b) >= gap for a, b in taken)

    def take(p):
        taken.append(p)
        return p
    # the leader at the head of the camp, by the chest of the take, facing the way in
    ch = camp.get("chest")
    if ch and "x" in ch:
        cx, cy = ch["x"], ch["y"]
        ux, uy = _unit(fx - cx, fy - cy)
        leader = take((cx + ux * 30, cy + uy * 30))
    else:
        leader = take((fx - ix * 62, fy - iy * 62))
    # by the fire: the seats spaced round it, every other one; more on a ring if the seats run out
    seats = list(camp.get("seats") or [])
    ring = [(fx + 46 * math.cos(a), fy + 46 * math.sin(a))
            for a in (math.atan2(iy, ix) + math.pi / 2 + k * math.pi / 4 for k in range(5))]
    sitting = []
    for p in seats + ring:
        if len(sitting) >= sit: break
        if far(p): sitting.append(take(p))
    # by the tents and bedrolls: in front of each, toward the fire
    homes = []
    for o in spec.d["objects"]:
        t = o.get("type") or ""
        if ("Tent" in t or t.startswith("Cot")) and math.hypot(o["x"] - fx, o["y"] - fy) < 260:
            homes.append((0 if "Tent" in t else 1, math.hypot(o["x"] - fx, o["y"] - fy), o["x"], o["y"], "Tent" in t))
    by_tents = []
    for _, _, x, y, tent in sorted(homes):
        if len(by_tents) >= tents: break
        ux, uy = _unit(fx - x, fy - y)
        d = 40 if tent else 22
        p = (x + ux * d, y + uy * d)
        if far(p): by_tents.append(take(p))
    back = math.atan2(-iy, -ix)
    for k in range(8):                                        # no tents: about the back of the camp
        if len(by_tents) >= tents: break
        a = back + (k - 3.5) * 0.45
        p = (fx + 104 * math.cos(a), fy + 104 * math.sin(a))
        if far(p): by_tents.append(take(p))
    # the watch at the approach, well apart across it
    lx, ly = camp.get("lookout") or (fx + ix * 120, fy + iy * 120)
    px_, py_ = -iy, ix
    watching = []
    for k in range(watch):
        side = (k % 2) * 2 - 1
        off = 46 * (1 + k // 2)
        watching.append(take((lx + side * px_ * off, ly + side * py_ * off)))
    return dict(leader=leader, sit=sitting, tent=by_tents, watch=watching)
