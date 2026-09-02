# Reproduction commands

The source ROMs remain local and ignored.

```bash
python3 tools/nds/scan_rom.py --compact --output analysis/generated/rom-scan.json roms/*.nds
python3 tools/nds/content_map.py analysis/generated/fusion-arm9.dec.bin --compact --output analysis/generated/fusion-bey-resource-map.json
python3 tools/nds/content_map.py analysis/generated/masters-arm9.dec.bin --compact --output analysis/generated/masters-bey-resource-map.json
python3 -m unittest discover -s tests -v
python3 -m compileall -q tools tests
```

The decompressed ARM9 inputs are generated research artifacts and must not be committed. `scan_rom.py` contains the BLZ decompressor used to reconstruct those inputs from the immutable ROM ARM9 binaries.
