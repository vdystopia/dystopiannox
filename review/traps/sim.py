"""The trap simulator: can a player pass each station, how tight is it, what does a careless run cost?

    py review/traps/sim.py <map_out_dir>                 every station of a built trap map (<Name>.traps.json and
                                                         <Name>.lab.json beside the .map) -> <Name>.sim.json + .sim.md
    py review/traps/sim.py <map_out_dir> --only TL-SPIKE-03 [--trace]

It replays the map's trap logic (kit/traps.py data: groups, clocks, movers, zones, watches, actions) frame by frame
against a player who moves as the game measured (rules/TRAPS.md 1): walk 3.3 units a frame, run 6.9, a jump of 18
frames airborne at run speed (one a second), radius 10. Damage per frame by thing (ENGINE.md, the bench): spikes 1
per spike touched, Flame 1, LargeFlame 2, FireGrateFlame 5, RotatingSpikes 4 (and a shove), SpikeBlock 1 (and a
shove), arrows 25 a hit (one a second while held, one volley per switch-on), skull fireballs 90, a sentry beam is
death, an open pit is a fall; a jump passes over spikes, flames, pits, plates and crumbling floor, not over blocks,
blades, arrows or beams.

For each station:
1. **plan**: a search over (time, place, jump readiness) on a half-square grid in 3-frame ticks, from the way in to
   the way out, minimising damage (then time); visible plates are avoided on foot (a jump passes them); a lever on
   the way is tried both pulled and not. The best plan's damage, time, waits and jumps.
2. **slack**: the same search from six other moments of the traps' cycles (the player arrives when he arrives): the
   share of moments from which the station is passed with 10 HP or less.
3. **margin**: the best plan replayed exactly (frame by frame, plates and all) and again with the player 4 frames
   late: what a slightly mistimed run costs.
4. **careless**: walking, and running, straight down the middle without waiting: damage, or fell / died.
Verdicts (rules/TRAPS.md T2-T4): IMPOSSIBLE (no plan under 60 HP, 90 for hard), TOO EASY (a careless walk and run
both cost under 35 HP and neither falls), TIER (a standard station that needs more than 25 HP or has slack under
0.5; a hard station a careless walk survives with under 60 HP), else PASS.
"""
import argparse, json, math, os, sys
import numpy as np

SQ = 32.5
FPT = 2                        # frames a tick
CELL = 0.4                     # squares a grid cell: a step of one cell a tick is a run (6.5 units a frame)
WALK, RUN = 3.3, 6.9           # units a frame
JUMP_FRAMES, JUMP_COOL = 18, 30
JT = JUMP_FRAMES // 2          # ticks airborne (set from FPT below)
PLAYER_R = 10.0
LETHAL = 1000.0
SHOVE = 30.0                   # the planner's price for being touched by a moving block (it shoves: into pits too)
PLATE_PENALTY = 15.0
JUMP_COST = 2.0                # a jump is free in HP but costs stamina: the planner jumps only when it helps
H_TICKS = 630                  # 42 s
JT = JUMP_FRAMES // FPT        # a jump: ticks airborne, cells covered straight / diagonally (~124 units at run speed)
JD = int(124 / (SQ * CELL))     # rounded down (3.6 squares): a plan never asks for a longer jump than the game's
JDD = int(124 / 1.414 / (SQ * CELL))
PLAN_MARGIN = 5.0              # px: the planner keeps this much farther from contact than the replay needs
WALL_GAP = 0.35                # squares: a player's centre stays this far from a wall line

# per-frame contact damage: (radius, damage, jumpable)
SMALL = {"Spike": (3, 1.0, True), "PeriodicSpike": (3, 1.0, True), "SmallFlame": (4, 1.0, True),
         "MediumFlame": (6, 1.0, True), "Flame": (8, 1.0, True), "LargeFlame": (12, 2.0, True),
         "FireGrateFlame": (12, 5.0, True), "SmallFlameImmobile": (4, 1.0, True), "FlameImmobile": (8, 1.0, True),
         "MediumFlameImmobile": (6, 1.0, True), "LargeFlameImmobile": (12, 2.0, True), "Glyph": (10, 10.0, True),
         "BearTrap": (10, 3.0, True), "PoisonGasTrap": (10, 3.0, True), "CampFire": (10, 3.0, True)}
BLOCKS = {"SpikeBlock": 1.0, "StoneBlock": 0.0, "IronBlock": 0.0, "SpikeBlockImmobile": 1.0}
BLADES = {"RotatingSpikes": (12, 4.0), "RotatingSpikesImmobile": (12, 4.0)}
PITS = ("Pit", "ForestPit")
CRUMBLE = ("PitCrumblingFloor",)
SENTRIES = ("SentryGlobe", "SentryGlobeN", "SentryGlobeE", "SentryGlobeS", "SentryGlobeW", "SentryGlobeMovable")
FIREBALL, BALL_R = 12.0, 18.0  # a skull gun's fireball: px a frame; it hits a player whose centre comes this close
SHOOTERS = {"ArrowTrap1": ((1, 1), 25.0), "ArrowTrap2": ((-1, 1), 25.0), "Skull1": ((-1, -1), 90.0),
            "Skull2": ((1, -1), 90.0), "Skull3": ((-1, 1), 90.0), "Skull4": ((1, 1), 90.0)}


