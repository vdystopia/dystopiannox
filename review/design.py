"""Design-level measurements of outdoor areas: the qualities the DysVale playtest found missing.

Flow (roads and paths):
  path_share          share of outdoor ground that is path (dirt, cobble or paving on a grass map)
  path_connected      share of path tiles in the largest connected path network
  doors_on_path       share of doors to the outside with a path tile at the doorstep (within 2 cells)
Vegetation (structure, not scatter):
  tree_clustering     Clark-Evans index of trees: 1 = random scatter, below 1 = clumped (groves, lines)
  tree_edge_share     share of trees within 3 cells of a wall or the map's edge (tree lines)
  plant_same_type     share of small plants whose nearest small plant is the same type (single-type clumps)
Spacing:
  road_near_water     share of path tiles within 2 tiles of water (Westwood keeps roads clear of banks
                      except where they cross; crowded bands of blends look messy)
Buildings:
  building_spacing    median gap between neighbouring buildings, in cells (compact towns are close)

Outdoor ground = floor tiles outside rooms, excluding water, lava, void, facades and interior floors.
"""
import collections, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "validate"))
import mapdata as md
import checks as C
import decoration as D

FAMILY = md.rules("floors")["material_family"]
NOT_GROUND = {"water", "lava", "void", "facade", "interior_wood", "interior_rug", "tile", "bones"}
PATH_FAMILIES = {"dirt", "cobble", "brick", "dungeon_stone"}
SIDES = ((1, -1), (-1, -1), (1, 1), (-1, 1))
NAMES = dict(path_share="Path share of outdoor ground", path_connected="Paths joined into one network",
             doors_on_path="Outside doors with a path at the doorstep", tree_clustering="Tree clustering (1 = random scatter)",
             tree_edge_share="Trees lining walls and edges", plant_same_type="Small plants in single-type clumps",
             building_spacing="Gap between neighbouring buildings (cells)",
             road_near_water="Road tiles crowding the water (within 2 tiles)")


def family(mat):
    return FAMILY.get(mat, "other")


