"""Mines floor-material rules from the reference corpus:

1. Material adjacency and edge blending (which pairs touch, whether/how they are blended, which
   material overlays which), an implied priority order, and pairs that never touch (need a buffer).
2. Edge piece rules (sides / corner "Sides" pieces / tips) and skip rates; tile and edge variation rule.
3. Floor families (biomes): membership, proportions, typical palettes and family neighbours.

Writes rules/out/floors.json and rules/sections/floors.md. Run: py rules/floors.py
"""
import json, os, re, statistics
from collections import Counter, defaultdict
import common as C

SIDE = C.EDGE_SIDES                       # E, N, S, W -> offset
TIPS = C.EDGE_TIPS                        # NE, NW, SE, SW -> offset
OPP = {"E": "W", "W": "E", "N": "S", "S": "N"}
SIDE_PIECES = {"E": (12, 13, 14), "N": (6, 8, 10), "S": (5, 7, 9), "W": (1, 2, 3)}
CORNER_PIECES = {("E", "N"): 18, ("E", "S"): 19, ("N", "W"): 17, ("S", "W"): 16}
TIP_PIECES = {"NE": 15, "NW": 4, "SE": 11, "SW": 0}
TIP_BLOCKERS = {"NE": ("E", "N"), "NW": ("N", "W"), "SE": ("E", "S"), "SW": ("S", "W")}
# edge pieces that cover a given side of the base tile
COVER = {d: set(SIDE_PIECES[d]) | {p for k, p in CORNER_PIECES.items() if d in k} for d in SIDE}
PIECE_KIND = {p: ("side", d) for d, ps in SIDE_PIECES.items() for p in ps}
PIECE_KIND.update({p: ("corner", k) for k, p in CORNER_PIECES.items()})
PIECE_KIND.update({p: ("tip", t) for t, p in TIP_PIECES.items()})

GAMEDATA = json.load(open(os.path.join(C.REPO, "corpus", "out", "json", "things.json"), encoding="utf-8"))
FLOOR_INFO = {f["name"]: f for f in GAMEDATA["floors"]}
EDGE_NVAR = {e["name"]: e["nvar"] for e in GAMEDATA["edges"]}

FAMILY_RULES = [  # first match wins
    ("water", r"^Water"), ("lava", r"Lava|Volcanic"), ("ice", r"^Ice"), ("swamp", r"^Swamp"),
    ("facade", r"Facade$"), ("interior_rug", r"^Rug|Bearskin"),
    ("interior_wood", r"Wood|Oak|Redwood"), ("grass", r"^Grass|^Weeds"),
    ("dirt", r"^Dirt|^Mud|ManaMineDirt"), ("cave", r"^Cave|^Rock"),
    ("cobble", r"Cobble"), ("brick", r"Brick|^Bluebrick|^Redbrick"),
    ("dungeon_stone", r"^Dungeon|^Crypt|^LOTD|^Stone|^AncientRuin|Marble"),
    ("tile", r"^Tile|^Checker|^Crystal|^Busy"), ("bones", r"^Bones"), ("void", r"^Black$|^Transparent"),
]


def family(mat):
    for fam, rx in FAMILY_RULES:
        if re.search(rx, mat): return fam
    return "other"


def auto_variation(mat, x, y):
    f = FLOOR_INFO[mat]
    cols, rows = f["cols"], f["rows"]
    h = (x + y) // 2
    return (h % cols) + (((y % rows) + 1 + cols - (h % cols)) % rows) * cols


