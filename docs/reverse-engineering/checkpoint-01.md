# Reverse-engineering checkpoint 01

## Scope

Initial comparative mapping of four supplied US Nintendo DS ROMs:

- Metal Fusion — Collector's Edition (`BBUY`)
- Metal Fusion — Toys'R'Us Exclusive (`BBUX`)
- Metal Fusion — Walmart Exclusive (`BBUZ`)
- Metal Masters (`BRZE`)

The commercial ROMs are immutable local inputs and are intentionally excluded from Git.

## Confirmed ROM structure

| ROM | SHA-256 | NitroFS files | ARM9 overlays | ARM9 compressed | ARM9 decompressed |
|---|---|---:|---:|---:|---:|
| Fusion Collector's | `e2730dac5cee463573c7d3f2293c6e85dd7bc26b219c9affb6d4a62b859a1a1b` | 5,541 | 77 | `0x9AC34` | `0x106A78` |
| Fusion Toys'R'Us | `93bef8a6ab52f723135d7335bb1e80a5c51a1f0e27a57fe3b943c4f9d2641b44` | 5,541 | 77 | `0x9AC34` | `0x106A78` |
| Fusion Walmart | `a5f07ea9681bf8115092ec8b07c14b94155c4b917fb9d779f2d096f662bdbc81` | 5,541 | 77 | `0x9AC34` | `0x106A78` |
| Metal Masters | `a8a2696cc448d5d5549caa32a1c95fe4a7542ff617852f91b6d5953c68b5012c` | 4,774 | 97 | `0x42D04` | `0x77F38` |

All four are 64 MiB images. The three Fusion editions use the same title string (`BEYBLADE2LOC`), while Metal Masters uses `BEYBLADE4NOA`.

## High-value Fusion result

The three Fusion editions are overwhelmingly the same game build:

- identical 5,541-path NitroFS tree
- every NitroFS file is byte-identical across all three editions
- all 77 ARM9 overlays are byte-identical
- ARM7 is byte-identical
- after BLZ decompression and excluding the DS secure-area region, the main ARM9 binaries differ by only 23–33 bytes depending on the pair compared

This changes the RE strategy. Fusion should be reverse-engineered once, with the small ARM9 edition deltas documented separately. There is no reason to independently reverse-engineer three copies of the same filesystem and overlay set.

The different Fusion product codes are:

- `BBUY` — Collector's Edition
- `BBUX` — Toys'R'Us Exclusive
- `BBUZ` — Walmart Exclusive

The next executable pass should identify the handful of post-secure-area ARM9 differences and determine exactly which edition-specific unlock or selection behavior they control.

## Metal Masters relationship

Metal Masters is a larger executable/overlay evolution rather than a trivial revision:

- Fusion: 77 ARM9 overlays
- Masters: 97 ARM9 overlays
- Fusion: 5,541 NitroFS files
- Masters: 4,774 NitroFS files

Even so, the games share 1,046 exact NitroFS paths. Of those, 99 are byte-identical at the same path. Across all paths, 304 Masters files have a byte-identical Fusion counterpart.

The strongest same-path reuse is in effects and field-common resources:

- `eff`: 222 shared paths, 86 byte-identical
- `fldcom`: 30 shared paths, 8 byte-identical
- `cam`: 2 shared paths, both byte-identical
- `bey`: 658 shared paths, 1 byte-identical at the same path

This is enough reuse to justify a comparative engine/content-pipeline approach rather than treating Metal Masters as unrelated.

## Working RE strategy

1. Treat `BBUY` as the canonical Fusion base for deep executable analysis.
2. Map the tiny `BBUX` / `BBUZ` ARM9 deltas as edition selectors/unlocks.
3. Catalogue Fusion NitroFS formats and NARC families once.
4. Build overlay maps and function maps for Fusion.
5. Map content tables: Beys, characters, moves, stats, camera/effect associations, unlocks, save representation.
6. Compare Masters overlays/functions against the Fusion map to identify inherited and new systems.
7. Build cross-game asset/content ID translation tables.
8. Keep full extracted assets and binaries in ignored generated directories; commit only tooling, hashes, schemas, labels, compact reports, and derived metadata.

## Reproduction

Run the scanner on local ROMs:

```bash
python3 tools/nds/scan_rom.py --compact --output analysis/generated/rom-scan.json roms/*.nds
```

Omit `--compact` when a complete per-file NitroFS hash map is needed. The full output belongs under `analysis/generated/` and is ignored by Git.

## Next checkpoint

The next checkpoint should contain:

- exact Fusion edition ARM9 delta locations after BLZ decompression
- ARM9/overlay compression inventory
- overlay ID → RAM/ROM/file map
- first-pass SDK/library signatures
- NARC family inventory
- Bey resource naming/ID map
- candidate master tables and executable consumers
