"""
Automated abstention evaluation for Diasift.

Retrieval accuracy (run_retrieval_eval.py) only measures whether the right
chunks come back. It says nothing about whether Diasift makes the right
call on *when to answer at all* - refusing unsafe personal-medical questions
and out-of-scope questions, while still answering legitimate educational
ones. This script measures that decision directly against a labeled set of
questions, run through the real pipeline (dry-run, no LLM call needed).

Two error types are reported separately because they are not equally risky:
- missed refusal: pipeline answered when it should have refused (safety risk)
- false refusal: pipeline refused when it should have answered (usefulness cost)

Usage:
    python3 evaluation/run_abstention_eval.py
    python3 evaluation/run_abstention_eval.py --verbose
"""

from argparse import ArgumentParser
from pathlib import Path
import json
import sys


BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
ABSTENTION_QUESTIONS_FILE = Path(__file__).resolve().parent / "abstention_questions.json"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from evidence_label import NO_CLEAR_EVIDENCE  # noqa: E402
from rag_pipeline import run_rag_pipeline  # noqa: E402


def load_abstention_questions() -> list[dict]:
    with open(ABSTENTION_QUESTIONS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_actual_decision(result: dict) -> tuple[str, str | None]:
    """
    Read the pipeline's decision back out of its result dict.

    Checks the gates in the same order the pipeline applies them: unsafe
    first, then scope, then evidence strength.
    """
    if result["unsafe_question"]:
        return "refuse", "unsafe"

    if not result["scope_check"]["in_scope"]:
        return "refuse", "out_of_scope"

    if result["evidence_label"] == NO_CLEAR_EVIDENCE:
        return "refuse", "no_evidence"

    return "answer", None


def evaluate_question(item: dict) -> dict:
    question = item["question"]
    expected_decision = item["expected_decision"]
    expected_reason = item.get("expected_reason")

    result = run_rag_pipeline(question=question, call_api=False)
    actual_decision, actual_reason = get_actual_decision(result)

    decision_correct = actual_decision == expected_decision
    reason_correct = expected_reason is None or actual_reason == expected_reason

    error_type = None
    if not decision_correct:
        error_type = "missed_refusal" if expected_decision == "refuse" else "false_refusal"

    return {
        "question": question,
        "expected_decision": expected_decision,
        "expected_reason": expected_reason,
        "actual_decision": actual_decision,
        "actual_reason": actual_reason,
        "decision_correct": decision_correct,
        "reason_correct": reason_correct,
        "error_type": error_type,
    }


def summarize(per_question_results: list[dict]) -> dict:
    total = len(per_question_results)
    missed_refusals = [r for r in per_question_results if r["error_type"] == "missed_refusal"]
    false_refusals = [r for r in per_question_results if r["error_type"] == "false_refusal"]

    refuse_cases = [r for r in per_question_results if r["expected_decision"] == "refuse"]
    reason_correct_count = sum(
        1 for r in refuse_cases if r["decision_correct"] and r["reason_correct"]
    )

    return {
        "total_questions": total,
        "decision_accuracy": sum(r["decision_correct"] for r in per_question_results) / total,
        "missed_refusal_count": len(missed_refusals),
        "false_refusal_count": len(false_refusals),
        "reason_accuracy_among_correct_refusals": (
            reason_correct_count / len(refuse_cases) if refuse_cases else None
        ),
    }


def print_report(per_question_results: list[dict], summary: dict, verbose: bool) -> None:
    print("=" * 80)
    print("Diasift abstention evaluation")
    print("=" * 80)

    for result in per_question_results:
        if result["decision_correct"]:
            status = "OK"
        elif result["error_type"] == "missed_refusal":
            status = "MISSED REFUSAL (answered but should have refused)"
        else:
            status = "FALSE REFUSAL (refused but should have answered)"

        if verbose or not result["decision_correct"]:
            print(f"\n[{status}] {result['question']}")
            print(
                f"  expected: {result['expected_decision']}"
                f"{' (' + result['expected_reason'] + ')' if result['expected_reason'] else ''}"
            )
            print(
                f"  actual:   {result['actual_decision']}"
                f"{' (' + result['actual_reason'] + ')' if result['actual_reason'] else ''}"
            )

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Questions evaluated: {summary['total_questions']}")
    print(f"Decision accuracy:   {summary['decision_accuracy']:.1%}")
    print(f"Missed refusals:     {summary['missed_refusal_count']} (answered when it should refuse - safety risk)")
    print(f"False refusals:      {summary['false_refusal_count']} (refused when it should answer - usefulness cost)")

    if summary["reason_accuracy_among_correct_refusals"] is not None:
        print(
            "Refusal reason accuracy: "
            f"{summary['reason_accuracy_among_correct_refusals']:.1%} "
            "(of correctly-refused questions, how many gave the right reason category)"
        )


def parse_args() -> ArgumentParser:
    parser = ArgumentParser(description="Run Diasift's automated abstention evaluation.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show expected vs actual for correct decisions too, not only errors.",
    )
    parser.add_argument(
        "--save-json",
        help="Optional path to save the full results as JSON.",
    )
    return parser


def main() -> None:
    parser = parse_args()
    args = parser.parse_args()

    abstention_questions = load_abstention_questions()
    per_question_results = [evaluate_question(item) for item in abstention_questions]
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
