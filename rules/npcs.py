"""How Westwood places and moves its creatures and NPCs (single-player maps, each layout once).

For every creature (MonsterXfer / NPCXfer):
- its default action (ai.ActionType: 0 idle, 3 escort, 4 guard, 5 hunt, 10 roam, ...), sight range, aggressiveness,
  retreat and resume ratios, roam-path flags, status flags, scripted events, escort target;
- where it stands: in a room (enclosed) or outdoors, its distance to the nearest wall, door, waypoint and the player
  start, the floor under it;
- its group: creatures of the same type within 4 cells (about 92 px) of each other form a group.
For every map's waypoints: count, flags, link degrees, spacing of linked waypoints, loops; which waypoints are near
roaming creatures.

Writes rules/out/npcs.json and prints a summary.
    py rules/npcs.py
"""
import collections, json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, "validate"))
import mapdata as md
from biomes import layout_key

ACTIONS = {0: "idle", 1: "wait", 2: "wait_relative", 3: "escort", 4: "guard", 5: "hunt", 6: "retreat", 7: "move_to",
           8: "far_move_to", 9: "dodge", 10: "roam", 24: "flee", 29: "random_walk", 37: "move_to_home"}
EVENTS = ["enemy_sighted", "looking_for_enemy", "death", "change_focus", "is_hit", "retreat", "collision",
          "enemy_heard", "end_of_waypoint", "lost_enemy"]
SKIP = re.compile(r"Generator|Shopkeeper|^NPC$|Wounded|Maiden|Glyph|Bomber")


def wq(vals):
    s = sorted(vals)
    if not s: return None
    return {f"p{p}": round(s[min(len(s) - 1, int(p / 100 * len(s)))], 2) for p in (10, 25, 50, 75, 90)}


def one(name):
    import checks as C
    m = md.load(md.corpus_json(name))
    rooms = C.find_rooms(m)
    cell_room = {}
    for k, r in enumerate(rooms):
        for c in r["cells"]: cell_room[c] = k
    walls = list(m.walls)
    wall_set = set(m.walls)
    doors = [(d["gap"][0] * 23 + 11.5, d["gap"][1] * 23 + 11.5) for d in m.doors]
    wps = m.waypoints
    starts = [(o["x"], o["y"]) for o in m.objects if o["type"] == "PlayerStart"]
    mons = []
    for o in m.objects:
        if o["xtype"] not in ("MonsterXfer", "NPCXfer") and "MONSTER" not in o["cls"]: continue
        x = o["xfer"] or {}
        cell = m.cell_of(o["x"], o["y"])
        # distance to the nearest wall cell (cells), searching outward
        dw = None
        for rad in range(0, 12):
            if any((cell[0] + a, cell[1] + b) in wall_set for a in range(-rad, rad + 1) for b in range(-rad, rad + 1)
                   if max(abs(a), abs(b)) == rad):
                dw = rad; break
        nearest = lambda pts: min((math.hypot(o["x"] - px, o["y"] - py) / 23 for px, py in pts), default=None)
        ev = x.get("ScriptEvents") or []
        mons.append(dict(type=o["type"], xtype=o["xtype"], x=o["x"], y=o["y"],
                         action=x.get("DefaultAction"), sight=x.get("SightRange"), aggr=x.get("Aggressiveness"),
                         retreat=x.get("RetreatRatio"), resume=x.get("ResumeRatio"), roamflag=x.get("ActionRoamPathFlag"),
                         status=x.get("StatusFlags"), escort=x.get("EscortObjName") or "", immortal=x.get("Immortal"),
                         events=[EVENTS[i] for i, e in enumerate(ev[:10]) if e], scr=o.get("scr") or "",
                         room=cell in cell_room, wall=dw, door=nearest(doors), start=nearest(starts),
                         wp=nearest([(w["x"], w["y"]) for w in wps]), floor=m.floor_at(o["x"], o["y"]),
                         spells=len(x.get("KnownSpells") or [])))
    # waypoint graph
    byn = {w["n"]: w for w in wps}
    deg = collections.Counter()
    lens = []
    for w in wps:
        for l in w.get("links") or []:
            t = l[0] if isinstance(l, (list, tuple)) else l.get("n") if isinstance(l, dict) else l
            if t in byn:
                deg[w["n"]] += 1
                lens.append(math.hypot(w["x"] - byn[t]["x"], w["y"] - byn[t]["y"]) / 23)
    return name, dict(tiles=len(m.tiles), mons=mons, n_wp=len(wps), wp_flags=collections.Counter(w.get("flags") for w in wps),
                      wp_named=sum(1 for w in wps if w.get("name") and not re.search(r":\d*$", w["name"])),
                      wp_deg=collections.Counter(deg[w["n"]] for w in wps), wp_link_len=lens,
                      script_funcs=len(m.script_funcs))


def groups(mons, radius=4.0):
    """Sizes of groups of the same creature type standing within `radius` cells of each other."""
    sizes = []
    by = collections.defaultdict(list)
    for i, c in enumerate(mons): by[c["type"]].append(i)
    for t, idx in by.items():
        left = set(idx)
        while left:
            a = left.pop(); comp = [a]; q = [a]
            while q:
                p = q.pop()
                for b in list(left):
                    if math.hypot(mons[p]["x"] - mons[b]["x"], mons[p]["y"] - mons[b]["y"]) / 23 <= radius:
                        left.remove(b); comp.append(b); q.append(b)
            sizes.append((t, len(comp)))
    return sizes