# ---- the trap logic, replayed ----------------------------------------------------------------------------------
class World:
    """kit/behaviours/traps.go in Python: groups, clocks, movers, zones, watches and the action queue."""

    def __init__(self, data, offset=0, events=()):
        self.d = data
        self.en = {k: v.get("enabled", True) for k, v in data["objects"].items()}
        self.pos = {k: (v["x"], v["y"]) for k, v in data["objects"].items()}
        self.groups = data["groups"]
        self.clocks = [dict(c) for c in data["clocks"]]
        self.movers = []
        for m in data["movers"]:
            mm = dict(m, seg=0, along=0.0, dir=1, wait=0, done=False)
            f = self.pos.get(m["objs"][0], m["path"][0])
            mm["offs"] = [(self.pos[o][0] - f[0], self.pos[o][1] - f[1]) if o in self.pos else (0, 0) for o in m["objs"]]
            self.movers.append(mm)
            self._place(mm)
        self.zones = [dict(z, inn=False, fired=False, cool=0, state=False) for z in data["zones"]]
        self.watches = [dict(w, done=False) for w in data.get("watches", [])]
        self.queue = []
        self.f = 0
        self.offset = offset
        self.events = sorted(events, key=lambda e: e[0])   # (frame, acts): a lever pulled by the plan
        self.closed = set()                       # secret walls closed now (the station model sets the start)
        self.wall_changed = set()
        self.changed = set()                      # objects whose state changed this frame
        self.volleys = set()                      # shooters switched on this frame
        for m in self.movers:                     # arriving `offset` frames later: the movers are that far on
            for _ in range(offset if m["armed"] else 0):
                if m["done"]: break
                self.step_mover(m)

    def set_group(self, g, on):
        for o in self.groups.get(g, []):
            if self.en.get(o) != on:
                self.en[o] = on
                self.changed.add(o)
                if on: self.volleys.add(o)

    def do(self, a):
        k, t = a["kind"], a.get("target", "")
        if k == "on": self.set_group(t, True)
        elif k == "off": self.set_group(t, False)
        elif k == "toggle":
            g = self.groups.get(t, [])
            self.set_group(t, not (g and self.en.get(g[0])))
        elif k == "pulse":
            self.set_group(t, True)
            self.queue.append((self.f + a.get("frames", 0), dict(kind="off", target=t)))
        elif k in ("arm", "disarm"):
            arm = k == "arm"
            for c in self.clocks:
                if c["name"] == t:
                    if arm and not c["armed"]: c["t0"] = self.f
                    c["armed"] = arm
                    if not arm: self.set_group(c["group"], False)
            for m in self.movers:
                if m["name"] == t: m["armed"] = arm
            for z in self.zones:
                if z["name"] == t: z["armed"] = arm
        elif k == "restart":
            for c in self.clocks:
                if c["name"] == t: c["t0"] = self.f
        elif k == "reset":
            for m in self.movers:
                if m["name"] == t:
                    m.update(seg=0, along=0.0, dir=1, wait=0, done=False); self._place(m)
            for z in self.zones:
                if z["name"] == t: z.update(fired=False, inn=False, cool=0)
        elif k in ("walls_open", "walls_close"):
            for wc in a.get("walls", []):
                wc = tuple(wc)
                if k == "walls_open" and wc in self.closed: self.closed.discard(wc); self.wall_changed.add(wc)
                if k == "walls_close" and wc not in self.closed: self.closed.add(wc); self.wall_changed.add(wc)
        # cast, wake, say, log, sound: no effect on the floor the simulator reads

    def fire(self, acts):
        for a in acts:
            if a.get("delay", 0) > 0: self.queue.append((self.f + a["delay"], a))
            else: self.do(a)

    def _place(self, m):
        p = self.mpoint(m)
        for o, (ox, oy) in zip(m["objs"], m["offs"]):
            self.pos[o] = (p[0] + ox, p[1] + oy)

    @staticmethod
    def mpoint(m):
        P = m["path"]
        a, b = P[m["seg"]], P[(m["seg"] + 1) % len(P)]
        L = math.dist(a, b) or 1e-9
        t = m["along"] / L
        return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t

    def step_mover(self, m):
        if m["wait"] > 0:
            m["wait"] -= 1; return
        P, n = m["path"], len(m["path"])
        last = n if m["mode"] == "loop" else n - 1
        left = m["speed"]
        while left > 0:
            a, b = P[m["seg"]], P[(m["seg"] + 1) % n]
            L = math.dist(a, b)
            if m["dir"] > 0:
                if m["along"] + left < L:
                    m["along"] += left; break
                left -= L - m["along"]; m["seg"] += 1; m["along"] = 0.0
                if m["seg"] >= last:
                    if m["mode"] == "loop": m["seg"] = 0; m["wait"] = m["pause"]
                    elif m["mode"] == "once": m["seg"] = last - 1; m["along"] = math.dist(P[last - 1], P[last]); m["done"] = True
                    else: m["seg"] = last - 1; m["along"] = math.dist(P[last - 1], P[last]); m["dir"] = -1; m["wait"] = m["pause"]
                    break
            else:
                if m["along"] - left > 0:
                    m["along"] -= left; break
                left -= m["along"]
                if m["seg"] == 0:
                    m["along"] = 0.0; m["dir"] = 1; m["wait"] = m["pause"]; break
                m["seg"] -= 1; m["along"] = math.dist(P[m["seg"]], P[m["seg"] + 1])
        self._place(m)

    def tick(self, player=None, airborne=False):
        """One frame: actions due, clocks, movers, zones (when a player position is given)."""
        self.f += 1
        self.changed, self.volleys, self.wall_changed = set(), set(), set()
        while self.events and self.events[0][0] <= self.f:
            self.fire(self.events.pop(0)[1])
        due = [q for q in self.queue if q[0] <= self.f]
        self.queue = [q for q in self.queue if q[0] > self.f]
        for _, a in sorted(due, key=lambda q: q[0]):
            self.do(a)
        for c in self.clocks:
            if not c["armed"]: continue
            t = (self.f + self.offset - c.get("t0", 0) + c["phase"]) % c["period"]
            self.set_group(c["group"], any(a <= t < b for a, b in c["on"]))
        for m in self.movers:
            if m["armed"] and not m["done"]: self.step_mover(m)
        if player is not None:
            for z in self.zones:
                if not z["armed"]: continue
                if z["cool"] > 0: z["cool"] -= 1
                occ = in_zone(z, player) and not (z.get("jump") and airborne)
                if occ and not z["inn"]:
                    z["inn"] = True
                    if (not z["once"] or not z["fired"]) and z["cool"] == 0:
                        z["fired"] = True
                        if z.get("toggle") and z["state"]:
                            z["state"] = False; self.fire(z["release"])
                        else:
                            z["state"] = True; self.fire(z["acts"])
                elif not occ and z["inn"]:
                    z["inn"] = False; z["cool"] = z["rearm"]
                    if not z.get("toggle"): self.fire(z["release"])
            for wt in self.watches:                  # an item the player reaches is picked up
                if wt["done"] or wt["obj"] not in self.pos: continue
                ox, oy = self.pos[wt["obj"]]
                if math.hypot(player[0] - ox, player[1] - oy) < 20:
                    wt["done"] = True; self.fire(wt["acts"])


