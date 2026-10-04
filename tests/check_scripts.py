"""Compile-checks a generated map's Go scripts (<map>_scripts/ beside the map) against the NoxScript 4 API the
installed OpenNox ships (v1.9.0-alpha13 bundles github.com/noxworld-dev/noxscript/ns/v4 v4.16.1: read from
opennox-server.exe), with `go vet`. A method from a newer NoxScript (such as Obj.Vel) fails here before it fails in the
game ("undefined method").

    py tests/check_scripts.py mapgen/out/NpcLab_scripts [--go path\\to\\go.exe] [--ns v4.16.1]

Go is not installed system-wide; pass --go (a portable Go works) or set GO. Module downloads go to GOPATH/GOCACHE
under the temp folder unless set.
"""
import argparse, os, re, shutil, subprocess, sys, tempfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scripts")
    ap.add_argument("--go", default=os.environ.get("GO", "go"))
    ap.add_argument("--ns", default="v4.16.1")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="nscheck_")
    pkg = os.path.join(tmp, "lab")
    os.makedirs(pkg)
    for fn in os.listdir(a.scripts):
        if fn.endswith(".go"):
            src = open(os.path.join(a.scripts, fn), encoding="utf-8").read()
            src = re.sub(r"^package \w+", "package lab", src, count=1, flags=re.M)
            open(os.path.join(pkg, fn), "w", encoding="utf-8").write(src)
    open(os.path.join(tmp, "go.mod"), "w").write(f"module nscheck\n\ngo 1.22\n\nrequire github.com/noxworld-dev/noxscript/ns/v4 {a.ns}\n")
    env = dict(os.environ, GOTOOLCHAIN="local", GOFLAGS="-mod=mod")
    env.setdefault("GOPATH", os.path.join(tempfile.gettempdir(), "nscheck_gopath"))
    env.setdefault("GOCACHE", os.path.join(tempfile.gettempdir(), "nscheck_gocache"))
    try:
        subprocess.run([a.go, "mod", "tidy"], cwd=tmp, env=env, capture_output=True, text=True)
        r = subprocess.run([a.go, "vet", "./lab"], cwd=tmp, env=env, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        print(out or f"OK: {a.scripts} compiles against noxscript/ns/v4 {a.ns}")
        sys.exit(r.returncode)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
