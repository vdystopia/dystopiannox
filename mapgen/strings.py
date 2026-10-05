"""The game's text table with our maps' own lines in it: dialogue, journal entries and shop greetings, without
recorded audio.

Nox scripts show text by key (TellStory, JournalEntry, a shopkeeper's greeting: "Con02:BarkeeperDefault"), looked up
in the game's string table nox.csf. OpenNox reads nox.csf.json instead when that file is beside it
(opennox-lib strman.ReadFile tries "<name>.csf.json" first), in its own JSON form. This tool writes that file: every
string of nox.csf, read the way OpenNox reads it (strman/csf.go: UTF-16 inverted bit by bit, runs of spaces folded),
plus the lines of each installed generated map (maps/<Name>/<Name>.strings.json: {"<Name>:Key": "text"}).

    py mapgen/strings.py [--nox "C:\\GOG Games\\Nox"] [--check]       write nox.csf.json (--check: only report)
    py mapgen/strings.py --remove                                      delete it: the game reads nox.csf again

The original nox.csf is never changed. Keys are case-insensitive in the game; each map's keys start with its name,
except creatures' titles ("NPC:<script name>"), which are shared: a title Westwood already has stays Westwood's, and
two maps may share one only with the same text.
"""
import argparse, glob, json, os, struct, sys

NOX = r"C:\GOG Games\Nox"


def _fold_spaces(s):
    """strman.filterSpaces: drop leading spaces and those before a line break or the end, fold runs into one."""
    out, prev, start = [], None, True
    for c in s:
        if c == " ":
            if prev != " " and not start:
                out.append(c); prev = c; start = False
        elif c in "\n\t":
            if prev == " ": out.pop()
            out.append(c); prev = c; start = True
        else:
            out.append(c); prev = c; start = False
    if prev == " ": out.pop()
    return "".join(out)


def read_csf(path):
    """(lang, [{"id", "vals": [{"str"[, "str2"]}]}]) from a Nox CSF file."""
    b = open(path, "rb").read()
    if b[0:4][::-1] != b"CSF ": raise ValueError(f"{path}: not a CSF file")
    vers, n_ent, n_var = struct.unpack_from("<III", b, 4)
    lang = struct.unpack_from("<I", b, 20)[0] if vers >= 2 else 0
    o = 24 if vers >= 2 else 20
    entries = []
    while o < len(b):
        if b[o:o + 4][::-1] != b"LBL ": raise ValueError(f"bad section at {o}")
        nv, ln = struct.unpack_from("<II", b, o + 4); o += 12
        name = b[o:o + ln].decode("latin1"); o += ln
        vals = []
        for _ in range(nv):
            sect = b[o:o + 4][::-1].lower(); wn = struct.unpack_from("<I", b, o + 4)[0]; o += 8
            raw = struct.unpack_from(f"<{wn}H", b, o); o += 2 * wn
            s = _fold_spaces(bytes(b"".join(struct.pack("<H", (~c) & 0xFFFF) for c in raw)).decode("utf-16-le", "replace"))
            v = {"str": s}
            if sect == b"strw":
                sz = struct.unpack_from("<I", b, o)[0]; o += 4
                if sz: v["str2"] = b[o:o + sz].decode("latin1"); o += sz
            vals.append(v)
        entries.append({"id": name, "vals": vals})
    return lang, entries


def map_lines(nox):
    """{key: text} from every installed map's <Name>.strings.json."""
    out, where = {}, {}
    for p in sorted(glob.glob(os.path.join(nox, "maps", "*", "*.strings.json"))):
        for k, v in json.load(open(p, encoding="utf-8")).items():
            # shared keys (a creature's title, "NPC:<script name>") must read the same in every map that has them
            if k in out and out[k] != v:
                sys.exit(f"{k} is {out[k]!r} in {where[k]} but {v!r} in {os.path.basename(p)}: rename one creature")
            out[k], where[k] = v, os.path.basename(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nox", default=NOX)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    dst = os.path.join(a.nox, "nox.csf.json")
    if a.remove:
        if os.path.exists(dst): os.remove(dst)
        print(f"removed {dst}: the game reads nox.csf again"); return
    lang, entries = read_csf(os.path.join(a.nox, "nox.csf"))
    ours = map_lines(a.nox)
    have = {e["id"].lower() for e in entries}
    # a title Westwood already has ("NPC:Clyde") stays Westwood's
    ours = {k: v for k, v in ours.items() if not (k.lower().startswith("npc:") and k.lower() in have)}
    clash = [k for k in ours if k.lower() in have]
    if clash: sys.exit(f"keys already in nox.csf: {clash[:5]}")
    entries += [{"id": k, "vals": [{"str": v}]} for k, v in ours.items()]
    print(f"nox.csf: {len(entries) - len(ours)} strings (language {lang}); maps' lines: {len(ours)}")
    if a.check: return
    tmp = dst + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump({"lang": lang, "entries": entries}, f, ensure_ascii=False)
    json.load(open(tmp, encoding="utf-8"))           # it must parse, or the game will not start
    os.replace(tmp, dst)
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
