"""How close Westwood stands outdoor pieces and grouped creatures, on the campaign maps only (Con/War/Wiz).

The numbers kit/spacing.py (PAIR, CART_GAP, FIRE_GAP) and kit/posts.py (GAP) stand on:
- pairs: for every piece of a spacing family (kit/spacing.py FAMILIES) its nearest piece of each other family (and of
  its own), on one map of each layout; per unordered pair the 5th, 25th and 50th percentile (px between centres) and
  how many pieces measured it. The kit keeps a pair at least its p05 apart.
- creatures: every creature with another of its kind within 6 cells (a group), its distance to the nearest of its kind,
  on every campaign map; p25 and p50 (kit/posts.py GAP stays under the median).

Writes rules/out/spacing.json and prints the pairs beside the kit's table.
    py rules/spacing.py
"""
import collections, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapgen"))
import common as C
from kit import spacing as S


def pct(v, ps=(5, 25, 50)):
    v = sorted(v)
    return {f"p{p}": math.ceil(v[min(len(v) - 1, int(p / 100 * len(v)))]) for p in ps} if v else None


def main():
    camp = C.campaign_weights()
    with C.db() as con:
        rep = {r["map"]: r["rep"] for r in con.execute("SELECT map, rep FROM layout_group")}
    one_each = sorted({rep[m] for m in camp})                 # a layout group never mixes campaign and other maps
    pairs = collections.defaultdict(list)
    for m in one_each:
        pcs = [(S.family(o["type"]), o["x"], o["y"]) for o in C.objects(m)]
        pcs = [p for p in pcs if p[0]]
        for i, (fa, x, y) in enumerate(pcs):
            best = {}
            for j, (fb, x2, y2) in enumerate(pcs):
                if i != j:
                    d = math.hypot(x - x2, y - y2)
                    if d < best.get(fb, 1e9): best[fb] = d
            for fb, d in best.items(): pairs[tuple(sorted((fa, fb)))].append(d)
    grouped = []
    for m in sorted(camp):
        mons = [o for o in C.objects(m) if "MONSTER" in (o.get("class") or "")]
        for i, a in enumerate(mons):
            d = min((math.hypot(a["x"] - b["x"], a["y"] - b["y"]) for j, b in enumerate(mons)
                     if j != i and b["type"] == a["type"]), default=1e9)
            if d <= 6 * C.CELL: grouped.append(d)
    out = dict(maps=len(camp), layouts=len(one_each),
               pairs={f"{a}|{b}": dict(n=len(v), **pct(v)) for (a, b), v in sorted(pairs.items())},
               grouped_creatures=dict(n=len(grouped), **pct(grouped, (25, 50))))
    C.save_json("spacing.json", out)
    print(f"campaign maps {len(camp)}, layouts {len(one_each)}")
    print(f"{'pair':22} kit   p05  p25  p50     n")
    for (a, b), v in sorted(pairs.items()):
        kit = S.PAIR.get((a, b)) or S.PAIR.get((b, a))
        q = pct(v)
        if kit or len(v) >= 20:
            print(f"{a + '|' + b:22} {kit if kit else '-':>4} {q['p5']:5} {q['p25']:4} {q['p50']:4} {len(v):5}")
    g = out["grouped_creatures"]
    print(f"grouped creatures: {g['n']}, nearest of the kind p25 {g['p25']} px, p50 {g['p50']} px (kit/posts.py GAP {64})")


if __name__ == "__main__":
    main()
