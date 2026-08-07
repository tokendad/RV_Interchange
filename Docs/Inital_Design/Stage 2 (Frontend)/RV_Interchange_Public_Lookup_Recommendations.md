# RV Interchange Public Lookup Page Recommendations

**Repository:** `tokendad/RV_Interchange`  
**Scope:** Frontend redesign recommendations for the public parts lookup experience  
**Current frontend:** Lightweight HTML, CSS, and JavaScript

---

## 1. Recommended Direction

The current search-first page should evolve into a more complete **public lookup experience** while preserving the existing lightweight frontend architecture.

The recommended design has three primary states:

1. Welcome and search
2. Search results
3. Part and replacement details

This approach keeps the lookup fast and simple while making RV Interchange feel like a public-facing product rather than an API test page.

The existing frontend is already a useful foundation. It currently supports:

- Free-text part and model searches
- Alternate identifier display
- Replacement lookup
- Exact Match results
- Direct Fit results
- Fits With Modification results
- Supersession results

A framework migration is not necessary for the first redesign. The current plain HTML, CSS, and JavaScript stack should be sufficient.

---

## 2. Suggested Page Layout

```text
┌──────────────────────────────────────────────────────────────┐
│ RV Interchange       Parts Lookup   Coverage   About         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│       Find the right replacement for your RV part            │
│                                                              │
│       Search by part number, model number, or SKU             │
│                                                              │
│       [ Try SW6DE, 7330G335, or 630762... ] [ Search ]       │
│                                                              │
│       Examples: SW6DEL · 7330G335 · AP7862 · 2608A           │
│                                                              │
│       Evidence-backed compatibility information              │
│       Suburban · Coleman-Mach · Atwood · Norcold               │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ Search results, recently viewed parts, or help content        │
└──────────────────────────────────────────────────────────────┘
```

The search should remain the primary action, but the page should also explain:

- What can be searched
- Which manufacturers are currently covered
- What the compatibility classifications mean
- How the data is researched
- What users can do when no match is found

---

## 3. Header and Navigation

Keep the header simple and focused.

Recommended navigation:

- **RV Interchange** logo or wordmark
- Parts Lookup
- Data Coverage
- How It Works
- Contribute or GitHub

The admin interface should not be presented as a primary public navigation item. It can remain available through a direct URL or future authenticated route.

### Suggested Header Structure

```text
RV Interchange | Parts Lookup | Data Coverage | How It Works | Contribute
```

On smaller screens, the secondary links can collapse into a menu while the wordmark and search remain visible.

---

## 4. Search Hero

The search area should be visually dominant and immediately explain the site's purpose.

### Suggested Heading

> Find the right replacement for your RV part

### Suggested Supporting Text

> Search by manufacturer part number, model number, SKU, or known alternate number.

### Suggested Placeholder

```text
Try SW6DE, 7330G335, AP7862, or 2608A
```

### Search Examples

Place clickable examples directly beneath the field:

- `SW6DE`
- `SW6DEL`
- `7330G335`
- `AP7862`
- `2608A`

Clicking an example should populate and submit the search automatically.

### Supported Manufacturer Summary

Display the current data coverage directly below the search area:

```text
Currently covering Suburban, Coleman-Mach, Atwood, and Norcold
```

This prevents users from assuming that the database covers every manufacturer.

---

## 5. Search Result Cards

The current results can be redesigned as accessible cards with stronger hierarchy.

### Example Result

```text
┌─────────────────────────────────────────────────────────┐
│ COLEMAN-MACH                                Thermostat  │
│                                                         │
│ 7330G335                                             →  │
│                                                         │
│ Also known as: AP7862 · 7330G3351                       │
│ View compatible replacements                            │
└─────────────────────────────────────────────────────────┘
```

### Recommended Result Fields

Each card should display:

- Manufacturer
- Matched part or model number
- Part type, when available
- Alternate identifiers
- A visible action such as **View replacements**
- A directional arrow or chevron

### Interaction Improvements

- Make each result an actual link or button.
- Support keyboard focus.
- Support Enter and Space activation.
- Add a visible focus state.
- Highlight the portion of the identifier that matched the query.
- Preserve the search query in the URL.

Example:

```text
/?q=7330G335
```

This allows users to:

- Bookmark searches
- Share lookup results
- Use browser Back and Forward buttons
- Reload the page without losing the search

### Namespace Formatting

Internal namespace values should be converted to public-friendly names.

Examples:

| Internal Value | Display Value |
|---|---|
| `coleman_mach` | Coleman-Mach |
| `suburban` | Suburban |
| `atwood` | Atwood |
| `norcold` | Norcold |

---

## 6. Part Detail View

Selecting a search result should open a deliberate detail view rather than simply appending a plain list beneath the search results.

