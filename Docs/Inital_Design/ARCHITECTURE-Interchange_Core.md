# Interchange Core — Architecture

**Project:** RV Interchange
**Status:** design, pre-implementation
**Date:** 2026-07-29
**Scope:** the cross-brand parts-interchange database for RV components

> **Naming note:** the project was initially scoped as "rvpartsmarketplace." That name is
> retired. The database is the product; the marketplace (Stage 3/4 in
> `PLAN-Staged_Build.md`) is a separate, later application that references this database —
> not the other way around. Project name going forward: **RV Interchange**.

---

## 1. The thesis

The defensible asset is not a marketplace. It is a **fitment/interchange database**.

RVs have no equivalent to the automotive Hollander interchange number. Salvage yards,
forums, and eBay storefronts each hold fragments of the crosswalk; nothing joins them.

**Key reframe:** RV parts are not "RV parts." They are *components* — a Dometic fridge,
a Suburban water heater, a Lippert slide — dropped into a coach by an integrator.
Therefore the index must be **component-first**, not coach year/make/model. Coach YMM is a
weak predictor of contents because OEMs swap suppliers mid-year and mid-floorplan.

- Automotive goes: vehicle → interchange → part
- RV must invert: **component → interchange → fitment observations**

### 1.1 How this diverges from Hollander (deliberately)

Hollander (first manual 1934, computerized 1970s) assigns one number to each group of
confirmed-interchangeable parts, so yards can search inventory by number rather than by car.
Nested buckets: full number including trailing letter = perfect swap; partial match = notes
on required modification.

Critically, **Hollander catalogs where manufacturers reused parts** — traceable through OEM
records. It does *not* declare two independently-designed parts interchangeable. Aftermarket
brands (Dorman, APDTY) only point at buckets; they aren't members of them.

This system deliberately diverges: it **does** place independently-designed but
fitment-compatible parts in the same bucket. A new Acme heater matching the Suburban cutout
belongs in the Suburban's group.

- **Cost:** harder to populate. No published source holds the relationship. It comes only
  from measurement and field reports.
- **Benefit:** more valuable and far more defensible once built. It cannot be scraped from
  anywhere, because it does not exist anywhere.

---

## 2. Three-layer identity

Each layer changes at a different rate. Keeping them separate is the whole design.

### Layer 1 — `component_id`

```
c_01HQ8F3K2M
```

- Opaque, immutable, 1:1 with a physical design.
- **Never changes.** Not on correction, not on regrouping, not on supersession.
- Opacity is not stylistic. It is what allows groups to be re-clustered without breaking
  every reference in the system.

### Layer 2 — `attributes`

The record. Specs, dimensions, materials, electrical characteristics.

- Change only on correction.
- **Every attribute carries its own provenance.** A spec-sheet value is not the same claim
  as a tape-measured value, and neither is the same as a value pulled from image alt text.
- Attributes are **inputs to clustering**, never decoded from the code.

### Layer 3 — `interchange_code`

```
412-0087-A
 |    |   |
 |    |   +-- variant  (non-matching but still compatible)
 |    +------ group    (computed equivalence class)
 +----------- part type
```

- 1:many. A human-speakable **pointer** to an equivalence class.
- Allowed to be wrong. Allowed to be re-clustered.

#### Visibility: hidden by default, optional for dealers

**Decided 2026-07-29.** General-consumer views never show the interchange number —
only the manufacturer identifier (e.g. "Suburban SW6DEL"). Dealers and salvage yards may
opt in to a view that surfaces it as a secondary line, since it is genuinely useful as a
phone/inventory handle for that audience. This is a display-layer toggle, not a schema
difference — the same record, gated by account type.

```
Consumer view:        Suburban SW6DEL
Dealer view (opt-in):  Suburban SW6DEL
                        RV Interchange: 412-0087-B
```

#### The code contains nothing

It is a label, like a ZIP code — not a container. Flow is one-directional:

```
attributes → clustering → group → gets a number
```

Never the reverse. Do not bake specs or manufacturer into the code:

- Corrections would mutate the primary key.
- You cannot cross manufacturers if the manufacturer is in the identifier.

#### Groups split as often as they grow

A field report forks `0087` into `0087` and `0088`. Opaque `component_id`s survive that
intact. This is the entire justification for opacity — plan for it, don't treat it as failure.

A new fitting manufacturer's part gets its own `component_id`, joins the existing group,
and nothing else in the system changes.

#### Stability rules for the code itself

- **Never reuse a retired group or variant number.** A dead number stays dead.
- **Never renumber for cosmetic reasons.** Colour, packaging, and condition never touch
  the code (see `compat_mode` §5).
- **Splits create new numbers.** The forking group keeps its old number; the new cluster
  gets the next unused one.
