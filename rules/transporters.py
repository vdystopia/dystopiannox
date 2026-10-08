"""Transporters in Westwood's campaign maps: lifts (elevator + pit), teleport pads (pentagrams), stairs and the exits
beside them, and scripted moves of the player. Writes rules/out/transporters.json; rules/TRANSPORTERS.md is the
reference written from it.

    py rules/transporters.py [--scripts DIR]     # DIR: decompiled map scripts (noxtools ns decomp), optional

Measured per link (validate/transport.py reads the links): the two ends' types and spots, the distance, whether it
starts enabled, whether the far end is walled off from the near one (isolated), whether it is the only way into the far
area, the way back, the wall clearance at each end, the floor and the room polygon at each end, what stands round each
end. Campaign maps only (Con/War/Wiz), each layout once where a share is given (common.campaign_weights).
"""
import argparse, collections, json, math, os, re, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "validate"))
import common as C                    # noqa: E402
import mapdata as md                  # noqa: E402
import transport as T                 # noqa: E402

STAIRS = re.compile(r"Stairs")
NEAR = 115          # px: what stands round an end


def in_poly(x, y, pts):
    inside = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: inside = not inside
    return inside


def polygon_at(m, x, y):
    for p in m.polygons:
        pts = p.get("points") or p.get("pts") or []
        if pts and in_poly(x, y, [tuple(q) for q in pts]): return p.get("name")
    return None


def around(m, o, r=NEAR):
    return sorted(q["type"] for q in m.objects if q is not o and abs(q["x"] - o["x"]) < r and abs(q["y"] - o["y"]) < r
                  and math.hypot(q["x"] - o["x"], q["y"] - o["y"]) < r)


def pct(vals, p):
    v = sorted(vals)
    if not v: return None
    k = (len(v) - 1) * p / 100
    f = int(k)
    return round(v[f] + (v[min(f + 1, len(v) - 1)] - v[f]) * (k - f), 1)


def spread(vals):
    return dict(n=len(vals), p5=pct(vals, 5), p25=pct(vals, 25), p50=pct(vals, 50), p75=pct(vals, 75),
                p95=pct(vals, 95), min=round(min(vals), 1) if vals else None, max=round(max(vals), 1) if vals else None)


def measure_map(name):
    m = md.MapData(md.corpus_json(name))
    blocked = T.walk_blocked(m)
    label, size = T.regions(m, blocked)
    lks = T.links(m)
    g = T.graph(m, lks, label, size)
    starts = [o for o in m.objects if o["type"] == "PlayerStart"]
    main = T.region_at(m, label, size, starts[0]["x"], starts[0]["y"]) if starts else None
    rows = []
    for l in lks:
        s, d = l.src, l.dst
        row = dict(map=name, kind=l.kind, src=s["type"], sx=round(s["x"]), sy=round(s["y"]), scr=s["scr"],
                   enabled=l.enabled, two_way=l.two_way, problem=l.problem,
                   src_floor=m.floor_at(s["x"], s["y"]), src_poly=polygon_at(m, s["x"], s["y"]),
                   src_clear=round(T.wall_clearance(m, s["x"], s["y"])), src_near=around(m, s))
        if l.kind == T.EXIT:
            row.update(to_map=(s["xfer"] or {}).get("MapName"), exit_xy=[(s["xfer"] or {}).get("ExitX"),
                                                                       (s["xfer"] or {}).get("ExitY")])
        if d is not None:
            a = T.region_at(m, label, size, s["x"], s["y"])
            b = T.region_at(m, label, size, d["x"], d["y"])
            # the far area without this link: is there another way in from the start?
            g2 = T.graph(m, [x for x in lks if x is not l], label, size)
            row.update(dst=d["type"], dx=round(d["x"]), dy=round(d["y"]), dst_scr=d["scr"], dst_enabled=d["enabled"],
                       dist=round(math.hypot(d["x"] - s["x"], d["y"] - s["y"])),
                       isolated=(a != b), dst_region_cells=size.get(b), src_region_cells=size.get(a),
                       dst_is_main=(b == main), src_is_main=(a == main),
                       only_way_in=(main is not None and b not in T.reach(g2, main) and b != main),
                       way_back=(a == b or a in T.reach(g, b)),
                       dst_floor=m.floor_at(d["x"], d["y"]), dst_poly=polygon_at(m, d["x"], d["y"]),
                       dst_clear=round(T.wall_clearance(m, d["x"], d["y"])), dst_near=around(m, d))
        rows.append(row)
    # stairs: the decorative pieces round a main piece, the pad on it and where the player arrives back at it
    stairs = []
    st = [o for o in m.objects if STAIRS.search(o["type"]) and not T.kind(o)]
    for o in st:
        near = [q for q in m.objects if T.kind(q) and math.hypot(q["x"] - o["x"], q["y"] - o["y"]) < 160]
        n = min(near, key=lambda q: math.hypot(q["x"] - o["x"], q["y"] - o["y"])) if near else None
        row = dict(map=name, type=o["type"], x=round(o["x"]), y=round(o["y"]),
                   nearest=n["type"] if n else None,
                   nearest_px=round(math.hypot(n["x"] - o["x"], n["y"] - o["y"])) if n else None)
        if not o["type"].endswith("Piece"):
            box = lambda q, r=130: abs(q["x"] - o["x"]) < r and abs(q["y"] - o["y"]) < r
            row["pieces"] = sorted([q["type"], round(q["x"] - o["x"]), round(q["y"] - o["y"])]
                                   for q in st if q is not o and q["type"].endswith("Piece") and box(q, 60))
            pad = [l for l in lks if l.kind in (T.PAD, T.EXIT) and box(l.src, 40)]
            if pad:
                l = pad[0]
                row["pad"] = [l.src["type"], round(l.src["x"] - o["x"]), round(l.src["y"] - o["y"])]
                row["leads"] = "map" if l.kind == T.EXIT else "in-map"
            arr = [l.dst for l in lks if l.kind == T.PAD and l.dst is not None and box(l.dst, 90)
                   and not (l.dst["xfer"] or {}).get("ExtentLink")]
            if arr: row["arrive"] = [round(arr[0]["x"] - o["x"]), round(arr[0]["y"] - o["y"])]
        stairs.append(row)
    # two-way pads: the arrival marker beside the pad that sends the player back (not on it: Westwood never links two
    # pads to each other both ways)
    returns = []
    srcs = [l.src for l in lks if l.kind == T.PAD]
    for l in lks:
        if l.kind != T.PAD or l.dst is None or (l.dst["xfer"] or {}).get("ExtentLink"): continue
        near = [s for s in srcs if s is not l.dst and s is not l.src]
        if not near: continue
        s = min(near, key=lambda s: math.hypot(s["x"] - l.dst["x"], s["y"] - l.dst["y"]))
        d = math.hypot(s["x"] - l.dst["x"], s["y"] - l.dst["y"])
        if 5 < d < 200:
            returns.append(dict(map=name, pad=s["type"], src=l.src["type"], px=round(d),
                                off=[round(l.dst["x"] - s["x"]), round(l.dst["y"] - s["y"])]))
    # a lift's base pieces (CaveElevatorBase under a cave lift and its pit)
    bases = collections.Counter()
    for o in m.objects:
        if T.kind(o) not in (T.LIFT, T.SHAFT): continue
        for q in m.objects:
            if q is not o and not T.kind(q) and "Elevator" in q["type"] and abs(q["x"] - o["x"]) < 40 and abs(q["y"] - o["y"]) < 40:
                bases[(o["type"], q["type"], round(q["x"] - o["x"]), round(q["y"] - o["y"]))] += 1
    return rows, stairs, m, returns, bases


