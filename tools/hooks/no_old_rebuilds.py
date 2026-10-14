"""Claude Code PreToolUse hook: never rebuild, QA-gate or install an old (frozen) map without the user asking for it.

The user's strategy (2026-10-04, restated 2026-10-13): "use the improved process to generate new maps instead of trying
to go back and fix old ones that were wrong from the beginning. Test maps like ModLab should be rebuilt because we need
to specifically test the functions. But not old, out-of-date random maps."

Which designs are test maps and which are frozen: mapgen/designs/status.json. A design not listed there is a new map.
Blocked, for a frozen design (by design name or by its map name):
    py [flags] .../mapgen/designs/<design>.py ...        building it
    py tests/qa.py <design or path> ...                    its QA gate (which builds it)
    py mapgen/install.py <out dir> <Map> ...               installing it into the game
and the same inside a shell script the command runs (.sh, .ps1, .bat, .cmd), or a loop over names that names one.
Allowed: reading or editing the files, the labs, the self-test, test maps, new maps. When the user asks for one old map
by name, prefix the command with NOX_REBUILD_OK=<design> (several: comma-separated).

Reads the hook's JSON on stdin; exit 2 with the reason on stderr blocks the call (Claude sees the reason).
"""
import json, os, re, shlex, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATUS = os.path.join(HERE, "..", "..", "mapgen", "designs", "status.json")
INTERP = re.compile(r"^(?:.*/)?(?:py|python3?)(?:\.exe)?$", re.I)
SCRIPT = re.compile(r'"([^"]+\.(?:sh|ps1|bat|cmd))"|\'([^\']+\.(?:sh|ps1|bat|cmd))\'|([^\s"\']+\.(?:sh|ps1|bat|cmd))\b')
LEAD = {"do", "then", "else", "time", "(", "{", "&", "exec"}


def load():
    try:
        s = json.load(open(STATUS, encoding="utf-8"))
    except Exception:
        return {}, {}
    frozen = {k.lower(): v for k, v in s.get("frozen", {}).items()}
    maps = {v.lower(): k for k, v in frozen.items()}
    return frozen, maps


def allowed(cmd):
    m = re.findall(r"NOX_REBUILD_OK\s*=\s*[\"']?([\w,]+)", cmd)
    return {x.lower() for g in m for x in g.split(",") if x}


def stem(path):
    b = path.strip("\"'").replace("\\", "/").rstrip("/").split("/")[-1]
    return b[:-3].lower() if b.lower().endswith(".py") else b.lower()


def segments(cmd):
    """The command's simple commands, split at ; & | and new lines outside quotes, each split into words."""
    c = cmd.replace("\\", "/")
    parts, cur, q = [], "", None
    for ch in c:
        if q:
            cur += ch
            if ch == q: q = None
        elif ch in "\"'":
            q = ch
            cur += ch
        elif ch in ";|&\n":
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    out = []
    for seg in parts:
        try:
            w = shlex.split(seg, posix=True)
        except ValueError:
            w = seg.split()
        if w: out.append(w)
    return out


def named(c, frozen, maps):
    words = set(re.findall(r"[A-Za-z0-9_]+", c.lower()))
    return {d for d in frozen if d in words} | {maps[w] for w in words if w in maps}


def hits(cmd, frozen, maps, depth=0):
    c = cmd.replace("\\", "/")
    out = set()
    for w in segments(cmd):
        while w and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w[0]) or w[0] in LEAD):
            w = w[1:]                                     # env assignments, `do`, `then` ...
        if not w or not INTERP.match(w[0]): continue
        rest = w[1:]
        while rest and rest[0].startswith("-"):
            rest = rest[2:] if rest[0] in ("-W", "-X") else rest[1:]
        if not rest or not rest[0].lower().endswith(".py"): continue
        script, args = rest[0], [a for a in rest[1:] if not a.startswith("-")]
        name = stem(script)
        low = "/" + script.lower()
        if "$" in script and "designs" in low:          # a loop feeding design scripts from a variable
            out |= named(c, frozen, maps)
        elif name in frozen and ("/designs/" in low or script.count("/") == 0):
            out.add(name)                               # a design run directly
        elif name == "qa" and args:                     # the QA gate builds the design it is given
            if stem(args[0]) in frozen: out.add(stem(args[0]))
            if "$" in args[0]: out |= named(c, frozen, maps)
        elif name == "install":                         # installing a map into the game
            for a in args[:2]:
                if stem(a) in frozen: out.add(stem(a))
                if stem(a) in maps: out.add(maps[stem(a)])
                if "$" in a: out |= named(c, frozen, maps)
    if depth == 0:                                      # the scripts the command runs
        for m in SCRIPT.finditer(c):
            f = next(g for g in m.groups() if g)
            if os.path.isfile(f):
                try:
                    out |= hits(open(f, encoding="utf-8", errors="replace").read(), frozen, maps, 1)
                except OSError:
                    pass
    return out


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not cmd: return 0
    frozen, maps = load()
    if not frozen: return 0
    bad = sorted(hits(cmd, frozen, maps) - allowed(cmd))
    if not bad: return 0
    names = ", ".join(f"{d} ({frozen[d]})" for d in bad)
    sys.stderr.write(
        f"Blocked: this would rebuild, QA-gate or install old map(s): {names}. The user's rule: old maps are not rebuilt "
        f"or patched; the improved process makes NEW maps, and only test maps (ModLab, the gauntlets, the labs) are "
        f"rebuilt to test functions (mapgen/designs/status.json). Do not work around this. Only if the user has asked "
        f"for this map by name, prefix the command with NOX_REBUILD_OK=<design>.\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
