#!/usr/bin/env python3
"""List every asset/string name in an NX1 fastfile (read-only) into a small zip.
Usage: python nx1_strings.py <zone.ffm> <out.zip>"""
import sys, zlib, struct, re, zipfile

def find_stream0(f):
    count = struct.unpack(">I", f[0x1a:0x1e])[0]
    start = max(0x20, 0x20 + count * 12 - 16)
    for p in range(start, min(len(f) - 8, start + 0x400)):
        if f[p] == 0x78 and f[p + 1] in (0x01, 0x5e, 0x9c, 0xda):
            try:
                zlib.decompressobj().decompress(f[p:p + 65536]); return p
            except Exception:
                pass
    raise SystemExit("Could not find the main data stream.")

def main():
    if len(sys.argv) != 3:
        print(__doc__); return 1
    f = open(sys.argv[1], "rb").read()
    if f[:4] != b"NXff":
        raise SystemExit("Not an NX1 fastfile.")
    d = zlib.decompressobj().decompress(f[find_stream0(f):])
    names = sorted(set(m.group(0).decode() for m in re.finditer(rb"[A-Za-z0-9_\.]{4,80}(?=\x00)", d)))
    with zipfile.ZipFile(sys.argv[2], "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("names.txt", "\n".join(names))
    print("%d names -> %s" % (len(names), sys.argv[2]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
