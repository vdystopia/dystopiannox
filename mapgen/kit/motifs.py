"""The motif engine: rooms composed from arrangements learned from Westwood's campaign rooms (rules/motifs.py ->
rules/out/motifs.json), not from hand-written recipes. An experimental second furnisher beside the recipe engine
(kit/furnish.py); the recipe engine stays the default.

    furnish_room(spec, room, kind=None, rng=None, style="town") -> list of placed object dicts
    furnish_original(spec, room, kind, rng, style) -> (objects, originality check)   # re-rolled until original
    engine_for(kind) -> "motifs" or "recipe"                                          # the switch (ENGINE_TYPES)

How a room is composed (review/roomlab/MOTIFS.md has the whole story):

1. **A skeleton.** One Westwood room of the type (of about our room's floor, its culture first) says which walls are used
   and how fully, which corners hold a heap, how many free groups stand where, where the focal piece stands from the
   door. Its own arrangements are hardly used (one at most, at a sixth of the weight): only its plan. A carpet is laid
   in floor tiles in the share of Westwood's rooms of the type that have one.
2. **The focal wall.** The type's focal piece (kit/roomtypes.py focal: a bed, a hearth, workstations, a bar) comes in a
   wall motif mined from another room, on the wall that stands from our main door as the skeleton's does (across from
   it, beside it), a back wall when the type wants it there; a bar may come in a free group.
3. **The walls.** Each stretch of wall (a run split at its doors, a door's clearance cut out) the skeleton uses takes wall
   motifs of the type from the same class of wall (back or front) and a similar share in use, end to end (a long wall
   of ours is two of Westwood's), each scaled to its part: the pieces at either end keep their distance from their
   corner, the middle ones scale, heaps move as one and jitter a little; a motif may run either way; its pieces take
   the variant for our wall (kit/furnish.py side_variant); now and then one kind is swapped for another of its category
   that Westwood stands in rooms of the type.
4. **Corners and the middle.** The skeleton's corner heaps and free groups, each filled with a motif of the type (a heap
   from the same corner or its mirror; a group where the skeleton's stood, kept inside the room, or as near as fits).
5. **Up to Westwood's density.** While the floor is covered less than this room's draw from Westwood's p25-p75 for the
   type, more motifs: on the free parts of the walls, in corners, free groups where Westwood's stood.
6. **The rules.** Every piece goes through the furnisher's own gate (Furnisher.try_put: the object knowledge base's caps,
   clearances, runs and hangings, the doors' ways in, walkability, the type's coverage limit) and the kind's profile
   (kit/roomtypes.py: never pieces and never_types left out, caps and free_most held, the identity's own types,
   kit/identity.py, with a piece the culture or the identity excludes swapped within its category); faced pieces only on
   the back walls; a seat at a table, a desk or the hearth (loose in a room with a table where Westwood has them), a
   nightstand by the bed, no rug or candelabra alone as a group; the focal family once where the type holds it once;
   lights no more than Westwood's rooms of the type hold; a cauldron off the hearth. The kind's must pieces missing at
   the end come from more motifs that hold them, the recipe's own placement as the last resort.
7. **Originality.** A motif once in a room, no source room more than MAX_PER_SOURCE motifs, and the composed room is
   checked against every stock room (kit/originality.py check): a near copy is composed again.

Builds are reproducible: every choice comes from the rng the caller passes (crc32 seeds; never hash()).
"""
import collections, json, math, os, random, re
from functools import lru_cache

from kit import furnish as F
from kit import objects as OBJ
from kit.roomtypes import TYPES, KIND_TYPE, profile as kind_profile

HERE = os.path.dirname(os.path.abspath(__file__))
MOTIFS_PATH = os.path.join(os.path.dirname(os.path.dirname(HERE)), "rules", "out", "motifs.json")

# The room types whose rooms the motif engine furnishes by default (kit/originality.furnish_original asks engine_for).
# Empty: the recipe engine furnishes every type unless a caller (the room lab's --engine motifs) asks for motifs.
ENGINE_TYPES = set()
# Kin types whose motifs a thin type borrows (at KIN_WEIGHT), filtered by the type's never pieces.
KIN = {"kitchen": ("living_room", "storeroom", "dining_hall", "tavern"),
       "tavern": ("dining_hall", "living_room", "kitchen", "guardroom"),
       "storeroom": ("cellar", "kitchen", "armoury"),
       "laboratory": ("study", "library", "herbalist"),
       "living_room": ("solar", "study", "kitchen"),
       "bedroom": ("solar",)}
KIN_WEIGHT, KIN_BELOW = 0.35, 12           # kin motifs count when the type has fewer than KIN_BELOW Westwood rooms
MAX_PER_SOURCE = 2
SWAP_P = 0.3                               # a motif swaps one of its kinds for another of the category
SWAP_CATS = {"supply", "chest", "chair", "plant", "clutter", "rug", "hanging", "shelf", "table"}
MIRROR = {"NE": "NW", "NW": "NE", "SE": "SW", "SW": "SE", "N": "N", "S": "S", "E": "W", "W": "E"}
FROM_HI = {"NW", "SW"}
CORNER_WALLS = {"N": ("NW", "NE"), "E": ("SE", "NE"), "S": ("SE", "SW"), "W": ("NW", "SW")}   # ('/' wall, '\\' wall)
OPP = {"NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW"}
DOOR_CUT = F.DOOR_CLEAR + 0.5
# focal families a room holds once (a bedroom's one bed, a hearth, a bar): once the focal is in, later motifs leave
# theirs out; the types whose focal repeats (a barracks' beds, a laboratory's benches) are not listed
ONCE = {"bed": ("bedroom", "solar"), "fireplace": ("living_room", "kitchen", "tavern", "study", "solar"),
        "counter_bar": ("tavern",)}
OPEN_TORCH = re.compile(r"^(Torch|TorchPole|TorchPoleImmobile)$")


