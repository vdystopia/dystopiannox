"""Creatures and NPCs, placed and moved the way Westwood does it (rules/NPCS.md, measured by rules/npcs.py), plus
scripted behaviour sets (kit/behaviours/behaviours.go, run by OpenNox from the map's folder).

What Westwood does (2,942 hostile creatures on its single-player maps, each layout once):
- 61% stand idle and 35% guard until they see the player; 4% roam a waypoint network; escorts are rare;
- they stand alone (group size p90: 2), about 2 cells from a wall, far from the player's start (p25 89 cells, p50
  110-125), 23 cells from the nearest door;
- sight 150 for most, 300-500 for archers, scorpions, grunts and sentries; aggressiveness 0.5 (0.83 when roused);
- 20% are wired to script callbacks: enemy sighted, is hit, looking for enemy, end of waypoint, death.
Movement beyond that is scripted: Move along waypoints, Wander, Guard, Hunt, Follow, GoBackHome.

    pop = Population(spec, rng)
    pop.creature("GruntAxe", x, y, action="guard", face=(fx, fy), scr="GateGuard1")
    pop.roam_loop([(x, y), ...], "Swordsman", n=2)            # roamers on a linked waypoint loop, no script
    pop.escort("BlackWolf", leader_xy, "Wolf", [xy, ...])      # Westwood's escort: followers keep with the leader
    pop.behaviours.sentry("GateGuard1", face=(fx, fy), rouse=[...])   # scripted sets (config.go)
    spec.scripts.update(pop.behaviours.files(spec.d["name"]))
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
# Creatures that cannot be placed. Empty since 2026-10-09: the "Zombie crashes the server" finding (and ModLab's Skeleton
# and Wolf) was the map writer, not the creature: a map whose object data ended in its last crypt block failed to load
# ("cannot read next section: EOF") whatever it held, about one size in eight; Shared/Map.cs now writes a spare block
# (checker rule setup.file_tail). Zombies, Skeletons and Wolves placed in maps load in the server. Westwood still keeps
# its zombies in coffins: a design habit, not a limit.
UNPLACEABLE = {}
ACTION = dict(idle=0, wait=1, escort=3, guard=4, hunt=5, roam=10)
# DirectionId: the editor's names for the 8 facings (MonsterXfer.NOX_DIRECT_NAMES), by screen direction
DIRECTION = dict(N=0, S=1, E=2, NW=3, SW=4, W=5, NE=6, SE=7)


def facing(dx, dy):
    """DirectionId for facing along (dx, dy) in world pixels (y grows down the screen)."""
    a = math.degrees(math.atan2(-dy, dx)) % 360          # 0 = east, 90 = north (up the screen)
    names = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
    return DIRECTION[names[int((a + 22.5) // 45) % 8]]


def westwood_types():
    """Westwood's per-type numbers (rules/out/npcs.json): sight range, aggressiveness, the default action mix."""
    p = os.path.join(HERE, "..", "..", "rules", "out", "npcs.json")
    try:
        return json.load(open(p))["actions_by_type"]
    except (OSError, KeyError):
        return {}


# Hostile creatures of a group stand apart (playtest 2026-10-05: "they cluster too tightly on a central point like a
# swarm"): Westwood's grouped creatures (another of the kind within 6 cells) stand 49 px from their nearest at p25,
# 70 at the median (corpus, 3,091 creatures); none of ours closer than GROUP_GAP.
GROUP_GAP = 48.0


