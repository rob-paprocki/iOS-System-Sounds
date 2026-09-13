#!/usr/bin/env bash
#
# Push the audio to R2, where the Worker serves it from.
#
#   web/audio/**        ->  audio/**              the AAC preview mirror (191 MB)
#   Current/**          ->  originals/Current/**  \
#   Removed/**          ->  originals/Removed/**   |  as Apple shipped them (355 MB)
#   Spoken Content/**   ->  originals/Spoken…/**  /
#
# Those prefixes are what worker/index.js maps URL paths onto, so the layout
# here is not cosmetic.
#
# Uses rclone against R2's S3 API. Do NOT use `wrangler r2 object put` for this:
# it percent-encodes the key it parses out of `bucket/key`, so a file with a
# space lands under "UI%20Sounds" and the Worker — which looks up the decoded,
# literal key — will never find it. Nearly every path in this collection has a
# space in it. rclone stores keys literally, which is what we want.
#
# One-time rclone setup (S3-compatible, provider Cloudflare):
#
#   rclone config create r2 s3 provider=Cloudflare \
#     access_key_id=<id> secret_access_key=<secret> \
#     endpoint=https://<account-id>.r2.cloudflarestorage.com
#
# Then:  ./tools/upload-audio.sh
#
set -euo pipefail

REMOTE="${R2_REMOTE:-r2}"
BUCKET="${R2_BUCKET:-ios-system-sounds-audio}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone is not installed. brew install rclone" >&2
  exit 1
fi

if ! rclone listremotes | grep -qx "${REMOTE}:"; then
  echo "rclone remote '${REMOTE}:' is not configured — see the header of this script." >&2
  exit 1
fi

if [ ! -d "$ROOT/web/audio" ]; then
  echo "web/audio is missing. Build it with: python3 tools/make-web.py" >&2
  exit 1
fi

# --checksum so re-runs after a partial upload only move what actually differs.
# rclone sets Content-Type from the file extension, which is what the Worker
# falls back to anyway.
common=(--checksum --transfers 32 --s3-no-check-bucket --progress)

echo "==> previews  -> ${REMOTE}:${BUCKET}/audio"
rclone copy "$ROOT/web/audio" "${REMOTE}:${BUCKET}/audio" "${common[@]}"

for tree in "Current" "Removed" "Spoken Content"; do
  if [ -d "$ROOT/$tree" ]; then
    echo "==> ${tree}/ -> ${REMOTE}:${BUCKET}/originals/${tree}"
    rclone copy "$ROOT/$tree" "${REMOTE}:${BUCKET}/originals/${tree}" "${common[@]}"
  fi
done

echo
echo "Done. Spot-check one of each through the deployed Worker:"
echo "  curl -I 'https://<your-domain>/audio/Current/UI%20Sounds/iPhone/Tink.m4a'"
echo "  curl -I 'https://<your-domain>/originals/Current/UI%20Sounds/iPhone/Tink.caf'"
echo "Both should be 200 with Accept-Ranges: bytes."
