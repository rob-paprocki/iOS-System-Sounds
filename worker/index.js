/* ===========================================================================
   The Worker.

   Two jobs, and it only ever does the second one.

   Static assets — the page, its modules, its fonts and the ~3 MB index — are
   served straight from the assets binding without invoking this script at all;
   that is the default routing behaviour when a request matches a file in the
   assets directory.

   Everything else lands here, and the only things that should are the audio
   paths. 355 MB of originals and a 191 MB preview mirror do not belong in a
   git repository, so they live in R2 and this Worker fronts them on the same
   origin as the page. Same origin is the point: no CORS preflight on every
   play, no second domain to keep alive, and range requests handled properly
   so seeking works — Safari will not play an <audio> source that cannot
   answer a Range request.

     /audio/Current/UI Sounds/iPhone/Tink.m4a   ->  R2 key audio/Current/…
     /originals/Current/UI Sounds/iPhone/Tink.caf -> R2 key originals/Current/…

   Note that a _headers file does not apply to responses generated here, only
   to static assets, so the caching headers below are set by hand.
   =========================================================================== */

const R2_PREFIXES = ['audio/', 'originals/'];

/* Fallbacks only: R2 serves whatever content type the upload recorded, and
   these fill in when that metadata is missing. audio/mp4 is the load-bearing
   one — it is what every preview in the collection is. */
const TYPES = {
  m4a: 'audio/mp4',
  caf: 'audio/x-caf',
  aiff: 'audio/aiff',
  aif: 'audio/aiff',
  wav: 'audio/wav',
  mp3: 'audio/mpeg',
  flac: 'audio/flac'
};

function typeFor(key) {
  const ext = key.slice(key.lastIndexOf('.') + 1).toLowerCase();
  return TYPES[ext] || 'application/octet-stream';
}

/* R2 hands back one of three range shapes; all three have to become a
   Content-Range, or the browser gets a 206 it cannot interpret. */
function contentRange(range, size) {
  let start, end;
  if (range.suffix != null) {
    start = Math.max(0, size - range.suffix);
    end = size - 1;
  } else {
    start = range.offset ?? 0;
    end = range.length != null ? start + range.length - 1 : size - 1;
  }
  return { value: `bytes ${start}-${end}/${size}`, length: end - start + 1 };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Decode per segment: decoding the whole path would turn an encoded %2F
    // into a separator and let a key climb out of its prefix.
    const segments = url.pathname.slice(1).split('/').map(s => {
      try { return decodeURIComponent(s); } catch { return s; }
    });
    const key = segments.join('/');

    if (!R2_PREFIXES.some(p => key.startsWith(p))) {
      return env.ASSETS.fetch(request);
    }

    if (segments.some(s => s === '..' || s === '.')) {
      return new Response('Bad request', { status: 400 });
    }

    if (request.method !== 'GET' && request.method !== 'HEAD') {
      return new Response('Method not allowed', {
        status: 405,
        headers: { allow: 'GET, HEAD' }
      });
    }

    const object = await env.AUDIO.get(key, {
      range: request.headers,
      onlyIf: request.headers
    });

    if (object === null) {
      return new Response('Not found', {
        status: 404,
        headers: { 'cache-control': 'public, max-age=60' }
      });
    }

    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set('etag', object.httpEtag);
    headers.set('accept-ranges', 'bytes');
    if (!headers.has('content-type')) headers.set('content-type', typeFor(key));

    // Every object here is content: a given path is one fixed recording, and a
    // re-ingest writes a new path rather than changing this one.
    headers.set('cache-control', 'public, max-age=31536000, immutable');

    // A body-less R2Object means the caller's If-None-Match / If-Modified-Since
    // already matched, so there is nothing to send.
    if (!('body' in object) || object.body === null || object.body === undefined) {
      return new Response(null, { status: 304, headers });
    }

    const wantsRange = request.headers.has('range') && object.range;
    let status = 200;
    let length = object.size;

    if (wantsRange) {
      const cr = contentRange(object.range, object.size);
      headers.set('content-range', cr.value);
      length = cr.length;
      status = 206;
    }
    headers.set('content-length', String(length));

    if (request.method === 'HEAD') return new Response(null, { status, headers });
    return new Response(object.body, { status, headers });
  }
};
