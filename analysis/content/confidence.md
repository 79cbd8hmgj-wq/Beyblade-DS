# Confidence notes

- Resource table boundaries/counts/strides: **confirmed** by structural parser on both decompressed ARM9 images.
- All `/bey` model and texture NARCs resolving through LZ11 to `BMD0`/`BTX0`: **confirmed** by complete directory scan.
- Groups 0–4 representing Face, Clear Wheel, Metal Wheel, Track, Bottom: **strongly supported** by embedded Nitro model names plus the five-way custom-Bey executable switch.
- Fusion groups 5–7 as alternate presentation families: **candidate** until their callers are fully traced.
- `BeyBladeLOC` 40-byte structure as a gameplay master table: **candidate only**; the stride is observed, the semantics are not.
- Metal Masters' four model NARCs missing from the ARM9 resource registry are **confirmed unregistered**, not confirmed unused.
