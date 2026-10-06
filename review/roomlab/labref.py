"""Westwood's campaign rooms for the room lab: found again from rules/rooms/westwood.json's index (campaign maps only,
Con/War/Wiz, each room once; the great rooms the finder misses read by hand with void bounds, as the index says), then
measured (review/roomlab/westwood_features.json) and rendered as the lab renders ours (review/out/roomlab/_westwood/).

    py review/roomlab/labref.py features            re-measure every room (writes westwood_features.json)
    py review/roomlab/labref.py gallery [type ...]  render each type's rooms (cached; every type by default)
"""
import collections, json, os, sys
import labenv as E
C, MD = E.C, E.MD


def index():
    with open(E.WW_INDEX, encoding="utf-8") as f:
        return E.curate(json.load(f)["index"])


def _centre(cells):
    xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
    return [round(sum(xs) / len(xs)), round(sum(ys) / len(ys))]


def rooms_of_map(name, entries):
    """[(entry, m, r)] for the index entries of one map: the checker's room with the same floor tiles and centre."""
    m = MD.load(MD.corpus_json(name))
    out = []
    plain = None
    void = None
    for e in entries:
        if e.get("by_hand"):
            void = void or C.find_rooms(m, max_tiles=1500, void_bounds=True)
            cands = void
        else:
            plain = plain or C.find_rooms(m, max_tiles=1500)
            cands = plain
        hit = next((r for r in cands if r["tiles"] == e["tiles"] and _centre(r["cells"]) == e["centre"]), None)
        if hit is None:
            hit = next((r for r in cands if abs(r["tiles"] - e["tiles"]) <= 2 and
                        abs(_centre(r["cells"])[0] - e["centre"][0]) + abs(_centre(r["cells"])[1] - e["centre"][1]) <= 2), None)
        if hit is None:
            print(f"  not found again: {name} {e['type']} at {e['centre']}"); continue
        out.append((e, m, hit))
    return out


def _measure_map(args):
    name, entries = args
    import metrics
    res = []
    for e, m, r in rooms_of_map(name, entries):
        f, d = metrics.features(m, r, e["type"])
        res.append(dict(map=name, type=e["type"], culture=e["culture"], centre=e["centre"], tiles=e["tiles"],
                        by_hand=bool(e.get("by_hand")), features=f, details=d))
    return res


def build_features():
    """Measures every indexed Westwood room; writes review/roomlab/westwood_features.json."""
    from concurrent.futures import ProcessPoolExecutor
    by = collections.defaultdict(list)
    for e in index(): by[e["map"]].append(e)
    with ProcessPoolExecutor(6) as pool:
        rooms = [r for rs in pool.map(_measure_map, sorted(by.items())) for r in rs]
    rooms.sort(key=lambda r: (r["type"], r["map"], r["centre"]))
    with open(E.WW_FEATURES, "w", encoding="utf-8") as f:
        json.dump(dict(source="rules/rooms/westwood.json index (Westwood's campaign maps, Con/War/Wiz, each room once)",
                       measured_by="review/roomlab/metrics.py features()", rooms=rooms), f, indent=0)
    print(f"{len(rooms)} Westwood rooms measured -> {E.rel(E.WW_FEATURES)}")
    return rooms


def gallery_dir(typ):
    return os.path.join(E.WW_OUT, typ)


def type_scale(typ):
    """The picture scale for a type: the median Westwood room of the type fits the canvas with room to spare (a room
    1.25 times as long, the kit's scale, still fits), from the gallery's boxes. Rooms of the pool stand in for a thin
    type."""
    return gallery(typ)["scale"]


def gallery(typ, log=print):
    """Renders Westwood's rooms of the type (and of its pool when it has under metrics.MIN_WW), cached in
    review/out/roomlab/_westwood/<type>/: one PNG per room and gallery.json. Returns the gallery's record."""
    import labrender as R
    import metrics
    d = gallery_dir(typ)
    meta_path = os.path.join(d, "gallery.json")
    pool_rooms, note = metrics.pool(typ)
    keys = {(r["map"], tuple(r["centre"])) for r in pool_rooms}
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f: meta = json.load(f)
        if meta.get("version") == 2 and meta.get("note") == note and \
                {(x["map"], tuple(x["centre"])) for x in meta["rooms"]} <= keys and \
                all(os.path.exists(os.path.join(d, x["file"])) for x in meta["rooms"]):
            return meta
    if os.path.isdir(d):
        for fn in os.listdir(d): os.remove(os.path.join(d, fn))
    os.makedirs(d, exist_ok=True)
    by = collections.defaultdict(list)
    for e in index():
        if (e["map"], tuple(e["centre"])) in keys: by[e["map"]].append(e)
    found = []
    for name in sorted(by):
        for e, m, r in rooms_of_map(name, by[name]):
            found.append((e, m, r))
    # one scale for the type: the median fit over the type's own rooms (or the pool's)
    fits = [R.fit_scale(r["cells"]) for e, m, r in found if e["type"] == typ] or [R.fit_scale(r["cells"]) for e, m, r in found]
    fits.sort()
    scale = round(max(0.3, min(1.6, fits[len(fits) // 2] / 1.25)), 3) if fits else 1.0
    rooms = []
    for e, m, r in found:
        full, bare = R.westwood_renders(m)
        pic, s = R.picture(full, bare, r["cells"], scale)
        fn = f"{e['type']}_{e['map']}_{e['centre'][0]}_{e['centre'][1]}.png"
        pic.save(os.path.join(d, fn))
        rooms.append(dict(file=fn, map=e["map"], type=e["type"], culture=e["culture"], centre=e["centre"],
                          tiles=e["tiles"], fit=round(R.fit_scale(r["cells"]), 3), scale=round(s, 3),
                          own=e["type"] == typ))
        log(f"  {fn}")
    meta = dict(version=2, type=typ, scale=scale, note=note, rooms=rooms)
    with open(meta_path, "w", encoding="utf-8") as f: json.dump(meta, f, indent=1)
    return meta


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "features":
        build_features()
    elif len(sys.argv) > 1 and sys.argv[1] == "gallery":
        for t in sys.argv[2:] or E.types():
            g = gallery(t)
            print(f"{t}: {len(g['rooms'])} rooms at scale {g['scale']}")
    else:
        print(__doc__)
