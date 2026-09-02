# Reverse-engineering checkpoint 03

## Scope

This checkpoint traces the ARM9 Bey resource lookup tables into executable consumers, reconstructs the second-level model/texture binding arrays, identifies the primary physical-part resource namespaces, and promotes overlay debug labels into exact `{string pointer, numeric ID}` enum evidence.

Canonical targets remain:

- Metal Fusion Collector's Edition (`BBUY`) for the shared Fusion executable
- Metal Masters (`BRZE`) for the evolved engine

No commercial ROM, decompressed executable, or extracted asset is tracked.

## Second-level Bey resource binding architecture

Checkpoint 02 found independent ARM9 model-path and texture-descriptor tables. The engine also owns a higher-level array of 8-byte binding records:

```text
struct BeyResourceBinding {
    u32 model_pointer_entry;      // points into the 4-byte model-path pointer table
    u32 texture_descriptor;       // points into the 12-byte texture descriptor table
};
```

For every resolved record, the model NARC stem and texture NARC stem match.

### Metal Fusion

Contiguous binding run:

- runtime start: `0x020DB200`
- count: **929**
- stride: `8`
- unique model indices: **858**
- unique texture indices: **858**
- unique model/texture pairs: **858**
- matching model/texture stems: **929 / 929**

The repeated rows fill context/default slots; the run still covers every unique model/texture pair exactly at least once.

Physical category segments:

| Prefix | Binding base | Rows | Model selector | Texture selector | Supported semantic |
|---|---:|---:|---:|---:|---|
| `00` | `0x020DB8C0` | 93 | 0 | 1 | Face / Face Bolt |
| `01` | `0x020DC928` | 188 | 1 | 2 | Clear Wheel / Energy Ring |
| `02` | `0x020DC3A8` | 176 | 2 | 3 | Metal Wheel / Fusion Wheel |
| `03` | `0x020DBBA8` | 128 | 3 | 4 | Track |
| `04` | `0x020DBFA8` | 128 | 4 | 5 | Bottom / Performance Tip |
| `05` | `0x020DB200` | 44 | 5 | 6 | alternate Face model family |
| `06` | `0x020DB5E0` | 92 | 6 | 7 | alternate Clear Wheel model family |
| `07` | `0x020DB360` | 80 | 7 | 8 | alternate Metal Wheel model family |

The semantics are **strongly supported**, not inferred only from franchise naming. Representative decompressed BMD0 model names include Face-like `*_f` names under `00`, Clear Wheel `*_cw*` names under `01`, Metal Wheel `*_mw*` names under `02`, track-style `t_*` names under `03`, and bottom-style `b_*` names under `04`.

Fusion also contains `cus` customization-model names within the physical `01`–`04` families. Prefixes `05`–`07` are therefore conservatively named alternate Face/Clear-Wheel/Metal-Wheel model families; their exact scene or animation purpose is not yet proven.

### Metal Masters

Contiguous binding run:

- runtime start: `0x020614DC`
- count: **1302**
- stride: `8`
- unique model indices: **666**
- unique texture indices: **666**
- unique model/texture pairs: **666**
- matching model/texture stems: **1302 / 1302**

Category segments:

| Prefix | Binding base | Rows | Half size | Selector | Supported semantic |
|---|---:|---:|---:|---:|---|
| `00` | `0x0206288C` | 260 | 130 | 0 | Face / Face Bolt |
| `01` | `0x020630AC` | 412 | 206 | 1 | Clear Wheel / Energy Ring |
| `02` | `0x020614DC` | 202 | 101 | 2 | Metal Wheel / Fusion Wheel |
| `03` | `0x020621DC` | 214 | 107 | 3 | Track |
| `04` | `0x02061B2C` | 214 | 107 | 4 | Bottom / Performance Tip |

Every Masters segment is exactly two equal halves. Representative BMD0 names in the second half contain `cus`, while the first half uses the ordinary non-`cus` model naming. This strongly supports two render contexts per physical category, one of which is the customization context.

