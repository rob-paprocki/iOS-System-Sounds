# research/

`ipswme-iphone.json` is a snapshot of the ipsw.me firmware API for every iPhone
identifier. `tools/plan.py` reads it to derive the extraction matrix, and re-fetches
it if it is missing. It is kept so the matrix can be reproduced exactly as published
even if the API changes.

`release-research.json` is the raw output of the release-history research: what each
iOS release did to its audio, with sources, plus the builds it recommended extracting
and an explicit account of what it could not establish. `docs/release-timeline.md` is
the readable version.
