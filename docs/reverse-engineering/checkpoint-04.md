# Reverse-engineering checkpoint 04

## Scope

Checkpoint 04 resolves the indirection layer left open by checkpoint 03: Metal Masters gameplay component IDs, customization IDs, component-definition records, runtime loadout state, and component stat/effect aggregation.

The commercial ROM, decompressed ARM9, overlays, and message databases remain local/ignored inputs. Only derived structure, tooling, and compact evidence are tracked.

## Nitro ARM9 runtime mapping correction

A flat `runtime = 0x02000000 + decompressed_file_offset` model is not valid for the whole ARM9 image. Nitro module parameters define static BSS and autoload source regions. Bytes stored late in the decompressed ARM9 are copied into ITCM/DTCM during startup and are not resident at the corresponding `0x020xxxxx` file-offset address.

### Metal Masters

- module parameters: `0x02000B88`
- static BSS: `0x02073540–0x021B8700`
- ITCM autoload destination: `0x01FF8000`, data size `0x4980`
- DTCM autoload destination: `0x027E0000`, data size `0x60`, BSS size `0x1480`

### Metal Fusion

- module parameters: `0x02000B68`
- static BSS: `0x02101240–0x021D12C0`
- ITCM autoload destination: `0x01FF8000`, data size `0x57C0`
- DTCM autoload destination: `0x027E0000`, data size `0x60`, BSS size `0x13C0`

`tools/nds/module_params.py` now parses the module parameters and maps a runtime address as static, static BSS, autoload data, autoload BSS, or unmapped.

This correction is important for every later runtime-structure analysis. For example, `0x020745C0` and `0x021AF524` in Masters are BSS globals/runtime objects, even though same-offset bytes exist in the decompressed file as autoload source material.

## Masters customization namespace

ARM9 functions `0x0201AF78` and `0x0201AFD0` decode the low ten bits of a customization selection ID into a category and category-local index.

Reserved global selection ranges are:

| Category | Global range | Local conversion |
|---|---:|---:|
| Energy Ring / Clear Wheel | `0x000–0x18F` | unchanged |
| Fusion Wheel / Metal Wheel | `0x190–0x257` | `id - 0x190` |
| Track | `0x258–0x31F` | `id - 0x258` |
| Performance Tip / Bottom | `0x320–0x3E6` | `id - 0x320` |
| Invalid/sentinel | `0x3E7` | no record |

Overlay 46 independently establishes the category order. It loads:

- slot 1: `mes/mes_beyparts_cw.msdt`
- slot 2: `mes/mes_beyparts_mw.msdt`
- slot 3: `mes/mes_beyparts_tr.msdt`
- slot 4: `mes/mes_beyparts_bt.msdt`

and contains the category resource stems `o4_c`, `o4_m`, `o4_t`, and `o4_b`.

The message-file binary format itself is not yet reconstructed. In particular, the first little-endian word is not currently assigned a semantic name; a naive file-offset-table interpretation was tested and rejected.

## Confirmed gameplay component master tables

`0x0201B188` is the component record accessor. It:

1. decodes the global selection ID category,
2. converts it to a category-local index,
3. selects one of four table bases,
4. returns `base + index * 0x14`.

`0x0201B024` supplies the gameplay record limits. These limits are smaller than some checkpoint-03 render-binding segment capacities, proving that render-resource capacity and gameplay component count are distinct concepts.

| Category | Table start | Count | End-exclusive | Selection base |
|---|---:|---:|---:|---:|
| Energy Ring | `0x0205BA44` | **127** | `0x0205C430` | `0x000` |
| Fusion Wheel | `0x0205A1A8` | **101** | `0x0205A98C` | `0x190` |
| Track | `0x0205A98C` | **107** | `0x0205B1E8` | `0x258` |
| Performance Tip | `0x0205B1E8` | **107** | `0x0205BA44` | `0x320` |

The Wheel, Track, and Bottom tables are exactly contiguous. Energy Ring follows after the Bottom table.

### Important correction to checkpoint-03 interpretation

Checkpoint 03 identified one render-context half of the Masters binding segments as:

- Face: 130
- Energy Ring: 206
- Fusion Wheel: 101
- Track: 107
- Bottom: 107

Only Fusion Wheel, Track, and Bottom happen to match the gameplay counts exactly. Energy Ring has 127 gameplay records but a 206-entry render half. Therefore a render binding slot is not automatically a gameplay component record.

Face / Face Bolt is not handled by the four-category accessor at `0x0201B188` and remains a separate subsystem.

## Twenty-byte component record

The supported structural layout is:

| Offset | Size | Current meaning |
|---|---:|---|
| `+0x00` | 4 | `field_00_u32`; rendered as a decimal number in customization UI, exact semantic unresolved |
| `+0x04` | 4 | `field_04_bytes[4]`; individual bytes have consumers but incomplete semantics |
| `+0x08` | 4 | primary stat/effect script pointer |
| `+0x0C` | 4 | optional secondary stat/effect script pointer |
| `+0x10` | 4 | `field_10_bytes[4]`; individual bytes have consumers but incomplete semantics |

Known consumers include:

- `+0x00`: passed to decimal-number renderer `0x020085AC`
- `+0x05`: consumed as an enum/label-like value and used during participant setup
- `+0x07`: compared between records by customization compatibility logic
- `+0x08`: primary script
- `+0x0C`: secondary script
- `+0x10`: one byte copied into participant derived state
- `+0x12`: consumed by overlay-46 UI logic

These fields remain neutrally named where evidence does not yet identify their gameplay semantics.

## Component stat/effect script format

`0x0201B724` dispatches a compact script of repeated four-byte entries:

```text
u16 opcode
s16 value
```

Opcode `0` terminates the list. Supported opcodes are `1–10`.

Opcodes `1–9` add the signed value to consecutive `s16` fields at vector offsets:

```text
opcode 1 -> +0x00
opcode 2 -> +0x02
...
opcode 9 -> +0x10
```

Opcode `10` writes/adds the value at `+0x12`.

### Additive nine-field vector

`0x0201DC80` adds vector fields `+0x00..+0x10` field-by-field and then calls `0x0201DD1C`.

`0x0201DD1C`:

1. clamps each of those nine signed fields to a minimum of zero,
2. compares each against the nine-element maximum vector at `0x0205C43C`,
3. clamps every maximum to **25**.

Therefore opcodes `1–9` form a nine-field additive component-stat vector with final range `0..25` in this aggregation path.

The exact names of those nine fields are not yet assigned.

### Opcode 10 is separate

The normal vector adder does **not** add `+0x12`. `0x0201D908` instead extracts selected `+0x12` values independently from per-component vectors into participant fields near `+0x150`.

Real data reinforces the distinction:

- Fusion Wheel opcode-10 values are zero in the mapped gameplay records.
- Energy Ring, Track, and Bottom records use nonzero opcode-10 values.

Opcode 10 should therefore remain a separate categorical/behavior parameter until its consumers establish semantics; it is not treated as a tenth additive stat.

## Per-component script coverage

Real Masters ARM9 parsing gives:

| Category | Records | Primary pointers | Primary records with nonzero contribution | Secondary pointers | Secondary nonzero |
|---|---:|---:|---:|---:|---:|
| Energy Ring | 127 | 127 | 87 | 6 | 6 |
| Fusion Wheel | 101 | 101 | 61 | 0 | 0 |
| Track | 107 | 107 | 69 | 13 | 13 |
| Performance Tip | 107 | 107 | 69 | 2 | 2 |

A script pointer may therefore exist even when all of its numeric contributions are zero.

## Stat aggregation pipeline

The primary component path is now mapped:

- `0x0201B188` — resolve component record
- `0x0201B54C` — apply primary script from record `+0x08`
- `0x0201B590` — apply optional secondary script from record `+0x0C`
- `0x0201B724` — effect/stat script dispatcher
- `0x0201DAD0` — build four primary 0x14-byte vectors
- `0x0201DBCC` — build four secondary 0x14-byte vectors
- `0x0201DC58` — build an additional 0x14-byte vector from another runtime source
- `0x0201DC80` — add nine vector fields and clamp
- `0x0201D908` — aggregate participant stats and preserve selected opcode-10 values
- `0x0201DA48` — high-level participant component/stat setup

