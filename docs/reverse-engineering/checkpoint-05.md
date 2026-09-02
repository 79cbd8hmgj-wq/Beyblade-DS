# Reverse-engineering checkpoint 05

## Scope

Checkpoint 05 follows the remaining boundary from checkpoint 04:

> Face / Face Bolt definition -> complete Bey/loadout -> four gameplay component IDs -> character/owner -> Special Move -> message/name relationship.

This checkpoint resolves the Masters character/loadout records, the Face/Energy-Ring render mapping, and the loadout Special Move selector. It also rejects an incorrect early interpretation of `mes/mes_beyfile.msdt`.

Commercial ROMs, decompressed executables, overlays, and message databases remain local/ignored inputs. Only compact derived evidence and reusable tooling are tracked.

## `mes_beyfile.msdt` is save-file UI text, not a Bey definition table

Checkpoint 04 identified `mes/mes_beyfile.msdt` as a high-priority lead because overlay 42 loads it and its binary header differs from the part-name message files.

Direct content inspection rejects the hypothesis that it is the complete-Bey database. Its strings include save/load UI text such as:

- `LOADING`
- `NOT TURN THE POWER / REMOVE THE GAME CARD`
- `SELECT SLOT`
- `LOAD THIS SLOT`
- `START NEW GAME WITH SAVE SLOT`
- `DELETE THIS DATA`
- save-corruption text

Overlay 42 uses the file through the message/UI path. The filename's `beyfile` label therefore refers to a game/save-file interface rather than a complete Beyblade record set.

This rejection is useful because it redirects complete-Bey discovery to executable data instead of forcing an unsupported interpretation onto the MSDT format.

The message-file format itself remains unresolved. In particular, the first little-endian words of `mes_beyfile.msdt` and the four `mes_beyparts_*.msdt` files are still not assigned semantic labels without a parser/code proof.

## Masters character/loadout table

A fixed executable table begins at:

```text
0x0205D834
```

and ends exclusively at:

```text
0x0205EAF4
```

Its shape is:

- 40 character groups
- 10 variants per character
- 12 bytes per variant
- `0x78` / 120 bytes per character group
- 400 physical records total

All ten variants inside every character group are byte-identical in the supported US Metal Masters ROM. The ten-slot dimension is therefore confirmed structurally, but its intended semantic purpose is not yet known.

The 40 group indices align exactly with the 40-entry Masters `character_debug` enum already reconstructed from overlay 1. This strongly supports group index as character/owner ID.

### Record layout

| Offset | Size | Interpretation | Confidence |
|---|---:|---|---|
| `+0x00` | 2 | Energy Ring gameplay ID, `0..126` | confirmed |
| `+0x02` | 2 | Fusion Wheel global selection ID, `400..500` | confirmed |
| `+0x04` | 2 | Spin Track global selection ID, `600..706` | confirmed |
| `+0x06` | 2 | Performance Tip global selection ID, `800..906` | confirmed |
| `+0x08` | 2 | one-based Special Move selector; `0` = none | strongly_supported |
| `+0x0A` | 2 | `field_0a_u16` | unknown |

### Component consumer

The primary loadout consumer at `0x0201D3CC`:

1. accepts participant, character/group, and variant values,
2. rejects/reset variants above 9,
3. calculates `0x0205D834 + character * 0x78 + variant * 0x0C`,
4. reads the first four halfwords,
5. validates each against the corresponding customization category,
6. feeds those selections into the existing component/runtime setup path.

A second consumer around `0x0201B364` validates character/group values below 40 and reads the variant-zero component fields for UI/gameplay use.

Overlay 4 also indexes the same table using character-group stride `0x78`, independently supporting the table dimensions.

## Canonical character ownership mapping

Because every variant currently duplicates variant zero, checkpoint tooling exports one canonical row per character. The first rows are illustrative:

| ID | Character | Ring | Wheel | Track | Tip | Special |
|---:|---|---:|---:|---:|---:|---:|
| 0 | GINGA | 22 | 402 | 625 | 817 | 1 |
| 1 | TSUBASA | 68 | 456 | 659 | 847 | 17 |
| 2 | MASAMUNE | 28 | 422 | 641 | 800 | 20 |
| 3 | RYUGA | 7 | 418 | 623 | 811 | 24 |
| 4 | KENTA | 72 | 462 | 668 | 870 | 31 |
| 5 | KYOYA | 56 | 444 | 663 | 846 | 19 |

All 40 canonical rows are tracked in `analysis/components/masters-character-loadouts.json`.

## `+0x08` is the Special Move selector

Multiple independent consumers support the interpretation.

### Direct accessor

`0x0201E1C4` returns the halfword at variant-zero record `+0x08` for a character group.

### Participant setup

`0x0201D180` reads the selected character/variant record and stores the `+0x08` value into the participant runtime state at approximately `+0xFC`.

