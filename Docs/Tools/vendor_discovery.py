#!/usr/bin/env python3
"""Discover vendor manuals, brochures, parts lists, and related documents.

The crawler is deliberately conservative: it stays on the seed host for HTML pages,
respects robots.txt by default, rate-limits requests, never downloads documents, and
writes a review queue for later capture with observations.py.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

USER_AGENT = "RV-Interchange vendor-discovery/0.1 (+research; rate-limited)"
DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip"}
DOC_HOSTS = {"drive.google.com", "docs.google.com", "dropbox.com", "www.dropbox.com"}
DOC_WORDS = re.compile(
    r"manual|brochure|flyer|catalog|parts?|service|install|technical|spec(?:ification)?|"
    r"diagram|drawing|dimension|wiring|replacement|cross[ -]?reference|download|guide",
    re.I,
)
CLASSIFIERS = [
    ("service_manual", re.compile(r"service|repair|troubleshoot", re.I), 10),
    ("parts_catalog", re.compile(r"parts?\s*(catalog|list|breakdown|diagram)|exploded", re.I), 10),
    ("installation_manual", re.compile(r"install|opening instruction|mounting", re.I), 9),
    ("fitment_guide", re.compile(r"replacement|retrofit|compatib|cross[ -]?ref|fitment", re.I), 9),
    ("dimension_drawing", re.compile(r"dimension|drawing|cutout|opening", re.I), 8),
    ("wiring_diagram", re.compile(r"wiring|schematic|terminal", re.I), 8),
    ("user_manual", re.compile(r"user manual|owner.?s manual|operation manual", re.I), 7),
    ("spec_sheet", re.compile(r"spec(?:ification)?|data sheet", re.I), 7),
    ("sales_brochure", re.compile(r"brochure|flyer|sales", re.I), 5),
    ("catalog", re.compile(r"catalog", re.I), 5),
    ("guide", re.compile(r"guide|manual", re.I), 4),
]


@dataclass(frozen=True)
class Candidate:
    vendor: str
    title: str
    url: str
    source_page: str
    document_type: str
    priority: int
    host: str
    model_hint: str = ""
    notes: str = ""
    fetched: bool = False


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str, str]] = []
        self._href: str | None = None
        self._anchor: list[str] = []
        self._context: list[str] = []
        self._row_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = dict(attrs)
        if tag in {"tr", "li", "article", "section"}:
            self._row_depth += 1
            if self._row_depth == 1:
                self._context = []
        if tag == "a" and attrs_d.get("href"):
            self._href = attrs_d["href"]
            self._anchor = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._href is not None:
            self._anchor.append(text)
        if self._row_depth:
            self._context.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._anchor).strip(), " ".join(self._context).strip()))
            self._href = None
            self._anchor = []
        if tag in {"tr", "li", "article", "section"} and self._row_depth:
            self._row_depth -= 1
            if self._row_depth == 0:
                self._context = []


def canonicalize(url: str) -> str:
    url, _ = urldefrag(url)
    parsed = urlparse(url)
    if parsed.netloc in {"drive.google.com", "docs.google.com"}:
        if "/file/d/" in parsed.path:
            return f"https://drive.google.com{parsed.path.split('/view')[0]}"
        file_id = parse_qs(parsed.query).get("id", [""])[0]
        if file_id:
            return f"https://drive.google.com/file/d/{file_id}"
    return parsed._replace(query="").geturl()


def is_document_link(url: str, label: str, context: str) -> bool:
    parsed = urlparse(url)
    suffix = Path(parsed.path.lower()).suffix
    return suffix in DOC_EXTENSIONS or parsed.netloc.lower() in DOC_HOSTS or bool(
        DOC_WORDS.search(f"{label} {context} {parsed.path}")
    )


def classify(label: str, context: str, url: str) -> tuple[str, int]:
    haystack = f"{label} {context} {url}"
    for name, pattern, score in CLASSIFIERS:
        if pattern.search(haystack):
            return name, score
    return "document", 2


def model_hint(label: str, context: str) -> str:
    text = f"{context} {label}"
    tokens = re.findall(r"\b[A-Z]{1,5}[A-Z0-9-]*\d[A-Z0-9-]*\b", text, flags=re.I)
    tokens += re.findall(
        r"\b(?:InstaShower|HybridShower|InstaCool|InstaHeat)\s+"
        r"\d+(?:\s*(?:Plus|Pro|Ultra|II))?\b",
        text,
        flags=re.I,
    )
    stop = {"12V", "115V", "120V", "BTU", "PDF"}
    unique = []
    for token in tokens:
        token = " ".join(token.upper().split())
        if token not in stop and token not in unique:
            unique.append(token)
    return ", ".join(unique[:8])


class DiscoveryCrawler:
    def __init__(
        self,
        vendor: str,
        seeds: list[str],
        delay: float,
        max_pages: int,
        respect_robots: bool = True,
        timeout: int = 30,
    ) -> None:
        self.vendor = vendor
        self.seeds = seeds
        self.delay = delay
        self.max_pages = max_pages
        self.respect_robots = respect_robots
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._robots: dict[str, RobotFileParser] = {}

    def _allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        if root not in self._robots:
            rp = RobotFileParser(urljoin(root, "/robots.txt"))
            try:
                rp.read()
            except Exception:
                return True
            self._robots[root] = rp
        return self._robots[root].can_fetch(USER_AGENT, url)

    def discover(self) -> list[Candidate]:
        queue = list(dict.fromkeys(self.seeds))
        seed_hosts = {urlparse(seed).netloc.lower() for seed in self.seeds}
        visited: set[str] = set()
        found: dict[str, Candidate] = {}

        while queue and len(visited) < self.max_pages:
            requested = canonicalize(queue.pop(0))
            if requested in visited or not self._allowed(requested):
                continue
            visited.add(requested)
            try:
                response = self.session.get(requested, timeout=self.timeout, allow_redirects=True)
                response.raise_for_status()
            except requests.RequestException as exc:
                print(f"warning: {requested}: {exc}", file=sys.stderr)
                continue
            final_url = canonicalize(response.url)
            content_type = response.headers.get("content-type", "").lower()
            if "html" not in content_type and "xhtml" not in content_type:
                continue
            parser = LinkParser()
            parser.feed(response.text)
            for href, label, context in parser.links:
                absolute = canonicalize(urljoin(final_url, href))
                parsed = urlparse(absolute)
                if parsed.scheme not in {"http", "https"}:
                    continue
                if is_document_link(absolute, label, context):
                    document_type, priority = classify(label, context, absolute)
                    title = label if label and label.lower() != "download" else context
                    title = title.strip() or Path(parsed.path).name or absolute
                    candidate = Candidate(
                        vendor=self.vendor,
                        title=title[:300],
                        url=absolute,
                        source_page=final_url,
                        document_type=document_type,
                        priority=priority,
                        host=parsed.netloc.lower(),
                        model_hint=model_hint(label, context),
                    )
                    previous = found.get(absolute)
                    if previous is None or candidate.priority > previous.priority:
                        found[absolute] = candidate
                elif parsed.netloc.lower() in seed_hosts and absolute not in visited:
                    if DOC_WORDS.search(f"{label} {context} {parsed.path}"):
                        queue.append(absolute)
            if self.delay:
                time.sleep(self.delay)
        return sorted(found.values(), key=lambda item: (-item.priority, item.document_type, item.title.lower()))


def write_output(candidates: Iterable[Candidate], path: Path) -> None:
    rows = [asdict(candidate) for candidate in candidates]
    if path.suffix.lower() == ".csv":
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(Candidate.__dataclass_fields__))
            writer.writeheader()
            writer.writerows(rows)
    else:
        path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vendor", required=True)
    parser.add_argument("--seed", action="append", required=True, help="Seed page; repeatable")
    parser.add_argument("--out", type=Path, required=True, help=".json or .csv review queue")
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--ignore-robots", action="store_true")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    crawler = DiscoveryCrawler(
        args.vendor,
        args.seed,
        args.delay,
        args.max_pages,
        not args.ignore_robots,
        args.timeout,
    )
    candidates = crawler.discover()
    write_output(candidates, args.out)
    print(f"Discovered {len(candidates)} candidate documents; wrote {args.out}")
    for item in candidates[: args.top]:
        hint = f" [{item.model_hint}]" if item.model_hint else ""
        print(f"  [{item.priority:>2}] {item.document_type:<20} {item.title[:70]}{hint}")
    print("No documents were downloaded. Review the queue, then capture selected URLs with observations.py.")
    return 0 if candidates else 1


if __name__ == "__main__":
    raise SystemExit(main())
