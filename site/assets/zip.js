/* ===========================================================================
   Minimal ZIP writer, STORE method only.

   Everything in this corpus is already a compressed audio stream, so deflating
   it would burn CPU to save nothing. Storing also keeps this small enough to
   read in one sitting and removes a third-party dependency from a site whose
   whole point is that it has no build step.

   Scope: < 4 GB total, < 65,535 entries, so no Zip64. The tray caps selections
   at 200 files, well inside that.
   =========================================================================== */

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(bytes) {
  let c = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}

/* MS-DOS date/time, which is what a ZIP central directory wants. */
function dosTime(d) {
  const time = ((d.getHours() & 31) << 11) | ((d.getMinutes() & 63) << 5) | ((d.getSeconds() / 2) & 31);
  const date = (((d.getFullYear() - 1980) & 127) << 9) | (((d.getMonth() + 1) & 15) << 5) | (d.getDate() & 31);
  return { time, date };
}

class Writer {
  constructor(size) { this.b = new Uint8Array(size); this.p = 0; }
  u16(v) { this.b[this.p++] = v & 0xFF; this.b[this.p++] = (v >>> 8) & 0xFF; }
  u32(v) { this.u16(v & 0xFFFF); this.u16((v >>> 16) & 0xFFFF); }
  raw(bytes) { this.b.set(bytes, this.p); this.p += bytes.length; }
}

/**
 * Build a zip from [{ name, data }] where data is a Uint8Array.
 * Returns a Blob.
 */
export function makeZip(entries) {
  const enc = new TextEncoder();
  const now = dosTime(new Date());

  const prepared = entries.map(e => {
    const name = enc.encode(e.name);
    return { name, data: e.data, crc: crc32(e.data) };
  });

  let size = 0;
  for (const e of prepared) size += 30 + e.name.length + e.data.length;      // local headers
  for (const e of prepared) size += 46 + e.name.length;                      // central directory
  size += 22;                                                               // end of central dir

  const w = new Writer(size);
  const offsets = [];

  for (const e of prepared) {
    offsets.push(w.p);
    w.u32(0x04034b50);      // local file header
    w.u16(20);              // version needed
    w.u16(0x0800);          // flags: UTF-8 names
    w.u16(0);               // method: store
    w.u16(now.time);
    w.u16(now.date);
    w.u32(e.crc);
    w.u32(e.data.length);   // compressed size
    w.u32(e.data.length);   // uncompressed size
    w.u16(e.name.length);
    w.u16(0);               // extra length
    w.raw(e.name);
    w.raw(e.data);
  }

  const cdStart = w.p;
  prepared.forEach((e, i) => {
    w.u32(0x02014b50);      // central directory header
    w.u16(20);              // version made by
    w.u16(20);              // version needed
    w.u16(0x0800);
    w.u16(0);
    w.u16(now.time);
    w.u16(now.date);
    w.u32(e.crc);
    w.u32(e.data.length);
    w.u32(e.data.length);
    w.u16(e.name.length);
    w.u16(0);               // extra
    w.u16(0);               // comment
    w.u16(0);               // disk number
    w.u16(0);               // internal attrs
    w.u32(0);               // external attrs
    w.u32(offsets[i]);
    w.raw(e.name);
  });

  // Take the directory's size before writing the trailer: w.p moves as the
  // trailer is written, and reading it mid-record reports a size too large by
  // however much of the trailer is already down.
  const cdSize = w.p - cdStart;

  w.u32(0x06054b50);        // end of central directory
  w.u16(0);                 // this disk
  w.u16(0);                 // disk with the central directory
  w.u16(prepared.length);   // entries on this disk
  w.u16(prepared.length);   // entries total
  w.u32(cdSize);
  w.u32(cdStart);
  w.u16(0);                 // comment length

  return new Blob([w.b], { type: 'application/zip' });
}
