"""TrapDemo missions: a finished, self-contained mission map built round its traps (the user, 2026-10-23: "production
quality medium size maps ... a basic story arc with a quest or 2 ... traps integrated", "in a dungeon, traps combine
with monsters for the true nox experience").

A mission is a walled complex (kit/dungeon.py) laid out as a tree from its first room: rooms with a purpose (the
expedition's camp at the way in, guard rooms, crypts, shrines, stores, a vault, the boss's hall) joined by passages
that are trap stations (kit/trapkit patterns, signed only by their hardware: no labels on the walls, as Westwood) or
plain corridors. The design file writes the story with the quest kit (kit/quests.py) on the rooms and items this
builds.

    M = Mission("TrapDem01", "The Drowned Reliquary", "crypt", seed=1)
    M.room("camp", (12, 10), role="camp")
    M.room("ossuary", (10, 10), role="crypt")
    M.link("camp", "ossuary", trap=("spike", 2))          # a spike pattern (its index in PATTERNS["spike"])
    M.link("ossuary", "vault", trap=("auto", "hard"))      # any hard pattern the setting favours
    M.link("ossuary", "well", length=6)                   # a plain corridor
    M.layout()                                            # place it all (retries until it fits)
    M.dress()                                             # rooms furnished by role, lights, ambience
    M.monsters("ossuary", {"Skeleton": 3})
    M.boss("hall", "B4")
    relic = M.item("vault", "RedOrbKeyOfTheLich")
    giver = M.person("camp", "Con02a", "Bryan", "Hadric", pic="QuarterMasterPic", title="Hadric")
    q = M.q; q.talker(giver, [...]); ...
    M.finish(out_dir)

Each trap passage is a station the simulator and the in-game tour read (<Name>.lab.json: TD-NN-Pk labels).
"""
import json, math, os, random, zlib

from nox import Spec, SOLO
from kit.dungeon import Dungeon, glow
from kit.traps import Traps
from kit.trapkit import Station, PATTERNS, tier_of
from kit.quests import QuestBook, A, QUEST, COMPLETED
from kit.npcs import Population, facing

HERE = os.path.dirname(os.path.abspath(__file__))
STOCK = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "maps")
if not os.path.isdir(STOCK):
    STOCK = r"C:\GOG Games\Nox\maps"

SETTINGS = {
    # walls, floor, room floor, favoured kinds, decor
    "crypt": ("DungeonStone", "GreenBrick", "CryptFloor", ["spike", "blade", "pit", "spell", "block"],
              dict(light="Candleabra3", amb="AmbSpiritsFOV", centre=["Monument1", "Obelisk"], pair=["Statue2a", "Statue2c", "Statue2e"],
                   column="Column6", corner=["SkullImmobile", "ArmBoneImmobile", "LegBoneImmobile", "SpiderWebNorth"],
                   coffin=["Coffin1", "Coffin2", "Coffin3", "Coffin4"], chest="CryptChest4", store=["Crate1", "Crate2", "Barrel"])),
    "forge": ("GalavaTownWall", "LOTDPitted", "GalavaBrick2", ["flame", "block", "push", "spell", "spike"],
              dict(light="Brazier", amb="AmbLavaBubbles", centre=["ObeliskPrimitive"], pair=["Column5"], column="Column5",
                   corner=["CaveRocksPebblesImmobile", "RuinsColumnOutdoorRubble07", "RuinsColumnOutdoorRubble08"],
                   coffin=["CrateSteel1", "CrateSteel2"], chest="Chest4", store=["CrateSteel1", "Barrel", "BlackPowderBarrel"])),
    "temple": ("IxTempleWall", "IxBrickFancy", "AncientRuin", ["arrow", "spike", "pit", "trigger", "sentry"],
               dict(light="Brazier", amb="AmbIxTemple", centre=["ObeliskPrimitive"], pair=["RuinsColumnOutdoorRubble09"],
                    column="RuinsColumnOutdoorRubble09", corner=["Plant4", "Mushroom4", "CaveRocksSmallImmobile", "PlantFern1"],
                    coffin=["Crypt1", "Crypt3"], chest="Chest4", store=["Crate1", "Barrel"])),
    "lotd": ("LOTDBrick", "LOTDPitted", "LOTDBlackMarble", ["sentry", "spell", "blade", "arrow", "trigger"],
             dict(light="LOTDCandleabra1", amb="AmbSpiritsLOTD", centre=["LOTDManaObelisk"], pair=["LOTDTombstone1"],
                  column="LOTDColumn1", corner=["SkullImmobile", "ArmBoneImmobile"], coffin=["Coffin1", "Coffin3"],
                  chest="CryptChest4", store=["DarkCrate1", "DarkCrate2"])),
    "mine": ("CaveWall", "CaveHardBrown", "CaveHardTan", ["pit", "push", "block", "blade", "flame"],
             dict(light="Brazier", amb="AmbCaveRumble", centre=["CaveRockPillarTall1"], pair=["CaveRockPillarShort1"],
                  column="CaveRockPillarTall1", corner=["CaveRocksSmallImmobile", "CaveRocksPebblesImmobile", "MineCrystalUp02"],
                  coffin=["Crate1", "Crate2"], chest="Chest4", store=["Barrel", "Barrel2", "Crate1", "BlackPowderBarrel"])),
    "castle": ("BrickBlue", "TileDark", "DungeonStoneDark", ["arrow", "trigger", "block", "sentry", "spell"],
               dict(light="Candleabra3", amb=None, centre=["Obelisk"], pair=["Statue2a", "Statue2c"], column="Column5",
                    corner=["PlantForest1", "Mushroom3"], coffin=["Coffin2", "Coffin4"], chest="Chest4",
                    store=["Crate1", "Crate2", "Barrel"])),
}
DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]
# a room's walls by the way out through them (a along i from the NW wall, b along j from the SW wall)
WALL_DIRS = {"NW": (-1, 0), "SE": (1, 0), "SW": (0, -1), "NE": (0, 1)}


