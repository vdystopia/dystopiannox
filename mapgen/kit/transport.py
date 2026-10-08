"""Transporters: lifts, stairs, portals and passages. Each moves the player from one place on the map to another (the
far place most often a part of the map that cannot be walked to), so one call lays any of them:

    tp = Transporters(m)
    tp.add("lift", a, b, "CellarLift", style="cave")              # platform at a, pit at b; two-way by nature
    tp.add("stairs", a, b, "TowerStair", style="castle")          # stairs down at a, stairs up at b
    tp.add("portal", a, b, "IslePortal", two_way=False)           # a pentagram at a, the player lands at b
    tp.add("passage", a, b, "CaveMouth")                          # walk into a, the screen fades, wake at b

a and b are world pixels (x, y). What Westwood does and why each piece stands where it does is rules/TRANSPORTERS.md
(measured by rules/transporters.py); the process is skills/nox-transporters/SKILL.md. The engine:
- lift: an ELEVATOR platform and its pit name each other by extent; an enabled platform rides down and up by itself
  (a second at each end), carrying whoever stands on it to the pit and whoever stands on the pit back up.
- stairs and portal: TRANSPORTER pads (TeleportPentagram, seen; InvisibleTeleportPentagram, unseen and at once) send
  whoever stands on them to the object they name: here always an arrival marker (an InvisibleTeleportPentagram that
  names nothing) a step off the pad that leads back, never onto it (Westwood links no two pads both ways: the player
  would be sent straight back).
- passage: no object does it: the map's script (transport.go, written at build) fades the screen when the player
  steps on the spot, moves him and lifts the fade, as Westwood's GoToMine / EnterTemple scripts do.

The build writes <Name>.transport.json beside the map (what was meant: the ends, the arrivals, one-way or not, the
places each serves), which the checker reads (validate/checks.py check_transport), and transport.go (the passages,
a self-check that every end exists, and a log line each time a transporter moves the player).
"""
import json, math, os

from nox import load_rules, CELL

KINDS = ("lift", "stairs", "portal", "passage")

# setting -> (platform, pit, base piece laid under both ends or None). Westwood's lifts by where they stand:
# CaveElevator in caves, sewers and dungeons (89; a CaveElevatorBase under 84 of them and 59 of their pits),
# Elevator in the mines (43, Con01A's mine lifts), GreenElevator in Ix and its swamps (31), LOTDElevator in the Land of
# the Dead (24), RedElevator at the volcano (7), WhiteElevator in Galava's castle (8).
LIFTS = {
    "cave": ("CaveElevator", "CaveElevatorPit", "CaveElevatorBase"),
    "dungeon": ("CaveElevator", "CaveElevatorPit", "CaveElevatorBase"),
    "mine": ("Elevator", "ElevatorPit", None),
    "town": ("GreenElevator", "GreenElevatorPit", None),
    "swamp": ("GreenElevator", "GreenElevatorPit", None),
    "castle": ("WhiteElevator", "WhiteElevatorPit", None),
    "lotd": ("LOTDElevator", "LOTDElevatorPit", None),
    "lava": ("RedElevator", "RedElevatorPit", None),
}
# setting -> (stairs down, stairs up): the pairs Westwood links within one map (Con07B and War07A's castle, Wiz02C's
# carpeted castle stairs, Con06b's Dun Mir, Con04b's crypt stairs, which are EXIT pieces naming no map: inert solo)
STAIRS = {
    "castle": ("GalavaStairsDown", "GalavaStairsUp1"),
    "castle_carpet": ("GalavaStairsDownCarpeted", "GalavaStairsUp1Carpeted"),
    "dunmir": ("DunMirStairsDown", "DunMirStairsUp"),
    "crypt": ("LOTDStairsExitBack1", "LOTDStairsUpExit1"),
}
# stairs Westwood measured too few times for the rules file: (pad offset, arrival offset) from the main piece
STAIRS_EXTRA = {"LOTDStairsExitBack1": ((1, 0), (-29, -31)), "LOTDStairsUpExit1": ((-1, -2), (33, 30))}
PAD, MARKER, INVISIBLE_PAD = "TeleportPentagram", "InvisibleTeleportPentagram", "InvisibleTeleportPentagram"
# Westwood's arrival beside the pad that leads back: 43-194 px, median 59 (rules/out/transporters.json returns)
RETURN_GAP = 59
PASSAGE_R = 26        # px: how near the passage's spot the player must step (a little over a cell)


def geometry():
    return load_rules("transporters")["summary"]["geometry"]


