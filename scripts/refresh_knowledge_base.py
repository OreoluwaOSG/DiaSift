"""
One-command refresh of the whole knowledge base:

    1. fetch_sources     - pull the latest NHS/NICE pages into data/raw/
    2. ingest_documents   - clean + chunk them into data/processed/chunks.json
    3. build_index        - re-embed everything into the ChromaDB vector store

Run this whenever you want DiaSift's knowledge base to reflect the
current live NHS/NICE guidance, instead of hand-editing files in
data/raw/.

Usage:
    python scripts/refresh_knowledge_base.py
    python scripts/refresh_knowledge_base.py --skip-index   # skip the (slow) embedding step
"""

import argparse
import sys

from build_index import build_index
from fetch_sources import fetch_all
from ingest_documents import ingest_documents


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Fetch and re-chunk sources, but don't rebuild the ChromaDB vector store.",
    )
    args = parser.parse_args()

    print("=== Step 1/3: fetching sources ===")
    failed = fetch_all()
    if failed:
        print(f"\n{len(failed)} source(s) failed to fetch: {failed}")
        print("Aborting before ingestion so stale/partial data isn't indexed.")
        sys.exit(1)

    print("\n=== Step 2/3: ingesting + chunking documents ===")
    ingest_documents()

    if args.skip_index:
        print("\n--skip-index set: leaving the vector store untouched.")
        return

    print("\n=== Step 3/3: rebuilding vector index ===")
    build_index()

    print("\nKnowledge base refresh complete.")


if __name__ == "__main__":
    main()
