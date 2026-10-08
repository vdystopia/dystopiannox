"""Where the OpenNox client would crash: the most times one screen row crosses the edge of the player's sight [CL-1].

    py tests/sightrows.py <map.map> [--step 230] [--at X,Y] [--png out.png]

OpenNox (v1.9.0-alpha13) blacks out what the player cannot see one screen row at a time: it lists where each row
crosses the edge of his sight, up to 32, and its filler (client_draw.go sub_4C5500) reads one pair past the list, so a
row with 31 or more crossings panics ("index out of range [1] with length 1") and the client dies on the spot. A
level forest edge (one running straight across the screen) is a saw whose valleys sit on one row: seen from a few
hundred pixels above or below, a long one gives 40 or more (Thornwick 2026-10-08 crashed as it loaded). Westwood's
maps stay under it almost everywhere; mapgen's Land.unlevel_edges breaks such edges into 45-degree bays.

This approximates the client's sight (every wall blocks it, as the forest does; doors and windows are left out) on the
1920x1080 view of the user's map-test launcher, from a point every `step` pixels on the map's floor, and counts each
row's changes between seen and unseen. It over-counts: measured against the game (the map loaded with its start moved
to the point, 2026-10-08, Thornwick builds of 10-05 and 10-08) points of 34, 40, 44, 44, 48 and 48 crashed the client;
points of 32 (8), 34 (4), 36 (2), 38, 40 and 42 did not, nor anything lower. So `CRASH` (the gate fails) at 33 or more,
`RISK` (a look) at 31-32.
"""
import argparse, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import noxmap

G = 23                                     # pixels per grid cell
VIEW = (1920, 1080)
CRASH, RISK = 33, 31
# the half-walls a wall piece is drawn from, by facing (bits: 1 to the top right corner, 2 top left, 4 bottom right,
# 8 bottom left; client/sight.go newFromWall): 0 and 1 the two diagonals, 2 a cross, 3-6 tees, 7-10 corners
HALVES = {0: 1 | 8, 1: 2 | 4, 2: 15, 3: 1 | 2 | 8, 4: 2 | 4 | 8, 5: 1 | 2 | 4, 6: 1 | 4 | 8, 7: 1 | 2, 8: 2 | 8,
          9: 4 | 8, 10: 1 | 4}


def segments(walls):
    out = []
    for x, y, d, *_ in walls:
        X, Y = x * G, y * G
        cx, cy = X + 11, Y + 11
        h = HALVES.get(d & 0x7F, 15)
        for bit, (ex, ey) in ((1, (X + G, Y)), (2, (X, Y)), (4, (X + G, Y + G)), (8, (X, Y + G))):
            if h & bit: out.append((cx, cy, ex, ey))
    return np.array(out, float).reshape(-1, 4)


def sight(segs, px, py, view=VIEW, rays=4096):
    """The seen/unseen mask of the view centred on (px, py) and the crossings of each of its rows."""
    W, H = view
    x0, y0 = px - W / 2, py - H / 2
    m = ((np.maximum(segs[:, 0], segs[:, 2]) > x0 - 50) & (np.minimum(segs[:, 0], segs[:, 2]) < x0 + W + 50) &
         (np.maximum(segs[:, 1], segs[:, 3]) > y0 - 50) & (np.minimum(segs[:, 1], segs[:, 3]) < y0 + H + 50))
    s = segs[m]
    ang = (np.arange(rays) + 0.5) * 2 * np.pi / rays
    dx, dy = np.cos(ang)[:, None], np.sin(ang)[:, None]
    if len(s):
        ax, ay = s[:, 0] - px, s[:, 1] - py
        ex, ey = s[:, 2] - s[:, 0], s[:, 3] - s[:, 1]
        den = dx * ey - dy * ex
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (ax * ey - ay * ex) / den
            u = (ax * dy - ay * dx) / den
            t = np.where((den != 0) & (t > 0) & (u >= 0) & (u <= 1), t, np.inf)
        hit = t.min(axis=1)
    else:
        hit = np.full(rays, np.inf)
    ys, xs = np.mgrid[0:H, 0:W]
    rx, ry = xs + x0 + 0.5 - px, ys + y0 + 0.5 - py
    ai = ((np.arctan2(ry, rx) % (2 * np.pi)) / (2 * np.pi) * rays).astype(int) % rays
    seen = np.hypot(rx, ry) < hit[ai]
    pad = np.pad(seen, ((0, 0), (1, 1)))
    return seen, (pad[:, 1:] != pad[:, :-1]).sum(axis=1)


def scan(map_path, step=230):
    """[(x, y, most crossings on a row, that row)] from a point every `step` px on the map's floor."""
    s = noxmap.sections(map_path)
    segs = segments(noxmap.walls(s["WallMap"]))
    tiles = {(t[0], t[1]) for t in noxmap.tiles(s["FloorMap"])}
    pts = sorted({(tx * G // step * step + step // 2, ty * G // step * step + step // 2) for tx, ty in tiles})
    out = []
    for x, y in pts:
        _, cr = sight(segs, x, y)
        out.append((x, y, int(cr.max()), int(cr.argmax())))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map"); ap.add_argument("--step", type=int, default=230)
    ap.add_argument("--at", help="one point X,Y instead of the scan"); ap.add_argument("--png")
    a = ap.parse_args()
    if a.at:
        x, y = map(float, a.at.split(","))
        segs = segments(noxmap.walls(noxmap.sections(a.map)["WallMap"]))
        seen, cr = sight(segs, x, y)
        print(f"({x:.0f}, {y:.0f}): {cr.max()} crossings on screen row {cr.argmax()}")
        if a.png:
            from PIL import Image, ImageDraw
            img = Image.fromarray(np.where(seen, 200, 40).astype(np.uint8)).convert("RGB")
            d = ImageDraw.Draw(img)
            x0, y0 = x - VIEW[0] / 2, y - VIEW[1] / 2
            for sx, sy, ex, ey in segs:
                d.line([(sx - x0, sy - y0), (ex - x0, ey - y0)], fill=(255, 0, 0), width=3)
            d.line([(0, int(cr.argmax())), (VIEW[0], int(cr.argmax()))], fill=(0, 255, 0))
            img.save(a.png)
        return
    res = scan(a.map, a.step)
    bad = sorted((r for r in res if r[2] >= RISK), key=lambda r: -r[2])
    print(f"{os.path.basename(a.map)}: {len(res)} points, most crossings {max(r[2] for r in res)}; "
          f"{sum(r[2] >= CRASH for r in res)} at {CRASH}+ (crash), {sum(RISK <= r[2] < CRASH for r in res)} at {RISK}-{CRASH - 1}")
    for x, y, c, row in bad: print(f"  ({x}, {y}) cells ({x // G}, {y // G}): {c} on screen row {row}")
    sys.exit(1 if any(r[2] >= CRASH for r in res) else 0)


if __name__ == "__main__":
    main()
