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
TOP_UP_TRIES = 40


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


# ---- clusters: Westwood's groups whole (round 2) -------------------------------------------------------------------
# The motifs above cut a room's arrangement at the walls: a desk on the wall and its chair in front of it became a wall
# motif and a lone centre group, a bed's chest at its foot another. The independent judges' first fault with the motif
# rooms was exactly that: "pieces floating free with no relation, chairs not pulled up to tables". A cluster keeps every
# piece of a Westwood group together with its geometry: the pieces within LINK of each other (edge to edge), anchored to
# the wall its wall pieces stand against (the free pieces before them kept relative to them), to a corner (a heap of
# small pieces against both walls), or free in the room (a table and its chairs).
LINK = 0.9
SMALL = {"supply", "plant", "statue", "light", "clutter", "bones", "straw", "monument", "feature", "chest"}
PELT = re.compile(r"Bearskin|Pelt")
SEAT_AT = {"table", "desk", "lab", "hearth", "counter_bar", "counter_shop"}    # what a seat in a cluster faces
UNIFY = {"chair", "chest", "nightstand", "light", "table", "bench"}            # one kind of each per room
# the piece a cluster is about, first found in this order (a desk cluster with a water barrel beside it is a desk's)
LEAD_ORDER = ("bed", "hearth", "counter_bar", "counter_shop", "lab", "desk", "table", "stove", "tomb", "shop_rack", "rack",
              "shelf", "bench", "chest", "nightstand", "supply", "statue", "chair", "light", "clutter", "plant", "rug",
              "hanging")
MINOR = {"supply", "chest", "light", "statue", "clutter", "plant", "nightstand"}   # small leads that stand in for each other
ZONE_FLOOR, ZONE_GAP = 1.0, 1.6     # a zone per Westwood median room of the type (floor), zones 1.6 units apart
FREE_TOPUP = 1.3                     # rooms this many times Westwood's median floor may take a free group more
DRESS = {"supply", "chest", "clutter", "statue", "plant", "nightstand", "bench"}   # the details between groups
DRESS_TRIES = 12
SUPPLY_SHARE = 0.4                   # no kind of store past this share of a room's stock
GROUP_PAD = 0.9                      # a step of floor between the groups along a wall
WALLS_ONLY = {"storeroom", "armoury", "cellar"}    # stores keep their middle as the aisle (no free heaps under 60 tiles)
DEBUG = os.environ.get("MOTIF_DEBUG") == "1"
COMPOSE = "clusters"                 # "clusters" (round 2) or "motifs" (round 1: wall, corner and centre motifs)


def _edge(a, b):
    return max(abs(a["u"] - b["u"]) - a["hu"] - b["hu"], abs(a["v"] - b["v"]) - a["hv"] - b["hv"])


def _run_of(r, name, p):
    """The wall run named `name` of Westwood room r that piece p stands against (the nearest whose span covers it)."""
    best = None
    for w in r["walls"]:
        if w["name"] != name: continue
        along = p["v"] if w["line"] == "/" else p["u"]
        if not w["lo"] - 1.5 <= along <= w["hi"] + 1.5: continue
        off = abs((p["u"] if w["line"] == "/" else p["v"]) - w["coord"])
        if best is None or off < best[0]: best = (off, w)
    return best and best[1]


def _wall_frame(r, w):
    """(sign into the room, interior start, interior end, from_hi) of run w of Westwood room r."""
    cu, cv = (r["U"][1] - r["U"][0]) / 2, (r["V"][1] - r["V"][0]) / 2
    sign = 1 if ((cu if w["line"] == "/" else cv) > w["coord"]) else -1
    return sign, w["lo"] + 1.0, w["hi"] - 1.0, w["name"] in FROM_HI


def _lead(items):
    bl = [x for x in items if x["blocking"] and x["cat"] != "light"] or [x for x in items if x["blocking"]] or items
    return max(bl, key=lambda x: x["hu"] * x["hv"])["cat"] if bl else "bare"


def room_clusters(r):
    """The clusters of one Westwood room (rules/out/motifs.json rooms[].pieces)."""
    ps = [dict(p, i=i) for i, p in enumerate(r.get("pieces") or [])]
    floor = [p for p in ps if not p["hang"]]
    hung = [p for p in ps if p["hang"]]
    n = len(floor)
    par = list(range(n))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            a, b = floor[i], floor[j]
            lim = 0.3 if "rug" in (a["cat"], b["cat"]) else LINK
            if _edge(a, b) <= lim: par[find(i)] = find(j)
    comps = collections.defaultdict(list)
    for i in range(n): comps[find(i)].append(floor[i])
    out = []
    W, H = max(1, r["U"][1] - r["U"][0]), max(1, r["V"][1] - r["V"][0])
    for comp in comps.values():
        walls = {p["wall"] for p in comp if p["wall"]}
        corner = next((k for k, ws in CORNER_WALLS.items() if set(ws) == walls), None)
        big = [p for p in comp if p["blocking"] and (p["cat"] not in SMALL or max(p["hu"], p["hv"]) > 1.4)]
        if not walls:
            out.append(_free_cluster(r, comp, W, H))
        elif len(walls) == 1:
            c = _wall_cluster(r, next(iter(walls)), comp)
            if c: out.append(c)
        elif corner and not big:
            c = _corner_cluster(r, corner, comp)
            if c: out.append(c)
        else:                                   # split by wall: each free piece goes with its nearest wall piece
            groups = collections.defaultdict(list)
            on = [p for p in comp if p["wall"]]
            for p in comp:
                if p["wall"]: groups[p["wall"]].append(p)
                else: groups[min(on, key=lambda q: _edge(p, q))["wall"]].append(p)
            for name, g in groups.items():
                c = _wall_cluster(r, name, g)
                if c: out.append(c)
    for p in hung:
        if not p["wall"]: continue
        c = _wall_cluster(r, p["wall"], [p], kind="hang")
        if c: out.append(c)
    for k, c in enumerate(out):
        c.update(room=r["id"], type=r["type"], culture=r["culture"], cid=f"{r['id']}#{k}",
                 lead=_lead(c["items"]), n=len(c["items"]),
                 n_block=sum(1 for x in c["items"] if x["blocking"] and x["cat"] != "light"))
    return out