Examples from prefix `02` include ordinary names such as `wind_mw1s`, `storm_mw1s`, and `rock_mw1s`, followed in the second half by `wind_mw1cus`, `storm_mw1cus`, and `rock_mw1cus`.

The four Masters filesystem-only resource pairs identified in checkpoint 02 remain unresolved:

- `03_047` / `03_047t`
- `03_048` / `03_048t`
- `03_154` / `03_154t`
- `03_155` / `03_155t`

They are not represented in the normal ARM9 lookup/binding namespaces and must still be tested for dynamic construction, another lookup mechanism, or unused status.

## Executable consumers

### Fusion texture resource loader candidate

Function start:

- runtime `0x02025B30`

A switch at `0x02025D54` uses a selector and chooses a binding-table category. For selector values `1..8`, the function indexes the selected base by `id * 8` and reads record `+4`, the texture-descriptor pointer.

Selector mapping:

```text
1 -> prefix 00
2 -> prefix 01
3 -> prefix 02
4 -> prefix 03
5 -> prefix 04
6 -> prefix 05
7 -> prefix 06
8 -> prefix 07
```

Selector 9 follows a separate path and remains unresolved.

Observed overlay call sites include:

- `0x021EF5A4`
- `0x021F599C`
- `0x021F2E5C`
- `0x021D189C`
- `0x021FB978`

### Fusion model lookup/release candidate

Function:

- runtime `0x0202744C`

Arguments behave as resource ID and category `0..7`. The function selects the corresponding binding segment, computes `base + id * 8`, reads the first record field, dereferences the model-path pointer, and then calls `0x0200414C`.

Category `0..7` maps directly to prefixes `00..07`.

A secondary consumer around `0x02102C40` remains candidate.

### Masters texture resource loader candidate

Function start:

- runtime `0x0201F27C`

A switch at `0x0201F648` maps category `0..4` directly to prefixes `00..04`, computes `base + id * 8`, and reads record `+4`.

Observed overlay call sites include:

- `0x021ECF5C`
- `0x021EF408`
- `0x021EFA80`

### Masters model lookup/release candidate

Function:

- runtime `0x02020B2C`

The function selects prefix `00..04` from category `0..4`, computes `id * 8`, reads the first binding field, dereferences the model path, and calls `0x020046D0`.

Additional consumers at `0x02021434` and `0x02074288` remain candidates.

These functions establish that the filename prefixes are engine-owned category namespaces rather than incidental asset naming.

## Overlay debug enum records

Both games contain developer tables of 8-byte records:

```text
{ pointer_to_debug_string, u32 numeric_id }
```

These tables are important because they provide exact numeric IDs independently of filesystem filenames.

### Metal Fusion overlay 0

Overlay RAM base: `0x021D12C0`

#### Character debug table

- start: `0x021D3B30`
- count: **38**
- IDs: `0..37`

Includes `GINGA`, `KYOYA`, `BENKEI`, `DAIDOUJI`, `KENTA`, `HIKARU`, `RYUGA`, `TSUBASA`, `YUU`, generic opponents, and debug/dummy entries.

#### Fusion Wheel debug enum

- start: `0x021D3C60`
- count: **40**

IDs are grouped as four variants for each family:

- `STORM_A..D` = 1..4
- `ROCK_A..D` = 5..8
- `MAD_A..D` = 9..12
- `DARK_A..D` = 13..16
- `FLAME_A..D` = 17..20
- `WIND_A..D` = 21..24
- `LIGHTNING_A..D` = 25..28
- `CLAY_A..D` = 29..32
- `EARTH_A..D` = 33..36
- `CYBER_A..D` = 37..40

This corrects the earlier interpretation of these strings as complete-Bey names: this table is a component-ID enum.

#### Energy Ring debug enum

- start: `0x021D3DA0`
- count: **48**

Examples:

- `PEGASIS_A..D` = 1..4
- `LEONE_A..D` = 5..8
- `CANCER_A..D` = 9..12
- `VOLF_A..D` = 13..16
- `SAGITTARIO_A..D` = 17..20
- `AQUARIO_A..D` = 21..24
- `BULL_A..D` = 25..28
- `LDRAGO_A..D` = 29..32
- `ARIES_A..D` = 33..36
- `AQUILA_A..D` = 37..40
- `LIBRA_A..D` = 41..44
- `CYBERPEGASIS_A..D` = 49..52

