"""Door construction rules: single vs double doors, opening width, hinge positions, and how the
wall pieces beside an opening are shaped. Writes rules/out/doors.json and rules/sections/doors.md.

Findings this encodes (single-player maps, layout-weighted):
- Single doors (ArchedDoor, WoodenDoor, DunMirDoor, ...) fill a 1-cell opening.
- Some types are double in one wall direction and single in the other: BandedPlankDoor pairs only
  in '/' walls; in '\' walls Westwood always hangs it alone (its '\' halves do not line up as a
  pair). types[t].by_line[line].kind gives the kind for each wall direction.
- Double doors (all *HalfDoor types, Gate, CryptDoor, CryptGate, ...) are two door objects hinged
  at opposite ends of a 2-cell opening ('/' walls: East + West; '\\' walls: North + South).
- Wall pieces next to an opening are shaped as if the opening were wall (a T beside a door stays
  a T, a corner stays a corner); computing them without the opening leaves visible gaps.
"""
import collections, sys
import common as c

DIRS = {"South": ((-1, -1), (1, 1)), "North": ((0, 0), (1, 1)), "East": ((-1, 0), (1, -1)), "West": ((0, -1), (1, -1))}


def main():
    sys.path.insert(0, c.os.path.join(c.REPO, "mapgen"))
    from nox import FACING_BY_ARMS, TL, TR, BL, BR
    width = collections.defaultdict(collections.Counter)
    width_line = collections.defaultdict(collections.Counter)     # (type, '/' or '\') -> opening widths
    maps_of = collections.defaultdict(set)
    jamb = collections.Counter()
    for m in c.sp_maps():
        W = c.walls(m); w = c.sp_weights()[m]
        gaps = set()
        for o in c.objects(m):
            if o["xtype"] != "DoorXfer" or o["xfer"].get("Direction") not in DIRS: continue
            cx, cy = round(o["x"] / c.CELL), round(o["y"] / c.CELL)
            (ox, oy), (sx, sy) = DIRS[o["xfer"]["Direction"]]
            g = (cx + ox, cy + oy)
            if g in W: continue
            gaps.add(g)
            prev, nxt = (g[0] - sx, g[1] - sy) not in W, (g[0] + sx, g[1] + sy) not in W
            wd = 2 if prev != nxt else 1 if not (prev or nxt) else 3
            width[o["type"]][wd] += w
            width_line[(o["type"], "\\" if o["xfer"]["Direction"] in ("North", "South") else "/")][wd] += w
            maps_of[o["type"]].add(m)
        for g in gaps:
            for a in (TL, TR, BL, BR):
                q = (g[0] + a[0], g[1] + a[1])
                if q not in W or W[q]["facing"] == 2: continue

                def facing(extra):
                    return FACING_BY_ARMS.get(frozenset(b for b in (TL, TR, BL, BR)
                                                        if (q[0] + b[0], q[1] + b[1]) in W or (q[0] + b[0], q[1] + b[1]) in extra))
                plain, withgap = facing(set()), facing(gaps)
                key = "same" if plain == withgap else "gap_as_wall" if W[q]["facing"] == withgap else \
                      "gap_as_empty" if W[q]["facing"] == plain else "neither"
                jamb[key] += w
    types = {}
    for t, cnt in width.items():
        tot = sum(cnt.values())
        two = cnt[2] / tot
        by_line = {}
        for line in ("/", "\\"):
            cl = width_line.get((t, line))
            if not cl: continue
            lt = sum(cl.values())
            by_line[line] = dict(share_two_cell=round(cl[2] / lt, 3), share_one_cell=round(cl[1] / lt, 3), weighted_count=round(lt, 1),
                                 kind="double" if cl[2] / lt >= 0.5 else "single")
        types[t] = dict(kind="double" if two >= 0.5 else "single", share_two_cell=round(two, 3),
                        share_one_cell=round(cnt[1] / tot, 3), weighted_count=round(tot, 1), maps=len(maps_of[t]),
                        by_line=by_line)
    jt = sum(jamb.values())
    rules = dict(
        types=types,
        double_placement={"/": "2-cell opening a, b=a+(1,-1): East door at corner (b.x+1, b.y), West door at corner (a.x, a.y+1)",
                          "\\": "2-cell opening a, b=a+(1,1): North door at corner (a.x, a.y), South door at corner (b.x+1, b.y+1)"},
        single_placement={"/": "1-cell opening g: East at (g.x+1, g.y) or West at (g.x, g.y+1)",
                          "\\": "1-cell opening g: South at (g.x+1, g.y+1) or North at (g.x, g.y)"},
        jamb_facing=dict(rule="compute wall facings treating door openings as wall",
                         shares={k: round(v / jt, 3) for k, v in jamb.items()}),
    )
    c.save_json("doors.json", rules)
    lines = ["# Doors", "", "Schema (`rules/out/doors.json`): `types[name] = {kind: single|double, share_two_cell, "
             "share_one_cell, weighted_count, maps}`; `double_placement` / `single_placement` (hinge corners per wall "
             "direction); `jamb_facing` (how pieces beside an opening are shaped, with evidence).", "",
             "## Single and double doors", "",
             "Double doors are two half-door objects hinged at the two outer ends of a 2-cell opening "
             "(East + West in `/` walls, North + South in `\\` walls). Single doors fill a 1-cell opening.", "",
             "| Door type | Kind | 2-cell share | 1-cell share | Weighted count | Maps |", "|---|---|---|---|---|---|"]
    for t, r in sorted(types.items(), key=lambda kv: -kv[1]["weighted_count"]):
        lines.append(f"| {t} | {r['kind']} | {r['share_two_cell']:.0%} | {r['share_one_cell']:.0%} | {r['weighted_count']} | {r['maps']} |")
    lines += ["", "## Wall pieces beside an opening", "",
              "Facings of the walls next to a door opening are computed as if the opening were wall: "
              f"{rules['jamb_facing']['shares'].get('gap_as_wall', 0):.1%} of jamb pieces match only that way, "
              f"{rules['jamb_facing']['shares'].get('gap_as_empty', 0):.1%} only the other way "
              f"({rules['jamb_facing']['shares'].get('same', 0):.1%} are the same either way). Computing them "
              "without the opening turns corners into straight pieces and Ts into corners, leaving see-through gaps.", ""]
    c.save_section("doors.md", "\n".join(lines))
    print(f"doors: {len(types)} types ({sum(1 for r in types.values() if r['kind'] == 'double')} double)")


if __name__ == "__main__":
    main()
