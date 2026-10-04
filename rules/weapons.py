"""How Nox's weapons fire: every weapon's USE handler and what it creates, and every missile's speed, update, collide
and damage, read from the game's object database (thing.bin, decrypted with noxcrypt to thing.dec).

thing.bin records each object as its name then "KEY = value" properties. A weapon's USE line names the handler and
its arguments:
  WandUse <delay> <projectile> <?> SINGLE_SHOT|MULTI_SHOT <sound> <charges>   (fires a missile object)
  WandCastUse <charges> <?> <spell>                                             (casts a spell)
  BowUse                                                                        (fires arrows from the quiver)
and a missile's UPDATE / COLLIDE lines its flight and impact.

    py rules/weapons.py <thing.dec>      writes rules/out/weapons.json and prints the tables
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = re.compile(r"^([A-Z][A-Z0-9_]+) = (.*)$")
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,}$")


SPLIT = re.compile(r"([A-Z][A-Z0-9_]+) = ")


def _props(s):
    """KEY = value pairs in one extracted string: neighbouring properties run together where a length byte happens to
    be printable ("WOOD'CLASS = WAND+..."), so split at every KEY = and trim stray bytes off each value."""
    out = []
    ms = list(SPLIT.finditer(s))
    for k, m in enumerate(ms):
        end = ms[k + 1].start() if k + 1 < len(ms) else len(s)
        val = s[m.end():end]
        val = re.sub(r"[^A-Za-z0-9_.+\- ]+$", "", val)          # trailing length bytes
        if k + 1 < len(ms):
            val = re.sub(r".$", "", val) if val and not val[-1:].isspace() and len(val) > 1 and not re.match(r".*[A-Za-z0-9]$", val) else val
        out.append((m.group(1), val.strip()))
    return out


def records(path):
    data = open(path, "rb").read()
    strs = [m.group().decode("latin-1").strip() for m in re.finditer(rb"[ -~]{3,}", data)]
    out, cur = {}, None
    BARE = ("DRAW", "PRETTYIMAGE", "MENUICON", "CLIENTUPDATE", "LIGHTPENUMBRA")    # keyword lines whose value follows
    for k, s in enumerate(strs):
        nxt = strs[k + 1] if k + 1 < len(strs) else ""
        prev = strs[k - 1] if k else ""
        if prev in BARE:                         # the draw function's (or icon's) name, not a new record
            if cur is not None: cur.setdefault(prev, s)
            continue
        if prev.endswith("GNHT") and NAME.match(s):           # each object record starts with the THNG tag
            cur = out.setdefault(s, {})
            continue
        if cur is None: continue
        for key, val in _props(s):
            cur.setdefault(key, val)
    return out


def main(path):
    things = records(path)
    weapons, missiles = {}, {}
    for name, p in things.items():
        cls = p.get("CLASS", "")
        if ("WEAPON" in cls or "WAND" in cls) and "MISSILE" not in cls and p.get("USE"):
            weapons[name] = dict(cls=cls, subclass=p.get("SUBCLASS", ""), use=p.get("USE"), damage=p.get("DAMAGE", ""))
        if "MISSILE" in cls or p.get("UPDATE", "").startswith(("Projectile", "Harpoon", "Arrow", "Homing", "Spell")):
            missiles[name] = dict(cls=cls, speed=p.get("SPEED"), update=p.get("UPDATE", ""), collide=p.get("COLLIDE", ""),
                                  subclass=p.get("SUBCLASS", ""), mass=p.get("MASS"))
    for w in weapons.values():
        u = w["use"].split()
        w["handler"] = u[0]
        if u[0] == "WandUse" and len(u) >= 3:
            w["fires"] = u[2]; w["delay"] = u[1]; w["mode"] = u[4] if len(u) > 4 else ""
            w["projectile"] = missiles.get(u[2])
        elif u[0] == "WandCastUse" and len(u) >= 4:
            w["casts"] = u[3]; w["charges"] = u[1]
    out = dict(weapons=weapons, missiles=missiles)
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    with open(os.path.join(HERE, "out", "weapons.json"), "w") as f: json.dump(out, f, indent=1)
    print(f"{len(weapons)} weapons with a USE handler, {len(missiles)} missiles\n")
    print("weapon -> handler -> what it fires")
    for n, w in sorted(weapons.items(), key=lambda kv: (kv[1]["handler"], kv[0])):
        tail = (f"fires {w['fires']} (delay {w['delay']} frames, {w['mode']}; missile speed {(w['projectile'] or {}).get('speed')}, "
                f"collide {(w['projectile'] or {}).get('collide')})" if "fires" in w else
                f"casts {w['casts']} ({w['charges']} charges)" if "casts" in w else w["use"])
        print(f"  {n:24s} {w['handler']:12s} {tail}")
    print("\nmissiles: speed / update / collide")
    for n, mm in sorted(missiles.items()):
        print(f"  {n:24s} {str(mm['speed']):5s} {mm['update']:28s} {mm['collide']}")


if __name__ == "__main__":
    main(sys.argv[1])