def mine():
    W = C.campaign_weights()
    # adjacency (unordered pair key sorted), per contact
    pair = defaultdict(lambda: dict(sp_w=0.0, all=0, maps=set(), sp_maps=set(), a_over_b=0.0, b_over_a=0.0,
                                    none=0.0, both=0.0, types=Counter(), all_edge=0))
    area_sp = Counter(); area_all = Counter(); maps_with = defaultdict(set)
    piece_stats = Counter(); piece_rule = Counter(); side_variants = Counter(); skips = Counter()
    var_tile = Counter(); var_edge = Counter(); var_tile_by_mat = defaultdict(Counter)
    edge_type_use = Counter(); edge_type_sp = Counter()
    fam_share = defaultdict(list)       # per SP map: family -> share
    fam_contacts = Counter()
    buffer_seen = defaultdict(Counter)  # (a, b) -> middle material along straight 2-step lines

    for m in C.all_maps():
        t = C.tiles(m)
        w = W.get(m, 0.0)
        mats = Counter()
        for (x, y), tile in t.items():
            mat = tile["material"]
            mats[mat] += 1
            area_all[mat] += 1; area_sp[mat] += w; maps_with[mat].add(m)
            # variation rule
            if mat in FLOOR_INFO:
                ok = tile["variation"] == auto_variation(mat, x, y)
                var_tile[ok] += 1; var_tile_by_mat[mat][ok] += 1
            for ov, ev, ed, et in tile["edges"]:
                if ov in FLOOR_INFO: var_edge[ev == auto_variation(ov, x, y)] += 1
                edge_type_use[et] += 1; edge_type_sp[et] += w
            # contacts: count each unordered contact once (E and S directions)
            for d in ("E", "S"):
                dx, dy = SIDE[d]
                q = t.get((x + dx, y + dy))
                if not q or q["material"] == mat: continue
                a, b = mat, q["material"]
                b_on_a = [e for e in tile["edges"] if e[0] == b and e[2] in COVER[d]]
                a_on_b = [e for e in q["edges"] if e[0] == a and e[2] in COVER[OPP[d]]]
                key = tuple(sorted((a, b)))
                s = pair[key]
                s["sp_w"] += w; s["all"] += 1; s["maps"].add(m)
                if w: s["sp_maps"].add(m)
                first_over_second = (a_on_b if key[0] == a else b_on_a)
                second_over_first = (b_on_a if key[0] == a else a_on_b)
                if first_over_second and second_over_first: s["both"] += w
                elif first_over_second: s["a_over_b"] += w
                elif second_over_first: s["b_over_a"] += w
                else: s["none"] += w
                if first_over_second or second_over_first: s["all_edge"] += 1
                for e in first_over_second + second_over_first: s["types"][e[3]] += 1
                if w: fam_contacts[tuple(sorted((family(a), family(b))))] += w
            # buffer materials: straight lines a - mid - b along a side direction
            if w:
                for d in ("E", "S"):
                    dx, dy = SIDE[d]
                    q1 = t.get((x + dx, y + dy)); q2 = t.get((x + 2 * dx, y + 2 * dy))
                    if q1 and q2:
                        mid, b = q1["material"], q2["material"]
                        if mid != mat and mid != b and mat != b:
                            buffer_seen[tuple(sorted((mat, b)))][mid] += w
            # edge piece rules (only edge types with the full 20-piece set)
            by_over = defaultdict(list)
            for e in tile["edges"]:
                if EDGE_NVAR.get(e[3], 0) == 20: by_over[e[0]].append(e)
            for ov, es in by_over.items():
                sides = {d for d, (dx, dy) in SIDE.items() if (x + dx, y + dy) in t and t[(x + dx, y + dy)]["material"] == ov}
                tips = {k for k, (dx, dy) in TIPS.items() if (x + dx, y + dy) in t and t[(x + dx, y + dy)]["material"] == ov}
                expected, rem = set(), set(sides)
                for (p, q2), piece in CORNER_PIECES.items():
                    if p in rem and q2 in rem: expected.add(("corner", (p, q2))); rem -= {p, q2}
                expected |= {("side", d) for d in rem}
                expected |= {("tip", k) for k in tips if not any(bl in sides for bl in TIP_BLOCKERS[k])}
                actual = {PIECE_KIND[e[2]] for e in es if e[2] in PIECE_KIND}
                piece_rule["exact" if actual == expected else "differs"] += w or 0.0
                piece_rule["n"] += w
                for kind in expected - actual: skips[("missing",) + (kind[0],)] += w
                for kind in actual - expected: skips[("extra",) + (kind[0],)] += w
                for e in es:
                    k = PIECE_KIND.get(e[2])
                    if k: piece_stats[k[0]] += w
                    if k and k[0] == "side": side_variants[(k[1], e[2])] += w
        if w and mats:
            tot = sum(mats.values())
            fams = Counter()
            for mat, n in mats.items(): fams[family(mat)] += n
            for f in set(family(x) for x in FLOOR_INFO) | set(fams):
                fam_share[f].append(fams[f] / tot)

    return dict(pair=pair, area_sp=area_sp, area_all=area_all, maps_with=maps_with, piece_stats=piece_stats,
                piece_rule=piece_rule, side_variants=side_variants, skips=skips, var_tile=var_tile, var_edge=var_edge,
                var_tile_by_mat=var_tile_by_mat, edge_type_use=edge_type_use, edge_type_sp=edge_type_sp,
                fam_share=fam_share, fam_contacts=fam_contacts, buffer_seen=buffer_seen)


