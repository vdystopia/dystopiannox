"""Measures Westwood's placement grammar on the curated campaign rooms (rules/rooms/westwood.json with
rules/rooms/curated.json applied: kept and retyped rooms only, campaign maps Con/War/Wiz) and writes
rules/out/grammar.json, which kit/grammar.py reads (both furnishing engines' last pass and the checker's
composition.grammar_* warnings).

Each room is seen exactly as the checker sees a generated one (kit/grammar.py view_from_map), so the numbers and the
rules share one geometry:

- **lights**: floor lights per room (p50/p75/p90) and per 100 tiles; where each stands (a room corner, by a wall beside
  a piece, flanking a door, beside a piece off the walls, alone along a wall, free), what it stands beside, at a bed's
  foot, on a carpet;
- **tables**: how far from the walls, and what anchors those that stand free (a carpet or rug, the hearth or bar, a
  row of tables); **chairs** drawn up to nothing;
- **lone pieces** by category: no other piece within LINK; where (in the open, on a front wall, on a back wall);
- **gaps along walls**: the coefficient of variation of the gaps between neighbours on walls of 3+ pieces; the share
  of walls at even gaps; stepped rows;
- **plants** by type; **twin knots** (two knots of the same kinds in one shape);
- and how often each kit/grammar.py rule fires on Westwood's own rooms (the checker's false alarms).

    py rules/grammar.py
"""
import collections, json, math, os, re, sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "review", "roomlab"))
import labenv as E            # noqa: E402  (sets the import paths: validate, mapgen, rules, review)
import labref                 # noqa: E402
C = E.C
from kit import grammar as G   # noqa: E402

OUT = os.path.join(HERE, "out", "grammar.json")
HOUSE = {"bedroom", "living_room", "kitchen", "laboratory", "shop", "tavern", "guardroom", "storeroom", "study", "solar",
         "herbalist", "library", "barracks", "dining_hall", "great_hall", "cellar", "armoury", "smithy", "treasury",
         "infirmary", "workshop"}


def q(xs, p):
    xs = sorted(xs)
    if not xs: return None
    k = (len(xs) - 1) * p / 100.0
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 3)


def measure_room(e, m, r):
    v = G.view_from_map(m, r, C, e["type"])
    out = dict(type=e["type"], id=f"{e['map']}@{e['centre'][0]},{e['centre'][1]}", tiles=v.tiles)
    L = G.floor_lights(v)
    out["lights"] = len(L)
    out["light_class"] = collections.Counter(G.light_class(v, p) for p in L)
    out["light_bedfoot"] = sum(1 for p in L if G.at_bed_foot(v, p))
    out["light_carpet"] = sum(1 for p in L if v.on_carpet(p))
    serv = collections.Counter()
    for p in L:
        near = [x for x in G._others(v, p) if G.edge(p, x) <= G.SERVE]
        if near: serv[min(near, key=lambda x: G.edge(p, x))["cat"]] += 1
    out["light_serves"] = serv
    out["tables"] = collections.Counter(G.table_state(v, p) for p in v.pieces if p["cat"] == "table")
    out["table_wall"] = [round(v.wall_dist(p), 2) for p in v.pieces if p["cat"] == "table"]
    chairs = [p for p in v.pieces if p["cat"] == "chair"]
    out["chairs"] = len(chairs)
    out["chairs_lone"] = sum(1 for p in chairs if G.seat_target(v, p) > G.SEAT_REACH)
    lone = collections.defaultdict(collections.Counter)
    for p in v.pieces:
        if not v.floor(p) or p["cat"] in ("light",): continue
        lone[p["cat"]]["n"] += 1
        w = G.lone_where(v, p)
        if w: lone[p["cat"]][w] += 1
    out["lone"] = lone
    cvs = []
    for key, ps in G.wall_rows(v).items():
        if len(ps) < 3: continue
        g = G.gaps_along(key[1], ps)
        if min(g) < 0.1 and max(g) < G.EVEN_MIN_GAP: continue
        if sum(g) / len(g) >= G.EVEN_MIN_GAP: cvs.append(round(G.cv([max(0.0, x) for x in g]), 3))
    out["wall_cvs"] = cvs
    out["plants"] = sum(1 for p in v.pieces if p["cat"] == "plant")
    out["twins"] = len(G.twins(v))
    out["stepped"] = len(G.stepped_rows(v))
    return out, v


def _mine_map(args):
    name, entries = args
    out = []
    for e, m, r in labref.rooms_of_map(name, entries):
        rec, _ = measure_room(e, m, r)
        out.append(rec)
    return out


def _fault_map(args):
    name, entries = args
    G.stats.cache_clear()
    out = []
    for e, m, r in labref.rooms_of_map(name, entries):
        v = G.view_from_map(m, r, C, e["type"])
        out.append((e["type"], collections.Counter(f["rule"] for f in G.faults(v))))
    return out


