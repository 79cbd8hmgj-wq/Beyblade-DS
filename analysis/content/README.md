# Content-layer analysis

Tracked files in this directory are compact, derived reverse-engineering metadata. Full per-file scans, decompressed ARM9 images, overlay dumps, NARC members, and extracted model/texture data belong under ignored generated-output directories.

Current checkpoint files:

- `bey-resource-map.json` — ARM9 physical model, texture descriptor, logical usage tables, category runs, and executable anchors
- `format-inventory.json` — NARC/LZ11/Nitro 3D and common wrapper counts
- `library-signatures.json` — embedded SDK signature locations
- `overlay-summary.json` — ARM9 overlay counts, address extents, and compression status
- `verification.json` — test and real-ROM validation evidence

See `docs/reverse-engineering/checkpoint-02.md` for interpretation and confidence levels.