def scripted_moves(scripts_dir, maps):
    """Functions of the decompiled campaign scripts that move the player (MoveObject on GetHost/GetCaller), with what
    calls them (a polygon, a trigger, another function) and whether the screen is blinded first."""
    out = []
    if not scripts_dir or not os.path.isdir(scripts_dir): return out
    for name, m in maps.items():
        p = os.path.join(scripts_dir, name.lower() + ".go")
        if not os.path.exists(p): continue
        src = open(p, encoding="utf-8", errors="replace").read()
        funcs = dict(re.findall(r"^func (\w+)\(\) \{\n(.*?)^\}", src, re.S | re.M))
        for fn, body in funcs.items():
            if not re.search(r"MoveObject\(ns\.(GetHost|GetCaller)\(\)", body): continue
            base = re.sub(r"SEG\d+$", "", fn)
            callers = [f for f, b in funcs.items() if f != fn and re.search(rf"\b{fn}\b", b)]
            polys = [p.get("name") for p in m.polygons if (p.get("enterP") or "") in (fn, base)]
            objs = [o["type"] for o in m.objects if any(v in (fn, base) for v in (o["xfer"] or {}).values()
                                                         if isinstance(v, str))]
            blind = bool(re.search(r"ns\.Blind\(\)", body + "".join(funcs.get(c, "") for c in callers + [base])))
            out.append(dict(map=name, func=fn, callers=callers, polygons=polys, objects=objs, blind=blind,
                            waypoint=bool(re.search(r"GetWaypointX|Waypoint\(", body))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripts", default=os.environ.get("NOX_SCRIPTS"), help="decompiled campaign scripts (*.go)")
    a = ap.parse_args()
    W = C.campaign_weights()
    rows, stairs, maps, returns, bases = [], [], {}, [], collections.Counter()
    for name in sorted(W):
        r, s, m, ret, b = measure_map(name)
        rows += r; stairs += s; maps[name] = m; returns += ret; bases.update(b)
    out = os.path.join(C.OUT, "transporters.json")
    moves = scripted_moves(a.scripts, maps)
    if not moves and os.path.exists(out):          # the decompiled scripts are not at hand: keep the last measure
        with open(out, encoding="utf-8") as f: moves = json.load(f).get("scripted", [])

    def lw(rs):            # layouts (weighted count)
        return round(sum(W[r["map"]] for r in rs), 1)

    summary = {}
    for k in (T.LIFT, T.PAD, T.EXIT):
        rs = [r for r in rows if r["kind"] == k]
        good = [r for r in rs if not r["problem"] and "dst" in r]
        summary[k] = dict(
            count=len(rs), maps=len({r["map"] for r in rs}), layouts=lw(rs),
            types=collections.Counter(r["src"] for r in rs).most_common(),
            dst_types=collections.Counter(r.get("dst") for r in rs).most_common(),
            problems=collections.Counter(r["problem"] for r in rs if r["problem"]).most_common(),
            enabled=sum(r["enabled"] for r in rs), disabled=sum(not r["enabled"] for r in rs),
            two_way=sum(r["two_way"] for r in good), isolated=sum(r["isolated"] for r in good),
            only_way_in=sum(r["only_way_in"] for r in good), way_back=sum(r["way_back"] for r in good),
            linked=len(good),
            dist=spread([r["dist"] for r in good]), src_clear=spread([r["src_clear"] for r in rs]),
            dst_clear=spread([r["dst_clear"] for r in good]),
            dst_region_cells=spread([r["dst_region_cells"] for r in good if r["dst_region_cells"]]),
            same_floor=sum(r["src_floor"] == r["dst_floor"] for r in good),
            other_poly=sum(r["src_poly"] != r["dst_poly"] for r in good),
            near_src=collections.Counter(t for r in rs for t in set(r["src_near"])).most_common(25),
            near_dst=collections.Counter(t for r in good for t in set(r["dst_near"])).most_common(25),
        )
    pads = [r for r in rows if r["kind"] == T.PAD and "dst" in r]
    summary[T.PAD]["visible_src"] = sum(r["src"] == "TeleportPentagram" for r in pads)
    summary[T.PAD]["arrival_marker"] = sum(r["dst"] == "InvisibleTeleportPentagram" and not r["two_way"] for r in pads)
    exits = [r for r in rows if r["kind"] == T.EXIT]
    summary[T.EXIT]["to_map"] = sum(bool(r.get("to_map")) for r in exits)
    summary["stairs"] = dict(count=len(stairs), types=collections.Counter(s["type"] for s in stairs).most_common(),
                             nearest=collections.Counter(s["nearest"] for s in stairs).most_common())
    summary["scripted"] = dict(count=len(moves), maps=len({x["map"] for x in moves}),
                               blind=sum(x["blind"] for x in moves),
                               by_polygon=sum(bool(x["polygons"]) for x in moves),
                               by_object=sum(bool(x["objects"]) for x in moves),
                               funcs=collections.Counter(re.sub(r"SEG\d+$", "", x["func"]) for x in moves).most_common(40))
    # the shapes the kit lays (mapgen/kit/transport.py): each stairs type's pieces, pad and arrival spot (medians over
    # the main pieces that have them), the arrival marker beside a return pad, a lift's base pieces
    med = lambda xs: round(statistics.median(xs)) if xs else None
    geo = dict(stairs={}, returns=dict(spread([r["px"] for r in returns]),
                                       off=collections.Counter(tuple(r["off"]) for r in returns).most_common(12)),
               lift_bases=[[a, b, x, y, n] for (a, b, x, y), n in bases.most_common()])
    for t in sorted({s["type"] for s in stairs if "pieces" in s}):
        ss = [s for s in stairs if s["type"] == t]
        shape = collections.Counter(tuple(p[0] for p in s["pieces"]) for s in ss).most_common(1)[0][0]
        same = [s for s in ss if tuple(p[0] for p in s["pieces"]) == shape]
        pieces = [[shape[i], med([s["pieces"][i][1] for s in same]), med([s["pieces"][i][2] for s in same])]
                  for i in range(len(shape))]
        pads = [s["pad"] for s in ss if "pad" in s]
        arr = [s["arrive"] for s in ss if "arrive" in s]
        geo["stairs"][t] = dict(n=len(ss), maps=sorted({s["map"] for s in ss}), pieces=pieces,
                                pad=[med([p[1] for p in pads]), med([p[2] for p in pads])] if pads else None,
                                arrive=[med([p[0] for p in arr]), med([p[1] for p in arr])] if arr else None,
                                n_arrive=len(arr), leads=collections.Counter(s.get("leads") for s in ss).most_common())
    summary["geometry"] = geo
    os.makedirs(C.OUT, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        # one line per link (what stands round each end is summed in the summary only)
        slim = [{k: v for k, v in r.items() if k not in ("src_near", "dst_near")} for r in rows]
        f.write("{\"summary\": " + json.dumps(summary, indent=1) + ",\n\"links\": [\n" +
                ",\n".join(json.dumps(r) for r in slim) + "],\n\"stairs\": [\n" +
                ",\n".join(json.dumps(r) for r in stairs) + "],\n\"scripted\": [\n" +
                ",\n".join(json.dumps(r) for r in moves) + "]}\n")
    print(json.dumps(summary, indent=1)[:20000])
    print("wrote", out)


if __name__ == "__main__":
    main()
