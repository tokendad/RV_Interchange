# Design Review #002
## RV Interchange Numbering System Review

**Date:** July 29, 2026
**Status:** Architectural Recommendation

## Executive Summary

The RV interchange number should function as a stable catalog reference, not as the source of compatibility truth.

Compatibility should always be derived from:
- Component identities
- Normalized attribute claims
- Directional compatibility relationships
- Supporting evidence

The interchange number is the shared language for buyers, sellers, dealers, and salvage yards.

## Recommended Identity Model

### Component ID
Example: `c_01HQ8F3K2M`

- Immutable
- Opaque
- Internal
- Never changes

### Interchange Number
Example: `412-0087`

- Stable
- Human-readable
- Used for shelves, phone calls, and inventory

### Variant
Example: `412-0087-A`

Represents meaningful installation or functional differences—not cosmetic differences.

## Proposed Format

`PPP-GGGG-V`

- PPP = Part Type
- GGGG = Interchange Group
- V = Variant

Examples:
- 412-0087-A
- 412-0087-B
- 415-0024-A
- 520-0011-C

## Numbering Principles

- Part type numbers should remain stable catalog identifiers.
- Group numbers should be sequential and contain no encoded technical meaning.
- Variant letters should represent installation-impacting differences only.
- Color, branding, packaging, and condition should never affect the interchange number.

## Stability Rules

- Never reuse retired numbers.
- Never renumber for cosmetic reasons.
- Group splits create new numbers.
- Group merges preserve redirects.
- Never recycle variant letters.

## Candidate vs Published Numbers

Internal candidate clusters may change frequently.

Public interchange numbers should only be assigned after review, ensuring long-term stability.

## Manufacturer Relationships

Manufacturer identifiers resolve first.

Example:

SW6DEL
→ Component
→ RV Interchange 412-0087-B

The interchange number supplements manufacturer identifiers rather than replacing them.

## UI Recommendation

Consumers should primarily see:

Suburban SW6DEL

RV Interchange: 412-0087-B

Dealers and salvage yards should also be able to search directly by interchange number.

## Suburban Example

Part Type:
412 = Water Heater Assembly

Interchange Family:
412-0087

Members:
- 412-0087-A = Suburban SW6DE
- 412-0087-B = Suburban SW6DEL

Compatibility:
- A → B: Drop-in upgrade
- B → A: Fits with caveat (interior electric wall switch becomes inactive)

## Final Recommendation

Use the interchange number as a stable conversation handle—not as the source of compatibility truth.

The database contains the intelligence.

The interchange number simply provides the shortest, clearest way for people to communicate about compatible RV components.
