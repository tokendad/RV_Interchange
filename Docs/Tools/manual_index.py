#!/usr/bin/env python3
"""
manual_index.py — scrape the myrvworks.com service-manual index into a local
work queue.

The index page is one HTML table: Category | Manufacturer | File Name | PDF URL.
That table is worth more than any single manual, because it tells you what
exists before you spend a single request on a document you don't need.

This script fetches the index ONCE and writes a queue. It does not download
any PDFs. Fetching those is a separate, deliberate, rate-limited step —
see PLAN-Staged_Build.md §7 (legal/ethical position: rate-limit, cache raw,
prefer manufacturer sources).

    python3 manual_index.py --out manual_queue.json
    python3 manual_index.py --out manual_queue.json --priority-only
    python3 manual_index.py --stats

The --priority flags score each row against the v0 scope defined in
PLAN-Staged_Build.md §3 (water heaters, furnaces, thermostats, monitor
panels, roof vents) so the queue sorts itself toward what's actually
needed now rather than what's merely available.
"""

import argparse
import json
import re
import sys
from collections import Counter

INDEX_URL = "https://myrvworks.com/manuals/"

# v0 scope from PLAN-Staged_Build.md §3, plus the specific in-hand parts
# from fixtures/ground-truth.yaml. Category slugs come from the index's own
# hf:tax:component_category column.
V0_CATEGORIES = {
    "water-heater": 10,
    "furnaces": 10,
    "monitor-system": 9,      # KIB M21VW is an in-hand part
    "roof-vent-fans": 9,      # unbranded 14x14 vent is an in-hand part
    "tank-monitors": 7,
    "air-conditioners": 6,    # Coleman thermostat is an in-hand part
}

# Document-title patterns that signal interchange-grade content: crosswalks,
# dimension tables, parts lists, supersession charts. These are the documents
# that carry edges, not just attributes.
HIGH_VALUE_TITLE = re.compile(
    r"cross[\s\-]?ref|dimension|parts?\s*list|parts?\s*break|"
    r"compatib|identification|chart|model\s*num|replacement\s*parts",
    re.IGNORECASE,
)


def fetch_index():
    import requests
    resp = requests.get(INDEX_URL, timeout=60, headers={
        "User-Agent": "Mozilla/5.0 (RV-Interchange research capture)"
    })
    resp.raise_for_status()
    return resp.text


# The index renders as a WordPress table; each data row carries the PDF link
# plus taxonomy slugs in trailing cells.
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
_HREF_RE = re.compile(r'href=["\']([^"\']+\.pdf)["\']', re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def clean(cell):
    import html as html_mod
    return html_mod.unescape(_TAG_RE.sub("", cell)).strip()


def parse_index(html_text):
    rows = []
    seen_urls = set()
    for row_html in _ROW_RE.findall(html_text):
        cells = _CELL_RE.findall(row_html)
        if len(cells) < 4:
            continue
        href = _HREF_RE.search(row_html)
        if not href:
            continue
        url = href.group(1)
        category = clean(cells[0])
        manufacturer = clean(cells[1])
        title = clean(cells[2])
        # taxonomy slugs, when present, are the last two cells
        cat_slug = clean(cells[4]) if len(cells) > 4 else ""
        mfg_slug = clean(cells[5]) if len(cells) > 5 else ""

        # The same PDF is listed under multiple categories in this library
        # (Lippert "Master Manual" appears under axles, awnings, steps,
        # slide-rooms, leveling). Dedupe by URL, keep the first category.
        if url in seen_urls:
            continue
        seen_urls.add(url)

        rows.append({
            "category": category,
            "category_slug": cat_slug,
            "manufacturer": manufacturer,
            "manufacturer_slug": mfg_slug,
            "title": title,
            "url": url,
            "priority": score(cat_slug or category, title),
            "fetched": False,
        })
    return rows


def score(category_slug, title):
    """Higher = pull sooner. Scope relevance + interchange-content signal."""
    s = 0
    for slug, weight in V0_CATEGORIES.items():
        if slug in category_slug.lower():
            s += weight
            break
    if HIGH_VALUE_TITLE.search(title):
        s += 5
    return s


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", help="Write the queue to this JSON file")
    p.add_argument("--priority-only", action="store_true",
                   help="Keep only rows scoring > 0 (in v0 scope or interchange-grade)")
    p.add_argument("--stats", action="store_true", help="Print a category/manufacturer summary")
    p.add_argument("--top", type=int, default=0, help="Print the N highest-priority rows")
    args = p.parse_args()

    html_text = fetch_index()
    rows = parse_index(html_text)
    if not rows:
        print("No rows parsed — the index markup probably changed.", file=sys.stderr)
        sys.exit(1)

    print(f"Parsed {len(rows)} unique PDFs from the index.")

    if args.stats:
        print("\nBy category:")
        for cat, n in Counter(r["category"] for r in rows).most_common():
            print(f"  {n:>4}  {cat}")
        print("\nBy manufacturer:")
        for mfg, n in Counter(r["manufacturer"] for r in rows).most_common(20):
            print(f"  {n:>4}  {mfg}")

    rows.sort(key=lambda r: (-r["priority"], r["category"], r["title"]))

    if args.priority_only:
        rows = [r for r in rows if r["priority"] > 0]
        print(f"{len(rows)} rows in v0 scope or flagged interchange-grade.")

    if args.top:
        print(f"\nTop {args.top} by priority:")
        for r in rows[:args.top]:
            print(f"  [{r['priority']:>2}] {r['manufacturer']:<22} {r['title'][:58]}")

    if args.out:
        with open(args.out, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"\nWrote {len(rows)} rows to {args.out}")
        print("Nothing downloaded. Feed URLs to observations.py fetch one at a time,")
        print("at whatever rate you're comfortable with against a small business's site.")


if __name__ == "__main__":
    main()
