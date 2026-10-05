"""Builds, checks, installs and smoke-tests a campaign of linked maps, the chain's end first (an exit reads its next
map's PlayerStart from that map's build: kit/story.StoryMap.arrival).

    py tests/campaign.py [--go path\\to\\go.exe] [--no-smoke] [design ...]

Default chain: thornwick > tnorth > rimehold > rimepass > emberhollow > ashroad (built in reverse). Prints one line
per map: the checker's result, the scripts' compile, the server's load and self-checks.
"""
import argparse, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAIN = ["thornwick", "tnorth", "rimehold", "rimepass", "emberhollow", "ashroad"]
GO = os.environ.get("GO", r"C:/Users/DYSTOP~1/AppData/Local/Temp/claude/C--GOG-Games-Nox/2ef10e66-3ba1-4500-9040-634cb857884d/scratchpad/tools/go/bin/go.exe")


def run(args):
    r = subprocess.run([sys.executable] + args, cwd=REPO, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("designs", nargs="*")
    ap.add_argument("--go", default=GO)
    ap.add_argument("--no-smoke", action="store_true")
    a = ap.parse_args()
    ok = True
    for d in reversed(a.designs or CHAIN):
        design = os.path.join("mapgen", "designs", d + ".py")
        _, out = run([design])
        chk = re.search(r"CHECK (\w+): (\d+) error\(s\), (\d+) warning\(s\)", out)
        if not chk:
            print(f"{d}: BUILD FAILED\n{out[-800:]}"); ok = False; continue
        name, errs, warns = chk.group(1), int(chk.group(2)), int(chk.group(3))
        out_dir = os.path.join("mapgen", "out", d)
        line = f"{name:10} check {errs} err {warns} warn"
        sd = os.path.join(out_dir, name + "_scripts")
        if os.path.isdir(sd):
            rc, o = run([os.path.join("tests", "check_scripts.py"), sd, "--go", a.go])
            line += " | scripts " + ("ok" if rc == 0 else "FAIL")
            ok &= rc == 0
        rc, o = run([os.path.join("mapgen", "install.py"), out_dir, name])
        line += " | installed" if rc == 0 else " | INSTALL FAIL"
        if not a.no_smoke:
            rc, o = run([os.path.join("tests", "server_smoke.py"), design])
            loaded = re.search(r"loaded=(\w+) problems=(\d+)", o)
            checks = re.findall(r"self-check: (.*)", o)
            line += f" | server {'ok' if rc == 0 else 'FAIL'}" + (f" ({'; '.join(c.strip() for c in checks)})" if checks else "")
            ok &= rc == 0
        ok &= errs == 0
        print(line, flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
