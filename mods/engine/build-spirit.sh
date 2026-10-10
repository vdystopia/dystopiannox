#!/bin/bash
# Build OpenNox (v1.9.0-alpha13 + spirit.patch) for 32-bit Windows from Git Bash, no MSYS2 install needed.
# It does the same as `go run ./internal/noxbuild` (the upstream build tool), which breaks when the
# path contains a space (e.g. C:\Users\Dystopian Machine): it passes -trimpath=<dir> unquoted.
#
# usage: build-spirit.sh <opennox checkout> <output dir> <target...>
#   targets: client-hd (opennox-hd.exe), client (opennox.exe), client-hd-debug, server (opennox-server.exe)
#   NAME_HD / NAME_SD / NAME_HDD / NAME_SRV override the output names (without .exe).
# Tools (portable, see SPIRIT.md for the download links); set these to where you unpacked them:
#   GO_DIR     folder holding go.exe            (Go 1.21 or newer; tested with 1.23.4 windows/amd64)
#   MINGW_DIR  WinLibs i686 "mingw32" folder    (tested: GCC 13.2.0 i686-posix-dwarf msvcrt r5)
#   SDL2_DIR   SDL2-2.32.10 folder from SDL2-devel-2.32.10-mingw.zip
#   OPENAL_DIR openal-soft-1.25.2-bin folder
# Use forward-slash Windows paths without spaces for SDL2_DIR / OPENAL_DIR (8.3 short names work, e.g. C:/Users/DYSTOP~1/...).
set -e
: "${GO_DIR:?set GO_DIR}" "${MINGW_DIR:?set MINGW_DIR}" "${SDL2_DIR:?set SDL2_DIR}" "${OPENAL_DIR:?set OPENAL_DIR}"
export PATH="$MINGW_DIR/bin:$GO_DIR:$PATH"
export CC=gcc CXX=g++ GOOS=windows GOARCH=386 CGO_ENABLED=1 GOTOOLCHAIN=local
export CGO_CFLAGS_ALLOW='(-fshort-wchar)|(-fno-strict-aliasing)|(-fno-strict-overflow)'
export CGO_CFLAGS="-O2 -I$SDL2_DIR/i686-w64-mingw32/include -I$OPENAL_DIR/include"
export CGO_LDFLAGS="-L$SDL2_DIR/i686-w64-mingw32/lib -L$OPENAL_DIR/libs/Win32"
SRC=$1; OUT=$2; shift 2
mkdir -p "$OUT"
cd "$SRC/src"
VP=github.com/noxworld-dev/opennox/v1/internal/version
LD="-X '$VP.commit=${NOX_COMMIT:-57827e6}' -X '$VP.version=${NOX_VERSION:-v1.9.0-alpha13}'"
for t in "$@"; do
  case $t in
    client-hd)       name=${NAME_HD:-opennox-hd};        tags="highres,guiapp"; ld="$LD -H windowsgui";;
    client)          name=${NAME_SD:-opennox};           tags="guiapp";         ld="$LD -H windowsgui";;
    client-hd-debug) name=${NAME_HDD:-opennox-hd-debug}; tags="highres";        ld="$LD";;
    server)          name=${NAME_SRV:-opennox-server};   tags="server";         ld="$LD";;
    *) echo "unknown target $t"; exit 1;;
  esac
  echo "=== building $name ($tags)"
  go build -ldflags="$ld" -tags "$tags" -trimpath -o "$OUT/$name.exe" ./cmd/opennox
done