class Mission:
    def __init__(self, name, title, setting, seed=1, summary=None, description=None, ambient=(110, 105, 100)):
        self.name, self.title, self.setting = name, title, setting
        self.rng = random.Random(zlib.crc32(f"{name}{seed}".encode()))
        self.m = Spec(name, summary=summary or title, description=description or
                      f"[env:castle] {title}: a mission among traps. Generated by Claude.",
                      author="vdystopia (generated by Claude)", version="0.1", date="2026", type=SOLO,
                      minPlayers=1, maxPlayers=1)
        self.m.d["nxz"] = False
        self.m.d["ambient"] = list(ambient)
        self.m.loot = False
        wall, floor, rfloor, self.fav, self.decor = SETTINGS[setting]
        self.wall, self.floor, self.rfloor = wall, floor, rfloor
        self.d = Dungeon(self.m, self.rng, wall=wall, floor=floor)
        self.T = Traps(self.m, prefix="")
        self.pop = Population(self.m, self.rng)
        self.q = QuestBook(name)
        self.rooms, self.links, self.parts, self.stations = {}, [], {}, []
        self.doors = {}                       # room -> [(a, b) of its doorways in room coordinates]
        self.boss_calls = None
        self.used = set()
        self.sign_n = 0

    # ---- the plan ----------------------------------------------------------------------------------------------
    def room(self, rid, size, role="room", floor=None, start=False, kind=None, style="town", closed=()):
        """A room: `role` places the plot pieces (camp, boss, vault...); `kind` furnishes it with the room kit.
        `closed`: walls no passage may open in ("NW", "NE", "SE", "SW"): a throne room's NW wall (the Dun Mir throne
        faces SE only, kit/identity.py), a camp's back walls for its beds."""
        self.rooms[rid] = dict(id=rid, size=size, role=role, floor=floor or self.rfloor, start=start or not self.rooms,
                               kind=kind, style=style, closed={WALL_DIRS[c] for c in closed})
        return rid

    def link(self, a, b, trap=None, length=8, width=4):
        self.links.append(dict(a=a, b=b, trap=trap, length=length, width=width))

    def _pattern(self, trap):
        kind, which = trap
        if kind == "auto":
            tier = which
            cand = [(k, i, p) for k in self.fav + list(PATTERNS) if k in PATTERNS
                    for i, p in enumerate(PATTERNS[k]) if tier_of(p) == tier and (k, i) not in self.used and p.size[0] <= 30]
            seen, uniq = set(), []
            for c in cand:
                if (c[0], c[1]) not in seen: seen.add((c[0], c[1])); uniq.append(c)
            w = [3.0 if k in self.fav else 1.0 for k, _, _ in uniq]
            k, i, p = self.rng.choices(uniq, w)[0]
        else:
            k, i = kind, which
            p = PATTERNS[k][i]
        self.used.add((k, i))
        return k, i, p

    def layout(self, start=(110, 0), tries=200):
        # the passages' patterns and sizes first (a trap passage is as big as its pattern wants)
        for L_ in self.links:
            if L_["trap"]:
                k, i, p = self._pattern(L_["trap"])
                L_["kind"], L_["index"], L_["pattern"] = k, i, p
                L_["length"], L_["width"] = p.size
        children = {}
        for L_ in self.links:
            children.setdefault(L_["a"], []).append(L_)
        root = next(r for r, v in self.rooms.items() if v["start"])
        for attempt in range(tries):
            rng = random.Random(attempt * 104729 + 7)
            placed = self._try_layout(root, children, start, rng)
            if placed:
                self.place = placed
                break
        else:
            raise AssertionError(f"{self.name}: no layout fits")
        for rid, (ci, cj) in placed["rooms"].items():
            w, h = self.rooms[rid]["size"]
            self.parts[rid] = self.d.box(rid, ci - w // 2, cj - h // 2, w, h, floor=self.rooms[rid]["floor"])
        for k, (L_, axis, sign, i0, j0) in enumerate(placed["links"]):
            L_["part"] = self.d.box(f"pass{k}", i0, j0, L_["length"], L_["width"], axis=axis, sign=sign,
                                    kind="corridor")
        self.d.apply()
        # doorways in room coordinates (to keep the dressing out of them)
        for L_ in self.links:
            p = L_["part"]
            for rid, a in ((L_["a"], 0.0), (L_["b"], p.length)):
                x, y = p.at(a, p.width / 2)
                self.doors.setdefault(rid, []).append(self.room_ab(rid, x, y))
        # the traps
        for n, L_ in enumerate(self.links):
            if not L_["trap"]: continue
            label = f"TD-{self.name[-2:]}-P{len(self.stations) + 1}"
            st = Station(self.T, L_["part"], f"P{len(self.stations) + 1:02d}", self.rng, spec=self.m,
                         fall_to=self.parts[L_["a"]].centre)
            meta = L_["pattern"](st)
            for o in self.m.d["objects"]:
                if o["type"] in ("Pit", "PitCrumblingFloor", "ForestPit") and o.get("scr", "").startswith(st.label):
                    o.setdefault("xfer", {}).update(FallX=int(self.parts[L_["a"]].centre[0]),
                                                     FallY=int(self.parts[L_["a"]].centre[1]))
            part = L_["part"]
            for a in range(3, part.length - 2, 7):
                glow(self.m, *part.at(a, part.width / 2))     # no torches indoors, nothing in a trap's lane
            tier = meta.get("tier", L_["pattern"].tier)
            self.T.label(label, L_["pattern"].title, [*part.at(0, 0), *part.at(part.length, part.width)], L_["kind"],
                         tier, notes=json.dumps(meta))
            self.stations.append(dict(label=label, title=L_["pattern"].title, kind=L_["kind"], tier=tier, meta=meta,
                                      L=part.length, W=part.width, start=list(part.at(0.5, part.width / 2)),
                                      end=list(part.at(part.length, part.width / 2)), along=list(part.direction()),
                                      across=list(part.across()), clocks=st.starts, rest=st.rest,
                                      between=[L_["a"], L_["b"]], prefix=st.label))

    def _try_layout(self, root, children, start, rng):
        taken = set()

        def room_sq(rid, ci, cj):
            w, h = self.rooms[rid]["size"]
            return {(i, j) for i in range(ci - w // 2, ci - w // 2 + w) for j in range(cj - h // 2, cj - h // 2 + h)}

        def box_sq(i0, j0, L, W, axis, sign):
            if axis == "i":
                ii = range(i0, i0 + L) if sign > 0 else range(i0 - L, i0)
                return {(i, j) for i in ii for j in range(j0, j0 + W)}
            jj = range(j0, j0 + L) if sign > 0 else range(j0 - L, j0)
            return {(i, j) for i in range(i0, i0 + W) for j in jj}

        def grow(sq, m=2):
            return {(i + a, j + b) for i, j in sq for a in range(-m, m + 1) for b in range(-m, m + 1)}

        def ok(sq):
            return all(8 <= i + j <= 246 and 8 <= i - j <= 246 for i, j in sq)
        rooms = {root: start}
        taken |= room_sq(root, *start)
        if not ok(taken): return None
        used_sides = {root: set()}
        out_links = []
        queue = [root]
        while queue:
            rid = queue.pop(0)
            ci, cj = rooms[rid]
            w, h = self.rooms[rid]["size"]
            for L_ in children.get(rid, []):
                b = L_["b"]
                bw, bh = self.rooms[b]["size"]
                sides = [d for d in DIRS if d not in used_sides[rid] and d not in self.rooms[rid]["closed"]]
                rng.shuffle(sides)
                done = False
                for d in sides:
                    # rooms span i in [ci - w//2, ci - w//2 + w), j in [cj - h//2, cj - h//2 + h); the passage leaves
                    # from the middle of the side d faces (a sign -1 passage covers origin - L .. origin - 1)
                    Lp, Wp = L_["length"], L_["width"]
                    axis = "i" if d[0] else "j"
                    sign = d[0] or d[1]
                    if d == (1, 0):
                        i0, j0 = ci - w // 2 + w, cj - Wp // 2
                        ni, nj = i0 + Lp + bw // 2, cj
                    elif d == (-1, 0):
                        i0, j0 = ci - w // 2, cj - Wp // 2
                        ni, nj = i0 - Lp - bw + bw // 2, cj
                    elif d == (0, 1):
                        i0, j0 = ci - Wp // 2, cj - h // 2 + h
                        ni, nj = ci, j0 + Lp + bh // 2
                    else:
                        i0, j0 = ci - Wp // 2, cj - h // 2
                        ni, nj = ci, j0 - Lp - bh + bh // 2
                    if (-d[0], -d[1]) in self.rooms[b]["closed"]: continue
                    sq = box_sq(i0, j0, Lp, Wp, axis, sign)
                    rq = room_sq(b, ni, nj)
                    if not ok(sq | rq): continue
                    if (sq | rq) & grow(taken - room_sq(rid, ci, cj), 2): continue
                    if rq & grow(taken, 2): continue
                    taken |= sq | rq
                    rooms[b] = (ni, nj)
                    used_sides[rid].add(d)
                    used_sides[b] = {(-d[0], -d[1])}
                    out_links.append((L_, axis, sign, i0, j0))
                    queue.append(b)
                    done = True
                    break
                if not done:
                    return None
        return dict(rooms=rooms, links=out_links)

    # ---- coordinates ---------------------------------------------------------------------------------------------
    def at(self, rid, a, b):
        """World px of point (a, b) in room `rid` (a along i from its NW wall, b along j from its SW wall)."""
        return self.parts[rid].at(a, b)

    def room_ab(self, rid, x, y):
        p = self.parts[rid]
        x0, y0 = p.at(0, 0)
        ux, uy = p.direction(); vx, vy = p.across()
        return ((x - x0) * ux + (y - y0) * uy) / 32.5, ((x - x0) * vx + (y - y0) * vy) / 32.5

    def free(self, rid, a, b, clear=2.2):
        return all(math.hypot(a - da, b - db) >= clear for da, db in self.doors.get(rid, []))

    def put(self, rid, t, a, b, clear=2.2, **kw):
        if not self.free(rid, a, b, clear): return None
        return self.m.obj_px(t, *self.at(rid, a, b), **kw)

    # ---- dressing -----------------------------------------------------------------------------------------------
    def dress(self):
        """Every room furnished by its role: lights on the back (north-east and north-west) walls, a piece in the
        middle or a composition along an axis, loose pieces in the south and west corners, ambience."""
        D = self.decor
        for k, (rid, R) in enumerate(self.rooms.items()):
            w, h = R["size"]
            role = R["role"]
            rng = self.rng
            if R.get("kind"):                       # a room the room kit furnishes (its own lights and pieces)
                try:
                    self.furnish(rid, R["kind"], R.get("style", "town"))
                    if D.get("amb") and k % 2 == 0: self.put(rid, D["amb"], w / 2, h / 2, clear=0)
                    continue
                except Exception as e:              # the furnisher could not: fall back to the plain dressing
                    print(f"{self.name}: furnishing {rid} as {R['kind']} failed ({type(e).__name__}: {e}); plain dressing")
            # lights: candelabras or braziers along the NE wall (b = h) and the NW wall (a = 0), every 4-5 squares
            for a in range(2, w - 1, 4):
                self.put(rid, D["light"], a + 0.5, h - 0.3, clear=1.4)
            for b in range(2, h - 1, 5):
                self.put(rid, D["light"], 0.3, b + 0.5, clear=1.4)
            if D.get("amb") and k % 2 == 0:
                self.put(rid, D["amb"], w / 2, h / 2, clear=0)
            if role == "camp":
                self.put(rid, "OutdoorTraderPupTent", 2.2, h - 2.2)
                self.put(rid, "CampFire", w / 2, h / 2)
                for z, (a, b) in enumerate(((w / 2 - 1.6, h / 2 + 0.2), (w / 2 + 1.6, h / 2 - 0.2))):
                    self.put(rid, "UrchinStool1" if z else "UrchinStool2", a, b)
                for z, t in enumerate(D["store"][:3]):
                    self.put(rid, t, w - 1.2, 1.2 + 1.1 * z)
                self.put(rid, "Chest4", w - 1.5, h - 1.4, items=["RedPotion", "RedPotion", "BluePotion"])
            elif role == "crypt":
                for z, a in enumerate(range(2, w - 1, 2)):
                    self.put(rid, D["coffin"][z % len(D["coffin"])], a + 0.5, h - 1.0)
                self.put(rid, D["centre"][0], w / 2, h / 2)
                for (a, b) in ((w - 1.2, 1.2), (w - 2.0, 1.0), (1.2, 1.4)):
                    self.put(rid, rng.choice(D["corner"]), a, b, clear=1.5)
            elif role == "shrine":
                self.put(rid, "DunMirAltar1" if self.setting != "lotd" else "LOTDManaObelisk", w / 2, h - 1.6)
                for s in (-1, 1):
                    self.put(rid, D["pair"][0], w / 2 + s * 2.5, h - 1.8)
                    self.put(rid, D["column"], w / 2 + s * 2.8, h / 2 - 1)
            elif role == "store":
                for z, a in enumerate(range(1, w - 1, 2)):
                    self.put(rid, D["store"][z % len(D["store"])], a + 0.5, h - 0.9, clear=1.6)
                for z, b in enumerate(range(2, h - 2, 2)):
                    self.put(rid, D["store"][(z + 1) % len(D["store"])], 0.9, b + 0.5, clear=1.6)
                self.put(rid, rng.choice(D["corner"]), w - 1.2, 1.2)
            elif role == "vault":
                for z, a in enumerate(range(2, w - 1, 3)):
                    self.put(rid, D["chest"], a + 0.5, h - 1.0, items=[("Gold", {"Amount": 80 + 20 * z})])
                self.put(rid, "Gold", w / 2, h / 2, xfer={"Amount": 120})
                for s in (-1, 1):
                    self.put(rid, D["pair"][-1], w / 2 + s * 2.2, h / 2 + 1.5)
            elif role == "boss":
                for a in range(2, w - 1, 3):
                    for b in (1.5, h - 1.5):
                        self.put(rid, D["column"], a + 0.5, b, clear=2.0)
                self.put(rid, D["centre"][-1], w / 2, h - 1.3)
            elif role == "guard":
                for (a, b) in ((w - 1.2, 1.2), (w - 2.3, 1.0), (1.2, 1.2), (w - 1.0, 2.4)):
                    self.put(rid, rng.choice(D["corner"]), a, b, clear=1.5)
                for z, a in enumerate(range(2, w - 2, 3)):
                    self.put(rid, D["store"][z % len(D["store"])], a + 0.5, h - 0.9, clear=1.6)
            else:
                self.put(rid, D["centre"][0], w / 2, h / 2)
                for (a, b) in ((w - 1.2, 1.2), (1.2, 1.2)):
                    self.put(rid, rng.choice(D["corner"]), a, b, clear=1.5)

    def furnish(self, rid, kind, style="town"):
        """Furnish room `rid` with the room kit (kit/furnish.py furnish_room: the composers the QA rounds rated) as a
        room of `kind` (kit/roomtypes TYPES: crypt, ossuary, shrine, storeroom, guardroom, barracks, armoury,
        treasury, torture_chamber, cell, library, laboratory, hall, great_hall, throne_room ...): its floor tiles,
        the walls round it and its doorways (the passages' openings) as the furnisher's Room record."""
        from kit.model import Room, Door
        from kit.furnish import furnish_room
        from kit.layout import square_tile, point_cell
        from nox import px
        part = self.parts[rid]
        sq = part.squares
        pts = set()
        for i, j in sq:
            for p_, q_ in ((i, j), (i + 1, j), (i, j - 1), (i + 1, j - 1)):
                quad = [(p_ - 1, q_), (p_, q_), (p_ - 1, q_ + 1), (p_, q_ + 1)]
                n = sum(s in sq for s in quad)
                if 0 < n < 4: pts.add((p_, q_))
        walls = {point_cell(*p_) for p_ in pts if point_cell(*p_) in self.m.wallmap}
        open_pts = [p_ for p_ in pts if point_cell(*p_) not in self.m.wallmap]
        # group the openings into doorways (runs of open points along one side)
        doors, seen = [], set()
        for p_ in sorted(open_pts):
            if p_ in seen: continue
            run, stack = [], [p_]
            while stack:
                c = stack.pop()
                if c in seen or c not in open_pts: continue
                seen.add(c); run.append(c)
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    stack.append((c[0] + d[0], c[1] + d[1]))
            run.sort()
            line = "\\" if len({q_ for _, q_ in run}) == 1 else "/"
            # a passage's mouth is as wide as the passage (4-12 squares): a door on every point of it, so the
            # furnisher's flood stops at the mouth (one door in the middle let the room's floor run on into the
            # passage and the next room) and its doorway clearance covers the whole width
            for p_ in run:
                doors.append(Door(gap=point_cell(*p_), line=line, type="CryptDoor", connects=(rid, "passage"),
                                  px=px(2 * p_[0], 2 * p_[1])))
        room = Room(id=rid, tiles={square_tile(i, j) for i, j in sq}, floor=self.rooms[rid]["floor"], walls=walls,
                    doors=doors, kind=kind, building=rid)
        objs = furnish_room(self.m, room, kind, self.rng, style)
        # and nothing stands in a mouth: a band 1.4 squares deep before each passage's opening, its whole width and a
        # little more, is cleared of what the furnisher laid there (a bench or a barrel snug to the wall beside it)
        drop = set()
        for L_ in self.links:
            if rid not in (L_["a"], L_["b"]) or "part" not in L_: continue
            p = L_["part"]
            x0, y0 = p.at(0, 0); ux, uy = p.direction(); vx, vy = p.across()
            for o in objs:
                a_ = ((o["x"] - x0) * ux + (o["y"] - y0) * uy) / 32.5
                b_ = ((o["x"] - x0) * vx + (o["y"] - y0) * vy) / 32.5
                near = (-1.4 < a_ < 0.4) if rid == L_["a"] else (p.length - 0.4 < a_ < p.length + 1.4)
                if near and -0.7 < b_ < p.width + 0.7: drop.add(id(o))
        if drop:
            self.m.d["objects"] = [o for o in self.m.d["objects"] if id(o) not in drop]
            objs = [o for o in objs if id(o) not in drop]
        for o in objs:                  # no open torches indoors: the room kit's torches are the setting's light
            if o.get("type") in ("Torch", "TorchPole"): o["type"] = self.decor["light"]
        self.rooms[rid]["furnished"] = kind
        return objs

    # ---- life ---------------------------------------------------------------------------------------------------------
    def monsters(self, rid, roster, spread=0.6):
        w, h = self.rooms[rid]["size"]
        out = []
        for t, n in roster.items():
            for z in range(n):
                for _ in range(20):
                    a, b = self.rng.uniform(w * (1 - spread) / 2, w * (1 + spread) / 2), self.rng.uniform(h * (1 - spread) / 2, h * (1 + spread) / 2)
                    if self.free(rid, a, b, 2.0): break
                out.append(self.pop.creature(t, *self.at(rid, a, b), action="guard", aggr=0.83))
        return out

    def boss(self, rid, bid, engage=300.0):
        from kit.bosses import Bosses
        if self.boss_calls is None:
            self.boss_calls = Bosses(self.m)
        w, h = self.rooms[rid]["size"]
        door = self.doors.get(rid, [(0, h / 2)])[0]
        return self.boss_calls.boss(bid, *self.at(rid, w / 2, h * 0.62), face=self.at(rid, *door), spares=(),
                                    engage=engage, respawn=30.0)

    def item(self, rid, t, a=None, b=None, **kw):
        w, h = self.rooms[rid]["size"]
        a = w / 2 if a is None else a
        b = h / 2 if b is None else b
        o = self.m.obj_px(t, *self.at(rid, a, b), **kw)
        return o

    def person(self, rid, donor, scr, name, a=None, b=None, face=None, pic=None, title=None):
        w, h = self.rooms[rid]["size"]
        a = w / 2 + 1.5 if a is None else a
        b = h / 2 + 1.5 if b is None else b
        x, y = self.at(rid, a, b)
        fx, fy = face or self.at(rid, w / 2, h / 2)
        xf = dict(DefaultAction=4, Aggressiveness=0.0, Immortal=True, DirectionId=facing(fx - x, fy - y))
        self.m.clone(os.path.join(STOCK, donor, donor + ".map"), f"{donor}:{scr}", x, y, name=name, xfer=xf)
        if pic: self.q.portrait(name, pic)
        if title: self.q.title(name, title)
        return name

    def sign(self, rid, text, a, b):
        from kit.signs import wrap
        for k, part in enumerate(wrap(text)):
            self.sign_n += 1
            key = self.q.text(part, "Sign")
            self.m.obj_px("Sign1", *self.at(rid, a + 0.45 * k, b - 0.45 * k), xfer={"Text": key})

    def start_at(self, rid, a=None, b=None):
        w, h = self.rooms[rid]["size"]
        self.m.obj_px("PlayerStart", *self.at(rid, 1.6 if a is None else a, h / 2 if b is None else b))

    # ---- output --------------------------------------------------------------------------------------------------
    def finish(self, out_dir):
        m = self.m
        self.T.attach()
        m.scripts.update(self.pop.behaviours.files(self.name))
        if self.boss_calls: self.boss_calls.attach()
        m.scripts.update(self.q.files())
        # where the trap tour parks the hero during a plan's jump: the player's start, a free spot (the camp's middle
        # holds its fire: 54 HP a parked jump)
        ps = next((o for o in m.d["objects"] if o["type"] == "PlayerStart"), None)
        info = dict(name=self.name, title=self.title, setting=self.setting, stations=self.stations,
                    hub_start=[ps["x"], ps["y"]] if ps else list(self.parts[next(r for r, v in self.rooms.items() if v["start"])].centre),
                    walls=sorted(m.wallmap),
                    secret={f"{x},{y}": w["secret"] for (x, y), w in m.wallmap.items() if w.get("secret")},
                    rooms={rid: dict(role=v["role"], size=v["size"], centre=list(self.parts[rid].centre))
                           for rid, v in self.rooms.items()},
                    creatures=len(self.pop.placed))
        lines = []
        if out_dir and out_dir != "-":
            os.makedirs(out_dir, exist_ok=True)
            self.q.write_strings(out_dir)
            lines = m.build(out_dir)
            self.T.write(out_dir)
            with open(os.path.join(out_dir, f"{self.name}.lab.json"), "w", encoding="utf-8") as f:
                json.dump(info, f, indent=1)
            print("\n".join(l for l in lines if l.startswith(("OK", "ERROR", "CHECK", "SCRIPTS", "VOICE"))))
        print(f"{self.name} {self.title}: {len(self.rooms)} rooms, {len(self.stations)} trap passages "
              f"({', '.join(s['kind'] for s in self.stations)}), creatures {len(self.pop.placed)}")
        return info
