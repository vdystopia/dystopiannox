"""The steps every story map shares (PROCESS.md, "Story"), taken out of Thornwick so the next map starts from them.

    sm = StoryMap(spec, rng, land, identity)
    placed = sm.place_buildings(no_build={"grove": 13})       # from the square outwards, never on the story's places
    sm.connect_and_furnish()
    sm.keep_open({"camp": 8, "den": 5})                       # before carve's thickets: the stages stay open ground
    halves = sm.gate_across(("gate", "north"), prefix="NorthGate")
    sm.person("Con02a", "Bryan", x, y, "Tobin", face=(fx, fy))
    sm.shops(WARES, GREET)
    sm.townsfolk(FOLK, rumours, q)
    sm.wild({"Bat": 3, "Spider": 1}, avoid=[...])
    sm.exit_to("north", "TNorth")

Coordinates: squares (i, j) for the land, world pixels for objects, as in kit/layout.py.
"""
import math, os, random, re, zlib
from nox import CELL
from kit.identity import BUILDINGS, role_size
from kit.layout import square_tile, square_px, px_square, point_cell
from kit.village import _squares_of
from kit.building import generate_building
from kit.originality import furnish_original
from kit.npcs import Population, facing
from kit.walkways import Ground, Router, CELL as WCELL

STOCK = r"C:\GOG Games\Nox\maps"

# Townsfolk's given names: the dialogue window titles a creature with the string "NPC:<script name>". None of these
# is in Westwood's table (nox.csf NPC:...) or given to a story character in a design. The donor's body picks the
# list: Westwood's Maiden clones are women.
WOMEN_DONORS = {"Lydia", "Tanya", "Julie", "Gretchen", "Maiden", "Kayla", "Kristine", "Melissa", "Shari", "Joyce",
                "Eowynn", "Jennifer", "Evelyn"}


def is_woman(src):
    """Whether a donor's body is a woman's: Westwood's Maiden clones (Wiz02A's Maiden1-9, TowerMaiden, Con06a's
    Townswoman1-6) and the named ones."""
    return src in WOMEN_DONORS or src.startswith(("Maiden", "TowerMaiden", "Townswoman"))
NAMES = {
    "f": ["Aelis", "Brida", "Cerys", "Dagny", "Elswyth", "Fenna", "Gisla", "Hild", "Ide", "Jorunn", "Ketta", "Leofa",
          "Nesta", "Odile", "Petra", "Rowena", "Sabine", "Tilde", "Una", "Ysolde", "Alys", "Berta", "Clemence",
          "Dorcas", "Elin", "Frida", "Greta", "Helga", "Isolde", "Liesel", "Marta", "Norah", "Runa"],
    "m": ["Aldo", "Bram", "Cedric", "Dunstan", "Egil", "Fulk", "Godric", "Hamon", "Ivo", "Jory", "Kester", "Leofric",
          "Merek", "Nils", "Oswin", "Piers", "Randal", "Sigurd", "Ulric", "Wat", "Yvain", "Alard", "Bennet", "Colm",
          "Drogo", "Emrys", "Fergus", "Ingram", "Joss", "Lambert", "Mabon", "Rolf"],
}


