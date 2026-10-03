"""The checks. Each takes a MapData (and the shared Context) and returns findings:
dict(check, severity, msg, x, y) with x, y in world pixels (None when map-wide).

Severities:
  error   - a defect the player will see or hit (black wall, see-through gap, hole to the void,
            broken door, misaligned kit, blocked doorway, ...). Westwood's maps have essentially none.
  warning - outside the range Westwood's single-player maps stay within (density, sizes, blends).
  info    - measurements, for the report.
Thresholds come from validate/baseline.json (validate/calibrate.py measures Westwood's maps).
"""
import collections, math, re
import mapdata as md
import room_types as RT
from mapdata import CELL, GRID, N4, DIAG, ARMS_OF, LINE_STEP, rules

LIGHT_NAME = re.compile(r"ColorLight|Torch|Candle|Lantern|Lamp|Sconse|Sconce|Flame|Fireplace|Brazier|Basin.*Lit|Chandelier|Lights?$", re.I)
KIT_RE = re.compile(r"^(DockDown|DockUp|RopeBridgeBroken[12]|RopeBridge[12]|LavaBridge[12])(.*?)(Front|Back)?$")
MP_ONLY = re.compile(r"^(Flag|GameBall|Crown|TeamBase|.*FlagBase)$")
NATURAL_WALL = re.compile(r"Cave|Rock|Dirt|Root|Tree|Decidious|Coni-|Aspen|Hedge|Shrub|Thorn|Volcano|IceWall|Shard|Mine", re.I)
WATER_RE = re.compile(r"Water", re.I)
TRAVEL = ("TRANSPORTER", "ELEVATOR", "ELEVATOR_SHAFT")
FLOOR_FURNITURE = {"bed", "nightstand", "counter_bar", "counter_shop", "table", "chair", "bench", "desk", "stove", "storage"}


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


def door_kind(t):
    """'double' (Westwood never puts it in a 1-cell opening), 'single' (never in an unpaired 2-cell
    opening), 'either' (Westwood uses both), or None for types with no evidence."""
    r = rules("doors")["types"].get(t)
    if not r: return None
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
        kind = door_kind(o["type"])
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
            if other not in gaps:
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
            out.append(F("objects", "warning", f"{o['type']} stands inside a wall piece.", o["x"], o["y"]))
        swims_or_flies = "AIRBORNE" in o["flags"] or WATER_RE.search(m.floor_at(o["x"], o["y"]) or "")
        if important and not m.is_door(o) and not swims_or_flies and c not in ctx.walk and ctx.starts:
            unreach.append(o)
    if unreach:
        sev = "info" if scripted else "error"
        for o in unreach[:25]:
            out.append(F("reachability", sev, f"{o['type']} cannot be reached from the player start.", o["x"], o["y"]))
        if len(unreach) > 25:
            out.append(F("reachability", sev, f"... and {len(unreach) - 25} more unreachable objects."))
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
def find_rooms(m):
    """Enclosed areas of 2..400 floor tiles (same definition as rules/rooms.py), with their objects."""
    blocked = set(m.walls) | set(m.door_gaps)
    comp = {}; rooms = []
    for start in m.cover:
        if start in comp or start in blocked: continue
        cid = len(rooms); comp[start] = cid; q = [start]; cells = []; enclosed = True
        while q:
            p = q.pop(); cells.append(p)
            for dx, dy in N4:
                n = (p[0] + dx, p[1] + dy)
                if not (0 <= n[0] < GRID and 0 <= n[1] < GRID) or n not in m.cover:
                    enclosed = False; continue
                if n in blocked or n in comp: continue
                comp[n] = cid; q.append(n)
        rooms.append(dict(cells=cells, enclosed=enclosed, objects=[]))
    for o in m.objects:
        cid = comp.get(m.cell_of(o["x"], o["y"]))
        if cid is not None: rooms[cid]["objects"].append(o)
    out = []
    for r in rooms:
        r["tiles"] = sum(1 for p in r["cells"] if p in m.tiles)
        if r["enclosed"] and 2 <= r["tiles"] <= 400: out.append(r)
    return out


def room_profile(r):
    fam = collections.Counter(RT.family(o["type"]) for o in r["objects"])
    fam.pop(None, None)
    npcs = {"shopkeeper": sum(1 for o in r["objects"] if RT.SHOPKEEPER.match(o["type"]))}
    kind = RT.classify(fam, npcs)
    furniture = sum(n for f, n in fam.items() if f in RT.BLOCKING_FAMILIES)
    return kind, furniture


def similar_rooms(samples, tiles):
    """Westwood rooms of the kind with a similar floor area (widening until there are enough)."""
    for f in (1.6, 2.5, 4.0):
        near = [n for t, n in samples if tiles / f <= t <= tiles * f]
        if len(near) >= 6: return sorted(near)
    return sorted(n for _, n in samples)


IDENTITY_ALIASES = {"bedroom": ("dwelling",), "living_room": ("dwelling",)}


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
    for r in find_rooms(m):
        kind, furniture = room_profile(r)
        k = kinds.get(kind)
        if not k or k["n"] < 4 or "samples" not in k or kind in ("other", "empty"): continue
        x, y = centre(r["cells"])
        near = similar_rooms(k["samples"], r["tiles"])
        hi = near[min(len(near) - 1, int(0.95 * len(near)))]
        lo = near[int(0.05 * len(near))]
        if furniture > max(hi, 2):
            out.append(F("rooms", "warning", f"{kind} room ({r['tiles']} tiles) holds {furniture} pieces of furniture; "
                         f"Westwood's {kind} rooms of a similar size hold at most about {hi}.", x, y))
        elif furniture < lo and furniture < 2:
            out.append(F("rooms", "warning", f"{kind} room ({r['tiles']} tiles) is nearly bare ({furniture} pieces); "
                         f"Westwood's of a similar size hold at least {lo}.", x, y))
        # identity: furniture that has no place in this kind of room (a barrel in a bedroom)
        stray = identity_strays(kind, r["objects"])
        if stray:
            out.append(F("rooms", "warning", f"{kind} room holds {', '.join(sorted(stray))}, which "
                         f"{'does' if len(stray) == 1 else 'do'} not belong in a {kind.replace('_', ' ')} "
                         f"(room identities: mapgen/kit/identity.py).", x, y))
        tlo, thi = k["tiles"]
        if r["tiles"] < tlo:
            out.append(F("rooms", "warning", f"{kind} room is small for its kind: {r['tiles']} tiles "
                         f"(Westwood's: {tlo:.0f} to {thi:.0f}).", x, y))
        elif r["tiles"] > thi:
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


ALL = [check_setup, check_wall_pieces, check_wall_shapes, check_boundary, check_doors, check_kits,
       check_objects, check_doorways, check_floors, check_rooms, check_density]


def run_all(m, base, only=None):
    ctx = Context(m)
    findings = []
    for chk in ALL:
        if only and chk.__name__.replace("check_", "") not in only: continue
        findings += chk(m, ctx, base)
    return findings, ctx
