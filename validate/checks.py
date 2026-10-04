"""The checks. Each takes a MapData (and the shared Context) and returns findings:
dict(check, severity, msg, x, y) with x, y in world pixels (None when map-wide).

Severities:
  error   - a defect the player will see or hit (black wall, see-through gap, hole to the void,
            broken door, misaligned kit, blocked doorway, ...). Westwood's maps have essentially none.
  warning - outside the range Westwood's single-player maps stay within (density, sizes, blends).
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
        # an item on a table stands in the table's blocked cells: reachable when the player can stand beside it
        beside = any((c[0] + a, c[1] + b) in ctx.walk for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2))
        if important and not m.is_door(o) and not swims_or_flies and not beside and ctx.starts:
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


def find_rooms(m):
    """Enclosed areas of 2..400 floor tiles (same definition as rules/rooms.py), with their objects. A
    room the design declared (declared_rooms) carries its record as r["declared"]."""
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
    decl = declared_rooms(m)
    for r in rooms:
        r["tiles"] = sum(1 for p in r["cells"] if p in m.tiles)
        if r["enclosed"] and 2 <= r["tiles"] <= 400:
            votes = collections.Counter(decl[p]["number"] for p in r["cells"] if p in decl)
            if votes:
                num, n = votes.most_common(1)[0]
                if n * 2 >= r["tiles"]:
                    r["declared"] = next(rec for rec in decl.values() if rec["number"] == num)
            out.append(r)
    return out


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


IDENTITY_ALIASES = {"bedroom": ("dwelling",), "living_room": ("dwelling",), "storeroom": ("ore_store",),
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
    for r in find_rooms(m):
        kind, furniture = room_kind(r)
        wkind = WESTWOOD_KIND.get(kind, kind)
        k = kinds.get(wkind)
        if not k or k["n"] < 4 or "samples" not in k or kind in ("other", "empty"): continue
        x, y = centre(r["cells"])
        near = similar_rooms(k["samples"], r["tiles"])
        hi = near[min(len(near) - 1, int(0.95 * len(near)))]
        lo = near[int(0.05 * len(near))]
        if furniture > max(hi, 2):
            out.append(F("rooms", "warning", f"{kind} room ({r['tiles']} tiles) holds {furniture} pieces of furniture; "
                         f"Westwood's {wkind} rooms of a similar size hold at most about {hi}.", x, y))
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
    for r in find_rooms(m):
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
        tables = [o for o in objs if RT.family(o["type"]) in ("table", "desk", "counter_bar", "counter_shop")]
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


def _half_uv(o):
    if o["ext"] == "BOX": return (o["ex"] or 0) / 2 / 16.26, (o["ey"] or 0) / 2 / 16.26
    return (o["ex"] or 0) / 16.26, (o["ex"] or 0) / 16.26


def room_arrangement(m):
    """Whether a room is laid out as a whole, from the TreePlace v0.1 playtest. Westwood never does the
    first four (0 cases on its 120 single-player maps):
    - food lying by a table (Nox draws items at floor level: it reads as dropped);
    - a long table seated only at its ends (75% of Westwood's chairs at long tables stand along the sides);
    - a bunk room of mixed bed kinds;
    - beds scattered instead of lined up (3 of Westwood's 14 rooms with 3+ beds).
    Also checked:
    - a table with no seats in a room for sitting and eating (dining hall, tavern, barracks);
    - furniture filling only one end of a room;
    - open torches inside a house. This is the user's house rule; Westwood does it in 35 rooms."""
    out = []
    for r in find_rooms(m):
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
            elif max(us) - min(us) > 1.2 and max(vs) - min(vs) > 1.2:
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
            _, furniture = room_kind(r)
            if k and "samples" in k:
                near = similar_rooms(k["samples"], r["tiles"])
                med = near[len(near) // 2]
                if furniture < med:
                    out.append(F("composition", "warning", f"{kind.replace('_', ' ')} room ({r['tiles']} tiles) is sparse: {furniture} "
                                 f"pieces, fewer than half of Westwood's of a similar size ({med}) (house rule from the "
                                 f"TreePlace room review: rooms at Westwood's median and below read as empty).", x0, y0))
    return out


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
    for o in m.objects:
        mt = BUNCH_RE.match(o["type"])
        if mt: groups[mt.group(1)].append(o)
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


ALL = [check_setup, check_composition, check_wall_pieces, check_wall_shapes, check_boundary, check_doors, check_kits,
       check_objects, check_doorways, check_floors, check_rooms, check_density]


def run_all(m, base, only=None):
    ctx = Context(m)
    findings = []
    for chk in ALL:
        if only and chk.__name__.replace("check_", "") not in only: continue
        findings += chk(m, ctx, base)
    return findings, ctx
