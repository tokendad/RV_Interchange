Research by Chat GPT

# Suburban SW12DEL SKU Research: 5148A, 5148F, and 5248A

**Research date:** July 30, 2026  
**Manufacturer:** Suburban, an Airxcel brand  
**Product family:** Suburban Advantage porcelain-lined steel tank water heater  
**Canonical model:** `SW12DEL`

## Executive conclusion

The available evidence indicates that **5148A, 5148F, and 5248A all refer to the Suburban SW12DEL 12-gallon RV water-heater model family**.

The most likely interpretation is:

| Number | Classification | Packaging | Status |
|---|---|---|---|
| `5148A` | Manufacturer SKU | Single-pack | Legacy/superseded catalog number |
| `5148F` | Manufacturer SKU | Bulk package of six | Legacy OEM/bulk catalog number |
| `5248A` | Manufacturer SKU | Single-pack | Current catalog number |
| `SW12DEL` | Manufacturer model designation | Not packaging-specific | Stable canonical model |

This appears to be a **catalog-number migration**, not evidence that Suburban reused the SW12DEL model name for an unrelated appliance.

## Official Suburban evidence

### 1. Suburban 2021 specification sheet

Suburban's 2021 porcelain-steel tank water-heater specification sheet lists:

- `SW12D (5146A/F)`
- `SW12DE (5147A/F)`
- `SW12DEL (5148A/F)`
- `SW12DEC (5229A/F)`
- `SW12DELC (5231A/F)`

The same document identifies the packaging suffixes for 12-gallon models as:

- `A` — single-pack
- `F` — bulk, six per package

This establishes that `5148A/F` is shorthand for two orderable packaging SKUs:

- `5148A`
- `5148F`

It is not a single SKU literally ending in `A/F`.

