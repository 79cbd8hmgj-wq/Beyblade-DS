# Reverse-engineering checkpoint 02

## Scope

This checkpoint moves from ROM-level comparison into engine-owned Bey resource lookup structures and overlay evidence.

The canonical deep-analysis targets remain:

- Metal Fusion Collector's Edition (`BBUY`) for the shared Metal Fusion engine
- Metal Masters (`BRZE`) for the evolved engine

The commercial ROMs and decompressed binaries remain local/ignored inputs.

## Fusion editions: executable normalization

The earlier comparison found 23–33 differing bytes outside the DS secure area. Those bytes have now been structurally decoded.

There are exactly **13 differing ARM instructions** after decompressed ARM9 offset `0x4000`. Every one is an ARM `BLX` immediate whose target lies inside the per-ROM secure area.

Twelve call sites target a two-instruction Thumb stub equivalent to:

```text
SWI 3
BX  LR
```

The remaining call at runtime `0x020C2A80` targets:

```text
SWI 0xB
BX  LR
```

The stub locations differ by cartridge:

| Edition | SWI 3 stub | SWI 0xB stub |
|---|---:|---:|
| BBUY | `0x020004AC` | `0x02000284` |
| BBUX | `0x0200036E` | `0x020005E6` |
| BBUZ | `0x02000154` | `0x020006E4` |

After canonicalizing those 13 branch instructions, the three decompressed ARM9 binaries are **byte-identical from offset `0x4000` through the end of ARM9**.

This is stronger than the previous "nearly identical" conclusion. The observed post-secure-area differences are relocation artifacts caused by different secure-area layouts, not separate retailer-specific gameplay implementations.

The actual mechanism selecting Collector's/Toys'R'Us/Walmart content remains unresolved. Since the shared executable, overlays, ARM7, and NitroFS are otherwise identical, the next search should focus on common code reading cartridge/header/runtime state or on default/save initialization rather than on edition-specific code blocks.

## Correct Nintendo BLZ interpretation

The initial overlay experiment exposed a decoder bug. The BLZ footer's 24-bit compressed-length value **includes the BLZ header itself**. Bytes before that compressed region are an uncompressed prefix and must remain verbatim.

A regression fixture now covers this boundary case.

With the corrected decoder:

| Game | ARM9 overlays | Compressed | Decompressed-size matches | Failures |
|---|---:|---:|---:|---:|
| Fusion BBUY | 77 | 77 | 77 | 0 |
| Masters BRZE | 97 | 97 | 97 | 0 |

Total compressed/decompressed overlay bytes:

- Fusion: `619,504` -> `1,286,688`
- Masters: `707,752` -> `1,404,832`

This makes every ARM9 overlay available for deterministic static string, pointer, and instruction analysis.

## Confirmed Bey resource lookup architecture

Both engines keep two separate ARM9-owned lookup structures:

1. a flat model-NARC path pointer array
2. a texture descriptor array containing texture NARC path, member filename, and a zero field

### Metal Fusion

Model table:

- decompressed ARM9 offset: `0x000D7C60`
- runtime: `0x020D7C60`
- count: **858**
- stride: `4`
- end-exclusive: `0x000D89C8`
- entry: pointer to a `/bey/NN_NNN.narc` string

Texture table:

- decompressed ARM9 offset: `0x000D89C8`
- runtime: `0x020D89C8`
- count: **858**
- stride: `12`
- end-exclusive: `0x000DB200`
- record: `{ texture_narc_path_ptr, texture_member_name_ptr, 0 }`

All 858 model NARCs contain one LZ11-compressed `BMD0` member. All 858 texture NARCs contain one LZ11-compressed `BTX0` member.

Prefix-group counts:

| Prefix | Count |
|---|---:|
| `00` | 93 |
| `01` | 172 |
| `02` | 148 |
| `03` | 113 |
| `04` | 128 |
| `05` | 44 |
| `06` | 86 |
| `07` | 74 |

Every one of the 1,716 Fusion `bey/*.narc` filesystem resources is represented by an ARM9 path string.

### Metal Masters

Model table:

- decompressed ARM9 offset: `0x0005EB3C`
- runtime: `0x0205EB3C`
- count: **666**
- stride: `4`
- end-exclusive: `0x0005F5A4`

Texture table:

- decompressed ARM9 offset: `0x0005F5A4`
- runtime: `0x0205F5A4`
- count: **666**
- stride: `12`
- end-exclusive: `0x000614DC`

