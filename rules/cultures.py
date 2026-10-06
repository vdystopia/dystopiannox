"""The furnishing of Westwood's culture rooms: the Land of the Dead's temples (LOTD objects), the ogres' lairs (Ogre
objects) and Dun Mir's halls (DunMir objects), measured room by room in the campaign maps (each layout once).

A room (validate/checks.py find_rooms) belongs to a culture when at least two of its pieces carry the culture's prefix.
For each culture: how many rooms, their size, their wall materials and floors; for each object type that stands in
them, the share of rooms holding it, its count per 100 floor tiles where present, and where it stands (against a wall
- the NE and NW walls the camera sees, or the SE and SW walls - or free in the room).

Writes rules/out/cultures.json and prints a summary.
    py rules/cultures.py
"""
import collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, "validate"))
import mapdata as md
from biomes import layout_key

CULTURES = {"lotd": r"^LOTD", "ogre": r"^Ogre", "dunmir": r"^DunMir"}
SKIP = re.compile(r"Shadow|Door|Elevator|Stairs|Switch|Facade|Rocks|MileStone|Generator|^OgreBrute$|^OgreWarlord$")


def wq(vals):
    s = sorted(vals)
    if not s: return None
    return {f"p{p}": round(s[min(len(s) - 1, int(p / 100 * len(s)))], 2) for p in (10, 25, 50, 75, 90)}


def rooms_of(name):
    import checks as C
    m = md.load(md.corpus_json(name))
    out = []
    for r in C.find_rooms(m):
        objs = [o for o in r["objects"] if not SKIP.search(o["type"])]
        cult = {c: sum(1 for o in objs if re.match(p, o["type"])) for c, p in CULTURES.items()}
        c, n = max(cult.items(), key=lambda kv: kv[1])
        if n < 2: continue
        cells = r["cells"]
        cu = sum(x + y + 1 for x, y in cells) / len(cells); cv = sum(x - y for x, y in cells) / len(cells)
        runs = C.room_runs(m, cells)
        walls = collections.Counter(m.walls[p].material for p in
                                    {(x + a, y + b) for x, y in cells for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))}
                                    if p in m.walls)
        floors = collections.Counter((m.tiles[p] or {}).get("material") if isinstance(m.tiles[p], dict) else str(m.tiles[p])
                                     for p in cells if p in m.tiles)
        pieces = []
        for o in objs:
            hit = C._against(o, runs, cu, cv, m, reach=1.6, across=True)
            pieces.append((o["type"], hit[0] if hit else "free"))
        out.append(dict(map=name, culture=c, tiles=r["tiles"], walls=dict(walls), floors=dict(floors), pieces=pieces))
    return out


def main():
    import sqlite3
    db = sqlite3.connect(os.path.join(REPO, "corpus", "out", "nox_corpus.db"))
    import common
    sp = set(common.campaign_maps())                 # campaign maps only (Con/War/Wiz); maps.type is a number, so the
                                                     # old filter "type != 'multiplayer'" let every map through
    has = {n for (n,) in db.execute("SELECT DISTINCT map FROM objects WHERE type LIKE 'LOTD%' OR type LIKE 'Ogre%' "
                                    "OR type LIKE 'DunMir%'")}
    seen, rooms = set(), []
    for n in sorted(has):
        if n not in sp: continue
        key = layout_key(n)
        if key in seen: continue
        seen.add(key)
        try:
            rooms += rooms_of(n)
        except Exception as e:                       # a map the exporter cannot read: skip it, say so
            print(f"  {n}: {e}")
    out = {}
    for c in CULTURES:
        rs = [r for r in rooms if r["culture"] == c]
        if not rs: continue
        per = collections.defaultdict(list)          # type -> [(count, tiles)] over the rooms holding it
        where = collections.defaultdict(collections.Counter)
        for r in rs:
            cnt = collections.Counter(t for t, _ in r["pieces"])
            for t, k in cnt.items(): per[t].append((k, r["tiles"]))
            for t, w in r["pieces"]: where[t]["back" if w in ("NE", "NW") else "front" if w in ("SE", "SW") else "free"] += 1
        types = {}
        for t, lst in sorted(per.items(), key=lambda kv: -len(kv[1])):
            if len(lst) < 2: continue
            tot = sum(where[t].values())
            types[t] = dict(rooms=round(len(lst) / len(rs), 3), per100=wq([100 * k / max(1, n) for k, n in lst]),
                            where={k: round(v / tot, 2) for k, v in where[t].items()})
        walls = collections.Counter(); floors = collections.Counter()
        for r in rs:
            walls.update(r["walls"]); floors.update(r["floors"])
        tw, tf = sum(walls.values()) or 1, sum(floors.values()) or 1
        out[c] = dict(rooms=len(rs), maps=sorted({r["map"] for r in rs}), tiles=wq([r["tiles"] for r in rs]),
                      walls={k: round(v / tw, 3) for k, v in walls.most_common(8)},
                      floors={k: round(v / tf, 3) for k, v in floors.most_common(10)}, types=types)
        print(f"== {c}: {len(rs)} rooms in {len(out[c]['maps'])} maps, tiles {out[c]['tiles']}")
        print(f"   walls {out[c]['walls']}")
        print(f"   floors {out[c]['floors']}")
        for t, v in list(types.items())[:30]:
            print(f"   {t:28s} in {v['rooms']:.0%} of rooms, per 100 tiles {v['per100']['p50']}, {v['where']}")
    with open(os.path.join(HERE, "out", "cultures.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