IDs `45..48` are absent from this debug run.

#### Move debug tables

- shorthand move table: `0x021D39F0`, 18 records
- named Special Move table: `0x021D3A80`, 20 records

The complete exact records are tracked in `analysis/overlays/debug-enums.json`.

### Metal Masters overlay 1

Overlay RAM base: `0x021B8700`

#### Fusion Wheel debug enum

- start: `0x021BA844`
- count: **32**

Examples include exact IDs for `STORM`, `EARTH`, `RAY`, `LIGHTNING`, `FLAME`, `ROCK`, `DARK`, `CLAY`, `CYBER`, `WIND`, `BURN`, `POISON`, `THERMAL`, `KILLER`, `GALAXY`, and `MAD` A/B variants.

#### Special Move presentation enums

- 1P: `0x021BA944`, **37** records, IDs `0..36`
- 2P: `0x021BAA6C`, **37** records, IDs `0..36`

Both arrays use the same numeric IDs but separate `_1P` and `_2P` labels. This strongly supports a shared mechanical Special Move ID with player-side-specific presentation naming.

#### Character debug enum

- start: `0x021BAB94`
- count: **40**
- IDs: `0..39`

#### Energy Ring debug enum

- start: `0x021BACD4`
- count: **42**

The values are sparse and frequently much larger than the debug-table row number. This is direct evidence that component numeric IDs are **not** simply resource-binding array indices.

#### Bey/effect entity debug enum

- start: `0x021BAE24`
- count: **45**
- IDs: `0..44`

Labels include `Bull`, `Sazi`, `GPega`, `Pega`, `Scor`, `Uni`, `Aquira`, `Libra`, `Leone`, `Eldrago`, `CPega`, `MEldrago`, `Serpent`, and others. Its exact subsystem role remains unresolved, so it is intentionally tracked as `bey_effect_entity_debug` rather than promoted to a canonical Bey master table.

## Critical unresolved indirection

The debug component IDs do **not** directly index the binding arrays.

For example, a Masters debug component can have a numeric ID for which the same binding slot is a default/fallback resource or no physical same-number NARC exists. Therefore another component-definition or translation structure must convert gameplay component IDs into resource-binding slots and likely also bind names, stats, behavior, and unlock data.

This is now the highest-priority static target.

## Tooling added

- `tools/nds/binding_map.py`
  - finds contiguous 8-byte model/texture binding runs
  - resolves model and texture table indices
  - scans overlays for contiguous `{ASCII-string pointer, numeric ID}` debug enum runs
- `tests/test_binding_map.py`
  - synthetic regression for binding-run detection
  - synthetic regression for debug-enum detection

Tracked evidence:

- `analysis/resources/bey-binding-tables.json`
- `analysis/overlays/debug-enums.json`

## Verification

The branch test suite was reconstructed locally from the tracked files and run with:

```text
python3 -m unittest discover -s tests -v
```

Result:

```text
Ran 4 tests
OK
```

The new scanner was also run against the real decompressed ARM9 inputs and independently rediscovered:

```text
BBUY  0x020DB200  929 records   858 unique pairs
BRZE  0x020614DC 1302 records   666 unique pairs
```

The original ROMs were read only; no ROM bytes were modified.

## Next RE targets

1. Locate the **component ID -> resource binding slot** translation records.
2. Recover the actual Face, Energy Ring, Fusion Wheel, Track, and Performance Tip component definition tables.
3. Cross-reference those records against localized names, stats, effect IDs, Special Move IDs, and ownership/unlock fields.
4. Locate complete Bey/loadout records that bind the five component namespaces into assembled Beyblades.
5. Resolve Fusion texture-loader selector 9.
6. Resolve the Masters 45-entry `bey_effect_entity_debug` namespace.
7. Determine whether the four filesystem-only Masters Track pairs are dynamically referenced or unused.
8. Continue toward save/unlock and battle-effective stat structures only after the component indirection layer is identified.