**Source:** [Suburban Porcelain Steel Tank Water Heater Specifications, October 2021](https://suburbanrv.com/files/product_documents/Water%20Heater%20Controls/Tank%20Water%20Heater%20101121.pdf)

### 2. Suburban 2023 product overview

Suburban's March 2023 product overview again lists:

- `SW12DEL (5148A/F)`

It defines the DEL configuration as:

> Direct Spark Ignition with 1440 Watt Electric Element and 12VDC Relay

For the 12-gallon family, it also specifies:

| Specification | Value |
|---|---:|
| Capacity | 12 gallons |
| Gas input | 12,000 BTU/h |
| Gas and electric recovery | 16.2 gallons/hour |
| Gas-only recovery | 10.1 gallons/hour |
| Electric-only recovery | 6.1 gallons/hour |
| Unit dimensions | 16.22 × 16.22 × 22.25 in. |
| Cutout dimensions | 16.38 × 16.38 × 22.25 in. |
| Door type | Flush |
| Packaging | Single-pack `A`; bulk six-per-package `F` |

**Source:** [Suburban Porcelain Lined, Steel Tank Water Heater Product Overview, March 2023](https://suburbanrv.com/files/product_documents/Water%20Heater%20Controls/AXL-SUB_Tank%20WH%20SS%2C%20kw03012023.pdf)

### 3. Suburban 2025 catalog

Suburban's official 2025 aftermarket catalog lists:

- `5248A — SW12DEL — 12 gallon; 12,000 BTU/h`

The catalog places it under:

> Direct Spark Ignition, Electric Element and 12V Relay (DEL Model)

The same section specifies a 1,440-watt electric element and combined electric-plus-LP recovery of 16.2 gallons per hour.

**Source:** [Suburban 2025 Aftermarket Catalog](https://suburbanrv.com/files/catalog/SUB-401.02_2025%20AMCAT.pdf)

## Evidence of a systematic SKU renumbering

The change from `5148A` to `5248A` was not isolated. Comparing Suburban's 2023 literature with its 2025 catalog shows a consistent change across the D, DE, and DEL water-heater series:

| Model | 2023 SKU | 2025 SKU |
|---|---:|---:|
| SW6D | 5138A | 5238A |
| SW6DE | 5139A | 5239A |
| SW6DEL | 5140A | 5240A |
| SW10D | 5142A | 5242A |
| SW10DE | 5143A | 5243A |
| SW10DEL | 5144A | 5244A |
| SW12D | 5146A | 5246A |
| SW12DE | 5147A | 5247A |
| **SW12DEL** | **5148A** | **5248A** |

This pattern strongly supports treating `5248A` as the newer catalog number for the same SW12DEL configuration formerly sold as `5148A`.

## Independent distributor cross-references

Several RV-parts sellers independently associate the numbers with the same model.

### United RV Parts

The listing title and product description associate `SW12DEL` with `5248A`, `5148A`, and `5148F`, stating that the numbers correspond to the same water-heater model.

**Source:** [United RV Parts — SW12DEL 12-Gallon Water Heater](https://unitedrvparts.com/products/suburban-direct-spark-ignition-gas-electric-water-heater-sw12del-12-gallon-5248a-5148a-5148f)

### RV Parts Online Canada

This listing identifies the product as:

- `Suburban SW12DEL #5248A`
- `Old# 5148A`

**Source:** [RV Parts Online Canada — Suburban SW12DEL #5248A](https://www.rvpartsonlinecanada.com/products/suburban-sw12del-5148a)

### Rex and Sons RVs

The parts catalog contains entries associating both `5148A` and `5248A` with the gas/electric `SW12DEL` 12-gallon water heater.

**Source:** [Rex and Sons RVs — Suburban 5248A](https://www.rexandsonsrvs.com/parts-catalog/suburban-mfg-water-heater-5248a)

## Why conflicting listings appear

Conflicting online records are likely caused by one or more of these issues:

1. **Legacy inventory records**  
   A distributor may still use `5148A` because its inventory system was created before Suburban changed the catalog number.

2. **Current manufacturer number with an old URL or database field**  
   Some stores display `5248A` in the title but retain `5148A` in the URL, manufacturer-number field, or internal catalog data.

3. **Packaging suffixes being collapsed**  
   Sellers may treat `5148A`, `5148F`, and `5148` as equivalent search aliases even though `A` and `F` originally represented different packaging quantities.

4. **Model transcription errors**  
   Some listings omit the final `L` and incorrectly describe `5148A` as `SW12DE`. Official Suburban literature assigns:

   - `SW12DE` to `5147A/F`
   - `SW12DEL` to `5148A/F`

5. **Supersession without a publicly indexed bulletin**  
   Suburban's public literature demonstrates the before-and-after catalog numbers, but an explicit public bulletin stating “5248A supersedes 5148A” was not located during this research.

## Recommended catalog treatment

For an RV-parts interchange or normalized catalog, the model should be represented as one canonical product entity with multiple manufacturer-number records.

```yaml
product:
  manufacturer: Suburban
  canonical_model: SW12DEL
  description: >
    12-gallon direct-spark-ignition LP gas and 120VAC electric
    water heater with interior electric-element control through
    a 12VDC relay.

manufacturer_numbers:
  - number: 5148A
    type: legacy_manufacturer_sku
    packaging: single
    status: superseded

  - number: 5148F
    type: legacy_manufacturer_sku
    packaging: bulk_6
    status: superseded

  - number: 5248A
    type: current_manufacturer_sku
    packaging: single
    status: active

relationships:
  - from: 5148A
    to: 5248A
    relation: superseded_by
    confidence: high
    basis:
      - official_catalog_sequence
      - unchanged_canonical_model
      - matching_core_specifications
      - distributor_cross_references

  - from: 5148F
    to: 5248A
    relation: same_model_different_packaging_or_successor
    confidence: medium_high
```

## Cataloging cautions

- Do not merge `SW12DE` and `SW12DEL`; the final `L` identifies the relay-equipped configuration.
- Preserve `5148F` separately from `5148A` because the suffix records a real packaging distinction.
- Treat `SW12DEL` as the canonical model identity and the four-digit-plus-letter values as orderable manufacturer SKUs.
- Record `5148A` as searchable legacy data even when `5248A` is the preferred current number.
- Before representing the relationship as a legally definitive manufacturer supersession, obtain a Suburban supersession notice or written confirmation.

## Confidence assessment

| Finding | Confidence |
|---|---|
| 5148A identifies an SW12DEL | Very high |
| 5148F identifies a bulk-packed SW12DEL | Very high |
| 5248A identifies the current SW12DEL | Very high |
| 5248A replaced 5148A in Suburban's catalog sequence | High |
| The appliances are functionally the same core model | High |
| Exact effective date of the SKU change | Unknown |
| Publicly documented formal supersession bulletin | Not located |

## Final determination

For catalog and interchange purposes:

```text
SW12DEL
├── 5148A — legacy single-pack SKU
├── 5148F — legacy bulk six-pack SKU
└── 5248A — current single-pack SKU
```

The numbers should be connected to the same canonical SW12DEL product record while retaining their status, date range, and packaging differences.



Additional research provided by Google Gemini:

While I cannot generate a downloadable file or save documents directly to your local hard drive, you can easily copy and paste the formatted text below into Notepad, Word, or Google Docs to save it. [1] 

Suburban RV Water Heater SKU Transition Research
Overview
Suburban (an Airxcel brand) updated its RV water heater part numbers from the 51xx series to the 52xx series. This change reflects the rollout of their updated "Advantage" and "Direct Fit" line of replacement water heaters.
Key Details of the Change
    • Direct Supersessions: The newer 52xx part numbers directly replace (supersede) the older 51xx configurations.
    • Identical Footprints: The 52xx units serve as "Direct Fit" upgrades. They maintain the exact same dimensions and drop into the existing 4, 6, 10, 12, or 16-gallon cutouts of older models.
    • Feature Enhancements: While physical dimensions match, the 52xx series introduces minor internal updates, such as a repositionable module board for easier installation flexibility.
    • 
Common SKU Transitions
    • 6-Gallon DSI Gas (SW6D): Transitioned from 5138A to 5238A.
    • 6-Gallon Gas/Electric (SW6DELC): Transitioned from 5124A to 5224A.
    • 10-Gallon DSI Gas (SW10D): Transitioned from 5142A to 5242A.
    • 10-Gallon Gas/Electric (SW10DEL): Transitioned from 5130A to 5230A.
    • 
Sourced Reference URLs
- United RV Parts: https://unitedrvparts.com/products/suburban-direct-spark-ignition-gas-water-heater-sw6d-6-gallon-5238a-5138a-5138e
- Suburban RV Parts: https://suburbanrvparts.com/suburban-water-heaters/
"""



