#!/usr/bin/env python3
"""Check the SigV4 signing in tools/upload-audio.py against AWS's own vectors.

The uploader speaks S3 by hand, so a quiet mistake in the signing would look
exactly like bad credentials. These are the worked examples AWS publishes, with
their expected intermediate values, so the maths is pinned to a known answer
rather than to whatever the code happens to produce.

    python3 tools/tests/test_sigv4.py
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
spec = importlib.util.spec_from_file_location("upload_audio", ROOT / "tools" / "upload-audio.py")
assert spec and spec.loader, "cannot load tools/upload-audio.py"
ua = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ua)

EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
failures: list[str] = []


def check(name: str, got, want) -> None:
    if got == want:
        print(f"  ok    {name}")
    else:
        print(f"  FAIL  {name}\n          got  {got}\n          want {want}")
        failures.append(name)


# The S3 "GET Object" example below is the only published vector asserted here,
# and it is the strong one: reaching its signature exercises the whole chain —
# canonical request, scope, the four-stage signing-key derivation and the final
# HMAC. A standalone derivation vector was dropped rather than assert a constant
# that could not be reproduced from any documented set of inputs.
#
# The full S3 GET Object example, canonical request through to signature.
headers = {
    "host": "examplebucket.s3.amazonaws.com",
    "range": "bytes=0-9",
    "x-amz-content-sha256": EMPTY_SHA,
    "x-amz-date": "20130524T000000Z",
}
creq, signed = ua.canonical_request("GET", "/test.txt", headers, EMPTY_SHA)

check("signed header list", signed, "host;range;x-amz-content-sha256;x-amz-date")
check("canonical request hash",
      hashlib.sha256(creq.encode()).hexdigest(),
      "7344ae5b7ee6c3e7e6b0fe0640412a37625d1fbfff95c48bbb2dc43964946972")

scope = "20130524/us-east-1/s3/aws4_request"
sts = ua.string_to_sign("20130524T000000Z", scope, creq)
signature = hmac.new(
    ua._signing_key("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "20130524",
                    region="us-east-1", service="s3"),
    sts.encode(), hashlib.sha256).hexdigest()
check("S3 GET example signature",
      signature,
      "f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41")


# 3. Key encoding. The Worker looks up the decoded path, so a space has to
#    survive as %20 in the URL and as a literal space in the stored key — and
#    a slash must never be encoded, or the key gains a directory level.
check("space encodes", ua.encode_key("audio/UI Sounds/Tink.m4a"),
      "audio/UI%20Sounds/Tink.m4a")
check("ampersand encodes", ua.encode_key("originals/Ringtones & Alert Tones/Old Phone.m4a"),
      "originals/Ringtones%20%26%20Alert%20Tones/Old%20Phone.m4a")
check("separators survive", ua.encode_key("a/b/c.caf"), "a/b/c.caf")
check("unreserved untouched", ua.encode_key("a-b_c.d~e"), "a-b_c.d~e")


print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("all signing vectors match")
