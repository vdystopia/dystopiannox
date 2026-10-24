"""Traps: the objects Westwood's traps are built from, placed in a map, and the script that drives them
(kit/behaviours/traps.go; the research behind every number: rules/TRAPS.md).

A trap is objects plus logic. The objects are the game's own (spikes that rise from the floor, flames, fire grates,
arrow traps in the walls, spike blocks, rotating spikes, pits, crumbling floor, sentry globes, pressure plates,
levers, buttons). The logic is data the map's script runs every frame:

    T = Traps(m)                                     # m: the nox.Spec
    g = T.group("F1", [T.obj("Flame", x, y), ...])   # trap objects with script names, switched together
    T.clock("F1c", "F1", period=60, on=[(0, 30)])    # on for the first second of every two
    T.mover("B1", [T.obj("SpikeBlock", x, y)], path=[(x0, y0), (x1, y1)], speed=3.0, mode="pingpong", pause=15)
    T.zone("P1", (x, y), 22.6, acts=[T.act("pulse", "S1", frames=40)])          # a pressure plate's diamond
    T.switch("L1", lever_name, acts=[T.act("disarm", "F1c")])
    T.attach()                                       # LAST: traps.go + traps_config.go into m.scripts

Everything is also written as data (`T.data()`: <map>.traps.json beside the map) for the trap simulator
(review/traps/sim.py), which replays the clocks, movers and zones frame by frame against a player's moves to judge
whether a trap can be passed, how tight its windows are and what a careless run costs.

Frames are 1/30 s; positions are world px (units).
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))


def _go_str(s):
    return json.dumps(s)


def _go_pt(p):
    return f"ns.Ptf({float(p[0]):.1f}, {float(p[1]):.1f})"


class Traps:
    def __init__(self, spec, prefix="T"):
        self.spec, self.prefix = spec, prefix
        self.groups, self.clocks, self.movers, self.zones, self.switches = {}, {}, {}, {}, []
        self.starts = []                 # extra Go lines run at the start (after the clocks start)
        self.count = 0
        self.objects = {}                # script name -> the object dict (type, x, y)
        self.labels = []                 # station labels (TL-FLAME-03 ...) with their boxes, for the page and sim

    # ---- objects ---------------------------------------------------------------------------------------------
    def obj(self, type_, x, y, name=None, enabled=True, **extra):
        """A trap object with a script name; `enabled=False` places it switched off (stored flags: Westwood's
        cflags without ENABLED)."""
        self.count += 1
        name = name or f"{self.prefix}{type_}{self.count}"
        o = self.spec.obj_px(type_, x, y, scr=name, **extra)
        if not enabled:
            o["enabled"] = False
        self.objects[name] = o
        return name

    def group(self, name, objs):
        self.groups[name] = list(objs)
        return name

    # ---- logic -------------------------------------------------------------------------------------------------
    @staticmethod
    def act(kind, target="", delay=0, frames=0, spell="", src=None, dst=None, walls=(), text=""):
        return dict(kind=kind, target=target, delay=int(delay), frames=int(frames), spell=spell,
                    src=list(src) if src else None, dst=list(dst) if dst else None,
                    walls=[list(w) for w in walls], text=text)

    def clock(self, name, group, period, on, phase=0, armed=True):
        assert all(0 <= a < b <= period for a, b in on), (name, on, period)
        self.clocks[name] = dict(name=name, group=group, period=int(period), on=[[int(a), int(b)] for a, b in on],
                                 phase=int(phase), armed=armed)
        return name

    def mover(self, name, objs, path, speed, mode="pingpong", pause=0, armed=True):
        assert len(path) >= 2 and speed > 0
        self.movers[name] = dict(name=name, objs=list(objs), path=[[round(x, 1), round(y, 1)] for x, y in path],
                                 speed=float(speed), mode=mode, pause=int(pause), armed=armed)
        return name

    def zone(self, name, centre, r, shape="diamond", h=0.0, who="player", once=False, rearm=0, armed=True,
             acts=(), release=()):
        self.zones[name] = dict(name=name, shape=shape, c=[round(centre[0], 1), round(centre[1], 1)], r=float(r),
                                h=float(h), who=who, once=once, rearm=int(rearm), armed=armed, acts=list(acts),
                                release=list(release))
        return name

    def switch(self, name, obj, acts=()):
        self.switches.append(dict(name=name, obj=obj, acts=list(acts)))
        return name

    def label(self, label, title, box, kind, difficulty, notes=""):
        """A station's label for the rating page and the simulator: box = (x0, y0, x1, y1) world px."""
        self.labels.append(dict(label=label, title=title, box=[round(v, 1) for v in box], kind=kind,
                                difficulty=difficulty, notes=notes))

    # ---- output ------------------------------------------------------------------------------------------------
    def data(self):
        return dict(groups=self.groups, clocks=list(self.clocks.values()), movers=list(self.movers.values()),
                    zones=list(self.zones.values()), switches=self.switches, labels=self.labels,
                    objects={k: dict(type=v["type"], x=v["x"], y=v["y"], enabled=v.get("enabled", True))
                             for k, v in self.objects.items()})

    def _act_go(self, a):
        parts = [f"Kind: {_go_str(a['kind'])}"]
        if a["target"]: parts.append(f"Target: {_go_str(a['target'])}")
        if a["delay"]: parts.append(f"Delay: {a['delay']}")
        if a["frames"]: parts.append(f"Frames: {a['frames']}")
        if a["spell"]: parts.append(f"Spell: {_go_str(a['spell'])}")
        if a["src"]: parts.append(f"From: {_go_pt(a['src'])}")
        if a["dst"]: parts.append(f"To: {_go_pt(a['dst'])}")
        if a["walls"]: parts.append("Walls: [][2]int{" + ", ".join(f"{{{w[0]}, {w[1]}}}" for w in a["walls"]) + "}")
        if a["text"]: parts.append(f"Text: {_go_str(a['text'])}")
        return "{" + ", ".join(parts) + "}"

    def _acts_go(self, acts):
        return "[]trapAct{" + ", ".join(self._act_go(a) for a in acts) + "}"

    def config_go(self, pkg):
        L = [f"package {pkg}", "", f"// The traps on {self.spec.d['name']} (written by dystopiannox mapgen/kit/traps.py).", "",
             'import "github.com/noxworld-dev/noxscript/ns/v4"', "", "var trapsSetUp bool", "",
             "func setUpTraps() {", "\tif trapsSetUp {", "\t\treturn", "\t}", "\ttrapsSetUp = true"]
        for g, objs in self.groups.items():
            L.append(f"\tTrapGroup({_go_str(g)}, " + ", ".join(_go_str(o) for o in objs) + ")")
        for c in self.clocks.values():
            on = "[][2]int{" + ", ".join(f"{{{a}, {b}}}" for a, b in c["on"]) + "}"
            L.append(f"\tTrapClock(trapClock{{Name: {_go_str(c['name'])}, Group: {_go_str(c['group'])}, "
                     f"Period: {c['period']}, On: {on}, Phase: {c['phase']}, Armed: {str(c['armed']).lower()}}})")
        for mv in self.movers.values():
            path = "[]ns.Pointf{" + ", ".join(_go_pt(p) for p in mv["path"]) + "}"
            objs = "[]string{" + ", ".join(_go_str(o) for o in mv["objs"]) + "}"
            L.append(f"\tTrapMover(trapMover{{Name: {_go_str(mv['name'])}, Objs: {objs}, Path: {path}, "
                     f"Speed: {mv['speed']:.3f}, Mode: {_go_str(mv['mode'])}, Pause: {mv['pause']}, "
                     f"Armed: {str(mv['armed']).lower()}}})")
        for z in self.zones.values():
            L.append(f"\tTrapZone(trapZone{{Name: {_go_str(z['name'])}, Shape: {_go_str(z['shape'])}, "
                     f"C: {_go_pt(z['c'])}, R: {z['r']:.1f}, H: {z['h']:.1f}, Who: {_go_str(z['who'])}, "
                     f"Once: {str(z['once']).lower()}, Rearm: {z['rearm']}, Armed: {str(z['armed']).lower()}, "
                     f"Acts: {self._acts_go(z['acts'])}, Release: {self._acts_go(z['release'])}}})")
        for s in self.switches:
            L.append(f"\tTrapSwitch(trapSwitch{{Name: {_go_str(s['name'])}, Obj: {_go_str(s['obj'])}, "
                     f"Acts: {self._acts_go(s['acts'])}}})")
        L += ["\tStartTraps()"] + [f"\t{x}" for x in self.starts] + ["}", "",
              # on MapInitialize, or after a second of frames if it never fires (the dedicated server: kit/quests.py)
              "func init() {", "\tns.OnMapEvent(ns.MapInitialize, setUpTraps)", "\ttframes := 0",
              "\tns.OnEachFrame(1, func() {", "\t\tif tframes++; tframes == 30 {", "\t\t\tsetUpTraps()", "\t\t}",
              "\t})", "}", ""]
        return "\n".join(L)

    def files(self, map_name):
        pkg = map_name.lower()
        lib = open(os.path.join(HERE, "behaviours", "traps.go"), encoding="utf-8").read()
        lib = lib.replace("package PKG", f"package {pkg}", 1)
        return {"traps.go": lib, "traps_config.go": self.config_go(pkg)}

    def attach(self):
        self.spec.scripts.update(self.files(self.spec.d["name"]))
        self.spec.traps = self.data()

    def write(self, out_dir):
        with open(os.path.join(out_dir, f"{self.spec.d['name']}.traps.json"), "w", encoding="utf-8") as f:
            json.dump(self.data(), f, indent=1)