WW_PATH = os.path.join(os.path.dirname(os.path.dirname(HERE)), "rules", "rooms", "westwood.json")
SEATS = {"chair", "bench"}
FREE_NEVER = {"chest", "shelf", "hearth", "stove", "hanging"}   # never in a free group: they stand against a wall
TOP_UP_TRIES = 24


@lru_cache(None)
def ww_cover(rtype):
    """Westwood's p25 and p75 floor cover for the type (rules/rooms/westwood.json), or None."""
    try:
        with open(WW_PATH, encoding="utf-8") as f:
            c = (json.load(f)["types"].get(rtype) or {}).get("cover")
    except OSError:
        return None
    return (c["p25"], c["p75"]) if c else None


# kinds that stand in rows or line walls by design (review/roommeasure.py LINED, which the room score's repeat check reads)
LINED = re.compile(r"^(Bookcase|MovableBookcase|LogShelves|PotionShelves|WizardWorkstation|Trader|Bed|WoodBed|Cot|Bench|"
                   r"LightBench|CushionedBench|Crypt|Coffin|Column|CathedralColumn|LOTD|Barrel|Crate|DarkCrate|Sack|"
                   r"PiledBarrels|LargeBarrel|WaterBarrel|BarrelWithTools|Candleabra|Nightstand|Chest|OgreStraw|BarPiece|"
                   r"BarCorner|BarHinged)")
SEATED = {"tavern", "dining_hall", "great_hall", "guardroom"}     # a table there has its seats
LOOSE_SEATS = {"living_room", "tavern", "study", "solar", "laboratory", "great_hall", "dining_hall", "guardroom"}


def engine_for(kind):
    t = KIND_TYPE.get(kind, kind)
    return "motifs" if t in ENGINE_TYPES else "recipe"


@lru_cache(None)
def library():
    with open(MOTIFS_PATH, encoding="utf-8") as f:
        d = json.load(f)
    rooms = {r["id"]: r for r in d["rooms"]}
    by_room = collections.defaultdict(lambda: dict(wall=[], corner=[], centre=[]))
    for k in ("wall", "corner", "centre"):
        for x in d[k]: by_room[x["room"]][k].append(x)
    return dict(rooms=rooms, by_room=by_room, wall=d["wall"], corner=d["corner"], centre=d["centre"], stats=d["stats"])


def _never(rtype):
    return set((TYPES.get(rtype) or {}).get("never", ()))


@lru_cache(None)
def pool(rtype):
    """{room id: weight} of the Westwood rooms whose motifs a room of the type draws on."""
    lib = library()
    own = [rid for rid, r in lib["rooms"].items() if r["type"] == rtype]
    out = {rid: 1.0 for rid in own}
    if len(own) < KIN_BELOW:
        for k in KIN.get(rtype, ()):
            for rid, r in lib["rooms"].items():
                if r["type"] == k: out.setdefault(rid, KIN_WEIGHT)
    if not out:                                   # a type with no Westwood rooms: its family's
        fam = (TYPES.get(rtype) or {}).get("family")
        for rid, r in lib["rooms"].items():
            if (TYPES.get(r["type"]) or {}).get("family") == fam: out[rid] = KIN_WEIGHT
    return out


@lru_cache(None)
def type_kinds(rtype):
    """category -> Counter of the types Westwood stands in rooms of the type's pool (what may swap in)."""
    lib = library()
    c = collections.defaultdict(collections.Counter)
    for rid in pool(rtype):
        for k in ("wall", "corner", "centre"):
            for m in lib["by_room"][rid][k]:
                for x in m["items"]: c[x["cat"]][x["t"]] += 1
    return c