def summarise(recs):
    def block(rs):
        n = len(rs)
        if not n: return {}
        lights = [x["lights"] for x in rs]
        per100 = [100.0 * x["lights"] / max(1, x["tiles"]) for x in rs]
        cls = sum((x["light_class"] for x in rs), collections.Counter())
        nl = sum(cls.values()) or 1
        tables = sum((x["tables"] for x in rs), collections.Counter())
        nt = sum(tables.values()) or 1
        chairs = sum(x["chairs"] for x in rs)
        lone = collections.defaultdict(collections.Counter)
        for x in rs:
            for c, d in x["lone"].items(): lone[c].update(d)
        cvs = [c for x in rs for c in x["wall_cvs"]]
        return dict(
            rooms=n,
            lights_p50=q(lights, 50), lights_p75=q(lights, 75), lights_p90=q(lights, 90), lights_max=max(lights),
            lights_per100_p50=round(q(per100, 50), 2), lights_per100_p90=round(q(per100, 90), 2),
            rooms_lit=round(sum(1 for x in lights if x) / n, 2),
            light_class={k: round(c / nl, 3) for k, c in cls.most_common()}, light_n=sum(cls.values()),
            light_bedfoot=sum(x["light_bedfoot"] for x in rs), light_carpet=sum(x["light_carpet"] for x in rs),
            light_serves=dict(sum((x["light_serves"] for x in rs), collections.Counter()).most_common()),
            tables={k: round(c / nt, 3) for k, c in tables.most_common()}, table_n=sum(tables.values()),
            table_wall_p50=q([d for x in rs for d in x["table_wall"]], 50),
            table_wall_p90=q([d for x in rs for d in x["table_wall"]], 90),
            chairs=chairs, lone_chair_share=round(sum(x["chairs_lone"] for x in rs) / chairs, 3) if chairs else 0.0,
            lone={c: dict(n=d["n"], alone=round((d["open"] + d["front"] + d["back"]) / d["n"], 3),
                          open=round(d["open"] / d["n"], 3), front=round(d["front"] / d["n"], 3))
                  for c, d in sorted(lone.items(), key=lambda kv: -kv[1]["n"]) if d["n"]},
            lone_exposed={c: round((d["open"] + d["front"]) / d["n"], 3) for c, d in lone.items() if d["n"] >= 8},
            wall_cv_p10=q(cvs, 10), wall_cv_p25=q(cvs, 25), wall_cv_p50=q(cvs, 50), walls_3plus=len(cvs),
            walls_even=round(sum(1 for c in cvs if c < G.EVEN_CV) / len(cvs), 3) if cvs else 0.0,
            plants=sum(x["plants"] for x in rs), rooms_with_plants=sum(1 for x in rs if x["plants"]),
            rooms_twins=sum(1 for x in rs if x["twins"]), rooms_stepped=sum(1 for x in rs if x["stepped"]),
        )
    by = collections.defaultdict(list)
    for x in recs: by[x["type"]].append(x)
    return dict(types={t: block(rs) for t, rs in sorted(by.items())},
                house=block([x for x in recs if x["type"] in HOUSE]),
                all=block(recs))


def main():
    by = collections.defaultdict(list)
    for e in labref.index():          # the curated index: kept and retyped rooms only, never the excluded ones
        if not re.match(r"^(Con|War|Wiz)", e["map"]) or e["type"] == "passage": continue
        by[e["map"]].append(e)
    with ProcessPoolExecutor(6) as pool:
        recs = [x for xs in pool.map(_mine_map, sorted(by.items())) for x in xs]
    st = summarise(recs)
    st["source"] = ("rules/rooms/westwood.json index with rules/rooms/curated.json applied (campaign maps Con/War/Wiz, "
                    "kept and retyped rooms only), each room as validate/checks.py finds it")
    st["made_by"] = "rules/grammar.py"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)
    # how often each rule fires on Westwood's own rooms, with the numbers just written
    with ProcessPoolExecutor(6) as pool:
        fr = [x for xs in pool.map(_fault_map, sorted(by.items())) for x in xs]
    fires = collections.defaultdict(collections.Counter)
    rooms = collections.Counter()
    for t, c in fr:
        rooms[t] += 1; rooms["*"] += 1
        for rule in c:
            fires[t][rule] += 1; fires["*"][rule] += 1
            if t in HOUSE: fires["house"][rule] += 1
        if t in HOUSE: rooms["house"] += 1
    st["westwood_fires"] = {t: {rule: round(n / rooms[t], 3) for rule, n in c.most_common()} for t, c in fires.items()}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)
    h = st["house"]
    print(f"{len(recs)} rooms -> {os.path.relpath(OUT, REPO)}")
    print(f"house lights: per room p50 {h['lights_p50']} p90 {h['lights_p90']}; where {h['light_class']}; "
          f"at a bed's foot {h['light_bedfoot']}, on a carpet {h['light_carpet']}; beside {h['light_serves']}")
    print(f"house tables: {h['tables']} (wall p50 {h['table_wall_p50']}, p90 {h['table_wall_p90']}); "
          f"lone chairs {h['lone_chair_share']}")
    print(f"house lone (exposed: open + front): {h['lone_exposed']}")
    print(f"house walls of 3+: CV p10 {h['wall_cv_p10']} p50 {h['wall_cv_p50']}, even {h['walls_even']} of {h['walls_3plus']}")
    print(f"rooms with twins {st['all']['rooms_twins']}, stepped rows {st['all']['rooms_stepped']} of {st['all']['rooms']}")
    print("plants by type:", {t: s["plants"] for t, s in st["types"].items() if s["plants"]})
    print(f"{'type':14} {'rooms':>5}  lights p50/p90 per100p90  lone chairs  tables")
    for t, s in sorted(st["types"].items(), key=lambda kv: -kv[1]["rooms"]):
        print(f"{t:14} {s['rooms']:5}  {s['lights_p50']}/{s['lights_p90']} {s['lights_per100_p90']:>6}   "
              f"{s['lone_chair_share']:.2f}   {s['tables']}")
    print("Westwood rooms a rule fires on (share):")
    for t in ("*", "house"):
        print(f"  {t}: {st['westwood_fires'].get(t)}")


if __name__ == "__main__":
    main()
