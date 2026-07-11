"""
Fetch trusted UK medical source pages (NHS, NICE) and save them as clean
text files in data/raw/, replacing the old manually copy-pasted files.

Each fetched page also gets a metadata sidecar (<slug>.meta.json) that
records the exact URL, licence, and retrieval timestamp, so every
document in the knowledge base is traceable back to its live source.

Usage:
    python scripts/fetch_sources.py                # fetch everything
    python scripts/fetch_sources.py --only nhs_diabetes_overview,nice_type2diabetes_overview
    python scripts/fetch_sources.py --list          # show configured sources
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from sources import DOMAIN_PROFILES, FORBIDDEN_DOMAINS, LICENSES, SOURCES

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

# Identifies this project and gives sites a contact point, per good
# scraping etiquette - not just a generic browser string.
USER_AGENT = (
    "DiaSift-Research/1.0 (MSc dissertation project; "
    "non-commercial educational RAG knowledge base; "
    "contact: oretimi08@gmail.com)"
)

REQUEST_TIMEOUT_SECONDS = 20
RETRIES_PER_SOURCE = 2
DELAY_BETWEEN_REQUESTS_SECONDS = 2

# Tags that never contain article content, wherever they appear.
STRIP_TAGS = [
    "script", "style", "noscript", "svg", "iframe", "form", "button",
    "template", "nav", "header", "footer",
]

# Class/id fragments that mark navigation, chrome, or decoration rather
# than article content. Matched case-insensitively as a substring.
STRIP_CLASS_HINTS = [
    "skip-link", "breadcrumb", "pagination", "cookie", "share",
    "back-to-top", "visually-hidden", "nhsuk-header", "nhsuk-footer",
    "print-link", "social",
]


# Tags treated as one paragraph/list-item unit. Inline tags nested inside
# these (like <a> links) are folded into the surrounding sentence rather
# than starting a new line - ingest_documents.py treats each line here as
# one atomic chunking unit, so a line must be a whole sentence/paragraph,
# not a sentence fragment split at a hyperlink.
BLOCK_TAGS = [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "li", "dt", "dd", "th", "td", "caption", "blockquote",
    "summary",  # e.g. nhs.uk's <details><summary> accordions - carries the
                # symptom/question label for the content nested below it
]


def extract_block_lines(container) -> list[str]:
    """One string per top-level block element, with any nested inline
    tags (links, spans, etc.) joined into that block's own line instead
    of becoming separate lines."""
    lines = []
    previous_line = None

    for tag in container.find_all(BLOCK_TAGS):
        # Skip blocks nested inside another block we already captured
        # (e.g. a <p> inside a <li>), so we don't emit the same text twice.
        if any(ancestor.name in BLOCK_TAGS for ancestor in tag.parents if ancestor is not container):
            continue

        line = " ".join(tag.get_text(" ", strip=True).split())

        if not line or line == previous_line:
            continue

        lines.append(line)
        previous_line = line

    return lines


def extract_article_text(html: str, domain_profile: str) -> tuple[str, str]:
    """Return (title, cleaned_text) for the main article content."""
    soup = BeautifulSoup(html, "html.parser")

    container = None
    for selector in DOMAIN_PROFILES[domain_profile]["content_selectors"]:
        container = soup.select_one(selector)
        if container is not None:
            break

    if container is None:
        raise ValueError(f"No content container matched for profile '{domain_profile}'")

    for tag in container.find_all(STRIP_TAGS):
        tag.decompose()

    for hint in STRIP_CLASS_HINTS:
        for tag in container.select(f'[class*="{hint}"], [id*="{hint}"]'):
            tag.decompose()

    for tag in container.select('[aria-hidden="true"]'):
        tag.decompose()

    heading = container.find(["h1", "h2"])
    title = heading.get_text(strip=True) if heading else (soup.title.get_text(strip=True) if soup.title else "")

    text = "\n".join(extract_block_lines(container))
    return title, text


def fetch_html(session: requests.Session, url: str) -> str:
    last_error = None

    for attempt in range(1, RETRIES_PER_SOURCE + 2):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.text
        except requests.RequestException as error:
            last_error = error
            if attempt <= RETRIES_PER_SOURCE:
                time.sleep(attempt * 2)

    raise RuntimeError(f"Failed to fetch {url} after {RETRIES_PER_SOURCE + 1} attempts: {last_error}")


def fetch_source(session: requests.Session, source: dict) -> None:
    slug = source["slug"]
    url = source["url"]

    for domain in FORBIDDEN_DOMAINS:
        if domain in url:
            raise ValueError(
                f"Refusing to fetch '{slug}': {domain} explicitly prohibits scraping."
            )

    print(f"Fetching {slug} <- {url}")
    html = fetch_html(session, url)

    title, text = extract_article_text(html, source["domain_profile"])

    if len(text) < 200:
        raise ValueError(
            f"Extracted text for '{slug}' looks too short ({len(text)} chars); "
            "the page structure may have changed. Check the domain profile selectors."
        )

    txt_path = RAW_DATA_DIR / f"{slug}.txt"
    txt_path.write_text(text, encoding="utf-8")

    meta_path = RAW_DATA_DIR / f"{slug}.meta.json"
    meta_path.write_text(
        json.dumps(
            {
                "slug": slug,
                "title": title,
                "url": url,
                "license": LICENSES[source["license"]],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "char_count": len(text),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"  saved {len(text)} chars -> {txt_path.name}")


def fetch_all(only_slugs: set[str] | None = None) -> list[str]:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    sources = SOURCES
    if only_slugs:
        sources = [s for s in SOURCES if s["slug"] in only_slugs]
        missing = only_slugs - {s["slug"] for s in sources}
        if missing:
            print(f"Warning: unknown source slugs ignored: {sorted(missing)}")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    failed = []

    for index, source in enumerate(sources):
        try:
            fetch_source(session, source)
        except Exception as error:
            print(f"  FAILED: {error}")
            failed.append(source["slug"])

        if index < len(sources) - 1:
            time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)

    return failed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        help="Comma-separated list of source slugs to fetch (default: all)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List configured sources and exit",
    )
    args = parser.parse_args()

    if args.list:
        for source in SOURCES:
            print(f"{source['slug']:45s} {source['url']}")
        return

    only_slugs = set(args.only.split(",")) if args.only else None

    print(f"Fetching {len(only_slugs) if only_slugs else len(SOURCES)} source(s)...\n")
    failed = fetch_all(only_slugs)

    print("\nDone.")
    if failed:
        print(f"{len(failed)} source(s) failed: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
