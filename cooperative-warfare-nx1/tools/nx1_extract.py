#!/usr/bin/env python3
"""Extract the plain-text .gsc scripts from an NX1 fastfile into a small zip (read-only).
Usage: python nx1_extract.py <zone.ffm> <out.zip>"""
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
    n = 0
    with zipfile.ZipFile(sys.argv[2], "w", zipfile.ZIP_DEFLATED) as z:
        for m in re.finditer(rb"[A-Za-z0-9_/]+\.gsc\x00\x78[\x01\x5e\x9c\xda]", d):
            o = m.start(); name = d[o:d.index(b"\0", o)].decode(); hdr = d[o - 16:o]
            if hdr[:4] != b"\xff\xff\xff\xff" or hdr[12:16] != b"\xff\xff\xff\xff":
                continue
            cl, ln = struct.unpack(">II", hdr[4:12]); s = o + len(name) + 1
            try:
                t = zlib.decompressobj().decompress(d[s:s + cl + 16]); assert len(t) == ln
            except Exception:
                continue
            z.writestr(name, t); n += 1
    print("extracted %d scripts -> %s" % (n, sys.argv[2]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