def main():
    env = json.load(open(os.path.join(HERE, "out", "environments.json")))["maps"]
    names = [n for n, _ in md.sp_corpus_maps()]
    seen, chosen = set(), []
    for n in sorted(names):
        k = layout_key(n)
        if k in seen: continue
        seen.add(k); chosen.append(n)
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(6) as pool:
        data = dict(pool.map(one, chosen))
    allm = [dict(c, map=n, env=env.get(n, {}).get("type")) for n, d in data.items() for c in d["mons"]]
    hostile = [c for c in allm if not SKIP.search(c["type"]) and c["xtype"] == "MonsterXfer"]
    out = {}
    out["n_creatures"] = len(allm); out["n_hostile"] = len(hostile)
    out["actions"] = collections.Counter(ACTIONS.get(c["action"], c["action"]) for c in hostile).most_common()
    out["actions_by_type"] = {}
    for t, n in collections.Counter(c["type"] for c in hostile).most_common(40):
        cs = [c for c in hostile if c["type"] == t]
        out["actions_by_type"][t] = dict(n=n, actions=collections.Counter(ACTIONS.get(c["action"], c["action"]) for c in cs).most_common(4),
                                         sight=wq([c["sight"] for c in cs if c["sight"] is not None]),
                                         aggr=wq([c["aggr"] for c in cs if c["aggr"] is not None]),
                                         in_room=round(sum(c["room"] for c in cs) / n, 2),
                                         scripted=round(sum(1 for c in cs if c["events"] or c["scr"]) / n, 2))
    out["events"] = collections.Counter(e for c in hostile for e in c["events"]).most_common()
    out["scripted_share"] = round(sum(1 for c in hostile if c["events"] or c["scr"]) / max(1, len(hostile)), 3)
    out["escorts"] = sum(1 for c in allm if c["escort"])
    out["roam_flags"] = collections.Counter(c["roamflag"] for c in hostile if c["action"] == 10).most_common()
    out["status"] = collections.Counter(c["status"] for c in hostile).most_common(12)
    for key in ("wall", "door", "start", "wp"):
        out[f"dist_{key}"] = {a: wq([c[key] for c in hostile if ACTIONS.get(c["action"]) == a and c[key] is not None])
                              for a in ("guard", "roam", "idle", "hunt", "escort")}
    out["roamers_near_waypoint"] = round(sum(1 for c in hostile if c["action"] == 10 and c["wp"] is not None and c["wp"] < 8) /
                                         max(1, sum(1 for c in hostile if c["action"] == 10)), 2)
    gs = groups(hostile)
    out["group_sizes"] = wq([s for _, s in gs])
    out["group_size_by_type"] = {t: wq([s for tt, s in gs if tt == t]) for t, _ in collections.Counter(c["type"] for c in hostile).most_common(25)}
    out["by_env"] = {}
    for e in ("town", "forest", "swamp", "cave", "dungeon", "castle", "ice", "lava"):
        ns = [n for n in chosen if env.get(n, {}).get("type") == e]
        tiles = sum(data[n]["tiles"] for n in ns) or 1
        hs = [c for c in hostile if c["env"] == e]
        out["by_env"][e] = dict(maps=len(ns), per100=round(100 * len(hs) / tiles, 2),
                                in_rooms=round(sum(c["room"] for c in hs) / max(1, len(hs)), 2),
                                actions=collections.Counter(ACTIONS.get(c["action"], c["action"]) for c in hs).most_common(4),
                                types=collections.Counter(c["type"] for c in hs).most_common(8),
                                start_dist=wq([c["start"] for c in hs if c["start"] is not None]))
    out["waypoints"] = dict(per_map=wq([d["n_wp"] for d in data.values()]),
                            per100_tiles=wq([100 * d["n_wp"] / max(1, d["tiles"]) for d in data.values()]),
                            flags=sum((d["wp_flags"] for d in data.values()), collections.Counter()).most_common(8),
                            degree=sum((d["wp_deg"] for d in data.values()), collections.Counter()).most_common(8),
                            link_len=wq([l for d in data.values() for l in d["wp_link_len"]]),
                            named_share=round(sum(d["wp_named"] for d in data.values()) / max(1, sum(d["n_wp"] for d in data.values())), 2))
    with open(os.path.join(HERE, "out", "npcs.json"), "w") as f: json.dump(out, f, indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if k not in ("actions_by_type", "group_size_by_type", "dist_wp")}, indent=1, default=str)[:9000])
    print("\nby type:")
    for t, d in out["actions_by_type"].items():
        print(f"  {t:18s} n={d['n']:4d} {d['actions']} sight={d['sight'] and d['sight']['p50']} aggr={d['aggr'] and d['aggr']['p50']} "
              f"room={d['in_room']} scripted={d['scripted']} group={out['group_size_by_type'].get(t)}")


if __name__ == "__main__":
    main()