def _wall_cluster(r, name, comp, kind="wall"):
    att = [p for p in comp if p["wall"] == name]
    w = _run_of(r, name, att[0]) if att else None
    if not w: return None
    sign, lo, hi, from_hi = _wall_frame(r, w)
    items = []
    for p in comp:
        along = p["v"] if w["line"] == "/" else p["u"]
        s = (hi - along) if from_hi else (along - lo)
        d = ((p["u"] if w["line"] == "/" else p["v"]) - w["coord"]) * sign
        ha, hp = (p["hv"], p["hu"]) if w["line"] == "/" else (p["hu"], p["hv"])
        items.append(dict(t=p["t"], cat=p["cat"], fam=p["fam"], blocking=p["blocking"], hang=p["hang"], s=s, d=d,
                          ha=ha, hp=hp, hu=p["hu"], hv=p["hv"], att=p["wall"] == name, gap=p["gap"] or 0.0))
    a0 = min(x["s"] - x["ha"] for x in items)
    a1 = max(x["s"] + x["ha"] for x in items)
    for x in items: x["s"] -= a0
    L = hi - lo
    return dict(kind=kind, wall=name, back=name in ("NE", "NW"), Lw=round(L, 2), span=round(a1 - a0, 2),
                g0=round(a0, 2), g1=round(L - a1, 2), rel=round((a0 + a1) / 2 / max(1.0, L), 3),
                depth=round(max(x["d"] + x["hp"] for x in items), 2), items=items)


def _corner_cluster(r, corner, comp):
    na, nb = CORNER_WALLS[corner]
    pa = next((p for p in comp if p["wall"] == na), None)
    pb = next((p for p in comp if p["wall"] == nb), None)
    wa = pa and _run_of(r, na, pa)
    wb = pb and _run_of(r, nb, pb)
    if not (wa and wb): return None
    items = []
    for p in comp:
        items.append(dict(t=p["t"], cat=p["cat"], fam=p["fam"], blocking=p["blocking"], hang=p["hang"],
                          da=abs(p["u"] - wa["coord"]), db=abs(p["v"] - wb["coord"]), hu=p["hu"], hv=p["hv"]))
    return dict(kind="corner", corner=corner, items=items,
                span=round(max(max(x["da"] + x["hu"], x["db"] + x["hv"]) for x in items), 2))


def _free_cluster(r, comp, W, H):
    u0 = min(p["u"] - p["hu"] for p in comp); u1 = max(p["u"] + p["hu"] for p in comp)
    v0 = min(p["v"] - p["hv"] for p in comp); v1 = max(p["v"] + p["hv"] for p in comp)
    gu, gv = (u0 + u1) / 2, (v0 + v1) / 2
    items = [dict(t=p["t"], cat=p["cat"], fam=p["fam"], blocking=p["blocking"], hang=False, du=p["u"] - gu,
                  dv=p["v"] - gv, hu=p["hu"], hv=p["hv"]) for p in comp]
    return dict(kind="free", items=items, pos=(round(gu / W, 3), round(gv / H, 3)), span_uv=(u1 - u0, v1 - v0),
                span=round(max(u1 - u0, v1 - v0), 2),
                wall_dist=round(min(gu, W - gu, gv, H - gv), 2))


@lru_cache(None)
def clusters_of(rid):
    return tuple(room_clusters(library()["rooms"][rid]))


