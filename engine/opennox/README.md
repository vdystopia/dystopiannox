# OpenNox client fix: sight-row overflow panic

A local patch to [OpenNox](https://github.com/noxworld-dev/opennox) v1.9.0-alpha13 (the version installed in
`C:\GOG Games\Nox`). It fixes a client crash that our generated maps trigger, at its source in the engine.
The map-side workaround (CL-1, `tests/sightrows.py`, commit e675aa7) stays: it keeps maps playable on
unpatched OpenNox clients.

Files:

- `sight-row-overflow.patch`: `git diff v1.9.0-alpha13..fix` of the OpenNox repo (2 files, +22/-11).
  Applies cleanly to v1.9.0-alpha13 and to upstream `dev` (0e78e4cd5, checked 2026-10-08).
- `build.sh`, `Dockerfile`: reproducible Windows cross-build in Docker.

## The crash

```
panic: runtime error: index out of range [1] with length 1
github.com/noxworld-dev/opennox/v1.(*Client).sub_4C5500  src/client_draw.go:342
  <- nox_xxx_drawAllMB_475810_draw  client_draw.go:278 <- clientDrawAll <- clientDraw <- Update
```

### Cause

Each frame the client turns the player's sight polygon (up to `sightPointsMax` = 1024 points) into
per-screen-row lists of edge crossings (`sub_4C52E0` -> `sub_4C5430`). A row's crossings are kept
sorted in `tileMapXxx.arr [32]int` with the count in `nox_arr_956A00[y]`; pairs `[arr[2k], arr[2k+1])` are
the row's visible spans. `sub_4C5430` stops adding once a row holds 32.

`sub_4C5500` then blacks out everything outside the visible spans. The loop, ported from C, ran
`(n+1)/2` times and on each pass also read the start of the next span, `arr[2i+2]`. On the last pass
that element is past the last crossing. In C the extra read was harmless. In Go, with a row at 31 or 32
crossings it is `arr[32]`, past the end of the array, and the client panics. A long, jagged sight edge
seen side-on (a level forest edge: a row of tree walls along a horizontal line) gives single screen rows
more than 30 crossings. Rows with more than 32 crossings had a second, silent bug: the extra crossings
were dropped, so the visible and dark spans on that row came out in the wrong places.

Only the HD client (`opennox-hd.exe`) crashed on our test view. The SD client renders a smaller
viewport and stayed under the limit there, but it has the same code.

### Fix

1. `sub_4C5500` reads only complete pairs (`n := min(count, len(arr)) &^ 1`). It never reads past the
   last crossing. Output for normal rows (an even count within capacity) is unchanged. An unpaired last
   crossing, which can only happen when a row overflowed, is ignored, so the rest of that row stays dark
   (it hides rather than reveals).
2. Per-row capacity goes from 32 to `tileRowMaxCrossings` = 256, so rows with many crossings are drawn
   correctly instead of losing crossings. Memory: (2160+150) rows x 256 x 4 bytes, about 2.4 MB in the
   32-bit HD build. `sub_4C5430` checks against `len(arr)` instead of a hard-coded 32.

All the other readers of these arrays (`Sub4C5630`, `Sub4C42A0`, the solid and textured floor drawers)
stay in bounds for any count up to the capacity. The capacity is even, and they read at most index `count`.

## Build

```
engine/opennox/build.sh <opennox checkout dir> <output dir> [targets]
```

If the checkout dir does not exist, the script clones OpenNox at v1.9.0-alpha13 and applies the patch.
It needs only Docker (Docker Desktop with WSL2 works). This follows upstream
`docs/build-windows-on-linux.md`, with the toolchain pinned to match the official alpha13 binaries.
Their build info: go1.21.5, GOARCH=386, cgo, tags `guiapp` / `highres,guiapp` / `server`. Upstream's
CI image `ghcr.io/noxworld-dev/docker-build:latest-win` cannot be pulled anonymously, so we use this
equivalent:

| Part | Version |
|---|---|
| Go | 1.21.5 (`golang:1.21.5-bookworm`) |
| C compiler | Debian `gcc-mingw-w64-i686-win32` 12.2.0-14+deb12u1 (i686-w64-mingw32-gcc 12) |
| SDL2 headers/import lib | SDL2-devel-2.28.5-mingw (same version as the shipped `SDL2.dll`) |
| OpenAL headers/import lib | openal-soft-1.23.1-bin (same version as the shipped `OpenAL32.dll`) |