The high-level participant base is:

```text
0x020745C0 + participant_index * 0x158
```

Within that structure:

- aggregate vector: `+0x00`
- four primary per-part vectors: `+0x14`
- four secondary per-part vectors: `+0x64`
- additional vector: `+0xB4`
- pointers to selected component entries: `+0xC8,+0xCC,+0xD0,+0xD4`
- normalized selection IDs: `+0xD8,+0xDC,+0xE0,+0xE4`
- derived type/state bytes near `+0x108/+0x10C`
- five derived resource halfwords: `+0x10E..+0x116`

## Customization to battle handoff

Global `0x020749CC` stores packed 16-bit customization selection IDs. The low ten bits carry the global selection ID described above.

Battle setup validates the four slots against the expected category ranges and stores both pointers and normalized IDs in the participant structure.

This is the first confirmed bridge from menu/equipment selection state to battle participant component/stat state.

## Five-part render/resource state

A separate runtime resource manager lives at BSS global `0x021AF524`.

The active resource-state object maintains two snapshots:

- old/loaded five-part IDs at `+0x18..+0x20`
- current five-part IDs at `+0x2C..+0x34`
- dirty/change bitmask at `+0x10`

`0x02021524` compares the snapshots and marks only changed component categories for resource reload.

For this render/resource path, category order is the full five-part Metal system:

1. Face
2. Energy Ring
3. Fusion Wheel
4. Track
5. Performance Tip

Stored resource values use:

- `0` = none
- nonzero = subtract 1 before zero-based resource lookup

This five-part render state is distinct from the four-category gameplay component-record accessor above.

## Reserved/special component IDs

`0x0201B024` treats four selection IDs specially while iterating ordinary availability:

- Energy Ring: global `0x074`, local 116
- Fusion Wheel: global `0x1EA`, local 90
- Track: global `0x2B8`, local 96
- Bottom: global `0x380`, local 96

These positions align near the end of normal message-backed content ranges, but their exact semantics remain unresolved. They may be special, reserved, hidden, or placeholder definitions. No stronger label is assigned yet.

## Tooling and compact evidence

Added:

- `tools/nds/module_params.py`
- `tools/nds/component_records.py`
- `tests/test_module_params.py`
- `tests/test_component_records.py`

Tracked evidence:

- `analysis/runtime/module-params.json`
- `analysis/components/masters-component-tables.json`
- `analysis/components/runtime-component-state.json`
- `analysis/components/customization-ui.json`

`component_records.py` parses the 20-byte records and their primary/secondary effect scripts without modifying the source ARM9.

## Verification

The checkpoint tool set was combined with the previous BLZ/resource/binding regressions and run locally:

```text
python3 -m unittest discover -s tests -v
```

Result before final branch verification: **7 tests passed, 0 failed**.

Python compilation checks also passed for the checkpoint tools.

Real-ROM integration checks parsed all four Masters gameplay component tables with the exact counts above and validated every referenced effect-script opcode as `0–10` with no out-of-bounds script pointer in these tables.

## Remaining unknowns / next targets

1. **Face / Face Bolt definition path.** It is not part of the four 20-byte gameplay tables and must be reconstructed separately.
2. **Complete Bey / loadout records.** Locate records binding Face plus the four global selection IDs, character ownership, names, and move/special-move IDs.
3. **Nine stat names.** Trace aggregate vector fields into battle/UI consumers before assigning Attack/Defense/Stamina/etc. labels.
4. **Opcode-10 semantics.** It is separate from additive stats and requires consumer tracing.
5. **Record scalar fields.** Resolve `field_00_u32`, bytes at `+0x04..+0x07`, and `+0x10..+0x13` from UI and battle consumers.
6. **Message database format.** Reconstruct `*.msdt` rather than assuming the first word or following data layout.
7. **Fusion equivalent tables.** Apply the now-understood Masters architecture to Metal Fusion and build cross-game ID translation.
8. **`mes_beyfile.msdt` / overlay 42.** This is the highest-priority complete-Bey/Face/loadout lead for the next checkpoint.
