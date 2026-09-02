# Reverse-engineering checkpoint 02 — content and Bey resource layer

## Scope

This checkpoint moves past ROM-container comparison and maps the first inherited executable/content subsystem shared by Metal Fusion (`BBUY` canonical base) and Metal Masters (`BRZE`). Commercial ROMs and extracted assets remain local immutable inputs.

Confidence vocabulary:

- **confirmed** — directly established by binary structure and reproducible parsing
- **strongly supported** — multiple static signals agree, but runtime confirmation would still improve the label
- **candidate** — plausible interpretation that should not yet be treated as a semantic fact

## Standard container and compression path

Both games use ordinary Nintendo `NARC` containers with `BTAF`, `BTNF`, and `GMIF` sections. `tools/nds/content_map.py` now parses these containers and implements bounded Nintendo LZ11 decompression.

The `/bey` resource family is unusually clean:

| Game | `/bey` files | model NARCs | texture NARCs | model inner format | texture inner format |
|---|---:|---:|---:|---|---|
| Metal Fusion | 1,716 | 858 | 858 | LZ11 → `BMD0` | LZ11 → `BTX0` |
| Metal Masters | 1,340 | 670 | 670 | LZ11 → `BMD0` | LZ11 → `BTX0` |

Every `/bey/*.narc` in both supplied canonical ROMs validated under that model/texture split. This gives the project a deterministic model/texture extraction boundary without requiring guessed formats.

Other major content families continue to use `ASBA`, `RLCN`, `RGCN`, screen/tile data, effect records, and multi-member NARCs. `ASBA` is still only identified as a wrapper/signature family; its complete compression semantics are deliberately unresolved here.

## ARM9 overlay map

The overlay-table compression flag is set on every ARM9 overlay in both games:

| Game | ARM9 overlays | IDs | compressed |
|---|---:|---|---:|
| Metal Fusion | 77 | 0–76 | 77 |
| Metal Masters | 97 | 0–96 | 97 |

The full per-overlay ID/RAM/ROM/file/hash map is reproducible with `tools/nds/scan_rom.py`; compact tracked totals live in `analysis/content/overlay-summary.json`.

## Embedded SDK/library signatures

Metal Fusion's decompressed ARM9 contains confirmed strings for:

- Nintendo DWC 3.1 plus 6
- Nintendo WiFi 2.1
- Ubiquitous CPS
- Ubiquitous SSL
- Nintendo BACKUP

Metal Masters retains a confirmed Nintendo BACKUP signature in its decompressed ARM9. The smaller signature set is not evidence that the other libraries are absent; only that their equivalent signature strings were not found in the same scan scope.

Exact offsets are tracked in `analysis/content/library-signatures.json`.

## Confirmed Bey resource-table architecture

The decompressed ARM9 in both games contains the same three-stage lookup design:

1. a contiguous pointer array to physical `/bey/...narc` model paths
2. an equally sized 12-byte texture-descriptor array
3. an 8-byte logical-usage array whose records point into the first two tables

### Metal Fusion

- model pointer array: `0x020D7C60`, 858 entries
- texture descriptor array: `0x020D89C8`, 858 × 12 bytes
- logical usage array: `0x020DB200`, 929 × 8 bytes

All 858 physical model resources appear in the model table. The logical table contains 929 records because some model/texture pairs are reused by multiple logical IDs.

### Metal Masters

- model pointer array: `0x0205EB3C`, 666 entries
- texture descriptor array: `0x0205F5A4`, 666 × 12 bytes
- logical usage array: `0x020614DC`, 1,302 × 8 bytes

Metal Masters contains 670 physical model NARCs on disk, but four are not registered in the ARM9 model pointer array:

- `/bey/03_047.narc`
- `/bey/03_048.narc`
- `/bey/03_154.narc`
- `/bey/03_155.narc`

These are **confirmed unregistered resources**, not yet confirmed unused gameplay content. A different subsystem could still address them by path or file ID.

## Five primary customizable part groups

Embedded Nitro model names provide direct structural evidence for the five primary groups:

