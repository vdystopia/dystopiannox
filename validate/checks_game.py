"""In-game behaviour checks (QA round 1, 2026-10-13: the user's screenshots and set notes): signs that read, wells that
heal, fish that swim, people who stand clear of doors with their backs to the walls and keepers by their counters,
and items with a name, a description, a price and a use. checks.py imports this at its end and adds RULES and ALL.

Severity: errors on generated maps (a .loot.json, _scripts or .routes.json beside the map, or built under mapgen);
on Westwood's maps the same findings are notes, for calibration (validate/calibrate.py, checkcheck.py).
"""
import json, math, os, re, sys
import mapdata as md

sys.path.insert(0, os.path.join(md.REPO, "mapgen"))

WELL_RE = re.compile(r"^(Well|WishingWell)$")
FISH_RE = re.compile(r"^Fish(Small|Big)$")
FISH_REACH = 250.0        # px: a fish's nearest linked waypoint in sight (Westwood: 239 of 240 campaign fish)
PERSON_DOOR = 40.0        # px from a door's middle no one stands (the kit keeps 46: kit/story.py PERSON_DOOR)
DOOR_CROWD = 70.0         # px round a door's middle: two people standing here crowd its entrance
FACE_CLOSE = 60.0         # px: a door this near straight ahead (within 35 degrees) is faced


def F(*a, **k):
    import checks
    return checks.F(*a, **k)


def generated(m):
    f = (m.file or "").replace("\\", "/")
    if not f: return False
    base = os.path.splitext(f)[0]
    return "mapgen" in f.lower() or any(os.path.exists(base + s) for s in (".loot.json", "_scripts", ".routes.json"))


def map_strings(m):
    """{key lower: text}: the map's own string table (<map>.strings.json beside it) over the game's (nox.csf, with
    kit/items.py's item names)."""
    from kit.items import _table
    out = dict(_table())
    side = os.path.splitext(m.file or "")[0] + ".strings.json"
    if m.file and os.path.exists(side):
        for k, v in json.load(open(side, encoding="utf-8")).items(): out[k.lower()] = v
    return out


# ---- signs (nox1, nox10; ModLab M2) --------------------------------------------------------------------------------
def check_signs(m, ctx, base):
    """Every sign reads on one line, short enough for the client, and is a small sign: the client prints "The sign
    reads: <text>" on one line, dropping line breaks (nox1: "THE OLD BRIDGETo the mill."), into a 256-character buffer
    (ModLab's M2 sign, 274 characters, crashed the game); the tall plank boards "do not look good. Use the smaller
    ones instead, always" (kit/signs.py)."""
    from kit.signs import LARGE, problem
    out, gen = [], generated(m)
    readable = [o for o in m.objects if "READABLE" in o["cls"]]
    if not readable: return out
    table = map_strings(m)
    for o in readable:
        if LARGE.match(o["type"]):
            out.append(F("signs", "error" if gen else "info", f"{o['type']} is a tall plank sign: the kit stands the "
                         f"small signs (Sign1, Sign2), never the plank boards (kit/signs.py).", o["x"], o["y"]))
        key = (o["xfer"] or {}).get("Text") or ""
        pr = problem(table.get(key.lower()) if key else "")
        if pr:
            sev = pr[0] if gen else "info"
            out.append(F("signs", sev, f"The sign {o['type']} ({key or 'no text'}) {pr[1]} (kit/signs.py).", o["x"], o["y"]))
    return out


