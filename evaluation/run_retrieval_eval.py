"""
Automated retrieval evaluation for Diasift.

Runs each labeled question in eval_questions.json through the real retrieval
path (search_test.search_documents) and reports recall@1, recall@3, recall@5,
and mean reciprocal rank (MRR) against the expected source(s).

Usage:
    python3 evaluation/run_retrieval_eval.py
    python3 evaluation/run_retrieval_eval.py --k 5 --verbose
"""

from argparse import ArgumentParser
from pathlib import Path
import json
import sys


BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
EVAL_QUESTIONS_FILE = Path(__file__).resolve().parent / "eval_questions.json"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from search_test import search_documents  # noqa: E402


def load_eval_questions() -> list[dict]:
    with open(EVAL_QUESTIONS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def first_hit_rank(expected_sources: list[str], retrieved_sources: list[str]) -> int | None:
    """Return the 1-based rank of the first retrieved chunk whose source is
    in expected_sources, or None if no retrieved chunk matches."""
    expected_set = set(expected_sources)

    for rank, source in enumerate(retrieved_sources, start=1):
        if source in expected_set:
            return rank

    return None


def evaluate_question(item: dict, max_k: int) -> dict:
    question = item["question"]
    expected_sources = item["expected_sources"]

    results = search_documents(question, number_of_results=max_k, verbose=False)
    retrieved_sources = [result["metadata"].get("source") for result in results]

    rank = first_hit_rank(expected_sources, retrieved_sources)

    return {
        "question": question,
        "expected_sources": expected_sources,
        "retrieved_sources": retrieved_sources,
        "rank": rank,
        "reciprocal_rank": (1 / rank) if rank else 0,
        "hit_at_1": rank == 1,
        "hit_at_3": rank is not None and rank <= 3,
        "hit_at_5": rank is not None and rank <= 5,
    }


def summarize(per_question_results: list[dict]) -> dict:
    total = len(per_question_results)

    return {
        "total_questions": total,
        "recall_at_1": sum(r["hit_at_1"] for r in per_question_results) / total,
        "recall_at_3": sum(r["hit_at_3"] for r in per_question_results) / total,
        "recall_at_5": sum(r["hit_at_5"] for r in per_question_results) / total,
        "mrr": sum(r["reciprocal_rank"] for r in per_question_results) / total,
    }


def print_report(per_question_results: list[dict], summary: dict, verbose: bool) -> None:
    print("=" * 80)
    print("Diasift retrieval evaluation")
    print("=" * 80)

    for result in per_question_results:
        status = "HIT " + f"(rank {result['rank']})" if result["rank"] else "MISS"

        print(f"\n[{status}] {result['question']}")

        if verbose or not result["rank"]:
            print(f"  expected:  {result['expected_sources']}")
            print(f"  retrieved: {result['retrieved_sources']}")

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Questions evaluated: {summary['total_questions']}")
    print(f"Recall@1: {summary['recall_at_1']:.1%}")
    print(f"Recall@3: {summary['recall_at_3']:.1%}")
    print(f"Recall@5: {summary['recall_at_5']:.1%}")
    print(f"MRR:      {summary['mrr']:.3f}")


def parse_args() -> ArgumentParser:
    parser = ArgumentParser(description="Run Diasift's automated retrieval evaluation.")
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of results to retrieve per question. Default: 5",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show expected vs retrieved sources for hits too, not only misses.",
    )
    parser.add_argument(
        "--save-json",
        help="Optional path to save the full results as JSON.",
    )
    return parser


def main() -> None:
    parser = parse_args()
    args = parser.parse_args()

    eval_questions = load_eval_questions()
    per_question_results = [evaluate_question(item, args.k) for item in eval_questions]
    summary = summarize(per_question_results)

    print_report(per_question_results, summary, verbose=args.verbose)

    if args.save_json:
        output = {"summary": summary, "results": per_question_results}
        Path(args.save_json).write_text(
            json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nSaved full results to {args.save_json}")


if __name__ == "__main__":
    main()