class Transporter:
    def __init__(self, kind, name, a, b, two_way, enabled, style):
        self.kind, self.name, self.a, self.b = kind, name, tuple(a), tuple(b)
        self.two_way, self.enabled, self.style = two_way, enabled, style
        self.arrive_a = self.arrive_b = None       # where the player lands at each end (arrive_a only when two-way)
        self.objects = []                           # spec objects laid, with their role
        self.sources = []                           # script names of what sends the player (enable/disable these)
        self.serves = []                            # spots the far end exists for (the checker proves them reachable)

    def record(self):
        return dict(kind=self.kind, name=self.name, style=self.style, a=list(self.a), b=list(self.b),
                    arrive_a=list(self.arrive_a) if self.arrive_a else None, arrive_b=list(self.arrive_b),
                    two_way=self.two_way, enabled=self.enabled, sources=self.sources,
                    serves=[list(s) for s in self.serves],
                    objects=[dict(role=r, type=o["type"], x=o["x"], y=o["y"], scr=o.get("scr", "")) for r, o in self.objects])


class Transporters:
    """The map's transporters. add() lays one; the build (Spec.build) writes the sidecar and transport.go."""

    def __init__(self, spec):
        self.m = spec
        self.items = []
        spec.transporters = self

    # ---- the one call -------------------------------------------------------------------------------------------
    def add(self, kind, a, b, name, style=None, two_way=True, enabled=True, arrive_a=None, arrive_b=None,
            invisible=False, serves=()):
        """Lays a transporter from a to b (world px) and returns it.

        kind: "lift" (platform at a, pit at b; always two-way), "stairs" (stairs down at a, up at b), "portal" (a
        pentagram at a; two-way: one at b too), "passage" (a scripted fade: step on a, wake at b).
        name: the script name of what sends the player from a (from b: name + "Back"; a lift's pit: name + "Pit").
        style: lifts by LIFTS (cave, dungeon, mine, town, swamp, castle, lotd, lava), stairs by STAIRS (castle,
        castle_carpet, dunmir, crypt).
        enabled: False lays it switched off: the story turns it on with A.enable on each of t.sources.
        arrive_a / arrive_b: where the player lands (default: Westwood's spot for the kind; a pad's landing a clear
        spot RETURN_GAP px off the pad that leads back).
        invisible: a portal with an unseen pad (InvisibleTeleportPentagram: no glow, sends at once).
        serves: spots the transporter is there for (the chest on the island): the checker proves each reachable on
        foot from where it lands the player (either end of a two-way one)."""
        assert kind in KINDS, f"kind must be one of {KINDS}"
        assert name and len(name) + 4 <= 31, "a transporter's name becomes script names: keep it short"
        assert not any(t.name == name for t in self.items), f"transporter {name} laid twice"
        t = Transporter(kind, name, a, b, two_way, enabled, style)
        t.serves = [tuple(s) for s in serves]
        getattr(self, "_" + kind)(t, arrive_a, arrive_b, invisible)
        self.items.append(t)
        return t

    # ---- the kinds -----------------------------------------------------------------------------------------------
    def _put(self, t, role, type_, x, y, **extra):
        o = self.m.obj_px(type_, x, y, **extra)
        t.objects.append((role, o))
        return o

    def _lift(self, t, arrive_a, arrive_b, invisible):
        assert t.two_way, "a lift always rides both ways: a one-way move is a portal or a passage"
        platform, pit, base = LIFTS[t.style or "cave"]
        k = t.name
        self._put(t, "platform", platform, *t.a, scr=k, key=k, link=k + "Pit",
                  **({} if t.enabled else {"enabled": False}))
        self._put(t, "pit", pit, *t.b, scr=k + "Pit", key=k + "Pit", link=k)
        if base:
            self._put(t, "base", base, *t.a)
            self._put(t, "base", base, *t.b)
        t.sources = [k]
        t.arrive_b, t.arrive_a = t.b, t.a            # the engine puts the rider on the pit's, the platform's centre

    def _stairs(self, t, arrive_a, arrive_b, invisible):
        down, up = STAIRS[t.style or "castle"]
        geo = geometry()["stairs"]

        def shape(main):
            g = geo.get(main)
            if g and g.get("pad") is not None and g.get("arrive") is not None:
                return g["pieces"], tuple(g["pad"]), tuple(g["arrive"])
            pad, arr = STAIRS_EXTRA[main]
            return (g or {}).get("pieces", []), pad, arr

        ends = []
        for main, (x, y), role in ((down, t.a, "down"), (up, t.b, "up")):
            pieces, pad, arr = shape(main)
            extra = {}
            if main.startswith("LOTDStairs"):          # EXIT pieces: naming no map they do nothing in a solo game
                extra = dict(xfer=dict(MapName="", ExitX=float(x), ExitY=float(y)))
            self._put(t, "stairs_" + role, main, x, y, **extra)
            for p, dx, dy in pieces:
                self._put(t, "piece", p, x + dx, y + dy)
            ends.append(((x + pad[0], y + pad[1]), (x + arr[0], y + arr[1])))
        (pad_a, land_a), (pad_b, land_b) = ends
        t.arrive_b = tuple(arrive_b or land_b)
        t.arrive_a = tuple(arrive_a or land_a) if t.two_way else None
        k = t.name
        off = {} if t.enabled else {"enabled": False}
        self._put(t, "pad", INVISIBLE_PAD, *pad_a, scr=k, key=k, link=k + "To", **off)
        self._put(t, "arrival", MARKER, *t.arrive_b, key=k + "To")
        t.sources = [k]
        if t.two_way:
            self._put(t, "pad_back", INVISIBLE_PAD, *pad_b, scr=k + "Back", key=k + "Back", link=k + "BackTo", **off)
            self._put(t, "arrival_back", MARKER, *t.arrive_a, key=k + "BackTo")
            t.sources.append(k + "Back")

    def _portal(self, t, arrive_a, arrive_b, invisible):
        pad = INVISIBLE_PAD if invisible else PAD
        k = t.name
        off = {} if t.enabled else {"enabled": False}
        if t.two_way:
            t.arrive_b = tuple(arrive_b or self.clear_spot(t.b, RETURN_GAP))
            t.arrive_a = tuple(arrive_a or self.clear_spot(t.a, RETURN_GAP))
        else:
            t.arrive_b = tuple(arrive_b or t.b)
        self._put(t, "pad", pad, *t.a, scr=k, key=k, link=k + "To", **off)
        self._put(t, "arrival", MARKER, *t.arrive_b, key=k + "To")
        t.sources = [k]
        if t.two_way:
            self._put(t, "pad_back", pad, *t.b, scr=k + "Back", key=k + "Back", link=k + "BackTo", **off)
            self._put(t, "arrival_back", MARKER, *t.arrive_a, key=k + "BackTo")
            t.sources.append(k + "Back")

    def _passage(self, t, arrive_a, arrive_b, invisible):
        # the spot is an arrival marker that names nothing (it does nothing by itself): the script finds it by name,
        # so A.enable / A.disable work on a passage as on any transporter
        k = t.name
        off = {} if t.enabled else {"enabled": False}
        if t.two_way:
            t.arrive_b = tuple(arrive_b or self.clear_spot(t.b, RETURN_GAP))
            t.arrive_a = tuple(arrive_a or self.clear_spot(t.a, RETURN_GAP))
        else:
            t.arrive_b = tuple(arrive_b or t.b)
        self._put(t, "spot", MARKER, *t.a, scr=k, **off)
        t.sources = [k]
        if t.two_way:
            self._put(t, "spot_back", MARKER, *t.b, scr=k + "Back", **off)
            t.sources.append(k + "Back")

    # ---- where to land -------------------------------------------------------------------------------------------
    def clear_spot(self, at, gap):
        """A spot `gap` px from `at` on floor, with the most room to the walls and objects: where Westwood sets the
        arrival beside a pad that leads back (43-194 px, median 59), so the player lands beside it, not on it."""
        m = self.m
        cover = set()
        for (x, y) in m.floor: cover |= {(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)}
        walls = set(m.wallmap)
        objs = [(o["x"], o["y"]) for o in m.d["objects"] if "x" in o]
        best, score = None, -1
        for k in range(16):
            ang = k * math.pi / 8
            for g in (gap, gap * 0.8, gap * 1.3):
                x, y = at[0] + g * math.cos(ang), at[1] + g * math.sin(ang)
                c = (int(x // CELL), int(y // CELL))
                if c not in cover or c in walls: continue
                wall = min((math.hypot(w[0] * CELL + CELL / 2 - x, w[1] * CELL + CELL / 2 - y) for w in walls
                            if abs(w[0] - c[0]) <= 6 and abs(w[1] - c[1]) <= 6), default=6 * CELL)
                obj = min((math.hypot(ox - x, oy - y) for ox, oy in objs if abs(ox - x) < 120 and abs(oy - y) < 120),
                          default=120)
                if wall < 34 or obj < 26: continue
                s = min(wall, 90) + min(obj, 60) * 0.5 - abs(g - gap) * 0.3
                if s > score: best, score = (round(x, 1), round(y, 1)), s
        assert best, f"no clear spot to land {gap} px round {at}: give arrive_a / arrive_b"
        return best

    # ---- the build ------------------------------------------------------------------------------------------------
    def records(self):
        return [t.record() for t in self.items]

    def write(self, out_dir, name):
        """<Name>.transport.json: the transporters as meant, for the checker and the QA gate."""
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, name + ".transport.json"), "w", encoding="utf-8") as f:
            json.dump(self.records(), f, indent=1)

    def script(self, pkg):
        """transport.go: the passages (fade, move, lift the fade), a self-check that every named end exists, and a
        log line each time a transporter of this map moves the player (the playtest's and the client test's proof)."""
        ends = []
        for t in self.items:
            ends.append((t.name, t.arrive_b))
            if t.two_way and t.arrive_a: ends.append((t.name + "Back", t.arrive_a))
        passages = []
        for t in self.items:
            if t.kind != "passage": continue
            passages.append((t.name, t.arrive_b))
            if t.two_way: passages.append((t.name + "Back", t.arrive_a))
        names = sorted({o["scr"] for t in self.items for _, o in t.objects if o.get("scr")})
        go = lambda s: '"' + s.replace('"', '') + '"'
        arr = ", ".join(f"{{{go(n)}, {x:.1f}, {y:.1f}}}" for n, (x, y) in ends)
        pas = ", ".join(f"{{{go(n)}, {x:.1f}, {y:.1f}}}" for n, (x, y) in passages)
        return TRANSPORT_GO.replace("package PKG", f"package {pkg}", 1).replace(
            "/*NAMES*/", ", ".join(go(n) for n in names)).replace("/*ARRIVALS*/", arr).replace(
            "/*PASSAGES*/", pas).replace("/*RADIUS*/", f"{PASSAGE_R}")

    def finish(self, spec, out_dir):
        """Run by Spec.build: the sidecar and the script."""
        name = spec.d["name"]
        self.write(out_dir, name)
        if self.items:
            spec.scripts["transport.go"] = self.script(name.lower())


