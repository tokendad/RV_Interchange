# Suburban RV Water Heaters Spec Sheet

> **Dimension caveat (revised 2026-07-30):** Height/Width/Depth below are **product
> (envelope) size**, not installation-opening size — this sheet has no opening column at all
> (observation #17, `dimension_kind: PRODUCT_SIZE_NOT_CUTOUT`). **Do not use these figures as
> the interchange key.**
>
> The interchange key is the **framed opening**, and it is **two-dimensional**. Suburban's
> Master Service and Training Manual (obs #19, Figure 1) specifies:
>
> | Capacities | Opening (A × B) | Tolerance |
> | :--- | :--- | :--- |
> | 4 & 6 gal | 12 3/4" × 12 3/4" | **+1/8, −0** (may be oversize, never undersize) |
> | 10, 12 & 16 gal | 16 3/8" × 16 3/8" | ± 1/16 |
>
> **There is no opening depth.** Any source publishing a third "cutout" figure (19.19", 19.75",
> 22.25") is either repeating the unit's own depth or mislabelling a cavity-clearance number.
> Depth belongs to the unit, as `unit_depth` — a secondary constraint answering "is the cavity
> deep enough," not "does it fit the hole."
>
> Note that 10, 12 and 16 gallon **share one opening**; capacity does not imply a distinct
> opening. In `fixtures/ground-truth.yaml`, `critical_attributes` for part type 412 are
> `opening_h`, `opening_w`, `capacity_gal`, `ignition_type`. The former `cutout_d` is retired.
> See `VENDOR-Suburban.md` §6.5.

| Category | Nom. Gals. | Model Number | BTU/h Input | Height | Width | Depth *(unit)* | Shipping Weight |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard** | 3 | SW3P | 9,000 | 12 11/16" | 12 11/16" | 16 1/8" | 30 |
| **Super Performance Pilot** | 6 | SW6P | 12,000 | 12 11/16" | 12 11/16" | 19 3/16" | 37 |
| **Super Performance Pilot** | 10 | SW10P | 12,000 | 16 7/32" | 16 7/32" | 20 1/2" | 48 |
| **Super Performance Pilot with Reignitor** | 6 | SW6PR | 12,000 | 12 11/16" | 12 11/16" | 19 3/16" | 37 |
| **Super Performance Pilot with Reignitor** | 10 | SW10PR | 12,000 | 16 7/32" | 16 7/32" | 20 1/2" | 48 |
| **Super Performance Combination Electric and Pilot** | 6 | SW6PE | 12,000 | 12 11/16" | 12 11/16" | 19 3/16" | 37 |
| **Super Performance Combination Electric and Pilot** | 10 | SW10PE | 12,000 | 16 7/32" | 16 7/32" | 20 1/2" | 48 |
| **Super Performance Combination Electric and Pilot with Reignitor** | 6 | SW6PER | 12,000 | 12 11/16" | 12 11/16" | 19 3/16" | 37 |
| **Super Performance Combination Electric and Pilot with Reignitor** | 10 | SW10PER | 12,000 | 16 7/32" | 16 7/32" | 20 1/2" | 49 |
| **Direct Spark Ignition** | 6 | SW6D | 12,000 | 12 11/16" | 12 11/16" | 19 3/16" | 35 |
| **Direct Spark Ignition** | 10 | SW10D | 12,000 | 16 7/32" | 16 7/32" | 20 1/2" | 49 |
| **Electric and Direct Spark Ignition** | 6 | SW6DE | 12,000 | 12 11/16" | 12 11/16" | 19 3/16" | 37 |
| **Electric and Direct Spark Ignition** | 10 | SW10DE | 12,000 | 16 7/32" | 16 7/32" | 20 1/2" | 50 |
| **Electric and Direct Spark Ignition with Motor Aid** | 6 | SW6DEM | 12,000 | 12 11/16" | 12 11/16" | 19 3/16" | 39 |
| **Electric and Direct Spark Ignition with Motor Aid** | 10 | SW10DEM | 12,000 | 16 7/32" | 16 7/32" | 20 1/2" | 60 |

---

### Accessories

| Part Number | Description |
| :--- | :--- |
| **520821** | Reignitor Kit (Applicable only to models above. See #991801501) |
| **6261ACW** | Door, Colonial White, SW Model, Radius Corner, 3, 6 Gallon |
| **697205** | Door, Colonial White, V Model, Radius Corner, 3, 6 and 8 Gallon |
| **690578** | Door, Colonial White, V Model, Square Corner, 3, 6 and 8 Gallon |
| **520781** | Kit to adapt old style 6 Gallon Door to SW6 Water Heater |
| **6255ACW** | Door, Colonial White, SW Model, Flush Mount, 3, 6 Gallon |
| **697221** | Door, Colonial White, V Model, Flush Mount, 6 Gallon |
| **520771** | Kit to adapt old style Flush Mount Door to SW6 Water Heater |
| **6257ACW** | Door, Colonial White, V Model, Radius Corner, 10 Gallon |
| **697213** | Door, Colonial White, V Model, Square Corner, 10 Gallon |
| **6259ACW** | Door, Colonial White, SW Model, Flush Mount, 10 Gallon |
| **520787** | Door Kit (6 Gallon Aluminum Tank Replacement Kit) Colonial White |
| **520818** | Door Kit (6 Gallon Aluminum Tank Replacement Kit) Polar White |

> **Note:** Water heaters and doors are sold separately. Specifications and prices are subject to change without notice.