### Suggested Detail Layout

```text
Back to results

Coleman-Mach 7330G335
Wall Thermostat

Alternate numbers
AP7862    7330G3351

COMPATIBLE REPLACEMENTS

✓ Exact Match
  9420-351
  Same functionality and connection requirements

↔ Direct Fit
  Part number...
  Installs without modification

⚠ Fits With Modification
  Part number...
  Requires wiring or installation changes

SUPERSESSION HISTORY
7330G335 → 9420-351

[Copy link]  [Report incorrect information]
```

### Recommended Detail Sections

- Manufacturer and part number
- Part type
- Alternate numbers
- Exact replacements
- Direct-fit replacements
- Replacements requiring modification
- Supersession history
- Compatibility notes
- Required additional parts
- Source or evidence summary
- Copy/share link
- Report incorrect information

---

## 7. Compatibility Classifications

Compatibility classifications are one of the most important parts of the interface.

Each classification should have:

- A label
- An icon
- A brief explanation
- A distinct visual treatment

### Exact Match

Suggested icon:

```text
✓
```

Suggested explanation:

> Matches the original part's fit and intended function.

### Direct Fit

Suggested icon:

```text
↔
```

Suggested explanation:

> Installs without physical modification, but specifications should still be reviewed.

### Fits With Modification

Suggested icon:

```text
⚠
```

Suggested explanation:

> May require wiring, adapters, installation changes, or additional parts.

The **Fits With Modification** tier should be especially prominent. Users should not mistake it for a drop-in replacement.

Do not rely on color alone. The label and icon must remain visible for accessibility.

---

## 8. Supersession History

Supersessions should be displayed separately from compatibility replacements.

A supersession identifies a later manufacturer part number. It is not always the same thing as a general interchangeable replacement.

### Suggested Timeline

```text
7330G335
    ↓ superseded by
9420-351
```

For longer chains:

```text
Original Part
    ↓
First Replacement
    ↓
Current Replacement
```

This presentation helps distinguish:

- Alternate identifiers
- Manufacturer supersessions
- Compatible substitutions
- Parts that fit only with modification

---

## 9. Public Information Cards

Below the main search area, include three compact cards explaining how the service works.

### Search Any Known Number

> Use an OEM number, model number, SKU, retailer number, or known alternate identifier.

### Understand the Fit

> Results distinguish exact replacements, direct-fit replacements, and parts that require modification.

### Evidence-Backed Data

> Compatibility information is built from manufacturer literature, source documents, and captured research evidence.

These cards help communicate that RV Interchange is more than a simple parts catalog.

---

## 10. Empty Search State

Before a search is submitted, the lower part of the page can display:

- Example searches
- Current manufacturer coverage
- A short explanation of compatibility tiers
- Recently added manufacturers or parts
- A link to report a missing part

Avoid displaying an empty result container or an unfinished-looking blank page.

---

## 11. No-Result State

The current no-match message should be expanded into something helpful.

### Suggested Message

> **We couldn't find that number yet.**  
> Check the spelling, remove spaces or dashes, or try another number printed on the part.

### Suggested Follow-Up Actions

- Try the number without spaces.
- Try the number without hyphens.
- Search another identifier printed on the label.
- Review supported manufacturers.
- Report a missing part.
- Open a GitHub issue or submission form.

### Example

```text
No match found for "630-762"

Try:
• 630762
• Another model or SKU printed on the label
• The appliance model number

[Report a missing part]
```

---

## 12. Error and Loading States

### Loading

Replace plain text such as `Searching...` with a visible progress state.

Example:

```text
Searching RV Interchange...
```

The search button should be temporarily disabled while a request is active.

### Public Error Message

Avoid exposing raw technical responses such as:

```text
HTTP 500
```

Use a friendlier message:

> **The lookup service is temporarily unavailable.**  
> Please try the search again.

Technical details can optionally be placed inside a collapsible troubleshooting section.

---

## 13. Visual Style

The design should feel like a dependable technical catalog or knowledgeable RV parts counter rather than an online marketplace.

### Recommended Visual Direction

- Dark navy header
- White or light-gray page background
- Slate or charcoal body text
- Amber accent inspired by equipment and warning labels
- Green reserved for confirmed exact matches
- Blue for direct-fit replacements
- Amber for modification warnings
- Moderate border radius
- Clear card borders
- Strong mobile readability

### Suggested Page Width

Increase the current narrow layout to approximately:

```css
max-width: 72rem;
```

or:

```css
max-width: 80rem;
```

The search content can remain narrower while results and detail views use the wider page.

### Typography

Continue using a system font stack to avoid adding dependencies.

Example:

```css
font-family:
  Inter,
  ui-sans-serif,
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  sans-serif;
```