@lru_cache(None)
def ww_floor(rtype):
    """The median floor (cells) of the Westwood rooms a room of the type draws on (its own, else its pool's)."""
    rooms = library()["rooms"]
    fl = sorted(rooms[rid]["floor"] for rid, w in pool(rtype).items() if w >= 1.0 and rooms[rid].get("floor")) or \
        sorted(rooms[rid]["floor"] for rid in pool(rtype) if rooms[rid].get("floor")) or [40]
    return fl[len(fl) // 2]


@lru_cache(None)
def ww_tiles(rtype):
    """Westwood's floor tiles for the type (p10..p90), or None."""
    try:
        with open(WW_PATH, encoding="utf-8") as f:
            return (json.load(f)["types"].get(rtype) or {}).get("tiles")
    except OSError:
        return None


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
        self.floor = len(self.g.cells)            # floor cells, as Westwood's rooms are measured (rooms[].floor)
        self.lights_n = 0
        self.once_done = set()                    # ONCE families already in the room
        self.used_ids = set()                     # the motifs used in this room
        # lights as Westwood lights rooms of the type (rules/out/motifs.json stats: under one a room in most types),
        # never past the knowledge base's cap for the size
        lpr = (self.lib["stats"].get(self.rtype) or {}).get("lights_per_room", 1.0)
        self.light_cap = min(OBJ.light_cap(self.tiles), max(1, int(round(lpr * 1.5 + 0.4))))
        self.stretches = self._stretches()
        self.corners = self._corners()
        self.cat_kind = {}                        # category -> the one kind of it the room takes (UNIFY)
        self._ok_memo = {}
        # the straight way in from every door kept clear four units deep (the user's rule, rules/rooms/README.md GW-7)
        for op in self.openings:
            self.g.zones.append(self._way_box(op, 0.5, min(4.4, 0.62 * op["extent"])))

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
        k0, k1 = OBJ.kind(t), self.cat_kind.get(cat)
        if cat in UNIFY and k1 and k0 != k1:                 # the room's one kind of chair, chest, candelabra
            alt = k1 + t[len(k0):]
            if self.ok_type(alt) and F._family_of(alt) == F._family_of(t): t = alt
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

    # ---- round 2: composing from Westwood's clusters, zone by zone, round one centrepiece ---------------------------
    def _zones(self):
        """The room split into zones of Westwood's room sizes for the type: one zone up to 1.7 times Westwood's median
        room, else two halves across the long axis with a walking gap between them (a bed end and a sitting end). Each
        zone: its box, its tiles, its parts of the walls (stretches clipped to it) and its corners."""
        p50 = ww_floor(self.rtype)
        lu, lv = self.U1 - self.U0, self.V1 - self.V0
        M = 4.0
        box = (self.U0 - M, self.U1 + M, self.V0 - M, self.V1 + M)
        boxes = [box]
        nz = max(1, min(4, int(self.floor / (ZONE_FLOOR * p50) + 0.5)))
        long_u = lu >= lv
        L, S = max(lu, lv), min(lu, lv)
        g = ZONE_GAP / 2
        if nz >= 3 and L / max(1, S) < 1.6 and S >= 10:
            # a big square room: four quarters round its middle (the front quarter, by the SE and SW walls, stays light
            # as Westwood's front walls do)
            mu = (self.U0 + self.U1) / 2 + self.rng.uniform(-0.1, 0.1) * lu
            mv = (self.V0 + self.V1) / 2 + self.rng.uniform(-0.1, 0.1) * lv
            boxes = [(box[0], mu - g, box[2], mv - g), (box[0], mu - g, mv + g, box[3]),
                     (mu + g, box[1], box[2], mv - g), (mu + g, box[1], mv + g, box[3])]
        elif nz >= 2 and L >= 9:
            k = min(nz, max(2, int(L / 7)))            # strips across the long axis, each at least 7 units long
            lo, hi = (self.U0, self.U1) if long_u else (self.V0, self.V1)
            cuts = [lo + (hi - lo) * i / k + (self.rng.uniform(-0.08, 0.08) * (hi - lo) if 0 < i < k else 0)
                    for i in range(k + 1)]
            boxes = []
            for i in range(k):
                a = (box[0] if long_u else box[2]) if i == 0 else cuts[i] + g
                b = (box[1] if long_u else box[3]) if i == k - 1 else cuts[i + 1] - g
                boxes.append((a, b, box[2], box[3]) if long_u else (box[0], box[1], a, b))
        zones = []
        for b in boxes:
            sts = []
            for st in self.stretches:
                r = st["run"]
                perp_lo, perp_hi = (b[0], b[1]) if r["line"] == "/" else (b[2], b[3])
                if not perp_lo <= r["coord"] <= perp_hi: continue
                a_lo, a_hi = (b[2], b[3]) if r["line"] == "/" else (b[0], b[1])
                s0, s1 = max(st["s0"], a_lo), min(st["s1"], a_hi)
                if s1 - s0 < 1.0: continue
                sts.append(dict(st, s0=s0, s1=s1, L=s1 - s0, parent=st, used=False))
            corners = {k: c for k, c in self.corners.items()
                       if b[0] <= c["a"]["coord"] <= b[1] and b[2] <= c["b"]["coord"] <= b[3]}
            inner = (max(b[0], self.U0), min(b[1], self.U1), max(b[2], self.V0), min(b[3], self.V1))
            zones.append(dict(box=b, inner=inner, stretches=sts, corners=corners,
                              floor=self.floor * ((inner[1] - inner[0]) * (inner[3] - inner[2])) /
                              max(1.0, lu * lv)))
        return zones

    def _focal_wall(self):
        """The back wall the focal piece stands on: the one farther from the main door (across the room from a door in
        a front wall; the other back wall when the door is in one)."""
        door = self._main_door_wall()
        backs = [n for n in ("NE", "NW") if any(st["name"] == n and st["L"] >= 3.0 for st in self.stretches)]
        if not backs: return None
        if door in ("SW", "SE"):
            want = OPP[door]
            if want in backs: return want
        elif door in ("NE", "NW"):
            other = MIRROR[door]
            if other in backs: return other
        return max(backs, key=lambda n: max(st["L"] for st in self.stretches if st["name"] == n))

    def _zone_skeleton(self, z, used):
        rooms = [r for rid, r in self.lib["rooms"].items() if self.pool.get(rid, 0) >= 1.0 and rid not in used and
                 r.get("pieces")] or [self.lib["rooms"][rid] for rid in self.pool if self.lib["rooms"][rid].get("pieces")]
        cands = []
        for r in rooms:
            w = math.exp(-abs(math.log(max(9, r["floor"]) / max(9, z["floor"]))) * 2.0)
            if r["culture"] == self.culture: w *= 1.5
            cands.append((w, r))
        return self._choose(cands)

    @staticmethod
    def _lead_of(c):
        cats = {x["cat"] for x in c["items"] if x["blocking"]} or {x["cat"] for x in c["items"]}
        return next((k for k in LEAD_ORDER if k in cats), c["lead"])

    def _cw(self, c, sk_id=None):
        """A cluster's weight here: its room's weight in the pool, none when it was used, its room gave its share, or it
        holds a piece the room may not hold or holds once already."""
        w = self.pool.get(c["room"], 0.0)
        if not w or c["cid"] in self.used_ids or self.sources[c["room"]] >= MAX_PER_SOURCE: return 0.0
        bl = [x for x in c["items"] if x["blocking"] and x["cat"] != "light"]
        fams = {F._family_of(x["t"]) for x in bl}
        if fams & self.once_done: return 0.0
        if any(F._family_of(x["t"]) in self.never and F._family_of(x["t"]) not in SEATS for x in bl): return 0.0
        if self.never_rx and any(self.never_rx.search(x["t"]) for x in bl): return 0.0
        if any(self._capped(x["t"]) for x in bl if F._family_of(x["t"]) not in SEATS): return 0.0
        if bl and all(F._family_of(x["t"]) in SEATS for x in bl) and                 not (c["kind"] == "wall" and self.rtype in LOOSE_SEATS):
            return 0.0                                  # never a lone chair facing nothing (a bench on a hall's wall)
        if c["kind"] == "free":
            if not bl and not any(PELT.search(x["t"]) for x in c["items"]): return 0.0
            if self.rtype in WALLS_ONLY and c["kind"] == "free" and self.tiles < 60: return 0.0
        if c["room"] == sk_id: w *= 0.3
        if c["culture"] != self.culture: w *= 0.5
        return w

    def _pool_clusters(self):
        if not hasattr(self, "_pc"):
            self._pc = [c for rid in sorted(self.pool) for c in clusters_of(rid)]
        return self._pc

    # -- plans: where each piece of a cluster goes in our room
    def _face_seats(self, plan):
        """A seat in a cluster faces the table, desk or hearth of its cluster nearest to it (the seat's own variant for
        that side, kit chair_facing): a chair is drawn up to its table whichever way the cluster was turned."""
        anchors = [p for p in plan if p["x"]["cat"] in SEAT_AT]
        if not anchors: return
        for p in plan:
            if F._family_of(p["t"]) not in SEATS or p["run"] is not None: continue
            a = min(anchors, key=lambda a: abs(a["u"] - p["u"]) + abs(a["v"] - p["v"]))
            du, dv = a["u"] - p["u"], a["v"] - p["v"]
            d = ("+u" if du > 0 else "-u") if abs(du) >= abs(dv) else ("+v" if dv > 0 else "-v")
            var = (self.chair_facing.get(F._base(p["t"]), {}).get(d) or {}).get("variant")
            if var and self.ok_type(var): p["t"] = var

    def _types_for(self, c, run_of):
        """[(item, type)] for cluster c's pieces here (run_of(item): the wall run whose variant it takes, or None), or
        None when a piece the cluster stands on (not a seat, a light or a hanging) can't be had."""
        out = []
        kinds = collections.Counter(OBJ.kind(o["type"]) for o in self.objects
                                    if OBJ.category(o["type"]) == "supply")
        tot = sum(kinds.values())
        for x in c["items"]:
            t0 = x["t"]
            if x["cat"] == "supply":
                # stores mixed as Westwood mixes them: a kind past its share of the room's stock gives way to the
                # type's least used one (never one kind filling a big room, review/FEEDBACK.md TW-8)
                k0 = OBJ.kind(t0)
                if kinds[k0] >= max(3, SUPPLY_SHARE * (tot + 1)):
                    alts = sorted(((kinds[OBJ.kind(t2)], n, t2) for t2, n in type_kinds(self.rtype).get("supply", {}).items()
                                   if OBJ.kind(t2) != k0 and self.ok_type(t2) and self.belongs(t2)),
                                  key=lambda a: (a[0], -a[1]))
                    if alts: t0 = alts[0][2]
                kinds[OBJ.kind(t0)] += 1
                tot += 1
            t = self._fit_type(t0, x["cat"], run_of(x), None)
            if not t:
                if x["blocking"] and x["cat"] != "light" and F._family_of(x["t"]) not in SEATS:
                    if DEBUG: self.log.append(f"  notype {x['t']} capped={self._capped(x['t'])} run={run_of(x) and run_of(x)['side']}")
                    return None
                continue
            out.append((x, t))
        return out

    def _plan_wall(self, c, st, at, flip):
        run = st["run"]
        typed = self._types_for(c, lambda x: run if (x.get("att") or x["hang"]) else None)
        if not typed: return None
        pos = {}
        for x, t in typed:
            if x.get("att") or x["hang"]:
                hu, hv = self.half(t)
                ha, hp = (hv, hu) if run["line"] == "/" else (hu, hv)
                gap = x["gap"] if x["hang"] else max(0.12, min(x["gap"], 0.9))
                pos[id(x)] = (x["s"], gap + hp, ha, hp)
        if not pos: return None
        for x, t in typed:
            if id(x) in pos: continue
            hu, hv = self.half(t)
            ha, hp = (hv, hu) if run["line"] == "/" else (hu, hv)
            anc = min((y for y, _ in typed if id(y) in pos and not y["hang"]),
                      key=lambda y: abs(y["s"] - x["s"]) + abs(y["d"] - x["d"]), default=None)
            d = x["d"]
            if anc is not None:
                _, dn, _, hpn = pos[id(anc)]
                d = x["d"] + (dn + hpn) - (anc["d"] + anc["hp"])
            pos[id(x)] = (x["s"], d, ha, hp)
        plan = []
        for x, t in typed:
            s, d, ha, hp = pos[id(x)]
            s2 = at + ((c["span"] - s) if flip else s)
            if (x.get("att") or x["hang"]) and not (ha - 0.2 <= s2 <= st["L"] - ha + 0.2):
                if DEBUG: self.log.append(f"  range {t} s2={s2:.1f} ha={ha:.1f} L={st['L']:.1f}")
                return None
            along = (st["s1"] - s2) if st["from_hi"] else (st["s0"] + s2)
            perp = run["coord"] + run["sign"] * d
            u, v = (perp, along) if run["line"] == "/" else (along, perp)
            plan.append(dict(t=t, u=u, v=v, x=x, run=run if (x.get("att") or x["hang"]) else None, along=along,
                             ha=ha, hp=hp))
        self._face_seats(plan)
        return plan

    def _plan_corner(self, c, corner, mirrored):
        a, b = corner["a"], corner["b"]
        typed = self._types_for(c, lambda x: None)
        if not typed: return None
        plan = []
        for x, t in typed:
            da, db = (x["db"], x["da"]) if mirrored else (x["da"], x["db"])
            run = a if da <= db else b
            if x["cat"] not in ("supply", "plant", "light", "clutter", "statue", "chest") or x["hang"]:
                t2 = self._fit_type(t, x["cat"], run, None)
                if not t2:
                    if x["blocking"] and x["cat"] != "light": return None
                    continue
                t = t2
            plan.append(dict(t=t, u=a["coord"] + a["sign"] * da, v=b["coord"] + b["sign"] * db, x=x, run=None,
                             along=0, ha=0, hp=0))
        self._face_seats(plan)
        return plan

    def _plan_free(self, c, inner, pos, mirrored, shift=(0.0, 0.0)):
        typed = self._types_for(c, lambda x: None)
        if not typed: return None
        su, sv = c["span_uv"]
        if mirrored: su, sv = sv, su
        u0, u1, v0, v1 = inner
        gu = u0 + pos[0] * (u1 - u0) + shift[0]
        gv = v0 + pos[1] * (v1 - v0) + shift[1]
        mu, mv = su / 2 + 1.0, sv / 2 + 1.0
        if u1 - u0 > 2 * mu: gu = min(max(gu, u0 + mu), u1 - mu)
        if v1 - v0 > 2 * mv: gv = min(max(gv, v0 + mv), v1 - mv)
        plan = []
        for x, t in typed:
            du, dv = (-x["dv"], -x["du"]) if mirrored else (x["du"], x["dv"])
            plan.append(dict(t=t, u=gu + du, v=gv + dv, x=x, run=None, along=0, ha=0, hp=0))
        self._face_seats(plan)
        return plan

    def _realise(self, plan, c, where):
        """Places a cluster's plan as one: every piece it stands on, or nothing (seats, lights and hangings may drop).
        Returns the pieces placed or None."""
        if not plan: return None
        blk = lambda p: p["x"]["blocking"] and p["x"]["cat"] != "light" and not p["x"]["hang"] and \
            F._family_of(p["t"]) not in SEATS
        lead = self._lead_of(c)
        ess = lambda p: blk(p) and p["x"]["cat"] == lead
        n_blk = sum(1 for p in plan if blk(p))
        order = sorted(plan, key=lambda p: (p["x"]["hang"], not ess(p), not blk(p), F._family_of(p["t"]) in SEATS,
                                            -self.footprint(p["t"])))
        snap = (len(self.wall_used), len(self.wall_tall), len(self.g.zones), len(self.light_zones))
        placed, ok = [], True
        self._group = []
        for p in order:
            nud = [(0, 0), (0.12, 0), (-0.12, 0), (0, 0.12), (0, -0.12)]
            o = self._put(p["t"], p["u"], p["v"], p["x"]["blocking"], hang=p["x"]["hang"], touch=True, nudges=nud)
            if o:
                placed.append(o)
                if p["run"] is not None:
                    rec = self._placed_of[id(o)]
                    self._after_put(o, p["run"], p["along"], p["ha"], p["hp"], rec[0], rec[1])
            elif ess(p):
                ok = False
                if DEBUG: self.log.append(f"  fail {c['cid']} {where}: {p['t']} at {p['u']:.1f},{p['v']:.1f} {self._why(p)}")
                break
        self._group = None
        if ok and n_blk and sum(1 for o in placed if F._family_of(o["type"]) not in SEATS and
                                 OBJ.category(o["type"]) != "light" and self._placed_of[id(o)][4]) < 0.6 * n_blk:
            ok = False
        if ok and placed:
            placed = self._drop_lone_seats(placed)
        if not ok or not placed or (c["kind"] != "hang" and not any(
                self._placed_of.get(id(o)) and self._placed_of[id(o)][4] for o in placed)
                and not any(PELT.search(o["type"]) for o in placed)):
            for o in placed:
                if id(o) in self._placed_of:
                    if OBJ.category(o["type"]) == "light": self.lights_n -= 1
                    self._remove(o)
            del self.wall_used[snap[0]:]; del self.wall_tall[snap[1]:]; del self.g.zones[snap[2]:]
            del self.light_zones[snap[3]:]
            return None
        self.sources[c["room"]] += 1
        self.used_ids.add(c["cid"])
        for o in placed:
            cat = OBJ.category(o["type"])
            if cat in UNIFY: self.cat_kind.setdefault(cat, OBJ.kind(o["type"]))
        self._mark_once()
        self.log.append(f"{c['kind']} {where} <- {c['cid']} ({c.get('wall') or c.get('corner') or 'free'}): " +
                        " ".join(o["type"] for o in placed))
        return placed

    def _at_for(self, c, st, like=None):
        """Where along stretch st cluster c starts: at the corner end it kept in Westwood's room (like: the skeleton's
        cluster whose slot it fills), or its place along the wall scaled to ours."""
        ref = like or c
        L, span = st["L"], c["span"]
        if span > L + 0.05: return None
        if ref.get("g0", 9) <= 1.3: at = min(c.get("g0", 0.3), 1.3)
        elif ref.get("g1", 9) <= 1.3: at = L - span - min(c.get("g1", 0.3), 1.3)
        else: at = ref.get("rel", 0.5) * L - span / 2 + self.rng.uniform(-0.6, 0.6)
        return min(max(0.0, at), L - span)

    def _try_wall(self, c, sts, like=None, where="", ordered=False):
        """Cluster c on one of stretches sts (longest first, or as given), at its own place along the wall, shifted a
        little when that fails."""
        for st in (sts if ordered else sorted(sts, key=lambda s: -s["L"])):
            at = self._at_for(c, st, like)
            if at is None: continue
            flip = (like or c).get("g0", 9) > 1.3 and (like or c).get("g1", 9) > 1.3 and self.rng.random() < 0.35
            room = st["L"] - c["span"]
            tries = [at + dx for dx in (0.0, 0.35, -0.35, 0.8, -0.8, 1.4, -1.4)] + [room / 2, 0.0, room]
            seen = set()
            for a in tries:
                a2 = round(min(max(0.0, a), room), 2)
                if a2 in seen: continue
                seen.add(a2)
                plan = self._plan_wall(c, st, a2, flip)
                if DEBUG and not plan: self.log.append(f"  noplan {c['cid']} {[x['t'] for x in c['items']]} on {st['name']} L{st['L']:.1f} at {a2:.1f}")
                got = self._realise(plan, c, f"{st['name']} {st['L']:.0f}u@{a2:.1f}") if plan else None
                if got:
                    st["used"] = True
                    return got
        return None

    def _try_corner(self, c, corner, mirrored):
        for sh in ((0, 0), (0.2, 0.2), (0.45, 0.1), (0.1, 0.45)):
            c2 = dict(c, items=[dict(x, da=x["da"] + sh[0], db=x["db"] + sh[1]) for x in c["items"]])
            got = self._realise(self._plan_corner(c2, corner, mirrored), c, corner["name"])
            if got: return got
        return None

    def _try_free(self, c, inner, pos, mirrored):
        spots = [(0.0, 0.0)]
        for rad in (0.8, 1.6, 2.6):
            for k in range(6):
                ang = k * math.pi / 3 + self.rng.uniform(-0.4, 0.4)
                spots.append((rad * math.cos(ang), rad * math.sin(ang)))
        for sh in spots:
            got = self._realise(self._plan_free(c, inner, pos, mirrored, sh), c, f"({pos[0]:.2f},{pos[1]:.2f})")
            if got: return got
        return None

    def _kinds_ok(self, c, back, run=None):
        """Whether every piece cluster c stands on can be had here, on a wall of this class (back: True, False, or None
        for a corner or free group): the type's own pieces, never a faced piece on a front wall. Memoised."""
        key = (c["cid"], back, run and run["side"])
        if key in self._ok_memo: return self._ok_memo[key]
        if back is not None and run is None:
            run = next((st["run"] for st in self.stretches if st["back"] == back), None)
        ok = True
        state = self.rng.getstate()
        for x in c["items"]:
            if not x["blocking"] or x["cat"] == "light" or F._family_of(x["t"]) in SEATS: continue
            att = x.get("att") or x["hang"]
            if not self._fit_type(x["t"], x["cat"], run if att else None, None):
                ok = False
                break
        self.rng.setstate(state)
        self._ok_memo[key] = ok
        return ok

    def _slot_cands(self, c0, sk_id, kind, back=None, max_span=None, run=None):
        lead0 = self._lead_of(c0) if c0 else None
        out = []
        for c in self._pool_clusters():
            if c["kind"] != kind: continue
            if back is not None and c.get("back") != back: continue
            if not self._kinds_ok(c, back if kind in ("wall", "hang") else None, run): continue
            if max_span is not None and c["span"] > max_span: continue
            w = self._cw(c, sk_id)
            if not w: continue
            if c0 is not None:
                l = self._lead_of(c)
                if l != lead0:
                    if l in MINOR and lead0 in MINOR: w *= 0.25
                    else: continue
                w *= math.exp(-abs(c["span"] - c0["span"]) / 2.5)
                if c["room"] == c0["room"] and c is c0: w *= 1.0
            out.append((w, c))
        return out

    def _fill_slot(self, z, c0, mirrored, sk_id):
        """One cluster of the skeleton's: a cluster like it (its lead piece, its size) from the pool, where it stood."""
        if c0["kind"] in ("wall", "hang"):
            W0 = MIRROR[c0["wall"]] if mirrored else c0["wall"]
            for W in (W0, MIRROR[W0]):
                sts = [st for st in z["stretches"] if st["name"] == W]
                if not sts: continue
                longest = max(st["L"] for st in sts)
                cands = self._slot_cands(c0, sk_id, c0["kind"], back=W in ("NE", "NW"), max_span=longest,
                                         run=sts[0]["run"])
                for _ in range(5):
                    c = self._choose(cands)
                    if not c: break
                    got = self._try_wall(c, sts, like=c0)
                    if got: return got
                    cands = [(w, x) for w, x in cands if x is not c]
            return None
        if c0["kind"] == "corner":
            want = MIRROR[c0["corner"]] if mirrored else c0["corner"]
            corner = z["corners"].get(want)
            if not corner: return None
            cands = self._slot_cands(c0, sk_id, "corner")
            for _ in range(6):
                c = self._choose(cands)
                if not c: return None
                mir = (MIRROR[c["corner"]] == want) if c["corner"] != want else False
                got = self._try_corner(c, corner, mir)
                if got: return got
                cands = [(w, x) for w, x in cands if x is not c]
            return None
        # a free group where the skeleton's stood
        pos = (1 - c0["pos"][1], 1 - c0["pos"][0]) if mirrored else tuple(c0["pos"])
        cands = self._slot_cands(c0, sk_id, "free")
        for _ in range(5):
            c = self._choose(cands)
            if not c: return None
            got = self._try_free(c, z["inner"], pos, mirrored)
            if got: return got
            cands = [(w, x) for w, x in cands if x is not c]
        return None

    def _place_focal(self, zones, target):
        """The type's focal cluster (a bed with its nightstands and chest) on the back wall across from the door, at
        its own place along the wall (in its corner, or centred), before anything else."""
        fo = self.prof.get("focal") or {}
        rx = fo.get("types")
        if not rx: return None
        has = lambda c: any(re.search(rx, x["t"]) for x in c["items"])
        walls = [target] + [w for w in ("NE", "NW") if w != target] if target else ["NE", "NW"]
        for W in walls:
            zs = sorted(zones, key=lambda z: -self._door_dist(z))
            for z in zs:
                sts = [st for st in z["stretches"] if st["name"] == W and st["L"] >= 3.5]
                if not sts: continue
                sts.sort(key=lambda st: -(0.3 * self._st_door_dist(st) + st["L"]))
                longest = max(st["L"] for st in sts)
                cands = [(self._cw(c) * (1.5 if c.get("wall") == W else 1.0) * c["n_block"] ** 1.5, c)
                         for c in self._pool_clusters()
                         if c["kind"] == "wall" and c.get("back") and has(c) and c["span"] <= longest]
                for _ in range(12):
                    c = self._choose(cands)
                    if not c: break
                    got = self._try_wall(c, sts, ordered=True)
                    if got:
                        self.focal_zone = z
                        return got
                    cands = [(w, x) for w, x in cands if x is not c]
        return None

    def _st_door_dist(self, st):
        """How far the middle of stretch st lies from the main door."""
        op = self.main_door()
        if not op: return 0.0
        du, dv = (op["coord"], op["along"]) if op["line"] == "/" else (op["along"], op["coord"])
        a = (st["s0"] + st["s1"]) / 2
        r = st["run"]
        u, v = (r["coord"], a) if r["line"] == "/" else (a, r["coord"])
        return math.hypot(u - du, v - dv)

    def _door_dist(self, z):
        op = self.main_door()
        if not op: return 0.0
        du, dv = (op["coord"], op["along"]) if op["line"] == "/" else (op["along"], op["coord"])
        i = z["inner"]
        return math.hypot((i[0] + i[1]) / 2 - du, (i[2] + i[3]) / 2 - dv)

    def _carpet(self):
        """A carpet in floor tiles in the share of Westwood's rooms of the type that lay one. Westwood's larger rooms
        lay a larger one (its big bedrooms: a carpet over most of the floor between the groups on the walls; rules/rooms/
        shells.json carpet_share p50-p90 0.3-0.53): a room over 1.3 times Westwood's median takes a carpet over the
        middle half to two thirds of each side, a smaller room Westwood's own (its floor less a ring, kit/shells)."""
        carpeted = (self.lib["stats"].get(self.rtype) or {}).get("carpeted", 0.0)
        big = self.floor >= 1.3 * ww_floor(self.rtype)
        if carpeted and big: carpeted = min(0.9, carpeted + 0.15)
        if self.rng.random() >= carpeted: return
        laid = None
        if big:
            fu, fv = self.rng.uniform(0.5, 0.7), self.rng.uniform(0.5, 0.7)
            cu, cv = (self.U0 + self.U1) / 2, (self.V0 + self.V1) / 2
            hu, hv = (self.U1 - self.U0) * fu / 2, (self.V1 - self.V0) * fv / 2
            cu += self.rng.uniform(-0.15, 0.15) * (self.U1 - self.U0 - 2 * hu)
            cv += self.rng.uniform(-0.15, 0.15) * (self.V1 - self.V0 - 2 * hv)
            laid = self.lay_carpet((cu - hu, cu + hu, cv - hv, cv + hv), margin=0.0)
        if not laid: laid = self.lay_carpet(None)
        if laid: self.log.append(f"carpet laid ({len(laid)} squares)")

    def compose_clusters(self):
        rng_c = ww_cover(self.rtype)
        self.cover_goal = self.rng.uniform(*rng_c) if rng_c else 0.15
        self._carpet()
        zones = self._zones()
        self.zones = zones
        self.log.append(f"zones {len(zones)} (tiles {self.tiles}, floor {self.floor})")
        fo = self.prof.get("focal") or {}
        target = self._focal_wall() if fo.get("where") == "back" else None
        self.focal_zone = None
        if fo.get("types") and fo.get("where") == "back":
            self._place_focal(zones, target)
        used_sk = set()
        frx = fo.get("types")
        for z in sorted(zones, key=lambda z: z is not self.focal_zone):
            sk = self._zone_skeleton(z, used_sk)
            if not sk: continue
            used_sk.add(sk["id"])
            clus = list(clusters_of(sk["id"]))
            self.log.append(f"zone skeleton {sk['id']} ({sk['type']}, {sk['culture']}, floor {sk['floor']}) for "
                            f"floor {z['floor']:.0f}")
            skf = next((c for c in clus if c["kind"] == "wall" and frx and
                        any(re.search(frx, x["t"]) for x in c["items"])), None)
            if skf and target and skf["wall"] in ("NE", "NW") and z is self.focal_zone:
                mirrored = skf["wall"] != target
            else:
                mirrored = self.rng.random() < 0.5
            clus.sort(key=lambda c: (-c["n_block"], -c["span"]))
            for c0 in clus:
                if c0 is skf and self.once_done: continue
                if frx and any(re.search(frx, x["t"]) for x in c0["items"]) and self.once_done: continue
                if self.coverage() >= self.cover_max * 0.9: break
                if not self._fill_slot(z, c0, mirrored, sk["id"]):
                    self.log.append(f"  slot missed: {c0['kind']} {c0.get('wall') or c0.get('corner') or ''} "
                                    f"{self._lead_of(c0)} {[x['t'] for x in c0['items']]}")
        if fo.get("types") and not self.once_done and fo.get("where") == "back":
            self._place_focal(zones, None)
        self.repair_clusters(zones)
        self.top_up_clusters(zones)
        if fo.get("types") and fo.get("where") not in ("back",) and                 not any(re.search(fo["types"], o["type"]) for o in self.objects):
            self._focal_alone(fo["types"])

    def _focal_alone(self, rx):
        """A kind's focal piece that no Westwood cluster of the type holds (an ore store's cart): against a wall, the
        back walls first, at a spot along it where it fits."""
        types = sorted(t for t in self.things if re.search(rx, t) and self.ok_type(t))
        if not types: return None
        t = self.rng.choice(types)
        sts = sorted(self.stretches, key=lambda st: (not st["back"], -st["L"]))
        for st in sts:
            run = st["run"]
            hu, hv = self.half(t)
            ha, hp = (hv, hu) if run["line"] == "/" else (hu, hv)
            for f in (0.5, 0.3, 0.7, 0.15, 0.85):
                a = st["s0"] + f * st["L"]
                perp = run["coord"] + run["sign"] * (0.4 + hp)
                u, v = (perp, a) if run["line"] == "/" else (a, perp)
                o = self._put(t, u, v, True, nudges=((0, 0), (0.2, 0), (0, 0.2), (-0.2, 0), (0, -0.2)))
                if o:
                    self.log.append(f"focal {t} on {st['name']} (no cluster holds it)")
                    return o
        return None

    def top_up_clusters(self, zones):
        """Up to this room's draw from Westwood's cover for the type: more clusters on the free parts of the walls
        (back walls first, each in its zone, with a step of floor between groups) and in empty corners; in a room well
        over Westwood's size, a free group of the type's (a table and its chairs) in one of its zones."""
        failed = set()
        big = self.floor >= FREE_TOPUP * ww_floor(self.rtype) and (self.rtype not in WALLS_ONLY or self.tiles >= 60)
        free_n = 0
        for _ in range(TOP_UP_TRIES):
            if self.coverage() >= self.cover_goal: break
            walls_done = getattr(self, "_walls_done", False)
            if big and free_n < 1 + (self.floor >= 2.5 * ww_floor(self.rtype)) and                     (walls_done or self.rng.random() < 0.3):
                cands = [(w * (1 + c["n_block"]), c) for w, c in self._slot_cands(None, None, "free")
                         if self._lead_of(c) in ("table", "desk", "bed", "bench") or self.rtype not in ("bedroom",)]
                c = self._choose(cands)
                z = self.rng.choice(zones)
                if DEBUG: self.log.append(f"  free try {c and c['cid']} of {len(cands)}")
                if c and self._try_free(c, z["inner"], tuple(c["pos"]), self.rng.random() < 0.5): free_n += 1
                elif walls_done: break
                if walls_done: free_n += 0.5
                continue
            parts = []
            for z in zones:
                for st in z["stretches"]:
                    if st.get("full"): continue
                    for p in self.free_parts(st, pad=GROUP_PAD, least=1.6):
                        key = (p["run"]["line"], p["run"]["coord"], round(p["s0"], 1), round(p["s1"], 1))
                        if key not in failed: parts.append((p, st, key))
            if self.rtype in WALLS_ONLY and any(p[0]["back"] for p in parts):
                parts = [p for p in parts if p[0]["back"]]       # Westwood's stores: stock on two walls, the front bare
            corners = [c for z in zones for c in z["corners"].values()
                       if not self._corner_busy(c)]
            if not parts and not corners:
                if big and not walls_done:
                    self._walls_done = True
                    continue
                break
            if DEBUG: self.log.append(f"topup: {len(parts)} parts {[round(p[0]['L'], 1) for p in parts]} {len(corners)} corners")
            if parts and (not corners or self.rng.random() < 0.75):
                parts.sort(key=lambda ps: (not ps[0]["back"], -ps[0]["L"] * self.rng.uniform(0.6, 1.4)))
                part, st, key = parts[0]
                have = collections.Counter(OBJ.category(o["type"]) for o in self.objects)
                kinds = collections.Counter(OBJ.kind(o["type"]) for o in self.objects)
                lead_kind = lambda c: OBJ.kind(next((x["t"] for x in c["items"] if x["cat"] == self._lead_of(c)),
                                                    c["items"][0]["t"]))
                cands = [(w * (1 + c["n_block"]) * 0.3 ** have[self._lead_of(c)] * 0.6 ** kinds[lead_kind(c)] /
                          0.3 ** (have[self._lead_of(c)] if self._lead_of(c) in ("supply",) else 0) *
                          (0.5 if self._lead_of(c) == "shelf" else 1.0), c)
                         for w, c in self._slot_cands(None, None, "wall", back=part["back"], max_span=part["L"] - 0.2,
                                                      run=part["run"])
                         if c["n_block"] >= 1]
                got = None
                for _ in range(8):
                    c = self._choose(cands)
                    if not c: break
                    got = self._try_wall(c, [part])
                    if got: break
                    cands = [(w, x) for w, x in cands if x is not c]
                if not got: failed.add(key)
                continue
            corner = self.rng.choice(corners)
            cands = [(w, c) for w, c in self._slot_cands(None, None, "corner")]
            for _ in range(4):
                c = self._choose(cands)
                if not c: break
                mir = MIRROR[c["corner"]] == corner["name"] and c["corner"] != corner["name"]
                if c["corner"] != corner["name"] and not mir: w_ok = False
                else: w_ok = True
                if w_ok and self._try_corner(c, corner, mir): break
                cands = [(w, x) for w, x in cands if x is not c]
            corner["busy"] = True
        self.dress_gaps(zones)

    def dress_gaps(self, zones):
        """The lived-in details, at Westwood's rates: while the room is still under its cover, the small pieces Westwood's
        rooms of the type stand on their own in the gaps between the groups (a water barrel, an odd crate, a spittoon, a
        chest; a statue in a hall), from its own one-piece clusters, closer in than the groups keep (a step of floor)."""
        failed = set()
        stores = self.rtype in WALLS_ONLY          # a store heaps its stock: the pieces packed against each other
        pad = 0.05 if stores else 0.35
        for _ in range(DRESS_TRIES * (2 if stores else 1)):
            if self.coverage() >= self.cover_goal: break
            parts = [p for z in zones for st in z["stretches"] for p in self.free_parts(st, pad=pad, least=1.1)]
            parts = [p for p in parts if (p["run"]["coord"], round(p["s0"], 1)) not in failed]
            if not parts: break
            if stores:      # beside the stock already there (a heap grows), not out on a bare wall
                parts = [p for p in parts if p["back"]] or parts
                near = [p for p in parts if self._beside_stock(p)]
                parts = near or parts
            part = max(parts, key=lambda p: (p["back"], p["L"] * self.rng.uniform(0.5, 1.5)))
            have = collections.Counter(OBJ.kind(o["type"]) for o in self.objects)
            cands = [(w * 0.4 ** sum(have[OBJ.kind(x["t"])] for x in c["items"]) *
                      (2.0 if self._lead_of(c) in ("supply", "chest") else 1.0), c)
                     for w, c in self._slot_cands(None, None, "wall", back=part["back"], max_span=part["L"] - 0.1,
                                                  run=part["run"])
                     if c["n_block"] == 1 and len(c["items"]) <= 2 and self._lead_of(c) in DRESS]
            got = None
            for _ in range(5):
                c = self._choose(cands)
                if not c: break
                got = self._try_wall(c, [part])
                if got: break
                cands = [(w, x) for w, x in cands if x is not c]
            if not got: failed.add((part["run"]["coord"], round(part["s0"], 1)))
        # hangings on bare back wall, as many as Westwood's rooms of the type hang for their floor (a trophy, a
        # tapestry, a painting over no piece)
        rate = sum(1 for rid, w in self.pool.items() if w >= 1 for c in clusters_of(rid) if c["kind"] == "hang")
        rooms = sum(1 for rid, w in self.pool.items() if w >= 1) or 1
        want = rate / rooms * self.floor / ww_floor(self.rtype)
        n = int(want) + (self.rng.random() < want - int(want))
        n -= sum(1 for o in self.objects if OBJ.category(o["type"]) == "hanging")
        for _ in range(max(0, n)):
            parts = [p for z in zones for st in z["stretches"] if st["back"]
                     for p in self.free_parts(st, pad=0.3, least=2.2)]
            if not parts: break
            part = self.rng.choice(parts)
            cands = self._slot_cands(None, None, "hang", back=True, max_span=part["L"], run=part["run"])
            for _ in range(4):
                c = self._choose(cands)
                if not c or self._try_wall(c, [part]): break
                cands = [(w, x) for w, x in cands if x is not c]

    def _beside_stock(self, part):
        """Whether a free part of a wall starts or ends at a piece of stock standing against that wall."""
        r = part["run"]
        for a in (part["s0"], part["s1"]):
            for rec in self.g.placed:
                if not rec[4] or rec[5] == "wall": continue
                along, perp = (rec[1], rec[0]) if r["line"] == "/" else (rec[0], rec[1])
                ha, hp = (rec[3], rec[2]) if r["line"] == "/" else (rec[2], rec[3])
                if abs(perp - r["coord"]) - hp < 1.0 and abs(along - a) < ha + 0.5: return True
        return False

    def _why(self, p):
        t, u, v = p["t"], p["u"], p["v"]
        hu, hv = self.half(t)
        if self._capped(t): return "capped"
        if self.n_blocking >= self.cap: return "cap"
        if self.coverage(self.footprint(t)) > self.cover_max: return "cover_max"
        if not self._one_of_a_kind_ok(t, u, v): return "one-of-a-kind"
        before = dict(self.kb_refused)
        if not self._kb_ok(t, u, v, hu, hv, p["x"]["blocking"], "floor"):
            return "kb " + str({k: v - before.get(k, 0) for k, v in self.kb_refused.items() if v != before.get(k, 0)})
        pts = [(u + a * hu, v + b * hv) for a in (-1, 0, 1) for b in (-1, 0, 1)]
        if not all(self.g.inside(*q) for q in pts): return "outside"
        if min(self.g.wall_dist(*q) for q in pts) < 0.1: return "wall_dist"
        if not self.g.before_back_wall(u, v): return "behind wall"
        for du, dv in self.g.doors:
            if math.hypot(u - du, v - dv) < F.DOOR_CLEAR + max(hu, hv): return "door"
        for z in self.g.zones:
            if u + hu > z[0] and u - hu < z[1] and v + hv > z[2] and v - hv < z[3]: return f"zone {[round(q,1) for q in z]}"
        if not self.g.fits(u, v, hu, hv, True, False, wall_min=0.1, touch=True): return "overlap"
        if not self.g.reachable_ok((u, v, hu, hv, True, "floor")): return "reach"
        return "?"

    def _corner_busy(self, c):
        if c.get("busy"): return True
        cu, cv = c["a"]["coord"] + c["a"]["sign"] * 1.5, c["b"]["coord"] + c["b"]["sign"] * 1.5
        return any(abs(rec[0] - cu) < 1.8 + rec[2] and abs(rec[1] - cv) < 1.8 + rec[3] for rec in self.g.placed
                   if rec[5] != "wall")

    def repair_clusters(self, zones):
        """The type's must pieces still missing: clusters that hold them, on free parts of the walls; the recipe's own
        placement as the last resort."""
        must = self.prof.get("must", {})
        for fam, n in must.items():
            for attempt in range(5):
                if self._count_fam(fam) >= n: break
                has = lambda c: any(F._family_of(x["t"]) == fam for x in c["items"])
                parts = [p for z in zones for st in z["stretches"] for p in self.free_parts(st, pad=GROUP_PAD,
                                                                                           least=1.6)]
                parts.sort(key=lambda p: (not p["back"], -p["L"]))
                done = False
                for part in parts[:4]:
                    cands = [(w, c) for w, c in self._slot_cands(None, None, "wall", back=part["back"],
                                                                 max_span=part["L"] - 0.1, run=part["run"]) if has(c)]
                    for _ in range(3):
                        c = self._choose(cands)
                        if not c: break
                        if self._try_wall(c, [part]): done = True; break
                        cands = [(w, x) for w, x in cands if x is not c]
                    if done: break
                if not done:
                    for z in zones:
                        for name, corner in z["corners"].items():
                            cands = [(w, c) for w, c in self._slot_cands(None, None, "corner") if has(c)]
                            c = self._choose(cands)
                            if c and self._try_corner(c, corner, c["corner"] != name):
                                done = True; break
                        if done: break
                if not done:
                    if fam in F.WALL_ONLY or fam in ("storage", "stove", "fireplace", "bed", "desk", "lab"):
                        res = self.place_on_wall(fam, at=self.rng.choice(["center", "corner"]))
                    else:
                        res = self.place_center(fam)
                    if res: self.log.append(f"repair {fam}: recipe placement")
                    else: break

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
        if COMPOSE == "clusters": self.compose_clusters()
        else: self.compose_room()
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