Overlay 1 performs the same initialization for both participants. When an override structure supplies a zero-based move value, overlay 1 adds one before storing it into the participant field. This establishes a one-based runtime representation.

### UI/message consumer

Overlay 4 reads participant `+0xFC`:

- zero skips the Special Move entry,
- nonzero is converted into the corresponding Special Move message selector before rendering.

### Debug enum correlation

Masters contains 37 zero-based Special Move debug IDs (`0..36`). Canonical loadout `+0x08` values occupy `1..37`. Therefore:

```text
loadout value 0     -> no Special Move
loadout value N>0   -> debug/mechanical Special Move index N-1
```

The exact relationship between the mechanical move enum, 1P/2P presentation variants, and all localized message IDs still warrants a dedicated move/message pass, but the loadout field role itself is strongly supported.

## Face / Face Bolt is derived through the Energy Ring selection path

Checkpoint 04 established four gameplay component tables and a separate five-part renderer. Checkpoint 05 resolves the missing bridge.

A 127-entry pair table begins at:

```text
0x02059890
```

Each eight-byte record is:

```text
u32 face_resource_id
u32 energy_ring_resource_id
```

The count of 127 exactly matches the Energy Ring gameplay table.

`0x0201B8D0` indexes this pair table using the Energy Ring ID and returns both values. `0x0201D730` uses the result during participant resource setup and stores 1-based renderer IDs for:

- Face at participant `+0x10E`
- Energy Ring at participant `+0x110`

Fusion Wheel, Track, and Tip render IDs are then resolved from their own selected component IDs.

### Supported conclusion

Masters has five independently rendered physical parts, but the canonical gameplay-selection/loadout path stores four gameplay part selections. The Face render identity is derived from the selected Energy Ring through the `0x02059890` pair table.

This does **not** yet prove that Face has no mechanics elsewhere. It proves only that no independent Face entry exists in the four 20-byte component-record path and that the battle renderer obtains Face identity from the Energy Ring mapping at this stage.

## Unknown `+0x0A` field

The final loadout halfword remains neutral.

Canonical variant-zero distribution:

- `0`: 38 characters
- `11`: character 24 (`DJ`) and character 25 (`ZAKO_A`)

No direct literal reference to table address `0x0205D83E` was found in the main ARM9 or the scanned overlay set. This is not proof that the field is unused because code may read it through a computed record pointer.

Until a consumer is found, the field remains:

```text
field_0a_u16
```

with confidence `unknown`.

## New tooling and compact evidence

Added:

- `tools/nds/loadout_map.py`
- `tests/test_loadout_map.py`
- `analysis/components/masters-character-loadouts.json`

`loadout_map.py` accepts a caller-supplied decompressed Masters ARM9 image, validates the known table ranges, parses all 400 records, verifies the ten duplicate variants when requested, derives category-local IDs, and resolves Face/Energy-Ring renderer IDs.

Example:

```bash
python3 tools/nds/loadout_map.py \
  path/to/masters-arm9-decompressed.bin \
  --output analysis/generated/masters-character-loadouts.json
```

The source image is never modified.

## Verification

The new parser was exercised against the supported real Masters ARM9 and produced:

- 400 parsed records
- 40 canonical character rows
- ten byte-identical variants for every character group
- valid Energy Ring IDs `0..126`
- valid Fusion Wheel IDs `400..500`
- valid Track IDs `600..706`
- valid Tip IDs `800..906`
- Face/Energy-Ring pair lookup inside all 127 mapped records

The focused regression suite for the new parser passes three tests covering:

1. full record parsing and derived local/resource IDs,
2. duplicate-variant validation failure,
3. canonical report shape and `field_0a_u16` distribution.

Python compilation checks for the new tool and test also pass.

## Remaining unknowns / next targets

1. **`field_0a_u16`.** Find computed-record consumers and determine why DJ and ZAKO_A carry value 11.
2. **Ten-variant dimension.** The executable reserves ten records per character even though all are identical in this ROM; determine whether another mode/save/customization path can populate alternatives at runtime.
3. **Whole-Bey display naming.** No dedicated `mes_beyname` file has been found. Trace the UI path that assembles/displays complete Bey names from part/message data before claiming a composition model.
4. **Face mechanics.** The Face renderer mapping is established; search for any independent gameplay modifiers or flags derived from the Face resource/paired Ring mapping.
5. **Special Move mechanics/message translation.** Finish the one-based loadout selector -> zero-based move mechanics -> 1P/2P presentation -> localized message chain.
6. **Fusion equivalent.** Apply the Masters loadout/resource architecture to Metal Fusion and construct cross-game character/loadout/component translations.
7. **Persistence.** Locate save/load structures that store selected custom parts versus fixed character templates, especially if the ten-variant dimension reflects saved loadouts.