TRANSPORT_GO = r'''package PKG

// The map's transporters (written by dystopiannox mapgen/kit/transport.py): the scripted passages, a self-check that
// every named end exists, and a log line each time a transporter moves the player.

import (
	"github.com/noxworld-dev/noxscript/ns/v4"
)

type tpEnd struct {
	Name string
	X, Y float32
}

var (
	tpNames    = []string{/*NAMES*/}
	tpArrivals = []tpEnd{/*ARRIVALS*/}
	tpPassages = []tpEnd{/*PASSAGES*/}
)

func tpDist(ax, ay, bx, by float32) float32 {
	dx, dy := ax-bx, ay-by
	if dx < 0 {
		dx = -dx
	}
	if dy < 0 {
		dy = -dy
	}
	if dx > dy {
		return dx + dy/2
	}
	return dy + dx/2
}

func init() {
	checked := false
	var lastX, lastY float32
	have := false
	busy := 0         // frames left of a passage's fade
	var goX, goY float32
	ns.OnEachFrame(1, func() {
		if !checked {
			checked = true
			found := 0
			for _, n := range tpNames {
				if ns.Object(n) != nil {
					found++
				} else {
					println("transport: missing", n)
				}
			}
			println("transport self-check: ends", found, "of", len(tpNames))
		}
		p := ns.GetHost()
		if p == nil {
			return
		}
		pos := p.Pos()
		// a passage: the player steps on its spot (enabled), the screen fades, he wakes at the far end
		if busy > 0 {
			busy--
			if busy == 0 {
				p.SetPos(ns.Ptf(goX, goY))
				p.Freeze(false)
				ns.UnBlind()
				pos = p.Pos()
			}
		} else {
			for _, e := range tpPassages {
				o := ns.Object(e.Name)
				if o == nil || !o.IsEnabled() {
					continue
				}
				at := o.Pos()
				if tpDist(pos.X, pos.Y, at.X, at.Y) < /*RADIUS*/ {
					ns.Blind()
					p.Freeze(true)
					goX, goY = e.X, e.Y
					busy = 30
					break
				}
			}
		}
		// the log: a jump of more than four cells in a frame, landing by one of this map's arrivals
		if have && tpDist(pos.X, pos.Y, lastX, lastY) > 92 {
			for _, e := range tpArrivals {
				if tpDist(pos.X, pos.Y, e.X, e.Y) < 70 {
					println("transport:", e.Name, "moved the player from", int(lastX), int(lastY), "to", int(pos.X), int(pos.Y))
					break
				}
			}
		}
		lastX, lastY, have = pos.X, pos.Y, true
	})
}
'''