- **Merges preserve redirects.** If two groups turn out to be the same equivalence class,
  the retired number resolves forward to the surviving one rather than going dead. Lookups
  against a merged-away number must still succeed.
- **Never recycle variant letters.** A retired `-C` stays retired within its group, even
  after a merge or split, so a stale reference (a customer's old note, a cached page) never
  silently starts meaning something else.

#### Candidate vs. published numbers

Internal clustering is expected to churn — that's the whole point of computing groups
rather than hand-assigning them. But a number that's visible to a dealer on the phone needs
to *stay put*.

So the code has two states:

- **Candidate:** an internal cluster, may still merge, split, or be corrected. Not exposed
  outside the system.
- **Published:** assigned after review, stable from that point forward under the rules
  above.

A group can sit at CANDIDATE confidence (§7) indefinitely without being published — evidence
strength and publication are related but separate decisions. Don't publish a number just
because an edge crossed a confidence threshold; publish it when the *identity of the group*
is judged stable enough to hand to a stranger on the phone.

---

## 3. Identifiers are namespaced

Not a flat alias list. Numbers come from multiple issuing authorities.

```yaml
identifiers:
  - {ns: suburban,  value: SW6DEL}
  - {ns: suburban,  value: "5240A"}
  - {ns: icm,       value: AP7862-3}
  - {ns: coleman,   value: 7330G335}
  - {ns: silkscreen, value: PCB1060-4A}
```

Required because:

- A builder's number (ICM) and a brand's number (Coleman) refer to the same object with
  different authority.
- Namespacing is what lets you distinguish **supersession** from **revision**.

### `identifier_visibility`

```
exterior_plate | behind_faceplate | hidden_mold_face | none_marked
```

This field splits **buyer evidence** from **seller evidence**. A buyer sees only the
installed exterior. A seller at teardown has the part in hand. Two different identification
problems, two different query paths.

---

## 4. Edge vocabulary

| Edge | Direction | Notes |
|---|---|---|
| `substitutes` | bidirectional *or* asymmetric | carries confidence, basis, caveats, evidence |
| `alias` | bidirectional | same object, different issuing authority |
| `supersedes` | directional | replacement chain |
| `shares_subassembly` | bidirectional | partial-parts overlap |
| `contains` | directional | assembly → component |
| `requires_system` | directional | needs matching harness/sensors |
| `controls` | directional | switch → appliance |
| `aftermarket_replaces` | directional | **lower trust weight** |

**Substitution can be asymmetric.** Model the direction explicitly. See the SW6DE/SW6DEL
case in `VENDOR-Suburban.md` — a confirmed real instance.

---

## 5. `compat_mode`

Different part types are identified by fundamentally different keys. Declare which.

| Mode | Meaning | Example |
|---|---|---|
| `standard_opening` | brand-agnostic standard hole | 14×14 roof vent — huge group |
| `proprietary_interface` | terminal/wire map is the key, not dimensions | analog thermostat — tiny group |
| `system_bound` | requires matching sensors/harness | KIB monitor panel |
| `attribute_only` | identity is pure geometry + color | unmarked round register |

### Cosmetic axes stay out of the interchange key

Colour (almond / white / tan) lives on a **display axis** only.

Confirmed in the wild: the Suburban interior switch ships as 232882 (white),
233111 (black), 232881 (cream). One component, three numbers, colour-only difference.

### Assembly level must be declared per listing

KIB sells the whole panel, the bare board (SUBPCBM21), the pump switch (SWOKLED1),
the harness (K101), and the sensors (MP5). "A KIB monitor panel" is five different
transactions. The listing must say which.

---

## 6. Part-type taxonomy

`part_type_id` uses the same opaque-key pattern one level up.

**Do not design the taxonomy in advance.** Real parts have genuinely ambiguous parents:
a water heater is plumbing *and* LP gas *and* electrical *and* appliance; a thermostat
controls the furnace *and* the A/C.

Rules:

1. `part_type_id` is **opaque**.
2. Categories are **tags** — many-to-many, never a tree path.
3. Each type carries an `attribute_schema` telling the clusterer which fields matter
   *for this type* (cutout dims for a heater; terminal map for a thermostat).
4. IDs assigned in **encounter order**, block-allocated loosely for sortability.
   **Code never branches on a range.**
5. The registry is **data, not schema**. Append as ingest encounters new things.
   Start Suburban with two rows.

### Loose blocks (sortability only — not semantics)

```
100s  exterior / structural
200s  plumbing
300s  LP gas
400s  climate
500s  electrical
600s  appliances
700s  chassis
800s  interior
900s  awnings / accessories
```

Working assignments for the five test parts:

| Type | ID | Compat mode |
|---|---|---|
| Water heater | 412 | attribute (cutout) |
| Thermostat | 415 | proprietary_interface |
| Ceiling register | 418 | attribute_only |
| Roof vent | 105 | standard_opening |
| Monitor panel | 520 | system_bound |

### `pcdb_term_id` — nullable, intentionally

The Auto Care Association's PCdb (part types) and PAdb (108k+ attributes, 12k+
terminologies) are the same shape as this — but subscription-based *and* automotive.
RV appliances are almost certainly absent.

