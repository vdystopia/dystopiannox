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
UNPLACEABLE = {"Zombie": "OpenNox cannot read the map back; Westwood keeps zombies inside coffins",
               "VileZombie": "as Zombie"}
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


class Population:
    def __init__(self, spec, rng):
        self.spec, self.rng = spec, rng
        self.ww = westwood_types()
        self.behaviours = Behaviours()
        self.placed = []
        self._n = {}

    def name(self, prefix):
        self._n[prefix] = self._n.get(prefix, 0) + 1
        return f"{prefix}{self._n[prefix]}"

    def creature(self, t, x, y, action="idle", face=None, scr=None, sight=None, aggr=None, roamflag=None, escort=None,
                 **xfer):
        """One creature at world pixel (x, y): its default action, its facing (a point to look toward, or random),
        Westwood's sight range for its type (or `sight`), aggressiveness 0.5 like Westwood's (or `aggr`), roam flags
        and escort target. Returns the object dict."""
        # a Zombie written as a placed creature makes OpenNox misread the map's object section (the server stops at
        # "cannot read next section: EOF" and panics; 2026-10-04): Westwood only ever puts zombies inside coffins
        assert t not in UNPLACEABLE, f"{t} cannot be placed as a creature ({UNPLACEABLE[t]})"
        x, y = self._on_floor(x, y)
        ww = self.ww.get(t, {})
        x_ = dict(DefaultAction=ACTION.get(action, action),
                  DirectionId=facing(face[0] - x, face[1] - y) if face else self.rng.randrange(8),
                  SightRange=float(sight or ((ww.get("sight") or {}).get("p50")) or 150),
                  Aggressiveness=float(0.5 if aggr is None else aggr))
        if roamflag is not None: x_["ActionRoamPathFlag"] = roamflag
        if escort: x_["EscortObjName"] = escort
        x_.update(xfer)
        o = self.spec.obj_px(t, x, y, xfer=x_, **({"scr": scr} if scr else {}))
        self.placed.append(o)
        return o

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
    the map's folder."""

    def __init__(self):
        self.calls = []
        self.shouts = set()          # what sentries call out: text, not names

    @staticmethod
    def _s(names):
        return "[]string{" + ", ".join(json.dumps(n) for n in names) + "}"

    def sentry(self, name, face, rouse=(), shout="Intruder!"):
        self.shouts.add(shout)
        self.calls.append(f'Sentry({json.dumps(name)}, {face[0]:.1f}, {face[1]:.1f}, {self._s(rouse)}, {json.dumps(shout)})')

    def patrol(self, name, route, pause=2.0, loop=True):
        self.calls.append(f'Patrol({json.dumps(name)}, {self._s(route)}, {pause:.1f}, {"true" if loop else "false"})')

    def pack(self, leader, members):
        self.calls.append(f'Pack({json.dumps(leader)}, {self._s(members)})')

    def skittish(self, name, flee=3.0):
        self.calls.append(f'Skittish({json.dumps(name)}, {flee:.1f})')

    def ambush(self, names, at, reach=140.0):
        self.calls.append(f'Ambush({self._s(names)}, {at[0]:.1f}, {at[1]:.1f}, {reach:.1f})')

    def townsfolk(self, name, spots, linger=4.0):
        self.calls.append(f'Townsfolk({json.dumps(name)}, {self._s(spots)}, {linger:.1f})')

    def villager(self, name, spots, home, linger=5.0, fear=180.0):
        """Townsfolk who run for their home doorstep (waypoint `home`) while a hostile creature is within `fear` px."""
        self.calls.append(f'Villager({json.dumps(name)}, {self._s(spots)}, {linger:.1f}, {json.dumps(home)}, {fear:.1f})')

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
        return sorted(objs - self.shouts), sorted(wps)

    def files(self, map_name):
        """{filename: Go source} for the map's folder, package named after the map (as OpenNox expects)."""
        if not self.calls: return {}
        pkg = map_name.lower()
        lib = open(os.path.join(HERE, "behaviours", "behaviours.go"), encoding="utf-8").read().replace("package PKG", f"package {pkg}", 1)
        objs, wps = self.names()
        cfg = (f"package {pkg}\n\n// Who does what on {map_name} (written by dystopiannox mapgen/kit/npcs.py).\n\n"
               'import "github.com/noxworld-dev/noxscript/ns/v4"\n\n'
               # set up once, on MapInitialize or after a second of frames if it never fires (as kit/quests.py)
               "var behavioursSetUp bool\n\nfunc setUpBehaviours() {\n\tif behavioursSetUp {\n\t\treturn\n\t}\n"
               "\tbehavioursSetUp = true\n" + "".join(f"\t{c}\n" for c in self.calls) +
               "\tprintln(\"behaviours: started\")\n}\n\nfunc init() {\n\tns.OnMapEvent(ns.MapInitialize, setUpBehaviours)\n"
               "\tbframes := 0\n\tns.OnEachFrame(1, func() {\n\t\tif bframes++; bframes == 30 {\n\t\t\tsetUpBehaviours()\n\t\t}\n\t})\n"
               f"\tDiagnose({self._s(objs)}, {self._s(wps)})\n}}\n")
        out = {"behaviours.go": lib, "config.go": cfg}
        if getattr(self, "weapons", False):
            out["weapons.go"] = open(os.path.join(HERE, "behaviours", "weapons.go"), encoding="utf-8").read().replace(
                "package PKG", f"package {pkg}", 1)
        return out
