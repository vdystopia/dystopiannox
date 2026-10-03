"""Independent Nox .map reader used to check what the editor writes.

Deliberately shares no code with the editor: if the editor's reader and writer agree
with each other but not with the game's format, this catches it. Format details
follow noxworld-dev/opennox-lib; the Blowfish key is Nox key #19 from
noxworld-dev/noxcrypt (MIT).
"""
import struct
from Crypto.Cipher import Blowfish

MAP_KEY = bytes.fromhex(
    "31d1d34ee92d8331c96de709b0c8fa4641ddd48fc173f770bd7ecae670a7b6e2"
    "67f65e08c27b5b41ab3937a9bf0f63995c09497a27fe0d23")


def decrypt(data):
    n = len(data) - len(data) % 8
    return Blowfish.new(MAP_KEY, Blowfish.MODE_ECB).decrypt(data[:n])


class R:
    def __init__(self, b, off=0): self.b, self.o = b, off
    def u8(self):  v = self.b[self.o]; self.o += 1; return v
    def u16(self): v, = struct.unpack_from("<H", self.b, self.o); self.o += 2; return v
    def u32(self): v, = struct.unpack_from("<I", self.b, self.o); self.o += 4; return v
    def i32(self): v, = struct.unpack_from("<i", self.b, self.o); self.o += 4; return v
    def u64(self): v, = struct.unpack_from("<Q", self.b, self.o); self.o += 8; return v
    def f32(self): v, = struct.unpack_from("<f", self.b, self.o); self.o += 4; return v
    def raw(self, n): v = self.b[self.o:self.o + n]; self.o += n; return v
    def s8(self): return self.raw(self.u8()).split(b"\0")[0].decode("latin1")
    def align(self):
        if self.o % 8: self.o += 8 - self.o % 8
    def left(self): return len(self.b) - self.o


def sections(path):
    """Decrypt a .map and split it into {section name: bytes}."""
    p = decrypt(open(path, "rb").read())
    r = R(p)
    magic = r.u32()
    if magic == 0xFADEFACE:
        r.align(); r.u32(); r.o += 4  # CRC occupies a full crypt block
    elif magic != 0xFADEBEEF:
        raise ValueError(f"{path}: bad magic {magic:#x}")
    r.u32(); r.u32()  # wall offset
    out = {}
    while r.left() > 0:
        n = r.u8()
        if n == 0: break
        name = r.raw(n).split(b"\0")[0].decode("latin1"); r.align()
        size = r.u64()
        out[name] = p[r.o:r.o + size]; r.o += size
    return out


def walls(b):
    r = R(b, 18); out = []
    while True:
        x = r.u8()
        if x == 0xFF: return out
        y = r.u8(); d, mat, var, mm, mod = r.raw(5)
        out.append((x, y, d, mat, var, mm, mod))  # d keeps bit 7, which the game preserves


def _tile(r):
    t = (r.u8(), r.u16(), r.u16()); n = r.u8()
    return t + tuple((r.u8(), r.u16(), r.u8(), r.u8()) for _ in range(n))


def tiles(b):
    """Floor tiles as (x, y, tile). Each entry is a pair of tiles: the first byte holds the
    pair's Y and flags the left tile; the second holds X and flags the right tile; when both
    are present the right tile comes first. This matches the game's writer (and the editor).
    opennox-lib's maps package reads these bytes the other way round and misplaces tiles."""
    r = R(b, 18); out = []
    while True:
        b1, b2 = r.u8(), r.u8()
        if b1 == 0xFF and b2 == 0xFF: return out
        px, py = b2 & 0x7F, b1 & 0x7F
        right = _tile(r) if b2 & 0x80 else None
        left = _tile(r) if b1 & 0x80 else None
        if left:  out.append((2 * px, 2 * py, left))
        if right: out.append((2 * px + 1, 2 * py - 1, right))


def waypoints(b):
    r = R(b); r.u16(); out = []
    for _ in range(r.u32()):
        w = (r.u32(), r.f32(), r.f32(), r.s8(), r.u32())
        out.append(w + tuple((r.u32(), r.u8()) for _ in range(r.u8())))
    return out


def objects(toc_b, data_b):
    """(type, x, y, name, team) for every object; only the common xfer header is parsed."""
    r = R(toc_b); r.u16()
    toc = {r.u16(): r.s8() for _ in range(r.u16())}
    r = R(data_b); r.u16(); out = []
    while r.left() >= 2:
        ind = r.u16()
        if ind == 0: break
        r.align()
        size = r.u64(); blob = R(data_b[r.o:r.o + size]); r.o += size
        gv = blob.u16(); ov = blob.u16() if gv >= 40 else 0
        name = team = None
        if gv >= 40 and ov >= 61:
            blob.u32(); blob.u32(); x, y = blob.f32(), blob.f32()
            if blob.u8():
                blob.u32(); name = blob.s8(); team = blob.u8()
        else:
            blob.u32(); blob.u32()
            x, y = (blob.f32(), blob.f32()) if gv >= 40 and ov >= 4 else (blob.i32(), blob.i32())
            if gv >= 10: name = blob.s8()
        out.append((toc.get(ind, f"?{ind}"), x, y, name, team))
    return out
