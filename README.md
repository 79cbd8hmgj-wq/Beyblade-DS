# Beyblade DS Reverse Engineering

Comparative reverse-engineering workspace for the US Nintendo DS releases of Beyblade: Metal Fusion and Beyblade: Metal Masters.

## Local ROM inputs

Commercial ROMs are not stored in this repository. Place legally supplied `.nds` inputs under `roms/`; that directory is ignored by Git.

The current supported research set is documented in `analysis/roms/rom-identities.json`.

## Tooling

The repository contains the existing NDS disassembly and ROM-mod toolkit archives plus project-specific analysis code under `tools/`.

Initial scanner:

```bash
python3 tools/nds/scan_rom.py --compact roms/*.nds
```

For full NitroFS hashes:

```bash
python3 tools/nds/scan_rom.py --output analysis/generated/rom-scan.json roms/*.nds
```

## Current result

The three Metal Fusion retail editions share an identical NitroFS tree and identical overlays. Their decompressed main ARM9 binaries differ by only a few dozen bytes outside the secure area, so they are treated as one shared RE target plus edition-specific executable deltas.

Metal Masters has a larger executable/overlay layout but substantial path and asset reuse with Fusion, making comparative analysis useful.

See `docs/reverse-engineering/checkpoint-01.md` for the current evidence and next targets.