class Outdoor:
    """Outdoor ground, paths, buildings and vegetation of one map."""

    def __init__(self, m):
        self.m = m
        self.rooms = C.find_rooms(m)
        room_cells = set()
        for r in self.rooms: room_cells.update(r["cells"])
        self.room_of = {c: i for i, r in enumerate(self.rooms) for c in r["cells"]}
        self.ground = {t: d["material"] for t, d in m.tiles.items()
                       if family(d["material"]) not in NOT_GROUND and (t[0] + 1, t[1] + 1) not in room_cells}
        fams = collections.Counter(family(mt) for mt in self.ground.values())
        self.base_family = fams.most_common(1)[0][0] if fams else None
        # a path is ground of a path family that differs from the dominant ground (grass towns: dirt and cobble)
        self.paths = {t for t, mt in self.ground.items()
                      if family(mt) in PATH_FAMILIES and family(mt) != self.base_family}
        self.deco = collections.defaultdict(list)
        for o in m.objects:
            cat = D.classify({"type": o["type"], "class": o["cls"], "xtype": o["xtype"]})
            if cat and m.tile_at_cell(m.cell_of(o["x"], o["y"])) in self.ground:
                self.deco[cat].append(o)

    # ---- flow -------------------------------------------------------------------------------------
    def path_components(self):
        left, comps = set(self.paths), []
        while left:
            s = left.pop(); q = [s]; n = 1
            while q:
                x, y = q.pop()
                for dx, dy in SIDES:
                    t = (x + dx, y + dy)
                    if t in left: left.remove(t); q.append(t); n += 1
            comps.append(n)
        return sorted(comps, reverse=True)

    def outside_doors(self):
        """Doors with one side in a room and the other side on outdoor ground: (door, outside cell)."""
        out = []
        for d in self.m.doors:
            g = d["gap"]
            sides = [(g[0] + a, g[1] + b) for a, b in md.N4]
            inside = [c for c in sides if c in self.room_of]
            outside = [c for c in sides if c not in self.room_of and self.m.tile_at_cell(c) in self.ground]
            if inside and outside: out.append((d, outside[0]))
        return out

    def doors_on_path(self):
        doors = self.outside_doors()
        if not doors: return None
        hit = 0
        for d, c in doors:
            near = {(c[0] + a, c[1] + b) for a in range(-3, 3) for b in range(-3, 3)}
            hit += any(t in self.paths for t in near)
        return hit / len(doors)

    # ---- vegetation ---------------------------------------------------------------------------------
    def clark_evans(self, objs):
        if len(objs) < 10 or not self.ground: return None
        area = len(self.ground) * 2 * md.CELL ** 2            # a tile covers 2 cells' area
        pts = [(o["x"], o["y"]) for o in objs]
        grid = collections.defaultdict(list)
        for i, (x, y) in enumerate(pts): grid[(int(x // 100), int(y // 100))].append(i)
        dists = []
        for i, (x, y) in enumerate(pts):
            best, r = None, 1
            while best is None and r < 30:
                for gx in range(int(x // 100) - r, int(x // 100) + r + 1):
                    for gy in range(int(y // 100) - r, int(y // 100) + r + 1):
                        for j in grid.get((gx, gy), ()):
                            if j != i:
                                dd = math.hypot(pts[j][0] - x, pts[j][1] - y)
                                if best is None or dd < best: best = dd
                r += 1
            if best is not None: dists.append(best)
        expected = 0.5 / math.sqrt(len(pts) / area)
        return (sum(dists) / len(dists)) / expected if dists else None

    def edge_share(self, objs, cells=3):
        if len(objs) < 10: return None
        m = self.m
        n = 0
        for o in objs:
            cx, cy = m.cell_of(o["x"], o["y"])
            n += any((cx + a, cy + b) in m.walls or (cx + a, cy + b) not in m.cover
                     for a in range(-cells, cells + 1) for b in range(-cells, cells + 1))
        return n / len(objs)

    def same_type(self):
        small = self.deco["plant"] + self.deco["flower_tuft"]
        if len(small) < 10: return None
        same = tot = 0
        for o in small:
            best, bt = None, None
            for p in small:
                if p is o: continue
                dd = math.hypot(p["x"] - o["x"], p["y"] - o["y"])
                if dd < 80 and (best is None or dd < best): best, bt = dd, p["type"]
            if bt is not None:
                tot += 1; same += bt == o["type"]
        return same / tot if tot else None

    # ---- buildings ----------------------------------------------------------------------------------
    def buildings(self):
        """Groups of rooms joined by shared walls or doors (as in rules/rooms.py)."""
        parent = list(range(len(self.rooms)))

        def find(i):
            while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
            return i
        wall_owner = {}
        for i, r in enumerate(self.rooms):
            for (x, y) in r["cells"]:
                for a, b in md.N4:
                    w = (x + a, y + b)
                    if w in self.m.walls or w in self.m.door_gaps:
                        if w in wall_owner: parent[find(i)] = find(wall_owner[w])
                        else: wall_owner[w] = i
        groups = collections.defaultdict(set)
        for i, r in enumerate(self.rooms): groups[find(i)].update(r["cells"])
        return [g for g in groups.values() if len(g) >= 16]

    def building_spacing(self):
        bs = self.buildings()
        if len(bs) < 3: return None
        pts = [list(b)[::max(1, len(b) // 60)] for b in bs]   # sample cells of each footprint
        gaps = []
        for i, a in enumerate(pts):
            best = min(min(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p in a for q in b) for j, b in enumerate(pts) if j != i)
            gaps.append(best / 2)                              # 4-step distance -> approx. cells
        return sorted(gaps)[len(gaps) // 2]

    def metrics(self):
        comps = self.path_components()
        trees = self.deco["tree"]
        return dict(
            outdoor_tiles=len(self.ground), trees=len(trees), buildings=len(self.buildings()),
            path_share=round(len(self.paths) / len(self.ground), 3) if self.ground else None,
            path_connected=round(comps[0] / len(self.paths), 3) if len(self.paths) >= 20 else None,
            doors_on_path=round(self.doors_on_path(), 3) if self.doors_on_path() is not None else None,
            tree_clustering=r3(self.clark_evans(trees)),
            tree_edge_share=r3(self.edge_share(trees)),
            plant_same_type=r3(self.same_type()),
            building_spacing=r3(self.building_spacing()),
            road_near_water=r3(self.road_near_water()))

    def road_near_water(self):
        water = {t for t, d in self.m.tiles.items() if family(d["material"]) == "water"}
        if len(self.paths) < 50 or len(water) < 50: return None
        near = sum(1 for (x, y) in self.paths if any((x + a, y + b) in water for a in range(-2, 3) for b in range(-2, 3)))
        return near / len(self.paths)


def r3(v):
    return None if v is None else round(v, 3)


def is_outdoor_map(mt):
    """Maps with real outdoor areas (villages, forests): the comparison set for design metrics."""
    return mt["outdoor_tiles"] >= 800 and mt["trees"] >= 15
