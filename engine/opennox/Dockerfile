# OpenNox Windows cross-build image (docs/build-windows-on-linux.md of noxworld-dev/opennox, pinned to the
# toolchain that built the official v1.9.0-alpha13 binaries: Go 1.21.5, GOARCH=386, MinGW i686,
# headers/import libs matching the DLLs shipped with that release: SDL2 2.28.5, OpenAL Soft 1.23.1).
FROM golang:1.21.5-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends gcc-mingw-w64-i686 unzip curl ca-certificates git \
 && rm -rf /var/lib/apt/lists/*
RUN cd /tmp && curl -fsSLo sdl2.tgz https://github.com/libsdl-org/SDL/releases/download/release-2.28.5/SDL2-devel-2.28.5-mingw.tar.gz \
 && tar -xzf sdl2.tgz && cp -r SDL2-2.28.5/i686-w64-mingw32/include/* /usr/i686-w64-mingw32/include/ \
 && cp -r SDL2-2.28.5/i686-w64-mingw32/lib/* /usr/i686-w64-mingw32/lib/ && rm -rf /tmp/*
RUN cd /tmp && curl -fsSLo openal.zip https://openal-soft.org/openal-binaries/openal-soft-1.23.1-bin.zip \
 && unzip -q openal.zip && cp -r openal-soft-1.23.1-bin/include/* /usr/i686-w64-mingw32/include/ \
 && cp openal-soft-1.23.1-bin/libs/Win32/* /usr/i686-w64-mingw32/lib/ \
 && ln -sf libOpenAL32.dll.a /usr/i686-w64-mingw32/lib/libOpenAL.dll.a && rm -rf /tmp/*
RUN git config --system --add safe.directory '*'