The output imports exactly what the official build imports (`OpenAL32.dll SDL2.dll KERNEL32.dll
msvcrt.dll OPENGL32.DLL WS2_32.dll`; the server imports only the system DLLs). So the DLLs already in the
game folder are reused and no new ones are needed. The game reports the version `v1.9.0-alpha13-sightfix`.
A first build takes about 3 minutes; later builds take seconds because the Go module and build caches
are kept in Docker volumes.

## Installed on pc1 (2026-10-08)

- Originals backed up to `%LOCALAPPDATA%\dystopianentity\backups\opennox-original\` (with `SHA256SUMS.txt`):
  `opennox.exe` 191af208..., `opennox-hd.exe` 70a5e019..., `opennox-debug.exe` 4241eef1...,
  `opennox-server.exe` 2718d135...
- Patched builds in `C:\GOG Games\Nox` (built from OpenNox commit 075dd37ba = v1.9.0-alpha13 + this patch):
  `opennox.exe` 93b96517..., `opennox-hd.exe` e40053c8..., `opennox-debug.exe` 8c179479...,
  `opennox-server.exe` 0100069f...
- To revert, copy the four files from the backup folder back into `C:\GOG Games\Nox`.

## Verification

The test method is the same as for CL-1. Start `opennox-hd.exe -swindow -config opennox-test.yml
-autosrv -minimize -rcon 127.0.0.1:2022 -rcon-pass test`, then over rcon run `racoiaws; load <map>` and
watch stderr. The crash map was the pre-CL-1 Thornwick (from nox 6b300f5), installed as a separate
Arena-flagged test map `SgtCrash` and removed afterwards. To load the real, unmodified Solo Thornwick
into the test game we used `set maps allow.all 1`, so the installed Thornwick was never touched.

| Client | Map | Result |
|---|---|---|
| official opennox-hd.exe | SgtCrash | **panic** at client_draw.go:342 right after load |
| our rebuild of unpatched v1.9.0-alpha13 (same toolchain) | SgtCrash | **panic** at client_draw.go:342 |
| patched opennox-hd.exe | SgtCrash | alive 30 s, no panic; fog of war draws cleanly along the forest edge (framebuffer grab) |
| patched opennox-hd.exe | installed Thornwick | loads (Go scripts load), alive 60 s, no panic |
| patched opennox.exe | SgtCrash / Thornwick | alive 20 s / 30 s |
| patched opennox-debug.exe | SgtCrash | alive 20 s |
| patched opennox-server.exe | default | starts, loads estate, no panic (15 s smoke test) |

The control rebuild crashing in the same way shows that the fix, not a toolchain difference, removes the
crash.

## Upstream (draft; not filed: the user decides)

**Issue title:** Client panic `index out of range [1] with length 1` in `sub_4C5500` (client_draw.go) when
a screen row crosses the sight polygon 31+ times

**Body:**

> OpenNox v1.9.0-alpha13 (also present on `dev`) panics in `(*Client).sub_4C5500` at
> `src/client_draw.go:342` (`lxe = ptr2i[1]`) when a screen row has 31 or more sight-polygon edge
> crossings. This is easy to hit with the HD client on maps that have long jagged sight edges, such as a
> long row of tree walls seen from the side.
>
> `tileMapXxx.arr` holds 32 crossings. The fill loop runs `(n+1)/2` times and on every pass also reads
> the start of the next span, so on the last pass it reads `arr[n]`. With `n >= 31` that is `arr[32]`,
> which is out of range. The original C read was harmless but unused. Separately, `sub_4C5430` silently
> drops crossings past 32, which misplaces the visible spans on that row.
>
> Repro: load a map whose view has a long jagged wall edge in `opennox-hd` at 1920x1080. We can provide
> a test map.

**PR title:** Fix sub_4C5500 out-of-range read; raise per-row sight crossing capacity to 256

**PR body:**

> - `sub_4C5500` reads only complete span pairs and never reads past the last crossing. Rendering of
>   normal rows is unchanged.
> - `tileMapXxx.arr` grows from 32 to 256 entries (`tileRowMaxCrossings`), and `sub_4C5430` checks
>   against `len(arr)`, so rows with many crossings render correctly instead of dropping crossings.
>   The cost is about 2.4 MB in the 386 HD build.
> - Other readers of the arrays stay within bounds (the capacity is even and they read at most index
>   `count`).
>
> Tested on Windows (386, HD and SD): the map that panicked on alpha13 now renders correctly; normal maps
> are unaffected.
