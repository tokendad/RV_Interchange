# Coleman thermostat evidence correction

**Status:** approved for implementation
**Date:** 2026-08-01

## Goal

Replace assumed suffixed thermostat identifiers in the ground-truth fixture with the
exact identifiers photographed on the installed unit, capture the teardown and service
manual as append-only observations, and record the complete terminal-to-function map
without overstating unproven identifier equivalence.

## Evidence and authority

The four in-hand photographs are authoritative for the physical unit's identifiers,
terminal order, installed wire colors, and board markings. They show:

- ICM part number `AP7862`
- RVP/Coleman number `7330G335`
- date code `1203`
- board markings `PCB1060` and `SPCB-2`
- board terminal order `R, Y, W, GL, GH, B`
- installed wire colors `red, yellow, white, gray, green, blue`

The RV Products/Airxcel service manual, document number `1976-376 (4-02)`, is
authoritative for electrical function. It maps the terminals as follows:

| Terminal | Function |
|---|---|
| `R` | +12 VDC supply |
| `Y` | compressor control |
| `W` | furnace/heat control |
| `GL` | low-fan control |
| `GH` | high-fan control |
| `B` | 12 VDC negative/ground |

The manual also states that the commonly found mechanical, electronic, and electronic
digital Coleman/RV Products wall thermostats shown there are interchangeable. That is
family-level compatibility evidence, not proof that every nearby part number is an alias.

## Data changes

1. Add one append-only in-hand teardown observation referencing all four photographs.
2. Add one append-only manufacturer-PDF observation for the service manual URL and its
   terminal/function and compatibility claims.
3. Extend the canonical observation vocabulary only for the newly required structured
   fields: physical identifiers, date code, terminal order, wire colors, terminal-function
   mapping, and the manual's compatibility statement.
4. Correct the thermostat fixture identifiers from `AP7862-3` to `AP7862` and from
   `PCB1060-4A` to `PCB1060`.
5. Preserve `SPCB-2` and `7330G335`, now with direct in-hand provenance.
6. Keep `AP7862-3` and `PCB1060-4A` out of the confirmed component identifier set. If they
   remain useful from earlier research, document them as unconfirmed candidates rather
   than aliases.
7. Record both the physical board order and the semantic terminal-function map. Installed
   wire color is supporting evidence, not the interchange key, because the service manual
   warns that installer-provided wire colors may differ.
8. Refresh project documentation that has fallen behind the implemented state:
   - update `README.md` so it no longer describes the repository as pre-implementation or
     directs work toward already-completed observation/schema prerequisites;
   - update `ARCHITECTURE-Interchange_Core.md` so its status distinguishes the implemented
     Stage 1 core from still-open design areas;
   - update `PLAN-Staged_Build.md` with the Coleman teardown/manual evidence and the revised
     next action;
   - update `Docs/Tools/TOOLS.md` so observation #3 is not described as the current register
     measurement state after observations #36/#39 completed and corrected it.

## Confidence boundaries

- The photos prove `AP7862`, `7330G335`, `PCB1060`, and `SPCB-2` coexist on this unit.
- They do not prove `AR7815`, `AR7816`, `AP7862-3`, or `PCB1060-4A` are aliases.
- The existing retailer claim connecting `AR7815` to `7330F3858` remains candidate evidence
  and must not be merged into this component solely from these photos.
- The manual's interchangeability statement supports a compatibility relationship among
  the thermostat generations it depicts; it does not establish identifier equivalence.

## Validation

- Add a resolver self-test first and verify it fails because the new evidence keys are
  unclassified.
- Add the minimal vocabulary mappings and verify the test passes.
- Run `resolver.py --validate` against the updated observations database and require zero
  unmapped keys.
- Run all existing inline self-tests, vendor-discovery unit tests, and the canonical edge
  fixture check.
- Review the final fixture diff to ensure no candidate identifier was silently promoted to
  a confirmed alias.
- Review the refreshed README, architecture, staged plan, and tools guide against the actual
  repository and observation database so they do not claim work is complete unless it is
  directly evidenced.
