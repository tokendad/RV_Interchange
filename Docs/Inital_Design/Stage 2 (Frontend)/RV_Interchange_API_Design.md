# RV Interchange Platform

# API Architecture Design

## Public API & Dealer API

**Document Status:** Draft for Architecture Review

**Version:** 2.0

---

# 1. Executive Summary

The RV Interchange platform will expose **two distinct APIs** built on top of a shared interchange engine.

Although both APIs access the same underlying knowledge base, they are designed for different audiences and different objectives.

The APIs are **not simply different permission levels** of the same interface.

Instead, they represent two separate products:

* **Public API** — answers compatibility questions.
* **Dealer API** — builds and manages compatibility knowledge.

This separation allows the Marketplace and public applications to remain fast, simple, and stable while giving trusted partners access to the complete research and evidence ecosystem.

---

# 2. Design Philosophy

The central value of RV Interchange is **not the database itself**.

The value is the ability to answer questions such as:

* What replaces this part?
* Will this fit?
* What modifications are required?
* Which replacement is recommended?

The platform should expose **answers**, not database tables.

Likewise, trusted contributors should be able to submit observations and evidence without exposing that complexity to public users.

---

# 3. High-Level Architecture

```text
                        Public Website
                        Marketplace
                        Mobile Apps
                        Third-Party Apps
                               │
                               ▼
                        PUBLIC API
                     (Query-Oriented)
                               │
         ───────────────────────────────────────────
                               │
                     Interchange Service Layer
                               │
         ───────────────────────────────────────────
                               │
                        DEALER API
             (Resource & Command Oriented)
                               │
         ───────────────────────────────────────────
                               │
                Components / Relationships
                               │
                      Evidence & Resolver
                               │
                     Observations Database
```

The Interchange Service Layer contains all business logic.

Neither API communicates directly with database tables.

---

# 4. Public API

## Purpose

The Public API exists to answer compatibility questions.

Its users are not researchers.

They simply want to know:

> "What fits?"

Typical users include:

* RV owners
* Marketplace buyers
* Repair shops
* Mobile applications
* Public websites
* Third-party integrations

---

## Characteristics

* Query-oriented
* Read-only
* Anonymous access
* Optimized for speed
* Published information only
* Simple response objects

---

## Typical Questions

"I have part ABC."

"What replaces it?"

"Will this fit?"

"What is the best replacement?"

---

## Example Endpoints

```text
GET /public/v1/search

GET /public/v1/resolve

GET /public/v1/replacements

GET /public/v1/compare

GET /public/v1/interchange/{code}

GET /public/v1/components/{id}
```

---

## Example Request

```text
GET /public/v1/replacements?identifier=SW6DEL
```

Example Response

```json
{
  "source":"SW6DEL",
  "replacements":[
    {
      "part":"SW6DEL",
      "fit":"Direct Fit",
      "rank":1
    },
    {
      "part":"SW12DEL",
      "fit":"Fits With Modification",
      "rank":2,
      "summary":"Requires switch kit"
    }
  ]
}
```

The response intentionally hides implementation details.

The consumer receives recommendations rather than graph data.

---

# 5. Dealer API

## Purpose

The Dealer API exists for organizations that help **build and improve** the interchange database.

These users are contributors rather than simple consumers.

Typical users include:

* RV dealers
* Salvage yards
* Manufacturers
* Fleet maintenance organizations
* Insurance companies
* Professional repair facilities
* Research partners

---

## Characteristics

* Authenticated
* Role-based security
* Resource-oriented
* Command-oriented
* Full access to research objects
* Supports evidence submission
* Supports review workflows

---

## Example Workflows

"I found a new part."

"I installed this replacement."

"These two identifiers refer to the same component."

"I measured this opening."

"Here's the manufacturer's service manual."

---

## Example Endpoints

```text
POST /dealer/v1/observations

POST /dealer/v1/evidence

POST /dealer/v1/fitment-reports

POST /dealer/v1/new-component

POST /dealer/v1/resolver-runs

GET /dealer/v1/components/{id}

PATCH /dealer/v1/components/{id}

GET /dealer/v1/relationships/{id}

PATCH /dealer/v1/relationships/{id}

POST /dealer/v1/interchange/publish
```

---

## Example Fitment Report