class StoryMap:
    def __init__(self, spec, rng, land, identity):
        self.m, self.rng, self.land, self.ID = spec, rng, land, identity
        self.placed, self.by_role, self.missed = [], {}, []
        self._movers = set()          # people the scripts walk: where they were placed is no one's standing spot
        self.pop = Population(spec, rng)
        self.B = self.pop.behaviours
        self.unsafe = []                     # [(world px, radius px)]: places townsfolk and the watch never stop at

    def keep_folk_away(self, centre, r):
        """No townsperson's or watchman's stop within `r` squares of `centre` (squares): a camp of foes at the town's
        edge (Ambermere: a graveyard's gate by the diggers' camp had become a stop on the watch's beat). Call it before
        townsfolk() and beat()."""
        self.unsafe.append((square_px(*centre), r * 32.5))

    # ---- buildings -------------------------------------------------------------------------------------------------
    def place_buildings(self, no_build=None, scale=1.0, square_area="town", first=(), centred=None):
        """Every building of the identity, public ones on the square first, then by size; none within the radius
        (squares) of the named areas in `no_build` (the story's wild places), which stay free for the forest after.
        square_area: the area whose paved square (Land.paint_square) the public buildings face (a castle's
        courtyard). first: areas whose buildings are placed before all others (a hamlet down a road from the town,
        whose few lots the town's houses would otherwise take: Ambermere's fishers). centred: {area: toward area}:
        the area's building stands centred on the area's middle, its door on the side toward the other area (a
        lone structure at the end of its road, as kit/biome.Dresser.structure places one: Ambermere's barrow)."""
        m, land, rng = self.m, self.land, self.rng
        held = set()
        for k_, r_ in (no_build or {}).items():
            c_ = land.areas[k_]["c"]
            held |= {s for s in land.squares if math.hypot(s[0] - c_[0], s[1] - c_[1]) <= r_} - land.taken
        land.taken |= held
        B_ = self.ID.buildings
        centred = centred or {}
        order = sorted(range(len(B_)), key=lambda k: (B_[k].area not in first, B_[k].area not in centred,
                                                      BUILDINGS[B_[k].role]["faces"] != "square",
                                                      -BUILDINGS[B_[k].role]["size"][0], k))
        for k in order:
            bid = B_[k]
            role = BUILDINGS[bid.role]
            size0, min_units0 = role_size(role)
            program = [kind for kind, _ in role["rooms"]]
            b = None
            # a house too small for its rooms at their least sizes is tried a size up before a size down
            for shrink in (1.0, 1.12, 0.92, 1.25, 0.84):
                size = (2 * round(size0[0] * scale * shrink / 2), 2 * round(size0[1] * scale * shrink / 2))
                lots = land.square_lots(size) if role["faces"] == "square" and bid.area == square_area else []
                if bid.area in centred:
                    lots = self._centred_lots(bid.area, centred[bid.area], size)
                else:
                    lots += land.lots(bid.area, size)
                for origin, side in lots:
                    if not land.lot_free(origin, size, margin=1): continue
                    b = generate_building(m, rng, origin, size, bid.style or role["style"], program=program, entrance_side=side,
                                          building_id=f"B{k}", occupied={square_tile(*s) for s in land.taken},
                                          tries=24 if size[0] <= 30 else 12,       # small houses: more layouts to try
                                          shape=role.get("shape"), min_units=int(min_units0 * (scale * shrink) ** 2))
                    if b: break
                if b: break
            if not b:
                self.missed.append(bid.role)
                print(f"could not place the {bid.role} in the {bid.area}"); continue
            land.take_cells(b.cells, margin=1)
            land.wall_cells |= {c for c in m.wallmap}
            land.taken_strict |= _squares_of(b.footprint)
            self.placed.append((bid, b))
        self.by_role = {}
        for bid, b in self.placed: self.by_role.setdefault(bid.role, b)
        land.taken -= held
        self._blend_outside_floors()
        return self.placed

    def _centred_lots(self, area, toward, size):
        """Origins (uv) for a building centred on `area`'s middle, nudged a little either way, its entrance on the
        side facing `toward`."""
        land = self.land
        cx, cy = land.areas[area]["c"]
        tx, ty = land.areas[toward]["c"]
        dx, dy = tx - cx, ty - cy
        side = ("u_max" if dx > 0 else "u_min") if abs(dx) >= abs(dy) else ("v_max" if dy > 0 else "v_min")
        W, H = size
        out = []
        for r in range(0, 5):
            for a in range(-r, r + 1):
                for b in range(-r, r + 1):
                    if max(abs(a), abs(b)) != r: continue
                    out.append(((2 * round(cx - W / 4) + 2 * a, 2 * round(cy - H / 4) + 2 * b), side))
        return out

    def _blend_outside_floors(self, priority=8):
        """Floors laid outside the buildings (the paving a building style puts round its walls) blend into the land
        in whatever palette: a biome's blend list knows its own floors, not the houses' paving (Emberhollow:
        GalavaBrownMarble against VolcanicCraggy, a hard seam; Rimehold: GreenBrick against the rock paths)."""
        m = self.m
        inside = set()
        for bid, b in self.placed:
            inside |= set(b.footprint)
            for r in b.rooms: inside |= set(r.tiles)
        for mat in {mat for t, mat in m.floor.items() if t not in inside}:
            if mat not in m.blend: m.blending(mat, priority)

    def connect_and_furnish(self, style="town", path_material="DirtDark2"):
        """Paths from every door to the roads (dead ends trimmed), then every room furnished by its identity."""
        m, land = self.m, self.land
        land.clear_walls(m)
        door_paths = set()
        for bid, b in self.placed:
            foot = _squares_of(b.footprint)
            for d in b.entrances:
                path = land.connect_door(m, d, foot, material=path_material)
                if path is None: print(f"  no path from the {bid.role}'s door")
                else: door_paths |= set(path)
        land.trim_dead_ends(m, keep=door_paths)
        for bid, b in self.placed:
            for room in b.rooms:        # a role in a culture's style is furnished in that culture (a barrow: lotd)
                furnish_original(m, room, kind=room.kind, rng=self.rng, style=BUILDINGS[bid.role].get("furnish") or style)

    def room_of(self, role, kind):
        b = self.by_role.get(role)
        return next((r for r in (b.rooms if b else []) if r.kind == kind), None)

    def building_in(self, area):
        return next((b for bid, b in self.placed if bid.area == area), None)

    def outside_door(self, role=None, building=None):
        """World px just outside a building's main door."""
        b = building or self.by_role.get(role)
        if not b: return None
        o_ = self.land.door_outside(b.entrances[0], _squares_of(b.footprint))
        return o_ and square_px(o_[0] + 0.5, o_[1] - 0.5)

    def free_px(self, room, prefer=None, clear=30.0):
        """A floor point of the room off the walls with nothing within `clear` px, nearest `prefer` (default the
        room's middle)."""
        m = self.m
        pts = [((x + 1) * CELL, (y + 1) * CELL) for x, y in room.tiles]
        cx = prefer or (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        objs = [(o["x"], o["y"]) for o in m.d["objects"]]
        off_wall = lambda p: not any((int(p[0] // CELL) + a, int(p[1] // CELL) + b) in m.wallmap
                                     for a in (-1, 0, 1) for b in (-1, 0, 1))
        for p in sorted(pts, key=lambda p: (p[0] - cx[0]) ** 2 + (p[1] - cx[1]) ** 2):
            if off_wall(p) and all((p[0] - a) ** 2 + (p[1] - b) ** 2 > clear * clear for a, b in objs): return p
        return pts[0]

    # ---- the land ----------------------------------------------------------------------------------------------------
    def keep_open(self, stages):
        """The story's places stay open ground: {area: radius in squares} taken, so no clump of forest or tree goes
        there. Returns the squares of the forest paths (passages without a road), for thickets(avoid=)."""
        land = self.land
        for k_, r_ in stages.items():
            c_ = land.areas[k_]["c"]
            land.taken |= {s for s in land.squares if math.hypot(s[0] - c_[0], s[1] - c_[1]) <= r_}
        lanes = set()
        for l_ in land.links:
            if l_["road"]: continue
            for pi_, pj_ in l_["path"]:
                ci, cj = int(math.floor(pi_)), int(math.floor(pj_)) + 1
                lanes |= {(ci + a, cj + b) for a in (-1, 0, 1) for b in (-1, 0, 1)}
        return lanes & land.squares

    def road_near(self, sq):
        return min(self.land.roads, key=lambda s: (s[0] - sq[0]) ** 2 + (s[1] - sq[1]) ** 2)

    def hidden_spot(self, near, r=(4, 9)):
        """A square 1-2 from the forest wall, off the ways, r squares from `near`: where a cache is hidden."""
        land = self.land
        edge = land.edge_distance()
        c = [s for s, d in edge.items() if 1 <= d <= 2 and s not in land.taken and s not in land.roads
             and r[0] <= math.hypot(s[0] - near[0], s[1] - near[1]) <= r[1]]
        return self.rng.choice(c) if c else None

    # ---- a gate across a road ----------------------------------------------------------------------------------------
    def _wall_across(self, at_sq, along, material, gate, prefix, dry=False):
        m, land = self.m, self.land
        i0, j0 = at_sq
        pts = []
        for sgn in (-1, 1):
            k = 0 if sgn > 0 else -1
            while abs(k) < 40:
                p = (i0, j0 + k) if along == "j" else (i0 + k, j0)
                nb = [(p[0] - 1, p[1]), (p[0], p[1])] if along == "j" else [(p[0], p[1]), (p[0], p[1] + 1)]
                if not any(s in land.squares for s in nb): break
                # never into a building or its margin
                if any((s[0] + a, s[1] + b) in land.taken_strict for s in nb for a in (-1, 0, 1) for b in (-1, 0, 1)):
                    return None
                pts.append(p); k += sgn
                if abs(k) > 1 and point_cell(*p) in m.wallmap: break        # it meets the forest
        pts = sorted(set(pts), key=lambda p: p[1] if along == "j" else p[0])
        if not 4 <= len(pts) <= 40: return None
        if dry: return True
        for p in pts:
            c = point_cell(*p)
            if c not in m.wallmap: m.wall(*c, material)
        mid = min(range(len(pts) - 1), key=lambda n: abs((pts[n][1] if along == "j" else pts[n][0]) - (j0 if along == "j" else i0)))
        a, b2 = point_cell(*pts[mid]), point_cell(*pts[mid + 1])
        line = "\\" if (b2[0] - a[0], b2[1] - a[1]) == (1, 1) else "/"
        n0 = len(m.d["objects"])
        m.door(gate, a, line)
        halves = [o for o in m.d["objects"][n0:] if o["type"] == gate]
        for k_, o in enumerate(halves):
            o["scr"] = f"{prefix}{k_ + 1}"
            o.setdefault("xfer", {})["LockType"] = "Mechanism"
        for p in pts: land.taken.add(p)
        return halves, pts

    def gate_across(self, link, prefix="Gate", material="Cobblestone", gate="WoodAndSteelHalfDoor",
                    ts=(0.35, 0.45, 0.25, 0.55, 0.15, 0.65)):
        """A wall across the road of `link` (a, b), from forest to forest, square to the road as drawn on screen, with
        a double gate locked by mechanism (script names <prefix>1, <prefix>2; A.unlock opens them). Tried at the
        fractions `ts` along the link from a, where no building is in the way. Returns (halves, wall points, square)."""
        land = self.land
        lk = next(l for l in land.links if {l["a"], l["b"]} == set(link))
        path = lk["path"] if lk["a"] == link[0] else lk["path"][::-1]

        def across(t):
            k = int(t * (len(path) - 1))
            a_, b_ = path[max(0, k - 4)], path[min(len(path) - 1, k + 4)]
            ax, ay = square_px(*a_); bx, by = square_px(*b_)
            rx, ry = bx - ax, by - ay

            def cos_(d):
                c0, c1 = point_cell(0, 0), point_cell(*d)
                wx, wy = c1[0] - c0[0], c1[1] - c0[1]
                return abs(rx * wx + ry * wy) / ((math.hypot(rx, ry) or 1) * (math.hypot(wx, wy) or 1))
            return "j" if cos_((0, 1)) <= cos_((1, 0)) else "i"

        for t in ts:
            sq = self.road_near(path[int(t * (len(path) - 1))])
            if self._wall_across(sq, across(t), material, gate, prefix, dry=True):
                res = self._wall_across(sq, across(t), material, gate, prefix)
                return res[0], res[1], sq
        raise AssertionError(f"no place for a gate on the {link} road")

    @staticmethod
    def arrival(map_name):
        """Where a player arriving in map_name stands: its PlayerStart (world px), read from the built map
        (mapgen/out/*/<map_name>.map) or the installed one. In solo play an exit drops the player at its ExitX/ExitY
        in the next map (opennox save.go nox_xxx_saveMakePlayerLocation_4DB600); 0, 0 is the map's corner, the void."""
        import glob, sys
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cands = glob.glob(os.path.join(here, "out", "*", map_name + ".map")) +             [os.path.join(STOCK, map_name, map_name + ".map")]
        sys.path.insert(0, os.path.join(os.path.dirname(here), "validate"))
        import mapdata as MD
        for p in cands:
            if not os.path.exists(p): continue
            st = next((o for o in MD.load(p).objects if o["type"] == "PlayerStart"), None)
            if st: return (st["x"], st["y"])
        raise AssertionError(f"no built {map_name}.map with a PlayerStart: build the next map first (the exit needs "
                             f"its arrival point)")

    def exit_to(self, area, map_name, prefix="Exit", n=3, arrive=None):
        """Exit areas (InvisibleExitArea) where the road reaches `area` near the forest's edge, leading to map_name,
        the player arriving at `arrive` (world px; default the next map's PlayerStart, which must be built).
        Script names <prefix>1..n (A.disable/A.enable)."""
        ax, ay = arrive or self.arrival(map_name)
        land = self.land
        edge = land.edge_distance()
        c = land.areas[area]["c"]
        sq = min(land.roads, key=lambda s: math.hypot(s[0] - c[0], s[1] - c[1]) + 0.2 * edge.get(s, 0))
        ex, ey = square_px(sq[0] + 0.5, sq[1] - 0.5)
        names = []
        for k in range(n):
            off = 18 * (k - (n - 1) / 2)
            self.m.obj_px("InvisibleExitArea", ex + off, ey + off, scr=f"{prefix}{k + 1}",
                          xfer={"MapName": f"{map_name}.map", "ExitX": float(ax), "ExitY": float(ay)})
            names.append(f"{prefix}{k + 1}")
        return names

    # ---- people ------------------------------------------------------------------------------------------------------
    def person(self, donor, scr, x, y, name, face=None, action=4, immortal=True):
        """A person cloned in their clothes from a stock map (maps/<donor>/<donor>.map, script name <donor>:<scr>), named
        in this map; standing on guard (action 4) by default, facing `face`. Immortal by default, as Westwood's quest
        townsfolk are (Con02a's guards): a giver killed by a passing wolf would strand the quest."""
        xf = dict(DefaultAction=action, Aggressiveness=0.0, Immortal=bool(immortal))
        if face: xf["DirectionId"] = facing(face[0] - x, face[1] - y)
        return self.m.clone(os.path.join(STOCK, donor, donor + ".map"), f"{donor}:{scr}", x, y, name=name, xfer=xf)

    def shops(self, wares, greet, keeper=None):
        """A shopkeeper behind each counter the furnisher set (or in the forge's floor for a smithy), selling the
        role's `wares` [(count, type)] with the greeting key `greet[role]`. keeper: {role: shopkeeper type}."""
        keeper = keeper or {}
        n = 0
        for bid, b in self.placed:
            if bid.role not in wares: continue
            for room in b.rooms:
                spots = [sp for sp in (getattr(room, "spots", []) or []) if sp.get("role") in ("shopkeeper", "barkeep")]
                if not spots and room.kind != "smithy": continue
                at = spots[0]["px"] if spots else self.free_px(room)
                xs = [(x + 1) * CELL for x, _ in room.tiles]; ys = [(y + 1) * CELL for _, y in room.tiles]
                self.pop.shopkeeper(keeper.get(bid.role, "ShopkeeperYellow"), *at, wares[bid.role],
                                    greeting=greet.get(bid.role, ""), face=(sum(xs) / len(xs), sum(ys) / len(ys)))
                n += 1
                break
        return n

    def townsfolk(self, folk, centre, q=None, rumours=(), after=None, pics=(), radius=6.5, prefix="Folk", stops=(5, 7),
                  pause=(16.0, 24.0)):
        """Townspeople (clones [(donor, scr)]), each on a tour of the town's real places in Westwood's manner and the
        playtester's (2026-10-05: "walk from point a to point b and then stand still for longer"): from their home
        door to the square, a shop, the well, a garden, a neighbour's door..., `stops` places in all, along the roads
        and paths (a waypoint at each bend, three square-on through a shop's doorway), standing `pause` seconds at
        each, facing what is there; running home when a creature comes near (kit/behaviours Tour). Different people
        get different tours. The tours are laid when the scripts are written (Behaviours.files), once every wall,
        tree and bench stands. With a QuestBook q, each says its rumour (and `after`: (flag, line) once the main
        quest is done), with its portrait. Returns the square's ring (px)."""
        rng = self.rng
        ring = [square_px(centre[0] + radius * math.cos(a), centre[1] - 0.5 + radius * math.sin(a))
                for a in (k * math.pi / 4 for k in range(8))]
        # given names from their own generator, so naming them leaves the map's other draws (and its layout) unchanged
        name_rng = random.Random(zlib.crc32(self.m.d["name"].encode()))
        taken = {o.get("scr") for o in self.m.d["objects"] if o.get("scr")}
        self.folk_names = []
        people = []
        # the draws the earlier rounds-between-spots scheme made, made still, so everything placed after the townsfolk
        # (the fights, the wood's creatures) stands where it stood
        n_doors = sum(1 for bid, b in self.placed for d in b.entrances[:1]
                      if self.land.door_outside(d, _squares_of(b.footprint)))
        for k, (donor, src) in enumerate(folk):
            pool = [n for n in NAMES["f" if is_woman(src) else "m"] if n not in taken]
            name = name_rng.choice(pool) if pool else f"{prefix}{k + 1}"
            taken.add(name); self.folk_names.append(name)
            self._movers.add(name)
            x, y = ring[k % len(ring)]
            people.append(self.person(donor, src, x + rng.uniform(-10, 10), y + rng.uniform(-10, 10), name))
            rng.sample(range(n_doors), min(2, n_doors)); rng.sample(range(8), 3)
            if q and k < len(rumours):
                lines = []
                if after: lines.append(q.say(after[1], when=q.when(flag=after[0]), who=prefix))
                lines.append(q.say(rumours[k], who=prefix))
                q.talker(name, lines)
                if k < len(pics): q.portrait(name, pics[k])

        def lay():
            town = self._town(centre, radius)
            homes = [s for s in town["stops"] if s["kind"] == "home"] or [s for s in town["stops"] if s["kind"] in ("door", "shop")]
            for k, o in enumerate(people):
                name = o["scr"]
                trng = random.Random(zlib.crc32(f"{self.m.d['name']}:{name}:tour".encode()))
                home = homes[k % len(homes)] if homes else None
                tour = self._spots(town, self._pick_tour(town, trng, home, trng.randint(*stops), indoors=True))
                laid = self._lay_route(town, name + "Way", tour, trng, pause, home_kind=True)
                if not laid:
                    self.B.tour(name, [], [], fear=0.0)      # nowhere to walk: stands where it is
                    continue
                route, pauses, looks, home_wp = laid
                o["x"], o["y"] = self._at(route[0])          # starts the day at its first stop: home
                self.B.tour(name, route, pauses, looks, home=home_wp or "", fear=180.0)
        self.B.later(lay)
        return ring

    def beat(self, name, centre, radius=6.5, stops=6, pause=(8.0, 12.0)):
        """A watchman's beat (kit/behaviours Patrol): a loop through `stops` of the town's places spread wide (the
        gate, the square, far doorsteps, the yards), along the roads, standing `pause` seconds at each. The named
        person is moved to the beat's first stop. Laid when the scripts are written, as the townsfolk's tours."""
        self._movers.add(name)

        def lay():
            town = self._town(centre, radius)
            trng = random.Random(zlib.crc32(f"{self.m.d['name']}:{name}:beat".encode()))
            cand = [s for s in town["stops"] if s["kind"] != "square" or trng.random() < 0.3]
            if not cand: return
            # spread: the first stop by the gate or the far edge, then each next the farthest from those taken
            # places another watchman's beat already takes count for less: two beats share as little as they can
            used = self.__dict__.setdefault("_beat_used", set())
            fresh = lambda s: 1.0 if id(s) not in used else 0.45
            first = max(cand, key=lambda s: (s["kind"] == "gate" and id(s) not in used,
                                             math.dist(s["p"], town["c"]) * trng.uniform(0.8, 1.0) * fresh(s)))
            pick = [first]
            while len(pick) < min(stops, len(cand)):
                pick.append(max((s for s in cand if s not in pick),
                                key=lambda s: min(math.dist(s["p"], t["p"]) for t in pick) * trng.uniform(0.75, 1.0) * fresh(s)))
            used |= {id(s) for s in pick}
            laid = self._lay_route(town, name + "Beat", self._spots(town, self._order(pick, pick[0])), trng, pause)
            if not laid: return
            route, pauses, looks, _ = laid
            o = next((o for o in self.m.d["objects"] if o.get("scr") == name), None)
            if o is not None: o["x"], o["y"] = self._at(route[0])
            self.B.patrol(name, route, pauses, loop=True, looks=looks)
        self.B.later(lay)

    # ---- the town's places, and routes between them (kit/walkways) -----------------------------------------------
    LANDMARK = re.compile(r"^(Well|Fountain|Statue|Bench|LightBench|Garden|Gate$|IronFenceGate|BarredGate|Sign|"
                          r"OutdoorTrader|WaterBarrel|Anvil|Stump|WoodPile|Tombstone|Grave|Wagon|Cart|Shrine|Obelisk)")
    VISIT = ("store", "inn", "tavern", "chapel", "smithy")      # roles a townsperson steps inside
    HOMES = ("home", "cottage", "house", "farm", "hut", "mill", "woodcutter", "hunter", "fisher", "herbwife")

    def _at(self, wp_name):
        w = next(w for w in self.m.d["waypoints"] if w["name"] == wp_name)
        return w["x"], w["y"]

    def _town(self, centre, radius, reach=95.0):
        """The places townsfolk go, reachable from the square along the ground (never through a doorway) within
        `reach` (road cells cost 1, open ground 2.6): {"stops": [dict(p, look, kind, visit)], "router", "ground"}.
        Built once per centre, when the map is placed."""
        key = (round(centre[0], 2), round(centre[1], 2))
        cache = self.__dict__.setdefault("_towns", {})
        if key in cache: return cache[key]
        m, land = self.m, self.land
        g, router, locked = self._world()
        c = square_px(centre[0], centre[1] - 0.5)
        costs = router.costs_from(c, reach)
        if len(costs) < 50:                          # the centre itself is cluttered (a well): from the nearest clear cell
            near = [(c[0] + dx * WCELL, c[1] + dy * WCELL) for dx in range(-5, 6) for dy in range(-5, 6)]
            for p in sorted(near, key=lambda p: math.dist(p, c)):
                more = router.costs_from(p, reach)
                if len(more) > len(costs): costs = more
                if len(costs) >= 50: break
        reach_ok = lambda p: (int(p[0] // WCELL), int(p[1] // WCELL)) in costs
        stops = []
        clear = lambda p: g.point_ok(p[0], p[1], wall_clear=15, obj_clear=12)

        def add(p, look, kind, visit=None, gap=60.0):
            if not p or not reach_ok(p) or not clear(p): return False
            if any(math.dist(p, c_) < r_ for c_, r_ in self.unsafe): return False
            if any(math.dist(p, s["p"]) < gap for s in stops): return False
            stops.append(dict(p=p, look=look, kind=kind, visit=visit))
            return True
        # doorsteps (and, for the shops, the inn and the chapel, a step inside)
        for bid, b in self.placed:
            foot = list(b.footprint)
            bx = sum(square_px(i + 0.5, j - 0.5)[0] for i, j in _squares_of(foot)) / max(1, len(_squares_of(foot)))
            by = sum(square_px(i + 0.5, j - 0.5)[1] for i, j in _squares_of(foot)) / max(1, len(_squares_of(foot)))
            for d in b.entrances:
                dd = g.gap_door.get(d.gap)
                if not dd: continue
                (ox, oy) = dd[0]
                ps = g.passage(d.gap, (2 * ox - bx, 2 * oy - by))
                if not ps or not ps[0]: continue
                out, mid, inn = ps
                kind = "home" if bid.role in self.HOMES else "shop" if bid.role in self.VISIT else "door"
                visit = None
                if bid.role in self.VISIT and inn and not any(math.dist(dd[0], q_) < 50 for q_ in locked) and \
                        g.leg_problem(out, inn) is None:
                    deep = (inn[0] + (inn[0] - out[0]) * 1.5, inn[1] + (inn[1] - out[1]) * 1.5)
                    visit = dict(mid=mid, inn=inn, look=deep)
                add(out, (ox, oy), kind, visit, gap=30.0)
        # the square: a ring round its middle, facing in
        for a in range(8):
            ang = a * math.pi / 4 + 0.39
            p = square_px(centre[0] + radius * 0.8 * math.cos(ang), centre[1] - 0.5 + radius * 0.8 * math.sin(ang))
            add(p, c, "square", gap=70.0)
        # the town's features: the well, statues, benches, gardens, yard gates, graves, stalls
        for o in m.d["objects"]:
            t = o.get("type") or ""
            if not self.LANDMARK.match(t) or math.dist((o["x"], o["y"]), c) > reach * WCELL: continue
            best = None
            for r_ in (30, 38, 46):
                for k_ in range(12):
                    ang = k_ * math.pi / 6
                    p = (o["x"] + r_ * math.cos(ang), o["y"] + r_ * math.sin(ang))
                    cell = (int(p[0] // WCELL), int(p[1] // WCELL))
                    if cell not in costs or not clear(p): continue
                    if best is None or costs[cell] < best[0]: best = (costs[cell], p)
                if best: break
            if best: add(best[1], (o["x"], o["y"]), "gate" if "Gate" in t else "landmark", gap=90.0)
        town = dict(stops=stops, router=router, ground=g, c=c, start={}, costs=costs)
        cache[key] = town
        return town

    @staticmethod
    def _order(stops, first):
        """A short loop through the stops from `first`: nearest next, then untangled (2-opt), on straight distance."""
        rest, order = [s for s in stops if s is not first], [first]
        while rest:
            nxt = min(rest, key=lambda s: math.dist(s["p"], order[-1]["p"]))
            order.append(nxt); rest.remove(nxt)
        n = len(order)
        better = True
        while better and n > 3:
            better = False
            for i in range(1, n - 1):
                for j in range(i + 1, n):
                    a, b, c_, d = order[i - 1]["p"], order[i]["p"], order[j]["p"], order[(j + 1) % n]["p"]
                    if math.dist(a, c_) + math.dist(b, d) < math.dist(a, b) + math.dist(c_, d) - 1e-6:
                        order[i:j + 1] = order[i:j + 1][::-1]; better = True
        return order

    def _pick_tour(self, town, rng, home, n, indoors=True):
        """`n` stops for one person: home first, a place on the square, a shop, then the town's other places, in a
        loop. Different draws give different people different tours."""
        stops = [s for s in town["stops"] if s is not home]
        used = self.__dict__.setdefault("_square_used", set())
        pick = [home] if home else []
        sq = [s for s in stops if s["kind"] == "square" and id(s) not in used] or [s for s in stops if s["kind"] == "square"]
        if sq:
            s = rng.choice(sq); used.add(id(s)); pick.append(s)
        shops = [s for s in stops if s["kind"] == "shop"]
        if shops: pick.append(rng.choice(shops))
        others = [s for s in stops if s not in pick and s["kind"] != "square"]
        rng.shuffle(others)
        others.sort(key=lambda s: s["kind"] not in ("landmark", "gate"))      # the town's features before doorsteps
        k = 0
        while len(pick) < n and k < len(others):
            if rng.random() < 0.8: pick.append(others[k])
            k += 1
        if not pick: return []
        order = self._order(pick, pick[0])
        return [dict(s, visit=s["visit"] if indoors and s["visit"] and rng.random() < 0.6 else None) for s in order]

    def _lay_route(self, town, prefix, tour, rng, pause, home_kind=False):
        """Waypoints for a loop through the tour's stops: each leg routed along the roads (Router), the stop itself
        stood on for `pause` seconds facing its look point, a visit going square-on through the doorway (out, the
        opening's middle, in) and back. Stops whose legs cannot be routed are dropped. Returns (waypoint names,
        pauses, looks, home waypoint name) or None."""
        router = town["router"]
        tour = list(tour)
        while len(tour) >= 2:
            legs, bad = [], None
            for k, s in enumerate(tour):
                nxt = tour[(k + 1) % len(tour)]
                leg = router.route(s["p"], nxt["p"])
                if leg is None: bad = nxt if (k + 1) % len(tour) else s; break
                legs.append(leg)
            if bad is None: break
            tour.remove(bad)
        if len(tour) < 2: return None
        pts, pauses, looks, home_at = [], [], [], None
        for k, s in enumerate(tour):
            stay = rng.uniform(*pause)
            v = s.get("visit")
            if v:
                pts.append(s["p"]); pauses.append(0.0); looks.append(None)
                if v["mid"]: pts.append(v["mid"]); pauses.append(0.0); looks.append(None)
                spot = v.get("spot")
                if spot and math.dist(spot, v["inn"]) > 4:       # in past the threshold, then to its own spot
                    pts.append(v["inn"]); pauses.append(0.0); looks.append(None)
                    pts.append(spot); pauses.append(stay); looks.append(v["look"])
                    pts.append(v["inn"]); pauses.append(0.0); looks.append(None)
                else:
                    pts.append(v["inn"]); pauses.append(stay); looks.append(v["look"])
                if v["mid"]: pts.append(v["mid"]); pauses.append(0.0); looks.append(None)
                pts.append(s["p"]); pauses.append(0.0); looks.append(None)
            else:
                if home_kind and k == 0: home_at = len(pts)
                pts.append(s["p"]); pauses.append(stay); looks.append(s["look"])
            for p in legs[k][:-1]:
                pts.append(p); pauses.append(0.0); looks.append(None)
        names = self.pop.waypoint_path(prefix, pts)
        return names, pauses, looks, (names[home_at] if home_at is not None else None)

    # ---- standing spots: nobody shares one (playtest 2026-10-05: two people pushing each other off one stop) ---------
    SPOT_GAP = 40.0       # px between any two standing spots: a body is 24 px across
    DOORWAY_CLEAR = 26.0  # px a standing spot keeps from a doorway's passage points (out in front, middle, in behind)

    def _world(self):
        """(Ground, Router along the roads, locked doors' points): the map as it stands once everything is placed,
        built once, when the first route is laid (Behaviours.later)."""
        w = self.__dict__.get("_world_")
        if w: return w
        m, land = self.m, self.land
        g = Ground.from_spec(m)
        roads = set()
        for i, j in land.roads | land.plaza:
            x, y = square_tile(i, j)
            roads |= {(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)}
        locked = [(o["x"], o["y"]) for o in m.d["objects"]
                  if o.get("door") is not None and (o.get("xfer") or {}).get("LockType")]
        self._world_ = (g, Router(g, roads), locked)
        return self._world_

    def _claims(self):
        """Standing spots taken so far: every creature standing where it was placed (a shopkeeper, a guard at the
        gate, a quest giver), then each stop given out. Built once, with the doorways' passage points kept clear."""
        c = self.__dict__.get("_claims_")
        if c is None:
            g = self._world()[0]
            c = self._claims_ = [(o["x"], o["y"]) for o in self.m.d["objects"]
                                 if "DefaultAction" in (o.get("xfer") or {}) and o.get("scr") not in self._movers]
            self._doorways = []
            for (cx, cy), (nx, ny), half in sorted({v[0]: v for v in g.gap_door.values()}.values()):
                self._doorways += [(cx, cy), (cx + nx * 40, cy + ny * 40), (cx - nx * 40, cy - ny * 40)]
        return c

    def _free_spot(self, cands, clear):
        """The first candidate (world px) a body stands clear on that is SPOT_GAP from every spot taken and out of the
        doorways; taken. None if none is."""
        claims = self._claims()
        for p in cands:
            if not clear(p): continue
            if any(math.dist(p, q) < self.SPOT_GAP for q in claims): continue
            if any(math.dist(p, q) < self.DOORWAY_CLEAR for q in self._doorways): continue
            claims.append(p)
            return p
        return None

    def _spots(self, town, tour):
        """Each stop of a tour or beat on a standing spot of its own: round a feature (another side of the well,
        another bench), beside a doorstep rather than in front of the door, a place of its own on the square, a spot
        of its own past a shop's threshold. Stops with no spot left are dropped."""
        g, costs, router = town["ground"], town["costs"], town["router"]

        def reach(p):            # on the ground the town reaches, or a clear step off its edge (never over a fence)
            c = (int(p[0] // WCELL), int(p[1] // WCELL))
            if c in costs: return True
            return router.ok(c) and any(g.leg_problem(p, (q[0] * WCELL + WCELL / 2, q[1] * WCELL + WCELL / 2)) is None
                                        for q in ((c[0] + a, c[1] + b) for a in (-2, -1, 0, 1, 2) for b in (-2, -1, 0, 1, 2))
                                        if q in costs)
        clear = lambda p: reach(p) and g.point_ok(p[0], p[1], wall_clear=15, obj_clear=12)
        out = []
        for s in tour:
            p, look, v = s["p"], s["look"], s.get("visit")
            if v:
                inn = v["inn"]
                L = math.dist(p, inn) or 1.0
                n = ((inn[0] - p[0]) / L, (inn[1] - p[1]) / L); t = (-n[1], n[0])
                cands = [(inn[0] + n[0] * d + t[0] * l, inn[1] + n[1] * d + t[1] * l)
                         for d, l in ((16, 0), (26, 26), (26, -26), (34, 0), (18, 44), (18, -44), (44, 30), (44, -30),
                                      (52, 0), (30, 60), (30, -60))]
                inside = lambda q: g.point_ok(q[0], q[1], wall_clear=15, obj_clear=12) and g.leg_problem(inn, q) is None
                spot = self._free_spot(cands, inside)
                if spot:
                    out.append(dict(s, visit=dict(v, spot=spot)))
                    continue
                s = dict(s, visit=None)            # no room inside: they stand by the doorstep instead
            if s["kind"] in ("landmark", "gate"):
                fx, fy = look
                cands = [p] + sorted(((fx + r * math.cos(k * math.pi / 8), fy + r * math.sin(k * math.pi / 8))
                                      for r in (30, 38, 46, 56, 66) for k in range(16)), key=lambda q: math.dist(q, p))
            elif s["kind"] in ("home", "door", "shop"):
                L = math.dist(p, look) or 1.0
                n = ((p[0] - look[0]) / L, (p[1] - look[1]) / L); t = (-n[1], n[0])
                cands = [(p[0] + n[0] * d + t[0] * l, p[1] + n[1] * d + t[1] * l)
                         for d, l in ((0, 0), (0, 34), (0, -34), (12, 46), (12, -46), (26, 30), (26, -30), (30, 0),
                                      (14, 64), (14, -64), (40, 46), (40, -46))]
            else:
                cands = [p] + [(p[0] + r * math.cos(k * math.pi / 4), p[1] + r * math.sin(k * math.pi / 4))
                               for r in (22, 36, 50) for k in range(8)]
            spot = self._free_spot(cands, clear)
            if spot: out.append(dict(s, p=spot))
        return out

    def journey(self, name, key, to, look=None):
        """A long walk for person `name` that the story starts with A.walk(name, key) (a rescued man walking home,
        a deserter going back to face his captain): laid once the map is placed, from where the person stands to a
        standing spot of its own near `to` (world px), along the roads and paths and through any open doorway or
        gate square-on (Router.route_far), as a chain of waypoints <key>_1, _2... walked leg by leg (kit/behaviours
        Journey). The game's own path search gives up on a far goal and walks straight at it, into the trees
        (Greywatch's Wil, 2026-10-05). At its end the person stays, facing `look` (default: on along the last leg).
        Returns key."""
        self._movers.add(name)

        def lay():
            g, router, locked = self._world()
            o = next((o for o in self.m.d["objects"] if o.get("scr") == name), None)
            if o is None:
                print(f"  journey {key}: no {name}"); return
            start = (o["x"], o["y"])
            clear = lambda p: g.point_ok(p[0], p[1], wall_clear=15, obj_clear=12) and router.ok(
                (int(p[0] // WCELL), int(p[1] // WCELL)))
            cands = [to] + [(to[0] + r * math.cos(k * math.pi / 8), to[1] + r * math.sin(k * math.pi / 8))
                            for r in (20, 34, 48, 64, 80, 100, 124, 150) for k in range(16)]
            end = self._free_spot(cands, clear) or to
            route = router.route_far(start, end, shut=locked)
            if route is None:
                print(f"  journey {key}: no way from {name}'s place to ({end[0]:.0f}, {end[1]:.0f})")
                route = [end]
            pts = ([start] if g.point_ok(start[0], start[1], wall_clear=14, obj_clear=12) else []) + route
            names = self.pop.waypoint_path(key, pts)
            lk = look
            if lk is None and len(pts) >= 2:
                a, b = pts[-2], pts[-1]
                lk = (b[0] + (b[0] - a[0]) * 3, b[1] + (b[1] - a[1]) * 3)
            self.B.journey(key, name, names, lk)
        self.B.later(lay)
        return key

    def walkable(self):
        """Grid cells the player can walk to from the PlayerStart, flooded as the checker floods them
        (validate/checks.py Context): cells under a floor tile, not a wall's, not under a tree, a big rock or a
        building (Emberhollow's review: creatures set in pockets closed off by trees). None without a PlayerStart."""
        import collections
        m = self.m
        st = next((o for o in m.d["objects"] if o.get("type") == "PlayerStart"), None)
        if not st: return None
        floor = m.floor
        cover = lambda c: any(t in floor for t in ((c[0], c[1]), (c[0] - 1, c[1]), (c[0], c[1] - 1), (c[0] - 1, c[1] - 1)))
        blocked = set(m.wallmap)
        for o in m.d["objects"]:                 # cells within a piece's radius, as the checker blocks them
            t = o.get("type", "")
            r = self.WAY_BLOCKERS.get(t, 20 if t.startswith("Tree") else 0)
            if not r: continue
            cx, cy = int(o["x"] // CELL), int(o["y"] // CELL)
            blocked |= {(x, y) for x in range(cx - 2, cx + 3) for y in range(cy - 2, cy + 3)
                        if math.hypot(x * CELL + 11.5 - o["x"], y * CELL + 11.5 - o["y"]) <= r}
        s0 = (int(st["x"] // CELL), int(st["y"] // CELL))
        seen, q = {s0}, collections.deque([s0])
        while q:
            x, y = q.popleft()
            for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + a, y + b)
                if n in seen or n in blocked or not cover(n): continue
                seen.add(n); q.append(n)
        return seen

    # radii (px) of the pieces the planting stands in the way, as the checker measures them (corpus things table)
    WAY_BLOCKERS = {"CaveRockPillarShort1": 18, "CaveRockPillarTall1": 18, "CaveRockPillarTall2": 18,
                    "CaveRockPillarShort2": 12, "LargeStalagmite": 12, "CaveRocksHuge": 12, "CaveBoulders": 12,
                    "CaveRocksLarge": 10}

    def open_ways(self, targets, rounds=12):
        """After the planting: every target (world px: quest givers, creatures, chests) the player cannot walk to from
        the PlayerStart gets a way opened, by taking out the fewest pillars, trees and big rocks between it and the
        walkable ground. Cells are blocked as the checker blocks them (validate/checks.py Context.object_cells: a cell
        whose centre lies within the piece's radius), which walkable() only approximates (Deepvault: pillars either side
        of a narrow cave neck shut off a far camp, and a wild spider). Walls are left alone. Returns the objects removed."""
        import collections
        m = self.m
        st = next((o for o in m.d["objects"] if o.get("type") == "PlayerStart"), None)
        if not st: return []
        floor = m.floor
        cover = lambda c: any(t in floor for t in ((c[0], c[1]), (c[0] - 1, c[1]), (c[0], c[1] - 1), (c[0] - 1, c[1] - 1)))
        s0 = (int(st["x"] // CELL), int(st["y"] // CELL))
        removed = []
        for _ in range(rounds):
            by_cell = collections.defaultdict(list)
            for o in m.d["objects"]:
                t = o.get("type", "")
                r = self.WAY_BLOCKERS.get(t, 20 if t.startswith("Tree") else 0)
                if not r: continue
                cx, cy = int(o["x"] // CELL), int(o["y"] // CELL)
                for x in range(cx - 2, cx + 3):
                    for y in range(cy - 2, cy + 3):
                        if math.hypot(x * CELL + 11.5 - o["x"], y * CELL + 11.5 - o["y"]) <= r: by_cell[(x, y)].append(o)
            walk, q = {s0}, collections.deque([s0])
            while q:
                x, y = q.popleft()
                for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + a, y + b)
                    if n in walk or n in m.wallmap or n in by_cell or not cover(n): continue
                    walk.add(n); q.append(n)
            near = lambda c: any((c[0] + a, c[1] + b) in walk for a in range(-2, 3) for b in range(-2, 3))
            todo = [c for c in ((int(x // CELL), int(y // CELL)) for x, y in targets) if not near(c)]
            if not todo: break
            # fewest blocked cells from the target to the walkable ground (0-1 breadth first search)
            c0 = todo[0]
            dist, prev, dq, end = {c0: 0}, {c0: None}, collections.deque([c0]), None
            while dq:
                c = dq.popleft()
                if c in walk: end = c; break
                for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (c[0] + a, c[1] + b)
                    if n in m.wallmap or not cover(n): continue
                    w = dist[c] + (1 if n in by_cell else 0)
                    if w < dist.get(n, 1 << 30):
                        dist[n], prev[n] = w, c
                        (dq.append if n in by_cell else dq.appendleft)(n)
            if end is None:                           # walled off: not something taking out a pillar can fix
                targets = [p for p in targets if (int(p[0] // CELL), int(p[1] // CELL)) != c0]
                continue
            gone = set()
            c = end
            while c:
                for o in by_cell.get(c, ()):
                    if id(o) not in gone: gone.add(id(o)); removed.append(o)
                c = prev[c]
            m.d["objects"][:] = [o for o in m.d["objects"] if id(o) not in gone]
        return removed

    def wild(self, mix, avoid=(), per100=0.35, away_from=None, min_away=40, gap=8):
        """The wood's own creatures, alone, 2-3 squares in from the forest wall, away from the town (away_from,
        squares) and from the story's places (`avoid`: square points kept 14 squares clear). Returns how many."""
        land, rng, m = self.land, self.rng, self.m
        edge = land.edge_distance()
        walk = self.walkable()
        from kit.layout import bfs_distance
        homes = bfs_distance(list(land.taken_strict), land.squares, 10) if land.taken_strict else {}
        far = [s for s, dd in sorted(edge.items()) if 2 <= dd <= 3 and s not in land.taken and s not in land.roads
               and homes.get(s, 99) >= 10          # no spider at a house's door: the wood's creatures keep to the wood
               and (walk is None or all((int(square_px(s[0] + 0.5, s[1] - 0.5)[0] // CELL) + a,
                                         int(square_px(s[0] + 0.5, s[1] - 0.5)[1] // CELL) + b) in walk
                                        for a in (-1, 0, 1) for b in (-1, 0, 1)))
               and s not in land.taken_strict
               and (away_from is None or math.hypot(s[0] - away_from[0], s[1] - away_from[1]) > min_away)
               and all(math.hypot(s[0] - a[0], s[1] - a[1]) > 14 for a in avoid)]
        rng.shuffle(far)
        centres, n = [], 0
        for s_ in far:
            if n >= int(len(land.squares) * per100 / 100): break
            if any(math.hypot(s_[0] - a, s_[1] - b) < gap for a, b in centres): continue
            x, y = square_px(s_[0] + 0.5, s_[1] - 0.5)
            if any((int(x // 23) + a, int(y // 23) + b) in m.wallmap for a in (-1, 0, 1) for b in (-1, 0, 1)): continue
            self.pop.creature(rng.choices(list(mix), list(mix.values()))[0], x, y,
                              action="guard" if rng.random() < 0.38 else "idle")
            centres.append(s_); n += 1
        return n

    def keepers(self, room, types, prefix, aggr=0.83, spacing=28):
        """Creatures standing guard about a room's floor, off its walls and furniture (the restless dead of a crypt).
        Returns their script names."""
        m, rng = self.m, self.rng
        pts = sorted(((x + 1) * CELL, (y + 1) * CELL) for x, y in room.tiles)
        rng.shuffle(pts)
        objs = [(o["x"], o["y"]) for o in m.d["objects"]]
        names = []
        for k, t in enumerate(types):
            p = next((p for p in pts if all((p[0] - a) ** 2 + (p[1] - b) ** 2 > spacing ** 2 for a, b in objs)
                      and not any((int(p[0] // CELL) + a, int(p[1] // CELL) + b) in m.wallmap
                                  for a in (-1, 0, 1) for b in (-1, 0, 1))), None)
            if not p: break
            objs.append(p)
            self.pop.creature(t, *p, action="guard", scr=f"{prefix}{k + 1}", aggr=aggr)
            names.append(f"{prefix}{k + 1}")
        return names

    def seal_entrance(self, building, prefix, lock="Mechanism"):
        """A building's main entrance locked (by default to a mechanism: only the story opens it, A.unlock) and named
        <prefix>1, <prefix>2 (one name for a single door): a sealed door the story breaks (Starwell's observatory).
        Returns the names."""
        d = building.entrances[0]
        names = []
        for o in self.m.d["objects"]:
            if o.get("door") is not None and math.hypot(o["x"] - d.px[0], o["y"] - d.px[1]) < 40:
                o["scr"] = f"{prefix}{len(names) + 1}"
                o.setdefault("xfer", {})["LockType"] = lock
                names.append(o["scr"])
        assert names, "no door at the building's entrance"
        return names

    def lock_room(self, room, lock="Silver"):
        """The door(s) into a room locked: a key's lock (Silver, Gold, Ruby, Saphire) or Mechanism (scripts only)."""
        n = 0
        for d in room.doors:
            for o in self.m.d["objects"]:
                if o.get("door") is not None and math.hypot(o["x"] - d.px[0], o["y"] - d.px[1]) < 40:
                    o.setdefault("xfer", {})["LockType"] = lock; n += 1
        return n


class Curtain:
    """A castle's curtain wall round its courtyard (Greywatch): a rectangle of wall points on the square grid (a
    diamond on screen, as Westwood's buildings stand), a tower over each corner, a gatehouse (a tower either side of a
    double gate) where a road crosses one of the `gates` faces. The courtyard is all land however far it lies from
    what is built in it, and a band of forest is kept outside the wall (Land.forbidden) except before the gate faces,
    so the gates are the only ways in: a gate locked to a mechanism seals the road beyond it (check_story_gates).

        cw = Curtain(land, centre=(ci, cj), half=(24, 22), gates=("j0", "j1"))   # after the links, before the roads
        land.paint_roads(m, ..., skip=land.reserved | land.forbidden)
        cw.plan_gates(m)            # after the roads: where they cross the gate faces; the gatehouse towers
        cw.hold()                   # before place_buildings: the wall's band and the gate passages stay free
        sm.place_buildings(...); cw.release()
        land.carve(...); cw.fill()  # the courtyard all land, the towers and the band forest
        land.apply(...)
        gates = cw.build(m, prefix={"j0": "SouthGate", "j1": "NorthGate"}, lock={"j1": "Mechanism"})

    Faces, as a building's sides in square coordinates: i0 upper left, i1 lower right, j0 lower left, j1 upper
    right. Material: GalavaTownWall, the town wall of Westwood's Galava castle (G_Lava, War07A, Wiz07F); its double
    gate GalavaHalfDoor."""

    def __init__(self, land, centre, half, gates=("j0", "j1"), band=7, tower=3):
        self.land = land
        ci, cj = centre
        hi, hj = half
        self.gi, self.gj = int(round(ci - hi)), int(round(cj - hj + 1))
        self.w, self.h = 2 * hi, 2 * hj
        self.gates, self.t = tuple(gates), tower
        gi, gj, w, h, t = self.gi, self.gj, self.w, self.h, tower
        self.plot = {(gi + a, gj + b) for a in range(w) for b in range(h)}
        # corner towers: a t x t block over each corner, one square of it inside the courtyard
        self.blocks = [{(i0 + a, j0 + b) for a in range(t) for b in range(t)}
                       for i0 in (gi - t + 1, gi + w - 1) for j0 in (gj - t + 1, gj + h - 1)]
        forb = set()
        for i in range(gi - band, gi + w + band):
            for j in range(gj - band, gj + h + band):
                if (i, j) in self.plot: continue
                out_i = i < gi or i >= gi + w
                out_j = j < gj or j >= gj + h
                face = ("i0" if i < gi else "i1") if out_i else ("j0" if j < gj else "j1")
                if (out_i and out_j) or face not in self.gates: forb.add((i, j))      # beyond a corner or a closed face
        for b in self.blocks: forb |= b
        self.forb = forb
        land.forbidden |= forb
        self.gate_at, self.held = {}, set()

    def points(self, face):
        """The face's wall points in order along it."""
        gi, gj, w, h = self.gi, self.gj, self.w, self.h
        return {"i0": [(gi, q) for q in range(gj - 1, gj + h)], "i1": [(gi + w, q) for q in range(gj - 1, gj + h)],
                "j0": [(p, gj - 1) for p in range(gi, gi + w + 1)], "j1": [(p, gj + h - 1) for p in range(gi, gi + w + 1)]}[face]

    @staticmethod
    def touching(pt):
        p, q = pt
        return [(p - 1, q), (p, q), (p - 1, q + 1), (p, q + 1)]

    def _across(self, face):
        """The rows (squares across the face) a gatehouse tower covers: t-1 outside and one inside."""
        gi, gj, w, h, t = self.gi, self.gj, self.w, self.h, self.t
        return {"j0": range(gj - t + 1, gj + 1), "j1": range(gj + h - 1, gj + h + t - 1),
                "i0": range(gi - t + 1, gi + 1), "i1": range(gi + w - 1, gi + w + t - 1)}[face]

    @staticmethod
    def _sq(face, along, across):
        return (across, along) if face in ("i0", "i1") else (along, across)

    def plan_gates(self, spec):
        """Where the roads cross the gate faces: the gate in the middle of each crossing, a tower either side of it
        clear of the road. Road squares that fall under a tower go back to ground. Returns {face: gate index}."""
        land = self.land
        for face in self.gates:
            pts = self.points(face)
            hits = [k for k, p in enumerate(pts[1:-2], 1) if any(s in land.roads for s in self.touching(p))]
            if not hits:
                print(f"  curtain: no road crosses the {face} face"); continue
            k = hits[len(hits) // 2]
            self.gate_at[face] = k
            a0 = pts[k][1] if face in ("i0", "i1") else pts[k][0]
            if face in ("j0", "j1"): lo, hi = a0 - 1, a0 + 2           # the open squares between the jambs
            else: lo, hi = a0, a0 + 3
            for side in (-1, 1):
                for off in range(0, 4):
                    al = range(lo - off - self.t, lo - off) if side < 0 else range(hi + off, hi + off + self.t)
                    block = {self._sq(face, a, c) for a in al for c in self._across(face)}
                    if block & (land.roads | land.plaza): continue
                    self.blocks.append(block); self.forb |= block; land.forbidden |= block
                    break
            # the passage through the gate: kept free of buildings, yards and trees
            acr = self._across(face)
            self.held |= {self._sq(face, a, c) for a in range(lo, hi) for c in range(min(acr) - 4, max(acr) + 5)}
        for s in list(land.roads):
            if s in self.forb:
                land.roads.discard(s); spec.floor.pop(square_tile(*s), None)
        return self.gate_at

    def hold(self, inside=2):
        """Squares the buildings keep off while they are placed: `inside` rows within the wall, the gate passages and
        everything outside near the wall. release() gives them back (the passages stay taken)."""
        gi, gj, w, h = self.gi, self.gj, self.w, self.h
        ring = {s for s in self.plot if min(s[0] - gi, gi + w - 1 - s[0], s[1] - gj, gj + h - 1 - s[1]) < inside}
        near = {(i, j) for i in range(gi - 8, gi + w + 8) for j in range(gj - 8, gj + h + 8)} - self.plot
        self._hold = (ring | near) - self.land.taken
        self.land.taken |= self._hold | self.held
        return self._hold

    def release(self):
        self.land.taken -= getattr(self, "_hold", set()) - self.held

    def fill(self):
        """After carve: the courtyard all land, the towers and the band outside the closed faces void."""
        land = self.land
        land.squares |= self.plot
        land.squares -= self.forb
        return land.squares

    def courtyard(self):
        """The courtyard's land squares (not the towers)."""
        return self.plot - self.forb

    def build(self, spec, material="GalavaTownWall", gate="GalavaHalfDoor", prefix=None, lock=None):
        """After land.apply: the wall on every point of the faces and round every tower that touches land (laid over
        the forest's edge where the courtyard meets the band), and the double gates. prefix: {face: script name
        prefix} for the gate halves (<prefix>1, <prefix>2); lock: {face: LockType}. Returns {face: [halves]}."""
        land = self.land
        prefix, lock = prefix or {}, lock or {}
        cells = set()
        for face in ("i0", "i1", "j0", "j1"):
            for p in self.points(face):
                if any(s in land.squares for s in self.touching(p)): cells.add(point_cell(*p))
        for b in self.blocks:
            # a tower is solid stone: every point of its block (an outline alone shows the void inside as a pit)
            pts = {(i + a, j + c) for i, j in b for a in (0, 1) for c in (-1, 0)}
            if any(s in land.squares for p in pts for s in self.touching(p)):
                cells |= {point_cell(*p) for p in pts}
        for c in cells: spec.wall(*c, material)
        out = {}
        for face, k in self.gate_at.items():
            pts = self.points(face)
            a, b = point_cell(*pts[k]), point_cell(*pts[k + 1])
            line = "\\" if (b[0] - a[0], b[1] - a[1]) == (1, 1) else "/"
            n0 = len(spec.d["objects"])
            spec.door(gate, a, line)
            halves = [o for o in spec.d["objects"][n0:] if o["type"] == gate]
            for n, o in enumerate(halves):
                if face in prefix: o["scr"] = f"{prefix[face]}{n + 1}"
                if face in lock: o.setdefault("xfer", {})["LockType"] = lock[face]
            out[face] = halves
        return out

    def gate_px(self, face, outward=0.0):
        """World px of a gate's middle, `outward` squares out from the wall (negative: into the courtyard)."""
        pts = self.points(face)
        k = self.gate_at[face]
        p = ((pts[k][0] + pts[k + 1][0]) / 2, (pts[k][1] + pts[k + 1][1]) / 2)
        d = {"i0": (-1, 0), "i1": (1, 0), "j0": (0, -1), "j1": (0, 1)}[face]
        return square_px(p[0] + d[0] * outward, p[1] + d[1] * outward)