def in_zone(z, p):
    dx, dy = p[0] - z["c"][0], p[1] - z["c"][1]
    if z["shape"] == "circle": return dx * dx + dy * dy <= z["r"] ** 2
    if z["shape"] == "box": return -z["r"] <= dx <= z["r"] and -z["h"] <= dy <= z["h"]
    return abs(dx) + abs(dy) <= z["r"]


def seg_dist(p, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy or 1e-9
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


# ---- a station's frame -----------------------------------------------------------------------------------------
class StationModel:
    def __init__(self, data, st, walls, secret=None):
        secret = secret or {}
        self.secret_state = {tuple(k): v for k, v in secret.items()}
        self.data, self.st = data, st
        self.L, self.W = st["L"], st["W"]
        self.U, self.V = st["along"], st["across"]
        sx, sy = st["start"]
        self.O = (sx - 0.5 * SQ * self.U[0] - self.W / 2 * SQ * self.V[0],
                  sy - 0.5 * SQ * self.U[1] - self.W / 2 * SQ * self.V[1])
        self.NA = int(math.ceil((self.L + 1.1) / CELL))       # to half a square past the way out
        self.NB = int(round(self.W / CELL))
        self.objs = {k: v for k, v in data["objects"].items() if self.inside(v["x"], v["y"], 1.0)}
        movers = [m for m in data["movers"] if any(o in self.objs for o in m["objs"]) or
                  any(self.inside(x, y, 1.0) for x, y in m["path"])]
        for m in movers:
            for o in m["objs"]:
                self.objs[o] = data["objects"][o]
        self.blocked = np.zeros((self.NA, self.NB), bool)
        for (x, y) in walls:
            if (x, y) in self.secret_state: continue      # a secret wall opens: the fields carry it while closed
            cx, cy = (x + 0.5) * 23.0, (y + 0.5) * 23.0
            a, b = self.ab(cx, cy)
            if -1 <= a <= self.L + 1 and 0 < b < self.W:
                for i, j in self.cells_near(a, b, 0.62):
                    self.blocked[i, j] = True
        for j in range(self.NB):                         # the cells along the walls: the player cannot stand there
            _, cb = self.cell_ab(0, j)
            if cb < WALL_GAP or cb > self.W - WALL_GAP: self.blocked[:, j] = True
        self.zones = [z for z in data["zones"] if self.inside(z["c"][0], z["c"][1], 1.0)]
        self.secret = {}                                 # secret wall cell -> the grid cells it blocks while closed
        for (x, y), state in secret.items():
            cx, cy = (x + 0.5) * 23.0, (y + 0.5) * 23.0
            a, b = self.ab(cx, cy)
            if -1 <= a <= self.L + 1 and -0.5 <= b <= self.W + 0.5:
                self.secret[(x, y)] = self.cells_near(a, b, 0.62)

    def inside(self, x, y, pad=0.0):
        a, b = self.ab(x, y)
        return -0.5 - pad <= a <= self.L + 0.5 + pad and -pad <= b <= self.W + pad

    def ab(self, x, y):
        dx, dy = x - self.O[0], y - self.O[1]
        return (dx * self.U[0] + dy * self.U[1]) / SQ, (dx * self.V[0] + dy * self.V[1]) / SQ

    def xy(self, a, b):
        return (self.O[0] + SQ * (a * self.U[0] + b * self.V[0]), self.O[1] + SQ * (a * self.U[1] + b * self.V[1]))

    def cell_ab(self, i, j):
        return (i + 0.5) * CELL - 0.5, (j + 0.5) * CELL

    def cell_of(self, a, b):
        return int(math.floor((a + 0.5) / CELL)), int(math.floor(b / CELL))

    def cells_near(self, a, b, r):
        out = []
        i0, j0 = self.cell_of(a - r, b - r)
        i1, j1 = self.cell_of(a + r, b + r)
        for i in range(max(0, i0), min(self.NA, i1 + 1)):
            for j in range(max(0, j0), min(self.NB, j1 + 1)):
                ca, cb = self.cell_ab(i, j)
                if (ca - a) ** 2 + (cb - b) ** 2 <= r * r: out.append((i, j))
        return out

    def cells_square(self, a, b, h):
        out = []
        for i in range(self.NA):
            ca, _ = self.cell_ab(i, 0)
            if abs(ca - a) >= h: continue
            for j in range(self.NB):
                _, cb = self.cell_ab(0, j)
                if abs(cb - b) < h: out.append((i, j))
        return out

    # ---- the hazard field over time (no player: plates are not pressed) ------------------------------------
    def fields(self, offset=0, events=(), ticks=H_TICKS):
        """ground[t], air[t]: damage a player standing in each cell takes over tick t (3 frames) on foot / in a jump."""
        w = World(self.data, offset, events)
        G = np.zeros((ticks + JT + 2, self.NA, self.NB), np.float32)
        A = np.zeros_like(G)
        static = {}                                     # object -> (cells, ground per frame, air per frame)
        for o, v in self.objs.items():
            t = v["type"]
            a, b = self.ab(v["x"], v["y"])
            if t in SMALL:
                r, dmg, jump = SMALL[t]
                static[o] = (self.cells_near(a, b, (r + PLAYER_R + PLAN_MARGIN) / SQ), dmg, 0.0 if jump else dmg)
            elif t in PITS:
                static[o] = (self.cells_square(a, b, 0.62), LETHAL / FPT, 0.0)        # a margin: the replay falls at the edge
        crumble = [o for o, v in self.objs.items() if v["type"] in CRUMBLE]
        self.crumble_cells = set()
        for o in crumble:
            a, b = self.ab(self.objs[o]["x"], self.objs[o]["y"])
            self.crumble_cells |= set(self.cells_square(a, b, 0.62))
        shooters = {o: v for o, v in self.objs.items() if v["type"] in SHOOTERS}
        lanes = {o: self.lane(v) for o, v in shooters.items()}
        sentries = {o: v for o, v in self.objs.items() if v["type"] in SENTRIES}
        sentry_on = {o: (offset if w.en.get(o, True) else 0) for o in sentries}   # an always-on globe has turned
        dyn = [o for o, v in self.objs.items() if v["type"] in BLOCKS or v["type"] in BLADES]
        skulls = [o for o, v in shooters.items() if v["type"].startswith("Skull")]
        balls = []                                      # skull fireballs in flight: (gun, frame fired)
        base_g = np.zeros((self.NA, self.NB), np.float32)
        base_a = np.zeros_like(base_g)

        def apply(o, sign):
            if o not in static: return
            cells, g, a_ = static[o]
            for i, j in cells:
                base_g[i, j] += sign * g
                base_a[i, j] += sign * a_
        for o in static:
            if w.en.get(o, True): apply(o, +1)
        w.closed = {wc for wc in self.secret if self.secret_state.get(wc, "closed") == "closed"}

        def wall(wc, sign):
            for i, j in self.secret.get(wc, ()):
                base_g[i, j] += sign * LETHAL / FPT
                base_a[i, j] += sign * LETHAL / FPT
        for wc in w.closed: wall(wc, +1)
        for t in range(ticks + JT + 2):
            vol = np.zeros_like(base_g)
            for k in range(FPT):
                w.tick()
                fr = t * FPT + k
                for o in skulls:                        # held on, a skull fires once a second (its fireball flies)
                    if w.en.get(o, True) and (fr + offset) % 30 == 0: balls.append((o, fr))
                for o in w.changed:
                    apply(o, +1 if w.en[o] else -1)
                for wc in w.wall_changed:
                    if wc in self.secret: wall(wc, +1 if wc in w.closed else -1)
                for o in w.volleys & set(shooters):
                    for i, j in lanes[o]: vol[i, j] += SHOOTERS[shooters[o]["type"]][1]
                G[t] += base_g
                A[t] += base_a
                for o in sentries:
                    sentry_on[o] = sentry_on[o] + 1 if w.en.get(o, True) else 0
            G[t] += vol; A[t] += vol
            hot = set()
            for o, f0 in balls:
                for k in range(FPT):
                    hot |= self.ball_cells(o, t * FPT + k - f0, (BALL_R + PLAN_MARGIN) / SQ)
            for i, j in hot:
                G[t, i, j] += 90.0; A[t, i, j] += 90.0
            balls = [(o, f0) for o, f0 in balls if (t * FPT - f0) * FIREBALL <= self.ball_range(o)]
            for o, v in shooters.items():                # held on: a shot a second
                if o in skulls: continue
                if w.en.get(o, True) and o not in w.volleys:
                    for i, j in lanes[o]:
                        G[t, i, j] += SHOOTERS[v["type"]][1] * FPT / 30.0
                        A[t, i, j] += SHOOTERS[v["type"]][1] * FPT / 30.0
            for o, v in sentries.items():
                if sentry_on[o] > 0:
                    x = v.get("xfer") or {}
                    rot = x.get("RotateSpeed", 0.0)
                    for df in range(-FPT, FPT + 1):            # the beam over the tick and a tick either side: it
                        ang = x.get("BasePosRadian", 0.0) + rot * max(1, sentry_on[o] + df)   # kills in one frame
                        for i, j in self.beam(w.pos[o], ang, pad=PLAN_MARGIN + 6):
                            for tt in (t - 1, t, t + 1):
                                if 0 <= tt < G.shape[0] and G[tt, i, j] < LETHAL:
                                    G[tt, i, j] += LETHAL; A[tt, i, j] += LETHAL
                        if not rot: break
            for o in dyn:
                tp = self.objs[o]["type"]
                a, b = self.ab(*w.pos[o])
                if tp in BLOCKS:
                    cells = self.cells_square(a, b, 0.91 + PLAYER_R / SQ)
                    cost = SHOVE + BLOCKS[tp] * FPT
                else:
                    cells = self.cells_near(a, b, (BLADES[tp][0] + PLAYER_R) / SQ)
                    cost = SHOVE + BLADES[tp][1] * FPT
                for i, j in cells:
                    G[t, i, j] += cost; A[t, i, j] += cost
        return G, A

    def lane(self, v):
        (dx, dy), _ = SHOOTERS[v["type"]]
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        out = set()
        x, y = v["x"], v["y"]
        for k in range(1, 70):
            px, py = x + dx * 8 * k, y + dy * 8 * k
            a, b = self.ab(px, py)
            if not (-0.5 <= a <= self.L + 0.5 and 0 <= b <= self.W): break
            i, j = self.cell_of(a, b)
            if 0 <= i < self.NA and 0 <= j < self.NB:
                if self.blocked[i, j]: break
                out |= set(self.cells_near(a, b, 14 / SQ))
        return out

    def moments(self):
        """Six arrival moments (frames) spread over the station's longest cycle: its clocks' periods, its movers'
        rounds and its globes' turns (a player comes at any point of them)."""
        P = 90
        mine = set(self.objs)
        for c in self.data["clocks"]:
            if mine & set(self.data["groups"].get(c["group"], [])): P = max(P, c["period"])
        for m in self.data["movers"]:
            if not (mine & set(m["objs"])) or not m.get("speed"): continue
            pts = m["path"]
            L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) + (math.dist(pts[-1], pts[0]) if m["mode"] == "loop" else 0)
            P = max(P, int(L / m["speed"] * (1 if m["mode"] == "loop" else 2) + 2 * m.get("pause", 0)))
        for o, v in self.objs.items():
            rot = abs((v.get("xfer") or {}).get("RotateSpeed", 0.0)) if v["type"] in SENTRIES else 0
            if rot: P = max(P, int(2 * math.pi / rot))
        P = min(P, 1500)
        return [int(round(P * k / 7)) for k in range(1, 7)]

    def ball_range(self, o):
        """How far a skull's fireball flies (px) before a wall or a pillar stops it."""
        if not hasattr(self, "_range"): self._range = {}
        if o not in self._range:
            v = self.objs[o]
            (dx, dy), _ = SHOOTERS[v["type"]]
            n = math.hypot(dx, dy)
            d = 0.0
            while d < 900:
                d += 8
                a, b = self.ab(v["x"] + dx / n * d, v["y"] + dy / n * d)
                if not (-0.5 <= a <= self.L + 0.5 and 0 <= b <= self.W): break
                i, j = self.cell_of(a, b)
                if 0 <= i < self.NA and 0 <= j < self.NB and self.blocked[i, j]: break
            self._range[o] = d
        return self._range[o]

    def ball_xy(self, o, age):
        v = self.objs[o]
        (dx, dy), _ = SHOOTERS[v["type"]]
        n = math.hypot(dx, dy)
        return v["x"] + dx / n * FIREBALL * age, v["y"] + dy / n * FIREBALL * age

    def ball_cells(self, o, age, r):
        if age < 0 or age * FIREBALL > self.ball_range(o): return set()
        a, b = self.ab(*self.ball_xy(o, age))
        return set(self.cells_near(a, b, r))

    def beam(self, p, ang, pad=4.0):
        out = set()
        dx, dy = math.cos(ang), math.sin(ang)
        for k in range(1, 76):
            x, y = p[0] + dx * 8 * k, p[1] + dy * 8 * k
            a, b = self.ab(x, y)
            if not (-0.5 <= a <= self.L + 0.5 and 0 <= b <= self.W): break
            i, j = self.cell_of(a, b)
            if 0 <= i < self.NA and 0 <= j < self.NB and self.blocked[i, j]: break
            out |= set(self.cells_near(a, b, (PLAYER_R + pad) / SQ))
        return out

    # ---- the plan --------------------------------------------------------------------------------------------
    MOVES = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    JUMPS = [(JD, 0), (-JD, 0), (0, JD), (0, -JD), (JDD, JDD), (JDD, -JDD), (-JDD, JDD), (-JDD, -JDD)]

    def plan(self, G, A, start_cells=None, t0=0, d0=0.0, goal=None, avoid_plates=True):
        """Least damage from start_cells at tick t0 to the goal (default: the way out). Returns
        (damage, arrival tick, path [(t, i, j, airborne)]) or None."""
        NA, NB, T = self.NA, self.NB, G.shape[0] - (JT + 2)
        INF = np.float32(1e9)
        C = JUMP_COOL // FPT + 1                      # cooldown states (0 = a jump is ready)
        best = np.full((T + JT + 2, C, NA, NB), INF, np.float32)
        par = np.zeros((T + JT + 2, C, NA, NB), np.int16)   # how the state was reached (move or jump index, from cooldown)
        ground_pen = np.zeros((NA, NB), np.float32)
        if avoid_plates:
            for z in self.zones:
                if z.get("jump"):
                    a, b = self.ab(*z["c"])
                    for i, j in self.cells_near(a, b, z["r"] / SQ):
                        ground_pen[i, j] += PLATE_PENALTY
        block = self.blocked
        if start_cells is None:
            start_cells = [(i, j) for i in range(NA) for j in range(NB)
                           if 0.0 <= self.cell_ab(i, j)[0] <= 1.0 and not block[i, j]]
        for i, j in start_cells:
            best[t0, 0, i, j] = d0
        goal_mask = np.zeros((NA, NB), bool)
        if goal is None:
            for i in range(NA):
                if self.cell_ab(i, 0)[0] >= self.L + 0.2: goal_mask[i, :] = True      # through the way out
        else:
            for i, j in goal: goal_mask[i, j] = True
        goal_mask &= ~block
        crumble = np.zeros((NA, NB), bool)
        for i, j in getattr(self, "crumble_cells", ()):
            crumble[i, j] = True
        found = None
        for t in range(t0, T):
            cur = best[t]
            hits = float(np.where(goal_mask[None], cur, INF).min())
            if hits < INF and (found is None or hits < found[1] - 1):
                found = (t, hits)                      # the best arrival so far (a later one may hurt less)
            if found is not None and found[1] <= 30 and t > found[0] + 40: break
            g = G[t + 1] + ground_pen
            for c in range(C):
                src = cur[c]
                if not np.isfinite(src).any() or src.min() >= INF: continue
                nc = max(c - 1, 0)
                for k, (di, dj) in enumerate(self.MOVES):
                    sh = np.full((NA, NB), INF, np.float32)
                    si0, si1 = max(0, -di), NA - max(0, di)
                    sj0, sj1 = max(0, -dj), NB - max(0, dj)
                    sh[si0 + di:si1 + di, sj0 + dj:sj1 + dj] = src[si0:si1, sj0:sj1]
                    if k == 0:
                        sh = np.where(crumble, INF, sh)            # no standing still on crumbling floor
                    cost = sh + g
                    cost = np.where(block, INF, cost)
                    better = cost < best[t + 1, nc]
                    best[t + 1, nc] = np.where(better, cost, best[t + 1, nc])
                    par[t + 1, nc] = np.where(better, k * 16 + c, par[t + 1, nc])
                if c == 0:
                    for k, (di, dj) in enumerate(self.JUMPS):
                        land = np.full((NA, NB), INF, np.float32)
                        si0, si1 = max(0, -di), NA - max(0, di)
                        sj0, sj1 = max(0, -dj), NB - max(0, dj)
                        if si1 <= si0 or sj1 <= sj0: continue
                        acc = src[si0:si1, sj0:sj1].copy()
                        ok = np.ones_like(acc, bool)
                        for s in range(1, JT + 1):
                            oi, oj = round(di * s / JT), round(dj * s / JT)
                            acc = acc + A[t + s][si0 + oi:si1 + oi, sj0 + oj:sj1 + oj]
                            ok &= ~block[si0 + oi:si1 + oi, sj0 + oj:sj1 + oj]
                        acc = acc + G[t + JT][si0 + di:si1 + di, sj0 + dj:sj1 + dj] - A[t + JT][si0 + di:si1 + di, sj0 + dj:sj1 + dj] + JUMP_COST
                        land[si0 + di:si1 + di, sj0 + dj:sj1 + dj] = np.where(ok, acc, INF)
                        land = np.where(block, INF, land)
                        lc = max(C - 1 - JT, 0)
                        better = land < best[t + JT, lc]
                        best[t + JT, lc] = np.where(better, land, best[t + JT, lc])
                        par[t + JT, lc] = np.where(better, 1000 + k, par[t + JT, lc])
        if found is None:
            return None
        # the best arrival within 40 ticks of the first: least damage, then earliest
        cand = []
        for t in range(found[0], min(found[0] + 41, T)):    # from the best arrival: least damage, then earliest
            v = np.where(goal_mask[None], best[t], INF)
            m = float(v.min())
            if m < INF: cand.append((round(m, 1), t))
        dmg, tt = min(cand)
        c, i, j = np.unravel_index(int(np.argmin(np.where(goal_mask[None], best[tt], INF))), best[tt].shape)
        path = []
        t = tt
        while t > t0:
            p = int(par[t, c, i, j])
            if p >= 1000:
                di, dj = self.JUMPS[p - 1000]
                for s in range(JT, 0, -1):
                    path.append((t - JT + s, i - di + round(di * s / JT), j - dj + round(dj * s / JT), True))
                i, j, t, c = i - di, j - dj, t - JT, 0
            else:
                k, pc = divmod(p, 16)
                di, dj = self.MOVES[k]
                path.append((t, i, j, False))
                i, j, t, c = i - di, j - dj, t - 1, pc
        path.append((t0, i, j, False))
        path.reverse()
        return float(dmg), tt, path

    # ---- exact replay ----------------------------------------------------------------------------------------
    def replay(self, path_px, offset=0, max_frames=None):
        """Frame by frame: positions [(x, y, airborne)] per frame; returns (damage, outcome, frames)."""
        w = World(self.data, offset)
        w.closed = {wc for wc in self.secret if self.secret_state.get(wc, "closed") == "closed"}
        dmg, crumble_touch = 0.0, {}
        objs = self.objs
        small = [(o, v) for o, v in objs.items() if v["type"] in SMALL]
        grid = {}
        for o, v in small:
            grid.setdefault((int(v["x"] // 64), int(v["y"] // 64)), []).append((o, v))
        pits = [(o, v) for o, v in objs.items() if v["type"] in PITS + CRUMBLE]
        shooters = [(o, v) for o, v in objs.items() if v["type"] in SHOOTERS]
        lanes = {o: [self.xy(*self.cell_ab(i, j)) for i, j in self.lane(v)] for o, v in shooters}
        cool = {o: 0 for o, _ in shooters}
        balls = []
        sentries = [(o, v) for o, v in objs.items() if v["type"] in SENTRIES]
        on_for = {o: (offset if w.en.get(o, True) else 0) for o, _ in sentries}
        dyn = [(o, v) for o, v in objs.items() if v["type"] in BLOCKS or v["type"] in BLADES]
        for f, (x, y, air) in enumerate(path_px):
            w.tick((x, y), air)
            p = (x, y)
            for wc in w.closed:
                wx, wy = (wc[0] + 0.5) * 23.0, (wc[1] + 0.5) * 23.0
                if math.hypot(x - wx, y - wy) < 18: return dmg, "blocked", f
            gx, gy = int(x // 64), int(y // 64)
            for ddx in (-1, 0, 1):
                for ddy in (-1, 0, 1):
                    for o, v in grid.get((gx + ddx, gy + ddy), ()):
                        if not w.en.get(o, True): continue
                        r, d_, jump = SMALL[v["type"]]
                        if air and jump: continue
                        if math.hypot(x - v["x"], y - v["y"]) < r + PLAYER_R: dmg += d_
            for o, v in pits:
                ox, oy = v["x"], v["y"]
                inside = abs(x - ox) + abs(y - oy) < 22.6
                if v["type"] in CRUMBLE and not w.en.get(o, True):
                    if inside and not air and o not in crumble_touch:
                        to = (v.get("xfer") or {}).get("ScriptTimeout", 4)
                        crumble_touch[o] = f + max(1, to)
                    if o in crumble_touch and f >= crumble_touch[o]:
                        w.en[o] = True
                    continue
                if w.en.get(o, True) and inside and not air:
                    return dmg, "fell", f
            for o, v in shooters:
                cool[o] = max(0, cool[o] - 1)
                if not w.en.get(o, True): continue
                if v["type"].startswith("Skull"):       # a fireball a second, flying at 12 px a frame
                    if (f + offset) % 30 == 0: balls.append((o, f))
                    continue
                hit = any(math.hypot(x - lx, y - ly) < 12 for lx, ly in lanes[o])
                if hit and (o in w.volleys or cool[o] == 0):
                    dmg += SHOOTERS[v["type"]][1]; cool[o] = 30
            left = []
            for o, f0 in balls:
                bx, by = self.ball_xy(o, f - f0)
                if math.hypot(x - bx, y - by) < BALL_R: dmg += SHOOTERS[self.objs[o]["type"]][1]
                elif (f - f0) * FIREBALL <= self.ball_range(o): left.append((o, f0))
            balls = left
            for o, v in sentries:
                on_for[o] = on_for[o] + 1 if w.en.get(o, True) else 0
                if on_for[o]:
                    xf = v.get("xfer") or {}
                    ang = xf.get("BasePosRadian", 0.0) + xf.get("RotateSpeed", 0.0) * on_for[o]
                    sx, sy = w.pos[o]
                    end = (sx + 600 * math.cos(ang), sy + 600 * math.sin(ang))
                    end = self.clip(sx, sy, end)
                    if seg_dist(p, (sx, sy), end) < PLAYER_R + 2:
                        return dmg + 500, "died", f
            for o, v in dyn:
                tp = v["type"]
                ox, oy = w.pos[o]
                if tp in BLOCKS:
                    if abs(x - ox) + abs(y - oy) < 42 + PLAYER_R * 1.414: dmg += BLOCKS[tp] + 0.5
                else:
                    if math.hypot(x - ox, y - oy) < BLADES[tp][0] + PLAYER_R: dmg += BLADES[tp][1]
            if dmg >= 300:
                return dmg, "died", f
        return dmg, "passed", len(path_px)

    def clip(self, sx, sy, end):
        """A beam cut at the station's walls and pillars."""
        dx, dy = end[0] - sx, end[1] - sy
        n = int(math.hypot(dx, dy) // 8)
        for k in range(1, n + 1):
            x, y = sx + dx * k / n, sy + dy * k / n
            a, b = self.ab(x, y)
            if not (-0.5 <= a <= self.L + 0.5 and 0 <= b <= self.W): return (x, y)
            i, j = self.cell_of(a, b)
            if 0 <= i < self.NA and 0 <= j < self.NB and self.blocked[i, j]: return (x, y)
        return end

    def path_frames(self, path, delay=0):
        """A plan's ticks as positions per frame (a jump's 6 ticks become 18 frames at run speed)."""
        out = []
        first = path[0]
        x0, y0 = self.xy(*self.cell_ab(first[1], first[2]))
        out += [(x0, y0, False)] * delay
        for (t, i, j, air), nxt in zip(path, path[1:]):
            a = self.xy(*self.cell_ab(i, j))
            b = self.xy(*self.cell_ab(nxt[1], nxt[2]))
            for k in range(FPT):
                s = k / FPT
                out.append((a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s, nxt[3]))
        last = path[-1]
        x1, y1 = self.xy(*self.cell_ab(last[1], last[2]))
        out.append((x1, y1, False))
        return out

    def straight(self, speed):
        out = []
        a = 0.3
        while a <= self.L + 0.2:
            out.append((*self.xy(a, self.W / 2), False))
            a += speed / SQ
        return out


def analyse(map_dir, only=None, trace=False):
    names = [f for f in os.listdir(map_dir) if f.endswith(".lab.json")]
    if not names:
        raise SystemExit(f"no .lab.json in {map_dir}")
    lab = json.load(open(os.path.join(map_dir, names[0])))
    data = json.load(open(os.path.join(map_dir, lab["name"] + ".traps.json")))
    rows, runs = [], {}
    for st in lab["stations"]:
        if only and st["label"] != only: continue
        sm = StationModel(data, st, [tuple(w) for w in lab.get("walls", [])],
                          {tuple(map(int, k.split(","))): v for k, v in lab.get("secret", {}).items()})
        tier = st.get("tier", "standard")
        G, A = sm.fields(0)
        res = sm.plan(G, A)
        levers = [(z["name"], z["c"], (z["r"] - 4) / SQ, z["acts"]) for z in sm.zones if z.get("toggle")]
        for wt in data.get("watches", []):             # an item to take: the plan may go and pick it up
            o = data["objects"].get(wt["obj"])
            if o and sm.inside(o["x"], o["y"]):
                levers.append((wt["name"], (o["x"], o["y"]), 0.6, wt["acts"]))
        used = None
        for zname, zc, zr, zacts in levers:            # try pulling each lever (taking each item) on the way
            a, b = sm.ab(*zc)
            goal = [c for c in sm.cells_near(a, b, max(zr, 0.4)) if not sm.blocked[c]]
            r1 = sm.plan(G, A, goal=goal) if goal else None
            if not r1: continue
            d1, t1, p1 = r1
            G2, A2 = sm.fields(0, events=[(t1 * FPT, zacts)])
            r2 = sm.plan(G2, A2, start_cells=[(p1[-1][1], p1[-1][2])], t0=t1, d0=d1)
            if r2 and (res is None or r2[0] < res[0] - 5):
                res, used = (r2[0], r2[1], p1[:-1] + r2[2]), zname
        slack_ok = 0
        offsets = sm.moments()
        for off in offsets:
            Gs, As = sm.fields(off)
            r = sm.plan(Gs, As)
            if r and min(r[0], sm.replay(sm.path_frames(r[2]), offset=off)[0]) <= 10: slack_ok += 1
        slack = slack_ok / len(offsets)
        if used and slack < 0.5:
            slack = 1.0                                 # a lever station is passed from any moment once pulled
        row = dict(label=st["label"], title=st["title"], tier=tier)
        rr = runs[st["label"]] = {}
        if res:
            dmg, tt, path = res
            frames_ = sm.path_frames(path)
            rr["plan"] = [[round(x, 1), round(y, 1), int(air)] for x, y, air in frames_]
            ex, outcome, _ = sm.replay(frames_)
            late, outcome_late, _ = sm.replay(sm.path_frames(path, delay=4))
            row.update(plan=round(dmg, 1), time=round(tt * FPT / 30, 1), waits=sum(1 for a_, b_ in zip(path, path[1:])
                       if (a_[1], a_[2]) == (b_[1], b_[2]) and not b_[3]) * FPT / 30,
                       jumps=sum(1 for a_, b_ in zip(path, path[1:]) if b_[3] and not a_[3]), lever=used,
                       replay=round(ex, 1), replay_outcome=outcome, late=round(late, 1), late_outcome=outcome_late)
            if trace:
                row["path"] = [(t, round(sm.cell_ab(i, j)[0], 2), round(sm.cell_ab(i, j)[1], 2), air) for t, i, j, air in path]
        else:
            row.update(plan=None)
        for nm, sp in (("walk", WALK), ("run", RUN)):
            # the player arrives at any moment of the cycles: the mean over the moments, and the worst outcome
            tries = [sm.replay(sm.straight(sp), offset=off) for off in [0] + offsets]
            row[f"careless_{nm}"] = round(sum(r_[0] for r_ in tries) / len(tries), 1)
            bad = [r_[1] for r_ in tries if r_[1] != "passed"]
            row[f"careless_{nm}_outcome"] = (f"{bad[0]} {len(bad)}/{len(tries)}" if bad else "passed")
            row[f"careless_{nm}_worst"] = round(max(r_[0] for r_ in tries), 1)
        rr["walk"] = [[round(x, 1), round(y, 1), 0] for x, y, _ in sm.straight(WALK)]
        rr["run"] = [[round(x, 1), round(y, 1), 0] for x, y, _ in sm.straight(RUN)]
        for nm in ("walk", "run"):                      # what the replay says at the moment the tour runs them (0)
            d_, o_, _ = sm.replay(sm.straight(WALK if nm == "walk" else RUN), offset=0)
            row[f"careless_{nm}_0"] = [round(d_, 1), o_]
        row["slack"] = round(slack, 2)
        # what this station does that the simulator does not model: its verdict is the game's (the tour)
        known = {"on", "off", "toggle", "pulse", "arm", "disarm", "restart", "reset", "walls_open", "walls_close",
                 "log", "sound", "say", "wake"}
        pre = st.get("prefix") or ""
        acts = [a for z in data["zones"] if z["name"].startswith(pre) or sm.inside(*z["c"]) for a in z["acts"] + z["release"]]
        acts += [a for w in data.get("watches", []) if w["name"].startswith(pre) for a in w["acts"]]
        blind = sorted({a["kind"] for a in acts if a["kind"] not in known})
        blind += sorted({t for t in (v["type"] for v in sm.objs.values()) if t in ("Glyph", "PoisonGasTrap", "BearTrap")})
        if any(m["name"].startswith(pre) for m in data["movers"]) and any(k.startswith("push") for k in blind):
            pass
        row["sim_blind"] = blind
        row["verdict"] = verdict(row)
        if blind and row["verdict"] in ("TOO EASY", "TIER (easier than hard)", "PASS"):
            row["verdict"] += f" [sim blind to {', '.join(blind)}: judged in the game]"
        rows.append(row)
        print(f"{row['label']:14s} {tier:8s} plan {row.get('plan')} t={row.get('time')}s jumps={row.get('jumps')} "
              f"lever={row.get('lever')} replay={row.get('replay')}/{row.get('replay_outcome')} "
              f"late={row.get('late')}/{row.get('late_outcome')} slack={row['slack']} | walk {row['careless_walk']}"
              f"/{row['careless_walk_outcome']} run {row['careless_run']}/{row['careless_run_outcome']} -> {row['verdict']}")
    if not only:
        json.dump(runs, open(os.path.join(map_dir, lab["name"] + ".runs.json"), "w"))
    out = os.path.join(map_dir, lab["name"] + (".sim.json" if not only else f".sim_{only}.json"))
    json.dump(rows, open(out, "w"), indent=1)
    md = [f"# {lab['name']}: simulated", "", "| Station | Tier | Plan HP | Time s | Jumps | Lever | Replay | 4 frames late | "
          "Slack | Careless walk | Careless run | Verdict |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['label']} {r['title']} | {r['tier']} | {r.get('plan')} | {r.get('time')} | {r.get('jumps')} | "
                  f"{r.get('lever') or ''} | {r.get('replay')} {r.get('replay_outcome', '')} | {r.get('late')} "
                  f"{r.get('late_outcome', '')} | {r['slack']} | {r['careless_walk']} {r['careless_walk_outcome']} | "
                  f"{r['careless_run']} {r['careless_run_outcome']} | {r['verdict']} |")
    open(out.replace(".json", ".md"), "w").write("\n".join(md) + "\n")
    return rows


def verdict(r):
    hard = r["tier"] == "hard"
    if r.get("plan") is None:
        return "IMPOSSIBLE"
    if r.get("replay_outcome") != "passed":         # the exact replay is the judge: a plan that dies there is no plan
        return f"IMPOSSIBLE (the best plan {r.get('replay_outcome')} in the replay)"
    best = r["replay"]
    if best >= (90 if hard else 60):
        return "IMPOSSIBLE"
    walk_bad = r["careless_walk_outcome"] != "passed" or r["careless_walk"] >= 35
    run_bad = r["careless_run_outcome"] != "passed" or r["careless_run"] >= 35
    if not walk_bad and not run_bad:
        return "TOO EASY"
    if not hard and (best > 25 or r["slack"] < 0.5):
        return "TIER (harder than standard)"
    if hard and r["careless_walk_outcome"] == "passed" and r["careless_walk"] < 60 and r["careless_run"] < 60:
        return "TIER (easier than hard)"
    return "PASS"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("map_dir")
    ap.add_argument("--only")
    ap.add_argument("--trace", action="store_true")
    a = ap.parse_args()
    analyse(a.map_dir, a.only, a.trace)