**Decision:** do not subscribe. Leave the column nullable. It is cheap future interop with
ACES/PIES and eBay Motors instead of a rewrite.

---

## 7. Confidence scoring

**Accumulate from evidence with an attribute-derived prior. Do not compute from an
attribute formula.**

Model as Beta(α, β) pseudo-counts.

### Prior, from attribute match

| Match quality | Prior |
|---|---|
| All critical attributes exact | Beta(3, 1) |
| Within tolerance | Beta(2, 1) |
| Unknown / incomplete | Beta(1, 1) |

### Evidence

| Event | Effect |
|---|---|
| Buyer-confirmed install | α + 3 |
| Teardown co-occurrence | α + 2 |
| Manufacturer assertion | α + 2 (capped, once) |
| Retailer cross-reference | α + 1 |
| Reported fitment failure | β + 6 |
| Return / dispute | β + 8 |

```
confidence = α / (α + β)
certainty  = α + β
```

**Report both.** 0.95 from n=3 is not 0.95 from n=90.

### Why failures outweigh successes

A failure is a hard existence proof. Successes carry survivorship bias — the people for whom
it worked are exactly the people who don't write in.

Consequence: **confidence climbs slowly and falls hard.** One failure knocks a full tier.
That is correct. A wrong drop-in badge means somebody cuts into their sidewall on a Saturday.

### Handling variance

High variance → **do not average. Segment.** Find the splitter (make, model year,
floorplan) and fork the edge.

### Other rules

- **Decay** toward the prior over time — manufacturers make silent revisions.
- **Cap evidence per source and per actor.** Ten installs quoted from one forum thread is
  not ten samples.
- **Weight by incentive.** Buyer confirmation is the highest-value signal.
  Manufacturer and seller assertions are self-interested.
- **Cluster failure text** into a caveat list. The caveat list is more valuable to the user
  than the score.
- Most edges start at prior with zero field evidence. **CANDIDATE is the honest day-1 state**
  for nearly everything.

---

## 8. Tiered search

An identifier — say `SW6DEL` — resolves: identifier → component → group → members.

**Always tiered. Never flat.** Flattening is the eBay failure mode.

| Tier | Rule |
|---|---|
| **EXACT** | same `component_id` |
| **DROP-IN (verified)** | n ≥ 8 and mean > 0.90 |
| **FITS WITH ONE CHECK** | mean > 0.70, or high mean with low n |
| **PARTS FOR THIS UNIT** | `contains` edges — catches misdirected intent |

**Show why.** "Matched on 5140A." "Same cutout, BTU, ignition type."

**Blocking caveats become inputs.** Don't just warn — ask: *"Enter your cutout depth →"*

**Empty tiers are a valid answer** and a demand signal. Capture as a component-keyed "want."

---

## 9. Persistence: two tables

```
observations/            (append-only)
    source, url, fetched_at, raw_text, extracted
         |
         v
      resolve
         |
         v
components/   edges/     (derived, REBUILDABLE)
```

The grouping logic **will** change repeatedly. Resolution must be re-runnable, not a
migration each time. Nothing fetched in week one should be lost when the real schema lands.

**Build `observations` before fetching anything.** It is source-agnostic, so it can be
designed without knowing what the data looks like.

---

## 10. Teardown as the capture moment

Teardown is the highest-information moment in a part's life: hidden markings are exposed and
the part is in hand.

**Build intake as a teardown flow, not a photograph-the-shelf flow.**

- Capture molded numbers before they are lost to reinstallation.
- **Correlate hidden identifiers against externally-visible features** (garnish profile,
  hinge style, crank type) so a buyer who *cannot* see a number still gets an answer.
  This is a moat that deepens over time and cannot be scraped.
- **Classify every OCR'd string before it touches the graph:**
  `part_number | cavity_id | resin_code | date_wheel | unknown`.
  Molded plastic is full of numbers that are not part numbers.
- **Date wheels are free value:** manufacture date orders supersession chains and infers
  coach model year.

---

## 11. Open questions

- Clustering algorithm and distance function per `attribute_schema` — unspecified.
- Tolerance bands per attribute type (how close is "within tolerance" for a cutout?).
- Decay half-life for confidence.
- Whether `variant` letter should be assigned deterministically or in encounter order.
- Conflict-resolution policy when two sources disagree and both are high-trust
  (see the Suburban wattage case — currently unresolved).