# ---- wells (nox13 and the well set's note) -------------------------------------------------------------------------
def check_wells(m, ctx, base):
    """Every well heals the player, as Westwood's do (its WishingWell runs MakeAWish on being pressed; the kit's
    wells.go restores health and mana at every well it lists: kit/wells.py)."""
    from kit.wells import covered
    wells = [o for o in m.objects if WELL_RE.match(o["type"])]
    if not wells: return []
    gen = generated(m)
    src = ""
    sd = os.path.splitext(m.file or "")[0] + "_scripts"
    if os.path.isdir(sd) and os.path.exists(os.path.join(sd, "wells.go")):
        src = open(os.path.join(sd, "wells.go"), encoding="utf-8").read()
    pts = covered(src)
    out = []
    for o in wells:
        if any(math.hypot(o["x"] - x, o["y"] - y) < 3 for x, y in pts): continue
        if o["type"] == "WishingWell" and ((o["xfer"] or {}).get("ScriptOnPressed") or ""): continue
        out.append(F("wells", "error" if gen else "info", f"The {o['type']} does not heal: no script restores the "
                     f"player who drinks at it (kit/wells.py writes wells.go with every well's spot).", o["x"], o["y"]))
    return out


# ---- fish (nox4) ---------------------------------------------------------------------------------------------------
def check_fish(m, ctx, base):
    """Every fish has a linked waypoint in sight within FISH_REACH px to swim to: the game's roam gives up without one
    and the fish stand still until the player frightens them (kit/npcs.py Population.fish)."""
    fish = [o for o in m.objects if FISH_RE.match(o["type"])]
    if not fish: return []
    by_n = {w.get("n"): w for w in m.waypoints}
    linked = set()
    for w in m.waypoints:
        for l in w.get("links") or []:
            n = l if isinstance(l, int) else l.get("n") if isinstance(l, dict) else l[0] if l else None   # [n, flag]
            if n in by_n: linked.add(id(w)); linked.add(id(by_n[n]))
    wps = [w for w in m.waypoints if id(w) in linked]
    gen = generated(m)

    def sight(a, b):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        for k in range(1, int(d // 8) + 1):
            x, y = a[0] + (b[0] - a[0]) * k * 8 / d, a[1] + (b[1] - a[1]) * k * 8 / d
            if m.cell_of(x, y) in m.walls: return False
        return True
    out = []
    for o in fish:
        if any(math.hypot(w["x"] - o["x"], w["y"] - o["y"]) <= FISH_REACH and sight((o["x"], o["y"]), (w["x"], w["y"]))
               for w in wps):
            continue
        out.append(F("fish", "error" if gen else "info", f"The {o['type']} has no linked waypoint within "
                     f"{FISH_REACH:.0f} px to swim to: it will stand still until the player comes near "
                     f"(Population.fish lays the loop).", o["x"], o["y"]))
    return out


# ---- people at doors, walls and counters (nox9, nox10, nox14, nox18) ----------------------------------------------
def _doors(g):
    return sorted({v[0]: v for v in g.gap_door.values()}.values())


def _in_door(p, doors):
    for (cx, cy), (nx, ny), half in doors:
        dx, dy = p[0] - cx, p[1] - cy
        if math.hypot(dx, dy) < PERSON_DOOR: return (cx, cy)
        if abs(dx * nx + dy * ny) < 40 and abs(-dx * ny + dy * nx) < half: return (cx, cy)
    return None


TENDED = re.compile(r"^(Anvil|DunMirAltar|LOTDLichGodStatue|TraderDesk|Desk\d|AlchemistDesk|Bar|Cauldron|Forge|"
                    r"Telescope|Well$|WishingWell|Fountain|Statue|Throne|DunMirThrone|Stove|Fireplace|Table)")
DIR_DEG = {0: -90, 1: 90, 2: 0, 3: -135, 4: 135, 5: 180, 6: -45, 7: 45}


def check_people(m, ctx, base):
    """People stand clear of doors and face open ground: nobody standing still, and no stop of a route, in a doorway
    or within PERSON_DOOR px of a door's middle (nox10: one "stuck in the frame of the door"); no two at one door
    (nox10: "clustered at the entrance of a door"); nobody standing still faces a door, a wall or a building close
    ahead, and one beside a wall has his back to it (nox9, nox10: "facing the door ... He should be facing away from
    the building with his back to the wall"). Keepers by their counters: checks.py identity.keeper (nox18)."""
    from kit.walkways import Ground, facing_problem, wall_away, NEAR_WALL, AWAY_SLACK
    side = os.path.splitext(m.file or "")[0] + ".routes.json"
    routes = json.load(open(side, encoding="utf-8")) if m.file and os.path.exists(side) else []
    walkers = {r.get("who") for r in routes}
    people = [o for o in m.objects if "MONSTER" in o["cls"] and (o.get("scr") or "").split(":")[-1] not in walkers
              and not ((o["xfer"] or {}).get("ShopkeeperInfo") or {}).get("ShopItems")
              and (o["type"] in ("NPC", "Maiden") or (o["xfer"] or {}).get("Aggressiveness", 1) < 0.1)]
    by_name = {(w.get("name") or "").split(":")[-1]: w for w in m.waypoints}
    stops = []
    for r in routes:
        for k, n in enumerate(r.get("waypoints") or []):
            w = by_name.get(n)
            if w is not None and k < len(r.get("pauses") or []) and r["pauses"][k] > 0:
                stops.append((w, r.get("who", "?"), r.get("kind")))
    if not people and not stops: return []
    gen = generated(m)
    sev = lambda s: s if gen else "info"
    g = Ground.from_mapdata(m)
    doors = _doors(g)
    out = []
    who = lambda o: (o.get("scr") or o["type"]).split(":")[-1]
    at_door = {}
    for o in people:
        d = _in_door((o["x"], o["y"]), doors)
        if d:
            out.append(F("people", sev("error"), f"{who(o)} stands in a doorway, {math.dist(d, (o['x'], o['y'])):.0f} px "
                         f"from the door's middle: a person waits beside a door, never in it or in its way "
                         f"(StoryMap.doorside, settle_people).", o["x"], o["y"]))
    for w, name, _ in stops:
        d = _in_door((w["x"], w["y"]), doors)
        if d:
            out.append(F("people", sev("error"), f"{name}'s stop {(w.get('name') or '').split(':')[-1]} stands in a "
                         f"doorway, {math.dist(d, (w['x'], w['y'])):.0f} px from the door's middle: a stop stands "
                         f"beside a doorstep, never in front of the door (StoryMap._spots).", w["x"], w["y"]))
    # crowding: the people who stand at each door
    for (c, n, half) in doors:
        still = {who(o) for o in people if math.dist(c, (o["x"], o["y"])) < DOOR_CROWD}
        # (a journey's end at a door is a homecoming: the rescued boy walks home to his mother waiting there)
        near = still | {name for w, name, kind in stops if kind != "journey" and math.dist(c, (w["x"], w["y"])) < DOOR_CROWD}
        # someone waits at the door and another comes to stand there, or three walkers' stops share it
        if (still and len(near) >= 2) or len(near) >= 3:
            out.append(F("people", sev("warning"), f"{len(near)} people stand at one door ({', '.join(sorted(near))}): "
                         f"a door someone waits at is nobody else's stop (StoryMap._town).", c[0], c[1]))
    # facing: the people standing still and friendly
    for o in people:
        xf = o["xfer"] or {}
        if xf.get("Aggressiveness", 1) >= 0.1 or xf.get("DirectionId") is None: continue
        p = (o["x"], o["y"])
        a = math.radians(DIR_DEG.get(int(xf["DirectionId"]), 0))
        look = (p[0] + 240 * math.cos(a), p[1] + 240 * math.sin(a))
        why = facing_problem(g, p, look)
        if why and "obstacle" in why:                # a piece he works at or tends (an anvil, an altar) is faced
            mm = re.search(r"at \((-?\d+), (-?\d+)\)", why)
            q = mm and (float(mm.group(1)), float(mm.group(2)))
            if q and any(TENDED.match(t["type"]) and math.dist((t["x"], t["y"]), q) < 4 for t in m.objects): why = None
        if not why:
            for c, n, half in doors:
                dd = math.dist(c, p)
                off = abs((math.atan2(c[1] - p[1], c[0] - p[0]) - a + math.pi) % (2 * math.pi) - math.pi)
                if dd < FACE_CLOSE and math.degrees(off) < 35:
                    why = f"faces a door {dd:.0f} px ahead"
                    break
        if not why:
            away = wall_away(g, p)
            if away is not None and math.degrees(abs((a - away + math.pi) % (2 * math.pi) - math.pi)) > AWAY_SLACK + 23:
                why = f"stands within {NEAR_WALL:.0f} px of a wall without his back to it"
        if why:
            out.append(F("people", sev("warning"), f"{who(o)} {why}: a person standing still faces open ground, his "
                         f"back to the wall beside him (StoryMap.settle_people).", p[0], p[1]))
    return out


# ---- items (nox12, nox19) ------------------------------------------------------------------------------------------
def check_items(m, ctx, base):
    """Every item placed, held in a container or sold has a name; every ware a description, a price, a use and a price
    in Westwood's range for the act's chapter; a spell book placed teaches a spell (kit/items.py)."""
    from kit import items as I
    gen = generated(m)
    act = I.act_of(m.name)
    tag = re.search(r"\[act:(\d+)\]", str((m.info or {}).get("description", "")))
    act = act or (int(tag.group(1)) if tag else None)          # a test map names its act
    out, seen = [], set()

    def add(t, where, o, sold=False, spell=None):
        for sv, why in I.problems(t, sold=sold, act=act if sold else None, spell="?" if spell is None else spell,
                                  buy=((o["xfer"] or {}).get("ShopkeeperInfo") or {}).get("BuyValueMultiplier") or 1.0):
            if (t, why) in seen: continue
            seen.add((t, why))
            out.append(F("items", sv if gen else "info", f"{t} ({where}) {why} (kit/items.py).", o["x"], o["y"]))
    for o in m.objects:
        info = (o["xfer"] or {}).get("ShopkeeperInfo") or {}
        for s in info.get("ShopItems") or []:
            # (the export writes a ware as "x2 SpellBook", without its SpellID: Population.shopkeeper checks the spell)
            t = str(s).split(" ", 1)[-1] if isinstance(s, str) else s.get("Name")
            add(t, f"sold by {o.get('scr') or o['type']}", o, sold=True, spell=None if isinstance(s, str) else s.get("SpellID"))
        if o["type"] in I.FACTS and "MONSTER" not in o["cls"]:
            add(o["type"], "placed", o)
            if I.SPELL_BOOKS.search(o["type"]) and (o["xfer"] or {}).get("SpellName", "SPELL_INVALID") in ("", "SPELL_INVALID"):
                out.append(F("items", "error" if gen else "info", f"{o['type']} (placed) teaches no spell: set its "
                             f"SpellName (kit/items.py).", o["x"], o["y"]))
        for it in o.get("inv") or []:
            if it["type"] in I.FACTS: add(it["type"], f"in {o['type']}", o)
    return out


RULES = [
    ("signs.large", "signs", r"is a tall plank sign", "Q1G-2"),
    ("signs.text", "signs", r"^The sign ", "Q1G-1 Q1G-8"),
    ("wells.heal", "wells", r"does not heal", "Q1G-3"),
    ("fish.swim", "fish", r"no linked waypoint", "Q1G-4"),
    ("people.doorway", "people", r"in a doorway", "Q1G-5"),
    ("people.crowd", "people", r"people stand at one door", "Q1G-5"),
    ("people.facing", "people", r"faces open ground", "Q1G-5"),
    ("items.name", "items", r"has no name|is no item", "Q1G-7"),
    ("items.ware", "items", r"has no description|has no price|does nothing|spell book with no spell|teaches no spell", "Q1G-7"),
    ("items.price", "items", r"over \d+, the dearest", "Q1G-7"),
]
ALL = [check_signs, check_wells, check_fish, check_people, check_items]
