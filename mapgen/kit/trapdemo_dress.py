"""Dressing helpers for TrapDemo missions (kit/trapdemo.py Mission): the expedition's camp laid by the camp kit, open
spots for the plot's items, a spot cleared for a lever, a chest of loot against a wall.

    from kit.trapdemo_dress import kit_camp, open_spot, clear_around
    yard = M.rooms.pop("yard"); M.dress(); M.rooms = {"yard": yard, **M.rooms}   # the room kit skips the camp
    camp = kit_camp(M, "yard", trade="bandit")          # the hearth, the sleeping row, the store, the arms, the lookout
    M.person("yard", ..., *M.room_ab("yard", *camp["leader"]), face=camp["fire"])
    M.item("vault", "RedOrb", *open_spot(M, "vault", 6, 6))                      # on bare floor, in sight
"""
import math

SQ = 32.5
# what may stand on a spot an item or a lever is given: the floor's own marks, lights on the walls, people
SOFT = ("Torch", "PlayerStart", "Sign", "Amb", "Rug", "Carpet", "Blood", "Puddle")


def _ab(M, rid, o):
    return M.room_ab(rid, o["x"], o["y"])


def _solid(o):
    t = o.get("type", "")
    return t and not t.startswith(SOFT) and "clone" not in o


def _mouth_band(M, rid, x, y, deep=2.2, side=1.0):
    """Whether world point (x, y) lies in the band before one of the room's passage mouths (its whole width)."""
    for L_ in M.links:
        if rid not in (L_["a"], L_["b"]) or "part" not in L_: continue
        p = L_["part"]
        (x0, y0), (ux, uy), (vx, vy) = p.at(0, 0), p.direction(), p.across()
        pa, pb = ((x - x0) * ux + (y - y0) * uy) / SQ, ((x - x0) * vx + (y - y0) * vy) / SQ
        if (-deep < pa < 0.5 or p.length - 0.5 < pa < p.length + deep) and -side < pb < p.width + side:
            return True
    return False


def kit_camp(M, rid, trade="bandit", sleepers=3, tents=1, loot=()):
    """The expedition's camp laid by the camp kit (kit/camps.py bandit_camp: the hearth, the sleeping row against the
    back wall, the store, the arms or the dig, the lookout) on the room's floor, open toward its passage, the band
    before every mouth kept clear. Take the room out of M.dress() first. Returns the camp's spots (world px)."""
    from kit import camps
    part = M.parts[rid]

    class Land:
        pass
    land = Land()
    land.squares, land.roads, land.water, land.taken, land.taken_strict = set(part.squares), set(), set(), set(), set()
    for (i, j) in part.squares:
        x, y = camps.square_px(i + 0.5, j - 0.5)
        a, b = M.room_ab(rid, x, y)
        if not M.free(rid, a, b, clear=2.8) or _mouth_band(M, rid, x, y):
            land.taken_strict.add((i, j))
    centre = camps._sq(*part.centre)
    da, db = M.doors[rid][0]
    toward = camps._sq(*M.at(rid, da, db))
    return camps.bandit_camp(M.m, M.rng, land, centre, toward, loot=list(loot), sleepers=sleepers, tents=tents,
                             trade=trade, hideout=False)


def open_spot(M, rid, a, b, clear=0.9, wall=1.0, reach=6.0):
    """The point nearest room point (a, b) on bare floor: `clear` squares from every solid piece, `wall` squares from
    the walls, out of the passages' mouths. Returns (a, b)."""
    w, h = M.rooms[rid]["size"]
    pts = [(_ab(M, rid, o), o) for o in M.m.d["objects"] if _solid(o)]
    pts = [(ab, o) for ab, o in pts if -1 < ab[0] < w + 1 and -1 < ab[1] < h + 1]
    steps = int(reach / 0.25)
    for r in range(steps + 1):
        for k in range(max(1, 8 * r)):
            th = 2 * math.pi * k / max(1, 8 * r)
            ca, cb = a + 0.25 * r * math.cos(th), b + 0.25 * r * math.sin(th)
            if not (wall <= ca <= w - wall and wall <= cb <= h - wall): continue
            if _mouth_band(M, rid, *M.at(rid, ca, cb)): continue
            if all(math.hypot(ca - pa, cb - pb) >= clear for (pa, pb), _ in pts):
                return ca, cb
    return a, b


def wall_spot(M, rid, walls=("NE", "NW"), off=0.9, clear=1.1):
    """A spot `off` squares out from one of the room's back walls (NE: b = h, NW: a = 0; also SE, SW), with `clear`
    squares to every solid piece and out of the mouths, searched from each wall's middle outward. None if none is."""
    w, h = M.rooms[rid]["size"]
    pts = [_ab(M, rid, o) for o in M.m.d["objects"] if _solid(o)]
    for wall in walls:
        n = w if wall in ("NE", "SW") else h
        for k in range(int(n * 2)):
            t = n / 2 + (k // 2 + 0.5) * 0.5 * (1 if k % 2 else -1)
            if not 1.2 <= t <= n - 1.2: continue
            a, b = dict(NE=(t, h - off), SW=(t, off), NW=(off, t), SE=(w - off, t))[wall]
            if _mouth_band(M, rid, *M.at(rid, a, b)): continue
            if all(math.hypot(a - pa, b - pb) >= clear for pa, pb in pts):
                return a, b
    return None


def clear_around(M, rid, a, b, r=1.0):
    """Lifts the room kit's pieces within r squares of room point (a, b) (a lever's place by the wall)."""
    gone = [o for o in M.m.d["objects"] if _solid(o) and "scr" not in o and
            math.hypot(*(p - q for p, q in zip(_ab(M, rid, o), (a, b)))) < r]
    ids = {id(o) for o in gone}
    M.m.d["objects"] = [o for o in M.m.d["objects"] if id(o) not in ids]
    return [o["type"] for o in gone]


def chest(M, rid, a, b, items, t=None):
    """A chest of loot at room point (a, b), its back to the nearest wall (Westwood's variants by the wall behind:
    Chest3 on the NE wall, Chest4 on the NW, Chest1 on the SE, Chest2 on the SW)."""
    w, h = M.rooms[rid]["size"]
    if t is None:
        d = {"Chest4": a, "Chest1": w - a, "Chest2": b, "Chest3": h - b}
        t = min(d, key=d.get)
    return M.m.obj_px(t, *M.at(rid, a, b), items=list(items))
