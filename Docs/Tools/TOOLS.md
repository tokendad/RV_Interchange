# observations.py

The append-only evidence layer for RV Interchange. See ARCHITECTURE-Interchange_Core.md
section 9 for why this exists as a separate table from components/edges.

## Setup

Requires Python 3 and `requests` (already installed if you can run `pip install requests`).

## Quick start

    cd tools
    python3 observations.py --db ../data/observations.db init
    python3 observations.py --db ../data/observations.db list

To avoid typing --db every time, set an env var and alias, or just `cd` into a folder
where you always run it against the same file — the db is a single portable .db file,
safe to move, back up, or put under version control alongside the markdown docs.

## Commands

    init                 create the table
    fetch <url> ...       fetch a page, store raw HTML + your hand-typed extracted JSON
    add ...                store an observation with no URL (measurement, PDF, photo, call)
    list [--source-name] [--source-type]
    show <id> [--raw]

Run `python3 observations.py --help` or `python3 observations.py fetch --help` for full
option lists.

## Known limitation, fixed 2026-07-29

Live commerce pages embed session IDs and Cloudflare challenge tokens inside <script>
blocks that change on every request. Early testing against the real Suburban site
confirmed this: an unmodified refetch hashed differently purely because of these tokens,
which would have silently flooded the table with false "revision" rows. content_hash()
now strips <script> blocks before hashing. raw_content still stores the page untouched —
only the change-detection hash is normalized.

If another vendor's site embeds volatility somewhere other than <script> tags (inline
style timestamps, tracking pixels in the body, etc.), the same false-positive will
resurface for that vendor. Check a same-page refetch before trusting dedup on a new site.

## What's already seeded in data/observations.db

- #1, #2: the real SW6DEL and SW6DE product pages (suburbanrvparts.com), fetched live.
- #3: the ceiling register teardown measurement (duct_diameter_in still null — TODO
  per fixtures/ground-truth.yaml, measure the actual part and update with a new `add`
  call rather than editing this row).