def build(r):
    pair, area_sp = r["pair"], r["area_sp"]
    blend = []
    for (a, b), s in pair.items():
        if s["all"] < 10: continue
        tot = s["sp_w"] or 1e-9
        edged_sp = s["a_over_b"] + s["b_over_a"] + s["both"]
        if s["sp_w"] > 0:
            over = (a, b) if s["a_over_b"] >= s["b_over_a"] else (b, a)
            over_share = max(s["a_over_b"], s["b_over_a"]) / max(edged_sp, 1e-9)
        else:
            over, over_share = (a, b), None
        types = s["types"].most_common()
        blend.append(dict(
            a=a, b=b, contacts_all=s["all"], maps_all=len(s["maps"]), contacts_sp_weighted=round(s["sp_w"], 1),
            maps_sp=len(s["sp_maps"]),
            edge_share_sp=round(edged_sp / tot, 3) if s["sp_w"] else None,
            edge_share_all=round(s["all_edge"] / s["all"], 3),
            overlay=over[0], base=over[1], overlay_direction_share=round(over_share, 3) if over_share is not None else None,
            edge_types={k: round(v / max(1, sum(s["types"].values())), 3) for k, v in types[:4]},
            preferred_edge_type=types[0][0] if types else None))
    blend.sort(key=lambda d: -d["contacts_all"])

    # priority: Copeland-style score from overlay direction, weighted by contacts (SP)
    score = Counter(); seen = Counter()
    for (a, b), s in pair.items():
        if s["sp_w"] <= 0: continue
        n = s["a_over_b"] + s["b_over_a"]
        if n <= 0: continue
        score[a] += (s["a_over_b"] - s["b_over_a"]) / n * min(n, 50)
        score[b] += (s["b_over_a"] - s["a_over_b"]) / n * min(n, 50)
        seen[a] += min(n, 50); seen[b] += min(n, 50)
    priority = {m: dict(score=round(score[m] / seen[m], 3), evidence=round(seen[m], 1)) for m in seen if seen[m] >= 5}

    # never-touch pairs among common materials
    common = [m for m, v in area_sp.most_common() if v >= 200][:70]
    cooc = Counter()
    for m in C.campaign_maps():
        mats = {t["material"] for t in C.tiles(m).values()}
        for i, a in enumerate(common):
            if a not in mats: continue
            for b in common[i + 1:]:
                if b in mats: cooc[tuple(sorted((a, b)))] += 1
    buffers = []
    for (a, b), n in cooc.items():
        s = pair.get((a, b))
        if n >= 4 and (not s or s["all"] == 0):
            mids = r["buffer_seen"].get((a, b), Counter())
            tot = sum(mids.values())
            buffers.append(dict(a=a, b=b, cooccur_sp_maps=n,
                                buffer_materials={k: round(v / tot, 3) for k, v in mids.most_common(4)} if tot else {}))
    buffers.sort(key=lambda d: (not d["buffer_materials"], -d["cooccur_sp_maps"]))

    # families
    fam_members = defaultdict(list)
    for m, v in area_sp.most_common():
        fam_members[family(m)].append((m, v))
    families = {}
    for f, mems in fam_members.items():
        tot = sum(v for _, v in mems) or 1e-9
        shares = r["fam_share"].get(f, [])
        nz = [x for x in shares if x > 0]
        families[f] = dict(
            materials={m: round(v / tot, 3) for m, v in mems if v > 0},
            unused_in_sp=[m for m, v in mems if v == 0],
            sp_maps_using=len(nz), median_share_when_used=round(statistics.median(nz), 3) if nz else 0)
    fam_nb = defaultdict(Counter)
    for (fa, fb), v in r["fam_contacts"].items():
        if fa != fb: fam_nb[fa][fb] += v; fam_nb[fb][fa] += v
    for f in families:
        tot = sum(fam_nb[f].values()) or 1e-9
        families[f]["neighbour_families"] = {k: round(v / tot, 3) for k, v in fam_nb[f].most_common(5)}

    pr = r["piece_rule"]
    piece_total = sum(r["piece_stats"].values()) or 1e-9
    sv = defaultdict(dict)
    for (d, p), v in r["side_variants"].items(): sv[d][p] = v
    side_variant_share = {d: {str(p): round(v / sum(ps.values()), 3) for p, v in sorted(ps.items())} for d, ps in sv.items()}
    vt, ve = r["var_tile"], r["var_edge"]
    by_mat = {m: round(c[True] / max(1, c[True] + c[False]), 3) for m, c in r["var_tile_by_mat"].items() if sum(c.values()) >= 200}
    return dict(
        blend=blend,
        priority=dict(sorted(priority.items(), key=lambda kv: -kv[1]["score"])),
        material_family={m: family(m) for m in FLOOR_INFO},
        families=families,
        never_touch=buffers[:80],
        edge_pieces=dict(
            rule="side neighbour of overlay material -> side piece (3 variants, random); two adjacent sides -> "
                 "corner 'Sides' piece; tip neighbour with neither adjacent side -> tip piece",
            exact_match_share_sp=round(pr["exact"] / max(pr["n"], 1e-9), 3),
            piece_kind_share_sp={k: round(v / piece_total, 3) for k, v in r["piece_stats"].items()},
            deviations_per_group_sp={f"{a}_{k}": round(v / max(pr["n"], 1e-9), 3) for (a, k), v in r["skips"].items()},
            side_variant_share_sp=side_variant_share,
            piece_ids=dict(side={d: list(p) for d, p in SIDE_PIECES.items()},
                           corner={"+".join(k): p for k, p in CORNER_PIECES.items()}, tip=TIP_PIECES),
            note="only edge types with 20 pieces are analysed; edge types with fewer pieces use the editor's remapped numbering"),
        variation_rule=dict(
            tile_matches_editor_formula_all=round(vt[True] / max(1, sum(vt.values())), 3),
            edge_matches_editor_formula_all=round(ve[True] / max(1, sum(ve.values())), 3),
            tile_match_by_material=dict(sorted(by_mat.items(), key=lambda kv: kv[1]))),
        edge_types={k: dict(uses_all=v, nvar=EDGE_NVAR.get(k), sp_weighted=round(r["edge_type_sp"][k], 1))
                    for k, v in r["edge_type_use"].most_common()},
    )