class MotifFurnisher(F.Furnisher):
    """The recipe furnisher's geometry and gate (try_put and the object knowledge base), composing from motifs."""

    def __init__(self, spec, room, kind, rng, style):
        super().__init__(spec, room, kind, rng, style)
        self.lib = library()
        self.pool = pool(self.rtype)
        # the kind's own profile (a dwelling's bed, an ore store's carts): must, never, focal, caps, free_most
        self.prof = kind_profile(self.kind) if KIND_TYPE.get(self.kind) else dict(TYPES.get(self.rtype, {}))
        self.never = set(self.prof.get("never", ())) or _never(self.rtype)
        self.never_rx = re.compile(self.prof["never_types"]) if self.prof.get("never_types") else None
        self.culture = {"dunmir": "dunmir", "lotd": "lotd", "ogre": "ogre"}.get(style, "town")
        self.sources = collections.Counter()      # source room -> motifs taken from it
        self.log = []                             # what was composed (for the lab and MOTIFS.md)
        self.house = bool(F.HOUSE_WALLS.search(self.g.wall_material or ""))
        cells = self.g.cells
        us = [x + y + 1 for x, y in cells]; vs = [x - y for x, y in cells]
        self.U0, self.U1, self.V0, self.V1 = min(us), max(us), min(vs), max(vs)
        self.tiles = len(room.tiles)
        self.lights_n = 0
        self.once_done = set()                    # ONCE families already in the room
        self.used_ids = set()                     # the motifs used in this room
        # lights as Westwood lights rooms of the type (rules/out/motifs.json stats: under one a room in most types),
        # never past the knowledge base's cap for the size
        lpr = (self.lib["stats"].get(self.rtype) or {}).get("lights_per_room", 1.0)
        self.light_cap = min(OBJ.light_cap(self.tiles), max(1, int(round(lpr * 1.5 + 0.4))))
        self.stretches = self._stretches()
        self.corners = self._corners()

    # ---- our room's frame ---------------------------------------------------------------------------------------
    def _stretches(self):
        """[dict(run, name, back, s0, s1, L, from_hi)]: every wall run's interior split at its doors."""
        out = []
        doors = list(self.g.doors) + [(x + y + 1, x - y) for x, y in getattr(self.spec, "door_gaps", ())]
        for r in self.g.runs:
            name = F.WALL_NAME[r["side"]]
            lo, hi = r["lo"] + 1.0, r["hi"] - 1.0
            cuts = sorted({round(along, 2) for du, dv in doors
                           for perp, along in [((du, dv) if r["line"] == "/" else (dv, du))]
                           if abs(perp - r["coord"]) < 1.6 and lo - 1 <= along <= hi + 1})
            start = lo
            segs = []
            # a doorway keeps DOOR_CUT clear either side (the furnisher's DOOR_CLEAR round a door, Furnisher.segments)
            for a in cuts:
                if a - DOOR_CUT - start >= 1.0: segs.append((start, a - DOOR_CUT))
                start = max(start, a + DOOR_CUT)
            if hi - start >= 1.0: segs.append((start, hi))
            for s0, s1 in segs:
                out.append(dict(run=r, name=name, back=name in ("NE", "NW"), s0=s0, s1=s1, L=s1 - s0,
                                from_hi=name in FROM_HI, used=False))
        return out

    def _corners(self):
        out = {}
        slash = [r for r in self.g.runs if r["line"] == "/"]
        back = [r for r in self.g.runs if r["line"] == "\\"]
        for a in slash:
            for b in back:
                if not (b["lo"] - 1.5 <= a["coord"] <= b["hi"] + 1.5 and a["lo"] - 1.5 <= b["coord"] <= a["hi"] + 1.5):
                    continue
                pair = (F.WALL_NAME[a["side"]], F.WALL_NAME[b["side"]])
                name = next((k for k, w in CORNER_WALLS.items() if w == pair), None)
                if name and name not in out:
                    out[name] = dict(name=name, a=a, b=b)
        return out

    # ---- choosing -----------------------------------------------------------------------------------------------
    def _weight(self, m, skeleton=None):
        w = self.pool.get(m["room"], 0.0)
        if not w or m["id"] in self.used_ids: return 0.0          # a motif once in a room: no stamp
        fams = {F._family_of(x["t"]) for x in m["items"] if x.get("blocking")}
        if fams & self.once_done: return 0.0                     # its bed when the room has its bed already
        if fams and fams <= self.never: return 0.0                # nothing in it the type may hold
        bl = [x for x in m["items"] if x.get("blocking") and x["cat"] != "light"]
        if bl:
            lead = max(bl, key=lambda x: self.footprint(x["t"]) if x["t"] in self.things else 0.0)
            if self._capped(lead["t"]): return 0.0
            if all(F._family_of(x["t"]) in SEATS for x in bl) and not self._seat_anchor_in_room():
                return 0.0                                     # loose seats come with a table or a hearth
        if m["room"] == (skeleton or {}).get("id"):
            if self.sources[m["room"]] >= 1: return 0.0
            w *= 0.15
        if self.sources[m["room"]] >= MAX_PER_SOURCE: return 0.0
        if m.get("culture") != self.culture: w *= 0.5
        return w

    def _choose(self, cands):
        cands = [(w, m) for w, m in cands if w > 0]
        if not cands: return None
        tot = sum(w for w, _ in cands)
        r = self.rng.uniform(0, tot)
        for w, m in cands:
            r -= w
            if r <= 0: return m
        return cands[-1][1]

    def skeleton(self):
        rooms = [r for rid, r in self.lib["rooms"].items() if self.pool.get(rid, 0) >= 1.0] or \
                [self.lib["rooms"][rid] for rid in self.pool]
        # our rooms are built 1.25 times Westwood's (kit/identity.py BUILDING_SCALE) but hold the pieces a room of their
        # own floor would: a skeleton of about our size, so a bigger room takes a plan with more in it
        want = self.tiles
        cands = []
        for r in rooms:
            w = math.exp(-abs(math.log(max(4, r["tiles"]) / max(4, want))) * 2.0)
            if r["culture"] == self.culture: w *= 1.5
            cands.append((w, r))
        return self._choose(cands)

    # ---- types --------------------------------------------------------------------------------------------------
    def _capped(self, t):
        """Whether the room holds all of t it may: the knowledge base's cap for its kind (a bedroom's one table set, a
        cauldron), the profile's caps (kit/roomtypes.py caps: tables in a tavern), and its free_most (a piece that
        stands alone repeated at most once per so many tiles)."""
        fam = F._family_of(t)
        cap = OBJ.room_cap(t, self.rtype, self.tiles)
        if cap is not None:
            key = OBJ.cap_key(t)
            if sum(1 for tt, _ in self._typed if OBJ.cap_key(tt) == key) >= cap: return True
        if self.rtype == "bedroom" and OBJ.category(t) in ("table", "desk") and                 any(OBJ.category(tt) in ("table", "desk") for tt, _ in self._typed): return True
        spec = self.prof.get("caps", {}).get(fam)
        if spec:
            per, most = spec
            if self._count_fam(fam) >= max(self.prof.get("must", {}).get(fam, 0), min(most, int(self.tiles / per))):
                return True
        fm = self.prof.get("free_most")
        if fm and not LINED.match(t) and fam not in ("wall_decor", "rug") and                 fam not in set(self.prof.get("free_skip", ("chair",))) | set(self.prof.get("caps", {})):
            least, per = fm
            k = OBJ.kind(t)
            if sum(1 for o in self.objects if OBJ.kind(o["type"]) == k) >= max(least, int(self.tiles / per)): return True
        return False

    def _swap_kind(self, t, cat):
        """Another type of the same category that Westwood stands in rooms of the type, keeping t's number (its
        facing) where the other kind has it."""
        kinds = type_kinds(self.rtype).get(cat) or {}
        k0 = OBJ.kind(t)
        suffix = t[len(k0):] if t.startswith(k0) else ""
        opts = []
        for t2, n in kinds.items():
            k2 = OBJ.kind(t2)
            if k2 == k0: continue
            cand = k2 + suffix if suffix and self.ok_type(k2 + suffix) else t2
            if self.ok_type(cand) and F._family_of(cand) == F._family_of(t): opts.append((n, cand))
        return self._choose(opts)

    def _fit_type(self, t, cat, run=None, swap=None):
        """The type to stand for t here: swapped (the motif's swap), the culture's own (a piece the style excludes swapped
        within its category), lit by a candelabra in a house (never an open torch), in the variant for wall `run`."""
        if swap and OBJ.kind(t) in swap:
            k2 = swap[OBJ.kind(t)]
            suffix = t[len(OBJ.kind(t)):]
            t = k2 + suffix if self.ok_type(k2 + suffix) else (self._swap_kind(t, cat) or t)
        if cat == "light" and OPEN_TORCH.match(t) and self.house:
            t = self.light_type()
        if not self.ok_type(t):
            t = self._swap_kind(t, cat)
            if not t: return None
        if F._family_of(t) in self.never or F._family_of(t) in self.once_done: return None
        if self.never_rx and self.never_rx.search(t): return None
        if self._capped(t): return None
        if cat != "light" and not self.belongs(t):          # the room identity's own pieces (a bedroom's chests)
            alt = self._swap_kind(t, cat)
            if not alt or not self.belongs(alt): return None
            t = alt
        if run is not None:
            fam = F._family_of(t)
            if run["side"] not in F.BACK_SIDES and (fam in F.FACING_FAMS or F.FACING_TYPES.match(t)):
                return None                                  # the camera would see only its back
            t2 = self.side_variant(t, run, fam) if fam not in ("rug", None) and cat != "light" else t
            if not t2 and cat != "light":
                alt = self._swap_kind(t, cat)
                t2 = alt and self.belongs(alt) and self.side_variant(alt, run, F._family_of(alt))
            t = t2 or None
        return t

    def _motif_swap(self, items):
        """One kind in the motif swapped for another of its category, now and then (SWAP_P)."""
        if self.rng.random() >= SWAP_P: return {}
        kinds = [x for x in items if x["cat"] in SWAP_CATS]
        if not kinds: return {}
        x = self.rng.choice(kinds)
        alt = self._swap_kind(x["t"], x["cat"])
        return {OBJ.kind(x["t"]): OBJ.kind(alt)} if alt else {}

    # ---- placing ------------------------------------------------------------------------------------------------
    def _put(self, t, u, v, blocking, hang=False, touch=False, nudges=((0, 0),)):
        is_light = OBJ.category(t) == "light"
        cat = OBJ.category(t)
        if not is_light and self._capped(t): return None   # again here: a group's pieces were chosen together
        if cat in ("cauldron", "hearth"):            # a cauldron two units from the hearth (rules/rooms/README.md)
            other = "hearth" if cat == "cauldron" else "cauldron"
            hu, hv = self.half(t)
            if any(OBJ.category(tt) == other and max(abs(u - r[0]) - hu - r[2], abs(v - r[1]) - hv - r[3]) < 1.6
                   for tt, r in self._typed): return None
        if is_light:
            if self.lights_n >= self.light_cap: return None
            if not hang and (any(u + 0.5 > z[0] and u - 0.5 < z[1] and v + 0.5 > z[2] and v - 0.5 < z[3]
                                 for z in self.light_zones) or self._before_anchor(u, v)):
                return None
        self.placing_light = is_light
        try:
            for du, dv in nudges:
                o = self.try_put(t, u + du, v + dv, blocking=blocking and not hang, wall_ok=hang,
                                 layer="wall" if hang else "floor", snug=True, touch=touch)
                if o:
                    if is_light: self.lights_n += 1
                    return o
        finally:
            self.placing_light = False
        return None

    def _after_put(self, o, run, along, ha, hp, u, v):
        t = o["type"]
        fam = F._family_of(t)
        self.wall_used.append(((run["line"], run["coord"]), along - ha, along + ha))
        if fam in F.TALL_FAMS: self.wall_tall.append(((run["line"], run["coord"]), along - ha, along + ha))
        if F.NEEDS_FRONT.search(t):
            self.g.zones.append(self.front_zone(run, u, v, max(0.8, ha) + 0.3, hp, 2.3))
            self.light_zones.append(self.front_zone(run, u, v, ha + 0.3, hp, 2.6))

    def place_wall_motif(self, m, st, need=None):
        """Lays wall motif m along our stretch st, scaled to it. Returns the pieces placed (need: a pattern one of
        them must match, or nothing stays)."""
        run = st["run"]
        L, L2 = m["L"], st["L"]
        k = L2 / max(0.5, L)
        flip = self.rng.random() < 0.3
        swap = self._motif_swap(m["items"])
        # heaps move as one; the pieces at either end keep their distance from their corner
        clusters = collections.OrderedDict()
        for x in m["items"]:
            key = ("h", x["heap"]) if x.get("heap") else ("x", id(x))
            clusters.setdefault(key, []).append(x)
        plan = []
        for key, xs in clusters.items():
            a0 = min(x["s"] - x["ha"] for x in xs); a1 = max(x["s"] + x["ha"] for x in xs)
            if a0 <= 1.6: base = a0                                   # anchored to the start
            elif L - a1 <= 1.6: base = L2 - (L - a0)                  # anchored to the end
            else: base = a0 * k + self.rng.uniform(-0.35, 0.35)
            if 0.85 <= k <= 1.2: base = a0 * k + self.rng.uniform(-0.2, 0.2) if a0 > 1.6 and L - a1 > 1.6 else base
            for x in xs:
                plan.append((base + (x["s"] - a0), x))
        placed = []
        snap = (len(self.wall_used), len(self.wall_tall), len(self.g.zones), len(self.light_zones))
        self._group = []
        for s2, x in sorted(plan, key=lambda p: (p[1]["hang"], -p[1]["ha"] * p[1]["hp"])):
            t = self._fit_type(x["t"], x["cat"], run, swap)
            if not t: continue
            hu, hv = self.half(t)
            ha, hp = (hv, hu) if run["line"] == "/" else (hu, hv)
            if s2 - ha < -0.05 or s2 + ha > L2 + 0.05:
                s2 = min(max(s2, ha), L2 - ha)
                if L2 < 2 * ha: continue
            if flip: s2 = L2 - s2
            along = (st["s1"] - s2) if st["from_hi"] else (st["s0"] + s2)
            gap = x["gap"] if x["hang"] else max(0.12, min(x["gap"], 0.9))
            perp = run["coord"] + run["sign"] * (gap + hp)
            u, v = (perp, along) if run["line"] == "/" else (along, perp)
            n = [(0, 0)]
            for d in (0.25, -0.25, 0.5, -0.5):
                n.append((0, d) if run["line"] == "/" else (d, 0))
            for d in (0.15, 0.35):
                n.append((run["sign"] * d, 0) if run["line"] == "/" else (0, run["sign"] * d))
            o = self._put(t, u, v, x["blocking"], hang=x["hang"], touch=bool(x.get("heap")), nudges=n)
            if o:
                rec = self._placed_of[id(o)]
                self._after_put(o, run, along, ha, hp, rec[0], rec[1])
                placed.append(o)
        self._group = None
        placed = self._drop_lone_seats(placed)
        if placed and all(F._family_of(o["type"]) == "rug" for o in placed):
            need = need or "^$"                           # a rug alone along a wall is no motif
        if need and not any(re.search(need, o["type"]) for o in placed):
            for o in placed: self._remove(o)
            del self.wall_used[snap[0]:]; del self.wall_tall[snap[1]:]; del self.g.zones[snap[2]:]
            del self.light_zones[snap[3]:]
            return []
        if placed:
            st["used"] = True
            self.sources[m["room"]] += 1
            self.used_ids.add(m["id"])
            self.log.append(f"wall {st['name']} {st['L']:.0f}u <- {m['id']} ({m['room']} {m['wall']} {m['L']:.0f}u): "
                            + " ".join(o["type"] for o in placed))
        return placed

    def place_corner_motif(self, m, c, mirrored):
        a, b = c["a"], c["b"]
        swap = self._motif_swap(m["items"])
        placed = []
        self._group = []
        for x in sorted(m["items"], key=lambda x: (x["hang"], not x["blocking"])):
            da, db = (x["db"], x["da"]) if mirrored else (x["da"], x["db"])
            # the wall it is nearer keeps its variant (a mounted light, a statue's back)
            run = a if da <= db else b
            src_wall = CORNER_WALLS[m["corner"]][0 if (x["da"] <= x["db"]) else 1]
            t = self._fit_type(x["t"], x["cat"], run if (src_wall != F.WALL_NAME[run["side"]] and
                                                          (x["hang"] or x["cat"] not in ("supply", "plant", "light",
                                                                                         "clutter", "statue"))) else None,
                               swap)
            if not t: continue
            u = a["coord"] + a["sign"] * da; v = b["coord"] + b["sign"] * db
            nud = [(0, 0), (a["sign"] * 0.2, 0), (0, b["sign"] * 0.2), (a["sign"] * 0.2, b["sign"] * 0.2),
                   (a["sign"] * 0.45, b["sign"] * 0.1), (a["sign"] * 0.1, b["sign"] * 0.45)]
            o = self._put(t, u, v, x["blocking"], hang=x["hang"], touch=True, nudges=nud)
            if o: placed.append(o)
        self._group = None
        if placed:
            self.sources[m["room"]] += 1
            self.used_ids.add(m["id"])
            self.log.append(f"corner {c['name']} <- {m['id']} ({m['room']} {m['corner']}): " + " ".join(o["type"] for o in placed))
        return placed

    def place_centre_motif(self, m, pos):
        """A free group near normalised position pos (its pieces' offsets as Westwood stood them)."""
        swap = self._motif_swap(m["items"])
        items = [x for x in m["items"] if x["cat"] not in FREE_NEVER]
        types = []
        for x in items:
            t = self._fit_type(x["t"], x["cat"], None, swap)
            if t: types.append((t, x))
        if not types: return []
        blk = sorted([p for p in types if p[1]["blocking"]], key=lambda p: -self.footprint(p[0]))
        soft = [p for p in types if not p[1]["blocking"]]
        tu = self.U0 + pos[0] * (self.U1 - self.U0); tv = self.V0 + pos[1] * (self.V1 - self.V0)
        # the whole group inside the room: its centre kept half its span (and a step) from the walls
        su, sv = m["span"][0] / 2 + 0.6, m["span"][1] / 2 + 0.6
        if self.U1 - self.U0 > 2 * su: tu = min(max(tu, self.U0 + su), self.U1 - su)
        if self.V1 - self.V0 > 2 * sv: tv = min(max(tv, self.V0 + sv), self.V1 - sv)
        spots = [(0.0, 0.0)]
        for rad in (0.7, 1.4, 2.2, 3.2):
            for k in range(6):
                ang = k * math.pi / 3 + self.rng.uniform(-0.4, 0.4)
                spots.append((rad * math.cos(ang), rad * math.sin(ang)))
        n_blk = len(blk)
        best = None
        for du, dv in spots:
            placed, got = self._try_group(blk + soft, tu + du, tv + dv)
            if placed is None: continue
            if got == n_blk:
                return self._group_done(m, pos, placed)
            if best is None or got > best[0]: best = (got, du, dv)
            for o in placed: self._remove(o)
        if best and best[0] >= max(1, (n_blk + 1) // 2):
            placed, _ = self._try_group(blk + soft, tu + best[1], tv + best[2])
            if placed: return self._group_done(m, pos, placed)
        return []

    def _try_group(self, items, gu, gv):
        """Places a free group's pieces round (gu, gv). Returns (placed, blocking pieces placed), or (None, 0) when its
        first (biggest) piece does not fit."""
        placed, got = [], 0
        self._group = []
        snap = (len(self.g.zones), len(self.light_zones))
        for i, (t, x) in enumerate(items):
            nud = [(0, 0)] + [(sx * 0.2, sy * 0.2) for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            o = self._put(t, gu + x["du"], gv + x["dv"], x["blocking"], touch=True, nudges=nud)
            if o:
                placed.append(o); got += bool(x["blocking"])
            elif i == 0:
                self._group = None
                return None, 0
        self._group = None
        placed = self._drop_lone_seats(placed)
        if not any(self._placed_of.get(id(o)) and self._placed_of[id(o)][4] and OBJ.category(o["type"]) != "light"
                   for o in placed):
            for o in placed: self._remove(o)            # a rug or a candelabra alone is no group
            return None, 0
        return placed, got

    def _group_done(self, m, pos, placed):
        if not placed: return []
        self.sources[m["room"]] += 1
        self.used_ids.add(m["id"])
        self.log.append(f"centre ({pos[0]:.2f},{pos[1]:.2f}) <- {m['id']} ({m['room']}): " +
                        " ".join(o["type"] for o in placed))
        return placed

    # ---- the room -----------------------------------------------------------------------------------------------
    def _wall_cands(self, st, sk, need=None, used_share=None, chain=False):
        """(weight, motif) for stretch st: wall motifs of the same class of wall (back or front), of a length that
        scales to it (chain: or shorter, to stand end to end with others)."""
        out = []
        for m in self.lib["wall"]:
            if not m["items"] or m["back"] != st["back"]: continue
            w = self._weight(m, sk)
            if not w: continue
            r = st["L"] / max(0.5, m["L"])
            if not 0.45 <= r <= (99 if chain else 2.4): continue
            if chain and r > 1.6: r = 1.0 + 0.1 * (r - 1.6)
            if need and not any(re.search(need, x["t"]) for x in m["items"]): continue
            if not need and any(F._family_of(x["t"]) in self.never for x in m["items"] if x["blocking"]) and \
                    all(F._family_of(x["t"]) in self.never for x in m["items"] if x["blocking"]):
                continue
            w *= math.exp(-abs(math.log(r)) * 1.5)
            if m["wall"] == st["name"]: w *= 1.5
            if used_share is not None: w *= math.exp(-abs(m["used"] - used_share) * 3.0)
            out.append((w, m))
        return out

    def free_parts(self, st, pad=0.4, least=2.5):
        """The parts of stretch st no piece stands against yet, as sub-stretches of `least` units or more."""
        key = (st["run"]["line"], st["run"]["coord"])
        used = []
        for k, a0, a1 in self.wall_used:
            if k != key or a1 < st["s0"] or a0 > st["s1"]: continue
            c0, c1 = ((st["s1"] - a1, st["s1"] - a0) if st["from_hi"] else (a0 - st["s0"], a1 - st["s0"]))
            used.append((c0 - pad, c1 + pad))
        used.sort()
        out, cur = [], 0.0
        for c0, c1 in used:
            if c0 - cur >= least: out.append(self._sub(st, cur, c0))
            cur = max(cur, c1)
        if st["L"] - cur >= least: out.append(self._sub(st, cur, st["L"]))
        return out

    @staticmethod
    def _sub(st, c0, c1):
        """The part c0..c1 (from the stretch's canonical start) of stretch st, as a stretch."""
        d = dict(st, L=c1 - c0, parent=st)
        if st["from_hi"]: d["s1"], d["s0"] = st["s1"] - c0, st["s1"] - c1
        else: d["s0"], d["s1"] = st["s0"] + c0, st["s0"] + c1
        return d

    def fill_stretch(self, st, sk, share, need=None, solid=False):
        """Motifs laid end to end along stretch st (a long wall of ours is two of Westwood's walls side by side), from
        one end or the other, each scaled a little to its part, until the wall is used about as the skeleton's (share)
        or the room reaches its cover. need: a pattern the first motif must hold (the focal piece). Returns pieces."""
        out, cursor, first = [], 0.0, True
        rev = self.rng.random() < 0.5
        while st["L"] - cursor >= (1.5 if first else 2.5):
            rem = st["L"] - cursor
            probe = dict(st, L=rem)
            cands = self._wall_cands(probe, sk, need=need if first else None,
                                     used_share=max(share, 0.15), chain=True)
            if solid or not first:                 # more than a candelabra or a hanging
                cands = [(w, m) for w, m in cands if any(x["blocking"] and x["cat"] != "light" for x in m["items"])]
            placed = None
            for _ in range(8):
                m = self._choose(cands)
                if not m: break
                seg = min(rem, m["L"] * self.rng.uniform(0.9, 1.15))
                if rem - seg < 2.5: seg = rem                      # no sliver left over
                c0, c1 = (st["L"] - cursor - seg, st["L"] - cursor) if rev else (cursor, cursor + seg)
                placed = self.place_wall_motif(m, self._sub(st, c0, c1), need=need if first else None)
                if placed: break
                cands = [(w, x) for w, x in cands if x is not m]
            if not placed:
                if first: return out
                break
            out += placed
            st["used"] = True
            self._mark_once()
            cursor += seg + self.rng.uniform(0.4, 2.0)
            first = False
            if self.coverage() >= self.cover_goal or self.rng.random() > min(0.85, 0.3 + share): break
        return out

    def _main_door_wall(self):
        op = self.main_door()
        if not op: return None
        side = ("BR" if op["sign"] > 0 else "TL") if op["line"] == "/" else ("TR" if op["sign"] > 0 else "BL")
        return F.WALL_NAME[f"{op['line']}|{side}"]

    def compose_room(self):
        rng_c = ww_cover(self.rtype)
        self.cover_goal = self.rng.uniform(*rng_c) if rng_c else 0.15
        sk = self.skeleton()
        if sk is None: return
        # a carpet in floor tiles, in the share of Westwood's rooms of the type that lay one (rules/out/motifs.json
        # stats carpeted: three bedrooms in four, no storeroom); furniture stands on it as on any floor
        carpeted = (self.lib["stats"].get(self.rtype) or {}).get("carpeted", 0.0)
        if self.rng.random() < carpeted and self.lay_carpet(None):
            self.log.append("carpet laid")
        self.log.append(f"skeleton {sk['id']} ({sk['type']}, {sk['culture']}, {sk['tiles']} tiles)")
        skm = self.lib["by_room"][sk["id"]]
        door = self._main_door_wall()
        fo = self.prof.get("focal")
        mirrored = self.rng.random() < 0.5
        focal_done = False
        # 1. the focal piece on the wall the skeleton's stands on from its door
        if fo:
            sf = sk.get("focal") or {}
            if sf.get("wall") == "centre" and fo.get("where") != "back":
                cands = [(self._weight(m, sk), m) for m in self.lib["centre"]
                         if any(re.search(fo["types"], x["t"]) for x in m["items"])]
                for _ in range(6):
                    m = self._choose(cands)
                    if not m: break
                    if self.place_centre_motif(m, m["pos"]): focal_done = True; self._mark_once(); break
                    cands = [(w, x) for w, x in cands if x is not m]
            if not focal_done:
                rel = sf.get("rel")
                back_only = fo.get("where") == "back"
                sts = sorted(self.stretches, key=lambda s: -s["L"])
                scored = []
                for st in sts:
                    if back_only and not st["back"]: continue
                    sc = st["L"] + self.rng.uniform(0, 3)
                    if door and rel:
                        r2 = "door" if st["name"] == door else "opposite" if OPP[door] == st["name"] else "beside"
                        if r2 == rel: sc += 8
                    scored.append((sc, st))
                for _, st in sorted(scored, key=lambda p: -p[0])[:4]:
                    src = (sf.get("wall") if sf.get("wall") in MIRROR else st["name"])
                    share = max([w["used"] for w in skm["wall"] if w["wall"] == src] or [0.4])
                    if self.fill_stretch(st, sk, share, need=fo["types"]):
                        focal_done = True
                        self._mark_once()
                        if sf.get("wall") in MIRROR: mirrored = MIRROR[sf["wall"]] == st["name"]
                        break
        # 2. the other walls, as the skeleton uses its walls
        sk_use = collections.defaultdict(list)
        for w in skm["wall"]: sk_use[w["wall"]].append(w["used"])
        for st in sorted(self.stretches, key=lambda s: (not s["back"], -s["L"])):
            if st["used"] or st["L"] < 1.5: continue
            src = MIRROR[st["name"]] if mirrored else st["name"]
            uses = sk_use.get(src) or sk_use.get(MIRROR[src]) or [0.0]
            share = max(uses)
            if share < 0.05 and self.rng.random() < 0.85: continue           # a bare wall stays bare
            self.fill_stretch(st, sk, share)
        # 3. corners
        for cm in skm["corner"]:
            want = MIRROR[cm["corner"]] if mirrored else cm["corner"]
            c = self.corners.get(want)
            if not c: continue
            cands = []
            for m in self.lib["corner"]:
                w = self._weight(m, sk)
                if not w: continue
                if m["corner"] == want: cands.append((w, (m, False)))
                elif MIRROR[m["corner"]] == want: cands.append((w * 0.8, (m, True)))
            for _ in range(8):
                pick = self._choose(cands)
                if not pick: break
                if self.place_corner_motif(pick[0], c, pick[1]): break
                cands = [(w, x) for w, x in cands if x is not pick]
        # 4. the free groups, where the skeleton's stood
        for g in skm["centre"]:
            if focal_done and fo and any(re.search(fo["types"], x["t"]) for x in g["items"]) and \
                    (sk.get("focal") or {}).get("wall") == "centre":
                continue
            pos = (1 - g["pos"][1], 1 - g["pos"][0]) if mirrored else tuple(g["pos"])
            lead_big = max(g["span"])
            cands = []
            for m in self.lib["centre"]:
                w = self._weight(m, sk)
                if not w: continue
                if all(F._family_of(x["t"]) in self.never for x in m["items"] if x["blocking"]) and \
                        any(x["blocking"] for x in m["items"]): continue
                w *= math.exp(-abs(max(m["span"]) - lead_big) / 3.0)
                cands.append((w, m))
            for _ in range(8):
                m = self._choose(cands)
                if not m: break
                if self.place_centre_motif(m, pos): break
                cands = [(w, x) for w, x in cands if x is not m]
        self.repair()
        self.top_up_motifs(sk)

    def top_up_motifs(self, sk):
        """More motifs of the type while the floor is covered less than this room's draw from Westwood's p25-p75 for
        the type: a free stretch of wall first (back walls first), then a corner, then a free group where Westwood's
        stood."""
        for _ in range(TOP_UP_TRIES):
            if self.coverage() >= self.cover_goal: break
            pick = self.rng.random()
            free = [p for st in self.stretches if not st.get("full") for p in self.free_parts(st)]
            if free and pick < 0.6:
                free.sort(key=lambda p: (not p["back"], -p["L"] * self.rng.uniform(0.5, 1.5)))
                part = free[0]
                if not self.fill_stretch(part, sk, 0.4, solid=True):
                    part["parent"]["full"] = True
                continue
            if pick < 0.75 and self.corners:
                c = self.corners[self.rng.choice(sorted(self.corners))]
                cands = [(self._weight(m, sk), m) for m in self.lib["corner"] if m["corner"] == c["name"]]
                m = self._choose(cands)
                if m: self.place_corner_motif(m, c, False)
                continue
            cands = [(self._weight(m, sk), m) for m in self.lib["centre"]
                     if any(x["blocking"] and x["cat"] not in FREE_NEVER for x in m["items"])]
            m = self._choose(cands)
            if m: self.place_centre_motif(m, m["pos"])

    def _seat_anchor_in_room(self):
        return any(F._family_of(o["type"]) in ("table", "desk", "fireplace", "counter_bar") for o in self.objects)

    def _drop_lone_seats(self, placed):
        """Seats of a motif with no table, desk or counter within reach are taken up again (a chair stands at its
        table: the checker's "2 chairs and no table to sit at")."""
        keep = []
        of = lambda fams: [self._placed_of[id(o)] for o in self.objects if id(o) in self._placed_of and
                           F._family_of(o["type"]) in fams]
        tables, beds = of(("table", "desk", "counter_bar", "counter_shop", "lab")), of(("bed",))
        hearths = of(("fireplace",))
        near = lambda rec, ps, d: any(max(abs(rec[0] - t[0]) - rec[2] - t[2], abs(rec[1] - t[1]) - rec[3] - t[3]) < d
                                      for t in ps)
        if self.rtype in SEATED:                      # a table with no seat at it goes, and its seats then
            seats = of(SEATS)
            for o in list(placed):
                rec = self._placed_of.get(id(o))
                if rec and F._family_of(o["type"]) == "table" and not near(rec, seats, 1.2):
                    self._remove(o); placed.remove(o)
            tables = of(("table", "desk", "counter_bar", "counter_shop", "lab"))
        for o in placed:
            rec = self._placed_of.get(id(o))
            fam = F._family_of(o["type"])
            # a seat at a table or desk, or by the hearth; in a room with a table, a seat may stand loose (Westwood's
            # chair pulled out by a wall), never in a room with nothing to sit at
            loose_ok = fam in SEATS and (near(rec, hearths, 3.0) or (tables and self.rtype in LOOSE_SEATS)) if rec else False
            if rec and ((fam in SEATS and not near(rec, tables, 1.2) and not loose_ok) or
                        (fam == "nightstand" and not near(rec, beds, 1.6))):
                self._remove(o); continue
            keep.append(o)
        return keep

    def _mark_once(self):
        for fam, types in ONCE.items():
            if self.rtype in types and self._count_fam(fam): self.once_done.add(fam)

    def _count_fam(self, fam):
        return sum(1 for o in self.objects if F._family_of(o["type"]) == fam)

    def repair(self):
        """The type's must pieces, from more motifs that hold them; the recipe's placement as the last resort."""
        must = self.prof.get("must", {})
        for fam, n in must.items():
            for attempt in range(6):
                if self._count_fam(fam) >= n: break
                has = lambda m: any(F._family_of(x["t"]) == fam for x in m["items"])
                free = [st for st in self.stretches if not st["used"] and st["L"] >= 2.0]
                done = False
                self.rng.shuffle(free)
                for st in free[:4]:
                    cands = [(w, m) for w, m in self._wall_cands(st, None) if has(m)]
                    m = self._choose(cands)
                    if m and self.place_wall_motif(m, st):
                        done = True; break
                if not done:
                    cands = [(self._weight(m), m) for m in self.lib["centre"] if has(m)]
                    m = self._choose(cands)
                    if m and self.place_centre_motif(m, (self.rng.uniform(0.3, 0.7), self.rng.uniform(0.3, 0.7))):
                        done = True
                if not done:
                    if fam in F.WALL_ONLY or fam in ("storage", "stove", "fireplace", "bed", "desk", "lab"):
                        res = self.place_on_wall(fam, at=self.rng.choice(["center", "corner"]))
                    else:
                        res = self.place_center(fam)
                    if res: self.log.append(f"repair {fam}: recipe placement")
                    else: break

    def furnish(self):
        self.composing = True
        self.compose_room()
        self.composing = False
        self.face_statues()
        # the room's ambient light, as the recipe engine adds it (not drawn; it lights what is there)
        self.placing_light = True
        cl = self.T.get("colorlights", {})
        if self.rng.random() < max(0.35, cl.get("p_any", 0)):
            presets = [p for p in self.lighting["colorlight"]["presets"]
                       if p["animation"] == "steady" and p["family"] in ("orange", "yellow", "white") and
                       p["intensity_class"] == "full"]
            if presets:
                p = self.rng.choices(presets, [x["weighted_share"] for x in presets])[0]
                cu, cv = self.g.centroid
                x, y = F._px(cu, cv)
                self.objects.append(self.spec.obj_px("ColorLight", x, y, xfer=dict(p["xfer"])))
        self.placing_light = False
        return self.objects


def furnish_room(spec, room, kind=None, rng=None, style="town"):
    """Furnish one room from motifs, in place. Returns the list of object dicts added to the spec."""
    rng = rng or random.Random(0)
    f = MotifFurnisher(spec, room, kind, rng, style)
    objs = f.furnish()
    room.kind = f.kind
    room.spots = f.spots
    room.kb_refused = dict(f.kb_refused)
    room.motif_log = list(f.log)
    from kit import loot
    loot.tag(spec, objs, f.kind)
    return objs


def furnish_original(spec, room, kind=None, rng=None, style="town", tries=6, threshold=None):
    """furnish_room, composed again (the previous attempt's objects removed) until the layout is no near copy of a stock
    room (kit/originality.py check). Returns (objects, check result)."""
    from kit import originality as ORIG
    threshold = threshold or ORIG.THRESHOLD
    rng = rng or random.Random(0)
    best = None
    for _ in range(tries):
        objs = furnish_room(spec, room, kind, random.Random(rng.random()), style)
        res = ORIG.check(spec, room, objs, threshold)
        if res["ok"]: return objs, res
        if best is None or res["max_sim"] < best[1]["max_sim"]: best = (objs, res)
        ids = {id(o) for o in objs}
        spec.d["objects"][:] = [o for o in spec.d["objects"] if id(o) not in ids]
    objs = furnish_room(spec, room, kind, random.Random(rng.random()), style)
    return objs, ORIG.check(spec, room, objs, threshold)