| Group | Embedded examples | Interpretation | Confidence |
|---:|---|---|---|
| 0 | `ps_f`, `leo_f`, `can_f` | Face / Face Bolt model family | strongly supported |
| 1 | `ps_cw1`, `leo_cw1` | Clear Wheel / Energy Ring family | strongly supported |
| 2 | `storm_mw1`, `rock_mw1` | Metal Wheel / Fusion Wheel family | strongly supported |
| 3 | `t_145a`, `t_125a` | Track family | strongly supported |
| 4 | `b_fa`, `b_sa` | Bottom / Performance Tip family | strongly supported |

This is additionally tied to executable behavior. `bbCustomBeyTsrKeySet` switches across exactly five category values and selects a category-specific logical-usage table base.

Fusion function start: `0x02026008`

Fusion category bases, in switch order 0–4:

- `0x020DB8C0`
- `0x020DC928`
- `0x020DC3A8`
- `0x020DBBA8`
- `0x020DBFA8`

Masters homologous function start: `0x0201F4F8`

Masters category bases, in switch order 0–4:

- `0x0206288C`
- `0x020630AC`
- `0x020614DC`
- `0x020621DC`
- `0x02061B2C`

The two functions therefore provide a strong cross-game executable anchor for translating custom-part resource IDs.

Fusion also has groups 5–7 with embedded names such as `ps_fs`, `ps_cw1s`, and `storm_mw1s`. They are currently classified only as **candidate alternate/presentation variants** of the Face, Clear Wheel, and Metal Wheel families. Their exact use must be resolved from callers or runtime tracing.

## Additional executable anchors

The following embedded identifiers now have direct code-reference regions and are useful starting points for the next function-map pass:

### Fusion

- `bbCustomBeyTsrKeySet`: `0x02026008`
- `bbFileEntryMapLoad` literal user: `0x02027400`
- `EnemyEquipSet` reference cluster: approximately `0x02023EFC–0x020240F8`
- `BeyBladeLOC` consumers: around `0x02009E0C` and `0x0200A210`

The `BeyBladeLOC` path includes code using a 40-byte fixed stride. This is a **candidate record-table lead**, not yet a confirmed gameplay Beyblade master table.

### Metal Masters

- `bbCustomBeyTsrKeySet`: `0x0201F4F8`
- `bbFileEntryMapLoad` literal user: `0x02020AE0`
- `EnemyEquipSet` reference cluster: approximately `0x0201D4F8–0x0201D5E8`

These homologous names and structures provide high-value anchors for function matching between the games.

## Why the 8-byte usage table matters

The usage record is structurally confirmed as two pointers:

```text
+0x00 -> one entry inside the physical model-path pointer array
+0x04 -> one 12-byte texture descriptor
```

This is a logical-to-physical presentation mapping. It is **not yet the statistics, ownership, unlock, or complete-Bey gameplay master record**.

That distinction is important: the RE has now separated a rendering-resource ID layer from the gameplay tables we still need to locate.

## Reproduction

Run tests:

```bash
python3 -m unittest tests/test_content_map.py
```

Map a decompressed ARM9 image:

```bash
python3 tools/nds/content_map.py \
  analysis/generated/fusion-arm9.dec.bin \
  --compact \
  --output analysis/generated/fusion-bey-resource-map.json
```

Generate the ROM/NitroFS/overlay structure map:

```bash
python3 tools/nds/scan_rom.py \
  --compact \
  --output analysis/generated/rom-scan.json \
  roms/*.nds
```

Full generated records, decompressed executables, and extracted model/texture payloads remain ignored.

## Next checkpoint

The next RE milestone should use these resource IDs and function anchors to locate the actual gameplay records:

1. finish ARM9 and overlay function matching around `EnemyEquipSet`, `bbFileEntryMapLoad`, and `BeyBladeLOC`
2. reconstruct the 40-byte `BeyBladeLOC` candidate and reject or confirm it as a gameplay table
3. trace logical part ID → resource usage ID → runtime model loading
4. locate stats/type/weight/track/bottom property records independently of rendering data
5. locate complete-Bey preset records and opponent loadouts
6. map save/inventory ownership IDs and unlock tables
7. dynamically verify at least one custom-part change through the supplied DeSmuME GDB server

The key result of this checkpoint is that the physical model pipeline, the logical presentation mapping, and the five customizable part groups are no longer speculative. The remaining work can now target gameplay data without confusing it with resource lookup tables.
