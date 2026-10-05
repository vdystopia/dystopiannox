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
import math, os
from nox import CELL
from kit.identity import BUILDINGS, role_size
from kit.layout import square_tile, square_px, px_square, point_cell
from kit.village import _squares_of
from kit.building import generate_building
from kit.originality import furnish_original
from kit.npcs import Population, facing

STOCK = r"C:\GOG Games\Nox\maps"


class StoryMap:
    def __init__(self, spec, rng, land, identity):
        self.m, self.rng, self.land, self.ID = spec, rng, land, identity
        self.placed, self.by_role, self.missed = [], {}, []
        self.pop = Population(spec, rng)
        self.B = self.pop.behaviours

    # ---- buildings -------------------------------------------------------------------------------------------------
    def place_buildings(self, no_build=None, scale=1.0):
        """Every building of the identity, public ones on the square first, then by size; none within the radius
        (squares) of the named areas in `no_build` (the story's wild places), which stay free for the forest after."""
        m, land, rng = self.m, self.land, self.rng
        held = set()
        for k_, r_ in (no_build or {}).items():
            c_ = land.areas[k_]["c"]
            held |= {s for s in land.squares if math.hypot(s[0] - c_[0], s[1] - c_[1]) <= r_} - land.taken
        land.taken |= held
        B_ = self.ID.buildings
        order = sorted(range(len(B_)), key=lambda k: (BUILDINGS[B_[k].role]["faces"] != "square",
                                                      -BUILDINGS[B_[k].role]["size"][0], k))
        for k in order:
            bid = B_[k]
            role = BUILDINGS[bid.role]
            size0, min_units0 = role_size(role)
            program = [kind for kind, _ in role["rooms"]]
            b = None
            for shrink in (1.0, 0.92, 0.84):
                size = (2 * round(size0[0] * scale * shrink / 2), 2 * round(size0[1] * scale * shrink / 2))
                lots = land.square_lots(size) if role["faces"] == "square" and bid.area == "town" else []
                lots += land.lots(bid.area, size)
                for origin, side in lots:
                    if not land.lot_free(origin, size, margin=1): continue
                    b = generate_building(m, rng, origin, size, role["style"], program=program, entrance_side=side,
                                          building_id=f"B{k}", occupied={square_tile(*s) for s in land.taken}, tries=12,
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
        return self.placed

    def connect_and_furnish(self, style="town"):
        """Paths from every door to the roads (dead ends trimmed), then every room furnished by its identity."""
        m, land = self.m, self.land
        land.clear_walls(m)
        door_paths = set()
        for bid, b in self.placed:
            foot = _squares_of(b.footprint)
            for d in b.entrances:
                path = land.connect_door(m, d, foot)
                if path is None: print(f"  no path from the {bid.role}'s door")
                else: door_paths |= set(path)
        land.trim_dead_ends(m, keep=door_paths)
        for bid, b in self.placed:
            for room in b.rooms:
                furnish_original(m, room, kind=room.kind, rng=self.rng, style=style)

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

    def exit_to(self, area, map_name, prefix="Exit", n=3):
        """Exit areas (InvisibleExitArea) where the road reaches `area` near the forest's edge, leading to map_name.
        Script names <prefix>1..n (A.disable/A.enable)."""
        land = self.land
        edge = land.edge_distance()
        c = land.areas[area]["c"]
        sq = min(land.roads, key=lambda s: math.hypot(s[0] - c[0], s[1] - c[1]) + 0.2 * edge.get(s, 0))
        ex, ey = square_px(sq[0] + 0.5, sq[1] - 0.5)
        names = []
        for k in range(n):
            off = 18 * (k - (n - 1) / 2)
            self.m.obj_px("InvisibleExitArea", ex + off, ey + off, scr=f"{prefix}{k + 1}",
                          xfer={"MapName": f"{map_name}.map", "ExitX": 0, "ExitY": 0})
            names.append(f"{prefix}{k + 1}")
        return names

    # ---- people ------------------------------------------------------------------------------------------------------
    def person(self, donor, scr, x, y, name, face=None, action=4):
        """A person cloned in their clothes from a stock map (maps/<donor>/<donor>.map, script name <donor>:<scr>), named
        in this map; standing on guard (action 4) by default, facing `face`."""
        xf = dict(DefaultAction=action, Aggressiveness=0.0)
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

    def townsfolk(self, folk, centre, q=None, rumours=(), after=None, pics=(), radius=6.5, prefix="Folk"):
        """Townspeople (clones [(donor, scr)]) walking between the square round `centre` (squares) and the doorsteps,
        running home when a creature comes near (kit/behaviours Villager). With a QuestBook q, each says its rumour
        (and `after`: (flag, line) once the main quest is done), with its portrait. Returns the square's ring (px)."""
        rng = self.rng
        ring = [square_px(centre[0] + radius * math.cos(a), centre[1] - 0.5 + radius * math.sin(a))
                for a in (k * math.pi / 4 for k in range(8))]
        square_wps = self.pop.waypoint_path("Square", ring)
        door_wps = []
        for bid, b in self.placed:
            for d in b.entrances[:1]:
                o_ = self.land.door_outside(d, _squares_of(b.footprint))
                if o_: door_wps += self.pop.waypoint_path(f"Door{len(door_wps) + 1}", [square_px(o_[0] + 0.5, o_[1] - 0.5)])
        for k, (donor, src) in enumerate(folk):
            name = f"{prefix}{k + 1}"
            x, y = ring[k % len(ring)]
            self.person(donor, src, x + rng.uniform(-10, 10), y + rng.uniform(-10, 10), name)
            homes = rng.sample(door_wps, min(2, len(door_wps)))
            self.B.villager(name, rng.sample(square_wps, 3) + homes, home=homes[0] if homes else square_wps[0], linger=5.0)
            if q and k < len(rumours):
                lines = []
                if after: lines.append(q.say(after[1], when=q.when(flag=after[0]), who=prefix))
                lines.append(q.say(rumours[k], who=prefix))
                q.talker(name, lines)
                if k < len(pics): q.portrait(name, pics[k])
        return ring

    def wild(self, mix, avoid=(), per100=0.35, away_from=None, min_away=40, gap=8):
        """The wood's own creatures, alone, 2-3 squares in from the forest wall, away from the town (away_from,
        squares) and from the story's places (`avoid`: square points kept 14 squares clear). Returns how many."""
        land, rng, m = self.land, self.rng, self.m
        edge = land.edge_distance()
        far = [s for s, dd in sorted(edge.items()) if 2 <= dd <= 3 and s not in land.taken and s not in land.roads
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

    def lock_room(self, room, lock="Silver"):
        """The door(s) into a room locked: a key's lock (Silver, Gold, Ruby, Saphire) or Mechanism (scripts only)."""
        n = 0
        for d in room.doors:
            for o in self.m.d["objects"]:
                if o.get("door") is not None and math.hypot(o["x"] - d.px[0], o["y"] - d.px[1]) < 40:
                    o.setdefault("xfer", {})["LockType"] = lock; n += 1
        return n