class Population:
    def __init__(self, spec, rng):
        self.spec, self.rng = spec, rng
        self.ww = westwood_types()
        self.behaviours = Behaviours(spec)
        self.behaviours.last(self.settle_waypoints)
        self.placed, self.hostiles = [], []
        self._n = {}

    def name(self, prefix):
        self._n[prefix] = self._n.get(prefix, 0) + 1
        return f"{prefix}{self._n[prefix]}"

    def creature(self, t, x, y, action="idle", face=None, scr=None, sight=None, aggr=None, roamflag=None, escort=None,
                 spread=True, **xfer):
        """One creature at world pixel (x, y): its default action, its facing (a point to look toward, or random),
        Westwood's sight range for its type (or `sight`), aggressiveness 0.5 like Westwood's (or `aggr`), roam flags
        and escort target. A hostile creature stands at least GROUP_GAP px from every hostile one placed before it
        (moved to the nearest clear point that is, within 72 px; spread=False keeps it where it is: two prisoners
        in one cell). Returns the object dict."""
        # a Zombie written as a placed creature makes OpenNox misread the map's object section (the server stops at
        # "cannot read next section: EOF" and panics; 2026-10-04): Westwood only ever puts zombies inside coffins
        assert t not in UNPLACEABLE, f"{t} cannot be placed as a creature ({UNPLACEABLE[t]})"
        x, y = self._on_floor(x, y)
        hostile = (0.5 if aggr is None else aggr) > 0 and "ShopkeeperInfo" not in xfer
        if hostile and spread: x, y = self._spaced(x, y)
        ww = self.ww.get(t, {})
        x_ = dict(DefaultAction=ACTION.get(action, action),
                  DirectionId=facing(face[0] - x, face[1] - y) if face else self.rng.randrange(8),
                  SightRange=float(sight or ((ww.get("sight") or {}).get("p50")) or 150),
                  Aggressiveness=float(0.5 if aggr is None else aggr))
        if roamflag is not None: x_["ActionRoamPathFlag"] = roamflag
        if escort: x_["EscortObjName"] = escort
        x_.update(xfer)
        o = self.spec.obj_px(t, x, y, xfer=x_, **({"scr": scr} if scr else {}))
        if hostile: self.hostiles.append(o)
        self.placed.append(o)
        return o

    def _spaced(self, x, y, gap=GROUP_GAP, reach=72):
        """(x, y), or the nearest point within `reach` px that stands GROUP_GAP px from every hostile creature placed
        so far, on floor, off the walls (a cell's clearance) and out of obstacles (tents, stumps, rocks, trees)."""
        others = [(o["x"], o["y"]) for o in self.hostiles]
        far = lambda p: all((p[0] - a) ** 2 + (p[1] - b) ** 2 >= gap * gap for a, b in others)
        if far((x, y)): return x, y
        from kit.walkways import thing_shapes, blocks
        shapes = thing_shapes()
        near = []
        for o in self.spec.d["objects"]:
            if abs(o["x"] - x) > reach + 60 or abs(o["y"] - y) > reach + 60: continue
            sh = shapes.get(o.get("type"))
            if not sh or not blocks(*sh): continue
            r = sh[1] if sh[0] != "BOX" else math.hypot(sh[1], sh[2]) / 2
            near.append((o["x"], o["y"], r))
        fl, wm, C = self.spec.floor, self.spec.wallmap, 23
        def ok(p):
            cx, cy = int(p[0] // C), int(p[1] // C)
            if not any(t in fl for t in ((cx, cy), (cx - 1, cy), (cx, cy - 1), (cx - 1, cy - 1))): return False
            if any((cx + a, cy + b) in wm for a in (-1, 0, 1) for b in (-1, 0, 1)): return False
            return all(math.hypot(p[0] - a, p[1] - b) >= r + 12 for a, b, r in near)
        for r in range(8, reach + 1, 8):
            for k in range(16):
                a = k * math.pi / 8
                p = (x + r * math.cos(a), y + r * math.sin(a))
                if far(p) and ok(p): return p
        return x, y

    def _on_floor(self, x, y, reach=4):
        """(x, y), or the nearest point within `reach` cells that has floor under it and no wall: a creature set in
        the void or in a wall piece is an error and never moves (Emberhollow seed 2: a demon off the lake's rim)."""
        fl, wm, C = self.spec.floor, self.spec.wallmap, 23
        def ok(cx, cy):
            return (cx, cy) not in wm and any(t in fl for t in ((cx, cy), (cx - 1, cy), (cx, cy - 1), (cx - 1, cy - 1)))
        cx, cy = int(x // C), int(y // C)
        if ok(cx, cy) or not fl: return x, y
        best = min(((a, b) for a in range(-reach, reach + 1) for b in range(-reach, reach + 1) if ok(cx + a, cy + b)),
                   key=lambda d: d[0] * d[0] + d[1] * d[1], default=None)
        return (x, y) if best is None else ((cx + best[0]) * C + C / 2, (cy + best[1]) * C + C / 2)

    def shopkeeper(self, t, x, y, items, greeting="", buy=1.0, sell=0.33, face=None, scr=None):
        """A shopkeeper selling `items` ([(count, type)]) as Westwood sets one up (MonsterXfer ShopkeeperInfo, read from
        its town maps: Con02a's mystic sells potions and a spell book, its barkeeper apples, meat and cider): immortal,
        on guard behind the counter, buying at full value and paying a third when it buys."""
        info = dict(BuyValueMultiplier=float(buy), SellValueMultiplier=float(sell), ShopkeeperGreetingText=greeting,
                    ShopItems=[dict(Name=n, Count=int(c), SpellID="", Ench1="", Ench2="", Ench3="", Ench4="")
                               for c, n in items])
        return self.creature(t, x, y, action="guard", face=face, scr=scr, aggr=0.0, Immortal=True, ShopkeeperInfo=info)

    def waypoint_path(self, prefix, pts, link=False, loop=False):
        """Named waypoints <prefix>_1, _2, ... at world pixel points; linked in a chain (and closed into a loop) when
        asked. Linked connections carry flag 128, which roaming creatures follow (ActionRoamPathFlag 128 or 255)."""
        wps = [self.spec.waypoint(x, y, name=f"{prefix}_{k + 1}") for k, (x, y) in enumerate(pts)]
        if link:
            for a, b in zip(wps, wps[1:]): self.spec.link(a, b)
            if loop and len(wps) > 2: self.spec.link(wps[-1], wps[0])
        return [w["name"] for w in wps]

    def settle_waypoints(self, reach=3):
        """Every waypoint off the walls and obstacles, on floor a body can stand on (validate check_routes): one set
        against a wall, in a tree or on water moves to the nearest clear point within `reach` cells. Run once the map
        is placed (Behaviours.files runs it last)."""
        from kit.walkways import Ground, CELL as C_
        wps = self.spec.d["waypoints"]
        if not wps: return 0
        g = Ground.from_spec(self.spec)
        moved = 0
        for w in wps:
            if g.point_ok(w["x"], w["y"], wall_clear=14, obj_clear=12): continue
            cx, cy = int(w["x"] // C_), int(w["y"] // C_)
            cand = [((cx + a) * C_ + C_ / 2, (cy + b) * C_ + C_ / 2) for a in range(-reach, reach + 1) for b in range(-reach, reach + 1)]
            cand = [p for p in cand if g.point_ok(p[0], p[1], wall_clear=14, obj_clear=12)]
            if not cand: continue
            x, y = min(cand, key=lambda p: (p[0] - w["x"]) ** 2 + (p[1] - w["y"]) ** 2)
            w["x"], w["y"] = round(x, 1), round(y, 1)
            moved += 1
        return moved

    def roam_loop(self, pts, t, n=1, prefix=None):
        """Westwood's unscripted patrol: creatures with the roam action on a loop of linked waypoints (4% of its
        creatures; they start on a waypoint, 1.6 cells away at the median)."""
        prefix = prefix or self.name("Roam")
        self.waypoint_path(prefix, pts, link=True, loop=True)
        out = []
        for k in range(n):
            x, y = pts[(k * len(pts)) // max(1, n)]
            out.append(self.creature(t, x + self.rng.uniform(-8, 8), y + self.rng.uniform(-8, 8), action="roam",
                                     roamflag=128))
        return out

    def escort(self, leader_t, at, follower_t, spots, leader_action="idle"):
        """Westwood's unscripted escort: a named leader and followers whose default action is escort, keeping with
        it (EscortObjName)."""
        lname = self.name("Leader")
        self.creature(leader_t, at[0], at[1], action=leader_action, scr=lname)
        for x, y in spots:
            self.creature(follower_t, x, y, action="escort", escort=lname)
        return lname


class Behaviours:
    """Scripted behaviour sets for named creatures (kit/behaviours/behaviours.go); files() gives the Go sources for
    the map's folder. Routes walked (tours, patrols) are also recorded on the spec (spec.routes), which the build
    writes beside the map as <map>.routes.json for the checker (validate check_routes)."""

    def __init__(self, spec=None):
        self.spec = spec
        self.calls = []
        self.shouts = set()          # what sentries call out: text, not names
        self.keys = set()            # journeys' keys: names of walks, not of creatures
        self._later, self._last = [], []

    def later(self, fn):
        """fn() runs when files() is called, once the map is placed (routes need every wall, tree and bench)."""
        self._later.append(fn)

    def last(self, fn):
        self._last.append(fn)

    @staticmethod
    def _s(names):
        return "[]string{" + ", ".join(json.dumps(n) for n in names) + "}"

    @staticmethod
    def _f(vals):
        return "[]float32{" + ", ".join(f"{v:.1f}" for v in vals) + "}"

    def _record(self, name, kind, route, loop, pauses, looks=None, features=None):
        if self.spec is not None:
            if not hasattr(self.spec, "routes"): self.spec.routes = []
            pt = lambda p: [round(p[0], 1), round(p[1], 1)] if p else None
            self.spec.routes.append(dict(who=name, kind=kind, waypoints=list(route), loop=bool(loop),
                                         pauses=[round(p, 1) for p in pauses],
                                         looks=[pt(p) for p in (looks or [None] * len(route))],
                                         features=[pt(p) for p in (features or [None] * len(route))]))

    def _ground(self):
        """The ground the stops' facings are judged on: the story's (StoryMap._world sets it), else built from the
        map as it stands when the first route is laid."""
        g = getattr(self, "ground", None)
        if g is None and self.spec is not None:
            from kit.walkways import Ground
            g = self.ground = Ground.from_spec(self.spec)
        return g

    def _facings(self, route, pauses, looks=None, features=None):
        """The point each stop of a route (a waypoint with a pause) is faced toward, turned to open ground by
        kit/walkways stop_facing: away from a building or wall it stands beside, never into a tree, a wall or the
        void; looks[k] (a point: the feature, the square's middle, straight out from a door) is what it would face,
        features[k] the feature it stands at (faced unturned when it is open). A stop with no look faces the most
        open way. Bends and doorway points face nothing (None). (Starwell playtest 2026-10-05.)"""
        from kit.walkways import stop_facing
        looks = list(looks or [None] * len(route)); features = list(features or [None] * len(route))
        g = self._ground()
        if g is None or self.spec is None: return looks, features
        pos = {w["name"]: (w["x"], w["y"]) for w in self.spec.d.get("waypoints", [])}
        out = []
        for k, n in enumerate(route):
            lk = looks[k] if k < len(looks) else None
            if k < len(pauses) and pauses[k] > 0 and n in pos:
                lk = stop_facing(g, pos[n], lk, features[k] if k < len(features) else None)
            out.append(lk)
        return out, features

    def sentry(self, name, face, rouse=(), shout="Intruder!"):
        self.shouts.add(shout)
        self.calls.append(f'Sentry({json.dumps(name)}, {face[0]:.1f}, {face[1]:.1f}, {self._s(rouse)}, {json.dumps(shout)})')

    def patrol(self, name, route, pause=2.0, loop=True, looks=None, features=None):
        """Walks `route` (waypoint names) in turn, round when loop, else there and back. pause: seconds at every
        waypoint, or a list (0 = a bend passed through); looks: an (x, y) per waypoint to face there, or None;
        features: the feature (x, y) a stop stands at, or None. Every stop's facing is turned to open ground
        (_facings)."""
        pauses = list(pause) if isinstance(pause, (list, tuple)) else [pause] * len(route)
        looks, features = self._facings(route, pauses, looks, features)
        look = [c for p in looks for c in (p or (0.0, 0.0))]
        self._record(name, "patrol", route, loop, pauses, looks, features)
        self.calls.append(f'Patrol({json.dumps(name)}, {self._s(route)}, {self._f(pauses)}, {self._f(look)}, '
                          f'{"true" if loop else "false"})')

    def tour(self, name, route, pauses, looks=None, home="", fear=180.0, features=None):
        """A townsperson's tour (kit/behaviours Tour): `route` waypoint names walked round in order, standing
        pauses[k] seconds at each stop (0 = a bend or doorway point), facing looks[k]; runs for the `home` waypoint
        (one of the route's) while a hostile creature is within `fear` px (0: never). Every stop's facing is turned to
        open ground (_facings)."""
        looks, features = self._facings(route, pauses, looks, features)
        look = [c for p in looks for c in (p or (0.0, 0.0))]
        self._record(name, "tour", route, True, pauses, looks, features)
        self.calls.append(f'Tour({json.dumps(name)}, {self._s(route)}, {self._f(pauses)}, {self._f(look)}, '
                          f'{json.dumps(home)}, {fear:.1f})')

    def journey(self, key, name, route, look=None, feature=None):
        """A long walk `name` takes when the story says (quests A.walk(name, key)): `route` waypoint names from where
        it stands to where it ends, a waypoint at each bend of the roads and paths and three square-on through each
        doorway (StoryMap.journey lays them), walked leg by leg as a tour is; at the last it stays, facing `look`."""
        self.keys.add(key)
        pauses = [0.0] * (len(route) - 1) + [1.0]
        looks, features = self._facings(route, pauses, [None] * (len(route) - 1) + [look],
                                        [None] * (len(route) - 1) + [feature])
        look = looks[-1] if looks else look
        self._record(name, "journey", route, False, pauses, looks, features)
        lx, ly = look or (0.0, 0.0)
        self.calls.append(f'Journey({json.dumps(key)}, {json.dumps(name)}, {self._s(route)}, {lx:.1f}, {ly:.1f})')

    def pack(self, leader, members):
        self.calls.append(f'Pack({json.dumps(leader)}, {self._s(members)})')

    def skittish(self, name, flee=3.0):
        self.calls.append(f'Skittish({json.dumps(name)}, {flee:.1f})')

    def ambush(self, names, at, reach=140.0):
        self.calls.append(f'Ambush({self._s(names)}, {at[0]:.1f}, {at[1]:.1f}, {reach:.1f})')

    def townsfolk(self, name, spots, linger=4.0):
        """Walks between `spots` in turn, standing `linger` seconds at each (a Tour without a home)."""
        self.tour(name, spots, [linger] * len(spots), fear=0.0)

    def villager(self, name, spots, home, linger=5.0, fear=180.0):
        """Townsfolk who run for their home doorstep (waypoint `home`) while a hostile creature is within `fear` px."""
        self.tour(name, spots, [linger] * len(spots), home=home, fear=fear)

    def harpoon_staff(self, staff, speed=26.0, reach=320.0, damage=20, reel=40, pull=6.0):
        """A named Lesser Fireball staff that throws harpoons (kit/behaviours/weapons.go, rules/WEAPONS.md)."""
        self.weapons = True
        self.calls.append(f'HarpoonStaff({json.dumps(staff)}, {speed:.1f}, {reach:.1f}, {int(damage)}, {int(reel)}, {pull:.1f})')

    def names(self):
        """Every creature and waypoint name the calls use (for the self-check): waypoints end in _<number>."""
        import re
        objs, wps = set(), set()
        for c in self.calls:
            for q in re.findall(r'"([^"]+)"', c):
                (wps if re.search(r"_\d+$", q) else objs).add(q)
        return sorted(objs - self.shouts - self.keys), sorted(wps)

    def files(self, map_name):
        """{filename: Go source} for the map's folder, package named after the map (as OpenNox expects)."""
        while self._later: self._later.pop(0)()
        for fn in self._last: fn()
        self._last = []
        if not self.calls: return {}
        pkg = map_name.lower()
        lib = open(os.path.join(HERE, "behaviours", "behaviours.go"), encoding="utf-8").read().replace("package PKG", f"package {pkg}", 1)
        objs, wps = self.names()
        cfg = (f"package {pkg}\n\n// Who does what on {map_name} (written by dystopiannox mapgen/kit/npcs.py).\n\n"
               'import "github.com/noxworld-dev/noxscript/ns/v4"\n\n'
               # set up once, on MapInitialize or after a second of frames if it never fires (as kit/quests.py)
               "var behavioursSetUp bool\n\nfunc setUpBehaviours() {\n\tif behavioursSetUp {\n\t\treturn\n\t}\n"
               "\tbehavioursSetUp = true\n" +
               # the story's A.walk starts a journey (quests.go declares the hook; journeys come only with a story)
               ("\tjourneyStart = startJourney\n" if self.keys else "") + "".join(f"\t{c}\n" for c in self.calls) +
               "\tprintln(\"behaviours: started\")\n}\n\nfunc init() {\n\tns.OnMapEvent(ns.MapInitialize, setUpBehaviours)\n"
               "\tbframes := 0\n\tns.OnEachFrame(1, func() {\n\t\tif bframes++; bframes == 30 {\n\t\t\tsetUpBehaviours()\n\t\t}\n\t})\n"
               f"\tDiagnose({self._s(objs)}, {self._s(wps)})\n}}\n")
        out = {"behaviours.go": lib, "config.go": cfg}
        if getattr(self, "weapons", False):
            out["weapons.go"] = open(os.path.join(HERE, "behaviours", "weapons.go"), encoding="utf-8").read().replace(
                "package PKG", f"package {pkg}", 1)
        return out
