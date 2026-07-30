#!/usr/bin/env python3
"""
observations.py — the append-only evidence layer for RV Interchange.

One SQLite table. Two things go in every row: what a source actually said
(raw_content, untouched) and a small best-effort guess at the structured
claims inside it (extracted, a JSON blob you write by hand after reading).

Nothing in this table is authoritative. The `resolve` step (not built yet)
reads these rows and produces the real components/edges/attributes records,
with per-attribute provenance pointing back to the observation that supplied
each value. This table is never edited after insert — corrections happen by
adding a new observation, not by changing an old one.

No dependencies beyond `requests`, which is already on your system.

USAGE
-----

Initialize the database (creates observations.db in the current directory,
or wherever --db points):

    python3 observations.py init

Fetch a web page. Saves the raw HTML untouched. You then supply --extracted
with the handful of fields you actually care about, as JSON, after reading
the page yourself:

    python3 observations.py fetch \\
        "https://suburbanrvparts.com/suburban-water-heater-sw6del.../" \\
        --source-name suburbanrvparts.com \\
        --extracted '{"model": "SW6DEL", "sku": "5240A", "cutout_in": {"h": 12.75, "w": 12.75, "d": 19.19}}'

Fetching the same URL again only inserts a new row if the content actually
changed (dedup by hash) — that's how a silent manufacturer revision gets
caught rather than silently ignored.

Add an observation with no URL — a tape measurement, a data-plate photo, a
PDF manual, a phone call with a dealer:

    python3 observations.py add \\
        --source-type manual_measurement \\
        --source-name "walter - in-hand teardown" \\
        --extracted '{"duct_diameter_in": 4.0, "material": "plastic"}'

    python3 observations.py add \\
        --source-type manufacturer_pdf \\
        --source-name "Suburban SW-series install manual, 2019 rev" \\
        --raw-file ./manual_page_12.txt \\
        --extracted '{"orifice_size": "61", "gas_type": "LP"}'

Review what's in there:

    python3 observations.py list
    python3 observations.py list --source-name suburbanrvparts.com
    python3 observations.py show 3
"""

import argparse
import hashlib
import html
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = "observations.db"

_SCRIPT_BLOCK_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)

