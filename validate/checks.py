"""The checks. Each takes a MapData (and the shared Context) and returns findings:
dict(check, severity, msg, x, y) with x, y in world pixels (None when map-wide).

Severities:
  error   - a defect the player will see or hit (black wall, see-through gap, hole to the void,
            broken door, misaligned kit, blocked doorway, ...). Westwood's maps have essentially none.
  warning - outside the range Westwood's campaign maps stay within (density, sizes, blends).
  info    - measurements, for the report.
Thresholds come from validate/baseline.json (validate/calibrate.py measures Westwood's maps).
"""
import collections, json, math, os, re
import mapdata as md
import room_types as RT
from mapdata import CELL, GRID, N4, DIAG, ARMS_OF, LINE_STEP, rules

LIGHT_NAME = re.compile(r"ColorLight|Torch|Candle|Lantern|Lamp|Sconse|Sconce|Flame|Fireplace|Brazier|Basin.*Lit|Chandelier|Lights?$", re.I)
KIT_RE = re.compile(r"^(DockDown|DockUp|RopeBridgeBroken[12]|RopeBridge[12]|LavaBridge[12])(.*?)(Front|Back)?$")
MP_ONLY = re.compile(r"^(Flag|GameBall|Crown|TeamBase|.*FlagBase)$")
NATURAL_WALL = re.compile(r"Cave|Rock|Dirt|Root|Tree|Decidious|Coni-|Aspen|Hedge|Shrub|Thorn|Volcano|IceWall|Shard|Mine", re.I)
WATER_RE = re.compile(r"Water", re.I)
TRAVEL = ("TRANSPORTER", "ELEVATOR", "ELEVATOR_SHAFT")
FLOOR_FURNITURE = {"bed", "nightstand", "counter_shop", "table", "chair", "bench", "desk", "stove", "storage"}   # bar counters meet walls by design


def F(check, severity, msg, x=None, y=None, **extra):
    return dict(check=check, severity=severity, msg=msg, x=x, y=y, **extra)


def cell_px(c):
    return c[0] * CELL + CELL / 2, c[1] * CELL + CELL / 2


def clusters(cells, gap=2):
    """Groups cells lying within `gap` cells of each other."""
    cells = set(cells); out = []
    while cells:
        seed = cells.pop(); group = [seed]; q = [seed]
        while q:
            x, y = q.pop()
            for dx in range(-gap, gap + 1):
                for dy in range(-gap, gap + 1):
                    n = (x + dx, y + dy)
                    if n in cells:
                        cells.remove(n); group.append(n); q.append(n)
        out.append(group)
    return out


def centre(cells):
    return cell_px((sum(c[0] for c in cells) / len(cells), sum(c[1] for c in cells) / len(cells)))


# ---- shared flood fills ----------------------------------------------------------------------------
class Context:
    """Flood fills shared by several checks.

    walk: cells a player can reach from the start points (for reachability). Walls block, except
          secret walls and walls a script removes (wall groups); doors and destructible walls are
          passable. Teleports and elevators connect every area they stand in.
    closed: the same with every wall shut, as the map looks before anything opens (for holes).
    sight: cells visible from `closed`. Visible walls (windows included) and closed doors block
          sight; invisible walls do not.
    Void cells (no floor tile) and the grid border stop the fills and are recorded as leaks.
    """

    def __init__(self, m):
        self.m = m
        self.starts = [m.cell_of(o["x"], o["y"]) for o in m.objects if o["type"] == "PlayerStart"]
        blockers = self.object_cells()
        walk_block = {c for c, w in m.walls.items() if not (w.secret or w.destructible or c in m.scripted_walls)}
        self.walk, self.walk_leaks = self._reach(walk_block | blockers)
        self.closed, self.closed_leaks = self._reach(set(m.walls) | blockers)
        # windows count as solid here: an outer-wall window showing the dark outside is normal
        sight_block = {c for c, w in m.walls.items() if not w.invisible} | set(m.door_gaps)
        self.sight, self.sight_leaks = self._flood(list(self.closed), sight_block - self.closed)

    def _reach(self, blocked):
        cells, leaks = self._flood(self.starts, blocked)
        # elevators and teleports join the areas they stand in (the object itself blocks its cell,
        # so "reached" means the player can get next to it)
        travel = [self.m.cell_of(o["x"], o["y"]) for o in self.m.objects if any(t in o["cls"] for t in TRAVEL)]
        around = lambda c: [c] + [(c[0] + dx, c[1] + dy) for dx, dy in N4]   # beside it, never across a wall
        if any(n in cells for t in travel for n in around(t)):
            seeds = [n for t in travel for n in around(t) if n not in blocked and n in self.m.cover]
            more, more_leaks = self._flood(seeds, blocked, cells)
            cells |= more; leaks |= more_leaks
        return cells, leaks

    def object_cells(self):
        """Cells whose centre lies inside a large blocking object (rocks, trees, blocker boxes):
        Westwood sometimes closes an edge with these instead of walls."""
        m, out = self.m, set()
        for o in m.objects:
            if not m.blocking(o) or "TRIGGER" in o["cls"]: continue
            r = m.radius(o)
            if r < 10: continue
            cx, cy = m.cell_of(o["x"], o["y"])
            k = int(r // CELL) + 1
            for x in range(cx - k, cx + k + 1):
                for y in range(cy - k, cy + k + 1):
                    if o["ext"] == "BOX":
                        inside = abs(x * CELL + 11.5 - o["x"]) <= o["ex"] / 2 and abs(y * CELL + 11.5 - o["y"]) <= o["ey"] / 2
                    else:
                        inside = math.hypot(x * CELL + 11.5 - o["x"], y * CELL + 11.5 - o["y"]) <= r
                    if inside: out.add((x, y))
        return out

    def _flood(self, seeds, blocked, already=frozenset()):
        m = self.m
        seen, leaks, q = set(), set(), []
        for s in seeds:
            if s in seen or s in already: continue
            if s not in m.cover: leaks.add(s); continue
            seen.add(s); q.append(s)
        while q:
            x, y = q.pop()
            for dx, dy in N4:
                n = (x + dx, y + dy)
                if n in seen or n in blocked or n in already: continue
                if not (0 <= n[0] < GRID and 0 <= n[1] < GRID) or n not in m.cover:
                    leaks.add(n); continue
                seen.add(n); q.append(n)
        return seen, leaks


# ---- checks ---------------------------------------------------------------------------------------
def check_setup(m, ctx, base):
    out = []
    t = m.info.get("type") or 0
    sp = bool(t & 0x1) or bool(t & 0x2)
    if not ctx.starts:
        out.append(F("setup", "error", "No PlayerStart: the player has nowhere to appear."))
    if sp:
        mp = [o for o in m.objects if MP_ONLY.match(o["type"])]
        for o in mp[:10]:
            out.append(F("setup", "warning", f"Multiplayer-only object {o['type']} in a single-player map.", o["x"], o["y"]))
    if not t:
        out.append(F("setup", "error", "Map type flags are 0: the game lists the map under no game mode."))
    return out


def check_wall_pieces(m, ctx, base):
    """Black walls: (material, shape, variation) combinations with no artwork in the game."""
    valid = rules("walls")["valid_variations"]
    bad = collections.defaultdict(list)
    for c, w in m.walls.items():
        if w.invisible: continue
        ok = valid.get(w.material, {}).get(str(w.facing), {})
        if str(w.variation) not in ok:
            bad[(w.material, w.facing, w.variation)].append(c)
    out = []
    for (mat, f, v), cells in bad.items():
        for g in clusters(cells, 4):
            out.append(F("wall_pieces", "error", f"{len(g)} wall piece(s) {mat} shape {f} variation {v} never appear in "
                         f"Westwood's maps and may draw black or invisible.", *centre(g)))
    return out


def check_wall_shapes(m, ctx, base):
    """See-through gaps: a neighbour reaches toward this piece but this piece does not reach back
    (e.g. a corner drawn as a straight piece). Door openings count as wall (jamb rule)."""
    out = []
    for c, w in m.walls.items():
        # natural walls (cave rock, roots, trees) draw as overlapping blobs where an unanswered arm
        # does not show; built walls (stone, brick, wood, stucco) show the gap
        if w.facing not in ARMS_OF or w.invisible or NATURAL_WALL.search(w.material): continue
        mine = ARMS_OF[w.facing]
        for d in DIAG:
            n = (c[0] + d[0], c[1] + d[1])
            if d in mine: continue
            back = (-d[0], -d[1])
            if back in m.arms(n) and (n in m.walls or n in m.door_gaps):
                if n in m.walls and m.walls[n].invisible != w.invisible: continue
                beside_door = n in m.door_gaps
                out.append(F("wall_shapes", "error",
                             (f"Wall piece beside a door opening is shaped as if the opening were empty "
                              f"({w.material}, shape {w.facing}); it leaves a visible gap at the door frame."
                              if beside_door else
                              f"Wall piece ({w.material}, shape {w.facing}) does not connect to the neighbouring "
                              f"piece that reaches toward it: a see-through gap."), *cell_px(c), cell=c))
                break
    return out


def check_boundary(m, ctx, base):
    """Holes to the outside. The game stops players at the edge of the floor, but the void beyond
    shows as black. Westwood closes edges with walls (98% of boundary length) or, on cliff maps,
    ends the floor with cliff-edge art. A short opening in an otherwise walled edge is a hole: the
    player sees out through it (the Mossford playtest)."""
    out = []
    leaks = ctx.closed_leaks | ctx.sight_leaks
    max_gap = base.get("hole_max_cells", 12)
    for g in clusters(leaks, 2):
        near = {(x + dx, y + dy) for x, y in g for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)}
        walls = [m.walls[c] for c in near if c in m.walls]
        opaque = sum(1 for w in walls if w.opaque)
        spot = min(g, key=lambda c: (c[0] * CELL - centre(g)[0]) ** 2 + (c[1] * CELL - centre(g)[1]) ** 2)
        x, y = cell_px(spot)
        if len(g) <= max_gap and opaque >= 2:
            invisible_only = any(w.invisible for w in walls)
            out.append(F("boundary", "error", f"Hole in the outer wall: {len(g)} cell(s) of void visible through a gap"
                         + (" closed only by an invisible wall" if invisible_only else "") + ".", x, y))
        elif len(g) > max_gap:
            out.append(F("boundary", "warning", f"Open edge: the floor runs into the void for {len(g)} cells with no wall. "
                         f"Westwood does this only for cliff edges.", x, y))
    return out


def door_kind(t, line=None):
    """'double' (Westwood never puts it in a 1-cell opening), 'single' (never in a 2-cell opening),
    'either' (Westwood uses both), or None for types with no evidence. With `line` ('/' or '\\'),
    Westwood's habit for that wall direction (BandedPlankDoor pairs only in '/' walls)."""
    r = rules("doors")["types"].get(t)
    if not r: return None
    bl = r.get("by_line", {}).get(line) if line else None
    if bl and bl.get("weighted_count", 0) >= 5: r = bl
    if r["share_one_cell"] < 0.05: return "double"
    if r["share_two_cell"] < 0.05: return "single"
    return "either"


def check_doors(m, ctx, base):
    out = []
    gaps = m.door_gaps
    for d in m.doors:
        o, g, line = d["obj"], d["gap"], d["line"]
        sx, sy = LINE_STEP[line]
        if d["in_wall_cell"]:
            out.append(F("doors", "error", f"{o['type']} stands on a wall piece instead of in an opening "
                         f"(wrong direction or position).", o["x"], o["y"]))
            continue
        prev, nxt = (g[0] - sx, g[1] - sy), (g[0] + sx, g[1] + sy)
        p_open, n_open = prev not in m.walls, nxt not in m.walls
        kind = door_kind(o["type"], line)
        walled = lambda sign: any((g[0] + sign * k * sx, g[1] + sign * k * sy) in m.walls for k in (1, 2, 3))
        if not walled(-1) and not walled(1):
            out.append(F("doors", "error", f"{o['type']} is not set in a wall: no wall beside its opening on either side.",
                         o["x"], o["y"]))
        elif p_open and n_open:
            pass                                              # wider opening (e.g. a pair at a wall end)
        elif kind == "double":
            if not (p_open or n_open):
                out.append(F("doors", "error", f"{o['type']} is half of a double door but fills a 1-cell opening: "
                             f"the frame shows a gap. Use the single-door type or a 2-cell opening.", o["x"], o["y"]))
            else:
                other = prev if p_open else nxt
                mate = gaps.get(other)
                if not mate or door_kind(mate["obj"]["type"]) not in ("double", "either") or mate["direction"] == d["direction"]:
                    out.append(F("doors", "error", f"{o['type']} has no matching half in the other cell of its "
                                 f"2-cell opening.", o["x"], o["y"]))
        elif kind == "single" and (p_open or n_open):
            other = prev if p_open else nxt
            if other in gaps and gaps[other]["obj"]["type"] == o["type"]:
                out.append(F("doors", "error", f"{o['type']} is hung as a pair in a '{line}' wall, which Westwood never "
                             f"does: its halves do not line up in that direction.", o["x"], o["y"]))
            elif other not in gaps:
                out.append(F("doors", "error", f"{o['type']} (a single door) is in a 2-cell opening: one cell stays open.",
                             o["x"], o["y"]))
    return out


def check_kits(m, ctx, base):
    """Bridge and dock pieces must sit at Westwood's exact step offsets, or the planks mismatch."""
    allowed = base.get("kit_steps", {})
    back = base.get("kit_back", {})
    tol = 3.0
    out = []
    for kit, fronts, backs in kit_pieces(m):
        steps = allowed.get(kit, [])
        for o in fronts:
            p = nearest_piece(o, fronts)
            if not p or not steps: continue
            dx, dy = p["x"] - o["x"], p["y"] - o["y"]
            best = min(math.hypot(dx - s[0], dy - s[1]) for s in steps)
            if best > tol:
                out.append(F("kits", "error", f"{o['type']} is {best:.0f} px off every step Westwood uses between {kit} "
                             f"pieces: the planks will not line up.", o["x"], o["y"]))
        offs = back.get(kit, [])
        for o in backs:
            if not nearest_piece(o, fronts): continue          # railing without a deck: Westwood does this too
            if offs and not any(abs(f["x"] + b[0] - o["x"]) <= tol and abs(f["y"] + b[1] - o["y"]) <= tol
                                for f in fronts for b in offs):
                out.append(F("kits", "error", f"{o['type']} is not at any of Westwood's offsets from its front piece.",
                             o["x"], o["y"]))
    return out


def kit_pieces(m):
    """[(kit, front pieces, back pieces)]: bridge and dock kits are chains of front pieces, each
    rope or lava bridge piece with a back (railing) piece behind it."""
    pieces = collections.defaultdict(list)
    for o in m.objects:
        k = KIT_RE.match(o["type"])
        if k: pieces[k.group(1)].append((o, k.group(3)))
    return [(kit, [o for o, s in ps if s != "Back"], [o for o, s in ps if s == "Back"]) for kit, ps in pieces.items()]


def nearest_piece(o, pieces, max_px=100):
    near = [p for p in pieces if p is not o and abs(p["x"] - o["x"]) < max_px and abs(p["y"] - o["y"]) < max_px]
    return min(near, key=lambda p: math.hypot(p["x"] - o["x"], p["y"] - o["y"])) if near else None


def wall_cell_side(m, c, o, depth=0.3):
    """Where an object whose centre falls in wall cell c stands. "front" is in front of a NE or NW wall, at least
    `depth` units on the room's side of the wall's line, and is drawn in front of the wall: Westwood's snug chests and
    desks often stand so. "hidden" is behind a SE or SW wall, drawn under it. "inside" is on the line, or in a corner
    or junction piece."""
    w = m.walls[c]
    u, v = uv_of(o)
    x, y = c
    if w.facing == 0:                       # a '/' wall: the room on its lower right has it as the NW wall
        off = u - (x + y + 1)
        return "front" if off >= depth else "hidden" if off <= -depth else "inside"
    if w.facing == 1:                       # a '\' wall: the room on its lower left has it as the NE wall
        off = v - (x - y)
        return "front" if off <= -depth else "hidden" if off >= depth else "inside"
    return "inside"


def check_objects(m, ctx, base):
    out = []
    unreach = []
    # Westwood opens areas with scripts (levers, keys, secret walls) and moves creatures in from
    # off the map; a map with no script functions can do neither, so there these are defects
    scripted = bool(set(m.script_funcs) - {"GLOBAL", "MapInitialize"})     # the blank template has these two
    for o in m.objects:
        c = m.cell_of(o["x"], o["y"])
        cls = o["cls"]
        important = "MONSTER" in cls or m.is_door(o) or o["type"] == "PlayerStart" or \
            any(k in cls for k in ("WEAPON", "ARMOR", "FOOD")) or o["xtype"] == "NPCXfer"
        if c not in m.cover and important:
            # Westwood parks scripted creatures off the map until a script moves them in
            out.append(F("objects", "info" if scripted else "error",
                         f"{o['type']} stands in the void (no floor under it).", o["x"], o["y"]))
            continue
        if RT.family(o["type"]) in FLOOR_FURNITURE and c in m.walls and m.walls[c].opaque and not m.walls[c].secret:
            side = wall_cell_side(m, c, o)
            if side == "inside":
                out.append(F("objects", "warning", f"{o['type']} stands inside a wall piece.", o["x"], o["y"]))
            elif side == "hidden":
                out.append(F("objects", "warning", f"{o['type']} stands in a SE or SW wall's cell: the wall is drawn over "
                             f"it.", o["x"], o["y"]))
        swims_or_flies = "AIRBORNE" in o["flags"] or WATER_RE.search(m.floor_at(o["x"], o["y"]) or "")
        # an item on a table stands in the table's blocked cells: reachable when the player can stand beside it
        beside = any((c[0] + a, c[1] + b) in ctx.walk for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2))
        if important and not m.is_door(o) and not swims_or_flies and not beside and ctx.starts:
            unreach.append(o)
    if unreach:
        sev = "info" if scripted else "error"
        for k, o in enumerate(unreach[:25]):
            why = _what_blocks(m, ctx, o) if k < 6 else ""
            out.append(F("reachability", sev, f"{o['type']} cannot be reached from the player start{why}.", o["x"], o["y"]))
        if len(unreach) > 25:
            out.append(F("reachability", sev, f"... and {len(unreach) - 25} more unreachable objects."))
    return out


