#!/bin/bash
# build.sh <opennox checkout dir> <output dir> [targets...]
#
# Cross-compiles the patched OpenNox for Windows in Docker (no local Go or MinGW needed).
# If <opennox checkout dir> does not exist it is cloned from GitHub at v1.9.0-alpha13 and
# sight-row-overflow.patch is applied. Default targets: opennox opennox-hd opennox-debug opennox-server.
# GIT_TAG=<version> sets the version string the game shows (default v1.9.0-alpha13-sightfix).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
if [ ! -d "$1" ]; then
  git clone -q https://github.com/noxworld-dev/opennox.git "$1"
  git -C "$1" checkout -q v1.9.0-alpha13
  git -C "$1" apply "$HERE/sight-row-overflow.patch"
fi
SRC=$(cd "$1" && pwd); OUT=$(mkdir -p "$2" && cd "$2" && pwd); shift 2
TARGETS=${*:-opennox opennox-hd opennox-debug opennox-server}
docker build -q -t opennox-winbuild:go1.21.5 "$HERE" >/dev/null
docker run --rm -e GIT_TAG="${GIT_TAG:-v1.9.0-alpha13-sightfix}" -v "$SRC:/src:ro" -v "$OUT:/out" \
  -v opennox-gomod:/go/pkg/mod -v opennox-gocache:/root/.cache/go-build opennox-winbuild:go1.21.5 bash -c "set -e
  cp -a /src /work; cd /work/src
  go run ./internal/noxbuild --os=windows -o /out $TARGETS
  for f in /out/*.exe; do echo \"\$f imports:\" \$(i686-w64-mingw32-objdump -p \$f | grep 'DLL Name' | awk '{print \$3}'); done"