SOURCE_TYPES = {
    "retailer_page",
    "manufacturer_pdf",
    "manufacturer_page",
    "manual_measurement",
    "dataplate_photo",
    "retailer_prose",
    "forum_post",
    "dealer_call",
    "other",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type        TEXT NOT NULL,
    source_name        TEXT NOT NULL,
    url                TEXT,
    fetched_at         TEXT NOT NULL,
    fetched_by         TEXT NOT NULL,
    content_hash       TEXT,
    raw_content        TEXT,
    extracted          TEXT,
    extraction_method  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_obs_url ON observations(url);
CREATE INDEX IF NOT EXISTS idx_obs_source_name ON observations(source_name);
CREATE INDEX IF NOT EXISTS idx_obs_hash ON observations(content_hash);
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def content_hash(text):
    """
    Hash for change detection — NOT the same as what's stored in raw_content.

    Live commerce pages embed session IDs, analytics timestamps, and
    Cloudflare challenge tokens inside <script> blocks that change on every
    single request regardless of whether the product content changed at all.
    Hashing the raw HTML directly makes every refetch look like a revision.

    So: strip <script>...</script> blocks before hashing. raw_content still
    stores the untouched original — this function only affects what gets
    compared for dedup.
    """
    if text is None:
        return None
    normalized = _SCRIPT_BLOCK_RE.sub("", text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


_STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES_RE = re.compile(r"\n\s*\n+")

# Best-effort regexes for common spec fields on RV parts pages. These are
# guesses to speed up hand-typing extracted JSON, not a real parser — always
# eyeball the source page before trusting a match.
_FIELD_PATTERNS = {
    "sku": re.compile(r"\b(?:SKU|Item\s*#|Part\s*#|Model\s*#?)\s*[:#]?\s*(?=[A-Za-z0-9\-]*\d)([A-Za-z0-9\-]{3,20})", re.IGNORECASE),
    "dimensions_in": re.compile(r"\d+(?:\.\d+)?\"?\s*[xX]\s*\d+(?:\.\d+)?\"?\s*[xX]\s*\d+(?:\.\d+)?\"?\s*(?:in\b|inch(?:es)?\b)?", re.IGNORECASE),
    "weight_lbs": re.compile(r"\d+(?:\.\d+)?\s*(?:lbs?\.?|pounds?)\b", re.IGNORECASE),
    "btu": re.compile(r"\d{3,6}\s*BTU\b", re.IGNORECASE),
    "voltage": re.compile(r"\b\d{1,3}\s*[Vv](?:olts?)?\b"),
    "price": re.compile(r"\$\s?\d+(?:\.\d{2})?"),
}


def strip_tags(html_text):
    """Rough HTML-to-text for eyeballing a fetched page in the terminal."""
    text = _SCRIPT_BLOCK_RE.sub(" ", html_text)
    text = _STYLE_BLOCK_RE.sub(" ", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n", text)
    return text.strip()


def detect_candidate_fields(text):
    """Best-effort regex guesses at common spec fields. Not authoritative."""
    found = {}
    for name, pattern in _FIELD_PATTERNS.items():
        m = pattern.search(text)
        if m:
            found[name] = m.group(0).strip()
    return found


def interactive_capture(raw_html):
    """Show auto-detected candidates, let the user approve/edit/add, return
    the extracted dict (or None if there's nothing to save)."""
    text = strip_tags(raw_html)
    candidates = detect_candidate_fields(text)

    print()
    print("--- Auto-detected candidate fields (verify against the page!) ---")
    if candidates:
        for k, v in candidates.items():
            print(f"  {k}: {v}")
    else:
        print("  (none detected)")
    print("-------------------------------------------------------------")
    print("Enter fields as name=value (blank line to finish).")
    print("Type 'a' to accept all detected fields above, then keep adding/editing.")

    fields = {}
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            break
        if line.lower() == "a":
            fields.update(candidates)
            print(f"  added {len(candidates)} detected field(s)")
            continue
        if "=" not in line:
            print("  format is name=value (or 'a' or blank line to finish)")
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key:
            fields[key] = value

    if not fields:
        return None

    print()
    print("Extracted JSON:")
    print(json.dumps(fields, indent=2))
    confirm = input("Save this with the observation? [Y/n] ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("Discarding extracted fields — raw page will still be saved.")
        return None
    return fields


def get_conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_init(args):
    conn = get_conn(args.db)
    conn.executescript(SCHEMA)
    conn.commit()
    print(f"Initialized {args.db}")


def latest_hash_for_url(conn, url):
    row = conn.execute(
        "SELECT content_hash FROM observations WHERE url = ? "
        "ORDER BY fetched_at DESC LIMIT 1",
        (url,),
    ).fetchone()
    return row["content_hash"] if row else None


def insert_observation(conn, *, source_type, source_name, url, raw_content,
                        extracted, extraction_method, fetched_by):
    h = content_hash(raw_content)
    conn.execute(
        """
        INSERT INTO observations
            (source_type, source_name, url, fetched_at, fetched_by,
             content_hash, raw_content, extracted, extraction_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_type,
            source_name,
            url,
            now_iso(),
            fetched_by,
            h,
            raw_content,
            json.dumps(extracted) if extracted is not None else None,
            extraction_method,
        ),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


def load_extracted(args):
    if args.extracted_file:
        text, source = Path(args.extracted_file).read_text(), args.extracted_file
    elif args.extracted:
        text, source = args.extracted, "--extracted"
    else:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {source}: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_fetch(args):
    import requests

    conn = get_conn(args.db)
    extracted = load_extracted(args)

    url = args.url
    source_name = args.source_name

    if args.no_interactive:
        if not url:
            print("URL is required (positional arg) with --no-interactive.", file=sys.stderr)
            sys.exit(1)
        if not source_name:
            print("--source-name is required with --no-interactive.", file=sys.stderr)
            sys.exit(1)
    else:
        if not url:
            url = input("URL to fetch: ").strip()
            if not url:
                print("No URL given.", file=sys.stderr)
                sys.exit(1)
        if not source_name:
            source_name = input("Source name (e.g. suburbanrvparts.com): ").strip()
            if not source_name:
                print("Source name is required.", file=sys.stderr)
                sys.exit(1)

    resp = requests.get(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (RV-Interchange research capture)"
    })
    resp.raise_for_status()
    raw = resp.text

    new_hash = content_hash(raw)
    old_hash = latest_hash_for_url(conn, url)

    if old_hash == new_hash and not args.force:
        print(f"Unchanged since last fetch (hash {new_hash[:12]}...). "
              f"Skipping insert. Use --force to insert anyway.")
        return

    if old_hash is not None and old_hash != new_hash:
        print(f"CONTENT CHANGED for {url}")
        print(f"  old hash: {old_hash[:12]}...")
        print(f"  new hash: {new_hash[:12]}...")
        print("  Inserting as a new observation (a revision, not a correction).")

    if extracted is None and not args.no_interactive:
        extracted = interactive_capture(raw)

    obs_id = insert_observation(
        conn,
        source_type=args.source_type,
        source_name=source_name,
        url=url,
        raw_content=raw,
        extracted=extracted,
        extraction_method=args.extraction_method,
        fetched_by=args.fetched_by,
    )
    print(f"Inserted observation #{obs_id} ({len(raw)} chars raw)")


def cmd_add(args):
    conn = get_conn(args.db)
    extracted = load_extracted(args)

    raw = None
    if args.raw_file:
        raw = Path(args.raw_file).read_text()
    elif args.raw:
        raw = args.raw

    if raw is None and extracted is None:
        print("Nothing to insert: provide --raw/--raw-file and/or "
              "--extracted/--extracted-file.", file=sys.stderr)
        sys.exit(1)

    obs_id = insert_observation(
        conn,
        source_type=args.source_type,
        source_name=args.source_name,
        url=args.url,
        raw_content=raw,
        extracted=extracted,
        extraction_method=args.extraction_method,
        fetched_by=args.fetched_by,
    )
    print(f"Inserted observation #{obs_id}")


def cmd_list(args):
    conn = get_conn(args.db)
    q = "SELECT id, source_type, source_name, url, fetched_at, extraction_method FROM observations WHERE 1=1"
    params = []
    if args.source_name:
        q += " AND source_name LIKE ?"
        params.append(f"%{args.source_name}%")
    if args.source_type:
        q += " AND source_type = ?"
        params.append(args.source_type)
    q += " ORDER BY id"

    rows = conn.execute(q, params).fetchall()
    if not rows:
        print("No observations found.")
        return

    for r in rows:
        print(f"#{r['id']:<4} {r['fetched_at']}  [{r['source_type']}]  "
              f"{r['source_name']}")
        if r["url"]:
            print(f"       {r['url']}")


def cmd_show(args):
    conn = get_conn(args.db)
    row = conn.execute(
        "SELECT * FROM observations WHERE id = ?", (args.id,)
    ).fetchone()
    if row is None:
        print(f"No observation #{args.id}")
        sys.exit(1)

    print(f"id:                {row['id']}")
    print(f"source_type:       {row['source_type']}")
    print(f"source_name:       {row['source_name']}")
    print(f"url:               {row['url']}")
    print(f"fetched_at:        {row['fetched_at']}")
    print(f"fetched_by:        {row['fetched_by']}")
    print(f"extraction_method: {row['extraction_method']}")
    print(f"content_hash:      {row['content_hash']}")
    print()
    if row["extracted"]:
        print("extracted:")
        print(json.dumps(json.loads(row["extracted"]), indent=2))
        print()
    if args.raw:
        print("raw_content:")
        print(row["raw_content"])
    else:
        n = len(row["raw_content"] or "")
        print(f"raw_content: {n} chars (use --raw to print it)")


def build_parser():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=DEFAULT_DB, help=f"SQLite file (default: {DEFAULT_DB})")
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create the observations table")
    p_init.set_defaults(func=cmd_init)

    p_fetch = sub.add_parser("fetch", help="Fetch a URL and store it as an observation")
    p_fetch.add_argument("url", nargs="?", default=None,
                          help="Omit to be prompted for it")
    p_fetch.add_argument("--source-name", default=None,
                          help="Omit to be prompted for it")
    p_fetch.add_argument("--source-type", default="retailer_page", choices=sorted(SOURCE_TYPES))
    p_fetch.add_argument("--extracted", help="JSON string of the fields you pulled from the page")
    p_fetch.add_argument("--extracted-file", help="Path to a JSON file instead of an inline string")
    p_fetch.add_argument("--extraction-method", default="hand_typed",
                          choices=["hand_typed", "script", "ocr"])
    p_fetch.add_argument("--fetched-by", default="walter")
    p_fetch.add_argument("--force", action="store_true",
                          help="Insert even if content hash matches the last fetch")
    p_fetch.add_argument("--no-interactive", action="store_true",
                          help="Never prompt: url/--source-name become required, "
                               "and --extracted is left as given (no field capture)")
    p_fetch.set_defaults(func=cmd_fetch)

    p_add = sub.add_parser("add", help="Add an observation with no URL (measurement, PDF, photo, call)")
    p_add.add_argument("--source-type", required=True, choices=sorted(SOURCE_TYPES))
    p_add.add_argument("--source-name", required=True)
    p_add.add_argument("--url", default=None, help="Optional — set if the source does have one")
    p_add.add_argument("--raw", help="Raw text inline")
    p_add.add_argument("--raw-file", help="Path to a text file with the raw content")
    p_add.add_argument("--extracted", help="JSON string of the fields you pulled from the source")
    p_add.add_argument("--extracted-file", help="Path to a JSON file instead of an inline string")
    p_add.add_argument("--extraction-method", default="hand_typed",
                        choices=["hand_typed", "script", "ocr"])
    p_add.add_argument("--fetched-by", default="walter")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List observations")
    p_list.add_argument("--source-name", help="Filter: substring match")
    p_list.add_argument("--source-type", choices=sorted(SOURCE_TYPES))
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show one observation in full")
    p_show.add_argument("id", type=int)
    p_show.add_argument("--raw", action="store_true", help="Also print the full raw_content")
    p_show.set_defaults(func=cmd_show)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
