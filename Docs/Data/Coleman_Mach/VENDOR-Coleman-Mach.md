# VENDOR — Coleman-Mach / RV Products / Airxcel

**Status:** thermostat fixture resolver complete; broader adapter research in progress
**Updated:** 2026-08-01

## 1. Why this adapter

Coleman-Mach is the second Stage 1 vendor after Suburban. The in-hand analog wall
thermostat is the first fixture case where identity crosses namespaces: its rear label
carries both an ICM part number and an RVP/Coleman number, while its circuit board carries
two additional manufacturing markings. Unlike water heaters, its compatibility key is the
electrical terminal interface rather than physical dimensions.

## 2. In-hand thermostat teardown

Observation #44 and four photographs record the exact physical unit:

| Namespace | Identifier | Location |
|---|---|---|
| ICM | `AP7862` | rear label, behind faceplate |
| Coleman/RVP | `7330G335` | rear label, behind faceplate |
| board silkscreen | `PCB1060` | reverse of circuit board |
| board silkscreen | `SPCB-2` | reverse of circuit board |

The rear label also gives date code `1203`. The photographs do **not** show the earlier
fixture variants `AP7862-3` or `PCB1060-4A`; those have therefore been removed from the
confirmed component. They may be related variants, but there is no evidence here that
allows suffixes to be discarded.

Photographs:

- `Thermostat Images/20260801_103947.jpg` — rear labels and installed harness
- `Thermostat Images/20260801_104000.jpg` — terminal labels, board positions, and colors
- `Thermostat Images/20260801_104039.jpg` — reverse-board `PCB1060` / `SPCB-2` markings
- `Thermostat Images/20260801_104050.jpg` — housing/date-wheel context

## 3. Terminal interface

The board photograph establishes the physical order, board positions, and installed wire
colors. The RV Products service manual `1976-376 (4-02)` (observation #45) establishes the
electrical function:

| Order | Terminal | Board position | Installed color | Manual function |
|---:|---|---|---|---|
| 1 | `R` | `W1` | red | +12 VDC supply |
| 2 | `Y` | `W5` | yellow | compressor control |
| 3 | `W` | `W6` | white | furnace/heat control |
| 4 | `GL` | `W3` | gray | low-fan control |
| 5 | `GH` | `W4` | green | high-fan control |
| 6 | `B` | `W2` | blue | 12 VDC negative/ground |

The installed colors agree with the manual's conventional colors, but color is supporting
evidence only. The manual explicitly warns that vehicle-manufacturer or installer wiring
may not follow those colors. Terminal label and function—not conductor color—form the
portable compatibility contract.

## 4. What the service manual proves

The manual covers 12 VDC Coleman/RV Products wall-thermostat control for rooftop systems.
It depicts mechanical/bimetal, electronic, and electronic-digital thermostats in
chronological order and says all three are completely interchangeable. It also documents
the operating connections:

- low cool connects `R` to `Y` and `GL`;
- high cool connects `R` to `Y` and `GH`;
- heat connects `R` to `W`;
- fan-only connects `R` to `GH`.

This is strong manufacturer evidence for compatibility among the depicted generations.
It is **not** proof that every catalog, builder, board, or retailer number found near those
products is a pure alias.

Local source: `Docs/Data/Coleman_Mach/Coleman-Wall-Thermostat.pdf`<br>
Mirror URL: <https://myrvworks.com/wp-content/uploads/2019/04/Coleman-Wall-Thermostat.pdf>

## 5. Identifier crosswalk boundaries

Confirmed on one physical unit:

```text
ICM AP7862 = Coleman/RVP 7330G335 = board PCB1060 / SPCB-2
```

Here `=` means the identifiers coexist on this one component, not that their namespaces
or numbering systems are generally interchangeable.

Still candidate-only:

- Observation #43: a used-parts retailer presents ICM `AR7815` and Coleman `7330F3858`
  as the same thermostat. Neither appears on the in-hand unit.
- `AR7816`, `AP7862-3`, and `PCB1060-4A` currently lack captured evidence sufficient to
  attach them to the in-hand component.
- Observation #40 lists the current manufacturer model `7330G3351`; the extra trailing
  digit must not be normalized away from the photographed legacy `7330G335` without an
  explicit cross-reference.
- Observation #41 says current `9420-351` replaces `7330G3351` and `7330F3852`. That is a
  supersession claim, not an alias claim, and still needs resolver representation.

## 6. Sources

- obs #40 — Coleman-Mach current analog thermostat product page
- obs #41 — Coleman-Mach 2025 aftermarket catalog
- obs #42 — 2013 RVP/Coleman product catalog via MyRVWorks
- obs #43 — used-parts retailer `AR7815` / `7330F3858` claim
- obs #44 — in-hand rear-label, terminal, wiring, and circuit-board photographs
- obs #45 — RV Products/Airxcel service manual `1976-376 (4-02)`
- obs #46 — structured PCB-position transcription supplement to obs #44
- obs #47 — structured voltage/stage extraction supplement to obs #45

## 7. Resolver status and next milestone

The fixture resolver now builds the thermostat component from observations #44-#47,
persists 26 qualified attributes, and stores the retailer-only `AR7815`/`7330F3858` claim
as a separate open identifier-equivalence candidate sourced to observation #43.

Next, resolve the exact endpoint components depicted or named by the manual/catalog before
persisting family compatibility or the `9420-351` supersession relationships. The resolver
must continue to keep compatibility, supersession, identity, and candidate equivalence
separate.