---

## 14. Mobile Design

Many users may perform a lookup while standing near an RV or holding a removed part.

Mobile usability should be treated as a primary requirement.

Recommended mobile behavior:

- Full-width search field
- Search button beneath or attached to the field
- Large touch targets
- Single-column result cards
- Sticky search header after scrolling
- Easily readable part numbers
- Copy buttons for identifiers
- Minimal horizontal scrolling
- Compatibility warnings visible without expanding a section

---

## 15. Accessibility Improvements

Recommended accessibility changes:

- Use semantic `<main>`, `<header>`, `<nav>`, and `<section>` elements.
- Give the search input an explicit `<label>`.
- Use buttons or links for clickable results.
- Add visible keyboard focus styles.
- Use `aria-live` for search status messages.
- Do not communicate compatibility through color alone.
- Maintain sufficient color contrast.
- Give icons accessible text.
- Ensure touch targets are at least approximately 44 pixels tall.
- Move focus appropriately when results or details load.

---

## 16. Search URL and Browser History

The search interface should synchronize its state with the browser URL.

### Search URL

```text
/?q=SW6DE
```

### Optional Detail URL

```text
/part/suburban/SW6DE
```

or:

```text
/?q=SW6DE&part=SW6DE
```

A dedicated part route is preferable long-term because it provides:

- Cleaner sharing
- Better bookmarking
- Search-engine indexing
- Easier QR-code use
- Better browser navigation

---

## 17. Suggested Footer

The footer can remain compact.

Recommended items:

- RV Interchange
- Current manufacturer coverage
- Data methodology
- GitHub repository
- Report missing or incorrect data
- Disclaimer

### Suggested Disclaimer

> Compatibility information is provided as a research aid. Verify dimensions, connections, electrical requirements, fuel type, and installation instructions before purchasing or installing a replacement part.

---

## 18. Recommended Implementation Phases

**Priority update (2026-08-06):** No Marketplace is needed yet — the near-term goal is a public-facing site to start collecting public feedback. Phase 2 (richer Public API fields) is promoted alongside Phase 1 rather than deferred; the Dealer API in the companion architecture doc remains future scope, not active work.

## Phase 1: Frontend-Only Redesign

This phase can use the existing public API.

Recommended work:

- Add a public header and navigation.
- Create the search hero.
- Add clickable example searches.
- Add manufacturer coverage information.
- Redesign search result cards.
- Improve loading, error, and no-result states.
- Store the search query in the URL.
- Add browser Back and Forward support.
- Add copy/share links.
- Improve compatibility tier presentation.
- Add a supersession timeline.
- Add public explanation cards.
- Improve mobile and keyboard accessibility.
- Add a public footer and disclaimer.

No frontend framework is required for this phase.

## Phase 2: Small Public API Enhancements

The existing search response is intentionally limited. A richer public interface would benefit from additional fields.

Potential additions:

- Manufacturer display name
- Part type
- Component description
- Important component attributes
- Compatibility caveats
- Required additional parts
- Evidence summary
- Public source references
- Search result count
- Search filters
- Current manufacturer coverage endpoint

These additions should preserve the project's existing rule that internal interchange identifiers, review internals, and unpublished candidate data remain hidden from public users.

## Phase 3: Expanded Public Features

Possible later features:

- Browse by manufacturer
- Browse by appliance category
- Recently added parts
- Popular searches
- Missing-part submissions
- Incorrect-data reports
- Printable replacement summary
- QR-friendly part links
- Saved or recently viewed lookups
- Dealer or salvage-yard account view
- Optional advanced filters

---

## 19. Recommended First Release Scope

The strongest first release would include:

1. Public header and branding
2. Large search hero
3. Example searches
4. Manufacturer coverage statement
5. Shareable search URLs
6. Redesigned search result cards
7. Dedicated part detail layout
8. Clear compatibility tiers
9. Supersession timeline
10. Helpful no-result state
11. Mobile-responsive design
12. Accessibility improvements
13. Public disclaimer
14. Missing or incorrect part reporting link

This would provide a substantial public-facing improvement without requiring a major backend rewrite.

---

## 20. Final Recommendation

Begin with a **frontend-only redesign using the existing vanilla JavaScript implementation**.

The current application architecture is adequate for the next version. The highest-value improvements are:

- Clearer public-facing language
- Better result hierarchy
- Shareable search and part URLs
- Strong compatibility warnings
- A polished part detail view
- Helpful no-result guidance
- Mobile-friendly interactions
- Clear manufacturer coverage
- Better explanation of the evidence-backed data model

A React, Vue, or other framework migration can be reconsidered later if the public site grows into account management, advanced browsing, saved parts, or dealer features. It is not necessary for the immediate Public Lookup page redesign.