```json
{
  "source":"SW6DE",
  "replacement":"SW6DEL",
  "result":"Fits With Modification",
  "required_parts":[
    "232882"
  ],
  "notes":"Installed successfully after replacing interior switch."
}
```

This information becomes evidence.

It does **not** immediately become public.

---

# 6. Publication Workflow

All new information follows the same lifecycle.

```text
Dealer Submission
        │
Observation
        │
Resolver
        │
Candidate Component
        │
Evidence Accumulation
        │
Review
        │
Publication
        │
Public API
```

Only published knowledge is returned through the Public API.

---

# 7. Service Layer

The Service Layer contains the intelligence of the system.

Examples include:

* SearchService
* CompareService
* ReplacementService
* IdentifierService
* EvidenceService
* ConfidenceService
* PublicationService

Neither API should duplicate business logic.

Every request flows through these services.

---

# 8. Repository Layer

Repositories isolate storage from application logic.

Examples:

* ComponentRepository
* IdentifierRepository
* RelationshipRepository
* EvidenceRepository
* ObservationRepository

This abstraction allows future migration from SQLite to PostgreSQL—or another storage engine—without affecting either API.

---

# 9. Security Model

## Public API

Open to everyone.

Possible future enhancements:

* Anonymous access
* API keys
* Rate limiting
* Usage quotas

Public users may only access published knowledge.

---

## Dealer API

Authentication required.

Role examples:

Contributor

Verified Dealer

Manufacturer

Reviewer

Administrator

Automation

Each role controls access to specific resources and workflows.

---

# 10. Information Exposure

## Public API

Returns only:

* Published components
* Published interchange groups
* Ranked replacement options
* Simple fitment descriptions
* High-level evidence summaries

Hidden from public users:

* Observation records
* Candidate relationships
* Reviewer notes
* Internal confidence calculations
* Resolver metadata
* Experimental data

---

## Dealer API

Returns complete research objects, including:

* Component attributes
* Relationships
* Evidence records
* Observation history
* Confidence calculations
* Candidate identifiers
* Review status
* Publication status

---

# 11. Future Subscription Model

The architecture naturally supports commercial offerings.

## Public API

Free

* Search
* Replacement lookup
* Compare
* Published compatibility information

---

## Dealer API

Subscription

Potential premium capabilities include:

* Bulk inventory matching
* Inventory synchronization
* Evidence submission
* Component creation
* Manufacturer data imports
* PDF uploads
* Image uploads
* Webhooks
* Priority API limits
* Advanced reporting
* Candidate notifications
* Fleet integration

The subscription is not simply access to more endpoints.

It is participation in the RV Interchange knowledge network.

---

# 12. Why Two APIs?

A single API would force one of two compromises:

* Public users would be exposed to unnecessary complexity.
* Professional contributors would lack the tools needed to improve the database.

Splitting the platform allows each audience to receive an interface designed specifically for its needs.

| Public API              | Dealer API                       |
| ----------------------- | -------------------------------- |
| Query-oriented          | Resource & command-oriented      |
| Read-only               | Read + Write                     |
| Anonymous               | Authenticated                    |
| Published knowledge     | Published + Candidate + Evidence |
| Fast, concise responses | Complete research objects        |
| Marketplace & consumers | Dealers & professional partners  |

---

# 13. Long-Term Vision

The RV Interchange Engine becomes the single source of truth.

Different products consume that knowledge in different ways.

```text
                  RV Interchange Engine
                           │
          ┌────────────────┴────────────────┐
          │                                 │
     Public API                        Dealer API
          │                                 │
  Marketplace                     Dealer Systems
  Mobile Apps                     Salvage Yards
  Public Search                   Manufacturers
  Consumer Websites               Research Platform
```

Both APIs rely on the same business logic, ensuring consistency while allowing each audience to interact with the platform at the appropriate level of detail.

---

# 14. Recommendation

Adopt a dual-API architecture consisting of:

* **Public API** for fast, query-oriented access to published fitment information.
* **Dealer API** for authenticated access to research, evidence, and contribution workflows.

Both APIs should share a common service layer and repository layer, ensuring a single source of truth while allowing each interface to evolve independently.

This architecture supports the long-term goals of the RV Interchange platform by enabling a scalable public marketplace, fostering a trusted contributor ecosystem, and providing a clear path toward subscription-based dealer services without exposing internal implementation details to public consumers.
