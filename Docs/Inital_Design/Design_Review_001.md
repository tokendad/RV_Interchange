RV Parts Interchange Marketplace

Design Review #001

Reviewer: ChatGPT (GPT-5.5)
Date: July 29, 2026
Status: Initial Architecture Review

---

Executive Summary

After reviewing the current design documents, I believe the project is pursuing the correct problem.

The most valuable asset is not a marketplace—it is a continuously improving interchange database capable of identifying RV components and determining verified replacement options.

The proposed development order:

1. Interchange database
2. Free identification tool
3. Marketplace
4. Dealer integrations

is strategically sound and significantly reduces the traditional two-sided marketplace problem.

Overall I would characterize the current design as:

Architecture: ★★★★★
Product Strategy: ★★★★★
Implementation Readiness: ★★★★☆

The remaining work is primarily refining the data model before implementation rather than changing the overall direction.

---

Major Strengths

1. Correct Core Thesis

The strongest decision in the design is recognizing that RVs should not be indexed like automobiles.

Instead of:

Vehicle → Part

the system correctly models:

Component → Identity → Interchange → Fitment

This reflects how RVs are actually built, where manufacturers frequently change suppliers within the same model year.

I believe this becomes the project's primary competitive advantage.

---

2. Lookup Before Marketplace

This is likely the most important business decision in the design.

The lookup tool:

- works with zero sellers
- works with zero buyers
- works with zero transactions
- creates useful data every day

Every search becomes another observation.

Every unknown identifier becomes another research target.

Every uploaded dataplate photo expands the catalog.

This allows the database to improve long before marketplace liquidity exists.

---

3. Three-Layer Identity

Separating:

• Component Identity
• Component Attributes
• Interchange Group

is excellent.

This prevents one of the classic failures of interchange databases:

confusing "today's compatibility conclusion" with permanent identity.

Groups can evolve without breaking references throughout the rest of the system.

---

4. Evidence-Based Design

The append-only observation model is exactly the right direction.

Instead of storing conclusions, the system stores observations and continually derives conclusions from them.

That makes the database reproducible and allows improvements to the clustering logic without losing history.

---

5. Real-World Validation

The Suburban research demonstrates that the architecture already solves actual problems.

Examples include:

- conflicting specifications
- incorrect retailer metadata
- asymmetric substitutions
- multiple identifier namespaces
- hidden identifiers
- cosmetic variants

Finding these issues before writing software is an excellent sign.

---

Architectural Questions

These are not criticisms.

These are the primary questions I would answer before significant implementation begins.

---

Question 1

What exactly is a Component?

The documentation currently treats Component as the central object.

However several different concepts may be hiding inside it.

For example:

Physical Design

↓

Manufacturer SKU

↓

Color Variant

↓

Inventory Item

↓

Marketplace Listing

Those are probably not the same object.

Recommendation:

Explicitly separate:

- Component
- Component Variant
- Inventory Item
- Marketplace Listing

Interchange should operate primarily at the Component level.

---

Question 2

Where should color live?

The current fixture correctly identifies color as non-interchange information.

However color is still important commercially.

Example:

White Switch

Black Switch

Cream Switch

Functionally identical.

Commercially different.

Recommendation:

Treat color as a Variant rather than as part of the core Component.

---

Question 3

Should Interchange Groups be Stored?

Currently a Component carries an Interchange Code.

I recommend making group membership derived rather than intrinsic.

Component

↓

Resolver

↓

Interchange Group

↓

Search Results

This better supports regrouping later as evidence improves.

---

Question 4

Are Aliases Identifier Relationships or Component Relationships?

The documentation currently uses "Alias" in two ways.

Sometimes:

Different identifiers referring to one component.

Other times:

Edges between components.

These should probably become separate concepts.

Identifiers should resolve Components.

Components should connect to other Components.

---

Question 5

How are Conflicting Facts Stored?

Current examples include:

1400W

1440W

Different warranty lengths

Different weights

The design already introduces provenance.

I recommend going one step further.

Store every individual claim separately.

Then derive the current "best" attribute from those claims.

That preserves complete history while allowing improvements to trust ranking.

---

Question 6

Should Confidence be Directional?

The SW6DE → SW6DEL example suggests yes.

Installing:

DE

↓

DEL

is not equivalent to:

DEL

↓

DE

Those should accumulate evidence independently.

---

Question 7

What is an Observation?

The Observation table is correctly identified as the first milestone.

Before implementation I would define exactly what every Observation contains.

Suggested fields include:

- source
- capture method
- parser version
- timestamp
- raw payload
- extracted claims
- content hash
- trust level

The Observation becomes the permanent historical record.

Everything else becomes rebuildable.

---

Question 8

Are Part Types Truly Opaque?

The documentation describes Part Types as opaque IDs while simultaneously organizing them into numeric ranges.

Either approach works.

The project simply needs to decide whether:

412

is merely a catalog number,

or

an opaque identifier.

---

Question 9

When Should Silence Become Evidence?

The design proposes treating:

"No return."

"No dispute."

"No additional searches."

as weak positive evidence.

I would delay this until marketplace transactions exist.

Prior to that, silence may simply mean the user left the site.

---

Question 10

Should Variants be Marketplace Objects?

A seller owns:

Black switch

not

Generic switch.

Marketplace listings should therefore reference the exact sellable variant while still inheriting interchange information from the parent Component.

---

Suggested Implementation Order

Phase 1

Observation Repository

Goal:

Capture information.

No clustering.

No marketplace.

Deliverable:

Permanent append-only evidence storage.

---

Phase 2

Component Catalog

Implement:

Components

Identifiers

Variants

Attributes

Claims

Normalization

Deliverable:

Every identifier resolves correctly.

---

Phase 3

Relationship Graph

Implement:

Substitutions

Supersessions

Contains

Controls

Requires System

Shared Assemblies

Deliverable:

Graph traversal produces known fixture results.

---

Phase 4

Resolver

Generate:

Exact Match

Verified Drop-in

Fits with Checks

Parts for this Unit

from graph traversal.

No hardcoded relationships.

---

Phase 5

Public Lookup Tool

Provide:

Identifier search

Dataplate recognition

Measurement assistance

Empty-result logging

Explanation of why matches were returned

No accounts required.

---

Marketplace Recommendation

I would intentionally avoid designing marketplace functionality until the lookup experience is solving real problems.

The marketplace should feel like a natural continuation of the identification engine.

Not the other way around.

---

Long-Term Opportunity

If executed successfully, this project has the potential to become the RV equivalent of the Hollander interchange system.

However, unlike Hollander, it would also incorporate:

- crowd-sourced fitment observations
- evidence-weighted compatibility
- asymmetric substitutions
- image-assisted identification
- continuously improving confidence scoring

Those capabilities would make the database increasingly difficult for competitors to reproduce over time.

That growing data advantage—not marketplace features—is the project's long-term moat.

---

Overall Recommendation

I recommend proceeding with the current architecture.

The central product strategy appears sound.

The immediate focus should remain on strengthening the underlying data model rather than building marketplace features.

The next milestone should be a fully specified Observation and Claim architecture, followed by refinement of the Ground Truth fixture until it can serve as the acceptance test for the resolver.

Once that foundation exists, the lookup tool can be built with confidence that every improvement strengthens the long-term interchange database rather than creating technical debt.