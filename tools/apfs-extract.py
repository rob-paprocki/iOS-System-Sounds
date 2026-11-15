#!/usr/bin/env python3
"""Copy files matching a pattern out of raw APFS images, without mounting them.

`ipsw extract --files` mounts each filesystem image, which works on macOS and
nowhere else. This reads the same images with dissect.apfs instead, so the
pipeline runs on Windows and Linux too. Like ipsw, the pattern is a regex
searched against each file's path inside the volume, and every image is
extracted into the same output root.

    pip install dissect.apfs
    python3 tools/apfs-extract.py --pattern '.*\\.caf$' --out _work/x fs.dmg sys.dmg
"""
import argparse
import os
import re
import shutil
import sys

import dissect.apfs.stream
from dissect.apfs import APFS


def lzbitmap_decompress(src):
    """LZBITMAP, ported line for line from eafer/libzbitmap (MIT).

    dissect.util's decoder rejects valid streams -- WebCore's Composite.wav in
    the iOS 27.0 SystemOS cryptex is one -- so this replaces it.
    """
    src = bytes(src)
    if src[:4] != b'ZBM\x09':
        raise ValueError('not an LZBITMAP stream')
    u24 = lambda o: src[o] | src[o + 1] << 8 | src[o + 2] << 16
    dst = bytearray()
    pos = 4
    while True:
        length, decmp_len = u24(pos), u24(pos + 3)
        end = pos + length
        if length > len(src) - pos or decmp_len > 0x8000:
            raise ValueError('bad LZBITMAP chunk header')
        if length == decmp_len + 6:
            dst += src[pos + 6:pos + 6 + decmp_len]
        elif decmp_len:
            meta1, meta2, meta3 = u24(pos + 6) + pos, u24(pos + 9) + pos, u24(pos + 12) + pos
            data, period, written = pos + 15, 8, 0
            # Twelve 10-bit entries, LSB first, from the chunk's last 17 bytes
            bits = int.from_bytes(src[end - 17:end], 'little')
            bitmaps = [((bits >> 10 * i) & 0xFF, (bits >> 10 * i + 8) & 3) for i in range(12)]
            nib = [meta3, 0]

            def read_nibble():
                if nib[0] >= end:
                    raise ValueError('LZBITMAP nibble overrun')
                b = src[nib[0]]
                if nib[1] == 0:
                    nib[1] = 1
                    return b & 0xF
                nib[1] = 0
                nib[0] += 1
                return b >> 4

            def rewind_nibble():
                if nib[1] == 0:
                    nib[1] = 1
                    nib[0] -= 1
                else:
                    nib[1] = 0

            while written < decmp_len:
                num = read_nibble()
                # Don't confuse the trailing bitmaps with a repetition count
                if decmp_len - written <= 8:
                    repeat = 1
                else:
                    n = read_nibble()
                    if n != 0xF:
                        rewind_nibble()
                        repeat = 1
                    else:
                        repeat = 4
                        while n == 0xF:
                            n = read_nibble()
                            repeat += n
                if num == 0xF:
                    raise ValueError('bad LZBITMAP bitmap number')
                for _ in range(repeat):
                    if num > 2:
                        bitmap, nbytes = bitmaps[num - 3]
                    else:
                        bitmap, nbytes = src[meta2], num
                        meta2 += 1
                    if nbytes:
                        period = int.from_bytes(src[meta1:meta1 + nbytes], 'little')
                        meta1 += nbytes
                    if period == 0:
                        raise ValueError('zero LZBITMAP period')
                    for i in range(8):
                        if written == decmp_len:
                            break
                        if bitmap >> i & 1:
                            dst.append(src[data])
                            data += 1
                        else:
                            dst.append(dst[-period])
                        written += 1
        pos = end
        if decmp_len == 0:
            return bytes(dst)


dissect.apfs.stream.lzbitmap.decompress = lzbitmap_decompress


def walk(node, path, pattern, out, counts):
    for entry in node.iterdir():
        rel = path + '/' + entry.name if path else entry.name
        if entry.is_dir():
            walk(entry.inode, rel, pattern, out, counts)
        elif entry.is_file() and pattern.search(rel):
            dest = os.path.join(out, *rel.split('/'))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                with entry.inode.open() as src, open(dest, 'wb') as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
            except Exception as e:
                os.remove(dest)
                print('  FAILED %s: %s %s' % (rel, type(e).__name__, e), file=sys.stderr)
                counts[1] += 1
                continue
            counts[0] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pattern', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('images', nargs='+')
    args = ap.parse_args()

    pattern = re.compile(args.pattern)
    failed = 0
    for image in args.images:
        with open(image, 'rb') as fh:
            for vol in APFS(fh).volumes:
                counts = [0, 0]
                walk(vol.get('/'), '', pattern, args.out, counts)
                print('  %s [%s]: %d files, %d unreadable'
                      % (os.path.basename(image), vol.name, counts[0], counts[1]))
                failed += counts[1]
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
