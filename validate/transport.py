"""Transporters on a map: the objects that move the player from one place to another (rules/TRANSPORTERS.md).

Read from the map data alone (MapData), shared by the checker (checks.check_transport) and the measurement of
Westwood's maps (rules/transporters.py). What the engine does (OpenNox v1.9.0-alpha13, legacy C of the original):

- lift: an ELEVATOR platform (Elevator, CaveElevator, GreenElevator, LOTDElevator, RedElevator, WhiteElevator) and
  its ELEVATOR_SHAFT (the *Pit) name each other by extent (xfer ExtentLink, both ways). An enabled platform cycles by
  itself: it waits a second, sinks (height 0 to 64, 2 a frame), and whatever stands on it is moved to the pit at
  height 32; it waits a second at the bottom and rises, and whatever stands on the pit comes back up onto the
  platform. Always two-way. Disabled, it stops (a script turns it on: ObjectOn / ObjectGroupOn).
- pad: a TRANSPORTER (TeleportPentagram; InvisibleTeleportPentagram, the invisible kind) with ExtentLink sends
  whatever stands on it to the linked object's spot (TeleportPentagram after its glow animation, the invisible one at
  once), with Westwood's teleport flash (fx 137) and sound (147) at both ends. One-way unless the target is a pad that
  links back. A pad with ExtentLink 0 does nothing: it is an arrival marker.
- exit: an EXIT (InvisibleExitArea, ExitCaveDown, LOTDStairs*Exit, TeleporterExit...) changes the map (xfer MapName);
  with an empty MapName it does nothing in a solo game.
"""
import collections, math
from mapdata import CELL, GRID, N4

LIFT, SHAFT, PAD, EXIT = "lift", "shaft", "pad", "exit"


def kind(o):
    cls = o["cls"]
    if "ELEVATOR_SHAFT" in cls: return SHAFT
    if "ELEVATOR" in cls: return LIFT
    if "TRANSPORTER" in cls: return PAD
    if "EXIT" in cls: return EXIT
    return None


Link = collections.namedtuple("Link", "kind src dst two_way enabled problem")


def links(m):
    """Every transporter on the map as a Link: kind (lift, pad, exit), src and dst objects (dst None when it names no
    object on this map), two_way, enabled (the source starts enabled), problem (None, or what is wrong with the link).
    A lift is listed once, from its platform; a pad pair that links both ways is listed from each side."""
    by_extent = {o["extent"]: o for o in m.objects if o.get("extent")}
    out = []
    for o in m.objects:
        k = kind(o)
        if not k: continue
        link = (o["xfer"] or {}).get("ExtentLink") or 0
        dst = by_extent.get(link) if link else None
        if k == LIFT:
            problem = None
            if not link: problem = "names no pit (ExtentLink 0)"
            elif dst is None: problem = f"names pit {link}, which is not on the map"
            elif kind(dst) != SHAFT: problem = f"names a {dst['type']}, not an elevator pit"
            elif (dst["xfer"] or {}).get("ExtentLink") != o["extent"]: problem = "its pit does not name it back"
            out.append(Link(LIFT, o, dst, True, o["enabled"], problem))
        elif k == SHAFT:
            back = by_extent.get(link) if link else None
            if back is None or kind(back) != LIFT:
                out.append(Link(LIFT, o, back, True, o["enabled"], "an elevator pit with no platform naming it"))
        elif k == PAD:
            if not link: continue                         # an arrival marker
            problem = None if dst is not None else f"names object {link}, which is not on the map"
            two = bool(dst is not None and kind(dst) == PAD and (dst["xfer"] or {}).get("ExtentLink") == o["extent"])
            out.append(Link(PAD, o, dst, two, o["enabled"], problem))
        elif k == EXIT:
            name = (o["xfer"] or {}).get("MapName") or ""
            out.append(Link(EXIT, o, None, False, o["enabled"], None if name else "names no map (does nothing solo)"))
    return out


def walk_blocked(m, object_cells=frozenset()):
    """Cells a walking player cannot enter: walls (not secret, destructible or opened by a script) and the cells of
    large blocking objects; doors are open (a key or a lever opens them in the story)."""
    walls = {c for c, w in m.walls.items() if not (w.secret or w.destructible or c in m.scripted_walls)}
    return walls | set(object_cells)


def regions(m, blocked):
    """cell -> region number over the floor (4-connected, `blocked` cells excluded), and region -> size in cells."""
    label, size = {}, collections.Counter()
    n = 0
    for c in m.cover:
        if c in label or c in blocked: continue
        n += 1
        label[c] = n; q = [c]
        while q:
            x, y = q.pop(); size[n] += 1
            for dx, dy in N4:
                nb = (x + dx, y + dy)
                if nb in label or nb in blocked or nb not in m.cover: continue
                if not (0 <= nb[0] < GRID and 0 <= nb[1] < GRID): continue
                label[nb] = n; q.append(nb)
    return label, size


def region_at(m, label, size, x, y, reach=2):
    """The region a player standing at (x, y) is in: the cell's own, else the largest within `reach` cells (the
    transporter's own footprint may block its cell)."""
    c = m.cell_of(x, y)
    if c in label: return label[c]
    near = {label[(c[0] + a, c[1] + b)] for a in range(-reach, reach + 1) for b in range(-reach, reach + 1)
            if (c[0] + a, c[1] + b) in label}
    return max(near, key=lambda r: size[r]) if near else None


def graph(m, lks, label, size):
    """region -> set of regions a transporter takes the player to (lifts both ways, pads one way)."""
    g = collections.defaultdict(set)
    for l in lks:
        if l.problem or l.dst is None: continue
        a = region_at(m, label, size, l.src["x"], l.src["y"])
        b = region_at(m, label, size, l.dst["x"], l.dst["y"])
        if a is None or b is None or a == b: continue
        g[a].add(b)
        if l.kind == LIFT: g[b].add(a)
    return g


def reach(g, start):
    seen, q = {start}, [start]
    while q:
        r = q.pop()
        for n in g.get(r, ()):
            if n not in seen: seen.add(n); q.append(n)
    return seen


def wall_clearance(m, x, y, radius=8):
    """Distance in px from (x, y) to the nearest wall cell's centre within `radius` cells (radius * CELL if none)."""
    cx, cy = m.cell_of(x, y)
    best = radius * CELL
    for a in range(-radius, radius + 1):
        for b in range(-radius, radius + 1):
            c = (cx + a, cy + b)
            w = m.walls.get(c)
            if w is None or w.invisible: continue
            best = min(best, math.hypot(c[0] * CELL + CELL / 2 - x, c[1] * CELL + CELL / 2 - y))
    return best