def _what_blocks(m, ctx, o):
    """The objects standing in the way of an unreachable object (Deepvault's review: finding the pillars that shut
    off a camp took a hand-written min-cut): the shortest way to it with objects ignored, walls not, and the blocking
    objects on that way. Returns ': blocked by Type at (x, y), ...' or ''."""
    import collections
    target = m.cell_of(o["x"], o["y"])
    walls = {c for c, w in m.walls.items() if not (w.secret or w.destructible or c in m.scripted_walls)}
    prev = {s: None for s in ctx.starts}
    q = collections.deque(ctx.starts)
    end = None
    while q:
        c = q.popleft()
        if abs(c[0] - target[0]) <= 1 and abs(c[1] - target[1]) <= 1: end = c; break
        for dx, dy in N4:
            n = (c[0] + dx, c[1] + dy)
            if n in prev or n in walls or n not in m.cover: continue
            prev[n] = c; q.append(n)
    if end is None: return ": walled off (no way even past the objects)"
    path = set()
    while end is not None: path.add(end); end = prev[end]
    hits = []
    for p in m.objects:
        if p is o or not m.blocking(p) or "TRIGGER" in p["cls"]: continue
        r = m.radius(p)
        if r < 10: continue
        pc = m.cell_of(p["x"], p["y"])
        if any(abs(pc[0] - c[0]) <= 1 and abs(pc[1] - c[1]) <= 1 for c in path):
            hits.append(p)
    if not hits: return ""
    return ": blocked by " + ", ".join(f"{p['type']} at ({p['x']:.0f}, {p['y']:.0f})" for p in hits[:3])


def check_story_gates(m, ctx, base):
    """A story gate seals what it guards: with every door locked to a mechanism (a gate only a script opens) shut,
    no exit can be reached from the start (Emberhollow's review: nothing else proved the Cinder Gate crossed the
    whole road). Doors locked to a key are left open here: the key is in the map."""
    out = []
    sealed = {d["gap"] for d in m.doors if (d["obj"].get("xfer") or {}).get("LockType") == "Mechanism"}
    exits = [o for o in m.objects if "EXIT" in o["cls"]]
    if not sealed or not exits or not ctx.starts: return out
    walk_block = {c for c, w in m.walls.items() if not (w.secret or w.destructible or c in m.scripted_walls)}
    cells, _ = ctx._reach(walk_block | ctx.object_cells() | sealed)
    for o in exits:
        c = m.cell_of(o["x"], o["y"])
        # the exit area blocks its own cells (an immobile object): standing beside it is reaching it
        if any((c[0] + a, c[1] + b) in cells for a in range(-3, 4) for b in range(-3, 4)):
            out.append(F("story", "error", f"{o['type']} can be reached with the story's gates locked: the gate does not "
                         f"seal the way out.", o["x"], o["y"]))
            break
    return out


