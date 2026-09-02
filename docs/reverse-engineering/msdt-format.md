# Masters MSDT message format

This document records findings completed late in reverse-engineering checkpoint 05 and **supersedes** the earlier checkpoint-05 statement that the `*.msdt` message-file format was unresolved.

## Confirmed structural container

For the inspected US Metal Masters message files, the container is:

```text
+0x00  u32 marker = message_count + 1
+0x04  message_count entries, 4 bytes each:
       u16 bank
       u16 payload_end_unit_inclusive
...    payload of 16-bit glyph/control units
```

Message zero begins at payload unit zero. Each later message begins at the previous message's inclusive end plus one. In every validated file, the final table entry ends on the final payload unit.

The payload is **not plain UTF-16**. It uses game-specific 16-bit glyph/control codes. `tools/nds/msdt.py` therefore exposes the raw units and only provides a deliberately conservative Latin-oriented display helper; unknown control values are not assigned invented semantics.

## Real-file validation

| File | Marker | Messages | Payload units |
|---|---:|---:|---:|
| `mes/mes_beyfile.msdt` | 25 | 24 | 776 |
| `mes/mes_item.msdt` | 3340 | 3339 | 16119 |
| `mes/mes_beyparts_cw.msdt` | 810 | 809 | 23103 |
| `mes/mes_beyparts_mw.msdt` | 625 | 624 | 5497 |
| `mes/mes_beyparts_tr.msdt` | 675 | 674 | 13451 |
| `mes/mes_beyparts_bt.msdt` | 676 | 675 | 13334 |

All observed table-bank fields in these six files are zero. That observation must not be generalized to all game message files until additional files are checked.

## `mes_item.msdt` namespace

The 3339-message item database aligns directly with the gameplay customization namespace reconstructed in checkpoints 04 and 05.

Observed ranges:

| Range | Role |
|---|---|
| `0..999` | short/component selection names; global selection namespace |
| `1000..1999` | parallel alternate/full display-name bank |
| `2000..2999` | blank in the supported US file |
| `3000..3020` | 21 ability names |
| `3100..3120` | 21 ability descriptions |
| `3200..3237` | `LOCK` plus 37 Special Move names |
| `3301..3338` | Special Move description text |

The first bank independently confirms the selection-ID partition used by executable code:

- Energy Ring: `0..399`
- Fusion Wheel: `400..599`
- Spin Track: `600..799`
- Performance Tip: `800..998`
- invalid/sentinel: `999`

Only the gameplay-record subsets of these reserved ranges are valid selectable part records; the wider message namespace reserves unused slots.

## Special Move mapping

Checkpoint 05 established that character-loadout record `+0x08` is a one-based Special Move selector. `mes_item.msdt` closes the message-name relationship:

```text
loadout value 0      -> no move / locked path
loadout value N 1..37
                    -> zero-based debug/mechanical move index N-1
                    -> mes_item message 3200 + N
```

Examples:

| Loadout ID | Debug index | Message | Display name |
|---:|---:|---:|---|
| 1 | 0 | 3201 | `CYCLONE BLAST` |
| 17 | 16 | 3217 | `FLYING IMPACT` |
| 20 | 19 | 3220 | `SAVAGE NOISE` |
| 24 | 23 | 3224 | `DARK STREAM` |
| 26 | 25 | 3226 | `BLADE OF LIGHT` |
| 36 | 35 | 3236 | `NOVA STRIKE` |
| 37 | 36 | 3237 | `ELEMENTAL RAGE` |

The full 37-entry mapping is tracked in `analysis/messages/masters-msdt-map.json`.

This resolves the **loadout selector -> localized Special Move name** link. The mechanical effect implementation, 1P/2P presentation-resource selection, and damage/effect behavior remain separate reverse-engineering targets.

## Tooling

`tools/nds/msdt.py` provides deterministic read-only parsing. It does not modify the ROM or message file.

Example:

```bash
python3 tools/nds/msdt.py path/to/mes_item.msdt --output analysis/generated/mes-item.json
```

`tests/test_msdt.py` covers inclusive message boundaries, invalid/non-monotonic tables, and the conservative Latin display helper.