Prefix-group counts:

| Prefix | Count |
|---|---:|
| `00` | 96 |
| `01` | 182 |
| `02` | 120 |
| `03` | 134 |
| `04` | 134 |

The Masters filesystem contains 670 physical model/texture pairs. Four pairs are absent from the ARM9 path tables:

- `03_047` / `03_047t`
- `03_048` / `03_048t`
- `03_154` / `03_154t`
- `03_155` / `03_155t`

Each of those eight NARCs has a unique hash within the Masters Bey directory. They are therefore not simple duplicate files. They remain candidates for dynamically constructed references, unused content, or another lookup mechanism.

## Important table-boundary correction

The earlier exploratory note described an 859-entry Fusion pointer run and a 667-entry Masters run. The extra entry is now understood: it is the first texture-NARC pointer of the immediately following 12-byte texture descriptor table.

The supported boundaries are therefore:

- Fusion: **858 model pointers**, then 858 texture descriptors
- Masters: **666 model pointers**, then 666 texture descriptors

The two tables are independent permutations. Model-table index `i` does **not** pair with texture-table index `i` by filename.

## Overlay debug/name anchors

Fusion overlay 0 (`0x021D12C0`, decompressed size `0x3AC0`) contains a dense developer/debug label block with character indices and Bey variant names.

Confirmed character labels include:

- `00:GINGA`
- `01:KYOYA`
- `02:BENKEI`
- `03:DAIDOUJI`
- `04:KENTA`
- `05:HIKARU`
- `06:RYUGA`
- `08:HYOMA`
- `09:TSUBASA`
- `10:YUU`
- `11:TOBIO`

The table continues through index 37 with dummy, generic, Fury, and `NOS_*` debug labels.

Bey variant labels include A-D variants for major names such as:

- `PEGASIS_*`
- `LEONE_*`
- `SAGITTARIO_*`
- `AQUARIO_*`
- `BULL_*`
- `CANCER_*`
- `VOLF_*`
- `LDRAGO_*`
- `ARIES_*`
- `AQUILA_*`
- `LIBRA_*`
- `CYBERPEGASIS_*`

The same overlay contains developer-menu strings for Cyber Pegasus, Counter Leone, Shadow Saggitario, sound testing, and debug mode.

Masters overlay 1 contains related anchors including `Eldrago`, `MEldrago`, `LDRAGO_A`, `LDRAGO_B`, `GEMIOS_A`, `GEMIOS_B`, `BeybladeDS - SOUND TEST`, and `BeybladeDS - EVENT FLAG`.

These labels are cross-reference anchors, not yet proof of canonical gameplay master-record layouts.

## Tooling added

- `tools/nds/blz.py`
  - corrected backward-LZ decompressor
- `tools/nds/resource_map.py`
  - automatically locates the ARM9 model pointer run and texture descriptor run from path/member strings
- `tests/test_blz.py`
  - synthetic regression for the compressed-length/header boundary
- `tests/test_resource_map.py`
  - synthetic resource-table detection test

Compact evidence is tracked in:

- `analysis/resources/bey-resource-tables.json`
- `analysis/overlays/compression-summary.json`
- `analysis/overlays/named-anchors.json`
- `analysis/comparison/fusion-executable-normalization.json`

## Verification

Local verification performed against the supplied ROMs:

```text
python3 -m unittest discover -s tests -v
```

Result: 2 tests passed.

Integration checks also verified:

- all 77 Fusion ARM9 overlays decompress successfully
- all 97 Masters ARM9 overlays decompress successfully
- every decompressed overlay length equals its overlay-table RAM size
- Fusion resource detector returns 858 model + 858 texture records
- Masters resource detector returns 666 model + 666 texture records

## Next RE targets

1. Find executable consumers of the model and texture lookup tables and recover the resource-ID namespaces.
2. Cross-reference overlay debug labels against model/texture IDs to locate the first canonical Bey definition records.
3. Determine the semantic meaning of filename prefix groups, especially why Fusion has `00`–`07` while Masters has `00`–`04`.
4. Trace the four Masters filesystem-only resource pairs for dynamic references or unused-content status.
5. Locate character/Bey/loadout records that bind model IDs, texture IDs, names, stats, moves, and ownership/unlock fields.
6. Identify the shared Fusion retailer-selection mechanism now that edition-specific executable code has been ruled out.