def check_doorways(m, ctx, base):
    """Furniture, trees or rocks standing in a door opening or right in front of it."""
    out = []
    blockers = [o for o in m.objects if m.blocking(o) and "TRIGGER" not in o["cls"] and not re.match(r"Extent|Invisible", o["type"])]
    grid = collections.defaultdict(list)
    for o in blockers: grid[(int(o["x"] // 92), int(o["y"] // 92))].append(o)
    clearance = base.get("doorway_clearance_px", 8)
    for d in m.doors:
        gx, gy = cell_px(d["gap"])
        for o in (p for i in (-1, 0, 1) for j in (-1, 0, 1) for p in grid[(int(gx // 92) + i, int(gy // 92) + j)]):
            dist = math.hypot(o["x"] - gx, o["y"] - gy) - m.radius(o)
            if dist < clearance:
                out.append(F("doorways", "error", f"{o['type']} blocks the doorway of {d['obj']['type']}.", o["x"], o["y"]))
    return out


def outdoor_on_floors(m):
    """The tiles of a generated map's rooms that carry the outdoor ground, as their floor or as an edge spilt onto them
    (Starwell playtest, 2026-10-05: "Tile blending on the inside of doors seems consistently off", the path's dirt and
    the grass drawn on the boards just inside the door). A room's tile is one whose cells all lie in the room or in its
    walls and doorways; an outdoor material is one that lies on the ground outside and on no room's tiles (a doorstep
    takes the room's floor, so the room's floor is never outdoor). Only the rooms a design declared (Westwood's own
    doorways carry the ground's edge inside at about 1 in 10). Returns [(tile, material, how)]."""
    rooms = [r for r in find_rooms(m) if r.get("declared") and not r.get("yard")]
    if not rooms: return []
    blocked = set(m.walls) | set(m.door_gaps)
    room_cells = set().union(*(set(r["cells"]) for r in rooms))
    cells = lambda t: ((t[0], t[1]), (t[0] + 1, t[1]), (t[0], t[1] + 1), (t[0] + 1, t[1] + 1))
    inside, outdoor = [], set()
    room_of = {c: k for k, r in enumerate(rooms) for c in r["cells"]}
    per_room = collections.defaultdict(collections.Counter)
    for t, rec in m.tiles.items():
        cs = cells(t)
        if all(c in room_cells or c in blocked for c in cs) and any(c in room_cells for c in cs):
            inside.append(t)
            per_room[next(room_of[c] for c in cs if c in room_of)][rec["material"]] += 1
        elif not any(c in room_cells for c in cs):
            outdoor.add(rec["material"])
    # a room's own floors (those that make up a fifth or more of some room: its boards, its carpet of floor tiles) are
    # never outdoor ground, though a doorstep takes them; one grass tile laid inside a room is (it had cancelled itself
    # out of the outdoor materials, so a floor of ground inside a room was never found)
    indoor_mats = {mat for cnt in per_room.values() for mat, n in cnt.items() if n >= 0.2 * sum(cnt.values())}
    outdoor -= indoor_mats
    out = []
    for t in inside:
        rec = m.tiles[t]
        if rec["material"] in outdoor: out.append((t, rec["material"], "floor"))
        for e in rec["edges"]:
            if e[0] in outdoor: out.append((t, e[0], "edge")); break
    return out


def check_thresholds(m, ctx, base):
    """No outdoor ground lies on a room's floor, nor blends onto it (outdoor_on_floors)."""
    out = []
    for t, mat, how in outdoor_on_floors(m):
        out.append(F("floors", "warning", f"The outdoor {mat} {'lies on' if how == 'floor' else 'blends onto'} a room's "
                     f"floor: a doorway's ground stops at the wall line (Westwood's doorstep takes the room's floor).",
                     (t[0] + 1) * CELL, (t[1] + 1) * CELL))
    return out


def edge_between(m, a, b):
    ta, tb = m.tiles[a], m.tiles[b]
    return any(e[0] == tb["material"] for e in ta["edges"]) or any(e[0] == ta["material"] for e in tb["edges"])


def check_floors(m, ctx, base):
    fl = rules("floors")
    never = {frozenset((r["a"], r["b"])) for r in fl["never_touch"]}
    blended = {frozenset((r["a"], r["b"])): r for r in fl["blend"]}
    min_share = base.get("blend_share_required", 0.9)
    harsh, bad_touch, contacts = collections.defaultdict(list), collections.defaultdict(list), collections.Counter()
    for (x, y), t in m.tiles.items():
        for d in ((1, -1), (1, 1)):                           # E and S sides; each pair once
            n = (x + d[0], y + d[1])
            if n not in m.tiles: continue
            a, b = t["material"], m.tiles[n]["material"]
            if a == b: continue
            # side neighbours share one grid cell: a visible wall there hides the seam (a building's
            # floor against the ground outside)
            shared = (x + 1, y) if d == (1, -1) else (x + 1, y + 1)
            if shared in m.walls and m.walls[shared].opaque: continue
            pair = frozenset((a, b))
            if pair in never: bad_touch[pair].append((x + 1, y + 1))
            r = blended.get(pair)
            if r and (r["edge_share_sp"] or 0) >= min_share and (r["maps_sp"] or 0) >= 3:
                contacts[pair] += 1
                if not edge_between(m, (x, y), n): harsh[pair].append((x + 1, y + 1))
    out = []
    for pair, cells in bad_touch.items():
        for g in clusters(cells, 3):
            out.append(F("floors", "error", f"{' and '.join(sorted(pair))} touch directly: Westwood always puts another "
                         f"floor between them.", *centre(g)))
    # Westwood leaves a few seams unblended (95% of a map's pairs: under a quarter of the seams), so
    # only a pair left mostly unblended is reported
    for pair, cells in harsh.items():
        if len(cells) < 4 or len(cells) / contacts[pair] <= 0.25: continue
        for g in clusters(cells, 3):
            out.append(F("floors", "warning", f"Hard seam between {' and '.join(sorted(pair))} ({len(g)} tile sides): "
                         f"Westwood blends this pair with edge pieces.", *centre(g)))
    tot, bad = sum(contacts.values()), sum(len(v) for v in harsh.values())
    lim = base.get("unblended_share_p95", 0.055)
    if tot >= 20 and bad / tot > lim:
        out.append(F("floors", "warning", f"{bad / tot:.0%} of floor seams that Westwood blends have no edge pieces "
                     f"(Westwood's maps: at most about {lim:.0%})."))
    return out


# ---- rooms ------------------------------------------------------------------------------------------
def declared_rooms(m):
    """The design's own rooms, from <map>.rooms.json beside the map when the generator wrote one
    (kit/identity.rooms_sidecar): floor tile -> room record (number, building, kind, purpose)."""
    if getattr(m, "_declared", None) is not None: return m._declared
    m._declared = {}
    side = os.path.splitext(m.file or "")[0] + ".rooms.json"
    if m.file and os.path.exists(side):
        for rec in json.load(open(side, encoding="utf-8")):
            for x, y in rec.get("floor", []): m._declared[(x, y)] = rec
    return m._declared


def find_rooms(m, max_tiles=400, void_bounds=False):
    """Enclosed areas of 2..400 floor tiles, with their objects. A room the design declared (declared_rooms) carries
    its record as r["declared"]. rules/rooms/westwood.py reads Westwood's grandest rooms with a larger max_tiles.
    void_bounds: the void (no floor) bounds a room as a wall does, as in rules/rooms.py; Westwood's great rooms often
    end in the void (Hecubah's throne hall in Con06b, the Lich's in Con10d), and without it they never count as
    rooms. r["void_share"] is then the share of the room's edge that is void."""
    blocked = set(m.walls) | set(m.door_gaps)
    comp = {}; rooms = []
    for start in m.cover:
        if start in comp or start in blocked: continue
        cid = len(rooms); comp[start] = cid; q = [start]; cells = []; enclosed = True; void = edge = 0
        while q:
            p = q.pop(); cells.append(p)
            for dx, dy in N4:
                n = (p[0] + dx, p[1] + dy)
                if not (0 <= n[0] < GRID and 0 <= n[1] < GRID):
                    enclosed = False; continue
                if n not in m.cover:
                    void += 1; edge += 1
                    if not void_bounds: enclosed = False
                    continue
                if n in blocked: edge += 1
                if n in blocked or n in comp: continue
                comp[n] = cid; q.append(n)
        rooms.append(dict(cells=cells, enclosed=enclosed, objects=[], void_share=void / max(1, edge)))
    for o in m.objects:
        c = m.cell_of(o["x"], o["y"])
        cid = comp.get(c)
        if cid is None and c in blocked:
            # a piece set snug against a wall can have its centre in the wall's own cell (Westwood: 202 pieces of
            # floor furniture): it belongs to the room on its side of the wall, the one with the nearest cell centre
            near = [(math.hypot((n[0] + 0.5) * CELL - o["x"], (n[1] + 0.5) * CELL - o["y"]), comp[n])
                    for a in (-1, 0, 1) for b in (-1, 0, 1) for n in [(c[0] + a, c[1] + b)] if n in comp]
            if near: cid = min(near)[1]
        if cid is not None: rooms[cid]["objects"].append(o)
    out = []
    decl = declared_rooms(m)
    for r in rooms:
        r["tiles"] = sum(1 for p in r["cells"] if p in m.tiles)
        if r["enclosed"] and 2 <= r["tiles"] <= max_tiles:
            votes = collections.Counter(decl[p]["number"] for p in r["cells"] if p in decl)
            if votes:
                num, n = votes.most_common(1)[0]
                if n * 2 >= r["tiles"]:
                    r["declared"] = next(rec for rec in decl.values() if rec["number"] == num)
            r["yard"] = bool(r.get("declared", {}).get("yard"))
            out.append(r)
    return out


def indoor_rooms(m):
    """find_rooms without the yards a design declared (kit/yards.py): a graveyard or a quarry is fenced, not a room,
    and answers to none of the indoor rooms' rules."""
    return [r for r in find_rooms(m) if not r.get("yard")]


def piece_area(o):
    """Floor footprint of an object in square uv units (its collision box or circle; one uv unit is 16.26 px)."""
    if o["ext"] == "BOX": return (o["ex"] or 0) * (o["ey"] or 0) / 264.4
    return math.pi * (o["ex"] or 0) ** 2 / 264.4


def room_coverage(m, r):
    """Share of a room's floor its furniture covers (blocking furniture families; a grid cell is 2 square uv units).
    Westwood's house rooms: p50 0.10-0.14, p75 0.15-0.19 (storerooms 0.23, barracks 0.25)."""
    area = sum(piece_area(o) for o in r["objects"] if m.blocking(o) and RT.family(o["type"]) in RT.BLOCKING_FAMILIES)
    return area / (2.0 * max(1, len(r["cells"])))


def room_kind(r):
    """(kind, furniture count): the kind the design declared for the room, else the kind its furniture reads as."""
    kind, furniture = room_profile(r)
    return (r["declared"]["kind"], furniture) if r.get("declared") else (kind, furniture)


# Shelves of goods and apple crates hold supplies: a room stocked with them is a storeroom or kitchen, not a
# library or a shop (the rulebook files them under shelves and shop racks).
SUPPLY_PIECES = re.compile(r"^(LogShelves|TeepeeShelves|UrchinShelves)|^TraderAppleCrate$")


def room_profile(r):
    fam = collections.Counter("storage" if SUPPLY_PIECES.match(o["type"]) else RT.family(o["type"]) for o in r["objects"])
    fam.pop(None, None)
    npcs = {"shopkeeper": sum(1 for o in r["objects"] if RT.SHOPKEEPER.match(o["type"]))}
    kind = RT.classify(fam, npcs)
    if kind == "smithy" and not any(re.match(r"Anvil|CinderBin", o["type"]) for o in r["objects"]):
        fam.pop("smithy", None)                      # bellows alone are hearth tools, not a forge
        kind = RT.classify(fam, npcs)
    furniture = sum(n for f, n in fam.items() if f in RT.BLOCKING_FAMILIES)
    return kind, furniture


def similar_rooms(samples, tiles):
    """Westwood rooms of the kind with a similar floor area (widening until there are enough)."""
    for f in (1.6, 2.5, 4.0):
        near = [n for t, n in samples if tiles / f <= t <= tiles * f]
        if len(near) >= 6: return sorted(near)
    return sorted(n for _, n in samples)


IDENTITY_ALIASES = {"bedroom": ("dwelling",), "living_room": ("dwelling",), "storeroom": ("ore_store", "gear_store"),
                    "kitchen": ("herbalist",), "study": ("herbalist",), "dining_hall": ("mess_hall",),
                    "tavern": ("mess_hall",)}


def identity_strays(kind, objects):
    """Object types in a room that its kind's identity does not allow (blocking furniture only)."""
    import re as _re
    from kit.identity import ROOMS
    kinds = [k for k in (kind,) + IDENTITY_ALIASES.get(kind, ()) if k in ROOMS]
    if not kinds: return set()
    out = set()
    for o in objects:
        fam = RT.family(o["type"])
        if fam not in RT.BLOCKING_FAMILIES: continue
        if any(o["type"] in d for k in kinds for d in ROOMS[k].get("prefer", {}).values()):
            continue                                  # chosen by the identity itself (an anvil in a forge)
        if o["type"].startswith("Bellows") and any("fireplace" in ROOMS[k]["core"] or "fireplace" in ROOMS[k]["optional"]
                                                   for k in kinds):
            continue                                  # bellows are hearth tools: they go wherever a hearth does
        ok = False
        for k in kinds:
            ident = ROOMS[k]
            if fam in ident["core"] or fam in ident["optional"] or (fam in ("chair", "bench") and "table" in ident["core"]):
                pat = ident.get("types", {}).get(fam)
                if not pat or _re.search(pat, o["type"]): ok = True
        if not ok: out.add(o["type"])
    return out


def check_rooms(m, ctx, base):
    """Room size and furniture count against Westwood's rooms of the same kind and similar size."""
    out = []
    kinds = base.get("room_kinds", {})
    from kit.identity import WESTWOOD_KIND
    for r in indoor_rooms(m):
        kind, furniture = room_kind(r)
        wkind = WESTWOOD_KIND.get(kind, kind)
        k = kinds.get(wkind)
        if not k or k["n"] < 4 or "samples" not in k or kind in ("other", "empty"): continue
        x, y = centre(r["cells"])
        near = similar_rooms(k["samples"], r["tiles"])
        hi = near[min(len(near) - 1, int(0.95 * len(near)))]
        lo = near[int(0.05 * len(near))]
        if r.get("declared"):
            # a generated room is furnished fuller than Westwood's (TreePlace room reviews), up to the share of its
            # floor its kind may cover (kit/identity.py ROOM_COVER); counts would call a wall of shelves clutter
            from kit.identity import ROOM_COVER, ROOM_COVER_DEFAULT
            cover, cmax = room_coverage(m, r), ROOM_COVER.get(kind, ROOM_COVER_DEFAULT)[1]
            if cover > cmax:
                out.append(F("rooms", "warning", f"{kind} room ({r['tiles']} tiles) is crammed: furniture covers "
                             f"{100 * cover:.0f}% of its floor (at most {100 * cmax:.0f}% for its kind).", x, y))
        elif furniture > max(hi, 2):
            out.append(F("rooms", "warning", f"{kind} room ({r['tiles']} tiles) holds {furniture} pieces of furniture; "
                         f"Westwood's {wkind} rooms of a similar size hold at most about {hi}.", x, y))
        elif furniture < lo and furniture < 2:
            out.append(F("rooms", "warning", f"{kind} room ({r['tiles']} tiles) is nearly bare ({furniture} pieces); "
                         f"Westwood's of a similar size hold at least {lo}.", x, y))
        # identity: furniture that has no place in this kind of room (a barrel in a bedroom)
        # (a generated room only: Westwood's rooms, read by their furniture, answer to no identity of ours; calibrate:
        # 471 findings on 87 of its 120 maps)
        stray = identity_strays(kind, r["objects"]) if r.get("declared") else set()
        if stray:
            out.append(F("rooms", "warning", f"{kind} room holds {', '.join(sorted(stray))}, which "
                         f"{'does' if len(stray) == 1 else 'do'} not belong in a {kind.replace('_', ' ')} "
                         f"(room identities: mapgen/kit/identity.py).", x, y))
        tlo, thi = k["tiles"]
        if r["tiles"] < tlo:
            out.append(F("rooms", "warning", f"{kind} room is small for its kind: {r['tiles']} tiles "
                         f"(Westwood's: {tlo:.0f} to {thi:.0f}).", x, y))
        elif r["tiles"] > thi and not r.get("declared"):      # generated buildings are larger than Westwood's by design
            out.append(F("rooms", "warning", f"{kind} room is large for its kind: {r['tiles']} tiles "
                         f"(Westwood's: {tlo:.0f} to {thi:.0f}).", x, y))
    return out


# ---- map-wide measurements ------------------------------------------------------------------------------
def metrics(m, ctx):
    import decoration as D
    n_tiles = max(1, len(m.tiles))
    per100 = lambda n: round(100 * n / n_tiles, 2)
    lights = sum(1 for o in m.objects if LIGHT_NAME.search(o["type"]) or "FIRE" in o["cls"])
    colorlights = sum(1 for o in m.objects if o["type"] == "ColorLight")
    decor = 0
    for o in m.objects:
        cat = D.classify({"type": o["type"], "class": o["cls"], "xtype": o["xtype"]})
        if cat in D.STYLE_CATS: decor += 1
    creatures = sum(1 for o in m.objects if "MONSTER" in o["cls"])
    seams = edged = 0
    for (x, y), t in m.tiles.items():
        for d in ((1, -1), (1, 1)):
            n = (x + d[0], y + d[1])
            if n in m.tiles and m.tiles[n]["material"] != t["material"]:
                seams += 1; edged += edge_between(m, (x, y), n)
    # crowded transitions: a tile where three or more floor materials meet (itself and its sides)
    junctions = sum(1 for (x, y), t in m.tiles.items()
                    if len({t["material"]} | {m.tiles[(x + a, y + b)]["material"] for a, b in ((1, -1), (1, 1), (-1, 1), (-1, -1))
                                              if (x + a, y + b) in m.tiles}) >= 3)
    return dict(tiles=n_tiles, walls=len(m.walls), objects=len(m.objects), junctions_per100=per100(junctions),
                lights_per100=per100(lights), colorlights_per100=per100(colorlights), decor_per100=per100(decor),
                creatures_per100=per100(creatures), edge_coverage=round(edged / seams, 3) if seams else None,
                walls_per100=per100(len(m.walls)))


def environment(m):
    """The map's environment type: declared in its description as [env:town], else classified the
    same way as Westwood's maps (rules/environments.py)."""
    mt = re.search(r"\[env:(\w+)\]", m.info.get("description") or "")
    if mt: return mt.group(1)
    import environments as E
    return E.classify(E.features(m))


def check_density(m, ctx, base):
    out = []
    env = environment(m)
    ranges = base.get("metrics_by_env", {}).get(env) or base.get("metrics", {})
    mt = metrics(m, ctx)
    names = dict(lights_per100="lights per 100 floor tiles", colorlights_per100="coloured lights per 100 floor tiles",
                 decor_per100="decorations per 100 floor tiles", edge_coverage="share of floor seams with edge pieces",
                 creatures_per100="creatures per 100 floor tiles", walls_per100="wall pieces per 100 floor tiles",
                 junctions_per100="crowded floor junctions (3+ materials meeting) per 100 floor tiles")
    for k, label in names.items():
        v, r = mt.get(k), ranges.get(k)
        if v is None or not r: continue
        if v < r["p5"]:
            out.append(F("density", "warning", f"Few {label}: {v} (Westwood's {env} maps: {r['p5']} to {r['p95']}, typical {r['p50']})."))
        elif v > r["p95"]:
            out.append(F("density", "warning", f"Many {label}: {v} (Westwood's {env} maps: {r['p5']} to {r['p95']}, typical {r['p50']})."))
    out.append(F("density", "info", f"Environment: {env} (compared with Westwood's {env} maps)."))
    out.append(F("density", "info", "Measurements: " + ", ".join(f"{k}={v}" for k, v in mt.items()), metrics=mt))
    return out


# ---- composition: how pieces relate to what is around them ------------------------------------------
DOCK_DIR = {"DockDown": (1, 1), "DockUp": (-1, 1)}       # world-px direction a dock kit runs out over water
BAR_RE = re.compile(r"^(BarPiece|BarCorner|BarHingedTop)")
VISIBLE_LIGHT = re.compile(r"Candleabra|Candelabra|Lantern|Torch|Sconse|Sconce|Lamp|Brazier|Chandelier")


def check_composition(m, ctx, base):
    """Pieces that make no sense where they stand (the DysVale v0.4 playtest):
    - a dock with no open water past its tip (spanning a puddle to the far bank);
    - lights of one room standing side by side;
    - a path that ends at a building wall with no door;
    - a bar counter that stops short of the wall it runs toward."""
    out = []
    water = {t for t, d in m.tiles.items() if WATER_RE.search(d["material"])}

    def tile_of(x, y):
        return m.tile_at_cell(m.cell_of(x, y))

    # docks: the tip piece must have water beyond it
    chains = []
    for kit, fronts, _ in kit_pieces(m):
        if kit not in DOCK_DIR: continue
        left = list(fronts)
        while left:                                    # one chain = pieces within 120 px of each other
            chain = [left.pop()]
            grew = True
            while grew:
                grew = False
                for o in list(left):
                    if any(math.hypot(o["x"] - c["x"], o["y"] - c["y"]) < 120 for c in chain):
                        chain.append(o); left.remove(o); grew = True
            chains.append((kit, chain))
    for kit, fronts in chains:
        dx, dy = DOCK_DIR[kit]
        L = math.hypot(dx, dy)
        tip = max(fronts, key=lambda o: o["x"] * dx + o["y"] * dy)
        open_water = 0
        for k in range(1, 5):                              # 4 tiles past the tip (32 px each)
            t = tile_of(tip["x"] + dx / L * 32 * k, tip["y"] + dy / L * 32 * k)
            if t in water: open_water += 1
            else: break
        if open_water < base.get("dock_open_tiles", 2):
            out.append(F("composition", "warning", f"{kit} dock ends {open_water} tile(s) from the far bank: a dock "
                         f"reaches out into open water, it does not span a pond.", tip["x"], tip["y"]))

    # lights side by side in a room
    gap = base.get("light_gap_px", 30)
    for r in find_rooms(m):
        lights = [o for o in r["objects"] if VISIBLE_LIGHT.search(o["type"]) and "ColorLight" not in o["type"]]
        for i, a in enumerate(lights):
            for b in lights[i + 1:]:
                if math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < gap:
                    out.append(F("composition", "warning", f"{a['type']} and {b['type']} stand side by side in one room; "
                                 f"spread lights to different corners.", (a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2))

    # bar counters that stop short of a wall
    bars = [o for o in m.objects if BAR_RE.match(o["type"])]
    uv = lambda o: ((o["x"] + o["y"]) / CELL, (o["x"] - o["y"]) / CELL)
    slash, back = collections.defaultdict(list), collections.defaultdict(list)
    for (x, y), w in m.walls.items():
        if w.invisible: continue
        slash[x + y + 1].append(x - y); back[x - y].append(x + y + 1)
    for o in bars:
        if not o["type"].startswith("BarPiece"): continue
        u, v = uv(o)
        along_u = o["type"][8] in "24"
        nb = [p for p in bars if p is not o and (
            (abs(uv(p)[1] - v) < 0.6 and 1.2 < abs(uv(p)[0] - u) < 2.8) if along_u else
            (abs(uv(p)[0] - u) < 0.6 and 1.2 < abs(uv(p)[1] - v) < 2.8))]
        if len(nb) != 1: continue                          # only run ends
        d = 1 if (uv(nb[0])[0] < u if along_u else uv(nb[0])[1] < v) else -1
        if along_u:
            dist = [abs(U - u) for U, vs in slash.items() if (U - u) * d > 0 and abs(U - u) < 6 and any(abs(V - v) < 1.6 for V in vs)]
        else:
            dist = [abs(V - v) for V, us in back.items() if (V - v) * d > 0 and abs(V - v) < 6 and any(abs(U - u) < 1.6 for U in us)]
        if dist and 1.6 < min(dist) < 4.5:
            out.append(F("composition", "warning", f"The bar counter stops {min(dist) * 16:.0f} px short of the wall: "
                         f"a bar run meets the wall.", o["x"], o["y"]))

    out += check_room_composition(m, ctx, base)

    # paths that end at a building wall with no door
    import design as DS
    od = DS.Outdoor(m)
    room_walls, room_floor = set(), {}
    for r in find_rooms(m):
        walls_here = {(x + a, y + b) for x, y in r["cells"] for a, b in N4 if (x + a, y + b) in m.walls
                      and m.walls[(x + a, y + b)].opaque and not NATURAL_WALL.search(m.walls[(x + a, y + b)].material)}
        room_walls |= walls_here
        mats = collections.Counter(m.tiles[c]["material"] for c in r["cells"] if c in m.tiles)
        if mats:
            for w in walls_here: room_floor[w] = mats.most_common(1)[0][0]
    doors = [d["gap"] for d in m.doors]
    SIDES = ((1, 1), (1, -1), (-1, 1), (-1, -1))
    # only paths that belong to a road network (25+ connected tiles), not paved patches by a hearth
    network, left = set(), set(od.paths)
    while left:
        st = left.pop(); comp = {st}; q = [st]
        while q:
            a = q.pop()
            for dx, dy in SIDES:
                n = (a[0] + dx, a[1] + dy)
                if n in left: left.remove(n); comp.add(n); q.append(n)
        if len(comp) >= 25: network |= comp
    for (x, y) in network:
        if (x + 1, y + 1) in m.walls: continue             # a building's own floor, half under its wall
        nb = [(x + a, y + b) for a, b in SIDES if (x + a, y + b) in od.paths]
        if len(nb) != 1: continue                          # not the end of a path
        # only thin paths (one tile wide, like a doorstep path); wide paved areas meet walls by design
        n2 = nb[0]
        if sum((n2[0] + a, n2[1] + b) in od.paths for a, b in SIDES) > 2: continue
        if any((x + a, y + b) in od.paths for a, b in ((2, 0), (-2, 0), (0, 2), (0, -2))
               if (x + a, y + b) != (n2[0] + (n2[0] - x), n2[1] + (n2[1] - y))): continue
        # a spur: walk back along the thin path to where it joins the network; doorstep paths are short
        prev, cur, length = (x, y), n2, 1
        while length <= 9:
            nxt = [(cur[0] + a, cur[1] + b) for a, b in SIDES if (cur[0] + a, cur[1] + b) in network and (cur[0] + a, cur[1] + b) != prev]
            if len(nxt) != 1: break
            prev, cur, length = cur, nxt[0], length + 1
        if length > 8: continue
        near = [(x + a, y + b) for a in range(-1, 3) for b in range(-1, 3) if (x + a, y + b) in room_walls]
        if any(room_floor.get(w) == m.tiles[(x, y)]["material"] for w in near): continue   # the room's own floor
        near_wall = bool(near)
        near_door = any(abs(gx - x) <= 3 and abs(gy - y) <= 3 for gx, gy in doors)
        if near_wall and not near_door:
            out.append(F("composition", "warning", "A path ends at a building wall with no door; paths lead to doors.",
                         (x + 1) * CELL, (y + 1) * CELL))
    return out


# ---- room composition and bridge landings (DysVale v0.5 playtest) ----------------------------------------
# pieces that need the space in front of them (a chest to open, a hearth or stove to tend); Westwood puts
# reading tables before bookcases, so shelves are not included
NEEDS_FRONT = re.compile(r"^Chest\d|^Chest[NS][EW]$|^DunMirChest|Fireplace|^Stove|^Cauldron|^CinderBin")
FRONT_BLOCKERS = {"table", "desk", "bed", "counter_bar", "counter_shop", "stove", "shelves", "chair", "bench"}
FLOOR_LIGHT = re.compile(r"Candleabra|Candelabra|^TorchPole|Lantern\d$")
PLANK = re.compile(r"^WoodSlatFloor")


def room_runs(m, cells):
    """Straight wall runs around a room: (line, coord) -> (lo, hi) along the run, in uv units."""
    near = {(x + a, y + b) for x, y in cells for a, b in N4} & set(m.walls)
    runs = collections.defaultdict(list)
    for (x, y) in near:
        w = m.walls[(x, y)]
        for line, nbs, f in (("/", ((1, -1), (-1, 1)), 0), ("\\", ((1, 1), (-1, -1)), 1)):
            if any((x + a, y + b) in m.walls for a, b in nbs) or w.facing == f:
                runs[(line, x + y + 1 if line == "/" else x - y)].append(x - y if line == "/" else x + y + 1)
    return {k: (min(v) - 1, max(v) + 1) for k, v in runs.items() if len(v) >= 2}


def uv_of(o):
    return (o["x"] + o["y"]) / CELL, (o["x"] - o["y"]) / CELL


def furniture_offset(m, r):
    """How far a room's furniture sits from the room's middle, relative to its size (None for rooms
    with fewer than 5 pieces): Westwood's rooms: median 0.35, 90% under 0.70."""
    cells = r["cells"]
    furn = [o for o in r["objects"] if m.blocking(o) and RT.family(o["type"]) in RT.BLOCKING_FAMILIES]
    if len(furn) < 5: return None, 0, 0
    cu = sum(x + y + 1 for x, y in cells) / len(cells); cv = sum(x - y for x, y in cells) / len(cells)
    fu = sum(uv_of(o)[0] for o in furn) / len(furn); fv = sum(uv_of(o)[1] for o in furn) / len(furn)
    return math.hypot(fu - cu, fv - cv) / (math.sqrt(len(cells)) / 1.4), fu, fv


def check_room_composition(m, ctx, base):
    """How a room's pieces relate: the space before a chest, hearth, shelf or stove stays clear (the
    chest behind a table and a lamp); chairs stand at a table; furniture is not bunched into one part
    of the room."""
    out = []
    lim = base.get("furniture_offset_p95", 0.85)
    for r in indoor_rooms(m):
        cells = r["cells"]
        cu = sum(x + y + 1 for x, y in cells) / len(cells); cv = sum(x - y for x, y in cells) / len(cells)
        runs = room_runs(m, cells)
        objs = r["objects"]
        blockers = [o for o in objs if m.blocking(o) and (RT.family(o["type"]) in FRONT_BLOCKERS or FLOOR_LIGHT.search(o["type"]))]
        for o in objs:
            if not NEEDS_FRONT.search(o["type"]): continue
            u, v = uv_of(o)
            best = None
            for (line, coord), (lo, hi) in runs.items():
                perp = abs(u - coord) if line == "/" else abs(v - coord)
                along = v if line == "/" else u
                if perp <= 2.8 and lo - 0.5 <= along <= hi + 0.5 and (best is None or perp < best[0]):
                    best = (perp, line, coord)
            if not best: continue
            _, line, coord = best
            sgn = (1 if cu > coord else -1) if line == "/" else (1 if cv > coord else -1)
            ha = max(0.8, m.radius(o) / 16.26) + 0.3          # half its width along the wall, plus a little
            a0 = v if line == "/" else u
            p0 = u if line == "/" else v
            for p in blockers:
                if p is o: continue
                pu, pv = uv_of(p)
                pa, pp = (pv, pu) if line == "/" else (pu, pv)
                depth = (pp - p0) * sgn                          # how far into the room, in front of the piece
                if abs(pa - a0) <= ha and 0.4 <= depth <= 2.6:
                    out.append(F("composition", "warning", f"{p['type']} stands right in front of {o['type']}: keep the "
                                 f"space before it clear.", p["x"], p["y"]))
                    break
        for o in objs:                                # chests, bookcases and desks lie along their wall
            if not FRONTED.search(o["type"]) or o["ext"] != "BOX": continue
            ex, ey = o["ex"] or 0, o["ey"] or 0
            if min(ex, ey) <= 0 or max(ex, ey) / min(ex, ey) < 1.5: continue
            u, v = uv_of(o)
            near = []
            for (line, coord), (lo, hi) in runs.items():
                perp = abs(u - coord) if line == "/" else abs(v - coord)
                along = v if line == "/" else u
                if lo - 0.5 <= along <= hi + 0.5: near.append((perp, line))
            if not near: continue
            reach = max(ex, ey) / 2 / 16.26 + 0.9
            if not any(pp <= reach for pp, _ in near): continue        # not against a wall
            long_along_v = ey > ex                                     # '/' walls run along v
            # near a corner the end wall can be the closer one: its back is against the wall it lies along
            if not any(long_along_v == (ln == "/") and pp <= reach + 0.6 for pp, ln in near):
                out.append(F("composition", "warning", f"{o['type']} stands across the wall instead of with its back "
                             f"against it.", o["x"], o["y"]))
        chairs = [o for o in objs if RT.family(o["type"]) == "chair"]
        tables = [o for o in objs if RT.family(o["type"]) in ("table", "desk", "counter_bar", "counter_shop") or
                  re.search(r"FirePit|^FreestandingFireplace", o["type"])]     # stools ring an ogre's fire pit too
        if len(chairs) >= 2 and not any(math.hypot(c["x"] - t["x"], c["y"] - t["y"]) < 70 for c in chairs for t in tables):
            out.append(F("composition", "warning", f"{len(chairs)} chairs and no table to sit at.", chairs[0]["x"], chairs[0]["y"]))
        off, fu, fv = furniture_offset(m, r)
        if off is not None:
            if off > lim:
                x, y = (fu + fv) / 2 * CELL, (fu - fv) / 2 * CELL
                out.append(F("composition", "warning", f"The furniture is bunched into one part of the room (offset {off:.2f}; "
                             f"Westwood's rooms stay under about {lim:.2f}).", x, y))
    out += bridge_landings(m)
    out += bunched_props(m, base)
    out += bridge_squareness(m)
    out += room_arrangement(m)
    out += room_ways(m)
    out += building_doors(m)
    return out


# ---- a room laid out as a whole (TreePlace v0.1 playtest) ---------------------------------------------------
HOUSE_WALL = re.compile(r"^(Log|Stucco|Brick|StoneGray|StoneBlue|Galava|Cobblestone|FieldStone|Dilapidated)")
OPEN_TORCH = re.compile(r"^(Torch|TorchPole|TorchPoleImmobile)$")
FOOD_ITEM = re.compile(r"^(Meat|Bread|RedApple|Apple|Cider|Cheese|Ham|Drumstick|Mead|Wine|Soup|Pie|Cake|Fish|Grapes|Watermelon)$")
DINING_TABLE = re.compile(r"^(Table\d|RoundTable\d|SquareTable\d|OvalTable\d|RoundTableWithFood|SmallTable\d)$")
SEATED_ROOMS = {"dining_hall", "tavern", "barracks"}      # rooms whose tables are for sitting at
SPREAD_MIN = 0.35   # share of a room's length its furniture spans; Westwood's rooms of 40+ tiles: p5 0.24, p10 0.45
BED_GAP_MIN = 0.9   # units between neighbouring beds; Westwood's rooms with 3+ beds: never under 0.92
HEARTH_GAP_MIN = 0.6   # units between a cauldron or stove and a fireplace; Westwood: never under 0.87
TABLE = re.compile(r"^(Table\d|RoundTable\d|SquareTable\d|OvalTable\d|RoundTableWithFood|SmallTable\d)$")


def _lines_of(coords, tol=1.2):
    """How many straight lines sorted coordinates fall into (a gap over `tol` starts a new one)."""
    return 1 + sum(1 for a, b in zip(coords, coords[1:]) if b - a > tol)


def _half_uv(o):
    if o["ext"] == "BOX": return (o["ex"] or 0) / 2 / 16.26, (o["ey"] or 0) / 2 / 16.26
    return (o["ex"] or 0) / 16.26, (o["ex"] or 0) / 16.26


def room_arrangement(m):
    """Whether a room is laid out as a whole, from the TreePlace v0.1 playtest. Westwood never does the
    first four (0 cases on its 107 campaign maps):
    - food lying by a table (Nox draws items at floor level: it reads as dropped);
    - a long table seated only at its ends (75% of Westwood's chairs at long tables stand along the sides);
    - a bunk room of mixed bed kinds;
    - beds scattered instead of lined up (3 of Westwood's 14 rooms with 3+ beds).
    Also checked:
    - a table with no seats in a room for sitting and eating (dining hall, tavern, barracks);
    - furniture filling only one end of a room;
    - open torches inside a house. This is the user's house rule; Westwood does it in 35 rooms."""
    out = []
    for r in indoor_rooms(m):
        objs, cells = r["objects"], r["cells"]
        kind, _ = room_kind(r)
        x0, y0 = centre(cells)
        mats = collections.Counter()
        for (x, y) in cells:
            for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                w = m.walls.get((x + a, y + b))
                if w and not w.invisible: mats[w.material] += 1
        mat = mats.most_common(1)[0][0] if mats else ""
        torches = [o for o in objs if OPEN_TORCH.match(o["type"])]
        if torches and HOUSE_WALL.match(mat):
            out.append(F("composition", "warning", f"{len(torches)} open torch{'es' if len(torches) > 1 else ''} inside a "
                         f"house ({mat} walls): light houses with candelabras and a hearth (house rule from the TreePlace "
                         f"playtest; Westwood does it in 35 rooms).", torches[0]["x"], torches[0]["y"]))
        tables = [o for o in objs if DINING_TABLE.match(o["type"])]
        seats = [o for o in objs if RT.family(o["type"]) in ("chair", "bench")]
        for f in objs:
            if not FOOD_ITEM.match(f["type"]): continue
            fu, fv = uv_of(f)
            t = next((t for t in tables if abs(fu - uv_of(t)[0]) <= _half_uv(t)[0] + 1.2 and
                      abs(fv - uv_of(t)[1]) <= _half_uv(t)[1] + 1.2), None)
            if t:
                out.append(F("composition", "warning", f"{f['type']} lies by {t['type']}: Nox draws items at floor level, so "
                             f"food set on a table reads as dropped on the floor (use RoundTableWithFood).", f["x"], f["y"]))
        for t in tables:
            hu, hv = _half_uv(t); tu, tv = uv_of(t)
            near = [s for s in seats if abs(uv_of(s)[0] - tu) <= hu + 1.8 and abs(uv_of(s)[1] - tv) <= hv + 1.8]
            if not near:
                if kind in SEATED_ROOMS:
                    out.append(F("composition", "warning", f"{t['type']} has no seats, in a room for sitting at tables "
                                 f"({kind.replace('_', ' ')}).", t["x"], t["y"]))
                continue
            if abs(hu - hv) >= 0.3 and len(near) >= 2:
                hl, hs = max(hu, hv), min(hu, hv)
                ends = sum(1 for s in near if abs((uv_of(s)[0] - tu) if hu > hv else (uv_of(s)[1] - tv)) > hl and
                           abs((uv_of(s)[1] - tv) if hu > hv else (uv_of(s)[0] - tu)) < hs + 0.4)
                if ends == len(near):
                    out.append(F("composition", "warning", f"{t['type']} is seated only at its ends: seat a long table along "
                                 f"its sides (Westwood: 75% of the chairs at its long tables).", t["x"], t["y"]))
        beds = [o for o in objs if RT.family(o["type"]) == "bed"]
        if len(beds) >= 3:
            stems = sorted({re.sub(r"\d+$", "", b["type"]) for b in beds})
            us = [uv_of(b)[0] for b in beds]; vs = [uv_of(b)[1] for b in beds]
            if len(stems) > 1:
                out.append(F("composition", "warning", f"{len(beds)} beds of {len(stems)} kinds ({', '.join(stems)}): a bunk "
                             f"room uses one kind (all of Westwood's rooms with 3 or more beds do).", x0, y0))
            elif not any(_lines_of(sorted(c)) <= 2 for c in (us, vs)):        # one row, or two facing rows
                out.append(F("composition", "warning", f"{len(beds)} beds scattered about the room: line them up side by "
                             f"side along one wall.", x0, y0))
        furn = [o for o in objs if m.blocking(o) and RT.family(o["type"]) in RT.BLOCKING_FAMILIES]
        if len(furn) >= 4 and r["tiles"] >= 40:
            cu_ = [x + y + 1 for x, y in cells]; cv_ = [x - y for x, y in cells]
            long_u = (max(cu_) - min(cu_)) >= (max(cv_) - min(cv_))
            L = (max(cu_) - min(cu_)) if long_u else (max(cv_) - min(cv_))
            fp = sorted((uv_of(o)[0] if long_u else uv_of(o)[1]) for o in furn)
            if L >= 10 and (fp[-1] - fp[0]) / L < SPREAD_MIN:
                out.append(F("composition", "warning", f"The furniture fills only {100 * (fp[-1] - fp[0]) / L:.0f}% of the "
                             f"room's length and the rest stands empty: spread it through the room.", x0, y0))
        # TreePlace v0.2 room review
        if len(beds) >= 3:                                         # bunks packed side by side
            for b in beds:
                bu, bv = uv_of(b); hu, hv = _half_uv(b)
                for o in beds:
                    if o is b: continue
                    ou, ov = uv_of(o); ohu, ohv = _half_uv(o)
                    gu, gv = abs(ou - bu) - hu - ohu, abs(ov - bv) - hv - ohv
                    gap = gv if gu < 0.5 else gu if gv < 0.5 else None
                    if gap is not None and -0.5 <= gap < BED_GAP_MIN:
                        out.append(F("composition", "warning", f"{b['type']} stands {max(gap, 0):.1f} units from the next bed: "
                                     f"space the beds out (Westwood leaves at least {BED_GAP_MIN} between them).", b["x"], b["y"]))
                        break
                else:
                    continue
                break
        hearths = [o for o in objs if "Fireplace" in o["type"]]
        for s in (o for o in objs if re.match(r"^(Cauldron|Stove)", o["type"])):
            su, sv = uv_of(s); shu, shv = _half_uv(s)
            for f in hearths:
                fu, fv = uv_of(f); fhu, fhv = _half_uv(f)
                gap = max(abs(su - fu) - shu - fhu, abs(sv - fv) - shv - fhv)
                if gap < HEARTH_GAP_MIN:
                    out.append(F("composition", "warning", f"{s['type']} crowds {f['type']} ({max(gap, 0):.1f} units apart): give the "
                                 f"hearth room (Westwood: at least 0.87).", s["x"], s["y"]))
        for g_ in (o for o in objs if RT.family(o["type"]) == "rug"):
            gu, gv = uv_of(g_); ghu, ghv = _half_uv(g_)
            for t in (o for o in objs if TABLE.match(o["type"])):
                tu, tv = uv_of(t); thu, thv = _half_uv(t)
                ou = min(gu + ghu, tu + thu) - max(gu - ghu, tu - thu); ov = min(gv + ghv, tv + thv) - max(gv - ghv, tv - thv)
                inside = tu - thu >= gu - ghu - 0.05 and tu + thu <= gu + ghu + 0.05 and \
                    tv - thv >= gv - ghv - 0.05 and tv + thv <= gv + ghv + 0.05
                if ou > 0.05 and ov > 0.05 and not inside:
                    out.append(F("composition", "warning", f"{t['type']} stands half on {g_['type']}: centre the table on its rug "
                                 f"or keep it off (house rule from the TreePlace room review).", t["x"], t["y"]))
        if r.get("declared"):                                      # generated rooms: at least as full as Westwood's median
            from kit.identity import WESTWOOD_KIND
            k = _room_baseline().get(WESTWOOD_KIND.get(kind, kind))
            band = "coverage_large" if r["tiles"] >= 50 and (k or {}).get("coverage_large") else "coverage"
            med = ((k or {}).get(band) or {}).get("p50")       # against Westwood's rooms of its size (50+ tiles: large)
            cover = room_coverage(m, r)
            if med and cover < med:
                out.append(F("composition", "warning", f"{kind.replace('_', ' ')} room ({r['tiles']} tiles) is sparse: furniture "
                             f"covers {100 * cover:.0f}% of its floor, less than half of Westwood's rooms of its kind "
                             f"({100 * med:.0f}%) (house rule from the TreePlace room review: rooms at Westwood's median and "
                             f"below read as empty).", x0, y0))
        out += wall_side_rules(m, r)
    return out


# ---- what the camera sees (TreePlace v0.3 room review) --------------------------------------------------------------
# The user's frame of reference: the NE wall is the top right of a room on screen, the NW wall the top left, the SE
# wall the bottom right and the SW wall the bottom left. The camera sees the front of what stands against the NE and
# NW walls and only the back of what stands against the SE and SW walls, or nothing where the wall hides it.
FACING_PIECE = re.compile(r"^(Bookcase\d|PotionShelves\d|LogShelves(Full|Empty)\d|TraderShelves\d|TraderHelmShelf\d|Desk\d|"
                          r"Fireplace\d|WallFireplace\d|Stove0\d|Chest\d|Chest[NS][EW]|DunMirChest\d)")
SHELF_PIECE = re.compile(r"^(Bookcase\d|PotionShelves\d|LogShelves(Full|Empty)\d|TraderShelves\d)")
FLOAT_MIN, FLOAT_MAX = 0.9, 3.0    # a chest, shelf or desk this many units off its wall floats in the room


def _wall_name(line, coord, cu, cv):
    if line == "/": return "NW" if cu > coord else "SE"
    return "SW" if cv > coord else "NE"


def _against(o, runs, cu, cv, m, reach=1.4, across=False, prefer_back=False):
    """(wall name, gap from the wall line to the piece's back, along, line, coord) of the wall run a piece stands
    against (its back within `reach` units of the line), or None. A long piece lying across a wall (a bed with its head
    to it) counts only `across`."""
    u, v = uv_of(o)
    hu, hv = _half_uv(o)
    long_box = o["ext"] == "BOX" and max(hu, hv) >= 1.3 * min(hu, hv) > 0
    best = None
    for (line, coord), (lo, hi) in runs.items():
        perp = abs(u - coord) if line == "/" else abs(v - coord)
        along = v if line == "/" else u
        depth = hu if line == "/" else hv
        if not (lo - 0.5 <= along <= hi + 0.5): continue
        if long_box and not across and depth > (hv if line == "/" else hu): continue   # it lies across this wall
        gap = perp - depth
        if gap > reach: continue
        name = _wall_name(line, coord, cu, cv)
        # a piece tight in a corner touches both walls (2026-10-04: shelves fit tight into corners): its back is to
        # the NE or NW wall it was set against, not to the front wall across the corner
        key = (name not in ("NE", "NW"), gap) if prefer_back else (gap,)
        if best is None or key < best[0]:
            best = (key, (name, gap, along, line, coord))
    return best and best[1]


def _in_row(o, objs):
    """True if a shelf or rack is one of a row of its kind standing end to end (library stacks, rows of racks down the
    middle of a storeroom), which stands free on purpose."""
    u, v = uv_of(o)
    hu, hv = _half_uv(o)
    along_u = hu >= hv
    for p in objs:
        if p is o or not SHELF_PIECE.match(p["type"]) and not p["type"].startswith("Trader"): continue
        pu, pv = uv_of(p)
        phu, phv = _half_uv(p)
        if along_u and abs(pv - v) < 0.3 and abs(pu - u) <= hu + phu + 0.6: return True
        if not along_u and abs(pu - u) < 0.3 and abs(pv - v) <= hv + phv + 0.6: return True
    return False


def wall_side_rules(m, r):
    """House rules from the TreePlace v0.3 room review:
    - pieces with a face (shelves, desks, hearths, stoves, chests, hangings) stand against the NE or NW wall, never
      the SE or SW wall, where the camera sees only their back;
    - shelves line a wall end to end: two shelves against one wall with bare wall between them are scattered;
    - a chest, shelf or desk stands against its wall, not 0.9 to 3 units off it in the room."""
    out = []
    cells, objs = r["cells"], r["objects"]
    cu = sum(x + y + 1 for x, y in cells) / len(cells); cv = sum(x - y for x, y in cells) / len(cells)
    runs = room_runs(m, cells)
    beds = [o for o in objs if RT.family(o["type"]) == "bed"]
    lines = collections.defaultdict(list)          # (line, coord) -> [(along0, along1, is_shelf, object)]
    for o in objs:
        decor = RT.family(o["type"]) == "wall_decor"
        if not (FACING_PIECE.match(o["type"]) or decor or (m.blocking(o) and RT.family(o["type"]) in RT.BLOCKING_FAMILIES)):
            continue
        hit = _against(o, runs, cu, cv, m, reach=1.6 if decor else 1.4, prefer_back=True)
        if hit:
            name, gap, along, line, coord = hit
            ha = _half_uv(o)[1] if line == "/" else _half_uv(o)[0]
            lines[(line, coord)].append((along - ha, along + ha, bool(SHELF_PIECE.match(o["type"])), o))
            if (FACING_PIECE.match(o["type"]) or decor) and name in ("SE", "SW"):
                out.append(F("composition", "warning", f"{o['type']} stands against the {name} wall, where the camera sees only "
                             f"its back: shelves, hangings and other pieces with a face go on the NE and NW walls (house "
                             f"rule from the TreePlace v0.3 room review).", o["x"], o["y"]))
        elif re.match(r"Chest\d|Bookcase|Shelves|^Desk\d", o["type"]) and o["ext"] == "BOX" and not _in_row(o, objs):
            far = _against(o, runs, cu, cv, m, reach=FLOAT_MAX)
            if far and far[1] >= FLOAT_MIN and not any(math.hypot(b["x"] - o["x"], b["y"] - o["y"]) < 60 for b in beds):
                out.append(F("composition", "warning", f"{o['type']} stands {far[1]:.1f} units off the {far[0]} wall, alone in "
                             f"the room: set it against the wall (house rule from the TreePlace v0.3 room review).",
                             o["x"], o["y"]))
    # what stands at each wall, a bed with its head to it too: wall between two shelves that a bed or a desk fills is
    # not bare
    at_wall = collections.defaultdict(list)
    for o in objs:
        if not (m.blocking(o) and RT.family(o["type"]) in RT.BLOCKING_FAMILIES): continue
        hit = _against(o, runs, cu, cv, m, reach=1.4, across=True)
        if hit:
            ha = _half_uv(o)[1] if hit[3] == "/" else _half_uv(o)[0]
            at_wall[(hit[3], hit[4])].append((hit[2] - ha, hit[2] + ha))
    doors = [(d["gap"][0] + d["gap"][1] + 1, d["gap"][0] - d["gap"][1]) for d in m.doors]
    for (line, coord), items in lines.items():
        items.sort(key=lambda it: it[0])
        for (a0, a1, s1, o1), (b0, b1, s2, o2) in zip(items, items[1:]):
            if not (s1 and s2) or _bare(a1, b0, at_wall[(line, coord)]) <= 1.0: continue
            between = [dd for dd in doors if abs((dd[0] if line == "/" else dd[1]) - coord) < 1.6 and
                       a1 < (dd[1] if line == "/" else dd[0]) < b0]
            if between: continue
            out.append(F("composition", "warning", f"{o1['type']} and {o2['type']} stand {b0 - a1:.1f} units apart on the "
                         f"{_wall_name(line, coord, cu, cv)} wall with bare wall between them: line shelves end to end "
                         f"(house rule from the TreePlace v0.3 room review).", o2["x"], o2["y"]))
    return out


# ---- the way in and the way pieces face (2026-10-05 playtest, Greywatch's keep: "The pillars are in the dead center of
# the room, making walking straight in through the door impossible. There are also two statues that mysteriously face
# directly against the wall.") --------------------------------------------------------------------------------------
DOOR_WAY_HALF = 1.0     # half the width of the straight way in from a door (a door's opening is about 2 units)
DOOR_WAY_DEPTH = 4.0    # how far into the room it runs (at most 0.4 of the room's depth that way)
DOOR_WAY_FAR = 12.0     # columns and statues keep out of it further in (at most 3/4 of the room's depth that way): a
                        # pillar in line with the door blocks the walk in and the view down the hall
TALL_IN_WAY = {"column", "statue"}
# Statues by the way they face, as Westwood stands them (corpus: a statue with its back to one wall, Statue2a 35 of 50 at
# the NW wall, 2c 39 of 55 at the SW, 2e 49 of 73 at the SE, 2g 48 of 58 at the NE): a faces SE (+u), c NE (+v), e NW
# (-u), g SW (-v)
STATUE_FACING = {"a": (1, 0), "c": (0, 1), "e": (-1, 0), "g": (0, -1)}
STATUE = re.compile(r"^Statue[12]([a-h])$")
FACE_WALL_MAX = 3.0     # a statue this near the wall it faces stares at it


def room_ways(m):
    """House rules from the Greywatch keep (2026-10-05 playtest):
    - the straight way in from every door stays clear: no piece stands in the opening's path for the first
      DOOR_WAY_DEPTH units (a column in line with the door, a statue before it);
    - a statue faces into the room, never at a wall it stands against or near."""
    out = []
    for r in indoor_rooms(m):
        cells, objs = r["cells"], r["objects"]
        cs = set(cells)
        cu = sum(x + y + 1 for x, y in cells) / len(cells); cv = sum(x - y for x, y in cells) / len(cells)
        runs = room_runs(m, cells)
        pieces = [o for o in objs if m.blocking(o) and not m.is_door(o) and
                  (RT.family(o["type"]) in RT.BLOCKING_FAMILIES or FLOOR_LIGHT.search(o["type"]))]
        for d in m.doors:
            gx, gy = d["gap"]
            if not any((gx + a, gy + b) in cs for a, b in N4): continue
            du, dv = gx + gy + 1, gx - gy
            across_u = d["line"] == "/"                         # a door in a '/' wall (u constant) opens along u
            p0, a0 = (du, dv) if across_u else (dv, du)
            sgn = 1 if ((cu if across_u else cv) > p0) else -1
            extent = max(((x + y + 1 if across_u else x - y) - p0) * sgn for x, y in cells)
            for o in pieces:
                tall = RT.family(o["type"]) in TALL_IN_WAY
                depth_max = min(DOOR_WAY_FAR, 0.75 * extent) if tall else min(DOOR_WAY_DEPTH, 0.4 * extent)
                u, v = uv_of(o)
                hu, hv = _half_uv(o)
                pp, pa = (u, v) if across_u else (v, u)
                hp, ha = (hu, hv) if across_u else (hv, hu)
                depth = (pp - p0) * sgn
                if abs(pa - a0) < DOOR_WAY_HALF + ha and depth - hp < depth_max and depth + hp > 0.6:
                    out.append(F("composition", "warning", f"{o['type']} stands in the way in from the door, {max(0.0, depth - hp):.1f} "
                                 f"units inside it: keep the straight way in from every door clear (house rule from the "
                                 f"2026-10-05 playtest, Greywatch's keep).", o["x"], o["y"]))
                    break
        for o in objs:
            mm = STATUE.match(o["type"])
            if not mm or mm.group(1) not in STATUE_FACING: continue
            fu, fv = STATUE_FACING[mm.group(1)]
            u, v = uv_of(o)
            for (line, coord), (lo, hi) in runs.items():
                if (line == "/") != bool(fu): continue           # the walls across the way it faces
                along = v if line == "/" else u
                if not (lo - 0.5 <= along <= hi + 0.5): continue
                ahead = (coord - u) * fu if fu else (coord - v) * fv
                if 0 < ahead <= FACE_WALL_MAX:
                    out.append(F("composition", "warning", f"{o['type']} faces the {_wall_name(line, coord, cu, cv)} wall "
                                 f"{ahead:.1f} units in front of it: a statue faces into the room, its back to the wall "
                                 f"(house rule from the 2026-10-05 playtest, Greywatch's keep).", o["x"], o["y"]))
                    break
    return out


def _bare(a, b, spans):
    """The longest stretch of (a, b) that none of the spans covers."""
    edge, longest = a, 0.0
    for s0, s1 in sorted(spans):
        if s1 <= edge or s0 >= b: continue
        longest = max(longest, s0 - edge)
        edge = max(edge, s1)
    return max(longest, b - edge)


def _room_baseline():
    import validate as V
    return V.baseline().get("room_kinds", {})


def _door_kind_name(t):
    return re.sub(r"(Half|Single)?Door$", "", t)


def building_doors(m):
    """Doors within a building (TreePlace v0.2 room review): a double door between two rooms of a house
    (house rule; Westwood keeps them to palaces and Galava's town houses), and a building whose doors come in
    3 or more kinds (Westwood: 11 of 630 buildings)."""
    out = []
    rooms = find_rooms(m)
    cell_room = {}
    for k, r in enumerate(rooms):
        for c in r["cells"]: cell_room[c] = k
    parent = list(range(len(rooms)))

    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    door_rooms = []
    for d in m.doors:
        gx, gy = d["gap"]
        near = sorted({cell_room.get((gx + a, gy + b)) for a in (-1, 0, 1) for b in (-1, 0, 1)} - {None})
        door_rooms.append((d, near))
        for a_ in near[1:]: parent[find(a_)] = find(near[0])
    kinds = rules("doors")["types"]
    groups = collections.defaultdict(set)
    for d, near in door_rooms:
        if not near: continue
        groups[find(near[0])].add(_door_kind_name(d["obj"]["type"]))
        if len(near) >= 2 and kinds.get(d["obj"]["type"], {}).get("kind") == "double":
            mats = collections.Counter()
            for k in near:
                for (x, y) in rooms[k]["cells"]:
                    for a, b in N4:
                        w = m.walls.get((x + a, y + b))
                        if w and not w.invisible: mats[w.material] += 1
            mat = mats.most_common(1)[0][0] if mats else ""
            if HOUSE_WALL.match(mat) and not mat.startswith("Galava"):
                out.append(F("doors", "warning", f"{d['obj']['type']} is a double door between two rooms of a house: use the "
                             f"single door of the same kind inside (house rule from the TreePlace room review).",
                             d["obj"]["x"], d["obj"]["y"]))
    for g, names in groups.items():
        if len(names) >= 3:
            r = rooms[g]
            out.append(F("doors", "warning", f"One building uses {len(names)} kinds of door ({', '.join(sorted(names))}): keep "
                         f"one kind throughout (Westwood: 11 of 630 buildings use three).", *centre(r["cells"])))
    return out


FRONTED = re.compile(r"Chest\d|Bookcase|Shelves|^Desk\d")            # pieces with a front that faces the room
BUNCH_RE = re.compile(r"^(Stump|ForestLog|CaveRocks|Boulder|MineCrystal|Mushroom)")


def bunched_props(m, base):
    """Props of one kind that all sit in one tight spot and nowhere else on the map (felled stumps
    piled into one clearing): Westwood spreads such props with a falloff from where they belong."""
    out = []
    groups = collections.defaultdict(list)
    # seats round a campfire are one composed set piece, as on Westwood's camps (Con03A's bandit camp: stumps round
    # its CampFire), not props bunched in one spot
    fires = [o for o in m.objects if re.match(r"^(CampFire|OgreFirePit|DunMirFlameBasinLit)$", o["type"])]
    for o in m.objects:
        mt = BUNCH_RE.match(o["type"])
        if not mt or any(math.hypot(o["x"] - f["x"], o["y"] - f["y"]) <= 110 for f in fires): continue
        groups[mt.group(1)].append(o)
    lim = base.get("bunch_share", 0.85)
    for kind, objs in groups.items():
        if len(objs) < 4: continue
        best = max(objs, key=lambda o: sum(1 for p in objs if math.hypot(p["x"] - o["x"], p["y"] - o["y"]) <= 330))
        close = [p for p in objs if math.hypot(p["x"] - best["x"], p["y"] - best["y"]) <= 330]
        if len(close) >= 4 and len(close) / len(objs) >= lim:
            out.append(F("composition", "warning", f"{len(close)} of the map's {len(objs)} {kind} props sit in one spot and "
                         f"nowhere else: spread them out from where they belong.", best["x"], best["y"]))
    return out


def _axis(points):
    """Principal direction (radians, in uv) and anisotropy of a point set."""
    n = len(points)
    mu = sum(p[0] for p in points) / n; mv = sum(p[1] for p in points) / n
    cuu = sum((p[0] - mu) ** 2 for p in points) / n
    cvv = sum((p[1] - mv) ** 2 for p in points) / n
    cuv = sum((p[0] - mu) * (p[1] - mv) for p in points) / n
    ang = 0.5 * math.atan2(2 * cuv, cuu - cvv)
    tr, det = cuu + cvv, cuu * cvv - cuv * cuv
    disc = math.sqrt(max(0.0, tr * tr / 4 - det))
    l1, l2 = tr / 2 + disc, tr / 2 - disc
    return ang, (l1 / l2 if l2 > 1e-6 else 99.0)


def _angle_between(a, b):
    d = abs(a - b) % math.pi
    return math.degrees(min(d, math.pi - d))


def bridge_squareness(m):
    """A bridge crosses square to the water on a straight stretch, never at a slant or on a bend."""
    out = []
    water = [((x + y + 2), (x - y)) for (x, y), d in m.tiles.items() if WATER_RE.search(d["material"])]
    if not water: return out
    chains = collections.defaultdict(list)
    for o in m.objects:
        mt = re.match(r"^(RopeBridge[12])", o["type"])
        if mt and "Back" not in o["type"]: chains[mt.group(1)].append(o)
    decks = []
    for kit, pieces in chains.items():
        left = list(pieces)
        while left:
            ch = [left.pop()]; grew = True
            while grew:
                grew = False
                for o in list(left):
                    if any(math.hypot(o["x"] - c["x"], o["y"] - c["y"]) < 120 for c in ch):
                        ch.append(o); left.remove(o); grew = True
            if len(ch) >= 3:
                cu = sum(uv_of(o)[0] for o in ch) / len(ch); cv = sum(uv_of(o)[1] for o in ch) / len(ch)
                decks.append((cu, cv, 0.0 if kit == "RopeBridge1" else math.pi / 2))
    # plank decks: floor components of planks touching water (Westwood's are 2 tiles wide)
    waterset = {t for t, d in m.tiles.items() if WATER_RE.search(d["material"])}
    planks = {t for t, d in m.tiles.items() if PLANK.match(d["material"])}
    seen = set()
    for st in planks:
        if st in seen: continue
        comp, q = {st}, [st]
        while q:
            a = q.pop()
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                n = (a[0] + dx, a[1] + dy)
                if n in planks and n not in comp: comp.add(n); q.append(n)
        seen |= comp
        if sum(1 for t in comp if any((t[0] + dx, t[1] + dy) in waterset for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)))) < 3:
            continue
        us = [x + y + 2 for x, y in comp]; vs = [x - y for x, y in comp]
        su, sv = (max(us) - min(us)) / 2 + 1, (max(vs) - min(vs)) / 2 + 1
        cu, cv = sum(us) / len(us), sum(vs) / len(vs)
        decks.append((cu, cv, 0.0 if su >= sv else math.pi / 2))
        if min(su, sv) > 2:
            out.append(F("composition", "warning", f"The plank bridge is {min(su, sv):.0f} tiles wide; Westwood's are 2 tiles "
                         f"wide (a narrow deck across a narrow stream).", (cu + cv) / 2 * CELL, (cu - cv) / 2 * CELL))
    for cu, cv, deck_ang in decks:
        near = [(u, v) for u, v in water if 3.0 <= math.hypot(u - cu, v - cv) <= 16.0]
        if len(near) < 12: continue
        flow, aniso = _axis(near)
        if aniso < 2.5: continue                                     # a lake or a wide pool: no flow direction
        x, y = (cu + cv) / 2 * CELL, (cu - cv) / 2 * CELL
        if _angle_between(flow, deck_ang) < 60:
            out.append(F("composition", "warning", "The bridge crosses the water at a slant: lay the crossing square to "
                         "a straight stretch of the stream.", x, y))
            continue
        # both banks of the crossing should run the same way (a straight stretch, not a bend)
        nx, ny = math.cos(deck_ang), math.sin(deck_ang)
        side_a = [(u, v) for u, v in near if (u - cu) * -ny + (v - cv) * nx > 0]
        side_b = [(u, v) for u, v in near if (u - cu) * -ny + (v - cv) * nx <= 0]
        if len(side_a) >= 8 and len(side_b) >= 8:
            fa, aa = _axis(side_a); fb, ab = _axis(side_b)
            if aa >= 2.5 and ab >= 2.5 and _angle_between(fa, fb) > 35:
                out.append(F("composition", "warning", "The bridge sits on a bend of the stream: lay crossings on a "
                             "straight stretch.", x, y))
    return out


def bridge_landings(m):
    """Each end of a plank bridge must open onto ground: a bridge is planned with its road, not jammed
    against the forest."""
    out = []
    water = {t for t, d in m.tiles.items() if WATER_RE.search(d["material"])}
    deck = {t for t, d in m.tiles.items() if PLANK.match(d["material"]) and
            any((t[0] + a, t[1] + b) in water for a, b in ((1, 1), (1, -1), (-1, 1), (-1, -1)))}
    # whole decks: plank tiles connected to a tile touching water
    planks = {t for t, d in m.tiles.items() if PLANK.match(d["material"])}
    seen = set()
    for start in deck:
        if start in seen: continue
        comp, q = {start}, [start]
        while q:
            a = q.pop()
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                n = (a[0] + dx, a[1] + dy)
                if n in planks and n not in comp: comp.add(n); q.append(n)
        seen |= comp
        us = [x + y for x, y in comp]; vs = [x - y for x, y in comp]
        if len(comp) < 6: continue
        axis_u = (max(us) - min(us)) >= (max(vs) - min(vs))
        for end in (0, 1):
            coord = (max(us) if end else min(us)) if axis_u else (max(vs) if end else min(vs))
            mid = (sum(vs) / len(vs)) if axis_u else (sum(us) / len(us))
            step = 2 if end else -2
            bad = 0
            for k in (1, 2):                              # the two tiles beyond this end of the deck
                u, v = (coord + step * k, mid) if axis_u else (mid, coord + step * k)
                x, y = int(round((u + v) / 2)), int(round((u - v) / 2))
                if (x + y) % 2: x += 1
                tile = (x, y)
                cells = ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1))
                if tile not in m.tiles or tile in water or any(c in m.walls and not m.walls[c].invisible for c in cells):
                    bad += 1
            if bad:
                ex, ey = ((coord + mid) / 2 * CELL, (coord - mid) / 2 * CELL) if axis_u else ((mid + coord) / 2 * CELL, (mid - coord) / 2 * CELL)
                out.append(F("composition", "warning", "A bridge ends against a wall or the forest instead of on open ground: "
                             "plan the crossing with its road.", ex, ey))
    return out


PERSON_CLEAR = 18.0       # px between a route's leg and a person standing still (AMR-7); a body is about 24 across
TOUR_STOPS_MIN, TOUR_PAUSE_MIN = 4, 15.0     # a townsperson's tour: stops, and seconds at each (TW-9)
STOP_GAP = 32.0      # px between two stops of the scripted routes: more than a body's width (24) and a little


def check_routes(m, ctx, base):
    """Where creatures walk (playtest 2026-10-05: townsfolk walking into walls and sticking on a door's frame):
    every waypoint stands on floor a body can stand on (off the walls, out of trees, rocks, benches and furniture,
    not on water), and every leg walked between waypoints - each waypoint link, and each step of the routes the
    scripts walk (<map>.routes.json beside a generated map) - runs straight without crossing the void, a wall (fences
    and forest walls are walls), a building or an obstacle, sampled along the segment, and passes any doorway
    square-on through its middle (kit/walkways); every stop faces open ground. Errors on generated maps, notes on
    Westwood's."""
    out = []
    if not m.waypoints: return out
    from kit.walkways import Ground
    g = Ground.from_mapdata(m)
    side = os.path.splitext(m.file or "")[0] + ".routes.json"
    routes = json.load(open(side, encoding="utf-8")) if m.file and os.path.exists(side) else []
    sev = "error" if routes or "mapgen" in (m.file or "").replace("\\", "/").lower() else "info"
    short = lambda n: (n or "").split(":")[-1]
    bad = []
    for w in m.waypoints:
        why = g.point_problem(w["x"], w["y"], wall_clear=11, obj_clear=9)
        if why: bad.append(F("routes", sev, f"Waypoint {short(w['name']) or w.get('n')} stands {why}.", w["x"], w["y"]))
    by_n = {w.get("n"): w for w in m.waypoints}
    by_name = {short(w["name"]): w for w in m.waypoints if w.get("name")}
    legs = {}
    for w in m.waypoints:
        for l in w.get("links") or []:
            o = by_n.get(l if isinstance(l, int) else (l.get("n") if isinstance(l, dict) else None))
            if o is not None and (id(o), id(w)) not in legs: legs[(id(w), id(o))] = (w, o, "link")
    for r in routes:
        ws = [by_name.get(n) for n in r["waypoints"]]
        ws = [w for w in ws if w is not None]
        pairs = list(zip(ws, ws[1:])) + ([(ws[-1], ws[0])] if r.get("loop") and len(ws) > 2 else [])
        for a, b in pairs:
            if (id(a), id(b)) not in legs and (id(b), id(a)) not in legs: legs[(id(a), id(b))] = (a, b, r.get("who", "?"))
    for a, b, who in legs.values():
        why = g.leg_problem((a["x"], a["y"]), (b["x"], b["y"]))
        if why:
            what = "Link" if who == "link" else f"{who}'s route"
            bad.append(F("routes", sev, f"{what} from {short(a['name'])} to "
                         f"{short(b['name'])} {why}.", (a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2))
    # nobody shares a standing spot (playtest 2026-10-05: two people landing on one stop push each other off it for
    # ever): every stop of every route (a waypoint with a pause, a journey's end) STOP_GAP px from every other
    stops = []
    for r in routes:
        for k, n in enumerate(r["waypoints"]):
            w = by_name.get(n)
            if w is not None and k < len(r.get("pauses") or []) and r["pauses"][k] > 0:
                stops.append((w, r.get("who", "?")))
    close = 0
    for i in range(len(stops)):
        for j in range(i + 1, len(stops)):
            (a, wa), (b, wb) = stops[i], stops[j]
            if a is b or wa == wb: continue            # one walker back at its own spot shares it with no one
            d = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
            if d < STOP_GAP:
                close += 1
                bad.append(F("routes", sev, f"{wa}'s stop {short(a['name'])} and {wb}'s stop {short(b['name'])} stand "
                             f"{d:.0f} px apart (under {STOP_GAP:.0f}): one spot for two.",
                             (a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2))
    # every stop faces open ground (Starwell playtest 2026-10-05: "NPCs seem to face random directions when they get
    # to stopping points"): the point it is turned toward at each stop (routes.json "looks", laid by kit/walkways
    # stop_facing) with no wall, building, tree, obstacle or void within FACE_REACH px straight ahead (the feature it
    # stands at excepted)
    from kit.walkways import facing_problem, FACE_REACH
    faced = facing_bad = 0
    for r in routes:
        looks, feats = r.get("looks"), r.get("features") or []
        if looks is None: continue
        for k, n in enumerate(r["waypoints"]):
            w = by_name.get(n)
            if w is None or k >= len(r.get("pauses") or []) or r["pauses"][k] <= 0: continue
            lk = looks[k] if k < len(looks) else None
            faced += 1
            why = "faces nowhere" if not lk else facing_problem(g, (w["x"], w["y"]), lk, feats[k] if k < len(feats) else None)
            if why:
                facing_bad += 1
                bad.append(F("routes", sev, f"{r.get('who', '?')}'s stop {short(n)} {why} (within {FACE_REACH:.0f} px "
                             f"it should face open ground).", w["x"], w["y"]))
    # nobody's walk runs through a person standing still (AMR-7: Morwen waiting at her door stood in Pip's way home): a
    # creature that stands where it was placed (not a walker of these routes) within PERSON_CLEAR px of a route's leg
    walkers = {r.get("who") for r in routes}
    standing = [o for o in m.objects if "MONSTER" in o["cls"] and (o.get("scr") or "").split(":")[-1] not in walkers
                and not (o["xfer"] or {}).get("ShopkeeperInfo", {}).get("ShopItems")
                and (o["type"] in ("NPC", "Maiden") or (o["xfer"] or {}).get("Aggressiveness", 1) < 0.1)]
    blocked = set()
    for a, b, who in legs.values():
        if who == "link": continue
        ax, ay, bx, by = a["x"], a["y"], b["x"], b["y"]
        L2 = (bx - ax) ** 2 + (by - ay) ** 2 or 1.0
        for o in standing:
            t = max(0.0, min(1.0, ((o["x"] - ax) * (bx - ax) + (o["y"] - ay) * (by - ay)) / L2))
            d = math.hypot(ax + t * (bx - ax) - o["x"], ay + t * (by - ay) - o["y"])
            if d < PERSON_CLEAR and 0.0 < t < 1.0 and (who, o["id"]) not in blocked:
                blocked.add((who, o["id"]))
                out.append(F("routes", "warning", f"{who}'s route passes {d:.0f} px from {o['scr'] or o['type']}, who "
                             f"stands there: a person waiting stands beside the way, not in it (StoryMap.doorside).",
                             o["x"], o["y"]))
    # a townsperson walks a tour of real places and stands a while at each (TW-9: "their patrol routes are often too
    # short and repetitive ... stand still for longer (20 seconds)"): StoryMap.townsfolk lays 5-7 stops, 16-24 s each
    for r in routes:
        if r.get("kind") != "tour": continue
        ps = [p for p in (r.get("pauses") or []) if p > 0]
        if len(ps) < TOUR_STOPS_MIN or (ps and min(ps) < TOUR_PAUSE_MIN):
            w = by_name.get(r["waypoints"][0]) if r.get("waypoints") else None
            out.append(F("routes", "warning", f"{r.get('who', '?')} walks a townsperson's tour of {len(ps)} stops, the "
                         f"shortest pause {min(ps) if ps else 0:.0f} s: a tour has {TOUR_STOPS_MIN} or more stops and "
                         f"{TOUR_PAUSE_MIN:.0f} s or more at each (StoryMap.townsfolk).",
                         w["x"] if w else None, w["y"] if w else None))
    out += bad[:40]
    if len(bad) > 40: out.append(F("routes", sev, f"... and {len(bad) - 40} more waypoint and route problems."))
    out.append(F("routes", "info", f"Routes: {len(m.waypoints)} waypoints, {len(legs)} legs walked, {len(stops)} stops, "
                                   f"{len(bad)} problems ({close} stops sharing a spot, {facing_bad} of {faced} stops "
                                   f"facing into something)."))
    return out


# ---- the outdoor ground (Starwell and Ambermere playtests, 2026-10-05) -----------------------------------------
CROWD_PAIR = 30.0         # px: two creatures nearer than this stand on each other (Westwood: 2.5% of its creatures)
CROWD_R, CROWD_N = 90.0, 5      # px, creatures: five round one spot is a swarm ("ten people packed round the fire")
SKIP_PROP = re.compile(r"^(Dock|RopeBridge|LavaBridge|TraderTent|ColorLight|Invisible|Amb|PlayerStart|Extent|Torch$|Boulder|"
                       r"DunMirTorch|LOTDWallSconse|Sconse|Sign|Plank|Waypoint)|Shadow|Door|Gate|Window")
# (calibrated on Westwood's maps: plants, bushes, torch poles and statues stand at a wall's or fence's foot there, 553
# findings on 66 maps; what the playtest saw was crops and goods on the line)
ON_LINE = re.compile(r"^(Garden|Tombstone|Cross\d|Well$|Anvil|Cauldron|CampFire|MiningShovel|MiningPickAxe|"
                     r"SmallStoneBlock|Brazier)")
# (calibrated a second time: goods and racks stand snug to building and dungeon walls in Westwood's maps, 147 findings
# on 45 maps, most where find_rooms sees no room; what the playtest saw was a crop row under a fence)
# creatures that come in swarms in Westwood's maps (spiders, bats, wasps, fish, rats, imps, the dead): two bodies on one
# spot or five round one are a camp's people standing badly, not these (calibrated: 229 findings on 51 maps)
SWARMERS = re.compile(r"Spider|Bat$|Wasp|Fish|Rat$|Imp$|Zombie|Frog|Leech|Wisp|Beetle|Scorpion|Ghost|Skeleton|Urchin$|"
                      r"Mimic|Wolf|Bear|Lizard|Shade")


def _indoor_cells(m):
    """Cells inside buildings: the enclosed rooms' (find_rooms, yards left out), the design's own rooms' floors
    (<map>.rooms.json: a hall too big for find_rooms), and the wall cells beside them (a piece snug to a wall)."""
    if getattr(m, "_indoor", None) is None:
        cells = {c for r in indoor_rooms(m) for c in r["cells"]}
        for (x, y), rec in declared_rooms(m).items():
            if not rec.get("yard"): cells |= {(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)}
        cells |= {(x + a, y + b) for x, y in cells for a in (-1, 0, 1) for b in (-1, 0, 1) if (x + a, y + b) in m.walls}
        m._indoor = cells
    return m._indoor


def check_exterior(m, ctx, base):
    """The outdoor ground, as the playtests read it:
    - props of a scene, a camp or a yard that overlap (Starwell: "barrels of several sizes overlapping one another"):
      two pieces nearer than Westwood's closest pairs allow (kit/spacing.gap);
    - a piece on a fence or wall line (Ambermere: "this fence is literally on top of this row of plants");
    - a pickable thing as ground decor (Starwell: candles as outdoor lights, which the player can pick up);
    - creatures standing on each other or swarming one spot (Starwell: "NPCs are all on top of each other like a
      swarm"); a person's disabled twin, on the person's own spot, is one body;
    - a dock that does not run out from the shore into open water (Ambermere: "the dock is way too close to the
      shore and does not extend out into the middle of the pond")."""
    from kit import spacing as SP
    out = []
    indoor = _indoor_cells(m)
    outdoor = [o for o in m.objects if m.cell_of(o["x"], o["y"]) not in indoor]
    # overlapping props
    props = [o for o in outdoor if not SKIP_PROP.search(o["type"]) and "MONSTER" not in o["cls"] and
             not SP.LOOSE.match(o["type"]) and (SP.family(o["type"]) or (m.blocking(o) and "OBSTACLE" in o["cls"]))]
    grid = collections.defaultdict(list)
    for o in props: grid[(int(o["x"] // 80), int(o["y"] // 80))].append(o)
    bad = []
    for o in props:
        gx, gy = int(o["x"] // 80), int(o["y"] // 80)
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                for p in grid.get((gx + a, gy + b), ()):
                    if p["id"] <= o["id"]: continue
                    g = SP.gap(o["type"], p["type"]) * 0.85
                    d = math.hypot(o["x"] - p["x"], o["y"] - p["y"])
                    # pieces of the spacing families only (a bench at its table, a bench of workstations stand close
                    # by design: calibrated, 147 findings on 38 Westwood maps)
                    if g and d < g and SP.family(o["type"]) and SP.family(p["type"]):
                        bad.append(F("exterior", "warning", f"{o['type']} and {p['type']} stand {d:.0f} px apart (Westwood "
                                     f"keeps them {g / 0.85:.0f}): outdoor pieces overlap.", (o["x"] + p["x"]) / 2,
                                     (o["y"] + p["y"]) / 2))
    out += bad[:25]
    if len(bad) > 25: out.append(F("exterior", "warning", f"... and {len(bad) - 25} more overlapping outdoor pieces."))
    # pieces on a fence or a built wall's line
    built = {c: w for c, w in m.walls.items() if not w.invisible and not NATURAL_WALL.search(w.material)}
    online = []
    for o in outdoor:
        if not ON_LINE.match(o["type"]): continue
        d = SP.wall_clearance(built, o["x"], o["y"], reach=2)
        lim = 0.5 * SP.sprite_half(o["type"]) + 6
        if d < lim:
            online.append(F("exterior", "warning", f"{o['type']} stands {d:.0f} px from a fence or wall line: nothing is "
                            f"placed on top of a fence (keep it {lim:.0f} px or more inside).", o["x"], o["y"]))
    out += online[:25]
    if len(online) > 25: out.append(F("exterior", "warning", f"... and {len(online) - 25} more pieces on a fence or wall line."))
    # pickable things as decor
    for o in outdoor:
        if o.get("scr") or "MONSTER" in o["cls"]: continue
        if SP.PICK_TYPES.match(o["type"]):            # Westwood lays potions and food outdoors as pickups, never lights
            out.append(F("exterior", "warning", f"A {o['type']} lies outdoors as decor: the player can pick it up. Light "
                         f"the ground with a torch pole, a brazier, a lamp or a fire.", o["x"], o["y"]))
    # creatures on each other, and swarms
    # those who stand where they are placed: a walker of the scripted routes (a townsperson's tour, the watch's beat)
    # sets out from its start at once and is not counted
    side = os.path.splitext(m.file or "")[0] + ".routes.json"
    walkers = {r.get("who") for r in json.load(open(side, encoding="utf-8"))} if m.file and os.path.exists(side) else set()
    cr = [o for o in outdoor if "MONSTER" in o["cls"] and "Shopkeeper" not in o["type"] and not SWARMERS.search(o["type"]) and
          (o.get("scr") or "").split(":")[-1] not in walkers]
    for i, a in enumerate(cr):
        for b in cr[i + 1:]:
            d = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
            if 2.0 < d < CROWD_PAIR:
                out.append(F("exterior", "warning", f"{a['type']} and {b['type']} stand {d:.0f} px apart: two bodies on one "
                             f"spot.", (a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2))
    flagged = []
    for a in cr:
        near = {(round(b["x"]), round(b["y"])) for b in cr if math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < CROWD_R}
        if len(near) >= CROWD_N and not any(math.hypot(a["x"] - x, a["y"] - y) < CROWD_R for x, y in flagged):
            flagged.append((a["x"], a["y"]))
            out.append(F("exterior", "warning", f"{len(near)} creatures stand within {CROWD_R:.0f} px of one spot: a swarm. "
                         f"Give each its own post (kit/posts.camp_posts).", a["x"], a["y"]))
    out += outdoor_groups(m)
    out += dock_reach(m)
    return out


def dock_reach(m):
    """A dock runs out from its shore, square to it, over open water: its axis within 35 degrees of the shore's
    normal at its root, most of its length over water, and open water on every side of its far end."""
    out = []
    # a dock's own deck (kit/water._strip lays WoodGray planks over the water it spans) counts as water
    water = {t for t, d in m.tiles.items() if WATER_RE.search(d["material"]) or re.match(r"^WoodGray2?$", d["material"])}
    wet = lambda x, y: m.tile_at_cell(m.cell_of(x, y)) in water
    pieces = collections.defaultdict(list)
    for o in m.objects:
        mt = re.match(r"^(DockDown|DockUp)", o["type"])
        if mt: pieces[mt.group(1)].append(o)
    for kit, ps in pieces.items():
        left = list(ps)
        while left:
            ch = [left.pop()]; grew = True
            while grew:
                grew = False
                for o in list(left):
                    if any(math.hypot(o["x"] - c["x"], o["y"] - c["y"]) < 120 for c in ch):
                        ch.append(o); left.remove(o); grew = True
            dx, dy = DOCK_DIR[kit]; L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
            root = min(ch, key=lambda o: o["x"] * ux + o["y"] * uy)
            tip = max(ch, key=lambda o: o["x"] * ux + o["y"] * uy)
            # the shore's normal at the root: toward the water round it
            sx = sy = 0.0
            for a in range(-10, 11):
                for b in range(-10, 11):
                    x, y = root["x"] + a * 23, root["y"] + b * 23
                    if math.hypot(a, b) <= 10 and wet(x, y): sx += a; sy += b
            nl = math.hypot(sx, sy)
            ang = math.degrees(math.acos(max(-1, min(1, (sx * ux + sy * uy) / nl)))) if nl else 180
            length = math.hypot(tip["x"] - root["x"], tip["y"] - root["y"])
            steps = max(2, int(length / 12))
            over = sum(wet(root["x"] + ux * length * k / steps, root["y"] + uy * length * k / steps)
                       for k in range(steps + 1)) / (steps + 1)
            # water on both sides of it, along its outer three quarters (one that runs along its shore has the bank
            # beside it all the way)
            px_, py_ = -uy, ux
            sides = [all(wet(root["x"] + ux * length * k / steps + px_ * e, root["y"] + uy * length * k / steps + py_ * e)
                         for e in (56, -56)) for k in range(steps + 1) if k >= steps / 4]
            flank = sum(sides) / max(1, len(sides))
            ring = [wet(tip["x"] + 70 * math.cos(q * math.pi / 4), tip["y"] + 70 * math.sin(q * math.pi / 4))
                    for q in range(8)]
            why = []
            if ang > 35: why.append(f"it runs {ang:.0f} degrees off square to its shore")
            if over < 0.6: why.append(f"only {over:.0%} of it lies over water")
            if flank < 0.6: why.append(f"the bank runs beside it ({flank:.0%} of it has water on both sides)")
            if sum(ring) < 7: why.append("its far end lies near a shore")
            if why:
                out.append(F("exterior", "warning", f"The {kit} dock does not reach out into the water: " + "; ".join(why) +
                             ". A dock starts on the bank and runs out square to the shore toward open water.",
                             tip["x"], tip["y"]))
    return out


# ---- the minimap (TW-5, GW-3) -----------------------------------------------------------------------------------------
MAP_EDGE = 5888.0


def _seg_cross(p, q, a, b):
    """Segments pq and ab meet, ends included (as the game counts them: a line through a vertex crosses both edges)."""
    def orient(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]); return (v > 0) - (v < 0)
    def on(p, q, r): return min(p[0], q[0]) <= r[0] <= max(p[0], q[0]) and min(p[1], q[1]) <= r[1] <= max(p[1], q[1])
    o1, o2, o3, o4 = orient(p, q, a), orient(p, q, b), orient(a, b, p), orient(a, b, q)
    if o1 != o2 and o3 != o4: return True
    return (o1 == 0 and on(p, q, a)) or (o2 == 0 and on(p, q, b)) or (o3 == 0 and on(a, b, p)) or (o4 == 0 and on(a, b, q))


def in_polygon_as_game(pts, x, y):
    """The game's test (nox_xxx_polygon_421660): count the polygon's edges crossed by a line from the point to the
    map's corner (0, 0), and again to (5888, 5888); odd both ways is inside. A corner on either map corner, or on the
    diagonal those lines follow, puts every point outside (no minimap: TW-5, GW-3)."""
    for corner in ((0.0, 0.0), (MAP_EDGE, MAP_EDGE)):
        n = sum(_seg_cross((x, y), corner, tuple(pts[i]), tuple(pts[(i + 1) % len(pts)])) for i in range(len(pts)))
        if n % 2 == 0: return False
    return True


MINIMAP_SHARE_MIN = 0.25     # Westwood: median 100% of the floor inside a minimap polygon; lowest 28% (Con06a, War06a)


def minimap_cover(m):
    """Share of a sample of the floor (and whether the PlayerStart is) inside a polygon with a minimap group."""
    import random as _r
    polys = [p for p in m.polygons if p.get("mm") and len(p.get("pts") or []) >= 3]
    cells = sorted(m.cover)
    sample = _r.Random(1).sample(cells, min(300, len(cells))) if cells else []
    inside = lambda x, y: any(in_polygon_as_game(p["pts"], x, y) for p in polys)
    share = sum(inside(cx * CELL + 11.5, cy * CELL + 11.5) for cx, cy in sample) / max(1, len(sample))
    starts = [o for o in m.objects if o["type"] == "PlayerStart"]
    return share, all(inside(o["x"], o["y"]) for o in starts), len(polys)


def check_minimap(m, ctx, base):
    out = []
    if not m.cover: return out
    share, start_in, n = minimap_cover(m)
    if not start_in:
        out.append(F("minimap", "error", f"The player starts outside every minimap polygon ({n} with a minimap group): "
                     f"the minimap draws nothing there. One polygon over the whole map, inset from its edges, its corners "
                     f"off the (0,0)-(5888,5888) diagonal (Spec.build does this)."))
    elif share < MINIMAP_SHARE_MIN:
        out.append(F("minimap", "warning", f"Only {share:.0%} of the floor lies inside a minimap polygon: the minimap "
                     f"is blank over the rest."))
    return out


# ---- a room with an identity (SW-6, SWR-1, SWR-2, GW-7, TW-8, AMR-4) ---------------------------------------------
# kinds that stand in rows or line walls by design: not counted as a piece repeated along a wall
LINED = re.compile(r"^(Plant|Bush|Obelisk|CaveRockPillar|RuinsColumn|Tombstone|LOTDTombstone|Flower|"
                   r"Bookcase|MovableBookcase|LogShelves|PotionShelves|WizardWorkstation|Trader|Bed|WoodBed|Cot|Bench|"
                   r"LightBench|CushionedBench|Crypt|Coffin|Column|CathedralColumn|LOTD|Barrel|Crate|DarkCrate|Sack|"
                   r"PiledBarrels|LargeBarrel|WaterBarrel|BarrelWithTools|Candleabra|Nightstand|Chest|OgreStraw|"
                   r"BlackPowderBarrel)")     # (a powder store's kegs stand in rows: rules/rooms/powder_store.md)
TABLES_RE = re.compile(r"^(Table\d|RoundTable\d|SquareTable\d|OvalTable\d|RoundTableWithFood|SmallTable\d|OgreTable\d)$")
SUPPLY_RE = re.compile(r"^(Barrel|Barrel2|LargeBarrel\d|PiledBarrels\d|WaterBarrel|BarrelWithTools\d|BarrelSteel\d|Crate\d|"
                       r"DarkCrate\d|CrateSteel\d|SackChest|TraderAppleCrate|BlackPowderBarrel)")
STORE_KINDS = {"storeroom", "ore_store", "gear_store", "kitchen", "cellar", "warehouse"}
SUPPLY_WALL_MAX = 0.6        # share of one wall's length supplies may take outside a store (Westwood: see calibrate)
MONOTONY_MIN_PIECES, MONOTONY_SHARE = 16, 0.6
MONOTONY_EXEMPT = re.compile(r"^(Bookcase|MovableBookcase|LogShelves|PotionShelves|TraderShelves|LOTDTombstone|Coffin|"
                             r"Sarcophagus|Crypt)")     # a room of 16+ pieces of furniture where one kind is 60%+ of them
COUNTER_RE = re.compile(r"^(TraderDesk|BarPiece|BarCorner|BarHingedTop)")
KEEPER_REACH = 90.0          # px from a keeper to the counter he stands behind (Westwood: 25-49 px for 54 of 94 keepers)
THRONE_RE = re.compile(r"^DunMirThroneBase")


def _kind_stem(t):
    return re.sub(r"(\d+[a-z]?|HalfFull|Empty|NE|NW|SE|SW|N|S|E|W)$", "", t)


def identity_flags(m, r, kind):
    """What makes a room read as having no identity: (walls used, the most of one stand-alone kind on a wall, flags),
    each flag (rule, text, object). Shared by check_identity and review/roomscore.py."""
    from kit.furnish import SHOWPIECES, SHOWPIECE_LIMIT, SHOWPIECE_BIG
    from kit.identity import ROOMS
    cells = r["cells"]
    cu = sum(x + y + 1 for x, y in cells) / len(cells); cv = sum(x - y for x, y in cells) / len(cells)
    runs = room_runs(m, cells)
    flags, per_wall, used, show = [], collections.defaultdict(collections.Counter), set(), collections.defaultdict(list)
    wall_obj, supplies = {}, collections.defaultdict(list)
    for o in r["objects"]:
        t = o["type"]
        hit = _against(o, runs, cu, cv, m, reach=1.6, across=True)
        fam = RT.family(t)
        if hit and fam not in (None, "light") and not t.startswith("Candleabra"): used.add(hit[0])
        if hit and not LINED.match(t) and fam not in (None, "wall_decor", "light"):
            per_wall[hit[0]][_kind_stem(t)] += 1; wall_obj[(hit[0], _kind_stem(t))] = o
        if hit and SUPPLY_RE.match(t):
            ha = _half_uv(o)[1] if hit[3] == "/" else _half_uv(o)[0]
            supplies[(hit[3], hit[4])].append((hit[2] - ha, hit[2] + ha, o))
        sm = SHOWPIECES.match(t)
        if sm: show[sm.group(1)].append(o)
    big = r["tiles"] >= SHOWPIECE_BIG
    for base_, os_ in show.items():
        if len(os_) > SHOWPIECE_LIMIT.get(base_, 1) + (1 if big else 0):
            flags.append(("showpiece", f"{len(os_)} {base_}", os_[0]))
    rep_ = max((n for c in per_wall.values() for n in c.values()), default=0)
    if rep_ >= 4:
        w, (k, n) = max(((w, c.most_common(1)[0]) for w, c in per_wall.items()), key=lambda x: x[1][1])
        flags.append(("repeat_wall", f"{n} {k} on the {w} wall", wall_obj[(w, k)]))
    ident = ROOMS.get(kind, {})
    tables = [o for o in r["objects"] if TABLES_RE.match(o["type"])]
    most = (ident.get("repeat", {}).get("table") or (None, None))[1]
    if r.get("declared") and most is not None and len(tables) > most:
        flags.append(("tables", f"{len(tables)} tables (its kind sets at most {most})", tables[0]))
    from kit.roomtypes import profile as _type_profile         # the room's type sets what may line a wall and repeat
    tp = _type_profile(kind) or {}
    if kind not in STORE_KINDS and not tp.get("supplies_line"):
        for (line, coord), sp in supplies.items():
            lo, hi = runs.get((line, coord), (0, 0))
            length = hi - lo
            if length < 6: continue
            sp.sort(key=lambda s: s[0]); covered, end = 0.0, -1e9
            for a, b, _ in sp:
                if b > end: covered += b - max(a, end); end = b
            if covered / length > SUPPLY_WALL_MAX and len(sp) >= 5:
                flags.append(("supplies_wall", f"{len(sp)} barrels, crates or sacks take {covered / length:.0%} of the "
                              f"{_wall_name(line, coord, cu, cv)} wall", sp[0][2]))
    furn = [o for o in r["objects"] if m.blocking(o) and RT.family(o["type"]) in RT.BLOCKING_FAMILIES]
    if len(furn) >= MONOTONY_MIN_PIECES:
        # shelves lining walls are a store's or a library's walls, and a crypt is rows of its dead: not one kind filling
        # the floor (calibrated: Ambermere's crypt and storeroom)
        stems = collections.Counter(_kind_stem(o["type"]) for o in furn if not MONOTONY_EXEMPT.match(o["type"]))
        k, n = stems.most_common(1)[0] if stems else ("", 0)
        if n / len(furn) >= tp.get("monotony", MONOTONY_SHARE):
            flags.append(("monotony", f"{n} of its {len(furn)} pieces are {k}",
                          next(o for o in furn if _kind_stem(o["type"]) == k)))
    return len(used), rep_, flags


IDENTITY_TEXT = {
    "showpiece": "a showpiece stands once in a room (kit/furnish.py SHOWPIECES; SWR-1)",
    "repeat_wall": "a piece that stands alone is not repeated along a wall; walls are lined only with the kinds Westwood "
                   "lines walls with (SW-6, SWR-1)",
    "tables": "more free-standing tables than the room's kind sets (ROOMS repeat; SW-6, TW-8)",
    "supplies_wall": "supplies line a wall corner to corner only in a store (stock_walls per_wall; AMR-4)",
    "monotony": "one kind fills a big room: cap the repeated set and mix composed groups (ROOMS repeat; TW-8, SW-6)",
}


def check_identity(m, ctx, base):
    """A room reads as what it is (Starwell playtest: the laboratory "almost looks like some sort of shoddy mess hall
    with random objects stuffed in it"; the NE wall's showpiece shelves repeated; Greywatch's chapel of 46 pews): the
    identity flags above, a shop's keeper behind his counter (SWR-2), a throne facing its door (GW-7)."""
    out = []
    for r in indoor_rooms(m):
        kind, _ = room_kind(r)
        _, _, flags = identity_flags(m, r, kind)
        for rule, text, o in flags:
            out.append(F("identity", "warning", f"{kind.replace('_', ' ')} room: {text}: {IDENTITY_TEXT[rule]}.",
                         o["x"], o["y"], rule=f"identity.{rule}"))
        objs = r["objects"]
        counters = [o for o in objs if COUNTER_RE.match(o["type"])]
        cells = r["cells"]
        cx, cy = centre(cells)
        for k in objs:
            if "MONSTER" not in k["cls"] or not ((k["xfer"].get("ShopkeeperInfo") or {}).get("ShopItems")): continue
            if not counters: continue
            near = min(counters, key=lambda c: math.hypot(c["x"] - k["x"], c["y"] - k["y"]))
            d = math.hypot(near["x"] - k["x"], near["y"] - k["y"])
            behind = math.hypot(cx - near["x"], cy - near["y"]) < math.hypot(cx - k["x"], cy - k["y"])
            if d > KEEPER_REACH or not behind:
                out.append(F("identity", "warning", f"The shopkeeper {k['scr'] or k['type']} stands "
                             f"{'away from' if d > KEEPER_REACH else 'in front of'} the counter ({d:.0f} px): a keeper "
                             f"stands behind his counter, between it and the wall (StoryMap.shops; SWR-2).",
                             k["x"], k["y"], rule="identity.keeper"))
        for t in objs:
            if not THRONE_RE.match(t["type"]): continue
            u, v = uv_of(t)
            cs = set(cells)
            doors = [d for d in m.doors if any((d["gap"][0] + a, d["gap"][1] + b) in cs for a, b in N4)]
            ahead = []
            for d in doors:
                du, dv = d["gap"][0] + d["gap"][1] + 1, d["gap"][0] - d["gap"][1]
                if du - u > 2 and abs(dv - v) <= max(2.5, 0.25 * (du - u)): ahead.append(d)
            if doors and not ahead:
                out.append(F("identity", "warning", "The throne does not face a door: Dun Mir's throne faces SE, so it "
                             "stands on the NW wall in line with the room's door in the SE wall, down a clear aisle "
                             "(place_throne, building._seat_throne; GW-7).", t["x"], t["y"], rule="identity.throne"))
    return out


# ---- the object knowledge base (Harrowby playtest HB-1..HB-5; mapgen/kit/objects.py, rules/out/objects.json) ---------
PIECE_REACH, HANG_REACH = 1.0, 2.6     # uv units from a wall line: a piece against the wall, a hanging on it
COMPOSITE_GAP = 0.1                    # two statues this near are one statue of several pieces (Westwood's)
# the checker's tolerances over the furnisher's rules, so Westwood's campaign rooms rarely trip them (calibrated on one map
# of each campaign layout; the furnisher holds the rules themselves): a chest more than the type's p90, statues nearly
# touching (Westwood stands a pair 1 unit apart flanking a door; the furnisher keeps 2), half as many candelabras again
CHEST_SLACK, STATUE_CLOSE, LIGHT_SLACK, HANG_OVERLAP = 1, 0.6, 1.5, 0.4


def _piece_walls(o, runs, cu, cv, reach):
    """[(wall name, line, coord, gap, along, half-length along)] of every wall a piece stands against."""
    u, v = uv_of(o)
    hu, hv = _half_uv(o)
    out = []
    for (line, coord), (lo, hi) in runs.items():
        along = v if line == "/" else u
        if not (lo - 0.5 <= along <= hi + 0.5): continue
        perp = abs(u - coord) if line == "/" else abs(v - coord)
        depth, ha = (hu, hv) if line == "/" else (hv, hu)
        if perp - depth <= reach: out.append((_wall_name(line, coord, cu, cv), line, coord, perp - depth, along, ha))
    return out


def _edge(a, b):
    au, av = uv_of(a); bu, bv = uv_of(b)
    ahu, ahv = _half_uv(a); bhu, bhv = _half_uv(b)
    return max(abs(au - bu) - ahu - bhu, abs(av - bv) - ahv - bhv)


def piece_flags(m, r, kind):
    """What the object knowledge base faults in one room: (rule, text, object). Shared by check_pieces and the labs."""
    from kit import objects as OBJ
    from kit.roomtypes import KIND_TYPE
    rtype = KIND_TYPE.get(kind, kind)
    tiles = r["tiles"]
    cells = r["cells"]
    cu = sum(x + y + 1 for x, y in cells) / len(cells); cv = sum(x - y for x, y in cells) / len(cells)
    runs = room_runs(m, cells)
    objs = [o for o in r["objects"] if "MONSTER" not in o["cls"]]
    cat = {id(o): OBJ.category(o["type"]) for o in objs}
    floor = [o for o in objs if cat[id(o)] not in (None, "hanging", "rug") and not m.is_door(o)]
    flags = []
    # caps: one cauldron, chests by the room type, a showpiece once
    groups = collections.defaultdict(list)
    for o in floor:
        # (a second hearth in a big kitchen or hall is Westwood's own: the furnisher caps it, the checker leaves it)
        if OBJ.room_cap(o["type"], rtype, tiles) is not None and cat[id(o)] not in ("table", "hearth", "statue") \
                and cat[id(o)] not in OBJ.EVIDENCE_CATS:
            groups[OBJ.cap_key(o["type"])].append(o)
    for key, os_ in groups.items():
        cap = OBJ.room_cap(os_[0]["type"], rtype, tiles)
        if len(os_) <= cap: continue
        if key == "cauldron": flags.append(("cauldrons", f"{len(os_)} cauldrons", os_[0]))
        elif key == "chest":
            if len(os_) > cap + CHEST_SLACK:
                flags.append(("chests", f"{len(os_)} chests (its type holds {cap} at most)", os_[0]))
        else: flags.append(("showpiece", f"{len(os_)} {key}", os_[0]))
    # a bedroom's one table-and-chair set
    if rtype == "bedroom":
        sets = [o for o in floor if cat[id(o)] in ("table", "desk")]
        if len(sets) > 1: flags.append(("sets", f"{len(sets)} tables and desks", sets[0]))
    # clearances the playtest set (a bed or a chest by a fire, a bench by a bed, two statues side by side)
    seen = set()
    for a in floor:
        for b in floor:
            if a is b or (id(b), id(a)) in seen: continue
            ca, cb = cat[id(a)], cat[id(b)]
            g = OBJ.HOUSE_CLEAR.get((ca, cb)) or OBJ.HOUSE_CLEAR.get((cb, ca))
            if not g: continue
            seen.add((id(a), id(b)))
            gap = _edge(a, b)
            if ca == cb == "statue":
                if gap <= COMPOSITE_GAP: continue
                g = STATUE_CLOSE
            if gap < g - 0.15:
                flags.append(("clearance", f"{a['type']} {max(0.0, gap):.1f} units from {b['type']} (they keep {g:.1f} apart)", a))
    # runs of a piece that stands alone, along a wall
    walls_of = {id(o): _piece_walls(o, runs, cu, cv, PIECE_REACH) for o in floor}
    by = collections.defaultdict(list)
    for o in floor:
        for w in walls_of[id(o)][:1]:
            by[(w[1], w[2], w[0], OBJ.kind(o["type"]))].append((w[4], o))
    for (line, coord, name, k), lst in by.items():
        mr = OBJ.max_run(lst[0][1]["type"])
        if mr is None or len(lst) <= mr: continue
        lst.sort(key=lambda x: x[0])
        run = [lst[0][1]]; best = run
        for (_, p0), (_, p1) in zip(lst, lst[1:]):
            run = run + [p1] if _edge(p0, p1) <= OBJ.RUN_GAP else [p1]
            if len(run) > len(best): best = run
        if len(best) > mr + 1:
            flags.append(("run", f"{len(best)} {k} side by side along the {name} wall (it stands {mr} at most so)", best[0]))
    # a hanging above a piece standing against the same wall
    for h in objs:
        if cat[id(h)] != "hanging": continue
        hw = _piece_walls(h, runs, cu, cv, HANG_REACH)
        if not hw: continue
        name, line, coord, _, along, ha = min(hw, key=lambda w: w[3])
        ha = max(ha, 0.9)
        for o in floor:
            if cat[id(o)] == "light": continue
            for w in walls_of[id(o)]:
                if w[1] == line and w[2] == coord and w[0] == name and abs(w[4] - along) < ha + w[5] - HANG_OVERLAP:
                    flags.append(("hung", f"{h['type']} hangs above {o['type']} on the {name} wall", h)); break
            else:
                continue
            break
    # candelabras by the room's size
    lights = [o for o in floor if re.match(r"Candleabra|Candelabra", o["type"])]
    cap = OBJ.light_cap(tiles)
    if len(lights) > LIGHT_SLACK * cap + 1:
        flags.append(("lights", f"{len(lights)} candelabras in {tiles} tiles (rooms of its size hold {cap})", lights[0]))
    return flags


PIECE_TEXT = {
    "cauldrons": "a room holds one cauldron at most (kit/objects.py room_cap; HB-1)",
    "chests": "chests by the room type's Westwood p90, a bedroom one (kit/objects.py chest_cap; HB-2, HB-3)",
    "showpiece": "a showpiece stands once in a room (kit/objects.py role; HB-1)",
    "sets": "a bedroom holds one table-and-chair set (kit/objects.py; HB-3)",
    "clearance": "a bed or a chest keeps off the fires, a bench off the bed, statues apart unless a pair flanking "
                 "something (kit/objects.py HOUSE_CLEAR; HB-1, HB-2, HB-4)",
    "run": "only the pieces Westwood lines walls with line them; the others stand alone or in short runs (kit/objects.py "
           "max_run; HB-1, HB-5)",
    "hung": "a hanging takes bare wall, never above a piece against it (kit/objects.py hangs_over; HB-2)",
    "lights": "candelabras by the room's size (kit/objects.py light_cap; HB-4)",
}


def check_pieces(m, ctx, base):
    """How each piece fits its room, by the object knowledge base measured on Westwood's campaign rooms
    (rules/objects.py): caps (one cauldron, chests by the room type, a showpiece once, a bedroom's one table set),
    clearances between categories, runs only of the pieces that line walls, hangings on bare wall, candelabras by size."""
    out = []
    for r in indoor_rooms(m):
        kind, _ = room_kind(r)
        for rule, text, o in piece_flags(m, r, kind):
            out.append(F("pieces", "warning", f"{kind.replace('_', ' ')} room: {text}: {PIECE_TEXT[rule]}.",
                         o["x"], o["y"], rule=f"pieces.{rule}"))
    return out

# ---- camps and outdoor groups (GW-2, GW-4, SW-1, SW-3, SW-9) ------------------------------------------------------
STUMP_RE = re.compile(r"^Stump\d+$")
FIRE_RE = re.compile(r"^(CampFire|CampFireUnused)$")
CAMP_SEAT_R = 90.0           # px: a stump this near a camp fire reads as its seat (SW-3)
COT_RE = re.compile(r"^(Cot\d|UrchinBed(Flat)?\d)$")
TENT_RE = re.compile(r"^(OutdoorTraderPupTent|TraderTent)")
BEDROLL_REACH = 120.0
CAMP_REACH = 400.0           # px from a camp fire: the camp's ground        # px: a bedroll lies before a tent or beside another in a row
PILE_RE = re.compile(r"^(Barrel|Barrel2|LargeBarrel\d|PiledBarrels\d|Crate\d|DarkCrate\d|CrateSteel\d|SackChest\d?)$")
PILE_LINK, PILE_MIN, PILE_KINDS = 45.0, 5, 2     # five or more crates and barrels of at most two kinds, bunched
PILE_COMPANY = 90.0          # ...with nothing else of a scene (a cart, a rack, a bench, a tool) within this of them
GRAVES_MIN = 3


def outdoor_groups(m):
    """Camp and scene faults on the outdoor ground: stumps as seats round a fire, bedrolls strewn in the open, a pile of
    crates and barrels with no purpose about it, a graveyard with no graves."""
    out = []
    indoor = _indoor_cells(m)
    outdoor = [o for o in m.objects if m.cell_of(o["x"], o["y"]) not in indoor]
    fires = [o for o in outdoor if FIRE_RE.match(o["type"])]
    for o in outdoor:
        if STUMP_RE.match(o["type"]):
            f = min(fires, key=lambda f: math.hypot(f["x"] - o["x"], f["y"] - o["y"]), default=None)
            if f is not None and math.hypot(f["x"] - o["x"], f["y"] - o["y"]) < CAMP_SEAT_R:
                out.append(F("exterior", "warning", f"{o['type']} stands by a camp fire as a seat: a fire's seats are "
                             f"log benches, stools or logs, never stumps (camps.bandit_camp; SW-3).", o["x"], o["y"],
                             rule="exterior.camp_seat"))
    cots = [o for o in outdoor if COT_RE.match(o["type"])]
    tents = [o for o in outdoor if TENT_RE.match(o["type"])]
    for o in cots:
        # a camp's bedrolls: a fire within CAMP_REACH (Westwood's barracks and dens lay cots on their floors, many in
        # buildings find_rooms does not close: 105 findings on 30 maps before this)
        if not any(math.hypot(f["x"] - o["x"], f["y"] - o["y"]) < CAMP_REACH for f in fires): continue
        by_tent = any(math.hypot(t["x"] - o["x"], t["y"] - o["y"]) < BEDROLL_REACH for t in tents)
        fam = o["type"][:3]                                   # Cot / Urc(hinBed): a row of one family
        in_row = any(p is not o and p["type"][:3] == fam and math.hypot(p["x"] - o["x"], p["y"] - o["y"]) < 80
                     for p in cots)
        if not by_tent and not in_row:
            out.append(F("exterior", "warning", f"{o['type']} lies alone in the open: a camp's bedrolls lie before their "
                         f"tents, two to a tent, or side by side in a row (camps.bandit_camp, camps.urchin_camp; GW-4, "
                         f"SW-1).", o["x"], o["y"], rule="exterior.bedroll"))
    pile = [o for o in outdoor if PILE_RE.match(o["type"])]
    left = list(pile)
    others = [o for o in outdoor if not PILE_RE.match(o["type"]) and (SKIP_PROP.search(o["type"]) is None) and
              "MONSTER" not in o["cls"] and m.blocking(o) and not re.match(r"^(Tree|Rock|Boulder|Stump|Bush|Plant)", o["type"])]
    while left:
        g = [left.pop()]; grew = True
        while grew:
            grew = False
            for o in list(left):
                if any(math.hypot(o["x"] - c["x"], o["y"] - c["y"]) < PILE_LINK for c in g):
                    g.append(o); left.remove(o); grew = True
        if len(g) < PILE_MIN or len({_kind_stem(o["type"]) for o in g}) > PILE_KINDS: continue
        gx, gy = sum(o["x"] for o in g) / len(g), sum(o["y"] for o in g) / len(g)
        if any(math.hypot(o["x"] - gx, o["y"] - gy) < PILE_COMPANY for o in others): continue
        out.append(F("exterior", "warning", f"{len(g)} {' and '.join(sorted({_kind_stem(o['type']) for o in g}))} stand "
                     f"heaped with nothing else about them: an outdoor group is a scene with a purpose (a cart, barrels, a "
                     f"crate, a rack...; kit/scenes.py CATALOGUE; GW-2).", gx, gy, rule="exterior.pile"))
    side = os.path.splitext(m.file or "")[0] + ".rooms.json"
    if m.file and os.path.exists(side):
        for rec in json.load(open(side, encoding="utf-8")):
            if not rec.get("yard") or "grave" not in (rec.get("kind") or ""): continue
            fl = {tuple(c) for c in rec.get("floor", [])}
            graves = [o for o in m.objects if re.match(r"^(Tombstone|LOTDTombstone|Cross\d)", o["type"]) and
                      (lambda c: any((c[0] + a, c[1] + b) in fl for a in (-1, 0) for b in (-1, 0)))(m.cell_of(o["x"], o["y"]))]
            if len(graves) < GRAVES_MIN and fl:
                x, y = centre(list(fl))
                out.append(F("exterior", "warning", f"The graveyard holds {len(graves)} graves: a graveyard has graves "
                             f"in rows, headstones on dug earth (yards._graveyard; SW-9).", x, y, rule="exterior.graveyard"))
    return out


# ---- every finding has a rule: (rule, check, message pattern, feedback it answers) ----------------------------------
# Feedback IDs are those of review/FEEDBACK.md. A finding whose message matches no pattern is "<check>.other": the
# self-test fails on one, so a new message gets its rule here.
RULES = [
    ("setup.no_start", "setup", r"^No PlayerStart", ""),
    ("setup.mp_object", "setup", r"^Multiplayer-only", ""),
    ("setup.type_flags", "setup", r"^Map type flags", ""),
    ("minimap.start", "minimap", r"^The player starts outside every minimap", "TW-5 GW-3"),
    ("minimap.cover", "minimap", r"of the floor lies inside a minimap", "TW-5 GW-3"),
    ("wall_pieces.black", "wall_pieces", r"never appear in", "MF-1"),
    ("wall_shapes.jamb", "wall_shapes", r"^Wall piece beside a door opening", "DV1-2"),
    ("wall_shapes.gap", "wall_shapes", r"does not connect to the neighbouring", "DV1-2"),
    ("boundary.hole", "boundary", r"^Hole in the outer wall", "MF-2"),
    ("boundary.open_edge", "boundary", r"^Open edge", "MF-2"),
    ("doors.on_wall", "doors", r"stands on a wall piece instead", "DV1-3"),
    ("doors.no_wall", "doors", r"is not set in a wall", "DV1-3"),
    ("doors.half_single", "doors", r"is half of a double door but fills", "DV1-3"),
    ("doors.no_half", "doors", r"has no matching half", "DV1-3"),
    ("doors.pair_line", "doors", r"is hung as a pair in", "DV6-4"),
    ("doors.single_in_pair", "doors", r"\(a single door\) is in a 2-cell", "DV1-3"),
    ("doors.double_inside", "doors", r"is a double door between two rooms", "TP2-10"),
    ("doors.kinds", "doors", r"kinds of door", "TP2-10"),
    ("kits.step", "kits", r"off every step Westwood uses", "DV1-1"),
    ("kits.back", "kits", r"offsets from its front piece", "DV1-1"),
    ("objects.void", "objects", r"stands in the void", ""),
    ("objects.in_wall", "objects", r"stands inside a wall piece", ""),
    ("objects.hidden", "objects", r"SE or SW wall's cell", ""),
    ("reachability.unreachable", "reachability", r"cannot be reached|more unreachable", ""),
    ("story.gate", "story", r"story's gates locked", ""),
    ("doorways.blocked", "doorways", r"blocks the doorway", ""),
    ("floors.threshold", "floors", r"^The outdoor .* a room's", "SW-4"),
    ("floors.never_touch", "floors", r"touch directly", "MF-3"),
    ("floors.hard_seam", "floors", r"^Hard seam", "DV3-2"),
    ("floors.unblended", "floors", r"of floor seams that Westwood blends", "DV3-2"),
    ("rooms.crammed", "rooms", r"is crammed", "DV1-4"),
    ("rooms.count", "rooms", r"pieces of furniture; Westwood", "DV1-4"),
    ("rooms.bare", "rooms", r"is nearly bare", "TP2-1"),
    ("rooms.stray", "rooms", r"not belong in a", "DV3-4 TP1-4"),
    ("rooms.small", "rooms", r"is small for its kind", "DV1-4"),
    ("rooms.large", "rooms", r"is large for its kind", ""),
    ("identity.showpiece", "identity", r"a showpiece stands once", "SWR-1"),
    ("identity.repeat_wall", "identity", r"is not repeated along a wall", "SW-6 SWR-1"),
    ("identity.tables", "identity", r"free-standing tables than", "SW-6 TW-8"),
    ("identity.supplies_wall", "identity", r"supplies line a wall", "AMR-4"),
    ("identity.monotony", "identity", r"one kind fills a big room", "TW-8 SW-6"),
    ("identity.keeper", "identity", r"stands behind his counter", "SWR-2"),
    ("identity.throne", "identity", r"throne does not face a door", "GW-7"),
    ("pieces.cauldrons", "pieces", r"cauldrons", "HB-1"),
    ("pieces.chests", "pieces", r"chests by the room type", "HB-2 HB-3"),
    ("pieces.showpiece", "pieces", r"showpiece stands once", "HB-1"),
    ("pieces.sets", "pieces", r"one table-and-chair set", "HB-3"),
    ("pieces.clearance", "pieces", r"keeps off the fires", "HB-1 HB-2 HB-4"),
    ("pieces.run", "pieces", r"stand alone or in short runs", "HB-1 HB-5"),
    ("pieces.hung", "pieces", r"hanging takes bare wall", "HB-2"),
    ("pieces.lights", "pieces", r"candelabras by the room's size", "HB-4"),
    ("density.range", "density", r"^(Few|Many) ", "DV3-5 TL-4"),
    ("composition.dock_puddle", "composition", r"dock ends .* from the far bank", "DV4-1"),
    ("composition.lights_pair", "composition", r"side by side in one room", "DV4-5 DV6-2"),
    ("composition.bar_gap", "composition", r"bar counter stops", "DV4-6"),
    ("composition.path_to_wall", "composition", r"^A path ends at a building wall", "DV4-2"),
    ("composition.anchor_blocked", "composition", r"right in front of", "DV5-4"),
    ("composition.across_wall", "composition", r"across the wall instead", "DV6-1"),
    ("composition.chairs_no_table", "composition", r"chairs and no table", "DV5-4"),
    ("composition.bunched", "composition", r"bunched into one part", "DV5-4"),
    ("composition.torch_indoors", "composition", r"open torch", "TP1-5"),
    ("composition.food", "composition", r"Nox draws items at floor level", "TP1-1"),
    ("composition.table_no_seats", "composition", r"has no seats", "TP1-3"),
    ("composition.ends_only", "composition", r"seated only at its ends", "TP1-2"),
    ("composition.mixed_beds", "composition", r"beds of \d+ kinds", "TP1-3"),
    ("composition.scattered_beds", "composition", r"beds scattered", "TP1-3"),
    ("composition.short_span", "composition", r"furniture fills only", "TP1-1"),
    ("composition.beds_close", "composition", r"from the next bed", "TP2-6"),
    ("composition.hearth_crowded", "composition", r"crowds .*hearth room", "TP2-9"),
    ("composition.table_on_rug", "composition", r"stands half on", "TP2-1"),
    ("composition.sparse", "composition", r"is sparse: furniture", "TP2-1 TP3-9"),
    ("composition.front_wall", "composition", r"where the camera sees only", "TP3-a"),
    ("composition.off_wall", "composition", r"units off the .* wall, alone", "TP3-3"),
    ("composition.shelves_gap", "composition", r"with bare wall between them", "TP3-b TL-2"),
    ("composition.way_in", "composition", r"in the way in from the door", "GW-7"),
    ("composition.statue_wall", "composition", r"a statue faces into the room", "GW-7"),
    ("composition.props_bunched", "composition", r"props sit in one spot", "DV6-3"),
    ("composition.bridge_wide", "composition", r"plank bridge is", "DV6-5 MF-3"),
    ("composition.bridge_slant", "composition", r"crosses the water at a slant", "DV6-5"),
    ("composition.bridge_bend", "composition", r"sits on a bend", "DV6-5"),
    ("composition.bridge_landing", "composition", r"^A bridge ends against", "DV5-3"),
    ("routes.waypoint", "routes", r"^Waypoint ", "TW-1 TW-9"),
    ("routes.leg", "routes", r"^(Link|.*'s route) from", "TW-1 TW-9 GW-1"),
    ("routes.shared_stop", "routes", r"one spot for two", "GW-6"),
    ("routes.facing", "routes", r"should face open ground", "SW-2"),
    ("routes.tour", "routes", r"a townsperson's tour", "TW-9"),
    ("routes.through_person", "routes", r"who stands there", "AMR-7"),
    ("routes.more", "routes", r"more waypoint and route problems", ""),
    ("exterior.overlap", "exterior", r"outdoor pieces overlap|more overlapping outdoor", "SW-5"),
    ("exterior.on_fence", "exterior", r"fence or wall line", "AM-1"),
    ("exterior.pickable", "exterior", r"lies outdoors as decor", "SW-8"),
    ("exterior.two_bodies", "exterior", r"two bodies on one", "GW-5 SW-1"),
    ("exterior.swarm", "exterior", r"a swarm", "GW-5 SW-1"),
    ("exterior.dock", "exterior", r"dock does not reach out", "DV4-1 AM-2"),
    ("exterior.camp_seat", "exterior", r"never stumps", "SW-3"),
    ("exterior.bedroll", "exterior", r"lies alone in the open", "GW-4 SW-1"),
    ("exterior.pile", "exterior", r"heaped with nothing else", "GW-2"),
    ("exterior.graveyard", "exterior", r"The graveyard holds", "SW-9"),
]
_RULE_RX = [(r, c, re.compile(p), fb) for r, c, p, fb in RULES]


def rule_of(f):
    """The rule a finding comes under (RULES), or '<check>.other'."""
    if f.get("rule"): return f["rule"]
    for r, c, rx, _ in _RULE_RX:
        if c == f["check"] and rx.search(f["msg"]): return r
    return f["check"] + ".other"


ALL = [check_setup, check_minimap, check_composition, check_wall_pieces, check_wall_shapes, check_boundary, check_doors,
       check_kits, check_objects, check_doorways, check_routes, check_story_gates, check_floors, check_thresholds,
       check_rooms, check_identity, check_pieces, check_density, check_exterior]


def run_all(m, base, only=None):
    ctx = Context(m)
    findings = []
    for chk in ALL:
        if only and chk.__name__.replace("check_", "") not in only: continue
        findings += chk(m, ctx, base)
    for f in findings:
        if f["severity"] != "info": f["rule"] = rule_of(f)
    return findings, ctx