def md(d):
    L = ["# Floors and edge blending", "",
         "Schema of `rules/out/floors.json`:",
         "- `blend[]`: one entry per pair of materials that touch as side neighbours (>= 10 contacts in all maps): "
         "`a`, `b`, `contacts_all`, `maps_all`, `contacts_sp_weighted`, `maps_sp`, `edge_share_sp` (share of campaign contacts "
         "with an edge overlay on the touching side), `edge_share_all`, `overlay`/`base` (which material is drawn over which), "
         "`overlay_direction_share`, `edge_types` (share), `preferred_edge_type`.",
         "- `priority{material: {score, evidence}}`: score -1..1, higher = drawn over neighbours (campaign maps, weighted); evidence = weighted blended contacts.",
         "- `material_family{}`, `families{family: materials (area share), unused_in_sp, sp_maps_using, median_share_when_used, neighbour_families}`.",
         "- `never_touch[]`: common materials that co-occur in campaign maps but never touch; `buffer_materials` seen between them.",
         "- `edge_pieces{}`: piece rule, match rate, deviations, side-variant shares, piece ids.",
         "- `variation_rule{}`: share of tiles/edges whose variation equals the editor's automatic formula.",
         "- `edge_types{}`: usage counts and piece count (`nvar`).", ""]
    vr = d["variation_rule"]
    L += ["## Variation rule", "",
          f"- Tile variation equals the editor's position formula for {vr['tile_matches_editor_formula_all']:.0%} of all tiles; "
          f"edge variation equals the overlay material's formula for {vr['edge_matches_editor_formula_all']:.0%} of edges.",
          "- Lowest-matching materials: " + ", ".join(f"{m} {v:.0%}" for m, v in list(vr["tile_match_by_material"].items())[:8]), ""]
    ep = d["edge_pieces"]
    L += ["## Edge pieces", "", f"- Rule: {ep['rule']}.",
          f"- Exact match with the rule: {ep['exact_match_share_sp']:.0%} of (tile, overlay) groups (campaign maps, weighted).",
          f"- Piece kinds: {ep['piece_kind_share_sp']}. Deviations per group: {ep['deviations_per_group_sp']}.",
          f"- Side variants are used about equally: {ep['side_variant_share_sp']}.", ""]
    L += ["## Most common blends (campaign maps)", "",
          "| a | b | contacts (all) | maps | blended | overlay on base | edge type |", "|---|---|---|---|---|---|---|"]
    for b in [b for b in d["blend"] if b["maps_sp"] >= 3][:45]:
        L.append(f"| {b['a']} | {b['b']} | {b['contacts_all']} | {b['maps_all']} | {b['edge_share_sp']:.0%} | "
                 f"{b['overlay']} over {b['base']} ({b['overlay_direction_share'] or 0:.0%}) | {b['preferred_edge_type']} |")
    L += ["", "## Families", ""]
    for f, v in sorted(d["families"].items(), key=lambda kv: -kv[1]["sp_maps_using"]):
        top = ", ".join(f"{m} {s:.0%}" for m, s in list(v["materials"].items())[:6])
        nb = ", ".join(f"{k} {s:.0%}" for k, s in v["neighbour_families"].items())
        L.append(f"- **{f}**: in {v['sp_maps_using']} campaign maps, median {v['median_share_when_used']:.0%} of a map's floor when used. "
                 f"Palette: {top}. Borders: {nb or '-'}.")
    pr = sorted(((m, v["score"]) for m, v in d["priority"].items() if v["evidence"] >= 100), key=lambda kv: -kv[1])
    L += ["", "## Priority (who overlays whom, materials with >= 100 weighted blended contacts)", "",
          ", ".join(f"{m} {s:+.2f}" for m, s in pr),
          "", "## Materials that never touch (need a buffer)", ""]
    for b in d["never_touch"][:30]:
        bm = ", ".join(f"{k} {v:.0%}" for k, v in b["buffer_materials"].items()) or "(different areas)"
        L.append(f"- {b['a']} / {b['b']} (both in {b['cooccur_sp_maps']} maps): between them {bm}")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    data = build(mine())
    C.save_json("floors.json", data)
    C.save_section("floors.md", md(data))
    print("floors: blends", len(data["blend"]), "| families", len(data["families"]), "| never-touch", len(data["never_touch"]),
          "| edge rule match", data["edge_pieces"]["exact_match_share_sp"],
          "| variation match", data["variation_rule"]["tile_matches_editor_formula_all"])
